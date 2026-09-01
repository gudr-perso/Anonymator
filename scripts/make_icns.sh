#!/usr/bin/env bash
# scripts/make_icns.sh
# Genere anonymator/ui/assets/anonymator.icns depuis picto.png.
#
# Equivalent macOS de scripts/make_ico.py : PyInstaller refuse un .ico comme
# icone de bundle .app. On ne versionne pas le .icns (cf. .gitignore), il est
# regenere a chaque build par scripts/build.sh.
#
# sips et iconutil sont fournis par macOS : aucune dependance a installer
# (contrairement a make_ico.py, qui a besoin de Pillow).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/anonymator/ui/assets/picto.png"
dst="$root/anonymator/ui/assets/anonymator.icns"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "make_icns.sh : macOS uniquement (sips/iconutil absents ici)." >&2
    exit 1
fi
[[ -f "$src" ]] || { echo "Source introuvable : $src" >&2; exit 1; }

iconset="$(mktemp -d)/anonymator.iconset"
mkdir -p "$iconset"
trap 'rm -rf "$(dirname "$iconset")"' EXIT

# picto.png fait 512x512 : on genere toutes les tailles jusqu'a 512, y compris
# les variantes @2x qui tiennent dans la source. Le slot 512x512@2x (1024 px)
# est volontairement omis plutot que d'y mettre un upscale flou — macOS se
# rabat alors sur le 512.
for spec in "16 icon_16x16" \
            "32 icon_16x16@2x" \
            "32 icon_32x32" \
            "64 icon_32x32@2x" \
            "128 icon_128x128" \
            "256 icon_128x128@2x" \
            "256 icon_256x256" \
            "512 icon_256x256@2x" \
            "512 icon_512x512"; do
    size="${spec%% *}"
    name="${spec#* }"
    sips -z "$size" "$size" "$src" --out "$iconset/$name.png" >/dev/null
done

iconutil --convert icns "$iconset" --output "$dst"
echo "Genere : $dst"
