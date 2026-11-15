#!/usr/bin/env python3
"""Eight-pixel overlapping rigid-picture diagnostic on pinned vote-off High.

obmc.py INPUT.glsl OUTPUT.glsl
obmc.py --control
Estimator and support are unchanged; four pictures, never four vectors, are blended.
See OBMC.md before interpreting the result. No GPU work occurs here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

EXPECTED_SHA256='b7b92988b2f2c581a8aaed0c03a25440c3ae45ea8aa68a0d920c9526e943aece'
ANCHOR='    vec4 warped = mix(warped_a, warped_b, mix_t);\n'
HELPER='''
// RIPPLE OBMC8 diagnostic: each candidate draws a locally rigid paired picture.
vec4 rp_obmc_pair(vec2 flow) {
    return mix(warp_sample_a(HOOKED_pos - flow * mix_t),
               warp_sample_b(NEXT_pos + flow * (1.0 - mix_t)), mix_t);
}
'''
OVERLAP='''
    // RIPPLE OBMC8: sample the SAME A-indexed field on a fixed eight-full-pixel grid.
    // Blend pictures from its four nodes; do not interpolate their displacement vectors.
    if (mix_t > 0.001 && mix_t < 0.999) {
        vec2 rp_pos = HOOKED_pos / HOOKED_pt;
        vec2 rp_grid = (rp_pos - vec2(4.0)) / 8.0;
        vec2 rp_cell = floor(rp_grid), rp_w = fract(rp_grid);
        vec2 rp_low = vec2(4.0);
        vec2 rp_high = max(rp_low, vec2(4.0) + 8.0 * floor((HOOKED_size - vec2(4.0)) / 8.0));
        vec2 rp_n00 = clamp(vec2(4.0) + 8.0 * rp_cell, rp_low, rp_high);
        vec2 rp_n10 = clamp(vec2(4.0) + 8.0 * (rp_cell + vec2(1.0, 0.0)), rp_low, rp_high);
        vec2 rp_n01 = clamp(vec2(4.0) + 8.0 * (rp_cell + vec2(0.0, 1.0)), rp_low, rp_high);
        vec2 rp_n11 = clamp(vec2(4.0) + 8.0 * (rp_cell + vec2(1.0, 1.0)), rp_low, rp_high);
        vec2 rp_f00 = FLOW_H_AB_tex(rp_n00 * HOOKED_pt).xy * 2.0 * HOOKED_pt;
        vec2 rp_f10 = FLOW_H_AB_tex(rp_n10 * HOOKED_pt).xy * 2.0 * HOOKED_pt;
        vec2 rp_f01 = FLOW_H_AB_tex(rp_n01 * HOOKED_pt).xy * 2.0 * HOOKED_pt;
        vec2 rp_f11 = FLOW_H_AB_tex(rp_n11 * HOOKED_pt).xy * 2.0 * HOOKED_pt;
        // Preserve the original arithmetic in the constant-flow degeneracy.
        bool rp_same = all(equal(rp_f00, flow_ab)) && all(equal(rp_f10, flow_ab))
                    && all(equal(rp_f01, flow_ab)) && all(equal(rp_f11, flow_ab));
        if (!rp_same) {
            vec4 rp_c00 = rp_obmc_pair(rp_f00), rp_c10 = rp_obmc_pair(rp_f10);
            vec4 rp_c01 = rp_obmc_pair(rp_f01), rp_c11 = rp_obmc_pair(rp_f11);
            warped = mix(mix(rp_c00, rp_c10, rp_w.x), mix(rp_c01, rp_c11, rp_w.x), rp_w.y);
        }
    }
'''


def add(text):
    if hashlib.sha256(text.encode()).hexdigest()!=EXPECTED_SHA256:
        raise ValueError('requires the registered preceding High, WARP_VOTE=0')
    marker='//!DESC [high] motion-compensated warp\n'
    if text.count(marker)!=1 or text.count(ANCHOR)!=1:
        raise ValueError('unexpected final warp anchor')
    i=text.index(marker);start=text.rfind('//!HOOK FRAME_MIX',0,i)
    end=text.find('//!HOOK FRAME_MIX',i);end=len(text) if end<0 else end
    block=text[start:end]
    if block.count('vec4 hook() {')!=1 or block.count(ANCHOR)!=1:
        raise ValueError('unexpected final warp body')
    block=block.replace('vec4 hook() {',HELPER+'\nvec4 hook() {',1)
    block=block.replace(ANCHOR,ANCHOR+OVERLAP,1)
    out=text[:start]+block+text[end:]
    assert out.replace(HELPER+'\n','',1).replace(OVERLAP,'',1)==text
    assert out.count('//!HOOK FRAME_MIX')==text.count('//!HOOK FRAME_MIX')
    return out


def grid(p,size):
    coordinate=[(v-4)/8 for v in p]
    cell=[math.floor(v) for v in coordinate]
    fraction=[coordinate[i]-cell[i] for i in range(2)]
    high=[max(4,4+8*math.floor((v-4)/8)) for v in size]
    nodes=[tuple(min(high[i],max(4,4+8*(cell[i]+offset[i]))) for i in range(2))
           for offset in ((0,0),(1,0),(0,1),(1,1))]
    x,y=fraction
    weights=[(1-x)*(1-y),x*(1-y),(1-x)*y,x*y]
    return nodes,weights


def pair(a,b,p,t,flow):
    qa=tuple(p[i]-t*flow[i] for i in range(2))
    qb=tuple(p[i]+(1-t)*flow[i] for i in range(2))
    return (1-t)*a(qa)+t*b(qb)


def picture_blend(a,b,field,p,t,size=(64,48)):
    baseline_flow=field(p);baseline=pair(a,b,p,t,baseline_flow)
    if not .001<t<.999:return baseline
    nodes,weights=grid(p,size);flows=[field(node) for node in nodes]
    if all(flow==baseline_flow for flow in flows):return baseline
    return sum(weight*pair(a,b,p,t,flow) for weight,flow in zip(weights,flows))


def control():
    a=lambda p:.5+.15*math.sin(.4*p[0])+.1*math.cos(.3*p[1])
    b=lambda p:.5+.15*math.sin(.4*(p[0]-4))+.1*math.cos(.3*(p[1]+2))
    field=lambda p:(4.,-2.)
    points=[(.5,.5),(4.,4.),(7.75,8.25),(13.2,17.9),(63.5,47.5)]
    constant_checks=0
    for p in points:
        nodes,weights=grid(p,(64,48))
        assert abs(sum(weights)-1)<1e-15 and min(weights)>=0
        assert all(4<=n[0]<=60 and 4<=n[1]<=44 for n in nodes)
        for t in (0.,.001,.25,.5,.75,.999,1.):
            assert picture_blend(a,b,field,p,t)==pair(a,b,p,t,field(p))
            constant_checks+=1
    # The vector average is zero and draws the correct static Gaussian peak.
    # The four displaced pictures instead average off-peak values: averaging
    # nonlinear pictures and averaging vectors are different operations.
    gaussian=lambda p:.2+.6*math.exp(-.5*(p[0]-8)**2)
    varying=lambda p:(p[0]-8,0.)
    p=(8.,8.);t=.5
    nodes,weights=grid(p,(64,48))
    averaged=tuple(sum(w*varying(n)[i] for n,w in zip(nodes,weights)) for i in range(2))
    vector_picture=pair(gaussian,gaussian,p,t,averaged)
    pictures=picture_blend(gaussian,gaussian,varying,p,t)
    assert averaged==(0.,0.) and vector_picture==.8
    assert abs(pictures-(.2+.6*math.exp(-2)))<1e-14
    assert vector_picture-pictures>.5
    for t in (0.,.001,.999,1.):
        assert picture_blend(a,b,varying,p,t)==pair(a,b,p,t,varying(p))
    fixture='prefix\n'+ANCHOR+'suffix\n'
    assert (fixture.replace(ANCHOR,ANCHOR+OVERLAP,1)).replace(OVERLAP,'',1)==fixture
    for bad in ('',fixture,fixture+fixture):
        try:add(bad)
        except ValueError:pass
        else:raise AssertionError('unpinned source accepted')
    return dict(scope='CPU formula controls only; no GPU or footage quality result',
                grid_spacing_full_pixels=8,node_centers_first=[4,12,20],constant_identity_checks=constant_checks,
                weights_nonnegative_and_normalized=True,edge_policy='Replicate the first/last in-image grid node',
                source_phase_identity=True,nonlinear_picture_vs_vector=dict(nodes=nodes,weights=weights,
                    node_vectors=[varying(n) for n in nodes],averaged_vector=averaged,
                    vector_blend_picture=vector_picture,picture_blend=pictures,
                    difference=vector_picture-pictures,meaning='A deliberate worsening example; not a quality claim'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path,nargs='?');p.add_argument('output',type=Path,nargs='?')
    p.add_argument('--control',action='store_true');args=p.parse_args()
    if args.control:print(json.dumps(control(),indent=2,allow_nan=False));return
    if not args.source or not args.output:p.error('INPUT and OUTPUT required unless --control is used')
    args.output.write_text(add(args.source.read_text()))


if __name__=='__main__':main()
