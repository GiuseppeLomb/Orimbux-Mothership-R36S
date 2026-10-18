# VOX NEBULA - live voice effects through the USB mic: robot, alien, monster, radio, distortion, cave, echo.
# The mic keeps running when you leave (sing over Loop Reactor / Beat Forge); R2 turns it on/off.
# All effects are block-based audioop maths (cheap enough for the console CPU).
import os
import subprocess
import threading
import time

import engine
from engine import C, W, SR, BUF, audioop

EFFECTS = [("ROBOT", "up"), ("ALIEN", "left"), ("MONSTRO", "right"), ("ECO", "down"),
           ("CAVERNA", "x"), ("RADIO", "y"), ("DISTORCAO", "a"), ("LIMPO", "b")]
SHOW = {"ROBOT": "ROBÔ", "RADIO": "RÁDIO", "DISTORCAO": "DISTORÇÃO"}
MAX_BUF = (BUF + 512) * 2          # mono s16 bytes kept from the mic (more = older = later)


class Comb(object):
    """y[t] = x[t] + fb * y[t-D]  (mono s16 bytes, any block size)"""

    def __init__(self, d, fb):
        self.d, self.fb = d, fb
        self.y = b"\0" * (d * 2)

    def run(self, x):
        out = []
        d2 = self.d * 2
        for p in range(0, len(x), d2):
            c = x[p:p + d2]
            k = len(self.y) - d2
            delayed = self.y[k:k + len(c)]
            yc = audioop.add(c, audioop.mul(delayed, 2, self.fb), 2)
            self.y = (self.y + yc)[-d2:]
            out.append(yc)
        return b"".join(out)


class MicReader(object):
    """arecord -> raw mono s16 into a small ring buffer (or a wav file when testing: VOX_FAKE=path)"""

    def __init__(self, dev=None, arecord=None, fake=None):
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.proc = None
        self.alive = True
        self.error = ""
        if fake:
            threading.Thread(target=self._fake, args=(fake,), daemon=True).start()
            return
        try:
            self.proc = subprocess.Popen([arecord, "-q", "-D", dev, "-f", "S16_LE", "-r", str(SR), "-c", "1",
                                          "-t", "raw", "--buffer-time=20000", "--period-time=5000"],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            threading.Thread(target=self._pump, daemon=True).start()
        except Exception as e:
            self.error = str(e)
            self.alive = False

    def _push(self, d):
        with self.lock:
            self.buf += d
            if len(self.buf) > MAX_BUF:
                del self.buf[:len(self.buf) - MAX_BUF]

    def _pump(self):
        while self.alive and self.proc:
            d = self.proc.stdout.read(512)
            if not d:
                self.alive = False
                self.error = "o micro parou"
                break
            self._push(d)

    def _fake(self, path):
        data = engine.load_wav(path)
        mono = audioop.tomono(data, 2, 0.5, 0.5)
        pos, t0 = 0, time.time()
        while self.alive and pos < len(mono):
            want = int((time.time() - t0) * SR) * 2
            if want > pos:
                self._push(mono[pos:want])
                pos = want
            time.sleep(0.005)
        self.alive = False

    def take(self, n):
        with self.lock:
            extra = len(self.buf) - (n + 256) * 2            # never let old audio pile up: drop it (lower latency)
            if extra > 0:
                del self.buf[:extra]
            d = bytes(self.buf[:n * 2])
            del self.buf[:n * 2]
        if len(d) < n * 2:
            d += b"\0" * (n * 2 - len(d))
        return d

    def buffered(self):
        return len(self.buf) // 2

    def stop(self):
        self.alive = False
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(1)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None


class Shifter(object):
    """pitch shift without changing speed (WSOLA-style): grains of 512 samples, 2x overlap, stepped triangular
    window; each new grain is slid (in-phase search with audioop, in C) to the position that best continues the previous one,
    so the waveform stays in phase instead of sounding granulated"""
    G, HOP, PIECES, TOL, REF = 512, 256, 16, 256, 96

    def __init__(self, ratio):
        self.ratio = ratio
        self.L = int(self.G * ratio)
        self.hist = b""
        self.base = 0              # absolute index of hist[0]
        self.total = 0             # samples received so far
        self.prev = None           # absolute start of the previous grain
        self.acc = b"\0" * (self.G * 2)
        self.win = [(i + 0.5) / 8.0 if i < 8 else (15.5 - i) / 8.0 for i in range(self.PIECES)]
        self.piece = self.G // self.PIECES

    def seg(self, a, b):
        return self.hist[(a - self.base) * 2:(b - self.base) * 2]

    @staticmethod
    def best_offset(frag, ref):
        """offset in frag where ref fits best IN PHASE (findfit would also accept an inverted match):
        coarse search every 8 samples, then refine; each test is two audioop calls"""
        r2 = len(ref)
        neg = audioop.mul(ref, 2, -1.0)
        maxo = (len(frag) - r2) // 2

        def dist(o):
            return audioop.rms(audioop.add(frag[o * 2:o * 2 + r2], neg, 2), 2)
        best = min(range(0, maxo + 1, 8), key=dist)
        return min(range(max(0, best - 7), min(maxo, best + 7) + 1), key=dist)

    def run(self, x):
        n = len(x) // 2
        self.hist += x
        start_block = self.total
        self.total += n
        keep = self.L + self.TOL + n + self.REF + 64
        if len(self.hist) > keep * 2:
            cut = len(self.hist) // 2 - keep
            self.hist = self.hist[cut * 2:]
            self.base += cut
        out = []
        G2, P2 = self.G * 2, self.piece * 2
        for j in range(n // self.HOP):
            nominal = start_block + (j + 1) * self.HOP - self.L
            st = nominal
            if self.prev is not None:
                lo = max(self.base, nominal - self.TOL)
                ref = self.seg(self.prev + self.L // 2, self.prev + self.L // 2 + self.REF)
                frag = self.seg(lo, nominal + self.REF)
                if len(ref) == self.REF * 2 and len(frag) > len(ref):
                    st = lo + self.best_offset(frag, ref)
            st = max(self.base, min(st, start_block + n - self.L))
            self.prev = st
            src = self.seg(st, st + self.L)
            if len(src) < self.L * 2:
                src += b"\0" * (self.L * 2 - len(src))
            gr = audioop.ratecv(src, 2, 1, self.L, self.G, None)[0]
            gr = (gr + b"\0" * G2)[:G2]
            gr = b"".join(audioop.mul(gr[i * P2:(i + 1) * P2], 2, w) for i, w in enumerate(self.win))
            self.acc = audioop.add(self.acc, gr, 2)
            out.append(self.acc[:self.HOP * 2])
            self.acc = self.acc[self.HOP * 2:] + b"\0" * (self.HOP * 2)
        y = b"".join(out)
        return (y + b"\0" * (n * 2))[:n * 2]


class VoxStream(object):
    group = "vox"

    def __init__(self, vox):
        self.vox = vox
        self.done = False
        self.start = 0

    def read(self, n, clock=None):
        v = self.vox
        if not v.mic:
            return None
        x = v.mic.take(n)
        lvl = audioop.rms(x, 2)
        v.level = v.level * 0.5 + 0.5 * min(1.0, lvl / 6000.0)
        if lvl < v.gate:
            x = audioop.mul(x, 2, 0.1)
        x = audioop.mul(x, 2, v.gain)
        y = v.process(x)
        if v.echo:
            y = v.echo_fx.run(y)
        return audioop.tostereo(y, 2, 1, 1)

    def fade(self, to, seconds):
        if to <= 0:
            self.vox.stop()

    def close(self):
        pass


class Vox(object):
    name = "VOX NEBULA"

    def __init__(self, app):
        self.app = app
        self.mic = None
        self.stream = VoxStream(self)
        self.fx = "LIMPO"
        self.echo = False
        self.echo_fx = Comb(int(SR * 0.27), 0.42)
        self.robot = Comb(220, 0.72)
        self.up = Shifter(2.0)
        self.down = Shifter(0.5)
        self.cave = [Comb(d, 0.62) for d in (1201, 1607, 2111, 2729)]
        self.gain = 1.5
        self.gate = 300
        self.level = 0.0
        self.msg = ("", 0.0)
        self.flash = {}

    @property
    def live(self):
        return self.mic is not None

    def say(self, s):
        self.msg = (s, time.time())

    # ---------------------------------------------------------------- effects (mono s16 bytes in/out)
    def process(self, x):
        fx = self.fx
        n = len(x) // 2
        if fx == "LIMPO":
            return x
        if fx == "ROBOT":
            return audioop.mul(self.robot.run(audioop.mul(x, 2, 0.6)), 2, 0.8)
        if fx == "ALIEN":                       # an octave up, same speed
            return self.up.run(x)
        if fx == "MONSTRO":                     # an octave down, same speed, a bit of grit
            y = self.down.run(x)
            return audioop.mul(audioop.mul(y, 2, 2.2), 2, 0.6)
        if fx == "RADIO":
            lo = audioop.ratecv(x, 2, 1, SR, 6000, None)[0]
            lo = audioop.lin2lin(audioop.lin2lin(lo, 2, 1), 1, 2)
            back = audioop.ratecv(lo, 2, 1, 6000, SR, None)[0]
            back = (back + b"\0" * (n * 2))[:n * 2]
            return audioop.mul(audioop.mul(back, 2, 3.0), 2, 0.45)
        if fx == "DISTORCAO":
            return audioop.mul(audioop.mul(x, 2, 7.0), 2, 0.3)
        if fx == "CAVERNA":
            wet = None
            for c in self.cave:
                y = c.run(audioop.mul(x, 2, 0.25))
                wet = y if wet is None else audioop.add(wet, y, 2)
            return audioop.add(audioop.mul(x, 2, 0.6), wet, 2)
        if fx == "ECO":
            return self.echo_fx.run(x)
        return x

    # ---------------------------------------------------------------- mic on/off
    def start(self):
        if hasattr(self.app, "mission"):
            self.app.mission("vox_live")
        ab = self.app.sections["abductor"]
        fake = os.environ.get("VOX_FAKE")
        if ab.proc:
            self.say("O Abductor está a gravar: para essa gravação primeiro.")
            return
        if fake:
            self.mic = MicReader(fake=fake)
        else:
            if not ab.arecord or not ab.devices:
                ab.scan()
            if not ab.arecord:
                self.say("Esta consola não consegue gravar som.")
                return
            if not ab.has_mic:
                self.say("Não encontrei nenhum micro USB.")
                return
            card, dev, _ = ab.devices[ab.sel]
            self.mic = MicReader("plughw:%d,%d" % (card, dev), ab.arecord)
            if not self.mic.alive:
                self.say("O micro não respondeu.")
                self.mic = None
                return
        m = self.app.mixer
        with m.lock:
            if self.stream not in m.streams:
                m.streams.append(self.stream)
        self.say("Micro ligado: usa auscultadores para não apitar")

    def stop(self):
        if self.mic:
            self.mic.stop()
        self.mic = None

    # ---------------------------------------------------------------- section interface
    def enter(self):
        ab = self.app.sections["abductor"]
        if not ab.proc:
            ab.scan()

    def leave(self):
        pass

    def toggle_mic(self):
        if self.live:
            self.stop()
            self.say("Micro desligado")
        else:
            self.start()

    def rec_spec(self):
        return ("VOX", None)

    def combo(self, b):
        if b in ("up", "down"):
            self.gate = max(0, min(3000, self.gate + (100 if b == "up" else -100)))
        elif b == "a":
            self.app.rec.toggle("VOX")
        else:
            return False
        return True

    def on(self, kind, b):
        if kind not in ("press", "repeat"):
            return
        if b == "r2" and kind == "press":
            self.toggle_mic()
            return
        if b in ("l1", "r1"):
            self.gain = max(0.25, min(6.0, round(self.gain + (0.25 if b == "r1" else -0.25), 2)))
            return
        if b == "l2" and kind == "press":
            self.echo = not self.echo
            return
        for name, key in EFFECTS:
            if key == b and kind == "press":
                self.fx = name
                self.flash[name] = time.time()

    def update(self, dt):
        if self.mic and not self.mic.alive and not os.environ.get("VOX_FAKE"):
            self.say("O micro parou.")
            self.mic = None

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        import app as appmod
        app = self.app
        g.clear(C["void"])
        appmod.header(g, app, "VOX NEBULA", "vox")
        ab = app.sections["abductor"]
        live = self.live
        # status + meter
        g.text("p16", "● AO VIVO" if live else "MICRO OFF", 20, 62, (255, 70, 90) if live else C["dim"])
        dev = ab.devices[ab.sel][2][:30] if ab.devices else "sem micro USB"
        g.text("v20", dev, 20, 84, C["muted"])
        lv = self.level if live else 0.0
        bars = []
        for i in range(30):
            on = i < int(lv * 30)
            bars.append((200 + i * 14, 66, 10, 22))
            if on:
                g.rect(200 + i * 14, 66, 10, 22, C["green"] if i < 20 else (C["orange"] if i < 26 else (255, 70, 90)))
        g.rects([r for i, r in enumerate(bars) if i >= int(lv * 30)], C["hull"])
        lat = (self.mic.buffered() + BUF) * 1000 // SR if live else 0
        g.text("v20", "ganho x%.2f  ·  corta ruído %d  ·  eco %s%s" % (self.gain, self.gate, "ON" if self.echo else "OFF",
                                                       ("  ·  ~%d ms" % lat) if live else ""), 200, 92, C["soft"])
        # effects cross
        cell, gap = 92, 8
        pos = {"up": (1, 0), "left": (0, 1), "right": (2, 1), "down": (1, 2),
               "x": (1, 0), "y": (0, 1), "a": (2, 1), "b": (1, 2)}
        glyph = {"up": "up", "left": "left", "right": "right", "down": "down", "x": "X", "y": "Y", "a": "A", "b": "B"}
        for name, key in EFFECTS:
            side = 0 if key in ("up", "left", "right", "down") else 1
            ox = 14 if side == 0 else W - 14 - 3 * cell - 2 * gap
            cx, cy = pos[key]
            x, y = ox + cx * (cell + gap), 124 + cy * 96
            sel = name == self.fx
            lit = time.time() - self.flash.get(name, 0) < 0.15
            g.rect(x, y, cell, 84, app.accent if (sel or lit) else C["hull"])
            g.frame(x, y, cell, 84, C["orangehi"] if sel else C["hullhi"], 2)
            gl = glyph[key]
            if gl in ("up", "left", "right", "down"):
                g.tri(x + 8, y + 8, 6, gl, C["void"] if sel else C["cyan"])
            else:
                g.text("p8", gl, x + 10, y + 10, C["void"] if sel else C["cyan"])
            g.text("p8", SHOW.get(name, name), x + cell // 2, y + 50, C["void"] if sel else C["text"], 255, "center")
        import ui
        if not live:
            xe = ui.keys(g, "R2", W // 2 - 190, 420)
            g.text("v20", "liga o micro (USB com adaptador). Usa auscultadores!", xe + 6, 418, C["cyan"])
        appmod.footer(g, [("R2", "micro on/off", 0), ("setas + X/Y/A/B", "efeito", 0), ("L2", "eco", 0)])
        s, t0 = self.msg
        if s and time.time() - t0 < 2.8:
            ui.toast(g, s, app.accent, 214)

