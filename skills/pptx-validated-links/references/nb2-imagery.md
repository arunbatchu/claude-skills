# Painterly conceptual imagery (NB2 / Gemini 3 Pro Image)

Add rich painterly *atmospheric* art to a deck without destroying its teaching
value or legibility. The rule that makes this safe: **images carry mood and
metaphor only; all data, diagrams, labels, stats and hyperlinks stay as crisp
vector.** Never bake slide text into a generated image — it pixelates, can't be
edited, can't be hyperlinked, and the model garbles letters.

Model: `gemini-3-pro-image-preview` via `google-genai` (`pip install google-genai`),
key in `GEMINI_API_KEY`. ~$0.30/image, ~30s each, 16:9. Scripts: `gen_nb2_images.py`
(manifest → PNGs) and `compose_nb2.py` (PNGs → unpacked deck).

## Two image roles

| Role | Where | Treatment | Opacity |
|---|---|---|---|
| `hero` | title + section dividers | full-bleed, **opaque**, behind left-aligned text | 100% |
| `bg` | content slides | full-bleed **faint watermark** behind cards/text | `alphaModFix amt≈20000` (~12%) |

## The art-direction rules that actually matter

1. **Negative space where the text goes (heroes).** Prompt the subject onto ONE
   side and leave the other ~45% as "calm soft empty negative space (light cream
   and faint mist) reserved for a title." Then position the slide's text into that
   empty zone. Without this, text lands on busy art and needs an ugly scrim.
2. **Verify the text-zone luminance before trusting it.** Crop the left (or
   wherever text goes) 45% of each hero, average it, count dark pixels. Want
   avg > 165 and dark-pixel(<110) fraction < 12% so dark text reads. If a hero
   comes back dark on the text side, regenerate (cheaper than scrims) — see the
   PIL snippet at the bottom.
3. **Backgrounds must be "extremely soft, low-contrast, airy, mostly empty pale
   canvas with only a faint dissolving suggestion of the concept, no focal
   subject."** Say this explicitly; otherwise the model returns a vivid hero that
   fights the text even at 12% alpha.
4. **Metaphor, never literal, never text.** "Absolutely NO text, NO words, NO
   letters, NO numbers, NO charts, NO UI elements." Repeat it — the model leaks
   text otherwise. Then QA every image for leaked glyphs (a montage contact sheet
   catches the whole set in one look).
5. **Palette per brand.** Pass the brand's two colors over "a soft warm-neutral
   off-white background" so the art sits inside the deck instead of on top of it.
   Generate a separate palette set per brand (e.g. teal+amber vs maroon+gold) —
   don't recolor one set, regenerate.

## Workflow

1. **Manifest** — one JSON entry per slide: `{slide, role, slug, concept}`. The
   `concept` is a metaphor phrase ("a poised brass balance scale beside a calm
   lighthouse — trust, governance"), not the slide's literal title.
2. **Generate** both palette sets: `gen_nb2_images.py --manifest m.json
   --palette "deep teal (#0f766e) and warm amber (#d97706)" --outdir /tmp/nb2/teal`.
   Caches by slug; safe to re-run.
3. **QA-gate** — build a labeled montage (`montage *.png -tile 4x -label '%f'
   sheet.jpg`), eyeball for garbled text / off-concept / too-dark heroes,
   regenerate only the misses (delete the PNG, re-run — it's cached).
4. **Composite** onto a COPY of the unpacked deck: `compose_nb2.py --unpacked DIR
   --manifest m.json --imgdir DIR --accent HEX --num HEX --bg-alpha 20000
   --dividers dividers.json`. Heroes go in opaque; for dividers the script strips
   the deck's existing big-number/label/title shapes and re-lays the text into the
   image's negative space (left). Content slides get the faint pic.
5. **Pilot first.** Composite + render 3 slides (one title, one divider, one dense
   content) and eyeball before scaling to all 25. The negative-space and
   alpha values are the two things that go wrong; catch them on 3, not 25.
6. **Pack, render to PDF/JPG, legibility QA**, especially the densest content
   slide (faint bg must not fight small text or underlined links) and the busiest
   divider (text must not collide with the subject).

## Compositing mechanics

- Full-bleed pic: `<p:pic>` with `xfrm off=0,0 ext=9144000,5143500`, inserted
  right after `</p:grpSpPr>` so it sits BEHIND existing shapes.
- Faint watermark: add `<a:alphaModFix amt="20000"/>` inside the `<a:blip>`.
- New image relationship: append a `Relationship` with a fresh `rId` to
  `slideN.xml.rels` (compute next id as `max(existing)+1`).
- Divider text re-lay: a left-anchored textbox at ~`off x=430000 y=1500000`
  with a big soft numeral (a light tint of the accent — accent lightened ~65%),
  a small gray part-label, and the accent-colored title.
- **Strip the old divider shapes with a whitespace-tolerant regex** — unpack.py
  pretty-prints, so `<p:sp>\s*<p:nvSpPr>\s*...`; see pptx-gotchas.md §13.

## Luminance check (regenerate-or-keep, per hero)

```python
from PIL import Image
im = Image.open("hero.png").convert("L"); w,h = im.size
left = list(im.crop((0,0,int(w*0.45),h)).get_flattened_data())
avg = sum(left)/len(left); dark = sum(p<110 for p in left)/len(left)
# keep if avg>165 and dark<0.12 (dark text will read); else regenerate
```
