"""Deterministic TryHackMe completed-room pagination tests (no live login)."""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import portfolio  # noqa: E402
import room_sync  # noqa: E402
from platforms import cisco_netacad as cisco  # noqa: E402
from platforms import hackthebox as htb  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FALLBACK_DATE = dt.date(2026, 7, 28)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def live_pages() -> dict[int, dict]:
    return {
        1: fixture("thm_completed_rooms_page1.json"),
        2: fixture("thm_completed_rooms_page2.json"),
    }


def room(code: str, title: str | None = None, **extra) -> dict:
    value = {
        "type": "walkthrough",
        "difficulty": "easy",
        "code": code,
        "title": title or code.replace("-", " ").title(),
    }
    value.update(extra)
    return value


def page(
    number: int,
    total_pages: int,
    docs: list[dict],
    total_docs: int,
    *,
    next_page: int | None | object = ...,
) -> dict:
    if next_page is ...:
        next_page = number + 1 if number < total_pages else None
    return {
        "status": "success",
        "data": {
            "docs": docs,
            "totalDocs": total_docs,
            "limit": 16,
            "page": number,
            "totalPages": total_pages,
            "nextPage": next_page,
            "prevPage": number - 1 if number > 1 else None,
            "hasPrevPage": number > 1,
            "hasNextPage": next_page is not None,
        },
    }


def collect(
    pages: dict[int, dict],
    *,
    messages: list[str] | None = None,
) -> tuple[list[dict], room_sync.CollectionDiagnostics, list[tuple[int, int]]]:
    calls = []

    def fetch(page_number: int, limit: int) -> dict:
        calls.append((page_number, limit))
        return copy.deepcopy(pages[page_number])

    rooms, diagnostics = room_sync.collect_paginated_rooms(
        fetch,
        FALLBACK_DATE,
        log=messages.append if messages is not None else None,
    )
    return rooms, diagnostics, calls


class TestCompletedRoomPagination(unittest.TestCase):
    def test_one_page_history_stops_at_clean_final_page(self):
        pages = {1: page(1, 1, [room("only-room")], 1)}
        rooms, diagnostics, calls = collect(pages)
        self.assertEqual(calls, [(1, 16)])
        self.assertEqual([item["slug"] for item in rooms], ["only-room"])
        self.assertEqual(diagnostics.page_counts, ((1, 1),))
        self.assertEqual(diagnostics.expected_pages, 1)

    def test_two_page_live_fixture_follows_numbered_next_page(self):
        messages = []
        rooms, diagnostics, calls = collect(live_pages(), messages=messages)
        self.assertEqual(calls, [(1, 16), (2, 16)])
        self.assertEqual(diagnostics.page_counts, ((1, 16), (2, 11)))
        self.assertEqual(diagnostics.expected_pages, 2)
        self.assertEqual(diagnostics.expected_total, 27)
        self.assertEqual(diagnostics.unique_rooms, 27)
        self.assertEqual(
            messages,
            [
                "Completed-room pages detected: 2",
                "Page 1: 16 completed rooms found",
                "Page 2: 11 completed rooms found",
                "Unique completed rooms collected: 27",
            ],
        )

    def test_more_than_two_pages_are_followed_to_true_final_page(self):
        pages = {
            1: page(1, 4, [room("one")], 4),
            2: page(2, 4, [room("two")], 4),
            3: page(3, 4, [room("three")], 4),
            4: page(4, 4, [room("four")], 4),
        }
        rooms, diagnostics, calls = collect(pages)
        self.assertEqual([number for number, _limit in calls], [1, 2, 3, 4])
        self.assertEqual(diagnostics.pages_loaded, 4)
        self.assertEqual(diagnostics.unique_rooms, 4)
        self.assertEqual([item["slug"] for item in rooms], ["one", "two", "three", "four"])

    def test_duplicate_across_pages_is_deduplicated_by_stable_code(self):
        pages = {
            1: page(1, 2, [room("one")], 2),
            2: page(2, 2, [room("one"), room("two")], 2),
        }
        rooms, diagnostics, _calls = collect(pages)
        self.assertEqual([item["slug"] for item in rooms], ["one", "two"])
        self.assertEqual(diagnostics.records_inspected, 3)
        self.assertEqual(diagnostics.unique_rooms, 2)
        self.assertEqual(diagnostics.page_for("one"), 1)

    def test_navigation_loop_or_non_advancing_next_page_is_rejected(self):
        pages = {
            1: page(1, 2, [room("one")], 2, next_page=1),
        }
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "invalid nextPage"
        ):
            collect(pages)

    def test_empty_intermediate_page_is_rejected(self):
        pages = {
            1: page(1, 3, [room("one")], 2),
            2: page(2, 3, [], 2),
            3: page(3, 3, [room("three")], 2),
        }
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "empty before the final page"
        ):
            collect(pages)

    def test_total_count_mismatch_is_rejected(self):
        pages = {
            1: page(1, 2, [room("one")], 3),
            2: page(2, 2, [room("two")], 3),
        }
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "pagination was incomplete"
        ):
            collect(pages)

    def test_page_totals_changing_mid_collection_are_rejected(self):
        pages = live_pages()
        pages[2]["data"]["totalDocs"] = 28
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "changed during collection"
        ):
            collect(pages)

    def test_premature_final_page_is_rejected(self):
        pages = {
            1: page(1, 3, [room("one")], 3, next_page=None),
        }
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "stopped before totalPages"
        ):
            collect(pages)

    def test_wrong_returned_page_is_rejected(self):
        pages = {1: page(2, 2, [room("two")], 1)}
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "different page than requested"
        ):
            collect(pages)

    def test_malformed_or_explicitly_incomplete_records_are_rejected(self):
        malformed = {1: page(1, 1, [{"title": "Missing stable code"}], 1)}
        incomplete = {
            1: page(
                1,
                1,
                [room("suggested-room", userCompleted=False)],
                1,
            )
        }
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "stable room code"
        ):
            collect(malformed)
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "explicitly marked incomplete"
        ):
            collect(incomplete)

    def test_saved_count_rejects_incomplete_snapshot(self):
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "zero completed rooms"
        ):
            room_sync.validate_collection_against_saved([], 16)
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "15 completed rooms"
        ):
            room_sync.validate_collection_against_saved(
                [{"slug": str(index)} for index in range(15)],
                16,
            )

    def test_completion_date_fallback_is_explicit(self):
        rooms, diagnostics, _calls = collect(live_pages())
        malware = next(
            item for item in rooms if item["slug"] == "malwareclassification"
        )
        self.assertEqual(malware["completed"], "2026-07-28")
        self.assertEqual(
            malware["completion_date_source"], "sync-date-fallback"
        )
        self.assertEqual(diagnostics.fallback_dates, 27)


class TestRoomMergeAndRendering(unittest.TestCase):
    def setUp(self):
        pages = live_pages()
        self.saved = {
            "rooms": [
                room_sync._room_from_api(record, dt.date(2026, 7, 23))
                for record in pages[1]["data"]["docs"]
            ]
        }
        self.saved["rooms"][0]["completed"] = "2026-07-23"
        self.saved["rooms"][0]["source"] = "authenticated-browser-sync"
        self.saved["rooms"][0]["custom_note"] = "preserve this metadata"
        self.discovered, self.diagnostics, _calls = collect(pages)

    def test_all_page_two_rooms_are_added_and_existing_data_is_preserved(self):
        original_slugs = {item["slug"] for item in self.saved["rooms"]}
        merged, added = room_sync.merge_rooms(
            copy.deepcopy(self.saved), self.discovered
        )
        expected_added = [
            "introtoresearch",
            "startingoutincybersec",
            "linuxfundamentalspart2",
            "howwebsiteswork",
            "linuxfundamentalspart3",
            "httpindetail",
            "osimodelzi",
            "packetsframes",
            "extendingyournetwork",
            "malwareclassification",
            "theciatriad",
        ]
        self.assertEqual([item["slug"] for item in added], expected_added)
        self.assertEqual(len(merged["rooms"]), 27)
        self.assertTrue(
            original_slugs.issubset({item["slug"] for item in merged["rooms"]})
        )
        first = next(
            item for item in merged["rooms"]
            if item["slug"] == "linuxfundamentalspart1"
        )
        self.assertEqual(first["completed"], "2026-07-23")
        self.assertEqual(first["source"], "authenticated-browser-sync")
        self.assertEqual(first["custom_note"], "preserve this metadata")

    def test_malware_is_discovered_normally_on_page_two(self):
        malware = next(
            item for item in self.discovered
            if item["slug"] == "malwareclassification"
        )
        self.assertEqual(self.diagnostics.page_for("malwareclassification"), 2)
        self.assertEqual(malware["name"], "Malware Classification")
        self.assertEqual(
            malware["url"],
            "https://tryhackme.com/room/malwareclassification",
        )
        self.assertEqual(malware["difficulty"], "Easy")

    def test_repeated_merge_is_idempotent(self):
        merged, added = room_sync.merge_rooms(
            copy.deepcopy(self.saved), self.discovered
        )
        merged_again, added_again = room_sync.merge_rooms(
            merged, self.discovered
        )
        self.assertEqual(len(added), 11)
        self.assertEqual(added_again, [])
        self.assertEqual(len(merged_again["rooms"]), 27)
        self.assertEqual(
            sum(
                item["slug"] == "malwareclassification"
                for item in merged_again["rooms"]
            ),
            1,
        )

    def test_rich_readme_and_training_render_deterministically(self):
        merged, _added = room_sync.merge_rooms(
            copy.deepcopy(self.saved), self.discovered
        )
        profile = {"last_sync": "2026-07-28T15:30:00+00:00"}
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        readme = portfolio.render(
            profile, merged, badges, htb.empty_schema(), cisco.empty_schema()
        )
        training = portfolio.render_training(
            profile, merged, badges, htb.empty_schema(), cisco.empty_schema()
        )

        for section in (
            "## Skills and Evidence",
            "## TryHackMe",
            "### Completed Rooms — Recent First",
            "### Achievement Cabinet",
            "### Room Milestones",
            "## Practical Reports and Lab Evidence",
            "## Other Platforms in Progress",
        ):
            self.assertIn(section, readme)
        self.assertIn("Rooms Completed</strong>&nbsp;<br>27", readme)
        self.assertIn("Easy</strong>&nbsp;<br>17", readme)
        self.assertIn("Info</strong>&nbsp;<br>10", readme)
        self.assertIn("Malware Classification", readme)
        self.assertIn("<strong>25 Rooms</strong><br>Complete", readme)
        self.assertIn("<strong>50 Rooms</strong><br>27 / 50", readme)
        self.assertIn("Malware Classification", training)
        self.assertEqual(
            readme,
            portfolio.render(
                profile,
                merged,
                badges,
                htb.empty_schema(),
                cisco.empty_schema(),
            ),
        )
        self.assertEqual(
            training,
            portfolio.render_training(
                profile,
                merged,
                badges,
                htb.empty_schema(),
                cisco.empty_schema(),
            ),
        )


class TestSafeFailureBoundary(unittest.TestCase):
    def test_collection_failure_does_not_write_timestamp_or_render(self):
        class FakeContext:
            pages = [object()]

            def close(self):
                return None

        fake_context = FakeContext()
        fake_playwright = SimpleNamespace(
            chromium=SimpleNamespace(
                launch_persistent_context=mock.Mock(
                    return_value=fake_context
                )
            )
        )
        fake_manager = mock.MagicMock()
        fake_manager.__enter__.return_value = fake_playwright
        fake_manager.__exit__.return_value = False
        fake_sync_api = ModuleType("playwright.sync_api")
        fake_sync_api.sync_playwright = mock.Mock(return_value=fake_manager)
        fake_playwright_module = ModuleType("playwright")
        fake_playwright_module.sync_api = fake_sync_api

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rooms_path = root / "rooms.json"
            profile_path = root / "profile.json"
            browser_path = root / ".thm-browser"
            original_rooms = {"rooms": [{"slug": "saved-room"}]}
            original_profile = {
                "last_sync": "2026-07-23T11:44:41+00:00"
            }
            rooms_path.write_text(
                json.dumps(original_rooms), encoding="utf-8"
            )
            profile_path.write_text(
                json.dumps(original_profile), encoding="utf-8"
            )

            with mock.patch.object(room_sync, "ROOMS", rooms_path), \
                 mock.patch.object(room_sync, "PROFILE", profile_path), \
                 mock.patch.object(room_sync, "BROWSER_STATE", browser_path), \
                 mock.patch.dict(
                     sys.modules,
                     {
                         "playwright": fake_playwright_module,
                         "playwright.sync_api": fake_sync_api,
                     },
                 ), \
                 mock.patch.object(room_sync, "load_page"), \
                 mock.patch.object(
                     room_sync,
                     "_authenticated_account_summary",
                     return_value=("PreMortem", 27),
                 ), \
                 mock.patch.object(
                     room_sync,
                     "_collect_from_authenticated_page",
                     side_effect=room_sync.RoomCollectionError(
                         "fixture pagination failure"
                     ),
                 ), \
                 mock.patch("builtins.input", return_value=""), \
                 mock.patch.object(room_sync, "write_json") as write_json, \
                 mock.patch.object(
                     room_sync, "regenerate_readme"
                 ) as regenerate:
                with self.assertRaisesRegex(
                    SystemExit, "fixture pagination failure"
                ):
                    room_sync.sync_rooms()

            write_json.assert_not_called()
            regenerate.assert_not_called()
            self.assertEqual(
                json.loads(rooms_path.read_text(encoding="utf-8")),
                original_rooms,
            )
            self.assertEqual(
                json.loads(profile_path.read_text(encoding="utf-8")),
                original_profile,
            )


if __name__ == "__main__":
    unittest.main()
