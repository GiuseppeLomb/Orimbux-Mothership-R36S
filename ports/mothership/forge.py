# BEAT FORGE - drum machine with 3 modes (L2):
#   GRELHA     8 tracks x 8..32 steps, 8 patterns (A-H): velocity / ratchet / chance per step, swing,
#              per-track sound (kit or YOUR wavs) / pitch / pan / volume / mute / solo, undo/redo
#   CONSTRUTOR ready-made beats by style (FL-style quick building): pick a style, swap each track's variation
#   ARRANJO    patterns in a row = a song (like FL's playlist); export it as a song for Beat Duel / Twin Decks
# Locked to the ship's beat grid, keeps playing under the other music sections.
import glob
import json
import math
import os
import random
import threading
import time
import wave

import engine
from engine import C, W, SR, BUF, audioop, Voice
import forge_styles
import ui

D = os.path.join(engine.ASSETS, "forge")
SAVE = os.path.join(engine.APP, "forge.json")
EXPORT_DIR = os.path.join(engine.APP, "forge")
USER_DIR = os.path.join(engine.APP, "samples")
REC_DIR = os.path.join(engine.APP, "recordings")
CHOP_DIR = os.path.join(engine.APP, "chop")
MAXS, NPAT = 32, 8
LENGTHS = [8, 12, 16, 24, 32]
PAT_NAMES = "ABCDEFGH"
VEL_GAIN = [0.0, 0.42, 0.8, 1.15]
VEL_NAME = ["-", "SUAVE", "NORMAL", "ACENTO"]
CHANCES = [100, 75, 50, 25]
TRACK_COL = {"kick": C["orange"], "snare": C["cyan"], "snap": C["violet"], "hat": C["green"],
             "open": (120, 220, 255), "tom": (255, 110, 170), "perc": (255, 236, 140), "fx": (200, 160, 255)}
DEFAULT_VOL = {"kick": 9, "snare": 8, "snap": 7, "hat": 5, "open": 5, "tom": 7, "perc": 6, "fx": 6}
LANE_BTN = {"kick": "left", "snare": "right", "snap": "right", "open": "down", "tom": "up", "perc": "up",
            "fx": "down"}            # hats are left out of Beat Duel charts on purpose (too dense)
LANE_NUM = {"left": 0, "down": 1, "up": 2, "right": 3}
MODES = [("grid", "GRELHA"), ("build", "CONSTRUTOR"), ("song", "ARRANJO")]
SONG_MAX = 64


def new_pattern(nt, length=16):
    return {"len": length, "t": [[[0, 1, 100] for _ in range(MAXS)] for _ in range(nt)]}


def demo_patterns(ids):
    pats = [new_pattern(len(ids)) for _ in range(NPAT)]

    def put(p, tid, steps, vel=2, rat=1):
        if tid in ids:
            for s in steps:
                pats[p]["t"][ids.index(tid)][s] = [vel, rat, 100]

    put(0, "kick", [0, 4, 8, 12])                       # A: house
    put(0, "snap", [4, 12])
    put(0, "hat", [2, 6, 10, 14])
    put(0, "hat", [1, 3, 5, 7, 9, 11, 13, 15], 1)
    put(0, "open", [14], 1)
    put(1, "kick", [0, 10])                             # B: breakbeat
    put(1, "kick", [3], 1)
    put(1, "snare", [4, 12], 3)
    put(1, "snare", [7, 15], 1)
    put(1, "hat", [0, 2, 4, 6, 8, 10, 12, 14])
    put(1, "hat", [13], 1)
    put(2, "kick", [0, 7, 10])                          # C: half-time with rolls
    put(2, "snare", [8], 3)
    put(2, "hat", [0, 2, 4, 6, 8, 10, 12])
    put(2, "hat", [14], 2, 3)
    put(2, "hat", [15], 1, 2)
    put(2, "perc", [11], 1)
    return pats


def clean_step(s):
    """[velocity 0-3, ratchet 1-4, chance 1-100] from a saved file; a damaged step becomes an empty one"""
    if type(s) is list and len(s) == 3 and type(s[0]) is int and type(s[1]) is int and type(s[2]) is int \
            and 0 <= s[0] <= 3 and 1 <= s[1] <= 4 and 1 <= s[2] <= 100:
        return list(s)                           # the usual case: a valid step, checked cheaply
    if isinstance(s, list) and len(s) in (2, 3):
        v = [engine.num(x, None) for x in s] + [100] * (3 - len(s))
        if None not in v:
            return [int(min(3, max(0, v[0]))), int(min(4, max(1, v[1]))), int(min(100, max(1, v[2])))]
    return [0, 1, 100]


def clean_pattern(p):
    rows = [r if isinstance(r, list) else [] for r in p["t"]]
    return {"len": int(engine.num(p.get("len"), 16, 1, MAXS)),
            "t": [[clean_step(s) for s in r[:MAXS]] + [[0, 1, 100] for _ in range(MAXS - len(r))] for r in rows]}


def write_wav(path, data):
    wf = wave.open(path, "wb")
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(data)
    wf.close()


class Forge(object):
    name = "BEAT FORGE"

    def __init__(self, app):
        self.app = app
        self.kit = json.load(open(os.path.join(D, "kit.json")))["tracks"]
        self.ids = [t["id"] for t in self.kit]
        self.user = []
        self.raw = {}
        self.cache = {}
        self.undo_stack, self.redo_stack = [], []
        self.last_op = (None, 0.0)
        self.load()
        self.mode = "grid"
        self.edit = 0          # pattern on screen
        self.cur = 0           # pattern playing
        self.queued = None
        self.row = 0
        self.col = 0
        self.solo = None
        self.playing = False
        self.next_step = 0
        self.pos = 0           # step inside the playing pattern
        self.fresh = True
        self.song_idx = 0
        self.scol = 0          # cursor in the arrangement
        self.hist = {}         # global step -> (pattern, pos)
        self.logged = set()
        self.dirty = 0.0
        self.msg = ("", 0.0)
        self.confirm = (None, 0.0)
        self.exporting = None

    # ---------------------------------------------------------------- persistence
    def load(self):
        nt = len(self.kit)
        st = engine.load_save(SAVE) or {}
        tracks = st.get("tracks") if isinstance(st.get("tracks"), list) else []
        self.tracks = []
        for i, t in enumerate(self.kit):
            d = tracks[i] if i < len(tracks) and isinstance(tracks[i], dict) else {}
            s = d.get("s", t["samples"][0]["file"])
            if isinstance(s, int) and not isinstance(s, bool):      # v1 saved an index
                s = t["samples"][min(s, len(t["samples"]) - 1)]["file"]
            if not isinstance(s, str):
                s = t["samples"][0]["file"]
            self.tracks.append({"s": s, "vol": int(engine.num(d.get("vol"), DEFAULT_VOL.get(t["id"], 7), 0, 10)),
                                "pitch": int(engine.num(d.get("pitch"), 0, -12, 12)),
                                "pan": int(engine.num(d.get("pan"), 0, -2, 2)), "mute": bool(d.get("mute", False))})
        pats = st.get("pats")
        if isinstance(pats, list) and pats and isinstance(pats[0], list):     # v1: 16-step lists
            conv = []
            for p in pats:
                np_ = new_pattern(nt)
                p = p if isinstance(p, list) else []
                for ti in range(min(nt, len(p))):
                    row = p[ti] if isinstance(p[ti], list) else []
                    for si in range(min(16, len(row))):
                        np_["t"][ti][si] = clean_step(row[si])
                conv.append(np_)
            pats = conv
        if not isinstance(pats, list) or len(pats) != NPAT or not all(
                isinstance(p, dict) and isinstance(p.get("t"), list) and len(p["t"]) == nt for p in pats):
            pats = demo_patterns(self.ids)
        self.pats = [clean_pattern(p) for p in pats]
        self.swing = int(engine.num(st.get("swing"), 50))
        song = st.get("song") if isinstance(st.get("song"), list) else []
        self.song = [int(x) % NPAT for x in song if engine.num(x, None) is not None][:SONG_MAX]
        self.song_on = bool(st.get("song_on", st.get("chain", False)))
        self.style = int(engine.num(st.get("style"), 0)) % len(forge_styles.STYLES)
        v = st.get("vars")
        self.vars = dict((k, int(n)) for k, n in v.items() if engine.num(n, None) is not None) \
            if isinstance(v, dict) else {}
        if st.get("v") == 2:                     # what had to be corrected: keep a copy of the file first
            state = self.state()
            engine.check_save(SAVE, dict((k, st[k]) for k in st if k in state), state)
        elif st:                                 # an older (or unknown) format is converted: keep the original
            engine.keep_bad(SAVE, move=False)

    def state(self):
        return {"v": 2, "tracks": self.tracks, "pats": self.pats, "swing": self.swing, "song": self.song,
                "song_on": self.song_on, "style": self.style, "vars": self.vars}

    def save(self, sync=True):
        try:
            engine.write_json(SAVE, self.state(), sync, separators=(",", ":"))
        except Exception:
            pass
        self.dirty = 0.0

    def touch(self):
        self.dirty = time.time()

    # ---------------------------------------------------------------- undo / redo
    def change(self, op=None):
        """call BEFORE a modification; repeated presses of the same control within 0.8 s are one undo step"""
        now = time.time()
        if op is None or op != self.last_op[0] or now - self.last_op[1] > 0.8:
            self.undo_stack.append(json.dumps([self.pats, self.tracks, self.song, self.swing]))
            self.undo_stack = self.undo_stack[-40:]
            self.redo_stack = []
        self.last_op = (op, now)
        self.touch()

    def _restore(self, snap):
        self.pats, self.tracks, self.song, self.swing = json.loads(snap)
        self.cache.clear()
        self.touch()

    def undo(self):
        if not self.undo_stack:
            self.say("Nada para desfazer.")
            return
        self.redo_stack.append(json.dumps([self.pats, self.tracks, self.song, self.swing]))
        self._restore(self.undo_stack.pop())
        self.last_op = (None, 0.0)
        self.say("Desfeito (%d)" % len(self.undo_stack))

    def redo(self):
        if not self.redo_stack:
            self.say("Nada para refazer.")
            return
        self.undo_stack.append(json.dumps([self.pats, self.tracks, self.song, self.swing]))
        self._restore(self.redo_stack.pop())
        self.last_op = (None, 0.0)
        self.say("Refeito")

    # ---------------------------------------------------------------- samples (kit + yours)
    def scan_user(self):
        out = []
        for pattern in (os.path.join(USER_DIR, "*.wav"), os.path.join(CHOP_DIR, "slice_*.wav"),
                        os.path.join(REC_DIR, "rec_*.wav")):
            for p in sorted(glob.glob(pattern)):
                base = os.path.splitext(os.path.basename(p))[0]
                label = base.replace("slice_", "FATIA ").replace("rec_", "REC ").upper()
                out.append({"file": "user:" + p, "label": label[:10]})
        self.user = out[:60]

    def choices(self, ti):
        return self.kit[ti]["samples"] + self.user

    def sample_label(self, ti):
        f = self.tracks[ti]["s"]
        for s in self.choices(ti):
            if s["file"] == f:
                return s["label"]
        return os.path.basename(f)[:10].upper()

    def mono(self, f):
        d = self.raw.get(f)
        if d is not None:
            return d
        try:
            if f.startswith("user:"):
                d = audioop.tomono(engine.load_wav(f[5:]), 2, 0.5, 0.5)[:SR * 2 * 4]   # max 4 s
            else:
                wf = wave.open(os.path.join(D, f + ".wav"), "rb")
                d = wf.readframes(wf.getnframes())
                wf.close()
        except Exception:
            d = b"\0\0" * 400
        if len(self.raw) > 40:
            self.raw.clear()
        self.raw[f] = d
        return d

    def sample(self, ti):
        tr = self.tracks[ti]
        key = (tr["s"], tr["pitch"], tr["pan"])
        d = self.cache.get(key)
        if d is None:
            mono = self.mono(tr["s"])
            if tr["pitch"]:
                ratio = 2 ** (tr["pitch"] / 12.0)
                mono = audioop.ratecv(mono, 2, 1, int(SR * ratio), SR, None)[0]
            pan = tr["pan"] / 2.0
            d = audioop.tostereo(mono, 2, 1.0 if pan <= 0 else 1.0 - pan, 1.0 if pan >= 0 else 1.0 + pan)
            if len(self.cache) > 48:
                self.cache.clear()
            self.cache[key] = d
        return d

    def gain(self, ti, vel):
        return VEL_GAIN[vel] * self.tracks[ti]["vol"] / 8.0

    def preview(self, ti, vel=2):
        self.app.mixer.shot("fprev%d" % ti, self.sample(ti), group="forge", gain=self.gain(ti, vel))

    # ---------------------------------------------------------------- transport (runs every frame, any section)
    def pattern_empty(self, p):
        pt = self.pats[p]
        return not any(s[0] for tr in pt["t"] for s in tr[:pt["len"]])

    def step_frame(self, n):
        m = self.app.mixer
        f = m.frame_of_beat(n / 4.0)
        if n % 2:
            f += int((2 * self.swing / 100.0 - 1.0) * m.beat_frames() / 4.0)
        return f

    def reactor_busy(self):
        m = self.app.mixer
        return any(v.group == "reactor" and v.loop and not v.done for v in m.voices)

    def song_list(self):
        if self.song:
            return self.song
        return [p for p in range(NPAT) if not self.pattern_empty(p)] or [self.edit]

    def play(self):
        if hasattr(self.app, "mission"):
            self.app.mission("forge_play")
        m = self.app.mixer
        with m.lock:
            start = m.clock + int(0.06 * SR)
            if not self.reactor_busy():
                b0 = math.ceil(m.beat_at(start) / 4.0) * 4.0     # nothing else running: "now" becomes a bar line
                m.anchor_clock, m.anchor_beat = start, b0
                nb = b0
            else:
                nb = math.ceil(m.beat_at(start) / 4.0 - 1e-6) * 4.0
            self.next_step = int(round(nb * 4))
        if self.song_on:
            sl = self.song_list()
            self.song_idx = min(self.scol, len(sl) - 1) if self.mode == "song" and self.song else 0
            self.cur = sl[self.song_idx]
        else:
            self.cur = self.edit
        self.pos = 0
        self.fresh = True
        self.queued = None
        self.hist = {}
        self.playing = True

    def stop(self):
        if not self.playing:
            return
        self.playing = False
        m = self.app.mixer
        with m.lock:
            m.voices = [v for v in m.voices if not (v.group == "forge" and v.start > m.clock)]
        self.queued = None

    def tick(self):
        if self.dirty and time.time() - self.dirty > 2.0:
            self.save(sync=False)
        if not self.playing:
            return
        m = self.app.mixer
        horizon = m.clock + int(0.1 * SR) + BUF
        guard = 0
        while guard < 64:
            f = self.step_frame(self.next_step)
            if f >= horizon:
                break
            # after a stall (loading, slow frame) skip what is already late instead of firing a burst
            self.play_step(self.next_step, max(f, m.clock), f >= m.clock - int(0.03 * SR))
            self.next_step += 1
            guard += 1

    def boundary(self):
        """start of a pattern: queued pattern, or the next block of the song"""
        if self.fresh:
            self.fresh = False
            return
        if self.queued is not None:
            self.cur, self.queued = self.queued, None
        elif self.song_on:
            sl = self.song_list()
            self.song_idx = (self.song_idx + 1) % len(sl)
            self.cur = sl[self.song_idx]

    def play_step(self, n, f, sound=True):
        m = self.app.mixer
        if self.pos == 0:
            self.boundary()
        pt = self.pats[self.cur]
        pos = self.pos
        self.hist[n] = (self.cur, pos, self.song_idx)
        if len(self.hist) > 80:
            for k in [k for k in self.hist if k < n - 40]:
                del self.hist[k]
        self.pos = (pos + 1) % max(1, pt["len"])
        if not sound:
            return
        six = m.beat_frames() / 4.0
        rec = self.app.rec.active()
        new = []
        for ti, tr in enumerate(self.tracks):
            vel, rat, ch = pt["t"][ti][pos]
            if not vel or tr["mute"] or (self.solo is not None and ti != self.solo):
                continue
            if ch < 100 and random.random() * 100 >= ch:
                continue
            tid = self.ids[ti]
            data = self.sample(ti)
            g = self.gain(ti, vel)
            for r in range(rat):
                new.append(Voice("f%d" % ti, "forge", data, None, False, g * (1.0 - 0.12 * r), f + int(r * six / rat)))
            if tid == "hat":
                self.choke_open(f)
            if rec and vel >= 2 and tid in LANE_BTN and (n, LANE_BTN[tid]) not in self.logged:
                self.logged.add((n, LANE_BTN[tid]))
                self.app.rec.event(f, LANE_BTN[tid])
        if new:
            with m.lock:
                m.voices.extend(new)

    def choke_open(self, f):
        key = "f%d" % self.ids.index("open") if "open" in self.ids else None
        m = self.app.mixer
        with m.lock:
            for v in m.voices:
                if v.key == key and v.start < f and v.stop is None:
                    v.stop = f

    def audible(self):
        """(pattern, step, song index) currently heard"""
        m = self.app.mixer
        n = int(math.floor(m.play_beat() * 4))
        return self.hist.get(n, (None, None, None))

    # ---------------------------------------------------------------- rendering (export)
    def render_pattern(self, p, tail=True, wrap=False):
        """stereo bytes of pattern p at the current BPM/swing; tail = keep ringing samples after the end"""
        m = self.app.mixer
        six = m.beat_frames() / 4.0
        pt = self.pats[p]
        frames = int(round(pt["len"] * six))
        total = frames + (int(SR * 2.5) if tail and not wrap else 0)
        buf = bytearray(total * 4)
        hits = []
        for ti, tr in enumerate(self.tracks):
            if tr["mute"] or (self.solo is not None and ti != self.solo):
                continue
            data = None
            for pos in range(pt["len"]):
                vel, rat, ch = pt["t"][ti][pos]
                if not vel:
                    continue
                if data is None:
                    data = self.sample(ti)
                f0 = int(round(pos * six + ((2 * self.swing / 100.0 - 1.0) * six if pos % 2 else 0)))
                tid = self.ids[ti]
                if vel >= 2 and tid in LANE_BTN:
                    hits.append((f0, LANE_NUM[LANE_BTN[tid]]))
                for r in range(rat):
                    g = self.gain(ti, vel) * (1.0 - 0.12 * r) * engine.HEADROOM
                    self.mix_into(buf, total, audioop.mul(data, 2, g), f0 + int(r * six / rat), wrap)
        return bytes(buf), frames, hits

    @staticmethod
    def mix_into(buf, frames, data, off, wrap=True):
        pos = 0
        n = len(data) // 4
        off %= frames
        while pos < n:
            take = min(n - pos, frames - off)
            a, b = off * 4, (off + take) * 4
            buf[a:b] = audioop.add(bytes(buf[a:b]), data[pos * 4:(pos + take) * 4], 2)
            pos += take
            if not wrap:
                break
            off = 0          # loops: the tail wraps to the start so the loop is seamless

    def export(self, p):
        """pattern -> seamless loop in the Loop Reactor's FORGE bank"""
        data, frames, _ = self.render_pattern(p, wrap=True)
        if not os.path.isdir(EXPORT_DIR):
            os.makedirs(EXPORT_DIR)
        path = os.path.join(EXPORT_DIR, "forge_%s.wav" % PAT_NAMES[p])
        write_wav(path, data)
        self.app.bank.set_forge_pad(p, path, self.pats[p]["len"] / 4.0)
        return path

    def export_song(self):
        """the arrangement -> recordings/session_*_forge.wav + chart: playable in Beat Duel and Twin Decks"""
        sl = self.song_list()
        self.exporting = "A exportar musica..."
        threading.Thread(target=self._export_song, args=(list(sl),), daemon=True).start()

    def _export_song(self, sl):
        try:
            rendered = {}
            for p in set(sl):
                rendered[p] = self.render_pattern(p, tail=True)
            total = sum(rendered[p][1] for p in sl) + int(SR * 2.5)
            total = min(total, SR * 60 * 6)
            out = bytearray(total * 4)
            off, notes = 0, []
            for p in sl:
                data, frames, hits = rendered[p]
                if off >= total:
                    break
                n = min(len(data) // 4, total - off)
                a, b = off * 4, (off + n) * 4
                out[a:b] = audioop.add(bytes(out[a:b]), data[:n * 4], 2)
                notes += [[round((off + f) / float(SR), 3), lane] for f, lane in hits]
                off += frames
            # normalise gently (patterns are rendered with headroom)
            peak = audioop.max(bytes(out), 2) or 1
            out = audioop.mul(bytes(out), 2, min(2.0, 29000.0 / peak))
            if not os.path.isdir(REC_DIR):
                os.makedirs(REC_DIR)
            base = os.path.join(REC_DIR, time.strftime("session_%Y%m%d_%H%M%S_forge"))
            write_wav(base + ".wav", out)
            notes = sorted(set((t, l) for t, l in notes))
            notes = [list(x) for x in notes]
            easy, last = [], -9.0
            for t, lane in notes:
                if t - last >= 0.4:
                    easy.append([t, lane])
                    last = t
            meta = {"id": os.path.basename(base), "title": time.strftime("FORGE SONG %d/%m %H:%M"),
                    "artist": "TU", "bpm": round(self.app.mixer.bpm, 1), "duration": round(total / float(SR), 2),
                    "file": os.path.basename(base) + ".wav", "charts": {"easy": easy, "normal": notes, "hard": notes}}
            engine.write_json(base + ".json", meta)
            self.say("Música exportada: Beat Duel e Twin Decks (%d:%02d)" % (total // SR // 60, total // SR % 60))
            self.last_song = base
        except Exception as e:
            self.say("Erro a exportar: %s" % e)
        self.exporting = None

    # ---------------------------------------------------------------- construtor
    def apply_style(self, si=None):
        st = forge_styles.STYLES[self.style if si is None else si]
        self.change("style")
        self.style = forge_styles.STYLES.index(st)
        self.vars = {}
        for ti, tid in enumerate(self.ids):
            if tid in st["sounds"]:
                self.tracks[ti]["s"] = st["sounds"][tid]
                self.tracks[ti]["pitch"] = 0
        self.cache.clear()
        self.swing = st["swing"]
        self.app.set_bpm(st["bpm"])
        self.write_vars()

    def write_vars(self):
        st = forge_styles.STYLES[self.style]
        pt = self.pats[self.edit]
        pt["len"] = 16
        for ti, tid in enumerate(self.ids):
            vs = st["vars"].get(tid, ["." * 16])
            v = self.vars.get(tid, 0) % len(vs)
            steps = forge_styles.decode(vs[v])
            pt["t"][ti] = steps + [[0, 1, 100] for _ in range(MAXS - len(steps))]

    def var_step(self, ti, d):
        st = forge_styles.STYLES[self.style]
        tid = self.ids[ti]
        n = len(st["vars"].get(tid, ["."]))
        self.change("var%d" % ti)
        self.vars[tid] = (self.vars.get(tid, 0) + d) % n
        self.write_vars()

    def dice(self):
        st = forge_styles.STYLES[self.style]
        self.change()
        for tid in self.ids:
            self.vars[tid] = random.randrange(len(st["vars"].get(tid, ["."])))
        self.write_vars()

    # ---------------------------------------------------------------- section interface
    def enter(self):
        self.scan_user()

    def leave(self):
        if self.dirty:
            self.save()

    def say(self, s):
        self.msg = (s, time.time())

    def ask(self, what, text):
        """two presses within 2 s to confirm a destructive action"""
        if self.confirm[0] == what and time.time() - self.confirm[1] < 2.0:
            self.confirm = (None, 0.0)
            return True
        self.confirm = (what, time.time())
        self.say(text)
        return False

    def select_pattern(self, p):
        self.edit = p % NPAT
        self.col = min(self.col, self.pats[self.edit]["len"] - 1)
        if self.playing:
            if not self.song_on:
                self.queued = self.edit if self.edit != self.cur else None
        else:
            self.cur = self.edit
        self.app.ui_move()

    def set_mode(self, d):
        keys = [k for k, _ in MODES]
        self.mode = keys[(keys.index(self.mode) + d) % len(keys)]
        self.app.ui_move()
        self.app.help.maybe_tutorial("forge")

    def combo(self, b):
        app = self.app
        if b in ("up", "down"):
            app.set_bpm(app.mixer.bpm + (1 if b == "up" else -1))
        elif b in ("left", "right"):
            self.change("swing")
            self.swing = max(50, min(75, self.swing + (1 if b == "right" else -1)))
        elif b == "a":
            app.rec.toggle("FORGE")
            self.logged = set()
        elif b == "l2":
            self.undo()
        elif b == "r2":
            self.redo()
        elif b == "x":
            if self.mode == "song":
                if self.exporting:
                    return True
                self.export_song()
            elif self.pattern_empty(self.edit):
                self.say("O padrão %s está vazio." % PAT_NAMES[self.edit])
            else:
                self.export(self.edit)
                self.say("Padrão %s enviado para o Loop Reactor (banco FORGE)" % PAT_NAMES[self.edit])
                app.ui_ok()
        elif b == "y":
            dst = (self.edit + 1) % NPAT
            if self.pattern_empty(dst) or self.ask(("copy", dst), "SELECT+Y outra vez para substituir %s"
                                                                  % PAT_NAMES[dst]):
                self.change()
                self.pats[dst] = json.loads(json.dumps(self.pats[self.edit]))
                self.select_pattern(dst)
                self.say("Copiado para %s" % PAT_NAMES[dst])
        elif b == "b":
            self.song_on = not self.song_on
            self.queued = None
            self.touch()
            self.say("Modo música %s" % (("ligado: toca o ARRANJO" if self.song else "ligado: toca A... até ao último padrão")
                                  if self.song_on else "DESLIGADO"))
        elif b == "l1":
            if self.ask(("clear", self.edit), "SELECT+L1 outra vez para APAGAR o padrao %s" % PAT_NAMES[self.edit]):
                self.change()
                self.pats[self.edit] = new_pattern(len(self.kit), self.pats[self.edit]["len"])
                self.say("Padrão %s apagado (SELECT+L2 desfaz)" % PAT_NAMES[self.edit])
        elif b == "r1":
            st = self.pats[self.edit]["t"][self.row][self.col]
            self.change("chance")
            st[2] = CHANCES[(CHANCES.index(st[2]) + 1) % len(CHANCES)] if st[2] in CHANCES else 100
            if not st[0]:
                st[0] = 2
        else:
            return False
        return True

    def on(self, kind, b):
        if kind not in ("press", "repeat"):
            return
        if b == "l2" and kind == "press" and not self.app.input.down("r2"):
            self.set_mode(1)
            return
        if b == "b" and kind == "press" and not self.app.input.down("r2"):
            if self.playing:
                self.stop()
            else:
                self.play()
            return
        if self.mode == "grid":
            self.on_grid(kind, b)
        elif self.mode == "build":
            self.on_build(kind, b)
        else:
            self.on_song(kind, b)

    def on_grid(self, kind, b):
        inp = self.app.input
        ti = self.row
        tr = self.tracks[ti]
        pt = self.pats[self.edit]
        st = pt["t"][self.row][self.col]
        if inp.down("r2"):                       # track page
            if b in ("left", "right"):
                ch = self.choices(ti)
                files = [c["file"] for c in ch]
                i = files.index(tr["s"]) if tr["s"] in files else 0
                self.change("snd%d" % ti)
                tr["s"] = files[(i + (1 if b == "right" else -1)) % len(files)]
                self.preview(ti)
            elif b in ("up", "down"):
                self.change("pitch%d" % ti)
                tr["pitch"] = max(-12, min(12, tr["pitch"] + (1 if b == "up" else -1)))
                self.preview(ti)
            elif b in ("x", "y"):
                self.change("vol%d" % ti)
                tr["vol"] = max(0, min(10, tr["vol"] + (1 if b == "y" else -1)))
                self.preview(ti)
            elif b == "a" and kind == "press":
                self.change()
                tr["pan"] = {0: 1, 1: 2, 2: -2, -2: -1, -1: 0}[tr["pan"]]
                self.preview(ti)
            elif b == "b" and kind == "press":
                self.change()
                tr["mute"] = not tr["mute"]
            elif b == "l2" and kind == "press":
                self.solo = None if self.solo == ti else ti
            elif b in ("l1", "r1") and kind == "press":
                i = LENGTHS.index(pt["len"]) if pt["len"] in LENGTHS else 2
                self.change()
                pt["len"] = LENGTHS[max(0, min(len(LENGTHS) - 1, i + (1 if b == "r1" else -1)))]
                self.col = min(self.col, pt["len"] - 1)
                self.say("Padrão %s: %d passos" % (PAT_NAMES[self.edit], pt["len"]))
            return
        if b in ("up", "down"):
            self.row = (self.row + (1 if b == "down" else -1)) % len(self.kit)
        elif b in ("left", "right"):
            self.col = (self.col + (1 if b == "right" else -1)) % pt["len"]
        elif kind != "press":
            return
        elif b == "a":
            self.change()
            st[0] = 0 if st[0] else 2
            if not st[0]:
                st[1], st[2] = 1, 100
            elif not self.playing:
                self.preview(ti, st[0])
        elif b == "x":
            self.change("vel")
            st[0] = 1 if st[0] in (0, 3) else st[0] + 1
            if not self.playing:
                self.preview(ti, st[0])
        elif b == "y":
            self.change("rat")
            st[1] = st[1] % 4 + 1
            if not st[0]:
                st[0] = 2
        elif b == "l1":
            self.select_pattern(self.edit - 1)
        elif b == "r1":
            self.select_pattern(self.edit + 1)

    def on_build(self, kind, b):
        if b in ("up", "down"):
            self.row = (self.row + (1 if b == "down" else -1)) % len(self.kit)
        elif kind != "press":
            return
        elif b in ("left", "right"):
            self.style = (self.style + (1 if b == "right" else -1)) % len(forge_styles.STYLES)
            self.apply_style()
            self.say("%s - %d BPM" % (forge_styles.STYLES[self.style]["name"], forge_styles.STYLES[self.style]["bpm"]))
        elif b in ("a", "y"):
            self.var_step(self.row, 1 if b == "a" else -1)
            if not self.playing:
                self.preview(self.row)
        elif b == "x":
            self.dice()
        elif b == "l1":
            self.select_pattern(self.edit - 1)
        elif b == "r1":
            self.select_pattern(self.edit + 1)

    def on_song(self, kind, b):
        song = self.song
        if b in ("left", "right"):
            if song:
                self.scol = max(0, min(len(song) - 1, self.scol + (1 if b == "right" else -1)))
        elif b in ("up", "down"):
            if not song:
                self.change()
                song.append(self.edit)
                self.scol = 0
            else:
                self.change("blk")
                song[self.scol] = (song[self.scol] + (1 if b == "up" else -1)) % NPAT
        elif kind != "press":
            return
        elif b == "a":
            if len(song) >= SONG_MAX:
                self.say("Máximo de %d blocos." % SONG_MAX)
                return
            self.change()
            if song:
                song.insert(self.scol + 1, song[self.scol])
                self.scol += 1
            else:
                song.append(self.edit)
        elif b == "y":
            if song:
                self.change()
                del song[self.scol]
                self.scol = max(0, min(self.scol, len(song) - 1))
        elif b == "x":
            self.song_on = not self.song_on
            self.queued = None
            self.touch()
            self.say("Modo música %s" % ("ligado" if self.song_on else "desligado"))
        elif b in ("l1", "r1"):
            self.select_pattern(self.edit + (1 if b == "r1" else -1))

    def update(self, dt):
        pass

    # ---------------------------------------------------------------- drawing
    def draw(self, g, t, dt):
        import app as appmod
        app = self.app
        g.clear(C["void"])
        appmod.header(g, app, "BEAT FORGE", "forge")
        blink = int(t * 4) % 2 == 0 or not app.cfg["anim"]
        aud = self.audible() if self.playing else (None, None, None)
        self.draw_top(g, aud, blink)
        if self.mode == "grid":
            self.draw_grid(g, aud, blink)
            items = [("A", "liga passo", 0), ("B", "tocar", 0), ("L1/R1", "padrão", 0), ("L2", "modo", 0)]
        elif self.mode == "build":
            self.draw_build(g, aud, blink)
            items = [("esq/dir", "estilo", 0), ("A", "variação", 0), ("X", "dado", 0), ("B", "tocar", 0)]
        else:
            self.draw_song(g, aud, blink)
            items = [("A", "inserir bloco", 0), ("Y", "apagar", 0), ("X", "modo música", 0), ("SEL+X", "exportar", 0)]
        appmod.footer(g, items)
        s, t0 = self.msg
        if self.exporting:
            s, t0 = self.exporting, time.time()
        if s and time.time() - t0 < 2.5:
            import ui
            ui.toast(g, s, app.accent, 200)

    def draw_top(self, g, aud, blink):
        app = self.app
        aud_p = aud[0]
        for p in range(NPAT):
            x, y = 12 + p * 30, 58
            empty = self.pattern_empty(p)
            playing = self.playing and p == aud_p
            col = app.accent if p == self.edit else (C["hullhi"] if not empty else C["hull"])
            if playing:
                g.rect(x, y, 27, 26, C["green"] if p != self.edit else app.accent)
            elif self.queued == p and blink:
                g.rect(x, y, 27, 26, C["hullhi"])
            else:
                g.rect(x, y, 27, 26, C["panel"])
            g.frame(x, y, 27, 26, col, 2)
            g.text("p8", PAT_NAMES[p], x + 14, y + 9, C["void"] if playing else (C["text"] if not empty else C["dim"]),
                   255, "center")
        x0 = 12 + NPAT * 30 + 8
        # mode tabs
        x = x0
        for k, label in MODES:
            w = g.tw("p8", label) + 10
            on = k == self.mode
            g.rect(x, 58, w, 14, app.accent if on else C["hull"])
            g.text("p8", label, x + 5, 61, C["void"] if on else C["muted"])
            x += w + 3
        g.text("v20", "%d BPM  ·  swing %d%%  ·  %s" % (round(app.mixer.bpm), self.swing,
                                                 "música" if self.song_on else "repetir"), x0, 72,
               C["soft"])
        g.text("p8", "▶ A TOCAR" if self.playing else "■ PARADO", W - 14, 78, C["green"] if self.playing else C["dim"], 255,
               "right")

    def draw_grid(self, g, aud, blink):
        """batched: one draw call per colour instead of one per cell (matters on the console CPU)"""
        app = self.app
        aud_p, aud_s = aud[0], aud[1]
        pt = self.pats[self.edit]
        page = self.col // 16
        gx, gy, cw, ch, rh = 112, 98, 28, 30, 34
        off_beat, off_rest, white, dots, frames, out_len = [], [], [], [], [], []
        on = {}
        for ti, tk in enumerate(self.kit):
            tr = self.tracks[ti]
            y = gy + ti * rh
            tcol = TRACK_COL.get(tk["id"], C["cyan"])
            muted = tr["mute"] or (self.solo is not None and self.solo != ti)
            if ti == self.row:
                g.rect(8, y - 2, W - 16, rh, C["deck"])
            strip = (255, 70, 90) if tr["mute"] else (C["green"] if self.solo == ti else (tcol if not muted else C["hull"]))
            g.rect(12, y, 5, ch, strip)
            g.text("p8", ui.fit(g, "p8", tk["name"], gx - 26), 22, y + 3, C["text"] if not muted else C["dim"])
            user = tr["s"].startswith("user:")
            g.text("v20", ui.fit(g, "v20", ("* " if user else "") + self.sample_label(ti), gx - 26), 22, y + 11,
                   (C["orange"] if user else tcol) if not muted else C["dim"])
            row = pt["t"][ti]
            for c in range(16):
                s = page * 16 + c
                x = gx + c * (cw + 2) + (c // 4) * 6
                if s >= pt["len"]:
                    out_len.append((x, y, cw, ch))
                    continue
                vel, rat, chn = row[s]
                if vel:
                    on.setdefault((tcol if not muted else C["dim"], (110, 200, 255)[vel - 1]), []).append((x, y, cw, ch))
                    if vel == 3:
                        white.append((x, y, cw, 4))
                    if rat > 1:
                        dots.extend((x + 4 + r * 6, y + ch - 7, 4, 4) for r in range(rat))
                    if chn < 100:
                        dots.append((x + cw - 9, y + 5, 6, 6 * (100 - chn) // 75 + 1))
                else:
                    (off_beat if s % 4 == 0 else off_rest).append((x, y, cw, ch))
            if aud_p == self.edit and aud_s is not None and aud_s // 16 == page:
                c = aud_s % 16
                frames.append((gx + c * (cw + 2) + (c // 4) * 6, y))
        g.rects(off_beat, C["hull"])
        g.rects(off_rest, C["off"])
        g.rects(out_len, C["void"])
        for (col, a), lst in on.items():
            g.rects(lst, col, a)
        g.rects(white, C["white"])
        g.rects(dots, C["void"])
        for x, y in frames:
            g.frame(x - 1, y - 1, cw + 2, ch + 2, C["white"], 2, 200)
        c = self.col % 16
        x = gx + c * (cw + 2) + (c // 4) * 6
        y = gy + self.row * rh
        g.frame(x - 3, y - 3, cw + 6, ch + 6, app.accent if blink else C["orangehi"], 3)
        if pt["len"] > 16:
            g.text("v20", "%d-%d/%d" % (page * 16 + 1, page * 16 + 16, pt["len"]), W - 64, 72, C["cyan"], 255,
                   "right")
        # info panel
        iy = gy + len(self.kit) * rh + 6
        r2 = app.input.down("r2")
        g.rect(8, iy, W - 16, 52, C["panel"])
        g.frame(8, iy, W - 16, 52, app.accent if r2 else C["hull"], 2)
        tr = self.tracks[self.row]
        tk = self.kit[self.row]
        tcol = TRACK_COL.get(tk["id"], C["cyan"])
        ch_list = self.choices(self.row)
        files = [c_["file"] for c_ in ch_list]
        idx = files.index(tr["s"]) + 1 if tr["s"] in files else 0
        g.text("p8", "%s  %s  %d/%d  %s" % (tk["name"], self.sample_label(self.row), idx, len(files),
                                           "(TEU)" if tr["s"].startswith("user:") else ""), 20, iy + 8, tcol)
        g.text("v20", "VOL", 20, iy + 24, C["muted"])
        g.rect(56, iy + 30, 100, 8, C["hull"])
        g.rect(56, iy + 30, tr["vol"] * 10, 8, tcol)
        g.text("v20", "TOM %+d" % tr["pitch"], 170, iy + 24, C["soft"] if tr["pitch"] else C["dim"])
        g.text("v20", "PAN %s" % {-2: "L", -1: "l", 0: "C", 1: "r", 2: "R"}[tr["pan"]], 250, iy + 24,
               C["soft"] if tr["pan"] else C["dim"])
        if tr["mute"] or self.solo == self.row:
            g.text("v20", "SILÊNCIO" if tr["mute"] else "SOLO", 318, iy + 24, (255, 90, 100) if tr["mute"] else C["green"])
        st = pt["t"][self.row][self.col]
        if r2:
            g.text("v20", "esq/dir som · cima/baixo tom · X/Y volume · A pan · B silenciar", W - 18, iy + 24, app.accent, 255,
                   "right")
        else:
            g.text("v20", "PASSO %d/%d: %s  x%d  %d%%" % (self.col + 1, pt["len"], VEL_NAME[st[0]], st[1], st[2]),
                   W - 18, iy + 24, C["text"] if st[0] else C["dim"], 255, "right")

    def draw_build(self, g, aud, blink):
        app = self.app
        st = forge_styles.STYLES[self.style]
        g.text("v20", "<", 16, 96, C["cyan"])
        g.text("p16", st["name"], 36, 98, app.accent)
        g.text("v20", ">", 36 + g.tw("p16", st["name"]) + 10, 96, C["cyan"])
        g.text("v20", "%d BPM - swing %d%% - escreve no padrao %s" % (st["bpm"], st["swing"], PAT_NAMES[self.edit]),
               W - 16, 98, C["muted"], 255, "right")
        pt = self.pats[self.edit]
        aud_p, aud_s = aud[0], aud[1]
        y0, rh = 126, 36
        cells_on, cells_off, heads = {}, [], []
        for ti, tk in enumerate(self.kit):
            y = y0 + ti * rh
            tid = tk["id"]
            tcol = TRACK_COL.get(tid, C["cyan"])
            sel = ti == self.row
            if sel:
                g.rect(8, y - 3, W - 16, rh - 2, C["deck"])
                g.frame(8, y - 3, W - 16, rh - 2, app.accent if blink else C["orangehi"], 2)
            g.rect(12, y, 5, 28, tcol)
            g.text("p8", tk["name"][:10], 22, y + 2, C["text"])
            n = len(st["vars"].get(tid, ["."]))
            g.text("v20", "VAR %d/%d" % (self.vars.get(tid, 0) % n + 1, n), 22, y + 10, tcol)
            for s in range(16):
                x = 130 + s * 24 + (s // 4) * 6
                vel = pt["t"][ti][s][0] if s < pt["len"] else 0
                if vel:
                    cells_on.setdefault((tcol, (110, 200, 255)[vel - 1]), []).append((x, y + 4, 20, 20))
                else:
                    cells_off.append((x, y + 4, 20, 20))
                if aud_p == self.edit and aud_s == s:
                    heads.append((x, y + 25, 20, 3))
            g.text("v20", "A/Y", W - 16, y + 6, C["dim"] if not sel else C["cyan"], 255, "right")
        g.rects(cells_off, C["off"])
        for (col, a), lst in cells_on.items():
            g.rects(lst, col, a)
        g.rects(heads, C["white"])
        g.text("v20", "X = dado (tudo ao acaso)  ·  SELECT+L2 desfaz  ·  afina depois na GRELHA", W // 2, 418, C["muted"],
               255, "center")

    def draw_song(self, g, aud, blink):
        app = self.app
        song = self.song
        g.text("p8", "ARRANJO", 16, 98, app.accent)
        bars = sum(self.pats[p]["len"] for p in self.song_list()) / 16.0
        secs = bars * 4 * 60.0 / app.mixer.bpm
        g.text("v20", "%d blocos - %.1f compassos - %d:%02d   %s" % (len(song), bars, secs // 60, secs % 60,
                                                                  "MÚSICA ON" if self.song_on else "MÚSICA OFF (X)"),
               W - 16, 96, C["soft"] if self.song_on else C["dim"], 255, "right")
        if not song:
            g.text("v20", "Vazio: A ou cima/baixo cria o primeiro bloco (com o padrão %s)." % PAT_NAMES[self.edit],
                   W // 2, 160, C["soft"], 255, "center")
            g.text("v20", "Sem arranjo, o modo música toca A, B, C... até ao último padrão.", W // 2, 184, C["muted"],
                   255, "center")
        cols, bw, bh = 16, 36, 40
        top = max(0, (self.scol // cols - 1)) * cols
        playing_idx = aud[2] if (self.playing and self.song_on and song) else None
        for i in range(top, min(len(song), top + cols * 3)):
            r, c = (i - top) // cols, (i - top) % cols
            x, y = 16 + c * (bw + 2), 124 + r * (bh + 8)
            p = song[i]
            empty = self.pattern_empty(p)
            fill = C["green"] if i == playing_idx else (C["hull"] if not empty else C["off"])
            g.rect(x, y, bw, bh, fill)
            g.frame(x, y, bw, bh, app.accent if i == self.scol and blink else C["hullhi"], 3 if i == self.scol else 1)
            g.text("p16", PAT_NAMES[p], x + bw // 2, y + 8, C["void"] if i == playing_idx else C["text"], 255, "center")
            g.text("v20", "%d" % (i + 1), x + bw // 2, y + 24, C["dim"], 255, "center")
        # preview of the block under the cursor
        p = song[self.scol] if song else self.edit
        pt = self.pats[p]
        y0 = 290
        g.text("p8", "PADRÃO %s · %d passos" % (PAT_NAMES[p], pt["len"]), 16, y0 - 14, C["muted"])
        cells = {}
        for ti, tk in enumerate(self.kit):
            tcol = TRACK_COL.get(tk["id"], C["cyan"])
            for s in range(pt["len"]):
                if pt["t"][ti][s][0]:
                    cells.setdefault(tcol, []).append((16 + s * 19, y0 + ti * 14, 17, 12))
        g.rect(14, y0 - 2, min(32, pt["len"]) * 19 + 2, len(self.kit) * 14 + 2, C["off"])
        for col, lst in cells.items():
            g.rects(lst, col)
