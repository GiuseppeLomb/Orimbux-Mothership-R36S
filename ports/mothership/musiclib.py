# MUSICLIB - the player's own music for WARP FLOOR, TWIN DECKS, COMET CHOP, VOID RUNNER and BEAT DUEL.
# Two folders: ports/mothership/music and the console's menu music (ArkOS: /roms/bgmusic, what EmulationStation
# plays in its menus; read only, nothing is ever written there). Any common audio file, game music (SPC, NSF,
# VGM, GBS, HES, KSS, AY, SAP, GYM: one entry per track, titles from the file itself) and tracker modules.
# A PCM wav plays as it is (the players convert it on the fly); everything else is decoded on demand by the
# system's ffmpeg (ArkOS builds it with libgme and libopenmpt) into music/.cache, one file at a time, and that
# cache never grows past what the card can spare: the files used longest ago go first.
import gzip
import os
import shutil
import struct
import subprocess
import threading
import time
import wave

import engine

MUSIC_DIR = os.path.join(engine.APP, "music")
CACHE = os.path.join(MUSIC_DIR, ".cache")
CHARTS = os.path.join(MUSIC_DIR, ".charts")
MENU_DIR = os.path.normpath(os.path.join(engine.APP, "..", "..", "bgmusic"))
AUDIO = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".opus")
GAME = {".spc": "SNES", ".nsf": "NES", ".nsfe": "NES", ".vgm": "VGM", ".vgz": "VGM", ".gbs": "GAME BOY",
        ".gym": "MEGA DRIVE", ".hes": "PC ENGINE", ".kss": "MSX", ".ay": "ZX SPECTRUM", ".sap": "ATARI"}
TRACKER = (".mod", ".xm", ".s3m", ".it", ".mptm")
SOURCE_NAME = {"MUSICA": "A TUA MÚSICA", "MENU": "MENU DA CONSOLA"}
DEFAULT_LEN = 150.0           # a game track that loops forever: 2 min 30 s, like libgme's own default
FADE = 5.0                    # ... and then it fades out
MAX_LEN = 600.0               # nothing longer than 10 minutes is decoded
MAX_TRACKS = 64               # tracks listed per game-music file
RESERVE = 32 << 20            # the cache never leaves the card with less free space than this
MAX_CACHE = 512 << 20
CACHE_SR = 32000              # decoded copies at 32 kHz (the SNES's own rate): a quarter smaller than 44.1 kHz,
                              # and the players resample on the fly

_lock = threading.Lock()
_meta = {}                    # (path, size, mtime) -> header info, so a scan of the folders stays instant
_by_key = {}                  # key -> track (from the last scan)
_busy = set()                 # keys being decoded or waiting for it
_queue = []
_worker = None
errors = {}                   # key -> why it could not be decoded


class ConvError(Exception):
    """a reason to show the player, in plain words"""


def ffmpeg():
    return shutil.which("ffmpeg")


def log(msg):
    try:
        import io
        with io.open(os.path.join(engine.APP, "log.txt"), "a", encoding="utf-8", errors="replace") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def _txt(b):
    return b.split(b"\0")[0].decode("latin-1", "replace").strip()


def _u32(d, o):
    return struct.unpack("<I", d[o:o + 4])[0] if len(d) >= o + 4 else 0


# ---------------------------------------------------------------- what is inside a game-music file
def game_info(path):
    """{'system', 'game', 'n' tracks, 'titles' [..] or None, 'lens' [seconds or None] or None, 'loops' bool}
    from the file's own header (no decoder needed); None when the header is not one we know"""
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        d = f.read(1 << 20)
    if ext == ".vgz" or d[:2] == b"\x1f\x8b":
        try:
            d = gzip.decompress(d if len(d) < (1 << 20) else open(path, "rb").read())
        except Exception:
            return None
    info = {"system": GAME.get(ext, "JOGO"), "game": "", "n": 1, "titles": None, "lens": None, "loops": True}
    if d[:5] == b"NESM\x1a":
        info.update(n=max(1, d[6]), game=_txt(d[0x0E:0x2E]))
    elif d[:4] == b"NSFE":
        p, labels, lens = 4, None, None
        while p + 8 <= len(d):
            size, cid = _u32(d, p), d[p + 4:p + 8]
            body = d[p + 8:p + 8 + size]
            if cid == b"INFO" and len(body) >= 9:
                info["n"] = max(1, body[8])
            elif cid == b"auth":
                info["game"] = _txt(body)
            elif cid == b"tlbl":
                labels = [x.decode("latin-1", "replace").strip() for x in body.split(b"\0")]
            elif cid == b"time":
                lens = [struct.unpack("<i", body[i:i + 4])[0] for i in range(0, len(body) - 3, 4)]
            elif cid == b"NEND":
                break
            p += 8 + size
        if labels:
            info["titles"] = labels[:info["n"]]
        if lens:
            info["lens"] = [(v / 1000.0 if v > 0 else None) for v in lens[:info["n"]]]
    elif d[:3] == b"GBS":
        info.update(n=max(1, d[4]), game=_txt(d[0x10:0x30]))
    elif d[:27] == b"SNES-SPC700 Sound File Data":
        if len(d) > 0xB1 and d[0x23] == 26:
            info["titles"] = [_txt(d[0x2E:0x4E])]
            info["game"] = _txt(d[0x4E:0x6E])
            secs, fade = d[0xA9:0xAC], d[0xAC:0xB1]
            if all(c in b"0123456789\0 " for c in secs + fade) and any(48 <= c <= 57 for c in secs):
                s = int(_txt(secs) or 0)
                fd = int(_txt(fade) or 0)
            else:
                s = secs[0] | secs[1] << 8 | secs[2] << 16
                fd = _u32(d, 0xAC)
            if 0 < s < 3600:
                info["lens"] = [s + min(fd, 30000) / 1000.0]
    elif d[:4] == b"Vgm ":
        total, loop = _u32(d, 0x18), _u32(d, 0x20)
        if total:
            info["lens"] = [(total + loop) / 44100.0]
            info["loops"] = loop > 0
        g = _u32(d, 0x14)
        if g and d[0x14 + g:0x18 + g] == b"Gd3 ":
            s = d[0x14 + g + 12:0x14 + g + 12 + _u32(d, 0x14 + g + 8)].decode("utf-16-le", "replace").split("\0")
            if len(s) > 4:
                info["titles"] = [s[0].strip()]
                info["game"] = s[2].strip()
                info["system"] = s[4].strip().upper() or "VGM"
    elif d[:4] in (b"GYMX", b"GYM\x00") or ext == ".gym":
        if d[:4] == b"GYMX":
            info["titles"] = [_txt(d[0x04:0x24])]
            info["game"] = _txt(d[0x24:0x44])
    elif d[:3] == b"SAP":
        head = d.split(b"\xff\xff")[0].decode("latin-1", "replace")
        lens = []
        for line in head.splitlines():
            k, _, v = line.strip().partition(" ")
            if k == "SONGS" and v.strip().isdigit():
                info["n"] = max(1, int(v))
            elif k == "NAME":
                info["game"] = v.strip().strip('"')
            elif k == "TIME":
                try:
                    mm, ss = v.split()[0].split(":")
                    lens.append(int(mm) * 60 + float(ss))
                except Exception:
                    lens.append(None)
        if lens:
            info["lens"] = lens
    elif ext in (".hes", ".kss", ".ay"):
        info["n"] = _probe_tracks(path)
    else:
        return None
    info["n"] = min(info["n"], MAX_TRACKS)
    return info


def _probe_tracks(path):
    """the formats without a track count in their header: ask ffprobe (libgme knows)"""
    tool = shutil.which("ffprobe")
    if not tool:
        return 1
    try:
        out = subprocess.check_output([tool, "-v", "error", "-show_entries", "format_tags=tracks", "-of",
                                       "default=nw=1:nk=1", path], timeout=10)
        return max(1, min(MAX_TRACKS, int(out.strip() or 1)))
    except Exception:
        return 1


# ---------------------------------------------------------------- the library
def sources():
    return [(MUSIC_DIR, "MUSICA"), (MENU_DIR, "MENU")]


def _entries(path, tag):
    low = path.lower()
    name = os.path.splitext(os.path.basename(path))[0]
    ext = os.path.splitext(low)[1]
    base = {"src": path, "sub": None, "tag": tag, "system": None, "dur": None, "fade": False}
    if ext in AUDIO:
        return [dict(base, key=path, title=name, kind="wav" if ext == ".wav" else "audio")]
    if ext in TRACKER:
        return [dict(base, key=path, title=name, kind="tracker", system="TRACKER")]
    if ext not in GAME:
        return []
    try:
        st = os.stat(path)
        mk = (path, st.st_size, int(st.st_mtime))
        info = _meta.get(mk)
        if info is None:
            info = _meta[mk] = game_info(path) or {"system": GAME[ext], "game": "", "n": 1, "titles": None,
                                                   "lens": None, "loops": True}
    except OSError:
        return []
    out = []
    n = info["n"]
    game = info["game"] or name
    for i in range(n):
        title = (info["titles"][i] if info["titles"] and i < len(info["titles"]) else "") or ""
        if n == 1:
            full = ("%s - %s" % (game, title)) if title and title != game else (title or game)
        else:
            full = "%s %02d%s" % (game, i + 1, (" - " + title) if title else "")
        ln = info["lens"][i] if info["lens"] and i < len(info["lens"]) else None
        dur = min(MAX_LEN, ln + (FADE if info["loops"] else 0.5)) if ln else DEFAULT_LEN
        out.append(dict(base, key=path if n == 1 else "%s#%d" % (path, i), sub=i, title=full, kind="game",
                        system=info["system"], dur=dur, fade=(not ln) or info["loops"]))
    return out


def tracks():
    """every song in the two folders, music folder first; game files give one entry per track"""
    out = []
    for d, tag in sources():
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = sorted(x for x in dirs if not x.startswith("."))
            for f in sorted(files):
                if not f.startswith("."):
                    out.extend(_entries(os.path.join(root, f), tag))
    with _lock:
        _by_key.clear()
        for t in out:
            _by_key[t["key"]] = t
    return out


def get(key):
    with _lock:
        return _by_key.get(key)


def label(t):
    """where it comes from, in plain words: A TUA MÚSICA · SNES"""
    s = SOURCE_NAME.get(t["tag"], t["tag"])
    return s + (" · " + t["system"] if t.get("system") else "")


def short(t):
    """a few letters for tight lists: MUSICA, MENU, SNES, NES, TRACKER..."""
    return (t.get("system") or ("MENU" if t["tag"] == "MENU" else "MUSICA"))[:12]


def cache_path(t):
    base = os.path.basename(t["src"])
    if t["tag"] != "MUSICA":
        base = t["tag"].lower() + "__" + base
    if t["sub"] is not None and t["key"] != t["src"]:
        base += ".t%02d" % (t["sub"] + 1)
    return os.path.join(CACHE, base + ".wav")


def chart_path(t):
    """Beat Duel's chart: next to a song of the music folder (as always); the console's menu music and game
    tracks keep theirs in music/.charts, so nothing is written outside the app's folders"""
    if t["tag"] == "MUSICA" and t["key"] == t["src"]:
        return t["src"] + ".chart.json"
    return os.path.join(CHARTS, os.path.basename(cache_path(t))[:-4] + ".chart.json")


def _pcm_wav(path):
    """a wav the players read as it is (any PCM: mono/stereo, 8-32 bit, any rate: they convert on the fly)"""
    try:
        w = wave.open(path, "rb")
        try:
            return w.getnchannels() in (1, 2) and w.getsampwidth() in (1, 2, 3, 4) and w.getnframes() > 0
        finally:
            w.close()
    except Exception:
        return False


def wav_for(t):
    """the wav that plays this track: the file itself or its decoded copy (it may not exist yet)"""
    if t["kind"] == "wav" and _pcm_wav(t["src"]):
        return t["src"]
    return cache_path(t)


def ready_path(key_or_track):
    """the playable wav of a track when it is ready (and marks it as just used), else None"""
    t = key_or_track if isinstance(key_or_track, dict) else get(key_or_track)
    if t is None:
        return None
    p = wav_for(t)
    if os.path.exists(p):
        if p != t["src"]:
            try:
                os.utime(p, None)              # the cache drops what was used longest ago: this was used now
            except OSError:
                pass
        return p
    return None


def busy(key):
    with _lock:
        return key in _busy


def prepare(key_or_track):
    """make sure the track can be played: returns its wav at once if it is ready, else starts decoding it in the
    background (one at a time) and returns None"""
    t = key_or_track if isinstance(key_or_track, dict) else get(key_or_track)
    if t is None:
        return None
    p = ready_path(t)
    if p:
        return p
    global _worker
    with _lock:
        _by_key.setdefault(t["key"], t)
        errors.pop(t["key"], None)
        if t["key"] not in _busy:
            _busy.add(t["key"])
            _queue.append(t)
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_work, daemon=True)
            _worker.start()
    return None


def _work():
    while True:
        with _lock:
            if not _queue:
                return
            t = _queue.pop(0)
        try:
            _convert(t)
        except Exception as e:
            if isinstance(e, ConvError):
                why = str(e)
            elif getattr(e, "errno", None) == 28:
                why = "pouco espaço no cartão para esta música"
            elif isinstance(e, subprocess.TimeoutExpired):
                why = "demorou demasiado a ler"
            else:
                why = "não consegui ler este ficheiro"
            with _lock:
                errors[t["key"]] = why
            log("music %s: %r" % (os.path.basename(t["src"]), e))
        with _lock:
            _busy.discard(t["key"])


# ---------------------------------------------------------------- the cache
def cache_files():
    out = []
    try:
        for f in os.listdir(CACHE):
            if f.endswith(".wav"):
                p = os.path.join(CACHE, f)
                st = os.stat(p)
                out.append((st.st_mtime, st.st_size, p))
    except OSError:
        pass
    return sorted(out)


def _open_files():
    """the files this app has open (Linux: /proc). Deleting one would not free its space until it is closed"""
    out = set()
    try:
        for fd in os.listdir("/proc/self/fd"):
            try:
                out.add(os.path.realpath(os.readlink("/proc/self/fd/" + fd)))
            except OSError:
                pass
    except OSError:
        pass
    return out


def make_room(need, now=None):
    """drop cached songs, used longest ago first, until `need` more bytes fit: the cache stays under MAX_CACHE
    and the card keeps RESERVE bytes free. Only a song being played (an open file) or one decoded in the last
    15 seconds stays. Returns how many bytes are still missing (0: it fits)."""
    now = time.time() if now is None else now
    try:
        for f in os.listdir(CACHE):                  # a decode cut short (the console switched off) left this
            p = os.path.join(CACHE, f)
            if f.endswith(".part") and now - os.path.getmtime(p) > 3600:
                os.remove(p)
    except OSError:
        pass
    files = cache_files()
    used = sum(s for _, s, _ in files)
    try:
        free = shutil.disk_usage(MUSIC_DIR).free
    except OSError:
        free = 1 << 40
    room = free - RESERVE                            # what can be written now
    opened = _open_files()
    for mt, size, p in files:
        if need <= room and used + need <= MAX_CACHE:
            break
        if now - mt < 15 or os.path.realpath(p) in opened:
            continue
        try:
            os.remove(p)                             # (Windows refuses an open file: it simply stays)
            used -= size
            room += size
        except OSError:
            pass
    return max(0, need - room, used + need - MAX_CACHE)


def _need(t):
    if t["dur"]:
        return int(t["dur"] * CACHE_SR * 4) + 4096
    tool = shutil.which("ffprobe")
    if tool:
        try:
            out = subprocess.check_output([tool, "-v", "error", "-show_entries", "format=duration", "-of",
                                           "default=nw=1:nk=1", t["src"]], timeout=10)
            return int(min(MAX_LEN, float(out.strip())) * CACHE_SR * 4) + 4096
        except Exception:
            pass
    return min(int(MAX_LEN * CACHE_SR * 4), os.path.getsize(t["src"]) * 9)


def _convert(t):
    dst = cache_path(t)
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    short = make_room(_need(t))
    if short:
        raise ConvError("cartão cheio: faltam %d MB para esta música" % (short // (1 << 20) + 1))
    part = dst + ".part"
    try:
        tool = ffmpeg()
        if not tool and t["src"].lower().endswith(".mp3") and shutil.which("mpg123"):
            subprocess.check_call([shutil.which("mpg123"), "-q", "-r", str(CACHE_SR), "--stereo", "-w", part,
                                   t["src"]], timeout=900)
        elif not tool:
            raise ConvError("precisa do ffmpeg (não está instalado)")
        else:
            cmd = [tool, "-nostdin", "-v", "error", "-y"]
            if t["kind"] == "game":
                cmd += ["-track_index", str(t["sub"] or 0)]
            cmd += ["-i", t["src"], "-t", "%.2f" % (t["dur"] or MAX_LEN)]
            if t["kind"] == "game" and t["fade"]:
                cmd += ["-af", "afade=t=out:st=%.2f:d=%.2f" % (max(0.0, t["dur"] - FADE), FADE)]
            cmd += ["-ar", str(CACHE_SR), "-ac", "2", "-sample_fmt", "s16", "-f", "wav", part]
            subprocess.check_call(cmd, timeout=900)
        if not _pcm_wav(part):
            raise ConvError("o ficheiro não tem som que se possa ler")
        os.replace(part, dst)
    finally:
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
