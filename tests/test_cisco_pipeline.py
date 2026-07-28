"""Deterministic Cisco NetAcad foundation tests (no browser or network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from platforms import cisco_netacad as cisco  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class TestCiscoSchema(unittest.TestCase):
    def test_valid_fixture(self):
        data = fixture("cisco_valid.json")
        self.assertEqual(cisco.validate_data(data), [])
        self.assertEqual(cisco.dataset_counts(data), {
            "courses": 1, "badges": 1, "certificates": 1,
        })

    def test_missing_optional_fields_fixture(self):
        data = fixture("cisco_missing_optional.json")
        self.assertEqual(cisco.validate_data(data), [])
        course = data["courses"][0]
        self.assertNotIn("completed_at", course)
        self.assertNotIn("skills", course)

    def test_malformed_fixture_rejected(self):
        errors = cisco.validate_data(fixture("cisco_malformed.json"))
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("unsupported root fields" in error for error in errors))
        self.assertTrue(any("courses must be a list" in error for error in errors))

    def test_dates_and_timestamps_are_strict(self):
        data = fixture("cisco_valid.json")
        data["synced_at"] = "2026-07-01 12:00:00"
        data["courses"][0]["completed_at"] = "2026-06-30T12:00:00Z"
        errors = cisco.validate_data(data)
        self.assertTrue(any("synced_at" in error for error in errors))
        self.assertTrue(any("completed_at" in error for error in errors))

    def test_empty_states_are_valid(self):
        self.assertEqual(cisco.validate_data(cisco.empty_schema()), [])
        self.assertEqual(cisco.validate_data(cisco.empty_schema("unavailable")), [])


class TestCiscoSanitisation(unittest.TestCase):
    def test_identity_leakage_attempts_are_scrubbed(self):
        raw = fixture("cisco_identity_leakage.json")
        data = cisco.build_dataset(raw, synced_at="2026-07-01T12:00:00+00:00")
        serialised = json.dumps(data).casefold()

        self.assertEqual(cisco.validate_data(data), [])
        self.assertEqual([course["title"] for course in data["courses"]], ["Fixture Safe Course"])
        self.assertEqual(data["courses"][0]["skills"], ["Networking"])
        self.assertEqual([cert["title"] for cert in data["certificates"]],
                         ["Fixture Safe Certificate"])
        self.assertEqual(data["badges"], [])
        for forbidden in (
            "redact-me", "learner@example.invalid", "account-fixture-123",
            "token-fixture-456", "certificate-fixture-789", "private_url",
            "certificate_id", "session_token", "full_name", "email",
        ):
            self.assertNotIn(forbidden, serialised)

    def test_unknown_fields_are_discarded(self):
        data = cisco.build_dataset({
            "courses": [{
                "title": "Fixture Course",
                "status": "completed",
                "secret": "discarded",
                "account": {"id": "discarded"},
            }],
        })
        self.assertEqual(set(data["courses"][0]), {"title", "status"})

    def test_malformed_records_are_dropped(self):
        data = cisco.build_dataset({
            "courses": [None, "bad", {"status": "completed"}, {"title": "No status"}],
            "badges": [{"earned_at": "2026-01-01"}],
            "certificates": [{"title": "javascript:alert(1)"}],
        })
        self.assertTrue(cisco.is_empty(data))
        self.assertEqual(data["collection_status"], "not_collected")


class TestCiscoPersistence(unittest.TestCase):
    def test_atomic_write_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cisco.json"
            data = fixture("cisco_valid.json")
            ok, errors = cisco.write_data(data, target)
            self.assertTrue(ok, errors)
            self.assertEqual(cisco.load_data(target), data)
            self.assertEqual([path.name for path in Path(directory).iterdir()], ["cisco.json"])

    def test_invalid_write_preserves_previous_data(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cisco.json"
            previous = fixture("cisco_valid.json")
            cisco.write_data(previous, target)
            ok, errors = cisco.write_data(fixture("cisco_malformed.json"), target)
            self.assertFalse(ok)
            self.assertTrue(errors)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), previous)

    def test_live_sync_is_explicitly_unimplemented_and_preserves_data(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "cisco.json"
            previous = fixture("cisco_valid.json")
            cisco.write_data(previous, target)
            result = cisco.sync(interactive=False, data_path=target)
            self.assertFalse(result.ok)
            self.assertIn("not implemented", result.message)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), previous)

    def test_cisco_failure_does_not_touch_other_platform_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cisco_target = root / "cisco_netacad.json"
            rooms_target = root / "rooms.json"
            htb_target = root / "hackthebox.json"
            rooms_target.write_text('{"rooms":[{"name":"Keep THM"}]}', encoding="utf-8")
            htb_target.write_text('{"labs":{"machines":[{"name":"Keep HTB"}]}}', encoding="utf-8")
            before = (rooms_target.read_bytes(), htb_target.read_bytes())

            result = cisco.sync(interactive=False, data_path=cisco_target)

            self.assertFalse(result.ok)
            self.assertEqual((rooms_target.read_bytes(), htb_target.read_bytes()), before)
            self.assertFalse(cisco_target.exists())


if __name__ == "__main__":
    unittest.main()
