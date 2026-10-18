# headless test for VOX NEBULA with a fake mic (a wav played in real time). Snapshots to argv[1].
import ctypes, os, sys, time as _time
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib")); sys.path.insert(0, APPD)
os.environ["VOX_FAKE"] = os.path.join(APPD, "assets", "bd", "moon_hop.wav")
import sdl2
from PIL import Image
import engine, app as appmod, vox as vm
from engine import audioop
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
while not a.bank.ready: _time.sleep(0.05)


def snap(name, frames=2):
    for _ in range(frames):
        a.frame(1 / 30.0); _time.sleep(1 / 30.0)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


try:
    a.go("vox"); vx = a.cur
    snap("v0_off", 3)
    vx.on("press", "r2"); assert vx.live        # R2 = mic on/off (START is "next app")
    snap("v1_live", 40)                      # ~1.3 s of real time: the fake mic fills
    print("buffered frames:", vx.mic.buffered(), "level %.2f" % vx.level)
    assert vx.level > 0.02
    x = audioop.mul(vx.mic.take(1024), 2, 1.0)
    if audioop.rms(x, 2) < 200:
        x = audioop.mul(engine.load_wav(os.environ["VOX_FAKE"])[400000:400000 + 4096], 2, 1)[:2048]
    for name, key in vm.EFFECTS:
        vx.on("press", key); assert vx.fx == name
        t0 = _time.perf_counter()
        for _ in range(50):
            y = vx.process(x)
        ms = (_time.perf_counter() - t0) / 50 * 1000
        print("%-10s out %d bytes  rms in %5d out %5d  %.3f ms/block" % (name, len(y), audioop.rms(x, 2),
                                                                         audioop.rms(y, 2), ms))
        assert len(y) == len(x)
    vx.on("press", "x"); vx.on("press", "l2"); assert vx.echo
    snap("v2_cave_echo", 10)
    s = vx.stream.read(1024)
    assert s is not None and len(s) == 4096
    a.go("bridge"); assert vx.live                 # keeps singing over other sections
    a.go("voidrunner"); assert not vx.live         # games silence the mic
    print("ok")
finally:
    try: a.sections["vox"].stop()
    except Exception: pass
    for f in ("config.json", "pet.json", "forge.json", "earlab.json"):
        try: os.remove(os.path.join(APPD, f))
        except OSError: pass
