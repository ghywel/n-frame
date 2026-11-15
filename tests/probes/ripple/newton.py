#!/usr/bin/env python3
"""Bounded Newton warp diagnostic on the registered vote-off High; see NEWTON.md.

newton.py INPUT.glsl OUTPUT.glsl
newton.py --control                 CPU controls only, JSON on stdout
No GPU work and no production-source mutation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

EXPECTED_SHA256 = 'b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece'
ANCHOR = '    vec2 flow_ab = FLOW_H_AB_tex(HOOKED_pos).xy * 2.0 * HOOKED_pt;'
HELPER = '''
// RIPPLE Newton diagnostic: source-A-indexed displacement, in full pixels.
vec2 rp_newton_field(vec2 q) {
    return FLOW_H_AB_tex(q * HOOKED_pt).xy * 2.0;
}
'''
STEP = '''
    // RIPPLE bounded Newton: diagnostic geometry only, not a visibility decision.
    if (mix_t > 0.001 && mix_t < 0.999) {
        vec2 rp_p = HOOKED_pos / HOOKED_pt;
        vec2 rp_q = rp_p - mix_t * (flow_ab / HOOKED_pt);
        vec2 rp_lo = vec2(0.5), rp_hi = HOOKED_size - vec2(0.5);
        bool rp_inside = all(greaterThanEqual(rp_q, rp_lo)) && all(lessThanEqual(rp_q, rp_hi));
        bool rp_changed = false;
        if (rp_inside) {
            vec2 rp_r = rp_q + mix_t * rp_newton_field(rp_q) - rp_p;
            float rp_best = length(rp_r);
            for (int rp_iter = 0; rp_iter < 4; rp_iter++) {
                if (rp_best <= 0.0001) break;
                // Central differences need their complete one-pixel stencil inside the source.
                if (any(lessThan(rp_q, rp_lo + vec2(1.0)))
                    || any(greaterThan(rp_q, rp_hi - vec2(1.0)))) break;
                vec2 rp_dx = 0.5 * (rp_newton_field(rp_q + vec2(1.0, 0.0))
                                  - rp_newton_field(rp_q - vec2(1.0, 0.0)));
                vec2 rp_dy = 0.5 * (rp_newton_field(rp_q + vec2(0.0, 1.0))
                                  - rp_newton_field(rp_q - vec2(0.0, 1.0)));
                vec2 rp_jx = vec2(1.0, 0.0) + mix_t * rp_dx;
                vec2 rp_jy = vec2(0.0, 1.0) + mix_t * rp_dy;
                float rp_det = rp_jx.x * rp_jy.y - rp_jy.x * rp_jx.y;
                float rp_tau = dot(rp_jx, rp_jx) + dot(rp_jy, rp_jy);
                float rp_smax = sqrt(0.5 * (rp_tau + sqrt(max(rp_tau * rp_tau - 4.0 * rp_det * rp_det, 0.0))));
                float rp_smin = abs(rp_det) / max(rp_smax, 1.0e-6);
                if (!(rp_smin >= 0.2)) break;  // also refuses a NaN singular-value estimate
                vec2 rp_step = vec2(rp_jy.y * rp_r.x - rp_jy.x * rp_r.y,
                                   -rp_jx.y * rp_r.x + rp_jx.x * rp_r.y) / rp_det;
                float rp_length = length(rp_step);
                if (rp_length > 8.0) rp_step *= 8.0 / rp_length;
                vec2 rp_try = rp_q - rp_step;
                if (any(lessThan(rp_try, rp_lo)) || any(greaterThan(rp_try, rp_hi))) break;
                vec2 rp_try_r = rp_try + mix_t * rp_newton_field(rp_try) - rp_p;
                float rp_error = length(rp_try_r);
                if (!(rp_error + 0.0001 < rp_best)) break;
                rp_q = rp_try; rp_r = rp_try_r; rp_best = rp_error; rp_changed = true;
            }
        }
        // This vector draws A at the accepted q. Using F(q) would move that sample again
        // whenever the bounded solve leaves a nonzero residual. Both endpoints share it.
        if (rp_changed) flow_ab = ((rp_p - rp_q) / mix_t) * HOOKED_pt;
    }
'''


def add(text):
    if hashlib.sha256(text.encode()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('requires the registered preceding High, WARP_VOTE=0')
    marker='//!DESC [high] motion-compensated warp\n'
    if text.count(marker) != 1 or text.count(ANCHOR) != 1:
        raise ValueError('unexpected final-warp source shape')
    i=text.index(marker);start=text.rfind('//!HOOK FRAME_MIX',0,i)
    end=text.find('//!HOOK FRAME_MIX',i);end=len(text) if end<0 else end
    block=text[start:end]
    if block.count('vec4 hook() {') != 1 or block.count(ANCHOR) != 1:
        raise ValueError('unexpected final-warp body')
    block=block.replace('vec4 hook() {',HELPER+'\nvec4 hook() {',1)
    block=block.replace(ANCHOR,ANCHOR+STEP,1)
    result=text[:start]+block+text[end:]
    assert result.replace(HELPER+'\n','',1).replace(STEP,'',1) == text
    assert result.count('//!HOOK FRAME_MIX') == text.count('//!HOOK FRAME_MIX')
    return result


def norm(v):
    return math.hypot(*v)


def solve(field,p,t,size=(512.,512.)):
    """Double-precision CPU mirror of the GLSL choices; no image/visibility claim."""
    original=tuple(field(p));q=tuple(p[i]-t*original[i] for i in range(2));initial=q
    history=[];reason='iteration_limit';changed=False
    inside=lambda v: all(.5<=v[i]<=size[i]-.5 for i in range(2))
    if not .001<t<.999:
        return original,dict(changed=False,reason='endpoint',history=[])
    if not inside(q):
        return original,dict(changed=False,reason='initial_outside',history=[])
    residual=lambda v: tuple(v[i]+t*field(v)[i]-p[i] for i in range(2))
    r=residual(q);best=norm(r);initial_residual=best
    for _ in range(4):
        if best<=1e-4:reason='residual_small';break
        if not all(1.5<=q[i]<=size[i]-1.5 for i in range(2)):
            reason='stencil_outside';break
        xp,xm=field((q[0]+1,q[1])),field((q[0]-1,q[1]))
        yp,ym=field((q[0],q[1]+1)),field((q[0],q[1]-1))
        jx=(1+t*.5*(xp[0]-xm[0]),t*.5*(xp[1]-xm[1]))
        jy=(t*.5*(yp[0]-ym[0]),1+t*.5*(yp[1]-ym[1]))
        det=jx[0]*jy[1]-jy[0]*jx[1]
        tau=sum(v*v for v in jx+jy)
        smax=math.sqrt(.5*(tau+math.sqrt(max(tau*tau-4*det*det,0))))
        smin=abs(det)/max(smax,1e-6)
        if not smin>=.2:reason='singular_value';break
        step=((jy[1]*r[0]-jy[0]*r[1])/det,(-jx[1]*r[0]+jx[0]*r[1])/det)
        length=norm(step)
        if length>8:step=tuple(v*8/length for v in step)
        candidate=tuple(q[i]-step[i] for i in range(2))
        if not inside(candidate):reason='proposal_outside';break
        candidate_r=residual(candidate);error=norm(candidate_r)
        if not error+1e-4<best:reason='no_strict_improvement';break
        q,r,best=candidate,candidate_r,error;changed=True
        history.append(dict(q=q,step_length=norm(step),residual=best,minimum_singular_value=smin))
    flow=tuple((p[i]-q[i])/t for i in range(2)) if changed else original
    return flow,dict(changed=changed,reason=reason,initial_q=initial,final_q=q,
                     initial_residual=initial_residual,final_residual=best,history=history)


def control():
    constant=lambda q:(8.,-2.)
    for t in (0.,.001,.2,.5,.8,.999,1.):
        flow,record=solve(constant,(256.,256.),t)
        assert flow==constant(None) and not record['changed']
    affine=lambda q:(3*(q[0]-256)+2,0.)
    flow,expansion=solve(affine,(266.,256.),.5)
    assert expansion['changed'] and len(expansion['history'])==2
    assert norm((flow[0]-12.8,flow[1]))<1e-10
    assert abs(expansion['final_q'][0]-259.6)<1e-10
    assert expansion['final_residual']<1e-10
    _,bounded=solve(affine,(356.,256.),.5)
    assert len(bounded['history'])==4 and bounded['reason']=='iteration_limit'
    assert all(h['step_length']<=8+1e-12 for h in bounded['history'])
    assert norm(tuple(bounded['final_q'][i]-bounded['initial_q'][i] for i in range(2)))<=32+1e-12
    assert bounded['final_residual']>100, 'Bounded solve must not be reported as converged'
    unstable=lambda q:((-2+1e-6)*(q[0]-256)+1,0.)
    original=unstable((266.,256.));got,near_singular=solve(unstable,(266.,256.),.5)
    assert got==original and near_singular['reason']=='singular_value' and not near_singular['changed']
    # An orientation-changing Jacobian with adequate singular values is not refused by
    # this numerical guard. The diagnostic intentionally makes no visibility/topology claim.
    _,outside=solve(lambda q:(1000.,0.),(5.,256.),.5)
    assert outside['reason']=='initial_outside' and not outside['changed']
    return dict(scope='CPU mirror only; not a GPU or visibility validation',
                constant_and_endpoint_identity=True,affine_expansion=expansion,
                bounded_nonconvergence=bounded,near_singular_rejection=near_singular,
                outside_source_rejection=outside)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,nargs='?');parser.add_argument('output',type=Path,nargs='?')
    parser.add_argument('--control',action='store_true');args=parser.parse_args()
    if args.control:
        print(json.dumps(control(),indent=2,allow_nan=False));return
    if not args.source or not args.output:parser.error('INPUT and OUTPUT are required unless --control is used')
    args.output.write_text(add(args.source.read_text()))


if __name__=='__main__':main()
