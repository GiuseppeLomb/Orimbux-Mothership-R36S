"""Player files read from disk (Beat Duel sessions and charts, recording metadata, Forge loops in the Loop Reactor,
the Void Runner scan cache): a damaged one never crashes the app, and the built-in songs keep every note.
  python3 tools/files_test.py [APPDIR]"""
import glob
import json
import os
import shutil
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
import beatduel  # noqa: E402
import decks  # noqa: E402
import recmgr  # noqa: E402
import songscan  # noqa: E402

made = []


def put(rel, data):
    p = os.path.join(APPD, rel)
    if not os.path.isdir(os.path.dirname(p)):
        os.makedirs(os.path.dirname(p))
    if isinstance(data, bytes):
        open(p, "wb").write(data)
    else:
        open(p, "w").write(data if isinstance(data, str) else json.dumps(data))
    made.append(p)
    return p


try:
    wav = open(os.path.join(APPD, "assets", "bd", "moon_hop.wav"), "rb").read()
    # ---- the built-in songs keep every note
    for p in glob.glob(os.path.join(APPD, "assets", "bd", "*.json")):
        raw = json.load(open(p))
        assert beatduel.clean_charts(raw["charts"]) == raw["charts"], p
    # ---- damaged player files
    put("recordings/session_29990101_000000.wav", wav)
    put("recordings/session_29990101_000000.json",
        {"id": "session_29990101_000000", "title": 5, "bpm": "x", "file": "session_29990101_000000.wav",
         "charts": {"easy": [[1.0, 7], [2.0, 1.0], ["a", 1], 3, [4.0, 2, "x"]], "normal": [[1.0, 0], [2.5, 3, 0.8]],
                    "hard": "x"}})
    put("recordings/session_29990101_000001.json", "[1, 2")
    put("recordings/rec_29990101_000002.wav", wav)
    put("recordings/rec_29990101_000002.wav.chart.json", {"bpm": "fast", "charts": [1]})
    put("recordings/session_29990101_000003.wav", wav)
    put("recordings/session_29990101_000003.json", {"title": ["x"], "bpm": "z"})
    put("forge/forge_A.wav", wav)
    put("forge/forge_A.json", {"beats": "x"})
    songs = beatduel.find_songs()
    s = [x for x in songs if x.get("id") == "session_29990101_000000"][0]
    assert s["charts"] == {"easy": [], "normal": [[1.0, 0], [2.5, 3, 0.8]]}, s["charts"]
    assert s["title"] == "SESSION_29990101_000000" and s["bpm"] == 120
    r = [x for x in songs if x["id"] == "rec_29990101_000002.wav"][0]
    assert r["charts"] == {} and r["bpm"] == 120
    assert not [x for x in songs if x.get("id") == "session_29990101_000003"]
    print("damaged sessions and charts are cleaned or skipped")

    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    while not a.bank.ready:
        time.sleep(0.05)
    assert a.bank.pad(a.bank.forge_bank, 0)["beats"] == 4
    a.go("reactor")
    rx = a.sections["reactor"]
    rx.bank = a.bank.forge_bank
    rx.trigger(0)
    for _ in range(3):
        a.mixer.render(1024)
        a.frame(1 / 30.0)
    print("a Forge loop with damaged metadata plays")
    bd = a.sections["beatduel"]
    a.go("beatduel")
    bd.sel = [i for i, x in enumerate(bd.songs) if x.get("id") == "session_29990101_000000"][0]
    bd.diff = 1
    for _ in range(3):
        a.frame(1 / 30.0)
    bd.on("press", "a")
    assert bd.state == "play"
    for _ in range(30):
        a.mixer.render(1024)
        a.frame(1 / 30.0)
    bd.on("press", "start")
    print("Beat Duel plays a session with damaged notes")
    a.go("voidrunner")                               # its song list is built from the same files
    for _ in range(3):
        a.frame(1 / 30.0)
    # ---- recordings manager and Twin Decks library with damaged metadata
    put("recordings/session_29990101_000004.wav", wav)
    put("recordings/session_29990101_000004.json", {"title": 42, "bpm": "fast", "file": "x.wav"})
    titles = [it["title"] for it in recmgr.scan()]
    assert "session_29990101_000004" in titles
    lib = decks.library(a)
    assert [it for it in lib if it["title"] == "session_29990101_000004"][0]["bpm"] is None
    a.go("hangar")
    hg = a.cur
    hg.sel = [n for n, _ in hg.items()].index("GRAVACOES")
    hg.on("press", "a")
    a.frame(1 / 30.0)
    hg.on("press", "b")
    print("recordings manager and Twin Decks library ignore damaged metadata")
    # ---- a damaged Void Runner scan cache is scanned again
    src = put("music/scan_test_29990101.wav", wav)
    key = songscan._key(src)
    good = songscan.scan_file(src)
    cp = os.path.join(songscan.CACHE, key + ".json")
    for broken in ({"dur": "x"}, {"dur": 3.0, "env": 5, "on": []}, {"dur": 3.0, "env": ["a"], "on": []}, [1]):
        json.dump(broken, open(cp, "w"))
        assert songscan.scan_file(src) == good
    made.append(cp)
    print("a damaged scan cache is scanned again")
    print("ok")
finally:
    if "a" in globals():
        for st in list(a.mixer.streams):         # Windows cannot delete a file that is still open
            st.close()
    for p in made:
        try:
            os.remove(p)
        except OSError:
            pass
    for d in ("forge",):
        dd = os.path.join(APPD, d)
        if os.path.isdir(dd) and not os.listdir(dd):
            shutil.rmtree(dd)
    for f in SAVES:
        try:
            os.remove(os.path.join(APPD, f))
        except OSError:
            pass
        if f in BACK:
            open(os.path.join(APPD, f), "wb").write(BACK[f])
