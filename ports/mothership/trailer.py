# TRAILER - a 78-second presentation: a signal in the stars, the Mothership jumps in, its logo, the eight
# music apps on the ship's viewscreen (real footage, flipped on the beat), the four games, and the ship
# taking them all home under a final chorus. Runs live on the console; tools/render_trailer.py records
# the same thing to an MP4.
import json
import math
import os
import random
import time

import sdl2

import engine
from engine import C, W, H, SR, StreamVoice, draw_ship, load_frm, frm_texture

D = os.path.join(engine.ASSETS, "trailer")
BEAT = 60.0 / 140.0
BAR = BEAT * 4
# bar map - the same numbers as tools/build_trailer.py
B_APPROACH, B_HYPER, B_LOGO, B_CHM, B_MUSIC, B_CHG, B_GAMES, B_MOSAIC, B_LAUNCH, B_FINAL, B_END = \
    2, 4, 6, 8, 10, 26, 28, 36, 38, 40, 44
END = B_END * BAR + 3.0
VERSION = "v1.9"
GOLD = (255, 214, 80)
PINK = (255, 110, 170)
APPS = [  # file, name, tag, colour (the same as on the bridge), one line
    ("pulsar", "PULSAR", "TEMPO", C["cyan"], "O coração da nave: um tempo para tudo."),
    ("forge", "BEAT FORGE", "RITMO", C["orange"], "Caixa de ritmos: constrói, toca e arranja."),
    ("abductor", "ABDUCTOR", "SONS TEUS", PINK, "Grava a tua voz ou corta músicas em fatias."),
    ("reactor", "LOOP REACTOR", "AO VIVO", C["orange"], "Oito pads de loops, sempre a tempo."),
    ("xeno", "XENO SYNTH", "MELODIA", C["violet"], "Sintetizador alien: nenhuma nota falha."),
    ("vox", "VOX NEBULA", "VOZ", C["cyan"], "A tua voz com efeitos, ao vivo."),
    ("decks", "TWIN DECKS", "MISTURA", C["violet"], "Dois decks para misturar como um DJ."),
    ("warp", "WARP FLOOR", "OUVIR", C["green"], "Ouve as tuas músicas com visuais."),
    ("pet", "XENO PET", "JOGO", PINK, "Um bicho alien que cresce contigo."),
    ("quiz", "SOM DE OURO", "JOGO", GOLD, "Quiz musical: sozinho ou em festa, até 10."),
    ("voidrunner", "VOID RUNNER", "JOGO", C["violet"], "A tua música é o nível: foge do Grave ao ritmo."),
    ("beatduel", "BEAT DUEL", "JOGO", C["cyan"], "Duelo de ritmo, até frente a frente."),
]
VSTART = [B_MUSIC + 2 * i for i in range(8)] + [B_GAMES + 2 * i for i in range(4)]
SEQ = [0, 1, 2, 3, 3, 4, 5, 5]          # footage frame shown on each of the 8 beats of a vignette
WX, WY, WW, WH = 8, 42, 624, 360        # the viewscreen: a 1:1 window onto the 640x480 footage
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
LOGO_BANDS = [(255, 255, 255), (176, 246, 255), (60, 222, 255), (150, 112, 255), (226, 84, 226)]
LOGO_SCALE = 5


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def target(ren, w, h):
    tex = sdl2.SDL_CreateTexture(ren, sdl2.SDL_PIXELFORMAT_ARGB8888, sdl2.SDL_TEXTUREACCESS_TARGET, w, h)
    if not tex:
        return None
    sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
    sdl2.SDL_SetRenderTarget(ren, tex)
    sdl2.SDL_SetRenderDrawColor(ren, 0, 0, 0, 0)
    sdl2.SDL_RenderClear(ren)
    return tex


def make_logo(app):
    """the big ORIMBUX: Tiny5 bold drawn small with a chrome gradient and an extruded shadow, shown at 5x.
    Returns (texture, white texture for the shine, w, h) or None (no render targets)."""
    g, ren = app.g, app.ren
    if not sdl2.SDL_RenderTargetSupported(ren):
        return None
    s = "ORIMBUX"
    w, h = g.tw("kb16", s) + 4, 15
    out = []
    for white in (False, True):
        tex = target(ren, w, h)
        if not tex:
            sdl2.SDL_SetRenderTarget(ren, None)
            return None
        if not white:
            for k, col in ((3, (24, 12, 60)), (2, (66, 36, 140)), (1, (110, 70, 210))):
                g.text("kb16", s, k, -4 + k, col)
        r = sdl2.SDL_Rect(0, 0, w, 2)
        for i, col in enumerate(LOGO_BANDS):
            r.y = 2 + 2 * i
            sdl2.SDL_RenderSetClipRect(ren, r)
            g.text("kb16", s, 0, -4, (255, 255, 255) if white else col)
        sdl2.SDL_RenderSetClipRect(ren, None)
        out.append(tex)
    sdl2.SDL_SetRenderTarget(ren, None)
    return out[0], out[1], w, h


def draw_logo(g, logo, cx, y, t, a=255, glitch=0.0, shine=None):
    """the logo centred on cx; shine 0..1 sweeps a white band across the letters"""
    if not logo:
        g.text("kb48", "ORIMBUX", cx, y, C["cyan"], a, "center")
        return
    tex, white, w, h = logo
    k = LOGO_SCALE
    x0 = int(cx - w * k / 2)
    if glitch > 0:
        dx = int(glitch * 10 * math.sin(t * 90))
        sdl2.SDL_SetTextureColorMod(tex, 255, 60, 200)
        g.blit(tex, None, (x0 - 6 + dx, y, w * k, h * k), int(a * 0.7))
        sdl2.SDL_SetTextureColorMod(tex, 60, 242, 255)
        g.blit(tex, None, (x0 + 6 - dx, y, w * k, h * k), int(a * 0.7))
        sdl2.SDL_SetTextureColorMod(tex, 255, 255, 255)
    g.blit(tex, None, (x0, y, w * k, h * k), a)
    if shine is not None and 0 <= shine <= 1:
        sx = int(-8 + shine * (w + 8))
        for i, (dw, al) in enumerate(((3, 70), (1, 150))):
            lo = max(0, sx + i)
            hi = min(w, sx + i + dw)
            if hi > lo:
                g.blit(white, (lo, 0, hi - lo, h), (x0 + lo * k, y, (hi - lo) * k, h * k), int(al * a / 255))


class Trailer(object):
    name = "TRAILER"

    def __init__(self, app):
        self.app = app
        self.stream = None
        self.t0 = 0.0
        self.force_t = None
        self.files = {}
        self.tex = {}
        self.thumbs = []
        self.stars = []
        self.last = 0.0
        self.logo = None
        self.crops = {}

    # ------------------------------------------------------------ lifecycle
    def enter(self):
        for f, *_ in APPS:
            try:
                self.files[f] = load_frm(os.path.join(D, f + ".frm"))
            except Exception:
                self.files[f] = None
        try:
            self.crops = json.load(open(os.path.join(D, "crops.json")))
        except Exception:
            self.crops = {}
        try:
            w, h, rgba, frames = load_frm(os.path.join(D, "thumbs.frm"))
            self.thumbs = [frm_texture(self.app.ren, w, h, rgba, z) for z in frames]
        except Exception:
            self.thumbs = []
        self.logo = make_logo(self.app)
        rnd = random.Random(3)
        self.stars = [[rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.05, 1.0)] for _ in range(150)]
        m = self.app.mixer
        with m.lock:
            m.kill_group("reactor")
            for s in m.streams:
                s.fade(0.0, 0.4)
        self.stream = None
        if self.force_t is None:
            try:
                self.stream = StreamVoice(os.path.join(D, "trailer.wav"), "trailer")
                with m.lock:
                    m.streams.append(self.stream)
            except Exception:
                self.stream = None
        self.t0 = time.time()
        self.last = 0.0

    def leave(self):
        if self.stream:
            self.stream.fade(0.0, 0.3)
            self.stream = None
        for lst in self.tex.values():
            for t in lst:
                if t:
                    sdl2.SDL_DestroyTexture(t)
        self.tex = {}
        for t in self.thumbs:
            sdl2.SDL_DestroyTexture(t)
        self.thumbs = []
        if self.logo:
            sdl2.SDL_DestroyTexture(self.logo[0])
            sdl2.SDL_DestroyTexture(self.logo[1])
        self.logo = None
        self.files = {}

    def on(self, kind, b):
        if kind == "press" and b in ("b", "start", "a"):
            self.app.go("bridge")

    def on_select(self):
        self.app.go("bridge")

    def now(self):
        if self.force_t is not None:
            return self.force_t
        if self.stream is not None and self.app.mixer.ok:
            return self.stream.pos / float(SR)
        return time.time() - self.t0

    # ------------------------------------------------------------ footage cache: decode ahead, free behind
    def frame_tex(self, vi, k, decode=True):
        f = APPS[vi][0]
        lst = self.tex.setdefault(f, [None] * 6)
        if lst[k] is None and decode and self.files.get(f):
            w, h, rgba, frames = self.files[f]
            lst[k] = frm_texture(self.app.ren, w, h, rgba, frames[min(k, len(frames) - 1)])
        return lst[k]

    def update(self, dt):
        t = self.now()
        if t > END:
            self.app.go("bridge")
            return
        bar = t / BAR
        nxt = [i for i in range(12) if VSTART[i] + 2 > bar][:2]
        budget = 2
        for v in nxt:
            for k in range(6):
                if budget <= 0:
                    break
                if self.tex.get(APPS[v][0], [None] * 6)[k] is None:
                    self.frame_tex(v, k)
                    budget -= 1
        for v in range(12):
            if VSTART[v] + 2 < bar - 0.5:
                f = APPS[v][0]
                for k, tx in enumerate(self.tex.get(f, [])):
                    if tx:
                        sdl2.SDL_DestroyTexture(tx)
                        self.tex[f][k] = None

    # ------------------------------------------------------------ helpers
    def line(self, x1, y1, x2, y2, col, a=255):
        sdl2.SDL_SetRenderDrawColor(self.app.ren, col[0], col[1], col[2], a)
        sdl2.SDL_RenderDrawLine(self.app.ren, int(x1), int(y1), int(x2), int(y2))

    def starfield(self, g, dt, speed, streak=0.0, cx=W / 2, cy=H / 2, a=255):
        near, mid, far, trails = [], [], [], []
        for s in self.stars:
            z0 = s[2]
            s[2] -= dt * speed
            if s[2] <= 0.04:
                s[0], s[1], s[2] = random.uniform(-1, 1), random.uniform(-1, 1), 1.0
                continue
            x, y = cx + s[0] / s[2] * 220, cy + s[1] / s[2] * 220
            if not (0 <= x < W and 0 <= y < H):
                s[2] = 0
                continue
            sz = 3 if s[2] < 0.3 else (2 if s[2] < 0.6 else 1)
            (near if sz == 3 else mid if sz == 2 else far).append((x, y, sz, sz))
            if streak > 0 and s[2] < 0.7:
                px, py = cx + s[0] / (z0 + streak * 0.08) * 220, cy + s[1] / (z0 + streak * 0.08) * 220
                for k in (0.25, 0.5, 0.75):
                    trails.append((x + (px - x) * k, y + (py - y) * k, sz, sz))
        g.rects(far, (110, 100, 170), a)
        g.rects(mid, (190, 185, 235), a)
        g.rects(near, (255, 255, 255), a)
        if trails:
            g.rects(trails, (150, 200, 255), int(a * 0.6))

    def nebula(self, g, t, a=255, speed=5.0):
        pan = (t * speed) % 80
        g.art("nebula", -int(pan), 0, 2, a)

    def typed(self, g, font, s, x, y, el, col, cps=26.0, align="left", a=255):
        """types s out; centred text is laid out at its final place so it does not slide while typing"""
        n = int(max(0.0, el) * cps)
        if n <= 0:
            return
        if align == "center":
            x -= g.tw(font, s) // 2
        elif align == "right":
            x -= g.tw(font, s)
        end = g.text(font, s[:n], x, y, col, a)
        if n < len(s) and int(el * 8) % 2:
            g.rect(end + 2, y + 4, max(4, g.th(font) // 4), g.th(font) - 6, col, a)

    def ship(self, g, cx, cy, scale, t, beam=0.0, a=255):
        """the saucer centred on (cx, cy) at any scale (smooth zooms); whole scales stay pixel-exact"""
        sp = g.sprite("ship")
        if not sp:
            draw_ship(g, cx - 20 * scale, cy - 11 * scale, max(1, int(scale)), t, beam)
            return
        if abs(scale - round(scale)) < 0.02 and scale >= 1:
            k = int(round(scale))
            draw_ship(g, cx - 40 * k, cy - 22 * k, 2 * k, t, beam)
            return
        tex, w, h = sp
        g.blit(tex, None, (cx - w * scale / 2, cy - 22 * scale, w * scale, h * scale), a)

    def corners(self, g, x, y, w, h, col, n=14, t=2, a=255):
        g.rects([(x, y, n, t), (x, y, t, n), (x + w - n, y, n, t), (x + w - t, y, t, n),
                 (x, y + h - t, n, t), (x, y + h - n, t, n), (x + w - n, y + h - t, n, t),
                 (x + w - t, y + h - n, t, n)], col, a)

    def bevel_box(self, g, x, y, w, h, fill, edge, a=255, cut=4):
        g.rects([(x + cut, y, w - 2 * cut, h), (x, y + cut, cut, h - 2 * cut), (x + w - cut, y + cut, cut, h - 2 * cut)],
                fill, a)
        g.rects([(x + cut, y, w - 2 * cut, 2), (x + cut, y + h - 2, w - 2 * cut, 2), (x, y + cut, 2, h - 2 * cut),
                 (x + w - 2, y + cut, 2, h - 2 * cut)], edge, a)
        for i in range(1, cut):
            g.rects([(x + i, y + cut - i, 1, 1), (x + w - 1 - i, y + cut - i, 1, 1),
                     (x + i, y + h - cut + i - 1, 1, 1), (x + w - 1 - i, y + h - cut + i - 1, 1, 1)], edge, a)

    # ------------------------------------------------------------ main
    def draw(self, g, tg, dt):
        t = self.now()
        fdt = max(0.0, min(0.1, t - self.last)) if self.force_t is None else 1 / 30.0
        self.last = t
        g.clear((4, 2, 12))
        bar = t / BAR
        if bar < B_HYPER:
            self.signal(g, t, bar, fdt)
        elif bar < B_LOGO:
            self.hyper(g, t, bar - B_HYPER, fdt)
        elif bar < B_CHM:
            self.logo_scene(g, t, bar - B_LOGO, fdt)
        elif bar < B_MUSIC:
            self.chapter(g, t, bar - B_CHM, True)
        elif bar < B_CHG:
            self.vignette(g, t, bar, fdt)
        elif bar < B_GAMES:
            self.chapter(g, t, bar - B_CHG, False)
        elif bar < B_MOSAIC:
            self.vignette(g, t, bar, fdt)
        elif bar < B_LAUNCH:
            self.mosaic(g, t, bar - B_MOSAIC, fdt)
        elif bar < B_FINAL:
            self.launch(g, t, bar - B_LAUNCH, fdt)
        else:
            self.finale(g, t, bar - B_FINAL, fdt)

    # ------------------------------------------------------------ bars 0-3: a signal in the nebula
    def signal(self, g, t, bar, dt):
        fade = ease(bar / 0.8)
        self.nebula(g, t, int(255 * fade))
        self.starfield(g, dt, 0.05 + 0.03 * bar, a=int(255 * fade))
        g.art("ringed", 470 - int(t * 4), 64, 2, int(255 * fade))
        # the ship comes closer: a dot, then the saucer
        k = ease(bar / 4.0)
        sc = 0.35 + k * 2.65
        cx, cy = W / 2 + math.sin(t * 0.7) * 30 * (1 - k), 210 + math.sin(t * 1.3) * 5
        self.ship(g, cx, cy, sc, t, 0.0)
        # the scanner locks on
        lock = min(1.0, bar / 1.2)
        bw = int(220 - 120 * lock + sc * 40)
        bh = int(120 - 60 * lock + sc * 16)
        col = C["cyan"] if bar < 2 else C["orange"]
        if bar > 0.3:
            self.corners(g, cx - bw // 2, cy - bh // 2 - 4, bw, bh, col, 12, 2, 220)
        # HUD
        self.corners(g, 12, 12, W - 24, H - 24, (60, 80, 140), 26, 2, 200)
        if bar < 2:
            if int(t * 3) % 2:
                g.text("kb24", "SINAL DETETADO", 30, 26, C["cyan"])
        else:
            g.text("kb24", "ALVO IDENTIFICADO", 30, 26, C["orange"])
            if bar > 2.3:
                g.text("k16", "ORIMBUX MOTHERSHIP · 12 MÓDULOS", int(cx), int(cy + bh // 2 + 2), C["orange"], 255,
                       "center")
        g.text("k16", "SETOR %04d.%02d   DIST %05.1f UA" % (int(t * 997) % 9999, int(t * 31) % 99, 999 * (1 - k) + 0.4),
               30, 58, C["dim"])
        # radar
        rx, ry, rr = W - 76, H - 80, 40
        g.rects([(rx + math.cos(i * 0.314) * rr - 1, ry + math.sin(i * 0.314) * rr - 1, 2, 2) for i in range(20)],
                (60, 80, 140))
        ang = t * 3.0
        g.rects([(rx + math.cos(ang) * r - 1, ry + math.sin(ang) * r - 1, 3, 3) for r in range(0, rr, 4)], C["cyan"], 200)
        g.rect(rx + 10, ry - 8, 4, 4, C["orange"] if int(t * 4) % 2 else C["dim"])
        # the story, typed
        if bar < 2:
            self.typed(g, "k24", "Algures entre as estrelas...", W // 2, 380, t - 0.8, C["soft"], 18, "center",
                       int(255 * (1 - ease((bar - 1.75) / 0.25))))
        else:
            self.typed(g, "k24", "...uma nave-mãe guarda 12 apps.", W // 2, 380, t - 2 * BAR - 0.1, C["soft"], 20,
                       "center")

    # ------------------------------------------------------------ bars 4-5: the jump
    def hyper(self, g, t, k, dt):
        self.nebula(g, t, int(255 * max(0.0, 1 - k * 1.2)), 30 + 200 * k)
        self.starfield(g, dt, 0.25 + 1.6 * k, streak=k * 3.5)
        sc = 3 + (k / 2.0) ** 2.4 * 13
        sh = int(k * 5)
        ox, oy = random.randint(-sh, sh), random.randint(-sh, sh)
        self.ship(g, W / 2 + ox, 220 + oy - k * 40, sc, t, min(1.0, k))
        if k < 1.0:
            a = int(255 * (1 - ease((k - 0.75) / 0.25)))
            g.text("kb32", "A SALTAR PARA O", W // 2, 372, C["text"], a, "center")
            g.text("kb32", "HIPERESPAÇO", W // 2, 414, C["text"], a, "center")
        if k > 1.85:
            g.rect(0, 0, W, H, (255, 255, 255), int(255 * (k - 1.85) / 0.15))

    # ------------------------------------------------------------ bars 6-7: the logo over a gas giant
    def logo_scene(self, g, t, k, dt):
        self.starfield(g, dt, 0.12)
        rise = ease(k / 0.6)
        g.art("planet", 0, int(H - 220 * rise + 40), 2)
        bob = math.sin(t * 2.2) * 4
        self.ship(g, W / 2, 86 + bob, 3, t, 0.5 + 0.4 * math.sin(t * 6))
        draw_logo(g, self.logo, W // 2, 160, t, 255, max(0.0, 1 - k * 4), shine=(k - 0.6) / 0.5)
        g.text("kb24", "M O T H E R S H I P", W // 2, 248, C["orange"], int(255 * ease((k - 0.1) * 5)), "center")
        self.typed(g, "k24", "12 apps de música e jogos na tua consola", W // 2, 292, (k - 0.6) * BAR, C["text"], 34,
                   "center")
        if k < 0.12:
            g.rect(0, 0, W, H, (255, 255, 255), int(255 * (1 - k / 0.12)))

    # ------------------------------------------------------------ chapter cards (2 bars): a synthwave horizon
    def chapter(self, g, t, k, music):
        hy = 252
        sky = [(8, 4, 24), (14, 6, 36), (22, 8, 50), (34, 10, 64), (50, 12, 78), (70, 16, 86)] if music else \
            [(4, 8, 24), (6, 14, 36), (8, 22, 50), (10, 34, 64), (12, 50, 78), (16, 70, 86)]
        band = hy // len(sky)
        for i, col in enumerate(sky):
            g.rect(0, i * band, W, band + 1, col)
        self.starfield(g, 1 / 30.0, 0.04, a=150)
        rise = ease(k / 0.5)
        if music:
            g.art("sun", W // 2 - 72, hy - 128 + int((1 - rise) * 80), 2)
        else:
            g.art("ringed", W // 2 - 72, hy - 96 + int((1 - rise) * 60), 2)
        # floor + grid moving towards us on the beat
        g.rect(0, hy, W, H - hy, (10, 4, 26) if music else (4, 10, 26))
        gcol = (255, 60, 200) if music else C["cyan"]
        ph = (t / BEAT) % 1.0
        for i in range(16):
            d = i + 1 - ph
            if d <= 0.05:
                continue
            y = hy + 228.0 / d
            if y > H:
                continue
            a = int(255 * min(1.0, (y - hy) / 60.0))
            g.rect(0, int(y), W, 2 if y > hy + 40 else 1, gcol, a)
        for j in range(-10, 11):
            self.line(W / 2 + j * 14, hy, W / 2 + j * 140, H, gcol, 170)
        g.rect(0, hy, W, 2, gcol)
        # title
        title, sub = ("MÚSICA", "8 apps · um caminho do ritmo à mistura") if music else \
            ("JOGOS", "4 jogos para quando a música faz uma pausa")
        a = int(255 * ease(k / 0.15))
        g.text("kb48", title, W // 2 + 4, 34 + 4, (40, 10, 60), a, "center")
        g.text("kb48", title, W // 2, 34, C["text"], a, "center")
        self.typed(g, "k24", sub, W // 2, 100, k * BAR - 0.25, (255, 214, 240) if music else (200, 255, 250), 40,
                   "center")
        # the items pop in on the beat
        if music:
            items = [(str(i + 1), APPS[i][2], APPS[i][3]) for i in range(8)]
            per, cols, ph_, y0, lf, nf = 1.0, 4, 36, 284, "kb16", "kb24"
        else:
            items = [("▶", APPS[8 + i][1], APPS[8 + i][3]) for i in range(4)]
            per, cols, ph_, y0, lf, nf = 2.0, 2, 44, 286, "kb24", "kb24"
        gap = 8
        beat = k * 4
        # each pill as wide as its label (a fixed grid cut the longer ones), every row centred
        pws = [ph_ + 6 + g.tw(lf, label) + 12 for _, label, _ in items]
        if any(sum(pws[r:r + cols]) + (cols - 1) * gap > W - 16 for r in range(0, len(items), cols)):
            lf = "k16"
            pws = [ph_ + 6 + g.tw(lf, label) + 12 for _, label, _ in items]
        if not music:
            pws = [max(pws)] * len(pws)
        xs = []
        for r in range(0, len(items), cols):
            row = pws[r:r + cols]
            x = W // 2 - (sum(row) + (len(row) - 1) * gap) // 2
            for w_ in row:
                xs.append(x)
                x += w_ + gap
        for i, (num, label, col) in enumerate(items):
            el = beat - i * per
            if el < 0:
                continue
            x, pw = xs[i], pws[i]
            y = y0 + (i // cols) * (ph_ + 10)
            pop = ease(el / 0.4)
            yy = int(y + (1 - pop) * 16)
            a = int(255 * pop)
            self.bevel_box(g, x, yy, pw, ph_, (14, 10, 36), col, int(240 * pop))
            g.rect(x + 4, yy + 4, ph_ - 8, ph_ - 8, col, a)
            g.text(nf, num, x + ph_ // 2, yy + (ph_ - 30) // 2, C["void"], a, "center")
            g.text(lf, label, x + ph_ + 6, yy + (ph_ - g.th(lf)) // 2, C["text"], a)
        # a beginner's hint on the second bar
        if k > 1.25:
            a = int(255 * ease((k - 1.25) / 0.2))
            hint = "START salta para a app seguinte" if music else "SELECT volta sempre à ponte da nave"
            key, rest = hint.split(" ", 1)
            w = g.tw("kb16", key) + 14 + 8 + g.tw("k16", rest)
            x = W // 2 - w // 2
            yy = 412 if music else 404
            self.bevel_box(g, x, yy, g.tw("kb16", key) + 14, 24, (30, 26, 74), C["soft"], a, 3)
            g.text("kb16", key, x + 7, yy + 2, C["text"], a)
            g.text("k16", rest, x + g.tw("kb16", key) + 22, yy + 2, C["soft"], a)
        if k < 0.08:
            g.rect(0, 0, W, H, (255, 255, 255), int(200 * (1 - k / 0.08)))

    # ------------------------------------------------------------ the apps on the viewscreen (2 bars each)
    def crop(self, vi):
        """where the viewscreen sits on app vi's footage: chosen by tools/build_trailer.py so that its edges
        do not slice through words (a moving pan always would)"""
        c = self.crops.get(APPS[vi][0])
        if c:
            return max(0, min(640 - WW, int(c[0]))), max(0, min(480 - WH, int(c[1])))
        return (640 - WW) // 2, 48

    def vignette(self, g, t, bar, dt):
        vi = max(i for i in range(12) if VSTART[i] <= bar)
        lb = bar - VSTART[vi]                    # 0..2 bars into this app
        beat = min(7, int(lb * 4))
        bf = lb * 4 - int(lb * 4)
        f, name, tag, col, line = APPS[vi]
        games = vi >= 8
        self.nebula(g, t, 120, 8)
        self.starfield(g, dt, 0.45, streak=0.5, a=200)
        # top strip
        g.rect(0, 0, W, 32, (8, 6, 22), 235)
        g.rect(0, 32, W, 2, col, 140)
        # ORIMBUX | MÚSICA · 3 DE 8 | ● IMAGEM REAL          (12 steps)
        x = g.text("kb16", "ORIMBUX", 16, 6, C["text"]) + 14
        chap = ("JOGOS · %d DE 4" % (vi - 7)) if games else ("MÚSICA · %d DE 8" % (vi + 1))
        ccol = PINK if games else C["orange"]
        cw = g.tw("kb16", chap) + 16
        self.bevel_box(g, x, 5, cw, 22, ccol, ccol, 255, 3)
        g.text("kb16", chap, x + cw // 2, 6, C["void"], 255, "center")
        x += cw + 14
        if int(t * 2) % 2:
            g.rect(x, 12, 8, 8, (255, 60, 90))
        g.text("k16", "IMAGEM REAL", x + 14, 6, C["muted"])
        for i in range(12):
            x = W - 16 - (12 - i) * 11
            on = i == vi
            g.rect(x, 10 if on else 12, 8, 10 if on else 6, APPS[i][3] if (on or i < vi) else (40, 34, 70),
                   255 if on else (200 if i < vi else 255))
        # the viewscreen
        flash = (1 - bf) if beat in (0, 4) else 0.3 * (1 - bf)
        self.bevel_box(g, WX - 6, WY - 6, WW + 12, WH + 12, (12, 8, 30), col, 255, 6)
        g.glow(WX - 4, WY - 4, WW + 8, WH + 8, col, 0.35 * flash)
        cur = self.frame_tex(vi, SEQ[beat], decode=True)
        sx, sy = self.crop(vi)
        if cur:
            g.blit(cur, (sx, sy, WW, WH), (WX, WY, WW, WH))
        else:
            g.rect(WX, WY, WW, WH, (20, 16, 50))
        # pixel dissolve from the previous app of the same chapter (first 0.3 s)
        el = lb * BAR
        if el < 0.3 and vi > 0 and VSTART[vi - 1] + 2 == VSTART[vi]:
            prev = self.frame_tex(vi - 1, SEQ[7], decode=False)
            if prev:
                k = int(el / 0.3 * 17)
                cell = 32
                px, py0 = self.crop(vi - 1)
                for by in range((WH + cell - 1) // cell):
                    for bx in range((WW + cell - 1) // cell):
                        if BAYER[by % 4][bx % 4] >= k:
                            cw_, ch_ = min(cell, WW - bx * cell), min(cell, WH - by * cell)
                            g.blit(prev, (px + bx * cell, py0 + by * cell, cw_, ch_),
                                   (WX + bx * cell, WY + by * cell, cw_, ch_))
        if el < 0.12:
            g.rect(WX, WY, WW, WH, (255, 255, 255), int(140 * (1 - el / 0.12)))
        # name plate: number tile, the name with what it is for, one line
        py = WY + WH + 12
        ix = ease(el / 0.3)
        a = int(255 * ix)
        tile = 58
        tx = int(16 - (1 - ix) * 100)
        self.bevel_box(g, tx, py + 2, tile, tile, col, col, 255, 5)
        if games:
            g.text("kb32", "▶", tx + tile // 2 + 2, py + 11, C["void"], 255, "center")
        else:
            g.text("kb48", str(vi + 1), tx + tile // 2 + 2, py - 2, C["void"], 255, "center")
        nx = 16 + tile + 12
        g.text("kb32", name, nx + 3, py - 4 + 3, (0, 0, 0), a)
        end = g.text("kb32", name, nx, py - 4, C["text"], a)
        if not games:
            lw = g.tw("kb16", tag) + 16
            if end + 14 + lw <= W - 16:
                self.bevel_box(g, end + 14, py + 4, lw, 24, (14, 10, 36), col, a, 3)
                g.text("kb16", tag, end + 14 + lw // 2, py + 5, col, a, "center")
        fnt = "k24" if g.tw("k24", line) <= W - 16 - nx else "k16"
        self.typed(g, fnt, line, nx, py + 34, el - 0.25, C["soft"], 44)

    # ------------------------------------------------------------ bars 36-37: twelve apps, one ship
    def mosaic(self, g, t, k, dt):
        self.nebula(g, t, 140, 10)
        self.starfield(g, dt, 0.3 + k * 0.4, streak=k * 1.5)
        shipy = -150 + 196 * ease((k - 0.95) / 0.5)
        beam = ease((k - 1.25) / 0.25)
        for i, tx in enumerate(self.thumbs[:12]):
            appear = i * 0.05
            if k < appear:
                continue
            gx, gy = 4 + (i % 4) * 158, 64 + (i // 4) * 136
            pull = ease((k - 1.3 - (11 - i) * 0.03) / 0.45)
            sc = 1 - 0.92 * pull
            pop = min(1.0, (k - appear) / 0.08)
            w, h = 150 * sc * pop, 112 * sc * pop
            cx = gx + 75 + (W / 2 - gx - 75) * pull
            cy = gy + 56 + (shipy + 140 - gy - 56) * pull
            if pull < 0.05:
                self.bevel_box(g, gx - 3, gy - 3, 156, 118, (12, 8, 30), APPS[i][3], 255, 4)
            g.blit(tx, None, (cx - w / 2, cy - h / 2, w, h))
            if pull < 0.05 and pop >= 1.0:
                lw = min(int(w), g.tw("k16", APPS[i][1]) + 10)
                lx, ly = int(cx - w / 2), int(cy + h / 2) - 22
                g.rect(lx, ly, lw, 22, (0, 0, 0), 190)
                g.text("k16", APPS[i][1], lx + lw // 2, ly, C["text"], 255, "center")
        if k < 1.3:
            a = int(255 * ease(k / 0.2))
            g.text("kb32", "12 APPS · 1 NAVE", W // 2, 14, C["text"], a, "center")
        if shipy > -140:
            self.ship(g, W / 2, shipy + 44, 3, t, beam)

    # ------------------------------------------------------------ bars 38-39: the launch
    def launch(self, g, t, k, dt):
        self.starfield(g, dt, 0.4 + 1.8 * k, streak=1 + k * 3)
        sc = max(0.2, 3.0 - 2.7 * ease(k / 1.9))
        y = 200 - 30 * ease(k / 1.9)
        self.ship(g, W / 2, y, sc, t, 0.0)
        if k < 1.6:
            self.typed(g, "kb32", "PRONTO PARA EMBARCAR?", W // 2, 360, k * BAR - 0.2, C["text"], 18, "center",
                       int(255 * (1 - ease((k - 1.4) / 0.2))))
        if k > 1.75:
            g.rect(0, 0, W, H, (255, 255, 255), int(255 * min(1.0, (k - 1.75) / 0.2)))

    # ------------------------------------------------------------ bars 40-44: final chorus, the logo, the end
    def finale(self, g, t, k, dt):
        self.nebula(g, t, 150, 4)
        self.starfield(g, dt, 0.1)
        g.art("planet", 0, H - 180, 2)
        bob = math.sin(t * 2.0) * 4
        self.ship(g, W / 2, 80 + bob, 3, t, 0.6 + 0.3 * math.sin(t * 5))
        draw_logo(g, self.logo, W // 2, 152, t, 255, max(0.0, 1 - k * 5), shine=(k % 1.0) / 0.6)
        g.text("kb24", "M O T H E R S H I P", W // 2, 240, C["orange"], 255, "center")
        lines = ["12 apps de música e jogos", "cria · toca · mistura · joga", "feito para a R36S com ArkOS",
                 "Orimbux powered by Claude"]
        i = min(3, int(k))
        el = (k - i) * BAR
        a = 255 if i == 3 else int(255 * (1 - ease((el - BAR + 0.25) / 0.25)))
        self.typed(g, "k24", lines[i], W // 2, 290, el - 0.05, C["text"] if i < 3 else C["soft"], 40, "center", a)
        g.text("k16", VERSION, W - 20, H - 26, C["muted"], 255, "right")
        if k < 0.1:
            g.rect(0, 0, W, H, (255, 255, 255), int(255 * (1 - k / 0.1)))
        end = (B_END - B_FINAL) + 0.25
        if k > end:
            g.rect(0, 0, W, H, (0, 0, 0), int(255 * min(1.0, (k - end) / 1.2)))
