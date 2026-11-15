#!/usr/bin/env python3
"""GPT's exactness and timing gate (../mci_accel/gate.py), unchanged, with the mask range widened to 0..63
and 4:2:2 / 4:4:0 frame sizes known (the coloured edge fixtures, colour_fixtures.py).

    gate_fused.py check|bench ...        exactly gate.py's arguments (see ../mci_accel/GATE.md)

Bit 16 is the fused overlap stage, bit 32 the wavefront search (PLAN.md). Nothing else differs: the module is imported and two functions replaced.
"""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('gate', Path(__file__).resolve().parents[1] / 'mci_accel' / 'gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def configs(text):
    result = []
    for item in text.split(','):
        mask, threads = map(int, item.split(':'))
        gate.require(0 <= mask <= 63 and 1 <= threads <= 64, 'invalid mask:threads')
        gate.require((mask, threads) not in result, 'duplicate mask:threads')
        result.append((mask, threads))
    gate.require(bool(result), 'empty configurations')
    return result


def frame_bytes(case):
    """gate.py's rule for 4:2:0 and 4:4:4, and the two samplings the coloured edge fixtures add."""
    w, h = case['width'], case['height']
    cw, ch = {'yuv420p': (1, 1), 'yuv444p': (0, 0), 'yuv422p': (1, 0), 'yuv440p': (0, 1)}.get(case['pix_fmt'], (None, None))
    gate.require(cw is not None, 'unsupported gate pixel format')
    return w * h + 2 * ((w + (1 << cw) - 1) >> cw) * ((h + (1 << ch) - 1) >> ch)


gate.configs = configs
gate.frame_bytes = frame_bytes
if __name__ == '__main__':
    gate.main()
