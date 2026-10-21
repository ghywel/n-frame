#!/bin/bash
# The frame-mix hook's window, READ from a live build rather than transcribed (2026-10-21).
#
#   probes/window/window_live.sh [outdir]          FFMPEG= picks the build (default ffmpeg on PATH)
#
# window_rule.py tabulates the rule as the patch's C states it: the nearest frame before and after first, then the
# remaining slots greedily from whichever side is nearer, TIES TO THE EARLIER FRAME. That tie is what puts the
# four-frame window at [-2, -1, 0, +1] at N:N, where -2 and +2 are exactly as far from the output time, and every
# N:N field read of the quad assumes it. The rule lives in C that compares timestamps the queue computes; libplacebo
# API 375 (2026-10-10) changed those timestamps from float to double, so a tie that was exact in float can come out
# a hair uneven in double and flip silently. Nothing else in the harness would see it: a translation's flow is the
# same for every pair, and the picture at N:N is a passthrough.
#
# How: a generated hook per window size N (3, 4, 5) paints slot k's relative timestamp into its own band of
# columns: R = (floor(t) + 8) / 16 and G = fract(t), with B = mix_t; the last band carries num_mix / 16. The output is
# rgb48le chosen INSIDE the filter (libplacebo's own format option), never by -pix_fmt on the output (TESTING.md,
# field-read path). The hook's output passes an fp16 stage (REPAIRS.md L10): small integers over 16 survive it exactly,
# and a fraction in G is read to 2^-11 of a frame or better, about 0.0005. The first form, R = 0.5 + t / 16, read the
# timestamp only to fp16's step there (0.004-0.008 of a frame), which on its first run looked like a timestamp error
# of 0.006 and a straddling pair 0.9959 apart: the instrument's floor, not the queue's (2026-10-21).
# One steady-state output frame per phase is decoded at 24 -> 24 (N:N), 24 -> 60 and 25 -> 60, and two things are
# reported. THE WINDOW (the verdict): each slot's source frame, round(t_src + rts), against the rule's set. Exit 0
# when every output's set matches; 1 on any mismatch. THE TIMESTAMPS (a measurement, no verdict): each slot's
# error against the ideal i - t_src, and the spacing of the pair that straddles the output, exactly 1 for a source at
# a constant rate; read them against the 0.0005 resolution.
#
# Where the ties are: at a phase of 0 (every output at N:N, every fifth at 24 -> 60) for N = 4, and at a phase of
# one half (25 -> 60) for N = 3 and 4. For N = 5 a tie decides only the order of picks, not the set. Calibration:
# the non-tie outputs must read the rule exactly, and a deliberately wrong expectation (ties to the LATER frame)
# must be refused at N:N, N = 4. Both are printed.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FFMPEG="${FFMPEG:-ffmpeg}"
PY="${PY:-python3}"
OUT="${1:-${NP_SCRATCH:-$HOME/Developer/np-scratch}/window-live/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT" || { echo "cannot make $OUT"; exit 2; }
. "$HERE/../../mvk-env.sh"

for N in 3 4 5; do
  {
    echo "//!HOOK FRAME_MIX"
    echo "//!BIND HOOKED"
    for k in $(seq 1 $((N - 1))); do echo "//!BIND FRAME$k"; done
    echo "//!DESC [probe] window_live: rts_mix per slot, N=$N"
    echo ""
    echo "vec4 hook() {"
    echo "    int k = int(HOOKED_pos.x * 8.0);"
    echo "    if (k == 7) return vec4(float(num_mix) / 16.0, 0.0, 0.0, 1.0);"
    echo "    if (k >= num_mix) return vec4(0.0, 0.0, 0.0, 1.0);"
    echo "    float t = rts_mix[k];"
    echo "    return vec4((floor(t) + 8.0) / 16.0, fract(t), mix_t, 1.0);"
    echo "}"
  } > "$OUT/w$N.glsl"
done

render() {   # render <N> <src fps> <out fps> <frames to read from> <count>
  local N="$1" SF="$2" OF="$3" F0="$4" C="$5" tag="w$1_$2_$3"
  ( cd "$OUT" && "$FFMPEG" -y -hide_banner -loglevel error -init_hw_device vulkan=vk -filter_hw_device vk \
      -f lavfi -i "testsrc2=s=64x8:r=$SF:d=12" \
      -vf "libplacebo=fps=$OF:frame_mixer=custom_n:custom_shader_path=w$N.glsl:format=rgb48le,select='between(n\,$F0\,$((F0 + C - 1)))'" \
      -fps_mode passthrough -f rawvideo -pix_fmt rgb48le "$tag.raw" ) 2> "$OUT/$tag.err"
  if grep -q "compile status .error" "$OUT/$tag.err" || [ ! -s "$OUT/$tag.raw" ]; then
    echo "  $tag FAILED (see $OUT/$tag.err)"; return 1
  fi
}

fail=0
for N in 3 4 5; do
  render "$N" 24 24 120 4 || fail=1     # N:N: four outputs, each sitting exactly on a source frame
  render "$N" 24 60 300 5 || fail=1     # one whole phase period (0, 0.4, 0.8, 0.2, 0.6)
  render "$N" 25 60 288 12 || fail=1    # one whole period of 25 -> 60
done
[ "$fail" = 0 ] || exit 1

"$PY" - "$OUT" <<'EOF'
import struct, sys, math, os
out = sys.argv[1]
W, H = 64, 8

def rule(n_want, t_src, ties_to_lo=True, n_frames=10000):
    ts = lambda i: i - t_src
    split = next(i for i in range(n_frames) if ts(i) > 0.0)
    lo, hi, sel = split - 1, split, []
    sel.append(lo); lo -= 1
    if len(sel) < n_want: sel.append(hi); hi += 1
    while len(sel) < n_want:
        d_lo, d_hi = abs(ts(lo)), ts(hi)
        take_lo = d_lo <= d_hi if ties_to_lo else d_lo < d_hi
        if take_lo: sel.append(lo); lo -= 1
        else: sel.append(hi); hi += 1
    return [ts(i) for i in sorted(sel)]

def frames(path):
    raw = open(path, "rb").read()
    size = W * H * 3 * 2
    for f in range(len(raw) // size):
        px = struct.unpack_from("<%dH" % (W * H * 3), raw, f * size)
        row = 4
        yield [[px[(row * W + 8 * k + 4) * 3 + c] / 65535.0 for c in range(3)] for k in range(8)]

bad = 0
calib_ok = True
alt_fits = 0
worst = {}
cases = [(24, 24, 120, 4), (24, 60, 300, 5), (25, 60, 288, 12)]
print("case            out  t_src   window (offsets from floor t)  ok   max |ts error|  straddle spacing  read rts")
for N in (3, 4, 5):
    for sf, of, f0, c in cases:
        tag = "w%d_%d_%d" % (N, sf, of)
        for j, slots in enumerate(frames(os.path.join(out, tag + ".raw"))):
            n_out = f0 + j
            t_src = n_out * sf / of
            num = round(slots[7][0] * 16)
            read = [round(s[0] * 16) - 8 + s[1] for s in slots[:num]]
            got = [round(t_src + r) for r in read]
            want = [round(t_src + r) for r in rule(N, t_src)]
            ok = num == N and got == want
            # the counterfactual: at N:N, N = 4, ties to the LATER frame must name a different window, or the
            # probe could not tell the two rules apart; count the outputs that fit it
            alt = [round(t_src + r) for r in rule(N, t_src, ties_to_lo=False)]
            if sf == of and N == 4:
                calib_ok = calib_ok and alt != want
                alt_fits += got == alt
            bad += not ok
            err = max(abs(r - (i - t_src)) for r, i in zip(read, got)) if ok else float("nan")
            k = max(i for i in range(num) if got[i] - t_src <= 0)
            spacing = read[k + 1] - read[k] if k + 1 < num else float("nan")
            w = worst.setdefault((sf, of), [0.0, 1.0, 1.0])
            if ok:
                w[0] = max(w[0], err); w[1] = min(w[1], spacing); w[2] = max(w[2], spacing)
            fl = math.floor(t_src + 1e-9)
            print("%-15s %4d %7.3f  %-30s %-4s %.4f          %.4f            %s" % (tag, n_out, t_src,
                  " ".join("%+d" % (g - fl) for g in got), "ok" if ok else "BAD", err, spacing,
                  " ".join("%+.4f" % v for v in read)))
print()
for (sf, of), (e, lo, hi) in sorted(worst.items()):
    print("timestamps %d -> %d: largest error %.4f frame; straddling pair %.4f to %.4f apart" % (sf, of, e, lo, hi))
print("counterfactual: ties to the later frame %s at N:N, N=4, and fits %d of those 4 outputs" % ("names a different window" if calib_ok else "NAMES THE SAME WINDOW (the probe cannot tell the rules apart)", alt_fits))
print("window_live: %s (%d outputs with the wrong window)" % ("PASS" if bad == 0 and calib_ok else "FAIL", bad))
sys.exit(0 if bad == 0 and calib_ok else 1)
EOF
