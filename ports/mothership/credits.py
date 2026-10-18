# CREDITOS - an opening line, the logo flying away, then the text crawling into the stars in perspective.
# The crawl is drawn once into a tall texture; every frame it is copied in thin strips, each strip a little
# narrower the higher it is on screen (a floor plane seen from a low angle, gentle enough to stay readable).
import os
import random
import time

import sdl2

import engine
import trailer
from engine import C, W, H, SR, StreamVoice, draw_ship

D = os.path.join(engine.ASSETS, "trailer")
VERSION = "v1.9"
GOLD = (255, 214, 80)
OPENER = ["Num cartão microSD,", "dentro de uma consola de bolso..."]
CRAWL = [
    ("title", "CAPÍTULO 1.9"),
    ("title", "A NAVE DAS APPS"),
    ("gap", ""),
    ("p", "Uma pequena consola vagueia pelo espaço. Dentro dela, uma nave-mãe guarda doze módulos de música "
          "e jogos, prontos para quem os quiser pilotar."),
    ("gap", ""),
    ("p", "Ritmos são forjados, loops reagem ao vivo, vozes atravessam nebulosas e as músicas misturam-se "
          "em dois decks."),
    ("gap", ""),
    ("p", "Enquanto o Xeno Pet dorme, os pilotos sobem até ao disco de ouro e fogem de um grave gigante que "
          "devora tudo pelo caminho."),
    ("gap", ""),
    ("p", "Esta é a tripulação que a pôs a voar..."),
    ("gap", ""), ("gap", ""),
    ("role", "CRIAÇÃO E DIREÇÃO"), ("name", "ORIMBUX"),
    ("role", "PILOTO DE TESTES"), ("name", "ORIMBUX"),
    ("role", "MÓDULOS DE MÚSICA"), ("name", "PULSAR · BEAT FORGE"), ("name", "ABDUCTOR · LOOP REACTOR"),
    ("name", "XENO SYNTH · VOX NEBULA"), ("name", "TWIN DECKS · WARP FLOOR"),
    ("role", "MÓDULOS DE JOGO"), ("name", "XENO PET · SOM DE OURO"), ("name", "VOID RUNNER · BEAT DUEL"),
    ("role", "MÚSICA ORIGINAL"), ("name", "NEON DRIFT · PIXEL RUSH"), ("name", "VOID BASS · MOON HOP"),
    ("name", "MOTHERSHIP ANTHEM"), ("name", "Tema do trailer e tema dos créditos"),
    ("role", "SONS"), ("name", "Samples do Sonic Pi (CC0)"), ("name", "com doações de The Black Dog"),
    ("name", "e Arovane"),
    ("role", "ARTE"), ("name", "Pixel art desenhada em código"),
    ("role", "LETRA"), ("name", "Tiny5 (SIL Open Font License)"),
    ("role", "MOTOR"), ("name", "Python + SDL2 (pysdl2)"),
    ("role", "CHIP TRACKER"), ("name", "LittleGPTracker (open source)"), ("name", "instalado pelo PortMaster"),
    ("role", "SISTEMA"), ("name", "ArkOS na R36S"),
    ("gap", ""), ("gap", ""),
    ("p", "Nenhum alien foi magoado durante a construção desta nave. O Xeno Pet exigiu que isto ficasse escrito."),
    ("gap", ""), ("gap", ""),
    ("title", "OBRIGADO"), ("title", "POR EMBARCARES"),
    ("name", "ORIMBUX MOTHERSHIP " + VERSION),
    ("name", "Orimbux, 2026"),
]
TW = 600                    # crawl texture width (= its width on screen at the bottom edge)
PF = "k32"                  # crawl font
# a gentle floor plane: its horizon sits far above the screen, so the text shrinks slowly and stays
# readable over most of the screen (at mid height it is still ~3/4 size); it fades out near the top
HOR = -320                  # screen y of the (virtual) horizon
TOP = 40                    # first screen row of the crawl
SPAN = float(H - HOR)
DIST = SPAN                 # 1:1 at the bottom edge
FADE = 150                  # rows over which the text fades out at the top
T_LOGO, T_CRAWL, T_END = 5.0, 8.5, 88.0


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Credits(object):
    name = "CREDITOS"

    def __init__(self, app):
        self.app = app
        self.back = "bridge"
        self.stream = None
        self.crawl = None
        self.logo = None
        self.th = 0
        self.t0 = 0.0
        self.force_t = None
        self.scroll = 0.0
        self.speed = 1.0
        self.last = None
        self.stars = []
        self.done_t = None
        self.logo_w = 440

    # ------------------------------------------------------------ build the textures once per visit
    def layout(self, g):
        rows = []
        for kind, s in CRAWL:
            if kind == "p":
                words, line = s.split(), []
                for w in words:
                    if line and g.tw(PF, " ".join(line + [w])) > TW - 40:
                        rows.append(("pj", line))
                        line = [w]
                    else:
                        line.append(w)
                rows.append(("pl", line))
            else:
                rows.append((kind, s))
        h = {"pj": 44, "pl": 44, "title": 64, "gap": 36, "role": 52, "name": 42}
        return rows, sum(h[k] for k, _ in rows) + 20, h

    def target(self, w, h):
        tex = sdl2.SDL_CreateTexture(self.app.ren, sdl2.SDL_PIXELFORMAT_ARGB8888, sdl2.SDL_TEXTUREACCESS_TARGET, w, h)
        if not tex:
            return None
        sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
        sdl2.SDL_SetRenderTarget(self.app.ren, tex)
        sdl2.SDL_SetRenderDrawColor(self.app.ren, 0, 0, 0, 0)
        sdl2.SDL_RenderClear(self.app.ren)
        return tex

    def draw_rows(self, g, rows, hmap, x0, y0):
        y = y0
        for kind, s in rows:
            if kind in ("pj", "pl"):                 # paragraph lines, centred
                g.text(PF, " ".join(s), x0 + TW // 2, y, GOLD, 255, "center")
            elif kind == "title":
                g.text("kb48", s, x0 + TW // 2, y + 2, GOLD, 255, "center")
            elif kind == "role":
                g.text("kb24", s, x0 + TW // 2, y + 18, C["orange"], 255, "center")
            elif kind == "name":
                g.text(PF, s, x0 + TW // 2, y, (240, 236, 255), 255, "center")
            y += hmap[kind]

    def build(self):
        g, ren = self.app.g, self.app.ren
        self.rows, self.th, self.hmap = self.layout(g)
        self.crawl = None
        if sdl2.SDL_RenderTargetSupported(ren):
            self.crawl = self.target(TW, self.th)
            if self.crawl:
                self.draw_rows(g, self.rows, self.hmap, 0, 10)
            sdl2.SDL_SetRenderTarget(ren, None)
            small = trailer.make_logo(self.app)
            # as wide as the logo really is (a fixed width cut its first and last letters)
            lw = (small[2] * trailer.LOGO_SCALE if small else g.tw("kb48", "ORIMBUX")) + 16
            lw = max(lw, g.tw("kb24", "M O T H E R S H I P") + 16)
            self.logo_w = lw
            self.logo = self.target(lw, 124)
            if self.logo:
                trailer.draw_logo(g, small, lw // 2, 4, 0.0)
                g.text("kb24", "M O T H E R S H I P", lw // 2, 92, C["orange"], 255, "center")
            sdl2.SDL_SetRenderTarget(ren, None)
            if small:
                sdl2.SDL_DestroyTexture(small[0])
                sdl2.SDL_DestroyTexture(small[1])

    # ------------------------------------------------------------ lifecycle
    def enter(self):
        self.build()
        rnd = random.Random(5)
        self.stars = [(rnd.randrange(W), rnd.randrange(H), rnd.choice((1, 1, 1, 2, 2, 3))) for _ in range(170)]
        m = self.app.mixer
        with m.lock:
            m.kill_group("reactor")
            for s in m.streams:
                s.fade(0.0, 0.4)
        self.stream = None
        if self.force_t is None:
            try:
                self.stream = StreamVoice(os.path.join(D, "credits.wav"), "credits")
                with m.lock:
                    m.streams.append(self.stream)
            except Exception:
                self.stream = None
        self.t0 = time.time()
        self.scroll = DIST - 12.0             # first line just under the bottom edge
        self.neb_x = 0.0
        self.speed = 1.0
        self.last = None
        self.done_t = None

    def leave(self):
        if self.stream:
            self.stream.fade(0.0, 0.5)
            self.stream = None
        for t in (self.crawl, self.logo):
            if t:
                sdl2.SDL_DestroyTexture(t)
        self.crawl = self.logo = None
        self.back = "bridge"

    def exit(self):
        self.app.go(self.back)

    def on(self, kind, b):
        if kind == "press" and b in ("a", "b", "start"):
            self.exit()
        elif kind in ("press", "repeat") and b == "up":
            self.speed = min(4.0, self.speed * 2)
        elif kind in ("press", "repeat") and b == "down":
            self.speed = max(0.25, self.speed / 2)

    def on_select(self):
        self.exit()

    def now(self):
        if self.force_t is not None:
            return self.force_t
        if self.stream is not None and self.app.mixer.ok and not self.stream.done:
            return self.stream.pos / float(SR)
        return time.time() - self.t0

    def gone_at(self):
        """scroll at which the last line has faded out at the top"""
        return self.th + DIST / ((TOP + FADE * 0.6 - HOR) / SPAN)

    def base_speed(self):
        return (self.gone_at() - DIST) / (T_END - T_CRAWL)

    def update(self, dt):
        t = self.now()
        step = (t - self.last) if self.last is not None else 0.0
        self.last = t
        if t > T_CRAWL:
            self.scroll += max(0.0, min(0.2, step)) * self.base_speed() * self.speed
        if self.done_t is None and self.scroll > self.gone_at():
            self.done_t = t
        if self.done_t is not None and t - self.done_t > 6.0:
            self.exit()

    # ------------------------------------------------------------ drawing
    def draw(self, g, tg, dt):
        t = self.now()
        g.clear((2, 1, 8))
        fade_in = ease(t / 1.2)
        g.art("nebula", -int((t * 3) % 80), 0, 2, int(110 * fade_in))
        tw = int(t * 3)
        for i, (x, y, s) in enumerate(self.stars):
            a = 255 if (i + tw) % 23 else 120
            g.rect(x, y, s, s, (200, 200, 235) if s < 3 else (255, 255, 255), int(a * fade_in))
        # opener
        if 0.8 < t < 5.0:
            a = int(255 * min(ease((t - 0.8) / 0.8), ease((5.0 - t) / 0.8)))
            for i, l in enumerate(OPENER):
                g.text("kb32", l, W // 2, 190 + i * 48, (90, 200, 255), a, "center")
        # logo flying away
        if self.logo and T_LOGO <= t < T_LOGO + 7.0:
            k = (t - T_LOGO) / 7.0
            sc = min(2.4, (W - 24.0) / self.logo_w) * (1 - k) ** 2.2 + 0.01
            w, h = self.logo_w * sc, 124 * sc
            sdl2.SDL_SetTextureAlphaMod(self.logo, int(255 * min(1.0, k / 0.05, (1 - k) * 4)))
            d = sdl2.SDL_Rect(int(W / 2 - w / 2), int(210 - h / 2), int(w), int(h))
            sdl2.SDL_RenderCopy(self.app.ren, self.logo, None, d)
            sdl2.SDL_SetTextureAlphaMod(self.logo, 255)
        # the crawl
        if t > T_CRAWL:
            if self.crawl:
                self.draw_crawl(g)
            else:
                self.draw_flat(g)
        # the end: the Mothership crosses the stars
        if self.done_t is not None:
            k = (t - self.done_t) / 4.5
            if k < 1:
                s = 3 + int(k * 3)
                draw_ship(g, -160 + k * (W + 320), 330 - k * 230, s, t, 0.4)
            if t - self.done_t > 4.2:
                g.rect(0, 0, W, H, (0, 0, 0), int(255 * min(1.0, (t - self.done_t - 4.2) / 1.6)))
        if t < 1.0:
            g.rect(0, 0, W, H, (0, 0, 0), int(255 * (1 - t)))

    def draw_crawl(self, g):
        ren = self.app.ren
        src, dst = sdl2.SDL_Rect(), sdl2.SDL_Rect()
        for y in range(TOP, H, 2):
            u = (y - HOR) / SPAN
            v = self.scroll - DIST / u
            if v < 0 or v >= self.th:
                continue
            v2 = self.scroll - DIST / ((y + 2 - HOR) / SPAN)
            w = int(TW * u)
            src.x, src.y, src.w, src.h = 0, int(v), TW, max(1, int(v2) - int(v))
            dst.x, dst.y, dst.w, dst.h = W // 2 - w // 2, y, w, 2
            k = (y - TOP) / float(FADE)
            sdl2.SDL_SetTextureAlphaMod(self.crawl, int(255 * ease(k)) if k < 1 else 255)
            sdl2.SDL_RenderCopy(ren, self.crawl, src, dst)
        sdl2.SDL_SetTextureAlphaMod(self.crawl, 255)

    def draw_flat(self, g):
        """renderers without texture targets: a straight scroll"""
        y = int(H - (self.scroll - DIST) * 0.9)
        self.draw_rows(g, self.rows, self.hmap, (W - TW) // 2, y)
