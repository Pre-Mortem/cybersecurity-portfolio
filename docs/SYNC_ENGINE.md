# Cybersecurity Portfolio Sync Engine

The **Cybersecurity Portfolio Sync Engine** is the supporting infrastructure for this personal cybersecurity portfolio. It automatically collects, normalises, validates, and renders evidence of hands-on training, lab completions, and certifications into structured Markdown documents (`README.md` and `TRAINING.md`).

---

## Architecture Overview

The sync engine separates data extraction, authentication, validation, and rendering into distinct modules:

```
portfolio.py (CLI & Orchestrator)
 ├── platforms/
 │    ├── base.py       (Platform sync interface & schema validators)
 │    └── hackthebox.py (HTB Playwright collector & parser)
 ├── room_sync.py       (TryHackMe rooms collector)
 ├── badge_sync.py      (TryHackMe badges collector)
 └── room_difficulty_sync.py (TryHackMe difficulty collector)
```

- **Data Storage**: Collected evidence is stored in versioned JSON files under `data/` (`rooms.json`, `badges.json`, `profile.json`, `hackthebox.json`, `evidence.json`).
- **Rendering Engine**: `portfolio.py` parses saved JSON data and populates bounded comment markers in `README.md` (compact summary) and `TRAINING.md` (detailed platform history).

---

## Supported Platforms

1. **TryHackMe**
   - Synced data: Completed rooms, difficulty levels, completion dates, badges, profile metrics.
   - Mechanism: Authenticated Playwright browser session (`.thm-browser/`) and validated API endpoints.

2. **Hack The Box**
   - Synced data: Labs (Machines, Sherlocks, Challenges, Badges, Rank) and Academy (Modules, Paths, Certifications).
   - Mechanism: Authenticated Playwright browser session (`.htb-browser/`) intercepting web app JSON payloads.

3. **Cisco Networking Academy** (Roadmap)
   - Planned support for course completions, badges, and certificates with strict public identity protection.

---

## CLI Usage

### Launching the Interactive Sync Menu

Run the interactive wrapper script or execute `portfolio.py` directly:

```bash
./sync-portfolio
# OR
python3 portfolio.py sync
```

The menu options include:
1. **TryHackMe** — Sync TryHackMe rooms, difficulty, and badges.
2. **Hack The Box** — Sync HTB Labs and Academy activity.
3. **Both platforms** — Sequential sync across all supported platforms.
4. **Regenerate from saved data** — Re-render `README.md` and `TRAINING.md` using existing local JSON data.
5. **Exit**

### Non-Interactive & Automation Commands

```bash
# Sync specific platform non-interactively
python3 portfolio.py sync --platform tryhackme --non-interactive
python3 portfolio.py sync --platform hackthebox --non-interactive
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

Browser session profiles (`.thm-browser/`, `.htb-browser/`), diagnostic dumps, temporary files, and raw response logs are strictly excluded from Git tracking via `.gitignore` and pre-commit checks.
