"""Trailer build: the soundtrack (made from the Mothership's own sounds) + the app footage as 8-bit frames.
  python3 tools/build_trailer.py [music] [frames] [credits]
Bar map (140 BPM, 1 bar = 1.714 s, 45 bars = 77 s + tail):
  0-1 signal | 2-3 approach | 4-5 the jump | 6-7 logo | 8-9 chapter MUSICA | 10-25 eight music apps x 2 bars
  26-27 chapter JOGOS | 28-35 four games x 2 bars | 36-37 mosaic | 38-39 launch | 40-43 final chorus + logo | 44 end"""
import os
import struct
import subprocess
import sys
import zlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa
from dsp import SR, Song, mtof, saw, sq, sine, noise, perc, adsr, lp, hp, sweep_lp, supersaw, reverb, delay  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
A = os.path.join(APPD, "assets")
OUTD = os.path.join(A, "trailer")
BUILD = os.path.join(ROOT, "tools", "build")
APPS = ["pulsar", "forge", "abductor", "reactor", "xeno", "vox", "decks", "warp", "pet", "quiz", "voidrunner",
        "beatduel"]
BPM = 140


def wav(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def a(rel):
    return wav(os.path.join(A, rel))


def pitch(x, semis):
    return dsp.fit(x, max(2, int(len(x) / 2 ** (semis / 12.0))))


def xeno_osc(table, f, n):
    ph = np.cumsum(np.full(n, f / SR)) % 1.0
    idx = ph * len(table)
    i0 = idx.astype(int) % len(table)
    fr = idx - np.floor(idx)
    return table[i0] * (1 - fr) + table[(i0 + 1) % len(table)] * fr


# ====================================================================== music
# bar map (140 BPM, 1 bar = 1.714 s), shared with trailer.py
B_APPROACH, B_HYPER, B_LOGO, B_CHM, B_MUSIC, B_CHG, B_GAMES, B_MOSAIC, B_LAUNCH, B_FINAL, B_END = \
    2, 4, 6, 8, 10, 26, 28, 36, 38, 40, 44
NBARS = 45


def music():
    S = Song(BPM, NBARS, tail=3.0)
    bar = 16
    # ---- the ship's sound bank
    kick, boom, cine = a("forge/bd_haus.wav"), a("forge/bd_boom.wav"), a("forge/misc_cineboom.wav")
    snare, clap = a("forge/sn_dolf.wav"), a("forge/perc_snap.wav")
    hat, ohat, crash = a("forge/hat_zild.wav"), a("forge/drum_cymbal_open.wav"), a("forge/drum_splash_hard.wav")
    toms = [a("forge/drum_tom_hi_hard.wav"), a("forge/drum_tom_mid_hard.wav"), a("forge/drum_tom_lo_hard.wav")]
    ping, chime = a("forge/elec_ping.wav"), a("forge/elec_chime.wav")
    click_hi, click_lo = a("click_hi.wav"), a("click_lo.wav")
    amen = dsp.fit(a("samples/loop_amen.wav"), int(bar * S.step * SR))
    anthem = a("bd/mothership_anthem.wav")
    xtab = np.frombuffer(open(os.path.join(A, "synth", "xeno_o4_b.raw"), "rb").read(), dtype="<i2") / 32768.0
    choir, robot = dsp.load("ambi_choir"), a("samples/glitch_robot1.wav")
    scratch, backspin = a("forge/vinyl_scratch.wav"), dsp.load("vinyl_backspin")
    ep = a("ear/ep_60.wav")
    chirp, happy, star = a("pet/chirp.wav"), a("pet/happy.wav"), a("pet/star.wav")
    zap, vboom, bolt = a("vr/zap.wav"), a("vr/boom.wav"), a("vr/bolt.wav")
    drone, lunar, glass = dsp.load("ambi_drone"), dsp.load("ambi_lunar_land"), dsp.load("ambi_glass_hum")
    roll = a("forge/drum_roll.wav")
    kicks = []                                  # kick times for the sidechain

    CH = [(41, [53, 56, 60, 65]), (37, [49, 53, 56, 60]), (44, [51, 56, 60, 63]), (39, [51, 55, 58, 63])]  # Fm Db Ab Eb
    FIXED = {6: 0, 7: 1, 8: 2, 9: 3, B_CHG: 1, B_CHG + 1: 3, B_END: 0}

    def chord(b):
        if b in FIXED:
            return CH[FIXED[b]]
        for b0 in (B_FINAL, B_MOSAIC, B_GAMES, B_MUSIC):
            if b >= b0:
                return CH[(b - b0) % 4]
        return CH[0]

    def put(sig, b, s, vol, bus):
        S.put(sig, b * bar + s, vol, bus)
        if bus == "kick" and vol >= 0.6:
            kicks.append(S.t(b * bar + s))

    def pad_chord(notes, nsteps, cutoff, seed=0):
        n = int(nsteps * S.step * SR) + int(0.4 * SR)
        y = sum(supersaw(mtof(m), n, 5, 0.01, seed + i) for i, m in enumerate(notes))
        return lp(y, cutoff) * adsr(n, 0.08, 0.3, 0.8, 0.35)

    def bass_note(m, nsteps, cut=900):
        n = int(nsteps * S.step * SR)
        y = saw(mtof(m), n) * 0.6 + sq(mtof(m - 12), n) * 0.4
        return lp(y, cut, 2) * adsr(n, 0.004, 0.08, 0.7, 0.03)

    def chip_bass(m, nsteps):
        n = int(nsteps * S.step * SR)
        return lp(sq(mtof(m), n, 0.25) * 0.7 + sq(mtof(m - 12), n, 0.5) * 0.3, 2400) * adsr(n, 0.002, 0.05, 0.6, 0.02)

    def reese(m, nsteps):
        n = int(nsteps * S.step * SR)
        y = saw(mtof(m) * 0.995, n) + saw(mtof(m) * 1.006, n, 0.3)
        return lp(y, 700, 2) * adsr(n, 0.01, 0.1, 0.9, 0.05) * 0.6

    def lead(m, nsteps):
        n = int(nsteps * S.step * SR) + int(0.15 * SR)
        y = saw(mtof(m), n) * 0.5 + saw(mtof(m) * 1.004, n, 0.5) * 0.5
        return lp(y, 3200) * adsr(n, 0.01, 0.2, 0.75, 0.12)

    def xlead(m, nsteps):
        n = int(nsteps * S.step * SR) + int(0.12 * SR)
        f = mtof(m)
        y = xeno_osc(xtab, f, n) * 0.6 + xeno_osc(xtab, f * 2.001, n) * 0.2
        return lp(y, 4200) * adsr(n, 0.006, 0.15, 0.8, 0.1)

    def chip_lead(m, nsteps):
        n = int(nsteps * S.step * SR) + int(0.05 * SR)
        return sq(mtof(m), n, 0.25, vib=0.004, vdelay=0.12) * adsr(n, 0.002, 0.1, 0.7, 0.05)

    def bell(m, ln=1.5):
        return pitch(ep, m - 60)[:int(ln * SR)]

    def stab(notes, n=0.35, seed=3):
        k = int(n * SR)
        y = sum(supersaw(mtof(m), k, 5, 0.012, seed + i) for i, m in enumerate(notes))
        return lp(y, 5000) * perc(k, 0.002, 0.12)

    def choir_to(root):                 # the choir sample sings ~Eb5 (midi 75)
        k = (root - 75) % 12
        return pitch(choir, k - 12 if k > 6 else k)

    def riser(b, nbars, seed, lo=300, hi=9000, vol=0.35, curve=2):
        nr = int(nbars * bar * S.step * SR)
        r = dsp.bp(noise(nr, seed), 200, 10000) * np.linspace(0, 1, nr) ** curve
        put(sweep_lp(r, lo, hi), b, 0, vol, "fx")

    def rev_crash(b, vol=0.42):         # reversed crash ending on bar b
        rc = crash[::-1][-int(0.9 * SR):]
        put(rc, b - 1, 16 - int(0.9 / S.step), vol, "fx")

    def groove(b, hats=True, clap_on=True, bass="saw", open_hats=False):
        root, notes = chord(b)
        for s in (0, 4, 8, 12):
            put(kick, b, s, 0.95, "kick")
        for s in (2, 6, 10, 14):
            m = root + (12 if s == 10 and b % 2 else 0)
            if bass == "reese":
                put(reese(m, 2), b, s, 0.6, "bass")
            elif bass == "chip":
                put(chip_bass(m + 12, 2), b, s, 0.4, "bass")
            else:
                put(bass_note(m, 2), b, s, 0.55, "bass")
        if clap_on:
            for s in (4, 12):
                put(clap, b, s, 0.5, "snare")
                put(snare, b, s, 0.35, "snare")
        if hats:
            for s in (2, 6, 10, 14):
                put(hat, b, s, 0.28, "hat")
        if open_hats:
            for s in range(0, 16, 2):
                put(hat, b, s + 1, 0.12, "hat")

    def arps(b, vol=0.07):
        notes = chord(b)[1]
        for i in range(16):
            m = notes[(i * 3) % 4] + 12 * (1 + (i // 4) % 2)
            nn = int(S.step * 0.8 * SR)
            put(sq(mtof(m), nn, 0.3) * perc(nn, 0.002, 0.06), b, i, vol, "arpL" if i % 2 else "arpR")

    HOOK = [(0, 72, 3), (3, 75, 3), (6, 77, 2), (8, 80, 4), (12, 79, 2), (14, 77, 2),
            (16, 80, 3), (19, 77, 3), (22, 75, 2), (24, 77, 8),
            (32, 75, 3), (35, 72, 3), (38, 75, 2), (40, 80, 4), (44, 82, 4),
            (48, 79, 4), (52, 80, 4), (56, 84, 8)]

    # ------------------------------------------------------------ 0-5: a signal, the ship, the jump
    put(lunar[:int(9 * SR)], 0, 0, 0.55, "amb")
    put(drone[:int(9 * SR)] if len(drone) > 9 * SR else drone, 0, 0, 0.45, "amb")
    for b, steps in ((0, (0, 6, 12)), (1, (0, 6, 10, 12)), (2, (0, 6, 12)), (3, (0, 3, 6, 9, 12, 14))):
        for s in steps:
            put(pitch(ping, 12 if s % 2 else 7), b, s, 0.32, "ping")
    n_sub = int(6 * bar * S.step * SR)
    put(sine(mtof(29), n_sub) * np.linspace(0, 1, n_sub) ** 2, 0, 0, 0.5, "sub")
    pad_in = pad_chord(CH[0][1], 6 * bar, 4000)
    put(sweep_lp(pad_in, 220, 3600) * np.linspace(0.2, 1, len(pad_in)), 0, 0, 0.22, "pad")
    for b in (2, 3):                                     # heartbeat
        put(boom, b, 0, 0.45, "sub")
        put(boom, b, 3, 0.25, "sub")
    arp_notes = [CH[0][1][i % 4] + 12 * (i // 4 % 2) for i in range(8)]
    arp_len = int(4 * bar * S.step * SR) + SR
    arp_buf = np.zeros(arp_len)
    for i in range(4 * bar):
        k = int(i * S.step * SR)
        nn = int(S.step * 0.9 * SR)
        arp_buf[k:k + nn] += sq(mtof(arp_notes[i % 8] + 12), nn, 0.25) * perc(nn, 0.002, 0.08)
    put(sweep_lp(arp_buf, 250, 7000), 2, 0, 0.13, "arp")
    for b in (B_HYPER, B_HYPER + 1):                     # the jump: kick + accelerating snare
        for s in range(0, 16, 4):
            put(kick, b, s, 0.7, "kick")
    for s in range(0, 16, 4):
        put(snare, B_HYPER, s, 0.18, "snare")
    for s in range(0, 8, 2):
        put(snare, B_HYPER + 1, s, 0.25 + 0.03 * s, "snare")
    for s in range(8, 16):
        put(snare, B_HYPER + 1, s, 0.35 + 0.03 * (s - 8), "snare")
    for i, s in enumerate((12, 13, 14, 15)):
        put(toms[min(2, i)], B_HYPER + 1, s, 0.45, "snare")
    riser(B_HYPER, 2, 4)
    rev_crash(B_LOGO)

    # ------------------------------------------------------------ 6-7: the logo (half time)
    put(boom, B_LOGO, 0, 1.0, "kick")
    put(cine, B_LOGO, 0, 0.6, "fx")
    put(crash, B_LOGO, 0, 0.55, "cym")
    for b in (B_LOGO, B_LOGO + 1):
        root, notes = chord(b)
        put(pad_chord(notes + [notes[0] + 12], bar, 5000, b), b, 0, 0.26, "pad")
        put(choir_to(root), b, 0, 0.32, "choir")
        put(bass_note(root, 6), b, 0, 0.5, "bass")
        put(bass_note(root, 4), b, 10, 0.4, "bass")
        if b > B_LOGO:
            put(kick, b, 0, 0.8, "kick")
        put(kick, b, 10, 0.6, "kick")
        put(snare, b, 8, 0.55, "snare")
        put(clap, b, 8, 0.35, "snare")
        for s in (2, 6, 10, 14):
            put(hat, b, s, 0.18, "hat")
    for s in range(12, 16):
        put(snare, B_LOGO + 1, s, 0.3 + 0.06 * (s - 12), "snare")
    put(sine(mtof(29), int(2.5 * SR)) * np.linspace(1, 0, int(2.5 * SR)), B_LOGO, 0, 0.45, "sub")

    # ------------------------------------------------------------ 8-9: chapter MUSICA (eight steps, eight pings)
    put(crash, B_CHM, 0, 0.4, "cym")
    scale = [65, 67, 68, 70, 72, 73, 75, 77]
    for i in range(8):
        b, s = B_CHM + i // 4, (i % 4) * 4
        put(pitch(ping, scale[i] - 72), b, s, 0.32, "ping")
        put(bell(scale[i] + 12, 0.8), b, s, 0.12, "bell")
    for b in (B_CHM, B_CHM + 1):
        groove(b, hats=b > B_CHM, clap_on=True)
        put(pad_chord(chord(b)[1], bar, 2200, b), b, 0, 0.12, "pad")
    riser(B_CHM + 1, 1, 6, vol=0.25)

    # ------------------------------------------------------------ 10-25: the eight music apps
    for b in range(B_MUSIC, B_MUSIC + 16):
        k = b - B_MUSIC
        groove(b, hats=k >= 2, open_hats=(2 <= k <= 3 or k >= 10), clap_on=k >= 2)
        if k >= 4:
            put(pad_chord(chord(b)[1], bar, 1800 if k < 12 else 3200, b), b, 0, 0.12 if k < 12 else 0.16, "pad")
        if k >= 6:
            arps(b)
        if k in (0, 4, 8, 12):
            put(crash, b, 0, 0.35, "cym")
    m0 = B_MUSIC
    for b in (m0, m0 + 1):                                     # 1 PULSAR: the metronome
        for s in (0, 4, 8, 12):
            put(click_hi if s == 0 else click_lo, b, s, 0.8, "click")
    for i, s in enumerate((12, 13, 14, 15)):                    # 2 BEAT FORGE: tom fill
        put(toms[min(2, i)], m0 + 3, s, 0.5, "snare")
    src = pitch(anthem[int(31.0 * SR):int(33.5 * SR)], -4)       # 3 ABDUCTOR: anthem slices
    sl = int(2 * S.step * SR)
    for b in (m0 + 4, m0 + 5):
        for s, k in [(0, 0), (3, 1), (6, 2), (8, 0), (10, 3), (12, 4), (14, 4), (15, 5)]:
            put(src[k * sl:(k + 1) * sl] * np.minimum(1, np.linspace(8, 0, sl)), b, s, 0.55, "chop")
    for b in (m0 + 6, m0 + 7):                                  # 4 LOOP REACTOR: the amen
        put(hp(amen, 180), b, 0, 0.42, "amen")
    for s, m, ln in HOOK:                                       # 5 XENO + 6 VOX: the hook; 7 + 8 on leads
        put(xlead(m, ln), m0 + 8 + s // 16, s % 16, 0.3, "lead")
        put(lead(m, ln), m0 + 12 + s // 16, s % 16, 0.26, "lead")
        put(lead(m - 12, ln), m0 + 12 + s // 16, s % 16, 0.12, "lead")
    for b in (m0 + 10, m0 + 11):
        put(choir_to(chord(b)[0]), b, 0, 0.4, "choir")
    put(robot, m0 + 10, 0, 0.4, "chop")
    for s, cut in ((0, 0.18), (2, 0.09), (3, 0.09), (6, 0.18), (8, 0.12), (11, 0.12)):   # 7 TWIN DECKS
        seg = scratch[:int(cut * SR)]
        put(seg if s % 3 else seg[::-1], m0 + 12, s, 0.55, "scratch")
    put(backspin[:int(1.0 * SR)], m0 + 13, 10, 0.5, "scratch")
    for b in (m0 + 14, m0 + 15):                                # 8 WARP FLOOR: the lift
        for s in (2, 6, 10, 14):
            put(ohat, b, s, 0.12, "hat")
    for s in range(8, 16):
        put(snare, m0 + 15, s, 0.2 + 0.03 * s, "snare")

    # ------------------------------------------------------------ 26-27: chapter JOGOS (breakdown)
    put(crash, B_CHG, 0, 0.4, "cym")
    put(star, B_CHG, 0, 0.5, "pet")
    for b in (B_CHG, B_CHG + 1):
        root, notes = chord(b)
        put(pad_chord(notes, bar, 2600, b + 40), b, 0, 0.2, "pad")
        put(bass_note(root, 14, 600), b, 0, 0.4, "bass")
        for i in range(16):                                     # chip arpeggio, climbing
            nn = int(S.step * 0.6 * SR)
            m = notes[i % 4] + 12 * (1 + i // 8) + (12 if b > B_CHG else 0)
            put(sq(mtof(m), nn, 0.125) * perc(nn, 0.001, 0.05), b, i, 0.08, "arpR" if i % 2 else "arpL")
    for i in range(4):
        put(pitch(ping, (0, 3, 7, 12)[i]), B_CHG + i // 2, (i % 2) * 8, 0.3, "ping")
    for s in range(0, 16, 2):
        put(snare, B_CHG + 1, s, 0.15 + 0.02 * s, "snare")
    for s in range(12, 16):
        put(snare, B_CHG + 1, s, 0.4, "snare")
    put(kick, B_CHG + 1, 0, 0.7, "kick")
    put(kick, B_CHG + 1, 8, 0.7, "kick")
    riser(B_CHG, 2, 12, vol=0.3)
    rev_crash(B_GAMES, 0.35)

    # ------------------------------------------------------------ 28-35: the four games
    g0 = B_GAMES
    for b in range(g0, g0 + 8):
        k = b - g0
        if k == 2:
            continue                                            # the quiz bar has its own beat
        groove(b, hats=True, open_hats=k >= 4, bass="reese" if k in (4, 5) else "chip")
        if k % 2 == 0:
            put(crash, b, 0, 0.3, "cym")
        put(pad_chord(chord(b)[1], bar, 2400, b), b, 0, 0.11, "pad")
    for b in (g0, g0 + 1):                                     # 9 XENO PET
        for i in range(16):
            nn = int(S.step * 0.5 * SR)
            put(sq(mtof(84 + (0, 3, 7, 12)[i % 4]), nn, 0.5) * perc(nn, 0.001, 0.04), b, i, 0.06, "arpR")
    for b, s, smp in ((g0, 0, chirp), (g0, 6, chirp), (g0, 10, happy), (g0 + 1, 4, chirp), (g0 + 1, 12, star)):
        put(smp, b, s, 0.5, "pet")
    qb = g0 + 2                                                 # 10 DISCO VOADOR: the quiz clock, then the reveal
    for s in range(16):
        put(click_hi if s % 2 == 0 else click_lo, qb, s, 0.5, "click")
    for s in (0, 3, 8, 11):
        put(pitch(boom, -5), qb, s, 0.5 if s in (0, 8) else 0.3, "sub")
    put(pad_chord([53, 56, 59, 62], bar, 1400, 77), qb, 0, 0.2, "pad")    # diminished: suspense
    put(bass_note(41, 16, 500), qb, 0, 0.35, "bass")
    for s in range(12, 16):
        put(snare, qb, s, 0.25 + 0.05 * (s - 12), "snare")
    rb = qb + 1
    put(stab([65, 68, 72, 77]), rb, 0, 0.4, "duelL")
    put(stab([65, 68, 72, 77], seed=8), rb, 0, 0.4, "duelR")
    put(chime, rb, 0, 0.45, "bell")
    put(pitch(chime, 7), rb, 4, 0.3, "bell")
    for s, m in ((0, 72), (2, 77), (4, 80), (6, 84)):
        put(chip_lead(m, 2), rb, s, 0.18, "lead")
    for b in (g0 + 4, g0 + 5):                                  # 11 VOID RUNNER
        put(vboom, b, 0, 0.5, "fx")
        for s in (2, 6, 10, 14):
            put(zap, b, s, 0.35, "vr")
        for s in (5, 13):
            put(bolt, b, s, 0.3, "vr")
    for s, m, ln in HOOK[:10]:                                  # the hook, chip style, over Void Runner + Duel
        put(chip_lead(m, ln), g0 + 4 + s // 16, s % 16, 0.14, "lead")
    for b in (g0 + 6, g0 + 7):                                  # 12 BEAT DUEL: call and response
        notes = chord(b)[1]
        for s in (0, 3, 6):
            put(stab([n + 12 for n in notes[:3]]), b, s, 0.28, "duelL")
        for s in (8, 11, 14):
            put(stab([n + 7 for n in notes[:3]], seed=5), b, s, 0.28, "duelR")
    for s in range(8, 16):
        put(snare, g0 + 7, s, 0.2 + 0.03 * s, "snare")

    # ------------------------------------------------------------ 36-39: the mosaic and the launch
    for b in (B_MOSAIC, B_MOSAIC + 1):
        groove(b, open_hats=True)
        put(pad_chord(chord(b)[1], bar, 3000, b), b, 0, 0.15, "pad")
        arps(b, 0.06)
    put(crash, B_MOSAIC, 0, 0.4, "cym")
    nb = int(bar * S.step * SR)
    beam = sweep_lp(saw(mtof(53), nb) * 0.4 + saw(mtof(60.07), nb) * 0.4, 200, 4000) * np.linspace(0, 1, nb)
    put(beam, B_MOSAIC + 1, 0, 0.12, "fx")
    L0 = B_LAUNCH
    for s in range(0, 16, 4):
        put(kick, L0, s, 0.85, "kick")
    for s in range(0, 16, 2):
        put(snare, L0, s, 0.22 + 0.01 * s, "snare")
    for s in range(0, 12):
        put(snare, L0 + 1, s, 0.35 + 0.02 * s, "snare")
    put(roll[:int(1.4 * SR)], L0 + 1, 0, 0.3, "snare")
    for i, s in enumerate((8, 9, 10, 11)):
        put(toms[min(2, i)], L0 + 1, s, 0.5, "snare")
    put(pad_chord(chord(L0)[1], 2 * bar - 4, 2500, 21), L0, 0, 0.16, "pad")
    riser(L0, 2, 9, lo=300, hi=10000, vol=0.4, curve=3)
    rc = crash[::-1][-int(0.7 * SR):]
    put(rc, L0 + 1, 12 - int(0.7 / S.step), 0.4, "fx")
    # beats 13-16 of bar 39 stay empty: the breath before the final chorus

    # ------------------------------------------------------------ 40-43: final chorus under the logo
    put(boom, B_FINAL, 0, 1.0, "kick")
    put(cine, B_FINAL, 0, 0.6, "fx")
    for b in range(B_FINAL, B_FINAL + 4):
        groove(b, open_hats=True)
        put(pad_chord(chord(b)[1], bar, 4000, b), b, 0, 0.17, "pad")
        put(choir_to(chord(b)[0]), b, 0, 0.3, "choir")
        arps(b, 0.06)
        if b % 2 == 0:
            put(crash, b, 0, 0.4, "cym")
    for s, m, ln in HOOK:
        put(lead(m, ln), B_FINAL + s // 16, s % 16, 0.26, "lead")
        put(xlead(m + 12, ln), B_FINAL + s // 16, s % 16, 0.12, "lead")
        put(lead(m - 12, ln), B_FINAL + s // 16, s % 16, 0.1, "lead")
    for s in range(8, 16):
        put(snare, B_FINAL + 3, s, 0.25 + 0.03 * s, "snare")

    # ------------------------------------------------------------ 44: the last chord
    put(boom, B_END, 0, 1.0, "kick")
    put(cine, B_END, 0, 0.7, "fx")
    put(crash, B_END, 0, 0.6, "cym")
    put(pad_chord([41 + 12, 53, 56, 60, 65, 72], 2 * bar + 8, 5500, 30), B_END, 0, 0.3, "pad")
    put(choir_to(41), B_END, 0, 0.35, "choir")
    put(choir_to(41), B_END, 12, 0.25, "choir")
    put(sine(mtof(29), int(3.4 * SR)) * np.linspace(1, 0, int(3.4 * SR)), B_END, 0, 0.5, "sub")
    put(glass[:int(4.5 * SR)], B_END, 8, 0.35, "amb")
    put(pitch(ping, 12), B_END, 8, 0.3, "ping")
    put(pitch(ping, 19), B_END, 14, 0.22, "ping")

    # ------------------------------------------------------------ mix (stereo)
    pan = {"hat": 0.25, "arpL": -0.6, "arpR": 0.6, "ping": -0.3, "duelL": -0.7, "duelR": 0.7, "bell": 0.15,
           "pet": 0.3, "vr": -0.2, "scratch": 0.1, "chop": -0.1, "cym": -0.15}
    send = {"pad": 0.35, "lead": 0.3, "arpL": 0.3, "arpR": 0.3, "ping": 0.6, "bell": 0.45, "choir": 0.5, "snare": 0.15,
            "pet": 0.25, "duelL": 0.25, "duelR": 0.25, "amb": 0.3, "fx": 0.2, "click": 0.1}
    n = S.n
    L, R, wet = np.zeros(n), np.zeros(n), np.zeros(n)
    duck = dsp.sidechain(n, sorted(set(kicks)), 0.45, 0.09)
    for name, x in S.bus.items():
        if name in ("bass", "pad", "arpL", "arpR", "lead", "choir"):
            x = x * duck
        if name == "lead":
            x = delay(x, 3 * S.step, 0.35, 0.35, 3500)
        p = pan.get(name, 0.0)
        L += x * np.sqrt((1 - p) / 2) * 1.41
        R += x * np.sqrt((1 + p) / 2) * 1.41
        wet += x * send.get(name, 0.0)
    wl, wr = reverb(wet, 2.2, 1.0, 11, 7000), reverb(wet, 2.2, 1.0, 12, 7000)
    L += wl * 0.5
    R += wr * 0.5
    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    L, R = [np.tanh(1.25 * c / peak) / np.tanh(1.25) * 0.92 for c in (L, R)]
    fade = np.ones(n)
    k = int(1.8 * SR)
    fade[-k:] = np.linspace(1, 0, k) ** 2
    L, R = L * fade, R * fade
    os.makedirs(OUTD, exist_ok=True)
    os.makedirs(BUILD, exist_ok=True)
    import wave
    with wave.open(os.path.join(BUILD, "trailer_44k.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.stack([L, R], 1).clip(-1, 1) * 32767).astype("<i2").tobytes())
    dsp.save_mono(os.path.join(OUTD, "trailer.wav"), (L + R) * 0.5)
    print("music: %.1f s, peak L %.2f, rms %.3f" % (n / float(SR), np.max(np.abs(L)), np.sqrt(np.mean(L ** 2))))
    for b in range(0, NBARS, 2):
        i0, i1 = int(b * bar * S.step * SR), int((b + 1) * bar * S.step * SR)
        print("  bar %2d rms %.3f" % (b, np.sqrt(np.mean(L[i0:i1] ** 2))))


# ====================================================================== credits theme
CRED_BPM = 96          # 1 bar = 2.5 s; fanfare on bar 2 (5.0 s); crawl until ~88 s; final chord bar 35


def credits_music():
    S = Song(CRED_BPM, 38, tail=0.5)
    bar = 16
    stp = S.step
    tom = a("forge/drum_tom_lo_hard.wav")
    crash, snare = a("forge/drum_splash_hard.wav"), a("forge/sn_dolf.wav")
    cine, boom = a("forge/misc_cineboom.wav"), a("forge/bd_boom.wav")
    choir, drone = dsp.load("ambi_choir"), dsp.load("ambi_drone")

    def put(sig, b, s, vol, bus):
        S.put(sig, b * bar + s, vol, bus)

    def strings(notes, nsteps, cut=2600, att=0.25):
        n = int(nsteps * stp * SR) + int(0.6 * SR)
        y = sum(supersaw(mtof(m), n, 5, 0.008, i) for i, m in enumerate(notes))
        return lp(y, cut) * adsr(n, att, 0.4, 0.85, 0.5)

    def brass(m, nsteps, vol=1.0):
        n = int(nsteps * stp * SR) + int(0.25 * SR)
        f = mtof(m)
        y = saw(f, n) + saw(f * 1.003, n, 0.4) * 0.8 + saw(f * 0.5, n, 0.2) * 0.4
        cut = 600 + 3200 * np.clip(np.arange(n) / SR / 0.12, 0, 1) * np.exp(-np.arange(n) / SR * 0.6)
        return sweep_lp(y, np.array([cut[min(len(cut) - 1, i * 512)] for i in range((n + 511) // 512)]), None) * \
            adsr(n, 0.04, 0.3, 0.8, 0.2) * vol

    def timp(semis=0, vol=1.0):
        x = pitch(tom, -7 + semis)[:int(1.2 * SR)]
        n = len(x)
        return (x + sine(mtof(33 + semis), n) * perc(n, 0.002, 0.35) * 0.8) * vol

    def harp(m):
        n = int(1.4 * SR)
        return dsp.pluck(mtof(m), n, 0.997, m) * 0.8

    def choir_to(root):
        k = (root - 75) % 12
        return pitch(choir, k - 12 if k > 6 else k)

    PROG_A = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]  # Am F C G
    PROG_B = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (55, [55, 59, 62, 67]), (52, [56, 59, 64, 68])]  # Am F G E
    TA = [(0, 69, 6), (6, 72, 2), (8, 76, 8), (16, 77, 4), (20, 76, 4), (24, 74, 4), (28, 72, 4),
          (32, 74, 6), (38, 76, 2), (40, 79, 8), (48, 74, 12), (60, 71, 4)]
    TB = [(0, 69, 6), (6, 72, 2), (8, 76, 8), (16, 81, 8), (24, 79, 4), (28, 77, 4),
          (32, 76, 4), (36, 74, 4), (40, 79, 8), (48, 80, 8), (56, 83, 8)]
    # bars 0-1: drone + distant timpani
    put(drone[:int(5.2 * SR)], 0, 0, 0.5, "amb")
    for s in (0, 8, 16, 24, 28):
        put(timp(0, 0.25 + s / 60.0), s // 16, s % 16, 1.0, "timp")
    put(strings([45, 52, 57], 2 * bar, 900, 1.5), 0, 0, 0.25, "str")
    # bars 2-3: fanfare (logo)
    put(cine, 2, 0, 0.7, "fx")
    put(crash, 2, 0, 0.5, "fx")
    put(timp(0, 1.0), 2, 0, 1.0, "timp")
    fan = [(0, [57, 64, 69], 4), (4, [57, 64, 69], 2), (6, [60, 64, 72], 2), (8, [62, 67, 74], 8),
           (16, [60, 65, 72], 6), (22, [59, 64, 71], 2), (24, [57, 64, 69], 8)]
    for s, notes, ln in fan:
        for m in notes:
            put(brass(m, ln, 0.5), 2 + s // 16, s % 16, 0.22, "brass")
    put(strings([45, 57, 60, 64], 2 * bar, 3000, 0.1), 2, 0, 0.25, "str")
    # bars 4-31: theme
    plan = [(4, TA, "str", 0.0), (8, TB, "str", 0.4), (12, TA, "brass", 0.7), (16, TB, "brass", 1.0),
            (20, None, None, 0.3), (24, TA, "brass", 1.0), (28, TB, "brass", 1.0)]
    for b0, theme, lead_bus, energy in plan:
        prog = PROG_B if theme is TB else PROG_A
        for i in range(4):
            root, notes = prog[i]
            b = b0 + i
            put(strings(notes, bar, 1800 + 1800 * energy), b, 0, 0.2, "str")
            put(strings([root - 12], bar, 500), b, 0, 0.3, "bass")
            put(timp(root - 57 if root >= 52 else root - 45, 0.5 + 0.5 * energy), b, 0, 1.0, "timp")
            if energy >= 0.7:
                put(timp(root - 57 if root >= 52 else root - 45, 0.4), b, 10, 1.0, "timp")
                for s in (4, 12):
                    put(snare, b, s, 0.25, "snare")
                for s in (14, 15):
                    put(snare, b, s, 0.12, "snare")
            if theme is None:
                for s in range(0, 16, 2):
                    put(harp(notes[(s // 2) % 4] + 12), b, s, 0.22, "harp")
        if b0 in (12, 24):
            put(crash, b0, 0, 0.45, "fx")
        if theme is not None:
            for s, m, ln in theme:
                if lead_bus == "str":
                    put(strings([m], ln, 3200, 0.12), b0 + s // 16, s % 16, 0.32, "lead")
                    if energy > 0.3:
                        put(brass(m - 12, ln, 0.5), b0 + s // 16, s % 16, 0.12, "brass")
                else:
                    put(brass(m, ln), b0 + s // 16, s % 16, 0.2, "brass")
                    put(strings([m + 12], ln, 4200, 0.08), b0 + s // 16, s % 16, 0.12, "lead")
        if b0 in (16, 28):
            for i in range(4):
                put(choir_to(prog[i][0]), b0 + i, 0, 0.3, "choir")
    # bars 32-35: finale, A major at the end
    fin = [(32, [57, 60, 64, 69, 72]), (33, [53, 57, 60, 65, 69]), (34, [55, 59, 62, 67, 71]), (35, [57, 61, 64, 69, 73])]
    for b, notes in fin:
        ln = bar if b < 35 else 2 * bar + 8
        put(strings(notes, ln, 4200, 0.1), b, 0, 0.24, "str")
        for m in notes[1:4]:
            put(brass(m, min(ln, 12), 0.8), b, 0, 0.16, "brass")
        put(timp(notes[0] - 57, 1.0), b, 0, 1.0, "timp")
        put(crash, b, 0, 0.35 if b < 35 else 0.6, "fx")
    for s in range(0, 16):
        put(timp(-2, 0.25 + s * 0.04), 34, s, 1.0, "timp")
    put(boom, 35, 0, 0.9, "fx")
    put(choir_to(57), 35, 0, 0.4, "choir")
    put(choir_to(57), 35, 12, 0.3, "choir")
    # mix
    pan = {"brass": -0.15, "lead": 0.1, "harp": 0.4, "choir": -0.2, "timp": 0.0, "str": 0.0}
    send = {"str": 0.45, "brass": 0.35, "lead": 0.5, "harp": 0.5, "choir": 0.6, "timp": 0.3, "snare": 0.25, "fx": 0.3,
            "amb": 0.3}
    n = S.n
    L, R, wet = np.zeros(n), np.zeros(n), np.zeros(n)
    for name, x in S.bus.items():
        p = pan.get(name, 0.0)
        L += x * np.sqrt((1 - p) / 2) * 1.41
        R += x * np.sqrt((1 + p) / 2) * 1.41
        wet += x * send.get(name, 0.0)
    L += reverb(wet, 3.2, 1.0, 21, 6000) * 0.6
    R += reverb(wet, 3.2, 1.0, 22, 6000) * 0.6
    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    L, R = [np.tanh(1.2 * c / peak) / np.tanh(1.2) * 0.9 for c in (L, R)]
    k = int(3.0 * SR)
    fade = np.ones(n)
    fade[-k:] = np.linspace(1, 0, k) ** 1.5
    L, R = L * fade, R * fade
    import wave
    with wave.open(os.path.join(BUILD, "credits_44k.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.stack([L, R], 1).clip(-1, 1) * 32767).astype("<i2").tobytes())
    dsp.save_mono(os.path.join(OUTD, "credits.wav"), (L + R) * 0.5)
    print("credits: %.1f s, rms %.3f" % (n / float(SR), np.sqrt(np.mean(L ** 2))))


# ====================================================================== frames
def write_frm(path, images):
    """8-bit frames sharing one palette: FRM1, count, w, h, palette, [len + zlib(indices)]"""
    from PIL import Image
    w, h = images[0].size
    strip = Image.new("RGB", (w, h * len(images)))
    for i, im in enumerate(images):
        strip.paste(im, (0, i * h))
    q = strip.quantize(256, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = bytes(q.getpalette()[:768]).ljust(768, b"\0")
    out = [b"FRM1", struct.pack("<BHH", len(images), w, h), pal]
    for i in range(len(images)):
        idx = q.crop((0, i * h, w, (i + 1) * h)).tobytes()
        z = zlib.compress(idx, 9)
        out.append(struct.pack("<I", len(z)) + z)
    open(path, "wb").write(b"".join(out))
    return os.path.getsize(path)


CROP_W, CROP_H = 624, 360          # the trailer's viewscreen (trailer.py WW, WH): a 1:1 window on the footage


def best_crop(ims, title_bar=True):
    """where to put the viewscreen on an app's footage so its edges cut through as little text as possible:
    an edge is bad where something bright sits right on both sides of it (a word sliced in two). The app's
    own title bar (its name is on the trailer's plate anyway) and hint bar are the first things to give up."""
    from PIL import ImageFilter
    lum = []
    for im in ims:            # 'ink': pixels that stand out from their surroundings (dim text included)
        L = im.convert("L")
        d = np.abs(np.asarray(L, dtype=np.int16) - np.asarray(L.filter(ImageFilter.MedianFilter(7)), dtype=np.int16))
        lum.append(d > 36)

    def cut_rows(r, x0, x1):          # edge between rows r-1 and r
        c = 0
        for b in lum:
            a = b[max(0, r - 5):r, x0:x1].any(axis=0)
            d = b[r:r + 5, x0:x1].any(axis=0)
            c += int((a & d).sum())
        return c

    def cut_cols(c0, y0, y1):
        c = 0
        for b in lum:
            a = b[y0:y1, max(0, c0 - 6):c0].any(axis=1)      # 6 px: wider than the gap between two letters
            d = b[y0:y1, c0:c0 + 6].any(axis=1)
            c += int((a & d).sum())
        return c

    h, w = lum[0].shape
    best = None
    for sx in range(0, w - CROP_W + 1, 2):
        cost = (cut_cols(sx, 0, h) if sx else 0) + (cut_cols(sx + CROP_W, 0, h) if sx + CROP_W < w else 0)
        cost += abs(sx - (w - CROP_W) // 2) * 0.5
        if best is None or cost < best[0]:
            best = (cost, sx)
    sx = best[1]
    best = None
    for sy in range(0, h - CROP_H + 1, 2):
        cost = (cut_rows(sy, sx, sx + CROP_W) if sy else 0) + \
            (cut_rows(sy + CROP_H, sx, sx + CROP_W) if sy + CROP_H < h else 0)
        cost += max(0, 46 - sy) * 4 * title_bar + max(0, sy + CROP_H - 436) * 4   # rather lose the title / hint bars
        if best is None or cost < best[0]:
            best = (cost, sy)
    return sx, best[1], best[0]


def frames():
    import json
    from PIL import Image
    src = os.path.join(BUILD, "trailer")
    os.makedirs(OUTD, exist_ok=True)
    total = 0
    thumbs = []
    crops = {}
    for app in APPS:
        ims = [Image.open(os.path.join(src, "%s_%d.png" % (app, i))).convert("RGB") for i in range(6)]
        total += write_frm(os.path.join(OUTD, app + ".frm"), ims)
        thumbs.append(ims[3].resize((160, 120), Image.LANCZOS))
        sx, sy, cost = best_crop(ims, APPS.index(app) < 8)   # games keep their score bar
        crops[app] = [sx, sy]
        print("  %-10s crop %3d,%3d  (edge cost %d)" % (app, sx, sy, cost))
    total += write_frm(os.path.join(OUTD, "thumbs.frm"), thumbs)
    json.dump(crops, open(os.path.join(OUTD, "crops.json"), "w"))
    print("frames: %.1f MB" % (total / 1e6))


if __name__ == "__main__":
    what = sys.argv[1:] or ["music", "frames", "credits"]
    if "frames" in what:
        frames()
    if "music" in what:
        music()
    if "credits" in what:
        credits_music()
