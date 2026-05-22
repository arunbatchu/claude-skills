# Social Media Preview Hook

Install an MkDocs hook that emits Open Graph and Twitter Card meta tags
(`og:title`, `og:description`, `og:image`, `twitter:*`) on every page —
without requiring Cairo / `mkdocs-material[imaging]`.

## When to Use This Reference

Use this guide when the user asks for any of:

- "social media preview", "social card", "social meta tags"
- "og:image", "og:title", "og:description", "Open Graph"
- "Twitter Card", "Twitter image"
- "LinkedIn preview", "Facebook preview", "Slack unfurl"
- A failing `bk-check-social-cover` run

This is the **default** social-preview approach for intelligent textbooks.
The full `social` plugin (`mkdocs-material[imaging]`) auto-generates card
images per page, but it requires Cairo, which most macOS/Linux dev
environments don't have installed. The hook approach below has no system
dependencies and works on every install of `mkdocs-material`.

## Prerequisites

- Existing MkDocs Material project with `site_url:` set in `mkdocs.yml`
- `docs/index.md` with `title:` and `description:` frontmatter (typically
  already installed via `home-page-template.md`)
- A cover image at `docs/img/cover.png`. **The basename MUST be `cover.png`** —
  the verifier (`~/.local/bin/bk-check-social-cover`) hard-fails on any other
  filename. Resize/rename existing covers if needed.

## What This Installs

| File | Purpose |
|------|---------|
| `plugins/social_override.py` | Hook that injects/replaces og:* and twitter:* meta tags |
| `mkdocs.yml` (edited) | Adds a top-level `hooks:` entry loading the file above |

The hook is loaded via MkDocs' `hooks:` config option, **not** as a plugin.
This avoids name collisions with other projects that also have a top-level
`plugins/` directory or `social_override` package.

## Installation Workflow

### Step 1: Create the Hook File

Create `plugins/social_override.py` at the project root (NOT under `docs/`).
Use exactly this content:

```python
"""MkDocs hook that injects Open Graph and Twitter Card meta tags into
every rendered page using the page's frontmatter.

Loaded via the `hooks:` entry in mkdocs.yml, not as a plugin -- this
avoids collisions with other projects that also install a package
called `social_override` or a top-level module called `plugins`.

Frontmatter fields read (per page):
    title         -- falls back to the H1/page.title
    description   -- falls back to site_description
    image         -- path under docs/ (e.g. img/cover.png); falls back to
                     site-wide default `img/cover.png`

The hook emits absolute URLs by joining `site_url` with the image path,
so the og:image / twitter:image tags work for crawlers and the
bk-check-social-cover verifier (which HEAD-requests the image URL).

If the social plugin (mkdocs-material[imaging]) is enabled, this hook
also replaces its auto-generated /assets/images/social/ tags with the
declared cover image.
"""

import re

DEFAULT_IMAGE = "img/cover.png"


def _absolute_image_url(site_url, image_path):
    if image_path.startswith(("http://", "https://")):
        return image_path
    return site_url.rstrip("/") + "/" + image_path.lstrip("/")


def _meta_tag(prop, content, attr="property"):
    return f'<meta {attr}="{prop}" content="{content}">'


def on_post_page(html, page, config, **kwargs):
    site_url = config.get("site_url") or ""
    if not site_url:
        return html

    title = (page.meta or {}).get("title") or page.title or config.get("site_name", "")
    description = (page.meta or {}).get("description") or config.get("site_description", "")
    image = (page.meta or {}).get("image") or DEFAULT_IMAGE
    image_url = _absolute_image_url(site_url, image)

    # Replace social-plugin-emitted /assets/images/social/ tags first.
    og_social = re.compile(
        r'<meta\s+property="og:image"\s+content="[^"]*/assets/images/social/[^"]*"[^>]*>'
    )
    html = og_social.sub(_meta_tag("og:image", image_url), html)

    tw_social = re.compile(
        r'<meta\s+(?:property|name)="twitter:image"\s+content="[^"]*/assets/images/social/[^"]*"[^>]*>'
    )
    html = tw_social.sub(_meta_tag("twitter:image", image_url, attr="name"), html)

    # Inject any tags that are still missing, immediately before </head>.
    injections = []
    if not re.search(r'<meta\s+property="og:title"', html):
        injections.append(_meta_tag("og:title", title))
    if not re.search(r'<meta\s+property="og:description"', html):
        injections.append(_meta_tag("og:description", description))
    if not re.search(r'<meta\s+property="og:image"', html):
        injections.append(_meta_tag("og:image", image_url))
    if not re.search(r'<meta\s+property="og:type"', html):
        injections.append(_meta_tag("og:type", "website"))
    if not re.search(r'<meta\s+property="og:url"', html):
        page_url = site_url.rstrip("/") + "/" + (page.url or "").lstrip("/")
        injections.append(_meta_tag("og:url", page_url))

    if not re.search(r'<meta\s+(?:property|name)="twitter:card"', html):
        injections.append(_meta_tag("twitter:card", "summary_large_image", attr="name"))
    if not re.search(r'<meta\s+(?:property|name)="twitter:title"', html):
        injections.append(_meta_tag("twitter:title", title, attr="name"))
    if not re.search(r'<meta\s+(?:property|name)="twitter:description"', html):
        injections.append(_meta_tag("twitter:description", description, attr="name"))
    if not re.search(r'<meta\s+(?:property|name)="twitter:image"', html):
        injections.append(_meta_tag("twitter:image", image_url, attr="name"))

    if injections:
        html = html.replace("</head>", "  " + "\n  ".join(injections) + "\n</head>", 1)

    return html
```

### Step 2: Wire the Hook into `mkdocs.yml`

Add a top-level `hooks:` block. Place it directly under the `plugins:` block
for discoverability. The exact location doesn't matter to MkDocs, but the
block must be at the top level (not nested under `plugins:` — `hooks:` is a
peer of `plugins:`, not a child).

```yaml
# Hooks -- loaded as raw Python modules, not plugins (avoids name collisions).
# `plugins/social_override.py` injects og:title, og:description, og:image and
# twitter:* meta tags on every page using the page's frontmatter `image:` (and
# falling back to `img/cover.png` site-wide). When the optional `social` plugin
# is enabled, the same hook replaces its auto-generated
# /assets/images/social/ tags with the declared cover image.
hooks:
  - plugins/social_override.py
```

### Step 3: Confirm `docs/index.md` Frontmatter

The home page should declare `image:` (relative to `docs/`). If the project
was scaffolded by `home-page-template.md`, this is already the case:

```yaml
---
title: {{Book Title}}
description: {{One- or two-sentence book description, 55-200 chars optimal.}}
image: img/cover.png
hide:
  - toc
---
```

Notes:

- The hook reads only the `image:` key. Older templates also include
  `og:image:` and `twitter:image:` — those are harmless but unused by the
  hook. Don't strip them; they make the frontmatter self-documenting.
- **Title length:** the bk-check-social-cover verifier wants `og:title` in
  the 40-60 character range. If the bare book name is shorter, expand the
  frontmatter title (e.g. `Psychology — An AP-Level Intelligent Textbook`).
  The hook trusts the frontmatter, so this is the only place to fix it.
- **Description length:** target 55-200 chars. The home-page-template's
  default `site_description` is usually already in range.

### Step 4: Build and Verify Locally

```bash
mkdocs build
grep -E '<meta\s+(property|name)="(og|twitter)' site/index.html
```

Expected output: nine meta tags — `og:title`, `og:description`, `og:image`,
`og:type`, `og:url`, `twitter:card`, `twitter:title`, `twitter:description`,
`twitter:image`. The `og:image` and `twitter:image` URLs should be absolute
(start with `site_url`).

### Step 5: Run the Cover-Page Verifier

The verifier (`~/.local/bin/bk-check-social-cover`) checks the deployed
home page over HTTP. To test the local build before deploying, stage the
site under a `/<project>/` path and serve it:

```bash
# Replace <project> with the repo / site path segment, e.g. "psychology"
PROJ=<project>
rm -rf /tmp/bk-serve && mkdir -p /tmp/bk-serve/$PROJ
cp -r site/* /tmp/bk-serve/$PROJ/
(cd /tmp/bk-serve && python -m http.server 8765 >/tmp/bk-serve.log 2>&1 &)
sleep 1
~/.local/bin/bk-check-social-cover http://127.0.0.1:8765/$PROJ/
# cleanup:
pkill -f "python -m http.server 8765"
rm -rf /tmp/bk-serve /tmp/bk-serve.log
```

The script verifies:

1. `og:title` is present and reasonable length (warn outside 40-60 chars).
2. `og:description` is present and reasonable length (warn outside 55-200).
3. `og:image` is present, basename is **exactly** `cover.png`, and the
   image URL is reachable (HTTP 200).

The image-reachability check HEAD-requests the URL the hook produced — which
is `site_url + image`, i.e. the production URL. As long as the deployed site
already has `cover.png` at that path, this passes even when running the
verifier against a local server. (On a brand-new project with no deploy yet,
deploy first via `mkdocs gh-deploy`, then re-run.)

A successful run exits 0. Warnings are non-fatal. Errors are fatal —
typically caused by:

| Error | Fix |
|-------|-----|
| `og:image MISSING` | The hook didn't load. Check `hooks:` path in `mkdocs.yml`. |
| `og:image basename MUST be "cover.png"` | Rename the file to `cover.png` and update `image:` frontmatter. |
| `cover image not reachable (HTTP 404)` | Deploy first (`mkdocs gh-deploy --force`), or fix the `image:` path. |

### Step 6: Deploy

```bash
mkdocs gh-deploy --force
```

After deploy, run the verifier against the live URL with no localhost
plumbing:

```bash
~/.local/bin/bk-check-social-cover <project>
# or
~/.local/bin/bk-check-social-cover https://<user>.github.io/<project>/
```

## Best Practices

### Always Pair the Hook with a Cover Image

The hook is inert without `docs/img/cover.png`. If the project doesn't have
one yet, route the user to `cover-image-generator.md` first, then install
this hook.

### Don't Mix With the Social Plugin Unless Cairo Is Confirmed

The `mkdocs-material[imaging]` `social` plugin generates per-page card
images but requires Cairo (`brew install cairo` on macOS, plus
`pip install "mkdocs-material[imaging]"`). When a project enables the
social plugin without Cairo present, every build fails with a
`cairosvg` import error.

The hook in this guide is **the safer default**. Only enable the `social`
plugin when:

1. Cairo is installed and confirmed working (`python -c "import cairo"`).
2. The user explicitly wants per-page generated cards (rare).

When both are enabled, the hook automatically swaps the plugin's
`/assets/images/social/...` URLs for the declared `cover.png`. That's the
right behavior for an intelligent textbook — students share the *book*, not
individual pages.

### One Image Per Book (Not Per Page)

The hook defaults every page's `og:image` to the same `cover.png`. This is
intentional: when a chapter URL is shared on Slack/LinkedIn, the cover image
brands the unfurl with the book identity rather than a chapter-specific
graphic.

If a chapter genuinely needs its own preview image (rare), add `image:
img/chapters/01-foo.png` to that chapter's frontmatter. The hook picks it
up automatically.

### Don't Hand-Edit the Generated HTML

If a verifier failure tempts you to patch `site/index.html` directly, stop.
The fix belongs in either the hook or the frontmatter. Hand-edits get
clobbered on the next `mkdocs build`.

## Footgun: Frontmatter Key Collisions

YAML frontmatter keys with colons (`og:image:`, `twitter:image:`) parse as
**namespaced keys** in MkDocs' YAML loader, and *most* MkDocs plugins
silently ignore unknown keys. Authors who add `og:image: /img/cover.png`
to frontmatter and inspect the rendered HTML often find no meta tag and
assume MkDocs is broken.

It isn't — there's just no code emitting the tag. This hook is the missing
piece. If a verifier finds no og:image after install, double-check that
the `hooks:` block actually loads `plugins/social_override.py`.

## Troubleshooting

### "No meta tags in output, hook seems silent"

- Confirm the `hooks:` block is at the top level of `mkdocs.yml`, not
  nested under `plugins:`.
- Confirm the file is at `plugins/social_override.py` relative to
  `mkdocs.yml`, not under `docs/`.
- Run `mkdocs build --verbose` and look for `Running on_post_page event`
  entries. If none appear for `social_override`, the path is wrong.

### "og:image points to localhost, not the production URL"

- The hook uses `site_url` from `mkdocs.yml`. Confirm it's set to the
  production URL (e.g. `https://dmccreary.github.io/<project>/`), not a
  localhost address.

### "Title is too short" warning from bk-check-social-cover

This is a content fix, not a hook bug. Expand the `title:` frontmatter on
`docs/index.md` to land in the 40-60 char range. Example:

```yaml
title: Psychology — An AP-Level Intelligent Textbook
```

### "I want per-page descriptions but they're not showing"

Each page's `description:` frontmatter is read by the hook. If a chapter
has no `description:`, the hook falls back to `site_description`. Add a
`description:` to the chapter frontmatter to fix.

## Related References

- `home-page-template.md` — establishes the frontmatter the hook reads
- `cover-image-generator.md` — generates the `cover.png` the hook points to
- `mkdocs-features.md` — alternative `social` plugin path (Cairo-based)
