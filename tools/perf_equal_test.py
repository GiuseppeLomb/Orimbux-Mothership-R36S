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
print("ok")
