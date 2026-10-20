"""v1.9 checks: START tap/hold (next app / music menu), the music transport, missions, DISCO VOADOR, help glyphs."""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "quiz.json", "forge.json")
REC = os.path.join(APPD, "recordings")
REC0 = set(os.listdir(REC)) if os.path.isdir(REC) else set()      # the session recorded below is removed after
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import sdl2
import app as appmod
import quiz as qz
import ui

a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["welcomed"] = True
while not a.bank.ready:
    time.sleep(0.05)
queue = []


class FakeInput(object):
    pass


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


try:
    # ---- music order + START tap walks the 8 music apps
    assert appmod.CYCLE == ["pulsar", "forge", "abductor", "reactor", "xeno", "vox", "decks", "warp"], appmod.CYCLE
    a.go("pulsar"); frame()
    seen = []
    for _ in range(8):
        queue.append(("press", "start")); frame(); queue.append(("release", "start")); frame()
        seen.append(a.cur_name)
    assert seen == ["forge", "abductor", "reactor", "xeno", "vox", "decks", "warp", "pulsar"], seen
    print("START tap order ok")
    # ---- hold START = music menu (no app change)
    a.go("reactor"); frame()
    queue.append(("press", "start")); frame()
    a.st_t0 = time.time() - 0.5                 # pretend it was held
    frame()
    assert a.music_menu.active and a.cur_name == "reactor"
    queue.append(("release", "start")); frame()
    assert a.music_menu.active and a.cur_name == "reactor", "releasing after the hold must not jump apps"
    # A = play (nothing playing -> starts the Beat Forge)
    queue.append(("press", "a")); frame()
    assert a.sections["forge"].playing and a.now_playing()["playing"]
    # a loop on top, then pause all -> everything silent; resume -> both back
    a.music_menu.close()
    a.sections["reactor"].trigger(0)
    frame(3)
    assert a.reactor_loops(), "loop should be playing/queued"
    a.music_menu.open()
    queue.append(("press", "a")); frame()
    st = a.now_playing()
    assert not st["forge"] and not st["loops"], st
    queue.append(("press", "a")); frame()
    st = a.now_playing()
    assert st["forge"] and st["loops"], st
    bpm0 = a.mixer.bpm
    queue.append(("press", "right")); frame()
    assert round(a.mixer.bpm) == round(bpm0) + 1
    queue.append(("press", "x")); frame()
    assert not a.now_playing()["playing"]
    queue.append(("press", "b")); frame()
    assert not a.music_menu.active
    print("music menu ok")
    # ---- record from the music menu (Decks: up to 20 min)
    a.go("decks"); frame()
    a.music_menu.open()
    queue.append(("press", "y")); frame()
    assert a.rec.active() and a.rec.max_s == 20 * 60, (a.rec.active(), a.rec.max_s)
    queue.append(("press", "y")); frame()
    assert not a.rec.active()
    a.music_menu.close()
    # ---- vox mic on R2 (START is next-app everywhere in music)
    a.go("vox"); frame()
    queue.append(("press", "start")); frame(); queue.append(("release", "start")); frame()
    assert a.cur_name == "decks"
    # ---- missions tick
    ms = a.missions
    ms.reset()
    a.go("pulsar"); frame()
    a.cur.on("press", "right"); frame()
    assert "pulsar_bpm" in ms.done_set
    a.go("forge"); a.cur.on("press", "b"); frame()
    assert "forge_play" in ms.done_set
    a.sections["forge"].stop()
    assert ms.next_step()[0] == "reactor_pad"
    a.go("bridge"); frame(3)
    br = a.sections["bridge"]
    assert appmod.CATS[br.cat][1][br.sel[br.cat]][1] == "reactor", "bridge should wait on the next mission app"
    br.on("press", "down"); a.go("pulsar"); a.go("bridge")
    assert appmod.CATS[br.cat][1][br.sel[br.cat]][1] == "xeno", "same step: the bridge keeps the user's choice"
    print("missions ok")
    # ---- DISCO VOADOR: a full game with the right answers, lifelines, the safe level and a wrong answer
    q = a.sections["quiz"]
    a.go("quiz"); frame()
    q.start_game(); frame()
    assert q.state == "q" and len(q.q["opts"]) == 4
    q.use("50")
    assert len(q.removed) == 2 and q.q["answer"] not in q.removed
    q.use("poll")
    assert q.poll and abs(sum(q.poll) - 1.0) < 0.05 or sum(q.poll) <= 1.0
    q.use("xeno")
    assert q.xeno is not None
    for level in range(6):
        assert q.state == "q", q.state
        q.cur = q.q["answer"]
        q.on("press", "a"); assert q.state == "suspense", "A answers at once (no final-answer question)"
        q.t0 -= 3; q.update(0.1); assert q.state == "reveal" and q.q["ok"]
        q.t0 -= 3; q.update(0.1); assert q.state == "climb", q.state
        q.t0 -= 3; q.update(0.1)
    assert q.level == 6 and "quiz_5" in ms.done_set
    # wrong answer at 7 -> you keep the safe level 5 ("Primeiro single")
    q.cur = [i for i in range(4) if i != q.q["answer"]][0]
    q.on("press", "a")
    q.t0 -= 3; q.update(0.1); q.t0 -= 3; q.update(0.1)
    assert q.state == "over" and q.result == ("lose", 4), q.result
    # every question kind builds a valid question at every level
    for kind in ("trivia", "high4", "low4", "count", "mood2", "mood4", "tempo", "drum", "interval3", "interval4",
                 "bpm", "note", "scale"):
        for lvl in (1, 2, 3):
            qq = q.make(kind, lvl)
            assert len(qq["opts"]) == 4 and 0 <= qq["answer"] < 4 and len(set(qq["opts"])) == 4, (kind, qq)
    # trivia: all answers distinct, the right one always among them
    for t in qz.TRIVIA:
        assert len(set(t[3:7])) == 4, t
    # practice mode
    q.start_practice(0); frame()
    assert q.state == "q"
    q.cur = q.q["answer"]; q.on("press", "a"); q.t0 -= 3; q.update(0.1); q.t0 -= 3; q.update(0.1)
    assert q.streak == 1 and q.state == "q"
    print("quiz ok: %d trivia questions" % len(qz.TRIVIA))
    # ---- glyph parser understands the help vocabulary
    toks = ui.tokens("SELECT+cima/baixo")
    assert toks[0] == ("pill", "SELECT") and ("dpad", "UD") in toks, toks
    assert ui.tokens("setas + X/Y/A/B")[0] == ("dpad", "DPAD")
    assert ("stick", "L") in ui.tokens("analogico esq.")
    print("ok")
finally:
    try:
        a.sections["forge"].stop()
    except Exception:
        pass
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACK:
            open(p, "wb").write(BACK[f])
    for f in (set(os.listdir(REC)) - REC0) if os.path.isdir(REC) else ():
        if f.startswith("session_"):
            os.remove(os.path.join(REC, f))
