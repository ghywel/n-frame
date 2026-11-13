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
