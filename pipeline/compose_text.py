#!/usr/bin/env python3
"""Overlay crisp typographic headlines onto rendered (text-free) slide images.

The image model (gpt-image-1) is great at backgrounds + product heroes but
unreliable at rendering text. So we render TEXT-FREE backgrounds, then bake the
headline here with a real font — pixel-sharp, perfectly spelled, properly bold.

Reads manifest.json (written by openai_render.py) and, for each slide, draws its
headline (and optional subline) using a clean bold font. The original render is
preserved as slides/raw-N.png so re-running is idempotent (you can retune
typography for free, without re-rendering images).

Usage:
    python3 pipeline/compose_text.py brands/<slug>/manifest.json

Per-slide typography is read from each slide's optional "type" object in
slides.json (carried through into manifest.json). All fields optional:
    "type": {
      "font": "Poppins-SemiBold.ttf",  # file in assets/fonts/
      "color": "#2B2B2B",               # headline color
      "size": 84,                        # MAX cap in px (auto-shrinks to fit)
      "align": "left",                   # left | center
      "valign": "top",                   # top | center | bottom
      "tracking": -1.5,                  # letter spacing in px (negative=tighter)
      "leading": 1.12,                   # line-height multiple
      "accent": "#C56B4E",               # rule bar above headline (null hides)
      "scrim": false,                    # soft contrast pad behind text
      "subline": "Link in bio",          # optional small line under headline
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
DEFAULT_FONTS = ["Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "ArchivoBlack-Regular.ttf"]
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Type scale (relative to a 1080px-wide canvas).
MARGIN_FRAC = 0.078
MAX_WIDTH_FRAC = 0.84
DEFAULT_MAX_SIZE = 86
MIN_SIZE = 34
DEFAULT_LEADING = 1.12
DEFAULT_TRACKING = -1.5
MAX_LINES = 3


def resolve_font(name: str | None) -> str:
    if name:
        p = ASSETS / name
        if p.exists():
            return str(p)
    for f in DEFAULT_FONTS:
        if (ASSETS / f).exists():
            return str(ASSETS / f)
    for p in FALLBACK_FONTS:
        if Path(p).exists():
            return p
    raise RuntimeError("No headline font found (expected assets/fonts/Poppins-SemiBold.ttf)")


def line_width(draw, text, font, tracking) -> float:
    if not text:
        return 0.0
    w = sum(draw.textlength(ch, font=font) for ch in text)
    return w + tracking * (len(text) - 1)


def draw_line(draw, xy, text, font, fill, tracking):
    x, y = xy
    if tracking == 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def wrap(draw, text, font, max_w, tracking) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if line_width(draw, trial, font, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_headline(draw, text, font_path, max_w, max_size, max_lines, tracking):
    """Largest size <= max_size that wraps within width and line budget."""
    size = max_size
    while size >= MIN_SIZE:
        font = ImageFont.truetype(font_path, size)
        lines = wrap(draw, text, font, max_w, tracking)
        if len(lines) <= max_lines:
            return font, lines, size
        size -= 3
    font = ImageFont.truetype(font_path, MIN_SIZE)
    return font, wrap(draw, text, font, max_w, tracking), MIN_SIZE


def compose_slide(slide, brand_colors, out_dir, brand_font=None, W_hint=1080):
    n = slide["n"]
    headline = slide.get("headline", "")
    cfg = slide.get("type", {}) or {}

    final = out_dir / (slide.get("file") or f"slide-{n}.png")
    raw = out_dir / f"raw-{n}.png"
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
    draw = ImageDraw.Draw(img, "RGBA")

    dark = brand_colors[2] if len(brand_colors) > 2 else "#1a1a1a"
    accent_default = brand_colors[1] if len(brand_colors) > 1 else "#ff4d00"

    font_path = resolve_font(cfg.get("font") or brand_font)
    color = cfg.get("color") or dark
    accent = cfg.get("accent", accent_default)
    align = cfg.get("align", "left")
    valign = cfg.get("valign", "top")
    tracking = cfg.get("tracking", DEFAULT_TRACKING)
    leading = cfg.get("leading", DEFAULT_LEADING)
    max_size = int(cfg.get("size", round(DEFAULT_MAX_SIZE * W / 1080)))
    subline = cfg.get("subline")
    subcolor = cfg.get("subcolor") or color

    margin = int(W * MARGIN_FRAC)
    max_w = int(W * cfg.get("max_width_frac", MAX_WIDTH_FRAC))

    font, lines, size = fit_headline(draw, headline, font_path, max_w,
                                     max_size, cfg.get("max_lines", MAX_LINES), tracking)
    line_h = int(size * leading)
    block_h = line_h * len(lines)
    sub_gap, sub_size = int(size * 0.45), max(20, int(size * 0.34))
    sub_h = (sub_gap + sub_size) if subline else 0
    bar_h, bar_gap = max(5, int(size * 0.07)), int(size * 0.30)
    bar_w = int(size * 0.95)
    top_extra = (bar_gap + bar_h) if accent else 0

    if valign == "top":
        y0 = margin
    elif valign == "bottom":
        y0 = H - margin - block_h - sub_h
    else:
        y0 = (H - block_h - sub_h - top_extra) // 2 + top_extra

    if accent:
        bx = margin if align == "left" else (W - bar_w) // 2
        draw.rectangle([bx, y0, bx + bar_w, y0 + bar_h], fill=accent)
        y0 += bar_h + bar_gap

    # Optional soft contrast pad behind the text region.
    if cfg.get("scrim"):
        pad = int(size * 0.4)
        sl = luminance(color)
        veil = (255, 255, 255, 90) if sl < 128 else (0, 0, 0, 90)
        draw.rectangle([0, max(0, y0 - pad), W, y0 + block_h + sub_h + pad // 2], fill=veil)

    y = y0
    for ln in lines:
        lw = line_width(draw, ln, font, tracking)
        x = margin if align == "left" else (W - lw) // 2
        draw_line(draw, (x, y), ln, font, color, tracking)
        y += line_h

    if subline:
        sub_font = ImageFont.truetype(font_path, sub_size)
        sw = line_width(draw, subline, sub_font, 0)
        sx = margin if align == "left" else (W - sw) // 2
        draw.text((sx, y - line_h + size + sub_gap), subline, font=sub_font, fill=subcolor)

    img.save(final, format="PNG")
    print(f"  slide {n}: '{headline[:32]}' @ {size}px, {len(lines)} line(s) -> {final.name}")


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 0.0
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def main() -> int:
    ap = argparse.ArgumentParser(description="Overlay typographic headlines onto slides")
    ap.add_argument("manifest", help="path to manifest.json")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text())
    brand = manifest.get("brand", {})
    colors = brand.get("colors", [])
    brand_font = brand.get("font_file")
    out_dir = manifest_path.parent / "slides"
    default_name = Path(resolve_font(brand_font)).name
    print(f"Composing headlines (font: {default_name})")

    for slide in manifest.get("slides", []):
        if slide.get("file"):
            compose_slide(slide, colors, out_dir, brand_font=brand_font)
    print("Done. Re-run is idempotent (sources from slides/raw-N.png).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
