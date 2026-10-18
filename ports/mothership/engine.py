# Orimbux Mothership - engine: video, input and audio on top of plain SDL2 (via pysdl2).
# Python 3.7+ compatible. Only needs libSDL2 + python3 (audioop) on the console.
import ctypes
import json
import math
import os
import struct
import sys
import threading
import time
import wave
import zlib

try:
    import audioop
except ImportError:  # Python 3.13+ on a PC: pip install audioop-lts
    import audioop_lts as audioop  # noqa

import sdl2

APP = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP, "assets")
W, H = 640, 480
SR = 44100
BUF = 1024  # frames per audio callback (~23 ms); HANGAR > BUFFER AUDIO 512 halves the latency (after a restart)
try:
    if json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))).get("buffer") == 512:
        BUF = 512
except Exception:
    pass
HEADROOM = 0.5  # per-voice pre-gain so several loops can stack without clipping
# running on a computer (Windows / macOS / a Linux desktop) instead of the console: a window, keyboard
# or an Xbox-style pad
PC = sys.platform.startswith("win") or sys.platform == "darwin" or \
    bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

# ------------------------------------------------------------------ palette
C = {
    "void": (7, 6, 26), "deck": (18, 15, 51), "hull": (30, 26, 74), "hullhi": (58, 52, 120),
    "hulllo": (5, 4, 15), "panel": (12, 10, 38), "dim": (76, 71, 133), "muted": (142, 136, 194),
    "soft": (201, 196, 242), "text": (237, 235, 255), "cyan": (60, 242, 255), "violet": (157, 107, 255),
    "orange": (255, 138, 42), "orangehi": (255, 192, 138), "orangelo": (140, 58, 0),
    "green": (124, 255, 138), "alien": (91, 63, 214), "alien2": (70, 48, 176), "white": (255, 255, 255),
    "black": (0, 0, 0), "led": (36, 30, 82), "off": (15, 13, 42),
}


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


# ------------------------------------------------------------------ graphics
def load_frm(path):
    """8-bit frames sharing one palette: FRM1, count, w, h, palette, [len + zlib(indices)]"""
    d = open(path, "rb").read()
    n, w, h = struct.unpack("<BHH", d[4:9])
    pal = d[9:9 + 768]
    rgba = b"".join(pal[i * 3:i * 3 + 3] + b"\xff" for i in range(256))
    off, frames = 9 + 768, []
    for _ in range(n):
        ln = struct.unpack("<I", d[off:off + 4])[0]
        frames.append(d[off + 4:off + 4 + ln])
        off += 4 + ln
    return [w, h, rgba, frames]


def frm_texture(ren, w, h, rgba, z, key=None):
    idx = zlib.decompress(z)
    surf = sdl2.SDL_CreateRGBSurfaceWithFormat(0, w, h, 8, sdl2.SDL_PIXELFORMAT_INDEX8)
    s = surf.contents
    if s.pitch == w:
        ctypes.memmove(s.pixels, idx, w * h)
    else:
        base = ctypes.cast(s.pixels, ctypes.c_void_p).value
        for y in range(h):
            ctypes.memmove(base + y * s.pitch, idx[y * w:(y + 1) * w], w)
    cols = (sdl2.SDL_Color * 256)()
    ctypes.memmove(cols, rgba, 1024)
    sdl2.SDL_SetPaletteColors(s.format.contents.palette, cols, 0, 256)
    if key is not None:
        sdl2.SDL_SetColorKey(surf, 1, key)
    tex = sdl2.SDL_CreateTextureFromSurface(ren, surf)
    sdl2.SDL_FreeSurface(surf)
    if key is not None:
        sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
    return tex


class Font(object):
    def __init__(self, ren, name):
        meta = json.load(open(os.path.join(ASSETS, "fonts", name + ".json")))
        raw = open(os.path.join(ASSETS, "fonts", name + ".rgba"), "rb").read()
        self.h = meta["h"]                       # nominal box (layout height)
        self.top = meta.get("top", 0)            # extra rows above it (accents on capitals)
        self.hf = self.h + self.top
        self.glyphs = meta["glyphs"]
        w, h = meta["w"], len(raw) // (meta["w"] * 4)
        buf = ctypes.create_string_buffer(raw, len(raw))
        surf = sdl2.SDL_CreateRGBSurfaceWithFormatFrom(buf, w, h, 32, w * 4, sdl2.SDL_PIXELFORMAT_ABGR8888)
        self.tex = sdl2.SDL_CreateTextureFromSurface(ren, surf)
        sdl2.SDL_FreeSurface(surf)
        sdl2.SDL_SetTextureBlendMode(self.tex, sdl2.SDL_BLENDMODE_BLEND)
        self._src = sdl2.SDL_Rect()
        self._dst = sdl2.SDL_Rect()

    def width(self, s):
        g = self.glyphs
        return sum(g[c][2] if c in g else g[" "][2] for c in s)


FONT_ALIAS = {  # old name -> (Tiny5 size, y shift)
    "p8": ("k16", -7), "v20": ("k16", 0), "p16": ("kb24", -9), "v28": ("k24", -1), "p24": ("kb32", -11),
    "v44": ("k32", 1), "p40": ("kb48", -15), "v76": ("kb48", 6),
}


class Gfx(object):
    def __init__(self, ren):
        self.ren = ren
        self.fonts = {}
        for n in ("k16", "k24", "k32", "k48", "kb16", "kb24", "kb32", "kb48"):
            self.fonts[n] = Font(ren, n)
        # one typeface for the whole app (Tiny5, the Xeno Pet font). Older font names map to the closest size,
        # shifted so the capitals sit where the old ones did.
        self.alias = dict((k, (self.fonts[f], dy)) for k, (f, dy) in FONT_ALIAS.items())
        for n, f in self.fonts.items():
            self.alias[n] = (f, 0)
        self._r = sdl2.SDL_Rect()
        sdl2.SDL_SetRenderDrawBlendMode(ren, sdl2.SDL_BLENDMODE_BLEND)
        self.scan = self._make_scanlines()
        self.anim = True
        self._art = {}

    def _make_scanlines(self):
        surf = sdl2.SDL_CreateRGBSurfaceWithFormat(0, W, H, 32, sdl2.SDL_PIXELFORMAT_ARGB8888)
        sdl2.SDL_FillRect(surf, None, 0x00000000)
        r = sdl2.SDL_Rect(0, 0, W, 1)
        for y in range(2, H, 3):
            r.y = y
            sdl2.SDL_FillRect(surf, r, 0x46000000)
        tex = sdl2.SDL_CreateTextureFromSurface(self.ren, surf)
        sdl2.SDL_FreeSurface(surf)
        sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
        return tex

    def scanlines(self):
        sdl2.SDL_RenderCopy(self.ren, self.scan, None, None)

    def clear(self, col):
        sdl2.SDL_SetRenderDrawColor(self.ren, col[0], col[1], col[2], 255)
        sdl2.SDL_RenderClear(self.ren)

    def rect(self, x, y, w, h, col, a=255):
        sdl2.SDL_SetRenderDrawColor(self.ren, col[0], col[1], col[2], a)
        r = self._r
        r.x, r.y, r.w, r.h = int(x), int(y), int(w), int(h)
        sdl2.SDL_RenderFillRect(self.ren, r)

    def rects(self, lst, col, a=255):
        """batch fill: lst of (x,y,w,h) - one SDL call"""
        if not lst:
            return
        arr = (sdl2.SDL_Rect * len(lst))(*[sdl2.SDL_Rect(int(x), int(y), int(w), int(h)) for x, y, w, h in lst])
        sdl2.SDL_SetRenderDrawColor(self.ren, col[0], col[1], col[2], a)
        sdl2.SDL_RenderFillRects(self.ren, arr, len(lst))

    def frame(self, x, y, w, h, col, t=2, a=255):
        self.rects([(x, y, w, t), (x, y + h - t, w, t), (x, y, t, h), (x + w - t, y, t, h)], col, a)

    def bevel(self, x, y, w, h, fill, hi, lo, t=3):
        self.rect(x, y, w, h, fill)
        self.rects([(x, y, w, t), (x, y, t, h)], hi)
        self.rects([(x, y + h - t, w, t), (x + w - t, y, t, h)], lo)

    def glow(self, x, y, w, h, col, strength):
        """cheap glow: stacked translucent frames"""
        for i in range(1, 5):
            a = int(90 * strength / i)
            if a > 0:
                self.frame(x - i * 2, y - i * 2, w + i * 4, h + i * 4, col, 2, a)

    def text(self, fname, s, x, y, col, a=255, align="left"):
        f, dy = self.alias[fname]
        y += dy
        s = str(s)
        if align != "left":
            w = f.width(s)
            x = x - (w if align == "right" else w // 2)
        sdl2.SDL_SetTextureColorMod(f.tex, col[0], col[1], col[2])
        sdl2.SDL_SetTextureAlphaMod(f.tex, a)
        src, dst, g = f._src, f._dst, f.glyphs
        x = int(x)
        y = int(y) - f.top
        hf = f.hf
        for ch in s:
            gl = g.get(ch) or g["?"]
            if ch != " ":
                src.x, src.y, src.w, src.h = gl[0], gl[1], gl[2], hf
                dst.x, dst.y, dst.w, dst.h = x, y, gl[2], hf
                sdl2.SDL_RenderCopy(self.ren, f.tex, src, dst)
            x += gl[2]
        return x

    def tw(self, fname, s):
        return self.alias[fname][0].width(str(s))

    # ---- pixel-art sprites (assets/art/*.frm, index 0 transparent), loaded on first use
    def sprite(self, name, frame=0):
        lst = self._art.get(name, 0)
        if lst == 0:
            try:
                w, h, rgba, frames = load_frm(os.path.join(ASSETS, "art", name + ".frm"))
                lst = [(frm_texture(self.ren, w, h, rgba, z, key=0), w, h) for z in frames]
            except Exception:
                lst = None
            self._art[name] = lst
        if not lst:
            return None
        return lst[min(frame, len(lst) - 1)]

    def blit(self, tex, src, dst, a=255):
        """src None = whole texture; rects as (x, y, w, h)"""
        if a < 255:
            sdl2.SDL_SetTextureAlphaMod(tex, max(0, int(a)))
        s = sdl2.SDL_Rect(*[int(v) for v in src]) if src else None
        d = sdl2.SDL_Rect(*[int(v) for v in dst])
        sdl2.SDL_RenderCopy(self.ren, tex, s, d)
        if a < 255:
            sdl2.SDL_SetTextureAlphaMod(tex, 255)

    def art(self, name, x, y, scale=2, a=255, src=None):
        """draws a sprite at an integer scale; returns its drawn size"""
        sp = self.sprite(name)
        if not sp:
            return 0, 0
        tex, w, h = sp
        if src:
            w, h = src[2], src[3]
        self.blit(tex, src, (x, y, w * scale, h * scale), a)
        return w * scale, h * scale

    def th(self, fname):
        return self.alias[fname][0].h

    def tri(self, x, y, n, direction, col):
        """pixel triangle icon inside a (2n x 2n) box; direction up/down/left/right"""
        rs = []
        for i in range(n):
            w = 2 * i + 2
            if direction == "up":
                rs.append((x + n - 1 - i, y + i * 2, w, 2))
            elif direction == "down":
                rs.append((x + i, y + i * 2, 2 * n - 2 * i, 2))
            elif direction == "left":
                rs.append((x + i * 2, y + n - 1 - i, 2, w))
            else:
                rs.append((x + i * 2, y + i, 2, 2 * n - 2 * i))
        self.rects(rs, col)


# ------------------------------------------------------------------ ship sprite (40 x 24 grid)
SHIP = [
    (16, 2, 8, 1, "glass2"), (14, 3, 12, 5, "glass"), (13, 4, 1, 4, "glass2"), (26, 4, 1, 4, "glass2"),
    (14, 3, 1, 1, "glass2"), (25, 3, 1, 1, "glass2"),
    (17, 3, 6, 1, "alien"), (16, 4, 8, 4, "alien"), (17, 8, 6, 1, "alien2"),
    (17, 5, 2, 2, "eye"), (21, 5, 2, 2, "eye"), (18, 5, 1, 1, "spark"), (22, 5, 1, 1, "spark"),
    (8, 8, 24, 1, "hull1"), (4, 9, 32, 1, "hull2"), (2, 10, 36, 2, "hull3"), (4, 12, 32, 1, "hull4"),
    (6, 7, 2, 2, "eye"), (32, 7, 2, 2, "eye"), (5, 8, 1, 1, "eye"), (34, 8, 1, 1, "eye"),
    (12, 13, 16, 1, "hull5"), (15, 14, 10, 1, "thrust"),
]
SHIP_COL = {
    "glass": ((60, 242, 255), 46), "glass2": ((60, 242, 255), 140), "alien": ((91, 63, 214), 255),
    "alien2": ((70, 48, 176), 255), "eye": ((255, 138, 42), 255), "spark": ((255, 243, 230), 255),
    "hull1": ((214, 220, 245), 255), "hull2": ((154, 163, 201), 255), "hull3": ((94, 103, 151), 255),
    "hull4": ((56, 63, 110), 255), "hull5": ((38, 43, 82), 255), "thrust": ((60, 242, 255), 255),
}


RIM_X = [4 + 6 * i for i in range(13)]     # rim light columns on the 80x32 saucer


def draw_ship(g, ox, oy, s, t, beam=0.0, accent=None):
    """the Mothership over the old 40 x 16 footprint (ox, oy, unit s). From s >= 2 it is the 80x32 pixel-art
    saucer at the nearest whole scale (twice the detail of the old grid), with live rim lights."""
    sp = g.sprite("ship") if s >= 2 else None
    if not sp:
        return draw_ship_flat(g, ox, oy, s, t, beam, accent)
    tex, w, h = sp
    k = max(1, int(s / 2.0 + 0.5))
    x0 = int(ox + 20 * s - 40 * k)
    y0 = int(oy + 11 * s - 22 * k)
    g.blit(tex, None, (x0, y0, w * k, h * k))
    ph = int(t * 6)
    on, alt, off = [], [], []
    for i, x in enumerate(RIM_X):
        r = (x0 + x * k, y0 + 22 * k, 2 * k, k)
        m = (i + ph) % 4
        (on if m == 0 else alt if m == 2 else off).append(r)
    g.rects(on, accent or C["orange"])
    g.rects(alt, C["cyan"])
    g.rects(off, (40, 34, 92))
    if int(t * 2) % 2:
        g.rects([(x0 + 39 * k, y0 + 28 * k, 2 * k, k)], (255, 255, 255), 200)
    if beam > 0:
        top = y0 + 30 * k
        hgt = int(20 * s)
        cx = ox + 20 * s
        rs = []
        for i in range(0, hgt, 2):
            half = int(5 * s + (i / float(hgt)) * 9 * s)
            rs.append((cx - half, top + i, 2 * half, 2))
        g.rects(rs, C["cyan"], int(60 * beam))


def draw_ship_flat(g, ox, oy, s, t, beam=0.0, accent=None):
    by_col = {}
    for x, y, w, h, k in SHIP:
        by_col.setdefault(k, []).append((ox + x * s, oy + y * s, w * s, h * s))
    for k, lst in by_col.items():
        col, a = SHIP_COL[k]
        if k == "eye" and accent:
            col = accent
        g.rects(lst, col, a)
    # blinking hull lights
    ph = int(t * 2) % 2
    lights_a = [(ox + x * s, oy + 10 * s, 2 * s, s) for x in (6, 16, 26)]
    lights_b = [(ox + x * s, oy + 10 * s, 2 * s, s) for x in (11, 21, 31)]
    g.rects(lights_a, (accent or C["orange"]) if ph else (94, 103, 151))
    g.rects(lights_b, C["cyan"] if not ph else (94, 103, 151))
    if beam > 0:
        top = oy + 15 * s
        hgt = int(20 * s)
        rs = []
        for i in range(0, hgt, 2):
            half = int(5 * s + (i / float(hgt)) * 9 * s)
            rs.append((ox + 20 * s - half, top + i, 2 * half, 2))
        g.rects(rs, C["cyan"], int(60 * beam))


# ------------------------------------------------------------------ input
DEFAULT_JOY = {"b": 0, "a": 1, "x": 2, "y": 3, "l1": 4, "r1": 5, "l2": 6, "r2": 7, "up": 8, "down": 9,
               "left": 10, "right": 11, "select": 12, "start": 13, "l3": 14, "r3": 15, "fn": 16}
# Xbox-style pads on a PC (XInput): letters as printed on the pad; d-pad = hat, LT/RT = axes 4/5
PC_JOY = {"a": 0, "b": 1, "x": 2, "y": 3, "l1": 4, "r1": 5, "select": 6, "start": 7, "l3": 8, "r3": 9}
KEYS = {
    sdl2.SDLK_UP: "up", sdl2.SDLK_DOWN: "down", sdl2.SDLK_LEFT: "left", sdl2.SDLK_RIGHT: "right",
    sdl2.SDLK_z: "a", sdl2.SDLK_x: "b", sdl2.SDLK_s: "x", sdl2.SDLK_a: "y", sdl2.SDLK_q: "l1",
    sdl2.SDLK_w: "r1", sdl2.SDLK_1: "l2", sdl2.SDLK_2: "r2", sdl2.SDLK_RETURN: "start",
    sdl2.SDLK_BACKSPACE: "select", sdl2.SDLK_RSHIFT: "select", sdl2.SDLK_3: "l3", sdl2.SDLK_4: "r3",
}


class Input(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.held = {}
        self.axes = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}
        self.events = []  # (kind, button)  kind in press/release/repeat
        self.joys = []
        self.last_raw = "-"
        self._rep = {}
        self.quit = False
        self.fs_toggle = False
        self.reload()

    def reload(self):
        m = dict(PC_JOY if PC else DEFAULT_JOY)
        m.update(self.cfg.get("joy_map", {}))
        if self.cfg.get("swap_ab"):
            m["a"], m["b"] = m["b"], m["a"]
            m["x"], m["y"] = m["y"], m["x"]
        self.joy_map = dict((v, k) for k, v in m.items())

    def open_joysticks(self):
        for i in range(sdl2.SDL_NumJoysticks()):
            j = sdl2.SDL_JoystickOpen(i)
            if j:
                self.joys.append(j)

    def _press(self, b):
        if not self.held.get(b):
            self.held[b] = True
            self.events.append(("press", b))
            self._rep[b] = time.time() + 0.35

    def _release(self, b):
        if self.held.get(b):
            self.held[b] = False
            self.events.append(("release", b))
            self._rep.pop(b, None)

    def poll(self):
        self.events = []
        ev = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(ev)):
            t = ev.type
            if t == sdl2.SDL_QUIT:
                self.quit = True
            elif t == sdl2.SDL_KEYDOWN and not ev.key.repeat:
                k = ev.key.keysym.sym
                if k == sdl2.SDLK_ESCAPE:
                    self.quit = True
                elif k == sdl2.SDLK_F11:
                    self.fs_toggle = True
                b = KEYS.get(k)
                if b:
                    self._press(b)
                self.last_raw = "KEY %d" % k
            elif t == sdl2.SDL_KEYUP:
                b = KEYS.get(ev.key.keysym.sym)
                if b:
                    self._release(b)
            elif t == sdl2.SDL_JOYBUTTONDOWN:
                self.last_raw = "BTN %d" % ev.jbutton.button
                b = self.joy_map.get(ev.jbutton.button)
                if b:
                    self._press(b)
            elif t == sdl2.SDL_JOYBUTTONUP:
                b = self.joy_map.get(ev.jbutton.button)
                if b:
                    self._release(b)
            elif t == sdl2.SDL_JOYHATMOTION:
                v = ev.jhat.value
                self.last_raw = "HAT %d" % v
                for bit, b in ((1, "up"), (4, "down"), (8, "left"), (2, "right")):
                    if v & bit:
                        self._press(b)
                    else:
                        self._release(b)
            elif t == sdl2.SDL_JOYAXISMOTION:
                ax = ev.jaxis.axis
                val = ev.jaxis.value / 32767.0
                if abs(val) < 0.18:
                    val = 0.0
                name = {0: "lx", 1: "ly", 2: "rx", 3: "ry"}.get(ax)
                if name:
                    self.axes[name] = max(-1.0, min(1.0, val))
                elif ax in (4, 5):  # some builds expose L2/R2 as axes
                    b = "l2" if ax == 4 else "r2"
                    if val > 0.5:
                        self._press(b)
                    elif val < 0.2:
                        self._release(b)
            elif t == sdl2.SDL_JOYDEVICEADDED and not self.joys:
                self.open_joysticks()
        now = time.time()
        for b, due in list(self._rep.items()):
            if b in ("up", "down", "left", "right") and self.held.get(b) and now >= due:
                self.events.append(("repeat", b))
                self._rep[b] = now + 0.09

    def down(self, b):
        return bool(self.held.get(b))


# ------------------------------------------------------------------ audio helpers
def load_wav(path):
    """any 8/16-bit PCM wav -> 44.1 kHz stereo s16 bytes"""
    wf = wave.open(path, "rb")
    ch, sw, rate, n = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
    data = wf.readframes(n)
    wf.close()
    return to_std(data, ch, sw, rate)


def to_std(data, ch, sw, rate):
    if sw == 1:
        data = audioop.bias(data, 1, -128)
    if sw != 2:
        data = audioop.lin2lin(data, sw, 2)
    if ch == 1:
        data = audioop.tostereo(data, 2, 1, 1)
    elif ch > 2:
        raise ValueError("só mono/estéreo")
    if rate != SR:
        data = audioop.ratecv(data, 2, 2, rate, SR, None)[0]
    return data


def fit(data, frames):
    """resample stereo s16 bytes to exactly `frames` frames (changes speed + pitch, jungle-style)"""
    src = len(data) // 4
    if src == frames or src == 0:
        return data
    out = audioop.ratecv(data, 2, 2, src, frames, None)[0]
    need = frames * 4
    if len(out) < need:
        out += b"\0" * (need - len(out))
    return out[:need]


def same_len(a, b):
    if len(b) < len(a):
        return b + b"\0" * (len(a) - len(b))
    return b[:len(a)]


# ------------------------------------------------------------------ voices
class Voice(object):
    __slots__ = ("key", "group", "data", "dark", "pos", "loop", "gain", "start", "stop", "done")

    def __init__(self, key, group, data, dark=None, loop=False, gain=1.0, start=0):
        self.key, self.group, self.data, self.dark = key, group, data, dark
        self.pos = 0
        self.loop = loop
        self.gain = gain
        self.start = start
        self.stop = None
        self.done = False

    def read(self, clock, n, warp):
        out = bytearray()
        need = n
        if self.start > clock:
            lead = self.start - clock
            if lead >= n:
                return None
            out += b"\0" * (lead * 4)
            need -= lead
        if self.stop is not None:
            allowed = self.stop - (clock + (n - need))
            if allowed <= 0:
                self.done = True
                need = 0
            elif allowed < need:
                need = allowed
                self.done = True
        src = self.dark if (warp and self.dark is not None) else self.data
        total = len(src) // 4
        while need > 0:
            if self.pos >= total:
                if self.loop and total:
                    self.pos = 0
                else:
                    self.done = True
                    break
            take = min(need, total - self.pos)
            out += src[self.pos * 4:(self.pos + take) * 4]
            self.pos += take
            need -= take
        if len(out) < n * 4:
            out += b"\0" * (n * 4 - len(out))
        return bytes(out)


class SynthVoice(object):
    """looped wavetable played at any pitch through audioop.ratecv (streaming)"""

    def __init__(self, note, bright, dark, table_freq):
        self.note = note
        self.tb, self.td = bright, dark
        self.table_freq = table_freq
        self.pos = 0
        self.fb = b""
        self.fd = b""
        self.sb = self.sd = None
        self.rate_key = None
        self.g = 0.0
        self.target = 1.0
        self.done = False
        self.held = True

    def release(self):
        self.target = 0.0
        self.held = False

    def _take(self, m):
        tot = len(self.tb) // 4
        out_b = bytearray()
        out_d = bytearray()
        while m > 0:
            if self.pos >= tot:
                self.pos = 0
            k = min(m, tot - self.pos)
            out_b += self.tb[self.pos * 4:(self.pos + k) * 4]
            out_d += self.td[self.pos * 4:(self.pos + k) * 4]
            self.pos += k
            m -= k
        return bytes(out_b), bytes(out_d)

    def read(self, n, bend, tone):
        freq = 440.0 * 2 ** ((self.note + bend - 69) / 12.0)
        ratio = freq / self.table_freq
        inrate = max(1, int(ratio * 4096))
        if inrate != self.rate_key:
            self.rate_key = inrate
            self.sb = self.sd = None
        while len(self.fb) < n * 4 or len(self.fd) < n * 4:
            m = int(n * ratio) + 16
            b, d = self._take(m)
            ob, self.sb = audioop.ratecv(b, 2, 2, inrate, 4096, self.sb)
            od, self.sd = audioop.ratecv(d, 2, 2, inrate, 4096, self.sd)
            self.fb += ob
            self.fd += od
        b, self.fb = self.fb[:n * 4], self.fb[n * 4:]
        d, self.fd = self.fd[:n * 4], self.fd[n * 4:]
        out = audioop.add(audioop.mul(b, 2, tone), audioop.mul(d, 2, 1.0 - tone), 2)
        g0 = self.g
        if self.target > self.g:
            self.g = min(self.target, self.g + 0.5)
        else:
            self.g = max(0.0, self.g - 0.12)
        gain = (g0 + self.g) * 0.5
        if self.g <= 0.0 and self.target == 0.0:
            self.done = True
        return audioop.mul(out, 2, gain)


class StreamVoice(object):
    """streams a PCM wav from disk (any rate, mono/stereo; converted on the fly), with gain ramps"""

    def __init__(self, path, group="floor"):
        self.path = path
        self.group = group
        self.wf = wave.open(path, "rb")
        self.ch, self.sw, self.rate = self.wf.getnchannels(), self.wf.getsampwidth(), self.wf.getframerate()
        self.std = (self.ch, self.sw, self.rate) == (2, 2, SR)
        self.frames = int(self.wf.getnframes() * SR / float(self.rate))
        self.pend = b""
        self.cv = None
        self.pos = 0
        self.g = 1.0
        self.g_to = 1.0
        self.g_step = 0.0
        self.done = False
        self.paused = False
        self.loop = False
        self.start = 0          # mixer clock at which playback begins (sample-accurate)

    def _raw(self, n):
        if self.std:
            return self.wf.readframes(n)
        while len(self.pend) < n * 4:
            d = self.wf.readframes(int(n * self.rate / float(SR)) + 32)
            if not d:
                break
            if self.sw == 1:
                d = audioop.bias(d, 1, -128)
            if self.sw != 2:
                d = audioop.lin2lin(d, self.sw, 2)
            if self.ch == 1:
                d = audioop.tostereo(d, 2, 1, 1)
            if self.rate != SR:
                d, self.cv = audioop.ratecv(d, 2, 2, self.rate, SR, self.cv)
            self.pend += d
        out, self.pend = self.pend[:n * 4], self.pend[n * 4:]
        return out

    def _wrap(self):
        self.wf.rewind()
        self.pend, self.cv = b"", None

    def seek(self, seconds):
        self.wf.setpos(max(0, min(self.wf.getnframes(), int(seconds * self.rate))))
        self.pend, self.cv = b"", None
        self.pos = int(seconds * SR)

    def fade(self, to, seconds):
        steps = max(1, int(seconds * SR / BUF))
        self.g_to = to
        self.g_step = (to - self.g) / steps

    def read(self, n, clock=None):
        if self.paused or self.done:
            return None
        lead = 0
        if clock is not None and self.start > clock:
            lead = self.start - clock
            if lead >= n:
                return None
        data = self._raw(n - lead)
        self.pos += len(data) // 4
        if len(data) < (n - lead) * 4:
            if self.loop:
                self._wrap()
                data += self._raw(n - lead - len(data) // 4)
                self.pos = len(data) // 4
            if len(data) < (n - lead) * 4:
                data += b"\0" * ((n - lead) * 4 - len(data))
                self.done = not self.loop
        if lead:
            data = b"\0" * (lead * 4) + data
        g0 = self.g
        if self.g_step:
            self.g += self.g_step
            if (self.g_step > 0 and self.g >= self.g_to) or (self.g_step < 0 and self.g <= self.g_to):
                self.g = self.g_to
                self.g_step = 0.0
        if self.g <= 0.0 and self.g_to <= 0.0:
            self.done = True
        return audioop.mul(data, 2, (g0 + self.g) * 0.5)

    def close(self):
        try:
            self.wf.close()
        except Exception:
            pass


class PlaylistVoice(StreamVoice):
    """endless music made of segments (same key and tempo): when one ends the next starts on the very next
    sample, chosen at random but never the same twice in a row"""

    def __init__(self, paths, group="floor"):
        import random
        self.rnd = random.Random()
        self.paths = list(paths)
        self.cur_i = self.rnd.randrange(len(self.paths))
        StreamVoice.__init__(self, self.paths[self.cur_i], group)
        self.loop = True

    def _wrap(self):
        others = [i for i in range(len(self.paths)) if i != self.cur_i] or [self.cur_i]
        self.cur_i = self.rnd.choice(others)
        try:
            self.wf.close()
        except Exception:
            pass
        self.wf = wave.open(self.paths[self.cur_i], "rb")
        fmt = (self.wf.getnchannels(), self.wf.getsampwidth(), self.wf.getframerate())
        if fmt != (self.ch, self.sw, self.rate):
            self.ch, self.sw, self.rate = fmt
            self.std = fmt == (2, 2, SR)
            self.pend, self.cv = b"", None


# ------------------------------------------------------------------ mixer + transport
class Mixer(object):
    def __init__(self):
        self.lock = threading.RLock()
        self.voices = []
        self.synth = []
        self.streams = []
        self.clock = 0
        self.master = 0.8
        self.warp = False
        self.bpm = 174.0
        self.beats_per_bar = 4
        self.anchor_clock = 0
        self.anchor_beat = 0.0
        self.metro = False
        self.metro_div = 1
        self.click_hi = self.click_lo = None
        self.synth_bend = 0.0
        self.synth_tone = 0.7
        self.last = b"\0" * (BUF * 4)
        self.rec = None         # list of rendered chunks while a session is being recorded
        self.dev = 0
        self.ok = False
        self._cb = None
        self._t0 = None

    # ---- transport
    def beat_frames(self):
        return SR * 60.0 / self.bpm

    def beat_at(self, frame):
        return self.anchor_beat + (frame - self.anchor_clock) / self.beat_frames()

    def frame_of_beat(self, b):
        return int(round(self.anchor_clock + (b - self.anchor_beat) * self.beat_frames()))

    def set_bpm(self, bpm):
        with self.lock:
            bpm = max(60.0, min(220.0, float(bpm)))
            self.anchor_beat = self.beat_at(self.clock)
            self.anchor_clock = self.clock
            self.bpm = bpm

    def play_beat(self):
        """beat position of what is currently heard"""
        return self.beat_at(self.clock - (BUF if self.ok else 0))

    def next_boundary(self, quant_beats):
        b = self.beat_at(self.clock)
        nb = math.ceil(b / quant_beats - 1e-6) * quant_beats
        return self.frame_of_beat(nb)

    # ---- voices
    def add(self, v):
        with self.lock:
            self.voices.append(v)

    def find(self, key):
        for v in self.voices:
            if v.key == key and not v.done:
                return v
        return None

    def kill_group(self, group):
        with self.lock:
            self.voices = [v for v in self.voices if v.group != group]

    def kill_key(self, key):
        with self.lock:
            self.voices = [v for v in self.voices if v.key != key]

    def shot(self, key, data, dark=None, group="fx", gain=1.0, choke=True):
        with self.lock:
            if choke:
                self.voices = [v for v in self.voices if v.key != key]
            self.voices.append(Voice(key, group, data, dark, False, gain, self.clock))

    # ---- render
    def render(self, n):
        with self.lock:
            clock = self.clock
            out = b"\0" * (n * 4)
            if self.metro and self.click_hi:
                b0 = self.beat_at(clock) * self.metro_div
                b1 = self.beat_at(clock + n) * self.metro_div
                k = math.ceil(b0 - 1e-9)
                while k < b1:
                    f = self.frame_of_beat(k / float(self.metro_div))
                    accent = (k % (self.beats_per_bar * self.metro_div)) == 0
                    sub = (k % self.metro_div) != 0
                    data = self.click_hi if accent else self.click_lo
                    self.voices.append(Voice("click%d" % k, "metro", data, None, False, 0.6 if sub else 1.3,
                                             max(f, clock)))
                    k += 1
            alive = []
            for v in self.voices:
                ch = v.read(clock, n, self.warp)
                if ch is not None:
                    ch = audioop.mul(ch, 2, v.gain * HEADROOM)
                    out = audioop.add(out, ch, 2)
                if not v.done:
                    alive.append(v)
            self.voices = alive
            if self.synth:
                keep = []
                for s in self.synth:
                    out = audioop.add(out, audioop.mul(s.read(n, self.synth_bend, self.synth_tone), 2, 1.0), 2)
                    if not s.done:
                        keep.append(s)
                self.synth = keep
            if self.streams:
                keep = []
                for s in self.streams:
                    ch = s.read(n, clock)
                    if ch is not None:
                        out = audioop.add(out, audioop.mul(ch, 2, 0.85), 2)
                    if s.done:
                        s.close()
                    else:
                        keep.append(s)
                self.streams = keep
            out = audioop.mul(out, 2, self.master)
            self.last = out
            if self.rec is not None:
                self.rec.append(out)
            self.clock += n
            return out

    def _callback(self, userdata, stream, length):
        try:
            data = self.render(length // 4)
            ctypes.memmove(stream, data, length)
        except Exception as e:  # never let the audio thread die
            ctypes.memset(stream, 0, length)
            try:
                open(os.path.join(APP, "log.txt"), "a").write("audio: %s\n" % ascii(e))
            except Exception:
                pass

    def open(self):
        self._cb = sdl2.SDL_AudioCallback(self._callback)
        want = sdl2.SDL_AudioSpec(SR, sdl2.AUDIO_S16SYS, 2, BUF, self._cb)
        have = sdl2.SDL_AudioSpec(0, 0, 0, 0)
        self.dev = sdl2.SDL_OpenAudioDevice(None, 0, ctypes.byref(want), ctypes.byref(have), 0)
        if self.dev:
            self.ok = True
            sdl2.SDL_PauseAudioDevice(self.dev, 0)
        return self.ok

    def pump(self):
        """no audio device: keep the transport moving in real time"""
        if self.ok:
            return
        now = time.time()
        if self._t0 is None:
            self._t0 = now
        target = int((now - self._t0) * SR)
        while self.clock + BUF <= target:
            self.render(BUF)

    def close(self):
        if self.dev:
            sdl2.SDL_CloseAudioDevice(self.dev)


class SequenceVoice(StreamVoice):
    """several wavs played one after the other with no gap (a mix, or endless music); pos keeps counting
    across files, so pos / SR is the time inside the whole sequence. More paths can be appended while it plays."""

    def __init__(self, paths, group="floor"):
        self.paths = list(paths)
        self.idx = 0
        StreamVoice.__init__(self, self.paths[0], group)

    def _open_next(self):
        try:
            self.wf.close()
        except Exception:
            pass
        self.idx += 1
        self.wf = wave.open(self.paths[self.idx], "rb")
        self.ch, self.sw, self.rate = self.wf.getnchannels(), self.wf.getsampwidth(), self.wf.getframerate()
        self.std = (self.ch, self.sw, self.rate) == (2, 2, SR)
        self.pend, self.cv = b"", None

    def _raw(self, n):
        out = StreamVoice._raw(self, n)
        while len(out) < n * 4 and self.idx + 1 < len(self.paths):
            self._open_next()
            out += StreamVoice._raw(self, n - len(out) // 4)
        return out
