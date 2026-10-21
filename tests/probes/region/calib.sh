#!/bin/bash
# THE REGION COLUMN'S CALIBRATION (2026-10-21, the swarm's instruments lane, item 2): a defect whose score is known
# exactly, planted inside a case's object and then outside its region, through bench.sh's own graph.
#
#   probes/region/calib.sh [outdir]        FFMPEG= the build (default ffmpeg on PATH); PY= python3 (analyze.py needs
#                                          no numpy); CASE= (default L0_static)
#   Exit 0 when all three checks pass. CPU only: no libplacebo, no Vulkan -- the "interpolated" input is the 60 fps
#   truth itself with +8 added to the Y plane inside a 100x100 patch, so every frame is identical and the answer is
#   arithmetic: PSNR = 10 log10(255^2 / (64 * patch / area)).
#
# WHY L0_static: the patch must sit INSIDE the object's mask on every frame, and L0's 100x100 box at (400, 310) is
# the only box that does not move, so the patch IS the object. Its region (regions.sh) is 132x132 at (384, 294).
#
# THE THREE CHECKS, each with its number written before the run:
#   1. planted_in  (patch = the object, 400..499 x 310..409):
#        whole frame: 64 * 10000 / 921600 -> 49.71 dB;  region: 64 * 10000 / 17424 -> 32.48 dB.
#      (The brief's "about 30.07" is the patch filling its region; with a swept-path crop the exact figure is
#       30.07 + 10 log10(crop area / patch area), and that is what is checked, to 0.02 dB.)
#   2. planted_out (patch at 1000..1099 x 100..199, outside the crop): whole frame 49.71 dB again (the same patch
#      size), region inf (the two crops are identical). The region column must not move; the frame column must.
#   3. the whole-frame log written by the new graph (split + two psnr) must be BYTE-IDENTICAL to one written by the
#      old single-psnr graph for the same input: the region pass changes nothing that existed.
# The pass is judged on the psnr stats files AND on analyze.py --region's printed columns (the parsing is part of
# the instrument). A failure of 1 or 2 is a wrong crop or a wrong parse; of 3, the split altered the frame scoring.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS="$(cd "$HERE/../.." && pwd)"
. "$TESTS/scenes.sh"
. "$TESTS/regions.sh"
FFMPEG="${FFMPEG:-ffmpeg}"
PY="${PY:-python3}"
CASE="${CASE:-L0_static}"
OUT="${1:-${NP_SCRATCH:-$HOME/Developer/np-scratch}/region-calib/$(date +%Y%m%d-%H%M%S)}"
D="$OUT/$CASE"; mkdir -p "$D" || { echo "cannot make $D"; exit 2; }

S60="$(scene "$CASE" 60)"
REGION="$(region_crop "$CASE")"
[ -n "$REGION" ] || { echo "no region for $CASE in regions.sh"; exit 2; }
# the crop's geometry, for the expected values
CW=$(echo "$REGION" | sed -E 's/crop=([0-9]+):([0-9]+):([0-9]+):([0-9]+)/\1/'); CH=$(echo "$REGION" | sed -E 's/crop=([0-9]+):([0-9]+):([0-9]+):([0-9]+)/\2/')
CX=$(echo "$REGION" | sed -E 's/crop=([0-9]+):([0-9]+):([0-9]+):([0-9]+)/\3/'); CY=$(echo "$REGION" | sed -E 's/crop=([0-9]+):([0-9]+):([0-9]+):([0-9]+)/\4/')

plant() {   # <mode> <x0> <y0>  -- +8 Y levels on a 100x100 patch, bench.sh's graph verbatim but for the input
  local mode="$1" x0="$2" y0="$3"
  local chain="format=yuv420p,geq=lum='lum(X\,Y)+8*between(X\,$x0\,$((x0 + 99)))*between(Y\,$y0\,$((y0 + 99)))':cb='cb(X\,Y)':cr='cr(X\,Y)'"
  ( cd "$D" && "$FFMPEG" -y -hide_banner -loglevel error -f lavfi -i "$S60" -f lavfi -i "$S60" \
      -filter_complex "[0:v]${chain}[ip];[ip]format=yuv420p,split[a][a2];[1:v]split[b][b2];[a][b]psnr=stats_file=$mode.log[o];[a2]$REGION[ra];[b2]$REGION[rb];[ra][rb]psnr=stats_file=$mode.region.log[o2]" \
      -map "[o]" -f null - -map "[o2]" -f null - ) 2> "$D/$mode.err" || { echo "$mode: ffmpeg failed"; cat "$D/$mode.err"; exit 1; }
  # the old graph, for check 3
  ( cd "$D" && "$FFMPEG" -y -hide_banner -loglevel error -f lavfi -i "$S60" -f lavfi -i "$S60" \
      -filter_complex "[0:v]${chain}[ip];[ip]format=yuv420p[i2];[i2][1:v]psnr=stats_file=${mode}_oldgraph.log[o]" \
      -map "[o]" -f null - ) 2>> "$D/$mode.err" || { echo "$mode (old graph): ffmpeg failed"; exit 1; }
}
plant planted_in  400  310      # inside: the object itself (L0's box; for another CASE set the patch by hand)
plant planted_out 1000 100      # outside the crop

echo "== analyze.py --variants --region on $OUT"
OUTROOT="$OUT" "$PY" "$TESTS/analyze.py" --variants --region "$CASE" | tee "$OUT/analyze.txt"
echo
"$PY" - "$D" "$CW" "$CH" "$CX" "$CY" "$OUT/analyze.txt" <<'EOF'
import math, re, sys, os
d, cw, ch, cx, cy, table = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
area = 1280 * 720; patch = 100 * 100
exp_frame = 10 * math.log10(255 ** 2 / (64.0 * patch / area))
exp_region = 10 * math.log10(255 ** 2 / (64.0 * patch / (cw * ch)))
inside = cx <= 400 and 400 + 100 <= cx + cw and cy <= 310 and 310 + 100 <= cy + ch
def mean(path):
    vals = [float("inf") if v == "inf" else float(v) for v in re.findall(r"psnr_y:([0-9.]+|inf)", open(path).read())]
    vals = [v for v in vals if v != float("inf")]
    return sum(vals) / len(vals) if vals else float("inf")
f_in, r_in = mean(os.path.join(d, "planted_in.log")), mean(os.path.join(d, "planted_in.region.log"))
f_out, r_out = mean(os.path.join(d, "planted_out.log")), mean(os.path.join(d, "planted_out.region.log"))
same = open(os.path.join(d, "planted_in.log"), "rb").read() == open(os.path.join(d, "planted_in_oldgraph.log"), "rb").read()
same &= open(os.path.join(d, "planted_out.log"), "rb").read() == open(os.path.join(d, "planted_out_oldgraph.log"), "rb").read()
print("crop %dx%d at (%d, %d); the planted patch is %s it" % (cw, ch, cx, cy, "inside" if inside else "NOT inside"))
print("expected: whole frame %.2f dB (both placements); region %.2f dB inside, inf outside" % (exp_frame, exp_region))
print("measured: planted_in  frame %.2f  region %s" % (f_in, "inf" if r_in == float("inf") else "%.2f" % r_in))
print("          planted_out frame %.2f  region %s" % (f_out, "inf" if r_out == float("inf") else "%.2f" % r_out))
c1 = abs(f_in - exp_frame) < 0.02 and abs(r_in - exp_region) < 0.02
c2 = abs(f_out - exp_frame) < 0.02 and r_out == float("inf")
c3 = same
# the printed table must carry the same numbers (the parse is part of the instrument)
t = open(table).read()
row = [ln for ln in t.splitlines() if ln.startswith(os.path.basename(d))]
c4 = bool(row) and ("%.2f" % r_in) in row[0] and ("%.2f" % f_in) in row[0] and "inf" in row[0]
print("check 1 (inside: frame diluted, region exact):   %s" % ("PASS" if c1 else "FAIL"))
print("check 2 (outside: frame moves, region inf):      %s" % ("PASS" if c2 else "FAIL"))
print("check 3 (whole-frame log byte-identical to the old graph): %s" % ("PASS" if c3 else "FAIL"))
print("check 4 (analyze.py --region prints the same numbers):     %s" % ("PASS" if c4 else "FAIL"))
print("region calib: " + ("PASS" if c1 and c2 and c3 and c4 else "FAIL"))
sys.exit(0 if c1 and c2 and c3 and c4 else 1)
EOF
