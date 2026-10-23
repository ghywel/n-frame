# Render a native window's half-rate input back to full rate with each shader and score ONE withheld frame against
# its original: whole-frame PSNR Y, the 8x8 SSIM of GPT's tool, and the worst 16x16-grid cell's luma RMS.
import sys, os, json, subprocess, numpy as np
d, frame, rate, W, H = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
shaders = dict(a.split('=', 1) for a in sys.argv[6:])
ff = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
env = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
def luma(path, chain, hw):
    cmd = [ff, '-nostdin', '-v', 'error'] + (['-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk'] if hw else []) + \
          ['-i', path, '-vf', chain + f",select='eq(n\\,{frame})'", '-fps_mode', 'passthrough', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    r = subprocess.run(cmd, capture_output=True, env=env)
    if len(r.stdout) != W * H or b'compile status' in r.stderr.lower(): sys.exit(f'refused {chain[:40]}: {r.stderr[-200:]}')
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W).astype(float)
ref = luma(f'{d}/ref.mkv', 'null', False)
def ssim8(a, b):
    h, w = (H // 8) * 8, (W // 8) * 8
    A = a[:h, :w].reshape(h // 8, 8, w // 8, 8); B = b[:h, :w].reshape(h // 8, 8, w // 8, 8)
    ma, mb = A.mean((1, 3)), B.mean((1, 3)); va, vb = A.var((1, 3)), B.var((1, 3))
    cov = ((A - ma[:, None, :, None]) * (B - mb[:, None, :, None])).mean((1, 3)); C1, C2 = (.01 * 255) ** 2, (.03 * 255) ** 2
    return float((((2 * ma * mb + C1) * (2 * cov + C2)) / ((ma ** 2 + mb ** 2 + C1) * (va + vb + C2))).mean())
res = {}
for name, sh in shaders.items():
    chain = f'libplacebo=fps={rate}:frame_mixer=linear' if sh == 'linear' else f'libplacebo=fps={rate}:frame_mixer=custom_n:custom_shader_path={sh}'
    im = luma(f'{d}/half.mkv', chain, True); e = (im - ref) ** 2
    cells = [e[int(i*H/16):int((i+1)*H/16), int(j*W/16):int((j+1)*W/16)].mean() for i in range(16) for j in range(16)]
    k = int(np.argmax(cells))
    res[name] = dict(psnr=float(10 * np.log10(255 ** 2 / e.mean())), ssim8=ssim8(im, ref), worst_cell_rms=float(np.sqrt(cells[k])), worst_cell=[k % 16, k // 16])
    print(f"{name:10s} PSNR {res[name]['psnr']:6.2f}  SSIM8 {res[name]['ssim8']:.4f}  worst cell RMS {res[name]['worst_cell_rms']:6.2f} at {res[name]['worst_cell']}", flush=True)
json.dump(res, open(f'{d}/withheld-{frame}-local.json', 'w'), indent=1)
