#!/usr/bin/env python3
"""Actual video-path counterfactual: corrupt only a withheld GPU output frame.

fault_control.py OUT (after reconstruct.py controls OUT). Every retained frame
stays intact, so alignment must still pass; the injected defect must rank first.
No GPU job or footage input; uses the previously rendered synthetic control.
"""
import json
from pathlib import Path
import sys
import reconstruct as r


def main(out):
    root = out / 'controls'
    r.call([r.FF, '-nostdin', '-y', '-v', 'warning', '-i', str(root/'high.mkv'), '-vf',
            "drawbox=x=96:y=48:w=64:h=48:color=white:t=fill:enable='eq(n,25)'", '-an',
            '-c:v', 'ffv1', str(root/'corrupt.mkv')], root, 'corrupt.log')
    original = json.loads((root/'metrics.json').read_text())
    broken = r.measure(root, 256, 128, '24', high='corrupt')
    ranked = r.shortlist(broken)
    top = ranked['candidates'][0]
    assert top['frame'] == 25 and top['regression'] and top['local_regression']
    assert broken['retained_max'] == original['retained_max']
    result = dict(injected_frame=25, top_frame=top['frame'], loss_db=top['loss_db'],
                  ssim_shader=top['ssim_shader'], ssim_linear=top['ssim_linear'],
                  retained_unchanged=True, alignment_passed=True, fault_detected=True)
    r.save(root/'fault-control.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
