"""BEAT FORGE kit: Sonic Pi CC0 one-shots -> trimmed 44.1 kHz mono s16 wavs in assets/forge + kit.json."""
import json, os, subprocess, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_assets import A, SRC  # noqa

OUT = os.path.join(A, "forge")
SR = 44100
# id, name, max seconds, samples (first = default)
KIT = [
    ("kick", "KICK", 0.9, ["bd_haus", "bd_808", "bd_boom", "bd_klub", "bd_fat", "bd_tek", "bd_zum", "bd_pure",
                           "bd_ada", "bd_gas", "bd_sone", "bd_zome", "bd_jazz", "bd_chip", "drum_heavy_kick",
                           "drum_bass_hard", "elec_soft_kick", "elec_hollow_kick"]),
    ("snare", "SNARE", 0.8, ["sn_dolf", "sn_dub", "sn_zome", "sn_generic", "drum_snare_hard", "drum_snare_soft",
                             "elec_snare", "elec_hi_snare", "elec_mid_snare", "elec_lo_snare", "elec_filt_snare"]),
    ("snap", "SNAP", 0.6, ["perc_snap", "perc_snap2", "elec_pop", "elec_flip", "tbd_perc_tap_1", "tbd_perc_tap_2",
                           "elec_twip", "glitch_perc1"]),
    ("hat", "HAT", 0.35, ["hat_zild", "hat_bdu", "hat_cats", "hat_gem", "hat_noiz", "hat_psych", "hat_raw",
                          "hat_snap", "hat_star", "hat_tap", "hat_zap", "hat_gnu", "hat_yosh", "hat_len",
                          "hat_metal", "hat_cab", "hat_sci", "hat_gump", "drum_cymbal_closed", "drum_cymbal_pedal",
                          "elec_tick", "tbd_perc_hat"]),
    ("open", "HAT ABERTO", 1.4, ["drum_cymbal_open", "drum_cymbal_soft", "elec_cymbal", "drum_splash_soft",
                                 "ride_tri", "ride_via", "hat_zan", "hat_mess", "hat_hier"]),
    ("tom", "TOM", 1.0, ["drum_tom_mid_hard", "drum_tom_lo_hard", "drum_tom_hi_hard", "drum_tom_lo_soft",
                         "drum_tom_mid_soft", "drum_tom_hi_soft", "elec_fuzz_tom", "elec_bong"]),
    ("perc", "PERC", 0.8, ["drum_cowbell", "perc_bell", "perc_bell2", "elec_triangle", "elec_wood", "elec_blip",
                           "elec_blip2", "elec_ping", "elec_plip", "elec_beep", "tbd_perc_blip", "tabla_na",
                           "tabla_te1", "tabla_ke1", "tabla_ghe1", "glitch_perc2", "glitch_perc3", "glitch_perc4",
                           "glitch_perc5", "perc_till"]),
    ("fx", "FX", 2.2, ["drum_cymbal_hard", "drum_splash_hard", "perc_impact1", "perc_impact2", "misc_cineboom",
                       "vinyl_scratch", "perc_swash", "elec_chime", "bass_hit_c", "bass_voxy_hit_c", "elec_twang",
                       "drum_roll"]),
]
PREFIX = ("bd_", "sn_", "hat_", "drum_", "elec_", "perc_", "tbd_perc_", "tbd_", "glitch_", "misc_", "vinyl_",
          "tabla_", "bass_", "ride_")


NAMES = {"drum_snare_hard": "ACUST H", "drum_snare_soft": "ACUST S", "drum_cymbal_soft": "SOFT",
         "drum_cymbal_hard": "CRASH", "drum_splash_hard": "SPLASH", "drum_splash_soft": "SPLASH S",
         "elec_soft_kick": "ELEC S", "elec_hollow_kick": "HOLLOW", "drum_bass_hard": "ACUST", "drum_heavy_kick": "HEAVY",
         "tbd_perc_blip": "BLIP3", "elec_cymbal": "ELEC", "glitch_perc1": "GLITCH", "elec_snare": "ELEC",
         "elec_hi_snare": "ELEC HI", "elec_mid_snare": "ELEC MID", "elec_lo_snare": "ELEC LO",
         "elec_filt_snare": "FILTRO", "bass_hit_c": "BASS HIT", "bass_voxy_hit_c": "VOXY HIT", "tbd_perc_hat": "TBD",
         "drum_cymbal_open": "OPEN"}


def label(name):
    if name in NAMES:
        return NAMES[name]
    for p in sorted(PREFIX, key=len, reverse=True):
        if name.startswith(p):
            name = name[len(p):]
            break
    words = name.replace("_", " ").upper().split()
    if len(words) > 1:
        words = [w for w in words if w not in ("CYMBAL", "SNARE", "TOM")] or words
    words = [{"SOFT": "S", "HARD": "H"}.get(w, w) for w in words]
    return " ".join(words)[:10]


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def process(x, max_s):
    nz = np.nonzero(np.abs(x) > 0.004)[0]
    if len(nz):
        x = x[max(0, nz[0] - 16):]
    # cut the tail once it stays below -50 dB, then cap the length
    env = np.abs(x)
    above = np.nonzero(env > 0.003)[0]
    end = min(len(x), (above[-1] + 1) if len(above) else len(x), int(max_s * SR))
    x = x[:end].copy()
    fade = min(len(x), int(0.03 * SR) if end < int(max_s * SR) else int(0.25 * SR))
    if fade:
        x[-fade:] *= np.linspace(1, 0, fade) ** 2
    peak = np.max(np.abs(x)) or 1.0
    return x / peak * 0.89


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    kit, total = [], 0
    for tid, name, max_s, files in KIT:
        samples = []
        for f in files:
            src = os.path.join(SRC, f + ".flac")
            if not os.path.exists(src):
                print("missing", f)
                continue
            x = process(decode(src), max_s)
            dst = os.path.join(OUT, f + ".wav")
            write(dst, x)
            total += os.path.getsize(dst)
            samples.append({"file": f, "label": label(f)})
        kit.append({"id": tid, "name": name, "samples": samples})
    json.dump({"tracks": kit}, open(os.path.join(OUT, "kit.json"), "w"), indent=1)
    print("kit:", sum(len(t["samples"]) for t in kit), "samples, %.1f MB" % (total / 1e6))


if __name__ == "__main__":
    main()
