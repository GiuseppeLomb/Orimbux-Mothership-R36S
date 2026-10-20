"""LOOP REACTOR sample packs (v1.10): free CC0 sounds of other genres -> assets/samples (+ dark copies).

Sources, both CC0 1.0 (public domain), pinned to the commits below:
- VCSL, the Versilian Community Sample Library (github.com/sgossner/VCSL): world, Latin, orchestral, mallets, kit
- the Sonic Pi sample library (github.com/sonic-pi-net/sonic-pi, etc/samples, from freesound.org): 808, techno, loops

    python tools/build_packs.py CACHE_DIR

Downloads what is missing into CACHE_DIR (use an empty folder of its own), then writes 44.1 kHz s16 WAVs and the
22.05 kHz mono "dark" copies (low-passed twice at 520 Hz, x1.25, like build_assets.py does with ffmpeg) next to the
other samples, plus CREDITS-packs.md. It only writes the files listed here: the old samples are never touched.
The banks themselves are in ports/mothership/banks.json. Needs numpy and soundfile (pip install soundfile).
"""
import math, os, sys, urllib.parse, urllib.request, wave
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ports", "mothership", "assets", "samples")
SR = 44100
VCSL = "https://raw.githubusercontent.com/sgossner/VCSL/c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e/"
SPI = "https://raw.githubusercontent.com/sonic-pi-net/sonic-pi/abbb2fdfe5820ea73c47957a453f4667ea52f0b3/etc/samples/"
MEM = "Membranophones/Struck Membranophones/"
IDI = "Idiophones/Struck Idiophones/"
PLK = "Idiophones/Plucked Idiophones/"
# name in assets/samples, source ("sp:" Sonic Pi sample / "vcsl:" path in VCSL), max seconds (0 = a loop: kept
# whole and at its level), start offset in seconds
SOUNDS = [
    # HIP HOP
    ("bd_808", "sp:bd_808", 1.0, 0), ("perc_snap", "sp:perc_snap", 1.0, 0), ("hat_cab", "sp:hat_cab", 0.5, 0),
    ("vcsl_clap", "vcsl:" + IDI + "Claps/Clap_rr1.wav", 0.8, 0), ("loop_mika", "sp:loop_mika", 0, 0),
    ("bass_hit_c", "sp:bass_hit_c", 1.0, 0), ("bass_voxy_hit_c", "sp:bass_voxy_hit_c", 1.0, 0),
    ("vinyl_backspin", "sp:vinyl_backspin", 1.5, 0),
    # TECHNO
    ("bd_klub", "sp:bd_klub", 1.0, 0), ("elec_snare", "sp:elec_snare", 1.0, 0), ("hat_noiz", "sp:hat_noiz", 0.6, 0),
    ("ride_via", "sp:ride_via", 2.5, 0), ("loop_industrial", "sp:loop_industrial", 0, 0),
    ("loop_compus", "sp:loop_compus", 0, 0), ("glitch_perc1", "sp:glitch_perc1", 1.5, 0),
    ("hat_metal", "sp:hat_metal", 0.6, 0),
    # LATINO
    ("vcsl_conga", "vcsl:" + MEM + "Conga/Conga_HitN_v3_rr1_Sum.wav", 1.0, 0),
    ("vcsl_bongo", "vcsl:" + MEM + "Bongos/BongoH_Hit1_v3_rr1_Mid.wav", 0.8, 0),
    ("vcsl_cajon", "vcsl:" + IDI + "Cajon/Cajon_hit3_f_rr1.wav", 0.6, 0),
    ("vcsl_shaker", "vcsl:" + IDI + "Shaker, Small/Mid_ShakerDouble_Down_rr1.wav", 0.4, 0),
    ("vcsl_agogo", "vcsl:" + IDI + "Agogo Bells/Agogo_High_v3_rr1_Mid.wav", 0.6, 0),
    ("vcsl_claves", "vcsl:" + IDI + "Claves/Claves1_Hit_v3_rr1_Mid.wav", 0.5, 0),
    ("vcsl_guiro", "vcsl:" + IDI + "Guiro/Guiro_Med_rr1_Mid.wav", 1.4, 0),
    ("vcsl_cowbell", "vcsl:" + IDI + "Cowbells/Cowbell1_Hit_v3_rr1_Mid.wav", 0.7, 0),
    # MUNDO
    ("vcsl_darbuka", "vcsl:" + MEM + "Darbuka/Darbuka_1_hit_vl2_rr1.wav", 1.0, 0),
    ("vcsl_frame", "vcsl:" + MEM + "Frame Drum/HDrumL_Hit_v3_rr1_Sum.wav", 1.4, 0),
    ("vcsl_logdrum", "vcsl:" + IDI + "Slit Drum/LogDrumLo_MedM_v3_rr1_Sum.wav", 0.8, 0),
    ("vcsl_didge", "vcsl:Aerophones/Lip Aerophones/Didgeridoo/Didgeridoo1_Bark1_Main_rr3.wav", 0.6, 0),
    ("vcsl_kalimba", "vcsl:" + PLK + "Kalimba, Tanzania/MBira3_pluck_Main_C#4_k5_50_100_rr2.wav", 1.8, 0),
    ("vcsl_balafon", "vcsl:" + IDI + "Balafon/Hard Mallet/EthnicXylo_hardM_C4_vl3_rr1_Mid.wav", 0.8, 0),
    ("vcsl_mbira", "vcsl:" + PLK + "Mbira Mavembe (Gandanga), Zimbabwe, Low G/Mbira5_Normal_MainSpirit_C3_k9_vl2_rr1.wav",
     3.0, 0),
    ("loop_safari", "sp:loop_safari", 0, 0),
    # EPICO
    ("vcsl_timpani", "vcsl:" + MEM + "Timpani 1/Hit/Timpani1_Hit_v4_rr1_Sum.wav", 2.5, 0),
    ("vcsl_bassdrum", "vcsl:" + MEM + "Bass Drum 2/bassdrum_hit_ff.wav", 3.0, 0),
    ("vcsl_crash", "vcsl:" + IDI + "Clash Cymbals 1/cymbal_crash1_ff2.wav", 3.0, 0),
    ("vcsl_rope_snare", "vcsl:" + MEM + "Snare Drum, Rope Tension/Hi/RopeSnare_hi_sn_Main_vl4_rr1.wav", 1.4, 0),
    ("vcsl_gong", "vcsl:" + IDI + "Gong 1/gong_f.wav", 4.0, 0),
    ("vcsl_bells", "vcsl:" + IDI + "Tubular Bells 1/chimes_C4_ff_rr2.wav", 4.0, 0),
    ("vcsl_glock", "vcsl:" + IDI + "Glockenspiel/glock_loud_C6_01.wav", 2.5, 0),
    ("vcsl_roll", "vcsl:" + MEM + "Bass Drum 2/bassdrum_cresc_short.wav", 4.5, 3.0),
    # LO-FI
    ("vcsl_fm_piano", "vcsl:Electrophones/TX81Z/FM Piano/FMPiano_C4_vl2.wav", 3.0, 0),
    ("vcsl_vibes", "vcsl:" + IDI + "Vibraphone/Hard Mallets/Vibes_hard_C3_v3_rr1_Main.wav", 3.0, 0),
    ("vcsl_marimba", "vcsl:" + IDI + "Marimba/Marimba_hit_Outrigger_C4_med_01.wav", 1.8, 0),
    ("vcsl_clavi", "vcsl:Electrophones/TX81Z/Clavisynth/Clavisynth_C4_vl2.wav", 1.6, 0),
    ("guit_em9", "sp:guit_em9", 6.0, 0), ("vinyl_hiss", "sp:vinyl_hiss", 0, 0), ("loop_garzul", "sp:loop_garzul", 0, 0),
    ("tbd_highkey_c4", "sp:tbd_highkey_c4", 1.2, 0),
    # ROCK
    ("drum_heavy_kick", "sp:drum_heavy_kick", 1.0, 0),
    ("vcsl_snare", "vcsl:" + MEM + "Snare Drum, Modern 1/Snare2_HitSN_v6_rr1_Mid.wav", 0.6, 0),
    ("vcsl_hihat", "vcsl:" + IDI + "Hi-Hat Cymbal/HiHat_HitC_v3_rr1_Mid.wav", 0.5, 0),
    ("vcsl_tom", "vcsl:" + MEM + "Tom 1/Mallet/TomH_HitM_v4_rr1_Mid.wav", 0.9, 0),
    ("guit_e_fifths", "sp:guit_e_fifths", 4.0, 0), ("guit_e_slide", "sp:guit_e_slide", 3.0, 0),
    ("vcsl_open_hat", "vcsl:" + IDI + "Hi-Hat Cymbal/HiHat_HitO_rr1_Mid.wav", 2.0, 0),
    ("drum_splash_hard", "sp:drum_splash_hard", 2.5, 0),
]


def url(src):
    kind, path = src.split(":", 1)
    if kind == "sp":
        return SPI + path + ".flac"
    return VCSL + urllib.parse.quote(path)


def fetch(src, cache):
    dst = os.path.join(cache, os.path.basename(src.split(":", 1)[1]) + (".flac" if src.startswith("sp:") else ""))
    if not os.path.exists(dst):
        with urllib.request.urlopen(url(src)) as r:
            data = r.read()
        with open(dst + ".part", "wb") as f:
            f.write(data)
        os.replace(dst + ".part", dst)
    return dst


def resample(x, sr):
    """band-limited (FFT) resampling of an (n, ch) array to SR"""
    if sr == SR:
        return x
    n = len(x)
    xp = np.concatenate([x, np.zeros((n // 4 + 1024, x.shape[1]))])
    big = len(xp)
    m = int(round(big * SR / float(sr)))
    spec = np.fft.rfft(xp, axis=0)
    keep = min(len(spec), m // 2 + 1)
    out = np.zeros((m // 2 + 1, x.shape[1]), dtype=complex)
    out[:keep] = spec[:keep]
    return np.fft.irfft(out, m, axis=0)[:int(round(n * SR / float(sr)))] * (m / float(big))


def shot(x, max_s, start):
    """a one-shot: from its first sound (or `start`), tail cut below -50 dB, capped, faded, peak at -1 dB"""
    x = x[int(start * SR):]
    x = x * (0.89 / (np.max(np.abs(x)) or 1.0))
    mono = np.max(np.abs(x), axis=1)
    if not start:
        nz = np.nonzero(mono > 0.004)[0]
        if len(nz):
            x, mono = x[max(0, nz[0] - 16):], mono[max(0, nz[0] - 16):]
    above = np.nonzero(mono > 0.003)[0]
    cap = int(max_s * SR)
    end = min(len(x), (above[-1] + 1) if len(above) else len(x), cap)
    x = x[:end].copy()
    fade = min(len(x), int(0.03 * SR) if end < cap else int(max(0.25, 0.2 * max_s) * SR))
    if fade:
        x[-fade:] *= (np.linspace(1, 0, fade) ** 2)[:, None]
    return x * (0.89 / (np.max(np.abs(x)) or 1.0))


def lowpass(x, f=520.0):
    """ffmpeg's `lowpass` (2-pole RBJ biquad, Q 0.707) on a mono array"""
    w = 2 * math.pi * f / SR
    al = math.sin(w) / (2 * 0.7071)
    a0 = 1 + al
    b0 = b2 = (1 - math.cos(w)) / 2 / a0
    b1 = (1 - math.cos(w)) / a0
    a1, a2 = -2 * math.cos(w) / a0, (1 - al) / a0
    out = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x.tolist()):
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, y
        out[i] = y
    return np.array(out)


def write(path, x, sr):
    pcm = (np.clip(x, -1, 1) * 32767).round().astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    cache = sys.argv[1]
    if not os.path.isdir(cache):
        os.makedirs(cache)
    total, credits = 0, []
    for name, src, max_s, start in SOUNDS:
        x, sr = sf.read(fetch(src, cache), always_2d=True)
        x = resample(x[:, :2], sr)
        if max_s:
            x = shot(x.mean(axis=1, keepdims=True), max_s, start)     # a short hit: one channel is enough
        elif np.max(np.abs(x[:, 0] - x[:, -1])) < 0.002:
            x = x[:, :1]                                              # a loop keeps its stereo, if it has any
        main_path = os.path.join(OUT, name + ".wav")
        write(main_path, x[:, 0] if x.shape[1] == 1 else x, SR)
        dark = lowpass(lowpass(x.mean(axis=1))) * 1.25
        write(os.path.join(OUT, name + ".dark.wav"), dark[::2], SR // 2)
        total += os.path.getsize(main_path) + os.path.getsize(os.path.join(OUT, name + ".dark.wav"))
        kind, path = src.split(":", 1)
        credits.append("* `%s` - %s" % (name, ("VCSL: " + path) if kind == "vcsl" else ("Sonic Pi: `:%s`" % path)))
    with open(os.path.join(OUT, "CREDITS-packs.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Sample packs (v1.10)\n\nAll CC0 1.0 (public domain): "
                "http://creativecommons.org/publicdomain/zero/1.0/\n\n"
                "* VCSL, the Versilian Community Sample Library by Versilian Studios: https://github.com/sgossner/VCSL "
                "(commit c1ea7bc)\n* the Sonic Pi sample library (originals and links in "
                "CREDITS-sonic-pi-samples.md): https://github.com/sonic-pi-net/sonic-pi (commit abbb2fd)\n\n"
                "Trimmed, normalised and converted with tools/build_packs.py.\n\n" + "\n".join(credits) + "\n")
    print("packs: %d sounds, %.1f MB" % (len(SOUNDS), total / 1e6))


if __name__ == "__main__":
    main()
