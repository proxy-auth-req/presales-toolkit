#!/usr/bin/env python3
"""Assemble the customer-facing companion document that the source file's evidence
column points at (a security concept, technical annex, or similar).

CUSTOMER-FACING — so no confidence scores, no source links, no POCs, no internal
caveats. Those stay in STATE.md and the answer JSONs.

Renders only `concept_text` and `evidence_customer`. It cannot read
`evidence_internal` at all: that separation is the point, not a convention.

Also leak-checks the rendered result and fails loudly. Reading for leaks by eye does
not work — see references/playbook.md §1 and §2.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import load_answers, load_config, load_inventory, write_out  # noqa: E402
from validate_answers import build_leaks  # noqa: E402


def check_leaks(text, leaks):
    return [(lbl, m.group(0)) for rx, lbl in leaks for m in rx.finditer(text)]


def main():
    cfg = load_config()
    spec = cfg.get("companion_doc") or {}
    if not spec.get("enabled"):
        print("companion_doc disabled in config — nothing to build.")
        return

    source_id = spec.get("source_id")
    inv = {k: v for k, v in load_inventory().items()
           if not source_id or v.get("source") == source_id}
    by_id, _by_batch, _docs = load_answers()

    answers = {k: v for k, v in by_id.items() if k in inv}
    override = spec.get("category_override") or {}

    by_cat = defaultdict(list)
    for gid, item in answers.items():
        cat = override.get(gid) or (inv.get(gid, {}).get("extra") or {}).get("category")
        if not cat:
            cat = inv.get(gid, {}).get("section")
        if not cat:
            print(f"!! {gid}: no category — it will NOT be rendered. Add it to "
                  f"companion_doc.category_override.", file=sys.stderr)
        by_cat[cat].append((gid, item))

    out = [f"# {spec.get('title', 'Companion document')}", ""]
    for line in spec.get("preamble", []):
        out += [line, ""]
    if spec.get("intro"):
        out += [spec["intro"], ""]
    out += ["---", ""]

    written = 0
    for sec in spec.get("sections", []):
        entries = by_cat.get(sec["category"], [])
        if not entries:
            continue
        out += [f"## {sec['num']}. {sec.get('heading', sec['category'])}", ""]

        def subnum(pair):
            s = str(pair[1].get("section", ""))
            try:
                return float(s.split(".", 1)[1])
            except (IndexError, ValueError):
                return 999.0

        for gid, item in sorted(entries, key=subnum):
            sub = item.get("section") or f"{sec['num']}.x"
            title = (inv.get(gid, {}).get("extra") or {}).get("title") \
                or inv.get(gid, {}).get("section_title") or gid
            out += [f"### {sub} {title}", ""]
            # The criterion id and verdict usually already live in the source
            # workbook's own columns. Repeating them here is redundant, so this
            # defaults off -- set show_verdict:true only if the format needs it.
            if spec.get("show_verdict", False):
                out += [f"*{spec.get('verdict_label', 'Kriterium')} {gid} — "
                        f"{item.get('verdict', 'open')}*", ""]
            out += [item.get("concept_text") or "_Not yet drafted._", ""]
            arts = item.get("evidence_customer") or []
            if arts:
                out += [f"**{spec.get('evidence_label', 'Nachweise')}:**", ""]
                for a in arts:
                    # The text before the first colon-SPACE is the customer's own
                    # wording, copied from their evidence column. Render it as a
                    # quotation so it reads as their demand, not our claim.
                    # Split on ": " not ":" -- identifiers like "ISO/IEC 27001:2022"
                    # carry a colon of their own and must not be cut there.
                    if ": " in a[:150]:
                        demand, rest = a.split(": ", 1)
                        out.append(f"- *\u201e{demand.strip()}\u201c* \u2014 {rest.strip()}")
                    else:
                        out.append(f"- {a}")
                out.append("")
            written += 1

    body = "\n".join(out)
    write_out(spec.get("filename", "Companion document.md"), body, "Companion document")
    print(f"  {written}/{len(inv)} items rendered")

    leaks = check_leaks(body, build_leaks(cfg))
    if leaks:
        print(f"\n!! {len(leaks)} potential leaks in the CUSTOMER-FACING document:",
              file=sys.stderr)
        for label, match in leaks:
            print(f"   [{label}] {match!r}", file=sys.stderr)
        print("   -> move to evidence_internal, or justify retention explicitly",
              file=sys.stderr)
        sys.exit(1)
    print("  Leak check: clean.")


if __name__ == "__main__":
    main()
