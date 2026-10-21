# Judge's notes, lane by lane (Claude, the coordinator; 2026-10-21 evening)

Written as each lane lands, before the contraction. One block per lane: its headline, what I checked myself, what I
doubt, and where it collides with another lane. The ranked list comes after all nine.

## instruments (landed 21:38)
- Headline [M by the lane, CPU]: the whole-frame mean dilutes a region-confined defect by 15-25 dB on 22 of 42 cases;
  edgeerror/bandmetric/cage.sh's crop exist and feed nothing the gate runs. `(n-1)%5` right only for 24->60.
- Checked: bench.sh does score after `format=yuv420p` and analyze.py parses psnr_y only (I read both tonight). Agree.
- Doubt: the "+-0.05 on L0 is dither wander" is [J]; plausible, untested. Fine as a note.
- Proposals 1-2 are zero-GPU and hour-scale: a region column from the analytic mask, a min-frame column. These are
  instrument-before-science and precede any shader measurement from the other lanes. Proposal 4 (the sensitivity
  matrix, 72 GPU min) is the standing instrument the 09-10 ablation decision asked for.

## real-and-field (landed 21:39)
- Headline [R]: every real-footage number is a whole-frame mean over a few fixed 3 s segments, no frozen results file;
  would have caught none of the four eye-found defects. Corrects my brief: the weave was found on synthetic masters,
  never yet on real footage.
- Collides with instruments on the region/min statistic: the same instrument, real side. Merge.
- The turntable (known rpm, decimated by integer factors, numbers only) is the first real derivative of any order and
  a clean kill test for the quint's jerk. It needs Gareth's camera: DECISION/ACT OWED.
- NAS mount owed for the sandstone/railing film and the standard clips.

## wildcard (landed 21:40)
- Headline [J + CPU toy]: the weave comb is two mechanisms; (a) the sampler comb (both frames point-decimated on one
  fixed grid) is cured by fetching B at the candidate's exact phase from a finer level; (b) the print's d vs d+kP
  ambiguity is irreducible locally.
- Its hand-off answered by me (21:44): bidirectional-interpolation.glsl lines 78-90 build LUMA_*_S by one point sample
  per texel; sad5x5_s (line ~196) samples LUMA_B_S_tex(uv_b + o) from the stored level. The shader does NOT fetch at
  the candidate's phase. Proposal 1 is untried and is not the refuted prefilter.
- Doubt: the toy is 1-D with a 64-texel SAD; the shader's coarse window is 3x3 (COARSE_WINDOW_RADIUS 1). Cost: a 1/16
  pass fetching 9 taps per candidate from the full-res or 1/8 luma; bandwidth, not dispatches. Prediction on M1 is
  bold (28-31 -> within 5 dB of 46.9): a sharp kill test.
- The PIV peak ratio Q as the per-level trust input collides with the periodic lane's HELD trust gate: wait for it.
- The sceptic's question (per-texel uncertainty and resolution as a pair) is the field lane's gap 4; fold in.

## reach (landed 21:44)
- Diagnosis [R + CPU emulation]: the cliff is a constant (0.75 x 1.9375 coarse texels = 23.25 px) opened at the 1/16
  descent, SEALED by the 1/8 prior SEED_MAG_LAMBDA centred on zero (the larger term), finished by PROP_DISAGREE
  zeroing. Corrects my brief: on bodies the energy channel already moved the cliff (24 -> 36+), so "unbuilt" was
  stale for that half; nothing local exists for the pan in the picture tiers.
- The cheapest discriminating experiment is a 15 GPU min run (prior re-centred only, pan.sh W3 + limb K1-K3) with a
  written decision rule. This is the model of what I asked for.
- Collides with wildcard proposal 1 on the coarse level: different mechanisms (prior vs sampler comb); both can be
  gated on W3 and M1 in one queue. Hand-off to the ladder lane: W3's 4 px cells are grid-aligned (36 reads exact for 37).

## periodic-alias (landed 21:50)
- Corrects my brief: the quarter-level carry's GLSL form IS built (ALIAS_CARRY builds 1-6, in High and Standard);
  what is unbuilt is a quarter-level rival SEARCH. I wrote "never built" from memory; [U] that became wrong. Noted.
- Headline [R code + M CPU]: one gate (ALIAS_E_M_ST, the 1/8 margins) feeds every switch after the cage, and its
  ridge test needs the rival >= 2 texels (16 px) away, so a 9 px print can never be flagged: C1 flagged 0.2-0.7% of
  its rectangle, C3 1.6-7.8%, V3 90-97%. C3 has been untouched BY CONSTRUCTION since 09-21, and the shipped tiers were
  never scored on C1-C3 or the railing. This is the cheapest important finding so far: proposal 1 is 4-5 GPU min, no
  code, with a kill test (>1 dB move kills the map).
- C3 at 1/8 is a confident lock (the weave's anatomy), not V3's tie: a tie-breaker is the wrong tool. Agrees with the
  wildcard's split of the comb into two mechanisms. The ALIAS_Q1D rival search (its leap) and the wildcard's
  phase-exact fetch attack different halves; both gate on C3/M1.
- The HELD trust gate: resolve the one Sonic run first (1 GPU min dump), do not retire. Collides with the wildcard's
  PIV Q as the trust input: Q would be a different pick statistic; queue after 4a.
- The undecidable case D1 built as a speed ramp: 1 h + 4 GPU min; turns an assumption into a knee.

## ladder-audit (landed 21:58)
- Gareth's instinct about the early synthetic cases was right, twice over.
- Finding 2 [M by the lane, CPU, numpy model validated on hold V2/V3 to the hundredth]: V2, V3, H2 carry a 30.66 dB
  CEILING in their ground truth: TEX_V2/TEX_H2 use gt(sin(),0), a hard threshold, so at the 60 fps truth frames the
  bar edges snap to whole rows (a CPU render of V2 frame 2 shows two levels only). A bilinear warp can average at
  most 30.66 over the scored frames; the rec reads 29.02/28.64, the cage's V3 27.4, the carry's 28.6: every V2/V3/H2
  delta since 09-06 was compressed against a wall. scenecheck.sh cannot see it (coincident frames are integer). The
  P-series is clean. TIER 2: this changes the headline of the alias work; I verify the carrying step myself before
  the record changes (a CPU render of V2 at 60 fps and its level count; the 30.66 bound recomputed).
- Finding 3 [M on the saved gate logs]: whole-frame PSNR carries a size bonus (+19.6 dB for a 100x100 box, +10 for
  300x300); dividing it out, the binding set goes 8 -> 29 cases and the RANKING FLIPS (on-object: high 32.54 > quad
  32.21 > rec 31.52). The lane's own gut: suspicious until a crop-scored run confirms. Agrees with instruments
  (dilution) from the truth side. The crop-scored bench run is the confirmation: GPU, 4 shaders, ~25 min.
- Finding 1: the capped mean is decided by 8 cases, several of them one mechanism twice. Finding 4: all four textured
  translations run at 16 px/f, the pyramid's one immune speed (the comb at 10/12 is the record's own "not done").
- Verdicts: keep 27, merge 4, retune 6, wrong-name 2, retire none; everything built beside the frozen 42.
- Proposals P1 (exact-coverage stairs, ~2 GPU min) and P2 (the speed comb) are cheap and decisive; P3 is the
  instruments lane's region column from the truth side (merge); P7 a LADDER2 group never merged into one mean.
- DECISION OWED: whether frozen V2/V3/H2 stay in the capped mean once the retunes exist.

## record-map (landed 22:00)
- The draft map exists: 240 dated entries with status, number and pointer, 322 lines. Tier 1 for the shipped and
  refuted sections (mechanical, with pointers); the lead-4 lines are heading-level and get a spot-check against
  `grep -n -i 'MISSED\|REFUTED' ENERGY-TRANSFER.md` before it enters the repo.
- Finding 1 [R]: the 2026-09-10 ruling "the family is not rebuilt" is NOT in the repository; it lives in Claude's
  memory and in my brief. G6.4 (procedures and rulings live in shared files) was broken here; a fresh reader would
  propose a rebuild. Fix: the ruling, with its three measured reasons, goes into NFRAME-LIMITS (or the map) with its
  date. Gareth's words are in memory (project_nframe_limits): quote them.
- Finding 2 [M]: SHADERS.md's pass counts are stale by two in every file since REPAIRS L1/L2. Mechanical fix.
- Finding 3 [R]: the record contradicts itself on the trust gate (two status headers say "never built"; the 10-01
  evening entries say built, gated, HELD). Under G7.10 this is reconciled in the same session the map lands: the
  headers get a dated SUPERSEDED line.
- Findings 4-9: Low tier named two ways in SHADERS.md; two Arc run times; README's M5 row stale (my own update tonight
  missed README and BUILDANDUSAGE line 353); HANDOVER's bases list; QUINT's ambiguous sentence. All mechanical.
- Its five leads overlap the other lanes' (L10, L8, the Sonic run, L7, the comb): convergence from an independent
  reader is evidence the ranking is right.
- TIER-2 CHECK DONE (22:10, Claude, independent numpy model from the scene expression): a bilinear warp of the exact
  source against the gt()-thresholded truth, V2, 35 scored frames: mean 28.57 dB (min 24.1, max 34.0); the lane's
  30.66 (25.5, 37.4). Two models, ~2 dB apart in the number, the same wall; the rec's V2 29.02 / H2 28.64 sit on it.
  Control: the same warp on a soft (sin) texture scores 52.65. The finding STANDS; the exact ceiling is to be taken
  from a real render (P1's V2x beside V2), not from either model.

## mathematics (landed 22:14)
- Finding 1 [M from tonight's own gate logs]: the base is NOT time-symmetric by output phase: on L1 every interior
  frame at t = 0.2 and 0.6 is at the ~80 dB ceiling while t = 0.4 reads 46.3 and 0.8 reads 49.1; L2 47.0/39.7/40.8/41.9
  by phase; linear symmetric to 0.01. So L1's 61.92 is an average of exact and lattice-error phases. Mechanism
  conjectured (the L4 lattice fraction against the quarter-texel flow read), not shown. P1 is free (split the saved
  logs) plus 10 s of GPU. Collides with the ladder lane's per-phase profile proposal and the instruments' min column:
  one tool, three lanes asked for it. BUILD IT FIRST (zero GPU).
- Finding 8 [M]: frames 59-60 of every case are hold/linear frames (the window's end: the hook does not fire and the
  builtin mixer answers) and analyze.py has no end-of-clip skip: L1's mean drops ~1.3 dB from them. A scoring defect in
  the ladder's own instrument, cheap to confirm from the gate logs and cheap to fix (an end skip beside SKIP_STARTUP).
  The ladder lane's "window-edge frames are a third of a six-frame shader's scored outputs" is the same thing.
- Finding 2 [M]: BIDIRECTIONAL-AS-MATHEMATICS.md section 12.6 has the B-side error term wrong (-t(1-t)(grad f)f, not
  (1-t)^2); document-only. Finding 3 [R]: every //!SAVE is fp16, the STORAGE caches rgba32f; SUBPEL_REFINE flows are
  rounded to 1/64-1/32 px in FLOW_H_AB itself, one hop before L10's readback floor: the floor is TWO stages, not one.
  Finding 6 [R]: at 1080p the S level has 68 rows (15.88 px pitch) and the seed's x2 overstates vertical motion by
  0.74%; invisible at 720p. Finding 5: NaN-clean by construction. Finding 9 [U]: subTexelPrecisionBits, seconds to query.
- The lane did what was asked: checks that can fail, no rewrite. Its six discrepancies are mechanical fixes to the
  mathematics document.
- CONFIRMED BY ME (22:18, from tonight's gate logs, the recommendation): frames 59 and 60 read identical for rec,
  hold and linear on every case checked (L1: 36.63 / 31.30; L2: 33.13 / 28.25): the window's end falls through to the
  builtin mixer and analyze.py scores it under the shader's name. L1 65.69 -> 67.20 and L2 50.12 -> 51.05 with those
  two skipped. Every ladder number carries this; it dilutes every shader toward hold by about a dB on the clean cases.
  The phase asymmetry is confirmed on the recommendation too: L1 by phase t = 0.4/0.8/0.2/0.6 reads 70.95/64.10/
  70.36/63.32; L2 51.24/43.32/66.33/44.06. (The lane's figures were the base's; the pattern differs, the asymmetry
  does not.) Both are instrument facts, zero GPU to fix, and both precede any new science.

## cost (landed 22:20)
- Headline [M, CPU dataflow over 950 passes]: L7 undercounts the dead B->A chain 6-8x, and dead_passes.py (SAVE/BIND
  only, blind to storage images) would cut two LIVE passes (ALIAS_E_AB/ALIAS_Q_AB imageStore what the live 1/8 refines
  read). The silent-failure catalogue gains a shape: a liveness tool blind to the project's own cross-pass channel.
- Dead at read_view 0: rec 17 of 52 whole passes (35% of dispatches), Low 17/53, Standard 24/80, High 17/92, base
  6/22, N-frame 0. 14-15 of them recompute every output frame (no pair_changed cache). 0.29-0.31 ms/dispatch tonight.
- Proposal 1 (dataflow prune as gen_variational's last step; byte-identical; rec -28%, High -17%; kill: any differing
  frame, identity on the Arc with a warm-up first, or <10% fall) is the highest-certainty return of the night, and
  the most dangerous if the liveness is wrong: the identity check IS the gate, frame by frame, all 42 cases.
- Confirms [R]: libplacebo skips //!WHEN passes before building, so the reading tail is free at read_view 0 (the
  record's open question). SAVE textures fp16, caches rgba32f: caching is byte-identical, moving SAVE->storage is not.
- The leap (pair_changed as a WHEN variable, skipping cached dispatches on 60% of 24->60 frames) is a patch change
  and bounded-not-identical: DECISION OWED.
- Hand-off: SHADERS.md pass table stale by two (record-map lane found the same independently).

## GPU item 3 landed (21:52): the shipped tiers on the cage cases (cage.sh, the cage's own rectangle)
| case | rec | Low (-cut) | Standard (adopt-cut) | High (lattice-cut) | hold | linear | the 09-21 three-switch file |
| C1 | 24.93 | 24.93 | 34.88 | 34.88 | 30.99 | 43.20 | 34.6 |
| C2 | 25.47 | 25.47 | 31.78 | 31.78 | 30.01 | 34.06 | 31.6 |
| C3 | 21.82 | 21.82 | 23.20 | 23.24 | 24.41 | 28.94 | 22.7 |
Prediction held (every tier within 1 dB of the three-switch file: +0.3 / +0.2 / +0.5): the energy, carry, adoption,
lattice and cut switches do nothing for 9 px prints, as the gate finding says. Plainly: the Low tier IS the plain
recommendation on these (the cut gate never fires); on C3 every shipped tier is below hold and 5.7 dB below linear;
on C1 the best tier is 8.3 dB below the blend. The whole-frame column (High 40.83 on C1) dilutes the rectangle's 34.88
by 6 dB: the instruments finding, live. (The -global-cage row is missing from cage.sh's table though it rendered ok:
check the table's label handling.)
