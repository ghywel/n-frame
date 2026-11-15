# Estimator ablations — registered 2026-11-15

Status: diagnostic designs; no GPU result from either ablation at registration.
Input is the preceding High generated from current `content.HIGH_ENV` with `WARP_VOTE=0`, as
`ripple/build.py` generates `prev.glsl`. Do not apply these transforms to the adopted light vote,
the full vote variant, or the older Nov13 experimental inverse/global shaders.
The exact registered prior-High SHA-256 is
`b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece`; the helper refuses another input.

These are separate interventions, each compared with the same `prev` baseline. They are not
proposed production settings. The owner reports native playback ripples in translating clothing;
current field observations motivate testing but do not yet identify the mechanism. In particular,
the image replay and field-read calibration must support attribution before a gradient or fold
statistic is interpreted as a visible defect.

## 1. E temporal selection off (`prev-e-temporal-off`)

`add_e_temporal_off(text)` changes exactly the two 1/8-resolution refine passes' `trusted`
booleans to `false`. This removes both the temporal candidate C from the winner selection and
the temporal-distance prior on the competing candidates. Setting only `SEED_TEMP_LAMBDA=0`
would leave cached candidate C eligible, so would not perform this intervention.

The zero/ring/global candidate searches, non-temporal priors, propagation, Q/H stages and final
warp remain unchanged. The coarse temporal descent still executes but its E candidate cannot
win. Same-pair result caches remain active. **This is not all temporal memory off:** global-pan
persistence remains, and source-pair cache behavior is not being tested by removing it.

There is also a pre-existing asymmetry worth isolating: the E A→B pass checks old AB against old
BA, then overwrites AB's cache. The subsequent E B→A pass checks old BA against the newly written
AB cache. Thus that latter check is not wholly a previous-pair round trip. This ablation disables
both temporal trust checks; an improvement cannot distinguish cache-time asymmetry from a harmful
but correctly implemented temporal prior without a further experiment.

Registered predictions:

- If stale temporal selection contributes, final flow and the cloth picture can change between
  source pairs under this ablation, despite unchanged input frames and lead-in.
- Identical outputs reject E temporal selection as the cause on that sampled sequence.
- A smoother field alone does not establish better correspondence. Loss of stability or detail is
  a legitimate negative result, not a reason to adjust thresholds after seeing the pictures.

## 2. H data search/subpixel refinement off (`prev-h-data-refine-off`)

`add_h_data_refine_off(text)` overrides `best_off = base_off` immediately before the half-resolution
A→B search pass writes its cache. It therefore preserves the snapped Q→H seed and discards all
data-search and optional subpixel correction from **that one pass**. The present baseline's
subpixel switch is already off, but the name describes the full intervention rather than implying
that the downstream H variational stages have been disabled.

The four H variational iterations and two final H median passes remain byte-identical, as do all
Q stages, the Q field, support computation and final warp. Consequently the final field can still
vary spatially and can still receive H-level brightness-constancy corrections. The source search
code remains present and may be optimized away by the compiler; no speed claim is intended.

Registered predictions:

- The coarse and Q fields are unchanged; the first possible changed field is the H search output.
- If the H data search injects the relevant variation, this ablation reduces that component before
  the retained H variational/median stages. Native cloth detail may improve or deteriorate.
- Unchanged visible ripples do not prove all H processing harmless: its variational iterations
  remain active, and inherited variation can survive them.

## Comparison and controls

Use identical full-resolution decoded input, exact 24000/1001 → 48000/1001 timestamps, frame count,
lead-in and process validation. Compare the shirt and suit windows with both source endpoints and
the unchanged `prev` output. Do not crop the estimator input. Crop only diagnostic output or scoring.
Check source instants remain aligned. Inspect garment interiors and silhouettes separately.
Withheld-frame accuracy is a different stress condition because decimation doubles displacement.

```sh
python3 tests/probes/ripple/estimator_ablations.py e-temporal-off prev.glsl prev-e-temporal-off.glsl
python3 tests/probes/ripple/estimator_ablations.py h-data-refine-off prev.glsl prev-h-data-refine-off.glsl
```

The transforms refuse voting inputs, already modified inputs, missing/duplicated pass anchors and
unexpected selection/cache structure. CPU validation should confirm the original input is recovered
by reversing the exact substitutions, and that hook counts and all unrelated code are unchanged.
Neither transform nor a positive result in these two windows authorizes a shipped High replacement.

CPU source validation completed before GPU: a fresh prior High generated with the command above's
recipe matches the registered hash; reversing the two trust substitutions or the one H override
recovers that input exactly. Hook counts are unchanged. Eight wrong-base/already-modified/malformed
input checks refuse transformation. These checks do not execute GLSL.
