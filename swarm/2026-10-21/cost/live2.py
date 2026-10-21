"""live2.py: liveness that also follows STORAGE textures (imageStore = write, imageLoad = read), any direction (storage
persists across frames). Compare with dead_passes.py, which follows //!SAVE and //!BIND only."""
import re, sys, pathlib
def blocks(text):
    out=[]
    for b in re.split(r"(?m)^(?=//!HOOK\b)", text):
        if not b.startswith("//!HOOK"): continue
        hook=re.search(r"(?m)^//!HOOK\s+(\S+)", b).group(1)
        save=re.search(r"(?m)^//!SAVE\s+(\S+)", b); save=save.group(1) if save else None
        binds=set(re.findall(r"(?m)^//!BIND\s+(\S+)", b))
        desc=re.search(r"(?m)^//!DESC\s+(.*)$", b); desc=desc.group(1).strip() if desc else ""
        st_w=set(re.findall(r"imageStore\(\s*(\w+)", b))
        st_r=set(re.findall(r"imageLoad\(\s*(\w+)", b)) | set(re.findall(r"imageAtomic\w*\(\s*(\w+)", b))
        out.append(dict(hook=hook,save=save,binds=binds,desc=desc,st_w=st_w,st_r=st_r))
    return out
def analyse(text):
    ps=blocks(text); n=len(ps)
    live=[p["save"] is None or p["save"]==p["hook"] for p in ps]
    changed=True
    while changed:
        changed=False
        for i,p in enumerate(ps):
            if live[i]: continue
            ok=False
            if p["save"] and any(live[j] and p["save"] in ps[j]["binds"] for j in range(i+1,n)): ok=True
            for w in p["st_w"]:
                # a storage write is live if another live pass reads it (any direction: storage persists)
                if any(live[j] and j!=i and w in ps[j]["st_r"] for j in range(n)): ok=True
            if ok: live[i]=True; changed=True
    return ps, live
if __name__=="__main__":
    here=pathlib.Path(__file__).resolve()
    root=pathlib.Path(sys.argv[1]); files=sorted(root.rglob("*.glsl")) if root.is_dir() else [root]
    tot=0
    for f in files:
        ps,live=analyse(f.read_text(encoding="utf-8"))
        d=[(i,ps[i]["save"],ps[i]["desc"][:50]) for i in range(len(ps)) if not live[i]]
        tot+=len(d)
        if d: print(f"{f.name}: {len(d)} dead of {len(ps)}: " + "; ".join(f"#{i} {s}" for i,s,_ in d))
    print("LIVE2 DONE:", tot, "dead in", len(files), "files")
