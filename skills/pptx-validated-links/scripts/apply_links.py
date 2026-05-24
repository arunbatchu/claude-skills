"""Apply hyperlinks to runs inside an unpacked PPTX.

Reads candidates.tsv (slide, category, label, url, [anchor], [substring]).
For each (slide, anchor), splits the matching <a:t> run into prefix + linked
substring(s) + suffix runs and adds hyperlink relationships to the slide's rels.

If `anchor` is empty, auto-finds the first run on the slide whose text contains
`label`. (Specify `anchor` explicitly to avoid matching titles.)

Outputs applied_links.tsv with the rows that succeeded — feed this to
append_link_data.py and build_references.py.

Usage:
    python apply_links.py --unpacked unpacked/ --plan candidates.tsv [--color 7A0019]
"""
import argparse
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

RUN_RE = re.compile(
    r'<a:r>\s*(<a:rPr\b[^>]*?(?:/>|>.*?</a:rPr>))?\s*<a:t(?:\s[^>]*)?>([^<]*)</a:t>\s*</a:r>',
    re.DOTALL,
)
HLINK_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"


def make_run(text: str, sz: str | None, bold: bool, italic: bool, color_scheme: bool = False, rid: str | None = None, color: str = "7A0019") -> str:
    sz_attr = f' sz="{sz}"' if sz else ""
    b = ' b="1"' if bold else ""
    i_attr = ' i="1"' if italic else ""
    if rid:
        return (
            f'<a:r><a:rPr lang="en"{sz_attr}{b}{i_attr} u="sng">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:hlinkClick xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="{rid}"/>'
            f'</a:rPr><a:t>{text}</a:t></a:r>'
        )
    if color_scheme:
        return (
            f'<a:r><a:rPr lang="en"{sz_attr}{b}{i_attr}>'
            f'<a:solidFill><a:schemeClr val="dk1"/></a:solidFill>'
            f'</a:rPr><a:t>{text}</a:t></a:r>'
        )
    return f'<a:r><a:rPr lang="en"{sz_attr}{b}{i_attr}/><a:t>{text}</a:t></a:r>'


def next_rid(rels_text: str) -> int:
    rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels_text)]
    return (max(rids) + 1) if rids else 1


def add_hlink_rel(rels_text: str, rid: str, url: str) -> str:
    new = f'  <Relationship Id="{rid}" Type="{HLINK_REL_TYPE}" Target="{url}" TargetMode="External"/>\n'
    return rels_text.replace("</Relationships>", new + "</Relationships>")


def split_run(slide_xml: str, anchor_text: str, links: list[tuple[str, str]], color: str) -> tuple[str, bool, list[str]]:
    """Find anchor_text run, split it, return (new_xml, ok, applied_substrings)."""
    for m in RUN_RE.finditer(slide_xml):
        rpr = m.group(1) or ""
        text = m.group(2)
        if text != anchor_text:
            continue
        sz_m = re.search(r'sz="(\d+)"', rpr)
        sz = sz_m.group(1) if sz_m else None
        bold = ' b="1"' in rpr
        italic = ' i="1"' in rpr
        color_scheme = "schemeClr" in rpr
        cursor = 0
        parts: list[str] = []
        applied: list[str] = []
        for substring, rid in links:
            idx = text.find(substring, cursor)
            if idx == -1:
                continue
            if idx > cursor:
                parts.append(make_run(text[cursor:idx], sz, bold, italic, color_scheme=color_scheme))
            parts.append(make_run(substring, sz, bold, italic, rid=rid, color=color))
            applied.append(substring)
            cursor = idx + len(substring)
        if not applied:
            continue
        if cursor < len(text):
            parts.append(make_run(text[cursor:], sz, bold, italic, color_scheme=color_scheme))
        return slide_xml[:m.start()] + "".join(parts) + slide_xml[m.end():], True, applied
    return slide_xml, False, []


def find_anchor_for(slide_xml: str, label: str) -> str | None:
    """Auto-discovery: return the first run text that contains `label`, else None."""
    for m in RUN_RE.finditer(slide_xml):
        if label in m.group(2):
            return m.group(2)
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unpacked", required=True, type=Path, help="Path to unpacked PPTX directory")
    p.add_argument("--plan", required=True, type=Path, help="Path to candidates.tsv")
    p.add_argument("--color", default="7A0019", help="Hex color for link text (default UMN maroon). Note: renderers may use the theme's hlink color instead; use recolor_hyperlinks.py for a real color change.")
    p.add_argument("--out", default="applied_links.tsv", type=Path, help="Output TSV of applied rows")
    args = p.parse_args()

    slides_dir = args.unpacked / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"

    # Group rows by (slide, anchor)
    grouped: OrderedDict[tuple[str, str], list[tuple[str, str, str, str]]] = OrderedDict()
    for line in args.plan.read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        slide, category, label, url = parts[:4]
        anchor = parts[4] if len(parts) > 4 and parts[4] else ""
        substring = parts[5] if len(parts) > 5 and parts[5] else label
        grouped.setdefault((slide, anchor), []).append((category, label, url, substring))

    applied_rows: list[tuple[str, str, str, str]] = []
    failures: list[str] = []

    for (slide_num, anchor), specs in grouped.items():
        slide_path = slides_dir / f"slide{slide_num}.xml"
        rels_path = rels_dir / f"slide{slide_num}.xml.rels"
        if not slide_path.exists():
            failures.append(f"slide{slide_num}.xml not found")
            continue
        slide_xml = slide_path.read_text(encoding="utf-8")
        rels_xml = rels_path.read_text(encoding="utf-8")

        # Auto-discover anchor if not given (uses the FIRST spec's label)
        resolved_anchor = anchor or find_anchor_for(slide_xml, specs[0][1])
        if not resolved_anchor:
            failures.append(f"slide{slide_num}: no anchor found for label {specs[0][1]!r}")
            continue

        # Assign rIds and prepare links
        links_with_rids: list[tuple[str, str]] = []
        for category, label, url, substring in specs:
            rid = f"rId{next_rid(rels_xml)}"
            rels_xml = add_hlink_rel(rels_xml, rid, url)
            links_with_rids.append((substring, rid))

        new_xml, ok, applied = split_run(slide_xml, resolved_anchor, links_with_rids, args.color)
        if not ok:
            failures.append(f"slide{slide_num} anchor not matched: {resolved_anchor[:80]!r}")
            # Roll back the rels we speculatively added
            for substring, rid in links_with_rids:
                rels_xml = re.sub(
                    rf'  <Relationship Id="{rid}" Type="{re.escape(HLINK_REL_TYPE)}"[^/]*/>\n',
                    "",
                    rels_xml,
                )
            continue

        slide_path.write_text(new_xml, encoding="utf-8")
        rels_path.write_text(rels_xml, encoding="utf-8")

        for (category, label, url, substring), (applied_substring, _) in zip(specs, links_with_rids):
            tag = "+" if applied_substring in applied else "-"
            print(f"  {tag} slide{slide_num} {category} {label} -> {url}")
            if applied_substring in applied:
                applied_rows.append((slide_num, category, label, url))

    out_path = args.out
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"# generated {date.today().isoformat()}\n")
        for row in applied_rows:
            f.write("\t".join(row) + "\n")
    print(f"\nApplied {len(applied_rows)} links. Wrote {out_path}.")

    if failures:
        print(f"\n{len(failures)} failures:", file=sys.stderr)
        for fail in failures:
            print(f"  ! {fail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
