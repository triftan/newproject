#!/usr/bin/env python3
"""Build a self-contained HTML gallery for a rendered carousel.

Reads manifest.json (written by fal_render.py) and emits index.html next to it,
showing all slides at Instagram 4:5 ratio with the framework label, headline,
and the image prompt used. Open it in a browser to review / download slides.

Usage:
    python3 pipeline/build_gallery.py brands/<brand>/manifest.json
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:{bg}; --fg:{fg}; --accent:{accent}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         background:var(--bg); color:var(--fg); }}
  header {{ padding:40px 32px 8px; }}
  header h1 {{ margin:0 0 6px; font-size:28px; letter-spacing:-.02em; }}
  header p {{ margin:0; opacity:.7; font-size:15px; }}
  .swatches {{ display:flex; gap:8px; margin-top:16px; }}
  .swatch {{ width:28px; height:28px; border-radius:6px; border:1px solid rgba(128,128,128,.3); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
          gap:28px; padding:28px 32px 64px; }}
  .card {{ background:rgba(128,128,128,.06); border:1px solid rgba(128,128,128,.16);
          border-radius:14px; overflow:hidden; display:flex; flex-direction:column; }}
  .frame {{ position:relative; aspect-ratio:1080/1350; background:#000; }}
  .frame img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .badge {{ position:absolute; top:10px; left:10px; background:var(--accent); color:#fff;
           font-size:11px; font-weight:700; padding:4px 9px; border-radius:999px;
           text-transform:uppercase; letter-spacing:.04em; }}
  .meta {{ padding:14px 16px 18px; }}
  .meta .n {{ font-size:12px; opacity:.55; }}
  .meta h2 {{ font-size:16px; margin:4px 0 10px; line-height:1.3; }}
  .prompt {{ font-size:12px; opacity:.6; line-height:1.5; max-height:5.4em;
            overflow:hidden; }}
  .meta a {{ display:inline-block; margin-top:12px; font-size:12px; font-weight:600;
            color:var(--accent); text-decoration:none; }}
  .missing {{ display:flex; align-items:center; justify-content:center; height:100%;
             color:#888; font-size:13px; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <div class="swatches">{swatches}</div>
</header>
<div class="grid">
{cards}
</div>
</body>
</html>
"""

CARD = """  <div class="card">
    <div class="frame">
      <span class="badge">{framework}</span>
      {image}
    </div>
    <div class="meta">
      <div class="n">Slide {n}</div>
      <h2>{headline}</h2>
      <div class="prompt">{prompt}</div>
      {download}
    </div>
  </div>"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def build(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text())
    brand = manifest.get("brand", {})
    colors = brand.get("colors", []) or ["#111111", "#ff4d00", "#f5f5f5"]
    bg = colors[0] if colors else "#111"
    accent = colors[1] if len(colors) > 1 else "#ff4d00"
    # readable fg based on bg luminance
    fg = "#f5f5f5"
    try:
        h = bg.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        fg = "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#f5f5f5"
    except Exception:
        pass

    swatches = "".join(
        f'<div class="swatch" style="background:{esc(c)}" title="{esc(c)}"></div>'
        for c in colors
    )

    cards = []
    for slide in manifest.get("slides", []):
        n = slide.get("n")
        file = slide.get("file")
        if file:
            image = f'<img src="slides/{esc(file)}" alt="Slide {esc(n)}">'
            download = f'<a href="slides/{esc(file)}" download>Download PNG ↓</a>'
        else:
            image = '<div class="missing">not rendered</div>'
            download = ""
        cards.append(CARD.format(
            framework=esc(slide.get("framework", "")),
            n=esc(n),
            headline=esc(slide.get("headline", "")),
            prompt=esc(slide.get("prompt", "")),
            image=image,
            download=download,
        ))

    product = brand.get("name", "") or ""
    subtitle_bits = [b for b in [manifest.get("product"), product] if b]
    page = PAGE.format(
        title=esc(brand.get("name") or manifest.get("product") or "Carousel"),
        subtitle=esc(" · ".join(subtitle_bits) + "  —  Instagram carousel (1080×1350)"),
        bg=esc(bg), fg=fg, accent=esc(accent),
        swatches=swatches,
        cards="\n".join(cards),
    )
    out = manifest_path.parent / "index.html"
    out.write_text(page)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build HTML gallery from a carousel manifest")
    ap.add_argument("manifest", help="path to manifest.json")
    ap.add_argument("--open", action="store_true", help="open the gallery in a browser")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}")
        return 1
    out = build(manifest_path)
    print(f"Gallery written -> {out}")
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
