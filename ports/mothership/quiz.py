# DISCO VOADOR - a music quiz show.
#  JOGAR: 15 questions from the garage to the Diamond Record, difficulty climbing from FÁCIL to ESPECIALISTA.
#    Levels 5 and 10 are safe. Lifelines (once per game): 50:50 (L1), crew poll (R1), ask the Xeno Pet (L2).
#  FESTA: 2 to 10 players pass the console; every player gets a question per round, points for right answers
#    (more for harder ones and for answering fast), standings after each round and a podium at the end.
#  TREINO LIVRE: endless practice by theme. X replays the sound of a question, for free.
import math
import os
import random
import time

import engine
import ui
import earlab
import quizbank as qb
from engine import C, W, H, load_wav

SAVE = os.path.join(engine.APP, "quiz.json")
GOLD = (255, 214, 80)
GOLD_DK = (150, 110, 20)
LADDER = ["Ensaio na garagem", "Primeiro concerto", "Bar da esquina", "Rádio local", "Primeiro single",
          "Festival de verão", "Videoclip", "Tour nacional", "Disco de prata", "Disco de ouro",
          "Tour mundial", "Disco de platina", "Estádio cheio", "Galeria da fama", "DISCO DE DIAMANTE"]
SAFE = (4, 9)                     # indexes of the safe levels (5 and 10)
LETTERS = "ABCD"
DRUMS = [("Bombo", "bd_haus"), ("Tarola", "sn_dolf"), ("Pratos de choque", "hat_zild"),
         ("Prato de ataque", "drum_splash_hard"), ("Timbalão", "drum_tom_mid_hard"), ("Cowbell", "drum_cowbell")]

# the questions live in quizbank.py: TRIVIA rows (level 1-4, category, question, right, wrong x3) and
# generated theory questions. Ear questions are made here (they need sounds).
TRIVIA = qb.TRIVIA
DIFF = qb.LEVELS                          # FÁCIL, MÉDIO, DIFÍCIL, ESPECIALISTA
EAR_KINDS = {1: ["high4", "count", "mood2", "tempo", "drum"], 2: ["high4", "low4", "mood4", "drum", "interval3",
                                                               "count"],
             3: ["interval4", "bpm", "note", "scale", "mood4", "low4"]}
PRACTICE = [("OUVIDO", ["high4", "low4", "count", "interval3", "interval4", "note"], "Qual é mais aguda, quantas notas, intervalos"),
            ("ACORDES E ESCALAS", ["mood2", "mood4", "scale"], "Alegre, triste, tenso..."),
            ("RITMO", ["tempo", "bpm", "drum"], "Acelera ou abranda, BPM, sons da bateria"),
            ("TEORIA", ["theory"], "Acordes, intervalos, figuras, termos italianos"),
            ("CULTURA MUSICAL", ["trivia"], "%d perguntas: artistas, géneros, Portugal, cinema..." % len(qb.TRIVIA))]
PCOL = [(255, 138, 42), (60, 242, 255), (255, 110, 170), (124, 255, 138), (157, 107, 255), (255, 214, 80),
        (255, 90, 90), (120, 200, 255), (200, 160, 255), (180, 255, 210)]
NAME_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
PARTY_DIFF = ["A SUBIR", "FÁCIL", "MÉDIO", "DIFÍCIL", "ESPECIALISTA"]
ROUNDS = [3, 5, 8, 10, 15]


def diff_of(level):
    """ladder rung 0..14 -> difficulty 1..4"""
    return min(4, 1 + level // 4)


def clean_stats(saved):
    """quiz.json: values that would crash the quiz go back to their defaults"""
    st = dict(saved)
    st["best"] = int(engine.num(st.get("best"), -1, -1, len(LADDER) - 1))
    for k in ("games", "right", "asked"):
        st[k] = int(engine.num(st.get(k), 0))
    pc = st.pop("party_cfg", None)
    if isinstance(pc, dict):
        names = pc.get("names") if isinstance(pc.get("names"), list) else []
        names = [n if isinstance(n, str) and n else "JOGADOR %d" % (i + 1) for i, n in enumerate(names[:10])]
        st["party_cfg"] = {"n": int(engine.num(pc.get("n"), 4, 2, 10)),
                           "diff": int(engine.num(pc.get("diff"), 0, 0, len(PARTY_DIFF) - 1)),
                           "rounds": int(engine.num(pc.get("rounds"), 1, 0, len(ROUNDS) - 1)),
                           "names": names + ["JOGADOR %d" % (i + 1) for i in range(len(names), 10)]}
    pb = st.pop("party_best", None)
    if isinstance(pb, list) and len(pb) == 2 and engine.num(pb[1], None) is not None:
        st["party_best"] = pb
    return st


class Quiz(object):
    name = "DISCO VOADOR"

    def __init__(self, app):
        self.app = app
        self.ear = earlab.EarLab(app)          # tones, chords and clicks
        self.drums = {}
        saved = engine.load_save(SAVE)
        self.st = clean_stats(saved) if saved else {"best": -1, "games": 0, "right": 0, "asked": 0}
        if saved:
            engine.check_save(SAVE, saved, self.st)
        self.state = "menu"
        self.msel = 0
        self.psel = 0
        self.party = {"n": 4, "diff": 0, "rounds": 1, "names": ["JOGADOR %d" % (i + 1) for i in range(10)],
                      "scores": [0] * 10, "delta": [0] * 10, "round": 1, "turn": 0, "sel": 0, "nsel": 0,
                      "edit": None, "got": None}
        self.party.update(self.st.get("party_cfg", {}))
        self.reset()

    def reset(self):
        self.level = 0
        self.q = None
        self.cur = 0
        self.life = {"50": True, "poll": True, "xeno": True}
        self.removed = set()
        self.poll = None
        self.xeno = None
        self.t0 = time.time()
        self.used = set()
        self.result = None
        self.practice = None
        self.streak = 0

    def save(self):
        try:
            engine.write_json(SAVE, self.st)
        except Exception:
            pass

    # ---------------------------------------------------------------- sound
    def drum(self, name):
        if name not in self.drums:
            try:
                self.drums[name] = load_wav(os.path.join(engine.ASSETS, "forge", name + ".wav"))
            except Exception:
                self.drums[name] = None
        return self.drums[name]

    def sting(self, kind):
        e = self.ear
        if kind == "right":
            e.play([(i * 0.09, e.tone(n)) for i, n in enumerate((60, 64, 67, 72, 76))], 0.7)
        elif kind == "wrong":
            e.play([(0.0, e.tone(43)), (0.0, e.tone(44)), (0.35, e.tone(38)), (0.35, e.tone(39))], 0.6)
        elif kind == "suspense":
            e.play([(i * 0.42, e.tone(36 if i % 2 == 0 else 43)) for i in range(4)], 0.5)
        elif kind == "climb":
            e.play([(i * 0.06, e.tone(n)) for i, n in enumerate((55, 60, 64, 67, 72, 79, 84))], 0.55)

    # ---------------------------------------------------------------- questions
    def make(self, kind, lvl):
        """returns a question dict: text, opts (4), answer index, sound (callable or None)"""
        e = self.ear
        r = random.randint
        if kind == "trivia":
            lv = max(1, min(4, lvl))
            pool = [t for t in TRIVIA if t[0] == lv and t[2] not in self.used] or \
                [t for t in TRIVIA if abs(t[0] - lv) <= 1 and t[2] not in self.used] or [t for t in TRIVIA if t[0] == lv]
            t = random.choice(pool)
            self.used.add(t[2])
            opts = list(t[3:7])
            random.shuffle(opts)
            return {"text": t[2], "opts": opts, "answer": opts.index(t[3]), "sound": None, "kind": "trivia",
                    "cat": t[1], "lvl": t[0]}
        if kind == "theory":
            for _ in range(20):
                g = qb.gen_theory(max(1, min(4, lvl)))
                if g and g[0] not in self.used:
                    break
            text, right, opts = g
            self.used.add(text)
            return {"text": text, "opts": list(opts), "answer": list(opts).index(right), "sound": None,
                    "kind": "trivia", "cat": "TEORIA", "lvl": lvl}
        lvl = max(1, min(3, lvl))
        if kind in ("high4", "low4"):
            spread = {1: 7, 2: 4, 3: 2}[lvl]
            notes = []
            for _ in range(300):
                if len(notes) == 4:
                    break
                n = r(48, 78)
                if all(abs(n - m) >= spread for m in notes):
                    notes.append(n)
            if len(notes) < 4:                         # never loop forever: an evenly spaced fallback
                base = r(48, 78 - 3 * spread)
                notes = [base + i * spread for i in range(4)]
                random.shuffle(notes)
            target = max(notes) if kind == "high4" else min(notes)
            notes4 = list(notes)
            return {"text": "Ouve 4 notas. Qual é a mais %s?" % ("aguda" if kind == "high4" else "grave"),
                    "opts": ["A 1ª nota", "A 2ª nota", "A 3ª nota", "A 4ª nota"], "answer": notes.index(target),
                    "sound": lambda: e.notes(notes4, 0.6), "kind": "ear"}
        if kind == "count":
            n = r(2, 5) if lvl == 1 else r(3, 6)
            base = r(55, 67)
            seq = [base + random.choice([0, 2, 4, 5, 7, 9]) for _ in range(n)]
            gap = 0.5 if lvl == 1 else 0.32
            opts = [2, 3, 4, 5] if lvl == 1 else [3, 4, 5, 6]
            return {"text": "Quantas notas ouviste?", "opts": ["%d notas" % o for o in opts], "answer": opts.index(n),
                    "sound": lambda: e.notes(seq, gap), "kind": "ear"}
        if kind in ("mood2", "mood4"):
            moods = [("Alegre", [0, 4, 7]), ("Triste", [0, 3, 7]), ("Tenso", [0, 3, 6]), ("Suspenso", [0, 5, 7])]
            choice = random.choice(moods[:2] if kind == "mood2" else moods)
            root = r(52, 62)
            keys = [root + i for i in choice[1]]
            return {"text": "Como soa este acorde?", "opts": [m for m, _ in moods],
                    "answer": [m for m, _ in moods].index(choice[0]),
                    "sound": lambda: e.play([(i * 0.12, e.tone(k)) for i, k in enumerate(keys)] +
                                            [(0.9, e.tone(k)) for k in keys], 0.5), "kind": "ear"}
        if kind == "tempo":
            way = random.choice(["acc", "dec", "same", "stop"])
            times, t, bpm = [], 0.0, 100.0
            for i in range(12):
                if way == "stop" and i == 6:
                    t += 1.4
                times.append(t)
                bpm *= {"acc": 1.07, "dec": 0.94}.get(way, 1.0)
                t += 60.0 / bpm
            hi, lo = self.app.snd.get("click_hi"), self.app.snd.get("click_lo")
            opts = ["A acelerar", "A abrandar", "Sempre igual", "Parou a meio"]
            return {"text": "Ouve o ritmo. Como está ele?", "opts": opts,
                    "answer": ["acc", "dec", "same", "stop"].index(way),
                    "sound": lambda: e.play([(x, hi if i % 4 == 0 else lo) for i, x in enumerate(times)], 1.2),
                    "kind": "ear"}
        if kind == "drum":
            pick = random.sample(DRUMS, 4)
            ans = random.randrange(4)
            data = self.drum(pick[ans][1])
            return {"text": "Que som da bateria é este?", "opts": [p[0] for p in pick], "answer": ans,
                    "sound": (lambda: e.play([(0.0, data), (0.6, data), (1.2, data)], 0.9)) if data else None,
                    "kind": "ear"}
        if kind in ("interval3", "interval4"):
            names = [("Segunda (passo pequeno)", 2), ("Terceira", 4), ("Quinta", 7), ("Oitava (a mesma nota)", 12)]
            if kind == "interval4":
                names = random.sample([("Segunda", 2), ("Terceira menor", 3), ("Terceira maior", 4), ("Quarta", 5),
                                       ("Quinta", 7), ("Sexta", 9), ("Oitava", 12)], 4)
            ans = random.randrange(4)
            root = r(52, 64)
            keys = [root, root + names[ans][1]]
            return {"text": "Que distância há entre as duas notas?", "opts": [n for n, _ in names], "answer": ans,
                    "sound": lambda: e.notes(keys, 0.7), "kind": "ear"}
        if kind == "bpm":
            bpm = r(80, 160)
            opts = {bpm}
            for _ in range(500):
                if len(opts) == 4:
                    break
                c = bpm + random.choice([-1, 1]) * r(10, 40)
                if 60 <= c <= 190 and all(abs(c - o) >= 10 for o in opts):
                    opts.add(c)
            k = 1
            while len(opts) < 4:
                opts.add(bpm + 12 * k)
                k += 1
            opts = sorted(opts)
            return {"text": "Ouve o metrónomo. Qual é o BPM?", "opts": ["%d BPM" % o for o in opts],
                    "answer": opts.index(bpm), "sound": lambda: e.clicks(bpm, 8), "kind": "ear"}
        if kind == "note":
            names = ["DÓ", "RÉ", "MI", "FÁ", "SOL", "LÁ", "SI"]
            semis = [0, 2, 4, 5, 7, 9, 11]
            pick = random.sample(range(1, 7), 4)
            ans = random.randrange(4)
            k = semis[pick[ans]]
            return {"text": "Ouves um DÓ e depois outra nota. Qual é?", "opts": [names[i] for i in pick],
                    "answer": ans, "sound": lambda: e.notes([60, 60 + k], 0.9), "kind": "ear"}
        if kind == "scale":
            sc = [("Alegre (maior)", [0, 2, 4, 5, 7, 9, 11, 12]), ("Triste (menor)", [0, 2, 3, 5, 7, 8, 10, 12]),
                  ("Oriental (pentatónica)", [0, 2, 4, 7, 9, 12]), ("Blues", [0, 3, 5, 6, 7, 10, 12])]
            ans = random.randrange(4)
            root = r(55, 62)
            keys = [root + i for i in sc[ans][1]]
            return {"text": "Esta escala soa...", "opts": [n for n, _ in sc], "answer": ans,
                    "sound": lambda: e.notes(keys, 0.3), "kind": "ear"}
        return self.make("trivia", lvl)

    def pick_kind(self, lvl):
        r = random.random()
        if r < 0.55:
            return "trivia"
        if r < 0.7:
            return "theory"
        return random.choice(EAR_KINDS[max(1, min(3, lvl))])

    def next_question(self):
        lvl = diff_of(self.level)
        if self.practice is not None:
            kinds = PRACTICE[self.practice][1]
            lvl = 1 if self.streak < 4 else (2 if self.streak < 8 else (3 if self.streak < 13 else 4))
            kind = random.choice(kinds)
        else:
            kind = self.pick_kind(lvl)
        self.q = self.make(kind, lvl)
        self.q["diff"] = lvl
        self.cur = 0
        self.removed = set()
        self.poll = None
        self.xeno = None
        self.state = "q"
        self.t0 = time.time()
        if self.q["sound"]:
            self.q["sound"]()

    # ---------------------------------------------------------------- flow
    def start_game(self):
        self.reset()
        self.st["games"] = self.st.get("games", 0) + 1
        self.save()
        self.next_question()

    def start_practice(self, i):
        self.reset()
        self.practice = i
        self.next_question()

    def safe_prize(self):
        won = [i for i in SAFE if i < self.level]
        return won[-1] if won else -1

    def lock_answer(self):
        self.state = "suspense"
        self.t0 = time.time()
        self.sting("suspense")

    def reveal(self):
        q = self.q
        ok = self.cur == q["answer"]
        q["ok"] = ok
        self.st["asked"] = self.st.get("asked", 0) + 1
        self.st["right"] = self.st.get("right", 0) + (1 if ok else 0)
        self.state = "reveal"
        self.t0 = time.time()
        self.sting("right" if ok else "wrong")
        if self.practice is not None:
            self.streak = self.streak + 1 if ok else 0
            return
        if ok:
            self.st["best"] = max(self.st.get("best", -1), self.level)
            if self.level + 1 >= 5:
                self.app.mission("quiz_5")
        self.save()

    def after_reveal(self):
        q = self.q
        if self.practice is not None:
            self.next_question()
            return
        if q["ok"]:
            if self.level == len(LADDER) - 1:
                self.result = ("win", self.level)
                self.state = "over"
                self.sting("climb")
            else:
                self.level += 1
                self.state = "climb"
                self.t0 = time.time()
                self.sting("climb")
        else:
            self.result = ("lose", self.safe_prize())
            self.state = "over"
            self.t0 = time.time()

    def use(self, which):
        if self.practice is not None or not self.life.get(which) or self.state != "q":
            return
        self.life[which] = False
        q = self.q
        lvl = min(3, diff_of(self.level))
        wrong = [i for i in range(4) if i != q["answer"]]
        if which == "50":
            self.removed = set(random.sample(wrong, 2))
            if self.cur in self.removed:
                self.cur = q["answer"]
        elif which == "poll":
            good = random.uniform(*{1: (0.55, 0.8), 2: (0.4, 0.62), 3: (0.28, 0.48)}[lvl])
            winner = q["answer"] if random.random() < {1: 1.0, 2: 0.92, 3: 0.8}[lvl] else random.choice(wrong)
            rest = [random.random() for _ in range(4)]
            rest[winner] = 0
            tot = sum(rest) or 1
            self.poll = [good if i == winner else (1 - good) * rest[i] / tot for i in range(4)]
            for i in self.removed:
                self.poll[i] = 0.0
        else:
            right = random.random() < {1: 0.9, 2: 0.72, 3: 0.55}[lvl]
            pick = q["answer"] if right else random.choice([w for w in wrong if w not in self.removed] or wrong)
            sure = random.choice(["Tenho a certeza", "Acho que é", "Hmm... talvez"]) if right else \
                random.choice(["Acho que é", "Hmm... talvez", "Não sei bem... a"])
            self.xeno = (pick, sure)
        self.app.ui_ok()

    # ---------------------------------------------------------------- section interface
    def enter(self):
        self.state = "menu"

    def leave(self):
        self.app.mixer.kill_group("ear")

    def on_select(self):
        if self.state == "menu":
            self.app.go("bridge")
        elif self.state in ("practice_menu", "party_setup"):
            self.state = "menu"
        elif self.state in ("party_names", "party_edit"):
            self.state = "party_setup"
        else:
            self.app.mixer.kill_group("ear")
            self.state = "menu"

    def on(self, kind, b):
        if kind not in ("press", "repeat"):
            return
        st = self.state
        if st == "menu":
            if b in ("up", "down"):
                self.msel = (self.msel + (1 if b == "down" else -1)) % 3
                self.app.ui_move()
            elif b in ("a", "start") and kind == "press":
                self.app.ui_ok()
                if self.msel == 0:
                    self.start_game()
                elif self.msel == 1:
                    self.state = "party_setup"
                    self.party["sel"] = 4
                else:
                    self.state = "practice_menu"
            elif b == "b" and kind == "press":
                self.app.go("bridge")
        elif st == "practice_menu":
            if b in ("up", "down"):
                self.psel = (self.psel + (1 if b == "down" else -1)) % len(PRACTICE)
                self.app.ui_move()
            elif b == "a" and kind == "press":
                self.start_practice(self.psel)
            elif b == "b" and kind == "press":
                self.state = "menu"
        elif st == "q":
            if b in ("up", "down", "left", "right"):
                c = self.cur
                c = {"up": c - 2 if c >= 2 else c, "down": c + 2 if c < 2 else c,
                     "left": c - 1 if c % 2 else c, "right": c + 1 if c % 2 == 0 else c}[b]
                if c not in self.removed:
                    self.cur = c
                    self.app.ui_move()
            elif kind != "press":
                return
            elif b == "a":                               # the answer is locked at once (no "final answer?")
                self.lock_answer()
                if self.practice is not None:
                    self.t0 = time.time() - 1.0          # practice: short suspense
            elif b == "x" and self.q["sound"]:
                self.q["sound"]()
            elif b == "l1":
                self.use("50")
            elif b == "r1":
                self.use("poll")
            elif b == "l2":
                self.use("xeno")
            elif b == "b":
                self.state = "menu" if self.practice is not None else "quit"
        elif st == "quit" and kind == "press":
            if b == "a":
                self.result = ("quit", self.level - 1)
                self.state = "over"
                self.t0 = time.time()
            elif b == "b":
                self.state = "q"
        elif st == "reveal" and kind == "press" and time.time() - self.t0 > 0.6 and b in ("a", "b"):
            self.after_reveal()
        elif st == "climb" and kind == "press" and b in ("a", "b"):
            self.next_question()
        elif st == "over" and kind == "press" and time.time() - self.t0 > 1.0:
            if b == "a":
                self.start_game()
            elif b == "b":
                self.state = "menu"
        elif st.startswith("party"):
            self.party_on(kind, b)

    def update(self, dt):
        if self.state == "party_q" and time.time() - self.t0 > self.q["limit"]:
            self.party_lock(None)                       # time is up: no answer
        if self.state == "suspense" and time.time() - self.t0 > 1.9:
            self.reveal()
        elif self.state == "reveal" and time.time() - self.t0 > 2.6:
            self.after_reveal()
        elif self.state == "climb" and time.time() - self.t0 > 2.2:
            self.next_question()

    # ---------------------------------------------------------------- drawing
    def stage(self, g, t):
        """show lights: dark violet, rays from the top, a gold floor line"""
        g.clear((10, 4, 26))
        for i in range(7):
            x = 40 + i * 95
            a = int(28 + 20 * math.sin(t * 1.3 + i))
            pts = [(x + (k * (i - 3) * 0.6) - 3 - k * 0.35, k, 6 + k * 0.7, 4) for k in range(0, 300, 4)]
            g.rects(pts, (120, 70, 220), a)
        g.rect(0, H - 60, W, 2, GOLD_DK)

    def disc(self, g, cx, cy, r, t):
        cols = [(GOLD, 1.0), ((255, 236, 150), 0.86), (GOLD, 0.8), (GOLD_DK, 0.62), (GOLD, 0.58), ((40, 20, 0), 0.2)]
        for col, f in cols:
            rr = int(r * f)
            g.rects([(cx - int(math.sqrt(max(0, rr * rr - dy * dy))), cy + dy,
                      2 * int(math.sqrt(max(0, rr * rr - dy * dy))), 2) for dy in range(-rr, rr, 2)], col)
        a = t * 2.0
        g.rect(cx + math.cos(a) * r * 0.7 - 3, cy + math.sin(a) * r * 0.7 - 3, 6, 6, (255, 255, 230))

    def draw(self, g, t, dt):
        self.stage(g, t)
        st = self.state
        if st == "menu":
            return self.draw_menu(g, t)
        if st == "practice_menu":
            return self.draw_practice_menu(g, t)
        if st.startswith("party"):
            return self.draw_party(g, t)
        if st == "over":
            return self.draw_over(g, t)
        self.draw_question(g, t)
        if st == "quit":
            prize = LADDER[self.level - 1] if self.level > 0 else "nada"
            self.dialog(g, "DESISTIR?", "Ficas com: %s" % prize, [("A", "desistir"), ("B", "continuar")])
        elif st == "climb":
            g.rect(0, 0, W, H, (10, 4, 26), 160)
            g.text(ui.SMALL, "PERGUNTA %d DE 15" % (self.level + 1), W // 2, 150, C["muted"], 255, "center")
            g.text(ui.TITLE, LADDER[self.level - 1].upper(), W // 2, 176, GOLD, 255, "center")
            if self.level - 1 in SAFE:
                g.text(ui.HEAD, "★ PATAMAR GARANTIDO ★", W // 2, 230, C["green"], 255, "center")
            g.text(ui.SMALL, "a seguir: %s" % LADDER[self.level], W // 2, 280, C["soft"], 255, "center")

    def draw_menu(self, g, t):
        self.disc(g, W // 2, 92, 58, t)
        g.text(ui.DISPLAY, "DISCO VOADOR", W // 2 + 3, 165, (60, 30, 0), 255, "center")
        g.text(ui.DISPLAY, "DISCO VOADOR", W // 2, 162, GOLD, 255, "center")
        g.text(ui.SMALL, "%d perguntas de música, do fácil ao especialista" % len(TRIVIA), W // 2, 214,
               C["soft"], 255, "center")
        for i, (lab, sub) in enumerate((("JOGAR", "15 perguntas, do fácil ao especialista, 3 ajudas"),
                                        ("FESTA", "2 a 10 jogadores, cada um com a sua pontuação"),
                                        ("TREINO LIVRE", "sem pressão, por tema"))):
            y = 246 + i * 52
            sel = i == self.msel
            ui.box(g, W // 2 - 190, y, 380, 44, GOLD if sel else (40, 24, 70))
            g.text(ui.HEAD, lab, W // 2, y + 2, (40, 20, 0) if sel else C["text"], 255, "center")
            g.text(ui.SMALL, sub, W // 2, y + 24, (80, 50, 0) if sel else C["muted"], 255, "center")
        best = self.st.get("best", -1)
        pb = self.st.get("party_best")
        rec = "Recorde: %s" % (LADDER[best] if best >= 0 else "ainda nenhum")
        if pb:
            rec += "   ·   Festa: %s %d pts" % (pb[0], pb[1])
        g.text(ui.SMALL, rec, W // 2, 406, GOLD, 255, "center")
        ui.footer(g, [("A", "escolher"), ("cima/baixo", "mudar"), ("B", "sair")])

    def draw_practice_menu(self, g, t):
        g.text(ui.TITLE, "TREINO LIVRE", W // 2, 40, GOLD, 255, "center")
        g.text(ui.SMALL, "Perguntas sem fim. Acerta seguidas e ficam mais difíceis.", W // 2, 84, C["soft"], 255,
               "center")
        for i, (lab, _, sub) in enumerate(PRACTICE):
            y = 112 + i * 62
            sel = i == self.psel
            ui.box(g, 100, y, 440, 56, GOLD if sel else (40, 24, 70))
            g.text(ui.HEAD, lab, 120, y + 4, (40, 20, 0) if sel else C["text"])
            g.text(ui.SMALL, sub, 120, y + 30, (80, 50, 0) if sel else C["muted"])
        ui.footer(g, [("A", "começar"), ("cima/baixo", "escolher"), ("B", "voltar")])

    def draw_question(self, g, t):
        q = self.q
        practice = self.practice is not None
        # ladder (right)
        lx = 452
        if not practice:
            for i in range(len(LADDER) - 1, -1, -1):
                y = 14 + (len(LADDER) - 1 - i) * 26
                cur = i == self.level
                done = i < self.level
                if cur:
                    ui.box(g, lx, y, W - lx - 8, 24, C["orange"])
                col = C["void"] if cur else (GOLD if i in SAFE or i == len(LADDER) - 1 else (C["muted"] if done else C["soft"]))
                g.text(ui.SMALL, "%2d" % (i + 1), lx + 6, y + 2, col)
                g.text(ui.SMALL, ui.fit(g, ui.SMALL, LADDER[i], W - lx - 52), lx + 34, y + 2, col)
        else:
            ui.panel(g, lx, 20, W - lx - 8, 120, GOLD, "TREINO")
            g.text(ui.SMALL, PRACTICE[self.practice][0], lx + 12, 40, C["text"])
            g.text(ui.SMALL, "seguidas", lx + 12, 70, C["muted"])
            g.text(ui.TITLE, "%d" % self.streak, lx + 12, 88, GOLD)
        # lifelines (top left)
        if not practice:
            for i, (k, lab, key) in enumerate((("50", "50:50", "L1"), ("poll", "SONDAGEM", "R1"), ("xeno", "XENO", "L2"))):
                x = 14 + i * 142
                on = self.life[k]
                ui.box(g, x, 12, 132, 30, (60, 34, 110) if on else (24, 16, 40))
                xe = ui.keys(g, key, x + 6, 18)
                g.text(ui.SMALL, lab, xe + 4, 17, C["text"] if on else C["dim"])
                if not on:
                    g.rect(x + 4, 26, 124, 2, (255, 80, 80))
            prize_y = 52
        else:
            prize_y = 16
        # question box
        qx, qy, qw, qh = 14, prize_y, 428, 150 if not practice else 186
        ui.box(g, qx, qy, qw, qh, (26, 14, 56))
        ui.outline(g, qx, qy, qw, qh, GOLD, 2)
        if not practice:
            g.text(ui.SMALL, "PERGUNTA %d  ·  %s" % (self.level + 1, LADDER[self.level]), qx + 12, qy + 6, GOLD)
        ui.para(g, ui.BODY, q["text"], qx + 14, qy + 30, qw - 28, C["text"], 30)
        if q["sound"]:
            playing = time.time() < self.ear.sound_end
            sx, sy = qx + 14, qy + qh - 34
            g.rects([(sx, sy + 8, 8, 12), (sx + 8, sy + 4, 6, 20)], GOLD)
            for k in range(3):
                if playing and int(t * 6 + k) % 3:
                    g.rect(sx + 18 + k * 6, sy + 12 - k * 4, 3, 4 + k * 8, GOLD)
            xe = ui.keys(g, "X", sx + 46, sy + 5)
            g.text(ui.SMALL, "ouvir outra vez", xe + 4, sy + 4, C["soft"])
        # answers 2x2
        ay = qy + qh + 12
        bw, bh = 208, 56
        for i in range(4):
            x = qx + (i % 2) * (bw + 12)
            y = ay + (i // 2) * (bh + 10)
            gone = i in self.removed
            fill, fg, letter = (44, 26, 84), C["text"], GOLD
            if gone:
                fill, fg, letter = (20, 12, 36), C["dim"], C["dim"]
            elif self.state in ("q", "quit") and i == self.cur:
                fill, fg, letter = C["orange"], C["void"], C["void"]
            elif self.state == "suspense" and i == self.cur:
                blink = int(t * 6) % 2
                fill, fg, letter = (C["orange"] if blink else (255, 190, 90)), C["void"], C["void"]
            elif self.state in ("reveal", "climb"):
                if i == q["answer"]:
                    fill, fg, letter = (C["green"] if int(t * 5) % 2 or q.get("ok") else (60, 160, 70)), C["void"], C["void"]
                elif i == self.cur:
                    fill, fg, letter = (230, 60, 70), C["void"], C["void"]
            ui.box(g, x, y, bw, bh, fill, cut=6)
            g.text(ui.HEAD, LETTERS[i], x + 10, y + 12, letter)
            tx = x + 10 + g.tw(ui.HEAD, LETTERS[i]) + 10
            if not gone:
                room = bw - (tx - x) - 10
                font = ui.SMALL if g.tw(ui.BODY, q["opts"][i]) > room else ui.BODY
                ln = ui.wrap(g, font, q["opts"][i], room)
                yy = y + (bh - len(ln[:2]) * (g.th(font) - 2)) // 2 - 2
                for l2 in ln[:2]:
                    g.text(font, l2, tx, yy, fg)
                    yy += g.th(font) - 2
            if self.poll and not gone:
                p = self.poll[i]
                g.rect(x + bw - 14, y + bh - 6 - int((bh - 12) * p), 8, int((bh - 12) * p), C["cyan"])
                g.text(ui.SMALL, "%d%%" % round(p * 100), x + bw - 18, y + 2, C["cyan"], 255, "right")
        if self.xeno:
            pick, sure = self.xeno
            pn = self.app.sections["pet"].p.get("name") or "XENO"
            ui.box(g, qx, ay - 34 + 2 * (bh + 10) + 46, qw, 26, (30, 18, 60))
            g.text(ui.SMALL, "%s: \"%s %s!\"" % (pn, sure, LETTERS[pick]), qx + 10, ay + 2 * (bh + 10) + 14,
                   (255, 110, 170))
        if self.state == "reveal":
            ok = q.get("ok")
            g.text(ui.TITLE, "CERTO!" if ok else "ERRADO", 228, H - 50, C["green"] if ok else (255, 90, 100), 255,
                   "center")
        elif self.state == "q":
            if practice:
                ui.footer(g, [("setas", "escolher"), ("A", "responder"), ("B", "sair")], hints=False)
            else:
                ui.footer(g, [("setas", "escolher"), ("A", "responder"), ("B", "desistir")], hints=False)

    def dialog(self, g, title, line, keys):
        g.rect(0, 0, W, H, (10, 4, 26), 150)
        x, y, w, h = 90, 150, 460, 170
        ui.box(g, x, y, w, h, (26, 14, 56))
        ui.outline(g, x, y, w, h, GOLD, 3)
        g.text(ui.TITLE, title, W // 2, y + 18, GOLD, 255, "center")
        ui.para(g, ui.BODY, line, x + 20, y + 66, w - 40, C["text"], 30, "left")
        xx = x + 24
        for k, lab in keys:
            xe = ui.keys(g, k, xx, y + h - 34)
            g.text(ui.BODY, lab, xe + 6, y + h - 40, C["text"])
            xx = xe + 30 + g.tw(ui.BODY, lab)

    def draw_over(self, g, t):
        kind, lvl = self.result
        self.disc(g, W // 2, 120, 60 if kind == "win" else 44, t)
        if kind == "win":
            g.text(ui.DISPLAY, "DISCO DE DIAMANTE!", W // 2, 196, (180, 240, 255), 255, "center")
            g.text(ui.BODY, "Respondeste às 15. És uma lenda da nave.", W // 2, 260, C["text"], 255, "center")
        else:
            title = "DESISTISTE" if kind == "quit" else "FIM DO JOGO"
            g.text(ui.TITLE, title, W // 2, 190, GOLD, 255, "center")
            if kind == "lose" and self.q:
                g.text(ui.SMALL, "A resposta certa era: %s" % self.q["opts"][self.q["answer"]], W // 2, 236,
                       C["soft"], 255, "center")
            g.text(ui.SMALL, "Ficas com", W // 2, 270, C["muted"], 255, "center")
            g.text(ui.HEAD, LADDER[lvl] if lvl >= 0 else "a experiência (e já é muito)", W // 2, 290, GOLD, 255,
                   "center")
        best = self.st.get("best", -1)
        g.text(ui.SMALL, "Recorde: %s" % (LADDER[best] if best >= 0 else "-"), W // 2, 340, C["muted"], 255, "center")
        ui.footer(g, [("A", "jogar outra vez"), ("B", "menu")], hints=False)

    # ================================================================ FESTA (2-10 players)
    def party_lvl(self):
        P = self.party
        if P["diff"]:
            return P["diff"]
        R = ROUNDS[P["rounds"]]
        return min(4, 1 + int((P["round"] - 1) * 4 / R))

    def party_start(self):
        P = self.party
        self.reset()
        n = P["n"]
        P["scores"] = [0] * n
        P["delta"] = [0] * n
        P["round"], P["turn"] = 1, 0
        self.st["party_cfg"] = {"n": n, "diff": P["diff"], "rounds": P["rounds"], "names": P["names"]}
        self.save()
        self.state = "party_turn"
        self.t0 = time.time()

    def party_ask(self):
        lvl = self.party_lvl()
        self.q = self.make(self.pick_kind(lvl), lvl)
        self.q["diff"] = lvl
        self.q["limit"] = 25.0 if self.q["sound"] else 20.0
        self.cur = 0
        self.removed = set()
        self.state = "party_q"
        self.t0 = time.time()
        if self.q["sound"]:
            self.q["sound"]()

    def party_lock(self, choice):
        P = self.party
        q = self.q
        left = max(0.0, q["limit"] - (time.time() - self.t0))
        ok = choice is not None and choice == q["answer"]
        pts = 0
        if ok:
            pts = q["diff"] * 100 + int(round(q["diff"] * 5 * left / q["limit"])) * 10
        q["ok"], q["pick"] = ok, choice
        P["got"] = pts
        P["scores"][P["turn"]] += pts
        P["delta"][P["turn"]] = pts
        self.st["asked"] = self.st.get("asked", 0) + 1
        self.st["right"] = self.st.get("right", 0) + (1 if ok else 0)
        self.state = "party_reveal"
        self.t0 = time.time()
        self.sting("right" if ok else "wrong")

    def party_next(self):
        P = self.party
        P["turn"] += 1
        if P["turn"] < P["n"]:
            self.state = "party_turn"
        else:
            self.state = "party_board"
            self.sting("climb")
        self.t0 = time.time()

    def party_after_board(self):
        P = self.party
        if P["round"] >= ROUNDS[P["rounds"]]:
            self.state = "party_over"
            best = max(range(P["n"]), key=lambda i: P["scores"][i])
            pb = self.st.get("party_best")
            if not pb or P["scores"][best] > pb[1]:
                self.st["party_best"] = [P["names"][best], P["scores"][best]]
            self.save()
            self.sting("climb")
        else:
            P["round"] += 1
            P["turn"] = 0
            P["delta"] = [0] * P["n"]
            self.state = "party_turn"
        self.t0 = time.time()

    def standings(self):
        P = self.party
        order = sorted(range(P["n"]), key=lambda i: -P["scores"][i])
        out, place = [], 0
        for k, i in enumerate(order):
            if k == 0 or P["scores"][i] != P["scores"][order[k - 1]]:
                place = k + 1
            out.append((place, i))
        return out

    def party_on(self, kind, b):
        P = self.party
        st = self.state
        if kind not in ("press", "repeat"):
            return
        if st == "party_setup":
            if b in ("up", "down"):
                P["sel"] = (P["sel"] + (1 if b == "down" else -1)) % 5
                self.app.ui_move()
            elif b in ("left", "right"):
                d = 1 if b == "right" else -1
                if P["sel"] == 0:
                    P["n"] = max(2, min(10, P["n"] + d))
                elif P["sel"] == 1:
                    P["diff"] = (P["diff"] + d) % len(PARTY_DIFF)
                elif P["sel"] == 2:
                    P["rounds"] = max(0, min(len(ROUNDS) - 1, P["rounds"] + d))
                self.app.ui_move()
            elif kind == "press" and b in ("a", "start"):
                self.app.ui_ok()
                if P["sel"] == 3:
                    self.state, P["nsel"] = "party_names", 0
                elif P["sel"] == 4 or b == "start":
                    self.party_start()
            elif kind == "press" and b == "b":
                self.state = "menu"
        elif st == "party_names":
            n = P["n"]
            if b in ("up", "down"):
                P["nsel"] = (P["nsel"] + (1 if b == "down" else -1)) % n
                self.app.ui_move()
            elif b in ("left", "right") and n > 5:
                j = P["nsel"] - 5 if P["nsel"] >= 5 else P["nsel"] + 5
                if 0 <= j < n:
                    P["nsel"] = j
                    self.app.ui_move()
            elif kind == "press" and b == "a":
                name = P["names"][P["nsel"]]
                buf = list(name[:8]) if not name.startswith("JOGADOR") else ["A"]
                P["edit"] = {"buf": buf, "pos": 0}
                self.state = "party_edit"
            elif kind == "press" and b == "start":
                self.party_start()
            elif kind == "press" and b == "b":
                self.state = "party_setup"
        elif st == "party_edit":
            e = P["edit"]
            buf, pos = e["buf"], e["pos"]
            if b in ("up", "down"):
                c = buf[pos] if buf[pos] in NAME_CHARS else "A"
                k = (NAME_CHARS.index(c) + (1 if b == "up" else -1)) % len(NAME_CHARS)
                buf[pos] = NAME_CHARS[k]
            elif b == "right":
                if pos == len(buf) - 1 and len(buf) < 8:
                    buf.append(buf[pos] if buf[pos] != " " else "A")
                e["pos"] = min(len(buf) - 1, pos + 1)
            elif b == "left":
                e["pos"] = max(0, pos - 1)
            elif kind == "press" and b == "x" and len(buf) > 1:
                del buf[pos]
                e["pos"] = min(pos, len(buf) - 1)
            elif kind == "press" and b in ("a", "start"):
                name = "".join(buf).strip()
                P["names"][P["nsel"]] = name or "JOGADOR %d" % (P["nsel"] + 1)
                self.state = "party_names"
                self.app.ui_ok()
            elif kind == "press" and b == "b":
                self.state = "party_names"
        elif st == "party_turn" and kind == "press":
            if b in ("a", "start") and time.time() - self.t0 > 0.4:
                self.party_ask()
            elif b == "b":
                self.state = "party_quit"
        elif st == "party_quit" and kind == "press":
            if b == "a":
                self.state = "party_over"
                self.t0 = time.time()
            elif b == "b":
                self.state = "party_turn"
        elif st == "party_q":
            if b in ("up", "down", "left", "right"):
                c = self.cur
                self.cur = {"up": c - 2 if c >= 2 else c, "down": c + 2 if c < 2 else c,
                            "left": c - 1 if c % 2 else c, "right": c + 1 if c % 2 == 0 else c}[b]
                self.app.ui_move()
            elif kind == "press" and b == "a":
                self.party_lock(self.cur)
            elif kind == "press" and b == "x" and self.q["sound"]:
                self.q["sound"]()
        elif st == "party_reveal" and kind == "press" and time.time() - self.t0 > 0.6 and b in ("a", "b", "start"):
            self.party_next()
        elif st == "party_board" and kind == "press" and time.time() - self.t0 > 0.6 and b in ("a", "start"):
            self.party_after_board()
        elif st == "party_over" and kind == "press" and time.time() - self.t0 > 1.0:
            if b == "a":
                self.party_start()
            elif b == "b":
                self.state = "menu"

    # ---------------------------------------------------------------- FESTA drawing
    def draw_party(self, g, t):
        st = self.state
        P = self.party
        if st == "party_setup":
            g.text(ui.TITLE, "FESTA", W // 2, 24, GOLD, 255, "center")
            g.text(ui.SMALL, "Passem a consola: cada um responde à sua pergunta, ronda a ronda.", W // 2, 68,
                   C["soft"], 255, "center")
            rows = [("JOGADORES", "%d" % P["n"], True), ("DIFICULDADE", PARTY_DIFF[P["diff"]], True),
                    ("RONDAS", "%d" % ROUNDS[P["rounds"]], True), ("NOMES", "A para mudar", False),
                    ("COMEÇAR", "", False)]
            for i, (lab, val, arrows) in enumerate(rows):
                y = 104 + i * 58
                sel = i == P["sel"]
                ui.box(g, 80, y, 480, 48, GOLD if sel else (40, 24, 70))
                fg = (40, 20, 0) if sel else C["text"]
                if lab == "COMEÇAR":
                    g.text(ui.HEAD, "▶ COMEÇAR", W // 2, y + 9, fg, 255, "center")
                    continue
                g.text(ui.HEAD, lab, 100, y + 9, fg)
                vx = 540
                if arrows:
                    g.text(ui.HEAD, "<  %s  >" % val if sel else val, vx, y + 9, fg, 255, "right")
                else:
                    g.text(ui.SMALL, val, vx, y + 14, (80, 50, 0) if sel else C["muted"], 255, "right")
            # the players, as coloured chips
            x = 80
            for i in range(P["n"]):
                g.rect(x + i * 48, 400, 40, 8, PCOL[i])
            hint = {0: "2 a 10 jogadores", 1: "A SUBIR começa fácil e acaba especialista",
                    2: "quantas perguntas responde cada jogador", 3: "dá um nome a cada jogador",
                    4: "carrega A para começar"}[P["sel"]]
            g.text(ui.SMALL, hint, W // 2, 412, C["soft"], 255, "center")
            ui.footer(g, [("cima/baixo", "escolher"), ("esq/dir", "mudar"), ("A", "ok"), ("B", "voltar")],
                      hints=False)
            return
        if st in ("party_names", "party_edit"):
            g.text(ui.TITLE, "NOMES", W // 2, 24, GOLD, 255, "center")
            for i in range(P["n"]):
                col, row = (i // 5, i % 5) if P["n"] > 5 else (0, i)
                x = 40 + col * 290 if P["n"] > 5 else 140
                w = 270 if P["n"] > 5 else 360
                y = 84 + row * 62
                sel = i == P["nsel"]
                ui.box(g, x, y, w, 52, GOLD if sel else (40, 24, 70))
                g.rect(x + 10, y + 12, 28, 28, PCOL[i])
                g.text(ui.HEAD, "%d" % (i + 1), x + 24, y + 12, C["void"], 255, "center")
                name = P["names"][i]
                if st == "party_edit" and sel:
                    e = P["edit"]
                    xx = x + 52
                    for k, ch in enumerate(e["buf"]):
                        on = k == e["pos"]
                        if on:
                            g.rect(xx - 2, y + 6, 22, 40, C["void"])
                        g.text(ui.HEAD, ch if ch != " " else "_", xx + 9, y + 9, GOLD if on else (40, 20, 0), 255,
                               "center")
                        if on and int(t * 4) % 2:
                            g.text(ui.SMALL, "▲", xx + 9, y - 10, C["text"], 255, "center")
                        xx += 22
                else:
                    g.text(ui.HEAD, ui.fit(g, ui.HEAD, name, w - 64), x + 52, y + 9, (40, 20, 0) if sel else C["text"])
            if st == "party_edit":
                ui.footer(g, [("cima/baixo", "letra"), ("esq/dir", "posição"), ("X", "apagar"), ("A", "guardar")],
                          hints=False)
            else:
                ui.footer(g, [("A", "mudar nome"), ("START", "começar"), ("B", "voltar")], hints=False)
            return
        if st in ("party_turn", "party_quit"):
            i = P["turn"]
            col = PCOL[i]
            g.text(ui.SMALL, "RONDA %d DE %d  ·  %s" % (P["round"], ROUNDS[P["rounds"]], DIFF[self.party_lvl() - 1]),
                   W // 2, 70, C["muted"], 255, "center")
            g.text(ui.HEAD, "VEZ DE", W // 2, 120, C["soft"], 255, "center")
            ui.box(g, 90, 160, 460, 96, col)
            g.text(ui.DISPLAY, ui.fit(g, ui.DISPLAY, P["names"][i], 440), W // 2, 178, C["void"], 255, "center")
            g.text(ui.BODY, "%d pontos" % P["scores"][i], W // 2, 280, GOLD, 255, "center")
            if int(t * 2) % 2:
                g.text(ui.SMALL, "passa a consola a %s e carrega A" % P["names"][i], W // 2, 340, C["text"], 255,
                       "center")
            ui.footer(g, [("A", "ver a pergunta"), ("B", "acabar o jogo")], hints=False)
            if st == "party_quit":
                self.dialog(g, "ACABAR A FESTA?", "Mostra já a classificação final.", [("A", "acabar"), ("B", "continuar")])
            return
        if st in ("party_q", "party_reveal"):
            return self.draw_party_q(g, t)
        if st == "party_board":
            g.text(ui.TITLE, "CLASSIFICAÇÃO", W // 2, 14, GOLD, 255, "center")
            g.text(ui.SMALL, "depois da ronda %d de %d" % (P["round"], ROUNDS[P["rounds"]]), W // 2, 54, C["muted"],
                   255, "center")
            self.draw_table(g, 70, 30 if P["n"] > 6 else 40)
            ui.footer(g, [("A", "continuar")], hints=False)
            return
        if st == "party_over":
            return self.draw_podium(g, t)

    def draw_table(self, g, y0, rh):
        P = self.party
        for row, (place, i) in enumerate(self.standings()):
            y = y0 + row * (rh + 4)
            ui.box(g, 70, y, 500, rh, (40, 24, 70) if place > 1 else (90, 64, 20))
            g.text(ui.HEAD if rh >= 36 else ui.SMALL, "%dº" % place, 96, y + (rh - (30 if rh >= 36 else 20)) // 2,
                   GOLD if place == 1 else C["soft"], 255, "center")
            g.rect(122, y + 6, rh - 12, rh - 12, PCOL[i])
            f = ui.HEAD if rh >= 36 else ui.BODY
            g.text(f, ui.fit(g, f, P["names"][i], 250), 122 + rh, y + (rh - g.th(f)) // 2, C["text"])
            g.text(f, "%d" % P["scores"][i], 470, y + (rh - g.th(f)) // 2, GOLD, 255, "right")
            d = P["delta"][i]
            if d:
                g.text(ui.SMALL, "+%d" % d, 558, y + (rh - 20) // 2, C["green"], 255, "right")

    def draw_podium(self, g, t):
        P = self.party
        g.text(ui.TITLE, "FIM DA FESTA", W // 2, 12, GOLD, 255, "center")
        table = self.standings()
        spots = [(W // 2, 120), (W // 2 - 170, 80), (W // 2 + 170, 56)]
        for k, (place, i) in enumerate(table[:3]):
            cx, hgt = spots[k]
            hgt = {1: 120, 2: 80}.get(place, 56)
            base = 300
            ui.box(g, cx - 75, base - hgt, 150, hgt, PCOL[i])
            g.text(ui.DISPLAY, "%d" % place, cx, base - hgt + (hgt - 60) // 2 + 4, C["void"], 255, "center")
            g.text("kb16", ui.fit(g, "kb16", P["names"][i], 160), cx, base - hgt - 54, C["text"], 255, "center")
            g.text(ui.BODY, "%d pts" % P["scores"][i], cx, base - hgt - 32, GOLD, 255, "center")
        if table and int(t * 3) % 2:
            g.text(ui.HEAD, "★", spots[0][0], 300 - 120 - 96, GOLD, 255, "center")
        rest = table[3:]
        for k, (place, i) in enumerate(rest):
            x = 70 + (k % 2) * 260
            y = 316 + (k // 2) * 26
            g.text(ui.SMALL, "%dº  %s  %d" % (place, P["names"][i], P["scores"][i]), x, y, C["soft"])
        ui.footer(g, [("A", "jogar outra vez"), ("B", "menu")], hints=False)

    def draw_party_q(self, g, t):
        P = self.party
        q = self.q
        i = P["turn"]
        col = PCOL[i]
        # top: who, round, difficulty, time
        ui.box(g, 14, 10, 300, 34, col)
        g.text(ui.HEAD, ui.fit(g, ui.HEAD, P["names"][i], 280), 26, 12, C["void"])
        g.text(ui.SMALL, "RONDA %d/%d · %s" % (P["round"], ROUNDS[P["rounds"]], DIFF[q["diff"] - 1]), W - 14, 10,
               C["muted"], 255, "right")
        left = max(0.0, q["limit"] - (time.time() - self.t0)) if self.state == "party_q" else 0.0
        frac = left / q["limit"]
        bar_col = C["green"] if frac > 0.5 else (C["orange"] if frac > 0.25 else (255, 80, 90))
        ui.bar(g, 330, 32, W - 344, 8, frac, bar_col)
        # question
        qx, qy, qw, qh = 14, 54, W - 28, 140
        ui.box(g, qx, qy, qw, qh, (26, 14, 56))
        ui.outline(g, qx, qy, qw, qh, GOLD, 2)
        g.text(ui.SMALL, q.get("cat", "OUVIDO") if q["kind"] == "trivia" else "OUVIDO", qx + 12, qy + 6, GOLD)
        ui.para(g, ui.BODY, q["text"], qx + 14, qy + 30, qw - 28, C["text"], 30)
        if q["sound"]:
            xe = ui.keys(g, "X", qx + 14, qy + qh - 30)
            g.text(ui.SMALL, "ouvir outra vez", xe + 4, qy + qh - 31, C["soft"])
        # answers
        ay = qy + qh + 12
        bw, bh = (qw - 12) // 2, 62
        for k in range(4):
            x = qx + (k % 2) * (bw + 12)
            y = ay + (k // 2) * (bh + 10)
            fill, fg, letter = (44, 26, 84), C["text"], GOLD
            if self.state == "party_q" and k == self.cur:
                fill, fg, letter = col, C["void"], C["void"]
            elif self.state == "party_reveal":
                if k == q["answer"]:
                    fill, fg, letter = C["green"], C["void"], C["void"]
                elif k == q.get("pick"):
                    fill, fg, letter = (230, 60, 70), C["void"], C["void"]
            ui.box(g, x, y, bw, bh, fill, cut=6)
            g.text(ui.HEAD, LETTERS[k], x + 12, y + (bh - 30) // 2, letter)
            tx = x + 12 + g.tw(ui.HEAD, LETTERS[k]) + 12
            room = bw - (tx - x) - 10
            font = ui.SMALL if g.tw(ui.BODY, q["opts"][k]) > room else ui.BODY
            ln = ui.wrap(g, font, q["opts"][k], room)
            yy = y + (bh - len(ln[:2]) * (g.th(font) - 2)) // 2 - 2
            for l2 in ln[:2]:
                g.text(font, l2, tx, yy, fg)
                yy += g.th(font) - 2
        if self.state == "party_reveal":
            ok = q.get("ok")
            msg = ("CERTO!  +%d" % P["got"]) if ok else ("TEMPO!" if q.get("pick") is None else "ERRADO")
            g.text(ui.TITLE, msg, W // 2, H - 84, C["green"] if ok else (255, 90, 100), 255, "center")
            ui.footer(g, [("A", "continuar")], hints=False)
        else:
            ui.footer(g, [("setas", "escolher"), ("A", "responder")] + ([("X", "ouvir")] if q["sound"] else []),
                      hints=False)
