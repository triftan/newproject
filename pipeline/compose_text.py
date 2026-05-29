#!/usr/bin/env python3
"""Overlay crisp typographic headlines onto rendered (text-free) slide images.

The image model (gpt-image-1) is great at backgrounds + product heroes but
unreliable at rendering text. So we render TEXT-FREE backgrounds, then bake the
headline here with a real font — pixel-sharp, perfectly spelled, properly bold.

Reads manifest.json (written by openai_render.py) and, for each slide, draws its
headline (and optional subline) using the brand's display font. The original
render is preserved as slides/raw-N.png so re-running is idempotent.

Usage:
    python3 pipeline/compose_text.py brands/<slug>/manifest.json

Per-slide typography is read from each slide's optional "type" object in
slides.json (carried through into manifest.json):
    "type": {
      "color": "#2B2B2B",        # headline color
      "align": "left",            # left | center
      "valign": "top",            # top | center | bottom
      "accent": "#C56B4E",        # accent bar color (omit/null to hide)
      "subline": "Link in bio",   # optional smaller line under the headline
      "subcolor": "#2B2B2B"
    }
Sensible brand-derived defaults fill anything omitted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
HEADLINE_FONTS = ["ArchivoBlack-Regular.ttf", "Anton-Regular.ttf"]
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find_font() -> str:
    for f in HEADLINE_FONTS:
        p = ASSETS / f
        if p.exists():
            return str(p)
    for p in FALLBACK_FONTS:
        if Path(p).exists():
            return p
    raise RuntimeError("No bold font found (expected assets/fonts/ArchivoBlack-Regular.ttf)")


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 0.0
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
         max_w: int) -> list[str]:
    """Greedy word-wrap to a pixel width."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_headline(draw, text, font_path, max_w, max_h, max_lines,
                 start=150, min_size=40):
    """Shrink font size until the wrapped headline fits the box."""
    size = start
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        lines = wrap(draw, text, font, max_w)
        if len(lines) <= max_lines:
            line_h = font.getbbox("Ag")[3] + int(size * 0.16)
            if line_h * len(lines) <= max_h:
                return font, lines, line_h
        size -= 4
    font = ImageFont.truetype(font_path, min_size)
    return font, wrap(draw, text, font, max_w), font.getbbox("Ag")[3] + int(min_size * 0.16)


def compose_slide(slide: dict, brand_colors: list[str], out_dir: Path,
                  font_path: str) -> None:
    n = slide["n"]
    headline = slide.get("headline", "")
    cfg = slide.get("type", {}) or {}

    final = out_dir / (slide.get("file") or f"slide-{n}.png")
    raw = out_dir / f"raw-{n}.png"
    # Source from the preserved raw render if present, else snapshot the render.
    if raw.exists():
        src = raw
    else:
        if not final.exists():
            print(f"  slide {n}: no image at {final}, skipping")
            return
        final.replace(raw)
        src = raw

    img = Image.open(src).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    # Defaults derived from the brand palette.
    dark = brand_colors[2] if len(brand_colors) > 2 else "#1a1a1a"
    cream = brand_colors[0] if brand_colors else "#f5f5f5"
    accent_default = brand_colors[1] if len(brand_colors) > 1 else "#ff4d00"

    color = cfg.get("color") or dark
    accent = cfg.get("accent", accent_default)
    align = cfg.get("align", "left")
    valign = cfg.get("valign", "top")
    subline = cfg.get("subline")
    subcolor = cfg.get("subcolor") or color

    margin = int(W * 0.075)
    max_w = int(W * cfg.get("max_width_frac", 0.86))
    max_lines = cfg.get("max_lines", 4)
    box_h = int(H * 0.42)

    font, lines, line_h = fit_headline(draw, headline, font_path, max_w, box_h, max_lines)
    block_h = line_h * len(lines)

    if valign == "top":
        y = margin + int(H * 0.02)
    elif valign == "bottom":
        y = H - margin - block_h - (90 if subline else 0)
    else:  # center
        y = (H - block_h) // 2

    # Accent bar above the headline (the "designed" agency touch).
    if accent:
        bar_x = margin if align == "left" else (W - 90) // 2
        draw.rectangle([bar_x, y - 34, bar_x + 90, y - 22], fill=accent)

    for line in lines:
        lw = draw.textlength(line, font=font)
        x = margin if align == "left" else (W - lw) // 2
        draw.text((x, y), line, font=font, fill=color)
        y += line_h

    if subline:
        sub_font = ImageFont.truetype(font_path, max(26, line_h // 4))
        sw = draw.textlength(subline, font=sub_font)
        sx = margin if align == "left" else (W - sw) // 2
        draw.text((sx, y + 18), subline, font=sub_font, fill=subcolor)

    img.save(final, format="PNG")
    print(f"  slide {n}: headline composed ({len(lines)} line(s)) -> {final}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Overlay typographic headlines onto slides")
    ap.add_argument("manifest", help="path to manifest.json")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text())
    colors = manifest.get("brand", {}).get("colors", [])
    out_dir = manifest_path.parent / "slides"
    font_path = find_font()
    print(f"Composing headlines with {Path(font_path).name}")

    for slide in manifest.get("slides", []):
        if slide.get("file"):
            compose_slide(slide, colors, out_dir, font_path)
    print("Done. Re-run is idempotent (sources from slides/raw-N.png).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
