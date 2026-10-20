"""Captures real footage of every app for the trailer: drives each section headless into a lively state
and grabs a few frames. Output: tools/build/trailer/<app>_<n>.png  (+ contact sheet)."""
import ctypes, math, os, random, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
os.environ["VOX_FAKE"] = os.path.join(APPD, "assets", "bd", "moon_hop.wav")
SAVES = ("vr_save.json", "pet.json", "config.json", "forge.json", "quiz.json", "bd_save.json", "bd_scores.json")
BACKUP = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACKUP[f] = open(p, "rb").read()
        os.remove(p)
import sdl2
from PIL import Image
import app as appmod

OUT = os.path.join(ROOT, "tools", "build", "trailer")
os.makedirs(OUT, exist_ok=True)
random.seed(7)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["scanlines"] = False
a.cfg["welcomed"] = True
while not a.bank.ready:
    time.sleep(0.05)
ONLY = sys.argv[1].split(",") if len(sys.argv) > 1 else None


def grab():
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    return Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB")


def step(n=1, real=True):
    for _ in range(n):
        a.missions.toast = ("", 0.0)            # no mission ticks over the footage
        a.mixer.render(1470)
        a.frame(1 / 30.0)
        sdl2.SDL_RenderPresent(a.ren)
        if real:
            time.sleep(1 / 30.0)


def shoot(name, n=6, gap=14, act=None, real=True):
    """n frames, gap frames apart; act(i) runs before frame i"""
    frames = []
    for i in range(n):
        if act:
            act(i)
        step(gap, real)
        frames.append(grab())
    for i, im in enumerate(frames):
        im.save(os.path.join(OUT, "%s_%d.png" % (name, i)))
    print("captured", name)


def press(b, hold=False):
    a.cur.on("press", b)
    if not hold:
        a.cur.on("release", b)


def want(name):
    return ONLY is None or name in ONLY


try:
    # 1 PULSAR: tap tempo + metronome running
    if want("pulsar"):
        a.go("pulsar")
        a.set_bpm(128)
        if not a.mixer.metro:
            press("b")
        shoot("pulsar")

    # 2 BEAT FORGE: builder dice -> grid playing
    if want("forge"):
        a.set_bpm(128)
        a.go("forge"); fg = a.cur
        fg.on("press", "l2")
        for _ in range(3):
            fg.on("press", "x")
        fg.on("press", "l2"); fg.on("press", "l2")
        if fg.mode != "grid":
            fg.mode = "grid"
        if not fg.playing:
            fg.on("press", "b")
        fg.row, fg.col = 2, 5
        shoot("forge", act=lambda i: setattr(fg, "col", (fg.col + 3) % 16))
        fg.on("press", "b")

    # 3 ABDUCTOR / COMET CHOP: slices playing
    if want("abductor"):
        a.go("abductor"); ab = a.cur
        ab.chop.load_path(os.path.join(APPD, "assets", "bd", "mothership_anthem.wav"), "MOTHERSHIP ANTHEM")
        while ab.chop.loading:
            time.sleep(0.02)
        ab.panel = "cut"
        step(5)
        ab.panel = "play" if hasattr(ab, "panel") else ab.panel
        keys = ["left", "up", "right", "down", "x", "y", "a", "b"]
        def chopact(i):
            step(11)
            for j in range(1 + i % 2):
                ab.chop.on(ab.panel, "press", keys[(i * 3 + j * 5) % 8])
        ab.chop.msg = ("", 0.0)
        shoot("abductor", gap=3, act=chopact)

    # 4 LOOP REACTOR: loops on air + one-shots
    if want("reactor"):
        a.go("reactor"); r = a.cur
        a.set_bpm(128)
        for i in (0, 2, 5):
            r.trigger(i)
        step(40, False)
        shoot("reactor", act=lambda i: r.trigger((i * 3 + 1) % 8))

    # 5 XENO SYNTH: chords held
    if want("xeno"):
        a.go("xeno"); xs = a.cur
        seq = [("left", "right"), ("up", "a"), ("down", "y"), ("right", "b"), ("x", "up"), ("left", "a")]

        def play(i):
            for b in appmod.XENO_KEYS:
                xs.on("release", b)
            for b in seq[i % len(seq)]:
                xs.on("press", b)
                a.input.held[b] = time.time()
        shoot("xeno", act=play)
        for b in appmod.XENO_KEYS:
            xs.on("release", b)
            a.input.held.pop(b, None)

    # 6 VOX NEBULA: fake mic singing through effects
    if want("vox"):
        a.go("vox"); vx = a.cur
        vx.toggle_mic()
        step(30)
        vx.msg = ("", 0.0)
        import vox as vm
        fxk = [k for _, k in vm.EFFECTS]
        shoot("vox", act=lambda i: vx.on("press", fxk[i % len(fxk)]) if i % 2 else None)
        vx.stop()

    # 7 TWIN DECKS: two songs mixing
    if want("decks"):
        a.go("decks"); dk = a.cur
        dk.combo("l1")
        titles = [it["title"] for it in dk.lib]
        dk.bsel = titles.index("NEON DRIFT"); dk.on("press", "a")
        dk.combo("r1"); dk.bsel = titles.index("MOTHERSHIP ANTHEM"); dk.on("press", "a")
        step(10, False)
        dk.on("press", "l1"); dk.on("press", "r1")
        step(60, False)
        dk.msg = ("", 0.0)
        shoot("decks", act=lambda i: setattr(dk.mix.fa, "pos", -3.0 + i) if hasattr(dk.mix, "fa") else None)
        dk.stop_all()

    # 8 WARP FLOOR: music + visuals
    if want("warp"):
        import shutil
        md = os.path.join(APPD, "music")
        made_md = not os.path.isdir(md)
        os.makedirs(md, exist_ok=True)
        tmp_song = os.path.join(md, "Neon Drift.wav")
        shutil.copy(os.path.join(APPD, "assets", "bd", "neon_drift.wav"), tmp_song)
        a.go("warp"); w = a.cur
        w.scan()
        for _ in range(450):
            if w.cur is not None and not w.cur.done:
                break
            if w.tracks and w.cur is None and _ % 30 == 0:
                press("a")
            step(1)
        print("warp cur:", w.cur, w.msg if hasattr(w, "msg") else "")
        try:
            w.cur.seek(38.0)
        except Exception as ex:
            print("seek failed", ex)

        def wact(i):
            w.msg = ""
        for _ in range(45):
            w.msg = ""
            step(1)
        shoot("warp", gap=12, act=wact)
        press("b")
        step(5)
        os.remove(tmp_song)
        shutil.rmtree(os.path.join(md, ".cache"), ignore_errors=True)
        if made_md:
            shutil.rmtree(md, ignore_errors=True)

    # 10 DISCO VOADOR: a question, the answer locked, the reveal, the climb
    if want("quiz"):
        a.go("quiz"); q = a.cur
        random.seed(11)
        q.start_game()
        for _ in range(3):                     # climb a little so the ladder shows progress
            q.cur = q.q["answer"]; q.on("press", "a"); q.on("press", "a")
            q.t0 -= 3; q.update(0.1); q.t0 -= 3; q.update(0.1); q.t0 -= 3; q.update(0.1)
        step(10)

        def party_setup():
            P = q.party
            P["n"], P["rounds"], P["diff"] = 6, 1, 0
            P["names"][:6] = ["ANA", "RUI", "MIGUEL", "INÊS", "TIAGO", "SOFIA"]
            q.party_start()
            for i in range(6):                     # round 1: a few right answers, so the table has points
                q.party_ask()
                q.t0 -= 2.0 + i
                q.party_lock(q.q["answer"] if i in (0, 2, 3, 5) else (q.q["answer"] + 1) % 4)
                q.party_next()
            q.party_after_board()                   # round 2, player 1

        def qact(i):
            if i == 1:
                q.use("50")
            if i == 2:
                q.cur = q.q["answer"]; q.on("press", "a")          # locked at once: suspense
            if i == 3:                                             # FESTA: 6 players
                party_setup()
                q.party_ask()
                q.cur = q.q["answer"]
            if i == 4:
                q.party_lock(q.q["answer"])
            if i == 5:
                q.party_next()
                for k in range(5):
                    q.party_ask(); q.party_lock(q.q["answer"] if k % 2 else None); q.party_next()
        shoot("quiz", act=qact)

    # 10 XENO PET: adult pet at home
    if want("pet"):
        import pet as petmod
        pet = a.sections["pet"]
        a.go("pet")
        pet.tick(petmod.HATCH_AT + 10); pet.process_events(); step(5)
        pet.on("press", "a"); step(10)
        pet.p["age"] = petmod.ADULT_AT + 5; pet.tick(1); pet.process_events(); pet.finish_event()
        pet.p.update({"form": "glorpo", "name": "MOMO", "hue": 0.3, "full": 70, "happy": 90})
        step(10)

        def petact(i):
            if i == 1:
                pet.sel = 0; pet.on("press", "a")
            if i == 2:
                pet.on("press", "a")
        shoot("pet", act=petact)

    # 11 VOID RUNNER: the Mix of the ship, world 4, evolved weapons, O GRAVE on screen and a drop hitting
    if want("voidrunner"):
        vr = a.sections["voidrunner"]
        a.go("voidrunner")
        vr.save_d["unlocked"] = 6
        vr.save_d["seen_en"] = sorted(__import__("voidrunner").TYPES)
        run = vr.start_now(3, [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0])
        run.weapons = {"bolt": 5, "beam": 5, "aura": 4, "drone": 3, "comet": 3}
        run.evo = {"bolt", "beam"}
        run.passive = {"haste": 2, "area": 2, "speed": 3, "regen": 2}
        run.lv = 18
        drop = run.tl.drops[4] if len(run.tl.drops) > 4 else run.tl.drops[-1]
        run.mt = run.t = drop - 7.5
        run.die = lambda why: None
        run.need = 10 ** 9
        run.hp = run.maxhp = 9999
        run.open_chest = lambda kind: None

        def bot(i):
            dx, dy = run.px - run.hx, run.py - run.hy
            dl = math.hypot(dx, dy) or 1
            ux, uy = dx / dl, dy / dl
            k = 0.4 if run.gd - run.R > 160 else 1.0
            a.input.axes["lx"], a.input.axes["ly"] = ux * k - uy * (1 - k), uy * k + ux * (1 - k)
            if run.state == "levelup":
                run.choose()
            if run.state == "chest":
                run.state = "play"
        for k in range(200):
            bot(k)
            step(1, False)
        run.hx, run.hy = run.px - 210, run.py + 40          # O GRAVE in the shot
        run.banner = ("", 0, "")
        shoot("voidrunner", gap=10, act=bot, real=False)
        a.input.axes["lx"] = a.input.axes["ly"] = 0.0

    # 12 BEAT DUEL: CPU duel in full swing
    if want("beatduel"):
        a.go("beatduel"); bd = a.cur
        bd.sel, bd.diff, bd.mode = 4, 1, __import__("beatduel").MODES.index("VS CPU")
        bd.on("press", "a")
        match = bd.match
        lanes = ["left", "down", "up", "right"]
        held = []

        def auto():
            t = match.now()
            for r_ in [r_ for r_ in held if t >= r_[0]]:
                held.remove(r_)
                bd.on("release", r_[1])
            p = match.players[0]
            for i in range(p.next, min(len(p.notes), p.next + 12)):
                n = p.notes[i]
                if not n[2] and t >= n[0] + 0.01 and i not in done_:
                    done_.add(i)
                    bd.on("press", lanes[n[1]])
                    held.append((n[0] + (n[3] if n[3] > 0 else 0.05), lanes[n[1]]))
        done_ = set()
        for _ in range(150):
            auto()
            step(1)

        def act(i):
            for _ in range(9):
                auto()
                step(1)
            auto()
        shoot("beatduel", gap=1, act=act)
        bd.on("press", "start")
finally:
    try:
        a.sections["vox"].stop()
        a.sections["forge"].stop()
    except Exception:
        pass
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACKUP:
            open(p, "wb").write(BACKUP[f])

# contact sheet
names = sorted(set(f.rsplit("_", 1)[0] for f in os.listdir(OUT) if f.endswith(".png") and not f.startswith("sheet")))
sheet = Image.new("RGB", (6 * 214, len(names) * 160), (0, 0, 0))
for r, nm in enumerate(names):
    for c in range(6):
        p = os.path.join(OUT, "%s_%d.png" % (nm, c))
        if os.path.exists(p):
            sheet.paste(Image.open(p).resize((213, 160)), (c * 214, r * 160))
sheet.save(os.path.join(OUT, "sheet.png"))
print("sheet", names)
