# Bounded real-footage prospecting — 2026-10-23

Five five-minute middle windows, five content types, **18,129 evaluable withheld frames**. No whole-video scan.
The strongest useful lead is a repeatable native-size TV grille/toaster reconstruction weakness. The scan also
exposed important false-positive mechanisms: illumination transitions, uneven drawing timing, and rapid rotation
that an unwarped-change threshold does not fully exclude. No shader or default was changed.

The raw top 20 errors in **every** source are all excluded: 100/100 across the five windows (92 cut-guard rows,
seven extreme-change rows, one boundary). Raw absolute-error ranking would indeed have trapped this run.
Relative ranking finds quieter candidates, but still needs source-triplet inspection; it is not a defect classifier.

Data and source identities: external `$NP_SCRATCH/prospect-20261023/`, private `sources.json`. Exact instrument:
[reconstruct.py](reconstruct.py), [review.py](review.py); usage [README.md](README.md), frozen rules
[PREDICTION.md](PREDICTION.md). M5/MoltenVK, FFmpeg `3a5eb94`, libplacebo `285d1cc`, two documented Metal environment
guards. High SHA256: `8d8cecce658d570fede309988f2b3478cae9618a5ea3f6741c152dccedb33faa`.

## Sampling and measurement

Reused the first commercial title in each class of Local's existing content manifest, then made **new** windows
centred at 50% runtime: 300 seconds of film, television, anime, western cartoon and CG. Purposive coverage, not a
random census or evidence about a whole content class. Source properties and requested seek times are in the
private manifest. One bounded input seek/decode per source; no audio/subtitles, whole-source hash, or end-to-end
NAS decode. Native FFV1 expansion was written locally. All subsequent work used local copies only.

Full-frame scans at width 640, never upscaled; native-size confirmations below. Reference/input rates 23.976/11.988,
or 25/12.5 for TV. Explicit even-length reference: four windows lose one terminal frame; TV loses none. The final
unsupported midpoint and first/last half-second are not ranked. Local frame indices are exact; quoted original
programme seek times are approximate to a source frame/container rounding. This is the harder doubled-motion
reconstruction task, distinct from normal-rate playback.

Three decoded streams are consumed by frame index. Counts must match; retained-frame RMS must be <= 2.55 luma code
values (40 dB). All five passed, worst retained RMS 0.755. All native packet intervals match their nominal rate
within millisecond rounding. TV has no field-order tag: a separate 125-frame centre idet sample gives 124 progressive,
one undetermined, no TFF/BFF in multi-frame classification. Supporting evidence, not a whole-window proof.

| source | frames compared | eligible midpoints | cut guard | hold/near-hold | low signal | extreme change | boundary | median eligible High gain over linear |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| film | 7192 | 1480 | 554 | 591 | 921 | 38 | 11 | +5.20 dB |
| TV | 7500 | 2022 | 254 | 340 | 1069 | 52 | 12 | +3.89 dB |
| anime | 7192 | 527 | 484 | 1990 | 569 | 14 | 11 | +4.83 dB |
| cartoon | 7192 | 2193 | 448 | 821 | 65 | 57 | 11 | +3.15 dB |
| CG | 7192 | 1742 | 405 | 629 | 763 | 45 | 11 | +2.88 dB |

Exclusive bucket priority: boundary, cut, hold, low, extreme, eligible. Separate overlapping counts are retained in
ranked.json. Total eligible: 7964 (43.9%). The 245 eligible midpoint flags satisfying both full-frame regression
thresholds are **not 245 defects**; neighbouring frames, drawing timing and transitions remain confounded. Likewise,
a maximum over 256 spatial cells is a selection statistic, not a calibrated local significance test.

Luma RMS uses 8-bit code values; PSNR = 20 log10(255/RMS). `ssim8` uses non-overlapping 8x8 luma blocks, population
moments and usual C1/C2 constants; it is **not ffmpeg's overlapping SSIM**. Spatial measurements use a 16x16 grid,
not fixed 16-pixel squares. Partial bottom/right cells are omitted from the grid statistic only. Full-frame RMS
uses all pixels; SSIM8 omits the final partial 8-pixel blocks. Robust rankings are not p-values.

## Native confirmation and inspection

Inspected the three relative and two absolute events per source, 25 sheet rows, then one selected native event per
source. Native windows preserve the original decimation parity, approximately three seconds each. High rendered
twice. The table's positive dB values mean **High is worse than linear** at the selected withheld frame.

| source / local frame | native size | loss to linear | SSIM8 High / linear | disposition |
|---|---|---:|---|---|
| film 4991 | 1920x800 | +4.35 dB | .9800 / .9917 | secondary only: High RMS 1.725 is below the frozen full-frame effect floor |
| TV 73 | 1440x1080 | +5.77 dB | .9880 / .9939 | best quiet-shot lead; local grille/rim deformation, mechanism unresolved |
| anime 4649 | 1920x1080 | +1.93 dB | .9668 / .9793 | shoulder/arm weakness; uneven drawing timing remains a confound |
| cartoon 6525 | 1280x720 | +5.08 dB | .9347 / .9796 | repeatable but photometric-transition dominated; exclude from primary pure-motion leads |
| CG 797 | 1920x804 | +2.35 dB | .9292 / .9594 | horn/foreground deformation; asymmetric pose/timing, secondary lead |

Film/TV/anime/cartoon repeated with identical decoded luma. CG did not: maximum whole-frame repeat RMS 0.556,
median 0.308 (consistent with the known small readback/dither variation; cause not newly isolated here). Its selected
loss repeats at +2.34649/+2.34674 dB and SSIM8 .929198/.929192, far smaller variation than the observed deficit.
No claim of byte identity across every channel or universal determinism.

**TV 73:** local worst-cell RMS 32.55 versus linear 9.70, excess 22.84; this is not a frame-wide noise-floor fluctuation.
The native crop shows the grille and surrounding ring's shape changing in High relative to the withheld original.
Nearby scan event 101 is the same shot. Global translation explains little of the source change (best adjacent fits
zero displacement); a global affine brightness fit explains only 10-15%. Local lighting/reflectance, periodic mesh
matching, and physical movement are competing explanations; no material-velocity ground truth is claimed.

Normal **25->60** context made from the full-rate native TV input by [playback.py](playback.py): High and linear,
178 frames each; 15 retained instants, worst RMS 0.344. Local `playback60/high-left-linear-right.mp4` is High on the
left, linear on the right. The context crop brackets output 93 with source 38/39 (alpha .75). There is no withheld
truth at this new instant. Distortion is subtler here; the preview supports human review, not a new accuracy score
or a confirmed production defect. All production claims remain open.

**Other inspected events:** film 1053/2647/2701/3045 are vigorous rotation/action, kept as hard-motion examples rather
than clean shader-defect leads. TV 183 and CG 4843 fail the .005 SSIM-loss criterion; TV 6613/6677 and CG 6659/6835
show High's advantage over visibly ghosted linear images. CG 6623 is vigorous foreground movement. Anime 2519 has a
changing light overlay; 3325 has translucent moving text; 1041 is large animated displacement; 3603 has glow/animated
shape effects and is not isolated. Cartoon 2721/2831 have multiple independently timed drawings; 3137's source A/B
are nearly the same pose, C jumps (adjacent RMS 2.51 versus 34.40), so it is an animation-timing confound. Cartoon
2293's wide architecture/weather shot remains secondary and unconfirmed at native size. None of these is silently
promoted to a shader bug merely because its metric is poor.

## A hypothesis broken by the independent witness

I initially read cartoon 6525 as a smooth architecture pan with tearing. [pan_witness.py](pan_witness.py), an
**exploratory post-discovery** check, challenged that explanation: an exhaustive integer translation search +/-24 px
with quarter-pixel local refinement gives A->B and B->C both (.25,-.25), but leaves RMS 7.28/7.23 against the
unwarped 7.34/7.30. Agreement between fitted displacements alone is not evidence of a good motion model.

A global affine brightness fit C = g A + b explains **92.94% of endpoint-change MSE**, g=1.14844, b=2.171,
residual RMS 3.83 against 14.42 unchanged. Adjacent gains 1.0893 and 1.0714 also show monotonic brightening.
This is photometric-transition dominated, not an established rigid-pan defect. Endpoint-only half-translation
prediction RMS 1.332 versus High 3.867 and linear 1.416 in the same interior does not rescue the pan interpretation:
most of that prediction's success is effectively blending a slowly changing image.

The witness's integer-roll, affine subpixel, and multiplicative/additive-light oracles pass. It has finite search,
a quarter-pixel grid, gamma-coded luma, and a selected 32-pixel interior sampled at stride two. It is a falsification
check on this proposed explanation, not a new motion ground truth or a production classifier.

There is also a mathematical limit to a future fade guard: on an intensity ramp, I(x)=a.x+b, translation gives
I(x-vt)=I(x)-a.v t, exactly an additive brightness change. Image-only affine fitting cannot always distinguish
motion from illumination. Such a guard should mark ambiguity, retain the raw candidate, and be tested against moving
ramps/textured pans before it is allowed to discard cases. No retrospective new guard was fitted into this run's
frozen ranking.

## Controls and refutations

Before footage renders: CPU affine-translation midpoint oracle zero residual, identity SSIM8 1, corrupted local
patch large residual, bad-reconstruction scorer row ranks first. Actual decoded black/white cut: scdet fires only
at the known transition. Low/noise RMS below the frozen floors. Both count mismatch directions and shifted reference
are refused. Actual GLSL moving synthetic, 72 frames: retained maximum RMS .275; shifting reference by two frames
gives minimum RMS 13.70 and is refused. All controls repeated after the initial boundary/count changes.

Additional whole-video-path counterfactual, [fault_control.py](fault_control.py): corrupt **only withheld output
frame 25**, keep retained frames intact. Alignment still passes unchanged, but the actual decode/measure/rank path
places frame 25 first: +30.01 dB loss to linear, SSIM8 .9334/.9977, both global and local regression flags.
This exercises a picture defect independently of the alignment alarm. No GPU rerender or real footage needed.
Final GPU/CPU controls and this injection rerun passed again; empty-eligible sources return no candidates, and
missing/refused native cadence metadata is rejected before rendering.

Pre-registered predictions: (1) raw extremes dominated by exclusions **supported**, all 100 top-20 slots excluded;
(2) High wins the median eligible pair in every selected source **supported**, not generalised to whole classes;
(3) at least one non-cut native reconstruction weakness **supported narrowly** by TV, with normal-playback causality
still open. The initial film candidate drops below the native effect floor; the architecture-pan hypothesis is
**refuted as an adequate explanation**; photometric transitions and locally held drawings escape the simple guards.

## Execution record and next scientific step

The first storage plan was amended **before footage rendering** from packet-copy to bounded input-seek -> local
native FFV1, to avoid keyframe-origin ambiguity. Compressed source packets still cross the NAS only for the selected
window plus seek pre-roll. The one-frame even-length trim and strict quantile-tie handling were also fixed before
footage renders. The legacy `tail_unpaired_frames` preparation key records this terminal trim; it does not mean the
removed source frame itself lacked a predecessor. The renderer's unsupported last midpoint is separately omitted.

An early scan launch refused before the final manifest existed. A preparation restart replacing a slow count decode
briefly left an old child overlapping the new writer; both stopped, reference regenerated with one writer, then
all actual decoded counts and alignment checks passed. The first helper filename shadowed Python's inspect module;
renamed review.py before use. An initial crop-view request found no crop from a helper loaded before that addition;
the crop was generated from saved renders. These were orchestration mistakes, not shader defects; no measurements
from incomplete/overlapping files were accepted.

The next useful controlled experiment is a near-stationary textured/periodic surface with local light/reflectance
changes, alongside a genuinely translating counterpart. Match the TV crop's scale/contrast, freeze zero-motion
truth, and ask whether High invents flow/shape changes. Compare brightness-normalised and gradient/energy evidence
without weakening the real-motion control. Keep the anime/CG timing examples separate: two endpoints cannot in
general reveal a held drawing's schedule or a unique accelerating trajectory. These are research leads, not switch
recommendations. The older flow-disagreement prospector can later be paired with these saved frame-error labels.
