#!/usr/bin/env python3

from __future__ import annotations

import json
import re

from portfolio import (
    BADGES,
    BROWSER_STATE,
    PROFILE,
    ROOMS,
    read_json,
    render,
    update_readme,
    write_json,
)

# Validated against the live session (2026-07-23): the authoritative source is
#   /api/v2/rooms/details?roomCode=<slug>  ->  {"status":"success","data":{"difficulty": "easy"|"info"|...}}
# TryHackMe reports "info" for informational rooms (e.g. Careers in Cyber), which
# is a real tier, not a missing value — so it is recognised here.
ROOM_DETAILS_PATH = "/api/v2/rooms/details"

KNOWN_DIFFICULTIES = {
    "info": "Info",
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "insane": "Insane",
}


def normalise_difficulty(value) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip().lower()
    for key, label in KNOWN_DIFFICULTIES.items():
        if text == key or re.search(rf"\b{re.escape(key)}\b", text):
            return label
    return ""


def find_difficulty(value) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"difficulty", "level", "complexity"}:
                found = normalise_difficulty(item)
                if found:
                    return found
        for item in value.values():
            found = find_difficulty(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_difficulty(item)
            if found:
                return found
    return ""


def details_difficulty(payload) -> str:
    """Read data.difficulty from a /api/v2/rooms/details success envelope."""
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return ""
    data = payload.get("data")
    if isinstance(data, dict):
        return normalise_difficulty(data.get("difficulty"))
    return ""


def difficulty_from_page(page, captured: list, slug: str) -> str:
    # 1. Authoritative source: the room's own /api/v2/rooms/details response,
    #    matched to THIS room's code so a sibling request (e.g. a "next room"
    #    recommendation) can never leak the wrong difficulty.
    slug_l = slug.lower()
    for url, payload in reversed(captured):
        if ROOM_DETAILS_PATH in url and f"roomcode={slug_l}" in url.lower():
            found = details_difficulty(payload)
            if found:
                return found
    for url, payload in reversed(captured):
        if ROOM_DETAILS_PATH in url:
            found = details_difficulty(payload)
            if found:
                return found

    # 2. Fetch the details endpoint directly from within the page (inherits the
    #    browser's session + anti-bot cookies that a bare request lacks).
    try:
        payload = page.evaluate(
            """async (code) => {
                try {
                    const r = await fetch(`/api/v2/rooms/details?roomCode=${encodeURIComponent(code)}`,
                        {credentials: 'include', headers: {accept: 'application/json'}});
                    if (!(r.headers.get('content-type') || '').includes('json')) return null;
                    return await r.json();
                } catch (e) { return null; }
            }""",
            slug,
        )
        found = details_difficulty(payload)
        if found:
            return found
    except Exception:
        pass

    for selector in (
        "[data-testid*='difficulty' i]",
        "[class*='difficulty' i]",
        "[aria-label*='difficulty' i]",
    ):
        locator = page.locator(selector)
        for index in range(min(locator.count(), 20)):
            found = normalise_difficulty(locator.nth(index).inner_text(timeout=2000))
            if found:
                return found

    for script in page.locator("script[type='application/ld+json'], script#__NEXT_DATA__").all():
        try:
            payload = json.loads(script.text_content(timeout=2000) or "")
        except Exception:
            continue
        found = find_difficulty(payload)
        if found:
            return found

    try:
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""

    patterns = (
        r"Difficulty\s*[:\n-]?\s*(Info|Easy|Medium|Hard|Insane)\b",
        r"\b(Info|Easy|Medium|Hard|Insane)\s+Difficulty\b",
    )
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return normalise_difficulty(match.group(1))
    return ""


def sync_room_difficulties() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    if not BROWSER_STATE.exists():
        raise SystemExit("No TryHackMe browser session exists. Run ./sync-tryhackme and log in first.")

    rooms_data = read_json(ROOMS, {"rooms": []})
    pending = [room for room in rooms_data.get("rooms", []) if room.get("url") and not room.get("difficulty")]

    if not pending:
        print("All recorded rooms already have difficulty metadata.", flush=True)
        return 0

    print(f"Backfilling difficulty for {len(pending)} room(s)...", flush=True)
    updated = 0

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=True,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()

        for index, room in enumerate(pending, start=1):
            captured = []

            def capture(response):
                try:
                    if response.request.resource_type in {"xhr", "fetch"} and "tryhackme.com" in response.url:
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            captured.append((response.url, response.json()))
                except Exception:
                    pass

            page.on("response", capture)
            print(f"[{index}/{len(pending)}] Reading {room['name']}...", flush=True)
            try:
                page.goto(room["url"], wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                difficulty = difficulty_from_page(page, captured, room.get("slug", ""))
            except Exception as exc:
                print(f"  Could not read room: {exc}", flush=True)
                difficulty = ""
            finally:
                page.remove_listener("response", capture)

            if difficulty:
                room["difficulty"] = difficulty
                updated += 1
                print(f"  Difficulty: {difficulty}", flush=True)
            else:
                print("  Difficulty was not exposed by the page or its API responses.", flush=True)

        context.close()

    write_json(ROOMS, rooms_data)
    profile = read_json(PROFILE, {})
    badges = read_json(BADGES, {"badges": []})
    update_readme(render(profile, rooms_data, badges))
    print(f"Updated difficulty for {updated} room(s).", flush=True)
    return updated


if __name__ == "__main__":
    sync_room_difficulties()
