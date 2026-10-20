#!/bin/bash
# ORIMBUX MOTHERSHIP - launcher for ArkOS / dArkOS (R36S) and other Linux handhelds.
# Install/update: put this file + the "mothership" folder (or mothership*.zip packages) in the ports folder.
# mothership*.zip packages found here are unpacked on launch (your saves are kept) and then removed.
PORTDIR="$(cd "$(dirname "$0")" && pwd)"
GAMEDIR="$PORTDIR/mothership"

say() {
  for t in /dev/tty0 /dev/tty1; do
    printf "%s\n" "$1" > "$t" 2>/dev/null
  done
}
for t in /dev/tty0 /dev/tty1; do printf "\033c" > "$t" 2>/dev/null; done

if ! command -v python3 >/dev/null 2>&1; then
  mkdir -p "$GAMEDIR"
  echo "python3 nao encontrado" >> "$GAMEDIR/log.txt"
  say "ORIMBUX: python3 nao encontrado neste sistema."
  sleep 4
  exit 1
fi

# install/update packages: mothership.zip or mothership_1.zip, mothership_2.zip, ...
# Only what is inside mothership/ is unpacked, never the player's own files (saves, recordings, music...), and
# never a name with ".." or an absolute path: a zip made by hand from a PC copy cannot wipe the console's saves.
UNZIP='
import sys, zipfile
SAVES = {"config.json", "pet.json", "vr_save.json", "bd_save.json", "bd_scores.json", "forge.json", "earlab.json",
         "quiz.json", "missions.json", "log.txt"}
PLAYER_DIRS = {"recordings", "music", "samples", "forge", "chop", "vr_cache"}
z = zipfile.ZipFile(sys.argv[1])
for m in z.infolist():
    name = m.filename.replace("\\", "/")
    parts = name.split("/")
    if name.startswith("/") or ":" in parts[0] or ".." in parts or parts[0] != "mothership" or len(parts) < 2:
        continue
    top, last = parts[1], parts[-1]
    if (len(parts) == 2 and (top in SAVES or ".bad-" in top or top.endswith(".tmp"))) or \
            (top in PLAYER_DIRS and last != "LEIA-ME.txt"):
        continue
    z.extract(m, sys.argv[2])
'
set -- "$PORTDIR"/mothership*.zip
if [ -f "$1" ]; then
  say "ORIMBUX MOTHERSHIP"
  say "A instalar / atualizar... (pode demorar 1 minuto)"
  for Z in "$@"; do
    say "  $(basename "$Z")"
    if python3 -c "$UNZIP" "$Z" "$PORTDIR"; then
      rm -f "$Z"
    else
      say "Falhou: $(basename "$Z"). Copia esse ficheiro outra vez."
      sleep 5
      exit 1
    fi
  done
  # files from older versions that are no longer part of the app
  # v1.8: DEMO 64K -> TRAILER | v1.9: one font for everything (Tiny5), EAR LAB -> SOM DE OURO
  rm -f "$GAMEDIR/demo.py" "$GAMEDIR/__pycache__/demo."*
  rm -rf "$GAMEDIR/assets/demo"
  for F in p8 p16 p24 p40 v20 v28 v44 v76; do rm -f "$GAMEDIR/assets/fonts/$F.json" "$GAMEDIR/assets/fonts/$F.rgba"; done
  rm -f "$GAMEDIR/assets/fonts/pressstart2p-OFL.txt" "$GAMEDIR/assets/fonts/vt323-OFL.txt"
  rm -f "$GAMEDIR/assets/trailer/earlab.frm"
  sync
  say "Instalado."
fi

cd "$GAMEDIR" || exit 1
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8      # the UI uses Portuguese accents
: > "$GAMEDIR/log.txt"
python3 --version >> "$GAMEDIR/log.txt" 2>&1
python3 main.py >> "$GAMEDIR/log.txt" 2>&1
for t in /dev/tty0 /dev/tty1; do printf "\033c" > "$t" 2>/dev/null; done
