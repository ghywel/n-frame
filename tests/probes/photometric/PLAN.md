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
