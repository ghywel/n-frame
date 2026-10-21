#!/bin/bash
# Time from a file, build against build (2026-10-21): what an FFmpeg / libplacebo update does to a shader's cost.
#
#   probes/build/buildtime.sh <outdir> <A>=<ffmpeg A> <B>=<ffmpeg B> <tag>=<shader.glsl|linear> [...]
#
# The record's method (TESTING.md, "Timing basis"; cost/timing.sh, which is written for the Windows boot): the source
# is an ffv1 FILE rendered once, since a lavfi source was up to 70% of a naive "shader time"; the output goes to -f
# null; every (build, shader) pair is INTERLEAVED over three rounds after one warm-up render each, and the median is
# reported, so thermal drift and driver warm-up land on both builds alike. 720p (the ladder's O5_osc_textured, scaled
# to 1280x720), 24 -> 60, 120 output frames. MoltenVK's determinism switches are OFF here (MVK_DETERMINISTIC=0), as
# for the record's timing runs: the default path is the one timed. One GPU job at a time; run it alone.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS="$HERE/../.."
[ $# -ge 4 ] || { sed -n '3,4p' "$0"; exit 2; }
OUT="$1"; shift
mkdir -p "$OUT" || exit 2
export MVK_DETERMINISTIC=0
. "$TESTS/mvk-env.sh"
. "$TESTS/scenes.sh"
A="$1"; B="$2"; shift 2
SRC="$OUT/src.mkv"
if [ ! -s "$SRC" ]; then
  S="$(scene O5_osc_textured 24)"; S="${S//:d=1,/:d=3,}"
  "${A#*=}" -y -hide_banner -loglevel error -f lavfi -i "$S" -c:v ffv1 "$SRC" || exit 1
fi
# 120 outputs at 60 fps need 2 s of source; a short source would end the run early and time fewer frames, silently
n=$("$(dirname "${A#*=}")/ffprobe" -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$SRC")
[ "${n:-0}" -ge 60 ] || { echo "the source has ${n:-0} frames, fewer than the 60 a 120-frame output needs"; exit 1; }
echo "source: $n frames at 24 fps, 1280x720"
for spec in "$@"; do
  tag="${spec%%=*}"; sh="${spec#*=}"
  [ "$sh" = linear ] || cp -f "$sh" "$OUT/$tag.glsl" || exit 2
done
"${PY:-python3}" - "$OUT" "$A" "$B" "$@" <<'EOF'
import os, statistics, subprocess, sys, time
out, A, B, specs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
builds = [tuple(A.split("=", 1)), tuple(B.split("=", 1))]
tags = [s.split("=", 1)[0] for s in specs]
lin = {t: s.split("=", 1)[1] == "linear" for t, s in zip(tags, specs)}

def run(ff, tag):
    vf = ("libplacebo=fps=60:frame_mixer=linear" if lin[tag] else
          "libplacebo=fps=60:frame_mixer=custom_n:custom_shader_path=%s.glsl" % tag)
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-init_hw_device", "vulkan=vk", "-filter_hw_device", "vk",
           "-i", "src.mkv", "-vf", vf, "-frames:v", "120", "-f", "null", "-"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=out, capture_output=True, text=True)
    t = time.perf_counter() - t0
    if p.returncode or "compile status .error" in p.stderr:
        sys.exit("FAILED: %s %s\n%s" % (ff, tag, p.stderr[-400:]))
    return t

for name, ff in builds:
    for tag in tags:
        run(ff, tag)                     # warm-up, not counted
t = {(n, tag): [] for n, _ in builds for tag in tags}
for rnd in range(3):
    for tag in tags:
        for name, ff in (builds if rnd % 2 == 0 else builds[::-1]):
            t[(name, tag)].append(run(ff, tag))
    print("  round %d done" % (rnd + 1), flush=True)
print("\n%-8s %12s %12s %9s   (ms per output frame, median of 3; 120 frames, 720p, 24 -> 60, ffv1 source)"
      % ("shader", builds[0][0], builds[1][0], "B / A"))
for tag in tags:
    a = statistics.median(t[(builds[0][0], tag)]) / 120 * 1000
    b = statistics.median(t[(builds[1][0], tag)]) / 120 * 1000
    print("%-8s %12.2f %12.2f %9.3f   spread A %s, B %s" % (tag, a, b, b / a,
          "/".join("%.2f" % (x / 120 * 1000) for x in t[(builds[0][0], tag)]),
          "/".join("%.2f" % (x / 120 * 1000) for x in t[(builds[1][0], tag)])))
print("TIMING DONE")
EOF
