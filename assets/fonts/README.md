# Bundled fonts

Used by `pipeline/compose_text.py` to render headlines. All are licensed under
the **SIL Open Font License 1.1** (free for commercial use, including embedding
in generated images).

| Font | Use | Source |
|------|-----|--------|
| `Poppins-SemiBold.ttf` | **default** headline (clean geometric, weight 600) | https://github.com/google/fonts/tree/main/ofl/poppins |
| `Poppins-Bold.ttf` | heavier headline option | https://github.com/google/fonts/tree/main/ofl/poppins |
| `ArchivoBlack-Regular.ttf` | ultra-bold display option | https://github.com/google/fonts/tree/main/ofl/archivoblack |
| `Anton-Regular.ttf` | condensed display option | https://github.com/google/fonts/tree/main/ofl/anton |

Full license text: https://openfontlicense.org

More fonts land here on demand: `pipeline/get_font.py "<family>" --weight 700`
fetches a Google Font and instances it to a static weight (it aliases common
proprietary brand fonts — e.g. Cheltenham→Lora, Calibre→Inter, Gotham→Montserrat).

Set the typeface brand-wide via `font_file` in `brand.json`/`slides.json`, or per
slide via `type.font`. Use **static** weight files (these are) — variable fonts
render at their default Regular instance under Pillow, so they won't look bold.
