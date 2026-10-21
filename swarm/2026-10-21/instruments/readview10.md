# read_view 10: the velocity field read past the fp16 readback floor, as a mode, not a pass

Lane instruments, 2026-10-21. Paper only. Against `REPO/tests/add_human_reading.py` as it stands at worktree HEAD 782c821 (the file last changed in 4b6ad3b). Nothing written into REPO; this is the patch I would make. Tags: [R] read, [J] judgement, [U] unchecked.

## The design in one paragraph

[R] The machine modes return `0.5 + f * (0.5 / fs)` with fs = 32 for velocity (L407-411, L427-430); L10 says that output passes an fp16 stage, whose step near 0.5 is 1/2048, so f is read to 1/32 px. [J] Spending the mantissa on an offset of 0.5 is what costs it. The split encoding writes the fraction of f/2 to a channel of its own (exact in fp16 to at least 2^-11 of 2 px = 1/1024 px, finer below 0.5) and packs the two whole parts of x/2 and y/2, offset by +16, into one channel as (wx * 32 + wy) / 1024: every value k/1024 with k < 1024 is exact in fp16, the range is -32..+31.9 px as before, and it fits rgb48le without alpha. Decode: code = round(B * 1024); wx = code div 32 - 16; wy = code mod 32 - 16; x = 2 wx + 2 R; y = 2 wy + 2 G. `probes/window/window_live.sh` L14-19 and TESTING.md L2439-2443 did the same for a scalar and read it to 0.0005.

## The one condition, checked in the GLSL

[R] `READ_FIELD` is written by passes at `//!WIDTH HOOKED.w 8 /` and `//!HEIGHT HOOKED.h 8 /` (L170-171, and L134-135 for the N-frame family). The painter that holds the machine branch runs at `//!WIDTH FRAME_MIX.w` / `//!HEIGHT FRAME_MIX.h` (L385-386) and binds `READ_FIELD` (L379). Its machine branch samples `READ_FIELD_tex(FRAME_MIX_pos)` (L429): a full-resolution position into a 1/8-resolution texture, which the sampler filters between the four nearest cells ([U] libplacebo's hook textures sample linearly by default; the record's read_view 4 numbers are those blends). For read_view 4 the blend is harmless. For the split encoding it is fatal: between a cell whose x/2 is 2.98 (fraction 0.98) and one at 3.01 (fraction 0.01) the blended fraction is about 0.5 and the blended whole part is between slots, so the decode is off by up to a whole 2-px unit. So the mode must sample the cell's own centre: `(floor(FRAME_MIX_pos * READ_FIELD_size) + 0.5) / READ_FIELD_size`, which is `probes/repairs/l4_coarse_fraction.py` L39's idiom, and `READ_FIELD_size` is already used in this file (L214, L274), so the name exists for a bound texture [R].

[J] A consequence the calibration must allow for: read_view 10 reports one cell, read_view 4 a blend of four. On a smooth field they differ by up to the inter-cell gradient, not only by the floor; compare them on a uniform translation first (where cells agree), then on the sweep.

## The diff

```diff
--- a/tests/add_human_reading.py
+++ b/tests/add_human_reading.py
@@ -108,7 +108,7 @@ def build_tail(text, default):
     param = f"""//!PARAM read_view
-//!DESC 0 = normal output; 1/2/3 = velocity/acceleration/jerk painted for a human; 4/5/6 = the same fields raw, for a machine; 7 = the pooled reading raw; 8 = the per-cell mode memory raw; 9 = divergence, curl, shear raw
+//!DESC 0 = normal output; 1/2/3 = velocity/acceleration/jerk painted for a human; 4/5/6 = the same fields raw, for a machine; 7 = the pooled reading raw; 8 = the per-cell mode memory raw; 9 = divergence, curl, shear raw; 10 = velocity raw, split past the fp16 floor: R = fract(x/2), G = fract(y/2), B = ((floor(x/2)+16)*32 + floor(y/2)+16)/1024, +-32 px read to 1/1024 px, one cell per texel (REPAIRS.md L10, 2026-10-21)
 //!TYPE int
 //!MINIMUM 0
-//!MAXIMUM 9
+//!MAXIMUM 10
 {default}
 
@@ -425,6 +425,15 @@ vec4 hook() {{
     if (read_view == 8)      // the per-cell mode memory, raw
         return vec4(0.5 + READ_MODE_tex(FRAME_MIX_pos).xy * (0.5 / READ_MACHINE_FS_VEL), 0.5, 1.0);
+    if (read_view == 10) {{  // velocity raw, SPLIT (2026-10-21, REPAIRS.md L10): the fraction of x/2, y/2 exact in fp16,
+                             // the whole parts packed; read to 1/1024 px where read_view 4 reads to 1/32
+        // READ_FIELD is 1/8 res and this pass is full res: sample the cell's own centre, never between cells -- a
+        // bilinear blend across a whole-part step wraps the fraction and lands between slots (l4_coarse_fraction.py's idiom)
+        vec2 c = (floor(FRAME_MIX_pos * READ_FIELD_size) + 0.5) / READ_FIELD_size;
+        vec2 h = clamp(READ_FIELD_tex(c).xy, -32.0, 31.9375) * 0.5;   // the rail, as FS 32 railed; count texels there
+        vec2 w = floor(h);
+        return vec4(fract(h.x), fract(h.y), ((w.x + 16.0) * 32.0 + (w.y + 16.0)) / 1024.0, 1.0);
+    }}
     if (read_view >= 4) {{
         float fs = (read_view == 4) ? READ_MACHINE_FS_VEL : (read_view == 5) ? READ_MACHINE_FS_ACC : READ_MACHINE_FS_JERK;
         vec2 f = READ_FIELD_tex(FRAME_MIX_pos).xy;
```

Why nothing else changes: [R] `bool vel = (read_view == 1 || read_view == 4 || read_view >= 7)` (L420, L363) already treats 10 as velocity, and in the N-frame family the TRI_DIAG map `read_view >= 7 ? 7` (L148) selects the velocity field for it. [R] Every tail pass carries `//!WHEN read_view 0 >` (L106), so at read_view 0 the tail is skipped and the picture is untouched (`fielddiag.py` L8-9 says the same). The assertion at L484 (`//!PARAM read_view` exactly once) still holds. Braces are doubled because the pass is an f-string.

## Decoder side (for `fieldcheck.py`, not in this diff)

A `--split` decode: x = 2 (code div 32 - 16) + 2 R, y = 2 (code mod 32 - 16) + 2 G. Its zero-level instrument check (`fieldcheck.py` L35-45) must expect, off the object, R = G = 0 and B = 528/1024 = 0.515625, not 0.5. The 16-bit output step is 2/65535 = 3e-5 px, not binding. [U] Whether libplacebo dithers a 16-bit output; `fp16floor.sh`'s residuals answer it (rerun with `DITHER=none` if they are off the grid).

## Calibration (what `fp16floor.sh` does, and what follows it)

1. Known constant, no estimator (`fp16floor.sh`): single channel on the 1/32 grid, at most 5 distinct per 16; split within 1/1024 px on all 32, the wrap at set B k = 13 right. PASS/KILL/FAIL as its header says.
2. The mode on a real shader, uniform translation (L1-type box at exactly 8 px/frame, N:N): read_view 10 and read_view 4 must agree to 1/32 px on every interior cell (the blend is harmless on a uniform field), and read_view 10 must read 8.000 within 1/1024 px if the estimator lands there, else the residual is the estimator's and the mathematics lane's 1/64-1/32 px FLOW_H_AB rounding should show as a staircase at THAT pitch. This is the first time the record can see which stage is binding.
3. Counterfactual: the same with the cell-centre line replaced by `READ_FIELD_tex(FRAME_MIX_pos)` must show whole-unit errors at cell seams on any field whose x/2 crosses an integer between neighbours. If it does not, the sampler is not linear and the condition was unneeded; the line costs nothing either way.

## Risk

- [R] Every generator calls `add_human_reading.py` last (TOOLS.md L85), so this changes the text of every generated shader: `smoke.sh` steps 3-3e (TOOLS.md L118) compare the committed files byte for byte and will fail until the 28 generated files and their `-4k` twins are regenerated by their recipes (REPAIRS.md, "How it was done", item 2). The Metal port's graphs are matched to their GLSL by hash (TESTING.md, lockstep PASS 2026-10-21), so NFrameDemo's lockstep must be rerun after regeneration. [J] This is the main cost: a text change everywhere for a mode nobody renders by default.
- [J] The picture at read_view 0 is byte-identical (the tail is skipped), so the ladder must not move beyond the dither wander; that is the kill check on the regenerated files (6 GPU minutes per shader; the recommendation and High tier suffice).
- [U] Whether every host clamps `read_view` to `//!MAXIMUM`; the Metal port turns `//!PARAM` blocks into live uniforms (TOOLS.md L105) and may need its own range check updated.
- [J] The clamp rails at -32 and +31.9375 silently, as FS 32 did; `fieldexport.py`'s rule applies (count texels at the rail against live texels).
- [J] An alternative with no text change anywhere: a probe-style shader built the way `l4_coarse_fraction.py` builds its own (replace the painter's `hook()` at run time, L31-40 of that probe) carrying this same branch. It measures without touching the family; it cannot be a standing mode. If the regeneration cost is unwelcome tonight, that is the route for calibration step 2.
