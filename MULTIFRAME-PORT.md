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

## Form Q, pre-registered (2026-10-25 19:47, the owner's word: "build Form Q ... pre-registered, full gate"; before it is built)

**What is built** (`tests/gen_quadhigh.py`, from two generated files and nothing hand-edited):
- **The whole four-frame least-squares quad** (`QUAD_MODE 1`, the propagated base, field settings as shipped): its three
  slot pairs' plain chains and full-resolution level, which feed only the acceleration fit.
- **Today's shipped High, every pass, renamed into the quad's middle pair:** each texture it defines takes an `HI_`
  prefix (so nothing collides with the quad's), its frame A reads become slot 1 (`FRAME1`) and its frame B reads slot 2
  (`FRAME2`). Its pair caches are keyed by `pair_changed`, which in a four-frame window changes exactly when the middle
  pair does, so every cache keeps its meaning. High's reading tail is not carried; the quad's is.
- **The final pass is High's** (the motion-aware cut gate, the support and agreement fallback, the warp along High's
  half-resolution flow) **with the quad's correction added to both warp coordinates**, `corr = s(1-s) a/2`, the
  acceleration fitted by least squares over the quad's three anchor flows and gated by its residual and round trips,
  exactly as the quad computes it. One new gate, the consistency check: the correction is taken only where the quad's
  plain middle-pair flow agrees with High's within 1 px (where High has repaired an alias the plain chain still has,
  the plain acceleration is meaningless, and the output is High's). A pre-pass packs the five cut statistics into one
  texture (a pass binds at most 16). Outside the interior windows (the straddling pair not slots 1-2: clip edges), the
  nearer source frame. Then `prune_passes` over the result.
- This is the conservative form: a superset of High wherever the correction is off. **Its cost is about High plus the
  whole quad**, not High plus two outer chains (the design note's estimate assumed High's own flows would feed the fit);
  the cheaper form, High's middle-pair flows in the fit and the quad's plain middle chain dropped, is the follow-up if
  this one passes.

**Instrument checks, before any science** (fail any and nothing is measured): it compiles and runs with no skipped hooks
beyond the quad's lead-in; with the correction forced to zero it reproduces today's High within 0.01 dB on every one of
the 45 ladder cases (the renaming, the frame shift and the final pass proven, not assumed).

**Tests** (Form Q against today's High unless stated):
- **T1, the prize:** the oscillation family O1-O6 up by 2 dB or more on average, every case up. KILL if the mean gain is
  under 1 dB.
- **T2, nothing of High lost:** no ladder case down more than 1 dB, capped headline mean not down more than 0.05.
- **T3, real footage:** the content test's 40 windows (`INTERIOR=1`), no class down more than 0.05 dB; predicted up 0.05
  to 0.2 on live action and CG, within +-0.05 on animation.
- **T4, the cage** C1-C4: none down more than 0.5 dB.
- **T5, cost:** frame time on libplacebo (and Metal if `gen_metal.py` translates it), reported against High's.
Predicted: T1 passes with about +4 dB (the bare quad-m1's lead over High on the family is +4.63, and High's flow should
not cost it); T2 passes; T3 passes small; T5 roughly twice High's time.

### Form Q's instrument checks (2026-10-25, 20:06, before any of T1-T5 is read)

**Compiles and runs:** 158 passes (High's 78, renamed, beside the quad's), one skipped hook at each end of a clip (the
four-frame lead-in), no compile or disable line; the prune removes nothing. **The zero-correction check, as registered
("within 0.01 dB of High on every one of the 45 cases"), FAILS as stated, for a reason found and proven before any
science was read:**
- On the 1-second ladder clips, Form Q with `QH_CORR=0` differs from High on the first three and last four outputs on
  every case (the four-frame window's lead-in, the builtin mixer drawing them, as for every four-frame shader) and on a
  few outputs after the lead-in on 22 cases (up to 0.81 dB on one frame of V3x): High's carried state (the alias carry,
  the global shift's memory) starts a few source frames later in Form Q, because its first windows are not full.
- **Proof that the renaming, the frame shift and the final pass are exact:** both shaders are deterministic (two runs
  each, bit-identical), and on 3-second renders of H1, A5 and V3x Form Q with the correction off is **bit-identical to
  High on every output from frame 10, 8 and 50 respectively to the end** (L1 on its 1-second clip from frame 8). One
  thing not isolated: on the 1-second clips of H1 and A5 a few scattered mid-clip outputs also differ slightly
  (0.01-0.1 dB), which the 3-second renders of the same scenes do not show.
- **So the check's form is amended** (here, before T1-T5): the steady-state bit-identity above is the proof of the
  build, and **every ladder reading of Form Q is made twice, against High and against Form Q with the correction off**
  (same window, same lead-in, so that difference is the correction and nothing else). The kill lines are unchanged and
  apply to both readings.

### Form Q on the ladder (2026-10-25, 20:09): T1 passes, T2 KILLS it on fast stairs

Three shaders in one tree (`~/np-scratch-int/formq-20261025/ladder.txt`). Capped headline means: High 39.08, Form Q with
the correction off 39.05, **Form Q 39.05**. Scored on the interior outputs only (frames 8 to n-8, the source instants
excluded, capped at 40), where the four-frame lead-in is out of it: High 38.489, zero 38.487 (every case within 0.07 dB
of High: the lead-in and warm-up explain the whole-clip difference), **Form Q 38.479**.

| reading | oscillation O1-O6 | best elsewhere | worst |
|---|---|---|---|
| Form Q - High, whole clip | **+2.03 mean**, every case up (+0.38 to +3.81) | A7 +0.95, A6 +0.73 | H2x -4.15, P3 -3.33, V3x -2.95 (lead-in in every case) |
| Form Q - zero, whole clip (the correction alone) | **+2.67 mean** (+1.15 to +4.04) | A7 +2.11, A6 +1.78 | **H2x -2.83, P3 -1.91, V3x -1.70** |
| Form Q - High, interior | +2.28 to +4.97 (O2-O6) | A7 +1.73 | **H2x -5.82**, P3 -1.35, V3x -1.33, V2x -0.81 |

**T1 PASSES** (mean +2.03 against the 2 dB line, every case up; against the zero form +2.67). **T2 KILLS** Form Q: three
cases down more than 1 dB on every reading, all fast stairs and bars (H2x, P3, V3x), where the correction itself does
the damage (it shows against the zero form, where the window is the same). The prediction of about +4 dB on oscillation also MISSED (+2.0
to +2.7; the bare quad-m1 had +4.6 over High, so High's own flow and warp carry less of the quad's gain than assumed).

**Why, located before any third try:** on fast periodic stairs the plain outer chains (slots 0-1 and 2-3) alias, and the
agreement gate looks only at the MIDDLE pair (plain against High), which agrees there; the acceleration is fitted from
aliased outer flows and bends a correct High warp. **A correction to this record's pre-registration:** it said the
correction was "gated by its residual and round trips, exactly as the quad computes it"; reading the quad's code, in
`QUAD_MODE 1` the least-squares residual is computed but only displayed (`TRI_DIAG 6`), never applied: the acceleration
is gated by the three links' round trips alone. So the measured-confidence signal that motivated choosing mode 1 is
not in the warp. **The next design** (not built): High's middle flow in the fit in place of the plain one (Form Q's
cheaper form, which also drops the plain middle chain), and the residual applied as a gate, so an outer flow that
disagrees with High's middle flow (an alias) shows as residual and turns the correction off. The cage, the content test
and the cost runs continue as registered (they inform that design).

### Form Q, T3-T5, and the verdict (2026-10-25, 20:20)

**T3, real footage** (the content test's 40 windows, `INTERIOR=1`, against today's High): film +0.024, television +0.080,
anime +0.002, western cartoon -0.041, CG +0.060 dB (SSIM within 0.0003 everywhere); best segment +0.26 (television),
worst -0.22 (a cartoon). **PASSES** its line (no class down 0.05), narrowly on cartoons; the prediction "up 0.05 to 0.2
on live action and CG" holds for television and CG and MISSES on film (+0.02); "within +-0.05 on animation" holds.
**T4, the cage** (whole clip, against High; the cage's rectangle): C1 -0.89, C2 -0.55, C3 -0.11, C4 +0.04 dB: **MISSES**
its 0.5 dB line on C1 and C2. These clips carry the four-frame lead-in too (the worst-frame column falls to 21.7 against
High's 29.1); an interior reading was not taken. **T5, cost** (720p, 24 -> 60, O5 from an ffv1 file, 120 outputs to null,
three interleaved rounds, one process timing all: the first timing script read the clock in separate processes and
returned nonsense, caught and re-run): over the linear blend, **High 27.1 ms an output, the bare quad-m1 52.7, Form Q
79.0** (2.9x High; predicted about 2x). Metal not measured (no translation attempted for a killed form).

**Verdict: Form Q is KILLED by T2** (the correction bends High's warp on fast stairs: H2x -2.83, P3 -1.91, V3x -1.70
against its own zero form), with T1 passing (oscillation +2.0 over High, every case up), T3 passing small, T4 missing
on the cage with the lead-in unresolved, and the cost at three times High. Nothing shipped changed. **What it showed:**
High's estimator runs exactly inside a four-frame window (bit-identical in steady state), the oscillation prize
survives the port at about half its bare size, and the failure is located: an acceleration fitted from plain outer
flows that alias where High's middle flow does not, with the quad's least-squares residual never applied. **The next
design** is written above (High's middle flow in the fit, the residual as a gate); it also removes the plain middle
chain, so it should cost less than this form. Not built (one kill on this line; the owner's call whether to go on).

## Form Q2, pre-registered (2026-10-27 15:52, the owner's word: "build the revised Form Q (High's middle flow in the fit, the least-squares residual applied as a gate, the plain middle chain dropped), pre-registered, full gate"; before it is built)

**What changes from Form Q** (`tests/gen_quadhigh.py`, `QH_FORM=2`; Form Q stays reproducible as `QH_FORM=1`):
- **High's middle flow in the fit.** The anchor's middle-pair displacement is High's half-resolution flow at the output
  texel (slot 1 -> 2 for anchor 1; its negative for anchor 2, the same at-the-output-texel convention High's warp and
  the quad's fit already use); the outer links (slots 0-1, 2-3) stay the quad's plain full-resolution flows. The
  middle link's round trip is taken as passed (High's own support fallback already blends where High fails).
- **The quad's plain middle chain dropped** (its 1/16 to full-resolution BC/CB passes and the agreement gate that read
  them), and the quad's reading tail not carried (it read the plain middle flows and would keep them alive through the
  prune); the cut statistics stay.
- **The least-squares residual applied:** the acceleration is multiplied by 1 - smoothstep(0.5, 1.0, r), r the fit's
  largest residual over the three displacements in pixels (computed in true pixels; the quad's diagnostic divides by
  the diagonal texel length). The 0.5-1 px scale is the agreement gate's, chosen before any number.

**The risk, stated before the run:** the record has the mode-1 residual equal to (3/11)|jerk| per texel (QUADDIRECTIONAL.md,
P4). Real oscillation has large jerk: on O3_osc_hard (44 px peak, six samples a period) the residual is of order 14 px, so
a 1 px gate is expected to turn the correction OFF on the fast oscillation cases, the prize, while turning it off on
the aliased stairs, the defect. **So one isolating variant runs in the same sitting** (one change per reading):
`QH_FORM=2 QH_RESID=0` (High's flow in the fit, the plain middle chain dropped, no residual gate). Shaders: High,
Q2 with `QH_CORR=0` (the paired zero form), Q2, Q2-noresid.

**Predictions:** Q2: the stairs cases H2x, P3, V3x within 0.5 dB of its zero form (the defect gone); the oscillation
gain over the zero form under 1 dB on O2-O5 and kept partly on O1 and O6 (gentle, small jerk): **T1 at risk of the kill
line (mean gain under 1 dB)**. Q2-noresid: oscillation at or above Form Q's (+2.67 over its zero form), the stairs still
down more than 1 dB (the aliased outer links are still in the fit). Cost: Q2 below Form Q's 79 ms an output.

**Tests:** T1-T5 exactly as registered for Form Q, the lines unchanged, read against High and against Q2's zero form.
One change from Form Q's practice, set now: every ladder and cage figure is ALSO reported on the interior outputs
(frames 8 to n-8), since the whole-clip figures carry the four-frame lead-in; **T4's line is judged on the interior**
(the cage's whole-clip figure reported beside it), T1 and T2 on both readings as before.

### Form Q2 on the ladder (2026-10-27, 16:14): the residual gate fixes two of the three stairs and keeps half the prize; P3 still kills it

Four shaders in one tree (`~/np-scratch-int/formq2-20261027/ladder.txt`). **Instrument check:** Q2 with the correction
off reproduces Form Q's zero-form pattern exactly (the same lead-in and warm-up cases, the same worst frames), so the
renamed High is again intact. Capped headline means: High 39.08, Q2-zero 39.05, **Q2 39.05**, Q2-noresid 39.04.

| reading | Q2: oscillation O1-O6 | Q2: cases down > 1 dB | Q2-noresid: oscillation | Q2-noresid: down > 1 dB |
|---|---|---|---|---|
| against its zero form, whole clip | **+2.60 mean** (+1.76 min) | **P3 -2.34** | +5.34 mean (+2.50 min) | H2x -5.57, P3 -2.89, V3x -2.53 |
| against High, interior | **+2.46 mean** (+1.27 min) | **P3 -2.77** (then V2x -0.66, H2x -0.56, V3x -0.25) | +4.97 mean | H2x -8.34, P3 -2.95, V3x -2.56 |
| against High, whole clip | +1.97 mean (+0.99 min) | P3 -3.76 and fourteen more | +4.71 | (the four-frame lead-in on every case: the zero form is down too) |

By case (interior, against High): O1 +1.27, O2 +2.01, O3 +3.13, O4 +2.07, O5 +3.31, O6 +2.95; A6 +2.12, A7 +2.19.

**Against the predictions:** the stairs within 0.5 dB of the zero form: V3x PASS (-0.29), H2x a hair over (-0.56), **P3
MISSED (-2.77)**. The oscillation gain "under 1 dB on O2-O5": MISSED, gladly (+2.0 to +3.3: the fit's residual on
those cases is smaller than the (3/11)|jerk| estimate suggested, or the gate's soft edge keeps part of it). Q2-noresid:
oscillation at or above Form Q's: PASS (+5.34 against Form Q's +2.67: High's middle flow doubles the prize), stairs
still down: PASS (H2x -5.57). **T1 PASSES** on the zero-form and interior readings (+2.60, +2.46, every case up); against
High on the whole clip it is +1.97, a hair under the 2 dB pass line and far above the 1 dB kill line (the lead-in).
**T2 KILLS Q2 on one case, P3_stairs_along_v12**, which the residual does not see: there the three links agree on a
smooth wrong curve (an alias consistent across all four frames, the attack L024 asked GPT for). Cage, content and cost
follow.

### Form Q2, T3-T5, P3 diagnosed, and the verdict (2026-10-27, 16:31)

**T3, real footage** (40 windows, `INTERIOR=1`, against today's High): film +0.014, television +0.080, anime +0.007,
western cartoon +0.003, CG +0.080 dB; worst segment -0.04, best +0.24; SSIM within 0.0003. **PASSES**, and on every
class at or above Form Q (cartoon +0.003 against Form Q's -0.041). Q2-noresid: film +0.075, television +0.200, CG
+0.176, anime -0.009, **cartoon -0.080** (it would fail the line). **T4, the cage**, judged on the interior as
registered: C1-C4 within 0.01 dB of High; cage.sh's own whole-clip table puts Q2 0.11 to 0.30 under High, exactly
equal to its zero form (the lead-in): the correction does nothing on the cage. **PASSES.** **T5, cost** (the same
method as Form Q, one process timing all): over the linear blend, High 25.3 ms an output, **Q2 59.8** (2.4x High),
Form Q 74.7 (the prediction "below Form Q" holds).

**P3 diagnosed** (Q2's own diagnostic modes, acceleration and the true-pixel residual on a 32 px scale, interior
outputs): on P3_stairs_along_v12 the warp's acceleration is non-zero on 7.8% of texels, **small** (median 0.60 px per
interval squared, 90th percentile 1.36), with residuals under the gate (median 0.33 px); on O3_osc_hard the real
acceleration sits on 0.5% of texels and is large (median 4.63). So P3 is NOT a period-sized alias agreed by all links
(the L024 guess was wrong): it is a **sub-pixel disagreement between two estimators**. At uniform spacing a = f_prev +
f_next, and with the outer links from the plain chain and the middle link from High, any systematic sub-pixel
difference between the two estimators on the same motion (here a clean 12 px/frame translation) becomes an
acceleration, consistent across the window and so invisible to the residual. A raised dead band would not separate it
cleanly: the acceleration cases' true values (A4-A7, 0.33 to 1.67) overlap it.

**Verdict: Form Q2 is KILLED by T2 on one case** (P3 -2.34 against its zero form, -2.77 interior), with T1 passing
(oscillation +2.6 over its zero form, +2.5 over High on the interior, every case up; A6 and A7 +2.1 and +2.2), T3, T4
passing, and the cost at 2.4x High. Nothing shipped changed. **Progress over Form Q:** two of its three stairs failures
fixed (H2x -5.82 -> -0.56, V3x -1.33 -> -0.29 interior), cartoons no longer down, a fifth cheaper. **What is learned:**
the fit must take all three links from ONE estimator. **The next design** (not built): High's estimator on the outer
pairs too (the slot 0-1 and 2-3 chains High's, not plain), so the fit sees no estimator bias; it costs about three
Highs (75-80 ms an output, Form Q's cost), and Q2-noresid's +5.3 dB oscillation prize says what a consistent fit might
keep. The owner's call.

## Form Q3, pre-registered (2026-10-27 17:26, the owner's word: "build Form Q3 (High's estimator on all three pairs so the fit sees one estimator), pre-registered, full gate"; before it is built)

**What is built** (`tests/gen_quadhigh.py`, `QH_FORM=3`; Forms Q and Q2 stay reproducible):
- **Three copies of today's High estimator, one per slot pair**, each renamed with its own prefix and frames: `HA_` on
  slots 0-1 (`HOOKED`, `FRAME1`), `HI_` on slots 1-2 (`FRAME1`, `FRAME2`, as in Q and Q2), `HC_` on slots 2-3 (`FRAME2`,
  `FRAME3`). Each window's three pairs are functions of the window, so every copy's `pair_changed` cache keeps its
  meaning; each copy keeps its own carried state. **None of the quad's plain chains remain.**
- **The fit, every link a High flow** at the output texel (High's own convention): anchor 1 takes slot 1 -> 0 as the
  negative of `HA`'s flow, slot 1 -> 2 as `HI`'s, and the composed far link through `HC`'s at the moved texel; anchor 2
  the mirror. High keeps no half-resolution reverse flow, so the round trips are not taken; instead **a link is believed
  only where its own High does not fall back** (the acceleration times 1 minus the larger of the outer pairs' support
  fallback weights, High's own formula), and the least-squares residual gate of Q2 (0.5-1 px, true pixels) stays on.
- The cut statistics from the three Highs' own (the middle pair's motion-aware verdict for the hold, the raw
  statistics for the acceleration's cut gates), High's warp and support fallback as in Q and Q2, then the prune.
- Same sitting: Q3, **Q3-noresid** (`QH_RESID=0`, the isolating variant again), Q3 with `QH_CORR=0` (the zero form),
  and High.

**Instrument checks** (before any test is read): it compiles and runs with the four-frame lead-in only; Q3's zero form
reproduces High's interior pattern as Q and Q2's did (it must, the middle copy and warp are unchanged); and on P3 the
diagnostic acceleration falls below Q2's (median 0.60 px on 7.8% of texels): if one estimator removes the bias, the
false acceleration should all but vanish.

**Predictions:** P3 within 0.5 dB of the zero form (the bias gone); H2x and V3x no worse than Q2 (each outer pair now
gets High's alias repairs); oscillation at or above Q2's (+2.60 over the zero form). **Q3-noresid** passes T2 too (with
one estimator, the stairs need no residual) and keeps most of Q2-noresid's +5.34. Real footage at or above Q2. Cost
about three Highs, 75-80 ms an output (High 25.3).

**Tests:** T1-T5 exactly as registered for Form Q and read as for Q2 (against the zero form and High; interior and
whole clip; T4 judged on the interior).

### Form Q3: results and verdict (2026-10-27, 18:09)

Four shaders in one tree (`~/np-scratch-int/formq3-20261027`). **Instrument checks:** Q3's zero form reproduces Q and
Q2's zero-form pattern exactly (the middle High and the warp intact; every copy reads its own frames, checked in the
generated file). **The registered P3 check FAILS:** with one estimator on all three pairs the false acceleration on
P3 does not fall, it rises a little (median 0.82 px per interval squared on 9.3% of texels, against Q2's 0.60 on 7.8%;
residuals again under the gate, median 0.32). So Q2's diagnosis, a bias BETWEEN two estimators, was wrong: High's own
flow varies from pair to pair by a fraction of a pixel on P3, and any acceleration estimate amplifies that. On P3 the
motion runs along the stairs' own edges, where a match is weakly constrained (the aperture problem), so that is the
likely source; not yet isolated.

| reading | Q3: oscillation O1-O6 | Q3: cases down > 1 dB | Q3-noresid: oscillation | Q3-noresid: down > 1 dB |
|---|---|---|---|---|
| against its zero form, whole clip | +1.80 mean (+0.82 min) | **none** | +3.70 (+1.51) | L2 -2.90, P3 -2.24, F1 -1.41, M2 -1.32 |
| against its zero form / High, interior | +1.94 mean against High (+0.79 min) | **L1 -1.65** (78.19 -> 76.54 dB), **P3 -1.06** | +3.74 | P3 -3.53, L1 -1.65, F1 -1.61 |

Stairs repaired against Q2 (interior, against High): H2x +0.28, V3x +0.12, V2x +0.02 (Q2: -0.56, -0.25, -0.66). A6 +1.68,
A7 +1.79. **T3, real footage:** film +0.033, television +0.100, anime +0.008, cartoon +0.004, CG +0.124 dB (worst segment
-0.07): PASSES, the best of the three forms; Q3-noresid gains more on live action (+0.17 to +0.24) and loses 0.36 on
cartoons. **T4, the cage:** equal to High on the interior on all four (whole clip within 0.3, the lead-in): PASSES.
**T5:** High 25.6 ms an output, Q2 59.9, **Q3 72.7** (2.8x High).

**Against the predictions:** P3 within 0.5 dB of the zero form: MISSED (-1.06 interior; the whole-clip reading is
within the line). H2x and V3x no worse than Q2: PASS. Oscillation at or above Q2's +2.60: MISSED (+1.80; the outer
links' fallback gate and the residual take more). Q3-noresid passing T2: MISSED. Real footage at or above Q2: PASS on
every class. Cost about three Highs: PASS (72.7).

**Verdict: Form Q3 is KILLED by T2 on the interior reading** (L1 -1.65, a loss at 78 dB that is a few hundredths of a
code value and invisible to the capped mean; P3 -1.06, just over the line), passes T2 on the whole-clip reading against
its zero form, misses T1's 2 dB pass line (+1.80) without reaching its kill line, and passes T3 and T4. Nothing
shipped changed. **Three forms, three kills, each narrower** (Form Q: three stairs cases to -2.8; Q2: P3 -2.3; Q3:
P3 -1.1 and L1 -1.65 at 78 dB). **What is learned:** the remaining false acceleration is pair-to-pair flow noise where
a match is weakly constrained, not estimator mismatch. **The next design** (not built; the loop-check rule stops a
fourth form on this line without the owner): take the acceleration only along directions the image constrains (the
local structure tensor of the anchor frame: along an edge, no acceleration), which is how optical-flow confidence is
usually handled, rather than any further gate on the fit.

## Form Q4, pre-registered (2026-10-29 09:18, the owner's word on the fourth form, "Yes, build it"; before it is built)

**What changes from Q3** (`QH_FORM=4`; Q, Q2, Q3 stay reproducible): **the acceleration is taken only along directions
the anchor frame constrains.** Two new passes compute the structure tensor (Förstner and Gülch, 1987; Bigün and
Granlund, 1987) of slots 1 and 2 from High's own half-resolution lumas: central-difference gradients, their products
summed over a 5 x 5 Gaussian window (sigma 1.5 half-resolution texels, about 6 px at full resolution). In the final
pass the anchor's tensor is decomposed into its two eigenvectors (across the local edge, along it) and the fitted
acceleration, in pixels, is kept along each eigenvector in proportion to smoothstep(1e-4, 4e-4, eigenvalue): the
minimum-eigenvalue criterion of Shi and Tomasi (1994), applied per direction. Along a clean edge (the small
eigenvalue under the floor) the along-edge component is dropped; on texture and corners both survive; on flat ground
both go (a flat region's warp is invisible). The floor is from noise, before any number: 8-bit quantization gives a
squared-gradient level near 6e-7 and real footage's grain (about two code values) near 3e-5, so 1e-4 to 4e-4 is 3 to
13 times grain. Applied after Q3's gates (outer fallback, residual) and before the clamp.

**Same sitting:** High, Q4 with `QH_CORR=0` (the zero form), Q4, and **Q4-noresid** (`QH_RESID=0`): if the false
acceleration was aperture noise, the structure tensor removes it at its source and the residual gate, which cost Q3
half its oscillation prize (+1.80 against Q3-noresid's +3.70), may no longer be needed.

**Instrument checks:** the zero form reproduces High's interior as Q-Q3's did; on P3 the diagnostic acceleration
falls well below Q3's (median 0.82 px on 9.3% of texels): **predicted under a third of the texels**; on O3 the large
accelerations survive (median above 1 px on the texels Q3 had).

**Predictions:** P3 within 0.5 dB of the zero form; L1's interior loss (-1.65 at 78 dB, a few texels at the moving
object's boundary) NOT fixed by this change (a boundary is a corner, both directions constrained): **T2 at risk on L1
for Q4**; oscillation kept at Q3's level or above; **Q4-noresid** keeps most of Q3-noresid's +3.70 and, with the
aperture noise gone, loses less on the stairs and L2 than Q3-noresid did. Real footage at or above Q3. Cost: Q3's
plus two cheap passes (under 75 ms an output).

**Tests:** T1-T5 as registered for Form Q, read as for Q2 and Q3 (against the zero form and High; interior and whole
clip; T2's line on both readings; T4 judged on the interior).

### Form Q4: results, the diagnosis corrected twice over, and a defect in Q2-Q4's build (2026-10-29, 10:06)

**Results** (`~/np-scratch-int/formq4-20261029`): the zero form reproduces the earlier zero forms. Q4 differs from Q3
by at most 0.04 dB on any ladder case and 0.09 on any real segment: **interior, against its zero form, L1 -1.65 and P3
-1.06 exactly as Q3; oscillation +1.94 (+1.80 whole clip); T2 KILLS it as it killed Q3.** Q4-noresid: +3.73 oscillation,
P3 -3.53, L1 -1.65, F1 -1.62. Real footage: film +0.027, television +0.094, anime +0.000, cartoon +0.005, CG +0.106
(Q4-noresid: cartoon -0.361). Cage: equal to High on the interior. Cost (this sitting, warmer): High 27.7, Q3 78.7,
Q4 78.3 ms an output. Predictions: P3 within 0.5 dB, MISSED; L1 not fixed, as predicted; Q4-noresid better than
Q3-noresid on the stairs, MISSED (identical).

**The instrument, calibrated** (the field-read rule, before reading any field number): the gray16le read the Q2-Q4
diagnostics used agrees with an in-graph rgb48le read to 0.0005 px; A7 reads 1.680 against its true 1.67 and A6
1.328 against 1.33; the signed field's background reads 0.5000. Every field number in this record stands.

**What the structure tensor did:** it removed almost all of the small false acceleration Q2 and Q3 were diagnosed on
(P3's texels over 0.5 px: 9.3% in Q3 -> **0.19%** in Q4; L1's 0.38% -> 0.03%), **and changed neither loss.** Those
texels were never the damage: at about 0.8 px the warp's dead band leaves a correction of a few hundredths of a pixel.

**Where the damage is, measured directly** (Q4 and its zero form against the truth, full 16-bit, interior outputs): Q4's
output differs from its zero form on 0.064% of P3's pixels and 0.003% of L1's; **the worst 0.01% of pixels carry 99% to
100% of the added error.** On P3 they lie on sharp vertical step edges (columns such as x = 920, y 245-293), where a
horizontal acceleration of about 1 px (median 1.05; the horizontal component 0.97) moves the edge enough to change the
column by about 2600 codes in 65535 (truth error 138 -> 2938). On L1 they lie at the moving object's boundary. **Their
timing gives the cause:** on L1 they occur ONLY at the phases where the anchor is slot 1 (s = 0.2 and 0.4: 3-55
pixels a frame; s = 0.6 and 0.8: none), and on P3 the anchor-1 phases carry 376-837 a frame against 16-197.

**The defect, in Q3 and Q4's build (their registrations included it):** for anchor 1 the fit's backward link must be the
slot 1 -> 0 displacement of the content at slot 1. Q3 and Q4 took it as the negative of HA's slot 0 -> 1 flow, which
lies on slot 0's grid, and read it at the slot-1 position: **a whole frame of motion away.** Wherever the flow changes
over that distance (an object's boundary, a stair's corner), the link takes the wrong content's motion. The quad's original reverse flows (F_BA,
F_CB) were on the right grids; High computes both directions too, and the prune drops the half-resolution reverse
chain because High's own warp never reads it. So "P3 is aperture noise" (Q3) diagnosed the harmless texels; Q3 and Q4's harmful ones are this grid
error. **Checked the same day, by phase, against the truth** (P3, full 16-bit, added error over the zero form's): Q3
0.30 / 1.25 at s = 0.2 / 0.4 (anchor 1) against 0.01 / 0.10 at 0.6 / 0.8 (anchor 2); Q4 the same. **Q2's damage also
sits at anchor 1** (1.53 / 3.51 against 0.50 / 0.37), but Q2's anchor-1 links were all on the right grids (the quad's
plain F_BA, High's middle flow, the plain F_CD at the moved texel; its anchor-2 backward link reads the middle flow
with High's own fractional-frame approximation, not a whole frame). So Q2's cause is NOT this defect and is not
isolated; the mix of plain outer flows and High's middle flow (Q2's own diagnosis, "estimator bias", made from the
harmless texels) remains the suspect. **The fix** (not built, the owner's call):
the reverse links from High's own reverse flows (`FLOW_H_BA` of the HA and HI copies, generated unpruned and pruned
again after assembly), each on the right grid; everything else as Q3. It costs two half-resolution reverse chains.

## Form Q5, pre-registered (2026-10-29 10:12, the owner's word: "Yes, build the fix"; before it is built)

**One change from Q3** (`QH_FORM=5`): the fit's backward links come from High's own reverse flows, each on the grid
it is read on. The HA and HI copies of High are taken from High generated UNPRUNED (the same switches as the shipped
file, `PRUNE=0`; the shipped prune drops the half-resolution reverse chain only because High's warp never reads it,
so the forward flow and everything else are unchanged), and the assembled shader is pruned again. Anchor 1's backward
link is HA's slot 1 -> 0 flow at the output texel (slot 1's grid); anchor 2's backward link is HI's slot 2 -> 1 flow
(slot 2's grid) and its composed far link HA's slot 1 -> 0 flow at the moved texel. The forward links, the gates
(outer support fallback, residual), the warp and the cut statistics are Q3's exactly. Same sitting: High, Q5's zero
form, Q5, Q5-noresid.

**Instrument checks:** the zero form reproduces the earlier zero forms; and **the localisation that found the defect,
repeated**: on P3 (16-bit, against the truth, added error over the zero form's, by phase) the anchor-1 phases fall to
the anchor-2 level (Q3: 0.30 / 1.25 at s = 0.2 / 0.4 against 0.01 / 0.10 at 0.6 / 0.8); on L1 the added error at
anchor 1 vanishes. If they do not, the grid error is not the whole cause and the run is read as such.

**Predictions:** L1 and P3 within 0.5 dB of the zero form on every reading (T2 passes); the oscillation gain at or
above Q3's (+1.80 over the zero form, whole clip): with the backward links right the residual gate should reject less;
**Q5-noresid passes T2 as well** if the grid error was the stairs' cause too (Q3-noresid lost 2.2-2.9 on L2, P3, F1,
M2), and keeps more of the oscillation prize (Q3-noresid +3.70); real footage at or above Q3; cost Q3's plus two
half-resolution reverse chains (under 85 ms an output in Q3's sitting conditions).

**Tests:** T1-T5 as registered for Form Q, read as for Q2-Q4.
