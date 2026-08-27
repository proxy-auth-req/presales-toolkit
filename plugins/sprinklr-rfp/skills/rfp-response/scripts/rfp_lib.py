"""Shared helpers. Every script locates _work/ relative to the customer directory.

Set RFP_DIR to the customer directory, or run the scripts from inside it.
"""
import json
import os
import sys

BASE = os.environ.get("RFP_DIR") or os.getcwd()
WORK = os.path.join(BASE, "_work")

RAG_ICON = {"green": "🟢", "amber": "🟡", "red": "🔴"}
RAG_ORDER = {"red": 0, "amber": 1, "green": 2}
VALID_RAG = set(RAG_ICON)
VALID_AVAIL = {"yes", "nda", "third_party", "missing"}
VALID_FULFIL = {"ja", "ja_customizing", "ja_roadmap", "nein", "n/a"}
VALID_VALUE = {"high": 0, "medium": 1, "low": 2}


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def load_config():
    path = os.path.join(WORK, "config.json")
    if not os.path.exists(path):
        die(f"no config at {path} — write it during discovery "
            f"(see references/config-schema.md)")
    with open(path) as fh:
        return json.load(fh)


def sources(cfg):
    return {s["id"]: s for s in cfg.get("sources", [])}


def load_inventory(source_id=None):
    """All inventory items, or one source's. Returns {id: item}."""
    out = {}
    inv_dir = os.path.join(WORK, "inventory")
    if not os.path.isdir(inv_dir):
        die(f"no inventory at {inv_dir} — run extract_inventory.py first")
    for name in sorted(os.listdir(inv_dir)):
        if not name.endswith(".json") or name == "batches.json":
            continue
        sid = name[:-5]
        if source_id and sid != source_id:
            continue
        with open(os.path.join(inv_dir, name)) as fh:
            for item in json.load(fh):
                out[item["id"]] = item
    return out


def load_answers():
    """All answer records. Returns (by_id, by_batch, docs)."""
    by_id, by_batch, docs = {}, {}, []
    ans_dir = os.path.join(WORK, "answers")
    if not os.path.isdir(ans_dir):
        return by_id, by_batch, docs
    for name in sorted(os.listdir(ans_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(ans_dir, name)
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"  !! {name}: invalid JSON ({exc}) — skipped", file=sys.stderr)
            continue
        batch = doc.get("batch_id") or name[:-5]
        doc["_batch"] = batch
        docs.append(doc)
        for item in doc.get("items", []):
            item["_batch"] = batch
            item["_source"] = doc.get("source")
            item["_file"] = doc.get("file")
            by_id[item["id"]] = item
            by_batch.setdefault(batch, []).append(item)
    return by_id, by_batch, docs


def load_batches():
    path = os.path.join(WORK, "inventory", "batches.json")
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def short(text, n=70):
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text[: n - 1] + "…" if len(text) > n else text


def write_out(relpath, body, label):
    path = os.path.join(BASE, relpath)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        fh.write(body)
    print(f"{label}: {relpath}")
    return path
