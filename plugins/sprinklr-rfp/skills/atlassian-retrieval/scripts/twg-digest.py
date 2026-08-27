#!/usr/bin/env python3
"""Digest a twg JSON payload into a compact, readable summary.

`twg` writes full JSON to a file and prints a YAML envelope naming it. This script
reads either end of that and prints ranked hits plus the partial-result state that
must not be swallowed.

Usage:
    twg rovo search "topic" --output json --output-summary auto | python3 twg-digest.py -
    python3 twg-digest.py /path/to/stdout.json
    python3 twg-digest.py /path/to/stdout.json --limit 30 --snippets

Reading the envelope from stdin ("-") resolves output_files.stdout automatically,
preferring the full payload over the compact projection.
"""

import argparse
import json
import re
import sys

MAX_SNIPPET = 240


def resolve_path_from_envelope(text):
    """Pull the stdout.json path out of twg's YAML envelope."""
    m = re.search(r'^\s*stdout:\s*"([^"]+)"', text, re.M)
    if m:
        return m.group(1)
    m = re.search(r'^\s*compact:\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else None


def load(source):
    if source == "-":
        raw = sys.stdin.read()
        stripped = raw.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            return json.loads(raw)          # payload piped directly
        path = resolve_path_from_envelope(raw)
        if not path:
            sys.exit("No output_files path found in the envelope on stdin. "
                     "Re-run the twg command with --output json.")
        source = path
    with open(source) as fh:
        return json.load(fh)


def find_items(doc):
    """twg puts collections in different places depending on command shape."""
    if isinstance(doc, list):
        return doc
    if not isinstance(doc, dict):
        return []
    for candidate in (doc.get("items"),
                      (doc.get("data") or {}).get("items") if isinstance(doc.get("data"), dict) else None,
                      doc.get("data")):
        if isinstance(candidate, list):
            return candidate
    return []


def find_meta(doc, key):
    """Look for a metadata key at the top level, under data, or under meta."""
    if not isinstance(doc, dict):
        return None
    for container in (doc, doc.get("data"), doc.get("meta")):
        if isinstance(container, dict) and container.get(key) is not None:
            return container[key]
    return None


def one_line(value, limit=MAX_SNIPPET):
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def describe_entity(doc):
    """A non-collection response — a hydrated page or work item."""
    data = doc.get("data") if isinstance(doc, dict) else None
    if not isinstance(data, dict):
        return False
    fields = [(k, data[k]) for k in ("id", "key", "type", "title", "summary", "status", "detail")
              if k in data and not isinstance(data[k], (dict, list))]
    if not fields and "summary" not in data and "outline" not in data:
        return False
    print("Entity")
    for key, value in fields:
        print(f"  {key}: {one_line(value, 120)}")
    summary = data.get("summary")
    if isinstance(summary, dict):
        if summary.get("wordCount") is not None:
            print(f"  words: {summary['wordCount']}  sections: {summary.get('sectionCount')}")
        if summary.get("excerpt"):
            print(f"  excerpt: {one_line(summary['excerpt'])}")
    outline = data.get("outline")
    if isinstance(outline, list) and outline:
        print(f"\nOutline ({len(outline)} headings)")
        for node in outline:
            if isinstance(node, dict):
                indent = "  " * int(node.get("level", 1))
                print(f"{indent}- {one_line(node.get('text', ''), 90)}")
    body = data.get("body")
    if isinstance(body, dict) and body.get("value"):
        print(f"\nBody ({body.get('format')}, {len(str(body['value']))} chars) — "
              "re-run with --body-only --output-file to read it in full")
    return True


def main():
    ap = argparse.ArgumentParser(description="Digest a twg JSON payload.")
    ap.add_argument("source", help='Path to stdout.json, or "-" to read the envelope from stdin')
    ap.add_argument("--limit", type=int, default=20, help="Max items to print (default 20)")
    ap.add_argument("--snippets", action="store_true", help="Include result snippets")
    args = ap.parse_args()

    doc = load(args.source)
    items = find_items(doc)

    if not items and describe_entity(doc):
        print_state(doc)
        return

    if not items:
        print("No items in payload.")
        print("An empty result can mean the connector is unavailable rather than 'no matches' — "
              "check `twg rovo list-apps -o json` before concluding nothing exists.")
        print_state(doc)
        return

    print(f"{len(items)} item(s), showing up to {args.limit}\n")
    for i, item in enumerate(items[: args.limit], 1):
        if not isinstance(item, dict):
            print(f"{i:3}. {one_line(item, 120)}")
            continue
        title = item.get("title") or item.get("name") or item.get("summary") or item.get("key") or "(untitled)"
        kind = item.get("type") or item.get("app") or ""
        print(f"{i:3}. [{kind}] {one_line(title, 100)}" if kind else f"{i:3}. {one_line(title, 100)}")
        if item.get("url"):
            print(f"     {item['url']}")
        status = item.get("status")
        if isinstance(status, dict):
            status = status.get("name")
        if status:
            print(f"     status: {one_line(status, 60)}")
        if args.snippets and item.get("snippet"):
            print(f"     {one_line(item['snippet'])}")

    print_state(doc)


def print_state(doc):
    """Partial-result state is first-class — always print it."""
    info = find_meta(doc, "resultInfo")
    if isinstance(info, dict):
        bits = [f"{k}={info[k]}" for k in ("mode", "limit", "returned", "truncated", "partial")
                if k in info]
        if bits:
            print("\nresultInfo: " + "  ".join(bits))
        if info.get("partial") or info.get("truncated"):
            print("  ⚠ Incomplete: you saw a slice. Absence of evidence is not evidence of absence.")

    counts = find_meta(doc, "sourceCounts")
    if isinstance(counts, list) and counts:
        print("\nsourceCounts")
        for entry in counts:
            if isinstance(entry, dict):
                print(f"  {entry.get('source'):<14} returned={entry.get('returned')} "
                      f"estimatedMatches={entry.get('estimatedMatches')}")

    for key in ("warnings", "failures"):
        entries = find_meta(doc, key)
        if isinstance(entries, list) and entries:
            print(f"\n{key} ({len(entries)}) — report these, do not swallow them")
            for entry in entries:
                if isinstance(entry, dict):
                    label = entry.get("source") or entry.get("code") or ""
                    print(f"  - {label}: {one_line(entry.get('message', entry), 200)}")
                else:
                    print(f"  - {one_line(entry, 200)}")

    completeness = find_meta(doc, "completeness")
    if isinstance(completeness, dict):
        print(f"\ncompleteness: {completeness.get('status')}")
        if completeness.get("caveat"):
            print(f"  {one_line(completeness['caveat'], 300)}")


if __name__ == "__main__":
    main()
