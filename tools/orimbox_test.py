"""ORIMBOX (headless): the kit, loops staying in sync, mute/solo/remove, one sound per alien, the 5 secrets
(bonus at the next loop start, 2 loops long, saved), recording to a BEAT DUEL session, text inside the screen."""
import glob, json, os, sys, time, wave
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "orimbox.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import engine
import app as appmod
import orimbox as OB

off = []
orig = engine.Gfx.text


def text(self, fname, s, x, y, col, a=255, align="left"):
    end = orig(self, fname, s, x, y, col, a, align)
    if a > 60 and str(s).strip() and (end - self.tw(fname, s) < 0 or end > engine.W):
        off.append((fname, str(s)))
    return end


engine.Gfx.text = text
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["welcomed"] = True
recs_before = set(glob.glob(os.path.join(APPD, "recordings", "session_*.json")))
made = []


def step(n=1):
    for _ in range(n):
        a.mixer.render(1470)
        a.frame(1 / 30.0)


try:
    a.go("orimbox")
    ob = a.cur
    t0 = time.time()
    while ob.meta is None and ob.load_err is None and time.time() - t0 < 30:
        time.sleep(0.05)
    assert ob.meta and not ob.load_err, ob.load_err
    L = ob.L
    snd = ob.meta["sounds"]
    ids = [s["id"] for s in snd]
    assert len(snd) == 20 and len(ob.meta["bonus"]) == 5
    for c, _, _ in OB.CATS:
        assert sum(1 for s in snd if s["cat"] == c) == 5
    for sid in ids + [b["id"] for b in ob.meta["bonus"]]:
        w = wave.open(os.path.join(OB.D, sid + ".wav"))
        assert w.getnframes() == L and w.getframerate() == 44100 and w.getnchannels() == 1, sid
        assert len(ob.sound(sid)["env"]) == L // 1470, sid
        assert sid in ob.icons or ob.sound(sid)["cat"] == "bonus", sid

    def give(sid):
        ob.focus = "bar"
        ob.icon = ids.index(sid)
        ob.on("press", "a")

    def synced():
        m = a.mixer
        out = []
        for i, v in enumerate(ob.voice):
            if v is not None:
                out.append(v.pos % L == (m.clock - ob.t0) % L)
        return out

    give("bumtss")
    step(40)
    give("baixo")
    step(77)
    give("uuu")
    step(13)
    assert all(synced()) and len(synced()) == 3, synced()
    give("bumtss")                                            # already singing: just selects that alien
    assert ob.slot.count("bumtss") == 1 and ob.focus == "stage"
    # mute / solo / remove
    i_bass = ob.slot.index("baixo")
    ob.sel = i_bass
    ob.on("press", "a")
    assert ob.muted[i_bass] and ob.voice[i_bass].gain == 0.0
    ob.on("press", "a")
    assert not ob.muted[i_bass] and ob.voice[i_bass].gain > 0
    ob.on("press", "x")
    g = ob.gains()
    assert ob.solo == i_bass and all(g[k] == 0 for k in range(OB.SLOTS) if k != i_bass) and g[i_bass] > 0
    ob.on("press", "x")
    assert ob.solo is None
    ob.on("press", "b")
    assert ob.slot[i_bass] is None and not any(v.key == "obx%d" % i_bass for v in a.mixer.voices)
    step(20)
    assert all(synced())
    # a full stage: the 8th sound replaces the chosen alien
    ob.clear_all()
    assert ob.t0 is None and not any(v.group == "orimbox" for v in a.mixer.voices)
    for sid in ("bumtss", "zap", "baixo", "uuu", "bada", "kalimba", "risco"):
        give(sid)
    assert None not in ob.slot
    ob.sel = 3
    give("aah")
    assert ob.slot[3] == "aah" and ob.slot.count("aah") == 1
    # the secret: CORO COSMICO (uuu + nuvem + kalimba) starts at the next loop start, lasts 2 loops
    ob.clear_all()
    step(5)
    for sid in ("uuu", "nuvem"):
        give(sid)
    step(30)
    assert ob.bonus is None
    give("kalimba")
    assert ob.bonus and ob.bonus[0] == "coro", ob.bonus
    bid, st, en = ob.bonus
    assert (st - ob.t0) % L == 0 and st > a.mixer.clock and en - st == 2 * L
    while a.mixer.clock < st + 2000:
        step(1)
    assert "coro" in ob.found
    assert json.load(open(OB.SAVE))["found"] == ["coro"]
    before = [v.gain for v in ob.voice if v]
    assert all(abs(x - 0.7 * OB.GAIN[ob.sound(s)["cat"]]) < 1e-6 for x, s in zip(before, [s for s in ob.slot if s]))
    while a.mixer.clock < en + 2000:
        step(1)
    assert ob.bonus is None and not any(v.key == "obx_bonus" and not v.done for v in a.mixer.voices)
    # the crew: 7 aliens with the 4 groups -> A NAVE-MAE
    ob.clear_all()
    for sid in ("bumtss", "zap", "baixo", "uuu", "bada", "kalimba"):
        give(sid)
    assert not ob.bonus
    give("risco")
    assert ob.bonus and ob.bonus[0] == "nave", ob.bonus
    # recording: the mix becomes a session with BEAT DUEL notes
    ob.clear_all()
    for sid in ("tchka", "marimba", "dum"):
        give(sid)
    ob.on("press", "start")
    assert a.rec.active() and a.rec.src == "ORIMBOX"
    step(200)
    ob.on("press", "start")
    assert not a.rec.active()
    made = sorted(set(glob.glob(os.path.join(APPD, "recordings", "session_*.json"))) - recs_before)
    assert made, "no session saved"
    meta = json.load(open(made[-1]))
    lanes = set(n[1] for n in meta["charts"]["normal"])
    print("session %s: %.1f s, %d notes, lanes %s" % (meta["title"], meta["duration"], len(meta["charts"]["normal"]),
                                                       sorted(lanes)))
    assert meta["duration"] > 5 and len(meta["charts"]["normal"]) > 10 and {0, 2, 3} <= lanes
    assert meta["bpm"] == 100, meta["bpm"]
    # shuffle, drawing, leaving
    ob.shuffle()
    filled = [s for s in ob.slot if s]
    assert 5 <= len(filled) <= 7 and any(ob.sound(s)["cat"] == "beat" for s in filled)
    for f in ("bar", "stage"):
        ob.focus = f
        for k in range(3):
            ob.sel = k * 3
            ob.icon = k * 7
            step(2)
    a.go("bridge")
    step(2)
    assert not any(v.group == "orimbox" for v in a.mixer.voices)
    assert not off, off[:5]
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
    for p in made:
        for q in (p, p[:-5] + ".wav"):
            try:
                os.remove(q)
            except OSError:
                pass
