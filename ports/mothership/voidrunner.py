# VOID RUNNER - your music is the level. Pick a song: it is listened to first (songscan), then its loudness,
# hits and drops drive the horde, the power of your weapons and O GRAVE - a giant subwoofer from the void that
# pulses with the beat and pulls you in (gently far away, deadly close). Survive until the song ends and the
# GRAVE implodes. Drops bring a wave, a power boost and a chest.
# Design rules for speed on the R36S: every sprite is baked once into a texture (one RenderCopy per entity),
# the ground is a pre-rendered tile, hits use a spatial grid, nothing allocates much per frame.
import glob
import math
import os
import random
import time

import sdl2

import engine
import songscan
import vr_art as ART
from engine import C, W, H, SR, load_wav, Voice, SequenceVoice

SAVE = os.path.join(engine.APP, "vr_save.json")
VRD = os.path.join(engine.ASSETS, "vr")
LEVEL_TIME = 300.0           # SEM FIM: the world changes every 5 minutes
ROUT = 2000.0                # O GRAVE's reach: a huge zone of gentle pull, but not the whole map
FALL = 180.0                 # how fast the pull fades with distance (px): half strength 180 px from its edge
GEMS = [   # crystal colours: name, XP, runner level that unlocks it, palette (dark, bright, glow, core)
    ("VIOLETA", 1, 1, ((106, 31, 176), (178, 60, 255), (255, 60, 200), (255, 230, 255))),
    ("AZUL", 3, 5, ((20, 60, 150), (40, 140, 255), (90, 210, 255), (225, 245, 255))),
    ("VERDE", 8, 10, ((14, 96, 46), (40, 190, 90), (110, 255, 140), (225, 255, 230))),
    ("DOURADO", 20, 15, ((130, 80, 10), (225, 150, 30), (255, 214, 80), (255, 250, 220))),
    ("RUBI", 50, 21, ((120, 10, 30), (220, 30, 60), (255, 96, 116), (255, 228, 232))),
    ("PRISMA", 120, 28, ((90, 96, 130), (170, 186, 235), (236, 240, 255), (255, 255, 255))),
]
GEM_UP = [0.0, 0.15, 0.28, 0.28, 0.26, 0.24]   # chance of each step up the colours (a small foe, at unlock)
MOODS = os.path.join(engine.ASSETS, "moods")
CHEST = ["..KKKKKKKKKK..", ".KBBBBBBBBBBK.", "KBYYYYYYYYYYBK", "KBBBBBBBBBBBBK", "KKKKKKGGKKKKKK",
         "KBBBBBGWGBBBBK", "KBYYYYGGYYYYBK", "KBBBBBBBBBBBBK", ".KKKKKKKKKKKK."]
CHEST_PAL = {"K": (40, 20, 10), "B": (150, 84, 36), "Y": (255, 200, 70), "G": (255, 236, 140), "W": (255, 255, 255)}
S = 3                       # art pixel -> screen pixels
TILE = 80                   # ground tile in art pixels (240 px)

TYPES = {   # hp, speed, contact damage, xp, radius, mass fed to O GRAVE
    "mite": (4, 36, 4, 1, 10, 1), "skitter": (9, 52, 6, 2, 14, 2), "seer": (14, 26, 5, 3, 16, 3),
    "brood": (22, 20, 6, 3, 18, 4), "gorger": (60, 19, 10, 8, 22, 8),
    "spitter": (16, 30, 6, 3, 15, 3), "phantom": (11, 42, 8, 3, 13, 2), "bomber": (8, 50, 0, 2, 13, 2),
    "weaver": (18, 26, 6, 4, 18, 3), "warden": (44, 22, 10, 6, 19, 5),
}
AI = {"skitter", "seer", "brood", "gorger", "spitter", "phantom", "bomber", "weaver", "warden", "king", "matriarch"}
UNLOCK = {   # new enemy: (first level index, seconds into the level, weight); later levels bring them in sooner
    "bomber": (0, 100, 1), "spitter": (1, 70, 1), "phantom": (2, 90, 1), "weaver": (3, 100, 1), "warden": (4, 120, 1)}
WEAPON_IDS = ["bolt", "ring", "lance", "nova", "chain", "mine", "comet", "aura", "boomer", "drone", "frost", "beam"]
WEAPON_INFO = dict(zip(WEAPON_IDS, ART.WEAPONS))
SLOTS = 6                    # weapons and passives you can hold: choose a build
FX_COL = {"nova": (255, 255, 255), "boom": (255, 179, 71), "cboom": (255, 120, 80), "bblast": (255, 80, 60),
          "frost": (170, 230, 255), "white": (255, 255, 255)}
PASSIVES = {
    "speed": ("PROPULSORES", "+8% velocidade. Fugir é tudo.", (60, 242, 255)),
    "anchor": ("ÂNCORA", "-10% de puxão do Grave.", (178, 60, 255)),
    "magnet": ("ÍMAN", "+30% de alcance para apanhar cristais.", (92, 255, 138)),
    "vital": ("VITALIDADE", "+20 de vida máxima e cura total.", (255, 90, 110)),
    "armor": ("BLINDAGEM", "-12% de dano recebido.", (200, 200, 220)),
    "haste": ("RECARGA", "-7% de tempo de recarga das armas.", (255, 220, 90)),
    "dash": ("VOID DASH+", "-15% recarga do dash.", (120, 220, 255)),
    "crit": ("OLHO DE ÁGUIA", "+7% de golpes críticos (dano x2.5).", (255, 236, 140)),
    "area": ("AMPLIFICADOR", "+10% de área em todas as armas.", (255, 150, 60)),
    "regen": ("REGENERAÇÃO", "Recupera 0.5 de vida por segundo.", (120, 255, 160)),
    "wisdom": ("SABEDORIA", "+10% XP de cada cristal.", (180, 160, 255)),
}
MAXLV = 5
EVOS = {     # weapon at level 5 + this passive -> evolution card
    "bolt": ("haste", "TEMPESTADE", "5 raios perfurantes a ritmo frenetico."),
    "ring": ("magnet", "SATURNO", "Dois anéis de prismas em sentidos opostos."),
    "lance": ("speed", "RAIO SOLAR", "Lanças em cruz nas 4 direções."),
    "nova": ("armor", "SUPERNOVA", "Onda gigante que apaga os tiros inimigos."),
    "chain": ("dash", "TROVÃO", "Dois relâmpagos de 12 saltos."),
    "mine": ("anchor", "BURACO BRANCO", "Minas viram buracos brancos: sugam e explodem."),
    "comet": ("crit", "CHUVA DE METEOROS", "5 cometas pesados de cada vez."),
    "aura": ("regen", "SOL INTERIOR", "Aura enorme que te cura enquanto queima."),
    "boomer": ("wisdom", "ECLIPSE", "3 luas gigantes em todas as direções."),
    "drone": ("vital", "ENXAME DE LUZ", "5 sentinelas em fogo rapido."),
    "frost": ("area", "ZERO ABSOLUTO", "Congela tudo. Gelados levam +50% dano."),
    "beam": ("area", "HORIZONTE", "Dois lasers que varrem o ecrã inteiro."),
}


# ====================================================================== texture baking
def _surface(w, h):
    return sdl2.SDL_CreateRGBSurfaceWithFormat(0, w, h, 32, sdl2.SDL_PIXELFORMAT_ARGB8888)


def _to_tex(ren, surf):
    tex = sdl2.SDL_CreateTextureFromSurface(ren, surf)
    sdl2.SDL_FreeSurface(surf)
    sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
    return tex


def paint_grid(surf, grid, pal, s, ox=0, oy=0, white=False):
    """run-length FillRect of a char grid onto a surface"""
    fmt = surf.contents.format
    r = sdl2.SDL_Rect()
    for y, row in enumerate(grid):
        x, w = 0, len(row)
        while x < w:
            ch = row[x]
            col = pal.get(ch)
            if col is None:
                x += 1
                continue
            x2 = x
            while x2 + 1 < w and row[x2 + 1] == ch:
                x2 += 1
            c = (255, 255, 255) if white else col
            r.x, r.y, r.w, r.h = ox + x * s, oy + y * s, (x2 - x + 1) * s, s
            sdl2.SDL_FillRect(surf, r, sdl2.SDL_MapRGBA(fmt, c[0], c[1], c[2], 255))
            x = x2 + 1


def bake(ren, grid, pal, s=S, white=False, flip=False):
    if flip:
        grid = [row[::-1] for row in grid]
    w, h = len(grid[0]) * s, len(grid) * s
    surf = _surface(w, h)
    paint_grid(surf, grid, pal, s, white=white)
    return [_to_tex(ren, surf), w, h]


def bake_disc(ren, radius, layers):
    """layers: [(fraction_of_radius, (r,g,b,a))] painted outer -> inner (later layers overwrite)"""
    size = radius * 2
    surf = _surface(size, size)
    fmt = surf.contents.format
    r = sdl2.SDL_Rect()
    for frac, (cr, cg, cb, ca) in layers:
        rr = radius * frac
        col = sdl2.SDL_MapRGBA(fmt, cr, cg, cb, ca)
        for y in range(size):
            dy = y - radius + 0.5
            if abs(dy) > rr:
                continue
            half = int(math.sqrt(rr * rr - dy * dy))
            r.x, r.y, r.w, r.h = radius - half, y, half * 2, 1
            sdl2.SDL_FillRect(surf, r, col)
    return [_to_tex(ren, surf), size, size]


def bake_ring(ren, w, h, thick, col):
    """ellipse outline (the accretion disk)"""
    surf = _surface(w, h)
    fmt = surf.contents.format
    r = sdl2.SDL_Rect()
    c = sdl2.SDL_MapRGBA(fmt, col[0], col[1], col[2], 255)
    a, b = w / 2.0, h / 2.0
    for k in range(0, 720):
        t = k * math.pi / 360
        r.x, r.y, r.w, r.h = int(a + math.cos(t) * (a - thick)), int(b + math.sin(t) * (b - thick)), thick, thick
        sdl2.SDL_FillRect(surf, r, c)
    return [_to_tex(ren, surf), w, h]


def bake_ground(ren, biome, seed):
    """tileable, low-noise ground: 3 tones + rare void veins + a few decor sprites"""
    rng = random.Random(seed)
    L = 8
    lat = [[rng.random() for _ in range(L)] for _ in range(L)]
    lat2 = [[rng.random() for _ in range(L)] for _ in range(L)]
    step = TILE / float(L)

    def vn(x, y, g):
        fx, fy = x / step, y / step
        x0, y0 = int(fx), int(fy)
        tx, ty = fx - x0, fy - y0
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a = g[y0 % L][x0 % L] * (1 - tx) + g[y0 % L][(x0 + 1) % L] * tx
        b = g[(y0 + 1) % L][x0 % L] * (1 - tx) + g[(y0 + 1) % L][(x0 + 1) % L] * tx
        return a * (1 - ty) + b * ty
    tones = biome["ground"]
    maw = biome["id"] == "maw"
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    grid = []
    for y in range(TILE):
        row = []
        for x in range(TILE):
            n = vn(x, y, lat) + bayer[y % 4][x % 4] / 16.0 * 0.12
            ch = "1" if n < 0.48 else ("2" if n < 0.74 else "3")
            v = vn(x * 2 % TILE, y * 2 % TILE, lat2)
            if (maw or vn(x, y, lat2) > 0.72) and abs(v - 0.5) < 0.018:
                ch = "V"
            row.append(ch)
        grid.append("".join(row))
    pal = {"1": tones[0], "2": tones[1], "3": tones[2], "V": (86, 22, 130)}
    surf = _surface(TILE * S, TILE * S)
    paint_grid(surf, grid, pal, S)
    return [_to_tex(ren, surf), TILE * S, TILE * S]


# ====================================================================== entities
class Enemy(object):
    __slots__ = ("x", "y", "k", "hp", "spd", "dmg", "xp", "rad", "mass", "tex", "flash", "vx", "vy", "ring_t",
                 "boss", "t", "maxhp", "st", "cd", "ax", "ay", "slow", "slowk")

    def __init__(self, k, x, y, hp, spd, dmg, xp, rad, mass, tex, boss=False):
        self.k, self.x, self.y, self.hp, self.maxhp = k, x, y, hp, hp
        self.spd, self.dmg, self.xp, self.rad, self.mass, self.tex = spd, dmg, xp, rad, mass, tex
        self.flash = 0.0
        self.vx = self.vy = 0.0
        self.ring_t = 0.0
        self.boss = boss
        self.t = random.uniform(0, 3)
        self.st = ""                 # behaviour state: wind/dash, aim, fade/appear, armed, inhale, warp
        self.cd = random.uniform(0.8, 2.5)
        self.ax = self.ay = 0.0
        self.slow = 0.0
        self.slowk = 1.0


class Run(object):
    """one attempt at a level (or endless)"""

    def __init__(self, vr, level, song, timeline, endless=False):
        self.vr, self.app, self.level, self.endless = vr, vr.app, level, endless
        self.song, self.tl = song, timeline
        self.dur = max(20.0, timeline.dur) if not endless else 0.0
        self.mt = 0.0                      # time inside the song (the music clock)
        self.I = 0.4                       # music intensity 0..1 (smoothed)
        self.pulse = 0.0                   # beat pulse 0..1 (O GRAVE breathes and pulls harder)
        self.waves = []                    # sound rings leaving O GRAVE [t0, strength]
        self.boost_t = 0.0                 # after a drop: weapons hit harder
        self.charge = 0.0                  # 0..1 in the 2.5 s before a drop
        self.drops_hit = 0
        self.shake = 0.0
        self.chests = []                   # [x, y, kind 0 normal / 1 big]
        self.chest = None                  # the chest being opened
        self.xp_k = 1.0 if endless else max(1.0, min(2.5, 240.0 / self.dur))
        self.ren = vr.app.ren
        self.t = 0.0
        self.px, self.py = 0.0, 460.0
        self.fx_dir = 1.0
        self.dir = (0.0, -1.0)
        self.hx, self.hy, self.mass = 0.0, 0.0, 0.0
        self.R = 28.0
        self.hp = self.maxhp = 100.0
        self.inv = 0.0
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.weapons = {"bolt": 1}
        self.passive = {}
        self.evo = set()
        self.wt = dict((k, 0.5) for k in WEAPON_IDS)
        self.xp, self.lv, self.need = 0.0, 1, self.need_for(1)
        self.kills = 0
        self.enemies, self.shards, self.bullets, self.eshots, self.mines, self.fx = [], [], [], [], [], []
        self.missiles, self.boomers, self.whites, self.puddles, self.lobs = [], [], [], [], []
        self.pvx = self.pvy = 0.0          # external pushes on the runner (gorger inhale)
        self.slowed = False
        self.rerolls, self.banishes = 3, 2
        self.banned = set()
        self.seen_en = set(vr.save_d.get("seen_en", []))
        self.spawn_t = 1.0
        self.event_t = 35.0
        self.boss_spawned = False
        self.state = "play"
        self.end_t = 0.0
        self.banner = ("", 0.0, "")
        self.choices = []
        self.csel = 0
        self.snd_gap = {}
        self.moving = False
        self.anim = 0.0
        self.biome_i = level
        self.parts = [[random.uniform(0, math.tau), random.uniform(40, 260)] for _ in range(60)]
        self.lite = vr.cfg_lite()
        self.G = self.gravity()
        self.gd = 460.0
        self.why = ""
        self.grid = {}
        self.bake()
        self.say(song["title"][:30], ART.BIOMES[self.biome_i]["name"])
        self.music = None
        self.rumble = None
        self.start_music()

    # ---------------------------------------------------------------- assets
    def bake(self):
        self.free_level()
        b = ART.BIOMES[self.biome_i]
        pal = dict(ART.VOID)
        pal.update({"A": b["accent"], "B": b["accent2"]})
        self.tx = {}
        for k, e in ART.ENEMIES.items():
            self.tx[k] = bake(self.ren, e["grid"], pal)
            self.tx[k + "_w"] = bake(self.ren, e["grid"], pal, white=True)
        self.tx["king"] = bake(self.ren, ART.ENEMIES["gorger"]["grid"], pal, 6)
        self.tx["king_w"] = bake(self.ren, ART.ENEMIES["gorger"]["grid"], pal, 6, white=True)
        self.tx["matriarch"] = bake(self.ren, ART.BOSS["grid"], pal, 5)
        self.tx["matriarch_w"] = bake(self.ren, ART.BOSS["grid"], pal, 5, white=True)
        self.tx["shard"] = bake(self.ren, ART.SHARD, pal, 2)
        for i, (_, _, _, cols) in enumerate(GEMS):
            gp = dict(pal)
            gp.update(dict(zip("PMGE", cols)))
            self.tx["gem%d" % i] = bake(self.ren, ART.SHARD, gp, 2)
        self.tx["ground"] = bake_ground(self.ren, b, 1000 + self.biome_i)
        dpal = dict(pal)
        dpal.update(dict(zip("123", b["ground"])))
        self.decor = [bake(self.ren, d, dpal) for d in ART.DECOR[b["id"]]] + [bake(self.ren, ART.RIFT, dpal)]

    def free_level(self):
        for t in list(getattr(self, "tx", {}).values()) + getattr(self, "decor", []):
            sdl2.SDL_DestroyTexture(t[0])
        self.tx = {}
        self.decor = []

    def free(self):
        self.free_level()
        if self.music:
            self.music.fade(0.0, 0.6)
        if self.rumble:
            self.app.mixer.kill_key("vr_rumble")

    def start_music(self):
        """the song itself is the level's music (and its clock)"""
        m = self.app.mixer
        try:
            v = SequenceVoice(self.song["paths"], "vr")
            with m.lock:
                v.start = m.clock + int(0.6 * SR)
                m.streams.append(v)
            self.music = v
        except Exception:
            self.music = None

    def music_pause(self, p):
        if self.music and self.music.paused != p:
            self.music.paused = p

    def extend_endless(self):
        """SEM FIM: keep adding segments of the high-energy moods to the music and to the timeline"""
        v = self.music
        if not self.endless:
            return
        if not ((v is not None and v.idx >= len(v.paths) - 2) or self.mt > self.tl.dur - 20):
            return
        pool = self.song["pool"]
        last = self.song["paths"][-1]
        nxt = random.choice([p for p in pool if p != last] or pool)
        self.song["paths"].append(nxt)
        if v is not None and v.paths is not self.song["paths"]:
            v.paths.append(nxt)
        try:
            self.tl.add(songscan.scan_file(nxt))
        except Exception:
            pass

    def snd(self, k, gain=0.6, gap=0.04):
        now = time.time()
        if now - self.snd_gap.get(k, 0) < gap:
            return
        self.snd_gap[k] = now
        d = self.vr.snd.get(k)
        if d:
            self.app.mixer.shot("vr_" + k, d, group="vr", gain=gain, choke=False)

    def say(self, s, sub=""):
        self.banner = (s, time.time(), sub)

    # ---------------------------------------------------------------- stats
    def lvl(self, k):
        return self.passive.get(k, 0)

    def speed(self):
        return 85.0 * (1 + 0.08 * self.lvl("speed"))

    def magnet(self):
        return 55.0 * (1 + 0.3 * self.lvl("magnet"))

    def cd(self, base):
        """weapon cooldown: haste, and the music - louder music fires faster, a drop even more"""
        k = (0.88 + 0.3 * self.I) * (1.25 if self.boost_t > 0 else 1.0)
        return base * (1 - 0.07 * self.lvl("haste")) / k

    def power(self):
        return (0.8 + 0.5 * self.I) * (1.5 if self.boost_t > 0 else 1.0)

    def prog(self):
        if self.endless:
            return min(1.0, (self.mt % LEVEL_TIME) / LEVEL_TIME)
        return min(1.0, self.mt / self.dur)

    def tier(self):
        return int(self.mt // LEVEL_TIME) if self.endless else self.level

    def area(self):
        return 1 + 0.1 * self.lvl("area")

    def gravity(self):
        """O GRAVE's pull right at its edge (px/s). A progression: a whisper when the song starts, growing with
        it; the world raises the ceiling and loud parts add a little. Under your speed (85) for most of a
        song: only the end of the hardest worlds pulls about as fast as you run."""
        tier = self.tier()
        top = 52.0 + 6.0 * tier + (4.0 * tier if self.endless else 0.0)
        return top * (0.32 + 0.68 * self.prog() ** 1.25) * (0.9 + 0.2 * self.I)

    def pull(self, x, y, k=1.0):
        """velocity added by O GRAVE at (x, y): a huge, soft field - full strength at its edge, half 180 px
        away, a light current far out, fading to nothing at its reach (ROUT). Beats pull a little harder."""
        dx, dy = self.hx - x, self.hy - y
        d = math.sqrt(dx * dx + dy * dy) + 0.01
        if d >= ROUT:
            return 0.0, 0.0, d
        e = max(0.0, d - self.R)
        s = e / (ROUT - self.R)
        p = self.G * k * (1.0 + 0.2 * self.pulse) * (1.0 - s * s) / (1.0 + e / FALL) / d
        return dx * p - dy * p * 0.2, dy * p + dx * p * 0.2, d

    # weapon geometry, shared by update and draw
    def ring_specs(self, lv, ev):
        return [(6, 70, 3.0), (6, 108, -2.2)] if ev else [(1 + lv, 56 + 4 * lv, 3.0)]

    def beam_angles(self, ev):
        a = self.t * (1.6 if ev else 1.9)
        return [a, a + math.pi] if ev else [a]

    def beam_len(self, lv, ev):
        return (330 if ev else 150 + 18 * lv) * self.area()

    def aura_r(self, lv, ev):
        return (150 if ev else 48 + 9 * lv) * self.area()

    def drone_pos(self, lv, ev):
        n = 5 if ev else 1 + (lv >= 3) + (lv >= 5)
        a0 = -self.t * 1.6
        return [(self.px + math.cos(a0 + i * math.tau / n) * 78, self.py + math.sin(a0 + i * math.tau / n) * 78)
                for i in range(n)]

    # ---------------------------------------------------------------- spawning
    def scale_hp(self):
        return (1 + 0.07 * self.tier()) * (1 + 0.9 * self.prog()) * (0.85 + 0.3 * self.I) * (1.3 if self.endless else 1.0)

    def spawn(self, k, x, y, boss=None):
        hp, spd, dmg, xp, rad, mass = TYPES[k]
        if boss == "king":
            e = Enemy(k, x, y, 600 * (1 + 0.5 * self.level), 22, 20, 40, 44, 0, self.tx["king"], True)
        elif boss == "matriarch":
            e = Enemy(k, x, y, 2600, 18, 25, 80, 56, 0, self.tx["matriarch"], True)
        else:
            e = Enemy(k, x, y, hp * self.scale_hp(), spd, dmg, xp, rad, mass, self.tx[k])
            if k not in self.seen_en and k != "mite":
                self.seen_en.add(k)
                self.vr.save_d["seen_en"] = sorted(self.seen_en)
                self.vr.write(sync=False)          # mid-run: never stall a frame on the SD card
                self.say("NOVO: " + ART.ENEMIES[k]["name"], ART.ENEMIES[k]["desc"])
        e.k = boss or k
        self.enemies.append(e)
        return e

    def ring_pos(self, r, a=None):
        a = random.uniform(0, math.tau) if a is None else a
        return self.px + math.cos(a) * r, self.py + math.sin(a) * r

    def update_spawns(self, dt):
        """the music drives the horde: louder = more and faster spawns; how far into the song = which enemies"""
        p, I, tier = self.prog(), self.I, self.tier()
        cap = 70 if self.lite else 130
        self.spawn_t -= dt
        if self.spawn_t <= 0 and len(self.enemies) < cap:
            self.spawn_t = max(0.2, 1.15 - 0.75 * I - 0.25 * p) / (1 + 0.07 * tier)
            pool = ["mite"] * 6 + (["skitter"] * 2 if p > 0.1 else []) + (["seer"] if p > 0.25 else []) + \
                (["brood"] if p > 0.4 else []) + (["gorger"] if p > 0.57 else [])
            for k, (lv0, gate, w) in UNLOCK.items():
                if tier >= lv0 and p > max(0.1, (gate - 10 * (tier - lv0)) / LEVEL_TIME):
                    pool += [k] * w
            for _ in range(1 + int(2.5 * I * (0.4 + p))):
                x, y = self.ring_pos(random.uniform(360, 420))
                if (x - self.hx) ** 2 + (y - self.hy) ** 2 > (self.R + 60) ** 2:
                    self.spawn(random.choice(pool), x, y)
        # no drop in the song for a while: an event now and then anyway
        self.event_t -= dt
        if self.event_t <= 0:
            self.event_t = random.uniform(36, 52)
            self.event()
        if not self.boss_spawned and not self.endless:
            gate = 0.6 if self.dur < 120 else 0.76
            if p > gate:
                self.boss_spawned = True
                if self.level == 5:
                    self.spawn("gorger", *self.ring_pos(330), boss="matriarch")
                    self.say("A MATRIARCA DESPERTOU", "teias, ninhadas e bombas")
                else:
                    self.spawn("gorger", *self.ring_pos(330), boss="king")
                    self.say("REI DEVORADOR", "quando inspira, faz dash")
                self.snd("alarm", 0.8)

    def event(self, kind=None):
        """group events: a swarm, a charge, eyes, a wall of shots, an ambush"""
        p = self.prog()
        evs = ["enxame"]
        if p > 0.2:
            evs += ["investida", "olhos"]
        if p > 0.3 and self.tier() >= 1:
            evs.append("barragem")
        if p > 0.25 and self.tier() >= 2:
            evs.append("emboscada")
        ev = kind or random.choice(evs)
        self.snd("alarm", 0.6)
        if ev == "enxame":
            n = 14 + 2 * self.tier()
            for i in range(n):
                self.spawn("mite", *self.ring_pos(300, i * math.tau / n))
            return "ENXAME!"
        if ev == "investida":
            a = random.uniform(0, math.tau)
            ux, uy = math.cos(a), math.sin(a)
            for i in range(8):
                off = (i - 3.5) * 34
                e = self.spawn("skitter", self.px - ux * 380 - uy * off, self.py - uy * 380 + ux * off)
                e.vx, e.vy = ux * 120, uy * 120
            return "INVESTIDA!"
        if ev == "olhos":
            for i in range(6):
                self.spawn("seer", *self.ring_pos(270, i * math.tau / 6))
            return "OLHOS NO ESCURO"
        if ev == "barragem":
            a = random.uniform(0, math.tau)
            ux, uy = math.cos(a), math.sin(a)
            gap = random.randint(3, 11)
            for i in range(16):
                if gap <= i <= gap + 1:
                    continue
                off = (i - 7.5) * 26
                self.eshots.append([self.px - ux * 360 - uy * off, self.py - uy * 360 + ux * off, ux * 95, uy * 95, 7.5])
            return "BARRAGEM!"
        kind = "phantom" if self.tier() >= 2 else "skitter"
        for i in range(8):
            e = self.spawn(kind, *self.ring_pos(140, i * math.tau / 8 + 0.4))
            e.st, e.cd = "warp", 1.0
        return "EMBOSCADA!"

    # ---------------------------------------------------------------- the music
    def on_beat(self, strength):
        """a hit in the song: O GRAVE pumps (sound ring + harder pull), and on loud parts the horde surges"""
        self.pulse = max(self.pulse, 0.3 + 0.7 * strength)
        if len(self.waves) < 6:
            self.waves.append([self.t, strength])
        if self.I > 0.55 and strength > 0.5 and random.random() < 0.3 * self.I and len(self.enemies) < 120:
            a = random.uniform(0, math.tau)
            for i in range(1 + int(2 * self.I)):
                self.spawn("mite", *self.ring_pos(390, a + i * 0.25))

    def drop(self):
        """the drop: a wave, 8 s of power and a chest to grab"""
        self.drops_hit += 1
        self.boost_t = 8.0
        self.shake = 0.7
        self.pulse = 1.0
        name = self.event(random.choice(["enxame", "investida", "olhos"]))
        self.say("DROP!", "%s  ·  armas a 150%% durante 8 s" % name)
        self.snd("win", 0.6)
        hx, hy = self.px - self.hx, self.py - self.hy
        d = math.sqrt(hx * hx + hy * hy) + 0.01
        a = math.atan2(hy / d, hx / d) + random.uniform(-1.0, 1.0)
        self.chests.append([self.px + math.cos(a) * 200, self.py + math.sin(a) * 200, 0])

    # ---------------------------------------------------------------- combat helpers
    def build_grid(self):
        g = {}
        for e in self.enemies:
            g.setdefault((int(e.x) >> 6, int(e.y) >> 6), []).append(e)
        self.grid = g

    def near(self, x, y, r):
        out = []
        g = self.grid
        x0, x1, y0, y1 = int(x - r) >> 6, int(x + r) >> 6, int(y - r) >> 6, int(y + r) >> 6
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                lst = g.get((cx, cy))
                if lst:
                    for e in lst:
                        dx, dy = e.x - x, e.y - y
                        rr = r + e.rad
                        if dx * dx + dy * dy < rr * rr and e.hp > 0 and e.st != "warp":
                            out.append(e)
        return out

    def nearest(self, x, y, maxd, skip=()):
        best, bd = None, maxd * maxd
        for e in self.enemies:
            if e.hp <= 0 or e.st == "warp" or e in skip:
                continue
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < bd:
                best, bd = e, d
        return best

    def line_hit(self, x, y, ux, uy, length, wid, dmg):
        for e in self.enemies:
            if e.hp <= 0 or e.st == "warp":
                continue
            rx, ry = e.x - x, e.y - y
            along = rx * ux + ry * uy
            if 0 < along < length and abs(rx * uy - ry * ux) < wid + e.rad:
                self.hit(e, dmg)

    def shielded(self, e, x, y):
        """warden: is (x, y) on the shield side (the side facing the runner)?"""
        fx, fy = self.px - e.x, self.py - e.y
        rx, ry = x - e.x, y - e.y
        return (rx * fx + ry * fy) > 0.3 * math.sqrt((fx * fx + fy * fy) * (rx * rx + ry * ry)) + 0.01

    def blast(self, x, y, r, dmg):
        for e in self.near(x, y, r):
            self.hit(e, dmg)
        self.fx.append(("bblast", self.t, 0.35, x, y, r))
        self.snd("boom", 0.45, 0.05)

    def add_puddle(self, x, y, r, life, kind):
        if len(self.puddles) >= 28:
            self.puddles.pop(0)
        self.puddles.append([x, y, life, r, kind])

    def hit(self, e, dmg):
        if e.hp <= 0:
            return
        if e.slow > 0 and e.slowk < 0.05:
            dmg *= 1.5                                   # frozen enemies shatter
        dmg *= self.power()
        c = self.lvl("crit")
        if c and random.random() < 0.07 * c:
            dmg *= 2.5
            if len(self.fx) < 90:
                self.fx.append(("crit", self.t, 0.22, e.x, e.y))
        e.hp -= dmg
        e.flash = 0.08
        if e.hp <= 0:
            self.kill(e)
        else:
            self.snd("hit", 0.3, 0.05)

    def kill(self, e):
        self.kills += 1
        self.snd("pop", 0.35, 0.03)
        if random.random() < 0.012:
            self.shards.append([e.x, e.y, -1, 0])       # light orb: heals
        else:
            gt = self.gem_for(e)
            if len(self.shards) < 140:
                self.shards.append([e.x, e.y, GEMS[gt][1], gt])
            elif self.shards:
                self.shards[random.randrange(len(self.shards))][2] += GEMS[gt][1]
        if e.k == "brood":
            for i in range(3):
                self.spawn("mite", e.x + random.uniform(-12, 12), e.y + random.uniform(-12, 12))
        elif e.k == "bomber":                           # popped early: the blast only hurts the horde
            self.blast(e.x, e.y, 60, 26)
        if e.boss:
            self.say("DERROTADO!", "deixou um baú grande")
            top = self.gem_tiers() - 1
            for i in range(10):
                gt = max(0, top - (i % 3 == 2))
                self.shards.append([e.x + random.uniform(-40, 40), e.y + random.uniform(-40, 40), GEMS[gt][1], gt])
            self.chests.append([e.x, e.y, 1])
        elif e.k in ("gorger", "warden") and random.random() < 0.06 and len(self.chests) < 3:
            self.chests.append([e.x, e.y, 0])

    def hurt(self, dmg):
        if self.inv > 0 or self.dash_t > 0:
            return
        self.hp -= dmg * (1 - 0.12 * self.lvl("armor"))
        self.inv = 0.6
        self.snd("hurt", 0.6, 0.1)
        if self.hp <= 0:
            self.die("hp")

    def die(self, why):
        if self.state != "play":
            return
        self.state = "dead"
        self.end_t = time.time()
        self.why = why
        if self.music:
            self.music.fade(0.0, 2.5)
        self.snd("collapse" if why == "hole" else "hurt", 0.8)
        self.vr.record(self)

    # ---------------------------------------------------------------- level up
    @staticmethod
    def need_for(lv):
        """XP from level lv to lv + 1: grows faster than the crystals get richer, so levels come slower"""
        return int(5 + 3 * lv + 0.5 * lv * lv)

    def gem_tiers(self):
        """how many crystal colours this runner level has unlocked"""
        return sum(1 for gm in GEMS if self.lv >= gm[2])

    def gem_for(self, e):
        """the colour an enemy drops: one step up at a time, each step rarer; tougher foes, levels past the
        unlock and the 8 s after a music drop all make the rich colours more likely"""
        tier, top = 0, self.gem_tiers()
        k = math.sqrt(max(1, e.xp)) * (1.5 if self.boost_t > 0 else 1.0)
        for t in range(1, top):
            c = min(0.6, GEM_UP[t] * k * min(2.0, 1 + 0.06 * (self.lv - GEMS[t][2])))
            if random.random() >= c:
                break
            tier = t
        return tier

    def add_xp(self, v):
        self.xp += v * (1 + 0.1 * self.lvl("wisdom")) * self.xp_k
        if self.xp >= self.need and self.state == "play":
            self.xp -= self.need
            before = self.gem_tiers()
            self.lv += 1
            self.need = self.need_for(self.lv)
            if self.gem_tiers() > before:
                gm = GEMS[self.gem_tiers() - 1]
                self.say("CRISTAL %s!" % gm[0], "novo cristal: vale %d XP" % gm[1])
            self.offer()

    def evo_ready(self):
        return [("e", w) for w, ev in EVOS.items()
                if self.weapons.get(w, 0) >= MAXLV and w not in self.evo and self.lvl(ev[0]) > 0]

    def roll(self, keep=()):
        """3 cards: ready evolutions first, then a weighted draw that favours what you already own"""
        out = list(keep)
        for c in self.evo_ready():
            if c not in out and len(out) < 2:
                out.append(c)
        pool = []
        for k in WEAPON_IDS:
            lv = self.weapons.get(k, 0)
            c = ("w", k)
            if lv < MAXLV and (lv or len(self.weapons) < SLOTS) and c not in self.banned and c not in out:
                pool.append([c, 2.6 if lv else 1.0])
        for k in PASSIVES:
            lv = self.lvl(k)
            c = ("p", k)
            if lv < MAXLV and (lv or len(self.passive) < SLOTS) and c not in self.banned and c not in out:
                w = 2.6 if lv else 1.0
                if any(EVOS[x][0] == k for x in self.weapons if x not in self.evo):
                    w += 1.5                            # completes an evolution you are building
                pool.append([c, w])
        # when O GRAVE gets strong, make sure an escape option shows up
        if self.G > 0.65 * self.speed() and len(out) < 3:
            for i, (c, w) in enumerate(pool):
                if c == ("p", "speed"):
                    out.append(pool.pop(i)[0])
                    break
        while len(out) < 3 and pool:
            r = random.uniform(0, sum(w for _, w in pool))
            i = 0
            for i, (c, w) in enumerate(pool):
                r -= w
                if r <= 0:
                    break
            out.append(pool.pop(i)[0])
        self.choices = out[:3] or [("h", "heal")]

    def open_chest(self, kind):
        """like a level up you do not choose: upgrades what you have; evolutions first"""
        n = 3 if kind == 1 else (3 if random.random() < 0.2 else 1)
        items = []
        for _ in range(n):
            ev = self.evo_ready()
            if ev:
                w = ev[0][1]
                self.evo.add(w)
                items.append(("e", w, 0))
                continue
            ws = [k for k, lv in self.weapons.items() if lv < MAXLV]
            ps = [k for k, lv in self.passive.items() if lv < MAXLV]
            if ws:
                k = random.choice(ws)
                self.weapons[k] += 1
                items.append(("w", k, self.weapons[k]))
            elif ps:
                k = random.choice(ps)
                self.passive[k] += 1
                if k == "vital":
                    self.maxhp += 20
                items.append(("p", k, self.passive[k]))
            else:
                self.hp = self.maxhp
                items.append(("h", "heal", 0))
        self.chest = {"items": items, "t0": time.time(), "big": kind == 1}
        self.state = "chest"
        self.snd("lvlup", 0.7)

    def close_chest(self):
        if self.chest and time.time() - self.chest["t0"] > 0.4 * len(self.chest["items"]) + 0.3:
            self.chest = None
            self.state = "play"

    def offer(self):
        self.roll()
        self.csel = 0
        self.state = "levelup"
        self.snd("lvlup", 0.7)

    def reroll(self):
        if self.rerolls > 0:
            self.rerolls -= 1
            self.roll()
            self.csel = 0
            self.snd("ring", 0.5)

    def banish(self):
        c = self.choices[self.csel]
        if self.banishes > 0 and c[0] in ("w", "p"):
            self.banishes -= 1
            self.banned.add(c)
            self.roll([x for i, x in enumerate(self.choices) if i != self.csel])
            self.csel = min(len(self.choices) - 1, 2)
            self.snd("hurt", 0.35)

    def choose(self):
        kind, k = self.choices[self.csel]
        if kind == "e":
            self.evo.add(k)
            self.say(EVOS[k][1] + "!", "EVOLUCAO: " + EVOS[k][2])
            self.snd("win", 0.6)
        elif kind == "w":
            self.weapons[k] = self.weapons.get(k, 0) + 1
        elif kind == "p":
            self.passive[k] = self.lvl(k) + 1
            if k == "vital":
                self.maxhp += 20
                self.hp = self.maxhp
        else:
            self.hp = self.maxhp
        self.state = "play"
        if self.xp >= self.need:
            self.add_xp(0)

    # ---------------------------------------------------------------- update
    def update(self, dt):
        if self.state != "play" and self.rumble:
            self.rumble.gain = 0.0
        if self.state in ("levelup", "chest", "dead", "won"):
            return
        if self.state == "collapse":
            el = time.time() - self.end_t
            self.R = max(0.0, self.R * (1 - dt * 2.5))
            if el > 2.4:
                self.state = "won"
                self.vr.record(self)
                self.snd("win", 0.8)
            return
        self.t += dt
        # the music clock: the song's own position when there is audio, game time otherwise
        prev = self.mt
        m = self.music
        if m is not None and self.app.mixer.ok and not m.done:
            self.mt = max(self.mt, m.pos / float(SR))
        else:
            self.mt += dt
        self.extend_endless()
        self.I += (self.tl.I(self.mt) - self.I) * min(1.0, dt * 4.0)
        for o in self.tl.onsets(prev, self.mt):
            self.on_beat(o[1])
        nd = self.tl.next_drop(prev)
        if nd is not None and nd <= self.mt:
            self.drop()
        nd = self.tl.next_drop(self.mt)
        self.charge = max(0.0, 1.0 - (nd - self.mt) / 2.5) if nd is not None and nd - self.mt < 2.5 else 0.0
        self.pulse *= math.exp(-dt * 7.0)
        self.boost_t = max(0.0, self.boost_t - dt)
        self.shake = max(0.0, self.shake - dt)
        self.waves = [w for w in self.waves if self.t - w[0] < 0.9]
        self.G = self.gravity()
        inp = self.app.input
        # endless: the void changes the world every 5 minutes
        if self.endless and int(self.mt // LEVEL_TIME) % 6 != self.biome_i:
            self.biome_i = int(self.mt // LEVEL_TIME) % 6
            self.bake()
            for e in self.enemies:
                e.tex = self.tx[e.k] if e.k in self.tx else self.tx["gorger"]
            self.say("NOVO MUNDO: " + ART.BIOMES[self.biome_i]["name"])
        # O GRAVE grows with the song and what it swallows, and drifts after the runner (faster when loud)
        p = self.prog()
        self.R = min(190.0, 30 + 36 * p + math.sqrt(self.mass) * 1.5 + (self.mt // LEVEL_TIME) * 8 * self.endless)
        dx, dy = self.px - self.hx, self.py - self.hy
        d = math.sqrt(dx * dx + dy * dy) + 0.01
        # it creeps after you slowly (a progression too); left behind off screen, it catches up and keeps
        # swallowing the horde that chases you
        drift = ((2 + 12 * p + 5 * self.I) * (1 + 0.08 * self.tier()) + max(0.0, d - 600) * 0.08) * dt
        self.hx += dx / d * drift
        self.hy += dy / d * drift
        # player movement (goo and webs slow you down; the dash breaks free)
        mx = (1 if inp.down("right") else 0) - (1 if inp.down("left") else 0) + inp.axes["lx"]
        my = (1 if inp.down("down") else 0) - (1 if inp.down("up") else 0) + inp.axes["ly"]
        ml = math.sqrt(mx * mx + my * my)
        self.moving = ml > 0.15
        if self.moving:
            self.dir = (mx / ml, my / ml)
            mx, my = mx / max(1.0, ml), my / max(1.0, ml)
            if abs(mx) > 0.2:
                self.fx_dir = 1.0 if mx > 0 else -1.0
            self.anim += dt
        slowf = 1.0
        for p in self.puddles:
            if (p[0] - self.px) ** 2 + (p[1] - self.py) ** 2 < p[3] * p[3]:
                slowf = min(slowf, 0.5 if p[4] == "web" else 0.65)
        self.slowed = slowf < 1.0
        sp = self.speed() * slowf
        if self.dash_t > 0:
            self.dash_t -= dt
            sp = self.speed() * 3.2
            if not self.moving:
                mx, my = self.dir
        vx, vy = mx * sp + self.pvx, my * sp + self.pvy
        self.pvx = self.pvy = 0.0
        gx, gy, gd = self.pull(self.px, self.py, 1 - 0.1 * self.lvl("anchor"))
        self.px += (vx + gx) * dt
        self.py += (vy + gy) * dt
        self.gd = gd
        if gd < self.R + 6:
            self.die("hole")
            return
        for c in self.chests:
            if (c[0] - self.px) ** 2 + (c[1] - self.py) ** 2 < 28 * 28:
                self.chests.remove(c)
                self.open_chest(c[2])
                return
        self.inv = max(0.0, self.inv - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        rg = self.lvl("regen")
        if rg:
            self.hp = min(self.maxhp, self.hp + 0.5 * rg * dt)
        if self.rumble is None:
            d = self.vr.snd.get("rumble")
            if d:
                self.rumble = Voice("vr_rumble", "vr", d, None, True, 0.0, self.app.mixer.clock)
                self.app.mixer.add(self.rumble)
        if self.rumble:
            self.rumble.gain = max(0.0, min(1.2, 1.4 - (gd - self.R) / 360.0)) * 0.8
        # enemies
        self.update_spawns(dt)
        self.build_grid()
        px, py = self.px, self.py
        alive = []
        for e in self.enemies:
            if e.hp <= 0:
                continue
            e.flash -= dt
            e.t += dt
            dx, dy = px - e.x, py - e.y
            d = math.sqrt(dx * dx + dy * dy) + 0.01
            spd = e.spd
            if e.slow > 0:
                e.slow -= dt
                spd *= e.slowk
            if e.st == "warp":                      # ambush: a marker first, the body a second later
                e.cd -= dt
                if e.cd <= 0:
                    e.st, e.cd = "", random.uniform(1.0, 2.0)
                alive.append(e)
                continue
            if e.vx or e.vy:
                k = e.slowk if e.slow > 0 else 1.0
                e.x += e.vx * dt * k
                e.y += e.vy * dt * k
                if d > 700:
                    continue
            elif e.k in AI:
                if self.ai(e, dt, dx, dy, d, spd):
                    continue
            else:
                e.x += dx / d * spd * dt
                e.y += dy / d * spd * dt
            if not e.boss:
                gx, gy, gd2 = self.pull(e.x, e.y, 1.7)    # the horde is lighter than you: it feeds O GRAVE
                e.x += gx * dt
                e.y += gy * dt
                if gd2 < self.R:
                    self.mass += e.mass
                    continue
            if d < e.rad + 10 and e.dmg and e.st not in ("fade", "appear"):
                self.hurt(e.dmg)
            if d < 900:
                alive.append(e)
        self.enemies = [e for e in alive if e.hp > 0]
        # enemy shots
        keep = []
        for s in self.eshots:
            gx, gy, _ = self.pull(s[0], s[1], 0.5)
            s[0] += (s[2] + gx) * dt
            s[1] += (s[3] + gy) * dt
            s[4] -= dt
            if (s[0] - px) ** 2 + (s[1] - py) ** 2 < 144:
                self.hurt(5)
                continue
            if s[4] > 0:
                keep.append(s)
        self.eshots = keep
        # web lobs land as sticky puddles; puddles fade
        keep = []
        for L in self.lobs:
            L[4] += dt
            if L[4] >= L[5]:
                self.add_puddle(L[2], L[3], 46, 6.0, "web")
                continue
            keep.append(L)
        self.lobs = keep
        for p in self.puddles:
            p[2] -= dt
        self.puddles = [p for p in self.puddles if p[2] > 0]
        self.update_weapons(dt)
        # xp shards: pulled by the hole too
        keep = []
        mg = self.magnet()
        for s in self.shards:
            dx, dy = px - s[0], py - s[1]
            d = math.sqrt(dx * dx + dy * dy) + 0.01
            if d < 14:
                if s[2] < 0:
                    self.hp = min(self.maxhp, self.hp + 30)
                    self.snd("lvlup", 0.4)
                else:
                    self.add_xp(s[2])
                    self.snd("xp", 0.25, 0.03)
                continue
            if d < mg:
                s[0] += dx / d * 300 * dt
                s[1] += dy / d * 300 * dt
            else:
                gx, gy, gd2 = self.pull(s[0], s[1], 0.5)
                s[0] += gx * dt
                s[1] += gy * dt
                if gd2 < self.R:
                    self.mass += 0.5 + 0.5 * s[3]
                    continue
            keep.append(s)
        self.shards = keep
        for p in self.parts:
            p[1] -= (40 + self.G) * dt
            p[0] += dt * (2.2 + 120 / (p[1] + 20))
            if p[1] < self.R:
                p[1] = self.R + random.uniform(120, 280)
        self.fx = [f for f in self.fx if self.t - f[1] < f[2]]
        song_over = (m is not None and m.done) or self.mt >= self.dur
        if not self.endless and song_over:
            self.state = "collapse"
            self.end_t = time.time()
            self.snd("collapse", 0.9)
            self.say("O GRAVE IMPLODIU!")
            for e in self.enemies:
                self.kills += 1
            self.enemies = []
            self.eshots = []
            self.lobs = []

    def ai(self, e, dt, dx, dy, d, spd):
        """per-type behaviour; every attack has a readable wind-up. Returns True when the enemy is gone."""
        k = e.k
        ux, uy = dx / d, dy / d
        if k == "skitter":                                  # stops, aims (red line), then dashes
            if e.st == "wind":
                e.cd -= dt
                if e.cd <= 0:
                    e.st, e.cd = "dash", 0.42
            elif e.st == "dash":
                e.cd -= dt
                f = 290 * dt * (e.slowk if e.slow > 0 else 1.0)
                e.x += e.ax * f
                e.y += e.ay * f
                if e.cd <= 0:
                    e.st, e.cd = "", random.uniform(2.2, 3.2)
            else:
                e.cd -= dt
                e.x += ux * spd * dt
                e.y += uy * spd * dt
                if e.cd <= 0 and d < 230:
                    e.st, e.cd, e.ax, e.ay = "wind", 0.55, ux, uy
        elif k == "seer":                                   # keeps its distance, 3-orb spread
            if d < 170:
                e.x -= ux * spd * dt
                e.y -= uy * spd * dt
            elif d > 240:
                e.x += ux * spd * dt
                e.y += uy * spd * dt
            else:
                e.x -= uy * spd * 0.6 * dt
                e.y += ux * spd * 0.6 * dt
            if e.t > 4.0:
                e.t = 0
                base = math.atan2(dy, dx)
                for j in ((-1, 0, 1) if self.level or self.endless else (0,)):      # level 1: a single orb
                    a = base + j * 0.26
                    self.eshots.append([e.x, e.y, math.cos(a) * 90, math.sin(a) * 90, 5.0])
        elif k == "brood":                                  # leaves a trail of goo
            e.x += ux * spd * dt
            e.y += uy * spd * dt
            e.cd -= dt
            if e.cd <= 0:
                e.cd = 3.0
                self.add_puddle(e.x, e.y, 26, 5.0, "goo")
        elif k in ("gorger", "king"):                       # inhales: pulls the runner to its mouth
            big = k == "king"
            if e.st == "inhale":
                e.cd -= dt
                if d < (360 if big else 280):
                    f = 80 if big else 55
                    self.pvx -= ux * f
                    self.pvy -= uy * f
                if e.cd <= 0:
                    e.st, e.cd = "", 6.0 if big else 6.5
            else:
                e.x += ux * spd * dt
                e.y += uy * spd * dt
                e.cd -= dt
                if e.cd <= 0 and d < (340 if big else 250):
                    e.st, e.cd = "inhale", 2.0 if big else 1.5
            if big and e.t > 4.5:
                e.t = 0
                for i in range(10):
                    a = i * math.tau / 10 + random.uniform(0, 0.6)
                    self.eshots.append([e.x, e.y, math.cos(a) * 75, math.sin(a) * 75, 6.0])
        elif k == "spitter":                                # plants, swells, 5-orb fan
            if e.st == "aim":
                e.cd -= dt
                if e.cd <= 0:
                    base = math.atan2(dy, dx)
                    for j in range(5):
                        a = base + (j - 2) * 0.26
                        self.eshots.append([e.x, e.y, math.cos(a) * 85, math.sin(a) * 85, 5.0])
                    e.st, e.cd = "", 4.4
            else:
                e.cd -= dt
                if d > 230:
                    e.x += ux * spd * dt
                    e.y += uy * spd * dt
                elif d < 160:
                    e.x -= ux * spd * 0.6 * dt
                    e.y -= uy * spd * 0.6 * dt
                if e.cd <= 0 and d < 300:
                    e.st, e.cd = "aim", 0.8
        elif k == "phantom":                                # fades out, reappears on your path
            if e.st == "fade":
                e.cd -= dt
                if e.cd <= 0:
                    e.x, e.y = e.ax, e.ay
                    e.st, e.cd = "appear", 0.35
            elif e.st == "appear":
                e.cd -= dt
                if e.cd <= 0:
                    e.st, e.cd = "", random.uniform(2.8, 4.0)
            else:
                e.x += ux * spd * dt
                e.y += uy * spd * dt
                e.cd -= dt
                if e.cd <= 0 and d < 330:
                    if self.moving:
                        tx, ty = self.px + self.dir[0] * 95, self.py + self.dir[1] * 95
                    else:
                        tx, ty = self.ring_pos(85)
                    e.st, e.cd, e.ax, e.ay = "fade", 0.5, tx, ty
        elif k == "bomber":                                 # arms next to you, then explodes
            if e.st == "armed":
                e.cd -= dt
                e.x += ux * spd * 0.3 * dt
                e.y += uy * spd * 0.3 * dt
                if e.cd <= 0:
                    e.st, e.hp = "boom", 0
                    self.blast(e.x, e.y, 74, 30)
                    if d < 74:
                        self.hurt(16)
                    return True
            else:
                e.x += ux * spd * dt
                e.y += uy * spd * dt
                if d < 48:
                    e.st, e.cd = "armed", 0.9
        elif k == "weaver":                                 # lobs webs where you are going
            if d < 180:
                e.x -= ux * spd * dt
                e.y -= uy * spd * dt
            elif d > 260:
                e.x += ux * spd * dt
                e.y += uy * spd * dt
            else:
                e.x += uy * spd * 0.6 * dt
                e.y -= ux * spd * 0.6 * dt
            if e.t > 4.6 and d < 340:
                e.t = 0
                lead = self.speed() * 0.7 if self.moving else 0.0
                self.lobs.append([e.x, e.y, self.px + self.dir[0] * lead, self.py + self.dir[1] * lead, 0.0, 0.9])
        elif k == "matriarch":
            e.x += ux * spd * dt
            e.y += uy * spd * dt
            if e.t > 4.0:
                e.t = 0
                e.ax += 1
                if int(e.ax) % 2:
                    for i in range(12):
                        a = i * math.tau / 12
                        self.eshots.append([e.x, e.y, math.cos(a) * 80, math.sin(a) * 80, 6.0])
                    for i in range(2):
                        self.spawn("brood", e.x + random.uniform(-60, 60), e.y + random.uniform(-60, 60))
                else:
                    for i in range(3):
                        tx, ty = self.ring_pos(random.uniform(0, 90))
                        self.lobs.append([e.x, e.y, tx, ty, 0.0, 1.1])
                    for i in range(2):
                        self.spawn("bomber", e.x + random.uniform(-50, 50), e.y + random.uniform(-50, 50))
        else:                                               # warden: slow and steady behind its shield
            e.x += ux * spd * dt
            e.y += uy * spd * dt
        return False

    def update_weapons(self, dt):
        px, py = self.px, self.py
        now = self.t
        A = self.area()
        for k, lv in self.weapons.items():
            ev = k in self.evo
            self.wt[k] -= dt
            if k == "ring":
                dmg = 16 if ev else 5 + 2 * lv
                for n, rad, spin in self.ring_specs(lv, ev):
                    a0 = now * spin
                    for i in range(n):
                        a = a0 + i * math.tau / n
                        for e in self.near(px + math.cos(a) * rad, py + math.sin(a) * rad, 12 * A):
                            if now - e.ring_t > 0.35:
                                e.ring_t = now
                                self.hit(e, dmg)
                continue
            if self.wt[k] > 0:
                continue
            if k == "bolt":
                if ev:
                    self.wt[k] = self.cd(0.38)
                    n, spread, dmg, pierce, kind = 5, 0.2, 18, 3, 2
                else:
                    self.wt[k] = self.cd(0.85 - 0.07 * lv)
                    n, spread, dmg, pierce, kind = 1 + lv // 2, 0.18, 6 + 2 * lv, 1 + (lv == MAXLV), 0
                tgt = self.nearest(px, py, 360)
                if tgt:
                    base = math.atan2(tgt.y - py, tgt.x - px)
                    for i in range(n):
                        a = base + (i - (n - 1) / 2.0) * spread
                        self.bullets.append([px, py, math.cos(a) * 280, math.sin(a) * 280, dmg, pierce, 1.4, kind,
                                             None])
                    self.snd("bolt", 0.35, 0.06)
            elif k == "lance":
                base = math.atan2(self.dir[1], self.dir[0])
                if ev:
                    self.wt[k] = self.cd(1.4)
                    wid, dmg, dirs = 24 * A, 50, [base + j * math.pi / 2 for j in range(4)]
                else:
                    self.wt[k] = self.cd(2.6 - 0.2 * lv)
                    wid, dmg, dirs = (14 + 2 * lv) * A, 14 + 5 * lv, [base]
                for a in dirs:
                    ux, uy = math.cos(a), math.sin(a)
                    self.line_hit(px, py, ux, uy, 420, wid, dmg)
                    self.fx.append(("lance", now, 0.18, px, py, ux, uy, wid))
                self.snd("zap", 0.4)
            elif k == "nova":
                if ev:
                    self.wt[k] = self.cd(2.4)
                    r, dmg, push = 230 * A, 40, 100
                else:
                    self.wt[k] = self.cd(3.5 - 0.25 * lv)
                    r, dmg, push = (90 + 15 * lv) * A, 8 + 3 * lv, 60
                for e in self.near(px, py, r):
                    self.hit(e, dmg)
                    if not e.boss:
                        dx, dy = e.x - px, e.y - py
                        d = math.sqrt(dx * dx + dy * dy) + 0.01
                        e.x += dx / d * push
                        e.y += dy / d * push
                if ev:                                      # supernova wipes enemy shots and shields you
                    self.eshots = [s for s in self.eshots if (s[0] - px) ** 2 + (s[1] - py) ** 2 > r * r]
                    self.inv = max(self.inv, 0.4)
                self.fx.append(("nova", now, 0.45 if ev else 0.3, px, py, r))
                self.snd("boom", 0.4)
            elif k == "chain":
                if ev:
                    self.wt[k] = self.cd(0.9)
                    jumps, dmg, r0, rj, chains = 12, 30, 220, 140, 2
                else:
                    self.wt[k] = self.cd(1.8 - 0.15 * lv)
                    jumps, dmg, r0, rj, chains = 2 + lv, 8 + 3 * lv, 170, 100 * A, 1
                done = set()
                for c in range(chains):
                    cur = self.nearest(px, py, r0, done)
                    lx, ly = px, py
                    pts = []
                    for j in range(jumps):
                        if not cur:
                            break
                        pts.append((lx, ly, cur.x, cur.y))
                        done.add(cur)
                        self.hit(cur, dmg)
                        lx, ly = cur.x, cur.y
                        cur = self.nearest(lx, ly, rj, done)
                    if pts:
                        self.fx.append(("chain", now, 0.14, pts, ev))
                if done:
                    self.snd("zap", 0.35)
            elif k == "mine":
                self.wt[k] = self.cd(1.4 if ev else 2.2 - 0.2 * lv)
                if len(self.mines) < (8 if ev else 3 + lv):
                    self.mines.append([px, py, 12.0])
            elif k == "comet":
                if ev:
                    self.wt[k] = self.cd(1.3)
                    n, dmg, r = 5, 35, 60 * A
                else:
                    self.wt[k] = self.cd(2.3 - 0.15 * lv)
                    n, dmg, r = 1 + lv // 2, 10 + 4 * lv, (34 + 4 * lv) * A
                base = math.atan2(self.dir[1], self.dir[0])
                for i in range(n):
                    self.missiles.append([px, py, base + (i - (n - 1) / 2.0) * 0.7, dmg, 3.0, None, r])
                self.snd("dash", 0.25, 0.08)
            elif k == "aura":
                self.wt[k] = 0.4 if ev else 0.5
                hits = self.near(px, py, self.aura_r(lv, ev))
                for e in hits:
                    self.hit(e, 14 if ev else 3 + 1.5 * lv)
                if ev and hits:
                    self.hp = min(self.maxhp, self.hp + min(3.0, 0.2 * len(hits)))
            elif k == "boomer":
                if ev:
                    self.wt[k] = self.cd(1.6)
                    n, dmg, rad = 3, 30, 22 * A
                else:
                    self.wt[k] = self.cd(2.4 - 0.15 * lv)
                    n, dmg, rad = 1 + (lv >= 4), 12 + 4 * lv, 14 * A
                base = math.atan2(self.dir[1], self.dir[0])
                for i in range(n):
                    a = base + (i * math.tau / 3 if ev else (i - (n - 1) / 2.0) * 0.5)
                    self.boomers.append([px, py, math.cos(a) * 420, math.sin(a) * 420, 0.0, dmg, set(), rad, False])
                self.snd("ring", 0.3, 0.1)
            elif k == "drone":
                self.wt[k] = self.cd(0.5 if ev else 1.25 - 0.1 * lv)
                dmg = 14 if ev else 5 + 2 * lv
                fired = False
                for x, y in self.drone_pos(lv, ev):
                    tgt = self.nearest(x, y, 320)
                    if tgt:
                        a = math.atan2(tgt.y - y, tgt.x - x)
                        self.bullets.append([x, y, math.cos(a) * 300, math.sin(a) * 300, dmg, 1, 1.2, 1, None])
                        fired = True
                if fired:
                    self.snd("bolt", 0.18, 0.08)
            elif k == "frost":
                if ev:
                    self.wt[k] = self.cd(3.0)
                    r, dmg, dur, sk = 230 * A, 20, 2.2, 0.0
                else:
                    self.wt[k] = self.cd(4.2 - 0.3 * lv)
                    r, dmg, dur, sk = (100 + 12 * lv) * A, 4 + 2 * lv, 2.5, 0.45
                for e in self.near(px, py, r):
                    self.hit(e, dmg)
                    e.slow = max(e.slow, dur)
                    e.slowk = 0.7 if e.boss else sk
                self.fx.append(("frost", now, 0.35, px, py, r))
                self.snd("zap", 0.3)
            elif k == "beam":
                self.wt[k] = 0.15 if ev else 0.25
                L = self.beam_len(lv, ev)
                dmg = 13 if ev else 4 + 2 * lv
                for a in self.beam_angles(ev):
                    self.line_hit(px, py, math.cos(a), math.sin(a), L, 9 * A, dmg)
        # bullets (bolt, drone, storm); the warden's shield eats the ones that come from the front
        keep = []
        for b in self.bullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[6] -= dt
            if b[6] <= 0:
                continue
            tgt = None
            for e in self.near(b[0], b[1], 4):
                if e is not b[8]:
                    tgt = e
                    break
            if tgt:
                if tgt.k == "warden" and self.shielded(tgt, b[0], b[1]):
                    self.fx.append(("block", now, 0.2, b[0], b[1]))
                    self.snd("hit", 0.25, 0.08)
                    continue
                self.hit(tgt, b[4])
                b[8] = tgt
                b[5] -= 1
                if b[5] <= 0:
                    continue
            keep.append(b)
        self.bullets = keep
        # homing comets: explode on contact (area: shields do not help)
        keep = []
        for m in self.missiles:
            m[4] -= dt
            if m[4] <= 0:
                continue
            tg = m[5]
            if tg is None or tg.hp <= 0:
                tg = m[5] = self.nearest(m[0], m[1], 420)
            if tg:
                diff = (math.atan2(tg.y - m[1], tg.x - m[0]) - m[2] + math.pi) % math.tau - math.pi
                m[2] += max(-4.5 * dt, min(4.5 * dt, diff))
            m[0] += math.cos(m[2]) * 220 * dt
            m[1] += math.sin(m[2]) * 220 * dt
            if self.near(m[0], m[1], 5):
                for e in self.near(m[0], m[1], m[6]):
                    self.hit(e, m[3])
                self.fx.append(("cboom", now, 0.3, m[0], m[1], m[6]))
                self.snd("boom", 0.3, 0.06)
                continue
            keep.append(m)
        self.missiles = keep
        # crescents: fly out, slow down, come back through the horde
        keep = []
        for b in self.boomers:
            b[4] += dt
            if b[4] < 0.55:
                f = 1 - 1.6 * dt
                b[2] *= f
                b[3] *= f
            else:
                if not b[8]:
                    b[8] = True
                    b[6].clear()
                dx, dy = px - b[0], py - b[1]
                dl = math.sqrt(dx * dx + dy * dy) + 0.01
                if dl < 18 or b[4] > 3.0:
                    continue
                b[2], b[3] = dx / dl * 380, dy / dl * 380
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            for e in self.near(b[0], b[1], b[7]):
                if e not in b[6]:
                    b[6].add(e)
                    if e.k == "warden" and self.shielded(e, b[0], b[1]):
                        self.fx.append(("block", now, 0.2, b[0], b[1]))
                    else:
                        self.hit(e, b[5])
            keep.append(b)
        self.boomers = keep
        # mines (evolved: white holes that suck the horde in, then burst)
        keep = []
        lv = self.weapons.get("mine", 1)
        ev = "mine" in self.evo
        for m in self.mines:
            m[2] -= dt
            if self.near(m[0], m[1], 10) or m[2] <= 0:
                if ev:
                    self.whites.append([m[0], m[1], 1.1])
                else:
                    r = (50 + 6 * lv) * A
                    for e in self.near(m[0], m[1], r):
                        self.hit(e, 18 + 6 * lv)
                    self.fx.append(("boom", now, 0.3, m[0], m[1], r))
                    self.snd("boom", 0.45, 0.05)
                continue
            keep.append(m)
        self.mines = keep
        keep = []
        for w in self.whites:
            w[2] -= dt
            for e in self.near(w[0], w[1], 150 * A):
                if not e.boss:
                    dx, dy = w[0] - e.x, w[1] - e.y
                    d = math.sqrt(dx * dx + dy * dy) + 0.01
                    e.x += dx / d * min(d, 170 * dt)
                    e.y += dy / d * min(d, 170 * dt)
            if w[2] <= 0:
                for e in self.near(w[0], w[1], 130 * A):
                    self.hit(e, 70)
                self.fx.append(("white", now, 0.4, w[0], w[1], 130 * A))
                self.snd("boom", 0.5, 0.05)
                continue
            keep.append(w)
        self.whites = keep

    # ---------------------------------------------------------------- input
    def on(self, kind, b):
        if self.state == "levelup":
            if kind in ("press", "repeat") and b in ("left", "right"):
                self.csel = (self.csel + (1 if b == "right" else -1)) % len(self.choices)
                self.app.ui_move()
            elif kind == "press" and b == "a":
                self.choose()
            elif kind == "press" and b == "y":
                self.reroll()
            elif kind == "press" and b == "x":
                self.banish()
            return
        if self.state == "play" and kind == "press" and b in ("a", "b") and self.dash_cd <= 0:
            self.dash_t = 0.18
            self.dash_cd = 4.0 * (1 - 0.15 * self.lvl("dash"))
            self.snd("dash", 0.5)

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t):
        ren = self.ren
        cx, cy = self.px - W / 2, self.py - H / 2
        if self.shake > 0:
            cx += random.uniform(-6, 6) * self.shake
            cy += random.uniform(-6, 6) * self.shake
        dst = sdl2.SDL_Rect()

        def put(tx, x, y, w=None, h=None):
            dst.x, dst.y = int(x), int(y)
            dst.w, dst.h = int(w or tx[1]), int(h or tx[2])
            sdl2.SDL_RenderCopy(ren, tx[0], None, dst)

        def dots(x, y, r, n, col, a=255, sz=6, rot=0.0):
            h = sz / 2.0
            g.rects([(x + math.cos(rot + i * math.tau / n) * r - h, y + math.sin(rot + i * math.tau / n) * r - h,
                      sz, sz) for i in range(n)], col, a)
        # ground (tiled)
        gt = self.tx["ground"]
        ts = gt[1]
        ox, oy = -int(cx % ts), -int(cy % ts)
        for yy in range(oy, H, ts):
            for xx in range(ox, W, ts):
                put(gt, xx, yy)
        # sparse decor: one deterministic pick per 200px world cell (no visible repetition)
        n = len(self.decor)
        for gy in range(int(cy // 200) - 1, int((cy + H) // 200) + 1):
            for gx in range(int(cx // 200) - 1, int((cx + W) // 200) + 1):
                hsh = (gx * 73856093 ^ gy * 19349663) & 0xFFFFFF
                if hsh % 5 < 2:
                    d = self.decor[(hsh >> 3) % (n - 1)] if hsh % 13 else self.decor[-1]
                    put(d, gx * 200 + (hsh >> 6) % 150 - cx, gy * 200 + (hsh >> 12) % 150 - cy)
        # O GRAVE
        vr = self.vr
        hx, hy, R = self.hx - cx, self.hy - cy, self.R
        # the edge of its reach: a faint dotted circle when it crosses the screen
        er = ROUT
        if abs(math.hypot(W / 2 - hx, H / 2 - hy) - er) < 420:
            n = 180
            pts = []
            for i in range(n):
                a = i * math.tau / n + t * 0.05
                x, y = hx + math.cos(a) * er, hy + math.sin(a) * er
                if -4 < x < W + 4 and -4 < y < H + 4:
                    pts.append((x - 2, y - 2, 4, 4))
            g.rects(pts, (255, 60, 200), 70)
        if -R * 5 < hx < W + R * 5 and -R * 5 < hy < H + R * 5:
            pr, pr2 = [], []
            for i, p in enumerate(self.parts):
                x, y = hx + math.cos(p[0]) * p[1], hy + math.sin(p[0]) * p[1]
                (pr if i % 2 else pr2).append((x, y, 3, 3))
            g.rects(pr, C["violet"], 160)
            g.rects(pr2, (255, 60, 200), 160)
            vr.draw_grave(g, hx, hy, R, t, self.pulse, self.charge, [(self.t - w[0], w[1]) for w in self.waves],
                          self.boost_t > 0)
        # chests
        ct = vr.tex["chest"]
        for c in self.chests:
            x, y = c[0] - cx, c[1] - cy
            if -60 < x < W + 60 and -60 < y < H + 60:
                bob = math.sin(t * 4 + c[0]) * 3
                put(vr.tex["glowlight"], x - 46, y - 40)
                k = 1.5 if c[2] else 1.0
                put(ct, x - ct[1] * k / 2, y - ct[2] * k / 2 + bob, ct[1] * k, ct[2] * k)
        # goo + webs on the ground
        pt = vr.tex["pud"]
        for p in self.puddles:
            x, y, r = p[0] - cx, p[1] - cy, p[3]
            if -r < x < W + r and -r < y < H + r:
                web = p[4] == "web"
                sdl2.SDL_SetTextureColorMod(pt[0], *((235, 235, 255) if web else (150, 50, 200)))
                sdl2.SDL_SetTextureAlphaMod(pt[0], int(255 * min(1.0, p[2])))
                put(pt, x - r, y - r, r * 2, r * 2)
                if web:
                    g.rects([(x + math.cos(i * 0.785) * k - 1, y + math.sin(i * 0.785) * k - 1, 3, 3)
                             for i in range(8) for k in (12, 24, 36)], (255, 255, 255), 150)
        sdl2.SDL_SetTextureColorMod(pt[0], 255, 255, 255)
        sdl2.SDL_SetTextureAlphaMod(pt[0], 255)
        # solar crown (under everything that moves)
        lva = self.weapons.get("aura", 0)
        if lva:
            ar = self.aura_r(lva, "aura" in self.evo)
            put(vr.tex["aura"], W / 2 - ar, H / 2 - ar, ar * 2, ar * 2)
            dots(W / 2, H / 2, ar, 12, (255, 214, 60), 200, 4, t * 1.5)
        # shards, mines, white holes
        st = self.tx["shard"]
        for s in self.shards:
            x, y = s[0] - cx, s[1] - cy
            if -10 < x < W and -10 < y < H:
                if s[2] < 0:
                    g.rect(x - 7, y - 2, 14, 4, (255, 236, 140))
                    g.rect(x - 2, y - 7, 4, 14, (255, 236, 140))
                    g.rect(x - 2, y - 2, 4, 4, (255, 255, 255))
                else:
                    gt = s[3] if len(s) > 3 else 0
                    put(self.tx.get("gem%d" % gt, st), x - 5, y - 7)
                    if gt >= 3 and int(t * 6 + s[0]) % 5 == 0:          # the rich ones sparkle
                        g.rect(x + 3, y - 9, 2, 2, (255, 255, 255))
        for m in self.mines:
            x, y = m[0] - cx, m[1] - cy
            g.rect(x - 6, y - 6, 12, 12, (255, 179, 71))
            g.rect(x - 3, y - 3, 6, 6, (255, 250, 220) if int(t * 4) % 2 else (255, 179, 71))
        for w in self.whites:
            x, y = w[0] - cx, w[1] - cy
            k = 1 - w[2] / 1.1
            put(vr.tex["aura"], x - 26 - 10 * k, y - 26 - 10 * k, 52 + 20 * k, 52 + 20 * k)
            g.rect(x - 8, y - 8, 16, 16, (255, 255, 255))
            dots(x, y, 150 * self.area() * (1 - k), 10, (255, 255, 255), 200, 4, t * 3)
        # enemies + their wind-ups
        ppx, ppy = W / 2, H / 2
        for e in self.enemies:
            x, y = e.x - cx, e.y - cy
            tx = e.tex
            if not (-tx[1] < x < W + tx[1] and -tx[2] < y < H + tx[2]):
                continue
            est = e.st
            if est == "warp":
                dots(x, y, 8 + 22 * max(0.0, e.cd), 8, (178, 60, 255), 220, 5, t * 5)
                g.rect(x - 3, y - 3, 6, 6, (255, 60, 200))
                continue
            if e.flash > 0 or (e.k == "seer" and e.t > 3.6):
                tx = self.tx[e.k + "_w"] if (e.k + "_w") in self.tx else tx
            alpha = 255
            if est == "fade":
                alpha = int(255 * max(0.0, e.cd) / 0.5)
                mx, my = e.ax - cx, e.ay - cy
                if int(t * 12) % 2:
                    g.rects([(mx - 10, my - 2, 20, 4), (mx - 2, my - 10, 4, 20)], (178, 60, 255), 220)
            elif est == "appear":
                alpha = int(255 * (1 - max(0.0, e.cd) / 0.35))
            elif e.k == "phantom":
                alpha = 205
            sx = x + (math.sin(t * 70) * 2 if est in ("wind", "aim", "armed") else 0)
            cold = e.slow > 0
            if alpha < 255:
                sdl2.SDL_SetTextureAlphaMod(tx[0], max(0, alpha))
            if cold:
                sdl2.SDL_SetTextureColorMod(tx[0], *((90, 200, 255) if e.slowk < 0.05 else (130, 170, 255)))
            put(tx, sx - tx[1] / 2, y - tx[2] / 2)
            if alpha < 255:
                sdl2.SDL_SetTextureAlphaMod(tx[0], 255)
            if cold:
                sdl2.SDL_SetTextureColorMod(tx[0], 255, 255, 255)
            if est == "wind":
                g.rects([(x + e.ax * k - 3, y + e.ay * k - 3, 6, 6) for k in range(24, 190, 18)], (255, 60, 90), 170)
            elif est == "aim":
                base = math.atan2(ppy - y, ppx - x)
                rr = e.rad + 6 + 18 * (1 - max(0.0, e.cd) / 0.8)
                g.rects([(x + math.cos(base + (j - 2) * 0.26) * rr - 3, y + math.sin(base + (j - 2) * 0.26) * rr - 3,
                          6, 6) for j in range(5)], (255, 60, 200), 230)
            elif est == "armed":
                blink = int(t * (6 + 14 * (1 - max(0.0, e.cd) / 0.9))) % 2
                dots(x, y, 74, 16, (255, 80, 60), 220 if blink else 90, 5)
            elif est == "inhale":
                for j in range(9):
                    f = (t * 2.5 + j / 9.0) % 1.0
                    g.rect(ppx + (x - ppx) * f - 3, ppy + (y - ppy) * f - 3, 6, 6,
                           (255, 255, 255) if j % 2 else (255, 60, 200), int(90 + 150 * f))
            if e.k == "warden":
                base = math.atan2(ppy - y, ppx - x)
                g.rects([(x + math.cos(base + j * 0.3) * (e.rad + 8) - 3, y + math.sin(base + j * 0.3) * (e.rad + 8) - 3,
                          6, 6) for j in range(-3, 4)], (120, 220, 255), 230)
            if e.boss:
                g.rect(x - 40, y - tx[2] / 2 - 10, 80, 5, (40, 0, 30))
                g.rect(x - 40, y - tx[2] / 2 - 10, 80 * max(0, e.hp) / e.maxhp, 5, (255, 60, 200))
        # shots
        g.rects([(s[0] - cx - 4, s[1] - cy - 4, 8, 8) for s in self.eshots], (255, 60, 200))
        g.rects([(s[0] - cx - 2, s[1] - cy - 2, 4, 4) for s in self.eshots], (255, 230, 255))
        for L in self.lobs:
            f = L[4] / L[5]
            tx_, ty_ = L[2] - cx, L[3] - cy
            if int(t * 8) % 2:
                dots(tx_, ty_, 40, 12, (235, 235, 255), 140, 4)
            x = L[0] - cx + (L[2] - L[0]) * f
            y = L[1] - cy + (L[3] - L[1]) * f - math.sin(math.pi * f) * 50
            g.rect(x - 5, y - 5, 10, 10, (235, 235, 255))
        b0 = [(b[0] - cx - 3, b[1] - cy - 3, 6, 6) for b in self.bullets if b[7] == 0]
        b1 = [(b[0] - cx - 3, b[1] - cy - 3, 6, 6) for b in self.bullets if b[7] == 1]
        b2 = [(b[0] - cx - 4, b[1] - cy - 4, 8, 8) for b in self.bullets if b[7] == 2]
        g.rects(b0, (60, 242, 255))
        g.rects(b1, (110, 255, 170))
        if b2:
            g.rects(b2, (160, 250, 255))
            g.rects([(x + 2, y + 2, 4, 4) for x, y, _, _ in b2], (255, 255, 255))
        for m in self.missiles:
            x, y = m[0] - cx, m[1] - cy
            ux, uy = math.cos(m[2]), math.sin(m[2])
            g.rects([(x - ux * k * 6 - 2, y - uy * k * 6 - 2, 4, 4) for k in (1, 2, 3)], (255, 179, 71), 160)
            g.rect(x - 4, y - 4, 8, 8, (255, 120, 80))
            g.rect(x - 2, y - 2, 4, 4, (255, 240, 200))
        for b in self.boomers:
            x, y = b[0] - cx, b[1] - cy
            s = b[7]
            rot = t * 14
            g.rects([(x + math.cos(rot + j * 0.5) * s - 3, y + math.sin(rot + j * 0.5) * s - 3, 6, 6)
                     for j in range(-2, 3)], (190, 230, 255))
            g.rect(x + math.cos(rot) * s - 2, y + math.sin(rot) * s - 2, 4, 4, (255, 255, 255))
        # player
        px, py = W / 2, H / 2
        put(vr.tex["glowlight"], px - 46, py - 40)
        if self.dash_t > 0:
            ux, uy = self.dir
            g.rects([(px - 18 - ux * k * 10, py - 10 - uy * k * 10, 36, 30) for k in range(1, 4)], (60, 242, 255), 70)
        if not (self.inv > 0 and int(t * 20) % 2):
            frame = "run2" if (self.moving and int(self.anim * 8) % 2) else "run1"
            put(vr.tex[frame + ("" if self.fx_dir > 0 else "_l")], px - 18, py - 20)
        if self.slowed:
            g.rects([(px - 14 + i * 7, py + 16 + (i % 2) * 3, 4, 4) for i in range(5)], (235, 235, 255), 200)
        # prism ring(s)
        lvr = self.weapons.get("ring", 0)
        if lvr:
            pts = []
            for n, rad, spin in self.ring_specs(lvr, "ring" in self.evo):
                a0 = self.t * spin
                pts += [(px + math.cos(a0 + i * math.tau / n) * rad - 5, py + math.sin(a0 + i * math.tau / n) * rad - 5,
                         10, 10) for i in range(n)]
            g.rects(pts, (210, 180, 255))
            g.rects([(x + 3, y + 3, 4, 4) for x, y, _, _ in pts], (255, 255, 255))
        # sentinels
        lvd = self.weapons.get("drone", 0)
        if lvd:
            dp = [(x - cx - 5, y - cy - 5, 10, 10) for x, y in self.drone_pos(lvd, "drone" in self.evo)]
            g.rects(dp, (110, 255, 170))
            g.rects([(x + 3, y + 3, 4, 4) for x, y, _, _ in dp], (255, 255, 255))
        # lighthouse beam(s)
        lvb = self.weapons.get("beam", 0)
        if lvb:
            L = self.beam_len(lvb, "beam" in self.evo)
            for a in self.beam_angles("beam" in self.evo):
                ux, uy = math.cos(a), math.sin(a)
                g.rects([(px + ux * k - 4, py + uy * k - 4, 8, 8) for k in range(24, int(L), 12)], (255, 110, 230), 170)
                g.rects([(px + ux * k - 1, py + uy * k - 1, 3, 3) for k in range(24, int(L), 12)], (255, 255, 255))
        # effects
        now = self.t
        for f in self.fx:
            el = (now - f[1]) / f[2]
            kind = f[0]
            if kind == "lance":
                _, _, _, x, y, ux, uy, wid = f
                a = int(170 * (1 - el))
                ww = max(4, int(wid * 0.6))
                g.rects([(x - cx + ux * k - ww / 2, y - cy + uy * k - ww / 2, ww, ww) for k in range(0, 420, 16)],
                        (255, 220, 120), a)
            elif kind == "chain":
                c = (255, 255, 255) if f[4] else (160, 230, 255)
                sdl2.SDL_SetRenderDrawColor(ren, c[0], c[1], c[2], 255)
                for x0, y0, x1, y1 in f[3]:
                    sdl2.SDL_RenderDrawLine(ren, int(x0 - cx), int(y0 - cy), int(x1 - cx), int(y1 - cy))
                    sdl2.SDL_RenderDrawLine(ren, int(x0 - cx) + 1, int(y0 - cy), int(x1 - cx) + 1, int(y1 - cy))
            elif kind in ("nova", "boom", "cboom", "bblast", "frost", "white"):
                _, _, _, x, y, r = f
                rr = r * (0.4 + 0.6 * el)
                col = FX_COL[kind]
                dots(x - cx, y - cy, rr, 20 if r > 120 else 16, col, int(255 * (1 - el)))
            elif kind == "crit":
                x, y = f[3] - cx, f[4] - cy
                g.rects([(x - 8, y - 2, 16, 4), (x - 2, y - 8, 4, 16)], (255, 236, 140), int(255 * (1 - el)))
            elif kind == "block":
                x, y = f[3] - cx, f[4] - cy
                g.rects([(x - 6 + i * 4, y - 6 + ((i * 7) % 12), 3, 3) for i in range(4)], (120, 220, 255),
                        int(255 * (1 - el)))
        # danger vignette when the hole is close
        if self.boost_t > 7.6:
            g.rect(0, 0, W, H, (255, 255, 255), int(140 * (self.boost_t - 7.6) / 0.4))
        danger = max(0.0, 1 - (self.gd - self.R) / 180.0) if hasattr(self, "gd") else 0
        if danger > 0 and self.state == "play":
            a = int(120 * danger * (0.7 + 0.3 * math.sin(t * 10)))
            g.rects([(0, 0, W, 14), (0, H - 14, W, 14), (0, 0, 14, H), (W - 14, 0, 14, H)], (255, 0, 100), a)
        # off-screen arrows: chests (gold) and O GRAVE
        for c in self.chests:
            x, y = c[0] - cx, c[1] - cy
            if not (0 < x < W and 0 < y < H):
                ang = math.atan2(y - H / 2, x - W / 2)
                ex = max(20, min(W - 20, W / 2 + math.cos(ang) * 400))
                ey = max(60, min(H - 50, H / 2 + math.sin(ang) * 400))
                if int(t * 4) % 2:
                    g.rect(ex - 7, ey - 7, 14, 14, (255, 200, 70))
                    g.rect(ex - 3, ey - 3, 6, 6, (255, 255, 255))
        if not (0 < hx < W and 0 < hy < H):
            ang = math.atan2(hy - H / 2, hx - W / 2)
            ex = max(24, min(W - 24, W / 2 + math.cos(ang) * 400))
            ey = max(64, min(H - 48, H / 2 + math.sin(ang) * 400))
            put(vr.tex["glow"], ex - 18, ey - 18, 36, 36)
            g.rect(ex - 5, ey - 5, 10, 10, (0, 0, 0))
            g.text("k16", "GRAVE %dm" % max(0, (self.gd - self.R) / 10), ex, ey + 12, (255, 60, 200), 255, "center")
        self.draw_hud(g, t)

    def draw_hud(self, g, t):
        vr = self.vr
        dst = sdl2.SDL_Rect()
        g.rect(0, 0, W, 10, (10, 0, 20), 220)
        g.rect(1, 2, (W - 2) * min(1.0, self.xp / float(self.need)), 6, C["violet"])
        lx = g.text("kb16", "LV %d" % self.lv, 8, 14, C["text"])
        gt = self.tx.get("gem%d" % (self.gem_tiers() - 1))             # the richest crystal you can find now
        if gt:
            dst.x, dst.y, dst.w, dst.h = lx + 8, 16, gt[1], gt[2]
            sdl2.SDL_RenderCopy(self.ren, gt[0], None, dst)
        g.text("k16", ("♪ " + self.song["title"])[:26], 8, 34, C["muted"])
        if self.endless:
            tt = self.mt
            g.text("kb24", "%02d:%02d" % (tt // 60, tt % 60), W // 2, 12, C["text"], 255, "center")
        else:
            left = max(0.0, self.dur - self.mt)
            g.text("kb24", "%d:%02d" % (left // 60, left % 60), W // 2, 12,
                   (255, 220, 90) if left < 20 else C["text"], 255, "center")
            g.rect(W // 2 - 60, 44, 120, 3, (40, 20, 60))
            g.rect(W // 2 - 60, 44, 120 * self.prog(), 3, (255, 60, 200))
        g.text("kb16", "x %d" % self.kills, W - 10, 14, (255, 60, 200), 255, "right")
        # the music: energy meter + a little equaliser that dances with the song
        g.text("k16", "ENERGIA", W - 140, 34, (255, 60, 200), 255, "right")
        g.rect(W - 132, 38, 120, 10, (30, 0, 30))
        g.rect(W - 132, 38, 120 * self.I, 10, (255, 220, 90) if self.boost_t > 0 else (255, 60, 200))
        bars = []
        for i in range(12):
            hgt = 3 + int(14 * self.I * (0.55 + 0.45 * math.sin(t * (5 + i) + i * 1.7)) + 8 * self.pulse * (i % 3 == 0))
            bars.append((W - 132 + i * 10, 64 - hgt, 7, hgt))
        g.rects(bars, (60, 242, 255), 200)
        if self.charge > 0:
            if int(t * 8) % 2:
                g.text("kb24", "DROP A CAMINHO!", W // 2, 70, (255, 220, 90), 255, "center")
        elif self.boost_t > 0:
            g.text("kb16", "DROP · ARMAS 150%", W // 2, 70, (255, 220, 90), 255, "center")
            g.rect(W // 2 - 70, 90, 140 * self.boost_t / 8.0, 3, (255, 220, 90))
        # hp
        px, py = W / 2, H / 2
        g.rect(px - 18, py + 22, 36, 4, (40, 0, 20))
        g.rect(px - 18, py + 22, 36 * max(0, self.hp) / self.maxhp, 4, (255, 70, 90))
        # weapons (gold frame = evolved) + passives + dash
        x = 8
        for k in WEAPON_IDS:
            if k in self.weapons:
                col = WEAPON_INFO[k][2]
                ev = k in self.evo
                g.rect(x, H - 30, 22, 22, (16, 12, 34), 220)
                g.frame(x, H - 30, 22, 22, (255, 220, 90) if ev else col, 2)
                ic = vr.tex.get("ics_" + k)
                if ic:
                    dst.x, dst.y, dst.w, dst.h = x + 4, H - 26, ic[1], ic[2]
                    sdl2.SDL_RenderCopy(self.ren, ic[0], None, dst)
                for j in range(self.weapons[k]):
                    g.rect(x + 1 + j * 4, H - 6, 3, 3, (255, 220, 90) if ev else col)
                x += 26
        x = 8
        for k in PASSIVES:
            if k in self.passive:
                ic = vr.tex.get("icp_" + k)
                g.rect(x, H - 50, 16, 16, (16, 12, 34), 200)
                if ic:
                    dst.x, dst.y, dst.w, dst.h = x + 1, H - 49, ic[1], ic[2]
                    sdl2.SDL_RenderCopy(self.ren, ic[0], None, dst)
                g.rect(x, H - 34, 16 * self.passive[k] / float(MAXLV), 2, PASSIVES[k][2])
                x += 18
        ready = self.dash_cd <= 0
        dw = g.tw("kb16", "DASH")
        g.text("kb16", "DASH", W - 10 - dw, H - 26, (60, 242, 255) if ready else C["dim"])
        if not ready:
            g.rect(W - 10 - dw, H - 8, dw * (1 - self.dash_cd / (4.0 * (1 - 0.15 * self.lvl("dash")))), 3, C["dim"])
        s, t0, sub = self.banner
        el = time.time() - t0
        dur = 3.4 if sub else 2.4
        if s and el < dur:
            a = int(255 * min(1.0, (dur - el) / 0.5))
            big = s == "DROP!"
            f = "kb48" if big else "kb24"
            y = 104 if big else 108
            g.text(f, s, W // 2 + 2, y + 2, (0, 0, 0), a, "center")
            g.text(f, s, W // 2, y, (255, 220, 90) if big else (255, 60, 200), a, "center")
            if sub:
                g.text("k16", sub, W // 2 + 1, y + g.th(f) + 7, (0, 0, 0), a, "center")
                g.text("k16", sub, W // 2, y + g.th(f) + 6, C["text"], a, "center")


# ====================================================================== section (menus around a Run)
class VoidRunner(object):
    name = "VOID RUNNER"

    def __init__(self, app):
        self.app = app
        self.save_d = self.load()
        self.state = "menu"
        self.sel = 0
        self.world = 0
        self.top = 0
        self.run = None
        self.tex = None
        self.snd = {}
        self.psel = 0
        self.songs = []
        self.durs = {}
        self.scanner = None
        self.pending = None
        self.msg = ("", 0.0)
        self.parts = [[random.uniform(0, math.tau), random.uniform(60, 300)] for _ in range(70)]

    # ---------------------------------------------------------------- save
    def load(self):
        d = engine.load_save(SAVE)
        if d is None:
            return {"unlocked": 1, "best": {}, "endless": 0}
        d.setdefault("best", {})
        d.setdefault("unlocked", 1)
        return d

    def write(self, sync=True):
        try:
            engine.write_json(SAVE, self.save_d, sync)
        except Exception:
            pass

    def record(self, run):
        if run.endless:
            self.save_d["endless"] = max(self.save_d.get("endless", 0), int(run.mt))
        else:
            key = "%s|%d" % (run.song["id"], run.level)
            best = self.save_d["best"].get(key, {"kills": 0, "won": False, "t": 0})
            best["kills"] = max(best.get("kills", 0), run.kills)
            best["t"] = max(best.get("t", 0), int(run.mt))
            if run.state == "won":
                best["won"] = True
                before = self.save_d.get("unlocked", 1)
                self.save_d["unlocked"] = max(before, min(6, run.level + 2))
                run.unlocked_new = self.save_d["unlocked"] > before
            self.save_d["best"][key] = best
        self.write()

    def cfg_lite(self):
        return bool(self.app.cfg.get("vr_lite", False))

    # ---------------------------------------------------------------- the songs
    def song_list(self):
        import beatduel
        out = []
        pool = sorted(glob.glob(os.path.join(MOODS, "energetico_*.wav")) + glob.glob(os.path.join(MOODS, "zangado_*.wav")) +
                      glob.glob(os.path.join(MOODS, "alegre_*.wav")))
        if pool:
            out.append({"id": "SEM_FIM", "title": "SEM FIM", "tag": "MÚSICA DA NAVE SEM PARAR", "endless": True,
                        "pool": pool, "paths": random.sample(pool, min(3, len(pool))), "col": (255, 60, 200)})
        found = beatduel.find_songs()
        builtin = [x for x in found if x["src"] == "INCLUIDA"]
        if builtin:
            out.append({"id": "MIX_DA_NAVE", "title": "MIX DA NAVE", "tag": "AS %d MÚSICAS DA NAVE SEGUIDAS" % len(builtin),
                        "paths": [x["wav"] for x in builtin], "col": (255, 220, 90)})
        cols = {"INCLUIDA": C["violet"], "SESSAO": (255, 90, 100), "ABDUCTOR": C["cyan"], "MUSICA": C["green"]}
        for x in found:
            out.append({"id": x.get("id") or os.path.basename(x["wav"]), "title": x["title"],
                        "tag": beatduel.SRC_NAME.get(x["src"], x["src"]), "paths": [x["wav"]],
                        "missing": x.get("missing", False), "col": cols.get(x["src"], C["soft"])})
        return out

    def dur(self, song):
        if song.get("endless"):
            return 0
        tot = 0.0
        for p in song["paths"]:
            if p not in self.durs:
                self.durs[p] = songscan.duration(p) if os.path.exists(p) else 0.0
            tot += self.durs[p]
        return tot

    # ---------------------------------------------------------------- shared textures + sounds
    def enter(self):
        ren = self.app.ren
        if not self.tex:
            self.tex = {
                "glow": bake_disc(ren, 64, [(1.0, (255, 60, 200, 18)), (0.8, (255, 60, 200, 34)),
                                            (0.6, (178, 60, 255, 60)), (0.45, (178, 60, 255, 90))]),
                "glowlight": bake_disc(ren, 46, [(1.0, (255, 236, 140, 14)), (0.7, (255, 236, 140, 26)),
                                               (0.45, (255, 236, 140, 40))]),
                # O GRAVE: a subwoofer seen from the front - frame, rubber surround, ribbed cone, dust cap
                "g_frame": bake_disc(ren, 64, [(1.0, (20, 18, 30, 255)), (0.97, (86, 84, 110, 255)),
                                               (0.9, (58, 56, 78, 255)), (0.86, (30, 28, 42, 255))]),
                "g_surr": bake_disc(ren, 64, [(1.0, (14, 12, 22, 255)), (0.95, (40, 38, 54, 255)),
                                              (0.88, (64, 62, 84, 255)), (0.8, (40, 38, 54, 255)),
                                              (0.74, (14, 12, 22, 255))]),
                "g_cone": bake_disc(ren, 64, [(1.0, (28, 26, 40, 255)), (0.93, (36, 34, 50, 255)),
                                              (0.86, (28, 26, 40, 255)), (0.78, (44, 42, 60, 255)),
                                              (0.7, (34, 32, 48, 255)), (0.6, (52, 50, 70, 255)),
                                              (0.5, (40, 38, 56, 255)), (0.42, (62, 60, 84, 255))]),
                "g_cap": bake_disc(ren, 64, [(1.0, (16, 14, 26, 255)), (0.9, (70, 68, 96, 255)),
                                             (0.65, (96, 94, 126, 255)), (0.35, (130, 128, 164, 255))]),
                "run1": bake(ren, ART.RUNNER, ART.RUNNER_PAL),
                "run2": bake(ren, ART.RUNNER_RUN, ART.RUNNER_PAL),
                "run1_l": bake(ren, ART.RUNNER, ART.RUNNER_PAL, flip=True),
                "run2_l": bake(ren, ART.RUNNER_RUN, ART.RUNNER_PAL, flip=True),
                "chest": bake(ren, CHEST, CHEST_PAL, 3),
            }
            self.tex["pud"] = bake_disc(ren, 32, [(1.0, (255, 255, 255, 70)), (0.85, (255, 255, 255, 110))])
            self.tex["aura"] = bake_disc(ren, 64, [(1.0, (255, 214, 60, 46)), (0.93, (255, 214, 60, 20))])

            def icon(k, col, s):
                return bake(ren, ART.ICONS[k], {"X": col, "W": (255, 255, 255), "K": (10, 0, 20)}, s)
            gold = (255, 220, 90)
            for k, info in WEAPON_INFO.items():
                self.tex["ic_" + k] = icon(k, info[2], 4)        # card
                self.tex["ics_" + k] = icon(k, info[2], 2)       # HUD
                self.tex["ice_" + k] = icon(k, gold, 4)          # evolution card
            for k, info in PASSIVES.items():
                self.tex["icpb_" + k] = icon(k, info[2], 4)
                self.tex["icp_" + k] = icon(k, info[2], 2)
            for k in ("bolt", "zap", "boom", "hit", "pop", "xp", "lvlup", "dash", "hurt", "collapse", "win", "alarm",
                      "rumble", "ring"):
                try:
                    self.snd[k] = load_wav(os.path.join(VRD, k + ".wav"))
                except Exception:
                    pass
        self.songs = self.song_list()
        self.sel = max(0, min(self.sel, len(self.songs) - 1))
        self.world = min(self.world, self.save_d.get("unlocked", 1) - 1)
        m = self.app.mixer
        with m.lock:                       # the game brings its own music: everything else goes quiet
            m.kill_group("reactor")
            for st in m.streams:
                if getattr(st, "group", "") != "vr":
                    st.fade(0.0, 0.5)
        self.state = "menu" if self.run is None else self.state

    def leave(self):
        if self.run:
            self.run.free()
            self.run = None
        self.scanner = None
        self.state = "menu"

    def start(self, level, song):
        """listen to the song first (in the background), then play"""
        if self.run:
            self.run.free()
            self.run = None
        if song.get("endless"):
            song = dict(song, paths=random.sample(song["pool"], min(3, len(song["pool"]))))
        self.pending = (level, song)
        self.scanner = songscan.Scanner(song["paths"])
        self.scanner.start()
        self.scan_t0 = time.time()
        self.state = "scan"

    def start_now(self, level, song):
        """the same, without the thread (tests, footage capture)"""
        if song.get("endless"):
            song = dict(song, paths=random.sample(song["pool"], min(3, len(song["pool"]))))
        self.run = Run(self, level, song, songscan.build(song["paths"]), bool(song.get("endless")))
        self.state = "run"
        return self.run

    def on_select(self):
        if self.state == "run" and self.run and self.run.state == "play":
            self.state = "pause"
            self.psel = 0
        elif self.state == "scan":
            self.scanner = None
            self.state = "menu"
        elif self.state == "menu":
            self.app.go("bridge")

    # ---------------------------------------------------------------- input
    def on(self, kind, b):
        st = self.state
        if st == "menu":
            n = len(self.songs)
            if kind in ("press", "repeat") and b in ("up", "down") and n:
                self.sel = (self.sel + (1 if b == "down" else -1)) % n
                self.app.ui_move()
            elif kind == "press" and b in ("left", "right", "l1", "r1"):
                w = self.world + (1 if b in ("right", "r1") else -1)
                if 0 <= w < 6:
                    self.world = w
                    self.app.ui_move()
            elif kind == "press" and b in ("a", "start") and n:
                song = self.songs[self.sel]
                if song.get("missing"):
                    return
                if self.world < self.save_d.get("unlocked", 1):
                    self.app.ui_ok()
                    self.start(self.world, song)
            elif kind == "press" and b == "b":
                self.app.go("bridge")
            return
        if st == "scan":
            if kind == "press" and b == "b":
                self.scanner = None
                self.state = "menu"
            return
        if st == "pause":
            if kind in ("press", "repeat") and b in ("up", "down"):
                self.psel = (self.psel + (1 if b == "down" else -1)) % 3
            elif kind == "press" and b == "start":
                self.state = "run"
            elif kind == "press" and b == "a":
                if self.psel == 0:
                    self.state = "run"
                elif self.psel == 1:
                    self.app.cfg["vr_lite"] = not self.cfg_lite()
                    self.run.lite = self.cfg_lite()
                    self.app.save_cfg()
                else:
                    self.run.free()
                    self.run = None
                    self.state = "menu"
            return
        r = self.run
        if r is None:
            return
        if r.state == "chest":
            if kind == "press" and b in ("a", "b", "start"):
                r.close_chest()
            return
        if r.state in ("dead", "won"):
            if kind == "press" and time.time() - r.end_t > 1.2:
                if b == "a":
                    nxt = r.level + 1 if (r.state == "won" and r.level < 5) else r.level
                    self.world = nxt
                    self.start(nxt, r.song)
                elif b in ("b", "start"):
                    r.free()
                    self.run = None
                    self.state = "menu"
            return
        if kind == "press" and b == "start" and r.state == "play":
            self.state = "pause"
            self.psel = 0
            return
        r.on(kind, b)

    def update(self, dt):
        if self.state == "scan" and self.scanner and self.scanner.done:
            sc, (level, song) = self.scanner, self.pending
            self.scanner = None
            if sc.timeline is None or sc.timeline.dur < 5:
                self.state = "menu"
                self.msg = ("Não consegui ler esta música.", time.time())
            else:
                self.run = Run(self, level, song, sc.timeline, bool(song.get("endless")))
                self.state = "run"
        if self.run:
            r = self.run
            r.music_pause(self.state == "pause" or r.state in ("levelup", "chest"))
            if self.state == "run":
                r.update(min(dt, 1 / 20.0))
        for p in self.parts:
            p[1] -= 40 * dt
            p[0] += dt * (1.5 + 90 / (p[1] + 20))
            if p[1] < 40:
                p[1] = random.uniform(200, 320)

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        if self.run and self.state in ("run", "pause"):
            self.run.draw(g, t)
            r = self.run
            if r.state == "levelup":
                self.draw_levelup(g, t)
            elif r.state == "chest":
                self.draw_chest(g, t)
            elif r.state in ("dead", "won"):
                self.draw_end(g, t)
            elif r.state == "collapse":
                el = time.time() - r.end_t
                g.rect(0, 0, W, H, (255, 255, 255), int(max(0, 200 - el * 160)))
            if self.state == "pause":
                self.draw_pause(g)
            return
        if self.state == "scan":
            return self.draw_scan(g, t)
        self.draw_menu(g, t)

    def draw_grave(self, g, cx, cy, R, t, pulse, charge, waves, boost=False):
        """O GRAVE: glow, sound rings leaving it, frame with bolts, rubber surround, the cone pumping with the
        beat, the dust cap. Charging before a drop it glows hotter."""
        dst = sdl2.SDL_Rect()

        def put(tx, x, y, w, h):
            dst.x, dst.y, dst.w, dst.h = int(x), int(y), int(w), int(h)
            sdl2.SDL_RenderCopy(self.app.ren, tx[0], None, dst)
        gl = R * (3.0 + 0.6 * pulse + 1.2 * charge)
        put(self.tex["glow"], cx - gl, cy - gl, gl * 2, gl * 2)
        for age, strength in waves:                   # rings of sound
            k = age / 0.9
            rr = R * (1.1 + 3.2 * k)
            n = 28 if rr < 200 else 44
            col = (60, 242, 255) if int(strength * 10) % 2 else (255, 60, 200)
            a = int(200 * (1 - k) * (0.4 + 0.6 * strength))
            g.rects([(cx + math.cos(i * math.tau / n) * rr - 3, cy + math.sin(i * math.tau / n) * rr - 3, 6, 6)
                     for i in range(n)], col, a)
        fr = R * 1.22
        put(self.tex["g_frame"], cx - fr, cy - fr, fr * 2, fr * 2)
        g.rects([(cx + math.cos(i * math.tau / 8 + 0.39) * R * 1.12 - 3, cy + math.sin(i * math.tau / 8 + 0.39) * R * 1.12 - 3,
                  6, 6) for i in range(8)], (150, 148, 180))
        put(self.tex["g_surr"], cx - R, cy - R, R * 2, R * 2)
        cr = R * 0.8 * (1 + 0.1 * pulse)
        put(self.tex["g_cone"], cx - cr, cy - cr, cr * 2, cr * 2)
        hot = charge > 0 or boost
        cap = R * 0.32 * (1 + 0.16 * pulse)
        if hot:
            sdl2.SDL_SetTextureColorMod(self.tex["g_cap"][0], 255, 140 + int(80 * (1 - charge)), 220)
        put(self.tex["g_cap"], cx - cap, cy - cap, cap * 2, cap * 2)
        if hot:
            sdl2.SDL_SetTextureColorMod(self.tex["g_cap"][0], 255, 255, 255)
        if charge > 0 and int(t * 10) % 2:
            g.rects([(cx + math.cos(i * 0.785 + t) * R * 1.4 - 2, cy + math.sin(i * 0.785 + t) * R * 1.4 - 2, 5, 5)
                     for i in range(8)], (255, 220, 90))

    def draw_menu(self, g, t):
        import ui
        g.clear((6, 2, 14))
        g.text("kb48", "VOID RUNNER", W // 2 + 3, 9, (255, 60, 200), 255, "center")
        g.text("kb48", "VOID RUNNER", W // 2, 6, (240, 220, 255), 255, "center")
        g.text("k16", "a tua música é o nível: os drops trazem hordas e baús", W // 2, 66, C["soft"], 255, "center")
        # the songs
        x0, y0, w0, rh, vis = 14, 92, 392, 40, 8
        n = len(self.songs)
        if not n:
            g.text("k24", "Sem músicas.", x0 + w0 // 2, 200, C["text"], 255, "center")
        self.top = max(0, min(self.top, n - vis))
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + vis:
            self.top = self.sel - vis + 1
        for row, i in enumerate(range(self.top, min(n, self.top + vis))):
            sg = self.songs[i]
            y = y0 + row * rh
            sel = i == self.sel
            col = sg["col"]
            ui.box(g, x0, y, w0, rh - 4, C["hull"] if sel else (16, 12, 34))
            if sel:
                ui.outline(g, x0, y, w0, rh - 4, col, 2)
            g.rect(x0 + 8, y + 9, 6, rh - 22, col)
            d = self.dur(sg)
            dtxt = "sem fim" if sg.get("endless") else "%d:%02d" % (d // 60, d % 60)
            g.text("k16", dtxt, x0 + w0 - 10, y + 1, C["muted"], 255, "right")
            room = w0 - 22 - 10 - 12                    # each line gets what its right-hand text leaves free
            g.text("kb16", ui.fit(g, "kb16", sg["title"], room - g.tw("k16", dtxt)), x0 + 22, y + 1,
                   C["text"] if not sg.get("missing") else C["dim"])
            right, rcol = "", C["muted"]
            if sg.get("endless"):
                e = self.save_d.get("endless", 0)
                if e:
                    right, rcol = "recorde %d:%02d" % (e // 60, e % 60), (255, 220, 90)
            else:
                best = self.save_d["best"].get("%s|%d" % (sg["id"], self.world))
                if best and best.get("won"):
                    right, rcol = "✓ %d" % best["kills"], C["green"]
                elif best:
                    right = "%d abatidos" % best["kills"]
            if right:
                g.text("k16", right, x0 + w0 - 10, y + 17, rcol, 255, "right")
            tag = "ABRE NO WARP FLOOR" if sg.get("missing") else sg["tag"]
            g.text("k16", ui.fit(g, "k16", tag, room - (g.tw("k16", right) if right else 0)), x0 + 22, y + 17,
                   col if not sg.get("missing") else C["dim"])
        if n > vis:
            g.text("k16", "▲▼ %d/%d" % (self.sel + 1, n), x0 + w0 // 2, y0 + vis * rh - 2, C["muted"], 255, "center")
        # the world
        x1, w1 = 418, W - 418 - 14
        b = ART.BIOMES[self.world]
        unl = self.world < self.save_d.get("unlocked", 1)
        ui.box(g, x1, y0, w1, 186, (16, 12, 34))
        ui.outline(g, x1, y0, w1, 186, b["accent"] if unl else C["dim"], 2)
        g.text("k16", "MUNDO %d DE 6" % (self.world + 1), x1 + 12, y0 + 6, C["muted"])
        g.text("k16", "◀ ▶", x1 + w1 - 12, y0 + 6, C["soft"], 255, "right")
        g.rect(x1 + 12, y0 + 30, 26, 26, b["ground"][2] if unl else C["off"])
        g.text("kb24", b["short"] if unl else "BLOQUEADO", x1 + 46, y0 + 28, b["accent"] if unl else C["dim"])
        if unl:
            ui.para(g, "k16", b["desc"], x1 + 12, y0 + 66, w1 - 24, C["soft"], 18)
            hard = ["calmo", "a aquecer", "a sério", "difícil", "muito difícil", "a Matriarca"][self.world]
            g.text("k16", "dificuldade: " + hard, x1 + 12, y0 + 160, (255, 220, 90))
        else:
            ui.para(g, "k16", "Ganha uma música no mundo %d para abrir este." % self.world, x1 + 12, y0 + 66, w1 - 24,
                    C["muted"], 18)
        pulse = max(0.0, math.sin(t * 6.0)) ** 6
        self.draw_grave(g, x1 + w1 // 2, 352, 30, t, pulse, 0.0, [((t * 0.9) % 0.9, 0.7)])
        g.text("k16", "O GRAVE", x1 + w1 // 2, 404, (255, 60, 200), 255, "center")
        ui.footer(g, [("A", "jogar"), ("cima/baixo", "música"), ("esq/dir", "mundo"), ("B", "voltar")], hints=False)
        if self.msg[0] and time.time() - self.msg[1] < 2.5:
            ui.toast(g, self.msg[0], C["orange"])

    def draw_scan(self, g, t):
        g.clear((6, 2, 14))
        lvl, song = self.pending
        sc = self.scanner
        pulse = max(0.0, math.sin(t * 8.0)) ** 4
        self.draw_grave(g, W // 2, 190, 52, t, pulse, 0.0, [((t * 1.2) % 0.9, 0.8)])
        g.text("kb32", "A OUVIR A MÚSICA...", W // 2, 300, C["text"], 255, "center")
        g.text("k24", song["title"][:34], W // 2, 346, (255, 220, 90), 255, "center")
        g.text("k16", "ritmo, energia e drops: é isto que vai mandar no jogo", W // 2, 382, C["soft"], 255, "center")
        prog = sc.progress if sc else 1.0
        g.rect(W // 2 - 120, 410, 240, 6, (40, 20, 60))
        g.rect(W // 2 - 120, 410, int(240 * max(prog, min(0.9, (time.time() - self.scan_t0) / 3.0))), 6, (255, 60, 200))
        g.text("k16", "B cancelar", W // 2, 430, C["dim"], 255, "center")

    def draw_chest(self, g, t):
        r = self.run
        c = r.chest
        g.rect(0, 0, W, H, (6, 0, 14), 190)
        el = time.time() - c["t0"]
        gold = (255, 220, 90)
        ct = self.tex["chest"]
        k = 3
        dst = sdl2.SDL_Rect(W // 2 - ct[1] * k // 2, 46 + int(math.sin(t * 5) * 3), ct[1] * k, ct[2] * k)
        sdl2.SDL_RenderCopy(self.app.ren, ct[0], None, dst)
        g.text("kb32", "BAÚ GRANDE!" if c["big"] else "BAÚ!", W // 2, 140, gold, 255, "center")
        items = c["items"]
        n = len(items)
        w, h, gap = 176, 170, 14
        x0 = W // 2 - (n * w + (n - 1) * gap) // 2
        for i, (kind, key, lv) in enumerate(items):
            shown = el > 0.4 * (i + 1)
            x = x0 + i * (w + gap)
            y = 196
            g.rect(x, y, w, h, (28, 20, 8) if kind == "e" else (16, 12, 34))
            if not shown:
                g.frame(x, y, w, h, C["dim"], 2)
                g.text("kb48", "?", x + w // 2, y + 50, C["dim"], 255, "center")
                continue
            name, desc, col, tag, ic, _, _ = self.card(r, kind, key)
            if kind in ("w", "p"):
                tag = "NÍVEL %d" % lv
            elif kind == "e":
                tag = "EVOLUÇÃO!"
            flash = max(0.0, 1.0 - (el - 0.4 * (i + 1)) / 0.25)
            g.frame(x, y, w, h, col, 3)
            self.blit(ic, x + w // 2 - 14, y + 18)
            fn = "kb16" if g.tw("kb16", name) <= w - 12 else "k16"
            g.text(fn, name, x + w // 2, y + 66, col, 255, "center")
            g.text("k16", tag, x + w // 2, y + 92, gold if kind == "e" else C["muted"], 255, "center")
            if flash > 0:
                g.rect(x, y, w, h, (255, 255, 255), int(180 * flash))
        if el > 0.4 * n + 0.3:
            g.text("k16", "A continuar", W // 2, 392, C["cyan"], 255, "center")

    def blit(self, tx, x, y):
        dst = sdl2.SDL_Rect(int(x), int(y), tx[1], tx[2])
        sdl2.SDL_RenderCopy(self.app.ren, tx[0], None, dst)

    def wrap(self, g, s, x, y, w, col, step=20):
        line = ""
        for wd in s.split():
            if g.tw("v20", line + " " + wd) > w:
                g.text("v20", line, x, y, col, 255, "center")
                y += step
                line = wd
            else:
                line = (line + " " + wd).strip()
        g.text("v20", line, x, y, col, 255, "center")

    def card(self, r, kind, k):
        """(name, desc, colour, tag, icon, evolution hint line 1, line 2)"""
        gold = (255, 220, 90)
        if kind == "e":
            p = EVOS[k]
            return (p[1], p[2], gold, "EVOLUÇÃO", self.tex["ice_" + k], "de " + WEAPON_INFO[k][0], "")
        if kind == "w":
            name, desc, col = WEAPON_INFO[k]
            lv = r.weapons.get(k, 0)
            tag = "NOVA ARMA" if lv == 0 else ("NÍVEL MÁX" if lv + 1 == MAXLV else "NÍVEL %d" % (lv + 1))
            p = EVOS[k][0]
            have = r.lvl(p) > 0
            return (name, desc, col, tag, self.tex["ic_" + k], "evolui com" + (" (tens)" if have else ""),
                    PASSIVES[p][0])
        if kind == "p":
            name, desc, col = PASSIVES[k]
            ws = [w for w, e in EVOS.items() if e[0] == k and w in r.weapons and w not in r.evo]
            h1, h2 = ("evolui a tua", WEAPON_INFO[ws[0]][0]) if ws else ("", "")
            tag = "NOVO PASSIVO" if not r.lvl(k) else ("NÍVEL MÁX" if r.lvl(k) + 1 == MAXLV else "NÍVEL %d" % (r.lvl(k) + 1))
            return (name, desc, col, tag, self.tex["icpb_" + k], h1, h2)
        return ("CURA", "Recupera toda a vida.", (255, 90, 110), "", self.tex["icpb_vital"], "", "")

    def draw_levelup(self, g, t):
        r = self.run
        g.rect(0, 0, W, H, (6, 0, 14), 180)
        g.text("p24", "NÍVEL %d!" % r.lv, W // 2, 44, (255, 220, 90), 255, "center")
        g.text("v20", "ARMAS %d/%d     PASSIVOS %d/%d" % (len(r.weapons), SLOTS, len(r.passive), SLOTS),
               W // 2, 80, C["soft"], 255, "center")
        for i, (kind, k) in enumerate(r.choices):
            x, y, w, h = 30 + i * 200, 112, 180, 262
            sel = i == r.csel
            name, desc, col, tag, ic, h1, h2 = self.card(r, kind, k)
            if sel:
                g.glow(x, y, w, h, col, 0.6 + 0.3 * math.sin(t * 6))
            g.rect(x, y, w, h, (28, 20, 8) if kind == "e" else (16, 12, 34))
            g.frame(x, y, w, h, col, 3 if sel else 2)
            if kind == "e":
                g.frame(x + 5, y + 5, w - 10, h - 10, col, 1)
            self.blit(ic, x + w // 2 - 14, y + 18)
            fn = "p8" if g.tw("p8", name) <= w - 12 else "v20"
            g.text(fn, name, x + w // 2, y + 62, col, 255, "center")
            g.text("v20", tag, x + w // 2, y + 82, (255, 220, 90) if kind == "e" else C["muted"], 255, "center")
            self.wrap(g, desc, x + w // 2, y + 112, w - 20, C["text"])
            if h1:
                g.rect(x + 14, y + h - 60, w - 28, 1, C["dim"])
                g.text("v20", h1, x + w // 2, y + h - 52, C["muted"], 255, "center")
                if h2:
                    hc = (255, 220, 90) if (kind == "p" or "(tens)" in h1) else C["soft"]
                    g.text("v20", h2, x + w // 2, y + h - 32, hc, 255, "center")
        g.text("v20", "esq/dir escolher  ·  A confirmar", W // 2, 392, C["dim"], 255, "center")
        g.text("v20", "Y trocar cartas (%d)    X banir esta (%d)" % (r.rerolls, r.banishes), W // 2, 416,
               C["cyan"] if (r.rerolls or r.banishes) else C["dim"], 255, "center")

    def draw_pause(self, g):
        g.rect(0, 0, W, H, (6, 0, 14), 218)
        g.text("p24", "PAUSA", W // 2, 40, C["text"], 255, "center")
        opts = ["CONTINUAR", "INIMIGOS: %s" % ("MENOS" if self.cfg_lite() else "NORMAL"), "SAIR PARA O MENU"]
        for i, o in enumerate(opts):
            y = 84 + i * 44
            sel = i == self.psel
            g.rect(W // 2 - 150, y, 300, 36, self.app.accent if sel else C["hull"])
            g.text("p8", o, W // 2, y + 14, C["void"] if sel else C["text"], 255, "center")
        # build sheet: each weapon, its level and what it evolves with
        r = self.run
        if not r:
            return
        g.text("p8", "A TUA BUILD", W // 2, 226, (255, 220, 90), 255, "center")
        y = 248
        for k in WEAPON_IDS:
            if k not in r.weapons:
                continue
            p, evo_name, _ = EVOS[k]
            name, _, col = WEAPON_INFO[k]
            self.blit(self.tex["ics_" + k], 70, y + 2)
            if k in r.evo:
                g.text("v20", evo_name, 92, y, (255, 220, 90))
                g.text("v20", "EVOLUÍDA", W - 70, y, (255, 220, 90), 255, "right")
            else:
                lv = r.weapons[k]
                g.text("v20", "%s  %d/%d" % (name, lv, MAXLV), 92, y, col)
                have = r.lvl(p) > 0
                hint = "+ %s %s" % (PASSIVES[p][0], "OK" if have else "?")
                g.text("v20", hint, W - 70, y, C["green"] if have else C["muted"], 255, "right")
            y += 22
        if r.passive:
            x = 70
            for k in PASSIVES:
                if k in r.passive:
                    self.blit(self.tex["icp_" + k], x, y + 6)
                    g.text("v20", str(r.passive[k]), x + 18, y + 2, PASSIVES[k][2])
                    x += 44
        # the crystal colours: what each is worth, which are still locked
        y = H - 40
        g.text("k16", "CRISTAIS", 70, y + 2, (255, 220, 90))
        x = 70 + g.tw("k16", "CRISTAIS") + 14
        for i, (name, xp, lv0, cols) in enumerate(GEMS):
            got = r.lv >= lv0
            tx = r.tx.get("gem%d" % i)
            if tx:
                if not got:
                    sdl2.SDL_SetTextureAlphaMod(tx[0], 70)
                self.blit(tx, x, y + 3)
                sdl2.SDL_SetTextureAlphaMod(tx[0], 255)
            lab = ("%d" % xp) if got else ("LV%d" % lv0)
            g.text("k16", lab, x + 13, y + 2, cols[2] if got else C["muted"])
            x += 13 + g.tw("k16", lab) + 12


    def draw_end(self, g, t):
        r = self.run
        el = time.time() - r.end_t
        a = int(min(200, el * 300))
        g.rect(0, 0, W, H, (6, 0, 14), a)
        if r.state == "won":
            title, col = "O GRAVE IMPLODIU!", (255, 220, 90)
            sub = "Aguentaste a música até ao fim"
        else:
            title, col = ("ENGOLIDO PELO GRAVE" if r.why == "hole" else "DERROTADO"), (255, 60, 200)
            sub = "O grave puxou-te para dentro" if r.why == "hole" else "A horda foi demais"
        g.text("kb48" if g.tw("kb48", title) < W - 20 else "kb32", title, W // 2, 96, col, 255, "center")
        g.text("k24", sub, W // 2, 166, C["text"], 255, "center")
        g.text("k16", "♪ " + r.song["title"][:40] + "  ·  " + ART.BIOMES[r.level]["short"], W // 2, 200, C["muted"], 255,
               "center")
        rows = [("TEMPO", "%d:%02d" % (r.mt // 60, r.mt % 60)), ("NÍVEL", "%d" % r.lv), ("ABATIDOS", "%d" % r.kills),
                ("DROPS", "%d" % r.drops_hit), ("MASSA DO GRAVE", "%d" % r.mass)]
        for i, (k, v) in enumerate(rows):
            g.text("k24", k, W // 2 - 20, 232 + i * 30, C["muted"], 255, "right")
            g.text("k24", v, W // 2 + 20, 232 + i * 30, C["text"])
        if getattr(r, "unlocked_new", False):
            g.text("kb16", "MUNDO %d DESBLOQUEADO!" % (r.level + 2), W // 2, 386, C["green"], 255, "center")
        if el > 1.2:
            nxt = "PRÓXIMO MUNDO" if (r.state == "won" and r.level < 5 and not r.endless) else "OUTRA VEZ"
            g.text("kb16", "A %s    B MENU" % nxt, W // 2, 414, C["cyan"], 255, "center")
