# Exactness and serial timing gate

Registered 2026-11-15, before prototype measurements. `gate.py` prepares inputs,
validates frame records and runs serial measurements; it does not build FFmpeg.
The reference binary needs `mci_profile=1`. The candidate additionally needs
`mci_accel=0..15`: 1 SIMD, 2 direction threads, 4 output-row threads, 8 skipped
overwritten chroma calculations. Zero exercises the candidate's baseline path.

## Fixed inputs

All generated files stay in the supplied external output directory; no media is
committed. `prepare` reads existing `motionstress-20261113` and
`translation-ripple-20261115` scratch trees. Film entries reference the unchanged
119-frame shirt and 143-frame suit windows, preserving their complete history.

```sh
python3 tests/probes/mci_accel/gate.py prepare "$OUT/inputs" \
  --scratch "$SCRATCH" --ffmpeg "$INSTALLED_FFMPEG" --ffprobe "$FFPROBE"
```

Cases: `bars_v9`, `bars_h9`, `face_occluded`, `pan43`, `rigid_frozen`,
`rigid_grain`, flat `static`, frame-6 brightness-inversion `cut`, cropped
`border420` (638x358), `border444` (639x359), `shirt`, `suit`, and `pan43_60`.
The last case reuses `pan43` input bytes at 60fps; other cases double the source
rate. 60fps exercises phases beyond the midpoint. The 420 border has an odd
number of chroma rows; the 444 border has odd full-resolution dimensions.

Synthetic originals are 16-bit. Preparation converts once to 8-bit with the
installed binary's fixed swscale/format conversion, recording commands, tool
hashes, original source hashes and resulting input hashes. Quantization belongs
to fixture construction, not either timed implementation. The rigid pair tests
its quantized 8-bit realization. The 444 case stays 444; other cases are 420.
Prepared files use FFV1. Repeated preparation verifies the existing immutable
manifest and rejects changed bytes. A different recipe needs a fresh directory.

## Exactness matrix

```sh
python3 tests/probes/mci_accel/gate.py check "$OUT/small-check" \
  --fixtures "$OUT/inputs/fixtures.json" --baseline "$BASE" --candidate "$NEW" \
  --configs 0:1,1:1,2:2,4:4,8:1,15:4
python3 tests/probes/mci_accel/gate.py check "$OUT/film-check" \
  --fixtures "$OUT/inputs/fixtures.json" --baseline "$BASE" --candidate "$NEW" \
  --cases shirt,suit --configs 0:1,0:4,15:1,15:4
```

Small defaults: bars_v9/h9, face_occluded, pan43, static, cut, border420/444,
pan43_60. Add the rigid pair with `--cases rigid_frozen,rigid_grain`.
Use `--mb-sizes 4 8 16` initially on both border cases for the three optimized
SAD sizes. A second thread-count slice can use
`--configs 0:1,1:2,2:4,4:2,8:4,15:1,15:2,15:4`; `--repeats 3` checks combined
path determinism. These are selectable bounded matrices, not an implicit
Cartesian expansion across every option.

Commands use bidir/EPZS; decoder/encoder threads are one, filter threads separate.
Source PTS are normalized to the exact input rate; two terminal input frames are
cloned and output capped at 2N (5N/2 at 60fps). This reproduces the established
native MCI reference. Startup/terminal frames are included. Inactive bidir
`aobmc`/`vsbmc` flags are retained, without claiming those branches were exercised.

Rawvideo framemd5 hashes all Y/U/V bytes. The strict parser requires complete v2
records, rawvideo identity, dimensions, stream zero, exact frame counts, byte
sizes, physical PTS, DTS and durations. Reference/candidate semantic headers and
records agree exactly; only software-version text is ignored. Both successful
processes must emit exactly one active MCI_PROFILE with matching pair/draw counts.
All-zero dummy-filter destructor profiles are permitted; malformed, duplicate
active, nonzero inactive and dummy-only profiles fail. This accounts for the
observed baseline graph-construction destructor without accepting missing work.
Each run retains full records, stderr, commands and source/binary hashes.
Summary status stays incomplete until every selected comparison passes. Reruns
invalidate previous summary/per-run completion records before execution.

`controls.py --ffmpeg "$INSTALLED_FFMPEG"` tests hash, timestamp, duration, size,
header, truncation and profiling refusals. Tiny rawvideo controls change one
chroma-only pixel and one luma-only pixel; both must fail comparison. Controls
do not invoke minterpolate or measure acceleration.

## Timing after exactness

```sh
python3 tests/probes/mci_accel/gate.py bench "$OUT/film-timing" \
  --fixtures "$OUT/inputs/fixtures.json" --baseline "$BASE" --candidate "$NEW" \
  --gate "$OUT/film-check/check-summary.json" --cases shirt,suit \
  --configs 15:4 --rounds 3 --warmups 1
```

Timing refuses configurations absent from the successful gate and revalidates
raw evidence, hashes and parameter bindings. One process runs at a time. Both
implementations warm up, then paired AB/BA order alternates. Warmups are excluded.
The consistent sink is rawvideo framemd5: wall/child CPU measurements include
decoding, filters and checksums. Input/binary hashing is outside the timed interval.
Timed runs still require exact records. Keep unrelated workloads idle externally.

External summaries retain samples, min/max/median wall/user/system time, output
FPS and source-duration/wall ratio. MCI_PROFILE times are stage wall microseconds,
not CPU instruction counts; pair/draw counts are included. Stage sums are not
total CPU time. A correct slowdown remains a failed optimization. Mac evidence
does not establish NAS/Arc speed, interpolation quality or GPU equivalence.
Build artifacts should separately retain compiler flags/source provenance; this
harness pins the actual executables by SHA-256.

The benchmark records its current host separately from the exactness host and
requires every warm/timed run to retain the certified stage invocation counts.

## Portable evidence extraction

```sh
python3 tests/probes/mci_accel/summarize.py "$OUT/review-summary" \
  --fixtures "$OUT/inputs/fixtures.json" \
  --checks "$OUT/small-check/check-summary.json" "$OUT/film-check/check-summary.json" \
  --benches "$OUT/film-timing/bench-summary.json"
```

This performs no interpolation or timing. It revalidates completed raw evidence
and emits path-free JSON plus Markdown tables. The compact record retains input,
binary, command, raw framemd5/log and semantic frame-record hashes, without the
large per-frame arrays or absolute/private paths. Timing samples, ranges, medians
and stage counts remain. Omit `--benches` before timing is complete; the report
then explicitly marks timing pending. A tiny mocked-evidence extraction is part
of `controls.py`; it checks that private temporary paths do not enter the result.
