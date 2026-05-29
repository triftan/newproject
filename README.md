# Branded IG Carousel Generator

One brand URL + one product name → **6 finished, on-brand 1080×1350 Instagram
carousel slides** and an HTML gallery. No Canva, no designer back-and-forth.

Built to run **inside Claude Code**: Claude does the scraping, brand analysis,
concept writing, and image-prompt authoring; a small Python pipeline fires all
slides at [FAL](https://fal.ai) in parallel and assembles the gallery.

## How it works

```
brand URL + product
        │
   ┌────▼─────────────────────────────────────────────┐
   │ Claude (the /carousel skill)                      │
   │  1. WebFetch the site                             │
   │  2. extract colors / fonts / voice / positioning  │  → brand.json
   │  3. pick a framework, write 6 slide concepts      │
   │  4. author a detailed image prompt per slide      │  → slides.json
   └────┬──────────────────────────────────────────────┘
        │
   ┌────▼───────────────┐     ┌──────────────────────┐
   │ fal_render.py      │ ──► │ FAL (parallel render) │ → slides/slide-N.png
   │ (6 jobs at once)   │     └──────────────────────┘   manifest.json
   └────┬───────────────┘
        │
   ┌────▼───────────────┐
   │ build_gallery.py   │ → index.html  (open in a browser)
   └────────────────────┘
```

## Quick start (inside Claude Code)

Just ask:

> `/carousel` — make a carousel for **https://yourbrand.com**, product **"Your Product"**

Claude runs the whole flow and hands back `brands/<slug>/index.html`.

## Manual / CLI use

```bash
# 1. Author brands/<slug>/slides.json  (see examples/slides.example.json)

# 2. Render all slides in parallel via FAL
export FAL_KEY=...            # https://fal.ai/dashboard/keys
python3 pipeline/fal_render.py brands/<slug>/slides.json
#   --model fal-ai/...   pick a different FAL image model
#   --mock               no key: write placeholder PNGs to test the flow

# 3. Build the gallery
python3 pipeline/build_gallery.py brands/<slug>/manifest.json --open
```

## Try it now without a key

```bash
mkdir -p brands/drift && cp examples/slides.example.json brands/drift/slides.json
python3 pipeline/fal_render.py brands/drift/slides.json --mock
python3 pipeline/build_gallery.py brands/drift/manifest.json
open brands/drift/index.html   # or xdg-open / just open the file
```

`--mock` produces solid brand-colored placeholder slides so you can see the
pipeline and gallery work end-to-end. Real renders need `FAL_KEY`.

## Layout

| Path | What |
|------|------|
| `.claude/skills/carousel/SKILL.md` | the `/carousel` workflow Claude follows |
| `frameworks/carousel-frameworks.md` | proven carousel frameworks + copy/visual rules |
| `pipeline/fal_render.py` | fires prompts at FAL in parallel, downloads slides |
| `pipeline/build_gallery.py` | builds the HTML gallery from the manifest |
| `pipeline/png_writer.py` | zero-dep PNG writer used only for `--mock` |
| `examples/slides.example.json` | reference slides spec |
| `brands/<slug>/` | per-brand output (brand.json, slides.json, slides/, index.html) |

## Configuration

| Env var | Purpose |
|---------|---------|
| `FAL_KEY` | FAL API key (required for real renders) |
| `CAROUSEL_FAL_MODEL` | override the FAL image model (default `fal-ai/gpt-image-1/text-to-image`) |

Requires Python 3.10+ (standard library only — `urllib`, no pip install needed).
