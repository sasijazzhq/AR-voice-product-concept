#!/usr/bin/env bash
# Rebuild every deliverable from source. Requires Blender 4.2 LTS on PATH (or BLENDER=...), Python 3 + Pillow + segno, Node 20+.
set -euo pipefail
cd "$(dirname "$0")"
B=${BLENDER:-blender}
python3 scripts/make_textures.py
$B -b --factory-startup --python scripts/build_soundbox.py -- --lod hero --out paytm-soundbox-5.blend
$B -b --factory-startup --python scripts/build_soundbox.py -- --lod ar --out build/ar.blend
$B -b paytm-soundbox-5.blend --python scripts/export_glb.py -- --out build/hero_raw.glb
$B -b build/ar.blend --python scripts/export_glb.py -- --out ar_raw.glb
[ -d node_modules ] || npm ci
npm run -s postprocess:hero
npm run -s postprocess:ar
npm run -s validate
if [ "${RENDER:-0}" = "1" ]; then
  $B -b paytm-soundbox-5.blend --python scripts/render_views.py -- --views front,left,right,rear,top,threequarter,hero --samples 160 --outdir renders
fi
