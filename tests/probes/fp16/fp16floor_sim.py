"""fp16floor_sim.py <out.raw> fp16|fp32 : fabricate fp16floor.sh's raw (512x8, 3 frames, rgb48le) under the hook's
arithmetic, rounding each channel to fp16 (the L10 hypothesis) or leaving it fp32 (its negation), then to 16 bits.
CPU only. Calibrates fp16floor_decode.py: fp16 must PASS, fp32 must KILL."""
import sys, numpy as np
path, mode = sys.argv[1], sys.argv[2]
W, H = 512, 8
img = np.zeros((H, W, 3), np.float64)
for j in range(32):
    s, k = j // 16, j % 16
    f = np.float32((4.0 if s == 0 else 5.9) + k / 128.0)
    r = np.float32(0.5) + f * np.float32(0.5 / 32.0)
    h = f * np.float32(0.5); w = np.floor(h)
    g = h - w
    b = ((w + 16) * 32 + 16) / np.float32(1024.0)
    v = np.array([r, g, b], np.float32)
    if mode == "fp16":
        v = v.astype(np.float16).astype(np.float64)
    img[:, 16 * j:16 * (j + 1), :] = v
u16 = np.rint(np.clip(img, 0, 1) * 65535).astype("<u2")
with open(path, "wb") as fh:
    for _ in range(3): fh.write(u16.tobytes())
