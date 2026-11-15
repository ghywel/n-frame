# Scalar MCI renderer capture, version 1

Registered 2026-11-15 before execution. The isolated exporter and capture pipeline
have since run successfully; execution results belong in `GPU-RESULTS.md`, separate
from this format specification. `capture.py` transforms only pristine
`vf_minterpolate.c` from FFmpeg `3a5eb94`, SHA256
`42e776a33821d7e08a20371a554513bca17ee427aac123ec0923bc4cbefad8e7`.
It writes a separate source file; it does not install FFmpeg or edit the input.
Build the generated source in an isolated checkout.

The export happens after the original scalar `bidirectional_obmc` and
`set_frame_data` calls, before their source frames or motion arrays change. Sources
are `frames[1]` (A) and `frames[2]` (B); raw maps are, in order,
`frames[2].blocks[].mvs[0]` and `frames[1].blocks[].mvs[1]`. The golden is the actual
scalar output AVFrame. No regenerated, newly estimated or negated forward field
is substituted for the consumed backward map.

Capture is disabled unless both `MCI_CAPTURE_PREFIX` and `MCI_CAPTURE_DRAWS` are
set. Draw indices are **one-based actual bidirectional MCI draws**, excluding
retained instants and scene-cut early returns, not output-frame indices. Select
at most 16 strictly increasing positive indices, for example `1,25,37`. Each
selected draw creates `PREFIX-0000000001.bin` etc. Capture errors make FFmpeg fail;
the Python wrapper also requires every requested file and complete output records.
Disabled capture does not change output pixels. This is not a timing claim.

## Binary contract

One file contains a 64-word header followed by its payload. Every word is exactly
32 bits, little-endian. Source and golden samples are uint32 values in [0,255],
including all Y/U/V planes. Motion components are signed int32 bit patterns.
Offsets below are **words relative to the payload**, not bytes or file offsets.
No padding/trailer is allowed; the total length is `4*(64+payload_words)`.

| Header word(s) | Meaning |
|---|---|
| 0 | Magic `0x3149434d`, bytes `MCI1` |
| 1, 2 | Version 1, header words 64 |
| 3 | Payload word count |
| 4, 5 | Full width W, height H |
| 6, 7 | Macroblock B (4/8/16), search_param (32 in v1) |
| 8 | Integer alpha, **1..1023** |
| 9, 10, 11 | Chroma horizontal/vertical log2 subsampling, planes=3 |
| 12, 13, 14 | `floor(W/B)`, `floor(H/B)`, their product |
| 15 | Flags=1: scalar stock renderer, 8-bit planar source |
| 16, 17 | Draw index, uint64 low/high words |
| 18, 19 | Source A PTS, signed int64 low/high two's-complement words |
| 20, 21 | Source B PTS, same representation |
| 22, 23 | Output PTS, same representation |
| 24, 25 | Positive input time-base numerator/denominator |
| 26, 27 | Positive output time-base numerator/denominator |
| 28, 29, 30 | Offsets of source A, source B, CPU golden |
| 31, 32 | Offsets of vectors, overlap table |
| 33, 34, 35 | Y/U/V plane sample counts |
| 36 | Vector word count, `4*b_count` |
| 37 | Table word count, `4*B*B` |
| 38 | P = sum of the three plane counts |
| 39, 40, 41, 42 | ALPHA_MAX=1024, format tag, pair cap=16, table side=2B |
| 43 | Scene-change flag=0 |
| 44..63 | Reserved; must be zero |

Format tag 1 is 8-bit `yuv420p`, with hsub=vsub=1 and chroma dimensions
`ceil(W/2)` by `ceil(H/2)`. Tag 2 is 8-bit `yuv444p`, hsub=vsub=0. All plane
arrays are row-major and tightly packed. Copy only active row samples from the
AVFrame, honoring its signed linesize; do not export allocator padding.

Payload order is A planes Y,U,V; B planes Y,U,V; golden planes Y,U,V;
then the direction-0 raw B-to-A map, direction-1 raw A-to-B map, and table.
Each map is row-major blocks with consecutive x,y components. Exact offsets are
`0, P, 2P, 3P, 3P+4*b_count`, respectively. Payload words are
`3P+4*b_count+4B*B`. The table is the exact selected `obmc_tab_linear` entry,
row-major. SHA256 of its **little-endian uint32 representation** is:

| B | Table SHA256 |
|---|---|
| 4 | `0b058376e1c422e7b431d0689b8f5004a3350aa4a0739ef0117b5e2d344db670` |
| 8 | `c89ee038f51390188a6f72bae96e19faf1503f069f4e83a0a1102964dcffc444` |
| 16 | `b7ad253622fccb1916f436b772b2905af7a6afb24d48e52faacff5b5290a39f7` |

Readers must reject unsupported flags/formats, mismatched dimensions/counts,
noncanonical offsets, unexpected table values/hash, values outside 8-bit range,
motion outside the proved search/global anchor bounds, trailing/truncated bytes,
invalid PTS/phase relationships, zero draw index, and nonzero reserved words.
Version 1 caps files at 256 MiB and dimensions at 8192; this is a bounded proof
format, not an arbitrary-video interchange standard. PTS/alpha validation must
reproduce stock integer rescaling/phase rounding, not substitute floating time.
Reject ratios or timestamps that overflow the original signed-int64 rescale
factors, scaled A PTS, source interval, rescaled output PTS or phase numerator;
arbitrary-precision validator arithmetic must not certify undefined C arithmetic.

## Evidence boundaries and execution

The capture path is entered only after stock endpoint and scene-cut bypasses.
Version 1 therefore provides **no endpoint or cut-rendering equivalence evidence**.
A replay kernel may have defensive endpoint code, but it is not exercised here.
Full timing/count/endpoint evidence remains in the separate CPU gate. Requested
draws are exported while processing the full selected input history.

Generate the isolated source with:

```sh
python3 tests/probes/mci_accel/capture.py source ORIGINAL.c CAPTURE.c
```

The `run` action uses a separately built capture FFmpeg, normalized input
PTS, the registered stock bidir/EPZS options, two cloned tail frames and a fixed
output count. It emits all-plane framemd5 records, complete stderr and a manifest
only after successful exit, exact source/output timing checks and every requested
capsule passing `validate_capsule(path)`. Source video, source pair identities,
input/output PTS, capsule hashes, generated source hash, executable hash and exact
command remain in external scratch. These captures must not be committed as film
data. A failed attempt leaves incomplete status; use a fresh output directory.

```sh
python3 tests/probes/mci_accel/capture.py run INPUT.mkv FRESH_OUT \
  --ffmpeg CAPTURE_FFMPEG --ffprobe FFPROBE \
  --original-source ORIGINAL.c --capture-source CAPTURE.c \
  --draws 5 --mb-size 16
```

Output defaults to exact doubling. `--fps 60` is available for a fixture whose
input duration gives an integral output count. The manifest identifies each
captured source's normalized input index, original frame index and tail-clone
status, and binds its golden bytes to the actual emitted rawvideo frame checksum.

The portable GPU replay consumes this same contract. Matching its golden proves
rendering equivalence on the captured samples, not a new estimator's accuracy,
full-stream playback, or a GPU speedup. Golden data stays CPU-side during replay.
