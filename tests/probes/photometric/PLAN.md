# Brightness changes the matcher reads as motion: the defect, and two fixes planned

Local, 2026-10-23, after GPT's bounded footage prospecting (`tests/probes/prospect/RESULTS.md`, CHAT-LEDGER.md
G021-G024). The owner's ask: "check in with its update and plan some fixes for any real defects found."

## What GPT found, and what Local reproduced (measured, the M5)

GPT's five 300 s windows (18,129 withheld frames) left two strong native-size leads where the shipped High tier is
worse than a plain linear blend: **TV 73** (a toaster's brushed-metal grille, nearly still, 1440x1080 at 25 fps) and
**cartoon 6525** (a fade-in on a colonnade, 1280x720). GPT kept the cartoon out of its pure-motion leads because a
global brightness fit explains 93% of its change; it is still a case where High loses to the blend. Secondary leads
(anime 4649, CG 797) are confounded by drawing timing and pose; film 4991 is under the effect floor. Not planned here.

Local's rerun, `withheld.py` on GPT's own native windows (luma; GPT's SSIM8; the worst 16x16-grid cell):

| withheld frame | linear | High | Low | High + BAR_BASIN |
|---|---|---|---|---|
| TV 73 (frame 39), PSNR / worst cell RMS | 41.08 / 11.6 | 35.52 / 36.3 | 33.67 / 55.1 | 35.56 / 36.0 |
| cartoon 6525 (frame 37), PSNR / worst cell RMS | 41.41 / 8.6 | 36.40 / 13.7 | 35.28 / 13.3 | 36.63 / 13.4 |

GPT's losses reproduce (5.6 and 5.0 dB here, 5.8 and 5.1 there; luma conversion differs). **High's flow on the
nearly still toaster** (`flowtap.py`, the split-encoded tail calibrated by a known +6 px pan of the same frame: textured
toaster median +6.07, 93% within 1 px): zero almost everywhere, but a patch over the grille's upper face carries
vectors of median 6.6 px, mixed in direction, both along the brushed stripes (median 8.5 px) and across them (6.8 px).
The bars pass does not repair it (35.56 against 35.52): this is not the C3 regime.

**The defect isolated:** one frame of each shot, still, under a pure fade (`fade.py`, `mkfade.sh`: brightness x1.06
per decimated pair, no motion anywhere, the truth flow exactly zero, a full-rate reference made from the same fade):

| still picture, pure fade | linear | High | Low | High's invented flow |
|---|---|---|---|---|
| TV still | 52.90 dB | 49.03 (-3.9) | 48.28 | 46% of pixels over 1 px, 21% over 3 px, p99 13 px |
| cartoon still | 52.79 dB | 50.83 (-2.0) | 49.16 | 32% over 1 px, 8% over 3 px, p99 7 px |

**High's matcher is not brightness-invariant:** a change of brightness with no motion is read as motion, and where
the picture is finely textured the warp then deforms it. The SADs compare raw luma and the texture-energy channel
(`sad5x5_s` and its kin at every level); a search of the shader found nothing that compensates a gain or an offset. (The record's one test of a brightness-invariant cost, TESTING.md's
zero-mean SAD of August, replaced the data term wholesale, with the regulariser zeroed, on content with no brightness
change, and lost; it says nothing about compensating where brightness does change.)

## The two fixes

**F1, GLOBAL_GAIN (the cartoon's kind: fades, global lighting).** Estimate one luma gain and offset per source pair,
B = g A + b, at the coarsest level, robustly (a least-squares fit over the 1/16 grid with the worst residuals trimmed,
so moving objects do not drive it), and apply its inverse to B's luma wherever the matcher and the variational data
term read it, at every level. The output still mixes the original frames, so the picture's own fade is the blend's.
On a pair with no brightness change g = 1, b = 0 and the matched luma is unchanged; the structural risk is a moving
smooth ramp, where translation and an additive change are the same image change (GPT, RESULTS.md: on I = a x + b,
I(x - vt) = I(x) - a v t), so the fit must be trimmed and the ramp control below must hold.

**F2, a local zero-motion test (the toaster's kind: highlights sliding on metal, local light).** F1 cannot fix it: a
global affine fit explains only 10-15% of TV 73's change. Where the final flow is over a pixel, compare the
mean-removed (zero-mean) 5x5 cost of the chosen vector with that of zero motion at half resolution; where zero explains
the patch as well within a margin, take zero there. Mean removal is used only in this one comparison, never as the
data term, so the August result is not contradicted. First step before building: tap COHERENCE_GATE's decision on TV
73, which exists to blend unwarped where the warp is wrong, and find why it stays closed; if a fix to its trigger does
the job, that is the smaller change.

Both are switches, off by default, byte-identical without them, in `tests/gen_variational.py` (the rule for any change
that costs render time).

## Pre-registered tests (written before either fix is built)

For each fix, on High (and on Low too, the fall-back that loses most):
1. **The isolated defect:** both pure-fade stills at gains x1.03, x1.06, x1.12 per pair. Predicted: F1 takes High
   within 0.5 dB of linear on all six and the invented flow under 1 px on 95% of pixels; F2 helps less (local tests on
   a global change) but by at least half the gap. KILLED if F1 misses on more than one.
2. **The real cases:** GPT's two native windows, the same withheld frames. Predicted: F1 recovers at least 3 of the
   cartoon's 5 dB and little of TV 73's; F2 cuts TV 73's worst-cell RMS by at least 30%. KILLED (for that fix's
   purpose) otherwise.
3. **Motion must survive (the controls):** a textured pan at +6 px/frame under the same fades (F1 and F2 must keep the
   motion: median flow within 0.3 px of +6, picture within 0.2 dB of High without the fade's error); a smooth
   horizontal luma ramp panning at +4 px/frame with no fade (F1's trimmed fit must not cancel it: flow within 0.5 px of
   High's own); the isolated pure-period seeds and C1-C4 not down more than 0.5 dB.
4. **No regression:** the 45-case ladder (none down 1 dB, capped frozen and headline means within 0.05); the content
   test's 40 windows (`tests/probes/content/content.py`; no class mean down more than 0.05); the build gate's five film
   segments level.
5. **Cost:** Metal per-frame time on the demo engine and from files, interleaved; F1 is one reduction pass and a
   multiply per luma read; F2 a few dozen fetches on moving texels. Reported, not gated; the owner decides adoption.

Not planned: the anime and CG timing leads (two endpoints cannot reveal a held drawing's schedule; GPT's own reading),
and any change to the prospector's frozen ranking.

## Results of F1 and F2, and F1b pre-registered (2026-10-23, 12:20, before F1b is built)

**F2 COHERENCE_ZM: KILLED by test 2** (TV 73's worst cell -29.4% against the registered 30%; +2.8 dB, SSIM .9847 ->
.9889). Not retuned. **F1 GLOBAL_GAIN=1: passes tests 1-3** (pure fades: invented flow 0% on all six, within 0.5 dB of
linear on five, the sixth at 65 dB where the error is a seventh of an 8-bit code; cartoon 6525 36.40 -> 44.45, over
linear by 3 dB; the textured pan under fades kept and improved; cage level) **and is KILLED by test 4**: the ladder's
translating bars and stairs fall H2x -4.61, V2x -4.24, V1 -1.27 on High (Low: H1 -7.66, V2x -6.01, H2x -5.51), and the
content windows' film class -0.15 (CG -0.12). The mechanism is GPT's identifiability attack (G025) in measured form: a
moving periodic pattern changes the 60 px cells' means with its phase, the trimmed fit finds a gain or offset that is
motion, and the "compensation" then corrupts the matching. Trimming cannot tell.

**F1b, GLOBAL_GAIN=2: the fit accepted only where it explains the frames.** The same fit, then a second grid pass
measures the frames' zero-motion difference over the same taps raw, |A - B|, and compensated, |A - (B - b)/g|, and the
gain is used only if the compensated difference is under GG_ACCEPT = 0.7 of the raw one; otherwise identity. Rationale:
under a fade the difference IS the brightness change and compensation removes most of it; under motion the difference
is motion and compensation removes little or adds. Known blind spot, by construction: a pure translating linear ramp is
accepted (its difference is exactly an offset; GPT's case), where every shader's picture is the same anyway; and a fade
combined with large motion may be refused (F1's pan-under-fade gain may be lost). No other change to F1.
**Pre-registered (before building):** the ladder first, since it killed F1: no case down more than 1 dB on High or
Low, capped means within 0.05 (KILL otherwise). Then the content windows: no class mean down more than 0.05 (KILL).
Then tests 1-2: the pure fades within 1 dB of F1's own figures on at least five of six, and cartoon 6525 at least +3 dB
over High (KILL otherwise). Then the cage and the film segments, level within 0.05. Predicted: all pass; the pan under
fade keeps under half of F1's gain.

## F1b results (2026-10-23, 12:30; the M5, one sitting with F1's)

**Every registered condition held.** Instrument first: on the two moving staircases that killed F1 (H2x, V2x) F1 read
a spurious gain of 1.215 and F1b refuses it (identity); F1b accepts the pure fade (1.060), the real fade-in (1.221)
and the pan under a x1.06 fade. Ladder (45 cases): worst L0 -0.05 (a static scene near 81 dB), every bars/stairs case
within 0.01, capped frozen and headline means identical to High's and Low's. Content windows: live action -0.047
(SSIM +0.0002), 2D animation +0.020, CG 0.000 on High; Low -0.049 / +0.015 / 0.000; the one window that moves is a
film segment (Pirates, 3787.7 s) at PSNR -0.75 but SSIM +0.0029, where the record's rule trusts SSIM. Tests 1-2:
identical to F1 on all six pure fades (invented flow 0%) and on cartoon 6525 (36.40 -> 44.45, over linear by 3.0);
TV 73 untouched (its change is local; F2 was the attempt at it, killed). Pan under fade: refused at x1.03 (the
difference there is mostly motion), kept at x1.06 and x1.12 (+6.9, +8.9 dB): my "under half of F1's gain" was
pessimistic. Cage C1-C4 identical to High and to Low. The build gate's five film segments: 33.82 / 0.9583, identical.
Cost, time from files, interleaved: High +5.3% (O5) and +4.6% (film); Low +10% and +4%. The four gain passes run
every output frame; caching them per source pair like the passes around them is the obvious saving, not yet made.
**Standing:** GLOBAL_GAIN=2 is a switch, off, byte-identical without it; adoption into the tiers is the owner's call.
The local case (TV 73, highlights on brushed metal) remains open: F2's direction gained +2.8 dB but missed its line.

## GPT's G026 counterexamples, run through F1b on the GPU (2026-10-23, 12:45)

GPT's G026 (11:50, `GPT-REVIEW.md`, `attacks.py`) reached the ledger before F1b was registered (12:20), but Local had not
read it; its cases were not among F1b's registered tests, and are reported here as found, not as a kill. Both rendered
on the M5 through `run.py` (truth +4 px a pair; the 32 px border, and with it the sheet's stationary strip, excluded
from the flow statistic):

| scene | linear | High | High + F1 | High + F1b | Low + F1b |
|---|---|---|---|---|---|
| ramp .15-.85 over 256 px, +4 a pair | 68.42 | 65.85, flow +3.75 | 65.81, flow 0 | 65.81, flow 0 | 65.81, flow 0 |
| moving exponential sheet, still strip | 67.71 | 68.40, flow +3.38 | 61.94, flow 0 | 61.94, flow 0 | 62.21, flow 0 |

F1b accepts both fits (sheet g 0.984; ramp offset -0.011): **its blind spot, confirmed: motion whose image change is
exactly affine is taken for light, and the flow is erased** (100% of the field more than 1 px from the truth, against
0% and 34% for High). The picture cost is -0.04 dB on the ramp and -6.5 dB on the sheet, both above 61 dB (a fifth of an
8-bit code value at most): invisible in Cadence's picture, wrong for anything that reads the flow (the human-reading
views, the acceleration field). An anchor that would close it: refuse the fit where the coarse search finds a
confident non-zero global shift with a low residual (GLOBAL_SHIFT exists in Standard and High); not built.

## Adopted (2026-10-23, afternoon, the owner's word: "adopt GLOBAL_GAIN=2 into the three Cadence tiers and their 4K twins")

The three `-cut` tier files regenerated with `GLOBAL_GAIN=2` (their headers record it; the names are unchanged, as with
PRUNE), the 4K twins by scale_shader.py (taught the wrapped read of frame B in the energy pass; both frames' energy taps
and the lattice's samplers checked scaled alike). The new High and Low files are byte-identical to the high+gain2 and
low+gain2 that passed the tests above; Standard + F1b, untested until then, was run the same afternoon: the six fades
fixed (invented flow 0%), cartoon 6525 36.40 -> 44.45, the ladder worst -0.01 with identical means, the content windows
live -0.045 (SSIM +0.0002), 2D +0.01, CG 0. A 4K fade (the TV still at 2880x2160) on the 4K twins: Low 50.78 -> 66.68
and High 52.02 -> 66.68 on libplacebo. smoke.sh 19/19 (its tier check now regenerates with GLOBAL_GAIN=2); all six
compile. The Metal side (the demo engine, QuadDemo --export, Cadence's new graphs from gen_metal.py): the TV fade High
51.71 -> 67.84 and Low 50.50 -> 67.84 (libplacebo 51.61 -> 67.73), the 4K twins 52.09 / 50.90 -> 66.77, cartoon
6525's whole window +3.36 (High, Standard) and +2.58 (Low); retained frames within 0.07 codes. lockstep.sh PASS
(4 min 16 s; it regenerated the demo's three affected graphs).
Cadence's six graphs rebuilt from these files (Low 47, Standard 67, High 86 passes; metallibs for all three platforms);
Metal cost (QuadDemo --bench, medians of five interleaved rounds): High +3.8% at 1080p / +1.6% at 4K, Standard +3.9 /
+2.0, Low +5.3 / +4.1. Cadence's mac-tests short 56 passed, 0 failed (one case skipped itself: the owner's own Cadence
was open). The upload is the owner's.
