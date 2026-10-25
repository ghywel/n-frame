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

### LOCAL_LIGHT=2: T3 passes, KILLED by T1 and T2 (2026-10-25, 17:50). Import 1 stands as two measured kills and a design

| test | shipped High | LOCAL_LIGHT=1 | **LOCAL_LIGHT=2** |
|---|---|---|---|
| T1 swinging highlight: PSNR, invented flow over 1 px | 48.61, 4.7% | 50.96, 0.6% | **49.30, 4.4%** (lines: +2 dB or flow halved) |
| T2 TV 73: worst cell RMS | 36.26 | 15.50 (-57%) | **35.04 (-3%)** (line: -30%) |
| T3 textured pan: PSNR | 51.34 | 49.62 | **51.34** |

Instrument check before the tests: the residual cue no longer fires on the pan (0.3% of the frame, under 5 codes) and
still fires on the grille (mean -6.3 codes), but on the moving staircase H2x it fires MORE than mode 1 (8.6% of the
frame): where the 1/8 flow is an alias, the residual after it is coherent too.

**What the two kills say, together:** the toaster's false motion is decided at the coarsest level. Taking the light out
there fixes it (mode 1: the worst cell -57%) but cannot tell a light change from a bright edge moving over a flat ground;
measuring after the 1/8 flow is safe for moving edges (mode 2) but too late, the wrong coarse motion having already
absorbed the change. **The open design** (not built, a third variant on this line; set down by the loop-check rule
rather than tried a third time today): decide light against motion AT the coarse level, per cell: the best motion
candidate's cost against the zero-motion cost with the cell's offset taken out, and take the offset only where the
offset explains the cell at least as well as any motion does. A moving edge is explained by its motion; a highlight's
swing is not explained by any shift. That is the local form of the anchor GPT asked for in G025.

## Import 2, LOCAL_CADENCE: per-region cadence in the four-frame shader (pre-registered 2026-10-25, before it is built)

The quad's existing cadence branch (`CADENCE=1`, tests/gen_quaddirectional.py, 2026-09-19) re-times the output across a
held drawing, but only when the WHOLE coarse frame is a held copy (the largest coarse difference under 0.02), so a
character on twos over a background panning on ones (D2b: 18% of the western cartoon's moving stretches) never fires
it. `LOCAL_CADENCE=1` (with CADENCE=1) keeps the branch's two re-timing cases and decides them PER PIXEL: a pair of slots
is held at a pixel when the mean |difference| over a 5 x 5 grid of taps 6 px apart around it is under 0.012; the cut
test stays global. A region on ones (the panning background) fails the held test and takes the plain path; a held
character is re-timed across its drawing. The two-frame tiers Cadence ships cannot do this (the next drawing is outside
a two-frame window); this is a four-frame import.

Tests (a new synthetic scene made exactly in numpy, `tests/probes/imports/cadence_scenes.py`, 1280 x 720, 24 -> 60
against the exact 60 fps truth: a textured background panning +3 px a source frame on ones, and a textured disc of
radius 80 moving +8 px a frame drawn ON TWOS (+16 every second frame, held between); the truth puts the disc at its
smooth 8 px a frame, the convention of the existing branch):
- **C1, the mixed scene:** the disc's region (the truth's disc dilated 24 px) and the frame, synthesized frames only.
  Predicted: the quad + LOCAL_CADENCE cuts the disc region's error by half or more against the plain quad and the
  quad + CADENCE (which should not fire, the frame never being held whole). KILL if under a third.
- **C2, the control on ones** (the same scene, the disc on ones): within 0.1 dB of the plain quad on the frame and the
  disc (the held test must not fire on ones). KILL if not.
- **C3, the whole frame on twos** (background and disc both on twos): not worse than the quad + CADENCE by more than
  0.3 dB (the per-pixel test must do what the global one does where everything is held).
- **C4, the ladder on the quad:** the 45 cases not down 1 dB against the quad + CADENCE (content on ones never holds).

### LOCAL_CADENCE: C1-C3 pass (2026-10-25, 18:20)

24 -> 60 against the exact 60 fps truth (`cadence_scenes.py`), synthesized outputs only, PSNR (frame / the disc region):

| scene | blend | High (two frames) | quad | quad + CADENCE | **quad + LOCAL_CADENCE** |
|---|---|---|---|---|---|
| mixed: disc on twos, background on ones | 32.61 / 18.99 | 32.77 / 18.26 | 33.85 / 19.62 | 33.85 / 19.62 | **37.01 / 23.11** |
| ones (control) | 33.72 / 20.41 | 51.80 / 39.41 | 45.00 / 39.10 | 45.00 / 39.10 | **45.00 / 39.10** |
| twos (whole frame) | 26.69 / 18.80 | 27.03 / 18.08 | 27.25 / 19.48 | 44.22 / 31.58 | **44.22 / 31.58** |

**C1 passes:** the disc region's error falls 55% (+3.49 dB; the line was half) where the global branch never fires.
**C2 passes:** identical to the quad on ones. **C3 passes:** identical to the global branch where the whole frame is held.
Every shader we had, the two-frame High included, sat at the blend on the mixed scene's disc: the judder of a drawing on
twos was untouched by everything but this.

**Where the rest of the error is** (by distance from the disc's centre, the plain quad against LOCAL_CADENCE): inside
40 px 19.5 -> **45.6 dB**, 40-64 px 19.5 -> 34.0, the rim 64-84 px 15-19 -> 16-22 (barely moved), the background beyond
96 px 47 either way. The interior's judder is gone; a band about 40 px wide around the edge keeps it, where the held
test's footprint (5 x 5 taps 6 px apart) straddles the held disc and the moving background and the pixel takes the plain
path. The next refinement, a held test that respects the edge, is a new variant to be registered on its own.

### LOCAL_CADENCE=1: KILLED by C4 (2026-10-25, 18:45); LOCAL_CADENCE=2 registered before it is built

**C4 kills it**: against the quad + CADENCE on the 45-case ladder, L2 -13.78, L6 -12.03, L3 -10.71, M2 -8.30 dB, capped
means -0.43 (frozen and headline); 12 of 45 cases untouched. The mechanism: an object moving on ones over a STILL
background. A background pixel ahead of it is held, held, then the object arrives: locally exactly the pattern case A
re-times ("a held drawing, then the new drawing"); behind it, case B's. The whole-frame test never saw this (something
else in the frame always moved); my registered control, the disc on ones over a PANNING background, could not either.

**LOCAL_CADENCE=2 (registered now, before it is built): require the twos' ALTERNATION.** Drawings A A B B C C give
held, moving, held, moving pairs; an arriving or departing object gives held-held-moving or moving-moving-held. Case A
fires only on moving-held-moving across the window's three pairs (0-1 moving, 1-2 held, 2-3 moving), case B only on
held-moving-held. Local threes (held-held-moving, indistinguishable from an arrival) are given up; the whole-frame
global branch, where it fires, is unchanged. Tests: C1-C4 as registered, the same lines, plus **C2b, the control that
was missing**: the textured disc moving on ones over a STILL background (`cadence_scenes.py`, scene `still`): within 0.1
dB of the plain quad. Predicted: C2b and C4 pass; C1 keeps most of its gain (the disc's interior alternates).

### LOCAL_CADENCE=2: C1-C3 hold, KILLED by C4 (2026-10-25, 19:20). Import 2 stands as two measured kills and a design

| | quad + CADENCE | LOCAL_CADENCE=1 | **LOCAL_CADENCE=2** |
|---|---|---|---|
| C1 mixed scene: disc region (frame) | 19.62 (33.85) | 23.11 (37.01) | **22.49 (36.47)**: error -48% (predicted half; kill line a third) |
| C2 ones, C2b still background, C3 whole-frame twos | 39.10 / 36.72 / 31.58 | identical | **identical** |
| C4 ladder: capped means (frozen / headline) | 37.77 / 38.19 | -0.43 / -0.43 | **-0.04 / -0.04** |
| C4 ladder: cases down over 1 dB | | 33 moved, L2 -13.8 ... | **5: P1 -3.71, L5 -2.57, L4 -1.76, P2 -1.73, A3 -1.07** |

C2b, the control registered for mode 2, did not reproduce mode 1's failure (mode 1 is identical there too): the disc moves
8 px a frame, so the band ahead of it falls inside the held test's 30 px footprint; the ladder's failures were at 16-23
px a frame and over a flat ground. The control was too gentle; the ladder was the judge, as registered. Mode 2 removes
mode 1's arrivals (means -0.43 -> -0.04) but **alternation still occurs on ones**: a periodic print moving at the right
speed alternates locally (P1, P2), and low-contrast motion falls under an absolute held threshold (L5). It also GAINS on
O3 +3.61, A1 +2.24, O1 +1.99 (oscillation and acceleration), not yet understood.

**The open design** (set down by the loop-check rule after two kills, not tried a third time today): twos alternate
CONSISTENTLY, drawing after drawing, for seconds; a print's local alternation or a slow edge's is a coincidence of a few
frames. So confirm a region's alternation over a history kept in storage (the long-memory mechanism the effects work
built: a per-cell record of held and moving pairs across the last dozen source frames), and measure "held" against the
region's own contrast rather than an absolute 0.012. Both imports' open designs are this record's next steps.

**Where the imports stand tonight:** import 1 (the coherent-change cue) fixes the toaster when it acts at the coarse level
(the worst cell -57%) but cannot yet tell light from a moving edge there; import 2 (per-region cadence) removes a drawing
on twos' judder from a character's interior (19.5 -> 45.6 dB in the synthetic scene) but cannot yet tell twos from a
print's coincidences. Each failure is measured and located, and each next design follows from its failure. No shipped
shader or default changed.

## GPT's review (G027-G028, `tests/probes/imports/GPT-REVIEW.md`), reproduced, and what follows (2026-10-25, evening)

Every attack reproduces on the M5 from `review_attacks.py`: a periodic strip moving exactly its period a frame alternates
held-moving in 45 of 45 windows (held difference exactly zero), so **no history length proves cadence**; on a translating
ramp, true motion and zero-plus-offset cost exactly the same (both zero, a raw change of 7.97 codes), so **"offset at
least as good" erases motion on a tie** and a coarse competition needs a third outcome, undecided, which keeps motion;
**LOCAL_LIGHT=2 stored its residual in A's coordinates and read it at B's** (11.04 codes RMS with an ideal dense field
at +8 px, zero when transported); **cadence_scenes.py did not fail closed** (an injected failed, disabled, 30-frame
render printed 40 dB); and **the spectrum glows on textured motion too** (uniform +4 px motion of a period-16 stripe:
centroid 5.99 Hz), so the toaster's green says the grille varies in time, and only the shot's stillness (GPT's own
global fit: best displacement zero) makes that variation light.

**Corrections to this record** (GPT's, accepted): D2b's cartoon on-twos share (16.7%) missed its registered 20% line, so
D2b is a PARTIAL pass (its mixed-cadence 18.2% passed its 10% line); and D1b's precision is 4.6 / 6.2 / 32.5 / 18.9 /
8.9% across the five windows, not "about 6%" (the measured harmful swaps stand). Both were measured against the High of
2026-10-23, before GLOBAL_GAIN=2; the remaining target under today's High is measured below before it is attributed.

**Fixed now:** `cadence_scenes.py` refuses a non-zero exit, a disabled or uncompiled shader, more than eight skipped
hooks, a frame count other than the truth's, and source instants more than a code from their source frames (a broken
shader is now refused); `diagnose.py` refuses unequal stream lengths. The cadence scenes are re-scored under it.

**LOCAL_LIGHT=3 (registered now, before it is built): mode 2 with the residual read where it was measured.** A matcher
read of B at uv takes the offset at uv - v(uv), v the 1/8 flow there (the field holds B(x + v) - A(x) at A's x). T1-T3
as registered for modes 1 and 2, the same lines. **The question it answers:** if mode 3 passes T1 and T2 where mode 2
failed, mode 2's kill was the coordinate defect; if it fails them too, "too late" stands, now isolated.
