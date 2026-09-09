#!/usr/bin/env python3
"""Build the internal evidence register: every artefact the customer demands, and
whether we can actually deliver it.

INTERNAL ONLY — the counterpart to the customer-facing companion document. The
"we would have to build that" content lives here so it reaches the deal owner as an
action item instead of reaching the customer as a confession.

The `missing` section is the one to work: check whether something exists that
retrieval simply did not surface.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import load_answers, load_config, load_inventory, short, write_out  # noqa: E402

STATUS = {
    "missing": ("❌ missing", "Does not exist — check whether something does."),
    "third_party": ("🏢 third party", "Must be obtained from a third party."),
    "nda": ("🔒 under NDA", "Exists; release only under a confidentiality agreement."),
    "yes": ("✅ available", "Exists and can accompany the offer."),
}
ORDER = ["missing", "third_party", "nda", "yes"]


def main():
    cfg = load_config()
    inv = load_inventory()
    by_id, _by_batch, _docs = load_answers()

    rows = []
    for gid, item in by_id.items():
        for n in item.get("evidence_internal") or []:
            rows.append((gid, item, n))

    by_status = defaultdict(list)
    for gid, item, n in rows:
        by_status[n.get("available", "missing")].append((gid, item, n))

    out = [f"# Evidence register — {cfg.get('customer', '')} (internal)", "",
           "**Not customer-facing.** Counterpart to the companion document: which of "
           "the demanded evidence artefacts we can actually deliver.", "",
           "Generated from `_work/answers/*.json` — do not edit by hand.", ""]
    counts = " · ".join(f"{STATUS[s][0]}: {len(by_status.get(s, []))}"
                        for s in ORDER if by_status.get(s))
    out += [f"**{len(rows)} artefacts** — {counts}", ""]

    for status in ORDER:
        entries = by_status.get(status)
        if not entries:
            continue
        label, blurb = STATUS[status]
        out += [f"## {label}", "", f"_{blurb}_", "",
                "| Item | Demanded artefact | Substitute | Owner | Note |",
                "|---|---|---|---|---|"]
        for gid, _item, n in sorted(entries, key=lambda p: str(p[0])):
            title = short((inv.get(gid, {}).get("extra") or {}).get("title")
                          or inv.get(gid, {}).get("section_title") or "", 45)
            out.append(f"| `{gid}`<br>{title} | {short(n.get('artefact'), 60)} "
                       f"| {short(n.get('substitute'), 45) or '—'} "
                       f"| {n.get('owner') or '—'} | {short(n.get('note'), 70) or '—'} |")
        out.append("")

    write_out(f"Evidence register (internal).md", "\n".join(out), "Evidence register")
    print(f"  {len(rows)} artefacts · {len(by_status.get('missing', []))} missing")


if __name__ == "__main__":
    main()
