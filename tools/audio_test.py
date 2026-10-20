"""Audio thread: a sound source that raises is dropped and closed, the others keep playing bit for bit, and
log.txt gets one line per different error instead of one per callback.
  python3 tools/audio_test.py [APPDIR]"""
import os
import shutil
import struct
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ports", "mothership")
sys.path.insert(0, os.path.join(APPD, "lib"))
sys.path.insert(0, APPD)
import engine  # noqa: E402

LOG = os.path.join(APPD, "log.txt")
TMP = tempfile.mkdtemp()


def log_lines():
    try:
        return [l for l in open(LOG, errors="replace").read().splitlines() if l.startswith("audio:")]
    except IOError:
        return []


def wav_file(name, rate, ch, frames, cut=0):
    """a 16-bit PCM wav; cut > 0 removes bytes from the end of the data (a file cut short mid-sample)"""
    data = bytes(bytearray((i * 7) % 256 for i in range(frames * ch * 2)))
    data = data[:len(data) - cut]
    hdr = b"RIFF" + struct.pack("<I", 36 + frames * ch * 2) + b"WAVEfmt " + struct.pack(
        "<IHHIIHH", 16, 1, ch, rate, rate * ch * 2, ch * 2, 16) + b"data" + struct.pack("<I", frames * ch * 2)
    p = os.path.join(TMP, name)
    open(p, "wb").write(hdr + data)
    return p


class BadVoice(engine.Voice):
    def read(self, clock, n, warp):
        raise ValueError("broken voice")


class BadStream(object):
    group, done, start, closed = "floor", False, 0, False

    def read(self, n, clock=None):
        raise IOError("broken stream")

    def close(self):
        self.closed = True


def render(m, k=200):
    return b"".join(m.render(1024) for _ in range(k))


try:
    tone = bytes(bytearray((i * 13) % 256 for i in range(44100 * 4)))
    ref = engine.Mixer()
    ref.add(engine.Voice("good", "fx", tone, loop=True))
    expect = render(ref)

    lines0 = len(log_lines())
    m = engine.Mixer()
    m.add(engine.Voice("good", "fx", tone, loop=True))
    bad_v = BadVoice("bad", "fx", tone)
    m.add(bad_v)
    bad_s = BadStream()
    m.streams.append(bad_s)
    got = render(m)
    assert got == expect, "the good voice must play exactly as if the broken ones were not there"
    assert bad_v not in m.voices and bad_v.done and bad_s not in m.streams and bad_s.done and bad_s.closed
    assert len(log_lines()) - lines0 == 2, log_lines()[lines0:]
    for _ in range(3):                                 # the same errors again: no new lines in log.txt
        m.add(BadVoice("bad2", "fx", tone))
        m.streams.append(BadStream())
        render(m, 5)
    assert len(log_lines()) - lines0 == 2
    print("a broken voice and a broken stream are dropped, the rest plays bit for bit, each error logged once")

    # ---- real cases: a wav cut short mid-sample (not 44.1 kHz stereo) and a playlist whose next file is gone
    cut = engine.StreamVoice(wav_file("cut.wav", 22050, 1, 3000, cut=1))
    a, b = wav_file("a.wav", 44100, 2, 2000), wav_file("b.wav", 44100, 2, 2000)
    pl = engine.PlaylistVoice([a, b])
    os.remove(b if pl.cur_i == 0 else a)
    m = engine.Mixer()
    m.add(engine.Voice("good", "fx", tone, loop=True))
    m.streams += [cut, pl]
    got = render(m, 50)
    assert cut not in m.streams and pl not in m.streams and cut.done and pl.done
    k = 20 * 4096                                      # once both are gone: exactly the loop alone
    assert len(m.voices) == 1 and got[k:] == expect[k:len(got)]
    print("a wav cut short and a playlist with a missing file are dropped, the loop keeps playing")
    print("ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)
