"""Append a [LINK-DATA] paragraph block to each touched slide's speaker notes.

Reads applied_links.tsv (slide, category, label, url) and writes a machine-readable
block into the body text of the corresponding ppt/notesSlides/notesSlideN.xml.

The block is the input to build_references.py.

Note: this assumes notesSlideN.xml exists for the touched slide N. For decks
where slide-to-notes is not 1:1, edit NOTES_FILE_MAP in the source.

Usage:
    python append_link_data.py --unpacked unpacked/ --tsv applied_links.tsv
"""
import argparse
import sys
from datetime import date
from pathlib import Path


def para(text: str, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'          <a:p>\n'
        f'            <a:pPr marL="0" lvl="0" indent="0" algn="l" rtl="0"><a:buNone/></a:pPr>\n'
        f'            <a:r><a:rPr lang="en-US"{b} dirty="0"/><a:t>{safe}</a:t></a:r>\n'
        f'          </a:p>\n'
    )


# Markers indicating end of the notes body shape — varies slightly by authoring tool.
BODY_END_CANDIDATES = [
    "</p:txBody>\n      </p:sp>\n    </p:spTree>",
    "        </p:txBody>\n      </p:sp>\n    </p:spTree>",
]


def append_block(text: str, paragraphs: list[str]) -> str | None:
    block = "".join(paragraphs)
    for marker in BODY_END_CANDIDATES:
        if marker in text:
            return text.replace(marker, block + marker, 1)
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unpacked", required=True, type=Path)
    p.add_argument("--tsv", required=True, type=Path, help="applied_links.tsv from apply_links.py")
    p.add_argument("--verified-date", default=date.today().isoformat())
    p.add_argument("--notes-map", type=Path, help="Optional TSV mapping slide_num<TAB>notesSlide_filename (e.g., '87<TAB>notesSlide85.xml')")
    args = p.parse_args()

    # Read TSV; group by slide
    by_slide: dict[str, list[tuple[str, str, str]]] = {}
    for line in args.tsv.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        slide, category, label, url = parts[:4]
        by_slide.setdefault(slide, []).append((category, label, url))

    # Optional notes mapping (for decks where slide N's notes are notesSlide M)
    notes_map: dict[str, str] = {}
    if args.notes_map and args.notes_map.exists():
        for line in args.notes_map.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            slide, notes_file = line.split("\t")
            notes_map[slide] = notes_file

    notes_dir = args.unpacked / "ppt" / "notesSlides"
    failures = []
    successes = 0

    for slide_num, rows in sorted(by_slide.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        notes_filename = notes_map.get(slide_num, f"notesSlide{slide_num}.xml")
        notes_path = notes_dir / notes_filename
        if not notes_path.exists():
            failures.append(f"slide{slide_num}: {notes_path.name} not found")
            continue

        text = notes_path.read_text(encoding="utf-8")
        paragraphs = [para(f"[LINK-DATA verified={args.verified_date}]", bold=True)]
        for category, label, url in rows:
            paragraphs.append(para(f"{category} | {label} | {url}"))
        paragraphs.append(para("[/LINK-DATA]", bold=True))

        new_text = append_block(text, paragraphs)
        if new_text is None:
            failures.append(f"{notes_path.name}: body-end marker not found")
            continue

        notes_path.write_text(new_text, encoding="utf-8")
        print(f"  + {notes_path.name}: appended {len(rows)} link rows")
        successes += 1

    print(f"\nAppended LINK-DATA to {successes} notes file(s).")
    if failures:
        print(f"\n{len(failures)} failures:", file=sys.stderr)
        for fail in failures:
            print(f"  ! {fail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
