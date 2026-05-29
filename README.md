# Branded IG Carousel Generator

One brand URL + one product name → **6 finished, on-brand 1080×1350 Instagram
carousel slides** and an HTML gallery. No Canva, no designer back-and-forth.

Built to run **inside Claude Code**: Claude does the scraping, brand analysis,
concept writing, and image-prompt authoring; a small Python pipeline renders all
slides via the [OpenAI Images API](https://platform.openai.com/docs/guides/images)
(`gpt-image-1`) in parallel and assembles the gallery.

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
   ┌────▼───────────────┐     ┌──────────────────────────┐
   │ openai_render.py   │ ──► │ OpenAI Images (parallel) │ → slides/slide-N.png
   │ (6 jobs at once)   │     └──────────────────────────┘   manifest.json
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

# 2. Render all slides in parallel via OpenAI Images
export OPENAI_API_KEY=...     # https://platform.openai.com/api-keys
python3 pipeline/openai_render.py brands/<slug>/slides.json
#   --quality high       sharper slides (slower / costlier)
#   --size 1024x1536     gpt-image-1 sizes: 1024x1024 | 1024x1536 | 1536x1024
#   --mock               no key: write placeholder PNGs to test the flow

# 3. Build the gallery
python3 pipeline/build_gallery.py brands/<slug>/manifest.json --open
```

## Try it now without a key

```bash
mkdir -p brands/drift && cp examples/slides.example.json brands/drift/slides.json
python3 pipeline/openai_render.py brands/drift/slides.json --mock
python3 pipeline/build_gallery.py brands/drift/manifest.json
open brands/drift/index.html   # or xdg-open / just open the file
```

`--mock` produces solid brand-colored placeholder slides so you can see the
pipeline and gallery work end-to-end. Real renders need `OPENAI_API_KEY`.

## Layout

| Path | What |
|------|------|
| `.claude/skills/carousel/SKILL.md` | the `/carousel` workflow Claude follows |
| `frameworks/carousel-frameworks.md` | proven carousel frameworks + copy/visual rules |
| `pipeline/openai_render.py` | renders prompts via OpenAI Images in parallel |
| `pipeline/build_gallery.py` | builds the HTML gallery from the manifest |
| `pipeline/png_writer.py` | zero-dep PNG writer used only for `--mock` |
| `examples/slides.example.json` | reference slides spec |
| `brands/<slug>/` | per-brand output (brand.json, slides.json, slides/, index.html) |

## Configuration

| Env var | Purpose |
|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required for real renders) |
| `CAROUSEL_OPENAI_MODEL` | override the image model (default `gpt-image-1`) |
| `CAROUSEL_OPENAI_SIZE` | override the render size (default `1024x1536`) |

Requires Python 3.10+ (standard library only). Optional: install `Pillow` to
center-crop renders to exactly 1080×1350; without it, slides stay at the native
gpt-image-1 size and the gallery displays them at 4:5.
