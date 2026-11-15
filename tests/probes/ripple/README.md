# Translation ripple investigation

Start with [RESULTS.md](RESULTS.md). This is a diagnostic block prompted by two owner-identified garment failures,
not a replacement for High. [PLAN.md](PLAN.md) and the per-intervention documents preserve predictions made before
their renders. Generated shaders, source footage, diagnostic arrays and previews remain outside git.

The subsequent four-render known-motion/grain control is in [RIGID-RESULTS.md](RIGID-RESULTS.md), with its separate
registration in [RIGID.md](RIGID.md). It does not change the real-film conclusions or supply a production fix.

## Reproduce the two conditions

Run from the repository root, using the project's patched FFmpeg/libplacebo and a Python environment with NumPy
and SciPy. The recorded toolchain was FFmpeg `3a5eb94`, libplacebo `285d1cc`; the repository baseline was `ccfdf74`.
`build.py` requires the registered High recipe and byte-checks its output against the shipped shader. Individual
transforms also pin the preceding vote-off High hash. A changed baseline should stop rather than silently rebase.

Set these local variables to your own external locations. `RIPPLE_SOURCE` is the owner-supplied full film; its path
is deliberately not included in this repository. `RIPPLE_PY` needs NumPy/SciPy. Use a fresh output directory for a
new experiment; never combine score sidecars from different inputs or toolchains.

```sh
export RIPPLE_RUN="$NP_SCRATCH/translation-ripple-20261115"
export RIPPLE_FF="$NP_BUILD/ffmpeg/ffmpeg"
export RIPPLE_FP="$NP_BUILD/ffmpeg/ffprobe"
export RIPPLE_PY="$NP_BUILD/venv/bin/python3"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$RIPPLE_RUN"
"$RIPPLE_PY" tests/probes/ripple/build.py "$RIPPLE_RUN/shaders"
```

Cache only the two short windows. Keep full 1920×1080 input to the estimator. Seek before opening the film to bound
NAS traffic; no whole-film scan is needed. The observed clips contain 119 and 143 frames respectively.

```sh
"$RIPPLE_FF" -nostdin -y -ss 200 -i "$RIPPLE_SOURCE" -t 5 -map 0:v:0 -an \
  -c:v ffv1 -level 3 -pix_fmt yuv420p -fps_mode passthrough "$RIPPLE_RUN/shirt-source.mkv"
"$RIPPLE_FF" -nostdin -y -ss 207 -i "$RIPPLE_SOURCE" -t 6 -map 0:v:0 -an \
  -c:v ffv1 -level 3 -pix_fmt yuv420p -fps_mode passthrough "$RIPPLE_RUN/suit-source.mkv"
```

Render each clip serially. `render.py` assigns exact input PTS before libplacebo, uses deterministic MoltenVK
settings, rejects process/shader failures and checks doubled counts. Native input is 24000/1001 fps and output
48000/1001. Stock `linear` is a deliberately non-motion-compensated control.

```sh
for clip in shirt suit; do
  "$RIPPLE_PY" tests/probes/ripple/render.py "$RIPPLE_RUN/$clip" "$RIPPLE_RUN/$clip-source.mkv" \
    --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" --shaders \
    high="$RIPPLE_RUN/shaders/high.glsl" prev="$RIPPLE_RUN/shaders/prev.glsl" \
    vote-nearest="$RIPPLE_RUN/shaders/vote-nearest.glsl" \
    prev-no-fallback="$RIPPLE_RUN/shaders/prev-no-fallback.glsl" linear=linear \
    prev-e-temporal-off="$RIPPLE_RUN/shaders/prev-e-temporal-off.glsl" \
    prev-h-data-refine-off="$RIPPLE_RUN/shaders/prev-h-data-refine-off.glsl" \
    prev-inverse2="$RIPPLE_RUN/shaders/prev-inverse2.glsl" \
    prev-newton="$RIPPLE_RUN/shaders/prev-newton.glsl" \
    prev-aa-box="$RIPPLE_RUN/shaders/prev-aa-box.glsl" \
    prev-obmc8="$RIPPLE_RUN/shaders/prev-obmc8.glsl"
done
```

For withheld truth, make even-frame inputs at 12000/1001. Repeat the render loop with input
`$RIPPLE_RUN/$clip-half.mkv` and output `$RIPPLE_RUN/withheld-$clip`. It now renders 24000/1001. This test has **twice
the endpoint displacement of native interpolation**. It is not photographed ground truth for native midpoints.

```sh
for clip in shirt suit; do
  "$RIPPLE_FF" -nostdin -y -i "$RIPPLE_RUN/$clip-source.mkv" \
    -vf 'select=not(mod(n\,2)),settb=1/24000,setpts=N*2002' -an \
    -r 12000/1001 -fps_mode cfr -c:v ffv1 -level 3 -pix_fmt yuv420p "$RIPPLE_RUN/$clip-half.mkv"
done
```

`withheld.py` accepts any set of `label=video` arguments. For example:

```sh
"$RIPPLE_PY" tests/probes/ripple/withheld.py "$RIPPLE_RUN/shirt-source.mkv" \
  prev="$RIPPLE_RUN/withheld-shirt/prev.mkv" prev-obmc8="$RIPPLE_RUN/withheld-shirt/prev-obmc8.mkv" \
  --crop 240:230:700:620 --first-frame 49 --last-frame 95 \
  --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" --out "$RIPPLE_RUN/withheld-shirt-obmc-scores"
```

For the suit, use crop `160:80:960:800` and the same frame indices. The portable aggregator expects four score
groups for each clip: `withheld-CLIP-scores` contains the first eight render labels above; suffixes `-newton-scores`,
`-aa-scores`, `-obmc-scores` each contain `prev` and the corresponding single diagnostic. These deliberately repeated
baselines must match exactly. The score validates totals and retained-frame alignment before scoring the 24 odd
original frames 49…95, and writes per-frame/tail/gradient/tile results and PNG maps. An incomplete score run is not
a result. All DN values use a normalized grayscale range of 0…255, not raw limited-range Y codes.

```sh
"$RIPPLE_PY" tests/probes/ripple/summarize.py "$RIPPLE_RUN" --initial-video-defect-confirmed \
  --mci-shirt-calmer --obmc-no-clear-improvement
```

The flags record the owner's actual confirmation of the first reproduction video, the noticeably calmer MCI
shirt, and **no clear improvement** from the same-field OBMC shirt. Omit them for an independent run without those
human observations. The aggregator creates a portable
numeric record, checking arithmetic, counts, alignment, hashes and exact repeated baselines. It is specific to this
registered pair of windows; it does not invent a temporal-quality verdict from their PSNR.

## Field and temporal diagnostics

`dump.py` runs the full input, converts diagnostic output to RGB48 inside the filter graph, and crops **after**
interpolation. The field encoding is `0.5 + full_pixel_displacement / 256`. Calibrate it before treating values as
flow. The recorded static control has maximum 0.002 px; the known +32 px horizontal translation reads median
(31.25, 0.13) px in the textured interior. The latter verifies scale/sign within estimator error, not exact flow.

```sh
for field in field support quarter; do
  "$RIPPLE_PY" tests/probes/ripple/dump.py "$RIPPLE_RUN/shirt-$field.npy" "$RIPPLE_RUN/shirt-source.mkv" \
    --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" --shader "$RIPPLE_RUN/shaders/$field.glsl" \
    --frames 97 121 145 169 --crop 160 180 940 720
done
```

For the original calibration, run the `field` shader on the `face_static` and `face_fast` source fixtures produced
by `../motionstress/` at frame 11, without a crop; save `cal-static.npy` and `cal-translation.npy` respectively.
`replay.py "$RIPPLE_RUN" --ffmpeg "$RIPPLE_FF"` requires those calibration arrays and the three shirt dumps. It
reconstructs the preceding High's warp/fallback, refuses RMS disagreement ≥1 DN, and saves exploratory field and
sampling-map statistics. Its fixed rectangle is not a segmentation mask or a ground-truth motion measurement.

For source-only temporal registration:

```sh
"$RIPPLE_PY" tests/probes/ripple/temporal.py "$RIPPLE_RUN/shirt-source.mkv" \
  "$RIPPLE_RUN/shirt/high.mkv" "$RIPPLE_RUN/shirt/prev.mkv" \
  "$RIPPLE_RUN/shirt/vote-nearest.mkv" "$RIPPLE_RUN/shirt/prev-no-fallback.mkv" "$RIPPLE_RUN/shirt/linear.mkv" \
  --crop 440:450:140:140 --start-frame 48 --frames 37 --margin 160 \
  --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" --out "$RIPPLE_RUN/temporal-shirt-48"
```

The recorded track stops at 55→56 for ambiguity. Leave the remaining interval unknown; relaxing the threshold
after seeing failure would invalidate the registered test. Read [TEMPORAL.md](TEMPORAL.md) for both-parity measures
and the grain/physical-deformation ambiguity, and [GEOMETRY.md](GEOMETRY.md) for exact mathematical counterexamples.

## CPU controls and boundaries of this block

```sh
"$RIPPLE_PY" tests/probes/ripple/vote_sampling.py --control
"$RIPPLE_PY" tests/probes/ripple/aa_pyramid.py --control
"$RIPPLE_PY" tests/probes/ripple/newton.py --control
"$RIPPLE_PY" tests/probes/ripple/obmc.py --control
"$RIPPLE_PY" tests/probes/ripple/geometry.py "$RIPPLE_RUN/geometry-controls.json"
"$RIPPLE_PY" tests/probes/ripple/controls.py --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" \
  --out "$RIPPLE_RUN/measurement-controls.json"
"$RIPPLE_PY" tests/probes/ripple/harness_controls.py
```

The optional geometry preview needs a **software** FFmpeg build with libx264; the research build used here lacks
that encoder. Its command is in GEOMETRY.md. Preview encodes are not research renders or pixel-accurate evidence.

The independent FFmpeg `minterpolate` picture control used bidirectional estimation, adaptive overlapped block
compensation and variable-size blocks (`mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`). Two source-frame clones
flushed its delayed tail; output was bounded to the original doubled count. Four retained instants in each clip
were exactly equal in decoded grayscale. The owner reports its shirt is **noticeably calmer** than current High.
That is a human temporal observation on this preview, distinct from numeric gates; it is not a suit result or
deployment approval. The independent estimator and rendering both differ, so neither is isolated by this comparison.

The complete reproduction command for the shirt is below; for the suit change the input/output names and use
`-frames:v 286`. `mci.py` reproduces to separate `mci-recheck.mkv` files and verifies existing displayed `mci.mkv`
files without overwriting them. Its decoded grayscale hashes match every frame of both displayed originals.
Explicit source indices 48/60/72/84 match output 96/120/144/168 exactly. At midpoint 97/121/145/169, no checked
garment crop is simply a held source endpoint. These limited checks do not establish accurate correspondence.

```sh
"$RIPPLE_FF" -nostdin -y -v warning -i "$RIPPLE_RUN/shirt-source.mkv" \
  -vf 'settb=expr=1/48000,setpts=N*2002,tpad=stop_mode=clone:stop=2,minterpolate=fps=48000/1001:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1' \
  -an -frames:v 238 -c:v ffv1 -level 3 -pix_fmt yuv420p "$RIPPLE_RUN/shirt/mci.mkv"
"$RIPPLE_PY" tests/probes/ripple/mci.py "$RIPPLE_RUN" --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP"
```

This is a software CPU operation; it does not use the project's GPU shader. The complete portable reproduction
and endpoint-holding checks are in [mci-recheck.json](mci-recheck.json).

No shipped shader, default or Cadence graph was changed. These two windows and a four-case AA regression probe
are not the full ladder/content/cage or playback-comfort gate. New candidate behavior needs those tests before
adoption, with local boundary failures and the source/inserted transition retained in the assessment.
