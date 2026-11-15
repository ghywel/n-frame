# Frozen photographed plane: registered 2026-11-15

This is a known-motion estimator/grain control, **not film-cause evidence**. A
single photographed plane contains clothing, face and neighboring scene texture;
neither its crop nor its measurement region is a semantic garment segmentation.
The plate and all imagery remain in external scratch storage.

## Fixed construction

- Freeze original `shirt-source.mkv` frame 48 at its full 1920×1080 resolution.
- Convert once through the pinned FFmpeg decoder to normalized `gray16le` code
  values. The input is limited-range BT.709 YUV420; transfer metadata is recorded.
  Do not linearize gamma, resize, denoise or modify the photographed material.
- Make 640×360 frames from plate origin `(400,250)` with exact translation
  `d=(-16,0)` pixels/source frame: `I_t(x,y)=P(400+x+16t,250+y)`.
- Twelve input frames at `24000/1001`, 24 clean truth frames at `48000/1001`.
  All these sample positions are integers, so construction has no rounding of
  motion or subpixel-resampling uncertainty. The final truth midpoint exists as
  a construction but lacks a twelfth-next input and is excluded from scoring.
- Conditions: `frozen`, containing the original **frozen** grain as material
  texture; and `grain`, adding independent Gaussian luma noise of sigma 2/255
  per source frame using NumPy PCG64 seed 221115. Clip to [0,1], quantize once to
  16-bit, and record clipping and realized noise. Do not invent a midpoint noise
  realization as a target. Both conditions share the same clean material truth.
- Store source/truth fixtures as FFV1 `gray16le`, and verify lossless decoded
  round trips and frame/rate metadata before declaring preparation complete.

## Fixed material coordinates and interval

At source time `t=7`, the material ROI is `(128,48,384,264)`. At every output time
`t=j/2`, use output x-origin `128+16*(7-t)`, the same y-origin/size. This follows
the **same material pixels**, rather than a fixed screen rectangle. Every aligned
clean truth patch is consequently identical, without registration or interpolation.

Score output indices **9–19 inclusive**: six inserted and five retained outputs.
Temporal second differences centered there also use the adjacent support frames
8 and 20. Report all outputs and both parities separately. The terminal midpoint
and startup interval are excluded.

## Four-render matrix and instrument gates

For each condition, compare previous High with coherence fallback disabled
against its identical oracle shader with final `flow_ab=(-16,0)`, preserving all
other sample/blend arithmetic. Main owns shader generation and GPU execution.
The certified scorer accepts exactly `oracle` and `estimate`, with registered
hashes `b7ef3875a3c644947db4e0488d3d6871ae830370601f0963b033ec7d8008d464`
and `0d8ec94d53dbbd7a607265eb3c62f62ccab3797df58ad3c580e5efe5ac9cc3c6`
respectively. Passing the oracle as the estimator is refused even if its pictures
pass every numerical gate. An original-previous-High comparison would need
separate labeling and fallback scope; it is outside this certification.
No estimator parameter, noise seed, crop, interval or threshold is tuned
after looking at results.

Before attributing a difference to the estimated field:

1. Each selected retained source instant must have full-frame mean absolute
   difference from its decoded input of **at most 0.5 normalized DN**. Report the
   corresponding material-ROI residual too. Include support outputs
   **8,10,12,14,16,18,20**, corresponding to inputs 4–10, since curvature at 9/19
   consumes outputs 8/20.
2. Every selected oracle midpoint must have material-ROI RMS difference from
   the exact CPU blend of its **decoded** input endpoints of **at most 1.0 DN**.
   These integer-position CPU samples follow the known constant motion exactly.
3. Require successful renderer metadata, matching source/output hashes, 12→24
   frames and the registered rates. Any instrument failure invalidates field
   attribution. Preserve the failure; do not loosen a gate.

These gates allow output quantization. They are not claims of measured precision:
record actual source/oracle residuals, including Gaussian sigma 2 and gradients.
The actual measured oracle errors define the instrument floor, not its 1-DN gate.
Integer 16-pixel translation excludes a subpixel sampling mechanism. The four
preceding source pairs are a fixed lead-in, not evidence of temporal convergence.

## Readouts and grain interpretation

Measure material-coordinate error against the clean plane, against the exact CPU
endpoint blend, and estimated-output minus actual GPU-oracle output under the
same input/noise realization. The last difference isolates the final field choice
under this fixed pipeline, **conditional on the instrument gates**.

At raw and Gaussian-sigma-2 luma, retain per-output RMS and gradient error,
mean-adjusted contrast gain relative to the frozen signal, source-to-inserted
chord residual and its gradient, and temporal error differences over **all**
outputs as well as inserted outputs alone. Repeated midpoint errors can be
invisible to synthesized-only differences while alternating with correct sources.

For ideal independent, unclipped source noise, retained error RMS is 2 DN and
midpoint blend error RMS is `2/sqrt(2)` DN. This variance alternation exists with
perfect motion. Its ideal inserted-centered second difference is zero, whereas
the retained-centered noise curvature RMS is `2*sqrt(1.5)` DN. Gaussian filtering
reduces absolute noise energy but preserves the source/midpoint variance ratio.
Report these analytic expectations separately from the exact realized residual
of the clipped, quantized endpoint samples. A clean-plane error caused solely by
that known noise is not a motion-estimation failure.

This experiment can establish or refute a mechanism on the frozen photographed
plane. It cannot establish that the same mechanism causes the live film defect,
whose material deforms, occludes, changes lighting and contains motion blur.
