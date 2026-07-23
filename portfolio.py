#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
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

    badge_lines = []
    for badge in badges.get("badges", [])[:12]:
        label = badge.get("name", "Badge").replace("|", "\\|")
        badge_lines.append(f"- {label}")
    if not badge_lines:
        badge_lines.append("- No badges recorded yet")

    return f"""{START}
## TryHackMe

**Profile:** [PreMortem](https://tryhackme.com/p/PreMortem)  
**Completed rooms recorded:** {len(rooms['rooms'])}  
**Badges recorded:** {len(badges.get('badges', []))}  
**Last local sync:** {profile.get('last_sync') or 'Not yet synced'}

### Recently Completed Rooms

| Room | Difficulty | Completed |
|---|---|---|
{chr(10).join(rows)}

### Badges

{chr(10).join(badge_lines)}

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


def browser_sync(args) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    BROWSER_STATE.mkdir(parents=True, exist_ok=True)
    profile_url = "https://tryhackme.com/p/PreMortem"
    discovered_rooms: list[dict] = []
    discovered_badges: list[dict] = []

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(profile_url, wait_until="domcontentloaded", timeout=90000)
        print("A separate Chrome window has opened for TryHackMe syncing.")
        print("Log into TryHackMe there if required, then return here and press Enter.")
        input()
        page.goto(profile_url, wait_until="networkidle", timeout=90000)

        if "/login" in page.url.lower() or page.locator("text=Login").count() > 0 and "PreMortem" not in page.content():
            context.close()
            raise SystemExit("TryHackMe still appears logged out. Run ./sync-tryhackme again and complete login.")

        for url in (
            profile_url,
            profile_url + "?tab=completed",
            profile_url + "?tab=rooms",
        ):
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(1500)
            candidates = scrape_cards(page, "a[href*='/room/']")
            for candidate in candidates:
                text = candidate.get("text", "").lower()
                if any(word in text for word in ("completed", "complete", "100%")) or "tab=completed" in url:
                    candidate["url"] = urljoin("https://tryhackme.com", candidate["url"])
                    room = normalise_room(candidate)
                    if room:
                        discovered_rooms.append(room)

        page.goto(profile_url + "?tab=badges", wait_until="networkidle", timeout=90000)
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(1500)
        for item in scrape_cards(page, "img"):
            text = re.sub(r"\s+", " ", item.get("text", "")).strip()
            image = item.get("image", "")
            if image and ("badge" in image.lower() or "badge" in text.lower()) and text:
                discovered_badges.append({"name": text[:120], "image": image})
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

    badge_map = {slugify(item["name"]): item for item in discovered_badges if item.get("name")}
    badges_data = {"badges": sorted(badge_map.values(), key=lambda item: item["name"].lower())}
    write_json(BADGES, badges_data)

    profile = read_json(PROFILE, {})
    profile.update({
        "username": "PreMortem",
        "profile_url": profile_url,
        "last_sync": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sync_method": "isolated-authenticated-browser",
    })
    write_json(PROFILE, profile)
    update_readme(render(profile, rooms_data, badges_data))

    print(f"Found {len(discovered_rooms)} completed-room candidates and {len(discovered_badges)} badge candidates.")
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
