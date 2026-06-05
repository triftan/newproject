#!/usr/bin/env python3
"""Build a free, self-contained, swipeable HTML carousel from a folder of images.

Zero dependencies, no external libraries, no CDN. Drop your images in a folder,
point this at it, and open the resulting index.html in any browser. Works on
desktop (arrows / click / keyboard) and mobile (swipe).

Usage:
    python3 pipeline/build_carousel.py <images_dir>
    python3 pipeline/build_carousel.py <images_dir> --title "My Carousel" --out carousel.html
    python3 pipeline/build_carousel.py <images_dir> --embed     # inline images -> single portable file
    python3 pipeline/build_carousel.py <images_dir> --ratio 4:5 # slide aspect ratio (default 4:5)

--embed base64-inlines every image so the single HTML file is fully portable
(shareable / works offline with no sibling image files). Without it, images are
referenced by relative path, so keep the HTML next to the images.
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}


def natural_key(p: Path):
    """Sort like a human: slide-2 before slide-10."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def collect_images(d: Path) -> list[Path]:
    return sorted((p for p in d.iterdir() if p.suffix.lower() in IMAGE_EXTS), key=natural_key)


def src_for(img: Path, base: Path, embed: bool) -> str:
    if not embed:
        return img.relative_to(base).as_posix()
    mime = mimetypes.guess_type(img.name)[0] or "image/png"
    b64 = base64.b64encode(img.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_html(images: list[Path], base: Path, title: str, ratio: str, embed: bool) -> str:
    try:
        rw, rh = (float(x) for x in ratio.split(":"))
        aspect = f"{rw} / {rh}"
    except Exception:
        aspect = "4 / 5"

    slides = "\n".join(
        f'      <li class="slide"><img loading="lazy" src="{src_for(img, base, embed)}" '
        f'alt="Slide {i + 1}"></li>'
        for i, img in enumerate(images)
    )
    dots = "\n".join(
        f'      <button class="dot" data-i="{i}" aria-label="Go to slide {i + 1}"></button>'
        for i in range(len(images))
    )
    safe_title = (title or "Carousel").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
  :root {{ --aspect: {aspect}; --bg: #0e0e10; --fg: #f4f4f5; --accent: #ecd94f; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg);
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         min-height: 100vh; display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 18px; padding: 24px; }}
  h1 {{ font-size: 15px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;
        opacity: .7; margin: 0; }}
  .carousel {{ position: relative; width: min(92vw, 460px); }}
  .viewport {{ overflow: hidden; border-radius: 16px; aspect-ratio: var(--aspect);
               background: #000; box-shadow: 0 20px 60px rgba(0,0,0,.5); }}
  .track {{ display: flex; height: 100%; margin: 0; padding: 0; list-style: none;
            transition: transform .38s cubic-bezier(.4,.0,.2,1); touch-action: pan-y; }}
  .track.dragging {{ transition: none; }}
  .slide {{ min-width: 100%; height: 100%; }}
  .slide img {{ width: 100%; height: 100%; object-fit: cover; display: block; -webkit-user-drag: none; user-select: none; }}
  .nav {{ position: absolute; top: 50%; transform: translateY(-50%); width: 44px; height: 44px;
          border: none; border-radius: 50%; background: rgba(0,0,0,.45); color: #fff;
          font-size: 22px; cursor: pointer; display: grid; place-items: center;
          backdrop-filter: blur(4px); transition: background .2s; }}
  .nav:hover {{ background: rgba(0,0,0,.7); }}
  .nav.prev {{ left: 10px; }} .nav.next {{ right: 10px; }}
  .nav[disabled] {{ opacity: .25; cursor: default; }}
  .dots {{ display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 14px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; border: none; padding: 0;
          background: rgba(255,255,255,.3); cursor: pointer; transition: all .2s; }}
  .dot.active {{ background: var(--accent); transform: scale(1.35); }}
  .counter {{ font-variant-numeric: tabular-nums; font-size: 13px; opacity: .6; }}
</style>
</head>
<body>
  <h1>{safe_title}</h1>
  <div class="carousel">
    <div class="viewport">
      <ul class="track">
{slides}
      </ul>
    </div>
    <button class="nav prev" aria-label="Previous">&#8249;</button>
    <button class="nav next" aria-label="Next">&#8250;</button>
  </div>
  <div class="dots">
{dots}
  </div>
  <div class="counter"></div>
<script>
(function () {{
  const track = document.querySelector('.track');
  const slides = Array.from(track.children);
  const prev = document.querySelector('.prev');
  const next = document.querySelector('.next');
  const dots = Array.from(document.querySelectorAll('.dot'));
  const counter = document.querySelector('.counter');
  let index = 0;
  const n = slides.length;

  function render() {{
    track.style.transform = 'translateX(' + (-index * 100) + '%)';
    dots.forEach((d, i) => d.classList.toggle('active', i === index));
    prev.disabled = index === 0;
    next.disabled = index === n - 1;
    counter.textContent = (index + 1) + ' / ' + n;
  }}
  function go(i) {{ index = Math.max(0, Math.min(n - 1, i)); render(); }}

  prev.addEventListener('click', () => go(index - 1));
  next.addEventListener('click', () => go(index + 1));
  dots.forEach(d => d.addEventListener('click', () => go(+d.dataset.i)));
  window.addEventListener('keydown', e => {{
    if (e.key === 'ArrowLeft') go(index - 1);
    if (e.key === 'ArrowRight') go(index + 1);
  }});

  // Touch / pointer drag
  let startX = 0, dx = 0, dragging = false;
  const down = x => {{ startX = x; dx = 0; dragging = true; track.classList.add('dragging'); }};
  const move = x => {{
    if (!dragging) return;
    dx = x - startX;
    const pct = (dx / track.clientWidth) * 100;
    track.style.transform = 'translateX(' + (-index * 100 + pct) + '%)';
  }};
  const up = () => {{
    if (!dragging) return;
    dragging = false; track.classList.remove('dragging');
    const threshold = track.clientWidth * 0.18;
    if (dx > threshold) go(index - 1);
    else if (dx < -threshold) go(index + 1);
    else render();
  }};
  track.addEventListener('touchstart', e => down(e.touches[0].clientX), {{ passive: true }});
  track.addEventListener('touchmove', e => move(e.touches[0].clientX), {{ passive: true }});
  track.addEventListener('touchend', up);
  track.addEventListener('mousedown', e => {{ e.preventDefault(); down(e.clientX); }});
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', up);

  render();
}})();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a free swipeable HTML carousel from images")
    ap.add_argument("images_dir", help="folder containing the carousel images")
    ap.add_argument("--title", default="Carousel")
    ap.add_argument("--out", default=None, help="output HTML path (default: <images_dir>/carousel.html)")
    ap.add_argument("--ratio", default="4:5", help="slide aspect ratio, e.g. 4:5, 1:1, 9:16")
    ap.add_argument("--embed", action="store_true", help="inline images as base64 (single portable file)")
    args = ap.parse_args()

    images_dir = Path(args.images_dir).resolve()
    if not images_dir.is_dir():
        print(f"error: not a folder: {images_dir}")
        return 1
    images = collect_images(images_dir)
    if not images:
        print(f"error: no images found in {images_dir} (looked for {sorted(IMAGE_EXTS)})")
        return 1

    out = Path(args.out).resolve() if args.out else images_dir / "carousel.html"
    base = out.parent
    if not args.embed:
        # Relative paths only work if the HTML can reach the images.
        try:
            images[0].relative_to(base)
        except ValueError:
            print("warning: images are not under the output folder; use --embed or --out inside the images folder")
    html = build_html(images, base, args.title, args.ratio, args.embed)
    out.write_text(html, encoding="utf-8")
    print(f"Built carousel with {len(images)} slide(s) -> {out}")
    print("Open it in a browser. Swipe / arrow keys / click arrows to navigate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
