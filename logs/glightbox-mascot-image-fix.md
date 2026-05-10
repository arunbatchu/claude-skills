# GLightbox Mascot Image Fix

**Date:** 2026-05-09  
**Project:** us-history (dmccreary/us-history)  
**Plugin version:** mkdocs-glightbox 0.5.2  

---

## Problem Statement

After adding the `mkdocs-glightbox` plugin to the U.S. History intelligent
textbook, clicking on any chapter image opened a fullscreen lightbox — the
desired behavior. However, pressing the **Prev** or **Next** arrows inside the
lightbox cycled through every mascot pose image (welcome, thinking, tip,
warning, celebration, encourage) in addition to the chapter content images.
The mascot images were appearing in the sequential gallery index even though
nobody had clicked on them.

The mascot images are small 90×90 px icons embedded inside MkDocs Material
admonition blocks using this HTML pattern:

```html
<img src="../../img/mascot/welcome.png" class="mascot-admonition-img" alt="Liberty waves welcome">
```

---

## Attempt 1 — CSS `pointer-events: none` (already present, insufficient)

The `mascot.css` file already contained:

```css
.mascot-admonition-img {
  pointer-events: none;  /* prevent glightbox zoom on mascot icons */
}
```

**Why it failed:** `pointer-events: none` on an `<img>` blocks direct clicks
on that element's pixels. But the mkdocs-glightbox plugin wraps every image in
an `<a class="glightbox">` anchor tag at **build time** (in Python, during
`on_page_content`). The anchor is a separate DOM element surrounding the image.
Clicks on the anchor border — and any event bubbled up from the image — still
reach the `<a>` and fire the lightbox. More critically, the gallery index (the
sequential prev/next list) is built when the `<a>` tags are created, not when
they are clicked. `pointer-events: none` on the `<img>` does not remove an
image from a gallery that was baked into the HTML at build time.

---

## Attempt 2 — `a.glightbox:has(> .mascot-admonition-img)` CSS rule

Added to `mascot.css`:

```css
a.glightbox:has(> .mascot-admonition-img) {
  pointer-events: none;
  cursor: default;
}
```

**Why it failed:** Same root cause as Attempt 1. This rule disables the anchor
at click time, so a user cannot directly click a mascot image to open the
lightbox. But the image was already registered in GLightbox's internal gallery
array when the page was built. The gallery array is populated by the JavaScript
`GLightbox()` initializer, which finds all `<a class="glightbox">` elements in
the DOM on page load — before any click happens. Disabling `pointer-events` on
the anchor prevents direct clicks but does not remove the anchor from the DOM
and does not remove the image from the pre-built gallery array. The Prev/Next
arrows iterate over the gallery array, not over currently-clickable elements.

---

## Attempt 3 — `selector` config option in mkdocs.yml (invalid key, ignored)

Added to `mkdocs.yml`:

```yaml
plugins:
  - glightbox:
      ...
      selector: "img:not(.mascot-admonition-img)"
```

**Why it failed:** The `selector` key does not exist in the
`mkdocs-glightbox` plugin's `config_scheme`. Reading the actual plugin source
(`plugin.py`) confirmed this:

```python
config_scheme = (
    ("touchNavigation", ...),
    ("loop", ...),
    ("effect", ...),
    ("slide_effect", ...),
    ("width", ...),
    ("height", ...),
    ("zoomable", ...),
    ("draggable", ...),
    ("skip_classes", config_options.Type(list, default=[])),   # ← the real key
    ("auto_themed", ...),
    ("auto_caption", ...),
    ("caption_position", ...),
    ("background", ...),
    ("shadow", ...),
    ("manual", ...),
)
```

MkDocs silently ignores unknown plugin config keys. The `selector` value was
parsed and discarded; all images continued to be wrapped, including mascots.

The confusion arose because the GLightbox **JavaScript library** has a
`selector` option (defaulting to `.glightbox`) that controls which DOM elements
the JS initializer scans. The mkdocs-glightbox **Python plugin** does not
expose that as a config key and uses `.glightbox` unconditionally.

---

## Root Cause Analysis

The plugin processes images in two separate phases:

### Phase 1 — Python build time (`on_page_content` hook)

```python
def on_page_content(self, html, page, config, **kwargs):
    skip_classes = ["emojione", "twemoji", "gemoji", "off-glb"] + self.config["skip_classes"]
    return self.wrap_img_with_anchor_selectolax(html, ...)
```

```python
def _should_skip_img(self, img, skip_classes, ...):
    classes = img.attributes.get("class", "").split()
    if set(classes) & set(skip_classes):
        return True   # ← image is skipped entirely; no <a> is created
```

Every `<img>` whose `class` attribute intersects `skip_classes` is left alone.
Every other `<img>` is wrapped in `<a class="glightbox" href="...">`.

### Phase 2 — JavaScript runtime (`on_post_page` injects init script)

```javascript
const lightbox = GLightbox({ touchNavigation: true, loop: false, ... });
```

GLightbox scans the DOM for all `<a class="glightbox">` elements and registers
them in an internal array. Prev/Next arrows step through this array. CSS rules
applied after this point cannot remove elements from the array.

**The only correct fix is in Phase 1**: prevent the `<a class="glightbox">`
from being created for mascot images in the first place.

---

## Fix — `skip_classes` in mkdocs.yml

```yaml
plugins:
  - glightbox:
      touchNavigation: true
      loop: false
      effect: zoom
      slide_effect: slide
      width: 100%
      height: auto
      zoomable: true
      draggable: true
      auto_caption: false
      caption_position: bottom
      skip_classes:
        - mascot-admonition-img
```

With `mascot-admonition-img` in `skip_classes`, the plugin's
`_should_skip_img` method returns `True` for every mascot image. No `<a>`
anchor is created, the image is never registered in GLightbox's gallery array,
and it never appears in the Prev/Next sequence.

**Confirmed working** by the user after MkDocs rebuilt the site.

---

## Per-Image Alternative

For one-off exclusions without touching `mkdocs.yml`, the plugin natively
supports the `off-glb` CSS class:

```markdown
![Image](path.png){ .off-glb }
```

`off-glb` is hardcoded in the plugin's skip list alongside `emojione`,
`twemoji`, and `gemoji`. This works for individual images but is impractical
when a whole class of images (all mascot poses across all chapters) needs
exclusion.

---

## Files Changed

### `mkdocs.yml` (us-history project)
- Removed invalid `selector` key
- Added `skip_classes: [mascot-admonition-img]`

### `docs/css/mascot.css` (us-history project)
- Removed the `a.glightbox:has(...)` rule (no longer needed)
- Updated `pointer-events: none` comment to be accurate

### `skills/book-installer/references/mkdocs-features.md` (claude-skills)
- GLightbox section rewritten with correct config snippet
- Added explicit warning that `selector` is not a valid config key
- Added source-level explanation of the two-phase build/runtime model
- Added section on why CSS `pointer-events` cannot fix a build-time gallery index

### `skills/book-installer/references/learning-mascot.md` (claude-skills)
- Updated `pointer-events: none` CSS comment to stop implying it prevents GLightbox

### `skills/init-textbook/assets/templates/mkdocs.yml` (claude-skills)
- Commented-out glightbox block updated with full correct config including
  `skip_classes`, `auto_caption`, and `caption_position`

---

## Key Takeaways for Future Sessions

1. **Read the plugin source before guessing at config keys.** The plugin file
   is at:
   ```
   $(python3 -c "import mkdocs_glightbox; import inspect; print(inspect.getfile(mkdocs_glightbox))")
   ```
   `config_scheme` lists every valid key. Unknown keys are silently ignored by
   MkDocs — there is no warning.

2. **CSS cannot undo a build-time side effect.** The gallery index is
   constructed at build time in Python. Runtime CSS (pointer-events, display:
   none, visibility: hidden) can hide or disable elements in the browser but
   cannot remove them from a JavaScript array that was populated on page load.

3. **`skip_classes` is the correct exclusion mechanism.** It operates in Phase 1
   (Python, build time) and prevents the anchor from being created at all. It
   accepts a YAML list and is merged with the plugin's hardcoded skip list
   (`off-glb`, `emojione`, `twemoji`, `gemoji`).

4. **`off-glb` is for per-image exclusions; `skip_classes` is for whole
   categories.** When an entire CSS class of images (e.g., all mascot poses)
   needs exclusion, put the class name in `skip_classes` once in `mkdocs.yml`
   rather than adding `{ .off-glb }` to every image reference across every
   chapter file.
