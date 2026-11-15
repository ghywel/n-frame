# Results: FFmpeg's motion-compensated interpolator, exact and faster than real time on a CPU

Local, 2026-11-15. Registered in [PLAN.md](PLAN.md) before any code. Built on GPT's block
([../mci_accel/](../mci_accel/README.md)): its patch, its gate, its fixtures and its stock baseline binary, unchanged.
No installed FFmpeg, shader or Cadence resource is touched; the builds live in their own checkouts of FFmpeg 3a5eb94.

**In one line:** `minterpolate` in its bidirectional MCI mode (the pictures the owner found calmer than High) does its
filter work for 1080p 24 -> 48 in **4.5 ms a source pair on four threads of the M5: 41 times faster than stock, 8.6
times faster than real time, every output byte unchanged**. One thread alone is 2.7 times real time. 4K runs at
twice real time on four threads. Memory falls from 631 MiB to 73 MiB. NAS figures are in their own section.

## What was built

Two bits on GPT's `mci_accel` option, in [fused.patch](fused.patch) (applied on top of GPT's `ffmpeg.patch`):

- **16, the fused overlap stage.** Stock builds, for every luma pixel, a list of up to 32 (vector, weight, frame)
  entries, 304 bytes a pixel, and then only sums each list. Here each accepted pair is added straight into a weighted
  sum, a weight sum and a pair count (7 bytes a pixel), and at the luma pixel that owns each chroma sample into the
  chroma sums. Blocks are walked in the stock order and threads own bands of rows, so each pixel receives its pairs
  in the stock order and the 16-pair cap falls on the same pair. Two inner loops vectorise under clang and gcc (both
  compilers' reports checked): a block's row where no clip can act, and the finishing division, which goes through
  float32 with a short proof in the code that its truncated quotient is the integer one.
- **32, the wavefront search.** Of the pair being searched, a block's EPZS search reads three vectors only (left,
  top, top-right), so block x of row y may start once row y-1 has finished block x+1. Rows are claimed in order per
  direction, each job has its own scratch context, progress is published and awaited eight blocks at a time.

GPT's bit 1 (SIMD cost) still applies. `mci_accel=51` is all three; `19` is the fused stage with GPT's
one-thread-per-direction search.

## Exactness: 288 comparisons on the final binary, all equal to stock

GPT's gate (`gate.py` through [gate_fused.py](gate_fused.py), which only widens its mask range and frame-size table):
every Y, U and V byte, the frame count and every timestamp against the stock scalar binary.

| Matrix | Cases | Configurations (mask:threads) | Equal |
|---|---|---|---:|
| small | GPT's eleven (bars, face, pan, static, cut, rigid pair, both borders, 60 fps pan) | 16:1, 16:4, 19:4, 19:8, 31:4, 51:1, 51:4, 51:8 | 88 / 88 |
| block sizes | both border cases at macroblock 4, 8, 16 | 16:1, 19:4, 51:4, 51:8 | 24 / 24 |
| films | both 1080p windows, complete (238 and 286 outputs) | 19:1, 19:4, 19:8, 51:1, 51:4, 51:8, and GPT's 15:4 | 14 / 14 |
| repeats | three cases, five times each | 19:4, 19:8, 51:8, 51:10 | 60 / 60 |
| coloured edges (new) | six crops of the suit window, at macroblock 4, 8, 16 | 16:1, 19:4, 19:8, 51:4, 51:8 | 90 / 90 |
| film repeats | both films, three times each | 51:8, 51:10 | 12 / 12 |

The first build of each bit was exact (prediction 1 held without a repair). Earlier binaries of the afternoon went
through the same matrices (210 and 131 comparisons, all equal, including GPT's own masks 4, 8 and 15 on the coloured
crops); the table is the final one's.

## Two findings about the gate itself

**GPT's small fixtures are grey.** Ten of the eleven have U = V = 128 in every frame (the eleventh, `cut`, has
chroma of 127 and 128 after its inversion: one code of range), so no chroma error can show in them; only the two
films test colour, and neither tests a chroma cell on a frame edge. The odd-size border cases (638x358 4:2:0,
639x359 4:4:4) therefore proved the luma border and nothing about chroma. [colour_fixtures.py](colour_fixtures.py)
adds six 24-frame crops of the cached suit window with real chroma: 638x358 and 637x357 4:2:0 (the second has a last
chroma cell one luma pixel wide and high), 639x359 4:4:4, 638x359 4:2:2, 639x358 4:4:0, and the first at 60 fps. GPT's
own masks 4, 8 and 15 are exact on them too, so nothing was hiding there; the hole is closed for both blocks.

**The controls that must fail.** Four deliberately wrong builds, each run case by case:

| Sabotage | Refused by | Passed |
|---|---|---|
| cap of 15 pairs instead of 16 | pan43, pan43_60, border444, rigid_grain, suit, colour420, colour444, colour420_60 | the rest, **including the whole shirt window** |
| chroma owned by the first luma pixel of a cell instead of the last | shirt, suit, cut (by its one code of chroma), every subsampled coloured crop (5 of 5) | every flat-chroma case; colour444 (no owner to choose at 4:4:4) |
| wavefront: the wait one block short (three runs a case, 8 threads) | pan43, face_occluded, border444, shirt, suit | rigid_grain (three of three) |
| wavefront: no wait at all | all six cases tried | none |

Prediction 2 was wrong in the comfortable direction: four small cases catch the cap, where I expected perhaps none.
The stale value a search race reads is the previous pair's vector for that block, often the same vector, and the
one-block control still fails on five of six cases.

**A trap on the way, kept.** The first control run showed both sabotaged builds failing at the very same frames, and
the "restored" build failing too. All three were one binary: GNU Make 3.81 compares timestamps to the second and had
called the second and third rebuilds "up to date". The identical failure frames gave it away; rebuilds now remove
the object, the archive and the executable first, and a restored build is byte-identical to the gated one.

## Timing on the M5 (ten cores: four fast, six slow; one process at a time)

### The filter with nothing else in the way (raw source, null sink; [rawbench.py](rawbench.py))

GPT's filter chain and frame cap, the same frames stored uncompressed, `-f null`. Every variant is first checked
equal to stock on the raw source; then one warm-up and five interleaved rounds (4K: three), medians.

| 1080p 24 -> 48, shirt (119 source frames, 4.96 s of film) | Wall | CPU time | x real time | x stock | Filter per source pair | Peak memory |
|---|---:|---:|---:|---:|---:|---:|
| stock | 23.82 s | 23.8 s | 0.21 | 1 | 197.9 ms | 631 MiB |
| GPT's mask 15, 4 threads | 10.38 s | 15.7 s | 0.48 | 2.3 | 86.0 ms | 632 MiB |
| mask 51, 1 thread | 1.85 s | 1.9 s | 2.69 | 12.9 | 15.1 ms | 73 MiB |
| mask 51, 2 threads | 0.96 s | 1.9 s | 5.17 | 24.8 | 7.7 ms | 73 MiB |
| **mask 51, 4 threads** | **0.577 s** | 2.2 s | **8.59** | **41.3** | **4.5 ms** | 73 MiB |
| mask 51, 8 threads | 0.468 s | 3.3 s | 10.61 | 50.9 | 3.6 ms | 73 MiB |
| mask 51, 10 threads | 0.426 s | 3.5 s | 11.66 | 55.9 | 3.3 ms | 73 MiB |
| mask 19 (no wavefront), 4 / 8 threads | 0.729 / 0.649 s | 2.1 / 2.6 s | 6.81 / 7.65 | 32.7 / 36.7 | 5.8 / 5.1 ms | 73 MiB |

The suit window (143 source frames) gives the same ratios: stock 28.64 s; mask 51 at 1 / 4 / 8 / 10 threads 2.23 /
0.698 / 0.565 / 0.522 s (4.6 ms a pair at four threads, 8.6 times real time). The budget for 24 -> 48 is 41.7 ms a
source pair. Where stock's 198 ms went and where it is now, at four threads: search 37.5 -> 1.7 ms, overlap lists
plus output 161.8 -> 2.9 ms. Total CPU work is under a tenth of stock's.

| 4K 24 -> 48 (the shirt window upscaled to 3840x2160: a cost measure, not a picture sample) | Wall | x real time | x stock | Filter per source pair | Peak memory |
|---|---:|---:|---:|---:|---:|
| stock | 105.0 s | 0.05 | 1 | 873.5 ms | 2,502 MiB |
| mask 51, 1 thread | 8.23 s | 0.60 | 12.8 | 67.7 ms | 268 MiB |
| **mask 51, 4 threads** | **2.46 s** | **2.02** | 42.7 | 19.6 ms | 268 MiB |
| mask 51, 8 threads | 1.92 s | 2.59 | 54.8 | 15.1 ms | 268 MiB |
| mask 51, 10 threads | 1.85 s | 2.68 | 56.7 | 14.5 ms | 268 MiB |

### GPT's registered pipeline (FFV1 decoded on one thread, the filter, MD5 of every output frame)

Warm, three alternating paired rounds, medians:

| Clip | Stock | GPT's mask 15, 4 threads | Mask 19, 4 threads | Mask 51, 4 threads | Mask 51, 8 threads |
|---|---:|---:|---:|---:|---:|
| shirt | 23.8 s | 10.69 s (2.23x) | 3.218 s (7.38x) | 3.221 s (7.39x) | 3.218 s (7.40x) |
| suit | 29.0 s | 13.33 s (2.18x) | 3.889 s (7.47x) | 3.896 s (7.42x) | 3.901 s (7.59x) |

1.5 times real time, and flat across every fused variant: **this pipeline no longer measures the filter.** The
filter's stages take about 0.55 s of the 3.2 s; the rest is the FFV1 decoder on its one thread (about 27 ms a 1080p
frame). That is the reason for the decode-free measure above.

## Predictions against results

| Registered | Result |
|---|---|
| 1. exact at the first or second build | held: first build, both bits |
| 2. the films refuse both sabotages; the cap may pass every small case | half wrong: the shirt window passes the cap sabotage; four small cases refuse it |
| 3. fused stage under 2.0 s on the shirt window at four threads | held: 0.34 s (first build 0.44 s) |
| 4. whole process under 3.0 s in GPT's pipeline, faster than real time | **missed as registered**: 3.2 s (still 1.5x real time); the floor is the pipeline's FFV1 decoder, not the filter |
| wavefront: search under 0.20 s at four threads, under 0.13 s at eight | 0.202 s and 0.172 s: **missed** at eight (a wavefront moves at the pace of its slowest row; six of the ten cores are slow) and on the line at four |
| wavefront: filter about 5.0 ms a pair at four threads | held: 4.5 ms |

## What this is not

Two five-second 1080p windows and an upscale of one; 8-bit, the bidirectional EPZS path with 16-pixel blocks (other
block sizes and four chroma samplings are tested for exactness, not timed). Not playback: a real pipeline adds its own
decode and whatever follows the filter. No new claim about how the pictures look: they are stock's pictures, byte
for byte, and the owner's "calmer" verdict was on one shirt shot.
