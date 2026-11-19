#!/usr/bin/env python3
"""Prints the tables of docs/developer/results/bench-milestone1.md from stored measurements.

    python3 bench/report.py results/milestone1/bench

Reads every NAME.json written by kairn-bench (and asm-NAME.json written by asm_summary.py, if
present) in the directory, and prints Markdown: the configurations, one table per question of
the page, and the time of every function on every configuration. Ratios are of minimum times.
Standard library only.
"""
import json
import os
import re
import sys

ORDER = ['mac-appleclang-O2', 'mac-appleclang-O3', 'mac-gcc16-O2', 'mac-gcc16-O3',
         'linux-gcc-O2', 'linux-gcc-O3', 'linux-clang-O2', 'linux-clang-O3', 'windows-msvc-O2']


def label(name, run):
    cpu = {'macOS': 'M3', 'Linux': 'Zen 2', 'Windows': 'i5'}[run['machine']['os']]
    comp = run['compiler']
    if comp.startswith('Apple clang'):
        c = 'Apple clang'
    elif comp.startswith('Clang'):
        c = 'Clang ' + comp.split()[1].split('.')[0]
    elif comp.startswith('GCC'):
        c = 'GCC ' + comp.split()[1].split('.')[0]
    else:
        c = 'MSVC'
    level = re.findall(r'[-/]O\d', run['flags'])[-1]
    return '%s, %s %s' % (cpu, c, level)


def load(directory):
    runs = {}
    for f in sorted(os.listdir(directory)):
        if f.endswith('.json') and not f.startswith('asm-'):
            with open(os.path.join(directory, f)) as fp:
                runs[f[:-5]] = json.load(fp)
    asm = {}
    for f in sorted(os.listdir(directory)):
        if f.startswith('asm-') and f.endswith('.json'):
            with open(os.path.join(directory, f)) as fp:
                a = json.load(fp)
            cols = a['columns']
            asm[f[4:-5]] = {name: {'instructions': r['instructions'],
                                   'loops': [dict(zip(cols, lp)) for lp in r['loops']]}
                            for name, r in a['functions'].items()}
    names = [n for n in ORDER if n in runs] + sorted(n for n in runs if n not in ORDER)
    return names, runs, asm


def times(run):
    return {r['name']: r for r in run['results']}


def fmt_ns(x):
    return '%.3g' % x if x < 100 else '%.0f' % x


def ratio_table(names, runs, rows, title_col='Operation'):
    """rows: (label, numerator name, denominator name)."""
    labels = [label(n, runs[n]) for n in names]
    out = ['| %s | %s |' % (title_col, ' | '.join(labels)), '|---|' + '---:|' * len(names)]
    for text, num, den in rows:
        cells = []
        for n in names:
            t = times(runs[n])
            if num in t and den in t:
                cells.append('%.2f' % (t[num]['ns_min'] / t[den]['ns_min']))
            else:
                cells.append('—')
        out.append('| %s | %s |' % (text, ' | '.join(cells)))
    return '\n'.join(out)


def ns_table(names, runs, rows, title_col='Operation'):
    """rows: (label, name): minimum time per operation."""
    labels = [label(n, runs[n]) for n in names]
    out = ['| %s | %s |' % (title_col, ' | '.join(labels)), '|---|' + '---:|' * len(names)]
    for text, name in rows:
        cells = []
        for n in names:
            t = times(runs[n])
            cells.append(fmt_ns(t[name]['ns_min']) if name in t else '—')
        out.append('| %s | %s |' % (text, ' | '.join(cells)))
    return '\n'.join(out)


def configurations(names, runs):
    out = ['| Configuration | Machine | Compiler | Flags | Spread: median, worst | Date, commit |',
           '|---|---|---|---|---|---|']
    for n in names:
        r = runs[n]
        spreads = sorted(x['ns_median'] / x['ns_min'] - 1 for x in r['results'])
        med = spreads[len(spreads) // 2]
        worst = spreads[-1]
        out.append('| %s | %s | %s | `%s` | %.1f%%, %.0f%% | %s, `%s` |' % (
            label(n, r), r['machine']['description'], r['compiler'], r['flags'], 100 * med, 100 * worst,
            r['date'], r['commit']))
    return '\n'.join(out)


def checks(names, runs):
    out = ['| Configuration | Functions checked bit for bit | Full kernels: cases; differences (b) vs (a), packed vs scalar (a), variants vs (a); against the statement |',
           '|---|---:|---|']
    for n in names:
        c = runs[n]['checks']
        full = '; '.join('`%s` %d: %d, %d, %d; %d' % (f['kernel'], f['cases'], f['a_vs_b'], f['packed_vs_a'],
                                                     f.get('variants_vs_a', 0), f['not_canonical'] + f['against_statement'])
                         for f in c['full_forms'])
        out.append('| %s | %d (%d failed) | %s |' % (label(n, runs[n]), c['compared'], c['failed'], full))
    return '\n'.join(out)


def vector_table(names, runs, asm, funcs):
    """Vector width of the widest loop of each throughput function, and its selects and branches."""
    labels = [label(n, runs[n]) for n in names]
    out = ['| Function | %s |' % ' | '.join(labels), '|---|' + '---|' * len(names)]
    for f in funcs:
        cells = []
        for n in names:
            a = asm.get(n, {}).get(f)
            if not a or not a['loops']:
                cells.append('—')
                continue
            main = max(a['loops'], key=lambda lp: (lp['vector_bits'], lp['instructions']))
            v = '%d-bit' % main['vector_bits'] if main['vector_bits'] else 'scalar'
            cells.append('%s; %d fma, %d mul, %d sel, %d br' % (v, main['fma'], main['mul'], main['select'],
                                                               main['branch'] - 1 + main['call']))
        out.append('| `%s` | %s |' % (f, ' | '.join(cells)))
    return '\n'.join(out)


def all_times(names, runs):
    labels = [label(n, runs[n]) for n in names]
    every = []
    for n in names:
        for r in runs[n]['results']:
            if r['name'] not in every:
                every.append(r['name'])
    out = ['| Function | %s |' % ' | '.join(labels), '|---|' + '---:|' * len(names)]
    for name in every:
        cells = []
        for n in names:
            t = times(runs[n]).get(name)
            cells.append('%s (%.0f%%)' % (fmt_ns(t['ns_min']), 100 * (t['ns_median'] / t['ns_min'] - 1)) if t else '—')
        out.append('| `%s` | %s |' % (name, ' | '.join(cells)))
    return '\n'.join(out)


def main(argv):
    directory = argv[0] if argv else 'results/milestone1/bench'
    names, runs, asm = load(directory)
    S, P, M = 'scalar', 'packed', 'mpfr'

    def n(backend, kind, kernel, variant):
        return '%s/%s/%s/%s' % (backend, kind, kernel, variant)

    print('## Configurations\n')
    print(configurations(names, runs))
    print('\n## Checks\n')
    print(checks(names, runs))

    print('\n## Q1: opaque product over plain product\n')
    rows = []
    for b in (S, P):
        for k in ('two_prod', 'mul_2_1', 'mul_2_2', 'ball_mul_2'):
            rows.append(('%s throughput, `%s`' % (b, k), n(b, 'tp', k, 'kairn'), n(b, 'tp', k, 'plain')))
    for b in (S, P):
        for k in ('two_prod', 'mul_2_1', 'mul_2_2', 'ball_mul_2'):
            rows.append(('%s product chain, `%s`' % (b, k), n(b, 'prod', k, 'kairn'), n(b, 'prod', k, 'plain')))
        for k in ('mul_2_2+add_2_2', 'ball_mul_2+ball_add_2'):
            rows.append(('%s Horner, `%s`' % (b, k), n(b, 'horner', k, 'kairn'), n(b, 'horner', k, 'plain')))
    rows.append(('scalar product chain, one limb: `mul_1_1` over `double`', n(S, 'prod', 'mul_1_1', 'kairn'),
                 n(S, 'prod', 'mul_1_1', 'double')))
    print(ratio_table(names, runs, rows))

    print('\n## Q2: full kernel over its core\n')
    rows = []
    forms = (('full_sel', '(a) selects'), ('full_br', '(b) branch'), ('full_fabs', "(a') selects, `fabs`"),
             ('full_inl', "(b') branch, inline"))
    for k, chain in (('add_2_2', 'sum'), ('mul_2_2', 'prod')):
        for v, text in forms:
            rows.append(('scalar throughput, `%s`, %s' % (k, text), n(S, 'tp', k, v), n(S, 'tp', k, 'kairn')))
        for v, text in forms:
            rows.append(('scalar %s chain, `%s`, %s' % (chain, k, text), n(S, chain, k, v), n(S, chain, k, 'kairn')))
        rows.append(('packed throughput, `%s`, (a) blends' % k, n(P, 'tp', k, 'full_sel'), n(P, 'tp', k, 'kairn')))
        rows.append(('packed %s chain, `%s`, (a) blends' % (chain, k), n(P, chain, k, 'full_sel'), n(P, chain, k, 'kairn')))
    for v, text in forms:
        rows.append(('scalar Horner, 2 limbs, %s' % text, n(S, 'horner', 'mul_2_2+add_2_2', v),
                     n(S, 'horner', 'mul_2_2+add_2_2', 'kairn')))
    rows.append(('packed Horner, 2 limbs, (a) blends', n(P, 'horner', 'mul_2_2+add_2_2', 'full_sel'),
                 n(P, 'horner', 'mul_2_2+add_2_2', 'kairn')))
    print(ratio_table(names, runs, rows))
    print('\nForm (b) over form (a), scalar:\n')
    rows = []
    for kind, k in (('tp', 'add_2_2'), ('tp', 'mul_2_2'), ('sum', 'add_2_2'), ('prod', 'mul_2_2'),
                    ('horner', 'mul_2_2+add_2_2'), ('tp', 'ball_add_2'), ('tp', 'ball_mul_2'),
                    ('sum', 'ball_add_2'), ('prod', 'ball_mul_2'), ('horner', 'ball_mul_2+ball_add_2')):
        rows.append(('%s, `%s`' % ({'tp': 'throughput', 'sum': 'sum chain', 'prod': 'product chain',
                                    'horner': 'Horner'}[kind], k), n(S, kind, k, 'full_br'), n(S, kind, k, 'full_sel')))
    print(ratio_table(names, runs, rows))

    print('\n## Q3: Ball operations\n')
    rows = []
    for b in (S, P):
        rows += [('%s throughput, `ball_add_2` (ns)' % b, n(b, 'tp', 'ball_add_2', 'kairn')),
                 ('%s throughput, `add_2_2` (ns)' % b, n(b, 'tp', 'add_2_2', 'kairn')),
                 ('%s throughput, `ball_mul_2` (ns)' % b, n(b, 'tp', 'ball_mul_2', 'kairn')),
                 ('%s throughput, `mul_2_2` (ns)' % b, n(b, 'tp', 'mul_2_2', 'kairn')),
                 ('%s throughput, `ball_add_1` (ns)' % b, n(b, 'tp', 'ball_add_1', 'kairn')),
                 ('%s throughput, `ball_mul_1` (ns)' % b, n(b, 'tp', 'ball_mul_1', 'kairn')),
                 ('%s throughput, `double` addition (ns)' % b, n(b, 'tp', 'add_1_1', 'kairn' if b == P else 'double')),
                 ('%s throughput, `double` multiplication (ns)' % b, n(b, 'tp', 'mul_1_1', 'double'))]
    for kind, k, k1 in (('sum', 'ball_add_2', 'add_2_2'), ('prod', 'ball_mul_2', 'mul_2_2'),
                        ('horner', 'ball_mul_2+ball_add_2', 'mul_2_2+add_2_2')):
        rows += [('scalar %s chain, `%s` (ns)' % (kind, k), n(S, kind, k, 'kairn')),
                 ('scalar %s chain, `%s` (ns)' % (kind, k1), n(S, kind, k1, 'kairn'))]
    rows += [('scalar sum chain, `ball_add_1` (ns)', n(S, 'sum', 'ball_add_1', 'kairn')),
             ('scalar product chain, `ball_mul_1` (ns)', n(S, 'prod', 'ball_mul_1', 'kairn')),
             ('scalar Horner, `ball_mul_1+ball_add_1` (ns)', n(S, 'horner', 'ball_mul_1+ball_add_1', 'kairn')),
             ('scalar sum chain, `double` (ns)', n(S, 'sum', 'add_1_1', 'double')),
             ('scalar product chain, `double` (ns)', n(S, 'prod', 'mul_1_1', 'double')),
             ('scalar Horner, `double` (ns)', n(S, 'horner', 'mul_1_1+add_1_1', 'double'))]
    print(ns_table(names, runs, rows))
    print('\nRatios:\n')
    rows = []
    for b in (S, P):
        dadd = n(b, 'tp', 'add_1_1', 'kairn' if b == P else 'double')
        dmul = n(b, 'tp', 'mul_1_1', 'double')
        rows += [('%s throughput, `ball_add_2` / `add_2_2`' % b, n(b, 'tp', 'ball_add_2', 'kairn'), n(b, 'tp', 'add_2_2', 'kairn')),
                 ('%s throughput, `ball_mul_2` / `mul_2_2`' % b, n(b, 'tp', 'ball_mul_2', 'kairn'), n(b, 'tp', 'mul_2_2', 'kairn')),
                 ('%s throughput, `ball_add_1` / `double` addition' % b, n(b, 'tp', 'ball_add_1', 'kairn'), dadd),
                 ('%s throughput, `ball_mul_1` / `double` multiplication' % b, n(b, 'tp', 'ball_mul_1', 'kairn'), dmul),
                 ('%s throughput, `ball_add_2` / `double` addition' % b, n(b, 'tp', 'ball_add_2', 'kairn'), dadd),
                 ('%s throughput, `ball_mul_2` / `double` multiplication' % b, n(b, 'tp', 'ball_mul_2', 'kairn'), dmul)]
    rows += [('scalar sum chain, `ball_add_2` / `add_2_2`', n(S, 'sum', 'ball_add_2', 'kairn'), n(S, 'sum', 'add_2_2', 'kairn')),
             ('scalar product chain, `ball_mul_2` / `mul_2_2`', n(S, 'prod', 'ball_mul_2', 'kairn'), n(S, 'prod', 'mul_2_2', 'kairn')),
             ('scalar Horner, balls / 2 limbs', n(S, 'horner', 'ball_mul_2+ball_add_2', 'kairn'), n(S, 'horner', 'mul_2_2+add_2_2', 'kairn')),
             ('scalar sum chain, `ball_add_1` / `double`', n(S, 'sum', 'ball_add_1', 'kairn'), n(S, 'sum', 'add_1_1', 'double')),
             ('scalar product chain, `ball_mul_1` / `double`', n(S, 'prod', 'ball_mul_1', 'kairn'), n(S, 'prod', 'mul_1_1', 'double'))]
    for b in (S, P):
        for kind, k in (('tp', 'ball_add_2'), ('tp', 'ball_mul_2'), ('sum', 'ball_add_2'), ('prod', 'ball_mul_2'),
                        ('horner', 'ball_mul_2+ball_add_2')):
            rows.append(('%s %s, `%s`, full (a) / core' % (b, kind, k), n(b, kind, k, 'full_sel'), n(b, kind, k, 'kairn')))
    for kind, k in (('tp', 'ball_add_2'), ('tp', 'ball_mul_2'), ('sum', 'ball_add_2'), ('prod', 'ball_mul_2'),
                    ('horner', 'ball_mul_2+ball_add_2')):
        rows.append(('scalar %s, `%s`, full (b) / core' % (kind, k), n(S, kind, k, 'full_br'), n(S, kind, k, 'kairn')))
    print(ratio_table(names, runs, rows))

    print('\n## Q4: Kairn over the textbook baseline\n')
    rows = []
    for kind in ('tp', 'sum'):
        for k in ('add_2_2', 'add_fast_2_2'):
            text = '%s, `%s`' % ('throughput' if kind == 'tp' else 'sum chain', k)
            rows.append((text + ', core', n(S, kind, k, 'kairn'), n(S, kind, k, 'textbook')))
        for v, t in (('full_sel', '(a)'), ('full_br', '(b)')):
            rows.append(('%s, `add_2_2`, full %s' % ('throughput' if kind == 'tp' else 'sum chain', t),
                         n(S, kind, 'add_2_2', v), n(S, kind, 'add_2_2', 'textbook')))
    for kind in ('tp', 'prod'):
        text = 'throughput' if kind == 'tp' else 'product chain'
        rows.append(('%s, `mul_2_2`, core' % text, n(S, kind, 'mul_2_2', 'kairn'), n(S, kind, 'mul_2_2', 'textbook')))
        for v, t in (('full_sel', '(a)'), ('full_br', '(b)')):
            rows.append(('%s, `mul_2_2`, full %s' % (text, t), n(S, kind, 'mul_2_2', v), n(S, kind, 'mul_2_2', 'textbook')))
    rows.append(('Horner, core', n(S, 'horner', 'mul_2_2+add_2_2', 'kairn'), n(S, 'horner', 'mul_2_2+add_2_2', 'textbook')))
    for v, t in (('full_sel', '(a)'), ('full_br', '(b)')):
        rows.append(('Horner, full %s' % t, n(S, 'horner', 'mul_2_2+add_2_2', v), n(S, 'horner', 'mul_2_2+add_2_2', 'textbook')))
    print(ratio_table(names, runs, rows))
    print('\nMPFR at 106 bits over Kairn:\n')
    rows = [('throughput, addition / `add_2_2`', n(M, 'tp', 'add_2_2', 'mpfr'), n(S, 'tp', 'add_2_2', 'kairn')),
            ('throughput, multiplication / `mul_2_2`', n(M, 'tp', 'mul_2_2', 'mpfr'), n(S, 'tp', 'mul_2_2', 'kairn')),
            ('sum chain / `add_2_2`', n(M, 'sum', 'add_2_2', 'mpfr'), n(S, 'sum', 'add_2_2', 'kairn')),
            ('product chain / `mul_2_2`', n(M, 'prod', 'mul_2_2', 'mpfr'), n(S, 'prod', 'mul_2_2', 'kairn')),
            ('Horner / 2 limbs', n(M, 'horner', 'mul_2_2+add_2_2', 'mpfr'), n(S, 'horner', 'mul_2_2+add_2_2', 'kairn')),
            ('throughput, addition / `ball_add_2`', n(M, 'tp', 'add_2_2', 'mpfr'), n(S, 'tp', 'ball_add_2', 'kairn')),
            ('throughput, multiplication / `ball_mul_2`', n(M, 'tp', 'mul_2_2', 'mpfr'), n(S, 'tp', 'ball_mul_2', 'kairn'))]
    print(ratio_table(names, runs, rows))

    if asm:
        print('\n## Machine code of the throughput loops\n')
        funcs = ['kb_tp_mul_2_2__kairn', 'kb_tp_mul_2_2__plain', 'kb_tp_mul_2_2__full_sel', 'kb_tp_mul_2_2__full_br',
                 'kb_tp_mul_2_2__full_fabs', 'kb_tp_mul_2_2__full_inl',
                 'kb_tp_add_2_2__kairn', 'kb_tp_add_2_2__full_sel', 'kb_tp_add_2_2__full_br',
                 'kb_tp_add_2_2__full_fabs', 'kb_tp_add_2_2__full_inl',
                 'kb_tp_ball_add_2__kairn', 'kb_tp_ball_add_2__full_sel', 'kb_tp_ball_add_2__full_br',
                 'kb_tp_ball_mul_2__kairn']
        print(vector_table(names, runs, asm, funcs))

    print('\n## Every function\n')
    print(all_times(names, runs))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
