# High's final half-res flow A->B at a chosen pair, read through bar_gpu's split-encoded tail (calibrated there).
import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cage'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import bar_gpu as gpu
src, shader, pair, W, H, rate, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6], sys.argv[7]
tail = gpu.shader(6, False); tail = tail[tail.rindex('//!HOOK FRAME_MIX'):]
g = out + '.glsl'; open(g, 'w').write(open(shader).read() + '\n' + tail)
env = dict(os.environ, MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
ff = os.path.expanduser('~/np-build/ffmpeg/ffmpeg')
r = subprocess.run([ff, '-nostdin', '-y', '-hide_banner', '-loglevel', 'warning', '-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk',
    '-i', src, '-vf', f"format=rgba64le,libplacebo=fps={rate}:frame_mixer=custom_n:custom_shader_path={g}:dithering=none:format=rgba64le,select='eq(n\\,{pair})'",
    '-fps_mode', 'passthrough', '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba64le', out + '.raw'], capture_output=True, text=True, env=env)
if r.returncode or any(s in r.stderr.lower() for s in ['compile status', 'disabling', 'failed to']): sys.exit('render refused: ' + r.stderr[-300:])
a = np.fromfile(out + '.raw', '<u2').astype(float) / 65535
if a.size != W * H * 4: sys.exit(f'wrong size {a.size}')
a = a.reshape(H, W, 4); p = a[..., 2] * 1024
if np.max(abs(p - np.rint(p))) > .05: sys.exit('split readback invalid')
z = np.rint(p).astype(int); v = np.stack([2 * (z // 32 - 16 + a[..., 0]), 2 * (z % 32 - 16 + a[..., 1])], -1)
np.save(out + '.npy', v); print('saved', out + '.npy', 'median', np.median(v.reshape(-1, 2), 0))
