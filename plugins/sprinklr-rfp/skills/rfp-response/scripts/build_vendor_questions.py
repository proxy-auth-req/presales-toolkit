#!/usr/bin/env python3
"""Collect vendor-question candidates, rank them, cap them, mark the cut line.

Emits two files:
  Vendor questions (candidates, internal).md  — every candidate, ranked, with the
      internal reasoning and the cut line marked. The deal owner curates from this.
  Vendor questions.md                         — the selected questions only,
      customer-facing, no internal reasoning.

Ranking, in order:
  1. can_turn_red   — a question that can rescue a failing requirement beats one
                      that merely improves a score.
  2. value          — the drafting agent's own impact judgement.
  3. current RAG    — a documented failure outranks a hypothetical improvement.
  4. criterion type — mandatory above scored. LAST, deliberately: only some sources
                      carry a type, so ranking on it earlier buries every question
                      from files that have none. See playbook §11.

Nothing is sent anywhere; this only writes local markdown.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import (RAG_ICON, RAG_ORDER, VALID_VALUE, load_answers,  # noqa: E402
                     load_config, load_inventory, sources, write_out)


def collect(cfg, inv, srcs):
    out = []
    by_id, _by_batch, _docs = load_answers()
    for iid, item in by_id.items():
        vq = item.get("vendor_question")
        if not vq:
            continue
        src = srcs.get(item.get("_source")) or {}
        ctype = (inv.get(iid, {}).get("extra") or {}).get("criterion_type")
        rank_map = src.get("criterion_type_rank") or {}
        out.append({
            "id": iid, "row": item.get("row"), "source": item.get("_source"),
            "label": src.get("label", item.get("_source") or "?"),
            "batch": item.get("_batch"), "rag": item.get("rag"),
            "criterion_type": ctype,
            "type_rank": rank_map.get(ctype, 3),
            "ref": (f"Nr. {item.get('row')}" if src.get("answer_kind") != "criterion"
                    else f"{src.get('criterion_word', 'Kriterium')} {iid}"),
            **vq,
        })
    return out


def rank(cands):
    return sorted(cands, key=lambda c: (
        not c.get("can_turn_red", False),
        VALID_VALUE.get(c.get("value", "low"), 3),
        RAG_ORDER.get(c.get("rag"), 3),
        c.get("type_rank", 3),
        str(c["id"]),
    ))


def shortlist(ranked, cfg):
    spec = cfg.get("vendor_questions") or {}
    selected = spec.get("selected") or []
    if selected:
        return [c for c in ranked if c["id"] in selected]
    cap = spec.get("cap", 20)
    file_caps = spec.get("file_caps") or {}
    picked, per = [], {}
    for c in ranked:
        if len(picked) >= cap:
            break
        s = c["source"]
        if per.get(s, 0) >= file_caps.get(s, cap):
            continue
        per[s] = per.get(s, 0) + 1
        picked.append(c)
    return picked


def main():
    cfg = load_config()
    srcs = sources(cfg)
    inv = load_inventory()
    spec = cfg.get("vendor_questions") or {}
    cap = spec.get("cap", 20)

    cands = collect(cfg, inv, srcs)
    ranked = rank(cands)
    picked = shortlist(ranked, cfg)
    picked_ids = {c["id"] for c in picked}

    out = [f"# Vendor questions — candidates (internal), {cfg.get('customer','')}", "",
           "**Not customer-facing.** Generated from `_work/answers/*.json`. Fix the "
           "final selection via `vendor_questions.selected` in `_work/config.json`; "
           "until then the provisional ranking applies.", "",
           f"**Budget:** {cap} · **candidates:** {len(cands)} · "
           f"**shortlisted:** {len(picked)}", "",
           "Ranked: questions that can turn a failing requirement first, then stated "
           "impact, then how bad the item is today, then criterion type.", ""]

    already = spec.get("already_submitted") or []
    if already:
        out += ["## Already submitted", ""]
        out += [f"- {a}" for a in already]
        out.append("")

    out += ["## Candidates", "",
            "| # | Pick | Item | Source | RAG | Value | Turns red? | Question |",
            "|---:|---|---|---|---|---|---|---|"]
    cut_after = len(picked)
    for n, c in enumerate(ranked, 1):
        mark = "**✓**" if c["id"] in picked_ids else "—"
        out.append(f"| {n} | {mark} | `{c['id']}` | {c['label']} "
                   f"| {RAG_ICON.get(c.get('rag'), '⚪')} | {c.get('value', '—')} "
                   f"| {'yes' if c.get('can_turn_red') else '—'} "
                   f"| {' '.join(str(c.get('question', '')).split())[:110]} |")
        if n == cut_after and n < len(ranked):
            out.append("| | | | | | | | **── cut line ──** |")
    out.append("")

    out += ["## Reasoning", ""]
    for c in ranked:
        out += [f"### `{c['id']}` — "
                f"{'shortlisted' if c['id'] in picked_ids else 'not shortlisted'}", "",
                f"**Question:** {c.get('question', '—')}", "",
                f"**Unclear:** {c.get('rationale', '—')}", "",
                f"**Impact:** {c.get('impact', '—')}", ""]

    write_out("Vendor questions (candidates, internal).md", "\n".join(out),
              "Candidate register")

    cust = [f"# {spec.get('customer_title', 'Vendor questions')}", ""]
    if cfg.get("engagement"):
        cust += [f"**{cfg['engagement']}** — {cfg.get('customer', '')}", ""]
    if spec.get("customer_intro"):
        cust += [spec["customer_intro"], ""]
    by_source = {}
    for c in picked:
        by_source.setdefault(c["source"], []).append(c)
    n = 0
    for sid in [s["id"] for s in cfg.get("sources", [])]:
        entries = by_source.get(sid)
        if not entries:
            continue
        cust += [f"## {srcs[sid].get('label', sid)}", ""]
        for c in sorted(entries, key=lambda x: str(x["id"])):
            n += 1
            cust += [f"**{spec.get('question_word', 'Frage')} {n} — {c['ref']}**", "",
                     c.get("question", ""), ""]
    write_out("Vendor questions.md", "\n".join(cust), "Customer-facing questions")

    print(f"  {len(cands)} candidates, {len(picked)}/{cap} shortlisted")
    for sid in {c["source"] for c in picked}:
        got = sum(1 for c in picked if c["source"] == sid)
        print(f"    {srcs.get(sid, {}).get('label', sid):32} {got}")


if __name__ == "__main__":
    main()
