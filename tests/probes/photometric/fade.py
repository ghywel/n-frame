# A still picture under a pure fade, no motion: F_n = clip(A * g**n). Truth flow zero; the true withheld frame is
# A * g**(n+.5) up to clipping and rounding, which the reference stream carries exactly (made at the full rate).
import sys, numpy as np, subprocess, os
src, out, W, H, g, N, rate = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
ff = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
raw = subprocess.run([ff, '-v', 'error', '-i', src, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'], capture_output=True).stdout
A = np.frombuffer(raw, '<u2').reshape(H, W, 3).astype(float) / 65535
A = A * 0.55                                       # start dark enough that the fade never clips
frames = [np.clip(A * g ** (k / 2), 0, 1) for k in range(2 * N)]     # full rate: half-steps of the fade
full = np.stack([np.rint(f * 65535).astype('<u2') for f in frames])
full.tofile(out + '-full.rgb48'); full[::2].tofile(out + '-half.rgb48')
print('fade frames', len(frames), 'last max', float(frames[-1].max()))
