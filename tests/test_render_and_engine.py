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
from platforms import cisco_netacad as cisco  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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


class TestCiscoRenderer(unittest.TestCase):
    def test_empty_state(self):
        summary = portfolio.build_cisco_summary(cisco.empty_schema())
        detail = portfolio.build_cisco_detailed(cisco.empty_schema())
        self.assertIn("foundation ready", summary)
        self.assertIn("No Cisco Networking Academy achievements", detail)
        self.assertNotIn("<table>", detail)

    def test_unavailable_and_malformed_states(self):
        unavailable = portfolio.build_cisco_detailed(cisco.empty_schema("unavailable"))
        malformed = portfolio.build_cisco_summary(
            json.loads((FIXTURES / "cisco_malformed.json").read_text(encoding="utf-8"))
        )
        self.assertIn("unavailable", unavailable)
        self.assertIn("failed validation", malformed)
        self.assertNotIn("unexpected_identity", malformed)

    def test_populated_fixture(self):
        data = json.loads((FIXTURES / "cisco_valid.json").read_text(encoding="utf-8"))
        summary = portfolio.build_cisco_summary(data)
        detail = portfolio.build_cisco_detailed(data)
        self.assertIn("<strong>Courses</strong>", summary)
        self.assertIn("Fixture Networking Basics", detail)
        self.assertIn("Fixture Network Learner", detail)
        self.assertIn("Fixture Course Certificate", detail)
        self.assertIn("Network fundamentals, Troubleshooting", detail)
        self.assertNotIn("Profile:", summary)

    def test_missing_optional_fields_fixture(self):
        data = json.loads(
            (FIXTURES / "cisco_missing_optional.json").read_text(encoding="utf-8")
        )
        detail = portfolio.build_cisco_detailed(data)
        self.assertIn("Fixture Introductory Course", detail)
        self.assertIn("In Progress", detail)
        self.assertIn("| — | — |", detail)


class TestIdempotentRender(unittest.TestCase):
    def test_render_twice_identical(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        a = portfolio.render(profile, rooms, badges)
        b = portfolio.render(profile, rooms, badges)
        self.assertEqual(a, b)
        self.assertIn(portfolio.GEN_START, a)
        self.assertNotIn(portfolio.START, a)
        self.assertIn("## Training Snapshot", a)
        self.assertIn("## Achievement Cabinet", a)
        self.assertNotIn("Automated Sync Engine", a)

    def test_marker_updates_are_stable_and_preserve_authored_content(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        htb_data = portfolio.read_optional_json(portfolio.HACKTHEBOX, {})
        cisco_data = cisco.empty_schema()
        readme_section = portfolio.render(profile, rooms, badges, htb_data, cisco_data)
        training_section = portfolio.render_training(profile, rooms, badges, htb_data, cisco_data)

        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            training = Path(directory) / "TRAINING.md"
            authored_readme = (
                "# Pre-Mortem — Cybersecurity Portfolio\n\n"
                "I am developing practical cybersecurity skills.\n\n"
                "## About Me\n\nPractical work and safe design.\n\n"
                "## What I Bring\n\nEvidence-backed capabilities.\n\n"
                "## Selected Security Projects\n\n"
                "### PacketPunch\n\nPersonal project narrative.\n\n"
                "### ESP32-S2 AI HID Typer\n\nPersonal project narrative.\n\n"
                "### Cybersecurity Portfolio Automation\n\nPersonal project narrative.\n\n"
                f"{portfolio.GEN_START}\nold generated content\n{portfolio.GEN_END}\n\n"
                "## Current Focus\n\nCurrent development priorities.\n\n"
                "## Contact and Profiles\n\nPre-Mortem only.\n"
            )
            readme.write_text(authored_readme, encoding="utf-8")
            training.write_text(
                "Training-authored introduction.\n\n"
                f"{portfolio.TRAINING_START}\nold generated content\n{portfolio.TRAINING_END}\n\n"
                "Training-authored closing.\n",
                encoding="utf-8",
            )
            with mock.patch.object(portfolio, "README", readme), \
                 mock.patch.object(portfolio, "TRAINING_MD", training):
                portfolio.update_readme(readme_section)
                portfolio.update_training_md(training_section)
                first = (readme.read_text(encoding="utf-8"),
                         training.read_text(encoding="utf-8"))
                portfolio.update_readme(readme_section)
                portfolio.update_training_md(training_section)
                second = (readme.read_text(encoding="utf-8"),
                          training.read_text(encoding="utf-8"))

            self.assertEqual(first, second)
            for personal_section in (
                "I am developing practical cybersecurity skills.",
                "## About Me",
                "## What I Bring",
                "### PacketPunch",
                "### ESP32-S2 AI HID Typer",
                "### Cybersecurity Portfolio Automation",
                "## Current Focus",
                "## Contact and Profiles",
            ):
                self.assertIn(personal_section, first[0])
            for evidence_section in (
                "## Qualifications",
                "## Skills and Evidence",
                "## Training Snapshot",
                "## Recently Completed Rooms",
                "## Achievement Cabinet",
                "## Room Milestones",
                "## Practical Labs and Reports",
                "## Portfolio Statistics",
            ):
                self.assertIn(evidence_section, first[0])
            self.assertTrue(first[1].startswith("Training-authored introduction."))
            self.assertTrue(first[1].endswith("Training-authored closing.\n"))

    def test_empty_platforms_do_not_create_prominent_readme_sections(self):
        rendered = portfolio.render(
            {},
            {"rooms": []},
            {"badges": []},
            htb.empty_schema(),
            cisco.empty_schema(),
        )
        self.assertNotIn("Hack The Box Summary", rendered)
        self.assertNotIn("Hack The Box progress has not", rendered)
        self.assertNotIn("Cisco Networking Academy Summary", rendered)
        self.assertNotIn("Offline integration foundation", rendered)
        self.assertNotIn("Not yet synced", rendered)
        self.assertIn(
            "Hack The Box and Cisco Networking Academy evidence will appear",
            rendered,
        )

    def test_populated_platforms_add_only_concise_snapshot_counts(self):
        cisco_data = json.loads(
            (FIXTURES / "cisco_valid.json").read_text(encoding="utf-8")
        )
        rendered = portfolio.render(
            {},
            {"rooms": []},
            {"badges": []},
            _sample_htb(),
            cisco_data,
        )
        self.assertIn("**Hack The Box:**", rendered)
        self.assertIn("1 machine", rendered)
        self.assertIn("**Cisco Networking Academy:**", rendered)
        self.assertIn("1 course", rendered)
        self.assertNotIn("Fiction Box", rendered)
        self.assertNotIn("Fixture Networking Basics", rendered)

    def test_readme_render_restores_full_public_evidence(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        rendered = portfolio.render(
            profile,
            rooms,
            badges,
            htb.empty_schema(),
            cisco.empty_schema(),
        )

        expected_sections = (
            "## Qualifications",
            "## Skills and Evidence",
            "## Training Snapshot",
            "## Recently Completed Rooms",
            "## Achievement Cabinet",
            "## Room Milestones",
            "## Practical Labs and Reports",
            "### Lab Notes and Drafts",
            "## Portfolio Statistics",
        )
        for section in expected_sections:
            self.assertIn(section, rendered)
        self.assertIn("Rooms Completed</strong>&nbsp;<br>16", rendered)
        self.assertIn("Badges Earned</strong>&nbsp;<br>6", rendered)
        self.assertIn("Easy</strong>&nbsp;<br>15", rendered)
        self.assertIn("Info</strong>&nbsp;<br>1", rendered)
        self.assertIn("16 lab notes and write-up drafts", rendered)
        self.assertNotIn("### Hack The Box Summary", rendered)
        self.assertNotIn("### Cisco Networking Academy Summary", rendered)

    def test_all_badges_render_as_clickable_images(self):
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        rendered = portfolio.build_achievement_cabinet_section(badges)
        self.assertEqual(rendered.count("<img src="), len(badges["badges"]))
        for badge in badges["badges"]:
            self.assertIn(badge["name"], rendered)
            self.assertIn(badge["image"], rendered)
            self.assertIn(portfolio.badge_page_url(badge["code"]), rendered)

    def test_recent_rooms_are_data_driven_linked_and_limited(self):
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        rendered = portfolio.build_recent_rooms_section(rooms)
        table_rows = [line for line in rendered.splitlines() if line.startswith("| [")]
        self.assertEqual(len(table_rows), 10)
        for room in rooms["rooms"][:10]:
            self.assertIn(room["name"], rendered)
            self.assertIn(room["url"], rendered)
        self.assertNotIn(rooms["rooms"][10]["name"], rendered)

    def test_unsafe_room_identity_and_link_are_scrubbed(self):
        rendered = portfolio.build_recent_rooms_section(
            {
                "rooms": [
                    {
                        "name": "/Users/private-user/private.person@example.invalid",
                        "url": "https://example.invalid/private?token=secret",
                        "difficulty": "Easy",
                        "completed": "2026-07-28",
                    }
                ]
            }
        )
        self.assertIn("Sanitised room", rendered)
        self.assertNotIn("/Users/private-user", rendered)
        self.assertNotIn("example.invalid", rendered)
        self.assertNotIn("token=secret", rendered)

        badge_rendered = portfolio.build_achievement_cabinet_section(
            {
                "badges": [
                    {
                        "name": "private.person@example.invalid",
                        "code": "safe-code",
                        "image": "https://example.invalid/badge.png?token=secret",
                    }
                ]
            }
        )
        self.assertIn("<strong>Badge</strong>", badge_rendered)
        self.assertNotIn("private.person", badge_rendered)
        self.assertNotIn("<img src=", badge_rendered)
        self.assertNotIn("token=secret", badge_rendered)

    def test_private_identity_values_are_not_rendered(self):
        private_values = (
            "PRIVATE-LEGAL-NAME",
            "PRIVATE-FIRST-NAME",
            "private.person@example.invalid",
            "/private/home/path",
        )
        htb_data = _sample_htb()
        htb_data["public_identity"] = {
            "username": private_values[0],
            "profile_url": "https://example.invalid/private",
        }
        rendered = portfolio.render(
            {"real_name": private_values[1], "email": private_values[2]},
            {"rooms": [{"name": private_values[3]}]},
            {"badges": []},
            htb_data,
            cisco.empty_schema(),
        )
        for private_value in private_values:
            self.assertNotIn(private_value, rendered)

    def test_repository_readme_starts_with_personal_sections(self):
        readme = portfolio.README.read_text(encoding="utf-8")
        expected_order = (
            "# Pre-Mortem — Cybersecurity Portfolio",
            "## About Me",
            "## What I Bring",
            "## Selected Security Projects",
            portfolio.GEN_START,
            "## Current Focus",
            "## Contact and Profiles",
        )
        positions = [readme.index(section) for section in expected_order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(readme.count(portfolio.GEN_START), 1)
        self.assertEqual(readme.count(portfolio.GEN_END), 1)
        self.assertNotIn("16 room write-up stubs", readme)
        self.assertNotIn("Offline integration foundation ready", readme)
        for evidence_section in (
            "## Qualifications",
            "## Skills and Evidence",
            "## Training Snapshot",
            "## Recently Completed Rooms",
            "## Achievement Cabinet",
            "## Room Milestones",
            "## Practical Labs and Reports",
            "## Portfolio Statistics",
        ):
            self.assertIn(evidence_section, readme)
        self.assertNotRegex(readme, r"/Users/[^/\s]+")
        self.assertNotRegex(
            readme,
            r"(?i)[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}",
        )

    def test_training_document_retains_detailed_evidence(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        cisco_data = json.loads(
            (FIXTURES / "cisco_valid.json").read_text(encoding="utf-8")
        )
        rendered = portfolio.render_training(
            profile, rooms, badges, _sample_htb(), cisco_data
        )
        self.assertIn("### Completed Rooms", rendered)
        self.assertIn("Linux Fundamentals Part 1", rendered)
        self.assertIn("### Achievement Cabinet", rendered)
        self.assertIn("Fiction Box", rendered)
        self.assertIn("Fixture Networking Basics", rendered)


class TestInteractiveMenu(unittest.TestCase):
    def test_exit_option(self):
        with mock.patch("builtins.input", return_value="6"):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_invalid_then_exit(self):
        with mock.patch("builtins.input", side_effect=["9", "abc", "6"]):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_keyboard_interrupt_clean(self):
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            self.assertEqual(portfolio.interactive_menu(), 0)

    def test_selection_dispatches(self):
        with mock.patch("builtins.input", return_value="4"), \
             mock.patch.object(portfolio, "run_sync", return_value=0) as run:
            portfolio.interactive_menu()
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ["tryhackme", "hackthebox", "cisco"])

    def test_regenerate_option(self):
        with mock.patch("builtins.input", side_effect=["5", "n"]), \
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
        self.assertEqual(call.args[0], ["tryhackme", "hackthebox", "cisco"])

    def test_platform_single(self):
        self.assertEqual(self._run("hackthebox").args[0], ["hackthebox"])
        self.assertEqual(self._run("cisco").args[0], ["cisco"])


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

    def test_partial_cisco_failure_is_isolated(self):
        ok = portfolio.PlatformOutcome("TryHackMe", True, "ok", {"rooms": 16})
        bad = portfolio.PlatformOutcome("Cisco Networking Academy", False, "not implemented")
        with mock.patch.object(portfolio, "sync_tryhackme_platform", return_value=ok), \
             mock.patch.object(portfolio, "sync_cisco_platform", return_value=bad), \
             mock.patch.object(portfolio, "regenerate_readme"), \
             mock.patch.object(portfolio, "run_git", return_value=SimpleNamespace(stdout="")):
            rc = portfolio.run_sync(["tryhackme", "cisco"], interactive=False, auto_push=False)
        self.assertEqual(rc, 0)

    def test_platform_failure_does_not_erase_personal_readme(self):
        bad = portfolio.PlatformOutcome(
            "Cisco Networking Academy", False, "not implemented"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "README": root / "README.md",
                "TRAINING_MD": root / "TRAINING.md",
                "PROFILE": root / "profile.json",
                "ROOMS": root / "rooms.json",
                "BADGES": root / "badges.json",
                "HACKTHEBOX": root / "hackthebox.json",
                "CISCO_NETACAD": root / "cisco_netacad.json",
            }
            paths["README"].write_text(
                portfolio.README.read_text(encoding="utf-8"), encoding="utf-8"
            )
            paths["TRAINING_MD"].write_text(
                portfolio.TRAINING_MD.read_text(encoding="utf-8"), encoding="utf-8"
            )
            paths["PROFILE"].write_text("{}", encoding="utf-8")
            paths["ROOMS"].write_text('{"rooms": []}', encoding="utf-8")
            paths["BADGES"].write_text('{"badges": []}', encoding="utf-8")
            paths["HACKTHEBOX"].write_text(
                json.dumps(htb.empty_schema()), encoding="utf-8"
            )
            paths["CISCO_NETACAD"].write_text(
                json.dumps(cisco.empty_schema()), encoding="utf-8"
            )

            with mock.patch.multiple(portfolio, **paths), \
                 mock.patch.object(portfolio, "sync_cisco_platform", return_value=bad), \
                 mock.patch.object(
                     portfolio, "run_git",
                     return_value=SimpleNamespace(stdout="", returncode=0),
                 ):
                rc = portfolio.run_sync(
                    ["cisco"], interactive=False, auto_push=False
                )

            rewritten = paths["README"].read_text(encoding="utf-8")
            self.assertEqual(rc, 1)
            for personal_section in (
                "## About Me",
                "## What I Bring",
                "## Selected Security Projects",
                "## Current Focus",
                "## Contact and Profiles",
            ):
                self.assertIn(personal_section, rewritten)
            for evidence_section in (
                "## Qualifications",
                "## Skills and Evidence",
                "## Training Snapshot",
                "## Practical Labs and Reports",
                "## Portfolio Statistics",
            ):
                self.assertIn(evidence_section, rewritten)


class TestPublishSafety(unittest.TestCase):
    def test_allowlist_constant(self):
        self.assertEqual(portfolio.PUBLISH_ALLOWLIST, ("README.md", "TRAINING.md", "docs", "data", "writeups"))

    def test_private_artefact_rejected(self):
        with mock.patch.object(portfolio, "_git_paths_staged",
                               return_value=[".htb-browser/Default/Cookies",
                                             ".cisco-browser/Default/Cookies", "README.md"]):
            problems = portfolio._privacy_and_safety_checks()
        self.assertTrue(any(".htb-browser" in p for p in problems))
        self.assertTrue(any(".cisco-browser" in p for p in problems))

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
