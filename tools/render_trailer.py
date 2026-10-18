"""Records the TRAILER or CREDITOS section to an MP4 (1280x960, 30 fps) with its soundtrack.
  python3 tools/render_trailer.py trailer|credits OUT.mp4 [--frames t1,t2,...  (PNG stills instead)] [--noscan]"""
import ctypes, os, subprocess, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
import sdl2
import app as appmod

name, out = sys.argv[1], sys.argv[2]
stills = None
if "--frames" in sys.argv:
    stills = [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]
a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
a.cfg["scanlines"] = "--noscan" not in sys.argv
sec = a.sections[name]
sec.force_t = 0.0
a.go(name)
FPS = 30
if name == "trailer":
    import trailer
    total = trailer.END
    audio = os.path.join(ROOT, "tools", "build", "trailer_44k.wav")
else:
    import credits
    total = 96.0
    audio = os.path.join(ROOT, "tools", "build", "credits_44k.wav")
buf = ctypes.create_string_buffer(640 * 480 * 4)


def render_at(t):
    sec.force_t = t
    sec.update(1.0 / FPS)
    a.cur = sec
    sec.draw(a.g, t, 1.0 / FPS)
    if a.cfg["scanlines"]:
        a.g.scanlines()
    sdl2.SDL_RenderReadPixels(a.ren, None, sdl2.SDL_PIXELFORMAT_RGB888, buf, 640 * 4)
    raw = buf.raw
    sdl2.SDL_RenderPresent(a.ren)
    return raw


if stills:
    from PIL import Image
    os.makedirs(out, exist_ok=True)
    t, i = 0.0, 0
    for target in sorted(stills):
        while t < target:                       # step through time so stateful scenes stay correct
            sec.force_t = t
            sec.update(1.0 / FPS)
            t += 1.0 / FPS
        raw = render_at(target)
        Image.frombuffer("RGBX", (640, 480), raw, "raw", "BGRX", 0, 1).convert("RGB").save(
            os.path.join(out, "%s_%06.2f.png" % (name, target)))
    sys.exit(0)

ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "640x480",
                       "-r", str(FPS), "-i", "-", "-i", audio, "-vf", "scale=1280:960:flags=neighbor",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                      stdin=subprocess.PIPE)
n = int(total * FPS)
for i in range(n):
    t = i / float(FPS)
    if name == "credits" and sec.done_t is not None and t - sec.done_t > 5.9:
        break
    ff.stdin.write(render_at(t))
ff.stdin.close()
ff.wait()
print("wrote", out, "%.1f s" % (i / float(FPS)))
