# Results: the MCI reference's overlap stage as exact threaded sums

Local, 2026-11-15. Registered in [PLAN.md](PLAN.md) before any code. Built on GPT's block
([../mci_accel/](../mci_accel/README.md)): its patch, its gate, its fixtures and its stock baseline binary, unchanged.
No installed FFmpeg, shader or Cadence resource is touched; the build lives in its own checkout of FFmpeg 3a5eb94.

**In one line:** FFmpeg's `minterpolate` (bidirectional MCI, the pictures the owner found calmer) now runs its filter
work for 1080p 24 -> 48 in **6.3 ms a source pair on four threads of the M5, 30 times faster than stock and 6.3 times
faster than real time, with every output byte unchanged**; on one thread it is still 2.4 times real time; its memory
falls from 631 MiB to 73 MiB.

## What was built

`mci_accel` bit 16 ([fused.patch](fused.patch), applied on top of GPT's `ffmpeg.patch`; 258 lines). Stock builds, for
every luma pixel, a list of up to 32 (vector, weight, frame) entries, 304 bytes a pixel, and then only sums each list.
The fused stage adds each accepted pair straight into a weighted sum, a weight sum and a pair count (7 bytes a pixel),
and at the luma pixel that owns each chroma sample into the chroma sums. Blocks are walked in the stock order and
threads own bands of rows, so each pixel receives its pairs in the stock order and the 16-pair cap falls on the same
pair. Two inner loops vectorise (checked in the compiler's report): the row of a block whose pixels cannot be clipped,
16 lanes, and the finishing division. The division goes through float32 with a short proof in the code that the
truncated quotient is the integer one (numerator under 2^20, divisor under 2^12, quotient at most 255); it falls back
to the integer division if the file is ever compiled with fast-math.

Use: GPT's masks 1 (SIMD cost) and 2 (one search thread per direction) still apply; `mci_accel=19` is all three.

## Exactness: 210 comparisons, all equal to stock

GPT's gate (`gate.py` through [gate_fused.py](gate_fused.py), which only widens its mask range and frame-size table):
every Y, U and V byte, the frame count and every timestamp against the stock scalar binary.

| Matrix | Cases | Configurations (mask:threads) | Equal |
|---|---|---|---:|
| F1 small | GPT's eleven (bars, face, pan, static, cut, rigid pair, both borders, 60 fps pan) | 16:1, 16:4, 19:4, 19:8, 31:4 | 55 / 55 |
| F2 block sizes | both border cases at macroblock 4, 8, 16 | 16:1, 19:4 | 12 / 12 |
| F3 films | both 1080p windows, complete (238 and 286 outputs) | 19:1, 19:4, 19:8 (and GPT's 15:4) | 8 / 8 |
| F4 determinism | three cases, three repeats | 19:1, 19:4, 19:8 | 27 / 27 |
| Coloured edges (new) | six crops of the suit window, below | 16:1, 19:4, 19:8 and GPT's 4:4, 8:1, 15:4, at macroblock 4, 8, 16 | 108 / 108 |

The first build was exact on F1-F4 (prediction 1 held without a repair). The final binary (the vectorised build) was
run through the whole table again; the numbers above are its.

## Two findings about the gate itself

**GPT's small fixtures are grey.** Ten of the eleven have U = V = 128 in every frame (the eleventh, `cut`, has
chroma of 127 and 128 after its inversion: one code of range), so no chroma error can show in them; only the two
films test colour, and neither tests a chroma cell on a frame edge. The odd-size border cases
(638x358 4:2:0, 639x359 4:4:4) therefore proved the luma border and nothing about chroma. [colour_fixtures.py](colour_fixtures.py)
adds six 24-frame crops of the cached suit window with real chroma: 638x358 and 637x357 4:2:0 (the second has a last
chroma cell one luma pixel wide and high), 639x359 4:4:4, 638x359 4:2:2, 639x358 4:4:0, and the first at 60 fps. The
fused stage and GPT's own masks 4, 8 and 15 are all exact on them (108 of 108), so nothing was hiding there; the hole
is closed for both blocks.

**F5, the controls that must fail.** Two deliberately wrong builds, each run case by case at 19:4:

| Sabotage | Refused by | Passed |
|---|---|---|
| cap of 15 pairs instead of 16 | pan43, pan43_60, border444, rigid_grain, suit, colour420, colour444, colour420_60 | the rest, **including the whole shirt window** |
| chroma owned by the first luma pixel of a cell instead of the last | shirt, suit, cut (by its one code of chroma), and every subsampled coloured crop (5 of 5) | every flat-chroma case; colour444 (no owner to choose at 4:4:4) |

So the cap is exercised by eight cases and the chroma owner by eight; prediction 2 was wrong in the comfortable
direction (four small cases catch the cap, where I expected perhaps none).

**A trap on the way, kept:** the first control run showed both sabotaged builds failing at the very same frames, and
the "restored" build failing too. All three were one binary: GNU Make 3.81 compares timestamps to the second and had
called the second and third rebuilds "up to date". The identical failure frames gave it away; the rebuilds now remove
the object, the archive and the executable first, and the restored build is byte-identical to the gated one.

## Timing on the M5 (ten cores, one process at a time)

### GPT's registered pipeline (FFV1 decoded on one thread, the filter, MD5 of every output frame)

Warm, three alternating paired rounds, medians (ranges in the portable record):

| Clip | Stock | GPT's mask 15, 4 threads | Fused mask 19, 4 threads | Fused mask 19, 8 threads |
|---|---:|---:|---:|---:|
| shirt | 23.5-24.0 s | 10.81 s (2.22x) | **3.21 s (7.33x)** | 3.22 s (7.36x) |
| suit | 28.3 s | 12.53 s (2.26x) | **3.84 s (7.36x)** | 3.84 s (7.35x) |

1.55 times real time. **This pipeline no longer measures the filter:** its stages take 0.77 s of the 3.21 s; the rest
is the FFV1 decoder on its one thread (about 27 ms a 1080p frame), which is why 8 threads change nothing.
Prediction 4 (whole process under 3.0 s) is therefore **missed as registered** (3.21 s), for a reason outside the
filter; prediction 3 (the fused stage under 2.0 s at 4 threads) held with room: 0.44 s.

### The filter with nothing else in the way (raw source, null sink; [rawbench.py](rawbench.py))

The same filter chain and frame cap, the same frames stored uncompressed, `-f null`. Every variant is first checked
equal to stock on the raw source; then one warm-up and five interleaved rounds, medians:

| 1080p 24 -> 48, shirt (119 source frames, 4.96 s) | Wall | CPU time | x real time | Filter per source pair | Peak memory |
|---|---:|---:|---:|---:|---:|
| stock | 23.59 s | 23.6 s | 0.21 | 196.0 ms | 631 MiB |
| GPT's mask 15, 4 threads | 10.23 s | 15.5 s | 0.49 | 84.8 ms | 631 MiB |
| fused, 1 thread | 2.04 s | 2.1 s | 2.43 | 16.7 ms | 73 MiB |
| fused, 2 threads | 1.07 s | 2.1 s | 4.63 | 8.7 ms | 73 MiB |
| **fused, 4 threads** | **0.79 s** | 2.3 s | **6.30** | **6.3 ms** | 73 MiB |
| fused, 8 threads | 0.70 s | 3.0 s | 7.11 | 5.6 ms | 73 MiB |

The suit window gives the same ratios (stock 28.49 s; fused 2.46 / 1.32 / 0.96 / 0.85 s at 1 / 2 / 4 / 8 threads,
6.4 ms a pair at four). The budget for 24 -> 48 is 41.7 ms a source pair. At four threads the time is now split
almost evenly: motion search 0.37 s, the fused overlap stage 0.39 s (it was 8.1 s of lists plus 10.9 s of output in
stock, and 8.1 + 1.7 s in mask 15). Total CPU work is a tenth of stock's.

What these numbers are not: playback, or a film's worth of footage. Two five-second 1080p windows, 8-bit 4:2:0, the
bidirectional EPZS path with 16-pixel blocks; a real pipeline adds its own decode and whatever follows.
