"""EAR LAB tone: a soft FM electric piano rendered at C3, C4 and C5 (the console pitch-shifts +-6 semitones)."""
import os, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_assets import A  # noqa

OUT = os.path.join(A, "ear")
SR = 44100


def epiano(midi, dur=1.8):
    f = 440.0 * 2 ** ((midi - 69) / 12.0)
    t = np.arange(int(dur * SR)) / SR
    idx = 1.6 * np.exp(-t * 5.0) + 0.25                       # bright attack, mellow body
    mod = np.sin(2 * np.pi * f * t) * idx
    tine = np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 40) * 0.12
    car = np.sin(2 * np.pi * f * t + mod) + tine
    env = (1 - np.exp(-t * 400)) * np.exp(-t * (1.6 + f / 900.0))
    rel = np.clip((dur - t) / 0.08, 0, 1)
    x = car * env * rel
    return x / np.max(np.abs(x)) * 0.8


def main():
    os.makedirs(OUT, exist_ok=True)
    for m in (48, 60, 72):
        x = epiano(m)
        pcm = (x * 32767).astype("<i2")
        with wave.open(os.path.join(OUT, "ep_%d.wav" % m), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())
    print("ear tones ok")


if __name__ == "__main__":
    main()
