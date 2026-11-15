# Accelerating the independent MCI reference

The source-rate n-directional fields remain a separate useful measurement tool.
This experiment asks whether the independent interpolator Gareth found calmer
can run faster **without changing its pictures**. It does not establish that MCI
is universally better, or fix the existing GLSL estimator.

- [Registered plan](PLAN.md), [exactness/timing gate](GATE.md).
- [CPU results](RESULTS.md) and [portable measurements](measurements.json).
- [GPU renderer derivation and implementation plan](GPU-DESIGN.md).
- [Primary sources and prior implementations](SOURCES.md).

## Isolated build

Use an independent worktree of FFmpeg commit
`3a5eb948e76dc6390e4b3cff7becf84bc492b7af`. Preserve the installed research binary
and its unrelated patches. `profile.py /absolute/ffmpeg-source` adds optional
timers to the pinned stock file; it rejects another source hash.

Configure the profiling baseline and compile it. The measured minimal baseline
used these options (the candidate additionally enabled pixelutils):

```sh
./configure --disable-everything --disable-autodetect --disable-doc --disable-debug \
  --enable-ffmpeg --enable-ffprobe --enable-pthreads \
  --enable-protocol=file,pipe --enable-demuxer=matroska \
  --enable-decoder=ffv1,rawvideo --enable-encoder=ffv1,rawvideo \
  --enable-muxer=matroska,rawvideo,framemd5,null \
  --enable-filter=minterpolate,format,scale,setpts,settb,tpad,trim,select,testsrc2,color,null \
  --enable-indev=lavfi
make -j8 ffmpeg ffprobe
```

Copy the baseline executables and `ffbuild/config.mak` outside the build tree.
Then generate the candidate with `accelerate.py --source /absolute/ffmpeg-source
--out /absolute/patch-directory`, inspect its manifest, and apply its generated
`accelerate.patch` to that isolated checkout. **Re-run configure**, with the same
options and `--enable-pixelutils`, then rebuild and preserve the candidate too.
The changed configure dependency does not update an existing configuration when
only `make` is run. Our first SIMD control refused that incomplete build; it was
reconfigured before any candidate equivalence or timing claim.

The complete profiling-plus-acceleration patch is retained as
[ffmpeg.patch](ffmpeg.patch). Reproduction can apply that directly to the pinned
stock source, instead of invoking both generators. These are alternative routes,
not patches to apply twice. `build-provenance.json` records source, executable,
patch, compiler and configuration hashes for the measured builds.

## Runtime choices

`mci_accel` defaults to zero and is an experimental initialization-time bitmask:

| Bit | Work changed | Algorithmic boundary |
|---:|---|---|
| 1 | Existing pixelutils SIMD overlapping SAD | Same integer cost, clipping and predictor penalty |
| 2 | Independent bidirectional EPZS searches | Two private contexts; each retains row-major predictor order |
| 4 | Output-row jobs | One owner per complete chroma row group |
| 8 | Skip chroma calculations subsequently overwritten | Keep the original last luma representative |

Mask 15 combines all four. It does not parallelize the order-sensitive OBMC
scatter. The command's `aobmc` and `vsbmc=1` are inactive under `me_mode=bidir`;
the preserved reference is ordinary fixed-block overlap with EPZS.

Run the generated `sad_control.c` against the candidate's actual libavutil,
then the all-plane gates in GATE.md. `controls.py` verifies refusals, including
chroma-only corruption. `summarize.py` revalidates the external evidence before
extracting compact measurements. `gather_controls.py` checks the GPU design's
ordered-gather formula on CPU constructions; it is not a GPU speed test.

The tested scope is explicitly recorded in RESULTS.md. Do not infer validation
of every FFmpeg pixel format, search algorithm, interpolation mode or hardware
backend from a passing bidirectional EPZS matrix.
