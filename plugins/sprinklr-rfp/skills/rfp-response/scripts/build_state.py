#!/usr/bin/env python3
"""Regenerate STATE.md — the audit trail.

Always generated, never hand-edited: that is what lets many concurrent agents work
without fighting over one file. Each owns one answers/*.json; only this reads them all.

Carries everything that must NOT go in a customer file: confidence, RAG, deployment
tag, internal source links and the product/engineering POC.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import (RAG_ICON, load_answers, load_batches, load_config,  # noqa: E402
                     load_inventory, short, sources, write_out)


def ref_cell(item):
    srcs = item.get("sources") or []
    poc = item.get("poc") or "—"
    if not srcs:
        return "—", poc
    links = []
    for s in srcs[:2]:
        title = short(s.get("title", "source"), 40)
        url = s.get("url")
        links.append(f"[{title}]({url})" if url else title)
    if len(srcs) > 2:
        links.append(f"+{len(srcs) - 2}")
    return "<br>".join(links), poc


def main():
    cfg = load_config()
    srcs = sources(cfg)
    inv = load_inventory()
    by_id, by_batch, _docs = load_answers()

    out = [f"# {cfg.get('customer', 'RFP')} — Bearbeitungsstand / status", ""]
    out.append("Generated from `_work/answers/*.json` by `build_state.py`. "
               "**Do not edit by hand** — it is overwritten.")
    out.append("")
    dep = cfg.get("deployment_context")
    if dep:
        out.append(f"Deployment assumption: **{dep}**")
        out.append("")

    by_source = {}
    for item in inv.values():
        by_source.setdefault(item["source"], []).append(item)

    total_scope = len(inv)
    done = sum(1 for i in by_id.values() if i.get("status") == "done")
    rag_all = Counter(i.get("rag") for i in by_id.values())

    out += ["## Overall", "",
            "| Source | Scope | Answered | 🟢 | 🟡 | 🔴 |",
            "|---|---:|---:|---:|---:|---:|"]
    for sid, items in by_source.items():
        label = (srcs.get(sid) or {}).get("label", sid)
        mine = [by_id[i["id"]] for i in items if i["id"] in by_id]
        rag = Counter(i.get("rag") for i in mine)
        d = sum(1 for i in mine if i.get("status") == "done")
        out.append(f"| {label} | {len(items)} | {d} | {rag['green']} | "
                   f"{rag['amber']} | {rag['red']} |")
    out.append(f"| **Total** | **{total_scope}** | **{done}** | "
               f"**{rag_all['green']}** | **{rag_all['amber']}** | **{rag_all['red']}** |")
    out.append("")

    batches = load_batches()
    out += ["## Batches", "",
            "| Batch | Scope | Items | 🟢 | 🟡 | 🔴 | Avg conf | Open Qs |",
            "|---|---|---:|---:|---:|---:|---:|---:|"]
    for batch in sorted(by_batch):
        items = by_batch[batch]
        rag = Counter(i.get("rag") for i in items)
        confs = [i["confidence"] for i in items
                 if isinstance(i.get("confidence"), (int, float))]
        avg = f"{sum(confs) / len(confs):.2f}" if confs else "—"
        openq = sum(1 for i in items if i.get("open_question"))
        label = (batches.get(batch) or {}).get("label", "")
        out.append(f"| `{batch}` | {short(label, 34)} | {len(items)} | {rag['green']} | "
                   f"{rag['amber']} | {rag['red']} | {avg} | {openq} |")
    out.append("")

    for sid, items in by_source.items():
        label = (srcs.get(sid) or {}).get("label", sid)
        out += [f"## {label}", "",
                "| ID | Section | Question / criterion | Batch | Status | Conf | "
                "RAG | Deployment | Internal reference | POC |",
                "|---|---|---|---|---|---:|---|---|---|---|"]
        for q in items:
            item = by_id.get(q["id"])
            title = q.get("question") or q.get("section_title") or ""
            section = q.get("section") or ""
            if not item:
                out.append(f"| `{q['id']}` | {section} | {short(title)} | — | open | "
                           f"— | ⚪ | — | — | — |")
                continue
            ref, poc = ref_cell(item)
            conf = (f"{item['confidence']:.2f}"
                    if isinstance(item.get("confidence"), (int, float)) else "—")
            flag = " ⚠️" if item.get("open_question") else ""
            out.append(
                f"| `{q['id']}` | {section} | {short(title)} | `{item['_batch']}` | "
                f"{item.get('status', '?')}{flag} | {conf} | "
                f"{RAG_ICON.get(item.get('rag'), '⚪')} | "
                f"{item.get('host_validation') or '—'} | {ref} | {poc} |")
        out.append("")

    openq = [i for i in by_id.values() if i.get("open_question")]
    out += ["## Open questions for humans", ""]
    if not openq:
        out.append("_None._")
    for i in sorted(openq, key=lambda x: str(x["id"])):
        out.append(f"- **`{i['id']}`** ({i['_batch']}, "
                   f"{RAG_ICON.get(i.get('rag'), '⚪')}) — {i['open_question']}  \n"
                   f"  POC: {i.get('poc') or '—'}")
    out.append("")

    risky = [i for i in by_id.values() if i.get("host_validation") == "CONFLICT"]
    out += ["## Deployment / source conflicts", ""]
    out.append("_None._" if not risky else "")
    for i in sorted(risky, key=lambda x: str(x["id"])):
        out.append(f"- **`{i['id']}`** — {i.get('caveats') or 'see answer file'}")
    out.append("")

    write_out("STATE.md", "\n".join(out), "STATE.md")
    print(f"  {done}/{total_scope} answered · {len(by_batch)} batches · "
          f"{len(openq)} open questions")


if __name__ == "__main__":
    main()
