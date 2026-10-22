#!/usr/bin/env python3
"""RUN-ON: cpu. COMMAND: python3 tests/probes/uncertainty/link_covariance.py DATA --out JSON
G012 fixes sampling, reconstruction gate, frozen training and held-out variance prediction.
No Gaussian/constant-covariance assumption is silently treated as calibration.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from fit_math import basis
from sext_resid import scene_law
CASES=['M2c_period40_v10','A4_accel_tex_a033','O9_osc_tex_fast']

def sample(path,case,rng):
    z=np.load(path);frames=z['frames'];x0,y0,bw,bh,_=scene_law(case)
    fs=[];ys=[];xs=[]
    for f,n in enumerate(frames):
        T=n/24;xs.extend(np.floor(x0(T)+rng.uniform(4,bw-4,1024)).astype(int));ys.extend(np.floor(y0+rng.uniform(4,bh-4,1024)).astype(int)-160);fs.extend([f]*1024)
    fs,ys,xs=map(np.asarray,[fs,ys,xs])
    state=z['state'][fs,ys,xs];num=z['nlinks'][fs,ys,xs]
    mask=((state&8)!=0)&(num==5)
    counts={'sampled':len(mask),'eligible':int(mask.sum()),'not_fitted':int(((state&8)==0).sum()),'not_five_links':int((num!=5).sum())}
    fs,ys,xs=fs[mask],ys[mask],xs[mask]
    d=z['d'][fs,:,ys,xs,:].astype(float);w=z['w'][fs,:,ys,xs].astype(float);tau=z['tau'][fs,:,ys,xs].astype(float)
    if np.max(abs(tau-np.rint(tau)))>=.0001:raise ValueError('tau encoding not calibrated')
    tau=np.rint(tau)
    if not np.all(tau[:,:5]==np.array([-3,-2,-1,1,2])):raise ValueError('unexpected live link ordering')
    if not np.all(w[:,:5]>.05) or np.any(w[:,5]>.05):raise ValueError('unexpected active slots')
    tc=z['tc'][fs,ys,xs].astype(float);vf=z['vfit'][fs,ys,xs,:].astype(float)
    tau=np.concatenate([tau,np.zeros((len(tau),1))],axis=1)
    w=np.concatenate([w,np.ones((len(w),1))],axis=1);w=np.where(w>.05,w,0)
    d=np.concatenate([d,np.zeros((len(d),1,2))],axis=1)
    X=basis(tau-tc[:,None]);root=np.sqrt(w)
    A=np.linalg.pinv(X*root[:,:,None])*root[:,None,:]
    h=np.einsum('ni,nij->nj',basis(-tc,1),A)
    recon=np.einsum('ni,nij->nj',h,d)
    diff=np.linalg.norm(recon-vf,axis=1)
    gate=float(np.quantile(diff,.99))
    if gate>=.05:raise ValueError(f'{case}: reconstruction p99 {gate} >=.05')
    # Counterfactual: a coherent one-pixel/frame velocity error in every measured link.
    bad=d.copy();bad[:,:,0]+=tau
    badrecon=np.einsum('ni,nij->nj',h,bad)
    badgate=float(np.quantile(np.linalg.norm(badrecon-vf,axis=1),.99))
    if badgate<.05:raise ValueError('coherent wrong input was not detected')
    truth=np.zeros_like(d);vel=np.zeros((len(d),2))
    for f,n in enumerate(frames):
        m=fs==f;T=n/24
        for j,t in enumerate([-3,-2,-1,1,2]):truth[m,j,0]=x0(T+t/24)-x0(T)
        dt=1e-5;vel[m,0]=(x0(T+dt)-x0(T-dt))/(2*dt*24)
    error=(d-truth)[:,:5,:].reshape(len(d),10)
    trunc=np.einsum('ni,nij->nj',h,truth)-vel
    projected=np.einsum('ni,nij->nj',h[:,:5],error.reshape(-1,5,2))
    return {'error':error,'h':h[:,:5],'projected':projected,'trunc':trunc,'counts':counts,
            'reconstruction_p99':gate,'coherent_fault_p99':badgate,'frames':frames.tolist(),
            'truth':truth[:,:5,:],'velocity':vel}

def evaluate(data,mu,cov):
    h=data['h'];hs=np.zeros((len(h),2,10));hs[:,0,::2]=h;hs[:,1,1::2]=h
    centered=data['projected']-np.einsum('nai,i->na',hs,mu)
    V=np.einsum('nai,ij,nbj->nab',hs,cov,hs)
    D=np.einsum('nai,i,nbi->nab',hs,np.diag(cov),hs)
    actual=np.var(data['projected'],axis=0)
    full=np.mean(np.diagonal(V,axis1=1,axis2=2),axis=0);diag=np.mean(np.diagonal(D,axis1=1,axis2=2),axis=0)
    q=np.einsum('ni,nij,nj->n',centered,np.linalg.pinv(V),centered)
    return {'counts':data['counts'],'reconstruction_p99':data['reconstruction_p99'],
      'coherent_fault_p99':data['coherent_fault_p99'],'link_error_mean':data['error'].mean(axis=0).tolist(),
      'actual_projected_variance':actual.tolist(),'full_predicted_variance':full.tolist(),
      'diagonal_predicted_variance':diag.tolist(),'full_to_actual':(full/actual).tolist(),
      'diagonal_to_actual':(diag/actual).tolist(),'gaussian_68_ellipse_coverage':float(np.mean(q< -2*np.log(.32))),
      'projected_bias':data['projected'].mean(axis=0).tolist(),
      'truncation_norm_p50_p95':np.quantile(np.linalg.norm(data['trunc'],axis=1),[.5,.95]).tolist()}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('data',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rng=np.random.default_rng(20261022)
    data=[sample(a.data/(c+'.npz'),c,rng) for c in CASES]
    train=np.concatenate([d['error'] for d in data[:2]])
    mu=train.mean(axis=0);cov=np.cov(train,rowvar=False,ddof=1)
    rows={c:evaluate(d,mu,cov) for c,d in zip(CASES,data)}
    full=np.array(rows[CASES[-1]]['full_to_actual']);diag=np.array(rows[CASES[-1]]['diagonal_to_actual'])
    held=bool(np.all((full>.5)&(full<2)) and np.all(abs(np.log(full))<abs(np.log(diag))))
    result={'cases':rows,'training_cases':CASES[:2],'holdout':CASES[-1],'mean':mu.tolist(),'covariance':cov.tolist(),
      'prediction_held':held,'input_sha256':{c:hashlib.sha256((a.data/(c+'.npz')).read_bytes()).hexdigest() for c in CASES}}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':rows,'prediction_held':held},indent=2))
    return 0 if held else 3
if __name__=='__main__':raise SystemExit(main())
