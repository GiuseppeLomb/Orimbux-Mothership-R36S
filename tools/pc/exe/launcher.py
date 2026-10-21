"""Orimbux Mothership.exe - the Windows build without Python: this script, frozen by tools/package_pc.py together with
Python, SDL2.dll and audioop, runs mothership/main.py from the folder next to the .exe. The app's own files stay
plain .py there (the same code as the console), and the player's files (saves, music, recordings) live in that
folder, as they always did."""
import os
import runpy
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
APPD = os.path.join(BASE, "mothership")
MAIN = os.path.join(APPD, "main.py")
LOG = os.path.join(APPD, "log.txt")
TITLE = "Orimbux Mothership"


def message(text, error=True):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, TITLE, 0x10 if error else 0x40)
    except Exception:
        pass


def writable(d):
    probe = os.path.join(d, ".write-test.tmp")
    try:
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def setup():
    # a windowed .exe has no console: print() and warnings go nowhere instead of failing
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    # SDL2.dll travels inside the .exe's folder (_internal)
    dlls = getattr(sys, "_MEIPASS", BASE)
    os.environ["PYSDL2_DLL_PATH"] = dlls
    # an ffmpeg.exe the player drops next to the .exe (or in an "ffmpeg" folder) decodes .mp3/.ogg/game music
    extra = [BASE, os.path.join(BASE, "ffmpeg"), os.path.join(BASE, "ffmpeg", "bin")]
    os.environ["PATH"] = os.pathsep.join(extra + [os.environ.get("PATH", "")])
    # ffmpeg is a console program: started from a window it would flash a black console on every song
    if os.name == "nt":
        class Quiet(subprocess.Popen):
            def __init__(self, *a, **kw):
                kw.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
                super().__init__(*a, **kw)
        subprocess.Popen = Quiet
    os.chdir(BASE)


def main():
    if not os.path.isfile(MAIN):
        message("Não encontrei a pasta \"mothership\" ao lado do Orimbux Mothership.exe.\n\n"
                "Descomprime o zip inteiro (botão direito > Extrair tudo) e abre o .exe dessa pasta.")
        return 1
    if not writable(APPD):
        message("Não consigo escrever na pasta da nave:\n%s\n\n"
                "Move a pasta Orimbux Mothership para os Documentos ou o Ambiente de trabalho "
                "(não para Programas) e abre outra vez." % APPD)
        return 1
    setup()
    sys.argv[0] = MAIN
    try:
        runpy.run_path(MAIN, run_name="__main__")
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException:
        import traceback
        with open(LOG, "a", encoding="utf-8", errors="replace") as f:
            traceback.print_exc(file=f)
        code = 1
    else:
        code = 0
    if code:
        message("A nave fechou com um erro.\n\nVê o ficheiro mothership\\log.txt (tem a descrição do erro).")
    return code


if __name__ == "__main__":
    sys.exit(main())
