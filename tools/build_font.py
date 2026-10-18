"""Tiny5 (OFL) pixel font atlases for the whole app, with Portuguese accents and a few symbols.
Tiny5 sits on an 8-units-per-em pixel grid: each glyph is rasterised big, sampled once per font pixel
(perfectly crisp) and scaled by an integer: 2x -> k16, 3x -> k24, 4x -> k32, 6x -> k48; bold: kb*.
Accents above capitals live in extra rows *above* the nominal box ("top" in the json), so text drawn at y
keeps the same baseline as before."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ports", "mothership", "assets", "fonts")
SRC = "/home/claude/gf/ofl/tiny5/Tiny5[BLED,JITT,ROND,wdth,wght].ttf"
CHARS = "".join(chr(c) for c in range(32, 127)) + "".join(chr(c) for c in range(160, 256)) + "▶◀▲▼■●○♪♫…–—«»€·✓✗★☆♥←→↑↓"
U = 25


def raster_set(weight):
    font = ImageFont.truetype(SRC, 200)
    font.set_variation_by_axes([weight, 100, 0, 0, 0])
    asc, desc = font.getmetrics()
    ox, oy = 40, 120
    cw, chh = 420, oy + asc + desc + 80

    def raster(ch):
        im = Image.new("L", (cw, chh), 0)
        ImageDraw.Draw(im).text((ox, oy), ch, font=font, fill=255)
        return np.array(im) > 127
    href = raster("H")
    ys, xs = np.where(href)
    px, py = xs.min() % U, ys.min() % U
    rows0 = py + U // 2
    nrows = (chh - rows0) // U
    top_row = (oy - U - rows0) // U               # the old box: one font pixel above the ascender origin
    bot_row = (oy + asc + desc - rows0) // U + 1
    cols0 = px + U // 2 - U * ((px + U // 2 - (ox - U)) // U)
    cells, first = {}, top_row
    for ch in CHARS:
        a = raster(ch)
        adv = int(round(font.getlength(ch) / U))
        rows = []
        for r in range(0, nrows):
            yy = rows0 + r * U
            rows.append([1 if (0 <= cols0 + c * U < cw and a[yy, cols0 + c * U]) else 0 for c in range(adv + 2)])
        cells[ch] = (np.array(rows, dtype=np.uint8), adv)
        nz = np.where(cells[ch][0].any(1))[0]
        if len(nz):
            first = min(first, nz[0])
    extra = (top_row + 1) - first                 # rows above the old box (it started 1 row lower): accents
    out = {}
    for ch, (g, adv) in cells.items():
        out[ch] = (g[first:bot_row], adv)
    return out, extra


def write(name, small, extra, k, track=0):
    """track: extra screen pixels after every glyph (letters were too close at small sizes)"""
    chars = list(small.keys())
    hf = small["H"][0].shape[0] * k
    widths = [small[ch][0].shape[1] * k for ch in chars]
    maxw, x, y, pos = 1024, 0, 0, []
    for wdt in widths:
        if x + wdt + 2 > maxw:
            x, y = 0, y + hf + 2
        pos.append((x, y))
        x += wdt + 2
    img = Image.new("L", (maxw, y + hf), 0)
    glyphs = {}
    for ch, wdt, (gx, gy) in zip(chars, widths, pos):
        g, adv = small[ch]
        img.paste(Image.fromarray(g * 255).resize((g.shape[1] * k, g.shape[0] * k), Image.NEAREST), (gx, gy))
        glyphs[ch] = [int(gx + k), int(gy), int(adv * k + (track if ch != " " else 0))]
    rgba = Image.merge("RGBA", (Image.new("L", img.size, 255),) * 3 + (img,))
    open(os.path.join(OUT, name + ".rgba"), "wb").write(rgba.tobytes())
    json.dump({"w": maxw, "h": int(hf - extra * k), "top": int(extra * k), "glyphs": glyphs},
              open(os.path.join(OUT, name + ".json"), "w"))          # ascii-escaped: safe on any locale


# hand-drawn bold capitals and digits: 5 rows tall, 2-pixel stems (the old automatic bold merged the
# diagonals of N, M, W, V... into blobs). Accents are taken from the regular glyphs and centred on these.
BOLD = {
    "A": [".XXXX.", "XX..XX", "XXXXXX", "XX..XX", "XX..XX"],
    "B": ["XXXXX.", "XX..XX", "XXXXX.", "XX..XX", "XXXXX."],
    "C": [".XXXX", "XX...", "XX...", "XX...", ".XXXX"],
    "D": ["XXXXX.", "XX..XX", "XX..XX", "XX..XX", "XXXXX."],
    "E": ["XXXXX", "XX...", "XXXX.", "XX...", "XXXXX"],
    "F": ["XXXXX", "XX...", "XXXX.", "XX...", "XX..."],
    "G": [".XXXXX", "XX....", "XX.XXX", "XX..XX", ".XXXX."],
    "H": ["XX..XX", "XX..XX", "XXXXXX", "XX..XX", "XX..XX"],
    "I": ["XXXX", ".XX.", ".XX.", ".XX.", "XXXX"],
    "J": ["...XX", "...XX", "...XX", "XX.XX", ".XXX."],
    "K": ["XX..XX", "XX.XX.", "XXXX..", "XX.XX.", "XX..XX"],
    "L": ["XX...", "XX...", "XX...", "XX...", "XXXXX"],
    "M": ["XX...XX", "XXX.XXX", "XX.X.XX", "XX...XX", "XX...XX"],
    "N": ["XX..XX", "XXX.XX", "XX.XXX", "XX..XX", "XX..XX"],
    "O": [".XXXX.", "XX..XX", "XX..XX", "XX..XX", ".XXXX."],
    "P": ["XXXXX.", "XX..XX", "XXXXX.", "XX....", "XX...."],
    "Q": [".XXXX.", "XX..XX", "XX..XX", "XX.XX.", ".XX.XX"],
    "R": ["XXXXX.", "XX..XX", "XXXXX.", "XX.XX.", "XX..XX"],
    "S": [".XXXXX", "XX....", ".XXXX.", "....XX", "XXXXX."],
    "T": ["XXXXXX", "..XX..", "..XX..", "..XX..", "..XX.."],
    "U": ["XX..XX", "XX..XX", "XX..XX", "XX..XX", ".XXXX."],
    "V": ["XX..XX", "XX..XX", "XX..XX", ".XXXX.", "..XX.."],
    "W": ["XX...XX", "XX...XX", "XX.X.XX", "XXX.XXX", "XX...XX"],
    "X": ["XX..XX", ".XXXX.", "..XX..", ".XXXX.", "XX..XX"],
    "Y": ["XX..XX", "XX..XX", ".XXXX.", "..XX..", "..XX.."],
    "Z": ["XXXXXX", "...XX.", "..XX..", ".XX...", "XXXXXX"],
    "0": [".XXX.", "XX.XX", "XX.XX", "XX.XX", ".XXX."],
    "1": [".XX.", "XXX.", ".XX.", ".XX.", "XXXX"],
    "2": ["XXXX.", "...XX", ".XXX.", "XX...", "XXXXX"],
    "3": ["XXXX.", "...XX", ".XXX.", "...XX", "XXXX."],
    "4": ["XX.XX", "XX.XX", "XXXXX", "...XX", "...XX"],
    "5": ["XXXXX", "XX...", "XXXX.", "...XX", "XXXX."],
    "6": [".XXX.", "XX...", "XXXX.", "XX.XX", ".XXX."],
    "7": ["XXXXX", "...XX", "..XX.", ".XX..", ".XX.."],
    "8": [".XXX.", "XX.XX", ".XXX.", "XX.XX", ".XXX."],
    "9": [".XXX.", "XX.XX", ".XXXX", "...XX", ".XXX."],
}
# a few regular glyphs that were hard to tell apart at 3 pixels wide
REGULAR_FIX = {
    "8": [".XX.", "X..X", ".XX.", "X..X", ".XX."],
    "x": ["X.X", ".X.", ".X.", "X.X"],
}
CAP_TOP = 4            # first row of a capital in the small grid (rows 4..8); lowercase x-height rows 5..8


def cell(design, rows, top):
    w = len(design[0])
    g = np.zeros((rows, w + 2), dtype=np.uint8)
    for r, line in enumerate(design):
        for c, v in enumerate(line):
            if v == "X":
                g[top + r, 1 + c] = 1
    return g, w + 1


def fix_regular(small):
    out = dict(small)
    rows = small["H"][0].shape[0]
    for ch, d in REGULAR_FIX.items():
        out[ch] = cell(d, rows, CAP_TOP if len(d) == 5 else CAP_TOP + 1)
    return out


def embolden(small):
    """bold set: the hand-drawn capitals and digits (accented capitals get the regular accent, centred);
    everything else keeps its regular shape"""
    import unicodedata
    rows = small["H"][0].shape[0]
    out = {}
    for ch, (g, adv) in small.items():
        if ch in BOLD:
            out[ch] = cell(BOLD[ch], rows, CAP_TOP)
            continue
        base = unicodedata.normalize("NFD", ch)[0] if ch.isalpha() else ch
        if ch.isupper() and base in BOLD and base != ch:
            b, badv = cell(BOLD[base], rows, CAP_TOP)
            rg, radv = small[base]
            acc = g.copy()
            acc[CAP_TOP:CAP_TOP + 5] &= ~rg[CAP_TOP:CAP_TOP + 5].astype(bool)  # keep only the marks
            if base == "C":                                              # cedilla: keep only below the letter
                acc[:CAP_TOP + 5] = 0
            else:
                acc[CAP_TOP:] = 0
            shift = int(round((badv - radv) / 2.0))
            wide = np.zeros((rows, b.shape[1] + 2), dtype=np.uint8)
            wide[:, :b.shape[1]] = b
            for r in range(rows):
                for c in range(acc.shape[1]):
                    if acc[r, c] and 0 <= c + shift < wide.shape[1]:
                        wide[r, c + shift] = 1
            out[ch] = (wide[:, :b.shape[1]], badv)
            continue
        out[ch] = (g, adv)
    return out


def main():
    base, extra = raster_set(400)
    base = fix_regular(base)
    track = {"k": {16: 1, 24: 1, 32: 1, 48: 2}, "kb": {16: 2, 24: 2, 32: 3, 48: 3}}
    for small, pre in ((base, "k"), (embolden(base), "kb")):
        for sz, k in ((16, 2), (24, 3), (32, 4), (48, 6)):
            write("%s%d" % (pre, sz), small, extra, k, track[pre][sz])
        print(pre, "extra rows", extra, "glyphs", len(small))
    open(os.path.join(OUT, "tiny5-OFL.txt"), "w").write(open("/home/claude/gf/ofl/tiny5/OFL.txt").read())


if __name__ == "__main__":
    main()
