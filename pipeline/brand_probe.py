#!/usr/bin/env python3
"""Probe a brand site for REAL colors and fonts (grounds the brand kit in data).

Fetches the page HTML and its linked stylesheets, then extracts:
  - the most frequent colors (hex + rgb), ranked by use
  - font-family names in use, and @font-face families (the brand's real fonts)
  - theme-color / og:image hints

This replaces guesswork: Claude reads the JSON and curates a coherent palette +
picks a font to match (via get_font.py). Output is printed as JSON.

Usage:
    python3 pipeline/brand_probe.py https://brand.com
    python3 pipeline/brand_probe.py https://brand.com --css 8   # max stylesheets
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/120 Safari/537.36"
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", re.I)
FONT_FACE_RE = re.compile(r"@font-face\s*{[^}]*?font-family\s*:\s*['\"]?([^;'\"}]+)", re.I)
FONT_FAM_RE = re.compile(r"font-family\s*:\s*([^;{}]+)", re.I)
LINK_CSS_RE = re.compile(r"<link[^>]+rel=['\"]?stylesheet['\"]?[^>]*>", re.I)
HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]", re.I)
META_RE = re.compile(r"<meta[^>]+>", re.I)


def fetch(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return raw.decode("utf-8", "ignore")
    except Exception:
        return raw.decode("latin-1", "ignore")


def norm_hex(h: str) -> str:
    h = h.lower()
    if len(h) == 4:  # #abc -> #aabbcc
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def is_greyish(h: str) -> bool:
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return max(r, g, b) - min(r, g, b) < 12  # near-grey/white/black


def collect_colors(text: str, counter: Counter) -> None:
    for m in HEX_RE.findall(text):
        counter[norm_hex(m)] += 1
    for r, g, b in RGB_RE.findall(text):
        try:
            counter["#%02x%02x%02x" % (int(r), int(g), int(b))] += 1
        except ValueError:
            pass


def collect_fonts(text: str, families: Counter, faces: Counter) -> None:
    for fam in FONT_FACE_RE.findall(text):
        faces[fam.strip().strip("'\"")] += 1
    for decl in FONT_FAM_RE.findall(text):
        first = decl.split(",")[0].strip().strip("'\"")
        if first and not first.startswith(("var(", "inherit", "initial")):
            families[first] += 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe a brand site for colors + fonts")
    ap.add_argument("url")
    ap.add_argument("--css", type=int, default=8, help="max stylesheets to fetch")
    args = ap.parse_args()

    try:
        html = fetch(args.url)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"error": f"failed to fetch {args.url}: {e}"}))
        return 1

    colors: Counter = Counter()
    families: Counter = Counter()
    faces: Counter = Counter()

    collect_colors(html, colors)
    collect_fonts(html, families, faces)

    # Follow linked stylesheets.
    css_urls = []
    for link in LINK_CSS_RE.findall(html):
        m = HREF_RE.search(link)
        if m:
            css_urls.append(urllib.parse.urljoin(args.url, m.group(1)))
    fetched = []
    for cu in css_urls[: args.css]:
        try:
            css = fetch(cu)
            collect_colors(css, colors)
            collect_fonts(css, families, faces)
            fetched.append(cu)
        except Exception:
            continue

    # meta theme-color / og:image
    theme, og_image = None, None
    for tag in META_RE.findall(html):
        low = tag.lower()
        if "theme-color" in low:
            mm = re.search(r"content=['\"]([^'\"]+)", tag, re.I)
            if mm:
                theme = mm.group(1)
        if "og:image" in low:
            mm = re.search(r"content=['\"]([^'\"]+)", tag, re.I)
            if mm:
                og_image = mm.group(1)

    vivid = [(c, n) for c, n in colors.most_common() if len(c) == 7 and not is_greyish(c)]
    neutrals = [(c, n) for c, n in colors.most_common() if len(c) == 7 and is_greyish(c)]

    out = {
        "url": args.url,
        "stylesheets_scanned": fetched,
        "theme_color": theme,
        "og_image": og_image,
        "top_brand_colors": [c for c, _ in vivid[:10]],
        "top_neutrals": [c for c, _ in neutrals[:6]],
        "font_faces_declared": [f for f, _ in faces.most_common(10)],
        "font_families_used": [f for f, _ in families.most_common(10)],
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
