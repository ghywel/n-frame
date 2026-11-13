# Motion stress probes

Research tests for bars, fast pans and moving faces in the two-frame High family. Start with
[RESULTS.md](RESULTS.md) for the measured outcome and [PLAN.md](PLAN.md) for the registered gates.
The current combined variant is experimental and fails the replacement gate.

Run from the repository root with the project's patched FFmpeg, NumPy and deterministic Vulkan/MoltenVK setup.
The MSL translation step also requires `glslc` and `spirv-cross` on PATH. Generated shaders and media belong
outside git. No simultaneous GPU jobs.

```sh
set -eu
PY="${PY:-python3}"
FF="${FFMPEG:-ffmpeg}"
export PYTHONDONTWRITEBYTECODE=1
R="$NP_SCRATCH/motionstress-20261113"
mkdir -p "$R"

"$PY" tests/probes/motionstress/scenes.py
"$PY" tests/probes/motionstress/controls.py "$R/controls.json"
"$PY" tests/probes/motionstress/build.py "$R/shaders"

# First experiment's original fourteen cases (exclude the later pan holdouts).
"$PY" tests/probes/motionstress/run.py "$R" --ffmpeg "$FF" \
  --shaders "high=$R/shaders/high.glsl" "inverse2=$R/shaders/inverse2.glsl" linear=linear \
  --cases face_static face_slow face_fast face_counterpan face_occluded face_lowcontrast \
  pan_detail pan_mixed bars_v9 bars_v24 bars_h9 bars_h24 bars_diagonal bars_static

# All seventeen analytic cases, including the three off-grid holdouts.
"$PY" tests/probes/motionstress/run.py "$R/round2" --ffmpeg "$FF" \
  --shaders "high=$R/shaders/high.glsl" "inverse-data=$R/shaders/inverse-data.glsl" \
  "global-fullres=$R/shaders/global-fullres.glsl" "combined=$R/shaders/combined.glsl"

"$PY" tests/probes/motionstress/failure_controls.py "$R/failure-controls" \
  "$R/face_static/source.mkv" --ffmpeg "$FF"

for label in high inverse2 combined; do
  FFMPEG="$FF" OUTROOT="$R/ladder" bash tests/bench.sh all "$R/shaders/$label.glsl" "$label"
done
for label in inverse2 combined; do
  "$PY" tests/probes/motionstress/ladder_report.py "$R/ladder" "$label"
done
OUTROOT="$R/ladder" "$PY" tests/analyze.py --variants
SKIP_END=2 OUTROOT="$R/ladder" "$PY" tests/analyze.py --variants
```

The optional photographic tests require the original external `photo-head.npy` (215x155 float grayscale in [0,1])
and its provenance record. An arbitrary replacement crop is a different experiment. Source material stays external.
Omitting the photos permits an analytic-only run; the final complete-summary command below requires both photos
and all six cached footage windows, as well as the analytic, ladder and timing results.

```sh
"$PY" tests/probes/motionstress/run.py "$R/photos" --ffmpeg "$FF" \
  --photo-patch "$R/photo-head.npy" --cases photo_fast photo_counterpan \
  --shaders "high=$R/shaders/high.glsl" "inverse2=$R/shaders/inverse2.glsl" \
  "inverse-data=$R/shaders/inverse-data.glsl" "combined=$R/shaders/combined.glsl"

# CONTENT_CACHE contains real/{film1,tv1,cg1}/{ref,half}_<time>.mkv, two windows each.
"$PY" tests/probes/motionstress/real.py "$R/real" "$CONTENT_CACHE" \
  --ffmpeg "$FF" --ffprobe "${FFPROBE:-ffprobe}" \
  --shaders "high=$R/shaders/high.glsl" "combined=$R/shaders/combined.glsl"
"$PY" tests/probes/motionstress/timing.py "$R/timing" "$CONTENT_CACHE/real/tv1/ref_216.0.mkv" \
  --ffmpeg "$FF" --shaders "high=$R/shaders/high.glsl" "combined=$R/shaders/combined.glsl"
"$PY" tests/gen_metal.py "$R/shaders/combined.glsl" "$R/metal-combined" --compile
"$PY" tests/probes/motionstress/summarize.py "$R" --require-timing
```

`run.py` checks process status, shader fallback indicators, exact decoded length and retained-frame alignment.
Per-case `<label>.json` files are authoritative; `summary.json` contains only the latest invocation's labels.
`summarize.py` deliberately reads the per-case files and rejects incomplete evidence. Its extraction describes
this registered experiment; it does not perform or certify visual inspection. Worst-feature comparison crops
used in RESULTS are saved as `photos/{photo_fast,photo_counterpan}/comparison.png`, ordered truth / High / combined.
