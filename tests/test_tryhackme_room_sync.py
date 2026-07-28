"""Deterministic TryHackMe completed-room collection tests (no live login)."""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import portfolio  # noqa: E402
import room_sync  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def completed_pages():
    return {
        1: fixture("thm_completed_rooms_page1.json"),
        2: fixture("thm_completed_rooms_page2.json"),
    }


class TestCompletedRoomCollection(unittest.TestCase):
    def collect(self, pages=None):
        pages = pages or completed_pages()
        calls = []

        def fetch(page_number, limit):
            calls.append((page_number, limit))
            return pages[page_number]

        rooms, diagnostics = room_sync.collect_paginated_rooms(
            fetch, dt.date(2026, 7, 28)
        )
        return rooms, diagnostics, calls

    def test_new_completed_room_is_discovered_with_canonical_metadata(self):
        rooms, diagnostics, calls = self.collect()
        self.assertEqual(calls, [(1, 16), (2, 16)])
        self.assertEqual(len(rooms), 17)
        self.assertEqual(diagnostics.expected_total, 17)
        self.assertEqual(diagnostics.unique_rooms, 17)

        malware = next(
            room for room in rooms if room["slug"] == "malwareclassification"
        )
        self.assertEqual(malware["name"], "Malware Classification")
        self.assertEqual(
            malware["url"],
            "https://tryhackme.com/room/malwareclassification",
        )
        self.assertEqual(malware["difficulty"], "Easy")
        self.assertEqual(malware["completed"], "2026-07-28")
        self.assertEqual(malware["completion_date_source"], "tryhackme")

    def test_repeated_records_across_pages_are_deduplicated(self):
        pages = completed_pages()
        duplicate = copy.deepcopy(pages[1]["data"]["docs"][0])
        pages[1]["data"]["docs"].append(duplicate)
        rooms, diagnostics, _calls = self.collect(pages)
        self.assertEqual(len(rooms), 17)
        self.assertEqual(diagnostics.records_inspected, 18)
        self.assertEqual(
            sum(room["slug"] == "linuxfundamentalspart1" for room in rooms),
            1,
        )

    def test_unrelated_or_malformed_links_are_not_collected(self):
        pages = completed_pages()
        pages[1]["data"]["docs"].append(
            {
                "title": "Featured Room",
                "url": "https://tryhackme.com/room/featured-not-completed",
                "difficulty": "hard",
            }
        )
        rooms, diagnostics, _calls = self.collect(pages)
        self.assertEqual(len(rooms), 17)
        self.assertEqual(diagnostics.records_inspected, 18)
        self.assertNotIn(
            "featured-not-completed", {room["slug"] for room in rooms}
        )

    def test_missing_lazy_loaded_page_is_a_collection_failure(self):
        pages = completed_pages()
        pages[2]["data"]["docs"] = []
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "pagination was incomplete"
        ):
            self.collect(pages)

    def test_zero_and_partial_results_are_rejected(self):
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "zero completed rooms"
        ):
            room_sync.validate_collection_against_saved([], 16)
        with self.assertRaisesRegex(
            room_sync.RoomCollectionError, "15 completed rooms"
        ):
            room_sync.validate_collection_against_saved(
                [{"slug": str(index)} for index in range(15)], 16
            )

    def test_current_live_fixture_records_target_as_incomplete(self):
        live = fixture("thm_malware_classification_incomplete.json")
        self.assertEqual(live["data"]["code"], "malwareclassification")
        self.assertEqual(live["data"]["type"], "walkthrough")
        self.assertEqual(live["data"]["difficulty"], "easy")
        self.assertFalse(live["data"]["userCompleted"])
        self.assertEqual(live["data"]["progressPercentage"], 92)

    def test_relative_and_fallback_completion_dates_are_labelled(self):
        yesterday, source = room_sync._completion_date(
            "yesterday", dt.date(2026, 7, 28)
        )
        fallback, fallback_source = room_sync._completion_date(
            None, dt.date(2026, 7, 28)
        )
        self.assertEqual((yesterday, source), ("2026-07-27", "tryhackme-relative"))
        self.assertEqual(
            (fallback, fallback_source),
            ("2026-07-28", "sync-date-fallback"),
        )


class TestRoomPersistenceAndRendering(unittest.TestCase):
    def setUp(self):
        pages = completed_pages()
        self.saved = {
            "rooms": [
                room_sync._room_from_api(record, dt.date(2026, 7, 23))
                for record in pages[1]["data"]["docs"]
            ]
        }
        self.discovered, _diagnostics = room_sync.collect_paginated_rooms(
            lambda page, _limit: pages[page],
            dt.date(2026, 7, 28),
        )

    def test_new_room_persists_once_and_all_saved_rooms_remain(self):
        prior_slugs = {room["slug"] for room in self.saved["rooms"]}
        merged, added = room_sync.merge_rooms(
            copy.deepcopy(self.saved), self.discovered
        )
        self.assertEqual(len(merged["rooms"]), 17)
        self.assertEqual(
            [room["slug"] for room in added], ["malwareclassification"]
        )
        self.assertTrue(
            prior_slugs.issubset({room["slug"] for room in merged["rooms"]})
        )

        merged_again, added_again = room_sync.merge_rooms(
            merged, self.discovered
        )
        self.assertEqual(len(merged_again["rooms"]), 17)
        self.assertEqual(added_again, [])
        self.assertEqual(
            sum(
                room["slug"] == "malwareclassification"
                for room in merged_again["rooms"]
            ),
            1,
        )

    def test_partial_snapshot_cannot_delete_saved_rooms(self):
        partial = self.discovered[:5]
        with self.assertRaises(room_sync.RoomCollectionError):
            room_sync.validate_collection_against_saved(
                partial, len(self.saved["rooms"])
            )
        self.assertEqual(len(self.saved["rooms"]), 16)

    def test_rendering_updates_count_recent_table_milestone_and_difficulties(self):
        merged, _added = room_sync.merge_rooms(
            copy.deepcopy(self.saved), self.discovered
        )
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        profile = portfolio.read_json(portfolio.PROFILE, {})

        summary = portfolio.build_tryhackme_summary(profile, merged, badges)
        detail = portfolio.build_tryhackme_detailed(profile, merged, badges)
        milestones = portfolio.build_milestones(len(merged["rooms"]))
        root_render = portfolio.render(profile, merged, badges)

        self.assertIn("Rooms Completed</strong>&nbsp;<br>17", summary)
        self.assertIn("Easy</strong>&nbsp;<br>12", summary)
        self.assertIn("Info</strong>&nbsp;<br>5", summary)
        self.assertIn("#### Recent Completed Rooms", summary)
        self.assertIn("Malware Classification", summary)
        self.assertIn("17 / 25", milestones)
        self.assertIn("Malware Classification", detail)
        self.assertIn("### Recent Completed Rooms", root_render)
        self.assertIn("Malware Classification", root_render)
        self.assertEqual(
            root_render,
            portfolio.render(profile, merged, badges),
        )

    def test_collection_failure_does_not_write_or_update_last_sync(self):
        class FakeContext:
            pages = [object()]

            def close(self):
                return None

        fake_context = FakeContext()
        fake_playwright = SimpleNamespace(
            chromium=SimpleNamespace(
                launch_persistent_context=mock.Mock(return_value=fake_context)
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
            rooms_path = Path(directory) / "rooms.json"
            profile_path = Path(directory) / "profile.json"
            rooms_path.write_text(json.dumps(self.saved), encoding="utf-8")
            original_profile = {"last_sync": "2026-07-23T11:44:41+00:00"}
            profile_path.write_text(json.dumps(original_profile), encoding="utf-8")

            with mock.patch.object(room_sync, "ROOMS", rooms_path), \
                 mock.patch.object(room_sync, "PROFILE", profile_path), \
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
                     return_value=("PreMortem", 17),
                 ), \
                 mock.patch.object(
                     room_sync,
                     "_collect_from_authenticated_page",
                     side_effect=room_sync.RoomCollectionError("fixture failure"),
                 ), \
                 mock.patch("builtins.input", return_value=""), \
                 mock.patch.object(room_sync, "write_json") as write_json, \
                 mock.patch.object(room_sync, "regenerate_readme") as regenerate:
                with self.assertRaisesRegex(SystemExit, "fixture failure"):
                    room_sync.sync_rooms()

            write_json.assert_not_called()
            regenerate.assert_not_called()
            self.assertEqual(
                json.loads(profile_path.read_text(encoding="utf-8")),
                original_profile,
            )


if __name__ == "__main__":
    unittest.main()
