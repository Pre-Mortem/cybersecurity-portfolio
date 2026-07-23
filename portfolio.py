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
BROWSER_STATE = ROOT / ".thm-browser"
START = "<!-- THM:START -->"
END = "<!-- THM:END -->"
# Outer markers delimiting the whole generated portfolio body. The TryHackMe
# START/END markers stay nested inside this region so TryHackMe sync tooling is
# unaffected.
GEN_START = "<!-- PORTFOLIO:START -->"
GEN_END = "<!-- PORTFOLIO:END -->"
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


def _read_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return ""


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
    groups = {label: [] for label, _ in EVIDENCE_GROUPS}

    # Auto-discover lab write-ups that actually exist in the repository.
    writeups_dir = ROOT / "writeups"
    if writeups_dir.exists():
        for path in sorted(writeups_dir.rglob("*.md")):
            title = _read_title(path) or path.stem
            rel = path.relative_to(ROOT).as_posix()
            groups["Lab write-ups"].append(_evidence_link(title, rel))

    # Merge an optional manifest of further evidence (validated file paths / links).
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
                    groups[label].append(_evidence_link(title, target))

    blocks = []
    for label, _ in EVIDENCE_GROUPS:
        items = groups[label]
        if not items:
            continue
        listing = "\n".join(items)
        if label == "Lab write-ups" and len(items) > 6:
            blocks.append(
                f"**{label}**\n\n"
                f"<details>\n<summary>{len(items)} documents</summary>\n\n"
                f"{listing}\n\n</details>"
            )
        else:
            blocks.append(f"**{label}**\n\n{listing}")

    header = "## Practical Labs and Reports\n\n"
    if not blocks:
        return header + "Practical reports and lab evidence will be added as work is completed."
    intro = "Evidence drawn from documents that exist in this repository.\n\n"
    return header + intro + "\n\n".join(blocks)


# --- Hack The Box (future-ready, no invented data) -------------------------

HTB_CATEGORIES = [
    ("Machines", "machines"),
    ("Sherlocks", "sherlocks"),
    ("Challenges", "challenges"),
    ("Academy modules", "academy_modules"),
]


def build_hackthebox_section() -> str:
    data = read_optional_json(HACKTHEBOX, {})
    if not isinstance(data, dict):
        data = {}

    counts = []
    total = 0
    for label, key in HTB_CATEGORIES:
        value = data.get(key)
        count = len(value) if isinstance(value, list) else 0
        counts.append((label, count))
        total += count
    profile = safe_url(data.get("profile_url"))

    header = "## Hack The Box\n\n"
    if total == 0 and not profile:
        return header + (
            "Hack The Box progress has not been added yet. This section will track "
            "Machines, Sherlocks, Challenges and Academy modules as they are completed."
        )

    labels = " | ".join(label for label, _ in counts)
    values = " | ".join(str(count) for _, count in counts)
    table = (
        f"| {labels} |\n"
        f"|{'---|' * len(counts)}\n"
        f"| {values} |"
    )
    profile_line = f"**Profile:** {profile}\n\n" if profile else ""
    return header + profile_line + table + "\n\n_Current recorded totals._"


def render(profile: dict, rooms: dict, badges: dict) -> str:
    rows = []
    ordered = sorted(rooms["rooms"], key=lambda item: item.get("completed", ""), reverse=True)
    for room in ordered[:10]:
        name = room["name"].replace("|", "\\|")
        if room.get("url"):
            name = f"[{name}]({room['url']})"
        rows.append(f"| {name} | {room.get('difficulty') or '—'} | {room['completed']} |")
    if not rows:
        rows.append("| No rooms recorded yet | — | — |")

    badge_showcase = build_badge_showcase(badges.get("badges", []))
    progress_summary = build_progress_summary(rooms, badges)
    milestones = build_milestones(len(rooms["rooms"]))
    last_sync = format_sync_timestamp(profile.get("last_sync"))

    tryhackme = f"""{START}
## TryHackMe

**Profile:** [PreMortem]({PROFILE_URL})<br>
**Last local sync:** {last_sync}

{progress_summary}

### Recently Completed Rooms

| Room | Difficulty | Completed |
|---|---|---|
{chr(10).join(rows)}

### Achievement Cabinet

A growing collection of achievements earned through completed TryHackMe rooms and learning paths.

{badge_showcase}

### Room Milestones

_Portfolio progress milestones — a personal tracker, not official TryHackMe badges._

{milestones}

This section is generated locally from my authenticated TryHackMe profile. Browser cookies remain on my own computer and are excluded from Git.
{END}"""

    sections = [
        build_qualification_section(),
        build_projects_section(),
        build_skills_section(rooms, badges),
        build_evidence_section(),
        build_hackthebox_section(),
        tryhackme,
    ]
    return GEN_START + "\n" + "\n\n".join(sections) + "\n" + GEN_END


def update_readme(section: str) -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(GEN_START) + r".*?" + re.escape(GEN_END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README is missing portfolio generated markers")
    README.write_text(pattern.sub(lambda _match: section, text), encoding="utf-8")


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
    update_readme(render(profile, rooms_data, badges_data))

    print(f"Found {len(discovered_rooms)} completed-room candidates.")
    print(f"Added {len(added)} new room(s).")
    for room in added:
        print(f"  + {room['name']}")

    if args.publish:
        run_git("add", "README.md", "data", "writeups")
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
    update_readme(render(read_json(PROFILE, {}), data, read_json(BADGES, {"badges": []})))
    print(f"Added {name}")


def main():
    parser = argparse.ArgumentParser(description="TryHackMe portfolio updater")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("browser-sync")
    sync_parser.add_argument("--publish", action="store_true")
    sync_parser.set_defaults(func=browser_sync)
    room_parser = sub.add_parser("add-room")
    room_parser.add_argument("--name")
    room_parser.add_argument("--url")
    room_parser.add_argument("--difficulty")
    room_parser.add_argument("--completed")
    room_parser.set_defaults(func=add_room)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
