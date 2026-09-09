#!/usr/bin/env python3
"""Restore extended (x14) data validation that an openpyxl round-trip strips.

openpyxl warns "Data Validation extension is not supported and will be removed" on
load and then silently drops those dropdowns on save. Cell values are unaffected;
the input validation is not. Splices the original <extLst> dataValidations block
back into the saved workbook at the XML level.

Usage: restore_validation.py <current.xlsx> <pristine-original.xlsx> [--apply]
"""
import re, shutil, sys, zipfile, os

EXT_RE = re.compile(
    r'<extLst>\s*<ext[^>]*mc:Ignorable="x14"[^>]*>\s*<x14:dataValidations.*?</ext>\s*</extLst>',
    re.S)
ALT_RE = re.compile(r'<extLst>.*?<x14:dataValidations.*?</extLst>', re.S)


def grab(path):
    """{sheet_name: extLst_xml} for sheets that carry x14 validations."""
    out = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if not n.startswith("xl/worksheets/sheet"):
                continue
            xml = z.read(n).decode("utf8")
            if "x14:dataValidation" not in xml:
                continue
            m = EXT_RE.search(xml) or ALT_RE.search(xml)
            if m:
                out[n] = m.group(0)
    return out


NS = {
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "x14": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main",
    "xm": "http://schemas.microsoft.com/office/excel/2006/main",
    "xr": "http://schemas.microsoft.com/office/spreadsheetml/2014/revision",
    "xr2": "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2",
    "x14ac": "http://schemas.microsoft.com/office/spreadsheetml/2009/9/ac",
}

PREFIX_RE = re.compile(r'[<\s]/?([A-Za-z][A-Za-z0-9]*):[A-Za-z]')


def ensure_ns(xml):
    """openpyxl drops the x14/xm namespace declarations along with the extLst.
    Re-inserting x14 elements without them produces 'unbound prefix' and a file
    neither Excel nor openpyxl can open. Declare them on <worksheet>."""
    m = re.match(r"(.*?<worksheet\b)([^>]*)(>)", xml, re.S)
    if not m:
        return xml
    head, attrs, close = m.groups()
    # Detect prefixes on BOTH elements and attributes -- xr:uid appears only as an
    # attribute, and missing it produces "unbound prefix" on an otherwise valid file.
    used = set(PREFIX_RE.findall(xml)) - {"xmlns"}
    unknown = sorted(p for p in used if p not in NS)
    for pfx in sorted(used):
        uri = NS.get(pfx)
        if uri and f'xmlns:{pfx}=' not in attrs:
            attrs += f' xmlns:{pfx}="{uri}"'
    if unknown:
        print(f"    !! undeclared prefixes with no known URI: {unknown}",
              file=sys.stderr)
    return head + attrs + close + xml[m.end():]


def splice(current, blocks, dest):
    with zipfile.ZipFile(current) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in items:
            if info.filename in blocks:
                xml = data.decode("utf8")
                if "x14:dataValidation" not in xml:
                    xml = xml.replace("</worksheet>",
                                      blocks[info.filename] + "</worksheet>")
                xml = ensure_ns(xml)          # idempotent; also repairs a prior splice
                data = xml.encode("utf8")
            zout.writestr(info, data)


def main():
    cur, orig = sys.argv[1], sys.argv[2]
    apply_ = "--apply" in sys.argv
    blocks = grab(orig)
    have = grab(cur)
    print(f"original: {len(blocks)} sheet(s) with x14 validation · "
          f"current: {len(have)}")
    if not blocks:
        print("  nothing to restore")
        return
    if have:
        print("  current already has the rules — checking namespace declarations")
    for n, b in blocks.items():
        rng = re.findall(r'<xm:sqref>([^<]+)</xm:sqref>', b)
        print(f"  {n.split('/')[-1]}: restoring {len(rng)} rule(s) -> {', '.join(rng)}")
    if not apply_:
        print("  dry run — pass --apply to write")
        return
    tmp = cur + ".tmp"
    splice(cur, blocks, tmp)
    shutil.move(tmp, cur)
    print(f"  RESTORED: {os.path.basename(cur)}")


if __name__ == "__main__":
    main()
