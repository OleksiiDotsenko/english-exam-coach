#!/usr/bin/env python3
"""Generate the plugin's listing icon — a square PNG in the banner's style.

Pure stdlib, like the banner: the PNG is written by hand (zlib + struct), so
there is no imaging library to install. The mark is "EC" in the banner's 5x7
pixel font over a level bar, white on the banner's orange.

Run from the repo root:  python3 tools/make_icon.py
"""

import struct
import zlib
from pathlib import Path

SIZE = 1024
RADIUS = 200                      # corner radius of the rounded square
TOP, BOTTOM = (0xFB, 0x92, 0x3C), (0xC2, 0x41, 0x0C)   # the banner's ramp
WHITE = (255, 255, 255)

FONT = {
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    # A plainer C than the banner's: at icon size its two serif pixels read
    # as stray squares.
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
}
CELL = 64                         # one font pixel
LETTERS_TOP = 200
BAR_TOP, BAR_HEIGHT = 728, 76
BLOCK, GAP, BLOCKS, FILLED = 96, 28, 5, 3
OUTLINE = 10


def shapes():
    """(x0, y0, x1, y1, kind) rectangles drawn over the background."""
    rects = []
    width = (5 + 1 + 5) * CELL
    left = (SIZE - width) // 2
    for index, letter in enumerate("EC"):
        for row, bits in enumerate(FONT[letter]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    x = left + (index * 6 + col) * CELL
                    y = LETTERS_TOP + row * CELL
                    rects.append((x, y, x + CELL, y + CELL, "solid"))
    total = BLOCKS * BLOCK + (BLOCKS - 1) * GAP
    start = (SIZE - total) // 2
    for index in range(BLOCKS):
        x = start + index * (BLOCK + GAP)
        kind = "solid" if index < FILLED else "outline"
        rects.append((x, BAR_TOP, x + BLOCK, BAR_TOP + BAR_HEIGHT, kind))
    return rects


def corner_alpha(x, y):
    """Coverage of the rounded square at a pixel centre, 0..255."""
    cx = min(max(x + 0.5, RADIUS), SIZE - RADIUS)
    cy = min(max(y + 0.5, RADIUS), SIZE - RADIUS)
    distance = ((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2) ** 0.5
    return int(round(255 * min(1.0, max(0.0, RADIUS - distance + 0.5))))


def render():
    rows = []
    for y in range(SIZE):
        t = y / (SIZE - 1)
        base = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        rows.append([base] * SIZE)
    for x0, y0, x1, y1, kind in shapes():
        for y in range(y0, y1):
            row = rows[y]
            for x in range(x0, x1):
                edge = (x - x0 < OUTLINE or x1 - x <= OUTLINE
                        or y - y0 < OUTLINE or y1 - y <= OUTLINE)
                if kind == "solid" or edge:
                    row[x] = WHITE
    data = bytearray()
    for y, row in enumerate(rows):
        data.append(0)                                   # filter: none
        for x, (r, g, b) in enumerate(row):
            data += bytes((r, g, b, corner_alpha(x, y)))
    return bytes(data)


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def build():
    """The icon as PNG bytes — the same every time."""
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(render(), 9))
            + chunk(b"IEND", b""))


def main():
    png = build()
    out = (Path(__file__).resolve().parent.parent / "plugins" / "english-exam-coach"
           / ".claude-plugin" / "icon.png")
    out.write_bytes(png)
    print("wrote %s (%dx%d, %d bytes)" % (out, SIZE, SIZE, len(png)))


if __name__ == "__main__":
    main()
