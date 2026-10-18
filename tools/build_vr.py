"""VOID RUNNER audio: sfx + two looping chiptune tracks (dev machine only, needs numpy)."""
import math, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_assets import wav_write, A, SR          # noqa
from build_extra import mtof, env_ad, pulse, tri, kick, snare, hat, seq   # noqa

OUT = os.path.join(A, "vr")


def noise(n, seed=1):
    return np.random.RandomState(seed).uniform(-1, 1, n)


def sweep(f0, f1, dur, duty=0.5, vol=0.3, dec=None):
    n = int(SR * dur)
    f = np.geomspace(f0, f1, n)
    ph = np.cumsum(f / SR) % 1.0
    s = np.where(ph < duty, 1.0, -1.0)
    e = env_ad(n, 0.002, dec or dur * 0.6)
    return s * e * vol


def sfx():
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    boom = noise(n, 3) * np.exp(-t * 14) * 0.5 + np.sin(2 * math.pi * 60 * t) * np.exp(-t * 10) * 0.5
    n2 = int(SR * 1.6)
    t2 = np.arange(n2) / SR
    collapse = (noise(n2, 5) * np.exp(-t2 * 2.5) * 0.4 +
                np.sin(2 * math.pi * np.cumsum(np.geomspace(400, 30, n2)) / SR) * np.exp(-t2 * 1.6) * 0.6)
    n3 = int(SR * 1.0)
    t3 = np.arange(n3) / SR
    rum = noise(n3, 9)
    k = 60
    rum = np.convolve(rum, np.ones(k) / k, mode="same") * 6
    rum = rum * 0.5 + np.sin(2 * math.pi * 38 * t3) * 0.35
    fade = int(SR * 0.05)
    rum[:fade] *= np.linspace(0, 1, fade)
    rum[-fade:] *= np.linspace(1, 0, fade)
    s = {
        "bolt": sweep(1800, 900, 0.06, 0.25, 0.12),
        "zap": np.concatenate([sweep(2400, 600, 0.03, 0.5, 0.12), sweep(2000, 500, 0.04, 0.5, 0.1)]),
        "boom": boom,
        "hit": sweep(500, 200, 0.04, 0.5, 0.1),
        "pop": sweep(900, 120, 0.08, 0.5, 0.14),
        "xp": seq([(96, 0.03), (101, 0.04)], 0.25, 0.08, 0.03),
        "lvlup": seq([(72, 0.06), (76, 0.06), (79, 0.06), (84, 0.06), (88, 0.14)], 0.25, 0.2, 0.15),
        "dash": sweep(200, 1400, 0.12, 0.5, 0.15),
        "hurt": sweep(300, 80, 0.15, 0.5, 0.25),
        "collapse": collapse,
        "win": seq([(72, 0.1), (76, 0.1), (79, 0.1), (84, 0.2), (79, 0.1), (84, 0.4)], 0.5, 0.2, 0.3),
        "alarm": seq([(81, 0.1), (None, 0.05), (81, 0.1), (None, 0.05), (81, 0.1)], 0.5, 0.16),
        "rumble": rum,
        "ring": sweep(700, 1100, 0.05, 0.125, 0.06),
    }
    for k_, v in s.items():
        wav_write(os.path.join(OUT, k_ + ".wav"), v)
    print("vr sfx", len(s))


def track(name, bpm, bars, chords, roots, intense):
    step = 60.0 / bpm / 4
    total = int(SR * bars * 16 * step)
    L = np.zeros(total)
    R = np.zeros(total)

    def put(sig, st, pan=0.0, vol=1.0):
        i = int(st * step * SR) % total
        j = i + len(sig)
        s = sig * vol
        if j <= total:
            L[i:j] += s * (1 - max(0, pan))
            R[i:j] += s * (1 + min(0, pan))
        else:              # wrap around so the loop is seamless
            a = total - i
            L[i:] += s[:a] * (1 - max(0, pan))
            R[i:] += s[:a] * (1 + min(0, pan))
            L[:j - total] += s[a:] * (1 - max(0, pan))
            R[:j - total] += s[a:] * (1 + min(0, pan))
    K, S, Hh = kick(), snare(), hat()
    for bar in range(bars):
        b0 = bar * 16
        ch = chords[(bar // 2) % len(chords)]
        root = roots[(bar // 2) % len(roots)]
        if bar % 2 == 0:
            n = int(SR * 32 * step)
            pad = sum(tri(mtof(m), n) + tri(mtof(m) * 1.005, n) for m in ch)
            e = np.minimum(1, np.arange(n) / (SR * 0.8)) * np.minimum(1, (n - np.arange(n)) / (SR * 0.5))
            put(pad * e, b0, 0, 0.035)
        for k in range(16):
            if k % 2 == 0 or intense:
                m = root + (12 if k % 4 == 2 else 0)
                nn = int(SR * step * 0.9)
                put(pulse(mtof(m), nn, 0.25) * env_ad(nn, 0.002, 0.09), b0 + k, 0, 0.16)
        for k in range(0, 16, 4 if not intense else 2):
            m = ch[(k // 2) % 3] + 24
            nn = int(SR * step * 1.6)
            put(pulse(mtof(m), nn, 0.125) * env_ad(nn, 0.002, 0.12), b0 + k + 1, -0.4, 0.06)
            put(pulse(mtof(m), nn, 0.125) * env_ad(nn, 0.002, 0.12), b0 + k + 4, 0.5, 0.03)
        for k in (0, 6, 10) if intense else (0, 10):
            put(K, b0 + k, 0, 0.8)
        for k in (4, 12):
            put(S, b0 + k, 0, 0.45)
        for k in range(0, 16, 2):
            put(Hh, b0 + k + 1, 0.3, 0.25)
    st = np.stack([L, R], 1)
    st /= max(1.0, np.max(np.abs(st)) / 0.9)
    wav_write(os.path.join(OUT, name + ".wav"), st)
    print(name, "%.1fs" % (total / SR))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sfx()
    track("music_run", 112, 16, [[57, 60, 64], [53, 57, 60], [55, 58, 62], [52, 55, 59]], [33, 29, 31, 28], False)
    track("music_boss", 132, 16, [[50, 53, 57], [51, 55, 58], [50, 53, 57], [49, 52, 56]], [26, 27, 26, 25], True)
