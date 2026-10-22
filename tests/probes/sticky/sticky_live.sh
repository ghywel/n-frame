#!/bin/bash
# The patch's //!WHEN pair_changed and //!STICKY, proven on a live build (2026-10-22).
#
#   probes/sticky/sticky_live.sh [outdir]          FFMPEG= picks the build
#
# What the patch adds (frame-mix-hook.patch, custom_mpv.c): `pair_changed` as a //!WHEN variable in the FRAME_MIX stage,
# and //!STICKY, under which a pass renders into a texture of its own and, when its //!WHEN is false, offers that
# texture again under its //!SAVE name. The use: a pass whose work depends only on the window of source frames (every
# pass that begins `if (!pair_changed) return imageLoad(cache)`) can be skipped on the outputs that reuse the window
# (60% of them at 24 -> 60), and the passes reading its result still find it, unchanged. The claim is byte identity.
#
# Three checks in one run, 24 -> 60 on a moving test pattern, framemd5 of every output:
#   (a) MUST MATCH: a two-pass hook, the first pass `//!WHEN pair_changed` + `//!STICKY` (it reads the two frames and
#       saves them), the second every output (it mixes the saved pair by mix_t), against the same hook with neither
#       directive. Identical frames, or the sticky texture is not what the pass would have made.
#   (b) MUST DIFFER: the same skip WITHOUT //!STICKY. The second pass then finds no texture on the skipped outputs and
#       libplacebo skips it too, so the output changes: the counterfactual that shows the sticky part carries the value.
#   (c) THE SKIP HAPPENS: the first pass also writes `frame` (libplacebo's frame counter) into a channel the second pass
#       passes through; with the skip, the counter must stay frozen across the outputs that share a window, and advance
#       on the outputs where the window changes. Read back as numbers.
# Exit 0 when (a) matches, (b) differs and (c) shows frozen counters on at least half the outputs; 1 otherwise.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FFMPEG="${FFMPEG:-ffmpeg}"
PY="${PY:-python3}"
OUT="${1:-${NP_SCRATCH:-$HOME/Developer/np-scratch}/sticky-live/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT" || exit 2
. "$HERE/../../mvk-env.sh"

hook() {   # hook <when+sticky lines> <frame?>  -> the shader text
  # No blank line may sit inside a pass's header: libplacebo ends the header there, the rest becomes the body, the
  # shader fails to compile and libplacebo silently mixes with its own mixer (the first run of this probe, 2026-10-22).
  { echo "//!HOOK FRAME_MIX"; echo "//!BIND HOOKED"; echo "//!BIND NEXT"; [ -n "$1" ] && printf '%s\n' "$1"
  cat <<EOF
//!SAVE PAIRVAL
//!COMPONENTS 4
//!DESC [probe] the pair's two frames, saved
vec4 hook() {
    return vec4(HOOKED_tex(HOOKED_pos).r, NEXT_tex(NEXT_pos).r, $2, 1.0);
}

//!HOOK FRAME_MIX
//!BIND PAIRVAL
//!DESC [probe] every output: the saved pair mixed by mix_t
vec4 hook() {
    vec4 v = PAIRVAL_tex(PAIRVAL_pos);
    return vec4(mix(v.r, v.g, mix_t), v.b, 0.0, 1.0);
}
EOF
  }
}
hook "" "0.0" > "$OUT/plain.glsl"
hook "$(printf '//!WHEN pair_changed\n//!STICKY')" "0.0" > "$OUT/sticky.glsl"
hook "//!WHEN pair_changed" "0.0" > "$OUT/skiponly.glsl"
hook "$(printf '//!WHEN pair_changed\n//!STICKY')" "fract(float(frame) / 256.0)" > "$OUT/counter.glsl"

SRC="testsrc2=s=320x180:r=24:d=4"
md5() {   # md5 <shader> -> one hash per output frame
  ( cd "$OUT" && "$FFMPEG" -nostdin -hide_banner -loglevel error -init_hw_device vulkan=vk -filter_hw_device vk \
      -f lavfi -i "$SRC" -vf "libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path=$1:format=rgba64le" \
      -f framemd5 - 2>"$OUT/${1%.glsl}.err" | grep -v '^#' | awk -F, '{print $NF}' )
}
md5 plain.glsl > "$OUT/plain.md5"; md5 sticky.glsl > "$OUT/sticky.md5"; md5 skiponly.glsl > "$OUT/skiponly.md5"
( cd "$OUT" && "$FFMPEG" -nostdin -hide_banner -loglevel error -init_hw_device vulkan=vk -filter_hw_device vk \
    -f lavfi -i "$SRC" -vf "libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path=counter.glsl:format=rgba64le" \
    -f rawvideo -pix_fmt rgba64le counter.raw ) 2>"$OUT/counter.err"

# Every render must have compiled and run the hook: a compile error means libplacebo fell back to its own mixer and
# every comparison below would compare that fallback with itself.
# The output is rgba64le, not rgb48le: libplacebo on Mesa (the NAS's Arc) cannot configure an rgb48le output pad and
# rendered nothing, and the first Arc run printed a verdict over zero frames (2026-10-22). Any render that produced no
# frame, or failed to configure, is refused here.
for e in "$OUT"/plain.err "$OUT"/sticky.err "$OUT"/counter.err; do   # skiponly is the counterfactual: it may break
  if grep -q -i -E "compile status .error|Failed executing|disabling|Failed to configure|Error reinitializing" "$e"; then
    echo "sticky_live: FAIL: $(basename "$e") shows a shader that did not run:"; grep -i -m3 -E "error|Failed" "$e"; exit 1
  fi
done

"$PY" - "$OUT" <<'PY'
import struct, sys, os
out = sys.argv[1]
r = lambda f: open(os.path.join(out, f)).read().split()
plain, sticky, skip = r("plain.md5"), r("sticky.md5"), r("skiponly.md5")
n = len(plain)
a = n > 0 and plain == sticky
disabled = "Disabling" in open(os.path.join(out, "skiponly.err")).read()
b = n > 0 and (skip != plain or disabled)
diff_b = sum(x != y for x, y in zip(plain, skip))
raw = open(os.path.join(out, "counter.raw"), "rb").read()
if n == 0 or not raw:
    print("sticky_live: FAIL: no frames were rendered (see the .err files); no verdict"); sys.exit(1)
W, H = 320, 180; size = W * H * 8
counters = []
for f in range(len(raw) // size):
    g = struct.unpack_from("<4H", raw, f * size + (90 * W + 160) * 8)
    counters.append(round(g[1] / 65535 * 256))
same = sum(1 for i in range(1, len(counters)) if counters[i] == counters[i - 1])
print("outputs: %d" % n)
print("(a) sticky against plain:      %s" % ("IDENTICAL, every frame" if a else "DIFFERENT (%d frames)" % sum(x != y for x, y in zip(plain, sticky))))
print("(b) skip without sticky:       %s" % (("differs on %d of %d frames" % (diff_b, n)) + ("; libplacebo DISABLED the hook (the reading pass found no texture on a skipped output)" if disabled else "") + ", as it must" if b else "IDENTICAL: the counterfactual failed"))
print("(c) the counter, first 15:     %s" % " ".join(str(c) for c in counters[:15]))
print("    outputs repeating the previous output's counter: %d of %d (the window reused, the pass skipped)" % (same, len(counters) - 1))
ok = a and b and same >= (len(counters) - 1) // 2
print("sticky_live: %s" % ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
PY
