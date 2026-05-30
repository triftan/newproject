# IG Carousel Generator

One brand URL + one product name → **6 finished, on-brand 1080×1350 Instagram
carousel slides** and an HTML gallery. No Canva, no designer back-and-forth.

### Two skills, one engine

| Skill | Use it for | Look |
|-------|-----------|------|
| **`/carousel`** | branded / e-commerce product carousels | brand palette, graphic color-blocked backgrounds, matched brand fonts, product hero |
| **`/viral-carousel`** | organic-growth faceless carousels (IG/TikTok) | candid iPhone "found, not made" photos, faceless people, plain white overlay, 8 slides + proven viral formats |

Both share the same Python pipeline (OpenAI Images + Pillow compositor) — they
differ in framework and aesthetic, not engine. Pick by goal: sell a product →
`/carousel`; grow an account → `/viral-carousel`.

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
   │  1. brand_probe.py → REAL colors + fonts from CSS │
   │  2. get_font.py → fetch the brand's matched font  │  → brand.json
   │  3. WebFetch → voice / positioning / product facts│
   │  4. pick a framework, write 6 slide concepts      │
   │  5. author a TEXT-FREE image prompt per slide     │  → slides.json
   └────┬──────────────────────────────────────────────┘
        │
   ┌────▼───────────────┐     ┌──────────────────────────┐
   │ openai_render.py   │ ──► │ OpenAI Images (parallel) │ → text-free backgrounds
   │ (6 jobs at once)   │     └──────────────────────────┘   slides/slide-N.png
   └────┬───────────────┘                                    manifest.json
        │
   ┌────▼───────────────┐
   │ compose_text.py    │ → overlays real bold headlines (Poppins SemiBold, Pillow)
   │ (typography)       │   size-capped, crisp + correctly spelled → slides/slide-N.png
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
# 0. Probe the brand for real colors + fonts, and fetch the matched font
python3 pipeline/brand_probe.py https://brand.com
python3 pipeline/get_font.py "BrandFontName" --weight 700   # -> assets/fonts/...

# 1. Author brands/<slug>/slides.json  (see examples/slides.example.json)
#    Put the palette in brand.colors and the font in brand.font_file

# 2. Render text-free backgrounds in parallel via OpenAI Images
export OPENAI_API_KEY=...     # https://platform.openai.com/api-keys
python3 pipeline/openai_render.py brands/<slug>/slides.json
#   --quality high       sharper slides (slower / costlier)
#   --size 1024x1536     gpt-image-1 sizes: 1024x1024 | 1024x1536 | 1536x1024
#   --concurrency 2      lower if a low-tier key 429s on 6 parallel jobs
#   --mock               no key: write placeholder PNGs to test the flow

# 3. Composite real bold headlines onto the backgrounds
python3 pipeline/compose_text.py brands/<slug>/manifest.json

# 4. Build the gallery
python3 pipeline/build_gallery.py brands/<slug>/manifest.json --open
```

## Try it now without a key

```bash
mkdir -p brands/drift && cp examples/slides.example.json brands/drift/slides.json
python3 pipeline/openai_render.py brands/drift/slides.json --mock
python3 pipeline/compose_text.py brands/drift/manifest.json
python3 pipeline/build_gallery.py brands/drift/manifest.json
open brands/drift/index.html   # or xdg-open / just open the file
```

`--mock` produces solid brand-colored placeholder slides so you can see the
pipeline and gallery work end-to-end. Real renders need `OPENAI_API_KEY`.

## Layout

| Path | What |
|------|------|
| `.claude/skills/carousel/SKILL.md` | the `/carousel` workflow (branded product) |
| `.claude/skills/viral-carousel/SKILL.md` | the `/viral-carousel` workflow (organic faceless) |
| `frameworks/carousel-frameworks.md` | branded carousel frameworks + copy/visual rules |
| `frameworks/viral-carousel-frameworks.md` | viral faceless formats + "found, not made" rules |
| `pipeline/brand_probe.py` | extracts real colors + fonts from the site's CSS |
| `pipeline/get_font.py` | fetches the brand's matched font (variable→static) |
| `pipeline/openai_render.py` | renders text-free backgrounds via OpenAI Images in parallel |
| `pipeline/compose_text.py` | overlays real bold headlines (Poppins SemiBold) with Pillow |
| `pipeline/build_gallery.py` | builds the HTML gallery from the manifest |
| `pipeline/png_writer.py` | zero-dep PNG writer used only for `--mock` |
| `assets/fonts/` | bundled fonts (Poppins, Archivo Black, Anton — OFL) |
| `examples/slides.example.json` | reference branded slides spec |
| `examples/viral.example.json` | reference viral faceless slides spec |
| `brands/<slug>/` | per-brand output (brand.json, slides.json, slides/, index.html) |

## Configuration

| Env var | Purpose |
|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required for real renders) |
| `CAROUSEL_OPENAI_MODEL` | override the image model (default `gpt-image-1`) |
| `CAROUSEL_OPENAI_SIZE` | override the render size (default `1024x1536`) |

Requires Python 3.10+ and **Pillow** (`pip install -r requirements.txt`). Pillow
powers both the exact 1080×1350 crop and the headline compositing in
`compose_text.py`.

### Why typography is composited, not generated

Image models (incl. `gpt-image-1`) render text unreliably — wrong weights,
mangled spelling ("Shop now" → "Shopmow"). So backgrounds are generated
text-free and headlines are drawn afterward with a real font. The result is
crisp, correctly spelled, genuinely bold type. When `gpt-image-2` ("ChatGPT
Images 2.0", ~99% text accuracy) reaches your account you can let the model draw
text directly — but compositing stays the most reliable, controllable path.
