# BEAT FORGE construtor: ready-made beats by style. Each track has a few variations (16 steps).
# Step codes: . off | o soft | x normal | X accent | 2/3/4 normal with a 2/3/4-hit ratchet | ? normal at 50%
# Order of tracks: kick snare snap hat open tom perc fx (kit.json ids).

STYLES = [
    {"name": "TRAP", "bpm": 140, "swing": 50,
     "sounds": {"kick": "bd_808", "snare": "elec_snare", "snap": "perc_snap", "hat": "hat_tap", "open": "hat_zan",
                "tom": "elec_bong", "perc": "elec_plip", "fx": "perc_impact1"},
     "vars": {"kick": ["x......x..x.....", "x.....x...x..x..", "x..x......x.....", "x......x.x...x.."],
              "snare": ["........X.......", "........X......o", "........X...o..."],
              "snap": ["........x.......", "................", "........x.....x."],
              "hat": ["x.x.x.x.x.x.x.x.", "x.x.x.x.x.x.x3x2", "xxxxx.x.xxxx3.x.", "x.x.x.x.x.4.x.x."],
              "open": ["................", "..............o.", "......o.......o."],
              "tom": ["................", "............o.o."],
              "perc": ["................", "...o.......o....", "......?........."],
              "fx": ["................", "X..............."]}},
    {"name": "BOOM BAP", "bpm": 90, "swing": 58,
     "sounds": {"kick": "bd_klub", "snare": "sn_dolf", "snap": "perc_snap2", "hat": "hat_zild",
                "open": "drum_cymbal_soft", "tom": "drum_tom_lo_soft", "perc": "elec_wood", "fx": "vinyl_scratch"},
     "vars": {"kick": ["x.......x.x.....", "x......x..x.....", "x.x.......x..x..", "x.......x...x.o."],
              "snare": ["....X.......X...", "....X.......X..o", "....X..o....X..."],
              "snap": ["................", "....x.......x..."],
              "hat": ["x.x.x.x.x.x.x.x.", "xox.xox.xox.xox.", "x.x.x.xox.x.x.xo"],
              "open": ["................", "..............o."],
              "tom": ["................"],
              "perc": ["................", "......o.......o."],
              "fx": ["................", "X..............."]}},
    {"name": "HOUSE", "bpm": 124, "swing": 54,
     "sounds": {"kick": "bd_haus", "snare": "sn_generic", "snap": "perc_snap", "hat": "drum_cymbal_closed",
                "open": "drum_cymbal_open", "tom": "drum_tom_mid_soft", "perc": "drum_cowbell",
                "fx": "drum_cymbal_hard"},
     "vars": {"kick": ["x...x...x...x...", "x...x...x...x..o"],
              "snare": ["................", "....o.......o..."],
              "snap": ["....x.......x...", "....x.......x..o", "....x..o....x..."],
              "hat": ["oooooooooooooooo", "..x...x...x...x.", "o.x.o.x.o.x.o.x."],
              "open": ["..x...x...x...x.", "................", "..o...o...o...x."],
              "tom": ["................", "...........o..o."],
              "perc": ["................", "...o..o....o..o.", "o..o..o.o..o..o."],
              "fx": ["................", "X..............."]}},
    {"name": "TECHNO", "bpm": 130, "swing": 50,
     "sounds": {"kick": "bd_tek", "snare": "elec_lo_snare", "snap": "elec_pop", "hat": "hat_metal",
                "open": "ride_tri", "tom": "elec_fuzz_tom", "perc": "elec_blip", "fx": "perc_swash"},
     "vars": {"kick": ["X...x...x...x...", "x...x...x...x.o."],
              "snare": ["................", "............o..."],
              "snap": ["....x.......x...", "................", "............x..."],
              "hat": ["..x...x...x...x.", "oxoxoxoxoxoxoxox", "..x.o.x...x.o.x."],
              "open": ["................", "..o...o...o...o."],
              "tom": ["................", "......o.......o."],
              "perc": ["................", "x..x..x..x..x..x", "o.o..o.o..o.o..."],
              "fx": ["................", "X..............."]}},
    {"name": "DRUM & BASS", "bpm": 174, "swing": 50,
     "sounds": {"kick": "bd_fat", "snare": "sn_zome", "snap": "elec_flip", "hat": "hat_raw",
                "open": "drum_splash_soft", "tom": "drum_tom_hi_soft", "perc": "elec_ping", "fx": "drum_cymbal_hard"},
     "vars": {"kick": ["x.........x.....", "x.........x..o..", "x.x.......x....."],
              "snare": ["....X.......X...", "....X.......X..o", "....X..o....X..."],
              "snap": ["................", "....x.......x..."],
              "hat": ["x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx", "x.xox.xox.xox.xo"],
              "open": ["................", "......o.......o."],
              "tom": ["................"],
              "perc": ["................", "..o.......o....."],
              "fx": ["X...............", "................"]}},
    {"name": "REGGAETON", "bpm": 94, "swing": 50,
     "sounds": {"kick": "bd_boom", "snare": "elec_mid_snare", "snap": "perc_snap", "hat": "hat_tap",
                "open": "hat_hier", "tom": "drum_tom_mid_hard", "perc": "elec_wood", "fx": "misc_cineboom"},
     "vars": {"kick": ["x...x...x...x...", "x...x...x...x..o"],
              "snare": ["...x..x....x..x.", "...x..x....x..xo"],
              "snap": ["...x..x....x..x.", "................"],
              "hat": ["x.x.x.x.x.x.x.x.", "................", "xoxoxoxoxoxoxoxo"],
              "open": ["................", "..............o."],
              "tom": ["................", "......o.......o."],
              "perc": ["................", "x..o..x.x..o..x."],
              "fx": ["................", "X..............."]}},
    {"name": "AFRO HOUSE", "bpm": 122, "swing": 54,
     "sounds": {"kick": "bd_pure", "snare": "elec_hi_snare", "snap": "perc_snap2", "hat": "hat_cab",
                "open": "hat_zan", "tom": "elec_bong", "perc": "tabla_na", "fx": "perc_swash"},
     "vars": {"kick": ["x...x...x...x...", "x...x...x...x.o."],
              "snare": ["................", ".......o.......o"],
              "snap": ["....x.......x...", "......x.......x."],
              "hat": ["oxoxoxoxoxoxoxox", "o.x.o.x.o.x.o.x."],
              "open": ["..o...o...o...o.", "................"],
              "tom": ["...x..x.....x...", "..o..x...o..x...", "................"],
              "perc": ["x..x..x...x..x..", "x..x..x.x..x..x.", "o.o..o.o.o..o.o."],
              "fx": ["................", "X..............."]}},
    {"name": "LO-FI", "bpm": 80, "swing": 62,
     "sounds": {"kick": "bd_jazz", "snare": "drum_snare_soft", "snap": "tbd_perc_tap_1", "hat": "hat_gem",
                "open": "drum_cymbal_soft", "tom": "drum_tom_lo_soft", "perc": "perc_bell", "fx": "vinyl_scratch"},
     "vars": {"kick": ["x......x..x.....", "x.......x.......", "x.....x...x...o."],
              "snare": ["....x.......x...", "....x.......x..o"],
              "snap": ["................", "....o.......o..."],
              "hat": ["o.o.o.o.o.o.o.o.", "o.oxo.o.o.oxo.o.", "................"],
              "open": ["................", "..............o."],
              "tom": ["................"],
              "perc": ["................", "......o.......o."],
              "fx": ["................"]}},
    {"name": "ROCK", "bpm": 120, "swing": 50,
     "sounds": {"kick": "drum_heavy_kick", "snare": "drum_snare_hard", "snap": "perc_snap",
                "hat": "drum_cymbal_closed", "open": "drum_cymbal_open", "tom": "drum_tom_mid_hard",
                "perc": "drum_cowbell", "fx": "drum_splash_hard"},
     "vars": {"kick": ["x.......x.x.....", "x.x.....x.x.....", "x...x...x...x..."],
              "snare": ["....X.......X...", "....X.......X.oo"],
              "snap": ["................"],
              "hat": ["x.x.x.x.x.x.x.x.", "xxxxxxxxxxxxxxxx"],
              "open": ["................", "..............x."],
              "tom": ["................", "............xxoo"],
              "perc": ["................"],
              "fx": ["X...............", "................"]}},
]


def decode(code):
    """'x..X3?' -> [[vel, ratchet, chance], ...]"""
    out = []
    for ch in code:
        if ch == ".":
            out.append([0, 1, 100])
        elif ch == "o":
            out.append([1, 1, 100])
        elif ch == "x":
            out.append([2, 1, 100])
        elif ch == "X":
            out.append([3, 1, 100])
        elif ch in "234":
            out.append([2, int(ch), 100])
        elif ch == "?":
            out.append([2, 1, 50])
        else:
            out.append([0, 1, 100])
    return out
