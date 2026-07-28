# Pre-Mortem — Cybersecurity Portfolio

I am developing practical cybersecurity skills through formal study, hands-on
labs, software development, embedded systems, and security-focused hardware
tooling. I learn most effectively by building and testing real systems,
investigating what goes wrong, and documenting how I improved them.

I am currently completing a Level 3 Certificate in Cyber Security Practices
while building evidence across networking, Linux, web security, Python,
security automation, embedded systems, USB HID, Android, Git, and GitHub. I am
working towards junior opportunities where I can keep developing in defensive
security, security engineering, SOC or technical support work, embedded
security, and security tooling.

## About Me

I am developing towards a cybersecurity career through practical, repeatable
work rather than theory alone. Building tools helps me understand how
technologies behave at their boundaries: how devices discover each other, how
input becomes a hardware action, how failures propagate, and how data can be
handled without exposing private information.

I am comfortable tracing faults, testing assumptions against real behaviour,
and iterating until a system is more reliable. I value clear documentation,
evidence, privacy, and safe design. My strongest interests are defensive
security, network visibility, embedded systems, modern hardware-assisted
security work, and tools that make technical investigation more effective.

## What I Bring

- **Practical problem-solving:** I have worked through embedded HID timing and
  reliability, dynamic network discovery, emergency-stop behaviour, UTF-8 and
  keyboard-layout handling, and partial platform failures. These projects
  require testing the real system rather than assuming the first design is
  correct. See [PacketPunch](#packetpunch), the
  [ESP32-S2 AI HID Typer](#esp32-s2-ai-hid-typer), and the
  [completed-room evidence](#completed-rooms--recent-first).
- **Security-minded development:** My work uses defensive input validation,
  payload limits, isolated browser profiles, privacy scrubbing, safe
  persistence, failure isolation, and credential checks. I aim for automation
  that fails safely and does not destroy previously verified data. The
  [Skills and Evidence](#skills-and-evidence) table ties these controls to
  visible work.
- **Software and automation:** I use Python, JSON, command-line tooling,
  deterministic tests, schema validation, GitHub Actions, and generated
  documentation to turn repeatable technical work into maintainable systems.
  The [portfolio automation project](#cybersecurity-portfolio-automation)
  demonstrates that workflow.
- **Hardware and embedded systems:** My projects cover ESP32-S2 and ESP32-P4
  development, USB HID, Wi-Fi discovery, Android companion software, and
  hardware-oriented security tooling; both hardware projects are documented
  under [Selected Security Projects](#selected-security-projects).
- **Documentation and evidence:** I maintain structured technical
  documentation, milestone-based development, reproducible checks, training
  evidence, and clear Git history so that claims can be traced to work. The
  [TryHackMe evidence](#tryhackme), [achievement cabinet](#achievement-cabinet),
  and [lab notes](#practical-labs-and-reports) keep that evidence visible.

## Selected Security Projects

### PacketPunch

_In development · Private repository_

I am developing PacketPunch as a modern security hardware and software platform
for current wireless, network, and embedded technologies. The goal is to build
useful open-source hardware around modern components and real network
visibility needs, rather than reproduce older devices without reconsidering
their design.

My work currently focuses on the ESP32-P4, embedded systems, wireless security,
network visibility, and the design of practical security tooling. The project
demonstrates how I approach hardware constraints, system architecture, and the
connection between physical devices and security workflows.

_Security tools with impact._

### ESP32-S2 AI HID Typer

_In development · Private repository_

I built an ESP32-S2-based wireless HID keyboard system with an Android
companion application. It includes dynamic device discovery, emergency-stop
controls, payload limits, defensive input validation, UTF-8 handling, and UK
and US keyboard layouts.

Developing it required me to investigate HID timing and reliability against
real hardware behaviour rather than treating keyboard output as a simple text
operation. The project demonstrates embedded debugging, networked device
control, Android integration, safety controls, and iterative problem-solving
across software and hardware.

### [Cybersecurity Portfolio Automation](https://github.com/Pre-Mortem/cybersecurity-portfolio)

_Active · Public repository_

I built the Python automation behind this portfolio to collect training
evidence, validate and sanitise structured data, preserve privacy, isolate
platform failures, and update public evidence without publishing credentials or
private account information.

The system supports TryHackMe, Hack The Box, and an offline Cisco Networking
Academy foundation. It demonstrates Python and CLI development, JSON schemas,
automated testing, GitHub Actions, non-destructive persistence, and security
controls around public data. Detailed architecture is available in
[docs/SYNC_ENGINE.md](docs/SYNC_ENGINE.md).

<!-- PORTFOLIO:START -->
## Qualifications

| Qualification | Reference | Provider | Status |
|---|---|---|---|
| Certificate in Cyber Security Practices — Level 3 | 603/5762/9 | Think Employment | In progress |

Alongside formal study, I am building practical evidence through TryHackMe labs and project-based development, while preparing to expand the record through Hack The Box and Cisco Networking Academy.

## Skills and Evidence

Each skill below is tied to work recorded in this repository — completed training, badges, projects or scripts. No self-rated scores are used.

| Skill area | Evidence |
|---|---|
| Networking | TryHackMe rooms: DNS in Detail, What is Networking?, Intro to LAN; and the Networking Nerd badge |
| Linux | TryHackMe rooms: Linux Fundamentals Part 1; and the cat linux.txt badge |
| Web security | TryHackMe rooms: Walking An Application, Content Discovery, Subdomain Enumeration, Authentication Bypass, IDOR; and the Webbed badge |
| Python | Portfolio automation, platform adapters, rendering, schema validation, privacy checks, and deterministic test tooling |
| Git and GitHub | Version control, focused branches, GitHub Actions validation, and reproducible history |
| Embedded systems | PacketPunch and ESP32-S2 AI HID Typer development |
| Android | ESP32-S2 AI HID Typer companion application |
| Security automation | TryHackMe and Hack The Box evidence collection plus Cisco offline sanitisation and rendering foundation |
| Privacy and safe design | Credential checks, isolated browser state, payload limits, sanitisation, and failure-safe persistence |

## Practical Labs and Reports

### Completed Reports

No completed reports are published yet. Reports will appear here only after their notes have been reviewed and finished.

### Lab Notes and Drafts

These files relate to completed rooms, but the write-ups themselves are still working notes or templates and are not presented as completed reports.

<details>
<summary>16 lab notes and write-up drafts</summary>

- [Authentication Bypass](writeups/tryhackme/authenticationbypass.md)
- [Careers in Cyber](writeups/tryhackme/careersincyber.md)
- [Content Discovery](writeups/tryhackme/contentdiscovery.md)
- [DNS in Detail](writeups/tryhackme/dnsindetail.md)
- [IDOR](writeups/tryhackme/idor.md)
- [Intro to LAN](writeups/tryhackme/introtolan.md)
- [Linux Fundamentals Part 1](writeups/tryhackme/linuxfundamentalspart1.md)
- [Metasploit: Exploitation](writeups/tryhackme/metasploitexploitation.md)
- [Metasploit: Introduction](writeups/tryhackme/metasploitintro.md)
- [Metasploit: Meterpreter](writeups/tryhackme/meterpreter.md)
- [Offensive Security Intro](writeups/tryhackme/offensivesecurityintro.md)
- [Pentesting Fundamentals](writeups/tryhackme/pentestingfundamentals.md)
- [Principles of Security](writeups/tryhackme/principlesofsecurity.md)
- [Subdomain Enumeration](writeups/tryhackme/subdomainenumeration.md)
- [Walking An Application](writeups/tryhackme/walkinganapplication.md)
- [What is Networking?](writeups/tryhackme/whatisnetworking.md)

</details>

## TryHackMe

**Profile:** [PreMortem](https://tryhackme.com/p/PreMortem)<br>
**Last local sync:** 23 July 2026, 11:44 UTC

<div align="center">

<table>
<tr>
<td align="center">&nbsp;<strong>Rooms Completed</strong>&nbsp;<br>16</td>
<td align="center">&nbsp;<strong>Badges Earned</strong>&nbsp;<br>6</td>
<td align="center">&nbsp;<strong>Easy</strong>&nbsp;<br>15</td>
<td align="center">&nbsp;<strong>Info</strong>&nbsp;<br>1</td>
</tr>
</table>

</div>

**Current focus:** networking fundamentals, Linux fundamentals, web security.

[TRAINING.md](TRAINING.md#tryhackme) retains the same evidence as a complete platform history.

### Completed Rooms — Recent First

| Room | Difficulty | Completed |
|---|---|---|
| [Linux Fundamentals Part 1](https://tryhackme.com/room/linuxfundamentalspart1) | Easy | 2026-07-23 |
| [DNS in Detail](https://tryhackme.com/room/dnsindetail) | Easy | 2026-07-23 |
| [What is Networking?](https://tryhackme.com/room/whatisnetworking) | Easy | 2026-07-23 |
| [Intro to LAN](https://tryhackme.com/room/introtolan) | Easy | 2026-07-23 |
| [Walking An Application](https://tryhackme.com/room/walkinganapplication) | Easy | 2026-07-23 |
| [Pentesting Fundamentals](https://tryhackme.com/room/pentestingfundamentals) | Easy | 2026-07-23 |
| [Principles of Security](https://tryhackme.com/room/principlesofsecurity) | Easy | 2026-07-23 |
| [Metasploit: Exploitation](https://tryhackme.com/room/metasploitexploitation) | Easy | 2026-07-23 |
| [Content Discovery](https://tryhackme.com/room/contentdiscovery) | Easy | 2026-07-23 |
| [Subdomain Enumeration](https://tryhackme.com/room/subdomainenumeration) | Easy | 2026-07-23 |
| [Authentication Bypass](https://tryhackme.com/room/authenticationbypass) | Easy | 2026-07-23 |
| [Metasploit: Introduction](https://tryhackme.com/room/metasploitintro) | Easy | 2026-07-23 |
| [IDOR](https://tryhackme.com/room/idor) | Easy | 2026-07-23 |
| [Metasploit: Meterpreter](https://tryhackme.com/room/meterpreter) | Easy | 2026-07-23 |
| [Offensive Security Intro](https://tryhackme.com/room/offensivesecurityintro) | Easy | 2026-07-23 |
| [Careers in Cyber](https://tryhackme.com/room/careersincyber) | Info | 2026-07-23 |

### Achievement Cabinet

Earned TryHackMe badges generated from the saved canonical badge data. Each badge links to its public achievement page.

<div align="center">

<table>
<tr>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/terminaled">
<img src="https://assets.tryhackme.com/img/badges/linux.png" alt="cat linux.txt" width="100"><br>
<strong>cat linux.txt</strong>
</a>
</td>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/first-4-rooms">
<img src="https://assets.tryhackme.com/img/badges/firstfour.png" alt="First Four" width="100"><br>
<strong>First Four</strong>
</a>
</td>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/metasploitable">
<img src="https://assets.tryhackme.com/img/badges/metasploit.png" alt="Metasploitable" width="100"><br>
<strong>Metasploitable</strong>
</a>
</td>
</tr>
<tr>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/network-fundamentals">
<img src="https://assets.tryhackme.com/img/badges/networkfundamentals.png" alt="Networking Nerd" width="100"><br>
<strong>Networking Nerd</strong>
</a>
</td>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/intro-to-pentesting">
<img src="https://assets.tryhackme.com/img/badges/introtooffensivesecurity.png" alt="Pentesting Principles" width="100"><br>
<strong>Pentesting Principles</strong>
</a>
</td>
<td align="center" width="130">
<a href="https://tryhackme.com/PreMortem/badges/web-fund">
<img src="https://assets.tryhackme.com/img/badges/webbed.png" alt="Webbed" width="100"><br>
<strong>Webbed</strong>
</a>
</td>
</tr>
</table>

</div>

### Room Milestones

_Portfolio progress milestones — a personal tracker, not official TryHackMe badges._

<div align="center">

<table>
<tr>
<td align="center" width="120">
✅<br><strong>10 Rooms</strong><br>Complete
</td>
<td align="center" width="120">
🚧<br><strong>25 Rooms</strong><br>16 / 25
</td>
<td align="center" width="120">
⬜<br><strong>50 Rooms</strong><br>Upcoming
</td>
<td align="center" width="120">
⬜<br><strong>100 Rooms</strong><br>Upcoming
</td>
</tr>
</table>

</div>

## Hack The Box

**Profile:** [PreMortem](https://htb.site/PreMortem)<br>**Last local sync:** Not yet synced

Hack The Box integration is active. No completed labs recorded yet. See [TRAINING.md](TRAINING.md#hack-the-box) for complete platform metrics.

## Cisco Networking Academy

**Status:** Offline integration foundation ready; no achievements imported.<br>
_Live browser extraction remains a future milestone. Only sanitised, non-identifying achievement metadata can be rendered._

## Portfolio Statistics

| Category | Recorded Count | Description |
|---|---|---|
| Completed TryHackMe Rooms | 16 | Completed hands-on training rooms |
| Earned TryHackMe Badges | 6 | Achievement badges from completed training |
| Active Security Projects | 3 | Hardware, embedded systems, and automation |
| Lab Notes and Drafts | 16 | Clearly labelled work in progress |

## How This Portfolio Is Maintained

The evidence above is generated from versioned JSON data by [`portfolio.py`](portfolio.py). Sync operations replace only the content between the generated markers; the personal introduction, About Me, What I Bring, project narratives, Current Focus, and contact details remain manually authored outside that boundary.

### Supported Platforms

- **TryHackMe:** completed rooms, difficulty, completion dates, earned badges, and public profile metadata.
- **Hack The Box:** Labs and Academy achievement metadata where the authenticated application exposes it reliably. Flags, answers, and solution steps are never published.
- **Cisco Networking Academy:** versioned offline schema, privacy scrubber, saved-data rendering, and CLI selection. Live browser extraction is not yet implemented and is not claimed as working.

### Running the Sync Engine

The local Python CLI isolates platform failures, validates saved data, and regenerates both this public showcase and the complete [TRAINING.md](TRAINING.md) record. A failed platform sync preserves previously verified data from every other platform.

```bash
git clone https://github.com/Pre-Mortem/cybersecurity-portfolio.git
cd cybersecurity-portfolio
chmod +x setup sync-portfolio sync-tryhackme
./setup
./sync-portfolio
```

The interactive menu offers individual platforms, all platforms, regeneration from saved data, or exit. Equivalent non-interactive commands include:

```bash
python3 portfolio.py sync --platform tryhackme
python3 portfolio.py sync --platform hackthebox
python3 portfolio.py sync --platform all
python3 portfolio.py render
```

Nothing is committed automatically. After synchronisation the CLI reports per-platform outcomes and requests confirmation before any commit; pushing requires explicit authorization. On macOS, `install-desktop-shortcut` can create a local Finder launcher without storing machine-specific paths in Git.

### Local Browser Sessions

Each authenticated platform uses its own persistent local browser profile: `.thm-browser/` for TryHackMe, `.htb-browser/` for Hack The Box, and the reserved `.cisco-browser/` for future Cisco collection. These directories are Git-ignored and never logged or shared. Login, SSO, MFA, and session reset remain manual, user-controlled browser actions.

### What Is Collected

Safe public achievement metadata only: titles, names, difficulty, category, operating system, active or retired status, completion or issue dates, badges, certifications, skills where reliably exposed, and explicitly public profile identity where supported.

### What Is Never Collected

Passwords, email addresses, real names, 2FA or recovery codes, access or bearer tokens, raw cookies, session or local storage, internal account IDs, private certificate URLs or IDs, VPN configuration, flags, answers, and solution steps are excluded.

### Generated Data and Privacy

Interactive authentication uses isolated local browser profiles (`.thm-browser/`, `.htb-browser/`, and the reserved `.cisco-browser/`). Cookies, tokens, browser storage, account identifiers, private URLs, learner identity, email addresses, VPN material, flags, answers, and credentials are excluded from tracked output. Only safe public achievement metadata is rendered, and staged files are checked before publication.

### Technical Documentation

- [Sync engine architecture and CLI](docs/SYNC_ENGINE.md)
- [Authentication model](docs/AUTHENTICATION.md)
- [Privacy controls](docs/PRIVACY.md)
- [Versioned data schemas](docs/DATA_SCHEMA.md)
- [Development roadmap](docs/ROADMAP.md)

### Current Limitations

- Live account login cannot run in CI because authentication is interactive and may require SSO or MFA.
- Cisco live browser collection remains unimplemented; no endpoints have been guessed.
- Platform fields that cannot be collected reliably are left empty rather than fabricated.

### Roadmap

The multi-platform CLI, TryHackMe integration, Hack The Box integration, personal portfolio renderer, and Cisco offline foundation are complete. The next planned integration work is evidence-based Cisco browser collection after its live user journey has been inspected safely. See the [development roadmap](docs/ROADMAP.md) for milestone details.

### Repository Rules

- No TryHackMe or Hack The Box flags, copied answers, or solution steps.
- No passwords, cookies, tokens, API keys, private account data, or learner identity.
- No unfinished write-up template is presented as a completed report.
- Every public claim must be supported by saved evidence or documented project work.
<!-- PORTFOLIO:END -->

## Current Focus

I am currently:

- progressing the Level 3 Certificate in Cyber Security Practices;
- strengthening networking and Linux fundamentals;
- developing web security knowledge through hands-on labs;
- expanding practical experience across security training platforms;
- building embedded and hardware-assisted security tools;
- improving Python-based security automation and validation; and
- finishing clear, publishable write-ups for completed practical lab work.

## Contact and Profiles

I use **Pre-Mortem** as my public identity.

- [GitHub — Pre-Mortem](https://github.com/Pre-Mortem)
- [TryHackMe — PreMortem](https://tryhackme.com/p/PreMortem)
- [Hack The Box — PreMortem](https://htb.site/PreMortem)
