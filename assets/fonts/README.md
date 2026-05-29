# Bundled display fonts

Used by `pipeline/compose_text.py` to render headlines. Both are licensed under
the **SIL Open Font License 1.1** (free for commercial use, including embedding
in generated images).

| Font | Use | Source |
|------|-----|--------|
| `ArchivoBlack-Regular.ttf` | default headline (heavy geometric sans) | https://github.com/google/fonts/tree/main/ofl/archivoblack |
| `Anton-Regular.ttf` | alternate condensed headline | https://github.com/google/fonts/tree/main/ofl/anton |

Full license text: https://openfontlicense.org

To use a different headline font, drop a `.ttf`/`.otf` here and update
`HEADLINE_FONTS` in `pipeline/compose_text.py`.
