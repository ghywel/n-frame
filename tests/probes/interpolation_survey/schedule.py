#!/usr/bin/env python3
"""Exact constant-rate schedules, with source and output timelines starting at 0.

If S/T = a/b in lowest terms, output n lies at source coordinate n*a/b.
Its fractional phase repeats after b outputs, spanning a source intervals.
One output per cycle is an exact source timestamp: endpoint rate T/b;
the remaining output rate is T*(b-1)/b. Cycles are half-open, [0, b/T).

Endpoint reuse means exact timestamp coincidence, not visually equal pixels,
nearest-frame selection or a claim about an implementation's handling of them.
"Synthesized" means outputs requiring a non-endpoint temporal sample. A blend
or duplicate does not become genuine motion interpolation by meeting this count.
Inference caching, flow reuse, model calls, startup/tail behavior, scene cuts,
decode/render overhead and cost are deliberately excluded.

Usage:
  python3 schedule.py --check --out schedule.json  # five registered cases
  python3 schedule.py 24000/1001 60 --check        # one custom case

--check independently enumerates output timestamps on a common integer clock
until the first positive exact source endpoint, then asserts the closed forms.
It also checks explicit expected values for all five registered cases.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


CASES = (('24', '48'), ('24', '60'),
         ('24000/1001', '48000/1001'),
         ('24000/1001', '60000/1001'), ('24000/1001', '60'))
MAX_CHECK_OUTPUTS = 1_000_000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rate(text):
    value = Fraction(text)
    require(value > 0, 'rates must be positive')
    return value


def schedule(source, target):
    ratio = source / target
    a, b = ratio.numerator, ratio.denominator
    phases = [str(Fraction((n*a) % b, b)) for n in range(b)] if b <= 20 else None
    return dict(source_rate=str(source), target_rate=str(target),
                source_coordinate_step=str(ratio), phase_period_outputs=b,
                source_intervals_per_cycle=a, cycle_duration_seconds=str(b/target),
                shared_endpoint_rate=str(target/b), synthesized_output_rate=str(target*(b-1)/b),
                shared_endpoint_fraction=str(Fraction(1,b)),
                synthesized_output_fraction=str(Fraction(b-1,b)),
                phase_cycle=phases, phase_cycle_omitted=b > 20)


def enumerate_cycle(source, target):
    # Construct the input/output clocks directly; do not use reduced S/T or b.
    ticks_per_second = math.lcm(source.numerator, target.numerator)
    source_step = ticks_per_second // source.numerator * source.denominator
    output_step = ticks_per_second // target.numerator * target.denominator
    phases, tick = [], 0
    while True:
        phases.append(Fraction(tick % source_step, source_step))
        tick += output_step
        if tick % source_step == 0:
            return phases, Fraction(tick, ticks_per_second), tick // source_step
        require(len(phases) < MAX_CHECK_OUTPUTS,
                f'cycle enumeration exceeds {MAX_CHECK_OUTPUTS} outputs; omit --check for this rate')


def verify(source, target, row):
    phases, duration, source_intervals = enumerate_cycle(source, target)
    endpoints = sum(phase == 0 for phase in phases)
    require(len(phases) == row['phase_period_outputs'], 'phase period differs')
    require(len(set(phases)) == len(phases), 'phase repeats before registered cycle boundary')
    require(endpoints == 1, 'wrong exact endpoint count per half-open cycle')
    require(source_intervals == row['source_intervals_per_cycle'], 'source advance differs')
    require(duration == Fraction(row['cycle_duration_seconds']), 'cycle duration differs')
    require(Fraction(endpoints, 1)/duration == Fraction(row['shared_endpoint_rate']), 'endpoint rate differs')
    require(Fraction(len(phases)-endpoints, 1)/duration == Fraction(row['synthesized_output_rate']),
            'synthesized rate differs')
    require(Fraction(row['shared_endpoint_rate'])+Fraction(row['synthesized_output_rate']) == target,
            'rates do not sum to target')
    if row['phase_cycle'] is not None:
        require([str(p) for p in phases] == row['phase_cycle'], 'listed phase order differs')
    return dict(method='independent common-integer-clock enumeration',
                enumerated_outputs=len(phases), exact_endpoints=endpoints,
                nonendpoint_outputs=len(phases)-endpoints, passed=True)


def self_checks():
    expected = [
        (2, '24', '24', ['0', '1/2']),
        (5, '12', '48', ['0', '2/5', '4/5', '1/5', '3/5']),
        (2, '24000/1001', '24000/1001', ['0', '1/2']),
        (5, '12000/1001', '48000/1001', ['0', '2/5', '4/5', '1/5', '3/5']),
        (1001, '60/1001', '60000/1001', None),
    ]
    for (s, t), (period, shared, synthesized, phases) in zip(CASES, expected):
        source, target = rate(s), rate(t)
        row = schedule(source, target)
        require((row['phase_period_outputs'], row['shared_endpoint_rate'],
                 row['synthesized_output_rate'], row['phase_cycle']) ==
                (period, shared, synthesized, phases), f'explicit expected schedule failed: {s}->{t}')
        verify(source, target, row)
    # Boundary cases ensure the method is not assuming doubling or upconversion.
    for s, t in [('24', '24'), ('60', '24'), ('17/13', '29/19')]:
        source, target = rate(s), rate(t)
        verify(source, target, schedule(source, target))
    for bad in ['0', '-24']:
        try:
            rate(bad)
        except ValueError:
            continue
        raise ValueError('nonpositive rate silently accepted')
    return dict(registered_expected_cases=5, additional_cycle_cases=3,
                nonpositive_rate_refusals=2, passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', nargs='?', help='positive exact source rate, e.g. 24000/1001')
    parser.add_argument('target', nargs='?', help='positive exact target rate, e.g. 60')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    require((args.source is None) == (args.target is None), 'supply both source and target rates')
    pairs = [(args.source, args.target)] if args.source is not None else CASES
    report = dict(schema=1, arithmetic='exact rational; no floating point',
                  assumptions=['constant rates', 'source and output timestamp origins both zero',
                               'half-open phase cycle', 'endpoint reuse requires exact timestamp coincidence'],
                  exclusions=['inference caching and flow reuse', 'model calls and execution cost',
                              'startup and finite-clip tails', 'scene-cut and quality fallbacks',
                              'decoder, transfer and display cost'],
                  synthesized_definition='non-endpoint temporal samples required by the schedule; not proof of motion synthesis',
                  generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), cases=[])
    if args.check:
        report['self_checks'] = self_checks()
    for s, t in pairs:
        source, target = rate(s), rate(t)
        row = schedule(source, target)
        if args.check:
            row['verification'] = verify(source, target, row)
        report['cases'].append(row)
    text = json.dumps(report, indent=2)+'\n'
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
