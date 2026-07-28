# Cybersecurity Portfolio Sync Engine

The **Cybersecurity Portfolio Sync Engine** is the supporting infrastructure for this personal cybersecurity portfolio. It automatically collects, normalises, validates, and renders evidence of hands-on training, lab completions, and certifications into structured Markdown documents (`README.md` and `TRAINING.md`).

---

## Architecture Overview

The sync engine separates data extraction, authentication, validation, and rendering into distinct modules:

```
portfolio.py (CLI & Orchestrator)
 ├── platforms/
 │    ├── base.py       (Platform sync interface & schema validators)
 │    ├── hackthebox.py (HTB Playwright collector & parser)
 │    └── cisco_netacad.py (Cisco offline schema, scrubber & persistence boundary)
 ├── room_sync.py       (TryHackMe rooms collector)
 ├── badge_sync.py      (TryHackMe badges collector)
 └── room_difficulty_sync.py (TryHackMe difficulty collector)
```

- **Data Storage**: Collected evidence is stored in versioned JSON files under `data/` (`rooms.json`, `badges.json`, `profile.json`, `hackthebox.json`, `cisco_netacad.json`, `evidence.json`).
- **Rendering Engine**: `portfolio.py` parses saved JSON data and updates two
  bounded regions in `README.md`. The small `PROFILE-SNAPSHOT` region owns only
  the changing TryHackMe room and badge totals. The main `PORTFOLIO` region
  owns evidence-backed skills, the complete saved TryHackMe room table, the
  earned badge cabinet, room milestones, report and draft links, and compact
  Hack The Box and Cisco status. The personal introduction, qualification,
  key areas, About Me, working style, project narratives, Current Focus,
  contact details, and automation summary are maintained outside those regions
  and cannot be replaced by a platform sync. Platforms without completed
  activity render an accurate empty state rather than invented achievements.
  `TRAINING.md` remains the complete generated platform history, while detailed
  engine, authentication, privacy, schema, and roadmap information remains in
  `docs/`.

---

## Supported Platforms

1. **TryHackMe**
   - Synced data: Completed rooms, difficulty levels, completion dates, badges, profile metrics.
   - Mechanism: Authenticated Playwright browser session (`.thm-browser/`) and
     the completed-history view's observed numbered
     `/api/v2/public-profile/completed-rooms` fetch response. The collector uses
     the response's explicit page size and follows every `nextPage` until
     `hasNextPage` is false on `totalPages`.
   - Completeness: every page number and per-page count is logged; stable room
     codes are deduplicated; the final unique count must match `totalDocs` and,
     when available, the authenticated account's completed-room statistic.
     Malformed records, empty intermediate pages, repeated/non-advancing pages,
     inconsistent totals, or a snapshot smaller than saved evidence cause a
     clear failure.
   - Failure safety: a failed collection does not write `data/rooms.json`,
     advance `last_sync`, or regenerate `README.md` or `TRAINING.md`. Existing
     platform evidence is retained.
   - Completion dates: exact timestamps are preferred when supplied. The
     current response omits completion timestamps, so newly discovered rooms
     use the local sync date with
     `completion_date_source=sync-date-fallback`; existing dates are preserved.

2. **Hack The Box**
   - Synced data: Labs (Machines, Sherlocks, Challenges, Badges, Rank) and Academy (Modules, Paths, Certifications).
   - Mechanism: Authenticated Playwright browser session (`.htb-browser/`) intercepting web app JSON payloads.

3. **Cisco Networking Academy** (Offline foundation)
   - Implemented: schema v1, identity scrubbing, atomic persistence, CLI selection, and saved-data rendering for courses, badges, certificates, dates, and skills.
   - Not implemented: live browser extraction or successful authenticated sync.
   - The reserved `.cisco-browser/` profile will support a later interactive login flow. No endpoint has been guessed or hard-coded.

---

## CLI Usage

### Launching the Interactive Sync Menu

Run the interactive wrapper script or execute `portfolio.py` directly:

```bash
./sync-portfolio
# OR
python3 portfolio.py sync
```

### macOS Desktop Shortcut

Install a Finder-launchable shortcut with:

```bash
./install-desktop-shortcut
```

The installer validates this repository and its existing `./sync-portfolio`
entry point, then creates the executable file:

```text
~/Desktop/Sync Cybersecurity Portfolio.command
```

Double-click that file in Finder to open the interactive sync menu in Terminal.
The launcher changes into this repository and delegates directly to
`./sync-portfolio`; it contains no duplicate sync logic and does not
automatically commit or push. It reports the final exit status and pauses before
closing when attached to an interactive Terminal.

The installer is idempotent and safely replaces its own regular launcher file.
Use `./install-desktop-shortcut --dry-run` to validate launcher generation
without writing to the Desktop. `--desktop-dir PATH` is available for isolated
testing.

The menu options include:
1. **TryHackMe** — Sync TryHackMe rooms, difficulty, and badges.
2. **Hack The Box** — Sync HTB Labs and Academy activity.
3. **Cisco Networking Academy** — Report the current offline-only collector state and preserve saved data.
4. **All platforms** — Sequential sync with per-platform failure isolation.
5. **Regenerate from saved data** — Re-render `README.md` and `TRAINING.md` using existing local JSON data.
6. **Exit**

### Non-Interactive & Automation Commands

```bash
# Sync specific platform non-interactively
python3 portfolio.py sync --platform tryhackme --non-interactive
python3 portfolio.py sync --platform hackthebox --non-interactive
python3 portfolio.py sync --platform cisco --non-interactive
python3 portfolio.py sync --platform all --non-interactive

# Re-render README and TRAINING.md without connecting to platforms
python3 portfolio.py render

# Commit and push automatically (requires explicit --push flag)
python3 portfolio.py sync --platform all --push
python3 portfolio.py render --push
```

---

## Staging & Commit Safety

The sync engine enforces an explicit staging allow-list (`PUBLISH_ALLOWLIST`):
- `README.md`
- `TRAINING.md`
- `data/`
- `writeups/`

Browser session profiles (`.thm-browser/`, `.htb-browser/`, `.cisco-browser/`),
diagnostic dumps, temporary files, and raw response logs are strictly excluded
from Git tracking via `.gitignore` and pre-commit checks.

Each platform returns an independent outcome. A multi-platform run renders when
at least one selected platform succeeds, so one platform failure cannot erase
another platform's saved evidence. If every selected sync fails, public
README/TRAINING regeneration is skipped.
