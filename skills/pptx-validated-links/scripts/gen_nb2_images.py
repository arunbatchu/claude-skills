#!/usr/bin/env python3
"""Generate per-slide painterly conceptual images for a deck (Gemini 3 Pro Image / NB2).

Reads a manifest JSON (list of {slide, role, slug, concept}) and emits one PNG per
entry into --outdir, named <slug>.png. Caches: skips slugs whose PNG already exists,
so a re-run only fills gaps (delete a PNG to force regeneration of just that one).

role "hero"  -> subject pushed to one side, opposite ~45% left as empty negative
                space for a title (for full-bleed opaque art behind divider/title text).
role "bg"    -> extremely soft, low-contrast, airy faint watermark (for behind content).

Requires: google-genai  (pip install google-genai)  and  GEMINI_API_KEY in env.
See references/nb2-imagery.md for the art-direction rationale.

Usage:
  gen_nb2_images.py --manifest m.json \
      --palette "deep teal (#0f766e) and warm amber (#d97706)" \
      --outdir /tmp/nb2/teal [--model gemini-3-pro-image-preview] [--text-side left]

Manifest entry example:
  {"slide": 4, "role": "hero", "slug": "div-what",
   "concept": "a glowing geometric mind of gears seen through a brass magnifying lens"}
"""
import argparse, json, os, sys, time
from pathlib import Path

DEFAULT_MODEL = "gemini-3-pro-image-preview"

BASE = ("Rich painterly conceptual editorial illustration for a premium business keynote. "
        "Sophisticated, modern, metaphorical (never literal). {palette} palette over a soft "
        "warm-neutral off-white background. Painterly brushwork, subtle canvas texture, tasteful "
        "directional light, depth and atmosphere. Absolutely NO text, NO words, NO letters, NO "
        "numbers, NO charts, NO UI elements. Cinematic 16:9 widescreen.")
HERO = (" The subject sits entirely on the {far} side of the frame; the {near} ~45 percent is calm "
        "soft empty negative space (light cream and faint mist) reserved for a title. CONCEPT: ")
BG = (" Render this EXTREMELY SOFT, light, low-contrast and airy — mostly empty pale canvas with "
      "only a faint dissolving suggestion of the concept, no focal subject, designed to sit faintly "
      "BEHIND text without competing. CONCEPT: ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, type=Path, help="JSON list of {slide,role,slug,concept}")
    ap.add_argument("--palette", required=True, help='e.g. "deep teal (#0f766e) and warm amber (#d97706)"')
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--text-side", default="left", choices=["left", "right"],
                    help="which side heroes reserve for text (default left)")
    a = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr); return 1
    try:
        from google import genai
    except ImportError:
        print("ERROR: pip install google-genai", file=sys.stderr); return 1
    try:
        items = json.loads(a.manifest.read_text())
    except Exception as e:
        print(f"ERROR: cannot read manifest {a.manifest}: {e}", file=sys.stderr); return 1
    if not isinstance(items, list) or not items:
        print("ERROR: manifest must be a non-empty JSON list", file=sys.stderr); return 1

    near = a.text_side
    far = "right" if near == "left" else "left"
    a.outdir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=key)
    base = BASE.format(palette=a.palette)
    ok = 0
    for it in items:
        slug, role, concept = it.get("slug"), it.get("role", "bg"), it.get("concept", "")
        if not slug:
            print("  skip: entry without slug", file=sys.stderr); continue
        out = a.outdir / f"{slug}.png"
        if out.exists():
            print(f"  cached {slug}"); ok += 1; continue
        suffix = HERO.format(near=near, far=far) if role == "hero" else BG
        prompt = base + suffix + concept + "."
        try:
            resp = client.models.generate_content(model=a.model, contents=prompt)
            saved = False
            for c in resp.candidates or []:
                for part in (c.content.parts or []):
                    d = getattr(part, "inline_data", None)
                    if d and d.data:
                        out.write_bytes(d.data); saved = True; break
                if saved:
                    break
            if saved:
                ok += 1; print(f"  OK   {slug} (slide {it.get('slide','?')})", flush=True)
            else:
                # surface any refusal/explanation text
                msg = ""
                for c in resp.candidates or []:
                    for part in (c.content.parts or []):
                        if getattr(part, "text", None):
                            msg = part.text[:160]
                print(f"  MISS {slug}: no image. {msg}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"  ERR  {slug}: {type(e).__name__} {e}", file=sys.stderr, flush=True)
            time.sleep(3)
    print(f"DONE: {ok}/{len(items)} images in {a.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
