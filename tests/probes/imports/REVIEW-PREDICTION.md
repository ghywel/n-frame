# GPT's attacks on the two open import designs

Written before running the new checks, 2026-10-25, against `24c5412` and Local L022.
This reviews proposed rules; it does not implement a third shader variant or reopen a killed one.

1. **History is not an identifiability fix.** A periodic strip translating uniformly can present a fixed,
   textured cell with moving-held-moving-held forever. Construct 48 source samples, test both a dense 32x32
   cell and the existing quad's 5x5, six-pixel-spaced taps. Predicted: every successive pair classification
   alternates, all 45 four-frame windows qualify, although displacement is constant every frame. Held
   differences are exactly zero, so contrast normalization cannot reject this example. Controls: a stationary
   textured patch must not qualify; a generic continuously moving texture must not alternate throughout.
2. **Coarse light-versus-motion ties are still undecidable.** On a translating affine ramp, the correct shift
   and zero motion plus an offset both have zero residual. The proposed "offset at least as good" rule selects
   light incorrectly. A textured pan and an actual additive light change are the opposite positive controls.
3. **LOCAL_LIGHT=2 has a coordinate issue to check separately from its measured kill.** Its grid measures a
   residual indexed in A, but its helper looks that grid up at B's coordinate. For known translation and a
   spatially varying additive light field, predict the leftover analytically and check it against direct
   image arithmetic. Correct inverse transport must remove it. Constant light and zero translation must
   mask the issue, providing the counterfactual controls.
4. **Unexpected side check, spectrum specificity.** A sinusoidal print at constant translation produces a
   temporal sinusoid at a fixed pixel. Removing a line does not remove that oscillation. Reproduce the
   spectrum shader's eight-sample detrending/DFT; predict nonzero energy for a uniform pan, zero for a
   constant/linear time trace. Hue is an energy-weighted bin index, not a measured single physical frequency.

Run CPU analytic checks first. Any GPU check must distinguish a predicate/measurement validation from a full
interpolator quality regression. Do not describe the unbuilt history or coarse competition as GPU-tested.
No thresholds will be fitted to these attacks. Raw results and optional videos belong in external scratch.

GPU follow-up registered after the CPU checks, before its render: run the **unchanged spectrum shader** on 16
frames of a grayscale period-16 print translating 4 px/source frame, and a constant gray control, 192x96 at
24 fps. Interior frames 4 through 11 must show mean RGB channel spread above .05 for the pan and below .005
for the constant. The grayscale input/fallback cannot produce the pan's colour, so this also checks execution.
Require successful commands, exactly 16 output frames and no shader-disable/compile failure. This tests the
existing spectrum's specificity, not either proposed interpolator fix.
