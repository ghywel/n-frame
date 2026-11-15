# A sampling-map fold does not prove that the estimated field is wrong

2026-11-15. Independent mathematical controls for the shirt/suit investigation. These are CPU constructions
with exact fields, not evidence that either construction describes the film. Constants were chosen for simple
counterexamples, not fitted to the footage. Run `python tests/probes/ripple/geometry.py [OUT.json]`.

## Exact and approximate coordinates

Let the displacement field F be indexed in source A. A material point q appears at time t at

`p = q + t F(q)`.

Its source-A coordinate therefore solves that equation; its B coordinate is `q + F(q)`. High's basic warp instead
uses `q0 = p - t F(p)` and `b0 = p + (1-t) F(p)`. This distinction exists even when F is known without error.
Constant displacement is a case where the two are equal. The argument does not identify the visible root at an
occlusion, and a per-pixel image blend can involve additional sampling maps and weights.

For an affine field `F(q) = Kq + b`, write `M = I + tK`. When M is invertible:

- Exact A coordinate: `q* = M^-1 (p - tb)`.
- Approximate A coordinate: `q0 = (I - tK)p - tb`.
- Forward reprojection residual: `q0 + tF(q0) - p = -t² K F(p)`.
- Coordinate error: `q0 - q* = -t² M^-1 K F(p)`.
- Exact A sampling Jacobian: `M^-1`; approximate A sampling Jacobian: `I - tK`.
- Approximate B sampling Jacobian: `I + (1-t)K`.

For a general differentiable field, the exact inverse Jacobian uses `DF(q*)`, at the source root. The approximate
Jacobian uses `DF(p)`, at the output position. Substituting one for the other is itself an approximation.

## A valid forward deformation can make the approximation reverse direction

Take `K = diag(3,0)`, `b = (2,0)`, and `t = 1/2`. For every phase from 0 to 1 the true forward deformation has
positive determinant, between 1 and 4. Its x-coordinate is strictly increasing. Yet the approximate A sampling
Jacobian is `diag(-1/2,1)`, with determinant -1/2, whereas the exact inverse is `diag(2/5,1)`.

At output x=10, the correct A coordinate is 3.6. High's approximation samples -6; forwarding that point to the
midpoint gives -14 rather than 10, a residual of -24 pixels. The correct B coordinate is 16.4, versus the approximate
26. An independently evaluable analytic material texture produces a nonzero picture error under the approximation
and zero up to roundoff under the exact coordinates. Retained endpoint pictures still pass through correctly.

This deliberately strong local expansion is a proof of possibility, not a proposed motion model for clothing.
Also, **negative determinant means local orientation reversal**. A globally affine reversal remains one-to-one;
calling every negative determinant a global many-to-one fold would overstate the diagnostic.

The script therefore also supplies a genuine smooth fold. In one dimension embedded in 2D, take

`F(q) = 3 L log(1 + exp(q/L))`, with `L=8` and unchanged y.

Then `0 < F'(q) < 3`, so `1 + tF'(q) > 0` for every phase in [0,1]: the true forward map never reverses or folds.
But at t=1/2 the approximate derivative `1 - tF'(p)` crosses zero at `p = L log(2)`. The script finds two distinct
output positions that High's approximate A map sends to exactly the same source coordinate. Their exact source
coordinates are distinct and ordered. The fold is created by the inverse-coordinate approximation alone.

## Why two fixed-point proposals may not repair this

The iteration `q[n+1] = p - tF(q[n])` has affine error recurrence `e[n+1] = -tK e[n]`. Its asymptotic convergence
condition is `spectral_radius(tK) < 1`; a bounded norm below one in a neighborhood is a sufficient contraction
condition for a nonlinear field. Finite iteration counts do not inherit an asymptotic convergence guarantee.

In the affine example above, errors grow by 1.5 on each iteration. Replaying the existing inverse2 proposal rule
gives residual magnitudes 24, 36 and 54 pixels. Its strict improvement guard correctly retains the original vector.
Thus little improvement from inverse2 where the sampling map reverses would **not** refute a coordinate problem.
It may indicate a solver outside its convergence region.

Newton's update is `q_new = q - [I + t DF(q)]^-1 (q + tF(q) - p)`. It solves the exact affine example in one step.
It is not a safe default merely for that reason. Differentiating noisy estimated fields can be unstable; Jacobians
near singularity amplify residuals, steps can leave the image, and multiple visibility roots remain unresolved.
The script includes an explicitly unreliable estimated gradient `-2 + 1e-6` at t=1/2: the denominator is about
5e-7 and one Newton step moves about one million pixels. Its algebraic residual is then tiny, despite leaving a
declared source domain [-100,100]. At gradient -2 the update is singular. This second example is not an
orientation-preserving true motion over the whole source interval; it models a risk of trusting estimated flow.

## What the film's Jacobian measurement can establish

For the vote-off A sampling map, a reliably measured negative `det(I-t DF(p))` establishes local orientation
reversal in that particular map. It is a useful place to inspect the picture. It does not on its own establish:

- whether F is physically wrong or the output-position approximation is wrong;
- whether the region is a visible continuous surface, an occlusion boundary or a true material fold;
- whether the local intensity texture makes the coordinate error visible;
- whether the final output is dominated by that map, another candidate, or the coherence fallback;
- whether the source root exists uniquely, or whether a solver's lower residual chooses the visible surface.

A causal real-footage claim still needs the calibrated replay, separate warp/estimator ablations, and an image
test that detects the reported defect. The fixed probe rectangle's determinant statistic is not a count of
proven wrong pixels or a ground-truth motion-error measurement.

## A shared wrong vector does not move both material samples in the same direction

The `NO OCCLUSION FALLBACK` comment in `shaders/src/bidirectional-interpolation-propagated.glsl` gives two different
types of argument. Its recorded comparisons say three particular fallback implementations looked worse on the
tested clip. Those are empirical results, and the following counterexample does not overturn them. However, its
mathematical explanation that shared wrong flow makes both samples wrong "together and in the same direction"
and therefore spatially coherent is false in general.

Take an unbounded material plane with intensity I, translating by the exact constant vector d. The retained frames
are `A(x)=I(x)` and `B(x)=I(x-d)`. Let the warp use a shared displacement `d+δ` at output p and phase t. Writing
`s=p-td`, the two sampled **material** coordinates are

`A side: s - tδ`, and `B side: s + (1-t)δ`.

For 0<t<1 and nonzero δ they lie on opposite sides of the true material point s, separated by exactly δ. Using
one vector for both samples therefore does not guarantee their agreement or exclude a doubled contour. The CPU
control translates a narrow painted Gaussian line by 8 pixels and uses a displacement of 14. At the midpoint,
the correct peak is at x=4, but the prediction has two peaks near x=1 and x=7. No occlusion, estimator-grid
interpretation, or source-pixel resampling is involved.

There is a genuine beneficial property: the weighted material-coordinate centroid is exactly s. For a smooth
intensity field, the first-order Taylor terms cancel; the leading small-error term is

`0.5 t(1-t) δᵀ H_I(s) δ`.

An intensity ramp is reproduced exactly by this blend even with a wrong vector. Curved intensity profiles and
edges generally are not. This cancellation explains why some errors are inconspicuous; it is not a guarantee of
spatial coherence. Endpoint preservation for bounded flow also remains valid.

### Exact 24→48 contrast breathing, despite an unchanged synthesized-only error

For a sinusoidal material carrier of period P, `I(s)=c+a cos(2πs/P)`, at t=1/2 the same shared wrong-vector warp
gives exactly

`c + a cos(2πs/P) cos(πδ/P)`.

Retained frames have contrast factor 1; inserted midpoints have factor `cos(πδ/P)`. At exact 24→48 these alternate
at 24 Hz. For δ=4 and P=16, midpoint contrast is 0.7071 of the retained contrast. Individual frames can remain
recognizable while the alternating contrast is uncomfortable in motion. This is a constructed mechanism; it does
not establish the error magnitude, contrast response or causal contribution in the supplied film.

The control also varies the explicitly output-indexed error smoothly from 0 to 6 pixels along material position,
with spatial period 128. Midpoint contrast then varies from 1 to 0.3827, creating patches that breathe differently.
Both sampling-map derivatives remain above 0.926, so this example needs neither an orientation reversal nor a
fold. The actual motion is still one constant translation, with no occlusion. This effect therefore exists
independently of the inverse-coordinate approximation studied above.

In material coordinates the exact output is stationary. The constructed error sequence alternates **zero on
retained frames** and the same spatial error map E on inserted frames. Consequently:

- Synthesized-only changes in scalar MAE are exactly zero.
- Even synthesized-only *pixelwise* error changes are exactly zero.
- Across **all** output frames, per-pixel error first-difference RMS is `RMS(E)` and second-difference RMS is
  `2 RMS(E)`. Both retained-centered and inserted-centered curvature are nonzero, with opposite signs.

Thus repairing a scalar-MAE-change statistic is not enough if retained frames are still omitted from the temporal
measurement. Both phase classes and their transition must be examined. For the actual 24000/1001→48000/1001
pipeline, this same two-phase construction would cycle at 24000/1001 Hz, rather than exactly 24 Hz. Native footage
lacks photographed midpoint truth, so its corresponding detector still needs the alignment/physical-motion
controls described in PLAN.md.

### Grain is a separate exact contrast-breathing control

Perfect motion does not exclude contrast alternation. Suppose corresponding source samples contain independent,
zero-mean grain with equal variance σ². Ordinary blending gives noise variance

`[(1-t)² + t²] σ²`.

At a midpoint the noise variance is halved and noise RMS is 0.7071 of a retained frame's. The CPU control uses two
exact zero-mean, unit-variance, zero-covariance finite populations and checks the variance at five phases; no motion
error is present. For source noise correlation ρ, the equal-variance expression becomes

`[(1-t)² + t² + 2t(1-t)ρ] σ²`.

The supplied film's grain variance and correlation have not been estimated by this control. Low-pass shape/contrast
measurements reduce the energy of fine grain, but they do not mathematically eliminate this ambiguity: equally
filtering two independent noise fields preserves the midpoint-to-retained variance ratio. Apparent breathing alone
therefore cannot establish incorrect motion. The noiseless rigid-texture construction above proves that flow error
is sufficient; this grain-only construction proves it is not necessary. Both explanations must remain available
until the film's deformation, phase and texture/noise evidence distinguishes them.

An optional three-second preview is generated entirely on the CPU, with software H.264 encoding:

```sh
python tests/probes/ripple/geometry.py "$NP_SCRATCH/translation-ripple-20261115/geometry-controls.json" \
  --video "$NP_SCRATCH/translation-ripple-20261115/shared-flow-breathing-proof.mp4" \
  --ffmpeg /path/to/software-ffmpeg-with-libx264
```

The left half is exact 48fps translation; the right half uses the declared shared-vector error only at inserted
midpoints. The video uses 3 pixels/source frame, a 16-pixel carrier and a smooth two-dimensional error in [0,6].
It contains no film footage. Its 8-bit encoded pictures are a preview; the floating-point controls are the numerical
evidence. None of this reinstates an old fallback or proves that a new one is safe. Production comments have not
been edited by this mathematical audit.
