#!/bin/bash
# The sext's fit inputs, per pixel, for GPT's covariance check (2026-10-22; MATHS.md, "The smallest next export";
# CHAT-LEDGER.md G005, L003). What is exported and how to read it: export_links.py's docstring.
#
#   export_links.sh [outdir]     FFMPEG=, PY=, CASES= (default M2c_period40_v10 A4_accel_tex_a033 O9_osc_tex_fast),
#                                KEEP= the output frames kept (default 12 18 24 30 42 54)
#
# RUN-ON: the deterministic host (the NAS's Arc; the M5 does not repeat itself byte for byte), warmed.
# Exit 0 when every check holds (export_links.py pack: the calibration, the background, the channels' sanity, the
# estimator hashes, the repeat control); 1 on any ALARM or a refused render. N:N (24 -> 24, where the sext's
# diagnostic modes are anchored per phase), three seconds of source so every kept frame has its six-frame window.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
FFMPEG="${FFMPEG:-$HOME/np-build/ffmpeg/ffmpeg}"
PY="${PY:-$HOME/np-build/venv/bin/python3}"
OUT="${1:-$HOME/np-scratch-int/uncertainty/export_links}"
CASES="${CASES:-M2c_period40_v10 A4_accel_tex_a033 O9_osc_tex_fast}"
KEEP="${KEEP:-12 18 24 30 42 54}"
mkdir -p "$OUT/glsl" || exit 2
. "$REPO/tests/mvk-env.sh"
. "$REPO/tests/scenes.sh"
echo "########## EXPORT LINKS start $(date +%T)  out $OUT"
uname -sm > "$OUT/host.txt"; "$FFMPEG" -hide_banner -version | head -1 > "$OUT/ffmpeg.txt"
SH="$REPO/shaders/sextdirectional-interpolation-propagated.glsl"
shasum -a 256 "$SH" 2>/dev/null | cut -c1-64 > "$OUT/shader_sha256.txt" || sha256sum "$SH" | cut -c1-64 > "$OUT/shader_sha256.txt"
for m in $(seq 20 32); do
  "$PY" "$HERE/export_links.py" mk "$m" "$OUT/glsl/m$m.glsl" >/dev/null || { echo "variant m$m FAILED"; exit 1; }
done
"$PY" "$HERE/export_links.py" hashes "$OUT"/glsl/m*.glsl "$SH" > "$OUT/hashes.txt"; tail -1 "$OUT/hashes.txt"
grep -q IDENTICAL "$OUT/hashes.txt" || exit 1
SEL=$(for f in $KEEP; do printf 'eq(n\\,%s)+' "$f"; done); SEL="${SEL%+}"

render() {   # <case> <mode> [dst]: the kept frames, rgba64le in and out, rows 160..559
  local c="$1" m="$2" dst="${3:-$OUT/$1/m$2.raw}" S n
  S="$(scene "$c" 24)" || { echo "  unknown case $c"; return 1; }
  S="${S//:d=1,/:d=3,},format=rgba64le"
  "$FFMPEG" -nostdin -y -hide_banner -loglevel warning -init_hw_device vulkan=vk -filter_hw_device vk -f lavfi -i "$S" \
      -vf "libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=$OUT/glsl/m$m.glsl:format=rgba64le,select='$SEL',crop=1280:400:0:160" \
      -fps_mode passthrough -f rawvideo -pix_fmt rgba64le "$dst" 2> "${dst%.raw}.err"
  if grep -qiE "compile status|disabling|Failed to configure|Error reinitializing" "${dst%.raw}.err"; then
    echo "  $c m$m: REFUSED (the shader did not run):"; grep -iE "compile status|disabling|failed|error" "${dst%.raw}.err" | head -3
    rm -f "$dst"; return 1
  fi
  n=$(( $(wc -c < "$dst") / (1280 * 400 * 8) ))
  [ "$n" -eq "$(echo $KEEP | wc -w)" ] || { echo "  $c m$m: $n frames, want $(echo $KEEP | wc -w): REFUSED"; head -3 "${dst%.raw}.err"; return 1; }
}

echo "== $(date +%T) warm-up (REPAIRS L8: the first render of a fresh process may differ)"
mkdir -p "$OUT/warm"; render M2c_period40_v10 20 "$OUT/warm/w.raw" || exit 1
for c in $CASES; do
  mkdir -p "$OUT/$c"; echo $KEEP > "$OUT/$c/frames.txt"
  for m in $(seq 20 32); do render "$c" "$m" || exit 1; done
  echo "  $c: 13 modes, $(echo $KEEP | wc -w) frames each, $(date +%T)"
done
echo "== $(date +%T) the repeat control: link 23 (the next link) of the first case rendered again"
c1=${CASES%% *}
render "$c1" 23 "$OUT/warm/repeat.raw" || exit 1
if cmp -s "$OUT/warm/repeat.raw" "$OUT/$c1/m23.raw"; then echo "IDENTICAL ($c1 m23, rendered twice)" > "$OUT/repeat_control.txt"
else echo "DIFFERENT ($c1 m23, rendered twice)" > "$OUT/repeat_control.txt"; fi
cat "$OUT/repeat_control.txt"
# shellcheck disable=SC2086
"$PY" "$HERE/export_links.py" pack "$OUT" $CASES 2>&1 | tee "$OUT/pack.txt"
rc=${PIPESTATUS[0]}
echo "EXPORT LINKS DONE $(date +%T) (exit $rc)"
exit $rc
