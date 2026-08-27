# Installing and authenticating `twg`

Read this when Step 0 of the skill found no binary, or when `twg doctor` reports no resolved token.

## 1. Check it is really missing first

Do not install over an existing setup. Both of these must fail before you conclude it is missing:

```bash
command -v twg
ls "$HOME/.local/bin/twg"
```

Windows PowerShell: `Get-Command twg` then `Test-Path "$env:LOCALAPPDATA\Programs\twg\bin\twg.exe"`.

A command error or an auth error is **not** a missing binary. Only "no such file" counts.

## 2. Install

**macOS / Linux**

```bash
curl -fsSL https://teamwork-graph.atlassian.com/cli/install | bash
```

**Windows PowerShell**

```powershell
curl.exe -fsSL https://teamwork-graph.atlassian.com/cli/install.ps1 -o "$env:TEMP\twg-install.ps1"
powershell -ExecutionPolicy Bypass -File "$env:TEMP\twg-install.ps1"
```

It installs to `~/.local/bin/twg` (macOS/Linux) or `%LOCALAPPDATA%\Programs\twg\bin\twg.exe`
(Windows), verifies the download against Atlassian's published SHA256 sums, and needs no
administrator rights. The CLI is free and available to all Atlassian customers.

If that directory is not on PATH, keep using the full path and tell the user to add it — do not
report a PATH problem as an install failure.

### If you are an agent without a controlling terminal

The installer ends in an interactive consent prompt and will fail with *"Interactive auth prompting
is unavailable … without a controlling terminal."* That is expected. Two clean options:

- **Preferred:** hand the user the install command above and let them run it in their own terminal.
  It is one command and it covers consent, login, and skills in one pass.
- Install the binary only, then let the user finish auth:
  `curl -fsSL https://teamwork-graph.atlassian.com/cli/install | bash -s -- --skip-login`

Do not auto-accept the terms consent on the user's behalf. Let them see it.

## 3. Authenticate

```bash
twg setup
```

Rerunnable, and it picks the next missing step from local state. Run it **in the foreground** and
relay each prompt to the user. They will only ever be asked for:

- **Consent** — show it, ask yes/no.
- **Email and site** — can be pre-seeded: `twg setup --user you@example.com --site yourcompany`.
- **Token** — `twg` prints a URL and offers to open the browser. The user consents to scopes there
  and grants the CLI access. Read-only scopes are enough for this skill and are the safer default.
- **Bitbucket (optional)** — offered after core setup. Setup succeeds either way; add it later with
  `twg setup bitbucket`.

`twg login` alone is enough if only the token is missing.

**Hard rules.** Interactive prompts read the controlling terminal (`/dev/tty`), not stdin, so
`echo yes | twg setup` does nothing — do not try to fake them. Never ask for, echo, log, or
summarize a token, and never pass one as a CLI flag. `twg` exits with a clear "needs an interactive
terminal" message when it cannot prompt; relay that instead of working around it.

For y/N confirmations, take the shown default (the capitalized letter) for non-destructive prompts
only. Stop and ask the user for anything destructive or hard to undo, such as uninstall or
force-overwriting existing credentials.

### No-browser / headless alternative

Every command reads credentials straight from the environment, so no login is needed if the user
sets these themselves:

```bash
export TWG_USER="you@example.com"
export TWG_TOKEN="…"      # the user sets this; never handle it yourself
```

Then verify with `twg doctor` — do not rerun `twg setup`, which requires a terminal.

## 4. Verify

```bash
twg doctor
```

Report back: binary path, auth status, selected site, and connectivity. Never include token values.
Connectivity `Status: ok` with a valid token means retrieval is ready.

## Repair, update, uninstall

- **Repair** — rerun `twg setup` (re-pass `--user` / `--site` if known).
- **Update** — `twg update && twg setup --force-auth && twg doctor`.
- **Uninstall** — `twg uninstall --dry-run` to preview, then `twg uninstall`. It removes the CLI,
  scheduled upkeep, installer-owned skills, credentials, and local configs. Confirm with the user
  before running it for real.

## Optional: Atlassian's own skill bundle

The installer also ships ~11 official `twg-*` skills (root `twg`, `twg-agentic-search`,
`twg-confluence`, `twg-jira`, and others) into `~/.agents/skills` and `~/.claude/skills`. Install or
refresh them with:

```bash
twg skills install --yes --detect-agents
```

They are broader than this skill — they cover writes, rollups, incident work, and ownership routing.
**This skill is self-contained and does not require them.** Where both are present, prefer this one
for read-only retrieval; reach for the official bundle when a task genuinely needs a surface this
skill deliberately excludes.
