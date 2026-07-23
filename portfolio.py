#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
EXAMPLE = ROOT / "config.example.json"
ROOMS = ROOT / "data/rooms.json"
PROFILE = ROOT / "data/profile.json"
README = ROOT / "README.md"
CARD = ROOT / "assets/tryhackme/public-profile.png"
START = "<!-- THM:START -->"
END = "<!-- THM:END -->"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def configure(_):
    if CONFIG.exists():
        print("config.json already exists")
        return
    shutil.copyfile(EXAMPLE, CONFIG)
    print("Created config.json. Add your TryHackMe details, then run: python3 portfolio.py sync")


def render(config, profile, rooms):
    thm = config["tryhackme"]
    username = thm.get("username") or "TryHackMe profile"
    profile_url = thm.get("public_profile_url", "")
    label = f"[{username}]({profile_url})" if profile_url else username
    rows = []
    for room in sorted(rooms["rooms"], key=lambda item: item["completed"], reverse=True)[:10]:
        name = room["name"].replace("|", "\\|")
        name = f"[{name}]({room['url']})" if room.get("url") else name
        rows.append(f"| {name} | {room.get('difficulty') or '—'} | {room['completed']} |")
    if not rows:
        rows.append("| No rooms recorded yet | — | — |")
    return f"""{START}
## TryHackMe

**Profile:** {label}  
**Recorded rooms:** {len(rooms['rooms'])}  
**Last sync:** {profile.get('last_sync') or 'Not yet synced'}

![TryHackMe public profile](assets/tryhackme/public-profile.png)

### Recently Recorded Rooms

| Room | Difficulty | Completed |
|---|---|---|
{chr(10).join(rows)}

The profile image is retrieved from TryHackMe's public badge endpoint. Room notes are recorded separately so this portfolio does not depend on an undocumented personal API.
{END}"""


def update_readme(section):
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    README.write_text(pattern.sub(section, text), encoding="utf-8")


def sync(_):
    if not CONFIG.exists():
        raise SystemExit("Run: python3 portfolio.py configure")
    config = read_json(CONFIG)
    user_id = config["tryhackme"].get("public_user_id", "").strip()
    if not user_id:
        raise SystemExit("Add tryhackme.public_user_id to config.json")
    url = "https://tryhackme.com/api/v2/badges/public-profile?userPublicId=" + urllib.parse.quote(user_id)
    request = urllib.request.Request(url, headers={"User-Agent": "cybersecurity-portfolio/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise SystemExit(f"TryHackMe sync failed: {exc}")
    if not body:
        raise SystemExit("TryHackMe returned an empty profile image")
    CARD.parent.mkdir(parents=True, exist_ok=True)
    CARD.write_bytes(body)
    profile = read_json(PROFILE)
    profile["last_sync"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    write_json(PROFILE, profile)
    update_readme(render(config, profile, read_json(ROOMS)))
    print("Updated TryHackMe profile card and README")


def add_room(args):
    name = args.name or input("Room name: ").strip()
    if not name:
        raise SystemExit("Room name is required")
    slug = slugify(name)
    data = read_json(ROOMS)
    if any(room["slug"] == slug for room in data["rooms"]):
        raise SystemExit("That room is already recorded")
    completed = args.completed or dt.date.today().isoformat()
    room = {
        "name": name,
        "slug": slug,
        "url": args.url or "",
        "difficulty": args.difficulty or "",
        "category": args.category or "",
        "completed": completed,
        "writeup": f"writeups/tryhackme/{slug}.md"
    }
    data["rooms"].append(room)
    write_json(ROOMS, data)
    path = ROOT / room["writeup"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""# {name}

- Platform: TryHackMe
- Completed: {completed}
- Room URL: {room['url'] or 'Not recorded'}
- Difficulty: {room['difficulty'] or 'Not recorded'}
- Category: {room['category'] or 'Not recorded'}

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
    if CONFIG.exists():
        update_readme(render(read_json(CONFIG), read_json(PROFILE), data))
    print(f"Added {name} and created {room['writeup']}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("configure")
    p.set_defaults(func=configure)
    p = sub.add_parser("sync")
    p.set_defaults(func=sync)
    p = sub.add_parser("add-room")
    p.add_argument("--name")
    p.add_argument("--url")
    p.add_argument("--difficulty")
    p.add_argument("--category")
    p.add_argument("--completed")
    p.set_defaults(func=add_room)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
