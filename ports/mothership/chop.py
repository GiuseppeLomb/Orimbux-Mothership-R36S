# COMET CHOP - the slicer inside ABDUCTOR (works without a mic, on any wav).
# You place the cuts yourself (no automatic analysis): a window divided into 4/8/16 equal slices, every marker
# movable by hand, window length snapped to 1/2/4 bars at the ship's BPM. Slices play on the 8 buttons and can be
# sent to the Loop Reactor (bank CHOP).
import os
import threading
import time
import wave

import engine
from engine import C, W, SR, audioop, load_wav

EXPORT_DIR = os.path.join(engine.APP, "chop")
PADS = ["up", "left", "right", "down", "x", "y", "a", "b"]


def ramp(data):
    """3 ms fade in / 6 ms fade out so cuts never click"""
    n = len(data) // 4
    if n < 600:
        return data
    fi, fo = 128, 256
    head = b"".join(audioop.mul(data[i * 64:(i + 1) * 64], 2, (i + 1) / 9.0) for i in range(8))
    tail = b"".join(audioop.mul(data[(n - fo) * 4 + i * 128:(n - fo) * 4 + (i + 1) * 128], 2, (8 - i) / 9.0)
                    for i in range(8))
    return head + data[fi * 4:(n - fo) * 4] + tail


class Chop(object):
    def __init__(self, app):
        self.app = app
        self.data = None
        self.title = ""
        self.frames = 0
        self.peaks = bytearray()
        self.loading = None
        self.start = 0
        self.end = 0
        self.marks = []           # internal cut points (frames), sorted
        self.n = 8
        self.sel = 0              # 0 = START, 1..n-1 = cuts, n = END
        self.bars = 0
        self.page = 0
        self.choke = True
        self.flash = {}
        self.playing = None       # (slice index, start clock, length)
        self.msg = ("", 0.0)
        self.undo_stack, self.redo_stack = [], []
        self.last_op = (None, 0.0)
        self.lib = []
        self.browse = False
        self.bsel = 0

    def say(self, s):
        self.msg = (s, time.time())

    # ---------------------------------------------------------------- loading
    def load_path(self, path, title):
        self.loading = title
        threading.Thread(target=self._load, args=(path, title), daemon=True).start()

    def _load(self, path, title):
        try:
            wf = wave.open(path, "rb")
            secs = wf.getnframes() / float(wf.getframerate())
            wf.close()
            if secs > 600:
                raise ValueError("ficheiro com mais de 10 minutos")
            data = load_wav(path)
            frames = len(data) // 4
            peaks = bytearray()
            blk = 441 * 4
            for i in range(0, len(data), blk):
                peaks.append(min(255, audioop.max(data[i:i + blk], 2) >> 7))
            self.data, self.frames, self.peaks, self.title = data, frames, peaks, title
            self.start = 0
            self.end = min(frames, int(SR * 2.0 * 60.0 / self.app.mixer.bpm * 4))   # 2 bars to start
            self.bars = 0
            self.divide()
            self.sel = 0
            self.undo_stack, self.redo_stack = [], []
            self.say("Carregado: %s" % title[:30])
        except Exception:
            self.say("Não consegui abrir este ficheiro.")
        self.loading = None

    def open_browser(self):
        import decks
        self.lib = decks.library(self.app)
        self.browse = True
        self.bsel = min(self.bsel, max(0, len(self.lib) - 1))

    def pick(self):
        it = self.lib[self.bsel]
        path = it.get("path")
        if path is None:
            warp = self.app.sections["warp"]
            warp.prepare(it["warp"])
            path = warp.ready.get(it["src"])
            if path is None:
                self.say("A converter... escolhe outra vez daqui a pouco.")
                return
        self.browse = False
        self.load_path(path, it["title"])

    # ---------------------------------------------------------------- slicing
    def divide(self):
        span = self.end - self.start
        self.marks = [self.start + span * k // self.n for k in range(1, self.n)]

    def points(self):
        return [self.start] + self.marks + [self.end]

    def slice_bounds(self, k):
        p = self.points()
        return p[k], p[k + 1]

    # ---- undo / redo (marker edits)
    def snap(self):
        return (self.start, self.end, list(self.marks), self.n, self.bars)

    def change(self, op=None):
        now = time.time()
        if op is None or op != self.last_op[0] or now - self.last_op[1] > 0.8:
            self.undo_stack = (self.undo_stack + [self.snap()])[-40:]
            self.redo_stack = []
        self.last_op = (op, now)

    def _restore(self, st):
        self.start, self.end, marks, self.n, self.bars = st
        self.marks = list(marks)
        self.sel = min(self.sel, self.n)

    def undo(self):
        if not self.undo_stack:
            self.say("Nada para desfazer.")
            return
        self.redo_stack.append(self.snap())
        self._restore(self.undo_stack.pop())
        self.last_op = (None, 0.0)
        self.say("Desfeito")

    def redo(self):
        if not self.redo_stack:
            self.say("Nada para refazer.")
            return
        self.undo_stack.append(self.snap())
        self._restore(self.redo_stack.pop())
        self.last_op = (None, 0.0)
        self.say("Refeito")

    def move(self, delta):
        self.change("move%d" % self.sel)
        p = self.points()
        i = self.sel
        lo = 0 if i == 0 else p[i - 1] + 64
        hi = self.frames if i == len(p) - 1 else p[i + 1] - 64
        newv = max(lo, min(hi, p[i] + delta))
        if i == 0:
            self.start = newv
            self.divide()
        elif i == len(p) - 1:
            self.end = newv
            self.divide()
        else:
            self.marks[i - 1] = newv

    def snap_bars(self):
        self.change()
        self.bars = {0: 1, 1: 2, 2: 4, 4: 1}[self.bars]
        beat = SR * 60.0 / self.app.mixer.bpm
        self.end = min(self.frames, self.start + int(beat * 4 * self.bars))
        self.divide()
        self.say("Janela = %d compasso%s a %d BPM" % (self.bars, "s" if self.bars > 1 else "",
                                                     round(self.app.mixer.bpm)))

    def play_slice(self, k, button=None):
        if not self.data or k >= self.n:
            return
        s, e = self.slice_bounds(k)
        m = self.app.mixer
        key = "chop" if self.choke else "chop%d" % k
        m.shot(key, ramp(self.data[s * 4:e * 4]), group="chop", choke=True)
        if self.choke:
            with m.lock:
                m.voices = [v for v in m.voices if not (v.group == "chop" and v.key != key)]
        self.flash[k] = time.time()
        self.playing = (k, m.clock, e - s)
        if button:
            self.app.rec.event(m.clock, button)

    def play_window(self):
        if self.data:
            m = self.app.mixer
            m.shot("chop", ramp(self.data[self.start * 4:self.end * 4]), group="chop")
            self.playing = (-1, m.clock, self.end - self.start)

    def export(self):
        if not self.data:
            return
        if not os.path.isdir(EXPORT_DIR):
            os.makedirs(EXPORT_DIR)
        for k in range(8):
            path = os.path.join(EXPORT_DIR, "slice_%d.wav" % (k + 1))
            if k < self.n:
                s, e = self.slice_bounds(k)
                wf = wave.open(path, "wb")
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(SR)
                wf.writeframes(ramp(self.data[s * 4:e * 4]))
                wf.close()
            self.app.bank.set_chop_pad(k)
        self.say("Fatias 1-8 enviadas para o Loop Reactor (banco CHOP)")

    # ---------------------------------------------------------------- input (panel = "cut" | "play")
    def on(self, panel, kind, b):
        if self.browse:
            if kind in ("press", "repeat") and b in ("up", "down") and self.lib:
                self.bsel = (self.bsel + (1 if b == "down" else -1)) % len(self.lib)
            elif kind == "press" and b == "a" and self.lib:
                self.pick()
            elif kind == "press" and b == "b":
                self.browse = False
            return
        if kind not in ("press", "repeat"):
            return
        if not self.data:
            if kind == "press" and b in ("a", "b"):
                self.open_browser()
            return
        if panel == "cut":
            fine = self.app.input.down("r2")
            if b in ("up", "down"):
                self.sel = (self.sel + (1 if b == "down" else -1)) % (self.n + 1)
            elif b in ("left", "right"):
                ms = (1 if kind == "press" else 5) if fine else (10 if kind == "press" else 50)
                self.move((1 if b == "right" else -1) * SR * ms // 1000)
            elif kind != "press":
                return
            elif b == "x":
                self.change()
                self.n = {4: 8, 8: 16, 16: 4}[self.n]
                self.divide()
                self.sel = min(self.sel, self.n)
            elif b == "y":
                k = min(self.sel, self.n - 1)
                self.play_slice(k)
                self.app.mission("chop_slices")
            elif b == "a":
                self.play_window()
            elif b == "b":
                self.open_browser()
            elif b == "l2":
                self.snap_bars()
        else:
            if kind != "press":
                return
            if b in PADS:
                self.play_slice(self.page * 8 + PADS.index(b), b)
                self.app.mission("chop_slices")
            elif b in ("l2", "r2") and self.n > 8:
                self.page = 1 - self.page

    def combo(self, panel, b):
        if b == "x":
            self.export()
            self.app.mission("chop_to_reactor")
        elif b == "y":
            self.choke = not self.choke
            self.say("Uma fatia de cada vez: %s" % ("ligado" if self.choke else "desligado"))
        elif b == "a":
            self.app.rec.toggle("CHOP")
        elif b == "l2":
            self.undo()
        elif b == "r2":
            self.redo()
        else:
            return False
        return True

    # ---------------------------------------------------------------- drawing
    def draw(self, g, panel, t):
        app = self.app
        if self.loading:
            g.text("p16", "A CARREGAR...", W // 2, 200, C["text"], 255, "center")
            g.text("v20", self.loading[:40], W // 2, 230, C["muted"], 255, "center")
            return
        if not self.data:
            g.text("p16", "CORTAR EM FATIAS", W // 2, 150, app.accent, 255, "center")
            g.text("v20", "Corta uma música ou gravação em pedaços e toca-os nos 8 botões.", W // 2, 190, C["soft"], 255, "center")
            g.text("v20", "Funciona com as músicas da nave, as tuas gravações e sessões.", W // 2, 212, C["muted"],
                   255, "center")
            g.text("p8", "carrega A para escolher a música", W // 2, 260, C["cyan"], 255, "center")
        else:
            self.draw_overview(g, 78)
            self.draw_window(g, 134, 130 if panel == "cut" else 80, panel)
            if panel == "cut":
                self.draw_cut_info(g, 272)
            else:
                self.draw_pads(g, 240, t)
        if self.browse:
            self.draw_browser(g)
        s, t0 = self.msg
        if s and time.time() - t0 < 2.5:
            import ui
            ui.toast(g, s, app.accent, 200)

    def draw_overview(self, g, y):
        x0, w, h = 16, W - 32, 36
        g.rect(x0, y, w, h, C["off"])
        n = len(self.peaks)
        if not n:
            return
        bars = []
        for c in range(0, w, 2):
            i = c * n // w
            v = self.peaks[i] * h // 255
            bars.append((x0 + c, y + h // 2 - v // 2, 2, max(1, v)))
        g.rects(bars, C["muted"], 150)
        a = x0 + self.start * w // max(1, self.frames)
        b = x0 + self.end * w // max(1, self.frames)
        g.rect(a, y, max(2, b - a), h, self.app.accent, 70)
        g.frame(a, y, max(2, b - a), h, self.app.accent, 2)
        g.text("v20", self.title[:44], x0, y + h, C["dim"])

    def draw_window(self, g, y, h, panel):
        x0, w = 16, W - 32
        g.rect(x0, y, w, h, C["deck"])
        span = max(1, self.end - self.start)
        i0, i1 = self.start // 441, max(self.start // 441 + 1, self.end // 441)
        n = i1 - i0
        cols = 200
        bars = []
        top = max(self.peaks[i0:i1] or b"\x01") or 1          # normalise to the window so quiet parts are visible
        for c in range(cols):
            a = i0 + c * n // cols
            b = max(a + 1, i0 + (c + 1) * n // cols)
            if a >= len(self.peaks):
                break
            v = max(self.peaks[a:b]) * (h // 2 - 4) // top
            bars.append((x0 + c * w // cols, y + h // 2 - v, max(1, w // cols), 2 * v + 1))
        g.rects(bars, C["cyan"], 210)
        # playing slice highlight
        if self.playing:
            k, c0, ln = self.playing
            el = self.app.mixer.clock - c0
            if 0 <= el < ln:
                s, e = (self.start, self.end) if k < 0 else self.slice_bounds(k)
                px = x0 + (s + el - self.start) * w // span
                g.rect(px, y, 2, h, C["white"])
        pts = self.points()
        for i, p in enumerate(pts):
            x = x0 + (p - self.start) * w // span
            sel = panel == "cut" and i == self.sel
            col = self.app.accent if sel else (C["orange"] if i in (0, len(pts) - 1) else C["violet"])
            g.rect(min(x, x0 + w - 2), y, 3 if sel else 2, h, col)
            if i < len(pts) - 1:
                g.text("p8", "%d" % (i + 1), x + 4, y + 4, C["soft"] if not sel else self.app.accent)

    def draw_cut_info(self, g, y):
        app = self.app
        beat = SR * 60.0 / app.mixer.bpm
        span = self.end - self.start
        pts = self.points()
        name = "INICIO" if self.sel == 0 else ("FIM" if self.sel == self.n else "CORTE %d" % (self.sel + 1))
        g.text("p8", "MARCADOR: %s  @ %.3f s" % (name, pts[self.sel] / float(SR)), 20, y + 6, app.accent)
        g.text("v20", "JANELA %.2f s = %.2f batidas" % (span / float(SR), span / beat), 20, y + 24, C["soft"])
        g.text("v20", "(a %d BPM)" % round(app.mixer.bpm), 20, y + 42, C["muted"])
        g.text("v20", "%d fatias  ·  %s" % (self.n, "uma de cada vez" if self.choke else "várias ao mesmo tempo"), 20, y + 62, C["cyan"])
        import ui
        rows = [("cima/baixo", "escolher marcador"), ("esq/dir", "mover (R2 = fino)"), ("X", "4 / 8 / 16 fatias"),
                ("Y", "ouvir a fatia"), ("A", "ouvir a janela"), ("L2", "janela 1/2/4 compassos"), ("B", "outro ficheiro")]
        for i, (k, v) in enumerate(rows):
            xe = ui.keys(g, k, 350, y + 6 + i * 21, 16)
            g.text("v20", v, max(xe + 6, 400), y + 4 + i * 21, C["muted"])

    def draw_pads(self, g, y, t):
        app = self.app
        cell, gap = 62, 6
        names = PADS
        pos = {"up": (1, 0), "left": (0, 1), "right": (2, 1), "down": (1, 2)}
        for side, ox, keys, glyphs in (("dpad", 40, names[:4], ["up", "left", "right", "down"]),
                                       ("face", W - 40 - 3 * cell - 2 * gap, names[4:], ["X", "Y", "A", "B"])):
            for j, b in enumerate(keys):
                k = self.page * 8 + names.index(b)
                cx, cy = pos[["up", "left", "right", "down"][j]]
                x, yy = ox + cx * (cell + gap), y + cy * (cell + gap) - 20
                on = k < self.n
                lit = time.time() - self.flash.get(k, 0) < 0.12
                g.rect(x, yy, cell, cell, app.accent if lit else (C["hull"] if on else C["off"]))
                g.frame(x, yy, cell, cell, C["violet"] if on else C["hull"], 2)
                gl = glyphs[j]
                if gl in ("up", "left", "right", "down"):
                    g.tri(x + 6, yy + 6, 5, gl, C["cyan"])
                else:
                    g.text("p8", gl, x + 8, yy + 8, C["cyan"])
                if on:
                    g.text("p16", "%d" % (k + 1), x + cell // 2, yy + 26, C["void"] if lit else C["text"], 255,
                           "center")
        cxm = W // 2
        g.text("p8", "FATIAS %d-%d" % (self.page * 8 + 1, min(self.n, self.page * 8 + 8)), cxm, y + 40, C["soft"],
               255, "center")
        if self.n > 8:
            g.text("v20", "L2/R2 página", cxm, y + 58, C["muted"], 255, "center")
        g.text("v20", "uma de cada vez" if self.choke else "várias juntas", cxm, y + 80, C["cyan"], 255, "center")

    def draw_browser(self, g):
        x, y, w, h = 40, 64, W - 80, 340
        g.rect(x, y, w, h, C["panel"], 248)
        g.frame(x, y, w, h, self.app.accent, 3)
        g.text("p8", "ESCOLHE O QUE QUERES CORTAR", x + 16, y + 12, self.app.accent)
        if not self.lib:
            g.text("v20", "Nada encontrado.", x + 16, y + 40, C["soft"])
            return
        top = max(0, min(self.bsel - 6, len(self.lib) - 13))
        for row, i in enumerate(range(top, min(len(self.lib), top + 13))):
            it = self.lib[i]
            yy = y + 34 + row * 22
            sel = i == self.bsel
            if sel:
                g.rect(x + 8, yy - 2, w - 16, 22, C["hull"])
            g.text("v20", it["title"][:40], x + 16, yy, C["text"] if sel else C["soft"])
            g.text("v20", it["tag"], x + w - 16, yy, C["cyan"] if sel else C["dim"], 255, "right")


