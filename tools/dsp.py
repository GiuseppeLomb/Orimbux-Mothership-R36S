"""Small numpy/scipy synth toolkit for the build-time music (Beat Duel songs, trailer, credits)."""
import math
import subprocess
import wave

import numpy as np
import scipy.signal as sg

SR = 44100
SAMPLES = "/home/claude/sp/etc/samples"


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


def saw(f, n, phase=0.0):
    return 2 * ((phase + np.arange(n) * f / SR) % 1.0) - 1


def sq(f, n, duty=0.5, vib=0.0, vr=5.5, vdelay=0.0):
    t = tt(n)
    depth = vib * np.clip((t - vdelay) / 0.15, 0, 1) if vdelay else vib
    ph = np.cumsum(f * (1 + depth * np.sin(2 * np.pi * vr * t)) / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def tri(f, n):
    return 4 * np.abs(((np.arange(n) * f / SR) % 1.0) - 0.5) - 1


def sine(f, n, vib=0.0, vr=5.0):
    t = tt(n)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * vr * t)) / SR))


def noise(n, seed=0):
    return np.random.RandomState(seed).uniform(-1, 1, n)


def adsr(n, a=0.005, d=0.1, s=0.7, r=0.05):
    t = tt(n)
    dur = n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((dur - t) / max(r, 1e-4), 0, 1)
    return e * rel


def perc(n, a=0.002, d=0.2):
    t = tt(n)
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))


def lp(x, fc, order=2):
    b, a = sg.butter(order, min(fc, SR * 0.45) / (SR / 2))
    return sg.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = sg.butter(order, fc / (SR / 2), "high")
    return sg.lfilter(b, a, x)


def bp(x, lo, hi):
    b, a = sg.butter(2, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], "band")
    return sg.lfilter(b, a, x)


def sweep_lp(x, f0, f1, block=512, q_order=2):
    """low-pass whose cutoff glides exponentially from f0 to f1 (or follows an array of cutoffs)"""
    out = np.zeros_like(x)
    nb = (len(x) + block - 1) // block
    zi = None
    for i in range(nb):
        k = i / max(1, nb - 1)
        fc = f0 * (f1 / f0) ** k if not hasattr(f0, "__len__") else f0[min(i, len(f0) - 1)]
        b, a = sg.butter(q_order, min(fc, SR * 0.45) / (SR / 2))
        seg = x[i * block:(i + 1) * block]
        if zi is None:
            zi = sg.lfilter_zi(b, a) * 0
        y, zi = sg.lfilter(b, a, seg, zi=zi)
        out[i * block:i * block + len(seg)] = y
    return out


def supersaw(f, n, voices=7, det=0.012, seed=0):
    rng = np.random.RandomState(seed)
    y = np.zeros(n)
    for i in range(voices):
        d = det * (i - (voices - 1) / 2.0) / ((voices - 1) / 2.0)
        y += saw(f * (1 + d), n, rng.rand())
    return y / math.sqrt(voices)


def reverb(x, sec=1.8, mix=0.25, seed=1, damp=6000):
    n = int(sec * SR)
    ir = noise(n, seed) * np.exp(-tt(n) * 6.9 / sec)
    ir = lp(ir, damp)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    wet = sg.fftconvolve(x, ir)[:len(x)]
    return x * (1 - mix) + wet * mix


def delay(x, sec, fb=0.35, mix=0.3, tone=5000):
    d = int(sec * SR)
    a = np.zeros(d + 1)
    a[0] = 1.0
    a[d] = -fb
    wet = sg.lfilter([1.0], a, x) - x
    return x + lp(wet, tone) * mix


def pluck(f, n, dec=0.996, seed=0):
    d = max(2, int(SR / f))
    exc = np.zeros(n)
    exc[:d] = noise(d, seed)
    a = np.zeros(d + 2)
    a[0] = 1.0
    a[d] = -0.5 * dec
    a[d + 1] = -0.5 * dec
    return sg.lfilter([1.0], a, exc)


def epiano(f, n):
    t = tt(n)
    idx = 1.4 * np.exp(-t * 4.0) + 0.2
    car = np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * f * t) * idx)
    tine = np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 35) * 0.1
    return (car + tine) * (1 - np.exp(-t * 300)) * np.exp(-t * (1.3 + f / 1000.0))


def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "%s/%s.flac" % (SAMPLES, name), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def fit(x, n):
    """resample to exactly n samples (speed + pitch change, jungle style)"""
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def sidechain(n, times, depth=0.6, tau=0.12):
    imp = np.zeros(n)
    for t in times:
        i = int(t * SR)
        if 0 <= i < n:
            imp[i] = 1.0
    k = np.exp(-tt(int(tau * 6 * SR)) / tau)
    env = sg.fftconvolve(imp, k)[:n]
    return 1.0 - depth * np.clip(env, 0, 1)


def master(y, drive=1.3):
    y = y / (np.max(np.abs(y)) + 1e-9)
    y = np.tanh(drive * y) / math.tanh(drive)
    return y * 0.92


def save_mono(path, y, rate=22050):
    """write at 22.05 kHz (anti-aliased 2:1) or 44.1 kHz mono s16"""
    y = np.clip(y, -1, 1)
    if rate == 22050:
        k = np.arange(-48, 49)
        h = np.sinc(k * 0.45) * np.hamming(len(k))
        y = np.convolve(y, h / h.sum(), mode="same")[::2]
    pcm = (y * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


class Song(object):
    """step-based arranger: buses mixed at render; events logged for Beat Duel charts"""

    def __init__(self, bpm, bars, swing=0.0, tail=2.5):
        self.bpm, self.bars = bpm, bars
        self.step = 60.0 / bpm / 4
        self.swing = swing
        self.n = int(SR * (bars * 16 * self.step + tail))
        self.bus = {}
        self.ev = []

    def t(self, st):
        sw = self.swing * self.step if (self.swing and int(round(st * 2)) % 4 == 2) else 0.0
        return st * self.step + sw

    def put(self, sig, st, vol=1.0, bus="main", kind=None, pitch=0, ln=1):
        b = self.bus.get(bus)
        if b is None:
            b = self.bus[bus] = np.zeros(self.n)
        i = int(self.t(st) * SR)
        if i >= self.n or i < 0:
            return
        j = min(self.n, i + len(sig))
        b[i:j] += sig[:j - i] * vol
        if kind:
            self.ev.append((round(self.t(st), 4), kind, pitch, ln))

    def notes(self, notes, bar0, synth, vol, bus, kind="lead", transpose=0):
        """notes: [(step offset, midi, length steps)] from bar0"""
        for st, m, ln in notes:
            if m is None:
                continue
            m += transpose
            n = int(SR * self.step * ln * 1.05) + int(0.08 * SR)
            self.put(synth(mtof(m), n, ln * self.step), bar0 * 16 + st, vol, bus, kind, m, ln)

    def kick_times(self):
        return [e[0] for e in self.ev if e[1] == "kick"]

    def charts(self):
        leads = sorted([e for e in self.ev if e[1] == "lead"])
        pitches = sorted(e[2] for e in leads) or [60]
        q = [pitches[int(len(pitches) * f)] for f in (0.25, 0.5, 0.75)]

        def lane_of(p):
            return 0 if p < q[0] else (1 if p < q[1] else (2 if p < q[2] else 3))
        kicks = sorted(e[0] for e in self.ev if e[1] == "kick")
        snares = sorted(e[0] for e in self.ev if e[1] == "snare")
        stabs = sorted(e[0] for e in self.ev if e[1] == "stab")
        beat = 60.0 / self.bpm

        def build(items, min_gap, max_rate):
            items = sorted(items)
            out, last, busy, window = [], [-9.0] * 4, [-9.0] * 4, []
            for it in items:
                t, lane = it[0], it[1]
                dur = it[2] if len(it) > 2 else 0.0
                if t - last[lane] < min_gap or t < busy[lane] + 0.08:
                    continue
                window = [w for w in window if t - w < 1.0]
                if len(window) >= max_rate:
                    continue
                if out and abs(out[-1][0] - t) < 0.001 and out[-1][1] == lane:
                    continue
                out.append([round(t, 3), lane] + ([round(dur, 3)] if dur else []))
                last[lane] = t
                busy[lane] = t + dur
                window.append(t)
            return out

        def lead_item(e, hold_from):
            ln = e[3]
            if ln >= hold_from:
                return (e[0], lane_of(e[2]), ln * self.step * 0.8)
            return (e[0], lane_of(e[2]))
        easy = [lead_item(e, 6) for e in leads if e[3] >= 4]
        easy += [(t, 3) for t in snares if abs((t / beat) % 2 - 1) < 0.01][::2]
        easy += [(t, 0) for t in kicks if abs((t / beat) % 4) < 0.01][::2]
        normal = [lead_item(e, 4) for e in leads if e[3] >= 2]
        normal += [(t, 0) for t in kicks if abs((t / beat) % 2) < 0.01] + [(t, 3) for t in snares]
        normal += [(t, 1) for t in stabs][::2]
        hard = [lead_item(e, 4) for e in leads]
        hard += [(t, 0) for t in kicks] + [(t, 3) for t in snares] + [(t, 2) for t in stabs]
        return {"easy": build(easy, 0.35, 2), "normal": build(normal, 0.2, 4), "hard": build(hard, 0.11, 7)}
