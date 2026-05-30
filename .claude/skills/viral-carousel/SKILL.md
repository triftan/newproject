---
name: viral-carousel
description: Generate a viral faceless 8-slide Instagram/TikTok carousel in the "found, not made" organic style — candid iPhone-look lifestyle imagery, faceless people, natural light. Picks one of five proven viral formats (non-negotiables, green flags, hear me out, ranked list, before/after), writes a primary hook + standalone slide-2 hook, renders text-free backgrounds via the OpenAI Images API in parallel, composites clean white overlay text, and builds a gallery. Use when the user wants viral/organic faceless carousels, "growth" content, or a TikTok/IG slideshow that looks native rather than like a branded ad. For polished BRANDED product carousels, use the `carousel` skill instead.
---

# Viral faceless carousel generator

Turn **a topic or brand + a vibe** into **8 finished, native-looking
1080×1350 carousel slides** plus an HTML gallery — content engineered to look
**found, not made**: candid, iPhone-shot, faceless, organic. Built for saves,
shares, and comments, not for looking like an ad.

This shares the same Python pipeline as the `carousel` skill (OpenAI Images +
Pillow compositor) — no Higgsfield, no extra services. The difference is the
*aesthetic and the framework*, not the engine.

> When to use which skill:
> - **`viral-carousel`** (this one) → organic growth, faceless lifestyle, looks
>   native. White text, candid photos.
> - **`carousel`** → branded/e-comm product carousel. Brand palette, graphic
>   color-blocked backgrounds, matched brand fonts.

## Inputs to collect
- **Topic / angle** (e.g. "morning routines for focus") OR a **brand URL**.
- **Optional product** to feature *inside* the content (not as a hero shot).
- **Optional `image-refs/` folder** — 8–15 images in the exact visual style you
  want (Pinterest/IG/camera roll). You (Claude) can **Read these images** to
  learn the lighting, grade, camera feel, props, and locations, then write
  prompts that match. By default they are NOT posted and only teach *you* the
  look so your prompts inherit it. **Optionally** you can also hand them to the
  image model itself (see Step 6, `--refs`): the renderer will generate each
  slide through the OpenAI `images/edits` endpoint with the refs attached, so
  the render inherits their look directly — useful when prompt-matching alone
  drifts off the aesthetic.
- Optional: preferred format, slide count (default 8), platform (IG vs TikTok).

If there's no topic and no brand URL, ask for one before proceeding.

## Step 1 — Set up the folder
Slugify the topic/brand. Create `brands/<slug>/`. All artifacts live there.
(The `brands/` folder is reused for both skills; it's just per-project output.)

## Step 2 — Study the look
- If a **brand URL** was given, optionally run `python3 pipeline/brand_probe.py
  <url>` and WebFetch it for audience/voice — but remember the goal is *organic*,
  not on-brand-polished. Pull voice and a loose palette, not a rigid brand kit.
- If an **`image-refs/` folder** exists, **Read several of the images** and write
  down the concrete aesthetic baseline: lighting (natural/window?), color grade
  (warm/muted/filmic?), camera feel (phone/grain?), recurring props, locations,
  framing. Every slide prompt must inherit this.
- Default look when no refs: candid iPhone, soft natural window light, real
  rooms, muted natural grade, slightly imperfect — see the framework doc.

## Step 3 — Pick ONE viral format
Read `frameworks/viral-carousel-frameworks.md`. Choose the single format that
best fits the topic and goal:
- **Non-negotiables** (saves), **Green flags** (DM shares), **Hear me out**
  (comments), **Ranked list** (completion), **Before and after** (engagement).
Decide autonomously — don't make the user pick. State which you chose and why.

## Step 4 — Plan the 8 slides (copy)
Map the format onto 8 slides:
- **Slide 1** — primary hook: specific, < 10 words, one archetype (contrarian /
  listicle promise / transformation tease). No clickbait openers.
- **Slide 2** — **standalone alternate hook**: works on its own (IG re-serves
  from slide 2). Different angle, same promise.
- **Slides 3–7** — one idea each, same format throughout, each stands alone.
- **Slide 8** — soft CTA / save trigger from the framework doc's CTA menu. One
  action. Never "follow for more".

Copy rules (enforce): write like a real person, ≤ 60 chars per overlay, one idea
per slide, NO banned words (unlock, transform, discover, game-changing,
must-have, level up, life-changing, revolutionary, ultimate, secret, hack,
masterclass). If a product appears, it's a natural step in the scene, never a
hero shot.

## Step 5 — Write a TEXT-FREE background prompt per slide
The image model can't spell reliably, so every prompt makes a **text-free
background** and the overlay is composited later (Step 6.5). Each prompt must
bake in the "found, not made" rules from the framework doc:
- natural light only, candid iPhone feel, the studied aesthetic from Step 2,
- **faceless** if a person appears (back of head, hood/cap, hands-only, top-down
  POV, cropped chest-down — never a clear face, never a mirror selfie),
- the product *inside* the scene where relevant (a ritual, not a product photo),
- a clean area (centered or bottom-third — same on all 8) kept clear for text,
- **ABSOLUTELY NO text/words/letters/numbers**, no watermark, no logo, no
  uncanny hands / warped objects / duplicated limbs,
- one consistent grade + light + camera feel across all 8 (vary scene, not vibe).

Give each slide a **`type`** block for the compositor. Native default styling:
```json
{"color": "#ffffff", "align": "center", "valign": "bottom",
 "accent": null, "shadow": true, "font": "Inter-SemiBold.ttf"}
```
Use the **same** `align`/`valign`/`font`/`color` on every slide. `shadow: true`
keeps white type legible over photos without a "designed" box; switch to
`"scrim": true` only for an especially busy background. Set the font brand-wide
via `brand.font_file` so you don't repeat it per slide.

Write `brands/<slug>/slides.json` (see `examples/viral.example.json`):
```json
{
  "brand": {"name": "Topic", "colors": ["#1c1a17", "#c9a27a", "#ffffff"],
            "font_file": "Inter-SemiBold.ttf",
            "voice": "Real, plain, first-person"},
  "product": "(optional) Focus Drops",
  "framework": "Green flags",
  "platform": "instagram",
  "image_size": {"width": 1080, "height": 1350},
  "slides": [
    {"n": 1, "headline": "green flags in a morning routine",
     "type": {"color": "#ffffff", "align": "center", "valign": "bottom",
              "accent": null, "shadow": true},
     "prompt": "<text-free candid iPhone background, bottom third kept clear>"},
    ... 8 total ...
  ]
}
```
For TikTok, set `"platform": "tiktok"` and `image_size` to 1080×1920.

## Step 6 — Render all 8 backgrounds in parallel (OpenAI Images)
```bash
python3 pipeline/openai_render.py brands/<slug>/slides.json
```
- Needs `OPENAI_API_KEY` (https://platform.openai.com/api-keys). `--mock` writes
  placeholders so you can test the flow with no key.
- `gpt-image-1` emits 1024×1024 / 1024×1536 / 1536×1024; the script picks the
  nearest portrait and center-crops to the exact target with Pillow.
- Low-tier keys may 429 on 8 concurrent jobs — re-run (kept renders are skipped)
  or pass `--concurrency 2`.

**Optional — guide renders with reference images.** If you want the *image
model* (not just your prompts) to inherit the look from `image-refs/`, pass them
through:
```bash
python3 pipeline/openai_render.py brands/<slug>/slides.json --refs brands/<slug>/image-refs
```
Slides with references render through the `images/edits` endpoint (gpt-image-1
accepts reference images), so lighting/grade/camera feel carry over directly.
Finer control without a flag: set `reference_images` (a list of file or folder
paths, relative to the spec) at the spec level for all slides, or on an
individual slide to override. `--max-refs` caps how many are sent per slide
(default 4). With no refs anywhere, rendering is unchanged (text-only
`images/generations`). Backgrounds must still stay **text-free** — choose
text-free reference photos too.

Writes `brands/<slug>/slides/slide-N.png` + `manifest.json`.

## Step 6.5 — Composite the overlay text
```bash
python3 pipeline/compose_text.py brands/<slug>/manifest.json
```
White bold Inter, centered, same placement on every slide, soft `shadow` for
legibility. Idempotent — preserves each raw render as `slides/raw-N.png`, so
retuning type is free (no re-render).

## Step 7 — Build the gallery
```bash
python3 pipeline/build_gallery.py brands/<slug>/manifest.json
```
Writes `brands/<slug>/index.html`.

## Step 8 — Review, then deliver
Scan all 8 for misses (uncanny hands, a face slipped in, wrong product, aesthetic
drift, text bleeding into the background) and regenerate ONLY those slides — edit
the prompt and re-run steps 6–6.5 for them. Then hand the user:
- the format you chose and why,
- the slide-by-slide plan with each overlay line,
- the path to `index.html`,
- a native **caption** (3–4 lines, first-person voice, no banned words),
- the **CTA** restated (save / send / comment-keyword).

Publishing note: don't auto-post from a fresh account — it reads as a bot and
risks a shadow-ban. Recommend saving the assets and posting manually from the
phone at peak time (check slide-1 crop, the slide-2 hook, and mobile readability
first).

## Quality bar (definition of done) — do not skip
1. **Looks found, not made** — natural light, candid iPhone texture, consistent
   grade across all 8. No studio/editorial/AI gloss.
2. **Faceless** — any person is shown without a clear face; no mirror selfies.
3. **Slide 2 is a standalone hook**, not a continuation.
4. **One idea per slide**, ≤ 60 chars, zero banned words, real-person voice.
5. **Product is inside the content** (a ritual/step), never a hero shot.
6. **Backgrounds are text-free**; overlay is plain white bold, same placement on
   all 8, legible (shadow/scrim).
7. **Same aspect ratio on every slide** so IG/TikTok doesn't crop inconsistently.
8. **CTA is a real action** (save / send / comment keyword), never "follow for
   more".
9. **Render check** — open 2–3 slides; confirm a face didn't appear, hands look
   right, and the overlay reads on mobile, before reporting done.
