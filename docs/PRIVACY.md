# Identity & Privacy Controls

This repository serves as a public cybersecurity CV and portfolio. Privacy, security, and ethics are paramount.

---

## Public Identity

- **Public Handle**: **PreMortem**
- **Public Profile URLs**:
  - TryHackMe: `https://tryhackme.com/p/PreMortem`
  - Hack The Box: `https://htb.site/PreMortem`
  - GitHub: `https://github.com/Pre-Mortem`

---

## Real Name & PII Exclusion Policy

To maintain privacy and online identity separation:

1. **Zero Real-Name Exposure**: Real names, home addresses, local machine usernames, and email addresses are excluded from all tracked files, documentation, comments, generated outputs, commit messages, and test fixtures.
2. **Cisco Networking Academy Rules**: Internal platforms (such as Cisco Networking Academy) may require real names for official certificates. However, the public portfolio only displays non-identifying achievement details:
   - Course title
   - Completion status
   - Date achieved
   - Badge / Certificate type
   - Skills covered
   - *Real names from Cisco or any third-party issuer are strictly scrubbed before publishing.*

---

## Data Collection Boundaries

### What IS Collected (Public Achievement Metadata)
- Room and machine names, categories, tags, operating systems, and difficulty tiers.
- Completion timestamps and active/retired status.
- Publicly verifiable badges, milestones, and certifications.
- Safe public profile URLs and handle (**PreMortem**).

### What IS NEVER Collected or Published
- **No Flags**: `user.txt`, `root.txt`, THM/HTB flags.
- **No Solutions or Write-up Leaks**: Answers, passwords, exploits, payload files, or step-by-step solutions for active platforms.
- **No Credentials or Secrets**: Passwords, API tokens, bearer headers, SSH keys, cookies, or browser storage.
- **No Local Paths or System PII**: User home paths, internal network IPs, or local workstation names.

---

## Automated Safety Auditing

`portfolio.py` performs automated safety checks prior to staging any file for commit:

- **Forbidden Pattern Scan**: Scans data files for regex patterns matching sensitive terms (`password`, `bearer`, `authorization`, `session_id`, `flag{`, `htb{`, `thm{`, `user.txt`, `root.txt`, `BEGIN PRIVATE KEY`).
- **Staging Allow-List Enforcement**: Ensures only `README.md`, `TRAINING.md`, `data/`, and `writeups/` are ever staged.
