#!/usr/bin/env python3
"""Controlled translation of an external photographic head crop; no bundled media.

configure(npy_path), then render(case,t)->(float32 gray HxW, ROI bool, features bool).
Ground truth: a fixed bilinear image surface, translated continuously. See PHOTO-PREDICTION.md.
"""
from pathlib import Path

import numpy as np

W, H, N, FPS = 640, 360, 12, 24
SOURCE_FRAMES, SOURCE_FPS = N, FPS
CASES = {
    'photo_fast': dict(kind='photo', velocity=(32., 0.), background=(0., 0.)),
    'photo_counterpan': dict(kind='photo', velocity=(32., 0.), background=(-12., 0.)),
}
_PATCH = None
_Y, _X = np.mgrid[:H, :W].astype(np.float32)+.5


def configure(path):
    global _PATCH
    a = np.load(Path(path), allow_pickle=False)
    if a.shape != (215, 155) or a.dtype.kind != 'f':
        raise ValueError('expected a 215x155 float grayscale crop')
    if not np.isfinite(a).all() or a.min() < 0 or a.max() > 1:
        raise ValueError('photographic crop must be finite and in [0,1]')
    _PATCH = a.astype(np.float32)


def _bilinear(u, v):
    h, w = _PATCH.shape
    u = np.clip(u, 0, w-1); v = np.clip(v, 0, h-1)
    x = np.floor(u).astype(np.int32); y = np.floor(v).astype(np.int32)
    xx = np.minimum(x+1,w-1); yy = np.minimum(y+1,h-1)
    a, b = u-x, v-y
    return ((_PATCH[y,x]*(1-a)+_PATCH[y,xx]*a)*(1-b)
            +(_PATCH[yy,x]*(1-a)+_PATCH[yy,xx]*a)*b)


def _sample(c,t,x,y):
    tau = t-(N-1)/2
    vx, vy = c['velocity']; bx, by = c['background']
    dx, dy = x-(W/2+vx*tau), y-(H/2+vy*tau)
    u, v = dx+77., dy+107.
    rho = np.sqrt((dx/70.)**2+(dy/100.)**2)
    # Two-pixel feather, still at least six pixels from the crop's four edges.
    alpha = np.clip((1-rho)*70./2+.5,0,1)
    fg = _bilinear(u,v)
    xx, yy = x-bx*t, y-by*t
    bg = (.37+.055*np.sin(.113*xx+.067*yy)+.04*np.cos(.053*xx-.139*yy)
          +.035*np.sin(.317*xx)*np.cos(.269*yy)+.025*np.sin(.021*xx+.037*yy))
    roi = rho < 1.12
    features = (((u-104)/23)**2+((v-103)/12)**2 < 1)
    features |= (((u-125)/16)**2+((v-132)/20)**2 < 1)
    features |= (((u-114)/20)**2+((v-157)/10)**2 < 1)
    features &= alpha > .99
    return bg*(1-alpha)+fg*alpha,roi,features


def render(name,t):
    if _PATCH is None:
        raise RuntimeError('call photo.configure(external_npy_path) before rendering')
    c = CASES[name]
    im = np.zeros((H,W),np.float32)
    for dy in (-.25,.25):
        for dx in (-.25,.25):
            im += _sample(c,float(t),_X+dx,_Y+dy)[0].astype(np.float32)*.25
    _,roi,features = _sample(c,float(t),_X,_Y)
    return im,roi,features


def smoke():
    for name in CASES:
        for t in (0.,5.5,11.):
            im,roi,features=render(name,t)
            assert im.shape==roi.shape==features.shape==(H,W)
            assert np.isfinite(im).all() and im.min()>=0 and im.max()<=1
            assert roi.any() and features.any()
        a=render(name,4.)[0]; b=render(name,4.125)[0]
        assert np.max(np.abs(a-b))>.001
    c=dict(velocity=(0.,0.),background=(0.,0.))
    assert np.array_equal(_sample(c,0.,_X,_Y)[0],_sample(c,7.25,_X,_Y)[0])
    print('photo cases: shape/range/masks/subpixel/static controls PASS')
