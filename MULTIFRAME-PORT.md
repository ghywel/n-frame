# Porting the High lineage up the multi-frame family, starting with the tri

*Opened 2026-10-25 at the owner's word: "It had not really occurred to me that we have not been porting our techniques
in the bidirectional up the chain to the higher frame variants. The > 2 frame shaders are practically sitting bare ...
Can we start with an investigation into the 3-frame shader, see what can be moved up and how that improves its
performance, particularly vs the bi-directional High." The same day's measurement (NFRAME-LIMITS.md, "The multi-frame
family against today's tiers") put today's High 0.6 to 2.1 dB above the tri on every class of real footage, and the
tri under Low too.*

## What the tri is today, read from its generator (`tests/gen_tridirectional.py`)

- **Its base is the plain propagated two-frame shader** (`bidirectional-interpolation-propagated.glsl`, 28 passes), not
  any tier. High (86 passes) is that base plus thirteen generator switches (`gen_variational.py`, `global_gain.py`,
  `bar_redecide.py`): the variational refinement and medians at 1/4 and 1/2, the global seed, the coherence gate, the
  coarse texture energy, the alias basins and their carry, outline adoption, the print lattice, the motion-compensated
  cut statistic, the global gain, and the prune. None of it is in the tri.
- **It was built as a field instrument, not a picture shader.** The generator turns sub-pixel refinement and its
  self-referenced fit on (off in every picture base: "fractional flow only costs it resampling sharpness") and adds a
  full-resolution level, both for the acceleration field's sake.
- **Its final pass is a plain warp** of the straddling pair plus the quadratic correction 0.5 a s(1 - s): no occlusion
  handling, no support or agreement test, no motion-compensated cut gate, no gain compensation. High's final pass has
  all of these.
- **It is slot-keyed**: four adjacent-slot flows (F01, F10, F12, F21), each a full copy of the base's flow chain, because
  the straddling pair's roles rotate inside a fixed three-frame window and a role-keyed cache goes stale (the generator's
  own history). Porting High the same way means one full High estimator per slot pair: about twice High's passes and
  time, unless the sticky cache (patch stage 2) or a stored previous pair carries one of them over.

## Step 1: where today's gap comes from (pre-registered 2026-10-25 18:30, before any of it runs)

Six shaders in one sitting on the M5 (`~/np-scratch-int/port-20261025`): today's High; the plain propagated base
(`biprop`, the tri's own base); the tri as shipped; the tri with its acceleration term zeroed in the output warp
(`tri-noaccel`, the warp's `accel_w` set to zero, the field and diagnostics untouched); the tri in picture mode
(`tri-pic`, sub-pixel refinement and its self-referenced fit off at all eight sites); and both (`tri-pic-noaccel`).
Each runs the 45-case ladder (`bench.sh all`, capped means) and the content test's 40 windows (`content.py`,
`INTERIOR=1`). The chain reads, link by link:

| link | difference | what it isolates |
|---|---|---|
| D1 | tri - tri-noaccel | the acceleration term itself: what three frames buy on this base |
| D2 | tri-pic - tri | the field-mode sub-pixel refinement's cost to the picture |
| D3 | tri-pic-noaccel - biprop | the tri's structure without acceleration: the full-resolution level and its plain final pass, against the base's |
| D4 | High - biprop | the High lineage on two frames |

**Predictions** (from the record: the 09-04 real-footage tie, the acceleration ladder cases, the base's comment on
fractional flow):
- **D1 on real footage: within +-0.10 dB in every class** (predicted 0.00 to +0.08); on the ladder, +1 dB or more on most
  of the acceleration cases (A1-A7, F2) and within 0.2 dB on the constant-velocity cases.
- **D2: 0.00 to +0.30 dB** on real footage (picture mode sharper); within 0.3 on the ladder.
- **D3: -0.10 to -0.40 dB** on real footage (no occlusion or cut handling in the plain final pass).
- **D4 reproduces the tier gap**: High 1.3 to 2.1 dB over the base on film and CG, less on television and animation.

**What decides the next step** (fixed now): a ported tri can at best be about High + D1 on real footage, if the gains
add. **If D1 is at most +0.05 dB in every class**, three frames add nothing High lacks on real footage and the full
slot-keyed port (twice High's cost) is not justified for it; the port is then aimed at the acceleration content the
ladder holds, in its cheapest form (High's estimator once, the other pair's flow from storage or from the sticky cache),
and judged on the ladder and the cage. **If D1 is +0.10 dB or more in any class**, the full port is built first. Between
the two lines, both forms are designed and the cheaper is built first.

## Step 2: the two forms of a tri-High (designed while step 1 runs; which is built first follows step 1's rule)

**Form M, "High with a memory" (cheap, new).** A three-frame trajectory needs two adjacent flows out of one anchor
frame. A two-frame High caches its pair's fields in storage: A -> B at every level, B -> A down to the 1/4 level (the
prune drops the half-resolution B -> A chain, which the final warp does not read). Keep the previous pair's last B -> A
field when the pair changes: it lies on the previous B's grid, which IS the current A's grid, so at the next pair the
anchor A has both flows on its own grid without transport, **a = F_prev(B -> A) + F_cur(A -> B)**, the tri's anchor
formula with the anchor fixed at A (the past side). The stored field is the 1/4-level B -> A (after adoption; the
acceleration is smooth and the tri deadbands it anyway), or the half-resolution A -> B carried over and inverted by a
fixed-point lookup; which one is a build-time measurement. The window stays two frames; the third frame comes
from memory, the effects work's storage lesson turned back on interpolation. Cost: two or three small passes ahead of
the flow chain (on `pair_changed`, copy the outgoing pair's B -> A field, its A -> B twin for the round trip, and a 1/16
luma signature of its B into storage), and the quadratic correction in High's final pass. **Validity:** the stored field
is used only where its pair's B signature matches the current A at 1/16 (a seek, a cut, the first frame of a clip or a
dropped frame breaks the match and the acceleration is zero: exactly High). Deterministic, seek-safe. What it gives up
against the full tri: the second half of each interval uses the past pair rather than the future one (the quadratic
through prev, A, B rather than A, B, next), and nothing about occlusion from the third frame.

**Form F, the full slot-keyed port (about twice High's cost).** `gen_tridirectional.py` generalised from "copy the
FLOW chains with the luma pair shifted" to "copy every pass that is a function of the pair": the gain, energy, alias,
global, propagation, adoption, print and support passes each get a slot 1-2 twin (SAVE names suffixed), the frame reads
shift HOOKED/NEXT to FRAME1/FRAME2, and High's final pass (cut gate, support, gain compensation) becomes the tri's,
choosing the straddling pair's fields by role and adding the correction. With the sticky cache (patch stage 2, a
variant until every host carries it) the slot 1-2 chain of one window is not the next window's slot 0-1 chain (the
names differ), so the cost stays about double.

**Tests for either** (written now, applied with step 1's numbers in view only for choosing which to build, never to
move a line): the 45-case ladder against today's High (no case down 1 dB; the acceleration cases A1-A7, F2 up), the
content test's 40 windows (no class down 0.05), the cage C1-C4 (none down 0.5), and cost on both engines.

## Step 1, the ladder half (2026-10-25, 18:53): the third frame's prize is oscillation, and High has none of it

45 cases, the six shaders in one sitting (`~/np-scratch-int/port-20261025/ladder.txt`). Capped headline means (42
scoreable cases): biprop 38.28, **High 39.08**, tri 38.25, tri-noaccel 38.32, tri-pic 38.20, tri-pic-noaccel 38.18. The
capped mean hides most of it (only 8 cases sit below 40 dB); by family, per case:

| family (cases) | D1: tri - tri-noaccel | D2: tri-pic - tri | tri - High | tri-pic - High |
|---|---|---|---|---|
| oscillation O1-O6 (6) | **+3.27 to +6.40** | -1.23 to -0.40 | **+1.77 to +5.89** | +0.55 to +5.41 |
| acceleration A1-A7, F2 (8) | -0.14 to +2.56 | -1.18 to -0.09 | -3.75 to +1.72 | -3.84 to +0.56 |
| translation L0-L9 (10) | **-7.15** to +0.92 | -1.42 to **+6.72** | -4.60 to +15.26 | -3.55 to +15.28 |
| stairs and bars P, V, H (13) | -1.64 to +0.08 | -1.07 to +1.31 | -22.94 to -0.52 | -22.94 to +0.79 |
| prints and rotation M, R (7) | -0.43 to +0.10 | -0.08 to +0.88 | -4.27 to +5.49 | -4.30 to +6.37 |

**Against the predictions:** D1's "+1 dB or more on most acceleration cases" MISSED (2 of 8: A6 +2.01, A7 +2.56); its
"within 0.2 dB on constant velocity" MISSED (L1_trans_8px -7.15, L2 -2.32: the field-mode sub-pixel refinement reads
false acceleration on a clean translation; in picture mode the same term costs L1 0.15 dB). Not predicted at all: **the
oscillation family, where the acceleration term is worth 3.3 to 6.4 dB and the bare tri beats today's High on all six
cases** (O5_osc_textured 48.38 against 42.49). D3 on the ladder: tri-pic-noaccel equals biprop within 0.01 dB on 41
of 45 cases (the a = 0 degeneracy holds); its structural losses are V3 and V3x (-3.1, -4.4), the tri's full-resolution
level on fast stairs.

**What the ladder says for the port:** the tri and High are good at different things. High's lineage owns the stairs,
prints and periodic texture (V3x 45.14 against the tri's 22.20; P1 53.77 against 43.50) and the translations; the third
frame owns oscillation and part of acceleration. A tri-High is worth building if it keeps both, and the oscillation
cases are its pass line. The content half (real footage) decides which form first.

## Step 1b: the same decomposition on the quad and quint (pre-registered 2026-10-25 18:56, before it runs)

The owner, on the ladder half: "very early on in this project we moved from 3 frame to 4 frame because the maths showed
we couldn't do what we needed with 3 (4 it follows isn't symmetric, 5 is again. So i expect to see more interesting
results in 4-frame and 5-frame)". The record agrees on the mechanism: three frames' one redundancy constrains the sum
of the flows, not the acceleration, so the tri cannot check its acceleration (QUADDIRECTIONAL.md); the quad's
`QUAD_MODE 1` spends its extra measurement on a least-squares quadratic with a per-texel residual (a measured
confidence), and the quint's symmetric window cuts the quad's under-read of fast oscillation (-8.8% at six samples a
period, 3-6x better at eight and fewer; QUINTDIRECTIONAL.md). Shaders, the ladder in the same tree as step 1: `quad` (as
shipped, `QUAD_MODE 0`, the exact cubic), `quad-m1` (`QUAD_MODE 1`), `quad-pic` and `quad-pic-m1` (sub-pixel refinement and
its self-referenced fit off at all twelve sites), `quint` (as shipped) and `quint-pic` (off at all sixteen). The a = 0
degeneracy was shown for the tri (41 of 45 cases within 0.01 dB of the base) and is not re-run.

**Predictions:** (1) oscillation O1-O6: every quad and quint variant at or above the tri on at least five of six cases;
the quint above the quad by 1 dB or more on O3 and O5 (the fast cases). (2) Constant velocity L1-L2: `quad-m1` loses
at most half what `quad` loses against biprop (the residual gate suppressing false acceleration); the picture forms
lose less than the field forms, as the tri did. (3) Stairs, prints, translations: no multi-frame form reaches High
(the estimator, not the window). The content test follows for the two best forms on the ladder, chosen by the capped
headline mean and the oscillation family together, not by any single case.
