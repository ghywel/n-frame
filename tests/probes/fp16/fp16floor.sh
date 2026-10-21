#!/bin/bash
# The fp16 readback floor, MEASURED on a known constant (REPAIRS.md L10's cheap step; swarm 2026-10-21, lane instruments).
#
#   fp16floor.sh [outdir]          FFMPEG= picks the build (default ffmpeg on PATH); PY= the numpy python
#                                  (default $HOME/np-build/venv/bin/python3); REPO= the checkout (default
#                                  ~/Developer/n-frame; only its tests/mvk-env.sh is used); DITHER=none|ordered_fixed
#                                  adds libplacebo's dithering option (default unset: the path loop.sh/fieldtier.sh use)
#   Exit 0 on PASS, 1 otherwise. One GPU job; about ten seconds. Decoder: fp16floor_decode.py beside this file.
#
# WHAT IT ISOLATES. The reading tail's machine modes return 0.5 + f * (0.5 / FS) (tests/add_human_reading.py L427-430,
# FS 32 for velocity). L10 says the hook's output passes an fp16 stage, so near 0.5 the step is 1/2048 and f is read to
# 1/32 px. The mathematics lane found a second stage one hop earlier (FLOW_H_AB itself rounded to 1/64-1/32 px). This
# probe exercises ONLY the output stage: a tiny hook paints a CONSTANT it computes itself (no estimate, no flow
# texture), so whatever quantisation the decode shows is the readback's and nothing else's.
#
# HOW. One hook shader, 32 bands of 16 columns on a 512x8 source, as probes/window/window_live.sh does for timestamps.
# Band j: set s = j / 16, k = j mod 16, the constant f = (s == 0 ? 4.0 : 5.9) + k / 128 px. Set A is the brief's
# (4 + k/128); set B puts the two-channel fraction near the top of its channel (fract(f/2) from 0.95) and crosses a
# whole-part boundary at k = 13, so the wrap is tested in the same run. Each band's texel carries both encodings:
#   R = 0.5 + f * (0.5 / 32)                                      the existing read_view 4 encoding (single channel)
#   G = fract(f / 2)                                              the two-channel fraction, in 2-px units
#   B = ((floor(f / 2) + 16) * 32 + (floor(0 / 2) + 16)) / 1024   the packed whole parts (x, and y = 0), exact in fp16
# rgb48le is chosen INSIDE the filter (format=rgb48le on libplacebo), never by -pix_fmt on the output (fieldcheck.py's
# READ PATH BROKEN check: an 8-bit or limited-range intermediate shifts the zero level; the decoder refuses levels that
# are all multiples of 257). Three steady-state frames at 24 -> 24 are decoded at row 4, the centre column of each band.
# The hook binds HOOKED and FRAME1 as window_live.sh's smallest window does; [U] whether HOOKED alone would run.
#
# PREDICTION (written before any run). Single channel: every reading sits on the 1/32 px grid (residual under 0.004 px,
# four 16-bit levels) and at most 5 distinct grid points per set of 16 inputs spaced 1/128 px. Two-channel: all 32
# readings within 1/1024 px of their constants, hence 32 distinct, the k = 13..15 wrap of set B included.
# KILL. 16 distinct single-channel readings within 1/1000 px of their constants kills L10 for the output stage (the fp16
# is elsewhere). Two-channel readings off by more than 1/1024 px, or a wrong whole part at the wrap, kills the
# read_view 10 design in readview10.md as written. INCONCLUSIVE tips: readings quantised but not on the 1/32 grid
# (another format than fp16) means L10's number is wrong and its mechanism right; rerun with DITHER=none first.
# CALIBRATED CPU-ONLY (2026-10-21): fp16floor_sim.py fabricates the raw under fp16 rounding (decoder says PASS) and
# under fp32 (decoder says KILL); the GPU path itself has not been run.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FFMPEG="${FFMPEG:-ffmpeg}"
PY="${PY:-$HOME/np-build/venv/bin/python3}"
OUT="${1:-${NP_SCRATCH:-$HOME/Developer/np-scratch}/fp16floor/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT" || { echo "cannot make $OUT"; exit 2; }
REPO="${REPO:-$HOME/Developer/n-frame}"
[ -f "$REPO/tests/mvk-env.sh" ] && . "$REPO/tests/mvk-env.sh"     # MoltenVK determinism on macOS, as every harness does
DOPT="${DITHER:+:dithering=$DITHER}"

cat > "$OUT/fp16floor.glsl" <<'GLSL'
//!HOOK FRAME_MIX
//!BIND HOOKED
//!BIND FRAME1
//!DESC [probe] fp16floor: a known constant through the read_view 4 encoding and a split encoding, 32 bands

vec4 hook() {
    int j = int(HOOKED_pos.x * 32.0);
    int s = j / 16;
    int k = j - 16 * s;
    float f = (s == 0 ? 4.0 : 5.9) + float(k) / 128.0;        // px, the constant under test
    float r_single = 0.5 + f * (0.5 / 32.0);                 // add_human_reading.py L430 with FS 32
    float h = f * 0.5;                                       // 2-px units
    float w = floor(h);
    float packed = ((w + 16.0) * 32.0 + (0.0 + 16.0)) / 1024.0;   // y = 0: whole part 0 -> slot 16
    return vec4(r_single, fract(h), packed, 1.0);
}
GLSL

( cd "$OUT" && "$FFMPEG" -y -hide_banner -loglevel error -init_hw_device vulkan=vk -filter_hw_device vk \
    -f lavfi -i "testsrc2=s=512x8:r=24:d=2" \
    -vf "libplacebo=fps=24:frame_mixer=custom_n:custom_shader_path=fp16floor.glsl:format=rgb48le${DOPT},select='between(n\,10\,12)'" \
    -fps_mode passthrough -f rawvideo -pix_fmt rgb48le out.raw ) 2> "$OUT/render.err"
if grep -q "compile status .error" "$OUT/render.err" || [ ! -s "$OUT/out.raw" ]; then
  echo "render FAILED (see $OUT/render.err); a compile error means libplacebo used its own mixer"; exit 1
fi
echo "rendered $OUT/out.raw ($(wc -c < "$OUT/out.raw") bytes; 3 frames expected = 73728)"
"$PY" -I "$HERE/fp16floor_decode.py" "$OUT/out.raw" | tee "$OUT/fp16floor.txt"
exit "${PIPESTATUS[0]}"
