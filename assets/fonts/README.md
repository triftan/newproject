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

Pick a font per slide via the `type.font` field in `slides.json`, or change the
default order in `DEFAULT_FONTS` in `pipeline/compose_text.py`. Use **static**
weight files (like these) — variable fonts render at their default Regular
instance under Pillow, so they won't look bold.
