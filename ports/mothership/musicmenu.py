# Hold START (in any music app, the bridge or the Hangar): the music menu.
# Same fixed keys everywhere:  A play/pause all   X stop all   ◀▶ tempo   ▲▼ volume   Y record   L1 metronome   B close
import time

import ui
from engine import C, W, H

ROWS = [("A", "Tocar / pausa (tudo)"), ("X", "Parar tudo"), ("esq/dir", "Tempo (BPM)"), ("cima/baixo", "Volume"),
        ("Y", "Gravar sessão"), ("L1", "Metrónomo"), ("B", "Fechar")]


class MusicMenu(object):
    def __init__(self, app):
        self.app = app
        self.active = False
        self.t0 = 0.0
        self.msg = ("", 0.0)

    def open(self):
        self.active = True
        self.t0 = time.time()
        self.app.ui_move()

    def close(self):
        self.active = False

    def say(self, s):
        self.msg = (s, time.time())

    def on(self, kind, b):
        app = self.app
        if kind == "release":
            return
        if kind == "press" and b in ("b", "start", "select"):
            self.close()
        elif kind == "press" and b == "a":
            self.say(app.music_toggle())
        elif kind == "press" and b == "x":
            app.music_stop()
            self.say("Tudo parado")
        elif b in ("left", "right"):
            app.set_bpm(round(app.mixer.bpm) + (1 if b == "right" else -1))
        elif b in ("up", "down"):
            app.set_volume(app.cfg["volume"] + (5 if b == "up" else -5))
            app.save_cfg()
        elif kind == "press" and b == "y":
            self.say(app.record_toggle())
        elif kind == "press" and b == "l1":
            app.mixer.metro = not app.mixer.metro
            self.say("Metrónomo " + ("ligado" if app.mixer.metro else "desligado"))

    def sources(self):
        """what is making sound right now, in plain words"""
        app = self.app
        st = app.now_playing()
        out = []
        fg = app.sections["forge"]
        out.append(("BEAT FORGE", ("a tocar o padrão %s" % "ABCDEFGH"[fg.cur]) if st["forge"] else "parado", st["forge"]))
        n = len(st["loops"])
        out.append(("LOOP REACTOR", ("%d loop%s a tocar" % (n, "s" if n != 1 else "")) if n else "sem loops", n > 0))
        dk = app.sections["decks"]
        da, db = st["decks"]
        if da or db:
            names = [d.title for d, on in ((dk.a, da), (dk.b, db)) if on]
            out.append(("TWIN DECKS", ", ".join(names), True))
        if st["warp"]:
            w = app.sections["warp"]
            out.append(("WARP FLOOR", w.now_title() if hasattr(w, "now_title") else "a tocar", True))
        if st["mic"]:
            out.append(("VOX NEBULA", "micro ligado", True))
        if st["rec"]:
            out.append(("GRAVAÇÃO", app.rec.label(), True))
        return out

    def draw(self, g, t):
        app = self.app
        g.rect(0, 0, W, H, C["void"], 170)
        x, y, w, h = 70, 54, 500, 372
        ui.panel(g, x, y, w, h, C["orange"], "MÚSICA")
        st = app.now_playing()
        g.text(ui.TITLE, ("▶ A TOCAR" if st["playing"] else "■ PARADO"), x + 22, y + 18,
               C["green"] if st["playing"] else C["muted"])
        g.text(ui.TITLE, "%d BPM" % round(app.mixer.bpm), x + w - 22, y + 18, C["text"], 255, "right")
        g.text(ui.SMALL, "%d/4   ·   volume %d%%   ·   metrónomo %s" % (
            app.mixer.beats_per_bar, app.cfg["volume"], "ON" if app.mixer.metro else "OFF"), x + 22, y + 58, C["muted"])
        yy = y + 86
        for name, what, on in self.sources()[:5]:
            g.rect(x + 22, yy + 7, 6, 6, C["green"] if on else C["dim"])
            g.text(ui.SMALL, name, x + 36, yy, C["text"] if on else C["muted"])
            g.text(ui.SMALL, ui.fit(g, ui.SMALL, what, 250), x + 190, yy, C["soft"] if on else C["dim"])
            yy += 20
        yy = y + 196
        g.rect(x + 20, yy - 8, w - 40, 1, C["hullhi"])
        for i, (k, label) in enumerate(ROWS):
            cx = x + 26 + (i % 2) * 238
            cy = yy + (i // 2) * 30
            xe = ui.keys(g, k, cx, cy)
            g.text(ui.SMALL, label, xe + 6, cy - 1, C["text"])
        s, t0 = self.msg
        if s and time.time() - t0 < 1.8:
            ui.toast(g, s, C["green"], y + h - 4)
