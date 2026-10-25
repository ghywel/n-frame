# Review for Local: what the effects can import into interpolation

2026-10-25; response to L022, reviewing `24c5412`. Read L018-L022, the
[import record](../../../IMPORTS-TO-INTERPOLATION.md), the generators, diagnostic tools, effect bodies and saved
results. Predictions precede the runs in [REVIEW-PREDICTION.md](REVIEW-PREDICTION.md); executable checks are in
[review_attacks.py](review_attacks.py). No shipped shader, generator or default changed.

**Recommendation:** keep the four measured kills. Both open designs need another source of discriminating evidence,
or an explicit ambiguous outcome. Longer history does not make alternation unique to drawing cadence; competition
at the coarse level does not make light and motion identifiable on a ramp. There is also a coordinate defect in
LOCAL_LIGHT=2 and a demonstrated silent-failure path in the cadence scorer to address before another quality gate.

The imports share temporal evidence, but their input requirements differ:

| Evidence or operation | Available input | What transfers to interpolation |
|---|---|---|
| Coherent brightness change | One retained pair | The cue can run in the shipped two-frame tiers; it does not require the eight-frame spectrum. |
| Temporal spectrum | Eight timestamps and pixels | A diagnostic of temporal variation; replacing it with the one-pair cue changes what is measured. |
| Alternation / existing cadence re-timing | Four ordered slots | The quad can both see an alternating pattern and access the next distinct drawing used by its warp. |
| Six-frame median / trajectory residual | Six retained frames | Extra reference/support, with visibility and motion ambiguity; median success alone does not identify a safe fallback. |
| Stored history | Past source observations across calls | Can supply persistence to a two-frame tier, but cannot supply the next unseen drawing across a held pair without added lookahead or prediction. |

In particular, sharing a storage mechanism does not make the quad's re-timing formula directly implementable in
a two-frame window. History, future context and the output's interpolation phase must stay separate in the design.

## 1. A continuously moving print alternates for as long as the history lasts

This answers the specific request for twelve consistent frames that are **not** drawing on twos.
Let a material strip have period 256 px, two intensity plateaus of width 128 px, and translate right at a constant
64 px **every source frame**. Look at a fixed 32x32 cell, x in [16,48). Every sampled cell is wholly inside a plateau;
the sequence alternates moving/held forever. Smooth eight-pixel transitions between plateaus make the underlying
continuous motion smooth too. Add a stationary-in-y sinusoidal texture of amplitude .08 to the strip: the cell
has real spatial contrast even during its locally flat horizontal plateaus.

Measured by the CPU probe over **48 frames / 47 pairs / 45 four-frame windows**:

| Test | Qualifying alternating windows | Largest held difference | Smallest moving difference |
|---|---:|---:|---:|
| Dense 32x32 cell, constant +64 px/frame | **45/45** | **0** | **.4 (102 codes)** |
| Existing 5x5 taps at 6 px spacing, period 12, constant +3 px/frame | **45/45** | **0** | **.4 (102 codes)** |
| Stationary textured control | 0/45 | 0 | none |
| Generic textured pan control | 0/45 | none | .1032 |

The second construction uses the actual footprint and LC_DUP=.012 from
[gen_quaddirectional.py](../../gen_quaddirectional.py), with square stripes six pixels wide. Its tap spacing
preserves the temporal hold phase. This is a sparse-sampling alias; the first construction **also works with dense
sampling**, so changing the tap pattern alone is insufficient. Dense-cell spatial standard deviation is .05775,
above the diagnostic's 4-code texture threshold. Dividing an exactly zero held difference by contrast still gives
zero. Any history length sees the same pattern by periodicity, not just the tested 48 frames.

This establishes false *cadence evidence*. It is **not a measured picture regression of a history shader**, which
does not yet exist. A local A,A,B,B observation also has a literal held-drawing explanation with identical samples;
no decision using only that observation can prove which physical history generated it. Elsewhere in the moving
strip, a different hold phase supplies useful contrary evidence. Spatial phase agreement can therefore help this
case, but it must be tested across layers and occlusions rather than treated as a universal proof.

**Before building:** add both fixtures, require a region's evidence to survive a constant-motion explanation, and
carry an unknown state on ties. A known nonzero displacement/seed or an informative boundary is a control: an
already unobservable baseline returning zero does not establish a cadence-induced loss. Contrast normalization
addresses the low-contrast ladder failure, not this exact alias. History can improve statistical confidence on
ordinary footage, but repeated samples of the same alias are not independent votes.

The native fixture is `constant-speed-history.npz` in the external run folder: 48x144x512 working-luma samples,
ROI and full-pixel displacement included. It has no implicit video transfer function or claimed GPU result.

## 2. Coarse light-versus-motion selection must not award light an exact tie

The proposed rule is “take the offset where it explains the cell at least as well as any motion does.” For
`A(x,y)=c+a*x+b*y`, true horizontal translation d gives `B(x,y)=A(x-d,y)=A(x,y)-a*d`.
Both the correct motion and **zero motion plus offset -a*d** explain every pixel exactly. That survives dense
sampling and all pyramid levels. The probe uses d=4 and a=1/128: a 7.96875-code change, both residuals **exactly zero**.
The rule's equality arm therefore selects the wrong physical explanation.

Opposite positive controls pass: a generic textured pan has zero correct-shift residual but .17197 RMS under
zero-plus-offset; a stationary random texture with +.04 lighting has essentially zero compensated residual and
best raw-shift RMS .04. Thus competition can discriminate informative scenes. It cannot resolve an exact tie.

Compare candidates on the **same support, radiometric scale and refinement opportunity**, and distinguish
`motion wins`, `light wins`, and `indeterminate`. Requiring strict improvement prevents this particular tie from
becoming evidence for light; it does not by itself calibrate a reliable threshold or fix alias-induced wrong winners.
A local test can report how much of the image gradient survives projection away from the fitted light basis:
for offset-only compensation, subtract each gradient component's spatial mean before constructing its 2x2 Gram
matrix. A ramp loses its informative gradient completely. Low eigenvalues mean that motion and offset cannot be
separated on that support, not that motion is zero. This is a diagnostic proposal, not a validated new shader gate.

GLOBAL_GAIN=2's adopted trade remains the owner's decision. This review does not ask to reverse it. The present
issue is avoiding the same ambiguity in a new local decision that can affect a much larger class of moving edges.

## 3. LOCAL_LIGHT=2 stores an A-indexed residual and reads it as B-indexed

In [global_gain.py](../../global_gain.py), LIGHT2 measures
`r_A(x) = B(x+v(x))-A(x)` and saves the grid at **x**, frame A's coordinate. HELPER_LOCAL instead subtracts
`LOCAL_LIGHT_tex(uv)` at every **NEXT** read's coordinate uv. For a matcher reading B at y=x+v, that is r_A(y),
not r_A(x). This is harmless for v=0 or spatially constant residuals; neither is true in general.

For known translation d and `B(y)=A(y-d)+L(y)`, the grid ideally stores `r_A(x)=L(x+d)`.
The helper leaves `L(x+d)-L(x+2d)` after compensating the correct match. In the CPU control, d=8 and
`L(y)=.08*sin(2*pi*y/64)`: **.0432957 RMS, or 11.0404 codes**, remains. Correctly transporting the residual gives
**zero**. Both zero-motion and constant-light controls mask the fault, as predicted.

This isolates the coordinate convention using a dense residual and unity gate; it is **not** a numerical claim
about the actual smoothed/gated shader's output or an explanation of all its measured loss. Still, the mismatch
is in the source. Any successor using this residual must either transport it onto B with visibility handling,
or retain it in A coordinates and apply it to candidate residuals at the corresponding A support. Bilinear
sampling does not perform inverse motion transport. Under disocclusion, the inverse may not even exist.

Consequently, “mode 2 was too late in the pyramid” remains a plausible mechanism, not the only isolated cause of
its failure. The two killed variants alone do not prove the toaster's wrong motion was decided exclusively at
the coarsest level. Tap the candidate/cost trajectory or use a controlled seed if that stronger claim is needed.

## 4. The cadence scorer can publish a good score after a failed, truncated render

[cadence_scenes.py](cadence_scenes.py) checks only the text `compile status`, ignores render and decode return
codes, and scores `min(len(output), len(truth))`. Its decoder similarly accepts any complete-frame prefix.

The review executes that **unchanged scorer** with injected subprocess replies: render return code 1 with
“Disabling custom shader”, decode return code 1 after **30 frames against 180 truth frames**. It prints
**40.00 dB for all four scenes**, without refusal. This is a reproduced harness failure, not a hypothetical warning
and not an assertion that Local's real runs failed. Read-only packet checks on all four saved mode-2 videos show
180 video packets, 1280x720 at 60 fps; those particular files do not exhibit the injected truncation.

Before the next gate, require successful processes, a hook-execution/fallback check, expected frame count and
timestamps, nonempty scoring sets, and source-alignment controls. Refuse a partial prefix rather than silently
changing the scored interval. The diagnostic [diagnose.py](diagnose.py) has a related risk: `zip` stops at the
shortest stream and `stream()` neither checks child exit status nor rejects a short final frame. These should
become separate fail-closed checks, preserving the actual endpoint/window allowances explicitly.

The injected-failure check currently **asserts the reviewed defect exists** so the review is reproducible.
After Local repairs the scorer, that assertion should fail; replace it with an expected-refusal regression test
rather than weaken the repaired scorer to keep this historical attack passing.

## 5. Spectrum is a temporal-change instrument, not a light-versus-motion discriminator

Unexpected side check: a uniformly translating sinusoid `I(x,t)=c+a*sin(2*pi*(x-v*t)/P)` produces a temporal
sinusoid at every fixed pixel, frequency v/P cycles per source frame. Detrending removes a line in intensity,
not a constant velocity through a textured scene. Thus the body comment “a steady pan or slide stays dark” and
the effect record's “only what goes back and forth lights” are too strong.

CPU reproduction of the actual eight-sample detrending and DFT, P=16, v=4, amplitude .1:
residual energy **.00496375**, weighted bin **1.99676**, equivalent to **5.9903 Hz at 24 fps** (true temporal
frequency 6 Hz). Constant and linear-intensity traces give zero/numerically negligible energy.

**GPU confirmation on the M5:** the unchanged [spectrum shader](../../../shaders/effects/spectrum.glsl), 16
grayscale input frames at 192x96/24 fps. Both outputs contain exactly 16 frames; interior frames 4-11:
constant-gray mean RGB channel spread **0**, uniform-pan spread **.33548**, passing the registered <.005/>.05
checks. The pan visibly glows green. A grayscale fallback could not produce that colour. No compile/disable
error; input/output, logs and a viewed side-by-side PNG are external. This is the only new GPU test in this review.

The toaster's green grille remains useful localization of temporal variation, consistent with the independent
still-frame light experiments. Spectrum alone does not establish its physical cause or a single oscillation
frequency: its hue is a **power-weighted bin centroid**, and bins are f*source_fps/8. At this TV source's 25 fps,
bins 2 and 3 mean 6.25 and 9.375 Hz, not exactly 6 and 9. A multiband trace can have the same hue. Keep the light
diagnosis tied to the controlled photometric evidence, and describe the spectrum as supporting evidence.

## Diagnostic interpretation and the next block

The stored `imports.json` supports D1b's five lift improvements and the measured harm from blind blend swaps.
Two wording corrections matter:

- D2b registered **20%** on-twos moving cells in both animation classes. Measured cartoon **16.7404%** and anime
  **8.4956%** miss that prediction. Cartoon mixed stretches **18.1940%** passes its separate 10% line, and the
  controls are low. Call this a partial result and a useful target; not a complete registered pass or proof that
  every flagged cell is a held drawing.
- Top-one-percent D1b precision equals base rate times lift. Recomputed from saved results: film **4.60%**,
  TV **6.18%**, anime **32.54%**, cartoon **18.85%**, CG **8.92%**. “About 6%” is not a cross-window summary.
  The actual error-weighted swap calculation remains the stronger reason not to replace the warp blindly.

Those diagnostic labels came from **pre-GLOBAL_GAIN High**. The new mechanism's baseline is the adopted High
with GLOBAL_GAIN=2. Some photometric targets are already repaired; quantify the residual target on that baseline
before attributing the old lift to a new switch. Keep the five discovery windows in-sample, and reserve separate
bounded footage windows for a later generalization gate. No additional NAS footage was read in this review.

Suggested next block, in order:

1. Repair the fail-open scorer and run its deliberate failure controls before any long batch.
2. Correct/declare residual coordinates and add the known-motion-plus-spatial-light control.
3. Register a three-outcome coarse comparison with the ramp/periodic counterexamples; measure field and picture
   separately, retaining the current kills and the adopted GLOBAL_GAIN trade.
4. Treat history as extra evidence, not the deciding rule. Before a storage implementation, specify fixed-cell
   versus tracked-region history, spatial cadence-phase checks, visibility/reset rules, and behavior on ties.
   Repeated calls at output rate must not become extra source observations; cuts/seeks must not inherit confidence.

## Reproduce and evidence boundary

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/imports/review_attacks.py "$NP_SCRATCH/imports-review"
# Optional, actual spectrum GPU check, with the patched executable:
PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/imports/review_attacks.py "$NP_SCRATCH/imports-review" \
    --gpu-spectrum "$PATCHED_FFMPEG"
```

NumPy and SciPy (for exercising the existing scorer) are required. Source SHA256 values are saved in `results.json`;
the actual spectrum shader hash is saved separately in `gpu-spectrum.json`. This run:
`$NP_SCRATCH/imports-review-20261025/`. Existing evidence read: `cadence-20261025/analyze2.txt`,
`light-20261025/t13-light2.json`, and `prospect-20261023/imports.json` under the same scratch root.
All analytic/positive/negative controls pass; the deliberate scorer fault is demonstrably accepted. No full ladder,
new interpolator render or native-footage quality result is claimed. The proposed fixes remain unbuilt.

Reasoned verdict: the cross-pollination has useful measured targets, but the two next designs need explicit
ambiguity handling. Attention verdict: persistence looked like stronger evidence until the exact periodic
counterexample showed it was repeating the same uncertainty.
