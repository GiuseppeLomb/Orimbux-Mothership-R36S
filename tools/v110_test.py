"""v1.10 checks: the Xeno Pet never asks how long you were away (it lives what the clock says, and ignores a clock
that went back or jumped too far), SOM DE OURO is DISCO VOADOR, and the 2.5D Void Runner draws its lit world.
  python3 tools/v110_test.py [APPDIR]"""
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "vr_save.json", "quiz.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod  # noqa: E402
import engine  # noqa: E402
import pet as petmod  # noqa: E402
import quiz as quizmod  # noqa: E402
import voidrunner as V  # noqa: E402

try:
    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    while not a.bank.ready:
        time.sleep(0.02)

    # --- XENO PET: no question, ever
    assert not hasattr(petmod, "AWAY_CHOICES") and not hasattr(petmod, "boot_uptime")
    pet = a.sections["pet"]
    AGE = petmod.ADULT_AT + 3600.0

    def put_pet(last_seen):
        p = petmod.new_pet()
        p.update({"form": "glorpo", "name": "MOMO", "age": AGE, "last_seen": last_seen})
        engine.write_json(petmod.PET_FILE, p)
        pet.p = pet.load()
        pet.away_report, pet.events = None, []
        pet.catch_up()

    put_pet(time.time() - 5 * 3600)                     # the clock ran while it was off: those hours are lived
    assert pet.away_report and abs(pet.away_report["gap"] - 5 * 3600) < 60, pet.away_report
    assert pet.p["age"] >= AGE + 5 * 3600 - 60
    a.go("pet")
    assert pet.mode == "away"                            # a report of what happened, not a question
    pet.draw(a.g, a.t, 1 / 30.0)
    pet.on("press", "a")
    assert pet.mode == "home" and pet.away_report is None
    for jump in (3 * 86400, -90 * 86400):               # the clock went back / jumped months ahead: not lived
        put_pet(time.time() + jump)
        assert pet.away_report is None and pet.p["age"] == AGE, (jump, pet.p["age"])
        assert abs(pet.p["last_seen"] - time.time()) < 5
        pet.enter()
        assert pet.mode == "home"
    put_pet(time.time() - 60)                            # a minute: nothing to report
    assert pet.away_report is None and pet.p["age"] == AGE
    a.go("bridge")

    # --- DISCO VOADOR
    assert quizmod.Quiz.name == "DISCO VOADOR"
    names = [it[0] for _, items in appmod.CATS for it in items]
    assert "DISCO VOADOR" in names and not any("OURO" in n for n in names), names

    # --- VOID RUNNER in 2.5D: a lit world with shadows, drawn from the same game
    vr = a.sections["voidrunner"]
    a.go("voidrunner")
    for k in ("pool", "ray", "vignette"):
        assert vr.tex.get(k), k
    run = vr.start_now(0, [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0])
    for _ in range(90):
        run.update(1 / 30.0)
        a.mixer.render(1470)
    run.draw(a.g, a.t)
    assert any(k.endswith("_lit") for k in run.tx), sorted(run.tx)[:8]
    assert 0 < V.TILT < 1 and V.ROUT == 6000.0
    run.free()
    vr.run = None

    # --- v1.11: the song never stops for the level-up and chest screens; only a real pause stops it
    vr.run = r = vr.start_now(0, [x for x in vr.songs if x["id"] == "MIX_DA_NAVE"][0])
    r.die = lambda why: None
    ok_was, a.mixer.ok = a.mixer.ok, True                      # as on the console: the song is the clock
    for _ in range(60):
        a.mixer.render(1470)
        vr.update(1 / 30.0)
    beats, drops = [], []
    r.on_beat = lambda s: beats.append(s)
    real_drop = r.drop
    r.drop = lambda: (drops.append(r.mt), real_drop())
    for menu in ("levelup", "chest"):
        r.state, p0, mt0 = menu, r.music.pos, r.mt
        for _ in range(150):                                   # 5 s with the menu open
            a.mixer.render(1470)
            vr.update(1 / 30.0)
        assert not r.music.paused and r.music.pos - p0 > 4.5 * 44100, (menu, r.music.pos - p0)
        assert r.held and r.mt == mt0                          # the game waits, the song goes on
        del beats[:]
        r.state = "play"
        vr.update(1 / 30.0)
        assert r.mt - mt0 > 4.5 and not beats and not r.held, (r.mt - mt0, len(beats))   # no burst of beats
    nd = r.tl.next_drop(r.mt)                                  # a drop that comes while a menu is open...
    del drops[:]
    r.state = "levelup"
    while r.music.pos / 44100.0 < nd + 0.5:
        a.mixer.render(1470)
        vr.update(1 / 30.0)
    r.state = "play"
    vr.update(1 / 30.0)
    assert len(drops) == 1 and drops[0] >= nd, (drops, nd)    # ...still hits once, when the game goes on
    vr.state = "pause"
    vr.update(1 / 30.0)
    assert r.music.paused                                      # START: a real pause stops the song
    vr.state = "run"
    vr.update(1 / 30.0)
    assert not r.music.paused
    a.mixer.ok = ok_was
    r.free()
    vr.run = None
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
