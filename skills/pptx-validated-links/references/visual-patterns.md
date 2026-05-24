# PPTX Visual Patterns Library

Copy-pasteable PPTX XML snippets for recurring visual structures. All assume a 16:9 slide (9,144,000 × 5,143,500 EMU).

These are real building blocks shipped in production decks; each pattern has been visually verified in LibreOffice and PowerPoint.

## Brand colors are placeholders

All snippets use `#7A0019` as the working example for the brand-primary color (it happens to be UMN maroon from the deck these patterns were extracted from). **Substitute your own brand color via global find-replace before shipping.**

| Placeholder role | Example value used in snippets | Where it appears |
|---|---|---|
| `BRAND_PRIMARY` | `#7A0019` | Headings, hyperlinks, card borders, callout text |
| `BRAND_PRIMARY_TINT` | `#F7EFEF` | Card fills (very light tint of `BRAND_PRIMARY`) |
| `ALERT_FILL` | `#FFF8E1` | Yellow "watch this" callout background |
| `ALERT_BORDER` | `#C68B00` | Yellow callout border |
| `ALERT_TEXT` | `#8A6500` | Yellow callout heading text |
| `MUTED_GRAY` | `#999999` | Directional arrows |
| `SUBTITLE_GRAY` | `#555555` | Italic taglines / subtitles |
| `BODY_GRAY` | `#333333` | Body text in cards |

For your brand: pick `BRAND_PRIMARY`, then derive `BRAND_PRIMARY_TINT` as ~10% mix with white. The alert palette can stay neutral yellow regardless of brand.

## Common conventions

- **Card shape**: `roundRect` with `adj fmla="val 12000-25000"` for corner radius, `ln w="12700"` for border weight.
- **Common slide layout grid** (after title at y=350000):
  - Body starts ~y=950000–1100000
  - Body ends before y=4700000 (leave room for footer)
  - Margins: x=311700 left/right (~0.32")
  - Available width: 8,520,600 EMU (~8.88")

## 1. Emoji voting card

Use case: poll questions, sentiment selection, quick room-engagement moments.

Pattern: 4 rounded rectangles in a row, each with a large emoji on top and a bold maroon label below.

```xml
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Vote Card"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{X}" y="2550000"/><a:ext cx="1900000" cy="1400000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 12000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="F7EFEF"/></a:solidFill>
    <a:ln w="15875"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="ctr"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="ctr"><a:spcBef><a:spcPts val="0"/></a:spcBef><a:spcAft><a:spcPts val="200"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="4400"/><a:t>{EMOJI_HEX_ENTITY}</a:t></a:r>
    </a:p>
    <a:p>
      <a:pPr algn="ctr"><a:spcBef><a:spcPts val="0"/></a:spcBef><a:spcAft><a:spcPts val="0"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1600" b="1"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:rPr><a:t>{LABEL}</a:t></a:r>
    </a:p>
  </p:txBody>
</p:sp>
```

Layout: 4 cards × 1,900,000 wide + 3 gaps × 307,000 = 8,520,600 (fits inside slide margins). Position from `X = 311700 + i * (1900000 + 307000)` for `i in [0, 3]`.

Emoji as XML entity: `&#x1F615;` (confused), `&#x1F928;` (skeptical), `&#x1F914;` (curious), `&#x1F929;` (excited), `&#x270B;` (raised hand), `&#x1F9E0;` (brain), `&#x1F525;` (fire).

## 2. DevOps loop / 3-box stacked process

Use case: SDLC stages, lifecycle process, sequential phases. Three stacked rounded rectangles connected by down-arrows, with a "continuous loop" indicator below.

```xml
<!-- Box -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="LoopBox"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="411700" y="{Y}"/><a:ext cx="3800000" cy="540000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 25000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="F7EFEF"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1300" b="1"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:rPr><a:t>{HEADER}</a:t></a:r>
      <a:r><a:rPr lang="en" sz="1200"/><a:t>   {STAGES}</a:t></a:r>
    </a:p>
  </p:txBody>
</p:sp>

<!-- Down-arrow between boxes -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Arrow"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="2200000" y="{Y}"/><a:ext cx="200000" cy="160000"/></a:xfrm>
    <a:prstGeom prst="downArrow"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="999999"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>

<!-- Continuous loop indicator at bottom -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="LoopLabel"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="1100000" y="{Y_BOTTOM}"/><a:ext cx="2400000" cy="280000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
  <p:txBody>
    <a:bodyPr wrap="none"><a:spAutoFit/></a:bodyPr>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"><a:buNone/></a:pPr><a:r><a:rPr lang="en" sz="1100" i="1"><a:solidFill><a:srgbClr val="666666"/></a:solidFill></a:rPr><a:t>↻  continuous loop — DevOps cycle</a:t></a:r></a:p>
  </p:txBody>
</p:sp>
```

Layout: box at y=1900000, arrow at y=2480000, box at y=2680000, arrow at y=3260000, box at y=3460000, loop label at y=4060000.

## 3. Horizontal timeline strip (5 milestones with arrows)

Use case: timelines, sequential events, milestone progression. Five connected boxes in a horizontal row with right-arrows between.

```xml
<!-- Milestone box -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Milestone"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{X}" y="1300000"/><a:ext cx="1600000" cy="2100000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 10000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="F7EFEF"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"><a:spcAft><a:spcPts val="300"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1300" b="1"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:rPr><a:t>{DATE}</a:t></a:r>
    </a:p>
    <a:p><a:pPr algn="ctr"><a:spcAft><a:spcPts val="300"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1400" b="1"/><a:t>{TITLE}</a:t></a:r>
    </a:p>
    <a:p><a:pPr algn="ctr"><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1000"><a:solidFill><a:srgbClr val="333333"/></a:solidFill></a:rPr><a:t>{BLURB}</a:t></a:r>
    </a:p>
  </p:txBody>
</p:sp>

<!-- Right-arrow between boxes -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Arr"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{X}" y="2280000"/><a:ext cx="100000" cy="170000"/></a:xfrm>
    <a:prstGeom prst="rightArrow"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="999999"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>
```

Layout math: 5 boxes × 1,600,000 wide + 4 gaps × 130,000 = 8,520,000 (fits in 8,520,600). Place boxes at `X = 311700 + i * (1600000 + 130000)` for `i in [0, 4]`. Arrows go in the gaps.

## 4. Spectrum bar with axis label

Use case: continuum visualization (deterministic ↔ non-deterministic, simple ↔ complex, etc.). Same row of boxes as the timeline, plus an axis label below.

Use the timeline-strip pattern above, then add:

```xml
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="AxisLabel"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="311700" y="2750000"/><a:ext cx="8520600" cy="320000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
  <p:txBody>
    <a:bodyPr wrap="none"><a:spAutoFit/></a:bodyPr>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"><a:buNone/></a:pPr><a:r><a:rPr lang="en" sz="1200" i="1"><a:solidFill><a:srgbClr val="555555"/></a:solidFill></a:rPr><a:t>{LEFT_LABEL}  ←——————————————→  {RIGHT_LABEL}</a:t></a:r></a:p>
  </p:txBody>
</p:sp>
```

For shorter spectrum cards (no blurb), set milestone `cy=650000` and the axis label `y=2750000`.

## 5. 4-quadrant grid

Use case: "best practices" type slides with 4 distinct dimensions, "Eisenhower matrix" style breakdowns. 2x2 grid of text boxes (no fill, just bold headers + bullets).

```xml
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Quadrant"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{X}" y="{Y}"/><a:ext cx="4200000" cy="1700000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
  </p:spPr>
  <p:txBody>
    <a:bodyPr spcFirstLastPara="1" wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="t"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:pPr><a:spcAft><a:spcPts val="400"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1500" b="1"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:rPr><a:t>{HEADER}</a:t></a:r>
    </a:p>
    <!-- bullets follow as <a:p> entries -->
  </p:txBody>
</p:sp>
```

Layout grid:
- Top row: `Y = 1280000`, height 1700000
- Bottom row: `Y = 3080000`, height 1700000 (gap of 100000 between rows)
- Left col: `X = 311700`, width 4200000
- Right col: `X = 4632400`, width 4200000

Add a tagline above the grid at `y=930000, cy=300000` (italic gray, sz=1300).

## 6. "Watch in X" yellow callout

Use case: forward-looking framing, "what to watch" lists, supplementary notes that need attention but aren't the main content.

```xml
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Watch Callout"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="311700" y="{Y}"/><a:ext cx="8520600" cy="{CY}"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 8000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="FFF8E1"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="C68B00"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="91425" tIns="91425" rIns="91425" bIns="91425" anchor="t"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:pPr><a:spcAft><a:spcPts val="300"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1400" b="1"><a:solidFill><a:srgbClr val="8A6500"/></a:solidFill></a:rPr><a:t>Watch in {YEAR_OR_TOPIC}</a:t></a:r>
    </a:p>
    <!-- bullets follow -->
  </p:txBody>
</p:sp>
```

Common heights: `cy=430000` for 1-line callout, `cy=1050000` for 3-bullet callout.

## 7. 3-column MECE layout

Use case: showing 3 mutually-exclusive collectively-exhaustive buckets (e.g., Patient / Clinician / Enterprise; UX / Dev / Integration). Used heavily for the agent spectrum and "where AI shows up" slides.

```xml
<!-- One column shape, repeated 3x -->
<p:sp>
  <p:nvSpPr><p:cNvPr id="{ID}" name="Col"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{X}" y="1100000"/><a:ext cx="2750000" cy="3600000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"><a:noAutofit/></a:bodyPr>
    <a:lstStyle/>
    <a:p>
      <a:pPr><a:spcAft><a:spcPts val="700"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1600" b="1"><a:solidFill><a:srgbClr val="7A0019"/></a:solidFill></a:rPr><a:t>{BUCKET_NAME}</a:t></a:r>
    </a:p>
    <!-- 2-3 items per bucket, each as a paragraph -->
    <a:p>
      <a:pPr><a:spcAft><a:spcPts val="600"/></a:spcAft><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1200" b="1"/><a:t>{ITEM_LABEL}</a:t></a:r>
      <a:br><a:rPr lang="en" sz="1200"/></a:br>
      <a:r><a:rPr lang="en" sz="1100"/><a:t>{ITEM_DESC}</a:t></a:r>
    </a:p>
    <!-- optional autonomy/note at bottom -->
    <a:p>
      <a:pPr><a:spcBef><a:spcPts val="600"/></a:spcBef><a:buNone/></a:pPr>
      <a:r><a:rPr lang="en" sz="1000" i="1"><a:solidFill><a:srgbClr val="666666"/></a:solidFill></a:rPr><a:t>Note: {AUTONOMY_OR_FOOTNOTE}</a:t></a:r>
    </a:p>
  </p:txBody>
</p:sp>
```

Layout math: 3 cols × 2,750,000 wide. Place at `X = 311700, 3211700, 6111700` (small gaps between).

## Patterns I'd add next

If you build more decks and notice recurring layouts, add them here. Candidates I see coming:

- **2-column comparison table** (used for MCP vs A2A — could be generalized)
- **Stat callout** (big number, small label — for "1,200+ FDA-authorized devices" type emphasis)
- **Quote slide** (single big quote, attribution below)
- **Section divider with image overlay** (for chapter breaks)

When adding a pattern: include the use case, the XML snippet with `{PLACEHOLDERS}`, and layout math (positions, sizes, gaps).
