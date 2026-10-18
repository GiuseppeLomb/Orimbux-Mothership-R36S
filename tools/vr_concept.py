"""Renders VOID RUNNER concept sheets from the real sprite data (vr_art.py)."""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ports", "mothership"))
import vr_art as A  # noqa

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vr"
os.makedirs(OUT, exist_ok=True)
GF = "/home/claude/gf/ofl"
F_TITLE = lambda s: ImageFont.truetype(GF + "/pressstart2p/PressStart2P-Regular.ttf", s)  # noqa
F_TXT = lambda s: ImageFont.truetype(GF + "/vt323/VT323-Regular.ttf", s)  # noqa

# sanity: equal row widths
for k, e in list(A.ENEMIES.items()) + [("boss", A.BOSS)]:
    ws = set(len(r) for r in e["grid"])
    assert len(ws) == 1, (k, ws)


def pal_for(biome, extra=None):
    p = dict(A.VOID)
    p["A"] = biome["accent"]
    p["B"] = biome["accent2"]
    p["1"], p["2"], p["3"] = biome["ground"]
    if extra:
        p.update(extra)
    return p


def blit(img, grid, x, y, s, pal, alpha=255):
    d = ImageDraw.Draw(img, "RGBA")
    for ry, row in enumerate(grid):
        for rx, ch in enumerate(row):
            c = pal.get(ch)
            if c:
                d.rectangle([x + rx * s, y + ry * s, x + rx * s + s - 1, y + ry * s + s - 1], fill=c + (alpha,))


def glow(img, cx, cy, r, col, strength=0.5):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(6, 0, -1):
        rr = r * i / 6
        a = int(255 * strength * (1 - i / 7) ** 1.5)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (a,))
    img.alpha_composite(layer)


def ground(w, h, biome, seed=1, s=3):
    """dithered value-noise ground in 3 tones + void veins, in art pixels of size s"""
    rng = np.random.RandomState(seed)
    gw, gh = w // s + 1, h // s + 1

    def noise(scale):
        cw, ch = gw // scale + 2, gh // scale + 2
        g = rng.rand(ch, cw)
        yy, xx = np.mgrid[0:gh, 0:gw] / float(scale)
        x0, y0 = xx.astype(int), yy.astype(int)
        fx, fy = xx - x0, yy - y0
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = g[y0, x0] * (1 - fx) + g[y0, x0 + 1] * fx
        b = g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x0 + 1] * fx
        return a * (1 - fy) + b * fy
    n = noise(14) * 0.65 + noise(5) * 0.35
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    th = np.tile(bayer, (gh // 4 + 1, gw // 4 + 1))[:gh, :gw] * 0.18
    lvl = np.where(n + th < 0.45, 0, np.where(n + th < 0.68, 1, 2))
    tones = np.array(biome["ground"], dtype=np.uint8)
    arr = tones[lvl]
    # void corruption: only inside patches (everywhere in the Maw)
    patch = noise(22)
    th_p = 0.0 if biome["id"] == "maw" else 0.6
    zone = patch > th_p
    tint = np.array((40, 0, 60), dtype=np.int16)
    arr = arr.astype(np.int16)
    arr[zone] = (arr[zone] * 0.6 + tint * 0.4).astype(np.int16)
    v = noise(9)
    vein = (np.abs(v - 0.5) < 0.02) & zone
    arr[vein] = (90, 20, 140)
    core = (np.abs(v - 0.5) < 0.007) & zone
    arr[core] = (200, 70, 255)
    arr = arr.clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB").resize((gw * s, gh * s), Image.NEAREST).crop((0, 0, w, h))
    return img.convert("RGBA")


def text(img, s, xy, font, col, anchor="la", shadow=True):
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((xy[0] + 2, xy[1] + 2), s, font=font, fill=(0, 0, 0), anchor=anchor)
    d.text(xy, s, font=font, fill=col, anchor=anchor)


# ================================================================== sheet 1: biomes
def sheet_biomes():
    W, H = 1280, 900
    img = Image.new("RGBA", (W, H), (6, 2, 14, 255))
    text(img, "VOID RUNNER  -  BIOMAS", (40, 30), F_TITLE(28), (200, 120, 255))
    text(img, "Mesma linguagem visual (vazio, quitina, fendas). Cores diferentes por bioma.", (40, 76), F_TXT(30),
         (190, 180, 220))
    bw, bh = 384, 360
    for i, b in enumerate(A.BIOMES):
        col, row = i % 3, i // 3
        x, y = 40 + col * (bw + 22), 130 + row * (bh + 30)
        g = ground(bw, 250, b, seed=10 + i)
        pal = pal_for(b)
        rnd = random.Random(i)
        dec = A.DECOR[b["id"]]
        for k in range(9):
            grid = dec[k % len(dec)]
            blit(g, grid, rnd.randint(0, bw - 30), rnd.randint(0, 220), 3, pal)
        blit(g, A.RIFT, rnd.randint(40, bw - 80), rnd.randint(40, 180), 3, pal)
        glow(g, bw - 70, 150, 34, b["accent"], 0.35)
        blit(g, A.ENEMIES["mite"]["grid"], bw - 92, 140, 4, pal)
        blit(g, A.ENEMIES["skitter"]["grid"], bw - 170, 60, 3, pal)
        img.alpha_composite(g, (x, y))
        d = ImageDraw.Draw(img)
        d.rectangle([x - 3, y - 3, x + bw + 2, y + 252], outline=b["accent"], width=3)
        text(img, b["name"], (x, y + 266), F_TITLE(14), b["accent"])
        words, line, yy = b["desc"].split(), "", y + 290
        for w_ in words:
            if len(line + " " + w_) > 40:
                text(img, line, (x, yy), F_TXT(22), (210, 200, 230))
                yy += 18
                line = w_
            else:
                line = (line + " " + w_).strip()
        text(img, line, (x, yy), F_TXT(22), (210, 200, 230))
        for j, c in enumerate(b["ground"] + [b["accent"], b["accent2"], (178, 60, 255), (255, 60, 200)]):
            d.rectangle([x + j * 32, y + 334, x + j * 32 + 26, y + 352], fill=c)
    img.convert("RGB").save(os.path.join(OUT, "vr_biomas.png"))


# ================================================================== sheet 2: bestiary
def sheet_bestiary():
    W, H = 1280, 900
    img = Image.new("RGBA", (W, H), (6, 2, 14, 255))
    text(img, "VOID RUNNER  -  BESTIARIO", (40, 30), F_TITLE(28), (200, 120, 255))
    text(img, "Inimigos sempre do vazio (roxo/preto, olhos a brilhar). O bioma infunde a cor de acento.",
         (40, 76), F_TXT(30), (190, 180, 220))
    # runner
    x0, y0 = 40, 130
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + 230, y0 + 300], fill=(16, 12, 34), outline=(60, 242, 255), width=3)
    glow(img, x0 + 150, y0 + 150, 70, (255, 230, 140), 0.35)
    blit(img, A.RUNNER, x0 + 70, y0 + 70, 9, A.RUNNER_PAL)
    text(img, "O RUNNER", (x0 + 115, y0 + 220), F_TITLE(14), (60, 242, 255), "ma")
    text(img, "Luz contra o vazio.", (x0 + 115, y0 + 248), F_TXT(24), (210, 200, 230), "ma")
    text(img, "Lanterna = arma.", (x0 + 115, y0 + 270), F_TXT(24), (210, 200, 230), "ma")
    # enemies
    tundra = A.BIOMES[0]
    x = 300
    for k in ("mite", "skitter", "seer", "brood", "gorger"):
        e = A.ENEMIES[k]
        g = e["grid"]
        s = 7 if len(g[0]) < 13 else 6
        d.rectangle([x, y0, x + 180, y0 + 300], fill=(16, 12, 34), outline=(106, 31, 176), width=3)
        blit(img, g, x + 90 - len(g[0]) * s // 2, y0 + 110 - len(g) * s // 2, s, pal_for(tundra))
        text(img, e["name"], (x + 90, y0 + 210), F_TITLE(12), (255, 60, 200), "ma")
        words, line, yy = e["desc"].split(), "", y0 + 236
        for w in words:
            if len(line + " " + w) > 20:
                text(img, line, (x + 90, yy), F_TXT(22), (210, 200, 230), "ma")
                yy += 20
                line = w
            else:
                line = (line + " " + w).strip()
        text(img, line, (x + 90, yy), F_TXT(22), (210, 200, 230), "ma")
        x += 196
    # boss + accent variants
    y1 = 470
    d.rectangle([40, y1, 560, y1 + 390], fill=(16, 12, 34), outline=(255, 60, 200), width=3)
    glow(img, 300, y1 + 170, 150, (255, 60, 200), 0.3)
    blit(img, A.BOSS["grid"], 300 - 24 * 8 // 2, y1 + 50, 8, pal_for(A.BIOMES[4]))
    text(img, A.BOSS["name"], (300, y1 + 290), F_TITLE(18), (255, 60, 200), "ma")
    text(img, A.BOSS["desc"], (300, y1 + 324), F_TXT(24), (210, 200, 230), "ma")
    text(img, "O MESMO INIMIGO EM CADA BIOMA", (600, y1), F_TITLE(12), (200, 120, 255))
    for i, b in enumerate(A.BIOMES):
        xx = 600 + i * 132
        d.rectangle([xx, y1 + 30, xx + 120, y1 + 170], fill=b["ground"][1], outline=b["accent"], width=3)
        blit(img, A.ENEMIES["gorger"]["grid"], xx + 60 - 32, y1 + 60, 4, pal_for(b))
        text(img, b["id"].upper(), (xx + 60, y1 + 140), F_TXT(22), b["accent"], "ma")
    text(img, "ARMAS DE LUZ", (600, y1 + 200), F_TITLE(12), (255, 236, 140))
    for i, (n, desc, col) in enumerate(A.WEAPONS):
        xx, yy = 600 + (i % 2) * 340, y1 + 230 + (i // 2) * 52
        glow(img, xx + 16, yy + 16, 18, col, 0.6)
        d.rectangle([xx + 8, yy + 8, xx + 24, yy + 24], fill=col)
        text(img, n, (xx + 40, yy + 2), F_TITLE(10), col)
        text(img, desc if len(desc) < 34 else desc[:32] + "...", (xx + 40, yy + 18), F_TXT(20), (190, 180, 220))
    img.convert("RGB").save(os.path.join(OUT, "vr_bestiario.png"))


# ================================================================== gameplay mock
def gameplay(biome_i, name, boss=False, seed=3):
    W, H = 640, 480
    b = A.BIOMES[biome_i]
    pal = pal_for(b)
    img = ground(W, H, b, seed=seed)
    rnd = random.Random(seed)
    for k in range(14):
        grid = A.DECOR[b["id"]][k % 2]
        blit(img, grid, rnd.randint(0, W - 30), rnd.randint(30, H - 30), 3, pal)
    blit(img, A.RIFT, 470, 330, 3, pal)
    blit(img, A.RIFT, 90, 380, 3, pal)
    # vignette fog
    fog = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog)
    for i in range(12):
        a = int(10 + i * 9)
        fd.rectangle([i * 8, i * 6, W - i * 8, H - i * 6], outline=b["ground"][0] + (a,), width=8)
    img.alpha_composite(fog)
    px, py = W // 2, H // 2 + 10
    # xp shards
    for k in range(26):
        a = rnd.random() * math.tau
        r = rnd.uniform(40, 260)
        blit(img, A.SHARD, int(px + math.cos(a) * r), int(py + math.sin(a) * r * 0.8), 2, pal)
    # enemies swarm
    kinds = ["mite"] * 10 + ["skitter"] * 3 + ["seer", "brood", "gorger"]
    for k in range(70):
        a = rnd.random() * math.tau
        r = rnd.uniform(110, 330)
        kind = rnd.choice(kinds)
        g = A.ENEMIES[kind]["grid"]
        s = 3 if kind != "gorger" else 3
        blit(img, g, int(px + math.cos(a) * r), int(py + math.sin(a) * r * 0.75), s, pal)
    if boss:
        glow(img, 500, 120, 110, (255, 60, 200), 0.35)
        blit(img, A.BOSS["grid"], 500 - 48, 60, 4, pal)
    # weapons: prism ring + bolts + nova
    glow(img, px + 18, py + 20, 60, (255, 236, 140), 0.25)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([px - 92, py - 72, px + 128, py + 108], outline=(255, 255, 255, 70), width=3)
    for i in range(3):
        a = 0.6 + i * math.tau / 3
        cx, cy = px + 18 + math.cos(a) * 80, py + 20 + math.sin(a) * 80
        glow(img, int(cx), int(cy), 16, (200, 160, 255), 0.7)
        d.polygon([(cx, cy - 10), (cx + 7, cy), (cx, cy + 10), (cx - 7, cy)], fill=(230, 210, 255))
    for (tx, ty) in ((px - 150, py - 90), (px + 170, py + 40), (px + 60, py - 150)):
        sx, sy = px + 18, py + 20
        for t in range(10):
            f = t / 10.0
            x = sx + (tx - sx) * (0.55 + f * 0.45)
            y = sy + (ty - sy) * (0.55 + f * 0.45)
            d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(60, 242, 255, int(80 + 175 * f)))
        glow(img, int(tx), int(ty), 12, (60, 242, 255), 0.8)
    blit(img, A.RUNNER, px, py, 3, A.RUNNER_PAL)
    d = ImageDraw.Draw(img, "RGBA")
    # HUD
    d.rectangle([0, 0, W, 14], fill=(10, 0, 20, 230))
    d.rectangle([2, 3, int(W * 0.62), 11], fill=(178, 60, 255))
    d.rectangle([2, 3, int(W * 0.62), 5], fill=(230, 160, 255))
    text(img, "LV 14", (8, 20), F_TITLE(12), (255, 255, 255))
    text(img, "07:42", (W // 2, 20), F_TITLE(16), (255, 255, 255), "ma")
    text(img, "x 1.284", (W - 10, 20), F_TITLE(10), (255, 60, 200), "ra")
    text(img, b["name"], (W - 10, 36), F_TXT(20), b["accent"], "ra")
    d.rectangle([px - 2, py + 44, px + 38, py + 48], fill=(40, 0, 20))
    d.rectangle([px - 2, py + 44, px + 26, py + 48], fill=(255, 70, 90))
    for i, (n, desc, col) in enumerate(A.WEAPONS[:4]):
        x = 8 + i * 30
        d.rectangle([x, H - 34, x + 24, H - 10], fill=(16, 12, 34, 230), outline=col, width=2)
        d.rectangle([x + 8, H - 26, x + 16, H - 18], fill=col)
    if boss:
        d.rectangle([140, 52, 500, 58], fill=(40, 0, 30))
        d.rectangle([140, 52, 420, 58], fill=(255, 60, 200))
        text(img, "A MATRIARCA", (320, 38), F_TXT(20), (255, 60, 200), "ma")
    # scanlines
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(2, H, 3):
        sd.line([(0, y), (W, y)], fill=(0, 0, 0, 60))
    img.alpha_composite(sl)
    img.convert("RGB").save(os.path.join(OUT, name))


def title():
    W, H = 640, 480
    b = A.BIOMES[4]
    img = ground(W, H, b, seed=9)
    pal = pal_for(b)
    glow(img, W // 2, 250, 220, (178, 60, 255), 0.35)
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(4)
    pts_l, pts_r = [], []
    for i in range(13):
        y = 168 + i * 12
        w = 6 + 26 * math.sin(i / 12.0 * math.pi)
        jx = rnd.randint(-10, 10)
        pts_l.append((W // 2 + jx - w, y))
        pts_r.append((W // 2 + jx + w, y))
    poly = pts_l + pts_r[::-1]
    d.polygon(poly, fill=(255, 60, 200, 255))
    inner = [(x + (W // 2 - x) * 0.45, y) for x, y in pts_l] + [(x - (x - W // 2) * 0.45, y) for x, y in pts_r[::-1]]
    d.polygon(inner, fill=(10, 0, 20, 255))
    for k in range(8):
        a = rnd.uniform(-0.5, 0.5) + (math.pi if k % 2 else 0)
        x0, y0 = W // 2, 200 + rnd.randint(0, 100)
        x1, y1 = x0 + math.cos(a) * rnd.randint(60, 140), y0 + math.sin(a) * rnd.randint(20, 60)
        d.line([(x0, y0), (x1, y1)], fill=(178, 60, 255, 200), width=3)
    glow(img, W // 2, 380, 50, (255, 236, 140), 0.5)
    blit(img, A.RUNNER, W // 2 - 24, 330, 4, A.RUNNER_PAL)
    for k, (gx, gy) in enumerate(((90, 300), (520, 320), (140, 400), (470, 410), (60, 220), (560, 230))):
        blit(img, A.ENEMIES[["mite", "skitter", "seer"][k % 3]]["grid"], gx, gy, 3, pal)
    text(img, "VOID", (W // 2 + 4, 60 + 4), F_TITLE(56), (255, 60, 200), "ma", False)
    text(img, "VOID", (W // 2, 60), F_TITLE(56), (240, 220, 255), "ma", False)
    text(img, "RUNNER", (W // 2, 128), F_TITLE(32), (178, 60, 255), "ma")
    text(img, "PRESS START", (W // 2, 446), F_TITLE(12), (255, 255, 255), "ma")
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(2, H, 3):
        sd.line([(0, y), (W, y)], fill=(0, 0, 0, 60))
    img.alpha_composite(sl)
    img.convert("RGB").save(os.path.join(OUT, "vr_title.png"))


sheet_biomes()
sheet_bestiary()
gameplay(0, "vr_game_tundra.png")
gameplay(1, "vr_game_ember.png", seed=5)
gameplay(4, "vr_game_maw.png", boss=True, seed=7)
title()
print("ok")


def blackhole_shot(biome_i=1, name="vr_blackhole.png", seed=11):
    W, H = 640, 480
    b = A.BIOMES[biome_i]
    pal = pal_for(b)
    img = ground(W, H, b, seed=seed)
    rnd = random.Random(seed)
    for k in range(12):
        blit(img, A.DECOR[b["id"]][k % 2], rnd.randint(0, W - 30), rnd.randint(30, H - 30), 3, pal)
    bx, by, R = 170, 170, 46       # black hole centre + event horizon radius
    # darkening gravity well
    well = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(well)
    for i in range(14, 0, -1):
        rr = R + i * 16
        wd.ellipse([bx - rr, by - rr, bx + rr, by + rr], fill=(10, 0, 20, int(14 + (14 - i) * 9)))
    img.alpha_composite(well)
    d = ImageDraw.Draw(img, "RGBA")
    # spiral streams of matter (ground debris being sucked in)
    for arm in range(5):
        for k in range(70):
            f = k / 70.0
            r = R + 8 + (1 - f) * 230
            a = arm * math.tau / 5 + f * 5.2
            x, y = bx + math.cos(a) * r, by + math.sin(a) * r * 0.86
            s = 2 + int(3 * (1 - f))
            col = (255, 60, 200) if k % 3 == 0 else (178, 60, 255)
            if k % 5 == 0:
                col = b["accent"]
            d.rectangle([x, y, x + s, y + s], fill=col + (int(90 + 165 * f),))
    # enemies & shards being pulled (stretched toward the hole)
    for k in range(34):
        a = rnd.random() * math.tau
        r = rnd.uniform(R + 30, 300)
        x, y = bx + math.cos(a) * r, by + math.sin(a) * r * 0.86
        kind = rnd.choice(["mite", "mite", "skitter", "seer"])
        g = A.ENEMIES[kind]["grid"]
        blit(img, g, int(x), int(y), 3, pal)
        if r < 160:   # streak
            dx, dy = (bx - x) / r, (by - y) / r
            for t in range(6):
                d.rectangle([x + 12 + dx * t * 6, y + 10 + dy * t * 6, x + 15 + dx * t * 6, y + 13 + dy * t * 6],
                            fill=(178, 60, 255, 160 - t * 25))
    for k in range(18):
        a = rnd.random() * math.tau
        r = rnd.uniform(R + 20, 220)
        blit(img, A.SHARD, int(bx + math.cos(a) * r), int(by + math.sin(a) * r * 0.86), 2, pal)
    # accretion disk (tilted ring) + photon ring + horizon
    for i in range(3):
        rr = R + 14 + i * 7
        d.ellipse([bx - rr - 10, by - rr * 0.38, bx + rr + 10, by + rr * 0.38],
                  outline=[(255, 240, 255), (255, 60, 200), (178, 60, 255)][i] + (230,), width=5)
    glow(img, bx, by, R + 50, (255, 60, 200), 0.45)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([bx - R - 4, by - R - 4, bx + R + 4, by + R + 4], outline=(255, 220, 250, 255), width=3)
    d.ellipse([bx - R, by - R, bx + R, by + R], fill=(0, 0, 0, 255))
    # front half of the disk passes in front of the hole
    rr = R + 14
    d.arc([bx - rr - 10, by - rr * 0.38, bx + rr + 10, by + rr * 0.38], 0, 180, fill=(255, 240, 255), width=5)
    d.arc([bx - rr - 17, by - (rr + 7) * 0.38, bx + rr + 17, by + (rr + 7) * 0.38], 0, 180,
          fill=(255, 60, 200), width=4)
    # player running away, with pull vector + dash trail
    px, py = 430, 330
    for t in range(6):
        d.rectangle([px - 16 - t * 12, py + 12 - t * 7, px - 6 - t * 12, py + 30 - t * 7],
                    fill=(60, 242, 255, 150 - t * 24))
    glow(img, px + 18, py + 20, 50, (255, 236, 140), 0.3)
    blit(img, A.RUNNER, px, py, 3, A.RUNNER_PAL)
    d = ImageDraw.Draw(img, "RGBA")
    # danger vignette on the side of the hole
    vg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vg)
    for i in range(10):
        vd.rectangle([-i * 10, -i * 10, W * 0.55 - i * 30, H * 0.6 - i * 20], outline=(255, 0, 120, 10), width=12)
    img.alpha_composite(vg)
    d = ImageDraw.Draw(img, "RGBA")
    # HUD + gravity meter
    d.rectangle([0, 0, W, 14], fill=(10, 0, 20, 230))
    d.rectangle([2, 3, int(W * 0.44), 11], fill=(178, 60, 255))
    text(img, "LV 9", (8, 20), F_TITLE(12), (255, 255, 255))
    text(img, "05:18", (W // 2, 20), F_TITLE(16), (255, 255, 255), "ma")
    text(img, "x 642", (W - 10, 20), F_TITLE(10), (255, 60, 200), "ra")
    d.rectangle([W - 190, 44, W - 12, 64], fill=(16, 0, 30, 230), outline=(255, 60, 200), width=2)
    d.rectangle([W - 186, 48, W - 186 + 100, 60], fill=(255, 60, 200))
    text(img, "GRAVIDADE", (W - 196, 46), F_TXT(20), (255, 60, 200), "ra")
    text(img, "FUGA 142 m", (W - 12, 70), F_TXT(20), (60, 242, 255), "ra")
    d.rectangle([px - 2, py + 44, px + 38, py + 48], fill=(40, 0, 20))
    d.rectangle([px - 2, py + 44, px + 30, py + 48], fill=(255, 70, 90))
    text(img, "A = VOID DASH", (8, H - 30), F_TITLE(10), (60, 242, 255))
    sl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sl)
    for y in range(2, H, 3):
        sd.line([(0, y), (W, y)], fill=(0, 0, 0, 60))
    img.alpha_composite(sl)
    img.convert("RGB").save(os.path.join(OUT, name))


blackhole_shot()
blackhole_shot(0, "vr_blackhole_tundra.png", seed=4)
