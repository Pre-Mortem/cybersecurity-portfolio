"""Deterministic tests for the Hack The Box data pipeline (no browser)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from platforms import base, hackthebox as htb  # noqa: E402


class TestNormalisation(unittest.TestCase):
    def test_machine_valid_and_status_from_boolean(self):
        rec = htb.normalise_machine({
            "name": "  Example Box ", "difficulty": "easy", "os": "Linux",
            "isRetired": True, "user_own": True, "root_own": "false",
            "owned_at": "2026-07-23T10:00:00Z",
        })
        self.assertEqual(rec["name"], "Example Box")
        self.assertEqual(rec["difficulty"], "Easy")
        self.assertEqual(rec["operating_system"], "Linux")
        self.assertEqual(rec["status"], "retired")
        self.assertTrue(rec["user_own"])
        self.assertNotIn("root_own", rec)  # falsey compacted away
        self.assertEqual(rec["completed_at"], "2026-07-23")

    def test_machine_requires_name(self):
        self.assertIsNone(htb.normalise_machine({"difficulty": "Easy"}))
        self.assertIsNone(htb.normalise_machine("not a dict"))

    def test_unknown_difficulty_preserved_as_text(self):
        rec = htb.normalise_challenge({"name": "X", "difficulty": "Brutal"})
        self.assertEqual(rec["difficulty"], "Brutal")

    def test_missing_optional_fields(self):
        rec = htb.normalise_module({"name": "Intro to Whatever"})
        self.assertEqual(rec["name"], "Intro to Whatever")
        self.assertEqual(rec["status"], "completed")
        self.assertNotIn("completed_at", rec)
        self.assertNotIn("tier", rec)

    def test_malformed_date_dropped(self):
        rec = htb.normalise_sherlock({"name": "S1", "date": "not-a-date"})
        self.assertNotIn("completed_at", rec)


class TestBuildDataset(unittest.TestCase):
    def test_dedup_and_sort(self):
        raw = {"machines": [
            {"name": "Zeta", "difficulty": "Hard"},
            {"name": "alpha", "difficulty": "Easy"},
            {"name": "Zeta", "difficulty": "Hard"},  # duplicate
        ]}
        data = htb.build_dataset({"username": "ExampleUser"}, raw, synced_at="2026-07-23T00:00:00+00:00")
        names = [m["name"] for m in data["labs"]["machines"]]
        self.assertEqual(names, ["alpha", "Zeta"])  # sorted, deduped

    def test_identity_sanitised(self):
        data = htb.build_dataset(
            {"username": "ExampleUser", "profile_url": "javascript:alert(1)"}, {})
        self.assertEqual(data["public_identity"]["username"], "ExampleUser")
        self.assertEqual(data["public_identity"]["profile_url"], "")  # unsafe rejected

    def test_safe_url_kept(self):
        data = htb.build_dataset(
            {"username": "ExampleUser", "profile_url": "https://app.hackthebox.com/users/1"}, {})
        self.assertEqual(data["public_identity"]["profile_url"], "https://app.hackthebox.com/users/1")

    def test_unsupported_fields_discarded(self):
        raw = {"machines": [{"name": "Box", "secret_token": "abc", "email": "x@y.z"}]}
        data = htb.build_dataset({}, raw)
        self.assertNotIn("secret_token", data["labs"]["machines"][0])
        self.assertNotIn("email", data["labs"]["machines"][0])

    def test_idempotent_snapshot_ignores_timestamp(self):
        raw = {"challenges": [{"name": "C1", "category": "Web"}]}
        a = htb.build_dataset({}, raw, synced_at="2026-01-01T00:00:00+00:00")
        b = htb.build_dataset({}, raw, synced_at="2026-12-31T23:59:59+00:00")
        self.assertEqual(htb.dataset_snapshot(a), htb.dataset_snapshot(b))


class TestValidation(unittest.TestCase):
    def test_empty_schema_is_valid(self):
        self.assertEqual(htb.validate_data(htb.empty_schema()), [])

    def test_missing_name_flagged(self):
        data = htb.empty_schema()
        data["labs"]["machines"].append({"difficulty": "Easy"})
        errors = htb.validate_data(data)
        self.assertTrue(any("missing name" in e for e in errors))

    def test_unsafe_url_flagged(self):
        data = htb.empty_schema()
        data["public_identity"]["profile_url"] = "ftp://x"
        self.assertTrue(any("profile_url" in e for e in htb.validate_data(data)))

    def test_wrong_types_flagged(self):
        self.assertTrue(htb.validate_data("nope"))
        data = htb.empty_schema()
        data["labs"] = []
        self.assertTrue(any("labs" in e for e in htb.validate_data(data)))


class TestPersistence(unittest.TestCase):
    def test_atomic_write_and_no_temp_left(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        target = d / "htb.json"
        ok, errors = htb.write_data(htb.build_dataset({"username": "ExampleUser"}, {}), target)
        self.assertTrue(ok, errors)
        self.assertTrue(target.exists())
        leftovers = [p for p in d.iterdir() if p.name != "htb.json"]
        self.assertEqual(leftovers, [])
        json.loads(target.read_text())  # valid JSON

    def test_invalid_data_not_written(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        target = d / "htb.json"
        target.write_text(json.dumps(htb.empty_schema()))
        bad = htb.empty_schema()
        bad["schema_version"] = 999
        ok, errors = htb.write_data(bad, target)
        self.assertFalse(ok)
        self.assertTrue(errors)
        # Original preserved.
        self.assertEqual(json.loads(target.read_text())["schema_version"], 1)

    def test_is_empty(self):
        self.assertTrue(htb.is_empty(htb.empty_schema()))
        d = htb.build_dataset({"username": "ExampleUser"}, {})
        self.assertFalse(htb.is_empty(d))


class TestSyncPreservesOnFailure(unittest.TestCase):
    def test_failed_collection_preserves_previous(self):
        import tempfile
        from unittest import mock
        d = Path(tempfile.mkdtemp())
        target = d / "htb.json"
        previous = htb.build_dataset(
            {"username": "ExampleUser"},
            {"machines": [{"name": "KeepMe", "difficulty": "Easy"}]},
        )
        htb.write_data(previous, target)

        with mock.patch.object(htb, "collect_from_browser", side_effect=RuntimeError("boom")):
            result = htb.sync(interactive=False, data_path=target)
        self.assertFalse(result.ok)
        # Previous data untouched.
        kept = json.loads(target.read_text())
        self.assertEqual(kept["labs"]["machines"][0]["name"], "KeepMe")

    def test_empty_result_does_not_erase_previous(self):
        import tempfile
        from unittest import mock
        d = Path(tempfile.mkdtemp())
        target = d / "htb.json"
        previous = htb.build_dataset(
            {"username": "ExampleUser"},
            {"machines": [{"name": "KeepMe", "difficulty": "Easy"}]},
        )
        htb.write_data(previous, target)

        with mock.patch.object(htb, "collect_from_browser", return_value=({}, {})):
            result = htb.sync(interactive=False, data_path=target)
        self.assertFalse(result.ok)
        kept = json.loads(target.read_text())
        self.assertEqual(kept["labs"]["machines"][0]["name"], "KeepMe")


if __name__ == "__main__":
    unittest.main()
