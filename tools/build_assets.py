"""Build-time asset pipeline for Orimbux Mothership (runs on the dev machine, not the console).

- converts the chosen Sonic Pi CC0 samples to 44.1 kHz s16 stereo WAV (+ a dark low-passed copy)
- renders bitmap font atlases (raw RGBA + JSON metrics) so the console needs no SDL_ttf
- synthesises the intro jingle, metronome clicks and synth wavetables
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "ports", "mothership")
A = os.path.join(APP, "assets")
SRC = "/home/claude/sp/etc/samples"
FONTS = "/home/claude/gf/ofl"
SR = 44100


def wav_write(path, data, sr=SR):
    """data: float array (n,) or (n,2) in -1..1"""
    import wave
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- samples
def build_samples():
    banks = json.load(open(os.path.join(APP, "banks.json")))
    out = os.path.join(A, "samples")
    used = set()
    for bank in banks["banks"]:
        for pad in bank["pads"]:
            used.add(pad["file"])
    for name in sorted(used):
        src = os.path.join(SRC, name + ".flac")
        dst = os.path.join(out, name + ".wav")
        dark = os.path.join(out, name + ".dark.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", str(SR), "-ac", "2",
                        "-sample_fmt", "s16", dst], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        "lowpass=f=520,lowpass=f=520,volume=1.25", "-ar", "22050", "-ac", "1",
                        "-sample_fmt", "s16", dark], check=True)
    print("samples:", len(used))


# ---------------------------------------------------------------- fonts
CHARS = "".join(chr(c) for c in range(32, 127))


def atlas(ttf, size, name, crisp):
    font = ImageFont.truetype(ttf, size)
    asc, desc = font.getmetrics()
    h = asc + desc
    glyphs = {}
    widths = [int(math.ceil(font.getlength(ch))) for ch in CHARS]
    maxw = 1024
    x = y = 0
    pos = []
    for adv in widths:
        if x + adv + 2 > maxw:
            x = 0
            y += h + 2
        pos.append((x, y))
        x += adv + 2
    img = Image.new("L", (maxw, y + h), 0)
    d = ImageDraw.Draw(img)
    if crisp:
        d.fontmode = "1"
    for ch, adv, (gx, gy) in zip(CHARS, widths, pos):
        d.text((gx, gy), ch, font=font, fill=255)
        glyphs[ch] = [gx, gy, adv]
    rgba = Image.merge("RGBA", (Image.new("L", img.size, 255),) * 3 + (img,))
    raw = rgba.tobytes()
    with open(os.path.join(A, "fonts", name + ".rgba"), "wb") as f:
        f.write(raw)
    json.dump({"w": img.size[0], "h": h, "glyphs": glyphs},
              open(os.path.join(A, "fonts", name + ".json"), "w"))


def build_fonts():
    p = os.path.join(FONTS, "pressstart2p", "PressStart2P-Regular.ttf")
    v = os.path.join(FONTS, "vt323", "VT323-Regular.ttf")
    for s in (8, 16, 24, 40):
        atlas(p, s, "p%d" % s, True)
    for s in (20, 28, 44, 76):
        atlas(v, s, "v%d" % s, False)
    for d in ("pressstart2p", "vt323"):
        src = os.path.join(FONTS, d, "OFL.txt")
        open(os.path.join(A, "fonts", d + "-OFL.txt"), "w").write(open(src).read())
    print("fonts ok")


# ---------------------------------------------------------------- synth tables
WAVES = ["SAW", "SQUARE", "TRI", "XENO"]


def cycle(wave, period, bright):
    """one band-limited cycle of `period` samples"""
    f0 = SR / period
    nyq = SR / 2 * (0.45 if bright else 0.15)
    nmax = max(1, int(nyq // f0))
    t = np.arange(period) / period
    y = np.zeros(period)
    for n in range(1, nmax + 1):
        if wave == "SAW":
            a = 1.0 / n
        elif wave == "SQUARE":
            a = (1.0 / n) if n % 2 else 0
        elif wave == "TRI":
            a = (1.0 / (n * n)) * (1 if (n // 2) % 2 == 0 else -1) if n % 2 else 0
        else:  # XENO: formant-ish, odd emphasis around 3rd-7th harmonics
            a = (1.0 / n) * (1.0 + 2.5 * math.exp(-((n - 5) ** 2) / 6.0))
        if not bright:
            a *= 1.0 / (1 + (n / 3.0) ** 2)
        y += a * np.sin(2 * math.pi * n * t)
    y /= (np.max(np.abs(y)) or 1)
    return y * 0.55


def build_synth():
    meta = {"sr": SR, "waves": WAVES, "octaves": {}}
    out = os.path.join(A, "synth")
    for octv in range(1, 7):
        cfreq = 440.0 * 2 ** ((12 * (octv + 1) - 69) / 12.0)  # C of octave (C4=261.6 when octv=4)
        period = int(round(SR / cfreq))
        meta["octaves"][str(octv)] = {"period": period, "freq": SR / period}
        for w in WAVES:
            for b in (True, False):
                y = cycle(w, period, b)
                pcm = (y * 32767).astype("<i2").tobytes()
                fn = "%s_o%d_%s.raw" % (w.lower(), octv, "b" if b else "d")
                open(os.path.join(out, fn), "wb").write(pcm)
    json.dump(meta, open(os.path.join(out, "synth.json"), "w"))
    print("synth ok")


# ---------------------------------------------------------------- jingle + clicks
def tone(freq, dur, kind="sq", vol=0.3, duty=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = (t * freq) % 1.0
    if kind == "sq":
        y = np.where(ph < duty, 1.0, -1.0)
    elif kind == "tri":
        y = 4 * np.abs(ph - 0.5) - 1
    else:
        y = np.random.uniform(-1, 1, n)
    env = np.minimum(1, np.arange(n) / (SR * 0.004)) * np.exp(-t * 3.0)
    return y * env * vol


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def build_jingle():
    bpm = 150
    step = 60.0 / bpm / 4  # 16ths
    total = int(SR * 5.4)
    L = np.zeros(total)
    R = np.zeros(total)

    def put(buf, start_step, sig):
        i = int(start_step * step * SR)
        j = min(total, i + len(sig))
        buf[i:j] += sig[: j - i]

    # arpeggio: Cm -> Ab -> Bb -> C (alien-ish with a #11 sparkle)
    chords = [[60, 63, 67, 72], [56, 60, 63, 68], [58, 62, 65, 70], [60, 64, 66, 72]]
    for ci, ch in enumerate(chords):
        for k in range(8):
            m = ch[k % 4] + (12 if k >= 4 else 0)
            s = tone(note(m), step * 0.95, "sq", 0.16, 0.25)
            put(L, ci * 8 + k, s)
            put(R, ci * 8 + k + 0.5, s * 0.6)  # stereo echo
    # bass
    for ci, root in enumerate([36, 32, 34, 36]):
        for k in (0, 3, 6):
            put(L, ci * 8 + k, tone(note(root), step * 2, "tri", 0.35))
            put(R, ci * 8 + k, tone(note(root), step * 2, "tri", 0.35))
    # final power chord + noise sweep
    for m in (48, 55, 60, 67, 72):
        s = tone(note(m), 1.6, "sq", 0.09, 0.5) * np.exp(-np.arange(int(SR * 1.6)) / SR * 1.2)
        put(L, 32, s)
        put(R, 32, s)
    nz = tone(0, 0.5, "nz", 0.12)
    put(L, 31, nz)
    put(R, 31, nz)
    stereo = np.stack([L, R], 1)
    stereo /= max(1.0, np.max(np.abs(stereo)) / 0.9)
    wav_write(os.path.join(A, "jingle.wav"), stereo)

    # UI blips + metronome clicks
    wav_write(os.path.join(A, "click_hi.wav"), tone(1760, 0.05, "sq", 0.35, 0.5))
    wav_write(os.path.join(A, "click_lo.wav"), tone(1175, 0.04, "sq", 0.25, 0.5))
    wav_write(os.path.join(A, "ui_move.wav"), tone(988, 0.035, "sq", 0.12, 0.25))
    ok = np.concatenate([tone(1319, 0.04, "sq", 0.14, 0.25), tone(1976, 0.06, "sq", 0.14, 0.25)])
    wav_write(os.path.join(A, "ui_ok.wav"), ok)
    print("jingle ok")


if __name__ == "__main__":
    for d in ("samples", "fonts", "synth"):
        os.makedirs(os.path.join(A, d), exist_ok=True)
    what = sys.argv[1:] or ["samples", "fonts", "synth", "jingle"]
    if "samples" in what:
        build_samples()
    if "fonts" in what:
        build_fonts()
    if "synth" in what:
        build_synth()
    if "jingle" in what:
        build_jingle()
