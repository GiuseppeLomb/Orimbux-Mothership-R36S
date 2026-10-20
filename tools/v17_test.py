# v1.7 checks: first-visit cards, hold-SELECT help everywhere (no accidental "back"), GRAVACOES manager,
# Comet Chop undo/redo, Twin Decks filter. Snapshots to argv[1].
import ctypes, os, shutil, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)
for f in ("config.json", "pet.json", "forge.json", "quiz.json"):
    try: os.remove(os.path.join(APPD, f))
    except OSError: pass
import sdl2
from PIL import Image
import engine, app as appmod, help as hm
from engine import audioop
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
while not a.bank.ready: time.sleep(0.05)
queue = []


def fake_poll():
    a.input.events = []
    while queue:
        kind, b = queue.pop(0)
        (a.input._press if kind == "press" else a.input._release)(b)


a.input.poll = fake_poll


def frame(n=1):
    for _ in range(n):
        a.handle()
        a.frame(1 / 30.0)


def snap(name, frames=1):
    frame(frames)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


made = []
try:
    # ---- first visit: tutorial card, the first button only closes it
    a.go("reactor")
    assert a.help.tutorial == "reactor"
    snap("h0_tutorial_reactor", 2)
    queue.append(("press", "up")); frame(); queue.append(("release", "up")); frame()
    assert a.help.tutorial is None and "reactor" in a.cfg["seen"]
    assert not [v for v in a.mixer.voices if v.group == "reactor"], "the closing press must not play a pad"
    # second visit: no card
    a.go("bridge"); a.go("reactor"); assert a.help.tutorial is None
    # ---- hold SELECT: help overlay, and releasing does NOT go back to the bridge
    queue.append(("press", "select")); frame()
    a.sel_t0 = time.time() - 1.0
    snap("h1_help_reactor", 1)
    assert a.help_shown
    queue.append(("release", "select")); frame()
    assert a.cur_name == "reactor", a.cur_name
    # quick tap still goes back
    queue.append(("press", "select")); frame(); queue.append(("release", "select")); frame()
    assert a.cur_name == "bridge", a.cur_name
    # ---- every section has help; draw each overlay
    a.cfg["seen"] = list(hm.HELP)
    for name in ("forge", "decks", "abductor", "quiz", "vox", "beatduel", "voidrunner", "pet", "hangar", "xeno",
                 "pulsar", "warp", "trailer", "credits", "bridge"):
        a.go(name)
        key = hm.key_for(a)
        assert key in hm.HELP, key
        a.input.held["select"] = True; a.sel_t0 = time.time() - 1.0
        if name in ("forge", "decks", "abductor", "beatduel"):
            snap("h2_help_%s" % key, 1)
        else:
            frame()
        a.input.held["select"] = False; a.help_shown = False
    a.go("forge"); a.cur.mode = "build"
    a.input.held["select"] = True; a.sel_t0 = time.time() - 1.0
    snap("h3_help_forge_build", 1)
    a.input.held["select"] = False; a.help_shown = False
    # first-visit card for a forge mode
    a.cfg["seen"] = [k for k in a.cfg["seen"] if k != "forge_song"]
    a.cur.mode = "build"; a.cur.set_mode(1)
    assert a.help.tutorial == "forge_song"
    snap("h4_tutorial_forge_song", 1)
    a.help.dismiss()
    # ---- GRAVACOES manager
    rd = os.path.join(APPD, "recordings")
    for i in range(3):
        p = os.path.join(rd, "rec_2026010%d_120000.wav" % i)
        shutil.copy(os.path.join(APPD, "assets", "bd", "moon_hop.wav"), p)
        made.append(p)
    a.go("hangar"); hg = a.cur
    hg.sel = [n for n, _ in hg.items()].index("GRAVACOES")
    hg.on("press", "a"); assert hg.files is not None
    n0 = len(hg.files.items)
    snap("h5_recordings", 2)
    hg.on("press", "a"); assert hg.files.playing
    hg.on("press", "y"); assert len(hg.files.items) == n0          # first Y only asks
    hg.on("press", "y")
    print("recordings: %d -> %d" % (n0, len(hg.files.items)))
    assert len(hg.files.items) == n0 - 1
    hg.on("press", "b"); assert hg.files is None
    hg.sel = [n for n, _ in hg.items()].index("BUFFER AUDIO")
    hg.on("press", "a"); assert a.cfg["buffer"] == 512
    snap("h6_hangar", 2)
    hg.on("press", "a"); assert a.cfg["buffer"] == 1024
    # ---- Comet Chop undo/redo
    a.go("abductor"); ab = a.cur
    ab.chop.load_path(os.path.join(APPD, "assets", "bd", "neon_drift.wav"), "NEON DRIFT")
    while ab.chop.loading: time.sleep(0.02)
    ab.panel = "cut"; ch = ab.chop
    ch.sel = 2; m0 = list(ch.marks)
    for _ in range(5): ch.on("cut", "press", "right")
    assert ch.marks != m0
    ch.on("cut", "press", "x"); assert ch.n == 16
    ab.combo("l2"); assert ch.n == 8 and ch.marks != m0
    ab.combo("l2"); assert ch.marks == m0, "undo of the 5 moves (one group) failed"
    ab.combo("r2"); assert ch.marks != m0
    print("chop undo/redo ok")
    # ---- Twin Decks filter
    dk = a.sections["decks"]
    x = engine.load_wav(os.path.join(APPD, "assets", "bd", "pixel_rush.wav"))[4000000:4000000 + 4096 * 8]
    res = {}
    for v in (0, -6, 6):
        f = __import__("decks").DJFilter(); f.pos = v
        out = b"".join(f.process(x[i:i + 4096]) for i in range(0, len(x), 4096))
        res[v] = audioop.rms(out, 2)
    print("filter rms: off %d  LP6 %d  HP6 %d" % (res[0], res[-6], res[6]))
    assert res[-6] < res[0] and res[6] < res[0]
    a.go("decks"); dk.mix.fa.pos = -4.0
    queue.append(("press", "l3")); frame(); queue.append(("release", "l3")); frame()
    assert dk.mix.fa.pos == 0.0
    print("ok")
finally:
    for p in made:
        try: os.remove(p)
        except OSError: pass
    for f in ("config.json", "pet.json", "forge.json", "quiz.json"):
        try: os.remove(os.path.join(APPD, f))
        except OSError: pass
