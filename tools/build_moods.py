"""Intro music: 5 moods (melancolico, alegre, energetico, triste, zangado). Each mood is 3-4 segments of
8 bars in the same key and tempo; the app chains them in a random order without gaps, so the music keeps
changing and can play for hours. Reverb/delay tails are wrapped into the start of each segment (seamless).
  python3 tools/build_moods.py [mood ...]  ->  ports/mothership/assets/moods/<mood>_<n>.wav (22 kHz mono)"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa
from dsp import SR, Song, mtof, saw, sq, tri, sine, noise, perc, adsr, lp, hp, sweep_lp, supersaw, reverb, delay  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "ports", "mothership", "assets")
OUTD = os.path.join(A, "moods")
TAIL = 3.5
TARGET_RMS = 0.13


def wav(rel):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(A, rel), "-ac", "1", "-ar", str(SR), "-f",
                          "f32le", "-"], check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


KIT = {}


def kit(name):
    if name not in KIT:
        KIT[name] = wav("forge/%s.wav" % name)
    return KIT[name]


# ---------------------------------------------------------------- instruments
def n_of(steps, S, extra=0.0):
    return int(steps * S.step * SR + extra * SR)


def ep_chord(S, notes, steps, strum=0.012, bright=1.0):
    n = n_of(steps, S, 1.2)
    y = np.zeros(n + int(strum * SR * len(notes)) + 1)
    for i, m in enumerate(notes):
        k = int(i * strum * SR)
        y[k:k + n] += dsp.epiano(mtof(m), n) * (0.8 if i else 1.0)
    return lp(y, 2600 * bright)


def pad(S, notes, steps, cut=1200, att=0.6, rel=1.2, seed=0, voices=5, det=0.009):
    n = n_of(steps, S, rel)
    y = sum(supersaw(mtof(m), n, voices, det, seed + i) for i, m in enumerate(notes))
    return lp(y, cut) * adsr(n, att, 0.5, 0.85, rel) / max(1, len(notes))


def soft_bass(S, m, steps, cut=500):
    n = n_of(steps, S, 0.05)
    f = mtof(m)
    y = sine(f, n) + 0.35 * tri(f, n) + 0.12 * sine(2 * f, n)
    return lp(np.tanh(1.4 * y), cut) * adsr(n, 0.01, 0.2, 0.8, 0.08)


def sq_bass(S, m, steps):
    n = n_of(steps, S, 0.02)
    y = sq(mtof(m), n, 0.5) * 0.6 + sine(mtof(m), n) * 0.6
    return lp(y, 900) * adsr(n, 0.003, 0.08, 0.6, 0.03)


def saw_bass(S, m, steps, cut=700, drive=1.0):
    n = n_of(steps, S, 0.02)
    y = saw(mtof(m), n) * 0.6 + saw(mtof(m) * 1.007, n, 0.3) * 0.4 + sine(mtof(m) / 2, n) * 0.5
    return lp(np.tanh(drive * y), cut) * adsr(n, 0.005, 0.1, 0.75, 0.04)


def reese(S, m, steps, cut=520):
    n = n_of(steps, S, 0.03)
    y = saw(mtof(m) * 0.993, n) + saw(mtof(m) * 1.008, n, 0.4) + sine(mtof(m) / 2, n) * 0.9
    return lp(np.tanh(2.2 * y), cut) * adsr(n, 0.01, 0.1, 0.9, 0.05) * 0.5


def soft_lead(S, m, steps, vib=0.004):
    n = n_of(steps, S, 0.25)
    f = mtof(m)
    t = np.arange(n) / SR
    v = 1 + vib * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.15) / 0.3, 0, 1)
    ph = np.cumsum(f * v / SR)
    y = np.sin(2 * np.pi * ph) * 0.7 + (2 * np.abs(2 * (ph % 1) - 1) - 1) * 0.35
    return lp(y, 3000) * adsr(n, 0.03, 0.3, 0.75, 0.22)


def bell(S, m, steps=8):
    n = n_of(steps, S, 0.8)
    return dsp.epiano(mtof(m), n) * 0.8 + sine(mtof(m) * 2, n) * np.exp(-np.arange(n) / SR * 3) * 0.15


def pluck(S, m, dec=0.996, cut=3500, seed=0):
    n = int(1.6 * SR)
    return lp(dsp.pluck(mtof(m), n, dec, seed), cut)


def chip(S, m, steps, duty=0.25, cut=3200):
    n = n_of(steps, S, 0.03)
    return lp(sq(mtof(m), n, duty), cut) * perc(n, 0.002, max(0.05, steps * S.step * 0.6))


def saw_lead(S, m, steps, cut=3200):
    n = n_of(steps, S, 0.15)
    y = saw(mtof(m), n) * 0.5 + saw(mtof(m) * 1.005, n, 0.3) * 0.5 + sq(mtof(m) / 2, n, 0.5) * 0.15
    return lp(y, cut) * adsr(n, 0.01, 0.2, 0.7, 0.12)


def stab(S, notes, steps=2, cut=2400, seed=3):
    n = n_of(steps, S, 0.05)
    y = sum(supersaw(mtof(m), n, 4, 0.01, seed + i) for i, m in enumerate(notes)) / len(notes)
    return lp(y, cut) * perc(n, 0.002, 0.14)


def crackle(n, seed=0, density=14):
    rng = np.random.RandomState(seed)
    y = noise(n, seed + 100) * 0.015
    for _ in range(int(n / SR * density)):
        i = rng.randint(0, n - 40)
        y[i:i + 40] += rng.uniform(-1, 1) * np.exp(-np.arange(40) / 6.0) * rng.uniform(0.1, 0.5)
    return hp(lp(y, 6000), 300)


# ---------------------------------------------------------------- arranging + mixing
class Seg(object):
    def __init__(self, bpm, bars=8):
        self.S = Song(bpm, bars, tail=TAIL)
        self.bars = bars
        self.kicks = []

    def put(self, sig, bar, step, vol, bus):
        self.S.put(sig, bar * 16 + step, vol, bus)
        if bus == "kick" and vol > 0.3:
            self.kicks.append(self.S.t(bar * 16 + step))

    def notes(self, fn, mel, vol, bus, bar0=0):
        for st, m, ln in mel:
            self.put(fn(self.S, m, ln), bar0 + st // 16, st % 16, vol, bus)

    def mix(self, sends, pans=None, duck=(), duck_depth=0.4, verb=2.4, delays=None, gains=None):
        S = self.S
        n = S.n
        dry, wet = np.zeros(n), np.zeros(n)
        sc = dsp.sidechain(n, self.kicks, duck_depth, 0.12) if duck and self.kicks else None
        for name, x in S.bus.items():
            x = x * (gains or {}).get(name, 1.0)
            if sc is not None and name in duck:
                x = x * sc
            if delays and name in delays:
                d = delays[name]
                x = delay(x, d[0] * S.step, d[1], d[2], d[3] if len(d) > 3 else 4000)
            dry += x
            wet += x * sends.get(name, 0.0)
        out = dry + reverb(wet, verb, 1.0, 7, 6500) * 0.55
        # seamless loop: fold everything after the last bar back onto the start
        L = int(self.bars * 16 * S.step * SR)
        y = out[:L].copy()
        tail = out[L:]
        y[:len(tail)] += tail
        return y


def finish(segs):
    allx = np.concatenate(segs)
    g = TARGET_RMS / (np.sqrt(np.mean(allx ** 2)) + 1e-9)
    out = []
    k = int(0.004 * SR)                                   # 4 ms edges: no click between any two segments
    ramp = np.linspace(0, 1, k)
    for s in segs:
        x = np.tanh(1.1 * s * g) / np.tanh(1.1) * 0.95
        x[:k] *= ramp
        x[-k:] *= ramp[::-1]
        out.append(x)
    return out


def ch(notes, octave=0):
    return [m + 12 * octave for m in notes]


# ====================================================================== 1 MELANCOLICO (A minor, lo-fi)
def melancolico():
    bpm = 80
    C = {"Fmaj7": [53, 57, 60, 64], "G6": [55, 59, 62, 64], "Em7": [52, 55, 59, 62], "Am7": [57, 60, 64, 67],
         "Dm7": [50, 53, 57, 60], "Cmaj7": [48, 52, 55, 59], "E7": [52, 56, 59, 62], "G": [55, 59, 62, 67]}
    root = {"Fmaj7": 41, "G6": 43, "Em7": 40, "Am7": 45, "Dm7": 38, "Cmaj7": 36, "E7": 40, "G": 43}
    P1 = ["Fmaj7", "G6", "Em7", "Am7", "Fmaj7", "G6", "Am7", "Am7"]
    P2 = ["Dm7", "G", "Cmaj7", "Fmaj7", "Dm7", "E7", "Am7", "Am7"]
    MEL_B = [(0, 76, 6), (6, 74, 2), (8, 72, 4), (12, 69, 4), (16, 74, 6), (22, 72, 2), (24, 71, 8),
             (32, 67, 4), (36, 72, 4), (40, 76, 6), (46, 74, 2), (48, 72, 12), (60, 69, 4),
             (64, 77, 6), (70, 76, 2), (72, 74, 4), (76, 72, 4), (80, 71, 6), (86, 68, 2), (88, 71, 4), (92, 74, 4),
             (96, 72, 8), (104, 71, 4), (108, 69, 4), (112, 69, 16)]
    MEL_C = [(0, 69, 4), (4, 72, 4), (8, 76, 8), (16, 74, 4), (20, 71, 4), (24, 67, 8), (32, 71, 6), (38, 74, 2),
             (40, 76, 8), (48, 72, 16), (64, 76, 4), (68, 77, 4), (72, 76, 4), (76, 72, 4), (80, 74, 8), (88, 71, 8),
             (96, 72, 4), (100, 71, 4), (104, 69, 8), (112, 64, 4), (116, 69, 12)]
    BELLS = [(0, 76, 16), (16, 74, 16), (32, 71, 16), (48, 72, 16), (64, 69, 16), (80, 71, 16), (96, 72, 16),
             (112, 76, 16)]

    def base(prog, drums=True, seed=0):
        s = Seg(bpm)
        for b, c in enumerate(prog):
            s.put(ep_chord(s.S, C[c], 10), b, 0, 0.32, "keys")
            s.put(ep_chord(s.S, C[c][1:], 6), b, 10, 0.18, "keys")
            s.put(pad(s.S, ch(C[c], 0), 16, 900, 0.8, seed=b + seed), b, 0, 0.16, "pad")
            s.put(soft_bass(s.S, root[c], 7), b, 0, 0.42, "bass")
            s.put(soft_bass(s.S, root[c] + (7 if b % 2 else 12), 5), b, 10, 0.28, "bass")
            if drums:
                s.put(kit("bd_boom"), b, 0, 0.5, "kick")
                s.put(kit("bd_boom"), b, 10, 0.32, "kick")
                for st in (4, 12):
                    s.put(kit("drum_snare_soft"), b, st, 0.3, "snare")
                for st in range(0, 16, 2):
                    s.put(kit("hat_tap"), b, st + (1 if st % 4 else 0) * 0.35, 0.12 if st % 4 else 0.18, "hat")
        s.put(crackle(s.S.n, seed), 0, 0, 1.0, "vinyl")
        return s

    sends = {"keys": 0.3, "pad": 0.4, "lead": 0.45, "bell": 0.5, "pluck": 0.45, "pluckmel": 0.45, "snare": 0.25}
    delays = {"lead": (3, 0.35, 0.3, 3000), "pluck": (3, 0.4, 0.35, 2800), "pluckmel": (3, 0.35, 0.3, 2800)}
    G = {"bass": 0.45, "kick": 0.75, "lead": 1.1, "keys": 0.7, "pad": 1.3, "hat": 1.8, "snare": 2.0, "bell": 2.0,
         "pluck": 4.0, "pluckmel": 7.0}
    segs = []
    s = base(P1)
    s.notes(bell, BELLS, 0.14, "bell")
    segs.append(s.mix(sends, delays=delays, gains=G))
    s = base(P2, seed=10)
    s.notes(soft_lead, MEL_B, 0.24, "lead")
    segs.append(s.mix(sends, delays=delays, gains=G))
    s = base(P1, seed=20)
    for b, c in enumerate(P1):
        for st in range(0, 16, 2):
            m = C[c][(st // 2) % 4] + 12
            s.put(pluck(s.S, m, 0.993, 3000, st), b, st, 0.07, "pluck")
    s.notes(soft_lead, MEL_C, 0.22, "lead")
    segs.append(s.mix(sends, delays=delays, gains=G))
    s = base(P2, drums=False, seed=30)
    s.notes(lambda S, m, ln: pluck(S, m, 0.997, 2600), MEL_B[:14], 0.18, "pluckmel")
    segs.append(s.mix(sends, delays=delays, gains=G))
    return finish(segs)


# ====================================================================== 2 ALEGRE (D major, chip-pop)
def alegre():
    bpm = 112
    C = {"D": [62, 66, 69], "A": [61, 64, 69], "Bm": [62, 66, 71], "G": [62, 67, 71], "F#m": [61, 66, 69]}
    root = {"D": 38, "A": 45, "Bm": 47, "G": 43, "F#m": 42}
    P1 = ["D", "A", "Bm", "G", "D", "A", "Bm", "G"]
    P2 = ["G", "A", "F#m", "Bm", "G", "A", "D", "D"]
    MEL_A = [(0, 78, 2), (2, 81, 2), (4, 78, 2), (6, 76, 2), (8, 74, 4), (12, 69, 4), (16, 76, 2), (18, 78, 2),
             (20, 76, 2), (22, 73, 2), (24, 69, 8), (32, 71, 2), (34, 74, 2), (36, 78, 4), (40, 76, 2), (42, 74, 2),
             (44, 71, 4), (48, 74, 4), (52, 71, 4), (56, 67, 4), (60, 69, 4), (64, 78, 2), (66, 81, 2), (68, 83, 2),
             (70, 81, 2), (72, 78, 4), (76, 74, 4), (80, 76, 2), (82, 78, 2), (84, 81, 4), (88, 76, 8), (96, 74, 2),
             (98, 76, 2), (100, 78, 4), (104, 71, 4), (108, 74, 4), (112, 74, 8), (120, 73, 8)]
    MEL_C = [(0, 71, 4), (4, 74, 4), (8, 79, 6), (14, 78, 2), (16, 76, 4), (20, 73, 4), (24, 69, 8), (32, 69, 2),
             (34, 73, 2), (36, 78, 6), (42, 76, 2), (44, 73, 4), (48, 74, 8), (56, 71, 8), (64, 79, 4), (68, 78, 4),
             (72, 76, 4), (76, 74, 4), (80, 73, 4), (84, 76, 4), (88, 81, 8), (96, 78, 6), (102, 76, 2), (104, 74, 8),
             (112, 69, 4), (116, 74, 12)]
    COUNTER = [(0, 81, 8), (16, 81, 8), (32, 83, 8), (48, 79, 8), (64, 81, 8), (80, 76, 8), (96, 78, 8),
               (112, 79, 8)]

    def base(prog, kick=True, seed=0):
        s = Seg(bpm)
        for b, c in enumerate(prog):
            notes = C[c]
            for st in range(16):                     # bouncy arp
                m = notes[[0, 1, 2, 1][st % 4]] + 12 * (st // 8)
                s.put(chip(s.S, m, 1, 0.25, 2800), b, st, 0.055, "arpL" if st % 2 else "arpR")
            for st in (0, 4, 8, 12):
                s.put(sq_bass(s.S, root[c], 2), b, st, 0.34, "bass")
                s.put(sq_bass(s.S, root[c] + 12, 1), b, st + 2, 0.22, "bass")
            s.put(pad(s.S, ch(notes, 0), 16, 2200, 0.15, 0.6, seed + b, 4), b, 0, 0.11, "pad")
            if kick:
                for st in (0, 8):
                    s.put(kit("bd_klub"), b, st, 0.55, "kick")
                s.put(kit("bd_klub"), b, 11, 0.3, "kick")
            for st in (4, 12):
                s.put(kit("elec_snare"), b, st, 0.28, "snare")
                s.put(kit("perc_snap") if os.path.exists(os.path.join(A, "forge/perc_snap.wav")) else
                      kit("elec_snare"), b, st, 0.2, "snare")
            for st in range(16):
                s.put(kit("hat_cats"), b, st, 0.06 if st % 2 else 0.1, "hat")
        return s

    sends = {"lead": 0.3, "bell": 0.4, "bellmel": 0.4, "pad": 0.3, "arpL": 0.2, "arpR": 0.2, "snare": 0.15}
    delays = {"lead": (3, 0.3, 0.25, 3500)}
    G = {"bass": 0.43, "kick": 0.65, "lead": 1.25, "pad": 1.4, "arpL": 2.0, "arpR": 2.0, "hat": 1.2, "snare": 1.5,
         "bell": 1.7, "bellmel": 1.5}
    segs = []
    s = base(P1)
    s.notes(bell, COUNTER, 0.13, "bell")
    segs.append(s.mix(sends, duck=("pad", "bass"), duck_depth=0.25, delays=delays, gains=G))
    s = base(P1, seed=10)
    s.notes(lambda S, m, ln: chip(S, m, ln, 0.5, 3600), MEL_A, 0.17, "lead")
    s.notes(lambda S, m, ln: bell(S, m, ln), MEL_A[::2], 0.07, "bell")
    segs.append(s.mix(sends, duck=("pad", "bass"), duck_depth=0.25, delays=delays, gains=G))
    s = base(P2, seed=20)
    s.notes(lambda S, m, ln: chip(S, m, ln, 0.5, 3600), MEL_C, 0.17, "lead")
    segs.append(s.mix(sends, duck=("pad", "bass"), duck_depth=0.25, delays=delays, gains=G))
    s = base(P2, kick=False, seed=30)
    s.notes(bell, [(st, m - 12, ln) for st, m, ln in MEL_A], 0.14, "bellmel")
    segs.append(s.mix(sends, delays=delays, gains=G))
    return finish(segs)


# ====================================================================== 3 ENERGETICO (E minor, synthwave drive)
def energetico():
    bpm = 124
    C = {"Em": [64, 67, 71], "C": [64, 67, 72], "G": [62, 67, 71], "D": [62, 66, 69]}
    root = {"Em": 40, "C": 36, "G": 43, "D": 38}
    P = ["Em", "C", "G", "D", "Em", "C", "G", "D"]
    HOOK = [(0, 71, 3), (3, 76, 3), (6, 79, 2), (8, 78, 4), (12, 76, 4), (16, 79, 3), (19, 76, 3), (22, 72, 2),
            (24, 74, 4), (28, 76, 4), (32, 74, 3), (35, 71, 3), (38, 67, 2), (40, 69, 4), (44, 71, 4), (48, 69, 6),
            (54, 66, 2), (56, 69, 4), (60, 74, 4), (64, 83, 3), (67, 81, 3), (70, 79, 2), (72, 78, 4), (76, 76, 4),
            (80, 79, 4), (84, 76, 4), (88, 72, 8), (96, 74, 4), (100, 79, 4), (104, 78, 4), (108, 74, 4),
            (112, 76, 8), (120, 78, 8)]

    def base(seg_i, kick=True, arp_open=1.0):
        s = Seg(bpm)
        for b, c in enumerate(P):
            notes = C[c]
            if kick:
                for st in (0, 4, 8, 12):
                    s.put(kit("bd_haus"), b, st, 0.7, "kick")
                for st in (4, 12):
                    s.put(kit("elec_snare"), b, st, 0.3, "snare")
                for st in (2, 6, 10, 14):
                    s.put(kit("drum_cymbal_open"), b, st, 0.07, "hat")
                for st in range(0, 16, 2):
                    s.put(kit("hat_zild") if os.path.exists(os.path.join(A, "forge/hat_zild.wav")) else
                          kit("hat_cats"), b, st + 1, 0.07, "hat")
            for st in (2, 6, 10, 14):
                s.put(saw_bass(s.S, root[c], 2, 800), b, st, 0.4, "bass")
            for st in range(16):
                m = notes[(st * 2) % 3] + 12 * ((st // 4) % 2)
                s.put(saw_lead(s.S, m, 1, 1800 + 2400 * arp_open), b, st, 0.05, "arpL" if st % 2 else "arpR")
            s.put(pad(s.S, ch(notes, 0) + [notes[0] - 12], 16, 2000, 0.05, 0.4, b + seg_i * 10, 6), b, 0, 0.16,
                  "pad")
        if kick:
            s.put(kit("drum_splash_soft"), 0, 0, 0.25, "hat")
        return s

    sends = {"lead": 0.3, "pad": 0.3, "arpL": 0.25, "arpR": 0.25, "snare": 0.15}
    delays = {"lead": (3, 0.35, 0.3, 3500)}
    duck = ("pad", "bass", "arpL", "arpR", "lead")
    G = {"bass": 0.78, "kick": 0.66, "lead": 1.6, "pad": 1.25, "arpL": 2.5, "arpR": 2.5, "hat": 1.4, "snare": 1.6}
    segs = []
    s = base(0, arp_open=0.3)
    segs.append(s.mix(sends, duck=duck, duck_depth=0.45, delays=delays, gains=G))
    s = base(1)
    s.notes(saw_lead, HOOK, 0.2, "lead")
    segs.append(s.mix(sends, duck=duck, duck_depth=0.45, delays=delays, gains=G))
    s = base(2)
    s.notes(saw_lead, [(st, m - 12, ln) for st, m, ln in HOOK], 0.16, "lead")
    s.notes(lambda S, m, ln: bell(S, m, ln), HOOK[::2], 0.08, "lead")
    segs.append(s.mix(sends, duck=duck, duck_depth=0.45, delays=delays, gains=G))
    s = base(3, kick=False, arp_open=0.6)
    s.notes(soft_lead, HOOK[:16], 0.2, "lead")
    nr = int(2 * 16 * s.S.step * SR)
    riser = dsp.bp(noise(nr, 5), 300, 8000) * np.linspace(0, 1, nr) ** 2
    s.put(sweep_lp(riser, 400, 8000), 6, 0, 0.12, "fx")
    segs.append(s.mix(sends, delays=delays, gains=G))
    return finish(segs)


# ====================================================================== 4 TRISTE (D minor, piano + strings)
def triste():
    bpm = 68
    C = {"Dm": [50, 57, 62, 65], "Bb": [46, 53, 58, 62], "Gm": [43, 55, 58, 62], "A7": [45, 55, 61, 64],
         "F": [41, 53, 57, 60], "C": [48, 55, 60, 64], "A": [45, 57, 61, 64]}
    P1 = ["Dm", "Bb", "Gm", "A7", "Dm", "F", "C", "A"]
    P2 = ["Gm", "Dm", "Bb", "A", "Gm", "Dm", "Bb", "A7"]
    MEL_B = [(0, 69, 8), (8, 65, 4), (12, 64, 4), (16, 62, 8), (24, 65, 8), (32, 67, 6), (38, 69, 2), (40, 70, 8),
             (48, 69, 12), (60, 73, 4), (64, 74, 8), (72, 72, 4), (76, 69, 4), (80, 72, 8), (88, 69, 4), (92, 65, 4),
             (96, 64, 4), (100, 67, 4), (104, 72, 8), (112, 73, 8), (120, 69, 8)]
    MEL_C = [(0, 70, 4), (4, 74, 4), (8, 79, 8), (16, 77, 8), (24, 76, 4), (28, 74, 4), (32, 74, 4), (36, 77, 4),
             (40, 70, 8), (48, 69, 8), (56, 73, 4), (60, 76, 4), (64, 74, 6), (70, 72, 2), (72, 70, 8), (80, 69, 8),
             (88, 65, 8), (96, 67, 4), (100, 65, 4), (104, 62, 8), (112, 64, 8), (120, 69, 8)]

    def base(prog, seed=0, arps=True):
        s = Seg(bpm)
        for b, c in enumerate(prog):
            notes = C[c]
            s.put(pad(s.S, notes[1:], 16, 1100, 1.2, 1.6, seed + b, 5, 0.006), b, 0, 0.2, "strings")
            s.put(soft_bass(s.S, notes[0] - 12 if notes[0] > 44 else notes[0], 15, 380), b, 0, 0.36, "bass")
            if arps:
                for st in range(0, 16, 2):
                    m = (notes[1:] + [notes[2] + 12])[[0, 1, 2, 3, 2, 1, 2, 1][st // 2]]
                    s.put(dsp.epiano(mtof(m), int(1.6 * SR)), b, st, 0.11 if st % 4 else 0.15, "piano")
            else:
                s.put(ep_chord(s.S, notes[1:], 16, 0.03), b, 0, 0.22, "piano")
        return s

    sends = {"strings": 0.5, "piano": 0.4, "lead": 0.5, "bass": 0.1}
    delays = {"lead": (6, 0.3, 0.2, 2500)}
    G = {"bass": 0.37, "lead": 1.25, "strings": 1.2}
    segs = []
    s = base(P1)
    segs.append(s.mix(sends, verb=3.2, delays=delays, gains=G))
    s = base(P1, seed=10, arps=False)
    s.notes(lambda S, m, ln: dsp.epiano(mtof(m), int((ln * S.step + 1.5) * SR)), MEL_B, 0.3, "lead")
    for b in range(8):
        s.put(dsp.epiano(mtof(C[P1[b]][1] - 12), int(2 * SR)), b, 8, 0.1, "piano")
    segs.append(s.mix(sends, verb=3.2, delays=delays, gains=G))
    s = base(P2, seed=20)
    s.notes(soft_lead, MEL_C, 0.2, "lead")
    segs.append(s.mix(sends, verb=3.2, delays=delays, gains=G))
    return finish(segs)


# ====================================================================== 5 ZANGADO (C minor, dark synthwave)
def zangado():
    bpm = 92
    C = {"Cm": [60, 63, 67], "Ab": [60, 63, 68], "Bb": [62, 65, 70], "G": [62, 67, 71], "Db": [61, 65, 68]}
    root = {"Cm": 36, "Ab": 32, "Bb": 34, "G": 31, "Db": 37}
    P1 = ["Cm", "Cm", "Ab", "Ab", "Bb", "Bb", "G", "G"]
    P2 = ["Cm", "Db", "Cm", "Bb", "Ab", "G", "Cm", "Cm"]
    LEAD = [(0, 67, 4), (4, 72, 4), (8, 75, 6), (14, 74, 2), (16, 72, 8), (24, 67, 8), (32, 68, 4), (36, 72, 4),
            (40, 75, 4), (44, 77, 4), (48, 75, 12), (60, 72, 4), (64, 74, 4), (68, 77, 4), (72, 77, 6), (78, 75, 2),
            (80, 74, 8), (88, 70, 8), (96, 71, 8), (104, 74, 4), (108, 77, 4), (112, 75, 4), (116, 74, 4),
            (120, 71, 8)]
    LEAD2 = [(0, 72, 6), (6, 75, 2), (8, 79, 8), (16, 77, 4), (20, 73, 4), (24, 72, 8), (32, 79, 4), (36, 75, 4),
             (40, 72, 8), (48, 70, 4), (52, 74, 4), (56, 77, 8), (64, 75, 4), (68, 72, 4), (72, 68, 8), (80, 67, 4),
             (84, 71, 4), (88, 74, 8), (96, 75, 8), (104, 72, 8), (112, 67, 8), (120, 72, 8)]

    def base(prog, drums=True, seed=0):
        s = Seg(bpm)
        for b, c in enumerate(prog):
            notes = C[c]
            if drums:
                for st in (0, 3, 10):
                    s.put(kit("drum_heavy_kick"), b, st, 0.6 if st == 0 else 0.42, "kick")
                s.put(kit("elec_hi_snare") if b % 2 else kit("sn_dolf") if os.path.exists(
                    os.path.join(A, "forge/sn_dolf.wav")) else kit("elec_hi_snare"), b, 8, 0.36, "snare")
                for st in range(0, 16, 2):
                    s.put(kit("hat_metal") if os.path.exists(os.path.join(A, "forge/hat_metal.wav")) else
                          kit("hat_cats"), b, st, 0.07 if st % 4 else 0.1, "hat")
            for st in range(0, 16, 2):
                s.put(reese(s.S, root[c], 2, 480 + 120 * (st % 4 == 0)), b, st, 0.42, "bass")
            for st in (0, 6, 12):
                s.put(stab(s.S, notes, 2, 2000, seed + b), b, st, 0.13, "stab")
            s.put(pad(s.S, [notes[0] - 12] + notes, 16, 900, 0.3, 0.8, seed + b, 5, 0.012), b, 0, 0.14, "pad")
        return s

    sends = {"lead": 0.3, "pad": 0.35, "stab": 0.3, "snare": 0.25}
    delays = {"lead": (3, 0.35, 0.25, 2500), "stab": (3, 0.3, 0.2, 2000)}
    duck = ("pad", "bass", "stab")
    G = {"bass": 0.56, "kick": 1.3, "lead": 1.75, "pad": 1.5, "hat": 2.5, "snare": 1.8, "stab": 3.0}
    segs = []
    s = base(P1)
    segs.append(s.mix(sends, duck=duck, duck_depth=0.35, delays=delays, gains=G))
    s = base(P1, seed=10)
    s.notes(lambda S, m, ln: saw_lead(S, m, ln, 2400), LEAD, 0.2, "lead")
    segs.append(s.mix(sends, duck=duck, duck_depth=0.35, delays=delays, gains=G))
    s = base(P2, seed=20)
    s.notes(lambda S, m, ln: saw_lead(S, m, ln, 2200), LEAD2, 0.19, "lead")
    for b in range(8):
        for st in range(16):
            m = C[P2[b]][st % 3] + 12
            s.put(chip(s.S, m, 1, 0.5, 2200), b, st, 0.035, "stab")
    segs.append(s.mix(sends, duck=duck, duck_depth=0.35, delays=delays, gains=G))
    s = base(P2, drums=False, seed=30)
    for b in range(8):
        s.put(kit("drum_tom_lo_hard"), b, 0, 0.3, "kick")
        s.put(kit("drum_tom_lo_hard"), b, 10, 0.2, "kick")
    s.notes(soft_lead, LEAD2[:12], 0.18, "lead")
    segs.append(s.mix(sends, delays=delays, gains=G))
    return finish(segs)


MOODS = [("melancolico", "MELANCÓLICO", melancolico), ("alegre", "ALEGRE", alegre),
         ("energetico", "ENERGÉTICO", energetico), ("triste", "TRISTE", triste), ("zangado", "ZANGADO", zangado)]


def main():
    want = sys.argv[1:]
    os.makedirs(OUTD, exist_ok=True)
    index = {}
    if os.path.exists(os.path.join(OUTD, "moods.json")):
        index = json.load(open(os.path.join(OUTD, "moods.json")))
    for key, label, fn in MOODS:
        if want and key not in want:
            index.setdefault(key, index.get(key))
            continue
        segs = fn()
        for f in [f for f in os.listdir(OUTD) if f.startswith(key + "_")]:
            os.remove(os.path.join(OUTD, f))
        files = []
        for i, x in enumerate(segs):
            name = "%s_%d.wav" % (key, i)
            dsp.save_mono(os.path.join(OUTD, name), x, 22050)
            files.append(name)
        index[key] = {"label": label, "files": files}
        tot = sum(len(x) for x in segs) / float(SR)
        print("%-12s %d segments, %.0f s, rms %.3f" % (key, len(segs), tot,
                                                       np.sqrt(np.mean(np.concatenate(segs) ** 2))))
    order = [k for k, _, _ in MOODS if index.get(k)]
    json.dump({"order": order, "moods": dict((k, index[k]) for k in order)}, open(os.path.join(OUTD, "moods.json"), "w"),
              ensure_ascii=True, indent=1)


if __name__ == "__main__":
    main()
