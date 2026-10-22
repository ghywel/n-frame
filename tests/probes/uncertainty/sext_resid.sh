#!/bin/bash
# DOES THE SEXT'S LEAST-SQUARES RESIDUAL PREDICT ITS FIELD'S ERROR? (2026-10-22; step 2 of
# swarm/2026-10-21/uncertainty.md section 5, "the free confidence map measured".)
#
#   sext_resid.sh [outdir]      default ~/np-scratch-int/uncertainty/sext_resid; FFMPEG= (default the research
#                               build $HOME/np-build/ffmpeg/ffmpeg), PY= (default $HOME/np-build/venv/bin/python3),
#                               CASES= to override the list, FRAMES= (default 60), RERENDER=1 to render again.
#   Exit 0 when every instrument check holds, 1 on any ALARM. One GPU job at a time, about 22 renders of 60 frames.
#
# WHY. The sext fits one quartic trajectory through five composed links and keeps the leftover (TRI_DIAG 6), the
# only per-texel confidence any shader in the family already computes. If it ranks texels by their error against
# exact truth, the uncertainty map has a free noise channel in the sext; if not, the map must be built from the
# other cues (uncertainty.md section 2). The scorer's docstring (sext_resid.py) says what is computed and how.
#
# WHAT IS RENDERED. Five diagnostic variants of the sext, each a copy with its substitutions asserted:
#   m10  the fit's velocity at the anchor (the field the residual belongs to; no shipped mode returns it)
#   m11  the residual as mode 6 computes it, the residual in true px, and the fit's state (links, fitted)
#   m12  f_fwd, the straddle flow the warp uses (mode 7's field), split-encoded like m10
#   m6   the shipped mode 6 at RESID_DIAG_FS 64 (nothing clips)      } identity checks of m11 and m12, and of
#   m7   the shipped mode 7 at VEL_DIAG_FS 32 (0.5 + v/64)            } the read path (0.5 off the object)
# on the textured O-family (O5, O6, O9, O10: a 300x300 TEX_M2 square at y 210, x oscillating), the zero-jerk
# scene A4_accel_tex_a033 (TEX_M2, constant acceleration 1/3 px/frame^2, v -4 -> +18 over three seconds), and the
# calibration M2c_period40_v10 (TEX_M2, rigid translation at 10 px/frame), all at 24 -> 24 (N:N, where the
# diagnostic modes are anchored per phase), three seconds of source so 60 output frames have their window.
#
# TRAPS HANDLED. The scene is converted to RGB before libplacebo and the field is read through format=rgb48le
# INSIDE the graph, written as rawvideo (never -pix_fmt rgb48le on the output alone). Rows 160-559 are kept (crop
# after the read: lossless). A compile error makes libplacebo use its own mixer silently: stderr is kept at warning
# level and a "compile status" or "disabling" line refuses the render. The calibration case must read its 10 px
# to 0.01 px and the far background zero before any science line is quoted (the scorer prints ALARM otherwise).
#
# HOW TO READ. sext_resid.txt in the outdir: per case the ALIGN, ZERO, CAL and identity lines, then per field
# (fit, fwd) and region (interior, edge, near) the statistics, with the permuted residual under each interior row,
# then the pooled block and the VERDICT line. KILL: pooled interior decile-bin Spearman < 0.5.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
FFMPEG="${FFMPEG:-$HOME/np-build/ffmpeg/ffmpeg}"
PY="${PY:-$HOME/np-build/venv/bin/python3}"
OUT="${1:-$HOME/np-scratch-int/uncertainty/sext_resid}"
FRAMES="${FRAMES:-60}"
CASES="${CASES:-M2c_period40_v10 O5_osc_textured O6_osc_tex_gentle O9_osc_tex_fast O10_osc_tex_tiny A4_accel_tex_a033}"
IDENT="${IDENT:-M2c_period40_v10 O5_osc_textured}"     # the cases that also get the shipped modes 6 and 7
mkdir -p "$OUT/glsl" || exit 2
. "$REPO/tests/mvk-env.sh"
. "$REPO/tests/scenes.sh"
echo "########## SEXT RESIDUAL start $(date +%T)  repo $REPO  out $OUT"

for m in 6 7 10 11 12; do
  "$PY" "$HERE/sext_resid.py" mk "$m" "$OUT/glsl/m$m.glsl" || { echo "variant m$m FAILED"; exit 1; }
done

render() {  # <case> <mode>
  local c="$1" m="$2" S
  local dst="$OUT/$c/m$m.raw" err="$OUT/$c/m$m.err"
  [ -s "$dst" ] && [ "${RERENDER:-0}" != 1 ] && return 0
  S="$(scene "$c" 24)" || { echo "  unknown case $c"; return 1; }
  S="${S//:d=1,/:d=3,},format=rgb48le"
  "$FFMPEG" -y -hide_banner -loglevel warning -init_hw_device vulkan=vk -filter_hw_device vk -f lavfi -i "$S" \
      -vf "libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=$OUT/glsl/m$m.glsl,format=rgb48le,crop=1280:400:0:160" \
      -frames:v "$FRAMES" -f rawvideo "$dst" 2> "$err"
  if grep -qiE "compile status|disabling" "$err"; then
    echo "  $c m$m: SHADER REJECTED (libplacebo fell back to its own mixer):"; grep -iE "compile status|disabling|error" "$err" | head -3
    rm -f "$dst"; return 1
  fi
  local n=$(( $(wc -c < "$dst") / (1280 * 400 * 6) ))
  [ "$n" -ge "$FRAMES" ] || { echo "  $c m$m SHORT ($n frames)"; head -3 "$err"; return 1; }
  echo "  $c m$m: $n frames $(date +%T)"
}

for c in $CASES; do
  mkdir -p "$OUT/$c"
  for m in 10 11 12; do render "$c" "$m" || exit 1; done
  case " $IDENT " in *" $c "*) render "$c" 6 || exit 1; render "$c" 7 || exit 1 ;; esac
done

# shellcheck disable=SC2086
"$PY" "$HERE/sext_resid.py" score "$OUT" $CASES 2>&1 | tee "$OUT/sext_resid.txt"
rc=${PIPESTATUS[0]}
echo "SEXT RESIDUAL DONE $(date +%T) (exit $rc)"
exit "$rc"
