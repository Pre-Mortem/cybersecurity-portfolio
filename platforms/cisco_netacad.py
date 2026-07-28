"""Cisco Networking Academy offline data foundation.

This module deliberately implements only the deterministic, privacy-preserving
data boundary for Cisco Networking Academy. It does not automate a browser,
call undocumented endpoints, or attempt authentication. A later milestone can
add an interactive collector behind ``collect_from_browser`` after the live
site has been inspected and validated safely.

Only allow-listed achievement metadata can cross this boundary. Unknown fields
are discarded, identity-bearing values are detected and removed, and validated
data is written atomically so a failed Cisco operation cannot damage saved
TryHackMe, Hack The Box, or previous Cisco data.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .base import SyncResult, atomic_write_json, clean_str, dedup_by_key, iso_now, parse_date, sort_records

ROOT = Path(__file__).resolve().parent.parent
CISCO_DATA = ROOT / "data/cisco_netacad.json"
CISCO_BROWSER = ROOT / ".cisco-browser"

SCHEMA_VERSION = 1
PLATFORM = "cisco_netacad"
COLLECTION_STATES = ("not_collected", "available", "unavailable")
COURSE_STATUSES = ("completed", "in_progress")

_ROOT_KEYS = {
    "schema_version", "platform", "synced_at", "collection_status",
    "courses", "badges", "certificates",
}
_COURSE_KEYS = {"title", "status", "completed_at", "skills"}
_AWARD_KEYS = {"title", "earned_at", "skills"}
_CERTIFICATE_KEYS = {"title", "issued_at", "skills"}

# Key names likely to carry account identity or authentication material.
_IDENTITY_KEY = re.compile(
    r"(^|_)(full_?name|first_?name|last_?name|display_?name|user_?name|email|"
    r"account|user_?id|certificate_?id|credential|cookie|token|session|"
    r"authorization|profile_?url|private_?url|url)($|_)",
    re.IGNORECASE,
)
_SENSITIVE_TEXT = re.compile(
    r"(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})|"
    r"(?:https?://|javascript:|file://)|"
    r"(?:-----BEGIN [A-Z ]+PRIVATE KEY-----)|"
    r"(?:\b(?:bearer|authorization|session[_ -]?id|access[_ -]?token|"
    r"refresh[_ -]?token|cookie)\b\s*[:=]?)|"
    r"(?:/(?:Users|home)/[^\s]+)|(?:[A-Za-z]:\\Users\\[^\s]+)",
    re.IGNORECASE,
)


def empty_schema(collection_status: str = "not_collected") -> dict:
    """Return a fresh, valid Cisco dataset with no achievements."""
    if collection_status not in COLLECTION_STATES:
        collection_status = "not_collected"
    return {
        "schema_version": SCHEMA_VERSION,
        "platform": PLATFORM,
        "synced_at": None,
        "collection_status": collection_status,
        "courses": [],
        "badges": [],
        "certificates": [],
    }


def _identity_terms(raw: Any) -> set[str]:
    """Extract values attached to identity-bearing keys for content scrubbing."""
    terms: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if _IDENTITY_KEY.search(str(key)):
                    if isinstance(child, (str, int)):
                        text = clean_str(child, 300)
                        if len(text) >= 3:
                            terms.add(text.casefold())
                            if "@" in text:
                                local = text.split("@", 1)[0].strip()
                                if len(local) >= 3:
                                    terms.add(local.casefold())
                    continue
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(raw)
    return terms


def _safe_text(value: Any, identity_terms: Iterable[str], limit: int = 200) -> str:
    """Return bounded public text, or an empty string when it may leak identity."""
    if not isinstance(value, str):
        return ""
    text = clean_str(value, limit)
    if not text or _SENSITIVE_TEXT.search(text):
        return ""
    folded = text.casefold()
    if any(term and term in folded for term in identity_terms):
        return ""
    return text


def _skills(value: Any, identity_terms: Iterable[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [_safe_text(item, identity_terms, 100) for item in value]
    cleaned = [item for item in cleaned if item]
    return sorted(set(cleaned), key=str.casefold)


def _first(raw: dict, *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def normalise_course(raw: Any, identity_terms: Iterable[str] = ()) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = _safe_text(_first(raw, "title", "course_title", "name"), identity_terms)
    if not title:
        return None
    status = clean_str(_first(raw, "status", "completion_status"), 30).lower().replace(" ", "_")
    if status not in COURSE_STATUSES:
        status = "completed" if parse_date(_first(raw, "completed_at", "completion_date")) else ""
    if not status:
        return None
    record = {"title": title, "status": status}
    completed_at = parse_date(_first(raw, "completed_at", "completion_date", "date_completed"))
    if completed_at:
        record["completed_at"] = completed_at
    skills = _skills(_first(raw, "skills", "associated_skills"), identity_terms)
    if skills:
        record["skills"] = skills
    return record


def normalise_badge(raw: Any, identity_terms: Iterable[str] = ()) -> dict | None:
    return _normalise_award(raw, identity_terms, "earned_at", ("earned_at", "issued_at", "date_earned"))


def normalise_certificate(raw: Any, identity_terms: Iterable[str] = ()) -> dict | None:
    return _normalise_award(raw, identity_terms, "issued_at", ("issued_at", "earned_at", "completion_date"))


def _normalise_award(
    raw: Any,
    identity_terms: Iterable[str],
    date_field: str,
    date_keys: tuple[str, ...],
) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = _safe_text(_first(raw, "title", "name", "badge_title", "certificate_title"), identity_terms)
    if not title:
        return None
    record = {"title": title}
    date_value = parse_date(_first(raw, *date_keys))
    if date_value:
        record[date_field] = date_value
    skills = _skills(_first(raw, "skills", "associated_skills"), identity_terms)
    if skills:
        record["skills"] = skills
    return record


def _normalise_list(raw: Any, normaliser, identity_terms: set[str]) -> list[dict]:
    if not isinstance(raw, list):
        return []
    records = [record for record in (normaliser(item, identity_terms) for item in raw) if record]
    records = dedup_by_key(records, lambda record: record["title"].casefold())
    return sort_records(records, "title")


def build_dataset(raw: Any, synced_at: str | None = None) -> dict:
    """Build an allow-listed, identity-scrubbed dataset from untrusted input."""
    raw = raw if isinstance(raw, dict) else {}
    identity_terms = _identity_terms(raw)
    data = empty_schema()
    data["courses"] = _normalise_list(raw.get("courses"), normalise_course, identity_terms)
    data["badges"] = _normalise_list(raw.get("badges"), normalise_badge, identity_terms)
    data["certificates"] = _normalise_list(raw.get("certificates"), normalise_certificate, identity_terms)
    if any((data["courses"], data["badges"], data["certificates"])):
        data["collection_status"] = "available"
        data["synced_at"] = synced_at or iso_now()
    return data


def dataset_counts(data: dict) -> dict[str, int]:
    return {
        "courses": len(data.get("courses") or []),
        "badges": len(data.get("badges") or []),
        "certificates": len(data.get("certificates") or []),
    }


def is_empty(data: Any) -> bool:
    return not isinstance(data, dict) or not any(
        isinstance(data.get(field), list) and data[field]
        for field in ("courses", "badges", "certificates")
    )


def _valid_iso_timestamp(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return dt.date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate_data(data: Any) -> list[str]:
    """Return schema/privacy errors. An empty list means the dataset is safe."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root is not an object"]
    extra_root = sorted(set(data) - _ROOT_KEYS)
    if extra_root:
        errors.append("unsupported root fields: " + ", ".join(extra_root))
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if data.get("platform") != PLATFORM:
        errors.append("platform mismatch")
    state = data.get("collection_status")
    if state not in COLLECTION_STATES:
        errors.append("collection_status is invalid")
    if not _valid_iso_timestamp(data.get("synced_at")):
        errors.append("synced_at must be an ISO 8601 timestamp or null")

    def check_records(field: str, allowed: set[str], date_field: str | None = None) -> None:
        records = data.get(field)
        if not isinstance(records, list):
            errors.append(f"{field} must be a list")
            return
        for index, record in enumerate(records):
            prefix = f"{field}[{index}]"
            if not isinstance(record, dict):
                errors.append(f"{prefix} must be an object")
                continue
            extra = sorted(set(record) - allowed)
            if extra:
                errors.append(f"{prefix} has unsupported fields: {', '.join(extra)}")
            title = record.get("title")
            if not isinstance(title, str) or not title.strip():
                errors.append(f"{prefix} missing title")
            elif not _safe_text(title, ()):
                errors.append(f"{prefix}.title contains sensitive content")
            if field == "courses" and record.get("status") not in COURSE_STATUSES:
                errors.append(f"{prefix}.status is invalid")
            if date_field and date_field in record and not _valid_iso_date(record.get(date_field)):
                errors.append(f"{prefix}.{date_field} must be an ISO date")
            skills = record.get("skills", [])
            if not isinstance(skills, list):
                errors.append(f"{prefix}.skills must be a list")
            else:
                for skill_index, skill in enumerate(skills):
                    if not isinstance(skill, str) or not _safe_text(skill, ()):
                        errors.append(f"{prefix}.skills[{skill_index}] contains sensitive content")

    check_records("courses", _COURSE_KEYS, "completed_at")
    check_records("badges", _AWARD_KEYS, "earned_at")
    check_records("certificates", _CERTIFICATE_KEYS, "issued_at")

    if state == "available" and is_empty(data):
        errors.append("available dataset must contain achievement metadata")
    if state == "available" and data.get("synced_at") is None:
        errors.append("available dataset requires synced_at")
    if state != "available" and data.get("synced_at") is not None:
        errors.append("non-available dataset must not have synced_at")
    if state != "available" and not is_empty(data):
        errors.append("achievement metadata requires collection_status=available")
    return errors


def load_data(path: Path = CISCO_DATA) -> dict:
    """Load valid saved Cisco data, falling back to an unavailable state."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty_schema("unavailable")
    return loaded if not validate_data(loaded) else empty_schema("unavailable")


def write_data(data: dict, path: Path = CISCO_DATA) -> tuple[bool, list[str]]:
    """Validate and atomically persist Cisco data; never write unsafe input."""
    errors = validate_data(data)
    if errors:
        return False, errors
    atomic_write_json(path, data)
    return True, []


def dataset_snapshot(data: dict) -> str:
    copy = {key: value for key, value in (data or {}).items() if key != "synced_at"}
    return json.dumps(copy, sort_keys=True, ensure_ascii=False)


def sync(interactive: bool = True, data_path: Path = CISCO_DATA) -> SyncResult:
    """Report the intentionally unavailable live collector without writing data."""
    del interactive, data_path
    return SyncResult(
        platform="Cisco Networking Academy",
        ok=False,
        message=(
            "Cisco live browser extraction is not implemented in this foundation; "
            "saved data was preserved."
        ),
    )
