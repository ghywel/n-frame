#!/usr/bin/env python3
"""CPU attacks on L016's F1/F2 proposal, extended to L017's F1 estimator.

Prediction: residual trimming cannot distinguish translated ramps/exponentials
from affine brightness; a moving majority can cause static gain witnesses to be
trimmed away. F2's proposed zero-on-a-mean-removed-tie rule erases a correct
nonzero seed on a ramp; low-frequency sinusoids approach this with finite contrast.
No GPU results implied. The CPU fit is an explicit example of the planned family,
with a separate source-hash-guarded scalar mirror of the built F1.

attacks.py OUT [--fade-root DIR]: write JSON and an analytic three-frame fixture
outside git; optionally inspect Local's existing 24-frame RGB48 fade sources.
Units: intensities 0..1, displacements FULL-resolution pixels per input pair;
the 5x5 F2 test samples a half-resolution grid (two full pixels per tap).
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def fit(a, b, trim=0., rounds=3):
    x, y = a.ravel(), b.ravel()
    keep = np.ones(len(x), dtype=bool)
    for step in range(rounds+1):
        X = np.column_stack([x[keep], np.ones(keep.sum())])
        gain, bias = np.linalg.lstsq(X, y[keep], rcond=None)[0]
        residual = abs(y-(gain*x+bias))
        if trim and step<rounds:
            keep = residual <= np.quantile(residual, 1-trim)
    return float(gain), float(bias), keep.reshape(a.shape)


def zm_cost(a, b):
    return float(np.mean(abs((a-a.mean())-(b-b.mean()))))


def energy(a):
    # The shader primitive: absolute two-pixel gradient magnitude, degree
    # ONE in positive gain. Dense averaging/Gaussian smoothing are linear and
    # preserve this homogeneity. This is not the entire GLSL sampling graph.
    return abs(np.roll(a,-2,axis=0)-a)+abs(np.roll(a,-2,axis=1)-a)


def nuisance_information(i, gx, gy):
    # Linearised GLOBAL shared translation + affine-light model only:
    # dI = G u + Z theta, Z=[I,1]. Remove nuisance columns without claiming
    # that an independently moving scene has one shared displacement.
    G = np.column_stack([gx.ravel(),gy.ravel()])
    Z = np.column_stack([i.ravel(),np.ones(i.size)])
    residual = G-Z@np.linalg.lstsq(Z,G,rcond=None)[0]
    total = float(np.sum(G*G))
    return dict(motion_energy_after_light_projection=float(np.sum(residual*residual)),
                surviving_fraction=float(np.sum(residual*residual)/max(total,1e-30)),
                projected_motion_eigenvalues=np.linalg.eigvalsh(residual.T@residual).tolist())


def built_f1(a,b):
    """Float64 scalar mirror of eab98f9 global_gain.py, not GPU arithmetic."""
    assert a.shape==b.shape==(18,32)
    gain,bias,sigma,kept=1.,0.,1e9,0
    for iteration in range(4):
        mask=abs(b-(gain*a+bias))<=2.5*sigma
        kept=int(mask.sum())
        if not kept:break
        x,y=a[mask],b[mask];mx,my=x.mean(),y.mean()
        vx=(x*x).mean()-mx*mx
        gain=float(np.clip(((x*y).mean()-mx*my)/vx,.5,2.)) if vx>1e-4 else 1.
        bias=float(my-gain*mx)
        residual=b-(gain*a+bias)
        mask2=np.ones_like(mask) if iteration==0 else abs(residual)<=2.5*sigma
        sigma=max(float(np.sqrt(np.sum(residual[mask2]**2)/max(int(mask2.sum()),1))),.5/255)
    effect=max(abs(bias),abs(gain-1+bias))
    active=effect>=2.5/255 and kept>=288
    return dict(gain=gain if active else 1.,bias=bias if active else 0.,
                ungated_gain=gain,ungated_bias=bias,effect_dn=effect*255,active=bool(active),
                sigma_dn=sigma*255,kept=kept,mask=mask)


def implementation_attacks():
    source=Path(__file__).resolve().parents[2]/'global_gain.py'
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if sha!='4e509a19a35253b2ce4a5f06e776925f9817ffe6534fe2b033ce553f71c95321':
        raise ValueError('GLOBAL_GAIN changed; review the scalar mirror before reporting results')
    gy,gx=np.mgrid[0:18,0:32].astype(float)
    positive=.4+.12*np.sin(.3*gx+.2*gy)+.09*np.cos(.4*gx-.7*gy)
    recovered=built_f1(positive,1.06*positive+.017);recovered.pop('mask')
    assert recovered['active'] and abs(recovered['gain']-1.06)<1e-12
    assert abs(recovered['bias']-.017)<1e-12
    ramp_cases=[]
    for width in (256,512,1280):
        for d in (4.,8.,16.,32.):
            a=.15+.7*(gx+.5)/32
            b=a-.7*d/width
            result=built_f1(a,b);result.pop('mask')
            ramp_cases.append(dict(width_full_px=width,flow_full_px=d,**result))
    small=next(r for r in ramp_cases if r['width_full_px']==256 and r['flow_full_px']==4)
    assert small['active'] and abs(small['bias']+.7*4/256)<1e-12
    # Native 512x288 frame, literal 32x18 grid of 8x8 cell taps. The top
    # 16-pixel stationary reference strip fills one grid row (5.56%).
    x=(gx[...,None,None]+(np.arange(8)[None,None,None,:]+.5)/8)*16
    y=(gy[...,None,None]+(np.arange(8)[None,None,:,None]+.5)/8)*16
    pattern=.08*np.exp(.004*x)*(1+.12*np.cos(2*np.pi*y/128))
    foreground=np.mean(pattern,axis=(-2,-1))
    stationary=gy==0
    references=np.where(gx.astype(int)%2==0,.78,.94)
    a=np.where(stationary,references,foreground)
    rows=[]
    for d in (4.,8.,16.,32.):
        b=np.where(stationary,references,foreground*np.exp(-.004*d))
        result=built_f1(a,b);mask=result.pop('mask')
        result.update(flow_full_px=d,expected_false_gain=float(np.exp(-.004*d)),
                      static_fraction=float(stationary.mean()),
                      stationary_kept=float(mask[stationary].mean()),
                      moving_kept=float(mask[~stationary].mean()),
                      normalised_moving_zero_rms=float(np.sqrt(np.mean(
                          (((b-result['bias'])/result['gain']-a)[~stationary])**2))))
        rows.append(result)
    witness=rows[0]
    assert witness['active'] and witness['stationary_kept']==0
    assert abs(witness['gain']-witness['expected_false_gain'])<1e-10
    assert witness['normalised_moving_zero_rms']<1e-10
    qb=np.where(stationary,references,foreground*np.exp(-.004*4))
    quantised=built_f1(a.astype('float16').astype('float32'),qb.astype('float16').astype('float32'))
    qmask=quantised.pop('mask')
    quantised['stationary_kept']=float(qmask[stationary].mean())
    assert quantised['active'] and quantised['stationary_kept']==0 and abs(quantised['gain']-np.exp(-.016))<.001
    return dict(source_sha256=sha,scope='32x18 scalar fit mirror, float64; not a rendered GLSL result',
                ramp_cases=ramp_cases,moving_reference_cases=rows,positive_illumination=recovered,
                quantised_grid_stress=quantised)


def moving_reference_scene(time, displacement=4.):
    """Native 512x288 analytic fixture in normalised working-luma coordinates.

    time is in input-pair periods; a full-rate reference samples time=k/2.
    Top 16 px: stationary reference strip; rest: sheet translating right.
    A declared colour transfer is needed before rendering, not implicit gamma.
    """
    yy,xx=np.indices((288,512),dtype=float);xx+=.5;yy+=.5
    moving=.08*np.exp(.004*(xx-displacement*time))*(1+.12*np.cos(2*np.pi*yy/128))
    reference=np.where((xx.astype(int)//16)%2==0,.78,.94)
    return np.where(yy<16,reference,moving)


def main(out, fade_root=None):
    out.mkdir(parents=True,exist_ok=True)
    controls=[]
    yy,xx=np.mgrid[0:64,0:64].astype(float)
    texture=.4+.13*np.sin(.37*xx+.23*yy)+.09*np.cos(.19*xx-.41*yy)
    # Positive control: actual stationary exposure change is recovered.
    for trim in (0.,.05,.1,.2):
        g,b,_=fit(texture,1.06*texture+.017,trim)
        assert abs(g-1.06)<1e-12 and abs(b-.017)<1e-12
    controls.append('true affine illumination, trims 0/5/10/20 percent')
    rng=np.random.default_rng(20261023)
    random=rng.uniform(.1,.9,(64,64))
    g,b,_=fit(random,np.roll(random,4,axis=1))
    random_error=float(np.sqrt(np.mean((np.roll(random,4,axis=1)-(g*random+b))**2)))
    assert random_error>.1  # ordinary translation is not always an affine light fit
    controls.append('random-texture translation is not an exact photometric fit')

    # F1: exact ambiguity, with the native 1/16 grid's physical coordinates.
    x=(xx+.5)*16; y=(yy+.5)*16
    displacement=8.; slope=.0003
    ramp=.2+slope*x+.0001*y
    shifted_ramp=ramp-slope*displacement
    ramp_rows=[]
    for trim in (0.,.05,.1,.2,.4):
        g,b,keep=fit(ramp,shifted_ramp,trim)
        rms=float(np.sqrt(np.mean(((shifted_ramp-b)/g-ramp)**2)))
        assert abs(g-1)<1e-12 and abs(b+slope*displacement)<1e-12 and rms<1e-12
        ramp_rows.append(dict(trim=trim,gain=g,bias=b,normalised_zero_displacement_rms=rms,
                              fraction_kept=float(keep.mean())))

    k=.002
    moving=.08*np.exp(k*x)*(1+.12*np.cos(2*np.pi*y/128))
    shifted=moving*np.exp(-k*displacement)
    static=np.zeros_like(moving,dtype=bool);static[:4]=True  # 6.25% of coarse samples
    calibration=np.where((xx.astype(int)//2)%2==0,.78,.94)
    a=np.where(static,calibration,moving)
    bimage=np.where(static,calibration,shifted)
    moving_rows=[]
    expected=float(np.exp(-k*displacement))
    for trim in (0.,.05,.1,.2):
        for rounds in (0,1,3,8):
            g,b,keep=fit(a,bimage,trim,rounds)
            norm=(bimage-b)/g
            moving_rows.append(dict(trim=trim,rounds=rounds,gain=g,bias=b,
                stationary_kept=float(keep[static].mean()),moving_kept=float(keep[~static].mean()),
                moving_zero_rms=float(np.sqrt(np.mean((norm[~static]-a[~static])**2))),
                stationary_normalisation_rms=float(np.sqrt(np.mean((norm[static]-a[static])**2)))))
    witness=next(r for r in moving_rows if r['trim']==.1 and r['rounds']==3)
    assert abs(witness['gain']-expected)<1e-10 and abs(witness['bias'])<1e-10
    assert witness['stationary_kept']==0 and witness['moving_zero_rms']<1e-12
    family=[]
    for shift in (4.,8.,16.,32.):
        target=np.where(static,calibration,moving*np.exp(-k*shift))
        g,b,keep=fit(a,target,.1,3)
        assert abs(g-np.exp(-k*shift))<1e-10 and not keep[static].any()
        family.append(dict(flow_full_px=shift,fitted_gain=g,stationary_kept=float(keep[static].mean())))
    # A/B/midpoint and exact piecewise motion for a future full-graph probe.
    # Fixed aperture, moving exponential-pattern sheet, stationary reference
    # strip. No clipping. This is sampled analytic data, not a GLSL result.
    midpoint=np.where(static,calibration,moving*np.exp(-k*displacement/2))
    np.savez_compressed(out/'moving-majority-coarse.npz',a=a,b=bimage,midpoint=midpoint,
                        stationary_mask=static,flow_x=np.where(static,0,displacement),
                        full_pixel_pitch=16)
    np.savez_compressed(out/'built-f1-native.npz',a=moving_reference_scene(0),midpoint=moving_reference_scene(.5),
                        b=moving_reference_scene(1),stationary_rows=16,full_pixel_pitch=1,flow_full_px=4)

    # F2: final field carries a valid propagated nonzero seed. Local ramp
    # support cannot distinguish that seed from zero after mean subtraction.
    py,px=np.mgrid[-2:3,-2:3].astype(float);px*=2;py*=2
    d=4.;patch=.5+px/128+py/256
    zero_patch=.5+(px-d)/128+py/256
    true_patch=.5+(px+d-d)/128+py/256
    zero_cost=zm_cost(patch,zero_patch);true_cost=zm_cost(patch,true_patch)
    assert zero_cost<1e-12 and true_cost<1e-12
    raw_zero=float(np.mean(abs(patch-zero_patch)))
    assert raw_zero>.02
    margins=(0.,1e-12,1e-6,1e-5,1e-4,1e-3)
    # Binary-rational ramp: the tie is exact in both algebra and float64.
    tie_decisions={str(m):bool(zero_cost<=true_cost+m) for m in margins}
    assert tie_decisions['0.0'] and zero_cost==true_cost==0
    sine=[]
    for contrast in (.02,.10,.20):
        for period in (32.,64.,128.,256.,512.):
            for d in (2.,4.,6.):
                p=.5+contrast*np.sin(2*np.pi*px/period)
                z=.5+contrast*np.sin(2*np.pi*(px-d)/period)
                t=.5+contrast*np.sin(2*np.pi*(px+d-d)/period)
                cz,ct=zm_cost(p,z),zm_cost(p,t)
                sine.append(dict(contrast=contrast,period_full_px=period,flow_full_px=d,
                    raw_zero_mad=float(np.mean(abs(p-z))),zero_mean_zero_mad=cz,true_mad=ct,
                    zero_mean_zero_dn=255*cz,
                    cancelled_by_margins=[m for m in margins[2:] if cz<=ct+m]))
    assert any(r['contrast']==.1 and r['flow_full_px']==4 and 1e-4 in r['cancelled_by_margins'] for r in sine)
    # Positive F2 distinction: with a richer translated patch, zero is worse.
    rich=.5+.15*np.sin(.6*px+.4*py)+.1*np.cos(.9*px-.3*py)
    richzero=.5+.15*np.sin(.6*(px-4)+.4*py)+.1*np.cos(.9*(px-4)-.3*py)
    rich_cost=zm_cost(rich,richzero)
    assert rich_cost>.05
    controls.append('F2 genuinely informative moving texture prefers nonzero')

    ea=energy(texture);eb=energy(1.06*texture+.017)
    energy_error=float(np.max(abs(eb/1.06-ea)))
    assert energy_error<1e-12
    information=dict(ramp=nuisance_information(ramp,np.full_like(ramp,slope),np.full_like(ramp,.0001)),
                     exponential=nuisance_information(moving,k*moving,np.zeros_like(moving)))
    assert max(v['surviving_fraction'] for v in information.values())<1e-20

    fades={}
    for gain in (1.03,1.06,1.12):
        end=.55*gain**11.5
        fades[str(gain)]=dict(last_source_multiplier=end,source_peak_limit=1/end)
    actual={}
    if fade_root:
        for name,w,h in [('tv',1440,1080),('cartoon',1280,720)]:
            p=fade_root/f'{name}-fade/raw-full.rgb48'
            data=np.memmap(p,dtype='<u2',mode='r')
            if data.size%(h*w*3):raise ValueError('short RGB48 source '+name)
            data=data.reshape(-1,h,w,3)
            actual[name]=dict(frames=len(data),first_peak=float(data[0].max()/65535),
                raw_bytes=p.stat().st_size,first_frame_sha256=hashlib.sha256(data[0].tobytes()).hexdigest(),
                last_frame_sha256=hashlib.sha256(data[-1].tobytes()).hexdigest(),
                last_peak=float(data[-1].max()/65535),last_clipped_channel_fraction=float(np.mean(data[-1]==65535)),
                frames_with_clipped_channels=sum(bool(np.any(f==65535)) for f in data),
                projected_last_clipped_channel_fraction={str(g):float(np.mean(
                    data[0].astype(float)*g**11.5>=65535)) for g in (1.03,1.06,1.12)})
    result=dict(scope='CPU estimator/proposed-rule attacks; no rendered GLSL regression claimed',
        controls=controls,pair_displacement_units='full-resolution pixels per input pair',
        ramp=ramp_rows,moving_majority=dict(expected_motion_gain=expected,static_fraction=float(static.mean()),
            rows=moving_rows,witness=witness,displacement_family=family),f2_ramp=dict(flow_full_px=4.,raw_zero_mad=raw_zero,
            zero_mean_zero_mad=zero_cost,zero_mean_true_mad=true_cost,tie_decisions=tie_decisions),
        f2_sinusoids=sine,f2_informative_zero_cost=rich_cost,
        energy=dict(degree=1,normalised_max_error=energy_error,
                    unnormalised_mean_difference=float(np.mean(abs(eb-ea)))),
        projected_information=information,fade_headroom=fades,existing_fade_clipping=actual,
        built_f1=implementation_attacks())
    (out/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('CPU plan attacks and positive controls pass')
    print('F1 moving-majority witness:',witness)
    print('F2 ramp:',result['f2_ramp'])
    for row in sine:
        if row['contrast']==.1 and row['flow_full_px']==4:
            print('F2 sine:',row)
    print('existing fade clipping:',actual)
    print('built F1 estimator, small ramp:',next(r for r in result['built_f1']['ramp_cases']
                                               if r['width_full_px']==256 and r['flow_full_px']==4))
    print('built F1 estimator, moving foreground:',result['built_f1']['moving_reference_cases'][0])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path);p.add_argument('--fade-root',type=Path)
    a=p.parse_args();main(a.out.resolve(),a.fade_root.resolve() if a.fade_root else None)
