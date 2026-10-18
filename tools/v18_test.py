"""v1.8/1.9 checks: SISTEMA menu, trailer (live + to the end), credits crawl (from SISTEMA and from the Hangar),
music workflow order, and the 'Claude only at the end of the trailer' rule."""
import ctypes, os, re, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
for f in ("config.json", "pet.json"):
    try:
        os.remove(os.path.join(APPD, f))
    except OSError:
        pass
import sdl2
from PIL import Image
import app as appmod
import trailer as trm
import credits as crm

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v18"
os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready:
    time.sleep(0.05)


def snap(name):
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(
        os.path.join(OUT, name + ".png"))


def frames(n, real=False):
    for _ in range(n):
        a.frame(1 / 30.0)
        sdl2.SDL_RenderPresent(a.ren)
        if real:
            time.sleep(1 / 30.0)


try:
    # ---- music order is the workflow, SYSTEM has trailer + credits
    cats = dict(appmod.CATS)
    music = [it[1] for it in cats["MÚSICA"]]
    assert music[:8] == appmod.CYCLE, music
    games = [it[1] for it in cats["JOGOS"]]
    assert games == ["pet", "quiz", "voidrunner", "beatduel"], games
    system = [it[1] for it in cats["SISTEMA"]]
    assert system == ["hangar", "trailer", "credits"], system
    assert "demo" not in a.sections and "trailer" in appmod.QUIET and "credits" in appmod.QUIET
    # ---- trailer: plays live, decodes footage ahead, ends on the bridge
    tr = a.sections["trailer"]
    a.go("trailer")
    frames(45, real=True)
    assert a.cur_name == "trailer"
    tr.t0 = time.time() - (trm.B_MUSIC + 1.2) * trm.BAR     # jump into the first app
    frames(20)
    assert tr.tex.get("pulsar") and all(tr.tex["pulsar"]), "pulsar footage not decoded"
    snap("t1_pulsar")
    tr.t0 = time.time() - (trm.B_GAMES + 3.0) * trm.BAR
    frames(20)
    assert all(tr.tex.get("quiz") or [None]), "game footage not decoded"
    snap("t2_quiz")
    tr.t0 = time.time() - (trm.B_MOSAIC + 1.0) * trm.BAR
    frames(5)
    snap("t3_mosaic")
    tr.t0 = time.time() - (trm.B_FINAL + 1.5) * trm.BAR
    frames(3)
    snap("t2_end")
    alive = sum(1 for lst in tr.tex.values() for x in lst if x)
    assert alive <= 12, "footage textures are not being freed (%d alive)" % alive
    tr.t0 = time.time() - trm.END - 0.1
    frames(2)
    assert a.cur_name == "bridge", a.cur_name
    assert not tr.tex and not tr.thumbs, "trailer did not free its textures"
    a.go("trailer"); frames(2)
    a.cur.on("press", "b"); assert a.cur_name == "bridge"
    print("trailer ok")
    # ---- credits from SYSTEM: back to the bridge
    cr = a.sections["credits"]
    a.go("credits")
    frames(10)
    assert cr.crawl is not None and cr.th > 1000, "crawl texture missing"
    cr.t0 = time.time() - 30.0
    frames(5)
    snap("c1_crawl")
    s0 = cr.scroll
    cr.on("press", "up"); cr.on("press", "up")
    frames(15)
    fast = cr.scroll - s0
    cr.on("press", "down"); cr.on("press", "down"); cr.on("press", "down"); cr.on("press", "down")
    s1 = cr.scroll
    frames(15)
    slow = cr.scroll - s1
    assert fast > slow * 4, (fast, slow)
    cr.on("press", "b")
    assert a.cur_name == "bridge" and cr.crawl is None
    # ---- credits from the Hangar: back to the Hangar; runs to the end on its own
    a.go("hangar"); hg = a.cur
    hg.sel = [n for n, _ in hg.items()].index("CREDITOS")
    hg.on("press", "a")
    assert a.cur_name == "credits"
    cr.speed = 4.0
    cr.force_t = 10.0
    for i in range(30 * 120):
        cr.force_t += 1 / 30.0
        frames(1)
        if a.cur_name != "credits":
            break
        if i == 30 * 18:
            snap("c2_names")
    cr.force_t = None
    print("credits ran to the end in %.0f s of crawl time at 4x" % (i / 30.0))
    assert a.cur_name == "hangar", a.cur_name
    print("credits ok")
    # ---- 'Claude' appears only once: the last line of the trailer
    hits = []
    for root, _, files in os.walk(APPD):
        for f in files:
            if f.endswith((".py", ".txt", ".sh", ".json")):
                txt = open(os.path.join(root, f), errors="ignore").read()
                for m in re.finditer(r"(?i)claude|evw|elegant video|fairy|faeos", txt):
                    hits.append((f, m.group(0)))
    sh = os.path.join(ROOT, "ports", "Orimbux Mothership.sh")
    for m in re.finditer(r"(?i)claude|evw", open(sh).read()):
        hits.append(("launcher", m.group(0)))
    assert hits == [("trailer.py", "Claude")], hits
    print("mentions ok")
    print("ok")
finally:
    for f in ("config.json", "pet.json"):
        try:
            os.remove(os.path.join(APPD, f))
        except OSError:
            pass
