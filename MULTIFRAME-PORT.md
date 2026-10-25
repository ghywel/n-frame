# Porting the High lineage up the multi-frame family, starting with the tri

*Opened 2026-10-25 at the owner's word: "It had not really occurred to me that we have not been porting our techniques
in the bidirectional up the chain to the higher frame variants. The > 2 frame shaders are practically sitting bare ...
Can we start with an investigation into the 3-frame shader, see what can be moved up and how that improves its
performance, particularly vs the bi-directional High." The same day's measurement (NFRAME-LIMITS.md, "The multi-frame
family against today's tiers") put today's High 0.6 to 2.1 dB above the tri on every class of real footage, and the
tri under Low too.*

## What the tri is today, read from its generator (`tests/gen_tridirectional.py`)

- **Its base is the plain propagated two-frame shader** (`bidirectional-interpolation-propagated.glsl`, 28 passes), not
  any tier. High (86 passes) is that base plus thirteen generator switches (`gen_variational.py`, `global_gain.py`,
  `bar_redecide.py`): the variational refinement and medians at 1/4 and 1/2, the global seed, the coherence gate, the
  coarse texture energy, the alias basins and their carry, outline adoption, the print lattice, the motion-compensated
  cut statistic, the global gain, and the prune. None of it is in the tri.
- **It was built as a field instrument, not a picture shader.** The generator turns sub-pixel refinement and its
  self-referenced fit on (off in every picture base: "fractional flow only costs it resampling sharpness") and adds a
  full-resolution level, both for the acceleration field's sake.
- **Its final pass is a plain warp** of the straddling pair plus the quadratic correction 0.5 a s(1 - s): no occlusion
  handling, no support or agreement test, no motion-compensated cut gate, no gain compensation. High's final pass has
  all of these.
- **It is slot-keyed**: four adjacent-slot flows (F01, F10, F12, F21), each a full copy of the base's flow chain, because
  the straddling pair's roles rotate inside a fixed three-frame window and a role-keyed cache goes stale (the generator's
  own history). Porting High the same way means one full High estimator per slot pair: about twice High's passes and
  time, unless the sticky cache (patch stage 2) or a stored previous pair carries one of them over.

## Step 1: where today's gap comes from (pre-registered 2026-10-25 18:30, before any of it runs)

Six shaders in one sitting on the M5 (`~/np-scratch-int/port-20261025`): today's High; the plain propagated base
(`biprop`, the tri's own base); the tri as shipped; the tri with its acceleration term zeroed in the output warp
(`tri-noaccel`, the warp's `accel_w` set to zero, the field and diagnostics untouched); the tri in picture mode
(`tri-pic`, sub-pixel refinement and its self-referenced fit off at all eight sites); and both (`tri-pic-noaccel`).
Each runs the 45-case ladder (`bench.sh all`, capped means) and the content test's 40 windows (`content.py`,
`INTERIOR=1`). The chain reads, link by link:

| link | difference | what it isolates |
|---|---|---|
| D1 | tri - tri-noaccel | the acceleration term itself: what three frames buy on this base |
| D2 | tri-pic - tri | the field-mode sub-pixel refinement's cost to the picture |
| D3 | tri-pic-noaccel - biprop | the tri's structure without acceleration: the full-resolution level and its plain final pass, against the base's |
| D4 | High - biprop | the High lineage on two frames |

**Predictions** (from the record: the 09-04 real-footage tie, the acceleration ladder cases, the base's comment on
fractional flow):
- **D1 on real footage: within +-0.10 dB in every class** (predicted 0.00 to +0.08); on the ladder, +1 dB or more on most
  of the acceleration cases (A1-A7, F2) and within 0.2 dB on the constant-velocity cases.
- **D2: 0.00 to +0.30 dB** on real footage (picture mode sharper); within 0.3 on the ladder.
- **D3: -0.10 to -0.40 dB** on real footage (no occlusion or cut handling in the plain final pass).
- **D4 reproduces the tier gap**: High 1.3 to 2.1 dB over the base on film and CG, less on television and animation.

**What decides the next step** (fixed now): a ported tri can at best be about High + D1 on real footage, if the gains
add. **If D1 is at most +0.05 dB in every class**, three frames add nothing High lacks on real footage and the full
slot-keyed port (twice High's cost) is not justified for it; the port is then aimed at the acceleration content the
ladder holds, in its cheapest form (High's estimator once, the other pair's flow from storage or from the sticky cache),
and judged on the ladder and the cage. **If D1 is +0.10 dB or more in any class**, the full port is built first. Between
the two lines, both forms are designed and the cheaper is built first.
