# Lane ladder-audit: the recommendation's capped mean is decided by 8 of the 42 cases, and three of those eight sit against a ceiling the scene itself imposes

No GPU was used. Every number marked [M] here comes from numpy on the scene expressions or on the saved psnr logs of
the 2026-10-21 build gate (`np-scratch/build-gate-20261021/old/`), plus two CPU-only ffmpeg lavfi renders. The numpy
model reproduces the ladder's own `hold` on V2 and V3 to the hundredth (18.19, 15.64), which is the check that the
model of the scene and of `analyze.py`'s scoring is right.

## What I read

- `REPO/tests/scenes.sh` whole (lines 1-640). `REPO/tests/analyze.py` whole. `REPO/tests/scenecheck.sh` 1-80.
  `REPO/tests/bench.sh` 30-78 (the render loop, the `hold`/`linear` chains).
- `REPO/tests/TESTING.md` 129-335 (honesty, the ladder, texture/acceleration/rotation/aperture/period-24 series,
  the reset table), 1341-1470 (known limitation, the 2026-08-31 reset), 1911-1930, 1995-2095, 2367-2445.
- `REPO/NFRAME-LIMITS.md` 355-445 (section 3's comb and section 4), 545-600 and 640-660 (section 8), 1335-1370 (the
  diagonal Moire and the zero seed's passes), 2313-2372 (the owner's eyes: V1/V2/V3), 2680-2740 (the aperture series),
  3167-3330 (the synthetic pool, the tensor's third component, verb-object pairs), 3785-3850 (the fast pan),
  3972-4030 (the cage), 4523-4700 (V3 reopened, band by band, the ambiguity flag, the carry, B1), 4975-5030 (the weave).
- `REPO/PLAN.md` 39-122. `REPO/REPAIRS.md` 97-132, 201-260. `REPO/tests/probes/cases/cluster.py` whole.
  `REPO/tests/probes/PROBES.md` rows for jerk, shear, verbs, weird, masters, cage, pan, limb, weave, trust.
  `REPO/INSTINCT-STRATEGY.md` 1-130. `REPO/shaders/bidirectional-interpolation.glsl` 232, 311-345, 1576-1600.
- Deliberately not read: ENERGY-TRANSFER.md beyond its MISSED list; SHADERS.md; PRIOR-ART.md beyond headings; the
  master tier (TESTING.md 392-685); any real-footage section. The animation audit.

## Findings

Numbers for "the rec" are `bidirectional-interpolation-variational-propagated` from the gate's old build; "high" is
the player's `-lattice-cut` tier; "quad" the four-frame field shader.

**1. [M] The recommendation's capped mean (38.05) is moved by exactly 8 cases: A3 39.93, L4 30.58, L7 23.57, M3
21.77, R3 38.14, V2 29.02, H2 28.64, V3 26.46.** The other 34 sit above the 40 dB cap and contribute a constant.
Of those eight: L7 and M3 are one mechanism (finding 4); V2 and H2 are one mechanism (finding 5), and the record
itself settled that direction is irrelevant (NFRAME-LIMITS 2352-2355); L4 and A3 are both the coarse reach (finding 6);
V3 is bimodal with start phase (NFRAME-LIMITS 4536-4543 [R]); R3 confounds rotation with the texture's diagonal alias
(finding 7). So the number the owner reads for a shader change is a function of about five mechanisms, three of them
pinned by the construction. The high tier has 6 binding cases, the quad 7.

**2. [M] V2, V3 and H2 have a ceiling of 30.66 dB built into their ground truth.** `TEX_V2`/`TEX_H2` are
`gt(sin(ld(1)/3.8197),0)`, a hard threshold evaluated at integer pixel coordinates. At the 24 fps source frames the
box sits at integer positions (`100+6n`), so the stairs are exact. At the 60 fps truth frames it sits at `100+2.4m`,
and the bar edges snap to whole rows: an ffmpeg CPU render of V2's second 60 fps frame (y0 = 102.4) shows the bar
column inside the box at two levels only, no intermediate value [M]. This is the quantisation the 2026-08-31 reset
removed from M1 ("a texture quantised to a grid CANNOT be translated to a fractional position", scenes.sh 179-187
[R]); `gt()` is such a quantiser, and `scenecheck.sh` cannot see it because the coincident frames are integer. The
family's warp is bilinear (the texel snap was retired, shader 1576-1600 [R]), so the best any warp can produce at a
fractional offset is a partial row; against the snapped truth that scores 30.66 dB averaged over the 44 scored frames
(min 25.5, max 37.4 by frame phase) [M]. An oracle nearest warp with the exact flow scores 30.33; with the flow
quantised to 2 px, 29.74 [M]. The rec reads V2 29.02 and H2 28.64: within 1.6-2.0 dB of a wall. The high tier's
29.45/29.60, the cage's phase-averaged V3 27.4 and the carry's V3 28.6 (NFRAME-LIMITS 4650-4748 [R]) all sit under
the same wall. [J] Every "V2 -1.3, visible" or "V3 +6" in the record from 2026-09-06 onward should be re-read against
a 30.7 dB ceiling: the cases cannot show a gain beyond it and compress any gain approaching it. The P-series is clean:
its bars are horizontal and its motion along x, so the bar edges never move (checked in the expressions [J]).

**3. [M] Whole-frame PSNR carries an object-size bonus of 19.6 dB for a 100 x 100 box, 10.1 for 300 x 300, 7.1 for
600 x 300, 11.1 for the blob** (10 log10 of frame area over object area, when the error is confined to the object; the
swept band makes it slightly less). The cap at 40 dB whole-frame is therefore 20 dB on a small box and 30 dB on a
large one: the capped mean does not treat the cases equally, it treats them by size. Dividing out the bonus from the
saved logs (approximate, since the real error occupies the object plus its swept band): the rec's binding set grows
from 8 to 29 cases, and the ranking changes: whole-frame high 38.33 > rec 38.05 > quad 37.80; on-object high 32.54 >
quad 32.21 > rec 31.52 [M]. The quad's 3-6 dB lead on O1-O3 (52.2/49.1/47.4 against 49.4/43.7/41.3) is invisible
whole-frame because all six numbers are above 40, and visible on-object because all six are below 33. This is
NFRAME-LIMITS "The cage" (3972-3980 [R]: "a small region's fault vanishes in a frame mean") applied to the ladder
itself. The honest instrument is a region score (crop before psnr), which `cage.sh` and `limb.sh` already do.

**4. [J] L7_textured_large and M3_period16_trap measure one mechanism.** L7's period is 15.7 px, M3's 16.0, the motion
16 px per frame; the difference is a 0.3 px drift per frame that no stage can resolve (there is no sub-pixel stage,
PLAN.md 111-121 [R]; the finest step is 2 px). Both read 21.8-25.3 for every shader in the gate table; the record
says of L7 "measures a failure, not sigma_f ... the period-locking failure" (NFRAME-LIMITS 646-649 [R]). Two votes for
one mechanism, both below the cap, so the capped mean counts the period lock twice.

**5. [R][J] All four textured translations run at 16 px per frame, the one speed where an aliased level is
shift-invariant** (NFRAME-LIMITS 361-369 [R]: "the one speed at which the block matcher can match on aliased
content"). M1's 47 dB is "the matcher at its best" (649 [R]); the same box at 6-14 px/frame scored 28-31 on the base
(section 8 table [R]) and the weave at 3-5 px/frame falls below the blend on the current default (4983-5000 [R]).
Recommendation 2 of section 5, "add the comb to the ladder (TEX_M1 and TEX_M2 boxes at 10 and 12 px/frame)", is
marked "not done as of 2026-10-01" (438-442 [R]). So the ladder's most-cited textured result sits on the immune
speed, and the regime the record calls "the commonest in footage" has no case in `ALL_CASES`.

**6. [M] The accelerating twins spend much of their scored window past the reach.** With 44 scored frames at
t = 0.10-0.98 s, instantaneous speed exceeds 23 px/frame on 24 of 44 frames (55%) for A3, and on 13 of 44 (30%) for
A2, F2, R2 and R3 (at the rim) [M]. scenes.sh 302-304 says so for A3 [R]; the TESTING.md table (181-187) does not.
A3 is a reach case wearing an acceleration name, and together with L4 gives the reach two of the eight binding votes.

**7. [R][J] R3_rot_tex confounds rotation with the texture's diagonal alias.** TEX_M2 axis-aligned is below the 1/16
Nyquist along x, but "rotate it into the 17-73 deg band and it should alias too -- consistent with ... R3's interior
failing from frame 10 onward (theta > 25 deg); that is one datum, not a test" (NFRAME-LIMITS 375-379 [R]). R3 is
binding for the rec (38.14) and is the case the energy channel and the zero seed's pass 6 moved most (+2.4) [R 1364,
4648]. Whether those gains are rotation or alias handling is undecided by this case.

**8. [M] L9_occlusion occludes for 3 of its 24 source frames.** Box A spans [300+300t, 400+300t], B [900-300t,
1000-300t]; they touch at t = 5/6. The CPU render confirms A fully visible to source frame 20 and 75/50/25 px visible
at frames 21-23 [M]. In the scored window that is 8 of 44 frames (18%); the rest is two flat boxes translating at
12.5 px/frame with a gap. The name claims a mechanism the case shows for a sixth of its length.

**9. [M] P4's crosser is in front of the stairs from source frame 13 (t > 0.52) and never fully.** Render: crosser at
x 900-1059 at frame 0, stairs end at 700+192t; overlap begins at frame 13 and the crosser is still 24 px outside the
stairs at frame 23 [M]. Half the clip is P2 with a second box on black.

**10. [J] L5_lowcontrast and M4_belowgate cannot bind whatever the shader does.** L5's object is 12 gray levels (10.3 in
Y) above its background; the largest possible error is that contrast, so the on-object PSNR is at least 27.9 dB and
the whole-frame at least 47.5. M4's bound is about 59.5. Both are sentinels (the gate open / closed), not difficulty
cases, and they read identically for every shader (61.8-62.3; 60.56-60.59) [M from the table].

**11. [R][J] Every textured case in `ALL_CASES` moves along an axis** (x: L7, M1-M3, H1, H2, P1-P5, A4-A7, O5, O6, R3's
centre fixed; y: V1-V3). L8_diagonal is a flat box, so it cannot show the diagonal Moire the record measured on
TEX_M2 at (8,8) px/frame: "61% locked, 21 px" (1336-1340 [R]). The zero seed's passes were scored on that scratch
scene's field, never on a ladder picture.

**12. [R] V1 and H1 are non-binding since ZERO_SEED (55.7/55.6)** and the question they were built to settle,
period or direction, is settled: "The direction is irrelevant" (2352 [R]). They remain the ladder's one regression
sentinel for the zero seed (19 -> 55 dB), which is worth one case, not two.

**13. [J] Duration is adequate everywhere.** Every case is 1 s: 24 source frames, 60 outputs, 44 scored (n = 6..60
minus 11 passthroughs), t = 0.10-0.98 s [M]. No case is starved. O1 at 1 Hz covers one period less its first tenth.

**14. [J] Texture against texel, summarised.** Period 24 (V/H/P bars) is aliased at 1/16 (Nyquist 32) and resolved at
1/8 (16). TEX_P's speckle (13.8 x 11.3) is aliased at 1/16 and 1/8, resolved at 1/4. TEX_PC's 40 x 30 is aliased in y
at 1/16 (30 < 32), but the motion is along x. TEX_M1's five components have periods 35.9, 17.9, 9.3, 4.9, 4.6 px:
four of five alias at 1/16, three at 1/8, two at 1/4 (section 8's "four of five" [R]). TEX_M2 is 40 px on each axis
(two diagonal waves of 28.3 px). Speeds in coarse texels: 4 px = 0.25, 6 = 0.375, 8 = 0.5 (= 1 texel at 1/8, the
immune speed of the weave's comb, 5005-5009 [R]), 12 = 0.75, 16 = 1, 23 = 1.44, 40 = 2.5. P2, P4 and P5 at 8 px/frame
therefore sit on the 1/8 level's immune speed; P3 at 12 does not, and reads 5 dB lower on the rec.

## The 42, one by one

Columns: speed vs reach (23 px/frame; S = 16 px coarse texel); texture vs texel; axis; verdict. "bind" = below the
40 dB cap for the rec. Whole-frame rec dB from the gate table; the on-object figure subtracts finding 3's bonus.

| case | claimed | actually isolates | speed / reach | texture / texel | axis | confound or redundancy | rec dB (obj) | verdict |
|---|---|---|---|---|---|---|---|---|
| L0_static | passthrough | round-trip ceiling | 0 | flat | - | sentinel; cannot bind | 81.1 | keep (sentinel) |
| L1_trans_8px | 8 px/f | flat-box translation, 0.5 S | in | flat | x | +19.6 size bonus | 65.7 (46.0) | keep |
| L2_trans_16px | 16 px/f | same, 1 S | in | flat | x | size bonus | 50.1 (30.5) | keep |
| L3_trans_23px | at reach | same, 1.44 S | at | flat | x | size bonus | 41.4 (21.8) | keep |
| L4_trans_40px | past reach | reach failure, 2.5 S | beyond | flat | x | the reach also binds via A3 | 30.6 bind | keep; label as reach |
| L5_lowcontrast | weak but gated in | gate open; error bounded by contrast | in | flat | x | cannot bind (>= 47.5) | 61.8 | keep (sentinel); wrong as difficulty |
| L6_flat_large | size control | 300-px flat box | in | flat | x | pairs with L2 | 48.8 (38.6) | keep |
| L7_textured_large | textured translation | period lock, p = 15.7 at v = 16 | in | aliased at 1/16, 1/8 | x | same mechanism as M3 | 23.6 bind | merge with M3 |
| M1_noise_large | aperiodic texture | the matcher at the immune speed | in | 4 of 5 comps alias at 1/16 | x | only at 16 px/f; comb unmeasured | 47.0 (36.9) | keep; add comb twins |
| M2_period40 | unambiguous period | alias rejection at the immune speed | in | sub-Nyquist on axes | x | - | 52.0 (41.9) | keep |
| M3_period16_trap | period == motion | period lock | in | aliased at 1/16, 1/8 | x | same as L7; every shader 21.8 | 21.8 bind | keep one of L7/M3 |
| M4_belowgate | gate closed | gate closed; blend only | in | flat | x | cannot bind (>= 59.5) | 60.6 | keep (sentinel) |
| L8_diagonal | axis asymmetry | flat box at (16, 9) px/f | in (18.4) | flat | diag | no texture: blind to the diagonal Moire | 46.7 (27.1) | retune (textured twin) |
| L9_occlusion | crossing, occlusion | two translations at 12.5; occlusion in 3 of 24 frames | in | flat | x | 18% of scored frames occlude | 44.4 (27.7) | wrong-name; retune |
| A1_accel_8mean | acceleration | 0 -> 16 px/f, flat | in | flat | x | size bonus | 51.4 (31.8) | keep |
| A2_accel_16mean | acceleration | 0 -> 32; 30% of frames past reach | 30% beyond | flat | x | reach confound | 45.2 (25.6) | keep; label |
| A3_accel_23mean | acceleration | 0 -> 46; 55% past reach | 55% beyond | flat | x | a reach case; duplicates L4 | 39.9 bind | wrong-name |
| A4_accel_tex_a033 | field at a = 0.33 | sub-pixel floor (PLAN 111) | in (+-4) | M2 on axis | x | field case; 4 votes for one law | 54.5 | keep as FIELD |
| A5_accel_tex_a067 | a = 0.67 | textured constant accel, reversal | in (+-8) | M2 | x | as A4 | 53.8 | keep as FIELD |
| A6_accel_tex_a133 | a = 1.33 | as A5 | in (+-16) | M2 | x | as A4 | 50.2 (40.1) | keep as FIELD |
| A7_accel_tex_a167 | a = 1.67 | as A5 | in (+-20) | M2 | x | as A4 | 49.3 (39.2) | keep as FIELD |
| F1_fourier_edge | irregular boundary | 1/f boundary, flat interior, 16 px/f | in | flat | x | pairs with L6 | 49.8 (38.7) | keep |
| F2_fourier_accel | boundary + accel | 0 -> 32; 30% past reach | 30% beyond | flat | x | reach confound | 44.3 (33.2) | keep; label |
| R1_rot_const | rotation | boundary-only flow, rim 16 px/f | in | flat | - | flat: no interior field | 41.5 (30.4) | keep |
| R2_rot_accel | rotation + accel | rim 0 -> 32; 30% past reach at rim | partial | flat | - | reach at the rim | 41.6 (30.5) | keep; label |
| R3_rot_tex | rotation, textured | rotation AND TEX_M2's diagonal alias past 25 deg | partial | M2 aliases off-axis | all | NFRAME-LIMITS 375-379 | 38.1 bind | retune (isotropic texture) |
| O1_osc_gentle | placement, a = 2.7 | flat 100-px box; mid-frame 0.34 px | in | flat | x | size bonus hides quad's lead | 49.4 (29.8) | keep |
| O2_osc_medium | a = 8.6 | as O1, 1.07 px | in | flat | x | as O1 | 43.7 (24.1) | keep |
| O3_osc_hard | a = 13.2, model edge | as O1, 1.64 px | in | flat | x | as O1 | 41.3 (21.7) | keep |
| O4_osc_flat300 | size control for O5 | O2 on a 300-px flat box | in | flat | x | - | 44.9 (34.8) | keep |
| O5_osc_textured | field calibration | textured O2; low \|a\| = max jerk | in | M2 | x | PLAN.md 39-86 | 42.4 (32.3) | keep (needs O6) |
| O6_osc_tex_gentle | jerk control | textured O1 | in | M2 | x | control for O5 | 49.5 (39.4) | keep |
| V1_bars_sine24_v6 | period below Nyquist, y | zero-seed sentinel | in (0.375 S) | 24: alias 1/16, clean 1/8 | y | duplicate of H1 | 55.7 (45.6) | keep one of V1/H1 |
| V2_stairs_sq24_v6 | hard bars, y | as V1 with a snapped truth; ceiling 30.7 | in | as V1 | y | ceiling; duplicate of H2 | 29.0 bind | retune (exact coverage) |
| V3_stairs_sq24_v12 | half-period alias | alias; start-phase bimodal; ceiling 30.7 | in (0.75 S) | as V1 | y | phase-fragile [R]; ceiling | 26.5 bind | retune + phase-average |
| H1_bars_sine24_h6 | V1 turned 90 deg | same as V1 | in | as V1 | x | question answered [R 2352] | 55.6 (45.5) | merge with V1 |
| H2_stairs_sq24_h6 | V2 turned 90 deg | same as V2; ceiling 30.7 | in | as V1 | x | ceiling; duplicate of V2 | 28.6 bind | retune / merge |
| P1_stairs_along_v4 | aperture, slow | aperture + fine speckle at 1 Q texel | in (0.25 S) | speckle aliases 1/16, 1/8 | x | picture blind to the aperture [R] | 45.3 (38.2) | keep; field-scored |
| P2_stairs_along_v8 | aperture alone | aperture at the 1/8 immune speed | in (1 E texel) | PC: 40 x 30 | x | immune speed | 58.4 (51.3) | keep; label |
| P3_stairs_along_v12 | aperture, fast | aperture at a non-immune speed | in (0.75 S) | PC | x | - | 53.6 (46.5) | keep |
| P4_stairs_along_v8_crosser | crosser in front | crosser arrives at t = 0.52, never fully | in | PC + crosser 4.1 x 3.7 | x | half the clip is P2 | 51.6 (45.9) | retune (start touching) |
| P5_stairs_along_v8_alias | fine speckle alias | v - p alias at the 1/8 immune speed | in | P: 13.8 x 11.3 | x | - | 41.9 (34.8) | keep |

Count: 42 cases; verdicts keep 27 (five of them with a label change), merge 4 (L7/M3, V1/H1, with H2 folding into
V2's retune), retune 6 (L8, L9, R3, V2, V3, P4), wrong-name 2 (A3, L9). Nothing is retired: the frozen set stays frozen
and every change is a case built beside it (TESTING.md 1391-1400's rule that numbers before a reset do not compare
with numbers after [R]).

## Proposals, ranked

Costs use the brief's 6 minutes per 42-case run per shader, so about 9 s per case per mode. Each proposal is a
scene line or an analyzer column; none is a shader change, so none can repeat a refuted shader mechanism.

**P1. Exact-coverage stairs beside V2, V3, H2 (V2x, V3x, H2x).** Mechanism: replace `gt(sin(ld(1)/3.8197),0)` with the
coverage of a 24-px square wave over the pixel, `clip(12-mod(ld(1)\,24)\,0\,1)+clip(mod(ld(1)\,24)-23\,0\,1)`,
so the truth at a fractional offset carries partial rows the way `_rect`'s box edges already do. At integer offsets it
equals the frozen stairs on every row but the box's top row (u = 0, where sin(0) = 0 is "off"; 300 px of the frame),
so the source frames are the frozen ones to within that row [M]. Nearest prior: the 2026-08-31 reset did this for M1
and the box edges; nobody applied it to the bars added on 2026-09-06. Prediction: the baselines move to hold
19.50/16.26 and blend about 24.2/20.8 (numpy gives 23.36/19.94 and the ladder's libplacebo blend runs 0.8-0.9 above
my blend on the frozen cases) [M]; the oracle ceiling goes to the round-trip's 81 dB; and if the rec's error on V2 is
the ceiling's error plus its own alias error, subtracting in MSE puts V2x near 34 dB, H2x near 35, V3x near 28.5.
Kill test: V2x within 0.5 dB of V2 kills the ceiling as the binding term (the two errors overlap on the same rows);
V2x above 33 confirms it. Inconclusive (1-3 dB) tips toward "partly a ceiling", and the phase-averaged form settles
V3x. Cost: 3 scene lines, scenecheck, 3 cases x 4 modes, about 2 GPU minutes. Rank 1: it changes how three of the
eight binding numbers are read, and costs nothing to run.

**P2. The speed comb on the ladder: TEX_M1 and TEX_M2 boxes at 6, 10 and 12 px/frame (six cases, or three with M1).**
Mechanism: the only textured translation speed in `ALL_CASES` is the immune one; the comb measures the point-sampled
pyramid where footage lives. Nearest prior: section 5 recommendation 2, never done (NFRAME-LIMITS 438-442 [R]); the
weave's sweep did it on a 2-D print outside the ladder (4983-5020 [R]). Prediction: on the base, 28-31 dB as section 8
measured [R]; on the rec, within 3 dB of the blend at 10 and 12 for TEX_M1 (every gate since "leaves the comb open",
5020 [R]) and 46-47 at 16 (the existing M1); TEX_M2 at 6 and 10 above 45 (sub-Nyquist on axis). Kill test: M1 at 10
and 12 above 40 on the rec kills the claim that the comb is open on the current default; below 34 confirms it. Cost:
three to six scene lines, 2-4 GPU minutes. Rank 2: a known mechanism with no regression case; same kind as P1 (a scene
line), so the next proposal differs in kind.

**P3. A region-normalised summary column in `analyze.py`, no re-render.** Mechanism: report beside each whole-frame
dB the on-object dB (minus 10 log10 frame/object, a per-case constant from the scene geometry) and a second capped
mean over it; then, as the honest form, a `crop` before `psnr` in `bench.sh` for a region-scored log. Nearest prior:
`cage.sh` and `limb.sh` score rectangles [R PROBES rows]; `analyze.py` never did. Prediction: the on-object capped
mean re-ranks the field shaders above the rec (high 32.5, quad 32.2, rec 31.5, the arithmetic form) and 29 cases
bind for the rec instead of 8 [M, arithmetic on the logs]; the crop-scored form will read 1-3 dB lower than the
arithmetic form on fast small boxes (the swept band). Kill test: the crop-scored capped mean ranks the rec above the
quad; confirmed if the quad leads by more than 0.3. Inconclusive (within 0.3) tips toward keeping both columns. Cost:
an hour in python; the crop-scored form is one bench.sh switch and a full run, 6 minutes per shader. Rank 3: it is the
cage lesson, the instrument the record says is the schedule (3195-3203 [R]).

**P4. A textured diagonal beside L8: L8t, TEX_M2 box at (8, 8) px/frame.** Mechanism: the record's diagonal lock
(61% of texels, 21 px, 1336-1340 [R]) has never been scored as a picture or on the ladder. Nearest prior: the scratch
scene behind the zero seed's six passes (the field only). Prediction: the rec, which ships pass 6, reads above 45 dB
if the zero seed holds the diagonal; below the blend (about 30) if the shipped pass lost it; the base reads near
hold. Kill test: L8t below linear on the rec kills "pass 6 fixed the diagonal in the picture". Cost: one line, one
GPU minute. Rank 4.

**P5. L9b: boxes crossing mid-clip.** Mechanism: B at `700-300*T` touches A at t = 0.5, fully overlaps at 0.67 and
separates by 1.0, so about half the scored frames occlude instead of 18%. Prediction: the rec falls 3-6 dB below L9's
44.35 because the occlusion share rises; the base falls further. Kill test: L9b within 1 dB of L9 means the
occlusion handling is fine and L9's name was fair after all. Cost: one line, one minute. Rank 5.

**P6. R3i: R2's rotation with an isotropic sub-Nyquist texture** (three sines of period 40 at 0, 60 and 120 degrees,
summed, each with axis frequencies under 1/32 cycles per pixel at every angle). Mechanism: remove the one datum's
confound. Prediction: R3i reads 3 dB or more above R3 on the rec and the interior field no longer fails past 25
degrees; if R3i reads within 1 dB of R3, rotation itself is the cost and 375-379's alias explanation is refuted,
which re-reads the energy channel's "+2.4 on R3". Cost: one line, one minute. Rank 6 (its payoff is in reading, not
in a gain).

**P7. The missing mechanisms as a second group, `LADDER2_CASES`, scored by the same `bench.sh` and summarised
separately.** Count first: five mechanisms the record names and the ladder lacks, and their existing scenes: fast pan
across structure (W2, W3; `d=2`, 48 source frames, `analyze.py`'s rules hold at 24->60), small movers (K1-K3: a
48 x 200 limb is 1% of the frame, +19.8 dB bonus, so these need P3's crop or `limb.sh`), periodic print under drift
(C1, C2: whole-frame is dominated by the cage's fifth, the record scores both), diagonals (P4 above; C3 exists for the
bars), deformation (the shear and weird scenes have closed-form inverse maps, so a 60 fps render is ground truth; no
picture score exists yet). Rule: `ALL_CASES` stays as it is; `analyze.py` prints the 42's capped mean and the
group's capped mean as two numbers and never one. Prediction for the first run: W3's mean over its ramp lands near
24 dB for the rec against 17 for linear (from the band table, 3812-3822 [R]); C1 below the hold (31.6 against 36.6
[R]); K1 whole-frame above 40 and meaningless until cropped. Cost: an hour of scripting, 8 cases, 2 minutes per
shader. Rank 7 by certainty per cost, because it is the only proposal here that enumerates more than one kind.

Loops of a kind: P1, P2, P4, P5, P6 are all "a scene line beside the frozen set"; P3 and P7 are instruments. The
owner should take at most two of the scene lines before P3, since finding 3 says the instrument decides what any new
line can show.

## Refuted entries checked

NFRAME-LIMITS: the prefilter (432-442, 545-600: built and refuted, "the aliased detail is load-bearing"); the comb
prediction (804, >= +6 dB refuted); R4/R5 (805); A7 mid-speed (808); the tensor fill (2716-2728, twice); the temporal
seed as the pan's term (3838-3841); the agreement blend (4031-4043); EDGE_PROP on the ladder (4368); the limb's size
hypothesis (4232); W1 shortest-vector (4983). ENERGY-TRANSFER: T2 (690) and T6 (719). None of my proposals is a
shader mechanism; P2 is the un-done recommendation that the refuted prefilter was meant to answer, and it is a
measurement, not the filter. The 2026-09-10 ruling that the family is not rebuilt is untouched.

## Hand-offs

- For the owner: whether the frozen V2/V3/H2 numbers keep their place in the capped mean once V2x/V3x/H2x exist, or
  are reported but excluded. The 2026-08-31 rule says a reset starts new numbers; this is a reset of three cases.
- For the shader lanes: every V2/H2 delta in the record since 2026-09-06 is compressed against a 30.7 dB ceiling;
  "-1.3, visible" on V2 (4547 [R]) may be reading the ceiling's phase pattern, not the change.
- For whichever lane reads the field: NFRAME-LIMITS 1340-1346 explains the diagonal lock by TEX_M2's 28.3 px diagonal
  waves being "above the 1/16 level's 32 px Nyquist"; on a square 16-px lattice each axis component of those waves is
  1/40 cycles per pixel, under the 1/32 axis Nyquist, so the sentence's reason does not follow even though its
  measurement stands [J]. I did not dig further.
- For the master tier (TESTING.md 392-685, not read): whether its full-frame scenes already cover P2 and P7's gaps.
- For the owner: `linear` in my numpy model runs 0.8-0.9 dB below the ladder's libplacebo blend on V2/V3 while
  `hold` matches to the hundredth. Likely a weighting or linear-light detail of `frame_mixer=linear` [U]; harmless to
  the ladder, worth one line in TESTING.md.

## Felt

- Felt: surprise, L9's boxes meeting at t = 1, medium; "they never cross inside the clip". -> Computed the touch at
  t = 5/6, rendered 24 frames: occlusion in 3 of 24. Outcome: right.
- Felt: unease, `gt()` inside a translating texture, high; "the reset said a quantised texture cannot translate, and
  this is a quantiser". -> Built the numpy model, matched the ladder's hold to 0.01, rendered one 60 fps frame: two
  levels only; ceiling 30.66. Outcome: right.
- Felt: unease, "28.3 px above the 32 px Nyquist" at 1340, low; "per axis it is under". -> Did not dig; handed off.
  Outcome: open.
- Felt: pull, the size-bonus arithmetic, medium; "the cap is a different height per object". -> One pass over the saved
  logs: 8 binding becomes 29, the quad overtakes the rec. Outcome: open (needs the crop-scored run).
- Felt: push, the master tier and ENERGY-TRANSFER as further ground, medium; "another 400 KB will not change the
  eight". -> Stopped reading; listed as hand-offs.

## Verdicts

Reasoned: the 42 are well built as scenes (coverage-exact edges, bit-identical at coincident frames) and the owner's
instinct that some are poor candidates is right in a specific place rather than in general. The number he reads, the
recommendation's capped mean, is decided by eight cases; two are one mechanism counted twice, two are the reach, one
is phase-fragile, one is confounded, and three of the eight sit within two decibels of a ceiling that the hard-bar
construction imposes on any bilinear warp. The regime the record says footage lives in, slow and mid-speed textured
motion off the immune speed, has no case in the default set, and the whole-frame cap weights the cases by object size,
not by difficulty. The cheapest corrections are three scene lines (P1) and one analyzer column (P3); the measured
predictions for both are written above and cost under ten GPU minutes together.

Gut: the ceiling on V2/V3/H2 feels solid and overdue; the on-object re-ranking feels suspicious until a cropped run
confirms it, because the arithmetic form ignores where the error actually lands. If they disagree, the crop-scored
run settles it.
