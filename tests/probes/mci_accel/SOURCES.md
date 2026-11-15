# Primary sources checked 2026-11-15

- [FFmpeg minterpolate](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavfilter/vf_minterpolate.c)
  and [motion estimation](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavfilter/motion_estimation.c):
  overlapping SAD, EPZS predictor order and temporal/current-neighbor dependencies.
  Implementation uses separately pinned local 3a5eb94, not a moving download.
- [Pixelutils API](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavutil/pixelutils.h),
  [aarch64](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavutil/aarch64/pixelutils.h),
  [x86](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavutil/x86/pixelutils.h):
  existing unaligned 32x32 NEON/SSE2/AVX2 SAD, independent signed strides, integer
  return. Production source headers are LGPL-2.1-or-later.
- [Checkasm](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/tests/checkasm/pixelutils.c)
  tests sizes, pointer alignments and independent positive/negative strides. Its
  standalone harness is GPL-2-or-later; the
  [libavutil pixelutils test](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavutil/tests/pixelutils.c)
  is LGPL-2.1-or-later. Do not infer production licensing from test licensing.
- [FFmpeg framerate](https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/libavfilter/vf_framerate.c):
  LGPL slice threading via `ff_filter_execute`; reuse still requires disjoint
  mutable state and output ownership in the caller.
- [MVTools documentation](https://raw.githubusercontent.com/pinterf/mvtools/mvtools-pfmod/Documentation/mvtools2.html):
  GPL implementation. Internal horizontal slices alter boundary output; docs
  describe processor-count dependence and a repaired shared bad-block-counter
  race. This slice scheme does not establish serial EPZS equivalence.
- [VapourSynth MVTools](https://raw.githubusercontent.com/dubhatervapoursynth/vapoursynth-mvtools/master/readme.rst):
  framework threading, with Analyse temporal prediction removed because it
  conflicts with threading. This is an algorithmic tradeoff.
- [2017 FFmpeg discussion](https://ffmpeg.org/pipermail/ffmpeg-devel/2017-February/207471.html)
  points to unfinished alternative `mcfps`;
  [2022 threading request](https://ffmpeg.org/pipermail/ffmpeg-devel/2022-March/294793.html)
  supplies no implementation. A bounded search did not locate a maintained exact
  bidir/EPZS threading/GPU patch; this is not proof none exists.
- [Futatabi](https://nageru.sesse.net/doc/futatabi.html) implements GPU DIS flow and
  occlusion-aware interpolation through OpenGL. Its
  [distribution site](https://nageru.sesse.net/) lists 2.3.4 (September 2026) and
  identifies Nageru's GPL-3-or-later license. Useful architecture, different
  estimator; check individual file licensing before reuse.
- [Lu and Hang, VCIP 2011](https://mcube.lab.nycu.edu.tw/~hmhang/publications/Conf/LuCT_VCIP2011.pdf):
  CUDA MODS replaces search to expose parallelism. Reported encoder speedups over
  EPZS are not an output-preserving EPZS port or a forecast for current hardware.
