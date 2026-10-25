# Two-pass shaders: foresight from a pre-processing pass

*Opened 2026-10-25 at the owner's idea: volume normalisation and two-pass encoding both read the whole file once before
the real pass, so the real pass knows what is coming. "Can we optionally do some sort of pre-processing pass over the
full video, creating some dataset file alongside the source video, giving the final pass shaders access to real
foresight data ... What kind of data would be useful to extract and store ... Would the data file be very large or a
reasonable size. Might this method be a real solution to the anime / cartoon interpolation question? Can we begin to
introduce some form of real object detection, machine learning or apple's neural network to make better decisions?"
A design record and its first measurements, nothing built.*

> **HELD by the owner, 2026-10-25 18:26** ("Hold and save state on 2 pass for now", as the effects and imports lines
> are held), while the multi-frame family gets the High lineage. **State:** the design, the oracle ceilings and the
> literature are below; nothing is built or pre-registered. **To resume:** pre-register and run "First steps" 1-4 in
> order (self-calibration with a guard first); the content test's renders in `np-scratch-int/content-20261023` are the
> inputs for step 1, and Apple's `VTFrameProcessor` headers are in the macOS SDK for step 3.

## The one principle

The real-time pass already sees eight frames and keeps unlimited notes in storage. What it can never have is **the
future beyond its window, and time to think**. So a sidecar should hold only what needs one of those two: decisions and
parameters that take the whole shot to make, or that take more computation than real time allows. It should not hold
anything the real-time pass can compute for itself (above all, not the dense motion field). That one rule settles both
what to store and how big the file is.

## What the record already says the window cannot know

- **Drawings on threes and on mixed timing.** The quad's cadence branch recovers the twos prize (16 to 25 dB on the
  exact ladder, `NFRAME-LIMITS.md`, "Content drawn on twos") but only 0.7 to 6 dB on threes, because inside four frames
  "case B sees the run's last two copies and starts its span a slot late" (the cadence branch, 2026-09-19). A whole-shot
  pass knows when every drawing starts and ends, on twos, threes or a timing that changes mid-shot.
- **A held drawing against a motion that came back** (the O8 turning point: two identical frames are "either a drawing
  held or a motion that came back to the same place"). One pair cannot tell; a shot's worth of frames on both sides of
  the pair usually can (a hold has stillness around it, an oscillation has motion either side).
- **Per-region cadence** (import 2, `IMPORTS-TO-INTERPOLATION.md`): a character on twos over a pan on ones. Two kills
  showed that four frames of evidence trip on moving prints and low contrast; GPT showed (G028) that no history proves
  cadence on a periodic texture. Foresight adds the frames AFTER, which history cannot, but GPT's limit still holds for
  a texture moving exactly its period: that case is identical to stillness in every frame, so it stays "undecided".
- **Light against motion** (import 1): the toaster's local light change is decided at the coarsest level, inside one
  pair. A pre-pass can fit each region's brightness curve over the whole shot (a flicker is periodic in time, a moving
  edge is not) and hand the real pass a per-region "this is light" verdict.
- **Which method wins on this footage.** Measured below: the answer changes frame to frame on animation.

## What foresight could be worth: the ceilings, from scores already on disk (2026-10-25)

If a perfect oracle chose, for every withheld frame, the better of today's High and a plain blend (the content test's
40 windows, decimate-and-reconstruct; PSNR of each segment's mean squared error, averaged over segments, so lower than
the mean-of-PSNR figures elsewhere in this record):

| class | High | High-or-blend per frame (oracle) | frames where the blend wins |
|---|---|---|---|
| film | 30.58 | 31.22 (+0.63) | 6.9% |
| television | 32.22 | 33.72 (+1.50) | 2.2% |
| anime | 38.15 | 39.10 (+0.95) | 25.6% |
| western cartoon | 25.66 | 26.81 (+1.14) | **53.8%** |
| CG | 33.25 | 33.56 (+0.31) | 6.0% |

On GPT's five 300-second prospecting windows (its own measure, today's High): +0.08 film, +0.13 television, +0.38
anime, +0.48 cartoon, +0.20 CG. Choosing one shader per three-second segment instead (the best of the 21 variants the
content test scored) is worth far less, +0.03 to +0.33 dB: **the gain is in decisions made per frame and per region,
not in picking a shader per film or per shot.** The per-frame figure is a floor for what a per-region oracle would
give (the import diagnostics found High's losses concentrated in a few cells). Television's +1.50 comes from the 2.2% of
frames where the blend wins, so those few frames carry very large losses; a cut or light verdict is the likely fix (not
yet looked at frame by frame).

A ceiling is not a method: at playback there is no truth to choose by. The next section is how a pre-pass could get one.

## The data: what to store, and how big it is

Sizes for a two-hour film at 24 fps (172,800 frames), computed, not measured on a real sidecar yet:

| layer | what | raw size | notes |
|---|---|---|---|
| **A. per frame** | cut and fade verdicts with confidence; the global gain and offset fitted over the whole fade, not one pair; the drawing timeline (is this a new drawing; the span it belongs to, for twos, threes and changing timing); camera motion (six affine numbers, smoothed over the shot); noise level; the method verdict (motion, blend or hold) | about 64 bytes a frame: **11 MB** | runs of equal values: compresses to a few MB or less |
| **B. per region** | the same verdicts per cell of a 64 x 36 grid: new drawing or held (per-region cadence), light or motion, method, "undecided" | 1 byte a cell: 2.3 KB a frame, **400 MB raw** | constant within a shot for most cells: run-length coding should take it to tens of MB (to be measured) |
| **C. dense fields** (not recommended) | the coarse motion field at 1/8 of 1080p (240 x 135 x two half floats) | 130 KB a frame: **22 GB** | the real-time pass computes this itself; storing it buys nothing foresight gives |

So **a useful sidecar is megabytes, not gigabytes**: layer A a few megabytes, layer B probably tens. Layer C is the one
thing not to store.

## How a two-step shader would work

**The pre-pass** (offline, any speed, on the same machine or a server; nothing about it need be real time):
1. Decode the whole film once at low resolution (luma at 480 or 640 px wide is enough for every verdict above).
2. Shot boundaries first (the cut and fade verdicts, with the whole fade in view).
3. Per shot: the light curves (global, and per region: fit, then classify periodic flicker against coherent change);
   the drawing timeline (each region's held/new sequence over the whole shot, with GPT's identifiability test: a
   region counts as held only where its texture matches uniquely, else "undecided"); camera motion.
4. **Self-calibration** (the new idea this makes possible): the pre-pass has the real frames, so it can run our own
   benchmark on the film itself. Withhold a frame, interpolate it with each candidate (High, a blend, a hold, the
   cadence-aware warp), score against the real frame, and keep per region which wins. This is exactly how every number
   in this repository is measured (decimate and reconstruct), turned from a test into a decision. Its catch is the one
   our benchmarks already carry: withholding a frame doubles the motion, so the verdict is made at twice the motion it
   is applied at. Whether the verdict at 2x predicts the right choice at 1x is measurable (the first test below).
5. Write the sidecar beside the video (`film.mkv` -> `film.nframe`), versioned, with the source's hash and the frame
   count so a stale or mismatched sidecar is refused, never silently used (a step that fails and returns something plausible is this record's commonest failure).

**The final pass** (real time, unchanged shaders plus reads): each frame's layer A record and its layer B grid arrive as
a small texture (a 64 x 36 grid is one 2.3 KB texture a frame). The shaders read verdicts where today they guess:
the cadence branch takes the span from the timeline instead of inferring it from four frames; the gain fit takes the
fade's curve; the blend-or-motion choice takes the self-calibrated verdict per region; "undecided" falls back to
today's behaviour exactly, so **with no sidecar, or an undecided region, the output is today's output**.

**How the data reaches the shader:**
- **Cadence (the Metal engine):** trivially. The engine is ours; it reads the sidecar and binds a per-frame buffer.
  This is where the idea would ship.
- **libplacebo (the research route):** the patch exposes `rts_mix[]` (relative times) but no absolute frame index or
  timestamp, and `//!TEXTURE` data is fixed in the shader text. Three ways in: (a) a storage counter of source frames
  (ghost-town-long already counts with `pair_changed`), valid for renders from the start without seeking, enough for
  research; (b) carry the per-frame record in a few extra rows padded onto each frame by ffmpeg before libplacebo and
  cropped after (no patch change); (c) a small patch addition exposing each window frame's absolute timestamp, the
  natural fix.

## Is it a real solution to anime and cartoons?

Partly, and the parts can be told apart:
1. **Timing** (when each drawing is new, per region, on twos, threes or mixed): **yes, mostly.** This was measured as
   the largest single prize in this record (16 to 25 dB on twos), and the window's bound on threes is exactly what
   foresight removes. What it cannot fix is the genuinely ambiguous case (a texture moving exactly its period).
2. **Policy** (motion, blend or hold, per frame and region): **plausibly**, worth up to about +1 dB on 2D animation by
   the ceilings above, if self-calibration predicts the right choice. That is the first thing to test.
3. **Drawings that are not motion** (smears, redraws, a pose that is a new drawing rather than the old one moved): **no.**
   No amount of foresight invents an in-between drawing that does not exist. The best a pre-pass can do there is
   recognise it and choose the hold or the blend, which (2) covers.

And one thing only foresight makes possible: **knowing the drawing timeline, Cadence can offer to respect it.** Anime
viewers argue about smoothing; with the timeline a player could smooth the camera pans and backgrounds (on ones) while
keeping the character animation's own timing, or smooth everything. That is a product choice no real-time interpolator
can offer honestly.

## Machine learning and Apple's neural tools

The pre-pass is where learned tools belong, if anywhere: it has no real-time limit, and its output is frozen into the
sidecar, so **the final pass stays deterministic for a given sidecar** (the project's identity), whatever produced it.
On this machine's SDK (checked 2026-10-25):
- **VideoToolbox `VTFrameProcessor`** (macOS 15.4 and iOS 26; not tvOS): Apple's own learned frame-rate conversion,
  low-latency frame interpolation, optical flow, motion blur, super-resolution and temporal noise filtering. Its
  frame-rate conversion takes `usePrecomputedFlow`: **Apple's design is itself two-step** (flow first, then synthesis).
  Never benchmarked in this repository. It is the learned reference line the 2026-09-19 survey said was "not testable
  here" (ATD-12K): now it is, on our own content windows.
- **Vision**: `VNGenerateOpticalFlowRequest` (a second flow opinion for the pre-pass), `VNGenerateForegroundInstanceMaskRequest`
  and `VNGeneratePersonSegmentationRequest` / `VNGeneratePersonInstanceMaskRequest` (object and person masks: the
  per-region cadence wants layers, and a character mask is a layer). Trained on photographs; whether they find a cel
  character is unknown and cheap to look at.
- **Core ML** would run published models (RAFT-class flow, anime-trained interpolators) in the pre-pass; licences and
  model sizes to be checked per model.

What object detection would actually decide: layers for per-region cadence (a character mask is the region whose timing
differs), occlusion order (what is in front where things cross), and where not to interpolate (faces and mouths on
holds are where artefacts are most visible). Each is a verdict for layer B, not a new kind of shader.

## Whose footsteps (surveyed 2026-10-25 by a research subagent; the three marked * opened and checked before filing)

- **Two-pass decimation is old practice.** AviSynth's TIVTC TDecimate* has a metrics mode (pass 1 writes one line per
  frame: frame number, difference metric, scene-change metric) and modes that read the whole file up front, which its
  documentation says generally give smoother results than one pass; MultiDecimate does the same. A few numbers a frame:
  layer A above is that idea extended. https://avisynth.org.ru/docs/english/externalfilters/tivtc_tdecimate.htm
- **Television frame-rate converters avoid foresight on purpose** (latency): cadence detectors buffer a handful of
  frames (Broadcom US8693552; Entropic US8842742 tags frames new or repeated and handles mixed film and video regions
  with one timing for the whole frame, no segmentation). The survey found no shipping product that analyses whole
  shots, and **no published automatic per-region timing detector for cel animation**.
- **Anime interpolation research treats holds as data to throw away.** AnimeInterp's ATD-12K (CVPR 2021) dropped
  near-duplicate triplets by SSIM; EISAI* (Chen and Zwicker, ECCV 2022) trained a duplicate detector, discarded pans
  because non-linear animation over a linear pan breaks its triplet filter (the survey's reading of the paper body), and
  argues PSNR and SSIM are the wrong measures for line art (LPIPS and chamfer line distance instead).
  https://arxiv.org/abs/2111.12792. Generative in-betweening (ToonCrafter, 2024) is far from real time.
- **Self-calibration exists for networks, not for choosing methods.** Choi et al.* (CVPR 2020, "Scene-Adaptive Video
  Frame Interpolation via Meta-Learning") adapt an interpolator at test time on the video's own frames (predict frame 3
  from 1 and 5); per the survey, plain fine-tuning helped most sequences and hurt one, so a guard is needed; Wu et al.
  (BMVC 2023) report naive adaptation degrading with more steps. https://arxiv.org/abs/2004.00779. The survey found
  nothing that uses withheld frames to CHOOSE between deterministic methods per region: step 1 below would be new.
- **Apple publishes no quality numbers** for VTFrameProcessor or Vision's flow and masks, on animation or anything
  else; WWDC25 session 300 shows frame-rate conversion at arbitrary phases and the precomputed-flow path.
  `VTLowLatencyFrameInterpolation` (macOS 26) uses only the previous and current frame. Measuring them is our own work.

## First steps, cheapest first (none run; each pre-registered before it runs)

1. **Self-calibration predicts?** On the content test's 40 windows: decimate the half-rate input once more (4x), choose
   per frame and per region between High and the blend by the 4x reconstruction, apply the choice at 2x, and score it
   against the per-frame oracle above, with a guard (a choice is taken only where the 4x verdict is clear; otherwise
High, today's output), since test-time adaptation is known to hurt some videos. Pass line set before the run. On the
animation classes also scored by a line-aware measure, not only PSNR (EISAI's point).
2. **The timing ceiling:** the twos probe's threes column with the true drawing timeline handed to the cadence branch
   (an oracle sidecar, carried by route (a) or (b)): how much of the twos prize the threes recover when the slot-late
   bound is removed.
3. **Apple's line:** `VTFrameRateConversion` on the content test's 40 windows, the same decimate-and-reconstruct score,
   as a reference (not a component).
4. **Masks on cels:** Vision's foreground instance masks on frames from the anime and cartoon windows, looked at.
5. Only then a sidecar format and a pre-pass tool, then the Cadence reader.
