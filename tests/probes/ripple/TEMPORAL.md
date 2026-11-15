# Garment ripple: temporal measurements, 2026-11-15

The reported defects are the white-shirted man leaning back around 202–204 s and
the standing man leaving left around 209–211 s. Whole-image PSNR can hide a small
region deforming or flickering. This probe keeps spatial maps and per-frame
measurements. A native insertion has no captured truth at its timestamp.

## Correction to the earlier temporal claim

`../occwarp/warpsim.py` currently calls the following scalar `flicker`:

1. Calculate the mean absolute ROI error against truth in each synthesized frame.
2. Calculate the mean absolute difference between successive scalar means.

This measures **variation in the total error**, not pixelwise temporal error. A
ripple that moves or changes sign while retaining the same total absolute error
can score zero. At 24→60, removing the retained-source frames also leaves unequal
time intervals between some compared samples. The recorded values remain valid
as scalar error variation; they do not establish the absence of local flicker.
This finding does not negate the separate PSNR, tail or visual observations in
the earlier experiment.

## Native 2× diagnostic

`temporal.py` tracks a chosen interior crop using lowpassed **source frames only**.
It fits bounded subpixel translation by normalized correlation; the output and
shader fields never influence registration. Low texture, a competing match, a
search-edge maximum or a poor rigid fit stops the track. Subsequent frames are
unknown. No threshold is loosened to obtain a complete score.

All variants share those source-derived transforms. At Gaussian sigma 1, 2 and
4 pixels, the registered sequence J is measured using
`J[k-1] - 2*J[k] + J[k+1]`, separately at inserted and retained-source centers.
The spatially nonuniform component removes only each curvature image's ROI mean;
the mean brightness component is retained as a separate measurement. Spatial RMS
maps, 32×32 tile statistics, and pixelwise changes in midpoint departure preserve
local defects. Midpoint departure is the insertion minus the mean of its two
registered sources. It is a diagnostic reference, not ground truth.

A piecewise-linear sequence formed from the registered originals is measured by
the same code. It shows why source film grain can generate parity curvature even
without invented deformation. Actual folds, shading changes, imperfect rigid
registration, and resampling-dependent grain variance can also produce a signal.
Source-only tracking prevents self-validation but does not solve these ambiguities.
The crop must stay inside the garment: the tracker cannot identify a semantic
occlusion merely because it can fit a translation.

## First registered crop: incomplete, as predicted

The crop `(440,450,140,140)` was specified from source imagery at source frame 48,
before examining variant errors. Requested source frames were 48–84 inclusive,
with a 160-pixel decoded margin. Default thresholds were retained.

Only frames **48–55** were accepted. Pair 55→56 was rejected for ambiguous
translation: best correlation 0.91549, competing peak 0.90746, gap 0.00802 below
the fixed 0.01 requirement. Its photometrically fitted rigid residual was 9.03 DN.
Frames 56–84 remain **unknown**, and this short accepted track cannot substantiate
a conclusion about the full visible episode. Retained-source agreement across
the accepted interval was within 0.03771 DN mean absolute error for every variant.

At sigma 2, in the accepted crop only:

| Variant | Insertion-centered shape curvature, DN | Pixelwise midpoint-departure change, DN |
|---|---:|---:|
| Current High | 1.0668 | 0.6556 |
| Previous High | 1.0668 | 0.6556 |
| Vote nearest | 1.0668 | 0.6556 |
| Previous without coherence fallback | 1.0608 | 0.6490 |
| Linear image blend | 4.0213 | 1.4974 |

These are diagnostic amplitudes, **not a ranking of visual quality**. In
particular, linear image blending creates large registered midpoint departure
when the shirt moves, whereas true cloth deformation can also depart from the
registered-source chord. No vote-related change is established in this crop.

## Withheld truth is a separate experiment

`withheld.py` compares reconstruction from even original frames against the odd
captured frames. For N originals it requires exactly `2*ceil(N/2)` rendered
frames, verifies retained even-frame alignment, and scores only odd originals
with valid neighbors. The final synthetic sample beyond an odd-length source is
never treated as truth. The source-to-source displacement is twice that of native
24→48 interpolation; success here is not direct proof of native midpoint quality.

Fixed garment-plus-boundary ROIs are scored on raw and Gaussian-1/2 luma using
pooled-MSE PSNR, worst-1% RMS and the worst 32×32 tile, with per-frame records.
Gaussian gradient error measures displacement of folds and edges separately from
uniform brightness error. Actual unpredictable grain still contributes error;
neither smoothing nor a lower PSNR error alone establishes a visual fix.

## CPU counterfactual checks

- A translated textured patch recovered `(2.3,-1.7)` pixels within 0.008 pixels.
- Flat and periodic/aperture-ambiguous patches were rejected.
- An alternating one-DN sinusoidal ripple with constant total absolute error
  produced 1.263 DN pixelwise midpoint-departure change at sigma 2; the unchanged
  control produced zero. The old scalar-MAE-difference statistic misses this case.
- Withheld exact truth scored zero error; a localized corruption selected its
  correct frame and increased the tail and gradient measures.
- A constant +12.75 DN offset produced intensity error and negligible gradient
  error, distinguishing brightness from spatial deformation.
- Tiny CPU-encoded videos verified odd-only scoring and the odd-length frame-count
  rule. Wrong output count and corrupted retained frames both failed loudly.
  Failed runs leave `execution_status=incomplete`, preventing stale successful JSON
  from being mistaken for a completed rerun.
