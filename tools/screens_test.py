"""Draws ~40 screens of the app deterministically (fixed clock, fixed random seed, audio rendered in fixed steps)
and prints a SHA-1 of the pixels of each one. Run it on two checkouts and compare the output to prove that a change
(an optimisation, a clean-up) left every screen identical, byte for byte.
  python3 tools/screens_test.py [APPDIR] [PNGDIR]"""
import ctypes
import hashlib
import os
import random
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
PNG = sys.argv[2] if len(sys.argv) > 2 else None
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "forge.json", "quiz.json", "vr_save.json", "bd_save.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
CLOCK = [1700000000.0]
real_sleep = time.sleep
time.time = lambda: CLOCK[0]
time.perf_counter = lambda: CLOCK[0]
random.seed(11)
import sdl2  # noqa: E402
import app as appmod  # noqa: E402

out = []


def frame(n=1):
    for _ in range(n):
        CLOCK[0] += 1 / 30.0
        a.mixer.render(1470)
        a.frame(1 / 30.0)


def shot(name, n=2):
    frame(n)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    h = hashlib.sha1(buf.raw).hexdigest()[:16]
    out.append((name, h))
    print("%-28s %s" % (name, h))
    if PNG:
        from PIL import Image
        os.makedirs(PNG, exist_ok=True)
        Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).save(os.path.join(PNG, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


try:
    a = appmod.App(headless=True)
    while not a.bank.ready:
        real_sleep(0.05)
    a.mixer.pump = lambda: None                 # audio advances in fixed steps (frame())
    random.seed(12)
    with a.mixer.lock:
        a.mixer.streams = []
    shot("intro", 40)
    a.go("bridge")
    shot("bridge_welcome", 10)
    a.cfg["welcomed"] = True
    a.cfg["seen"] = list(__import__("help").HELP)
    shot("bridge_music", 10)
    a.cur.on("press", "right")
    shot("bridge_games", 10)
    a.cur.on("press", "right")
    shot("bridge_system", 10)
    for name in ("pulsar", "abductor", "xeno", "vox", "warp", "decks", "hangar"):
        a.go(name)
        shot(name, 5)
    a.go("reactor")
    a.sections["reactor"].trigger(0)
    a.sections["reactor"].trigger(4)
    shot("reactor_loops", 20)
    fg = a.sections["forge"]
    a.go("forge")
    fg.play()
    shot("forge_grid_playing", 20)
    fg.mode = "build"
    shot("forge_build", 5)
    fg.mode = "song"
    fg.on("press", "a")
    shot("forge_song", 5)
    fg.mode = "grid"
    fg.stop()
    ab = a.sections["abductor"]
    a.go("abductor")
    ab.chop.load_path(os.path.join(APPD, "assets", "bd", "neon_drift.wav"), "NEON DRIFT")
    while ab.chop.loading:
        real_sleep(0.02)
    ab.panel = "cut"
    shot("abductor_cut", 5)
    ab.panel = "play"
    shot("abductor_play", 5)
    xs = a.sections["xeno"]
    a.go("xeno")
    xs.note_on("left")
    xs.note_on("a")
    shot("xeno_notes", 8)
    xs.leave()
    pt = a.sections["pet"]
    a.go("pet")
    shot("pet_egg", 5)
    import pet as petmod
    pt.tick(petmod.HATCH_AT + 10)
    pt.process_events()
    shot("pet_name", 5)
    pt.on("press", "a")
    pt.p.update({"full": 20, "poops": 2})
    shot("pet_baby_hungry", 10)
    pt.mode = "feed"
    shot("pet_feed", 3)
    pt.mode = "stats"
    shot("pet_stats", 3)
    pt.mode = "memorial"
    shot("pet_memorial", 3)
    pt.mode = "home"
    q = a.sections["quiz"]
    a.go("quiz")
    shot("quiz_menu", 5)
    q.start_game()
    shot("quiz_question", 5)
    q.use("50")
    q.use("poll")
    shot("quiz_lifelines", 5)
    q.state = "party_setup"
    shot("quiz_party_setup", 5)
    q.party_start()
    shot("quiz_party_turn", 5)
    vr = a.sections["voidrunner"]
    a.go("voidrunner")
    shot("vr_menu", 5)
    vr.save_d["unlocked"] = 6
    song = [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0]
    r = vr.start_now(2, song)
    for _ in range(150):
        CLOCK[0] += 1 / 30.0
        a.mixer.render(1470)
        r.update(1 / 30.0)
        if r.state == "levelup":
            r.csel = 0
            r.choose()
    shot("vr_run", 1)
    vr.state = "pause"
    shot("vr_pause", 1)
    vr.leave()
    bd = a.sections["beatduel"]
    a.go("beatduel")
    shot("beatduel_select", 5)
    bd.mode = 1
    bd.on("press", "a")
    for _ in range(90):
        CLOCK[0] += 1 / 30.0
        a.mixer.render(1470)
        a.frame(1 / 30.0)
    shot("beatduel_face_to_face", 1)
    bd.on("press", "start")
    bd.mode = 0
    bd.on("press", "a")
    for _ in range(90):
        CLOCK[0] += 1 / 30.0
        a.mixer.render(1470)
        a.frame(1 / 30.0)
    shot("beatduel_duel", 1)
    bd.on("press", "start")
    a.go("hangar")
    hg = a.cur
    hg.sel = [n for n, _ in hg.items()].index("GRAVACOES")
    hg.on("press", "a")
    shot("hangar_recordings", 3)
    hg.on("press", "b")
    tr = a.sections["trailer"]
    tr.force_t = 0.0
    a.go("trailer")
    for t in (3.0, 9.0, 20.0, 31.0, 45.0, 70.0):
        tr.force_t = t
        tr.update(1 / 30.0)
        shot("trailer_%02d" % t, 1)
    cr = a.sections["credits"]
    cr.force_t = 0.0
    a.go("credits")
    for t in (2.0, 30.0, 60.0):
        cr.force_t = t
        cr.update(1 / 30.0)
        shot("credits_%02d" % t, 1)
    a.go("reactor")
    a.input.held["select"] = True
    a.sel_t0 = CLOCK[0] - 1.0
    shot("help_reactor", 2)
    a.input.held["select"] = False
    a.help_shown = False
    a.music_menu.open()
    shot("music_menu", 3)
    a.music_menu.close()
    a.cfg["seen"] = []
    a.go("pulsar")
    shot("tutorial_pulsar", 3)
    a.help.dismiss()
    a.missions.toast = ("✓ Escolhe o tempo", CLOCK[0])
    shot("mission_toast", 2)
    print("%d screens, combined %s" % (len(out), hashlib.sha1("".join(h for _, h in out).encode()).hexdigest()[:16]))
finally:
    for f in SAVES:
        try:
            os.remove(os.path.join(APPD, f))
        except OSError:
            pass
        if f in BACK:
            open(os.path.join(APPD, f), "wb").write(BACK[f])
