# The barn: a corrugated wall under a camera pan (2026-11-18)

The owner's clip: a film's tracking shot, 10 s, two people walking in front of a corrugated metal wall while the camera
pans with them. He calls it the interpolation shaders' worst nightmare, and asks what the motion fields are doing and
whether a fix can end "the antialiasing issue" once and for all. Source cut once to a lossless local file (frames
0-335 = film 61:30-61:44); its path is not recorded here. Everything runs on the M5, the research build rebuilt today
at the pins (ffmpeg 3a5eb94, libplacebo 285d1cc; smoke 19 of 19), MoltenVK's deterministic switches set.

## The scene, from the source's pixels alone (scene.py, period.py; no shader)

- The pan runs from about pair 75 to the cut at 306: the wall moves **+20 to +36 px a frame** (strongest
  horizontal phase-correlation peak over the wall band; the posters and the seam make it unambiguous, its second peak
  is a twentieth of the first).
- The corrugation's period is **27-33 px** at 1080p (counted on frame 192: about 30.5 px; the wall is seen at an angle,
  so it changes across the frame and a whole-band spectrum wanders).
- So the wall moves **0.7 to 1.1 periods a frame**. A shift by one period, d - P (about -6 px at pair 192; near 0
  where d ~ P, pairs 230-250), matches the bars as well as the truth inside any window narrower than the nearest
  non-periodic feature (posters, the seam and its rivets, dents, the wall's end).

## The instrument (fielddump.py, calibrate.py)

Diagnostic copies of the shader replace the final pass's body with one read; 16-bit RGB read inside the graph.
Calibrated (calibrate.py, all PASS): a written constant (+7, +2) reads (+6.998, +1.998); the same through
libplacebo's default 4:2:0 output reads (+3.5, +4.5) (the control, which must miss, and did: the reason for
`--out-format`); a still reads zero within one code; M1's noise square at 16.016 px a frame reads 15.75 inside
(High's own 0.27 px bias toward zero) and exactly zero on the background; every level (1/16, 1/8, 1/4) reads it at
15.6-15.75. **A first calibration on a film frame failed** and is kept in calibrate.py's header: flat regions read
anything (ties go to zero), so a real frame cannot calibrate a speed.

## What High does on the wall (high-fields, high-levels; shipped High)

- **The final field splits the wall into patches**: the truth (+24), the alias (about -6 to -22) and values between.
  Wall band at pair 192: 70% between -22 and -2 px, 10% at the truth. Pooled over 139 pairs with a clear truth
  (wallscore.py): **44% of the wall within 4 px of the true pan, 25.5% reading zero or backwards**; pairs 195-232:
  2-12% at the truth.
- **Viewed**: High's inserted frame at pair 192 bends, forks and tears the bars across the middle third of the wall
  (the two source frames are clean; linear's blend is clean at lower contrast).
- **The decision is made at the 1/16 level and every finer level keeps it** (high-levels): at pairs 192 and 210 the
  1/16 field reads -24 to -8 on 56% of the band, and the final field matches it bin for bin; at 130 the 1/16 field
  reads +16 to +24 and the final field is right.
- Two reasons the 1/16 level cannot be right here: its **reach** ends near 24 px (it never reads above +24 on this
  clip, against a pan of up to +36), and it **point-samples** a 30 px corrugation every 16 px, which it sees as a
  coarse Moire of period about 34 px that moves BACKWARD at about -27 px a frame when the wall moves +24
  (aliased frequency 1/16 - 1/30). The coherent wrong vote comes from the missing antialiasing.
- The frame's own shift (GLOBAL_SHIFT) reads 0 on most pairs: the walkers are still in frame and the wall, at about a
  period a frame, also matches at zero.
- **The repairs already in High cannot reach it**: the alias carry's two hypotheses come from a +-3 texel (+-24 px)
  search around ZERO at the 1/8 level, so a pan above 24 px is not among them; the carry only switches a cell whose
  flow already lies in one of its basins; and the print lattice re-scores on 16 x 16 blocks, half a period, where the
  truth and the alias tie and a tie keeps the flow.

## Why antialiasing alone is not the fix (inferred, to be tested)

Low-passing the coarse levels removes the backward-moving Moire, the coherent wrong vote. It cannot make the bars
pick +24 over -6: inside the bars both match, and the shader's small-motion prior then prefers -6 (nearer zero).
The record already holds a box prefilter that lost 18 dB on a fast fine texture ("the aliased detail is
load-bearing", NFRAME-LIMITS.md). The tie has to go to the wall's own non-periodic features, with the truth among
the candidates.

## Registered 2026-11-18 about 19:36 GMT, before its run (started 19:37:32 by `date`): ALIAS_REACH=5

*(First written with "20:55", a time guessed rather than read: corrected from the run's own clock.)*

**Change, nothing else:** the 1/8-level basin search's radius from 3 texels (+-24 px) to 5 (+-40 px)
(`tests/alias_carry.py`, `ALIAS_REACH`; 3 regenerates the shipped High byte for byte, checked). The quarter-level
hypotheses, the scans, the pick and the print lattice read the basins as before.

**Predicted:** on the barn, the share of the wall at the true pan rises from 44.0% pooled; on pairs 190-235 (truth
22-35 px, the old search's edge and beyond) from 2-12% to over 30%, IF the carry propagates the posters' and the
seam's choice across the tied bars. Confidence about even: the carry switches only cells whose flow lies in a basin,
and many wall cells read between the basins. Pairs where the pan is about one period (the alias near zero) should
change least.

**Refuted** if the pooled share rises by under 5 points: then the reach is not the binding constraint, and the next
suspects are the carry's in-basin rule and the 1/16 level's Moire seed. Either way the ladder gate follows only a
barn gain; nothing ships from this file.

### ALIAS_REACH=5: refuted (run 19:37 GMT)

Pooled share at the true pan 43.6% against High's 44.0%; pairs 195-232 unchanged to the tenth (2.3 / 12.2 / 3.7 /
6.4%). The reach is not the binding constraint. Kept as a switch (default 3, inert); not proposed.

## Registered 2026-11-18 19:39 GMT (by `date`; first written "19:44", guessed), before their runs: the coarse level antialiased (AA_S), and every level (AA_ALL)

The owner's question, tested directly. `aa_variant.py` applies GPT's cascaded box (ripple/aa_pyramid.py, imported,
not edited) to the shipped High: AA_S low-passes only the 1/16 level's luma (the level that aliases a 30 px
corrugation; the 1/8 level samples every 8 px and resolves it), AA_ALL all four levels (GPT's form). One change each
against High. A second measure joins the first: the share of the wall band within 4 px of the band's own most common
reading, whichever that is (coherence: a wall read wholly at the truth or wholly at the alias is coherent; the tearing
is the incoherent mix).

**Predicted (from the mechanism above):** AA_S removes the backward-moving Moire from the 1/16 field on the wall
(its share at -24 to -8 px on pairs 190-215 falls from about half to under a fifth), but the wall does NOT move to the
truth: the share at the true pan rises by under 10 points pooled, because inside the bars the small-motion prior then
prefers the alias nearest zero. The wall's coherence should rise (fewer in-between readings). AA_ALL: the same on the
wall, with a risk elsewhere the record already holds (fine fast texture).

**Refuted** if AA_S puts the wall at the truth (pooled share up 20 points or more): then the Moire alone was the
cause and antialiasing the coarse level is the fix, against my inference. If the 1/16 field's Moire share does not
fall, the low-pass did not take (check the pass) before anything is concluded.

### AA_S and AA_ALL: the low-pass took and did not remove the Moire; no verdict on antialiasing (run 19:39-19:41 GMT)

| field | at truth / reading <= 0 / coherent, pooled over 139 pairs |
|---|---|
| High | 44.0 / 25.5 / 57.5 |
| ALIAS_REACH=5 | 43.6 / 26.2 / 57.4 |
| AA_S | 45.0 / 24.5 / 57.2 |
| AA_ALL | 45.2 / 24.4 / 57.0 |

The registered check came first: the 1/16 field's share at -24 to -8 px on the wall, pairs 190-215, went 44.1% ->
41.3% (both variants). The pass is read (the luma pass binds and reads AA_*_S), but **the cascade is a 16 px box at
the 1/16 level, and a box passes sin(pi w / P) / (pi w / P) of a period P: 0.59 of a 30 px corrugation.** A
filter that keeps a level sampled every 16 px from aliasing must stop periods under 32 px; this one stops periods of
16 px. So these runs do not test antialiasing on the barn: they test a filter too weak at its frequency. The coherence
prediction (rises) missed; the at-truth one (under +10) held, but for the wrong reason, and is not counted.

## Registered 2026-11-18 19:41 GMT (by `date`; first written "19:46", guessed), before its run: AA_S32, a 32 px box at the 1/16 level

**Change, nothing else, against AA_S:** the cascade's S pass averages 4 x 4 taps of the 8 px level at +-0.5 and +-1.5
of its texels, a 32 x 32 box (response 0.06 at a 30 px period, against 0.59). Only the 1/16 luma reads it.

**Predicted:** the 1/16 field's backward share (-24 to -8 px, wall band, pairs 190-215) falls from 44% to under 20%:
the Moire is gone. The final wall's share at the true pan rises by under 10 points pooled (the tie inside the bars
then goes to the small-motion prior's alias nearest zero, not to the truth); the backward share of the FINAL field may
shrink while the share near zero grows. **Refuted** if the final wall reaches the truth (pooled at-truth up 20 or
more): the Moire was the whole cause and antialiasing the coarse level is the fix. If the 1/16 backward share stays
above 30%, the filter is still not removing it, and the cause is not the Moire at all.

### AA_S32: the Moire mostly gone; the wall half right; the fast pairs untouched (run 19:41-19:42 GMT)

The 1/16 field's backward share (wall band, pairs 190-215) **44.1% -> 20.5%** (predicted under 20: met, just), near
zero 31 -> 41%, +16 to +32 11 -> 23%. Final field, pooled over 139 pairs: **at truth 44.0 -> 50.7, reading <= 0 25.5 ->
18.1, coherent 57.5 -> 59.1**. Predicted under +10 at truth: held. But not uniformly, and not for the reason I gave:
where the pan is within about 24 px the wall goes to the TRUTH, not to the near-zero alias (pair 173 72.7 -> 91.4%,
183 64.8 -> 81.3, 205 12.4 -> 37.7, 195 2.3 -> 19.4); where it is 32-35 px nothing moves (220 3.7 -> 8.6, 232
6.3 -> 11.4) and 153 loses (66.3 -> 54.7, as AA_S did). So my inference that the small-motion prior takes the tie once
the Moire is gone is **wrong where the truth is within reach**; the remaining failure is the coarse level's reach.

## Registered 2026-11-18 19:42 GMT (`date` read 19:42:57 in the same command that wrote "19:44": corrected), before its run: AA_S32 + ALIAS_REACH=5

Both measured alone above; combined because the reach's failure alone was read as "the Moire seed puts the cells
between the basins", which AA_S32 removes. **Predicted:** pooled at truth above AA_S32's 50.7 by 5 points or more,
the gain on the fast pairs (153, 220, 232: truth 32-35 px, beyond +-24 px). **Refuted** if the fast pairs stay under
15% at truth: then the 1/8 basins at +-40 px still do not hold the truth, or the carry does not take it, and the
reach needs the coarse level's own search, or a seed from the wall's anchors.

### AA_S32 + ALIAS_REACH=5: refuted (run 19:43-19:44 GMT)

Pooled 50.2 / 18.6 / 58.7 against AA_S32's 50.7 / 18.1 / 59.1; the fast pairs stay under 15% (220 8.7%, 232 11.5%).
The 1/8 basins' reach is not what holds the fast pairs. GLOBAL_SHIFT reads 0 on 18 of 20 sampled pairs in both
(the still walkers): the frame's shift does not carry the pan either.

## Registered 2026-11-18 19:44 GMT (`date` 19:44:27), before its run: AA_S32 + the coarse search's reach to ~39 px

The 1/16 search is a five-step logarithmic search whose first step is 0.75 coarse texels: reach 0.75 x 1.9375 x 16 =
23 px, capped there on purpose early in the project after long-reach false matches on a backlit edge against bokeh
(the comment at the pass). The barn's fast pairs move 30-36 px. **Change, nothing else, against AA_S32:** the first
step 1.25 (reach 39 px). **Predicted:** the fast pairs (153, 220, 232) rise above 30% at truth and the pooled share
above 58%; the pairs already right under AA_S32 hold. **Refuted** if the fast pairs stay under 15%. The risk this
cap was set against (false long matches) is what the ladder and the film windows must then judge; nothing ships
from a barn gain alone.

### AA_S32 + reach 39 px: part of the way in the field, no better to the eye (run 19:44-19:45 GMT)

Pooled **53.4 / 16.2 / 59.9** (High 44.0 / 25.5 / 57.5); the fast pairs 220 13.6%, 232 17.0%, 153 unchanged at 54.7.
Predicted above 30% on the fast pairs and above 58% pooled: missed; not refuted by its own line (232 is above 15%,
220 below). On the fast pairs the 1/16 field now reads mostly ZERO (40-44% of the band): there the pan is about one
period (P ~ 32, d ~ 32-34), the bars match at zero exactly, the walkers are still, and only the wall's dirt, seams and
poster edges say +32, against the level's small-motion prior.

**Viewed (look/cmp-*.png: High above, this variant below, the inserted frame):** pair 205, both tear in about the
same places; pair 220, **High is the cleaner**: it reads the wall as still, which draws the bars clean and steady (as
the 24 fps source shows them), while the variant reads part of the wall at the truth and part at the still alias and
tears where they meet. **The finding that changes the target: a wall read wholly at the truth draws right, a wall read
wholly at the alias draws like the source, and a MIX tears. The share at the truth was the wrong score; what the eye
sees is the mixing.** No variant here is proposed. The full ladder gate of AA_S32 and AA_S32 + reach runs anyway
(started 19:46 GMT), for the record of what a 32 px coarse box costs.

## The owner's question, 19:47 GMT: would a three-frame shader help?

His reasoning: the pan runs one way the whole time, so a shader that sees more frames could rule out the bars'
sign inversion. **On paper:** a constant pan over a periodic wall has a family of equally constant readings (+24 and
+24 - P every frame); three frames, or six, see the same tie in every pair and a zero-acceleration fit accepts the alias
as readily as the truth (PRIOR-ART.md already holds "more frames cannot break an exact half-period tie").
**Measured** (tridirectional-interpolation-propagated.glsl, its own read_view 4, calibrated on M1: 15.84 inside,
0 outside; it clips at 32 px, 2-15% of the band on the fastest pairs): **30.8 / 38.3 / 47.6** pooled, worse than High
on the wall; viewed (look/tri-*.png), sharper bars than High at 173 and cleaner at 205, but scattered with small
block-shaped dislocations at 173 and 220. Not a fix; and the file is the bare propagated family without any of High's
bar machinery, so this is a test of that file, not of the window.

**What his idea turns into, measured (High's wall mode, pair by pair):** the pan starts from rest (pairs 60-96, -2 to
+11 px, under half a period) and High reads the wall right; **from 99 to 190 High's dominant wall reading follows the
truth (+23 to +31) for about ninety pairs**; at 196 it jumps to -7 in one pair, back to +23 at 202, -13 at 208, and
sits at about 0 from 214 to 250 (the pan about one period a frame), back to +31 at 256. The failure is a branch High
HELD for four seconds and dropped, with a 30 px velocity change in 1/24 s that no camera can make. The direction this
points to is not a wider window but MEMORY of the branch: in a cell whose data ties between lattice candidates, take
the one nearest the previous pair's vector there (carried along the motion), not the one nearest zero, and let go
only where the frames contradict it. High already carries state between pairs (the 1/8 temporal seed,
SEED_TEMP_LAMBDA), but as a weak candidate under a 1/16 level that cannot hold more than 23 px. Not built.

### The ladder gate of AA_S32 and AA_S32 + reach (probes/limb/gateset.sh, one run, M5, 19:46-20:00 GMT)

Against the shipped High (regenerated byte for byte), 45 cases. Headline capped mean **+0.057 for both: flat**, with
large moves both ways, so a trade, not a candidate for High in place (the gate allows no case down more than 0.10):

| | AA_S32 | AA_S32 + reach 39 px |
|---|---|---|
| worst | P1_stairs_along_v4 **-8.92** | P1 **-10.22** |
| other losses > 1 dB | V2x -1.93, H2x -1.74, H1 -1.43, L2 -1.41, P3 -1.37, V1 -1.35 | H2x -2.07, P3 -1.98, V1 -1.39, L6 -1.35, V2x -1.14, H1 -1.11 |
| best | P5_stairs_along_v8_alias **+12.68**, L4_trans_40px **+9.30** | P5 **+12.70**, L4 **+10.59**, L2 +5.21 |
| other gains > 1 dB | L6 +4.72, L3 +2.40, A3 +2.13, L1 +1.81, L8 +1.76 | L3 +3.50, A3 +2.90, L1 +2.09, L8 +2.06 |

Worth keeping from it: a real coarse antialias with the reach lifted takes the ladder's known speed ceiling (L4, 40 px)
up 9-11 dB and the P5 alias trap up 12.7, and costs the slow stairs along their bars (P1) 9-10 dB and the 24 px bar
cases 1-2 dB. Not pursued now: the barn's picture did not improve, and the branch memory is the next registered idea.
High's run took 478 s against 184-187 s for the others because it shared the GPU with the tri renders; timing was not
the measure here.

## The owner's rule for what follows (2026-11-18, 20:05 GMT)

"The 0.10 dB drop rule is arbitrary - what matters is whether the real footage looks better or not. Testing on real
footage should always get a real comparison rather than a numbers by the book approach." From here every candidate is
shown to the owner as a synchronized side-by-side of the real clip in motion, and the ladder's losses are read as
places to look on footage, not as vetoes. The two antialiased variants above were set aside on their stills, not on
the ladder: on the barn they did not look better (pair 220 worse).

## Registered 2026-11-18 20:14 GMT (`date` 20:14:17), before its run: BRANCH_MEMORY=1

`tests/branch_memory.py`, a switch on gen_variational.py (off: the shipped High byte for byte, checked). High plus one
change: the previous pair's final A->B field, kept at 1/8 resolution (cleared at a cut), is a fifth candidate at both
1/8 refines, taken only where it is a different branch from the pick (over 12 px away), its SAD is within 10% (+0.01)
of the pick's, and the cell has texture. 90 passes against 89.

**Predicted:** on the barn the wall's dominant reading stays on the true branch through pairs 196-250, where High
drops it (High's band mode is the truth's within 4 px on about 55% of pairs 99-262; the candidate on 80% or more);
pooled share at the truth above 60% (High 44.0%); and, the verdict that counts, the inserted frames of 196-250 show
whole bars where High's tear, in the owner's side-by-side. **Refuted** if the mode still leaves the truth at 196-214.
If the 1/8 field holds the truth and the final field does not, the later passes (the quarter-level carry, the print
lattice) switch it back, and the per-level dump will say which. Risks to look for on footage: a remembered vector
dragged across a moving edge (the walkers' outlines), and a wrong branch held after a pan stops.

### BRANCH_MEMORY=1 (form 1): holds longer, then erodes (run 20:14-20:15 GMT)

Pooled at truth **48.7%** (High 44.0); the band's mode within 4 px of the truth on **79%** of 134 pairs (High 72%: my
"about 55%" in the registration was a guess, not a reading). Pairs 192, 240 and 258 now right; 198, 210, 222-246 still
on the alias. Predicted 80% and above 60% pooled: missed; not refuted by its line (the mode still leaves the truth at
196-214). Traced level by level (pairs 186-215): at 190 the 1/16 level flips to the Moire (-15); the 1/8 level, with the
memory, holds +23 but its share at the truth erodes 58 -> 49 -> 49 -> 42 -> 36% over 190-194, and the mode flips at 195.
A cell that loses one tie (grain on a 24 px window) drops to the alias, and its own memory then HOLDS the alias: form 1
can lose cells and never win them back.

## Registered 2026-11-18 20:16 GMT (`date` 20:16:20), before their runs: BM_FORM=2, and BM_FORM=2 with BM_TIE=0.25

**Form 2, one change against form 1:** the remembered candidate is the local majority of the memory (3 x 3 samples two
cells apart, 48 px; at least five agreeing within 12 px), so a lost cell is re-offered its neighbours' branch every
pair. **Form 2 + tie 0.25, one change against form 2:** the remembered branch is kept unless the frames prefer the
other by more than 25% (was 10%).
**Predicted:** form 2 stops the erosion: the 1/8 share at the truth stays above 45% through 190-200 and the mode holds
the truth past 195 (to about 205); the pairs where the pan is one period (214-250) are lost either way, since the
memory has nothing right to carry once the whole wall has gone. Tie 0.25 holds further. **Refuted** if form 2's
1/8 share erodes as form 1's did (under 40% by 194).

### BM_FORM=2 and BM_FORM=2 + BM_TIE=0.25 (runs 20:16-20:18 GMT); viewed; the exterior check (20:19-20:24 GMT)

| field | at truth / reading <= 0 / coherent, pooled | band mode at the truth (134 pairs) |
|---|---|---|
| High | 44.0 / 25.5 / 57.5 | 72% |
| form 1 | 48.7 / 23.6 / 58.8 | 79% |
| form 2 | 49.1 / 23.1 / 59.0 | 81% |
| form 2 + tie 0.25 | 50.5 / 22.2 / 59.0 | 83% |

**Form 2 refuted** by its own line: the 1/8 share at the truth still erodes to 36% by pair 194 (as form 1); the local
majority is not what holds it. **The tie is:** with 0.25 the 1/8 share holds 50 / 47 / 44 / 42% at 194-200 and the
wall's mode stays on the truth to pair 204 (High loses it at 192, form 1 at 194). Pairs 206-252 (the pan about a period)
are lost by every form, as predicted. Ladder of form 2 + tie (one run, bench.sh into the AA gate's run, gatetable
against the same High): capped mean **+0.085**, one case down more than 0.3 (**P1 -1.48**), up P5 +11.91, L4 +3.30,
R3 +2.42, L1 +0.96, L3 +0.90, V3x +0.80.

**Viewed, stills (look/bm-*.png, High above):** at 194 and 198 both tear across the left half of the wall, in slightly
different places; at 206 they are almost the same. Half the wall at the truth is still a mix, and a mix tears. What a
still cannot show is the wall's branch flipping from pair to pair (High: +23 / -13 / -13 / -7 / -15 over 190-198), which
the memory holds steady through 204: that is for the owner's eyes in motion.

**The exterior check** (the next 14 s of the film, own folder: faces, walkers, a brick wall and the hangar's corrugation
under a pan, cuts): retained frames identical; inserted frames differ from High by 0.30 codes on average, at most 2.26
(7% of pixels by more than 8 codes, at the end of a fast pan). Viewed at the two most different spots: the brick wall
mid-pan much the same; **the yellow truck at the end of the fast pan: High draws a doubled wheel and doubled panels, the
memory one clean wheel** (and one small torn fleck below it). No harm seen.

**For the owner:** synchronized stacked videos, High above and the memory (form 2 + tie 0.25) below, at 48000/1001:
the barn's wall half at full resolution (and at half speed), and the whole exterior shot. Not proposed for High until
he has watched them.

### The owner's verdict, 2026-11-18 20:42 GMT: "Better"

Having watched the three side-by-sides (the barn's wall at speed and at half speed, the exterior shot), the owner judges
the memory version (BRANCH_MEMORY=1 BM_FORM=2 BM_TIE=0.25 on High) **better**. It becomes a shipped variant,
`bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut-memory.glsl` with its 4K
twin; whether it replaces High in place (and Cadence's High graphs) is his call. Still open on the barn: pairs 206-252,
where the pan is about one period a frame and every form reads the wall as still.

### The 4K twin (20:45-21:00 GMT)

The barn's pairs 140-240 upscaled to 3840 x 2160 (a cost and correctness measure, not a picture sample): both 4K twins
run with no hook skips and the right counts. **A read-path error, found and fixed:** the scaler doubles the final pass's
FLOW_H -> px factor (2.0 -> 4.0) and fielddump.py read every file with 2.0, so a 4K twin's field came back at exactly
half; fielddump now reads the factor from the shader (2.0 / 4.0 checked). Doubled, the band mode against twice the
truth: shipped High-4K right at 160 and 180, on the alias from 192; **the memory's 4K twin right through 192 / 196 /
200 / 204 (+52 / +52 / +44 / +44 against +48 / +47 / +44 / +43), lost from 210**: as at 1080p.

## Registered 2026-11-18 21:13 GMT (`date` 21:13:34), before its run: BM_SUBPIX=1

Where the memory still loses (pairs 206-252), the pan is about one period a frame and the still alias wins the 1/8
level's comparison by more than the 25% tie. **Suspected mechanism (inferred, this run tests it):** the 1/8 refine steps
in WHOLE 1/8 texels (8 px); the still alias sits on whole texels and matches the bars exactly, while the true 30-35 px
is 3.75-4.4 texels, so the remembered candidate is compared at an offset up to half a texel (4 px) from its own match,
on bars whose profile is sharp. **Change, one, against the shipped memory:** before the tie test, the remembered
candidate is refined at half- and quarter-texel steps (8 neighbours each), and its best SAD there is the one compared.
**Predicted:** the 1/8 share at the truth on 206-212 rises from 11-23% to above 30%, and the wall's mode holds the truth
past 210. **Refuted** if 206-212 stay under 25%: the alias then wins on the data itself, not on the grid.

### BM_SUBPIX=1: held, partly (run 21:14-21:16 GMT); the variant shipped; its cost

The 1/8 share at the truth on 206-212 rose from 23 / 23 / 18 / 11% to **31 / 31 / 33 / 28%** (predicted above 30: met
on three of four, refutation line 25%: not crossed); the wall's mode holds the truth through 208 (the memory lost it at
206) and drops at 210 (predicted past 210: missed). Pooled 53.5 / 20.6 / 60.4; mode at the truth on **86%** of pairs
(memory 83, High 72). The grid was part of the cause. Viewed (look/sub-*.png, memory above): at 208 both still tear
around the same seam, the sub-texel one over a smaller patch. Not in the shipped variant: the owner judged the memory
without it; it goes to him as its own side-by-side.

**Shipped (variant):** `…-lattice-cut-memory.glsl` and its `-4k` twin, generated with `BRANCH_MEMORY=1` alone (the
switch's defaults are the judged form: BM_FORM=2, BM_TIE=0.25; the file differs from the one he watched only in its
recipe line); smoke.sh now regenerates it and its twin byte for byte: **19 of 19**. **Cost**, from the lossless file,
MoltenVK on the M5, 24000/1001 -> 48000/1001, decode included, warm-up then three interleaved rounds, medians: High
17.52 ms an output, memory 18.28 (+4.3%), memory + sub-texel 18.20 (+3.9%). Cadence's Metal engine not measured.

### The owner, 2026-11-18 (received between 21:26 and 21:49 GMT): sub-texel "no significant difference"; the memory into High and Cadence

Of the memory against memory + sub-texel side by side: "There is no significant difference". `BM_SUBPIX` stays a switch,
off. And: "Yes please the new version into cadence for further real content testing", in answer to whether the memory
should replace High including Cadence's High graphs. **High changed in place** (as WARP_VOTE=2 was on 2026-11-13): the
tier file and its 4K twin are now generated with `BRANCH_MEMORY=1` (90 passes; sha256 bf247af04fb8... / 9b83ece5ac46...),
`content.HIGH_ENV` carries it, smoke.sh regenerates High with it, the separate `-memory` files are gone (they were the
same shader), SHADERS.md's High row says so. The old High regenerates with BRANCH_MEMORY=0. GPT's ripple/build.py pins the
previous High's hash and will refuse until re-baselined, as it is meant to.

**Metal cost** (QuadDemo --bench, the demo engine on the graphs Cadence bundles, the player's path: hardware decode,
zero-copy, cached pairs; the barn as H.264 and its 4K upscale; 23.976 -> 47.952; a warm-up, five interleaved rounds,
medians, the M5): 1080p High 11.01 ms an output, memory 11.19 (**+1.6%**); 4K 16.18 against 16.26 (**+0.5%**). Inside
the 20.85 ms budget at 48 with room. (The 13 November entry's 20.62 ms was a different measure; same tool, same day,
same clips here.)

**Metal draws what libplacebo draws, memory included** (metal_check.py: QuadDemo on Cadence's graphs against the
libplacebo renders, the barn's pairs 186-212, the memory's change on the wall band): size Metal 1.3-7.0 codes against
libplacebo 0.9-7.4, the two change maps correlating **+0.61 to +0.94, median +0.85**; the hosts' absolute difference a
steady ~5 codes (the colour paths, reported, not judged). **A trap on the way, kept:** the first run read a median
correlation of **-0.48** with 13-20 codes between hosts. The clip was a STREAM COPY of the film (338 frames against the
lossless cut's 336); ffmpeg decodes it in step (edit list honoured, frame 0 identical), QuadDemo's AVFoundation reader
does not, so Metal's frame k was another picture than libplacebo's frame k. Re-encoded from the lossless cut (336
frames, no edit list, 0.2 codes from it): the result above. The timings used the stream copy for both shaders, so they
stand.

**Into Cadence** (its repository, branch `claude/high-branch-memory`, nothing committed): High's two graphs regenerated
with gen_metal.py from the new High and its twin (graph.json naming bf247af04fb8... and 9b83ece5ac46..., 90 passes each),
90 metallibs each for macOS, iOS and tvOS at the project's floors (compile-metallibs.sh); the old pair and the installed
Cadence 1.1.5 (202611141848) backed up under the n-frame scratch folder. One code change: Cadence's main had made MCI the
Mac default (2026-11-15, for the MCI content-test build); a regular build from it would have opened the owner's films
with MCI. Now the MCI test app (its own bundle identifier) defaults to MCI and the regular Cadence to n-frame; a saved
choice still wins (the owner's Cadence has none).

**Cadence's checks and the install (21:58-22:12 GMT):** mac-tests short **57 of 57** on the M5 with the new graphs (after
two harness repairs: its share python now from `CADENCE_TEST_PY`, and the stale Xcode project regenerated); installed
on the owner's word over his Cadence (his 1.1.5 kept in the backup folder); the installed app opens with n-frame by
default and runs High's 90 passes from metallibs at 48.3/s of 47.95 with no late frames. **The real-content test is
now his.**
