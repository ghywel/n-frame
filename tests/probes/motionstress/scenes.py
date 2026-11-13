#!/usr/bin/env python3
"""Analytic bars, pans and face proxies; registration and limits in SCENES.md.

render(case_name, source_frame_time) -> luma, roi, feature_mask (H,W)
motion(case_name) -> layer velocities in full pixels/source frame
All coordinates/trajectories are continuous; no nearest-frame rendering.
"""
import numpy as np

W, H, N, FPS = 640, 360, 12, 24
SOURCE_FRAMES, SOURCE_FPS = N, FPS
CASES = {
    'face_static': dict(kind='face', velocity=(0., 0.), background=(0., 0.)),
    'face_slow': dict(kind='face', velocity=(3., 0.), background=(0., 0.)),
    'face_fast': dict(kind='face', velocity=(32., 0.), background=(0., 0.)),
    'face_counterpan': dict(kind='face', velocity=(32., 0.), background=(-12., 0.)),
    'face_occluded': dict(kind='face', velocity=(32., 0.), background=(0., 0.), rails=True),
    'face_lowcontrast': dict(kind='face', velocity=(32., 0.), background=(0., 0.), contrast=.32),
    'pan_detail': dict(kind='pan', velocity=(40., 0.), background=(40., 0.)),
    'pan_mixed': dict(kind='pan', velocity=(48., 0.), background=(48., 0.), mixed=True),
    'bars_v9': dict(kind='bars', velocity=(24., 0.), background=(0., 0.), period=9., angle=0., phase=.37),
    'bars_v24': dict(kind='bars', velocity=(32., 0.), background=(0., 0.), period=24., angle=0., phase=.71),
    'bars_h9': dict(kind='bars', velocity=(0., 16.), background=(0., 0.), period=9., angle=np.pi/2, phase=.37),
    'bars_h24': dict(kind='bars', velocity=(0., 20.), background=(0., 0.), period=24., angle=np.pi/2, phase=.71),
    'bars_diagonal': dict(kind='bars', velocity=(24., 6.), background=(0., 0.), period=11., angle=.63, phase=.19),
    'bars_static': dict(kind='bars', velocity=(0., 0.), background=(0., 0.), period=9., angle=0., phase=.37),
    # Post-discovery, pre-second-run holdouts; see PLAN.md.
    'pan_detail37': dict(kind='pan', velocity=(37., 0.), background=(37., 0.)),
    'pan_detail43': dict(kind='pan', velocity=(43., 0.), background=(43., 0.)),
    'pan_mixed45': dict(kind='pan', velocity=(45., 0.), background=(45., 0.), mixed=True),
}
_Y, _X = np.mgrid[:H, :W].astype(np.float32) + .5


def _texture(x, y):
    return (.37 + .055*np.sin(.113*x+.067*y) + .04*np.cos(.053*x-.139*y)
            + .035*np.sin(.317*x)*np.cos(.269*y) + .025*np.sin(.021*x+.037*y))


def _bars(z, period, phase=0.):
    a = 2*np.pi*z/period + phase
    return .5 + .31*np.sin(a) + .08*np.sin(3*a)


def _box(x, y, rx, ry):
    return np.clip(rx+.5-np.abs(x), 0, 1) * np.clip(ry+.5-np.abs(y), 0, 1)


def _face(x, y, contrast=1.):
    rx, ry = 61., 83.
    rho = np.sqrt((x/rx)**2+(y/ry)**2)
    alpha = np.clip((1-rho)*rx+.5, 0, 1)
    # Smooth shading and skin detail, with deliberately small high-information features.
    skin = .69 + .075*np.exp(-((x+19)/37)**2-((y+20)/55)**2) - .04*x/rx
    skin += .012*np.sin(.43*x+.17*y)*np.cos(.31*y) + .007*np.sin(.77*x-.23*y)
    hair = np.exp(-((y+72)/16)**4) * np.exp(-(x/62)**8)
    skin -= .34*hair
    feature = np.zeros_like(x, dtype=bool)
    for eye in (-23., 23.):
        ex, ey = x-eye, y+18
        skin -= .28*np.exp(-(ex/9)**2-(ey/3.6)**2)
        skin -= .18*np.exp(-(ex/2.8)**2-(ey/4.2)**2)
        skin += .18*np.exp(-((ex+1)/1.4)**2-((ey+1)/1.3)**2)
        brow_y = y+29 + .05*ex
        skin -= .16*np.exp(-(ex/12)**4-(brow_y/2.2)**2)
        feature |= ((ex/15)**2+(ey/9)**2 < 1) | ((ex/16)**2+(brow_y/5)**2 < 1)
    skin += .075*np.exp(-((x+3)/4)**2-((y-3)/20)**2)
    skin -= .13*np.exp(-((x-5)/5)**2-((y-8)/16)**2)
    skin -= .11*np.exp(-(x/9)**2-((y-20)/3)**2)
    lip_y = y-40 + .007*x*x
    skin -= .23*np.exp(-(x/22)**4-(lip_y/2.2)**2)
    skin += .05*np.exp(-(x/18)**4-((lip_y-3)/1.7)**2)
    feature |= ((x/13)**2+((y-7)/24)**2 < 1) | ((x/26)**2+(lip_y/7)**2 < 1)
    skin = .37 + contrast*(skin-.37)
    return skin, alpha, feature & (alpha > .99)


def _sample(c, t, x, y):
    vx, vy = c['velocity']; bx, by = c['background']
    tau = t-(N-1)/2
    if c['kind'] == 'pan':
        u, v = x-vx*t, y-vy*t
        im = _texture(u, v)
        if c.get('mixed'):
            a = _box(np.mod(u+400, 480)-240, v-H/2, 68, 115)
            b = _box(np.mod(u+150, 480)-240, v-H/2, 62, 110)
            im = im*(1-a) + _bars(u, 13.7, .37)*a
            im = im*(1-b) + _bars(v+.17*u, 21.3, .71)*b
        roi = np.ones_like(x, dtype=bool)
        return im, roi, roi
    bg = _texture(x-bx*t, y-by*t)
    u, v = x-(W/2+vx*tau), y-(H/2+vy*tau)
    if c['kind'] == 'face':
        fg, alpha, features = _face(u, v, c.get('contrast', 1.))
        im = bg*(1-alpha) + fg*alpha
        roi = np.sqrt((u/61)**2+(v/83)**2) < 1.18
        if c.get('rails'):
            rail = np.maximum.reduce([np.clip(5.5-np.abs(x-center), 0, 1)
                                      for center in (262., 340., 418.)])
            im = im*(1-rail) + (.16+.025*np.sin(y*.07))*rail
            features &= rail == 0
        return im, roi, features
    angle, period = c['angle'], c['period']
    z = u*np.cos(angle)+v*np.sin(angle)
    alpha = _box(u, v, 100, 58)
    fg = _bars(z, period, c['phase'])
    # Co-moving nonperiodic boundary cues distinguish the material's true period basin.
    mark = np.exp(-((u+86)/5)**2-((v+37)/7)**2)
    mark += .7*np.exp(-((u-83)/7)**2-((v-34)/5)**2)
    fg = fg*(1-.75*mark)+.94*(.75*mark)
    im = bg*(1-alpha)+fg*alpha
    roi = (np.abs(u)<108) & (np.abs(v)<66)
    features = (((np.abs(np.cos(2*np.pi*z/period+c['phase']))>.85) & (alpha>.99))
                | ((np.abs(np.abs(u)-100)<2) & (np.abs(v)<60))
                | ((np.abs(np.abs(v)-58)<2) & (np.abs(u)<102)))
    return im, roi, features


def render(name, t):
    """Return antialiased luma and centre-sampled target/detail masks at continuous t."""
    c = CASES[name]
    accum = np.zeros((H, W), dtype=np.float32)
    for dy in (-.25, .25):
        for dx in (-.25, .25):
            im, _, _ = _sample(c, float(t), _X+dx, _Y+dy)
            accum += im.astype(np.float32)*.25
    _, roi, features = _sample(c, float(t), _X, _Y)
    return np.clip(accum, 0, 1), roi, features


def motion(name):
    """Ground-truth layer velocity metadata, not a visibility-labelled flow field."""
    c = CASES[name]
    return dict(foreground=c['velocity'], background=c['background'],
                occluder=(0., 0.) if c.get('rails') else None,
                units='full pixels per source frame')


def smoke():
    for name in CASES:
        for t in (0., 5.5, 11.):
            im, roi, features = render(name, t)
            assert im.shape == roi.shape == features.shape == (H, W)
            assert im.dtype == np.float32 and roi.dtype == features.dtype == bool
            assert np.isfinite(im).all() and im.min() >= 0 and im.max() <= 1
            assert roi.any() and features.any(), (name, t)
        a = render(name, 4.)[0]; b = render(name, 4.125)[0]
        if name.endswith('static'):
            assert np.array_equal(a, b), name
        else:
            assert np.max(np.abs(a-b)) > 1e-3, name
    print(f'{len(CASES)} cases: shape/range/masks/subpixel/static controls PASS')


if __name__ == '__main__':
    smoke()
