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

# Validated against the live authenticated session (2026-07-23):
#   /api/v2/users/badges?username=<user>  -> {"status":"success","data":[{"_id","name"}]}
#       ("name" is the badge slug; this is the list the account has actually earned)
#   /api/v2/badges                        -> {"status":"success","data":{"badges":[
#       {"name"(slug),"title","description","image","category",...]}}
#       (the global catalogue, used to enrich earned slugs with title/image)
# The old /api/badges/mine endpoint does not exist and returns the SPA HTML shell,
# which is why earlier runs recorded zero badges. A bare context.request.get() is
# rate-limited (HTTP 429) by the site's bot protection, so we mirror the SPA instead:
# load the profile page and read the JSON responses the page itself fetches.
EARNED_PATH = "/api/v2/users/badges"
CATALOG_PATH = "/api/v2/badges"
DEFAULT_USERNAME = "PreMortem"
PROFILE_URL_FALLBACK = "https://tryhackme.com/p/PreMortem"


def display_name(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[-_.]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.title() or "Badge"


def extract_earned(payload) -> list[dict] | None:
    """Return the list of earned badge records, or None if payload is not the
    expected success envelope."""
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None
    data = payload.get("data")
    if not isinstance(data, list):
        return None
    return data


def extract_catalog(payload) -> dict[str, dict]:
    """Map badge slug -> catalogue record ({title, image, category, ...})."""
    catalog: dict[str, dict] = {}
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return catalog
    data = payload.get("data")
    badges = data.get("badges") if isinstance(data, dict) else data
    if not isinstance(badges, list):
        return catalog
    for entry in badges:
        if isinstance(entry, dict) and entry.get("name"):
            catalog[str(entry["name"]).strip().lower()] = entry
    return catalog


def build_badge(earned: dict, catalog: dict[str, dict]) -> dict | None:
    slug = str(earned.get("name") or "").strip()
    if not slug:
        return None
    meta = catalog.get(slug.lower(), {})
    name = str(meta.get("title") or "").strip() or display_name(slug)
    badge = {"name": name, "code": slug}
    image = str(meta.get("image") or "").strip()
    if image:
        badge["image"] = image
    category = str(meta.get("category") or "").strip()
    if category:
        badge["category"] = category
    return badge


def collect_from_session(username: str, profile_url: str) -> tuple[list[dict] | None, dict[str, dict]]:
    """Load the authenticated profile page and read the badge JSON the SPA fetches.
    Falls back to an in-page fetch (which inherits the browser's anti-bot cookies)
    when the listener does not capture the responses."""
    from playwright.sync_api import sync_playwright

    earned_payload = None
    catalog_payload = None

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_STATE),
            headless=True,
            channel="chrome",
        )

        def on_response(response):
            nonlocal earned_payload, catalog_payload
            try:
                if response.request.resource_type not in {"xhr", "fetch"}:
                    return
                if "tryhackme.com" not in response.url:
                    return
                if "json" not in response.headers.get("content-type", ""):
                    return
                path = response.url
                if EARNED_PATH in path and earned_payload is None:
                    earned_payload = response.json()
                elif path.rstrip("/").endswith(CATALOG_PATH) and catalog_payload is None:
                    catalog_payload = response.json()
            except Exception:
                pass

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.on("response", on_response)
            page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            # Give the SPA time to issue its badge requests.
            for _ in range(10):
                page.wait_for_timeout(1000)
                if earned_payload is not None and catalog_payload is not None:
                    break

            # In-page fetch fallback (uses the browser's own fetch stack, so it
            # carries the session + anti-bot cookies that a bare request lacks).
            if earned_payload is None:
                earned_payload = page.evaluate(
                    """async (u) => {
                        try {
                            const r = await fetch(`/api/v2/users/badges?username=${encodeURIComponent(u)}`,
                                {credentials: 'include', headers: {accept: 'application/json'}});
                            if (!(r.headers.get('content-type') || '').includes('json')) return null;
                            return await r.json();
                        } catch (e) { return null; }
                    }""",
                    username,
                )
            if catalog_payload is None:
                catalog_payload = page.evaluate(
                    """async () => {
                        try {
                            const r = await fetch('/api/v2/badges',
                                {credentials: 'include', headers: {accept: 'application/json'}});
                            if (!(r.headers.get('content-type') || '').includes('json')) return null;
                            return await r.json();
                        } catch (e) { return null; }
                    }"""
                )
        finally:
            context.close()

    return extract_earned(earned_payload), extract_catalog(catalog_payload)


def sync_badges(publish: bool) -> int:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    if not BROWSER_STATE.exists():
        raise SystemExit("No TryHackMe browser session exists. Run ./sync-tryhackme and log in first.")

    profile = read_json(PROFILE, {})
    username = profile.get("username") or DEFAULT_USERNAME
    profile_url = profile.get("profile_url") or PROFILE_URL_FALLBACK

    print("Reading badges from the authenticated TryHackMe session...", flush=True)
    earned, catalog = collect_from_session(username, profile_url)

    if earned is None:
        # Do not clobber previously recorded badges on a failed read.
        raise SystemExit(
            "Could not read earned badges from the authenticated session "
            "(the badge API did not return the expected success payload). "
            "Existing data/badges.json has been left unchanged. "
            "Your saved login may have expired, or the site rate-limited the request."
        )

    badges = []
    for record in earned:
        badge = build_badge(record, catalog)
        if badge:
            badges.append(badge)

    badge_map = {slugify(item.get("code") or item["name"]): item for item in badges if item.get("name")}
    badges_data = {"badges": sorted(badge_map.values(), key=lambda item: item["name"].lower())}
    write_json(BADGES, badges_data)

    rooms = read_json(ROOMS, {"rooms": []})
    update_readme(render(profile, rooms, badges_data))

    print(f"Found {len(badges_data['badges'])} earned badge(s).", flush=True)
    for badge in badges_data["badges"]:
        code = badge.get("code", "")
        print(f"  + {badge['name']}" + (f" ({code})" if code else ""), flush=True)

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
