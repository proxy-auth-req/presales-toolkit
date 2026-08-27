# Command reference

Verified against `twg` v1.2.5. Commands marked ✅ were run end to end against a live Atlassian site;
the rest come from the CLI's own contracts. **Never guess grammar** — confirm with
`twg help describe "<path>"`, which returns args, options, field presets, and repair rules as JSON.

Every command below is read-only.

## Discovery — ranked pointers, not answers

### Cross-product topic search ✅

```bash
twg rovo search "<topic>" --output json --output-summary auto --agent-fields @compact
twg rovo search "<topic>" --output json --output-summary auto --agent-fields @evidence
twg rovo search "<topic>" --limit 20 --app jira
```

`@compact` shortlists (id, title, url, type, snippet); `@evidence` adds provenance detail. Returns a
flat top-K mixing sources — a default query returned 10 Confluence + 10 Jira hits in ~3s.

`--app <connector>` preflights connector auth. List valid values first:

```bash
twg rovo list-apps -o json          # alias: list-connectors
```

Only Atlassian built-ins are available: assets, bitbucket, compass, confluence, goals, jira, loom,
projects, trello. An unavailable `--app` returns an **empty array, not an error**.

### Documents ✅

```bash
twg docs search "<topic>" --limit 10 --output json --output-summary auto --agent-fields @compact
```

Fuzzy discovery across Confluence and ready document connectors. Returns useful inline snippets, so
it is often the cheapest first move for "is there a doc about X".

### Work items ✅

```bash
twg work search "<topic>" --limit 5 --output json --output-summary auto --agent-fields @compact
```

Tenant-wide fuzzy work discovery. Returns items under `data.items`.

### Jira, three distinct routes

```bash
twg jira workitem search <text...>            # fuzzy text, JQL-backed
twg jira workitem query --jql "<jql>"         # structured
twg rovo search "<text>" --app jira           # semantic
```

### Code

```bash
twg search-code "<query>"
```

Omit `--app` so all indexed SCM surfaces are searched; use `--repo` only as a discovery anchor and
widen after generated-doc or incomplete hits.

### Two traps — activity history, not topic search

```bash
twg docs query --since <duration> [--account-id <id>] [--first <n>]
twg work query --scope me|user
```

Both are **user activity history**. Never pass topic text to them. `work query` defaults to seven
days of authored work and must never be given `--scope global`. Route topics to `docs search` /
`work search`.

## Hydration — the actual content

### Confluence ✅

```bash
# orientation, a few KB
twg confluence content get <id-or-url> --detail outline \
  --output json --output-summary inline --agent-fields @evidence

# excerpt + word/section counts
twg confluence content get <id-or-url> --detail summary

# full body to a file
twg confluence content get <id-or-url> --detail full --format md \
  --body-only --output-file ./page.md

# version and author provenance
twg confluence content get <id-or-url> --include-metadata --agent-fields @metadata
```

Accepts a numeric content ID, a page ARI, or a Confluence URL — **not** a title or space key.
`--format`: `md` (alias `markdown`, lossy) or `html` for documents; `svg`/`png` for whiteboards;
`csv` for databases; `url` for embeds and smart links. Handles page, blogpost, whiteboard, database,
folder, and custom-content types, which is why a "404" on a search hit usually means wrong type
assumption rather than a missing page.

A 60KB body will not inline — `twg` warns and tells you to re-run with `--output-file`. Comply
rather than fighting it.

### Jira ✅

```bash
twg jira workitem get <KEY> --output json --output-summary auto --agent-fields @compact
```

The key is positional (`--key` is compatibility only). `@compact` returns key, summary, status,
assignee, and url — identity and state, not the description or comments. When the body or
discussion matters, check `twg help describe "jira workitem get"` for the right field paths rather
than guessing flags.

### Other surfaces

```bash
twg loom get <id>                       # transcript preview + file-backed full transcript
twg bb pull-requests get <id>
twg bb repo get
twg jsm ...                             # service desk requests, incidents, approvals
twg goals get <KEY>                     # key is positional
twg projects get <KEY>                  # key is positional
twg assets search | assets query --aql "<aql>" | assets object get
```

### Cross-system context — costs credits

```bash
twg context get <reference>
twg collaborators
```

`context get` resolves an Atlassian ARI into a product-neutral envelope aggregating cross-system
context around one work item, page, or user. These are the named **enriched** commands slated to
bill 1+ Rovo credit per call. Prefer plain search plus product-native gets; say so if one of these
is genuinely the right tool.

## Resolution helpers

```bash
twg resolve "<natural language reference>"     # → canonical ARIs
twg user search "<name>"
twg help "<terms>"                             # find commands
twg help describe "<path>"                     # exact contract for one command
twg help discover-skills "<intent>"
```

Namespace paths return YAML routing maps and are not executable; only leaf paths run.

## Global flags worth knowing

| Flag | Effect |
|---|---|
| `--output json\|jsonl\|text` | `text` is the default and is for humans; use `json` for anything you parse |
| `--output-summary stats\|auto\|inline` | `auto` inlines small payloads and summarizes large ones; `inline` always inlines. Requires `--output json`/`jsonl` |
| `--agent-fields <paths\|@preset>` | Trimmed projection for agent stdout. Presets: `@compact`, `@evidence`, `@metadata`, `@rows` |
| `--select <paths>` | Filters the payload itself, not just the summary |
| `--limit <n>` | Cap results on search commands |
| `--site <prefix>` | Override the configured Atlassian site |
| `--timeout-ms <ms>` | Per-request HTTP timeout |

Presets vary per command — `twg help describe` lists the exact `agentFieldPresets` for each. A
preset path that does not apply shows up as `fields_unresolved` in the envelope and is harmless.
