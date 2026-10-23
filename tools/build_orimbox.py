"""ORIMBOX sound kit: 20 loops a crew of 7 aliens can sing together (Incredibox-style), plus 5 bonus
choruses unlocked by combos. Every loop is 4 bars at 100 BPM in A minor over Am-F-C-G, so ANY mix works.
Tails (reverb, delay, long notes) are wrapped into the start, so each loop repeats without a seam.

Sources (all CC0 1.0 - open resources), pinned to the commits below:
  - the Sonic Pi sample library (github.com/sonic-pi-net/sonic-pi, etc/samples, from freesound.org)
  - VCSL, the Versilian Community Sample Library (github.com/sgossner/VCSL): kalimba, ocarina, marimba, claps,
    cajon, shaker, flexatone, vibraslap, siren whistle, log drums, didgeridoo, wood click
  - everything else (beatbox, voices, synths) is synthesized here: the voices are formant synthesis.

  python3 tools/build_orimbox.py CACHE_DIR [id ...]
      -> ports/mothership/assets/orimbox/<id>.wav (44.1 kHz mono) + kit.json
Downloads the samples that are missing into CACHE_DIR (use an empty folder of its own). With ids, only those
loops are written (kit.json always). Needs numpy, scipy and ffmpeg.
"""
import json
import math
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import numpy as np
import scipy.signal as sg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp  # noqa
from dsp import SR, mtof, saw, sine, noise, perc, adsr, lp, hp, bp, supersaw, reverb, delay  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(ROOT, "ports", "mothership", "assets", "orimbox")
SPI = "https://raw.githubusercontent.com/sonic-pi-net/sonic-pi/7508f5dcd80ae041722b937fe8aea217a029f6bc/etc/samples/"
VCSL = "https://raw.githubusercontent.com/sgossner/VCSL/c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e/"
VCSL_FILES = {                         # folder in VCSL -> the files used from it
    "Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/Sus": [
        "StdOcarina_Sus_B3.wav", "StdOcarina_Sus_D4.wav",
    ],
    "Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/SusVib": [
        "StdOcarina_SusVib_A3.wav", "StdOcarina_SusVib_A4.wav", "StdOcarina_SusVib_C4.wav",
        "StdOcarina_SusVib_C5.wav", "StdOcarina_SusVib_E4.wav", "StdOcarina_SusVib_F#4.wav",
        "StdOcarina_SusVib_G#4.wav",
    ],
    "Aerophones/Free Aerophones/Siren": [
        "Main_SirenWhistle-005.wav", "Main_SirenWhistle-009.wav",
    ],
    "Aerophones/Lip Aerophones/Didgeridoo": [
        "Didgeridoo1_Bark1_Main_rr3.wav", "Didgeridoo1_Phrase1_Main.wav", "Didgeridoo1_Sus2_Main.wav",
    ],
    "Idiophones/Plucked Idiophones/Kalimba, Kenya": [
        "Mbira6_Normal_MainSpirit_A4_k1_vl3_rr2.wav", "Mbira6_Normal_MainSpirit_B3_k3_vl3_rr2.wav",
        "Mbira6_Normal_MainSpirit_C#4_k2_vl3_rr2.wav", "Mbira6_Normal_MainSpirit_F#3_k5_vl3_rr2.wav",
    ],
    "Idiophones/Struck Idiophones/Cajon": [
        "Cajon_hit1_f_rr1.wav", "Cajon_hit1_f_rr2.wav", "Cajon_hit2_f_rr1.wav", "Cajon_hit2_mp_rr1.wav",
        "Cajon_hit3_f_rr1.wav", "Cajon_hit3_p_rr1.wav",
    ],
    "Idiophones/Struck Idiophones/Claps": [
        "Clap_rr1.wav", "Clap_rr2.wav", "Clap_rr3.wav", "Clap_rr4.wav",
    ],
    "Idiophones/Struck Idiophones/Flexatone": [
        "flexatone1.wav", "flexatone_fast.wav", "flexatone_slap1.wav",
    ],
    "Idiophones/Struck Idiophones/Marimba": [
        "Marimba_hit_Outrigger_B2_med_01.wav", "Marimba_hit_Outrigger_B4_med_01.wav",
        "Marimba_hit_Outrigger_C2_med_01.wav", "Marimba_hit_Outrigger_C4_med_01.wav",
        "Marimba_hit_Outrigger_F3_med_01.wav", "Marimba_hit_Outrigger_F5_med_01.wav",
        "Marimba_hit_Outrigger_G2_med_01.wav", "Marimba_hit_Outrigger_G4_med_01.wav",
    ],
    "Idiophones/Struck Idiophones/Shaker, Small": [
        "Mid_ShakerDouble_Down_rr1.wav", "Mid_ShakerHighFaster_Down_rr1.wav", "Mid_ShakerHighFaster_Up_rr1.wav",
        "Mid_Shaker_Slap_rr1.wav",
    ],
    "Idiophones/Struck Idiophones/Slit Drum": [
        "LogDrumHi_MedM_v2_rr1_Sum.wav", "LogDrumLo_MedM_v2_rr1_Sum.wav",
    ],
    "Idiophones/Struck Idiophones/Vibraslap/Legacy": [
        "vibraslap_rr1.wav",
    ],
    "Idiophones/Struck Idiophones/Woodblock": [
        "wood_click_f_rr1.wav",
    ],
}
VCSL_PATH = dict((f, d + "/" + f) for d, fs in VCSL_FILES.items() for f in fs)
CACHE = [None]                         # the download folder (first argument)

BPM = 100
STEP = 60.0 / BPM / 4                  # a 16th note: 0.15 s
BARS = 4
N = int(round(BARS * 16 * STEP * SR))  # 423360 samples = 9.6 s
FPS_ENV = 30                           # animation envelope rate (= 1470 samples per value)
# Am - F - C - G: (bass root, triad) as MIDI notes
CHORDS = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]
SCALE = {9, 11, 0, 2, 4, 5, 7}         # A natural minor
RNG = np.random.RandomState(7)


# ====================================================================== sample loading + tuning
_cache = {}


def ff(path):
    if path not in _cache:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                             check=True, stdout=subprocess.PIPE).stdout
        x = np.frombuffer(raw, dtype="<f4").astype(np.float64)
        pk = np.max(np.abs(x)) + 1e-9
        i = int(np.argmax(np.abs(x) > 0.02 * pk))                 # trim the silence before the hit
        _cache[path] = x[max(0, i - 32):] / pk
    return _cache[path]


def fetch(url, name):
    dst = os.path.join(CACHE[0], name)
    if not os.path.exists(dst):
        with urllib.request.urlopen(url) as r:
            data = r.read()
        with open(dst + ".part", "wb") as f:
            f.write(data)
        os.replace(dst + ".part", dst)
    return dst


def sp(name):
    return ff(fetch(SPI + name + ".flac", name + ".flac"))


def vc(name):
    return ff(fetch(VCSL + urllib.parse.quote(VCSL_PATH[name]), name))


def f0_near(x, guess, lo_st=-2.0, hi_st=2.0, seg=(0.08, 0.45)):
    """precise f0 of a pitched sample, searched within a few semitones of its labelled note"""
    a, b = int(seg[0] * SR), int(seg[1] * SR)
    s = x[a:min(len(x), b)]
    s = (s - s.mean()) * np.hanning(len(s))
    r = np.fft.irfft(np.abs(np.fft.rfft(s, 2 * len(s))) ** 2)[:len(s)]
    lag_lo = int(SR / (guess * 2 ** (hi_st / 12.0)))
    lag_hi = int(SR / (guess * 2 ** (lo_st / 12.0))) + 1
    k = lag_lo + int(np.argmax(r[lag_lo:lag_hi]))
    if 1 <= k < len(r) - 1:                                       # parabolic refinement
        y0, y1, y2 = r[k - 1], r[k], r[k + 1]
        k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
    return SR / k


def repitch(x, ratio):
    if abs(ratio - 1.0) < 1e-4:
        return x
    n = int(len(x) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x)


class Tuned(object):
    """a set of pitched samples {midi label: file}; plays any note from the nearest one, retuned exactly"""

    def __init__(self, loader, files, seg=(0.08, 0.45)):
        self.s = []
        for m, f in files.items():
            x = loader(f)
            f0 = f0_near(x, mtof(m), seg=seg)
            self.s.append((m, f0, x))
            print("    %-46s labelled %-4s measured %+.0f cents" % (f, m, 1200 * math.log2(f0 / mtof(m))))

    def note(self, m, length=None):
        lab, f0, x = min(self.s, key=lambda e: abs(e[0] - m))
        y = repitch(x, mtof(m) / f0)
        if length is not None:
            n = int(length * SR)
            y = y[:n] if len(y) >= n else np.concatenate([y, np.zeros(n - len(y))])
            fade = min(len(y), int(0.03 * SR))
            y[-fade:] *= np.linspace(1, 0, fade)
        return y


# ====================================================================== the loop canvas
HITS = set()          # 16th steps (0..63) where the loop being built has a note: the app's BEAT DUEL notes


class Loop(object):
    def __init__(self):
        self.y = np.zeros(N)

    def put(self, sig, step, vol=1.0):
        """add sig at a 16th-step position; whatever runs past the end wraps to the start (seamless)"""
        i = int(round(step * STEP * SR)) % N
        if vol >= 0.3:
            HITS.add(int(round(step)) % 64)
        sig = np.asarray(sig) * vol
        while len(sig):
            take = min(len(sig), N - i)
            self.y[i:i + take] += sig[:take]
            sig = sig[take:]
            i = 0

    def fx(self, fn):
        """an effect with a tail: process 2 laps, keep the second one (so tails wrap around)"""
        two = fn(np.concatenate([self.y, self.y]))
        self.y = two[N:2 * N]


def chord_at(bar):
    return CHORDS[bar % 4]


def tones(bar, lo=55, hi=72):
    """the chord's notes spread over a range, sorted"""
    root, tri = chord_at(bar)
    out = []
    for m in tri:
        for o in (-24, -12, 0, 12, 24):
            if lo <= m + o <= hi:
                out.append(m + o)
    return sorted(set(out))


# ====================================================================== drums: samples + mouth beatbox
def b_kick(n=0.32):
    k = int(n * SR)
    t = np.arange(k) / SR
    f = 46 + 140 * np.exp(-t / 0.028)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    pop = lp(noise(k, 3), 2500) * np.exp(-t / 0.004) * 0.8              # lips
    return np.tanh(1.6 * (body + pop))


def b_snare(n=0.22, seed=5):
    """the 'pf' of a beatboxer: air through the lips, a bit of tone"""
    k = int(n * SR)
    t = np.arange(k) / SR
    air = bp(noise(k, seed), 900, 5200) * (1 - np.exp(-t / 0.002)) * np.exp(-t / 0.075)
    ton = np.sin(2 * np.pi * 220 * t) * np.exp(-t / 0.03) * 0.5          # A3: in key with everything
    return air * 1.6 + ton


def b_hat(n=0.08, seed=9, dec=0.028):
    k = int(n * SR)
    t = np.arange(k) / SR
    return hp(noise(k, seed), 6500) * np.exp(-t / dec) * (1 - np.exp(-t / 0.0008))


def b_k(n=0.09, seed=11):
    """the inward 'k' click snare"""
    k = int(n * SR)
    t = np.arange(k) / SR
    return bp(noise(k, seed), 1800, 7000) * np.exp(-t / 0.018) * 1.4


def beat_bumtss():
    L = Loop()
    kick, kick2, snare, hat = sp("bd_haus"), sp("bd_boom"), sp("sn_dolf"), sp("hat_zild")
    for bar in range(4):
        o = bar * 16
        for st in ([0, 10] if bar % 2 == 0 else [0, 7, 10]):
            L.put(kick, o + st, 1.0)
            L.put(kick2[:int(0.35 * SR)] * np.exp(-np.arange(int(0.35 * SR)) / SR / 0.2), o + st, 0.35)
        for st in (4, 12):
            L.put(snare, o + st, 0.75)
        for st in range(0, 16, 2):
            L.put(hat, o + st, 0.22 if st % 4 == 0 else 0.34)
        if bar == 3:
            L.put(snare, o + 15, 0.3)
    return L.y


def beat_tchka():
    L = Loop()
    for bar in range(4):
        o = bar * 16
        for st in (0, 7, 9) if bar != 3 else (0, 7, 9, 11):
            L.put(b_kick(), o + st, 1.0)
        L.put(b_snare(seed=5 + bar), o + 4, 0.75)
        L.put(b_snare(seed=9 + bar), o + 12, 0.75)
        for st in (2, 6, 10, 14):
            L.put(b_hat(seed=st + bar), o + st, 0.5)
        L.put(b_hat(seed=40 + bar, dec=0.015), o + 15, 0.3)
        L.put(b_k(seed=bar), o + 3, 0.35)
        if bar == 3:
            for st in (13, 14):
                L.put(b_k(seed=20 + st), o + st, 0.55)
    return L.y


def beat_tabla():
    L = Loop()
    bass = [sp("tabla_ghe%d" % i) for i in (1, 2, 4, 6)]
    na, te, te2, ke, tun = sp("tabla_na"), sp("tabla_te1"), sp("tabla_te2"), sp("tabla_ke1"), sp("tabla_tun1")
    pat = [("g", 1.0), ("t", 0.4), ("t", 0.3), ("n", 0.7), ("k", 0.5), ("t", 0.35), ("n", 0.75), ("t", 0.3),
           ("g", 0.85), ("t", 0.4), ("n", 0.6), ("t", 0.3), ("k", 0.55), ("n", 0.5), ("tun", 0.6), ("t", 0.35)]
    for bar in range(4):
        for st, (h, v) in enumerate(pat):
            if h == "g":
                L.put(bass[(bar + st) % 4], bar * 16 + st, v)
                L.put(na, bar * 16 + st, v * 0.5)
            else:
                L.put({"t": te if st % 4 else te2, "n": na, "k": ke, "tun": tun}[h], bar * 16 + st, v)
    return L.y


def beat_cajon():
    L = Loop()
    hits = {k: vc("Cajon_%s.wav" % k) for k in ("hit1_f_rr1", "hit1_f_rr2", "hit2_f_rr1", "hit2_mp_rr1",
                                               "hit3_f_rr1", "hit3_p_rr1")}
    # which hit is the bass (lowest spectral centroid) and which is the slap
    def centroid(x):
        seg = np.zeros(4096)
        seg[:min(4096, len(x))] = x[:4096]
        s = np.abs(np.fft.rfft(seg * np.hanning(4096)))
        f = np.fft.rfftfreq(4096, 1.0 / SR)
        return float(np.sum(f * s) / (np.sum(s) + 1e-9))
    order = sorted(hits, key=lambda k: centroid(hits[k]))
    low, slap, ghost = hits[order[0]], hits[order[-1]], hits[order[-2]]
    print("    cajon bass=%s slap=%s ghost=%s" % (order[0], order[-1], order[-2]))
    for bar in range(4):
        o = bar * 16
        for st in (0, 6, 10):
            L.put(low, o + st, 1.0 if st != 6 else 0.75)
        for st in (4, 12):
            L.put(slap, o + st, 0.8)
        for st in (2, 7, 11, 14, 15):
            L.put(ghost, o + st, 0.22)
        if bar == 3:
            L.put(slap, o + 14, 0.5)
            L.put(slap, o + 15, 0.6)
    return L.y


def beat_shaker():
    L = Loop()
    dn, up = vc("Mid_ShakerHighFaster_Down_rr1.wav"), vc("Mid_ShakerHighFaster_Up_rr1.wav")
    claps = [vc("Clap_rr%d.wav" % i) for i in (1, 2, 3, 4)]
    wood = vc("wood_click_f_rr1.wav")
    for bar in range(4):
        o = bar * 16
        for st in range(16):
            L.put(dn if st % 2 == 0 else up, o + st, 0.5 if st % 2 else 0.3)
        for st in (4, 12):
            L.put(claps[(bar * 2 + st) % 4], o + st, 0.7)
            L.put(claps[(bar * 2 + st + 1) % 4], o + st + 0.08, 0.45)
        for st in ((3, 11) if bar % 2 else (11,)):
            L.put(wood[:int(0.25 * SR)], o + st, 0.45)
    return L.y


# ====================================================================== effects
def fx_zap():
    L = Loop()

    def zap(f_hi=1900, f_lo=170, n=0.16):
        k = int(n * SR)
        t = np.arange(k) / SR
        f = f_lo + f_hi * np.exp(-t / 0.028)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return (np.sin(ph) * 0.7 + np.sign(np.sin(ph)) * 0.2) * np.exp(-t / 0.05)
    for bar in range(4):
        o = bar * 16
        for i, st in enumerate((3, 6, 11) if bar < 3 else (3, 6, 9, 11, 13)):
            L.put(zap(1500 + 400 * ((i + bar) % 3)), o + st, 0.6)
    L.fx(lambda x: delay(x, 3 * STEP, 0.35, 0.45, 4200))
    return L.y


def fx_risco():
    L = Loop()
    scr, back = sp("vinyl_scratch"), sp("vinyl_backspin")
    for bar in (1, 3):
        o = bar * 16
        L.put(scr[:int(0.3 * SR)], o + 2, 0.8)
        L.put(repitch(scr[:int(0.34 * SR)], 1.25), o + 3, 0.6)
        L.put(scr[:int(0.3 * SR)], o + 10, 0.8)
        L.put(repitch(scr[:int(0.4 * SR)], 0.8), o + 11, 0.6)
    bk = back[:int(1.2 * SR)]
    L.put(bk * np.linspace(1, 0.2, len(bk)), 3 * 16 + 12, 0.45)
    L.put(scr[:int(0.25 * SR)], 0 * 16 + 14, 0.5)
    return hp(L.y, 120)


def fx_robo():
    L = Loop()
    bits = [sp("mehackit_robot%d" % i) for i in (1, 2, 3, 5, 6, 7)] + [sp("glitch_robot1"), sp("glitch_robot2")]
    plan = [(0, 0, 0.5), (0, 6, 0.35), (1, 8, 0.5), (1, 12, 0.3), (2, 0, 0.5), (2, 6, 0.35), (3, 4, 0.45),
            (3, 10, 0.5)]
    for i, (bar, st, ln) in enumerate(plan):
        s = bits[i % len(bits)][:int(ln * SR)]
        s = s * np.minimum(1, np.linspace(ln * 30, 0, len(s)))
        L.put(s, bar * 16 + st, 0.75)
    L.y = bp(L.y, 300, 6000)
    L.fx(lambda x: delay(x, 2 * STEP, 0.25, 0.3, 3000))
    return L.y


def fx_boing():
    L = Loop()

    def boing(f0=330, n=0.5):
        k = int(n * SR)
        t = np.arange(k) / SR
        f = f0 * (1 + 0.5 * np.exp(-t / 0.08)) * (1 + 0.06 * np.sin(2 * np.pi * 28 * t) * np.exp(-t / 0.2))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * (1 - np.exp(-t / 0.002))
    slap = vc("flexatone_slap1.wav")
    vib = vc("vibraslap_rr1.wav")
    for bar, st, f in ((0, 6, 440), (1, 14, 330), (2, 6, 440), (3, 10, 523), (3, 14, 392)):
        L.put(boing(f), bar * 16 + st, 0.6)
    for bar in (1, 3):
        L.put(slap, bar * 16 + 6, 0.55)
    L.put(vib[:int(1.4 * SR)], 3 * 16 + 0, 0.35)
    return L.y


def fx_cosmos():
    L = Loop()
    land, woosh = sp("ambi_lunar_land"), sp("ambi_dark_woosh")
    siren = vc("Main_SirenWhistle-005.wav")
    L.put(repitch(siren, 0.5) * 0.5, 0, 0.35)
    L.put(repitch(siren, 0.5) * 0.5, 32, 0.3)
    L.put(land[:int(4.5 * SR)], 8, 0.45)
    L.put(woosh, 3 * 16 + 4, 0.5)
    ping = sp("elec_ping")
    f0 = f0_near(ping, mtof(84), -12, 12, seg=(0.0, 0.2))           # whatever its pitch, retune to the scale
    pent = [69, 72, 74, 76, 79, 81, 84]
    for st in range(0, 64, 3):
        if RNG.rand() < 0.6:
            m = pent[RNG.randint(len(pent))]
            L.put(repitch(ping, mtof(m) / f0), st, 0.25)
    L.fx(lambda x: reverb(delay(x, 3 * STEP, 0.4, 0.4, 5000), 2.6, 0.45, 3))
    return L.y


# ====================================================================== melodies
def mel_baixo():
    L = Loop()

    def bass(m, steps):
        n = int(steps * STEP * SR) + int(0.03 * SR)
        f = mtof(m)
        x = saw(f, n) * 0.6 + np.sign(np.sin(2 * np.pi * f / 2 * np.arange(n) / SR)) * 0.25 + sine(f / 2, n) * 0.5
        env = adsr(n, 0.004, 0.18, 0.55, 0.03)
        cut = 220 + 1400 * np.exp(-np.arange(n) / SR / 0.07)
        return dsp.sweep_lp(x, cut[::256], None, 256) * env
    for bar in range(4):
        root = chord_at(bar)[0]
        fifth = root + 7
        nxt = chord_at(bar + 1)[0]
        pat = [(0, root, 3), (3, root, 2), (6, fifth, 2), (8, root + 12, 2), (10, root, 2), (13, root, 1),
               (14, nxt + (1 if nxt < root else -1) if abs(nxt - root) > 2 else fifth, 2)]
        for st, m, ln in pat:
            if (m % 12) not in SCALE:
                m = fifth
            L.put(bass(m, ln), bar * 16 + st, 0.9)
    return L.y


def mel_kalimba(T):
    L = Loop()
    for bar in range(4):
        tt = tones(bar, 64, 81)
        idx = [0, 2, 1, 2, 3, 2, 1, 2]
        for i, k in enumerate(idx):
            m = tt[min(k, len(tt) - 1)]
            L.put(T.note(m, 1.6), bar * 16 + i * 2, 0.75 if i % 2 == 0 else 0.5)
    L.fx(lambda x: delay(x, 3 * STEP, 0.25, 0.25, 4500))
    return L.y


OCARINA_LINE = [  # (bar, step, midi, length in steps)
    (0, 0, 76, 4), (0, 4, 72, 2), (0, 6, 74, 2), (0, 8, 76, 6),
    (1, 0, 72, 4), (1, 4, 69, 4), (1, 8, 72, 2), (1, 10, 74, 2), (1, 12, 72, 4),
    (2, 0, 67, 4), (2, 4, 72, 2), (2, 6, 76, 4), (2, 10, 74, 2), (2, 12, 72, 4),
    (3, 0, 74, 6), (3, 6, 71, 2), (3, 8, 67, 4), (3, 12, 71, 4)]


def mel_ocarina(T):
    L = Loop()
    for bar, st, m, ln in OCARINA_LINE:
        n = ln * STEP + 0.12
        y = T.note(m, n)
        y *= adsr(len(y), 0.02, 0.2, 0.9, 0.08)
        L.put(y, bar * 16 + st, 0.8)
    L.fx(lambda x: reverb(x, 1.6, 0.22, 4))
    return L.y


def mel_marimba(T):
    L = Loop()
    for bar in range(4):
        tt = tones(bar, 60, 77)
        L.put(T.note(chord_at(bar)[0] + 12, 1.5), bar * 16, 0.6)
        for st in (2, 6, 10, 13):
            for m in tt[1:3]:
                L.put(T.note(m, 0.9), bar * 16 + st, 0.42)
    return L.y


def mel_nuvem():
    L = Loop()
    for bar in range(4):
        root, tri = chord_at(bar)
        notes = [root + 12, tri[0], tri[1], tri[2] + 12]
        n = int(16 * STEP * SR) + int(0.8 * SR)
        y = sum(supersaw(mtof(m), n, 5, 0.008, bar * 10 + i) for i, m in enumerate(notes)) / len(notes)
        t = np.arange(n) / SR
        cut = 700 + 500 * np.sin(np.pi * np.clip(t / (16 * STEP), 0, 1))
        y = dsp.sweep_lp(y, cut[::512], None, 512) * adsr(n, 0.45, 0.6, 0.85, 0.8)
        L.put(y, bar * 16, 0.9)
    L.fx(lambda x: reverb(x, 2.2, 0.3, 5))
    return L.y


# ====================================================================== voices: formant synthesis
FORMANTS = {  # (frequency, bandwidth, gain) for an adult voice; shifted per singer
    "a": [(800, 80, 1.0), (1150, 90, 0.5), (2900, 120, 0.22), (3900, 130, 0.08)],
    "e": [(450, 70, 1.0), (1900, 100, 0.4), (2600, 120, 0.25), (3800, 130, 0.08)],
    "i": [(300, 60, 1.0), (2300, 100, 0.32), (3000, 120, 0.22), (3800, 130, 0.08)],
    "o": [(450, 70, 1.0), (800, 80, 0.6), (2830, 100, 0.14), (3800, 130, 0.05)],
    "u": [(325, 60, 1.0), (700, 70, 0.38), (2530, 100, 0.1), (3500, 130, 0.03)],
    "m": [(250, 60, 1.0), (1100, 200, 0.06), (2400, 200, 0.03)],
}


def glottal(fcurve, tilt=1.15, jitter=0.002, seed=0):
    """band-limited pulse train with the spectral tilt of a voice; fcurve = Hz per sample"""
    n = len(fcurve)
    rng = np.random.RandomState(seed)
    drift = 1 + jitter * lp(rng.randn(n), 8) * 30
    ph = 2 * np.pi * np.cumsum(fcurve * drift) / SR
    fmax = float(np.max(fcurve))
    y = np.zeros(n)
    for k in range(1, int(5500 / max(fmax, 60)) + 1):
        y += np.sin(k * ph) / k ** tilt
    return y / 2.0


def vowel_filter(src, v, shift=1.0):
    out = np.zeros(len(src))
    for f, bw, g in FORMANTS[v]:
        f2 = min(f * shift, SR * 0.45)
        b, a = sg.iirpeak(f2, f2 / (bw * shift), fs=SR)
        out += g * sg.lfilter(b, a, src)
    return out


def sing(syl, m, dur, shift=1.0, vib=0.010, glide_from=None, breath=0.05, seed=0, tilt=1.15):
    """one sung syllable: optional consonant (b, d, m, r, h) + vowel(s) + optional ending (m, x)"""
    seed = abs(int(seed)) % (2 ** 31 - 8)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = np.full(n, mtof(m))
    if glide_from is not None:
        f = mtof(m) + (mtof(glide_from) - mtof(m)) * np.exp(-t / 0.05)
    f = f * (1 + vib * np.clip((t - 0.15) / 0.2, 0, 1) * np.sin(2 * np.pi * 5.6 * t))
    src = glottal(f, tilt, seed=seed) + breath * noise(n, seed + 1)
    head = syl[0] if syl[0] in "bdmrh" else ""
    tail = syl[-1] if (len(syl) > 1 and syl[-1] in "mx") else ""
    vows = [c for c in syl if c in "aeiou"] or ["u"]
    # vowel(s): a diphthong crossfades through its vowels
    y = np.zeros(n)
    seg = n // len(vows)
    for i, v in enumerate(vows):
        part = vowel_filter(src, v, shift)
        w = np.zeros(n)
        a0, a1 = i * seg, n if i == len(vows) - 1 else (i + 1) * seg
        w[a0:a1] = 1.0
        w = lp(w, 25) if len(vows) > 1 else w
        y += part * w
    env = np.minimum(1, t / 0.015) * np.clip((dur - t) / 0.05, 0, 1)
    if tail == "m":                                   # close the mouth: hum
        k = int(n * 0.55)
        hum = lp(vowel_filter(src, "m", shift), 900) * 1.4
        mix_w = np.clip((np.arange(n) - k) / (0.03 * SR), 0, 1)
        y = y * (1 - mix_w) + hum * mix_w
    if head == "b":                                   # lips closed, then they burst
        k = int(0.025 * SR)
        y[:k] = lp(src[:k], 400) * 0.4
        r = min(len(y) - k, 130)
        y[k:k + r] *= np.linspace(0.4 * np.max(np.abs(y[:k])) / (np.max(np.abs(y[k:k + r])) + 1e-9), 1, r)
        y[k:k + 200] += lp(noise(200, seed + 2), 3000) * 0.6
    elif head == "d":
        k = int(0.012 * SR)
        y[:k] *= np.linspace(0.0, 0.15, k)
        y[k:k + 130] *= np.linspace(0.15, 1.0, 130)
        y[k:k + 260] += bp(noise(260, seed + 3), 2500, 5500) * 0.9
    elif head == "m":
        k = int(0.06 * SR)
        hum = lp(vowel_filter(src[:k], "m", shift), 900) * 1.4
        y[:k] = hum * np.linspace(1, 0.3, k) + y[:k] * np.linspace(0, 0.7, k)
    elif head == "r":
        k = int(0.02 * SR)
        y[k:k + int(0.012 * SR)] *= 0.3
    elif head == "h":
        k = int(0.07 * SR)
        y[:k] = y[:k] * np.linspace(0, 1, k) + bp(noise(k, seed + 4), 600, 3000) * np.linspace(0.6, 0, k)
    y *= env
    if tail == "x":                                   # 'ks' at the end
        k = int(0.07 * SR)
        y[-k:] *= np.linspace(1, 0, k)
        ks = hp(noise(int(0.09 * SR), seed + 5), 4200) * perc(int(0.09 * SR), 0.004, 0.04)
        y = np.concatenate([y, ks * 0.5])
    return y / (np.max(np.abs(y)) + 1e-9)


def voc_uuu():
    """choir pad: the Sonic Pi choir (CC0) retuned to every chord note + soft synthesized 'oo' voices"""
    L = Loop()
    ch = sp("ambi_choir")
    f0 = f0_near(ch, mtof(57), -12, 12, seg=(0.3, 1.2))
    for bar in range(4):
        root, tri = chord_at(bar)
        notes = [tri[0], tri[1], tri[2]]
        dur = 16 * STEP + 0.4
        n = int(dur * SR)
        for i, m in enumerate(notes):
            y = repitch(ch, mtof(m) / f0)
            y = y[:n] if len(y) >= n else np.concatenate([y, np.zeros(n - len(y))])
            y *= adsr(n, 0.3, 0.5, 0.9, 0.45)
            L.put(y, bar * 16, 0.45)
            L.put(sing("u", m, dur, 1.12, 0.006, seed=bar * 3 + i) * adsr(n, 0.35, 0.5, 0.9, 0.45), bar * 16, 0.22)
    L.fx(lambda x: reverb(x, 2.4, 0.35, 6))
    return L.y


def voc_bada():
    L = Loop()
    plan = [(0, "ba", 0, 2), (3, "da", 2, 1), (4, "ba", 1, 2), (7, "dum", 0, 3), (10, "ba", 2, 1),
            (12, "da", 1, 2), (14, "di", 3, 2)]
    for bar in range(4):
        tt = tones(bar, 55, 70)
        for st, syl, k, ln in plan:
            m = tt[min(k, len(tt) - 1)]
            L.put(sing(syl, m, ln * STEP * 0.95, 1.05, 0.0, seed=bar * 10 + st), bar * 16 + st, 0.8)
    L.fx(lambda x: reverb(x, 1.0, 0.12, 7))
    return L.y


def voc_aah():
    L = Loop()
    line = [(0, 0, 76, 16, None), (1, 0, 77, 8, 76), (1, 8, 76, 8, 77), (2, 0, 76, 8, None), (2, 8, 79, 8, 76),
            (3, 0, 74, 16, 79)]
    for bar, st, m, ln, gl in line:
        y = sing("a", m, ln * STEP + 0.05, 1.22, 0.014, glide_from=gl, seed=bar * 7 + st, tilt=1.3)
        y *= adsr(len(y), 0.12, 0.3, 0.9, 0.12)
        L.put(y, bar * 16 + st, 0.7)
    L.fx(lambda x: reverb(delay(x, 4 * STEP, 0.3, 0.3, 3500), 2.0, 0.3, 8))
    return L.y


def voc_dum():
    L = Loop()
    plan = [(0, "dum", 0, 3), (6, "dm", 0, 1), (8, "dum", 12, 2), (11, "m", 0, 1), (14, "dm", 7, 2)]
    for bar in range(4):
        root = chord_at(bar)[0]
        for st, syl, off, ln in plan:
            m = root + off
            if (m % 12) not in SCALE:
                m = root
            s = "du" + syl[-1] if syl == "dm" else syl
            L.put(sing(s, m, ln * STEP * 0.95, 0.85, 0.0, seed=bar * 9 + st, tilt=1.4), bar * 16 + st, 0.95)
    return lp(L.y, 3000)


def voc_orimbux():
    L = Loop()
    words = [(8, "o", 64, 2), (10, "rim", 60, 2), (12, "bux", 57, 3)]
    for bar in (1, 3):
        for st, syl, m, ln in words:
            y = sing(syl, m, ln * STEP * 0.95, 1.0, 0.0, breath=0.02, seed=bar * 5 + st, tilt=0.9)
            k = np.arange(len(y))
            y = y * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 70 * k / SR)))     # ring-mod: a robot voice
            y = y[(k // 5) * 5]                                                   # 8.8 kHz sample & hold
            L.put(y, bar * 16 + st, 0.75)
    for bar in (0, 2):                                   # a whispered echo in the other bars
        L.put(sing("bux", 57, 2 * STEP, 1.0, 0.0, breath=0.3, seed=bar) * 0.4, bar * 16 + 14, 0.5)
    L.fx(lambda x: delay(x, 3 * STEP, 0.3, 0.3, 3000))
    return L.y


# ====================================================================== bonus choruses (4 bars, played twice)
def bonus_coro(KAL, MAR):
    L = Loop()
    L.y += voc_uuu() * 1.0
    hook = [(0, 0, 81, 8), (0, 8, 79, 8), (1, 0, 77, 8), (1, 8, 76, 8), (2, 0, 79, 8), (2, 8, 84, 8),
            (3, 0, 83, 12)]
    for bar, st, m, ln in hook:
        for k, sh in ((0, 1.22), (-12, 1.05)):
            y = sing("a", m + k, ln * STEP, sh, 0.012, seed=bar + st + k, tilt=1.3) * adsr(int(ln * STEP * SR), 0.1,
                                                                                          0.3, 0.9, 0.15)
            L.put(y, bar * 16 + st, 0.45)
    for st in range(0, 64, 2):
        tt = tones(st // 16, 76, 88)
        L.put(KAL.note(tt[(st // 2) % len(tt)], 1.2), st, 0.3)
    L.fx(lambda x: reverb(x, 2.8, 0.35, 9))
    return L.y


def bonus_batalha():
    L = Loop()
    for bar in range(4):
        o = bar * 16
        for st in (0, 3, 6, 8, 11, 14):
            L.put(b_kick(), o + st, 1.0)
        for st in (4, 12):
            L.put(b_snare(seed=st + bar), o + st, 0.8)
        for k in range(32):
            if k % 2 == 1 or (bar == 3 and k > 24):
                L.put(b_hat(seed=k, dec=0.012), o + k / 2.0, 0.28)
    # the 'wub' bass of a beatboxer: a vowel opening and closing
    for bar in range(4):
        root = chord_at(bar)[0] - 12
        n = int(8 * STEP * SR)
        t = np.arange(n) / SR
        src = glottal(np.full(n, mtof(root + 12)), 1.0, seed=bar)
        wob = 0.5 + 0.5 * np.sin(2 * np.pi * (BPM / 60.0) * t - np.pi / 2)
        y = vowel_filter(src, "u", 0.8) * (1 - wob) + vowel_filter(src, "a", 0.8) * wob
        y = lp(y, 1800) * adsr(n, 0.01, 0.2, 0.9, 0.05)
        L.put(y / (np.max(np.abs(y)) + 1e-9), bar * 16 + 8, 0.6)
    return L.y


def bonus_selva():
    L = Loop()
    hi, lo = vc("LogDrumHi_MedM_v2_rr1_Sum.wav"), vc("LogDrumLo_MedM_v2_rr1_Sum.wav")
    # the log drums ring at a pitch: retune them to A and E so the jungle stays in key
    def tune_drum(x, target):
        s = np.abs(np.fft.rfft(x[:16384] * np.hanning(min(16384, len(x))), 1 << 16))
        f = np.fft.rfftfreq(1 << 16, 1.0 / SR)
        band = (f > 60) & (f < 1200)
        fpk = f[band][int(np.argmax(s[band]))]
        m = 12 * math.log2(fpk / 440.0) + 69
        goal = min((target + 12 * k for k in range(-3, 4)), key=lambda g: abs(g - m))
        print("    log drum %.0f Hz -> %s" % (fpk, goal))
        return repitch(x, mtof(goal) / fpk)
    hi, lo = tune_drum(hi, 64), tune_drum(lo, 57)
    for bar in range(4):
        o = bar * 16
        for st, h in ((0, lo), (3, hi), (6, hi), (8, lo), (10, hi), (11, hi), (13, lo), (14, hi)):
            L.put(h, o + st, 0.6)
    did = vc("Didgeridoo1_Sus2_Main.wav")
    f0 = f0_near(did, 70.0, -12, 12, seg=(0.5, 2.0))
    y = repitch(did, mtof(33) / f0)                  # retuned to a low A
    y = y[:N] if len(y) >= N else np.concatenate([y, np.zeros(N - len(y))])
    L.put(y * adsr(len(y), 0.4, 0.5, 0.9, 0.6), 0, 0.45)
    crow = sp("misc_crow")
    L.put(crow, 2 * 16 + 4, 0.35)
    bark = vc("Didgeridoo1_Bark1_Main_rr3.wav")
    for bar in range(4):
        L.put(bark, bar * 16 + 12, 0.35)
    L.fx(lambda x: reverb(x, 1.8, 0.25, 10))
    return L.y


def bonus_robos():
    L = Loop()
    words = [(0, "o", 2), (2, "rim", 2), (4, "bux", 4), (8, "o", 2), (10, "rim", 2), (12, "bux", 3)]
    for bar in range(4):
        tt = tones(bar, 57, 72)
        for st, syl, ln in words:
            for vi, k in enumerate((0, 1, 2)):
                m = tt[min(k + (1 if st >= 8 else 0), len(tt) - 1)]
                y = sing(syl, m, ln * STEP * 0.95, 1.0, 0.0, breath=0.02, seed=bar * 30 + st + vi, tilt=0.9)
                i = np.arange(len(y))
                y = y * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 70 * i / SR)))
                y = y[(i // 5) * 5]
                L.put(y, bar * 16 + st, 0.35)
    gl = sp("glitch_robot2")
    for bar in (1, 3):
        L.put(gl[:int(0.6 * SR)], bar * 16 + 14, 0.4)
    L.fx(lambda x: delay(x, 2 * STEP, 0.25, 0.25, 3500))
    return L.y


def bonus_nave(OCA, MAR):
    L = Loop()
    hook = [(0, 0, 69, 2), (0, 2, 72, 2), (0, 4, 76, 4), (0, 8, 81, 6), (1, 0, 77, 4), (1, 4, 76, 2),
            (1, 6, 72, 2), (1, 8, 69, 8), (2, 0, 72, 2), (2, 2, 76, 2), (2, 4, 79, 4), (2, 8, 84, 6),
            (3, 0, 83, 4), (3, 4, 79, 4), (3, 8, 74, 4), (3, 12, 71, 4)]
    for bar, st, m, ln in hook:
        y = OCA.note(m, ln * STEP + 0.1) * adsr(int((ln * STEP + 0.1) * SR), 0.02, 0.2, 0.9, 0.08)
        L.put(y, bar * 16 + st, 0.6)
        L.put(sing("a", m - 12, ln * STEP, 1.1, 0.01, seed=bar + st, tilt=1.3) * 0.5, bar * 16 + st, 0.4)
    for bar in range(4):
        tt = tones(bar, 60, 79)
        for st in (0, 4, 8, 12):
            for m in tt[:3]:
                L.put(MAR.note(m, 1.0), bar * 16 + st, 0.25)
    L.fx(lambda x: reverb(x, 2.4, 0.3, 11))
    return L.y


# ====================================================================== render + checks
KIT = [  # id, name on screen, category
    ("bumtss", "BUM-TSS", "beat"), ("tchka", "TCHKA", "beat"), ("tabla", "TABLA", "beat"),
    ("cajon", "CAJÓN", "beat"), ("shaker", "SHAKER", "beat"),
    ("zap", "ZAP", "fx"), ("risco", "RISCO", "fx"), ("robo", "ROBÔ", "fx"), ("boing", "BOING", "fx"),
    ("cosmos", "COSMOS", "fx"),
    ("baixo", "BAIXO", "melody"), ("kalimba", "KALIMBA", "melody"), ("ocarina", "OCARINA", "melody"),
    ("marimba", "MARIMBA", "melody"), ("nuvem", "NUVEM", "melody"),
    ("uuu", "UUU", "voice"), ("bada", "BA-DA", "voice"), ("aah", "AAH", "voice"), ("dum", "DUM", "voice"),
    ("orimbux", "O-RIM-BUX", "voice"),
]
BONUS = [  # id, name, what unlocks it
    ("coro", "CORO CÓSMICO", ["uuu", "nuvem", "kalimba"]),
    ("batalha", "BATALHA DE BEATBOX", ["tchka", "dum", "zap"]),
    ("selva", "SELVA ALIEN", ["tabla", "shaker", "ocarina"]),
    ("robos", "DANÇA DOS ROBÔS", ["robo", "orimbux", "baixo"]),
    ("nave", "A NAVE-MÃE", "crew"),        # all 7 singing, with every category on stage
]
LEVEL = {"beat": 0.12, "fx": 0.065, "melody": 0.085, "voice": 0.085, "bonus": 0.10}


def finish(y, cat):
    y = y - np.mean(y)
    y = hp(np.concatenate([y, y]), 30)[N:]                   # DC/rumble out, phase-continuous at the seam
    r = np.sqrt(np.mean(y ** 2)) + 1e-9
    y = y * (LEVEL[cat] / r)
    pk = np.max(np.abs(y))
    if pk > 0.5:                                             # tame peaks so 7 loops can stack
        y = np.tanh(y / 0.5) * 0.5
    return y


def env30(y):
    k = int(SR / FPS_ENV)
    m = len(y) // k
    e = np.sqrt(np.mean(y[:m * k].reshape(m, k) ** 2, axis=1))
    e = e / (np.percentile(e, 95) + 1e-9)
    return [int(min(99, v * 80)) for v in e]


def chroma_check(y):
    """share of tonal energy inside A minor (rough: FFT bins mapped to pitch classes)"""
    s = np.abs(np.fft.rfft(y[:SR * 8] * np.hanning(SR * 8))) ** 2
    f = np.fft.rfftfreq(SR * 8, 1.0 / SR)
    sel = (f > 80) & (f < 2000)
    pc = (np.round(12 * np.log2(f[sel] / 440.0)) + 9) % 12
    tot = s[sel].sum() + 1e-9
    inside = sum(s[sel][pc == p].sum() for p in SCALE)
    return inside / tot


def save(path, y):
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    CACHE[0] = sys.argv[1]
    os.makedirs(CACHE[0], exist_ok=True)
    os.makedirs(OUTD, exist_ok=True)
    print("tuning the CC0 instruments:")
    KAL = Tuned(vc, {69: "Mbira6_Normal_MainSpirit_A4_k1_vl3_rr2.wav", 59: "Mbira6_Normal_MainSpirit_B3_k3_vl3_rr2.wav",
                     61: "Mbira6_Normal_MainSpirit_C#4_k2_vl3_rr2.wav", 54: "Mbira6_Normal_MainSpirit_F#3_k5_vl3_rr2.wav"})
    OCA = Tuned(vc, {57: "StdOcarina_SusVib_A3.wav", 59: "StdOcarina_Sus_B3.wav", 60: "StdOcarina_SusVib_C4.wav",
                     62: "StdOcarina_Sus_D4.wav", 64: "StdOcarina_SusVib_E4.wav", 66: "StdOcarina_SusVib_F#4.wav",
                     68: "StdOcarina_SusVib_G#4.wav", 69: "StdOcarina_SusVib_A4.wav", 72: "StdOcarina_SusVib_C5.wav"},
                seg=(0.3, 0.8))
    MAR = Tuned(vc, {36: "Marimba_hit_Outrigger_C2_med_01.wav", 43: "Marimba_hit_Outrigger_G2_med_01.wav",
                     47: "Marimba_hit_Outrigger_B2_med_01.wav", 53: "Marimba_hit_Outrigger_F3_med_01.wav",
                     60: "Marimba_hit_Outrigger_C4_med_01.wav", 67: "Marimba_hit_Outrigger_G4_med_01.wav",
                     71: "Marimba_hit_Outrigger_B4_med_01.wav", 77: "Marimba_hit_Outrigger_F5_med_01.wav"},
                seg=(0.02, 0.3))
    makers = {
        "bumtss": beat_bumtss, "tchka": beat_tchka, "tabla": beat_tabla, "cajon": beat_cajon, "shaker": beat_shaker,
        "zap": fx_zap, "risco": fx_risco, "robo": fx_robo, "boing": fx_boing, "cosmos": fx_cosmos,
        "baixo": mel_baixo, "kalimba": lambda: mel_kalimba(KAL), "ocarina": lambda: mel_ocarina(OCA),
        "marimba": lambda: mel_marimba(MAR), "nuvem": mel_nuvem,
        "uuu": voc_uuu, "bada": voc_bada, "aah": voc_aah, "dum": voc_dum, "orimbux": voc_orimbux,
        "coro": lambda: bonus_coro(KAL, MAR), "batalha": bonus_batalha, "selva": bonus_selva,
        "robos": bonus_robos, "nave": lambda: bonus_nave(OCA, MAR),
    }
    meta = {"bpm": BPM, "bars": BARS, "frames": N, "env_fps": FPS_ENV, "sounds": [], "bonus": []}
    only = set(sys.argv[2:])
    total = np.zeros(N)
    for sid, name, cat in KIT + [(b[0], b[1], "bonus") for b in BONUS]:
        HITS.clear()
        y = finish(makers[sid](), cat)
        hits = sorted(HITS)
        if not only or sid in only:
            save(os.path.join(OUTD, sid + ".wav"), y)
        if cat != "bonus":
            total += y * 0.5
        seam = abs(y[-1] - y[0])
        tonal = chroma_check(y) if cat in ("melody", "voice", "bonus") else None
        print("  %-8s %-6s rms %.3f peak %.2f seam %.4f%s" % (sid, cat, np.sqrt(np.mean(y ** 2)), np.max(np.abs(y)),
                                                              seam, "  in-key %.0f%%" % (100 * tonal) if tonal else ""))
        entry = {"id": sid, "name": name, "cat": cat, "env": env30(y), "hits": hits}
        if cat == "bonus":
            entry["needs"] = [b for b in BONUS if b[0] == sid][0][2]
            meta["bonus"].append(entry)
        else:
            meta["sounds"].append(entry)
    print("  all 20 at once (x0.5 each, like the app): peak %.2f rms %.3f" % (np.max(np.abs(total)),
                                                                              np.sqrt(np.mean(total ** 2))))
    json.dump(meta, open(os.path.join(OUTD, "kit.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUTD)


if __name__ == "__main__":
    main()
