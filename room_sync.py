#!/usr/bin/env python3

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Callable

from portfolio import (
    BROWSER_STATE,
    PROFILE,
    ROOMS,
    read_json,
    regenerate_readme,
    write_json,
    writeup_for,
)

PROFILE_URL = "https://tryhackme.com/p/PreMortem"
COMPLETED_ROOMS_PATH = "/api/v2/public-profile/completed-rooms"
COMPLETED_ROOMS_PAGE_LIMIT = 16
MAX_COMPLETED_ROOM_PAGES = 100
VALID_ROOM_CODE = re.compile(r"^[A-Za-z0-9_-]+$")


class RoomCollectionError(RuntimeError):
    """Raised when TryHackMe does not return a complete, validated room set."""


@dataclass(frozen=True)
class CollectionDiagnostics:
    pages_loaded: int
    records_inspected: int
    expected_total: int
    unique_rooms: int
    fallback_dates: int


def load_page(page, url: str, label: str) -> None:
    print(f"Loading {label}: {url}", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3000)
    print(f"Loaded {label}.", flush=True)


def _completion_date(value, fallback_date: dt.date) -> tuple[str, str]:
    """Return an ISO date and its provenance.

    TryHackMe's completed-room endpoint currently omits completion timestamps.
    Timestamp fields are still honoured if the API starts returning one. A
    clearly labelled sync-date fallback is used only when no genuine date is
    exposed.
    """
    text = str(value or "").strip()
    if text:
        iso_candidate = text[:10]
        try:
            return dt.date.fromisoformat(iso_candidate).isoformat(), "tryhackme"
        except ValueError:
            pass

        relative = text.casefold()
        if relative == "today":
            return fallback_date.isoformat(), "tryhackme-relative"
        if relative == "yesterday":
            return (fallback_date - dt.timedelta(days=1)).isoformat(), "tryhackme-relative"
        match = re.fullmatch(r"(\d{1,3})\s+days?\s+ago", relative)
        if match:
            days = int(match.group(1))
            return (fallback_date - dt.timedelta(days=days)).isoformat(), "tryhackme-relative"

    return fallback_date.isoformat(), "sync-date-fallback"


def _room_from_api(record: dict, fallback_date: dt.date) -> dict | None:
    if not isinstance(record, dict):
        return None
    title = re.sub(r"\s+", " ", str(record.get("title") or "")).strip()
    code = str(record.get("code") or "").strip()
    if not title or len(title) > 120 or not VALID_ROOM_CODE.fullmatch(code):
        return None

    completed_value = next(
        (
            record.get(key)
            for key in (
                "completedAt",
                "completed_at",
                "completionDate",
                "completedDate",
                "completed",
            )
            if record.get(key)
        ),
        None,
    )
    completed, completion_date_source = _completion_date(
        completed_value, fallback_date
    )
    difficulty = re.sub(
        r"\s+", " ", str(record.get("difficulty") or "")
    ).strip().title()
    slug = code.casefold()
    return {
        "name": title,
        "slug": slug,
        "url": f"https://tryhackme.com/room/{slug}",
        "difficulty": difficulty,
        "category": "",
        "completed": completed,
        "completion_date_source": completion_date_source,
        "writeup": f"writeups/tryhackme/{slug}.md",
        "source": "authenticated-completed-rooms-api",
    }


def _parse_completed_page(payload) -> tuple[list[dict], dict]:
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RoomCollectionError(
            "the completed-room API did not return a success envelope"
        )
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise RoomCollectionError(
            "the completed-room API response is missing its data.docs list"
        )

    integer_fields = ("totalDocs", "page", "totalPages")
    for field in integer_fields:
        if not isinstance(data.get(field), int) or data[field] < 0:
            raise RoomCollectionError(
                f"the completed-room API returned an invalid {field}"
            )
    if data["page"] < 1 or data["totalPages"] < 0:
        raise RoomCollectionError(
            "the completed-room API returned invalid pagination metadata"
        )
    next_page = data.get("nextPage")
    if next_page is not None and (
        not isinstance(next_page, int) or next_page <= data["page"]
    ):
        raise RoomCollectionError(
            "the completed-room API returned an invalid nextPage"
        )
    if data.get("hasNextPage") and next_page is None:
        raise RoomCollectionError(
            "the completed-room API claims another page but omitted nextPage"
        )
    return data["docs"], data


def collect_paginated_rooms(
    fetch_page: Callable[[int, int], dict],
    fallback_date: dt.date,
) -> tuple[list[dict], CollectionDiagnostics]:
    """Collect every completed-room API page and reject partial results."""
    page_number = 1
    visited_pages: set[int] = set()
    records_inspected = 0
    expected_total: int | None = None
    rooms_by_slug: dict[str, dict] = {}

    while page_number is not None:
        if page_number in visited_pages or len(visited_pages) >= MAX_COMPLETED_ROOM_PAGES:
            raise RoomCollectionError(
                "completed-room pagination looped or exceeded the safety limit"
            )
        visited_pages.add(page_number)
        payload = fetch_page(page_number, COMPLETED_ROOMS_PAGE_LIMIT)
        records, metadata = _parse_completed_page(payload)

        current_total = metadata["totalDocs"]
        if expected_total is None:
            expected_total = current_total
        elif current_total != expected_total:
            raise RoomCollectionError(
                "completed-room total changed while pagination was in progress"
            )

        records_inspected += len(records)
        for record in records:
            room = _room_from_api(record, fallback_date)
            if room:
                rooms_by_slug[room["slug"]] = room

        page_number = metadata.get("nextPage")

    expected_total = expected_total or 0
    if records_inspected < expected_total:
        raise RoomCollectionError(
            "completed-room pagination was incomplete "
            f"(API total {expected_total}, inspected {records_inspected})"
        )
    if len(rooms_by_slug) != expected_total:
        raise RoomCollectionError(
            "completed-room records were duplicated or malformed "
            f"(API total {expected_total}, validated {len(rooms_by_slug)})"
        )

    rooms = list(rooms_by_slug.values())
    diagnostics = CollectionDiagnostics(
        pages_loaded=len(visited_pages),
        records_inspected=records_inspected,
        expected_total=expected_total,
        unique_rooms=len(rooms),
        fallback_dates=sum(
            room["completion_date_source"] == "sync-date-fallback"
            for room in rooms
        ),
    )
    return rooms, diagnostics


def validate_collection_against_saved(
    discovered_rooms: list[dict],
    saved_count: int,
) -> None:
    """Reject empty or partial live snapshots before any persistence occurs."""
    if saved_count and not discovered_rooms:
        raise RoomCollectionError(
            "zero completed rooms were returned "
            f"while {saved_count} rooms are saved"
        )
    if len(discovered_rooms) < saved_count:
        raise RoomCollectionError(
            f"{len(discovered_rooms)} completed rooms were returned while "
            f"{saved_count} rooms are saved"
        )


def _authenticated_account_summary(page) -> tuple[str, int | None]:
    result = page.evaluate(
        """async () => {
            try {
                const options = {
                    credentials: 'include',
                    headers: {accept: 'application/json'}
                };
                const [selfResponse, statsResponse] = await Promise.all([
                    fetch('/api/v2/users/self', options),
                    fetch('/api/v2/users/statistics', options)
                ]);
                if (!(selfResponse.headers.get('content-type') || '').includes('json')) {
                    return {authenticated: false, username: '', completedRooms: null};
                }
                const selfPayload = await selfResponse.json();
                const statsPayload =
                    (statsResponse.headers.get('content-type') || '').includes('json')
                        ? await statsResponse.json()
                        : null;
                const user = selfPayload?.data?.user;
                return {
                    authenticated:
                        selfPayload?.status === 'success' && Boolean(user?.username),
                    username: user?.username || '',
                    completedRooms:
                        Number.isInteger(statsPayload?.data?.completedRoomsNumber)
                            ? statsPayload.data.completedRoomsNumber
                            : null
                };
            } catch (error) {
                return {authenticated: false, username: '', completedRooms: null};
            }
        }"""
    )
    if not isinstance(result, dict) or not result.get("authenticated"):
        return "", None
    completed_rooms = result.get("completedRooms")
    if not isinstance(completed_rooms, int) or completed_rooms < 0:
        completed_rooms = None
    return str(result.get("username") or "").strip(), completed_rooms


def _collect_from_authenticated_page(
    page,
    username: str,
    fallback_date: dt.date,
) -> tuple[list[dict], CollectionDiagnostics]:
    def fetch_page(page_number: int, limit: int) -> dict:
        endpoint = (
            f"{COMPLETED_ROOMS_PATH}?username={username}"
            f"&limit={limit}&page={page_number}"
        )
        print(f"Loading completed-room API page {page_number}: {endpoint}", flush=True)
        payload = page.evaluate(
            """async ({username, limit, pageNumber}) => {
                try {
                    const query = new URLSearchParams({
                        username,
                        limit: String(limit),
                        page: String(pageNumber)
                    });
                    const response = await fetch(
                        `/api/v2/public-profile/completed-rooms?${query}`,
                        {credentials: 'include', headers: {accept: 'application/json'}}
                    );
                    if (!response.ok ||
                        !(response.headers.get('content-type') || '').includes('json')) {
                        return null;
                    }
                    return await response.json();
                } catch (error) {
                    return null;
                }
            }""",
            {
                "username": username,
                "limit": limit,
                "pageNumber": page_number,
            },
        )
        return payload

    return collect_paginated_rooms(fetch_page, fallback_date)


def merge_rooms(
    saved_data: dict,
    discovered_rooms: list[dict],
) -> tuple[dict, list[dict]]:
    """Merge a complete live snapshot without deleting saved evidence."""
    saved_rooms = saved_data.get("rooms")
    if not isinstance(saved_rooms, list):
        raise RoomCollectionError("saved room data is malformed")

    existing_by_slug = {
        str(room.get("slug") or ""): room
        for room in saved_rooms
        if isinstance(room, dict) and room.get("slug")
    }
    added: list[dict] = []
    for discovered in discovered_rooms:
        existing = existing_by_slug.get(discovered["slug"])
        if existing is None:
            saved_rooms.append(discovered)
            existing_by_slug[discovered["slug"]] = discovered
            added.append(discovered)
            continue

        existing["name"] = discovered["name"]
        existing["url"] = discovered["url"]
        if discovered.get("difficulty"):
            existing["difficulty"] = discovered["difficulty"]
        if (
            discovered.get("completion_date_source") != "sync-date-fallback"
            or not existing.get("completed")
        ):
            existing["completed"] = discovered["completed"]
            existing["completion_date_source"] = discovered[
                "completion_date_source"
            ]

    return saved_data, added


def sync_rooms() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Playwright is not installed. Run: ./setup")

    BROWSER_STATE.mkdir(parents=True, exist_ok=True)
    saved_data = read_json(ROOMS, {"rooms": []})
    saved_rooms = saved_data.get("rooms")
    if not isinstance(saved_rooms, list):
        raise SystemExit("Saved data/rooms.json is malformed; no files were changed.")
    saved_count = len(saved_rooms)
    fallback_date = dt.datetime.now().astimezone().date()

    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(BROWSER_STATE),
                headless=False,
                channel="chrome",
                viewport={"width": 1440, "height": 1000},
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                load_page(page, PROFILE_URL, "TryHackMe profile")
                print(
                    "A separate Chrome window has opened for TryHackMe syncing.",
                    flush=True,
                )
                print(
                    "Log into TryHackMe there if required, then return here and press Enter.",
                    flush=True,
                )
                input()
                print("Continuing sync...", flush=True)
                load_page(page, PROFILE_URL, "authenticated profile")

                (
                    authenticated_username,
                    account_completed_total,
                ) = _authenticated_account_summary(page)
                if authenticated_username.casefold() != "premortem":
                    raise RoomCollectionError(
                        "the isolated browser profile is not authenticated as "
                        "the expected public TryHackMe account"
                    )
                print(
                    "Authenticated browser profile verified as PreMortem.",
                    flush=True,
                )
                discovered_rooms, diagnostics = _collect_from_authenticated_page(
                    page, authenticated_username, fallback_date
                )
                if (
                    account_completed_total is not None
                    and diagnostics.expected_total != account_completed_total
                ):
                    raise RoomCollectionError(
                        "TryHackMe account statistics and completed-room pagination "
                        "disagree "
                        f"({account_completed_total} versus "
                        f"{diagnostics.expected_total})"
                    )
            finally:
                context.close()
    except RoomCollectionError as exc:
        raise SystemExit(
            f"TryHackMe room collection failed: {exc}. "
            "Existing room data, last_sync, README.md, and TRAINING.md were left unchanged."
        )

    try:
        validate_collection_against_saved(discovered_rooms, saved_count)
    except RoomCollectionError as exc:
        raise SystemExit(
            f"TryHackMe room collection appears partial: {exc}. "
            "Existing room data, last_sync, README.md, and TRAINING.md were "
            "left unchanged."
        )

    merged_data, added = merge_rooms(saved_data, discovered_rooms)
    write_json(ROOMS, merged_data)
    for room in added:
        writeup_for(room)

    synced_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    profile = read_json(PROFILE, {})
    profile.update(
        {
            "username": "PreMortem",
            "profile_url": PROFILE_URL,
            "last_sync": synced_at,
            "sync_method": "authenticated-completed-rooms-api",
        }
    )
    write_json(PROFILE, profile)
    regenerate_readme()

    print(
        "Room links inspected: "
        f"{diagnostics.records_inspected} structured completed-room records "
        f"across {diagnostics.pages_loaded} API page(s)."
    )
    print(f"Completed rooms discovered: {diagnostics.unique_rooms}.")
    print(f"Rooms already saved: {saved_count}.")
    print(f"New rooms added: {len(added)}.")
    for room in added:
        print(f"  + {room['name']} ({room['slug']})")
    print(
        "Collection completeness: complete "
        f"(API total {diagnostics.expected_total}; "
        f"collected {diagnostics.unique_rooms} unique)."
    )
    print(
        "Expected completed-room total changed: "
        f"{saved_count} -> {len(merged_data['rooms'])}."
    )
    if diagnostics.fallback_dates:
        print(
            "Completion-date notice: TryHackMe omitted completion timestamps for "
            f"{diagnostics.fallback_dates} room(s). Existing saved dates were "
            "preserved; newly discovered records use the local sync date and are "
            "labelled completion_date_source=sync-date-fallback."
        )
    print("Persistence and README/TRAINING rendering succeeded.")
    return len(added)


if __name__ == "__main__":
    sync_rooms()
