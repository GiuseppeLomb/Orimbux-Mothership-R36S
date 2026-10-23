# ORIMBOX - a crew of 7 aliens that sing and beatbox (in the spirit of Incredibox). Give each alien a sound from
# 4 groups of 5 (beats, effects, melodies, voices): every loop is 4 bars at 100 BPM in A minor, all in sync, so
# any mix works. 5 secret combos unlock animated bonus choruses. START records the mix (it shows up in
# BEAT DUEL and TWIN DECKS like any session). Sounds: tools/build_orimbox.py (CC0 samples + formant voices).
import math
import os
import random
import threading
import time
import wave

import sdl2

import engine
import ui
from engine import C, W, SR, BUF, Voice, audioop, draw_ship
from voidrunner import bake

D = os.path.join(engine.ASSETS, "orimbox")
SAVE = os.path.join(engine.APP, "orimbox.json")
SLOTS = 7
S = 4                                   # alien art pixel -> screen pixels
PINK = (255, 110, 170)
CATS = [("beat", "BATIDAS", C["orange"]), ("fx", "EFEITOS", C["cyan"]), ("melody", "MELODIAS", C["violet"]),
        ("voice", "VOZES", PINK)]
CAT_COL = dict((k, c) for k, _, c in CATS)
CAT_NAME = dict((k, n) for k, n, _ in CATS)
GAIN = {"beat": 1.3, "fx": 1.15, "melody": 1.25, "voice": 1.25}     # (each loop is mastered to the same loudness)
BODY = [(110, 222, 124), (86, 204, 226), (172, 126, 244), (244, 132, 192), (246, 184, 84), (120, 170, 255),
        (204, 232, 92)]
IDLE = (74, 76, 118)
FEET_Y = 344
SLOT_X = [64 + i * 85 for i in range(SLOTS)]

# 9x9 icons, one per sound ('#' = ink)
ICONS = {
    "bumtss": ["..#####..", ".#.....#.", "#..###..#", "#.#...#.#", "#.#.#.#.#", "#.#...#.#", "#..###..#",
               ".#.....#.", "..#####.."],
    "tchka": [".........", "..##.##..", ".#..#..#.", "#.......#", "#########", "#.......#", ".#.....#.",
              "..#####..", "........."],
    "tabla": [".........", "###...##.", "#.#..#..#", "###..####", ".#....##.", ".#....##.", "###..####",
              "###..####", "........."],
    "cajon": ["#########", "#.......#", "#.......#", "#..###..#", "#..#.#..#", "#..###..#", "#.......#",
              "#.......#", "#########"],
    "shaker": [".....###.", "....#####", "#..######", "...######", "#...####.", "...####..", "#..###...",
               ".........", "........."],
    "zap": ["....####.", "...####..", "..####...", ".#######.", "...####..", "..###....", ".###.....",
            ".##......", ".#......."],
    "risco": ["..####..#", ".#....#.#", "#..##..##", "#.#..#.#.", "#.#..#.#.", "#..##..#.", ".#....#..",
              "..####...", "........."],
    "robo": ["....#....", "....#....", ".#######.", ".#..#..#.", ".#######.", ".#.###.#.", ".#######.",
             "..#...#..", ".##...##."],
    "boing": [".#######.", "..#...#..", ".#######.", "..#...#..", ".#######.", "..#...#..", ".#######.",
              "....#....", "...###..."],
    "cosmos": ["....#....", "....#....", "...###...", "#########", ".#######.", "..#####..", "..##.##..",
               ".##...##.", ".#.....#."],
    "baixo": [".........", ".###...#.", "#...#....", "....#..#.", "...#.....", "..#......", ".#.......",
              "#........", "........."],
    "kalimba": [".#.#.#.#.", ".#.#.#.#.", ".#.#.#.#.", "#########", "#.......#", "#..###..#", "#..#.#..#",
                "#..###..#", "#########"],
    "ocarina": [".........", "...####..", ".###...##", "#.#.#.#.#", "#.......#", "#.#.#.#.#", ".#.....#.",
                "..#####..", "........."],
    "marimba": ["#........", "#.#......", "#.#.#....", "#.#.#.#..", "#.#.#.#.#", "#########", ".#.....#.",
                ".#.....#.", "........."],
    "nuvem": [".........", "...###...", "..#####..", ".#######.", "#########", "#########", ".#######.",
              ".........", "........."],
    "uuu": [".........", ".#..#..#.", "#.##.##.#", "#.##.##.#", ".#..#..#.", ".........", ".#######.",
            ".........", "........."],
    "bada": [".#######.", "#.......#", "#.#.#.#.#", "#.......#", ".#######.", "..##.....", ".#.......",
             ".........", "........."],
    "aah": [".........", "#########", "#.......#", "#.#####.#", "#.#...#.#", ".#.###.#.", "..#...#..",
            "...###...", "........."],
    "dum": [".....##..", ".....#.#.", ".....#..#", ".....#...", ".....#...", "..####...", ".#####...",
            ".####....", "........."],
    "orimbux": [".........", "...###...", "..#...#..", ".#######.", "#########", ".#.#.#.#.", "..#...#..",
                ".........", "........."],
}

# the 7 aliens: body ellipse (cx, cy, rx, ry in a 18x24 art grid), eyes, mouth row, what grows on the head
DESIGNS = [
    dict(cy=15, rx=6.2, ry=6.2, eyes=[(6, 12), (10, 12)], mouth=16, head="balls"),
    dict(cy=14, rx=5.2, ry=8.0, eyes=[(8, 10)], mouth=14, head="one", big=True),
    dict(cy=16, rx=7.4, ry=5.4, eyes=[(4, 14), (8, 13), (12, 14)], mouth=17, head="none"),
    dict(cy=15, rx=6.0, ry=7.0, eyes=[(6, 12), (10, 12)], mouth=16, head="horns"),
    dict(cy=16, rx=5.6, ry=6.0, eyes=[(6, 13), (10, 13)], mouth=17, head="spikes"),
    dict(cy=15, rx=6.4, ry=6.4, eyes=[(8, 11)], mouth=16, head="balls", big=True),
    dict(cy=15, rx=6.0, ry=7.0, eyes=[(6, 12), (10, 12)], mouth=16, head="curl"),
]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def alien_grid(d, cat):
    """an 18x24 char grid for one alien; cat None = asleep (grey), else the outfit of that sound group"""
    w, h = 18, 24
    cx = 9.0
    g = [["." for _ in range(w)] for _ in range(h)]
    body = set()
    for y in range(h):
        for x in range(w):
            if ((x + 0.5 - cx) / d["rx"]) ** 2 + ((y + 0.5 - d["cy"]) / d["ry"]) ** 2 <= 1.0:
                body.add((x, y))
    bottom = max(y for _, y in body)
    for fx in (int(cx) - 3, int(cx) + 2):                    # legs
        for y in range(bottom - 1, min(h - 1, bottom + 3)):
            body.add((fx, y))
            body.add((fx + 1, y))
    top = min(y for _, y in body)
    for (x, y) in body:
        u, v = (x + 0.5 - cx) / d["rx"], (y + 0.5 - d["cy"]) / d["ry"]
        ch = "B"
        if u + v < -0.75:
            ch = "L"
        elif u + v > 0.75 or y > bottom:
            ch = "D"
        if (u / 0.55) ** 2 + ((v - 0.45) / 0.45) ** 2 <= 1.0 and y <= bottom:
            ch = "E"                                          # belly
        g[y][x] = ch
    # arms
    my = int(d["cy"]) + 1
    for side in (-1, 1):
        x0 = int(cx + side * (d["rx"] + 0.2)) + (0 if side > 0 else -1)
        for k in range(2):
            x = x0 + side * k
            if 0 <= x < w:
                g[my - k][x] = "B"
                body.add((x, my - k))
    # what grows on the head
    hx = int(cx)
    if d["head"] in ("one", "balls"):
        stalks = [(hx, 0)] if d["head"] == "one" else [(hx - 3, -1), (hx + 2, 1)]
        for sx, lean in stalks:
            for k in range(1, 4):
                x, y = sx + (lean if k == 3 else 0), top - k
                if 0 <= y < h and 0 <= x < w:
                    g[y][x] = "D"
                    body.add((x, y))
            bx, by = sx + lean, top - 4
            for x, y in ((bx, by), (bx + 1, by), (bx, by - 1), (bx + 1, by - 1)):
                if 0 <= y < h and 0 <= x < w:
                    g[y][x] = "G"
                    body.add((x, y))
    elif d["head"] == "horns":
        for sx, lean in ((hx - 3, -1), (hx + 3, 1)):
            for k in range(1, 3):
                x, y = sx + (lean if k == 2 else 0), top - k + 1
                if 0 <= y < h and 0 <= x < w:
                    g[y][x] = "H"
                    body.add((x, y))
    elif d["head"] == "spikes":
        for sx in (hx - 3, hx, hx + 3):
            for k in range(1, 3 if sx == hx else 2):
                if top - k >= 0:
                    g[top - k][sx] = "D"
                    body.add((sx, top - k))
    elif d["head"] == "curl":
        pts = [(hx, top - 1), (hx, top - 2), (hx + 1, top - 3), (hx + 2, top - 3), (hx + 2, top - 2)]
        for x, y in pts:
            if 0 <= y:
                g[y][x] = "D"
                body.add((x, y))
    # outfit of the sound group
    ey = min(e[1] for e in d["eyes"])
    if cat == "beat":                                         # headphones
        for x in range(int(cx - d["rx"]) + 1, int(cx + d["rx"]) + 1):
            y = top - 1 if abs(x + 0.5 - cx) < d["rx"] * 0.6 else top
            if 0 <= y < h:
                g[y][x] = "A"
                body.add((x, y))
        for side in (-1, 1):
            x = int(cx + side * d["rx"]) + (0 if side > 0 else -1)
            for y in range(ey - 1, ey + 2):
                if 0 <= x < w:
                    g[y][x] = "A"
                    body.add((x, y))
    elif cat == "fx":                                          # visor over the eyes
        for (x, y) in list(body):
            if ey - 1 <= y <= ey + 1 and g[y][x] in "BLDE":
                g[y][x] = "A" if y != ey - 1 else "a"
    elif cat == "melody":                                      # bow tie
        y = d["mouth"] + 3
        for x, ch in ((hx - 2, "A"), (hx - 1, "a"), (hx, "A"), (hx + 1, "a"), (hx + 2, "A")):
            if (x, y) in body:
                g[y][x] = ch
        for x in (hx - 2, hx + 2):
            if (x, y - 1) in body:
                g[y - 1][x] = "A"
            if (x, y + 1) in body:
                g[y + 1][x] = "A"
    elif cat == "voice":                                       # a microphone by the mouth
        mx = int(cx + d["rx"]) - 1
        for x, y, ch in ((mx, d["mouth"] - 1, "A"), (mx + 1, d["mouth"] - 1, "A"), (mx, d["mouth"], "A"),
                         (mx + 1, d["mouth"], "a"), (mx, d["mouth"] + 1, "K"), (mx, d["mouth"] + 2, "K")):
            if 0 <= x < w:
                g[y][x] = ch
                body.add((x, y))
    # outline
    for y in range(h):
        for x in range(w):
            if g[y][x] == "." and any((x + dx, y + dy) in body for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                g[y][x] = "K"
    return ["".join(r) for r in g]


def palette(base, cat):
    if cat is None:
        base = IDLE
    acc = CAT_COL.get(cat, (120, 120, 160))
    return {"K": (12, 8, 30), "B": base, "L": mix(base, (255, 255, 255), 0.35), "D": mix(base, (0, 0, 0), 0.38),
            "E": mix(base, (255, 255, 255), 0.55) if cat else mix(base, (255, 255, 255), 0.18),
            "G": acc if cat else (110, 110, 150), "H": (236, 228, 255) if cat else (120, 120, 150),
            "A": acc, "a": mix(acc, (0, 0, 0), 0.35)}


class Orimbox(object):
    name = "ORIMBOX"

    def __init__(self, app):
        self.app = app
        self.meta = None
        self.mono = {}             # id -> mono s16 bytes (loaded in the background)
        self.stereo = {}           # id -> stereo s16 bytes, made when a sound goes on stage
        self.loading = None
        self.load_err = None
        self.slot = [None] * SLOTS         # sound id per alien
        self.voice = [None] * SLOTS
        self.muted = [False] * SLOTS
        self.solo = None
        self.t0 = None             # mixer frame where the loop started
        self.focus = "bar"         # "bar" (the sounds) or "stage" (the aliens)
        self.icon = 0
        self.sel = 0
        self.tex = {}
        self.icons = {}
        self.found = []
        self.complete = set()
        self.bonus = None          # [id, start frame, end frame]
        self.queue = []
        self.msg = ("", 0.0)
        self.stars = []
        self.blink = [0.0] * SLOTS
        self.rec_step = None
        self.rec_path = None
        self.load_save()

    # ------------------------------------------------------------ data
    def load_save(self):
        """the secrets already found; a damaged file is kept aside (engine.load_save) and never stops the app"""
        d = engine.load_save(SAVE) or {}
        found = d.get("found", [])
        clean = {"found": [b for b in found if isinstance(b, str) and len(b) < 40][:20] if isinstance(found, list)
                 else []}
        if d:
            engine.check_save(SAVE, d, clean)
        self.found = clean["found"]

    def write_save(self):
        try:
            engine.write_json(SAVE, {"found": self.found})
        except Exception:
            pass

    def load_kit(self):
        """meta + every loop's PCM, in a thread (21 MB from the SD card takes a moment)"""
        try:
            meta = engine.read_json(os.path.join(D, "kit.json"))
            ids = [s["id"] for s in meta["sounds"]] + [b["id"] for b in meta["bonus"]]
            for i, sid in enumerate(ids):
                if sid in self.mono:
                    continue
                with wave.open(os.path.join(D, sid + ".wav"), "rb") as wf:
                    data = wf.readframes(wf.getnframes())
                    if wf.getframerate() != SR or wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                        data = engine.to_std(data, wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
                        data = audioop.tomono(data, 2, 0.5, 0.5)
                n = meta["frames"] * 2                      # every loop exactly one loop long (sync)
                self.mono[sid] = data[:n] + b"\0" * max(0, n - len(data))
                self.progress = (i + 1) / float(len(ids))
            self.meta = meta
        except Exception as e:
            self.load_err = "%s" % (e,)

    def sound(self, sid):
        for s in self.meta["sounds"]:
            if s["id"] == sid:
                return s
        for b in self.meta["bonus"]:
            if b["id"] == sid:
                return b
        return None

    def pcm(self, sid):
        if sid not in self.stereo:
            self.stereo[sid] = audioop.tostereo(self.mono[sid], 2, 1, 1)
        return self.stereo[sid]

    @property
    def L(self):
        return self.meta["frames"] if self.meta else 1

    # ------------------------------------------------------------ lifecycle
    def enter(self):
        m = self.app.mixer
        with m.lock:                        # the crew sings alone (other tempos would clash)
            m.kill_group("reactor")
            for s in m.streams:
                s.fade(0.0, 0.4)
        if self.meta is None and self.loading is None:
            self.progress = 0.0
            self.loading = threading.Thread(target=self.load_kit)
            self.loading.daemon = True
            self.loading.start()
        rnd = random.Random(11)
        self.stars = [(rnd.randrange(W), rnd.randrange(48, 250), rnd.choice((1, 1, 2, 2, 3)), rnd.random())
                      for _ in range(90)]
        self.bake()
        self.focus, self.msg = "bar", ("", 0.0)

    def leave(self):
        self.clear_all()
        if self.app.rec.active() and self.app.rec.src == "ORIMBOX":
            self.app.rec.stop()
        self.rec_done()
        for t in list(self.tex.values()) + list(self.icons.values()):
            sdl2.SDL_DestroyTexture(t[0])
        self.tex, self.icons = {}, {}
        self.stereo = {}                       # 1.7 MB per sound: only kept while the crew is singing
        self.write_save()

    def bake(self):
        ren = self.app.ren
        if self.tex:
            return
        for i, d in enumerate(DESIGNS):
            for cat in (None, "beat", "fx", "melody", "voice"):
                self.tex[(i, cat)] = bake(ren, alien_grid(d, cat), palette(BODY[i], cat), S)
        for sid, grid in ICONS.items():
            self.icons[sid] = bake(ren, grid, {"#": (255, 255, 255)}, 2)

    # ------------------------------------------------------------ the mix
    def now(self):
        """mixer frame of what is being heard"""
        m = self.app.mixer
        return m.clock - (BUF if m.ok else 0)

    def pos(self):
        if self.t0 is None:
            return 0
        return (self.now() - self.t0) % self.L

    def gains(self):
        duck = 1.0
        if self.bonus and self.bonus[1] <= self.app.mixer.clock < self.bonus[2]:
            duck = 0.7
        out = []
        for i in range(SLOTS):
            sid = self.slot[i]
            if sid is None:
                out.append(0.0)
                continue
            on = (self.solo is None or self.solo == i) and not self.muted[i]
            out.append(GAIN[self.sound(sid)["cat"]] * duck if on else 0.0)
        return out

    def apply_gains(self):
        g = self.gains()
        m = self.app.mixer
        with m.lock:
            for i, v in enumerate(self.voice):
                if v is not None:
                    v.gain = g[i]

    def put(self, i, sid):
        """alien i sings sid, in sync with the others (from the right point of the loop)"""
        m = self.app.mixer
        data = self.pcm(sid)
        with m.lock:
            clk = m.clock
            if self.t0 is None or all(s is None for s in self.slot):
                self.t0 = clk
            m.voices = [v for v in m.voices if v.key != "obx%d" % i]
            v = Voice("obx%d" % i, "orimbox", data, None, True, 1.0, clk)
            v.pos = (clk - self.t0) % self.L
            m.voices.append(v)
        self.slot[i], self.voice[i], self.muted[i] = sid, v, False
        self.blink[i] = 0.0
        self.apply_gains()
        self.check_combos()

    def take(self, i):
        if self.slot[i] is None:
            return
        self.app.mixer.kill_key("obx%d" % i)
        self.slot[i], self.voice[i], self.muted[i] = None, None, False
        if self.solo == i:
            self.solo = None
        if all(s is None for s in self.slot):
            self.clear_all()
        else:
            self.apply_gains()
            self.check_combos()

    def clear_all(self):
        m = self.app.mixer
        m.kill_group("orimbox")
        self.slot, self.voice = [None] * SLOTS, [None] * SLOTS
        self.muted, self.solo, self.t0 = [False] * SLOTS, None, None
        self.bonus, self.queue, self.complete = None, [], set()

    def free_slot(self):
        if self.slot[self.sel] is None:
            return self.sel
        for k in range(SLOTS):
            i = (self.sel + k) % SLOTS
            if self.slot[i] is None:
                return i
        return self.sel                        # everyone is busy: the chosen alien changes song

    def give(self, sid):
        if sid in self.slot:                   # already on stage: pick that alien
            self.sel = self.slot.index(sid)
            self.focus = "stage"
            return
        i = self.free_slot()
        self.put(i, sid)
        self.sel = i
        self.app.ui_ok()

    def shuffle(self):
        """a random crew: 5 to 7 aliens, always a beat and a melody"""
        ids = dict((c, [s["id"] for s in self.meta["sounds"] if s["cat"] == c]) for c, _, _ in CATS)
        n = random.randint(5, SLOTS)
        pick = [random.choice(ids["beat"]), random.choice(ids["melody"])]
        rest = [s["id"] for s in self.meta["sounds"] if s["id"] not in pick]
        random.shuffle(rest)
        pick += rest[:n - 2]
        random.shuffle(pick)
        self.clear_all()
        for i, sid in enumerate(pick):
            self.put(i, sid)
        self.say("MISTURA AO ACASO")

    # ------------------------------------------------------------ combos
    def combo_done(self, b):
        on = set(s for s in self.slot if s)
        if b["needs"] == "crew":
            cats = set(self.sound(s)["cat"] for s in on)
            return len(on) == SLOTS and len(cats) == 4
        return set(b["needs"]) <= on

    def check_combos(self):
        now = set(b["id"] for b in self.meta["bonus"] if self.combo_done(b))
        new = [b for b in now if b not in self.complete]
        self.complete = now
        for b in new:
            if b not in self.queue and not (self.bonus and self.bonus[0] == b):
                self.queue.append(b)
        if self.bonus is None and self.queue:
            self.schedule_bonus()

    def schedule_bonus(self):
        if self.t0 is None:
            self.queue = []
            return
        bid = self.queue.pop(0)
        m = self.app.mixer
        with m.lock:
            k = (m.clock - self.t0) // self.L + 1                 # the next time the loop starts again
            start = self.t0 + k * self.L
            v = Voice("obx_bonus", "orimbox", self.pcm(bid), None, True, 1.0, start)
            v.stop = start + 2 * self.L
            m.voices = [x for x in m.voices if x.key != "obx_bonus"]
            m.voices.append(v)
        self.bonus = [bid, start, start + 2 * self.L]
        self.say("SEGREDO A CAMINHO...")

    # ------------------------------------------------------------ input
    def on(self, kind, b):
        if kind not in ("press", "repeat") or self.meta is None:
            return
        snd = self.meta["sounds"]
        if b == "start" and kind == "press":
            self.record()
            return
        if b == "y" and kind == "press":
            self.shuffle()
            return
        if b == "l2" and kind == "press":
            self.clear_all()
            self.say("PALCO VAZIO")
            return
        if self.focus == "bar":
            if b in ("left", "right"):
                self.icon = (self.icon + (1 if b == "right" else -1)) % len(snd)
                self.app.ui_move()
            elif b in ("l1", "r1"):
                g = self.icon // 5
                self.icon = ((g + (1 if b == "r1" else -1)) % 4) * 5
                self.app.ui_move()
            elif b == "a" and kind == "press":
                self.give(snd[self.icon]["id"])
            elif b == "b" and kind == "press":
                sid = snd[self.icon]["id"]
                if sid in self.slot:
                    self.take(self.slot.index(sid))
            elif b == "up":
                self.focus = "stage"
                self.app.ui_move()
        else:
            if b in ("left", "right"):
                self.sel = (self.sel + (1 if b == "right" else -1)) % SLOTS
                self.app.ui_move()
            elif b == "down":
                self.focus = "bar"
                self.app.ui_move()
            elif kind != "press":
                return
            elif b == "a":
                if self.slot[self.sel] is None:
                    self.focus = "bar"
                else:
                    self.muted[self.sel] = not self.muted[self.sel]
                    self.apply_gains()
            elif b == "x" and self.slot[self.sel] is not None:
                self.solo = None if self.solo == self.sel else self.sel
                self.apply_gains()
            elif b == "b":
                self.take(self.sel)

    def say(self, s):
        self.msg = (s, time.time())

    def record(self):
        rec = self.app.rec
        if rec.active():
            rec.stop()
            self.rec_done()
            self.say("GRAVADO: joga-o no BEAT DUEL")
        else:
            rec.start("ORIMBOX", 300)
            self.rec_step, self.rec_path = None, rec.path
            self.say("A GRAVAR A MISTURA")

    def rec_done(self):
        """the session was saved with the ship's tempo: it is the crew's (100 BPM) that BEAT DUEL and TWIN DECKS need"""
        if not self.rec_path:
            return
        p, self.rec_path = self.rec_path + ".json", None
        try:
            d = engine.read_json(p)
            d["bpm"] = self.meta["bpm"] if self.meta else 100
            engine.write_json(p, d)
        except Exception:
            pass

    def rec_spec(self):
        return ("ORIMBOX", 300)

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.meta is None:
            return
        clk = self.app.mixer.clock
        if self.bonus:
            bid, st, en = self.bonus
            if clk >= st and bid not in self.found:
                self.found.append(bid)
                self.write_save()
            if clk >= en:
                self.bonus = None
                self.apply_gains()
                if self.queue:
                    self.schedule_bonus()
            elif clk >= st:
                self.apply_gains()
        # recording: the hits of what is singing become BEAT DUEL notes (one lane per group)
        rec = self.app.rec
        if self.rec_path and not rec.active():               # stopped by itself (5 minutes)
            self.rec_done()
        if rec.active() and self.t0 is not None:
            step_len = self.L / 64.0
            cur = int((clk - self.t0) // step_len)
            if self.rec_step is None:
                self.rec_step = cur
            lane = {"beat": 0, "fx": 1, "melody": 2, "voice": 3}
            g = self.gains()
            while self.rec_step < cur:
                self.rec_step += 1
                k = self.rec_step % 64
                f = self.t0 + self.rec_step * step_len
                for i, sid in enumerate(self.slot):
                    if sid and g[i] > 0 and k in self.sound(sid).get("hits", []):
                        rec.events.append([round(max(0, f - rec.clock0) / float(SR), 3), lane[self.sound(sid)["cat"]]])
        for i in range(SLOTS):
            if self.slot[i] is None:
                self.blink[i] += dt
        # blink now and then
        if random.random() < dt * 0.5:
            self.blink[random.randrange(SLOTS)] = -0.15

    # ------------------------------------------------------------ drawing
    def env(self, sid):
        """0..1: how loud this sound is right now (drives mouths and dancing)"""
        e = self.sound(sid)["env"]
        k = int(self.pos() * self.meta["env_fps"] / SR) % len(e)
        return e[k] / 99.0

    def draw(self, g, t, dt):
        g.clear((10, 6, 30))
        if self.meta is None:
            self.draw_loading(g, t)
            return
        bonus = self.bonus if (self.bonus and self.bonus[1] <= self.app.mixer.clock < self.bonus[2]) else None
        self.draw_sky(g, t, bonus)
        self.draw_header(g, t)
        self.draw_stage(g, t, bonus)
        self.draw_bar(g, t)
        ui.footer(g, [("A", "dar som" if self.focus == "bar" else "silenciar"),
                      ("B", "tirar"), ("cima/baixo", "palco/sons"), ("Y", "ao acaso")], self.app, hints=False)
        if bonus:
            self.draw_bonus_banner(g, t, bonus)
        if all(x is None for x in self.slot) and not bonus:
            g.text("kb16", "A tripulação está a dormir", W // 2, 120, C["text"], 255, "center")
            g.text(ui.SMALL, "escolhe um som em baixo e carrega A", W // 2, 146, C["soft"], 255, "center")
        s, t0 = self.msg
        if s and time.time() - t0 < 2.2 and not bonus:
            ui.toast(g, s, PINK, 150)

    def draw_loading(self, g, t):
        g.text("kb32", "ORIMBOX", W // 2, 170, C["text"], 255, "center")
        if self.load_err:
            g.text("k16", "Sons em falta: " + self.load_err[:50], W // 2, 230, (255, 120, 120), 255, "center")
            return
        g.text("k16", "A acordar a tripulação...", W // 2, 222, C["soft"], 255, "center")
        p = getattr(self, "progress", 0.0)
        g.rect(W // 2 - 120, 252, 240, 8, C["hull"])
        g.rect(W // 2 - 120, 252, int(240 * p), 8, PINK)

    def draw_header(self, g, t):
        g.rect(0, 0, W, ui.HEADER_H, C["deck"], 235)
        g.rect(0, ui.HEADER_H - 2, W, 2, ui.CAT_COL["JOGOS"])
        g.text(ui.SMALL, "JOGOS", 14, 2, ui.CAT_COL["JOGOS"])
        g.text(ui.HEAD, "ORIMBOX", 14, 18, C["text"])
        # loop position: 16 beats, the current one lit
        beat = int(self.pos() / (self.L / 16.0)) if self.t0 is not None else -1
        for i in range(16):
            on = i == beat
            g.rect(192 + i * 11 + (i // 4) * 6, 24 if on else 27, 7, 10 if on else 5,
                   PINK if on else (C["hullhi"] if (self.t0 is not None and i < beat) else C["hull"]))
        found = len(self.found)
        g.text(ui.SMALL, "SEGREDOS %d/%d" % (found, len(self.meta["bonus"])), 404, 16,
               (255, 214, 80) if found else C["muted"])
        x, y, w = W - 116, 9, 106
        ui.box(g, x, y, w, 30, C["hull"])
        if self.app.rec.active() and self.app.rec.src == "ORIMBOX":
            if int(t * 2) % 2 == 0:
                g.rect(x + 8, y + 11, 8, 8, (255, 60, 80))
            g.text(ui.SMALL, self.app.rec.label(), x + 22, y + 5, (255, 90, 100))
        else:
            g.text(ui.HEAD, "100", x + 10, y + 1, C["text"])
            g.text(ui.SMALL, "BPM", x + 14 + g.tw(ui.HEAD, "100"), y + 5, C["muted"])

    def draw_sky(self, g, t, bonus):
        bands = [(16, 8, 44), (22, 10, 58), (30, 12, 70), (40, 14, 80), (52, 18, 88)]
        for i, col in enumerate(bands):
            g.rect(0, 48 + i * 40, W, 41, col)
        tw = [[], [], []]                                       # twinkling stars, in 3 brightness groups
        for x, y, s, ph in self.stars:
            tw[int(2.99 * (0.5 + 0.5 * math.sin(t * 2 + ph * 6)))].append((x, y, s, s))
        for k, lst in enumerate(tw):
            g.rects(lst, (220, 220, 255), 110 + 70 * k)
        g.art("ringed", 452, 58, 2, 230)
        # the stage
        g.rect(0, 300, W, 52, (34, 18, 64))
        g.rect(0, 300, W, 2, (90, 60, 150))
        for i in range(9):
            x = W // 2 + (i - 4) * 90
            g.rect(x - 1, 302, 2, 50, (48, 26, 86))
        if bonus:
            self.draw_bonus_fx(g, t, bonus)

    def draw_stage(self, g, t, bonus):
        beatk = (self.pos() / (self.L / 16.0)) % 1.0 if self.t0 is not None else 0.0
        for i in range(SLOTS):
            sid = self.slot[i]
            cx = SLOT_X[i]
            snd = self.sound(sid) if sid else None
            cat = snd["cat"] if snd else None
            on = sid is not None and self.gains()[i] > 0
            e = self.env(sid) if (on and self.t0 is not None) else 0.0
            if bonus and on:
                e = max(e, 0.6 + 0.4 * (1 - beatk))
            # spotlight on the floor
            if sid:
                col = CAT_COL[cat]
                g.rect(cx - 34, FEET_Y - 4, 68, 8, col, 80 + int(120 * e) if on else 40)
                if self.solo == i:                                  # solo: a light from above
                    for k in range(12):
                        g.rect(cx - 8 - k * 3, 52 + k * 24, 16 + k * 6, 24, (255, 250, 210), 34)
            # the alien
            tex = self.tex[(i, cat)]
            bob = int(-e * 10) if on else int(2 * math.sin(t * 1.5 + i))
            squash = 1.0 + (0.06 * e if on else 0.0)
            tw, th = tex[1], int(tex[2] / squash)
            x0, y0 = cx - tw // 2, FEET_Y - th + bob
            g.blit(tex[0], None, (x0, y0, tw, th), 255 if (on or sid is None) else 150)
            d = DESIGNS[i]
            # eyes
            for ex, ey in d["eyes"]:
                px, py = x0 + ex * S, y0 + int(ey * S / squash)
                big = d.get("big")
                ew = 4 * S if big else 3 * S
                if sid is None or (self.blink[i] < 0):            # asleep / blinking: closed
                    g.rect(px - S // 2, py + ew // 2, ew, S // 2 + 1, (12, 8, 30))
                    continue
                if cat == "fx" and on:
                    g.rect(px, py + S, ew - S, S, C["cyan"], 200 + int(55 * e))
                    continue
                g.rect(px - S // 2, py, ew, ew, (250, 250, 255))
                look = int(round(math.sin(t * 0.7 + i * 1.3)))
                ps = S * 2 if big else S + 2
                g.rect(px + ew // 2 - ps // 2 - S // 2 + look * 2, py + ew // 2 - ps // 2, ps, ps, (16, 10, 40))
            # mouth
            my = y0 + int(d["mouth"] * S / squash)
            mh = int(S // 2 + e * 3.2 * S) if on else S // 2
            mw = 4 * S if on else 3 * S
            g.rect(cx - mw // 2, my, mw, mh, (40, 6, 30))
            if on and mh > S:
                g.rect(cx - mw // 2 + S // 2, my + mh - S, mw - S, S // 2 + 1, (230, 80, 120))
            if sid and not on:                                     # muted: a little zZ
                g.text(ui.SMALL, "zZ", cx + 22, y0 - 4 + int(3 * math.sin(t * 2)), C["muted"])
            # the sound's badge above the head
            if sid:
                col = CAT_COL[cat]
                by = y0 - 34
                ui.box(g, cx - 13, by, 26, 26, col if on else C["hull"])
                ic = self.icons.get(sid)
                if ic:
                    sdl2.SDL_SetTextureColorMod(ic[0], *((12, 8, 30) if on else (130, 125, 180)))
                    g.blit(ic[0], None, (cx - 9, by + 4, ic[1], ic[2]))
            # the cursor on stage
            if self.focus == "stage" and i == self.sel:               # the chosen alien: corners around it
                bx, by, bw, bh = cx - 40, y0 - 40, 80, FEET_Y - y0 + 46
                c = C["text"]
                g.rects([(bx, by, 12, 3), (bx, by, 3, 12), (bx + bw - 12, by, 12, 3), (bx + bw - 3, by, 3, 12),
                         (bx, by + bh - 3, 12, 3), (bx, by + bh - 12, 3, 12), (bx + bw - 12, by + bh - 3, 12, 3),
                         (bx + bw - 3, by + bh - 12, 3, 12)], c, 200 + int(55 * math.sin(t * 6)))
            elif self.focus == "bar" and i == self.free_slot() and self.meta:
                g.rect(cx - 6, FEET_Y + 12, 12, 3, C["dim"])

    def draw_bar(self, g, t):
        snd = self.meta["sounds"]
        cur = snd[self.icon]
        # info line
        y = 354
        if self.focus == "bar":
            col = CAT_COL[cur["cat"]]
            x = g.text("kb16", CAT_NAME[cur["cat"]], 14, y, col)
            x = g.text("kb16", " · " + cur["name"], x, y, C["text"])
            if cur["id"] in self.slot:
                hint = "já canta no alien %d · B tira" % (self.slot.index(cur["id"]) + 1)
            else:
                hint = "A: dar ao alien %d" % (self.free_slot() + 1)
            g.text(ui.SMALL, hint, W - 14, y, C["soft"], 255, "right")
        else:
            sid = self.slot[self.sel]
            x = g.text("kb16", "ALIEN %d" % (self.sel + 1), 14, y, C["text"])
            if sid:
                s = self.sound(sid)
                g.text("kb16", " · " + s["name"], x, y, CAT_COL[s["cat"]])
                g.text(ui.SMALL, "A silenciar · X solo · B tirar", W - 14, y, C["soft"], 255, "right")
            else:
                g.text(ui.SMALL, "a dormir · baixo: escolhe um som", W - 14, y, C["soft"], 255, "right")
        # the 20 sounds in 4 groups
        x0 = (W - (20 * 28 + 3 * 12)) // 2
        for gi, (cat, name, col) in enumerate(CATS):
            gx = x0 + gi * (5 * 28 + 12)
            g.text(ui.SMALL, name, gx + (5 * 28 - 4) // 2, 374, col, 255, "center")
            for k in range(5):
                idx = gi * 5 + k
                s = snd[idx]
                x = gx + k * 28
                used = s["id"] in self.slot
                sel = self.focus == "bar" and idx == self.icon
                if sel:
                    ui.box(g, x - 3, 393, 32, 32, C["text"])
                ui.box(g, x, 396, 26, 26, col if not used else mix(col, (20, 14, 50), 0.6))
                ic = self.icons.get(s["id"])
                if ic:
                    sdl2.SDL_SetTextureColorMod(ic[0], *((14, 10, 36) if not used else (200, 196, 240)))
                    g.blit(ic[0], None, (x + 4, 400, ic[1], ic[2]))
                if used:
                    n = self.slot.index(s["id"]) + 1
                    g.text(ui.SMALL, "%d" % n, x + 22, 404, C["text"], 255, "right")

    # ------------------------------------------------------------ bonus show
    def draw_bonus_fx(self, g, t, bonus):
        bid = bonus[0]
        k = (self.app.mixer.clock - bonus[1]) / float(bonus[2] - bonus[1])
        beat = (self.pos() / (self.L / 16.0)) % 1.0
        if bid == "coro":                                    # an aurora
            for i in range(6):
                y = 70 + i * 26 + int(10 * math.sin(t * 1.3 + i))
                col = [(80, 255, 180), (100, 200, 255), (200, 120, 255)][i % 3]
                g.rects([(xx, y + int(14 * math.sin(xx * 0.02 + t * 2 + i)), 16, 10) for xx in range(0, W, 16)],
                        col, 50)
        elif bid == "batalha":                               # strobes on the beat
            if beat < 0.15:
                g.rect(0, 48, W, 252, (255, 255, 255), 50)
            g.rects([(int((i * 73 + t * 300) % W), 48, 6, 252) for i in range(10)], (255, 138, 42), 60)
        elif bid == "selva":                                 # leaves falling
            for c, col in enumerate(((90, 220, 110), (60, 170, 80), (160, 230, 90))):
                g.rects([((i * 97 + int(t * 30 * (1 + i % 3))) % W, 48 + (i * 53 + int(t * 60)) % 250, 6, 4)
                         for i in range(c, 30, 3)], col, 200)
        elif bid == "robos":                                 # a grid and glitches
            g.rects([(x, 48, 1, 252) for x in range(0, W, 32)] + [(0, y, W, 1) for y in range(56, 300, 24)],
                    (60, 242, 255), 60)
            if int(t * 8) % 3 == 0:
                g.rect(0, 48 + int(t * 997) % 240, W, 6, (255, 60, 200), 90)
        elif bid == "nave":                                  # the Mothership crosses the sky, beaming
            sx = int(-200 + k * (W + 400))
            draw_ship(g, sx - 120, 74, 3, t, 0.8)

    def draw_bonus_banner(self, g, t, bonus):
        name = self.sound(bonus[0])["name"]
        el = (self.app.mixer.clock - bonus[1]) / float(SR)
        if el < 3.0:
            a = int(255 * min(1.0, (3.0 - el) / 0.5))
            g.text("kb16", "SEGREDO DESCOBERTO!", W // 2, 108, (255, 214, 80), a, "center")
            g.text("kb32", name, W // 2 + 2, 130, (0, 0, 0), a, "center")
            g.text("kb32", name, W // 2, 128, C["text"], a, "center")
