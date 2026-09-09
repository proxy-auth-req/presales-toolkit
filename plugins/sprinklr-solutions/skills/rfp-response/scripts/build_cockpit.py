#!/usr/bin/env python3
"""Generate the RFP cockpit -- a single self-contained HTML status page.

A status view, not the audit trail: it carries counts and the named items that
decide the bid, never source URLs, POCs or internal caveats. Opens in a browser
and publishes unchanged as an Artifact.

LANGUAGE. This file, like the whole skill, is written in English. Everything the
cockpit *renders* is a label pulled from config.cockpit.labels, so the page comes
out in the customer's language (or whatever language the user asked for). Defaults
below are English; override every one of them per engagement.

Reads the same _work/ artefacts as build_state.py.
"""
import html
import os
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rfp_lib import BASE, load_answers, load_config, load_inventory, sources, write_out  # noqa: E402

# English defaults. config.cockpit.labels overrides any of them.
L = {
    "answered": "Answered",
    "ko_short": "Eligibility failed",
    "evidence_missing": "Evidence missing",
    "open_owner": "Open with AE",
    "h_eligibility": "Eligibility",
    "h_progress": "Progress by catalogue",
    "h_evidence": "Evidence position",
    "h_decisions": "Still to be decided",
    "ko_lead": "{n} mandatory criteria not met.",
    "ko_body": ("Mandatory criteria are pass/fail — they are not scored. "
                "Each of these answers states the gap openly."),
    "scored_note": "A further {n} scored or open criteria are not met. These cost points, not eligibility.",
    "legend_green": "sound",
    "legend_amber": "with caveats",
    "legend_red": "critical",
    "ev_total": "{n} artefacts demanded",
    "ev_yes": "available",
    "ev_nda": "under NDA",
    "ev_third": "from third parties",
    "ev_missing": "missing",
    "file_prefix": "File",
    "foot": "Generated from _work/answers/ · {d} · Internal overview, not part of the submission",
}


def e(s):
    return html.escape(str(s))


def bar(counts, total):
    segs = []
    for key, cls in (("green", "g"), ("amber", "a"), ("red", "r")):
        n = counts.get(key, 0)
        if n:
            segs.append(f'<span class="seg {cls}" style="flex:{n}"></span>')
    return f'<div class="bar" role="img" aria-label="{total}">' + "".join(segs) + "</div>"


def title_of(inv, iid, cap=76):
    """Criterion catalogues carry a title; question sheets carry the question
    itself -- and the question identifies the row, not its section heading."""
    x = inv.get(iid, {})
    extra = x.get("extra") or {}
    t = extra.get("title") or x.get("question") or x.get("section_title") or ""
    t = " ".join(str(t).split())
    return t[: cap - 1] + "…" if len(t) > cap else t


CSS = """
:root{
  --paper:#F7F8FA; --card:#FFFFFF; --ink:#14171C; --ink-2:#4A5260; --ink-3:#78818F;
  --rule:#E3E7ED; --rule-2:#EDF0F4;
  --accent:#1250DE; --ok:#2F7A4F; --warn:#B0801F; --crit:#B4342B;
  --crit-bg:#F8E8E7;
}
@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]){
  --paper:#101319; --card:#171B22; --ink:#E9ECF1; --ink-2:#A3ACBA; --ink-3:#6F7887;
  --rule:#262C36; --rule-2:#1E232B;
  --accent:#7FA0F5; --ok:#5FBF8A; --warn:#D8AE55; --crit:#E0776E;
  --crit-bg:#2A1917;
}}
:root[data-theme="dark"]{
  --paper:#101319; --card:#171B22; --ink:#E9ECF1; --ink-2:#A3ACBA; --ink-3:#6F7887;
  --rule:#262C36; --rule-2:#1E232B;
  --accent:#7FA0F5; --ok:#5FBF8A; --warn:#D8AE55; --crit:#E0776E;
  --crit-bg:#2A1917;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:44px 28px 72px}
code,.num,.tag{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums}
.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:32px;
  padding-bottom:18px;border-bottom:2px solid var(--ink);flex-wrap:wrap}
.mast h1{margin:0;font-size:25px;font-weight:600;letter-spacing:-.015em;text-wrap:balance}
.mast .sub{color:var(--ink-2);font-size:14px;margin-top:3px}
.state{display:flex;align-items:center;gap:9px;font-size:13px;color:var(--ink-2);white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);flex:none}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:2px;background:var(--rule);border-bottom:1px solid var(--rule)}
.fig{background:var(--paper);padding:20px 4px 22px 0}
.fig .v{font-size:31px;font-weight:600;letter-spacing:-.02em;line-height:1.05;
  font-family:"IBM Plex Mono",monospace}
.fig .k{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--ink-3);margin-top:7px}
.fig.crit .v{color:var(--crit)}
h2{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);
  font-weight:600;margin:44px 0 14px}
.ko{background:var(--crit-bg);border-left:3px solid var(--crit);border-radius:0 5px 5px 0;
  padding:20px 24px 8px}
.ko .lead{font-size:14px;color:var(--ink);margin:0;max-width:64ch}
.ko .lead b{color:var(--crit)}
ul.fails{list-style:none;margin:14px 0 0;padding:0;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:0 30px}
ul.fails li{display:grid;grid-template-columns:112px 1fr;gap:2px 12px;
  padding:11px 0;border-top:1px solid color-mix(in srgb,var(--crit) 16%,transparent)}
ul.fails code{font-size:12.5px;color:var(--ink);font-weight:500}
.ft{font-size:13.5px;color:var(--ink);line-height:1.4}
.fm{grid-column:2;font-size:11.5px;color:var(--ink-2);display:flex;gap:8px;align-items:center}
.tag{font-size:10px;padding:1px 5px;border-radius:3px;background:var(--rule);color:var(--ink-2)}
.scored{margin-top:8px}
.scored ul.fails li{border-top-color:var(--rule)}
.scored .note{font-size:13px;color:var(--ink-2);margin:0;max-width:64ch}
.file{display:grid;grid-template-columns:1fr 210px 84px;gap:22px;align-items:center;
  padding:15px 0;border-top:1px solid var(--rule)}
.file:last-child{border-bottom:1px solid var(--rule)}
.file .nm{font-size:14px}
.file .nm .t{font-size:11px;color:var(--ink-3);margin-top:2px}
.file .ct{text-align:right;font-family:"IBM Plex Mono",monospace;font-size:14px;color:var(--ink-2)}
.bar{display:flex;height:7px;border-radius:4px;overflow:hidden;background:var(--rule-2)}
.seg.g{background:var(--ok)} .seg.a{background:var(--warn)} .seg.r{background:var(--crit)}
.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:11.5px;color:var(--ink-2)}
.legend i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:6px}
.ev{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule);border-radius:5px;overflow:hidden}
.ev div{background:var(--card);padding:15px 16px}
.ev .v{font-family:"IBM Plex Mono",monospace;font-size:22px;font-weight:600}
.ev .k{font-size:11px;color:var(--ink-3);margin-top:3px;text-transform:uppercase;letter-spacing:.07em}
.ev .miss .v{color:var(--crit)}
.own{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:26px}
.own section{border-top:2px solid var(--accent);padding-top:13px}
.own h3{margin:0 0 5px;font-size:14px;font-weight:600}
.own p{margin:0;font-size:13px;color:var(--ink-2);max-width:44ch}
.own .n{font-family:"IBM Plex Mono",monospace;font-size:19px;font-weight:600;color:var(--accent)}
.foot{margin-top:52px;padding-top:16px;border-top:1px solid var(--rule);
  font-size:11.5px;color:var(--ink-3)}
@media (max-width:660px){
  .file{grid-template-columns:1fr;gap:9px}
  .file .ct{text-align:left}
  ul.fails li{grid-template-columns:100px 1fr}
}
"""


def main():
    cfg = load_config()
    spec = cfg.get("cockpit") or {}
    L.update(spec.get("labels") or {})
    srcs = sources(cfg)
    inv = load_inventory()
    by_id, _by_batch, _docs = load_answers()
    items = list(by_id.values())
    total = len(items)
    if not total:
        print("no answers yet — cockpit not built")
        return

    rag = Counter(i.get("rag") for i in items)

    # A failing mandatory criterion threatens eligibility; a failing scored one only
    # costs points. Most public tenders draw that line and the cockpit must not
    # flatten it. ko_criterion_type names the mandatory type in the customer's own
    # vocabulary; leave it unset and everything lands in one list.
    ko_type = spec.get("ko_criterion_type")
    fails = [i for i in items
             if i.get("verdict") == "fail" or i.get("std_fulfillment") == "nein"]

    def ctype(iid):
        return ((inv.get(iid) or {}).get("extra") or {}).get("criterion_type")

    ko = [i for i in fails if ko_type and ctype(i["id"]) == ko_type]
    oth = [i for i in fails if i not in ko]

    ev = Counter(n.get("available") for i in items for n in (i.get("evidence_internal") or []))
    ev_total = sum(ev.values())
    owner_prefix = spec.get("owner_prefix", "AE:")
    owned = [i for i in items if str(i.get("open_question") or "").startswith(owner_prefix)]

    def short(sid):
        s = srcs.get(sid) or {}
        return s.get("short") or s.get("label", sid)

    def rows(rs, show_type=True):
        out = []
        for i in sorted(rs, key=lambda x: str(x["id"])):
            sid = (inv.get(i["id"]) or {}).get("source", "")
            meta = f'<span class="tag">{e(short(sid))}</span>'
            if show_type:
                t = ctype(i["id"]) or ""
                if t:
                    meta += e(t)
            out.append(f'<li><code>{e(i["id"])}</code>'
                       f'<span class="ft">{e(title_of(inv, i["id"]) or "—")}</span>'
                       f'<span class="fm">{meta}</span></li>')
        return "\n".join(out)

    ko_html = (f'<div class="ko"><p class="lead"><b>{e(L["ko_lead"].format(n=len(ko)))}</b> '
               f'{e(L["ko_body"])}</p><ul class="fails">{rows(ko, show_type=False)}</ul></div>'
               if ko else "")
    oth_html = (f'<div class="scored"><p class="note">{e(L["scored_note"].format(n=len(oth)))}</p>'
                f'<ul class="fails">{rows(oth)}</ul></div>' if oth else "")

    files_html = ""
    for s in cfg.get("sources", []):
        sub = [i for i in items if (inv.get(i["id"]) or {}).get("source") == s["id"]]
        if not sub:
            continue
        c = Counter(i.get("rag") for i in sub)
        files_html += (f'<div class="file"><div class="nm">{e(s.get("label", s["id"]))}'
                       f'<div class="t">{e(L["file_prefix"])} {e(s.get("short", s["id"]))}</div></div>'
                       f'{bar(c, len(sub))}<div class="ct">{len(sub)}</div></div>')

    panels = ""
    for pn in spec.get("panels", []):
        panels += (f'<section><h3>{e(pn.get("title",""))}</h3>'
                   f'<div class="n">{e(pn.get("value",""))}</div>'
                   f'<p>{e(pn.get("note",""))}</p></section>')

    st = spec.get("status") or {}
    doc = f"""<title>{e(spec.get("title", cfg.get("customer", "RFP")))}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
  <header class="mast">
    <div><h1>{e(cfg.get("engagement", ""))}</h1>
    <div class="sub">{e(cfg.get("customer", ""))}</div></div>
    <div class="state"><span class="dot"></span>{e(st.get("label", ""))}
    {(" · " + e(st["on"])) if st.get("on") else ""}</div>
  </header>
  <div class="figs">
    <div class="fig"><div class="v">{total}</div><div class="k">{e(L["answered"])}</div></div>
    <div class="fig crit"><div class="v">{len(ko) or len(fails)}</div><div class="k">{e(L["ko_short"])}</div></div>
    <div class="fig crit"><div class="v">{ev.get("missing",0)}</div><div class="k">{e(L["evidence_missing"])}</div></div>
    <div class="fig"><div class="v">{len(owned)}</div><div class="k">{e(L["open_owner"])}</div></div>
  </div>
  <h2>{e(L["h_eligibility"])}</h2>
  {ko_html}{oth_html}
  <h2>{e(L["h_progress"])}</h2>
  <div class="files">{files_html}</div>
  <div class="legend">
    <span><i style="background:var(--ok)"></i>{e(L["legend_green"])} {rag["green"]}</span>
    <span><i style="background:var(--warn)"></i>{e(L["legend_amber"])} {rag["amber"]}</span>
    <span><i style="background:var(--crit)"></i>{e(L["legend_red"])} {rag["red"]}</span>
  </div>
  <h2>{e(L["h_evidence"])} — {e(L["ev_total"].format(n=ev_total))}</h2>
  <div class="ev">
    <div><div class="v">{ev.get("yes",0)}</div><div class="k">{e(L["ev_yes"])}</div></div>
    <div><div class="v">{ev.get("nda",0)}</div><div class="k">{e(L["ev_nda"])}</div></div>
    <div><div class="v">{ev.get("third_party",0)}</div><div class="k">{e(L["ev_third"])}</div></div>
    <div class="miss"><div class="v">{ev.get("missing",0)}</div><div class="k">{e(L["ev_missing"])}</div></div>
  </div>
  {f'<h2>{e(L["h_decisions"])}</h2><div class="own">{panels}</div>' if panels else ""}
  <div class="foot">{e(L["foot"].format(d=date.today().strftime("%d.%m.%Y")))}</div>
</div>
"""
    write_out(spec.get("filename", "RFP-Cockpit.html"), doc, "Cockpit")
    print(f"  {total} answered · {len(ko)} mandatory failures · {ev.get('missing',0)} evidence gaps")


if __name__ == "__main__":
    main()
