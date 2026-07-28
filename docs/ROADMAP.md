# Development Roadmap

This document outlines completed milestones and future enhancements for the **Pre-Mortem Cybersecurity Portfolio & Sync Engine**.

---

## Milestone 1 — TryHackMe Integration & Base Portfolio (Completed)
- [x] Initial portfolio layout and markdown template structure.
- [x] Automated TryHackMe completed rooms collector (`room_sync.py`).
- [x] Complete numbered completed-room API pagination using the platform's
  explicit `nextPage`, `totalPages`, `totalDocs`, and page-size metadata.
- [x] Stable-code deduplication, account-total cross-checking, loop detection,
  and preserve-on-partial-result failure safety.
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
- [x] Keep visible proof on the front page: a qualification and evidence
  snapshot, evidence-backed skills, live training totals, the complete saved
  room table, earned badge cabinet, personal milestones, report links, and
  compact secondary-platform states.
- [x] Protect the introduction, qualification, key areas, About Me, project
  narratives, Current Focus, contact details, and concise automation summary
  outside the generated evidence marker.
- [x] Keep changing room and badge totals inside their own bounded snapshot
  marker so regeneration cannot overwrite the surrounding authored profile.
- [x] Keep long-form engine, authentication, privacy, schema, and roadmap
  material in `docs/` rather than making the automation dominate the README.
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
