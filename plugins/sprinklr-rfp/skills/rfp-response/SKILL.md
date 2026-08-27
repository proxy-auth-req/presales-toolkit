---
name: rfp-response
description: >
  Draft a complete, auditable response to a customer RFP, RFI, tender, security
  questionnaire, or vendor-assessment workbook by orchestrating subagents over the
  question set. Point it at a directory of customer files. Trigger on "answer this
  RFP", "fill in this questionnaire", "respond to this tender", "we got a security
  questionnaire", "Anforderungskatalog", "Kriterienkatalog", "vendor assessment",
  or any request to answer many customer questions from internal knowledge. Handles
  arbitrary file structures and languages. Produces answers merged back into the
  customer's own files, plus an internal state file with confidence, RAG, source
  links and owners, a companion narrative document, an evidence-gap register, and
  a ranked set of vendor questions. Grounds every claim in Sprinklr's internal
  documentation through the `atlassian-retrieval` skill; never answers from model
  priors.
---

# RFP response orchestration

You are the orchestrator. Your context is the scarce resource — protect it. Subagents
do the reading, retrieval and drafting; you do discovery, scoping, batching,
cross-batch consistency, merging and reporting.

**Read `references/playbook.md` before starting.** It carries the failure modes this
skill exists to prevent, each one learned by making the mistake.

## Who we are

The vendor is **Sprinklr** — a unified customer experience management (CXM) platform.
The user is a Sprinklr employee, normally a Solutions Architect or Solution Consultant
in presales. "We", "our platform" and "the solution" mean Sprinklr throughout, and
every answer is written as Sprinklr addressing a prospect or customer.

What Sprinklr actually does — which product carries which capability, how modules are
packaged, what a given SKU entitles — is **not** knowledge this skill holds. It is
retrieved, every time, like any other claim. Model recall about Sprinklr's portfolio is
a prior, and priors are exactly what this architecture exists to keep out of a bid.
See `references/playbook.md` §13.

**Role boundary — this constrains what may be written.** An SC or SA states what is
documented: capability, architecture, documented limits. Pricing, discounts, scope
commitments, contractual SLA levels and effort estimates belong to the AE, Deal Desk
or Legal. Never write a commercial commitment into a customer file, and never put a
commercial decision to the user as though it were theirs — route it by naming the
owner. "This document is provided as evidence" is fine. "This will be agreed as part
of the offer" is not.

## Non-negotiable architecture

1. **Subagents never write to a customer file.** Each owns exactly one
   `_work/answers/<batch>.json`. You are the sole writer to source documents.
   This is what makes parallelism safe.
2. **The state file is generated, never hand-edited.** Regenerate from the answer
   JSONs. No write contention, ever.
3. **Customer-facing and internal content live in separate fields from the start.**
   Never one field doing both jobs — see playbook §1, the most expensive mistake.
4. **Every claim carries its source.** When one batch reuses another's work, the
   citation travels with the claim. A claim is not grounded because someone else
   grounded it.
5. **Nothing reaches a customer file until the validator passes.**
6. **Audit data never enters the customer's file.** Confidence, sources, POCs, host
   tags, caveats live only in `_work/` and the state file.

## Preconditions — verify before anything else

This skill is worthless without retrieval. Establish both of these before Phase 0 and
**stop if either fails**. Do not scaffold, do not spawn agents, do not fall back to
model priors or the public web.

**1. Resolve the retrieval skill identifier.** The expected backend is
`atlassian-retrieval`, which ships alongside this skill. Its invocation name depends
on how it was installed — bare `atlassian-retrieval` for a user- or project-level
skill, `<plugin>:atlassian-retrieval` when it arrives inside a plugin. Read the exact
identifier off the available-skills listing rather than assuming it, and record the
resolved string; every drafting agent is handed it verbatim.

If `atlassian-retrieval` is genuinely absent, ask the user which retrieval skill to
use before continuing. Do not silently substitute a general-purpose search skill, and
never substitute WebSearch — public web results are not internal documentation and
are not an acceptable source for a bid.

**2. Confirm the backend is authenticated.**  For `atlassian-retrieval`:

```bash
command -v twg || echo "$HOME/.local/bin/twg"
twg doctor
```

Connectivity `ok` against a resolved token means retrieval is live. Anything else is a
setup problem the user must fix in their own terminal — point them at the retrieval
skill's `references/INSTALL.md`. Five drafting agents against a dead backend produce a
wall of red and burn hours; catching it here costs thirty seconds.

## Phase 0 — Discovery

Inspect the directory yourself. Do not delegate this; you need the structure in your
own head to batch sensibly.

For each file: what sheets/sections exist, where questions live, where answers go,
what answer format is expected, what columns are the customer's versus ours, whether
any work already exists, and what language it is in.

Watch for:
- **No prose answer column.** Common in formal criteria catalogues: they want a
  verdict plus a pointer to a companion document. That changes the deliverable
  fundamentally — ask (Phase 1).
- **Internal working columns** a colleague added (owner, status, comments). Follow
  their existing convention rather than inventing a parallel one.
- **Partial prior work.** Never overwrite it.
- **Instructions embedded in the sheet** — header rows, legends, "please put an x in
  columns E–H", weighting schemes, scoring multipliers. These are binding format
  rules and are easy to miss.
- **Criterion types** (mandatory/qualifying vs scored/optional). Mandatory failures
  are eligibility risk, not point loss. This drives prioritisation everywhere.
- **Defects in the customer's own document** — unreplaced placeholders,
  self-contradictory requirements. These are the best vendor questions you will find.

## Phase 1 — Scope with the user

Ask only what materially changes the work. Typically:

- **Output format** where there is no prose column: verdict only, or verdict plus a
  companion document you also draft?
- **Language** — mirror the customer's. If the file is bilingual, which column is
  authoritative?
- **Depth per section** — full answers everywhere, or triage some?
- **Product scope** — exactly what are we bidding? Get the module names from the user;
  do not supply them from recall. A native module versus a partner product changes
  every answer, and so does which product carries the capability (playbook §13).
- **Deployment context** — the variables that change answers: hosting provider,
  region, data residency, tenancy model, on-prem vs SaaS. Get these explicitly; they
  are usually decisive and usually under-documented internally.
- **Merge cadence** — merge per wave after review, or hold until the end.

Do not ask what you can determine yourself, and do not ask commercial questions — see
the role boundary above.

## Phase 2 — Scaffold and configure

Create `_work/` inside the customer directory:

```
_work/
├── config.json        what the source files are and where answers go
├── CONTRACT.md        the brief every drafting agent reads
├── inventory/         extracted questions, one JSON per source
├── answers/           one JSON per batch — agent-owned
├── backups/           timestamped, before every write
└── .venv/             python dependencies for the scripts
```

### Resolve paths once, then write them down

Two absolute paths drive every command below: this skill's directory and the customer
directory. Resolve both now and record them at the top of `_work/CONTRACT.md`.
**Shell state does not persist between tool calls in most hosts**, so treat the
variables here as shorthand and substitute the literal paths you recorded into each
command you actually run.

```bash
RFP_DIR=/absolute/path/to/customer/dir

RFP_SKILL=$(for d in \
  "$CLAUDE_PLUGIN_ROOT/skills/rfp-response" \
  "$PWD/.claude/skills/rfp-response" \
  "$HOME/.claude/skills/rfp-response" \
  "$HOME/.agents/skills/rfp-response" \
  "$HOME/Library/Application Support/Claude"/local-agent-mode-sessions/skills-plugin/*/*/skills/rfp-response ; do
    [ -f "$d/scripts/rfp_lib.py" ] && printf '%s' "$d" && break
  done)
echo "skill dir: ${RFP_SKILL:-UNRESOLVED}"
```

If the resolver comes up empty, you read this file from somewhere — use that directory.

### Python environment

The scripts need `openpyxl` for xlsx, and system Pythons are routinely
externally-managed. Build the venv **inside `_work/`**, never under `/tmp`, which can
be cleaned between sessions:

```bash
python3 -m venv "$RFP_DIR/_work/.venv"
"$RFP_DIR/_work/.venv/bin/python" -m pip install --quiet --upgrade pip openpyxl
```

Use `"$RFP_DIR/_work/.venv/bin/python"` as the interpreter for every script from here
on (Windows: `_work/.venv/Scripts/python.exe`). Record that path in the contract too.

### Config and inventory

Write `config.json` from discovery — see `references/config-schema.md`. Set
`forbidden_terms` now (competitor names, other customers' environments, wrong hosting
providers), and add `leak_patterns` for the answer language: the validator's built-in
guards cover German and English only, so a French, Italian or Spanish tender needs its
own patterns for internal-document references and shouty capitalised negations.

```bash
cd "$RFP_DIR" && "$RFP_DIR/_work/.venv/bin/python" "$RFP_SKILL/scripts/extract_inventory.py"
```

All scripts resolve `_work/` from `RFP_DIR`, defaulting to cwd — hence the `cd`.

For formats the extractor does not handle (PDF, Word, portal exports), convert first
or have a subagent write the inventory JSON directly in the same shape. Everything
downstream only depends on the inventory shape, not the source format.

### The contract

Copy `references/contract-template.md` to `_work/CONTRACT.md` and fill in deal context,
deployment context, language, tone, the resolved paths above, and the retrieval skill
identifier resolved in Preconditions. **The contract is the single source of truth for
agents.** When you learn something mid-run that agents must know, update the contract,
not just the next prompt.

## Phase 3 — Batch by topic

Group by *underlying subject*, not row ranges — retrieval cost is per topic. 8–20
items per batch.

**Sequence matters.** Find the file with the densest shared facts (usually the
security or platform catalogue) and run it first. Other files then reuse settled
answers instead of re-deriving them and contradicting each other. This is the single
biggest efficiency and consistency win available.

Write the batch map to `_work/inventory/batches.json` so coverage is machine-checkable:

```json
{"sec-auth": {"ids": ["G-SEC-16", "G-SEC-17"], "label": "Authentication",
              "section_base": 5, "subsection_start": 1}}
```
Assign each batch its companion-document section numbers up front so concurrent agents
cannot collide.

## Phase 4 — Draft in parallel

Run 3–5 concurrently. More risks throttling the retrieval backend and floods review.

Every prompt must carry: read the contract in full; your exact scope; **ground every
claim through the retrieval skill named in the contract, invoked with the Skill tool**;
the settled positions established by earlier batches (list them explicitly — agents
cannot see each other); deployment-context rules; write one file only; run the
validator and iterate until clean.

Pass the resolved retrieval skill identifier verbatim. An agent that cannot find the
skill under the name it was given will improvise, and improvised grounding is exactly
what this architecture exists to prevent.

Instruct **chunked writes** — rewrite the whole answer file after every 3–5 completed
items. Infrastructure failures are common on long runs; this makes progress durable.

If a run is long, hold a wake lock (`caffeinate -i -t <seconds>` on macOS). Sleep-induced
stream stalls were the dominant failure mode in practice.

## Phase 5 — Validate and reconcile

```bash
cd "$RFP_DIR" && "$RFP_DIR/_work/.venv/bin/python" "$RFP_SKILL/scripts/validate_answers.py"
```

Exits non-zero on any error. Catches schema violations, missing/duplicate coverage,
invalid enums, ungrounded claims, section collisions, leaked internal text, and
confidence/RAG mismatches.

**Then do the job only you can do: cross-batch consistency.** Agents cannot see each
other. Look for two answers resting on the same fact with different confidence
signals, one file contradicting another, and absolute claims in one file falsified by
a finding in another. When you find one, send the owning agent back with the specific
contradiction and the reasoning — do not fix it yourself; the agent has the context.

Verify agent reports independently. Re-run the checks; do not take "validator clean"
on trust.

## Phase 6 — Independent verification

The validator checks form. This checks truth, and it is the last cheap moment to catch
a false claim. A drafting agent that has already reasoned its way to an answer will
confirm itself, so verifiers must start clean.

Run one verifier per claim-bearing item across every section that will be scored.
**Block them from `_work/` and from the drafting artefacts entirely** — they get the
question and the proposed answer text, nothing else, and they re-derive from retrieval.

Ask for a verdict per assertion — `supported | contradicted | unverifiable |
overstated` — each with the quoted source that settles it.

Expect findings in **both** directions. In practice this pass found five false claims
in nine rows, and three of them were false *against us*: capability Sprinklr actually
ships, conceded for free. Defensive honesty (playbook §7) has exactly that failure
mode, and only a clean-context check surfaces it.

Present corrections to the user for sign-off rather than applying them silently, and
expect to re-verify at least one — a verifier's own correction can itself be wrong.

## Phase 7 — Merge

```bash
cd "$RFP_DIR"
"$RFP_DIR/_work/.venv/bin/python" "$RFP_SKILL/scripts/merge_answers.py"            # dry run, prints every intended write
"$RFP_DIR/_work/.venv/bin/python" "$RFP_SKILL/scripts/merge_answers.py" --apply    # backup, then write
```

The merge aborts on a cell collision and refuses to write any column listed as
`never_write` in the config (commercial fields, effort estimates, customer-only
columns).

## Phase 8 — Deliverables

```bash
cd "$RFP_DIR"
P="$RFP_DIR/_work/.venv/bin/python"
"$P" "$RFP_SKILL/scripts/build_state.py"             # STATE.md — the audit trail
"$P" "$RFP_SKILL/scripts/build_companion_doc.py"     # narrative doc, if the format needs one
"$P" "$RFP_SKILL/scripts/build_evidence_register.py" # internal gap list with owners
"$P" "$RFP_SKILL/scripts/build_vendor_questions.py"  # ranked, capped, cut line marked
```

## Phase 9 — Report

Lead with what the answers reveal about the bid, not with process metrics. Failing
mandatory criteria, missing evidence, contradictions between internal sources,
claims that need a human before they ship, and promises made in customer text that
nobody has committed to deliver.

Group decisions by owner so the user can forward slices directly — and keep commercial
items in the AE's pile, not the user's.

## Vendor questions

Most tenders permit written questions before submission. Treat this as a scored
opportunity, not admin. The bar: **if the customer's answer would not change what we
write or bid, it is not a question.**

The highest-value category is a requirement we currently fail where clarifying the
protective *intent* might show we meet it — that converts a failure into a pass.
Rank those first.

Keep vendor questions strictly separate from internal open questions. Asking the
customer something that reveals we do not understand our own product is the worst
outcome available here.
