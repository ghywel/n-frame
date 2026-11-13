#!/usr/bin/env python3
"""Fail-closed comparison of one complete 45-case bench run, including region logs."""
import json
import math
from pathlib import Path
import re
import sys
import numpy as np


def read(path):
    rows={}
    for line in path.read_text().splitlines():
        m=re.search(r'n:(\d+).*?psnr_y:([\d.]+|inf)',line)
        if m:
            index=int(m[1]); value=float(m[2])
            assert index not in rows, (path, 'duplicate frame', index)
            assert math.isfinite(value), (path, 'nonfinite score', index)
            rows[index]=value
    assert set(rows)==set(range(1,61)),(path, 'expected exactly frames 1..60', sorted(rows))
    return rows


def main(root, label):
    dirs=sorted(p for p in root.iterdir() if p.is_dir());assert len(dirs)==45,len(dirs)
    results=[]
    for d in dirs:
        for name in ('high',label):
            error=(d/f'{name}.err').read_text().lower()
            assert not any(t in error for t in ('compile status','disabling','failed to')), (d,name,error[-400:])
            assert error.count('hook skipped')<=2,(d,name)
        row={'case':d.name}
        for suffix in ('.log','.region.log'):
            a=read(d/f'high{suffix}');b=read(d/f'{label}{suffix}');assert a.keys()==b.keys(),d
            for end in (0,2):
                keep=[k for k in a if k>5 and k<=max(a)-end and (k-1)%5!=0]
                assert keep
                aa=float(np.mean([a[k] for k in keep]));bb=float(np.mean([b[k] for k in keep]))
                assert math.isfinite(aa) and math.isfinite(bb), (d, suffix, end)
                key=('region' if 'region' in suffix else 'frame')+('_interior' if end else '')
                row[key]=dict(high=aa,variant=bb,delta=bb-aa,frames=len(keep))
        results.append(row)
    out={'variant':label,'cases':results}
    (root/f'{label}-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
    for key in ('frame','frame_interior','region','region_interior'):
        ordered=sorted(results,key=lambda r:r[key]['delta'])
        print(key,'worst',[(r['case'],round(r[key]['delta'],3)) for r in ordered[:8]])
        print('losses >.1',sum(r[key]['delta']<-.1 for r in ordered),'losses >1',sum(r[key]['delta']<-1 for r in ordered))


if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2])
