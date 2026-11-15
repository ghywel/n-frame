# The overlap stage of the MCI reference without its lists: an exact, threaded accumulate on the CPU

Local, registered 2026-11-15 14:05 GMT, before any code is written or run. The owner: GPT "has been working on a more
efficient ffmpeg minterpolate ... a good candidate but slow ... Please update and continue this work." This continues
[../mci_accel/](../mci_accel/README.md) (GPT's block, G036-G039) and builds on its patch, gate and inputs unchanged.

## Where GPT's block stands, and the door taken

GPT's exact CPU prototype (mask 15) is 2.2x faster than stock and its time is now somewhere else: of 10.7 s on the
shirt window, motion estimation is 0.34 s, the pixel output 1.7 s, and **8.5 s is the serial construction of the
per-pixel overlap lists** (`bidirectional_obmc`: for every luma pixel up to 32 entries of vector, weight and frame,
about 605 MB at 1080p, written block by block and read back once). GPT's route past it is the GPU: a gather shader
that reproduces the lists' arithmetic per output sample, proven exact on 22 captured frames on the M5 and the Arc,
not yet joined to the filter. That in-filter GPU integration is GPT's named next block and is left to GPT.

This block takes the other door: **the same arithmetic on the CPU, with no lists.** What the lists hold is only ever
summed. Per luma pixel the output is `(sum w_i c_i + W/2) / W` over the pairs the scatter accepted, in the scatter's
order, the first 16 pairs only. So the scatter can add each accepted pair straight into three small arrays (the
weighted sum, the weight sum, the pair count: 7 bytes a pixel in place of 304), and for the one luma pixel that owns
each chroma sample, into the chroma sums too. The order within a pixel is kept by visiting blocks in the stock order;
it is kept **under threads** by giving each thread a band of rows: every thread walks all blocks in the stock order
and writes only the rows it owns, so each pixel still receives its pairs in the stock order and the cap falls on the
same pair. Nothing is approximated: integer sums in a different container.

## What must be preserved (from the stock source and GPT's CAPSULE.md)

- block order: direction 0 then 1, rows then columns; the block window `start = mb*B - B/2 + mv*a/1024`, clipped to
  `[0, W-1) x [0, H-1)` exactly as stock clips it (the last row and column are never written by a block);
- a pair is skipped where the overlap weight is zero or 16 pairs are already held;
- the two samples of a pair: frame A at `p + clip(mv*alpha/1024)`, frame B at `p + clip(-mv*(1024-alpha)/1024)`, the
  clip to the frame in luma, with weights `w*(1024-alpha)` and `w*alpha` (C division, truncating);
- chroma from the LAST luma pixel of each chroma cell, its position `(p >> s) + clipped_luma_offset / (1 << s)`
  (truncating division of the clipped offset);
- a pixel with no pair: `(A*(1024-alpha) + B*alpha + 512) / 1024` at its own position;
- endpoints (alpha 0 or 1024) and scene cuts never reach this code: untouched.

## The build

`mci_accel` gains bit 16 ("fused"): `bidirectional_obmc` + the output stage are replaced by one threaded
scatter-accumulate-and-finish over row bands (bands of whole chroma row groups). A fast inner loop for blocks whose
window and both displaced windows lie inside the frame (no clip can act), the general per-pixel loop otherwise. Bits
1 and 2 (GPT's SIMD cost and two-direction search) are kept; 4 and 8 have nothing left to do when 16 is set. The
patch applies on top of GPT's `ffmpeg.patch` at the pinned FFmpeg 3a5eb94, in its own isolated checkout; the
installed research FFmpeg, Cadence and the shaders are not touched.

## Gate (GPT's, unchanged: `../mci_accel/gate.py`, its fixtures and its stock baseline binary)

- **F1 exactness, small matrix:** the eleven small cases (bars, face, pan, static, cut, the rigid pair, both border
  cases, the 60 fps pan), masks 16:1, 16:4, 19:4, 19:8, 31:4; every Y/U/V byte, count and timestamp equal to stock.
- **F2 block sizes:** both border cases at macroblocks 4, 8, 16, masks 16:1 and 19:4.
- **F3 films:** both complete 1080p windows (shirt 238 outputs, suit 286), masks 19:1, 19:4, 19:8.
- **F4 determinism:** three cases, three repeats at 19:1 / 19:4 / 19:8.
- **F5 a control that can fail:** the cap moved from 16 to 15 pairs, and the chroma owner moved from the last to the
  first luma pixel, each built once: the gate must refuse both on at least one case (else the matrix does not
  exercise what the block claims to preserve, and that is reported as a hole).
- **F6 timing** (GPT's `bench`: warm, three alternating paired rounds, the framemd5 sink, one process at a time):
  stock against mask 19 at 4 and at 8 threads, and GPT's mask 15 at 4 threads re-timed in the same sitting.

KILL: any byte differs and no exact repair is found. A correct slowdown is a failed optimisation and is reported so.

## Predictions (written before the first compile)

1. Exact on F1-F4 at the first or second build (the arithmetic is the stock's; the risks are the border clip and the
   chroma owner at odd sizes).
2. F5: both sabotaged builds are refused by the films; the cap control may pass every small case (16 pairs at one
   pixel needs strongly converging vectors).
3. The fused stage, shirt, 4 threads: **under 2.0 s** against 10.2 s for lists + output in mask 15 (about 17 million
   pair-visits a frame at 1 to 3 ns, over four threads).
4. Whole process, shirt, mask 19 at 4 threads: **under 3.0 s** (stock 23.7 s, mask 15 10.7 s), which is **faster than
   real time** for 24 -> 48 at 1080p on the M5 (the window is 4.96 s of film); at 8 threads under 2.2 s.
5. Not predicted: the NAS. A weaker CPU may not reach real time; that is measured separately if this passes.

## Next job, registered 2026-11-15 14:53 GMT while the timings run: the motion search as an exact wavefront (bit 32)

**Done the same afternoon: [RESULTS.md](RESULTS.md).** Exact; the search 0.36 -> 0.20 s at four threads.

After the fused stage the filter's time at four threads is split evenly: 0.37 s of motion search against 0.39 s of
overlap on the shirt window, and the search uses only two threads (GPT's mask 2: one per direction), each walking
8,160 blocks in row order. The order matters because EPZS takes three predictors from the pair being searched: the
block to the left, the block above and the block above-right (`mv_table[0]`), as read in `search_mv_context`. Its
other predictors come from the two previous pairs' tables, which nothing writes during the search. So block (x, y)
needs exactly: (x-1, y) done, and row y-1 done through x+1. **A wavefront satisfies that with any number of threads:
a thread may search block x of row y once row y-1 has finished block x+1** (all of it at the row's end). Every block
then reads the same predictor values as in the serial order, so every vector is the same. Per-thread scratch
contexts, as mask 2 already has per direction; a progress counter per row.

Gate: the whole matrix of this block again (F1-F4, the coloured crops) with masks 51:1, 51:4, 51:8, plus F4's repeats
at 8 threads five times (a wavefront's failure mode is a race, which may pass once). Control that must fail: the
wait relaxed by one block (row y-1 through x only), which should be refused on some repeat of some case; if nothing
refuses it, the matrix cannot see a race and that is reported.

Predicted: exact; the search on the shirt window from 0.37 s to under 0.20 s at four threads and under 0.13 s at
eight; the filter per pair from 6.3 to about 5.0 ms at four threads. Smaller than this block's step: the search is
already SIMD and the wavefront's rows are short (120 blocks).

## Next job, registered 2026-11-15 16:37 GMT: 4K on the NAS, the overlap stage's bands sized to the cache

Found by the third NAS job: at 4K the fused stage takes 5.4 s at four threads and 4.9 s at six on the i5-9500, while
at 1080p it scales (0.92 to 0.69 s) and on the M5 at 4K it scales too. The bands are `4 x threads` slices of the
frame: at 4K and six threads, 24 bands of 90 rows, each 90 x 3840 x 7 bytes = 2.4 MB of sums, written by every block
that crosses the band, twice (two directions). Six such working sets are 14.5 MB against a 9 MB shared cache.

Change, nothing else: the band height capped (bands of at most 32 rows of whole chroma groups, so 0.86 MB a band at
4K; more bands than `4 x threads` where the frame is tall), each band's blocks found from a per-row index instead of
a walk over all blocks (the walk is 65,280 block tests a band at 4K and would grow with the band count). Order within
a pixel is untouched: bands are disjoint rows and each still takes its blocks in the stock order.

Gate: this block's whole matrix on the M5 and the NAS again. Predicted: exact; the NAS at 4K, six threads, native,
from 6.6 s to under 4.5 s (above real time, 4.96 s of film); 1080p on both hosts within 5% either way; the M5 at 4K
no slower. If the NAS at 4K does not move, the bound is the frames' own traffic (two 12 MB frames read at scattered
offsets), and the next door there is the GPU renderer GPT has already proven exact on the Arc.
