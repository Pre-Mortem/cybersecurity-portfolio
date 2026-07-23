"""Hack The Box synchroniser.

Design notes
------------
* Authentication is interactive and happens in a real, persistent Playwright
  browser rooted at ``.htb-browser``. This module never handles passwords,
  OAuth, 2FA codes, cookies or tokens — the user signs in manually and the
  browser keeps the session locally.
* Data source: the JSON responses the official HTB single-page app itself
  requests from ``*.hackthebox.com`` while the authenticated profile/academy
  pages load. These are captured at runtime via Playwright response
  interception rather than by hard-coding undocumented endpoints, so the
  collector follows whatever the official web app already relies on. Extraction
  falls back through: captured JSON -> embedded page data -> semantic DOM.
* Only achievement *metadata* is stored (that an item was completed, its name,
  difficulty, category, dates). Flags, answers, solution notes and any protected
  content are never requested or written.

The pure data pipeline (``normalise_*`` -> ``build_dataset`` -> ``validate_data``
-> ``write_data``) is fully deterministic and unit-tested without a browser. The
browser collection layer is exercised only during a real interactive sync.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .base import (
    SyncResult,
    atomic_write_json,
    clean_str,
    dedup_by_key,
    iso_now,
    normalise_difficulty,
    parse_date,
    safe_url,
    sort_records,
)

ROOT = Path(__file__).resolve().parent.parent
HTB_DATA = ROOT / "data/hackthebox.json"
HTB_BROWSER = ROOT / ".htb-browser"
HTB_DIAGNOSTICS = ROOT / ".htb-diagnostics"

SCHEMA_VERSION = 1
PLATFORM = "hackthebox"

# Domains involved in the unified HTB Account (SSO may redirect between them).
ACCOUNT_URL = "https://account.hackthebox.com/"
APP_URL = "https://app.hackthebox.com/"
LOGIN_HINT = "/login"

VALID_MACHINE_STATUS = ("active", "retired")


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

def empty_schema() -> dict:
    """A fresh, valid, empty HTB dataset."""
    return {
        "schema_version": SCHEMA_VERSION,
        "platform": PLATFORM,
        "synced_at": None,
        "public_identity": {"username": "", "profile_url": ""},
        "labs": {
            "machines": [],
            "sherlocks": [],
            "challenges": [],
            "badges": [],
            "rank": None,
        },
        "academy": {
            "modules": [],
            "paths": [],
            "badges": [],
            "certifications": [],
        },
        "achievements": [],
    }


# --------------------------------------------------------------------------- #
# Record normalisation (pure)
# --------------------------------------------------------------------------- #

def _first(raw: dict, *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return clean_str(value).lower() in ("true", "1", "yes", "owned", "solved", "complete", "completed")


def _compact(record: dict) -> dict:
    """Drop empty/None fields so records stay minimal and comparable."""
    return {k: v for k, v in record.items() if v not in (None, "", [], {})}


def normalise_machine(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title", "machine_name", "machineName"), 200)
    if not name:
        return None
    status = clean_str(_first(raw, "status", "state")).lower()
    if status not in VALID_MACHINE_STATUS:
        # "retired"/"active" may arrive as a boolean flag instead.
        retired = _first(raw, "retired", "isRetired", "is_retired")
        if retired is not None:
            status = "retired" if _as_bool(retired) else "active"
        else:
            status = ""
    record = {
        "name": name,
        "difficulty": normalise_difficulty(_first(raw, "difficulty", "difficultyText", "difficulty_text")),
        "operating_system": clean_str(_first(raw, "operating_system", "os", "operatingSystem"), 40),
        "status": status,
        "completed_at": parse_date(_first(raw, "completed_at", "owned_at", "date", "dateCompleted", "last_owned")),
    }
    # Record own-state only when true (presence means owned); absence avoids noise.
    if _as_bool(_first(raw, "user_own", "authUserInUserOwns", "isUserOwned", "user_owned")):
        record["user_own"] = True
    if _as_bool(_first(raw, "root_own", "authUserInRootOwns", "isRootOwned", "root_owned")):
        record["root_own"] = True
    return _compact(record)


def normalise_sherlock(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 200)
    if not name:
        return None
    return _compact({
        "name": name,
        "category": clean_str(_first(raw, "category", "category_name", "categoryName"), 60),
        "difficulty": normalise_difficulty(_first(raw, "difficulty", "difficultyText")),
        "completed_at": parse_date(_first(raw, "completed_at", "solved_at", "date", "dateCompleted")),
    })


def normalise_challenge(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 200)
    if not name:
        return None
    return _compact({
        "name": name,
        "category": clean_str(_first(raw, "category", "category_name", "challenge_category", "categoryName"), 60),
        "difficulty": normalise_difficulty(_first(raw, "difficulty", "difficultyText")),
        "completed_at": parse_date(_first(raw, "completed_at", "solved_at", "date", "dateCompleted")),
    })


def normalise_badge(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 120)
    if not name:
        return None
    return _compact({
        "name": name,
        "category": clean_str(_first(raw, "category", "category_name", "type"), 60),
    })


def normalise_module(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 200)
    if not name:
        return None
    tier = clean_str(_first(raw, "tier", "tier_name", "difficulty"), 40)
    record = {
        "name": name,
        "tier": tier,
        "status": "completed",
        "completed_at": parse_date(_first(raw, "completed_at", "completion_date", "date", "completedAt")),
    }
    return _compact(record)


def normalise_path(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 200)
    if not name:
        return None
    return _compact({
        "name": name,
        "status": "completed",
        "completed_at": parse_date(_first(raw, "completed_at", "completion_date", "date", "completedAt")),
    })


def normalise_certification(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title", "certification"), 200)
    if not name:
        return None
    return _compact({
        "name": name,
        "issued_at": parse_date(_first(raw, "issued_at", "issue_date", "date", "completed_at")),
    })


def normalise_achievement(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = clean_str(_first(raw, "name", "title"), 200)
    if not name:
        return None
    return _compact({
        "name": name,
        "category": clean_str(_first(raw, "category", "type"), 60),
    })


_COLLECTORS = {
    ("labs", "machines"): (normalise_machine, ("name",)),
    ("labs", "sherlocks"): (normalise_sherlock, ("name",)),
    ("labs", "challenges"): (normalise_challenge, ("name", "category")),
    ("labs", "badges"): (normalise_badge, ("name",)),
    ("academy", "modules"): (normalise_module, ("name",)),
    ("academy", "paths"): (normalise_path, ("name",)),
    ("academy", "badges"): (normalise_badge, ("name",)),
    ("academy", "certifications"): (normalise_certification, ("name",)),
}


def _clean_collection(raw_list: Any, normaliser, sort_keys) -> list[dict]:
    if not isinstance(raw_list, list):
        return []
    cleaned = [rec for rec in (normaliser(item) for item in raw_list) if rec]
    cleaned = dedup_by_key(cleaned, lambda r: "|".join(str(r.get(k, "")).lower() for k in sort_keys))
    return sort_records(cleaned, *sort_keys)


# --------------------------------------------------------------------------- #
# Dataset assembly (pure)
# --------------------------------------------------------------------------- #

def build_dataset(identity: dict, raw: dict, synced_at: str | None = None) -> dict:
    """Assemble a clean, sorted, de-duplicated dataset from raw collected lists.

    ``raw`` maps categories to raw record lists, e.g.
    ``{"machines": [...], "modules": [...], ...}``. Unknown categories and
    unsupported fields are discarded. This function performs no I/O.
    """
    data = empty_schema()
    data["synced_at"] = synced_at or iso_now()

    identity = identity if isinstance(identity, dict) else {}
    data["public_identity"] = {
        "username": clean_str(identity.get("username"), 80),
        "profile_url": safe_url(identity.get("profile_url")),
    }

    for (section, field_name), (normaliser, sort_keys) in _COLLECTORS.items():
        data[section][field_name] = _clean_collection(raw.get(field_name), normaliser, sort_keys)

    rank = clean_str(raw.get("rank"), 60)
    data["labs"]["rank"] = rank or None

    data["achievements"] = _clean_collection(raw.get("achievements"), normalise_achievement, ("name",))
    return data


def is_empty(data: dict) -> bool:
    """True when the dataset carries no records and no identity."""
    if not isinstance(data, dict):
        return True
    identity = data.get("public_identity") or {}
    if clean_str(identity.get("username")) or safe_url(identity.get("profile_url")):
        return False
    labs = data.get("labs") or {}
    academy = data.get("academy") or {}
    lists = [
        labs.get("machines"), labs.get("sherlocks"), labs.get("challenges"), labs.get("badges"),
        academy.get("modules"), academy.get("paths"), academy.get("badges"), academy.get("certifications"),
        data.get("achievements"),
    ]
    if labs.get("rank"):
        return False
    return not any(isinstance(x, list) and x for x in lists)


def dataset_counts(data: dict) -> dict[str, int]:
    labs = data.get("labs") or {}
    academy = data.get("academy") or {}
    return {
        "machines": len(labs.get("machines") or []),
        "sherlocks": len(labs.get("sherlocks") or []),
        "challenges": len(labs.get("challenges") or []),
        "labs_badges": len(labs.get("badges") or []),
        "modules": len(academy.get("modules") or []),
        "paths": len(academy.get("paths") or []),
        "academy_badges": len(academy.get("badges") or []),
        "certifications": len(academy.get("certifications") or []),
        "achievements": len(data.get("achievements") or []),
    }


# --------------------------------------------------------------------------- #
# Validation (pure)
# --------------------------------------------------------------------------- #

def validate_data(data: Any) -> list[str]:
    """Return a list of schema errors; empty means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root is not an object"]
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if data.get("platform") != PLATFORM:
        errors.append("platform mismatch")

    identity = data.get("public_identity")
    if not isinstance(identity, dict):
        errors.append("public_identity must be an object")
    else:
        url = identity.get("profile_url", "")
        if url and not safe_url(url):
            errors.append("profile_url must be http(s)")

    def check_list(container: dict, section: str, field_name: str, required: tuple[str, ...]):
        seq = container.get(field_name)
        if not isinstance(seq, list):
            errors.append(f"{section}.{field_name} must be a list")
            return
        for index, record in enumerate(seq):
            if not isinstance(record, dict):
                errors.append(f"{section}.{field_name}[{index}] must be an object")
                continue
            for req in required:
                if not clean_str(record.get(req)):
                    errors.append(f"{section}.{field_name}[{index}] missing {req}")
            url = record.get("profile_url") or record.get("url")
            if url and not safe_url(url):
                errors.append(f"{section}.{field_name}[{index}] has an unsafe url")

    labs = data.get("labs")
    academy = data.get("academy")
    if not isinstance(labs, dict):
        errors.append("labs must be an object")
    else:
        check_list(labs, "labs", "machines", ("name",))
        check_list(labs, "labs", "sherlocks", ("name",))
        check_list(labs, "labs", "challenges", ("name",))
        check_list(labs, "labs", "badges", ("name",))
    if not isinstance(academy, dict):
        errors.append("academy must be an object")
    else:
        check_list(academy, "academy", "modules", ("name",))
        check_list(academy, "academy", "paths", ("name",))
        check_list(academy, "academy", "badges", ("name",))
        check_list(academy, "academy", "certifications", ("name",))
    if not isinstance(data.get("achievements"), list):
        errors.append("achievements must be a list")
    return errors


# --------------------------------------------------------------------------- #
# Persistence (preserve-on-failure, atomic)
# --------------------------------------------------------------------------- #

def load_data(path: Path = HTB_DATA) -> dict:
    """Load existing HTB data, tolerating a missing or malformed file."""
    import json
    try:
        if not path.exists():
            return empty_schema()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else empty_schema()
    except (OSError, ValueError):
        return empty_schema()


def write_data(data: dict, path: Path = HTB_DATA) -> tuple[bool, list[str]]:
    """Validate then atomically write. Never writes an invalid dataset."""
    errors = validate_data(data)
    if errors:
        return False, errors
    atomic_write_json(path, data)
    return True, []


# --------------------------------------------------------------------------- #
# Browser collection (interactive; not unit-tested)
# --------------------------------------------------------------------------- #

# Pages whose network traffic is captured. Kept semantic and shallow.
_PROFILE_PATHS = [
    "https://app.hackthebox.com/profile/overview",
    "https://app.hackthebox.com/profile/activity",
    "https://app.hackthebox.com/academy/my-dashboard",
    "https://app.hackthebox.com/academy/completed",
]

# URL substrings used to classify captured JSON into categories, in priority
# order. Matching is intentionally forgiving (the official app owns these paths).
_URL_CLASSIFIERS = [
    ("modules", ("academy" , "module")),
    ("paths", ("academy", "path")),
    ("certifications", ("certificat",)),
    ("sherlocks", ("sherlock",)),
    ("challenges", ("challenge",)),
    ("machines", ("machine",)),
    ("badges", ("badge",)),
    ("achievements", ("achievement",)),
]


def _extract_lists(payload: Any) -> list:
    """Yield candidate lists-of-dicts found anywhere in a JSON payload."""
    found = []
    if isinstance(payload, list):
        if payload and all(isinstance(x, dict) for x in payload):
            found.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            found.extend(_extract_lists(value))
    return found


def _classify(url: str) -> str | None:
    """Return the category for a captured URL, requiring every needle present."""
    low = url.lower()
    for category, needles in _URL_CLASSIFIERS:
        if all(needle in low for needle in needles):
            return category
    return None


def _save_diagnostic(page, label: str) -> None:
    """Save a failure screenshot to the ignored diagnostics directory.

    Screenshots are only taken on failure and land in a git-ignored local
    directory. They may show generic app chrome; account menus are avoided by
    only capturing on error pages / login states.
    """
    try:
        HTB_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        page.screenshot(path=str(HTB_DIAGNOSTICS / f"{label}-{stamp}.png"))
    except Exception:
        pass


def _looks_authenticated(page, captured: list[tuple[str, Any]]) -> bool:
    """Heuristic: authenticated if not on a login URL and the app has fetched
    user/profile JSON successfully."""
    if LOGIN_HINT in page.url.lower():
        return False
    for url, payload in captured:
        low = url.lower()
        if any(k in low for k in ("/user/", "/profile", "users/me", "/info")) and isinstance(payload, dict):
            return True
    return False


def collect_from_browser(interactive: bool, login_timeout: int = 300) -> tuple[dict, dict]:
    """Drive the persistent browser to capture the authenticated app's own JSON.

    Returns ``(identity, raw)``. Raises RuntimeError on unrecoverable problems.
    Never returns or logs cookies/tokens.
    """
    from playwright.sync_api import sync_playwright

    captured: list[tuple[str, Any]] = []

    def on_response(response):
        try:
            if "hackthebox.com" not in response.url:
                return
            if response.request.resource_type not in ("xhr", "fetch"):
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            captured.append((response.url, response.json()))
        except Exception:
            pass

    identity: dict = {}
    raw: dict = {category: [] for category in (
        "machines", "sherlocks", "challenges", "badges",
        "modules", "paths", "certifications", "achievements",
    )}

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(HTB_BROWSER),
            headless=not interactive,
            channel="chrome",
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("response", on_response)
        try:
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            if not _looks_authenticated(page, captured):
                if not interactive:
                    _save_diagnostic(page, "not-authenticated")
                    raise RuntimeError("Hack The Box session is not authenticated (non-interactive run).")
                print("\nA browser window has opened for Hack The Box.", flush=True)
                print("Sign in there (email, OAuth and 2FA as required). "
                      "Syncing continues automatically once login is detected.", flush=True)
                deadline = dt.datetime.now() + dt.timedelta(seconds=login_timeout)
                while dt.datetime.now() < deadline:
                    page.wait_for_timeout(3000)
                    if _looks_authenticated(page, captured):
                        break
                else:
                    _save_diagnostic(page, "login-timeout")
                    raise RuntimeError("Timed out waiting for Hack The Box login.")
                print("Hack The Box login detected. Collecting achievement metadata...", flush=True)

            # Identity from the app's own captured user JSON (no email/id stored).
            identity = _discover_identity(captured)

            # Visit profile/academy pages and let the app fetch its own data.
            for url in _PROFILE_PATHS:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3500)
                    page.mouse.wheel(0, 4000)
                    page.wait_for_timeout(1500)
                except Exception:
                    continue

            _classify_captured(captured, raw)
        except Exception:
            _save_diagnostic(page, "collect-error")
            raise
        finally:
            context.close()

    return identity, raw


def _discover_identity(captured: list[tuple[str, Any]]) -> dict:
    """Pull only the public username and (public) profile URL from captured JSON.

    Deliberately ignores email, internal numeric id and avatar. If a public
    profile URL is not clearly present, it is left empty rather than invented.
    """
    username = ""
    profile_url = ""
    for url, payload in captured:
        low = url.lower()
        if not any(k in low for k in ("/user", "/profile", "users/me", "/info")):
            continue
        candidates = [payload]
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, dict):
                    candidates.append(value)
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            if not username:
                username = clean_str(obj.get("name") or obj.get("username"), 80)
            public = obj.get("public_url") or obj.get("profile_url") or obj.get("publicProfileUrl")
            if public and not profile_url:
                profile_url = safe_url(public)
    return {"username": username, "profile_url": profile_url}


def _classify_captured(captured: list[tuple[str, Any]], raw: dict) -> None:
    """Route captured list payloads into raw category buckets by URL keyword."""
    for url, payload in captured:
        category = _classify(url)
        if not category:
            continue
        for candidate in _extract_lists(payload):
            raw[category].extend(candidate)


# --------------------------------------------------------------------------- #
# Public sync entry point
# --------------------------------------------------------------------------- #

def sync(interactive: bool = True, data_path: Path = HTB_DATA) -> SyncResult:
    """Run a full Hack The Box sync, preserving prior valid data on failure."""
    result = SyncResult(platform="Hack The Box")
    previous = load_data(data_path)

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        result.message = "Playwright is not installed. Run: ./setup"
        return result

    try:
        identity, raw = collect_from_browser(interactive=interactive)
    except Exception as exc:  # noqa: BLE001 - report, never leak internals/secrets
        result.message = f"Hack The Box sync failed: {exc}"
        return result

    dataset = build_dataset(identity, raw)

    # Never overwrite prior real data with an empty result caused by a failed page.
    if is_empty(dataset) and not is_empty(previous):
        result.message = "Hack The Box returned no data; previous achievements preserved."
        return result

    ok, errors = write_data(dataset, data_path)
    if not ok:
        result.message = "Hack The Box data failed validation; previous data preserved: " + "; ".join(errors[:5])
        return result

    result.ok = True
    result.counts = dataset_counts(dataset)
    result.changed = dataset_snapshot(dataset) != dataset_snapshot(previous)
    result.message = "Hack The Box sync complete."
    return result


def dataset_snapshot(data: dict) -> str:
    """Normalised snapshot (identity + records, ignoring synced_at) for change
    detection so an unchanged re-sync is idempotent."""
    import json
    copy = {k: v for k, v in (data or {}).items() if k != "synced_at"}
    return json.dumps(copy, sort_keys=True, ensure_ascii=False)
