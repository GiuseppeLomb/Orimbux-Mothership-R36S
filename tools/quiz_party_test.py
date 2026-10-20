"""DISCO VOADOR checks: the question bank in the game, difficulty per rung, FESTA with 10 players (turns, points,
standings, podium, ties, name editor), practice themes. Screens -> argv[1]."""
import ctypes, os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "quiz.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import sdl2
from PIL import Image
import app as appmod
import quiz as qz
import quizbank as qb

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/quiz_party"
os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["welcomed"] = True
shots = []


def snap(name, n=2):
    for _ in range(n):
        a.frame(1 / 30.0)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(
        os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)
    shots.append(name)


def press(b):
    a.cur.on("press", b)


try:
    q = a.sections["quiz"]
    a.go("quiz")
    a.missions.toast = ("", 0)
    snap("q0_menu")
    # ---- the solo ladder climbs through the 4 difficulties
    assert [qz.diff_of(i) for i in range(15)] == [1] * 4 + [2] * 4 + [3] * 4 + [4] * 3
    for lvl in (1, 2, 3, 4):
        for _ in range(30):
            x = q.make("trivia", lvl)
            assert x["lvl"] in (lvl, lvl - 1, lvl + 1) and len(set(x["opts"])) == 4 and 0 <= x["answer"] < 4
            y = q.make("theory", lvl)
            assert len(set(y["opts"])) == 4 and y["opts"][y["answer"]]
    print("bank: %d trivia, %d categories" % (len(qb.TRIVIA), len(qb.CATEGORIES)))
    # ---- FESTA setup: 10 players, 3 rounds, rising difficulty
    press("down"); press("a")
    assert q.state == "party_setup", q.state
    P = q.party
    P["sel"] = 0
    for _ in range(12):
        press("right")
    assert P["n"] == 10
    P["sel"] = 2; P["rounds"] = 0                   # 3 rounds
    P["sel"] = 1; P["diff"] = 0
    snap("q1_setup")
    # names: edit player 2 with the arcade editor
    P["sel"] = 3; press("a")
    assert q.state == "party_names"
    press("down"); press("a")
    assert q.state == "party_edit"
    for b in ("up", "up", "right", "down", "right", "up"):      # C, B?, ...
        press(b)
    snap("q2_edit")
    press("a")
    assert q.state == "party_names" and P["names"][1] != "JOGADOR 2", P["names"][1]
    print("renamed player 2 ->", P["names"][1])
    press("right")
    assert P["nsel"] == 6
    snap("q3_names")
    press("start")
    assert q.state == "party_turn" and P["round"] == 1 and P["turn"] == 0
    snap("q4_turn")
    # ---- play 3 rounds: even players answer right, odd players wrong, player 9 runs out of time
    for rnd in range(3):
        assert q.party_lvl() == [1, 2, 3][rnd], (rnd, q.party_lvl())
        for i in range(10):
            assert q.state == "party_turn", (rnd, i, q.state)
            q.t0 -= 1
            press("a")
            assert q.state == "party_q"
            if rnd == 1 and i == 0:
                snap("q5_question")
            if i == 9:
                q.t0 -= q.q["limit"] + 1
                q.update(0.1)
                assert q.state == "party_reveal" and not q.q["ok"] and q.q["pick"] is None
            else:
                q.cur = q.q["answer"] if i % 2 == 0 else (q.q["answer"] + 1) % 4
                press("a")
            assert q.state == "party_reveal"
            if rnd == 1 and i == 0:
                snap("q6_reveal")
            q.t0 -= 1
            press("a")
        assert q.state == "party_board", q.state
        if rnd == 1:
            snap("q7_board")
        q.t0 -= 1
        press("a")
    assert q.state == "party_over", q.state
    sc = P["scores"][:10]
    print("scores:", sc)
    assert all(sc[i] > 0 for i in range(0, 10, 2)) and all(sc[i] == 0 for i in range(1, 10, 2))
    # points: difficulty x 100 + speed bonus (answered instantly -> close to the full bonus)
    assert all(600 <= sc[i] <= 900 for i in range(0, 9, 2)), sc
    table = q.standings()
    assert table[0][0] == 1 and [p for p, _ in table].count(table[-1][0]) == 5, table   # 5 tied at zero
    snap("q8_podium")
    assert q.st["party_best"][1] == max(sc)
    # ---- practice: theory theme
    q.state = "practice_menu"; q.psel = [i for i, p in enumerate(qz.PRACTICE) if p[0] == "TEORIA"][0]
    press("a")
    assert q.state == "q" and q.q["cat"] == "TEORIA"
    snap("q9_practice")
    # ---- solo game still works
    q.start_game()
    assert q.q["diff"] == 1
    q.level = 13; q.next_question()
    assert q.q["diff"] == 4
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
for i in range(0, len(shots), 6):
    grp = shots[i:i + 6]
    sheet = Image.new("RGB", (3 * 640, 2 * 480))
    for j, nm in enumerate(grp):
        sheet.paste(Image.open(os.path.join(OUT, nm + ".png")), ((j % 3) * 640, (j // 3) * 480))
    sheet.resize((1440, 720), Image.LANCZOS).save(os.path.join(OUT, "sheet_%d.png" % (i // 6)))
