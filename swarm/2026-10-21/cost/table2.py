import sys, pathlib, collections, re
sys.path.insert(0, '~/Developer/np-scratch/swarm-20261021/cost')
import prune_sim as P
SH = pathlib.Path('REPO/shaders')
VP = 'bidirectional-interpolation-variational-propagated'
W, H = 1280, 720
def rpn(expr, w, h):
    st=[]
    for tok in expr.split():
        if tok in ('+','-','*','/'):
            b=st.pop(); a=st.pop(); st.append({'+':a+b,'-':a-b,'*':a*b,'/':a/b}[tok])
        elif tok.endswith('.w'): st.append(w)
        elif tok.endswith('.h'): st.append(h)
        else: st.append(float(tok))
    return st[-1]
def size(block):
    w=re.search(r"(?m)^//!WIDTH\s+(.*)$", block); h=re.search(r"(?m)^//!HEIGHT\s+(.*)$", block)
    return (int(rpn(w.group(1),W,H)) if w else W, int(rpn(h.group(1),W,H)) if h else H)
rows = [('base', 'bidirectional-interpolation'), ('propagated', 'bidirectional-interpolation-propagated'),
        ('animation', 'bidirectional-interpolation-animation'), ('recommendation (vp)', VP),
        ('Low = vp-cut', VP + '-cut'), ('Standard = adopt-cut', VP + '-global-cage-energy-carry-adopt-cut'),
        ('High = lattice-cut', VP + '-global-cage-energy-carry-adopt-lattice-cut'),
        ('tri-prop', 'tridirectional-interpolation-propagated'), ('quad-prop', 'quaddirectional-interpolation-propagated'),
        ('quint-prop', 'quintdirectional-interpolation-propagated'), ('sext-prop', 'sextdirectional-interpolation-propagated')]
print('| tier | dispatches at read_view 0 | of which pair-cached | full-res passes | Mtexels per output frame (all) | Mtexels in uncached passes | dead dispatches (+half) | dead Mtexels | dead share: dispatches / texels | fusion candidates after prune (same size, no dependency, adjacent) |')
print('|---|---|---|---|---|---|---|---|---|---|')
for label, stem in rows:
    t=(SH/(stem+'.glsl')).read_text(encoding='utf-8')
    blocks=[b for b in re.split(r'(?m)^(?=//!HOOK\b)', t) if b.startswith('//!HOOK')]
    ps=P.blocks(t); live,tl=P.run(ps)
    sizes=[size(b) for b in blocks]; gated=[bool(re.search(r'(?m)^//!WHEN',b)) for b in blocks]
    idx=[i for i in range(len(ps)) if not gated[i]]
    tex=lambda i: sizes[i][0]*sizes[i][1]/1e6
    total=sum(tex(i) for i in idx); unc=sum(tex(i) for i in idx if not ps[i]['pc'])
    dead=[i for i in idx if not live[i]]; half=[i for i in idx if tl[i] is False]
    dtex=sum(tex(i) for i in dead)+0.5*sum(tex(i) for i in half)
    full=sum(1 for i in idx if sizes[i]==(W,H))
    # fusion candidates: consecutive live ungated passes with equal size and no dependency
    alive=[i for i in idx if live[i]]
    cands=[]
    for a,b in zip(alive, alive[1:]):
        pa,pb=ps[a],ps[b]
        if sizes[a]!=sizes[b]: continue
        wa={pa['save']}|pa['st_w']; rb=pb['binds']|pb['st_r']; wb={pb['save']}|pb['st_w']
        if wa & rb or wb & (pa['binds']|pa['st_r']) or pa['save']==pb['save']: continue
        cands.append((a,b))
    print(f"| {label} | {len(idx)} | {sum(ps[i]['pc'] for i in idx)} | {full} | {total:.1f} | {unc:.1f} | {len(dead)} (+{len(half)}) | {dtex:.2f} | {100*(len(dead)+0.5*len(half))/len(idx):.0f}% / {100*dtex/total:.0f}% | {len(cands)} |")
    if label in ('recommendation (vp)','High = lattice-cut'):
        print('    fusion candidates:', '; '.join(f"#{a}+#{b} {ps[a]['save']}/{ps[b]['save']} @{sizes[a][0]}x{sizes[a][1]}" for a,b in cands))
