# `_work/config.json`

Written during discovery. Everything downstream reads it, so the scripts never
hardcode a customer's layout.

```json
{
  "customer": "EVN / Netz Niederösterreich GmbH",
  "engagement": "Auswahl Omnichannel-Kontaktcenterlösung",
  "language": "de",
  "companion_doc": {
    "enabled": true,
    "filename": "Sicherheitskonzept Sprinklr (EVN).md",
    "title": "Sicherheitskonzept Sprinklr",
    "intro": "Dieses Dokument beantwortet die Kriterien des Kriterienkatalogs.",
    "source_id": "sec-06",
    "sections": [
      {"num": 1, "category": "Sec Lösung", "heading": "Lösungsarchitektur"},
      {"num": 3, "category": "Sec Kryptographie", "heading": "Kryptographie"}
    ],
    "category_override": {"G-SEC-146": "Sec Authentifizierung/Autorisierung"}
  },
  "vendor_questions": {"cap": 20, "file_caps": {}},
  "sources": [ ... ]
}
```

`category_override` exists because customers leave category cells blank; without it
those items silently vanish from the companion document. The build script warns on
any uncategorised item — do not ignore that warning.

## Source entries

Two answer kinds. `prose` — a free-text answer column, optionally plus a
classification to tick. `criterion` — a verdict column plus a pointer to a companion
document, no prose in the sheet.

### `prose`

```json
{
  "id": "omni-C",
  "file": "04 Anforderungsübersicht OmniChannel.xlsx",
  "label": "04 OmniChannel — Sektion C",
  "type": "xlsx",
  "sheet": "Anforderungsübersicht",
  "answer_kind": "prose",
  "row_range": [384, 466],
  "section_col": 2,
  "question_col": 3,
  "id_prefix": "OMNI",
  "read_cols": {
    "weight": 4, "existing_answer": 9,
    "existing_owner": 10, "internal_comment": 11, "stand": 12
  },
  "write": {
    "answer": 9,
    "classification": {"ja": 5, "ja_customizing": 6, "ja_roadmap": 7, "nein": 8},
    "classification_mark": "x",
    "constants": {"10": "Sprinklr", "12": "ok"}
  },
  "never_write": []
}
```

`row_range` — inclusive, covering only the in-scope block. `section_col` holds section
numbers on header rows and is blank on question rows: that is how questions are
distinguished from headers. `constants` writes fixed values into the team's own
internal tracking columns — follow their existing convention, never invent a parallel one.

### `criterion`

```json
{
  "id": "sec-06",
  "file": "06 Omnichannel Security Requirements.xlsx",
  "label": "06 Security Requirements",
  "type": "xlsx",
  "sheet": "Kriterienkatalog",
  "answer_kind": "criterion",
  "first_data_row": 3,
  "id_col": 1,
  "read_cols": {
    "title": 2, "category": 4, "criterion_type": 5,
    "description": 6, "evidence_required": 8,
    "client_note": 10, "max_points": 12
  },
  "write": {
    "evidence_ref": 13,
    "evidence_ref_template": "Sicherheitskonzept Sprinklr, Abschnitt {section}",
    "verdict": 14
  },
  "verdict_values": {"pass": "erfüllt", "fail": "nicht erfüllt"},
  "never_write": [15],
  "criterion_type_rank": {
    "Eignungskriterium": 0, "Auswahlkriterium": 1,
    "Zuschlagskriterium": 2, "Information": 3
  }
}
```

`never_write` is enforced by the merge script — put every commercial, effort-estimate
and customer-only column here. `criterion_type_rank` orders mandatory criteria above
scored ones in vendor-question ranking; rank 0 means failing it threatens eligibility.

## Columns

1-indexed integers (A=1). Use `read_cols` for anything an agent should see —
bilingual columns, notes, weights, existing work.

## CSV sources

Set `"type": "csv"`, use `header_row` and name columns by header string instead of
index. Everything else is identical.

## Formats the extractor does not parse

PDF, Word, portal exports: either convert to xlsx/csv first, or have a subagent write
`_work/inventory/<id>.json` directly in the extractor's output shape. Downstream
scripts depend only on that shape.

For a non-spreadsheet deliverable, set `"write": {"mode": "document"}` — answers are
assembled into a document instead of merged into cells, and the merge script skips
the source.

## Inventory shape

```json
{"id": "...", "source": "<source id>", "file": "...", "row": 42,
 "section": "C.1", "section_title": "...", "question": "...",
 "extra": { "...read_cols..." }}
```

`id` must be stable and unique across all sources — batch maps, answer files and the
state file all key on it.

## `_work/inventory/batches.json`

The batch map. The validator uses it to check coverage — every assigned item
answered, nothing answered outside its batch.

```json
{
  "sec-auth": {
    "ids": ["G-SEC-16", "G-SEC-17", "G-SEC-146"],
    "label": "Authentication and authorisation",
    "section_base": 5,
    "subsection_start": 1
  }
}
```

`ids` must match inventory ids exactly. `section_base` and `subsection_start` reserve
a companion-document range for the batch, so concurrent agents cannot collide on
section numbers — assign these up front. Where a batch spans categories that map to
different document sections, tell the agent the per-category mapping in its prompt.

## Optional top-level keys

- `leak_patterns` — `[{"pattern": "regex", "label": "..."}]`, added to the built-in
  set. Never weaken a pattern to silence an honest caveat; record why it is retained.
- `forbidden_terms` — plain strings that must never reach customer text (other
  environments, wrong providers, competitor names, internal codenames).
- `vendor_questions.selected` — ids fixing the final curated set; until set, the
  provisional ranking applies.
- `vendor_questions.already_submitted` — questions already sent, so counts stay honest.

## `cockpit`

Configures the HTML status page. Every label is written in the customer's language; the
script's English defaults exist only so it runs unconfigured. See
`cockpit-design.md` for the reasoning behind the layout.

```json
"cockpit": {
  "filename": "RFP-Cockpit.html",
  "title": "EVN Bid Cockpit",
  "ko_criterion_type": "Eignungskriterium",
  "owner_prefix": "AE:",
  "status": {"label": "Eingereicht", "on": "09.09.2026"},
  "labels": {
    "answered": "Positionen",
    "ko_short": "Eignung nicht erfüllt",
    "evidence_missing": "Nachweise fehlen",
    "open_owner": "Offen beim AE",
    "h_eligibility": "Eignung",
    "h_progress": "Bearbeitungsstand je Katalog",
    "h_evidence": "Nachweislage",
    "h_decisions": "Was noch entschieden wird",
    "ko_lead": "{n} Eignungskriterien nicht erfüllt.",
    "ko_body": "Eignungskriterien sind Ausschlusskriterien — sie werden nicht bepunktet, sondern bestanden oder nicht.",
    "scored_note": "Zusätzlich {n} nicht erfüllte Zuschlagskriterien. Diese kosten Punkte, nicht die Eignung.",
    "legend_green": "tragfähig", "legend_amber": "mit Vorbehalt", "legend_red": "kritisch",
    "ev_total": "{n} geforderte Artefakte",
    "ev_yes": "liegen vor", "ev_nda": "unter NDA",
    "ev_third": "von Dritten", "ev_missing": "fehlen",
    "file_prefix": "Datei",
    "foot": "Generiert aus _work/answers/ · {d} · Interne Übersicht, nicht Bestandteil des Angebots"
  },
  "panels": [
    {"title": "AE / Bid Management", "value": "18",
     "note": "Umfangs- und Angebotsentscheidungen. Nicht vom Solution Architect zu entscheiden."}
  ]
}
```

`ko_criterion_type` names the **mandatory** criterion type exactly as the customer
writes it. Failing one threatens eligibility; failing a scored criterion only costs
points, and the cockpit keeps the two apart. Leave it unset where the tender draws no
such distinction — everything then lands in a single list.

`owner_prefix` matches the prefix drafting agents put on routed open questions
(`AE:` by default), so the cockpit can count what is parked with someone else.

`panels` are free text — the three or four things genuinely open at the end of this
bid. Do not force a fixed set.

Give every source a **`short`** (`"06"`, `"04"`) alongside its `label`: the cockpit tags
each failing row with it, so a reader sees which catalogue an item came from without
consulting a legend.

`{n}` and `{d}` are the only placeholders — item count and today's date.
