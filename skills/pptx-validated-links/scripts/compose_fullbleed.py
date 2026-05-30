#!/usr/bin/env python3
"""Overlay full-bleed images ON TOP of slides (opaque) — for FULL-SLIDE stylized renders,
where each slide IS one styled image (e.g. a chalkboard variant). The image covers all the
slide's vector content; nothing peeks out. Use a CLEAN VECTOR base deck (not one that already
has painterly backgrounds) to keep file size down. Stdlib only.

Contrast with compose_nb2.py, which puts art BEHIND the vector content (text stays live/editable).
This bakes text into the image: no live hyperlinks, not text-editable — a deliberate stylistic trade.

Usage: compose_fullbleed.py --unpacked DIR --imgdir DIR --manifest m.json
manifest: JSON list of {"slide": 204, "slug": "div-p1"} -> overlays imgdir/<slug>.png onto slide204.xml.
"""
import argparse, json, re, shutil, sys
from pathlib import Path

RID_RE = re.compile(r'Id="rId(\d+)"')


def slide_size(unpacked):
    t = (unpacked / "ppt" / "presentation.xml").read_text()
    m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', t)
    return (int(m.group(1)), int(m.group(2))) if m else (9144000, 5143500)


def add_rel(slides_rels, media):
    t = slides_rels.read_text()
    nxt = max((int(m) for m in RID_RE.findall(t)), default=0) + 1
    rid = "rId" + str(nxt)
    t = t.replace("</Relationships>",
        '  <Relationship Id="' + rid + '" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="../media/' + media + '"/>\n</Relationships>')
    slides_rels.write_text(t)
    return rid


def pic(rid, cx, cy, sid=900):
    return ('<p:pic><p:nvPicPr><p:cNvPr id="' + str(sid) + '" name="FullBleed"/><p:cNvPicPr/>'
            '<p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="' + rid + '"/>'
            '<a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr>'
            '<a:xfrm><a:off x="0" y="0"/><a:ext cx="' + str(cx) + '" cy="' + str(cy) + '"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unpacked", required=True, type=Path)
    ap.add_argument("--imgdir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    a = ap.parse_args()
    cx, cy = slide_size(a.unpacked)
    slides = a.unpacked / "ppt" / "slides"
    rels = slides / "_rels"
    media = a.unpacked / "ppt" / "media"
    media.mkdir(exist_ok=True)
    items = json.loads(a.manifest.read_text())
    n = 0
    for it in items:
        num, slug = it.get("slide"), it.get("slug")
        img = a.imgdir / f"{slug}.png"
        sp = slides / f"slide{num}.xml"
        if not img.exists():
            print(f"  skip slide{num}: missing {img.name}", file=sys.stderr); continue
        if not sp.exists():
            print(f"  skip slide{num}: no slide{num}.xml", file=sys.stderr); continue
        mname = f"fb-{slug}.png"
        shutil.copy(img, media / mname)
        rid = add_rel(rels / f"slide{num}.xml.rels", mname)
        t = sp.read_text()
        if "</p:spTree>" not in t:
            print(f"  WARN slide{num}: no </p:spTree>", file=sys.stderr); continue
        t = t.replace("</p:spTree>", pic(rid, cx, cy) + "</p:spTree>", 1)
        sp.write_text(t)
        n += 1
    print(f"Overlaid full-bleed art on {n} slides ({cx}x{cy} EMU each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
