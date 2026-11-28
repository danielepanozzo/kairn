#!/usr/bin/env python3
"""up_report.py: the tables of docs/developer/results/bench-upward.md, from the stored runs.

    python3 bench/up_report.py results/upward/bench [--section NAME]
    python3 bench/up_report.py results/upward/bench --earlier results/upward/bench/4710839b \
        --fill docs/developer/results/bench-upward.md

Reads the runs of kairn-bench-up that bench/up_run.py wrote (bench/README.md, "The round-up
interval"): main-MACHINE-COMPILER-LEVEL-rN.json and the pairs checks-MACHINE-COMPILER-LEVEL-cK-rN.json
(K 0 without KAIRN_CHECKS, 1 with), and msvc-windows-msvc-O2-rN.json. A time is the minimum over a
function's samples; a ratio or a difference is taken within one run (for the checked build, within
one pair); a cell is the lowest and highest value over the runs of a configuration, -O2 and -O3
given apart where they differ by more than 0.05 or 3% (ratios), 5% (times), or 0.5 ns and 10%
(differences). With --fill, the text between the lines <!-- BEGIN up_report SECTION --> and
<!-- END up_report SECTION --> of the page is replaced by the tables of SECTION, so that no number
in a table of the page is typed by hand. With --earlier DIR, the section changed puts the times of
the runs in DIR (an earlier campaign) beside these; the sections unord and placement read the
summaries of two programs run alternately (DIR/unord/, DIR/placement/). Standard library only.
"""
import contextlib
import io
import argparse
import glob
import json
import os
import re
import sys

COLUMNS = [('mac', 'appleclang', 'M3, Apple clang'), ('mac', 'gcc16', 'M3, GCC 16'),
           ('linux', 'gcc', 'Zen 2, GCC 13'), ('linux', 'clang', 'Zen 2, Clang 18')]
WINDOWS = [('windows', 'msvc', 'i5-13500T, MSVC (unpinned)')]
NAME = re.compile(r'^(?P<item>main|checks|msvc)-(?P<machine>mac|linux|windows)-(?P<compiler>[a-z0-9]+)-(?P<level>O[23])'
                  r'(?:-c(?P<c>[01]))?-r(?P<run>\d+)$')


def load(directory):
    """{item: {(machine, compiler, level): [run, ...]}}; for checks a run is the pair (c0, c1)."""
    items = {}
    pairs = {}
    for path in sorted(glob.glob(os.path.join(directory, '*.json'))):
        m = NAME.match(os.path.basename(path)[:-len('.json')])
        if not m:
            continue
        with open(path) as f:
            d = json.load(f)
        d['ns'] = {r['name']: r['ns_min'] for r in d['results']}
        d['path'] = os.path.basename(path)
        key = (m.group('machine'), m.group('compiler'), m.group('level'))
        if m.group('item') == 'checks':
            pairs.setdefault(key + (int(m.group('run')),), {})[int(m.group('c'))] = d
        else:
            items.setdefault(m.group('item'), {}).setdefault(key, []).append(d)
    for k, p in sorted(pairs.items()):
        if 0 in p and 1 in p:
            items.setdefault('checks', {}).setdefault(k[:3], []).append(p)
    return items


def fmt_ratio(lo, hi):
    digits = 2 if hi < 10 else 1 if hi < 100 else 0
    a, b = '%.*f' % (digits, lo), '%.*f' % (digits, hi)
    return a if a == b else '%s to %s' % (a, b)


def fmt_one(v):
    if abs(v) >= 100:
        return '%.0f' % v
    if abs(v) >= 10:
        return '%.1f' % v
    return '%.2f' % v if abs(v) >= 1 else '%.3f' % v


def fmt_ns(lo, hi):
    a, b = fmt_one(lo), fmt_one(hi)
    return a if a == b else '%s to %s' % (a, b)


def values(runs, f):
    out = []
    for r in runs:
        try:
            v = f(r)
        except (KeyError, ZeroDivisionError, TypeError):
            continue
        if v is not None:
            out.append(v)
    return out


def close(kind, lo, hi):
    if kind == 'ratio':
        return hi - lo <= max(0.05, 0.03 * abs(lo))
    if kind == 'time':
        return hi <= 1.05 * lo
    return hi - lo <= max(0.5, 0.1 * abs(lo))


def cell(configs, machine, compiler, f, kind):
    per = {}
    for level in ('O2', 'O3'):
        v = values(configs.get((machine, compiler, level), []), f)
        if v:
            per[level] = (min(v), max(v))
    if not per:
        return ''
    fmt = fmt_ratio if kind == 'ratio' else fmt_ns
    if len(per) == 2:
        lo = min(per['O2'][0], per['O3'][0])
        hi = max(per['O2'][1], per['O3'][1])
        if close(kind, lo, hi):
            return fmt(lo, hi)
        return '%s (-O2), %s (-O3)' % (fmt(*per['O2']), fmt(*per['O3']))
    level, (lo, hi) = next(iter(per.items()))
    return '%s (-%s)' % (fmt(lo, hi), level)


# Functions of one run (r['ns']) or of one pair ((c0, c1)).
def t(a):
    return lambda r: r['ns'][a]


def ratio(a, b):
    return lambda r: r['ns'][a] / r['ns'][b]


def diff(a, b, scale=1.0):
    return lambda r: (r['ns'][a] - r['ns'][b]) * scale


def share(a, b):
    """(a - b) / a: the share of a that a has more than b."""
    return lambda r: (r['ns'][a] - r['ns'][b]) / r['ns'][a]


def checked(a):
    return lambda p: p[1]['ns'][a] / p[0]['ns'][a]


def table(configs, title, rows, kind='ratio', columns=COLUMNS):
    present = [c for c in columns if any(k[0] == c[0] and k[1] == c[1] for k in configs)]
    if not present:
        return
    print('\n| %s | %s |' % (title, ' | '.join(c[2] for c in present)))
    print('|---' * (len(present) + 1) + '|')
    for label, f in rows:
        cells = [cell(configs, c[0], c[1], f, kind) for c in present]
        if any(cells):
            print('| %s | %s |' % (label, ' | '.join(cells)))


# --- The tables of the page -----------------------------------------------------------------------

U = 'upw'
D = 'm2'


def type_tables(c):
    ops = [('+', 'interval_add_1', 'pair_add_1/plain'), ('-', 'interval_sub_1', None), ('*', 'interval_mul_1', 'plain4_mul_1/plain')]
    rows = []
    for sym, k, _ in ops:
        rows.append(('`%s/tp/%s/native`' % (U, k), t('%s/tp/%s/native' % (U, k))))
        rows.append(('`%s/tp/%s/native_x16`' % (U, k), t('%s/tp/%s/native_x16' % (U, k))))
        rows.append(('`%s/tp/%s/conv`' % (U, k), t('%s/tp/%s/conv' % (U, k))))
        rows.append(('`%s/tp/%s/op`' % (D, k), t('%s/tp/%s/op' % (D, k))))
        rows.append(('`%s/tp/%s/fenv_loop`' % (D, k), t('%s/tp/%s/fenv_loop' % (D, k))))
        rows.append(('`%s/tp/%s/fenv_loop_x16`' % (D, k), t('%s/tp/%s/fenv_loop_x16' % (D, k))))
    rows += [('`m2/tp/pair_add_1/plain`', t('m2/tp/pair_add_1/plain')), ('`m2/tp/plain4_mul_1/plain`', t('m2/tp/plain4_mul_1/plain'))]
    table(c, 'Loops, times (ns per operation)', rows, 'time')
    rows = []
    for sym, k, floor in ops:
        rows.append(('`X %s Y`: Interval<T, 1> over the type, one scope per loop' % sym,
                     ratio('%s/tp/%s/op' % (D, k), '%s/tp/%s/native' % (U, k))))
        rows.append(('`X %s Y`: Interval<T, 1> over the type, 16 loops per scope' % sym,
                     ratio('%s/tp/%s/op' % (D, k), '%s/tp/%s/native_x16' % (U, k))))
    for sym, k, floor in ops:
        rows.append(('`X %s Y`: the type over fenv_loop' % sym, ratio('%s/tp/%s/native' % (U, k), '%s/tp/%s/fenv_loop' % (D, k))))
        rows.append(('`X %s Y`: the type over fenv_loop, 16 loops per change of mode' % sym,
                     ratio('%s/tp/%s/native_x16' % (U, k), '%s/tp/%s/fenv_loop_x16' % (D, k))))
    for sym, k, floor in ops:
        if floor:
            rows.append(('`X %s Y`: the type, 16 loops per scope, over the plain floor' % sym,
                         ratio('%s/tp/%s/native_x16' % (U, k), '%s/tp/%s' % (D, floor))))
    for sym, k, floor in ops:
        rows.append(('`X %s Y`: converted in the loop over native' % sym,
                     ratio('%s/tp/%s/conv' % (U, k), '%s/tp/%s/native' % (U, k))))
    table(c, 'Loops, ratios', rows)


def chain_tables(c):
    rows = []
    for k in ('sum/interval_add_1', 'prod/interval_mul_1'):
        rows += [('`upw/%s/native`' % k, t('upw/%s/native' % k)), ('`upw/%s/native_x16`' % k, t('upw/%s/native_x16' % k)),
                 ('`upw/%s/conv`' % k, t('upw/%s/conv' % k)), ('`m2/%s/op`' % k, t('m2/%s/op' % k)),
                 ('`m2/%s/fenv_loop`' % k, t('m2/%s/fenv_loop' % k)),
                 ('`m2/%s/fenv_loop_x16`' % k, t('m2/%s/fenv_loop_x16' % k))]
    table(c, 'Chains, times (ns per step)', rows, 'time')
    rows = [('`S + X`: Interval<T, 1> over the type', ratio('m2/sum/interval_add_1/op', 'upw/sum/interval_add_1/native')),
            ('`S + X`: Interval<T, 1> over the type, a chain 16 times as long per scope', ratio('m2/sum/interval_add_1/op', 'upw/sum/interval_add_1/native_x16')),
            ('`P * X`: Interval<T, 1> over the type', ratio('m2/prod/interval_mul_1/op', 'upw/prod/interval_mul_1/native')),
            ('`P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope', ratio('m2/prod/interval_mul_1/op', 'upw/prod/interval_mul_1/native_x16')),
            ('`S + X`: the type over fenv_loop', ratio('upw/sum/interval_add_1/native', 'm2/sum/interval_add_1/fenv_loop')),
            ('`S + X`: the type over fenv_loop, both 16 times as long', ratio('upw/sum/interval_add_1/native_x16', 'm2/sum/interval_add_1/fenv_loop_x16')),
            ('`P * X`: the type over fenv_loop', ratio('upw/prod/interval_mul_1/native', 'm2/prod/interval_mul_1/fenv_loop')),
            ('`P * X`: the type over fenv_loop, both 16 times as long', ratio('upw/prod/interval_mul_1/native_x16', 'm2/prod/interval_mul_1/fenv_loop_x16')),
            ('`S + X`: converted over native', ratio('upw/sum/interval_add_1/conv', 'upw/sum/interval_add_1/native')),
            ('`P * X`: converted over native', ratio('upw/prod/interval_mul_1/conv', 'upw/prod/interval_mul_1/native'))]
    table(c, 'Chains, ratios', rows)


def poly_tables(c):
    rows = [('`upw/tp/horner_i1/native`', t('upw/tp/horner_i1/native')), ('`upw/tp/horner_i1/conv`', t('upw/tp/horner_i1/conv')),
            ('`m2/tp/horner_i1/op`', t('m2/tp/horner_i1/op')), ('`m2/tp/horner_i1/fenv_loop`', t('m2/tp/horner_i1/fenv_loop')),
            ('`upw/lat/horner_i1/native`', t('upw/lat/horner_i1/native')), ('`upw/lat/horner_i1/conv`', t('upw/lat/horner_i1/conv')),
            ('`m2/lat/horner_i1/op`', t('m2/lat/horner_i1/op')), ('`m2/lat/horner_i1/fenv_loop`', t('m2/lat/horner_i1/fenv_loop')),
            ('`upw/tp/det3_i1/native`', t('upw/tp/det3_i1/native')), ('`upw/tp/det3_i1/conv`', t('upw/tp/det3_i1/conv')),
            ('`m2/tp/det3_i1/op`', t('m2/tp/det3_i1/op')), ('`m2/tp/det3_i1/fenv_loop`', t('m2/tp/det3_i1/fenv_loop')),
            ('`m2/tp/det3_i2/op`', t('m2/tp/det3_i2/op')), ('`m2/tp/det3_b1/op`', t('m2/tp/det3_b1/op')),
            ('`m2/tp/det3_b2/op`', t('m2/tp/det3_b2/op')), ('`m2/tp/det3_t/plain`', t('m2/tp/det3_t/plain'))]
    table(c, 'Horner and the determinant, times (ns per evaluation)', rows, 'time')
    rows = [('Horner, independent: Interval<T, 1> over the type', ratio('m2/tp/horner_i1/op', 'upw/tp/horner_i1/native')),
            ('Horner, dependent: Interval<T, 1> over the type', ratio('m2/lat/horner_i1/op', 'upw/lat/horner_i1/native')),
            ('Horner, independent: the type over fenv_loop', ratio('upw/tp/horner_i1/native', 'm2/tp/horner_i1/fenv_loop')),
            ('Horner, dependent: the type over fenv_loop', ratio('upw/lat/horner_i1/native', 'm2/lat/horner_i1/fenv_loop')),
            ('Horner, independent: converted over native', ratio('upw/tp/horner_i1/conv', 'upw/tp/horner_i1/native')),
            ('det3: Interval<T, 1> over the type', ratio('m2/tp/det3_i1/op', 'upw/tp/det3_i1/native')),
            ('det3: the type over fenv_loop', ratio('upw/tp/det3_i1/native', 'm2/tp/det3_i1/fenv_loop')),
            ('det3: converted over native', ratio('upw/tp/det3_i1/conv', 'upw/tp/det3_i1/native')),
            ('det3: Ball<T, 1> over the type', ratio('m2/tp/det3_b1/op', 'upw/tp/det3_i1/native')),
            ('det3: Interval<T, 2> over the type', ratio('m2/tp/det3_i2/op', 'upw/tp/det3_i1/native')),
            ('det3: Ball<T, 2> over the type', ratio('m2/tp/det3_b2/op', 'upw/tp/det3_i1/native')),
            ('det3: the type over plain double', ratio('upw/tp/det3_i1/native', 'm2/tp/det3_t/plain'))]
    table(c, 'Horner and the determinant, ratios', rows)


def conversion_tables(c):
    rows = [('`upw/tp/from_interval_1/op`, ns per element', t('upw/tp/from_interval_1/op')),
            ('`upw/tp/to_interval_1/op`, ns per element', t('upw/tp/to_interval_1/op'))]
    table(c, 'Conversions alone, times', rows, 'time')
    rows = [('`X + Y`, converted minus native (two conversions in, one out)', diff('upw/tp/interval_add_1/conv', 'upw/tp/interval_add_1/native')),
            ('`X * Y`, converted minus native', diff('upw/tp/interval_mul_1/conv', 'upw/tp/interval_mul_1/native')),
            ('`S + X`, converted minus native (one conversion in)', diff('upw/sum/interval_add_1/conv', 'upw/sum/interval_add_1/native')),
            ('det3, converted minus native (12 in, one out)', diff('upw/tp/det3_i1/conv', 'upw/tp/det3_i1/native'))]
    table(c, 'What the conversions cost (ns per operation)', rows, 'diff')
    rows = [('`X + Y`: Interval<T, 1> over the type converted in the loop', ratio('m2/tp/interval_add_1/op', 'upw/tp/interval_add_1/conv')),
            ('`X * Y`: Interval<T, 1> over the type converted in the loop', ratio('m2/tp/interval_mul_1/op', 'upw/tp/interval_mul_1/conv')),
            ('`S + X`: Interval<T, 1> over the type converted in the loop', ratio('m2/sum/interval_add_1/op', 'upw/sum/interval_add_1/conv')),
            ('det3: Interval<T, 1> over the type converted in the loop', ratio('m2/tp/det3_i1/op', 'upw/tp/det3_i1/conv'))]
    table(c, 'The default type against the type converted in the loop', rows)


def array_tables(c):
    rows = []
    for b, f in (('upwa', 'double'), ('upwaf', 'float')):
        for k in ('interval_add_1', 'interval_sub_1', 'interval_mul_1'):
            rows.append(('`%s/tp/%s/op`' % (b, k), t('%s/tp/%s/op' % (b, k))))
            rows.append(('`%s/tp/%s/packed`' % (b, k), t('%s/tp/%s/packed' % (b, k))))
            rows.append(('`%s/tp/%s/fenv_loop`' % (b, k), t('%s/tp/%s/fenv_loop' % (b, k))))
    for k in ('interval_add_1', 'interval_mul_1'):
        rows.append(('`m2p/tp/%s/kairn`' % k, t('m2p/tp/%s/kairn' % k)))
        rows.append(('`m2p/tp/%s/fenv_loop`' % k, t('m2p/tp/%s/fenv_loop' % k)))
    table(c, 'Functions on arrays of 256, times (ns per interval)', rows, 'time')
    rows = []
    for b, f in (('upwa', 'double'), ('upwaf', 'float')):
        for sym, k in (('+', 'interval_add_1'), ('-', 'interval_sub_1'), ('*', 'interval_mul_1')):
            rows.append(('%s `%s`: the packed kernel over the function' % (f, sym), ratio('%s/tp/%s/packed' % (b, k), '%s/tp/%s/op' % (b, k))))
    for b, f in (('upwa', 'double'), ('upwaf', 'float')):
        for sym, k in (('+', 'interval_add_1'), ('-', 'interval_sub_1'), ('*', 'interval_mul_1')):
            rows.append(('%s `%s`: the function over fenv_loop' % (f, sym), ratio('%s/tp/%s/op' % (b, k), '%s/tp/%s/fenv_loop' % (b, k))))
    for sym, k in (('+', 'interval_add_1'), ('*', 'interval_mul_1')):
        rows.append(('double `%s`: m2p (the arrays of m2.cpp) over packed (placed)' % sym, ratio('m2p/tp/%s/kairn' % k, 'upwa/tp/%s/packed' % k)))
        rows.append(('double `%s`: m2p fenv_loop over fenv_loop (placed)' % sym, ratio('m2p/tp/%s/fenv_loop' % k, 'upwa/tp/%s/fenv_loop' % k)))
    for sym, k in (('+', 'interval_add_1'), ('*', 'interval_mul_1')):
        rows.append(('`%s`: the function on arrays over the type, 16 loops per scope' % sym, ratio('upwa/tp/%s/op' % k, 'upw/tp/%s/native_x16' % k)))
        rows.append(('`%s`: float over double, the function on arrays' % sym, ratio('upwaf/tp/%s/op' % k, 'upwa/tp/%s/op' % k)))
        rows.append(('`%s`: float over double, the type' % sym, ratio('upwf/tp/%s/native' % k, 'upw/tp/%s/native' % k)))
    table(c, 'Functions on arrays, ratios', rows)


LENGTHS = (4, 16, 64, 256, 1024, 4096)


def length_tables(c):
    for op in ('add', 'mul'):
        rows = []
        for n in LENGTHS:
            for v in ('nearest', 'nested', 'none'):
                rows.append(('`%s_%d/%s`' % (op, n, v), t('upwa/call/%s_%d/%s' % (op, n, v))))
        table(c, '`kairn::upward::%s` by length, times (ns per call)' % op, rows, 'time')
        rows = []
        for n in LENGTHS:
            rows.append(('%d: called from rounding to nearest, minus without the scope' % n,
                         diff('upwa/call/%s_%d/nearest' % (op, n), 'upwa/call/%s_%d/none' % (op, n))))
        for n in LENGTHS:
            rows.append(('%d: inside an outer Scope, minus without the scope' % n,
                         diff('upwa/call/%s_%d/nested' % (op, n), 'upwa/call/%s_%d/none' % (op, n))))
        table(c, '`kairn::upward::%s`: the scope of a call (ns per call)' % op, rows, 'diff')
        rows = []
        for n in LENGTHS:
            rows.append(('%d' % n, share('upwa/call/%s_%d/nearest' % (op, n), 'upwa/call/%s_%d/none' % (op, n))))
        table(c, '`kairn::upward::%s`: the scope\'s share of a call from rounding to nearest' % op, rows, 'ratio')


def scope_rows():
    s = 'upws/call/'
    return [
        ('`Scope` that changes the mode', diff(s + 'scope_add_1/change', s + 'scope_add_1/none')),
        ('`Scope` inside a `Scope` (nothing changes)', diff(s + 'scope_add_1/nested', s + 'scope_add_1/none')),
        ('register-only scope (of the functions on arrays) that changes the mode', diff(s + 'regscope_add_1/change', s + 'scope_add_1/none')),
        ('register-only scope inside a `Scope`', diff(s + 'regscope_add_1/nested', s + 'scope_add_1/none')),
        ('`NearestScope` inside a `Scope` (changes the mode)', diff(s + 'nearest_add_1/change', s + 'nearest_add_1/none')),
        ('`NearestScope` where the mode is to nearest', diff(s + 'nearest_add_1/nested', s + 'nearest_add_1/none')),
    ]


def scope_tables(c, columns=COLUMNS):
    s = 'upws/call/'
    rows = [('`%s`' % (s + n), t(s + n)) for n in (
        'scope_add_1/none', 'scope_add_1/change', 'scope_add_1/nested', 'regscope_add_1/change', 'regscope_add_1/nested',
        'nearest_add_1/none', 'nearest_add_1/change', 'nearest_add_1/nested')]
    table(c, 'Calls of one operation, times (ns per call)', rows, 'time', columns)
    table(c, 'The cost of a scope (ns per call: the call with it minus without it)', scope_rows(), 'diff', columns)


def float_tables(c):
    rows = [('`upwf/tp/interval_add_1/native`', t('upwf/tp/interval_add_1/native')),
            ('`upwf/tp/interval_add_1/conv`', t('upwf/tp/interval_add_1/conv')),
            ('`m2f/tp/interval_add_1/op`', t('m2f/tp/interval_add_1/op')),
            ('`m2f/tp/interval_add_1/fenv_loop`', t('m2f/tp/interval_add_1/fenv_loop')),
            ('`upwf/tp/interval_mul_1/native`', t('upwf/tp/interval_mul_1/native')),
            ('`upwf/tp/interval_mul_1/conv`', t('upwf/tp/interval_mul_1/conv')),
            ('`m2f/tp/interval_mul_1/op`', t('m2f/tp/interval_mul_1/op')),
            ('`m2f/tp/interval_mul_1/fenv_loop`', t('m2f/tp/interval_mul_1/fenv_loop'))]
    table(c, '`float`, times (ns per operation)', rows, 'time')
    rows = [('`X + Y`: Interval<float, 1> over the type', ratio('m2f/tp/interval_add_1/op', 'upwf/tp/interval_add_1/native')),
            ('`X * Y`: Interval<float, 1> over the type', ratio('m2f/tp/interval_mul_1/op', 'upwf/tp/interval_mul_1/native')),
            ('`X + Y`: the type over fenv_loop', ratio('upwf/tp/interval_add_1/native', 'm2f/tp/interval_add_1/fenv_loop')),
            ('`X * Y`: the type over fenv_loop', ratio('upwf/tp/interval_mul_1/native', 'm2f/tp/interval_mul_1/fenv_loop')),
            ('`X + Y`: converted over native', ratio('upwf/tp/interval_add_1/conv', 'upwf/tp/interval_add_1/native')),
            ('`X * Y`: converted over native', ratio('upwf/tp/interval_mul_1/conv', 'upwf/tp/interval_mul_1/native'))]
    table(c, '`float`, ratios', rows)


CHECKED = ['upw/tp/interval_add_1/native', 'upw/tp/interval_add_1/native_x16', 'upw/tp/interval_add_1/conv',
           'upw/tp/interval_mul_1/native', 'upw/tp/interval_mul_1/native_x16', 'upw/tp/interval_mul_1/conv',
           'upw/sum/interval_add_1/native', 'upw/sum/interval_add_1/native_x16', 'upw/prod/interval_mul_1/native',
           'upw/prod/interval_mul_1/native_x16', 'upwf/tp/interval_add_1/native',
           'upwf/tp/interval_mul_1/native', 'upwa/tp/interval_add_1/op', 'upwa/tp/interval_mul_1/op',
           'upwaf/tp/interval_add_1/op', 'upwaf/tp/interval_mul_1/op', 'upws/call/scope_add_1/change',
           'upws/call/scope_add_1/nested', 'upws/call/regscope_add_1/change', 'm2/tp/interval_add_1/op',
           'm2/tp/interval_mul_1/op', 'm2/sum/interval_add_1/op', 'm2/prod/interval_mul_1/op']


def checks_tables(c):
    rows = [('`%s`' % n, checked(n)) for n in CHECKED]
    table(c, 'With `KAIRN_CHECKS` 1 over without, the same run order', rows)


def msvc_tables(c):
    if not c:
        return
    rows = [(('`%s`' % n), t(n)) for n in (
        'upw/tp/interval_add_1/native', 'upw/tp/interval_add_1/native_x16', 'upw/tp/interval_add_1/conv',
        'm2/tp/interval_add_1/op', 'm2/tp/interval_add_1/fenv_loop', 'upw/tp/interval_mul_1/native',
        'upw/tp/interval_mul_1/native_x16', 'upw/tp/interval_mul_1/conv', 'm2/tp/interval_mul_1/op',
        'm2/tp/interval_mul_1/fenv_loop', 'upw/sum/interval_add_1/native', 'm2/sum/interval_add_1/op',
        'upw/sum/interval_add_1/native_x16', 'upw/prod/interval_mul_1/native', 'upw/prod/interval_mul_1/native_x16',
        'upw/prod/interval_mul_1/conv', 'm2/prod/interval_mul_1/op', 'm2/prod/interval_mul_1/fenv_loop')]
    table(c, 'MSVC, times (ns per operation or step), unpinned', rows, 'time', WINDOWS)
    rows = [('`X + Y`: Interval<T, 1> over the type', ratio('m2/tp/interval_add_1/op', 'upw/tp/interval_add_1/native')),
            ('`X + Y`: Interval<T, 1> over the type, 16 loops per scope', ratio('m2/tp/interval_add_1/op', 'upw/tp/interval_add_1/native_x16')),
            ('`X * Y`: Interval<T, 1> over the type', ratio('m2/tp/interval_mul_1/op', 'upw/tp/interval_mul_1/native')),
            ('`X * Y`: Interval<T, 1> over the type, 16 loops per scope', ratio('m2/tp/interval_mul_1/op', 'upw/tp/interval_mul_1/native_x16')),
            ('`S + X`: Interval<T, 1> over the type', ratio('m2/sum/interval_add_1/op', 'upw/sum/interval_add_1/native')),
            ('`P * X`: Interval<T, 1> over the type', ratio('m2/prod/interval_mul_1/op', 'upw/prod/interval_mul_1/native')),
            ('`P * X`: Interval<T, 1> over the type, a chain 16 times as long per scope', ratio('m2/prod/interval_mul_1/op', 'upw/prod/interval_mul_1/native_x16')),
            ('`X + Y`: the type over fenv_loop', ratio('upw/tp/interval_add_1/native', 'm2/tp/interval_add_1/fenv_loop')),
            ('`X * Y`: the type over fenv_loop', ratio('upw/tp/interval_mul_1/native', 'm2/tp/interval_mul_1/fenv_loop')),
            ('`P * X`: the type over fenv_loop', ratio('upw/prod/interval_mul_1/native', 'm2/prod/interval_mul_1/fenv_loop'))]
    table(c, 'MSVC, ratios, unpinned', rows, 'ratio', WINDOWS)
    scope_tables(c, WINDOWS)


# --- The runs -------------------------------------------------------------------------------------

def configurations(items):
    print('\n| Configuration | CPU | Compiler | Flags | The units of the round-up interval | Runs | Date, commit |')
    print('|---|---|---|---|---|---:|---|')
    for item in ('main', 'msvc'):
        for key in sorted(items.get(item, {})):
            r = items[item][key][0]
            print('| %s | %s; %s | %s | `%s` | `%s` | %d | %s, `%s` |' % (
                '-'.join(key), r['machine']['cpu'], r['machine']['pinning'], r['compiler'], r['flags'],
                r.get('upward_flags', '').replace(r['flags'], '...'), len(items[item][key]), r['date'], r['commit']))


def checks_counts(items):
    """The checks before timing, from the first run of each configuration."""
    print('\n| Checks of | Functions checked, failed | Of the round-up interval\'s: compared with the default kernels, '
          'values, equal, zero of the other sign, one number tighter; not the value rounded to nearest | '
          'Compared byte for byte (the default types\' determinant) |')
    print('|---|---|---|---|')
    for item in ('main', 'msvc'):
        for key in sorted(items.get(item, {})):
            r = items[item][key][0]
            u = r.get('up_checks', {})
            five = [v for v in u.values() if len(v) == 5]
            two = [v for v in u.values() if len(v) == 2]
            sums = [sum(v[i] for v in five) for i in range(5)]
            print('| %s | %d, %d | %d functions: %d, %d, %d, %d; %d | %d functions, %d values |' % (
                '-'.join(key), r['checks']['compared'], r['checks']['failed'], len(five), *sums, len(two),
                sum(v[0] for v in two)))


def runs_table(items):
    print('\n| Run | CPU, its sibling: busiest 5 s, mean | Spread within the run (median function) | Over the fastest run of its configuration: median, 90th percentile | Load average (1 min) at start, end |')
    print('|---|---|---|---|---|')
    for item in ('main', 'msvc', 'checks'):
        for key in sorted(items.get(item, {})):
            rs = items[item][key]
            groups = [[p[0] for p in rs], [p[1] for p in rs]] if item == 'checks' else [rs]
            best = {}
            for g in groups:
                names = set(g[0]['ns'])
                for r in g[1:]:
                    names &= set(r['ns'])
                for r in g:
                    for n in names:
                        k = (id(g), n)
                        best[k] = min(best.get(k, float('inf')), r['ns'][n])
            for g in groups:
                for r in g:
                    names = [n for (gid, n) in best if gid == id(g)]
                    rel = sorted(r['ns'][n] / best[(id(g), n)] for n in names)
                    rc = r.get('run_conditions', {})
                    cpu = ('%s, %s: %.0f%%, %.1f%%' % (rc['cpu'], rc['sibling'], 100 * rc.get('sibling_busy_max', 0),
                                                         100 * rc.get('sibling_busy_mean', 0))
                           if rc.get('cpu') is not None else 'not pinned')
                    la = r['load_average']
                    print('| `%s` | %s | %.3f | %.3f, %.3f | %.1f, %.1f |' % (
                        r['path'], cpu, rc.get('spread', 0), rel[len(rel) // 2], rel[int(0.9 * (len(rel) - 1))],
                        la['start'][0], la['end'][0]))


def spread_table(items):
    print('\n| Spread of | Runs | A function over the runs: median, 90th percentile, worst | Worst function |')
    print('|---|---:|---|---|')
    for item in ('main', 'msvc'):
        for key in sorted(items.get(item, {})):
            rs = items[item][key]
            if len(rs) < 2:
                continue
            names = set(rs[0]['ns'])
            for r in rs[1:]:
                names &= set(r['ns'])
            sp = sorted((max(r['ns'][n] for r in rs) / min(r['ns'][n] for r in rs) - 1, n) for n in names)
            print('| %s | %d | %.1f%%, %.1f%%, %.1f%% | `%s` |' % ('-'.join(key), len(rs), 100 * sp[len(sp) // 2][0],
                                                              100 * sp[int(0.9 * (len(sp) - 1))][0], 100 * sp[-1][0], sp[-1][1]))


def attempts_table(directory):
    """Per configuration and item: the attempts, the kept runs, and those set aside by reason, with
    the range of their spreads at the median function or of their sibling's busiest sample."""
    print('\n| Configuration, item | Runs made | Kept | Set aside: for the spread at the median function; for a busy sibling (its busiest 5 s) |')
    print('|---|---:|---:|---|')
    for path in sorted(glob.glob(os.path.join(directory, 'attempts-*.json'))):
        with open(path) as f:
            a = json.load(f)
        name = os.path.basename(path)[len('attempts-'):-len('.json')]
        config, item = name.rsplit('-', 1)
        kept = glob.glob(os.path.join(directory, '%s-%s-*r[0-9]*.json' % (item, config)))
        spread = [x['spread'] for x in a if 'spread' in x.get('reason', '') and 'sibling' not in x.get('reason', '')]
        busy = [x for x in a if 'sibling' in x.get('reason', '')]
        parts = []
        if spread:
            parts.append('%d, spread %.3f to %.3f' % (len(spread), min(spread), max(spread)))
        if busy:
            b = [x.get('sibling_busy_max', 0) for x in busy]
            parts.append('%d, sibling %.0f%% to %.0f%%' % (len(busy), 100 * min(b), 100 * max(b)))
        other = [x for x in a if x.get('reason') != 'kept' and x not in busy and 'spread' not in x.get('reason', '')]
        if other:
            parts.append('%d, %s' % (len(other), '; '.join(sorted(set(x['reason'] for x in other)))))
        partners = len(a) - len(kept) - len(spread) - len(busy) - len(other)
        if partners:
            parts.append('%d kept alone, set aside with the other run of their pair' % partners)
        print('| %s | %d | %d | %s |' % (name, len(a), len(kept), '; '.join(parts) or 'none'))


SECTIONS = {'type': type_tables, 'chains': chain_tables, 'poly': poly_tables, 'conversions': conversion_tables,
            'arrays': array_tables, 'lengths': length_tables, 'scopes': scope_tables, 'float': float_tables}


# --- What changed since the earlier runs (--earlier) ---------------------------------------------

# The functions whose loops loaded the pointers of their arrays again in every iteration (or before
# every call) in the program of the earlier runs, and controls that did not.
CHANGED = ['upw/tp/interval_add_1/native', 'upw/tp/interval_add_1/native_x16', 'upw/tp/interval_sub_1/native',
           'upw/tp/interval_sub_1/native_x16', 'upw/tp/interval_mul_1/native', 'upw/tp/interval_mul_1/native_x16',
           'upw/tp/interval_add_1/conv', 'upw/tp/det3_i1/native', 'upw/tp/from_interval_1/op',
           'upw/sum/interval_add_1/native', 'upws/call/scope_add_1/none', 'upwa/call/add_4/none',
           'upwa/tp/interval_add_1/packed', 'upwa/tp/interval_add_1/fenv_loop', 'upwa/tp/interval_mul_1/fenv_loop',
           'upw/tp/horner_i1/native', 'upwa/tp/interval_add_1/op', 'm2/tp/interval_add_1/op',
           'm2/tp/interval_add_1/fenv_loop']


def changed_tables(now, earlier, commit):
    """Per function of CHANGED, its times in the earlier runs and in these, one row each."""
    rows = []
    for name in CHANGED:
        rows.append(('`%s`, at `%s`' % (name, commit), t(name), earlier))
        rows.append(('`%s`, now' % name, t(name), now))
    present = [c for c in COLUMNS if any(k[0] == c[0] and k[1] == c[1] for k in now)]
    print('\n| Before and after the repair, times (ns per operation, per call for the calls) | %s |' %
          ' | '.join(c[2] for c in present))
    print('|---' * (len(present) + 1) + '|')
    for label, f, src in rows:
        cells = [cell(src, c[0], c[1], f, 'time') for c in present]
        if any(cells):
            print('| %s | %s |' % (label, ' | '.join(cells)))


# The test of an empty operand on arm64 (detail::unord), measured on two builds of the repaired
# program, the old helper and the new, run alternately (DIR/unord/COMPILER-LEVEL.json, the summary
# of each configuration's pairs): the new over the old, the lowest and highest ratio over the pairs.
UNORD = ['upw/tp/interval_mul_1/native', 'upw/tp/interval_mul_1/native_x16', 'upw/tp/interval_mul_1/conv',
         'upw/prod/interval_mul_1/native', 'upw/tp/det3_i1/native', 'upw/tp/det3_i1/conv', 'upw/tp/horner_i1/native',
         'upw/lat/horner_i1/native', 'upwf/tp/interval_mul_1/native', 'upwa/tp/interval_mul_1/op',
         'upwaf/tp/interval_mul_1/op', 'upwa/call/mul_4/none', 'upw/tp/interval_add_1/native',
         'm2/tp/interval_mul_1/op']


def ab_table(directory, sub, columns, names, title):
    """The ratios B/A of the alternate runs stored in DIR/SUB/TAG.json (TAG COMPILER-LEVEL, with the
    machine first for those of Linux), per function of names: the lowest and highest over the pairs,
    -O2 and -O3 given apart as the other tables give them."""
    data = {}
    for p in sorted(glob.glob(os.path.join(directory, sub, '*.json'))):
        with open(p) as f:
            d = json.load(f)
        compiler, level = d['tag'].rsplit('-', 1)
        data[(compiler, level)] = d
    cols = [c for c in columns if any(k[0] == c[0] for k in data)]
    if not cols:
        return
    pairs = sorted(set(d['pairs'] for d in data.values()))
    print('\n| %s (%s pairs) | %s |' % (title, ' or '.join(str(p) for p in pairs), ' | '.join(c[1] for c in cols)))
    print('|---' * (len(cols) + 1) + '|')
    for name in names:
        cells = []
        for compiler, _ in cols:
            per = {lv: (data[(compiler, lv)]['summary'][name]['ratio_min'], data[(compiler, lv)]['summary'][name]['ratio_max'])
                   for lv in ('O2', 'O3') if (compiler, lv) in data and name in data[(compiler, lv)]['summary']}
            if not per:
                cells.append('')
            elif len(per) == 2 and close('ratio', min(per['O2'][0], per['O3'][0]), max(per['O2'][1], per['O3'][1])):
                cells.append(fmt_ratio(min(per['O2'][0], per['O3'][0]), max(per['O2'][1], per['O3'][1])))
            else:
                cells.append(', '.join('%s (-%s)' % (fmt_ratio(*per[lv]), lv) for lv in ('O2', 'O3') if lv in per))
        if any(cells):
            print('| `%s` | %s |' % (name, ' | '.join(cells)))


def unord_tables(directory):
    ab_table(directory, 'unord', (('appleclang', 'M3, Apple clang'), ('gcc16', 'M3, GCC 16')), UNORD,
             'The new test over the old, the same program')


# The program of these runs against that of the earlier ones on Zen 2, alternately on one CPU
# (DIR/placement/linux-COMPILER-LEVEL.json; linux-gcc-scopes-O3.json, the scopes of GCC 13 at -O3).
PLACEMENT = ['upw/tp/interval_add_1/native', 'upw/tp/interval_add_1/native_x16', 'upw/tp/interval_sub_1/native',
             'upw/tp/interval_sub_1/native_x16', 'upw/tp/interval_mul_1/native', 'upw/tp/interval_mul_1/native_x16',
             'upw/tp/interval_add_1/conv', 'upw/tp/from_interval_1/op', 'upw/tp/to_interval_1/op',
             'upw/sum/interval_add_1/native', 'upwa/tp/interval_add_1/fenv_loop', 'm2/tp/interval_add_1/op',
             'upws/call/scope_add_1/change', 'upws/call/scope_add_1/none', 'upws/call/regscope_add_1/change',
             'upws/call/nearest_add_1/change']


def placement_tables(directory):
    ab_table(directory, 'placement', (('linux-gcc', 'Zen 2, GCC 13'), ('linux-gcc-scopes', 'Zen 2, GCC 13, the scopes'),
                                      ('linux-clang', 'Zen 2, Clang 18')), PLACEMENT,
             'This program over that of the earlier runs, alternately on one CPU')


MARK = re.compile(r'^<!-- (BEGIN|END) up_report (\S+) -->$')


EARLIER = {}


def earlier_tables(items):
    if not EARLIER:
        raise SystemExit('the section changed needs --earlier DIR')
    first = next(iter(EARLIER['main'].values()))[0]
    changed_tables(items.get('main', {}), EARLIER['main'], first['commit'])


def section_text(items, directory, name):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        if name in SECTIONS:
            SECTIONS[name](items.get('main', {}))
        elif name == 'changed':
            earlier_tables(items)
        elif name == 'unord':
            unord_tables(directory)
        elif name == 'placement':
            placement_tables(directory)
        elif name == 'checks':
            checks_tables(items.get('checks', {}))
        elif name == 'msvc':
            msvc_tables(items.get('msvc', {}))
        elif name == 'configurations':
            configurations(items)
        elif name == 'counts':
            checks_counts(items)
        elif name == 'runs':
            runs_table(items)
        elif name == 'spread':
            spread_table(items)
        elif name == 'attempts':
            attempts_table(directory)
        else:
            raise SystemExit('unknown section %s' % name)
    return out.getvalue().strip('\n')


def fill(items, directory, page):
    with open(page) as f:
        lines = f.read().split('\n')
    out, inside = [], None
    for line in lines:
        m = MARK.match(line)
        if m and m.group(1) == 'BEGIN':
            out.append(line)
            out.append('')
            out.append(section_text(items, directory, m.group(2)))
            out.append('')
            inside = m.group(2)
        elif m and m.group(1) == 'END':
            inside = None
            out.append(line)
        elif inside is None:
            out.append(line)
    with open(page, 'w') as f:
        f.write('\n'.join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('directory')
    ap.add_argument('--section', choices=sorted(SECTIONS) + ['checks', 'msvc', 'runs', 'changed', 'unord', 'placement'])
    ap.add_argument('--fill', metavar='PAGE')
    ap.add_argument('--earlier', metavar='DIR', help='the runs of an earlier program, for the section changed')
    args = ap.parse_args()
    items = load(args.directory)
    if args.earlier:
        EARLIER.update(load(args.earlier))
    if args.fill:
        fill(items, args.directory, args.fill)
        return 0
    main_runs = items.get('main', {})
    if args.section in SECTIONS:
        SECTIONS[args.section](main_runs)
        return 0
    if args.section == 'changed':
        earlier_tables(items)
        return 0
    if args.section == 'unord':
        unord_tables(args.directory)
        return 0
    if args.section == 'placement':
        placement_tables(args.directory)
        return 0
    if args.section == 'checks':
        checks_tables(items.get('checks', {}))
        return 0
    if args.section == 'msvc':
        msvc_tables(items.get('msvc', {}))
        return 0
    if args.section == 'runs':
        configurations(items)
        checks_counts(items)
        runs_table(items)
        spread_table(items)
        attempts_table(args.directory)
        return 0
    for name in ('type', 'chains', 'poly', 'conversions', 'arrays', 'lengths', 'scopes', 'float'):
        print('\n### %s' % name)
        SECTIONS[name](main_runs)
    print('\n### checks')
    checks_tables(items.get('checks', {}))
    print('\n### msvc')
    msvc_tables(items.get('msvc', {}))
    print('\n### runs')
    configurations(items)
    checks_counts(items)
    runs_table(items)
    spread_table(items)
    attempts_table(args.directory)
    return 0


if __name__ == '__main__':
    sys.exit(main())
