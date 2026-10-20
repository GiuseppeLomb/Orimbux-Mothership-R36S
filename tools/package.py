"""Release packaging.
  python3 tools/package.py VERSION OUTDIR
-> OUTDIR/OrimbuxMothership_VERSION.zip   (LEIA-ME + ports/..., the whole thing, for archive / manual install)
-> OUTDIR/card/Orimbux Mothership.sh + mothership_1.zip ... (each < 15 MB: the launcher installs them itself)"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTS = os.path.join(ROOT, "ports")
APPD = os.path.join(PORTS, "mothership")
USER_FILES = {"config.json", "pet.json", "vr_save.json", "bd_save.json", "bd_scores.json", "forge.json",
              "earlab.json", "quiz.json", "missions.json", "log.txt"}       # the launcher never unpacks these either
USER_DIRS = {"recordings", "music", "samples", "forge", "chop", "vr_cache"}      # only their LEIA-ME ships
PART = 15 * 1024 * 1024


def files():
    out = []
    for root, dirs, fs in os.walk(APPD):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
        rel = os.path.relpath(root, APPD)
        top = rel.split(os.sep)[0]
        for f in sorted(fs):
            if f.endswith((".pyc", ".pyo")) or f.startswith("."):
                continue
            if rel == "." and (f in USER_FILES or f.endswith(".tmp") or ".bad-" in f):   # + leftovers of a save
                continue
            if top in USER_DIRS and f != "LEIA-ME.txt":
                continue
            p = os.path.join(root, f)
            out.append((p, os.path.relpath(p, PORTS)))       # mothership/...
    return out


def main():
    ver, outd = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(outd, "card"), exist_ok=True)
    fl = files()
    launcher = os.path.join(PORTS, "Orimbux Mothership.sh")
    leia = os.path.join(ROOT, "LEIA-ME.txt")
    full = os.path.join(outd, "OrimbuxMothership_%s.zip" % ver)
    with zipfile.ZipFile(full, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(leia, "LEIA-ME.txt")
        info = zipfile.ZipInfo("ports/Orimbux Mothership.sh")
        info.external_attr = 0o100755 << 16
        z.writestr(info, open(launcher, "rb").read(), zipfile.ZIP_DEFLATED)
        for p, arc in fl:
            z.write(p, "ports/" + arc)
    # card parts: greedy fill by size, the LEIA-ME goes in part 1
    parts, cur, size = [], [(leia, "mothership/LEIA-ME.txt")], 0
    for p, arc in fl:
        s = os.path.getsize(p)
        if cur and size + s > PART:
            parts.append(cur)
            cur, size = [], 0
        cur.append((p, arc))
        size += s
    parts.append(cur)
    card = os.path.join(outd, "card")
    for f in os.listdir(card):
        if f.startswith("mothership") and f.endswith(".zip"):
            os.remove(os.path.join(card, f))
    for i, part in enumerate(parts):
        zp = os.path.join(card, "mothership_%d.zip" % (i + 1))
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p, arc in part:
                z.write(p, arc)
    data = open(launcher, "rb").read()
    open(os.path.join(card, "Orimbux Mothership.sh"), "wb").write(data)
    os.chmod(os.path.join(card, "Orimbux Mothership.sh"), 0o755)
    print("full:", full, "%.1f MB, %d files" % (os.path.getsize(full) / 1e6, len(fl)))
    for f in sorted(os.listdir(card)):
        print("  card/%s  %.1f MB" % (f, os.path.getsize(os.path.join(card, f)) / 1e6))


if __name__ == "__main__":
    main()
