# headless test for BEAT FORGE (fake clock): timing, swing, ratchets, queue/chain, export -> Reactor,
# session REC -> Beat Duel chart, track page, background play, perf. Snapshots to argv[1].
import ctypes, glob, json, os, shutil, sys, time as _time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)
for f in ("forge.json", "config.json", "pet.json"):
    try: os.remove(os.path.join(APPD, f))
    except OSError: pass


class FakeTime(object):
    def __init__(self): self.now = _time.time()
    def time(self): return self.now
    def __getattr__(self, k): return getattr(_time, k)


FT = FakeTime()
import sdl2
from PIL import Image
import engine, app as appmod, forge as fm, beatduel as bdm
engine.time = FT; appmod.time = FT; fm.time = FT; bdm.time = FT
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
made = []
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready: _time.sleep(0.05)
DT = 1 / 30.0
SR = engine.SR


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


seen = []


class RecVoice(engine.Voice):
    __slots__ = ()

    def __init__(self, *args, **kw):
        engine.Voice.__init__(self, *args, **kw)
        if self.group == "forge":
            seen.append((self.key, self.start, round(self.gain, 3)))


fm.Voice = RecVoice


def capture():
    pass


def run_bars(bars):
    m = a.mixer
    target = m.clock + int(bars * 4 * m.beat_frames())
    while m.clock < target:
        step()


try:
    a.go("bridge"); snap("f0_bridge", 15)
    a.go("forge"); fg = a.cur
    snap("f1_grid", 4)
    a.set_bpm(120)
    # ---- timing: pattern A, kicks on every beat
    fg.on("press", "b"); assert fg.playing
    capture()
    run_bars(2.2)
    kick_ti = fg.ids.index("kick")
    ks = sorted(set(st for k, st, g in seen if k == "f%d" % kick_ti))
    bf = a.mixer.beat_frames()
    beats = [(s - a.mixer.anchor_clock) / bf + a.mixer.anchor_beat for s in ks]
    errs = [abs(b - round(b)) * bf for b in beats]
    print("kicks", len(ks), "max err frames", max(errs))
    assert len(ks) >= 8 and max(errs) <= 1, errs
    snap("f2_playing", 1)
    # ---- swing: odd 16ths move
    fg.swing = 66; seen.clear(); run_bars(1.1)
    hat_ti = fg.ids.index("hat")
    hs = sorted(set(st for k, st, g in seen if k == "f%d" % hat_ti))
    offs = sorted(set(round(((s - a.mixer.anchor_clock) / (bf / 4.0)) % 2, 2) for s in hs))
    print("hat 16th phases with swing 66:", offs)
    assert any(abs(o - 1.32) < 0.02 for o in offs), offs
    fg.swing = 50
    # ---- queue pattern C (ratchets) at the bar line
    fg.on("press", "r1"); fg.on("press", "r1")
    assert fg.edit == 2 and fg.queued == 2
    snap("f3_queued", 1)
    seen.clear(); run_bars(2.2)
    assert fg.cur == 2 and fg.queued is None
    hat_c = sorted(st for k, st, g in seen if k == "f%d" % hat_ti)
    gaps = [b - a_ for a_, b in zip(hat_c, hat_c[1:])]
    print("hat gaps in C (frames):", sorted(set(gaps))[:6])
    assert min(gaps) <= int(bf / 4 / 3) + 2, gaps      # 3-hit ratchet inside one 16th
    snap("f4_pattern_c", 1)
    # ---- chain mode A->B->C->A
    fg.combo("b"); assert fg.song_on
    order = []
    for _ in range(4):
        run_bars(1)
        order.append(fg.cur)
    print("chain order:", order)
    assert sorted(set(order)) == [0, 1, 2], order
    fg.combo("b")
    # ---- track page: sample, pitch, volume, pan, solo
    a.input.held["r2"] = True
    fg.row = kick_ti
    s0 = fg.tracks[kick_ti]["s"]
    fg.on("press", "right"); fg.on("press", "up"); fg.on("press", "up"); fg.on("press", "y"); fg.on("press", "a")
    files = [c["file"] for c in fg.choices(kick_ti)]
    assert files.index(fg.tracks[kick_ti]["s"]) == files.index(s0) + 1 and fg.tracks[kick_ti]["pitch"] == 2
    snap("f5_trackpage", 2)
    fg.on("press", "l2"); assert fg.solo == kick_ti
    fg.on("press", "l2"); assert fg.solo is None
    a.input.held["r2"] = False
    # ---- step editing on pattern D (empty)
    fg.select_pattern(3)
    for c in (0, 4, 8, 12):
        fg.row, fg.col = kick_ti, c
        fg.on("press", "a")
    fg.col = 12; fg.on("press", "x"); fg.on("press", "y"); fg.combo("r1")
    st = fg.pats[3]["t"][kick_ti][12]
    print("step 13:", st)
    assert st == [3, 2, 75], st
    run_bars(1.2)
    snap("f6_edit_d", 1)
    a.input.held["select"] = True; snap("f7_help", 1); a.input.held["select"] = False
    # ---- export pattern A -> FORGE bank, play it in the Reactor
    fg.select_pattern(0)
    fg.combo("x")
    path = os.path.join(fm.EXPORT_DIR, "forge_A.wav")
    made.append(path)
    assert os.path.exists(path)
    bi = a.bank.forge_bank
    pad = a.bank.pad(bi, 0)
    print("forge pad:", pad["label"], pad["mode"], pad.get("gain"))
    assert pad["mode"] == "loop" and pad["label"] == "FORGE A"
    import wave
    w = wave.open(path); fr = w.getnframes(); w.close()
    assert abs(fr - 4 * SR * 60 / 120.0) < 2, fr
    fg.stop()
    a.go("reactor"); r = a.cur; r.bank = bi
    r.trigger(0); run_bars(1.5)
    assert r.state(bi, 0) == "play"
    snap("f8_reactor_forge_bank", 2)
    r.trigger(0)
    # ---- forge keeps playing in other music sections, stops in games
    a.go("forge"); fg.on("press", "b")
    a.go("xeno"); n0 = len(seen); run_bars(1)
    assert len(seen) > n0, "forge silent under xeno"
    a.go("voidrunner"); assert not fg.playing
    a.go("bridge")
    # ---- session REC from the drum machine -> Beat Duel chart
    a.go("forge"); fg.select_pattern(1); fg.on("press", "b")
    fg.combo("a"); assert a.rec.active()
    run_bars(4)
    rp = a.rec.path
    fg.combo("a")
    made += [rp + ".wav", rp + ".json"]
    meta = json.load(open(rp + ".json"))
    ln = {}
    for t, lane in meta["charts"]["normal"]:
        ln[lane] = ln.get(lane, 0) + 1
    print("session from forge:", meta["title"], meta["duration"], "notes", len(meta["charts"]["normal"]), ln)
    assert len(meta["charts"]["normal"]) >= 14 and 0 in ln and 3 in ln
    fg.stop()
    # ---- perf: mixer render with a dense pattern, and the forge frame
    fg.select_pattern(2); fg.on("press", "b"); run_bars(0.5)
    t0 = _time.perf_counter()
    nv = 0
    for _ in range(200):
        fg.tick()
        nv = max(nv, len(a.mixer.voices))
        a.mixer.render(1024)
    print("tick+render ms/1024 frames: %.3f  (budget 23 ms), max voices %d" % ((_time.perf_counter() - t0) / 200 * 1000, nv))
    t0 = _time.perf_counter(); step(120)
    print("forge ms/frame: %.2f" % ((_time.perf_counter() - t0) / 120 * 1000))
    fg.stop()
    # ---- persistence
    fg.save()
    st2 = json.load(open(fm.SAVE))
    assert st2["pats"][3]["t"][kick_ti][12] == [3, 2, 75]
    # ======================= v2 features
    # undo / redo
    before = json.dumps(fg.pats[3])
    fg.row, fg.col = kick_ti, 1; fg.edit = 3
    fg.on("press", "a"); assert fg.pats[3]["t"][kick_ti][1][0] == 2
    fg.combo("l2"); assert json.dumps(fg.pats[3]) == before, "undo failed"
    fg.combo("r2"); assert fg.pats[3]["t"][kick_ti][1][0] == 2, "redo failed"
    # pattern length 32 via R2+R1, playback wraps at 32
    a.input.held["r2"] = True
    fg.on("press", "r1"); fg.on("press", "r1")
    a.input.held["r2"] = False
    assert fg.pats[3]["len"] == 32, fg.pats[3]["len"]
    fg.col = 20; fg.on("press", "a")
    snap("f9_len32", 2)
    # builder: TRAP writes pattern E at 140 BPM, variations and dice
    fg.select_pattern(4)
    fg.on("press", "l2"); assert fg.mode == "build"
    import forge_styles
    trap = [i for i, s_ in enumerate(forge_styles.STYLES) if s_["name"] == "TRAP"][0]
    fg.style = (trap - 1) % len(forge_styles.STYLES)
    fg.on("press", "right")
    assert round(a.mixer.bpm) == 140 and not fg.pattern_empty(4), a.mixer.bpm
    k0 = [s_[0] for s_ in fg.pats[4]["t"][kick_ti][:16]]
    fg.row = kick_ti; fg.on("press", "a")
    k1 = [s_[0] for s_ in fg.pats[4]["t"][kick_ti][:16]]
    assert k0 != k1
    fg.on("press", "x")
    fg.on("press", "b"); run_bars(1.2)
    snap("f10_builder", 2)
    fg.on("press", "b")
    fg.combo("l2")                                   # undo the dice
    # arrangement: A A E B -> song mode plays in order
    fg.on("press", "l2"); assert fg.mode == "song"
    fg.song = []
    fg.edit = 0; fg.on("press", "a"); fg.on("press", "a")
    fg.on("press", "a"); fg.on("press", "up"); fg.on("press", "up"); fg.on("press", "up"); fg.on("press", "up")
    fg.on("press", "a"); fg.scol = 3
    fg.song[3] = 1
    print("song:", "".join("ABCDEFGH"[x] for x in fg.song))
    assert fg.song == [0, 0, 4, 1], fg.song
    fg.song_on = True; fg.scol = 0
    fg.on("press", "b")
    order = []
    for _ in range(4):
        run_bars(1)
        order.append(fg.cur)
    print("song order:", order)
    snap("f11_song", 2)
    fg.on("press", "b")
    # export the song -> session with chart (Beat Duel) + wav (Twin Decks)
    fg.combo("x")
    for _ in range(600):
        if not fg.exporting: break
        _time.sleep(0.02)
    base = fg.last_song
    made += [base + ".wav", base + ".json"]
    meta = json.load(open(base + ".json"))
    print("song export:", meta["title"], meta["duration"], "s, notes", len(meta["charts"]["normal"]))
    assert meta["duration"] > 6 and len(meta["charts"]["normal"]) > 10
    songs = bdm.find_songs()
    assert any(s_.get("chart_path") == base + ".json" for s_ in songs)
    # your own sounds: a wav in samples/ appears in every track's list
    os.makedirs(fm.USER_DIR, exist_ok=True)
    up = os.path.join(fm.USER_DIR, "meu clap.wav")
    shutil.copy(os.path.join(APPD, "assets", "forge", "perc_snap.wav"), up)
    made.append(up)
    fg.mode = "grid"; fg.enter()
    a.input.held["r2"] = True
    fg.row = fg.ids.index("snap")
    n = len(fg.choices(fg.row))
    for _ in range(n):
        if fg.tracks[fg.row]["s"].startswith("user:"):
            break
        fg.on("press", "right")
    a.input.held["r2"] = False
    print("user sound:", fg.tracks[fg.row]["s"], fg.sample_label(fg.row))
    assert fg.tracks[fg.row]["s"].startswith("user:") and len(fg.sample(fg.row)) > 1000
    snap("f12_user_sound", 2)
    # export with length 32 -> reactor loop of 8 beats
    fg.select_pattern(3); fg.mode = "grid"; fg.combo("x")
    made += [os.path.join(fm.EXPORT_DIR, "forge_D.wav"), os.path.join(fm.EXPORT_DIR, "forge_D.json")]
    assert a.bank.pad(a.bank.forge_bank, 3)["beats"] == 8
    print("ok")
finally:
    for p in made:
        try: os.remove(p)
        except OSError: pass
    for d_ in (fm.EXPORT_DIR, fm.USER_DIR):
        for f_ in glob.glob(os.path.join(d_, "*.json")) + glob.glob(os.path.join(d_, "*.wav")):
            if os.path.basename(f_).startswith(("forge_", "meu clap")):
                os.remove(f_)
        try: os.rmdir(d_)
        except OSError: pass
    for f in ("forge.json", "config.json", "pet.json", "bd_save.json"):
        try: os.remove(os.path.join(APPD, f))
        except OSError: pass
