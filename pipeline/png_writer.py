"""Tiny zero-dependency PNG writer used only for --mock placeholder slides.

Real renders come back from the OpenAI Images API as PNGs; this exists so the full
pipeline (render -> manifest -> gallery) can be exercised offline without an
API key or Pillow. It writes a single solid-color image.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (34, 34, 34)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_solid_png(dest: Path, width: int, height: int, color: str) -> None:
    r, g, b = _hex_to_rgb(color)
    row = b"\x00" + bytes((r, g, b)) * width  # filter byte 0 + RGB pixels
    raw = row * height
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    dest.write_bytes(png)
