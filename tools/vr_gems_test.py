"""VOID RUNNER v1.9.1: the softer, progressive Grave (huge, gentle field), the slower level curve and the
crystal colours (locked until a runner level, rarer the richer, twice as likely after a music drop)."""
import math, os, random, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("vr_save.json", "config.json", "pet.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod
import voidrunner as V

try:
    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    while not a.bank.ready:
        time.sleep(0.05)
    vr = a.sections["voidrunner"]
    a.go("voidrunner")
    vr.save_d["unlocked"] = 6
    song = [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0]
    random.seed(3)

    # --- the Grave: a progression, under your speed, a huge soft field
    for lvl in range(6):
        r = vr.start_now(lvl, song)
        sp = r.speed()
        gs = []
        for p in (0.0, 0.25, 0.5, 0.75, 1.0):
            r.mt = p * r.dur
            r.I = 1.0
            gs.append(r.gravity())
        assert all(b > a_ for a_, b in zip(gs, gs[1:])), gs              # grows with the song
        assert gs[0] < 0.45 * sp, (lvl, gs)                               # starts as a whisper
        assert gs[-1] < (0.75 if lvl == 0 else 1.15) * sp, (lvl, gs)      # world 1 never out-pulls you
        r.G, r.R, r.pulse = gs[-1], 60.0, 0.0
        r.hx, r.hy = 0.0, 0.0
        mags = []
        for d in (70, 150, 300, 600, 1000, 1500, 1990, 2010):
            gx, gy, _ = r.pull(d, 0.0)
            mags.append(math.hypot(gx, gy))
        assert all(b <= a_ + 1e-9 for a_, b in zip(mags, mags[1:])), mags  # gradual: weaker further out
        assert mags[-1] == 0.0 and mags[-2] < 0.5, mags                    # nothing past its reach
        assert mags[4] > 1.0, mags                                          # but felt very far out (1000 px)
        print("world %d: pull at the edge %.0f..%.0f px/s (speed %.0f); at 300 px %.0f, at 1000 px %.1f" % (
            lvl + 1, gs[0], gs[-1], sp, mags[2], mags[4]))
        r.free()
        vr.run = None

    # --- slower levels
    old = [int(4 + lv * 2.2) for lv in range(1, 31)]
    new = [V.Run.need_for(lv) for lv in range(1, 31)]
    assert all(b > a_ for a_, b in zip(new, new[1:]))
    assert all(n > o for n, o in zip(new, old)), (new, old)
    print("XP per level: 1->2 %d, 5->6 %d, 10->11 %d, 20->21 %d (was %d, %d, %d, %d)" % (
        new[0], new[4], new[9], new[19], old[0], old[4], old[9], old[19]))

    # --- crystals
    r = vr.start_now(0, song)
    foe = type("Foe", (), {"xp": 1})()
    for lv in (1, 4, 5, 9, 10, 14, 15, 20, 21, 27, 28):
        r.lv = lv
        tops = set(r.gem_for(foe) for _ in range(4000))
        assert max(tops) < r.gem_tiers(), (lv, tops)                     # nothing above what is unlocked
        assert r.gem_tiers() == sum(1 for gm in V.GEMS if lv >= gm[2])
    r.lv = 30
    cnt = [0] * len(V.GEMS)
    for _ in range(60000):
        cnt[r.gem_for(foe)] += 1
    assert all(b < a_ for a_, b in zip(cnt, cnt[1:])), cnt               # the richer, the rarer
    r.boost_t = 8.0
    cnt2 = [0] * len(V.GEMS)
    for _ in range(60000):
        cnt2[r.gem_for(foe)] += 1
    assert sum(cnt2[1:]) > 1.3 * sum(cnt[1:]) and cnt2[5] > 2 * cnt[5], (cnt, cnt2)   # a drop: more rare ones
    xp1 = sum(n * gm[1] for n, gm in zip(cnt, V.GEMS)) / 60000.0
    xp2 = sum(n * gm[1] for n, gm in zip(cnt2, V.GEMS)) / 60000.0
    assert xp2 < 4 * xp1, (xp1, xp2)                                    # ...but not a flood
    print("XP per small kill at LV30: %.1f, right after a drop %.1f" % (xp1, xp2))
    r.boost_t = 0.0
    big = type("Foe", (), {"xp": 8})()
    cnt3 = [0] * len(V.GEMS)
    for _ in range(60000):
        cnt3[r.gem_for(big)] += 1
    assert sum(cnt3[2:]) > 2 * sum(cnt[2:]), (cnt, cnt3)                # tough foes drop richer crystals
    print("crystals at LV30 per 60000 small kills:", dict(zip([gm[0] for gm in V.GEMS], cnt)))
    # picking one up gives its XP; unlocking a colour says so
    r.lv, r.xp, r.need = 4, 0.0, V.Run.need_for(4)
    r.state = "play"
    r.shards = [[r.px + 3, r.py, V.GEMS[2][1], 2]]
    r.update(1 / 30.0)
    assert abs(r.xp - V.GEMS[2][1] * r.xp_k) < 1e-6 or r.lv == 5, (r.xp, r.lv)
    r.state = "play"
    r.lv, r.xp, r.need = 4, 0.0, V.Run.need_for(4)
    r.add_xp(r.need / r.xp_k + 0.01)
    assert r.lv == 5 and "AZUL" in r.banner[0], r.banner
    print("ok")
finally:
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACK:
            open(p, "wb").write(BACK[f])
