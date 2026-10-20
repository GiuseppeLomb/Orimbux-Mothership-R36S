# headless test for TWIN DECKS (fake clock). Snapshots to argv[1].
import ctypes, os, sys, wave, time as _time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)


class FakeTime(object):
    def __init__(self): self.now = _time.time()
    def time(self): return self.now
    perf_counter = time     # pump() and the frame loop use the monotonic clock
    def __getattr__(self, k): return getattr(_time, k)


FT = FakeTime()
import sdl2
from PIL import Image
import engine, app as appmod, decks as dm, beatduel as bdm
from engine import audioop
engine.time = FT; appmod.time = FT; dm.time = FT; bdm.time = FT
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


def wait_peaks(d):
    for _ in range(400):
        if d.overview:
            return
        _time.sleep(0.01)


try:
    a.go("decks"); dk = a.cur
    snap("d0_empty", 3)
    dk.combo("l1"); assert dk.browse is dk.a
    titles = [it["title"] for it in dk.lib]
    print("library:", titles)
    snap("d1_browser", 2)
    dk.bsel = titles.index("NEON DRIFT"); dk.on("press", "a")
    dk.combo("r1"); dk.bsel = [it["title"] for it in dk.lib].index("MOTHERSHIP ANTHEM"); dk.on("press", "a")
    assert dk.a.wf and dk.b.wf and dk.a.bpm == 104 and dk.b.bpm == 128, (dk.a.bpm, dk.b.bpm)
    wait_peaks(dk.a); wait_peaks(dk.b)
    # ---- play A with +2% pitch: source advances 1.02x real time
    dk.a.pitch = 0.02
    dk.on("press", "l1"); assert dk.a.playing
    p0, c0 = dk.a.where(), a.mixer.clock
    step(90)
    adv = (dk.a.where() - p0) / float(dk.a.rate)
    real = (a.mixer.clock - c0) / float(SR)
    print("A advanced %.3f s in %.3f s (ratio %.4f)" % (adv, real, adv / real))
    assert abs(adv / real - 1.02) < 0.01
    # ---- nudge
    dk.on("press", "right"); assert dk.a.nudge > 0
    dk.on("release", "right"); assert dk.a.nudge == 0
    # ---- CDJ cue: playing -> cue jumps back to cue point and pauses
    dk.on("press", "l2"); assert not dk.a.playing and dk.a.where() == 0
    dk.on("press", "right"); dk.on("press", "right")       # search forward while paused
    assert abs(dk.a.where() - 0.2 * dk.a.rate) < 5, dk.a.where()
    dk.on("press", "l2"); cue = dk.a.cue                   # sets a new cue point here
    assert abs(cue - 0.2 * dk.a.rate) < 5
    dk.on("press", "l2"); assert dk.a.preview              # hold = preview
    step(30)
    assert dk.a.where() > cue
    dk.on("release", "l2"); assert not dk.a.preview and dk.a.where() == cue
    # ---- tap tempo + sync (B follows A because the crossfader is on A)
    for k in range(8):
        FT.now += 60 / 118.0; dk.combo("up")
    for k in range(8):
        FT.now += 60 / 126.0; dk.combo("x")
    print("tapped:", dk.a.bpm, dk.b.bpm)
    dk.a.pitch = 0.0
    dk.mix.xf = 0.0
    dk.combo("y")
    print("sync B pitch %.2f%% -> %.1f BPM" % (dk.b.pitch * 100, dk.b.eff_bpm()))
    assert abs(dk.b.eff_bpm() - 118.0) < 0.3
    # ---- both playing + snapshot
    dk.on("press", "l1"); dk.on("press", "r1")
    dk.mix.xf = 0.5
    step(60)
    snap("d2_mixing", 2)
    a.input.held["select"] = True; snap("d3_help", 1); a.input.held["select"] = False
    # ---- split cue: right ear = master (B only when xf=1), left = cue A
    dk.combo("a"); assert dk.mix.split
    dk.mix.xf = 1.0; dk.mix.cue_a, dk.mix.cue_b = True, False
    with a.mixer.lock:
        dk.b.playing = False
        out = dk.mix.read(4096)
    lft, rgt = audioop.tomono(out, 2, 1, 0), audioop.tomono(out, 2, 0, 1)
    print("split cue rms L %d  R %d" % (audioop.rms(lft, 2), audioop.rms(rgt, 2)))
    assert audioop.rms(lft, 2) > 300 and audioop.rms(rgt, 2) == 0
    dk.combo("a"); dk.b.playing = True
    snap("d4_split", 1)
    # ---- REC the mix (music menu: hold START, Y) -> session without notes (Beat Duel: editor)
    a.music_menu.open(); a.music_menu.on("press", "y"); a.music_menu.close()
    assert a.rec.active() and a.rec.max_s == 1200
    step(60)
    rp = a.rec.path
    a.record_toggle()
    made += [rp + ".wav", rp + ".json"]
    songs = bdm.find_songs()
    mine = [s for s in songs if s.get("chart_path") == rp + ".json"]
    assert mine and mine[0]["charts"] == {}, mine
    # ---- a user file that needs conversion (48 kHz mono) through the WARP FLOOR cache
    os.makedirs(dm.os.path.join(APPD, "music"), exist_ok=True)
    src = os.path.join(APPD, "music", "teste 48k.wav")
    w = wave.open(src, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
    import math, struct
    w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i * 0.05))) for i in range(48000 * 3))); w.close()
    made += [src, os.path.join(APPD, "music", ".cache", "teste 48k.wav.wav")]
    dk.combo("l1")
    i = [it["title"] for it in dk.lib].index("teste 48k")
    dk.bsel = i; dk.on("press", "a")
    for _ in range(300):
        step()
        if dk.a.title == "teste 48k":
            break
        _time.sleep(0.01)
    print("converted deck A:", dk.a.title, dk.a.rate, dk.a.ch)
    assert dk.a.title == "teste 48k"
    # ---- leaving for a game stops the decks
    dk.on("press", "l1"); step(5)
    a.go("trailer"); assert not dk.a.playing and not dk.b.playing
    a.go("decks")
    # ---- perf
    dk.on("press", "l1"); dk.on("press", "r1")
    t0 = _time.perf_counter()
    for _ in range(200):
        with a.mixer.lock:
            dk.mix.read(1024)
    print("deck mixer ms/1024 frames: %.3f" % ((_time.perf_counter() - t0) / 200 * 1000))
    t0 = _time.perf_counter(); step(90)
    print("decks ms/frame: %.2f" % ((_time.perf_counter() - t0) / 90 * 1000))
    print("ok")
finally:
    for p in made:
        try: os.remove(p)
        except OSError: pass
    try: os.rmdir(os.path.join(APPD, "music", ".cache"))
    except OSError: pass
    for f in ("forge.json", "config.json", "pet.json", "bd_save.json"):
        try: os.remove(os.path.join(APPD, f))
        except OSError: pass
