# Imports to interpolation: what the effect shaders can give back

*Opened 2026-10-25, after BEYOND-INTERPOLATION.md, at the owner's word: "by exploring extra use cases like this we might
actually be able to bring science back in to our interpolation shaders ... a sequence of frames will always be temporal,
which is why i often title this project as 'N-Frame Temporal Shader Analysis' - so there is cross-pollination between
discrete techniques ... concentrate on this import back to interpolation."*

The first import happened by accident: the spectrum effect lit the toaster grille that GPT's prospecting had found as
High's strongest quiet-shot failure, and showed its light going back and forth, the change the matcher reads as motion
(BEYOND-INTERPOLATION.md). This record takes the other effects the same way: each idea becomes a measurable question
about the interpolators' own losses, answered cheaply on footage before anything is built.

## The diagnostics, pre-registered (written before any is computed)

Data: GPT's five 300 s prospecting windows (film, television, anime, western cartoon, CG; tests/probes/prospect/), each
with the original at 640 px wide, High's reconstruction of every withheld frame (the High of 2026-10-23, before
GLOBAL_GAIN) and the GPU blend. Only GPT's eligible withheld frames (not a cut, a hold, low signal or a boundary). Cells
are GPT's 16 x 16 grid. Features are computed from the **retained** frames only (n-5, n-3, n-1, n+1, n+3, n+5: what a
six-frame interpolator sees), never from the withheld frame itself. Tool: `tests/probes/imports/diagnose.py`.

**A target cell** is one where High is clearly worse than the blend: High's mean squared error over twice the blend's,
and High's RMS over 3 code values (visible).

**D1, a flicker cue (from spectrum.glsl).** Three cell features: *coherent change*, |mean dI| / mean |dI| over the five
retained pairs (1 when a patch brightens or darkens as a whole, near 0 when texture moves across it); *oscillation*, the
share of each pixel's temporal variance left after removing its straight-line trend, the cell's mean; and the control
*raw change*, the cell's mean |I(n+1) - I(n-1)|. A feature's **lift** is the target rate among the top 1% of cells by
that feature, over the window's base rate. A feature is a candidate gate cue if its lift is 5 or more on at least three
of the five windows AND beats raw change's lift there. Predicted: coherent change passes (photometric change is
spatially coherent; motion is not), oscillation fails (moving texture oscillates too).

**D2, mixed cadence in animation (from the strobe and ghost-town work).** Per adjacent pair of original frames, per cell:
*held* if its RMS change is under 1.0 code, *moving* over 3.0; a pair is *mixed* when at least 10% of the textured cells
(cell standard deviation over 4 codes) are moving and at least 10% are held, outside cuts. Reported per window as the
share of moving pairs that are mixed. Predicted: 20% or more in anime and cartoon, under 5% in film and CG (the control).
If so, per-region cadence (interpolating each region at its own drawing rate) has a target the player's whole-frame
cadence stage cannot reach.

**D3, a temporal-median fallback (from ghost-town.glsl).** In target cells, is the per-pixel median of the six retained
frames closer to the truth than High? Reported as the share of target cells where it is, against the same share over
all eligible cells. Predicted: 30% or more of target cells, under 5% of all cells; then a cue that picks those cells
(D1's, or an occlusion test) would let a plate replace a failed warp.

Each is a diagnostic, not a shader: a pass only says the import has a target worth building for.

## First results (2026-10-25, 16:20) and two follow-ups registered before they ran

| window | base rate | lift: coherent change | oscillation | raw change | D3: median beats High, target cells / all cells | D2: "mixed" pairs |
|---|---|---|---|---|---|---|
| film | 0.53% | 1.1 | 2.0 | 3.0 | 55% / 14% | 34% |
| television | 0.50% | **17.2** | 6.5 | 7.1 | 65% / 45% | 78% |
| anime | 2.16% | **9.1** | 7.9 | 6.8 | 70% / 19% | 40% |
| western cartoon | 1.59% | **8.0** | 1.9 | 4.7 | 76% / 48% | 57% |
| CG | 0.76% | 4.9 | 3.8 | 9.1 | 55% / 50% | 87% |

(Eligibility here excludes cuts, holds, low signal and boundaries, as registered; GPT's separate "extreme change" bucket
was not excluded, so the counts run a few percent above GPT's eligible totals.)

**D1 PASSES, narrowly: coherent change is a candidate gate cue** on three of five windows (television 17.2, anime 9.1,
cartoon 8.0, each above raw change), as predicted; oscillation fails (moving texture oscillates too), as predicted. Film
(1.1) and CG (4.9, under raw change) are not helped: their failures are of another kind. On GPT's TV 73 frame, the three
worst cells read coherent change 0.72, 0.95 and 0.99. **D2 is INVALID as designed**: its controls read 34% (film) and 87%
(CG), because a still textured background beside a moving actor looks exactly like a held drawing; the measure cannot
see drawings. **D3 FAILS its registered line**: the six-frame median beats High in 55-76% of the target cells, but also in
14-50% of all cells (a six-frame median is less noisy than a two-frame warp on anything still), so a plate is only an
import together with a cue that picks its cells (D1's is the candidate).

**D1b, the cue with one pair** (for the two-frame tiers Cadence ships): coherent change from n-1 and n+1 alone. It
passes on the same terms (lift 5 or more and above raw change on at least three windows). Predicted: weaker but passing.
**D2b, held drawings by their alternation**: per textured cell, three consecutive adjacent pairs; a cell is *on twos*
when the pattern is moving-held-moving or held-moving-held (moving over 3 codes, held under 1), *on ones* when moving in
all three. Reported per window: the share of moving cell-instances on twos, and the share of moving pairs where
on-twos and on-ones cells coexist (mixed cadence). Predicted: on-twos 20% or more in anime and cartoon and under 3% in
film and CG (the control that D2 lacked); mixed cadence 10% or more of moving pairs in anime and cartoon.

## D1b and D2b results, and what they mean for building (2026-10-25, 16:40)

| window | lift, coherent change, six frames | **one pair (n-1, n+1)** | raw change | D2b: moving cells on twos | D2b: moving stretches mixing twos and ones |
|---|---|---|---|---|---|
| film | 1.1 | **8.6** | 3.0 | 0.1% | 0.4% |
| television | 17.2 | **12.4** | 7.1 | 0.2% | 0.6% |
| anime | 9.1 | **15.1** | 6.8 | 8.5% | 2.0% |
| western cartoon | 8.0 | **11.9** | 4.7 | **16.7%** | **18.2%** |
| CG | 4.9 | **11.8** | 9.1 | 0.1% | 0.3% |

("Coexist" in D2b: at least 2% of a stretch's textured cells on twos and 2% on ones, fixed in the tool before its first
run; the registration had left it open.)

**D1b PASSES on all five windows, and my prediction was wrong in direction:** the cue from the single pair a two-frame
tier sees is STRONGER than the six-frame one on four of five (a coherent change between the two frames a warp joins is
the direct sign). So Cadence's two-frame tiers have the cue for free. **D2b is now valid** (controls 0.1-0.2%) and passes
for the western cartoon (17% of moving cells on twos, 18% of moving stretches mixing twos and ones) but not for this
anime window (8.5%, 2.0%: its holds are mostly whole-frame, which the player's cadence stage already removes). Per-region
cadence has a real target in western cartoon; this one anime window does not show it.

**Sizing, exploratory (computed after D1b on the same data): a blend swap on the cue alone would HURT.** Replacing
High's warp with the blend in the top 0.5% / 1% / 2% / 5% of cells by the one-pair cue changes each window's total
squared error by: film +8.3 / +9.3 / +14.7 / +33.5%; television +3.4 / +5.6 / +9.9 / +19.9%; anime +2.0 / +1.8 / +1.6 /
+3.8%; cartoon -0.2 / -0.1 / 0.0 / +1.5%; CG +1.1 / +1.9 / +5.0 / +9.6% (raw change, the control, is far worse:
+6 to +140%). The cue's precision is about 6% (lift times base rate); the blend loses more in the cells where High was
right than it gains where High was wrong. So the cue is information, not a decision.

**What to build, in order** (each pre-registered when built, tested by the full gate):
1. **The coherent-change cue inside the matcher, not instead of it**: where a cell's change between the two frames is
   coherent, compare them with the cell's own brightness offset taken out (a local, cue-gated form of GLOBAL_GAIN, which
   cannot be fooled by moving bars where the change is not coherent), or let the cue be one vote in the coherence gate.
   Target: the television, anime and cartoon failures, with film and CG left as they are.
2. **Per-region cadence for drawn animation**: find cells on twos from their alternation (D2b's test, which a four- or
   six-frame window can see; the two-frame tiers would need a small history in storage) and interpolate those regions
   between their drawings rather than between frames. Target: western cartoon first.
3. **The median plate** waits for a cue that picks its cells (D3).

## Import 1, LOCAL_LIGHT: the coherent-change cue inside the matcher (pre-registered 2026-10-25, before it is built)

The owner's word: "build import 1 (the coherent-change cue inside the matcher, pre-registered, tested by the full gate),
then per-region cadence after it." Built on the shipped High (GLOBAL_GAIN=2), as a switch `LOCAL_LIGHT=1` in
`tests/global_gain.py` (it needs GLOBAL_GAIN): a 64 x 36 grid pass takes each cell's mean change B - A and mean absolute
change (B with the global gain already out, 6 x 6 taps a cell); a second pass forms D1b's cue over 3 x 3 cells,
|mean dI| / mean |dI| (about 90 px at 1080p), and where it is coherent keeps the cells' mean change as a local offset,
weighted smoothstep(0.6, 0.9, cue) and ignored under 1.5 code values; every read of frame B's luma for matching then
subtracts that offset, sampled bilinearly at the same place. Where change is not coherent (moving texture, moving bars)
the offset is zero. The thresholds come from the cue's meaning (1 for a pure brightness change, near 0 for moving
texture), not from any outcome. The warp and the cut statistics keep the true frames.

Tests (High + LOCAL_LIGHT against the shipped High, the M5):
- **T1, the isolated defect, a LOCAL light change:** the toaster still with a soft highlight (a Gaussian of 120 px
  radius on the grille) whose brightness swings +-10% over a six-frame cycle, nothing moving; truth flow zero. Predicted:
  invented flow over 1 px halved or better, and the withheld frames +2 dB or more. KILL if neither.
- **T2, the real frames:** GPT's TV 73 (frame 39): the worst cell's RMS cut by 30% or more (the line F2 missed at 29.4%);
  cartoon 6525 (frame 37) not worse than the shipped High by more than 0.2 dB. KILL on TV 73's line.
- **T3, motion survives:** the textured pan with no fade within 0.1 dB of High, its flow unchanged within 0.1 px; the
  ramp and GPT's moving sheet and 256-px ramp within 0.5 dB in picture. KILL if the pan moves.
- **T4, the full gate:** the 45-case ladder (none down 1 dB, capped means within 0.05), the content test's 40 windows
  (no class mean down more than 0.05), the cage C1-C4 (none down 0.5), the build gate's five film segments (within 0.05).
- **T5, the prospecting windows** (in-sample: the cue was found there): High + LOCAL_LIGHT over all five 300 s windows at
  640 px, the same withheld frames. Predicted: target cells (High twice the blend's error and visibly wrong) down 20% or
  more on television and cartoon, the total error not up by more than 1% on any window.
- **T6, cost** on Metal and libplacebo, reported.

### LOCAL_LIGHT=1: T1 and T2 pass, KILLED by T3 (2026-10-25, 17:20); LOCAL_LIGHT=2 registered before it is built

| test | shipped High | High + LOCAL_LIGHT | (Low / Low + LOCAL_LIGHT) |
|---|---|---|---|
| T1 still toaster, a highlight swinging +-10%: PSNR, invented flow over 1 px | 48.61, 4.7% | **50.96, 0.6%** | 46.81 / 50.81 |
| T2 TV 73 frame 39: PSNR, worst cell RMS | 35.52, 36.26 | **38.96, 15.50 (-57%)** | 33.67 / 37.32 |
| T2 cartoon 6525 frame 37 | 44.45 | 44.45 | 42.10 / 42.10 |
| T3 textured pan, no fade: PSNR, median flow (truth +6) | 51.34, +4.95 | **49.62, +4.30** | 48.88 / 47.53 |
| T3 ramp / 256-px ramp / GPT's moving sheet | 65.98 / 65.81 / 61.94 | 65.98 / 65.81 / 65.79 | |

**T1 and T2 pass** (the toaster's worst cell cut 57% against the 30% line F2 missed at 29.4%). **T3 KILLS it**: the plain
pan loses 1.72 dB. The instrument check before the tests had shown why: the cue fired on 11% of the pan's frame (up to
19 codes), because a bright edge moving over a dark flat ground is a one-signed change across its neighbourhood, as
coherent as a light change. Motion and light again (GPT's identifiability, now local).

**LOCAL_LIGHT=2, the cue on the residual after motion** (registered now, before it is built). The same two passes, moved
to after the 1/8 level's final flow (`FLOW_E_AB`, after the three-way data check): the grid takes each cell's mean and
mean absolute value of B(x + v) - A(x), B sampled where the 1/8 flow says A's pixel went; the offset is formed as before
and applied only to the reads from the 1/4 level down (the quarter and half pyramids, the variational and lattice reads),
never the coarse levels it was measured from. A correctly matched moving edge leaves a residual near zero (incoherent);
a light change leaves itself (coherent). Tests: T1-T6 exactly as registered for LOCAL_LIGHT=1, the same kill lines.
Predicted: T3 passes (the pan's residual is small); T1 and T2 weaken (where the 1/8 flow is already wrong on the grille,
the residual is partly the alias) but pass.
