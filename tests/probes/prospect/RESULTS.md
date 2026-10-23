# Reconstruction prospecting: first bounded round

Instrument: [reconstruct.py](reconstruct.py). Frozen discovery rules and amendments made before footage renders:
[PREDICTION.md](PREDICTION.md). Data are external, under `$NP_SCRATCH/prospect-20261023/`; source identities and
absolute source paths are in the private `sources.json`, not this repository. No shader changes.

## Instrument controls, before footage

CPU affine-translation midpoint oracle: zero residual; identity SSIM8 = 1. A deliberately corrupted local patch
produces a large residual, and a deliberately bad reconstruction ranks first in the scorer control. Cut/hold/low
signal/extreme-change labels remain outside that rank. Actual decoded black/white cut: scdet >= 8 on exactly the
known transition, zero elsewhere. Actual near-hold/noise RMS is below the frozen floors. Both short/long frame counts
and a shifted moving reference are refused.

Actual GLSL/MoltenVK moving synthetic, 72 frames: maximum retained-frame RMS 0.275 code values; deliberately pairing
the same GPU output to reference two frames ahead gives minimum RMS 13.70, and the alignment guard refuses it.
Repeated after adding the tail-count and affine controls, all passed. These controls establish the measurement
path, not an assertion that all real scene cuts or held drawings are detected.

Instrument amendments: decode bounded source windows once to local native-size FFV1 rather than compressed packet
copy (exact seek origin); trim a final unpaired frame explicitly; do not exclude every member of a tie at the
97.5th percentile. Before the final sample manifest existed, an early scan launch refused with FileNotFoundError;
no renders/scores resulted. This was an orchestration mistake, not a shader failure.

## Interpretation

Luma RMS uses 8-bit code values; PSNR = 20 log10(255/RMS). `ssim8` uses non-overlapping 8x8 luma blocks, population
moments and the usual C1/C2 constants. It is not ffmpeg's overlapping SSIM. Local witnesses use a 16x16 spatial grid;
its cells are not fixed 16-pixel squares. Bottom/right partial cells are omitted from this local statistic only.
Raw and excluded frames remain in metrics.json; counts in ranked.json use an exclusive bucket priority, with
separate overlapping counts too. Robust scores are rankings, not p-values or calibrated defect probabilities.

A source window is a selected commercial programme's five minutes centred on its runtime midpoint; these are
purposive content classes, not a random census. No source is decoded or hashed end-to-end over the NAS. Once copied,
all scans and confirmations use local footage. Reduced-width scan candidates need native-size inspection, repeat,
and normal-rate playback confirmation before attributing a production failure or changing a shader.

Footage measurements and inspection results follow when the run completes.

## First completed sources (interim, before native confirmation)

Film: 3595 evaluable midpoints, 1480 eligible; the raw top 20 errors are all excluded by the frozen guards. Median
eligible advantage over linear: +5.20 dB. Relative candidate 4991 (208.166 s into the copied window) loses 8.74 dB to
linear, SSIM8 .9711 versus .9937, with a local coat-area excess. The other four inspected events are vigorous
rotation/action and remain hard-motion examples rather than shader-defect leads. These show the change guard does
not remove all rapid motion: its statistic is image change, not velocity.

TV: 3749 evaluable midpoints, 2022 eligible, median advantage +3.89 dB. Relative candidate 73 (2.920 s into the window)
loses 6.02 dB, SSIM8 .9882 versus .9951, on a gently moving shot of a toaster and bottle. Candidate 101 is nearby in the
same shot. Candidate 183's SSIM8 gap is below the .005 regression threshold. The two absolute-error candidates show
arm motion: High improves SSIM8 over the visibly ghosted linear image. None is yet a native-size confirmed defect.

All five native windows' packet intervals agree with their nominal 23.976/25 fps within millisecond rounding. The
TV file lacks a field-order tag; a 125-frame centre sample with idet reports 124 progressive, one undetermined,
zero TFF/BFF in its multi-frame classification. This short check is supporting evidence, not a full-window proof.

Preparation was restarted to replace an unnecessarily slow single-threaded count decode with FFV1 packet counting.
A child process survived the first stop and briefly overlapped the new preparation; both were stopped, and the
reference regenerated with one writer before any scoring. Decoded counts and retained-frame checks then passed.
The first helper name shadowed Python's inspect module and failed at import; renamed review.py before use. These
orchestration errors produced no accepted quality measurements.
