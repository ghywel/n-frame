#!/usr/bin/env python3
"""Actual YUVA inserted-frame regression against stock, including a broken control.

Requires an untouched stock binary, Local's original fused binary, a repaired
binary and a preparation FFmpeg with rawvideo demux/FFV1 encode. Inputs are small
generated synthetic Y/U/V/alpha arrays. All raw outputs and independent exact PTS
framemd5 records are retained; no benchmark or quality conclusion is made.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess


WIDTH, HEIGHT, FRAMES = 80, 48, 12
FORMATS = {"yuva420p": (1, 1), "yuva422p": (1, 0), "yuva444p": (0, 0)}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, obj): Path(path).write_text(json.dumps(obj, indent=2) + "\n")
def require(ok, reason):
    if not ok: raise ValueError(reason)


def generate(fmt, folder, prep):
    hs, vs = FORMATS[fmt]
    dims = [(WIDTH, HEIGHT), ((WIDTH + (1 << hs) - 1) >> hs, (HEIGHT + (1 << vs) - 1) >> vs)]
    dims += [dims[1], dims[0]]
    raw = bytearray()
    for frame in range(FRAMES):
        for plane, (w, h) in enumerate(dims):
            for y in range(h):
                for x in range(w):
                    if plane == 3:
                        value = (17*x + 29*y + 23*frame + 73*((x//5+y//7+frame) % 2)) & 255
                    elif plane == 0:
                        value = (3*x + 5*y + 11*frame + 47*((x+2*frame)//9 % 2)) & 255
                    else:
                        value = (31*plane + 7*x + 13*y + (5+plane)*frame) & 255
                    raw.append(value)
    raw_path = folder / "source.raw"; source = folder / "source.mkv"
    raw_path.write_bytes(raw)
    cmd = [str(prep), "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", fmt,
           "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", "24", "-i", str(raw_path),
           "-an", "-c:v", "ffv1", "-level", "3", "-pix_fmt", fmt, "-threads:v", "1", str(source)]
    r = subprocess.run(cmd, capture_output=True)
    (folder / "prepare.log").write_bytes(r.stdout + r.stderr)
    require(r.returncode == 0, "fixture FFV1 encode failed")
    decode = [str(prep), "-nostdin", "-v", "error", "-i", str(source), "-map", "0:v:0", "-an",
              "-c:v", "rawvideo", "-pix_fmt", fmt, "-threads:v", "1", "-f", "rawvideo", "-"]
    d = subprocess.run(decode, capture_output=True)
    require(d.returncode == 0 and d.stdout == raw, "fixture lossless YUVA roundtrip failed")
    counts = [w*h for w, h in dims]
    return dict(format=fmt, width=WIDTH, height=HEIGHT, frames=FRAMES, plane_counts=counts,
        source_sha256=sha(source), raw_sha256=sha(raw_path), prepare_command=cmd, verify_command=decode), bytes(raw)


def records(text, frame_size):
    tb = None; data = []
    for line in text.splitlines():
        if line.startswith("#tb 0:"): tb = Fraction(line.split(":", 1)[1].strip())
        elif line and not line.startswith("#"):
            fields = [x.strip() for x in line.split(",")]
            require(len(fields) == 6 and int(fields[0]) == 0, "unexpected framemd5 record")
            data.append(dict(dts=int(fields[1]), pts=int(fields[2]), duration=int(fields[3]),
                             size=int(fields[4]), md5=fields[5]))
    require(tb is not None and len(data) == 2*FRAMES, "missing timebase or wrong output count")
    for i, row in enumerate(data):
        require(row["pts"]*tb == Fraction(i,48) and row["dts"] == row["pts"] and
                row["duration"]*tb == Fraction(1,48) and row["size"] == frame_size,
                "wrong frame timestamp/duration/size")
    return dict(time_base=str(tb), frames=data)


def render(binary, source, fmt, folder, label, mask, threads, frame_size):
    chain = "settb=expr=1/120,setpts=N*5,tpad=stop_mode=clone:stop=2,minterpolate=" + \
            "fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:mb_size=16:search_param=32:vsbmc=1:scd=none"
    if mask is not None: chain += f":mci_accel={mask}"
    base = [str(binary), "-nostdin", "-y", "-v", "error", "-threads", "1", "-filter_threads", str(threads),
            "-i", str(source), "-map", "0:v:0", "-an", "-vf", chain, "-frames:v", str(2*FRAMES),
            "-fps_mode", "passthrough", "-enc_time_base", "filter", "-c:v", "rawvideo", "-pix_fmt", fmt,
            "-threads:v", "1"]
    results = []
    for muxer, suffix in (("rawvideo", "raw"), ("framemd5", "framemd5")):
        destination = folder / f"{label}.{suffix}"
        cmd = base + ["-f", muxer, str(destination)]
        p = subprocess.run(cmd, capture_output=True)
        log = folder / f"{label}.{suffix}.log"; log.write_bytes(p.stdout + p.stderr)
        require(p.returncode == 0, f"{label}: {muxer} render failed")
        results.append(dict(command=cmd, returncode=p.returncode, file=destination.name,
                            sha256=sha(destination), log_sha256=sha(log)))
    raw = (folder / f"{label}.raw").read_bytes()
    require(len(raw) == 2*FRAMES*frame_size, f"{label}: wrong decoded output length")
    pts = records((folder / f"{label}.framemd5").read_text(), frame_size)
    require(all(hashlib.md5(raw[i*frame_size:(i+1)*frame_size]).hexdigest() == row["md5"]
                for i, row in enumerate(pts["frames"])), f"{label}: raw/PTS run pixels disagree")
    return raw, dict(label=label, mask=mask, threads=threads, output_frames=2*FRAMES,
                     all_plane_raw_sha256=sha(folder / f"{label}.raw"), frame_records=pts, executions=results)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("stock", "before", "after", "prep"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    require(not a.out.exists(), "use a fresh regression output directory")
    a.out.mkdir(parents=True)
    status = a.out / "regression.json"
    save(status, dict(execution_status="incomplete"))
    binaries = {k: dict(path=str(getattr(a,k).resolve()), sha256=sha(getattr(a,k))) for k in ("stock","before","after","prep")}
    rows = []
    for fmt in FORMATS:
        folder = a.out / fmt; folder.mkdir()
        case, source_raw = generate(fmt, folder, a.prep.resolve())
        size = sum(case["plane_counts"]); alpha_offset = size - WIDTH*HEIGHT
        stock, stock_record = render(a.stock.resolve(), folder/"source.mkv", fmt, folder, "stock", None, 1, size)
        before, before_record = render(a.before.resolve(), folder/"source.mkv", fmt, folder, "before-m51-t4", 51, 4, size)
        require(all(stock[2*f*size:(2*f+1)*size] == source_raw[f*size:(f+1)*size] for f in range(FRAMES)),
                "stock retained instants differ from source")
        alpha_different = []
        nonheld = []
        for f in range(FRAMES):
            index = 2*f+1; offset = index*size
            require(before[offset:offset+alpha_offset] == stock[offset:offset+alpha_offset],
                    "broken control differs outside alpha")
            if before[offset+alpha_offset:offset+size] != stock[offset+alpha_offset:offset+size]:
                alpha_different.append(index)
            if f+1 < FRAMES:
                alpha = stock[offset+alpha_offset:offset+size]
                if all(alpha != stock[k*size+alpha_offset:(k+1)*size] for k in (2*f,2*f+2)):
                    nonheld.append(index)
        require(alpha_different, "unmodified fused control did not expose inserted alpha defect")
        require(nonheld, "stock midpoint alpha is only endpoint holding")
        require(all(before[2*f*size:(2*f+1)*size] == stock[2*f*size:(2*f+1)*size] for f in range(FRAMES)),
                "broken control unexpectedly corrupts retained frames")
        repaired = []
        for mask in (16,51,63):
            for threads in (1,4):
                fixed, record = render(a.after.resolve(), folder/"source.mkv", fmt, folder,
                                       f"after-m{mask}-t{threads}", mask, threads, size)
                require(fixed == stock and record["frame_records"] == stock_record["frame_records"],
                        f"repair differs from stock: {fmt}, mask{mask}, threads{threads}")
                repaired.append(record)
        rows.append(dict(case=case, stock=stock_record, before=before_record,
                         before_inserted_alpha_mismatch_indices=alpha_different,
                         stock_nonheld_midpoint_alpha_indices=nonheld, repaired=repaired))
        print(fmt, "counterfactual exposed", len(alpha_different), "inserted frames; six repairs exact", flush=True)
    require(all(sha(v["path"]) == v["sha256"] for v in binaries.values()), "binary changed during regression")
    save(status, dict(execution_status="complete", binaries=binaries, rows=rows,
                      repaired_comparisons=sum(len(r["repaired"]) for r in rows),
                      script_sha256=sha(__file__), scope="Exact YUVA fallback regression; no performance/quality claim"))


if __name__ == "__main__": main()
