# Development Roadmap

This document outlines completed milestones and future enhancements for the **PreMortem Cybersecurity Portfolio & Sync Engine**.

---

## Milestone 1 — TryHackMe Integration & Base Portfolio (Completed)
- [x] Initial portfolio layout and markdown template structure.
- [x] Automated TryHackMe completed rooms collector (`room_sync.py`).
- [x] TryHackMe room difficulty fetcher (`room_difficulty_sync.py`).
- [x] TryHackMe badge scraper & showcase table generator (`badge_sync.py`).
- [x] Bounded comment markers for safe in-place README updates.

---

## Milestone 2 — Hack The Box Integration & Multi-Platform CLI (Completed)
- [x] Isolated persistent browser profile for Hack The Box (`.htb-browser/`).
- [x] Response-interception collector for HTB web app JSON payloads (`platforms/hackthebox.py`).
- [x] Versioned JSON data schema for HTB Labs and Academy (`data/hackthebox.json`).
- [x] Interactive CLI sync menu with multi-platform support (`sync-portfolio`, `portfolio.py`).
- [x] Non-interactive CLI switches (`--platform`, `--non-interactive`, `--push`).

---

## Milestone 3 — Recruiter CV Redesign & Training History Separation (Completed)
- [x] Redesign `README.md` as a concise, recruiter-facing cybersecurity CV and portfolio for **PreMortem**.
- [x] Create `TRAINING.md` for comprehensive, multi-platform activity tables.
- [x] Restructure documentation into `docs/` (`SYNC_ENGINE.md`, `AUTHENTICATION.md`, `PRIVACY.md`, `DATA_SCHEMA.md`, `ROADMAP.md`).
- [x] Modular write-up status tracking (distinguishing completed research from template stubs).

---

## Milestone 4 — Cisco Networking Academy Integration (Planned)
- [ ] Dedicated isolated session directory (`.cisco-browser/`).
- [ ] Automated sync for Cisco NetAcad course completions, badges, and certificates.
- [ ] Sanitised JSON storage (`data/cisco_netacad.json`).
- [ ] Strict public identity scrub (ensuring real name is never published, displaying course title, completion date, and skills only).
