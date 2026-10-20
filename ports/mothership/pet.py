# XENO PET - a virtual alien pet that lives in the Mothership (tamagotchi style)
import math
import os
import random
import time

import engine
from engine import C, W, H, load_wav

PET_FILE = os.path.join(engine.APP, "pet.json")
SND = ("chirp", "happy", "sad", "eat", "call", "hatch", "poop", "clean", "heal", "star", "evolve", "bye")

NAMES = ["ZORP", "KIKI", "BLOOP", "NIX", "ORBI", "PIXA", "GLIM", "ZUZU", "MIRO", "TOKA", "VEXI", "LUMO",
         "QUIX", "FIZZ", "NOVA", "BIPO", "KOMI", "ZENA", "YUBI", "RAXO", "MOMO", "TIKO", "ULLA", "JAX"]

# stage limits in pet-seconds
HATCH_AT = 1 * 86400.0      # 1 day as an egg
TEEN_AT = 4 * 86400.0       # child period (days 2-8): BEBE then CRIANCA
ADULT_AT = 8 * 86400.0      # adult from day 8 ...
DEPART_AT = 30 * 86400.0    # ... until day 30

# ------------------------------------------------------------------ sprites
# K outline, B body, D shade, L highlight, A accent, W shell, S spot
SPRITES = {
    "egg": ["...KKKK...", "..KLLWWK..", ".KLWWWWWK.", ".KWWSWWWK.", "KWWWWWWWWK", "KWSWWWWSWK",
            "KWWWWWWWWK", "KWWWWSWWWK", ".KWWWWWWK.", ".KWWWWWWK.", "..KKKKKK.."],
    "baby": ["......AA......", ".......K......", ".......K......", "....KKKKKK....", "...KBBBBBBK...",
             "..KBLLBBBBBK..", "..KBLBBBBBBK..", ".KBBBBBBBBBBK.", ".KBBBBBBBBBBK.", ".KDBBBBBBBBDK.",
             "..KDDBBBBDDK..", "...KKKKKKKK..."],
    "teen": ["..A..........A..", "...K........K...", "....K......K....", ".....KKKKKK.....",
             "....KBBBBBBK....", "...KBLLBBBBBK...", "..KBLBBBBBBBBK..", "..KBBBBBBBBBBK..",
             ".KBBBBBBBBBBBBK.", "KBKBBBBBBBBBBKBK", "KBKBBBBBBBBBBKBK", ".K.KDBBBBBBDK.K.",
             "...KDDBBBBDDK...", "....KKBKKBKK....", ".....KBK.KBK....", ".....KKK.KKK...."],
    "nebulon": ["........A.........", ".......AAA........", "........K.........", ".....KKKKKKKK.....",
                "....KBBBBBBBBK....", "...KBLLBBBBBBBK...", "..KBLBBBBBBBBBBK..", "..KBBBBBBBBBBBBK..",
                "..KBBBBBBBBBBBBK..", "...KBBBBBBBBBBK...", "..KKBBBBAABBBBKK..", ".KBKBBBBAABBBBKBK.",
                ".KBKBBBBBBBBBBKBK.", "..K.KBBBBBBBBK.K..", "....KDBBBBBBDK....", "....KDDKKKKDDK....",
                "....KBK....KBK....", "....KKK....KKK...."],
    "glorpo": ["...A..........A...", "....K........K....", ".....KKKKKKKK.....", "...KKBBBBBBBBKK...",
               "..KBBLLBBBBBBBBK..", ".KBBLBBBBBBBBBBBK.", ".KBBBBBBBBBBBBBBK.", "KBBBBBBBBBBBBBBBBK",
               "KBBBBBBBBBBBBBBBBK", "KBBBBBBBBBBBBBBBBK", "KDBBBBBBBBBBBBBBDK", ".KDBBBBBBBBBBBBDK.",
               ".KDDBBBBBBBBBBDDK.", "..KKDDDBBBBDDDKK..", "...KBBK....KBBK...", "...KKKK....KKKK..."],
    "snarx": [".K....K....K....K.", ".KK..KK....KK..KK.", "..KKKBK....KBKKK..", "...KBBKKKKKKBBK...",
              "...KBBBBBBBBBBK...", "..KBBBBBBBBBBBBK..", ".KBBDBBBBBBBBDBBK.", ".KBBBBBBBBBBBBBBK.",
              "KKBBBBBBBBBBBBBBKK", ".KBBBBBBBBBBBBBBK.", "KKDBBBBBBBBBBBBDKK", ".KDDBBBBBBBBBBDDK.",
              "..KDDBBBBBBBBDDK..", "...KKDDDDDDDDKK...", "....KBK....KBK....", "....KKK....KKK...."],
}
# eyes: list of (col,row) of the top-left of each 2x2 eye ; mouth (col,row) left cell of a 2-wide mouth
FACE = {
    "baby": ([(4, 6), (8, 6)], (6, 9)),
    "teen": ([(5, 6), (9, 6)], (7, 9)),
    "nebulon": ([(5, 6), (11, 6)], (8, 9)),
    "glorpo": ([(4, 6), (8, 6), (12, 6)], (8, 10)),
    "snarx": ([(5, 7), (11, 7)], (8, 10)),
}
PALETTES = {
    "egg": {"K": (40, 30, 90), "W": (232, 226, 255), "L": (255, 255, 255), "S": (157, 107, 255)},
    "baby": {"K": (36, 22, 92), "B": (150, 110, 255), "D": (104, 70, 214), "L": (205, 185, 255), "A": (255, 138, 42)},
    "teen": {"K": (20, 40, 90), "B": (90, 200, 255), "D": (50, 130, 214), "L": (190, 240, 255), "A": (255, 138, 42)},
    "nebulon": {"K": (16, 30, 80), "B": (70, 230, 240), "D": (40, 150, 200), "L": (210, 255, 255), "A": (255, 220, 90)},
    "glorpo": {"K": (20, 60, 30), "B": (124, 230, 120), "D": (70, 170, 80), "L": (210, 255, 200), "A": (255, 138, 42)},
    "snarx": {"K": (40, 10, 30), "B": (200, 70, 120), "D": (140, 40, 90), "L": (255, 160, 190), "A": (255, 138, 42)},
}
SCALE = {"egg": 9, "baby": 8, "teen": 7, "nebulon": 7, "glorpo": 7, "snarx": 7}
FORM_NAME = {"egg": "OVO", "baby": "BEBÉ", "teen": "CRIANÇA", "nebulon": "NEBULON", "glorpo": "GLORPO",
             "snarx": "SNARX"}
FORM_DESC = {"nebulon": "Cuidaste dele de forma exemplar. Brilha como uma estrela.",
             "glorpo": "Bem cuidado, feliz e redondinho. Tem três olhos para te ver melhor.",
             "snarx": "Cresceu com pouca atenção... e ficou espinhoso e rabugento."}

ICONS = {
    "COMER": ["...##...", "....#...", ".######.", "##+#####", "########", "########", ".######.", "..#..#.."],
    "BRINCAR": ["...#....", "...#....", "#######.", ".#####..", "..###...", ".##.##..", "##...##.", "........"],
    "LIMPAR": [".##.....", "#..#.##.", ".##.#..#", "....#..#", ".##..##.", "#..#....", "#..#.##.", ".##..##."],
    "LUZ": ["..####..", ".#++###.", ".#+####.", ".######.", "..####..", "...##...", "..####..", "...##..."],
    "CURAR": ["..####..", "..####..", "########", "########", "########", "########", "..####..", "..####.."],
    "MIMO": [".##.##..", "########", "#+######", "########", ".######.", "..####..", "...##...", "........"],
    "ESTADO": ["......#.", "......#.", "...#..#.", "...#..#.", "#..#..#.", "#..#..#.", "#..#..#.", "########"],
}
ACTIONS = ["COMER", "BRINCAR", "LIMPAR", "LUZ", "CURAR", "MIMO", "ESTADO"]
ICON_COL = {"COMER": C["orange"], "BRINCAR": C["cyan"], "LIMPAR": (120, 200, 255), "LUZ": (255, 220, 90),
            "CURAR": C["green"], "MIMO": (255, 110, 170), "ESTADO": C["violet"]}

HEART = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]
STAR = ["...#...", "..###..", "#######", ".#####.", ".##.##.", "#.....#"]
POOP = ["...#....", "..##....", ".####...", ".#####..", "#######.", "########"]
BUBBLE = [".##.", "#..#", "#..#", ".##."]
MOON = ["..####..", ".##.....", "##......", "##......", "##......", "##.....#", ".##...##", "..####.."]
BROKEN = [".##.##..", "###.###.", "####.##.", "###.###.", ".##.##..", "..#.#...", "...#....", "........"]
NEED_ICON = {"doente": (ICONS["CURAR"], C["green"]), "fome": (ICONS["COMER"], C["orange"]),
             "sujo": (POOP + ["........", "........"], (110, 200, 80)), "sono": (MOON, (255, 220, 90)),
             "triste": (BROKEN, (255, 110, 170))}
NEED_TEXT = {"doente": "%s está doente!", "fome": "%s tem fome!", "sujo": "%s precisa de banho!",
             "sono": "%s tem sono...", "triste": "%s sente-se sozinho..."}


def draw_grid(g, grid, x, y, s, colmap):
    """grid of chars -> batched rects per colour. colmap: char -> (r,g,b) or None"""
    groups = {}
    for ry, row in enumerate(grid):
        for rx, ch in enumerate(row):
            col = colmap.get(ch)
            if col is not None:
                groups.setdefault(col, []).append((x + rx * s, y + ry * s, s, s))
    for col, lst in groups.items():
        g.rects(lst, col)


def mono(grid, col, hi=None):
    m = {"#": col}
    if hi:
        m["+"] = hi
    return m


# ------------------------------------------------------------------ state
def new_pet(gen=1, history=None):
    return {"gen": gen, "name": None, "form": "egg", "age": 0.0, "full": 70.0, "happy": 70.0, "energy": 80.0,
            "hygiene": 100.0, "health": 100.0, "weight": 5.0, "poops": 0, "sick": False, "sleeping": False,
            "lights_off": False, "poop_t": 5400.0, "care_acc": 0.0, "care_t": 0.0, "games": 0, "meals": 0,
            "last_seen": time.time(), "history": history or [], "born_wall": time.time(),
            "hue": random.random()}


_PAL_CACHE = {}


AWAY_CHOICES = [("Pouco", "menos de 1 hora", 1800), ("Umas horas", "cerca de 3 horas", 3 * 3600),
                ("Uma noite", "cerca de 8 horas", 8 * 3600), ("Um dia", "24 horas", 86400),
                ("Vários dias", "3 dias", 3 * 86400)]


def boot_uptime():
    """seconds since the console booted (Linux), or None"""
    try:
        return float(open("/proc/uptime").read().split()[0])
    except Exception:
        return None


def palette_for(form, hue=0.0, sick=False):
    """form palette with the body colours hue-rotated (each pet has its own colour)"""
    key = (form, round(hue, 3), sick)
    if key in _PAL_CACHE:
        return _PAL_CACHE[key]
    import colorsys
    pal = dict(PALETTES[form])
    for k in ("B", "D", "L", "S"):
        if k in pal and hue:
            r, g, b = [c / 255.0 for c in pal[k]]
            h, l, sat = colorsys.rgb_to_hls(r, g, b)
            r, g, b = colorsys.hls_to_rgb((h + hue) % 1.0, l, sat)
            pal[k] = (int(r * 255), int(g * 255), int(b * 255))
    if sick and form != "egg":
        pal["B"] = engine.mix(pal["B"], (150, 200, 90), 0.45)
        pal["D"] = engine.mix(pal["D"], (100, 150, 60), 0.45)
    pal["."] = None
    _PAL_CACHE[key] = pal
    return pal


class XenoPet(object):
    name = "XENO PET"

    def __init__(self, app):
        self.app = app
        self.snd = {}
        for k in SND:
            try:
                self.snd[k] = load_wav(os.path.join(engine.ASSETS, "pet", k + ".wav"))
            except Exception:
                pass
        self.p = self.load()
        self.events = []        # queued modal events
        self.away_report = None
        self.mode = "home"
        self.sel = 0
        self.sub = 0
        self.x = W / 2.0
        self.tx = W / 2.0
        self.wait = 1.0
        self.hop = 0.0
        self.anim = None        # (kind, t_start, data)
        self.particles = []     # [x,y,vx,vy,life,kind]
        self.msg = ""
        self.msg_t = 0
        self.last_call = 0
        self.save_t = 0
        self.name_opts = []
        self.shake = 0.0
        self.game = None
        self.note = None
        self.prev_needs = set()
        self.msg_kind = "info"
        self.msel = 0
        self.mem_new = False
        self.stars = [[random.uniform(20, W - 20), random.uniform(90, 200), random.random()] for _ in range(40)]
        self.catch_up()
        self._wall = time.time()

    # ---------------------------------------------------------------- persistence
    def load(self):
        p = engine.load_save(PET_FILE)
        base = new_pet()
        if p:
            base.update(p)
        return base

    def save(self, sync=True):
        self.p["last_seen"] = time.time()
        try:
            engine.write_json(PET_FILE, self.p, sync)
        except Exception:
            pass

    def catch_up(self):
        """simulate the time the console was off. The pet lives in real time (the system clock), but the R36S
        has no battery-backed clock: while it is off, its clock stops (or resets), so that time is lost. When
        the console has just booted and its clock says almost no time passed, the pet asks how long you were
        away instead of guessing."""
        now = time.time()
        gap = now - float(self.p.get("last_seen", now))
        up = boot_uptime()
        if gap < 0 or gap > 60 * 86400:
            self.away_report = {"clock": True, "ask": True}
            self.p["last_seen"] = now
            return
        if up is not None and up < 900 and gap < up + 300 and gap < 1800 and self.p.get("name"):
            self.away_report = {"clock": True, "ask": True}
            return
        if gap < 120:
            return
        self.simulate(gap)

    def simulate(self, gap):
        """live through a long stretch of real time in 1-minute steps (console off, asleep or frozen)"""
        before = dict((k, self.p[k]) for k in ("full", "happy", "energy", "hygiene", "health", "poops", "form"))
        was_sick = self.p["sick"]
        gap = min(gap, 7 * 86400)
        step = 60.0
        n = int(gap // step)
        for _ in range(n):
            self.tick(step, away=True)
            if self.events and self.events[-1][0] == "depart":
                break
        self.tick(gap - n * step, away=True)
        self.away_report = {"gap": gap, "before": before, "after": dict((k, self.p[k]) for k in before),
                            "got_sick": (not was_sick) and self.p["sick"]}

    def real_dt(self):
        """seconds of REAL time since the last frame, from the wall clock: the pet ages in real time even
        when frames are slow (the app's frame time is capped at 0.1 s). A long jump (the console slept) is
        lived like time away; a clock that went backwards is ignored."""
        now = time.time()
        d = now - self._wall
        self._wall = now
        if d < 0 or d > 60 * 86400:
            return 0.0
        if d > 120:
            self.simulate(d * self.speed())
            return 0.0
        return d

    # ---------------------------------------------------------------- simulation
    def play(self, k, gain=0.7):
        if k in self.snd:
            self.app.mixer.shot("pet_" + k, self.snd[k], group="ui", gain=gain)

    def tick(self, sec, away=False):
        p = self.p
        p["age"] += sec
        if p["form"] == "egg":
            if p["age"] >= HATCH_AT and not self._queued("hatch") and self.mode != "name":
                self.events.append(("hatch", None))
            return
        h = sec / 3600.0
        mult = 0.6 if away else 1.0
        baby = p["form"] == "baby"
        if p["sleeping"]:
            p["full"] -= 2.5 * h * mult
            p["energy"] += 25 * h
            p["happy"] -= (1 + (0 if p["lights_off"] else 2)) * h * mult
            p["hygiene"] -= 2 * h * mult
            if p["energy"] >= 100:
                p["sleeping"] = False
                p["lights_off"] = False
                if not away:
                    self.say("%s acordou!" % p["name"])
                    self.play("chirp")
        else:
            p["full"] -= (9 if baby else 7) * h * mult
            p["energy"] -= (8 if baby else 6) * h * mult
            p["happy"] -= (5 + (4 if p["full"] < 25 else 0) + 3 * p["poops"] + (3 if p["lights_off"] else 0)) * h * mult
            p["hygiene"] -= (3 + 6 * p["poops"]) * h * mult
            if p["energy"] < 12 or (p["lights_off"] and p["energy"] < 85):
                p["sleeping"] = True
        p["poop_t"] -= sec
        if p["poop_t"] <= 0:
            if p["poops"] < 4:
                p["poops"] += 1
                if not away:
                    self.play("poop")
            p["poop_t"] = random.uniform(3600, 7200) if baby else random.uniform(5400, 10800)
        risk = (0.15 if p["hygiene"] < 30 else 0) + (0.15 if p["poops"] >= 3 else 0) + (0.1 if p["full"] < 10 else 0)
        if not p["sick"] and risk and random.random() < risk * h:
            p["sick"] = True
            if not away:
                self.play("sad")
        if p["sick"]:
            p["health"] -= 6 * h * mult
            p["happy"] -= 3 * h * mult
        if p["full"] <= 0 or p["hygiene"] <= 5:
            p["health"] -= 5 * h * mult
        elif not p["sick"] and p["full"] > 40 and p["hygiene"] > 40:
            p["health"] += 3 * h
        for k in ("full", "happy", "energy", "hygiene", "health"):
            p[k] = max(0.0, min(100.0, p[k]))
        q = (p["full"] + p["happy"] + p["hygiene"] + p["health"]) / 4.0
        p["care_acc"] += q * sec
        p["care_t"] += sec
        # growth
        if self.mode == "event":
            return
        if p["form"] == "baby" and p["age"] >= TEEN_AT and not self._queued("evolve"):
            self.events.append(("evolve", "teen"))
        elif p["form"] == "teen" and p["age"] >= ADULT_AT and not self._queued("evolve"):
            care = self.care()
            self.events.append(("evolve", "nebulon" if care >= 68 else ("glorpo" if care >= 42 else "snarx")))
        if (p["health"] <= 0 or p["age"] >= DEPART_AT) and not self._queued("depart"):
            self.events.append(("depart", "sick" if p["health"] <= 0 else "old"))

    def _queued(self, kind):
        return any(e[0] == kind for e in self.events)

    def care(self):
        p = self.p
        base = p["care_acc"] / p["care_t"] if p["care_t"] else 70.0
        return min(100.0, base + min(12, p["games"] * 1.5))

    def bg(self, dt):
        """called every frame while the pet section is not on screen"""
        self.tick(self.real_dt() * self.speed())
        self.save_t += dt
        if self.save_t > 30:
            self.save_t = 0
            self.save(sync=False)

    def speed(self):
        return {1: 1.0, 10: 10.0, 60: 60.0}.get(int(self.app.cfg.get("pet_speed", 1)), 1.0)

    def say(self, s, kind="info"):
        self.msg = s
        self.msg_kind = kind
        self.msg_t = time.time()

    def current_needs(self):
        p = self.p
        if p["form"] == "egg" or p["sleeping"]:
            return []
        n = []
        if p["sick"]:
            n.append("doente")
        if p["full"] < 25:
            n.append("fome")
        if p["hygiene"] < 30 or p["poops"] >= 2:
            n.append("sujo")
        if p["energy"] < 15:
            n.append("sono")
        if p["happy"] < 25:
            n.append("triste")
        return n

    def needs(self):
        return bool(self.current_needs())

    # ---------------------------------------------------------------- section api
    def enter(self):
        self.mode = "home"
        if self.away_report and (self.p["form"] != "egg" or self.away_report.get("ask")):
            self.mode = "away"
            self.sub = 1
        self.process_events()

    def leave(self):
        self.save()

    def process_events(self):
        if self.mode not in ("home", "away") or not self.events:
            return
        kind, data = self.events.pop(0)
        if (kind == "hatch" and self.p["form"] != "egg") or (kind == "evolve" and data == self.p["form"]):
            return self.process_events()
        if kind == "hatch":
            self.name_opts = random.sample(NAMES, 3)
            self.sub = 0
            self.mode = "name"
            self.anim = ("hatch", time.time(), None)
            self.play("hatch")
        elif kind == "evolve":
            self.mode = "event"
            self.anim = ("evolve", time.time(), data)
            self.play("evolve")
        elif kind == "depart":
            self.mode = "event"
            self.anim = ("depart", time.time(), data)
            self.play("bye")

    def finish_event(self):
        kind, t0, data = self.anim
        p = self.p
        if kind == "evolve":
            p["form"] = data
        elif kind == "depart":
            p["history"].append({"gen": p["gen"], "name": p["name"], "form": p["form"],
                                 "days": round(p["age"] / 86400.0, 1), "reason": data,
                                 "hue": p.get("hue", 0.0), "games": p["games"]})
            self.p = new_pet(p["gen"] + 1, p["history"][-40:])
            self.events = []
            self.anim = None
            self.mode = "memorial"
            self.msel = len(self.p["history"]) - 1
            self.mem_new = True
            self.save()
            return
        if kind == "evolve":
            self.say("%s cresceu!" % p["name"], "good")
        self.anim = None
        self.mode = "home"
        self.save()

    def on(self, kind, b):
        if kind not in ("press", "repeat"):
            if kind == "release" and self.game:
                self.game["keys"].discard(b)
            return
        m = self.mode
        if m == "away":
            r = self.away_report or {}
            if r.get("ask"):
                if b in ("up", "down"):
                    self.sub = (self.sub + (1 if b == "down" else -1)) % len(AWAY_CHOICES)
                    self.app.ui_move()
                elif kind == "press" and b in ("a", "start"):
                    self.simulate(AWAY_CHOICES[self.sub][2])
                    self.app.ui_ok()
                elif kind == "press" and b == "b":
                    self.away_report = None
                    self.mode = "home"
                    self.process_events()
                return
            if kind == "press" and b in ("a", "b", "start"):
                self.away_report = None
                self.mode = "home"
                self.process_events()
            return
        if m == "name":
            if b in ("left", "right"):
                self.sub = (self.sub + (1 if b == "right" else -1)) % 3
                self.app.ui_move()
            elif b == "x" and kind == "press":
                self.name_opts = random.sample(NAMES, 3)
            elif b == "a" and kind == "press":
                self.p["name"] = self.name_opts[self.sub]
                self.p["form"] = "baby"
                self.p["poop_t"] = 3600.0
                self.mode = "home"
                self.anim = None
                self.play("happy")
                self.say("Bem-vindo, %s!" % self.p["name"], "good")
                self.save()
            return
        if m == "event":
            if kind == "press" and b in ("a", "start") and time.time() - self.anim[1] > 2.5:
                self.finish_event()
                self.process_events()
            return
        if m == "stats":
            if kind == "press" and b in ("a", "b"):
                self.mode = "home"
            elif kind == "press" and b == "y":
                self.mode = "memorial"
                self.msel = max(0, len(self.p["history"]) - 1)
                self.mem_new = False
            return
        if m in ("memorial", "memorial_del"):
            hist = self.p["history"]
            if m == "memorial_del":
                if kind == "press" and b == "a" and hist:
                    del hist[self.msel]
                    self.msel = max(0, min(self.msel, len(hist) - 1))
                    self.save()
                    self.mode = "memorial"
                elif kind == "press" and b == "b":
                    self.mode = "memorial"
                return
            if b in ("left", "right") and hist:
                self.msel = (self.msel + (1 if b == "right" else -1)) % len(hist)
                self.app.ui_move()
            elif kind == "press" and b == "x" and hist:
                self.mode = "memorial_del"
            elif kind == "press" and b in ("b", "a", "start"):
                self.mode = "home"
                self.mem_new = False
            return
        if m == "feed":
            if b in ("left", "right"):
                self.sub = 1 - self.sub
            elif b == "a" and kind == "press":
                self.mode = "home"
                self.feed(self.sub)
            elif b == "b":
                self.mode = "home"
            return
        if m == "game":
            if kind == "press":
                self.game["keys"].add(b)
                if b == "b" and self.game.get("over"):
                    self.end_game()
            return
        # home
        if self.p["form"] == "egg":
            if kind == "press" and b == "a":
                self.hop = 0.3
                self.play("chirp", 0.4)
                left = max(0, HATCH_AT - self.p["age"]) / self.speed()
                self.say("A chocar... faltam %dh %02dm" % (left // 3600, (left % 3600) // 60))
            return
        if b in ("left", "right"):
            self.sel = (self.sel + (1 if b == "right" else -1)) % len(ACTIONS)
            self.app.ui_move()
        elif b == "a" and kind == "press":
            self.act(ACTIONS[self.sel])

    def act(self, a):
        p = self.p
        if p["sleeping"] and a not in ("LUZ", "ESTADO"):
            self.say("Shhh... %s está a dormir." % p["name"])
            return
        if a == "COMER":
            self.mode = "feed"
            self.sub = 0
        elif a == "BRINCAR":
            if p["sick"]:
                self.say("Está doente, não quer brincar.")
                self.play("sad")
            elif p["energy"] < 15:
                self.say("Esta muito cansado...")
            else:
                self.start_game()
        elif a == "LIMPAR":
            self.anim = ("clean", time.time(), None)
            self.play("clean")
            p["poops"] = 0
            p["hygiene"] = 100.0
            p["happy"] = min(100, p["happy"] + 3)
        elif a == "LUZ":
            p["lights_off"] = not p["lights_off"]
            if p["lights_off"] and p["energy"] < 85:
                p["sleeping"] = True
                self.say("Boa noite, %s..." % p["name"])
            elif p["lights_off"]:
                self.say("Não tem sono!")
        elif a == "CURAR":
            if p["sick"]:
                p["sick"] = False
                p["health"] = min(100, p["health"] + 25)
                p["happy"] = max(0, p["happy"] - 5)
                self.anim = ("heal", time.time(), None)
                self.play("heal")
                self.say("Remédio dado. Já está melhor!")
            else:
                self.say("Não está doente.")
                self.shake = 0.6
        elif a == "MIMO":
            p["happy"] = min(100, p["happy"] + 8)
            self.hop = 0.5
            self.play("happy")
            for _ in range(5):
                self.particles.append([self.x + random.uniform(-30, 30), 250, random.uniform(-15, 15), -60, 1.5,
                                       "heart"])
        elif a == "ESTADO":
            self.mode = "stats"

    def feed(self, kind):
        p = self.p
        if p["full"] >= 95:
            self.say("Não tem fome!")
            self.shake = 0.6
            return
        if kind == 0:
            p["full"] = min(100, p["full"] + 35)
            p["weight"] += 1
            p["meals"] += 1
        else:
            p["full"] = min(100, p["full"] + 10)
            p["happy"] = min(100, p["happy"] + 12)
            p["weight"] += 2
        self.anim = ("eat", time.time(), kind)
        self.play("eat")

    # ---------------------------------------------------------------- mini game: STAR CATCH
    def start_game(self):
        self.game = {"t": 20.0, "score": 0, "x": W / 2.0, "items": [], "spawn": 0.5, "keys": set(), "over": False,
                     "hit": 0.0}
        self.mode = "game"

    def end_game(self):
        g = self.game
        p = self.p
        p["happy"] = min(100, p["happy"] + min(35, 8 + g["score"] * 2))
        p["energy"] = max(0, p["energy"] - 10)
        p["weight"] = max(1, p["weight"] - 1)
        p["games"] += 1
        self.game = None
        self.mode = "home"
        self.play("happy")
        self.say("Estrelas apanhadas: %d" % g["score"])

    def update_game(self, dt):
        g = self.game
        if g["over"]:
            g["t"] -= dt
            if g["t"] < -2.5:
                self.end_game()
            return
        g["t"] -= dt
        ax = self.app.input.axes["lx"]
        v = 0
        if self.app.input.down("left"):
            v -= 1
        if self.app.input.down("right"):
            v += 1
        v += ax
        g["x"] = max(40, min(W - 40, g["x"] + v * 320 * dt))
        g["spawn"] -= dt
        if g["spawn"] <= 0:
            g["spawn"] = random.uniform(0.3, 0.65)
            meteor = random.random() < 0.22
            g["items"].append([random.uniform(30, W - 30), 60.0, random.uniform(130, 220), meteor])
        keep = []
        for it in g["items"]:
            it[1] += it[2] * dt
            if 330 < it[1] < 370 and abs(it[0] - g["x"]) < 40:
                if it[3]:
                    g["score"] = max(0, g["score"] - 2)
                    g["hit"] = 0.4
                    self.play("sad", 0.4)
                else:
                    g["score"] += 1
                    self.play("star", 0.5)
                continue
            if it[1] < 400:
                keep.append(it)
        g["items"] = keep
        g["hit"] = max(0, g["hit"] - dt)
        if g["t"] <= 0:
            g["over"] = True
            g["t"] = 0

    # ---------------------------------------------------------------- update
    def update(self, dt):
        self.tick(self.real_dt() * self.speed())
        self.save_t += dt
        if self.save_t > 30:
            self.save_t = 0
            self.save(sync=False)
        if self.mode == "game":
            self.update_game(dt)
            return
        self.process_events()
        # wander
        p = self.p
        if p["form"] != "egg" and not p["sleeping"] and self.anim is None:
            if abs(self.tx - self.x) < 3:
                self.wait -= dt
                if self.wait <= 0:
                    self.tx = random.uniform(140, W - 140)
                    self.wait = random.uniform(1.0, 4.0)
                    if p["happy"] > 70 and random.random() < 0.4:
                        self.hop = 0.35
            else:
                sp = 50 if p["happy"] > 40 else 25
                self.x += max(-sp * dt, min(sp * dt, self.tx - self.x))
        self.hop = max(0.0, self.hop - dt)
        self.shake = max(0.0, self.shake - dt)
        for pt in self.particles:
            pt[0] += pt[2] * dt
            pt[1] += pt[3] * dt
            pt[4] -= dt
        self.particles = [pt for pt in self.particles if pt[4] > 0]
        if self.anim and self.anim[0] in ("eat", "clean", "heal") and time.time() - self.anim[1] > 1.6:
            self.anim = None
        now = time.time()
        cur = self.current_needs()
        new = [k for k in cur if k not in self.prev_needs]
        if new or (cur and now - self.last_call > 25):
            k = new[0] if new else cur[0]
            self.note = (k, now)
            self.last_call = now
            self.play("call", 0.5)
            self.hop = 0.35
            if new and self.mode == "home":
                self.say(NEED_TEXT[k] % (p["name"] or ""), "warn")
        self.prev_needs = set(cur)
        if not cur:
            self.note = None

    # ---------------------------------------------------------------- drawing
    def draw_pet(self, g, form, cx, base_y, t, mood="ok", scale=None, hue=None, portrait=False):
        grid = SPRITES[form]
        s = scale or SCALE[form]
        w = len(grid[0]) * s
        h = len(grid) * s
        bob = 0
        p = self.p
        if portrait:
            x = int(cx - w / 2)
        elif form == "egg":
            wob = math.sin(t * 6) * 3 if (int(t) % 3 == 0) else 0
            x = int(cx - w / 2 + wob)
        else:
            if not p["sleeping"]:
                bob = int(abs(math.sin(t * 4)) * s * 0.6)
            if self.hop > 0:
                bob += int(math.sin(self.hop / 0.35 * math.pi) * 40)
            x = int(cx - w / 2 + (math.sin(t * 40) * 4 if self.shake > 0 else 0))
        y = int(base_y - h - bob)
        if portrait:
            draw_grid(g, grid, x, y, s, palette_for(form, hue or 0.0, False))
            eyes, mouth = FACE.get(form, ([], (0, 0)))
            dark = PALETTES[form]["K"]
            for ex, ey in eyes:
                g.rect(x + ex * s, y + ey * s, 2 * s, 2 * s, (255, 255, 255))
                g.rect(x + ex * s + s // 2, y + ey * s + s // 2, s, s, dark)
            g.rect(x + mouth[0] * s, y + mouth[1] * s, 2 * s, max(1, s // 2), dark)
            return x, y, w, h
        pal = palette_for(form, hue if hue is not None else p.get("hue", 0.0), p["sick"] and not portrait)
        # shadow
        g.rect(cx - w * 0.35, base_y - 2, w * 0.7, 6, (0, 0, 0), 90)
        draw_grid(g, grid, x, y, s, pal)
        if form == "egg":
            return x, y, w, h
        eyes, mouth = FACE[form]
        blink = (t % 3.7) < 0.12
        dark = PALETTES[form]["K"]
        look = 1 if self.tx > self.x + 2 else (-1 if self.tx < self.x - 2 else 0)
        for ex, ey in eyes:
            px, py = x + ex * s, y + ey * s
            if (p["sleeping"] and not portrait) or mood == "sleep":
                g.rect(px, py + s, 2 * s, max(2, s // 2), dark)
            elif blink:
                g.rect(px, py + s // 2 + s // 2, 2 * s, max(2, s // 2), dark)
            elif mood == "happy":
                g.rect(px, py + s, s, s // 2 + 1, dark)
                g.rect(px + s // 2, py + s // 2, s, s // 2 + 1, dark)
                g.rect(px + s, py + s, s, s // 2 + 1, dark)
            else:
                g.rect(px, py, 2 * s, 2 * s, (255, 255, 255))
                g.rect(px + s // 2 + look * (s // 2), py + s // 2 + (s // 3 if mood == "sad" else 0), s, s, dark)
                if mood == "sad":
                    g.rect(px, py, 2 * s, s // 2, pal["B"])
                if form == "snarx":
                    g.rect(px - s // 2, py - s // 2, 2 * s + s, s // 2, dark)
        mx, my = x + mouth[0] * s, y + mouth[1] * s
        if self.anim and self.anim[0] == "eat" and int(t * 6) % 2 == 0:
            g.rect(mx, my, 2 * s, 2 * s, dark)
        elif p["sleeping"]:
            g.rect(mx + s // 2, my + s // 2, s, s // 2, dark)
        elif mood == "happy":
            g.rect(mx, my, 2 * s, s // 2, dark)
            g.rect(mx - s // 2, my - s // 2, s // 2, s // 2, dark)
            g.rect(mx + 2 * s, my - s // 2, s // 2, s // 2, dark)
        elif mood == "sad":
            g.rect(mx, my + s // 2, 2 * s, s // 2, dark)
            g.rect(mx - s // 2, my + s, s // 2, s // 2, dark)
            g.rect(mx + 2 * s, my + s, s // 2, s // 2, dark)
        else:
            g.rect(mx + s // 4, my + s // 2, s + s // 2, s // 2, dark)
        return x, y, w, h

    def draw_bubble(self, g, t, ax, ay, size=1.0):
        """animated speech bubble with the icon of the current need. (ax, ay) = tail tip"""
        k, t0 = self.note
        el = time.time() - t0
        if el < 0.35:
            sc = min(1.0, el / 0.18) * (1 + 0.25 * math.sin(min(1.0, el / 0.35) * math.pi))
        else:
            sc = 1.0
        bw, bh = int(58 * sc * size), int(52 * sc * size)
        if bw < 6:
            return
        bob = math.sin(t * 4) * 3 * size
        bx, by = int(ax), int(ay - bh - 10 * size + bob)
        dark = (30, 20, 70)
        g.rect(bx + 2, by - 2, bw - 4, bh + 4, dark)
        g.rect(bx - 2, by + 2, bw + 4, bh - 4, dark)
        g.rect(bx + 4, by, bw - 8, bh, C["white"])
        g.rect(bx, by + 4, bw, bh - 8, C["white"])
        tail = [(ax + 2 + i, ay - 10 * size + bob + i * 2 - 2, max(2, 12 * size - i * 2), 3) for i in range(5)]
        g.rects(tail, C["white"])
        if sc > 0.85:
            grid, col = NEED_ICON[k]
            s = max(2, int(4 * size))
            gw = len(grid[0]) * s
            pulse = 1.0 + 0.12 * math.sin(t * 8)
            draw_grid(g, grid, int(bx + bw / 2 - gw * pulse / 2), int(by + bh / 2 - len(grid) * s / 2), s,
                      mono(grid, col, (255, 255, 255)))
        if el < 1.6 and size >= 1.0:
            jx = math.sin(t * 50) * 3
            g.text("k32", "!", bx + bw - 4 + jx, by - 24, (230, 40, 60))

    def mood(self):
        p = self.p
        if p["sleeping"]:
            return "sleep"
        if p["sick"] or p["happy"] < 30 or p["full"] < 20:
            return "sad"
        if p["happy"] > 70 or self.hop > 0:
            return "happy"
        return "ok"

    def draw_room(self, g, t, top=76, floor=330, bottom=388):
        p = self.p
        g.rect(0, top, W, floor - top, (14, 11, 40))
        # window
        wx, wy, ww, wh = 40, top + 16, 220, 150
        g.rect(wx, wy, ww, wh, (5, 4, 18))
        sts = []
        for s in self.stars:
            sx = wx + (s[0] / W) * ww
            sy = wy + ((s[1] - 90) / 110.0) * wh
            if wx < sx < wx + ww - 3 and wy < sy < wy + wh - 3:
                tw = 1 if (t * 2 + s[2] * 10) % 3 > 0.3 else 0
                if tw:
                    sts.append((sx, sy, 2, 2))
        g.rects(sts, (220, 220, 255))
        # planet with ring
        pcx, pcy, pr = wx + 150, wy + 60, 26
        rows = []
        for yy in range(-pr, pr + 1, 2):
            half = int(math.sqrt(max(0, pr * pr - yy * yy)))
            rows.append((pcx - half, pcy + yy, 2 * half, 2))
        g.rects(rows, (157, 107, 255))
        g.rects([(pcx - pr, pcy - pr // 3, pr, pr // 2)], (190, 150, 255), 90)
        g.rect(pcx - pr - 16, pcy - 2, 2 * pr + 32, 4, (255, 138, 42))
        g.frame(wx - 4, wy - 4, ww + 8, wh + 8, C["hullhi"], 4)
        g.rect(wx + ww // 2 - 2, wy, 4, wh, C["hullhi"])
        # shelf + plant
        g.rect(W - 230, top + 70, 170, 8, C["hull"])
        g.rect(W - 200, top + 40, 26, 30, (60, 50, 110))
        g.rect(W - 194, top + 22, 4, 20, C["green"])
        g.rect(W - 186, top + 16, 4, 26, C["green"])
        g.rect(W - 178, top + 26, 4, 16, C["green"])
        g.text("k16", "GEN %d" % p["gen"], W - 140, top + 46, C["muted"])
        # floor
        g.rect(0, floor, W, bottom - floor, (34, 28, 78))
        lines = [(0, floor + k * 14, W, 2) for k in range(1, 5)]
        g.rects(lines, (44, 38, 96))
        g.rect(0, floor, W, 3, C["hullhi"])

    def draw_poops(self, g, t, floor):
        for i in range(self.p["poops"]):
            px = W - 80 - i * 52
            draw_grid(g, POOP, px, floor + 6, 4, {"#": (110, 200, 80)})
            k = int(t * 3 + i) % 2
            g.rect(px + 8 + k * 6, floor - 8 - k * 4, 3, 8, (110, 200, 80), 140)
            g.rect(px + 22 - k * 6, floor - 14 + k * 4, 3, 8, (110, 200, 80), 140)

    def draw_bars(self, g):
        p = self.p
        items = [("Fome", p["full"], C["orange"]), ("Humor", p["happy"], (255, 110, 170)),
                 ("Energia", p["energy"], (255, 220, 90)), ("Higiene", p["hygiene"], (120, 200, 255)),
                 ("Saúde", p["health"], C["green"])]
        x = 12
        for lab, v, col in items:
            g.text("k16", lab, x, 45, C["muted"])
            g.rect(x, 71, 110, 7, C["deck"])
            low = v < 25 and int(time.time() * 3) % 2 == 0
            g.rect(x, 71, int(110 * v / 100.0), 7, (255, 70, 70) if low else col)
            x += 126

    def draw_icons(self, g, top=388):
        g.rect(0, top, W, H - top, C["deck"])
        g.rect(0, top, W, 3, C["hulllo"])
        n = len(ACTIONS)
        cw = W // n
        for i, a in enumerate(ACTIONS):
            x = i * cw
            sel = i == self.sel and self.mode == "home" and self.p["form"] != "egg"
            if sel:
                g.bevel(x + 4, top + 8, cw - 8, H - top - 14, self.app.accent, C["orangehi"], C["orangelo"])
            col = C["void"] if sel else ICON_COL[a]
            hi = (255, 255, 255) if not sel else C["void"]
            draw_grid(g, ICONS[a], x + cw // 2 - 12, top + 16, 3, mono(ICONS[a], col, hi))
            disabled = (a == "LUZ" and False)
            lab_col = C["void"] if sel else (C["dim"] if disabled else C["soft"])
            lab = a.capitalize()
            g.text("k16" if g.tw("k16", lab) < cw - 4 else "p8", lab, x + cw // 2, top + 50, lab_col, 255, "center")
        if self.p["lights_off"]:
            g.rect(3 * cw + 8, top + 8, cw - 16, 4, (255, 220, 90))

    def draw_header(self, g):
        p = self.p
        g.rect(0, 0, W, 42, C["deck"])
        g.rect(0, 42, W, 2, C["hulllo"])
        g.text("k24", "Xeno Pet", 12, 3, (255, 110, 170))
        name = p["name"] or "???"
        days = p["age"] / 86400.0
        hrs = (p["age"] % 86400) / 3600.0
        mins = (p["age"] % 3600) / 60.0
        age = ("%dd %dh" % (days, hrs)) if days >= 1 else ("%dh %02dm" % (hrs, mins))
        g.text("k24", name, W // 2, 3, C["text"], 255, "center")
        sp = self.speed()
        g.text("k16", "%s - %s%s" % (FORM_NAME[p["form"]].capitalize(), age, ("  x%d" % sp) if sp > 1 else ""),
               W - 12, 10, C["muted"] if sp == 1 else C["orange"], 255, "right")

    def draw(self, g, t, dt):
        p = self.p
        g.clear(C["void"])
        if self.mode == "game":
            self.draw_game(g, t)
            return
        if self.mode in ("memorial", "memorial_del"):
            self.draw_memorial(g, t)
            return
        self.draw_header(g)
        if p["form"] != "egg":
            self.draw_bars(g)
        top, floor, bottom = 84, 330, 388
        self.draw_room(g, t, top, floor, bottom)
        self.draw_poops(g, t, floor)
        form = p["form"]
        mood = self.mood()
        if self.mode == "event" and self.anim and self.anim[0] == "evolve":
            self.draw_evolve(g, t, floor)
        elif self.mode == "event" and self.anim and self.anim[0] == "depart":
            self.draw_depart(g, t, floor)
        else:
            cx = W / 2.0 if form == "egg" else self.x
            px, py, pw, ph = self.draw_pet(g, form, cx, floor + 30, t, mood)
            # need bubble
            if self.note and self.mode == "home":
                self.draw_bubble(g, t, px + pw - 8, py - 6, 1.0)
            if p["sleeping"]:
                for k in range(3):
                    zt = (t * 0.7 + k * 0.33) % 1.0
                    g.text("k24" if k else "k16", "Z", px + pw - 10 + zt * 40, py - zt * 50, C["text"],
                           int(255 * (1 - zt)))
            # animations
            if self.anim:
                kind, t0, data = self.anim
                el = time.time() - t0
                if kind == "eat":
                    bites = min(3, int(el / 0.5))
                    fx = int(self.x + pw / 2 + 10)
                    if data == 0:
                        cols = [(255, 160, 60), (255, 220, 120), (120, 220, 90)]
                        for i in range(3 - bites):
                            g.rect(fx, floor - 26 + i * 8, 34, 8, cols[i])
                        g.rect(fx - 4, floor - 2, 42, 6, (180, 180, 220))
                    else:
                        if bites < 3:
                            draw_grid(g, STAR, fx, floor - 34, 4, {"#": (255, 220, 90)})
                elif kind == "clean":
                    bl = []
                    for i in range(14):
                        bx = (el / 1.6) * (W + 200) - 100 - i * 30
                        by = floor - 20 - (i % 4) * 26 + math.sin(el * 8 + i) * 6
                        bl.append((bx, by))
                    for bx, by in bl:
                        draw_grid(g, BUBBLE, int(bx), int(by), 4, {"#": (160, 220, 255)})
                elif kind == "heal":
                    for i in range(8):
                        a = el * 4 + i * math.pi / 4
                        g.rect(px + pw / 2 + math.cos(a) * 70, py + ph / 2 + math.sin(a) * 50, 8, 8, C["green"])
        # particles
        for pt in self.particles:
            if pt[5] == "heart":
                draw_grid(g, HEART, int(pt[0]), int(pt[1]), 3, {"#": (255, 110, 170)})
        # night overlay
        if p["lights_off"]:
            g.rect(0, top, W, bottom - top, (4, 4, 24), 170)
        if p["sick"] and int(t * 1.5) % 2 == 0 and self.mode == "home":
            g.text("k16", "DOENTE", 16, floor + 40, C["green"])
        self.draw_icons(g, bottom)
        if self.msg and time.time() - self.msg_t < 3.2:
            el = time.time() - self.msg_t
            e = min(1.0, el / 0.4)
            ease = 1 - (1 - e) ** 3
            yy = top + 6 - (1 - ease) * 60 + math.sin(e * math.pi) * 8
            a = int(255 * max(0.0, min(1.0, (3.2 - el) / 0.4)))
            col = {"warn": C["orange"], "good": C["green"]}.get(self.msg_kind, C["cyan"])
            w = g.tw("k16", self.msg) + 36
            g.rect(W // 2 - w // 2, yy, w, 34, C["panel"], min(a, 240))
            g.frame(W // 2 - w // 2, yy, w, 34, col, 3, a)
            g.rect(W // 2 - w // 2 + 8, yy + 13, 8, 8, col, a)
            g.text("k16", self.msg, W // 2 + 8, yy + 7, C["text"], a, "center")
        # modals
        if self.mode == "feed":
            self.draw_modal(g, "COMER", ["REFEICAO", "SNACK"], self.sub,
                            ["+35 fome  +1 peso", "+10 fome  +12 humor  +2 peso"])
        elif self.mode == "stats":
            self.draw_stats(g)
        elif self.mode == "name":
            self.draw_name(g, t)
        elif self.mode == "away":
            self.draw_away(g)
        elif self.mode == "home" and form == "egg":
            g.text("k16", "UM OVO MISTERIOSO", 460, top + 110, C["text"], 255, "center")
            g.text("k16", "CAIU NA NAVE...", 460, top + 126, C["text"], 255, "center")
            if int(t * 1.5) % 2 == 0:
                g.text("k16", "A = AQUECER O OVO", 460, top + 152, C["orange"], 255, "center")

    def draw_modal(self, g, title, opts, sel, descs):
        x, y, w, h = 120, 150, 400, 160
        g.rect(x, y, w, h, C["panel"], 245)
        g.frame(x, y, w, h, self.app.accent, 3)
        g.text("k24", title, W // 2, y + 14, self.app.accent, 255, "center")
        for i, o in enumerate(opts):
            bx = x + 30 + i * 180
            on = i == sel
            g.bevel(bx, y + 46, 160, 50, self.app.accent if on else C["hull"],
                    C["orangehi"] if on else C["hullhi"], C["orangelo"] if on else C["hulllo"])
            g.text("k16", o, bx + 80, y + 66, C["void"] if on else C["text"], 255, "center")
        g.text("k16", descs[sel], W // 2, y + 106, C["soft"], 255, "center")
        g.text("k16", "A confirmar  ·  B cancelar", W // 2, y + 130, C["dim"], 255, "center")

    def draw_stats(self, g):
        p = self.p
        x, y, w, h = 60, 60, 520, 330
        g.rect(x, y, w, h, C["panel"], 250)
        g.frame(x, y, w, h, C["violet"], 3)
        g.text("k24", "FICHA DE %s" % (p["name"] or "?"), x + 20, y + 16, C["violet"])
        rows = [("GERAÇÃO", "%d" % p["gen"]), ("FASE", FORM_NAME[p["form"]]),
                ("IDADE", "%.1f dias" % (p["age"] / 86400.0)), ("PESO", "%d g" % p["weight"]),
                ("REFEIÇÕES", "%d" % p["meals"]), ("JOGOS", "%d" % p["games"]),
                ("CUIDADO", "%d%%" % self.care()), ("SAÚDE", "doente" if p["sick"] else "ok")]
        for i, (k, v) in enumerate(rows):
            yy = y + 52 + i * 26
            g.text("k16", k, x + 24, yy, C["muted"])
            g.text("k16", v, x + 220, yy, C["text"])
        if p["form"] in FORM_DESC:
            g.text("k16", FORM_DESC[p["form"]][:52], x + 24, y + 270, C["cyan"])
        hist = p.get("history", [])
        g.text("k16", "ANTEPASSADOS", x + 330, y + 52, C["muted"])
        for i, hh in enumerate(hist[-6:]):
            g.text("k16", "%d. %s %s %.0fd" % (hh["gen"], hh["name"], FORM_NAME.get(hh["form"], "?")[:7],
                                                 hh["days"]), x + 330, y + 68 + i * 22, C["soft"])
        g.text("k16", "Y memorial   -   A / B voltar", x + w - 20, y + h - 30, C["dim"], 255, "right")

    def draw_name(self, g, t):
        x, y, w, h = 90, 120, 460, 200
        g.rect(x, y, w, h, C["panel"], 245)
        g.frame(x, y, w, h, (255, 110, 170), 3)
        g.text("k24", "NASCEU UM XENO!", W // 2, y + 16, (255, 110, 170), 255, "center")
        g.text("k16", "Escolhe o nome dele", W // 2, y + 44, C["soft"], 255, "center")
        for i, n in enumerate(self.name_opts):
            bx = x + 20 + i * 145
            on = i == self.sub
            g.bevel(bx, y + 80, 130, 50, self.app.accent if on else C["hull"],
                    C["orangehi"] if on else C["hullhi"], C["orangelo"] if on else C["hulllo"])
            g.text("k24", n, bx + 65, y + 98, C["void"] if on else C["text"], 255, "center")
        g.text("k16", "A escolher  -  X outros nomes", W // 2, y + 150, C["dim"], 255, "center")

    def draw_away(self, g):
        r = self.away_report or {}
        x, y, w, h = 80, 110, 480, 230
        g.rect(x, y, w, h, C["panel"], 245)
        g.frame(x, y, w, h, C["cyan"], 3)
        g.text("k24", "ENQUANTO ESTIVESTE FORA", W // 2, y + 16, C["cyan"], 255, "center")
        if r.get("ask"):
            x, y, w, h = 70, 70, 500, 330
            g.rect(x, y, w, h, C["panel"], 250)
            g.frame(x, y, w, h, C["cyan"], 3)
            g.text("k24", "QUANTO TEMPO ESTIVESTE FORA?", W // 2, y + 14, C["cyan"], 255, "center")
            g.text("k16", "A consola não tem pilha de relógio: desligada, não conta o tempo.", W // 2, y + 50,
                   C["soft"], 255, "center")
            for i, (lab, sub, _) in enumerate(AWAY_CHOICES):
                yy = y + 84 + i * 42
                on = i == self.sub
                g.rect(x + 40, yy, w - 80, 36, self.app.accent if on else C["hull"])
                g.text("kb24", lab, x + 56, yy + 3, C["void"] if on else C["text"])
                g.text("k16", sub, x + w - 56, yy + 8, C["void"] if on else C["muted"], 255, "right")
            g.text("k16", "cima/baixo escolher  ·  A confirmar  ·  B não passou tempo", W // 2, y + h - 30, C["dim"],
                   255, "center")
            return
        if r.get("clock"):
            g.text("k16", "O relógio da consola foi reiniciado.", W // 2, y + 60, C["soft"], 255, "center")
            g.text("k16", "Não sei quanto tempo passou: ficou tudo como estava.", W // 2, y + 86, C["soft"], 255,
                   "center")
        else:
            gap = r.get("gap", 0)
            hrs = gap / 3600.0
            g.text("k16", "Passaram %s" % ("%.1f horas" % hrs if hrs < 48 else "%.1f dias" % (hrs / 24)), W // 2,
                   y + 50, C["soft"], 255, "center")
            b, a = r.get("before", {}), r.get("after", {})
            lines = []
            if a.get("poops", 0) > b.get("poops", 0):
                lines.append("Fez %d coco(s) na nave." % (a["poops"] - b["poops"]))
            if a.get("full", 0) < 30:
                lines.append("Está com fome!")
            if a.get("happy", 0) < 30:
                lines.append("Sente a tua falta.")
            if r.get("got_sick"):
                lines.append("Ficou doente: dá-lhe um remédio.")
            if a.get("form") != b.get("form"):
                lines.append("Cresceu!")
            if not lines:
                lines.append("Portou-se bem e está tudo em ordem.")
            for i, l in enumerate(lines[:4]):
                g.text("k16", l, W // 2, y + 86 + i * 24, C["text"], 255, "center")
        g.text("k16", "A continuar", W // 2, y + h - 34, C["dim"], 255, "center")

    def draw_evolve(self, g, t, floor):
        kind, t0, data = self.anim
        el = time.time() - t0
        cx = W / 2.0
        old = self.p["form"]
        flick = el < 2.5 and int(el * (4 + el * 6)) % 2 == 0
        form = old if (el < 2.5 and not flick) else data
        if el < 2.5:
            for i in range(12):
                a = el * 3 + i * math.pi / 6
                r = 120 - el * 30
                g.rect(cx + math.cos(a) * r, floor - 70 + math.sin(a) * r * 0.7, 6, 6, (255, 220, 90))
        self.draw_pet(g, form, cx, floor + 30, t, "happy")
        if el >= 2.5:
            g.rect(0, 0, W, H, (255, 255, 255), int(max(0, 255 - (el - 2.5) * 500)))
            g.text("k24", "%s EVOLUIU!" % self.p["name"], W // 2, 96, C["text"], 255, "center")
            g.text("k32", FORM_NAME[data], W // 2, 124, (255, 220, 90), 255, "center")
            if data in FORM_DESC:
                g.text("k16", FORM_DESC[data], W // 2, 156, C["soft"], 255, "center")
            if int(t * 2) % 2 == 0:
                g.text("k16", "A CONTINUAR", W // 2, floor + 40, C["text"], 255, "center")

    def draw_depart(self, g, t, floor):
        kind, t0, data = self.anim
        el = time.time() - t0
        cx = W / 2.0
        sy = -120 + min(1.0, el / 1.5) * 220
        rise = max(0.0, min(1.0, (el - 1.5) / 2.0))
        if el > 1.5:
            g.rects([(cx - 30 - i, sy + 110 + i * 4, 60 + 2 * i, 4) for i in range(0, 50, 2)], C["cyan"], 70)
        if rise < 1.0:
            self.draw_pet(g, self.p["form"], cx, floor + 30 - rise * 200, t, "happy" if data == "old" else "sad")
        engine.draw_ship(g, int(cx - 120), int(sy), 6, t, 0.0, self.app.accent)
        if el > 3.5:
            n = self.p["name"]
            if data == "old":
                l1, l2 = "%s cumpriu a sua missao." % n, "Regressou ao planeta natal, feliz."
            else:
                l1, l2 = "%s ficou muito doente." % n, "A nave-mae levou-o para o planeta natal."
            g.rect(60, 300, 520, 70, C["panel"], 240)
            g.text("k16", l1, W // 2, 308, C["text"], 255, "center")
            g.text("k16", l2, W // 2, 332, C["soft"], 255, "center")
            if int(t * 2) % 2 == 0:
                g.text("k16", "A = NOVO OVO", W // 2, 380, C["text"], 255, "center")

    def draw_tomb(self, g, t, x, y, entry, sel):
        w, h = 168, 232
        stone, stone_hi, stone_lo = (120, 116, 150), (160, 156, 190), (78, 74, 104)
        if sel:
            g.glow(x, y, w, h, self.app.accent, 0.45 + 0.35 * math.sin(t * 4))
        r = w // 2
        rows = []
        for yy in range(0, r, 3):
            half = int(math.sqrt(max(0, r * r - (r - yy) ** 2)))
            rows.append((x + r - half, y + yy, 2 * half, 3))
        g.rects(rows, stone)
        g.rect(x, y + r, w, h - r, stone)
        g.rect(x, y + r, 4, h - r, stone_hi)
        g.rect(x + w - 4, y + r, 4, h - r, stone_lo)
        g.rect(x - 10, y + h - 6, w + 20, 10, stone_lo)
        # portrait (the pet as a child)
        fx, fy, fw, fh = x + w // 2 - 40, y + 26, 80, 70
        g.rect(fx - 4, fy - 4, fw + 8, fh + 8, (90, 70, 40))
        g.rect(fx, fy, fw, fh, (20, 16, 50))
        self.draw_pet(g, "baby", fx + fw / 2, fy + fh - 6, t, scale=4, hue=entry.get("hue", 0.0), portrait=True)
        name = entry.get("name") or "?"
        g.text("k24", name, x + w // 2, y + 102, (40, 30, 70), 255, "center")
        g.text("k16", "Gen %d  -  %.0f dias" % (entry.get("gen", 1), entry.get("days", 0)), x + w // 2, y + 134,
               (50, 40, 80), 255, "center")
        g.text("k16", FORM_NAME.get(entry.get("form"), "?").capitalize(), x + w // 2, y + 154, (50, 40, 80), 255,
               "center")
        old = entry.get("reason") == "old"
        g.text("k16", "Viajou feliz" if old else "Partiu doente", x + w // 2, y + 176,
               (90, 40, 90) if old else (110, 40, 40), 255, "center")
        # flowers at the foot of the stone
        for i in range(3):
            fxx = x + 30 + i * 50
            sway = int(math.sin(t * 2 + i) * 2)
            g.rect(fxx + sway, y + h - 12, 3, 12, C["green"])
            g.rect(fxx - 4 + sway, y + h - 18, 11, 8, [(255, 110, 170), (255, 220, 90), (157, 107, 255)][i])

    def draw_memorial(self, g, t):
        g.clear((6, 5, 22))
        sts = [(s[0], (s[1] - 60) * 1.6, 2, 2) for s in self.stars if (t + s[2] * 5) % 4 > 0.4]
        g.rects(sts, (200, 200, 255))
        moon = []
        dark = []
        for yy in range(-24, 25, 2):
            half = int(math.sqrt(max(0, 24 * 24 - yy * yy)))
            moon.append((540 - half, 70 + yy, 2 * half, 2))
            half2 = int(math.sqrt(max(0, 22 * 22 - (yy + 4) ** 2)))
            if half2:
                dark.append((552 - half2, 66 + yy, 2 * half2, 2))
        g.rects(moon, (235, 230, 200))
        g.rects(dark, (6, 5, 22))
        g.rect(0, 410, W, 70, (24, 40, 30))
        g.rect(0, 410, W, 4, (40, 70, 50))
        g.text("k32", "MEMORIAL XENO", W // 2, 12, (255, 110, 170), 255, "center")
        hist = self.p["history"]
        if not hist:
            g.text("k24", "Ainda ninguem partiu.", W // 2, 210, C["soft"], 255, "center")
            g.text("k16", "B voltar", W // 2, 440, C["dim"], 255, "center")
            return
        page = self.msel // 3
        for i in range(3):
            idx = page * 3 + i
            if idx >= len(hist):
                break
            self.draw_tomb(g, t, 30 + i * 200, 170, hist[idx], idx == self.msel)
        if self.mem_new and int(t * 2) % 2 == 0:
            g.text("k16", "Uma nova lápide foi erguida. Um novo ovo já chegou à nave.", W // 2, 56, C["text"],
                   255, "center")
        g.text("k16", "%d / %d" % (self.msel + 1, len(hist)), W // 2, 84, C["muted"], 255, "center")
        g.text("k16", "esq/dir escolher  ·  X apagar lápide  ·  B voltar", W // 2, 446, C["text"], 255, "center")
        if self.mode == "memorial_del":
            g.rect(130, 170, 380, 130, C["panel"], 245)
            g.frame(130, 170, 380, 130, (230, 70, 70), 3)
            g.text("k24", "Apagar a lápide de", W // 2, 188, C["text"], 255, "center")
            g.text("k24", "%s?" % (hist[self.msel].get("name") or "?"), W // 2, 220, (255, 110, 170), 255, "center")
            g.text("k16", "A sim, apagar      B nao", W // 2, 264, C["soft"], 255, "center")

    def draw_widget(self, g, x, y, w, h, t):
        """small live status card for the Bridge"""
        p = self.p
        g.rect(x, y, w, h, (14, 11, 40))
        g.rect(x, y + h - 34, w, 34, (34, 28, 78))
        g.rect(x, y + h - 34, w, 2, C["hullhi"])
        sts = [(x + 6 + (s[0] / W) * (w - 12), y + 4 + ((s[1] - 90) / 110.0) * (h - 60), 2, 2)
               for s in self.stars[:20] if (t * 2 + s[2] * 10) % 3 > 0.3]
        g.rects(sts, (180, 180, 230))
        form = p["form"]
        cx = x + w * 0.62
        base = y + h - 30
        if form == "egg":
            self.draw_pet(g, "egg", cx, base, t, scale=5)
            left = max(0.0, HATCH_AT - p["age"]) / 3600.0
            g.text("k16", "OVO", x + 8, y + 6, (255, 110, 170))
            g.text("k16", "nasce em %.0fh" % left if left >= 1 else "quase a nascer!", x + 8, y + 26, C["soft"])
            return
        sc = 4 if form in ("baby",) else 3
        old_hop = self.hop
        px, py, pw, ph = self.draw_pet(g, form, cx, base, t, self.mood(), scale=sc)
        self.hop = old_hop
        g.text("k16", p["name"] or "?", x + 8, y + 6, (255, 110, 170))
        g.text("k16", FORM_NAME[form], x + 8, y + 26, C["muted"])
        if p["sleeping"]:
            g.text("k16", "Zz", px + pw, py - 10, C["text"])
        if self.note:
            self.draw_bubble(g, t, px + pw - 4, py + 4, 0.6)
        bw = (w - 16 - 9) // 4
        for i, (v, col) in enumerate(((p["full"], C["orange"]), (p["happy"], (255, 110, 170)),
                                      (p["energy"], (255, 220, 90)), (p["hygiene"], (120, 200, 255)))):
            bx = x + 8 + i * (bw + 3)
            g.rect(bx, y + h - 12, bw, 6, C["deck"])
            low = v < 25 and int(t * 3) % 2 == 0
            g.rect(bx, y + h - 12, int(bw * v / 100.0), 6, (255, 70, 70) if low else col)

    def draw_game(self, g, t):
        gm = self.game
        g.clear((5, 4, 18))
        sts = [(s[0], (s[1] * 3 + t * 40 * (1 + s[2])) % 400, 2, 2) for s in self.stars]
        g.rects(sts, (180, 180, 230))
        g.rect(0, 0, W, 44, C["deck"])
        g.text("k24", "STAR CATCH", 12, 14, C["cyan"])
        g.text("k24", "%d" % gm["score"], W // 2, 14, (255, 220, 90), 255, "center")
        g.text("k24", "%02d" % max(0, math.ceil(gm["t"])) if not gm["over"] else "FIM", W - 12, 14, C["text"], 255,
               "right")
        g.rect(0, 380, W, 100, (34, 28, 78))
        g.rect(0, 380, W, 3, C["hullhi"])
        for it in gm["items"]:
            if it[3]:
                draw_grid(g, [".##.", "####", "####", ".##."], int(it[0] - 10), int(it[1] - 10), 5,
                          {"#": (230, 70, 60)})
                g.rect(it[0] - 3, it[1] - 30, 6, 16, (255, 140, 60), 140)
            else:
                draw_grid(g, STAR, int(it[0] - 14), int(it[1] - 12), 4, {"#": (255, 220, 90)})
        form = self.p["form"] if self.p["form"] != "egg" else "baby"
        self.hop = 0
        old_shake = self.shake
        self.shake = gm["hit"]
        self.draw_pet(g, form, gm["x"], 384, t, "happy" if not gm["hit"] else "sad", scale=4)
        self.shake = old_shake
        if gm["over"]:
            g.rect(140, 170, 360, 110, C["panel"], 240)
            g.frame(140, 170, 360, 110, C["cyan"], 3)
            g.text("k24", "APANHASTE %d" % gm["score"], W // 2, 196, (255, 220, 90), 255, "center")
            g.text("k16", "+humor  -energia", W // 2, 230, C["soft"], 255, "center")
        else:
            g.text("k16", "SETAS / ANALOGICO = MOVER   EVITA OS METEOROS", W // 2, 440, C["muted"], 255, "center")
