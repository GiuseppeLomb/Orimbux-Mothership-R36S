"""Saved files: writes are atomic (a failure half-way never damages the old file), a damaged file never stops the
app and is always kept (<name>.bad-<date>), and the files the app writes itself load back unchanged.
  python3 tools/saves_test.py [APPDIR]"""
import ast
import glob
import json
import os
import subprocess
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "forge.json", "quiz.json", "vr_save.json", "bd_save.json")
PHASE = os.environ.get("SAVES_PHASE")          # set for the child processes


def path(f):
    return os.path.join(APPD, f)


def bad_copies(f):
    return glob.glob(path(f + ".bad-*"))


def child(phase):
    p = subprocess.run([sys.executable, os.path.abspath(__file__), APPD], env=dict(os.environ, SAVES_PHASE=phase),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    assert p.returncode == 0 and (phase.upper() + " OK") in out, "%s failed:\n%s" % (phase, out[-1500:])
    return out


def new_app():
    import app as appmod
    a = appmod.App(headless=True)
    while not a.bank.ready:
        time.sleep(0.05)
    return a


# ====================================================================== child processes
def phase_sections():
    """open every section with whatever saves are there, play a little, save everything (like leaving the app)"""
    a = new_app()
    a.cfg["seen"] = list(__import__("help").HELP)
    for name in ("bridge", "pet", "forge", "quiz", "voidrunner", "beatduel", "hangar", "reactor", "xeno", "bridge"):
        a.go(name)
        for _ in range(3):
            a.frame(1 / 30.0)
    fg = a.sections["forge"]
    fg.play()
    for _ in range(40):
        a.mixer.render(1024)
        fg.tick()
    a.go("forge")
    fg.on("press", "a")
    fg.on_grid("press", "x")
    a.frame(1 / 30.0)
    fg.stop()
    q = a.sections["quiz"]
    a.go("quiz")
    q.state = "party_setup"
    q.party_start()
    a.frame(1 / 30.0)
    q.state, q.result = "over", ("lose", q.safe_prize())
    a.frame(1 / 30.0)
    a.save_cfg(sync=True)
    fg.save()
    a.sections["pet"].save()
    for f in SAVES:
        if os.path.exists(path(f)):
            json.load(open(path(f)))
    print("SECTIONS OK")


def phase_make():
    """real saves, written by the app itself after using it"""
    a = new_app()
    import pet as petmod
    c = a.cfg
    a.set_volume(35)
    c.update({"scanlines": False, "quantize": "beat", "swap_ab": True, "pet_speed": 10, "bd_offset": 0.012,
              "vr_lite": True, "buffer": 512, "welcomed": True})
    a.set_bpm(128.5)
    a.mission("pulsar_bpm")
    a.go("reactor")
    a.help.dismiss()
    c.setdefault("custom_pads", {})["3:7"] = os.path.join(APPD, "assets", "bd", "moon_hop.wav")
    # the pet: hatch, name, care, grow up, leave a stone in the memorial
    pt = a.sections["pet"]
    pt.tick(petmod.HATCH_AT + 5)
    pt.process_events()
    pt.mode = "name"
    pt.on("press", "a")
    pt.feed(0)
    pt.tick(petmod.TEEN_AT)
    pt.process_events()
    pt.finish_event()
    pt.p["age"] = petmod.DEPART_AT + 1
    pt.tick(1)
    while pt.events:                                # grows up, then leaves for its planet
        pt.mode = "home"
        pt.process_events()
        pt.finish_event()
    # the Beat Forge: steps, velocity, ratchet, chance, length, a song, a style, swing, track settings
    fg = a.sections["forge"]
    a.go("forge")
    for b in ("a", "right", "a", "x", "right", "y", "y", "down", "a"):
        fg.on("press", b)
    fg.combo("r1")
    fg.combo("right")
    a.input.held["r2"] = True
    for b in ("r1", "up", "y", "a", "b"):
        fg.on("press", b)
    a.input.held["r2"] = False
    fg.mode = "song"
    for b in ("a", "a", "up", "x"):
        fg.on("press", b)
    fg.mode = "build"
    fg.on("press", "right")
    fg.on("press", "a")
    fg.mode = "grid"
    # Disco Voador: a game and a party with a name
    q = a.sections["quiz"]
    q.start_game()
    q.cur = q.q["answer"]
    q.reveal()
    q.party["names"][0] = "ZE"
    q.party_start()
    q.party_lock(q.party_ask() or q.q["answer"])
    q.party["round"] = 99
    q.party_after_board()
    # Void Runner and Beat Duel records
    vr = a.sections["voidrunner"]

    class FakeRun(object):
        endless, song, level, kills, mt, state = False, {"id": "MIX_DA_NAVE"}, 1, 321, 140.5, "won"
    vr.record(FakeRun())
    FakeRun.endless, FakeRun.mt = True, 99.0
    vr.record(FakeRun())
    vr.save_d["seen_en"] = ["skitter", "seer"]
    vr.write()
    bd = a.sections["beatduel"]
    bd.save_d["neon_drift|normal"] = 45210
    bd.write()
    # leave the app the normal way
    a.save_cfg(sync=True)
    a.rec.stop()
    fg.save()
    pt.save()
    print("MAKE OK")


def phase_check():
    """the saves above load back exactly as they were written"""
    import app as appmod
    import quiz as qz
    files = dict((f, json.load(open(path(f)))) for f in SAVES)
    assert appmod.load_cfg() == files["config.json"]
    a = new_app()
    assert a.sections["pet"].load() == files["pet.json"]
    assert a.sections["forge"].state() == files["forge.json"]
    assert qz.clean_stats(files["quiz.json"]) == files["quiz.json"] == a.sections["quiz"].st
    assert a.sections["voidrunner"].save_d == files["vr_save.json"]
    assert a.sections["beatduel"].save_d == files["bd_save.json"]
    assert files["pet.json"]["history"] and files["quiz.json"]["party_cfg"]["names"][0] == "ZE"
    print("CHECK OK")


def phase_old():
    """saves in the formats of older versions still open"""
    a = new_app()
    fg = a.sections["forge"]
    assert fg.tracks[0]["s"] == fg.kit[0]["samples"][1]["file"] and fg.tracks[0]["vol"] == 6
    assert fg.pats[0]["t"][0][:2] == [[2, 1, 100], [1, 3, 75]] and fg.pats[0]["len"] == 16
    assert fg.song_on and fg.swing == 55
    p = a.sections["pet"].p
    assert p["name"] == "MOMO" and p["form"] == "glorpo" and isinstance(p["hue"], float)
    print("OLD OK")


# ====================================================================== the test
def main():
    back = {}
    for f in SAVES:
        if os.path.exists(path(f)):
            back[f] = open(path(f), "rb").read()
            os.remove(path(f))
    import engine

    def cleanup():
        for f in SAVES:
            for p in [path(f)] + glob.glob(path(f + ".*")):
                try:
                    os.remove(p)
                except OSError:
                    pass
    try:
        # ---- every save goes through engine.write_json (no json.dump straight into the real file)
        for py in sorted(glob.glob(os.path.join(APPD, "*.py"))):
            tree = ast.parse(open(py, encoding="utf-8").read())
            for fn in ast.walk(tree):
                if isinstance(fn, ast.FunctionDef):
                    for node in ast.walk(fn):
                        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                                and node.func.attr == "dump" and getattr(node.func.value, "id", "") == "json"):
                            assert os.path.basename(py) == "engine.py" and fn.name == "write_json", \
                                "%s:%d json.dump outside engine.write_json" % (os.path.basename(py), node.lineno)
        print("every save goes through engine.write_json")

        # ---- write_json: a failure while writing leaves the old file untouched
        p = path("quiz.json")
        engine.write_json(p, {"best": 3, "games": 7})
        before = open(p, "rb").read()
        try:
            engine.write_json(p, {"best": 4, "oops": object()})
        except TypeError:
            pass
        assert open(p, "rb").read() == before, "a failed write damaged the file"
        assert json.load(open(p)) == {"best": 3, "games": 7}
        engine.write_json(p, {"best": 5}, sync=False, indent=1)
        assert json.load(open(p)) == {"best": 5} and not os.path.exists(p + ".tmp")
        cleanup()
        print("write_json is atomic")

        # ---- unreadable saves (cut short by a power cut, zeros, not an object) are kept, never written over
        damaged = {"config.json": b"[]", "pet.json": b'{"gen": 3, "name": "ZORP", "form": "glorpo", "age": 9',
                   "forge.json": b"\0" * 300, "quiz.json": b'{"best": 9, "gam', "vr_save.json": b"{",
                   "bd_save.json": b"[1, 2]"}
        for f, data in damaged.items():
            open(path(f), "wb").write(data)
        a = new_app()
        for f, data in damaged.items():
            kept = bad_copies(f)
            assert len(kept) == 1 and open(kept[0], "rb").read() == data, "%s: the damaged file was not kept" % f
            assert not os.path.exists(path(f)), f
        assert a.sections["pet"].p["form"] == "egg" and a.sections["quiz"].st["best"] == -1
        print("unreadable saves are kept as <name>.bad-<date>")

        # ---- the app's own saves: a crash half-way through json.dump never truncates the saved file
        a.cfg["volume"] = 55
        a.save_cfg()
        a.sections["pet"].save()
        a.sections["forge"].save()
        a.sections["quiz"].save()
        a.sections["voidrunner"].write()
        a.sections["beatduel"].save_d["x|normal"] = 1200
        a.sections["beatduel"].write()
        good = dict((f, open(path(f), "rb").read()) for f in SAVES)
        real_dump = json.dump

        def broken_dump(obj, fp, **kw):
            fp.write(json.dumps(obj, **kw)[:20])      # half a file, then the crash (power cut, full card...)
            raise IOError("simulated failure")
        json.dump = broken_dump
        try:
            for name, call in (("config.json", a.save_cfg), ("pet.json", a.sections["pet"].save),
                               ("forge.json", a.sections["forge"].save), ("quiz.json", a.sections["quiz"].save),
                               ("vr_save.json", a.sections["voidrunner"].write),
                               ("bd_save.json", a.sections["beatduel"].write)):
                call()
                assert open(path(name), "rb").read() == good[name], "%s was damaged" % name
        finally:
            json.dump = real_dump
        cleanup()
        print("app saves survive a failure half-way")

        # ---- valid JSON with damaged values: the app opens every section, the original is kept
        child("make")
        forge_ok = json.load(open(path("forge.json")))
        cleanup()
        forge_step = json.loads(json.dumps(forge_ok))
        forge_step["pats"][0]["t"][0][0] = [9, 1, "x"]
        cases = [
            ("forge.json", "[]"),
            ("forge.json", json.dumps({"v": 2, "tracks": [{"vol": "x", "pan": 7, "s": 3.5}], "swing": "a",
                                       "song": ["x", 2], "vars": [1]})),
            ("forge.json", json.dumps(forge_step)),
            ("quiz.json", "[1, 2]"),
            ("quiz.json", json.dumps({"best": 40, "games": "x", "party_cfg": {"n": 50, "names": ["A", 7]},
                                      "party_best": "ZE"})),
            ("pet.json", json.dumps({"last_seen": "ontem", "name": 5, "form": "dragon", "age": 9e5, "poops": "2",
                                     "sick": [], "history": [{"gen": "1", "form": [1]}, 3]})),
            ("config.json", json.dumps({"volume": "alto", "bpm": "x", "missions": 3, "seen": 5, "anim": "sim",
                                        "custom_pads": ["x"], "joy_map": {"a": [1]}, "bd_offset": "z"})),
            ("vr_save.json", json.dumps({"unlocked": "6", "best": {"a|0": 5, "b|1": {"kills": 3}}, "seen_en": 4,
                                         "endless": None})),
            ("bd_save.json", json.dumps({"a|normal": "x", "b|hard": 300})),
        ]
        for f, content in cases:
            open(path(f), "w").write(content)
            child("sections")
            kept = bad_copies(f)
            assert len(kept) == 1 and open(kept[0]).read() == content, "%s: the original was not kept" % content
            cleanup()
        print("damaged values never stop the app (%d cases), the originals are kept" % len(cases))

        # ---- the app's own saves load back unchanged, without any .bad copy
        child("make")
        made = dict((f, open(path(f), "rb").read()) for f in SAVES)
        child("check")
        for f in SAVES:
            assert not bad_copies(f), "a valid %s was treated as damaged" % f
        print("real saves load back unchanged: %s" % ", ".join("%s %d B" % (f, len(made[f])) for f in SAVES))
        cleanup()

        # ---- older formats: Beat Forge v1 (sample index, 16-step lists, "chain"), a pet without the newer fields
        nt = len(json.load(open(os.path.join(APPD, "assets", "forge", "kit.json")))["tracks"])
        row = [[2, 1, 100], [1, 3, 75]] + [[0, 1, 100]] * 14
        v1 = {"tracks": [{"s": 1, "vol": 6, "pitch": 0, "pan": 0, "mute": False}],
              "pats": [[row] * nt for _ in range(8)], "swing": 55, "chain": True}
        open(path("forge.json"), "w").write(json.dumps(v1))
        open(path("pet.json"), "w").write(json.dumps({"gen": 2, "name": "MOMO", "form": "glorpo", "age": 900000.0,
                                                      "full": 60.0, "last_seen": time.time()}))
        child("old")
        assert len(bad_copies("forge.json")) == 1 and not bad_copies("pet.json")
        print("older formats still open (the v1 Beat Forge file is kept before its conversion)")
        print("ok")
    finally:
        cleanup()
        for f, data in back.items():
            open(path(f), "wb").write(data)


if PHASE:
    {"sections": phase_sections, "make": phase_make, "check": phase_check, "old": phase_old}[PHASE]()
else:
    main()
