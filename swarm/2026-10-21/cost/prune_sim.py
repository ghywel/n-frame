"""prune_sim.py <shader>...: simulate the L7 prune done properly. Dataflow per pass: SAVE + imageStore = writes;
BIND (sampled) + imageLoad = reads. A fused pass '[fused with its B->A twin' is split: its B->A twin's inputs are the
FLOW_*_BA bind and the *_BA_M1_ST storage it writes; if the twin's storage output is unread, the twin's binds are dropped.
Iterate to a fixpoint. Report dead passes by level, and the dispatch share."""
import re, sys, pathlib, collections
def blocks(text):
    out=[]
    for b in re.split(r"(?m)^(?=//!HOOK\b)", text):
        if not b.startswith("//!HOOK"): continue
        hook=re.search(r"(?m)^//!HOOK\s+(\S+)", b).group(1)
        save=re.search(r"(?m)^//!SAVE\s+(\S+)", b); save=save.group(1) if save else None
        binds=set(re.findall(r"(?m)^//!BIND\s+(\S+)", b))
        desc=re.search(r"(?m)^//!DESC\s+(.*)$", b); desc=desc.group(1).strip() if desc else ""
        w=re.search(r"(?m)^//!WIDTH\s+(.*)$", b); w=w.group(1).strip() if w else "full"
        st_w=set(re.findall(r"imageStore\(\s*(\w+)", b)); st_r=set(re.findall(r"imageLoad\(\s*(\w+)", b))
        pc="pair_changed" in b
        out.append(dict(hook=hook,save=save,binds=binds,desc=desc,w=w,st_w=st_w,st_r=st_r,pc=pc,twin=None))
    for p in out:
        if "fused with" in p["desc"] and p["save"]:
            m=re.search(r"_([A-F])([A-F])(?=_|$)", p["save"])
            if not m: continue
            rev="_"+m.group(2)+m.group(1)
            tw={x for x in p["st_w"] if rev in x}
            if tw: p["twin"]=dict(binds={x for x in p["binds"] if rev in x and not x.endswith("_ST")}, st_w=tw)
    return out
def level(w):
    if w.strip()=="1" or "HOOKED.w HOOKED.w" in w: return "1x1"
    m=re.search(r"HOOKED\.w\s+(\d+)\s*/", w)
    if m: return "1/"+m.group(1)
    if "HOOKED.w" in w or "FRAME_MIX.w" in w: return "full"
    return "tiny"
def run(ps):
    n=len(ps); live=[p["save"] is None or p["save"]==p["hook"] for p in ps]
    twin_live=[True if p["twin"] else None for p in ps]
    def reads(j, name, sampled):
        p=ps[j]
        if not live[j]: return False
        if sampled:
            if name not in p["binds"]: return False
            if p["twin"] and name in p["twin"]["binds"] and not twin_live[j]: return False
            return True
        return name in p["st_r"]
    while True:
        changed=True
        while changed:   # liveness to a fixpoint with the twins as they stand
            changed=False
            for i,p in enumerate(ps):
                if live[i]: continue
                ok=False
                if p["save"] and any(reads(j,p["save"],True) for j in range(i+1,n)): ok=True
                for w in p["st_w"]:
                    if any(j!=i and reads(j,w,False) for j in range(n)): ok=True
                if ok: live[i]=True; changed=True
        killed=False   # then a twin whose storage outputs no live pass reads is dead; recompute from scratch
        for i,p in enumerate(ps):
            if p["twin"] and twin_live[i] and not any(any(j!=i and reads(j,w,False) for j in range(n)) for w in p["twin"]["st_w"]):
                twin_live[i]=False; killed=True
        if not killed: return live, twin_live
        live=[p["save"] is None or p["save"]==p["hook"] for p in ps]
for f in sys.argv[1:]:
    ps=blocks(pathlib.Path(f).read_text(encoding="utf-8")); live,tl=run(ps)
    dead=[i for i in range(len(ps)) if not live[i]]; half=[i for i in range(len(ps)) if tl[i] is False]
    c=collections.Counter(level(ps[i]["w"]) for i in dead)
    unc=sum(1 for i in dead if not ps[i]["pc"])
    print(f"=== {pathlib.Path(f).name}: {len(ps)} passes; DEAD {len(dead)} (+{len(half)} half of a fused pass) = {100*(len(dead)+0.5*len(half))/len(ps):.0f}% of dispatches; dead by level {dict(c)}; dead passes without a pair_changed cache: {unc}")
    for i in dead: print(f"   #{i:3d} {level(ps[i]['w']):5s} {'cached' if ps[i]['pc'] else 'EVERY FRAME'} {ps[i]['save']:16s} {ps[i]['desc'][:80]}")
    for i in half: print(f"   #{i:3d} {level(ps[i]['w']):5s} HALF   {ps[i]['save']:16s} {ps[i]['desc'][:80]}")
