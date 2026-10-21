# Lane cost: the dead B->A chain in the two-frame tiers is 17-25 passes per file, not 1-3; `dead_passes.py` misses it because the fused median binds the twin

No GPU was used. Every number below is from GLSL text, the record, or libplacebo's source. The three tools I wrote are in
`~/Developer/np-scratch/swarm-20261021/cost/` (`census.py`, `live2.py`, `prune_sim.py`, `table.py`,
`table2.py`); they read shader text only and were run CPU-side with the venv's python. There are no [M] claims
tonight; the CPU census results are marked [R] with the tool named, since they are read from the shader text.

## What I read

- `REPAIRS.md` whole (L1-L10, both rounds). `tests/probes/repairs/*` headers; `dead_passes.py` whole; `timepair.sh`,
  `identity.sh`, `compile_all.sh` whole (they are short). `tests/probes/cost/timing.sh` and `tiers.sh` headers.
- `tests/TESTING.md` "Timing basis (2026-09-04)" (L2105-2130).
- `NFRAME-LIMITS.md` L1395-1480 ("Where the time goes", the fusion table and what did not fuse); L1484-1500 (the
  motion-sensitive accident); the 41 "refuted" lines by grep.
- `ENERGY-TRANSFER.md` L3174-3330 (the cost cuts C1-C5, "fewer passes, then FUSION", the fused form's gates, the tiers'
  costs, the cost cap) and L3847-3872 (CUT_MOTION adopted per tier). Headings listed by `grep '^### '`; MISSED lines by grep.
- `SHADERS.md` "Which one to use" (L47-90) and "How each file is made"; the "Caching" paragraph (L1396-1403).
- `shaders/bidirectional-interpolation.glsl`: every `//!` directive (census), L176-265 (the coarse search's cache logic),
  L137-166 (SCENE_DIFF). The High tier: every directive; L5846-5930 (two variational iterations); L6020-6215 (the fused
  median, both second medians); the ALIAS_E_AB pass's storage lines. `bidirectional-interpolation-variational-propagated.glsl`:
  every directive; the storage lines of passes 6-15. `tridirectional-interpolation-propagated.glsl`: the B->A quarter
  refine's seed, the warp's binds and two sampling lines.
- `tests/gen_variational.py` L60-110, L740-870; `gen_quaddirectional.py` and `gen_tridirectional.py` by grep (how they
  find the base's passes). `tests/smoke.sh` L87-192 (the recipes). `tests/gen_metal.py` by grep (WHEN).
- libplacebo at the current pin (`~/np-build/libplacebo/src`): `shaders/custom_mpv.c` L945-950, L1030-1075, L1283-1305,
  L1576-1690; `renderer.c` L436-462, L3668-3680. `frame-mix-hook.patch` by grep (`pair_changed`).
- `INSTINCT-STRATEGY.md` L1-130. `README.md` L1-60. `BRIEF.md`.
- Deliberately not read: `PRIOR-ART.md`, `BIDIRECTIONAL-AS-MATHEMATICS.md`, the ladder's scene definitions, `tests/TOOLS.md`,
  `PROBES.md` beyond its index line, the alias/adopt/lattice generator modules' bodies, any Metal file.

## Findings

Count first: I enumerated **950 passes in 13 shipped files** (`table.py`: base 29, propagated 31, animation 31,
recommendation 59, Low 60, Standard 87, High 99, High-4k 99, tri 57, quad 79, quad-cadence 79, quint 108, sext 132), and
ran the liveness tools over all 49 files under `shaders/`.

1. **[R, `dead_passes.py` run tonight] L7's "177 dead in 49 files" is now 160** after L1 and L2 (the base reports 6 of
   29; the variational line 1; the carry line 3; the stock `-variational` and its 4k twin 52 each, the whole B->A cascade).
2. **[R, `live2.py`] The tool has a blind spot in each direction, because the project's cross-pass channel is storage
   images, which it does not see.** It follows `//!SAVE` and `//!BIND` only. (a) **False dead:** `ALIAS_E_AB` and
   `ALIAS_Q_AB` in the carry line write `ALIAS_E_AB_ST`, `ALIAS_E_BA_ST`, `ALIAS_E_M_ST` by `imageStore`, and the live
   refine passes `FLOW_E_AB_RAW`/`FLOW_E_BA_RAW` read them by `imageLoad` (High tier passes 11 and 15-16; the alias pass's
   body has one `imageLoad(ALIAS_E_AB_ST)` and three `imageStore`s). **Pruning them, as L7 proposes, would change the
   output.** With storage reads counted the total falls from 160 to 140. (b) **False live:** the fused first median
   (`[fused with its B->A twin: one dispatch]`) binds `FLOW_H_BA` to compute the B->A median into `FLOW_H_BA_M1_ST`,
   whose only reader is the second B->A median, which is dead. The bind keeps the whole upstream B->A chain "live" in the
   tool's eyes. I checked that no shader uses `imageAtomic*` or `texelFetch`, so BIND/imageLoad are the only read paths.
3. **[R, `prune_sim.py`: dataflow with storage, twins split, iterated to a fixpoint] The dead chain in the two-frame
   variational tiers is far larger than L7 says.** Dead at `read_view 0`:

   | tier (file) | dispatches at read_view 0 | dead whole passes | + half of a fused pass | dead share of dispatches / of texels | dead passes WITHOUT a pair cache |
   |---|---|---|---|---|---|
   | base | 22 | 6 (the B->A chain: S, E, Q, H refines, two medians) | 0 | 27% / 25% | 0 |
   | propagated (fast tier) | 24 | 3 (Q and H refine B->A, 2nd median B->A) | 2 (the three-way check's BA half, the 1st median's BA half) | 17% / 22% | 0 |
   | animation | 24 | 3 | 2 | 17% / 22% | 0 |
   | recommendation `-variational-propagated` | 52 | **17**: Q refine B->A, 8 variational Q B->A, 2 medians Q B->A, H refine B->A, 4 variational H B->A, 2nd median H B->A | 2 | **35% / 36%** | 14 |
   | Low `-cut` | 53 | 17 | 2 | 34% / 36% | 14 |
   | Standard `-carry-adopt-cut` | 80 | **24**: the 17 above + the alias pick (BA) + the six-pass outline-adoption BA chain | 2 | **31% / 34%** | 14 |
   | High `-carry-adopt-lattice-cut` | 92 | **17**: the print's apply (BA) + 8 variational Q B->A + 2 medians Q B->A + H refine B->A + 4 variational H B->A + 2nd median H B->A | 1 | **19% / 26%** | 15 |
   | tri, quad, quad-cadence, quint, sext, human-reading-quad | 50-125 | 0 | 0 | 0% | - |

   Mechanism: in every two-frame shader the output reads `FLOW_H_AB` only (the warp binds `HOOKED, SCENE_DIFF, [SCENE_RES,]
   NEXT, FLOW_H_AB, [SUPPORT]`). B->A is live only as far as something A->B reads it: the E-level propagation and three-way
   check (both tiers), `FLOW_Q_BA` into the alias scans, the adoption and the print gate (High only). Everything B->A after
   its last A->B reader is dead, and in the High tier the adoption's BA chain is live only because the print gate reads
   `FLOW_Q_BA`; in Standard there is no print gate, so the adoption's BA chain dies too. [J] The record's L7 count came
   from the tool, and the tool was reporting the one pass the fusion left visible.
4. **[R] The dead variational passes have no `pair_changed` cache**, so they do their arithmetic on every output frame,
   not on 40% of them (24 -> 60 is 2.5 output frames per pair; `SHADERS.md` L1396). Of the recommendation's 52 live-or-dead
   dispatches, only 10 test `pair_changed`; of High's 92, 39. Every variational iteration and every Q-level median is
   recomputed on cache-hit frames with identical inputs (an iteration reads only the two lumas and the flow; no phase).
5. **[R custom_mpv.c L1295-1302] libplacebo skips a `//!WHEN` pass before building any shader** (`eval_shexpr` on
   `hook->cond`, then `continue`). So the reading tail (7 passes in every shipped shader, all `read_view 0 >`) costs no
   dispatch at `read_view 0`. Its three `//!TEXTURE ... STORAGE` buffers (`MODE_MEM` 1440x270, `READ_ACC` 480x270,
   `READ_SCALE` 1x1, rgba32f) are allocated regardless: about 6 MB, memory only [J]. The Metal host does the same
   (`gen_metal.py` L67-73). Nothing in the tail is free to remove for time.
6. **[R custom_mpv.c L1030-1075, patch L571-576] `//!WHEN` cannot see content or the pair.** Its RPN evaluates constants,
   texture sizes and `//!PARAM`s; `pair_changed` is a GLSL uniform (`sh_var`), not a WHEN variable. Content gating by
   WHEN is therefore impossible without a patch change, and a cached pass cannot be skipped by WHEN today. Also
   `hook_reset` (L945) empties `pass_textures` on every frame (called from `renderer.c` L3675), so a pass skipped by WHEN
   leaves its SAVE name unbound for later passes that frame.
7. **[R renderer.c L436-462] Saved (`//!SAVE`) textures take the renderer's FBO format, probed from a list whose first
   entries are 16-bit; the project's storage caches are declared `rgba32f`.** This is L10's fp16 stage. It matters for
   byte-identity claims: a value cached in fp32 and returned through the same `//!SAVE` rounds to the same fp16, so a
   cache is identical; a value moved from a sampled SAVE to a storage image is NOT identical unless rounded to fp16 first
   (`unpackHalf2x16(packHalf2x16(v))`) [J].
8. **[R] The generators find the base's B->A passes by saved name and assert the base's pass count** (`gen_tridirectional.py`
   L245, L338-352, L369; `gen_quaddirectional.py` L358, L411-431, L454: `find("FLOW_H_BA", "refine")`, the second median
   found by `"pass 2"`). A pruned base breaks them, as L7 says. But `gen_variational.py` is the last generator on the
   two-frame player line and nothing consumes its output, so a prune step at its end is safe (`build()` L746-789 emits
   B->A iterations and medians unconditionally; `main` L791-870 writes the file after `READING.add_tail`).
9. **[R NFRAME-LIMITS L1419-1423, L1467-1470; ENERGY-TRANSFER L3237-3250] The record's cost model, restated for the M5
   from tonight's numbers:** (18.24 - 3.16) / 52 = 0.29 ms per dispatch on the recommendation; (32.01 - 3.16) / 92 = 0.31
   on High. [J] The two agree to 7%, which says the M5's time is dispatch-count first, as the RX 6600's was; the shader
   content barely moves the per-dispatch figure. Calibration from REPAIRS: L2 removed 2 of 31 passes for -6.3% (2/31 =
   6.5%); L3 removed 25-tap reads at three levels and no passes for -0.3% ("free, not faster").
10. **[R ENERGY-TRANSFER L3240] "every extra pass costs on real footage, because the passes run on every OUTPUT frame
    (about 2.5 per source pair) even when they only return their cache."** The record has already named the mechanism
    behind proposal 5 and left it at the shader level; the engine-level answer needs the patch.
11. **[R] The texel-heavy passes are not where the dispatch count is.** Per output frame at 720p the recommendation sums
    5.9 Mtexels over 52 dispatches, High 8.3 over 92, tri 11.0 over 50 (8 full-resolution passes), sext 29.6 over 125.
    The one-texel statistic passes (`SCENE_DIFF`, `SCENE_RES`, `GLOBAL_SHIFT`, `READ_MAX`) are 576-tap serial loops in a
    single thread (`SCENE_RES`: 24 x 24 samples, two `NEXT` taps each); small, not a cost.

## Proposals, ranked

Common measurement protocol, from the record: time by `tests/probes/repairs/timepair.sh old new 5` on the M5 (file source,
interleaved after a warm-up, median of five pairs; `TESTING.md` "Timing basis"); identity by `identity.sh` on the Arc,
each shader against itself first, **one warm-up render before the first comparison** (L8: the job's first render differs
on L7_textured_large), and a counterfactual pair that must differ; `compile_all.sh` before either (L3: a generator can
emit code that does not build and libplacebo falls back silently).

### 1. The L7 prune, done by dataflow, as the last step of `gen_variational.py` (rank 1)

**Mechanism.** A text-level pass `prune_dead.py`: parse the `//!HOOK` blocks; liveness = SAVE bound by a later live pass,
or an `imageStore` target `imageLoad`ed by any other live pass (storage persists, so any direction); a `[fused with ...]`
pass's twin half (the reversed pair token in its binds and stores, e.g. `_BA` for a `_AB` save) is dead when its storage
outputs have no live reader; iterate to a fixpoint. Delete dead blocks whole, together with the `//!TEXTURE ... STORAGE`
declarations only they reference (`FLOW_Q_BA_CACHE`, `FLOW_H_BA_CACHE`, `FLOW_H_BA_MEDIAN_CACHE`, the adoption's BA
buffers in Standard); in a fused pass with a dead twin, delete `hook_ba()` and its call, the twin's `//!BIND`s and its
`_M1_ST` texture. Assert every count; keep each banner with the block below it (L2's slip). Call it in `main` after
`CUT_MOTION` and before `BANNER`/`add_tail`, recorded in the banner as `PRUNE=1`. `rebuild_generated.py` then rebuilds the
nine player files (three tiers, their 4k twins by `scale_shader.py`, the recommendation and its twin); the control run
(prune off) must be byte-identical first. The hand-maintained bases stay unpruned because the N-frame generators consume
them (finding 8); their dead six passes are a separate decision (hand-off).
**Prior attempt.** L7 itself, which named 1-3 passes per file from `dead_passes.py`; L1 and L2, which removed passes and
measured -0.9% and -6.3%. This is not that: the count is 17-25 per file, found by following storage and splitting fused
twins, and it excludes the two alias passes L7 would have cut wrongly.
**Prediction.** Byte-identical on every scene (dead code). Dispatches at read_view 0: recommendation 52 -> 35 (and two
fused passes lose their BA half), Low 53 -> 36, Standard 80 -> 56, High 92 -> 75. Time on the M5 at 0.29-0.31 ms per
dispatch: recommendation 18.24 -> about 13.2 ms (-28%); High 32.01 -> about 26.7 (-17%); Standard about -30%; the
fused halves add a little on top (arithmetic only). The texel share agrees with the dispatch share within a few points
(finding 3), so the two models predict the same.
**Kill test.** Any differing frame on the Arc on the four `identity.sh` scenes (after the warm-up) kills it outright.
Time: a fall under 10% on the recommendation (five-pair median) refutes the dispatch model for these passes, which would
itself be a finding; a fall of 20-35% confirms. Inconclusive (10-20%) tips to "ship, and measure the Cadence graphs".
**Cost.** 2-3 hours to write and control; GPU about 12 minutes (compile_all; identity on four tiers x four scenes with
controls; five timing pairs x three tiers). Then `gen_metal.py` for the Cadence graphs (hand-off).

### 2. Pack the two frames' lumas into one texture per level (rank 2; a different kind: fusion)

**Mechanism.** `LUMA_A_x` and `LUMA_B_x` are two dispatches of the same size with no dependency (four pairs in every
two-frame shader; in the N-frame shaders three or more lumas per level). Emit one pass writing `LUMA_AB_x` with A in `.r`
and B in `.g` (`.rgba` where `.g` already carries the energy, as the High tier's S and E lumas do), and rewrite every
`LUMA_B_x_tex(p).r` to `LUMA_AB_x_tex(p).g` and every `LUMA_A_x_tex(p).r` to `.r`, plus the `_pt`/`_size`/`_pos` names.
The consumers keep their samplers, so bilinear reads are untouched (the record's limit on fusion, NFRAME-LIMITS L1460).
Do it as the last generator step after the prune, since the N-frame generators rename lumas by regex (`shift_lumas`).
**Prior attempt.** The 2026-09-04 fusion fused A->B/B->A twins through storage images; the lumas were not in it because
they are not twins of one computation. ENERGY-TRANSFER's `_fuse` is the same storage pattern. Channel packing is new here.
**Prediction.** Byte-identical if the FBO format for 2 or 4 components has the same per-channel depth as for 1 (renderer.c
probes per channel count from the same config; on the M5 and RX 6600 both are 16-bit float [U]); otherwise differences at
the fp16 ulp. Dispatches: recommendation -4 of 35 after the prune (about -1.2 ms, -9% of the shader's own time); tri -10 of
50, quad -15 of 72, sext -25 of 125 (three or more lumas per level pack into one). The High tier's three ENERGY A/B
pairs pack the same way (-3).
**Kill test.** A differing frame on the Arc kills the byte-identity claim; then check whether the difference is confined to
the fp16 ulp (a bounded result, shippable as a variant). No time fall across five pairs kills it.
**Cost.** 3 hours (the rewrite touches hundreds of sites; the assert-every-replacement rule); GPU 10 minutes.

### 3. Cache the live variational cascade per pair (rank 3; the same kind as the record's caching, said so)

**Mechanism.** After the prune the recommendation still runs 8 Q iterations, 2 Q medians and 4 H iterations A->B on every
output frame (1.5 Mtexels of about 20 taps and an `exp` each) though their inputs are the pair's. Give each chain the
median pattern already in the file: iterations 1..n-1 return a dummy when `!pair_changed`; iteration n stores its result
to a `rgba32f` storage image and returns `imageLoad` of it on cache-hit frames. Three storage images per shader (Q, H, the
Q median), sized like the existing caches.
**Prior attempt.** `SHADERS.md` "Caching": the four search levels and the second medians are cached; the variational
iterations never were. L3 is the calibration: removing arithmetic without dispatches gave -0.3%.
**Prediction.** Byte-identical (finding 7: the fp32 value re-enters the same fp16 SAVE). Time: the arithmetic share only,
on 60% of output frames: -1% to -4% at 24 -> 60; 0% at 24 -> 24 (the field instruments gain nothing). Memory +3 x 8 MB.
**Kill test.** Any differing frame kills. A fall under the pair noise (about 1%) kills the proposal and confirms the
record's "dispatch is the floor"; a fall above 3% says the variational arithmetic is heavier than L3's gates were.
**Cost.** 1 hour in `PASS`/`MEDIAN` templates; GPU 8 minutes. Rank 3 because the ceiling is low and already predicted low.

### 4. Skip cached dispatches on cache-hit frames: `pair_changed` as a `//!WHEN` variable (rank 4; the leap)

**Mechanism.** Two changes, one in `frame-mix-hook.patch`: expose `pair_changed` to `eval_shexpr` as a WHEN variable
(custom_mpv.c resolves variables by name; about ten lines), and give every per-pair pass `//!WHEN pair_changed`. Because
`hook_reset` empties the saved-name table every frame, the consumers of a skipped pass must read its storage cache
directly (`imageLoad(FLOW_H_AB_MEDIAN_CACHE)` in the warp instead of `FLOW_H_AB_tex`), which means the warp's bilinear
flow read becomes a manual four-tap lerp from the image.
**Prior attempt.** ENERGY-TRANSFER L3240 named the cost ("passes run on every OUTPUT frame ... even when they only return
their cache") and answered it with fewer passes and fusion inside the shader. The record never changed the engine's skip
rule; REPAIRS' round-two preamble confirms the engine skips only on stage or WHEN.
**Prediction.** On 60% of output frames at 24 -> 60, every cached dispatch vanishes: after proposal 1 the recommendation's
10 cached passes, High's 39 (of 75). Time: recommendation about -10%, High about -25% beyond proposal 1. Not
byte-identical: the manual lerp differs from the sampler's fixed-point weights at the last bits; bounded by one fp16 ulp
of flow, invisible in PSNR [J].
**Kill test.** Any ladder case moving by more than 0.05 dB kills it (the warp's flow read changed more than rounding). A
time fall under 5% on High kills the premise that cache-hit dispatches cost what full ones do. The owner decides whether a
patch change is in scope (hand-off); it also moves the Metal host out of lockstep until its engine learns the same skip.
**Cost.** Half a day (patch, rebuild ffmpeg, three tiers, Cadence graphs); GPU 20 minutes plus a ladder run (6 minutes
per shader) because identity is not claimed.

### 5. Lower resolution and content gating: counted, not proposed

The only full-resolution pass at `read_view 0` in every two-frame tier is the warp (finding 11); the energy's six 1/4-res
passes in High (Gaussian sigma 12 px = 3 texels at 1/4) could run at 1/8 for -6 x 0.0576 Mtexels and no fewer
dispatches, so the dispatch model predicts nothing from it and the picture would move (bounded, unknown). Content gating
by `//!WHEN` is impossible in libplacebo (finding 6), and the record's warning stands: the one content gate that helped
was an accident (NFRAME-LIMITS L1496). I propose neither. The N-frame full-resolution refines (8-22 passes of 0.92
Mtexels) are twins whose BA consumer samples at texel centres (`FLOW_F_BA_tex(HOOKED_pos)`) and could fuse through
storage with an fp16 round; the record left the 1/2 refines unfused for generator reasons, not algorithmic ones, but the
saving is 2-5 dispatches per file against a 21 ms arithmetic share (NFRAME-LIMITS L1421), so it ranks below the four
above.

Loops of a kind: proposals 1 and 3 are both "stop doing work nobody reads"; 2 and 4 differ in kind (fusion; an engine
skip). Proposal 4 is the only one that touches the patch.

## Refuted entries checked

- NFRAME-LIMITS L1395-1423: shared-memory compute tiles (+13%/+9%, slower) and tap reuse (4.5x fewer taps, no change).
  Nothing here reduces taps or uses compute; proposals count dispatches, and 3's small prediction is calibrated on L3.
- NFRAME-LIMITS L1458-1462: what did not fuse and why (the 1/8 refines' order dependency; the half-res refines cloned by
  name; the second medians feeding bilinear samplers). Proposal 2 keeps samplers; proposal 4 names the bilinear problem
  and bounds it; the Q refine A->B/B->A pair that my adjacency scan listed as a candidate is excluded for the first reason.
- NFRAME-LIMITS L1496 (the motion-sensitive accident) and L432/L545 (the prefilter), L2716 (the tensor fill), L4031 (the
  agreement blend): no content gate or picture change proposed.
- ENERGY-TRANSFER C3 MISSED (L3184: a cost gate on a cell's own margin breaks the weave): no gate tightened here.
- REPAIRS L3 "free, not faster": the calibration for proposal 3.

## Hand-offs

- **For the generator lane / owner:** replace `dead_passes.py` with the dataflow version (storage reads in any direction,
  twins split; `prune_sim.py` in my scratch folder is a start) and correct REPAIRS L7: `ALIAS_E_AB` and `ALIAS_Q_AB` are
  live through storage; the dead count in the variational line is 17-25 per file. Decide whether the three hand-maintained
  bases get a pruned shipped copy or stay as they are until `gen_tri/quad/quint/sext` can take a pruned base (they assert
  22 base passes and find `FLOW_H_BA` by name).
- **For the owner:** proposal 4 changes `frame-mix-hook.patch`; the Metal port's lockstep and the Cadence graphs follow
  every proposal that changes a shipped file (`gen_metal.py` records the source SHA-256).
- **For the ladder lane:** nothing here moves a ladder number if the identity checks hold; proposal 4 is the exception.
- **A record note:** the `SHADERS.md` pass table (L47-90) predates L2 by two passes per file (it says 54 for the
  recommendation; the file has 52 at `read_view 0` plus the 7-pass tail).

## Felt

- Felt: unease, `dead_passes.py` following BIND/SAVE while the project's channel is storage images, medium; its verdict
  could be wrong both ways. -> wrote `live2.py` and read the alias pass's stores. Outcome: right (two false deads).
- Felt: surprise, "FLOW_H_BA alone" dead in the variational line when the whole chain is dead in the base, medium; the
  fused median must be hiding it. -> read passes 86-88 of High; wrote `prune_sim.py`. Outcome: right (17 passes).
- Felt: surprise, no `pair_changed` in any variational iteration, low; identical work on 60% of frames. -> proposal 3,
  ranked low after L3's calibration. Outcome: open.
- Felt: unease, my tool marking the tri's propagation twins dead when the record checked those files, medium; my tool,
  not the record. -> dug: two bugs (twin death decided before the fixpoint; `_BA`-only twin names). Fixed; N-frame 0 dead.
  Outcome: right.
- Felt: pull, skipping whole dispatches on cache-hit frames through WHEN, medium; the record names the mechanism and
  stops at the shader. -> read `eval_shexpr`, `hook_reset`, the FBO pool; found the two obstacles; kept it as the leap.
  Outcome: open.

## Verdicts

**Reasoned.** The cheapest certain saving in the family is the one L7 already pointed at, undercounted by a factor of
six to eight: a text-level prune by dataflow removes 17 of 52 dispatches from the recommendation, 24 of 80 from Standard
and 17 of 92 from High, byte-identical by construction, for about -28%, -30% and -17% of frame time at 0.3 ms per dispatch.
The record's own tool would also have cut two live passes in the carry line. Everything else on this lane is smaller
(luma packing, -4 to -25 dispatches by file) or slower (the variational cache, a few percent) or needs the patch (the
WHEN skip, the only path to the 60% of output frames that redo cached work). The reading tail costs nothing at
`read_view 0` in either engine.

**Gut.** Satisfying and slightly embarrassing for the tool, not the shaders: the dead chain was hiding behind the one
optimisation that worked. Reasoned and gut agree; the identity run on the Arc settles the only thing that could separate
them.
