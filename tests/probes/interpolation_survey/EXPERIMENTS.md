# Proposed comparative experiment protocol

Registered **2026-11-17**, before executing the new candidates. This is the
execution queue and acceptance protocol, not a record of completed tests.

## 1. Freeze the common input and clocks

- Start with locally cached short windows containing both reported Bond actions
  at 3:22–3:24 and 3:29–3:31. Decode once into a canonical fixture; preserve
  source hashes, physical timestamps, chroma/range tags and exact frame counts.
  Avoid repeatedly reading full films over Wi-Fi.
- Use exact 24→48 and 24→60 synthetic schedules, plus the actual source-rate
  24000/1001→48000/1001, →60000/1001 and →60 schedules where relevant.
  `schedule.py` provides the exact timestamp arithmetic. Do not turn a
  midpoint-only engine into a claimed 60-fps engine by relabeling or dropping.
- Keep native 1080p output as the first common target. Record any reduced
  motion-estimation resolution separately from reduced output resolution.
- Pin source/patch/checkpoint/export hashes, precision, padding, input range,
  color conversion, model scale, TTA, thread count, runtime and actual device.
  Preserve raw outputs; make review encodes from those, not vice versa.

## 2. Correctness and negative controls before ranking

Require successful execution, all expected frames, correct timestamp/phase,
duration, color/chroma, source alignment and endpoint behavior. Check actual
generated values on known translating patterns, including non-midpoint times.
Record endpoint equality where a target timestamp really coincides, separately
from copying at other timestamps. Different declared endpoint policies must be
visible in the result rather than accidentally hidden by metrics.

Every new harness must reject deliberately wrong phase, reversed source order,
missing frames, failed/partial process output and changed color interpretation.
Copy and linear-blend baselines demonstrate that calm appearance or low
error on stationary regions alone cannot establish successful interpolation.
Hold/cut detection and adaptive bypasses must report their decisions. A method
must not win a smoothing test by quietly returning the source cadence.

## 3. Broaden motion and content, retaining known failures

Synthetic tests need independent truth at every requested output time:

- Rigid horizontal/vertical/diagonal translations; faces or face-like features,
  clothing texture, bars, fences and text, sweeping speed and subpixel phase.
- Camera pans, object motion against a stationary background, crossings,
  disocclusions, independently moving neighboring objects and repeated patterns.
- Nonrigid fabric and face deformation, acceleration, changing scale/rotation,
  with separate rigid controls. Register motion and visibility analytically.
- Motion blur and grain with clean and independently noisy controls; avoid
  baking knowledge of a candidate estimator into the generator.
- Cuts, dissolves, flashes and held animation exposures. Segment transition
  behavior from ordinary motion so cut spikes do not dominate the score.

Follow these with short held-out real clips spanning grainy film, clean digital
faces, rapid pans, sports/action and animation. A 12→24 withheld-frame test is
useful but doubles source displacement relative to native 24→48; it cannot
substitute for native playback. Keep both tests and label the distinction.

## 4. Measure sequences and obtain the human decision

Use identical-size, synchronized, anonymized moving comparisons at normal
speed, with crops for diagnosis. Review complete output sequences containing
both retained and synthesized pictures, not only a loop of inserted pictures.
Rate ripple, face/shape deformation, double edges, holes, blur, grain breathing,
cadence and comfort. Repeat difficult examples without telling the reviewer
which method is expected to win.

For synthetics measure spatial error and motion/visibility error, plus error
change in material coordinates over time. Use known truth to register motion.
For real footage mark unreliable registrations unknown; never use the
candidate's own field as unquestioned truth. Track tail defects and affected
area/duration alongside mean scores. Frame-to-frame change of **scalar MAE**
does not measure spatial movement of an error: a ripple can move while its
scalar magnitude stays unchanged.

A conspicuous recurring facial or clothing artifact rejects that setting for
content playback despite an improved average score. Retain rejected outputs,
including the old same-field patch-renderer failure, to prevent rediscovery of
an already unsuccessful remedy.

## 5. Measure real-time operation on each actual machine

Use the same selected settings for quality and speed. Warm up compilation and
allocation, but report cold startup separately. Record estimation, synthesis,
transfers and whole-pipeline time without counting PNG extraction as model
compute or omitting it from an actual image-file workflow.

Cadence needs decode→interpolate→display with audio and seek/retarget behavior;
the NAS needs decode→interpolate→encode. Report output FPS, synthesized frames,
missed deadlines, p50/p95/p99 latency, memory, queue depth and startup delay.
Inspect device placement and unexpected CPU fallback. Verify no steadily growing
backlog. Profile sustained five-minute runs for finalists after short tests
pass; expensive broad sweeps can remain short. 4K is tested separately.

Output intervals are 20.833 ms at 48 fps and 16.667 ms at 60 fps. They are not
necessarily per-inference limits: exact doubling can reuse every other source
picture, and pair features can be cached. End-to-end scheduling and tail
behavior decide whether the average compute fits the available buffer.

## 6. Staged execution queue

1. **Baselines:** current High, exact optimized MCI bidir, copy and linear blend.
   Add bilateral/AOBMC/VSBMC and smaller MCI block sizes as separately measured
   settings; do not assume current acceleration applies to every mode.
2. **First comparisons:** MVTools FlowFPS/BlockFPS from fixed analysis; portable
   RIFE 4.6 and Practical RIFE 4.25/lite through matching exports; IFRNet GoPro.
   Add SVP classic if already available, separating uniform/adaptive settings.
3. **Broader architectures:** EMA-small_t, AMT-S GoPro, forward splatting/M2M,
   independently estimated DIS flow with audited synthesis. FILM supplies a
   midpoint-only large-motion reference; learned kernels test another synthesis
   family. GIMM and diffusion remain quality/research references as access and
   port effort permit. Include GMFSS for animation, not as a film-only proxy.
4. **Promote finalists:** native frame-buffer adapter, complete pipeline and
   sustained content comparison; only then consider changing Cadence defaults.

For each candidate retain `unavailable`, `incorrect`, `quality-rejected`,
`too-slow`, `promising-needs-optimization` or `passes-measured-scope` distinctly.
A missing runtime is not evidence of bad quality. A fast average is not a
real-time pass. An attractive slow method can justify optimization, but should
not displace a working player until that optimization is demonstrated.
