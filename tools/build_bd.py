"""BEAT DUEL: 5 original songs, each a different genre with its own instruments, scale, groove and form.
Every note is written here, so the charts are exact (no audio analysis).
Output: assets/bd/<id>.wav (22.05 kHz mono) + <id>.json (meta + charts with long notes)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_assets import A                        # noqa
from dsp import (SR, Song, mtof, saw, sq, tri, sine, noise, adsr, perc, lp, hp, bp, sweep_lp, supersaw, reverb,  # noqa
                 delay, pluck, epiano, load, fit, sidechain, master, save_mono)

OUT = os.path.join(A, "bd")


def chord_tones(root, kind):
    return [root + i for i in {"m": (0, 3, 7), "M": (0, 4, 7), "m7": (0, 3, 7, 10), "M7": (0, 4, 7, 11),
                               "7": (0, 4, 7, 10), "m9": (0, 3, 7, 10, 14), "M9": (0, 4, 7, 11, 14),
                               "13": (0, 4, 10, 14, 21)}[kind]]


def finish(song, sid, title, mix):
    y = np.zeros(song.n)
    for name, proc in mix:
        b = song.bus.get(name)
        if b is not None:
            y += proc(b)
    y = master(y)
    save_mono(os.path.join(OUT, sid + ".wav"), y)
    dur = song.bars * 16 * song.step
    meta = {"id": sid, "title": title, "artist": "ORIMBUX", "bpm": song.bpm, "duration": round(dur, 2),
            "file": sid + ".wav", "charts": song.charts()}
    json.dump(meta, open(os.path.join(OUT, sid + ".json"), "w"))
    c = meta["charts"]
    print("%-18s %3d bpm %5.1fs  easy %3d normal %3d hard %3d  holds %d" % (
        title, song.bpm, dur, len(c["easy"]), len(c["normal"]), len(c["hard"]),
        sum(1 for x in c["normal"] if len(x) > 2)))


# ====================================================================== 1. NEON DRIFT - synthwave, F# minor
def neon_drift():
    s = Song(104, 36)
    prog = [(54, "m"), (50, "M"), (57, "M"), (52, "M")]            # F#m D A E
    K, SN, HH = load("bd_klub"), load("sn_dolf"), load("drum_cymbal_closed")

    def lead(f, n, dur):
        x = (saw(f, n) + saw(f * 1.006, n) * 0.7) * adsr(n, 0.01, 0.3, 0.75, 0.12)
        return lp(x * (0.6 + 0.4 * sine(5.2, n)), 3200)

    def bassnote(f, n, dur=0):
        return lp(saw(f, n), 900) * perc(n, 0.002, 0.16)

    def arpnote(f, n, dur=0):
        return sq(f, n, 0.25) * perc(n, 0.001, 0.09)
    chorus = [(0, 73, 4), (4, 76, 2), (6, 78, 2), (8, 76, 2), (10, 73, 2), (12, 71, 4),
              (16, 69, 6), (22, 71, 2), (24, 73, 4), (28, 69, 4),
              (32, 76, 4), (36, 73, 2), (38, 76, 2), (40, 78, 4), (44, 81, 4),
              (48, 80, 8), (56, 78, 4), (60, 76, 4)]
    verse = [(0, 66, 8), (8, 69, 4), (12, 68, 4), (16, 66, 8), (24, 64, 8),
             (32, 64, 4), (36, 66, 4), (40, 69, 8), (48, 68, 12)]
    for bar in range(36):
        root, kind = prog[bar % 4]
        tones = chord_tones(root, kind)
        b0 = bar * 16
        intro, outro = bar < 4, bar >= 32
        if bar % 4 == 0 and bar < 34:                                  # pads: 4-bar swells, one chord per bar
            for k in range(4):
                r, kd = prog[k]
                n = int(SR * 16 * s.step)
                pad = sum(supersaw(mtof(m), n, 5, 0.008, seed=m) for m in chord_tones(r, kd))
                s.put(lp(pad, 1400) * adsr(n, 0.4, 0.5, 0.8, 0.5), b0 + k * 16, 0.05, "pad")
        if not outro or bar < 34:
            for k in range(16):                                        # 16th arpeggio
                m = tones[k % len(tones)] + 12 + (12 if k % 8 >= 4 else 0)
                s.put(arpnote(mtof(m), int(SR * s.step * 0.95)), b0 + k, 0.05 if intro else 0.035, "arp")
        if 4 <= bar < 32 and not (20 <= bar < 24):
            for k in range(0, 16, 2):                                  # 8th octave bass
                m = root - 24 + (12 if k % 4 == 2 else 0)
                s.put(bassnote(mtof(m), int(SR * s.step * 2)), b0 + k, 0.28, "bass")
            for k in (0, 8):
                s.put(K, b0 + k, 0.9, "drums", "kick")
            s.put(K, b0 + 10, 0.5, "drums")
            for k in (4, 12):
                s.put(SN, b0 + k, 0.7, "snare", "snare")
            for k in range(0, 16, 2):
                s.put(HH, b0 + k, 0.18 if k % 4 else 0.25, "drums")
    s.notes(verse, 4, lead, 0.12, "lead")
    s.notes(verse, 8, lead, 0.12, "lead")
    for b in (12, 16, 24, 28):
        s.notes(chorus, b, lead, 0.14, "lead")
    s.notes(chorus, 20, lambda f, n, d: epiano(f, n), 0.25, "lead")    # breakdown: melody on keys
    for b in (24, 28):                                                 # final chorus doubled an octave up
        s.notes(chorus, b, lambda f, n, d: sq(f, n, 0.125) * adsr(n, 0.005, 0.2, 0.5, 0.1), 0.04, "lead2", None, 12)
    end = 32 * 16
    n = int(SR * 4)
    s.put(sum(supersaw(mtof(m), n, 5, 0.008) for m in chord_tones(54, "m")) * adsr(n, 0.01, 1.5, 0.3, 1.5), end,
          0.08, "pad")
    s.put(K, end, 1.0, "drums", "kick")
    finish(s, "neon_drift", "NEON DRIFT", [
        ("pad", lambda b: reverb(b, 2.5, 0.35)), ("arp", lambda b: delay(b, s.step * 3, 0.45, 0.4)),
        ("bass", lambda b: b), ("drums", lambda b: b), ("snare", lambda b: reverb(b, 1.1, 0.45, damp=7000)),
        ("lead", lambda b: reverb(delay(b, s.step * 3, 0.3, 0.25), 1.6, 0.2)),
        ("lead2", lambda b: delay(b, s.step * 2, 0.3, 0.3))])


# ====================================================================== 2. PIXEL RUSH - chiptune, C major -> D major
def pixel_rush():
    s = Song(150, 40)
    A = [(0, 76, 2), (2, 79, 2), (4, 84, 4), (8, 83, 2), (10, 79, 2), (12, 76, 4),
         (16, 74, 2), (18, 79, 2), (20, 83, 4), (24, 81, 2), (26, 79, 2), (28, 74, 4),
         (32, 72, 2), (34, 76, 2), (36, 81, 4), (40, 79, 2), (42, 76, 2), (44, 72, 4),
         (48, 77, 4), (52, 76, 2), (54, 74, 2), (56, 72, 4), (60, 74, 4)]
    B = [(0, 81, 6), (6, 79, 2), (8, 77, 4), (12, 81, 4), (16, 83, 6), (22, 81, 2), (24, 79, 4), (28, 74, 4),
         (32, 79, 4), (36, 76, 4), (40, 71, 4), (44, 76, 4), (48, 81, 8), (56, 83, 2), (58, 84, 2), (60, 83, 4)]
    progA = [(60, "M"), (55, "M"), (57, "m"), (53, "M")]
    progB = [(53, "M"), (55, "M"), (52, "m"), (57, "m")]
    progC = [(50, "m"), (55, "M"), (60, "M"), (60, "M")]

    def p1(f, n, d):
        return sq(f, n, 0.25, vib=0.006, vdelay=0.12) * adsr(n, 0.002, 0.08, 0.8, 0.03)

    def p2(f, n, d):
        return sq(f, n, 0.125) * adsr(n, 0.002, 0.05, 0.6, 0.02)

    def kick_c(n=int(SR * 0.12)):
        t = np.arange(n) / SR
        return np.sign(np.sin(2 * np.pi * np.cumsum(180 * np.exp(-t * 30) + 50) / SR)) * np.exp(-t * 25)

    def noise_hit(n, cut, dec, seed):
        x = np.sign(noise(n, seed))                        # 1-bit noise like the NES noise channel
        return lp(x, cut) * perc(n, 0.001, dec)
    KC = kick_c()
    SNC = noise_hit(int(SR * 0.12), 6000, 0.05, 2)
    HHC = noise_hit(int(SR * 0.03), 12000, 0.008, 3)

    def section(bar0, prog, mel, transpose=0, harmony=False, half=False):
        for k in range(8):
            bar = bar0 + k
            root, kind = prog[k % 4]
            root += transpose
            tones = chord_tones(root, kind)
            b0 = bar * 16
            for st in range(0, 16, 2):                      # triangle bass bouncing octaves
                m = root - 12 - (12 if st % 4 == 0 else 0)
                n = int(SR * s.step * 1.6)
                s.put(tri(mtof(m), n) * adsr(n, 0.001, 0.1, 0.9, 0.01), b0 + st, 0.32, "bass")
            for st in range(0, 16):                         # 3-note chip "chord" arpeggio, 32nd notes
                for h in range(2):
                    m = tones[(st * 2 + h) % 3] + 12
                    n = int(SR * s.step / 2)
                    s.put(sq(mtof(m), n, 0.125) * 0.9, b0 + st + h * 0.5, 0.028, "arp")
            ks, ss = ((0, 8), (12,)) if half else ((0, 6, 8), (4, 12))
            for st in ks:
                s.put(KC, b0 + st, 0.35, "drums", "kick")
            for st in ss:
                s.put(SNC, b0 + st, 0.3, "drums", "snare")
            for st in range(0, 16, 1 if not half else 2):
                s.put(HHC, b0 + st, 0.12, "drums")
        s.notes(mel, bar0, p1, 0.11, "lead", transpose=transpose)
        s.notes(mel, bar0 + 4, p1, 0.11, "lead", transpose=transpose)
        if harmony:
            s.notes(mel, bar0 + 4, p2, 0.05, "lead2", None, transpose - 4)
    # intro jingle: rising arpeggio run
    for k in range(32):
        m = [60, 64, 67, 72][k % 4] + 12 * (k // 8)
        n = int(SR * s.step / 2)
        s.put(sq(mtof(m), n, 0.25), k * 0.5, 0.08, "lead", "stab" if k % 8 == 0 else None, m)
    s.put(KC, 16, 0.4, "drums", "kick")
    section(2, progA, A)
    section(10, progB, B)
    section(18, progA, A, harmony=True)
    # bridge: half-time, melody on the triangle
    for k in range(4):
        root, kind = progC[k]
        b0 = (26 + k) * 16
        n = int(SR * 16 * s.step)
        s.put(sq(mtof(root), n, 0.5) * adsr(n, 0.01, 0.4, 0.4, 0.2), b0, 0.04, "arp")
        s.put(KC, b0, 0.35, "drums", "kick")
        s.put(SNC, b0 + 8, 0.3, "drums", "snare")
    s.notes([(0, 74, 8), (8, 77, 8), (16, 79, 12), (28, 76, 4), (32, 72, 8), (40, 74, 8), (48, 76, 16)], 26,
            lambda f, n, d: tri(f, n) * adsr(n, 0.01, 0.2, 0.9, 0.05), 0.2, "lead")
    s.put(noise_hit(int(SR * s.step * 16), 9000, 2.0, 9) * np.linspace(0, 1, int(SR * s.step * 16)), 29 * 16, 0.2,
          "drums")
    section(30, progA, A, transpose=2, harmony=True)              # key change up a tone
    # ending: big chord + sweep
    n = int(SR * 2.4)
    for m in (62, 66, 69, 74):
        s.put(sq(mtof(m), n, 0.25) * adsr(n, 0.005, 0.6, 0.5, 1.0), 38 * 16, 0.06, "lead2")
    s.put(KC, 38 * 16, 0.5, "drums", "kick")
    finish(s, "pixel_rush", "PIXEL RUSH", [
        ("bass", lambda b: b), ("arp", lambda b: b), ("drums", lambda b: b),
        ("lead", lambda b: delay(b, s.step * 3, 0.25, 0.2)), ("lead2", lambda b: b)])


# ====================================================================== 3. VOID BASS - drum & bass, D minor
def void_bass():
    s = Song(174, 48)
    bar_n = int(SR * 16 * s.step)
    amen = load("loop_amen")
    amen_bar = fit(amen, bar_n)                                     # one bar of break at 174 (jungle-style pitch up)
    KB, SNB = load("bd_klub"), load("sn_zome")
    prog = [(50, "m"), (46, "M"), (48, "M"), (45, "m")]             # Dm Bb C Am, 2 bars each
    hook = [(0, 74, 3), (3, 77, 3), (6, 81, 2), (8, 79, 4), (12, 77, 2), (14, 76, 2),
            (16, 74, 6), (22, 72, 2), (24, 69, 8)]
    hook2 = [(0, 81, 3), (3, 79, 3), (6, 77, 2), (8, 76, 4), (12, 74, 4), (16, 77, 6), (22, 76, 2), (24, 74, 8)]

    def reese(f, n, open_=1.0):
        x = saw(f, n) + saw(f * 1.011, n) + saw(f * 0.993, n) * 0.6
        lfo = 500 + 900 * open_ * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR * 1.6))
        return sweep_lp(x, lfo[::512], None) * 0.5

    def pl(f, n, d):
        return pluck(f, n, 0.997, seed=int(f)) * 1.4

    def stab(f, n, d):
        return sq(f, n, 0.5) * perc(n, 0.001, 0.12)
    for bar in range(48):
        b0 = bar * 16
        root, kind = prog[(bar // 2) % 4]
        intro, build, drop1, brk, build2, drop2, _ = (bar < 8, 8 <= bar < 12, 12 <= bar < 28, 28 <= bar < 32,
                                                        32 <= bar < 34, 34 <= bar < 46, bar >= 46)
        if intro or brk:
            if bar % 2 == 0:
                n = bar_n * 2
                pad = sum(supersaw(mtof(m), n, 5, 0.01, seed=m) for m in chord_tones(root, kind))
                s.put(lp(pad, 900) * adsr(n, 0.6, 0.5, 0.8, 0.6), b0, 0.05, "pad")
            if intro and bar >= 4:
                s.put(lp(amen_bar, 1200), b0, 0.5, "break")
        if build or build2:
            steps = range(0, 16, 4 if bar % 2 == 0 else 2) if build else range(0, 16, 1)
            for st in steps:
                s.put(SNB, b0 + st, 0.25 + 0.03 * st / 2, "drums", "snare" if st % 4 == 0 else None)
            if bar in (8, 32):
                n = bar_n * (4 if build else 2)
                s.put(bp(noise(n, 4), 800, 6000) * np.linspace(0, 1, n) ** 2, b0, 0.25, "fx")
        if drop1 or drop2:
            s.put(amen_bar, b0, 0.45, "break")
            for st in (0, 10):
                s.put(KB, b0 + st, 0.9, "drums", "kick")
            for st in (4, 12):
                s.put(SNB, b0 + st, 0.75, "drums", "snare")
            if bar % 2 == 0:
                n = bar_n * 2
                s.put(reese(mtof(root - 24), n, 1.0 if drop2 else 0.6) * adsr(n, 0.01, 0.3, 0.9, 0.1), b0, 0.3, "bass")
                s.put(sine(mtof(root - 24), n) * adsr(n, 0.01, 0.3, 0.9, 0.1), b0, 0.35, "sub")
            if drop2:
                for st in (2, 6, 14):
                    s.put(stab(mtof(root + 12), int(SR * s.step * 2), 0), b0 + st, 0.06, "stab", "stab", root)
    for b in (16, 20, 24):
        s.notes(hook, b, pl, 0.22, "lead")
        s.notes(hook2, b + 2, pl, 0.22, "lead")
    s.notes(hook, 28, lambda f, n, d: epiano(f, n), 0.25, "lead")
    s.notes(hook2, 30, lambda f, n, d: epiano(f, n), 0.25, "lead")
    for b in (36, 40):
        s.notes(hook, b, pl, 0.24, "lead", transpose=12)
        s.notes(hook2, b + 2, pl, 0.24, "lead", transpose=12)
    end = 46 * 16
    s.put(KB, end, 1.0, "drums", "kick")
    n = int(SR * 3)
    s.put(lp(supersaw(mtof(38), n, 7, 0.02), 600) * adsr(n, 0.01, 1.5, 0.2, 1.4), end, 0.2, "bass")
    finish(s, "void_bass", "VOID BASS", [
        ("pad", lambda b: reverb(b, 3.0, 0.45)), ("break", lambda b: hp(b, 120)), ("drums", lambda b: b),
        ("bass", lambda b: b), ("sub", lambda b: lp(b, 150)), ("fx", lambda b: reverb(b, 2.0, 0.3)),
        ("stab", lambda b: delay(b, s.step * 3, 0.4, 0.4)), ("lead", lambda b: reverb(b, 2.2, 0.3))])


# ====================================================================== 4. MOON HOP - lo-fi hip hop, Eb major (jazzy)
def moon_hop():
    s = Song(82, 24, swing=0.32)
    KB, SN, HH = load("bd_boom"), load("sn_dolf"), load("hat_zild")
    chords = [[56, 60, 63, 67], [56, 62, 67, 70], [55, 58, 62, 65], [55, 58, 63, 62 + 12]]   # Fm9 Bb13 Ebmaj9 Cm9
    roots = [41, 46, 39, 48]
    mel = [(0, 72, 6), (6, 75, 2), (8, 77, 4), (12, 75, 4), (16, 74, 8), (24, 72, 4), (28, 70, 4),
           (32, 67, 4), (36, 70, 4), (40, 74, 6), (46, 75, 2), (48, 72, 12)]
    mel2 = [(0, 75, 4), (4, 77, 4), (8, 79, 8), (16, 77, 6), (22, 74, 2), (24, 70, 8),
            (32, 74, 4), (36, 75, 4), (40, 79, 4), (44, 77, 4), (48, 75, 16)]

    def flute(f, n, d):
        x = sine(f, n, vib=0.004, vr=4.5) + 0.25 * sine(2 * f, n) + 0.04 * lp(noise(n, int(f)), 3000)
        return x * adsr(n, 0.06, 0.3, 0.8, 0.15)
    for bar in range(24):
        b0 = bar * 16
        k = bar % 4
        intro = bar < 2
        brk = 18 <= bar < 20
        n = int(SR * 16 * s.step)
        keys = sum(epiano(mtof(m), n) for m in chords[k])
        s.put(keys, b0, 0.13, "keys", "stab" if not intro else None, roots[k])
        s.put(sum(epiano(mtof(m), int(SR * 6 * s.step)) for m in chords[k][1:]), b0 + 10, 0.07, "keys")
        if not intro and not brk:
            for st, ln, off in ((0, 6, 0), (6, 2, 7), (8, 4, 12), (14, 2, 10)):     # walking-ish upright bass
                nn = int(SR * s.step * ln)
                m = roots[k] - 12 + off
                s.put(lp(sine(mtof(m), nn) + 0.3 * tri(mtof(m), nn), 700) * perc(nn, 0.004, 0.35), b0 + st, 0.38,
                      "bass")
            for st in (0, 10):
                s.put(KB, b0 + st, 0.85, "drums", "kick")
            s.put(KB, b0 + 7, 0.4, "drums")
            for st in (4, 12):
                s.put(SN, b0 + st, 0.6, "drums", "snare")
            for st in range(0, 16, 2):
                s.put(HH, b0 + st, 0.22 if st % 4 == 0 else 0.14, "drums")
    s.notes(mel, 10, flute, 0.16, "lead")
    s.notes(mel2, 14, flute, 0.16, "lead")
    s.notes(mel, 18, flute, 0.12, "lead")
    s.notes(mel2, 20, lambda f, n, d: epiano(f, n), 0.3, "lead")
    # vinyl crackle over everything
    crackle = np.zeros(s.n)
    rng = np.random.RandomState(5)
    idx = rng.randint(0, s.n, s.n // 1800)
    crackle[idx] = rng.uniform(-1, 1, len(idx))
    crackle = hp(crackle, 1500) + lp(noise(s.n, 6), 4000) * 0.02
    s.bus["vinyl"] = crackle

    def wobble(x):                                                 # tape wow: slow pitch drift of the whole mix
        t = np.arange(len(x))
        warp = t + 0.0018 * SR * np.sin(2 * np.pi * t / SR * 0.55)
        return np.interp(np.clip(warp, 0, len(x) - 1), t, x)
    finish(s, "moon_hop", "MOON HOP", [
        ("keys", lambda b: wobble(lp(reverb(b, 1.6, 0.25), 5000))), ("bass", lambda b: b),
        ("drums", lambda b: lp(b, 7000)), ("lead", lambda b: wobble(reverb(delay(b, s.step * 6, 0.3, 0.25), 2.0, 0.3))),
        ("vinyl", lambda b: b * 0.12)])


# ====================================================================== 5. MOTHERSHIP ANTHEM - big room house, A minor
def anthem():
    s = Song(128, 36)
    K, CL1, CL2 = load("bd_haus"), load("perc_snap"), load("sn_generic")
    OH, CH = load("drum_cymbal_open"), load("drum_cymbal_closed")
    CR = load("drum_cymbal_hard")
    prog = [(57, "m"), (53, "M"), (60, "M"), (55, "M")]             # Am F C G
    hook = [(0, 69, 3), (3, 72, 3), (6, 76, 2), (8, 74, 3), (11, 72, 3), (14, 71, 2),
            (16, 69, 3), (19, 72, 3), (22, 77, 2), (24, 76, 4), (28, 72, 4),
            (32, 67, 3), (35, 72, 3), (38, 76, 2), (40, 79, 4), (44, 76, 4),
            (48, 74, 6), (54, 71, 2), (56, 67, 8)]

    def saw_lead(f, n, d):
        return (supersaw(f, n, 7, 0.016, seed=int(f)) + 0.5 * supersaw(f * 2, n, 5, 0.01)) * adsr(n, 0.004, 0.2, 0.8, 0.08)
    sections = {"intro": range(0, 4), "build": range(4, 8), "drop": range(8, 20), "break": range(20, 24),
                "build2": range(24, 28), "drop2": range(28, 36)}

    def sec(bar):
        for k, r in sections.items():
            if bar in r:
                return k
    for bar in range(36):
        b0 = bar * 16
        root, kind = prog[bar % 4]
        tones = chord_tones(root, kind)
        sc = sec(bar)
        n = int(SR * 16 * s.step)
        if sc in ("intro", "drop", "drop2"):
            for st in (0, 4, 8, 12):
                s.put(K, b0 + st, 0.95, "drums", "kick")
        if sc in ("drop", "drop2", "intro"):
            for st in (2, 6, 10, 14):
                s.put(OH, b0 + st, 0.12 if sc == "intro" else 0.2, "hats")
            for st in range(0, 16):
                s.put(CH, b0 + st, 0.06, "hats")
        if sc in ("drop", "drop2"):
            for st in (4, 12):
                s.put(CL1, b0 + st, 0.6, "drums", "snare")
                s.put(CL2, b0 + st, 0.35, "drums")
            for st in (2, 6, 10, 14):                                   # offbeat rolling bass
                nn = int(SR * s.step * 2)
                s.put(lp(saw(mtof(root - 24), nn) + saw(mtof(root - 12), nn) * 0.4, 1200) * perc(nn, 0.002, 0.18),
                      b0 + st, 0.35, "bass")
            chords = sum(supersaw(mtof(m), n, 7, 0.014, seed=m) for m in tones)
            s.put(lp(chords, 4500) * adsr(n, 0.005, 0.3, 0.8, 0.1), b0, 0.06, "chords", "stab", root)
        if sc in ("build", "build2"):
            k = bar - sections[sc][0]
            chords = sum(supersaw(mtof(m), n, 7, 0.014, seed=m) for m in tones)
            s.put(sweep_lp(chords, 300 + 600 * k, 900 + 900 * k) * adsr(n, 0.05, 0.3, 0.9, 0.05), b0, 0.06, "chords")
            step = [4, 2, 1, 0.5][k]
            st = 0.0
            while st < 16:                                              # snare roll speeding up
                s.put(CL2 * (0.5 + 0.12 * k), b0 + st, 0.3 + 0.1 * k, "drums", "snare" if step >= 2 else None)
                st += step
            if k == 0:
                nr = int(SR * 64 * s.step)
                s.put(bp(noise(nr, 8), 500, 9000) * np.linspace(0, 1, nr) ** 3, b0, 0.25, "fx")
        if sc == "break":
            pad = sum(supersaw(mtof(m), n, 5, 0.01, seed=m) for m in tones)
            s.put(lp(pad, 1500) * adsr(n, 0.3, 0.5, 0.8, 0.3), b0, 0.05, "pad")
    for b in (8, 12, 16):
        s.notes(hook, b, saw_lead, 0.07, "lead")
    s.notes(hook, 20, lambda f, n, d: epiano(f, n) + 0.3 * pluck(f, n, 0.998, int(f)), 0.28, "lead")
    for b in (28, 32):
        s.notes(hook, b, saw_lead, 0.07, "lead")
        s.notes(hook, b, saw_lead, 0.035, "lead2", None, 12)
    for b in (8, 28):
        s.put(CR, b * 16, 0.4, "hats")
    end = 36 * 16
    s.put(K, end, 1.0, "drums", "kick")
    s.put(CR, end, 0.5, "hats")
    nn = int(SR * 2.5)
    s.put(sum(supersaw(mtof(m), nn, 7, 0.014) for m in chord_tones(57, "m")) * adsr(nn, 0.005, 1.2, 0.2, 1.2), end,
          0.08, "chords")
    side = sidechain(s.n, s.kick_times(), 0.65, 0.11)
    finish(s, "mothership_anthem", "MOTHERSHIP ANTHEM", [
        ("drums", lambda b: b), ("hats", lambda b: hp(b, 300)), ("bass", lambda b: b * side),
        ("chords", lambda b: reverb(b, 1.5, 0.2) * side), ("pad", lambda b: reverb(b, 2.5, 0.35)),
        ("fx", lambda b: b), ("lead", lambda b: reverb(delay(b, s.step * 3, 0.3, 0.2), 1.6, 0.18) * (0.5 + 0.5 * side)),
        ("lead2", lambda b: reverb(b, 1.6, 0.2) * side)])


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    for name, fn in (("neon_drift", neon_drift), ("pixel_rush", pixel_rush), ("void_bass", void_bass),
                     ("moon_hop", moon_hop), ("anthem", anthem)):
        if not only or name in only:
            fn()


if __name__ == "__main__":
    main()
