#!/usr/bin/env python3
"""Generate assets/banner.svg — the orange pixel-art README banner.

Pure stdlib. The title is drawn as real pixel rects from a tiny 5x7 bitmap
font, so it renders identically everywhere (no webfonts inside <img> SVGs).
Run from the repo root:  python3 tools/make_banner.py
"""

from pathlib import Path

FONT = {
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "N": ["10001", "11001", "11001", "10101", "10011", "10011", "10001"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "S": ["01110", "10001", "10000", "01110", "00001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
}

TITLE = "ENGLISH EXAM COACH"
SCALE = 8          # px per pixel-cell
PAD = 2            # cells of padding around everything
LETTER_GAP = 1     # cells between letters
SPACE_ADV = 4      # cells consumed by a space

# Orange ramp, light -> deep, interpolated across the title.
RAMP = [(0xFD, 0xBA, 0x74), (0xF9, 0x73, 0x16), (0xC2, 0x41, 0x0C)]


def ramp_color(t):
    """t in [0,1] -> hex color along the 3-stop orange ramp."""
    seg, local = (0, t * 2) if t <= 0.5 else (1, (t - 0.5) * 2)
    a, b = RAMP[seg], RAMP[seg + 1]
    return "#%02X%02X%02X" % tuple(
        round(a[i] + (b[i] - a[i]) * local) for i in range(3))


def main():
    letters = [c for c in TITLE if c != " "]
    rects, cursor = [], PAD
    li = 0
    for ch in TITLE:
        if ch == " ":
            cursor += SPACE_ADV
            continue
        color = ramp_color(li / max(len(letters) - 1, 1))
        for row, bits in enumerate(FONT[ch]):
            for col, bit in enumerate(bits):
                if bit == "1":
                    rects.append(
                        '<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                        % ((cursor + col) * SCALE, (PAD + row) * SCALE,
                           SCALE, SCALE, color))
        cursor += 5 + LETTER_GAP
        li += 1
    width_cells = cursor - LETTER_GAP + PAD

    # XP bar: B1 ▮▮▮▮▮▮▮▮▮▯▯▯▯▯ C2 — 14 blocks, 9 filled.
    bar_y = (PAD + 7 + 2) * SCALE
    block_w, block_h, gap = 5 * SCALE, 4 * SCALE, 2 * SCALE
    n_blocks, n_filled = 14, 9
    bar_total = n_blocks * block_w + (n_blocks - 1) * gap
    bar_x = (width_cells * SCALE - bar_total) // 2
    bar = []
    for i in range(n_blocks):
        x = bar_x + i * (block_w + gap)
        if i < n_filled:
            bar.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                       % (x, bar_y, block_w, block_h,
                          ramp_color(i / (n_blocks - 1))))
        else:
            bar.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
                       'stroke="#F97316" stroke-width="2"/>'
                       % (x + 1, bar_y + 1, block_w - 2, block_h - 2))
    mono = 'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"'
    label_style = '%s font-size="%d" fill="#9CA3AF"' % (mono, 2 * SCALE)
    bar.append('<text x="%d" y="%d" text-anchor="end" %s>B1</text>'
               % (bar_x - gap, bar_y + block_h - SCALE, label_style))
    bar.append('<text x="%d" y="%d" %s>C2</text>'
               % (bar_x + bar_total + gap, bar_y + block_h - SCALE, label_style))

    sub_y = bar_y + block_h + 4 * SCALE
    sub_style = '%s font-size="%d" fill="#9CA3AF"' % (mono, round(1.75 * SCALE))
    subtitle = ('<text x="%d" y="%d" text-anchor="middle" %s>'
                'Level up your English inside Claude Code — IELTS &#183; '
                'TOEFL iBT &#183; CEFR B1&#8211;C2</text>'
                % (width_cells * SCALE / 2, sub_y, sub_style))

    height = sub_y + 2 * SCALE
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
           'role="img" aria-label="English Exam Coach">\n%s\n%s\n%s\n</svg>\n'
           % (width_cells * SCALE, height,
              "\n".join(rects), "\n".join(bar), subtitle))

    out = Path(__file__).resolve().parent.parent / "assets" / "banner.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print("wrote %s (%d bytes, %d rects)" % (out, len(svg), len(rects)))


if __name__ == "__main__":
    main()
