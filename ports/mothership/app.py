# Orimbux Mothership - sections (Intro, Bridge, Loop Reactor, Xeno Synth, Pulsar, Abductor, Warp Floor, Hangar)
import array
import json
import math
import ctypes
import os
import random
import shutil
import subprocess
import threading
import time
import wave

import sdl2

import engine
import pet
import trailer
import credits
import voidrunner
import beatduel
import forge
import decks
import quiz
import chop
import vox
import help as helpmod
import ui
import musicmenu
import missions
import recmgr
from engine import C, W, H, SR, audioop, draw_ship, load_wav, to_std, fit, same_len, Voice, SynthVoice, StreamVoice

APP = engine.APP
CFG_PATH = os.path.join(APP, "config.json")
REC_DIR = os.path.join(APP, "recordings")
MUSIC_DIR = os.path.join(APP, "music")
DEFAULT_CFG = {"scanlines": True, "anim": True, "volume": 80, "quantize": "bar", "swap_ab": False,
               "bpm": 174, "custom_pads": {}, "joy_map": {}, "pet_speed": 1}

PAD_ORDER = ["up", "left", "right", "down", "x", "y", "a", "b"]
TABS = [("PULSAR", "pulsar"), ("FORGE", "forge"), ("ABDUCT", "abductor"), ("REACTOR", "reactor"), ("XENO", "xeno"),
        ("WARP", "warp")]
CYCLE = list(ui.MUSIC_KEYS)        # START (tap) follows the music workflow
MUSIC_HUB = CYCLE + ["bridge", "hangar"]   # where holding START opens the music menu
QUIET = ("pet", "voidrunner", "beatduel", "trailer", "credits", "quiz")      # sections with their own sound: drum machine stops
BANK_COL = {"orange": C["orange"], "violet": C["violet"], "cyan": C["cyan"], "green": C["green"]}


def log(msg):
    try:
        import io
        with io.open(os.path.join(APP, "log.txt"), "a", encoding="utf-8", errors="replace") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    saved = engine.load_save(CFG_PATH)
    if saved:
        cfg.update(saved)
        clean_cfg(cfg)
        engine.check_save(CFG_PATH, saved, cfg)
    return cfg


def clean_cfg(cfg):
    """settings that would crash the app (a damaged or hand-edited config.json) go back to their defaults"""
    for k in ("scanlines", "anim", "swap_ab"):
        if not isinstance(cfg[k], bool):
            cfg[k] = DEFAULT_CFG[k]
    for k, lo, hi in (("volume", 0, 100), ("bpm", 60, 220), ("pet_speed", None, None)):
        cfg[k] = engine.num(cfg[k], DEFAULT_CFG[k], lo, hi)
    if not isinstance(cfg["quantize"], str):
        cfg["quantize"] = DEFAULT_CFG["quantize"]
    pads, joy = cfg["custom_pads"], cfg["joy_map"]
    cfg["custom_pads"] = dict((k, v) for k, v in pads.items() if isinstance(v, str)) if isinstance(pads, dict) else {}
    cfg["joy_map"] = dict((k, v) for k, v in joy.items() if isinstance(v, int) and not isinstance(v, bool)) \
        if isinstance(joy, dict) else {}
    for k in ("seen", "missions"):
        if k in cfg:
            cfg[k] = [x for x in cfg[k] if isinstance(x, str)] if isinstance(cfg[k], list) else []
    if "bd_offset" in cfg:
        cfg["bd_offset"] = engine.num(cfg["bd_offset"], 0.0)


# ====================================================================== shared UI pieces
def header(g, app, title, active):
    ui.header(g, app, TITLE_OF.get(active, title), active)


TITLE_OF = dict((k, n) for k, n, _ in ui.MUSIC_FLOW)


def _old_header(g, app, title, active):
    g.rect(0, 0, W, 48, C["deck"])
    g.rect(0, 48, W, 3, C["hulllo"])
    g.text("p16", "ORIMBUX", 14, 16, C["violet"])
    g.text("p16", "ORIMBUX", 12, 14, C["cyan"])
    g.text("p8", "// " + title, 128, 22, app.accent)
    if app.rec.active():
        if int(time.time() * 2) % 2 == 0:
            g.rect(128, 34, 8, 8, (255, 50, 60))
        g.text("p8", app.rec.label(), 142, 34, (255, 90, 100))
    vx = app.sections.get("vox") if hasattr(app, "sections") else None
    if vx is not None and vx.live:
        g.text("p8", "MIC " + vx.fx, 250, 34, C["green"])
    x = W - 12
    for label, key in reversed(TABS):
        w = g.tw("p8", label) + 10
        x -= w
        if key == active:
            g.rect(x, 16, w, 18, app.accent)
            g.text("p8", label, x + 5, 21, C["void"])
        else:
            g.rect(x, 16, w, 18, C["hull"])
            g.text("p8", label, x + 5, 21, C["muted"])
        x -= 4


def footer(g, items, y=H - 44, h=44):
    ui.footer(g, [(it[0], it[1]) for it in items])


def _old_footer(g, items, y=H - 44, h=44):
    g.rect(0, y, W, h, C["deck"])
    g.rect(0, y, W, 3, C["hulllo"])
    if not items:
        return
    total = sum(g.tw("v20", k + " " + v) for k, v, _ in items)
    gap = (W - 32 - total) / max(1, len(items) - 1) if len(items) > 1 else 0
    x = 16
    for k, v, col in items:
        x2 = g.text("v20", k, x, y + 14, col)
        x2 = g.text("v20", " " + v, x2, y + 14, C["muted"])
        x = x2 + gap


def pad_box(g, app, x, y, w, h, label, glyph, state, t, beat_phase, bank_col):
    """state: idle / play / queue / stop / shot"""
    if state == "play" or state == "shot":
        pulse = (1.0 - beat_phase) if app.cfg["anim"] else 0.5
        g.glow(x, y, w, h, app.accent, 0.4 + 0.6 * pulse)
        g.bevel(x, y, w, h, app.accent, C["orangehi"], C["orangelo"])
        fg = C["void"]
    elif state == "queue":
        on = (int(t * 6) % 2 == 0) or not app.cfg["anim"]
        g.rect(x, y, w, h, C["hull"])
        g.frame(x, y, w, h, C["violet"] if on else C["dim"], 3)
        fg = C["violet"]
    elif state == "stop":
        g.bevel(x, y, w, h, app.accent, C["orangehi"], C["orangelo"])
        on = (int(t * 6) % 2 == 0)
        g.frame(x + 3, y + 3, w - 6, h - 6, C["void"] if on else app.accent, 2)
        fg = C["void"]
    else:
        g.bevel(x, y, w, h, C["hull"], C["hullhi"], C["hulllo"])
        fg = C["soft"]
    # glyph (arrow or letter) then label
    cx = x + w // 2
    if glyph in ("up", "down", "left", "right"):
        g.tri(cx - 5, y + 10, 5, glyph, fg)
    else:
        g.text("p8", glyph.upper(), cx, y + 12, fg, align="center")
    lab = label if g.tw("p8", label) <= w - 6 else label[:max(1, (w - 6) // 8)]
    g.text("p8", lab, cx, y + h - 22, fg, align="center")
    g.rect(x + 6, y + h - 9, w - 12, 3, bank_col, 160)


def cross(g, x, y, cell, gap, items):
    """items: dict pos->callable(x,y,w,h); positions up/left/right/down in a plus shape"""
    pos = {"up": (1, 0), "left": (0, 1), "right": (2, 1), "down": (1, 2)}
    for k, fn in items.items():
        cx, cy = pos[k]
        fn(x + cx * (cell + gap), y + cy * (cell + gap), cell, cell)


def stars_init(n=70):
    return [[random.uniform(0, W), random.uniform(0, H), random.uniform(10, 60),
             random.choice([C["text"], C["cyan"], C["violet"], C["text"], C["orange"]])] for _ in range(n)]


def stars_draw(g, stars, dt, vertical=True, alpha=200, move=True):
    groups = {}
    for s in stars:
        if move:
            if vertical:
                s[1] += s[2] * dt
                if s[1] > H:
                    s[1] -= H
                    s[0] = random.uniform(0, W)
            else:
                s[0] -= s[2] * dt
                if s[0] < 0:
                    s[0] += W
                    s[1] = random.uniform(0, H)
        size = 2 if s[2] > 45 else 1
        groups.setdefault(s[3], []).append((s[0], s[1], size, size))
    for col, lst in groups.items():
        g.rects(lst, col, alpha)


# ====================================================================== sample bank (Loop Reactor data)
class Bank(object):
    def __init__(self, app):
        self.app = app
        self.banks = json.load(open(os.path.join(APP, "banks.json")))["banks"]
        self.forge_bank = len(self.banks)
        self.banks.append({"name": "FORGE", "color": "orange", "pads": [self.forge_pad(p) for p in range(8)]})
        self.chop_bank = len(self.banks)
        self.banks.append({"name": "CHOP", "color": "violet", "pads": [self.chop_pad(p) for p in range(8)]})
        self.raw = {}      # (b,p) -> (data, dark)
        self.fitted = {}   # (b,p,bpm) -> (data, dark)
        self.progress = 0
        self.total = sum(len(b["pads"]) for b in self.banks)
        self.ready = False
        self.errors = []

    def pad(self, b, p):
        return self.banks[b]["pads"][p]

    @staticmethod
    def forge_pad(p):
        path = os.path.join(forge.EXPORT_DIR, "forge_%s.wav" % forge.PAT_NAMES[p])
        if os.path.exists(path):
            beats = 4
            try:
                beats = engine.num(engine.read_json(path[:-4] + ".json").get("beats", 4), 4, 0.25)
            except Exception:
                pass
            return {"label": "FORGE " + forge.PAT_NAMES[p], "file": path, "mode": "loop", "beats": beats,
                    "gain": 2.0}
        return {"label": "VAZIO", "file": path, "mode": "shot", "optional": True}

    @staticmethod
    def chop_pad(p):
        path = os.path.join(chop.EXPORT_DIR, "slice_%d.wav" % (p + 1))
        if os.path.exists(path):
            return {"label": "FATIA %d" % (p + 1), "file": path, "mode": "shot"}
        return {"label": "VAZIO", "file": path, "mode": "shot", "optional": True}

    def set_chop_pad(self, p):
        self.banks[self.chop_bank]["pads"][p] = self.chop_pad(p)
        self.load_pad(self.chop_bank, p)

    def set_forge_pad(self, p, path, beats=4):
        try:
            engine.write_json(path[:-4] + ".json", {"beats": beats})
        except Exception:
            pass
        self.banks[self.forge_bank]["pads"][p] = self.forge_pad(p)
        self.load_pad(self.forge_bank, p)

    def path_for(self, pad):
        f = pad["file"]
        if os.path.isabs(f) or f.endswith(".wav"):
            return f if os.path.isabs(f) else os.path.join(APP, f)
        return os.path.join(engine.ASSETS, "samples", f + ".wav")

    def load_all(self):
        custom = self.app.cfg.get("custom_pads", {})
        for k, path in custom.items():
            try:
                b, p = [int(v) for v in k.split(":")]
                pad = self.banks[b]["pads"][p]
                pad["file"] = path
                pad["mode"] = "shot"
                pad["label"] = "MY REC"
            except Exception:
                pass
        for bi, bank in enumerate(self.banks):
            for pi, pad in enumerate(bank["pads"]):
                self.load_pad(bi, pi)
                self.progress += 1
        self.ready = True

    def load_pad(self, bi, pi):
        pad = self.pad(bi, pi)
        path = self.path_for(pad)
        if pad.get("optional") and not os.path.exists(path):
            self.raw[(bi, pi)] = (b"\0" * 400, None)
            return
        try:
            data = load_wav(path)
            dpath = path[:-4] + ".dark.wav"
            dark = same_len(data, load_wav(dpath)) if os.path.exists(dpath) else None
            self.raw[(bi, pi)] = (data, dark)
            for k in list(self.fitted):
                if k[0] == bi and k[1] == pi:
                    del self.fitted[k]
        except Exception as e:
            self.errors.append("%s: %s" % (pad.get("label"), e))
            log("load %s %r" % (path, e))
            self.raw[(bi, pi)] = (b"\0" * 4000, None)

    def get(self, bi, pi, bpm):
        pad = self.pad(bi, pi)
        data, dark = self.raw.get((bi, pi), (b"\0" * 4000, None))
        if pad.get("mode") != "loop":
            return data, dark
        key = (bi, pi, round(bpm, 2))
        if key not in self.fitted:
            frames = int(round(pad.get("beats", 4) * SR * 60.0 / bpm))
            fd = fit(data, frames)
            fk = fit(dark, frames) if dark is not None else None
            self.fitted[key] = (fd, fk)
            if len(self.fitted) > 24:
                for k in list(self.fitted)[:8]:
                    if k != key:
                        del self.fitted[k]
        return self.fitted[key]


# ====================================================================== session recorder (for BEAT DUEL)
LANE_OF = {"left": 0, "down": 1, "up": 2, "right": 3, "y": 0, "b": 1, "x": 2, "a": 3}
REC_MAX = 180.0


class SessionRec(object):
    """records the mixer output to a wav + the exact moment of every pad/note (-> a BEAT DUEL chart)"""

    def __init__(self, app):
        self.app = app
        self.wf = None
        self.events = []
        self.clock0 = 0
        self.frames = 0
        self.path = None
        self.src = ""

    def active(self):
        return self.wf is not None

    def toggle(self, src, max_s=REC_MAX):
        if self.active():
            self.stop()
        else:
            self.start(src, max_s)

    def start(self, src, max_s=REC_MAX):
        self.max_s = max_s
        if not os.path.isdir(REC_DIR):
            os.makedirs(REC_DIR)
        self.path = os.path.join(REC_DIR, time.strftime("session_%Y%m%d_%H%M%S"))
        self.wf = wave.open(self.path + ".wav", "wb")
        self.wf.setnchannels(2)
        self.wf.setsampwidth(2)
        self.wf.setframerate(SR)
        self.events, self.frames, self.src = [], 0, src
        self.loop_ev, self.open_ev = [], {}
        m = self.app.mixer
        with m.lock:
            self.clock0 = m.clock
            m.rec = []
            self.next_beat = math.ceil(m.beat_at(m.clock))
        self.app.ui_ok()

    def event(self, clock, button):
        if self.wf is not None and button in LANE_OF:
            self.events.append([round(max(0, clock - self.clock0) / float(SR), 3), LANE_OF[button]])
            self.open_ev[LANE_OF[button]] = len(self.events) - 1

    def event_off(self, clock, button):
        """a note released: if it was held long enough it becomes a long note in Beat Duel"""
        if self.wf is None or button not in LANE_OF:
            return
        i = self.open_ev.pop(LANE_OF[button], None)
        if i is not None and i < len(self.events) and len(self.events[i]) == 2:
            dur = max(0, clock - self.clock0) / float(SR) - self.events[i][0]
            if dur >= 0.35:
                self.events[i].append(round(dur, 3))

    def loop_beats(self):
        """Loop Reactor loops that keep playing produce notes on their beats (not only when they start):
        1 loop = every beat, 2+ loops = the two newest take turns; HARD gets every loop on every beat"""
        m = self.app.mixer
        now = m.beat_at(m.clock)
        guard = 0
        while self.next_beat <= now and guard < 16:
            guard += 1
            f = m.frame_of_beat(self.next_beat)
            loops = [v for v in m.voices if v.group == "reactor" and v.loop and not v.done and v.start <= f and
                     (v.stop is None or v.stop > f)]
            loops.sort(key=lambda v: v.start)
            loops = loops[-2:]
            t = round(max(0, f - self.clock0) / float(SR), 3)
            for k, v in enumerate(loops):
                try:
                    lane = LANE_OF[PAD_ORDER[int(v.key.split(":")[2])]]
                except Exception:
                    continue
                normal = len(loops) == 1 or int(self.next_beat) % 2 == k
                self.loop_ev.append([t, lane, normal])
            self.next_beat += 1

    def flush(self):
        if self.wf is None:
            return
        m = self.app.mixer
        with m.lock:
            chunks, m.rec = m.rec or [], []
        if chunks:
            data = b"".join(chunks)
            self.wf.writeframes(data)
            self.frames += len(data) // 4
        self.loop_beats()
        if self.frames / float(SR) >= getattr(self, "max_s", REC_MAX):
            self.stop()

    def stop(self):
        if self.wf is None:
            return
        self.flush()
        m = self.app.mixer
        with m.lock:
            m.rec = None
        self.wf.close()
        self.wf = None
        def merge(extra):
            seen, out = set(), []
            for n in sorted(self.events + extra):
                key = (round(n[0], 2), n[1])
                if key not in seen:
                    seen.add(key)
                    out.append(n)
            return out
        dur = self.frames / float(SR)
        ev = [n for n in merge([[t, l] for t, l, nm in self.loop_ev if nm]) if n[0] < dur]
        hard = [n for n in merge([[t, l] for t, l, _ in self.loop_ev]) if n[0] < dur]
        easy, last = [], -9
        for n in ev:
            if n[0] - last > 0.4:
                easy.append(n)
                last = n[0]
        meta = {"id": os.path.basename(self.path), "title": time.strftime("SESSAO %d/%m %H:%M") + " " + self.src,
                "artist": "TU", "bpm": round(self.app.mixer.bpm, 1), "duration": round(self.frames / float(SR), 2),
                "file": os.path.basename(self.path) + ".wav",
                "charts": {"easy": easy, "normal": ev, "hard": hard}}
        try:
            engine.write_json(self.path + ".json", meta)
            self.app.mission("session_saved")
        except Exception as e:
            log("session json %r" % (e,))
        self.app.ui_ok()

    def label(self):
        return "REC %d:%02d" % (self.frames // SR // 60, self.frames // SR % 60)


# ====================================================================== sections
class Section(object):
    name = "?"

    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def leave(self):
        pass

    def on(self, kind, b):
        pass

    def update(self, dt):
        pass

    def draw(self, g, t, dt):
        pass


# ---------------------------------------------------------------------- INTRO
MOOD_DIR = os.path.join(engine.ASSETS, "moods")


def load_moods():
    try:
        d = json.load(open(os.path.join(MOOD_DIR, "moods.json")))
        return [(k, d["moods"][k]["label"], [os.path.join(MOOD_DIR, f) for f in d["moods"][k]["files"]])
                for k in d["order"]]
    except Exception as e:
        log("moods: %r" % e)
        return []


class Intro(Section):
    """the boarding screen: one of 5 synth moods plays (endlessly varied) until START"""

    def __init__(self, app):
        Section.__init__(self, app)
        self.stars = stars_init(80)
        self.t0 = 0
        self.wait = False
        self.moods = load_moods()
        self.mood = -1
        self.voice = None
        self.logo = None
        self.mood_t = 0.0

    def enter(self):
        self.t0 = time.time()
        self.logo = trailer.make_logo(self.app)
        if self.moods:
            last = self.app.cfg.get("last_mood")
            pool = [i for i, m in enumerate(self.moods) if m[0] != last] or list(range(len(self.moods)))
            self.play_mood(random.choice(pool))
        elif self.app.snd.get("jingle"):
            self.app.mixer.shot("jingle", self.app.snd["jingle"], group="ui", gain=0.9)

    def play_mood(self, i):
        m = self.app.mixer
        old = self.voice
        try:
            v = engine.PlaylistVoice(self.moods[i][2], "intro")
        except Exception as e:
            log("mood %r" % e)
            return
        v.g = 0.0
        v.fade(0.85, 1.6)
        with m.lock:
            m.streams.append(v)
        if old:
            old.fade(0.0, 1.0)
        self.voice, self.mood, self.mood_t = v, i, time.time()
        self.app.cfg["last_mood"] = self.moods[i][0]

    def leave(self):
        if self.voice:
            self.voice.fade(0.0, 1.4)
            self.voice = None
        if self.logo:
            sdl2.SDL_DestroyTexture(self.logo[0])
            sdl2.SDL_DestroyTexture(self.logo[1])
            self.logo = None

    def on(self, kind, b):
        if kind == "press" and b in ("start", "a"):
            self.wait = True
        elif kind == "press" and b in ("left", "right") and self.moods:
            self.play_mood((self.mood + (1 if b == "right" else -1)) % len(self.moods))
            self.app.ui_move()

    def update(self, dt):
        if self.wait and self.app.bank.ready:
            self.app.mixer.kill_key("jingle")
            self.app.ui_ok()
            self.app.go("bridge")

    def draw(self, g, t, dt):
        app = self.app
        el = time.time() - self.t0
        g.clear(C["void"])
        stars_draw(g, self.stars, dt, True, 220, app.cfg["anim"])
        bob = math.sin(t * 2.6) * 8 if app.cfg["anim"] else 0
        beam = 0.45 + 0.35 * math.sin(t * 5) if app.cfg["anim"] else 0.6
        draw_ship(g, 160, 24 + bob, 8, t, beam, app.accent)
        lx = W // 2
        glitch = 0.6 if (app.cfg["anim"] and (t % 4.0) > 3.72) else 0.0
        rise = min(1.0, el / 0.9)
        ly = 262 + int((1 - rise) * 24)
        trailer.draw_logo(g, self.logo, lx, ly, t, int(255 * rise), glitch,
                          shine=((t % 5.0) / 0.8) if app.cfg["anim"] else None)
        r2 = max(0.0, min(1.0, (el - 0.5) / 0.9))
        g.text("kb24", "M O T H E R S H I P", lx, 350 + int((1 - r2) * 20), app.accent, int(255 * r2), "center")
        if app.bank.ready:
            if int(t * 1.7) % 2 == 0 or not app.cfg["anim"]:
                g.text(ui.BODY, "carrega em START para embarcar", lx, 394, C["text"], 255, "center")
        else:
            p = app.bank.progress / float(app.bank.total or 1)
            g.text(ui.SMALL, "a carregar sons %d/%d" % (app.bank.progress, app.bank.total), lx, 392, C["muted"], 255,
                   "center")
            g.rect(lx - 120, 414, 240, 6, C["deck"])
            g.rect(lx - 120, 414, int(240 * p), 6, C["cyan"])
        if self.mood >= 0:                          # the mood that is playing; left/right changes it
            label = "♪ " + self.moods[self.mood][1]
            a = 255 if time.time() - self.mood_t < 3 else 170
            x = ui.keys(g, "esq/dir", 14, 446)
            g.text(ui.SMALL, label, x + 8, 446, C["soft"], a)
        g.text(ui.SMALL, "© 2026 ORIMBUX", W - 14, 446, C["dim"], 255, "right")


# ---------------------------------------------------------------------- BRIDGE
SOON = None
CATS = [  # (name, section, colour, tag, what it is - in plain words)
    ("MÚSICA", [
        ("PULSAR", "pulsar", C["cyan"], "TEMPO", "Começa aqui: escolhe a velocidade (BPM). Toda a nave toca neste tempo."),
        ("BEAT FORGE", "forge", C["orange"], "RITMO", "Cria a bateria: liga passos numa grelha ou escolhe um estilo pronto."),
        ("ABDUCTOR", "abductor", (255, 110, 170), "SONS TEUS", "Grava a tua voz (micro USB) ou corta uma música em pedaços para tocar."),
        ("LOOP REACTOR", "reactor", C["orange"], "AO VIVO", "8 botões, 8 loops: toca-os ao vivo, sempre certinhos no tempo."),
        ("XENO SYNTH", "xeno", C["violet"], "MELODIA", "Um teclado alien: cada botão é uma nota que soa sempre bem."),
        ("VOX NEBULA", "vox", C["cyan"], "VOZ", "Canta com efeitos: robô, alien, monstro, eco... (micro USB)."),
        ("TWIN DECKS", "decks", C["violet"], "MISTURA", "Dois leitores de DJ: junta músicas e passa de uma para a outra."),
        ("WARP FLOOR", "warp", C["green"], "OUVIR", "Ouve as tuas músicas com luzes e passagem automática entre faixas."),
        ("CHIP TRACKER", SOON, C["cyan"], "EXTRA", "Para compor a sério: LittleGPTracker (grátis), instalado pelo PortMaster."),
    ]),
    ("JOGOS", [
        ("XENO PET", "pet", (255, 110, 170), "BICHO", "O teu bicho alien: dá-lhe comida, brinca com ele e vê-o crescer."),
        ("SOM DE OURO", "quiz", (255, 214, 80), "CONCURSO", "Concurso de música: 15 perguntas, da garagem ao Disco de Diamante."),
        ("VOID RUNNER", "voidrunner", C["violet"], "AÇÃO", "A tua música é o nível: foge do Grave e das hordas, que crescem com o ritmo."),
        ("BEAT DUEL", "beatduel", C["cyan"], "RITMO", "Jogo de ritmo a dois, com as músicas da nave ou as tuas."),
    ]),
    ("SISTEMA", [
        ("HANGAR", "hangar", C["muted"], "AJUSTES", "Volume, botões, gravações, tutoriais e teste de botões."),
        ("TRAILER", "trailer", C["orange"], "VÍDEO", "Vídeo de 1 min e 18 s: a nave e todas as apps, com música."),
        ("CRÉDITOS", "credits", C["violet"], "VÍDEO", "Quem construiu a nave, a rolar pelo espaço."),
    ]),
]
VISIBLE = 8
WELCOME = [("SELECT", "toque: volta a este menu"), ("SELECT", "segura: ajuda da app onde estás"),
           ("START", "toque: próxima app de música"), ("START", "segura: menu da música")]


class Bridge(Section):
    def __init__(self, app):
        Section.__init__(self, app)
        self.cat = 0
        self.sel = [0, 0, 0]
        self.top = [0, 0, 0]
        self.stars = stars_init(40)
        self.t_enter = 0
        self.flash = ""
        self.flash_t = 0
        self.jumped = None

    def enter(self):
        self.t_enter = time.time()
        # a new mission step: the cursor waits on the app that does it (only once per step,
        # so wandering around and coming back keeps your own choice)
        nxt = self.app.missions.next_step()
        if nxt and nxt[0] != self.jumped:
            self.jumped = nxt[0]
            if nxt[3]:
                self.jump_to(nxt[3])

    def items(self):
        return CATS[self.cat][1]

    def welcome(self):
        return not self.app.cfg.get("welcomed")

    def on(self, kind, b):
        if self.welcome():
            if kind == "press":
                self.app.cfg["welcomed"] = True
                self.app.save_cfg()
            return
        if kind in ("press", "repeat") and b in ("up", "down"):
            n = len(self.items())
            i = (self.sel[self.cat] + (1 if b == "down" else -1)) % n
            self.sel[self.cat] = i
            if i < self.top[self.cat]:
                self.top[self.cat] = i
            elif i >= self.top[self.cat] + VISIBLE:
                self.top[self.cat] = i - VISIBLE + 1
            self.app.ui_move()
        elif kind == "press" and b in ("l1", "r1", "left", "right"):
            self.cat = (self.cat + (1 if b in ("r1", "right") else -1)) % len(CATS)
            self.t_enter = time.time()
            self.app.ui_move()
        elif kind == "press" and b == "a":
            self.on_start()

    def on_start(self):
        nm, key, _, _, _ = self.items()[self.sel[self.cat]]
        if key is None:
            self.flash = "Abre o PortMaster na consola para instalar"
            self.flash_t = time.time()
            return
        self.app.ui_ok()
        self.app.go(key)

    def jump_to(self, key):
        for ci, (_, its) in enumerate(CATS):
            for i, it in enumerate(its):
                if it[1] == key:
                    self.cat, self.sel[ci] = ci, i
                    self.top[ci] = max(0, i - VISIBLE + 1) if i >= VISIBLE else 0

    def draw(self, g, t, dt):
        app = self.app
        g.clear(C["void"])
        stars_draw(g, self.stars, dt, False, 150, app.cfg["anim"])
        ui.header(g, app, "MOTHERSHIP", "bridge")
        # ---- left column: the pet + the mission
        app.sections["pet"].draw_widget(g, 12, 58, 232, 132, t)
        ui.outline(g, 12, 58, 232, 132, C["hullhi"], 2)
        self.draw_mission(g, t, 12, 210, 232, 222)
        # ---- right column: categories, list, description
        cname, its = CATS[self.cat]
        ccol = ui.CAT_COL[cname]
        x0, x1 = 258, W - 12
        tw = (x1 - x0) // len(CATS)
        for i, (cn, _) in enumerate(CATS):
            on = i == self.cat
            col = ui.CAT_COL[cn]
            ui.box(g, x0 + i * tw + 2, 56, tw - 4, 30, col if on else C["hull"])
            g.text("kb16" if on else ui.SMALL, cn, x0 + i * tw + tw // 2, 61, C["void"] if on else C["muted"], 255,
                   "center")
        ly, rh = 94, 36
        el = time.time() - self.t_enter
        top = self.top[self.cat]
        music = cname == "MÚSICA"
        for row, i in enumerate(range(top, min(len(its), top + VISIBLE))):
            nm, k, c, tag, _ = its[i]
            slide = max(0.0, min(1.0, (el - row * 0.04) / 0.25)) if app.cfg["anim"] else 1.0
            x = x0 + int((1 - slide) * 30)
            y = ly + row * rh
            w = x1 - x                                   # slides in from the left, never past the edge
            sel = i == self.sel[self.cat]
            locked = k is None
            if sel:
                ui.box(g, x, y, w, rh - 4, ccol)
                fg, sub = C["void"], C["void"]
            else:
                ui.box(g, x, y, w, rh - 4, C["off"] if locked else C["hull"])
                fg, sub = (C["dim"] if locked else C["text"]), C["muted"]
            if music:                                    # the workflow step number
                badge = "%d" % (i + 1) if not locked else "+"
                ui.box(g, x + 6, y + 5, 22, 22, C["void"] if sel else c)
                g.text(ui.SMALL, badge, x + 17, y + 6, ccol if sel else C["void"], 255, "center")
            else:
                g.rect(x + 12, y + 11, 10, 10, C["void"] if sel else c)
            ne = g.text(ui.HEAD, nm, x + 38, y + 1, fg)
            if ne + 10 <= x + w - 10 - g.tw(ui.SMALL, tag):     # the tag only where it does not touch the name
                g.text(ui.SMALL, tag, x + w - 10, y + 6, sub, 255, "right")
        nm, key, col, tag, desc = its[self.sel[self.cat]]
        py = ly + VISIBLE * rh + 2
        ui.panel(g, x0, py, x1 - x0, 432 - py, ccol)
        ui.para(g, ui.SMALL, desc, x0 + 12, ly + VISIBLE * rh + 6, x1 - x0 - 24, C["soft"], 18)
        if len(its) > VISIBLE:                           # more apps than fit: a thin scroll bar by the list
            lh = VISIBLE * rh - 4
            g.rect(W - 8, ly, 3, lh, C["hull"])
            th = max(12, lh * VISIBLE // len(its))
            g.rect(W - 8, ly + (lh - th) * top // max(1, len(its) - VISIBLE), 3, th, ccol)
        ui.footer(g, [("A", "entrar"), ("cima/baixo", "escolher"), ("esq/dir", "MÚSICA · JOGOS · SISTEMA")])
        if self.flash and time.time() - self.flash_t < 2.2:
            ui.toast(g, self.flash, C["orange"])
        if self.welcome():
            self.draw_welcome(g, t)

    def draw_mission(self, g, t, x, y, w, h):
        ms = self.app.missions
        cur = ms.current()
        ui.panel(g, x, y, w, h, C["green"], "MISSÃO %d" % (cur[0] + 1) if cur else "MISSÕES")
        if not cur:
            g.text(ui.HEAD, "★ TUDO FEITO!", x + w // 2, y + 70, (255, 214, 80), 255, "center")
            ui.para(g, ui.SMALL, "Já conheces a nave toda. Agora é só criar.", x + 14, y + 110, w - 28, C["soft"], 18,
                    "left")
            return
        _, title, steps = cur
        g.text(ui.SMALL, title, x + 12, y + 14, C["text"])
        nxt = ms.next_step()
        # the hint for the next step sits at the bottom; the steps share what is left (no overlap)
        hint = ui.wrap(g, ui.SMALL, nxt[2], w - 24) if nxt else []
        hy = y + h - 8 - 18 * len(hint)
        yy = y + 40
        rh = min(26, (hy - 4 - yy) // max(1, len(steps)))
        for sid, label, _, where in steps:
            done = sid in ms.done_set
            now = nxt is not None and sid == nxt[0]
            if now:
                ui.box(g, x + 6, yy - 2, w - 12, rh - 2, C["hull"])
            g.text(ui.SMALL, "✓" if done else ("▶" if now else "○"), x + 14, yy, C["green"] if done else (
                C["orange"] if now else C["dim"]))
            g.text(ui.SMALL, ui.fit(g, ui.SMALL, label, w - 44), x + 32, yy,
                   C["muted"] if done else (C["text"] if now else C["soft"]))
            yy += rh
        for i, l in enumerate(hint):
            g.text(ui.SMALL, l, x + 12, hy + i * 18, C["orange"])

    def draw_welcome(self, g, t):
        g.rect(0, 0, W, H, C["void"], 200)
        x, y, w, h = 60, 60, 520, 360
        ui.panel(g, x, y, w, h, C["cyan"], "BEM-VINDO À NAVE")
        g.text(ui.TITLE, "4 regras de ouro", x + w // 2, y + 22, C["text"], 255, "center")
        for i, (k, label) in enumerate(WELCOME):
            yy = y + 82 + i * 46
            ui.box(g, x + 24, yy - 6, w - 48, 38, C["hull"])
            xe = ui.keys(g, k, x + 40, yy + 4)
            g.text(ui.BODY, label, xe + 14, yy, C["text"])
        ui.para(g, ui.SMALL, "Começa pela MISSÃO 1 (à esquerda): ensina-te a fazer a tua primeira música, passo a "
                "passo.", x + 28, y + 274, w - 56, C["soft"], 18)
        if int(t * 2) % 2 == 0:
            g.text(ui.SMALL, "carrega num botão para começar", x + w // 2, y + h - 30, C["cyan"], 255, "center")


# ---------------------------------------------------------------------- LOOP REACTOR
class Reactor(Section):
    name = "LOOP REACTOR"

    def __init__(self, app):
        Section.__init__(self, app)
        self.bank = 0
        self.flash = {}

    def key(self, b, p):
        return "r:%d:%d" % (b, p)

    def quant(self):
        m = self.app.mixer
        return m.beats_per_bar if self.app.cfg["quantize"] == "bar" else 1

    def trigger(self, p):
        app, m = self.app, self.app.mixer
        pad = app.bank.pad(self.bank, p)
        k = self.key(self.bank, p)
        data, dark = app.bank.get(self.bank, p, m.bpm)
        self.flash[k] = time.time()
        app.mission("reactor_pad")
        if pad.get("mode") == "loop":
            with m.lock:
                v = m.find(k)
                if v is None:
                    st = m.next_boundary(self.quant())
                    m.voices.append(Voice(k, "reactor", data, dark, True, pad.get("gain", 1.0), st))
                    app.rec.event(st, PAD_ORDER[p])
                elif v.start > m.clock:
                    m.voices.remove(v)          # cancel a queued start
                elif v.stop is not None:
                    v.stop = None               # cancel a queued stop
                else:
                    v.stop = m.next_boundary(self.quant())
        else:
            m.shot(k, data, dark, group="reactor", gain=pad.get("gain", 1.0))
            app.rec.event(m.clock, PAD_ORDER[p])

    def refit(self):
        """BPM changed: re-stretch every playing loop, keeping its phase"""
        app, m = self.app, self.app.mixer
        for b in range(len(app.bank.banks)):
            for p in range(8):
                pad = app.bank.pad(b, p)
                if pad.get("mode") != "loop":
                    continue
                v = m.find(self.key(b, p))
                if v is None:
                    continue
                data, dark = app.bank.get(b, p, m.bpm)
                with m.lock:
                    old = max(1, len(v.data) // 4)
                    v.pos = int(v.pos * (len(data) // 4) / float(old))
                    v.data, v.dark = data, dark

    def state(self, b, p):
        m = self.app.mixer
        v = m.find(self.key(b, p))
        if v is None:
            return "idle"
        if v.start > m.clock:
            return "queue"
        if v.stop is not None:
            return "stop"
        return "play" if v.loop else "shot"

    def on(self, kind, b):
        app = self.app
        if kind != "press":
            if kind == "release" and b == "r2":
                app.mixer.warp = False
            return
        if b in PAD_ORDER:
            self.trigger(PAD_ORDER.index(b))
        elif b == "l1":
            self.bank = (self.bank - 1) % len(app.bank.banks)
            app.ui_move()
        elif b == "r1":
            self.bank = (self.bank + 1) % len(app.bank.banks)
            app.ui_move()
        elif b == "l2":
            app.mixer.kill_group("reactor")
        elif b == "r2":
            app.mixer.warp = True

    def combo(self, b):
        if b in ("up", "down"):
            self.app.set_bpm(self.app.mixer.bpm + (1 if b == "up" else -1))
            return True
        if b == "a":
            self.app.rec.toggle("REACTOR")
            return True
        return False

    def update(self, dt):
        ry = self.app.input.axes["ry"]
        if ry:
            self.app.set_volume(self.app.cfg["volume"] - ry * 60 * dt)

    def draw(self, g, t, dt):
        app, m = self.app, self.app.mixer
        g.clear(C["void"])
        header(g, app, "LOOP REACTOR", "reactor")
        bank = app.bank.banks[self.bank]
        bcol = BANK_COL.get(bank.get("color"), C["cyan"])
        beat = m.play_beat()
        phase = beat % 1.0
        cell, gap = 64, 6
        # left cross = d-pad pads 0..3
        for side, base, ox in (("dpad", 0, 20), ("face", 4, W - 20 - 3 * cell - 2 * gap)):
            items = {}
            names = ["up", "left", "right", "down"]
            glyphs = ["up", "left", "right", "down"] if side == "dpad" else ["x", "y", "a", "b"]
            for i, pos in enumerate(names):
                p = base + i

                def mk(p=p, gl=glyphs[i]):
                    def f(x, y, w, h):
                        pad = app.bank.pad(self.bank, p)
                        st = self.state(self.bank, p)
                        fl = time.time() - self.flash.get(self.key(self.bank, p), 0)
                        if st == "idle" and fl < 0.12:
                            st = "shot"
                        pad_box(g, app, x, y, w, h, pad["label"], gl, st, t, phase, bcol)
                    return f
                items[pos] = mk()
            cross(g, ox, 72, cell, gap, items)
            # centre plate
            cx = ox + cell + gap
            g.rect(cx, 72 + cell + gap, cell, cell, C["hulllo"])
            g.frame(cx, 72 + cell + gap, cell, cell, C["hull"], 2)
            if side == "dpad":
                ui.dpad(g, cx + cell // 2 - 9, 72 + cell + gap + cell // 2 - 9, "DPAD")
            else:
                g.text(ui.SMALL, "XYAB", cx + cell // 2, 72 + cell + gap + 22, C["dim"], 255, "center")
        # reactor core
        ccx, ccy = W // 2, 140
        pulse = (1.0 - phase) ** 2 if app.cfg["anim"] else 0.3
        ring = []
        rot = t * 1.0 if app.cfg["anim"] else 0
        for i in range(24):
            a = rot + i * math.pi * 2 / 24
            ring.append((ccx + math.cos(a) * 64 - 3, ccy + math.sin(a) * 64 - 3, 6, 6))
        g.rects(ring, C["violet"])
        rad = 44 + int(5 * pulse)
        core = []
        for yy in range(-rad, rad + 1, 3):
            half = int(math.sqrt(max(0, rad * rad - yy * yy)))
            core.append((ccx - half, ccy + yy, half * 2, 3))
        g.rects(core, C["panel"])
        g.rects(core, C["cyan"], int(20 + 60 * pulse))
        edge = []
        for i in range(48):
            a = i * math.pi * 2 / 48
            edge.append((ccx + math.cos(a) * rad - 2, ccy + math.sin(a) * rad - 2, 4, 4))
        g.rects(edge, C["cyan"])
        g.text("v44", "%d" % round(m.bpm), ccx, ccy - 26, C["text"], 255, "center")
        g.text("p8", "BPM", ccx, ccy + 16, C["cyan"], 255, "center")
        # beat LEDs
        cur = int(math.floor(beat)) % m.beats_per_bar
        lw = 22
        lx0 = ccx - (m.beats_per_bar * (lw + 6) - 6) // 2
        for i in range(m.beats_per_bar):
            on = (i == cur)
            g.rect(lx0 + i * (lw + 6), 222, lw, lw, app.accent if on else C["led"])
            g.frame(lx0 + i * (lw + 6), 222, lw, lw, C["orangehi"] if on else C["hulllo"], 2)
        # bank selector
        ui.keys(g, "L1", ccx - 84, 258)
        ui.box(g, ccx - 52, 252, 104, 30, C["panel"])
        ui.outline(g, ccx - 52, 252, 104, 30, bcol, 2)
        g.text(ui.SMALL, bank["name"], ccx, 256, bcol, 255, "center")
        ui.keys(g, "R1", ccx + 58, 258)
        dots = len(app.bank.banks)
        for i in range(dots):
            g.rect(ccx - dots * 6 + i * 12 + 2, 288, 8, 8, bcol if i == self.bank else C["hull"])
        if m.warp:
            g.text(ui.SMALL, "SOM ABAFADO", ccx, 300, C["cyan"] if int(t * 8) % 2 else C["violet"], 255, "center")
        # playing loops = progress bars
        playing = []
        for v in list(m.voices):
            if v.group == "reactor" and v.loop and v.start <= m.clock:
                bi, pi = [int(x) for x in v.key.split(":")[1:]]
                playing.append((app.bank.pad(bi, pi)["label"], v.pos / float(max(1, len(v.data) // 4))))
        y = 330
        g.text(ui.SMALL, "A TOCAR", 20, y - 6, C["muted"])
        if not playing:
            g.text(ui.SMALL, "nenhum loop: carrega num pad", 110, y - 6, C["dim"])
        for i, (lab, pr) in enumerate(playing[:6]):
            col_x = 20 + (i % 3) * 206
            row_y = y + 20 + (i // 3) * 30
            g.text("v20", lab, col_x, row_y - 4, C["soft"])
            g.rect(col_x + 72, row_y + 2, 120, 8, C["deck"])
            g.rect(col_x + 72, row_y + 2, int(120 * pr), 8, app.accent)
        footer(g, [("setas + X/Y/A/B", "tocar pads"), ("L1/R1", "banco"), ("L2", "parar tudo")])


# ---------------------------------------------------------------------- XENO SYNTH
SCALES = [("MIN PENTA", [0, 3, 5, 7, 10, 12, 15, 17]), ("MINOR", [0, 2, 3, 5, 7, 8, 10, 12]),
          ("MAJOR", [0, 2, 4, 5, 7, 9, 11, 12]), ("BLUES", [0, 3, 5, 6, 7, 10, 12, 15]),
          ("DORIAN", [0, 2, 3, 5, 7, 9, 10, 12]), ("PHRYGIAN", [0, 1, 3, 5, 7, 8, 10, 12])]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SCALE_PT = {"MIN PENTA": "PENTA MENOR", "MINOR": "MENOR", "MAJOR": "MAIOR", "BLUES": "BLUES", "DORIAN": "DÓRICA",
            "PHRYGIAN": "FRÍGIA"}
XENO_KEYS = ["left", "up", "right", "down", "y", "x", "a", "b"]


class Xeno(Section):
    name = "XENO SYNTH"

    def __init__(self, app):
        Section.__init__(self, app)
        self.meta = json.load(open(os.path.join(engine.ASSETS, "synth", "synth.json")))
        self.wave = 0
        self.scale = 0
        self.octave = 3
        self.hold = False
        self.tables = {}
        self.active = {}   # button -> [voices]

    def table(self, wave, octv, bright):
        k = (wave, octv, bright)
        if k not in self.tables:
            fn = "%s_o%d_%s.raw" % (self.meta["waves"][wave].lower(), octv, "b" if bright else "d")
            cyc = open(os.path.join(engine.ASSETS, "synth", fn), "rb").read()
            reps = max(1, 8192 // (len(cyc) // 2))
            mono = cyc * reps
            self.tables[k] = audioop.tostereo(mono, 2, 1, 1)
        return self.tables[k]

    def voice(self, midi):
        octv = max(1, min(6, midi // 12 - 1))
        info = self.meta["octaves"][str(octv)]
        return SynthVoice(midi, self.table(self.wave, octv, True), self.table(self.wave, octv, False), info["freq"])

    def note_for(self, b):
        iv = SCALES[self.scale][1][XENO_KEYS.index(b)]
        return 12 * (self.octave + 1) + iv

    def note_on(self, b):
        m = self.app.mixer
        notes = [self.note_for(b)]
        if self.app.input.down("r2"):
            notes.append(notes[0] + 7)
        vs = [self.voice(n) for n in notes]
        self.app.rec.event(m.clock, b)
        with m.lock:
            m.synth.extend(vs)
            live = [s for s in m.synth if s.held]
            while len(live) > 6:
                live[0].release()
                live = live[1:]
        self.active.setdefault(b, []).extend(vs)

    def note_off(self, b):
        self.app.rec.event_off(self.app.mixer.clock, b)
        for v in self.active.pop(b, []):
            v.release()

    def on(self, kind, b):
        if kind == "press" and b in XENO_KEYS:
            self.notes_played = getattr(self, "notes_played", 0) + 1
            if self.notes_played >= 8:
                self.app.mission("xeno_notes")
            if self.hold and self.active.get(b):
                self.note_off(b)
            else:
                self.note_on(b)
        elif kind == "release" and b in XENO_KEYS and not self.hold:
            self.note_off(b)
        elif kind == "press" and b == "l1":
            self.octave = max(1, self.octave - 1)
        elif kind == "press" and b == "r1":
            self.octave = min(5, self.octave + 1)
        elif kind == "press" and b == "l2":
            self.hold = not self.hold
            if not self.hold:
                for k in list(self.active):
                    if not self.app.input.down(k):
                        self.note_off(k)
        elif kind == "press" and b == "l3":
            self.wave = (self.wave + 1) % len(self.meta["waves"])
        elif kind == "press" and b == "r3":
            self.scale = (self.scale + 1) % len(SCALES)

    def combo(self, b):
        if b == "a":
            self.app.rec.toggle("XENO")
            return True
        if b in ("left", "right"):
            self.wave = (self.wave + (1 if b == "right" else -1)) % len(self.meta["waves"])
            return True
        if b in ("up", "down"):
            self.scale = (self.scale + (1 if b == "up" else -1)) % len(SCALES)
            return True
        return False

    def leave(self):
        for k in list(self.active):
            self.note_off(k)

    def update(self, dt):
        ax = self.app.input.axes
        m = self.app.mixer
        m.synth_bend = round(ax["lx"] * 2.0 * 16) / 16.0
        m.synth_tone = max(0.0, min(1.0, 0.6 - ax["ry"] * 0.4))

    def draw(self, g, t, dt):
        app, m = self.app, self.app.mixer
        g.clear(C["void"])
        header(g, app, "XENO SYNTH", "xeno")
        # scope
        sx, sy, sw, sh = 16, 64, W - 32, 110
        g.rect(sx, sy, sw, sh, C["panel"])
        g.frame(sx, sy, sw, sh, C["hullhi"], 3)
        g.rect(sx + 3, sy + sh // 2, sw - 6, 1, C["hull"])
        smp = array.array("h")
        smp.frombytes(m.last)
        left = smp[0::2]
        n = len(left)
        pts = []
        prev = None
        cols = 300
        for i in range(cols):
            v = left[int(i * n / cols)] if n else 0
            y = sy + sh // 2 - int(v / 32768.0 * (sh // 2 - 8))
            x = sx + 4 + int(i * (sw - 8) / cols)
            if prev is not None:
                y0, y1 = min(prev, y), max(prev, y)
                pts.append((x, y0, 2, max(2, y1 - y0)))
            prev = y
        g.rects(pts, C["cyan"])
        g.text(ui.SMALL, "ONDA DO SOM", sx + 10, sy + 4, C["violet"])
        held = [s for s in m.synth if s.held]
        if held:
            names = " + ".join("%s%d" % (NOTE_NAMES[s.note % 12], s.note // 12 - 1) for s in held[:4])
            g.text("v20", names, sx + sw - 10, sy + 4, app.accent, 255, "right")
        # sticks
        for i, (lab, axx, axy, col) in enumerate((("DOBRAR NOTA", "lx", "ly", C["cyan"]),
                                                  ("FILTRO", "rx", "ry", C["violet"]))):
            bx = 16 if i == 0 else W - 16 - 104
            by = 200
            g.rect(bx, by, 104, 104, C["panel"])
            g.frame(bx, by, 104, 104, C["hullhi"], 3)
            g.rect(bx + 52, by + 3, 1, 98, C["hull"])
            g.rect(bx + 3, by + 52, 98, 1, C["hull"])
            dx = bx + 52 + int(app.input.axes[axx] * 40) - 6
            dy = by + 52 + int(app.input.axes[axy] * 40) - 6
            g.glow(dx, dy, 12, 12, col, 0.6)
            g.rect(dx, dy, 12, 12, col)
            ui.stick(g, bx + 2, by + 112, "L" if i == 0 else "R")
            g.text(ui.SMALL, lab, bx + 24, by + 111, C["muted"])
        # keys (2 rows x 4)
        kx0, ky0, kw, kh, kg = 140, 196, 84, 58, 6
        glyph = {"left": "left", "up": "up", "right": "right", "down": "down", "y": "y", "x": "x", "a": "a", "b": "b"}
        for i, b in enumerate(XENO_KEYS):
            x = kx0 + (i % 4) * (kw + kg)
            y = ky0 + (i // 4) * (kh + kg)
            midi = self.note_for(b)
            on = bool(self.active.get(b))
            if on:
                pulse = 0.5 + 0.5 * math.sin(t * 12) if app.cfg["anim"] else 0.6
                g.glow(x, y, kw, kh, app.accent, 0.3 + 0.5 * pulse)
                g.bevel(x, y, kw, kh, app.accent, C["orangehi"], C["orangelo"])
                fg = C["void"]
            else:
                g.bevel(x, y, kw, kh, C["hull"], C["hullhi"], C["hulllo"])
                fg = C["soft"]
            gl = glyph[b]
            if gl in ("up", "down", "left", "right"):
                g.tri(x + kw // 2 - 5, y + 8, 5, gl, fg)
            else:
                g.text("p8", gl.upper(), x + kw // 2, y + 10, fg, 255, "center")
            g.text("p16", NOTE_NAMES[midi % 12], x + kw // 2, y + 32, fg, 255, "center")
        ui.panel(g, 16, 344, W - 32, 82, C["violet"])
        stats = [("ONDA", {"SAW": "SERRA", "SQUARE": "QUADRADA", "TRI": "SUAVE"}.get(self.meta["waves"][self.wave],
                                                                                    self.meta["waves"][self.wave]), "SEL+esq/dir"), ("ESCALA", SCALE_PT.get(SCALES[self.scale][0], SCALES[self.scale][0]), "SEL+cima/baixo"),
                 ("OITAVA", "%d" % self.octave, "L1/R1"), ("SEGURAR", "ON" if self.hold else "OFF", "L2"),
                 ("ACORDE", "ON" if app.input.down("r2") else "OFF", "R2")]
        cw = (W - 48) // len(stats)
        for i, (lab, val, k) in enumerate(stats):
            x = 24 + i * cw
            g.text(ui.SMALL, lab, x, 350, C["muted"])
            g.text(ui.BODY, ui.fit(g, ui.BODY, val, cw - 6), x, 368, app.accent if val == "ON" else C["text"])
            ui.keys(g, k, x, 400, 16)
        footer(g, [("setas + X/Y/A/B", "tocar notas"), ("L1/R1", "oitava"), ("L2", "segurar")])


# ---------------------------------------------------------------------- PULSAR
class Pulsar(Section):
    name = "PULSAR"
    DIVS = [1, 2, 4]

    def __init__(self, app):
        Section.__init__(self, app)
        self.taps = []
        self.div_i = 0

    def on(self, kind, b):
        app, m = self.app, self.app.mixer
        if kind in ("press", "repeat") and b in ("left", "right"):
            app.set_bpm(m.bpm + (1 if b == "right" else -1))
            app.mission("pulsar_bpm")
        elif kind == "press" and b == "a":
            app.mission("pulsar_bpm")
            now = time.time()
            if self.taps and now - self.taps[-1] > 2.0:
                self.taps = []
            self.taps.append(now)
            self.taps = self.taps[-6:]
            if len(self.taps) >= 2:
                iv = [b2 - b1 for b1, b2 in zip(self.taps, self.taps[1:])]
                app.set_bpm(round(60.0 / (sum(iv) / len(iv)), 1))
            app.mixer.shot("tap", app.snd["click_hi"], group="ui", gain=0.5)
        elif kind == "press" and b in ("up", "down"):
            opts = [3, 4, 5, 7]
            i = opts.index(m.beats_per_bar) if m.beats_per_bar in opts else 1
            i = (i + (1 if b == "up" else -1)) % len(opts)
            with m.lock:
                m.anchor_beat = m.beat_at(m.clock)
                m.anchor_clock = m.clock
                m.beats_per_bar = opts[i]
        elif kind == "press" and b == "b":
            m.metro = not m.metro
        elif kind == "press" and b == "x":
            self.div_i = (self.div_i + 1) % len(self.DIVS)
            m.metro_div = self.DIVS[self.div_i]

    def draw(self, g, t, dt):
        app, m = self.app, self.app.mixer
        g.clear(C["void"])
        header(g, app, "PULSAR", "pulsar")
        beat = m.play_beat()
        ph = beat % 1.0
        flash = (1 - ph) ** 3 if app.cfg["anim"] else 0.3
        cx, cy = W // 2, 150
        # expanding rings (one per beat, offset half bar)
        for k, col in ((0.0, C["cyan"]), (0.5, C["violet"])):
            rr = ((beat / 2.0 + k) % 1.0)
            r = 30 + rr * 90
            a = int(200 * (1 - rr))
            ring = []
            for i in range(40):
                an = i * math.pi * 2 / 40
                ring.append((cx + math.cos(an) * r - 2, cy + math.sin(an) * r - 2, 4, 4))
            g.rects(ring, col, a)
        # pixel star
        s = 8 + int(4 * flash)
        rays = [(cx - s // 2, cy - s * 5 // 2 - s, s, s * 2), (cx - s // 2, cy + s * 3 // 2, s, s * 2),
                (cx - s * 5 // 2 - s, cy - s // 2, s * 2, s), (cx + s * 3 // 2, cy - s // 2, s * 2, s)]
        g.rects(rays, C["cyan"], int(80 + 175 * flash))
        g.rects([(cx - 2 * s, cy - s * 3 // 2, 4 * s, 3 * s), (cx - s * 3 // 2, cy - 2 * s, 3 * s, 4 * s)],
                mix(C["text"], C["white"], flash))
        g.rect(cx - s // 2, cy - s // 2, s, s, app.accent)
        # the BPM: the one thing to look at
        g.text(ui.DISPLAY, "%g" % round(m.bpm, 1), cx + 3, 236, C["violet"], 255, "center")
        g.text(ui.DISPLAY, "%g" % round(m.bpm, 1), cx, 233, C["text"], 255, "center")
        g.text(ui.SMALL, "BPM", cx, 288, C["cyan"], 255, "center")
        n = m.beats_per_bar
        bi = int(beat) % n
        for i in range(n):
            x = cx - n * 14 + i * 28 + 4
            on = i == bi
            ui.box(g, x, 312, 20, 12, (app.accent if i == 0 else C["cyan"]) if on else C["hull"])
        g.text(ui.SMALL, "%d/4" % n, cx, 330, C["muted"], 255, "center")
        # left: tap the tempo
        ui.panel(g, 16, 68, 172, 160, C["cyan"], "BATER O TEMPO")
        g.text(ui.SMALL, "carrega A ao ritmo", 28, 84, C["soft"])
        g.text(ui.SMALL, "de uma música", 28, 102, C["soft"])
        iv = [b2 - b1 for b1, b2 in zip(self.taps, self.taps[1:])]
        for i in range(6):
            x = 28 + i * 25
            if i < len(iv):
                hgt = int(max(8, min(60, 60.0 / iv[i] / 3)))
                g.rect(x, 196 - hgt, 20, hgt, app.accent if i == len(iv) - 1 else C["violet"])
            else:
                g.rect(x, 188, 20, 8, C["hull"])
        tap_on = (time.time() - (self.taps[-1] if self.taps else 0)) < 0.12
        xe = ui.keys(g, "A", 28, 203)
        g.text(ui.SMALL, "%d toques" % len(self.taps), xe + 6, 202, C["text"] if tap_on else C["muted"])
        # right: settings, each with its button
        rx, rw = W - 188, 172
        ui.panel(g, rx, 68, rw, 160, C["violet"], "AJUSTES")
        rows = [("cima/baixo", "Compasso", "%d/4" % n), ("X", "Subdivisão", "1/%d" % (4 * self.DIVS[self.div_i])),
                ("B", "Clique", "ON" if m.metro else "OFF")]
        for i, (k, lab, val) in enumerate(rows):
            y = 88 + i * 44
            xe = ui.keys(g, k, rx + 12, y + 2)
            g.text(ui.SMALL, lab, xe + 6, y, C["soft"])
            g.text(ui.HEAD, val, rx + rw - 12, y + 14, C["green"] if val == "ON" else C["text"], 255, "right")
        # bottom: which BPM for which style
        guide = [(90, "HIP HOP"), (120, "HOUSE"), (140, "TRAP"), (174, "DRUM & BASS")]
        near = min(guide, key=lambda gg: abs(gg[0] - m.bpm))
        gx = 40
        for bpm, name in guide:
            on = (bpm, name) == near and abs(bpm - m.bpm) <= 6
            wdt = (W - 80) // 4
            ui.box(g, gx + 2, 360, wdt - 4, 46, C["hull"] if not on else C["cyan"])
            g.text(ui.HEAD, "%d" % bpm, gx + wdt // 2, 360, C["void"] if on else C["text"], 255, "center")
            g.text(ui.SMALL, name, gx + wdt // 2, 384, C["void"] if on else C["muted"], 255, "center")
            gx += wdt
        footer(g, [("esq/dir", "mudar o BPM"), ("A", "bater o tempo"), ("B", "clique")])


def mix(a, b, t):
    return engine.mix(a, b, max(0.0, min(1.0, t)))


# ---------------------------------------------------------------------- ABDUCTOR (recorder)
class Abductor(Section):
    name = "ABDUCTOR"

    def __init__(self, app):
        Section.__init__(self, app)
        self.devices = []   # (card, dev, name)
        self.sel = 0
        self.has_mic = False
        self.proc = None
        self.rec_path = None
        self.rec_t0 = 0
        self.last = None
        self.level = 0.0
        self.msg = ""
        self.arecord = shutil.which("arecord")
        self.panel = "rec"                     # rec | cut | play  (L1/R1)
        self.chop = chop.Chop(app)
        self.scan()

    PANELS = [("rec", "GRAVAR"), ("cut", "CORTAR"), ("play", "TOCAR")]

    def switch(self, d):
        keys = [k for k, _ in self.PANELS]
        self.panel = keys[(keys.index(self.panel) + d) % len(keys)]
        if self.panel == "cut" and self.chop.data is None and self.last and not self.chop.loading:
            self.chop.load_path(self.last, os.path.splitext(os.path.basename(self.last))[0])
        self.app.ui_move()
        self.app.help.maybe_tutorial("abductor")

    def combo(self, b):
        if self.panel != "rec":
            return self.chop.combo(self.panel, b)
        return False

    def scan(self):
        self.devices = []
        if not self.arecord:
            self.msg = ""
            return
        try:
            out = subprocess.check_output([self.arecord, "-l"], stderr=subprocess.STDOUT, timeout=3).decode("utf8",
                                                                                                          "replace")
        except Exception:
            out = ""
            self.msg = ""
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("card ") and "device" in line:
                try:
                    card = int(line.split(":")[0].split()[1])
                    dev = int(line.split("device")[1].split(":")[0])
                    name = line.split("[")[1].split("]")[0] if "[" in line else line
                    self.devices.append((card, dev, name))
                except Exception:
                    pass
        usb = [d for d in self.devices if "usb" in d[2].lower() or d[0] > 0]
        self.has_mic = bool(usb)
        if usb:
            self.sel = self.devices.index(usb[0])
        if not self.devices and not self.msg:
            self.msg = ""

    def enter(self):
        if not self.proc:
            self.scan()

    def toggle_rec(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(2)
            except Exception:
                self.proc.kill()
            self.proc = None
            self.last = self.rec_path
            self.msg = "Gravado! R1 abre a gravação no CORTAR"
            return
        if not self.devices:
            self.msg = "Liga um micro USB e volta a entrar"
            return
        card, dev, _ = self.devices[self.sel]
        if not os.path.isdir(REC_DIR):
            os.makedirs(REC_DIR)
        self.rec_path = os.path.join(REC_DIR, time.strftime("rec_%Y%m%d_%H%M%S.wav"))
        try:
            self.proc = subprocess.Popen([self.arecord, "-q", "-D", "plughw:%d,%d" % (card, dev), "-f", "S16_LE",
                                          "-r", str(SR), "-c", "2", self.rec_path])
            self.rec_t0 = time.time()
            self.msg = "A gravar..."
        except Exception as e:
            log("rec: %r" % (e,))
            self.msg = "Não deu para gravar"
            self.proc = None

    def on(self, kind, b):
        if kind == "press" and b in ("l1", "r1") and not self.chop.browse:
            self.switch(1 if b == "r1" else -1)
            return
        if self.panel != "rec":
            self.chop.on(self.panel, kind, b)
            return
        if kind != "press":
            return
        if b in ("up", "down") and self.devices and not self.proc:
            self.sel = (self.sel + (1 if b == "down" else -1)) % len(self.devices)
        elif b == "a":
            self.toggle_rec()
        elif b == "x" and self.last and not self.proc:
            try:
                self.app.mixer.shot("recplay", load_wav(self.last), group="ui")
            except Exception as e:
                log("rec play: %r" % (e,))
                self.msg = "Não deu para tocar"
        elif b == "b":
            self.app.mixer.kill_key("recplay")
        elif b == "y" and self.last and not self.proc:
            self.app.cfg.setdefault("custom_pads", {})["3:7"] = self.last
            self.app.save_cfg()
            pad = self.app.bank.pad(3, 7)
            pad["file"], pad["mode"], pad["label"] = self.last, "shot", "MY REC"
            self.app.bank.load_pad(3, 7)
            self.msg = "Enviado para o Loop Reactor (banco SIGNAL, pad B)"

    def update(self, dt):
        if self.proc and self.proc.poll() is not None:
            self.proc = None
            self.msg = "a gravacao parou (micro desligado?)"
        if self.proc and self.rec_path and os.path.exists(self.rec_path):
            try:
                size = os.path.getsize(self.rec_path)
                if size > 44 + 8820:
                    with open(self.rec_path, "rb") as f:
                        f.seek(size - 8820 - (size - 44) % 4)
                        self.level = audioop.rms(f.read(8820), 2) / 12000.0
            except Exception:
                pass
        else:
            self.level *= 0.9

    def draw_tabs(self, g):
        x = 16
        xe = ui.keys(g, "L1", x, 55, 16)
        x = xe + 4
        for k, label in self.PANELS:
            w = g.tw(ui.SMALL, label) + 16
            on = k == self.panel
            ui.box(g, x, 53, w, 20, self.app.accent if on else C["hull"])
            g.text(ui.SMALL, label, x + 8, 53, C["void"] if on else C["muted"])
            x += w + 4
        ui.keys(g, "R1", x, 55, 16)

    def draw(self, g, t, dt):
        app = self.app
        g.clear(C["void"])
        header(g, app, "ABDUCTOR", "abductor")
        self.draw_tabs(g)
        if self.panel != "rec":
            self.chop.draw(g, self.panel, t)
            if self.chop.data and not self.chop.browse:
                items = ([("cima/baixo", "marcador", 0), ("esq/dir", "mover", 0), ("Y", "ouvir fatia", 0),
                          ("SEL+X", "fatias para o Reactor", 0)]
                         if self.panel == "cut" else
                         [("setas + X/Y/A/B", "tocar fatias", 0), ("L2/R2", "página", 0),
                          ("SEL+X", "fatias para o Reactor", 0)])
            else:
                items = [("A", "escolher ficheiro", 0), ("L1/R1", "mudar de painel", 0)]
            footer(g, items)
            return
        # beam visual
        rec = self.proc is not None
        cx = W // 2
        draw_ship(g, cx - 100, 64, 5, t, min(1.0, 0.2 + self.level * 2) if rec else 0.15, app.accent)
        lv = min(1.0, self.level)
        bars = []
        for i in range(24):
            hgt = int(4 + 70 * lv * abs(math.sin(i * 0.7 + t * 9))) if rec else 4
            bars.append((cx - 24 * 7 + i * 14, 290 - hgt, 10, hgt))
        g.rects(bars, C["cyan"] if not rec else app.accent)
        if rec:
            el = time.time() - self.rec_t0
            if int(t * 2) % 2 == 0:
                g.rect(cx - 104, 304, 16, 16, (255, 60, 60))
            g.text(ui.TITLE, "A GRAVAR %02d:%02d" % (el // 60, el % 60), cx + 8, 296, C["text"], 255, "center")
        else:
            g.text(ui.TITLE, "PRONTO A GRAVAR" if self.devices else "SEM MICRO", cx, 296,
                   C["green"] if self.devices else C["muted"], 255, "center")
        y = 342
        if not self.devices:
            ui.panel(g, 24, y, W - 48, 82, C["cyan"])
            g.text(ui.SMALL, "Para gravar a tua voz, liga um micro USB (com adaptador USB-C).", 38, y + 8, C["soft"])
            xe = ui.keys(g, "R1", 38, y + 42)
            g.text(ui.BODY, "Sem micro? Corta músicas em fatias e toca-as", xe + 8, y + 36, C["cyan"])
        else:
            g.text(ui.SMALL, "ENTRADA", 24, y, C["muted"])
            for i, (card, dev, name) in enumerate(self.devices[:3]):
                sel = i == self.sel
                g.text(ui.SMALL, ("▶ " if sel else "   ") + name[:44], 24, y + 20 + i * 20,
                       app.accent if sel else C["soft"])
        if self.msg:
            ui.toast(g, self.msg, C["cyan"], 252)
        footer(g, [("A", "gravar / parar", 0), ("X", "ouvir", 0), ("Y", "mandar para um pad", 0),
                   ("L1/R1", "mudar de painel", 0)])


# ---------------------------------------------------------------------- WARP FLOOR (dancefloor / auto-DJ)
class Warp(Section):
    name = "WARP FLOOR"
    XFADE = 8.0

    def __init__(self, app):
        Section.__init__(self, app)
        self.tracks = []
        self.idx = -1
        self.cur = None
        self.shuffle = False
        self.paused = False
        self.converting = set()
        self.ready = {}
        self.msg = ""
        self.conv = shutil.which("ffmpeg") or shutil.which("mpg123")
        self.lock = threading.Lock()

    def scan(self):
        if not os.path.isdir(MUSIC_DIR):
            try:
                os.makedirs(MUSIC_DIR)
            except Exception:
                pass
        exts = (".wav", ".mp3", ".ogg", ".flac", ".m4a")
        out = []
        for root, _, files in os.walk(MUSIC_DIR):
            if ".cache" in root:
                continue
            for f in sorted(files):
                if f.lower().endswith(exts):
                    out.append(os.path.join(root, f))
        self.tracks = out

    def enter(self):
        self.scan()
        if not self.tracks:
            self.msg = "poe musica em ports/mothership/music"
        if self.cur is None and self.tracks:
            self.prepare(0)

    def cache_path(self, src):
        d = os.path.join(MUSIC_DIR, ".cache")
        if not os.path.isdir(d):
            os.makedirs(d)
        return os.path.join(d, os.path.basename(src) + ".wav")

    def prepare(self, i):
        """make sure track i exists as 44.1k stereo s16 wav (converts in background)"""
        if not self.tracks:
            return
        src = self.tracks[i % len(self.tracks)]
        if src in self.ready or src in self.converting:
            return
        if src.lower().endswith(".wav"):
            try:
                wf = wave.open(src, "rb")
                okfmt = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) == (2, 2, SR)
                wf.close()
            except Exception:
                okfmt = False
            if okfmt:
                self.ready[src] = src
                return
        dst = self.cache_path(src)
        if os.path.exists(dst):
            self.ready[src] = dst
            return
        self.converting.add(src)
        threading.Thread(target=self._convert, args=(src, dst), daemon=True).start()

    def _convert(self, src, dst):
        ok = False
        try:
            tool = self.conv
            if src.lower().endswith(".wav") and not tool:
                wf = wave.open(src, "rb")
                data = to_std(wf.readframes(wf.getnframes()), wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
                wf.close()
                out = wave.open(dst + ".part", "wb")
                out.setnchannels(2)
                out.setsampwidth(2)
                out.setframerate(SR)
                out.writeframes(data)
                out.close()
                ok = True
            elif tool and os.path.basename(tool) == "ffmpeg":
                ok = subprocess.call([tool, "-v", "error", "-y", "-i", src, "-ar", str(SR), "-ac", "2", "-f", "wav",
                                      dst + ".part"]) == 0
            elif tool and src.lower().endswith(".mp3"):
                ok = subprocess.call([tool, "-q", "-r", str(SR), "--stereo", "-w", dst + ".part", src]) == 0
            if ok:
                os.rename(dst + ".part", dst)
        except Exception as e:
            log("convert %s %r" % (src, e))
        with self.lock:
            self.converting.discard(src)
            if ok:
                self.ready[src] = dst
            else:
                self.msg = "nao consegui ler %s" % os.path.basename(src)[:30]

    def next_index(self):
        if not self.tracks:
            return 0
        if self.shuffle and len(self.tracks) > 1:
            j = self.idx
            while j == self.idx:
                j = random.randrange(len(self.tracks))
            return j
        return (self.idx + 1) % len(self.tracks)

    def start(self, i, xfade):
        src = self.tracks[i % len(self.tracks)]
        path = self.ready.get(src)
        if not path:
            self.prepare(i)
            self.msg = "a preparar faixa..."
            return False
        try:
            v = StreamVoice(path)
        except Exception as e:
            self.msg = "erro: %s" % e
            return False
        m = self.app.mixer
        with m.lock:
            if self.cur is not None and not self.cur.done:
                self.cur.fade(0.0, xfade)
            if xfade > 0:
                v.g = 0.0
                v.fade(1.0, xfade)
            m.streams.append(v)
        self.cur = v
        self.idx = i % len(self.tracks)
        self.paused = False
        self.prepare(self.next_index())
        return True

    def on(self, kind, b):
        if kind not in ("press",):
            return
        if not self.tracks:
            self.scan()
            return
        if b == "a":
            if self.cur is None or self.cur.done:
                self.start(max(0, self.idx), 0.0)
            else:
                self.set_paused(not self.paused)
        elif b == "right":
            self.start(self.next_index(), 4.0)
        elif b == "left":
            self.start((self.idx - 1) % len(self.tracks), 2.0)
        elif b == "x":
            self.shuffle = not self.shuffle
        elif b == "b":
            self.stop()

    def set_paused(self, p):
        self.paused = p
        m = self.app.mixer
        with m.lock:
            for s in m.streams:
                if getattr(s, "group", "") == "floor":
                    s.paused = p

    def stop(self):
        m = self.app.mixer
        with m.lock:
            for s in m.streams:
                if getattr(s, "group", "") == "floor":
                    s.fade(0.0, 1.0)
        self.cur = None
        self.paused = False

    def now_title(self):
        try:
            return os.path.splitext(os.path.basename(self.tracks[self.idx]))[0]
        except Exception:
            return "a tocar"

    def update(self, dt):
        if self.cur is not None and not self.paused and not self.cur.done and self.tracks:
            left = (self.cur.frames - self.cur.pos) / float(SR)
            if left <= self.XFADE and self.cur.g_to > 0:
                self.start(self.next_index(), self.XFADE)

    def draw(self, g, t, dt):
        app, m = self.app, self.app.mixer
        g.clear(C["void"])
        header(g, app, "WARP FLOOR", "warp")
        smp = m.last
        seg = len(smp) // 16 // 4 * 4
        lv = []
        for i in range(16):
            try:
                lv.append(min(1.0, audioop.rms(smp[i * seg:(i + 1) * seg], 2) / 9000.0))
            except Exception:
                lv.append(0.0)
        energy = sum(lv) / 16.0
        bob = math.sin(t * 2.2) * 4 if app.cfg["anim"] else 0
        draw_ship(g, W // 2 - 120, 62 + bob, 6, t, min(1.0, 0.15 + energy * 2.2), app.accent)
        # floor tiles lit by the beam
        tiles = []
        tiles2 = []
        for i in range(16):
            x = 24 + i * 37
            hgt = int(6 + lv[i] * 90)
            (tiles if i % 2 else tiles2).append((x, 300 - hgt, 30, hgt))
        g.rects(tiles, C["cyan"])
        g.rects(tiles2, C["violet"])
        g.rect(16, 302, W - 32, 3, C["hullhi"])
        y = 318
        if self.tracks and self.idx >= 0:
            name = os.path.splitext(os.path.basename(self.tracks[self.idx]))[0]
            g.text(ui.SMALL, "A TOCAR" if not self.paused else "EM PAUSA", 24, y - 4, C["muted"])
            g.text(ui.HEAD, ui.fit(g, ui.HEAD, name, W - 220), 24, y + 14, C["text"])
            if self.cur is not None:
                pr = self.cur.pos / float(max(1, self.cur.frames))
                g.rect(24, y + 46, W - 48, 6, C["deck"])
                g.rect(24, y + 46, int((W - 48) * pr), 6, app.accent)
                el, tot = self.cur.pos // SR, self.cur.frames // SR
                g.text("v20", "%d:%02d / %d:%02d" % (el // 60, el % 60, tot // 60, tot % 60), W - 24, y + 54,
                       C["muted"], 255, "right")
            nxt = os.path.splitext(os.path.basename(self.tracks[self.next_index()]))[0] if not self.shuffle else "?"
            g.text(ui.SMALL, "a seguir: " + ui.fit(g, ui.SMALL, nxt, 300), 24, y + 54, C["dim"])
        else:
            g.text(ui.HEAD, "AINDA NÃO HÁ MÚSICA A BORDO", W // 2, y, C["text"], 255, "center")
            ui.para(g, ui.SMALL, "No PC, copia músicas (.mp3 .wav .ogg .flac) para a pasta ports/mothership/music "
                    "do cartão. As tuas gravações e sessões também aparecem no TWIN DECKS.", 40, y + 34, W - 80,
                    C["muted"], 18, "left")
        status = "EM PAUSA" if self.paused else ("ALEATÓRIO" if self.shuffle else "PASSAGEM AUTOMÁTICA")
        if self.tracks:
            g.text(ui.SMALL, status, W - 24, y - 4, C["green"], 255, "right")
        if self.msg and self.tracks:
            ui.toast(g, self.msg.replace("poe musica em", "Põe músicas em"), C["cyan"], 200)
        footer(g, [("A", "tocar / pausa", 0), ("esq/dir", "faixa", 0), ("X", "aleatório", 0), ("B", "parar", 0)])


# ---------------------------------------------------------------------- HANGAR (settings)
class Hangar(Section):
    name = "HANGAR"

    def __init__(self, app):
        Section.__init__(self, app)
        self.sel = 0
        self.files = None            # the GRAVACOES manager when open
        self.msg = ("", 0.0)

    def leave(self):
        if self.files is not None:
            self.files.close()
            self.files = None

    def items(self):
        c = self.app.cfg
        return [
            ("VOLUME", "%d" % c["volume"]),
            ("BUFFER AUDIO", "512 · rápido" if c.get("buffer") == 512 else "1024 · estável"),
            ("QUANTIZE", "no compasso" if c["quantize"] == "bar" else "na batida"),
            ("SCANLINES", "ON" if c["scanlines"] else "OFF"),
            ("ANIMACOES", "ON" if c["anim"] else "OFF"),
            ("BOTOES A/B X/Y", "trocados" if c["swap_ab"] else "normal"),
            ("TESTE DE BOTOES", self.app.input.last_raw),
            ("GRAVACOES", "ouvir / apagar"),
            ("REVER TUTORIAIS", ""),
            ("MISSOES", ""),
            ("PET VELOCIDADE", "x%d" % int(c.get("pet_speed", 1)) + (" demo" if int(c.get("pet_speed", 1)) > 1 else "")),
            ("CREDITOS", ""),
            ("SAIR DA NAVE", ""),
        ]

    def on(self, kind, b):
        app, c = self.app, self.app.cfg
        if self.files is not None:
            if not self.files.on(kind, b):
                self.files = None
            return
        if kind in ("press", "repeat") and b in ("up", "down"):
            self.sel = (self.sel + (1 if b == "down" else -1)) % len(self.items())
            app.ui_move()
            return
        if kind not in ("press", "repeat"):
            return
        name = self.items()[self.sel][0]
        delta = 1 if b in ("right", "a") else (-1 if b == "left" else 0)
        if not delta:
            return
        if name == "SCANLINES":
            c["scanlines"] = not c["scanlines"]
        elif name == "ANIMACOES":
            c["anim"] = not c["anim"]
        elif name == "VOLUME":
            app.set_volume(c["volume"] + 5 * delta)
        elif name == "QUANTIZE":
            c["quantize"] = "beat" if c["quantize"] == "bar" else "bar"
        elif name == "PET VELOCIDADE":
            opts = [1, 10, 60]
            cur = int(c.get("pet_speed", 1))
            c["pet_speed"] = opts[(opts.index(cur) + delta) % 3 if cur in opts else 0]
        elif name == "BOTOES A/B X/Y":
            c["swap_ab"] = not c["swap_ab"]
            app.input.reload()
        elif name == "GRAVACOES" and b == "a":
            self.files = recmgr.RecManager(app)
            self.files.open()
        elif name == "BUFFER AUDIO":
            c["buffer"] = 1024 if c.get("buffer") == 512 else 512
            self.msg = ("Fica ativo quando voltares a abrir a app.", time.time())
        elif name == "REVER TUTORIAIS" and b == "a":
            c["seen"] = []
            c["welcomed"] = False
            self.msg = ("Os cartões da primeira vez vão aparecer outra vez.", time.time())
        elif name == "MISSOES" and b == "a":
            app.missions.reset()
            self.msg = ("As missões recomeçam do início.", time.time())
        elif name == "CREDITOS" and b == "a":
            app.sections["credits"].back = "hangar"
            app.go("credits")
        elif name == "SAIR DA NAVE" and b == "a":
            app.running = False
        app.save_cfg()

    LABELS = {   # id -> (group, label, what it does)
        "VOLUME": ("SOM", "Volume", "O volume geral da nave."),
        "BUFFER AUDIO": ("SOM", "Buffer de áudio", "512 = menos atraso (melhor para a voz e o Beat Duel), 1024 = mais "
                         "estável. Aplica-se ao reabrir a app."),
        "QUANTIZE": ("SOM", "Entrada dos loops", "Quando carregas num loop, ele espera pelo início do compasso ou "
                     "só pela próxima batida."),
        "SCANLINES": ("ECRÃ", "Linhas de ecrã antigo", "Riscas finas como num monitor dos anos 80."),
        "ANIMACOES": ("ECRÃ", "Animações", "Desliga se preferires um ecrã mais calmo."),
        "BOTOES A/B X/Y": ("CONTROLOS", "Botões A/B e X/Y", "Troca A com B e X com Y, se os teus botões estiverem ao contrário."),
        "TESTE DE BOTOES": ("CONTROLOS", "Teste de botões", "Carrega em qualquer botão para ver o nome dele."),
        "GRAVACOES": ("NAVE", "Gravações", "Ouve ou apaga as tuas gravações, sessões e misturas."),
        "REVER TUTORIAIS": ("NAVE", "Rever tutoriais", "Mostra outra vez os cartões da primeira vez em cada app."),
        "MISSOES": ("NAVE", "Repetir missões", "Recomeça a missão 'A tua primeira música'."),
        "PET VELOCIDADE": ("NAVE", "Velocidade do Xeno Pet", "x1 normal. x10 e x60 para mostrar a evolução aos amigos."),
        "CREDITOS": ("NAVE", "Créditos", "Quem construiu a nave."),
        "SAIR DA NAVE": ("NAVE", "Sair da nave", "Fecha a app e volta ao menu da consola."),
    }

    def draw(self, g, t, dt):
        app = self.app
        g.clear(C["void"])
        ui.header(g, app, "HANGAR", "hangar")
        if self.files is not None:
            self.files.draw(g, t)
            footer(g, [("A", "ouvir / parar", 0), ("Y", "2x: apagar", 0), ("X", "data / tamanho", 0),
                       ("B", "voltar", 0)])
            return
        its = self.items()
        rh, y0, vis = 26, 56, 12
        top = max(0, min(self.sel - vis // 2, len(its) - vis))
        y = y0
        last_group = None
        shown = 0
        for i in range(top, len(its)):
            name, val = its[i]
            group, label, _ = self.LABELS.get(name, ("NAVE", name, ""))
            if group != last_group:
                if y + 18 + rh > 372:
                    break
                g.text(ui.SMALL, group, 24, y, ui.CAT_COL["SISTEMA"])
                y += 18
                last_group = group
            if y + rh > 372:
                break
            sel = i == self.sel
            ui.box(g, 20, y, W - 40, rh - 3, app.accent if sel else C["hull"])
            fg = C["void"] if sel else C["text"]
            g.text(ui.SMALL, label, 34, y + 1, fg)
            if name == "VOLUME":
                ui.bar(g, W - 230, y + 8, 140, 8, app.cfg["volume"] / 100.0, C["void"] if sel else C["cyan"], C["deck"])
            if name == "TESTE DE BOTOES":
                held = " ".join(k.upper() for k, v in app.input.held.items() if v)
                val = (val + "  " + held)[:30]
            g.text(ui.SMALL, val, W - 34, y + 1, fg, 255, "right")
            y += rh
            shown += 1
        name = its[self.sel][0]
        ui.panel(g, 20, 378, W - 40, 52, C["violet"])
        ui.para(g, ui.SMALL, self.LABELS.get(name, ("", "", ""))[2], 32, 384, W - 64, C["soft"], 18)
        footer(g, [("cima/baixo", "escolher", 0), ("A", "mudar / abrir", 0), ("esq/dir", "mudar valor", 0)])
        s, t0 = self.msg
        if s and time.time() - t0 < 2.5:
            ui.toast(g, s, app.accent, 200)


# ====================================================================== app
class App(object):
    def __init__(self, headless=False):
        self.cfg = load_cfg()
        self.headless = headless
        flags = sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO | sdl2.SDL_INIT_JOYSTICK
        if sdl2.SDL_Init(flags) != 0:
            log("SDL_Init: %s" % sdl2.SDL_GetError())
            sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_JOYSTICK)
        ww, wh = W, H
        if headless:
            wflags = sdl2.SDL_WINDOW_SHOWN
        elif engine.PC:                       # a window on a computer: the biggest whole scale that fits
            wflags = sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE
            r = sdl2.SDL_Rect()
            k = 2
            if sdl2.SDL_GetDisplayUsableBounds(0, ctypes.byref(r)) == 0 and r.w > 0:
                k = max(1, min(3, (r.w - 40) // W, (r.h - 70) // H))
            ww, wh = W * k, H * k
        else:                                 # the console: its whole screen
            wflags = sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_FULLSCREEN
        self.win = sdl2.SDL_CreateWindow(b"Orimbux Mothership", sdl2.SDL_WINDOWPOS_CENTERED,
                                         sdl2.SDL_WINDOWPOS_CENTERED, ww, wh, wflags)
        self.ren = sdl2.SDL_CreateRenderer(self.win, -1, sdl2.SDL_RENDERER_ACCELERATED |
                                           sdl2.SDL_RENDERER_PRESENTVSYNC)
        if not self.ren:
            self.ren = sdl2.SDL_CreateRenderer(self.win, -1, sdl2.SDL_RENDERER_SOFTWARE)
        sdl2.SDL_RenderSetLogicalSize(self.ren, W, H)
        if engine.PC and not headless:
            sdl2.SDL_RenderSetIntegerScale(self.ren, sdl2.SDL_TRUE)      # crisp pixels at any window size
        sdl2.SDL_ShowCursor(0)
        self.fullscreen = False
        self.g = engine.Gfx(self.ren)
        self.input = engine.Input(self.cfg)
        self.input.open_joysticks()
        self.mixer = engine.Mixer()
        self.mixer.bpm = float(self.cfg.get("bpm", 174))
        self.set_volume(self.cfg.get("volume", 80), save=False)
        if not headless:
            if not self.mixer.open():
                log("audio: %s" % sdl2.SDL_GetError())
        self.snd = {}
        for k in ("jingle", "click_hi", "click_lo", "ui_move", "ui_ok"):
            try:
                self.snd[k] = load_wav(os.path.join(engine.ASSETS, k + ".wav"))
            except Exception as e:
                log("snd %s %r" % (k, e))
        self.rec = SessionRec(self)
        self.mixer.click_hi = self.snd.get("click_hi")
        self.mixer.click_lo = self.snd.get("click_lo")
        self.accent = C["orange"]
        self.bank = Bank(self)
        self.sections = {}
        self.sections["abductor"] = Abductor(self)
        self.sections["pet"] = pet.XenoPet(self)
        self.sections["trailer"] = trailer.Trailer(self)
        self.sections["credits"] = credits.Credits(self)
        self.sections["voidrunner"] = voidrunner.VoidRunner(self)
        self.sections["beatduel"] = beatduel.BeatDuel(self)
        self.sections["forge"] = forge.Forge(self)
        self.sections["decks"] = decks.TwinDecks(self)
        self.sections["quiz"] = quiz.Quiz(self)
        self.sections["vox"] = vox.Vox(self)
        for k, cls in (("intro", Intro), ("bridge", Bridge), ("reactor", Reactor), ("xeno", Xeno),
                       ("pulsar", Pulsar), ("warp", Warp), ("hangar", Hangar)):
            self.sections[k] = cls(self)
        self.cur = None
        self.cur_name = None
        self.running = True
        self.sel_combo = False
        self.sel_t0 = 0.0
        self.help_shown = False
        self.help = helpmod.Help(self)
        ui.APP = self
        self.music_menu = musicmenu.MusicMenu(self)
        self.missions = missions.Missions(self)
        self.paused_state = None
        self.st_t0 = None             # START pressed at (tap = next app, hold = music menu)
        self.st_menu = False
        self.t = 0.0
        threading.Thread(target=self._load, daemon=True).start()
        self.go("intro")

    def _load(self):
        try:
            self.bank.load_all()
        except Exception as e:
            log("bank: %r" % (e,))
            self.bank.ready = True

    # ---- helpers
    def save_cfg(self, sync=False):
        try:
            self.cfg["bpm"] = round(self.mixer.bpm, 1)
            engine.write_json(CFG_PATH, self.cfg, sync, indent=1)
        except Exception as e:
            log("cfg %r" % (e,))

    def set_volume(self, v, save=True):
        v = max(0, min(100, v))
        self.cfg["volume"] = v
        self.mixer.master = (v / 100.0) ** 1.3

    def set_bpm(self, bpm):
        self.mixer.set_bpm(bpm)
        self.sections["reactor"].refit()

    def ui_move(self):
        if self.snd.get("ui_move"):
            self.mixer.shot("ui_move", self.snd["ui_move"], group="ui", gain=0.5)

    def ui_ok(self):
        if self.snd.get("ui_ok"):
            self.mixer.shot("ui_ok", self.snd["ui_ok"], group="ui", gain=0.6)

    # ---- START: tap = next music app, hold = music menu
    def start_tap(self):
        if self.cur_name in CYCLE:
            i = CYCLE.index(self.cur_name)
            self.ui_move()
            self.go(CYCLE[(i + 1) % len(CYCLE)])
        elif hasattr(self.cur, "on_start"):
            self.cur.on_start()

    # ---- the global music transport (music menu + header chip)
    def reactor_loops(self):
        m = self.mixer
        with m.lock:
            return [v.key for v in m.voices if v.group == "reactor" and v.loop and not v.done and v.stop is None]

    def now_playing(self):
        fg, dk, w, vx = (self.sections[k] for k in ("forge", "decks", "warp", "vox"))
        loops = self.reactor_loops()
        warp_on = w.cur is not None and not w.cur.done and not w.paused
        da, db = bool(dk.a.playing and dk.a.wf), bool(dk.b.playing and dk.b.wf)
        return {"playing": bool(fg.playing or loops or da or db or warp_on), "forge": fg.playing, "loops": loops,
                "decks": (da, db), "warp": warp_on, "rec": self.rec.active(), "mic": vx.live}

    def music_toggle(self):
        st = self.now_playing()
        fg, dk, w = (self.sections[k] for k in ("forge", "decks", "warp"))
        if st["playing"]:
            self.paused_state = st
            fg.stop()
            self.mixer.kill_group("reactor")
            dk.a.playing = dk.b.playing = False
            if st["warp"]:
                w.set_paused(True)
            return "Pausa"
        ps, self.paused_state = self.paused_state, None
        if ps:
            if ps["forge"]:
                fg.play()
            r = self.sections["reactor"]
            for k in ps["loops"]:
                try:
                    _, b, p = k.split(":")
                    old = r.bank
                    r.bank = int(b)
                    r.trigger(int(p))
                    r.bank = old
                except Exception:
                    pass
            dk.a.playing, dk.b.playing = ps["decks"][0] and bool(dk.a.wf), ps["decks"][1] and bool(dk.b.wf)
            if ps["warp"]:
                w.set_paused(False)
            return "A tocar"
        fg.play()
        return "Beat Forge a tocar"

    def music_stop(self):
        self.paused_state = None
        self.sections["forge"].stop()
        self.mixer.kill_group("reactor")
        dk = self.sections["decks"]
        dk.a.playing = dk.b.playing = False
        self.sections["warp"].stop()

    def record_toggle(self):
        if self.rec.active():
            self.rec.toggle(self.rec.src)
            return "Gravação guardada: joga-a no Beat Duel"
        spec = self.cur.rec_spec() if hasattr(self.cur, "rec_spec") else (TITLE_OF.get(self.cur_name, "SESSAO"), None)
        src, max_s = spec
        self.rec.toggle(src.split()[0], max_s) if max_s else self.rec.toggle(src.split()[0])
        return "A gravar"

    def mission(self, sid):
        self.missions.done(sid)

    def go(self, name):
        if self.music_menu.active:
            self.music_menu.close()
        if self.cur:
            self.cur.leave()
        self.cur_name = name
        self.cur = self.sections[name]
        if name in QUIET and "forge" in self.sections:
            self.sections["forge"].stop()
            self.sections["decks"].stop_all()
            self.sections["vox"].stop()
        self.cur.enter()
        self.help.maybe_tutorial(name)

    # ---- main loop pieces
    def handle(self):
        inp = self.input
        inp.poll()
        if inp.quit:
            self.running = False
        for kind, b in inp.events:
            if kind == "press" and ((b == "start" and inp.down("select")) or (b == "select" and inp.down("start"))):
                self.running = False
                return
            if self.help.tutorial:                   # first-visit card: any button closes it
                if kind == "press":
                    self.help.dismiss()
                continue
            if self.music_menu.active:
                self.music_menu.on(kind, b)
                continue
            if b == "start" and self.cur_name in MUSIC_HUB:
                if kind == "press":
                    self.st_t0, self.st_menu = time.time(), False
                elif kind == "release":
                    if self.st_t0 is not None and not self.st_menu:
                        self.start_tap()
                    self.st_t0 = None
                continue
            if b == "select" and kind == "press":
                self.sel_combo = False
                self.sel_t0 = time.time()
                self.help_shown = False
                continue
            if b == "select" and kind == "release":
                if self.help_shown:                  # SELECT was held to read the help: do nothing else
                    self.help_shown = False
                    continue
                if not self.sel_combo and hasattr(self.cur, "on_select"):
                    self.cur.on_select()
                elif not self.sel_combo and self.cur_name not in ("intro", "bridge"):
                    self.ui_move()
                    self.go("bridge")
                continue
            if inp.down("select") and kind in ("press", "repeat"):
                self.sel_combo = True
                if hasattr(self.cur, "combo") and self.cur.combo(b):
                    continue
                continue
            self.cur.on(kind, b)

    def frame(self, dt):
        self.t += dt
        self.mixer.pump()
        self.sections["forge"].tick()
        self.rec.flush()
        if self.cur_name != "pet":
            self.sections["pet"].bg(dt)
        self.cur.update(dt)
        self.cur.draw(self.g, self.t, dt)
        if self.st_t0 is not None and not self.st_menu and time.time() - self.st_t0 > 0.4:
            self.st_menu, self.st_t0 = True, None
            self.music_menu.open()
        if self.music_menu.active:
            self.music_menu.draw(self.g, self.t)
        msg, t0 = self.missions.toast
        if msg and time.time() - t0 < 3.0:
            ui.notice(self.g, msg, C["green"])
        if self.input.down("select") and time.time() - self.sel_t0 > 0.35 and not self.help.tutorial:
            self.help_shown = True
            self.help.draw_overlay(self.g)
        elif not self.input.down("select"):
            self.help.tip.clear()
        if self.help.tutorial:
            self.help.draw_tutorial(self.g, self.t)
        if self.cfg["scanlines"]:
            self.g.scanlines()

    def run(self):
        try:
            self.loop()
        finally:
            self.shutdown()

    def loop(self):
        # frame timing on a monotonic clock: the R36S has no clock battery and sets the time when the network comes
        # up; a jump of the system time must never stall the loop (SDL_Delay of hours) or run time backwards
        last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            dt = min(0.1, now - last)
            last = now
            self.handle()
            if not self.running:
                break
            if self.input.fs_toggle:              # F11 on a computer: full screen on/off
                self.input.fs_toggle = False
                self.fullscreen = not self.fullscreen
                sdl2.SDL_SetWindowFullscreen(self.win, sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP if self.fullscreen else 0)
            self.frame(dt)
            sdl2.SDL_RenderPresent(self.ren)
            spent = time.perf_counter() - now
            if spent < 1 / 30.0:
                sdl2.SDL_Delay(int((1 / 30.0 - spent) * 1000))

    def shutdown(self):
        """saves everything and stops the recorders, also when the loop ended with an error (an ABDUCTOR arecord
        left running would fill the card); each step on its own, so one that fails never skips the others"""
        ab = self.sections["abductor"]
        for step in (lambda: self.save_cfg(sync=True), self.rec.stop, self.sections["forge"].save,
                     self.sections["vox"].stop, self.sections["pet"].save, lambda: ab.proc and ab.proc.terminate(),
                     self.mixer.close, sdl2.SDL_Quit):
            try:
                step()
            except Exception as e:
                log("shutdown: %r" % (e,))
