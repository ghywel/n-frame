# Ripple experiment: compact numeric record

Status: `all_score_groups_complete`. Required original, Newton and AA score groups were validated.

The withheld test reconstructs odd originals from even originals: twice the native interpolation displacement.
All duplicate previous-High baselines match exactly. Renderer counts, hashes, retained alignment and score arithmetic passed.

Renderer sidecars without completion markers are explicitly labeled legacy. A historical log alone does not prove process exit status; full decoded counts and retained-frame alignment were independently checked.

Initial video depicts the reported defect: confirmed by the explicit recorded flag.
This does not record a human verdict on later variants.

## Shirt

119 originals; 60 half-rate inputs; 120 reconstructed frames; 238 native 2x outputs. ROI `[240, 230, 700, 620]`; 24 withheld frames 49–95.

| Variant | Raw PSNR dB | σ2 gradient DN/px | Raw tail DN | σ2 tail DN | Worst σ2 tile DN; frame, x, y |
|---|---:|---:|---:|---:|---|
| high | 31.35870 | 1.39156 | 46.858 | 37.260 | 63.588; 73, 752, 774 |
| prev | 31.27998 | 1.40266 | 47.128 | 37.634 | 63.588; 73, 752, 774 |
| vote-nearest | 31.34991 | 1.39206 | 46.916 | 37.262 | 63.588; 73, 752, 774 |
| prev-no-fallback | 31.22578 | 1.41894 | 47.465 | 37.461 | 62.064; 73, 752, 774 |
| linear | 26.87675 | 2.27167 | 70.245 | 60.038 | 71.654; 71, 496, 422 |
| prev-e-temporal-off | 31.11997 | 1.42456 | 47.909 | 38.515 | 62.881; 73, 752, 774 |
| prev-h-data-refine-off | 31.25749 | 1.40721 | 46.787 | 37.461 | 62.326; 73, 752, 774 |
| prev-inverse2 | 31.33709 | 1.38894 | 47.237 | 37.564 | 64.159; 73, 752, 774 |
| prev-newton | 31.30173 | 1.38606 | 46.969 | 37.692 | 63.931; 73, 752, 774 |
| prev-aa-box | 31.30567 | 1.39997 | 47.304 | 37.798 | 63.686; 73, 752, 774 |
| prev-obmc8 | 31.42577 | 1.37637 | 45.897 | 36.963 | 62.899; 73, 752, 774 |

| Variant | Δ raw dB vs prev / High | Δ σ2 dB vs prev / High | Δ gradient vs prev / High | Δ σ2 tail vs prev / High |
|---|---:|---:|---:|---:|
| high | +0.07872 / +0.00000 | +0.10714 / +0.00000 | -0.01110 / +0.00000 | -0.37420 / +0.00000 |
| prev | +0.00000 / -0.07872 | +0.00000 / -0.10714 | +0.00000 / +0.01110 | +0.00000 / +0.37420 |
| vote-nearest | +0.06993 / -0.00879 | +0.10712 / -0.00002 | -0.01060 / +0.00050 | -0.37211 / +0.00209 |
| prev-no-fallback | -0.05420 / -0.13292 | +0.04011 / -0.06703 | +0.01629 / +0.02738 | -0.17289 / +0.20131 |
| linear | -4.40324 / -4.48196 | -5.00852 / -5.11567 | +0.86902 / +0.88012 | +22.40411 / +22.77831 |
| prev-e-temporal-off | -0.16001 / -0.23873 | -0.21269 / -0.31984 | +0.02191 / +0.03300 | +0.88146 / +1.25566 |
| prev-h-data-refine-off | -0.02249 / -0.10121 | -0.02870 / -0.13584 | +0.00456 / +0.01565 | -0.17279 / +0.20141 |
| prev-inverse2 | +0.05711 / -0.02161 | +0.09167 / -0.01547 | -0.01371 / -0.00262 | -0.06965 / +0.30455 |
| prev-newton | +0.02175 / -0.05697 | -0.01128 / -0.11842 | -0.01659 / -0.00549 | +0.05811 / +0.43230 |
| prev-aa-box | +0.02569 / -0.05303 | +0.03682 / -0.07032 | -0.00268 / +0.00842 | +0.16402 / +0.53822 |
| prev-obmc8 | +0.14578 / +0.06706 | +0.09844 / -0.00870 | -0.02628 / -0.01518 | -0.67128 / -0.29708 |

Optional OBMC score group: **complete**.

## Suit

143 originals; 72 half-rate inputs; 144 reconstructed frames; 286 native 2x outputs. ROI `[160, 80, 960, 800]`; 24 withheld frames 49–95.

| Variant | Raw PSNR dB | σ2 gradient DN/px | Raw tail DN | σ2 tail DN | Worst σ2 tile DN; frame, x, y |
|---|---:|---:|---:|---:|---|
| high | 26.46358 | 1.88526 | 74.655 | 67.767 | 96.617; 83, 544, 240 |
| prev | 26.43890 | 1.89186 | 74.742 | 67.864 | 96.617; 83, 544, 240 |
| vote-nearest | 26.46024 | 1.88591 | 74.692 | 67.772 | 96.617; 83, 544, 240 |
| prev-no-fallback | 26.43855 | 1.89780 | 74.550 | 67.698 | 96.295; 83, 544, 240 |
| linear | 24.81277 | 2.30671 | 84.140 | 76.821 | 102.056; 83, 544, 208 |
| prev-e-temporal-off | 26.29302 | 1.92298 | 75.869 | 69.006 | 100.881; 71, 928, 400 |
| prev-h-data-refine-off | 26.45822 | 1.88480 | 74.332 | 67.515 | 96.311; 83, 544, 208 |
| prev-inverse2 | 26.39744 | 1.90530 | 75.357 | 68.188 | 95.734; 83, 544, 240 |
| prev-newton | 26.33928 | 1.89792 | 75.093 | 68.166 | 97.118; 83, 544, 208 |
| prev-aa-box | 26.48084 | 1.88598 | 74.724 | 67.766 | 96.849; 83, 544, 240 |
| prev-obmc8 | 26.53564 | 1.85541 | 73.643 | 67.185 | 96.190; 83, 544, 240 |

| Variant | Δ raw dB vs prev / High | Δ σ2 dB vs prev / High | Δ gradient vs prev / High | Δ σ2 tail vs prev / High |
|---|---:|---:|---:|---:|
| high | +0.02468 / +0.00000 | +0.02672 / +0.00000 | -0.00660 / +0.00000 | -0.09634 / +0.00000 |
| prev | +0.00000 / -0.02468 | +0.00000 / -0.02672 | +0.00000 / +0.00660 | +0.00000 / +0.09634 |
| vote-nearest | +0.02134 / -0.00335 | +0.02657 / -0.00015 | -0.00595 / +0.00065 | -0.09178 / +0.00456 |
| prev-no-fallback | -0.00034 / -0.02503 | +0.01278 / -0.01394 | +0.00594 / +0.01254 | -0.16589 / -0.06954 |
| linear | -1.62612 / -1.65081 | -1.68830 / -1.71502 | +0.41485 / +0.42145 | +8.95688 / +9.05322 |
| prev-e-temporal-off | -0.14587 / -0.17056 | -0.15744 / -0.18416 | +0.03112 / +0.03773 | +1.14269 / +1.23903 |
| prev-h-data-refine-off | +0.01932 / -0.00536 | +0.01431 / -0.01241 | -0.00706 / -0.00046 | -0.34834 / -0.25199 |
| prev-inverse2 | -0.04145 / -0.06614 | -0.02319 / -0.04991 | +0.01344 / +0.02004 | +0.32462 / +0.42096 |
| prev-newton | -0.09962 / -0.12430 | -0.11022 / -0.13694 | +0.00606 / +0.01266 | +0.30239 / +0.39874 |
| prev-aa-box | +0.04194 / +0.01726 | +0.05102 / +0.02430 | -0.00588 / +0.00072 | -0.09800 / -0.00165 |
| prev-obmc8 | +0.09674 / +0.07206 | +0.06538 / +0.03866 | -0.03645 / -0.02985 | -0.67863 / -0.58229 |

Optional OBMC score group: **complete**.

## Native temporal coverage

The source-only shirt tracker accepted 48–55; 56–84 are unknown. Pair 55→56 was rejected: correlation 0.91549, rival 0.90746, gap 0.00802, fitted residual 9.030 DN.
This is coverage metadata, not a native temporal quality score.

Geometry/Newton/OBMC CPU control values and per-frame metric rows are retained in the JSON. Their scopes remain separate from film attribution.
Runnable temporal/withheld measurement controls: `available`.
MCI status: `instrument_checks_available`.
Owner reports the MCI shirt is noticeably calmer than current High in the displayed native preview.
That MCI observation does not apply to the suit or the same-field OBMC diagnostic.
Owner reports no clear improvement in the same-field OBMC shirt preview: visual benefit not established.

## Current AA control probe

These four current-baseline comparisons are separate from the historical prefilter failures. Only comparison arithmetic is validated by this summary.

| Case | Whole Δ dB | Interior Δ dB |
|---|---:|---:|
| L0_static | -0.05000 | -0.05000 |
| L6_flat_large | +0.29727 | +0.31143 |
| M1_noise_large | +0.20227 | +0.21190 |
| A4_accel_tex_a033 | +0.32136 | +0.33667 |
