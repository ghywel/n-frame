import sys, pathlib, collections
sys.path.insert(0, '~/Developer/np-scratch/swarm-20261021/cost')
import prune_sim as P
SH = pathlib.Path('REPO/shaders')
VP = 'bidirectional-interpolation-variational-propagated'
rows = [('base', 'bidirectional-interpolation'), ('propagated (fast tier)', 'bidirectional-interpolation-propagated'),
        ('animation (rec. for animation)', 'bidirectional-interpolation-animation'), ('recommendation (vp)', VP),
        ('Low = vp-cut', VP + '-cut'), ('Standard = adopt-cut', VP + '-global-cage-energy-carry-adopt-cut'),
        ('High = lattice-cut', VP + '-global-cage-energy-carry-adopt-lattice-cut'), ('High 4k twin', VP + '-global-cage-energy-carry-adopt-lattice-cut-4k'),
        ('tri-prop', 'tridirectional-interpolation-propagated'), ('quad-prop', 'quaddirectional-interpolation-propagated'),
        ('quad-cadence', 'quaddirectional-interpolation-propagated-cadence'), ('quint-prop', 'quintdirectional-interpolation-propagated'),
        ('sext-prop', 'sextdirectional-interpolation-propagated')]
print('| tier | passes | tail (WHEN) | run at read_view 0 | full | 1/2 | 1/4 | 1/8 | 1/16 | 1/32+ | tiny | pair-cached | dead (dead_passes.py) | dead (dataflow, this lane) | half-dead fused | dead share of dispatches |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
tot = 0
for label, stem in rows:
    t = (SH / (stem + '.glsl')).read_text(encoding='utf-8')
    ps = P.blocks(t); live, tl = P.run(ps)
    lv = collections.Counter(P.level(p['w']) for p in ps if not p['when'] if 'when' in p) if False else None
    import re
    def when(b): return bool(re.search(r'(?m)^//!WHEN', b))
    blocks = [b for b in re.split(r'(?m)^(?=//!HOOK\b)', t) if b.startswith('//!HOOK')]
    gated = sum(when(b) for b in blocks)
    levels = collections.Counter(P.level(p['w']) for p in ps)
    cached = sum(p['pc'] for p in ps)
    # dead_passes.py's own count
    live0 = [False]*len(ps)
    for i in range(len(ps)-1, -1, -1):
        p = ps[i]
        if p['save'] is None or p['save'] == p['hook']: live0[i] = True; continue
        live0[i] = any(live0[j] and p['save'] in ps[j]['binds'] for j in range(i+1, len(ps)))
    d0 = sum(not x for x in live0); d1 = sum(not x for x in live); h = sum(1 for x in tl if x is False)
    tot += len(ps)
    small = levels['1/32'] + levels['1/64']
    print(f"| {label} | {len(ps)} | {gated} | {len(ps)-gated} | {levels['full']} | {levels['1/2']} | {levels['1/4']} | {levels['1/8']} | {levels['1/16']} | {small} | {levels['tiny']+levels['1x1']} | {cached} | {d0} | {d1} | {h} | {100*(d1+0.5*h)/len(ps):.0f}% |")
print('total passes enumerated:', tot)
