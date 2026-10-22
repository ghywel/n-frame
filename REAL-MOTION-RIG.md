# Real motion with a known answer: the rig

*Written 2026-10-22 for Gareth, who asked for it: "It would help if you produce an .md document with which experiments
you want me to run, controls for errors, consideration of textures, lighting conditions, backdrop (A busy background or
a flat white sheet occluding the background noise)". The plan behind it is the swarm's real-content lane
([swarm/2026-10-21/real-and-field.md](swarm/2026-10-21/real-and-field.md), proposal P6), corrected here in one place
(below, "Why three rigs").*

## What this is for

Every derivative the field reports (velocity, acceleration, jerk, curl) has been checked against exact truth only on
synthetic scenes, and on real content only once: the party, where the answer key was Apple Vision's skeleton and the
field read velocity at a gain of about 0.7 ([THREEDIMENSIONAL.md](THREEDIMENSIONAL.md), section 9.8). No acceleration
or jerk has ever been measured on real footage against a truth. These takes give that truth from physics and from a
second, independent tracker (a black dot's centroid, which needs no shader), on real texture, a real lens, real
sensor noise and real compression. The record's open questions they answer: does the five-frame shader's jerk (118:1
on synthetic content) survive a real camera; where does the reach cliff (about 23 px per source frame) sit on a real
surface; does a busy still background move it (the bench says yes); what is the field's noise floor on a real sensor.

## Why three rigs

- **A turntable** gives velocity, centripetal acceleration and curl exactly, from the rpm alone, and its speed grows
  with radius, so one disc sweeps the speed band and puts the reach cliff at a radius you can predict.
- **A weight on a spring** gives jerk. Jerk needs few samples per period (6 to 10 at the rate the shader sees), and on a
  turntable that only happens far past the reach. A small, fast bounce keeps the motion within reach while the period
  is short; dropping frames in software then sweeps the samples per period.
- **A pendulum** gives acceleration through its reversals, the case the record says real limbs pass through in 6 to 11%
  of moving frames.

Each rig carries a black dot. Its centroid is tracked by simple arithmetic, to about a twentieth of a pixel, with no
block matching, so the shader is checked against something it did not compute.

## What to print

The four sheets are in `~/Developer/np-scratch/n-frame/rig/` as PDF (A4, true size) and PNG. Print the PDFs at
**actual size / 100%** on matte paper. Measure the 100 mm bar on each print with a ruler and write the reading in the
log. A printer that scales by 3% makes every speed 3% wrong.

| sheet | what it is | used on |
|---|---|---|
| `disc-noise.pdf` | a 190 mm disc of aperiodic noise at five scales, a white dot near the rim, a centre cross | the turntable (the main target) |
| `disc-checker.pdf` | a 190 mm polar checkerboard, 36 sectors by 8 rings: the wagon wheel | the turntable (the hard case) |
| `markers.pdf` | black dots of 6, 10 and 16 mm | cut out: the spring's weight, the pendulum's bob |
| `noise-patch.pdf` | a 120 mm square and a strip of the same noise | glued to the weight's and the bob's faces |

Cut the discs out and pierce the centre cross for the spindle, so the disc turns about its own centre. An off-centre
disc wobbles once per turn. The rim dot's track measures the wobble, but a centred disc is cleaner.

## The camera

On the iPhone, in Settings > Camera > Record Video (names as in recent iOS versions [U]):

- [ ] **1080p at 60 fps.** 1080p reads the sensor faster than 4K on most phones [U], which halves the rolling-shutter
      skew (below).
- [ ] **HDR Video off.** HDR (HLG or Dolby Vision) needs tone mapping before any measurement.
- [ ] **Auto FPS off** (named "Auto Low Light FPS" in some versions [U]). It drops to 30 fps in dim light, mid-take.
- [ ] **Enhanced Stabilization off, Action Mode off, Cinematic off.** Stabilisation warps each frame to cancel shake, and
      the warp is a fake motion field.
- [ ] **Lock Camera on**, so it does not switch lenses mid-take. Use the 1x lens.
- [ ] **ProRes** if the phone offers it. Otherwise High Efficiency (HEVC) is fine.

In the Camera app, once the rig is framed: press and hold on the target to lock exposure and focus (AE/AF LOCK), then
drag exposure down a little if the white sheet looks blown out. Clipped white carries no texture.

Optional, for full manual control: Blackmagic's free Camera app sets shutter, ISO, white balance and a locked frame rate
[U]. Use a shutter of 1/500 s or faster. At the rim of a 33 1/3 rpm disc the image moves about 1200 px a second, so
1/500 s blurs it by 2.4 px and 1/1000 s by 1.2.

- [ ] **Tripod, on the floor, not on the turntable's table.** The motor's hum and your footsteps reach the camera through
      a shared table.
- [ ] **The phone square to the motion.** For the turntable, look straight down at the platter (a tripod arm, or the phone
      on a shelf above, screen up). Within about 5 degrees is fine: the disc's ellipse measures the tilt and it is
      corrected for. For the spring and the pendulum, the camera looks straight at the swing, and the motion stays in
      the plane facing the camera, not towards it.
- [ ] **Framing.** The 190 mm disc spans about two thirds of the frame's height (about 680 px of 1080: about 3.6 px per
      mm; the frame then sees about 54 x 30 cm). Keep the same distance for the spring and the pendulum, so one scale
      serves every take.
- [ ] **Send the original file.** AirDrop the .mov to the Mac, not through a messaging app (they re-encode).

## Light

- **Steady and bright.** Indirect daylight from a window is best. Cloud changes are slow enough not to matter within a
  take.
- **No mains flicker.** UK mains lighting flickers at 100 Hz, and at 60 fps that beats into a brightness change from
  frame to frame, which the matcher reads as motion. Test once: film a plain wall for a few seconds with a fast shutter.
  Rolling dark bands mean that light flickers, so use another light or daylight. An LED panel sold as flicker-free is
  fine. If mains light cannot be avoided, film at 50 fps with a 1/100 s shutter instead and say so in the log.
- **No glare.** Matte prints, the light at an angle, no reflection of the window or the lamp on the disc.
- **No moving shadows.** Swing the tonearm away and open the lid. Keep your own shadow off the rig, and keep fans off.

## The backdrop

Both, as separate conditions, and the flat one first:

1. **Flat**: a matte white or light-grey sheet behind and around the rig, filling the frame's edges. It isolates the
   object, the cleanest truth. It also keeps the home out of the picture.
2. **Busy**: something still and finely textured behind the rig: patterned fabric, newspaper pages taped flat, a
   bookcase. This is a real variable, not just realism. On the record's bench the reach cliff sat at 24 to 36 px per
   frame against a textured room and past 36 against a dark one. Use the same busy backdrop for every busy take.

Nothing behind the rig moves during a take: no screens, no pets, no curtains in a draught.

## The takes

About 30 seconds each, the rig already moving when you press record, so every take is in steady state. Whole
revolutions do not matter: the analysis finds them. Session A is the useful minimum. B adds the background variable,
C is optional.

**Session A: the flat sheet**

| take | what | why |
|---|---|---|
| A0 | Everything still for 10 s: the rig in frame, nothing moving | The noise floor: the field must read zero here, and the still edges of every later take must read zero too (the control that must not move) |
| A1 | The noise disc on the stopped platter for 5 s, a ruler lying on the platter | The scale in the plane of motion, and the lens |
| A2 | The noise disc at 33 1/3 rpm | The whole disc within reach (about 20 px a frame at the rim): velocity, centripetal acceleration and curl everywhere |
| A3 | The noise disc at 45 rpm | The reach cliff falls inside the disc, at about 290 px of its 340 px radius |
| A4 | The noise disc at 78 rpm, if the turntable has it | The cliff at about half the radius |
| A5 | The checker disc at 33 1/3 and at 45 (two takes) | The wagon wheel on real content: the period trap's speeds swept by radius |
| A6 | The spring: the noise patch and a 10 mm dot on the weight's face, pulled down a few millimetres (no more than a pencil's width) and let go, recorded as it rings down | Jerk. A few millimetres keeps it within reach after frame dropping; the ring-down sweeps the amplitude |
| A7 | The pendulum: a string about 25 cm long, the bob with the patch and a 10 mm dot, swinging gently (a couple of centimetres either side), across the camera's view | Acceleration through the reversals. A 25 cm string swings once a second |

**Session B: the busy backdrop.** Repeat A0, A2, A3 and A6 against it.

**Session C (optional): dim light.** Repeat A2 at about a quarter of the light, the exposure locked bright enough to
see. The field's noise sensitivity on a real sensor.

The spring can be anything soft enough to bounce a 100 to 300 g weight once or twice a second: a section of a Slinky,
a chain of rubber bands, a lamp spring. Hang it from something rigid (a shelf, not a door). If the weight spins, add a
second thread to stop it. The frequency is measured from the dot, so it need not be known in advance.

## The log

Copy this into `~/Developer/np-scratch/n-frame/footage/LOG.md`, one row per take, and put the files beside it named
`rig<take>-<what>.mov` (for example `rigA3-noise-45.mov`):

```
| take | file | rpm / spring / string | backdrop | light | printed 100 mm bar measured | distance (cm) | notes |
```

Note anything that went wrong as it happened (a nudge, a cloud, a shadow). A known fault in a take is data. An
unknown one is a wrong answer.

## What can go wrong, and the check for each

| fault | what it does | the check |
|---|---|---|
| The camera moves | Every texel reads a motion that is not there | A0, and the still border of every take, must read zero |
| Rolling shutter | A phone reads its rows over several milliseconds, so a moving object is skewed by row: a small, speed-proportional shear | The dot's centroid sees the same skew, and the rpm does not. The pendulum's horizontal swing is least affected. Modelled, not hidden |
| Motion blur | Smears texture along the motion, more at the rim | A fast shutter, and the blur length in the log |
| Flicker | A brightness change from frame to frame, read as motion | The light test; A0 must not flicker |
| Exposure or focus hunting | The same | AE/AF lock |
| Compression | Smears fine texture at low bitrate | ProRes or high HEVC; the original file sent |
| Print scale | Every speed off by the same factor | The measured 100 mm bar |
| The disc off-centre | A once-per-turn wobble | Pierce at the cross; the rim dot's track measures what is left |
| Tilt | The disc is an ellipse | Overhead framing; the ellipse is fitted |
| Platter speed | Turntables drift by about 1% [U] | The rpm is measured from the rim dot over the whole take, not taken from the dial |
| Variable frame rate | Timestamps drift | Auto FPS off; the file's frame times are checked on arrival |

## What happens to the footage

By default the takes are processed as numbers. I do not look at the frames unless you say so, as with all footage from
home. The rigs show nothing personal, and the flat sheet keeps the room out, so if you are happy for me to look at a
frame to check alignment, add "frames OK" to the log.

The analysis, for each take:

1. **The answer keys.** The rpm from the rim dot's turns, and the spring's and pendulum's trajectories from the dot's
   centroid, fitted (a damped sinusoid), with the derivatives taken from the fit.
2. **The field.** The take decimated in software by k = 1 to 6 (60, 30, 20, 15, 12, 10 fps), and for the spring up to
   k = 10, since a bounce once a second reaches 6 samples per period only at 6 fps (a 4 mm bounce then moves about
   15 px a frame at its fastest, still within reach). Each rate is run through the
   recommendation (velocity), the three-frame shader (acceleration), and the four- and five-frame shaders (jerk), read
   out as numbers (read_view 4 to 6, with the two-channel readback that lifts the fp16 floor).
3. **The comparison.** For the turntable, by radius band, against omega r, omega squared r and 2 omega: the gain, the
   spread and the share of wrong texels, and the radius where the cliff starts. For the spring and the pendulum, on the
   weight's and bob's patch, against the fit.

**Predictions, written before any take** (from the record; each with what would kill it):

- Turntable velocity reads at a gain of 0.9 to 1.0 inside the reach (synthetic discs: 0.93 to 1.03). Under 0.8 inside
  the reach would mean real texture and light cost what synthetic scenes do not show.
- The cliff starts where omega r k / 60 passes about 23 px, at r = 23 x 60 / (omega k) px. At 45 rpm and k = 1 that is
  r of about 290 px. A cliff more than 20% from that radius would mean the reach on real surfaces is not the constant
  the record measured.
- On the busy backdrop the cliff moves outward. The bench moved it from 24 to as far as 36 px a frame against a
  textured room.
- Curl reads at about 0.9 to 0.95 of 2 omega (synthetic: 0.93; the party's bodies: 0.9).
- The spring's jerk: the five-frame shader reads better than 20:1 at 8 or more samples per period, and the four-frame
  shader 3 to 5:1 flat. The quint under 10:1 at 8 samples per period would mean the fifth frame's advantage does not
  survive a real camera, which is the result this rig exists to find.
- The checker disc locks at the radii where its sector period sits near the speed, as the synthetic wagon wheel did
  (82% gross by design there).
