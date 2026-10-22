#!/usr/bin/env python3
"""CPU summary of guard_followup.py: frozen/headline sets, strict screen and partial local repair.
COMMAND: python3 tests/probes/cage/guard_report.py WORK (WORK is $NP_SCRATCH/bar-guard).
No GPU work and no tuning. Refuse incomplete case sets; never average the union as a canonical mean.
"""
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import ladder_sets

w=Path(sys.argv[1]);r=json.loads((w/'followup/results.json').read_text());rows={x['case']:x for x in r['ladder']}
if set(rows)!=set(ladder_sets.frozen())|set(ladder_sets.headline()):raise ValueError('incomplete or wrong cases')
sets={}
for name,cs in [('frozen',ladder_sets.frozen()),('headline',ladder_sets.headline())]:
 sets[name]={m:float(np.mean([min(40,rows[c][m]) for c in cs])) for m in ['high','guard']}
 sets[name]['delta']=sets[name]['guard']-sets[name]['high']
base=json.loads((w.parent/'bar-pipeline/results.json').read_text())['cases'][3]
old=next(x['mse'] for x in base['exploratory_flow_selected_picture_masks'] if x['mask_shift_x']==3)
local=r['fixed_local_mask_mse']
result={'sets':sets,'worst':min(rows.values(),key=lambda x:x['delta']),
 'screen_pass':min(x['delta'] for x in rows.values())>=-1 and min(x['delta'] for x in sets.values())>=-.05 and r['smoke_pass'],
 'c3_log_repeat':r['c3_logs_identical'],'local_mask_mse':{'high':old[0],'bars':old[1],'guard':local},
 'guard_local_delta_vs_high_db':float(10*np.log10(old[0]/local)),
 'guided_crop_guard_delta_db':float(10*np.log10(base['synthesized_mse'][0]/r['guided_crop_mse'])),
 'limits':'M5 screen; no Arc identity verdict, film gate or timing; local regression remains'}
(w/'followup/report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
