"""Validate URLs in a candidates TSV via HEAD-then-GET, with a real-browser UA.

Exits non-zero if any URL fails. Prints OK/FAIL per row.

Usage:
    python validate_links.py candidates.tsv
"""
import argparse
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
TIMEOUT = 12
CTX = ssl.create_default_context()


def check(url: str) -> tuple[bool, int | str]:
    """HEAD first; fall back to GET on 403/405/501 (sites that disallow HEAD)."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                return (200 <= r.status < 400, r.status)
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405, 501):
                continue
            return (False, e.code)
        except urllib.error.URLError as e:
            return (False, f"URLError: {e.reason}")
        except Exception as e:
            return (False, f"{type(e).__name__}: {e}")
    return (False, "unknown")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tsv", help="Path to candidates.tsv (slide<TAB>category<TAB>label<TAB>url[<TAB>anchor<TAB>substring])")
    args = p.parse_args()

    rows = []
    for line in Path(args.tsv).read_text(encoding="utf-8").splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            print(f"SKIP (too few columns): {line}", file=sys.stderr)
            continue
        rows.append(parts[:4])  # slide, category, label, url

    print(f"# Validation run: {date.today().isoformat()}  ({len(rows)} URLs)\n")
    failures = []
    for slide, category, label, url in rows:
        ok, code = check(url)
        tag = "OK  " if ok else "FAIL"
        print(f"[{tag}] {str(code):>14}  slide{slide:>3}  {category:<10}  {label:<40}  {url}")
        if not ok:
            failures.append((slide, label, url, code))

    print(f"\n{len(rows)} checked, {len(failures)} failed")
    if failures:
        print("\nFailures (resolve before applying):")
        for slide, label, url, code in failures:
            print(f"  slide{slide} '{label}' [{code}] {url}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
