"""Deterministic tests for the renderer and the sync engine (no browser/git)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import portfolio  # noqa: E402
from platforms import hackthebox as htb  # noqa: E402


def _sample_htb():
    return htb.build_dataset(
        {"username": "ExampleUser", "profile_url": "https://app.hackthebox.com/users/999"},
        {
            "machines": [{"name": "Fiction Box", "difficulty": "Easy", "os": "Linux",
                          "status": "retired", "completed_at": "2026-07-01"}],
            "challenges": [{"name": "Fake Crypto", "category": "Crypto", "difficulty": "Medium"}],
            "modules": [{"name": "Made-up Module", "tier": "Tier 0"}],
            "certifications": [{"name": "Fictional Certified Tester", "issued_at": "2026-06-01"}],
            "achievements": [{"name": "Imaginary Milestone"}],
        },
    )


class TestHtbRenderer(unittest.TestCase):
    def _render_with(self, data):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "htb.json"
            path.write_text(json.dumps(data))
            with mock.patch.object(portfolio, "HACKTHEBOX", path):
                return portfolio.build_hackthebox_section()

    def test_empty_state(self):
        out = self._render_with(htb.empty_schema())
        self.assertIn("Hack The Box progress has not been added yet", out)
        self.assertNotIn("<table>", out)

    def test_populated(self):
        out = self._render_with(_sample_htb())
        self.assertIn("ExampleUser", out)
        self.assertIn("Fiction Box", out)
        self.assertIn("Recently Completed Machines", out)
        self.assertIn("Fictional Certified Tester", out)
        self.assertIn("Achievement metadata only", out)
        # No empty tables for categories without data.
        self.assertNotIn("### Sherlocks", out)

    def test_html_escaping(self):
        data = htb.empty_schema()
        data["public_identity"]["username"] = "Ex<script>Alert"
        data["labs"]["machines"].append({"name": "Evil <b> & \"x\"", "difficulty": "Easy"})
        out = self._render_with(data)
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;", out)


class TestIdempotentRender(unittest.TestCase):
    def test_render_twice_identical(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        a = portfolio.render(profile, rooms, badges)
        b = portfolio.render(profile, rooms, badges)
        self.assertEqual(a, b)
        self.assertIn(portfolio.GEN_START, a)
        self.assertIn(portfolio.START, a)  # THM markers nested inside


class TestInteractiveMenu(unittest.TestCase):
    def test_exit_option(self):
        with mock.patch("builtins.input", return_value="5"):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_invalid_then_exit(self):
        with mock.patch("builtins.input", side_effect=["9", "abc", "5"]):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_keyboard_interrupt_clean(self):
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_selection_dispatches(self):
        with mock.patch("builtins.input", return_value="3"), \
             mock.patch.object(portfolio, "run_sync", return_value=0) as run:
            portfolio.interactive_menu()
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ["tryhackme", "hackthebox"])

    def test_regenerate_option(self):
        with mock.patch("builtins.input", side_effect=["4", "n"]), \
             mock.patch.object(portfolio, "regenerate_readme") as regen:
            self.assertEqual(portfolio.interactive_menu(), 0)
            regen.assert_called_once()


class TestNonInteractiveCli(unittest.TestCase):
    def _run(self, requested_platform):
        args = SimpleNamespace(platform=requested_platform, non_interactive=True, push=False)
        with mock.patch.object(portfolio, "run_sync", return_value=0) as run:
            portfolio.cmd_sync(args)
            return run.call_args

    def test_platform_all(self):
        call = self._run("all")
        self.assertEqual(call.args[0], ["tryhackme", "hackthebox"])

    def test_platform_single(self):
        self.assertEqual(self._run("hackthebox").args[0], ["hackthebox"])


class TestRunSyncOutcomes(unittest.TestCase):
    def _patch_common(self):
        return mock.patch.multiple(
            portfolio,
            regenerate_readme=mock.DEFAULT,
            run_git=mock.DEFAULT,
        )

    def test_partial_success_returns_zero(self):
        ok = portfolio.PlatformOutcome("TryHackMe", True, "ok", {"rooms": 16})
        bad = portfolio.PlatformOutcome("Hack The Box", False, "fail")
        with mock.patch.object(portfolio, "sync_tryhackme_platform", return_value=ok), \
             mock.patch.object(portfolio, "sync_hackthebox_platform", return_value=bad), \
             mock.patch.object(portfolio, "regenerate_readme"), \
             mock.patch.object(portfolio, "run_git", return_value=SimpleNamespace(stdout="")):
            rc = portfolio.run_sync(["tryhackme", "hackthebox"], interactive=False, auto_push=False)
        self.assertEqual(rc, 0)

    def test_complete_failure_returns_one(self):
        bad = portfolio.PlatformOutcome("Hack The Box", False, "fail")
        with mock.patch.object(portfolio, "sync_hackthebox_platform", return_value=bad), \
             mock.patch.object(portfolio, "regenerate_readme"), \
             mock.patch.object(portfolio, "run_git", return_value=SimpleNamespace(stdout="")):
            rc = portfolio.run_sync(["hackthebox"], interactive=False, auto_push=False)
        self.assertEqual(rc, 1)


class TestPublishSafety(unittest.TestCase):
    def test_allowlist_constant(self):
        self.assertEqual(portfolio.PUBLISH_ALLOWLIST, ("README.md", "data", "writeups"))

    def test_private_artefact_rejected(self):
        with mock.patch.object(portfolio, "_git_paths_staged",
                               return_value=[".htb-browser/Default/Cookies", "README.md"]):
            problems = portfolio._privacy_and_safety_checks()
        self.assertTrue(any(".htb-browser" in p for p in problems))

    def test_diagnostics_and_tmp_rejected(self):
        with mock.patch.object(portfolio, "_git_paths_staged",
                               return_value=[".htb-diagnostics/x.png", "scratch.tmp"]):
            problems = portfolio._privacy_and_safety_checks()
        self.assertEqual(len(problems), 2)

    def test_forbidden_pattern_in_data_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "data"
            bad.mkdir()
            (bad / "hackthebox.json").write_text('{"token": "bearer abc.def"}')
            with mock.patch.object(portfolio, "ROOT", Path(d)), \
                 mock.patch.object(portfolio, "_git_paths_staged", return_value=["data/hackthebox.json"]):
                problems = portfolio._privacy_and_safety_checks()
        self.assertTrue(any("forbidden pattern" in p for p in problems))

    def test_clean_data_passes(self):
        with mock.patch.object(portfolio, "_git_paths_staged", return_value=["README.md", "data/rooms.json"]):
            # data/rooms.json exists and is clean in the real repo.
            problems = portfolio._privacy_and_safety_checks()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
