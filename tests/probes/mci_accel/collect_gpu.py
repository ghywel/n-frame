#!/usr/bin/env python3
"""Re-audit this bounded GPU block and extract portable numerical evidence.

collect_gpu.py GPU_SCRATCH CPU_SCRATCH OUTPUT.json
No GPU work. Requires external captures, raw logs/results and CPU certificates.
"""
import json
from pathlib import Path
import sys
from audit_replays import audit
from gate import require, save, sha


def main():
    root,cpu,out=[Path(p).resolve() for p in sys.argv[1:]]
    save(out,dict(execution_status='incomplete'))
    groups=[('mac-replays','captures','all'),('mac-hotspot','hotspot-captures','all'),
            ('nas/arc-replays-validated','captures','all'),('nas/arc-hotspot','hotspot-captures','all'),
            ('mac-staging','captures','all'),('mac-staging-hotspot','hotspot-captures','all'),
            ('nas/arc-staging','captures','all'),('nas/arc-staging-hotspot','hotspot-captures','all'),
            ('nas/arc-direct-new','captures','shirt,suit'),('nas/arc-direct-new-hotspot','hotspot-captures','all')]
    results={}
    for group,base,cases in groups:
        results[group]=audit(root/base/'capture-matrix.json',cpu/'inputs/fixtures.json',
                             root/group/'replays.json',cases,cpu)
        print('audited',group,flush=True)
    controls={}
    for group in ['mac-controls','nas/arc-controls','mac-staging-controls','nas/arc-staging-controls']:
        folder=root/group;summary=folder/'gpu-controls.json';d=json.loads(summary.read_text())
        require(d['execution_status']=='complete' and d['stage']=='gpu' and
                d['gpu_controls_status']=='complete','incomplete GPU controls')
        for row in d['runner_trials']:
            name=row['name'];path=folder/(name+'.json');rec=json.loads(path.read_text())
            require(sha(path)==row['record_sha256'] and rec['execution_status']=='complete' and
                    rec['returncode']==row['returncode'] and rec['expected_status']==row['status'],
                    'control summary/record disagreement')
            require(sha(folder/(name+'.stdout'))==rec['stdout_sha256']==row['stdout_sha256'] and
                    sha(folder/(name+'.stderr'))==rec['stderr_sha256']==row['stderr_sha256'],
                    'control raw output changed')
            require(json.loads((folder/(name+'.stdout')).read_text())==rec['response'],
                    'control parsed/raw response disagreement')
        controls[group]=dict(summary_sha256=sha(summary),results=d)
    audit_controls=root/'audit-controls/audit-controls.json'
    failures=json.loads(audit_controls.read_text())
    require(failures['execution_status']=='complete','incomplete audit controls')
    save(out,dict(schema=1,execution_status='complete',
        scope='Captured-frame rendering equivalence and bounded replay timings; no live playback claim',
        original_matrix_captures=21,supplementary_shirt_captures=1,
        groups=results,controls=controls,audit_controls=dict(sha256=sha(audit_controls),results=failures),
        collector_sha256=sha(__file__)))


if __name__=='__main__':main()
