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

This section is generated locally from my authenticated TryHackMe profile. Browser cookies remain in my normal Chrome profile and are never copied into this repository.
<!-- THM:END -->

## Using the Updater

Clone the repository onto the Mac, then run:

```bash
git clone https://github.com/Pre-Mortem/cybersecurity-portfolio.git
cd cybersecurity-portfolio
chmod +x setup sync-tryhackme
./setup
```

Before syncing, fully quit Google Chrome with `Cmd+Q`. The updater uses the same Chrome profile you use every day, including its existing TryHackMe login.

For the normal Chrome profile, run:

```bash
./sync-tryhackme
```

If your daily Chrome account is stored under another profile directory, run one of these instead:

```bash
CHROME_PROFILE_DIR="Profile 1" ./sync-tryhackme
CHROME_PROFILE_DIR="Profile 2" ./sync-tryhackme
```

You can identify the active profile directory by opening `chrome://version` in your normal Chrome and checking **Profile Path**. The final folder name will usually be `Default`, `Profile 1`, `Profile 2`, and so on.

Each sync:

- opens the selected daily Chrome profile
- checks the authenticated TryHackMe profile for completed rooms and badges
- compares them with the repository data
- creates a safe write-up template for each newly detected room
- regenerates this README
- commits and pushes genuine changes

Chrome must be completely closed before the command runs because Chrome prevents two processes from using the same profile at once.

## Lab Notes

Safe room notes are stored under [`writeups/tryhackme`](writeups/tryhackme). These notes explain what I learned without publishing flags, credentials or direct room answers.

## Security Projects

This section will link to practical cybersecurity software, hardware and research projects as they are added.

## Repository Rules

- No TryHackMe flags or copied answers
- No passwords, cookies, tokens or API keys
- No sensitive personal or client information
- Claims must be supported by completed work or evidence
