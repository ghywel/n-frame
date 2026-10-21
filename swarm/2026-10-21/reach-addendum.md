# Lane reach, addendum: the energy channel on W3 (+6.3 at 28-32, +2.6 at 36-41), absorbed

Prediction 0(b) ("energy moves W3's 36-41 band by under 1 dB; the wall's energy is uniform") is KILLED by the
measurement (-energy minus the recommendation: +1.17 / +2.07 / +6.32 / +3.67 / +2.63 at 20-24 / 24-28 / 28-32 /
32-36 / 36-41 px). Source: the record and one more CPU emulation (`reach/energy_emu.py`); no GPU.

## 1. Why energy helps here, and what it changes

- **The premise was wrong.** [M-emu] W3's energy image (`tests/coarse_energy.py`: 4 x 4-block 2-px gradient magnitude,
  Gaussian sigma 12 px) splits its variance across scales as the luma does (13% at 128 px, 29% at 32, 58% finer; luma
  12 / 28 / 60). Its std is 0.031 against the luma's 0.17; W_S = 8 makes the two terms the same size.
- **It adds a band-limited channel beside the aliased one.** [J] The 1/16 luma is one tap per footprint: under a shift
  not a multiple of 4 px the 4-px cells re-randomise (the truth costs 0.57 at 37 px, finding 7) and the 32-px cells give
  shallow basins. The energy is smoothed over about three quarters of a coarse texel BEFORE sampling, so |dE| is near
  zero at the truth at every speed and grows smoothly with the error: a bowl centred on the truth laid over the aliased
  landscape. Section 8's prefilter in principle, ADDED rather than substituted, so the aliased contrast stays.
- **Where it acts.** [M-emu] With W_S 8 / W_E 1 the zero descent holds the truth on 91-98% of texels at 24-30 px (luma
  only 28-51%): the alias INSIDE the 1.45-texel reach is gone. Past 32 px the zero descent still reads 0% (reach is a
  constant); the temporal descent from a near-truth start reads 96-100% (luma 63-80%); the 1/8 pick 0.23-0.66 (luma
  0.11-0.46); with the prior re-centred as well, 0.94-1.00.
- **Why the gain peaks at 28-32 and falls to +2.6.** [J] W3 accelerates about a pixel a pair. The temporal seed chains
  from the previous pair's zero descent (3838-3841); energy makes that descent right up to the reach, and the chain then
  carries the truth past it as the speed rises. At 1/8 the prior's bite grows with speed (1.05-1.2 at 28-32, 1.35-1.5 at
  36-41) while the SAD gap does not, so the far bands keep less. `-global-cage-energy` minus `-energy` (+0.2 / +1.1 /
  +2.4 at 28-32 / 32-36 / 36-41) is the prior's residual, rising with speed as the model says.
- **Which term seals the cliff now.** On `-energy` the alias term is gone and, on an accelerating pan, so is most of the
  reach term; at 36-41 the gap to the 28-32 band (20.2 against 29.1) is the prior (+2.4 recoverable, measured) plus
  pairs the chain lost (not recoverable by a prior). On the plain recommendation the prior is still behind most of the
  deficit, but the set is thin there too. Finding 2 stands with a smaller share; finding 4's "nothing local exists
  for the pan" is wrong: energy is a local term.

## 2. Item 9's decision rule, read against both baselines

Run the re-centred prior alone (`LOCAL_CENTRE=1`, no new seed) on two bases; read W3's 36-41 band. The ladder gate
(any period or lattice case down more than 1.0 dB, or the capped mean down more than 0.15, each against its own base).

| base | 36-41 baseline | perfect-centre reference | UP: the prior is the term | DOWN: the set is the limit |
|---|---|---|---|---|
| recommendation | 17.60 | `-global` 22.5 | >= 19.6 (+2.0) | < 18.1 (+0.5) |
| `-energy` | 20.23 | `-global-cage-energy` 22.64 | >= 21.7 (+1.5) | < 20.7 (+0.5) |

Between thresholds: a secondary term; read `leveltap.py` at 37 px before building. More than 0.5 above the reference:
suspect the gate (a centre opening where the frame's gate refused).

- **Both UP:** build `LOCAL_CENTRE` as the switch, gate it, then K1-K3 on `-energy`, where the chain argument predicts
  the larger gain.
- **Plain DOWN, energy UP** (the emulation's expectation): on the plain file the alias inside the reach breaks the
  chain and the set lacks the truth, so a centre has nothing to centre on. Path: energy plus the centre for High; Low
  needs energy or proposal 2 before a prior can help it.
- **Plain UP, energy DOWN:** contradicts the +2.4 the frame centre buys on energy; the local gate (1.5 texels, 3 x 3
  agreement) is the first suspect; `leveltap.py` on both files.
- **Both DOWN:** the prior is not the far-end term; finding 2 is refuted for W3, and the `-global-cage-energy` gain came
  from the candidate. Proposal 2 leads, the doubled first step its cheap precursor; nothing built until `leveltap.py`
  shows which candidate was present and which refused.

Readouts: 28-32 is the band for a set or reach term (a centre should move it under 0.5 on `-energy`; more than 1.0
means it is doing more than re-centring); 36-41 is the band for the prior.

Felt: surprise, the energy's scale mix equal to the luma's, medium; "uniform texture, uniform energy" held only in the
mean. -> Dropped the premise, re-derived the mechanism as an added band-limited channel. Outcome: right (the 28-32 peak
and its fall with speed fit chain plus prior).

## 3. The gate, pre-registered (2026-10-21, night): `LOCAL_CENTRE=1`, built

**Built.** `tests/local_centre.py` (new) and three lines in `tests/gen_variational.py` (the switch, its call after
COARSE_ENERGY, `LOCAL_CENTRE=1 ` in the header's command line). With the variable unset both the recommendation and the
`-energy` file regenerate whole-file identical to the committed ones (`cmp`, and smoke.sh's banner strip). With it set,
the files in `~/Developer/np-scratch/swarm-20261021/reach/`:
- `bidirectional-interpolation-variational-propagated-centre.glsl`
- `bidirectional-interpolation-variational-propagated-energy-centre.glsl`
Census (identical for both): +69 / -9 lines; two new `//!TEXTURE` storage images (CENTRE_S_AB, CENTRE_S_BA, 240 x 135
rgba32f); the fused coarse pass +18 lines (the texel's winner by cost among the zero, ring and temporal descents, stored;
zero on the flat block's early return); each 1/8 refine pass +20 / -4 (the centre read from the 3 x 3 coarse
neighbourhood, the four prior terms rewritten to `|ref - g_e|`). No pass added or removed (59 and 65 HOOKs). The rule: the
centre is the texel's own winner, faded in over 1.0-2.0 coarse texels of its length (1.5 the midpoint), where at least 5 of
its 8 coarse neighbours' winners lie within 1.0 texel of it; zero otherwise. With GLOBAL_SEED=1 the frame's shift is the
centre where it is non-zero and the local one fills its zero (built and checked as `check-global-centre.glsl`, not part of
tonight's gate). Checks: `prune_passes.py --check` 0 parse faults, 0 orphans on both; the cost lane's `compile_check.py`
(glslangValidator, every pass) 59/59 and 65/65 compile, as do the two committed controls.

**Commands** (one GPU job at a time; from `REPO/tests/probes/pan` and `REPO/tests/probes/limb`; `SHADERS` is a
space-separated list of paths, each scored in turn against the same hold and linear):

    R=REPO/shaders
    C=~/Developer/np-scratch/swarm-20261021/reach
    SHADERS="$R/bidirectional-interpolation-variational-propagated.glsl $C/bidirectional-interpolation-variational-propagated-centre.glsl \
             $R/bidirectional-interpolation-variational-propagated-energy.glsl $C/bidirectional-interpolation-variational-propagated-energy-centre.glsl" \
      ./pan.sh W3_wall_pan_ramp_alone
    # then, with the same SHADERS, one case per run (limb.sh scores inside the box that follows the limb; bench.sh's
    # whole-frame PSNR would be the still wall's, limb.sh's header):
    SHADERS="..." ./limb.sh K1_limb_sweep_wall ; SHADERS="..." ./limb.sh K2_limb_sweep_dark ; SHADERS="..." ./limb.sh K3_limb_sweep_wall_bright

**Readout and thresholds (W3, PSNR Y, the 36-41 px band; tonight's baselines from the same host):**

| base | baseline | reference (a perfect centre) | UP: the prior is the term | DOWN: the set is the limit |
|---|---|---|---|---|
| recommendation -> `-centre` | 17.60 | `-global` 22.5 | >= 19.6 (+2.0) | < 18.1 (+0.5) |
| `-energy` -> `-energy-centre` | 20.23 | `-global-cage-energy` 22.64 | >= 21.7 (+1.5) | < 20.7 (+0.5) |

Between the thresholds on either base: a secondary term; `leveltap.py` at 37 px before anything is built on it. More
than 0.5 above the reference: suspect the gate (a centre opening where the frame's gate refused). The 28-32 band should
move by under 0.5 on `-energy-centre`; more than 1.0 means the switch is doing more than re-centring. Bands under 20 px
within 0.3 on both bases (the gate is shut there). Secondary readout, the limb: K2 (dark wall) 36-48 px up 1 dB or more on
both bases (the prior was the only term there); K1 under 1 dB on the plain base, +1 to +3 on `-energy`; K3 held.

**The four outcomes:**
- **Both UP:** the prior seals on both bases. Next: the 42-case ladder for each `-centre` file against its own base
  (kill: any period or lattice case down more than 1.0 dB, or the capped mean down more than 0.15), then the switch is
  the owner's call for High (`-energy-centre`) and Low.
- **Plain DOWN, energy UP** (the emulation's expectation): on the plain file the alias inside the reach breaks the
  temporal chain and the set lacks the truth, so there is nothing to centre on; energy supplies the set. Path: the
  centre rides on energy; Low needs energy or a far candidate (proposal 2) before a prior can help it.
- **Plain UP, energy DOWN:** contradicts the +2.4 the frame centre buys on energy; the local gate (5 of 8, 1.0 texel,
  the 1.0-2.0 fade) is the first suspect. `leveltap.py` on both files before any change to the rule.
- **Both DOWN:** the prior is not the far-end term; finding 2 is refuted for W3 and the `-global-cage-energy` gain
  came from the candidate. Proposal 2 leads, the doubled first step its cheap precursor; nothing built until
  `leveltap.py` shows which candidate was present and which refused.
