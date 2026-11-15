# Exact CPU acceleration of the calmer MCI reference

2026-11-15. Research prototype; no installed FFmpeg, Cadence resource or shader
default changed. The source-rate motion fields remain independent of playback.

## What was actually tested

The pinned active path is bidirectional EPZS, a 16-pixel vector grid and 32x32
matching/overlap support, with fixed overlap weights. `aobmc` and `vsbmc=1` in
the preserved command are inactive on this path. The owner found the independent
shirt reference calmer; this block accelerates those pictures without making a
new comfort or general interpolation-quality claim.

All **141 candidate/reference comparisons passed**:

- Eleven small cases, six individual/combined configurations: 66 comparisons.
  Vertical/horizontal bars, an occluding face, fast pan, static, cut, grain and
  frozen rigid texture, non-macroblock dimensions and non-midpoint 60fps phases.
- Both complete cached 1080p film windows, configurations 0/4 threads and
  15/1 or 4 threads: six comparisons.
- Both boundary cases, macroblocks 4/8/16, seven mask/thread configurations:
  42 comparisons. Includes 638x358 YUV420 and 639x359 YUV444.
- Three cases, three repeats at 1/2/4 threads with mask15: 27 comparisons.

Every decoded Y/U/V byte, count, physical PTS, DTS, duration and size agrees.
The new scalar baseline also matches every decoded YUV sample of the previously
displayed MCI clips: shirt 238 frames, suit 286. Their Matroska time-base rounding
is not confused with the exact normalized timestamps in the new rawvideo gate.
The gate checks invoked pair/draw counts and rejects incomplete runs.

The actual compiled scalar/SIMD cost functions agree in **49,152 cases**, including
border clipping, predictor penalties, unaligned starts, unequal strides, extreme,
periodic and random data at all three block sizes. Thirty refusal controls pass,
including real one-pixel chroma/luma changes, timestamp/count corruption, incomplete
records, wrong-but-rehashed commands and stale derived timing metrics.

Two independent source reviews checked direction contexts, spatial predictor
ordering, row ownership and synchronous worker joins. Exact output on this matrix
is evidence for this scope, not proof for every possible input or every FFmpeg mode.

## Where the time goes

Initial single-run stage profiling on the original scalar path found:

| Clip | ME s | Overlap-list construction s | Pixel output s | Process wall s |
|---|---:|---:|---:|---:|
| Shirt | 4.308 | 8.176 | 10.631 | 23.249 |
| Suit | 5.391 | 9.731 | 12.912 | 28.147 |

These are orientation measurements, not the warmed timing comparison below.
Motion estimation consumes about 19% of wall time; overlap plus output consumes
about 80%. Making only ME free would therefore cap the whole-process gain around
1.24x under this measured workload. Drawing deserves at least as much attention
as searching. SIMD and threading still reduce CPU work left in a future hybrid.

The original per-luma-pixel vector/weight/reference lists occupy about 605.5 MB
at 1080p, before frames and other state. The faithful GPU gather design avoids
materializing those lists while preserving their ordered, capped contributions.

## Repeated timing

The measured host is an Apple M5, ten CPU cores, 16 GiB RAM; this is not the
Intel NAS. Compiler and exact build flags are in
[build-provenance.json](build-provenance.json). Both builds use the same optimized
compiler settings; candidate configuration additionally enables pixelutils, the
dependency required by its SIMD path. Decoder and encoder threads are one.

The timed sink is rawvideo framemd5, including decoding and checksumming. One
process runs at a time with no simultaneous compilation or GPU job. Each clip
warms both implementations, then runs three alternating paired comparisons.
Every timed output is checked again against the certified exact records.

| Clip | Original wall s (range) | CPU candidate wall s (range) | Speedup | Output FPS | Source time / wall |
|---|---:|---:|---:|---:|---:|
| shirt | 23.666 (23.650–23.674) | 10.695 (10.661–10.764) | 2.213x | 22.25 | 0.464x |
| suit | 28.387 (28.355–28.396) | 12.726 (12.705–12.774) | 2.231x | 22.47 | 0.469x |

Mask15 uses four filter threads. Overlap-list construction remains serial and
now dominates the candidate; its median stage times are 8.535s/10.156s, compared
with only 0.343s/0.423s for ME and 1.703s/2.020s for output.

The individual samples, stage times, CPU time, output FPS and source-duration /
wall-time ratio are preserved in [measurements.json](measurements.json); the
automatically extracted [table](measurements.md) is an additional audit view.
These throughput figures are not timings of playback, hardware decode/encode or
the Arc A310. A 24->48 pipeline needs about 48 output frames/s for real time.

## Failures and limits

The first candidate compiled but its standalone SIMD control exited 3: pixelutils
was absent from the pre-existing build configuration. Merely editing configure's
dependency and running make had not regenerated it. Explicit reconfiguration and
rebuild resolved this before any equivalence/timing claim. The failed setup is
retained in provenance; the installed research binary was never replaced.

Only the registered bidirectional EPZS 8-bit YUV420/YUV444 matrix was run. Other
chroma formats, bilateral/AOBMC/VSBMC operation, other search methods, per-frame
vector dumps, x86 SIMD, sanitizer runs and long-form playback remain untested in
this block. Tests establish unchanged pictures, not a new quality improvement.
Native NAS build/throughput and GPU replay are separate follow-ups.

The GPU formula controls independently match ordered scatter at 30,138 luma
sites. Deliberately changing cap order changes a constructed output 127->124;
ignoring the cap gives125. Choosing the first rather than last chroma representative
changes 4,450 samples; negative signed division also has an explicit counterexample.
These are CPU formula controls, not execution of a GPU renderer.
