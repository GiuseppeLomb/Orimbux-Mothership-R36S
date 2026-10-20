# Beginner missions: a checklist on the Bridge that ticks itself as you use the apps.
# Mission 1 walks the music workflow; mission 2 teaches the remix tools.
import time

MISSIONS = [
    ("A TUA PRIMEIRA MÚSICA", [
        ("pulsar_bpm", "Escolhe o tempo", "PULSAR: esq/dir muda o BPM", "pulsar"),
        ("forge_play", "Faz um ritmo", "BEAT FORGE: A liga passos, B toca", "forge"),
        ("reactor_pad", "Toca um loop", "LOOP REACTOR: carrega num pad", "reactor"),
        ("xeno_notes", "Toca uma melodia", "XENO SYNTH: toca 8 notas", "xeno"),
        ("session_saved", "Grava uma sessão", "Segura START e carrega Y", None),
        ("duel_session", "Joga a tua música", "BEAT DUEL: escolhe a tua sessão", "beatduel"),
    ]),
    ("O REMIX", [
        ("chop_slices", "Corta uma música", "ABDUCTOR: CORTAR e ouve as fatias", "abductor"),
        ("chop_to_reactor", "Leva as fatias", "ABDUCTOR: SELECT+X manda para o Reactor", "abductor"),
        ("decks_both", "Mistura duas", "TWIN DECKS: põe os dois decks a tocar", "decks"),
        ("vox_live", "Põe a tua voz", "VOX NEBULA: R2 liga o micro", "vox"),
        ("quiz_5", "Treina o ouvido", "DISCO VOADOR: chega à pergunta 5", "quiz"),
    ]),
]


class Missions(object):
    def __init__(self, app):
        self.app = app
        self.done_set = set(app.cfg.setdefault("missions", []))
        self.toast = ("", 0.0)

    def current(self):
        """(mission index, title, steps) of the first unfinished mission, or None when everything is done"""
        for i, (title, steps) in enumerate(MISSIONS):
            if not all(s[0] in self.done_set for s in steps):
                return i, title, steps
        return None

    def next_step(self):
        cur = self.current()
        if not cur:
            return None
        for s in cur[2]:
            if s[0] not in self.done_set:
                return s
        return None

    def done(self, sid):
        if sid in self.done_set:
            return
        known = [s[0] for _, steps in MISSIONS for s in steps]
        if sid not in known:
            return
        self.done_set.add(sid)
        self.app.cfg["missions"] = sorted(self.done_set)
        self.app.save_cfg()
        label = [s[1] for _, steps in MISSIONS for s in steps if s[0] == sid][0]
        cur = self.current()
        finished = [t for t, steps in MISSIONS if all(s[0] in self.done_set for s in steps) and sid in [x[0] for x in steps]]
        self.toast = (("★ MISSÃO CUMPRIDA: " + finished[0]) if finished else ("✓ " + label), time.time())
        if cur is None:
            self.toast = ("★ TODAS AS MISSÕES CUMPRIDAS!", time.time())

    def reset(self):
        self.done_set = set()
        self.app.cfg["missions"] = []
