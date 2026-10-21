import re, sys, pathlib, collections
def passes(text):
    out=[]
    for block in re.split(r"(?m)^(?=//!HOOK\b)", text):
        if not block.startswith("//!HOOK"): continue
        g=lambda k: (re.search(r"(?m)^//!%s\s+(.*)$"%k, block) or [None,None])
        m=re.search(r"(?m)^//!HOOK\s+(\S+)", block); hook=m.group(1)
        save=re.search(r"(?m)^//!SAVE\s+(\S+)", block); save=save.group(1) if save else None
        w=re.search(r"(?m)^//!WIDTH\s+(.*)$", block); w=w.group(1).strip() if w else "full"
        when=re.search(r"(?m)^//!WHEN\s+(.*)$", block); when=when.group(1).strip() if when else ""
        desc=re.search(r"(?m)^//!DESC\s+(.*)$", block); desc=desc.group(1).strip() if desc else ""
        binds=re.findall(r"(?m)^//!BIND\s+(\S+)", block)
        comp=bool(re.search(r"(?m)^//!COMPUTE", block))
        body=block.split("\n",1)[1] if "\n" in block else ""
        pc = "pair_changed" in body
        out.append(dict(hook=hook,save=save,w=w,when=when,desc=desc,binds=binds,comp=comp,pc=pc))
    return out
def dead(ps):
    live=[False]*len(ps)
    for i in range(len(ps)-1,-1,-1):
        p=ps[i]
        if p["save"] is None or p["save"]==p["hook"]: live[i]=True; continue
        live[i]=any(live[j] and p["save"] in ps[j]["binds"] for j in range(i+1,len(ps)))
    return live
def level(w):
    m=re.search(r"/\s*(\d+)|(\d+)\s*/", w.replace("HOOKED.w","").replace("FRAME_MIX.w",""))
    if "HOOKED.w HOOKED.w" in w or w.strip()=="1": return "1x1"
    m=re.search(r"(\d+)\s*/", w)
    return ("1/"+m.group(1)) if m else "full"
for f in sys.argv[1:]:
    t=pathlib.Path(f).read_text(encoding="utf-8"); ps=passes(t); lv=dead(ps)
    print(f"=== {pathlib.Path(f).name}: {len(ps)} passes, {sum(not x for x in lv)} dead, {sum(bool(p['when']) for p in ps)} WHEN-gated, {sum(p['pc'] for p in ps)} pair_changed-cached, {sum(p['comp'] for p in ps)} compute")
    c=collections.Counter(level(p["w"]) for p in ps); print("  by level:", dict(c))
    c2=collections.Counter(level(p["w"]) for p in ps if p["when"]); print("  gated by level:", dict(c2))
    if "-v" in sys.argv[0] or len(sys.argv)==2:
        for i,p in enumerate(ps):
            print(f"  {i:3d} {level(p['w']):5s} {'D' if not lv[i] else ' '} {'C' if p['pc'] else ' '} {'W' if p['when'] else ' '} {p['save'] or '-':22s} <- {','.join(p['binds']):60s} | {p['desc'][:70]}")
