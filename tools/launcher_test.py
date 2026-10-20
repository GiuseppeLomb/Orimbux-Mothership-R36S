"""The console launcher installs mothership*.zip packages: only what is inside mothership/, never the player's
files, never outside the ports folder; a real package installs exactly what plain extraction would.
Also runs the whole launcher in bash (when there is one), with a stand-in python3 that does not start the app.
  python3 tools/launcher_test.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "ports", "Orimbux Mothership.sh")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import package  # noqa: E402

src = open(SH, encoding="utf-8").read().replace("\r\n", "\n")
UNZIP = src.split("UNZIP='", 1)[1].split("\n'\n", 1)[0]
TMP = tempfile.mkdtemp()


def tree(d):
    out = set()
    for root, _, files in os.walk(d):
        for f in files:
            out.add(os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/"))
    return out


def install(zpath, ports):
    subprocess.check_call([sys.executable, "-c", UNZIP, zpath, ports])


try:
    # ---- the launcher protects the same files the packager leaves out
    ns = {}
    exec(UNZIP.split("z = zipfile")[0], ns)
    assert package.USER_FILES <= ns["SAVES"] and package.USER_DIRS == ns["PLAYER_DIRS"]
    # ---- the packaged launcher is plain bash (LF), even when packed from a Windows checkout with CRLF files
    sh = package.launcher()
    assert b"\r" not in sh and sh.startswith(b"#!/bin/bash\n") and sh.decode("utf-8") == src

    # ---- a hostile or hand-made zip
    ports = os.path.join(TMP, "case1", "ports")
    os.makedirs(os.path.join(ports, "mothership", "recordings"))
    for f, data in (("pet.json", "MY PET"), ("config.json", "MY CONFIG"), ("recordings/rec_1.wav", "MY REC")):
        open(os.path.join(ports, "mothership", f), "w").write(data)
    bad = os.path.join(TMP, "mothership_1.zip")
    with zipfile.ZipFile(bad, "w") as z:
        for name in ("../evil.txt", "/abs.txt", "mothership/../../evil2.txt", "C:/win.txt", "other/x.txt",
                     "mothership/pet.json", "mothership/config.json", "mothership/forge.json.tmp",
                     "mothership/pet.json.bad-20260101-000000", "mothership/recordings/rec_1.wav",
                     "mothership/music/song.mp3", "mothership/recordings/LEIA-ME.txt", "mothership/app.py",
                     "mothership/assets/forge/kick.wav", "mothership/LEIA-ME.txt"):
            z.writestr(name, "FROM ZIP")
    install(bad, ports)
    got = tree(os.path.join(TMP, "case1"))
    assert got == {"ports/mothership/pet.json", "ports/mothership/config.json", "ports/mothership/recordings/rec_1.wav",
                   "ports/mothership/recordings/LEIA-ME.txt", "ports/mothership/app.py",
                   "ports/mothership/assets/forge/kick.wav", "ports/mothership/LEIA-ME.txt"}, sorted(got)
    for f, data in (("pet.json", "MY PET"), ("config.json", "MY CONFIG"), ("recordings/rec_1.wav", "MY REC")):
        assert open(os.path.join(ports, "mothership", f)).read() == data, f
    print("a hand-made zip cannot touch the saves, recordings or anything outside mothership/")

    # ---- a real package (the files package.py ships) installs exactly as plain extraction would
    real = os.path.join(TMP, "mothership_2.zip")
    with zipfile.ZipFile(real, "w", zipfile.ZIP_STORED) as z:
        z.write(os.path.join(ROOT, "LEIA-ME.txt"), "mothership/LEIA-ME.txt")
        for p, arc in package.files():
            z.write(p, arc.replace(os.sep, "/"))
    a, b = os.path.join(TMP, "plain"), os.path.join(TMP, "launcher")
    zipfile.ZipFile(real).extractall(a)
    install(real, b)
    assert tree(a) == tree(b) and len(tree(b)) > 400, (len(tree(a)), len(tree(b)))
    print("a real package installs the same %d files as before" % len(tree(b)))

    # ---- the whole launcher, in bash
    bash = shutil.which("bash")
    if not bash:
        print("no bash here: the launcher itself was not run")
    else:
        pd = os.path.join(TMP, "card", "ports")
        os.makedirs(os.path.join(pd, "mothership"))
        open(os.path.join(pd, "mothership", "pet.json"), "w").write("MY PET")
        open(os.path.join(pd, "Orimbux Mothership.sh"), "w", newline="\n").write(src)
        shutil.copy(bad, os.path.join(pd, "mothership_1.zip"))
        bindir = os.path.join(TMP, "bin")
        os.makedirs(bindir)
        py = sys.executable.replace("\\", "/")
        open(os.path.join(bindir, "python3"), "w", newline="\n").write(
            '#!/bin/bash\nif [ "$1" = "main.py" ]; then echo "app started"; exit 0; fi\nexec "%s" "$@"\n' % py)
        os.chmod(os.path.join(bindir, "python3"), 0o755)
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
        if os.name == "nt":                          # Git Bash: its own PATH syntax for the stand-in python3
            drive, rest = os.path.splitdrive(bindir)
            env["PATH"] = "/%s%s:%s" % (drive[0].lower(), rest.replace("\\", "/"), "/usr/bin:/bin")
        r = subprocess.run([bash, "Orimbux Mothership.sh"], cwd=pd, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        log = open(os.path.join(pd, "mothership", "log.txt")).read()
        # (the exit code is not checked: off the console there is no /dev/tty0 to clear, and that fails)
        assert "app started" in log and "Falhou" not in r.stdout.decode(errors="replace"), (r.stdout, log)
        assert not os.path.exists(os.path.join(pd, "mothership_1.zip")), "the package should be removed"
        assert open(os.path.join(pd, "mothership", "pet.json")).read() == "MY PET"
        assert os.path.exists(os.path.join(pd, "mothership", "app.py"))
        assert not os.path.exists(os.path.join(TMP, "card", "evil.txt"))
        assert not os.path.exists(os.path.join(pd, "evil.txt")) and not os.path.exists(os.path.join(pd, "other"))
        print("the launcher installs, removes the package, keeps the saves and starts the app")
    print("ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)
