#!/usr/bin/env python3
"""Reproducible switch wiring audit, CPU only. No quality/default adoption is inferred from text differences.
RUN-ON: cpu. COMMAND: python3 tests/probes/switches/audit.py --out "$NP_SCRATCH/switch-audit"
Checks semantic off/on differences, latent controls, dependencies, original regeneration, and optional app metadata.
A deliberately invalid dependency must fail; every ordinary expected difference must be observed.
"""
import argparse,ast,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
FILES=list((ROOT/'tests').glob('gen_*.py'))+[ROOT/'tests/trust_gate.py',ROOT/'tests/alias_carry.py']

def inventory():
 r=[]
 for p in FILES:
  t=p.read_text();tree=ast.parse(t)
  for n in ast.walk(tree):
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('get','getenv') and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
    f=ast.unparse(n.func)
    if f not in ('os.environ.get','os.getenv'):continue
    r.append({'file':str(p.relative_to(ROOT)),'line':n.lineno,'key':n.args[0].value,'default_expression':ast.unparse(n.args[1]) if len(n.args)>1 else 'None'})
 return sorted(r,key=lambda v:(v['file'],v['line']))

def semantic(text):
 text=re.sub(r'//(?!\!).*','',text)
 text=re.sub(r'(?m)^//!DESC.*$','',text)
 return re.sub(r'\s+',' ',text).strip()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--cadence',type=Path);p.add_argument('--demo',type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 inv=inventory();keys={x['key'] for x in inv};cache={};serial=0
 def gen(kind='variational',settings=None,base='bidirectional-interpolation-propagated.glsl'):
  nonlocal serial
  settings=settings or {};key=(kind,tuple(sorted(settings.items())),base)
  if key in cache:return cache[key]
  serial+=1;name=f'{serial:03d}-{kind}';dst=out/(name+'.glsl')
  env={k:v for k,v in os.environ.items() if k not in keys};env.update(settings,PYTHONDONTWRITEBYTECODE='1')
  actualbase=str(ROOT/'shaders/src'/base) if kind=='aperture' else base
  args=['0,0,8,4','0.3','0.08',str(dst),'0','0,0,2,0',base] if kind=='variational' else [str(dst),actualbase]
  r=subprocess.run([sys.executable,str(ROOT/f'tests/gen_{kind}.py'),*args],cwd=ROOT,env=env,capture_output=True,text=True)
  (out/(name+'.log')).write_text(r.stdout+r.stderr)
  value={'ok':r.returncode==0,'file':dst.name,'error':r.stderr.splitlines()[-1] if r.stderr else '', 'text':dst.read_text() if r.returncode==0 else ''}
  cache[key]=value;return value
 checks=[]
 def compare(name,key,off,on,dep=None,kind='variational',changed=True,base='bidirectional-interpolation-propagated.glsl'):
  dep=dep or {};x=gen(kind,{**dep,key:off},base);y=gen(kind,{**dep,key:on},base)
  diff=x['ok'] and y['ok'] and semantic(x['text'])!=semantic(y['text'])
  checks.append({'name':name,'expected_change':changed,'observed_change':bool(diff),'pass':bool(x['ok'] and y['ok'] and diff==changed),'off_file':x['file'],'on_file':y['file']})
 for k in ['GLOBAL_SEED','QZERO_MOIRE','COHERENCE_GATE','COARSE_ENERGY','EDGE_PROP','ALIAS_CARRY','LOCAL_CENTRE','PHASE_FETCH','CUT_MOTION','BAR_REDECIDE','STICKY_CACHE']:
  compare(k,k,'0','1')
 for k,dep in [('ALIAS_PRIOR',{'GLOBAL_SEED':'1'}),('OUTLINE_ADOPT',{'ALIAS_CARRY':'1'}),('PRINT_LATTICE',{'ALIAS_CARRY':'1'}),('TRUST_GATE',{'ALIAS_CARRY':'1'}),('PHASE_GATE',{'PHASE_FETCH':'1'}),('PHASE_FETCH_E',{'PHASE_FETCH':'1'}),('BAR_KEEP',{'BAR_REDECIDE':'1'}),('BAR_BASIN',{'BAR_REDECIDE':'1'}),('ALIAS_APERTURE',{'ALIAS_CARRY':'1'})]:compare(k,k,'0','1',dep)
 knobs=[('QZERO_MOIRE_MIN','.25','.5',{'QZERO_MOIRE':'1'}),('COARSE_ENERGY_WS','8','4',{'COARSE_ENERGY':'1'}),('COARSE_ENERGY_WE','1','2',{'COARSE_ENERGY':'1'}),('EDGE_PROP_TAU','1','2',{'EDGE_PROP':'1'}),('ALIAS_TAU_CARRY','.05','.1',{'ALIAS_CARRY':'1'}),('CUT_EXPLAINED','.3','.5',{'CUT_MOTION':'1'}),('TRUST_DECIDE','full','two',{'TRUST_GATE':'1','ALIAS_CARRY':'1'}),('TRUST_OFFER','whole','parab',{'TRUST_GATE':'1','ALIAS_CARRY':'1'}),('TRUST_UNIQUE','0','1',{'TRUST_GATE':'1','ALIAS_CARRY':'1'}),('TRUST_ALIAS','','.7',{'TRUST_GATE':'1','ALIAS_CARRY':'1'})]
 for k,x,y,d in knobs:compare(k,k,x,y,d)
 for k in ['PRUNE']:compare('PRUNE1',k,'0','1');compare('PRUNE2',k,'1','2')
 compare('ZERO_SEED propagated force-on is redundant','ZERO_SEED','0','1',changed=False)
 compare('ZERO_SEED seeded also redundant','ZERO_SEED','0','1',base='bidirectional-interpolation-seeded.glsl',changed=False)
 fixture=out/'seed-off-source.glsl';s=(ROOT/'shaders/src/bidirectional-interpolation-seeded.glsl').read_text()
 assert s.count('const int ZERO_SEED = 1;')==2
 fixture.write_text(s.replace('const int ZERO_SEED = 1;','const int ZERO_SEED = 0;'))
 compare('ZERO_SEED deliberate off source changes','ZERO_SEED','0','1',base=str(fixture))
 compare('GLOBAL_SEED literal true is off','GLOBAL_SEED','0','true',changed=False)
 for k in ['ALIAS_APERTURE','CUT_EXPLAINED','ALIAS_TAU_CARRY']:compare(k+' latent',k,'0','.1',changed=False)
 for kind in ['tridirectional','quaddirectional','quintdirectional','sextdirectional']:
  compare('STICKY '+kind,'STICKY_CACHE','0','1',kind=kind)
 for kind in ['quaddirectional','quintdirectional','sextdirectional']:
  compare('FORESIGHT '+kind,'FORESIGHT','0','1',kind=kind,changed=kind!='sextdirectional')
 compare('FORESIGHT stock base inactive','FORESIGHT','0','1',kind='quaddirectional',base='bidirectional-interpolation.glsl',changed=False)
 compare('CADENCE quad','CADENCE','0','1',kind='quaddirectional')
 for key,x,y in [('PROP_TENSOR','0','1'),('PROP_TENSOR_R','8','4'),('PROP_TENSOR_EPS','.05','.1')]:compare(key,key,x,y,kind='aperture')
 bad=[{'ALIAS_PRIOR':'1'},{'OUTLINE_ADOPT':'1'},{'PRINT_LATTICE':'1'},{'TRUST_GATE':'1'},{'PHASE_GATE':'1'},{'PHASE_FETCH_E':'1'},{'BAR_KEEP':'1'},{'BAR_BASIN':'1'},{'BAR_REDECIDE':'1','BAR_KEEP':'1','BAR_BASIN':'1'},{'PRUNE':'3'},{'ALIAS_CARRY':'1','TRUST_GATE':'1','TRUST_UNIQUE':'1','TRUST_DECIDE':'two'}]
 for d in bad:
  v=gen(settings=d);checks.append({'name':'invalid '+str(d),'pass':not v['ok'],'expected_rejection':True,'error':v['error']})
 # Ensure a deliberately impossible expectation is detected by the comparison machinery.
 z=gen();counter=semantic(z['text'])!=semantic(z['text']);checks.append({'name':'self-difference counterfactual refused','pass':not counter})
 app=[]
 if a.cadence:
  for g in sorted((a.cadence/'Bench/Resources/graphs').glob('*/graph.json')):
   j=json.loads(g.read_text());name=g.parent.name
   if not name.endswith('-cut') and not name.endswith('-cut-4k'):continue
   stem=name.removesuffix('-4k');src=ROOT/'shaders'/(name+'.glsl');sha=j['source_sha256']
   matches=[]
   for rev in ['eaab23e^','eaab23e']:
    r=subprocess.run(['git','show',rev+':shaders/'+name+'.glsl'],cwd=ROOT,capture_output=True)
    if r.returncode==0 and hashlib.sha256(r.stdout).hexdigest()==sha:matches.append(rev)
   app.append({'graph':name,'window':j['window'],'passes':len(j['passes']),'source_sha256':sha,'current_match':src.exists() and hashlib.sha256(src.read_bytes()).hexdigest()==sha,'historical_matches':matches,'uniforms':j.get('uniforms')})
 constants={}
 for name in ['bidirectional-interpolation-propagated','tridirectional-interpolation-propagated','quaddirectional-interpolation-propagated','quintdirectional-interpolation-propagated','sextdirectional-interpolation-propagated']:
  text=(ROOT/'shaders'/(name+'.glsl')).read_text()
  constants[name]={k:sorted(set(re.findall(r'const int\s+'+k+r'\s*=\s*(\d+);',text))) for k in ['ZERO_SEED','FRAME_DIFF_GATE','SUBPEL_REFINE','SUBPEL_FIT','SUBPEL_SELFREF','QUAD_MODE','TRI_DIAG','DIAG_HOLD_ANCHOR','READ_MEMORY','READ_GATE']}
 result={'inventory':inv,'checks':checks,'passed':sum(x['pass'] for x in checks),'total':len(checks),'cadence_graphs':app,'generated_variants':serial,'source_constants':constants}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['passed','total','generated_variants']},indent=2));print('FAILURES',json.dumps([c for c in checks if not c['pass']]))
 return 0 if all(c['pass'] for c in checks) else 1
if __name__=='__main__':raise SystemExit(main())
