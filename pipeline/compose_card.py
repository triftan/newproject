#!/usr/bin/env python3
"""Composite an editorial "card" layout onto rendered photos.

Inspired by clean photo-forward carousel templates (e.g. minimal habit-tips
decks): a full-bleed photo with a solid card at the bottom holding a small
uppercase KICKER label, a bold TITLE, and a 2-3 line description. This is a
different look from compose_text.py's big bottom headline, so it lives in its
own script and leaves the main compositor untouched.

Reads:
  - brands/<slug>/manifest.json   (for brand + the list of rendered slides)
  - brands/<slug>/cards.json      (kicker/title/body text per slide + style)

For each slide it sources the text-free photo (slides/raw-N.png if present,
else slides/slide-N.png which it backs up to raw-N.png first), draws the card,
and writes the final slides/slide-N.png. Idempotent: re-running re-sources from
raw-N.png so you can retune the layout for free.

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
TITLE_FONT = "Inter-SemiBold.ttf"
BODY_FONT = "Inter-SemiBold.ttf"
FALLBACK = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Layout constants, tuned for a 1080-wide canvas (scaled for other widths).
PAD_X = 70           # left/right padding inside the card
PAD_TOP = 60         # space above the kicker
PAD_BOTTOM = 64      # space below the body
KICKER_SIZE = 27
TITLE_SIZE = 60
BODY_SIZE = 30
TITLE_LEADING = 1.10
BODY_LEADING = 1.36
KICKER_TRACK = 3.0
GAP_KICKER_TITLE = 22
GAP_TITLE_BODY = 24
SWATCH = 18          # little accent square before the kicker


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


def compose(card, style, brand, src_path, dest_path, scale):
    img = Image.open(src_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    pad_x = int(PAD_X * scale)
    pad_top = int(PAD_TOP * scale)
    pad_bot = int(PAD_BOTTOM * scale)
    max_w = W - 2 * pad_x

    kicker_font = ImageFont.truetype(resolve_font(BODY_FONT), int(KICKER_SIZE * scale))
    title_font = ImageFont.truetype(resolve_font(TITLE_FONT), int(TITLE_SIZE * scale))
    body_font = ImageFont.truetype(resolve_font(BODY_FONT), int(BODY_SIZE * scale))

    kicker = (card.get("kicker") or "").upper()
    title_lines = wrap(draw, card.get("title", ""), title_font, max_w)
    body_lines = wrap(draw, card.get("body", ""), body_font, max_w)

    title_lh = int(TITLE_SIZE * scale * TITLE_LEADING)
    body_lh = int(BODY_SIZE * scale * BODY_LEADING)
    kicker_h = int(KICKER_SIZE * scale)

    content_h = (
        kicker_h
        + int(GAP_KICKER_TITLE * scale)
        + title_lh * len(title_lines)
        + int(GAP_TITLE_BODY * scale)
        + body_lh * len(body_lines)
    )
    card_h = content_h + pad_top + pad_bot
    card_top = H - card_h

    # Solid card band across the bottom.
    draw.rectangle([0, card_top, W, H], fill=style.get("card_bg", "#f6f3ea"))

    y = card_top + pad_top

    # Kicker row: a small accent swatch, then the tracked uppercase label.
    sw = int(SWATCH * scale)
    swatch_color = style.get("swatch_color")
    kx = pad_x
    if swatch_color:
        cy = y + (kicker_h - sw) // 2
        draw.rectangle([pad_x, cy, pad_x + sw, cy + sw], fill=swatch_color)
        kx = pad_x + sw + int(14 * scale)
    draw_tracked(draw, (kx, y), kicker, kicker_font,
                 style.get("kicker_color", "#2f6b4f"), KICKER_TRACK * scale)
    y += kicker_h + int(GAP_KICKER_TITLE * scale)

    # Title.
    for ln in title_lines:
        draw.text((pad_x, y), ln, font=title_font, fill=style.get("title_color", "#1b1b1b"))
        y += title_lh
    y += int(GAP_TITLE_BODY * scale)

    # Body.
    for ln in body_lines:
        draw.text((pad_x, y), ln, font=body_font, fill=style.get("body_color", "#5b5b5b"))
        y += body_lh

    # Optional brand handle, bottom-right of the card.
    handle = style.get("handle")
    if handle:
        hf = ImageFont.truetype(resolve_font(BODY_FONT), int(22 * scale))
        hw = draw.textlength(handle, font=hf)
        draw.text((W - pad_x - hw, H - int(34 * scale)), handle,
                  font=hf, fill=style.get("body_color", "#5b5b5b"))

    img.save(dest_path, format="PNG")
    n_lines = len(title_lines) + len(body_lines)
    print(f"  slide {card['n']}: '{card.get('title','')[:32]}' card, {n_lines} text line(s)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Composite editorial card layout onto photos")
    ap.add_argument("manifest", help="path to brands/<slug>/manifest.json")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}")
        return 1
    base = manifest_path.parent
    cards_path = base / "cards.json"
    if not cards_path.exists():
        print(f"error: cards.json not found next to manifest: {cards_path}")
        return 1

    manifest = json.loads(manifest_path.read_text())
    cards_doc = json.loads(cards_path.read_text())
    brand = manifest.get("brand", {})
    style = cards_doc.get("style", {})
    out_dir = base / "slides"

    print(f"Composing editorial cards (font: {TITLE_FONT})")
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
        # Scale layout constants relative to a 1080-wide reference.
        with Image.open(src) as probe:
            scale = probe.size[0] / 1080.0
        compose(card, style, brand, src, final, scale)

    print("Done. Re-run is idempotent (sources from slides/raw-N.png).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
