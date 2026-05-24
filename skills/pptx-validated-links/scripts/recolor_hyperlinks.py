"""Set the theme's hyperlink color for an unpacked PPTX.

PPTX renderers ignore the run-level <a:solidFill> when a run has <a:hlinkClick>;
they use the theme's <a:clrScheme><a:hlink> color instead. This script edits
ppt/theme/theme1.xml directly.

Usage:
    python recolor_hyperlinks.py --unpacked unpacked/ --color 7A0019 [--followed 5A0010]
"""
import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unpacked", required=True, type=Path)
    p.add_argument("--color", default="7A0019", help="Hex color for hyperlinks (no #). Default UMN maroon.")
    p.add_argument("--followed", default=None, help="Hex color for followed/visited hyperlinks. Defaults to a darker shade of --color if not given.")
    p.add_argument("--theme-file", default="theme1.xml", help="Filename under ppt/theme/ to edit (default theme1.xml)")
    args = p.parse_args()

    theme_path = args.unpacked / "ppt" / "theme" / args.theme_file
    if not theme_path.exists():
        print(f"Error: {theme_path} not found", file=sys.stderr)
        return 1

    color = args.color.lstrip("#").upper()
    followed = (args.followed or _darken(color)).lstrip("#").upper()

    text = theme_path.read_text(encoding="utf-8")
    before = text

    text, hlink_count = re.subn(
        r'(<a:hlink>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}("/>\s*</a:hlink>)',
        rf'\g<1>{color}\g<2>',
        text,
    )
    text, fol_count = re.subn(
        r'(<a:folHlink>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}("/>\s*</a:folHlink>)',
        rf'\g<1>{followed}\g<2>',
        text,
    )

    if text == before:
        print("No changes — theme already at requested colors or pattern didn't match.")
        return 0
    theme_path.write_text(text, encoding="utf-8")
    print(f"Updated {theme_path.name}: hlink -> #{color} ({hlink_count}); folHlink -> #{followed} ({fol_count})")
    return 0


def _darken(hex6: str) -> str:
    """Return a slightly darker shade (60% of each channel)."""
    r = int(hex6[0:2], 16)
    g = int(hex6[2:4], 16)
    b = int(hex6[4:6], 16)
    return f"{int(r * 0.6):02X}{int(g * 0.6):02X}{int(b * 0.6):02X}"


if __name__ == "__main__":
    sys.exit(main())
