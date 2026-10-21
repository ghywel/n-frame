#!/bin/bash
# The ladder, build against build: the gate for an FFmpeg / libplacebo update (2026-10-21).
#
#   probes/build/buildgate.sh <outroot> <A>=<ffmpeg A> <B>=<ffmpeg B> <tag>=<shader.glsl> [<tag>=<shader.glsl> ...]
#   probes/build/buildtable.py <outroot> <A> <B> [tag ...]        (run at the end; can be re-run alone)
#
# gateset.sh gates shader VARIANTS on one build. This gates one BUILD against another with the shaders held fixed:
# every shader runs the whole ladder (bench.sh all) on each build, interleaved shader by shader (A then B), so drift
# over the hour lands on both sides alike. Each build has its own result tree, <outroot>/<A> and <outroot>/<B>, so
# hold and linear are rendered by that build too: linear is libplacebo's own mixer and may move with it, and hold is
# a check that FFmpeg's lavfi sources still render the scenes the same. mvk-env.sh is set by bench.sh.
# One GPU job at a time: run it alone. Prints DONE when the table is written.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS="$HERE/../.."
[ $# -ge 4 ] || { sed -n '3,5p' "$0"; exit 2; }
OUT="$1"; shift
A="${1%%=*}"; FA="${1#*=}"; shift
B="${1%%=*}"; FB="${1#*=}"; shift
for f in "$FA" "$FB"; do [ -x "$f" ] || { echo "not an executable ffmpeg: $f"; exit 2; }; done
mkdir -p "$OUT/$A" "$OUT/$B" || exit 2
tags=()
for spec in "$@"; do
  tag="${spec%%=*}"; sh="${spec#*=}"
  [ -f "$sh" ] || { echo "no shader: $sh"; exit 2; }
  sh="$(cd "$(dirname "$sh")" && pwd)/$(basename "$sh")"
  tags+=("$tag")
  for side in "$A=$FA" "$B=$FB"; do
    name="${side%%=*}"; ff="${side#*=}"
    echo "== $(date '+%H:%M:%S') $tag on $name"
    ( cd "$TESTS" && OUTROOT="$OUT/$name" FFMPEG="$ff" ./bench.sh all "$sh" "$tag" ) > "$OUT/$name/$tag.bench.log" 2>&1
    fails=$(grep -c "FAILED" "$OUT/$name/$tag.bench.log")
    echo "   done, $fails FAILED lines"
  done
done
"${PY:-python3}" "$HERE/buildtable.py" "$OUT" "$A" "$B" "${tags[@]}" | tee "$OUT/table.txt"
echo "DONE"
