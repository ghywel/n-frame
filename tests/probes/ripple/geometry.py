#!/usr/bin/env python3
"""CPU geometry controls with exact fields and declared flow errors; no GPU is involved.

geometry.py [OUT.json] [--video PROOF.mp4 --ffmpeg SOFTWARE_FFMPEG]
Tests coordinate error, a valid forward deformation whose approximate inverse
reverses/folds, fixed-point nonconvergence, and a singular-Newton counterexample.
See GEOMETRY.md before interpreting real-footage Jacobian measurements.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess


def mean(values):
    return sum(values)/len(values)


def bisect(fn, lo, hi):
    flo, fhi = fn(lo), fn(hi)
    assert flo*fhi <= 0, (flo, fhi)
    for _ in range(100):
        mid = (lo+hi)/2
        fm = fn(mid)
        if flo*fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo+hi)/2


def bounded_inverse2(field, p, t):
    """Scalar replay of the two proposal/residual choices, not a new solver."""
    best = field(p)
    q = p-t*best
    nxt = field(q)
    error = abs(q+t*nxt-p)
    errors = [error]
    for _ in range(2):
        candidate = nxt
        q = p-t*candidate
        nxt = field(q)
        residual = abs(q+t*nxt-p)
        errors.append(residual)
        if residual+1e-4 < error:
            best, error = candidate, residual
    return best, errors


def texture(q):
    return .5+.2*math.sin(.23*q)+.12*math.cos(.49*q)+.05*math.sin(.83*q)


def affine_control():
    # Embedded in 2D with unchanged y: determinants equal these x derivatives.
    k, b, p, t = 3., 2., 10., .5
    f = lambda q: k*q+b
    exact = (p-t*b)/(1+t*k)
    approx = p-t*f(p)
    residual = approx+t*f(approx)-p
    expected_residual = -t*t*k*f(p)
    newton = approx-residual/(1+t*k)
    selected, residuals = bounded_inverse2(f, p, t)
    assert min(1+s*k for s in (0., .25, .5, .75, 1.)) > 0
    assert 1-t*k < 0 < 1/(1+t*k)
    assert abs(exact-3.6) < 1e-12 and abs(approx+6.) < 1e-12
    assert abs(residual-expected_residual) < 1e-12
    assert abs(newton-exact) < 1e-12
    assert selected == f(p), 'Residual-guarded proposals should retain original here'
    assert residuals == [24., 36., 54.]

    # Endpoint pictures are two independently evaluable views of one material.
    # I_B(x)=I_A((x-b)/(1+k)); the exact midpoint truth is I_A(q_exact).
    pixels = [i/4 for i in range(-80,81)]
    errors = []
    exact_errors = []
    endpoint_errors = []
    for x in pixels:
        q = (x-t*b)/(1+t*k)
        a0, b0 = x-t*f(x), x+(1-t)*f(x)
        prediction = (1-t)*texture(a0)+t*texture((b0-b)/(1+k))
        truth = texture(q)
        exact_b = q+f(q)
        corrected = (1-t)*texture(q)+t*texture((exact_b-b)/(1+k))
        errors.append((prediction-truth)**2)
        exact_errors.append((corrected-truth)**2)
        for phase in (0.,1.):
            a1, b1 = x-phase*f(x), x+(1-phase)*f(x)
            endpoint = (1-phase)*texture(a1)+phase*texture((b1-b)/(1+k))
            endpoint_truth = texture((x-phase*b)/(1+phase*k))
            endpoint_errors.append(abs(endpoint-endpoint_truth))
    assert mean(errors) > .001
    assert max(exact_errors) < 1e-28
    assert max(endpoint_errors) < 1e-14
    return dict(k=k, b=b, phase=t, output_position=p,
                valid_forward_derivative_range=[1.,1+k],
                exact_source=exact, approximate_source=approx,
                approximate_a_derivative=1-t*k, exact_a_derivative=1/(1+t*k),
                roundtrip_residual=residual, newton_source=newton,
                fixed_point_error_factor=-t*k, proposal_residuals=residuals,
                residual_guard_retains_original=True,
                approximate_picture_mse=mean(errors), exact_picture_mse=mean(exact_errors),
                retained_endpoint_abs_error_max=max(endpoint_errors))


def smooth_fold_control():
    # F' ranges from 0 to 3. The true forward map is strictly increasing for
    # every source-to-output phase, yet p-.5 F(p) has a turning point.
    scale, t = 8., .5
    softplus = lambda z: max(z,0.)+math.log1p(math.exp(-abs(z)))
    f = lambda q: 3*scale*softplus(q/scale)
    df = lambda q: 3/(1+math.exp(-q/scale))
    approximate = lambda p: p-t*f(p)
    turning = scale*math.log(2)
    target = approximate(turning)-2.
    left = bisect(lambda p: approximate(p)-target, -80., turning)
    right = bisect(lambda p: approximate(p)-target, turning, 80.)
    exact_left = bisect(lambda q: q+t*f(q)-left, -100.,100.)
    exact_right = bisect(lambda q: q+t*f(q)-right, -100.,100.)
    assert right-left > 1
    assert abs(approximate(left)-approximate(right)) < 1e-12
    assert 1-t*df(left) > 0 > 1-t*df(right)
    assert exact_right > exact_left
    assert all(1+s*df(q) > 0 for s in (0.,.25,.5,.75,1.) for q in range(-80,81))
    return dict(scope='Exact smooth field; actual noninjective approximate A sampling, not merely affine reversal',
                phase=t, derivative_turning_position=turning,
                output_positions=[left,right], shared_approximate_source=target,
                exact_source_positions=[exact_left,exact_right],
                approximate_derivatives=[1-t*df(left),1-t*df(right)],
                forward_derivative_strictly_positive_for_all_phases=True)


def newton_risk_control():
    # An unreliable estimated field, NOT the valid forward motion above.
    # A tiny inverse residual need not make its source coordinate acceptable.
    k, b, p, t = -2.+1e-6, 1., 1., .5
    jacobian = 1+t*k
    residual_at_zero = t*b-p
    step = -residual_at_zero/jacobian
    assert 0 < jacobian < 1e-6 and step > 1e5
    assert abs(step+t*(k*step+b)-p) < 1e-9
    assert not -100 <= step <= 100
    singular_jacobian = 1+.5*(-2.)
    assert singular_jacobian == 0
    return dict(scope='Unreliable estimated field counterexample; not a valid orientation-preserving motion over the whole interval',
                phase=t, estimated_gradient=k, inverse_jacobian_denominator=jacobian,
                residual_at_zero=residual_at_zero, newton_step=step,
                residual_after_step=step+t*(k*step+b)-p,
                outside_declared_source_domain=[-100,100], singular_control_denominator=singular_jacobian)


def shared_wrong_flow_control():
    # The source is one continuously translated, unbounded material plane.
    # A(x)=I(x), B(x)=I(x-d); no occlusion, grid ambiguity or sampling noise.
    d, error, t, p = 8., 6., .5, 4.
    s = p-t*d
    qa = p-t*(d+error)
    qb_material = p+(1-t)*(d+error)-d
    assert qa == s-t*error and qb_material == s+(1-t)*error
    assert qb_material-qa == error
    assert (1-t)*qa+t*qb_material == s
    draw=lambda material,x,phase,delta: ((1-phase)*material(x-phase*(d+delta))
                                        +phase*material(x+(1-phase)*(d+delta)-d))
    line=lambda x:.2+.6*math.exp(-.5*x*x)
    ghost_positions=[t*d-(1-t)*error,t*d+t*error]
    ghost_values=[draw(line,x,t,error) for x in ghost_positions]
    center=draw(line,t*d,t,error)
    assert min(ghost_values)>.499 and center<.21 and line(0)==.8
    ramp=lambda x:.5+.001*x
    for phase in (0.,.2,.5,.8,1.):
        for x in (-20.,4.,30.):
            assert abs(draw(ramp,x,phase,error)-ramp(x-phase*d))<1e-14

    # Spatially varying, correctly output-indexed error on the same rigid plane.
    # Both sampling maps remain increasing: this mechanism does not need a fold.
    period, amplitude = 16., .3
    k=2*math.pi/period
    material=lambda x:.5+amplitude*math.cos(k*x)
    positions=[i/4 for i in range(1024)]
    midpoint_errors=[];gains=[];derivatives=[]
    for u in positions:
        delta=3+3*math.sin(2*math.pi*u/128)
        delta_derivative=3*2*math.pi/128*math.cos(2*math.pi*u/128)
        x=u+t*d
        prediction=draw(material,x,t,delta)
        gain=math.cos(math.pi*delta/period)
        expected=.5+amplitude*math.cos(k*u)*gain
        assert abs(prediction-expected)<1e-14
        midpoint_errors.append(prediction-material(u));gains.append(gain)
        derivatives.extend([1-t*delta_derivative,1+(1-t)*delta_derivative])
    assert min(derivatives)>0
    midpoint_rms=math.sqrt(mean([e*e for e in midpoint_errors]))
    midpoint_mae=mean([abs(e) for e in midpoint_errors])
    assert midpoint_rms>.01
    # At fixed material coordinates, every inserted error map is the same,
    # but retained frames are exact. Synthesized-only change scores read zero.
    synthesized_errors=[midpoint_errors[:],midpoint_errors[:],midpoint_errors[:]]
    scalar_change=abs(mean([abs(e) for e in synthesized_errors[1]])
                      -mean([abs(e) for e in synthesized_errors[0]]))
    pixel_change=math.sqrt(mean([(b-a)**2 for a,b in zip(*synthesized_errors[:2])]))
    assert scalar_change==pixel_change==0
    all_output_second_rms=math.sqrt(mean([(2*e)**2 for e in midpoint_errors]))
    assert abs(all_output_second_rms-2*midpoint_rms)<1e-14
    return dict(scope='Known flow-error counterexample on exact rigid translation; not film attribution',
                true_displacement=d,used_displacement=d+error,phase=t,
                true_material_coordinate=s,sampled_material_coordinates=[qa,qb_material],
                material_sample_separation=error,weighted_material_centroid=s,
                gaussian_true_peak=line(0),gaussian_ghost_positions=ghost_positions,
                gaussian_ghost_values=ghost_values,gaussian_value_at_true_center=center,
                intensity_ramp_cancellation=True,carrier_period=period,
                constant_error_4_midpoint_contrast=math.cos(math.pi*4/period),
                varying_error_range=[0.,6.],midpoint_contrast_range=[min(gains),max(gains)],
                minimum_sampling_derivative=min(derivatives),midpoint_error_rms=midpoint_rms,
                midpoint_error_mae=midpoint_mae,retained_material_error=0.,
                synthesized_only_scalar_mae_change=scalar_change,
                synthesized_only_pixelwise_error_change=pixel_change,
                all_output_material_error_first_difference_rms=midpoint_rms,
                all_output_material_error_second_difference_rms=all_output_second_rms,
                exact_source_rate=24,exact_output_rate=48,contrast_cycle_hz=24)


def independent_grain_control():
    # Exact finite population with zero means, unit variances and zero covariance.
    # No motion error is introduced; these are already corresponding samples.
    a=[-1.,-1.,1.,1.];b=[-1.,1.,-1.,1.]
    assert mean(a)==mean(b)==0
    assert mean([v*v for v in a])==mean([v*v for v in b])==1
    assert mean([x*y for x,y in zip(a,b)])==0
    rows=[]
    for t in (0.,.25,.5,.75,1.):
        mixed=[(1-t)*x+t*y for x,y in zip(a,b)]
        variance=mean([x*x for x in mixed])
        expected=(1-t)**2+t*t
        assert variance==expected
        rows.append(dict(phase=t,variance_ratio=variance,rms_ratio=math.sqrt(variance)))
    assert rows[2]['rms_ratio']==math.sqrt(.5)
    return dict(scope='Zero motion-error grain-only contrast control; no film noise estimate',
                source_variance=1.,cross_covariance=0.,phase_results=rows,
                midpoint_rms_ratio=math.sqrt(.5),
                equal_variance_correlated_formula='(1-t)^2+t^2+2*t*(1-t)*rho',
                lowpass_note='Filtering lowers noise energy but does not remove this variance ratio for two equally filtered independent fields')


def proof_video(path,ffmpeg):
    """Software-encoded preview; floating controls above, not this 8-bit video, are the numerical evidence."""
    import numpy as np
    path.parent.mkdir(parents=True,exist_ok=True)
    x,y=np.meshgrid(np.arange(320,dtype=float)+.5,np.arange(360,dtype=float)+.5)
    process=subprocess.Popen([ffmpeg,'-nostdin','-y','-v','error','-f','rawvideo','-pixel_format','gray',
        '-video_size','640x360','-framerate','48','-i','-','-an','-c:v','libx264','-preset','medium',
        '-crf','12','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    material=lambda u:.5+.22*np.cos(2*np.pi*u/16)+.05*np.cos(2*np.pi*y/160)
    try:
        for frame in range(144):
            u=x-3*(frame/2)
            truth=material(u)
            if frame%2:
                delta=3+3*np.sin(2*np.pi*u/128)*np.sin(2*np.pi*y/128)
                wrong=.5*(material(u-.5*delta)+material(u+.5*delta))
            else:
                wrong=truth.copy()
            display=np.concatenate([truth,wrong],axis=1)
            display[:12]=.08;display[-12:]=.08;display[:,319:321]=.08
            process.stdin.write(np.rint(np.clip(display,0,1)*255).astype('uint8').tobytes())
        process.stdin.close()
        stderr=process.stderr.read().decode(errors='replace');code=process.wait()
        if code:raise RuntimeError(f'software proof encoding failed: {stderr}')
    except BaseException:
        process.kill();process.wait();raise
    return dict(output_name=path.name,scope='CPU-generated 8-bit preview, software libx264; no GPU or film footage',
                left='Exact rigid translation',right='Same translation with a declared shared-vector error at inserted midpoints',
                duration_seconds=3,source_fps=24,output_fps=48,frames=144,carrier_period_px=16,
                true_displacement_px_per_source_frame=3,error_range_px=[0,6],
                minimum_sampling_map_determinant=1-.5*3*2*math.pi/128)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path,nargs='?');parser.add_argument('--video',type=Path)
    parser.add_argument('--ffmpeg',default='ffmpeg');args=parser.parse_args()
    report=dict(scope='CPU exact-field and known-error controls only; no real-footage causal attribution or GPU result',
                affine=affine_control(), smooth_fold=smooth_fold_control(), newton_risk=newton_risk_control(),
                shared_wrong_flow=shared_wrong_flow_control(),independent_grain=independent_grain_control())
    if args.video:report['proof_video']=proof_video(args.video,args.ffmpeg)
    output=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(output)
    print(output,end='')


if __name__=='__main__':main()
