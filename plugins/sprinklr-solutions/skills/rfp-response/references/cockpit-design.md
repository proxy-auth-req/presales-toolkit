# The cockpit — design formula

`scripts/build_cockpit.py` emits a single self-contained HTML status page. It opens in
a browser and publishes unchanged as an Artifact. This file explains the decisions
behind it, so the look survives being regenerated for a different customer.

**Language.** This skill is written in English. The page is not. Every string it renders
comes from `config.cockpit.labels`, and those are written in the customer's language —
or whatever language the user asked for. Defaults in the script are English so it runs
out of the box; override all of them per engagement. Never leave a German page with
English column headings, or the reverse.

## What the page is for

One question, answered in about five seconds: **where does this bid stand, and what
could sink it.** It is scanned and operated, not read. That makes it information design,
not typography.

It is a *status view*, never the audit trail. Counts and the named items that decide the
bid — never source URLs, POCs, confidence scores or internal caveats. Those stay in
`STATE.md`, which the cockpit does not replace.

## The organising idea — do not flatten criterion types

Most public tenders separate **mandatory** criteria (pass/fail, they decide eligibility)
from **scored** criteria (they cost points). German-language tenders name these
*Eignungskriterium* and *Zuschlagskriterium*; other jurisdictions use their own terms.

A generic dashboard reports "13 failing". That is misleading and it is the single most
important thing this page gets right: six failing mandatory criteria is an eligibility
question, seven failing scored ones is a points question. Two different conversations.

So mandatory failures get their own band with a coloured rail and every item named;
scored failures sit underneath in plain rows with a one-line framing. Set
`cockpit.ko_criterion_type` to the mandatory type's name as the customer writes it.
Leave it unset where the tender draws no such line, and everything lands in one list.

## Hierarchy

Four figures, and only one is a completion metric — once a bid is drafted, completion is
the least interesting number on the page. The other three are risk: mandatory failures,
missing evidence, decisions parked with someone else.

Then bands in decreasing urgency: failing criteria named individually → progress per
catalogue → evidence position → who still owes a decision.

## Tokens

**Colour.** Cool paper `#F7F8FA` / ink `#14171C`, with neutrals biased slightly toward
the accent rather than pure grey. Accent `#1250DE` (Sprinklr) used *sparingly* — owner
rails and figures only. Semantic colours are a separate set and never double as the
accent: `#2F7A4F` sound, `#B0801F` caveats, `#B4342B` critical.

**Type.** IBM Plex Sans for UI, IBM Plex Mono for codes and every figure. The mono is
doing real work: `G-SEC-113` is a code and should read as one, and `tabular-nums` keeps
columns of digits aligned. Load both from Google Fonts, the one font host the Artifact
CSP admits.

**Layout.** One column, max 1080px. Air over borders — hierarchy comes from type weight
and spacing, not from wrapping every block in a card. Spend border, fill and radius on
the one band that needs lifting.

**Themes.** Full three-state setup: bare `:root` carries the complete light palette,
`@media (prefers-color-scheme:dark)` guarded as `:root:not([data-theme="light"])`
redefines the tokens, and `:root[data-theme="dark"]` redefines them again so an explicit
toggle wins both ways. `body` sets an explicit background from a token — the artifact
composites over a ground the viewer paints, and a transparent body borrows the host's.

## Config

```json
"cockpit": {
  "filename": "RFP-Cockpit.html",
  "title": "EVN Bid Cockpit",
  "ko_criterion_type": "Eignungskriterium",
  "owner_prefix": "AE:",
  "status": {"label": "Eingereicht", "on": "09.09.2026"},
  "labels": { "answered": "Positionen", "ko_short": "Eignung nicht erfüllt", "…": "…" },
  "panels": [
    {"title": "AE / Bid Management", "value": "18",
     "note": "Umfangs- und Angebotsentscheidungen."}
  ]
}
```

`panels` are free-text: whatever three or four things are genuinely open at the end of
*this* bid. Do not force a fixed set.

Each source entry should carry a `short` (e.g. `"06"`, `"04"`) — the cockpit tags rows
with it so a reader can see which catalogue an item came from without a legend.

## What was deliberately left out

**No trend or time series.** A bid is a push to a deadline, not a process with a
baseline. "Moved since last week" is noise on a page whose job is "what could sink this".
Add it only if the user asks.

**No completion percentage as a headline.** It reads as reassurance and crowds out risk.

**No per-item confidence.** That is audit data. It belongs in `STATE.md`.
