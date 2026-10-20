# SONGSCAN - listens to a song before you play it (VOID RUNNER): loudness at 10 Hz, hits (onsets) and drops.
# Pure Python + audioop (fast C) so it runs on the console: a 4-minute song takes a second or two, and the
# result is cached in vr_cache/ so the next time is instant.
import bisect
import os
import threading
import wave

import engine
from engine import audioop

CACHE = os.path.join(engine.APP, "vr_cache")
VERSION = 2


def _key(path):
    try:
        st = os.stat(path)
        return "%s-%d-%d-v%d" % (os.path.basename(path), st.st_size, int(st.st_mtime), VERSION)
    except OSError:
        return None


def valid_scan(c):
    """a cached scan has the shape Timeline.add reads (the cache is only ever written by scan_file, atomically:
    checking the shape, not every value, keeps loading it instant)"""
    return (isinstance(c, dict) and engine.num(c.get("dur"), None) is not None and isinstance(c.get("env"), list)
            and isinstance(c.get("on"), list) and all(engine.num(v, None) is not None for v in c["env"][:1])
            and all(isinstance(o, list) and len(o) == 2 for o in c["on"][:1]))


def scan_file(path):
    """{'dur': seconds, 'env': loudness at 40 Hz (0..1 of full scale), 'on': [[t, strength 0..1], ...]}"""
    key = _key(path)
    cp = os.path.join(CACHE, key + ".json") if key else None
    if cp and os.path.exists(cp):
        try:
            c = engine.read_json(cp)
            if valid_scan(c):              # a damaged cache file is simply scanned again
                return c
        except Exception:
            pass
    w = wave.open(path, "rb")
    try:
        ch, sw, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        hop = max(1, rate // 40)
        full = float(1 << (8 * sw - 1))
        env = []
        while True:
            d = w.readframes(hop)
            if not d:
                break
            if sw == 1:
                d = audioop.bias(d, 1, -128)
            if ch == 2:
                d = audioop.tomono(d, sw, 0.5, 0.5)
            env.append(audioop.rms(d, sw) / full)
        dur = w.getnframes() / float(rate)
    finally:
        w.close()
    # onsets: the loudness jumps above its recent level (kicks, snares, chords hitting)
    on, flux = [], []
    for i in range(len(env)):
        prev = max(env[max(0, i - 3):i] or [0.0])
        flux.append(max(0.0, env[i] - prev))
    cum = [0.0]
    for f in flux:
        cum.append(cum[-1] + f)
    last = -1.0
    for i in range(1, len(env) - 1):
        f = flux[i]
        if f <= 0.0 or f < flux[i - 1] or f < flux[i + 1]:
            continue
        lo, hi = max(0, i - 40), min(len(flux), i + 40)
        mean = (cum[hi] - cum[lo]) / float(hi - lo)
        t = i / 40.0
        if f > 1.8 * mean + 0.004 and t - last >= 0.18:
            on.append([round(t, 3), f])
            last = t
    if on:
        top = sorted(x[1] for x in on)[int(len(on) * 0.9)] or 1.0
        for x in on:
            x[1] = round(min(1.0, x[1] / top), 3)
    out = {"dur": round(dur, 3), "env": [round(v, 5) for v in env], "on": on}
    if cp:
        try:
            if not os.path.isdir(CACHE):
                os.makedirs(CACHE)
            engine.write_json(cp, out, sync=False)
        except Exception:
            pass
    return out


class Timeline(object):
    """one or more scanned files played in a row: intensity I(t) 0..1, onsets and drops.
    Each file is normalised on its own (songs are mastered differently)."""

    def __init__(self):
        self.on = []           # [t, strength]
        self.on_t = []         # their times, to find the ones of a frame by bisection
        self.ordered = True    # the times only go up (they always do: a file is scanned in order)
        self.dur = 0.0
        self.I10 = []          # 10 Hz intensity
        self.drops = []

    def add(self, scan):
        off = self.dur
        env = scan["env"]
        on = [[t + off, st] for t, st in scan["on"]]
        n10 = len(env) // 4
        if n10:
            loud = [sum(env[i * 4:i * 4 + 4]) / 4.0 for i in range(n10)]
            s = sorted(loud)
            lo, hi = s[int(len(s) * 0.15)], s[min(len(s) - 1, int(len(s) * 0.97))]
            rng = max(hi - lo, 0.02)
            sm, acc, k = [], 0.0, 12                   # 1.2 s moving average
            for i, v in enumerate(loud):
                acc += v
                if i >= k:
                    acc -= loud[i - k]
                sm.append(acc / min(i + 1, k))
            dens = [0.0] * n10                          # hits in the last 2 s
            for t, st in scan["on"]:
                i = int(t * 10)
                for j in range(i, min(n10, i + 20)):
                    dens[j] += 0.5 + 0.5 * st
            self.I10 += [max(0.0, min(1.0, 0.85 * (v - lo) / rng + 0.35 * min(1.0, dens[i] / 6.0)))
                         for i, v in enumerate(sm)]
        self.on += on
        self.on_t += [o[0] for o in on]
        self.ordered = all(a <= b for a, b in zip(self.on_t, self.on_t[1:]))
        self.dur += scan["dur"]
        self._drops()

    def _drops(self):
        """a jump to high energy after a quieter stretch (never in the first 8 s)"""
        I = self.I10
        cum = [0.0]
        for v in I:
            cum.append(cum[-1] + v)
        self.drops = []
        i, n = 80, len(I)
        while i < n - 20:
            after = (cum[i + 20] - cum[i]) / 20.0
            before = (cum[i - 5] - cum[i - 50]) / 45.0
            if after > 0.62 and after - before > 0.25:
                self.drops.append(i / 10.0)
                i += 120
            else:
                i += 2
        if not self.drops:                         # always give the song a peak: its loudest stretch
            best, bi = -1.0, None
            for i in range(80, n - 20, 5):
                v = (cum[i + 20] - cum[i]) / 20.0
                if v > best:
                    best, bi = v, i
            if bi is not None and best > 0.45:
                self.drops = [bi / 10.0]

    def I(self, t):
        if not self.I10:
            return 0.5
        x = t * 10.0
        i = int(x)
        if i >= len(self.I10) - 1:
            return self.I10[-1]
        if i < 0:
            return self.I10[0]
        f = x - i
        return self.I10[i] * (1 - f) + self.I10[i + 1] * f

    def onsets(self, t0, t1):
        if self.ordered:              # every frame of the Void Runner: no need to walk the whole song
            return self.on[bisect.bisect_right(self.on_t, t0):bisect.bisect_right(self.on_t, t1)]
        return [o for o in self.on if t0 < o[0] <= t1]

    def next_drop(self, t):
        for d in self.drops:
            if d > t:
                return d
        return None


def build(paths):
    tl = Timeline()
    for p in paths:
        tl.add(scan_file(p))
    return tl


class Scanner(threading.Thread):
    """scans in the background; .done / .timeline / .error"""

    def __init__(self, paths):
        threading.Thread.__init__(self)
        self.daemon = True
        self.paths = list(paths)
        self.timeline = None
        self.error = None
        self.done = False
        self.progress = 0.0
        self.cancelled = False

    def cancel(self):
        """the player went back to the menu: stop after the file being scanned (the CPU is needed elsewhere)"""
        self.cancelled = True

    def run(self):
        try:
            tl = Timeline()
            for i, p in enumerate(self.paths):
                if self.cancelled:
                    break
                tl.add(scan_file(p))
                self.progress = (i + 1) / float(len(self.paths))
            if not self.cancelled:
                self.timeline = tl
        except Exception as e:
            self.error = e
        self.done = True


def duration(path):
    try:
        w = wave.open(path, "rb")
        d = w.getnframes() / float(w.getframerate())
        w.close()
        return d
    except Exception:
        return 0.0
