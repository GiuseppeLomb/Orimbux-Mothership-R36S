"""The speed-ups give exactly the same result as the code they replaced (kept here as reference copies):
text and rectangles (pixels compared byte for byte).
  python3 tools/perf_equal_test.py [APPDIR]"""
import ctypes
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
import sdl2  # noqa: E402
import engine  # noqa: E402


# ---------------------------------------------------------------- reference copies (v1.9.1)
def ref_rects(g, lst, col, a=255):
    if not lst:
        return
    arr = (sdl2.SDL_Rect * len(lst))(*[sdl2.SDL_Rect(int(x), int(y), int(w), int(h)) for x, y, w, h in lst])
    sdl2.SDL_SetRenderDrawColor(g.ren, col[0], col[1], col[2], a)
    sdl2.SDL_RenderFillRects(g.ren, arr, len(lst))


def ref_text(g, fname, s, x, y, col, a=255, align="left"):
    f, dy = g.alias[fname]
    y += dy
    s = str(s)
    if align != "left":
        w = f.width(s)
        x = x - (w if align == "right" else w // 2)
    sdl2.SDL_SetTextureColorMod(f.tex, col[0], col[1], col[2])
    sdl2.SDL_SetTextureAlphaMod(f.tex, a)
    src, dst, gl_ = sdl2.SDL_Rect(), sdl2.SDL_Rect(), f.glyphs
    x = int(x)
    y = int(y) - f.top
    hf = f.hf
    for ch in s:
        gl = gl_.get(ch) or gl_["?"]
        if ch != " ":
            src.x, src.y, src.w, src.h = gl[0], gl[1], gl[2], hf
            dst.x, dst.y, dst.w, dst.h = x, y, gl[2], hf
            sdl2.SDL_RenderCopy(g.ren, f.tex, src, dst)
        x += gl[2]
    return x


# ---------------------------------------------------------------- the test
sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO)
win = sdl2.SDL_CreateWindow(b"t", 0, 0, 640, 480, sdl2.SDL_WINDOW_SHOWN)
ren = sdl2.SDL_CreateRenderer(win, -1, sdl2.SDL_RENDERER_SOFTWARE)
g = engine.Gfx(ren)


def pixels():
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    return buf.raw


rnd = random.Random(5)
for case in range(40):
    lst = [(rnd.uniform(-20, 640), rnd.uniform(-20, 480), rnd.uniform(0, 90), rnd.uniform(0, 60))
           for _ in range(rnd.randrange(0, 60))] + [(10, 10.9, -3.5, 7)]
    col, a = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)), rnd.choice((255, 160, 40))
    shots = []
    for fn in (lambda: ref_rects(g, lst, col, a), lambda: g.rects(lst, col, a)):
        g.clear((5, 5, 5))
        fn()
        shots.append(pixels())
    assert shots[0] == shots[1], "rects differ (case %d)" % case
print("rects: 40 random batches, identical pixels")

texts = ["Começa aqui: escolhe a velocidade (BPM).", "♪ ▶ ✓ ★ ç ã é Ω « » € …", 12345, "", "  ", "ÁÉÍÓÚ àèìòù"]
for fname in sorted(g.alias):
    for k, s in enumerate(texts):
        for align in ("left", "center", "right"):
            x, y = rnd.uniform(0, 600), rnd.uniform(0, 440)
            col, a = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)), rnd.choice((255, 120))
            res = []
            for fn in (ref_text, engine.Gfx.text):
                g.clear((5, 5, 5))
                end = fn(g, fname, s, x, y, col, a, align)
                res.append((end, pixels()))
            assert res[0] == res[1], "text differs: %s %r %s" % (fname, s, align)
print("text: every font, %d strings x 3 alignments, identical pixels and return values" % len(texts))

# ---- ui: key glyphs, line breaks and shortened texts come from a cache, with the same results
import help as helpmod  # noqa: E402
import ui  # noqa: E402
specs = set()
for h in helpmod.HELP.values():
    specs.update(k for k, _ in h[3])
specs.update(("START", "SELECT", "L1/R1", "SEL+X", "esq/dir", "setas + X/Y/A/B", "analogico esq.", "R2+L1/R1"))
for spec in sorted(specs):
    first = ui.tokens(spec)
    assert first == tuple(ui._tokens(spec)) == ui.tokens(spec), spec
words = [h[1] for h in helpmod.HELP.values()] + [t for h in helpmod.HELP.values() for t in h[4]]
for s in words:
    for font in (ui.SMALL, ui.BODY, ui.HEAD):
        for w in (120, 300, 560):
            lines = ui.wrap(g, font, s, w)
            assert lines == ui._wrap(g, font, s, w)
            lines.append("changed by the caller")          # a caller changing its copy never reaches the cache
            assert ui.wrap(g, font, s, w) == ui._wrap(g, font, s, w)
            assert ui.fit(g, font, s, w) == ui._fit(g, font, s, w) == ui.fit(g, font, s, w)
print("ui: %d key specs, %d texts: cached glyphs, line breaks and shortened texts are the same" % (
    len(specs), len(words)))

# ---- Void Runner: the onsets of a frame, found by bisection, are the ones the old filter found
import glob  # noqa: E402
import songscan  # noqa: E402


def ref_onsets(tl, t0, t1):
    return [o for o in tl.on if t0 < o[0] <= t1]


songs = sorted(glob.glob(os.path.join(APPD, "assets", "bd", "*.wav")))
tl = songscan.Timeline()
for p in songs:
    tl.add(songscan.scan_file(p))
assert tl.ordered and len(tl.on) > 500
frames = 0
for _ in range(3000):
    t0 = rnd.uniform(-1, tl.dur + 1)
    t1 = t0 + rnd.choice((0.0, 1 / 30.0, 1 / 20.0, 0.5, 3.0))
    assert tl.onsets(t0, t1) == ref_onsets(tl, t0, t1)
    frames += 1
for o in tl.on[:200]:                                   # windows that end or start exactly on an onset
    for t0, t1 in ((o[0], o[0] + 0.03), (o[0] - 0.03, o[0])):
        assert tl.onsets(t0, t1) == ref_onsets(tl, t0, t1)
odd = songscan.Timeline()                               # out of order: the old filter is used
odd.add({"dur": 2.0, "env": [0.1] * 80, "on": [[0.5, 1.0], [1.99, 0.5]]})
odd.on.insert(0, [1.5, 0.2])
odd.on_t.insert(0, 1.5)
odd.ordered = False
assert odd.onsets(0.0, 2.0) == [[1.5, 0.2], [0.5, 1.0], [1.99, 0.5]]
print("Void Runner onsets: %d windows over %d onsets, the same as the old filter" % (frames, len(tl.on)))

# ---- mixer: skipping a multiplication by exactly 1.0 gives the same bytes (every 16-bit value is checked)
import struct  # noqa: E402
every = struct.pack("<65536h", *range(-32768, 32768))
assert engine.audioop.mul(every, 2, 1.0) == every == engine.scale(every, 1.0)
for k in (0.0, 0.5, 0.85, 1.3, 2.0, 0.999999):
    assert engine.scale(every, k) == engine.audioop.mul(every, 2, k)
print("mixer: times 1.0 is the identity for all 65536 sample values; other gains still multiply")
print("ok")
