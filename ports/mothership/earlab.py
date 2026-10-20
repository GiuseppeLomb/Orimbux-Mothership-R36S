# EAR LAB - ear training: intervals, chords, scales, notes (relative to C) and tempo (BPM).
# Levels unlock on their own (80% of the last 10 right). Answers on the d-pad OR the face buttons (same cross).
import math
import os
import random
import time
import wave

import engine
from engine import C, W, SR, audioop, Voice

D = os.path.join(engine.ASSETS, "ear")
SAVE = os.path.join(engine.APP, "earlab.json")
NOTE_NAMES = ["DO", "DO#", "RE", "RE#", "MI", "FA", "FA#", "SOL", "SOL#", "LA", "LA#", "SI"]
CROSS = {"up": 0, "x": 0, "left": 1, "y": 1, "right": 2, "a": 2, "down": 3, "b": 3}
SLOT_GLYPH = [("up", "X"), ("left", "Y"), ("right", "A"), ("down", "B")]

INTERVALS = [("2a MENOR", 1), ("2a MAIOR", 2), ("3a MENOR", 3), ("3a MAIOR", 4), ("4a PERFEITA", 5),
             ("TRITONO", 6), ("5a PERFEITA", 7), ("6a MENOR", 8), ("6a MAIOR", 9), ("7a MENOR", 10),
             ("7a MAIOR", 11), ("OITAVA", 12)]
CHORDS = [("MAIOR", [0, 4, 7]), ("MENOR", [0, 3, 7]), ("DIMINUTO", [0, 3, 6]), ("AUMENTADO", [0, 4, 8]),
          ("7a MAIOR", [0, 4, 7, 11]), ("DOMINANTE 7", [0, 4, 7, 10]), ("MENOR 7", [0, 3, 7, 10]),
          ("SUS2", [0, 2, 7]), ("SUS4", [0, 5, 7]), ("MEIO-DIM", [0, 3, 6, 10]), ("DIM 7", [0, 3, 6, 9]),
          ("ADD9", [0, 4, 7, 14])]
SCALES = [("MAIOR", [0, 2, 4, 5, 7, 9, 11, 12]), ("MENOR", [0, 2, 3, 5, 7, 8, 10, 12]),
          ("PENTA MAIOR", [0, 2, 4, 7, 9, 12]), ("PENTA MENOR", [0, 3, 5, 7, 10, 12]),
          ("MENOR HARM.", [0, 2, 3, 5, 7, 8, 11, 12]), ("BLUES", [0, 3, 5, 6, 7, 10, 12]),
          ("DORICO", [0, 2, 3, 5, 7, 9, 10, 12]), ("MIXOLIDIO", [0, 2, 4, 5, 7, 9, 10, 12]),
          ("LIDIO", [0, 2, 4, 6, 7, 9, 11, 12]), ("FRIGIO", [0, 1, 3, 5, 7, 8, 10, 12]),
          ("MENOR MELOD.", [0, 2, 3, 5, 7, 9, 11, 12])]
# pools per level (names)
LEVELS = {
    "INTERVALOS": [["3a MAIOR", "5a PERFEITA", "OITAVA"],
                   ["3a MAIOR", "5a PERFEITA", "OITAVA", "4a PERFEITA", "3a MENOR"],
                   ["3a MAIOR", "5a PERFEITA", "OITAVA", "4a PERFEITA", "3a MENOR", "2a MAIOR", "6a MAIOR"],
                   ["3a MAIOR", "5a PERFEITA", "OITAVA", "4a PERFEITA", "3a MENOR", "2a MAIOR", "6a MAIOR",
                    "2a MENOR", "6a MENOR", "7a MENOR"],
                   [n for n, _ in INTERVALS], [n for n, _ in INTERVALS]],
    "ACORDES": [["MAIOR", "MENOR"], ["MAIOR", "MENOR", "DIMINUTO", "AUMENTADO"],
                ["MAIOR", "MENOR", "7a MAIOR", "DOMINANTE 7", "MENOR 7"],
                ["MAIOR", "MENOR", "DIMINUTO", "AUMENTADO", "7a MAIOR", "DOMINANTE 7", "MENOR 7", "SUS2", "SUS4"],
                [n for n, _ in CHORDS]],
    "ESCALAS": [["MAIOR", "MENOR"], ["MAIOR", "MENOR", "PENTA MAIOR", "PENTA MENOR"],
                ["MAIOR", "MENOR", "PENTA MAIOR", "PENTA MENOR", "MENOR HARM.", "BLUES"],
                ["MAIOR", "MENOR", "MENOR HARM.", "BLUES", "DORICO", "MIXOLIDIO"], [n for n, _ in SCALES]],
    "NOTAS": [["DO", "MI", "SOL"], ["DO", "RE", "MI", "FA", "SOL"], ["DO", "RE", "MI", "FA", "SOL", "LA", "SI"],
              NOTE_NAMES],
    "TEMPO": [20, 12, 8, 5, 3],          # minimum BPM gap between the 4 options
}
MODES = [("INTERVALOS", "Duas notas: que distancia ha entre elas?"),
         ("ACORDES", "Que tipo de acorde ouviste?"),
         ("ESCALAS", "Que escala subiu?"),
         ("NOTAS", "Ouves um DO e depois outra nota: qual e?"),
         ("TEMPO", "Ouve o metronomo: qual e o BPM?")]


class EarLab(object):
    name = "EAR LAB"

    def __init__(self, app):
        self.app = app
        self.raw = {}
        self.cache = {}
        self.st = engine.load_save(SAVE) or {}
        self.state = "menu"
        self.msel = 0
        self.q = None
        self.streak = 0
        self.sound_end = 0.0

    # ---------------------------------------------------------------- persistence / stats
    def stats(self, mode):
        return self.st.setdefault(mode, {"level": 0, "hist": [], "total": 0, "right": 0, "best": 0})

    def save(self):
        try:
            engine.write_json(SAVE, self.st)
        except Exception:
            pass

    def record(self, ok):
        s = self.stats(self.q["mode"])
        s["total"] += 1
        s["right"] += 1 if ok else 0
        s["hist"] = (s["hist"] + [1 if ok else 0])[-10:]
        self.streak = self.streak + 1 if ok else 0
        s["best"] = max(s["best"], self.streak)
        maxlvl = len(LEVELS[self.q["mode"]]) - 1
        up = False
        if len(s["hist"]) >= 10 and sum(s["hist"]) >= 8 and s["level"] < maxlvl:
            s["level"] += 1
            s["hist"] = []
            up = True
        self.save()
        return up

    # ---------------------------------------------------------------- sound
    def tone(self, midi):
        d = self.cache.get(midi)
        if d is None:
            base = min((48, 60, 72), key=lambda b: abs(b - midi))
            mono = self.raw.get(base)
            if mono is None:
                wf = wave.open(os.path.join(D, "ep_%d.wav" % base), "rb")
                mono = self.raw[base] = wf.readframes(wf.getnframes())
                wf.close()
            r = 2 ** ((midi - base) / 12.0)
            if midi != base:
                mono = audioop.ratecv(mono, 2, 1, int(SR * r), SR, None)[0]
            if len(self.cache) > 36:
                self.cache.clear()
            d = self.cache[midi] = audioop.tostereo(mono, 2, 1, 1)
        return d

    def play(self, events, gain=0.9):
        """events: [(seconds, data)] scheduled sample-accurately on the mixer clock"""
        m = self.app.mixer
        with m.lock:
            m.voices = [v for v in m.voices if v.group != "ear"]
            t0 = m.clock + int(0.05 * SR)
            for i, (sec, data) in enumerate(events):
                m.voices.append(Voice("ear%d" % i, "ear", data, None, False, gain, t0 + int(sec * SR)))
        last = max(sec + len(data) / 4.0 / SR for sec, data in events) if events else 0
        self.sound_end = time.time() + min(last, 4.0)

    def notes(self, midis, gap):
        self.play([(i * gap, self.tone(n)) for i, n in enumerate(midis)], 0.8 if gap else 0.55)

    def clicks(self, bpm, n=8):
        hi, lo = self.app.snd.get("click_hi"), self.app.snd.get("click_lo")
        if hi and lo:
            self.play([(i * 60.0 / bpm, hi if i % 4 == 0 else lo) for i in range(n)], 1.2)

    # ---------------------------------------------------------------- questions
    def new_question(self, mode):
        lvl = self.stats(mode)["level"]
        pool = LEVELS[mode][min(lvl, len(LEVELS[mode]) - 1)]
        q = {"mode": mode, "level": lvl, "answered": None}
        if mode == "TEMPO":
            gap = pool
            bpm = random.randint(72, 170)
            opts = {bpm}
            while len(opts) < 4:
                c = bpm + random.choice([-1, 1]) * random.randint(gap, gap * 4)
                if 60 <= c <= 200 and all(abs(c - o) >= gap for o in opts):
                    opts.add(c)
            opts = sorted(opts)
            q.update(opts=["%d BPM" % o for o in opts], answer=opts.index(bpm), bpm=bpm, keys=[])
        else:
            correct = random.choice(pool)
            others = [p for p in pool if p != correct]
            random.shuffle(others)
            opts = [correct] + others[:3]
            random.shuffle(opts)
            q.update(opts=opts, answer=opts.index(correct), name=correct)
            if mode == "INTERVALOS":
                semis = dict(INTERVALS)[correct]
                root = random.randint(50, 66)
                style = "asc" if lvl < 2 else random.choice(["asc", "desc"] if lvl < 4 else ["asc", "desc", "harm"])
                q["keys"] = [root, root + semis]
                q["style"] = style
            elif mode == "ACORDES":
                root = random.randint(50, 62)
                q["keys"] = [root + i for i in dict(CHORDS)[correct]]
            elif mode == "ESCALAS":
                root = random.randint(53, 62)
                q["keys"] = [root + i for i in dict(SCALES)[correct]]
            elif mode == "NOTAS":
                q["keys"] = [60, 60 + NOTE_NAMES.index(correct)]
        self.q = q
        self.play_question()

    def play_question(self, which=None):
        q = self.q
        mode = q["mode"]
        if mode == "TEMPO":
            self.clicks(q["bpm"] if which is None else int(q["opts"][which].split()[0]))
            return
        keys = q["keys"]
        if which is not None:                       # hear another option (after answering) to compare
            keys = self.keys_for(q["opts"][which], keys[0])
        if mode == "INTERVALOS":
            style = q["style"]
            if style == "harm":
                self.notes(keys, 0)
            elif style == "desc":
                self.notes(list(reversed(keys)), 0.7)
            else:
                self.notes(keys, 0.7)
        elif mode == "ACORDES":
            self.play([(i * 0.12, self.tone(n)) for i, n in enumerate(keys)] +
                      [(0.9, self.tone(n)) for n in keys], 0.5)
        elif mode == "ESCALAS":
            self.notes(keys, 0.32)
        elif mode == "NOTAS":
            self.notes(keys, 0.9)

    def keys_for(self, name, root):
        mode = self.q["mode"]
        if mode == "INTERVALOS":
            return [root, root + dict(INTERVALS)[name]]
        if mode == "ACORDES":
            return [root + i for i in dict(CHORDS)[name]]
        if mode == "ESCALAS":
            return [root + i for i in dict(SCALES)[name]]
        return [60, 60 + NOTE_NAMES.index(name)]

    def answer(self, i):
        q = self.q
        if i >= len(q["opts"]):
            return
        q["answered"] = i
        ok = i == q["answer"]
        q["ok"] = ok
        q["levelup"] = self.record(ok)
        if not ok:
            self.play_question()           # wrong: hear the right one again
        self.state = "feedback"

    # ---------------------------------------------------------------- section interface
    def enter(self):
        self.state = "menu"

    def leave(self):
        self.app.mixer.kill_group("ear")

    def on_select(self):
        if self.state == "menu":
            self.app.go("bridge")
        else:
            self.app.mixer.kill_group("ear")
            self.state = "menu"

    def on(self, kind, b):
        if kind not in ("press", "repeat"):
            return
        if self.state == "menu":
            if b in ("up", "down"):
                self.msel = (self.msel + (1 if b == "down" else -1)) % len(MODES)
                self.app.ui_move()
            elif b in ("a", "start") and kind == "press":
                self.app.ui_ok()
                self.streak = 0
                self.state = "question"
                self.new_question(MODES[self.msel][0])
            elif b == "b" and kind == "press":
                self.app.go("bridge")
            return
        if kind != "press":
            return
        if b == "r1":
            self.play_question()
        elif self.state == "question":
            if b == "l1" and self.q["mode"] != "TEMPO":
                self.notes(self.q["keys"][:1], 0)
            elif b in CROSS:
                self.answer(CROSS[b])
        elif self.state == "feedback":
            if b == "l1" and self.q["answered"] is not None:
                self.play_question(self.q["answered"])
            elif b in CROSS or b == "start":
                self.state = "question"
                self.new_question(self.q["mode"])

    def update(self, dt):
        pass

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        import app as appmod
        app = self.app
        g.clear(C["void"])
        appmod.header(g, app, "EAR LAB", "earlab")
        if self.state == "menu":
            self.draw_menu(g, t)
        else:
            self.draw_question(g, t)

    def draw_menu(self, g, t):
        app = self.app
        for i, (mode, desc) in enumerate(MODES):
            y = 64 + i * 66
            sel = i == self.msel
            s = self.stats(mode)
            if sel:
                g.glow(16, y, W - 32, 58, app.accent, 0.4 + 0.3 * math.sin(t * 5))
            g.rect(16, y, W - 32, 58, C["hull"] if sel else C["panel"])
            g.frame(16, y, W - 32, 58, app.accent if sel else C["hull"], 2)
            g.text("p16", mode, 32, y + 10, C["text"] if sel else C["soft"])
            g.text("v20", desc, 32, y + 32, C["muted"])
            nl = len(LEVELS[mode])
            g.text("p8", "NIVEL %d/%d" % (s["level"] + 1, nl), W - 32, y + 12, C["cyan"], 255, "right")
            if s["total"]:
                g.text("v20", "%d%% de %d  -  serie %d" % (100 * s["right"] // s["total"], s["total"], s["best"]),
                       W - 32, y + 30, C["dim"], 255, "right")
        appmod_footer(g, [("A", "comecar", C["cyan"]), ("cima/baixo", "exercicio", C["cyan"]),
                          ("SELECT", "bridge", C["violet"])])

    def draw_question(self, g, t):
        app = self.app
        q = self.q
        mode = q["mode"]
        s = self.stats(mode)
        g.text("p16", mode, 20, 62, app.accent)
        g.text("p8", "NIVEL %d" % (s["level"] + 1), 20, 86, C["cyan"])
        hist = s["hist"]
        for i in range(10):
            col = C["hull"] if i >= len(hist) else (C["green"] if hist[i] else (255, 80, 90))
            g.rect(110 + i * 14, 86, 10, 8, col)
        g.text("v20", "serie %d" % self.streak, W - 20, 62, C["soft"], 255, "right")
        g.text("v20", dict(MODES)[mode], W // 2, 110, C["muted"], 255, "center")
        # sound visual
        playing = time.time() < self.sound_end
        bars = []
        for i in range(32):
            h = int(4 + (28 * abs(math.sin(t * 7 + i * 0.6)) if playing else 0))
            bars.append((W // 2 - 32 * 6 + i * 12, 150 - h // 2, 8, h))
        g.rects(bars, C["violet"] if playing else C["hull"])
        # answers on a cross
        cx, cy, bw, bh = W // 2, 268, 196, 46
        pos = [(cx - bw // 2, cy - 78), (cx - bw - 14, cy - 23), (cx + 14, cy - 23), (cx - bw // 2, cy + 32)]
        fb = self.state == "feedback"
        for i, opt in enumerate(q["opts"]):
            x, y = pos[i]
            col, bg = C["hullhi"], C["panel"]
            if fb and i == q["answer"]:
                col, bg = C["green"], (20, 70, 40)
            elif fb and i == q["answered"]:
                col, bg = (255, 80, 90), (80, 20, 30)
            g.rect(x, y, bw, bh, bg)
            g.frame(x, y, bw, bh, col, 2)
            d, f = SLOT_GLYPH[i]
            g.tri(x + 8, y + 9, 6, d, C["cyan"])
            g.text("p8", f, x + 30, y + 10, C["violet"])
            g.text("v28" if len(opt) <= 11 else "v20", opt, x + bw // 2 + 14, y + (10 if len(opt) <= 11 else 13),
                   C["text"], 255, "center")
        if fb:
            ok = q["ok"]
            g.text("p16", "CERTO!" if ok else "ERA: %s" % q["opts"][q["answer"]], W // 2, 362,
                   C["green"] if ok else (255, 110, 120), 255, "center")
            if q.get("levelup"):
                g.text("p8", "SUBISTE DE NIVEL! NOVAS RESPOSTAS DESBLOQUEADAS", W // 2, 384, C["orange"], 255, "center")
            if mode != "TEMPO":
                self.draw_keys(g, q["keys"], 396)
        appmod_footer(g, ([("R1", "ouvir outra vez", C["cyan"]), ("L1", "ouvir a tua", C["cyan"]),
                           ("A/qualquer", "seguinte", C["violet"])] if fb else
                          [("cruz", "responder", C["cyan"]), ("R1", "repetir", C["cyan"]),
                           ("L1", "1a nota" if mode != "TEMPO" else "-", C["cyan"]), ("SELECT", "menu", C["violet"])]))

    def draw_keys(self, g, keys, y):
        """two-octave keyboard (from the C below the lowest note) with the played notes lit"""
        lo = (min(keys) // 12) * 12
        whites = [n for n in range(lo, lo + 25) if n % 12 in (0, 2, 4, 5, 7, 9, 11)]
        kw = 16
        x0 = W // 2 - len(whites) * kw // 2
        wx = {}
        for i, n in enumerate(whites):
            wx[n] = x0 + i * kw
            g.rect(x0 + i * kw, y, kw - 2, 30, C["orange"] if n in keys else C["soft"])
        for n in range(lo, lo + 25):
            if n % 12 in (1, 3, 6, 8, 10) and n - 1 in wx:
                g.rect(wx[n - 1] + kw - 6, y, 9, 18, C["orange"] if n in keys else C["void"])


def appmod_footer(g, items):
    import app as appmod
    appmod.footer(g, items)
