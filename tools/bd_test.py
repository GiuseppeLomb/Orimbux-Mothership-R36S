# headless test for BEAT DUEL: fake clock (runs a 70 s song in a few seconds), bots for both players,
# session recording -> chart -> play, editor on a music/*.wav, calibration. Writes snapshots to argv[1].
import ctypes, json, os, random, shutil, sys, time as _time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)


class FakeTime(object):
    def __init__(self):
        self.now = _time.time()

    def time(self):
        return self.now

    perf_counter = time          # the frame loop, pump() and the Beat Duel clock use the monotonic clock

    def __getattr__(self, k):
        return getattr(_time, k)


FT = FakeTime()
import sdl2
from PIL import Image
import engine, app as appmod, beatduel as bdm
engine.time = FT; bdm.time = FT; appmod.time = FT
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
made = []   # test files to clean up afterwards
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready: _time.sleep(0.05)
DT = 1 / 30.0


def step(n=1):
    for _ in range(n):
        FT.now += DT
        a.frame(DT)


def snap(name, frames=2):
    step(frames)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


KEY = {0: [("left", "y")], 1: [("down", "b")], 2: [("up", "x")], 3: [("right", "a")]}


def play(match, acc=((0.015, 1.0), (0.05, 0.9)), shots=()):
    """bots press each note with gaussian timing error; returns when the match ends"""
    plans = {}
    frames = 0
    releases = []
    while bd.state == "play":
        t = match.now()
        for r in [r for r in releases if t >= r[0]]:
            releases.remove(r)
            bd.on("release", r[1])
        for pi, p in enumerate(match.players):
            if p.cpu:
                continue
            sd, prob = acc[pi]
            for i in range(p.next, min(len(p.notes), p.next + 16)):
                n = p.notes[i]
                if n[2]:
                    continue
                k = (pi, i)
                if k not in plans:
                    plans[k] = random.random() < prob and random.gauss(0, sd)
                if plans[k] is not False and t >= n[0] + plans[k]:
                    keys = KEY[n[1]][0]
                    btn = keys[0] if (pi == 0 or match.mode != "DUELO") else keys[1]
                    plans[k] = False
                    bd.on("press", btn)
                    releases.append((n[0] + (n[3] if n[3] > 0 else 0.05), btn))
        step()
        frames += 1
        if frames in shots:
            snap(shots[frames], 0)
        if frames > 30 * 200:
            raise SystemExit("match never ended")
    return frames


def cleanup():
    for p in made:
        try:
            os.remove(p)
        except OSError:
            pass


import atexit
atexit.register(cleanup)
random.seed(3)
a.go("bridge"); a.cur.on("press", "r1"); snap("bd0_bridge", 15)
a.go("beatduel"); bd = a.cur
songs = bd.songs
print("songs:", [(s["title"], s["src"], {k: len(v) for k, v in s["charts"].items()}) for s in songs])
assert len([s for s in songs if s["src"] == "INCLUIDA"]) == 5
snap("bd1_select", 5)

# ---- DUELO, normal, song 0
bd.sel, bd.diff, bd.mode = 0, 1, 0
bd.on("press", "a"); assert bd.state == "play"
m = bd.match
f = play(m, shots={20: "bd2_countdown", 200: "bd3_duel", 700: "bd4_duel_late"})
print("duel frames", f, [(p.name, p.score, p.count, p.maxcombo, round(p.acc(), 1)) for p in m.players])
print("holds P1 %d/%d  P2 %d/%d" % (m.players[0].holds_ok, m.players[0].holds_total, m.players[1].holds_ok,
                                    m.players[1].holds_total))
assert m.players[0].holds_total > 5 and m.players[0].holds_ok >= m.players[0].holds_total - 2
assert m.players[0].count["perfect"] > m.players[0].count["miss"] * 5
snap("bd5_results", 3)
bd.on("press", "a"); assert bd.state == "select"

# ---- attacks are drawn
bd.sel = 2; bd.diff = 2; bd.on("press", "a"); m = bd.match
step(90)
m.players[1].fx = {"MIRROR": m.now() + 5, "HIDDEN": m.now() + 5}
m.players[0].fx = {"SPEED": m.now() + 5}
m.banner = ("P1 ATACA: MIRROR!", FT.now)
snap("bd6_attacks", 30)
bd.on("press", "start"); assert bd.state == "select"

# ---- VS CPU easy
bd.sel, bd.diff, bd.mode = 3, 0, bdm.MODES.index("VS CPU")
bd.on("press", "a"); m = bd.match
play(m, acc=((0.03, 0.95),), shots={400: "bd7_cpu"})
print("cpu", [(p.name, p.score, round(p.acc(), 1)) for p in m.players])
bd.on("press", "a")

# ---- calibration: taps 80 ms after each click
bd.on("press", "l1"); assert bd.state == "calib"
c = bd.calib
for b in c["beats"]:
    target = b + int(0.08 * engine.SR)
    while c["clock"].frames() < target:
        step()
    bd.on("press", "a")
    if b == c["beats"][4]:
        snap("bd8_calib", 0)
while bd.state == "calib":
    step()
print("offset", a.cfg.get("bd_offset"))
assert abs(a.cfg["bd_offset"] - 0.08) < 0.04, a.cfg["bd_offset"]

# ---- Loop Reactor loops become notes on every beat (not only when they start)
a.go("reactor"); r = a.cur
a.set_bpm(120)
a.rec.start("REACTOR")
r.bank = 0
r.trigger(0)                                   # AMEN loop, starts at the next bar
for _ in range(int(30 * 2.0 * 5)):            # 5 bars at 120 BPM
    step()
lp = a.rec.path
a.rec.stop(); r.trigger(0)
made += [lp + ".wav", lp + ".json"]
lm = json.load(open(lp + ".json"))
print("loop session notes: normal %d hard %d (before this fix: 1)" % (len(lm["charts"]["normal"]), len(lm["charts"]["hard"])))
assert len(lm["charts"]["normal"]) >= 12
a.mixer.kill_group("reactor")
# ---- Xeno: a held note becomes a long note
a.go("xeno"); xs = a.cur
a.rec.start("XENO")
step(10); xs.note_on("up"); step(30); xs.note_off("up"); step(5); xs.note_on("left"); step(3); xs.note_off("left"); step(10)
xp = a.rec.path
a.rec.stop()
made += [xp + ".wav", xp + ".json"]
xm = json.load(open(xp + ".json"))
print("xeno session:", xm["charts"]["normal"])
assert len(xm["charts"]["normal"][0]) == 3 and xm["charts"]["normal"][0][2] > 0.8 and len(xm["charts"]["normal"][1]) == 2
# ---- session recording -> chart
a.go("reactor")
a.rec.start("REACTOR")
for i in range(12):
    step(10)
    a.mixer.shot("t", a.snd["click_hi"], group="fx")
    a.rec.event(a.mixer.clock, ["left", "down", "up", "right"][i % 4])
step(30)
path = a.rec.path
a.rec.stop()
made += [path + ".wav", path + ".json"]
meta = json.load(open(path + ".json"))
print("session", meta["title"], meta["duration"], len(meta["charts"]["normal"]))
assert len(meta["charts"]["normal"]) == 12 and meta["duration"] > 4
a.go("beatduel"); bd = a.cur
ss = [i for i, s in enumerate(bd.songs) if s["src"] == "SESSAO"]
assert ss, "session not listed"
bd.sel, bd.mode, bd.diff = ss[0], bdm.MODES.index("TREINO"), 1
snap("bd9_select_session", 4)
bd.on("press", "a"); m = bd.match
play(m, acc=((0.01, 1.0),))
print("session play", m.players[0].count)
assert m.players[0].count["miss"] == 0
bd.on("press", "a")

# ---- editor on a music/*.wav (no chart yet)
os.makedirs(bdm.MUSIC_DIR, exist_ok=True)
test_wav = os.path.join(bdm.MUSIC_DIR, "teste editor.wav")
shutil.copy(os.path.join(bdm.BD, "moon_hop.wav"), test_wav)
made += [test_wav, test_wav + ".chart.json"]
bd.enter()
mi = [i for i, s in enumerate(bd.songs) if s["src"] == "MUSICA"][0]
bd.sel = mi
assert not bd.songs[mi]["charts"]
bd.on("press", "a"); assert bd.state == "select" and bd.prep   # no chart -> one is made from the song...
bd.on("press", "b"); assert bd.prep is None                     # ...unless B gives up
bd.on("press", "y"); assert bd.state == "editor"
e = bd.edit
for _ in range(20):
    bd.on("press", "left")                             # bpm 120 -> 100
snap("bd10_editor_setup", 2)
bd.on("press", "a")
off = a.cfg["bd_offset"]
beat = 60.0 / e["bpm"]
for k in range(16):
    target_t = 1.0 + k * beat + random.gauss(0, 0.02) + off + 0.137     # off-grid phase of 0.137 s
    while (e["clock"].frames() - e["start"]) / float(engine.SR) < target_t:
        step()
    bd.on("press", ["left", "b", "up", "a"][k % 4])
    if k == 8:
        snap("bd11_editor_rec", 0)
bd.on("press", "start")
ch = json.load(open(test_wav + ".chart.json"))
ts = [t for t, _ in ch["charts"]["normal"]]
print("editor notes", ts[:6], "...", len(ts))
step8 = beat / 2
errs = [abs(((t - 1.137) / step8) - round((t - 1.137) / step8)) * step8 for t in ts]
assert len(ts) == 16 and max(errs) - min(errs) < 0.002 and max(errs) < 0.04, errs   # frame-step lag only
bd.enter()
mi = [i for i, s in enumerate(bd.songs) if s["src"] == "MUSICA"][0]
assert bd.songs[mi]["charts"]["normal"]
bd.sel = mi
snap("bd12_select_custom", 3)

# ---- frame time of the play screen (no fake clock effect on perf_counter)
bd.sel, bd.mode, bd.diff = 1, 0, 2
bd.on("press", "a")
step(120)
t0 = _time.perf_counter()
step(120)
print("ms/frame duel hard: %.2f" % ((_time.perf_counter() - t0) / 120 * 1000))
bd.on("press", "start")
a.go("bridge")

for p in made:
    try:
        os.remove(p)
    except OSError:
        pass
for d in (bdm.MUSIC_DIR, bdm.REC_DIR):
    try:
        os.rmdir(d)
    except OSError:
        pass
for p in ("bd_save.json", "config.json", "pet.json"):
    try:
        os.remove(os.path.join(APPD, p))
    except OSError:
        pass
print("ok")
