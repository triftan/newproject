#!/usr/bin/env python3
"""Fire carousel slide prompts at FAL in parallel and download finished slides.

Reads a slides spec (JSON), submits every slide's image prompt to a FAL image
model concurrently, polls each queued job until it's done, and downloads the
resulting 1080x1350 PNG into the brand's output folder.

Usage:
    python3 pipeline/fal_render.py brands/<brand>/slides.json
    python3 pipeline/fal_render.py brands/<brand>/slides.json --model fal-ai/gpt-image-1/text-to-image
    python3 pipeline/fal_render.py brands/<brand>/slides.json --mock   # no API key needed

Auth:
    Set FAL_KEY in the environment (get one at https://fal.ai/dashboard/keys).

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
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

QUEUE_BASE = "https://queue.fal.run"
DEFAULT_MODEL = os.environ.get("CAROUSEL_FAL_MODEL", "fal-ai/gpt-image-1/text-to-image")
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 300.0


def log(msg: str) -> None:
    print(msg, flush=True)


def _request(url: str, *, method: str = "GET", headers: dict | None = None,
             body: bytes | None = None, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def submit_job(model: str, prompt: str, width: int, height: int, key: str) -> dict:
    """Submit one image request to the FAL queue, returns the queue response."""
    payload = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": 1,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }
    return _request(f"{QUEUE_BASE}/{model}", method="POST", headers=headers,
                    body=body, timeout=60.0)


def poll_until_done(model: str, request_id: str, key: str) -> dict:
    """Poll a queued FAL job until COMPLETED, then return the final result."""
    headers = {"Authorization": f"Key {key}"}
    status_url = f"{QUEUE_BASE}/{model}/requests/{request_id}/status"
    result_url = f"{QUEUE_BASE}/{model}/requests/{request_id}"
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        status = _request(status_url, headers=headers, timeout=30.0)
        state = status.get("status")
        if state == "COMPLETED":
            return _request(result_url, headers=headers, timeout=60.0)
        if state in {"FAILED", "ERROR"}:
            raise RuntimeError(f"FAL job {request_id} failed: {status}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"FAL job {request_id} timed out after {POLL_TIMEOUT:.0f}s")


def extract_image_url(result: dict) -> str:
    """Pull the first image URL out of a FAL result (handles common shapes)."""
    images = result.get("images") or result.get("data", {}).get("images")
    if images:
        first = images[0]
        return first["url"] if isinstance(first, dict) else first
    if result.get("image", {}).get("url"):
        return result["image"]["url"]
    raise RuntimeError(f"No image URL found in FAL result: {json.dumps(result)[:300]}")


def download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120.0) as resp:
        dest.write_bytes(resp.read())


def render_slide_fal(slide: dict, model: str, width: int, height: int,
                     key: str, out_dir: Path) -> dict:
    n = slide["n"]
    log(f"  slide {n}: submitting -> {model}")
    submitted = submit_job(model, slide["prompt"], width, height, key)
    request_id = submitted.get("request_id") or submitted.get("requestId")
    if not request_id:
        raise RuntimeError(f"slide {n}: no request_id in submit response: {submitted}")
    log(f"  slide {n}: queued ({request_id[:8]}…), polling")
    result = poll_until_done(model, request_id, key)
    url = extract_image_url(result)
    dest = out_dir / f"slide-{n}.png"
    download(url, dest)
    log(f"  slide {n}: done -> {dest}")
    return {"n": n, "file": dest.name, "source_url": url}


def render_slide_mock(slide: dict, width: int, height: int, out_dir: Path,
                      colors: list[str]) -> dict:
    """Offline placeholder: writes a solid brand-colored PNG (no deps)."""
    try:
        from png_writer import write_solid_png  # script run from pipeline/ dir
    except ImportError:
        from pipeline.png_writer import write_solid_png  # run as package
    n = slide["n"]
    color = colors[(n - 1) % len(colors)] if colors else "#222222"
    dest = out_dir / f"slide-{n}.png"
    write_solid_png(dest, width, height, color)
    log(f"  slide {n}: mock placeholder -> {dest} ({color})")
    return {"n": n, "file": dest.name, "source_url": None}


def main() -> int:
    ap = argparse.ArgumentParser(description="Render carousel slides via FAL")
    ap.add_argument("spec", help="path to slides.json")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="FAL model id")
    ap.add_argument("--mock", action="store_true",
                    help="generate placeholder PNGs locally (no API key)")
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
    size = spec.get("image_size", {"width": 1080, "height": 1350})
    width, height = int(size["width"]), int(size["height"])
    colors = spec.get("brand", {}).get("colors", [])

    out_dir = spec_path.parent / "slides"
    out_dir.mkdir(parents=True, exist_ok=True)

    key = os.environ.get("FAL_KEY")
    if not args.mock and not key:
        log("error: FAL_KEY not set. Export it, or run with --mock to test the pipeline.")
        return 2

    mode = "mock" if args.mock else f"FAL ({args.model})"
    log(f"Rendering {len(slides)} slides at {width}x{height} via {mode}")

    results: list[dict] = []
    errors: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {}
        for slide in slides:
            if args.mock:
                fut = ex.submit(render_slide_mock, slide, width, height, out_dir, colors)
            else:
                fut = ex.submit(render_slide_fal, slide, args.model, width, height, key, out_dir)
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
        "image_size": {"width": width, "height": height},
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
