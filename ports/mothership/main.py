#!/usr/bin/env python3
# Orimbux Mothership - entry point
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, HERE)

# let pysdl2 use the console's own libSDL2 (the one built for its screen)
if "PYSDL2_DLL_PATH" not in os.environ:
    for d in ("/usr/lib/aarch64-linux-gnu", "/usr/lib", "/usr/local/lib", "/usr/lib/arm-linux-gnueabihf"):
        if os.path.exists(os.path.join(d, "libSDL2-2.0.so.0")) or os.path.exists(os.path.join(d, "libSDL2.so")):
            os.environ["PYSDL2_DLL_PATH"] = d
            break
os.environ.setdefault("PYSDL2_DLL_PATH", "")
if not os.environ["PYSDL2_DLL_PATH"]:
    del os.environ["PYSDL2_DLL_PATH"]


def main():
    sys.setswitchinterval(0.001)  # keep the audio thread snappy
    import app
    a = app.App(headless="--headless" in sys.argv)
    a.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import io
        with io.open(os.path.join(HERE, "log.txt"), "a", encoding="utf-8", errors="replace") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        sys.exit(1)
