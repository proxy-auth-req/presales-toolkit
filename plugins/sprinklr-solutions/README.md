# Sprinklr Solutions (Beta)

Presales tooling for Sprinklr Solutions Architects and Solution Consultants.

## Skills

**`rfp-response`** — answers a customer RFP, tender, security questionnaire or
vendor-assessment workbook end to end. Point it at a directory of customer files.

It orchestrates subagents over the question set, grounds every claim in internal
documentation, and merges answers back into the customer's own files. Alongside that it
produces an audit trail with confidence, RAG and source links, a companion narrative
document, an evidence-gap register with owners, a ranked set of vendor questions, and an
HTML status cockpit.

Handles arbitrary file structures and languages. The skill is written in English; the
artefacts it produces come out in the customer's language.

**`atlassian-retrieval`** — read-only retrieval over Confluence, Jira, JSM, Bitbucket
and the rest of the Teamwork Graph via the `twg` CLI. `rfp-response` grounds through it,
and it is useful on its own for any "what does our doc say about X" question.

## Requirements

`twg` CLI installed and authenticated — see `skills/atlassian-retrieval/references/INSTALL.md`.
Python 3 with `openpyxl` for spreadsheet-shaped tenders; the skill creates its own venv.

## Status

Beta. Proven on one full tender: 221 questions across three workbooks in German, with a
98-criterion security catalogue and a companion security concept.

Known rough edge: `build_cockpit.py` was generalised from that engagement and parses
clean, but has not been run end to end against a second configuration. Expect a small
fix on first use.
