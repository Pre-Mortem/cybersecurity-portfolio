# Authentication Model & Local Sessions

The **Cybersecurity Portfolio Sync Engine** uses an interactive, browser-based authentication model to collect training activity without storing user credentials or session secrets in code or repository tracking.

---

## Zero Credentials Storage Policy

The sync engine operates under strict zero-credential storage principles:

- **No Passwords**: Passwords or authentication credentials are never prompted for, passed as CLI arguments, or saved in configuration files.
- **No API Secrets or Tokens**: No long-lived session tokens, bearer tokens, or API keys are written to tracked files.
- **No Automated Auth Bypass**: Multi-factor authentication (2FA) and SSO steps are performed interactively by the user directly inside a standard Chrome window opened by Playwright.

---

## Local Isolated Browser Profiles

Each platform maintains an isolated, persistent browser profile directory located inside the local workspace:

- **TryHackMe**: `.thm-browser/`
- **Hack The Box**: `.htb-browser/`

### How Authentication Works

1. **Interactive Session**: When running a sync task (e.g. `./sync-portfolio` or `python3 portfolio.py sync`), Playwright opens a standard browser instance using the designated profile path.
2. **User Sign-In**: If the session has expired or is unauthenticated, the user signs in manually (completing 2FA/SSO in the browser window).
3. **Session Persistence**: Cookies and session state remain stored locally within `.thm-browser/` or `.htb-browser/`.
4. **Data Extraction**: Once authenticated, the engine extracts public achievement metadata directly from authenticated page loads or response payloads.
5. **Session Cleanup**: Closing or resetting a session is as simple as deleting `.thm-browser/` or `.htb-browser/`.

---

## Git Safety & Gitignore Isolation

All browser session directories are strictly ignored by `.gitignore`:

```gitignore
.thm-browser/
.htb-browser/
.htb-diagnostics/
.htb-sync-cache/
*.tmp
```

Pre-commit safety checks inside `portfolio.py` double-check that no files inside browser session directories or temporary logs are ever staged or committed to Git.
