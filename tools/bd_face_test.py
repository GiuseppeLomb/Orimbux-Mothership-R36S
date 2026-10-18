"""Beat Duel FACE TO FACE: P1 (d-pad end) and P2 (buttons end) each see their half upright, notes travel
from the centre to each player. Checks key mapping, scoring, the geometry of the turned halves, results."""
import ctypes, os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "bd_save.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import sdl2
from PIL import Image
import app as appmod
import beatduel as bdm

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bd_face"
os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["welcomed"] = True


def grab(name):
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    im = Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB")
    im.save(os.path.join(OUT, name + ".png"))
    return im


try:
    # mapping: lanes left..right as each player sees them
    assert bdm.P1_FACE == {"up": 0, "left": 1, "right": 2, "down": 3}
    assert bdm.P2_FACE == {"b": 0, "a": 1, "y": 2, "x": 3}
    a.go("beatduel"); bd = a.cur
    bd.sel = [i for i, s in enumerate(bd.songs) if s["title"] == "NEON DRIFT"][0]
    bd.diff, bd.mode = 1, bdm.MODES.index(bdm.FACE)
    a.frame(1 / 30.0)
    grab("f0_select")
    bd.on("press", "a")
    m = bd.match
    assert bd.state == "play" and m.mode == bdm.FACE and m.players[0].keys is bdm.P1_FACE
    inv1 = dict((v, k) for k, v in bdm.P1_FACE.items())
    inv2 = dict((v, k) for k, v in bdm.P2_FACE.items())
    # play: P1 hits everything on time, P2 only every other note
    clock = [0.0]
    m.now = lambda: clock[0]
    notes = m.players[0].notes
    shot_at = notes[min(30, len(notes) - 1)][0] - 0.35
    shot_done = False
    for n in list(notes):
        clock[0] = n[0]
        bd.update(1 / 30.0)
        m.judge_press(m.players[0], n[1]) if False else bd.on("press", inv1[n[1]])
        bd.on("release", inv1[n[1]])
        k = notes.index(n)
        if k % 2 == 0:
            bd.on("press", inv2[n[1]])
            bd.on("release", inv2[n[1]])
        if not shot_done and n[0] >= shot_at:
            clock[0] = shot_at
            a.frame(1 / 30.0)
            im = grab("f1_play")
            shot_done = True
            clock[0] = n[0]
    p1, p2 = m.players
    print("P1", p1.score, p1.count, "| P2", p2.score, p2.count)
    assert p1.count["perfect"] >= len(notes) * 0.95, p1.count
    assert p2.score < p1.score
    # geometry: P1's receptors sit at P1's edge (left), P2's at the right edge, both halves upright-for-them
    px = im.load()
    left_lit = sum(1 for y in range(100, 380) for x in range(0, 70) if sum(px[x, y]) > 300)
    centre_lit = sum(1 for y in range(100, 380) for x in range(250, 310) if sum(px[x, y]) > 300)
    right_lit = sum(1 for y in range(100, 380) for x in range(570, 640) if sum(px[x, y]) > 300)
    print("bright pixels: left edge %d, centre %d, right edge %d" % (left_lit, centre_lit, right_lit))
    assert left_lit > 200 and right_lit > 200
    clock[0] = m.end_t + 1
    bd.update(1 / 30.0)
    assert bd.state == "results"
    a.frame(1 / 30.0)
    grab("f2_results")
    bd.on("press", "a")
    assert bd.state == "select" and bd.result.views is None
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
sheet = Image.new("RGB", (3 * 640, 480))
for j, nm in enumerate(("f0_select", "f1_play", "f2_results")):
    sheet.paste(Image.open(os.path.join(OUT, nm + ".png")), (j * 640, 0))
sheet.resize((1440, 360), Image.LANCZOS).save(os.path.join(OUT, "sheet.png"))
