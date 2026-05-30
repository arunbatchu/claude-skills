# PPTX Hyperlink Gotchas

Real traps encountered while building this skill. Each cost a debugging cycle.

## 1. The run-split regex must use lazy `[^>]*?`

When matching a PPTX run like:

```xml
<a:r>
  <a:rPr lang="en" sz="1400"/>
  <a:t>– Figma AI, v0, Galileo, Uizard</a:t>
</a:r>
```

The intuitive regex fails:

```python
# WRONG — silently skips runs with self-closing rPr
RUN_RE = re.compile(
    r'<a:r>\s*(<a:rPr[^>]*(?:/>|>.*?</a:rPr>))?\s*<a:t[^>]*>([^<]*)</a:t>\s*</a:r>',
    re.DOTALL,
)
```

Why: greedy `[^>]*` consumes the `/` in `/>`. Then the `(?:/>|>.*?</a:rPr>)` alternation can't match `/>` (the cursor is past it), falls through to `>.*?</a:rPr>`, and scans forward into the next runs hunting for `</a:rPr>` — which doesn't exist in self-closing-rPr runs. The optional capture group fails, the regex skips the run silently.

The correct form uses **lazy** `[^>]*?`:

```python
RUN_RE = re.compile(
    r'<a:r>\s*(<a:rPr\b[^>]*?(?:/>|>.*?</a:rPr>))?\s*<a:t(?:\s[^>]*)?>([^<]*)</a:t>\s*</a:r>',
    re.DOTALL,
)
```

The lazy quantifier stops just before `/`, so `/>` matches first. Backtracking still tries the long form for runs with body content.

## 2. Hyperlink color override at the run level is ignored

This run XML *looks* like it should render the link in dark maroon:

```xml
<a:r>
  <a:rPr u="sng">
    <a:solidFill><a:srgbClr val="7A0019"/></a:solidFill>
    <a:hlinkClick r:id="rId4"/>
  </a:rPr>
  <a:t>Figma AI</a:t>
</a:r>
```

But LibreOffice, PowerPoint, and Keynote all render it in the **theme's** `<a:hlink>` color, not the maroon you specified. The OOXML spec says the run-level color should win; renderers disagree.

The only reliable fix is to edit the theme:

```xml
<!-- ppt/theme/theme1.xml -->
<a:clrScheme name="Office">
  ...
  <a:hlink><a:srgbClr val="7A0019"/></a:hlink>
  <a:folHlink><a:srgbClr val="5A0010"/></a:folHlink>
</a:clrScheme>
```

One edit, every hyperlink across the deck recolors. `recolor_hyperlinks.py` handles this.

## 3. Inserting a new slide = 7 files to touch

Miss any one and PowerPoint either drops the slide silently or refuses to open the file:

1. `ppt/slides/slideX.xml` — new slide content (X = next free number)
2. `ppt/slides/_rels/slideX.xml.rels` — relationships to layout, notesSlide, images
3. `ppt/notesSlides/notesSlideX.xml` — speaker notes (or reuse an existing one)
4. `ppt/notesSlides/_rels/notesSlideX.xml.rels` — back-link to the slide + notesMaster
5. `[Content_Types].xml` — two new `<Override>` entries (slide + notesSlide)
6. `ppt/_rels/presentation.xml.rels` — new `<Relationship>` rId for the slide
7. `ppt/presentation.xml` `<p:sldIdLst>` — new `<p:sldId id="..." r:id="..."/>` at the desired position; `id` must be unique across the deck

LibreOffice is lenient about missing `[Content_Types].xml` entries — PowerPoint is not.

## 4. LibreOffice can silently drop slides during PDF render

`soffice --convert-to pdf` may produce a PDF with fewer pages than the PPTX has slides. Some layouts (especially decks with embedded video, certain SmartArt, or specific font references) cause LO to skip the slide entirely.

When the rendered output looks wrong, verify the slide count from the PPTX directly:

```python
from pptx import Presentation
print(len(Presentation("x.pptx").slides))
```

If that count is higher than `pdfinfo output.pdf | grep Pages`, you've hit the LO quirk. PowerPoint itself renders all the slides correctly. Don't chase it as a bug in your output.

## 5. URL validation: scripted HEAD/GET is blocked by some sites

Enterprise consultancies (McKinsey, Gartner, IDC) block scripted access regardless of `User-Agent`. The connection times out cleanly. The validator can't distinguish "URL is dead" from "site blocks bots."

Two strategies:
- **Substitute the source.** For "AI adoption stats," use Stanford HAI's AI Index Report instead of McKinsey's. Free, more comprehensive, passes validation.
- **Fall back to manual verification.** Skip auto-validation for known-blocked domains; have a human open the URL once and mark it verified in the TSV.

Don't silently skip failures — surface them so a human decides.

## 6. Anchor text must match `<a:t>` content byte-for-byte

The slide XML may store em-dash and en-dash as either literal UTF-8 bytes (`—`, `–`) or as XML entities (`&#8212;`, `&#8211;`). Same for apostrophes (`'` vs `&#x2019;`). Different authoring tools produce different output.

Check the actual file:

```bash
grep -c '&#8212;\|&#8211;' unpacked/ppt/slides/slide12.xml
# 0 = literal Unicode; nonzero = entities
```

The anchor string in your TSV must match exactly what's in the file. Ampersands are *always* `&amp;` in the XML, regardless of source tool — your anchor string for "R&D" should be `R&amp;D` if you're matching literal XML bytes.

## 7. Closing-tag typo: `</p:clrMapOvr>` not `</a:clrMapOvr>`

When generating new slide XML, the closing tag for `<p:clrMapOvr>` must use the `p:` namespace prefix, not `a:`. The opening tag is `<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>` — note the inner element is `a:` but the wrapper closes with `p:`. Easy to copy-paste wrong.

Symptom: pack.py validation fails with `Opening and ending tag mismatch: clrMapOvr line N and clrMapOvr, line N`. The repair output also misleadingly counts hundreds of "auto-repairs" but still aborts.

**How to apply:** in every freshly-generated slide XML, sanity-check that both `<p:clrMapOvr>` and `</p:clrMapOvr>` use the `p:` prefix. Same pattern for notesSlide XML.

## 8. Filename casing: `notesSlide` not `notesslide`

PPTX filenames are case-sensitive in the OOXML spec, and `pack.py` validates that referenced files exist with the exact case used in rels. The convention is camelCase: `notesSlide1.xml`, not `notesslide1.xml`.

Symptom: `Unreferenced file: ppt/notesSlides/notesslide93.xml` even though the file exists — because the slide's rels file references `notesSlide93.xml` (correct case), and the lowercase file is now an orphan.

**How to apply:** when scripting filename generation, use exact case `notesSlide{N}.xml` to match the established convention. If your script uses `f"notes{slide_filename}"` and `slide_filename = "slide93.xml"` you'll silently get `notesslide93.xml`. Use `f"notesSlide{N}.xml"` instead.

## 9. PowerPoint silently renumbers slide files on re-save

When a user opens a deck in PowerPoint and re-saves it (even without making changes), PowerPoint may reorganize the slide-file naming. A slide you created as `slide89.xml` at display position 45 might come back as `slide32.xml` after the user round-trips through PowerPoint. The sldIdLst ordering is preserved (display order is stable), but the filename → content mapping is not.

**How to apply:**
- **Never assume slide-file names are stable across PowerPoint round-trips.** When the user has been editing in PowerPoint between your sessions, locate slides by content (grep for distinctive text), not by file number.
- Use this pattern:
  ```bash
  grep -l "distinctive slide title" unpacked/ppt/slides/slide*.xml
  ```
- Cross-check with `python-pptx`:
  ```python
  from pptx import Presentation
  prs = Presentation('deck.pptx')
  for i, s in enumerate(prs.slides, 1):
      for sh in s.shapes:
          if sh.has_text_frame and 'My Slide' in sh.text_frame.text:
              print(f"position {i}, file = ?")
              break
  ```
- The display position (1-based index in `prs.slides`) IS stable across round-trips. The XML filename is not.

## 10. Card-layout shapes need clearance below hyperlinked term shapes

When a slide uses small per-card shapes (e.g., a glossary where each term is its own ~190,000 EMU tall shape, with a separate description shape directly below), adding `u="sng"` underline to the term causes the underline to render *outside* the term shape and overlap the description shape's first line of text — even though the text content technically fits inside its own shape.

This is because the underline character is drawn just below the text baseline, and on small shapes with no autofit, the baseline + underline extends past the shape's `cy` value.

**Symptom:** in the rendered slide, the hyperlink underline visually cuts through the description text. Looks like a layout bug but is actually a font-rendering edge case.

**How to apply:** when adding hyperlinks to short card-layout slides, shift each description shape's `y` coordinate down by ~80,000 EMU (~0.08") to give the underline clearance. Pattern:

```python
pattern = re.compile(r'(<a:off x="\d+" y=)"(\d+)"(/>\s*<a:ext cx="\d+" cy="DESCRIPTION_HEIGHT"/>)')
def shift_y(m):
    return f'{m.group(1)}"{int(m.group(2)) + 80000}"{m.group(3)}'
new_text = pattern.sub(shift_y, slide_xml)
```

Use a `cy` value that's unique to description shapes to avoid shifting unrelated shapes.

## 11. Bio / institutional-affiliation entities don't get hyperlinks

Even when an entity name (employer, school, founder role, citation-context institution) appears in a slide and validates fine, don't add a hyperlink unless the link helps the learner *understand the topic*.

**Examples to skip:**
- Speaker bio slides: links to past employers, alma maters, certifications
- Citation context: "Emeritus Professor, Stanford University" — Stanford is biographical context for McCarthy, not a pedagogical link about AI
- Author affiliations in references

**Examples to keep:**
- Acronym glossaries linked to definitional sources
- Product/tool mentions in use-case context
- Citations of guidance documents, papers, regulatory bodies
- People whose work IS the topic (link John McCarthy when teaching AI history)

**Rule of thumb:** "would a learner click this to deepen understanding of the *topic*, or just to satisfy curiosity about the *speaker*?" If the latter, skip — keeps the deck's clickability promise meaningful.

## 12. Double `<?xml?>` declaration when a helper double-wraps a slide

When generating slides with helper functions, a `slide_xml(body)` wrapper that
prepends `<?xml ...?>` + `<p:sld>` must receive the BODY shapes — not an already-
wrapped slide. A divider helper that returns `slide_xml(...)` and is then passed
to a `write_slide(num, body)` that calls `slide_xml(body)` AGAIN produces two XML
declarations:

  ppt/slides/slideN.xml: Line 6: XML declaration allowed only at the start of the document

**How to apply:** decide one layer owns the wrap. Helpers that compose a slide
should return BODY shapes (a string of `<p:sp>`/`<p:pic>`); the single writer wraps
once with `slide_xml()`. Audit any helper whose name implies a full slide
("divider_slide", "title_slide") — it likely already wraps; don't wrap it again.
