# Inverse2 with an independent endpoint-data guard

Registered 2026-11-13 before rendering this variant. The first geometric inverse
candidate improved face_fast's average score, but its inspected boundary still
tears. A smaller fixed-point residual does not prove that a selected foreground
or background root is the visible surface at the output pixel.

This second variant keeps inverse2's two candidate iterations and strict geometric
improvement test. It additionally compares each candidate with the currently kept
flow using the same full-resolution 3x3 endpoint support:

`mean | A(p + delta - t*f) - (B(p + delta + (1-t)*f) - b)/g |`.

The existing GLOBAL_GAIN value supplies g,b. Delta ranges over the nine pixel
offsets [-1,1]x[-1,1]. Accept only if geometry improves AND the endpoint cost
strictly decreases by more than 1e-6 in normalized luma. This tiny fixed tolerance
declares a numerical tie; no outcome will be used to tune it. On a tie retain
High/current flow. Reject either endpoint support outside the frame. The output
warp still uses original colour; the gain is used only for candidate evaluation.

Prediction: reject some newly torn face-boundary candidates, retain part of the
face_fast feature gain, and leave static/uniform-flow cases unchanged. Failure:
the boundary looks no better or worst-cell/feature errors grow, or new ladder
losses exceed the parent's registered limits. This is a candidate, not a proven
visibility solver, and a good average alone does not pass the boundary test.

Controls/risks declared before running:

- For an actual global light change, compare endpoints after the adopted global
  gain so a correct match is not rejected merely for that known illumination.
- A moving foreground can drive a wrong global gain; this guard inherits that
  adopted model's ambiguity and does not repair it.
- Local light changes remain uncompensated and can reject correct geometry.
- Occluded texture need not agree at both endpoints; an apparently better match
  can still be the wrong visible root. Inspect face_occluded and the silhouette.
- Uniform known translation and zero flow already have zero geometric residual;
  the strict geometry test must leave them alone. Exactly periodic endpoint costs
  can tie; the data guard must not treat equality as independent evidence.

`inverse_guard.add(text)` accepts the generated **inverse2** shader text, asserts
its expected sites, and changes only its final image warp pass. It has no circular
dependency on build.py. Generator wiring is checked locally without a GPU; the
parent owns rendering and outcome reporting.
