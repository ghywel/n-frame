# Vote sampling diagnostic — registered 2026-11-15

Status: source-level defect and CPU counterexample; no GPU or footage result at registration.
Base: `ccfdf74`, shipped High with `WARP_VOTE=2`.

The owner reports clothing ripples on several variants at 24 → 48. This issue is specific to the
new light vote and therefore **cannot explain the common defect in older variants**. Test it as a
separate, bounded diagnostic, not as the established cause of the Dr. No complaint.

## Mechanism

`tests/warp_vote.py:175–180` stores the raw winning vector even when the ownership gate reduces
that texel's weight to zero. The cost gates can also assign zero weight to a raw winner different
from the default vector. In `DRAW` (`:185–195`), the weight is read bilinearly, but the vector is
read from the nearest half-resolution texel. Positive neighboring weight can consequently draw
a vector that its own texel rejected. Both reads are individually well defined; their pairing
does not preserve the gate's decision.

For aligned 2× upsampling, each full-resolution pixel gives its nearest half-resolution texel
weight 9/16, the two adjacent texels 3/16 each and the diagonal 1/16. A nearest texel with weight
zero can therefore be drawn with weight 7/16 = 43.75% when those three neighbors have weight one.
At the next half-resolution boundary the selected vector can jump even though the interpolated
weight is smooth. This can produce small patch seams or modulation of texture inside a mover.
No claim is made that it has done so on the reported frames.

## One-change ablation

`vote_sampling.add_nearest_weight(text)` changes only the final vote's weight lookup to use the
same nearest texel as the vector. Candidate generation, cost, ownership, stored vectors, estimator,
coherence fallback, source-image sampling and source-frame handling remain unchanged.
This is intentionally a diagnostic: nearest weights can themselves reveal block boundaries.
A coherent interpolation of candidate **pictures** would be a separate, more expensive design.

Registered predictions:

1. A zero-weight nearest texel contributes no voted picture, regardless of its neighbors.
2. Regions with equal neighboring weights are unchanged by this ablation.
3. If borrowed confidence contributes to the reported ripple, altered pixels should lie where
   nearest and bilinear vote weights differ, and near differing candidate vectors. A change
   elsewhere is an implementation or comparison error.
4. `WARP_VOTE=0` can still ripple. An unchanged defect in that ablation rejects the vote as its
   sole cause; it does not refute this sampling counterexample.

Compare current High, High with this one change, and High with `WARP_VOTE=0` on identical decoded
frames, exact timestamps, identical lead-in and native 24 → 48 playback. Inspect the shirt at
202–204 s and suit at 209–211 s. Keep unmodified source instants as a control. A native midpoint
has no known ground truth, so visual improvement alone is not an interpolation-accuracy claim.
No adoption or full quality-gate claim follows from this diagnostic; any repair needs fresh
cage, boundary, ladder and content validation against the current baseline.

## CPU control and build

From the repository root:

```sh
python3 tests/probes/ripple/vote_sampling.py --control
python3 tests/probes/ripple/vote_sampling.py INPUT_HIGH.glsl OUTPUT_NEAREST_WEIGHT.glsl
```

The CPU control constructs a candidate whose endpoint costs pass but whose A-ownership check
fails, then gives its three neighbors positive weights. It reproduces the 7/16 leak and checks
that the nearest-weight rule refuses it. It also checks zero/equal-weight controls and rejects
missing or duplicated transform anchors. The CPU control is not a GLSL execution test.
