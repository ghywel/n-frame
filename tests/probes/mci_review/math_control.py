#!/usr/bin/env python3
"""Build/run the standalone arithmetic control; save hashes and observed results.

Uses only Python's standard library and a C compiler. No FFmpeg/GPU work.
Example: python3 math_control.py --out math_control_results.json
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cc', default='cc', help='C compiler executable, not a shell command')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    source = here / 'math_control.c'
    patch = here.parent / 'mci_fused' / 'fused.patch'
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise SystemExit(f'compiler not found: {args.cc}')
    # Division must remain division; the explicit counterfactual has its own
    # volatile intermediate to force reciprocal rounding as a separate step.
    flags = ['-std=c11', '-O3', '-fno-fast-math', '-fno-reciprocal-math', '-ffp-contract=off',
             '-Wall', '-Wextra', '-Werror']
    result = dict(execution_status='incomplete', control='fused_finish arithmetic only',
                  source_sha256=sha(source), wrapper_sha256=sha(__file__),
                  reviewed_patch_sha256=sha(patch), compiler=compiler,
                  compiler_version=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                  compiler_flags=flags, platform=platform.platform(), machine=platform.machine())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Invalidate any prior success before compilation/execution.
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    try:
        with tempfile.TemporaryDirectory(prefix='mci-math-control-') as tmp:
            binary = Path(tmp) / 'math-control'
            built = subprocess.run([compiler, *flags, str(source), '-o', str(binary)],
                                   check=True, capture_output=True, text=True)
            result['compiler_diagnostics'] = built.stderr
            result['binary_sha256'] = sha(binary)
            run = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            observed = json.loads(run.stdout)
            if observed.get('execution_status') != 'complete' or not observed.get('direct_division_pass'):
                raise ValueError('control did not report a complete pass')
            if observed.get('boundary_cases') != 3121200 or observed.get('factorization_cases') != 100000:
                raise ValueError('unexpected control counts')
            if observed.get('counterfactual', {}).get('reciprocal_integer') != 0:
                raise ValueError('reciprocal counterfactual did not fail as registered')
            result['observed'] = observed
            result['execution_status'] = 'complete'
    except Exception as exc:
        result['execution_status'] = 'failed'
        result['error'] = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            result['stderr'] = exc.stderr
        args.out.write_text(json.dumps(result, indent=2) + '\n')
        raise
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['observed'], indent=2))


if __name__ == '__main__':
    main()
