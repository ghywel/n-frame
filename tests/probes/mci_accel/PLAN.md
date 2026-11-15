# Faster MCI while preserving the useful motion-field instrument

Registered 2026-11-15 before builds/measurements. The owner explicitly prioritizes useful playback over retaining
the project's current interpolation renderer. The n-directional source-rate fields remain a separate useful
sense organ. Investigate CPU multithreading/SIMD, a GPU implementation of the calmer FFmpeg reference, and hybrids.
There is a human calmer-shirt observation, not proof of universal MCI superiority or a complete film-quality gate.

The active reference is pinned FFmpeg `3a5eb94`, default bidirectional EPZS, 16px vector grid, 32×32 matching/overlap,
fixed overlap weights. `aobmc` and `vsbmc=1` in the preserved command are inactive under `me_mode=bidir` (G035).
The installed research FFmpeg has unrelated local patches; build in a separate checkout and do not replace it.
No production shader, default, system package or Cadence resource changes in this block.

## First bounded engineering step

Profile ME, overlap-list construction and pixel output separately, then test runtime-selectable exact optimizations:

1. Existing unaligned pixelutils SIMD SAD for the active overlapping 8/16/32 square costs. Preserve clipping,
   the pre-clamp displacement penalty, candidate order and integer sums.
2. Two independent search directions, each with separate mutable ME context and unchanged row-major block order.
   Current left/top/top-right predictors make naive block/row parallelism invalid. Join before frame drawing.
3. Chroma-aligned output-row ownership for slice threading; shared output pixels must have one owner.
4. Eliminate overwritten chroma calculations while retaining exactly the last luma representative currently used
   for each chroma cell, including odd dimensions and signed division semantics.

Runtime bitmask `mci_accel` records which interventions ran; zero retains the baseline path. No OBMC scatter
threading: the first 16 accepted block hypotheses survive a 32-endpoint cap in a fixed order. Unordered atomics
would change results. Timers measure stage wall time, not CPU instruction counts; they are not part of the quality test.

## Gate

Use the two already cached short real windows (no further NAS media reads), plus compact synthetic/static/periodic,
positive/negative motion, cuts, startup/end and boundary cases. Compare **all decoded YUV planes**, frame counts and
timestamps, not just grayscale. Any mismatch fails an output-preserving claim and needs investigation. Test masks
separately before combined, thread counts 1/2/4, repeated combined runs, macroblock sizes 4/8/16 and relevant chroma
formats for the changed paths. SIMD costs must agree with scalar sums for unaligned pointers, unequal strides,
extreme differences and random pixels. Scope unsupported/untested paths explicitly.

Time warmed, interleaved baseline/candidate runs with the same source, build flags and output sink. Run one benchmark
process at a time. Report stage and whole-process time, spread, output FPS and source-duration/wall-time ratio.
Hardware is identified, and Mac results do not establish Arc or NAS performance. NAS read-only inspection confirms
an i5-9500 with six cores/six threads; native NAS build/benchmark is conditional on a usable isolated build environment.
No GPU timing or speedup claim from CPU tests. A correct but slower change is retained as a failed optimization.

## GPU and hybrid boundary

Design a faithful integer GPU gather renderer for stock CPU vectors first, or the reverse cross-test with an
unchanged stock renderer driven by another field. Keep these separate from altered motion algorithms. Preserve
moving support positions, canonical candidate order/cap, exact rounding, border and chroma semantics before changing
quality. Exact EPZS wavefront scheduling and alternative GPU matching have different equivalence claims.
Use profiling to choose which stage to port; do not assume drawing or estimation is the bottleneck.
