#!/usr/bin/env python3
"""Download a Google Font and produce a static TTF in assets/fonts/ to composite.

Brands' exact licensed fonts often aren't redistributable, so the workflow is:
identify the brand's font (or its style category) and fetch the closest open
match here. Pulls font files from the google/fonts GitHub repo via raw URLs
(the API is firewalled), and — since most families ship as *variable* fonts —
instances them to the requested weight with fontTools so Pillow gets a clean
static TTF.

Usage:
    python3 pipeline/get_font.py "Poppins" --weight 600
    python3 pipeline/get_font.py "Cheltenham" --weight 700   # aliased -> open serif
    python3 pipeline/get_font.py "Space Grotesk" --weight 600

Prints the saved filename (relative to assets/fonts/) on success, to set as a
slide's type.font or the brand-level font_file.
"""
from __future__ import annotations

import argparse
import io
import sys
import urllib.error
import urllib.request
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
RAW = "https://github.com/google/fonts/raw/main"
UA = "carousel-skill/1.0"
LICENSE_DIRS = ["ofl", "apache", "ufl"]
WEIGHT_TOKEN = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
                500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold",
                900: "Black"}
VAR_AXES = ["[wght]", "[opsz,wght]", "[wdth,wght]", "[ital,wght]", "[slnt,wght]",
            "[opsz,wdth,wght]", "[opsz,wght,GRAD]", "[wght,YTLC]"]

ALIASES = {
    "gt america": "Inter", "söhne": "Inter", "sohne": "Inter", "neue haas": "Inter",
    "helvetica": "Inter", "helvetica neue": "Inter", "arial": "Inter",
    "graphik": "Inter", "calibre": "Inter", "aktiv grotesk": "Inter",
    "circular": "Poppins", "futura": "Poppins", "avenir": "Nunito Sans",
    "gotham": "Montserrat", "proxima nova": "Montserrat", "brandon": "Montserrat",
    "founders grotesk": "Space Grotesk",
    "cheltenham": "Lora", "tiempos": "Lora", "georgia": "Lora",
    "canela": "Playfair Display", "times": "PT Serif", "garamond": "EB Garamond",
    "freight": "Libre Baskerville",
}


def resolve_family(name: str) -> str:
    return ALIASES.get(name.strip().lower(), name.strip())


def try_download(path: str) -> bytes | None:
    url = f"{RAW}/{urllib.request.quote(path)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45.0) as r:
            data = r.read()
        return data if data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf") else None
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def to_static(data: bytes, weight: int) -> bytes:
    """If variable, instance to a fully static TTF at the given weight."""
    from fontTools import ttLib
    from fontTools.varLib import instancer
    f = ttLib.TTFont(io.BytesIO(data))
    if "fvar" not in f:
        return data  # already static
    limits = {a.axisTag: a.defaultValue for a in f["fvar"].axes}
    if "wght" in limits:
        limits["wght"] = weight
    instancer.instantiateVariableFont(f, limits, inplace=True)
    out = io.BytesIO()
    f.save(out)
    return out.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch a Google Font as a static TTF")
    ap.add_argument("family", help="font family (brand font names are aliased to open matches)")
    ap.add_argument("--weight", type=int, default=600)
    args = ap.parse_args()

    family = resolve_family(args.family)
    camel = family.replace(" ", "")
    slug = family.lower().replace(" ", "")
    token = WEIGHT_TOKEN.get(args.weight, "Regular")

    # Candidate paths: static named-weight files first, then variable fonts.
    candidates: list[str] = []
    for lic in LICENSE_DIRS:
        candidates += [f"{lic}/{slug}/static/{camel}-{token}.ttf",
                       f"{lic}/{slug}/{camel}-{token}.ttf"]
    for lic in LICENSE_DIRS:
        candidates += [f"{lic}/{slug}/{camel}{ax}.ttf" for ax in VAR_AXES]

    data = None
    for path in candidates:
        data = try_download(path)
        if data:
            break
    if not data:
        print(f"error: could not find '{family}' in google/fonts (tried static + variable). "
              f"Try a different family name.", file=sys.stderr)
        return 3

    try:
        static = to_static(data, args.weight)
    except Exception as e:  # noqa: BLE001
        print(f"error: failed to instance variable font: {e}", file=sys.stderr)
        return 4

    ASSETS.mkdir(parents=True, exist_ok=True)
    fname = f"{camel}-{token}.ttf"
    dest = ASSETS / fname
    dest.write_bytes(static)
    try:
        from PIL import ImageFont
        ImageFont.truetype(str(dest), 40)
    except Exception as e:  # noqa: BLE001
        dest.unlink(missing_ok=True)
        print(f"error: result is not a usable TTF: {e}", file=sys.stderr)
        return 5

    if family.lower() != args.family.strip().lower():
        print(f"note: '{args.family}' matched to open font '{family}'", file=sys.stderr)
    print(fname)
    return 0


if __name__ == "__main__":
    sys.exit(main())
