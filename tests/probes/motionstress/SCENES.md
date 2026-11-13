# Motion stress scenes: registration before rendering

2026-11-13. These are new synthetic controls for the two-frame High shader's bar,
fast-pan and translating-face failures. No shader outcome was used to choose the
cases. Twelve source frames at 24 fps; analytic truth can be evaluated at any
fractional source-frame time. Native size 640x360. Motion is in full pixels per
source frame, not pixels per output frame.

The intended advance over a small, rigid textured square is a finite periodic
object with an informative boundary, a whole-frame pan containing several spatial
scales, and a face-shaped smooth surface whose small eyes, nose and mouth can be
damaged despite an acceptable whole-frame score. These are analytic face proxies,
not photographs or claims of full facial realism.

Registered cases:

| Case | Motion and purpose |
|---|---|
| face_static | Zero-motion control, all details fixed. |
| face_slow | Face +3 px/frame, still background; ordinary motion control. |
| face_fast | Face +32 px/frame, still background; detail/boundary damage. |
| face_counterpan | Face +32, background -12 px/frame; competing layers. |
| face_occluded | Face +32 behind three fixed foreground rails; visible-feature and visibility test. |
| face_lowcontrast | Same +32, face contrast reduced around background mean; smooth-region reach. |
| pan_detail | Whole-frame +40 px/frame, multiscale continuous texture. |
| pan_mixed | Whole-frame +48 px/frame, finite windows of vertical/horizontal stripes and nonperiodic cues. |
| bars_v9 | Period-9 vertical bars, +24 x; moving finite outline anchors an aliased interior. |
| bars_v24 | Period-24 vertical bars, +32 x; larger displacement / different phase. |
| bars_h9 | Period-9 horizontal bars, +16 y; rotated counterpart. |
| bars_h24 | Period-24 horizontal bars, +20 y; axis-dependent sampler check. |
| bars_diagonal | Period-11 oblique bars, (+24,+6); two-component motion. |
| bars_static | Period-9 vertical bars, zero motion; no-repair-needed control. |

Every case returns full-frame truth, a foreground/target ROI and a feature mask.
Face feature masks cover eyes, brows, nose and lips; occluded features are excluded.
Bars' feature masks cover contrast transitions and outline; pan masks cover the
frame. Report whole-frame, ROI and feature errors separately, plus a high-tail or
worst-cell measure: a small feature defect must not disappear in an average of the
unchanging background. Static/slow controls must not acquire an apparent benefit
from accidental frame misalignment. Whole-frame pan features have no occlusion.

Spatial image formation is fixed: 2x2 area quadrature of continuous smooth
functions, with one-pixel coverage ramps at object/rail edges. Periodic bar intensity
uses two bounded harmonics, avoiding point-sampled discontinuous square waves.
Neither trajectories nor fractional-frame positions are rounded. No exposure
integration is applied: adding shutter blur is a separate future experiment.

`render(name, t)` returns `(float32_luma, bool_roi, bool_features)`, each HxW.
`motion(name)` reports the known layer velocities in full pixels per source frame;
it is not an optical-flow estimate and does not label disoccluded pixels. `smoke()`
checks finite/ranged output, nonempty masks, subpixel responsiveness, and exact
stationary identity, without invoking FFmpeg or a GPU.

After the first 14-case baseline, three additional pan holdouts were registered in PLAN.md before the next run:
`pan_detail37`, `pan_detail43`, and `pan_mixed45` (the same textures at 37, 43, 45 px/source frame). They test motions
between the global witness's 8 px candidate-grid steps. They were not part of the initial case selection.
