# Bars, fast pans and translating faces — 2026-11-13

**Useful experimental gains, not a replacement for Cadence High.** The combined variant repairs much of the
moving facial detail and two registered pans. It still creates boundary fragments, leaves the difficult bars
largely broken, and loses 0.120 dB on the interior reading of O3. That exceeds the registered 0.1 dB replacement
limit. Shipped High and Cadence's resource graphs are unchanged.

Baseline is High at `474d70c`, including GLOBAL_GAIN=2. Its generator reproduced the shipped file byte for byte.
The new tests contain 17 analytic scenes and two photographic-plane cases, independently sampled at 24 and
60 fps. They cover horizontal/vertical/diagonal bars, nonperiodic boundary markers, stationary and moving
backgrounds, rails occluding a moving face, low contrast, two fast pans and three off-grid pan holdouts.
Definitions and limitations: [SCENES.md](SCENES.md), [PHOTO-PREDICTION.md](PHOTO-PREDICTION.md).

## What the experiments changed

High samples an A-indexed displacement field at the output position. If the output pixel is p and its phase is t,
the source coordinate should instead satisfy `q + t F_A(q) = p`, with the other endpoint at `q + F_A(q)`.
Sampling `F_A(p)` is exact for spatially constant displacement but approximate near a motion boundary.

`inverse2` proposes two fixed-point updates and accepts only lower forward reprojection error. Both endpoints
use the same selected vector. It improves some facial features, but the first inspected crop has rougher contour
tears. Two different visible-layer candidates can both have exactly zero reprojection error: solving the equation
does not solve visibility. [controls.py](controls.py) records that counterexample and a smooth affine case.

`inverse-data` additionally requires a strict reduction in the same full-resolution 3x3 endpoint-patch error,
using the adopted global gain for matching only. This reduces the analytic face's visible tearing and preserves
the feature gain. It still cannot decide visibility at occlusions. See [INVERSE-GUARD.md](INVERSE-GUARD.md).

`global-fullres` tests High's existing global displacement candidates against 256 full-resolution samples. A
candidate needs low residual and broad improvement over zero motion before it can bypass the coarse Moire veto.
On refusal the old search/gate remains, subject to the existing history state: a preceding accepted candidate can
change the next pair's temporal decision. This is evidence of a pan, not an alias-proof certificate.
See [GLOBAL-PREDICTION.md](GLOBAL-PREDICTION.md) for thresholds and counterexamples.

`combined` composes those last two changes without retuning. The isolated variants and their combination were
all rendered on the new suite. Generated shaders are reproducible through [build.py](build.py); no shipped source
was hand-edited. The combined file has SHA256
`3c02233f737645c3119f19d5730526905f0cd32a880207f8bd7cc9e591e20f2d`.

## New stress results

All values below are dB, higher is better. New-suite PSNR is computed from mean squared error across the 16
interior synthesized frames. The feature mask is declared from scene geometry/source imagery, not the error map.
These grayscale tests do not cover chroma aberrations, natural head rotation or expression change.

| Case | High ROI | Combined ROI | High feature | Combined feature |
|---|---:|---:|---:|---:|
| Analytic face, +32 px/source frame | 29.725 | 32.235 | 36.397 | 38.318 |
| Same face, background -12 | 29.497 | 31.225 | 50.670 | 58.645 |
| Photographic plane, +32 | 28.117 | 32.754 | 30.311 | 42.816 |
| Photographic plane, background -12 | 28.219 | 31.270 | 30.957 | 45.227 |
| Whole-scene pan, +40 | 23.562 | 31.910 | 23.562 | 31.910 |
| Mixed-detail pan, +48 | 15.359 | 21.987 | 15.359 | 21.987 |
| Vertical bars, period 9, speed 24 | 11.657 | 11.458 | 12.665 | 12.379 |
| Vertical bars, period 24, speed 32 | 13.248 | 13.184 | 14.124 | 14.060 |
| Horizontal bars, period 9, speed 16 | 12.999 | 12.830 | 14.389 | 14.075 |
| Horizontal bars, period 24, speed 20 | 14.207 | 14.076 | 15.255 | 15.296 |
| Diagonal bars | 10.755 | 10.729 | 11.845 | 11.808 |

Static controls are unchanged. The slow face gains 0.235 ROI dB. The occluded face gains 0.549 ROI dB but its
feature score stays at about 23.17 dB: the rails still cause serious errors. Bars remain poor, with some losses.
Their finite boundary markers make the true motion distinguishable globally; a periodic interior alone still
admits multiple shifts. Inverse transport cannot correct a spatially constant wrong period alias.

The isolated global witness gains 8.240 dB on the +40 pan and 5.166 dB on the +48 mixed pan. Combined gains are
8.348 and 6.628 dB respectively; both now exceed linear blending (24.584 and 16.150 dB). **The witness does
nothing on the +37, +43 and +45 holdouts.** Combined slightly loses there (-0.054, -0.015, -0.117 dB), through its
warp change. The existing proposal grid is too coarse for a general pan fix.

Post-result CPU exploration explains why merely refining the winning global candidate is insufficient. The +37
and +43 pans can refine from the 40-pixel seed. On mixed +45, the best coarse seed is in the wrong basin; the
second-ranked seed at 48 pixels can refine to the truth. This is an unimplemented next experiment, not a GPU
result. Actual coarse dimensions matter: 640x360 rounds to 40x23, so the vertical grid step is 7.826 pixels.

### The visual failure is real

Worst-feature photographic crops were inspected at output frames 14 (`photo_fast`) and 7 (`photo_counterpan`),
alongside truth and High. Eye/mouth duplication improves markedly. However, the combined output creates new
jagged fragments around parts of the upper/left elliptical boundary. **The photographic visual gate fails.**
The ROI worst-one-percent RMS falls by 36.80% and 35.76%, yet does not expose this thin-contour defect adequately.
The ellipse is a synthetic compositing boundary, not anatomical segmentation; some source background moves
inside it. The result supports an interior-detail improvement in these controlled translations, not a general
claim that faces now interpolate cleanly.

## Wider gates and cost

Fresh High, inverse2 and combined runs cover all 45 existing ladder cases, with whole-frame and region logs,
and both historical and interior readings. Every log has exactly frames 1–60; the scorer rejects missing,
duplicate and nonfinite records. This ladder uses mean per-frame PSNR, unlike the new suite's PSNR of mean MSE.

| Variant | Worst case | Whole-frame loss | Interior loss | Cases losing >0.1 dB |
|---|---|---:|---:|---:|
| inverse2 | O3_osc_hard | -0.148 | -0.156 | 1 |
| combined | O3_osc_hard | -0.115 | -0.120 | 1 |

Region readings reach the same verdict (combined O3 -0.116 / -0.121). No case loses over 1 dB. Combined's
40-dB-capped headline mean gains 0.143 dB, or 0.135 on the interior reading; this does not cancel the losing case.
The isolated inverse-data/global variants did not each receive the full old ladder and should not inherit the
combined variant's results.

Six previously cached three-second footage windows were selected before rendering; there were no new NAS reads.
Decimate/reconstruct scoring excludes retained frames and checks exact output counts and retained alignment.

| Window | Combined PSNR delta | SSIM8 delta | Worst-one-percent RMS change |
|---|---:|---:|---:|
| film1, 2986.7 | +0.004 dB | +0.000028 | -0.07% |
| film1, 3055.7 | +0.212 dB | +0.003338 | +0.17% |
| tv1, 216.0 | +0.029 dB | +0.000802 | +0.20% |
| tv1, 241.1 | +0.086 dB | +0.000184 | -0.42% |
| cg1, 862.4 | -0.010 dB | +0.000210 | +0.80% |
| cg1, 947.9 | -0.030 dB | +0.000269 | +0.68% |

SSIM8 is the script's nonoverlapping 8x8 grayscale statistic, not FFmpeg SSIM. Lower tail RMS is better. These
small mixed changes do not establish a broad footage gain and are not the full 40-window content gate.

One warm-up per shader followed by three interleaved timing rounds on the same cached source (180 output frames):
High median 5.47075 s, combined 5.73167 s, **+4.77%** (30.393 to 31.843 ms/output). This measures the full warmed
FFmpeg process/decode/GPU/null-sink pipeline on this arm64 Mac. It is not isolated GPU time, an Intel Arc result,
or native Cadence Metal timing. The data guard adds up to 54 full-resolution endpoint reads per output pixel;
the global witness adds one pass. Further cost reduction is untested.

## Measurement controls and record

- Initial LINEAR/pan_mixed scoring was refused at 2.9208 DN retained-frame RMS. The images at common instants
  were identical; Matroska's 1/1000 timestamps rounded the 24fps source times. Assigning exact 1/120 timestamps
  before libplacebo fixed the instrument. The full 14-case run was repeated; the 2.55-DN limit was not relaxed.
- Repeated High on the original 14 cases agrees exactly in feature PSNR. Constant flow and static scene controls
  pass. A controlled affine field's displacement error falls from 2.37037 to 0.01517 pixels with two iterations.
- The actual scorer refuses a one-output shift (10.9587 DN retained RMS). A +0.15 fault injected only into frame
  7's facial features is isolated to that scored frame, with MSE 0.0225 and bad-pixel fraction 1.
- The actual FFmpeg wrapper refuses an undefined-symbol shader even when fallback could otherwise produce an
  image; the decoder refuses a 12-frame stream where 30 are required. Evidence extraction also refuses a missing
  score file and deliberately corrupted score arithmetic.
- Metadata review caught `source_frames` incorrectly naming the reference count in real.py. The saved half-input
  counts were checked with ffprobe, the field corrected, and `reference_frames` added; quality values did not change.
- All 35 existing generated shader bodies rebuild identically. The experimental combined shader's 87 passes
  compile through glslc and translate to MSL with zero failures. This does not test native Cadence execution.

[results-20261113.json](results-20261113.json) preserves the numeric comparisons and SHA256 hashes of the 122
input JSON records. Full media, per-frame errors, logs, generated GLSL and translated graph remain under
`$NP_SCRATCH/motionstress-20261113`; photographed material/private source paths are not committed. Local toolchain:
patched FFmpeg `3a5eb94`, libplacebo `285d1cc`, deterministic MoltenVK settings from run.py.

Next bounded work: register a silhouette/background-band error measure and visibility counterexamples before
another warp change; retain multiple separated global candidates before full-pixel refinement; test the bar
boundary anchors versus the periodic interior independently. Keep exact aliases as indeterminate. These are
specific follow-ups to measured failures, not an adoption request.
