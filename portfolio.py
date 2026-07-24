#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.example.json"
ROOMS = ROOT / "data/rooms.json"
PROFILE = ROOT / "data/profile.json"
BADGES = ROOT / "data/badges.json"
HACKTHEBOX = ROOT / "data/hackthebox.json"
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
TRAINING_START = "<!-- TRAINING:START -->"
TRAINING_END = "<!-- TRAINING:END -->"
PROFILE_URL = "https://tryhackme.com/p/PreMortem"
REPO_URL = "https://github.com/Pre-Mortem/cybersecurity-portfolio"


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
        name = html.escape(str(badge.get("name") or "Badge"))
        image = str(badge.get("image") or "").strip()
        if image.lower().startswith(("http://", "https://")):
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


def md_cell(value) -> str:
    """Escape a value for safe use inside a Markdown table cell."""
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


# --- Qualifications (verified, static) -------------------------------------

QUALIFICATIONS = [
    {
        "title": "Certificate in Cyber Security Practices — Level 3",
        "reference": "603/5762/9",
        "provider": "Think Employment",
        "status": "In progress",
    },
]


def build_qualification_section() -> str:
    rows = "\n".join(
        f"| {md_cell(q['title'])} | {md_cell(q['reference'])} | "
        f"{md_cell(q['provider'])} | {md_cell(q['status'])} |"
        for q in QUALIFICATIONS
    )
    return (
        "## Qualifications\n\n"
        "| Qualification | Reference | Provider | Status |\n"
        "|---|---|---|---|\n"
        f"{rows}\n\n"
        "_Unit evidence, assignments and completed units will be added to this "
        "repository as the course progresses._"
    )


# --- Security projects (verified) ------------------------------------------
# Repository links are only included for repositories confirmed public. Private
# or non-public repositories are labelled accordingly and left unlinked.

PROJECTS = [
    {
        "name": "PacketPunch",
        "description": (
            "A modern open-source pentesting hardware and software platform "
            "focused on current wireless, network and embedded security technologies."
        ),
        "areas": ["pentesting hardware", "wireless security", "network visibility",
                  "embedded systems", "ESP32-P4"],
        "status": "In development",
        "repository": None,
        "visibility": "Private",
        "tagline": "Security tools with impact.",
    },
    {
        "name": "ESP32-S2 AI HID Typer",
        "description": (
            "An ESP32-S2-based wireless HID keyboard system with an Android client, "
            "dynamic device discovery, emergency stop controls and defensive input validation."
        ),
        "areas": ["embedded security", "USB HID", "ESP-IDF", "Android", "network discovery"],
        "status": "In development",
        "repository": None,           # verified PRIVATE on GitHub — no public link
        "visibility": "Private",
        "tagline": None,
    },
    {
        "name": "Cybersecurity Portfolio Automation",
        "description": (
            "A Python-based portfolio generator that synchronises training progress, "
            "badges and room difficulty data into a generated GitHub README."
        ),
        "areas": ["Python", "automation", "JSON", "GitHub", "data validation"],
        "status": "Active",
        "repository": REPO_URL,       # this repository (verified public)
        "visibility": "Public",
        "tagline": None,
    },
]


def build_projects_section() -> str:
    cards = []
    for project in PROJECTS:
        name = html.escape(project["name"])
        url = safe_url(project.get("repository"))
        heading = f"[{name}]({url})" if url else name
        repo_label = f"{project['visibility']} repository"
        lines = [
            f"**{heading}** — _{html.escape(project['status'])} · {repo_label}_",
            html.escape(project["description"]),
            "**Focus:** " + " · ".join(html.escape(area) for area in project["areas"]),
        ]
        if project.get("tagline"):
            lines.append(f"_{html.escape(project['tagline'])}_")
        cards.append("<br>\n".join(lines))
    body = "\n\n".join(cards)
    return (
        "## Security Projects\n\n"
        "Practical security engineering across hardware, embedded systems and automation.\n\n"
        f"{body}"
    )


# --- Skills matrix (evidence-backed) ---------------------------------------

def _rooms_matching(rooms: dict, keywords) -> list:
    names = []
    for room in rooms.get("rooms", []):
        low = str(room.get("name", "")).lower()
        if any(keyword in low for keyword in keywords):
            names.append(room.get("name", ""))
    return names


def _badge_name(badges: dict, code: str) -> str:
    for badge in badges.get("badges", []):
        if badge.get("code") == code:
            return str(badge.get("name") or "")
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
         "Portfolio generation and synchronisation scripts "
         "(portfolio.py, badge_sync.py, room_sync.py, room_difficulty_sync.py)"),
        ("Git and GitHub",
         "Version-controlled, automatically generated portfolio with JSON data validated in CI"),
        ("Embedded systems",
         "ESP32-S2 AI HID Typer and PacketPunch development"),
        ("Android",
         "Developing through the ESP32-S2 AI HID Typer Android client"),
        ("Security automation",
         "Automated TryHackMe room, badge and difficulty synchronisation"),
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
    stub_count = 0

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
                stub_count += 1

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

    header = "## Practical Labs and Reports\n\n"
    parts = []
    if completed_items:
        parts.append("**Completed Security Research & Reports**\n\n" + "\n".join(completed_items))
    else:
        parts.append("_Completed security research and practical reports will be featured here as completed._")

    if stub_count > 0:
        parts.append(
            f"_Note: {stub_count} room write-up stubs are maintained in [`writeups/tryhackme/`](writeups/tryhackme) "
            "as note-taking templates for completed TryHackMe rooms._"
        )

    return header + "\n\n".join(parts)


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

    identity = data.get("public_identity") if isinstance(data.get("public_identity"), dict) else {}
    username = html.escape(str(identity.get("username") or "PreMortem").strip())
    profile_url = safe_url(identity.get("profile_url")) or "https://htb.site/PreMortem"
    totals = _htb_totals(data)

    header = "### Hack The Box Summary\n\n"
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


def build_cisco_summary() -> str:
    return (
        "### Cisco Networking Academy Summary\n\n"
        "**Status:** Integration planned (Roadmap item)<br>\n"
        "_Public identity protection enabled by default. Only non-identifying achievement details "
        "(course title, completion status, date, badge, skills) will be published. "
        "See [docs/ROADMAP.md](docs/ROADMAP.md) for details._"
    )


def build_portfolio_stats(rooms: dict, badges: dict, htb_data: dict | None = None) -> str:
    if htb_data is None:
        htb_data = read_optional_json(HACKTHEBOX, {})
    room_count = len(rooms.get("rooms", []))
    badge_count = len(badges.get("badges", []))

    htb_machines = len(_htb_list(htb_data, "labs", "machines"))
    htb_sherlocks = len(_htb_list(htb_data, "labs", "sherlocks"))
    htb_total_labs = htb_machines + htb_sherlocks

    writeup_stubs = 0
    writeups_dir = ROOT / "writeups"
    if writeups_dir.exists():
        writeup_stubs = len([p for p in writeups_dir.rglob("*.md") if "templates" not in p.parts])

    return (
        "## Portfolio Statistics\n\n"
        "| Category | Recorded Count | Description |\n"
        "|---|---|---|\n"
        f"| TryHackMe Rooms | {room_count} | Completed hands-on training rooms |\n"
        f"| TryHackMe Badges | {badge_count} | Earned achievement badges |\n"
        f"| Hack The Box Labs | {htb_total_labs} | Completed Machines and Sherlocks |\n"
        f"| Practical Write-up Stubs | {writeup_stubs} | Maintained lab notes and template stubs |\n"
        "| Security Projects | 3 | Hardware, embedded systems, and security automation |"
    )


def build_sync_engine_note() -> str:
    return (
        "## Automated Sync Engine\n\n"
        "This portfolio is maintained using a custom local Python synchronisation tool "
        "that collects and validates training evidence from supported cybersecurity platforms. "
        "For complete architecture, CLI usage, privacy rules, and local session management, "
        "see [docs/SYNC_ENGINE.md](docs/SYNC_ENGINE.md)."
    )


def build_contact_section() -> str:
    return (
        "## Contact & Profiles\n\n"
        "- **GitHub**: [github.com/Pre-Mortem](https://github.com/Pre-Mortem)\n"
        "- **TryHackMe**: [tryhackme.com/p/PreMortem](https://tryhackme.com/p/PreMortem)\n"
        "- **Hack The Box**: [htb.site/PreMortem](https://htb.site/PreMortem)"
    )


def build_tryhackme_detailed(profile: dict, rooms: dict, badges: dict) -> str:
    rows = []
    ordered = sorted(rooms.get("rooms", []), key=lambda item: item.get("completed", ""), reverse=True)
    for room in ordered:
        name = room.get("name", "").replace("|", "\\|")
        if room.get("url"):
            name = f"[{name}]({room['url']})"
        rows.append(f"| {name} | {room.get('difficulty') or '—'} | {room.get('completed', '—')} |")
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


def build_cisco_detailed() -> str:
    return (
        "## Cisco Networking Academy\n\n"
        "Cisco Networking Academy progress has not been added yet. When integrated, "
        "this section will display course titles, completion status, badges, and completion dates "
        "without publishing real names or account holder credentials."
    )


def render(profile: dict, rooms: dict, badges: dict, htb_data: dict | None = None) -> str:
    if htb_data is None:
        htb_data = read_optional_json(HACKTHEBOX, {})

    sections = [
        build_qualification_section(),
        build_projects_section(),
        build_skills_section(rooms, badges),
        build_evidence_section(),
        "## Training Platforms\n\n" + "\n\n".join([
            build_tryhackme_summary(profile, rooms, badges),
            build_hackthebox_summary(htb_data),
            build_cisco_summary(),
        ]),
        build_portfolio_stats(rooms, badges, htb_data),
        build_sync_engine_note(),
        build_contact_section(),
    ]
    return GEN_START + "\n" + "\n\n".join(sections) + "\n" + GEN_END


def render_training(profile: dict, rooms: dict, badges: dict, htb_data: dict | None = None) -> str:
    if htb_data is None:
        htb_data = read_optional_json(HACKTHEBOX, {})

    sections = [
        build_tryhackme_detailed(profile, rooms, badges),
        build_hackthebox_section(htb_data),
        build_cisco_detailed(),
    ]
    return TRAINING_START + "\n" + "\n\n".join(sections) + "\n" + TRAINING_END


def update_readme(section: str) -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(GEN_START) + r".*?" + re.escape(GEN_END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README is missing portfolio generated markers")
    README.write_text(pattern.sub(lambda _match: section, text), encoding="utf-8")


def update_training_md(section: str) -> None:
    if not TRAINING_MD.exists():
        initial = (
            "# Cybersecurity Training History — PreMortem\n\n"
            "Detailed training activity maintained automatically by the "
            "[Cybersecurity Portfolio Sync Engine](docs/SYNC_ENGINE.md).\n\n"
            f"{TRAINING_START}\n{TRAINING_END}\n"
        )
        TRAINING_MD.write_text(initial, encoding="utf-8")
    text = TRAINING_MD.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(TRAINING_START) + r".*?" + re.escape(TRAINING_END), re.DOTALL)
    if not pattern.search(text):
        initial = (
            "# Cybersecurity Training History — PreMortem\n\n"
            "Detailed training activity maintained automatically by the "
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


def scrape_cards(page, selector: str) -> list[dict]:
    return page.locator(selector).evaluate_all("""elements => elements.map(el => {
      const anchor = el.closest('a') || el.querySelector('a');
      const text = (el.innerText || anchor?.innerText || '').trim();
      const href = anchor?.href || '';
      const image = el.querySelector('img');
      return {name: text.split('\\n')[0].trim(), text, url: href, image: image?.src || ''};
    })""")


def load_page(page, url: str, label: str) -> None:
    print(f"Loading {label}...", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    print(f"Loaded {label}.", flush=True)


def browser_sync(args) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    BROWSER_STATE.mkdir(parents=True, exist_ok=True)
    profile_url = "https://tryhackme.com/p/PreMortem"
    discovered_rooms: list[dict] = []

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        load_page(page, profile_url, "TryHackMe profile")
        print("A separate Chrome window has opened for TryHackMe syncing.", flush=True)
        print("Log into TryHackMe there if required, then return here and press Enter.", flush=True)
        input()
        print("Continuing sync...", flush=True)
        load_page(page, profile_url, "authenticated profile")

        page_text = page.locator("body").inner_text(timeout=10000)
        if "/login" in page.url.lower() or ("Login" in page_text and "PreMortem" not in page_text):
            context.close()
            raise SystemExit("TryHackMe still appears logged out. Run ./sync-tryhackme again and complete login.")

        room_pages = (
            (profile_url, "profile rooms"),
            (profile_url + "?tab=completed", "completed rooms"),
            (profile_url + "?tab=rooms", "rooms tab"),
        )
        for url, label in room_pages:
            load_page(page, url, label)
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)
            candidates = scrape_cards(page, "a[href*='/room/']")
            print(f"Found {len(candidates)} room links on {label}.", flush=True)
            for candidate in candidates:
                text = candidate.get("text", "").lower()
                if any(word in text for word in ("completed", "complete", "100%")) or "tab=completed" in url:
                    candidate["url"] = urljoin("https://tryhackme.com", candidate["url"])
                    room = normalise_room(candidate)
                    if room:
                        discovered_rooms.append(room)

        # Badges are collected separately and reliably by badge_sync.py against the
        # authenticated /api/v2/users/badges endpoint. Scraping the badges tab here
        # was unreliable (it found nothing and could hang closing the browser), so
        # room collection no longer touches badge data.
        context.close()

    rooms_data = read_json(ROOMS, {"rooms": []})
    existing = {room["slug"] for room in rooms_data["rooms"]}
    added = []
    for room in {item["slug"]: item for item in discovered_rooms}.values():
        if room["slug"] not in existing:
            rooms_data["rooms"].append(room)
            writeup_for(room)
            existing.add(room["slug"])
            added.append(room)
    write_json(ROOMS, rooms_data)

    # Preserve badges recorded by badge_sync.py; room collection must not clobber them.
    badges_data = read_json(BADGES, {"badges": []})

    profile = read_json(PROFILE, {})
    profile.update({
        "username": "PreMortem",
        "profile_url": profile_url,
        "last_sync": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sync_method": "isolated-authenticated-browser",
    })
    write_json(PROFILE, profile)
    regenerate_readme()

    print(f"Found {len(discovered_rooms)} completed-room candidates.")
    print(f"Added {len(added)} new room(s).")
    for room in added:
        print(f"  + {room['name']}")

    if args.publish:
        run_git("add", "--", *PUBLISH_ALLOWLIST)
        staged = run_git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            print("No repository changes to publish.")
        else:
            run_git("commit", "-m", f"Sync TryHackMe activity ({dt.date.today().isoformat()})")
            run_git("push")
            print("Committed and pushed the update.")
    return len(added)


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

PLATFORM_KEYS = ("tryhackme", "hackthebox")

# Files the automated commit flow is ever allowed to stage. Browser profiles,
# diagnostics, caches and temp files are deliberately excluded.
PUBLISH_ALLOWLIST = ("README.md", "TRAINING.md", "docs", "data", "writeups")

# Patterns that must never appear inside tracked data files.
FORBIDDEN_DATA_PATTERNS = re.compile(
    r"password|passwd|bearer|authorization|session[_-]?id|flag\{|htb\{|thm\{|user\.txt|root\.txt|-----BEGIN",
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
    rooms = read_json(ROOMS, {"rooms": []})
    badges = read_json(BADGES, {"badges": []})
    htb_data = read_optional_json(HACKTHEBOX, {})
    update_readme(render(profile, rooms, badges, htb_data))
    update_training_md(render_training(profile, rooms, badges, htb_data))


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


def _git_paths_staged() -> list[str]:
    out = run_git("diff", "--cached", "--name-only", check=False)
    return [line for line in out.stdout.splitlines() if line.strip()]


def _privacy_and_safety_checks() -> list[str]:
    """Return a list of problems that must block a commit (empty means safe)."""
    problems = []
    staged = _git_paths_staged()
    for path in staged:
        if re.search(r"(^|/)\.(thm|htb)-browser(/|$)", path) or ".htb-diagnostics" in path \
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

    # Always regenerate from whatever valid saved data now exists.
    try:
        regenerate_readme()
    except SystemExit as exc:
        print(f"README regeneration failed: {exc}")

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
        "3. Both platforms\n"
        "4. Regenerate from saved data\n"
        "5. Exit\n"
    )
    mapping = {
        "1": ["tryhackme"],
        "2": ["hackthebox"],
        "3": ["tryhackme", "hackthebox"],
    }
    while True:
        print(menu)
        try:
            choice = input("Select an option [1-5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0
        if choice in mapping:
            requested = mapping[choice]
            print(f"\nSelected: {', '.join(requested)}. A browser may open for login.")
            return run_sync(requested, interactive=True, auto_push=False)
        if choice == "4":
            try:
                regenerate_readme()
                print("README regenerated from saved data.")
            except SystemExit as exc:
                print(f"Regeneration failed: {exc}")
                return 1
            if _confirm("Commit and push the regenerated README? [y/N] "):
                publish_changes("Regenerate portfolio README")
            return 0
        if choice == "5":
            print("Exiting.")
            return 0
        print("Invalid selection. Please choose a number from 1 to 5.")


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
    sync_parser.add_argument("--platform", choices=("tryhackme", "hackthebox", "all"),
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
