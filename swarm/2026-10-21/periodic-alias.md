# Lane periodic-alias: the quarter-level carry is built; the family's open gap is a period band (6-15 px) that every switch after the cage is blind to, through one shared gate

Swarm 2026-10-21, lane periodic-alias. Paper only, plus one CPU-only numpy check (marked [M]). Scratch:
`~/Developer/np-scratch/swarm-20261021/periodic-alias/` (`flag_region.py`, `flag-region.txt`,
`ambiguity-cases.txt`). Nothing written into REPO; the worktree's `INSTINCT.md` carried the owner's 21:25 log line
before this lane started.

## What I read

- `NFRAME-LIMITS.md` 3972-4180 (the cage, the coherence gate, C3), 4523-4917 (V3 reopened; v3edges; the flag and the
  carry offline; the carry in the shader, builds 1-6; the aperture; B1), 4918-5259 (the weave through 1c); the
  `refuted` grep; section 8 by grep only (558-584, 804-816).
- `ENERGY-TRANSFER.md` 1996-2175 (stage 0b-0f), 2672-3212 (lead 4 steps 1e-1r, PRINT_LATTICE, cost cuts), 3289-3470
  and 3645-3881 (decisions, cost cap, trust gate T0, L1, U1-U5, trust5, L2, Sonic, where it stands), Sources.
- `PRIOR-ART.md` 213-437, 512-692. `tests/gen_variational.py` switch comments; `tests/alias_carry.py` 1-120 and
  225-335 (code); docstrings of `outline_adopt.py`, `print_lattice.py`, `trust_gate.py`; `tests/scenes.sh` 136-221,
  570-610; headers of `carry.py`, `ambiguity.py`, `v3phase.sh`, `cage.sh`; `tests/TESTING.md` 165-180, 2176-2186,
  2328-2336; `SHADERS.md` "Which one to use", 740-750; `REPAIRS.md` 76-132, 201-260; `INSTINCT-STRATEGY.md` 1-130.
- Not read: the trust gate's T1/T2 build (3470-3645), lead 4 steps 1a-1d, the stage 1a-1c unwrapping record,
  `PREDICTION.md`, the Metal lockstep, the field instruments.

## Findings

1. **[R] The prompt's premise is stale: the quarter-level carry's GLSL form is built.** `ALIAS_CARRY=1`
   (`tests/alias_carry.py`, 2026-09-28; NFRAME-LIMITS.md 4707-4760) is the offline carry in GLSL: each quarter-level
   cell keeps its own two basins with Imry-Ma flat costs on a tie, four SGM min-sum scans, a pick that only switches a
   tied cell between its aliases. Build 6 is in the player's High and Standard tiers (SHADERS.md "Which one to use").
   Phase-averaged V3 (six starts x three runs), down / up: recommendation 22.6 / 19.7; cage + prior + carry 28.6 /
   28.6; with energy 29.1 / 29.1 (4733-4737, 4801-4816); Metal | libplacebo 29.44 | 29.44 (4891).
2. **[R] What was NOT built is a quarter-level rival SEARCH.** The hypotheses pass (alias_carry.py 282-312) takes
   both basins from the 1/8 level's curve (`ALIAS_E`: 7 x 7 shifts of 8 px) and refines each +-2 quarter texels.
   carry.py searched +-5 quarter texels (121 SADs) per cell. The prompt's "the rival search is the engineering
   problem" is right for this residue only.
3. **[R, code] One gate feeds every switch after the cage.** `ALIAS_E_M_ST` (the 1/8 margins) is read by ALIAS_PRIOR,
   ALIAS_CARRY, OUTLINE_ADOPT ("only where the 1/8 level's cost curve holds a RIVAL basin within margin 0.3"),
   PRINT_LATTICE (5 of 25 cells under 0.3) and TRUST_GATE (the same plus the aliasing flag); gen_variational.py
   840-848 asserts the dependency. A rival must sit at least 2 texels (16 px) from the best with a ridge on the
   straight path (`alias_basins`: `if (n < 2) continue`, ridge >= 0.25 S).
4. **[J] So a print of period 6-10 px is invisible to that gate, by construction.** For 9 px (the cage, the film's
   railing, C3) the one-period alias is 1.125 texels away, under the floor; the two-period alias at 2.25 texels is
   legal, but the path sample at 1 texel (8 px) lies 1 px from the one-period alias, a low cost, so no ridge.
   **[M] Checked, CPU only** (`flag_region.py`: ambiguity.py's analyse() restricted to the region, every other frame
   2-19, A->B): share of textured 1/8 cells with a rival under margin 0.05 / 0.15 / 0.30, and the best shift's size:

       C1_cage_drift (the rectangle)   0.2% / 0.4% / 0.7%    24,381 cells   best shift 0 / 1 / 2 / 3 texels: 74 / 17 / 3 / 6%
       C3_bars_spin_drift (the disc)   1.6% / 4.5% / 7.8%    35,618 cells                                    26 / 46 / 21 / 7%
       V3_stairs_sq24_v12 (control)    90.6% / 96.9% / 96.9%  7,776 cells                                     0 / 8 / 29 / 63%

   The carry, the adoption, the lattice and the trust gate can never open on the cage family. C3 (22.7; hold 24.4,
   blend 28.9; NFRAME-LIMITS.md 4179) has been untouched since 2026-09-21 by construction, not by difficulty.
5. **[M+J] C3 at the 1/8 level is a confident lock, not a tie.** On the disc the best shift is one texel (8 px, a
   period out) on 46 percent of cells and two on 21, where the truth is 0-2 px, and under 8 percent are flagged.
   That is the weave's anatomy at 1/8 (stage 0d, ENERGY-TRANSFER.md 2076-2098), not V3's. A tie-breaker is the wrong
   tool for C3; the tools for a confident lock (a re-score among aliases; a wide search at the first honest level) are
   gated shut by finding 4.
6. **[R] Why QZERO_MOIRE and the coherence gate stop at C3.** The zero descent wins only as the smaller of two good
   matches with a ridge between, and on C3 "the ambiguity along a bar is a valley, not a second minimum" (4080-4083);
   the gate's agreement test is rightly closed (4176). The normal-flow projection of the OUTPUT changed nothing
   (21.93 -> 21.93); "what costs on C3 is the ACROSS error (7.4 px median on the wrong texels, a period or two out) at
   a motion of one to two pixels" (4175).
7. **[R] The ladder's V3 is not a stable measurement.** Bimodal 26 / 19-20 by start and run (4536-4543); the Arc
   lands on the bad branch deterministically, the M5 on the good one (tests/TESTING.md 2179-2182, 2332). The honest
   form is `v3phase.sh` (about 2 minutes). Every V3 number below is phase-averaged.
8. **[R] The HELD trust gate.** trust5: ladder +0.21 capped, no case down, L7 +8.73 (the period-16 trap, which
   nothing else fixes: PRINT_LATTICE's ladder had L7 -0.65); the weave box +3.0 / +5.7 / +10.4 / +6.3 / +5.1 at 5 /
   11 / 13 / 15 / 19; noise identical; with CUT_MOTION the frame-filling pan +6.4 and +2.8 dB more at 5 and 19
   (ENERGY-TRANSFER.md 3752-3790). Cost +8 percent on film. L2 passed on medians; frame by frame 6,876 of 21,678
   frames move, extremes +3.14 / -3.26, one run (Sonic @4341, frames 815-833) at -2.4 to -3.0 (3792-3803). Held for
   cost, the Sonic run, and the cut fix taking most of the frame-filling case (3875-3880). Half of its weave gain is
   the price of its two guards (trust1: +12.5 / +11.9 / +8.6; ladder V3 -10.97, R3 -8.89); U5 found no winner /
   runner-up ratio that separates (3697-3712).
9. **[R] The undecidable case was never built** (NFRAME-LIMITS.md 4911; PRIOR-ART.md 315).
10. **[R, grep] The player's tiers have never been scored on the case family that named them.** The last C1 / C2 /
    C3 and railing numbers are the three-switch file's (34.6, 31.6, 22.7, 27.1; 4156; SHADERS.md 746). No `-carry`,
    `-adopt`, `-lattice` or `-cut` file has a cage or railing number; C1-C3 and B1 run "only by name" (TESTING.md
    175). Finding 4 predicts no change, but it is a prediction.
11. **[R] The slow and fast weave have their switches** (OUTLINE_ADOPT +22-30 dB at 3-5 px/frame on a given region;
    PRINT_LATTICE +11.7 / +4.4 / +4.4 / +8.0 at 5 / 11 / 13 / 19, ladder -0.015 after 1r), and both act on prints of
    period 10-28 px and not under (finding 3).

### The map

| Case | Mechanism | Switch | Kill test that showed its limit | What is left |
|---|---|---|---|---|
| V3 (stairs P=24, 12 px/f) | exact two-way tie at the quarter level; held by the 1/8 temporal seed from one edge | GLOBAL_SEED (lucky), ALIAS_PRIOR, ALIAS_CARRY b4-b6 | v3phase.sh both ways 28.6 / 28.6; B1 up 23.7-24.5 | B1 up 1.5 dB under its down form; the ladder scores one phase |
| The cage (P=9, 0.5 px drift) | 1/8 Moire; the quarter refines a period out; true-flow warp 37.4 < blend 43.2 | QZERO_MOIRE (+3), COHERENCE_GATE; stacked 34.6 | remedy 4 (agreement alone) wrecked the ladder; the gate alone L1 -24 | the railing 27.1 vs blend 29.4; nothing since can see 9 px (finding 4) |
| C3 (P=9, rotate + drift, 0-2 px) | 1/8 confidently a period out (46% one texel, 21% two); no ridge along a bar; the gate rightly closed | none (22.7; hold 24.4, blend 28.9) | normal-flow projection 21.93 -> 21.93; gate alone 26.8 with L1 -24 | everything |
| B1 (V3 over a panning background) | the global shift (+24, +24) is a Moire of the background and decides every local tie | ALIAS_PRIOR; the aperture rule b5/b6 | b5: A6 -1.21 (M2's texture read as stripes at 20 px) -> b6 at 40 px | up 24.4 vs down 27.4 |
| Slow weave (P=14/28, 3-5 px/f) | the comb (the finest aliasing level's texel); the edge ring reads truth | OUTLINE_ADOPT | stage 0b-0e: the tie too loose, anchors wrong at 1/8, zero descent forced open changes nothing | region found only for a moving box; Metal keeps +2.8 of +9.8 at 5 px/f |
| Fast weave (11-19 px/f) | the lock enters at 1/16 and 1/8; the data prefer the truth by 0.019 luma at full res | PRINT_LATTICE + isolation + cost cap | L1: V1 -13, H1 -10.4 before 1r; L3 +107% time before the cap | 60-73% of the gain on a frame-filling print; frames never looked at |
| Frame-filling print, 5 and 19 px/f | the scene-cut gate held a frame | CUT_MOTION | CM1-CM3 | none |
| L7 (sin x sin P=15.7, 16 px/f) | ambiguous and aliased at 1/8 | TRUST_GATE trust5 (+8.7), HELD | trust1: V3 -11, R3 -8.9 | the Sonic run; 8% cost |
| Print behind a still window (P/2) | undecidable: +P/2, -P/2 and a flash are one picture | none | never built | finding 9 |

## Proposals, ranked

Proposals 1, 2, 3 and 4a are measurements (one kind); 5 and 4b are mechanisms of two kinds (a search; a decision
rule). Cheap steps first, as the brief asks.

### 1. Score the current tiers on the cage family and the railing (rank 1)

**Mechanism.** `cage.sh C1_cage_drift C2_cage_drift_occluded C3_bars_spin_drift` with the High, Standard, Low and
`-global-cage` files (region PSNR); the railing clip through the `dig` probe if the clip is still at hand. No code.
**Prior attempt.** The three-switch file, 2026-09-21 (finding 10); nothing since.
**Prediction.** [J] On every tier carrying the cage: C1's rectangle within 1.0 dB of 34.6, C2 within 1.0 of 31.6,
C3's disc 22.7 +- 0.5, the railing 27.1 +- 0.3 (finding 4: no later pass can open there). The Low tier: C1 24.9
+- 1, C3 21.9 +- 0.5.
**Kill test.** Any tier moving C3 or the railing by more than 1 dB either way kills finding 4's "by construction";
the map is redrawn before proposal 5 is built. Within the bands, confirmed. No inconclusive outcome.
**Cost.** About 4 GPU minutes plus 1 for the railing.

### 2. C3's ceiling: the true-flow warp on the disc (rank 2)

**Mechanism.** The oracle variant that forced the cage's uniform 0.5 px (NFRAME-LIMITS.md 4001-4005) takes C3's
closed-form law per texel, `v = (1, 0.5) + (0.15 / 24) * (-(Y - cy), X - cx)` (scenes.sh 598-601); scored on the
disc beside hold 24.4 and blend 28.9.
**Prior attempt.** The cage's oracle (37.4 against the blend's 43.2). C3's was never taken; its motion is 1-2 px on
3-px bars, not 0.5.
**Prediction.** [J] The oracle beats the blend: 31-35 dB. A 1-2 px blend of 3-px bars ghosts visibly.
**Kill test.** Oracle under 28.9 kills the flow route for C3: it is then a know-when-not-to-warp case, and the answer
is the coherence gate's third test with the SMALL good match in place of zero (proposal 5's rival as the reference).
Above 31 confirms 6-10 dB on the table for proposal 5. Between: tips to the gate route.
**Cost.** One hour for the oracle law; 1 GPU minute.

### 3. Build the undecidable case as a ramp, and measure the refusal (rank 3)

**Mechanism.** `D1_print_behind_window`: V3's texture (TEX_V2, scenes.sh 162) fills a fixed 300 x 300 window with
still edges (a mask over a taller print), the print drifting vertically with speed ramping 4 -> 20 px/frame over 2 s
(through P/2 = 12 at 1 s); `D1h` at a constant 12. Read: PSNR on the window; the sign of the window's median vertical
flow per frame (consistency); the blend share.
**Prior attempt.** None (finding 9). V2 and V3 have intrinsic ends; this has extrinsic ones (Shimojo), the survey's
"should fall back gracefully rather than choose".
**Prediction.** [J] Below about 11 px/frame the field reads the truth (Itoh's condition holds inside); above 12 it
reads v - 24 (the shorter alias wins by the magnitude prior: the weave's comb in one dimension, with a period the 1/8
level sees unaliased, so TRUST_GATE stays shut and PRINT_LATTICE's uniqueness test refuses the exact tie). PSNR on the
window >= 35 below the knee, 5-12 dB above it (inverted bars). No gate blends: the coherence gate's agreement tests
fail (frames differ by whole bars); QZERO_MOIRE finds no smaller good match. At D1h the sign is set by the first pair
and held by the 1/8 temporal seed: sign changes on under 10 percent of frames.
**Kill test.** "Graceful" dies if the sign flickers on more than 10 percent of D1h's frames, or a gate blends more
than 20 percent of the window (a grey smear); either names the fix (a bounded hysteresis term for flagged cells with
NO anchor, the survey's item 4; or the agreement test). A knee far from 12 (say 8) kills the "Itoh inside" reading:
the small-motion prior decides, and the survey's warning about it applies to 1-D prints too.
**Cost.** One hour for the scene; 1 GPU minute per shader, four shaders.

### 4a. Explain the trust gate's Sonic run before deciding it (rank 4)

**Mechanism.** On Sonic @4341, frames 810-840: trust5's gate-open mask, decided mask and replaced vectors (a
`leveltap.py`-style tap at the 1/8 grid) beside the per-frame PSNR against the default (`framediff.py`). Three
candidates: (i) decisions where the 1/255 margin is under the compression noise; (ii) the offer replacing a right flow
with a block-better alias on content locally periodic AND aliased (a fence, a grille); (iii) a cut-gate interaction.
**Prior attempt.** None on these frames; L2 was passed on medians.
**Prediction.** [U] (i): the decided cells' residual at the kept flow is 2-5/255 and the replacements win by 1-2/255.
**Kill test.** (i) sends the gate to 4b (resolve). (ii) retires it as a tier (the harm is in the offer; only region
consistency would mend it, lead 3's parked territory), kept as a switch. (iii) is CUT_MOTION's, not the gate's.
**Cost.** 1 GPU minute; an hour's reading. I would not retire a built, ladder-clean switch that holds the only L7 fix
on an unexplained run nobody has looked at; this is the look.

### 4b. If 4a says (i): a noise-aware decision margin, one constant (rank 6)

**Mechanism.** `TG_PICK` becomes `max(1/255, k * r)`, r the 16 x 16 block's mean |A - B| at the KEPT flow after its
+-0.5 px refine: zero on a clean synthetic print, 2-5/255 on compressed film. The winner must beat the kept flow and
the runner-up of a different basin by that margin.
**Prior attempt.** The winner / runner-up ratio (U5: "no ratio separates them"). This is not a ratio of candidates but
an absolute margin scaled by the data's own residual, which the clean weave does not pay and film does. Nothing
blends, so not the refuted agreement gate.
**Prediction.** [J] Sonic 815-833 from -2.4..-3.0 to within +-0.5; L2's 6,876 moved frames under 3,000; the weave box
keeps +5.7 / +10.4 / +5.1 within 1 dB; L7 +8.7 within 1 dB; V3 phase-averaged, the cage rectangle, C3 and the railing
unchanged (the gate is shut on all four).
**Kill test.** The Sonic run unmoved kills (i): retire as a tier. The weave box down more than 2 dB at 11 or 13 kills
the constant (the weave's margin 0.019 is 5/255: k must stay under about 2).
**Cost.** One constant (r is already in the decision); ladder 6 minutes on the Arc; L2 about an hour; v3phase 2 min.

### 5. The fine-period rival: a quarter-level one-dimensional search along the stripe normal (rank 5; the one leap)

**Mechanism.** A quarter-level pass `ALIAS_Q1D`, only where the 1/8 level's 5 x 5 structure tensor is coherent (the
carry's `aperture_w`, coherence over 0.5, already computed per quarter cell) and `ALIAS_E` has no rival. Along the
tensor's major axis (the stripe normal) it scores a 1-D SAD (9 taps along the normal, 1 across: on stripes the cost
is constant along them) at 9 shifts (+-4 quarter texels, +-16 px) from the level's own flow, and keeps the best and
the lowest second basin at least 2 quarter texels (8 px) away behind a ridge: the same ridge rule on a 1-D curve,
where the along-bar valley cannot hide the across-bar ridge. The rival and its margin enter the carry's hypotheses as
b2 where the 1/8 pass gave none, so the existing pick, scans and aperture rule consume it unchanged: an exact tie gets
flat costs and the rim's anchors decide; a near tie goes to the SMALLER of two good matches by the existing magnitude
prior (QZERO_MOIRE's own rule, now with a real second minimum instead of zero).
**Count.** 720p quarter grid 320 x 180 = 57,600 cells x 2 directions x 9 shifts x 9 taps = 9.3 M fetches per pair,
about a quarter of ALIAS_E's 35 M (14,400 x 2 x 49 x 25), and only coherent cells run. [J] Under 0.5 ms at 720p.
**Prior attempts, and why this is not them.** QZERO_MOIRE: zero as the rival with a 2-D ridge test, which fails on
C3's along-bar valley (finding 6); here the curve is 1-D across the bars and a rival at 1-2 px is a minimum, not
zero. The tensor FILL (PROP_TENSOR, refuted twice): it rewrote flows along bars; here nothing is rewritten, the
along-bar component is kept (the carry's rule). The normal-flow projection of the output (changed nothing): it moved
the invisible along-bar component; this changes the across-bar component, the 7.4 px error. The 1/8 basins pass:
blind under 16 px (finding 4). carry.py's 2-D +-5 search (121 SADs): this is its 1-D, 9-SAD form for the one case
where 2-D is unnecessary (stripes); the 2-D rival stays with ALIAS_E where it works (the weave's offsets were true
lattice vectors 96 percent of the time, ENERGY-TRANSFER.md 2857).
**Prediction.** C3's disc 22.7 -> 25-27 (above the hold; the blend 28.9 stays above unless proposal 2 says the warp
can beat it, then 29-31). C1's rectangle +-0.5 (the gate already blends it; in a dump the one-texel cells fall from
17 to under 5 percent). The railing 27.1 -> 27.5-28.5 [U]. V3 phase-averaged within 0.5 both ways (its +-12 rival
lies in the +-16 range: the same tie the 1/8 pass already hands the carry). V1 / V2 / H1 / H2 within 0.3 (aliases
at 18 px are out of range or already found); P1-P5 within 0.3 (motion along the bars: the across-bar best is 0, the
rival at 24 px out of range); M1, M2, M3, L7 untouched (coherence 0 on isotropic texture). Real footage: the four
clips within 0.1 dB, under 2 percent of cells changed (railings, blinds and text are coherent; the margin and ridge
rules must hold it).
**Kill test.** C3's disc under 23.5 with the new rival found on more than 50 percent of the disc's cells (a dump)
kills the quarter-level reading: something later erases the repair (the variational iterations pushed the weave's lock
outward, stage 0f; the half level lost part of the lattice's gain, T0), and the next step is `flowtap.py` on C3 stage
by stage, not another search. 25 or above confirms; 23.5-25 tips to the tap. Any ladder case down more than 0.5 on
the Arc keeps it a variant, not a default; any real clip down more than 0.2 kills it.
**Cost.** A generator switch (one hour; half a day with the dump); ladder 6 min x 2 on the Arc; cage.sh 4 min;
v3phase 2 min; real.sh 10 min.

Not proposed: a 2-D quarter-level rival search (350 M fetches per pair at 720p, ten times ALIAS_E); the lattice
vectors as the rival source (PRINT_LATTICE finds them FROM the 1/8 basins and inherits the blindness); the comb's
period (it is the level's texel, not the content's).

## Refuted entries checked

Not retried, and not repeated by any proposal: blending wherever the frames agree locally (the cage's remedy 4,
NFRAME-LIMITS.md 4031-4037; the old occlusion fallback); local agreement as a gate (the second condition alone, M1
-4.7); the flow's magnitude as a gate (4043); along-bar cues on C3 (the normal-flow projection, 4168-4178; the tensor
FILL, 2716-2728); replacing the seed under Moire outright (remedy 1 before its competition: L1 -5, L2 -6, M1 -10,
4014-4018); the prefiltered pyramid (section 8); averaging of vectors, including agreement-weighted propagation
(PRIOR-ART.md 266-269, 369-372); the carry on a confident lock (stage 0b-0e); the zero descent forced open on the
weave (0e); the lattice stand-ins (1e-1g); the small-vector prior alone (breaks 15-17 px/frame); ambiguity alone as a
trust gate (trust1: V3 -11, R3 -8.9); a winner / runner-up ratio as the decision (U5); the global shift deciding a
local tie (B1); RANSAC and consensus fits; temporal multi-baseline (the CRT).

## Hand-offs

- **The ladder lane:** V3 is bimodal by phase and host (finding 7); mark it or replace it with v3phase.sh's mean.
  C1-C3, B1 and the railing run only by name and were never run on the shipped tiers (finding 10); a named "cage
  set" in every tier gate would have caught this. The lattice "was adopted on medians alone; nobody has looked at its
  frames this way" (ENERGY-TRANSFER.md 3803): framediff.py High against Standard is one Arc hour.
- **The owner:** whether C3's target is the hold (24.4), the blend (28.9) or above (proposal 2 says what is possible;
  he says what is wanted); whether the railing clip (`tests/probes/dig/`) is still available; the trust gate decision
  after 4a.
- **A weave or Metal lane:** OUTLINE_ADOPT's 5 px/frame gain is "a tie-break that sub-LSB differences flip"
  (NFRAME-LIMITS.md 5236): Imry-Ma at the bit level.

## Felt

- Felt: surprise, "its GLSL form was never built" against alias_carry.py's six builds, high; the prompt was written
  from the 09-27 entry. -> Read 4707-4917 first; re-scoped the lane to the residue (finding 2). Outcome: right.
- Felt: eureka, the ridge test's path sample at one texel lands on the one-period alias of a 9-px print, so it can
  never be flagged, medium; from `if (n < 2) continue` and segment(). -> Checked CPU-only on the cage's rectangle
  (0.2-0.7 percent) and V3's patch (91-97 percent). Outcome: right.
- Felt: unease, C3 flagged 3.2 percent frame-wide could still be most of the disc, medium; a whole-frame share dilutes
  a 300-px disc. -> Dug: the region-restricted run (7.8 percent of the disc at margin 0.3). Found: the disc is mostly
  unflagged and 67 percent confidently a period or two out. Outcome: right.
- Felt: push, proposals 1-4a are all measurements, low; the lane was asked for mechanisms. -> Kept them, since each
  decides whether proposal 5 is worth an hour; said so under "loops of a kind".

## Verdicts

**Reasoned.** The periodic family's chain is not missing a mechanism; it is missing eyesight in one band. V3 (P=24)
is solved by the carry at every phase [R]; the weave (P=14-28) by the adoption and the lattice [R]; the frame-filling
print by the cut fix [R]; L7 (P=16) by the held trust gate [R]. Every one reads its "this is a print" signal from the
1/8 basins pass, whose ridge test cannot flag a period under about 16 px [R code; M on C1 and C3]. The cage family
(P=9: C1, C2, C3, the railing) therefore stopped at the 09-21 switches, and C3 has had no candidate since. The next
steps are measurements of one to four GPU minutes each, and each decides a build. The one build worth an hour is a
1-D rival search along the stripe normal at the quarter level, feeding the carry and the zero descent's competition;
its prediction is C3 22.7 -> 25-27 and nothing else moving. No [M] beyond the two flag shares.

**Gut.** Satisfying on the map, suspicious on C3: the variational iterations erased the weave's quarter-level truth
once and may erase this one. What settles it: `flowtap.py` on C3 after proposal 5's pick, before its ladder run.
