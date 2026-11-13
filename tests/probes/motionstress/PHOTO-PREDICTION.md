# Photographic translation follow-up

Registered 2026-11-13 before rendering the photographic cases. The analytic face
proxy exposed a geometric-warp defect, but does not cover photographic skin,
hair and facial detail. This follow-up uses a fixed grayscale head crop from an
already cached source frame; no new NAS read is needed. The crop and identifying
source metadata remain external scratch, not repository assets.

Two cases, 640x360, twelve 24-fps source frames:

- `photo_fast`: the head patch translates +32 full pixels per source frame over
  the same stationary multiscale background as the analytic tests.
- `photo_counterpan`: identical head motion, background -12 pixels per frame.

The crop is 155x215 pixels. It is reconstructed as a continuous bilinear intensity
surface and placed under a soft elliptical coverage mask wholly inside the crop.
Every requested frame, including fractional truth times, resamples that same
surface directly; there is no repeated video resampling or rounded trajectory.
Two-by-two spatial quadrature is applied identically at source and truth times.
ROI covers the moving layer, while a narrower feature mask covers the visible
eye/brow, nose and mouth. The mask locations are registered from inspecting the
source preview, not from shader error maps.

Prediction: a fix for erroneous sampling of an A-indexed displacement field can
benefit translating photographic features too. Reject a general photographic
improvement claim if either case's feature or worst-cell score regresses, if a
render/count/alignment guard fails, or if inspection finds a new silhouette tear
despite better averages. Static/subpixel CPU controls must pass first.

The truth is controlled translation of a photographed plane, not a true three-
dimensional face. It contains no expression change, turning, self-occlusion or
newly revealed facial texture. The synthetic elliptical outline is a compositing
boundary, not anatomical segmentation; crop background may move with that plane.
Passing these cases supports only this bounded translation claim. The original
footage and full regression gate remain necessary for adoption.

API: `configure(path_to_external_npy)` validates and loads the float grayscale
patch; `render(name,t)` has the same three-array interface as scenes.py. Explicit
configuration is required so no private source path is embedded in the tool.
