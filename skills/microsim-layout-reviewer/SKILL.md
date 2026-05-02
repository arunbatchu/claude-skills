---
name: microsim-layout-reviewer
description: Review the visual layout of a p5.js MicroSim using Claude Vision — capture a screenshot at the iframe height, inspect it for layout defects (clipped labels, overlapping controls, sliders extending past the canvas, panel content overflow, residual text strokes, low-contrast text, misaligned baselines, draw-order bugs), patch the `.js` file to fix what's wrong, and re-verify by re-capturing. Use this skill whenever the user asks to "review a MicroSim layout", "check a MicroSim for visual bugs", "fix layout issues in a sim", "QA a MicroSim screenshot", or anything similar. Also use it proactively right after generating a new MicroSim to catch layout defects before the user sees them. Trigger on phrases like "look at the screenshot", "the labels look clipped", "fix the layout", "why is that text cut off", or "review the visual" in a MicroSim context. This skill complements `microsim-iframe-tester` (which uses Playwright bounding-box checks for control visibility) by catching the *visual* defects that pixel-precise checks miss.
---

# MicroSim Layout Reviewer

## Purpose

`microsim-iframe-tester` uses Playwright to verify that every interactive
control is *positioned* inside the iframe boundary. That catches "the slider
got cut off" but it does not catch "the row label says `mpletion: false`
because the axis-offset is too small" or "the title is overlapping the JSON
panel" or "every text element has an ugly black outline because someone
forgot a `noStroke()`". Those defects are obvious to a human looking at the
sim — and obvious to Claude looking at the screenshot — but invisible to
geometric checks.

This skill is the visual-review counterpart. It captures the sim at its real
iframe height, looks at the image with intent, and patches the `.js` file
where the rendering is wrong.

## When to use

- Right after generating a new MicroSim (proactive QA)
- When the user pastes a screenshot and says "this looks off"
- When a sim's iframe height is correct but the layout still looks broken
- When a sim worked at one width and now looks wrong at another

If the issue is "controls clipped at the bottom of the iframe" only, prefer
`microsim-iframe-tester` first — it gives a precise suggested height. Use
this skill when the issue is *inside* the canvas, not at its edges.

## Workflow

### 1. Resolve the target sim

The user will give you a sim directory, a sim-id, or just say "the one I
just made". Resolve to an absolute path. The path must contain `main.html`,
`index.md`, and a `*.js` file. If multiple `.js` files exist, the one
referenced from `main.html` is the canvas script.

### 2. Read the iframe height from `index.md`

Find the line `<iframe src="main.html" height="NNNpx" ...>`. Extract `NNN`.
This is the height the sim will actually render at in the textbook, so this
is what you must screenshot at — not the tool's default height. If
`index.md` has no iframe (rare, but happens for new scaffolds), fall back to
the `// CANVAS_HEIGHT:` comment in the `.js` file plus 2.

### 3. Capture a screenshot

```bash
bk-capture-screenshot <sim-dir> 3 <iframe-height>
```

Output: `<sim-dir>/<sim-id>.png`. The script renders headless Chrome at
800px wide × the requested height, waits the delay seconds for JS to
settle, and writes a PNG.

If `bk-capture-screenshot` is not on PATH (`which bk-capture-screenshot`
returns nothing), tell the user — don't try to write your own headless
Chrome wrapper.

### 4. Read the screenshot

Use the `Read` tool on the PNG. The image is passed into context as
visual content for **Claude Vision** to analyze directly — no OCR, no
image-processing libraries. Claude Vision sees pixels the way a human
reviewer does: text legibility, color contrast, alignment, overlap,
clipping at edges. Capability tracks the model version, so when this
skill is invoked under a newer model it should produce sharper review
output without changes here. Note the active model version (e.g.
"Claude Vision (Opus 4.7)") when you write the review summary in
step 9 — the version anchors the judgment for anyone re-reading later.

### 5. Apply the visual checklist

Read `references/visual-checklist.md` and walk through every item
against the screenshot you just loaded. Don't skim — go item by item.
Claude Vision is **not deterministic**: what gets flagged depends on
what you're actively looking for. The checklist is what disciplines
review into reliable output, by forcing explicit inspection of every
known failure mode rather than a vague "does this look OK?".

For each item in the checklist, decide: **PASS**, **FAIL**, or **N/A**
(e.g., "no JSON panel exists in this sim"). Quote the specific evidence
from the image — *what you see* — for any FAIL.

### 6. Diagnose and patch

For each FAIL, consult `references/common-fixes.md`. The table maps each
visual symptom to the most likely root cause(s) in the `.js` file and the
specific edit that fixes it. Make the smallest change that resolves the
defect.

Edit only the `.js` file unless the defect is iframe-height-related (in
which case `index.md` and possibly the chapter file need updating, and
you should hand off to `fix-iframe-heights.py`).

### 7. Re-capture and verify

After every fix-patch round, re-run the screenshot and re-read it. Walk
the same checklist again. The fixes should turn FAILs into PASSes without
introducing new FAILs.

If a fix doesn't resolve the issue, *do not* keep widening it (e.g.,
ratcheting `axisOffset` from 60 → 110 → 160 → 200). Instead, stop and
think: the parameter you're tuning may not be the right lever. Re-read
the .js file around the suspect area and look for an unrelated cause.

### 8. Stop after 3 review-patch cycles

If the third re-capture still shows issues, stop and report what's left.
Continued tweaking past three cycles usually means the design has a
deeper issue that needs human judgement — better to surface that than to
quietly produce something subtly worse.

### 9. Report

Tell the user, for each sim reviewed:

- Initial defects found (one line per FAIL with quoted evidence)
- Edits applied (file:line, what changed)
- Final state (clean / partial / unfixed) with a one-sentence reason

## What this skill does *not* do

- It does not replace `microsim-iframe-tester`. If the iframe is the wrong
  height, run that first.
- It does not redesign sims. If the sim's overall layout is poorly
  conceived (e.g., 11 controls crammed into one row), this skill will
  surface the symptoms but won't propose a redesign — call that out and
  stop.
- It does not modify approved sims. If `index.md` frontmatter has
  `status: approved`, skip the sim and tell the user. Approved sims are
  locked from incidental edits.

## Reference files

- `references/visual-checklist.md` — every item to inspect, with what
  PASS/FAIL look like.
- `references/common-fixes.md` — symptom → root-cause-in-.js → edit.
  Read this when diagnosing a FAIL, not before.
