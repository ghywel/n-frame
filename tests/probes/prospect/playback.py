#!/usr/bin/env python3
"""Normal 25->60 context for the TV witness; no missing-frame ground truth.

playback.py OUT: uses tv/native-73's full-rate reference, not its decimated
input. High and linear side by side for human review; retained instants checked.
This deliberately narrow driver refuses other rates/paths rather than silently
generalise the 5-source-frames / 12-output-frames alignment witness.
"""
import itertools
import json
from pathlib import Path
import shutil
import sys
import reconstruct as r


def main(out):
    src = out/'tv/native-73'; root = src/'playback60'; root.mkdir(exist_ok=True)
    if r.probe(src/'ref.mkv')['r_frame_rate'] != '25/1':
        raise ValueError('this witness requires a 25 fps source')
    shutil.copyfile(src/'high.glsl', root/'high.glsl')
    for name in ['linear', 'high']:
        mix = 'linear' if name == 'linear' else 'custom_n:custom_shader_path=high.glsl'
        r.call([r.FF, '-nostdin', '-y', '-v', 'warning', '-init_hw_device', 'vulkan=vk',
                '-filter_hw_device', 'vk', '-i', str(src/'ref.mkv'), '-vf',
                f'libplacebo=fps=60:frame_mixer={mix},format=yuv420p', '-an', '-c:v', 'ffv1',
                str(root/f'{name}.mkv')], root, name+'.log')
    w, h = 1440, 1080
    refs = {n: a for n, a in enumerate(r.frames(src/'ref.mkv',w,h)) if n%5 == 0}
    retained = []; count = 0; marker = object()
    for n, pair in enumerate(itertools.zip_longest(r.frames(root/'high.mkv',w,h),
                                                   r.frames(root/'linear.mkv',w,h),fillvalue=marker)):
        if any(x is marker for x in pair):
            raise ValueError('playback count mismatch')
        count += 1
        if n%12 == 0 and n//12*5 in refs:
            retained.append(r.rms(pair[0],refs[n//12*5]))
    assert count == 178 and max(retained) <= 2.55
    # Compact watch copy: left High, right linear, no fictitious truth column.
    r.call([r.FF, '-nostdin', '-y', '-v', 'warning', '-i', str(root/'high.mkv'), '-i', str(root/'linear.mkv'),
            '-filter_complex', '[0:v][1:v]hstack=inputs=2,scale=1920:-2[o]', '-map', '[o]',
            '-an', '-c:v', 'h264_videotoolbox', '-b:v', '10M', '-pix_fmt', 'yuv420p',
            str(root/'high-left-linear-right.mp4')], root, 'watch.log')
    # Parent sources bracket output 93 (1.55s): source 38 at 1.52s and 39 at
    # 1.56s. Comparison is context, not a correctness score at 1.55s.
    inputs = [(src/'ref.mkv',38), (root/'high.mkv',93), (root/'linear.mkv',93), (src/'ref.mkv',39)]
    cmd = [r.FF,'-nostdin','-y','-v','warning']; filters=[]
    for i,(path,n) in enumerate(inputs):
        cmd += ['-i',str(path)]
        filters.append(f"[{i}:v]select='eq(n,{n})',setpts=N/TB,crop=360:268:494:502,scale=480:-2[x{i}]")
    filters.append('[x0][x1][x2][x3]hstack=inputs=4[o]')
    cmd += ['-filter_complex',';'.join(filters),'-map','[o]','-frames:v','1','-update','1',str(root/'context.png')]
    r.call(cmd,root,'context.log')
    result = dict(source_fps=25,output_fps=60,frames=count,retained_instants=len(retained),
                  retained_max_rms=max(retained),ground_truth_for_inserted_frames=False,
                  context_columns=['source 38','High 93','linear 93','source 39'],
                  context_alpha=.75,watch_columns=['High','linear'])
    r.save(root/'playback.json',result); print(json.dumps(result))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
