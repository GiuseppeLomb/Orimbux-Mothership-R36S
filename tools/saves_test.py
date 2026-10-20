"""Saved files: writes are atomic (a failure half-way never damages the old file).
  python3 tools/saves_test.py [APPDIR]"""
import ast
import glob
import json
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "forge.json", "quiz.json", "vr_save.json", "bd_save.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod  # noqa: E402
import engine  # noqa: E402


def cleanup():
    for f in SAVES:
        for p in [os.path.join(APPD, f)] + glob.glob(os.path.join(APPD, f + ".*")):
            try:
                os.remove(p)
            except OSError:
                pass


try:
    # ---- every save goes through engine.write_json (no json.dump straight into the real file)
    for path in sorted(glob.glob(os.path.join(APPD, "*.py"))):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                for node in ast.walk(fn):
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                            and node.func.attr == "dump" and getattr(node.func.value, "id", "") == "json"):
                        assert os.path.basename(path) == "engine.py" and fn.name == "write_json", \
                            "%s:%d json.dump outside engine.write_json" % (os.path.basename(path), node.lineno)
    print("every save goes through engine.write_json")

    # ---- write_json: a failure while writing leaves the old file untouched
    p = os.path.join(APPD, "quiz.json")
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
    print("write_json is atomic")

    # ---- unreadable saves (cut short by a power cut, zeros, not an object) are kept, never written over
    damaged = {"config.json": b"[]", "pet.json": b'{"gen": 3, "name": "ZORP", "form": "glorpo", "age": 9',
               "forge.json": b"\0" * 300, "quiz.json": b'{"best": 9, "gam', "vr_save.json": b"{",
               "bd_save.json": b"[1, 2]"}
    for f, data in damaged.items():
        open(os.path.join(APPD, f), "wb").write(data)
    a = appmod.App(headless=True)
    while not a.bank.ready:
        time.sleep(0.05)
    for f, data in damaged.items():
        kept = glob.glob(os.path.join(APPD, f + ".bad-*"))
        assert len(kept) == 1 and open(kept[0], "rb").read() == data, "%s: the damaged file was not kept" % f
        assert not os.path.exists(os.path.join(APPD, f)), f
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
    good = dict((f, open(os.path.join(APPD, f), "rb").read()) for f in SAVES)
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
            assert open(os.path.join(APPD, name), "rb").read() == good[name], "%s was damaged" % name
    finally:
        json.dump = real_dump
    for f in SAVES:
        json.load(open(os.path.join(APPD, f)))
    print("app saves survive a failure half-way")
    print("ok")
finally:
    cleanup()
    for f, data in BACK.items():
        open(os.path.join(APPD, f), "wb").write(data)
