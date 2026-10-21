# Lane mathematics: the document matches the code line for line except one equation, and the owner's own bench logs show the base is not time-symmetric (mirror phases differ by up to 34 dB on L1)

Date 2026-10-21. Paper only; no GPU job was run. Two CPU-only measurements were made ([M]), both from files that
already existed: a numpy check of one equation, and a per-phase split of the owner's bench logs for the base
(`~/np-build/bench/{L1_trans_8px,L2_trans_16px,L9_occlusion}/mac_v0.log`, written 2026-10-21 21:02 by the owner's
queue; the `_shader.glsl` beside them is byte-identical to `REPO/shaders/bidirectional-interpolation.glsl`, checked
with `cmp`). Scripts are in `~/Developer/np-scratch/swarm-20261021/mathematics/`.

## What I read

- `REPO/BIDIRECTIONAL-AS-MATHEMATICS.md` whole (752 lines).
- `REPO/shaders/bidirectional-interpolation.glsl` 1-1688 (all 22 passes: pyramid, scene-cut, coarse search, three
  refinements, sub-pixel block, medians, warp) and 2005-2017. Not the reading tail 1689-2004.
- `REPO/REPAIRS.md` 9-132 (second round: L1, L3, L2, L4, L7-L10) and 208-244 (first-round L1 and L4).
- `REPO/INSTINCT-STRATEGY.md` 1-130.
- `REPO/NFRAME-LIMITS.md` 545-600 (section 8, the prefilter refuted), 2974-3010 (the held anchor), 3836-3846 (temporal
  seed and reach), 4029-4036 (the agreement blend refuted), 5008-5020 (the comb and the prefilter again); the
  `grep -n -i refuted` listing in full.
- libplacebo as built here: `~/np-build/libplacebo/src/renderer.c` 416-487 (`find_fbo_format`) and
  `src/shaders/custom_mpv.c` 1578 (`roundf` on WIDTH/HEIGHT). `REPO/frame-mix-hook.patch` lines 137, 230-247.
- `REPO/tests/bench.sh` 28-78, `REPO/tests/analyze.py` 48-82, `REPO/tests/scenes.sh` 60-78, 100-112, 186-204,
  244-262, 354-362; `REPO/tests/gen_tridirectional.py` 98, 202-221, 383-392, 598-606; `REPO/tests/gen_variational.py`
  57, 305-307.
- Not read: ENERGY-TRANSFER.md beyond a grep of its MISSED lines, SHADERS.md, PRIOR-ART.md, TESTING.md, PROBES.md
  beyond the anchor row, the reading tail, the generated shaders.

## Findings

Numbered; the ones that change the story first.

**1. [M] The base is not time-symmetric: on L1 and L2 the output phases 0.2 and 0.6 are near-exact and 0.4 and 0.8 are
30 dB worse, while the linear mixer scores mirror phases identically.** `bench.sh` writes a per-frame `psnr` log and
`analyze.py` averages the dB over interpolated frames (lines 66-71: it drops phase-0 frames and `SKIP_STARTUP`
frames). Output frame $n$ at 60 fps from 24 fps has phase $t = \operatorname{frac}(0.4(n-1))$, so
$(n-1) \bmod 5 \to \lbrace 0, 0.4, 0.8, 0.2, 0.6 \rbrace$ (the same cycle NFRAME-LIMITS 2996 uses). Splitting the
owner's logs by that residue, steady state (frames 6-58; the first and last source pairs are discussed in finding 8):

| case | mode | $t=0.2$ | $t=0.4$ | $t=0.6$ | $t=0.8$ |
|---|---|---|---|---|---|
| L1_trans_8px | base | 79.9-80.4 | 46.3 | 79.8-80.9 | 49.1 |
| L1_trans_8px | linear | 36.48 | 34.54 | 34.54 | 36.48 |
| L2_trans_16px | base | 47.0-47.1 | 39.7 | 40.8 | 41.9 |
| L2_trans_16px | linear | 33.00 | 31.46 | 31.46 | 33.00 |
| L9_occlusion | base | 37.4-47.2 | 36.3-42.7 | 34.9-38.5 | 37.3-44.1 |
| L9_occlusion | linear | 32.6-34.5 | 31.0-33.5 | 31.0-33.8 | 32.6-34.5 |

(psnr_y, dB, per frame; `phase_psnr.py`, `phase_psnr2.py`, and the per-frame listing in the scratch folder.) The
linear control is symmetric to 0.01 dB under $t \leftrightarrow 1-t$, as a blend of two frames must be on a
constant-velocity scene. The base is not: on L1 every interior frame at $t = 0.2$ and $0.6$ is at the 80 dB ceiling,
every frame at $0.4$ is 46.3-46.4 and every frame at $0.8$ is 49.1, to a tenth, frame after frame. So L1's ladder
number (61.92 dB in REPAIRS L4) is the mean of two exact phases and two 46-49 dB phases, and L2's 41.75 is a four-phase
spread of 39.7-47.1. [J] A mirror phase swaps the roles of $A$ and $B$; an estimator that treated the two frames alike
would score them alike. The document says the output is a symmetric blend (§10.1) and that only $\mathcal F$, the
map from images to displacements, is asymmetric (§12.5: the $B \to A$ chain is unread). So the asymmetry lives in
the flow value or the flow field, not in the warp arithmetic. [J] On L1 the bad phases are exactly those where
$t \cdot 7.5$ is a whole number (3.0 and 6.0 px) and the good ones where it is a half (1.5 and 4.5), and 7.5 px is
$m = 10$ on the L4 lattice ($0.75 m$): the pattern has the signature of the lattice fraction interacting with the
quarter-texel bilinear read of the flow (§12.4), but I did not identify the mechanism on paper, and I stopped
digging (Felt, below). What the table does establish: the L4 finding ("scored on its lattice, not on its matching")
is phase-selective, and a per-phase readout is a free diagnostic the ladder has never used. See proposal P1.

**2. [M] The document's §12.6 is wrong on the $B$ side.** Line 736 says the $B$-side sampling error is "the same
expression with $1-t$ in place of $t$", i.e. $(1-t)^2 (\nabla\mathbf f)\mathbf f$. Solving the warp of lines
1683-1684 against the flow definition at line 1678 gives, to first order,

$$\mathbf x_A - \big(\mathbf p - t\,\mathbf f(\mathbf p)\big) = t^2 (\nabla\mathbf f)\mathbf f, \qquad
\mathbf x_B - \big(\mathbf p + (1-t)\,\mathbf f(\mathbf p)\big) = -\,t(1-t)\,(\nabla\mathbf f)\mathbf f .$$

Checked numerically (`warp_error.py`, a 1-D flow $f = 16 + 0.05x$): at $t = 0.2$ the exact $B$-side error is
$-0.166$ px, the corrected expression gives $-0.168$, the document's gives $+0.672$. The two errors have opposite
signs and equal size at $t = \tfrac12$, so in a region of flow gradient the two warped samples are pulled apart by
$t\,(\nabla\mathbf f)\mathbf f$ at time $t$: the shortcut makes a ghost, not a shift. The weighted size
$(1-t)t^2 + t \cdot t(1-t) = 2t^2(1-t)$ peaks at $t = \tfrac23$, not $\tfrac12$. This is a document error, not a
code error; the code is what the record measured. It would be visible only on scenes with a flow gradient (R1-R3,
the oscillations), which are not among the three logged cases.

**3. [R] Every `//!SAVE` texture is 16-bit float; the base's flows survive that exactly, the field shaders' do not.**
libplacebo allocates a hook pass's output with `fbofmt[comps]` (renderer.c 487), chosen by `find_fbo_format`
(429-435: 16-bit float first, 16-bit unorm after). So `LUMA_*`, `FLOW_*_AB/BA`, `SCENE_DIFF` and the median outputs are
r16f/rg16f, while the ten `//!STORAGE` caches are rgba32f (shader lines 164, 355, 474, ...). The document's §13 leaves
this open ("whatever precision libplacebo allocates"); it is settled. Consequences:
- With `SUBPEL_REFINE = 0`, $F_H = \tfrac38 m + k$ for integer $k$, $|F_H| \le 25.625$ texels, needs 8 significant
  bits; fp16 has 11. Every level's stored flow is exact ($F_E = \tfrac{3}{32}m + \delta$, $F_Q = \tfrac{3}{16}m + \ldots$).
  The rgba32f caches therefore carry nothing the fp16 readers can see; they could be rgba16f (a change, not mine to
  make; hand-off to the performance lane).
- With `SUBPEL_REFINE = 1` (every generated field shader, `gen_tridirectional.py` 218-221) the fraction is arbitrary and
  the stored flow is rounded to $2^{-7}$ texel ($\tfrac1{64}$ px) for $|F_H| \in [8, 16)$ and $2^{-6}$ texel
  ($\tfrac1{32}$ px) for $[16, 32)$. REPAIRS L10 found a $\tfrac1{32}$ px floor in the reading tail's output; this is
  the same floor one hop earlier, in `FLOW_H_AB` itself. Acceleration, a difference of two such flows, inherits it twice.
- Luma at r16f: a BT.601 dot of 8-bit values rounded to $2^{-11}$ near 1. The same rounding on both frames, so a
  perfect integer match still costs exactly 0. The 3x3 SADs and the 576-term scene-cut sum are fp32 in-shader: there
  is no fp16 accumulation anywhere in the base.

**4. [R] The document and the code agree line for line.** Every line number in the document (constants table,
§2 table, each section's header) points at the thing it names in the file as imported (the commit `be6fd30` it cites
is not in this repository's history, but the file matches). Checked equation by equation: the pyramid sample lands on
the corner of four texels when $s_\ell$ divides the frame (texel $k$ reads full-res $16k+7$ and $16k+8$: §3 ✓); the
contrast gate's $\max(0,\max) - \min(1,\min)$ is the loop's `lo = 1, hi = 0` (lines 235-243 ✓); the coarse scan keeps
`best_off` fixed within a round while `cand_best` advances (330-344 ✓ the document's $\operatorname{scan}$); the
penalty is on the whole displacement at S (337) and on the step at E/Q/H (626 ✓); seeds are `snap_texel` then `* 2.0`
(576, 815, 1028 ✓); the sub-pixel fit's two denominators and the unclamped self-reference bias (1151-1162 ✓); the
median's incumbent $10^{30}$ (1415 ✓); the warp's $t$-split (1683-1686 ✓); `mix_t` appears nowhere before line 1676
(§12.2 ✓). The $B \to A$ passes mirror $A \to B$ exactly, including the use of `LUMA_A_S_pt` for $B$'s pitch, which is
harmless because the two lumas share a size (375, 390, 426). Residual discrepancies, all small:

| # | Document | Code | Note |
|---|---|---|---|
| D1 | §12.6 line 736, $B$-side error | 1683-1684 | wrong, finding 2 |
| D2 | §13 "whatever precision libplacebo allocates" | fbofmt | fp16; finding 3 |
| D3 | §7 writes $F_H \leftarrow \mathbf d^\ast + \ldots$ as the stored value | SAVE is rg16f | the stored value is the fp16 rounding; matters only with `SUBPEL_REFINE = 1` |
| D4 | §1 "sizes rounded by libplacebo" | custom_mpv.c 1578 `roundf` | 1080/16 = 67.5 rounds to 68, finding 6 |
| D5 | §12.5 "`lum` at line 2011" | line 2011 | right; REPAIRS L6 says 2184, which is the pre-L2 file |
| D6 | §8 "$\mathbf v_0$ is always accepted first" | 1421 | true only if $\Phi_0$ is finite; it is (finding 5) |

**5. [R] The numerical path is NaN-clean by construction, with one door.** Every acceptance is a strict `<` against a
finite incumbent (338, 627, 1421, 1468), so a NaN cost is never accepted and a NaN luma yields the zero seed, not a NaN
flow. The one unconditional copy is the seed (`best_off = base_off`, 615, 704, 823, 912, 1036, 1244) and the median's
placeholder `best = v[4]`: a NaN in a parent flow texture passes straight down and through both medians (every
$\Phi_i$ becomes NaN, nothing is accepted, the centre is returned), and a single NaN texel also disables the median
for its eight neighbours. The only way a NaN enters a flow texture in the base is a cache read before a write, and
the patch (line 137: "very first dispatch always sees `pair_changed = true`") closes that. The temporal textures of
the propagated line and the reading tail's EMA (`mix`) are the real exposure; not in this file. Divisions: the
sub-pixel fit's are guarded (`dx > 1e-6`); `acc / 576` is fixed; nothing divides by a contrast. Normalisation over
clamped-out taps: none in the flow path (the SAD is unnormalised; the 24x24 scene-cut grid is wholly inside the
texture). The border bias that does exist: a candidate block pointing out of frame is scored against replicated
edge texels, and the 5x5 contrast window shrinks to 3x5 at the frame edge, so the gate fires more at borders. [J]
Harmless on the ladder (objects stay inside), untested on pans with content leaving frame.

**6. [R] Level sizes: the ladder is 1280x720, where every level divides exactly; 1080p does not.** 720/16 = 45,
1280/16 = 80, and 4K's 135 are exact. At 1080p libplacebo's `roundf` makes the S level 68 rows, a vertical pitch of
15.88 px, while the horizontal pitch is 16 px. The seed's `* 2.0` (576) then overstates vertical motion by 0.74 %
(135/68 against 2), about 0.12 px at 16 px/frame, which the whole-texel refinements cannot correct, and `length()` in
the S-level penalty mixes a 16 px unit with a 15.88 px one. [J] Invisible to the picture, visible to a field read at
1080p, and invisible to the 720p ladder by construction.

**7. [J] Ties and guards that are arbitrary and undocumented.** (a) The median breaks an exact $\Phi$ tie between
*different* vectors by scan order: top-left first (1417). The document says the centre is only a placeholder; it is,
so a symmetric 4-against-4 neighbourhood resolves up-left. (b) The coarse search, from $\mathbf d_0 = 0$, prefers axis
steps to diagonals through the penalty (intended) and, among equal axis steps, up before left before right before
down (331-335). (c) The sub-pixel guard `dx > 1e-6` is absolute (1153), unlike `TIE_MARGIN`, which the file argues at
length must be relative (281-289). The costs are fp32 sums of fp16-rounded luma, so a denominator of $10^{-6}$ with a
numerator of a few fp16 ulps gives a ratio that is pure rounding noise, and the clamp turns it into a $\pm\tfrac12$
texel ($\pm 1$ px) jump. Inert in the base; live in every field shader (`SUBPEL_REFINE = 1`).

**8. [M] The first and last source pairs are not the shader's.** In all three logs frames 59-60 match `hold`/`linear`
to the decimal (L1: 36.63, 31.30 in both base and linear) and frames 2-3 sit 10 dB under their phases' steady state on
L1 (35.74 and 37.34 against 46.3 and 49.1). `analyze.py` skips `SKIP_STARTUP` frames at the start but nothing at the
end, so frames 59-60 enter every case's mean: on L1 they take the dB mean down by about 1.3 dB. Not my lane to fix;
hand-off to the ladder lane with the numbers.

**9. [U] Sub-texel precision of the texture unit.** The coarse search's last two steps are $\tfrac{3}{32}$ and
$\tfrac{3}{64}$ texel. Vulkan guarantees only `subTexelPrecisionBits` $\ge 4$ ($\tfrac1{16}$ texel); at 4 bits the fifth
round samples the same position for $\pm\tfrac{3}{64}$ as for $\pm\tfrac1{16}$ and the fourth round's $\tfrac{3}{32}$
sits on a rounding tie. Most hardware reports 8 bits, at which every lattice point is exactly representable. I did
not query the M5 or the Arc.

**What propagates.** `gen_tridirectional.py` copies the base verbatim and flips the two `SUBPEL_REFINE` sites
(202-221; "search shape, TIE_MARGIN, regularisation, caching, medians -- inherited verbatim", 383-392);
`gen_variational.py` takes the base as `SRC` and rewrites anchored lines (305-307). So findings 3 (fp16 storage),
5 (the seed door), 6 (1080p pitch) and 7a/7b (tie order) are in every generated file; 7c (the absolute guard) is live
in every field shader; finding 2 is document-only; finding 1 is measured on the base alone, and whether the
variational line shares the phase pattern is [U] (its warp is copied, its flow is not). The propagated base is
hand-maintained (REPAIRS L9), so a base repair must be copied there by hand.

## Proposals, ranked

Mostly checks. Prior attempts are named; the refuted list is in the next section. Cost in GPU minutes is the
owner's; CPU work is mine or the ladder lane's.

**P1. Per-phase readout of existing logs, then one exact-flow control.** *Mechanism:* the `psnr` logs already hold
per-frame scores; splitting by $(n-1) \bmod 5$ costs nothing and shows whether a case's number is a phase mix.
Then re-run one case through `l4_variant.py`'s shader (the exact-16-px variant, REPAIRS L4) and split it the same
way. *Prior attempt:* none; L4 read the lattice but not the phases. *Prediction:* on every logged ladder case with a
moving object the base's mirror phases differ by more than 1 dB and the linear mixer's by less than 0.1; on L2 the
L4 variant scores all four phases within 1 dB of each other near 78 dB (its recorded case mean). *Kill test:* if the
variant keeps a mirror asymmetry above 1 dB the cause is the $A$-anchored field, not the lattice; if the asymmetry
vanishes it is the lattice value; if the base's asymmetry is absent on a case with a flow gradient (R1) the
mechanism is edge-specific. Inconclusive tips toward the lattice. *Cost:* CPU for the split; one case, about
10 s of GPU, for the control. *Rank 1.*

**P2. Correct §12.6 and test its consequence on a gradient scene.** *Mechanism:* finding 2; the ghost separation
$t(\nabla\mathbf f)\mathbf f$ and the weighted size $2t^2(1-t)$ predict the worst phase at $t \approx \tfrac23$ on a
scene whose flow has a gradient. *Prior attempt:* none; the document is the first statement of the term. *Prediction:*
on R1_rot_const the base's phase-0.6 frames score below its phase-0.4 frames by 0.5-2 dB after the lattice effect of
P1 is subtracted (R1 rotates at 2.56 rad/s, 150 px radius: the rim moves 16 px/frame with a gradient of about
$0.1$ per px, so the ghost at $t = 0.6$ is about 1 px). *Kill test:* 0.4 and 0.6 within 0.2 dB on R1 kills the term as
a visible effect (the document still needs its sign fixed); 0.6 worse by more than 0.5 dB confirms. Same kind as
P1 (a per-phase split); listed because the scene differs. *Cost:* the document edit is the owner's; one case of
GPU. *Rank 3.*

**P3. Query `subTexelPrecisionBits` on the M5 and the Arc.** *Mechanism:* finding 9; `vulkaninfo` prints the limit
without rendering. *Prior attempt:* none in the record. *Prediction:* 8 on both, clearing the hazard; 4 on either
would mean the coarse search's fifth round is sampling at the wrong offsets on that machine and the stored
$\tfrac{3}{64}$ lattice is fiction there. *Kill test:* the number. *Cost:* seconds, no render (the owner should
run it: it opens a Vulkan instance). *Rank 2.*

**P4. A numpy transcription of the document, compared with one GPU flow readout.** *Mechanism:* §13 says the
document "has not been checked numerically against the shader's output". Transcribe §3, §4, §5, §6 ($A \to B$), §8 and
§10 from the equations (not from the GLSL) in numpy with fp16 rounding at each SAVE; render L1 through `read_view 4`
(the raw flow, REPAIRS L10 shows its 1/32 px floor) and compare texel by texel. *Prior attempt:* `l4_coarse_fraction.py`
read the coarse lattice; nothing recomputed a flow. *Prediction:* identical to within the fp16 readback floor on more
than 99 % of texels; any texel outside it marks a line where the document and the code part. *Kill test:* a
systematic difference (a half-texel shift between levels, a wrong seed parent) kills the document at that section;
a scatter of ties within `TIE_MARGIN` is expected and not a kill. *Cost:* two to three hours of CPU writing, one
GPU case. Different in kind from P1-P3. *Rank 4.*

**P5. Perturb the sub-pixel guard on a field shader.** *Mechanism:* finding 7c; `tests/tieprobe.sh` already perturbs
every cost by a relative epsilon and counts frames that flip; run it on the tridirectional shader, where the guard is
live. *Prior attempt:* tieprobe on the base (shader comment 298-304), where the guard is inert. *Prediction:* at
$10^{-7}$ the base flips 0 frames (recorded); the tri shader flips more than 0, and the flips sit on flat-valley
texels where $|\mathrm{sub}| = \tfrac12$. *Kill test:* 0 flips at $10^{-7}$ and $10^{-6}$ clears the guard. *Cost:*
tieprobe's 240 frames, about 4 GPU minutes. *Rank 5.*

**P6. One 1080p vertical pan read raw.** *Mechanism:* finding 6. *Prediction:* a 16 px/frame vertical pan at
1920x1080 reads $16 \times 2 \times 68/135$ wrong, i.e. about 0.12 px low plus the lattice, where the same pan
horizontally reads the lattice alone. *Kill test:* no vertical-horizontal difference beyond the lattice. *Cost:* two
short renders. *Rank 6.*

**P7. Count exact median ties between distinct vectors.** *Mechanism:* finding 7a; read `FLOW_H_AB` before and
after the median on one case and count neighbourhoods with two distinct minimisers of $\Phi$. *Prediction:* under
0.1 % of texels on real footage, more on the ladder's flat squares. *Kill test:* a count above 1 % would make the
up-left preference a measurable bias. *Cost:* one render plus CPU. *Rank 7.*

Loops of a kind: P1 and P2 are both per-phase splits; P4 and P7 are both flow readouts. P3 and P5 differ in kind.

## Refuted entries checked

NFRAME-LIMITS section 8 (the box prefilter, built and refuted 2026-09-03; the aliased contrast is load-bearing;
lines 545-575 and 5008-5020): nothing here proposes a filter. Section 5's P6/P7 and the PB/PC/PE list (494-518):
not touched. The temporal seed as the pan's carrier (3838-3841, refuted) and the doubled coarse reach (3841-3846,
half-confirmed): not proposed. The agreement blend (4031-4036, refuted): not proposed. REPAIRS L2 (the snap,
retired, -0.99 dB) and L4's variant (not shipped, six cases down): P1 uses the L4 variant as a control only, not as a
candidate. The tensor fill (2716-2728) I did not read beyond the grep line. ENERGY-TRANSFER's MISSED steps were
grepped, not read; none of my proposals is an energy-channel mechanism.

## Hand-offs

- *Ladder lane:* finding 1 (the phase split is free and changes how L1/L2 read) and finding 8 (frames 59-60 are
  hold/linear frames inside every case mean; `SKIP_STARTUP` has no end-of-clip twin). Also: L9's source frames alternate
  integer and half-integer object positions (`300*T` at 24 fps; scenes.sh 244-248 says so), so on L9 the phase split
  is confounded with pair parity; L1 and L2 (192T, 384T) are clean.
- *Performance lane:* the ten rgba32f caches hold values that fp16 readers reproduce exactly (finding 3); rgba16f
  would halve their bandwidth at no loss in the base. Only a prediction; a change is the owner's.
- *Field/reading lane:* the fp16 floor of `FLOW_H_AB` under `SUBPEL_REFINE = 1` (finding 3) sits one hop before
  REPAIRS L10's floor; both should be subtracted from any field-precision claim below $\tfrac1{32}$ px.
- *Owner:* the §12.6 correction (finding 2) is a document edit; P3 is a one-line query on each machine.

## Felt

- Felt: unease, the document's "same expression with $1-t$" at line 736, medium; a backward warp is not symmetric
  in $t$. -> Derived both sides, then `warp_error.py`. Outcome: right.
- Felt: surprise, per-phase listing of L1 (80, 46, 80, 49 by phase, to a tenth, every cycle), high; the
  lattice. -> Tried to derive the phase pattern from a uniform 7.5/8.25 px flow; the uniform case comes out exact at
  every phase, so the mechanism is in the field, not the value. Outcome: open (P1 separates it).
- Felt: pull, keep deriving the phase mechanism, medium. -> Stopped after one block; wrote P1 instead. Outcome: open.
- Felt: push, the discrepancy hunt after the first 400 lines of code matched the document everywhere, low; a
  transcription this careful will not hide a wrong equation in its pass equations. -> Moved to the numerical path
  and libplacebo's allocation, where the document had left a gap. Outcome: right (finding 3).

## Verdicts

*Reasoned.* The document is a faithful transcription of the base: every cited line exists, every pass equation
matches, and the one error found is in its commentary (§12.6, $B$ side; corrected and checked numerically). The
code's numerical path is sound for the base: no fp16 accumulation, flows exact in fp16, NaN excluded by strict
comparisons and the patch's first-dispatch rule. The hazards are inherited by the generated family: fp16 rounding of
sub-pixel flows ($\tfrac1{64}$-$\tfrac1{32}$ px), an absolute guard in the sub-pixel fit, scan-order ties, and a
0.74 % vertical scale error at 1080p that the 720p ladder cannot see. The measured finding is finding 1: the base's
per-phase scores on L1 and L2 are a 30 dB bimodal mix where the linear mixer's are symmetric to 0.01 dB, so the
ladder's case means on the translations are averages of exact and lattice-error phases, and a per-phase split
(free, from logs that already exist) is the diagnostic the record has not run. Its mechanism is conjectured
(lattice fraction against the quarter-texel flow read), not shown.

*Gut.* Satisfying on the document, suspicious on the phases: a result that clean, frame after frame, is a lattice
talking, and the L4 variant's per-phase table will say so in ten seconds of GPU.
