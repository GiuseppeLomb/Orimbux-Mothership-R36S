# headless test for COMET CHOP (inside ABDUCTOR). Snapshots to argv[1].
import ctypes, json, os, sys, time as _time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)
import sdl2
from PIL import Image
import engine, app as appmod, chop as cm
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
made = []
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready: _time.sleep(0.05)
SR = engine.SR


def snap(name, frames=2):
    for _ in range(frames): a.frame(1 / 30.0)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


try:
    a.set_bpm(118)
    a.go("abductor"); ab = a.cur
    print("has_mic:", ab.has_mic)
    snap("c0_rec", 3)
    ab.on("press", "r1"); assert ab.panel == "cut"
    snap("c1_empty", 2)
    ab.on("press", "a"); ch = ab.chop; assert ch.browse
    snap("c2_browser", 2)
    ch.bsel = [it["title"] for it in ch.lib].index("NEON DRIFT")
    ab.on("press", "a")
    for _ in range(500):
        if ch.data: break
        _time.sleep(0.01)
    assert ch.data and ch.n == 8
    beat = SR * 60.0 / 118
    print("window %.3f beats, marks %d" % ((ch.end - ch.start) / beat, len(ch.marks)))
    assert abs((ch.end - ch.start) / beat - 8) < 0.01
    # move the window start to bar 3 (where the drums are), 1 bar, 16 slices
    ch.sel = 0
    ch.start = int(beat * 8); ch.end = ch.start + 1
    ch.bars = 4; ch.on("cut", "press", "l2")       # 4 -> 1 bar
    assert ch.bars == 1 and abs((ch.end - ch.start) - beat * 4) < 2
    ch.on("cut", "press", "x"); assert ch.n == 16
    ch.on("cut", "press", "x"); ch.on("cut", "press", "x"); assert ch.n == 8
    ch.sel = 3; before = ch.marks[2]
    ch.on("cut", "press", "right")
    assert ch.marks[2] - before == SR * 10 // 1000
    a.input.held["r2"] = True; ch.on("cut", "press", "left"); a.input.held["r2"] = False
    assert ch.marks[2] - before == SR * 9 // 1000
    ch.on("cut", "press", "y")
    vs = [v for v in a.mixer.voices if v.group == "chop"]
    s, e = ch.slice_bounds(3)
    assert vs and abs(len(vs[-1].data) // 4 - (e - s)) < 2
    snap("c3_cut", 3)
    # play panel: choke keeps one slice at a time
    ab.on("press", "r1"); assert ab.panel == "play"
    for b in ("up", "left", "right"):
        ab.on("press", b)
    assert len([v for v in a.mixer.voices if v.group == "chop"]) == 1
    snap("c4_play", 2)
    ab.combo("y"); assert not ch.choke
    for b in ("down", "x"):
        ab.on("press", b)
    assert len([v for v in a.mixer.voices if v.group == "chop"]) >= 2
    ab.combo("y")
    # export -> Loop Reactor bank CHOP
    ab.combo("x")
    for k in range(8):
        made.append(os.path.join(cm.EXPORT_DIR, "slice_%d.wav" % (k + 1)))
    bi = a.bank.chop_bank
    print("chop bank:", [a.bank.pad(bi, k)["label"] for k in range(8)])
    assert a.bank.pad(bi, 0)["label"] == "FATIA 1" and os.path.exists(made[0])
    # finger drumming REC -> Beat Duel chart
    ab.combo("a"); assert a.rec.active()
    for b in ("up", "right", "down", "left", "x", "a"):
        for _ in range(6): a.frame(1 / 30.0)
        ab.on("press", b)
    for _ in range(10): a.frame(1 / 30.0)
    rp = a.rec.path
    ab.combo("a")
    made += [rp + ".wav", rp + ".json"]
    meta = json.load(open(rp + ".json"))
    print("chop session lanes:", [l for _, l in meta["charts"]["normal"]])
    assert sorted(l for _, l in meta["charts"]["normal"]) == [0, 1, 2, 2, 3, 3]   # same-clock presses in headless
    a.go("reactor"); r = a.cur; r.bank = bi; r.trigger(0)
    snap("c5_reactor_chop", 3)
    print("ok")
finally:
    for p in made:
        try: os.remove(p)
        except OSError: pass
    try: os.rmdir(cm.EXPORT_DIR)
    except OSError: pass
    for f in ("config.json", "pet.json", "forge.json", "earlab.json"):
        try: os.remove(os.path.join(APPD, f))
        except OSError: pass
