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

## Profile Snapshot

- **Qualification:** Certificate in Cyber Security Practices — Level 3
  (603/5762/9), Think Employment — in progress
<!-- PROFILE-SNAPSHOT:START -->
- **TryHackMe evidence:** 27 completed rooms and 6 earned badges
<!-- PROFILE-SNAPSHOT:END -->
- **Key areas:** networking, Linux, web security, Python, security automation,
  embedded systems, and Android
- **Public identity:** Pre-Mortem

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
  and [lab notes](#practical-reports-and-lab-evidence) keep that evidence visible.

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
## Skills and Evidence

Each skill below is tied to work recorded in this repository — completed training, badges, projects or scripts. No self-rated scores are used.

| Skill area | Evidence |
|---|---|
| Networking | TryHackMe rooms: DNS in Detail, What is Networking?, Intro to LAN; and the Networking Nerd badge |
| Linux | TryHackMe rooms: Linux Fundamentals Part 1, Linux Fundamentals Part 2, Linux Fundamentals Part 3; and the cat linux.txt badge |
| Web security | TryHackMe rooms: Walking An Application, Content Discovery, Subdomain Enumeration, Authentication Bypass, IDOR, How Websites Work; and the Webbed badge |
| Python | Portfolio automation, platform adapters, rendering, schema validation, privacy checks, and deterministic test tooling |
| Git and GitHub | Version control, focused branches, GitHub Actions validation, and reproducible history |
| Embedded systems | PacketPunch and ESP32-S2 AI HID Typer development |
| Android | ESP32-S2 AI HID Typer companion application |
| Security automation | TryHackMe and Hack The Box evidence collection plus Cisco offline sanitisation and rendering foundation |
| Privacy and safe design | Credential checks, isolated browser state, payload limits, sanitisation, and failure-safe persistence |

## TryHackMe

**Profile:** [PreMortem](https://tryhackme.com/p/PreMortem)<br>
**Last local sync:** 28 July 2026, 15:12 UTC

<div align="center">

<table>
<tr>
<td align="center">&nbsp;<strong>Rooms Completed</strong>&nbsp;<br>27</td>
<td align="center">&nbsp;<strong>Badges Earned</strong>&nbsp;<br>6</td>
<td align="center">&nbsp;<strong>Easy</strong>&nbsp;<br>17</td>
<td align="center">&nbsp;<strong>Info</strong>&nbsp;<br>10</td>
</tr>
</table>

</div>

**Current focus:** networking fundamentals, Linux fundamentals, web security.

[TRAINING.md](TRAINING.md#tryhackme) retains the same evidence as a complete platform history.

### Completed Rooms — Recent First

| Room | Difficulty | Completed |
|---|---|---|
| [Introductory Researching](https://tryhackme.com/room/introtoresearch) | Easy | 2026-07-28 |
| [Starting Out In Cyber Sec](https://tryhackme.com/room/startingoutincybersec) | Easy | 2026-07-28 |
| [Linux Fundamentals Part 2](https://tryhackme.com/room/linuxfundamentalspart2) | Info | 2026-07-28 |
| [How Websites Work](https://tryhackme.com/room/howwebsiteswork) | Easy | 2026-07-28 |
| [Linux Fundamentals Part 3](https://tryhackme.com/room/linuxfundamentalspart3) | Info | 2026-07-28 |
| [HTTP in Detail](https://tryhackme.com/room/httpindetail) | Easy | 2026-07-28 |
| [OSI Model](https://tryhackme.com/room/osimodelzi) | Info | 2026-07-28 |
| [Packets &amp; Frames](https://tryhackme.com/room/packetsframes) | Info | 2026-07-28 |
| [Extending Your Network](https://tryhackme.com/room/extendingyournetwork) | Info | 2026-07-28 |
| [Malware Classification](https://tryhackme.com/room/malwareclassification) | Easy | 2026-07-28 |
| [The CIA Triad](https://tryhackme.com/room/theciatriad) | Easy | 2026-07-28 |
| [Linux Fundamentals Part 1](https://tryhackme.com/room/linuxfundamentalspart1) | Info | 2026-07-23 |
| [DNS in Detail](https://tryhackme.com/room/dnsindetail) | Easy | 2026-07-23 |
| [What is Networking?](https://tryhackme.com/room/whatisnetworking) | Info | 2026-07-23 |
| [Intro to LAN](https://tryhackme.com/room/introtolan) | Info | 2026-07-23 |
| [Walking An Application](https://tryhackme.com/room/walkinganapplication) | Easy | 2026-07-23 |
| [Pentesting Fundamentals](https://tryhackme.com/room/pentestingfundamentals) | Easy | 2026-07-23 |
| [Principles of Security](https://tryhackme.com/room/principlesofsecurity) | Info | 2026-07-23 |
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
✅<br><strong>25 Rooms</strong><br>Complete
</td>
<td align="center" width="120">
🚧<br><strong>50 Rooms</strong><br>27 / 50
</td>
<td align="center" width="120">
⬜<br><strong>100 Rooms</strong><br>Upcoming
</td>
</tr>
</table>

</div>

## Practical Reports and Lab Evidence

### Completed Reports

No completed reports are published yet. Reports will appear here only after their notes have been reviewed and finished.

### Lab Notes and Drafts

These files relate to completed rooms, but the write-ups themselves are still working notes or templates and are not presented as completed reports.

<details>
<summary>27 lab notes and write-up drafts</summary>

- [Authentication Bypass](writeups/tryhackme/authenticationbypass.md)
- [Careers in Cyber](writeups/tryhackme/careersincyber.md)
- [Content Discovery](writeups/tryhackme/contentdiscovery.md)
- [DNS in Detail](writeups/tryhackme/dnsindetail.md)
- [Extending Your Network](writeups/tryhackme/extendingyournetwork.md)
- [How Websites Work](writeups/tryhackme/howwebsiteswork.md)
- [HTTP in Detail](writeups/tryhackme/httpindetail.md)
- [IDOR](writeups/tryhackme/idor.md)
- [Intro to LAN](writeups/tryhackme/introtolan.md)
- [Introductory Researching](writeups/tryhackme/introtoresearch.md)
- [Linux Fundamentals Part 1](writeups/tryhackme/linuxfundamentalspart1.md)
- [Linux Fundamentals Part 2](writeups/tryhackme/linuxfundamentalspart2.md)
- [Linux Fundamentals Part 3](writeups/tryhackme/linuxfundamentalspart3.md)
- [Malware Classification](writeups/tryhackme/malwareclassification.md)
- [Metasploit: Exploitation](writeups/tryhackme/metasploitexploitation.md)
- [Metasploit: Introduction](writeups/tryhackme/metasploitintro.md)
- [Metasploit: Meterpreter](writeups/tryhackme/meterpreter.md)
- [Offensive Security Intro](writeups/tryhackme/offensivesecurityintro.md)
- [OSI Model](writeups/tryhackme/osimodelzi.md)
- [Packets &amp; Frames](writeups/tryhackme/packetsframes.md)
- [Pentesting Fundamentals](writeups/tryhackme/pentestingfundamentals.md)
- [Principles of Security](writeups/tryhackme/principlesofsecurity.md)
- [Starting Out In Cyber Sec](writeups/tryhackme/startingoutincybersec.md)
- [Subdomain Enumeration](writeups/tryhackme/subdomainenumeration.md)
- [The CIA Triad](writeups/tryhackme/theciatriad.md)
- [Walking An Application](writeups/tryhackme/walkinganapplication.md)
- [What is Networking?](writeups/tryhackme/whatisnetworking.md)

</details>

## Other Platforms in Progress

- **Hack The Box:** integration is ready; no completed labs are recorded yet.
- **Cisco Networking Academy:** the offline integration foundation is ready; no achievements have been imported yet.
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

## About the Portfolio Automation

This portfolio is updated through a privacy-conscious Python sync engine that
validates saved evidence, isolates platform failures, and regenerates only the
bounded snapshot and evidence regions without overwriting the personal CV
narrative.

Technical details are available in the
[sync engine](docs/SYNC_ENGINE.md), [authentication](docs/AUTHENTICATION.md),
[privacy](docs/PRIVACY.md), [data schema](docs/DATA_SCHEMA.md), and
[roadmap](docs/ROADMAP.md) documentation.
