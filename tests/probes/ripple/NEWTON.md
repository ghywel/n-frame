# Bounded Newton diagnostic — before its GPU run

2026-11-15. This is a warp-only experiment on the registered preceding High, `WARP_VOTE=0`, SHA256
`b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece`. It does not change the estimator, support
fallback, scene-cut rule, output colors or endpoint blend. It is not a visibility solver or a deployment proposal.

[GEOMETRY.md](GEOMETRY.md) supplies exact-field controls where a valid forward deformation causes High's
approximate A sampling map to reverse or fold. Two fixed-point proposals cannot repair the affine expansion
control because their errors grow. Newton can solve that control but needs bounded behavior on estimated fields.

## Fixed construction

All coordinates and displacements below are in full source pixels. At interior phase t:

1. Start at the A coordinate the original warp would use: `q = p - t F(p)`.
2. Residual is `r = q + t F(q) - p`. Estimate `DF(q)` by central differences at ±1 full pixel on each axis.
3. Form `J = I + t DF(q)`. Refuse the step if its minimum singular value is below 0.2. This bounds numerical
   inverse amplification; it does not certify correspondence or visibility. A negative determinant with adequate
   singular values is not rejected by this particular diagnostic.
4. Compute the Newton step `J^-1 r`, cap its Euclidean length at 8 pixels, and propose `q_new = q - step`.
5. Require q and the proposal to remain within source pixel-center bounds; require the whole derivative stencil
   to stay inside when computing J. Accept only if residual length decreases by more than 0.0001 pixel.
6. At most four iterations. Stop on refusal or sufficiently small residual. Do not run at t≤0.001 or t≥0.999.

If a proposal is accepted, the shared endpoint displacement becomes **`(p-q_best)/t`**. This makes the A sample
exactly the coordinate whose residual was evaluated; using `F(q_best)` would move A's sample again when the bounded
iteration leaves nonzero residual. B uses the same resulting vector. If every proposal is rejected or tied, retain
the original normalized vector without a conversion round trip. No per-endpoint substitution is introduced.

`newton.add(text)` inserts the helper and this block only in the final warp, asserting the original source hash
and exact anchors. Output is generated externally. The existing scene-cut return precedes the insertion; the
existing coherence fallback still follows it.

## Prediction and limits

The exact affine expansion control should converge where inverse2 refuses. Constant-flow and source-instant
controls should retain their original vector. A near-singular estimated Jacobian should refuse; no iteration may
move over 8 pixels and the four-step path may span at most 32. A large initial error can therefore remain large:
record the residual rather than silently extending the iteration budget or changing thresholds.

On the supplied film, lower geometric residual is predicted only where proposals pass these guards. **Picture
quality is unknown.** A lower residual can pick the wrong layer, make a disocclusion worse, or fit an incorrect
estimated field more faithfully. The unchanged coherence fallback is indexed at the output position and can still
mix in a different picture. Derivative noise, damping from the cap, unresolved roots and cost remain explicit risks.
Up to 21 extra field reads are needed per pixel (one initial residual, then four central differences and one proposed
residual per iteration), excluding paths that stop early. This is not a measured runtime estimate.

For a real-footage claim, compare with the same current/preceding baselines and the inverse2 and estimator-only
ablations, view garment interiors and boundaries, and keep native insertion distinct from withheld-frame truth.
The two film windows alone cannot authorize a production replacement. A lower warp residual alone is not a pass.
