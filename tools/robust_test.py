"""Robustness: leaving the app after an error still saves everything and stops the recorder.
  python3 tools/robust_test.py [APPDIR]"""
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
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod  # noqa: E402

procs = []
try:
    # ---- a section that raises: the loop ends, but config, pet and Beat Forge are saved and arecord is stopped
    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    while not a.bank.ready:
        time.sleep(0.05)
    a.go("bridge")
    a.cfg["volume"] = 42
    a.sections["pet"].p["name"] = "TESTE"
    fg = a.sections["forge"]
    fg.pats[3]["t"][0][5] = [3, 2, 50]
    rec = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])      # stands in for arecord
    procs.append(rec)
    a.sections["abductor"].proc = rec

    def broken_stop():
        raise IOError("card full")               # a failing step must not skip the ones after it
    a.rec.stop = broken_stop

    def broken_update(dt):
        raise RuntimeError("bug in a section")
    a.sections["bridge"].update = broken_update
    try:
        a.run()
        raise AssertionError("the error should reach main.py (it writes log.txt)")
    except RuntimeError:
        pass
    assert json.load(open(os.path.join(APPD, "config.json")))["volume"] == 42
    assert json.load(open(os.path.join(APPD, "pet.json")))["name"] == "TESTE"
    assert json.load(open(os.path.join(APPD, "forge.json")))["pats"][3]["t"][0][5] == [3, 2, 50]
    t0 = time.time()
    while rec.poll() is None and time.time() - t0 < 5:
        time.sleep(0.05)
    assert rec.poll() is not None, "the recorder was left running"
    print("an error in a section still saves config, pet and Beat Forge, and stops the recorder")

    # ---- the system time jumps (no clock battery: the time is set when the network comes up)
    import threading
    import sdl2
    import beatduel
    import engine
    real_time = time.time
    m = engine.Mixer()                                 # no audio device: pump() keeps the transport moving
    m.pump()
    time.time = lambda: real_time() + 1e7              # four months forward
    done = []
    th = threading.Thread(target=lambda: (m.pump(), done.append(1)))
    th.daemon = True
    th.start()
    th.join(3)
    time.time = real_time
    assert done and m.clock < 44100 * 60, "pump() tried to render the whole jump"
    clk = beatduel.Clock(m)
    f0 = clk.frames()
    time.time = lambda: real_time() - 3600             # an hour backwards
    f1 = clk.frames()
    time.time = real_time
    assert f1 >= f0, "the Beat Duel clock went backwards"
    delays = []
    real_delay = sdl2.SDL_Delay
    b = appmod.App(headless=True)
    b.cfg["seen"] = list(__import__("help").HELP)
    b.go("bridge")
    n = [0]

    def jumpy_update(dt):
        assert dt >= 0, dt
        n[0] += 1
        time.time = lambda: real_time() - 1e6 * n[0]   # the clock keeps jumping back while the loop runs
        if n[0] == 5:
            b.running = False
    b.sections["bridge"].update = jumpy_update
    sdl2.SDL_Delay = lambda ms: delays.append(ms)
    t0 = real_time()
    try:
        b.loop()
    finally:
        time.time, sdl2.SDL_Delay = real_time, real_delay
    assert n[0] == 5 and max(delays) <= 34 and real_time() - t0 < 5, delays
    print("a jump of the system time never stalls the loop, pump() or the Beat Duel clock")

    # ---- files are closed: the Twin Decks waveform scan (also when another track is loaded half-way), and
    # every file read while the app starts and its sections open
    import gc
    import warnings
    import wave
    import decks
    opened = []
    real_open = wave.open

    def counting_open(*args, **kw):
        w = real_open(*args, **kw)
        opened.append(w)
        return w
    decks.wave.open = counting_open
    try:
        d = decks.Deck("A")
        bd_dir = os.path.join(APPD, "assets", "bd")
        d.load(os.path.join(bd_dir, "pixel_rush.wav"), "A")
        d.load(os.path.join(bd_dir, "neon_drift.wav"), "B")       # the first scan is still running
        d.wf.close()
        t0 = time.time()                           # give both scans time to finish (or to stop early)
        while d.overview == [] and time.time() - t0 < 10:
            time.sleep(0.05)
        time.sleep(0.3)
    finally:
        decks.wave.open = real_open
    leaked = [w for w in opened if getattr(w, "_file", None) is not None]
    assert len(opened) >= 4 and not leaked, "%d of %d wav files left open" % (len(leaked), len(opened))
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        c = appmod.App(headless=True)
        c.cfg["seen"] = list(__import__("help").HELP)
        while not c.bank.ready:
            time.sleep(0.05)
        for name in ("bridge", "pet", "forge", "xeno", "quiz", "voidrunner", "beatduel", "trailer", "credits",
                     "hangar", "bridge"):
            c.go(name)
            c.frame(1 / 30.0)
        gc.collect()
    unclosed = [str(w.message) for w in caught if issubclass(w.category, ResourceWarning)]
    assert not unclosed, unclosed[:5]
    print("the waveform scan closes its files; starting the app leaves no file open")

    # ---- going back from the Void Runner's "listening to the song" screen stops the scan between files
    import songscan
    calls = []
    real_scan = songscan.scan_file

    def slow_scan(p):
        calls.append(p)
        time.sleep(0.4)
        return real_scan(p)
    songscan.scan_file = slow_scan
    try:
        vr = c.sections["voidrunner"]
        c.go("voidrunner")
        wavs = [os.path.join(bd_dir, f) for f in ("moon_hop.wav", "neon_drift.wav", "pixel_rush.wav", "void_bass.wav")]
        vr.start(0, {"id": "T", "title": "T", "paths": wavs, "col": (255, 255, 255)})
        time.sleep(0.1)
        sc = vr.scanner
        vr.on("press", "b")
        sc.join(5)
    finally:
        songscan.scan_file = real_scan
    assert vr.state == "menu" and not sc.is_alive() and len(calls) == 1 and sc.timeline is None, calls
    print("going back stops the Void Runner's song scan")
    print("ok")
finally:
    for p in procs:
        if p.poll() is None:
            p.kill()
    for f in SAVES:
        try:
            os.remove(os.path.join(APPD, f))
        except OSError:
            pass
        if f in BACK:
            open(os.path.join(APPD, f), "wb").write(BACK[f])
