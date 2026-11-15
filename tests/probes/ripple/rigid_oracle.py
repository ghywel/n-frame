#!/usr/bin/env python3
"""Replace only final-warp displacement with the registered rigid plane's exact flow.

rigid_oracle.py PREV_NO_FALLBACK.glsl OUT.glsl
The estimator and cut code still execute. An oracle picture mismatch invalidates
the control; this shader is not a usable interpolator for arbitrary footage.
"""
import hashlib
from pathlib import Path
import sys

EXPECTED='0d8ec94d53dbbd7a607265eb3c62f62ccab3797df58ad3c580e5efe5ac9cc3c6'
ANCHOR='    vec2 flow_ab = FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;'
ORACLE='    vec2 flow_ab = vec2(-16.0, 0.0) * HOOKED_pt; // Registered exact rigid-plane displacement.'


def add(text):
    if hashlib.sha256(text.encode()).hexdigest()!=EXPECTED or text.count(ANCHOR)!=1:
        raise ValueError('requires the pinned preceding High without coherence fallback')
    out=text.replace(ANCHOR,ORACLE)
    assert out.replace(ORACLE,ANCHOR)==text
    return out


if __name__=='__main__':
    Path(sys.argv[2]).write_text(add(Path(sys.argv[1]).read_text()))
