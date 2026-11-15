# Eight-pixel overlap rendering — before its GPU run

2026-11-15. An orthogonal rendering diagnostic on the preceding High, `WARP_VOTE=0`, pinned SHA256
`b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece`. It uses the same final estimated field and
does not change any estimator pass, temporal memory, support statistic or scene-cut decision. It is a comparison
of dense warping with overlapping locally rigid pictures, not a claim of corrected flow or visibility.

## Fixed construction

Use one prechosen grid spacing, **8 full source pixels**; do not sweep it on these windows. Its node centers are
4,12,20,… in each axis. For output p, use the four enclosing nodes. The first/last in-image nodes are replicated
at image boundaries. At each node, sample the existing A-indexed `FLOW_H_AB` and convert its displacement to full
image UV units exactly as the original final warp does.

Each node vector independently draws a paired picture **at output p**:

`C_i(p) = (1-t) A(p - t f_i) + t B(p + (1-t) f_i)`.

Bilinearly blend the four pictures using p's fractional position in the 8-pixel grid cell. **Never average the
four displacement vectors.** Within a node's picture the vector is constant, so its two sampling maps are rigid
translations. Overlapping picture weights vary with p; that blend can still change appearance and is not a proof
of geometric correctness.

The original final warp is retained for t≤0.001 or t≥0.999. If all four node vectors equal the original vector,
reuse the original picture arithmetic rather than blend identical copies. The original coherence fallback is
then applied using the unchanged SUPPORT(p); the original scene-cut return remains before the new block. Only
the final rendering pass changes, with no additional pass or binding.

## Prediction and failure risks

If dense spatial variation in the field is producing fluid-looking intra-garment deformation, overlapping
locally rigid pictures may reduce that deformation on the same field. Whether the resulting picture is better
is unknown. The construction can instead blur or double details, retain wrong node motions, show an 8-pixel grid,
or alter temporal contrast as moving content crosses the fixed grid. A ghost is a failure, even if the geometry
looks calmer or a scalar score improves. Source ownership, visibility and disocclusions are not solved.

The four-picture operation is not a disguised flow smoother. A CPU counterexample uses a static narrow Gaussian
line and opposite node vectors. Their averaged vector is zero and samples the peak at 0.8 intensity. Blending
the displaced pictures instead gives about 0.2812. This deliberate worsening example establishes the nonlinearity
and the need for a picture check; it does not predict a benefit.

Controls before rendering: constant-flow identity across phases and image edges; nonnegative normalized overlap
weights; source-phase identity even for varying node flow; the nonlinear picture-versus-vector counterexample;
and rejection of an unregistered shader source. The transform asserts reversibility of its two inserted blocks
and unchanged hook count. Generated GLSL remains external.

Compare native 24→48 garment playback against the preceding/current High and the other registered ablations.
Keep temporal phase evidence and full-image human comparison decisive; withheld-frame truth remains the separate
doubled-displacement test. A result on these two windows is not a production gate. Extra flow/image reads and
actual cost are unmeasured. This diagnostic neither reinstates an old fallback nor changes the accepted defaults.
