"""Renders every screen of the app (headless) for UI review.  python ui_shots.py OUTDIR [scene,scene...]
Writes OUTDIR/<scene>.png and OUTDIR/sheet_N.png contact sheets (6 per sheet)."""
import ctypes, math, os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
os.environ["VOX_FAKE"] = os.path.join(APPD, "assets", "bd", "moon_hop.wav")
SAVES = ("vr_save.json", "pet.json", "config.json", "forge.json", "earlab.json", "bd_save.json", "quiz.json",
         "missions.json")
BACKUP = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACKUP[f] = open(p, "rb").read()
        os.remove(p)
import sdl2
from PIL import Image
import app as appmod

OUT = sys.argv[1]
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["welcomed"] = False
while not a.bank.ready:
    time.sleep(0.05)
shots = []


def step(n=3):
    for _ in range(n):
        a.mixer.render(1470)
        a.frame(1 / 30.0)
        sdl2.SDL_RenderPresent(a.ren)


def snap(name, n=3):
    if ONLY and not any(name.startswith(o) for o in ONLY):
        return
    step(n)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(
        os.path.join(OUT, name + ".png"))
    shots.append(name)


def press(b):
    a.cur.on("press", b)
    a.cur.on("release", b)


def scene(name):
    return ONLY is None or any(name.startswith(o) or o.startswith(name) for o in ONLY)


try:
    a.set_bpm(128)
    if scene("intro"):
        a.go("intro"); step(60); snap("intro", 30)
    if scene("bridge"):
        a.go("bridge"); snap("bridge_welcome", 20)
        a.cfg["welcomed"] = True
        a.missions.done("pulsar_bpm"); a.missions.done("forge_play"); a.missions.toast = ("", 0)
        snap("bridge_music", 5)
        a.cur.on("press", "down"); a.cur.on("press", "down"); snap("bridge_music2", 5)
        a.cur.on("press", "r1"); snap("bridge_games", 10)
        a.cur.on("press", "r1"); snap("bridge_system", 10)
    if scene("help"):
        a.go("forge"); a.input.held["select"] = True; a.sel_t0 = time.time() - 1
        snap("help_overlay", 3)
        a.input.held.pop("select", None)
        a.help.tutorial = "reactor"; a.go("reactor"); a.help.tutorial = "reactor"; snap("help_tutorial", 3)
        a.help.tutorial = None
    if scene("musicmenu") and hasattr(a, "music_menu"):
        a.go("forge"); a.sections["forge"].on("press", "b"); step(5)
        a.music_menu.open(); snap("musicmenu", 5); a.music_menu.close()
        a.sections["forge"].stop()
    if scene("pulsar"):
        a.go("pulsar"); snap("pulsar", 20)
    if scene("forge"):
        a.go("forge"); fg = a.cur
        fg.on("press", "b"); snap("forge_grid", 20)
        fg.on("press", "l2"); snap("forge_build", 10)
        fg.on("press", "l2"); snap("forge_song", 10)
        fg.on("press", "l2"); fg.stop()
    if scene("abductor"):
        a.go("abductor"); ab = a.cur
        snap("abductor_rec", 10)
        ab.chop.load_path(os.path.join(APPD, "assets", "bd", "mothership_anthem.wav"), "MOTHERSHIP ANTHEM")
        while ab.chop.loading:
            time.sleep(0.02)
        ab.panel = "cut"; snap("abductor_cut", 10)
        ab.panel = "play"; snap("abductor_play", 10)
    if scene("reactor"):
        a.go("reactor"); r = a.cur
        r.trigger(0); r.trigger(5); step(40); snap("reactor", 10)
        a.sections["reactor"].stop_all() if hasattr(a.sections["reactor"], "stop_all") else None
    if scene("xeno"):
        a.go("xeno"); xs = a.cur
        xs.on("press", "up"); a.input.held["up"] = time.time(); snap("xeno", 10)
        xs.on("release", "up"); a.input.held.pop("up", None)
    if scene("vox"):
        a.go("vox"); vx = a.cur; snap("vox_off", 5)
        vx.on("press", "start") if not hasattr(a, "music_menu") else vx.toggle_mic()
        step(20); snap("vox_live", 10); vx.stop()
    if scene("decks"):
        a.go("decks"); dk = a.cur; snap("decks_empty", 5)
        dk.combo("l1"); snap("decks_browser", 5)
        titles = [it["title"] for it in dk.lib]
        dk.bsel = titles.index("NEON DRIFT"); dk.on("press", "a")
        dk.combo("r1"); dk.bsel = titles.index("MOTHERSHIP ANTHEM"); dk.on("press", "a")
        step(10); dk.on("press", "l1"); dk.on("press", "r1"); step(30); snap("decks_play", 10); dk.stop_all()
    if scene("warp"):
        a.go("warp"); snap("warp", 10)
    if scene("earlab") or scene("quiz"):
        key = "quiz" if "quiz" in a.sections else "earlab"
        a.go(key); snap(key + "_menu", 10)
        e = a.cur
        if key == "earlab":
            e.state = "menu"; e.msel = 0; e.on("press", "a"); snap("earlab_q", 10)
        else:
            e.start_game(); snap("quiz_q1", 20)
            e.on("press", "a"); snap("quiz_answer", 10)
    if scene("pet"):
        import pet as petmod
        pt = a.sections["pet"]
        a.go("pet")
        pt.tick(petmod.HATCH_AT + 10); pt.process_events(); step(5)
        pt.on("press", "a"); step(10)
        pt.p["age"] = petmod.ADULT_AT + 5; pt.tick(1); pt.process_events(); pt.finish_event()
        pt.p.update({"form": "glorpo", "name": "MOMO", "hue": 0.3})
        snap("pet", 10)
    if scene("voidrunner"):
        vr = a.sections["voidrunner"]
        a.go("voidrunner"); vr.save_d["unlocked"] = 3; vr.world = 1; snap("voidrunner_menu", 10)
        run = vr.start_now(1, [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0])
        run.die = lambda why: None
        for k in range(200):
            a.input.axes["lx"], a.input.axes["ly"] = math.cos(k * 0.05), math.sin(k * 0.05)
            step(1)
            if run.state == "levelup":
                run.choose()
            if run.state == "chest":
                run.chest["t0"] -= 9; run.close_chest()
        run.hx, run.hy = run.px - 190, run.py + 70
        run.banner = ("", 0, "")
        snap("voidrunner_play", 2)
        run.offer(); snap("voidrunner_levelup", 2); run.choose()
        run.open_chest(1); run.chest["t0"] -= 9; snap("voidrunner_chest", 2); run.close_chest()
        vr.state = "pause"; snap("voidrunner_pause", 2); vr.state = "run"
        a.input.axes["lx"] = a.input.axes["ly"] = 0.0
        vr.leave()
    if scene("beatduel"):
        a.go("beatduel"); bd = a.cur; snap("beatduel_menu", 10)
        bd.sel, bd.diff, bd.mode = 0, 1, __import__("beatduel").MODES.index("VS CPU")
        bd.on("press", "a"); step(120); snap("beatduel_play", 5)
        bd.on("press", "start")
    if scene("hangar"):
        a.go("hangar"); snap("hangar", 5)
        hg = a.cur
        hg.sel = [n for n, _ in hg.items()].index("GRAVACOES") if "GRAVACOES" in [n for n, _ in hg.items()] else 0
    if scene("credits"):
        cr = a.sections["credits"]; cr.force_t = 30.0; a.go("credits"); cr.scroll = 600; snap("credits", 2)
        cr.force_t = None
finally:
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACKUP:
            open(p, "wb").write(BACKUP[f])
for i in range(0, len(shots), 6):
    grp = shots[i:i + 6]
    sheet = Image.new("RGB", (3 * 640, 2 * 480), (0, 0, 0))
    for j, nm in enumerate(grp):
        sheet.paste(Image.open(os.path.join(OUT, nm + ".png")), ((j % 3) * 640, (j // 3) * 480))
    sheet.resize((1440, 720), Image.LANCZOS).save(os.path.join(OUT, "sheet_%d.png" % (i // 6)))
print("shots:", shots)
