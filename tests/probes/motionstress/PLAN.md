# Motion stress: bars, pans and translating faces

2026-11-13, before GPU runs; user requested better synthetic tests and a bidirectional High improvement.
Baseline: shipped High at `474d70c`, including GLOBAL_GAIN=2. Local's Q5 is a separate, more expensive four-frame
line; this block stays in the two-frame family. The new scenes and exact laws are in SCENES.md/scenes.py.

Tests use continuous analytic scenes sampled independently at 24 and 60 fps, including finite bar patches with
anchors, fast whole-scene pans, and shaded face-like objects translating against another motion layer. They are
controlled face-feature surrogates, not a model of all real faces. Score interior synthesized frames, region and
feature errors, >.05 feature-error fraction and worst-one-percent regional error, not only full-frame PSNR.
Render errors, disabled shaders, frame-count mismatch and retained-source misalignment must refuse scoring.
Controls: static/slow motion, two-frame linear, repeated High, deliberate temporal shift. Inspect worst crops.

First candidate: **inverse transport of the A-indexed flow in the final warp**. Current High evaluates F at output
p, though source q solves q+tF(q)=p. Two bounded fixed-point proposals use the same resulting vector for both
source samples; accept only when they reduce geometric reprojection residual. Keep the original on a tie or worse
residual. This changes sampling geometry, not the motion estimator or occlusion policy. Costs several half-res
flow reads per output; must be timed. Constant spatial flow must give the original answer. At motion boundaries
the inverse can be nonunique or absent: this is a candidate with an explicit failure test, not a correctness claim.

Prediction: translating-face feature/edge errors improve; globally uniform pan interiors remain similar; bars with
wrong aliases may not improve. Pass for further gates: >=1 dB feature/ROI gain on at least two difficult new cases,
no static-control loss over .1 dB, no new-case feature/ROI loss over .5 dB. Kill or revise if failed, keep the failure.
A successful candidate must pass the full existing ladder (losses first, no case >.1 dB for replacement), bounded
real-footage comparison and repeat/timing checks before an adoption recommendation. Otherwise keep it experimental.
No automatic replacement of Cadence's resource graphs based only on the synthetic subset.

## Instrument correction and additional holdouts (before the second GPU block)

The first run refused pan_mixed's LINEAR retained frames (2.9208 codes). Source/truth common instants were bitwise
identical; Matroska's 1/1000 input timestamps were rounding 24fps source positions. The runner now assigns exact
1/120-second timestamps before libplacebo, and the entire 14-case run passed the original 2.55-code guard. The
refused log remains external; no threshold relaxed. Source imagery/encoding was unchanged.

Inverse2 passed the new numerical gate, but viewing the worst face crop exposed boundary tearing despite the
better feature average. A second geometry-plus-data variant is registered in INVERSE-GUARD.md. The independent
global witness has its registration in GLOBAL-PREDICTION.md. Before their GPU runs, add non-grid pan holdouts:
whole-scene speeds37 and43, and mixed-texture speed45 px/frame. The global witness's existing 8px proposal grid
may refuse these even if it fixes40/48; report that limitation, do not silently refine/tune to the holdouts.

The combined variant composes the two independently registered changes (inverse-data and global-fullres), with
no parameter changes. It must earn its own new-suite, photographic, full-ladder and cached-footage results; their
separate gains do not establish its safety. The full ladder is run against the fresh High baseline from this sitting.
Any loss over .1 dB bars in-place replacement; a modest aggregate gain never hides a losing case.
