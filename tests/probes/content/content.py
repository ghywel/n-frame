#!/usr/bin/env python3
"""THE TIERS BY CONTENT TYPE: live action against 2D animation against CG animation (Local, 2026-10-23; the owner's ask
after the switch audit: "make sure the cadence graphs, with the scaled tiers, are running the best switches for the film
and television content type ... both real filmed footage and cartoon / anime needs testing separately").

    content.py draw    <out>                  the seeded draw of clips from the NAS pool (read-only), screened
    content.py shaders <out>                  the tiers regenerated (asserted identical to the shipped files) and variants
    content.py run     <out>                  realbench.sh for every clip and shader (decimate-and-reconstruct, 3 s windows)
    content.py score   <out>                  per class: synthesized-frame PSNR and SSIM, deltas against High

WHAT IS MEASURED. realbench.sh's decimate-and-reconstruct: each 3 s window at its native rate, every second frame dropped
and rebuilt, scored on the rebuilt frames only (PSNR Y and SSIM; SSIM is the one to trust where they disagree,
realanalyze.py's docstring). Motion doubles under decimation, so absolute figures are harder than playback's; the
comparison between shaders is what this is for.

THE CLIPS, not chosen by either party: titles drawn by a fixed seed from five classes of the pool, a file drawn within the
title, eight times drawn uniformly over 10-90 percent of it, and screen.sh keeping the first two windows with full
per-frame motion (an animation window held on twos flatters every mode, so it is refused). Rates 23.976, 24 and 25 are
taken (25 with realbench's RATE/HALFRATE); others are skipped and counted.
  live action: film (5 titles), television (3); 2D animation: anime and 2D hand-drawn film (5), western 2D cartoon (4);
  CG animation (3). Two windows per file.

THE SHADERS (gen_variational.py, the High tier's own command; every tier regenerated must equal its shipped file byte for
byte or the run refuses):
  low, standard, high                     the three Cadence tiers as shipped (1080p graphs; the -4k twins are their scaling)
  high-<switch>                           High without one switch: coherence, energy, qzero, global (with ALIAS_PRIOR,
                                          which needs it), cut, adopt
  high+bars                               BAR_REDECIDE + BAR_BASIN;   high+trust  TRUST_GATE (LOCAL_CENTRE does not
                                          compose with ALIAS_PRIOR: its anchor is gone, so it is no High candidate)
  low+anim, standard+anim, high+anim      PROP_DISAGREE 1.5 -> 0.75 (the 2026-09-04 animation file's one change: a texel
                                          whose propagated consensus disagrees with its refine blends sooner)
  high2                                  High again: the M5's run-to-run control
  linear                                  the blend

PRE-REGISTERED (Local, before any clip was drawn or rendered):
  1. Live action: the tiers rank High >= Standard >= Low on SSIM, the steps small (under 0.1 dB PSNR each); every
     ablation and addition within +-0.1 dB of High on the class mean; +anim a wash (within 0.1), as on 09-04.
  2. 2D animation: +anim gains on every tier, at least +0.3 dB PSNR on the class mean with SSIM not lower (09-04: +1.5 on
     one anime segment against the old propagated base); the alias switches (energy, qzero, adopt, lattice) neutral
     within 0.1 on flat-filled content.
  3. CG animation behaves as live action.
  THE DECISION RULE (a recommendation to the owner, never applied here): a switch that moves one class's mean by +0.1 dB
  or more with SSIM not lower, and costs no other class more than 0.05, is a default candidate; one that helps one class
  and costs another more than 0.1 is a content-toggle candidate (his rule of 09-21: toggles only where content types
  disagree). The noise floor is high2 against high; nothing inside it counts.
"""
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TESTS = REPO / 'tests'
POOL = Path('/Volumes/share')
FF = os.environ.get('FFMPEG', str(Path.home() / 'np-build/ffmpeg/ffmpeg'))
FP = os.environ.get('FFPROBE', str(Path.home() / 'np-build/ffmpeg/ffprobe'))
SEED = 20261023
VIDEO = ('.mkv', '.mp4', '.m4v', '.avi')

CLASSES = {
    'film': ('live', 5, 'Movies', ['007 James Bond', 'Austin Powers', 'Back To The Future', 'Beethoven', 'Bridget Jones',
              'Bruce Almighty', 'Cornetto', 'Cruel Intentions', 'Die Hard', 'DragonHeart', 'Dune', 'Gladiator',
              'Harry Potter', 'High School Musical', 'Home Alone', 'Homeward Bound', 'Independence Day', 'Indiana Jones',
              'Jason Bourne', 'Jumanji', 'Jurassic Park', 'Kevin Smith', 'Kick-Ass', 'Legally Blonde', 'Marvel Films',
              'Mean Girls', 'Meet the Parents', 'Men In Black', 'Miss Congeniality', 'Mission Impossible', 'Narnia',
              'Night at the Museum', 'Pacific Rim', 'Pirates of the Caribbean', 'Pitch Perfect', 'Star Wars', 'Tarantino',
              'Terminator', 'The Dark Knight', 'The Hunger Games', 'The Lord of the Rings', 'The Matrix',
              'The Princess Diaries', 'Total Recall', 'Transformers']),
    'tv': ('live', 3, 'Shows', ['Band of Brothers', 'Black Adder', 'Black Books', 'Brass Eye', 'Bunheads', 'Firefly',
            'Friends', 'Gilmore girls', 'IT Crowd', 'Impractical Jokers', 'Miranda', 'Red Dwarf', 'Saturday Night Live UK',
            'Stargate']),
    'anime': ('2d', 5, None, ['Anime/' + t for t in ['Accel World', 'Attack On Titan', 'Death Note',
               'Fate Stay Night - Unlimited Blade Works', 'Fate Stay Night Heavens Feel', 'Fate Zero', 'Free',
               'Fruits Basket', 'Fullmetal Alchemist Brotherhood', 'Re Zero', 'Sword Art Online', 'Violet Evergarden']]
              + ['Movies/Studio Ghibli']),
    'cartoon': ('2d', 4, 'Shows', ['Avatar - The Last Airbender', 'Bluey', 'Family Guy', 'Futurama',
                 'My Little Pony, Friendship is Magic', 'Rick and Morty', 'Solar Opposites', 'South Park',
                 'The Legend of Korra', 'The Lion Guard']),
    'cg': ('cg', 3, 'Movies', ['Despicable Me', 'How To Train Your Dragon', 'Kung Fu Panda', 'Madagascar', 'Megamind',
            'Minions', 'Shrek', 'Sing', 'The Lego Movie', 'The Secret Life of Pets', 'Trolls']),
}
EXCLUDE = re.compile(r'Earwig', re.I)            # Ghibli's one CG film, out of the 2D class
RATES = {'24000/1001': ('24000/1001', '12000/1001'), '24/1': ('24', '12'), '25/1': ('25', '25/2')}

HIGH_ENV = dict(GLOBAL_SEED='1', QZERO_MOIRE='1', COHERENCE_GATE='1', COARSE_ENERGY='1', COARSE_ENERGY_WS='8',
                COARSE_ENERGY_WE='1', ALIAS_PRIOR='1', ALIAS_CARRY='1', OUTLINE_ADOPT='1', PRINT_LATTICE='1',
                CUT_MOTION='1', PRUNE='2')
OFF = ['PHASE_FETCH', 'PHASE_FETCH_E', 'PHASE_GATE', 'BAR_REDECIDE', 'BAR_KEEP', 'BAR_BASIN', 'STICKY_CACHE', 'EDGE_PROP',
       'LOCAL_CENTRE', 'TRUST_GATE', 'ZERO_SEED']
SHIPPED = {'low': 'bidirectional-interpolation-variational-propagated-cut',
           'standard': 'bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-cut',
           'high': 'bidirectional-interpolation-variational-propagated-global-cage-energy-carry-adopt-lattice-cut'}
TIER_ENV = {'low': dict(CUT_MOTION='1', PRUNE='2'),
            'standard': {k: v for k, v in HIGH_ENV.items() if k != 'PRINT_LATTICE'},
            'high': HIGH_ENV}
ANIM_OLD, ANIM_NEW = 'const float PROP_DISAGREE     = 1.5;', 'const float PROP_DISAGREE     = 0.75;'


def variants():
    v = {t: (e, False) for t, e in TIER_ENV.items()}
    drop = {'coherence': ['COHERENCE_GATE'], 'energy': ['COARSE_ENERGY', 'COARSE_ENERGY_WS', 'COARSE_ENERGY_WE'],
            'qzero': ['QZERO_MOIRE'], 'global': ['GLOBAL_SEED', 'ALIAS_PRIOR'], 'cut': ['CUT_MOTION'],
            'adopt': ['OUTLINE_ADOPT']}
    for name, keys in drop.items():
        v['high-' + name] = ({k: x for k, x in HIGH_ENV.items() if k not in keys}, False)
    v['high+bars'] = (dict(HIGH_ENV, BAR_REDECIDE='1', BAR_BASIN='1'), False)
    v['high+trust'] = (dict(HIGH_ENV, TRUST_GATE='1'), False)
    for t in TIER_ENV:
        v[t + '+anim'] = (TIER_ENV[t], True)
    return v


def generate(env, out):
    e = os.environ.copy()
    for k in OFF + list(HIGH_ENV):
        e.pop(k, None)
    e.update({k: '0' for k in OFF}, PYTHONDONTWRITEBYTECODE='1', **env)
    r = subprocess.run([sys.executable, str(TESTS / 'gen_variational.py'), '0,0,8,4', '0.3', '0.08', str(out), '0',
                        '0,0,2,0', 'bidirectional-interpolation-propagated.glsl'], env=e, cwd=REPO, capture_output=True,
                       text=True)
    if r.returncode:
        raise SystemExit(f'generation failed for {out.name}: {r.stderr[-400:]}')


def shaders(out):
    d = out / 'shaders'; d.mkdir(parents=True, exist_ok=True); man = {}
    for name, (env, anim) in variants().items():
        p = d / f'{name}.glsl'; generate(env, p)
        if name in SHIPPED and p.read_bytes() != (REPO / 'shaders' / f'{SHIPPED[name]}.glsl').read_bytes():
            raise SystemExit(f'{name} does not reproduce the shipped file')
        if anim:
            t = p.read_text(); n = t.count(ANIM_OLD)
            if n < 1 or ANIM_NEW in t:
                raise SystemExit(f'{name}: PROP_DISAGREE found {n} times')
            p.write_text(t.replace(ANIM_OLD, ANIM_NEW))
        man[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (d / 'high2.glsl').write_bytes((d / 'high.glsl').read_bytes()); man['high2'] = man['high']
    (out / 'shaders.json').write_text(json.dumps(man, indent=1)); print(f'{len(man)} shaders; tiers reproduce exactly')


def probe(f):
    r = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=r_frame_rate,width,height,field_order:format=duration', '-of', 'json', str(f)],
                       capture_output=True, text=True)
    j = json.loads(r.stdout or '{}'); s = (j.get('streams') or [{}])[0]
    return s.get('r_frame_rate'), s.get('field_order', 'unknown'), float(j.get('format', {}).get('duration', 0) or 0), \
        s.get('width'), s.get('height')


def files(title_dir):
    return sorted(p for p in title_dir.rglob('*') if p.suffix.lower() in VIDEO and not p.name.startswith('.')
                  and not EXCLUDE.search(p.name))


def screen(f, times, rate):
    env = dict(os.environ, FFMPEG=FF, RATE=rate)
    r = subprocess.run(['bash', str(TESTS / 'screen.sh'), str(f)] + [f'{t:.1f}' for t in times], env=env,
                       capture_output=True, text=True)
    good = []
    for line in r.stdout.splitlines():
        m = re.match(r'\s*([0-9.]+)\s+\d+/\d+\s+[0-9.]+\s+GOOD', line)
        if m:
            good.append(float(m.group(1)))
    return good, r.stdout


def draw(out):
    rng = random.Random(SEED); clips = []; log = []
    for cls, (kind, k, root, titles) in CLASSES.items():
        order = titles[:]; rng.shuffle(order); got = 0
        for title in order:
            if got >= k:
                break
            tdir = POOL / (title if root is None else f'{root}/{title}')
            fs = files(tdir)
            if not fs:
                log.append(f'{cls} {title}: no video files'); continue
            ok = False
            for f in rng.sample(fs, min(3, len(fs))):
                rate, field, dur, w, h = probe(f)
                if rate not in RATES or field not in ('progressive', 'unknown') or dur < 60:
                    log.append(f'{cls} {title}: skip {f.name} ({rate}, {field}, {dur:.0f} s)'); continue
                times = sorted(rng.uniform(.1 * dur, .9 * dur) for _ in range(8))
                good, txt = screen(f, times, RATES[rate][0])
                log.append(f'{cls} {title}: {f.name} {rate} {w}x{h}: {len(good)} of 8 windows full-motion')
                if len(good) >= 2:
                    clips.append({'id': f'{cls}{got + 1}', 'class': cls, 'kind': kind, 'title': title, 'file': str(f),
                                  'rate': rate, 'size': f'{w}x{h}', 'segs': [round(x, 1) for x in good[:2]]})
                    got += 1; ok = True; break
            if not ok:
                log.append(f'{cls} {title}: no file with two full-motion windows')
        log.append(f'== {cls}: {got} of {k}')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'clips.json').write_text(json.dumps(clips, indent=1)); (out / 'draw.log').write_text('\n'.join(log) + '\n')
    print('\n'.join(log))


def run(out):
    clips = json.loads((out / 'clips.json').read_text()); names = list(json.loads((out / 'shaders.json').read_text()))
    for c in clips:
        root = out / 'real' / c['id']; root.mkdir(parents=True, exist_ok=True)
        rate, half = RATES[c['rate']]
        env = dict(os.environ, FFMPEG=FF, FFPROBE=FP, OUTROOT=str(root), RATE=rate, HALFRATE=half,
                   MVK_CONFIG_USE_METAL_ARGUMENT_BUFFERS='0', MVK_CONFIG_MAX_ACTIVE_METAL_COMMAND_BUFFERS_PER_QUEUE='1')
        for name in ['linear'] + names:
            what = 'linear' if name == 'linear' else str(out / 'shaders' / f'{name}.glsl')
            r = subprocess.run(['bash', str(TESTS / 'realbench.sh'), c['file'], name, what] + [str(s) for s in c['segs']],
                               env=env, capture_output=True, text=True)
            (root / f'run_{name}.log').write_text(r.stdout + r.stderr)
            if 'FAILED' in r.stdout or r.returncode:
                print(f"{c['id']} {name}: FAILED", flush=True)
        print(f"{c['id']} done", flush=True)


def read(p, pat):
    d = {}
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(pat, line)
            if m:
                d[int(m.group(1))] = float('inf') if m.group(2) == 'inf' else float(m.group(2))
    return d


def score(out):
    clips = json.loads((out / 'clips.json').read_text()); names = ['linear'] + list(json.loads((out / 'shaders.json').read_text()))
    pats = {'psnr': r'n:(\d+).*?psnr_y:([0-9.]+|inf)', 'ssim': r'n:(\d+).*?\sAll:([0-9.]+)'}
    per = {}; bad = []
    for c in clips:
        root = out / 'real' / c['id']
        for s in c['segs']:
            for name in names:
                for m, pat in pats.items():
                    d = read(root / f'{m}_{name}_{s:g}.log', pat) or read(root / f'{m}_{name}_{s}.log', pat)
                    syn = [v for n, v in d.items() if n % 2 == 0 and v != float('inf')]
                    thru = [v for n, v in d.items() if n % 2 == 1]
                    if m == 'psnr' and thru and min(thru) < 45:
                        bad.append(f"{c['id']} {s} {name}: passthrough {min(thru):.1f} dB")
                    if syn:
                        per.setdefault((c['class'], c['id'], s), {}).setdefault(name, {})[m] = statistics.mean(syn)
    groups = {'live action (film+tv)': ('film', 'tv'), 'film': ('film',), 'tv': ('tv',),
              '2D animation (anime+cartoon)': ('anime', 'cartoon'), 'anime': ('anime',), 'cartoon': ('cartoon',),
              'CG animation': ('cg',)}
    res = {}
    for g, cls in groups.items():
        segs = [v for k, v in per.items() if k[0] in cls and all(n in v and 'ssim' in v[n] for n in names)]
        if not segs:
            continue
        row = {}
        for n in names:
            row[n] = {m: statistics.mean(s[n][m] for s in segs) for m in pats}
            row[n]['d_psnr'] = row[n]['psnr'] - row['high']['psnr'] if 'high' in row else 0
        hi = {m: statistics.mean(s['high'][m] for s in segs) for m in pats}
        for n in names:
            row[n]['d_psnr'] = row[n]['psnr'] - hi['psnr']; row[n]['d_ssim'] = row[n]['ssim'] - hi['ssim']
            row[n]['segments_up'] = sum(s[n]['psnr'] > s['high']['psnr'] + .05 for s in segs)
            row[n]['segments_down'] = sum(s[n]['psnr'] < s['high']['psnr'] - .05 for s in segs)
        res[g] = {'segments': len(segs), 'rows': row}
        print(f"\n== {g}: {len(segs)} segments (deltas against High; up/down: segments beyond 0.05 dB)")
        for n in names:
            r = row[n]
            print(f"  {n:16s} PSNR {r['psnr']:6.2f} ({r['d_psnr']:+.3f})  SSIM {r['ssim']:.4f} ({r['d_ssim']:+.4f})  "
                  f"up {r['segments_up']:2d} down {r['segments_down']:2d}")
    (out / 'scores.json').write_text(json.dumps({'groups': res, 'passthrough_alarms': bad,
        'per_segment': {f'{k[1]}@{k[2]}': v for k, v in per.items()}}, indent=1))
    print('\npassthrough alarms:', len(bad)); [print(' ', b) for b in bad[:10]]


if __name__ == '__main__':
    cmd, out = sys.argv[1], Path(sys.argv[2]).expanduser().resolve()
    {'draw': draw, 'shaders': shaders, 'run': run, 'score': score}[cmd](out)
