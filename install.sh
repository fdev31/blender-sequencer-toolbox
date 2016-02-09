#!/bin/sh

x=$(blender -v)
BL_VER=${x:8:4}

OUT="~/.config/blender/$BL_VER/scripts/addons/"

mkdir -p "$OUT" 2>/dev/null
cp scripts/addons/*.py "$OUT"
