---
name: carousel
description: Generate a branded 6-slide Instagram carousel from a brand URL + product name. Scrapes the site for brand colors/fonts/voice, writes 6 slide concepts across proven carousel frameworks, renders 1080x1350 slides via FAL in parallel, and builds an HTML gallery. Use when the user wants on-brand IG/social carousel slides, asks to "make a carousel", or gives a brand URL and a product to promote.
---

# Branded IG Carousel Generator

Turn **one brand URL + one product name** into **6 finished, on-brand
1080×1350 Instagram carousel slides** plus an HTML gallery — no Canva, no
designer loop.

You (Claude) do the scraping, brand analysis, concept writing, and prompt
authoring directly. A Python pipeline handles parallel image rendering (FAL)
and the gallery. Follow these steps in order.

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

## Step 4 — Write a detailed image prompt per slide
For each slide author a rich, self-contained image prompt that bakes in:
- the exact slide **headline text** to render in the image (in quotes),
- the **extracted hex palette** and a wavy/organic color-blocked background,
- bold typographic treatment, legible at thumbnail size, type in top/center,
- product hero where relevant, clean lighting,
- a consistent layout/identity across all 6 (vary composition, not identity),
- 1080×1350, safe margins, no watermarks, no generic AI gloss.

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
     "prompt": "<full image prompt baking in the headline + palette + style>"},
    ... 6 total ...
  ]
}
```

## Step 5 — Render all slides in parallel (FAL)
The pipeline fires every slide to FAL concurrently and downloads the PNGs.

```bash
python3 pipeline/fal_render.py brands/<slug>/slides.json
```
- Requires `FAL_KEY` in the environment (https://fal.ai/dashboard/keys).
- Override the model with `--model <fal-model-id>` or `CAROUSEL_FAL_MODEL`.
- No key yet? Run `--mock` to produce placeholder slides and verify the flow:
  `python3 pipeline/fal_render.py brands/<slug>/slides.json --mock`

This writes `brands/<slug>/slides/slide-N.png` and `brands/<slug>/manifest.json`.

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
