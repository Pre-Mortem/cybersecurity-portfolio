#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
from urllib.parse import urljoin

from portfolio import (
    BADGES,
    BROWSER_STATE,
    PROFILE,
    ROOMS,
    normalise_room,
    read_json,
    render,
    scrape_cards,
    update_readme,
    write_json,
    writeup_for,
)

PROFILE_URL = "https://tryhackme.com/p/PreMortem"


def load_page(page, url: str, label: str) -> None:
    print(f"Loading {label}...", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    print(f"Loaded {label}.", flush=True)


def sync_rooms() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    BROWSER_STATE.mkdir(parents=True, exist_ok=True)
    discovered_rooms: list[dict] = []

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=False,
            channel="chrome",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        load_page(page, PROFILE_URL, "TryHackMe profile")
        print("A separate Chrome window has opened for TryHackMe syncing.", flush=True)
        print("Log into TryHackMe there if required, then return here and press Enter.", flush=True)
        input()
        print("Continuing sync...", flush=True)
        load_page(page, PROFILE_URL, "authenticated profile")

        page_text = page.locator("body").inner_text(timeout=10000)
        if "/login" in page.url.lower() or ("Login" in page_text and "PreMortem" not in page_text):
            context.close()
            raise SystemExit("TryHackMe still appears logged out. Run the sync again and complete login.")

        room_pages = (
            (PROFILE_URL, "profile rooms"),
            (PROFILE_URL + "?tab=completed", "completed rooms"),
            (PROFILE_URL + "?tab=rooms", "rooms tab"),
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

        print("Room collection complete. Closing the interactive browser...", flush=True)
        context.close()

    rooms_data = read_json(ROOMS, {"rooms": []})
    existing_by_slug = {room["slug"]: room for room in rooms_data["rooms"]}
    added = []

    for room in {item["slug"]: item for item in discovered_rooms}.values():
        existing = existing_by_slug.get(room["slug"])
        if existing is None:
            rooms_data["rooms"].append(room)
            existing_by_slug[room["slug"]] = room
            writeup_for(room)
            added.append(room)
        else:
            existing["name"] = room["name"]
            existing["url"] = room["url"]

    write_json(ROOMS, rooms_data)

    profile = read_json(PROFILE, {})
    profile.update({
        "username": "PreMortem",
        "profile_url": PROFILE_URL,
        "last_sync": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "sync_method": "isolated-authenticated-browser",
    })
    write_json(PROFILE, profile)

    badges = read_json(BADGES, {"badges": []})
    update_readme(render(profile, rooms_data, badges))

    print(f"Found {len(discovered_rooms)} completed-room candidates.")
    print(f"Added {len(added)} new room(s).")
    for room in added:
        print(f"  + {room['name']}")

    return len(added)


if __name__ == "__main__":
    sync_rooms()
