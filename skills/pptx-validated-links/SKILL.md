---
name: pptx-validated-links
description: Adds validated, clickable hyperlinks to PowerPoint decks from a TSV plan, validates every URL with HTTP HEAD/GET before insertion, appends machine-readable LINK-DATA blocks to speaker notes, and auto-builds a categorized References slide from the aggregate. Use this skill whenever the user wants to "add hyperlinks to a deck", "make terms clickable in PPTX", "validate links in a presentation", "build a references slide from links", "link acronyms to definitions", "turn glossary terms into clickable references", or otherwise wants to turn a PPTX into a self-service reference where learners click through to authoritative sources. Pairs with the anthropic-skills:pptx skill which handles unpack/pack — this skill handles the hyperlink workflow only.
---

# PPTX Validated Links

End-to-end workflow for adding **verified, clickable hyperlinks** to a PPTX deck and auto-building a categorized **References slide** from the link metadata.

## Quick start

Assume the deck has already been unpacked with `anthropic-skills:pptx`'s `unpack.py` to `unpacked/`.

```bash
# 1. Validate URLs (HEAD/GET, real browser UA, falls back to GET on 405/403)
python scripts/validate_links.py candidates.tsv

# 2. Apply hyperlinks to slides + emit applied_links.tsv
python scripts/apply_links.py --unpacked unpacked/ --plan candidates.tsv

# 3. Append [LINK-DATA] blocks to each touched slide's speaker notes
python scripts/append_link_data.py --unpacked unpacked/ --tsv applied_links.tsv

# 4. (Optional) Recolor the theme's hyperlink color — see "Why the theme fix" below
python scripts/recolor_hyperlinks.py --unpacked unpacked/ --color 7A0019

# 5. Build categorized References slide(s) at the end of the deck
python scripts/build_references.py --unpacked unpacked/ --before-slide thank-you
```

Then repack with `anthropic-skills:pptx`'s `pack.py`.

## TSV format

The `candidates.tsv` is the source of truth. Columns (tab-separated):

```
slide<TAB>category<TAB>label<TAB>url<TAB>anchor<TAB>substring
```

| column | required | meaning |
|---|---|---|
| `slide` | yes | PPTX slide number (1-based; matches `slideN.xml` after unpack) |
| `category` | yes | Grouping bucket: `acronym`, `product`, `person`, `citation`, `standard` |
| `label` | yes | Display name shown on the References slide |
| `url` | yes | Authoritative URL the link should point to |
| `anchor` | optional | The exact `<a:t>` content to find. If empty, the first run containing `label` is used. |
| `substring` | optional | Specific substring within `anchor` to wrap as the link. Defaults to `label`. |

Lines starting with `#` are comments. Blank lines are skipped.

See `assets/candidates-example.tsv` for a worked example. **Always specify `anchor`** when the same word appears in both a title and a body bullet — without it, the skill links the title (which gets an ugly 40pt underlined word).

## Workflow notes

**Build the candidates list before validating.** Read the deck text (e.g., `extract-text` from `anthropic-skills:pptx`) and identify acronyms, products, citations, and people worth linking. Decide on the authoritative URL for each. Validate before applying — link rot is cheap to catch upfront, painful to debug later.

**Anchor text must match `<a:t>` content byte-for-byte.** PPTX slide files store em-dash, en-dash, and apostrophes as either literal UTF-8 bytes OR as XML entities (`&#8212;`, `&#8211;`, `&#x2019;`) depending on the deck's authoring tool. Ampersands are *always* `&amp;`. To check what's in a slide, grep the raw `slideN.xml` rather than relying on extracted text — the extractor decodes entities silently.

**Multiple links in one anchor are fine.** Repeat the same `anchor` value across rows with different `substring` values. The applier splits the run into prefix + link + middle + link + suffix in a single pass.

## Why the theme fix matters

PPTX runs let you set `<a:solidFill>` *and* `<a:hlinkClick>` on the same run — but every renderer (LibreOffice, PowerPoint, Keynote) ignores the run-level color when a hyperlink is present and uses the theme's `<a:hlink>` color instead. Setting `srgbClr` on the run does nothing.

`recolor_hyperlinks.py` edits `ppt/theme/theme1.xml` directly — one change, all hyperlinks across the deck render in the chosen color. Default is UMN dark maroon (`7A0019`); pass `--color HEX` for anything else.

## Building the References slide

`build_references.py` reads every `[LINK-DATA verified=YYYY-MM-DD]` block out of `ppt/notesSlides/notesSlide*.xml`, dedupes by URL, groups by category, and emits one or more new slides inserted just before the deck's closing/Thank-You slide.

The script does not delete or merge existing references — only adds new ones. Re-running it produces deterministic output (sorted alphabetically within each category).

For decks with 50+ unique links, it splits Products onto a second slide automatically. For 100+, it splits into three.

## What NOT to link

Some entities will *validate* fine but shouldn't get hyperlinks:

- **Bio / credentials slides** — speaker employers, alma maters, certifications. The slide is personal context, not pedagogy. Linking turns it into a LinkedIn profile.
- **Institutional affiliations in citations** — e.g., "Emeritus Professor, Stanford University" — Stanford is biographical context for the cited person, not a pedagogical link about the topic.
- **Author affiliations in references** — same reasoning.

**Rule of thumb:** would a learner click this to deepen understanding of the *topic*, or just to satisfy curiosity about the *speaker*? If the latter, skip. Keeps the deck's clickability promise meaningful.

See [references/pptx-gotchas.md](references/pptx-gotchas.md) §11 for examples.

## Gotchas

See [references/pptx-gotchas.md](references/pptx-gotchas.md) for the non-obvious traps:

- Lazy regex `[^>]*?` for matching `<a:rPr ... />` self-closing tags
- Theme-vs-run hyperlink color override (fix at theme, not run)
- 7-file checklist for inserting a slide
- LibreOffice silently dropping slides during PDF render
- HEAD vs GET fallback for bot-blocking sites
- Anchor text must match `<a:t>` content byte-for-byte (entities vs literal Unicode)
- `<p:clrMapOvr>` closing-tag typo (use `p:` prefix, not `a:`)
- Filename casing matters — `notesSlide`, not `notesslide`
- PowerPoint silently renumbers slide files on re-save — locate by content, not filename
- Card-layout shapes need ~80,000 EMU clearance below hyperlinked term shapes

## Visual patterns library

When building new slides that need a recurring visual structure, see [references/visual-patterns.md](references/visual-patterns.md) for copy-pasteable PPTX XML snippets:

- Emoji voting cards (4 cards in a row)
- DevOps loop boxes (3 stacked boxes with down-arrows + continuous-loop indicator)
- Timeline strip (5 milestone boxes with arrows between)
- Spectrum bar with axis label (deterministic ↔ non-deterministic etc.)
- 4-quadrant grid (2x2 layout for "best practices" type slides)
- "Watch in X" yellow callout box
- 3-column MECE layout

All patterns use UMN maroon (`#7A0019`) by default; recolor by global find-replace.

## Known limitations

- **`build_references.py` slide-insertion is fragile** when the deck has been round-tripped through PowerPoint. Common failures: orphan notesSlide files from previous insertions, missing references, casing mismatches. Workaround: when these fail, rebuild the References slide by hand using the aggregator logic in `build_references.py:extract_link_data()` and `aggregate()` to pull the deduped link list, then write the slide XML directly. See `references/pptx-gotchas.md` §3 for the full 7-file insertion checklist.

## Troubleshooting

**"anchor NOT FOUND"**: The exact-string match failed. Grep the raw `slideN.xml` for the substring and copy the surrounding `<a:t>` content verbatim into the `anchor` column — paying attention to entities.

**Links render in teal, not the color I specified**: You set the color on the run instead of the theme. Run `recolor_hyperlinks.py`.

**LibreOffice PDF has fewer pages than the PPTX has slides**: LibreOffice quirk on certain layouts. Use `python -c "from pptx import Presentation; print(len(Presentation('x.pptx').slides))"` to verify the slide count and trust PowerPoint to render all of them.

**Validation fails on McKinsey / Gartner / IDC URLs**: These sites block scripted HEAD/GET. Either use a stronger primary source (e.g., Stanford HAI AI Index instead of McKinsey State of AI) or skip the link and accept manual verification.

## Bundled scripts

| script | purpose |
|---|---|
| `scripts/validate_links.py` | HEAD-then-GET URL validator |
| `scripts/apply_links.py` | Run-splitting hyperlink applier |
| `scripts/append_link_data.py` | Appends LINK-DATA notes blocks |
| `scripts/build_references.py` | Aggregates LINK-DATA → References slide(s) |
| `scripts/recolor_hyperlinks.py` | Sets theme hlink/folHlink colors |

All scripts are CLI-runnable with `--help`. Dependencies: Python 3.10+ standard library only — no `python-pptx`, no external packages. Slide XML is edited directly via regex.
