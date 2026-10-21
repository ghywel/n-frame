# Lane wildcard: the weave's comb is two mechanisms, and the sampler half dies on paper when B is fetched at the candidate's own phase

Outsider lane. Read the lay layer only, as instructed, plus the refuted paragraphs. No GPU. One CPU-only numpy toy gives
the lane's only [M] claims, and they are about the toy, not the shader.

## What I read

- `REPO/WHAT-IS-ACTUALLY-HAPPENING-HERE.md` whole (49 lines).
- `REPO/WHAT-WE-BUILT.md` whole (512 lines), in particular "What it cannot do" (140-201), "Is this new?" (203-223),
  "What to do next" (299-412).
- `REPO/WHAT-IT-CAN-MEASURE.md` whole (120 lines): the table (33-44), "The row that changes what the family is for"
  (51-68), "The field on real content" (89-99).
- `REPO/README.md` lines 1-90.
- `REPO/INSTINCT-STRATEGY.md` lines 1-130 (the brief's rule 6).
- `REPO/NFRAME-LIMITS.md`: only the refuted paragraphs, listed under "Refuted entries checked" with line ranges.
- `REPO/ENERGY-TRANSFER.md`: the `grep -n MISSED` listing only (headings), no paragraphs.
- Deliberately not read: SHADERS.md, the shader sources, the generators, tests/, PRIOR-ART.md, REPAIRS.md, the rest of
  NFRAME-LIMITS.md and ENERGY-TRANSFER.md. So I do not know what the brief's generator switches (the energy channel,
  the alias carry, the cage, the trust gate) do inside; where a proposal may collide with one, I hand it off.

Scratch: `~/Developer/np-scratch/swarm-20261021/wildcard/comb_toy.py` (the toy, 60 lines, numpy).

## Findings

1. **[R] The record's own words make the coarse level a fixed-grid decimation of both frames.** NFRAME-LIMITS.md
   4981-5022: "An aliased level is shift-invariant only for whole shifts of its own texels", immune speeds "within
   one pixel of 8 and 16, the 1/8 level's texel and its double". Section 8 (545-575): "Point sampling: full contrast,
   wrong motion at every other speed. Box: right motion, nothing left to match on." That sentence pair is only true
   if frame B's coarse row is decimated on the same fixed grid as A's and then read at a fractional offset.

2. **[J] That is two mechanisms the record treats as one.** (a) A sampler comb: the Moire of a fixed-grid point
   sample of B is a different pattern from the Moire of A unless the shift is a whole texel. This is set by the
   sampler and has nothing to do with the texture's period; the record's M1 random texture shows it too (section 8:
   28-31 dB at 6-14 px/frame against 46.9 at 16). (b) A texture-period ambiguity: a print of period P matches equally
   at d and d + kP from any one pair of frames. This is set by the scene and no local matcher on any number of frames
   at constant velocity can resolve it. The weave's "v - 28" reads (NFRAME-LIMITS 4999-5001) are (b); the "comb in
   speed, period 8" is (a). The prefilter attacked (a) by changing the content and paid with (b)'s and everything
   else's contrast. The cure for (a) is to change which samples are compared, not what is in them.

3. **[M, toy only] A 1-D numpy model reproduces the comb and the phase-exact fetch removes it.** Stride 8, a 14/28-px
   bar print and a random texture, speeds 3-19 px/frame, candidates -32..32 px, SAD over 64 coarse texels, B =
   A shifted plus 0.5% noise. Stock (B decimated on the fixed grid, candidates read by linear interpolation of the
   coarse row): print right only at 8 and 16, WRONG (neither truth nor a period alias) at the other eleven speeds;
   random texture right at 7, 8, 16, wrong at the other ten. Phase-exact (B's taps read from the full-res row at
   `8i + c`): random texture TRUE at all thirteen speeds; print TRUE or a `+-28k` alias at all thirteen, never WRONG.
   The record's "immune within one pixel of 8 and 16" also appears: stock reads 8 at v = 7 and 9, 16 at 15 and 17,
   1 px off, under the record's 2-px gross line. Fixed seed; the script reproduces it.

4. **[M, toy only] PIV's peak ratio separates the print from the random texture in the same toy.** Q = second-best
   SAD (at least 3 px from the best) over best SAD. Phase-exact: random 35-45, print 1.00-1.19. Stock: everything
   1.0-2.0 except the immune speeds (15-57). So Q is both the "is this a periodic lock" cue and, under the stock
   sampler, a "is this level corrupt at this speed" cue.

5. **[R] The record already named the right replacement lead and did not build it.** NFRAME-LIMITS 5018-5020:
   "Section 8's replacement lead was a PER-LEVEL TRUST GATE ... That is the answer this section should have named;
   nothing later in the record builds it." Proposals 1 and 2 below are two different ways to supply that gate's
   input.

6. **[R] The stated limits this lane is aimed at**, from WHAT-WE-BUILT.md 140-201 and WHAT-IT-CAN-MEASURE.md 89-118:
   periodic texture choosing the wrong copy (stripes at half spacing, the railing, the weave); a reach limit (23 px
   from any seed, NFRAME-LIMITS 3841; the real-body cliff past 24 px/frame); a non-affine cliff above about 1%
   strain per frame; lone edges reported as values rather than "no measurement"; rotation readable at patch
   resolution only; a one-frame latency; four-frame jerk limited by truncation.

7. **The sceptic's first question, from PIV. [J]** "Every headline field number is a spatial average over the object
   eroded by 40 px (WHAT-IT-CAN-MEASURE 28-31 [R]); the one time you looked point by point, the turning disc's error
   was noise less than twice the straight-moving case, which the calibrations had never shown because they averaged
   (WHAT-WE-BUILT 150-160 [R]). So what is the per-texel uncertainty of velocity, acceleration and jerk, as a
   distribution with a gross fraction, and what is the instrument's spatial resolution, given a halo twice a
   limb's width (WHAT-IT-CAN-MEASURE 95)?" PIV learned over a decade that accuracy and spatial resolution are one
   trade and must be quoted as a pair; a mean over a 300x300 object is a resolution of 300 px. [U] on the PIV
   history; it is my training, not a citation.

8. **What the project under-values, from outside. [J]** First, the per-texel error map and its gross fraction are
   the instrument's specification sheet, not a diagnostic: PIV vendors ship the uncertainty field beside the vector
   field, and this project has every ingredient and still presents a patch mean as the result. Second,
   reproducibility across six GPUs to 0.01 dB (README 37, 39 [R]) is a replication property neural interpolators and
   most PIV codes cannot offer, and the lay account gives it one clause. Third, the 42-scene analytic ladder plus
   decimate-and-reconstruct is a benchmark of the kind sub-fields were built on (synthetic PIV image generators; the
   Middlebury flow set [U]); the lay account mentions it in passing, when it is the most transferable thing in the
   repository after the patch.

## Proposals, ranked

Count before search: the coarse search's candidate set is whatever the descent already evaluates; none of these adds a
new enumeration except proposal 5 (which adds one extra link per texel) and proposal 8 (one extra match per texel).

### 1. Fetch B at the candidate's own phase (astronomy and radar: the matched filter evaluated at the hypothesised shift; drizzle's rule that you never resample twice)

- **Mechanism.** At a coarse level, keep A's row as the point-sampled pyramid it is, but do not match it against a
  pre-decimated B; for a candidate shift c (in full-res pixels) read B's tap for coarse texel i from the finer
  level at `S*i + c` (bilinear there for fractional c). Both sides are then the same Moire phase of the same texture,
  and the match is shift-invariant for every c, not only whole texels.
- **Maps to GLSL?** Yes: one `texture()` call per tap into the level-0 or level-1 image at a scaled coordinate,
  the same tap count as today; worse cache locality, since the taps are 8 px apart in a large image.
- **Nearest prior attempt and why this is not it.** The prefilter (section 8, refuted) changed the content of the
  level and lost the fine contrast. The two-descent (800-812, refuted on the comb) changed the seed. The "integer at
  a finer level rescues" test (518, refuted) changed the level but kept the fixed grid. This changes none of those; it
  changes only which texels of B are compared. The record never names it.
- **PREDICTION.** The weave's locked speeds (3, 5, 11, 13, 19 px/frame, field gross 63-98%) fall to under 2%
  gross wherever the print has an end or a modulation inside the window, and to the texture-period alias (`v - 28`
  only, never a stray) elsewhere; M1 at 6-14 px/frame rises from 28-31 dB to within 5 dB of its 16 px/frame score of
  46.9. R3/R6 (period locking, 564) unchanged, since (b) is untouched. Fine-texture ladder cases (M1, M2, A4, A5,
  F1, F3) gain; the L-family unchanged within 0.1 dB.
- **KILL TEST, written first.** Run the weave sweep (`weavesweep.py`'s scene) and M1 at 6, 8, 10, 12, 14, 16 with the
  phase-exact coarse level. Kills it: M1 at 10 or 12 stays under 34 dB, or the 16 control drops by more than 1 dB.
  Confirms: M1 at 10 and 12 within 5 dB of 16's score and the weave's gross at 11 and 13 under 10%. Inconclusive
  (the weave improves, M1 does not) tips toward the fetch being right but the descent's step schedule now
  stepping across period aliases; then test M1 alone with a finer first step.
- **COST.** A generator switch, about an hour, because the coarse pass's tap addressing changes; two scenes at six
  speeds plus the ladder, about 20 GPU minutes. Rank 1: it addresses a stated limit directly, the paper model is
  already positive, and nothing in the record has tried it.
- **Hand-off first:** if the coarse pass already reads B from a finer level at the candidate's exact offset, this
  proposal is dead and finding 2 is wrong about the record's sentence; a shader-lane reader can settle it in a
  minute by looking at where the coarse SAD fetches B.

### 2. PIV's peak ratio Q as the per-texel trust input (Keane and Adrian's detectability; the second-best peak)

- **Mechanism.** The matcher already evaluates candidates; keep the second-best SAD whose offset is at least a
  period-guard (3 px at the finest, 1 texel coarser) from the best, and output Q = second/best per texel and level. A
  periodic print in motion gives Q near 1 (two equal minima at d and d + P); a random or structured texture gives Q
  far above 1; a lone edge gives a ridge, so Q along the ridge direction is also near 1.
- **Maps to GLSL?** Yes: one extra register and a compare in the candidate loop; no new taps.
- **Nearest prior and why not it.** The agreement blend (4031, refuted) used the zero offset's match against the
  contrast; the coherence gate (4044 onward) uses neighbours' flows. Q is per texel, needs no neighbours, and is a
  property of the cost surface, not of the zero offset. It is the per-level trust the record asked for at 5018-5020.
- **PREDICTION.** On the cage C1/C2, over 90% of texels read Q under 1.3; on M1 moving, over 90% read Q above 2;
  a gate "warp if Q > 1.5, else blend" puts the cage within 1 dB of the blend's score (the record's ceiling, 4040)
  while costing M1, F1, L1 under 0.3 dB each. The toy's Q (finding 4) is the paper version of this prediction.
- **KILL TEST.** Histogram Q on the cage and on M1 at one speed each from the field dump, no new scene. Kills it:
  the two histograms overlap by more than 20% of their mass. Confirms: separation at a single threshold with under
  5% overlap. Inconclusive (overlap 5-20%) tips toward Q combined with the coherence gate as a product of two fades,
  the record's own pattern at 4101.
- **COST.** Writing the register out through a diagnostic view, half an hour; two field dumps, under 15 GPU
  minutes. Rank 2: cheapest first test in the set and it feeds the gate the record named and did not build.

### 3. PIV window deformation (Scarano's iterative image deformation) for the non-affine cliff

- **Mechanism.** At each finer level, sample B's match window at `p + d(p) + J(p)(q - p)`, J the gradient of the
  coarser level's flow at p, so the window is sheared and stretched to the current estimate and the match measures
  only the residual. PIV reads strain rates far above 1% per frame this way.
- **Maps to GLSL?** Yes: a per-tap offset from a 2x2 Jacobian read from the coarser flow texture; the tensor pass
  the project has for divergence, curl and shear ("read_view 9", WHAT-IT-CAN-MEASURE 42-44 [R]) supplies J.
- **Nearest prior and why not it.** The tensor fill (2716-2728, refuted) rewrote flows by the IMAGE's structure
  tensor; EDGE_PROP (4367) weighted propagation. Neither deformed the match window; both acted after matching.
- **PREDICTION.** The jelly at three times the cliff's strain rate ("one pixel in five stays wrong",
  WHAT-IT-CAN-MEASURE 85-87) falls under 5% wrong; divergence gain on real content rises from about 0.6 toward
  curl's 0.9 (line 97), divergence being the component a rigid window cannot see. Translation cases unchanged
  within 0.05 dB.
- **KILL TEST.** The jelly at 1x, 2x, 3x the cliff. Kills it: above 15% wrong at 3x, or any translation case down
  more than 0.2 dB. Confirms: under 5% at 3x. Inconclusive tips toward J needing the tensor pass's 5x5 window.
- **COST.** A generator switch, one to two hours; about 25 GPU minutes. Rank 3.

### 4. Seismology's envelope misfit: match a demodulated image at the coarse levels (the cure for cycle skipping that is not a low-pass)

- **Mechanism.** Cycle skipping in waveform inversion is this project's period lock; the field's cure, when a
  low-pass is unavailable, is to match the ENVELOPE (the rectified, then smoothed, signal), which carries the
  texture's amplitude modulation and its boundaries at low frequency without the carrier. Here: build the coarse
  levels of `|high-pass(image)|` smoothed over the level's footprint, so a railing's interior is near-flat but its
  ends, contrast changes and the wall behind it carry the right displacement, and no period alias exists in the
  envelope at all.
- **Maps to GLSL?** Yes: one rectify-and-box pass per level, the same shape as the refuted prefilter's pass.
- **Nearest prior and why not it.** The prefilter (section 8) was a box on the signal: it annihilates the texture
  because the texture's components sit above the level's Nyquist and have zero mean. A box on the RECTIFIED signal
  keeps the texture's local power, which has a non-zero mean; the content survives as an envelope rather than as a
  Moire. It is the step between "point sample" and "box" that section 8 did not test. **Collision check:** the brief
  names an "energy channel" switch; if that already matches local variance at the coarse levels, this is it and the
  proposal reduces to a hand-off.
- **PREDICTION.** Modest: on the weave at 3 and 5 px/frame (the slow lock, "the commonest in footage", 5013) the
  coarse field reads within 2 px of truth on texels within one footprint of the print's ends, where today it reads
  +15; interior texels stay ambiguous and come from propagation. Random texture loses at the coarse level (flat
  envelope) and needs the per-level trust gate to choose the plain level there. Ladder: a wash without the gate,
  which is why it ranks below 2.
- **KILL TEST.** The weave at 3 px/frame, field gross within 16 px of the print's ends. Kills it: above 40%.
  Confirms: under 10%. Inconclusive tips toward a wider footprint.
- **COST.** A generator switch, an hour; 10 GPU minutes. Rank 4.

### 5. Staggered match distance (radar's staggered PRF) as the fallback if proposal 1 cannot be done

- **Mechanism.** With a fixed-grid sampler the comb's immune set is a property of the DISPLACEMENT per match: at
  distance k frames it is k*v, so the immune speeds move to `(8m +- 1)/k`. The N-frame windows hold distances 1, 2
  and 3; per texel, trust the link whose displacement sits nearest a multiple of the texel.
- **Maps to GLSL?** Yes, in the 4-6 frame shaders; the links exist, the choice is a compare.
- **Nearest prior.** W1 (4983) tested the shortest vector, not the frame distance.
- **PREDICTION.** Arithmetic: at distance 3 the weave's 3, 5, 11, 13 land at 9, 15, 33, 39, all within 1 px of a
  multiple of 8, but 33 and 39 exceed the 23-px reach (3841). So it rescues 3 and 5 and nothing above about
  7 px/frame. Same target as proposal 1, different kind (dodge, not cure).
- **KILL TEST.** The weave at 3 and 5 through quad with the distance-3 link preferred. Kills it: gross above 40%.
  Confirms: under 10%.
- **COST.** A switch in the 4-frame generator, an hour; 6 GPU minutes. Rank 5, only if 1 fails.

### 6. PIV's normalised median test as the "no measurement" flag

- **Mechanism.** Flag a vector when `|d - median(8 neighbours)| / (median(|neighbour - median|) + eps) > 2`, eps
  about 0.1 px for the noise floor; the normalisation lets one threshold serve slow and fast flows. Replace with the
  median, or mark "no measurement" in the field output, which the instrument does not yet do (WHAT-WE-BUILT 169-175
  [R]).
- **Maps to GLSL?** Yes: a 3x3 gather and a nine-element median.
- **Nearest prior.** The coherence gate (4044 onward) is a neighbourhood test with an absolute or contrast-relative
  threshold [U]. This differs in the normalisation and in being a flag, not a blend decision. It does NOT catch a
  coherent lock (the weave's gross patches agree with each other); it catches the disc's per-texel mottle
  (1245-1247) and isolated edge contamination.
- **PREDICTION.** On R3 at N:N, flagged fraction 8-15%, pooled 12-px acceleration error from 20-27% to under 15%
  after replacement; on the straight-moving control, under 3% flagged.
- **KILL TEST.** R3 and its control from existing dumps. Kills it: control above 10% flagged, or R3's error unmoved.
- **COST.** A view pass, half an hour; 12 GPU minutes. Rank 6. Same kind as 7 (a flag); 7 differs in what it
  compares.

### 7. Dual-VENC's consistency flag: coarse-to-fine jump larger than half a period

- **Mechanism.** In phase-contrast MRI the unambiguous coarse reading only picks the wrap integer, and a voxel is
  flagged when the fine reading sits further from the coarse one than half the fine ambiguity interval. Here: flag a
  texel when the finest level's flow differs from its seed by more than half the local texture period (or one coarse
  texel where no period is measured): the texel where the fine level jumped a copy.
- **Maps to GLSL?** Yes: seed and result are both in hand at the finest pass; a subtract and a compare.
- **Nearest prior.** The cut and coherence gates act on neighbours or on time; this acts on the descent's own history.
- **PREDICTION.** At the weave's 3 px/frame the flag covers over 80% of the gross texels; immune speeds under 2%.
- **KILL TEST.** The weave at 3 and 8, from dumps. Kills it: coverage under 50% at 3.
- **COST.** Half an hour and 12 GPU minutes. Rank 7.

### 8. Interferometry's closure: the direct t to t+2 link as the three-frame shader's self-check

- **Mechanism.** Phases around a triangle of baselines sum to zero if the stations are consistent, whatever the
  source. Here: match t to t+2 directly (one more link; 2v must be within reach) and read `d12 + d23 - d13` per
  texel: zero on a consistent texel, about one period where one link locked to a wrong copy.
- **Maps to GLSL?** Yes: one more block-match pass over a pair already in the window.
- **Nearest prior.** The six-frame shader's overdetermined fit residual (WHAT-IT-CAN-MEASURE 72-74 [R]) is the
  five-link version; this is the cheapest, for the shader an acceleration user actually runs.
- **PREDICTION.** On the O-family at N:N, per-texel |closure| correlates with acceleration error at r > 0.7.
- **KILL TEST.** One oscillation scene. Kills it: r < 0.4. Confirms: r > 0.7.
- **COST.** A pass in the tri generator, an hour; 6 GPU minutes. Rank 8: a pass spent on a check, not a gain.

### 9. Radar tracking's alpha-beta-gamma filter over the persisted flow cache (a different kind: recursion, not a window)

- **Mechanism.** A radar tracker reads velocity and acceleration from noisy positions with a recursive filter that
  trades lag for noise; the project fits an exact polynomial through N frames (zero lag, full noise). The flow
  cache persists, so a per-texel exponentially weighted fit over past readings is one multiply-add per frame.
- **Maps to GLSL?** Yes; the cache is there.
- **Nearest prior.** The symmetric five-frame window (WHAT-WE-BUILT 343-351 [R]) is the zero-lag FIR answer; this
  is the IIR answer. Lag is a stated cost (176-180), so this is for the laboratory user, not the player.
- **PREDICTION.** The zero-jerk floor (0.05-0.1 px/frame^3, WHAT-WE-BUILT 129) halves at a gain of 0.3; the
  six-frames-per-cycle oscillation loses 20% of amplitude.
- **KILL TEST.** Those two scenes. Kills it: floor falls under 30% or amplitude loss above 40%.
- **COST.** A switch, an hour; 12 GPU minutes. Rank 9.

### Not proposed (two negative transfers that agree with the record)

- **YIN and the "shortest period" rule [U].** Pitch trackers cannot resolve a period ambiguity from one frame when
  the lag exceeds half a period. The analogue, a shortest-vector prior, is W1, refuted (4983): at 19 px/frame the
  short alias (-9) is the wrong one.
- **Chinese-remainder velocity unfolding [U].** It needs the ambiguity interval set by the sampler. The print's
  period is set by the scene, so changing the frame spacing changes the displacement, not the modulus. Proposal 5
  is what survives of it, for mechanism (a) only.

## Refuted entries checked

NFRAME-LIMITS.md: the prefilter (545-575; proposals 1 and 4 are not a box on the signal); the two-descent on the
comb and rotation (800-812); "integer at a finer level rescues" (518); peak locking and within-block shear on R3
(1240-1252); the tensor fill, both forms (2716-2728; proposal 3 deforms the window, not the flow); the temporal seed
(3838-3841); the agreement blend (4031-4040; proposal 2 does not use the zero offset); EDGE_PROP (4367-4370); size on
the limb (4232); W1 (4983-5001); build 5's carry (4863-4868); the P-table (490-520). ENERGY-TRANSFER.md: the MISSED
steps, by heading only.

## Hand-offs

- **For the shader lane (decides proposal 1 and finding 2):** does the coarse SAD read B from a stored decimated
  level, or from a finer level at the candidate's exact offset? One look at the coarse pass's fetch in
  `bidirectional-interpolation.glsl`.
- **For the generator lane:** what the "energy channel" and "alias carry" switches do. If the energy channel matches
  local variance at the coarse levels, proposal 4 is built; if the alias carry picks among `d + kP` by a prior,
  proposal 2's Q is its missing per-texel input, not a rival.
- **For the ladder lane:** the weave sweep and the cage are the scenes every proposal here tests on; a speed-sweep
  case (one scene, speeds 3-19) would make the comb a ladder number [U whether one exists].
- **For the owner:** whether the per-texel uncertainty map becomes a shipped output (finding 8). A product decision.

## Felt

- Felt: surprise, the staggered-PRF transfer, medium; the modulus is the scene's period, not the sampler's. -> Split
  the comb into two mechanisms and re-aimed at the sampler half. Outcome: right (the toy separates them).
- Felt: pull, "fetch B at the candidate's phase", high; the drizzle rule, and nobody in the record says it. -> Spent
  the lane's one block on the numpy toy instead of a tenth transfer. Outcome: MIXED (item 10 ran): the named prediction
  (M1c_v12 >= 38) was wrong, the mechanism was right in kind (capped mean +0.31, L7 +19.7, weave at 3 px/f +19 dB) and
  wrong in place (the comb at 12 px lives at the 1/8 level) and blind to a cost (period-24 aliases brought into reach).
- Felt: unease, whether the shader already does this and the record's sentence is loose, medium; the lane forbids
  reading the shader. -> Made it the first hand-off. Outcome: right to ask; the coordinator confirmed the stored read.

## Verdicts

**Reasoned.** The lay layer and the refuted paragraphs say the comb is a property of a fixed-grid point-sampled
pyramid; a 1-D model with that property reproduces the record's immune speeds and loses the comb when B is read at
the candidate's phase, leaving only the texture-period alias, which is irreducible locally and is where the trust gate
belongs. Proposals 1 and 2 are the cheapest tests of the lead the record itself named at 5018-5020 and did not build.
Everything else here is a flag or a self-check, worth less and cheap. No [M] claim tonight touches the shader.

**Gut.** Proposal 1 feels like a hole the whole record has been walking around; if the shader turns out to already do
it, that feeling was wrong and the comb needs a different explanation than the record's own sentence gives it.

## Gate pre-registration: PHASE_FETCH=1, the phase-exact fetch (2026-10-21, late; item 10)

**Built [R: the files named].** `REPO/tests/phase_fetch.py` (new) and a switch in `REPO/tests/gen_variational.py`
(definition after LOCAL_CENTRE's, call after LOCAL_CENTRE's and after COARSE_ENERGY's, recorded in the banner's command
line as `PHASE_FETCH=1`). Nothing committed; nothing else in REPO touched by this lane. The coordinator confirmed from the
base shader that the coarse SAD reads B from the stored 1/16 level, so the mechanism is untried in the record.

**What it does.** In the fused coarse pass (1/16, A->B and B->A in one dispatch) each SAD's TARGET taps are read from the
full-resolution frame (`NEXT` for A->B, `HOOKED` for B->A) at the reference tap's position plus the candidate's exact
offset, by the downsample passes' own luma formula; the REFERENCE taps stay on the stored 1/16 level, as do the contrast
gates, REG_LAMBDA, TIE_MARGIN, the three descents and the ring. With COARSE_ENERGY the energy term keeps its stored .g
sample (a 12-px Gaussian field) and only the luma moves. **Level read: the frame, not LUMA_*_E** [J]: the 1/8 lumas are
made after the coarse pass in this base (propagated base, line 707 against 347; only GLOBAL_SEED moves them ahead), and
they are a fixed 8-px grid, which would move the comb to period 8 instead of removing it. **Taps per candidate:
unchanged, 9 reference + 9 target (COARSE_WINDOW_RADIUS 1)**; per direction per coarse texel about 131 candidate
evaluations (3 descents of 1 + 5 x 8, plus the ring of 8), so 2 x 131 x 9 / 256 = about 9 full-resolution RGB fetches
per output pixel, 16 px apart, where before they hit a 1/256-size single-channel texture. Bandwidth, not arithmetic.
Predicted frame-time cost +3 to +10% [U]; the bench's ms column decides. Binds in the fused pass: 6 -> 8 (the High tier's
largest pass has 12 today).

**Census [M, CPU].** Both on-files against their committed twins: 10 lines added, 3 changed, 5 hunks, no pass added or
removed (59 and 65 passes). Hunks: the banner line; `//!BIND HOOKED` and `//!BIND NEXT` in the fused pass header; a
5-line helper block (`lum_pf_a`, `lum_pf_b`) before `sad5x5_s`; the one target tap in `sad5x5_s`; the one in
`sad5x5_s2`. Off: `cmp` whole-file identical to the committed recommendation and -energy file. On: `prune_passes.py
--check` 0 faults, 0 orphans on both; `compile_check.py` (glslangValidator, every pass) 59/59 and 65/65. The High tier's
full switch set (GLOBAL_SEED ... PRINT_LATTICE CUT_MOTION) with PHASE_FETCH=1 generates without an assertion (not
checked further; not tonight's gate). Files: `~/Developer/np-scratch/swarm-20261021/wildcard/
bidirectional-interpolation-variational-propagated-phase.glsl`, `...-propagated-energy-phase.glsl`, their `.diff`s,
and the `-off` twins.

**Commands (the owner runs; one GPU job at a time).**
```
cd REPO/tests
W=~/Developer/np-scratch/swarm-20261021/wildcard
for S in $W/bidirectional-interpolation-variational-propagated-phase.glsl \
         $W/bidirectional-interpolation-variational-propagated-energy-phase.glsl; do
  for c in M1c_noise_v6 M1c_noise_v10 M1c_noise_v12 M2c_period40_v6 M2c_period40_v10 \
           M1_noise_large L1_trans_8px L2 L7; do ./bench.sh $c $S phase; done     # L2, L7: scenes.sh's full names
  ./bench.sh all $S phase                                                          # the kill: the 42
done
./analyze.py
REC_SHADER=$W/bidirectional-interpolation-variational-propagated-phase.glsl \
  python3 probes/weave/weavesweep.py $W/weave 3,5,7,8,9,11,13,16,19 noise,weave
```
weavesweep's FIELD column reads the quad shader, which does not carry the switch; only its "default" picture column
(REC_SHADER against linear) tests it tonight. A field read through the switch needs the quad generator and is not asked.

**Predictions (recommendation, 24 -> 60, PSNR-Y, capped 40; the -energy file the same direction, smaller deltas).**

| case | today [R, coordinator] | predicted | note |
|---|---|---|---|
| M1c_noise_v12 | 28.6 (blend 26.5, High 31.8) | >= 38 | the comb's bite; on a random texture the toy says the sampler is the whole mechanism |
| M1c_noise_v10 | 45.1 | 44.5-46 | already escaped by the descents; must not regress |
| M1c_noise_v6 | 43.7 | 43-46 | |
| M1_noise_large (16 px/f, the immune control) | [U: not read] | unchanged within 0.5 | at whole texels the fetch equals the stored sample |
| M2c_period40_v6 / v10 | [U] | -0.5 to +2 | period 40 is 2.5 coarse texels: sampler and period ambiguity both present; low confidence |
| L1_trans_8px, L2, L7 | [U] | within 0.2 | flat and edge content; L7 is the record's "wart" and the most likely to twitch |
| the 42, capped mean | [U] | +0.1 to +0.5; M1, M2, A4, A5, F1, F3 up, the rest within 0.2 | |
| weave default - linear at 11, 13 | +2.1, +2.1 | > +10 | the sampler lock (reads v - 28 today) |
| weave at 3, 5 | -6.5, -5.1 (below the blend) | still negative, up by 0-3 dB | the toy says these go to a PERIOD alias, not truth: mechanism (b), not this switch's |
| weave at 7, 8, 9, 16 | +22 to +24 | unchanged within 1 | immune already |

**Kill test (written before any run).** Kills it: M1c_noise at 10 or 12 under 34 dB; or M1_noise_large (16 px/f) down
1.0 dB; or any of the 42 down more than 1.0; or the capped mean down more than 0.15. Confirms: M1c_noise_v12 >= 38 with
the 42 inside those limits. Inconclusive (v12 between 34 and 38): the sampler comb was part of the mechanism, not all
of it, and the next suspect is the 1/8 level, whose `sad5x5_e` still reads the stored `LUMA_B_E` on its own fixed 8-px
grid (the same mechanism one level down; a PHASE_FETCH at E would read the frame there too). A frame-time rise over 15%
on the M5 does not kill the mechanism but sends it to a variant, not the recommendation.

**Cost.** 9 cases x 2 shaders at about 8.5 s each (a 42-case ladder is about 6 minutes per shader): about 3 GPU minutes;
the two 42-case ladders, 12; the weave sweep, 9 speeds x 2 textures, about 6-8 [U]. About 25 GPU minutes in all.

**Refuted entries re-checked for this build:** the prefilter (section 8: this changes no level's content), the
two-descent (800-812: no seed changes), "integer at a finer level rescues" (518: no level change). None is this.

**Felt:** unease, the 1/8 level's `sad5x5_e` keeps the fixed grid, medium; if the coarse fix lands and v12 stops at
35-37, that is where the rest is. -> Written into the inconclusive branch above rather than built tonight. Outcome: open.

## Item 10's result, read on paper (2026-10-21, night)

**Prediction killed, mechanism alive [R: the coordinator's numbers].** M1c_v12 28.61 -> 28.71; capped mean +0.31 with
five cases down over 1.0, so a variant, not the recommendation. The weave (`gpu/phase-weave.log`, my column is "default"):
3 px/f -6.5 -> +13.0 over linear, 5: -5.1 -> +1.5, 11/13/19 still locked at v - 28, 7/8/9/16 held.

**(1) L7 against M1c_v12 [J].** L7 moves 16 px = one 1/16 texel, immune to the sampler comb by section 8's own
argument, so its +19.7 is not the comb removed: the stored-grid match there compared two beats of a 837-px Moire
(period 15.7 sampled at 16), nearly flat over the 3x3 window, and the 0.3-px drift won as a REG_LAMBDA near-tie; the
frame-fetched target restores the texture's full contrast at every candidate, so 16 px beats 0.3 px by the 9 taps'
gradient x 0.3 px (about 0.35) against REG_LAMBDA's 0.06. M1c_v12 is the inconclusive branch: 12 px is 1.5 texels of
the 1/8 level, whose `sad5x5_e` still reads the stored `LUMA_B_E`; v6 and v10 (0.75 and 1.25 texels there) were already
escaped by the descents. The 1/8 form: the same transform on `sad5x5_e`/`sad5x5_e2` and the post-propagation check
(coarse_energy.py's anchors exist), about 2 x 25 x 9 / 64 = 7 full-res fetches per output pixel more, an hour to write,
gate on M1c_v12 + the 42, 8 GPU minutes.

**(2) The period-24 losses: section 8 in reverse, and the mechanism is REACH [J].** Period 24 at 16-px pitch aliases
to a 48-px Moire; its false basin sat beyond the 23-px reach, so the stored grid left one basin in reach, distorted but
unique. The frame fetch restores the true 24-px ambiguity, whose alias at v - 24 is inside reach for v = 4-12 (P1, V1,
H1, V3, V3x), and at v = 12 the two tie exactly. The weave confirms the rule: locked at 11/13/19 (alias v - 28 at
17/15/9 px, in reach), freed at 3 (alias at 25 px, out of reach), half-freed at 5 (23 px, the edge); M2 period 40 and L7
gain because their aliases are out of reach. The anomaly: weave 7-9 (aliases 19-21 px, in reach) hold; REG_LAMBDA's
margin or the descents' 12-px first step; unresolved.

**(3) Classes and the gate.** Gains: random texture (M1c_v10, noise column), periodic content whose period exceeds
v + 23 px (L7, M2, P5, weave 3), flat (L6). Loses: periodic content with |v - P| <= 23 px (period 24 at v <= 12; the weave
at 11-19). The cue is the two-basin tie the fused pass already produces: where the ring descent's basin is >= 0.75 texel
from the zero descent's and `cost_b` within 10% of `cost_a` under the frame fetch, a period alias is in reach; take the
stored-grid result there (both forms in one pass, 18 target fetches per output pixel; or the stored form only in the tied
branch). moire_s would serve the same role if it reads the 1/16 period [U: not read]. **Kill test for the gated form:**
kills it if any of P1, V3, V1, H1, L1 is still more than 1.0 below the recommendation, or L7/P5/M2/L6 keep less than half
their gain, or the capped mean is under 38.26. Confirms: all nine inside those bounds and M1c_v12 unchanged (it is the
1/8's). Cost: a switch, 1-2 hours; one 42-case ladder plus the comb cases, 8 GPU minutes.
