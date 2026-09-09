# sprinklr-presales

A Claude Code plugin marketplace for Sprinklr presales. One plugin today:
**`sprinklr-solutions`** (Beta) — answering customer RFPs, tenders and security
questionnaires from Sprinklr's internal Atlassian knowledge.

**Before installing**, install and authenticate the Teamwork Graph CLI. Both skills read
through it, and without it they return nothing:

```bash
curl -fsSL https://teamwork-graph.atlassian.com/cli/install | bash
twg whoami          # must print your name and account id
```

Run that in your own terminal — the installer ends in a consent prompt.

## Install

Add the marketplace, then install the plugin:

```bash
claude plugin marketplace add <git-url-or-local-path>
```

```bash
claude plugin install sprinklr-solutions@sprinklr-presales
```

From inside an interactive Claude Code session the same two steps are
`/plugin marketplace add …` and `/plugin install sprinklr-solutions@sprinklr-presales`.

Confirm both skills registered — they will appear namespaced as
`sprinklr-solutions:rfp-response` and `sprinklr-solutions:atlassian-retrieval`.

## Prerequisites

**The `twg` CLI, installed and authenticated.** All retrieval runs through it, and
nothing in the RFP skill works without it. It is free to all Atlassian customers,
installs without admin rights, and uses your own OAuth credentials — it can surface
nothing you cannot already see.

```bash
curl -fsSL https://teamwork-graph.atlassian.com/cli/install | bash
```

Run that in your own terminal, not through Claude: it ends in an interactive consent
prompt. Then verify:

```bash
twg doctor
```

`Connectivity: ok` against a resolved token means you are ready. Full setup, repair and
headless instructions are in
[`skills/atlassian-retrieval/references/INSTALL.md`](plugins/sprinklr-solutions/skills/atlassian-retrieval/references/INSTALL.md).

**Python 3** with `venv`. The RFP skill builds its own virtualenv inside the customer
directory and installs `openpyxl` there; nothing is installed system-wide.

## Where it runs

Claude Code and Cowork on your own machine — both skills shell out to a local binary.
A hosted sandbox with no access to your `twg` install cannot do retrieval.

## Contributing

Skills live in `plugins/sprinklr-solutions/skills/`. Bump `version` in
`plugins/sprinklr-solutions/.claude-plugin/plugin.json` when you change one, so installs pick
the change up.
