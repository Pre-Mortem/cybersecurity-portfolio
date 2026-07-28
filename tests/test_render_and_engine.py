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


class TestPublicProfileRenderer(unittest.TestCase):
    def setUp(self):
        self.profile = portfolio.read_json(portfolio.PROFILE, {})

    def test_all_qualifications_render_as_a_safe_markdown_table(self):
        rendered = portfolio.build_qualifications_table(self.profile)
        self.assertIn(
            "| Qualification | Awarding body / provider | Level | Status | Awarded |",
            rendered,
        )
        self.assertEqual(
            len(
                [
                    line
                    for line in rendered.splitlines()
                    if line.startswith("| ") and not line.startswith("|---")
                ]
            ),
            4,
        )
        self.assertIn(
            "NCFE Level 2 Certificate in Understanding Coding", rendered
        )
        self.assertIn(
            "NCFE Level 2 Certificate in the Principles of Cyber Security",
            rendered,
        )
        self.assertIn("6 August 2025", rendered)
        self.assertIn("29 May 2025", rendered)
        self.assertEqual(rendered.count("| Completed |"), 2)
        self.assertIn(
            "| Certificate in Cyber Security Practices | Think Employment "
            "| 3 | In progress | — |",
            rendered,
        )

    def test_missing_award_date_renders_as_em_dash(self):
        profile = {
            "qualifications": [
                {
                    "title": "Fixture Qualification",
                    "awarding_body_or_provider": "Fixture Provider",
                    "level": "2",
                    "status": "completed",
                }
            ]
        }
        self.assertIn(
            "| Fixture Qualification | Fixture Provider | 2 | Completed | — |",
            portfolio.build_qualifications_table(profile),
        )

    def test_identifier_fields_are_rejected_and_never_rendered(self):
        private_values = (
            "PRIVATE-LEARNER-ID",
            "PRIVATE-CERTIFICATE-ID",
            "PRIVATE-CENTRE-ID",
        )
        profile = {
            "qualifications": [
                {
                    "title": "Safe Qualification",
                    "awarding_body_or_provider": "Safe Provider",
                    "level": "2",
                    "status": "completed",
                    "awarded": "2025-01-01",
                    "learner_number": private_values[0],
                    "certificate_number": private_values[1],
                    "centre_number": private_values[2],
                    "certificate_image": "private-certificate.jpg",
                }
            ]
        }
        errors = portfolio.validate_profile_data(profile)
        self.assertTrue(any("unknown fields" in error for error in errors))
        rendered = portfolio.build_qualifications_table(profile)
        for value in private_values:
            self.assertNotIn(value, rendered)
        self.assertNotIn("private-certificate.jpg", rendered)

    def test_selected_projects_include_existing_and_new_rows(self):
        rendered = portfolio.build_selected_projects_table(self.profile)
        for project in (
            "PacketPunch",
            "ESP32-S2 AI HID Typer",
            "Cybersecurity Portfolio Automation",
            "HackPod",
            "X-Link",
        ):
            self.assertIn(project, rendered)
        self.assertIn("33% — 2 of 6 top-level roadmap stages complete", rendered)
        self.assertIn("21% — 3 of 14 roadmap milestones complete", rendered)
        self.assertIn("lwIP NAPT", rendered)
        self.assertIn("Insignia compatibility work", rendered)

    def test_private_project_urls_are_not_rendered(self):
        profile = {
            "projects": [
                {
                    "name": "Private Fixture",
                    "status": "in_development",
                    "visibility": "private",
                    "public_url": "https://example.invalid/private-repository",
                    "summary": "Safe summary",
                    "progress_label": "Not quantified",
                }
            ]
        }
        rendered = portfolio.build_selected_projects_table(profile)
        self.assertIn("Private Fixture", rendered)
        self.assertNotIn("example.invalid", rendered)
        self.assertTrue(portfolio.validate_profile_data(profile))

    def test_profile_schema_and_repeated_render_are_stable(self):
        self.assertEqual(portfolio.validate_profile_data(self.profile), [])
        first = portfolio.build_qualifications_table(self.profile)
        second = portfolio.build_qualifications_table(self.profile)
        projects_first = portfolio.build_selected_projects_table(self.profile)
        projects_second = portfolio.build_selected_projects_table(self.profile)
        self.assertEqual(first, second)
        self.assertEqual(projects_first, projects_second)
        self.assertFalse(
            {
                "learner_number",
                "certificate_number",
                "centre_number",
                "certificate_image",
            }
            & portfolio.QUALIFICATION_FIELDS
        )

    def test_no_certificate_image_is_present_in_the_repository(self):
        image_suffixes = {".heic", ".jpeg", ".jpg", ".png", ".tiff", ".webp"}
        certificate_images = [
            path
            for path in portfolio.ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and ".venv" not in path.parts
            and path.suffix.lower() in image_suffixes
            and "certificate" in path.name.lower()
        ]
        self.assertEqual(certificate_images, [])


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
        self.assertIn("## TryHackMe", a)
        self.assertIn("### Achievement Cabinet", a)
        self.assertIn("## Practical Reports and Lab Evidence", a)
        self.assertIn("## Other Platforms in Progress", a)
        self.assertNotIn("## How This Portfolio Is Maintained", a)
        self.assertNotIn("Automated Sync Engine", a)

    def test_marker_updates_are_stable_and_preserve_authored_content(self):
        profile = portfolio.read_json(portfolio.PROFILE, {})
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        htb_data = portfolio.read_optional_json(portfolio.HACKTHEBOX, {})
        cisco_data = cisco.empty_schema()
        readme_section = portfolio.render(profile, rooms, badges, htb_data, cisco_data)
        snapshot_section = portfolio.render_profile_snapshot(
            rooms, badges, profile
        )
        project_section = portfolio.build_selected_projects_table(profile)
        training_section = portfolio.render_training(profile, rooms, badges, htb_data, cisco_data)

        with tempfile.TemporaryDirectory() as directory:
            readme = Path(directory) / "README.md"
            training = Path(directory) / "TRAINING.md"
            authored_readme = (
                "# Pre-Mortem — Cybersecurity Portfolio\n\n"
                "I am developing practical cybersecurity skills.\n\n"
                "## Profile Snapshot\n\n"
                "Qualification and key areas remain authored.\n"
                f"{portfolio.SNAPSHOT_START}\nold counts\n{portfolio.SNAPSHOT_END}\n\n"
                "## About Me\n\nPractical work and safe design.\n\n"
                "## What I Bring\n\nEvidence-backed capabilities.\n\n"
                "## Selected Security Projects\n\n"
                f"{portfolio.PROJECTS_START}\nold project table\n"
                f"{portfolio.PROJECTS_END}\n\n"
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
                portfolio.update_readme(
                    readme_section, snapshot_section, project_section
                )
                portfolio.update_training_md(training_section)
                first = (readme.read_text(encoding="utf-8"),
                         training.read_text(encoding="utf-8"))
                portfolio.update_readme(
                    readme_section, snapshot_section, project_section
                )
                portfolio.update_training_md(training_section)
                second = (readme.read_text(encoding="utf-8"),
                          training.read_text(encoding="utf-8"))

            self.assertEqual(first, second)
            for personal_section in (
                "I am developing practical cybersecurity skills.",
                "## Profile Snapshot",
                "Qualification and key areas remain authored.",
                "## About Me",
                "## What I Bring",
                "### PacketPunch",
                "### ESP32-S2 AI HID Typer",
                "### Cybersecurity Portfolio Automation",
                portfolio.PROJECTS_START,
                "HackPod",
                "X-Link",
                "## Current Focus",
                "## Contact and Profiles",
            ):
                self.assertIn(personal_section, first[0])
            for evidence_section in (
                "## Skills and Evidence",
                "## Practical Reports and Lab Evidence",
                "## TryHackMe",
                "### Completed Rooms — Recent First",
                "### Achievement Cabinet",
                "### Room Milestones",
                "## Other Platforms in Progress",
            ):
                self.assertIn(evidence_section, first[0])
            self.assertIn(
                f"- **TryHackMe evidence:** {len(rooms['rooms'])} completed rooms "
                f"and {len(badges['badges'])} earned badges",
                first[0],
            )
            self.assertIn(
                "Two completed NCFE Level 2 qualifications", first[0]
            )
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
        self.assertIn("## Other Platforms in Progress", rendered)
        self.assertIn(
            "**Hack The Box:** integration is ready; no completed labs are recorded yet.",
            rendered,
        )
        self.assertIn(
            "**Cisco Networking Academy:** the offline integration foundation is ready; "
            "no achievements have been imported yet.",
            rendered,
        )
        self.assertNotIn("## Hack The Box", rendered)
        self.assertNotIn("## Cisco Networking Academy", rendered)
        self.assertNotIn("### Completed Rooms — Recent First", rendered)
        self.assertNotIn("### Achievement Cabinet", rendered)
        self.assertNotIn("### Room Milestones", rendered)

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
        self.assertIn("## Other Platforms in Progress", rendered)
        self.assertIn("**Hack The Box:** 1 machine, 1 challenge, 1 module", rendered)
        self.assertIn(
            "**Cisco Networking Academy:** 1 course, 1 badge, 1 certificate",
            rendered,
        )
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
            "## Skills and Evidence",
            "## Practical Reports and Lab Evidence",
            "### Lab Notes and Drafts",
            "## TryHackMe",
            "### Completed Rooms — Recent First",
            "### Achievement Cabinet",
            "### Room Milestones",
            "## Other Platforms in Progress",
        )
        for section in expected_sections:
            self.assertIn(section, rendered)
        room_count = len(rooms["rooms"])
        badge_count = len(badges["badges"])
        difficulty_counts = {}
        for room in rooms["rooms"]:
            difficulty = room.get("difficulty") or ""
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        self.assertIn(
            f"Rooms Completed</strong>&nbsp;<br>{room_count}", rendered
        )
        self.assertIn(
            f"Badges Earned</strong>&nbsp;<br>{badge_count}", rendered
        )
        for difficulty, count in difficulty_counts.items():
            if difficulty:
                self.assertIn(
                    f"{difficulty}</strong>&nbsp;<br>{count}", rendered
                )
        self.assertIn(
            f"{room_count} lab notes and write-up drafts", rendered
        )
        self.assertIn(
            portfolio.format_sync_timestamp(profile["last_sync"]), rendered
        )
        for removed_section in (
            "## Portfolio Statistics",
            "## How This Portfolio Is Maintained",
            "### Supported Platforms",
            "### Running the Sync Engine",
            "### Local Browser Sessions",
            "### What Is Collected",
            "### What Is Never Collected",
            "### Generated Data and Privacy",
            "### Technical Documentation",
            "### Roadmap",
            "### Repository Rules",
        ):
            self.assertNotIn(removed_section, rendered)

    def test_all_badges_render_as_clickable_images(self):
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        rendered = portfolio.build_achievement_cabinet_section(badges)
        expected = {
            "cat linux.txt": (
                "terminaled",
                "https://assets.tryhackme.com/img/badges/linux.png",
            ),
            "First Four": (
                "first-4-rooms",
                "https://assets.tryhackme.com/img/badges/firstfour.png",
            ),
            "Metasploitable": (
                "metasploitable",
                "https://assets.tryhackme.com/img/badges/metasploit.png",
            ),
            "Networking Nerd": (
                "network-fundamentals",
                "https://assets.tryhackme.com/img/badges/networkfundamentals.png",
            ),
            "Pentesting Principles": (
                "intro-to-pentesting",
                "https://assets.tryhackme.com/img/badges/introtooffensivesecurity.png",
            ),
            "Webbed": (
                "web-fund",
                "https://assets.tryhackme.com/img/badges/webbed.png",
            ),
        }
        self.assertEqual(len(badges["badges"]), 6)
        self.assertEqual(rendered.count("<img src="), 6)
        self.assertEqual(rendered.count("<a href="), 6)
        for name, (code, image) in expected.items():
            self.assertIn(name, rendered)
            self.assertIn(image, rendered)
            self.assertIn(
                f"https://tryhackme.com/PreMortem/badges/{code}",
                rendered,
            )

    def test_recent_rooms_are_data_driven_linked_and_limited(self):
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        rendered = portfolio.build_recent_rooms_section(rooms)
        table_rows = [line for line in rendered.splitlines() if line.startswith("| [")]
        self.assertEqual(len(table_rows), len(rooms["rooms"]))
        for room in rooms["rooms"]:
            self.assertIn(portfolio.md_cell(room["name"]), rendered)
            self.assertIn(room["url"], rendered)

        limited = portfolio.build_recent_rooms_section(rooms, limit=10)
        limited_rows = [line for line in limited.splitlines() if line.startswith("| [")]
        self.assertEqual(len(limited_rows), 10)
        self.assertNotIn(rooms["rooms"][10]["name"], limited)

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
            "## Profile Snapshot",
            "## About Me",
            "## What I Bring",
            "## Selected Security Projects",
            portfolio.GEN_START,
            "## Current Focus",
            "## Contact and Profiles",
            "## About the Portfolio Automation",
        )
        positions = [readme.index(section) for section in expected_order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(readme.count(portfolio.GEN_START), 1)
        self.assertEqual(readme.count(portfolio.GEN_END), 1)
        self.assertEqual(readme.count(portfolio.SNAPSHOT_START), 1)
        self.assertEqual(readme.count(portfolio.SNAPSHOT_END), 1)
        self.assertEqual(readme.count(portfolio.PROJECTS_START), 1)
        self.assertEqual(readme.count(portfolio.PROJECTS_END), 1)
        self.assertLess(
            readme.index(portfolio.SNAPSHOT_START),
            readme.index("## About Me"),
        )
        self.assertIn(
            "I am developing practical cybersecurity skills through formal study",
            readme,
        )
        self.assertIn("dynamic device discovery", readme)
        self.assertIn("ESP32-P4", readme)
        self.assertIn("Security tools with impact.", readme)
        self.assertNotIn("16 room write-up stubs", readme)
        for evidence_section in (
            "## Skills and Evidence",
            "## Practical Reports and Lab Evidence",
            "## TryHackMe",
            "### Completed Rooms — Recent First",
            "### Achievement Cabinet",
            "### Room Milestones",
            "## Other Platforms in Progress",
        ):
            self.assertIn(evidence_section, readme)
        self.assertIn("NCFE Level 2 Certificate in Understanding Coding", readme)
        self.assertIn(
            "NCFE Level 2 Certificate in the Principles of Cyber Security",
            readme,
        )
        self.assertIn("HackPod", readme)
        self.assertIn("X-Link", readme)
        self.assertIn("27 completed rooms and 6 earned badges", readme)
        self.assertIn("Malware Classification", readme)
        rooms = portfolio.read_json(portfolio.ROOMS, {"rooms": []})
        badges = portfolio.read_json(portfolio.BADGES, {"badges": []})
        self.assertIn(
            f"{len(rooms['rooms'])} completed rooms and "
            f"{len(badges['badges'])} earned badges",
            readme,
        )
        self.assertNotIn("## Portfolio Statistics", readme)
        self.assertNotIn("## How This Portfolio Is Maintained", readme)
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
        self.assertIn("## Qualifications", rendered)
        self.assertIn("6 August 2025", rendered)
        self.assertIn("29 May 2025", rendered)
        self.assertIn("Certificate in Cyber Security Practices", rendered)
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
             mock.patch.object(portfolio, "regenerate_readme") as regenerate, \
             mock.patch.object(portfolio, "run_git", return_value=SimpleNamespace(stdout="")):
            rc = portfolio.run_sync(["hackthebox"], interactive=False, auto_push=False)
        self.assertEqual(rc, 1)
        regenerate.assert_not_called()

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
                "## Profile Snapshot",
                "## About Me",
                "## What I Bring",
                "## Selected Security Projects",
                "## Current Focus",
                "## Contact and Profiles",
            ):
                self.assertIn(personal_section, rewritten)
            for evidence_section in (
                "## Skills and Evidence",
                "## Practical Reports and Lab Evidence",
                "## TryHackMe",
                "## Other Platforms in Progress",
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
