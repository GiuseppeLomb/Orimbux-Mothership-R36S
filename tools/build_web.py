"""ORIMBOX for phones (a web app you add to the iPhone / Android home screen): builds the site in OUTDIR from the
app's own sounds and pixel art, ready for GitHub Pages (the gh-pages branch).

    python3 tools/build_web.py OUTDIR

OUTDIR gets index.html, sw.js (offline cache), manifest.webmanifest, kit.json, a/*.wav (the 25 loops of
assets/orimbox), img/ (the aliens, the planet, the ship and the app icons) and fonts/ (Tiny5, OFL).
The page itself is web/orimbox/index.html. Needs Pillow; the art comes from orimbox.py, so pysdl2 must import
(SDL_VIDEODRIVER=dummy is set here, nothing opens)."""
import hashlib
import json
import os
import random
import shutil
import sys
import zlib

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
SRC = os.path.join(ROOT, "web", "orimbox")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)

from PIL import Image  # noqa: E402

import engine  # noqa: E402
import orimbox as OB  # noqa: E402

CATS = [None, "beat", "fx", "melody", "voice"]


def alien_sheet():
    """7 aliens x 5 looks (asleep + the 4 outfits), 18x24 art pixels each"""
    sheet = Image.new("RGBA", (18 * len(OB.DESIGNS), 24 * len(CATS)), (0, 0, 0, 0))
    for i, d in enumerate(OB.DESIGNS):
        for r, cat in enumerate(CATS):
            pal = OB.palette(OB.BODY[i], cat)
            for y, row in enumerate(OB.alien_grid(d, cat)):
                for x, ch in enumerate(row):
                    if ch != ".":
                        sheet.putpixel((i * 18 + x, r * 24 + y), tuple(pal[ch]) + (255,))
    return sheet


def frm_png(name):
    w, h, rgba, frames = engine.load_frm(os.path.join(engine.ASSETS, "art", name + ".frm"))
    idx = zlib.decompress(frames[0])
    im = Image.new("RGBA", (w, h))
    im.putdata([(0, 0, 0, 0) if c == 0 else tuple(rgba[c * 4:c * 4 + 3]) + (255,) for c in idx])
    return im


def icon(sheet, size, fill):
    """the app icon: the stage sky, a few stars, the floor and one alien with headphones, in whole pixels"""
    bands = [(16, 8, 44), (22, 10, 58), (30, 12, 70), (40, 14, 80), (52, 18, 88)]
    im = Image.new("RGBA", (size, size), bands[0] + (255,))
    floor = int(size * 0.80)
    for k, col in enumerate(bands):
        im.paste(col + (255,), (0, k * floor // 5, size, (k + 1) * floor // 5 + 1))
    im.paste((34, 18, 64, 255), (0, floor, size, size))
    im.paste((255, 110, 170, 255), (0, floor, size, floor + max(2, size // 64)))
    rnd = random.Random(5)
    st = max(1, size // 96)
    for _ in range(18):
        x, y = rnd.randrange(size), rnd.randrange(int(floor * 0.85))
        im.paste((220, 220, 255, 255), (x, y, x + st, y + st))
    cell = sheet.crop((0, 24, 18, 48))                     # alien 1 with headphones (BATIDAS)
    sc = max(1, int(size * fill / 24))
    a = cell.resize((18 * sc, 24 * sc), Image.NEAREST)
    x0 = (size - a.width) // 2
    y0 = floor - a.height + 2 * sc
    im.alpha_composite(a, (x0, y0))
    return im.convert("RGB")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    for sub in ("a", "img", "fonts"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    version = None
    with open(os.path.join(APPD, "credits.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION = "):
                version = line.split('"')[1]
    # the kit: names, groups, the loudness envelopes that move the mouths, the secrets
    kit = engine.read_json(os.path.join(OB.D, "kit.json"))
    slim = {"bpm": kit["bpm"], "frames": kit["frames"], "env_fps": kit["env_fps"],
            "sounds": [{"id": s["id"], "name": s["name"], "cat": s["cat"], "env": s["env"]} for s in kit["sounds"]],
            "bonus": [{"id": b["id"], "name": b["name"], "needs": b["needs"]} for b in kit["bonus"]]}
    engine.write_json(os.path.join(out, "kit.json"), slim, separators=(",", ":"), ensure_ascii=False)
    for s in kit["sounds"] + kit["bonus"]:
        shutil.copyfile(os.path.join(OB.D, s["id"] + ".wav"), os.path.join(out, "a", s["id"] + ".wav"))
    # pixel art + icons
    sheet = alien_sheet()
    sheet.save(os.path.join(out, "img", "aliens.png"), optimize=True)
    for name in ("ringed", "ship"):
        frm_png(name).save(os.path.join(out, "img", name + ".png"), optimize=True)
    for size, fill, name in ((180, 0.62, "icon-180"), (192, 0.62, "icon-192"), (512, 0.62, "icon-512"),
                             (512, 0.44, "icon-maskable-512"), (32, 0.7, "icon-32")):
        icon(sheet, size, fill).save(os.path.join(out, "img", name + ".png"), optimize=True)
    for f in os.listdir(os.path.join(SRC, "fonts")):
        shutil.copyfile(os.path.join(SRC, "fonts", f), os.path.join(out, "fonts", f))
    shutil.copyfile(os.path.join(SRC, "manifest.webmanifest"), os.path.join(out, "manifest.webmanifest"))
    with open(os.path.join(SRC, "index.html"), encoding="utf-8") as f:
        page = f.read().replace("__VERSION__", version or "")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    open(os.path.join(out, ".nojekyll"), "w").close()
    # the offline cache: every file, and a version that changes whenever any of them does
    files = ["./"]
    h = hashlib.sha1()
    for dp, _, fs in sorted(os.walk(out)):
        if ".git" in dp.split(os.sep):
            continue
        for fn in sorted(fs):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, out).replace(os.sep, "/")
            if rel in ("sw.js", ".nojekyll", "CNAME") or rel.startswith("."):
                continue
            files.append(rel)
            with open(p, "rb") as f:
                h.update(rel.encode() + f.read())
    with open(os.path.join(SRC, "sw.js"), encoding="utf-8") as f:
        sw = f.read()
    sw = sw.replace("__VERSION__", "%s-%s" % (version, h.hexdigest()[:10])).replace("__FILES__", json.dumps(files))
    with open(os.path.join(out, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw)
    # every file the page asks for is there
    for ref in ["kit.json", "manifest.webmanifest", "sw.js", "img/aliens.png", "img/ringed.png", "img/ship.png",
                "img/icon-180.png", "img/icon-32.png", "fonts/Tiny5-Regular.woff2", "fonts/Tiny5-Bold.woff2"]:
        assert os.path.exists(os.path.join(out, ref)), ref
    assert "__" not in page.split("<script>")[0], "placeholder left in the page"
    size = sum(os.path.getsize(os.path.join(out, f)) for f in files if f != "./")
    print("ORIMBOX web %s: %d files, %.1f MB -> %s" % (version, len(files) - 1, size / 1e6, out))


if __name__ == "__main__":
    main()
