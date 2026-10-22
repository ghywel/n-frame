#!/usr/bin/env python3
"""RUN-ON: cpu. COMMAND: python3 tests/probes/uncertainty/anchor_gls.py DATA --out JSON
G015 exploratory prediction: >=10% link variance improvement per axis, <=10% total-MSE increase on reused O9.
Exact-anchor quartic derivative, minimum covariance weights on frozen training data. No shader edits.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from link_covariance import sample,CASES

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('data',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 rng=np.random.default_rng(20261022);data=[sample(a.data/(c+'.npz'),c,rng) for c in CASES]
 train=np.concatenate([d['error'] for d in data[:2]]);cov=np.cov(train,rowvar=False)
 t=np.array([-3,-2,-1,1,2],float);X=np.stack([t**k/math.factorial(k) for k in range(1,5)],axis=1)
 h0=np.linalg.pinv(X)[0];_,_,V=np.linalg.svd(X.T);n=V[-1];hs=[];checks={}
 for axis in [0,1]:
  C=cov[axis::2,axis::2];alpha=-(n@C@h0)/(n@C@n);h=h0+alpha*n;hs.append(h)
  checks[f'quartic_axis{axis}']=bool(np.max(abs(h@X-np.array([1,0,0,0])))<1e-10)
  checks[f'minimizer_axis{axis}']=bool(abs(n@C@h)<1e-10 and all((h+u*n)@C@(h+u*n)>h@C@h for u in [-1,.1,1]))
  wrong=h.copy();wrong[0]+=.1
  checks[f'bad_coefficients_refused_axis{axis}']=bool(np.max(abs(wrong@X-np.array([1,0,0,0])))>.01)
 if not all(checks.values()):raise ValueError('algebra controls failed')
 hs=np.array(hs);rows={}
 for case,d in zip(CASES,data):
  old=d['projected'];err=d['error'].reshape(-1,5,2)
  variants={}
  for name,h in [('anchor_ols',np.stack([h0,h0])),('anchor_gls',hs)]:
   induced=np.einsum('nka,ak->na',err,h)
   trunc=np.einsum('nka,ak->na',d['truth'],h)-d['velocity']
   variants[name]={'link_variance':np.var(induced,axis=0).tolist(),'total_mse':np.mean((induced+trunc)**2,axis=0).tolist(),
       'truncation_p95':float(np.quantile(np.linalg.norm(trunc,axis=1),.95))}
  oldvar=np.var(old,axis=0);oldmse=np.mean((old+d['trunc'])**2,axis=0)
  rows[case]={'old_link_variance':oldvar.tolist(),'old_total_mse':oldmse.tolist(),'variants':variants,
     'gls_variance_ratio':(np.array(variants['anchor_gls']['link_variance'])/oldvar).tolist(),
     'gls_total_mse_ratio':(np.array(variants['anchor_gls']['total_mse'])/oldmse).tolist()}
 last=rows[CASES[-1]];held=bool(max(last['gls_variance_ratio'])<=.9 and max(last['gls_total_mse_ratio'])<=1.1)
 r={'checks':checks,'h_ols':h0.tolist(),'h_gls':hs.tolist(),'null_vector':n.tolist(),'cases':rows,'exploratory_prediction_held':held}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
 return 0 if held else 3
if __name__=='__main__':raise SystemExit(main())
