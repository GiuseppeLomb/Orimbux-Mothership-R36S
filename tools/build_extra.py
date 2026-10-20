"""Build-time assets for XENO PET and DEMO 64K (needs numpy; runs on the dev machine only)."""
import math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_assets import wav_write, A, SR  # noqa

DEMO = os.path.join(A, "demo")
PET = os.path.join(A, "pet")
BPM = 140.0
STEP = 60.0 / BPM / 4.0  # 16th note
BARS = 36


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def env_ad(n, a=0.003, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))
    return e


def pulse(freq, n, duty=0.5, vib=0.0, vibrate=6.0):
    t = np.arange(n) / SR
    f = freq * (1 + vib * np.sin(2 * math.pi * vibrate * t))
    ph = np.cumsum(f / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def tri(freq, n):
    ph = (np.arange(n) * freq / SR) % 1.0
    return 4 * np.abs(ph - 0.5) - 1


# ------------------------------------------------------------------ drums
def kick(n=int(SR * 0.22)):
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = np.cumsum(f / SR)
    return np.sin(2 * math.pi * ph) * np.exp(-t * 11) * 1.0


def snare(n=int(SR * 0.18)):
    t = np.arange(n) / SR
    rng = np.random.RandomState(7)
    nz = rng.uniform(-1, 1, n)
    nz = nz - np.concatenate([[0], nz[:-1]]) * 0.6
    tone = np.sin(2 * math.pi * 190 * t)
    return (nz * 0.7 + tone * 0.4) * np.exp(-t * 18)


def hat(n=int(SR * 0.035), seed=3):
    rng = np.random.RandomState(seed)
    nz = rng.uniform(-1, 1, n)
    nz = nz - np.concatenate([[0], nz[:-1]])
    return nz * np.exp(-np.arange(n) / SR * 90) * 0.5


# ------------------------------------------------------------------ demo music
CHORDS = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]   # Am F C G
ROOTS = [45, 41, 48, 43]
MELODY = [(0, 69, 6), (6, 72, 2), (8, 76, 4), (12, 74, 4), (16, 72, 6), (22, 71, 2), (24, 69, 8),
          (32, 69, 4), (36, 72, 4), (40, 77, 6), (46, 76, 2), (48, 74, 8), (56, 72, 4), (60, 74, 4),
          (64, 76, 6), (70, 79, 2), (72, 76, 4), (76, 74, 4), (80, 72, 8), (88, 74, 4), (92, 76, 4),
          (96, 74, 6), (102, 71, 2), (104, 67, 8), (112, 71, 4), (116, 74, 4), (120, 79, 8)]


def build_demo_music():
    total = int(SR * (BARS * 16 * STEP + 2.5))
    L = np.zeros(total)
    R = np.zeros(total)

    def put(sig, step, pan=0.0, vol=1.0, delay_steps=0.0):
        i = int((step + delay_steps) * STEP * SR)
        if i >= total:
            return
        j = min(total, i + len(sig))
        s = sig[: j - i] * vol
        L[i:j] += s * (1 - max(0, pan))
        R[i:j] += s * (1 + min(0, pan))

    K, S, Hc, Ho = kick(), snare(), hat(), hat(int(SR * 0.12), 5)
    for bar in range(BARS):
        b0 = bar * 16
        sect = bar // 8
        chord = CHORDS[(bar // 2) % 4]
        root = ROOTS[(bar // 2) % 4]
        final = bar >= 32
        # ---- pad (intro + outro + under everything quietly)
        if bar % 2 == 0 and not final:
            n = int(SR * 32 * STEP)
            pad = sum(tri(mtof(m), n) + tri(mtof(m) * 1.004, n) for m in chord)
            e = np.minimum(1, np.arange(n) / (SR * 0.6)) * np.minimum(1, (n - np.arange(n)) / (SR * 0.4))
            put(pad * e, b0, 0, 0.05 if sect == 0 else 0.03)
        # ---- arpeggio
        if (bar >= 2 and not final) and not (bar == 31):
            for k in range(16):
                m = chord[k % 3] + 12 * ((k // 3) % 2) + 12
                n = int(SR * STEP * 0.9)
                s = pulse(mtof(m), n, 0.125 if sect < 2 else 0.25) * env_ad(n, 0.002, 0.07)
                v = 0.10 if sect == 2 else 0.13
                put(s, b0 + k, -0.4, v)
                put(s, b0 + k, 0.5, v * 0.45, delay_steps=3)  # echo
        if bar == 31:
            for k in range(16):
                m = chord[(15 - k) % 3] + 24
                n = int(SR * STEP)
                put(pulse(mtof(m), n, 0.25) * env_ad(n, 0.002, 0.09), b0 + k, 0, 0.13)
        # ---- drums
        if 4 <= bar < 8:
            for k in range(0, 16, 2):
                put(Hc, b0 + k, 0.3, 0.5)
        if 8 <= bar < 31:
            for k in (0, 10):
                put(K, b0 + k, 0, 0.9)
            if sect >= 2:
                put(K, b0 + 7, 0, 0.5)
            for k in (4, 12):
                put(S, b0 + k, 0, 0.55)
            for k in range(0, 16, 2):
                put(Hc if k % 4 else Ho, b0 + k, 0.3, 0.35)
            if sect == 3:
                for k in range(1, 16, 2):
                    put(Hc, b0 + k, -0.3, 0.2)
        if bar == 30:
            for k in range(8, 16):
                put(S, b0 + k, 0, 0.25 + 0.04 * (k - 8))
        if bar == 7:
            n = int(SR * 16 * STEP)
            rng = np.random.RandomState(11)
            nz = rng.uniform(-1, 1, n)
            nz = nz - np.concatenate([[0], nz[:-1]])
            put(nz * np.linspace(0, 0.35, n), b0)
        # ---- bass
        if 8 <= bar < 32:
            for k, oct_ in ((0, 0), (3, 0), (6, 12), (8, 0), (10, 0), (14, 12)):
                n = int(SR * STEP * 1.8)
                s = pulse(mtof(root - 12 + oct_ + 12), n, 0.25) * env_ad(n, 0.002, 0.14)
                put(s, b0 + k, 0, 0.22)
        # ---- lead melody
        if 16 <= bar < 32 and bar != 31:
            base = (bar - 16) % 8 * 16
            for st, m, ln in MELODY:
                if base <= st < base + 16:
                    n = int(SR * STEP * ln)
                    mm = m + (12 if sect == 3 and (st // 32) % 2 == 1 else 0)
                    s = pulse(mtof(mm), n, 0.5, vib=0.006) * env_ad(n, 0.01, 0.35 + ln * 0.03)
                    put(s, b0 + (st - base), 0.15, 0.14)
                    put(s, b0 + (st - base), -0.4, 0.05, delay_steps=4)
    # ---- final chord
    b0 = 32 * 16
    n = int(SR * 4.5)
    for m in (45, 57, 60, 64, 69, 76):
        s = pulse(mtof(m), n, 0.5) * env_ad(n, 0.004, 1.3)
        put(s, b0, 0, 0.06)
    put(K, b0, 0, 1.0)
    put(snare(int(SR * 0.4)), b0, 0, 0.5)
    st = np.stack([L, R], 1)
    st /= max(1.0, np.max(np.abs(st)) / 0.92)
    wav_write(os.path.join(DEMO, "demo_music.wav"), st)
    print("demo music %.1fs" % (len(L) / SR))


# ------------------------------------------------------------------ demo maps
def build_maps():
    W, H = 320, 240
    y, x = np.mgrid[0:H, 0:W].astype(np.float64)
    cx, cy = W / 2.0, H / 2.0
    v = (np.sin(x / 16.0) + np.sin(y / 8.0) + np.sin((x + y) / 16.0)
         + np.sin(np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / 8.0)
         + np.sin(np.sqrt((x * 0.7) ** 2 + (y * 1.3) ** 2) / 11.0))
    v = (v - v.min()) / (v.max() - v.min())
    open(os.path.join(DEMO, "plasma.idx"), "wb").write((v * 255).astype(np.uint8).tobytes())
    dx, dy = x - cx + 0.5, y - cy + 0.5
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    d = (np.floor(2048.0 / r)).astype(np.int64) % 16
    a = (np.floor((np.arctan2(dy, dx) / (2 * math.pi) + 0.5) * 64)).astype(np.int64) % 16
    idx = (d * 16 + a).astype(np.uint8)
    open(os.path.join(DEMO, "tunnel.idx"), "wb").write(idx.tobytes())
    # fog overlay (RGBA): black, alpha high near centre (far away)
    alpha = np.clip(1.15 - r / 120.0, 0, 1) ** 1.4
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    open(os.path.join(DEMO, "fog.rgba"), "wb").write(rgba.tobytes())
    print("maps ok")


# ------------------------------------------------------------------ pet sounds
def seq(notes, duty=0.25, vol=0.25, dec=0.08):
    out = []
    for m, dur in notes:
        n = int(SR * dur)
        if m is None:
            out.append(np.zeros(n))
        else:
            out.append(pulse(mtof(m), n, duty) * env_ad(n, 0.002, dec) * vol)
    return np.concatenate(out)


def build_pet_sounds():
    s = {
        "chirp": seq([(84, 0.05), (88, 0.05), (91, 0.07)]),
        "happy": seq([(79, 0.06), (83, 0.06), (86, 0.06), (91, 0.12)], 0.5),
        "sad": seq([(76, 0.12), (73, 0.12), (69, 0.25)], 0.5, 0.2, 0.2),
        "eat": seq([(60, 0.04), (None, 0.04), (62, 0.04), (None, 0.04), (60, 0.04), (None, 0.04), (64, 0.06)], 0.5, 0.25),
        "call": seq([(93, 0.08), (None, 0.05), (93, 0.08), (None, 0.05), (93, 0.08)], 0.5, 0.22),
        "hatch": seq([(72, 0.06), (76, 0.06), (79, 0.06), (84, 0.06), (88, 0.06), (91, 0.2)], 0.25, 0.25, 0.2),
        "poop": seq([(48, 0.08), (43, 0.14)], 0.5, 0.3, 0.1),
        "clean": seq([(96, 0.03), (91, 0.03), (98, 0.03), (93, 0.03), (100, 0.05)], 0.125, 0.2),
        "heal": seq([(72, 0.07), (79, 0.07), (84, 0.14)], 0.25),
        "star": seq([(96, 0.04), (103, 0.06)], 0.25, 0.2, 0.05),
        "evolve": seq([(60, 0.08), (64, 0.08), (67, 0.08), (72, 0.08), (76, 0.08), (79, 0.08), (84, 0.3)], 0.5, 0.22, 0.3),
        "bye": seq([(84, 0.2), (79, 0.2), (76, 0.2), (72, 0.6)], 0.5, 0.2, 0.5),
    }
    for k, v in s.items():
        wav_write(os.path.join(PET, k + ".wav"), v)
    print("pet sounds", len(s))


if __name__ == "__main__":
    # the old DEMO 64K (music + maps) was replaced by the trailer (tools/build_trailer.py); pass "music"/"maps"
    # explicitly to rebuild those files. The app's fonts (k16..kb48, with the Portuguese accents) are made by
    # tools/build_font.py: the ASCII-only font builder that lived here is gone (it would have overwritten them).
    what = sys.argv[1:] or ["pet"]
    if "font" in what:
        sys.exit("the fonts are made by tools/build_font.py")
    for d in ((DEMO,) if ("music" in what or "maps" in what) else ()) + (PET,):
        os.makedirs(d, exist_ok=True)
    if "music" in what:
        build_demo_music()
    if "maps" in what:
        build_maps()
    if "pet" in what:
        build_pet_sounds()
