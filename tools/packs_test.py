"""LOOP REACTOR v1.10 sample packs: the 7 genre banks (CC0 sounds from VCSL and Sonic Pi) load complete, with their
dark copies, after the 4 old banks (so the Abductor's pad 3:7 is still SIGNAL's B) and before FORGE and CHOP.
  python3 tools/packs_test.py [APPDIR]"""
import audioop
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import app as appmod  # noqa: E402
import engine  # noqa: E402
import help as helpmod  # noqa: E402

OLD = ["CORE", "GRAVITY", "NEBULA", "SIGNAL"]
NEW = ["HIP HOP", "TECHNO", "LATINO", "MUNDO", "ÉPICO", "LO-FI", "ROCK"]

try:
    a = appmod.App(headless=True)
    while not a.bank.ready:
        time.sleep(0.02)
    bank = a.bank
    assert bank.errors == [], bank.errors
    names = [b["name"] for b in bank.banks]
    assert names == OLD + NEW + ["FORGE", "CHOP"], names
    assert (bank.forge_bank, bank.chop_bank) == (11, 12)
    assert bank.pad(3, 7)["file"] == "elec_ping"                    # the Abductor's "3:7" is still SIGNAL, pad B
    assert "há %d" % len(bank.banks) in helpmod.HELP["reactor"][2][2]
    credits = open(os.path.join(engine.ASSETS, "samples", "CREDITS-packs.md"), encoding="utf-8").read()
    for bi in range(len(OLD), len(OLD) + len(NEW)):
        b = bank.banks[bi]
        assert len(b["pads"]) == 8 and b.get("color") in appmod.BANK_COL, b["name"]
        for pi, pad in enumerate(b["pads"]):
            path = bank.path_for(pad)
            assert os.path.exists(path) and os.path.exists(path[:-4] + ".dark.wav"), path
            assert "`%s`" % pad["file"] in credits, pad["file"]           # every sound says where it comes from
            data, dark = bank.raw[(bi, pi)]
            assert dark is not None and len(dark) == len(data), pad["file"]
            assert audioop.max(data, 2) > 0.3 * 32768, pad["file"]       # loud enough, never silence
            assert len(data) <= 8.1 * 44100 * 4, pad["file"]              # short: the whole bank stays light
            assert a.g.tw("p8", pad["label"]) <= 60, pad["label"]         # the name fits on its pad
            if pad["mode"] == "loop":
                fd, fk = bank.get(bi, pi, 120.0)
                assert len(fd) == len(fk) == int(round(pad["beats"] * 44100 * 60 / 120.0)) * 4, pad["file"]
            else:
                assert pad["mode"] == "shot", pad
    # a genre pad plays through the mixer like any other
    a.go("reactor")
    rx = a.cur
    rx.bank = NEW.index("LATINO") + len(OLD)
    rx.trigger(0)
    assert any(v.group == "reactor" for v in a.mixer.voices)
    a.mixer.render(1470)
    a.mixer.kill_group("reactor")
    print("ok: %d banks, %d new sounds" % (len(bank.banks), 8 * len(NEW)))
finally:
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACK:
            open(p, "wb").write(BACK[f])
