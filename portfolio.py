#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.example.json"
ROOMS = ROOT / "data/rooms.json"
PROFILE = ROOT / "data/profile.json"
BADGES = ROOT / "data/badges.json"
HACKTHEBOX = ROOT / "data/hackthebox.json"
CISCO_NETACAD = ROOT / "data/cisco_netacad.json"
EVIDENCE = ROOT / "data/evidence.json"
README = ROOT / "README.md"
TRAINING_MD = ROOT / "TRAINING.md"
BROWSER_STATE = ROOT / ".thm-browser"
START = "<!-- THM:START -->"
END = "<!-- THM:END -->"
# Outer markers delimiting the whole generated portfolio body. The TryHackMe
# START/END markers stay nested inside this region so TryHackMe sync tooling is
# unaffected.
GEN_START = "<!-- PORTFOLIO:START -->"
GEN_END = "<!-- PORTFOLIO:END -->"
SNAPSHOT_START = "<!-- PROFILE-SNAPSHOT:START -->"
SNAPSHOT_END = "<!-- PROFILE-SNAPSHOT:END -->"
PROJECTS_START = "<!-- PROJECTS:START -->"
PROJECTS_END = "<!-- PROJECTS:END -->"
TRAINING_START = "<!-- TRAINING:START -->"
TRAINING_END = "<!-- TRAINING:END -->"
PROFILE_URL = "https://tryhackme.com/p/PreMortem"


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def run_git(*args: str, check: bool = True):
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check, capture_output=True)


def writeup_for(room: dict) -> None:
    path = ROOT / room["writeup"]
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""# {room['name']}

- Platform: TryHackMe
- Status: Template Stub
- Completed: {room['completed']}
- Room URL: {room.get('url') or 'Not recorded'}
- Difficulty: {room.get('difficulty') or 'Not recorded'}

## What the Room Covered

Describe the room without exposing answers or flags.

## Skills Practised

- Add the relevant skills.

## Tools Used

- Add the tools used.

## What I Learned

Explain the concepts in your own words.

## Defensive Relevance

Explain how the techniques could be detected, prevented or mitigated.

## Disclosure Note

This entry contains learning notes only. Flags, credentials and direct room answers have not been published.
""", encoding="utf-8")


BADGE_COLUMNS = 3


VALID_BADGE_CODE = re.compile(r"[A-Za-z0-9._-]+")


def badge_page_url(code) -> str | None:
    """Return the individual public badge page URL for a badge code, or None.

    The code must be a non-empty slug of URL-safe characters; anything else
    (empty, or containing spaces, slashes, quotes, angle brackets, etc.) is
    rejected so it cannot inject HTML or alter the URL path structure. The
    accepted code is URL-encoded (a no-op for valid slugs) before use."""
    code = str(code or "").strip()
    if not code or not VALID_BADGE_CODE.fullmatch(code):
        return None
    return f"https://tryhackme.com/PreMortem/badges/{quote(code, safe='')}"


def build_badge_showcase(badges: list) -> str:
    """Return a GitHub-README-compatible HTML showcase of earned badges.

    Each badge is rendered image-over-name in its own centred table cell, with
    a fixed number of badges per row. Both the image and the name link to that
    badge's own public TryHackMe page, built from its stored ``code``. Names are
    HTML-escaped. A badge without a valid http(s) image falls back to its name
    as text (no broken image); a badge without a valid code is shown unlinked
    rather than wrapped in an invented link. The showcase is generated entirely
    from the supplied data, so future badges appear automatically.
    """
    cells = []
    for badge in badges:
        name = html.escape(safe_public_text(badge.get("name"), "Badge"))
        image = tryhackme_badge_image_url(badge.get("image"))
        if image:
            src = html.escape(image, quote=True)
            inner = f'<img src="{src}" alt="{name}" width="100"><br>\n<strong>{name}</strong>'
        else:
            inner = f"<strong>{name}</strong>"

        url = badge_page_url(badge.get("code"))
        if url:
            link = html.escape(url, quote=True)
            inner = f'<a href="{link}">\n{inner}\n</a>'

        cells.append(f'<td align="center" width="130">\n{inner}\n</td>')

    if not cells:
        return "No badges recorded yet"

    rows = []
    for start in range(0, len(cells), BADGE_COLUMNS):
        row = "\n".join(cells[start:start + BADGE_COLUMNS])
        rows.append(f"<tr>\n{row}\n</tr>")
    table = "<table>\n" + "\n".join(rows) + "\n</table>"
    return f'<div align="center">\n\n{table}\n\n</div>'


DIFFICULTY_ORDER = ("Easy", "Info", "Medium", "Hard", "Insane")


def format_sync_timestamp(value) -> str:
    """Format a stored ISO timestamp for display, e.g. '23 July 2026, 11:44 UTC'.

    The stored value is never modified. Timezone-aware values are normalised to
    UTC; a trailing 'Z' is tolerated. On any parse failure the original value is
    returned unchanged.
    """
    if not value:
        return "Not yet synced"
    text = str(value)
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(dt.timezone.utc)
        return f"{parsed.day} {parsed:%B %Y}, {parsed:%H:%M} UTC"
    except (ValueError, TypeError):
        return text


def build_progress_summary(rooms: dict, badges: dict) -> str:
    """Compact centred HTML summary of room/badge counts and difficulty spread.

    Rooms and Badges always appear; difficulty categories appear only when at
    least one recorded room has that difficulty. All figures are derived from
    the supplied data."""
    room_list = rooms.get("rooms", [])
    counts = {level: 0 for level in DIFFICULTY_ORDER}
    for room in room_list:
        level = (room.get("difficulty") or "").strip().title()
        if level in counts:
            counts[level] += 1

    metrics = [
        ("Rooms Completed", len(room_list)),
        ("Badges Earned", len(badges.get("badges", []))),
    ]
    for level in DIFFICULTY_ORDER:
        if counts[level] > 0:
            metrics.append((level, counts[level]))

    cells = "\n".join(
        f'<td align="center">&nbsp;<strong>{html.escape(label)}</strong>&nbsp;<br>{value}</td>'
        for label, value in metrics
    )
    return f'<div align="center">\n\n<table>\n<tr>\n{cells}\n</tr>\n</table>\n\n</div>'


ROOM_MILESTONES = (10, 25, 50, 100)


def build_milestones(room_count: int) -> str:
    """Portfolio progress milestones (a personal tracker, not TryHackMe badges).

    Completed milestones are marked done; the first incomplete milestone shows
    live progress (e.g. '16 / 25'); later milestones are upcoming. Everything is
    derived from the current room count."""
    next_shown = False
    cells = []
    for target in ROOM_MILESTONES:
        if room_count >= target:
            status = f"✅<br><strong>{target} Rooms</strong><br>Complete"
        elif not next_shown:
            status = f"🚧<br><strong>{target} Rooms</strong><br>{room_count} / {target}"
            next_shown = True
        else:
            status = f"⬜<br><strong>{target} Rooms</strong><br>Upcoming"
        cells.append(f'<td align="center" width="120">\n{status}\n</td>')

    row = "\n".join(cells)
    table = f"<table>\n<tr>\n{row}\n</tr>\n</table>"
    return f'<div align="center">\n\n{table}\n\n</div>'


def read_optional_json(path: Path, default):
    """Load an optional JSON data file, tolerating a missing or malformed file."""
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def safe_url(url) -> str | None:
    """Return the URL only if it is a plain http(s) link, else None."""
    text = str(url or "").strip()
    if text.lower().startswith(("http://", "https://")):
        return text
    return None


PRIVATE_TEXT_PATTERN = re.compile(
    r"(?i)(?:"
    r"/users/[^/\s]+|"
    r"/home/[^/\s]+|"
    r"[a-z]:\\users\\[^\\\s]+|"
    r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}"
    r")"
)


def safe_public_text(value, fallback: str = "") -> str:
    """Return display text only when it does not resemble private identity data."""
    text = str(value or "").strip()
    if not text or PRIVATE_TEXT_PATTERN.search(text):
        return fallback
    return text


def tryhackme_room_url(value) -> str | None:
    """Accept only canonical public TryHackMe room links."""
    url = safe_url(value)
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "tryhackme.com":
        return None
    if not parsed.path.startswith("/room/") or parsed.query or parsed.fragment:
        return None
    return url


def tryhackme_badge_image_url(value) -> str | None:
    """Accept only canonical public TryHackMe badge asset links."""
    url = safe_url(value)
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "assets.tryhackme.com":
        return None
    if not parsed.path.startswith("/img/badges/") or parsed.query or parsed.fragment:
        return None
    return url


def md_cell(value) -> str:
    """Escape a value for safe use inside a Markdown table cell."""
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


# --- Public profile, qualifications and selected projects -----------------

PROFILE_ROOT_FIELDS = {
    "schema_version",
    "last_sync",
    "profile_card_path",
    "username",
    "profile_url",
    "sync_method",
    "qualifications",
    "projects",
}
QUALIFICATION_FIELDS = {
    "title",
    "awarding_body_or_provider",
    "level",
    "status",
    "awarded",
    "completion_year",
}
PROJECT_FIELDS = {
    "name",
    "status",
    "visibility",
    "public_url",
    "summary",
    "progress_percent",
    "progress_label",
    "progress_evidence",
}


def validate_profile_data(profile: dict) -> list[str]:
    """Validate the public profile allow-list without accepting identifiers."""
    errors = []
    if not isinstance(profile, dict):
        return ["profile must be an object"]
    unknown_root = set(profile) - PROFILE_ROOT_FIELDS
    if unknown_root:
        errors.append(
            "unknown profile fields: " + ", ".join(sorted(unknown_root))
        )

    qualifications = profile.get("qualifications", [])
    if not isinstance(qualifications, list):
        errors.append("qualifications must be a list")
    else:
        for index, item in enumerate(qualifications):
            prefix = f"qualifications[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            unknown = set(item) - QUALIFICATION_FIELDS
            if unknown:
                errors.append(
                    f"{prefix} has unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            for field in (
                "title",
                "awarding_body_or_provider",
                "level",
                "status",
            ):
                if not safe_public_text(item.get(field)):
                    errors.append(f"{prefix}.{field} is required")
            if item.get("status") not in {"completed", "in_progress"}:
                errors.append(f"{prefix}.status is invalid")
            awarded = item.get("awarded")
            if awarded is not None:
                try:
                    dt.date.fromisoformat(str(awarded))
                except (TypeError, ValueError):
                    errors.append(f"{prefix}.awarded must be an ISO date")
            completion_year = item.get("completion_year")
            if completion_year is not None and (
                not isinstance(completion_year, int)
                or completion_year < 1900
                or completion_year > 9999
            ):
                errors.append(f"{prefix}.completion_year is invalid")

    projects = profile.get("projects", [])
    if not isinstance(projects, list):
        errors.append("projects must be a list")
    else:
        for index, item in enumerate(projects):
            prefix = f"projects[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            unknown = set(item) - PROJECT_FIELDS
            if unknown:
                errors.append(
                    f"{prefix} has unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            for field in ("name", "status", "visibility", "summary"):
                if not safe_public_text(item.get(field)):
                    errors.append(f"{prefix}.{field} is required")
            if item.get("status") not in {"active", "in_development"}:
                errors.append(f"{prefix}.status is invalid")
            if item.get("visibility") not in {"public", "private"}:
                errors.append(f"{prefix}.visibility is invalid")
            public_url = item.get("public_url")
            if public_url is not None and (
                item.get("visibility") != "public" or not safe_url(public_url)
            ):
                errors.append(
                    f"{prefix}.public_url requires a safe public project"
                )
            progress = item.get("progress_percent")
            if progress is not None and (
                not isinstance(progress, int) or not 0 <= progress <= 100
            ):
                errors.append(f"{prefix}.progress_percent is invalid")
    return errors


def format_public_date(value) -> str:
    try:
        parsed = dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return "—"
    return f"{parsed.day} {parsed:%B %Y}"


def build_qualifications_table(profile: dict) -> str:
    rows = []
    for item in profile.get("qualifications", []):
        if not isinstance(item, dict):
            continue
        title = md_cell(safe_public_text(item.get("title"), "Qualification"))
        provider = md_cell(
            safe_public_text(
                item.get("awarding_body_or_provider"), "—"
            )
        )
        level = md_cell(safe_public_text(item.get("level"), "—"))
        status = {
            "completed": "Completed",
            "in_progress": "In progress",
        }.get(item.get("status"), "—")
        awarded = (
            format_public_date(item.get("awarded"))
            if item.get("status") == "completed"
            else "—"
        )
        rows.append(
            f"| {title} | {provider} | {level} | {status} | {awarded} |"
        )
    if not rows:
        rows.append("| No qualifications recorded | — | — | — | — |")
    return (
        "| Qualification | Awarding body / provider | Level | Status | Awarded |\n"
        "|---|---|---:|---|---|\n"
        + "\n".join(rows)
    )


def build_qualification_summary(profile: dict) -> str:
    qualifications = [
        item
        for item in profile.get("qualifications", [])
        if isinstance(item, dict)
    ]
    completed_ncfe_level_two = [
        item
        for item in qualifications
        if item.get("status") == "completed"
        and item.get("awarding_body_or_provider") == "NCFE"
        and str(item.get("level")) == "2"
    ]
    current_level_three = next(
        (
            item
            for item in qualifications
            if item.get("status") == "in_progress"
            and str(item.get("level")) == "3"
        ),
        None,
    )
    if len(completed_ncfe_level_two) == 2 and current_level_three:
        provider = safe_public_text(
            current_level_three.get("awarding_body_or_provider"),
            "the current provider",
        )
        return (
            "Two completed NCFE Level 2 qualifications in cyber security "
            "principles and coding; currently completing a Level 3 Certificate "
            f"in Cyber Security Practices with {provider}."
        )
    completed = sum(
        item.get("status") == "completed" for item in qualifications
    )
    in_progress = sum(
        item.get("status") == "in_progress" for item in qualifications
    )
    return (
        f"{completed} completed qualification(s); "
        f"{in_progress} currently in progress."
    )


def build_qualifications_section(profile: dict) -> str:
    return (
        "## Qualifications\n\n"
        f"{build_qualification_summary(profile)}\n\n"
        f"{build_qualifications_table(profile)}"
    )


def build_selected_projects_table(profile: dict) -> str:
    rows = []
    for item in profile.get("projects", []):
        if not isinstance(item, dict):
            continue
        name = md_cell(safe_public_text(item.get("name"), "Project"))
        visibility = item.get("visibility")
        public_url = safe_url(item.get("public_url"))
        if visibility == "public" and public_url:
            name = f"[{name}]({public_url})"
        status = {
            "active": "Active",
            "in_development": "In development",
        }.get(item.get("status"), "—")
        visibility_label = {
            "public": "Public repository",
            "private": "Private repository",
        }.get(visibility, "Repository status unavailable")
        progress = item.get("progress_percent")
        progress_label = safe_public_text(
            item.get("progress_label"), "Not quantified"
        )
        if isinstance(progress, int) and 0 <= progress <= 100:
            progress_text = f"{progress}% — {progress_label}"
        else:
            progress_text = progress_label
        summary = safe_public_text(
            item.get("summary"), "Public project summary unavailable."
        )
        rows.append(
            f"| {name} | {status} · {visibility_label} "
            f"| {md_cell(progress_text)} | {md_cell(summary)} |"
        )
    if not rows:
        rows.append("| No projects recorded | — | — | — |")
    return (
        f"{PROJECTS_START}\n"
        "| Project | Status | Progress | Summary |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
        + f"\n{PROJECTS_END}"
    )


# --- Skills matrix (evidence-backed) ---------------------------------------

def _rooms_matching(rooms: dict, keywords) -> list:
    names = []
    for room in rooms.get("rooms", []):
        low = str(room.get("name", "")).lower()
        if any(keyword in low for keyword in keywords):
            name = safe_public_text(room.get("name"))
            if name:
                names.append(name)
    return names


def _badge_name(badges: dict, code: str) -> str:
    for badge in badges.get("badges", []):
        if badge.get("code") == code:
            return safe_public_text(badge.get("name"))
    return ""


def build_skills_section(rooms: dict, badges: dict) -> str:
    # Skills whose evidence is derived from live room/badge data.
    room_skills = [
        ("Networking", ("networking", "lan", "dns"), "network-fundamentals"),
        ("Linux", ("linux",), "terminaled"),
        ("Web security",
         ("web", "walking an application", "content discovery", "subdomain",
          "idor", "authentication bypass"),
         "web-fund"),
    ]
    matrix = []
    for label, keywords, badge_code in room_skills:
        matched = _rooms_matching(rooms, keywords)
        badge = _badge_name(badges, badge_code)
        if matched:
            evidence = "TryHackMe rooms: " + ", ".join(matched)
            if badge:
                evidence += f"; and the {badge} badge"
        else:
            evidence = "Developing through TryHackMe training"
        matrix.append((label, evidence))

    # Skills whose evidence is project/tooling based (verified in-repo or above).
    matrix.extend([
        ("Python",
         "Portfolio automation, platform adapters, rendering, schema validation, "
         "privacy checks, and deterministic test tooling"),
        ("Git and GitHub",
         "Version control, focused branches, GitHub Actions validation, and reproducible history"),
        ("Embedded systems",
         "PacketPunch and ESP32-S2 AI HID Typer development"),
        ("Android",
         "ESP32-S2 AI HID Typer companion application"),
        ("Security automation",
         "TryHackMe and Hack The Box evidence collection plus Cisco offline "
         "sanitisation and rendering foundation"),
        ("Privacy and safe design",
         "Credential checks, isolated browser state, payload limits, sanitisation, "
         "and failure-safe persistence"),
    ])

    rows = "\n".join(f"| {md_cell(label)} | {md_cell(evidence)} |" for label, evidence in matrix)
    return (
        "## Skills and Evidence\n\n"
        "Each skill below is tied to work recorded in this repository — completed "
        "training, badges, projects or scripts. No self-rated scores are used.\n\n"
        "| Skill area | Evidence |\n"
        "|---|---|\n"
        f"{rows}"
    )


# --- Practical labs and reports (evidence-driven) --------------------------

EVIDENCE_GROUPS = [
    ("Lab write-ups", "lab_writeups"),
    ("Threat research", "threat_research"),
    ("Incident analysis", "incident_analysis"),
    ("Qualification work", "qualification_work"),
    ("Security reports", "security_reports"),
]


def _read_title_and_status(path: Path) -> tuple[str, str]:
    title = path.stem
    status = "Template Stub"
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("# "):
                title = line_str[2:].strip()
            elif line_str.startswith("- Status:"):
                status = line_str.split(":", 1)[1].strip()
        if "Describe the room without exposing answers or flags" in content:
            status = "Template Stub"
    except OSError:
        pass
    return title, status


def _evidence_link(title: str, target: str) -> str:
    label = html.escape(title)
    url = safe_url(target)
    if url:
        return f"- [{label}]({url})"
    # Otherwise treat as a repository-relative path that must actually exist.
    candidate = (ROOT / target).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return f"- {label}"
    if candidate.exists():
        rel = candidate.relative_to(ROOT).as_posix()
        return f"- [{label}]({rel})"
    return f"- {label}"


def build_evidence_section() -> str:
    completed_items = []
    draft_items = []

    writeups_dir = ROOT / "writeups"
    if writeups_dir.exists():
        for path in sorted(writeups_dir.rglob("*.md")):
            if "templates" in path.parts:
                continue
            title, status = _read_title_and_status(path)
            rel = path.relative_to(ROOT).as_posix()
            if status.lower() == "completed":
                completed_items.append(_evidence_link(title, rel))
            else:
                draft_items.append(_evidence_link(title, rel))

    manifest = read_optional_json(EVIDENCE, {})
    if isinstance(manifest, dict):
        key_to_label = {key: label for label, key in EVIDENCE_GROUPS}
        for key, label in key_to_label.items():
            entries = manifest.get(key)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                title = str(entry.get("title") or "").strip()
                target = str(entry.get("path") or entry.get("url") or "").strip()
                if title and target:
                    completed_items.append(_evidence_link(title, target))

    parts = ["## Practical Reports and Lab Evidence"]
    if completed_items:
        parts.append("### Completed Reports\n\n" + "\n".join(completed_items))
    else:
        parts.append(
            "### Completed Reports\n\n"
            "No completed reports are published yet. Reports will appear here only "
            "after their notes have been reviewed and finished."
        )

    if draft_items:
        parts.append(
            "### Lab Notes and Drafts\n\n"
            "These files relate to completed rooms, but the write-ups themselves are "
            "still working notes or templates and are not presented as completed reports.\n\n"
            "<details>\n"
            f"<summary>{len(draft_items)} lab notes and write-up drafts</summary>\n\n"
            + "\n".join(draft_items)
            + "\n\n</details>"
        )

    return "\n\n".join(parts)


# --- Hack The Box (future-ready, no invented data) -------------------------

def _htb_list(data: dict, section: str, field: str) -> list:
    container = data.get(section)
    if isinstance(container, dict) and isinstance(container.get(field), list):
        return container[field]
    return []


def _htb_totals(data: dict) -> list[tuple[str, int]]:
    """Ordered (label, count) pairs, keeping only categories that have data."""
    pairs = [
        ("Machines", _htb_list(data, "labs", "machines")),
        ("Sherlocks", _htb_list(data, "labs", "sherlocks")),
        ("Challenges", _htb_list(data, "labs", "challenges")),
        ("Modules", _htb_list(data, "academy", "modules")),
        ("Paths", _htb_list(data, "academy", "paths")),
        ("Certifications", _htb_list(data, "academy", "certifications")),
        ("Badges", _htb_list(data, "labs", "badges") + _htb_list(data, "academy", "badges")),
    ]
    return [(label, len(items)) for label, items in pairs if items]


def _htb_machines_table(machines: list) -> str:
    header = "| Machine | Difficulty | OS | Status | Completed |\n|---|---|---|---|---|"
    rows = []
    for machine in machines[:10]:
        rows.append(
            f"| {md_cell(machine.get('name'))} | {md_cell(machine.get('difficulty') or '—')} "
            f"| {md_cell(machine.get('operating_system') or '—')} "
            f"| {md_cell((machine.get('status') or '—').title())} "
            f"| {md_cell(machine.get('completed_at') or '—')} |"
        )
    return header + "\n" + "\n".join(rows)


def _htb_simple_table(items: list, first_header: str) -> str:
    header = f"| {first_header} | Category | Difficulty | Completed |\n|---|---|---|---|"
    rows = []
    for item in items[:10]:
        rows.append(
            f"| {md_cell(item.get('name'))} | {md_cell(item.get('category') or '—')} "
            f"| {md_cell(item.get('difficulty') or '—')} | {md_cell(item.get('completed_at') or '—')} |"
        )
    return header + "\n" + "\n".join(rows)


def _htb_academy_table(modules: list, paths: list) -> str:
    header = "| Module or Path | Type | Status | Completed |\n|---|---|---|---|"
    rows = []
    for path in paths[:6]:
        rows.append(
            f"| {md_cell(path.get('name'))} | Path | {md_cell((path.get('status') or 'completed').title())} "
            f"| {md_cell(path.get('completed_at') or '—')} |"
        )
    for module in modules[:10]:
        module_type = f"Module ({md_cell(module.get('tier'))})" if module.get("tier") else "Module"
        rows.append(
            f"| {md_cell(module.get('name'))} | {module_type} "
            f"| {md_cell((module.get('status') or 'completed').title())} "
            f"| {md_cell(module.get('completed_at') or '—')} |"
        )
    return header + "\n" + "\n".join(rows)


def _htb_name_list(items: list) -> str:
    return "\n".join(f"- {md_cell(item.get('name'))}" for item in items)


def build_hackthebox_section(data: dict | None = None) -> str:
    """Render the Hack The Box section from data/hackthebox.json (new schema).

    Only categories with recorded data are shown; unsupported/empty categories
    never produce empty tables. All content is escaped and only http(s) links
    are emitted. No flags, answers or protected solution content are rendered.
    """
    if data is None:
        data = read_optional_json(HACKTHEBOX, {})
    if not isinstance(data, dict):
        data = {}

    identity = data.get("public_identity") if isinstance(data.get("public_identity"), dict) else {}
    username = html.escape(str(identity.get("username") or "").strip())
    profile_url = safe_url(identity.get("profile_url"))
    totals = _htb_totals(data)

    header = "## Hack The Box\n\n"
    if not totals and not username and not profile_url:
        return header + (
            "Hack The Box progress has not been added yet. This section will track "
            "Machines, Sherlocks, Challenges and Academy modules as they are completed."
        )

    parts = [header.rstrip("\n")]

    # Identity + last sync line.
    if profile_url and username:
        identity_line = f"**Profile:** [{username}]({profile_url})"
    elif profile_url:
        identity_line = f"**Profile:** {profile_url}"
    elif username:
        identity_line = f"**Profile:** {username}"
    else:
        identity_line = ""
    if identity_line:
        parts.append(identity_line + "<br>\n**Last successful HTB sync:** "
                     + format_sync_timestamp(data.get("synced_at")))
    else:
        parts.append("**Last successful HTB sync:** " + format_sync_timestamp(data.get("synced_at")))

    rank = (data.get("labs") or {}).get("rank")
    if rank:
        parts.append(f"**Rank:** {html.escape(str(rank))}")

    # Compact totals (centred), only populated categories.
    cells = "\n".join(
        f'<td align="center">&nbsp;<strong>{html.escape(label)}</strong>&nbsp;<br>{count}</td>'
        for label, count in totals
    )
    parts.append(f'<div align="center">\n\n<table>\n<tr>\n{cells}\n</tr>\n</table>\n\n</div>')

    machines = _htb_list(data, "labs", "machines")
    if machines:
        parts.append("### Recently Completed Machines\n\n" + _htb_machines_table(machines))

    sherlocks = _htb_list(data, "labs", "sherlocks")
    if sherlocks:
        parts.append("### Sherlocks\n\n" + _htb_simple_table(sherlocks, "Sherlock"))

    challenges = _htb_list(data, "labs", "challenges")
    if challenges:
        parts.append("### Challenges\n\n" + _htb_simple_table(challenges, "Challenge"))

    modules = _htb_list(data, "academy", "modules")
    paths = _htb_list(data, "academy", "paths")
    if modules or paths:
        parts.append("### Academy\n\n" + _htb_academy_table(modules, paths))

    certifications = _htb_list(data, "academy", "certifications")
    if certifications:
        cert_lines = "\n".join(
            f"- {md_cell(cert.get('name'))}" + (f" — {md_cell(cert.get('issued_at'))}" if cert.get("issued_at") else "")
            for cert in certifications
        )
        parts.append("### Certifications\n\n" + cert_lines)

    badges = _htb_list(data, "labs", "badges") + _htb_list(data, "academy", "badges")
    if badges:
        parts.append("### Badges\n\n" + _htb_name_list(badges))

    achievements = data.get("achievements") if isinstance(data.get("achievements"), list) else []
    if achievements:
        parts.append("### Verified Achievements\n\n" + _htb_name_list(achievements))

    parts.append(
        "Achievement metadata only — no flags, answers or solution steps are published, "
        "in line with Hack The Box content rules."
    )
    return "\n\n".join(parts)


def build_tryhackme_summary(profile: dict, rooms: dict, badges: dict) -> str:
    last_sync = format_sync_timestamp(profile.get("last_sync"))
    progress_summary = build_progress_summary(rooms, badges)

    room_list = rooms.get("rooms", [])
    ordered = sorted(room_list, key=lambda item: item.get("completed", ""), reverse=True)
    recent_names = [room.get("name", "") for room in ordered[:5] if room.get("name")]
    recent_str = ", ".join(recent_names) if recent_names else "None recorded yet"

    return f"""{START}
### TryHackMe Summary

**Profile:** [PreMortem]({PROFILE_URL})<br>
**Last local sync:** {last_sync}

{progress_summary}

**Recent Activity:** {recent_str}.<br>
_See [TRAINING.md](TRAINING.md#tryhackme) for complete TryHackMe room history, badge showcase, and room milestones._
{END}"""


def build_hackthebox_summary(data: dict | None = None) -> str:
    if data is None:
        data = read_optional_json(HACKTHEBOX, {})
    if not isinstance(data, dict):
        data = {}

    # The public README identity is deliberately fixed. Saved HTB identity data
    # may be absent, stale, malformed, or contain an account holder's private
    # name; none of it is allowed to override the approved public identity.
    username = "PreMortem"
    profile_url = "https://htb.site/PreMortem"
    totals = _htb_totals(data)

    header = "## Hack The Box\n\n"
    identity_line = f"**Profile:** [{username}]({profile_url})<br>**Last local sync:** {format_sync_timestamp(data.get('synced_at'))}"

    if not totals:
        return header + identity_line + "\n\n" + (
            "Hack The Box integration is active. No completed labs recorded yet. "
            "See [TRAINING.md](TRAINING.md#hack-the-box) for complete platform metrics."
        )

    cells = "\n".join(
        f'<td align="center">&nbsp;<strong>{html.escape(label)}</strong>&nbsp;<br>{count}</td>'
        for label, count in totals
    )
    table = f'<div align="center">\n\n<table>\n<tr>\n{cells}\n</tr>\n</table>\n\n</div>'
    return header + identity_line + "\n\n" + table + "\n\n" + (
        "_See [TRAINING.md](TRAINING.md#hack-the-box) for complete Hack The Box machine, "
        "Sherlock, challenge, and Academy history._"
    )


def _validated_cisco_data(data: dict | None = None) -> tuple[dict, str]:
    """Return safe Cisco data and its render state.

    Invalid or malformed saved data is never rendered. Importing here keeps the
    renderer compatible with installations that only use the legacy commands.
    """
    from platforms import cisco_netacad as cisco

    if data is None:
        data = read_optional_json(CISCO_NETACAD, None)
    if not isinstance(data, dict) or cisco.validate_data(data):
        return cisco.empty_schema("unavailable"), "unavailable"
    return data, data.get("collection_status", "unavailable")


def _cisco_counts(data: dict) -> list[tuple[str, int]]:
    return [
        ("Courses", len(data.get("courses") or [])),
        ("Badges", len(data.get("badges") or [])),
        ("Certificates", len(data.get("certificates") or [])),
    ]


def build_cisco_summary(data: dict | None = None) -> str:
    data, state = _validated_cisco_data(data)
    header = "## Cisco Networking Academy\n\n"
    if state == "unavailable":
        return header + (
            "**Status:** Saved Cisco data is unavailable or failed validation.<br>\n"
            "_No Cisco account or identity data is rendered. Other platform data remains unaffected._"
        )
    if state != "available":
        return header + (
            "**Status:** Offline integration foundation ready; no achievements imported.<br>\n"
            "_Live browser extraction remains a future milestone. Only sanitised, "
            "non-identifying achievement metadata can be rendered._"
        )

    populated = [(label, count) for label, count in _cisco_counts(data) if count]
    cells = "\n".join(
        f'<td align="center">&nbsp;<strong>{label}</strong>&nbsp;<br>{count}</td>'
        for label, count in populated
    )
    table = f'<div align="center">\n\n<table>\n<tr>\n{cells}\n</tr>\n</table>\n\n</div>'
    return header + (
        f"**Last local data update:** {format_sync_timestamp(data.get('synced_at'))}\n\n"
        f"{table}\n\n"
        "_See [TRAINING.md](TRAINING.md#cisco-networking-academy) for complete Cisco "
        "course, badge, certificate, and skills metadata._"
    )


def build_tryhackme_detailed(profile: dict, rooms: dict, badges: dict) -> str:
    rows = []
    ordered = sorted(rooms.get("rooms", []), key=lambda item: item.get("completed", ""), reverse=True)
    for room in ordered:
        name = md_cell(safe_public_text(room.get("name"), "Sanitised room"))
        room_url = tryhackme_room_url(room.get("url"))
        if room_url:
            name = f"[{name}]({room_url})"
        difficulty = md_cell(safe_public_text(room.get("difficulty"), "—"))
        completed = md_cell(safe_public_text(room.get("completed"), "—"))
        rows.append(f"| {name} | {difficulty} | {completed} |")
    if not rows:
        rows.append("| No rooms recorded yet | — | — |")

    badge_showcase = build_badge_showcase(badges.get("badges", []))
    progress_summary = build_progress_summary(rooms, badges)
    milestones = build_milestones(len(rooms.get("rooms", [])))
    last_sync = format_sync_timestamp(profile.get("last_sync"))

    return f"""## TryHackMe

**Profile:** [PreMortem]({PROFILE_URL})<br>
**Last local sync:** {last_sync}

{progress_summary}

### Completed Rooms

| Room | Difficulty | Completed |
|---|---|---|
{chr(10).join(rows)}

### Achievement Cabinet

A growing collection of achievements earned through completed TryHackMe rooms and learning paths.

{badge_showcase}

### Room Milestones

_Portfolio progress milestones — a personal tracker, not official TryHackMe badges._

{milestones}"""


def _cisco_skills(skills) -> str:
    return ", ".join(md_cell(skill) for skill in skills) if isinstance(skills, list) and skills else "—"


def build_cisco_detailed(data: dict | None = None) -> str:
    data, state = _validated_cisco_data(data)
    header = "## Cisco Networking Academy\n\n"
    if state == "unavailable":
        return header + (
            "Saved Cisco Networking Academy data is unavailable or failed privacy/schema "
            "validation. Nothing from that file has been rendered."
        )
    if state != "available":
        return header + (
            "No Cisco Networking Academy achievements have been imported. The offline "
            "schema, privacy scrubber, CLI selection, and saved-data renderer are ready; "
            "interactive browser collection remains the next milestone."
        )

    parts = [
        header.rstrip("\n"),
        "**Last local data update:** " + format_sync_timestamp(data.get("synced_at")),
    ]
    courses = data.get("courses") or []
    if courses:
        rows = "\n".join(
            f"| {md_cell(item.get('title'))} | {md_cell((item.get('status') or '').replace('_', ' ').title())} "
            f"| {md_cell(item.get('completed_at') or '—')} | {_cisco_skills(item.get('skills'))} |"
            for item in courses
        )
        parts.append(
            "### Courses\n\n"
            "| Course | Status | Completed | Skills |\n|---|---|---|---|\n" + rows
        )
    badges = data.get("badges") or []
    if badges:
        rows = "\n".join(
            f"| {md_cell(item.get('title'))} | {md_cell(item.get('earned_at') or '—')} "
            f"| {_cisco_skills(item.get('skills'))} |"
            for item in badges
        )
        parts.append("### Badges\n\n| Badge | Earned | Skills |\n|---|---|---|\n" + rows)
    certificates = data.get("certificates") or []
    if certificates:
        rows = "\n".join(
            f"| {md_cell(item.get('title'))} | {md_cell(item.get('issued_at') or '—')} "
            f"| {_cisco_skills(item.get('skills'))} |"
            for item in certificates
        )
        parts.append("### Certificates\n\n| Certificate | Issued | Skills |\n|---|---|---|\n" + rows)
    parts.append(
        "Sanitised achievement metadata only. Names, email addresses, account and "
        "certificate IDs, private URLs, cookies, tokens, and browser state are excluded."
    )
    return "\n\n".join(parts)


def build_training_snapshot(
    rooms: dict,
    badges: dict,
    htb_data: dict | None = None,
    cisco_data: dict | None = None,
    profile: dict | None = None,
) -> str:
    """Build the public TryHackMe overview from validated saved evidence."""
    del htb_data, cisco_data
    if not isinstance(profile, dict):
        profile = {}

    focus_areas = []
    if _rooms_matching(rooms, ("networking", "lan", "dns")):
        focus_areas.append("networking fundamentals")
    if _rooms_matching(rooms, ("linux",)):
        focus_areas.append("Linux fundamentals")
    if _rooms_matching(
        rooms,
        ("web", "walking an application", "content discovery", "subdomain",
         "idor", "authentication bypass"),
    ):
        focus_areas.append("web security")

    profile_lines = f"**Profile:** [PreMortem]({PROFILE_URL})"
    if profile.get("last_sync"):
        profile_lines += (
            f"<br>\n**Last local sync:** "
            f"{format_sync_timestamp(profile.get('last_sync'))}"
        )

    return (
        "## TryHackMe\n\n"
        f"{profile_lines}\n\n"
        f"{build_progress_summary(rooms, badges)}\n\n"
        f"**Current focus:** {', '.join(focus_areas) if focus_areas else 'practical security foundations'}.\n\n"
        "[TRAINING.md](TRAINING.md#tryhackme) retains the same evidence as a complete "
        "platform history."
    )


def build_recent_rooms_section(rooms: dict, limit: int | None = None) -> str:
    """Render completed rooms in reverse completion order.

    README rendering passes no limit so every saved room remains visible. A
    caller may still request a smaller sample for another output.
    """
    ordered = sorted(
        rooms.get("rooms") or [],
        key=lambda item: item.get("completed", ""),
        reverse=True,
    )
    if limit is not None:
        ordered = ordered[:limit]
    if not ordered:
        return ""

    rows = []
    for room in ordered:
        name = md_cell(safe_public_text(room.get("name"), "Sanitised room"))
        url = tryhackme_room_url(room.get("url"))
        linked_name = f"[{name}]({url})" if url else name
        rows.append(
            f"| {linked_name} | {md_cell(safe_public_text(room.get('difficulty'), '—'))} "
            f"| {md_cell(safe_public_text(room.get('completed'), '—'))} |"
        )
    return (
        "### Completed Rooms — Recent First\n\n"
        "| Room | Difficulty | Completed |\n"
        "|---|---|---|\n"
        + "\n".join(rows)
    )


def build_achievement_cabinet_section(badges: dict) -> str:
    earned = badges.get("badges") or []
    if not earned:
        return ""
    return (
        "### Achievement Cabinet\n\n"
        "Earned TryHackMe badges generated from the saved canonical badge data. "
        "Each badge links to its public achievement page.\n\n"
        + build_badge_showcase(earned)
    )


def build_room_milestones_section(rooms: dict) -> str:
    room_count = len(rooms.get("rooms") or [])
    if not room_count:
        return ""
    return (
        "### Room Milestones\n\n"
        "_Portfolio progress milestones — a personal tracker, not official TryHackMe badges._\n\n"
        + build_milestones(room_count)
    )


def render_profile_snapshot(
    rooms: dict,
    badges: dict,
    profile: dict | None = None,
) -> str:
    """Render changing public CV figures inside the authored profile snapshot."""
    room_count = len(rooms.get("rooms") or [])
    badge_count = len(badges.get("badges") or [])
    qualification_content = ""
    if profile and profile.get("qualifications"):
        qualification_content = (
            f"- **Qualifications:** {build_qualification_summary(profile)}\n\n"
            f"{build_qualifications_table(profile)}\n\n"
        )
    return (
        f"{SNAPSHOT_START}\n"
        f"{qualification_content}"
        f"- **TryHackMe evidence:** {room_count} completed rooms and "
        f"{badge_count} earned badges\n"
        f"{SNAPSHOT_END}"
    )


def build_other_platforms_section(
    htb_data: dict | None = None,
    cisco_data: dict | None = None,
) -> str:
    """Render compact status lines for platforms without dominant README evidence."""
    def count_label(count: int, label: str) -> str:
        singular = label[:-1] if count == 1 and label.endswith("s") else label
        return f"{count} {singular.lower()}"

    if not isinstance(htb_data, dict):
        htb_data = {}
    htb_totals = _htb_totals(htb_data)
    if htb_totals:
        htb_text = ", ".join(count_label(count, label) for label, count in htb_totals)
        htb_line = f"- **Hack The Box:** {htb_text} recorded."
    else:
        htb_line = (
            "- **Hack The Box:** integration is ready; no completed labs are "
            "recorded yet."
        )

    cisco_data, cisco_state = _validated_cisco_data(cisco_data)
    cisco_totals = [
        (label, count) for label, count in _cisco_counts(cisco_data) if count
    ]
    if cisco_state == "available" and cisco_totals:
        cisco_text = ", ".join(
            count_label(count, label) for label, count in cisco_totals
        )
        cisco_line = f"- **Cisco Networking Academy:** {cisco_text} recorded."
    elif cisco_state == "unavailable":
        cisco_line = (
            "- **Cisco Networking Academy:** saved data is unavailable or failed "
            "validation; no achievements are displayed."
        )
    else:
        cisco_line = (
            "- **Cisco Networking Academy:** the offline integration foundation is "
            "ready; no achievements have been imported yet."
        )

    return "## Other Platforms in Progress\n\n" + htb_line + "\n" + cisco_line


def render(
    profile: dict,
    rooms: dict,
    badges: dict,
    htb_data: dict | None = None,
    cisco_data: dict | None = None,
) -> str:
    if htb_data is None:
        htb_data = read_optional_json(HACKTHEBOX, {})

    sections = [
        build_skills_section(rooms, badges),
        build_training_snapshot(rooms, badges, htb_data, cisco_data, profile),
        build_recent_rooms_section(rooms),
        build_achievement_cabinet_section(badges),
        build_room_milestones_section(rooms),
        build_evidence_section(),
        build_other_platforms_section(htb_data, cisco_data),
    ]
    return GEN_START + "\n" + "\n\n".join(section for section in sections if section) + "\n" + GEN_END


def render_training(
    profile: dict,
    rooms: dict,
    badges: dict,
    htb_data: dict | None = None,
    cisco_data: dict | None = None,
) -> str:
    if htb_data is None:
        htb_data = read_optional_json(HACKTHEBOX, {})

    sections = [
        build_qualifications_section(profile),
        build_tryhackme_detailed(profile, rooms, badges),
        build_hackthebox_section(htb_data),
        build_cisco_detailed(cisco_data),
    ]
    return TRAINING_START + "\n" + "\n\n".join(sections) + "\n" + TRAINING_END


def update_readme(
    section: str,
    snapshot: str | None = None,
    projects: str | None = None,
) -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(GEN_START) + r".*?" + re.escape(GEN_END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README is missing portfolio generated markers")
    text = pattern.sub(lambda _match: section, text)

    if snapshot is not None:
        snapshot_pattern = re.compile(
            re.escape(SNAPSHOT_START) + r".*?" + re.escape(SNAPSHOT_END),
            re.DOTALL,
        )
        if not snapshot_pattern.search(text):
            raise SystemExit("README is missing profile snapshot markers")
        text = snapshot_pattern.sub(lambda _match: snapshot, text)

    if projects is not None:
        projects_pattern = re.compile(
            re.escape(PROJECTS_START) + r".*?" + re.escape(PROJECTS_END),
            re.DOTALL,
        )
        if not projects_pattern.search(text):
            raise SystemExit("README is missing selected-project markers")
        text = projects_pattern.sub(lambda _match: projects, text)

    README.write_text(text, encoding="utf-8")


def update_training_md(section: str) -> None:
    if not TRAINING_MD.exists():
        initial = (
            "# Cybersecurity Training History — Pre-Mortem\n\n"
            "This is the supporting training record for Pre-Mortem's cybersecurity "
            "portfolio. It contains detailed, evidence-backed activity generated from "
            "saved platform data by the "
            "[Cybersecurity Portfolio Sync Engine](docs/SYNC_ENGINE.md).\n\n"
            f"{TRAINING_START}\n{TRAINING_END}\n"
        )
        TRAINING_MD.write_text(initial, encoding="utf-8")
    text = TRAINING_MD.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(TRAINING_START) + r".*?" + re.escape(TRAINING_END), re.DOTALL)
    if not pattern.search(text):
        initial = (
            "# Cybersecurity Training History — Pre-Mortem\n\n"
            "This is the supporting training record for Pre-Mortem's cybersecurity "
            "portfolio. It contains detailed, evidence-backed activity generated from "
            "saved platform data by the "
            "[Cybersecurity Portfolio Sync Engine](docs/SYNC_ENGINE.md).\n\n"
            f"{TRAINING_START}\n{TRAINING_END}\n"
        )
        TRAINING_MD.write_text(initial, encoding="utf-8")
        text = TRAINING_MD.read_text(encoding="utf-8")
    TRAINING_MD.write_text(pattern.sub(lambda _match: section, text), encoding="utf-8")


def normalise_room(raw: dict) -> dict | None:
    name = re.sub(r"\s+", " ", raw.get("name", "")).strip()
    url = raw.get("url", "").strip()
    if not name or len(name) > 120 or "/room/" not in url:
        return None
    slug = slugify(urlparse(url).path.rsplit("/", 1)[-1] or name)
    return {
        "name": name,
        "slug": slug,
        "url": url,
        "difficulty": raw.get("difficulty", ""),
        "category": "",
        "completed": dt.date.today().isoformat(),
        "writeup": f"writeups/tryhackme/{slug}.md",
        "source": "authenticated-browser-sync",
    }


def browser_sync(args) -> int:
    # Preserve the legacy command, but route it through the same complete,
    # validated API collector used by the multi-platform CLI. The former
    # duplicate DOM scraper stopped after the first 16 rendered cards.
    import room_sync

    added = room_sync.sync_rooms()

    if args.publish:
        run_git("add", "--", *PUBLISH_ALLOWLIST)
        staged = run_git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            print("No repository changes to publish.")
        else:
            run_git("commit", "-m", f"Sync TryHackMe activity ({dt.date.today().isoformat()})")
            run_git("push")
            print("Committed and pushed the update.")
    return added


def add_room(args):
    name = args.name or input("Room name: ").strip()
    if not name:
        raise SystemExit("Room name is required")
    slug = slugify(name)
    data = read_json(ROOMS, {"rooms": []})
    if any(room["slug"] == slug for room in data["rooms"]):
        raise SystemExit("That room is already recorded")
    room = {
        "name": name,
        "slug": slug,
        "url": args.url or "",
        "difficulty": args.difficulty or "",
        "category": "",
        "completed": args.completed or dt.date.today().isoformat(),
        "writeup": f"writeups/tryhackme/{slug}.md",
        "source": "manual",
    }
    data["rooms"].append(room)
    write_json(ROOMS, data)
    writeup_for(room)
    regenerate_readme()
    print(f"Added {name}")


# --------------------------------------------------------------------------- #
# Cybersecurity Portfolio Sync Engine
# --------------------------------------------------------------------------- #

PLATFORM_KEYS = ("tryhackme", "hackthebox", "cisco")

# Files the automated commit flow is ever allowed to stage. Browser profiles,
# diagnostics, caches and temp files are deliberately excluded.
PUBLISH_ALLOWLIST = ("README.md", "TRAINING.md", "docs", "data", "writeups")

# Patterns that must never appear inside tracked data files.
FORBIDDEN_DATA_PATTERNS = re.compile(
    r"password|passwd|bearer|authorization|session[_-]?id|access[_-]?token|refresh[_-]?token|"
    r"cookie|\"(?:email|account[_-]?id|user[_-]?id|certificate[_-]?id|private[_-]?url)\"\s*:|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|flag\{|htb\{|thm\{|user\.txt|root\.txt|-----BEGIN",
    re.IGNORECASE,
)


class PlatformOutcome:
    """Lightweight per-platform result used by the sync engine."""

    def __init__(self, name: str, ok: bool, message: str, counts=None):
        self.name = name
        self.ok = ok
        self.message = message
        self.counts = counts or {}


def regenerate_readme() -> None:
    """Regenerate README.md and TRAINING.md from saved, validated local data only."""
    profile = read_json(PROFILE, {})
    profile_errors = validate_profile_data(profile)
    if profile_errors:
        raise SystemExit(
            "data/profile.json failed public schema validation: "
            + "; ".join(profile_errors)
        )
    rooms = read_json(ROOMS, {"rooms": []})
    badges = read_json(BADGES, {"badges": []})
    htb_data = read_optional_json(HACKTHEBOX, {})
    cisco_data = read_optional_json(CISCO_NETACAD, None)
    update_readme(
        render(profile, rooms, badges, htb_data, cisco_data),
        render_profile_snapshot(rooms, badges, profile),
        build_selected_projects_table(profile),
    )
    update_training_md(render_training(profile, rooms, badges, htb_data, cisco_data))


def sync_tryhackme_platform() -> PlatformOutcome:
    """Run the existing TryHackMe pipeline (rooms -> difficulty -> badges)."""
    try:
        import room_sync
        import room_difficulty_sync
        import badge_sync
    except ImportError as exc:
        return PlatformOutcome("TryHackMe", False, f"TryHackMe modules unavailable: {exc}")

    try:
        before = len(read_json(ROOMS, {"rooms": []}).get("rooms", []))
        room_sync.sync_rooms()
        room_difficulty_sync.sync_room_difficulties()
        badge_sync.sync_badges(publish=False)
        rooms = read_json(ROOMS, {"rooms": []}).get("rooms", [])
        badges = read_json(BADGES, {"badges": []}).get("badges", [])
        counts = {"rooms": len(rooms), "badges": len(badges), "rooms_added": max(0, len(rooms) - before)}
        return PlatformOutcome("TryHackMe", True, "TryHackMe sync complete.", counts)
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - report, do not crash the engine
        return PlatformOutcome("TryHackMe", False, f"TryHackMe sync failed: {exc}")


def sync_hackthebox_platform(interactive: bool) -> PlatformOutcome:
    """Run the Hack The Box sync via the platform module."""
    try:
        from platforms import hackthebox
    except ImportError as exc:
        return PlatformOutcome("Hack The Box", False, f"Hack The Box module unavailable: {exc}")
    result = hackthebox.sync(interactive=interactive)
    return PlatformOutcome("Hack The Box", result.ok, result.message, result.counts)


def sync_cisco_platform(interactive: bool) -> PlatformOutcome:
    """Run Cisco through its isolated module (offline foundation for now)."""
    try:
        from platforms import cisco_netacad
    except ImportError as exc:
        return PlatformOutcome("Cisco Networking Academy", False, f"Cisco module unavailable: {exc}")
    result = cisco_netacad.sync(interactive=interactive)
    return PlatformOutcome("Cisco Networking Academy", result.ok, result.message, result.counts)


def _git_paths_staged() -> list[str]:
    out = run_git("diff", "--cached", "--name-only", check=False)
    return [line for line in out.stdout.splitlines() if line.strip()]


def _privacy_and_safety_checks() -> list[str]:
    """Return a list of problems that must block a commit (empty means safe)."""
    problems = []
    staged = _git_paths_staged()
    for path in staged:
        if re.search(r"(^|/)\.(thm|htb|cisco)-browser(/|$)", path) or ".htb-diagnostics" in path \
                or ".htb-sync-cache" in path or path.endswith(".tmp"):
            problems.append(f"refusing to stage local artefact: {path}")
    # Scan staged data files for forbidden content.
    for path in staged:
        if path.startswith("data/") and path.endswith(".json"):
            full = ROOT / path
            if full.exists() and FORBIDDEN_DATA_PATTERNS.search(full.read_text(encoding="utf-8")):
                problems.append(f"forbidden pattern found in tracked data file: {path}")
    return problems


def publish_changes(commit_message: str) -> bool:
    """Stage only allow-listed paths, run safety checks, commit and push."""
    run_git("add", "--", *PUBLISH_ALLOWLIST)
    staged = run_git("diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        print("No repository changes to publish.")
        return False

    problems = _privacy_and_safety_checks()
    if problems:
        run_git("reset", check=False)
        print("Commit aborted by safety checks:")
        for problem in problems:
            print(f"  - {problem}")
        return False

    print("Staged files:")
    for path in _git_paths_staged():
        print(f"  {path}")

    run_git("commit", "-m", commit_message)
    run_git("push")
    head = run_git("rev-parse", "HEAD").stdout.strip()
    origin = run_git("rev-parse", "origin/main", check=False).stdout.strip()
    if head and head == origin:
        print("Pushed. HEAD matches origin/main.")
    else:
        print("Pushed, but HEAD/origin/main could not be confirmed equal.")
    return True


def _print_summary(requested, outcomes, changed_files):
    succeeded = [o.name for o in outcomes if o.ok]
    failed = [o.name for o in outcomes if not o.ok]
    print("\n=== Sync summary ===")
    print("Requested : " + ", ".join(requested))
    print("Succeeded : " + (", ".join(succeeded) or "none"))
    print("Failed    : " + (", ".join(failed) or "none"))
    for outcome in outcomes:
        detail = ", ".join(f"{k}={v}" for k, v in outcome.counts.items())
        print(f"  - {outcome.name}: {outcome.message}" + (f" ({detail})" if detail else ""))
    print("Files changed: " + (", ".join(changed_files) or "none"))


def _confirm(prompt: str) -> bool:
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


def run_sync(requested: list[str], interactive: bool, auto_push: bool) -> int:
    """Run the requested platform syncs, regenerate the README, offer to publish.

    Returns a process exit status: 0 if at least one requested platform
    succeeded (or render-only), 1 if every requested sync failed.
    """
    outcomes = []
    for platform in requested:
        print(f"\n>>> Syncing {platform}...", flush=True)
        if platform == "tryhackme":
            outcomes.append(sync_tryhackme_platform())
        elif platform == "hackthebox":
            outcomes.append(sync_hackthebox_platform(interactive))
        elif platform == "cisco":
            outcomes.append(sync_cisco_platform(interactive))

    # A wholly failed collection must not touch generated public output. In a
    # multi-platform run, successful platforms can still render while another
    # platform fails independently.
    if any(outcome.ok for outcome in outcomes):
        try:
            regenerate_readme()
        except SystemExit as exc:
            print(f"README regeneration failed: {exc}")
    else:
        print("Skipping README/TRAINING regeneration because every sync failed.")

    changed_files = [line.strip() for line in run_git("status", "--short", check=False).stdout.splitlines()]
    _print_summary(requested, outcomes, changed_files)

    any_ok = any(o.ok for o in outcomes)
    should_push = auto_push or (interactive and any_ok and _confirm("\nCommit and push these changes? [y/N] "))
    if should_push:
        publish_changes("Sync portfolio activity")
    elif not auto_push:
        print("Not committing (no confirmation).")

    return 0 if any_ok else 1


def interactive_menu() -> int:
    menu = (
        "\nCybersecurity Portfolio Sync\n"
        "1. TryHackMe\n"
        "2. Hack The Box\n"
        "3. Cisco Networking Academy\n"
        "4. All platforms\n"
        "5. Regenerate from saved data\n"
        "6. Exit\n"
    )
    mapping = {
        "1": ["tryhackme"],
        "2": ["hackthebox"],
        "3": ["cisco"],
        "4": list(PLATFORM_KEYS),
    }
    while True:
        print(menu)
        try:
            choice = input("Select an option [1-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0
        if choice in mapping:
            requested = mapping[choice]
            print(f"\nSelected: {', '.join(requested)}. A browser may open for login.")
            return run_sync(requested, interactive=True, auto_push=False)
        if choice == "5":
            try:
                regenerate_readme()
                print("README regenerated from saved data.")
            except SystemExit as exc:
                print(f"Regeneration failed: {exc}")
                return 1
            if _confirm("Commit and push the regenerated README? [y/N] "):
                publish_changes("Regenerate portfolio README")
            return 0
        if choice == "6":
            print("Exiting.")
            return 0
        print("Invalid selection. Please choose a number from 1 to 6.")


def cmd_sync(args) -> int:
    if args.platform:
        if args.platform == "all":
            requested = list(PLATFORM_KEYS)
        else:
            requested = [args.platform]
        return run_sync(requested, interactive=not args.non_interactive, auto_push=args.push)
    return interactive_menu()


def cmd_render(args) -> int:
    regenerate_readme()
    print("README regenerated from saved data.")
    if getattr(args, "push", False):
        publish_changes("Regenerate portfolio README")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Cybersecurity Portfolio Sync Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="interactive multi-platform sync menu")
    sync_parser.add_argument("--platform", choices=("tryhackme", "hackthebox", "cisco", "all"),
                             help="run a specific platform non-interactively (skips the menu)")
    sync_parser.add_argument("--non-interactive", action="store_true",
                             help="do not treat this as an interactive session")
    sync_parser.add_argument("--push", action="store_true",
                             help="commit and push after a successful sync (never pushes without this flag)")
    sync_parser.set_defaults(func=cmd_sync)

    render_parser = sub.add_parser("render", help="regenerate the README from saved data only")
    render_parser.add_argument("--push", action="store_true")
    render_parser.set_defaults(func=cmd_render)

    # Preserved legacy commands so existing TryHackMe workflows keep working.
    browser_parser = sub.add_parser("browser-sync")
    browser_parser.add_argument("--publish", action="store_true")
    browser_parser.set_defaults(func=browser_sync)
    room_parser = sub.add_parser("add-room")
    room_parser.add_argument("--name")
    room_parser.add_argument("--url")
    room_parser.add_argument("--difficulty")
    room_parser.add_argument("--completed")
    room_parser.set_defaults(func=add_room)

    args = parser.parse_args()
    try:
        result = args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)
    if isinstance(result, int) and args.command in ("sync", "render"):
        raise SystemExit(result)


if __name__ == "__main__":
    main()
