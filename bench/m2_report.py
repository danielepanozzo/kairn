#!/usr/bin/env python3
"""m2_report.py: the tables of docs/developer/results/bench-milestone2.md, from the stored runs.

    python3 bench/m2_report.py results/milestone2/bench [--section NAME]

Reads every MACHINE-COMPILER[-SETTING]-LEVEL-rN.json written by kairn-bench-m2 (bench/README.md,
"Milestone 2") and prints the tables of the page: ratios of minimum times within one run, a cell
being the lowest and highest value of a ratio over the runs of a configuration; times in ns; the
checks; the tightness of Horner; the spread of the runs. The compile-time measurements of the
same page are printed by enclosure_costs.py report and rational_cost.py. Standard library only.
"""
import argparse
import glob
import json
import os
import re
import sys

# The columns: (machine, compiler) and their headings.
COLUMNS = [('mac', 'appleclang', 'M3, Apple clang'), ('mac', 'gcc16', 'M3, GCC 16'),
           ('linux', 'gcc', 'Zen 2, GCC 13'), ('linux', 'clang', 'Zen 2, Clang 18')]
NAME = re.compile(r'^(?P<machine>mac|linux)-(?P<compiler>[a-z0-9]+)(?:-(?P<setting>outlined|external))?'
                  r'-(?P<level>O[23])-r(?P<run>\d+)$')


def load(directory):
    """{(machine, compiler, setting, level): [run, ...]}, a run being the parsed JSON with a
    dictionary 'ns' of name -> minimum time."""
    configs = {}
    for path in sorted(glob.glob(os.path.join(directory, '*.json'))):
        m = NAME.match(os.path.basename(path)[:-len('.json')])
        if not m:
            continue
        d = json.load(open(path))
        if d.get('what') != 'kairn-bench-m2':
            continue
        d['ns'] = {r['name']: r['ns_min'] for r in d['results']}
        d['path'] = os.path.basename(path)
        key = (m.group('machine'), m.group('compiler'), m.group('setting') or 'inline', m.group('level'))
        configs.setdefault(key, []).append(d)
    return configs


def fmt_range(lo, hi, digits=2):
    a, b = '%.*f' % (digits, lo), '%.*f' % (digits, hi)
    return a if a == b else '%s to %s' % (a, b)


def fmt_ns(v):
    return '%.3g' % v if v < 100 else '%.0f' % v


def fmt_ns_range(lo, hi):
    a, b = fmt_ns(lo), fmt_ns(hi)
    return a if a == b else '%s to %s' % (a, b)


def values(runs, f):
    out = []
    for r in runs:
        try:
            v = f(r['ns'])
        except (KeyError, ZeroDivisionError):
            continue
        if v is not None:
            out.append(v)
    return out


def cell(configs, machine, compiler, f, setting='inline', kind='ratio'):
    """One cell: the range of f over the runs of each level; the levels merged when they agree
    within 0.05 (ratios) or 5% (times)."""
    per = {}
    for level in ('O2', 'O3'):
        v = values(configs.get((machine, compiler, setting, level), []), f)
        if v:
            per[level] = (min(v), max(v))
    if not per:
        return ''
    fmt = fmt_range if kind == 'ratio' else fmt_ns_range
    if len(per) == 2:
        lo = min(per['O2'][0], per['O3'][0])
        hi = max(per['O2'][1], per['O3'][1])
        close = (hi - lo) <= 0.05 if kind == 'ratio' else hi <= 1.05 * lo
        if close:
            return fmt(lo, hi)
        return '%s (-O2), %s (-O3)' % (fmt(*per['O2']), fmt(*per['O3']))
    level, (lo, hi) = next(iter(per.items()))
    return '%s (-%s)' % (fmt(lo, hi), level)


def ratio(a, b):
    return lambda ns: ns[a] / ns[b]


def time(a):
    return lambda ns: ns[a]


def table(configs, title, rows, kind='ratio', setting='inline'):
    present = [c for c in COLUMNS if any(k[0] == c[0] and k[1] == c[1] for k in configs)]
    print('\n| %s | %s |' % (title, ' | '.join(c[2] for c in present)))
    print('|---' * (len(present) + 1) + '|')
    for label, f in rows:
        cells = [cell(configs, c[0], c[1], f, setting, kind) for c in present]
        if any(cells):
            print('| %s | %s |' % (label, ' | '.join(cells)))


# --- The tables of the page -----------------------------------------------------------------------

def blocks(c, b='m2'):
    rows = []
    for k, floor in (('add_down', 'add'), ('add_up', 'add'), ('sub_down', 'sub'), ('mul_down', 'mul'),
                     ('mul_up', 'mul')):
        rows.append(('`%s` over one `%s` of T, loop' % (k, floor), ratio('%s/tp/%s/op' % (b, k), '%s/tp/%s/plain' % (b, floor))))
    for k, floor, kind in (('add_down', 'add', 'sum'), ('add_up', 'add', 'sum'), ('mul_down', 'mul', 'prod'),
                           ('mul_up', 'mul', 'prod')):
        rows.append(('`%s` over one `%s` of T, chain' % (k, floor), ratio('%s/%s/%s/op' % (b, kind, k), '%s/%s/%s/plain' % (b, kind, floor))))
    table(c, 'Kairn over the plain operation', rows)
    rows = []
    for k in ('add_down', 'add_up', 'sub_down', 'sub_up', 'mul_down', 'mul_up'):
        rows.append(('`%s`, loop: fenv over Kairn' % k, ratio('%s/tp/%s/fenv' % (b, k), '%s/tp/%s/op' % (b, k))))
        rows.append(('`%s`, loop: csr over Kairn' % k, ratio('%s/tp/%s/csr' % (b, k), '%s/tp/%s/op' % (b, k))))
        rows.append(('`%s`, loop: Kairn over fenv_loop' % k, ratio('%s/tp/%s/op' % (b, k), '%s/tp/%s/fenv_loop' % (b, k))))
    for k, kind in (('add_down', 'sum'), ('add_up', 'sum'), ('mul_down', 'prod'), ('mul_up', 'prod')):
        rows.append(('`%s`, chain: fenv over Kairn' % k, ratio('%s/%s/%s/fenv' % (b, kind, k), '%s/%s/%s/op' % (b, kind, k))))
        rows.append(('`%s`, chain: csr over Kairn' % k, ratio('%s/%s/%s/csr' % (b, kind, k), '%s/%s/%s/op' % (b, kind, k))))
        rows.append(('`%s`, chain: Kairn over fenv_loop' % k, ratio('%s/%s/%s/op' % (b, kind, k), '%s/%s/%s/fenv_loop' % (b, kind, k))))
    table(c, 'Against a change of the rounding mode', rows)
    rows = [('`next_up`, loop, over `std::nextafter`', ratio('%s/tp/next_up/op' % b, '%s/tp/next_up/nextafter' % b)),
            ('`next_up`, chain, over `std::nextafter`', ratio('%s/step/next_up/op' % b, '%s/step/next_up/nextafter' % b)),
            ('`next_up`, loop, over one addition', ratio('%s/tp/next_up/op' % b, '%s/tp/add/plain' % b)),
            ('`radd`, loop, over one addition', ratio('%s/tp/radd/op' % b, '%s/tp/add/plain' % b)),
            ('`radd`, chain, over one addition', ratio('%s/sum/radd/op' % b, '%s/sum/add/plain' % b)),
            ('`rmul`, loop, over one product', ratio('%s/tp/rmul/op' % b, '%s/tp/mul/plain' % b)),
            ('`rmul`, chain, over one product', ratio('%s/prod/rmul/op' % b, '%s/prod/mul/plain' % b)),
            ('`two_sum`, loop, over one addition', ratio('%s/tp/two_sum/op' % b, '%s/tp/add/plain' % b)),
            ('`two_prod`, loop, over one product', ratio('%s/tp/two_prod/op' % b, '%s/tp/mul/plain' % b)),
            ('the public block over the generated kernel, `add_down`, loop', ratio('%s/tp/add_down/op' % b, '%s/tp/add_down/kairn' % b)),
            ('the public block over the generated kernel, `mul_down`, loop', ratio('%s/tp/mul_down/op' % b, '%s/tp/mul_down/kairn' % b))]
    table(c, 'The other blocks', rows)
    rows = [(n, time(n)) for n in ('%s/tp/add/plain' % b, '%s/tp/add_down/op' % b, '%s/tp/add_down/fenv' % b,
                                   '%s/tp/add_down/csr' % b, '%s/tp/add_down/fenv_loop' % b, '%s/tp/mul_down/op' % b,
                                   '%s/tp/mul_down/fenv' % b, '%s/sum/add/plain' % b, '%s/sum/add_down/op' % b,
                                   '%s/sum/add_down/fenv' % b, '%s/sum/add_down/csr' % b, '%s/sum/add_down/fenv_loop' % b,
                                   '%s/prod/mul_down/op' % b, '%s/prod/mul_down/fenv' % b)]
    table(c, 'Times (ns)', [('`%s`' % n, f) for n, f in rows], kind='time')


def interval1(c, b='m2'):
    rows = []
    for op, pair in (('add', 'pair_add_1'), ('sub', 'pair_sub_1'), ('mul', 'pair_mul_1')):
        k = 'interval_%s_1' % op
        rows.append(('`%s`, loop, over two plain operations' % k, ratio('%s/tp/%s/op' % (b, k), '%s/tp/%s/plain' % (b, pair))))
    rows.append(('`interval_mul_1`, loop, over the four products rounded to nearest', ratio('%s/tp/interval_mul_1/op' % b, '%s/tp/plain4_mul_1/plain' % b)))
    rows.append(('`interval_add_1`, chain, over two plain additions', ratio('%s/sum/interval_add_1/op' % b, '%s/sum/pair_add_1/plain' % b)))
    rows.append(('`interval_mul_1`, chain, over two plain products', ratio('%s/prod/interval_mul_1/op' % b, '%s/prod/pair_mul_1/plain' % b)))
    rows.append(('`interval_mul_1`, chain, over the four products rounded to nearest', ratio('%s/prod/interval_mul_1/op' % b, '%s/prod/plain4_mul_1/plain' % b)))
    table(c, 'Interval<T, 1> over the floor', rows)
    rows = []
    for op in ('add', 'sub', 'mul'):
        k = 'interval_%s_1' % op
        rows.append(('`%s`, loop: fenv over Kairn' % k, ratio('%s/tp/%s/fenv' % (b, k), '%s/tp/%s/op' % (b, k))))
        rows.append(('`%s`, loop: csr over Kairn' % k, ratio('%s/tp/%s/csr' % (b, k), '%s/tp/%s/op' % (b, k))))
        rows.append(('`%s`, loop: Kairn over fenv_loop' % k, ratio('%s/tp/%s/op' % (b, k), '%s/tp/%s/fenv_loop' % (b, k))))
    for kind, k in (('sum', 'interval_add_1'), ('prod', 'interval_mul_1')):
        rows.append(('`%s`, chain: fenv over Kairn' % k, ratio('%s/%s/%s/fenv' % (b, kind, k), '%s/%s/%s/op' % (b, kind, k))))
        rows.append(('`%s`, chain: csr over Kairn' % k, ratio('%s/%s/%s/csr' % (b, kind, k), '%s/%s/%s/op' % (b, kind, k))))
        rows.append(('`%s`, chain: Kairn over fenv_loop' % k, ratio('%s/%s/%s/op' % (b, kind, k), '%s/%s/%s/fenv_loop' % (b, kind, k))))
    table(c, 'Interval<T, 1> against a change of the rounding mode', rows)
    rows = []
    for op in ('add', 'sub', 'mul'):
        rows.append(('`X %s Y`, loop: interval over ball' % {'add': '+', 'sub': '-', 'mul': '*'}[op],
                     ratio('%s/tp/interval_%s_1/op' % (b, op), '%s/tp/ball_%s_1/op' % (b, op))))
    rows.append(('`S + X`, chain: interval over ball', ratio('%s/sum/interval_add_1/op' % b, '%s/sum/ball_add_1/op' % b)))
    rows.append(('`P * X`, chain: interval over ball', ratio('%s/prod/interval_mul_1/op' % b, '%s/prod/ball_mul_1/op' % b)))
    table(c, 'Interval<T, 1> over Ball<T, 1>', rows)
    rows = [('`-X` over two negations', ratio('%s/tp/interval_neg_1/op' % b, '%s/tp/interval_neg_1/plain' % b)),
            ('`hull` over a min and a max', ratio('%s/tp/interval_hull_1/op' % b, '%s/tp/interval_hull_1/plain' % b)),
            ('`intersection` over a max, a min and a test', ratio('%s/tp/interval_intersection_1/op' % b, '%s/tp/interval_intersection_1/plain' % b)),
            ('`midpoint` and `radius` over (l + h)/2, (h - l)/2', ratio('%s/tp/interval_midrad_1/op' % b, '%s/tp/plain_midrad_1/plain' % b)),
            ('`split` over (l + h)/2, (h - l)/2', ratio('%s/tp/interval_split_1/op' % b, '%s/tp/plain_midrad_1/plain' % b)),
            ('`Ball<T, 1>(X)` over (l + h)/2, (h - l)/2', ratio('%s/tp/interval_to_ball_1/op' % b, '%s/tp/plain_midrad_1/plain' % b)),
            ('`Interval<T, 1>(B)` over c - r, c + r', ratio('%s/tp/ball_to_interval_1/op' % b, '%s/tp/plain_bounds_1/plain' % b))]
    table(c, 'The other functions of Interval<T, 1>, loops', rows)
    names = ['%s/tp/%s/op' % (b, k) for k in ('interval_add_1', 'interval_mul_1', 'interval_neg_1', 'interval_hull_1',
                                               'interval_intersection_1', 'interval_midrad_1', 'interval_split_1',
                                               'interval_to_ball_1', 'ball_to_interval_1', 'ball_add_1', 'ball_mul_1')]
    names += ['%s/tp/interval_add_1/fenv' % b, '%s/tp/interval_mul_1/fenv' % b, '%s/tp/interval_mul_1/csr' % b,
              '%s/tp/interval_add_1/fenv_loop' % b, '%s/tp/interval_mul_1/fenv_loop' % b, '%s/tp/pair_add_1/plain' % b,
              '%s/tp/plain4_mul_1/plain' % b, '%s/sum/interval_add_1/op' % b, '%s/prod/interval_mul_1/op' % b,
              '%s/prod/interval_mul_1/fenv' % b, '%s/prod/interval_mul_1/fenv_loop' % b, '%s/sum/ball_add_1/op' % b,
              '%s/prod/ball_mul_1/op' % b]
    table(c, 'Times (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


def interval2(c, b='m2'):
    rows = []
    for op, sym in (('add', '+'), ('sub', '-'), ('mul', '*')):
        rows.append(('`X %s Y`, loop, over `Expansion<T, 2>` twice' % sym, ratio('%s/tp/interval_%s_2/op' % (b, op), '%s/tp/pair_%s_2/op' % (b, op))))
    rows.append(('`X * Y`, loop, over the four products of `Expansion<T, 2>`', ratio('%s/tp/interval_mul_2/op' % b, '%s/tp/plain4_mul_2/op' % b)))
    rows.append(('`S + X`, chain, over `Expansion<T, 2>` twice', ratio('%s/sum/interval_add_2/op' % b, '%s/sum/pair_add_2/op' % b)))
    rows.append(('`P * X`, chain, over `Expansion<T, 2>` twice', ratio('%s/prod/interval_mul_2/op' % b, '%s/prod/pair_mul_2/op' % b)))
    for op, sym in (('add', '+'), ('sub', '-'), ('mul', '*')):
        rows.append(('`X %s Y`, loop: interval over ball' % sym, ratio('%s/tp/interval_%s_2/op' % (b, op), '%s/tp/ball_%s_2/op' % (b, op))))
    rows.append(('`S + X`, chain: interval over ball', ratio('%s/sum/interval_add_2/op' % b, '%s/sum/ball_add_2/op' % b)))
    rows.append(('`P * X`, chain: interval over ball', ratio('%s/prod/interval_mul_2/op' % b, '%s/prod/ball_mul_2/op' % b)))
    rows.append(('`X * Y`, loop: as called over flattened', ratio('%s/tp/interval_mul_2/op' % b, '%s/tp/interval_mul_2/flat' % b)))
    rows.append(('`P * X`, chain: as called over flattened', ratio('%s/prod/interval_mul_2/op' % b, '%s/prod/interval_mul_2/flat' % b)))
    rows.append(('a call of the same signature, loop: its time over that of `X * Y`',
                 lambda ns: (ns['%s/tp/call_8_4/plain' % b] - ns['%s/tp/call_8_4/kairn' % b]) / ns['%s/tp/interval_mul_2/op' % b]))
    rows.append(('a call of the same signature, chain: its time over that of `P * X`',
                 lambda ns: (ns['%s/prod/call_8_4/plain' % b] - ns['%s/prod/call_8_4/kairn' % b]) / ns['%s/prod/interval_mul_2/op' % b]))
    rows.append(('`X * Y` of two limbs over one limb, loop', ratio('%s/tp/interval_mul_2/op' % b, '%s/tp/interval_mul_1/op' % b)))
    rows.append(('`X + Y` of two limbs over one limb, loop', ratio('%s/tp/interval_add_2/op' % b, '%s/tp/interval_add_1/op' % b)))
    rows.append(('`hull`, loop, over `X + Y` of `Expansion<T, 2>` twice', ratio('%s/tp/interval_hull_2/op' % b, '%s/tp/pair_add_2/op' % b)))
    table(c, 'Interval<T, 2>', rows)
    names = ['%s/tp/%s/op' % (b, k) for k in ('interval_add_2', 'interval_sub_2', 'interval_mul_2', 'interval_hull_2',
                                               'interval_intersection_2', 'pair_add_2', 'pair_mul_2', 'plain4_mul_2',
                                               'ball_add_2', 'ball_mul_2')]
    names += ['%s/tp/interval_mul_2/flat' % b, '%s/sum/interval_add_2/op' % b, '%s/prod/interval_mul_2/op' % b,
              '%s/prod/interval_mul_2/flat' % b, '%s/sum/ball_add_2/op' % b, '%s/prod/ball_mul_2/op' % b,
              '%s/sum/pair_add_2/op' % b, '%s/prod/pair_mul_2/op' % b, '%s/tp/call_8_4/plain' % b,
              '%s/tp/call_8_4/kairn' % b, '%s/prod/call_8_4/plain' % b, '%s/prod/call_8_4/kairn' % b]
    table(c, 'Times (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


def horner(c, b='m2'):
    names = [('Interval<T, 1>', 'horner_i1', 'op'), ('Interval<T, 1>, fenv', 'horner_i1', 'fenv'),
             ('Interval<T, 1>, csr', 'horner_i1', 'csr'), ('Interval<T, 1>, fenv_loop', 'horner_i1', 'fenv_loop'),
             ('Interval<T, 2>', 'horner_i2', 'op'), ('Interval<T, 2>, flattened', 'horner_i2', 'flat'),
             ('Ball<T, 1>', 'horner_b1', 'op'), ('Ball<T, 2>', 'horner_b2', 'op'),
             ('Expansion<T, 2>, a point', 'horner_e2', 'op'), ('T, a point', 'horner_t', 'plain')]
    for kind, what in (('tp', 'independent evaluations'), ('lat', 'dependent evaluations')):
        table(c, 'Horner, %s: ns per evaluation' % what,
              [(label, time('%s/%s/%s/%s' % (b, kind, k, v))) for label, k, v in names], kind='time')
    rows = []
    for kind in ('tp', 'lat'):
        rows += [('%s: `Interval<T, 1>` over `Ball<T, 1>`' % kind, ratio('%s/%s/horner_i1/op' % (b, kind), '%s/%s/horner_b1/op' % (b, kind))),
                 ('%s: `Interval<T, 2>` over `Ball<T, 2>`' % kind, ratio('%s/%s/horner_i2/op' % (b, kind), '%s/%s/horner_b2/op' % (b, kind))),
                 ('%s: `Ball<T, 1>` over T' % kind, ratio('%s/%s/horner_b1/op' % (b, kind), '%s/%s/horner_t/plain' % (b, kind))),
                 ('%s: `Ball<T, 2>` over `Expansion<T, 2>`' % kind, ratio('%s/%s/horner_b2/op' % (b, kind), '%s/%s/horner_e2/op' % (b, kind))),
                 ('%s: `Interval<T, 1>`, fenv over Kairn' % kind, ratio('%s/%s/horner_i1/fenv' % (b, kind), '%s/%s/horner_i1/op' % (b, kind))),
                 ('%s: `Interval<T, 1>`, Kairn over fenv_loop' % kind, ratio('%s/%s/horner_i1/op' % (b, kind), '%s/%s/horner_i1/fenv_loop' % (b, kind)))]
    table(c, 'Horner, ratios', rows)


def ball_additions(c, b='m2'):
    rows = [('`lower_as`, `upper_as`, one limb, over c - r, c + r', ratio('%s/tp/ball_bounds_1/op' % b, '%s/tp/plain_bounds_1/plain' % b)),
            ('`lower_as`, `upper_as`, two limbs, over c0 - r, c0 + r', ratio('%s/tp/ball_bounds_2/op' % b, '%s/tp/plain_bounds_2/plain' % b)),
            ('`from_interval` over (l + h)/2, (h - l)/2', ratio('%s/tp/ball_from_interval_2/op' % b, '%s/tp/plain_midrad_1/plain' % b)),
            ('`Ball<T, 1>(X)` of two limbs over c0, r + abs(c1)', ratio('%s/tp/ball_narrow_2_1/op' % b, '%s/tp/plain_narrow_2_1/plain' % b)),
            ('`half(X)` over `X * 0.5`, one limb, loop', ratio('%s/tp/ball_half_1/op' % b, '%s/tp/ball_scale_half_1/op' % b)),
            ('`half(X)` over `X * 0.5`, two limbs, loop', ratio('%s/tp/ball_half_2/op' % b, '%s/tp/ball_scale_half_2/op' % b)),
            ('`ldexp(X, n)` over `X * 2^n`, one limb, loop', ratio('%s/tp/ball_ldexp_1/op' % b, '%s/tp/ball_scale_pow2_1/op' % b)),
            ('`ldexp(X, n)` over `X * 2^n`, two limbs, loop', ratio('%s/tp/ball_ldexp_2/op' % b, '%s/tp/ball_scale_pow2_2/op' % b)),
            ('`ldexp(X, +-1)` over `X * 2^+-1`, one limb, chain', ratio('%s/prod/ball_ldexp_1/op' % b, '%s/prod/ball_scale_pow2_1/op' % b)),
            ('`ldexp(X, +-1)` over `X * 2^+-1`, two limbs, chain', ratio('%s/prod/ball_ldexp_2/op' % b, '%s/prod/ball_scale_pow2_2/op' % b))]
    table(c, 'The additions to Ball', rows)
    names = ['%s/tp/%s/op' % (b, k) for k in ('ball_bounds_1', 'ball_bounds_2', 'ball_from_interval_2', 'ball_narrow_2_1',
                                               'ball_half_1', 'ball_half_2', 'ball_scale_half_1', 'ball_scale_half_2',
                                               'ball_ldexp_1', 'ball_ldexp_2')]
    names += ['%s/prod/ball_ldexp_2/op' % b, '%s/prod/ball_scale_pow2_2/op' % b]
    table(c, 'Times (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


def rational(c, b='m2'):
    names = [('`rational<Expansion<T, 1>>`, small terms', 'rational_1_small/op'),
             ('`rational<Expansion<T, 1>>`, 64-bit terms', 'rational_1_large/op'),
             ('`rational<Expansion<T, 2>>`, small terms', 'rational_2_small/op'),
             ('`rational<Expansion<T, 2>>`, 64-bit terms', 'rational_2_large/op'),
             ('`is_rational_result`, two limbs, 64-bit terms', 'rational_check_2_large/op'),
             ('`T(num) / T(den)`, for scale', 'divide_large/plain')]
    table(c, 'kairn::rational, ns per call', [(label, time('%s/tp/%s' % (b, n))) for label, n in names], kind='time')


def packed(c):
    rows = []
    for k in ('add_down_1', 'add_up_1', 'mul_down_1', 'mul_up_1', 'next_up', 'interval_add_1', 'interval_mul_1',
              'interval_add_2', 'interval_mul_2', 'ball_add_1', 'ball_mul_1', 'ball_add_2', 'ball_mul_2'):
        rows.append(('`%s`: packed over scalar' % k, ratio('m2p/tp/%s/kairn' % k, 'm2s/tp/%s/kairn' % k)))
    rows += [('`add_down_1`: packed over packed fenv_loop', ratio('m2p/tp/add_down_1/kairn', 'm2p/tp/add_down_1/fenv_loop')),
             ('`mul_down_1`: packed over packed fenv_loop', ratio('m2p/tp/mul_down_1/kairn', 'm2p/tp/mul_down_1/fenv_loop')),
             ('`interval_add_1`: packed over packed fenv_loop', ratio('m2p/tp/interval_add_1/kairn', 'm2p/tp/interval_add_1/fenv_loop')),
             ('`interval_mul_1`: packed over packed fenv_loop', ratio('m2p/tp/interval_mul_1/kairn', 'm2p/tp/interval_mul_1/fenv_loop')),
             ('`interval_add_1`: packed over packed `ball_add_1`', ratio('m2p/tp/interval_add_1/kairn', 'm2p/tp/ball_add_1/kairn')),
             ('`interval_mul_1`: packed over packed `ball_mul_1`', ratio('m2p/tp/interval_mul_1/kairn', 'm2p/tp/ball_mul_1/kairn')),
             ('`interval_add_2`: packed over packed `ball_add_2`', ratio('m2p/tp/interval_add_2/kairn', 'm2p/tp/ball_add_2/kairn')),
             ('`interval_mul_2`: packed over packed `ball_mul_2`', ratio('m2p/tp/interval_mul_2/kairn', 'm2p/tp/ball_mul_2/kairn')),
             ('`add_down_1`: packed over packed plain addition', ratio('m2p/tp/add_down_1/kairn', 'm2p/tp/add/plain')),
             ('`interval_add_1`: packed over packed plain addition', ratio('m2p/tp/interval_add_1/kairn', 'm2p/tp/add/plain'))]
    table(c, 'Packed code (binary64)', rows)
    names = ['m2p/tp/%s/kairn' % k for k in ('add_down_1', 'mul_down_1', 'next_up', 'interval_add_1', 'interval_mul_1',
                                             'interval_add_2', 'interval_mul_2', 'ball_add_2', 'ball_mul_2')]
    names += ['m2p/tp/interval_add_1/fenv_loop', 'm2p/tp/interval_mul_1/fenv_loop', 'm2p/tp/add/plain']
    table(c, 'Packed times (ns per number, interval or ball)', [('`%s`' % n, time(n)) for n in names], kind='time')


def floats(c):
    rows = []
    for k, kind in (('add_down', 'tp'), ('mul_down', 'tp'), ('interval_add_1', 'tp'), ('interval_mul_1', 'tp'),
                    ('interval_add_2', 'tp'), ('interval_mul_2', 'tp'), ('ball_add_2', 'tp'), ('ball_mul_2', 'tp'),
                    ('interval_add_1', 'sum'), ('interval_mul_1', 'prod'), ('horner_i1', 'tp'), ('horner_b1', 'tp'),
                    ('horner_i2', 'tp'), ('horner_b2', 'tp')):
        rows.append(('`%s`, %s' % (k, kind), ratio('m2f/%s/%s/op' % (kind, k), 'm2/%s/%s/op' % (kind, k))))
    rows += [('`add_down`, loop: fenv over Kairn', ratio('m2f/tp/add_down/fenv', 'm2f/tp/add_down/op')),
             ('`interval_mul_1`, loop: fenv over Kairn', ratio('m2f/tp/interval_mul_1/fenv', 'm2f/tp/interval_mul_1/op')),
             ('`interval_mul_1`, loop: Kairn over fenv_loop', ratio('m2f/tp/interval_mul_1/op', 'm2f/tp/interval_mul_1/fenv_loop')),
             ('`interval_mul_1`, loop: interval over ball', ratio('m2f/tp/interval_mul_1/op', 'm2f/tp/ball_mul_1/op'))]
    table(c, 'float limbs: float over double, and float ratios', rows)


def settings(c):
    rows = []
    for k in ('interval_add_1', 'interval_mul_1', 'interval_add_2', 'interval_mul_2', 'ball_add_2', 'ball_mul_2'):
        for kind in ('tp',):
            rows.append(('`%s`, loop' % k, None, '%s/%s/%s/op' % ('m2', kind, k)))
    rows += [('`interval_add_1`, chain', None, 'm2/sum/interval_add_1/op'),
             ('`interval_mul_1`, chain', None, 'm2/prod/interval_mul_1/op'),
             ('`interval_mul_2`, chain', None, 'm2/prod/interval_mul_2/op'),
             ('Horner, `Interval<T, 1>`', None, 'm2/tp/horner_i1/op'),
             ('Horner, `Interval<T, 2>`', None, 'm2/tp/horner_i2/op'),
             ('Horner, `Ball<T, 2>`', None, 'm2/tp/horner_b2/op'),
             ('control: the kernel `interval_mul_1`, loop', None, 'm2/tp/interval_mul_1/kairn')]
    for setting in ('outlined', 'external'):
        present = [k for k in c if k[2] == setting]
        if not present:
            continue
        print('\n%s over inline (each a ratio of the minima over the runs of each program)' % setting)
        cols = [col for col in COLUMNS if any(k[0] == col[0] and k[1] == col[1] for k in present)]
        print('| Function | %s |' % ' | '.join(col[2] for col in cols))
        print('|---' * (len(cols) + 1) + '|')
        for label, _, name in rows:
            cells = []
            for col in cols:
                parts = []
                for level in ('O2', 'O3'):
                    a = values(c.get((col[0], col[1], setting, level), []), time(name))
                    b = values(c.get((col[0], col[1], 'inline', level), []), time(name))
                    if a and b:
                        parts.append('%.2f (-%s)' % (min(a) / min(b), level))
                cells.append(', '.join(parts))
            print('| %s | %s |' % (label, ' | '.join(cells)))


def checks(c):
    print('\n| Configuration | Runs | Functions checked, failed | Wide sample: compared, equal, zero sign, below P one wider, failed | Load average (1 min) at start, end |')
    print('|---|---:|---|---|---|')
    for key in sorted(c):
        runs = c[key]
        r = runs[0]
        wide = r['checks']['wide']
        comp = sum(w['compared'] for w in wide)
        eq = sum(w['equal'] for w in wide)
        zs = sum(w['zero_sign'] for w in wide)
        bp = sum(w['below_p_wider'] for w in wide)
        fl = sum(w['failed'] for w in wide)
        loads = ', '.join('%.1f, %.1f' % (x['load_average']['start'][0], x['load_average']['end'][0]) for x in runs)
        print('| %s | %d | %d, %d | %d, %d, %d, %d, %d | %s |' % ('-'.join(key), len(runs), r['checks']['compared'],
                                                                r['checks']['failed'], comp, eq, zs, bp, fl, loads))


def discrimination(c):
    """For each rounding-mode prop: of how many values, how many differ from rounding to nearest."""
    totals = {}
    for key, runs in c.items():
        for d in runs[0]['checks']['discrimination']:
            t = totals.setdefault(d['name'], [0, 0, set()])
            t[0] = d['values']
            t[1] = d['differ_from_nearest']
            t[2].add('-'.join(key))
    print('\n| Prop | Values compared with Kairn | Of them not the result rounded to nearest | Configurations |')
    print('|---|---:|---:|---:|')
    for name in sorted(totals):
        v, dif, cfgs = totals[name]
        print('| `%s` | %d | %d | %d |' % (name, v, dif, len(cfgs)))


def spread(c):
    print('\n| Configuration | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |')
    print('|---|---:|---|---|')
    for key in sorted(c):
        runs = c[key]
        if len(runs) < 2:
            continue
        names = set(runs[0]['ns'])
        for r in runs[1:]:
            names &= set(r['ns'])
        sp = []
        for n in names:
            v = [r['ns'][n] for r in runs]
            sp.append((max(v) / min(v) - 1, n))
        sp.sort()
        med = sp[len(sp) // 2][0]
        p90 = sp[int(0.9 * (len(sp) - 1))][0]
        print('| %s | %d | %.1f%%, %.1f%%, %.1f%% | `%s` |' % ('-'.join(key), len(runs), 100 * med, 100 * p90, 100 * sp[-1][0], sp[-1][1]))


def tightness(c):
    # The tightness does not depend on timing: one run of one configuration, and a check that every
    # configuration agrees with it.
    first = None
    agree = 0
    for key in sorted(c):
        t = c[key][0]['tightness']
        if first is None:
            first = (key, t)
        elif json.dumps(t, sort_keys=True) == json.dumps(first[1], sort_keys=True):
            agree += 1
        else:
            print('\nnote: the tightness of %s differs from that of %s' % ('-'.join(key), '-'.join(first[0])))
    if first is None:
        return
    print('\nTightness (from %s; %d other configurations give the same numbers):' % ('-'.join(first[0]), agree))
    print('\n| Limbs | Regime | Type | Width over the reference: median, 90th percentile, max | Median width | Not contained |')
    print('|---|---|---|---|---|---:|')
    for e in first[1]:
        print('| %s | %s | `%s` | %.3g, %.3g, %.3g (of %s) | %.3g | %d |' % (
            'double' if e['bits'] == 64 else 'float', e['regime'], e['type'], e['ratio_median'], e['ratio_p90'],
            e['ratio_max'], e['ratio_of'], e['width_median'], e['not_contained']))


def configurations(c):
    print('\n| Configuration | CPU | Compiler | Flags | Rounding-mode props | Runs | Date, commit |')
    print('|---|---|---|---|---|---:|---|')
    for key in sorted(c):
        r = c[key][0]
        print('| %s | %s; %s | %s | `%s` | `%s` | %d | %s, `%s` |' % (
            '-'.join(key), r['machine']['cpu'], r['machine']['pinning'], r['compiler'], r['flags'],
            r['fenv_flags'].replace(r['flags'], '...'), len(c[key]), r['date'], r['commit']))


SECTIONS = {'configurations': configurations, 'checks': checks, 'discrimination': discrimination,
            'spread': spread, 'blocks': blocks, 'interval1': interval1, 'interval2': interval2,
            'horner': horner, 'tightness': tightness, 'ball': ball_additions, 'rational': rational,
            'packed': packed, 'float': floats, 'settings': settings}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('dir')
    ap.add_argument('--section', choices=sorted(SECTIONS), action='append')
    a = ap.parse_args()
    c = load(a.dir)
    inline = {k: v for k, v in c.items() if k[2] == 'inline'}
    for name in a.section or list(SECTIONS):
        print('\n## %s' % name)
        SECTIONS[name](c if name == 'settings' else inline)
    return 0


if __name__ == '__main__':
    sys.exit(main())
