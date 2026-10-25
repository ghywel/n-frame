# Beyond interpolation: what a run of frames can tell a shader

*Opened 2026-10-25 at the owner's question: "Given a collection of n-sequential frames what fun things can we do ... what
can our frames tell us. What weird and wonderful things can we do." An exploration, not a programme: a map of what is
possible, six working shaders that try the first corner of it, and a ranked list of what to build next.*

The patch was built to interpolate. But what it actually gives a GPU shader is more general: **a short stretch of time**,
and a place to keep notes between frames. Interpolation is one thing to do with time. This document is about the others.

## What a shader can see

Read from the patch ([README.md](README.md#whats-new)) and checked by running the shaders below:

- **A window of up to 8 frames** (`FRAME0` ... `FRAME7`; `PL_FRAME_MIX_MAX` is 8), declared by the names a shader binds.
- **When each one is**: `rts_mix[k]` is slot k's time relative to the output, in source frames. The slots are not in time
  order (the window rule takes the nearest before and after first, then works outward, ties to the earlier frame), so a
  shader finds "now" and "three frames ago" from `rts_mix`. At N:N a 7-frame window is exactly [-3 .. +3] around the
  current frame and an 8-frame one [-4 .. +3]: **a centred window, three frames of the future included.**
- **N:N operation**: with the companion patch the hook fires at the source's own rate, so a shader is a *filter* on every
  frame, not only an in-betweener.
- **Memory without limit**: a `STORAGE` texture persists between calls, and `pair_changed` says when a new source frame
  has arrived. So a shader can keep a running sum, a running maximum, a counter, or a ring of past frames (one is built
  below: twelve frames, one every sixth, three seconds). **The window is 8 frames; the memory is whatever fits in GPU RAM.**
- **Limits met on the way**: a pass binds at most 16 textures (a ring of separate textures plus a window overflows it;
  tile the ring into one texture instead); `//!` inside a comment is parsed as a directive; storage textures have a fixed
  size; the first and last few frames of a clip fall back to the builtin mixer (loudly).
- **And the instruments we already have**: the interpolators' motion field (velocity, and from the six-frame fit
  acceleration and jerk, divergence, curl and shear; [WHAT-IT-CAN-MEASURE.md](WHAT-IT-CAN-MEASURE.md)), all
  deterministic, all on ordinary hardware. That is what nobody else has in a real-time filter.

## Six shaders built today

All in [shaders/effects/](shaders/effects/README.md), each an N:N filter (`libplacebo=fps=<source rate>:frame_mixer=
custom_n:custom_shader_path=<file>`), none needing motion estimation. Tried on stretches of five windows from the NAS pool
(film, television, anime, western cartoon, CG), every result looked at frame by frame before being described here.

| shader | window | what it does | what it showed |
|---|---|---|---|
| **chronophotograph** | 8 | Marey's photographic gun: the still world (the window's median) with the last five frames' movers laid on it as fading exposures | A pony's wings and mane fan into a strobe of her last five drawings; a gesturing hand leaves a fan of hands. Needs a still camera: a moving camera smears the plate |
| **ghost-town** / **ghost-town-long** | 7 / 7 + a 12-frame ring | each pixel's median over time: whatever passes vanishes | Seven frames (a third of a second) erase only fast movers. The long version keeps a three-second ring in storage: a man's raised gesturing arm is replaced by his resting pose, a turning face dissolves while a still child stays |
| **long-exposure** | 2 + storage | a running exposure kept in a storage texture: light painting (brightest, decaying) or shutter drag | Comet trails on a fight's bright edges, streaks behind a ship, a glowing trail behind a pony |
| **pulfrich** | 5 | red eye now, cyan eye two frames ago: lateral motion becomes depth through red/cyan glasses | Clean red/cyan disparity on a ship moving across the frame and on fighters (depth itself not checkable without glasses) |
| **spectrum** | 8 | each pixel's temporal Fourier energy, its straight-line trend removed: hue the frequency (3 to 12 Hz) | Only what goes back and forth lights. **The toaster's grille glows green**: its light goes back and forth at a few hertz (below) |
| **tremor** | 7 | Eulerian magnification (a temporal band of the blurred frames, amplified, large motion left alone) | Gentle: temporal variation doubled in near-still areas, small motion x1.2-1.4, large motion unchanged. Seven frames cannot reach a pulse (about 1 Hz), and the noise floor caps the gain |

**What the spectrum shader found.** GPT's footage prospecting (tests/probes/prospect/RESULTS.md) found its strongest quiet-shot lead
on a nearly still toaster in a television episode (High 5.6 dB under a plain blend), and the photometric work (tests/probes/photometric/PLAN.md) showed
that the grille's local light change fooled the matcher, but not what kind of change it was. The spectrum shader, run on
the same shot, lights the grille, green (around 6-9 Hz), and nothing else on the toaster: the light on the brushed metal **goes back and
forth at a few hertz**, a flicker or a shimmer, not a one-way change; exactly what a matcher that compares raw brightness
reads as motion. A five-minute
effect shader answered an open question about the interpolator. That is the strongest case for this whole direction:
these shaders are not only toys, they are instruments that let us see what the frames contain.

## The map: what the frames can tell us

Grouped by what they ask of the frames. **Built** marks today's prototypes; **ours** marks ideas only our motion field
makes possible in real time.

**Time as a picture (no motion estimation; cheap; the window and storage are enough)**
- The median and its relatives: ghost town (built), *only the movers* (built, a switch), a clean plate for compositing.
- Stacking: chronophotograph (built), long exposure and light painting (built), shutter drag (built), stroboscope.
- Slit-scan and time displacement: each row (or a radial band, or a gradient) taken from a different moment, so time is
  laid across the picture (Golan Levin's catalogue of slit-scan video works is the reference). With a storage ring the
  spread can be seconds, not eight frames.
- Spectra: what oscillates and how fast (built), flicker and mains-hum detection, a "beat" map for music video.
- Eulerian magnification (built, short): with a storage ring of a few seconds, a pulse in a face and breathing in a
  sleeper (Wu et al., SIGGRAPH 2012; phase-based, Wadhwa et al., 2013, is the cleaner form).
- Temporal denoising where nothing moves (practical; listed, not the focus).

**Motion made visible (ours: the field the interpolators already compute)**
- **Synthetic shutter**: integrate along each pixel's motion path to add true motion blur at any shutter angle; the
  natural companion to interpolation (60 fps output with a film's 180-degree blur; Brostow and Essa, SIGGRAPH 2001).
- **Speed lines**: manga-style streaks drawn back along each moving object's path, from the flow, for anime.
- **Force painting**: acceleration as the push on each thing (already in the reading tail as a field view); an
  **impact detector** flashing where jerk spikes (a ball hitting a bat, a door slamming).
- **Time to contact**: divergence is looming; tau = 1 / divergence is the seconds until a thing reaches the camera (Lee,
  1976). Colour what is coming at you by how soon.
- **Surprise**: predict each frame from the six-frame trajectory fit and show only what the prediction misses (sparks,
  things appearing, cuts, the unexpected), the motion field's residual turned into a picture.
- **The future overlaid**: extrapolate each moving thing a few frames ahead and draw where it will be.

**The scene's structure (ours, and the weirdest)**
- **Depth from parallax**: in a camera pan, near things move faster than far ones; flow magnitude against the frame's
  dominant shift is inverse depth. From that: depth fog, a tilt-shift miniature, relighting, and **3D from flat footage**
  (pulfrich.glsl does the cheap version with a fixed delay; with the flow, the disparity could be computed and steered).
- **Layers by motion**: separate camera motion from object motion; freeze the world and let only the actors move, or
  stabilise the camera with eight frames of path smoothing.
- **Vibration and sound**: the visual microphone (Davis et al., SIGGRAPH 2014) needs high frame rates, but at 24-60 fps a
  shaking speaker cone or guitar string still shows in the spectrum.

## What to build next (ranked)

1. **Synthetic shutter** (ours, useful, visibly beautiful): the warp already has the flow; sample K points along it.
   It makes our 60 fps output look like film where the owner wants it to, and it is a toggle for Cadence.
2. **Long-history ring as a library**: the ghost-town-long ring generalised (any K, any stride, colour or luma), so
   the median, slit-scan and Eulerian pulse work at seconds instead of a third of a second.
3. **Time to contact and surprise** (ours, instruments): both read fields we already compute; both turn the six-frame
   fit into something a viewer can see in one glance.
4. **Depth from parallax** (ours, the weirdest): pseudo-depth on camera pans, then fog, tilt-shift and steered 3D.
5. **Speed lines for anime** (ours, fun): the flow on cel animation, drawn in the medium's own language.

## Running them

```sh
ffmpeg -i in.mkv -vf "libplacebo=fps=24000/1001:frame_mixer=custom_n:custom_shader_path=shaders/effects/spectrum.glsl" out.mkv
```

The rate must be the source's own (N:N). The renders of 2026-10-25 (side by side, original left) are in the shared
hot-drops folder, `effects-2026-10-25/`.
