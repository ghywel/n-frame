# Imports to interpolation: what the effect shaders can give back

*Opened 2026-10-25, after BEYOND-INTERPOLATION.md, at the owner's word: "by exploring extra use cases like this we might
actually be able to bring science back in to our interpolation shaders ... a sequence of frames will always be temporal,
which is why i often title this project as 'N-Frame Temporal Shader Analysis' - so there is cross-pollination between
discrete techniques ... concentrate on this import back to interpolation."*

The first import happened by accident: the spectrum effect lit the toaster grille that GPT's prospecting had found as
High's strongest quiet-shot failure, and showed its light going back and forth, the change the matcher reads as motion
(BEYOND-INTERPOLATION.md). This record takes the other effects the same way: each idea becomes a measurable question
about the interpolators' own losses, answered cheaply on footage before anything is built.

## The diagnostics, pre-registered (written before any is computed)

Data: GPT's five 300 s prospecting windows (film, television, anime, western cartoon, CG; tests/probes/prospect/), each
with the original at 640 px wide, High's reconstruction of every withheld frame (the High of 2026-10-23, before
GLOBAL_GAIN) and the GPU blend. Only GPT's eligible withheld frames (not a cut, a hold, low signal or a boundary). Cells
are GPT's 16 x 16 grid. Features are computed from the **retained** frames only (n-5, n-3, n-1, n+1, n+3, n+5: what a
six-frame interpolator sees), never from the withheld frame itself. Tool: `tests/probes/imports/diagnose.py`.

**A target cell** is one where High is clearly worse than the blend: High's mean squared error over twice the blend's,
and High's RMS over 3 code values (visible).

**D1, a flicker cue (from spectrum.glsl).** Three cell features: *coherent change*, |mean dI| / mean |dI| over the five
retained pairs (1 when a patch brightens or darkens as a whole, near 0 when texture moves across it); *oscillation*, the
share of each pixel's temporal variance left after removing its straight-line trend, the cell's mean; and the control
*raw change*, the cell's mean |I(n+1) - I(n-1)|. A feature's **lift** is the target rate among the top 1% of cells by
that feature, over the window's base rate. A feature is a candidate gate cue if its lift is 5 or more on at least three
of the five windows AND beats raw change's lift there. Predicted: coherent change passes (photometric change is
spatially coherent; motion is not), oscillation fails (moving texture oscillates too).

**D2, mixed cadence in animation (from the strobe and ghost-town work).** Per adjacent pair of original frames, per cell:
*held* if its RMS change is under 1.0 code, *moving* over 3.0; a pair is *mixed* when at least 10% of the textured cells
(cell standard deviation over 4 codes) are moving and at least 10% are held, outside cuts. Reported per window as the
share of moving pairs that are mixed. Predicted: 20% or more in anime and cartoon, under 5% in film and CG (the control).
If so, per-region cadence (interpolating each region at its own drawing rate) has a target the player's whole-frame
cadence stage cannot reach.

**D3, a temporal-median fallback (from ghost-town.glsl).** In target cells, is the per-pixel median of the six retained
frames closer to the truth than High? Reported as the share of target cells where it is, against the same share over
all eligible cells. Predicted: 30% or more of target cells, under 5% of all cells; then a cue that picks those cells
(D1's, or an occlusion test) would let a plate replace a failed warp.

Each is a diagnostic, not a shader: a pass only says the import has a target worth building for.
