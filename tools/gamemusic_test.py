"""The player's music everywhere (musiclib): the music folder and the console's menu music (bgmusic), game music
(one entry per track, titles and lengths from the file itself), a cache that never outgrows the card, and the
apps that use it - WARP FLOOR, TWIN DECKS, COMET CHOP, BEAT DUEL (with a chart made from the song) and VOID
RUNNER. The decoding itself needs ffmpeg with libgme: it is checked when there is one on the PATH.
  python3 tools/gamemusic_test.py"""
import gzip
import math
import os
import shutil
import struct
import sys
import tempfile
import time
import wave

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
SAVES = ("config.json", "pet.json", "vr_save.json", "bd_save.json", "log.txt")
BACK = {}
for f in SAVES:
    p = os.path.join(APPD, f)
    if os.path.exists(p):
        BACK[f] = open(p, "rb").read()
        os.remove(p)
import musiclib as M  # noqa: E402

TMP = tempfile.mkdtemp()
MUS, MENU = os.path.join(TMP, "music"), os.path.join(TMP, "bgmusic")
os.makedirs(MUS)
os.makedirs(MENU)
M.MUSIC_DIR, M.MENU_DIR = MUS, MENU
M.CACHE, M.CHARTS = os.path.join(MUS, ".cache"), os.path.join(MUS, ".charts")


# ---------------------------------------------------------------- tiny game-music files of our own
def nsf(path, freqs, name):
    code = bytes([0x4C, 0x06, 0x80, 0x60, 0, 0, 0xAA, 0xA9, 0x01, 0x8D, 0x15, 0x40, 0xA9, 0xBF, 0x8D, 0x00, 0x40,
                  0xA9, 0x08, 0x8D, 0x01, 0x40, 0xBD, 0x30, 0x80, 0x8D, 0x02, 0x40, 0xBD, 0x38, 0x80, 0x8D, 0x03,
                  0x40, 0x60]).ljust(0x30, b"\0")
    lo, hi = bytearray(8), bytearray(8)
    for i, f in enumerate(freqs):
        p = int(round(1789773 / (16.0 * f) - 1))
        lo[i], hi[i] = p & 0xFF, (p >> 8) & 7 | 0x08
    h = bytearray(0x80)
    h[0:5], h[5], h[6], h[7] = b"NESM\x1a", 1, len(freqs), 1
    struct.pack_into("<HHH", h, 8, 0x8000, 0x8000, 0x8003)
    h[0x0E:0x0E + len(name)] = name.encode()
    struct.pack_into("<HH", h, 0x6E, 16639, 0)
    open(path, "wb").write(bytes(h) + code + bytes(lo) + bytes(hi))


def vgm_bytes(notes, loop_from):
    clock, data, total = 3579545, bytearray(), 0
    loop_off = loop_start = 0
    for i, (freq, ms) in enumerate(notes):
        if i == loop_from:
            loop_off, loop_start = len(data), total
        n = int(round(clock / (32.0 * freq)))
        data += bytes([0x50, 0x80 | (n & 0xF), 0x50, (n >> 4) & 0x3F, 0x50, 0x90 | 2])
        w = int(44.1 * ms)
        total += w
        data += bytes([0x61]) + struct.pack("<H", w)
    data += b"\x66"
    s = "\0".join(["Teste", "", "Orimbux Chip", "", "Sega Master System", "", "Orimbux", "", "2026", "", ""]) + "\0"
    gd3 = b"Gd3 " + struct.pack("<II", 0x100, len(s.encode("utf-16-le"))) + s.encode("utf-16-le")
    h = bytearray(0x40)
    h[0:4] = b"Vgm "
    struct.pack_into("<IIII", h, 0x08, 0x150, clock, 0, 0x40 + len(data) - 0x14)
    struct.pack_into("<III", h, 0x18, total, 0x40 + loop_off - 0x1C, total - loop_start)
    struct.pack_into("<IHB", h, 0x24, 60, 9, 16)
    struct.pack_into("<I", h, 0x34, 0x0C)
    body = bytes(h) + bytes(data) + gd3
    return body[:4] + struct.pack("<I", len(body) - 4) + body[8:], total, total - loop_start


def spc(path, text_tag):
    d = bytearray(0x10200)
    d[0:33] = b"SNES-SPC700 Sound File Data v0.30"
    d[0x21:0x23], d[0x23] = b"\x1a\x1a", 26
    d[0x2E:0x2E + 10] = b"Boss Theme"
    d[0x4E:0x4E + 11] = b"Orimbux RPG"
    if text_tag:
        d[0xA9:0xAC], d[0xAC:0xB1] = b"090", b"05000"
    else:
        d[0xA9:0xAC] = (75).to_bytes(3, "little")
        d[0xAC:0xB0] = (4000).to_bytes(4, "little")
    open(path, "wb").write(bytes(d))


def chunk(cid, body):
    return struct.pack("<I", len(body)) + cid + body


def write_wav(path, frames, rate=22050, ch=1):
    w = wave.open(path, "wb")
    w.setnchannels(ch)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(frames)
    w.close()


def beats_wav(path, bpm=120, secs=24.0, rate=22050):
    """a click track: a short tone burst on every beat, louder on the bar"""
    out = bytearray()
    beat = 60.0 / bpm
    for i in range(int(secs * rate)):
        t = i / float(rate)
        k, ph = divmod(t, beat)
        a = (0.9 if int(k) % 4 == 0 else 0.5) * max(0.0, 1.0 - ph / 0.08) if ph < 0.08 else 0.0
        out += struct.pack("<h", int(a * 30000 * math.sin(2 * math.pi * 660 * t)))
    write_wav(path, bytes(out), rate)


def float_wav(path, secs=12.0, rate=22050, bpm=100):
    """a 32-bit float wav: the app's wav reader cannot read it, so it has to be decoded (ffmpeg)"""
    beat, out = 60.0 / bpm, bytearray()
    for i in range(int(secs * rate)):
        t = i / float(rate)
        ph = t % beat
        out += struct.pack("<f", 0.7 * math.sin(2 * math.pi * 440 * t) if ph < 0.08 else 0.0)
    fmt = struct.pack("<HHIIHH", 3, 1, rate, rate * 4, 4, 32)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(out)) + bytes(out)
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


def tone_freq(path, start=1.0, secs=0.5):
    w = wave.open(path, "rb")
    w.setpos(int(start * w.getframerate()))
    d = w.readframes(int(secs * w.getframerate()))
    sm = struct.unpack("<%dh" % (len(d) // 2), d)[::w.getnchannels()]
    cross = sum(1 for a, b in zip(sm, sm[1:]) if a < 0 <= b)
    return cross / secs


try:
    nsf(os.path.join(MUS, "jogo.nsf"), [440.0, 523.25, 659.25], "Orimbux NES")
    vg, total, loop = vgm_bytes([(440, 300), (554, 300), (659, 300), (880, 600)], 2)
    open(os.path.join(MENU, "chip.vgm"), "wb").write(vg)
    open(os.path.join(MUS, "chip2.vgz"), "wb").write(gzip.compress(vg))
    spc(os.path.join(MUS, "boss.spc"), True)
    spc(os.path.join(MUS, "boss_bin.spc"), False)
    gbs = bytearray(0x70)
    gbs[0:3], gbs[3], gbs[4], gbs[5] = b"GBS", 1, 2, 1
    gbs[0x10:0x10 + 9] = b"Pocket GB"
    open(os.path.join(MUS, "pocket.gbs"), "wb").write(bytes(gbs))
    info = struct.pack("<HHHBB", 0x8000, 0x8000, 0x8003, 0, 0) + bytes([2, 0])
    nsfe = b"NSFE" + chunk(b"INFO", info) + chunk(b"auth", b"Orimbux NSFE\0Me\0\0\0") + \
        chunk(b"tlbl", b"Intro\0Batalha\0") + chunk(b"time", struct.pack("<ii", 30000, -1)) + chunk(b"NEND", b"")
    open(os.path.join(MUS, "suite.nsfe"), "wb").write(nsfe)
    open(os.path.join(MUS, "atari.sap"), "wb").write(b'SAP\r\nNAME "Orimbux Atari"\r\nSONGS 2\r\nTYPE B\r\n'
                                                      b'TIME 01:30.000\r\nTIME 00:45.500 LOOP\r\n\xff\xff' + bytes(64))
    write_wav(os.path.join(MENU, "menu song.wav"), b"\0\0" * 2000)
    beats_wav(os.path.join(MENU, "batida.wav"))
    open(os.path.join(MUS, "leia.txt"), "w").write("not music")
    os.makedirs(os.path.join(MUS, ".cache"))
    write_wav(os.path.join(MUS, ".cache", "old.mp3.wav"), b"\0\0\0\0" * 10, 44100, 2)

    # ---- the library: both folders, one entry per game track, titles and lengths from the files
    ts = M.tracks()
    by = dict((t["title"], t) for t in ts)
    keys = [t["key"] for t in ts]
    assert len(keys) == len(set(keys)), keys
    assert not any(t["src"].endswith((".txt", "old.mp3.wav")) for t in ts)        # not music / the cache
    assert [t["title"] for t in ts if t["src"].endswith("jogo.nsf")] == ["Orimbux NES 01", "Orimbux NES 02",
                                                                          "Orimbux NES 03"]
    n3 = by["Orimbux NES 03"]
    assert n3["sub"] == 2 and n3["dur"] == M.DEFAULT_LEN and n3["fade"] and M.label(n3) == "A TUA MÚSICA · NES"
    assert os.path.basename(M.cache_path(n3)) == "jogo.nsf.t03.wav"
    assert M.chart_path(n3) == os.path.join(M.CHARTS, "jogo.nsf.t03.chart.json")
    v = by["Orimbux Chip - Teste"]
    assert v["tag"] == "MENU" and v["system"] == "SEGA MASTER SYSTEM" and v["fade"], v
    assert abs(v["dur"] - ((total + loop) / 44100.0 + M.FADE)) < 0.01, v["dur"]
    assert os.path.basename(M.cache_path(v)) == "menu__chip.vgm.wav" and M.chart_path(v).startswith(M.CHARTS)
    assert any(t["src"].endswith("chip2.vgz") and t["title"] == "Orimbux Chip - Teste" for t in ts)
    b = [t for t in ts if t["src"].endswith("boss.spc")][0]
    assert b["title"] == "Orimbux RPG - Boss Theme" and b["system"] == "SNES"
    assert abs(b["dur"] - (90 + 5 + M.FADE)) < 0.01, b["dur"]
    assert any(t["src"].endswith("boss_bin.spc") and abs(t["dur"] - (75 + 4 + M.FADE)) < 0.01 for t in ts)
    assert [t["title"] for t in ts if t["src"].endswith(".gbs")] == ["Pocket GB 01", "Pocket GB 02"]
    ne = [t for t in ts if t["src"].endswith(".nsfe")]
    assert [t["title"] for t in ne] == ["Orimbux NSFE 01 - Intro", "Orimbux NSFE 02 - Batalha"], ne
    assert abs(ne[0]["dur"] - (30 + M.FADE)) < 0.01 and ne[1]["dur"] == M.DEFAULT_LEN
    sap = [t for t in ts if t["src"].endswith(".sap")]
    assert len(sap) == 2 and sap[0]["title"] == "Orimbux Atari 01" and abs(sap[1]["dur"] - 50.5) < 0.01
    m = by["menu song"]
    assert m["kind"] == "wav" and M.label(m) == "MENU DA CONSOLA" and M.short(m) == "MENU"
    print("library: %d tracks from %d files" % (len(ts), len(set(t["src"] for t in ts))))

    # ---- the cache keeps the card's space: oldest first, never what was used in the last minute
    os.makedirs(M.CACHE, exist_ok=True)
    now = time.time()
    for i, age in enumerate((3600, 1800, 30)):
        p = os.path.join(M.CACHE, "c%d.wav" % i)
        open(p, "wb").write(b"\0" * 1000)
        os.utime(p, (now - age, now - age))
    keep_max, keep_res = M.MAX_CACHE, M.RESERVE
    M.MAX_CACHE, M.RESERVE = 3200, 0
    assert M.make_room(1000, now)                                       # 3084 + 1000 > 3200: only c0 goes
    assert not os.path.exists(os.path.join(M.CACHE, "c0.wav")) and os.path.exists(os.path.join(M.CACHE, "c1.wav"))
    assert not M.make_room(5000, now)                                   # c2 is fresh: it stays, it cannot fit
    assert os.path.exists(os.path.join(M.CACHE, "c2.wav"))
    M.MAX_CACHE, M.RESERVE = keep_max, keep_res
    for f in os.listdir(M.CACHE):
        os.remove(os.path.join(M.CACHE, f))
    print("cache: drops the oldest, keeps what was just used")

    def wait(keys, secs=120):
        t0 = time.time()
        while any(M.busy(k) for k in keys) and time.time() - t0 < secs:
            time.sleep(0.05)

    # ---- a PCM wav of any rate plays as it is: nothing decoded, nothing written to the card
    assert M.prepare(m["key"]) == m["src"] and M.ready_path(m["key"]) == m["src"]
    assert not os.listdir(M.CACHE)
    has_ffmpeg = bool(M.ffmpeg())
    if has_ffmpeg:
        M.prepare(n3["key"])
        M.prepare(v["key"])
        wait([n3["key"], v["key"]])
        assert not M.errors, M.errors
        f3 = tone_freq(M.ready_path(n3["key"]))
        assert abs(f3 - 659.25) < 15, f3                                 # track 3 of the NSF, not track 1
        w = wave.open(M.ready_path(v["key"]), "rb")
        secs = w.getnframes() / 44100.0
        w.setpos(int((secs - 0.4) * 44100))
        tail = w.readframes(int(0.3 * 44100))
        w.setpos(int(1.0 * 44100))
        head = w.readframes(int(0.3 * 44100))
        w.close()
        assert abs(secs - v["dur"]) < 0.1, (secs, v["dur"])               # cut, never looped forever
        assert M.engine.audioop.rms(tail, 2) < 0.2 * M.engine.audioop.rms(head, 2)   # faded out
        print("decoded with ffmpeg: NSF track 3 at %.0f Hz, the VGM loops once and fades (%.1f s)" % (f3, secs))
    else:
        M.prepare(n3["key"])
        wait([n3["key"]])
        assert "ffmpeg" in M.errors.get(n3["key"], ""), M.errors
        M.errors.clear()
        print("no ffmpeg here: game music says so instead of failing (decoding not checked)")

    # ---- the apps
    import app as appmod
    import beatduel
    a = appmod.App(headless=True)
    a.cfg["seen"] = list(__import__("help").HELP)
    while not a.bank.ready:
        time.sleep(0.02)
    warp = a.sections["warp"]
    a.go("warp")
    assert warp.title(n3["key"]) == "Orimbux NES 03" and m["key"] in warp.tracks
    i = warp.tracks.index(by["batida"]["key"])
    warp.start(i, 0.0)
    t0 = time.time()
    while warp.cur is None and time.time() - t0 < 30:
        warp.update(1 / 30.0)
        time.sleep(0.02)
    assert warp.cur is not None and warp.now_title() == "batida"         # it started by itself once decoded
    warp.stop()
    import decks
    lib = decks.library(a)
    tags = dict((it["title"], it["tag"]) for it in lib)
    assert tags["Orimbux NES 02"] == "NES" and tags["menu song"] == "MENU" and tags["Orimbux RPG - Boss Theme"] == "SNES"
    dk = a.sections["decks"]
    it = [x for x in lib if x["title"] == "menu song"][0]
    dk.load_item(dk.a, it)
    assert dk.a.title == "menu song"
    ch = a.sections["abductor"].chop                                     # COMET CHOP: the same library
    ch.open_browser()
    ch.bsel = [x["title"] for x in ch.lib].index("batida")
    ch.pick()
    t0 = time.time()
    while ch.loading and time.time() - t0 < 30:
        time.sleep(0.02)
    assert ch.title == "batida" and ch.frames > 44100 * 20, (ch.title, ch.frames)
    songs = beatduel.find_songs()
    bs = dict((s["title"], s) for s in songs)
    s = bs["BATIDA"]
    assert s["src"] == "MENU" and s["chart_path"].startswith(M.CHARTS) and not s["charts"]
    assert bs["ORIMBUX NES 01"]["system"] == "NES"
    bpm, charts = beatduel.auto_chart(s["wav"])
    assert abs(bpm - 120) <= 2, bpm
    ne, nn, nh = len(charts["easy"]), len(charts["normal"]), len(charts["hard"])
    assert 0 < ne <= nn <= nh, (ne, nn, nh)
    assert all(0 <= n[1] <= 3 for d in charts.values() for n in d)
    assert all(abs((n[0] - 0.0) / 0.5 - round(n[0] / 0.5)) < 0.2 for n in charts["hard"]), charts["hard"][:8]
    bd = a.sections["beatduel"]
    a.go("beatduel")
    bd.sel = [x["title"] for x in bd.songs].index("BATIDA")
    bd.on("press", "a")                                                   # no chart: it makes one, then plays
    t0 = time.time()
    while bd.state != "play" and time.time() - t0 < 30:
        bd.update(1 / 30.0)
        time.sleep(0.02)
    assert bd.state == "play" and bd.match is not None
    saved = M.engine.read_json(bd.songs[bd.sel]["chart_path"])
    assert saved["auto"] is True and saved["charts"]["hard"]
    bd.stop_all()
    bd.state = "select"
    bd.songs = beatduel.find_songs()
    assert [x for x in bd.songs if x["title"] == "BATIDA"][0].get("auto")
    print("beat duel: a chart from the song itself at %d BPM (%d / %d / %d notes)" % (bpm, ne, nn, nh))
    vr = a.sections["voidrunner"]
    a.go("voidrunner")
    vr.songs = vr.song_list()
    sg = [x for x in vr.songs if x["title"] == "BATIDA"][0]
    assert sg["tag"] == "MENU DA CONSOLA" and sg["key"] == by["batida"]["key"] and not sg["missing"]
    float_wav(os.path.join(MENU, "outra.wav"))                         # needs decoding: not ready yet
    vr.songs = vr.song_list()
    vr.sel = [x["title"] for x in vr.songs].index("OUTRA")
    assert vr.songs[vr.sel]["missing"]
    vr.on("press", "a")
    t0 = time.time()
    while vr.state == "menu" and vr.prep and time.time() - t0 < 30:
        vr.update(1 / 30.0)
        time.sleep(0.02)
    if has_ffmpeg:
        assert vr.state in ("scan", "run"), vr.state
        vr.drop_scan()
        vr.state = "menu"
        print("void runner: a song not decoded yet is decoded and its level starts")
    else:
        assert vr.state == "menu" and "ffmpeg" in vr.msg[0], vr.msg
        print("void runner: without ffmpeg it says so and stays in the menu")
    print("ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    for f in SAVES:
        p = os.path.join(APPD, f)
        try:
            os.remove(p)
        except OSError:
            pass
        if f in BACK:
            open(p, "wb").write(BACK[f])
