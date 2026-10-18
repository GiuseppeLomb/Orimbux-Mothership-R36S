"""Pixel art drawn by code, stored as 8-bit indexed .frm files (index 0 = transparent):
  ship    80x32  the Mothership saucer (twice the detail of the old 40-unit grid; rim lights are added live)
  planet  320x110  a gas giant horizon (drawn at 2x)
  ringed  72x44  a small ringed planet (2x)
  nebula  360x240  deep-space backdrop with dust and sparkles (2x, pans sideways)
  sun     72x72  a striped synthwave sun (2x)
  python3 tools/build_art.py  ->  ports/mothership/assets/art/*.frm  + previews in tools/build/art/"""
import os
import struct
import zlib

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(ROOT, "ports", "mothership", "assets", "art")
PREV = os.path.join(ROOT, "tools", "build", "art")
B4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


class Pal(object):
    def __init__(self):
        self.cols = [(0, 0, 0)]                 # 0 = transparent

    def ramp(self, cols):
        i0 = len(self.cols)
        self.cols += [tuple(int(v) for v in c) for c in cols]
        return list(range(i0, len(self.cols)))

    def one(self, c):
        return self.ramp([c])[0]


def grid(h, w):
    Y, X = np.mgrid[0:h, 0:w]
    return X + 0.5, Y + 0.5, B4[Y % 4, X % 4]


def level(v, thr, n, soft=1.0):
    """ordered dither of v (0..1) onto n levels; soft < 1 keeps flat bands and dithers only near the edges"""
    t = 0.5 + (thr - 0.5) * soft
    return np.clip(np.floor(np.clip(v, 0, 1) * (n - 1) + t), 0, n - 1).astype(int)


def outline(img, col):
    op = img > 0
    pad = np.pad(op, 1)
    near = np.zeros_like(op)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near |= pad[1 + dy:1 + dy + op.shape[0], 1 + dx:1 + dx + op.shape[1]]
    img[near & ~op] = col
    return img


def write(name, pal, frames):
    h, w = frames[0].shape
    p = b"".join(bytes(c) for c in pal.cols).ljust(768, b"\0")
    out = [b"FRM1", struct.pack("<BHH", len(frames), w, h), p]
    for f in frames:
        z = zlib.compress(f.astype(np.uint8).tobytes(), 9)
        out.append(struct.pack("<I", len(z)) + z)
    os.makedirs(OUTD, exist_ok=True)
    open(os.path.join(OUTD, name + ".frm"), "wb").write(b"".join(out))
    # preview: 3x, magenta = transparent
    os.makedirs(PREV, exist_ok=True)
    rgb = np.array(pal.cols + [(0, 0, 0)] * (256 - len(pal.cols)), np.uint8)
    for i, f in enumerate(frames):
        im = rgb[f]
        im[f == 0] = (40, 0, 40)
        Image.fromarray(im).resize((w * 3, h * 3), Image.NEAREST).save(os.path.join(PREV, "%s_%d.png" % (name, i)))
    print(name, "%dx%d" % (w, h), "%d colours" % len(pal.cols), os.path.getsize(os.path.join(OUTD, name + ".frm")), "B")


def fbm(h, w, seed, octaves=5, base=4):
    rng = np.random.RandomState(seed)
    out, amp, tot = np.zeros((h, w)), 1.0, 0.0
    for o in range(octaves):
        gw, gh = base * 2 ** o + 1, int(base * 2 ** o * h / float(w)) + 2
        g = Image.fromarray((rng.rand(gh, gw) * 255).astype(np.uint8))
        out += np.asarray(g.resize((w, h), Image.BICUBIC), float) / 255.0 * amp
        tot += amp
        amp *= 0.5
    return out / tot


# ====================================================================== the Mothership
def ship():
    h, w = 32, 80
    P = Pal()
    OUT = P.one((10, 8, 30))
    HULL = P.ramp([(34, 36, 78), (52, 58, 108), (80, 90, 142), (120, 130, 184), (168, 178, 224), (214, 222, 248),
                   (250, 252, 255)])
    UNDER = P.ramp([(14, 12, 40), (26, 22, 62), (42, 36, 92), (64, 56, 128)])
    RIM = P.ramp([(36, 30, 86), (64, 54, 140), (100, 88, 196), (150, 140, 240)])
    GLASS = P.ramp([(14, 34, 64), (20, 60, 100), (30, 104, 156), (64, 190, 236), (196, 252, 255)])
    ALIEN = P.ramp([(46, 32, 128), (74, 54, 192), (110, 86, 236), (156, 136, 255)])
    EYE, SPARK = P.one((8, 4, 20)), P.one((255, 255, 255))
    ENG = P.ramp([(20, 84, 124), (36, 160, 206), (60, 242, 255), (210, 255, 255)])
    PORT = P.ramp([(24, 70, 110), (90, 220, 255)])
    xs, ys, thr = grid(h, w)
    img = np.zeros((h, w), int)
    cx = 40.0
    L = np.array([-0.5, -0.75, 0.45])
    L /= np.linalg.norm(L)

    # underside bowl
    nx, ny = (xs - cx) / 33.0, (ys - 23.0) / 7.0
    m = (nx ** 2 + ny ** 2 <= 1) & (ys >= 23)
    v = 0.85 - 0.75 * ny - 0.25 * nx
    img[m] = np.array(UNDER)[level(v, thr, 4, 0.35)][m]
    # engine ring
    ex, ey = (xs - cx) / 10.0, (ys - 28.6) / 2.1
    m = ex ** 2 + ey ** 2 <= 1
    v = 1.0 - np.sqrt(ex ** 2 + ey ** 2) * 0.9
    img[m] = np.array(ENG)[level(v, thr, 4, 0.5)][m]
    # top hull (ellipsoid cap) with panel seams and a row of portholes
    rx, ry, yr = 38.0, 10.0, 21.5
    nx, ny = (xs - cx) / rx, (ys - yr) / ry
    m = (nx ** 2 + ny ** 2 <= 1) & (ys <= yr)
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    sh = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    v = 0.12 + 0.88 * sh ** 1.2
    lon = nx / np.sqrt(np.clip(1 - ny ** 2, 0.05, 1))
    seam = np.zeros_like(m)
    for c in (-0.66, -0.33, 0.0, 0.33, 0.66):
        seam |= np.abs(lon - c) < 0.022
    seam |= np.abs(ny + 0.42) < 0.05
    v = np.where(seam, v - 0.2, v)
    img[m] = np.array(HULL)[level(v, thr, 7, 0.45)][m]
    for k in (-27, -18, -9, 9, 18, 27):
        x = int(cx + k)
        img[17, x - 1:x + 1] = PORT[1] if k < 0 else PORT[0]
    # rim band
    bx = (xs - cx) / 39.5
    m = (bx ** 2 <= 1) & (ys >= 20.5) & (ys <= 23.5)
    v = np.where(ys < 21.5, 0.95, np.where(ys > 22.5, 0.05, 0.4)) - 0.25 * np.clip(bx, 0, 1) * (ys < 21.5)
    img[m] = np.array(RIM)[level(v, thr, 4, 0.3)][m]
    # dome: alien first, then the glass over it
    dx, dy = (xs - cx) / 12.5, (ys - 15.5) / 11.5
    dome = (dx ** 2 + dy ** 2 <= 1) & (ys <= 18.5)
    dz = np.sqrt(np.clip(1 - dx ** 2 - dy ** 2, 0, 1))
    gsh = np.clip(dx * L[0] + dy * L[1] + dz * L[2], 0, 1)
    img[dome] = np.array(GLASS)[level(0.15 + 0.45 * gsh, thr, 4, 0.5)][dome]
    hx, hy = (xs - cx) / 6.2, (ys - 12.5) / 5.6
    head = hx ** 2 + hy ** 2 <= 1
    bxx, byy = (xs - cx) / 8.5, (ys - 19.0) / 3.5
    body = (bxx ** 2 + byy ** 2 <= 1) & dome
    az = np.sqrt(np.clip(1 - hx ** 2 - hy ** 2, 0, 1))
    ash = np.clip(hx * L[0] + hy * L[1] + az * L[2], 0, 1)
    for mm in (body, head):
        img[mm] = np.array(ALIEN)[level(0.2 + 0.8 * ash, thr, 4, 0.5)][mm]
    for sx in (-1, 1):
        ex0 = int(cx + sx * 3.0)
        img[12:14, ex0 - 1:ex0 + 1] = EYE
        img[12, ex0 - 2 if sx < 0 else ex0 + 1] = EYE
        img[12, ex0 - 1 if sx < 0 else ex0] = SPARK
        for ax, ay in ((sx * 3, 8), (sx * 4, 7)):
            img[ay, int(cx + ax) - (1 if sx < 0 else 0)] = ALIEN[2]
        tip = int(cx + sx * 5) - (1 if sx < 0 else 0)
        img[5:7, (tip - 1 if sx < 0 else tip):(tip + 1 if sx < 0 else tip + 2)] = ALIEN[3]
    # glass reflections
    spec = dome & (np.abs((dx + 0.55) + (dy + 0.25) * 0.6) < 0.09) & (dy < 0.1) & (dx < -0.2)
    img[spec] = GLASS[4]
    rim_d = dome & ((dx ** 2 + dy ** 2) > 0.8)
    img[rim_d & (img == GLASS[0])] = GLASS[2]
    # dome collar
    m = (np.abs(xs - cx) <= 13.5) & (ys >= 18) & (ys <= 20)
    v = 0.75 - 0.5 * (xs - cx) / 13.5
    img[m] = np.array(RIM)[level(v, thr, 4, 0.4)][m]
    img = outline(img, OUT)
    write("ship", P, [img])
    return P


# ====================================================================== gas giant horizon
def planet():
    h, w = 110, 320
    P = Pal()
    BANDS = P.ramp([(10, 8, 30), (20, 14, 52), (34, 22, 80), (56, 32, 112), (86, 46, 140), (124, 66, 164),
                    (168, 96, 186), (214, 140, 206)])
    ATM = P.ramp([(40, 120, 200), (60, 200, 255), (160, 240, 255)])
    xs, ys, thr = grid(h, w)
    cx, R = 160.0, 340.0
    cy = 40.0 + R
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    img = np.zeros((h, w), int)
    disk = d <= R
    nx, ny = (xs - cx) / R, (ys - cy) / R
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    L = np.array([-0.55, -0.55, 0.62])
    L /= np.linalg.norm(L)
    sh = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    turb = fbm(h, w, 11, 4, 6)
    lat = ys + turb * 9 + 3 * np.sin(xs / 23.0)
    band = 0.5 + 0.5 * np.sin(lat / 3.1) * np.cos(lat / 11.0)
    v = 0.3 * band + 0.12 * turb + 0.62 * (1 - 0.55 * (ys - 40) / 70.0) - 0.45 * np.clip(nx + 0.05, 0, 1) - 0.1
    img[disk] = np.array(BANDS)[level(v, thr, 8, 0.6)][disk]
    # limb light and atmosphere (dither thins out with height)
    limb = disk & (d > R - 2.2)
    img[limb] = np.where(sh[limb] > 0.35, ATM[1], ATM[0])
    for k, col in ((1.0, ATM[2]), (2.0, ATM[1]), (3.4, ATM[0]), (5.0, ATM[0])):
        ring = (d > R) & (d <= R + k) & (img == 0)
        keep = thr < (1.0 - (k - 1.0) / 4.5) * (0.4 + 0.6 * np.clip(-nx * 1.4 + 0.6, 0, 1))
        img[ring & keep] = col
    write("planet", P, [img])


def ringed():
    h, w = 44, 72
    P = Pal()
    BODY = P.ramp([(30, 16, 40), (70, 30, 70), (130, 50, 90), (200, 90, 100), (250, 160, 120)])
    RING = P.ramp([(60, 50, 110), (110, 100, 180), (180, 170, 240)])
    OUT = P.one((8, 6, 22))
    xs, ys, thr = grid(h, w)
    cx, cy, R = 36.0, 22.0, 13.0
    img = np.zeros((h, w), int)
    rx, ry = (xs - cx), (ys - cy)
    # ring ellipse (tilted ~ by drawing a skewed ellipse)
    ux, uy = rx * 0.97 + ry * 0.26, -rx * 0.26 + ry * 0.97
    er = np.sqrt((ux / 31.0) ** 2 + (uy / 7.5) ** 2)
    ring = (er > 0.62) & (er < 1.0) & ~((er > 0.78) & (er < 0.83))
    rv = 0.3 + 0.7 * (1 - np.abs(er - 0.8) * 3)
    back = ring & (uy < 0)
    img[back] = np.array(RING)[level(rv * 0.7, thr, 3)][back]
    d = np.sqrt(rx ** 2 + ry ** 2)
    body = d <= R
    nx, ny = rx / R, ry / R
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    sh = np.clip(-0.6 * nx - 0.5 * ny + 0.62 * nz, 0, 1)
    band = 0.5 + 0.5 * np.sin((ys + 1.5 * np.sin(xs / 5.0)) / 1.7)
    img[body] = np.array(BODY)[level(0.75 * sh + 0.25 * band * sh, thr, 5)][body]
    front = ring & (uy >= 0)
    img[front] = np.array(RING)[level(rv, thr, 3)][front]
    img = outline(img, OUT)
    write("ringed", P, [img])


# ====================================================================== nebula backdrop
def nebula():
    h, w = 240, 360
    P = Pal()
    A = P.ramp([(4, 2, 12), (8, 6, 26), (14, 10, 44), (24, 16, 70), (40, 24, 104), (64, 34, 136), (100, 48, 160),
                (150, 66, 176)])
    B = P.ramp([(4, 2, 12), (6, 10, 30), (10, 18, 52), (16, 30, 80), (22, 48, 110), (30, 76, 140), (44, 110, 170),
                (70, 150, 200)])
    STAR = P.ramp([(70, 66, 120), (140, 136, 200), (230, 230, 255), (255, 255, 255)])
    PINK = P.ramp([(255, 120, 200), (255, 200, 120)])
    xs, ys, thr = grid(h, w)
    n1, n2, n3 = fbm(h, w, 3, 6, 3), fbm(h, w, 8, 6, 3), fbm(h, w, 21, 3, 2)
    dens = np.clip((n1 - 0.38) * 2.6, 0, 1) ** 1.3
    # a diagonal band so the clouds read like a galaxy arm
    arm = np.exp(-((ys - (0.35 * xs + 40 + 30 * (n3 - 0.5))) / 70.0) ** 2)
    dens = dens * (0.35 + 0.65 * arm)
    which = (n2 + (thr - 0.5) * 0.25) > 0.52
    lv = level(dens, thr, 8)
    img = np.where(which, np.array(B)[lv], np.array(A)[lv])
    rng = np.random.RandomState(4)
    for _ in range(900):
        x, y = rng.randint(0, w), rng.randint(0, h)
        img[y, x] = STAR[0] if rng.rand() < 0.75 else STAR[1]
    for _ in range(40):
        x, y = rng.randint(2, w - 2), rng.randint(2, h - 2)
        img[y, x] = STAR[3]
        img[y - 1, x] = img[y + 1, x] = img[y, x - 1] = img[y, x + 1] = STAR[1]
    for _ in range(9):                                  # sparkles: plus shapes, some warm
        x, y = rng.randint(4, w - 4), rng.randint(4, h - 4)
        c = PINK[rng.randint(0, 2)] if rng.rand() < 0.4 else STAR[2]
        img[y, x - 3:x + 4] = STAR[0]
        img[y - 3:y + 4, x] = STAR[0]
        img[y, x - 1:x + 2] = c
        img[y - 1:y + 2, x] = c
        img[y, x] = STAR[3]
    write("nebula", P, [img])


# ====================================================================== synthwave sun
def sun():
    h, w = 72, 72
    P = Pal()
    S = P.ramp([(255, 240, 140), (255, 210, 80), (255, 160, 50), (255, 110, 60), (255, 70, 110), (230, 46, 150),
                (170, 40, 190)])
    xs, ys, thr = grid(h, w)
    cx, cy, R = 36.0, 36.0, 34.0
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    img = np.zeros((h, w), int)
    m = d <= R
    v = (ys - (cy - R)) / (2 * R)
    img[m] = np.array(S)[level(v, thr, 7)][m]
    # stripes cut through the lower half, thicker towards the bottom
    y0 = cy - 4
    yy = ys - y0
    period = 7.0
    gap = np.clip(yy / (cy + R - y0) * 4.2, 0, 4.2)
    cut = (yy > 0) & ((yy % period) < gap)
    img[cut] = 0
    write("sun", P, [img])


if __name__ == "__main__":
    ship()
    planet()
    ringed()
    nebula()
    sun()
