"""Shared building blocks for platform synchronisers.

This module is deliberately self-contained (it does not import the renderer in
``portfolio.py``) so platform collectors and the renderer stay decoupled and no
import cycle is possible. It provides small, well-tested helpers for:

* deterministic ISO 8601 timestamps
* atomic JSON writes (temp file + os.replace)
* record cleaning, validation, de-duplication and stable sorting
* a lightweight ``SyncResult`` used to report per-platform outcomes

None of these helpers touch authentication material, cookies or tokens.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

# HTB difficulty vocabulary. Unknown values are preserved as trimmed text rather
# than dropped, so the tracker tolerates new labels without losing information.
KNOWN_DIFFICULTIES = ("Very Easy", "Easy", "Medium", "Hard", "Insane")


@dataclass
class SyncResult:
    """Outcome of a single platform sync."""

    platform: str
    ok: bool = False
    message: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    changed: bool = False

    def total(self) -> int:
        return sum(self.counts.values())


def iso_now() -> str:
    """Current UTC time as a stable ISO 8601 string (seconds precision)."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def clean_str(value: Any, limit: int = 300) -> str:
    """Collapse whitespace and trim a value to a bounded plain string."""
    text = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
    return text[:limit]


def safe_url(value: Any) -> str:
    """Return the value only if it is a plain http(s) URL, else ''."""
    text = clean_str(value, limit=500)
    return text if text.lower().startswith(("http://", "https://")) else ""


def normalise_difficulty(value: Any) -> str:
    """Map a difficulty to a known label where possible, else preserve as text."""
    text = clean_str(value)
    if not text:
        return ""
    for known in KNOWN_DIFFICULTIES:
        if text.lower() == known.lower():
            return known
    return text


def parse_date(value: Any) -> str:
    """Return an ISO date (YYYY-MM-DD) if the value parses, else ''.

    Accepts full ISO 8601 timestamps (with or without a trailing 'Z') and plain
    dates. Anything unparseable yields '' so downstream data never carries a
    malformed date.
    """
    text = clean_str(value)
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(candidate)
        return parsed.date().isoformat()
    except ValueError:
        pass
    try:
        return dt.date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ""


def dedup_by_key(records: Iterable[dict], key: Callable[[dict], str]) -> list[dict]:
    """Remove duplicate records by a stable key, keeping the first occurrence."""
    seen: set[str] = set()
    out: list[dict] = []
    for record in records:
        identifier = key(record)
        if identifier in seen:
            continue
        seen.add(identifier)
        out.append(record)
    return out


def sort_records(records: Iterable[dict], *keys: str) -> list[dict]:
    """Deterministically sort records by the given fields (case-insensitive)."""
    def sort_key(record: dict):
        return tuple(str(record.get(k, "")).lower() for k in keys)

    return sorted(records, key=sort_key)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: serialise to a temp file, fsync, then os.replace.

    A partially written file can never replace a valid one, because the rename
    is atomic on POSIX filesystems.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
