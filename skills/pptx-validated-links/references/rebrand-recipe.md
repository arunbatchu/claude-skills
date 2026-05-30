# Rebranding a deck to a different brand

Take an existing deck and produce a same-content copy in another brand's colors, logo, and attribution. Used to spin a UMN-maroon teaching deck into a netrii-teal copy; generalizes to any brand swap.

Tooling: `scripts/rebrand_deck.py` does the mechanical work; `anthropic-skills:pptx` handles unpack/pack.

## Why it's a find-replace (mostly)

A deck's accent color usually lives as a **literal hex** (`srgbClr val="..."`) in three places, all of which `rebrand_deck.py` rewrites:

1. **Slides** — your content runs, card borders, headers, callouts, links.
2. **slideMaster / slideLayouts** — the *title* color is inherited from the master's title style, so the master must be swapped or titles stay the old color.
3. **theme1.xml** — the `<a:hlink>` color (renderers use this for hyperlinks, not the run color — see gotcha §2).

## Steps

1. Unpack the source deck (`unpack.py`).
2. Run `rebrand_deck.py` with the color map, logo, and attribution (see below).
3. `clean.py` (removes the orphaned old logo) → `pack.py`.
4. Render to PDF and eyeball — especially titles near the logo and any tint-fill/border combos.

## The color map — swap MORE than just the primary

Swapping only the primary leaves clashes. Map each role:

| Role | Example (UMN→netrii) |
|---|---|
| Brand primary (titles, links, borders, headers) | `7A0019` → `0F766E` |
| Tint fill (card/box backgrounds) | `F7EFEF` → `F0FDFA` |
| Faded divider numeral | `EEDDDF` → `D6F5EE` |
| Soft index numeral | `C9B7B9` → `9FD8CC` |
| Alert callout fill / border / text | `FFF8E1`→`FFFBEB`, `C68B00`→`D97706`, `8A6500`→`B45309` |

A teal border around a maroon-tint fill looks wrong — always swap the tint with the primary.

## Logo swap (avoid the stretch)

A new logo rarely matches the old one's aspect ratio. If you just overwrite the file, it stretches to the old box. Instead:

- `--new-logo` + `--old-logo-media image32.png` copies the new PNG into `ppt/media` and repoints the slide rels.
- `--old-logo-xfrm '<a:off .../><a:ext .../>'` + `--logo-height EMU` resizes the box: it keeps the **old logo's right edge**, reads the new PNG's aspect ratio, and sets width from the given height. This fits a wide wordmark into the corner footprint so long titles still clear it.
- A wide wordmark wants a smaller height than a square mark (the netrii wordmark used `cy=300000` vs the UMN M's `461700`).

## Attribution

`--set 'Old presenter line=New presenter line'` (defaults to the title slide only). E.g. drop a co-presenter and append the brand: `Arun Batchu · David H. Nguyen, PhD` → `Arun Batchu · netrii`.

## Worked example (the netrii regen)

```bash
python scripts/rebrand_deck.py --unpacked unpacked/ \
  --color 7A0019=0F766E --color F7EFEF=F0FDFA \
  --color EEDDDF=D6F5EE --color C9B7B9=9FD8CC \
  --color FFF8E1=FFFBEB --color C68B00=D97706 --color 8A6500=B45309 \
  --new-logo /path/to/netrii-logo-transparent.png --old-logo-media image32.png \
  --logo-media-name netrii-logo.png \
  --old-logo-xfrm '<a:off x="8048408" y="289874"/><a:ext cx="839337" cy="461700"/>' \
  --logo-height 300000 \
  --set 'Arun Batchu  ·  David H. Nguyen, PhD=Arun Batchu  ·  netrii'
# then: clean.py unpacked/  &&  pack.py unpacked/ out.pptx --original source.pptx
```

## Keeping a deck non-public

If the rebrand is internal-only: put it in a **private** repo, and in a Next.js/static-site repo keep it OUT of `public/` (web-served) — a `private/` folder is git-tracked but not served. Both conditions together = not public.
