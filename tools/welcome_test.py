"""The bridge's welcome card closes with any button, START and SELECT too: START (Enter on a PC) used to open the
selected music app behind it, so the card came back on every visit and hid the menu (and the games) for good.
  python3 tools/welcome_test.py [APPDIR]"""
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "quiz.json", "forge.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import sdl2  # noqa: E402
import app as appmod  # noqa: E402

a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready:
    time.sleep(0.05)
queue = []
orig_poll = a.input.poll


def poll():
    orig_poll()
    a.input.events = list(queue)
    for kind, b in queue:
        if kind == "press":
            a.input.held[b] = time.time()
        elif kind == "release":
            a.input.held.pop(b, None)
    del queue[:]


a.input.poll = poll


def frame(n=1):
    for _ in range(n):
        a.handle()
        a.mixer.render(1470)
        a.frame(1 / 30.0)
        sdl2.SDL_RenderPresent(a.ren)


def tap(b):
    queue.append(("press", b))
    frame()
    queue.append(("release", b))
    frame(3)


try:
    for b in ("start", "select", "a", "right"):
        a.cfg["welcomed"] = False
        a.go("bridge")
        bridge = a.sections["bridge"]
        cat = bridge.cat
        frame(2)
        assert bridge.welcome()
        tap(b)
        assert a.cur_name == "bridge", (b, a.cur_name)
        assert not bridge.welcome() and a.cfg["welcomed"], b
        assert bridge.cat == cat, b                      # the button only closed the card
        assert not a.music_menu.active and not a.help.tutorial, b
    print("the welcome card closes with START, SELECT, A and the d-pad, and nothing opens behind it")

    # ... and then the menu is there: the games tab, and a game opens with START (Enter) as with A
    bridge.cat = 0
    tap("right")
    assert appmod.CATS[bridge.cat][0] == "JOGOS"
    tap("start")
    assert a.cur_name == "orimbox", a.cur_name
    tap("select")
    assert a.cur_name == "bridge"
    tap("down")
    tap("a")
    assert a.cur_name == "pet", a.cur_name
    print("after it, the bridge shows the games: ORIMBOX opens with START, XENO PET with A")
    print("ok")
finally:
    for f in SAVES:
        p = os.path.join(APPD, f)
        if f in BACK:
            open(p, "wb").write(BACK[f])
        elif os.path.exists(p):
            os.remove(p)
