# The Mothership UI kit: one typeface (Tiny5), one header, one footer, one way to draw buttons.
# Every screen answers three questions at a glance:
#   top bar    -> where am I (category, step of the music workflow, app name) + what is playing
#   middle     -> the thing to look at (big), details (small)
#   bottom bar -> the 3-4 buttons that matter here; everything else lives in the SELECT help
import re
import time

from engine import C, W, H

# ---------------------------------------------------------------- type scale (Tiny5 everywhere)
DISPLAY = "kb48"     # splash / huge numbers
TITLE = "kb32"       # screen titles, the main value
HEAD = "kb24"        # section headings, list items that matter
BODY = "k24"         # normal text
SMALL = "k16"        # labels, hints, secondary info
HEADER_H = 48
FOOTER_H = 44
APP = None           # set by App: the footer hints and the header chip need it

BTN_COL = {"A": C["orange"], "B": (255, 96, 128), "X": C["cyan"], "Y": C["green"]}
MUSIC_FLOW = [  # the workflow: START jumps to the next one
    ("pulsar", "PULSAR", "TEMPO"), ("forge", "BEAT FORGE", "RITMO"), ("abductor", "ABDUCTOR", "SONS TEUS"),
    ("reactor", "LOOP REACTOR", "AO VIVO"), ("xeno", "XENO SYNTH", "MELODIA"), ("vox", "VOX NEBULA", "VOZ"),
    ("decks", "TWIN DECKS", "MISTURA"), ("warp", "WARP FLOOR", "OUVIR"),
]
MUSIC_KEYS = [k for k, _, _ in MUSIC_FLOW]
CAT_COL = {"MÚSICA": C["orange"], "JOGOS": (255, 110, 170), "SISTEMA": C["violet"], "NAVE": C["cyan"]}


def where(key):
    """(category, step label or '', colour)"""
    if key in MUSIC_KEYS:
        i = MUSIC_KEYS.index(key)
        return "MÚSICA", "PASSO %d DE %d · %s" % (i + 1, len(MUSIC_KEYS), MUSIC_FLOW[i][2]), CAT_COL["MÚSICA"]
    if key in ("pet", "voidrunner", "beatduel", "quiz", "earlab"):
        return "JOGOS", "", CAT_COL["JOGOS"]
    if key in ("hangar", "trailer", "credits"):
        return "SISTEMA", "", CAT_COL["SISTEMA"]
    return "NAVE", "", CAT_COL["NAVE"]


# ---------------------------------------------------------------- text helpers
def wrap(g, font, s, w):
    lines, line = [], ""
    for para in str(s).split("\n"):
        for word in para.split():
            test = (line + " " + word).strip()
            if line and g.tw(font, test) > w:
                lines.append(line)
                line = word
            else:
                line = test
        lines.append(line)
        line = ""
    return lines


def para(g, font, s, x, y, w, col, lh=None, align="left", a=255):
    lh = lh or g.th(font) + 2
    for ln in wrap(g, font, s, w):
        g.text(font, ln, x, y, col, a, align)
        y += lh
    return y


def fit(g, font, s, w):
    """shorten with '…' to fit"""
    s = str(s)
    if g.tw(font, s) <= w:
        return s
    while s and g.tw(font, s + "…") > w:
        s = s[:-1]
    return s + "…"


# ---------------------------------------------------------------- shapes
def box(g, x, y, w, h, fill, a=255, cut=2):
    """rectangle with cut corners (the house style)"""
    g.rects([(x + cut, y, w - 2 * cut, h), (x, y + cut, cut, h - 2 * cut), (x + w - cut, y + cut, cut, h - 2 * cut)],
            fill, a)


def outline(g, x, y, w, h, col, t=2, a=255, cut=2):
    g.rects([(x + cut, y, w - 2 * cut, t), (x + cut, y + h - t, w - 2 * cut, t),
             (x, y + cut, t, h - 2 * cut), (x + w - t, y + cut, t, h - 2 * cut)], col, a)


def panel(g, x, y, w, h, accent=None, title=None, fill=None, a=245):
    box(g, x, y, w, h, fill or C["panel"], a)
    outline(g, x, y, w, h, accent or C["hullhi"], 2)
    if title:
        tw = g.tw(SMALL, title) + 16
        box(g, x + 10, y - 9, tw, 18, accent or C["hullhi"])
        g.text(SMALL, title, x + 18, y - 9, C["void"])


def bar(g, x, y, w, h, frac, col, back=None):
    g.rect(x, y, w, h, back or C["led"])
    g.rect(x, y, int(w * max(0.0, min(1.0, frac))), h, col)


# ---------------------------------------------------------------- button glyphs
_PHRASES = [
    (r"analog(ico|\.)?\s*esq(\.|uerdo)?|stick esq|l-stick|LS\b", " §LS "),
    (r"analog(ico|\.)?\s*dir(\.|eito)?|stick dir|r-stick|RS\b", " §RS "),
    (r"cima/baixo|up/dn|\^v|UD\b", " §UD "), (r"esq/dir|esquerda/direita|left/right|<>|LR\b", " §LR "),
    (r"\bsetas\b|\bcruz\b|\bdpad\b", " §DPAD "),
    (r"\bcima\b|\bup\b", " §U "), (r"\bbaixo\b|\bdown\b|\bdn\b", " §D "),
    (r"\besq(uerda)?\b|\bleft\b", " §L "), (r"\bdir(eita)?\b|\bright\b", " §R "),
]
_TOK = re.compile(r"(\+|/|\s+|[^\s+/]+)")


def tokens(spec):
    s = " " + str(spec) + " "
    for pat, rep in _PHRASES:
        s = re.sub(pat, rep, s, flags=re.I)
    out = []
    for tk in _TOK.findall(s):
        if tk.isspace():
            continue
        u = tk.upper()
        if tk.startswith("§"):
            out.append(("dpad", tk[1:]) if tk[1:] not in ("LS", "RS") else ("stick", tk[1:2]))
        elif u in ("A", "B", "X", "Y"):
            out.append(("btn", u))
        elif u in ("L1", "R1", "L2", "R2", "L3", "R3"):
            out.append(("pill", u))
        elif u in ("SEL", "SELECT"):
            out.append(("pill", "SELECT"))
        elif u == "START":
            out.append(("pill", "START"))
        elif tk in ("+", "/"):
            out.append(("sep", tk))
        else:
            out.append(("text", tk))
    return out


def btn(g, x, y, name, s=18):
    col = BTN_COL.get(name, C["muted"])
    box(g, x, y, s, s, col, cut=4 if s >= 18 else 3)
    g.text(SMALL, name, x + s // 2 + 1, y + (s - 20) // 2, C["void"], 255, "center")
    return x + s


def dpad(g, x, y, which, s=18):
    t = s // 3
    arms = {"U": [(x + t, y, t, t + 1)], "D": [(x + t, y + 2 * t - 1, t, t + 1)],
            "L": [(x, y + t, t + 1, t)], "R": [(x + 2 * t - 1, y + t, t + 1, t)]}
    lit = {"UD": "UD", "LR": "LR", "DPAD": "UDLR"}.get(which, which)
    g.rects([(x + t, y, t, s), (x, y + t, s, t)], C["hullhi"])
    for k in lit:
        g.rects(arms[k], C["text"])
    return x + s


def stick(g, x, y, side, s=18):
    box(g, x, y, s, s, C["hullhi"], cut=5)
    box(g, x + 4, y + 4, s - 8, s - 8, C["text"], cut=3)
    g.text(SMALL, side, x + s // 2 + 1, y + (s - 20) // 2, C["void"], 255, "center")
    return x + s


def pill(g, x, y, label, h=18):
    w = g.tw(SMALL, label) + 10
    box(g, x, y, w, h, C["hull"])
    outline(g, x, y, w, h, C["hullhi"], 1)
    g.text(SMALL, label, x + 5, y + (h - 20) // 2, C["soft"])
    return x + w


def keys(g, spec, x, y, s=18):
    """draw a key spec ('SEL+A', 'L1/R1', 'setas', 'cima/baixo'...) as glyphs; returns end x"""
    for kind, v in tokens(spec):
        if kind == "btn":
            x = btn(g, x, y, v, s) + 2
        elif kind == "pill":
            x = pill(g, x, y, v, s) + 2
        elif kind == "dpad":
            x = dpad(g, x, y, v, s) + 2
        elif kind == "stick":
            x = stick(g, x, y, v, s) + 2
        elif kind == "sep":
            x = g.text(SMALL, v, x, y + (s - 20) // 2, C["muted"]) + 2
        else:
            x = g.text(SMALL, v, x, y + (s - 20) // 2, C["soft"]) + 4
    return x


def keys_w(g, spec, s=18):
    w = 0
    for kind, v in tokens(spec):
        if kind in ("btn", "dpad", "stick"):
            w += s + 2
        elif kind == "pill":
            w += g.tw(SMALL, v) + 12
        elif kind == "sep":
            w += g.tw(SMALL, v) + 2
        else:
            w += g.tw(SMALL, v) + 4
    return w


# ---------------------------------------------------------------- header
def chip(g, app, x, y):
    """now playing: ▶/■ + BPM, REC, MIC"""
    st = app.now_playing() if hasattr(app, "now_playing") else {"playing": False}
    playing = st.get("playing")
    w, h = 140, 30
    box(g, x, y, w, h, C["hull"])
    col = C["green"] if playing else C["muted"]
    if playing:
        ph = (app.mixer.beat_at(app.mixer.clock) % 1.0) if app.cfg.get("anim", True) else 0.5
        g.rect(x + 8, y + 7, 4, 16, col, int(120 + 135 * (1 - ph)))
        g.text(SMALL, "▶", x + 16, y + 5, col)
    else:
        g.text(SMALL, "■", x + 10, y + 5, col)
    g.text(HEAD, "%d" % round(app.mixer.bpm), x + 30, y + 1, C["text"])
    if not (st.get("rec") or st.get("mic")):              # no room for both
        g.text(SMALL, "BPM", x + 32 + g.tw(HEAD, "%d" % round(app.mixer.bpm)), y + 5, C["muted"])
    if st.get("rec"):
        if int(time.time() * 2) % 2 == 0:
            g.rect(x + w - 30, y + 11, 8, 8, (255, 60, 80))
        g.text(SMALL, "REC", x + w - 4, y + 5, (255, 90, 100), 255, "right")
    elif st.get("mic"):
        g.text(SMALL, "MIC", x + w - 6, y + 5, C["green"], 255, "right")


def header(g, app, title, key=None):
    cat, step, col = where(key)
    g.rect(0, 0, W, HEADER_H, C["deck"])
    g.rect(0, HEADER_H - 2, W, 2, col)
    g.text(SMALL, cat + ("  ·  " + step if step else ""), 14, 2, col)
    g.text(HEAD, title, 14, 18, C["text"])
    if key in MUSIC_KEYS:                       # the workflow as a row of steps
        i = MUSIC_KEYS.index(key)
        sx = W - 160 - 8 * 15 - 14
        for j in range(len(MUSIC_KEYS)):
            on = j == i
            g.rect(sx + j * 15, 24, 11, 11 if on else 7, col if on else (C["hullhi"] if j < i else C["hull"]),
                   255)
            if on:
                g.rect(sx + j * 15, 37, 11, 2, col)
    chip(g, app, W - 150, 9)


# ---------------------------------------------------------------- footer
def footer(g, items, app=None, hints=True):
    """items: [(key spec, label)] - at most 4 are shown (the rest is in the SELECT help)"""
    app = app or APP
    y = H - FOOTER_H
    g.rect(0, y, W, FOOTER_H, C["deck"])
    g.rect(0, y, W, 2, C["hulllo"])
    right = W - 8
    if hints:
        music = app is not None and getattr(app, "cur_name", None) in MUSIC_KEYS + ["bridge", "hangar"]
        x2 = W - 8
        if music:
            x2 -= g.tw(SMALL, "música") + keys_w(g, "START") + 2
            xe = keys(g, "START", x2, y + 4)
            g.text(SMALL, "música", xe, y + 3, C["muted"])
            x2b = W - 8 - g.tw(SMALL, "ajuda") - keys_w(g, "SELECT") - 2
            xe = keys(g, "SELECT", x2b, y + 23)
            g.text(SMALL, "ajuda", xe, y + 22, C["muted"])
            right = min(x2, x2b) - 10
        else:
            x2 -= g.tw(SMALL, "ajuda") + keys_w(g, "SELECT") + 2
            xe = keys(g, "SELECT", x2, y + 13)
            g.text(SMALL, "ajuda", xe, y + 12, C["muted"])
            right = x2 - 10
    items = [(it[0], it[1]) for it in items if it[0]][:4]
    if not items:
        return
    widths = [keys_w(g, k) + 4 + g.tw(SMALL, v) for k, v in items]
    gap = max(10, min(28, (right - 12 - sum(widths)) // max(1, len(items))))
    x = 12
    for (k, v), wd in zip(items, widths):
        if x + wd > right:
            break
        xe = keys(g, k, x, y + 13)
        g.text(SMALL, v, xe + 2, y + 12, C["text"])
        x += wd + gap


# ---------------------------------------------------------------- toast
def notice(g, text, col=None):
    """small pill under the header (mission ticks)"""
    w = g.tw(SMALL, text) + 24
    x = W - w - 10
    box(g, x, HEADER_H + 4, w, 24, C["panel"], 245)
    outline(g, x, HEADER_H + 4, w, 24, col or C["green"], 2)
    g.text(SMALL, text, x + 12, HEADER_H + 5, col or C["green"])


def toast(g, text, col=None, y=None):
    w = g.tw(BODY, text) + 36
    y = y if y is not None else H - FOOTER_H - 56
    box(g, W // 2 - w // 2, y, w, 40, C["panel"], 245)
    outline(g, W // 2 - w // 2, y, w, 40, col or C["orange"], 2)
    g.text(BODY, text, W // 2, y + 5, col or C["text"], 255, "center")
