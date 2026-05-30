"""Rebrand an unpacked PPTX to a different brand: color swaps, logo, attribution.

Runs IN PLACE on an unpacked deck (use anthropic-skills:pptx unpack.py first;
clean.py + pack.py after). Does three things:

1. Color find-replace across ppt/slides, ppt/slideMasters, ppt/slideLayouts,
   ppt/theme/theme1.xml. Hex is matched case-insensitively; the literal title
   color usually lives in the slideMaster, so master is included.
2. Logo swap: copy a new logo into ppt/media, repoint slide rels from the old
   logo file to it, and (optionally) resize the logo box so a wide wordmark
   fits the old logo's footprint instead of stretching.
3. Attribution text swap (e.g. a presenter line on the title slide).

Usage (the UMN-maroon -> netrii-teal example this skill was extracted from):

    python rebrand_deck.py --unpacked unpacked/ \
      --color 7A0019=0F766E --color F7EFEF=F0FDFA \
      --color EEDDDF=D6F5EE --color C9B7B9=9FD8CC \
      --color FFF8E1=FFFBEB --color C68B00=D97706 --color 8A6500=B45309 \
      --new-logo /path/to/brand-logo.png --old-logo-media image32.png \
      --old-logo-xfrm '<a:off x="8048408" y="289874"/><a:ext cx="839337" cy="461700"/>' \
      --logo-height 300000 \
      --set 'Old Presenter Line=New Presenter Line'

Notes:
 - --color is repeatable. Swap the brand-primary first; also swap any tint
   fills (a maroon-tint fill next to a new teal border looks wrong), the
   faded divider numeral, the soft index numeral, and the alert-callout trio.
 - --logo-height (EMU) + --old-logo-xfrm auto-computes the new logo box: it
   keeps the OLD logo's right edge and uses the new PNG's aspect ratio at the
   given height (so a wide wordmark sits in the corner without stretching and
   long titles still clear it). Omit --logo-height to keep the old box.
 - Run scripts/recolor_hyperlinks.py separately if you also want the THEME
   hlink color changed (renderers use the theme hlink color, not run color).
   Or just include the maroon->teal swap here — it also rewrites theme1.xml.
"""
import argparse
import re
import struct
import sys
from pathlib import Path


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read width/height from a PNG IHDR (stdlib only)."""
    with path.open("rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def apply_colors(unpacked: Path, pairs: list[tuple[str, str]]) -> int:
    targets = (list((unpacked / "ppt" / "slides").glob("slide*.xml"))
               + list((unpacked / "ppt" / "slideMasters").glob("*.xml"))
               + list((unpacked / "ppt" / "slideLayouts").glob("*.xml")))
    theme = unpacked / "ppt" / "theme" / "theme1.xml"
    if theme.exists():
        targets.append(theme)
    n = 0
    for f in targets:
        t = f.read_text(encoding="utf-8")
        nt = t
        for a, b in pairs:
            nt = nt.replace(a.upper(), b.upper()).replace(a.lower(), b.upper())
        if nt != t:
            f.write_text(nt, encoding="utf-8")
            n += 1
    return n


def swap_logo(unpacked: Path, new_logo: Path, old_media: str, media_name: str,
              old_xfrm: str | None, logo_height: int | None) -> tuple[int, int]:
    media_dir = unpacked / "ppt" / "media"
    media_dir.mkdir(exist_ok=True)
    (media_dir / media_name).write_bytes(new_logo.read_bytes())

    # repoint slide rels
    repointed = 0
    for f in (unpacked / "ppt" / "slides" / "_rels").glob("slide*.xml.rels"):
        t = f.read_text(encoding="utf-8")
        if f"../media/{old_media}" in t:
            f.write_text(t.replace(f"../media/{old_media}", f"../media/{media_name}"), encoding="utf-8")
            repointed += 1

    # resize logo box
    resized = 0
    if old_xfrm and logo_height:
        m = re.search(r'<a:off x="(\d+)" y="(\d+)"/>\s*<a:ext cx="(\d+)" cy="(\d+)"/>',
                      old_xfrm.replace("\n", " "))
        if not m:
            print("WARNING: --old-logo-xfrm did not parse; skipping resize", file=sys.stderr)
        else:
            ox, oy, ocx = int(m.group(1)), int(m.group(2)), int(m.group(3))
            right_edge = ox + ocx
            w, h = png_dimensions(new_logo)
            new_cx = round(logo_height * w / h)
            new_x = right_edge - new_cx
            new_xfrm = f'<a:off x="{new_x}" y="{oy}"/><a:ext cx="{new_cx}" cy="{logo_height}"/>'
            norm_old = re.sub(r"\s+", " ", old_xfrm).strip()
            for f in (unpacked / "ppt" / "slides").glob("slide*.xml"):
                t = f.read_text(encoding="utf-8")
                if norm_old in t:
                    f.write_text(t.replace(norm_old, new_xfrm), encoding="utf-8")
                    resized += 1
    return repointed, resized


def apply_sets(unpacked: Path, pairs: list[tuple[str, str]], all_slides: bool) -> int:
    files = sorted((unpacked / "ppt" / "slides").glob("slide*.xml"))
    if not all_slides:
        # title slide is the lowest-numbered slide referenced first in presentation;
        # default to slide with smallest number
        files = files[:1] if files else []
        # better: smallest number
        allf = sorted((unpacked / "ppt" / "slides").glob("slide*.xml"),
                      key=lambda p: int(re.match(r"slide(\d+)", p.name).group(1)))
        files = allf[:1]
    n = 0
    for f in files:
        t = f.read_text(encoding="utf-8")
        nt = t
        for a, b in pairs:
            nt = nt.replace(a, b)
        if nt != t:
            f.write_text(nt, encoding="utf-8")
            n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--unpacked", required=True, type=Path)
    p.add_argument("--color", action="append", default=[], metavar="OLD=NEW",
                   help="Hex color swap (repeatable), e.g. 7A0019=0F766E")
    p.add_argument("--new-logo", type=Path, help="Path to the replacement logo (PNG)")
    p.add_argument("--old-logo-media", default="image32.png", help="Logo filename in ppt/media to replace")
    p.add_argument("--logo-media-name", default="brand-logo.png", help="Filename for the new logo in ppt/media")
    p.add_argument("--old-logo-xfrm", help="Exact <a:off/><a:ext/> string of the old logo box (for resize)")
    p.add_argument("--logo-height", type=int, help="Target logo height in EMU; width auto from PNG aspect, right-aligned")
    p.add_argument("--set", action="append", default=[], metavar="OLD=NEW",
                   help="Text replacement (repeatable); default applies to title slide only")
    p.add_argument("--set-all-slides", action="store_true", help="Apply --set across all slides, not just title")
    args = p.parse_args()

    def parse_pairs(items):
        out = []
        for it in items:
            if "=" not in it:
                print(f"Bad pair (need OLD=NEW): {it}", file=sys.stderr); sys.exit(2)
            a, b = it.split("=", 1)
            out.append((a, b))
        return out

    colors = parse_pairs(args.color)
    sets = parse_pairs(args.set)

    if colors:
        n = apply_colors(args.unpacked, colors)
        print(f"Recolored {n} files ({len(colors)} swaps)")
    if args.new_logo:
        rep, res = swap_logo(args.unpacked, args.new_logo, args.old_logo_media,
                             args.logo_media_name, args.old_logo_xfrm, args.logo_height)
        print(f"Logo: repointed {rep} slide rels, resized {res} logo boxes")
        print(f"  (old media '{args.old_logo_media}' is now orphaned — clean.py will remove it)")
    if sets:
        n = apply_sets(args.unpacked, sets, args.set_all_slides)
        print(f"Text swaps applied to {n} slide(s)")
    print("Done. Next: clean.py then pack.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
