# Output envelope and context discipline

`twg` is built for agents: it writes the full JSON payload to a temp file and prints a small YAML
envelope naming it. Work with that design instead of forcing everything into context.

## The envelope

```yaml
output_files:
  stdout: "/…/run.hEU0Iy/stdout.json"       # full payload
  stdout_bytes: 22746
  compact: "/…/run.hEU0Iy/stdout.compact.json"   # trimmed projection
agent_output:
  summary: "auto"
  fields: ["items.id", "items.title", "items.url", "items.type", "items.snippet"]
  fields_unresolved: ["items.name"]
stdout_inline:
  items: …                                   # present when the payload is small enough
```

**Reading order, cheapest first:**

1. `stdout_inline` — use it whenever it is there and complete.
2. `output_files.compact` — the trimmed projection.
3. `output_files.stdout` — full payload, last resort.

`--output-summary auto` (the default worth using) inlines small payloads and summarizes large ones.
`inline` forces inlining — fine for an outline, wasteful for a 60KB body. `stats` gives file and
shape statistics only.

`fields_unresolved` just means a preset path did not apply to that command. Harmless.

## The digest script

`scripts/twg-digest.py` collapses any of these shapes into ranked hits plus partial-result state.
It handles the three collection layouts `twg` uses (`items`, `data.items`, and a bare `data` list)
plus hydrated entities, so you do not have to guess where the results live.

```bash
# pipe the envelope straight in — it resolves the payload path itself
twg rovo search "<topic>" --output json --output-summary auto --agent-fields @compact \
  | python3 scripts/twg-digest.py - --snippets

# or point it at a payload file
python3 scripts/twg-digest.py /…/run.hEU0Iy/stdout.json --limit 30
```

Flags: `--limit <n>` caps printed items (default 20), `--snippets` includes result text.

For a hydrated page it prints identity, word and section counts, and the heading tree — which is
usually enough to decide whether the full body is worth reading.

Python 3 with no third-party dependencies. If it is unavailable, read `stdout_inline` directly; the
script is a convenience, not a requirement.

## Keeping bodies out of context

Large bodies must be written to a file:

```bash
twg confluence content get <id-or-url> --detail full --format md \
  --body-only --output-file ./page.md
```

`twg` refuses to inline a large body and tells you to do exactly this. Then read the file — and if
only one section matters, read that section rather than the whole page. Orient with `--detail
outline` first so you know which section that is.

Budget deliberately: a top-K search is a few KB, an outline a few KB, a full page tens of KB. Five
full pages will cost more context than the answer is worth. Narrow in discovery, orient, then
hydrate only what carries the answer.

## Partial results

Always inspect and report these — the digest script prints all of them automatically:

| Field | Meaning |
|---|---|
| `resultInfo.partial` | At least one source failed or was degraded |
| `resultInfo.truncated` | More matches exist beyond what was returned |
| `sourceCounts[].returned` / `.estimatedMatches` | `returned: 20` against `estimatedMatches: 54460` means you saw the top slice |
| `warnings[]` | Human-readable degradation notices |
| `failures[]` | Structured per-source failures with `source`, `operation`, `message`, `code` |
| `completeness.status` + `.caveat` | On `list-apps`: `partial` means the inventory itself is provisional |

Real examples, both observed on ordinary queries:

```
Rovo search DataFetchingException: Problem while calling endpoint trello:
  400 Bad Request from GET [internal-search-service]

Partial search failure
  Source: Rovo federated search
  Error: Problem while calling endpoint api_search: 403 Forbidden from POST [internal-search-service]
  Impact: Results may have reduced recall.
```

A degraded search is still useful — but say which sources were degraded when it bears on
confidence, and never convert a truncated top-K into "that's all there is."
