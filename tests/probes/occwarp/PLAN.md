# The final warp at moving edges: WARP_VOTE (Local, 2026-11-13)

The owner, 2026-11-13: the main remaining aberrations are "vertical or horizontal bars, or fast pans / quickly
translating faces"; "update and continue the work, particularly looking to update the main high interpolation shader in
Cadence". GPT's block of the same morning (G029-G030, `tests/probes/motionstress/`) built the stress suite and three
experiments; its combined variant failed its own replacement gate. This record continues from it. GPT's files are
read, not edited.

## What was measured before designing anything (2026-11-13, all on the M5)

1. **GPT's numbers reproduce exactly** (`build.py`'s five shader hashes equal GPT's manifest; the 17-case suite's
   High and global-fullres scores equal GPT's saved ones to the last digit).
2. **GPT's global pan witness alone, through the full gate** (it had only been gated in combination): the 45-case
   ladder is bit-identical to High on 30 cases and within 0.014 dB on the other 15; the cage C1-C4 is identical; the
   content test's 40 real windows (`INTERIOR=1`) are unchanged on 37 and move on three anime windows (-0.149, -0.129,
   +0.088 dB; anime class -0.019). So it is safe, and on real footage it does nothing useful: **a CPU replay of its
   acceptance rule on all 1,413 real frame pairs of the content windows accepts none** (real pans leave residuals of
   1 to 15 codes at the best global shift against its 1.5-code line; flat animation fails its 65%-of-taps rule). Its
   gain is real on the two synthetic pans (+8.24, +5.17 dB) and confined to them.
3. **High on real pans is not broken on average.** By pan speed, on the 348 real pairs where one global shift
   explains over half the frame difference, High beats a blend by +13.7 dB (4-12 px a half-rate frame, at 1920 wide),
   +8.6 to +8.8 (24-48 px), +6.3 to +8.2 (48-128 px). What fails is the first pair of a pan (the previous-pair
   agreement gate needs two) and cartoon pans drawn with uneven steps (13 px, then 68: the same gate refuses them).
   So the owner's defect on live action is local, at moving things, and averages hide it.
4. **What the defect looks like** (GPT's photographic plane, viewed: truth / High / combined): High draws a ring about
   15 px wide around the moving head in which the background is dragged and smeared, a ghost bulge at the leading
   edge, and a doubled ear. GPT's inverse transport sharpens the interior and leaves the ring, with jagged fragments
   on it.
5. **A CPU replay of the final pass on High's own flow fields** (`flowdump.py` writes the half-resolution A -> B and
   B -> A fields as the final pass reads them, calibrated: a static scene reads 0.002 px, the fast face 31.2 against
   32; `warpsim.py` replays the shipped final pass to 0.09-0.12 codes RMS of High's real render, worst frame). On the
   fast face the flow of each frame is right inside the face ON THAT FRAME'S GRID and fattened about 30 px on the
   leading side in A and the trailing side in B. Reading A's flow at the output pixel therefore takes the background's
   vector for the face's leading band (the bulge) and a smooth patch's vector for a feature that has moved onto it.

## The change: `WARP_VOTE=1` (`tests/warp_vote.py`, a switch of `gen_variational.py`)

Four candidate vectors at each output pixel: High's own c0 = F_A(p); B's opinion c1 = -F_B(p); and the two gathered
vectors c2 = F_A(p - t c0), c3 = -F_B(p + (1-t) c1) (c2 is GPT's inverse step). Each is scored by the mean absolute
difference of the two endpoints it implies over a 3 x 3 full-resolution patch (global gain out of B, matching only).
The best replaces c0 only where its cost is under half of c0's (fading in from one half to one quarter) AND lower by
more than 2 codes (fading in to 4); the two pictures are blended, never the vectors. Where all candidates are within
0.5 px of c0 nothing is computed and the output is High's bit for bit. The constants were fixed before the first
replay and not changed after it. It keeps High's half-resolution B -> A chain alive (86 -> 103 passes).

What was tried on the CPU replay and left out, with the numbers (fast face; High ROI 29.72 / feature 36.36 dB):
the vote with c1-c3 gives 32.38 / 38.66; adding a zero vector, or the flows 24 px away in four directions (to reach
beyond the fattened rim), raises the ROI a little (32.54) and LOWERS the features (35.85): zero matches smooth skin as
well as the truth does. They are not in the build. An earlier idea (validate each endpoint by its own frame's flow,
two-sided before one-sided) reaches 39 dB with true flows and 30.35 with real ones (the fattened flow validates
itself), and is not built.

**What it cannot do, known before the run:** background uncovered behind a moving object is in one frame only, so no
candidate's endpoints agree there and High's smear stays (the trailing ring; about 26 px at t = 0.8 on the fast
face). The record's three earlier occlusion fallbacks (the final pass's own NO OCCLUSION FALLBACK note) died on
exactly that region, by substituting unwarped frames; this change substitutes nothing and leaves that region alone.
A periodic alias a period out ties with the truth and never wins or loses. Bars are not addressed.

## Tests, registered before the first GPU run of the vote (2026-11-13)

CPU design used face_fast, face_counterpan and face_slow only. **Holdouts** (never replayed): photo_fast,
photo_counterpan, face_occluded, face_lowcontrast, every pan and bar case, the ladder, the cage, real footage.

- **V1, the suite** (GPT's 17 cases and scorer): face_fast ROI +2.0 dB or more and feature +1.5 or more (replay: +2.66,
  +2.30); face_counterpan ROI +1.0, feature +5 (replay: +1.41, +7.98); no case's ROI or feature score down more than
  0.5 dB (GPT's line); the two static controls bit-identical. KILL if face_fast gains under 1 dB ROI.
- **V2, the photographs** (GPT's two cases; holdouts): ROI up 1 dB or more on both. And **the visual gate GPT's
  combined failed**: the worst-feature frames (14 and 7) viewed as truth / High / vote: no new fragments on the
  silhouette that High does not have. A failure here kills the replacement whatever the scores.
- **V3, the ladder** (45 cases, fresh High in the same sitting): no case down more than 0.1 dB, whole clip and
  interior (GPT's replacement line, kept); capped headline mean not down more than 0.05.
- **V4, the cage** C1-C4: none down more than 0.5 dB on the cage's rectangle.
- **V5, real footage**: the content test's 40 windows (`INTERIOR=1`): no class down more than 0.05 dB; predicted up
  0.02 to 0.2 on film, television and CG (moving people), within 0.03 on animation.
- **V6, time coherence**: on face_fast and photo_fast, the mean absolute frame-to-frame change of the ROI error not
  above High's (the old fallback's snap showed as a spike there; replay: 1.22 -> 0.64).
- **V7, cost**: frame time against High (file source, interleaved, one process), reported; and the Metal graph
  compiles (`gen_metal.py --compile`).

Adoption into Cadence's High follows only if V1-V6 pass; the graphs are then rebuilt and the app's tests run, the
upload left to the owner.

## The first form's results (12:40): KILLED by the cage, with the largest real-footage gain High has had

Fresh High in the same sitting; `~/np-scratch-int/motion-20261113`.

| test | result | verdict |
|---|---|---|
| V1 suite | face_fast ROI +2.65, feature +2.28; face_counterpan +1.43, +6.56 (the replay had said +2.66/+2.30, +1.41/+7.98); face_occluded +0.71; **bars_h24 feature -0.63** (ROI -0.31); statics identical | faces PASS; the 0.5 dB line MISSED on one bars case |
| V2 photographs | ROI +4.68 and +2.96, features +12.3 and +14.1 | scores PASS; **visual gate FAILS**: the interior is repaired, the ring stays and its edges carry small ragged fragments High's ring does not have (fewer than GPT's combined) |
| V3 ladder | no case down 0.1 dB on either reading (worst O3 -0.053); **L2 +10.4, L3 +7.0, L6 +6.1, L8 +5.6, L4 +3.9** (the object-edge losses High had against its own plain base); raw mean +1.53, capped +0.001 | PASS |
| V4 cage | **C1 -1.24** on the cage's rectangle (C2 -0.46, C3 +0.02, C4 +0.10) | **KILL** |
| V5 real footage | film **+0.300**, television +0.083, anime +0.102, cartoon -0.023, CG +0.154; best segment +1.29 (film1@3055.7), worst -0.11 | PASS |
| V7 cost | 6.78 s against 5.74 (median of three, 180 outputs): **+18%** | reported |

On the cage's thin bars the two frames' opinions differ by a period, and the better-registered of two aliases wins the
vote by the 2x rule although the picture it draws between the frames is a bar's width out.

## The second form, registered before its first run (12:40): the period guard

One addition, in `tests/warp_vote.py`: where the vote would act, each frame is compared with ITSELF displaced by the
difference of the two vectors, and by a half and a third of it. A frame that matches itself under the whole difference
(self-cost under the same kappa of High's cost) but not under the half or the third (larger by twice and by more than
eps) is periodic along that difference, and the vote abstains. A flat patch matches under all three and is left alone.
The constants are the vote's own (kappa 0.5, eps 2 codes); none is new. Tried on the CPU replay first, with one
alternative: the period guard keeps the faces' gain (fast face 32.22 / 38.63 against 32.38 / 38.66; photograph
32.57 / 42.45 against 32.80 / 42.65); requiring each endpoint's own flow to agree with the winner (ownership) loses half
of it (30.4) and is not built.

Tests V1-V7 as registered, the same lines. Predicted: C1 within 0.5 dB of High; bars_h24 within the 0.5 line; the faces
within 0.3 dB of the first form; the ladder's translation gains kept; real footage within 0.05 of the first form.
**The visual gate is at risk**: nothing in this form addresses the ring's ragged edges.

## The second form's result (12:51): the period guard does nothing for the cage; the cause located; the third form registered

**Second form, short gate:** C1 33.69 on the cage's rectangle (first form 33.64, High 34.88): the prediction MISSED and the
period guard is withdrawn. **Located on the CPU replay, against the truth** (the cage's flows dumped, the full final pass
replayed; it reproduces the loss: High 32.43, vote 31.30 on four outputs):
- the harm is entirely at pixels where High's own fallback is OFF (7.5% of the cage: there the picture error triples),
  and the vote helps where the fallback is partly on;
- of the pixels switched there, 7.3% carry 99% of the added error: winners 4 to 10 px from the true vector while
  High's own was within half a pixel. They win because a 3 px patch lets a candidate put BOTH endpoints in the flat gap
  between two bars (cost 2.7 codes) while High's nearly right vector, half a pixel off on a thin bright bar, costs 9.5;
- two guards tried in the replay and dropped: giving High's vector the best of its half-pixel neighbours (cage 31.63),
  and the period guard (31.25);
- **the footprint is the cause**: the same nine taps 3 px apart (a 7 px footprint, wider than the bars' gap) give the
  cage 32.69 (above High's 32.43), taps 4 px apart 32.66, 5 x 5 taps 2 px apart 32.74; the fast face keeps 32.03 / 38.88
  (first form 32.38 / 38.66), the counter-pan face 30.75 / 59.84.

**Third form, registered before its first GPU run:** the first form with the patch's taps 3 px apart (`WV_STEP`); the
period guard removed; nothing else changed. Tests V1-V7, the same lines. Predicted from the replay: C1 within 0.5 dB of
High; face_fast ROI +2.0 or more, feature +2.0 or more; the ladder's translation gains kept; real footage within 0.05
of the first form's (film +0.30). The visual gate on the photographs stays at risk and is judged by viewing.

## The third form's results (13:05): V1-V7 PASS

Fresh High in the same sitting (`~/np-scratch-int/motion-20261113`, labels `high` and `vote3`).

| test | result | verdict |
|---|---|---|
| V1 suite | face_fast ROI **+2.31**, feature **+2.51**; face_counterpan +1.25, +6.97; face_occluded +0.41; face_lowcontrast +0.23; bars_h9 +0.51, bars_v24 +0.32, bars_h24 -0.38 / -0.32 (inside the 0.5 line); no case past the line; statics bit-identical | PASS |
| V2 photographs | ROI **+4.64** and **+2.98**, features +12.5 and +14.2. **Viewed** (truth / High / vote, frames 14 and 7): the interior and the leading side are clean where High smears the nose, mouth and cheek; on the counter-pan (a holdout) the face is sharp where High doubles the eye and mouth. The trailing crescent (background uncovered behind the head) is still there, as registered, and its outer edge has two or three small notches High's smooth ring does not have | PASS, marginal on the visual gate: the notches are flagged for the owner's eye |
| V3 ladder | worst case -0.014 dB (M3); **O3 level** (GPT's combined lost 0.12 there); 36 of 45 cases up more than 0.1: **L2 +11.3, L6 +9.9, L3 +6.6, L8 +6.2, L4 +5.0, M2 +3.8**; raw mean +1.67, capped +0.001 | PASS |
| V4 cage | C1 -0.23, C2 -0.04, C3 +0.03, C4 -0.19 on the cage's rectangle | PASS |
| V5 real footage | film **+0.322**, television +0.072, anime +0.117, cartoon +0.012, CG +0.162 dB; 20 of 40 windows up more than 0.05, 2 down (worst -0.098); best film1@3055.7 +1.33, film5@2103 +0.71 | PASS |
| V6 time coherence | frame-to-frame change of the ROI error, codes: face_fast 1.21 -> 0.65; face_counterpan 1.01 -> 0.82; photo_fast 1.50 -> 0.43; photo_counterpan 1.39 -> 0.60 | PASS |
| V7 cost | 6.29 s against 5.39 (medians of three, 180 outputs, the whole libplacebo pipeline): **+16.7%**; the Metal graph compiles, 103 of 103 passes; scale_shader.py scales the two pixel constants (renamed `WV_STEP_PX`, `WV_SAME_PX` for it; the code is otherwise the gated file's) | reported |

Predictions: C1 within 0.5, PASS (-0.23); face_fast +2.0 / +2.0, PASS; translation gains kept, PASS (larger: L2 +11.3
against the first form's +10.4); real footage within 0.05 of the first form, PASS (film +0.32 against +0.30).

**What it is and is not.** It fixes the leading edge and the interior of fast-moving things (the ghost bulge, doubled
features), which is most of what the ladder's translations and the real windows were losing. It does not touch the
background uncovered behind a moving thing (the trailing crescent stays as High drew it), fast pans the estimator
cannot reach, or bars (bars_h24 is 0.3 dB down, three other bar cases 0.1 to 0.5 up, all at 11-15 dB: still broken).

## The Metal cost stops the third form at the door; the fourth form registered before its first run (13:13)

The third form on the demo's Metal engine (the graphs Cadence would bundle; `QuadDemo`): the gain reproduces (film1@3055.7
27.47 -> 28.24 dB, film5@2103 30.16 -> 30.69; retained frames within 0.05 codes), and **the cost does not fit**:
`--bench`, 24 -> 60, five interleaved rounds on the M5: 1080p 16.89 -> 19.42 ms an output (+14.9%), 4K 37.31 -> 44.64
(+19.6%). High already runs at 59 fps at 1080p on this machine; at 51 fps Cadence's fall-back would step the film down
to Standard, and the owner would lose High to gain the vote. The cost is the 17 passes of the half-resolution B -> A
chain the vote keeps alive, and the scoring of sub-pixel disputes.

**Fourth form** (`tests/warp_vote.py`; nothing else changed):
- B's opinion is read from the QUARTER-resolution B -> A field as it stands before the variational passes (after the
  alias choice, outline adoption and the print's apply), which High already computes for the print lattice. It is a
  candidate, checked against the frames before it is used, so it need not be the refined field. One small copy pass
  gives it a name; the prune then drops the B -> A variational and half-resolution chain as before: 88 passes
  against High's 86 (the third form: 103).
- Candidates within 2 px of High's vector are not scored (`WV_SAME_PX` 0.5 -> 2.0): a dispute under 2 px draws a band
  under 2 px wide, and on the cage 70% of pixels disputed by 0.5 to 2 px.

Tests V1-V7, the same lines, plus **V7 as a gate now: the Metal bench within 5% of High at 1080p and at 4K**. Predicted:
cost +2 to +5%; the faces and the ladder's translations within 0.5 dB of the third form (a coarser B opinion finds the
same vector, less precisely placed at the edge); real footage film +0.2 or more.

## The cheaper forms, and where it rests (13:36)

Metal bench, the M5, 24 -> 60, medians of five interleaved rounds, against the shipped High (16.9 ms an output at
1080p, 59 fps; 37.4 ms at 4K). Short gate (cage, suite, photographs) for each; none was taken to the full gate.

| form | B's opinion | dispute floor | passes | Metal 1080p / 4K | cage C1 (line -0.5) | faces and photographs |
|---|---|---|---|---|---|---|
| **third** | High's half-resolution B -> A field | 0.5 px | 103 | +14.9% / +19.6% | **-0.23** | the registered results above |
| fourth | quarter-resolution field before the variational passes | 2 px | 88 | +4.4% / +9.9% | -0.93 | face_fast +2.65 / +2.38; counter-pan feature +4.16 (under its +5 line); photographs kept |
| 4b | the same | 0.5 px | 88 | +7.4% / +16.7% | -0.95 | kept (counter-pan feature +7.08) |
| fifth | that field refined once at half resolution (the base's refine pass cloned) | 2 px | 89 | +7.6% / +11.7% | -1.40 | face_fast feature +1.82; photographs kept |
| 4c | 4b, abstaining where High's 1/8-level alias detector finds a rival basin | 0.5 px | 88 | not benched | -0.95 | **photographs +0.85 / +0.35**: the detector flags object edges |

Predictions for the fourth form: cost +2 to +5%, PASS at 1080p and MISSED at 4K; quality within 0.5 dB of the third,
MISSED on the cage. For the fifth: MISSED on both. What they show: the vote's scoring costs about 7% at 1080p with the
0.5 px floor and 4% with the 2 px floor; the B -> A chain about 7.5%; raising the floor removes the near-true
candidates that out-vote a look-alike on the cage; and only the fully refined B -> A field keeps the cage inside its
line. A fall-back while playing at 60 fps on this machine would trade High for Standard, so **the vote is not put into
Cadence's High on Local's authority**.

**Where it rests:** the third form is shipped as a VARIANT (the shader-variants rule):
`shaders/…-adopt-lattice-cut-vote.glsl` and its 4K twin, generated by `WARP_VOTE=1`, its code identical to the gated
file; smoke.sh regenerates it with the tiers (19 of 19). The shipped High, the tier recipes and Cadence's graphs are
unchanged. The Metal graphs of the variant compile (103 of 103 passes) and reproduce the gain on the demo's engine
(above). **The owner's decision:** High as it is; the variant as High (devices with headroom, or 2x output, gain; a
60 fps Mac at the edge falls back); or a further cost block (score the vote at half resolution, about a quarter of its
7%; a cheaper refined B -> A field has not been found in four tries).

**Open, measured, not addressed by any form:** background uncovered behind a moving thing (the trailing crescent);
bars (every bar case of GPT's suite is still at 11 to 15 dB); pans the estimator cannot reach (GPT's witness helps two
synthetic ones and no real pair of 1,413).
