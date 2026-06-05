#!/usr/bin/env python3
"""Composite editorial text onto rendered photos.

Two looks, chosen by `style.mode` in cards.json:

- "overlay" (default): a big serif TITLE in a brand color laid directly over the
  photo, with a small uppercase eyebrow above and an all-caps subtitle below.
  No card/band. A soft top gradient + text shadow keep it legible. This matches
  photo-forward editorial templates where the type sits right on the image.
- "card": a solid bottom band holding an uppercase kicker, bold title, and a
  2-3 line description.

Reads brands/<slug>/manifest.json (brand) + brands/<slug>/cards.json (text +
style). Sources each text-free photo from slides/raw-N.png (or backs up
slide-N.png to raw-N.png first), draws the text, writes slides/slide-N.png.
Idempotent: re-running re-sources from raw-N.png, so retuning is free.

Usage:
    python3 pipeline/compose_card.py brands/<slug>/manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FALLBACK = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def resolve_font(name: str) -> str:
    p = ASSETS / name
    if p.exists():
        return str(p)
    for f in FALLBACK:
        if Path(f).exists():
            return f
    raise RuntimeError(f"No font found for {name} (expected assets/fonts/{name})")


def track_width(draw, text, font, track):
    if not text:
        return 0.0
    return sum(draw.textlength(ch, font=font) for ch in text) + track * (len(text) - 1)


def draw_tracked(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
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


def wrap_tracked(draw, text, font, max_w, track):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if track_width(draw, trial, font, track) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_title(draw, text, font_path, max_w, max_size, max_lines, min_size=40):
    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        lines = wrap(draw, text, font, max_w)
        if len(lines) <= max_lines:
            return font, lines, size
        size -= 4
    font = ImageFont.truetype(font_path, min_size)
    return font, wrap(draw, text, font, max_w), min_size


def apply_band_gradient(img, max_alpha, valign):
    """Gently darken the third of the image where the text sits (legibility,
    no hard box). Disabled when max_alpha <= 0."""
    if max_alpha <= 0:
        return img
    W, H = img.size
    col = Image.new("L", (1, H), 0)
    px = col.load()
    for y in range(H):
        f = y / (H - 1)
        if valign == "top":
            a = max_alpha * max(0.0, 1 - f / 0.5)
        elif valign == "bottom":
            a = max_alpha * max(0.0, (f - 0.5) / 0.5)
        else:  # center
            a = max_alpha * max(0.0, 1 - abs(f - 0.5) / 0.32)
        px[0, y] = int(a)
    mask = col.resize((W, H))
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), mask)
    return img


def line_x(W, line_w, align, mx):
    if align == "right":
        return W - mx - line_w
    if align == "center":
        return (W - line_w) // 2
    return mx


def compose_overlay(card, style, src_path, dest_path, scale):
    img = Image.open(src_path).convert("RGB")
    W, H = img.size

    color = style.get("title_color", "#ecd94f")
    eyebrow_color = style.get("eyebrow_color", color)
    body_color = style.get("body_color", "#f5f0dd")
    serif = resolve_font(style.get("title_font", "LiberationSerif-Bold.ttf"))
    serif_italic = resolve_font(style.get("eyebrow_font", "LiberationSerif-Italic.ttf"))
    sans = resolve_font(style.get("body_font", "Inter-SemiBold.ttf"))

    align = card.get("align", "left")
    valign = card.get("valign", "center")

    # Safe margins so nothing is clipped on mobile.
    mx = int(W * style.get("margin_x", 0.075))
    mt = int(H * style.get("margin_top", 0.06))
    mb = int(H * style.get("margin_bottom", 0.06))
    max_w = W - 2 * mx

    img = apply_band_gradient(img, int(style.get("scrim", 90)), valign)
    draw = ImageDraw.Draw(img, "RGBA")

    eyebrow = card.get("kicker") or ""
    eyebrow_font = ImageFont.truetype(serif_italic, int(34 * scale))
    title_font, title_lines, tsize = fit_title(
        draw, card.get("title", ""), serif, max_w, int(96 * scale), 4)
    body_size = int(style.get("body_size", 24) * scale)
    body_font = ImageFont.truetype(sans, body_size)
    body_lines = wrap(draw, card.get("body") or "", body_font, max_w)

    # Pre-measure the full block so we can vertically place it within margins.
    title_lh = int(tsize * 1.04)
    body_lh = int(body_size * 1.45)
    eyebrow_h = int(34 * scale)
    gap_eyebrow = int(18 * scale)
    gap_body = int(30 * scale)
    para_gap = int(body_size * 0.6)  # blank line between body sentences

    block_h = 0
    if eyebrow:
        block_h += eyebrow_h + gap_eyebrow
    block_h += title_lh * len(title_lines) + gap_body
    block_h += body_lh * len(body_lines)

    if valign == "top":
        y = mt
    elif valign == "bottom":
        y = H - mb - block_h
    else:
        y = (H - block_h) // 2
    y = max(mt, y)

    if eyebrow:
        ew = draw.textlength(eyebrow, font=eyebrow_font)
        draw.text((line_x(W, ew, align, mx), y), eyebrow, font=eyebrow_font, fill=eyebrow_color)
        y += eyebrow_h + gap_eyebrow

    for ln in title_lines:
        lw = draw.textlength(ln, font=title_font)
        draw.text((line_x(W, lw, align, mx), y), ln, font=title_font, fill=color)
        y += title_lh
    y += gap_body

    for ln in body_lines:
        lw = draw.textlength(ln, font=body_font)
        draw.text((line_x(W, lw, align, mx), y), ln, font=body_font, fill=body_color)
        y += body_lh

    img.save(dest_path, format="PNG")
    print(f"  slide {card['n']}: '{card.get('title','')[:28]}' [{align}/{valign}], "
          f"title {len(title_lines)} line(s) @ {tsize}px, body {body_size}px")


def compose_card(card, style, src_path, dest_path, scale):
    img = Image.open(src_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    pad_x, pad_top, pad_bot = int(70 * scale), int(60 * scale), int(64 * scale)
    max_w = W - 2 * pad_x
    kicker_font = ImageFont.truetype(resolve_font("Inter-SemiBold.ttf"), int(27 * scale))
    title_font = ImageFont.truetype(resolve_font("Inter-SemiBold.ttf"), int(60 * scale))
    body_font = ImageFont.truetype(resolve_font("Inter-SemiBold.ttf"), int(30 * scale))

    kicker = (card.get("kicker") or "").upper()
    title_lines = wrap(draw, card.get("title", ""), title_font, max_w)
    body_lines = wrap(draw, card.get("body", ""), body_font, max_w)
    title_lh, body_lh, kicker_h = int(60 * scale * 1.1), int(30 * scale * 1.36), int(27 * scale)
    content_h = (kicker_h + int(22 * scale) + title_lh * len(title_lines)
                 + int(24 * scale) + body_lh * len(body_lines))
    card_top = H - (content_h + pad_top + pad_bot)
    draw.rectangle([0, card_top, W, H], fill=style.get("card_bg", "#f6f3ea"))

    y = card_top + pad_top
    sw = int(18 * scale)
    if style.get("swatch_color"):
        draw.rectangle([pad_x, y + (kicker_h - sw) // 2, pad_x + sw, y + (kicker_h - sw) // 2 + sw],
                       fill=style["swatch_color"])
        kx = pad_x + sw + int(14 * scale)
    else:
        kx = pad_x
    draw_tracked(draw, (kx, y), kicker, kicker_font, style.get("kicker_color", "#2f6b4f"), 3 * scale)
    y += kicker_h + int(22 * scale)
    for ln in title_lines:
        draw.text((pad_x, y), ln, font=title_font, fill=style.get("title_color", "#1b1b1b"))
        y += title_lh
    y += int(24 * scale)
    for ln in body_lines:
        draw.text((pad_x, y), ln, font=body_font, fill=style.get("body_color", "#5b5b5b"))
        y += body_lh
    img.save(dest_path, format="PNG")
    print(f"  slide {card['n']}: '{card.get('title','')[:30]}' card")


def main() -> int:
    ap = argparse.ArgumentParser(description="Composite editorial text onto photos")
    ap.add_argument("manifest", help="path to brands/<slug>/manifest.json")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    base = manifest_path.parent
    cards_path = base / "cards.json"
    if not manifest_path.exists() or not cards_path.exists():
        print("error: need both manifest.json and cards.json in the brand folder")
        return 1

    cards_doc = json.loads(cards_path.read_text())
    style = cards_doc.get("style", {})
    mode = style.get("mode", "overlay")
    out_dir = base / "slides"

    print(f"Composing editorial text (mode: {mode})")
    for card in cards_doc.get("cards", []):
        n = card["n"]
        final = out_dir / f"slide-{n}.png"
        raw = out_dir / f"raw-{n}.png"
        if raw.exists():
            src = raw
        elif final.exists():
            final.replace(raw)
            src = raw
        else:
            print(f"  slide {n}: no image at {final}, skipping")
            continue
        with Image.open(src) as probe:
            scale = probe.size[0] / 1080.0
        if mode == "card":
            compose_card(card, style, src, final, scale)
        else:
            compose_overlay(card, style, src, final, scale)

    print("Done. Re-run is idempotent (sources from slides/raw-N.png).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
