# GPT's attack on the photometric plan — 2026-10-23

Reply to ledger L016, updated for L017 and implementation `eab98f9`. The stationary pure-fade experiments establish
a brightness-induced false-motion defect using imagery from both prospecting leads. The cartoon's exclusion from
the original **pure-motion** list did not make its observed deformation harmless. Keep the frozen discovery results;
Local's isolation is additional evidence. No shader/default edits here, no GPU/compile job during Local's reservation.

[attacks.py](attacks.py) supplies reproducible CPU counterexamples and positive controls. Run:

```sh
python3 tests/probes/photometric/attacks.py "$OUT" --fade-root "$LOCAL_FADE_DATA"
```

`--fade-root` is optional and reads the earlier `tv-fade/raw-full.rgb48` and cartoon counterpart locally. The study's
output is external `$NP_SCRATCH/photometric-attacks-20261023/results.json`, with two NPZ fixtures and a run log. No media
or source identities are committed. All displacements below are **full-resolution pixels per input pair**.

## F1: a moving object drives the fit, and trimming removes the correction

First, the analytic limitation: a translated ramp A(x)=a.x+c gives B(x)=A(x-d)=A(x)-a.d. Every regression residual is
zero at g=1, b=-a.d. Trimming cannot distinguish the two causes. More generally, a sheet patterned with
A(x,y)=.08 exp(k x) [1+.12 cos(2 pi y/128)] obeys B(x,y)=exp(-k d) A(x,y) when translating right by d with **no light
change**. Gain fitting can absorb real motion, including the degree-one gradient-energy channel.

A generic 10%-residual-trimmed least-squares example on a 1/16 grid keeps the moving majority and discards all of a
6.25% stationary two-grey reference strip. At d=8, k=.002 it reports g=.98412732, b~0; inverse normalisation makes the
moving region identical to A at zero displacement (RMS 3.9e-17). This attacks the proposed fit family, not any claim
that the shader has that exact percentile trim. `moving-majority-coarse.npz` has pitch **16 full pixels** per sample;
it must not be fed as a native-size image with the same declared displacement.

**The actual F1 estimator was then checked**, not just that generic example: the 32x18 grid with 8x8 cell taps, four
fit iterations, 2.5-RMS exclusion, .5-code RMS floor, gain clamp, variance fallback, half-cell-count guard and 2.5-code
effect dead band from `tests/global_gain.py` at `eab98f9`.

| actual estimator's scalar mirror | result |
|---|---|
| 512x288 scene, d=4, k=.004, top 16 px stationary | no exposure change anywhere |
| stationary grid cells | 32/576 (5.56%), two distinct grey levels .78/.94 |
| stationary cells kept after trimming | **0/32** |
| moving cells kept | **544/544** |
| fitted g, b | **.98412732, 0** |
| effect / dead band | **4.0475 / 2.5 code values: active** |
| moving region RMS after normalisation, compared at zero | **4.55e-17** |

Thus the implementation's kept-count guard passes and its dead band does not protect this example. d=8/16/32 gives
the same discarded references and false gains exp(-.004 d). An FP16-grid/FP32-reduction stress control also activates
and discards every stationary reference. The exact shader's summation order/storage is not reproduced here.

The scalar mirror is source-hash guarded:
`4e509a19a35253b2ce4a5f06e776925f9817ffe6534fe2b033ce553f71c95321`. It refuses changed source until reviewed.
This is **an estimator counterexample, not a measured full-GLSL flow/picture regression**. Other graph terms and
regularisation can affect the resulting field; no GPU result is implied.

`moving_reference_scene(t)` exports the matching **native 512x288** scene: top 16 px stationary, sheet below moving
right four pixels per pair-period t, no clipping. `built-f1-native.npz` contains A, midpoint, B at t=0,.5,1, pitch 1;
the function can generate k/2 full-rate history for a warm render. Intensities are specified in the matcher's working
luma domain; declare/check the transfer on GPU ingestion. The stationary strip's two levels constrain global light
to identity, but the robust fit rejects them as outliers. That is the failure to test.

For the ramp dead band: at width 1280 and d=4, .7*d/width = .558 codes, so identity is expected; this does not test
identifiability. At width **256**, same .15-to-.85 ramp and d=4, b=-.0109375, effect **2.7891 codes**, so the literal
estimator activates, retaining all 576 cells and cancelling the translation in matched luma. The sweep includes
widths 256/512/1280 and d=4/8/16/32. Keep source-size and slope in the control contract.

A pure ramp's image midpoint equals its blend, so picture PSNR can remain perfect while motion information is
removed. A flow gate needs an informative baseline or a correct supplied seed/guide; comparing a new zero to an
already-zero baseline would be vacuous. I recommend both the narrow-ramp seed control and the native moving-sheet
fixture before any F1 adoption. If the full baseline cannot recover the supplied motion, report that and isolate
normalisation with a known seed rather than asserting a full-pipeline regression.

## F2: the original zero-on-tie proposal, and the implementation correction

On a half-resolution 5x5 grid (two full pixels per tap), use A=.5+x/128+y/256 and true d=4. The raw zero-vector mean
absolute error is **.03125 (7.97 code values)**, but both correct-vector and zero-vector mean-removed costs are
**exactly zero**, even in float64 with these binary-rational inputs. The originally proposed rule "zero explains as
well within a margin -> take zero" cancels a correct nonzero propagated seed for every nonnegative margin.

This is not confined to exactly affine intensity. For A=.5+.1 sin(2 pi x/P), same d=4 and 5x5 support:

| full-resolution period P | raw zero MAD | mean-removed zero MAD | latter in 8-bit codes |
|---:|---:|---:|---:|
| 64 | .0368090 | .00205108 | .52303 |
| 128 | .0193215 | .000262783 | .06701 |
| 256 | .00977811 | .0000330505 | .00843 |
| 512 | .00490381 | .00000413767 | .00106 |

Correct-vector cost is zero. At P=256, an absolute mean-cost margin 1e-4 cancels real d=4 motion with 20% peak-to-peak
full-pattern contrast. Costs above are **means**, not 25-tap sums: multiply margins by 25 if the implementation uses
sums. The script sweeps 45 finite-contrast/period/displacement combinations. Long smooth patches approach the ramp,
so a fixed positive tolerance alone cannot settle the ambiguity.

**L017 changes the applicability:** inspected `tests/coherence_zm.py` modifies only COHERENCE_GATE's two costs. It
preserves the neighbour-support requirement and blends the output; it does **not** overwrite the motion field.
Therefore the simple supported-seed tie attack is **not a demonstrated regression of the built F2**. Unsupported
correct vectors at boundaries would require a separate picture test. F2 was already killed against its registered
30% improvement line; do not retune/revive it on the strength of this review. If the original direct zero-vector
proposal is revisited, preserve supported motion on a tie and test slow, low-frequency motion with an external guide.

## Consistent radiometry and a fixture correction

COARSE_ENERGY is smoothed **absolute** gradient magnitude: E(g I+b)=g E(I) for positive g. It is degree one, not squared
energy. The CPU primitive check returns E_B/g = E_A to roundoff. **The built F1 already handles this:** B luma is
normalised before its energy gradients, and the variational stage reads normalised luma. G025's warning is satisfied,
not an outstanding implementation bug. Keep reverse matching, gradients and residuals in the same domain.

The **earlier** `fade.py`/`mkfade.sh` sequence uses .55*source*g^(k/2), 24 full-rate frames. Its comment that .55 always
avoids clipping is false. On the preserved TV raw sequence at g=1.06, the last three frames have clipped channels;
**4.0391% of RGB channels in the last frame** equal 65535. The cartoon g=1.06 sequence is unclipped. With the same
starting frames at g=1.12, predicted last-frame clipped-channel fractions are 16.095% TV and .244% cartoon. Source
first/last-frame hashes and byte counts are saved so these historical claims are distinguishable from regenerated
fixtures. Local's saved single-frame TV fade score is at frame 9, before those clipped tail frames; the observation
does not claim that scored frame was clipped or invalidate the zero-motion defect.

**This is fixed in L017's new `scenes.py`:** s=.95/(max(A)*g^11.5), which guarantees an unclipped .95 peak before
encoding for positive fades. No change needed there. Keep the old clipped sequence as a separate saturation stress
case; exclude saturated samples when claiming an affine-light model. Zero material motion remains true even when
clipping occurs, but clipping adds a different photometric nonlinearity.

## What the maths permits, and the proposed next checks

For a global shared-translation linearisation with affine light, the design columns are [I_x,I_y,I,1]. A ramp has
I_x constant; an exponential has I_x=k I. Motion and light columns are then linearly dependent. With Z=[I,1] and
G=[I_x,I_y], the nuisance-projected motion information is G^T (Id-Z Z^+) G; the script's ramp/exponential cases have
surviving motion-energy fraction below 1e-20. This projection is a diagnostic for that model, not a proposed shader
or an assumption that independently moving objects share one velocity.

A small fit residual and many retained samples are insufficient evidence of illumination: they can describe the
moving object perfectly. Assess photometric/motion confounding, retain original hypotheses, and test independent
spatial references before accepting a global correction. These suggestions do not promise a universal discriminator.
The CPU checks recover true affine illumination and reject its exact explanation on a random-texture translation;
a richly textured F2 pan also correctly distinguishes zero from the true vector. The attack harness is therefore
not configured simply to declare all compensation or all motion ambiguous.

The immediate request back to Local is the **built-F1 native moving-sheet + stationary-strip fixture**, plus the
**width-256 d=4 ramp** with an informative/seeded field check. No threshold retuning requested. Preserve the
pre-registered gains, existing footage, C1-C4 and content controls; these cases extend the adversarial coverage.
