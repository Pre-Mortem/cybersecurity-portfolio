# Identity & Privacy Controls

This repository serves as a public cybersecurity CV and portfolio. Privacy, security, and ethics are paramount.

---

## Public Identity

- **Public Identity**: **Pre-Mortem**
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

The Cisco schema has no fields for public identity, email, account IDs,
certificate IDs, URLs, or authentication state. Its normaliser discards unknown
fields, derives identity terms from identity-bearing source keys, rejects those
terms in public values, and removes strings containing email addresses, URLs,
tokens, cookies, session identifiers, private-key material, or local user paths.
The validator runs again before every write and the renderer refuses malformed
or unsafe Cisco data.

3. **Qualification Certificate Rules**: Public qualification records are
   restricted to the qualification title, awarding body or provider, level,
   completion status and award date. Learner numbers, certificate numbers,
   centre numbers, validation or document serials, signatures, QR/Data Matrix
   codes and certificate photographs are never stored or published. The
   `data/profile.json` qualification allow-list has no fields for them, and
   unknown fields fail profile validation before regeneration.

---

## Data Collection Boundaries

### What IS Collected (Public Achievement Metadata)
- Room and machine names, categories, tags, operating systems, and difficulty tiers.
- Completion timestamps and active/retired status.
- Publicly verifiable badges, milestones, and certifications.
- Safe public profile URLs and the public identity (**Pre-Mortem**). External
  platform usernames retain the spelling required by those platforms.

### What IS NEVER Collected or Published
- **No Flags**: `user.txt`, `root.txt`, THM/HTB flags.
- **No Solutions or Write-up Leaks**: Answers, passwords, exploits, payload files, or step-by-step solutions for active platforms.
- **No Credentials or Secrets**: Passwords, API tokens, bearer headers, SSH keys, cookies, or browser storage.
- **No Cisco Identity Data**: Real names, email addresses, account/user IDs, certificate IDs, public or private account URLs, and certificate verification URLs.
- **No Private Qualification Identifiers or Images**: Learner, certificate,
  centre, validation and serial numbers; signatures; QR/Data Matrix codes; and
  certificate photographs.
- **No Local Paths or System PII**: User home paths, internal network IPs, or local workstation names.

---

## Automated Safety Auditing

`portfolio.py` performs automated safety checks prior to staging any file for commit:

- **Forbidden Pattern Scan**: Scans data files for regex patterns matching sensitive terms (`password`, `bearer`, `authorization`, `session_id`, `flag{`, `htb{`, `thm{`, `user.txt`, `root.txt`, `BEGIN PRIVATE KEY`).
- **Staging Allow-List Enforcement**: Ensures only `README.md`, `TRAINING.md`, `docs/`, `data/`, and `writeups/` are ever staged.
