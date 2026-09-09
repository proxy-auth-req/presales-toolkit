#!/usr/bin/env python3
"""Check every answer against the contract before anything reaches a customer file.

Catches the failure modes that actually occurred: leaked internal text in
customer-facing prose, retired fields, missing or duplicated coverage, invalid enums,
ungrounded claims, companion-section collisions, and deployment tags contradicted by
their own caveats.

Exit 1 on any ERROR. HINWEIS/warn items are judgement calls for review.
"""
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import (VALID_AVAIL, VALID_FULFIL, VALID_RAG, VALID_VALUE,  # noqa: E402
                     load_answers, load_batches, load_config, load_inventory, sources)

# Generic leak patterns. Extend per engagement via config "leak_patterns":
# [{"pattern": "...", "label": "..."}] — never weaken one to silence an honest caveat.
DEFAULT_LEAKS = [
    (r"\b[Pp]rod\s?\d+\b", "internal environment id"),
    (r"Confluence|SharePoint|Atlassian|Jira|Notion",
     "internal system name"),
    (r"intern[a-zäöüß]*\s+(Bericht|Richtlinie|Dokument|Unterlage|Seite|Wiki)",
     "reference to an internal document"),
    (r"internal\s+(report|guideline|document|page|wiki|policy)",
     "reference to an internal document"),
    (r"wird nicht extern|nicht extern geteilt|nur in redigierter Form|"
     r"not shared externally|only in redacted form",
     "commentary on what we withhold"),
    (r"liegt derzeit (jedoch )?nicht als konsolidiert|"
     r"müsste für dieses Angebot|would have to be (created|produced) for this",
     "internal to-do leaking into customer text"),
    (r"\bNICHT\b|\bKEINE\b", "shouty internal register"),
]

errors, warns = [], []


def err(batch, item, msg):
    errors.append(f"[{batch}] {item}: {msg}")


def warn(batch, item, msg):
    warns.append(f"[{batch}] {item}: {msg}")


def build_leaks(cfg):
    pats = [(p, lbl) for p, lbl in DEFAULT_LEAKS]
    for extra in cfg.get("leak_patterns", []):
        pats.append((extra["pattern"], extra.get("label", "configured pattern")))
    for name in cfg.get("forbidden_terms", []):
        pats.append((r"\b" + re.escape(name) + r"\b", "forbidden term"))
    return [(re.compile(p), lbl) for p, lbl in pats]


def customer_text(item, kind):
    if kind == "criterion":
        parts = [item.get("concept_text") or ""]
        parts += item.get("evidence_customer") or []
    else:
        parts = [item.get("answer") or ""]
    vq = item.get("vendor_question") or {}
    parts.append(vq.get("question") or "")
    return "\n".join(parts)


def check_item(batch, it, kind, leaks, inv):
    iid = it.get("id", "<no id>")

    if it.get("rag") not in VALID_RAG:
        err(batch, iid, f"invalid rag {it.get('rag')!r}")
    c = it.get("confidence")
    if not isinstance(c, (int, float)) or not 0 <= c <= 1:
        err(batch, iid, f"confidence out of range: {c!r}")
    if not it.get("sources"):
        err(batch, iid, "no sources — every answer must be grounded")
    for s in it.get("sources") or []:
        if not s.get("url"):
            warn(batch, iid, f"source without url: {s.get('title')!r}")
    if not it.get("poc"):
        warn(batch, iid, "no poc")
    for retired in ("evidence_artifacts", "nachweise_kunde", "nachweise_intern"):
        if retired in it:
            err(batch, iid, f"retired field {retired!r} present")

    if isinstance(c, (int, float)):
        if it.get("rag") == "green" and c < 0.7:
            warn(batch, iid, f"green but confidence {c}")
        if it.get("rag") == "red" and c > 0.8:
            warn(batch, iid, f"red but confidence {c}")
    if it.get("host_validation") == "CONFLICT" and it.get("rag") != "red":
        warn(batch, iid, "CONFLICT should normally force red")

    # A strong deployment tag whose own caveat hedges about the target environment is
    # overstating the evidence. Agents cannot see each other, so this only shows here.
    tag = it.get("host_validation") or ""
    if tag and tag not in ("ASSUMED-GENERAL", "ALL-VARIANTS", "CONFLICT"):
        cav = (it.get("caveats") or "") + (it.get("defensive_note") or "")
        hedges = ("neu errichtet", "nicht automatisch", "noch nicht", "im Aufbau",
                  "nicht belegt", "Zielumgebung", "newly built", "not yet",
                  "not evidenced", "being built")
        hit = [h for h in hedges if h in cav]
        if hit:
            warn(batch, iid, f"tag {tag} but caveat hedges on the target environment "
                             f"({', '.join(hit)}) — ASSUMED-GENERAL may be honest")

    if kind == "criterion":
        if it.get("verdict") not in ("pass", "fail"):
            err(batch, iid, f"invalid verdict {it.get('verdict')!r}")
        if not it.get("section"):
            err(batch, iid, "no companion-document section")
        if not it.get("concept_text"):
            err(batch, iid, "no concept_text")
        if not it.get("evidence_customer"):
            warn(batch, iid, "no evidence_customer")
        for n in it.get("evidence_internal") or []:
            if n.get("available") not in VALID_AVAIL:
                err(batch, iid, f"invalid evidence availability {n.get('available')!r}")
    else:
        if it.get("std_fulfillment") not in VALID_FULFIL:
            err(batch, iid, f"invalid std_fulfillment {it.get('std_fulfillment')!r}")
        if not it.get("answer"):
            err(batch, iid, "no answer text")

    vq = it.get("vendor_question")
    if vq:
        if not vq.get("question"):
            err(batch, iid, "vendor_question without question text")
        if vq.get("value") not in VALID_VALUE:
            err(batch, iid, f"vendor_question invalid value {vq.get('value')!r}")
        for f in ("rationale", "impact"):
            if not vq.get(f):
                warn(batch, iid, f"vendor_question missing {f}")

    for rx, label in leaks:
        for m in rx.finditer(customer_text(it, kind)):
            err(batch, iid, f"LEAK in customer text [{label}] {m.group(0)!r}")

    if iid in inv and it.get("row") is not None:
        if it["row"] != inv[iid].get("row"):
            err(batch, iid, f"row {it['row']} != inventory row {inv[iid].get('row')}")
    elif iid not in inv:
        err(batch, iid, "id not present in any inventory")


def main():
    cfg = load_config()
    leaks = build_leaks(cfg)
    srcs = sources(cfg)
    inv = load_inventory()
    by_id, by_batch, docs = load_answers()

    total = vq_count = 0
    seen = {}
    for doc in docs:
        batch = doc["_batch"]
        src = srcs.get(doc.get("source")) or {}
        kind = src.get("answer_kind", "prose")
        if not doc.get("items"):
            err(batch, "-", "no items")
        for it in doc.get("items", []):
            total += 1
            if not it.get("id"):
                err(batch, "<no id>", "item without id")
                continue
            seen.setdefault(it["id"], []).append(batch)
            check_item(batch, it, kind, leaks, inv)
            if it.get("vendor_question"):
                vq_count += 1

    for iid, bs in seen.items():
        if len(bs) > 1:
            errors.append(f"[-] {iid}: answered by multiple batches {bs}")

    for bid, spec in load_batches().items():
        if bid not in by_batch:
            continue
        got = {i["id"] for i in by_batch[bid]}
        expected = set(spec.get("ids") or spec.get("guids") or [])
        for missing in sorted(expected - got):
            err(bid, missing, "assigned to this batch but not answered")
        for extra in sorted(got - expected):
            err(bid, extra, "answered but not assigned to this batch")

    secs = Counter()
    for it in by_id.values():
        if it.get("section") and (srcs.get(it.get("_source")) or {}).get(
                "answer_kind") == "criterion":
            secs[it["section"]] += 1
    for sec, n in sorted(secs.items()):
        if n > 1:
            errors.append(f"[-] companion section {sec} used {n} times")

    print(f"{total} answers checked · {vq_count} vendor-question candidates · "
          f"{len(errors)} errors · {len(warns)} warnings\n")
    if errors:
        print("ERRORS")
        for e in errors:
            print("  ✗", e)
        print()
    if warns:
        print("WARNINGS")
        for w in warns:
            print("  ·", w)
    if not errors and not warns:
        print("All clean.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
