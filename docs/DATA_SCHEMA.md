# Data Schemas

The sync engine stores portfolio data in versioned JSON files within `data/`. This document outlines the schema structure for each data file.

---

## 1. `data/rooms.json` (TryHackMe Rooms)

Stores completed TryHackMe rooms and difficulty metadata.

```json
{
  "rooms": [
    {
      "name": "Linux Fundamentals Part 1",
      "slug": "linuxfundamentalspart1",
      "url": "https://tryhackme.com/room/linuxfundamentalspart1",
      "difficulty": "Easy",
      "category": "",
      "completed": "2026-07-23",
      "writeup": "writeups/tryhackme/linuxfundamentalspart1.md",
      "source": "authenticated-browser-sync"
    }
  ]
}
```

---

## 2. `data/badges.json` (TryHackMe Badges)

Stores earned TryHackMe achievement badges.

```json
{
  "badges": [
    {
      "name": "cat linux.txt",
      "code": "terminaled",
      "image": "https://assets.tryhackme.com/img/badges/linux.png"
    }
  ]
}
```

---

## 3. `data/profile.json` (TryHackMe Profile State)

Stores top-level profile metadata for TryHackMe.

```json
{
  "username": "PreMortem",
  "profile_url": "https://tryhackme.com/p/PreMortem",
  "last_sync": "2026-07-23T11:44:00+00:00",
  "sync_method": "isolated-authenticated-browser"
}
```

---

## 4. `data/hackthebox.json` (Hack The Box Schema v1.0)

Stores Hack The Box Labs, Academy, Certifications, and identity.

```json
{
  "version": "1.0",
  "synced_at": "2026-07-23T16:00:00+00:00",
  "public_identity": {
    "username": "PreMortem",
    "profile_url": "https://htb.site/PreMortem"
  },
  "labs": {
    "rank": "Pro Hacker",
    "machines": [
      {
        "name": "Lame",
        "difficulty": "Easy",
        "operating_system": "Linux",
        "status": "completed",
        "completed_at": "2026-07-20"
      }
    ],
    "sherlocks": [],
    "challenges": [],
    "badges": []
  },
  "academy": {
    "modules": [],
    "paths": [],
    "certifications": [],
    "badges": []
  },
  "achievements": []
}
```

---

## 5. `data/evidence.json` (Custom Evidence Manifest)

Optional manifest for linking additional verified reports, certificates, or lab evidence.

```json
{
  "threat_research": [],
  "incident_analysis": [],
  "qualification_work": [],
  "security_reports": []
}
```
