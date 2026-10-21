# Lane reach: the cliff is opened by the 1/16 descent's 1.45-texel reach and SEALED by the 1/8 level's zero-centred prior; a local centre for that prior is the cheapest local reach, and an offline emulator already separates the two leading designs

## What I read

- `NFRAME-LIMITS.md`: the fast pan (3785-3863), the global-motion seed (3865-3960), the cage's field read (3995-4010), the
  field on real bodies, velocity and the cliff (4200-4260), the limb K1-K3 and its two mechanisms, EDGE_PROP, the energy
  channel in both forms (4336-4420), V3/B1 and the global shift's wrong pick (4670-4700), the energy channel on rendered
  children and build 6 (4830-4890), section 8 the prefilter (545-600), the seed history (860-930), the zero seed (1350-1390),
  the alias behind the fast end (2725-2740), the per-level view's first use (3415-3440). The refuted list (`grep -i refuted`).
- `BIDIRECTIONAL-AS-MATHEMATICS.md` §5 (208-266) and §12.4 (668-706).
- `shaders/bidirectional-interpolation.glsl` 70-100, 158-345, 486-640; `shaders/bidirectional-interpolation-variational-propagated.glsl`
  130-200, 640-730, 917-1062, 1280-1300, 1500-1630 (the fused coarse pass, the 1/8 arbitration, the three-way check).
- `tests/gen_variational.py` 1-240, 536-700 (`add_global_seed`); `tests/trust_gate.py` header; `tests/scenes.sh` 200-212, 525-570;
  `tests/probes/limb/PREDICTION.md`, `limb.sh`, `limblevels.py` header; `tests/probes/pan/pan.sh`; `tests/probes/weird/levels.py` header.
- `PRIOR-ART.md` 318-385 (warnings, what not to import), 519-600 and 631-690 (the lead-4 sweep on large displacement).
- `ENERGY-TRANSFER.md` 3405-3460, 3805-3850 (the trust gate), and the MISSED entries at 676-684, 795-802, 2109-2125.
- `REPAIRS.md` 76-132; `SHADERS.md` 251-330, 553-645, 1680-1695; `THREEDIMENSIONAL.md` 9.8 (916-975); `INSTINCT-STRATEGY.md` 1-130.
- Not read: `ENERGY-TRANSFER.md`'s weave, adoption and lattice work beyond the lines above; `tests/TESTING.md` beyond two
  tables; the Metal side; the propagation passes' bodies (their rule is in the record).

No GPU was used. One CPU-only numpy emulation was run (`~/Developer/np-scratch/swarm-20261021/reach/w3levels.py`,
`descent.py`, `capprior.py`); its claims are marked [M-emu] and carry the caveats in finding 7.

## Findings

**1. The 24-px cliff is a constant, not a phenomenon.** [R] The coarse descent is five rounds of an eight-neighbour step
search with the step halving from 0.75 texel; its reach is 0.75 x 1.9375 = 1.453 coarse texels = 23.25 px at 1080p
(`BIDIRECTIONAL-AS-MATHEMATICS.md` §5 258-259; the shader's own comment at `bidirectional-interpolation.glsl` 314-327 says
"0.75 caps full-res reach at ~23px", chosen against a false long-reach match on a backlit hair edge). L3 is named "the search
ceiling" and L4 "beyond it" in `scenes.sh` 200-201. The party's cliff "starts at 24 px/frame" (4225) and the forearm share
is counted "over 24" (4240). [J] The number the record keeps rediscovering on walls and bodies is this one constant.

**2. The reach alone does not make the W3 collapse; the alias and the 1/8 prior do.** [R] Doubling the first step moved
W3's collapse only 34 -> 37 px (3841-3848); the global seed alone (a correct coarse candidate at every texel) lifted 36-41
px from 17.6 to only 18.2, and re-centring the 1/8 prior `SEED_MAG_LAMBDA * |flow|` on the frame's shift took it to 22.5
(3877-3897). The prior is 0.3 per 1/8 texel (`...-variational-propagated.glsl` 937); at 4.6 texels it costs 1.39, "the size
of the whole SAD of a good match" (3880-3882). [M-emu] On W3's texture at the 1/8 level the 3x3 SAD at the truth is 0.49 and at
zero 1.36 (v = 37 px): the gap, 0.87, is smaller than the prior's 1.39, so a correct far candidate loses to zero on the
score even when it is in the set. Emulated: with the shipped descents the temporal seed holds 63-80% of coarse texels on the
truth at 32-40 px, and the 1/8 pick keeps 11-18% of them; with the prior centred on the truth the same candidates give
93-100% (`descent.py`, tables below).

**3. The three-way check turns "wrong" into "zero".** [R] After propagation, where the propagated and raw flows differ by
more than max(1.5 texels, 0.5 x |raw|) and neither is proven, the texel is set to zero ("an alias suspect and a blend
(zero) beats trusting it", `...-variational-propagated.glsl` 1509-1620, `PROP_DISAGREE`). [J] That branch is what paints the
record's signature, "a growing share snaps to near zero" (4227, 4324), on a fast region whose 5x5 neighbourhood is a still
background: the still texels' zeros win the contrast-weighted mean (finding 2 of the limb, 4356-4360), the raw flow disagrees,
and the rule zeroes it. This is the right rule for a period alias and the wrong one for a lone fast object; it has no cue to
tell them apart.

**4. The body cliff has two parts, and one is already moved.** [R] On K1 the coarse level reads a finely textured limb at
gain 0.26 because one bilinear tap per 16 x 16 footprint scrambles the grain while the still wall matches at zero (4347-4354);
the coarse texture-energy channel lifts that to 0.72 at W 8, and on the party app's rendered children it moves the cliff
"from 24 to past 36 px/frame on bodies, in both rooms" with nothing lost (4836-4862; the 2026-10-01 note at 4251). It ships
in `-energy` and in the player's High tier (SHADERS.md 724, 830). [J] So the prompt's "a LOCAL reach ... unbuilt" is half
stale: the limb's coarse visibility is built. What remains unbuilt for bodies is the prior and check terms (findings 2 and 3),
which the energy channel does not touch, and for the pan nothing local exists at all: the picture recommendation and Low tier
run neither the global seed nor the energy channel.

**5. The energy channel has never been scored on the pan, and the pan has never been read per level.** [R] W2/W3 appear
only in the fast-pan and global-seed entries, read by `read_view 4` (the final field); `levels.py`/`limblevels.py` have
been run on the weird scenes and on K1-K3, never on W1-W3 (grep over NFRAME-LIMITS.md, PROBES.md). [J] Both are
cheap and unrun; they come first (proposal 0).

**6. A local wide search already exists, gated on the wrong cue.** [R] `TRUST_GATE` (trust5) offers the quarter level's
three best minima within +-24 px and lets full resolution decide, but only where the 1/8 level is ambiguous AND aliased (a
print's signature); +1.0 ms a frame on film at 720p; held by the owner's decision (ENERGY-TRANSFER.md 3805-3850;
`tests/trust_gate.py`). [J] Its reach, +-24 px, would not reach 37 px anyway, and its cue never fires on a textured wall or a
limb. It is machinery for a reach switch, not the switch.

**7. The emulator and its limits.** [M-emu] `descent.py` emulates W3's texture (the `geq` formula of `scenes.sh` 540), the
point-sampled pyramid (the mean of the central 2 x 2 pixels of each footprint, as a bilinear tap at the texel centre is), the
three coarse descents with `REG_LAMBDA` 0.06 and the 1e-4 tie margin, the ring rule (>= 0.75 from `off_a`), the 1/8 refine
(+-2 texels, 0.05 per texel) and the score with both priors. It is one-dimensional (the pan's axis only), omits the
propagation passes, gives the temporal seed the previous pair's truth as its start (the best case; in the shader it chains from
the zero descent, 3838-3841), and computes the texture hash in double where ffmpeg uses float. [U] Its cell values therefore
differ from the rendered frames; its structure (three cell sizes at 128/32/4 px, weights 0.25/0.35/0.40) is the same. Share of
interior texels within 0.5 coarse texel (0.75 at 1/8) of the truth / of zero:

    v px   zero descent   ring      temporal   1/8 pick (shipped)   1/8 pick, prior on truth   1/8 pick, prior on own coarse winner (D)
    24     0.51/0.15      0.05/0.67  0.67/0.10  0.62/0.16            1.00/0.00                  0.68/0.13
    28     0.44/0.14      0.07/0.69  0.80/0.03  0.39/0.19            0.96/0.00                  0.66/0.08
    32     0.00/0.16      0.11/0.67  1.00/0.00  0.46/0.19            1.00/0.00                  0.98/0.01
    36     0.00/0.20      0.15/0.56  0.80/0.00  0.14/0.23            0.94/0.00                  0.68/0.06
    38     0.00/0.26      0.09/0.52  0.63/0.00  0.11/0.26            0.93/0.00                  0.50/0.12
    40     0.00/0.20      0.06/0.55  0.67/0.00  0.18/0.25            1.00/0.00                  0.62/0.09

What agrees with the record: the zero descent dies past 28 px (the record's 23-px reach, 3841); the ring seed lands in the
alias basin on the other side and never helps here (its rule excludes the near basin); the final share collapses to 11-18%
past 34 px (the record: 0% at 36-39, 3831; the emulator lacks the check pass that finishes the job). A 1/8 search widened to
+-5 texels from zero WITHOUT re-centring the prior reads 14-31% at 34-40 (`descent.py`, third block): width is not the term.
Capping the prior at half the texel's own zero-SAD (`capprior.py` C) reads 59-62% at 34-38: better than shipped, worse than
a centred prior. (D) in the table is proposal 1's mechanism, emulated.

**8. The ladder's reach cases are not pure reach.** [R] L4 (40 px) scores 30.6-34.6 across hosts and dates (3925; TESTING.md
1706) although 40 px is past 23.25, because the 1/8 refine adds +-16 px (§12.4: total reach 51.25 px) and a bright box on
black has a zero-SAD far above the prior's 1.5. [J] L3/L4 test reach with contrast on the matcher's side; W3 tests it with
contrast against. A local-reach switch must be predicted on both, and the two can move differently.

**9. Prior art, matched to the record.** [R] PRIOR-ART.md 541-600 and 631-690 surveyed: Nam 1995 (K candidates per
level), MRMCS 2001, Chalidabhongse 1997 and Bierling 1988 (spatial, temporal, hierarchical candidates: our three seeds),
the BBC's full-resolution phase-correlation menu (our global seed is its frame-sized cousin), PIV multigrid, Flow Fields,
Brox-Malik, Steinbrücker, DeepMatching; PatchMatch and random search excluded for determinism (373-375); mean pyramids
excluded (676). Of the techniques the prompt lists, the record has tried: deeper reach by step (3841), a frame-level
seed (3865), a per-level trust gate with a wide offer (ENERGY-TRANSFER 3805), neighbours' flows (the propagation, SHADERS.md
320-330), temporal seeding forward (the seeded base) and backward (the foresight seed, SHADERS.md 300-318), and multi-hypothesis
carry (ALIAS_CARRY, PRINT_LATTICE). Not tried: a per-texel candidate SET beyond the ring (a local menu), phase correlation per
block (the BBC's form), a motion-compensated temporal seed (PRIOR-ART 660-664 names it; "not recorded as tried", 672), and
any local centre for the prior.

## Proposals, ranked

**0. Steps first: three diagnostics nobody has run (GPU, about 25 minutes in all; the owner's queue).** Rank 1 by
certainty per cost.
- (a) `limblevels.py`'s dump on W3 (its SHADER argument takes the recommendation; it needs W3's law and a frame-wide box
  instead of the limb's, about 20 lines), at N:N, read at 30, 34, 37 and 40 px: the share near truth / near zero per level
  (S, E raw, E, Q, H). PREDICTION from finding 7: FLOW_S_AB near-truth falls to under 10% past 32 px; FLOW_E_AB_RAW keeps
  under 20%; FLOW_E_AB (after the check) adds the zeros. If instead E raw is right and E is wrong, the check pass (finding
  3) is the term and proposal 3 moves to the top. If S is right past 32, finding 1 is wrong for W3.
- (b) `pan.sh` on W3 with `-energy` and `-global-cage-energy` beside the recommendation. [KILLED 2026-10-21, measured
  +2.63 at 36-41 and +6.32 at 28-32: see `reach-addendum.md` beside this file for the absorbed diagnosis and the rewritten
  decision rule.] PREDICTION as written: the energy
  channel moves W3's 36-41 band by under 1 dB (the wall's energy is uniform; the record's own E4 reasoning at
  PREDICTION.md); `-global-cage-energy` reads within 1 dB of `-global`. A W3 gain of 2 dB or more from energy alone
  kills finding 2's claim that the pan's cliff is alias plus prior and not visibility.
- (c) `leveltap.py` (tests/probes/trust/) already taps "the 1/8 level's two basins and margin" on the High tier; pointed at
  W3 at 37 px it reads the SAD at the chosen and the true candidate and the prior each paid. PREDICTION: at the true candidate
  SAD 0.4-0.6 and prior 1.3-1.5; at the chosen one SAD 1.2-1.4 and prior under 0.3. This is the measured form of the
  emulator's central number and decides between proposals 1 and 2 before either is written.

**1. `LOCAL_CENTRE=1`: the 1/8 prior measured from a local reference, not from zero.** Rank 2.
- Mechanism: in the 1/8 arbitration, `SEED_MAG_LAMBDA * |ref - c|` with c the texel's own best coarse candidate by raw SAD
  (`cost_a/b/c`, already computed in the fused coarse pass and discardable today), used only where that candidate is more
  than 1.5 coarse texels from zero (the global seed's fade, made per texel) and its 3 x 3 coarse neighbours' winners agree
  with it within a texel; elsewhere c = 0 and every term is byte-identical. With `GLOBAL_SEED=1` on, c is the frame's shift
  where it is non-zero and the local centre where it is zero: the frame first, the region second.
- Nearest prior attempt: the global seed's re-centring (3877-3884), which is this with one centre for the whole frame and
  cannot see a lone mover (4231). EDGE_PROP (4367) weighted neighbours by agreement in the propagation; this touches the
  prior, not the mean, and is gated on distance from zero, so the period family's small motions (0.4-1.5 texels) never open it.
- PREDICTION: W3 36-41 px 17.6 -> 20-22 dB (emulated share 50-70% against 11-18%; the -global's frame centre reads 22.5), 32-36
  20.3 -> 24-26, under 28 px within 0.5 dB. K2 (dark wall) holds past 42 px (the prior was the only term there, 4382); K1 moves
  under 1 dB alone (the coarse scramble, finding 4) and 2-3 dB with `-energy`. L4 +0.5 to +1.5 (the far candidate pays no prior),
  L3 within 0.3. Ladder: P1-P5, V1-V3, H1-H2 within 0.3 (gated shut: their motions are inside 1.5 texels); A4-A7 are the risk
  (lattice motions near 1.5-2 texels where a coherent wrong coarse winner would centre the prior on an alias).
- KILL: any period or lattice case down more than 1.0 dB, or the capped mean down more than 0.15 (the trade the global seed
  showed, 3936-3945, is the floor to beat). Confirms: W3 36-41 up 2 dB or more with the ladder within 0.15. Inconclusive
  (W3 +1, ladder flat) tips toward proposal 2: the candidate set, not the prior, is then the limit.
- COST: 0 dispatches (the coarse pass stores c in a free `.zw`; the 1/8 pass reads 9 texels of the coarse cache); about 2% of
  shader time. An hour of generator; 6 minutes a ladder run; `pan.sh` and `limb.sh` 10 minutes more.

**2. `REACH_SEED=1`: a per-texel far menu as a fourth coarse descent and fifth 1/8 candidate.** Rank 3 (same kind as the
global seed: a candidate; it differs from proposal 1 in kind).
- Mechanism: before the descents, score 8 far starts per texel at radius 2.5 coarse texels (the 1-ring is already the ring
  seed; 2.5 sits past the 2-texel alias of a 32-px grain and inside the 1/8 level's reach from a 3-texel seed), take the
  cheapest, descend from it as `off_d`, carry it as the global seed's `off_g` is carried (`add_global_seed` 650-690 is the
  template: the fifth candidate, `base_off4`). Admit it at 1/8 only where the texel's zero descent ended with SAD above
  0.6 of its own contrast range (the reach cue: a bad best match on a textured texel), and only together with proposal 1's
  centre, or it dies at the prior (finding 7: width without centring 14-31%).
- Nearest prior attempt: the doubled first step (3841-3848), which is a longer walk from the same start and stopped at the
  alias; the trust gate's +-24 px offer (finding 6), gated on a print's signature. This starts past the alias and is gated on
  a bad match.
- PREDICTION: on W3 adds 1-2 dB over proposal 1 at 36-41 px (the temporal seed's near-truth start is not available in the
  shader, so a fresh far start is what finds 2.3 texels); K1 and K3 past 42 px up 1-2 dB where the energy channel sees the
  limb; L4 +1 to +2 (a 40-px box is 2.5 texels: the menu's own radius); L3 unchanged; M1/M2/L7 the risk (a far start on a
  fine texture finds a Moire copy; the cue must refuse it: their zero-descent SAD is low at integer speeds).
- KILL: M1, M2 or L7 down more than 0.5 dB; L0_static not bit-identical. Confirms: L4 up 1 dB and W3 36-41 up 1 dB over
  proposal 1 alone. Inconclusive tips toward leaving it out: the candidate was present (the temporal seed) in the emulation
  and the prior decided.
- COST: 0 dispatches (inside the fused coarse pass and the existing 1/8 pass); 8 SADs plus one descent per coarse texel,
  about the global seed's +3.8% of time (3952-3955). Two hours of generator.

**3. `CHECK_EVIDENCE=1`: the three-way check's disagreement branch asks the data before zeroing.** Rank 4 (a gate, a
different kind from 1 and 2).
- Mechanism: in the `textured` branch where `|prop - raw| > max(1.5, 0.5|raw|)`, return zero only if `s_zero <= 1.1 *
  min(s_raw, s_prop)`; otherwise return the lower of raw and prop. A texel whose frames plainly differ keeps a flow.
- Nearest prior attempt: EDGE_PROP (refuted, 4367-4374) changed the mean's weights; the refuted agreement blend (4031) blended
  where the frames AGREE. This changes neither; it asks, in the one branch that writes zero, whether zero matches at all.
- PREDICTION: K1 and K3 in the 24-36 px band +1 to +2 dB (the limb's edge texels keep their raw flow instead of the wall's
  zero); W3 under 0.5 dB (its collapse is upstream); L9 occlusion and the E-series the risk (a disoccluded texel has no match,
  and zero is the right blend there); the period family within 0.3 (an alias's zero-SAD is not low, so the branch still
  zeroes on a real alias suspect only where zero is a fair match, which is exactly where the blend was right).
- KILL: L9 down more than 0.5 or any period case down more than 0.5. Confirms: K1 24-36 up 1 dB with the ladder within 0.1.
- COST: 0 dispatches, one extra SAD already computed (`s_zero`). Half an hour.

**4. `-energy` into the Low tier's measurement, not its build.** Rank 5: a measurement that reframes the owner's decision
on bodies. The channel moved the body cliff past 36 on the party bench and is a -0.11 capped trade on the ladder (4388-4393).
The question for the picture is only whether the real-footage rows (4394-4399: level to +0.35) hold on footage with children.
PREDICTION: on the street clip (people against a still street) +0.1 to +0.3 dB. KILL: any clip down 0.2. COST: 15 GPU minutes.

**5. Not proposed, and why.** A 1/32 level: the 32-px grain becomes a 1-texel period (shift-invariant, a constant mess) and a
48-px limb 1.5 texels (invisible); it would need a new refine stage at 1/16 (+2-3 dispatches, 0.6-0.8 ms) to hand down; the
global seed already does its job for pans. Phase correlation per block (the BBC): new FFT machinery, 2+ dispatches, and the
record's reason for the global seed's sparse-grid SAD over a correlation stands. A motion-compensated temporal seed
(PRIOR-ART 660-664): [J] worth a line in the incubator, not a lane; on W3 the temporal chain fails because it starts from the
zero descent (3838-3841), and proposal 1 removes the reason that start was wrong.

## The cheapest experiment that discriminates proposals 1 and 2

Already run, offline: `descent.py` says that with the shipped candidate set a prior centred on the truth keeps 93-100% and
a wider search without re-centring keeps 14-31%; the prior is the first term. The GPU form, before any new search is
written: regenerate the recommendation with ONLY the prior re-centred on the texel's own coarse winner (proposal 1, no new
seed) and run `pan.sh` on W3 and `limb.sh` on K1-K3: 15 minutes. If W3's 36-41 band rises 2 dB or more, build proposal 1
and stop; if it rises under 1 dB while diagnostic 0(a) shows the coarse level right on fewer than a third of texels, the
set is the limit and proposal 2 is needed. Step 0(c) (`leveltap.py` on W3) gives the same answer for the cost of one render.

## Refuted entries checked

- Section 8, the box prefilter (545-600): nothing here filters a level; proposals 1-3 leave every luma tap as it is.
- The tensor fill, `PROP_TENSOR` (2716-2728): not a propagation change.
- The temporal chain from `off_c` as the pan's term (3838-3841): refuted as THE term; proposal 1 addresses the prior that
  made it moot, and does not re-propose it.
- Blending where the frames agree (4031-4043): proposal 3 reads disagreement with the data, not agreement.
- Size as the cause on bodies (4232): not assumed.
- EDGE_PROP (4367-4374; PREDICTION.md): no agreement weight in any mean here; proposal 3 touches only the branch that writes
  zero.
- Energy with a Gaussian footprint and sparse taps (4404-4407): not touched.
- The global shift as a prior on B1 (4680-4700, the Imry-Ma warning): proposal 1's centre is per texel and gated on a
  coherent far winner; the warning is why its KILL is the period and lattice families.
- ENERGY-TRANSFER MISSED: T1 (the true region warp, 680), F1/F2 (the found region, 797-800), Z1 (the zero descent forced
  open, 2109-2125). None is a reach mechanism; Z1's lesson, that a later stage can erase an earlier answer, is why step 0(a)
  reads every level and not the final field.
- PRIOR-ART "not to import" (369-385, 675-690): no random candidates, no averaging of vectors, no full-range search.

## Hand-offs

- For the ladder lane: W3's 4-px noise cells are aligned to the pyramid grid, so at 1/4 a 36-px shift matches a 37-px truth
  exactly (finding 7's emulator; the record's L4 fraction finding, REPAIRS.md 76-96, is the same effect one level down). A
  pan law with a non-integer offset, or a texture whose cells start at an odd pixel, would stop the ladder scoring the lattice.
- For the owner: the body cliff is moved in High and not in Low; whether the picture tiers take `-energy` is a trade he has
  already seen the numbers for (4388-4399). Proposal 1 would be the first reach term that costs no dispatch.
- For whoever runs step 0: the GPU queue rule; `limblevels.py` needs W3's law (`192 t + 192 t^2`) and a frame box.

## Felt

- Felt: surprise, the 2026-10-01 note at 4251 (the energy channel had already moved the body cliff), medium; the prompt's
  framing was older than the record. -> Re-aimed the lane at the pan's cliff, where nothing local exists, and at the prior.
  Outcome: right (findings 2, 4).
- Felt: unease, my emulator's texture arithmetic against ffmpeg's `geq`, medium; double against float, cell values will
  differ. -> Kept the cell sizes and weights, marked the values [U], and used only shares, not absolute dB. Outcome: open.
- Felt: pull, the capped prior (variant C), low; it looked like a one-line fix needing no centre. -> Ran it: 59-62% at 34-38
  px against the centred prior's 68-70%. Outcome: wrong as the leading design, kept as a fallback if the centre's gate
  fails the lattices.
- Felt: unease, the ring seed reading 0.00 near truth at 16 px in the emulation, low; a bug? -> Re-read lines 703-720: the
  ring excludes points within 0.75 of `off_a`, which sits on the truth, so the ring is the OTHER basin by design. Not a bug.
  Outcome: right to check, nothing found.

- Felt: pull, proposal 1 (the local centre) as the cheapest reach, high; built on 2026-10-21 night at the coordinator's
  request. Outcome: WRONG as a candidate (W3 +0.7 / +1.5; the limb 0 on plain, +0.5-0.9 on -energy; P1 -6.8, P5 -3.5); reach-addendum.md section 4.

## Verdicts

Reasoned: the cliff is made in two places that the record has measured separately and never named together. The 1/16
descent's constant reach (1.453 texels) and the 32-px grain's two-texel period leave the true candidate out of the set
past about 24-28 px; and wherever a true far candidate is in the set (the temporal seed, the global seed alone) the 1/8
level's zero-centred prior refuses it, and the check pass writes the refusal as zero. The global seed cured the pan by
re-centring that prior for the whole frame. A local centre for the same prior is the smallest local reach that exists
(zero dispatches, gated shut below 1.5 texels), the offline emulator says it is the larger of the two terms, and three
cheap diagnostics (a per-level read of W3, `-energy` on W3, `leveltap` at 37 px) would confirm the diagnosis before an hour
of generator is spent. Status: the diagnosis is [R] plus [M-emu]; every dB prediction is [J].

Gut: the prior is the door and everyone has been widening the corridor. Confident on the pan; less sure the per-texel
centre survives A4-A7, which is why the lattices are the kill test and the frame centre stays first in the hierarchy.
