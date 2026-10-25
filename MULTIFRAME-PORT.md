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

## Step 1, the real-footage half (2026-10-25, 19:06): three frames buy +0.03 to +0.13 dB on live action and CG, and cost 0.18 on cartoons

The content test's 40 windows, `INTERIOR=1`, the four new shaders beside the earlier tri and today's tiers (scores in
`~/np-scratch-int/content-20261023/scores-interior.json`; one alignment alarm, on the 10-23 Low label, not a shader in
this chain). PSNR Y, mean over segments:

| class (segments) | High | biprop | D1 tri - tri-noaccel | D2 tri-pic - tri | D3 tri-pic-noaccel - biprop | D4 High - biprop |
|---|---|---|---|---|---|---|
| film (10) | 34.17 | 32.06 | +0.028 | -0.009 | -0.000 | +2.11 |
| television (6) | 36.18 | 35.22 | +0.065 | -0.041 | -0.000 | +0.96 |
| anime (10) | 42.71 | 41.82 | -0.058 | -0.178 | +0.009 | +0.89 |
| western cartoon (8) | 29.18 | 28.65 | **-0.184** | -0.017 | +0.000 | +0.53 |
| CG (6) | 35.88 | 34.44 | **+0.125** | -0.024 | -0.000 | +1.44 |

**Against the predictions:** D1 within +-0.10 in every class: MISSED on two (CG +0.125, cartoon -0.184). D2 0.00 to
+0.30: MISSED (picture mode is slightly WORSE on real footage, -0.01 to -0.18: the sub-pixel refinement helps real
pictures even though it hurts the ladder's clean translation). D3 -0.10 to -0.40: MISSED (the tri's structure, its
full-resolution level and plain final pass, costs nothing measurable on real footage: within 0.01 dB everywhere). D4
reproduces the tier gap: PASS (film +2.11, CG +1.44, less on television and animation).

**So on real footage the whole gap between the tri and High is the lineage** (D4), the tri's own structure costs nothing
(D3), and the third frame's acceleration is a small real gain on live action and CG and a loss on cartoons, where
drawings held on twos make a held pair and a moving pair look like a change of speed. **The registered rule** (D1 of
+0.10 or more in any class: the full port first) **selects Form F**, the slot-keyed port, on CG's +0.125. Which window
it goes onto, the tri's or the quad's or the quint's, waits for step 1b (running): the owner expects more from four and
five frames, and the record's mechanism (a checkable acceleration) says the same. The cartoon loss is a pass line for
any form: the port must not take the acceleration where drawings are held (the cadence branch's held-pair test already
exists in the quad).

## Even windows are centred on the gap: why the quad is the natural home for High (2026-10-25, design note)

From `gen_quaddirectional.py`'s own window analysis: a four-frame window is always {k-1, k, k+1, k+2} at 24 -> 60,
**the straddling pair is slots 1 and 2 at every phase**, and the window changes exactly when the straddling pair does. A
three- or five-frame window re-centres as the output crosses mid-interval, so its straddling pair rotates within a
fixed window (the tri's slot-keying exists for that reason). Odd windows are centred on a frame (the anchor's symmetry,
which is what the quint's jerk stencil wants); even windows are centred on the gap being filled.

That changes the cost of a port. **Form Q, a quad-High:** High's whole estimator on the fixed straddling pair (1, 2),
cached by `pair_changed` exactly as in two-frame High (role and slot coincide), plus only the plain propagated chains on
the outer pairs (0, 1) and (2, 3), which feed nothing but the acceleration and jerk; High's final pass (cut gate,
support, gain) with the quad's cubic correction added. About High plus two plain chains (86 + roughly 2 x 13 passes),
not two or three Highs. The tri's Form F needs High on both its pairs; Form M stays the cheap past-side variant. The
held-pair test the cartoon loss calls for is already in the quad (its cadence branch's statistic). Which form is built
follows step 1b's numbers.

## Step 1b results, the ladder (2026-10-25, 19:29): `QUAD_MODE 1` is the best multi-frame form; the quint adds nothing over the quad

Capped headline means: biprop 38.28, **High 39.08**, quad 38.22, **quad-m1 38.24**, quad-pic 38.18, quad-pic-m1 38.14,
quint 38.22, quint-pic 38.17 (the tri forms as in step 1). The capped mean again hides the families; selected cases
(`~/np-scratch-int/port-20261025/ladder2.txt` has all 45):

| case | biprop | High | tri | quad | quad-m1 | quad-pic | quint |
|---|---|---|---|---|---|---|---|
| O1_osc_gentle | 48.06 | 50.31 | 52.08 | 52.20 | **52.37** | 50.90 | 52.20 |
| O3_osc_hard | 41.83 | 41.40 | 45.86 | 47.39 | **47.57** | 46.79 | 47.28 |
| O5_osc_textured | 41.87 | 42.49 | 48.38 | 48.72 | **48.99** | 48.20 | 48.76 |
| A7_accel_tex_a167 | 47.61 | 49.57 | 50.50 | **51.14** | 51.10 | 49.82 | 51.07 |
| L1_trans_8px | **77.59** | 75.32 | 70.72 | 70.49 | **77.55** | 77.28 | 70.43 |
| L2_trans_16px | **62.42** | 55.56 | 60.04 | 61.65 | 61.63 | 61.07 | 61.61 |
| L6_flat_large | **65.27** | 49.42 | 64.68 | 64.61 | 64.98 | 64.62 | 64.57 |
| V3x_stairs_cov_v12 | 27.24 | **45.14** | 22.20 | 20.08 | 19.90 | 20.09 | 19.69 |
| P1_stairs_along_v4 | 43.35 | **53.77** | 43.50 | 43.19 | 43.22 | 43.14 | 43.15 |

Over the oscillation family, against High: tri +4.01 dB on average (+1.77 to +5.89), quad +4.43, **quad-m1 +4.63 (+2.06 to
+6.50)**, quint +4.47. Over acceleration (A1-A7, F2) every form averages about -0.9 against High (High's lineage wins
A1-A3 and F2 by 2-4 dB; the multi-frame forms win A6-A7).

**Against the predictions:** (1) every quad and quint form at or above the tri on five of six oscillation cases: PASS
for the field forms (quad, quad-m1, quint: all six), MISSED for the picture forms (quad-pic under the tri on five); the
quint 1 dB above the quad on O3 and O5: MISSED (-0.11 and +0.04: the quint's symmetric quartic buys nothing here over
the quad's cubic). (2) quad-m1 losing at most half of quad's constant-velocity loss: PASS on L1 (quad -7.10 against
biprop, quad-m1 -0.04: the least-squares residual gate removes the false acceleration), MISSED on L2 (-0.77 and -0.79).
(3) no multi-frame form reaching High on stairs, prints or translations: PASS on stairs and prints, MISSED on the
translations, where **High itself is below the plain base** (L1 -2.27, L2 -6.86, L6 -15.85: High's lineage costs the
clean large translations what it wins elsewhere; the capped mean, at 40, does not see any of it).

**What it says for the port:** the quad in `QUAD_MODE 1` takes the oscillation prize without the tri's false acceleration,
and its straddling pair is fixed (the design note above), so **Form Q (High's estimator on the fixed middle pair, plain
chains outside, the least-squares quadratic with its residual gate in the final pass)** is the cheapest full port and the
best-placed one. A ported form must keep High's stairs, prints and acceleration wins AND the base's clean translations,
which High alone does not. The quad-m1 content run (real footage) is running; the quad and quint content scores are
already on disk.

## Step 1b results, real footage (2026-10-25, 19:35): four frames buy +0.11 to +0.21 dB on the same base, and nothing is lost on cartoons

`quad-m1` over the content test's 40 windows (`INTERIOR=1`; no new alarm), beside the family. Against the base each
shader is built on (biprop), PSNR Y, mean over segments:

| class | tri | quad | **quad-m1** | quint | (High - biprop) |
|---|---|---|---|---|---|
| film | +0.04 | +0.10 | **+0.11** | +0.10 | +2.11 |
| television | +0.12 | +0.19 | **+0.21** | +0.19 | +0.96 |
| anime | +0.10 | +0.13 | **+0.14** | +0.12 | +0.89 |
| western cartoon | -0.15 | -0.08 | **+0.01** | -0.08 | +0.53 |
| CG | +0.15 | +0.22 | **+0.19** | +0.22 | +1.44 |

(The tri's column includes its structure, which D3 found costs nothing; quad and quint likewise include theirs.) **The
four-frame least-squares form is the best multi-frame shader on real footage too**: +0.11 to +0.21 dB over its base on
live action, anime and CG, and the only form that does not lose on cartoons (its residual gate catches the held
drawings the tri reads as a change of speed). The quint equals the quad again. **If the gains add, a quad-High (Form Q)
would sit about 0.1 to 0.2 dB above today's High on real footage and about 4.6 dB above it on oscillation**, while
keeping High's stairs, prints and acceleration lead. That is the build this investigation points to.
