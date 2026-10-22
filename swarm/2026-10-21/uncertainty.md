# The uncertainty map: a per-texel error bar for the field

*Design on paper, 2026-10-22, the wildcard lane, at Gareth's go ("a useful tool to have regardless"). Nothing built.
Plain prose for a reader who knows the project. [R] read in the record, [J] judgement, [U] unverified.*

## 1. What it is for

The field today gives one number per texel and no word on how far to trust it. Everything downstream must therefore
treat a confident wrong reading and a confident right one alike. Four concrete uses in this project:

**Lily's Party.** The puppet is driven from the field. When a child's arm passes the reach cliff (24 px/frame against a
textured room, WHAT-IT-CAN-MEASURE 93 [R]) the field snaps toward zero or locks on the background, and the rig cannot
tell that zero from a measured zero: the puppet's arm stops or jumps. With an error bar per texel the rig weights each
bone's texels by 1/sigma^2, holds the last trusted pose where sigma is high, and fades back in as it falls. A snap
becomes a hold.

**Cadence's picture.** The cage, the railing, C3 and D1 fail the same way: the recommendation locks a wrong alias on
100% of the interior with 0% flips (SWARM-2026-10-21.md, the D1 row-sign read [R]) and warps it with full confidence.
The record's own answer, "warp where the flow is trusted, blend where it is not" (NFRAME-LIMITS 4040 [R]), has no trust
channel to read. The map is that channel: the blend becomes a fade in sigma. Item 10 added a second need: a switch that
gains +19.7 on one class and loses 6.7 on another wants a per-texel cue to choose by.

**The science.** Every headline field number is a mean over the object eroded by 40 px (WHAT-IT-CAN-MEASURE 28-31 [R]).
A per-texel sigma lets the mean be weighted, a gross texel be flagged rather than averaged in, and "reads at 118 to one"
become a distribution with a quoted coverage. PIV ships this beside every vector field [U: training, no citation].

**A downstream user.** A robotics user fuses the field into a Kalman filter, which needs a covariance per reading;
without it the filter assumes one noise for the frame and either trusts the lock or distrusts the good texels. A
sports-analysis user reports a limb speed with a +- and a refusal where the instrument cannot see (a limb along itself
reads 0.5, WHAT-IT-CAN-MEASURE 96 [R]).

One limit first. D1 shows a coherent lock is invisible to every single-frame local cue: the match is good, the
neighbours agree, the flow is steady. So the map carries two things: **noise** (how far a reading scatters) and
**ambiguity** (whether a second answer fits as well). The lock reads low noise and high ambiguity; a map that only knew
noise would bless it.

## 2. What to compute

Candidates the passes already have, or nearly have, each with its cost. Resolutions differ; all are upsampled to the
field's grid at read time.

| cue | what it measures | where it lives today | cost |
|---|---|---|---|
| **Alias margin** `ALIAS_E_M_ST.xy`: rival minus best, in units of the cost curve's rise, both directions, per 1/8 cell (alias_carry.py 78-81 [R]) | ambiguity: a period alias in reach ties at 0 | the carry tiers (High); not the recommendation | 0 passes there; 1 pass at 1/8 elsewhere |
| **Peak ratio Q** = cost_b / cost_a of the fused coarse pass's zero and ring descents, where their basins are >= 0.75 texel apart (the pass computes both; wildcard.md proposal 2) | ambiguity at 1/16; the in-reach alias item 10 exposed | the fused coarse pass, every shader | 2 registers and one store; 0 passes |
| **Sext LSQ residual**, mode 6 (SEXTDIRECTIONAL.md 32: "computed but never shown" [R]) | noise of the five-link fit, in px | the sext only (the quad and quint fit exactly, residual zero by construction) | 0 passes; unmeasured |
| **Forward-backward consistency** `|f_AB(x) + f_BA(x + f_AB(x))|`, px | noise and occlusion: one direction found another surface | both directions live in the N-frame shaders (the fit needs them); in the two-frame recommendation PRUNE cuts the B->A chain's end (FLOW_H_BA, the cost census [R]) | one gather in the tail; 0 passes in tri/quad/quint/sext [U] |
| **Coherence support** (the cage's gate: the share of neighbours within tol_px, radius 4; gen_variational.py add_coherence_gate [R]) | spatial agreement; low on a scrambled match | the cage tiers | 0 passes there; 1 pass at 1/2 elsewhere |
| **Temporal flip rate**: per-texel EMA of `|f_t - f_{t-1}| > 2 px` in the persisted cache | the D1 cue: High's interior flipped on 100% of frame pairs, the recommendation's on 0% [R] | nowhere yet; the cache has a spare channel | 0 passes; one channel |
| **Texture and aperture**: the smaller eigenvalue of the image structure tensor at 1/4 | "no measurement" (sky, wall) and the aperture direction (a lone edge: one eigenvalue near 0) | the coarse contrast gate is a scalar; the tensor pass of read_view 9 is the FLOW's gradient, not the image's | 1 pass at 1/4 |

Ship the cues raw first; fit one sigma afterwards (section 4). The scalar form I expect to survive calibration [J]:
`sigma^2 = sigma_0^2 + a * FB^2 + b / support`, with `sigma_0` the measured floor (0.4 px on the bench), and a separate
**ambiguity flag** from the margin or Q (a flag, not a sigma: a tie is not noise).

## 3. How it is output

A new machine mode in the reading tail, **read_view 10** (9 is the tensor; add_human_reading.py 109 [R]), raw:
R = sigma in px/frame, encoded as mode 4 encodes velocity, `0.5 + f * (0.5 / FS)` with FS 32, which the fp16 probe
measured at a 1/32-px step (fp16floor.sh header [R]); for sigma above 16 px the two-channel form from the same probe
(fraction in G, packed whole parts in B). G = ambiguity (the margin, clamped to [0, 4] rises, or Q - 1). B = a flag in
eighths: 0 measured, 1 ambiguous, 2 no texture, 3 cut- or occlusion-gated. Mode 11, for a human: the velocity painting
with saturation `1 / (1 + sigma)`, so a trusted reading is vivid and a doubtful one grey, and the ambiguous flag hatched.
The Metal app paints the same two views under Show (lockstep.sh after either side moves). analyze.py gains `--sigma`:
the weighted mean, the gross fraction and the coverage curve per case.

## 4. How it is calibrated

This is what makes it an instrument rather than a colour. On the ladder the truth is exact per texel, so for every case
(the 42, LADDER2, D1, D1h) compute the error `e = |f - f_true|` and the predicted sigma per texel, then:

1. **Monotone.** Bin texels by predicted sigma (deciles). The median and 90th percentile of |e| per bin must rise with
   the bin: Spearman over bins >= 0.9.
2. **Scale.** Fit one global factor k so that the 68th percentile of `e / (k sigma)` is 1; k stable across families
   within 1.5x, and the 95th percentile in [1.6, 2.6] (a heavier tail means sigma is missing a cue).
3. **Gross capture.** At least 80% of gross texels (|e| > 2 px) fall in the top 20% of sigma, or carry the ambiguity
   flag. Report the coverage curve: at each threshold sigma*, the share of texels kept and the share of gross removed.
4. **Cross-family.** Calibrate on the translation and oscillation families, test on the periodic and stairs families and
   on D1; a map that only works where it was fitted is not an instrument.
5. **The counterfactual that must fail.** Replace sigma by (a) a random permutation of itself across texels and (b) a
   sigma computed from a noise image: Spearman must fall under 0.2 and the gross capture to about 20%, chance. If the
   shuffled map still "works", the test is measuring the object mask, not the map.
6. **D1 as the named blind spot.** On the recommendation's interior (fy = -12 on 100%, 0% flips [R]) sigma will read low;
   the ambiguity channel must flag it. If it does not, the blind spot is measured and written down.

Real footage: the bench's skeleton (floor 0.4 px) can test monotone and gross capture for velocity; not scale.

## 5. First steps, ranked

| # | step | cost | kill |
|---|---|---|---|
| 1 | Mode 10 as a readout of cues that exist in the High tier (margin, coherence support, Q from the fused pass; forward-backward in the quad) plus the numpy calibration (section 4, steps 1, 3, 5) on ten ladder cases, LADDER2 and D1 | a tail switch, 2 h; analyzer, 1 h; 10 GPU min | best single cue Spearman < 0.5, or gross capture < 50% |
| 2 | The sext's mode 6 residual against truth on the O-family and the zero-jerk scene: the "free confidence map" measured | 0 build; 6 GPU min | Spearman < 0.5 |
| 3 | The flip-rate channel in the cache; D1 and V3 on the recommendation and High | 1 h; 4 GPU min | it does not separate High's wandering interior from the recommendation's lock |
| 4 | Fit the scalar sigma and the flag; cross-family test | 2 h; 0 GPU (the dumps exist from 1) | held-out 68th percentile of e / sigma outside [0.6, 1.6] |
| 5 | Lily's Party: bones weighted by 1/sigma^2 on the bench footage against the skeleton | 2 h; 10 GPU min | the 24-48 px/frame gain (0.31 today [R]) does not rise by 0.1 |
| 6 | Cadence: the sigma fade as the trust gate on the cage, the railing, D1h | a switch, 2 h; 8 GPU min | D1h stays below hold (6.78 vs 7.22 [R]) |

Steps 1 and 2 are pure readout: "do these cues predict the error at all" is answerable from numbers the shaders already
compute and throw away.
