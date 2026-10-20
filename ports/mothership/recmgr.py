# GRAVACOES - file manager for everything the ship records/exports (inside HANGAR): listen, see size, delete.
import glob
import os
import time
import wave

import engine
from engine import C, W, StreamVoice

APP = engine.APP


def kind_of(path):
    b = os.path.basename(path)
    d = os.path.basename(os.path.dirname(path))
    if d == "chop":
        return "FATIA"
    if d == "forge":
        return "LOOP FORGE"
    if b.startswith("rec_"):
        return "ABDUCTOR"
    if b.startswith("session_") and b.endswith("_forge.wav"):
        return "FORGE SONG"
    if b.startswith("session_"):
        return "SESSAO"
    return "OUTRO"


def scan():
    out = []
    for pattern in ("recordings/*.wav", "chop/*.wav", "forge/*.wav"):
        for p in glob.glob(os.path.join(APP, pattern)):
            try:
                size = os.path.getsize(p)
                wf = wave.open(p, "rb")
                try:
                    secs = wf.getnframes() / float(wf.getframerate())
                finally:
                    wf.close()
            except Exception:
                size, secs = 0, 0.0
            title = os.path.splitext(os.path.basename(p))[0]
            meta = p[:-4] + ".json"
            if os.path.exists(meta) and kind_of(p) in ("SESSAO", "FORGE SONG"):
                try:
                    t = engine.read_json(meta).get("title", title)
                    title = t if isinstance(t, str) else title
                except Exception:
                    pass
            out.append({"path": p, "title": title, "kind": kind_of(p), "size": size, "secs": secs,
                        "mtime": os.path.getmtime(p)})
    out.sort(key=lambda r: -r["mtime"])
    return out


def free_space():
    try:
        st = os.statvfs(APP)
        return st.f_bavail * st.f_frsize
    except Exception:
        return None


class RecManager(object):
    def __init__(self, app):
        self.app = app
        self.items = []
        self.sel = 0
        self.top = 0
        self.voice = None
        self.playing = None
        self.confirm = (None, 0.0)
        self.msg = ("", 0.0)
        self.by_size = False

    def open(self):
        self.items = scan()
        self.sel = min(self.sel, max(0, len(self.items) - 1))

    def close(self):
        self.stop()

    def say(self, s):
        self.msg = (s, time.time())

    def stop(self):
        if self.voice:
            self.voice.fade(0.0, 0.1)
        self.voice = None
        self.playing = None

    def play(self, it):
        self.stop()
        try:
            v = StreamVoice(it["path"], "recmgr")
            m = self.app.mixer
            with m.lock:
                m.streams.append(v)
            self.voice, self.playing = v, it["path"]
        except Exception:
            self.say("Não consegui tocar este ficheiro.")

    def remove(self, f):
        try:
            os.remove(f)
        except OSError:
            # Windows cannot delete a file that is still open (the stream fading out after stop() still reads it):
            # close that stream and try again. On the console the first os.remove already works.
            m = self.app.mixer
            with m.lock:
                mine = [s for s in m.streams if getattr(s, "path", None) == f]
                for s in mine:
                    s.done = True
                    s.close()
                    m.streams.remove(s)
            if not mine:
                raise
            os.remove(f)

    def delete(self, it):
        p = it["path"]
        if self.playing == p:
            self.stop()
        removed = 0
        for f in (p, p[:-4] + ".json", p + ".chart.json"):
            if os.path.exists(f):
                try:
                    self.remove(f)
                    removed += 1
                except Exception:
                    self.say("Não consegui apagar.")
                    return
        bank = self.app.bank
        base = os.path.basename(p)
        if it["kind"] == "FATIA" and base.startswith("slice_"):
            try:
                bank.set_chop_pad(int(base[6:-4]) - 1)
            except Exception:
                pass
        elif it["kind"] == "LOOP FORGE" and base.startswith("forge_"):
            try:
                k = "ABCDEFGH".index(base[6])
                bank.banks[bank.forge_bank]["pads"][k] = bank.forge_pad(k)
                bank.load_pad(bank.forge_bank, k)
            except Exception:
                pass
        self.say("Apagado: %s" % it["title"][:30])
        self.items = scan()
        if self.by_size:
            self.items.sort(key=lambda r: -r["size"])
        self.sel = min(self.sel, max(0, len(self.items) - 1))

    def on(self, kind, b):
        """returns False when the manager should close"""
        if kind not in ("press", "repeat"):
            return True
        if b == "b" and kind == "press":
            self.close()
            return False
        if not self.items:
            return True
        if b in ("up", "down"):
            self.sel = (self.sel + (1 if b == "down" else -1)) % len(self.items)
        elif b in ("left", "right"):
            self.sel = max(0, min(len(self.items) - 1, self.sel + (10 if b == "right" else -10)))
        elif kind != "press":
            return True
        elif b == "a":
            it = self.items[self.sel]
            if self.playing == it["path"]:
                self.stop()
            else:
                self.play(it)
        elif b == "y":
            it = self.items[self.sel]
            if self.confirm[0] == it["path"] and time.time() - self.confirm[1] < 2.5:
                self.confirm = (None, 0.0)
                self.delete(it)
            else:
                self.confirm = (it["path"], time.time())
                self.say("Carrega Y outra vez para apagar %s" % it["title"][:24])
        elif b == "x":
            self.by_size = not self.by_size
            self.items.sort(key=(lambda r: -r["size"]) if self.by_size else (lambda r: -r["mtime"]))
        return True

    def draw(self, g, t):
        app = self.app
        total = sum(r["size"] for r in self.items)
        free = free_space()
        g.text("p8", "GRAVAÇÕES", 24, 60, app.accent)
        g.text("v20", "%d ficheiros - %.1f MB%s" % (len(self.items), total / 1e6,
                                                     ("  ·  livre no cartão: %.1f GB" % (free / 1e9)) if free else ""),
               W - 24, 56, C["soft"], 255, "right")
        if not self.items:
            g.text("v20", "Ainda não há gravações. Grava uma sessão: segura START e carrega Y.", W // 2, 200, C["muted"], 255, "center")
            return
        rows = 13
        if self.sel < self.top:
            self.top = self.sel
        elif self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        for r, i in enumerate(range(self.top, min(len(self.items), self.top + rows))):
            it = self.items[i]
            y = 80 + r * 26
            sel = i == self.sel
            if sel:
                g.rect(16, y - 2, W - 32, 24, C["hull"])
                g.frame(16, y - 2, W - 32, 24, app.accent, 2)
            if self.playing == it["path"] and int(t * 3) % 2 == 0:
                g.tri(22, y + 3, 6, "right", C["green"])
            g.text("v20", it["title"][:30], 40, y, C["text"] if sel else C["soft"])
            g.text("v20", it["kind"], 330, y, C["cyan"] if sel else C["dim"])
            g.text("v20", "%d:%02d" % (it["secs"] // 60, it["secs"] % 60), 470, y, C["muted"])
            g.text("v20", "%.1f MB" % (it["size"] / 1e6), W - 24, y, C["muted"], 255, "right")
        s, t0 = self.msg
        if s and time.time() - t0 < 2.5:
            w = g.tw("v20", s) + 30
            g.rect(W // 2 - w // 2, 210, w, 34, C["panel"], 245)
            g.frame(W // 2 - w // 2, 210, w, 34, (255, 80, 90) if "apagar" in s else app.accent, 2)
            g.text("v20", s, W // 2, 216, C["text"], 255, "center")

