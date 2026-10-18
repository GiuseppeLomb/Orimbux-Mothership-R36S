"""Finds text drawn past the screen edges in the TRAILER and CREDITOS (every 0.1 s of both)."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
import sdl2
import app as appmod
import credits, trailer
from engine import W, H

a = appmod.App(headless=True)
a.cfg["seen"] = list(__import__("help").HELP)
g = a.g
orig = g.text
bad = {}
cur = [0.0, ""]


def text(fname, s, x, y, col, al=255, align="left"):
    end = orig(fname, s, x, y, col, al, align)
    if sdl2.SDL_GetRenderTarget(a.ren) or al < 40 or not str(s).strip():
        return end
    w = g.tw(fname, s)
    x0 = end - w
    if x0 < 2 or end > W - 2 or y < 0 or y + g.th(fname) > H + 4:
        key = (cur[1], fname, str(s))
        if key not in bad:
            bad[key] = (cur[0], x0, end, y)
    return end


g.text = text
for name, total in (("trailer", trailer.END), ("credits", 96.0)):
    sec = a.sections[name]
    sec.force_t = 0.0
    a.go(name)
    t = 0.0
    while t < total:
        sec.force_t = t
        cur[0], cur[1] = t, name
        sec.update(0.1)
        if a.cur is not sec:
            break
        a.frame(0.0) if False else sec.draw(g, None, 0.1)
        t += 0.1
    if name == "credits":
        rows, th, hm = sec.layout(g)
        for kind, s in rows:
            txt = " ".join(s) if kind in ("pj", "pl") else s
            f = {"pj": credits.PF, "pl": credits.PF, "title": "kb48", "role": "kb24", "name": credits.PF}.get(kind)
            if f and g.tw(f, txt) > credits.TW - 8:
                bad[("credits-crawl", f, txt)] = (0, 0, g.tw(f, txt), 0)
        lw = sec.logo_w if hasattr(sec, "logo_w") else None
    a.go("bridge")
for (sec, f, s), (t, x0, x1, y) in sorted(bad.items(), key=lambda kv: kv[1][0]):
    print("%-13s t=%5.1f %-5s x %4d..%4d y %4d  %s" % (sec, t, f, x0, x1, y, s))
print("%d problems" % len(bad))
