# Bounded real-footage reconstruction prospecting

The older `tests/prospect.py` ranks spatial disagreement in a flow field. This companion withholds every second
source frame, reconstructs it with the shipped High tier, and compares it with the original and a GPU linear blend.
Both are candidate finders. Neither can establish a defect from a scalar spike alone.

Use the patched FFmpeg/libplacebo build and a Python with numpy. `FFMPEG` and `FFPROBE` override the default build
paths. Supply an **external** output folder; footage and manifests must stay outside git. The sampling command
consumes `content.py`'s existing private clips.json, choosing the first title in each of its five classes. It makes
one accurate, bounded input seek per title, decoding five minutes centred at the runtime midpoint to a local
native-size lossless video-only working file. It refuses to fetch a completed dataset again.

```sh
python3 tests/probes/prospect/reconstruct.py controls "$OUT"
python3 tests/probes/prospect/reconstruct.py sample "$CONTENT_MANIFEST" "$OUT"
python3 tests/probes/prospect/review.py timing "$OUT"
python3 tests/probes/prospect/reconstruct.py scan "$OUT"
python3 tests/probes/prospect/review.py sheets "$OUT"
python3 tests/probes/prospect/review.py confirm "$OUT" film FRAME
```

On macOS the driver sets the two documented MoltenVK environment guards. Announce heavy GPU work in the ledger
before running, and do not overlap another person's timing jobs. These scans measure quality, not rendering speed.
No shader is generated or changed: the exact committed High file is copied beside the renders and SHA256 recorded.

Each full local window gets a width-640 (never upscaled), 8-bit YUV420 reference at its source rate. A final unpaired
frame may be dropped explicitly. Render naturally; consume output by frame index, never compare rounded timestamps.
Actual decoded stream counts must match and retained frames must stay above the frozen 40 dB alignment floor.
Local FFV1 packet counts accelerate the preparation count check; the three actual decoded streams are still checked
independently during measurement. `review.py timing` rejects nonuniform native packet intervals beyond millisecond
container rounding. The first study's five windows passed; VFR/interlace/HDR need a separate protocol.

`metrics.json` retains each evaluable midpoint's raw numbers and flags, including excluded rows. `ranked.json`
contains overlapping exclusion counts, exclusive bucket counts, and two event lists. The relative list finds an
unusual loss of advantage against linear; the absolute list finds large residuals among eligible rows. Events within
one second are deduplicated within each list. The same event can appear in both lists. `summary.json` combines titles
without their private identities. Sheet rows are chronological; columns are **original | High | linear** and the
adjacent sheet.json maps rows to exact frame indices and measurements. A native sheet shows the candidate and two
neighbouring withheld moments. No labels are painted into footage.

Cut score, held-frame and extreme-change rules are imperfect guards, not ground-truth labels. Inspect transition,
fast-motion and camera-shutter explanations; keep a rejected candidate's raw record and the rejection reason.
Full-frame squared error rewards blur; require SSIM/inspection as well as a linear loss before calling a regression.
A local grid witness prevents full-frame averages concealing small damage, but is still a selected measurement.
The original [pre-registration](PREDICTION.md) lists the thresholds and falsifiable predictions.

`confirm` extracts three seconds **from local native footage**, preserving the original decimation parity, renders
High twice and linear, and reads the same withheld-frame measurement. It writes `native-FRAME/confirmation.json`
and a sheet. Native confirmation has its own 3 s exclusion context; its percentile bucket is not the original 300 s
bucket. Reduced-resolution rankings are not scale-invariant. Run normal-rate interpolation separately before claiming
that a doubled-motion decimation failure occurs in ordinary playback; that playback has no withheld ground truth.

The additional `fault_control.py OUT` corrupts one withheld synthetic GPU output while preserving retained frames;
it must rank that frame first without tripping alignment. `pan_witness.py ROOT FRAME` is an exploratory independent
global-translation/photometric check on a selected candidate. Its model can fail; it does not change the frozen rank.
`playback.py OUT` makes the TV witness's normal 25->60 comparison with retained checks and a watch copy; it deliberately
requires that 25 fps witness. Preview columns and source bracketing are saved in JSON; no inserted-frame truth exists.
