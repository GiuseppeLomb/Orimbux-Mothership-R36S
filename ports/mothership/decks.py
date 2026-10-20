# TWIN DECKS - two players for beatmatching by ear: pitch fader (+-16%), nudge, search, CDJ-style cue,
# tap BPM (no automatic analysis), sync from the taps, crossfader on the analog stick, SPLIT CUE for headphones
# (left ear = what you cue, right ear = the mix), waveform overview + zoom, mix recording.
import glob
import os
import threading
import time
import wave

import engine
from engine import C, W, SR, audioop

BD = os.path.join(engine.ASSETS, "bd")
REC_DIR = os.path.join(engine.APP, "recordings")
PITCH_MAX = 0.16
NUDGE = 0.04
ZOOM_S = 3.0               # seconds either side of the playhead in the zoomed waveform


class Deck(object):
    def __init__(self, name):
        self.name = name
        self.wf = None
        self.path = None
        self.title = "VAZIO"
        self.rate, self.ch, self.sw = SR, 2, 2
        self.frames = 0
        self.pos = 0                    # source frames already read from disk
        self.pend = b""
        self.cv = None
        self.key = None
        self.playing = False
        self.pitch = 0.0
        self.nudge = 0.0
        self.cue = 0
        self.preview = False            # cue held while paused
        self.peaks = bytearray()
        self.block = SR // 100
        self.overview = []
        self.taps = []
        self.bpm = None
        self.level = 0.0
        self.ended = False

    # ---- file
    def load(self, path, title, bpm=None):
        wf = wave.open(path, "rb")
        if self.wf:
            self.wf.close()
        self.wf, self.path, self.title = wf, path, title
        self.ch, self.sw, self.rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
        self.frames = wf.getnframes()
        self.pos, self.pend, self.cv, self.key = 0, b"", None, None
        self.playing = self.preview = self.ended = False
        self.cue = 0
        self.pitch = self.nudge = 0.0
        self.taps = []
        self.bpm = bpm
        self.block = max(1, self.rate // 100)
        self.peaks = bytearray()
        self.overview = []
        self._ovbars = None
        threading.Thread(target=self._peaks, args=(path, self.block, self.sw, self.ch), daemon=True).start()

    def _peaks(self, path, block, sw, ch):
        try:
            wf = wave.open(path, "rb")
            try:
                out = bytearray()
                step = block * 2 * ch            # after conversion everything is 16-bit
                while True:
                    d = wf.readframes(block * 400)
                    if not d:
                        break
                    if sw == 1:
                        d = audioop.bias(d, 1, -128)
                    if sw != 2:
                        d = audioop.lin2lin(d, sw, 2)
                    for i in range(0, len(d), step):
                        out.append(min(255, audioop.max(d[i:i + step], 2) >> 7))
                    if path != self.path:    # another track was loaded meanwhile
                        return
                    self.peaks = out[:]          # partial result is drawn while it loads
            finally:
                wf.close()                       # also when it stops early (Windows keeps open files locked)
            n = len(out)
            if n and path == self.path:
                cols = 600
                self.overview = [max(out[int(c * n / cols):max(int(c * n / cols) + 1, int((c + 1) * n / cols))])
                                 for c in range(cols)]
        except Exception:
            pass

    def seek(self, frame):
        if not self.wf:
            return
        frame = int(max(0, min(self.frames - 1, frame)))
        self.wf.setpos(frame)
        self.pos, self.pend, self.cv = frame, b"", None
        self.ended = False

    # ---- playback (audio thread)
    def ratio(self):
        return (1.0 + self.pitch) * (1.0 + self.nudge) * self.rate / float(SR)

    def where(self):
        """source frame being heard (approximately: minus what is still buffered)"""
        return max(0, self.pos - int(len(self.pend) // 4 * self.ratio()))

    def read(self, n):
        if not (self.playing or self.preview) or not self.wf:
            return None
        r = self.ratio()
        key = max(1, int(round(r * 10000)))
        if key != self.key:
            self.key, self.cv = key, None
        while len(self.pend) < n * 4:
            need = int((n * 4 - len(self.pend)) // 4 * r) + 16
            d = self.wf.readframes(need)
            if not d:
                break
            self.pos += len(d) // (self.sw * self.ch)
            if self.sw == 1:
                d = audioop.bias(d, 1, -128)
            if self.sw != 2:
                d = audioop.lin2lin(d, self.sw, 2)
            d, self.cv = audioop.ratecv(d, 2, self.ch, key, 10000, self.cv)
            if self.ch == 1:
                d = audioop.tostereo(d, 2, 1, 1)
            self.pend += d
        out, self.pend = self.pend[:n * 4], self.pend[n * 4:]
        if len(out) < n * 4:
            out += b"\0" * (n * 4 - len(out))
            self.playing = self.preview = False
            self.ended = True
        self.level = self.level * 0.6 + 0.4 * min(1.0, audioop.rms(out, 2) / 9000.0)
        return out

    # ---- tempo (taps only: no automatic analysis)
    def tap(self, now):
        if self.taps and now - self.taps[-1] > 2.0:
            self.taps = []
        self.taps.append(now)
        self.taps = self.taps[-9:]
        if len(self.taps) >= 4:
            iv = sorted(b - a for a, b in zip(self.taps, self.taps[1:]))
            self.bpm = round(60.0 / iv[len(iv) // 2], 1)

    def eff_bpm(self):
        return self.bpm * (1.0 + self.pitch) if self.bpm else None


class DJFilter(object):
    """one-knob DJ filter, all in C (audioop): low-pass = box filter built by doubling stages
    (width 2^m frames), high-pass = signal minus its low-pass. val -6..-1 low-pass, 1..6 high-pass."""

    def __init__(self):
        self.pos = 0.0           # continuous knob position (analog stick moves it)
        self.tails = {}
        self.dtail = b""

    @property
    def val(self):
        return int(round(self.pos))

    def _lp(self, x, m):
        for k in range(1, m + 1):
            sh = (1 << (k - 1)) * 4
            tail = self.tails.get(k, b"\0" * sh)
            joined = tail + x
            shifted = joined[:len(x)]
            self.tails[k] = joined[-sh:]
            x = audioop.add(audioop.mul(x, 2, 0.5), audioop.mul(shifted, 2, 0.5), 2)
        return x

    def process(self, x):
        v = self.val
        if v == 0:
            return x
        if v < 0:
            return self._lp(x, min(8, 2 - v))                 # -1..-6 -> width 8..256 frames (5.5 kHz .. 170 Hz)
        m = max(3, 9 - v)                                      # 1..6 -> width 256..8 (cuts below ~100 Hz .. 3 kHz)
        lp = self._lp(x, m)
        d = ((1 << m) // 2) * 4                                # line the dry signal up with the box delay
        joined = (self.dtail or b"\0" * d) + x
        xd = joined[:len(x)]
        self.dtail = joined[-d:]
        return audioop.add(xd, audioop.mul(lp, 2, -1.0), 2)

    def label(self):
        v = self.val
        return "-" if v == 0 else ("LP%d" % -v if v < 0 else "HP%d" % v)


class DeckMixer(object):
    """lives in mixer.streams; mixes both decks with the crossfader (or the split-cue layout)"""
    group = "decks"

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.xf = 0.5
        self.split = False
        self.cue_a = True
        self.cue_b = False
        self.done = False
        self.start = 0
        self.fa, self.fb = DJFilter(), DJFilter()

    def gains(self):
        x = self.xf
        return min(1.0, 2.0 * (1.0 - x)), min(1.0, 2.0 * x)       # "dipless": both full in the middle

    def read(self, n, clock=None):
        da, db = self.a.read(n), self.b.read(n)
        if da is None and db is None:
            return None
        ga, gb = self.gains()
        z = b"\0" * (n * 4)
        da, db = da or z, db or z
        da, db = self.fa.process(da), self.fb.process(db)
        master = audioop.add(audioop.mul(da, 2, ga), audioop.mul(db, 2, gb), 2)
        if not self.split:
            return master
        if self.cue_a and self.cue_b:
            cue = audioop.add(audioop.mul(da, 2, 0.7), audioop.mul(db, 2, 0.7), 2)
        else:
            cue = da if self.cue_a else (db if self.cue_b else z)
        left = audioop.tostereo(audioop.tomono(cue, 2, 0.5, 0.5), 2, 1, 0)
        right = audioop.tostereo(audioop.tomono(master, 2, 0.5, 0.5), 2, 0, 1)
        return audioop.add(left, right, 2)

    def fade(self, to, seconds):
        if to <= 0:
            self.a.playing = self.b.playing = False
            self.a.preview = self.b.preview = False

    def close(self):
        pass


def library(app):
    """(title, path or None, src_key, bpm) - music folder (converted by WARP FLOOR when needed),
    recordings, and the 5 Beat Duel songs so the decks work out of the box"""
    out = []
    warp = app.sections["warp"]
    warp.scan()
    for i, src in enumerate(warp.tracks):
        out.append({"title": os.path.splitext(os.path.basename(src))[0], "src": src, "warp": i, "bpm": None,
                    "tag": "MUSICA"})
    for p in sorted(glob.glob(os.path.join(REC_DIR, "*.wav")), reverse=True):
        bpm = None
        meta = p[:-4] + ".json"
        if os.path.exists(meta):
            try:
                bpm = engine.num(engine.read_json(meta).get("bpm"), None, 1)     # the deck multiplies it
            except Exception:
                pass
        out.append({"title": os.path.splitext(os.path.basename(p))[0], "src": p, "path": p, "bpm": bpm,
                    "tag": "GRAVACAO"})
    for p in sorted(glob.glob(os.path.join(BD, "*.json"))):
        try:
            m = engine.read_json(p)
            out.append({"title": m["title"], "src": os.path.join(BD, m["file"]), "path": os.path.join(BD, m["file"]),
                        "bpm": m.get("bpm"), "tag": "BEAT DUEL"})
        except Exception:
            pass
    return out


class TwinDecks(object):
    name = "TWIN DECKS"

    def __init__(self, app):
        self.app = app
        self.a, self.b = Deck("A"), Deck("B")
        self.mix = DeckMixer(self.a, self.b)
        self.browse = None          # deck being loaded
        self.lib = []
        self.bsel = 0
        self.pending = None         # (deck, item) waiting for a conversion
        self.msg = ("", 0.0)

    def say(self, s):
        self.msg = (s, time.time())

    def ensure_stream(self):
        m = self.app.mixer
        with m.lock:
            if self.mix not in m.streams:
                self.mix.done = False
                m.streams.append(self.mix)

    def rec_spec(self):
        """the music menu records the mix (up to 20 min)"""
        if self.mix.split:
            self.mix.split = False
            self.say("SPLIT CUE desligado para gravar a mistura")
        return ("DECKS", 20 * 60)

    def stop_all(self):
        self.mix.fade(0.0, 0.1)

    def enter(self):
        warp = self.app.sections["warp"]
        if warp.cur is not None and not warp.cur.done:      # one DJ at a time
            warp.cur.fade(0.0, 1.5)
            warp.cur = None
        self.ensure_stream()

    def leave(self):
        self.browse = None

    # ---------------------------------------------------------------- loading
    def open_browser(self, deck):
        self.lib = library(self.app)
        self.browse = deck
        self.bsel = min(self.bsel, max(0, len(self.lib) - 1))

    def load_item(self, deck, it):
        path = it.get("path")
        if path is None:
            warp = self.app.sections["warp"]
            warp.prepare(it["warp"])
            path = warp.ready.get(it["src"])
            if path is None:
                self.pending = (deck, it)
                self.say("A converter %s..." % it["title"][:24])
                return
        m = self.app.mixer
        try:
            with m.lock:
                deck.load(path, it["title"], it.get("bpm"))
            self.say("Deck %s: %s" % (deck.name, it["title"][:28]))
        except Exception:
            self.say("Não consegui abrir este ficheiro.")
        self.ensure_stream()

    # ---------------------------------------------------------------- controls
    def deck_keys(self, b):
        """map a button to (deck, action)"""
        a, d = self.a, self.b
        table = {"l1": (a, "play"), "l2": (a, "cue"), "up": (a, "pitch+"), "down": (a, "pitch-"),
                 "left": (a, "back"), "right": (a, "fwd"),
                 "r1": (d, "play"), "r2": (d, "cue"), "x": (d, "pitch+"), "b": (d, "pitch-"),
                 "y": (d, "back"), "a": (d, "fwd")}
        return table.get(b, (None, None))

    def combo(self, b):
        a, d, mx = self.a, self.b, self.mix
        now = time.time()
        if b in ("left", "right"):
            mx.xf = max(0.0, min(1.0, mx.xf + (0.125 if b == "right" else -0.125)))
        elif b == "l1":
            self.open_browser(a)
        elif b == "r1":
            self.open_browser(d)
        elif b == "l2":
            mx.cue_a = not mx.cue_a
        elif b == "r2":
            mx.cue_b = not mx.cue_b
        elif b == "a":
            if self.app.rec.active():
                self.say("Para a gravação antes de ligar o SPLIT CUE.")
            else:
                mx.split = not mx.split
                self.say("SPLIT CUE %s" % ("LIGADO: esq = cue, dir = mistura" if mx.split else "DESLIGADO"))
        elif b == "up":
            a.tap(now)
        elif b == "x":
            d.tap(now)
        elif b == "down":
            a.pitch = 0.0
        elif b == "b":
            d.pitch = 0.0
        elif b == "y":
            self.sync()
        else:
            return False
        return True

    def sync(self):
        """the deck you are NOT hearing (crossfader) takes the tempo of the one on air - from your taps"""
        on_air, other = (self.a, self.b) if self.mix.xf < 0.5 else (self.b, self.a)
        if not (on_air.bpm and other.bpm):
            self.say("SYNC precisa do BPM dos dois decks (SELECT+cima / SELECT+X para bater).")
            return
        target = on_air.eff_bpm() / other.bpm - 1.0
        if abs(target) > PITCH_MAX:
            self.say("Diferença grande demais (%+.1f%%)." % (target * 100))
            return
        other.pitch = round(target, 4)
        self.say("Deck %s -> %.1f BPM (%+.2f%%)" % (other.name, other.eff_bpm(), other.pitch * 100))

    def on(self, kind, b):
        if self.browse is not None:
            if kind in ("press", "repeat") and b in ("up", "down") and self.lib:
                self.bsel = (self.bsel + (1 if b == "down" else -1)) % len(self.lib)
            elif kind == "press" and b == "a" and self.lib:
                self.load_item(self.browse, self.lib[self.bsel])
                self.browse = None
            elif kind == "press" and b == "b":
                self.browse = None
            return
        if kind == "press" and b in ("l3", "r3"):
            (self.mix.fa if b == "l3" else self.mix.fb).pos = 0.0
            return
        deck, act = self.deck_keys(b)
        if deck is None:
            return
        m = self.app.mixer
        if kind == "release":
            if act in ("back", "fwd"):
                deck.nudge = 0.0
            elif act == "cue" and deck.preview:
                with m.lock:
                    deck.preview = False
                    if not deck.playing:
                        deck.seek(deck.cue)
            return
        if not deck.wf:
            if kind == "press":
                self.say("Deck %s vazio: SELECT+%s para carregar." % (deck.name, "L1" if deck is self.a else "R1"))
            return
        if act == "play" and kind == "press":
            with m.lock:
                if deck.preview:
                    deck.preview = False
                    deck.playing = True
                elif deck.ended:
                    deck.seek(deck.cue)
                    deck.playing = True
                else:
                    deck.playing = not deck.playing
            self.ensure_stream()
        elif act == "cue" and kind == "press":
            with m.lock:
                if deck.playing:
                    deck.playing = False
                    deck.seek(deck.cue)
                elif abs(deck.where() - deck.cue) > deck.rate // 50:
                    deck.cue = deck.where()
                    deck.seek(deck.cue)
                else:
                    deck.preview = True
            self.ensure_stream()
        elif act in ("pitch+", "pitch-"):
            stp = 0.0005 if kind == "press" else 0.002
            deck.pitch = max(-PITCH_MAX, min(PITCH_MAX, deck.pitch + (stp if act == "pitch+" else -stp)))
        elif act in ("back", "fwd"):
            sign = 1 if act == "fwd" else -1
            if deck.playing:
                deck.nudge = sign * NUDGE
            else:
                jump = (0.1 if kind == "press" else 0.5) * deck.rate
                with m.lock:
                    deck.seek(deck.where() + sign * jump)

    def update(self, dt):
        if self.a.playing and self.b.playing and self.a.wf and self.b.wf:
            self.app.mission("decks_both")
        ax = self.app.input.axes
        lx = ax.get("lx", 0.0)
        if abs(lx) > 0.15:
            self.mix.xf = max(0.0, min(1.0, self.mix.xf + lx * 1.2 * dt))
        for f, k in ((self.mix.fa, "ly"), (self.mix.fb, "ry")):      # stick up = high-pass, down = low-pass
            v = ax.get(k, 0.0)
            if abs(v) > 0.2:
                f.pos = max(-6.0, min(6.0, f.pos - v * 6.0 * dt))
        if self.pending:
            deck, it = self.pending
            if self.app.sections["warp"].ready.get(it["src"]):
                self.pending = None
                self.load_item(deck, it)

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        import app as appmod
        app = self.app
        g.clear(C["void"])
        appmod.header(g, app, "TWIN DECKS", "decks")
        self.draw_deck(g, self.a, 56, C["cyan"], t, top=True)
        self.draw_zoom(g, self.a, 172, C["cyan"])
        self.draw_zoom(g, self.b, 232, C["violet"])
        self.draw_deck(g, self.b, 296, C["violet"], t, top=False)
        self.draw_mixer(g, t)
        import ui
        if self.browse is not None:
            appmod.footer(g, [("cima/baixo", "escolher", 0), ("A", "carregar", 0), ("B", "voltar", 0)])
        elif not (self.a.wf or self.b.wf):
            appmod.footer(g, [("SEL+L1", "carregar deck A", 0), ("SEL+R1", "carregar deck B", 0)])
        else:
            appmod.footer(g, [("L1/R1", "tocar A/B", 0), ("L2/R2", "cue A/B", 0), ("analogico esq.", "passar de A para B", 0)])
        helping = self.browse is None and app.input.down("select")
        if self.browse is not None:
            self.draw_browser(g)
        s, t0 = self.msg
        if s and time.time() - t0 < 2.8 and not helping:
            ui.toast(g, s, app.accent, 214)

    def draw_deck(self, g, d, y, col, t, top):
        g.rect(8, y, W - 16, 110, C["panel"])
        g.frame(8, y, W - 16, 110, col if (d.playing or d.preview) else C["hull"], 2)
        g.text("p16", d.name, 20, y + 10, col)
        g.text("p8", d.title[:40], 52, y + 8, C["text"] if d.wf else C["dim"])
        if d.wf:
            el = d.where() / float(d.rate)
            tot = d.frames / float(d.rate)
            left = max(0.0, (tot - el) / (1.0 + d.pitch))
            g.text("v20", "%d:%02d" % (el // 60, el % 60), 52, y + 20, C["soft"])
            g.text("v20", "-%d:%02d" % (left // 60, left % 60), 112, y + 20, C["orange"] if left < 30 else C["muted"])
            state = "PLAY" if d.playing else ("CUE" if d.preview else ("FIM" if d.ended else "PAUSA"))
            g.text("p8", state, W - 20, y + 10, C["green"] if d.playing else C["orange"], 255, "right")
            flt = self.mix.fa if d is self.a else self.mix.fb
            g.text("p8", "FILTRO " + flt.label(), W - 76, y + 10, C["orange"] if flt.val else C["dim"], 255, "right")
            # pitch + tempo
            g.text("v20", "PITCH %+.2f%%" % (d.pitch * 100), 200, y + 20, C["text"] if d.pitch else C["dim"])
            if d.bpm:
                g.text("v20", "BPM %.1f > %.1f" % (d.bpm, d.eff_bpm()), 330, y + 20, col)
            else:
                g.text("v20", "BPM ? (bate o tempo)", 330, y + 20, C["dim"])
            if d.nudge:
                g.text("p8", "<<" if d.nudge < 0 else ">>", W - 20, y + 26, C["orange"], 255, "right")
            # overview
            ox, oy, ow, oh = 20, y + 46, W - 64, 40
            g.rect(ox, oy, ow, oh, C["off"])
            bars = getattr(d, "_ovbars", None)
            if bars is None or getattr(d, "_ovsrc", None) is not d.overview:
                ov = d.overview
                if not ov and d.peaks:
                    n = len(d.peaks)
                    est = max(1, int(d.frames / d.block))
                    ov = [d.peaks[int(c * est / 600)] if int(c * est / 600) < n else 0 for c in range(600)]
                bars = []
                for c in range(0, len(ov), 2):
                    h = ov[c] * oh // 255
                    bars.append((ox + c * ow // 600, oy + oh // 2 - h // 2, 2, max(1, h)))
                if d.overview:                         # final: cache the rects, never rebuild per frame
                    d._ovbars, d._ovsrc = bars, d.overview
            if bars:
                g.rects(bars, col, 170)
            pr = d.where() / float(max(1, d.frames))
            g.rect(ox + int(ow * pr) - 1, oy - 3, 3, oh + 6, C["white"])
            cx = ox + int(ow * d.cue / float(max(1, d.frames)))
            g.rect(cx - 1, oy + oh, 3, 6, C["orange"])
            # level meter
            g.rect(W - 34, y + 46, 14, 40, C["off"])
            lv = int(40 * min(1.0, d.level))
            g.rect(W - 34, y + 86 - lv, 14, lv, C["green"] if lv < 34 else C["orange"])
        else:
            g.text("v20", "SELECT + %s para carregar uma música" % ("L1" if top else "R1"), 52, y + 50, C["muted"])

    def draw_zoom(self, g, d, y, col):
        g.rect(8, y, W - 16, 56, C["deck"])
        g.rect(W // 2 - 1, y, 2, 56, C["white"])
        if not (d.wf and d.peaks):
            return
        peaks = d.peaks
        n = len(peaks)
        cols = 160
        span = ZOOM_S * 100.0 * 2 / cols                   # peak blocks per column (blocks are 10 ms)
        centre = d.where() / float(d.block)
        bars = []
        x0 = 8
        cw = (W - 16) / float(cols)
        for c in range(cols):
            i0 = int(centre + (c - cols / 2) * span)
            if i0 < 0 or i0 >= n:
                continue
            i1 = min(n, int(i0 + span) + 1)
            h = max(peaks[i0:i1]) * 26 // 255
            bars.append((int(x0 + c * cw), y + 28 - h, max(1, int(cw)), 2 * h + 1))
        g.rects(bars, col, 220)
        if d.cue:
            dx = (d.cue / float(d.block) - centre) / span * cw
            if abs(dx) < W // 2 - 10:
                g.rect(int(W // 2 + dx), y, 2, 56, C["orange"])

    def draw_mixer(self, g, t):
        mx = self.mix
        y = 412
        g.rect(8, y, W - 16, 22, C["panel"])
        x0, x1 = 150, W - 150
        g.rect(x0, y + 9, x1 - x0, 4, C["hull"])
        kx = int(x0 + (x1 - x0) * mx.xf)
        g.rect(kx - 8, y + 2, 16, 18, C["text"])
        g.rect(kx - 1, y + 2, 2, 18, C["void"])
        g.text("p8", "A", x0 - 14, y + 7, C["cyan"])
        g.text("p8", "B", x1 + 6, y + 7, C["violet"])
        if mx.split:
            cue = ("A" if mx.cue_a else "") + ("B" if mx.cue_b else "")
            g.text("p8", "SPLIT  CUE:%s" % (cue or "-"), 16, y + 7, C["orange"])
        else:
            g.text("p8", "CROSSFADER", 16, y + 7, C["muted"])
        ga, gb = mx.gains()
        g.text("v20", "%d%% / %d%%" % (ga * 100, gb * 100), W - 16, y + 1, C["dim"], 255, "right")

    def draw_browser(self, g):
        x, y, w, h = 40, 64, W - 80, 340
        g.rect(x, y, w, h, C["panel"], 248)
        g.frame(x, y, w, h, self.app.accent, 3)
        g.text("p8", "CARREGAR NO DECK %s" % self.browse.name, x + 16, y + 12, self.app.accent)
        if not self.lib:
            g.text("v20", "Sem músicas. Copia para ports/mothership/music", x + 16, y + 40, C["soft"])
            return
        top = max(0, min(self.bsel - 6, len(self.lib) - 13))
        for row, i in enumerate(range(top, min(len(self.lib), top + 13))):
            it = self.lib[i]
            yy = y + 34 + row * 22
            sel = i == self.bsel
            if sel:
                g.rect(x + 8, yy - 2, w - 16, 22, C["hull"])
            g.text("v20", it["title"][:40], x + 16, yy, C["text"] if sel else C["soft"])
            tag = it["tag"] + (" %s BPM" % it["bpm"] if it.get("bpm") else "")
            g.text("v20", tag, x + w - 16, yy, C["cyan"] if sel else C["dim"], 255, "right")

