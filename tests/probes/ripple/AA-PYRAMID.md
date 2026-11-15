# Luma pyramid low-pass diagnostic — registered 2026-11-15

This is a diagnostic on prior High, not a new shipping proposal. Input is the registered
`WARP_VOTE=0` High with SHA-256
`b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece`.
No GPU or footage result for this intervention exists at registration.

## Existing construction and prior refutation

All eight original A/B luma passes at H/Q/E/S directly sample the source frame once. S and E
also retain a separately smoothed texture-energy channel. There is no explicit luma footprint
low-pass before these decimations. A bilinear source sample has at most a 2×2 source-pixel
footprint: at aligned 2:1 H reduction it already averages the four source pixels, but it does
not average the 4×4, 8×8 or 16×16 footprints of Q/E/S.

This was already investigated. `NFRAME-LIMITS.md` §8 records the prefilter's refutation:
the full box gained only 1.5–2.6 dB on some noninteger-speed cases and lost 18.27 dB on the
16-pixel/frame control; fine-texture and even static cases suffered. The subsequent full/half
box, tent, S+E-only and S-only sweep did not rescue the tradeoff. Aliased contrast can carry
useful matching information, and filtering can remove it or alter near-tie decisions. Those
failures stand. This experiment does not establish that anti-aliasing is generally better.

The later non-affine section (around lines 3396–3465) locates wrong/reversed vectors at the
coarse search, with incomplete recovery downstream. Strain changing the apparent motion of
near-Nyquist detail is consistent with those measurements, but the document explicitly calls
that explanation **not yet demonstrated**. Clothing deformation plus weave/grain/shadow is a
plausible reason to test the input statistics here, not an established cause of the film defect.

## Exact intervention

`aa_pyramid.add_cascade_box(text)` inserts eight scalar scratch textures immediately before the
original S luma pass: `AA_A_H/Q/E/S` and `AA_B_H/Q/E/S`. H averages four raw source-luma taps at
offsets `(±0.5, ±0.5)` source texels. Each following level averages four taps at those offsets
in the previous AA level. Dimensions equal the corresponding existing level. The original
eight luma passes then read these AA scalars in place of their single source-luma expression.

At exact 2:1 dimensions the cascade equals an aligned 2×2, 4×4, 8×8 or 16×16 box average.
At rounded dimensions it is precisely the stated four-tap cascade with bilinear sampling,
not an exact area resizer or ideal band-limit filter. In particular, 1080 height produces
H=540, Q=270, E=135, S=68 under libplacebo's rounding; E→S is not exactly 2:1. The normalized
sample centers are retained, so the ablation does not intentionally shift the luma grid.
Edges retain the shader sampler's existing boundary behavior.

Preserved verbatim:

- Original HOOKED/NEXT images and all final color sampling.
- GLOBAL_GAIN fitting/acceptance and each B luma pass's `gg_b(...)` compensation, applied once
  after the raw-luma average. The affine compensation commutes with averaging mathematically.
- Existing ENERGY_A/B production and the S/E `.g` expressions.
- All search, prior, propagation, variational, median, support and cut **code** and constants.

Scope caveat: LUMA is also consumed by support, cut, alias and global-shift calculations.
Their bodies remain unchanged, but their inputs/statistics can change. This is a matching-luma
intervention, not a pure flow-only or final-warp-only intervention. Any claimed flow mechanism
must be checked against changed support/cut behavior and source-image replay.

## Predictions and interpretation

1. Constant input luma remains constant at every level. Linear ramps retain their value at
   interior sample centers. Aligned H matches the original bilinear reduction mathematically.
2. Q/E/S suppress fine contrast; a source checkerboard averages to its mean. On textured cloth,
   both reduced flow instability and loss of useful correspondence are plausible outcomes.
3. A reduction in native ripple accompanied by reduced coarse/Q field irregularity supports
   sensitivity to pyramid input statistics. It does not by itself prove aliasing, distinguish
   grain from weave/shading, or establish that the new flow is correct.
4. An unchanged picture/field does not support this route on the sampled windows. Deterioration
   is a recorded negative result; do not tune filter widths after inspecting the target.

Compare `prev-aa-box` with identical `prev` native 24000/1001 → 48000/1001 input and lead-in.
Inspect garment interiors and boundaries in temporal playback, and compare changed support/cut
decisions. Preserve source-instant alignment and failure checks. A withheld-frame reconstruction
is separate because it doubles displacement. Any further proposal needs fine-pattern, integer
translation, static and boundary controls as well as the ordinary full gates. Do not promote
this diagnostic from the two reported windows.

```sh
python3 tests/probes/ripple/aa_pyramid.py --control
python3 tests/probes/ripple/aa_pyramid.py prev.glsl prev-aa-box.glsl
```

CPU controls check constant/ramp/checkerboard behavior and exact box equivalence on divisible
dimensions, plus the rounded 1080-height cascade's interior ramp behavior. These are sampling
arithmetic controls, not GPU execution or interpolation-quality measurements.

Before the diagnostic control run: recheck four of the old vulnerable ladder cases on this modern prior-High
baseline, `L0_static`, `L6_flat_large`, `M1_noise_large`, `A4_accel_tex_a033`. This is a small regression probe,
not the full gate. Preserve both historical and interior readings; do not infer the 2026-09-03 loss magnitudes
still hold for the later energy/carry/adopt/lattice pipeline.
