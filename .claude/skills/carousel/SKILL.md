---
name: carousel
description: Generate a branded 6-slide Instagram carousel from a brand URL + product name. Scrapes the site for brand colors/fonts/voice, writes 6 slide concepts across proven carousel frameworks, renders 1080x1350 slides via the OpenAI Images API in parallel, and builds an HTML gallery. Use when the user wants on-brand IG/social carousel slides, asks to "make a carousel", or gives a brand URL and a product to promote.
---

# Branded IG Carousel Generator

Turn **one brand URL + one product name** into **6 finished, on-brand
1080×1350 Instagram carousel slides** plus an HTML gallery — no Canva, no
designer loop.

You (Claude) do the scraping, brand analysis, concept writing, and prompt
authoring directly. A Python pipeline handles parallel image rendering (OpenAI
Images API) and the gallery. Follow these steps in order.

## Inputs to collect
- **Brand URL** (e.g. `https://acme.com`)
- **Product name** to feature
- Optional: preferred framework, number of slides (default 6), specific angle.

If either required input is missing, ask for it before proceeding.

## Step 1 — Set up the brand folder
Slugify the brand name. Create `brands/<slug>/`. All artifacts live there.

## Step 2 — Scrape & extract the brand kit
Use **WebFetch** on the brand URL (and 1–2 key pages like the product or
about page if helpful). Extract, grounded ONLY in what the site actually says:
- **Colors**: primary, accent, neutrals as hex. Infer from described
  styling/CSS/og-images; pick a coherent 3–5 color palette.
- **Fonts / type feel**: serif vs sans, weight, vibe.
- **Voice & tone**: formal/playful, sentence length, emoji use, signature
  phrases.
- **Positioning**: what they sell, who for, core benefit, differentiators.
- **Product facts** for the named product: real benefits/claims/wording.

Write `brands/<slug>/brand.json`:
```json
{
  "name": "Acme", "url": "https://acme.com",
  "colors": ["#0a0a0a", "#ff4d00", "#f5f1e8", "#1f6feb"],
  "fonts": "Bold geometric sans, tight tracking",
  "voice": "Direct, confident, no emoji, short punchy sentences",
  "positioning": "Premium sleep drops for busy professionals",
  "product_facts": ["Magnesium + L-theanine", "Drug-free", "20-min onset"]
}
```
Never invent prices, stats, or testimonials not present on the site.

## Step 3 — Generate 6 slide concepts
Read `frameworks/carousel-frameworks.md`. Choose ONE framework that best fits
the product and positioning. Map 6 slides onto its beats: slide 1 hook,
slides 2–5 body, slide 6 CTA. Write headlines in the extracted brand voice.

## Step 4 — Write a TEXT-FREE background prompt per slide
The image model is unreliable at rendering text, so we do NOT ask it to draw
the headline. Instead each prompt produces a **text-free background** and the
headline is composited later with a real font (Step 5.5). For each slide author
a rich, self-contained prompt that bakes in:
- the **extracted hex palette** and a wavy/organic color-blocked background,
- **ABSOLUTELY NO text/words/letters/numbers** anywhere in the image,
- a reserved clean **open negative-space area** (usually the top third) where
  the headline will be overlaid,
- product hero where relevant, clean lighting, in the remaining space,
- a consistent layout/identity across all 6 (vary composition, not identity),
- 1080×1350, safe margins, no watermarks, no generic AI gloss.

Also give each slide a **`type`** block telling the compositor how to set the
headline (all fields optional; brand-derived defaults fill the rest):
- `color` (headline hex — dark on light slides, cream on dark slides),
- `align` (`left`|`center`), `valign` (`top`|`center`|`bottom`),
- `accent` (hex of the small rule bar above the headline; null to hide),
- `subline` + `subcolor` (optional small line, e.g. a CTA),
- `max_lines`, `max_width_frac`.

See `examples/slides.example.json` for the exact shape. Write
`brands/<slug>/slides.json`:
```json
{
  "brand": { ...contents of brand.json... },
  "product": "Acme Sleep Drops",
  "framework": "PAS",
  "image_size": {"width": 1080, "height": 1350},
  "slides": [
    {"n": 1, "framework": "Hook", "headline": "Still can't switch off at night?",
     "type": {"color": "#0a0a0a", "align": "left", "valign": "top", "accent": "#ff4d00"},
     "prompt": "<TEXT-FREE background prompt: palette + waves + product, top third left clean>"},
    ... 6 total ...
  ]
}
```

## Step 5 — Render all slides in parallel (OpenAI Images)
The pipeline sends every slide to the OpenAI Images API concurrently and writes
the PNGs.

```bash
python3 pipeline/openai_render.py brands/<slug>/slides.json
```
- Requires `OPENAI_API_KEY` in the environment (https://platform.openai.com/api-keys).
- Model defaults to `gpt-image-1` (override with `--model` or `CAROUSEL_OPENAI_MODEL`).
- `gpt-image-1` only emits 1024x1024 / 1024x1536 / 1536x1024. The script picks
  the nearest portrait size (1024x1536) and, if Pillow is installed,
  center-crops to exactly 1080x1350. Use `--quality high` for sharper slides.
- No key yet? Run `--mock` to produce placeholder slides and verify the flow:
  `python3 pipeline/openai_render.py brands/<slug>/slides.json --mock`

This writes `brands/<slug>/slides/slide-N.png` and `brands/<slug>/manifest.json`.

Rate limits: low-tier OpenAI projects may 429 on 6 concurrent requests. If some
slides fail, re-run (rendered ones are kept) or pass `--concurrency 2`.

## Step 5.5 — Composite the headlines (real typography)
Overlay each slide's headline onto its text-free background with a real bold
font (Archivo Black), pixel-sharp and correctly spelled:
```bash
python3 pipeline/compose_text.py brands/<slug>/manifest.json
```
This preserves each raw render as `slides/raw-N.png` (so it's idempotent) and
writes the final `slides/slide-N.png`. Requires Pillow and the fonts in
`assets/fonts/`.

## Step 6 — Build the gallery
```bash
python3 pipeline/build_gallery.py brands/<slug>/manifest.json
```
Writes `brands/<slug>/index.html` (add `--open` to open a browser locally).

## Step 7 — Report back
Tell the user the folder, how many of 6 slides rendered, any failures, and
the path to `index.html`. Offer one revision pass (e.g. "tighten slide 3's
hook" or "warmer palette") — edit `slides.json` and re-run steps 5–6.

## Notes
- Re-running for a new brand = new `brands/<slug>/` folder, same workflow.
- If a slide fails to render, the others still complete; re-run to retry.
- Keep all 6 prompts visually consistent — same palette, type system, and
  layout language so they read as one carousel.
