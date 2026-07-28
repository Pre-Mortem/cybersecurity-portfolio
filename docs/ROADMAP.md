# Development Roadmap

This document outlines completed milestones and future enhancements for the **Pre-Mortem Cybersecurity Portfolio & Sync Engine**.

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
- [x] Redesign `README.md` as a personal-first, recruiter-facing cybersecurity portfolio for **Pre-Mortem**.
- [x] Keep visible proof on the front page: evidence-backed skills, live training
  totals, the complete saved room table, earned badge cabinet, personal
  milestones, report links, platform states, privacy rules, technical links,
  and concise portfolio statistics.
- [x] Protect the introduction, About Me, project narratives, Current Focus, and
  contact details outside the generated markers.
- [x] Create `TRAINING.md` for comprehensive, multi-platform activity tables.
- [x] Restructure documentation into `docs/` (`SYNC_ENGINE.md`, `AUTHENTICATION.md`, `PRIVACY.md`, `DATA_SCHEMA.md`, `ROADMAP.md`).
- [x] Modular write-up status tracking (distinguishing completed research from template stubs).

---

## Milestone 4 — Cisco Networking Academy Integration (In Progress)

### Architecture and Offline Foundation (Completed)
- [x] Reserve and Git-ignore the dedicated isolated session directory (`.cisco-browser/`).
- [x] Add the isolated Cisco platform module (`platforms/cisco_netacad.py`).
- [x] Define and validate sanitised schema v1 storage (`data/cisco_netacad.json`).
- [x] Add allow-list normalisation, identity-field removal, sensitive-text scrubbing, atomic writes, and preserve-on-failure behaviour.
- [x] Integrate Cisco into CLI platform selection and saved-data rendering for `README.md` and `TRAINING.md`.
- [x] Add deterministic offline fixtures and tests for valid, partial, malformed, and identity-leaking input.

### Interactive Browser Collection (Next)
- [ ] Inspect the live Cisco NetAcad user journey through the isolated browser profile without guessing endpoints.
- [ ] Support manual login, SSO, and MFA in the user-controlled browser window.
- [ ] Collect course completion metadata and completion dates from reliably observed page data.
- [ ] Collect badges, certificates, and associated skills only where reliably exposed.
- [ ] Validate the live collector against the schema and privacy boundary before enabling successful Cisco sync status.

Live Cisco collection is **not implemented yet**. The current CLI selection
reports that limitation and preserves all saved platform data.
