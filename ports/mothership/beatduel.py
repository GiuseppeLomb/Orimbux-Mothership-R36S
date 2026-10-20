# BEAT DUEL - rhythm duel for 2 players on one console (d-pad vs face buttons), vs CPU, or practice.
# Songs: 5 built-in (charts generated from the notes we composed), sessions recorded in Loop Reactor /
# Xeno Synth (chart = what you played), Abductor recordings and music/*.wav (chart made in the editor).
import glob
import json
import math
import os
import random
import time

import sdl2

import engine
from engine import C, W, H, SR, BUF, StreamVoice

BD = os.path.join(engine.ASSETS, "bd")
REC_DIR = os.path.join(engine.APP, "recordings")
MUSIC_DIR = os.path.join(engine.APP, "music")
SAVE = os.path.join(engine.APP, "bd_save.json")

P1_KEYS = {"left": 0, "down": 1, "up": 2, "right": 3}
P2_KEYS = {"y": 0, "b": 1, "x": 2, "a": 3}
# FACE TO FACE: the console lies flat between the two players, P1 at the d-pad end, P2 at the buttons end.
# Lanes are left..right as each player sees them, so the buttons are mapped from where they sit:
#   P1 faces the console's right edge: d-pad up points to P1's left, left points to P1, right away from P1.
#   P2 faces the console's left edge: B is on P2's left, A towards P2, Y away from P2, X on P2's right.
P1_FACE = {"up": 0, "left": 1, "right": 2, "down": 3}
P2_FACE = {"b": 0, "a": 1, "y": 2, "x": 3}
FACE = "FRENTE A FRENTE"
VW, VH = 480, 320                         # each player's view (drawn upright, then turned 90 degrees)
LANE_COL = [(255, 90, 170), (60, 242, 255), (124, 255, 138), (255, 180, 60)]
P1_GLYPH = ["left", "down", "up", "right"]
P2_GLYPH = ["Y", "B", "X", "A"]
DIFFS = ["easy", "normal", "hard"]
DIFF_NAME = {"easy": "FÁCIL", "normal": "NORMAL", "hard": "DIFÍCIL"}
SRC_NAME = {"INCLUIDA": "DA NAVE", "SESSAO": "A TUA SESSÃO", "ABDUCTOR": "GRAVAÇÃO", "MUSICA": "A TUA MÚSICA"}
MODES = ["DUELO", FACE, "VS CPU", "TREINO"]
WIN = {"perfect": 0.05, "great": 0.09, "good": 0.13}
MISS = 0.16
SCORE = {"perfect": 300, "great": 200, "good": 100}
ATTACKS = ["SPEED", "HIDDEN", "MIRROR"]
HIT_Y = 404


def find_songs():
    out = []
    for p in sorted(glob.glob(os.path.join(BD, "*.json"))):
        try:
            m = json.load(open(p))
            m.update({"wav": os.path.join(BD, m["file"]), "src": "INCLUIDA", "chart_path": None})
            out.append(m)
        except Exception:
            pass
    for p in sorted(glob.glob(os.path.join(REC_DIR, "session_*.json")), reverse=True):
        try:
            m = json.load(open(p))
            m.update({"wav": os.path.join(REC_DIR, m["file"]), "src": "SESSAO", "chart_path": p})
            if not any(m.get("charts", {}).values()):
                m["charts"] = {}            # e.g. a DJ mix: no notes yet -> editor (Y)
            if os.path.exists(m["wav"]):
                out.append(m)
        except Exception:
            pass
    entries = [(w, "ABDUCTOR", w) for w in sorted(glob.glob(os.path.join(REC_DIR, "rec_*.wav")))]
    for root, _, files in os.walk(MUSIC_DIR):
        if ".cache" in root:
            continue
        for f in sorted(files):
            src = os.path.join(root, f)
            low = f.lower()
            if low.endswith(".wav"):
                entries.append((src, "MUSICA", src))
            elif low.endswith((".mp3", ".ogg", ".flac", ".m4a")):
                entries.append((src, "MUSICA", os.path.join(MUSIC_DIR, ".cache", f + ".wav")))
    for src, tag, wav in entries:
        cp = src + ".chart.json"
        m = {"id": os.path.basename(src), "title": os.path.splitext(os.path.basename(src))[0][:34].upper(),
             "artist": "TU" if tag == "ABDUCTOR" else "", "bpm": 120, "wav": wav, "src": tag, "chart_path": cp,
             "charts": {}, "missing": not os.path.exists(wav)}
        if os.path.exists(cp):
            try:
                c = json.load(open(cp))
                m["charts"], m["bpm"] = c.get("charts", {}), c.get("bpm", 120)
            except Exception:
                pass
        out.append(m)
    return out


class Clock(object):
    """smooth mixer clock: the mixer advances in 1024-frame chunks, we interpolate with wall time"""

    def __init__(self, mixer):
        self.m = mixer
        self.last_c = -1
        self.last_w = 0.0
        self.chunk = BUF      # the device may ask for bigger chunks than we requested: learn it

    def frames(self):
        c = self.m.clock
        now = time.time()
        if c != self.last_c:
            if self.last_c >= 0 and 0 < c - self.last_c <= 8 * BUF:
                self.chunk = max(BUF, c - self.last_c)
            self.last_c, self.last_w = c, now
        return c + min(self.chunk, (now - self.last_w) * SR)


class Player(object):
    def __init__(self, name, chart, keys, cpu=None):
        self.name, self.keys, self.cpu = name, keys, cpu
        # [t, lane, state (0 pending 1 hit 2 missed), hold seconds (0 = tap), hold state (0, 1 holding, 2 ok, 3 dropped)]
        self.notes = [[n[0], n[1], 0, (n[2] if len(n) > 2 else 0.0), 0] for n in chart]
        self.holding = {}                                     # lane -> note being held
        self.next = 0
        self.score = self.combo = self.maxcombo = 0
        self.count = {"perfect": 0, "great": 0, "good": 0, "miss": 0}
        self.holds_ok = self.holds_total = 0
        self.meter = 0.0
        self.fx = {}
        self.judge = ("", 0.0, (255, 255, 255))
        self.flash = [0.0] * 4
        self.cpu_plan = {}

    def acc(self):
        n = sum(self.count.values())
        if not n:
            return 100.0
        return 100.0 * (self.count["perfect"] + self.count["great"] * 0.7 + self.count["good"] * 0.4) / n


class Match(object):
    def __init__(self, bd, song, diff, mode):
        self.bd, self.app, self.song, self.diff, self.mode = bd, bd.app, song, diff, mode
        chart = song["charts"].get(diff) or song["charts"].get("normal") or []
        self.chart = chart
        lvl = {"easy": (0.75, 0.06), "normal": (0.88, 0.045), "hard": (0.95, 0.032)}[diff]
        if mode == "DUELO":
            self.players = [Player("P1", chart, P1_KEYS), Player("P2", chart, P2_KEYS)]
        elif mode == FACE:
            self.players = [Player("P1", chart, P1_FACE), Player("P2", chart, P2_FACE)]
        elif mode == "VS CPU":
            both = dict(P1_KEYS)
            both.update(P2_KEYS)
            self.players = [Player("TU", chart, both), Player("CPU", chart, {}, lvl)]
        else:
            both = dict(P1_KEYS)
            both.update(P2_KEYS)
            self.players = [Player("TU", chart, both)]
        self.speed = {"easy": 260, "normal": 320, "hard": 380}[diff]
        if mode == FACE:
            self.speed *= 0.72                    # the view is only 320 px deep: keep ~1.2 s of notes on screen
        self.views = None
        self.offset = float(self.app.cfg.get("bd_offset", 0.0))
        self.clock = Clock(self.app.mixer)
        m = self.app.mixer
        # skip long intros: start the file 4 s before the first note, but keep >= 2.5 s before it to read the lanes
        self.first = chart[0][0] if chart else 0.0
        skip = max(0.0, self.first - 4.0)
        lead = max(0.0, 2.5 - (self.first - skip))
        self.stream = None
        self.length = 10.0
        try:
            self.stream = StreamVoice(song["wav"], "bd")
            self.length = self.stream.frames / float(SR)
            self.stream.seek(skip)
        except Exception:
            self.stream = None
        with m.lock:
            play_at = m.clock + int((0.2 + lead) * SR)
            self.t0_clock = play_at - int(skip * SR)      # mixer clock at which file time 0 "would" play
            if self.stream:
                self.stream.start = play_at
                m.streams.append(self.stream)
        self.end_t = max([n[0] for n in chart] + [0]) + 2.0
        if self.stream:
            self.end_t = min(self.end_t, self.length + 0.5)
        self.done = False
        self.banner = ("", 0.0)
        self.beat = 60.0 / float(song.get("bpm") or 120)

    def now(self):
        return (self.clock.frames() - self.t0_clock) / float(SR) - self.offset

    def stop(self):
        if self.stream:
            self.stream.fade(0.0, 0.3)

    def free_views(self):
        for v in self.views or []:
            if v:
                sdl2.SDL_DestroyTexture(v)
        self.views = None

    def make_views(self):
        ren = self.app.ren
        if self.views is None:
            self.views = []
            if sdl2.SDL_RenderTargetSupported(ren):
                for _ in range(2):
                    tex = sdl2.SDL_CreateTexture(ren, sdl2.SDL_PIXELFORMAT_ARGB8888, sdl2.SDL_TEXTUREACCESS_TARGET,
                                                 VW, VH)
                    self.views.append(tex or None)
        return self.views and all(self.views)

    def show_views(self, g, painter):
        """paint each player's view upright into its texture, then turn it to face its player:
        P1 (left end) sees 'up' towards the centre, P2 (right end) too"""
        ren = self.app.ren
        for k, p in enumerate(self.players):
            sdl2.SDL_SetRenderTarget(ren, self.views[k])
            sdl2.SDL_SetRenderDrawColor(ren, 8, 4, 20, 255)
            sdl2.SDL_RenderClear(ren)
            painter(g, p, k)
        sdl2.SDL_SetRenderTarget(ren, None)
        g.clear((6, 2, 16))
        for k, (cx, ang) in enumerate(((W // 4, 90.0), (3 * W // 4, 270.0))):
            d = sdl2.SDL_Rect(cx - VW // 2, H // 2 - VH // 2, VW, VH)
            sdl2.SDL_RenderCopyEx(ren, self.views[k], None, d, ang, None, sdl2.SDL_FLIP_NONE)
        g.rect(W // 2 - 2, 0, 4, H, (60, 40, 110))

    # ---------------------------------------------------------------- judging
    def judge_press(self, p, lane):
        t = self.now()
        best = None
        for i in range(p.next, min(len(p.notes), p.next + 24)):
            n = p.notes[i]
            if n[2] or n[1] != lane:
                continue
            d = n[0] - t
            if d > MISS:
                break
            if abs(d) <= MISS:
                best = n
                break
        p.flash[lane] = time.time()
        if best is None:
            return
        err = abs(best[0] - t)
        grade = "perfect" if err <= WIN["perfect"] else ("great" if err <= WIN["great"] else
                                                         ("good" if err <= WIN["good"] else None))
        best[2] = 1 if grade else 2
        self.score(p, grade or "miss")
        if grade and best[3] > 0:
            best[4] = 1
            p.holding[lane] = best

    def end_hold(self, p, lane, ok):
        n = p.holding.pop(lane, None)
        if n is None:
            return
        p.holds_total += 1
        if ok:
            n[4] = 2
            p.holds_ok += 1
            p.score += int(150 * n[3]) + min(p.combo, 50) * 2
            p.judge = ("SEGURO!", time.time(), (255, 236, 140))
        else:
            n[4] = 3
            p.combo = 0
            p.judge = ("SOLTASTE", time.time(), (255, 120, 90))

    def release(self, b):
        t = self.now()
        for p in self.players:
            if b in p.keys and not p.cpu:
                lane = p.keys[b]
                n = p.holding.get(lane)
                if n is not None:
                    self.end_hold(p, lane, t >= n[0] + n[3] - 0.15)

    def score(self, p, grade):
        p.count[grade] += 1
        if grade == "miss":
            p.combo = 0
            p.judge = ("FALHOU", time.time(), (255, 80, 90))
            return
        p.combo += 1
        p.maxcombo = max(p.maxcombo, p.combo)
        p.score += SCORE[grade] + min(p.combo, 50) * 4
        p.judge = ({"perfect": "PERFEITO", "great": "ÓTIMO", "good": "BOM"}[grade], time.time(),
                   {"perfect": (255, 236, 140), "great": (60, 242, 255), "good": (124, 255, 138)}[grade])
        if len(self.players) == 2:
            p.meter += {"perfect": 5, "great": 3, "good": 1}[grade]
            if p.meter >= 100:
                p.meter = 0
                other = self.players[1] if p is self.players[0] else self.players[0]
                atk = random.choice(ATTACKS)
                other.fx[atk] = self.now() + 6.0
                self.banner = ("%s ATACA: %s!" % (p.name, atk), time.time())
                self.bd.snd("alarm", 0.5)

    def update(self):
        t = self.now()
        for p in self.players:
            for lane, n in list(p.holding.items()):          # held to the end = success
                if t >= n[0] + n[3]:
                    self.end_hold(p, lane, True)
            while p.next < len(p.notes) and p.notes[p.next][2]:
                p.next += 1
            for i in range(p.next, min(len(p.notes), p.next + 24)):
                n = p.notes[i]
                if n[0] - t > 0.3:
                    break
                if n[2]:
                    continue
                if p.cpu:
                    hit_prob, sd = p.cpu
                    plan = p.cpu_plan.get(i)
                    if plan is None:
                        plan = p.cpu_plan[i] = (random.random() < hit_prob, random.gauss(0, sd))
                    if plan[0] and t >= n[0] + plan[1]:
                        err = abs(plan[1])
                        grade = "perfect" if err <= WIN["perfect"] else ("great" if err <= WIN["great"] else "good")
                        n[2] = 1
                        p.flash[n[1]] = time.time()
                        self.score(p, grade)
                        if n[3] > 0:
                            n[4] = 1
                            p.holding[n[1]] = n
                        continue
                if t - n[0] > MISS:
                    n[2] = 2
                    self.score(p, "miss")
        if t > self.end_t or (self.stream and self.stream.done and t > 1):
            self.done = True

    def press(self, b):
        for p in self.players:
            if b in p.keys:
                self.judge_press(p, p.keys[b])

    # ---------------------------------------------------------------- drawing
    def draw_field(self, g, p, x0, w, glyphs, t):
        lane_w = w // 4
        g.rect(x0, 50, w, H - 60, (10, 6, 26), 230)
        for i in range(1, 4):
            g.rect(x0 + i * lane_w, 50, 1, H - 60, (40, 30, 80))
        beat_ph = (t / self.beat) % 1.0 if t > 0 else 1.0
        pulse = int(60 * (1 - beat_ph) ** 2)
        mirror = p.fx.get("MIRROR", -99) > t
        hidden = p.fx.get("HIDDEN", -99) > t
        speed = self.speed * (1.5 if p.fx.get("SPEED", -99) > t else 1.0)
        # receptors
        for lane in range(4):
            vis = 3 - lane if mirror else lane
            cx = x0 + vis * lane_w + lane_w // 2
            col = LANE_COL[lane]
            lit = time.time() - p.flash[lane] < 0.1
            g.rect(cx - 22, HIT_Y - 18, 44, 36, col if lit else (30, 24, 60), 255 if lit else 160 + pulse)
            g.frame(cx - 22, HIT_Y - 18, 44, 36, col, 2)
            self.glyph(g, glyphs[lane], cx, HIT_Y, (10, 6, 26) if lit else col)
        # notes being held: the body shrinks into the receptor
        for lane, n in p.holding.items():
            vis = 3 - lane if mirror else lane
            cx = x0 + vis * lane_w + lane_w // 2
            ytail = max(50, HIT_Y - (n[0] + n[3] - t) * speed)
            if ytail < HIT_Y:
                g.rect(cx - 9, ytail, 18, HIT_Y - ytail, LANE_COL[lane], 235)
                g.rect(cx - 12, ytail - 3, 24, 6, (255, 255, 255))
        # notes
        for i in range(p.next, min(len(p.notes), p.next + 60)):
            n = p.notes[i]
            y = HIT_Y - (n[0] - t) * speed
            if y < 40:
                break
            if n[2] or y > H + 20:
                continue
            if hidden and y > HIT_Y - 150:
                continue
            vis = 3 - n[1] if mirror else n[1]
            cx = x0 + vis * lane_w + lane_w // 2
            col = LANE_COL[n[1]]
            if n[3] > 0:
                ytail = max(50, y - n[3] * speed)
                g.rect(cx - 9, ytail, 18, y - ytail, col, 150)
                g.rect(cx - 12, ytail - 3, 24, 6, col)
            g.rect(cx - 20, y - 14, 40, 28, col)
            g.rect(cx - 20, y - 14, 40, 4, (255, 255, 255))
            self.glyph(g, glyphs[n[1]], cx, y, (10, 6, 26))
        # hud
        g.text("p8", p.name, x0 + 6, 56, C["muted"])
        g.text("p16", "%d" % p.score, x0 + w - 6, 54, C["text"], 255, "right")
        if p.combo >= 4:
            g.text("p16", "%d COMBO" % p.combo, x0 + w // 2, 200, C["violet"], 200, "center")
        txt, t0, col = p.judge
        el = time.time() - t0
        if txt and el < 0.5:
            g.text("p16", txt, x0 + w // 2, HIT_Y - 70 - el * 30, col, int(255 * (1 - el / 0.5)), "center")
        if len(self.players) == 2:
            g.rect(x0 + 6, 76, w - 12, 6, (30, 20, 50))
            g.rect(x0 + 6, 76, (w - 12) * p.meter / 100.0, 6, (255, 60, 200))
            active = [k for k in ATTACKS if p.fx.get(k, -99) > t]
            if active:
                g.text("p8", " ".join(active), x0 + w // 2, 92, (255, 60, 200), 255, "center")
        if p.cpu:
            g.text("v20", "CPU", x0 + w // 2, H - 34, C["dim"], 255, "center")

    # ---------------------------------------------------------------- face to face: one player's upright view
    def draw_view(self, g, p, k, t, tg):
        col_me = LANE_COL[1] if k == 0 else LANE_COL[0]
        stars = [((i * 97 + k * 31) % VW, (i * 53 + int(tg * (20 + i % 3 * 15))) % VH, 2, 2) for i in range(26)]
        g.rects(stars, (50, 40, 96))
        lane_w, fw = 72, 288
        x0 = (VW - fw) // 2
        hit = VH - 44
        g.rect(x0, 0, fw, VH, (12, 8, 30), 235)
        for i in range(1, 4):
            g.rect(x0 + i * lane_w, 0, 1, VH, (40, 30, 80))
        beat_ph = (t / self.beat) % 1.0 if t > 0 else 1.0
        pulse = int(60 * (1 - beat_ph) ** 2)
        mirror = p.fx.get("MIRROR", -99) > t
        hidden = p.fx.get("HIDDEN", -99) > t
        speed = self.speed * (1.5 if p.fx.get("SPEED", -99) > t else 1.0)
        glyphs = ["left", "down", "up", "right"]
        for lane in range(4):
            vis = 3 - lane if mirror else lane
            cx = x0 + vis * lane_w + lane_w // 2
            col = LANE_COL[lane]
            lit = time.time() - p.flash[lane] < 0.1
            g.rect(cx - 24, hit - 18, 48, 36, col if lit else (30, 24, 60), 255 if lit else 160 + pulse)
            g.frame(cx - 24, hit - 18, 48, 36, col, 2)
            self.glyph(g, glyphs[lane], cx, hit, (10, 6, 26) if lit else col)
            if k == 1 and t < self.first:              # P2: which button is which lane
                g.text("kb16", "BAYX"[lane], cx, hit + 20, col, 255, "center")
        for lane, n in p.holding.items():
            vis = 3 - lane if mirror else lane
            cx = x0 + vis * lane_w + lane_w // 2
            ytail = max(0, hit - (n[0] + n[3] - t) * speed)
            if ytail < hit:
                g.rect(cx - 9, ytail, 18, hit - ytail, LANE_COL[lane], 235)
                g.rect(cx - 12, ytail - 3, 24, 6, (255, 255, 255))
        for i in range(p.next, min(len(p.notes), p.next + 60)):
            n = p.notes[i]
            y = hit - (n[0] - t) * speed
            if y < -20:
                break
            if n[2] or y > VH + 20:
                continue
            if hidden and y > hit - 110:
                continue
            vis = 3 - n[1] if mirror else n[1]
            cx = x0 + vis * lane_w + lane_w // 2
            col = LANE_COL[n[1]]
            if n[3] > 0:
                ytail = max(0, y - n[3] * speed)
                g.rect(cx - 9, ytail, 18, y - ytail, col, 150)
                g.rect(cx - 12, ytail - 3, 24, 6, col)
            g.rect(cx - 21, y - 14, 42, 28, col)
            g.rect(cx - 21, y - 14, 42, 4, (255, 255, 255))
            self.glyph(g, glyphs[n[1]], cx, y, (10, 6, 26))
        # side panels: me (left), the duel (right)
        g.text("kb32", p.name, 14, 8, col_me)
        g.text("kb24", "%d" % p.score, 14, 56, C["text"])
        if p.combo >= 4:
            g.text("k16", "COMBO", 14, 96, C["violet"])
            g.text("kb24", "%d" % p.combo, 14, 114, C["violet"])
        other = self.players[1 - k]
        g.text("k16", "RIVAL", VW - 14, 8, C["muted"], 255, "right")
        g.text("kb16", "%d" % other.score, VW - 14, 28, C["soft"], 255, "right")
        g.text("k16", "ATAQUE", VW - 14, 60, (255, 60, 200), 255, "right")
        g.rect(VW - 14 - 72, 82, 72, 8, (30, 20, 50))
        g.rect(VW - 14 - 72, 82, 72 * p.meter / 100.0, 8, (255, 60, 200))
        active = [a for a in ATTACKS if p.fx.get(a, -99) > t]
        for j, a in enumerate(active):
            g.text("kb16", a, VW - 14, 100 + j * 20, (255, 60, 200), 255, "right")
        prog = max(0.0, min(1.0, t / max(1.0, self.end_t)))
        g.rect(0, 0, VW, 3, (40, 30, 70))
        g.rect(0, 0, VW * prog, 3, C["violet"])
        txt, t0, col = p.judge
        el = time.time() - t0
        if txt and el < 0.5:
            g.text("kb24", txt, VW // 2, hit - 76 - el * 30, col, int(255 * (1 - el / 0.5)), "center")
        left = self.first - t
        if left > 3.0 and t < self.first:
            g.text("kb32", "PRONTOS?", VW // 2, 110, C["text"], int(180 + 75 * math.sin(tg * 6)), "center")
            g.text("k16", "notas a descer para ti: carrega quando chegam à linha", VW // 2, 156, C["soft"], 255,
                   "center")
        elif left > 0:
            g.text("kb48", "%d" % int(math.ceil(left)), VW // 2, 100, C["text"], 255, "center")
        s, bt = self.banner
        if s and time.time() - bt < 1.6:
            g.text("kb24", s, VW // 2, 60, (255, 60, 200), 255, "center")

    def draw_view_result(self, g, p, k):
        other = self.players[1 - k]
        if p.score > other.score:
            title, col = "GANHASTE!", (255, 236, 140)
        elif p.score < other.score:
            title, col = "PERDESTE", (255, 110, 140)
        else:
            title, col = "EMPATE!", C["cyan"]
        g.text("kb48", title, VW // 2, 18, col, 255, "center")
        g.text("kb32", "%d" % p.score, VW // 2, 92, C["text"], 255, "center")
        rows = [("PERFEITO", p.count["perfect"]), ("ÓTIMO", p.count["great"]), ("FALHOU", p.count["miss"]),
                ("COMBO MAX", p.maxcombo), ("PRECISÃO", "%d%%" % p.acc())]
        for j, (a, b) in enumerate(rows):
            g.text("k24", a, VW // 2 - 10, 150 + j * 28, C["muted"], 255, "right")
            g.text("k24", "%s" % b, VW // 2 + 10, 150 + j * 28, C["text"])
        g.text("k16", "rival: %d" % other.score, VW // 2, VH - 22, C["soft"], 255, "center")

    def glyph(self, g, gl, cx, cy, col):
        if gl in ("left", "right", "up", "down"):
            g.tri(cx - 7, cy - 7, 7, gl, col)
        else:
            g.text("p16", gl, cx, cy - 8, col, 255, "center")

    def draw(self, g, tg):
        t = self.now()
        if self.mode == FACE and self.make_views():
            self.show_views(g, lambda gg, p, k: self.draw_view(gg, p, k, t, tg))
            return
        g.clear((6, 2, 16))
        stars = [((i * 97) % W, (i * 53 + int(tg * (20 + i % 3 * 15))) % H, 2, 2) for i in range(50)]
        g.rects(stars, (60, 50, 110))
        if len(self.players) == 2:
            self.draw_field(g, self.players[0], 16, 296, P1_GLYPH if self.mode == "DUELO" else P1_GLYPH, t)
            self.draw_field(g, self.players[1], W - 312, 296, P2_GLYPH, t)
        else:
            self.draw_field(g, self.players[0], W // 2 - 160, 320, P1_GLYPH, t)
        g.rect(0, 0, W, 40, (16, 10, 36))
        g.text("p8", self.song["title"][:30], 12, 8, C["text"])
        g.text("v20", "%s  -  %s" % (DIFF_NAME[self.diff], self.mode), 12, 18, C["muted"])
        prog = max(0.0, min(1.0, t / max(1.0, self.end_t)))
        g.rect(W - 212, 16, 200, 8, (40, 30, 70))
        g.rect(W - 212, 16, 200 * prog, 8, C["violet"])
        left = self.first - t
        if left > 3.0 and t < self.first:
            g.text("p16", "PRONTOS?", W // 2, 210, C["text"], int(180 + 75 * math.sin(tg * 6)), "center")
        elif left > 0:
            g.text("p40", "%d" % int(math.ceil(left)), W // 2, 200, C["text"], 255, "center")
        s, t0 = self.banner
        if s and time.time() - t0 < 1.6:
            g.text("p16", s, W // 2, 140, (255, 60, 200), 255, "center")


# ====================================================================== section
class BeatDuel(object):
    name = "BEAT DUEL"

    def __init__(self, app):
        self.app = app
        self.state = "select"
        self.songs = []
        self.sel = 0
        self.diff = 1
        self.mode = 0
        self.match = None
        self.snds = {}
        self.save_d = self.load()
        self.calib = None
        self.edit = None
        self.msg = ("", 0.0)

    def load(self):
        return engine.load_save(SAVE) or {}

    def write(self):
        try:
            engine.write_json(SAVE, self.save_d)
        except Exception:
            pass

    def snd(self, k, gain=0.6):
        d = self.app.snd.get(k) or self.snds.get(k)
        if d:
            self.app.mixer.shot("bd_" + k, d, group="ui", gain=gain)

    def enter(self):
        self.songs = find_songs()
        self.sel = min(self.sel, max(0, len(self.songs) - 1))
        if not self.snds:
            try:
                self.snds["alarm"] = engine.load_wav(os.path.join(engine.ASSETS, "vr", "alarm.wav"))
            except Exception:
                pass
        m = self.app.mixer
        with m.lock:                       # a rhythm game needs silence underneath: stop loops, metronome, streams
            m.kill_group("reactor")
            for s in m.streams:
                s.fade(0.0, 0.4)
            self.metro_was = m.metro
            m.metro = False
        self.state = "select"

    def leave(self):
        self.stop_all()
        self.app.mixer.metro = getattr(self, "metro_was", False)
        self.state = "select"

    def stop_all(self):
        if self.match:
            self.match.stop()
            self.match.free_views()
            self.match = None
        if getattr(self, "result", None):
            self.result.free_views()
        if self.edit and self.edit.get("stream"):
            self.edit["stream"].fade(0.0, 0.3)
        self.edit = None
        self.calib = None

    def on_select(self):
        if self.state == "select":
            self.app.go("bridge")
        else:
            self.stop_all()
            self.state = "select"

    def song(self):
        return self.songs[self.sel] if self.songs else None

    def say(self, s):
        self.msg = (s, time.time())

    # ---------------------------------------------------------------- input
    def on(self, kind, b):
        st = self.state
        if st == "select":
            if not self.songs:
                if kind == "press" and b == "b":
                    self.app.go("bridge")
                return
            if kind in ("press", "repeat") and b in ("up", "down"):
                self.sel = (self.sel + (1 if b == "down" else -1)) % len(self.songs)
                self.app.ui_move()
            elif kind == "press" and b in ("left", "right"):
                self.diff = (self.diff + (1 if b == "right" else -1)) % 3
                self.app.ui_move()
            elif kind == "press" and b == "x":
                self.mode = (self.mode + 1) % len(MODES)
                self.app.ui_move()
            elif kind == "press" and b == "y":
                s = self.song()
                if s.get("missing"):
                    self.say("Abre-a primeiro no WARP FLOOR (converte o ficheiro).")
                elif s["src"] == "INCLUIDA":
                    self.say("As musicas incluidas ja tem pista.")
                else:
                    self.start_editor(s)
            elif kind == "press" and b == "l1":
                self.start_calib()
            elif kind == "press" and b in ("a", "start"):
                s = self.song()
                if s.get("missing"):
                    self.say("Abre-a primeiro no WARP FLOOR (converte o ficheiro).")
                    return
                if not s["charts"]:
                    self.say("Sem pista: Y para criar no editor.")
                    return
                self.app.ui_ok()
                if s.get("src") == "SESSAO" and hasattr(self.app, "mission"):
                    self.app.mission("duel_session")
                self.match = Match(self, s, DIFFS[self.diff], MODES[self.mode])
                self.state = "play"
            elif kind == "press" and b == "b":
                self.app.go("bridge")
            return
        if st == "play":
            if kind == "press":
                if b == "start":
                    self.match.stop()
                    self.match.free_views()
                    self.match = None
                    self.state = "select"
                else:
                    self.match.press(b)
            elif kind == "release":
                self.match.release(b)
            return
        if st == "results":
            if kind == "press" and b in ("a", "b", "start"):
                self.result.free_views()
                self.state = "select"
            return
        if st == "calib":
            if kind == "press" and b in ("a", "b", "x", "y", "left", "right", "up", "down"):
                self.calib["taps"].append(self.calib["clock"].frames())
                self.calib["flash"] = time.time()
            elif kind == "press" and b == "start":
                self.state = "select"
            return
        if st == "editor":
            e = self.edit
            if e["phase"] == "setup":
                if kind in ("press", "repeat") and b in ("left", "right"):
                    e["bpm"] = max(60, min(220, e["bpm"] + (1 if b == "right" else -1)))
                elif kind in ("press", "repeat") and b in ("up", "down"):
                    e["quant"] = (e["quant"] + (1 if b == "up" else -1)) % 4
                elif kind == "press" and b == "a":
                    self.editor_go()
                elif kind == "press" and b == "b":
                    self.stop_all()
                    self.state = "select"
                return
            if kind == "press" and b == "start":
                self.editor_save()
                return
            lane = P1_KEYS.get(b, P2_KEYS.get(b))
            if lane is None:
                return
            t = (e["clock"].frames() - e["start"]) / float(SR) - float(self.app.cfg.get("bd_offset", 0.0))
            if kind == "press":
                e["notes"].append([t, lane])
                e.setdefault("down", {})[lane] = len(e["notes"]) - 1
                e["flash"][lane] = time.time()
            elif kind == "release":
                i = e.setdefault("down", {}).pop(lane, None)
                if i is not None and t - e["notes"][i][0] >= 0.3:       # held = a long note
                    e["notes"][i].append(round(t - e["notes"][i][0], 3))

    # ---------------------------------------------------------------- calibration
    def start_calib(self):
        m = self.app.mixer
        clk = Clock(m)
        period = int(SR * 0.6)
        first = m.clock + SR
        beats = [first + i * period for i in range(10)]
        click = self.app.snd.get("click_hi")
        if click:
            for i, bc in enumerate(beats):
                m.add(engine.Voice("bd_cal%d" % i, "ui", click, None, False, 1.0, bc))
        self.calib = {"clock": clk, "beats": beats, "taps": [], "t0": time.time()}
        self.state = "calib"

    def update_calib(self):
        c = self.calib
        if time.time() - c["t0"] > 7.5:
            diffs = []
            for tap in c["taps"]:
                nearest = min(c["beats"], key=lambda b: abs(b - tap))
                d = (tap - nearest) / float(SR)
                if abs(d) < 0.3:
                    diffs.append(d)
            if len(diffs) >= 4:
                diffs.sort()
                off = diffs[len(diffs) // 2]
                self.app.cfg["bd_offset"] = round(off, 3)
                self.app.save_cfg()
                self.say("Calibrado: %+d ms" % (off * 1000))
            else:
                self.say("Poucos toques - tenta outra vez.")
            self.state = "select"

    # ---------------------------------------------------------------- editor
    def start_editor(self, s):
        self.edit = {"song": s, "phase": "setup", "bpm": int(s.get("bpm") or self.app.mixer.bpm), "quant": 1,
                     "notes": [], "flash": [0.0] * 4}
        self.state = "editor"

    def editor_go(self):
        e = self.edit
        m = self.app.mixer
        try:
            v = StreamVoice(e["song"]["wav"], "bd")
        except Exception:
            self.say("Nao consegui abrir o ficheiro.")
            self.state = "select"
            return
        with m.lock:
            e["start"] = m.clock + int(2 * SR)
            v.start = e["start"]
            m.streams.append(v)
        e["stream"], e["clock"], e["phase"] = v, Clock(m), "rec"

    def editor_save(self):
        e = self.edit
        if e.get("stream"):
            e["stream"].fade(0.0, 0.3)
        raw = sorted(e["notes"])
        notes, seen = [], set()
        if e["quant"] < 3:
            step = 60.0 / e["bpm"] / [1, 2, 4][e["quant"]]
            # the grid's phase is unknown (a recording rarely starts exactly on a beat):
            # take the circular mean of where the taps fall inside one step
            sx = sum(math.cos(2 * math.pi * n[0] / step) for n in raw)
            sy = sum(math.sin(2 * math.pi * n[0] / step) for n in raw)
            ph = (math.atan2(sy, sx) / (2 * math.pi)) * step if raw else 0.0
        for n in raw:
            t, lane = n[0], n[1]
            q = round(round((t - ph) / step) * step + ph, 3) if e["quant"] < 3 else round(t, 3)
            if q >= 0 and (q, lane) not in seen:
                seen.add((q, lane))
                notes.append([q, lane] + ([n[2]] if len(n) > 2 else []))
        easy, last = [], -9.0
        for n in notes:
            if n[0] - last >= 0.35:
                easy.append(n)
                last = n[0]
        s = e["song"]
        data = {"title": s["title"], "bpm": e["bpm"], "charts": {"easy": easy, "normal": notes, "hard": notes}}
        try:
            if s["src"] == "SESSAO":
                full = engine.read_json(s["chart_path"])
                full["charts"] = data["charts"]
                full["bpm"] = e["bpm"]
                engine.write_json(s["chart_path"], full)
            else:
                engine.write_json(s["chart_path"], data)
            self.say("Pista guardada: %d notas" % len(notes))
        except Exception as ex:
            self.say("Erro a guardar: %s" % ex)
        self.edit = None
        self.songs = find_songs()
        self.state = "select"

    # ---------------------------------------------------------------- update / results
    def update(self, dt):
        if self.state == "play" and self.match:
            self.match.update()
            if self.match.done:
                self.finish()
        elif self.state == "calib":
            self.update_calib()
        elif self.state == "editor" and self.edit and self.edit["phase"] == "rec":
            st = self.edit["stream"]
            if st.done:
                self.editor_save()

    def finish(self):
        m = self.match
        m.stop()
        key = "%s|%s" % (m.song["id"], m.diff)
        best = self.save_d.get(key, 0)
        top = max(p.score for p in m.players if not p.cpu)
        if top > best:
            self.save_d[key] = top
            self.write()
        self.result = m
        self.match = None
        self.state = "results"
        self.snd("ui_ok", 0.7)

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        st = self.state
        if st == "play" and self.match:
            self.match.draw(g, t)
            return
        g.clear((6, 2, 16))
        g.rect(0, 0, W, 46, (16, 10, 36))
        g.text("p16", "BEAT", 14, 14, (255, 90, 170))
        g.text("p16", "DUEL", 92, 14, (60, 242, 255))
        if st == "select":
            self.draw_select(g, t)
        elif st == "results":
            self.draw_results(g, t)
        elif st == "calib":
            self.draw_calib(g, t)
        elif st == "editor":
            self.draw_editor(g, t)
        s, t0 = self.msg
        if s and time.time() - t0 < 2.5:
            w = g.tw("v20", s) + 30
            g.rect(W // 2 - w // 2, 54, w, 30, C["panel"], 240)
            g.frame(W // 2 - w // 2, 54, w, 30, C["orange"], 2)
            g.text("v20", s, W // 2, 58, C["text"], 255, "center")

    def draw_select(self, g, t):
        g.text("v20", "MODO (X)", 300, 8, C["muted"])
        g.text("p8", MODES[self.mode], 300, 28, (255, 236, 140))
        g.text("v20", "DIFICULDADE", W - 12, 8, C["muted"], 255, "right")
        g.text("p8", "< %s >" % DIFF_NAME[DIFFS[self.diff]], W - 12, 28, LANE_COL[self.diff + 1], 255, "right")
        if not self.songs:
            g.text("v20", "Sem músicas.", W // 2, 200, C["text"], 255, "center")
            return
        top = max(0, min(self.sel - 4, len(self.songs) - 9))
        for row, i in enumerate(range(top, min(len(self.songs), top + 9))):
            s = self.songs[i]
            y = 60 + row * 40
            sel = i == self.sel
            col = {"INCLUIDA": C["violet"], "SESSAO": (255, 90, 100), "ABDUCTOR": C["cyan"],
                   "MUSICA": C["green"]}[s["src"]]
            if sel:
                g.glow(16, y, 400, 34, col, 0.4 + 0.3 * math.sin(t * 5))
            g.rect(16, y, 400, 34, C["hull"] if sel else (16, 12, 34))
            g.frame(16, y, 400, 34, col if sel else (40, 30, 70), 2)
            g.text("p8", s["title"][:34], 28, y + 7, C["text"] if s["charts"] else C["dim"])
            tag = "  -  ABRE NO WARP FLOOR" if s.get("missing") else ("" if s["charts"] else "  -  SEM PISTA (Y)")
            g.text("v20", SRC_NAME.get(s["src"], s["src"]) + tag, 28, y + 15, col)
            best = self.save_d.get("%s|%s" % (s["id"], DIFFS[self.diff]))
            if best:
                g.text("v20", "%d" % best, 406, y + 8, (255, 236, 140), 255, "right")
        s = self.song()
        x = 432
        g.rect(x, 60, W - x - 12, 352, (16, 12, 34))
        g.frame(x, 60, W - x - 12, 352, C["hullhi"], 2)
        import ui
        pw = W - x - 12 - 24                       # text width inside the panel
        lines = ui.wrap(g, "p8", s["title"], pw) or [""]
        g.text("p8", ui.fit(g, "p8", lines[0], pw), x + 12, 68, C["text"])
        if len(lines) > 1:
            g.text("p8", ui.fit(g, "p8", " ".join(lines[1:]), pw), x + 12, 80, C["text"])
        g.text("v20", s.get("artist", ""), x + 12, 93, C["muted"])
        g.text("v20", "%s BPM" % s.get("bpm", "?"), x + 12, 112, C["cyan"])
        if s.get("duration"):
            g.text("v20", "%d:%02d" % (s["duration"] // 60, s["duration"] % 60), x + 12, 132, C["cyan"])
        for k, d in enumerate(DIFFS):
            n = len(s["charts"].get(d, []))
            g.text("v20", "%s %d notas" % (DIFF_NAME[d], n) if n else "%s -" % DIFF_NAME[d], x + 12, 162 + k * 20,
                   LANE_COL[k + 1] if n else C["dim"])
        mode_txt = {"DUELO": "2 jogadores: um usa as setas, o outro Y B X A. Combos lançam ataques!",
                    FACE: "Consola deitada na mesa entre os dois: cada um vê a sua metade direita. P1 do lado da cruz, "
                          "P2 do lado dos botões.",
                    "VS CPU": "Tu contra a consola. Joga com as setas ou com os botões.",
                    "TREINO": "Sozinho, sem pressão."}.get(MODES[self.mode], "")
        ui.para(g, ui.SMALL, mode_txt, x + 12, 236, pw, C["soft"], 18)
        g.text(ui.SMALL, "atraso do som: %+d ms" % (float(self.app.cfg.get("bd_offset", 0)) * 1000), x + 12, 330,
               C["dim"])
        ui.footer(g, [("A", "jogar", 0), ("esq/dir", "dificuldade", 0), ("X", "modo", 0), ("L1", "acertar o som", 0)],
                  hints=True)

    def draw_results(self, g, t):
        m = self.result
        ps = m.players
        if m.mode == FACE and m.make_views():
            m.show_views(g, lambda gg, p, k: m.draw_view_result(gg, p, k))
            return
        if len(ps) == 2:
            win = ps[0] if ps[0].score > ps[1].score else (ps[1] if ps[1].score > ps[0].score else None)
            title = "EMPATE!" if win is None else "%s GANHA!" % win.name
        else:
            title = "FIM!"
        g.text("p40", title, W // 2, 70, (255, 236, 140), 255, "center")
        for i, p in enumerate(ps):
            x = W // 2 if len(ps) == 1 else (W // 4 if i == 0 else 3 * W // 4)
            g.text("p16", p.name, x, 140, LANE_COL[1 if i == 0 else 0], 255, "center")
            g.text("p24", "%d" % p.score, x, 166, C["text"], 255, "center")
            rows = [("PERFEITO", p.count["perfect"]), ("ÓTIMO", p.count["great"]), ("BOM", p.count["good"]),
                    ("FALHOU", p.count["miss"]), ("COMBO MAX", p.maxcombo), ("PRECISÃO", "%d%%" % p.acc())]
            if p.holds_total:
                rows.insert(4, ("LONGAS", "%d/%d" % (p.holds_ok, p.holds_total)))
            for k, (a, b) in enumerate(rows):
                g.text("v20", a, x - 10, 214 + k * 24, C["muted"], 255, "right")
                g.text("v20", "%s" % b, x + 10, 214 + k * 24, C["text"])
        g.text("p8", "A continuar", W // 2, H - 40, C["cyan"], 255, "center")

    def draw_calib(self, g, t):
        # audio only on purpose: a moving marker would make you tap with the eyes, not the ears
        c = self.calib
        g.text("p16", "ACERTAR O ATRASO DO SOM", W // 2, 90, C["text"], 255, "center")
        g.text("v20", "Fecha os olhos e carrega em A sempre que OUVES um clique.", W // 2, 130, C["soft"], 255,
               "center")
        g.text("v20", "Usa os auscultadores/coluna com que vais jogar.", W // 2, 152, C["muted"], 255, "center")
        last = c.get("flash", 0.0)
        k = max(0.0, 1.0 - (time.time() - last) / 0.25)
        r = int(40 + 30 * k)
        g.rect(W // 2 - r, 260 - r, 2 * r, 2 * r, C["violet"], int(60 + 160 * k))
        g.frame(W // 2 - 70, 190, 140, 140, C["cyan"], 2)
        g.text("p24", "%d" % len(c["taps"]), W // 2, 248, C["text"], 255, "center")
        g.text("v20", "toques  (10 cliques)", W // 2, 350, C["muted"], 255, "center")

    def draw_editor(self, g, t):
        e = self.edit
        s = e["song"]
        g.text("p8", "EDITOR DE PISTA: " + s["title"][:20], W // 2, 64, C["text"], 255, "center")
        if e["phase"] == "setup":
            q = ["1/4", "1/8", "1/16", "LIVRE"][e["quant"]]
            g.text("p24", "%d BPM" % e["bpm"], W // 2, 140, C["cyan"], 255, "center")
            g.text("v20", "esq/dir ajusta o BPM  ·  cima/baixo grelha (%s)" % q, W // 2, 184, C["soft"], 255, "center")
            g.text("v20", "Quando a música tocar, carrega nas setas ou em Y B X A ao ritmo.", W // 2, 230,
                   C["soft"], 255, "center")
            g.text("v20", "As notas são alinhadas à grelha. START termina e guarda.", W // 2, 252, C["soft"], 255,
                   "center")
            g.text("v20", "Grava a pista a ouvir: o atraso acertado (L1) já é descontado.", W // 2, 274,
                   C["muted"], 255, "center")
            g.text("p8", "A começar   ·   B voltar", W // 2, 320, C["cyan"], 255, "center")
            return
        tt = (e["clock"].frames() - e["start"]) / float(SR)
        g.text("p24", "%d:%02d" % (max(0, tt) // 60, max(0, tt) % 60) if tt >= 0 else "%d" % (int(-tt) + 1),
               W // 2, 100, C["text"], 255, "center")
        for lane in range(4):
            x = W // 2 - 150 + lane * 76
            lit = time.time() - e["flash"][lane] < 0.12
            g.rect(x, 200, 70, 120, LANE_COL[lane] if lit else (24, 18, 50))
            g.frame(x, 200, 70, 120, LANE_COL[lane], 2)
            fg = (10, 6, 26) if lit else LANE_COL[lane]
            g.tri(x + 28, 226, 7, P1_GLYPH[lane], fg)
            g.text("p16", P2_GLYPH[lane], x + 35, 266, fg, 255, "center")
        g.text("v20", "%d notas gravadas  -  START guardar  -  SELECT cancelar" % len(e["notes"]), W // 2, 350,
               C["muted"], 255, "center")
