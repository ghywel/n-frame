# Further synthesis families

Primary-source research checked **2026-11-17**. These entries broaden the
experiment pool; no implementation was installed or benchmarked here. Links to
moving source branches must be pinned when experiments begin.

## Forward splatting and reusable motion: M2M

Backward warping asks where each target pixel should sample its sources.
Forward splatting instead transports source contributions to their predicted
target locations, then resolves overlaps and holes. **Softmax splatting** adds
importance-weighted collision handling; it is a synthesis component, not a
complete motion estimator or playback pipeline.
[Original paper](https://arxiv.org/abs/2003.05534).

**Many-to-Many (M2M)** estimates/refines multiple motion hypotheses and reuses
motion work for several target times. Its emphasis on inexpensive extra
intermediate pictures makes it especially relevant to exact 60-fps schedules.
The paper's roughly 40-ms-per-frame 2K result is for 8× interpolation on a Titan
X; amortization, device and test configuration prevent treating that as a
single-midpoint or A310 result.
[Paper](https://arxiv.org/abs/2204.03513),
[authors' implementation](https://github.com/feinanshan/M2M_VFI).

The published implementation specifies Linux, PyTorch 1.8 and NVIDIA/CUDA 10.
A faithful cross-vendor port is work, not an existing deployment path. A smaller
project experiment could use an existing field with audited forward transport,
importance weighting and hole handling; that would be our hybrid, not a
reproduction of trained M2M. Compare identical fields across renderers and
identical renderers across fields before attributing gains.

## Learned kernels: SepConv and AdaCoF

**SepConv** predicts spatially varying separable resampling kernels. **AdaCoF**
predicts multiple sampling offsets and weights. They offer a useful challenge
to the assumption that one displacement at each location is the best synthesis
representation, especially at mixed or uncovered boundaries.
[SepConv authors' page](https://pages.cs.wisc.edu/~fliu/project/sepconv/),
[AdaCoF paper](https://openaccess.thecvf.com/content_CVPR_2020/papers/Lee_AdaCoF_Adaptive_Collaboration_of_Flows_for_Video_Frame_Interpolation_CVPR_2020_paper.pdf).

Their public reference implementations use CUDA/CuPy. Treat the provided pair
interfaces as midpoint references until an arbitrary-time implementation is
actually established. SepConv's reference code states academic-only use;
check applicable code/model terms before distribution. No modern target-device
speed claim follows from their age or architecture.
[SepConv implementation](https://github.com/sniklaus/sepconv-slomo),
[AdaCoF implementation](https://github.com/HyeongminLEE/AdaCoF-pytorch).

## Animation specialist: GMFSS Fortuna

The authors explicitly describe this as dedicated to anime interpolation.
Include it when the content set includes animation, drawn edges and held
exposures; do not assume an animation winner will best preserve live-action
faces or grain. The repository includes a CUDA CuPy dependency. A working
Arc/Mac export and exact target-time behavior were not established here.
[Official repository](https://github.com/98mxr/GMFSS_Fortuna),
[requirements](https://github.com/98mxr/GMFSS_Fortuna/blob/main/requirements.txt).

## New diffusion work: separate research interest from deployability

**SPEED** uses one-step pixel diffusion. It is a genuinely different synthesis
objective worth retaining as a quality reference, with particular attention to
identity, fabric texture, grain and temporal consistency across independent
predictions. The current inference runner explicitly says it is intended for
CUDA/xFormers. No A310/M5 speed or supported export was found.
[Official project](https://bbldcver.github.io/SPEED/),
[official source](https://github.com/bbldCVer/SPEED).

Source audit found an important concrete trap: `resolve_output_fps()` sets the
writer's rate, while both video loops emit each source picture followed by one
predicted midpoint. Consequently `--fps 60` on 24-fps input does not implement
duration-preserving 24→60 conversion. Also, its model argument `timestep=1000`
is a diffusion-step condition, not the requested physical video time. The
current runner is a 2× reference, not a verified arbitrary-time engine.
[Audited runner](https://github.com/bbldCVer/SPEED/blob/main/inference.py).

**RDVFI** generates sparse latent trajectories with one-step diffusion and
uses continuous pixel trajectories for interpolation. This relates directly to
our interest in reusable motion descriptions. Its project page reports 17 fps
at 1024×576; that is not evidence of meeting our 1080p targets. At inspection the
project's Code and Paper links still pointed to placeholders, so a runnable
release was not verified. Keep it on the research watchlist rather than in the
immediate installation queue.
[Authors' project page](https://mayongrui.github.io/RDVFI/),
[author-hosted paper](https://jhc.sjtu.edu.cn/~xiaohongliu/papers/2026realtime.pdf).

These methods should not be rejected solely because the first implementation
is slow. However, a pleasant generated midpoint is not sufficient evidence of
stable playback, source fidelity or deployability. Keep stochastic seeds and
checkpoint variants fixed and recorded for temporal comparisons.
