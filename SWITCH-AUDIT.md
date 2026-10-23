# Shader switch audit and use-case guide

Verified 2026-10-23 against n-frame e85c1d6 and the local Cadence source/resource snapshot. This expands the initial
inventory into a purpose, implementation, evidence and default review. **No settings or production shaders were
changed by this audit.** The build checks and their limits are in [the reproducible results](tests/probes/switches/RESULTS.md).

## What “default” and “works” mean

There are three defaults: the environment value a generator reads, constants baked into a generated shader, and the
graph an application selects. An unset generator flag is usually off so old experiments reproduce; that does **not**
mean a player should use a shader with all features off. Cadence selects prebuilt tiers with an adopted combination.
Changing an environment variable while playing does not rebuild or change those graphs.

This guide distinguishes **implementation verified** (the branch/transform matches its stated mechanism, with fresh
CPU counterfactuals and representative compilation), **recorded GPU evidence** (a named earlier experiment, with its
particular inputs/host), and **default judgement** (a recommendation for the stated use case). A compiled switch can
implement its mechanism correctly while failing its quality hypothesis. No setting is proved best for every film.
All quality figures below are existing recorded results, not newly rerun GPU tests in this audit.

The scope is all **37 distinct environment controls** found in the generators and their switch modules, including
every control in the supplied inventory. Later sections add the important source-level selectors and all three live
shader parameters. Ordinary mathematical constants, diagnostic-driver options and every historical research fork are
not presented as newly validated product switches.

## Cadence: what is actually selected

Read-only witnesses: the private app's `Player/Sources/Cadence/Playback.swift` (`QualityTier`, `graphName`, `isLarge`),
`Player/project.yml`, and `Bench/Resources/graphs/*/graph.json`. These private files are not copied into this public
repository. The [recorded public shader hashes](tests/probes/switches/RESULTS.md#cadence-resource-witness) make the
resource comparison reproducible when the app checkout is available.

| Tier | Shader suffix after `bidirectional-interpolation-variational-propagated` | Extra mechanisms | Current graph passes, including reading tail |
|---|---|---|---:|
| High, the quality default | `-global-cage-energy-carry-adopt-lattice-cut` | all adopted picture features below | 82 |
| Standard, first fallback | `-global-cage-energy-carry-adopt-cut` | High without print-lattice re-scoring | 63 |
| Low, second fallback | `-cut` | propagated variational reference plus motion-aware cut gate | 43 |

Each has a `-4k` twin. Selection is by **pixel count above 1920×1080**, not just a filename, a width threshold or the
presence of the text “4K”. All six graph source hashes currently match the repo's **PRUNE=2** files. The initial
inventory's “PRUNE is not in Cadence” statement is stale. Seven passes in each total are reading passes gated off at
`read_view=0`; normal-mode graph dispatch counts are consequently 75/56/36, before any other host scheduling costs.
This is source/resource inspection, not a fresh timing measurement or proof of every installed device's app state.

High is an appropriate **quality default when interpolation is enabled and the device can sustain it**. The code
falls back High→Standard→Low while playing. It is not a guarantee of performance on the Arc NAS or every Apple GPU.
Cadence also has independent policy: smoothing above 1080p is off by default unless enabled, and its current tvOS
`interpolationOffered` policy is false. A selected High preference therefore does not mean interpolation runs on
all platforms/content. Those policies are separate from GLSL generator switches.

### Adopted picture mechanisms

H/S/L below mean the current High/Standard/Low resources. “On H/S” describes the baked feature, not an environment
variable evaluated by the player. The [generator](tests/gen_variational.py) and the linked modules are the authority
for dependencies and details.

| Switch; generator default | Purpose and actual implementation | Does it do the claimed thing? | Default judgement and other uses |
|---|---|---|---|
| `GLOBAL_SEED=0` | Estimate dominant frame translation on a sparse coarse grid; add its candidate and centre the small-motion prior on it when the global estimate passes its gates. It does not force every object to share that motion. | **Implemented and measured.** The global estimate, candidate and prior are all present. [Global-motion record](NFRAME-LIMITS.md): fast tracking-shot improvement, but periodic-print trades. | **On H/S, absent L** is supported by the adopted combined tier. Useful for pans/tracking shots and reach diagnosis. Off remains the reproducible reference and can avoid a misleading global prior in independently moving/periodic scenes. |
| `QZERO_MOIRE=0` | At the quarter level, add a zero-start descent under Moire evidence. Select it only with good matches and a separating cost ridge; this is not a blanket preference for zero motion. | **Implemented and measured.** [Cage experiments](NFRAME-LIMITS.md) show a partial recovery; it does not solve all rotating bars. It is distinct from the base's earlier `ZERO_SEED`. | **On H/S, absent L.** Useful for fine prints/railings that alias at 1/8 sampling; leave the original thresholds for the adopted tiers. |
| `COHERENCE_GATE=0` | Measure agreement with neighbouring flow plus absolute/relative unwarped frame agreement; blend unwarped where all the tests favour refusing the warp. | **Implemented and measured.** [Field-coherence record](NFRAME-LIMITS.md) reports cage gains. It changes picture composition, not the underlying estimate into a proven correct field. | **On H/S, absent L.** Useful for unstable fine periodic content; unsuitable as a generic confidence/sigma readout. |
| `COARSE_ENERGY=0` | Add smoothed texture-energy channels beside point-sampled luma in coarse/1/8 matching and the data check. The original luma samples remain. | **Implemented and measured, a trade.** [Energy mechanism](tests/coarse_energy.py), [limb/periodic evidence](NFRAME-LIMITS.md): improves moving texture/reach, can worsen half-period aliases. It is not an anti-aliased replacement pyramid. | **On H/S, absent L**, with weights 8/1. Useful for textured moving subjects against detailed backgrounds and as a standalone `-energy` variant. Not a universal improvement for exact periodic prints. |
| `ALIAS_PRIOR=0` | Let the global shift break a tied cell's two-basin ambiguity only when the shift agrees with one basin. | **Implemented; measured principally in the combined carry tier.** Requires `GLOBAL_SEED=1`; invalid combinations are rejected. [Carry module](tests/alias_carry.py). | **On H/S, absent L.** Useful when dominant pan supplies an anchor. The combined gate supports the deployed setting; it does not independently prove this term's benefit on every scene. |
| `ALIAS_CARRY=0` | Quarter-level semi-global min-sum propagation over two candidate basins, carrying boundary/anchor evidence into a periodic interior. | **Implemented and measured.** [Half-period alias record](NFRAME-LIMITS.md). It chooses among available labels; it cannot create information absent from an exact periodic interior. | **On H/S, absent L.** Useful for periodic stair/bar prints with informative ends. Cost and its dependence on the surrounding features justify keeping Low simpler. |
| `ALIAS_APERTURE=1` | In the carry's smoothness cost, discount the component a stripe cannot constrain. `0` selects the older non-aperture-aware form. It does not change the whole optical-flow solver to a tensor solver. | **Implemented and recorded.** Only effective with `ALIAS_CARRY`; the fresh audit confirms it is inert without the parent. [Module](tests/alias_carry.py), [aperture record](NFRAME-LIMITS.md). | **Keep 1 on H/S.** Useful for oblique/rotating one-dimensional prints. `0` is an ablation/regression setting, not a recommended general default. Low has no carry, so the flag has no effect there. |
| `OUTLINE_ADOPT=0` | After the carry, let a locked periodic print use motion anchored by its outline under the module's gates/cap. | **Implemented and measured.** Requires `ALIAS_CARRY`. [Implementation](tests/outline_adopt.py), [adoption experiments](ENERGY-TRANSFER.md). An outline is useful only when it belongs to the moving print, not a still occluder. | **On H/S, absent L.** Useful for slowly moving periodic objects with informative outlines. Do not interpret it as proof that every visible boundary is an object-motion anchor. |
| `PRINT_LATTICE=0` | Re-score candidate aliases of a print lattice at full resolution after the carry/adoption, under a cost cap. | **Implemented and measured.** Requires `ALIAS_CARRY`. [Module](tests/print_lattice.py), [weave/lead-4 evidence](ENERGY-TRANSFER.md). Still limited by periodic ambiguity and available labels. | **On H only.** Its benefit/cost is the deliberate High/Standard distinction. Use for woven/printed textures; Standard is the valid performance alternative. |
| `CUT_MOTION=0` | Retain the existing scene-difference threshold but hold a source frame only if the final motion also leaves enough difference unexplained. | **Implemented and measured.** [Module](tests/cut_motion.py) explicitly tests both conditions; [cut/print evidence](ENERGY-TRANSFER.md). It does not disable cut protection or promise to detect every edit. | **On all H/S/L** is the adopted playback setting. Useful wherever moving high-contrast content could otherwise masquerade as a cut. Off is a reference/ablation, not the preferred Cadence policy. |
| `ZERO_SEED=0` environment override | **Force on**, when a compatible base has the two zero-seed sites. The seeded, propagated and animation sources already contain `ZERO_SEED=1`. `ZERO_SEED=0` leaves that base unchanged; it does not force those sites off. A base with no such sites is rejected if force-on is requested. | **Implemented, but the name can mislead.** Off/on are identical on current seeded/propagated sources; a deliberately disabled source copy changes under `=1`. [Source](shaders/src/bidirectional-interpolation-propagated.glsl). | **Effective seed stays on in Cadence's compatible base**, despite the environment default 0. Useful for experimental base restoration and historical reproduction. To ablate it, make a generated variant through the source/tool path; do not rely on `ZERO_SEED=0`. |

### Adopted mechanisms' tuning controls

These knobs are inactive unless their parent feature is enabled. Units are part of the setting; a matching numeric
value at a different resolution is not necessarily a matching screen-space decision. Use the generated 4K twins
rather than blindly applying the ordinary file to larger frames.

| Control; default | Actual effect and verification | Cadence/default judgement; other uses |
|---|---|---|
| `QZERO_MOIRE_MIN=.25` | Minimum Moire score for the quarter-level zero descent; emitted into that gate. A changed value changes executable text. | Keep .25 for the adopted tier. Useful for controlled sensitivity studies of aliased prints, not a measured probability of aliasing. |
| `COARSE_ENERGY_WS=8` | Weight of the energy mismatch at 1/16. Confirmed separate from the luma weight and from `_WE`. | Keep 8 with the adopted energy form; the record compared multiple weights. Use for scene/scale ablations, not per-film ad hoc retuning of the default. |
| `COARSE_ENERGY_WE=1` | Weight at 1/8, including its associated matching/check path. | Keep 1 in H/S. Useful for separating coarse candidate selection from later arbitration; 8/1 are not interchangeable constants. |
| `ALIAS_TAU_CARRY=.05` | Changes the **carry's** tie threshold only; the prior's base `TAU=.05` remains unchanged. Fresh code comparison verifies the knob is wired. | Keep .05. Larger tolerance can admit less ambiguous/wrong alternatives; smaller tolerance refuses more propagation. Useful for studying carry support; no alternate universal optimum established. |
| `CUT_EXPLAINED=.3` | Require motion-compensated residual `r > .3*d0` in addition to scene difference. Raising it makes the cut veto harder to trigger; lowering it makes holding more likely. It is a residual-ratio threshold, not “30% explained.” | Keep .3 in all tiers. The [record](tests/cut_motion.py) separated sampled real cuts from moving prints. Useful for cut-sensitivity tests; no guarantee for all dissolves/flashes. The emitted threshold has three decimal places, so tiny overrides may quantize away. |

## Built but not selected by Cadence

Off is the appropriate current **product** default for these controls. That does not make the implementation useless:
several are good instruments or bounded variants. A failed quality hypothesis is kept separate from a wiring fault.

| Switch; default | What it actually does | Evidence and default/use-case judgement |
|---|---|---|
| `EDGE_PROP=0` | Multiply 1/8 propagation votes by agreement with the texel's own motion, blended by own confidence. | **Implements the claim, quality hypothesis refuted.** [Source and measured failure](tests/gen_variational.py): helps limb boundaries but protects confident wrong aliases; capped ladder mean -.36 dB in its recorded gate. Keep off for Cadence; useful as an ablation of motion-edge protection. |
| `TRUST_GATE=0` | At ambiguous cells, offer wider quarter-level minima and decide at full resolution; insert decision/apply passes before downstream adoption. Requires carry. | **Implements the mechanism, product benefit unresolved/traded.** [Module](tests/trust_gate.py), [trust-gate record](ENERGY-TRANSFER.md). Do not infer the live pipeline from offline best-case search numbers. Keep off for Cadence; use to inspect coarse-seed failures and candidate ranking. |
| `LOCAL_CENTRE=0` | Re-centre the 1/8 small-motion prior on a trusted local coarse candidate for sufficiently fast, neighbourhood-consistent motion; fill the global centre's zero where applicable. It adds neither a new candidate nor a new SAD. | **Implementation verified; limited mixed evidence**, not a winning tier replacement. [Module](tests/local_centre.py), [reach-lane result](SWARM-2026-10-21.md). Keep off in Cadence. Useful for separating reach limits from the zero-centred prior. |
| `PHASE_FETCH=0` | Fetch the coarse matcher's target taps from full-resolution frames at the displaced reference phase; keep reference taps and the energy term's sampling otherwise unchanged. | **Implemented, measured trade.** [Module](tests/phase_fetch.py), [phase-fetch results](NFRAME-LIMITS.md). Fixes some locks and loses other speeds/periods. “Exact phase” does not imply perfect reconstruction at arbitrary fractional full-res coordinates. Keep off for Cadence; use for sampler-comb research. |
| `PHASE_FETCH_E=0` | Extend that fetch to four 1/8 comparison sites, including the candidate re-score and data check. Requires `PHASE_FETCH=1`. | **Implemented; registered combined quality claim refuted.** It recovers P1 and v12 but loses P5/v10 and other cases. Keep off for Cadence; useful to locate which lattice makes a failure. |
| `PHASE_GATE=0` | Under the coarse ring/zero-basin cost/separation test, re-run the descents on the stored grid and retain that result. Requires `PHASE_FETCH=1`. | **The gate executes, its intended discrimination failed.** It fires where some good answers tie and misses decisive wrong answers. [Kill test](NFRAME-LIMITS.md). Keep off; historical counterfactual, not a validated alias detector. |
| `BAR_REDECIDE=0` | On a one-dimensional patch, search across the bars at full resolution, selecting the smallest across speed among near-best minima. | **Implements exactly that prior; both benefit and harm measured.** C3 improves, but correct +6 can become -3 in the ordinary pipeline. [Independent review](tests/probes/cage/BAR-REVIEW.md). Keep off as Cadence default; useful for bar-recovery/coherence experiments. |
| `BAR_KEEP=0` | With re-decision enabled, retain the incoming vector if its nearby sampled basin is near-best. | **Implements the guard; quality repair killed.** Preserves the isolated counterexample but sacrifices most of C3's gain and harms C2. Keep off; comparison instrument. Requires `BAR_REDECIDE`; cannot combine with `BAR_BASIN`. |
| `BAR_BASIN=0` | Compare the selected basin and the nearest incoming basin at their own fine minima, then demand improvement on a broader 48 px block; retain incoming motion if refused. Requires re-decision. | **Implemented; strongest current candidate, not an adopted default.** Local's [basin probe](tests/probes/cage/bar_basin.py) closes the guided regression and passes its reported gate. [Random draws](tests/probes/cage/bar_draw.py) expose lost coherence gains on true ties. Keep off pending the next adoption decision; test on fine bars and both the regression/coherence cases. |

### Research controls belonging to those switches

| Control; default | Purpose and actual effect | Default/use-case judgement |
|---|---|---|
| `EDGE_PROP_TAU=1.0` | Flow agreement scale in **1/8-level texels** (8 source pixels in the ordinary form). Larger values weaken disagreement suppression. | Inactive with EDGE_PROP off. Keep the recorded value for reproduction; increasing it does not prove the refuted classifier is repaired. |
| `TRUST_DECIDE=full` | `full`: refine all decision candidates; `two`: score all coarsely, refine only the provisional winner and current flow. | Full is the reference for research quality. Two is a cost experiment, not assured equivalent. `TRUST_UNIQUE=1` with `two` is rejected. Unknown strings fall through to the full path; use the documented enum, not arbitrary text. |
| `TRUST_OFFER=whole` | `parab` adds sub-texel parabola offsets to offered quarter-level minima; `whole` offers their grid positions. | Whole preserves the original build. Parab is a candidate-quality experiment; it is not a host subpixel-quality setting. Unknown strings effectively use whole. |
| `TRUST_UNIQUE=0` | Demand that the winner also beat a candidate from a different basin by the acceptance margin. | Off reproduces trust1, which failed exact-print cases. **For trust research on periodic content, 1 is the safer comparison**, but it does not make TRUST_GATE adopted. Requires full decision. |
| `TRUST_ALIAS` unset | When set (the recorded experiment uses `.7`), add the box-versus-point contrast test so ambiguity alone does not open the gate. | Unset reproduces the older gate. Use `.7` with uniqueness to reproduce the guarded trust experiment, not as an established Cadence optimum. Empty string means disabled; numeric zero enables a zero-threshold test, so it is not the same setting. |

## Work removal and host compatibility

| Switch/default | Purpose and actual behaviour | Default/use-case judgement |
|---|---|---|
| `PRUNE=0` in gen_variational; **`2` in gen_bases** | `0`: preserve the graph. `1`: remove whole dead passes/storage. `2`: also remove dead fused B→A twins and their dependencies. Follows storage reads/writes as well as SAVE/BIND; keeps WHEN roots. Only 0/1/2 are accepted. | **Use 2 in the shipped picture tiers and base outputs**, as now deployed in the inspected Cadence resources. [Arc byte-identity gates](tests/TESTING.md) support removal, with the liveness contract preserving reading roots. Use 0/1 for census/ablation. Other N-frame generators do not expose this same PRUNE setting merely because gen_variational does. Do not use the pruned two-frame output as a substitute for a generator's required unpruned source. |
| `STICKY_CACHE=0` in variational and tri/quad/quint/sext | Add `//!WHEN pair_changed` plus `//!STICKY` to eligible pair-cached passes, suppressing dispatch on reused windows while offering the previous SAVE output. Apply after pruning. | **Keep off for current Cadence/portable shaders.** [Patched-host controls and Arc gates](tests/TESTING.md) support the compatible FFmpeg form; the current [Metal translator](tests/gen_metal.py) rejects STICKY. It can be a suitable optimization on a fully supported host. “Never a default” is too strong: future host support plus identity/performance gates could justify it. Unsupported libplacebo may reject the shader and fall back, so apparent playback is not proof it ran. |

Cadence's `prune-graphs.sh` removes packaged intermediate files/other platforms' libraries; it is **not** the
`PRUNE` pass-liveness transform. Also, code returning early from a pair cache and a host skipping a dispatch are
different optimizations. The current engine evaluates `when_rpn` but that alone does not implement STICKY retention
or make `pair_changed` a supported condition in the translator.

## Other generators

| Switch; default | Purpose and implementation | Default/use-case judgement |
|---|---|---|
| `CADENCE=0` in gen_quaddirectional | In interior four-frame windows, detect held drawings via a maximum sparse-cell difference, then re-time eligible duplicate/change spans and use the appropriate adjacent-pair flow. Cut checks prevent crossing detected cuts. The branch leaves the estimated flow chains unchanged. | **Works within its window limits** in the [twos/threes experiments](NFRAME-LIMITS.md), not a general inverse-telecine engine. Twos fit better than threes; wholly held/boundary windows fall back. Off remains appropriate for the ordinary continuous-motion quad and field instruments. Use the named `-cadence` quad for held-drawing interpolation experiments. **Cadence's H/S/L player graphs are two-frame and do not contain this branch**, despite the shared name. |
| `FORESIGHT=1` | On compatible seeded/propagated bases, quad and quint can seed an earlier generated pair using its later neighbour's flow, emitted in the required order. The shipped future-prior strength remains zero; a future candidate is not a future regularizing prior. | **Keep 1 for those picture variants**, consistent with recorded footage gains and small cost; not a universal field improvement. `0` is the ablation. Inactive on a base with no temporal-seed machinery. The fresh counterfactual confirms **quad and quint change; sext does not**. Cadence's two-frame tiers do not use this mechanism. |
| `PROP_TENSOR=1` in gen_aperture | Add per-frame structure tensors and tensor-weight the first propagation solve, with tensor-aware disagreement. `0` restores the base arithmetic, though emitted tensor machinery remains. | **Mechanism implemented, general quality hypothesis refuted.** [Generator's recorded gate](tests/gen_aperture.py): the revised form still loses plain translation without gaining the aperture cases. Appropriate default inside an explicitly experimental tensor generator, **not** a recommendation to use that output in Cadence. |
| `PROP_TENSOR_R=8` | Radius of the experimental tensor propagation window, in its 1/8-level grid. It changes neighbourhood size and own-vote normalization. | Reproduction setting, not an adopted optimum. Use to study support/cost; wide windows can swamp the useful local vote. Only relevant to the experimental tensor path. |
| `PROP_TENSOR_EPS=.05` | Diagonal regularization and a matching own-flow term stabilize the 2×2 solve, retaining own motion in unconstrained directions. | Keep for reproducing that experiment. Zero/negative/nonfinite values are not validated operating choices; the generator largely inserts literals rather than validating a safe tuning domain. |

The demo app additionally has a **host** cadence stage that drops held copies before window selection. That is not the
shader's `CADENCE=1` branch. Avoid stacking or interchanging them without a paired timing/identity/retiming test.
For an aperture build, pass an explicit output path outside `shaders/`; unlike the main N-frame generators, its
optional base argument is a literal path, not a bare-name lookup in shaders/src/.

## Source-level selectors omitted from the initial inventory

These are not supported environment flags. The table confirms their implementation/defaults by source review and
existing field/ablation records; it does not claim the 63 environment checks exhaustively test every source-selector
combination. Change the editable source/generator and regenerate a separately named variant; do not hand-edit a
shipped generated file. See [base-source ownership](shaders/src/README.md).

| Selector | Actual default/effect | Correct use and default judgement |
|---|---|---|
| `FRAME_DIFF_GATE` | 0 in the seeded/propagated sources and generated family. With ZERO_SEED enabled, also allow zero-seed competition when a cross-frame difference exceeds `DIFF_MIN=.10`. | **Wired, recorded trade:** synthetic/field gains, small consistent footage losses. Keep 0 for Cadence; useful for field studies. [Source](shaders/src/bidirectional-interpolation-propagated.glsl) explicitly documents the experiment. This is not the final scene-cut gate. |
| `SUBPEL_REFINE` | 0 in the two-frame picture bases; forced to 1 by the generated tri/quad/quint/sext field builders. Fits a sub-texel vertex at the half-res minimum. | **Use-case-specific default is deliberate:** two-frame sharp-picture trade versus more accurate small derivatives. The fractional coarse seed already exists when this is 0; “off means integer-only flow” is false. [Measured field/sharpness trade](NFRAME-LIMITS.md). |
| `SUBPEL_FIT` | 1 selects the equiangular SAD fit; 0 selects a parabola. Inert where SUBPEL_REFINE is 0. | Keep 1 for active field refinement: [recorded calibration](NFRAME-LIMITS.md) favours the SAD-shaped fit. 0 is the fitting-method counterfactual, not an independent picture-quality enhancement. |
| `SUBPEL_SELFREF` | 0 in picture bases, 1 in generated field shaders. Subtract the vertex bias produced by matching the reference patch to itself. | **Implemented and measured** to reduce texture-phase bias, especially at exact integer motion. Keep the current picture/field split. It does not remove true alias locks or all oblique-motion error. |
| `QUAD_MODE` | 0 in the ordinary quad: exact cubic. 1 selects the anchored least-squares quadratic and its residual. It is not a universal quint/sext option. | Keep 0 for the ordinary quad picture reference. Use 1 for model-order/residual comparisons; its picture gate was not a general win. Residual mode 6 at mode 0 is not a confidence signal. [Quad experiment](NFRAME-LIMITS.md), [instrument warning](tests/TESTING.md). |
| `TRI_DIAG` | 0 in the normal N-frame final pass. Nonzero modes return correction/derivative/magnitude/residual diagnostics, with meanings depending on N. | Keep 0 for playback. Choose the required instrument and units for research. Quint mode 6 is zero; sext implements its own residual there. A zero image can be an unused mode, not perfect estimation. Prefer named probe builders over blind substitutions. |
| `DIAG_HOLD_ANCHOR` | Normal quad/quint/sext diagnostics use 0, preserving phase-dependent calibration; the generated human-reading clone sets 1. It does not affect the ordinary warp. | Use the held anchor for stable human displays; keep instrument-specific anchor/time contracts for measurements. Seeing both 0 and 1 in the same file is expected: different passes, not a contradictory default. |
| `SEED_FUT_LAMBDA`, `FUT_PRIOR_DEADBAND`, `FUT_TRUST_CONTRAST` | In foresight.py, 0.0 / 0.0 / false. The future candidate remains enabled where applicable, but its additional prior is off. | Keep the candidate-only defaults. [Recorded prior study](NFRAME-LIMITS.md): a .5 prior harms leading-edge subpixel decisions; a .5 deadband changes the trade, while the contrast gate did not cure it. Useful paired experiments; do not turn on a prior just because FORESIGHT is on. |
| `READ_MEMORY` | 0: pooled exponential memory; 1: use the per-cell multimode memory path in the reading display. | Keep 0 for the established display; use 1 to compare representations of conflicting motion. Neither is the raw field's calibrated uncertainty. |
| `READ_GATE` | 1: allow visibility only near unpooled motion support (`READ_GATE_R=2` at 1/8). 0 removes that display restriction. | Keep 1 for human overlays to limit pooling halos. It does not improve the underlying field. Useful to separate a display halo from estimator spread. |
| `READ_EMA_ALPHA` and derivative/display thresholds | Display-memory/tuning constants, not generator mode switches. The shipped velocity value is .12; 1 removes that temporal smoothing. | Use display smoothing for readability, raw modes for measurement. An oscillation can average away in a smoothed display. Opacity/threshold choices are not estimates of sigma. [Reading-tail guide](SHADERS.md). |

## The three live shader parameters

All three exist as `//!PARAM` uniforms, distinct from generation flags. The inspected Cadence tier graphs carry
**read_view=0, read_alpha=0, read_plate=1**, suitable for ordinary playback. Changing a live parameter requires a host
that exposes it; ffmpeg's filter does not expose these custom shader parameters as ordinary generator environment
variables. Use the project's tail/probe generation tools to set diagnostic defaults when necessary.

| Parameter | Positions and purpose | Verification/default judgement and use cases |
|---|---|---|
| `read_view` | 0 normal output; 1/2/3 human velocity/acceleration/jerk; 4/5/6 raw corresponding fields; 7 pooled velocity; 8 mode memory; 9 velocity-gradient tensor. | **Keep 0 for Cadence.** Reading passes are WHEN-gated and do not run in normal mode. `human-reading-quad.glsl` intentionally defaults to 1. A two-frame shader lacks acceleration/jerk and its labelled views use velocity; three-frame jerk views use acceleration. Raw 4/5/6 are unpooled, but precision/encoding still require the [read-path controls](tests/probes/fp16/fp16floor.sh). Mode 9 is not a covariance map. |
| `read_alpha` | 0 auto exposure from running pooled-field maxima; positive sets a manual magnitude scale; negative selects the older flat-opacity behaviour. | **Keep 0 for readable overlays**, but it is irrelevant while read_view=0. Use positive fixed scales for quantitative side-by-side/deceleration comparisons: auto scaling can keep a slowing object looking dense. Negative is a display comparison, not “turn interpolation off.” |
| `read_plate` | 0 black background; .35 dim plate; 1 original brightness under the overlay. Only changes presentation. | **Keep 1 for ordinary/general viewing.** .35 matches the demo's dim background but can hide colour in dark footage; 0 isolates the field. It does not alter motion estimation or confidence. |

For diagnostic index/scale details, use [the reading-tail documentation](SHADERS.md) and the named probe's header.
Derivative units depend on the source interval and anchor: similarly coloured images are not automatically comparable
physical acceleration/jerk measurements.

## How to choose a configuration

- **Cadence, mixed ordinary film:** retain High with the existing fallback policy and its adopted switches; use the
  size-selected twin. Keep diagnostics and the unadopted research switches off. This endorses the current combined
  tier evidence, not every feature in isolation or a new optimum across all devices.
- **A slower client or expensive 4K source:** use the app's Standard/Low policy or disable smoothing as appropriate.
  Turning on every research mechanism is not a performance strategy. PRUNE=2 removes dead work without a quality trade.
- **Server-side FFmpeg on the Arc:** select a measured tier/size for that actual throughput. STICKY_CACHE is a valid
  candidate only on the matching patched host, after identity and timing controls; Cadence's native Metal compatibility
  does not automatically describe this server path.
- **Held-drawing animation:** compare the named quad-cadence/host duplicate handling against normal output with
  aligned truth and cut controls. The app name “Cadence” does not imply either duplicate mechanism is active.
- **Derivative/velocimetry work:** choose the N-frame estimator, anchor and raw mode deliberately; preserve subpixel
  refinement/self-reference and use synthetic nulls/known motion. A picture-refusal switch or residual is not by itself
  a calibrated motion-field uncertainty estimate; see [the covariance/refutation record](tests/probes/uncertainty/MATHS.md).
- **Fine periodic bars/prints:** retain the adopted carry/adoption/lattice combination for the product reference.
  Compare BAR_BASIN against the guided local-regression **and** random-print coherence cases before promotion. A
  whole-frame gain or fewer false flips alone is not sufficient.

## Reproduction, limits and actions

Fresh evidence: **63/63** environment-wiring/dependency controls, **35/35** unchanged generated-file rebuilds, and
**38** representative variants compiling across **2,366** passes; **five** sticky variants rejected by the current
Metal translator as expected. See [the report and commands](tests/probes/switches/RESULTS.md). Generated artifacts and
logs are outside git under `$NP_SCRATCH/switch-audit-20261023/`. These checks cover representative settings, not every
continuous knob value, every combination, or fresh GPU/Metal execution on every device.

Most boolean environment flags accept **only the literal `1`**: `true`, `on`, or a misspelling can silently leave a
feature off. PRUNE has explicit validation; several tuning enums/numbers do not. Small overrides can also disappear
in emitted decimal formatting. Record the exact generation command and inspect/rebuild the result. Parent flags
matter: ALIAS_PRIOR needs GLOBAL_SEED; adoption/lattice/trust need carry; phase extensions need phase fetch; bar guards
need re-decision; KEEP and BASIN are mutually exclusive; UNIQUE is incompatible with the two-candidate trust decision.

The audit recommends retaining the current Cadence quality recipe, correcting the deployment/force-on/scope notes,
and keeping promising but unresolved variants out of the default. No app or shader default change is authorized by
an implementation check alone. Installed-device verification, future STICKY Metal support and quality gates for new
combinations remain separate engineering work; they are not silently claimed complete by this documentation audit.
