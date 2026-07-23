# Cybersecurity Portfolio

A practical record of my cybersecurity training, TryHackMe progress, lab work and security engineering projects.

<!-- THM:START -->
## TryHackMe

**Profile:** [PreMortem](https://tryhackme.com/p/PreMortem)  
**Completed rooms recorded:** 16  
**Badges recorded:** 6  
**Last local sync:** 2026-07-23T11:44:41+00:00

### Recently Completed Rooms

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

### Badges

<div align="center">

<table>
<tr>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/linux.png" alt="cat linux.txt" width="100"><br>
<strong>cat linux.txt</strong>
</td>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/firstfour.png" alt="First Four" width="100"><br>
<strong>First Four</strong>
</td>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/metasploit.png" alt="Metasploitable" width="100"><br>
<strong>Metasploitable</strong>
</td>
</tr>
<tr>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/networkfundamentals.png" alt="Networking Nerd" width="100"><br>
<strong>Networking Nerd</strong>
</td>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/introtooffensivesecurity.png" alt="Pentesting Principles" width="100"><br>
<strong>Pentesting Principles</strong>
</td>
<td align="center" width="130">
<img src="https://assets.tryhackme.com/img/badges/webbed.png" alt="Webbed" width="100"><br>
<strong>Webbed</strong>
</td>
</tr>
</table>

</div>

This section is generated locally from my authenticated TryHackMe profile. Browser cookies remain on my own computer and are excluded from Git.
<!-- THM:END -->

## Using the Updater

Clone the repository onto the Mac, then run:

```bash
git clone https://github.com/Pre-Mortem/cybersecurity-portfolio.git
cd cybersecurity-portfolio
chmod +x setup sync-tryhackme
./setup
./sync-tryhackme
```

The first sync opens a separate Chrome profile used only by this updater. Log into TryHackMe in that window and press Enter in Terminal. Later runs reuse that saved login without affecting your everyday Chrome profile, saved passwords or extensions.

Each sync:

- checks the authenticated TryHackMe profile for completed rooms and badges
- compares them with the repository data
- creates a safe write-up template for each newly detected room
- regenerates this README
- commits and pushes genuine changes

The updater's browser profile is stored locally in `.thm-browser/`. It contains login data, is excluded by `.gitignore`, and must never be committed or shared.

## Lab Notes

Safe room notes are stored under [`writeups/tryhackme`](writeups/tryhackme). These notes explain what I learned without publishing flags, credentials or direct room answers.

## Security Projects

This section will link to practical cybersecurity software, hardware and research projects as they are added.

## Repository Rules

- No TryHackMe flags or copied answers
- No passwords, cookies, tokens or API keys
- No sensitive personal or client information
- Claims must be supported by completed work or evidence
