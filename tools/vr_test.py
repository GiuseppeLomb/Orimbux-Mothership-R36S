"""Headless VOID RUNNER test: a bot plays levels, we measure update/draw cost, balance and save screenshots."""
import ctypes, math, os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
for f in ("vr_save.json", "pet.json", "config.json"):
    try:
        os.remove(os.path.join(APPD, f))
    except OSError:
        pass
import sdl2
from PIL import Image
import app as appmod
import voidrunner as V
SMART = os.environ.get("BOT", "smart") == "smart"
import random
random.seed(int(os.environ.get("SEED", "1")))

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vrt"
LEVELS = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0]
os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready:
    time.sleep(0.05)
vr = a.sections["voidrunner"]
a.go("voidrunner")


def snap(name):
    if vr.run: print("  snap", name, [f[0] for f in vr.run.fx], "t=%.1f" % vr.run.t, vr.run.state)
    a.cur.draw(a.g, a.t, 1 / 30.0)
    a.g.scanlines()
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(
        os.path.join(OUT, name + ".png"))


snap("menu")
for lvl in LEVELS:
    vr.save_d["unlocked"] = 6
    song = [x for x in vr.songs if x["id"] == os.environ.get("SONG", "MIX_DA_NAVE")][0]
    vr.start_now(lvl, song)
    r = vr.run
    opened = []
    upd, drw, frames = 0.0, 0.0, 0
    maxe = 0
    shots = {20: "a", 90: "b", 200: "c", 280: "d", 350: "e"}
    taken = set()
    pref = ["speed", "anchor"]
    evo_snap = []
    seen_k = set()
    while r.state not in ("dead", "won") and frames < 12500:
        if r.state == "chest":
            opened.append((int(r.mt), r.chest["items"]))
            if len(opened) == 1:
                vr.draw(a.g, a.t, 1 / 30.0)
                r.chest["t0"] -= 5
                snap("L%d_chest" % (lvl + 1))
            r.chest["t0"] -= 5
            r.close_chest()
        # bot: run away from the hole, curving around it, dodge to the side of crowds
        dx, dy = r.px - r.hx, r.py - r.hy
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        ax, ay = (ux, uy) if r.gd - r.R < 220 else (ux * 0.8 - uy * 0.6, uy * 0.8 + ux * 0.6)
        crowd = sum(1 for e in r.enemies if (e.x - r.px) ** 2 + (e.y - r.py) ** 2 < 120 ** 2)
        if r.gd - r.R > 340 and r.shards and crowd < 6:     # safe: go get xp (not through a crowd)
            def clear(s):
                return all((e.x - s[0]) ** 2 + (e.y - s[1]) ** 2 > 50 ** 2 for e in r.enemies)
            near_s = [s for s in r.shards if (s[0] - r.px) ** 2 + (s[1] - r.py) ** 2 < 300 ** 2 and clear(s)]
            if near_s:
                sx = min(near_s, key=lambda s: (s[0] - r.px) ** 2 + (s[1] - r.py) ** 2)
                vx, vy = sx[0] - r.px, sx[1] - r.py
                vl = math.hypot(vx, vy) or 1
                ax, ay = vx / vl, vy / vl
        for e in r.enemies:                   # keep away from bodies
            ex, ey = r.px - e.x, r.py - e.y
            dd = ex * ex + ey * ey
            if dd < 8100:
                ax += ex / (dd + 1) * 60
                ay += ey / (dd + 1) * 60
        al = math.hypot(ax, ay) or 1
        ax, ay = ax / al, ay / al
        a.input.axes["lx"], a.input.axes["ly"] = ax, ay
        if r.state == "play" and r.gd - r.R < 120 and r.dash_cd <= 0:
            r.on("press", "a")
        if r.state == "levelup":
            if r.lv in (2, 12) and ("lvup%d" % r.lv) not in taken:
                taken.add("lvup%d" % r.lv)
                vr.state = "run"
                a.cur.draw(a.g, a.t, 1 / 30.0)
                snap("L%d_levelup%d" % (lvl + 1, r.lv))
            if r.lv == 4 and r.rerolls == 3:
                before = list(r.choices)
                r.reroll()
                r.banish()
                assert r.rerolls == 2 and r.banishes == 1 and len(r.choices) >= 1, (before, r.choices)
            def score(c):
                kind, k = c
                if kind == "e":
                    return 100
                if not SMART:
                    return 50 if (kind == "p" and k in pref and r.G > 40) else 0
                if kind == "p" and k in pref and r.G > 40 and r.lvl(k) < 3:
                    return 60
                if kind == "w" and k in r.weapons:
                    return 40 + r.weapons[k]
                if kind == "p" and any(V.EVOS[w][0] == k for w in r.weapons if w not in r.evo):
                    return 35
                if kind == "w" and len(r.weapons) < 4:
                    return 30
                return 10
            sc = [score(c) for c in r.choices]
            pick = sc.index(max(sc)) if (SMART or max(sc) > 0) else 0
            if r.choices[pick][0] == "e":
                evo_snap.append((r.lv, int(r.t), r.choices[pick][1]))
            r.csel = pick
            r.choose()
        t0 = time.perf_counter()
        a.mixer.render(1470)
        r.update(1 / 30.0)
        upd += time.perf_counter() - t0
        if frames % 30 == 0:
            t0 = time.perf_counter()
            r.draw(a.g, a.t)
            drw += time.perf_counter() - t0
        maxe = max(maxe, len(r.enemies))
        seen_k.update(e.k for e in r.enemies)
        if r.t >= 150 and "pause" not in taken and r.state == "play":
            taken.add("pause")
            vr.state = "pause"
            vr.draw(a.g, a.t, 1 / 30.0)
            snap("L%d_pause" % (lvl + 1))
            vr.state = "run"
        frames += 1
        for ts, tag in shots.items():
            if r.t >= ts and ts not in taken and r.state == "play":
                taken.add(ts)
                snap("L%d_%s" % (lvl + 1, tag))
    snap("L%d_end" % (lvl + 1))
    print("  song %s %.0fs drops at %s, hit %d, chests opened %s" % (song["title"], r.dur, r.tl.drops, r.drops_hit,
                                                                  [(t, len(it)) for t, it in opened]))
    print("level %d: state=%s why=%s t=%.0f lv=%d kills=%d hp=%.0f maxEnemies=%d G=%.0f R=%.0f mass=%.0f "
          "upd=%.2fms draw=%.2fms weapons=%s passive=%s evo=%s at %s\n  enemy kinds: %s" % (
              lvl + 1, r.state, r.why, r.t, r.lv, r.kills, r.hp, maxe, r.G, r.R, r.mass,
              upd / frames * 1000, drw / max(1, frames // 30) * 1000, r.weapons, r.passive, sorted(r.evo),
              evo_snap, sorted(seen_k)))
for f in ("vr_save.json", "pet.json", "config.json"):
    try:
        os.remove(os.path.join(APPD, f))
    except OSError:
        pass
