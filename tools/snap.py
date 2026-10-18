"""Headless test: boots the app with SDL's dummy drivers, drives it with fake button presses,
saves screenshots of every section and renders a few seconds of audio to WAV."""
import ctypes, os, sys, time, wave
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
import sdl2
from PIL import Image
import app as appmod
import engine

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snaps"
os.makedirs(OUT, exist_ok=True)

a = appmod.App(headless=True)
t0 = time.time()
while not a.bank.ready and time.time() - t0 < 60:
    time.sleep(0.05)
print("bank ready in %.1fs errors=%s" % (time.time() - t0, a.bank.errors))


def snap(name, frames=3, dt=1 / 30.0):
    for _ in range(frames):
        a.frame(dt)
    buf = ctypes.create_string_buffer(640 * 480 * 4)
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_ABGR8888, buf, 640 * 4)
    Image.frombuffer("RGBA", (640, 480), buf.raw, "raw", "RGBA", 0, 1).convert("RGB").save(
        os.path.join(OUT, name + ".png"))
    sdl2.SDL_RenderPresent(a.ren)


def press(b, release=True):
    a.cur.on("press", b)
    if release:
        a.cur.on("release", b)


def render_audio(seconds):
    frames = []
    for _ in range(int(seconds * 44100 / engine.BUF)):
        frames.append(a.mixer.render(engine.BUF))
    return b"".join(frames)


audio = []
a.go("intro")
snap("0_intro", 20)
a.go("bridge")
snap("1_bridge", 30)
a.go("reactor")
press("up")       # AMEN loop (queued)
press("left")     # KICK shot
snap("2a_reactor_queued", 2)
audio.append(render_audio(1.5))
press("x")        # BREAK
audio.append(render_audio(3.0))
snap("2b_reactor_playing", 2)
a.cur.on("press", "r2")
audio.append(render_audio(2.0))
a.cur.on("release", "r2")
press("r1")
press("a")
snap("2c_reactor_bank2", 2)
audio.append(render_audio(2.0))
a.set_bpm(160)
audio.append(render_audio(2.0))
press("l2")
a.go("xeno")
a.cur.on("press", "left")
a.cur.on("press", "down")
a.input.axes["lx"] = 0.5
a.cur.update(0.03)
audio.append(render_audio(1.0))
snap("3_xeno", 2)
a.cur.on("release", "left")
a.cur.on("release", "down")
audio.append(render_audio(0.6))
a.go("pulsar")
a.mixer.metro = True
audio.append(render_audio(2.0))
snap("4_pulsar", 2)
a.mixer.metro = False
a.go("abductor")
snap("5_abductor", 2)
a.go("warp")
snap("6_warp", 2)
a.go("hangar")
snap("7_hangar", 2)

pcm = b"".join(audio)
w = wave.open(os.path.join(OUT, "audio_test.wav"), "wb")
w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100); w.writeframes(pcm); w.close()
print("ok", OUT)
