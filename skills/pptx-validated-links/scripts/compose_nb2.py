#!/usr/bin/env python3
"""Composite painterly NB2 images into an UNPACKED deck per a manifest. Stdlib only.

heroes -> full-bleed OPAQUE art behind text. If the slide is in --dividers, its
          existing big-number/part-label/title shapes are stripped and the text is
          re-laid into the image's negative-space side (left). A title hero keeps
          its existing text and just gets art behind it.
bg     -> full-bleed FAINT watermark (alphaModFix) behind the content shapes.

Always work on a COPY of the unpacked deck. Pilot 3 slides + render before scaling.
See references/nb2-imagery.md for art direction and references/pptx-gotchas.md §13
for why the strip regex must tolerate whitespace.

Usage:
  compose_nb2.py --unpacked DIR --manifest m.json --imgdir DIR \
      --accent 0F766E --num 9FD8CC --bg-alpha 20000 [--dividers dividers.json]

manifest entry: {"slide": 4, "role": "hero"|"bg", "slug": "div-what"}  (concept ignored here)
dividers JSON:  {"4": ["1","Part 1","What is an agent?"], "17": ["5","Part 5 · SOTA","AI Coding Agents"]}
  --num is the big-numeral color (use a light tint of --accent, ~65% toward white).
"""
import argparse, json, re, shutil, sys
from pathlib import Path

RID_RE = re.compile(r'Id="rId(\d+)"')
AT = "</p:grpSpPr>"
# whitespace-tolerant: unpack.py pretty-prints, generated XML is minified (gotchas §13)
STRIP_RE = re.compile(
    r'<p:sp>\s*<p:nvSpPr>\s*<p:cNvPr id="[234]" name="(?:BigNum|PartLbl|DivTitle)".*?</p:sp>',
    re.DOTALL)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def add_rel(slides_rels, media):
    t = slides_rels.read_text()
    nxt = max((int(m) for m in RID_RE.findall(t)), default=0) + 1
    rid = "rId" + str(nxt)
    t = t.replace("</Relationships>",
        '  <Relationship Id="' + rid + '" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="../media/' + media + '"/>\n'
        '</Relationships>')
    slides_rels.write_text(t)
    return rid


def pic(rid, alpha=None, sid=500):
    blip = '<a:blip r:embed="' + rid + '">' + (
        ('<a:alphaModFix amt="' + str(alpha) + '"/>') if alpha else '') + '</a:blip>'
    return ('<p:pic><p:nvPicPr><p:cNvPr id="' + str(sid) + '" name="BG"/><p:cNvPicPr/>'
            '<p:nvPr/></p:nvPicPr><p:blipFill>' + blip +
            '<a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr>'
            '<a:xfrm><a:off x="0" y="0"/><a:ext cx="9144000" cy="5143500"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def divider_text(num, label, title, num_color, accent, sub="555555"):
    return ('<p:sp><p:nvSpPr><p:cNvPr id="20" name="DivTxt"/><p:cNvSpPr txBox="1"/>'
        '<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="430000" y="1500000"/>'
        '<a:ext cx="4000000" cy="2300000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
        '</a:prstGeom></p:spPr><p:txBody><a:bodyPr anchor="ctr"/><a:lstStyle/>'
        '<a:p><a:pPr algn="l"/><a:r><a:rPr lang="en" sz="7200" b="1"><a:solidFill>'
        '<a:srgbClr val="' + num_color + '"/></a:solidFill></a:rPr><a:t>' + esc(num) + '</a:t></a:r></a:p>'
        '<a:p><a:pPr algn="l"/><a:r><a:rPr lang="en" sz="1500" b="1"><a:solidFill>'
        '<a:srgbClr val="' + sub + '"/></a:solidFill></a:rPr><a:t>' + esc(label) + '</a:t></a:r></a:p>'
        '<a:p><a:pPr algn="l"/><a:r><a:rPr lang="en" sz="3000" b="1"><a:solidFill>'
        '<a:srgbClr val="' + accent + '"/></a:solidFill></a:rPr><a:t>' + esc(title) + '</a:t></a:r></a:p>'
        '</p:txBody></p:sp>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unpacked", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--imgdir", required=True, type=Path)
    ap.add_argument("--accent", default="0F766E")
    ap.add_argument("--num", default="9FD8CC", help="divider big-number color (light tint of accent)")
    ap.add_argument("--bg-alpha", type=int, default=20000, help="0-100000; ~20000 = 12%% opacity")
    ap.add_argument("--dividers", type=Path, help='JSON {"slide": [num,label,title]} for divider slides')
    a = ap.parse_args()

    items = json.loads(a.manifest.read_text())
    dividers = {str(k): v for k, v in (json.loads(a.dividers.read_text()).items() if a.dividers else {})}
    slides = a.unpacked / "ppt" / "slides"
    rels = slides / "_rels"
    media = a.unpacked / "ppt" / "media"
    media.mkdir(exist_ok=True)
    n_hero = n_bg = 0
    for it in items:
        num, role, slug = str(it.get("slide")), it.get("role", "bg"), it.get("slug")
        img = a.imgdir / f"{slug}.png"
        sp = slides / f"slide{num}.xml"
        if not img.exists():
            print(f"  skip slide{num}: missing {img.name}", file=sys.stderr); continue
        if not sp.exists():
            print(f"  skip slide{num}: no slide{num}.xml", file=sys.stderr); continue
        mname = f"nb2-{slug}.png"
        shutil.copy(img, media / mname)
        t = sp.read_text()
        rid = add_rel(rels / f"slide{num}.xml.rels", mname)
        if role == "hero":
            if num in dividers:
                t, removed = STRIP_RE.subn("", t)
                if removed == 0:
                    print(f"  WARN slide{num}: strip matched 0 shapes (check shape names/regex)",
                          file=sys.stderr)
                n_, lbl, ttl = dividers[num]
                t = t.replace(AT, AT + "\n" + pic(rid) + "\n" +
                              divider_text(n_, lbl, ttl, a.num, a.accent), 1)
                if 'name="BigNum"' in t:
                    print(f"  WARN slide{num}: BigNum still present after strip", file=sys.stderr)
            else:  # title hero: keep existing text, art behind
                t = t.replace(AT, AT + "\n" + pic(rid), 1)
            n_hero += 1
        else:
            t = t.replace(AT, AT + "\n" + pic(rid, alpha=a.bg_alpha), 1)
            n_bg += 1
        sp.write_text(t)
    print(f"Composited: {n_hero} heroes, {n_bg} backgrounds into {a.unpacked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
