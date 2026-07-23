#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.example.json"
ROOMS = ROOT / "data/rooms.json"
PROFILE = ROOT / "data/profile.json"
BADGES = ROOT / "data/badges.json"
README = ROOT / "README.md"
BROWSER_STATE = ROOT / ".thm-browser"
START = "<!-- THM:START -->"
END = "<!-- THM:END -->"
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


def build_badge_showcase(badges: list) -> str:
    """Return a GitHub-README-compatible HTML showcase of earned badges.

    Each badge is rendered image-over-name in its own centred table cell, with
    a fixed number of badges per row. Both the image and the name link to the
    TryHackMe profile (the badge data holds no per-badge URLs). Names are
    HTML-escaped. A badge without a valid http(s) image falls back to its name
    as a text link (no broken image). The showcase is generated entirely from
    the supplied data, so future badges appear automatically.
    """
    link = html.escape(PROFILE_URL, quote=True)
    cells = []
    for badge in badges:
        name = html.escape(str(badge.get("name") or "Badge"))
        image = str(badge.get("image") or "").strip()
        if image.lower().startswith(("http://", "https://")):
            src = html.escape(image, quote=True)
            inner = f'<img src="{src}" alt="{name}" width="100"><br>\n<strong>{name}</strong>'
        else:
            inner = f"<strong>{name}</strong>"
        cells.append(
            f'<td align="center" width="130">\n'
            f'<a href="{link}">\n{inner}\n</a>\n'
            f'</td>'
        )

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

    return f"""{START}
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


def update_readme(section: str) -> None:
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit("README is missing TryHackMe generated markers")
    README.write_text(pattern.sub(section, text), encoding="utf-8")


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
