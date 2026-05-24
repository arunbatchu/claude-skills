"""Aggregate [LINK-DATA] blocks from all notes and build categorized References slide(s).

Reads every ppt/notesSlides/notesSlide*.xml, extracts blocks of the form:

    [LINK-DATA verified=YYYY-MM-DD]
    category | label | url
    ...
    [/LINK-DATA]

Dedupes by URL, groups by category (acronym, person, product, citation, standard),
sorts alphabetically within each category, and either:
  - emits an aggregated TSV (default), and/or
  - generates a new References slide and inserts it after a specified slide.

Usage:
    # Aggregate only — print consolidated TSV
    python build_references.py --unpacked unpacked/ --tsv-out references.tsv

    # Generate + insert References slide after slide N (the new slide becomes N+1)
    python build_references.py --unpacked unpacked/ --insert-after 87 --title "References"

Notes on inserting:
  - Touches 7 files (slideX.xml, slideX.xml.rels, notesSlideX.xml, notesSlideX.xml.rels,
    [Content_Types].xml, presentation.xml.rels, presentation.xml).
  - If the deck already has 50+ unique links, the script does not auto-split into
    multiple slides — content may overflow. For deck-wide use, hand-split by passing
    --categories acronym,person and again with --categories product,citation,standard.
"""
import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

HLINK_COLOR = "7A0019"
HLINK_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
NOTES_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"

CATEGORY_TITLES = OrderedDict([
    ("acronym", "Acronyms & Terms"),
    ("person", "People"),
    ("product", "Products & Tools"),
    ("citation", "Sources & Guidance"),
    ("standard", "Standards"),
])


def extract_link_data(notes_text: str) -> list[tuple[str, str, str]]:
    """Pull (category, label, url) rows from [LINK-DATA]...[/LINK-DATA] blocks."""
    rows: list[tuple[str, str, str]] = []
    # The block lives across multiple <a:t> runs (one paragraph per row).
    # Extract all <a:t> contents, then look for the markers.
    texts = re.findall(r'<a:t(?:\s[^>]*)?>([^<]*)</a:t>', notes_text)
    in_block = False
    for t in texts:
        if t.startswith("[LINK-DATA"):
            in_block = True
            continue
        if t.startswith("[/LINK-DATA]"):
            in_block = False
            continue
        if in_block and "|" in t:
            parts = [p.strip() for p in t.split("|")]
            if len(parts) == 3:
                category, label, url = parts
                # Decode common entities
                label = label.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                rows.append((category, label, url))
    return rows


def aggregate(unpacked: Path, categories: set[str] | None = None) -> dict[str, list[tuple[str, str]]]:
    """Walk notes; return {category: [(label, url), ...]} sorted alphabetically, deduped by URL."""
    notes_dir = unpacked / "ppt" / "notesSlides"
    seen_urls: dict[str, tuple[str, str]] = {}
    for nfile in sorted(notes_dir.glob("notesSlide*.xml")):
        text = nfile.read_text(encoding="utf-8")
        for category, label, url in extract_link_data(text):
            if categories and category not in categories:
                continue
            if url not in seen_urls:
                seen_urls[url] = (category, label)

    groups: dict[str, list[tuple[str, str]]] = {}
    for url, (category, label) in seen_urls.items():
        groups.setdefault(category, []).append((label, url))
    for cat in groups:
        groups[cat].sort(key=lambda x: x[0].lower())
    return groups


def cat_header_para(title: str) -> str:
    safe = title.replace("&", "&amp;")
    return (
        f'          <a:p>\n'
        f'            <a:pPr marL="0" lvl="0" indent="0" algn="l" rtl="0"><a:spcBef><a:spcPts val="600"/></a:spcBef><a:spcAft><a:spcPts val="200"/></a:spcAft><a:buNone/></a:pPr>\n'
        f'            <a:r><a:rPr lang="en" sz="1200" b="1"><a:solidFill><a:schemeClr val="dk1"/></a:solidFill></a:rPr><a:t>{safe}</a:t></a:r>\n'
        f'          </a:p>\n'
    )


def link_para(label: str, url_to_rid: dict[str, str], url: str) -> str:
    safe = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rid = url_to_rid[url]
    return (
        f'          <a:p>\n'
        f'            <a:pPr marL="0" lvl="0" indent="0" algn="l" rtl="0"><a:spcBef><a:spcPts val="0"/></a:spcBef><a:spcAft><a:spcPts val="0"/></a:spcAft><a:buNone/></a:pPr>\n'
        f'            <a:r><a:rPr lang="en" sz="1000"/><a:t>• </a:t></a:r>'
        f'<a:r><a:rPr lang="en" sz="1000" u="sng"><a:solidFill><a:srgbClr val="{HLINK_COLOR}"/></a:solidFill>'
        f'<a:hlinkClick xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="{rid}"/></a:rPr><a:t>{safe}</a:t></a:r>\n'
        f'          </a:p>\n'
    )


def build_slide_xml(groups: dict[str, list[tuple[str, str]]], url_to_rid: dict[str, str], title: str, footer_num: str, logo_rid: str = "rId3") -> str:
    """Two-column references slide. Left col: first half of categories; right col: rest."""
    items = []
    for cat_key, cat_title in CATEGORY_TITLES.items():
        if cat_key not in groups or not groups[cat_key]:
            continue
        items.append((cat_title, groups[cat_key]))

    # Split roughly in half by row count
    total_rows = sum(len(rows) + 1 for _, rows in items)
    half = total_rows // 2
    left_parts: list[str] = []
    right_parts: list[str] = []
    cumulative = 0
    for cat_title, rows in items:
        block = cat_header_para(cat_title) + "".join(link_para(lbl, url_to_rid, u) for lbl, u in rows)
        if cumulative + len(rows) + 1 <= half:
            left_parts.append(block)
            cumulative += len(rows) + 1
        else:
            right_parts.append(block)
    left_body = "".join(left_parts) or '          <a:p><a:r><a:rPr lang="en" sz="1000"/><a:t></a:t></a:r></a:p>\n'
    right_body = "".join(right_parts) or '          <a:p><a:r><a:rPr lang="en" sz="1000"/><a:t></a:t></a:r></a:p>\n'

    safe_title = title.replace("&", "&amp;")
    return f'''<?xml version="1.0" encoding="utf-8"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name="References"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="311700" y="350000"/><a:ext cx="8520600" cy="540000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
        <p:txBody>
          <a:bodyPr spcFirstLastPara="1" wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="t"><a:noAutofit/></a:bodyPr>
          <a:lstStyle/>
          <a:p><a:r><a:rPr lang="en"/><a:t>{safe_title}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <p:pic>
        <p:nvPicPr><p:cNvPr id="3" name="Logo"/><p:cNvPicPr preferRelativeResize="0"/><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="{logo_rid}"><a:alphaModFix/></a:blip><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr><a:xfrm><a:off x="8048408" y="289874"/><a:ext cx="839337" cy="461700"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
      </p:pic>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="4" name="Left"/><p:cNvSpPr txBox="1"><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="311700" y="950000"/><a:ext cx="4200000" cy="3850000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
        <p:txBody>
          <a:bodyPr spcFirstLastPara="1" wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="t"><a:noAutofit/></a:bodyPr>
          <a:lstStyle/>
{left_body}        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="5" name="Right"/><p:cNvSpPr txBox="1"><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="2"/></p:nvPr></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="4632400" y="950000"/><a:ext cx="4200000" cy="3850000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
        <p:txBody>
          <a:bodyPr spcFirstLastPara="1" wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="t"><a:noAutofit/></a:bodyPr>
          <a:lstStyle/>
{right_body}        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="6" name="PageNum"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="8046720" y="4793500"/><a:ext cx="640080" cy="274320"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
        <p:txBody>
          <a:bodyPr wrap="none"><a:spAutoFit/></a:bodyPr><a:lstStyle/>
          <a:p><a:pPr algn="r"/><a:r><a:rPr sz="1000"><a:solidFill><a:srgbClr val="808080"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>{footer_num}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
'''


def insert_slide(unpacked: Path, slide_xml: str, slide_rels_xml: str, after_slide_num: int, logo_image: str = "image1.png", layout_file: str = "slideLayout1.xml") -> int:
    """Insert a new slide AFTER after_slide_num (file-name basis). Returns new slide number."""
    slides_dir = unpacked / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    notes_dir = unpacked / "ppt" / "notesSlides"
    notes_rels_dir = notes_dir / "_rels"
    pres_path = unpacked / "ppt" / "presentation.xml"
    pres_rels_path = unpacked / "ppt" / "_rels" / "presentation.xml.rels"
    ct_path = unpacked / "[Content_Types].xml"

    # Find next free slide number
    existing = [int(m.group(1)) for f in slides_dir.glob("slide*.xml") if (m := re.match(r"slide(\d+)\.xml$", f.name))]
    new_num = max(existing) + 1

    # 1. slideX.xml
    (slides_dir / f"slide{new_num}.xml").write_text(slide_xml, encoding="utf-8")

    # 2. slideX.xml.rels (always points to image32.png from the deck — adjust if needed)
    (rels_dir / f"slide{new_num}.xml.rels").write_text(slide_rels_xml, encoding="utf-8")

    # 3. minimal notesSlideX.xml
    notes_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" showMasterSp="0" showMasterPhAnim="0">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name="Notes"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    <p:sp><p:nvSpPr><p:cNvPr id="2" name="SlideImg"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg" idx="2"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="381000" y="685800"/><a:ext cx="6096000" cy="3429000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:sp>
    <p:sp><p:nvSpPr><p:cNvPr id="3" name="Body"/><p:cNvSpPr txBox="1"><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="685800" y="4343400"/><a:ext cx="5486400" cy="4114800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
      <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr marL="0" lvl="0" indent="0" algn="l" rtl="0"><a:buNone/></a:pPr><a:r><a:rPr lang="en-US" b="1" dirty="0"/><a:t>References — auto-generated by build_references.py</a:t></a:r></a:p></p:txBody>
    </p:sp>
  </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:notes>
'''
    (notes_dir / f"notesSlide{new_num}.xml").write_text(notes_xml, encoding="utf-8")

    # 4. notesSlideX.xml.rels
    notes_rels = f'''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="{SLIDE_REL_TYPE}" Target="../slides/slide{new_num}.xml"/>
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="../notesMasters/notesMaster1.xml"/>
</Relationships>
'''
    (notes_rels_dir / f"notesSlide{new_num}.xml.rels").write_text(notes_rels, encoding="utf-8")

    # 5. [Content_Types].xml — add Override for slide + notesSlide
    ct = ct_path.read_text(encoding="utf-8")
    overrides = (
        f'  <Override PartName="/ppt/slides/slide{new_num}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>\n'
        f'  <Override PartName="/ppt/notesSlides/notesSlide{new_num}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>\n'
    )
    ct = ct.replace("</Types>", overrides + "</Types>")
    ct_path.write_text(ct, encoding="utf-8")

    # 6. presentation.xml.rels — add Relationship for the new slide
    pres_rels = pres_rels_path.read_text(encoding="utf-8")
    rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', pres_rels)]
    new_rid = f"rId{max(rids) + 1}"
    new_rel = f'  <Relationship Id="{new_rid}" Type="{SLIDE_REL_TYPE}" Target="slides/slide{new_num}.xml"/>\n'
    pres_rels = pres_rels.replace("</Relationships>", new_rel + "</Relationships>")
    pres_rels_path.write_text(pres_rels, encoding="utf-8")

    # 7. presentation.xml sldIdLst — insert new <p:sldId> after the rId for after_slide_num
    pres = pres_path.read_text(encoding="utf-8")
    # Find the rId for slide{after_slide_num}.xml in presentation.xml.rels
    target = f'Target="slides/slide{after_slide_num}.xml"'
    rel_m = re.search(rf'<Relationship Id="(rId\d+)"[^>]*{re.escape(target)}', pres_rels)
    if not rel_m:
        print(f"WARNING: rId for slide{after_slide_num}.xml not found in presentation.xml.rels; appending sldId at end", file=sys.stderr)
        pres = pres.replace("</p:sldIdLst>", f'    <p:sldId id="{900 + new_num}" r:id="{new_rid}"/>\n  </p:sldIdLst>')
    else:
        after_rid = rel_m.group(1)
        # Insert new <p:sldId> right after the line with after_rid
        pattern = rf'(    <p:sldId id="[^"]+" r:id="{after_rid}"/>\n)'
        pres = re.sub(pattern, rf'\g<1>    <p:sldId id="{900 + new_num}" r:id="{new_rid}"/>\n', pres, count=1)
    pres_path.write_text(pres, encoding="utf-8")

    return new_num


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unpacked", required=True, type=Path)
    p.add_argument("--tsv-out", type=Path, help="Write aggregated TSV to this path")
    p.add_argument("--insert-after", type=int, help="Insert a new References slide AFTER this slide file number")
    p.add_argument("--title", default="References", help="Title text for the new slide")
    p.add_argument("--categories", help="Comma-separated category filter (acronym,person,product,citation,standard)")
    p.add_argument("--logo-image", default="image1.png", help="Logo image filename under ppt/media/")
    p.add_argument("--layout", default="slideLayout1.xml", help="Slide layout to reference")
    p.add_argument("--footer-num", default="", help="Footer page number for the new slide (default empty)")
    args = p.parse_args()

    cat_filter = set(args.categories.split(",")) if args.categories else None
    groups = aggregate(args.unpacked, cat_filter)
    total = sum(len(v) for v in groups.values())
    print(f"Aggregated {total} unique links across {len(groups)} categories")
    for cat, rows in groups.items():
        print(f"  {cat}: {len(rows)}")

    if args.tsv_out:
        with args.tsv_out.open("w", encoding="utf-8") as f:
            for cat, rows in groups.items():
                for label, url in rows:
                    f.write(f"{cat}\t{label}\t{url}\n")
        print(f"\nWrote {args.tsv_out}")

    if args.insert_after is not None:
        # Build URL -> rId map for the new slide's rels
        all_urls = [(label, url) for rows in groups.values() for (label, url) in rows]
        url_to_rid: dict[str, str] = {}
        rid_counter = 4
        rels_extras = []
        for _, url in all_urls:
            if url in url_to_rid:
                continue
            rid = f"rId{rid_counter}"
            rid_counter += 1
            url_to_rid[url] = rid
            rels_extras.append(f'  <Relationship Id="{rid}" Type="{HLINK_REL_TYPE}" Target="{url}" TargetMode="External"/>')

        # Build new slide's .rels — use ../media/<logo_image> for logo (rId3)
        base_rels = f'''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{args.logo_image}"/>
  <Relationship Id="rId2" Type="{NOTES_REL_TYPE}" Target="../notesSlides/notesSlideNEW.xml"/>
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/{args.layout}"/>
{chr(10).join(rels_extras)}
</Relationships>
'''
        slide_xml = build_slide_xml(groups, url_to_rid, args.title, args.footer_num or "")
        # We need the notesSlide filename to match the new slide number; do the insert first to get the number
        # Insert with a placeholder; then fix the rels back-reference.
        new_num = insert_slide(args.unpacked, slide_xml, base_rels.replace("notesSlideNEW.xml", f"notesSlide{0}.xml"), args.insert_after, args.logo_image, args.layout)
        # Fix the placeholder notesSlide reference now that we know new_num
        new_rels_path = args.unpacked / "ppt" / "slides" / "_rels" / f"slide{new_num}.xml.rels"
        text = new_rels_path.read_text(encoding="utf-8")
        new_rels_path.write_text(text.replace("notesSlide0.xml", f"notesSlide{new_num}.xml"), encoding="utf-8")

        print(f"\nInserted References slide as slide{new_num}.xml (after slide{args.insert_after}.xml).")
        print("Repack with anthropic-skills:pptx's pack.py to produce the final .pptx.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
