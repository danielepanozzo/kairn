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


def fmt_range(lo, hi, digits=None):
    if digits is None:   # two decimals below 10, one below 100, none above
        digits = 2 if hi < 10 else 1 if hi < 100 else 0
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
    within 0.05 or 3%, whichever is larger (ratios), or within 5% (times)."""
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
        close = (hi - lo) <= max(0.05, 0.03 * lo) if kind == 'ratio' else hi <= 1.05 * lo
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
    table(c, 'Times of the blocks (ns)', [('`%s`' % n, f) for n, f in rows], kind='time')


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
    table(c, 'Times of Interval<T, 1> (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


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
    table(c, 'Times of Interval<T, 2> (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


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
    table(c, 'Times of the additions to Ball (ns)', [('`%s`' % n, time(n)) for n in names], kind='time')


def rational(c, b='m2'):
    names = [('`rational<Expansion<T, 1>>`, small terms', 'rational_1_small/op'),
             ('`rational<Expansion<T, 1>>`, 64-bit terms', 'rational_1_large/op'),
             ('`rational<Expansion<T, 2>>`, small terms', 'rational_2_small/op'),
             ('`rational<Expansion<T, 2>>`, 64-bit terms', 'rational_2_large/op'),
             ('`is_rational_result`, two limbs, 64-bit terms', 'rational_check_2_large/op'),
             ('`T(num) / T(den)`, for scale', 'divide_large/plain')]
    table(c, 'kairn::rational, ns per call', [(label, time('%s/tp/%s' % (b, n))) for label, n in names], kind='time')


COMPILE = re.compile(r'^compile-(?P<machine>mac|linux)-(?P<compiler>[a-z0-9]+)-(?P<kind>mixed|interval2|interval1|compare|contains|setops)'
                     r'(?:-(?P<size>\d+))?(?:-r(?P<run>\d+))?$')


def compile_tables(directory):
    """compile-MACHINE-COMPILER-KIND[-SIZE][-rN].json, written by enclosure_costs.py compile: the
    compile time, peak memory, object size and run time of the units in each setting. The first
    file of a configuration (no -rN) is the one of the timed compilations (three of each unit, one of
    the largest); the -rN files are later compilations and runs of the same units, for the spread of
    the run times. The compile time is the compiler's processor time (user and system), which on
    an idle core is its wall time within 1%, and which a process left on the same core by a stopped
    compilation does not lengthen; the wall times stay in the files."""
    data = {}
    for path in sorted(glob.glob(os.path.join(directory, 'compile-*.json'))):
        m = COMPILE.match(os.path.basename(path)[:-len('.json')])
        if not m:
            continue
        d = json.load(open(path))
        key = (m.group('machine'), m.group('compiler'), m.group('kind'))
        first = m.group('run') is None
        for r in d['results']:
            if r['kind'] != 'unit':
                continue
            cell = data.setdefault(key, {}).setdefault((r['operations'], r['setting'], r['config']),
                                                       {'cpu': [], 'peak': [], 'obj': None, 'run': [], 'run_first': [],
                                                        'timeout': None})
            if first:
                cell['cpu'] += [c for c, s in zip(r['cpu'], r['status']) if s == 0]
                # The peak of a compilation stopped at its timeout is that of the driver alone.
                cell['peak'] += [m for m, s in zip(r['peak_mb'], r['status']) if s == 0]
                if not cell['cpu'] and -1 in r['status']:
                    cell['timeout'] = d.get('timeout')
                cell['obj'] = r.get('object_bytes')
                if 'run' in r:
                    cell['run_first'].append(r['run']['ns_per_op_min'])
            elif 'run' in r:
                cell['run'].append(r['run']['ns_per_op_min'])
    for kind in ('mixed', 'interval2', 'interval1', 'compare', 'contains', 'setops'):
        present = [col for col in COLUMNS if (col[0], col[1], kind) in data]
        if not present:
            continue
        rows = sorted({(n, s) for col in present for (n, s, _) in data[(col[0], col[1], kind)]},
                      key=lambda x: (x[0], ['inline', 'outlined', 'external', 'calls'].index(x[1])))

        def emit(title, f):
            print('\n| %s | %s |' % (title, ' | '.join(col[2] for col in present)))
            print('|---' * (len(present) + 1) + '|')
            for n, s in rows:
                cells = []
                for col in present:
                    t = data[(col[0], col[1], kind)]
                    parts = [f(t[(n, s, lvl)], col[0]) if (n, s, lvl) in t else '' for lvl in ('O2', 'O3')]
                    cells.append('' if not any(parts) else '; '.join(p or '–' for p in parts))
                if any(cells):
                    print('| %d, %s | %s |' % (n, s, ' | '.join(cells)))

        def med(v):
            return sorted(v)[len(v) // 2] if v else None

        def seconds(c, machine=None):
            w = med(c['cpu'])
            if w is None and c['timeout']:
                return 'stopped at %d' % c['timeout']
            return '' if w is None else ('%.2f' % w if w < 10 else '%.1f' % w if w < 100 else '%.0f' % w)

        def runs(c, machine):
            # On Linux the first runs were made on the cores of the timed compilations, on the
            # busier socket, and are left out (the table after shows them); on the Mac, which has
            # no affinity, every run counts.
            v = c['run'] + (c['run_first'] if machine == 'mac' else [])
            if not v:
                return ''
            return fmt_ns_range(min(v), max(v)) + (' (one run)' if len(v) == 1 else '')

        emit('%s: compile time, s of processor time (-O2; -O3)' % kind, seconds)
        emit('%s: peak memory, MB (-O2; -O3)' % kind, lambda c, m: '%d' % round(med(c['peak'])) if c['peak'] else '')
        emit('%s: object, KB (-O2; -O3)' % kind, lambda c, m: '%d' % round(c['obj'] / 1024) if c['obj'] else '')
        emit('%s: run time of the unit, ns per operation (-O2; -O3)' % kind, runs)
        emit('%s: run time of the unit, first runs, ns per operation (-O2; -O3)' % kind,
             lambda c, m: fmt_ns_range(min(c['run_first']), max(c['run_first'])) if c['run_first'] else '')


def modes(directory):
    """modes-MACHINE-COMPILER-LEVEL.json, written by kairn-bench-m2-modes: ns per element of a loop of
    additions and of products under each rounding mode."""
    runs = {}
    for path in sorted(glob.glob(os.path.join(directory, 'modes-*.json'))):
        m = re.match(r'^modes-(mac|linux)-([a-z0-9]+)-(O[23])\.json$', os.path.basename(path))
        if m:
            runs[(m.group(1), m.group(2), m.group(3))] = json.load(open(path))
    if not runs:
        return
    keys = sorted(runs)
    print('\n| Loop under the mode, ns per element | %s |' % ' | '.join(
        '%s -%s' % (next(c[2] for c in COLUMNS if c[0] == k[0] and c[1] == k[1]), k[2]) for k in keys))
    print('|---' * (len(keys) + 1) + '|')
    for op in ('add', 'mul'):
        for mode in ('nearest', 'downward', 'upward', 'towardzero'):
            cells = []
            for k in keys:
                r = next((x for x in runs[k]['results'] if x['op'] == op and x['mode'] == mode), None)
                cells.append(fmt_ns(r['ns_min']) if r else '')
            print('| `%s`, %s | %s |' % (op, mode, ' | '.join(cells)))


def rational_compile(directory):
    """rational-compile-MACHINE-COMPILER.json, written by rational_cost.py compile."""
    files = sorted(glob.glob(os.path.join(directory, 'rational-compile-*.json')))
    if not files:
        return
    print('\n| Compiler | Include only, s | Constants | `Expansion<double, 1>`: s, ms per constant (check 0; check 1) | `Expansion<double, 2>`: s, ms per constant (check 0; check 1) |')
    print('|---|---:|---:|---|---|')
    for path in files:
        d = json.load(open(path))
        name = os.path.basename(path)[len('rational-compile-'):-len('.json')]
        counts = sorted({r['constants'] for r in d['rows']})
        for n in counts:
            cells = []
            for typ in ('e1', 'e2'):
                parts = []
                for check in (0, 1):
                    r = next((x for x in d['rows'] if x['type'] == typ and x['constants'] == n and x['check'] == check), None)
                    parts.append('%.2f, %.2f' % (r['median_s'], r['per_constant_ms']) if r else '')
                cells.append('; '.join(parts))
            print('| %s (%s) | %.2f | %d | %s | %s |' % (name, d.get('version', d['compiler']), d['include_only_s'], n,
                                                    cells[0], cells[1]))


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
        cols = [col for col in COLUMNS if any(k[0] == col[0] and k[1] == col[1] for k in present)]
        print('\n| %s over inline | %s |' % (setting.capitalize(), ' | '.join(col[2] for col in cols)))
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
    print('\n| Checks of | Runs | Functions checked, failed | Wide sample: compared, equal, zero of the other sign, below P one number wider, failed; not the result rounded to nearest | Load average (1 min) at start, end of each run |')
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
        rn = sum(w['differ_from_nearest'] for w in wide)
        loads = '; '.join('%.1f, %.1f' % (x['load_average']['start'][0], x['load_average']['end'][0]) for x in runs)
        print('| %s | %d | %d, %d | %d, %d, %d, %d, %d; %d | %s |' % ('-'.join(key), len(runs), r['checks']['compared'],
                                                                    r['checks']['failed'], comp, eq, zs, bp, fl, rn, loads))


def discrimination(c):
    """For each rounding-mode prop: of how many values, how many differ from rounding to nearest."""
    totals = {}
    for key, runs in c.items():
        for d in runs[0]['checks']['discrimination']:
            t = totals.setdefault(d['name'], [0, 0, set()])
            t[0] = d['values']
            t[1] = d['differ_from_nearest']
            t[2].add('-'.join(key))
    # Summed by limb type and variant: the props are deterministic, so one configuration's counts
    # are every configuration's (each configuration checked them all before timing).
    groups = {}
    for name, (v, dif, cfgs) in totals.items():
        backend, _, _, variant = name.split('/')
        g = groups.setdefault((backend, variant), [0, 0, 0, len(cfgs)])
        g[0] += 1
        g[1] += v
        g[2] += dif
    print('\n| Props of | Variant | Props | Values compared with Kairn, bit for bit | Of them not the result rounded to nearest | Configurations |')
    print('|---|---|---:|---:|---:|---:|')
    for (backend, variant), (n, v, dif, cfgs) in sorted(groups.items()):
        print('| %s | `%s` | %d | %d | %d | %d |' % ({'m2': 'double', 'm2f': 'float'}.get(backend, backend), variant, n, v,
                                                  dif, cfgs))


def spread(c):
    print('\n| Spread of | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |')
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


def runs(c):
    """Each run against the fastest of its configuration: the median and 90th percentile over the
    functions of its minimum over the configuration's least minimum, the median over the functions
    of its own median over minimum (the spread within the run), and the load average."""
    print('\n| Run | Over the fastest run: median, 90th percentile | Median over minimum within the run (median function) | Load average (1, 5 min) at start, end |')
    print('|---|---|---|---|')
    for key in sorted(c):
        rs = c[key]
        names = set(rs[0]['ns'])
        for r in rs[1:]:
            names &= set(r['ns'])
        best = {n: min(r['ns'][n] for r in rs) for n in names}
        for r in rs:
            rel = sorted(r['ns'][n] / best[n] for n in names)
            within = sorted(x['ns_median'] / x['ns_min'] for x in r['results'])
            la = r['load_average']
            print('| `%s` | %.3f, %.3f | %.3f | %.1f %.1f, %.1f %.1f |' % (
                r['path'], rel[len(rel) // 2], rel[int(0.9 * (len(rel) - 1))], within[len(within) // 2],
                la['start'][0], la['start'][1], la['end'][0], la['end'][1]))


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
            e['ratio_max'], e['ratio_of'].replace('|', '\\|'), e['width_median'], e['not_contained']))


def configurations(c):
    print('\n| Configuration | CPU | Compiler | Flags | Rounding-mode props | Runs | Date, commit |')
    print('|---|---|---|---|---|---:|---|')
    for key in sorted(c):
        r = c[key][0]
        print('| %s | %s; %s | %s | `%s` | `%s` | %d | %s, `%s` |' % (
            '-'.join(key), r['machine']['cpu'], r['machine']['pinning'], r['compiler'], r['flags'],
            r['fenv_flags'].replace(r['flags'], '...'), len(c[key]), r['date'], r['commit']))


SECTIONS = {'configurations': configurations, 'checks': checks, 'discrimination': discrimination,
            'spread': spread, 'runs': runs, 'blocks': blocks, 'interval1': interval1, 'interval2': interval2,
            'horner': horner, 'tightness': tightness, 'ball': ball_additions, 'rational': rational,
            'packed': packed, 'float': floats, 'settings': settings}


# --- The second part ------------------------------------------------------------------------------
# ITEM-MACHINE-COMPILER-LEVEL-rN.json (ITEM soa, enc, bisect) and checks-MACHINE-COMPILER-LEVEL-cK-rN.json,
# written by kairn-bench-m2 with a filter (bench/README.md, "Milestone 2"); the cells as above.

NAME2 = re.compile(r'^(?P<item>soa|enc|bisect)-(?P<machine>mac|linux)-(?P<compiler>[a-z0-9]+)-(?P<level>O[23])'
                   r'-r(?P<run>\d+)$')
CHECKS2 = re.compile(r'^checks-(?P<machine>mac|linux)-(?P<compiler>[a-z0-9]+)-(?P<level>O[23])-c(?P<c>[01])'
                     r'-r(?P<run>\d+)$')


def load2(directory):
    """{item: {(machine, compiler, 'inline', level): [run, ...]}}, and for checks the runs of the ratio
    of each function's minimum with KAIRN_CHECKS 1 to its minimum with 0, the two programs of one run
    index paired."""
    items, pairs = {}, {}
    for path in sorted(glob.glob(os.path.join(directory, '*.json'))):
        stem = os.path.basename(path)[:-len('.json')]
        m, k = NAME2.match(stem), CHECKS2.match(stem)
        if not m and not k:
            continue
        d = json.load(open(path))
        d['ns'] = {r['name']: r['ns_min'] for r in d['results']}
        d['path'] = os.path.basename(path)
        if m:
            key = (m.group('machine'), m.group('compiler'), 'inline', m.group('level'))
            items.setdefault(m.group('item'), {}).setdefault(key, []).append(d)
        else:
            key = (k.group('machine'), k.group('compiler'), 'inline', k.group('level'))
            pairs.setdefault(key, {}).setdefault(k.group('run'), {})[int(k.group('c'))] = d
    checks = {}
    raw = {}
    for key, runs_ in pairs.items():
        for run, both in sorted(runs_.items()):
            if 0 in both and 1 in both:
                ns = {n: both[1]['ns'][n] / both[0]['ns'][n] for n in both[0]['ns'] if n in both[1]['ns']}
                checks.setdefault(key, []).append({'ns': ns, 'pair': (both[0], both[1])})
                raw.setdefault(key, []).extend([both[0], both[1]])
    items['checks'] = checks
    items['checks_raw'] = raw
    return items


def soa_tables(c):
    rows = []
    for b, t in (('m2v', 'double'), ('m2vf', 'float')):
        for k, size in (('tp', 'L1'), ('mem', 'memory')):
            p = '%s/%s/' % (b, k)
            rows += [('`x + y`, %s, %s' % (t, size), ratio(p + 'add22/packed', p + 'add22/op')),
                     ('`x * y`, %s, %s' % (t, size), ratio(p + 'mul22/packed', p + 'mul22/op')),
                     ('`x * a`, %s, %s' % (t, size), ratio(p + 'mul21/packed', p + 'mul21/op')),
                     ('dot, W sums, over the same in scalar code, %s, %s' % (t, size), ratio(p + 'dotw/packed', p + 'dotw/op')),
                     ('dot, W sums, over one sum in scalar code, %s, %s' % (t, size), ratio(p + 'dotw/packed', p + 'dot22/op')),
                     ('`x + a * b`, two passes, %s, %s' % (t, size), ratio(p + 'mix/packed', p + 'mix/op')),
                     ('`x + E2(a) * b`, %s, %s' % (t, size), ratio(p + 'mixp/packed', p + 'mixp/op')),
                     ('`x + E2(a) * b` packed, one pass, over `x + a * b` scalar, %s, %s' % (t, size),
                      ratio(p + 'mixp/packed', p + 'mix/op')),
                     ('copy, %s, %s' % (t, size), ratio(p + 'copy/packed', p + 'copy/op'))]
    table(c, 'Packed over the scalar loop', rows)
    rows = []
    for b, b1, t in (('m2v', 'm2v1', 'double'), ('m2vf', 'm2vf1', 'float')):
        for k, size in (('tp', 'L1'), ('mem', 'memory')):
            p, q = '%s/%s/' % (b, k), '%s/%s/' % (b1, k)
            rows += [('`x + y`, %s, %s' % (t, size), ratio(q + 'add22/packed', p + 'add22/op')),
                     ('`x * y`, %s, %s' % (t, size), ratio(q + 'mul22/packed', p + 'mul22/op')),
                     ('`x * a`, %s, %s' % (t, size), ratio(q + 'mul21/packed', p + 'mul21/op')),
                     ('dot, %s, %s' % (t, size), ratio(q + 'dotw/packed', p + 'dot22/op'))]
    table(c, 'Packed of one lane over the scalar loop', rows)
    rows = []
    for b, t in (('m2v', 'double'), ('m2vf', 'float')):
        p = '%s/tp/' % b
        rows += [('`x + y`, raw pointers, %s' % t, ratio(p + 'add22/op', p + 'add22/kairn')),
                 ('`x + y`, view and proxy, %s' % t, ratio(p + 'add22/view', p + 'add22/kairn')),
                 ('`x + y`, array of Expansion, %s' % t, ratio(p + 'add22/aos', p + 'add22/kairn')),
                 ('`x * y`, raw pointers, %s' % t, ratio(p + 'mul22/op', p + 'mul22/kairn')),
                 ('`x * y`, view and proxy, %s' % t, ratio(p + 'mul22/view', p + 'mul22/kairn')),
                 ('`x * y`, array of Expansion, %s' % t, ratio(p + 'mul22/aos', p + 'mul22/kairn')),
                 ('`x * a`, raw pointers, %s' % t, ratio(p + 'mul21/op', p + 'mul21/kairn')),
                 ('`x * a`, view and proxy, %s' % t, ratio(p + 'mul21/view', p + 'mul21/kairn')),
                 ('copy, raw pointers, %s' % t, ratio(p + 'copy/op', p + 'copy/kairn')),
                 ('copy, view and proxy, %s' % t, ratio(p + 'copy/view', p + 'copy/kairn')),
                 ('copy, packed, %s' % t, ratio(p + 'copy/packed', p + 'copy/kairn'))]
    table(c, 'The interfaces over the kernel on the limbs, L1', rows)
    rows = []
    for b, t in (('m2v', 'double'), ('m2vf', 'float')):
        for k, size in (('tp', 'L1'), ('mem', 'memory')):
            p = '%s/%s/' % (b, k)
            rows += [('`x + y` scalar over one `+` of T, %s, %s' % (t, size), ratio(p + 'add22/op', p + 'add11/plain')),
                     ('`x + y` packed over one `+` of T, %s, %s' % (t, size), ratio(p + 'add22/packed', p + 'add11/plain')),
                     ('`x * y` scalar over one `*` of T, %s, %s' % (t, size), ratio(p + 'mul22/op', p + 'mul11/plain')),
                     ('`x * y` packed over one `*` of T, %s, %s' % (t, size), ratio(p + 'mul22/packed', p + 'mul11/plain')),
                     ('dot, packed, over the dot of T, %s, %s' % (t, size), ratio(p + 'dotw/packed', p + 'dot11/plain'))]
    table(c, 'Two limbs over plain T', rows)
    rows = []
    for b, t in (('m2v', 'double'), ('m2vf', 'float')):
        for k, v in (('add11', 'plain'), ('copy', 'kairn'), ('add22', 'op'), ('add22', 'packed'), ('mul22', 'op'),
                     ('mul22', 'packed'), ('dotw', 'packed')):
            rows.append(('`%s/%s`, %s' % (k, v, t), ratio('%s/mem/%s/%s' % (b, k, v), '%s/tp/%s/%s' % (b, k, v))))
    table(c, 'Beyond the last-level cache over L1', rows)
    names = []
    for b in ('m2v', 'm2vf'):
        for k in ('tp', 'mem'):
            names += ['%s/%s/%s' % (b, k, n) for n in ('add11/plain', 'add22/op', 'add22/packed', 'mul22/op', 'mul22/packed',
                                                         'mul21/op', 'mul21/packed', 'dot22/op', 'dotw/op', 'dotw/packed',
                                                         'mix/op', 'mix/packed', 'mixp/packed', 'copy/kairn')]
    table(c, 'Times of Packed and the containers (ns per element)', [('`%s`' % n, time(n)) for n in names], kind='time')


ENC_TYPES = [('i1', '`Interval<T, 1>`'), ('i2', '`Interval<T, 2>`'), ('b1', '`Ball<T, 1>`'), ('b2', '`Ball<T, 2>`')]
ENC_QUESTIONS = [('empty', '`is_empty()`'), ('whole', '`is_whole()`'), ('pos', '`certainly_positive()`'),
                 ('zero', '`certainly_zero()`'), ('contains_t', '`contains(t)`'), ('contains_set', '`contains(Y)`'),
                 ('less', '`less`'), ('less_equal', '`less_equal`'), ('equal', '`equal`'), ('member', '`member(t, X)`')]


def enc_tables(c, b='m2e'):
    for tag, tname in ENC_TYPES:
        rows = [(label, time('%s/tp/%s_%s/op' % (b, tag, op))) for op, label in ENC_QUESTIONS]
        if tag[0] == 'i':
            rows += [('`ieee1788::equal`', time('%s/tp/%s_rel_equal/op' % (b, tag))),
                     ('`ieee1788::interior`', time('%s/tp/%s_rel_interior/op' % (b, tag))),
                     ('`ieee1788::disjoint`', time('%s/tp/%s_rel_disjoint/op' % (b, tag)))]
        table(c, 'Predicates and comparisons of %s, ns per operation%s' % (tname, '' if b == 'm2e' else ' (float)'), rows,
              kind='time')
    rows = []
    for tag in ('i1', 'b1'):
        tname = dict(ENC_TYPES)[tag]
        for op, label in ENC_QUESTIONS:
            rows.append(('%s, %s' % (label, tname), ratio('%s/tp/%s_%s/op' % (b, tag, op), '%s/tp/%s_%s/plain' % (b, tag, op))))
        if tag == 'i1':
            for op in ('rel_equal', 'rel_interior', 'rel_disjoint'):
                rows.append(('`ieee1788::%s`, %s' % (op[4:], tname), ratio('%s/tp/i1_%s/op' % (b, op), '%s/tp/i1_%s/plain' % (b, op))))
    table(c, 'The questions over the same in plain T%s' % ('' if b == 'm2e' else ' (float)'), rows)
    rows = []
    for op, label in ENC_QUESTIONS[4:] + [('hull', '`hull`'), ('split', '`split()`')]:
        rows += [('%s, `Ball<T, 1>` over `Interval<T, 1>`' % label, ratio('%s/tp/b1_%s/op' % (b, op), '%s/tp/i1_%s/op' % (b, op))),
                 ('%s, `Ball<T, 2>` over `Interval<T, 2>`' % label, ratio('%s/tp/b2_%s/op' % (b, op), '%s/tp/i2_%s/op' % (b, op))),
                 ('%s, `Interval<T, 2>` over `Interval<T, 1>`' % label, ratio('%s/tp/i2_%s/op' % (b, op), '%s/tp/i1_%s/op' % (b, op))),
                 ('%s, `Ball<T, 2>` over `Ball<T, 1>`' % label, ratio('%s/tp/b2_%s/op' % (b, op), '%s/tp/b1_%s/op' % (b, op)))]
    table(c, 'Ball over interval, two limbs over one%s' % ('' if b == 'm2e' else ' (float)'), rows)
    for tag, tname in ENC_TYPES:
        rows = [('`hull`', time('%s/tp/%s_hull/op' % (b, tag))), ('`intersection`', time('%s/tp/%s_intersection/op' % (b, tag))),
                ('`split()`', time('%s/tp/%s_split/op' % (b, tag))),
                ('`%s(X)`' % ('Ball<T, k>' if tag[0] == 'i' else 'Interval<T, k>'), time('%s/tp/%s_convert/op' % (b, tag)))]
        if tag[0] == 'i':
            rows += [('`midpoint()`', time('%s/tp/%s_midpoint/op' % (b, tag))), ('`radius()`', time('%s/tp/%s_radius/op' % (b, tag)))]
        rows += [('`midpoint()` and `radius()`', time('%s/tp/%s_midrad2/op' % (b, tag))), ('`mid_rad()`', time('%s/tp/%s_midrad/op' % (b, tag))),
                 ('chain of `hull`', time('%s/step/%s_hull/op' % (b, tag))),
                 ('chain of `intersection`', time('%s/step/%s_intersection/op' % (b, tag))),
                 ('chain of `split().left`', time('%s/step/%s_split/op' % (b, tag))),
                 ('chain of the conversion there and back', time('%s/step/%s_convert/op' % (b, tag)))]
        table(c, 'Set operations of %s, ns%s' % (tname, '' if b == 'm2e' else ' (float)'), rows, kind='time')
    rows = []
    for tag, tname in ENC_TYPES[:2]:
        rows += [('%s: `midpoint()` over `mid_rad()`' % tname, ratio('%s/tp/%s_midpoint/op' % (b, tag), '%s/tp/%s_midrad/op' % (b, tag))),
                 ('%s: `radius()` over `mid_rad()`' % tname, ratio('%s/tp/%s_radius/op' % (b, tag), '%s/tp/%s_midrad/op' % (b, tag))),
                 ('%s: both over `mid_rad()`' % tname, ratio('%s/tp/%s_midrad2/op' % (b, tag), '%s/tp/%s_midrad/op' % (b, tag))),
                 ('%s: `mid_rad()` over the kernel' % tname, ratio('%s/tp/%s_midrad/op' % (b, tag), '%s/tp/%s_midrad/kairn' % (b, tag))),
                 ('%s: `midpoint()` over the kernel writing the midpoint only' % tname,
                  ratio('%s/tp/%s_midpoint/op' % (b, tag), '%s/tp/%s_midpoint/kairn' % (b, tag)))]
    for tag, tname in ENC_TYPES[2:]:
        rows.append(('%s: both over `mid_rad()`' % tname, ratio('%s/tp/%s_midrad2/op' % (b, tag), '%s/tp/%s_midrad/op' % (b, tag))))
    table(c, 'midpoint() and radius() against mid_rad()%s' % ('' if b == 'm2e' else ' (float)'), rows)
    p = 'm2' if b == 'm2e' else 'm2f'
    rows = [('`hull`, `Interval<T, 1>`, over a min and a max', ratio('%s/tp/i1_hull/op' % b, '%s/tp/i1_hull/plain' % b)),
            ('`intersection`, `Interval<T, 1>`, over a max, a min and a test', ratio('%s/tp/i1_intersection/op' % b, '%s/tp/i1_intersection/plain' % b)),
            ('`split()`, `Interval<T, 1>`, over (l + h)/2, (h - l)/2', ratio('%s/tp/i1_split/op' % b, '%s/tp/plain_midrad_1/plain' % p)),
            ('`mid_rad()`, `Interval<T, 1>`, over (l + h)/2, (h - l)/2', ratio('%s/tp/i1_midrad/op' % b, '%s/tp/plain_midrad_1/plain' % p)),
            ('`Ball<T, 1>(X)` over (l + h)/2, (h - l)/2', ratio('%s/tp/i1_convert/op' % b, '%s/tp/plain_midrad_1/plain' % p)),
            ('`hull`, `Ball<T, 1>`, over the plain hull of c - r, c + r', ratio('%s/tp/b1_hull/op' % b, '%s/tp/b1_phull/plain' % b)),
            ('`intersection`, `Ball<T, 1>`, over the plain intersection', ratio('%s/tp/b1_intersection/op' % b, '%s/tp/b1_pinter/plain' % b)),
            ('`split()`, `Ball<T, 1>`, over c -+ r/2, r/2', ratio('%s/tp/b1_split/op' % b, '%s/tp/b1_psplit/plain' % b)),
            ('`Interval<T, 1>(B)` over c - r, c + r', ratio('%s/tp/b1_convert/op' % b, '%s/tp/plain_bounds_1/plain' % p))]
    for tag, tname in ENC_TYPES:
        for op, label in (('hull', '`hull`'), ('split', '`split()`'), ('convert', 'the conversion')):
            rows.append(('%s, %s, over the kernel' % (label, tname), ratio('%s/tp/%s_%s/op' % (b, tag, op), '%s/tp/%s_%s/kairn' % (b, tag, op))))
            rows.append(('chain of %s, %s, over the kernel' % (label, tname), ratio('%s/step/%s_%s/op' % (b, tag, op), '%s/step/%s_%s/kairn' % (b, tag, op))))
    table(c, 'Set operations over the plain forms and the kernels%s' % ('' if b == 'm2e' else ' (float)'), rows)


def enc_overhead(c, b='m2e'):
    """For each configuration, the public function over its kernel on the limbs, over every function
    of the loops that has both: the median and the largest, and which."""
    present = [col for col in COLUMNS if any(k[0] == col[0] and k[1] == col[1] for k in c)]
    print('\n| The public function over the kernel, every loop of %s | %s |' % (b, ' | '.join(col[2] for col in present)))
    print('|---' * (len(present) + 1) + '|')
    for level in ('O2', 'O3'):
        cells = []
        for col in present:
            runs_ = c.get((col[0], col[1], 'inline', level), [])
            if not runs_:
                cells.append('')
                continue
            names = [n for n in runs_[0]['ns'] if n.startswith(b + '/tp/') and n.endswith('/op')
                     and n[:-3] + '/kairn' in runs_[0]['ns']]
            best = {n: min(r['ns'][n] for r in runs_) / min(r['ns'][n[:-3] + '/kairn'] for r in runs_) for n in names}
            v = sorted(best.values())
            worst = max(best, key=best.get)
            cells.append('%.2f, %.2f (`%s`)' % (v[len(v) // 2], v[-1], worst.split('/')[2]))
        print('| -%s: median, largest | %s |' % (level, ' | '.join(cells)))


def float_enc(c):
    rows = []
    for tag, tname in ENC_TYPES:
        for op in ('less', 'contains_t', 'hull', 'split', 'convert'):
            rows.append(('`%s`, %s' % (op, tname), ratio('m2ef/tp/%s_%s/op' % (tag, op), 'm2e/tp/%s_%s/op' % (tag, op))))
    table(c, 'The enclosure interface, float over double', rows)


BISECT_TYPES = [('i1', 'Interval<double, 1>'), ('i2', 'Interval<double, 2>'), ('b1', 'Ball<double, 1>'), ('b2', 'Ball<double, 2>')]


def bisect_tables(c):
    rows = []
    for w, wl in (('w6', '1e-6'), ('w0', '0')):
        for tag, tname in BISECT_TYPES:
            rows.append(('`%s`, width %s' % (tname, wl), lambda ns, n='m2r/run/bisect_%s_%s/op' % (tag, w): ns[n] / 1000))
    table(c, 'Bisection: time to solution, microseconds', rows, kind='time')
    rows = []
    for w, wl in (('w6', '1e-6'), ('w0', '0')):
        for tag, tname in BISECT_TYPES:
            rows.append(('`%s` over `Ball<double, 1>`, width %s' % (tname, wl),
                         ratio('m2r/run/bisect_%s_%s/op' % (tag, w), 'm2r/run/bisect_b1_%s/op' % w)))
    table(c, 'Bisection: time to solution over that of Ball<double, 1>', rows)
    # The counts do not depend on the compiler: one run's, and a check that every run agrees.
    found, agree, differ = None, 0, []
    for key in sorted(c):
        for r in c[key]:
            if found is None:
                found = r['bisection']
            elif json.dumps(r['bisection'], sort_keys=True) == json.dumps(found, sort_keys=True):
                agree += 1
            else:
                differ.append(r['path'])
    if found is None:
        return
    evals = {}
    print('\nBisection counts (one run; %d other runs give the same%s):' % (agree, '; DIFFERENT: ' + ', '.join(differ) if differ else ''))
    print('\n| Bisection: what each type found | Width | Evaluations | Parts kept | Not narrowed by split() | Zeros | Radius of the zeros |')
    print('|---|---|---:|---:|---:|---:|---|')
    for e in found:
        print('| `%s` | %s | %d | %d | %d | %d | %.3g to %.3g |' % (e['type'], e['width'], e['evaluations'], e['kept'], e['stalled'],
                                                              e['zeros'], e['radius_min'], e['radius_max']))
        evals[(e['type'], float(e['width']))] = e['evaluations']
    rows = []
    for w, wl, wj in (('w6', '1e-6', '1e-06'), ('w0', '0', '0')):
        for tag, tname in BISECT_TYPES:
            n = evals.get((tname, float(wj)))
            if n:
                rows.append(('`%s`, width %s' % (tname, wl), lambda ns, k='m2r/run/bisect_%s_%s/op' % (tag, w), n=n: ns[k] / n))
    table(c, 'Bisection: ns per evaluation of p', rows, kind='time')
    rows = [('`self_test()`', lambda ns: ns['m2r/run/self_test/op'] / 1000),
            ('the checks of the environment and the flags, both limb types', lambda ns: ns['m2r/run/self_test_limb/op'] / 1000),
            ('the generated kernels on their fixed operands', lambda ns: ns['m2r/run/self_test_kernels/op'] / 1000)]
    table(c, 'self_test(), microseconds per call', rows, kind='time')


def checks_tables(c):
    rows = []
    for k, label in (('tp/interval_add_1', '`X + Y`, `Interval<T, 1>`, loop'), ('tp/interval_mul_1', '`X * Y`, `Interval<T, 1>`, loop'),
                     ('tp/interval_add_2', '`X + Y`, `Interval<T, 2>`, loop'), ('tp/interval_mul_2', '`X * Y`, `Interval<T, 2>`, loop'),
                     ('sum/interval_add_1', '`S + X`, `Interval<T, 1>`, chain'), ('prod/interval_mul_1', '`P * X`, `Interval<T, 1>`, chain'),
                     ('sum/interval_add_2', '`S + X`, `Interval<T, 2>`, chain'), ('prod/interval_mul_2', '`P * X`, `Interval<T, 2>`, chain'),
                     ('tp/interval_hull_1', '`hull`, `Interval<T, 1>`, loop'), ('tp/interval_split_1', '`split()`, `Interval<T, 1>`, loop'),
                     ('tp/horner_i1', 'Horner, `Interval<T, 1>`'), ('tp/horner_i2', 'Horner, `Interval<T, 2>`')):
        rows.append((label, time('m2/%s/op' % k)))
    for tag, tname in ENC_TYPES:
        for op, label in (('less', '`less`'), ('contains_t', '`contains(t)`'), ('pos', '`certainly_positive()`'),
                          ('hull', '`hull`'), ('split', '`split()`'), ('convert', 'the conversion')):
            rows.append(('%s, %s' % (label, tname), time('m2e/tp/%s_%s/op' % (tag, op))))
    rows += [('control: the kernel `interval_mul_1`, loop', time('m2/tp/interval_mul_1/kairn')),
             ('control: the kernel `ball_less_2`, loop', time('m2e/tp/b2_less/kairn')),
             ('control: the kernel `interval_split_2`, loop', time('m2e/tp/i2_split/kairn'))]
    table(c, 'KAIRN_CHECKS 1 over 0', rows)
    names = ['m2/tp/interval_add_1/op', 'm2/tp/interval_mul_1/op', 'm2e/tp/i1_less/op', 'm2e/tp/b2_less/op',
             'm2e/tp/i2_split/op']
    print('\n(The ratio of each pair of runs, the program with KAIRN_CHECKS 1 and that with 0 run one after the other.)')
    return names


def checks_times(raw):
    names = ['m2/tp/interval_add_1/op', 'm2/tp/interval_mul_1/op', 'm2/tp/interval_add_2/op', 'm2e/tp/i1_less/op',
             'm2e/tp/i1_contains_t/op', 'm2e/tp/b2_less/op', 'm2e/tp/i2_split/op', 'm2/tp/interval_mul_1/kairn']
    present = [col for col in COLUMNS if any(k[0] == col[0] and k[1] == col[1] for k in raw)]
    print('\n| Times with KAIRN_CHECKS 0; 1 (ns) | %s |' % ' | '.join(col[2] for col in present))
    print('|---' * (len(present) + 1) + '|')
    for n in names:
        cells = []
        for col in present:
            parts = []
            for level in ('O2', 'O3'):
                rs = raw.get((col[0], col[1], 'inline', level), [])
                v0 = [r['ns'][n] for r in rs if r.get('kairn_checks') == 0 and n in r['ns']]
                v1 = [r['ns'][n] for r in rs if r.get('kairn_checks') == 1 and n in r['ns']]
                if v0 and v1:
                    parts.append('%s; %s (-%s)' % (fmt_ns(min(v0)), fmt_ns(min(v1)), level))
            cells.append(', '.join(parts))
        print('| `%s` | %s |' % (n, ' | '.join(cells)))


def runs2(items):
    """Each run of the second part: its spread within (median over minimum at the median function) and
    against the fastest run of its configuration, and the load average."""
    print('\n| Run (second part) | Over the fastest run: median, 90th percentile | Median over minimum within the run (median function) | Load average (1 min) at start, end |')
    print('|---|---|---|---|')
    for item in ('soa', 'enc', 'bisect', 'checks_raw'):
        c = items.get(item, {})
        for key in sorted(c):
            rs = c[key]
            groups = {}
            for r in rs:
                groups.setdefault(r.get('kairn_checks', 0), []).append(r)
            for g in groups.values():
                names = set(g[0]['ns'])
                for r in g[1:]:
                    names &= set(r['ns'])
                best = {n: min(r['ns'][n] for r in g) for n in names}
                for r in g:
                    rel = sorted(r['ns'][n] / best[n] for n in names)
                    within = sorted(x['ns_median'] / x['ns_min'] for x in r['results'])
                    la = r['load_average']
                    print('| `%s` | %.3f, %.3f | %.3f | %.1f, %.1f |' % (r['path'], rel[len(rel) // 2], rel[int(0.9 * (len(rel) - 1))],
                                                                      within[len(within) // 2], la['start'][0], la['end'][0]))


def spread2(items):
    print('\n| Spread of (second part) | Runs | Spread of a function over the runs: median, 90th percentile, worst | Worst function |')
    print('|---|---:|---|---|')
    for item in ('soa', 'enc', 'bisect', 'checks_raw'):
        c = items.get(item, {})
        for key in sorted(c):
            groups = {}
            for r in c[key]:
                groups.setdefault(r.get('kairn_checks', 0), []).append(r)
            for k, runs_ in sorted(groups.items()):
                if len(runs_) < 2:
                    continue
                names = set(runs_[0]['ns'])
                for r in runs_[1:]:
                    names &= set(r['ns'])
                sp = sorted((max(r['ns'][n] for r in runs_) / min(r['ns'][n] for r in runs_) - 1, n) for n in names)
                label = '%s %s%s' % (item.replace('_raw', ''), '-'.join(x for x in key if x != 'inline'),
                                     (' checks %d' % k) if item == 'checks_raw' else '')
                print('| %s | %d | %.1f%%, %.1f%%, %.1f%% | `%s` |' % (label, len(runs_), 100 * sp[len(sp) // 2][0],
                                                                    100 * sp[int(0.9 * (len(sp) - 1))][0], 100 * sp[-1][0], sp[-1][1]))


def configurations2(items):
    print('\n| Configuration (second part) | CPU | Compiler | Flags | Runs per item (soa, enc, bisect, checks pairs) | Date, commit |')
    print('|---|---|---|---|---|---|')
    keys = sorted({k for item in ('soa', 'enc', 'bisect', 'checks') for k in items.get(item, {})})
    for key in keys:
        r = next(items[i][key][0] if i != 'checks' else items[i][key][0]['pair'][0]
                 for i in ('soa', 'enc', 'bisect', 'checks') if key in items.get(i, {}))
        counts = ', '.join(str(len(items.get(i, {}).get(key, []))) for i in ('soa', 'enc', 'bisect', 'checks'))
        print('| %s | %s; %s | %s | `%s` | %s | %s, `%s` |' % ('-'.join(key), r['machine']['cpu'], r['machine']['pinning'],
                                                            r['compiler'], r['flags'], counts, r['date'], r['commit']))


def checks2(items):
    print('\n| Checks of (second part) | Functions checked, failed, per run |')
    print('|---|---|')
    for item in ('soa', 'enc', 'bisect', 'checks_raw'):
        for key, rs in sorted(items.get(item, {}).items()):
            print('| %s %s | %s |' % (item.replace('_raw', ''), '-'.join(x for x in key if x != 'inline'),
                                     '; '.join('%d, %d' % (r['checks']['compared'], r['checks']['failed']) for r in rs)))


SELFTEST = re.compile(r'^selftest-compile-(?P<machine>mac|linux)-(?P<compiler>[a-z0-9]+)$')


def selftest_compile(directory):
    """selftest-compile-MACHINE-COMPILER.json, written by compile_time.py run: the minimum wall time
    over the compilations of each unit, seconds, at -O2 and -O3, and the peak memory."""
    data = {}
    for path in sorted(glob.glob(os.path.join(directory, 'selftest-compile-*.json'))):
        m = SELFTEST.match(os.path.basename(path)[:-len('.json')])
        if m:
            d = json.load(open(path))
            res = {}
            for r in d['results']:
                res.setdefault(r['unit'], {})[r['config']] = {'wall': r['wall_s'], 'peak_mb': r['peak_mb']}
            d['results'] = res
            data[(m.group('machine'), m.group('compiler'))] = d
    if not data:
        return
    present = [col for col in COLUMNS if (col[0], col[1]) in data]
    print('\n| Compile time, s (minimum wall time; -O2; -O3) | %s |' % ' | '.join(col[2] for col in present))
    print('|---' * (len(present) + 1) + '|')
    units = [('empty', 'an empty unit'), ('include', '`kairn/kairn.hpp`, nothing used'),
             ('self_test', 'one call of `kairn::self_test()`')]
    for u, label in units:
        cells = []
        for col in present:
            d = data[(col[0], col[1])]
            parts = []
            for cfg in ('O2', 'O3'):
                r = d['results'].get(u, {}).get(cfg)
                parts.append('%.2f' % min(r['wall']) if r else '–')
            cells.append('; '.join(parts))
        print('| %s | %s |' % (label, ' | '.join(cells)))
    for u, label in units[2:]:
        cells = []
        for col in present:
            d = data[(col[0], col[1])]
            parts = []
            for cfg in ('O2', 'O3'):
                r, e = d['results'].get(u, {}).get(cfg), d['results'].get('include', {}).get(cfg)
                parts.append('%.2f' % (min(r['wall']) - min(e['wall'])) if r and e else '–')
            cells.append('; '.join(parts))
        print('| %s, over the include alone | %s |' % (label, ' | '.join(cells)))
    cells = []
    for col in present:
        d = data[(col[0], col[1])]
        parts = []
        for cfg in ('O2', 'O3'):
            r = d['results'].get('self_test', {}).get(cfg)
            parts.append('%d' % round(min(r['peak_mb'])) if r and r.get('peak_mb') else '–')
        cells.append('; '.join(parts))
    print('| peak memory of `self_test`, MB | %s |' % ' | '.join(cells))


def report2(directory):
    items = load2(directory)
    print('\n## part 2: configurations')
    configurations2(items)
    checks2(items)
    runs2(items)
    spread2(items)
    if items.get('soa'):
        print('\n## part 2: Packed and the containers')
        soa_tables(items['soa'])
    if items.get('enc'):
        print('\n## part 2: the enclosure interface')
        enc_tables(items['enc'])
        enc_overhead(items['enc'])
        float_enc(items['enc'])
    if items.get('bisect'):
        print('\n## part 2: the bisection and self_test')
        bisect_tables(items['bisect'])
    if items.get('checks'):
        print('\n## part 2: KAIRN_CHECKS')
        checks_tables(items['checks'])
        checks_times(items['checks_raw'])
    selftest_compile(directory)


def report(directory, sections):
    c = load(directory)
    inline = {k: v for k, v in c.items() if k[2] == 'inline'}
    for name in sections:
        print('\n## %s' % name)
        if name == 'rational_compile':
            rational_compile(directory)
        elif name == 'compile_tables':
            compile_tables(directory)
        elif name == 'modes':
            modes(directory)
        elif name == 'part2':
            report2(directory)
        else:
            SECTIONS[name](c if name == 'settings' else inline)


def fill(directory, template, out):
    """Writes TEMPLATE to OUT with its table directives replaced by tables of the report, so that no
    number of the page is typed by hand:
        @@table TITLE           the table whose first heading is TITLE
        @@rows TITLE [=> NEW]   the rows of that table whose labels follow, one per line as
        @@ LABEL                '@@ LABEL', until '@@end'; the heading NEW in place of TITLE
        @@end
    """
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report(directory, list(SECTIONS) + ['rational_compile', 'compile_tables', 'modes', 'part2'])
    tables, current = {}, None
    for line in buf.getvalue().splitlines():
        if line.startswith('| ') and current is None:
            title = line[2:].split(' | ')[0]
            current = tables.setdefault(title, [])
            if current:   # a second table of the same title (Times (ns)): keep the first
                current = []
        if line.startswith('|') and current is not None:
            current.append(line)
        elif not line.startswith('|'):
            current = None
    lines = open(template).read().splitlines()
    result, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('@@table '):
            title = line[len('@@table '):]
            if title not in tables:
                sys.stderr.write('no table %r\n' % title)
                result.append('MISSING TABLE: %s' % title)
            else:
                result += tables[title]
        elif line.startswith('@@rows '):
            spec = line[len('@@rows '):]
            title, _, new = spec.partition(' => ')
            t = tables[title.strip()]
            head = t[0] if not new else '| ' + new.strip() + ' |' + t[0].split(' |', 1)[1]
            rows = [head, t[1]]
            i += 1
            while lines[i] != '@@end':
                label = lines[i][3:]
                match = [r for r in t[2:] if r.startswith('| %s |' % label)]
                if not match:
                    raise SystemExit('no row %r in table %r' % (label, title))
                rows.append(match[0])
                i += 1
            result += rows
        else:
            result.append(line)
        i += 1
    with open(out, 'w') as f:
        f.write('\n'.join(result) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('dir')
    ap.add_argument('--section', choices=sorted(SECTIONS) + ['rational_compile', 'compile_tables', 'modes', 'part2'], action='append')
    ap.add_argument('--fill', nargs=2, metavar=('TEMPLATE', 'OUT'))
    ap.add_argument('--part', type=int, choices=[1, 2], help='the tables of one part only (default: the first part)')
    a = ap.parse_args()
    if a.fill:
        fill(a.dir, a.fill[0], a.fill[1])
        return 0
    if a.part == 2:
        report2(a.dir)
        return 0
    report(a.dir, a.section or list(SECTIONS) + ['rational_compile', 'compile_tables', 'modes'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
