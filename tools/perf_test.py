"""Performance probe (headless): ms per frame of a few busy screens, the cost of one audio callback, and a hash
of the rendered audio so a speed-up can be checked for "same sound, bit for bit".
  python3 tools/perf_test.py [APPDIR]        (APPDIR defaults to this repository's ports/mothership)
Times are from the PC: the R36S is several times slower, compare runs on the same machine only."""
import hashlib
import os
import random
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "forge.json", "quiz.json", "vr_save.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod  # noqa: E402
import engine  # noqa: E402


def best_of(fn, runs=5):
    return min(fn() for _ in range(runs))


try:
    random.seed(7)
    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    a.cfg["welcomed"] = True
    while not a.bank.ready:
        time.sleep(0.05)
    m = a.mixer
    a.go("bridge")
    with m.lock:
        m.streams, m.voices = [], []
    # ---- screens (draw + update, no audio)
    fg, rx = a.sections["forge"], a.sections["reactor"]
    print("screen        ms/frame (best of 5 x 200 frames)")
    for name in ("bridge", "forge", "reactor", "hangar", "quiz", "pet", "xeno"):
        a.go(name)
        if name == "forge":
            fg.play()
        if name == "reactor":
            rx.trigger(0)
            rx.trigger(4)
        for _ in range(5):
            a.frame(1 / 30.0)

        def run():
            t0 = time.perf_counter()
            for _ in range(200):
                a.frame(1 / 30.0)
            return (time.perf_counter() - t0) / 200 * 1000
        print("  %-10s %.3f" % (name, best_of(run)))
        fg.stop()
        m.kill_group("reactor")
    # ---- one audio callback with a typical load (deterministic: fixed seed, fixed start)
    a.go("bridge")
    with m.lock:
        m.streams, m.voices, m.synth = [], [], []
        m.clock = 0
    random.seed(7)
    fg.play()
    rx.trigger(0)
    rx.trigger(4)
    xs = a.sections["xeno"]
    xs.note_on("left")
    xs.note_on("up")
    v = engine.StreamVoice(os.path.join(APPD, "assets", "bd", "moon_hop.wav"))
    with m.lock:
        m.streams.append(v)
    h = hashlib.sha1()
    spent = []
    for i in range(1500):
        fg.tick()
        t0 = time.perf_counter()
        out = m.render(1024)
        spent.append(time.perf_counter() - t0)
        h.update(out)
    spent.sort()
    print("audio render(1024): median %.1f us  p95 %.1f us   audio sha1 %s" % (
        spent[len(spent) // 2] * 1e6, spent[int(len(spent) * 0.95)] * 1e6, h.hexdigest()[:16]))
    fg.stop()
finally:
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACK:
            open(p, "wb").write(BACK[f])
