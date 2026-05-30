#!/usr/bin/env python3
"""Render carousel slide prompts via the OpenAI Images API, in parallel.

Reads a slides spec (JSON), submits every slide's image prompt to OpenAI's
image model concurrently, and writes the resulting PNGs into the brand's
output folder. The OpenAI Images API is synchronous (no polling) — each
request blocks until the image is ready, so we just run them on a thread pool.

Usage:
    python3 pipeline/openai_render.py brands/<brand>/slides.json
    python3 pipeline/openai_render.py brands/<brand>/slides.json --size 1024x1536
    python3 pipeline/openai_render.py brands/<brand>/slides.json --mock   # no key needed
    python3 pipeline/openai_render.py brands/<brand>/slides.json --refs brands/<brand>/image-refs

Auth:
    Set OPENAI_API_KEY in the environment (https://platform.openai.com/api-keys).

Reference images:
    The viral skill keeps an optional `image-refs/` folder of look-and-feel
    photos. By default those only teach *Claude* the aesthetic. Pass `--refs
    <dir>` (or set `reference_images` in the spec) to also hand them to the
    image model: when references are present a slide is rendered through the
    `/v1/images/edits` endpoint (gpt-image-1 accepts one or more reference
    images), so the render inherits the lighting/grade/camera feel of the refs
    instead of relying on the prompt alone. Resolution order, highest first:
    per-slide `reference_images` -> spec-level `reference_images` -> `--refs`
    dir -> a `image-refs/` folder next to the spec. With no references the
    text-only `/v1/images/generations` path is used exactly as before.

Size note:
    gpt-image-1 only supports 1024x1024, 1024x1536 (portrait), 1536x1024.
    For an IG 4:5 carousel we render the nearest portrait size (1024x1536) and,
    if Pillow is installed, center-crop to exactly 1080x1350. Without Pillow the
    native 1024x1536 PNG is kept (the gallery still shows it at 4:5).

The slides spec is produced by Claude during the /carousel workflow. Schema:
    {
      "brand": {"name": "...", "colors": ["#0a0a0a", "#ff4d00"], ...},
      "product": "Acme Sleep Drops",
      "image_size": {"width": 1080, "height": 1350},
      "slides": [
        {"n": 1, "framework": "Hook", "headline": "...", "prompt": "<image prompt>"},
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import sys
import urllib.request
from pathlib import Path

API_URL = "https://api.openai.com/v1/images/generations"
EDIT_URL = "https://api.openai.com/v1/images/edits"
DEFAULT_MODEL = os.environ.get("CAROUSEL_OPENAI_MODEL", "gpt-image-1")
DEFAULT_SIZE = os.environ.get("CAROUSEL_OPENAI_SIZE", "1024x1536")
REQUEST_TIMEOUT = 180.0
ALLOWED_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}

# How many reference images to send per slide at most. gpt-image-1 accepts more,
# but each one adds upload weight/latency; a handful is plenty to fix the look.
DEFAULT_MAX_REFS = int(os.environ.get("CAROUSEL_MAX_REFS", "4"))
REF_DIR_NAME = "image-refs"
REF_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg", ".webp": "image/webp"}


def log(msg: str) -> None:
    print(msg, flush=True)


def nearest_size(width: int, height: int) -> str:
    """Map a desired width/height to the closest size gpt-image-1 supports."""
    if width == height:
        return "1024x1024"
    return "1024x1536" if height > width else "1536x1024"


def generate(model: str, prompt: str, size: str, quality: str, key: str) -> bytes:
    """Call the OpenAI Images API and return decoded PNG bytes."""
    payload = {"model": model, "prompt": prompt, "size": size, "n": 1}
    if quality and quality != "auto":
        payload["quality"] = quality
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):  # dall-e style fallback
        with urllib.request.urlopen(item["url"], timeout=120.0) as r:
            return r.read()
    raise RuntimeError(f"No image in OpenAI response: {json.dumps(data)[:300]}")


def list_ref_dir(path: Path) -> list[Path]:
    """Return supported image files in a directory, sorted by name (stable)."""
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir()
                  if p.is_file() and p.suffix.lower() in REF_EXTS)


def resolve_refs(slide: dict, spec: dict, spec_dir: Path,
                 cli_refs: list[Path], max_refs: int) -> list[Path]:
    """Pick the reference images for one slide, highest-priority source first.

    Order: per-slide `reference_images` -> spec `reference_images` -> --refs dir
    -> a `image-refs/` folder next to the spec. Listed paths resolve relative to
    the spec dir; a path may point at a single file or a directory of images.
    Returns existing image files only, capped at `max_refs`.
    """
    listed = slide.get("reference_images") or spec.get("reference_images")
    refs: list[Path] = []
    if listed:
        for entry in listed:
            p = Path(entry)
            if not p.is_absolute():
                p = spec_dir / p
            refs.extend(list_ref_dir(p) if p.is_dir()
                        else ([p] if p.suffix.lower() in REF_EXTS else []))
    elif cli_refs:
        refs = list(cli_refs)
    else:
        refs = list_ref_dir(spec_dir / REF_DIR_NAME)

    seen: set[Path] = set()
    out: list[Path] = []
    for p in refs:
        rp = p.resolve()
        if rp in seen or not rp.is_file():
            continue
        seen.add(rp)
        out.append(rp)
    return out[:max_refs]


def _multipart(fields: dict[str, str], files: list[Path]) -> tuple[bytes, str]:
    """Build a multipart/form-data body for the images/edits endpoint."""
    boundary = "----carouselboundary" + base64.urlsafe_b64encode(
        os.urandom(12)).decode("ascii").rstrip("=")
    crlf = b"\r\n"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        chunks.append(b"")
        chunks.append(str(value).encode("utf-8"))
    for path in files:
        mime = MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")
        chunks.append(f"--{boundary}".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="image[]"; '
            f'filename="{path.name}"'.encode())
        chunks.append(f"Content-Type: {mime}".encode())
        chunks.append(b"")
        chunks.append(path.read_bytes())
    chunks.append(f"--{boundary}--".encode())
    chunks.append(b"")
    body = crlf.join(chunks)
    return body, f"multipart/form-data; boundary={boundary}"


def generate_with_refs(model: str, prompt: str, size: str, quality: str,
                       key: str, refs: list[Path]) -> bytes:
    """Call the images/edits endpoint with reference images; return PNG bytes."""
    fields = {"model": model, "prompt": prompt, "size": size, "n": "1"}
    if quality and quality != "auto":
        fields["quality"] = quality
    body, content_type = _multipart(fields, refs)
    req = urllib.request.Request(
        EDIT_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type},
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120.0) as r:
            return r.read()
    raise RuntimeError(f"No image in OpenAI response: {json.dumps(data)[:300]}")


def maybe_crop(png_bytes: bytes, target_w: int, target_h: int) -> bytes:
    """Center-crop/resize to target dims if Pillow is available; else passthrough."""
    try:
        import io
        from PIL import Image  # optional
    except ImportError:
        return png_bytes
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    w, h = img.size
    target_ratio = target_w / target_h
    ratio = w / h
    if ratio > target_ratio:  # too wide -> crop sides
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    elif ratio < target_ratio:  # too tall -> crop top/bottom
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    img = img.resize((target_w, target_h), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def render_slide(slide: dict, model: str, size: str, quality: str, key: str,
                 target: tuple[int, int], out_dir: Path,
                 refs: list[Path] | None = None) -> dict:
    n = slide["n"]
    if refs:
        names = ", ".join(p.name for p in refs)
        log(f"  slide {n}: requesting {model} @ {size} with {len(refs)} ref(s) [{names}]")
        png = generate_with_refs(model, slide["prompt"], size, quality, key, refs)
    else:
        log(f"  slide {n}: requesting {model} @ {size}")
        png = generate(model, slide["prompt"], size, quality, key)
    png = maybe_crop(png, *target)
    dest = out_dir / f"slide-{n}.png"
    dest.write_bytes(png)
    log(f"  slide {n}: done -> {dest}")
    return {"n": n, "file": dest.name, "refs": [p.name for p in (refs or [])]}


def render_slide_mock(slide: dict, target: tuple[int, int], out_dir: Path,
                      colors: list[str]) -> dict:
    """Offline placeholder: writes a solid brand-colored PNG (no deps)."""
    try:
        from png_writer import write_solid_png  # script run from pipeline/ dir
    except ImportError:
        from pipeline.png_writer import write_solid_png  # run as package
    n = slide["n"]
    color = colors[(n - 1) % len(colors)] if colors else "#222222"
    dest = out_dir / f"slide-{n}.png"
    write_solid_png(dest, target[0], target[1], color)
    log(f"  slide {n}: mock placeholder -> {dest} ({color})")
    return {"n": n, "file": dest.name}


def main() -> int:
    ap = argparse.ArgumentParser(description="Render carousel slides via OpenAI Images")
    ap.add_argument("spec", help="path to slides.json")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI image model")
    ap.add_argument("--size", default=None,
                    help=f"one of {sorted(ALLOWED_SIZES)} (default: nearest to image_size)")
    ap.add_argument("--quality", default="auto", choices=["auto", "low", "medium", "high"])
    ap.add_argument("--mock", action="store_true",
                    help="generate placeholder PNGs locally (no API key)")
    ap.add_argument("--refs", default=None,
                    help="dir of reference images to guide every slide via the "
                         "images/edits endpoint (per-slide/spec reference_images "
                         "override this; defaults to a image-refs/ folder by the spec)")
    ap.add_argument("--max-refs", type=int, default=DEFAULT_MAX_REFS,
                    help=f"cap reference images sent per slide (default {DEFAULT_MAX_REFS})")
    ap.add_argument("--concurrency", type=int, default=6)
    args = ap.parse_args()

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        log(f"error: spec not found: {spec_path}")
        return 1
    spec = json.loads(spec_path.read_text())

    slides = spec.get("slides", [])
    if not slides:
        log("error: spec has no slides")
        return 1

    size_spec = spec.get("image_size", {"width": 1080, "height": 1350})
    target = (int(size_spec["width"]), int(size_spec["height"]))
    size = args.size or nearest_size(*target)
    if size not in ALLOWED_SIZES:
        log(f"error: --size must be one of {sorted(ALLOWED_SIZES)}")
        return 1
    colors = spec.get("brand", {}).get("colors", [])
    spec_dir = spec_path.parent

    cli_refs: list[Path] = []
    if args.refs:
        refs_dir = Path(args.refs)  # relative to CWD, like the spec path itself
        cli_refs = list_ref_dir(refs_dir)
        if not cli_refs:
            log(f"warning: --refs {refs_dir} has no {sorted(REF_EXTS)} images")

    out_dir = spec_dir / "slides"
    out_dir.mkdir(parents=True, exist_ok=True)

    key = os.environ.get("OPENAI_API_KEY")
    if not args.mock and not key:
        log("error: OPENAI_API_KEY not set. Export it, or run with --mock to test the flow.")
        return 2

    mode = "mock" if args.mock else f"OpenAI {args.model} @ {size} (q={args.quality})"
    log(f"Rendering {len(slides)} slides -> {target[0]}x{target[1]} via {mode}")
    if not args.mock:
        with_refs = sum(
            1 for s in slides
            if resolve_refs(s, spec, spec_dir, cli_refs, args.max_refs))
        if with_refs:
            log(f"  {with_refs}/{len(slides)} slides use reference images "
                f"(images/edits endpoint)")

    results: list[dict] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {}
        for slide in slides:
            if args.mock:
                fut = ex.submit(render_slide_mock, slide, target, out_dir, colors)
            else:
                refs = resolve_refs(slide, spec, spec_dir, cli_refs, args.max_refs)
                fut = ex.submit(render_slide, slide, args.model, size,
                                args.quality, key, target, out_dir, refs)
            futures[fut] = slide["n"]
        for fut in concurrent.futures.as_completed(futures):
            n = futures[fut]
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001 - report per-slide, keep going
                errors.append(f"slide {n}: {exc}")
                log(f"  slide {n}: ERROR {exc}")

    results.sort(key=lambda r: r["n"])
    manifest = {
        "brand": spec.get("brand", {}),
        "product": spec.get("product"),
        "image_size": {"width": target[0], "height": target[1]},
        "slides": [
            {**next((s for s in slides if s["n"] == r["n"]), {}), **r}
            for r in results
        ],
    }
    (spec_path.parent / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"\nWrote manifest.json ({len(results)}/{len(slides)} slides rendered)")
    if errors:
        log("Some slides failed:\n  " + "\n  ".join(errors))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
