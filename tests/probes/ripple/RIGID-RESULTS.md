# Fixed rigid-plane / grain result — 2026-11-15

The four registered renders passed their instrument gates. A known rigid photographed plane gives a small
estimated-versus-exact picture error; adding 2 DN independent grain increases the raw error but does **not** increase
the pooled Gaussian-2 error here. This is not a reproduction or a cure of the owner's severe live-film ripple.
It supplies a controlled floor before introducing subpixel motion, deformation or visibility changes.

The construction, predictions and gates were registered in [RIGID.md](RIGID.md) before rendering. Frozen texture
moves by exactly (−16,0) pixels per source frame at native doubling. It contains clothing, faces and neighboring
scene detail, with original grain frozen into the material. It is not a garment segmentation. The 384×264 region
follows exactly the same material pixels; no estimated flow is used for measurement registration. Output 9…19
gives six inserted and five retained readings, with support frames 8/20 also alignment-checked. Lead-in is fixed;
it is not an independent convergence test of temporal history.

The two shaders differ only in final displacement: preceding High with coherence fallback off versus its oracle
copy with exact constant displacement. The source/cut/estimator code remains shared. Every complete renderer
sidecar, input/output hash, count, rate and registered shader hash was checked. Passing an oracle as the estimator
is an explicit refused counterfactual. All four renders contain 24 outputs from 12 inputs. No defaults changed.

## The instrument floor and the actual field difference

Retained-source maximum full-frame MAE is 0.3048 DN (frozen) / 0.3022 DN (grain), below the registered 0.5 DN
ceiling. Oracle midpoint RMS against the exact CPU blend is 0.3543 / at most 0.3670 DN, below the registered
1 DN ceiling. These are actual output conversion/quantization residuals; the ceiling is not measurement precision.
The GPU-oracle comparison below uses the **same output conversion**, avoiding an unequal comparison against an
unquantized ideal that ignores the oracle's own conversion error.

| Input | Estimated minus GPU oracle, midpoint RMS DN | Same, Gaussian-2 RMS DN | Difference curvature at inserted centers, DN | Same, Gaussian-2 DN |
|---|---:|---:|---:|---:|
| Frozen photographed plane | 0.54221 | 0.11730 | 1.08442 | 0.23461 |
| Same plane plus independent 2 DN grain | 0.69951 | 0.11455 | 1.39903 | 0.22909 |

Retained pictures are identical between the two GPU variants. Their difference therefore comes from the final
field choice in this controlled pipeline. The frozen-plane oracle is stationary in material coordinates **after
its fixed conversion error**: temporal curvature is zero. The estimated version has an alternating source/inserted
difference even without new grain. It is small in these pooled ROI readings; there is no human playback verdict
on this synthetic, and this table does not bound every local pixel error.

The added grain does not amplify the pooled low-pass field-choice error here (0.11730→0.11455 DN). That is a
negative result for strong amplification under these exact conditions. It does not exclude different noise,
subpixel motion, cloth strain, boundaries, motion blur, lighting or a different lead-in in the film. Integer
16-pixel motion deliberately excludes fractional sampling ambiguity.

## A clean-image score can favor a departure from known motion

With grain, midpoint RMS against the underlying clean material is **1.45677 DN for exact motion** and **1.33651 DN
for estimated motion**. Lower clean-image error does not mean more accurate correspondence: the true displacement
is known by construction, and the estimated output differs from the exact-field output. At Gaussian-2 scale the
order reverses: 0.24708 DN exact versus 0.26829 DN estimated. Inserted-centered temporal curvature against clean
truth is 0.82685 versus 1.37198 DN raw, and 0.12650 versus 0.23284 DN after Gaussian-2.

This is consistent with additional noise attenuation during imperfect warping, though the detailed resampling
mechanism is not separately measured here. It is a concrete reason not to treat aggregate reconstruction scores
as motion-correctness or temporal-comfort certificates. The same caution applies to the rigid-picture blend's
real-film numerical gain, which did not give the owner a clear visual improvement.

Realized decoded source noise is 1.99651 DN RMS on scored source phases; its exact CPU midpoint blend is
1.41226 DN RMS, close to the ideal √2 relationship. Gaussian-2 values are 0.28242/0.19959 DN. The CPU midpoint
chord residual is zero by construction. Oracle GPU curvature is not zero with grain because conversion errors
vary with noisy pixels; it must not all be called flow error. Of 2,764,800 generated source samples, 306 clipped
low and 1,491 high (0.0650%). Realized noise/covariance, rather than theoretical values, are preserved in
[rigid-results.json](rigid-results.json) alongside hashes and per-output comparisons.

## Reproduce

Use the external paths/tool variables from [README.md](README.md). Fixture/score commands are CPU operations;
only `render.py` runs the GPU, serially. Generated images/videos remain external.

```sh
"$RIPPLE_PY" tests/probes/ripple/rigid.py prepare "$RIPPLE_RUN/shirt-source.mkv" "$RIPPLE_RUN/rigid"
mkdir -p "$RIPPLE_RUN/rigid/shaders"
"$RIPPLE_PY" tests/probes/ripple/rigid_oracle.py "$RIPPLE_RUN/shaders/prev-no-fallback.glsl" "$RIPPLE_RUN/rigid/shaders/oracle.glsl"
for condition in frozen grain; do
  "$RIPPLE_PY" tests/probes/ripple/render.py "$RIPPLE_RUN/rigid/$condition/renders" "$RIPPLE_RUN/rigid/$condition/source.mkv" \
    --ffmpeg "$RIPPLE_FF" --ffprobe "$RIPPLE_FP" --shaders \
    oracle="$RIPPLE_RUN/rigid/shaders/oracle.glsl" estimate="$RIPPLE_RUN/shaders/prev-no-fallback.glsl"
  "$RIPPLE_PY" tests/probes/ripple/rigid.py score "$RIPPLE_RUN/rigid" "$condition" \
    oracle="$RIPPLE_RUN/rigid/$condition/renders/oracle.mkv" estimate="$RIPPLE_RUN/rigid/$condition/renders/estimate.mkv"
done
"$RIPPLE_PY" tests/probes/ripple/rigid.py controls "$RIPPLE_RUN/rigid"
```

For nonstandard tool paths, `rigid.py --ffmpeg ... --ffprobe ...` takes these options **before** the subcommand.
The portable record selects measurements from full external score files and records their SHA-256 values;
rerunning the scorer produces all recorded numeric readouts.

Next useful extension is a separately registered known deformation of this same plane, with exact inverse and
forward field available. The historical coarse-search strain failure is relevant prior evidence, not proof that
it explains this film. Preserve this rigid control, including its residual and the noise-ranking counterexample;
do not tune it until it resembles the reported ripple.
