#!/usr/bin/env python3
"""Compile the audit's semantically changed ON variants through gen_metal.py, glslc and spirv-cross.
COMMAND: python3 tests/probes/switches/compile.py AUDIT_DIR
STICKY variants are expected to be rejected by the current Metal graph generator, not silently accepted.
This validates compilation of representative settings, not every parameter combination or GPU quality.
"""
import json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[3];out=Path(sys.argv[1]).resolve();r=json.loads((out/'results.json').read_text())
files={};rows=[]
for c in r['checks']:
 if c.get('expected_change') and c['pass']:
  files.setdefault(c['on_file'],[]).append(c['name'])
for f,names in files.items():
 dst=out/'compiled'/Path(f).stem
 p=subprocess.run([sys.executable,str(R/'tests/gen_metal.py'),str(out/f),str(dst),'--compile'],capture_output=True,text=True)
 (out/(Path(f).stem+'-compile.log')).write_text(p.stdout+p.stderr)
 sticky=all('STICKY' in n for n in names)
 ok=p.returncode==0 if not sticky else p.returncode!=0 and 'STICKY' in (p.stdout+p.stderr)
 row={'file':f,'switches':names,'expected_host_rejection':sticky,'pass':ok,'compiler_returncode':p.returncode}
 if p.returncode==0:row['passes']=len(json.loads((dst/'graph.json').read_text())['passes'])
 rows.append(row);print(json.dumps(row),flush=True)
(out/'compilation.json').write_text(json.dumps(rows,indent=2)+'\n')
sys.exit(0 if all(x['pass'] for x in rows) else 1)
