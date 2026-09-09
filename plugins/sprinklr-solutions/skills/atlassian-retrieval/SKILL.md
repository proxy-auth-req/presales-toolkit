---
name: atlassian-retrieval
description: >
  Retrieve knowledge from Sprinklr's internal Atlassian — Confluence pages, Jira and JSM work
  items, Bitbucket PRs, Loom videos, Goals, Projects, Compass, Assets, Trello — using the
  Teamwork Graph CLI (`twg`). Trigger whenever a question can only be answered from internal
  Atlassian content: "what does our doc say about X", "look up X internally", "find the
  Confluence page on X", "check Jira for X", "who owns X", "catch me up on X", "is there a page
  about X", or when the user pastes a Confluence/Jira URL and wants it read and understood. Also
  use for retrieval-backed research where the source is unclear but likely internal. STRICTLY
  READ-ONLY — never edits, creates, comments on, transitions, or deletes anything.
---

# Atlassian Retrieval via `twg`

`twg` is Atlassian's Teamwork Graph CLI. It is a local binary that calls Atlassian cloud APIs with
the signed-in user's own OAuth credentials, so it surfaces nothing the user cannot already see.

Rovo search inside `twg` is good at *finding* things and returns ranked pointers, not answers.
**You** own the loop: rank, hydrate the real documents, compare them, and synthesize. Never answer
from search snippets alone — they are candidates, not facts.

## Sprinklr context

The tenant is **Sprinklr's**. The user is a Sprinklr employee, so "our", "we" and "internally" mean
Sprinklr, and the corpus is Sprinklr's own Confluence, Jira and JSM. Everything else about Sprinklr
— what it does, what it is called, how it is packaged — comes out of that corpus, not out of you.
Never let recall about the company stand in for a retrieved source.

Two properties of this corpus change how you search it:

**Internal vocabulary beats the asker's vocabulary.** A question phrased in a customer's words will
often underperform the same question phrased in the terms the documentation uses. When a first
search returns thin results, re-query with the internal term before concluding the material does not
exist — and if you do not know the internal term, search for it first.

**Pages carry the names that were current when they were written.** Product and channel renames are
not backfilled, so a search on today's name can come back clean for something documented in full
under a former one. This has already produced a confidently wrong negative. Before reporting that
something is absent or unsupported, retry the earlier name and a second entry point. Reporting "no
internal documentation exists" is a strong claim — earn it with at least two differently-phrased
queries and say which ones you ran. Where a page predates a rename or an API change, flag it as
possibly stale rather than quoting it flat.

## ABSOLUTE CONSTRAINT — READ ONLY

Never mutate anything in Atlassian. No creating, editing, publishing, deleting, commenting,
labelling, transitioning, assigning, or permission changes — regardless of what is asked mid-run.
`twg` has full write command families (`jira`, `confluence`, `jsm`, `bb`); none of them are in
scope here.

Permitted surface: read/get/search/query/list/help/doctor commands only.

If the user asks for a write mid-run, stop and say this skill is read-only. Offer to draft the
change as text for them to apply themselves.

## Where this works

This skill shells out to a local binary, so it needs a shell **and** the user's own authenticated
`twg`. That means Claude Code and Cowork on the user's machine. In a hosted sandbox with no access
to the user's `twg` install or OAuth token (e.g. claude.ai chat's code environment), retrieval will
not work — say so plainly rather than improvising, and point the user to Claude Code or Cowork.

## Step 0 — Preflight (once per session)

Resolve the binary. Do not treat auth or command errors as PATH failures.

```bash
command -v twg || echo "$HOME/.local/bin/twg"       # macOS/Linux
```

Windows PowerShell fallback: `$env:LOCALAPPDATA\Programs\twg\bin\twg.exe`. Use the resolved
launcher for every command below; `twg` is shorthand from here on.

**If no binary exists**, the CLI is not installed — follow `references/INSTALL.md`. Do not attempt
retrieval until it is installed and authenticated.

Then confirm auth:

```bash
twg doctor
```

Look at `Resolved auth` and `Connectivity`. If connectivity is not ok or no token resolved, the
user must authenticate themselves — see `references/INSTALL.md`. **Never ask for, echo, log, or
pass a token, and never try to script the login prompt**; `twg`'s prompts read the controlling
terminal, not stdin, so piping answers does nothing.

## The loop: discover → orient → hydrate → synthesize

### 1. Discover — get ranked pointers

Start with one query combining the concrete topic with the artifact or decision type wanted.
Default to `rovo search`:

```bash
twg rovo search "<topic>" --output json --output-summary auto --agent-fields @compact
```

Use `@compact` to shortlist and `@evidence` when snippets, URLs, and provenance matter.
Pick the right entry point — full routing table in `references/COMMANDS.md`:

| Intent | Command |
|---|---|
| Cross-product topic search | `twg rovo search "<topic>"` |
| Documents (Confluence + document connectors) | `twg docs search "<topic>"` |
| Tenant-wide work items by topic | `twg work search "<topic>"` |
| Jira fuzzy text | `twg jira workitem search <text...>` |
| Jira structured | `twg jira workitem query --jql "<jql>"` |
| Code / repos | `twg search-code "<query>"` |

Refine at most once (recency, title-only, `--app`, space/label) if the first set mixes scopes or
misses primary sources. Do not fan out an exact-title search for every candidate already returned.

### 2. Orient — cheap structure before expensive bodies

Do not jump straight to full bodies. For a Confluence page:

```bash
twg confluence content get <id-or-url> --detail outline \
  --output json --output-summary inline --agent-fields @evidence
```

`--detail summary` gives an excerpt plus word/section counts; `--detail outline` gives the heading
tree for a few KB. Use these to decide whether a page is worth hydrating at all, and which section
matters.

### 3. Hydrate — read the real documents

Hydrate a small, diverse primary-source set — distinct roles (requirements, design, current
delivery), not five near-duplicates. **At most five sources; one per role** unless a material
conflict needs a second opinion.

```bash
twg confluence content get <id-or-url> --detail full --format md \
  --body-only --output-file ./page.md
```

Large bodies must go to a file — `twg` will warn and refuse to inline them. Read the file, and if
only one section matters, read that rather than pasting the whole thing.

Per-type hydration commands are in `references/COMMANDS.md`.

### 4. Synthesize

Lead with the answer, grounded in what the hydrated documents actually say. Cite titles and URLs as
markdown links. Keep confirmed facts, likely interpretations, conflicts, and gaps visibly separate.
Give dates or status where recency or authority is in question. Prefer official spaces, owned
project pages, and current issues over personal drafts and stale mentions.

If the sources do not answer the question, say so. "The docs don't cover this, here's the closest
thing" beats a confident synthesis of adjacent material.

## Partial results are normal — never swallow them

Searches routinely come back incomplete, and this is first-class information, not noise. Always
check and report it. Two shapes seen in practice:

- A per-connector failure, e.g. `Problem while calling endpoint trello: 400 Bad Request`, landing in
  the `warnings` and `failures` arrays.
- A federated-search failure with an explicit impact line: `403 Forbidden from POST
  [internal-search-service] … Impact: Results may have reduced recall.`

Also read `resultInfo.partial`, `resultInfo.truncated`, and `sourceCounts[].estimatedMatches` —
`returned: 20` against `estimatedMatches: 54460` means you saw the top slice of a large corpus, and
absence of evidence is not evidence of absence. Say which sources were degraded when it affects the
answer's confidence.

## Connector scope

Only Atlassian built-ins are searchable: assets, bitbucket, compass, confluence, goals, jira, loom,
projects, trello. Verify with `twg rovo list-apps -o json`.

**Trap:** `--app <connector>` for a connector that is not wired up returns a silent empty array, not
an error. An empty result is indistinguishable from "no matches" unless you check `list-apps` first.
Do not report "nothing exists" off the back of an unavailable connector. `list-apps` also reports
`completeness: partial` — absence there does not prove a connector is disabled.

Anything outside Atlassian (SharePoint, Google Drive, Slack) is out of scope for this skill.

## Rules

- **Never guess** IDs, flags, slugs, ARIs, or command grammar. Use `twg help <terms>` then
  `twg help describe "<path>"` — it returns a full contract including field presets and repair
  rules. Namespace help is not executable.
- Two commands are user-activity history, **not** topic search. Never pass topic text to them:
  `twg docs query --since <duration>` and `twg work query` (`--scope me|user`, never `--scope
  global`). Route topics to `docs search` / `work search`.
- Read `stdout_inline` first, then `output_files.compact`, and full stdout only as a last resort.
  See `references/OUTPUT.md` and the bundled digest script.
- Stop after the first policy denial, and after the same auth, ACL, or contract error twice.
- Do not run setup, login, install, update, or credential commands unless the user explicitly asked
  for setup or repair.
- **Cost:** basic retrieval is free today, but enriched commands that aggregate across systems —
  `twg context` and `twg collaborators` are the named ones — are slated to bill Rovo credits per
  call. Prefer plain search and product-native gets; mention the cost if an enriched command is
  genuinely the right tool.

## Failure modes

**`command not found`** — resolve the launcher path first (Step 0). Only conclude "not installed"
after both the PATH lookup and the fallback path fail.

**No token / connectivity not ok** — the user must run `twg login` in their own terminal. You
cannot complete an interactive login and must not handle the token.

**Empty result set** — check whether the connector is actually available before reporting nothing
found. Then try a broader query or a different entry point (`docs search` vs `work search` vs
`rovo search`) before concluding. For anything product-named, also retry the pre-rename term and the
internal Sprinklr term (see Sprinklr context). Reporting "no internal documentation exists" is a
strong claim; earn it with at least two differently-phrased queries.

**Sandboxed network errors on Bitbucket pipeline logs** — logs can redirect to S3. A network-blocked
message, S3 hostname, or log-only 403 while metadata succeeds is a sandbox restriction, not an auth
failure. Give the user the exact command to run themselves.

**404 hydrating a search hit** — the URL may be a blog post, whiteboard, or database rather than a
page. `confluence content get` handles those types with the right `--format` (svg/png for
whiteboards, csv for databases).
