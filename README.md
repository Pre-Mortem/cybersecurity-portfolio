# Cybersecurity Portfolio

A practical record of my cybersecurity training, TryHackMe progress, lab work and security engineering projects.

<!-- THM:START -->
## TryHackMe

**Profile:** [PreMortem](https://tryhackme.com/p/PreMortem)  
**Completed rooms recorded:** 0  
**Badges recorded:** 0  
**Last local sync:** Not yet synced

### Recently Completed Rooms

| Room | Difficulty | Completed |
|---|---|---|
| No rooms recorded yet | — | — |

### Badges

- No badges recorded yet

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
