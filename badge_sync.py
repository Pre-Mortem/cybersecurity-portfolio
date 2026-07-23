#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re

from portfolio import (
    BADGES,
    BROWSER_STATE,
    PROFILE,
    ROOMS,
    read_json,
    render,
    run_git,
    slugify,
    update_readme,
    write_json,
)

BADGE_URL = "https://tryhackme.com/api/badges/mine"
PROFILE_URL = "https://tryhackme.com/p/PreMortem"


def display_name(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[-_.]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.title() or "Badge"


def normalise_badge(raw) -> dict | None:
    if isinstance(raw, str):
        code = raw.strip()
        if not code:
            return None
        return {"name": display_name(code), "code": code}

    if not isinstance(raw, dict):
        return None

    code = str(
        raw.get("code")
        or raw.get("badge")
        or raw.get("slug")
        or raw.get("id")
        or ""
    ).strip()
    name = str(raw.get("name") or raw.get("title") or "").strip()
    image = str(raw.get("image") or raw.get("imageUrl") or raw.get("imageURL") or "").strip()

    if not name and code:
        name = display_name(code)
    if not name:
        return None

    badge = {"name": name}
    if code:
        badge["code"] = code
    if image:
        badge["image"] = image
    return badge


def sync_badges(publish: bool) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    if not BROWSER_STATE.exists():
        raise SystemExit("No TryHackMe browser session exists. Run ./sync-tryhackme and log in first.")

    print("Reading badges from the authenticated TryHackMe session...")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=True,
            channel="chrome",
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
        response = context.request.get(BADGE_URL, timeout=30000)

        if not response.ok:
            status = response.status
            context.close()
            raise SystemExit(f"TryHackMe badge API returned HTTP {status}.")

        try:
            payload = response.json()
        except Exception as exc:
            context.close()
            raise SystemExit(f"TryHackMe badge API did not return JSON: {exc}")

        context.close()

    if not isinstance(payload, dict) or not payload.get("success", False):
        raise SystemExit("TryHackMe badge API did not report success. Your saved login may have expired.")

    raw_badges = payload.get("badges", [])
    if not isinstance(raw_badges, list):
        raise SystemExit("TryHackMe badge API returned an unexpected badge format.")

    badges = []
    for raw in raw_badges:
        badge = normalise_badge(raw)
        if badge:
            badges.append(badge)

    badge_map = {
        slugify(item.get("code") or item["name"]): item
        for item in badges
        if item.get("name")
    }
    badges_data = {
        "badges": sorted(badge_map.values(), key=lambda item: item["name"].lower())
    }
    write_json(BADGES, badges_data)

    profile = read_json(PROFILE, {})
    rooms = read_json(ROOMS, {"rooms": []})
    update_readme(render(profile, rooms, badges_data))

    print(f"Found {len(badges_data['badges'])} badge(s) through the authenticated badge API.")
    for badge in badges_data["badges"]:
        print(f"  + {badge['name']}")

    if publish:
        run_git("add", "README.md", "data", "writeups")
        staged = run_git("diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            print("No repository changes to publish.")
        else:
            run_git("commit", "-m", "Sync TryHackMe activity and badges")
            run_git("push")
            print("Committed and pushed the room and badge update.")

    return len(badges_data["badges"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Authenticated TryHackMe badge synchroniser")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    sync_badges(args.publish)


if __name__ == "__main__":
    main()
