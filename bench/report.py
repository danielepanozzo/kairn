#!/usr/bin/env python3
"""Prints the tables of docs/developer/results/bench-milestone1.md from stored measurements.

    python3 bench/report.py results/milestone1/bench

Reads every CONFIG-rN.json written by kairn-bench (one per repeated run of a configuration) and
every asm-CONFIG.json written by asm_summary.py in the directory, and prints Markdown: the
configurations, one table per question of the page, the machine code of the main loops, and the
time of every function on every configuration. A ratio is a ratio of minimum times within one run;
a cell shows the lowest and highest value of that ratio over the runs of the configuration (one
value when they agree to two decimals). Standard library only.
"""
import json
import os
import re
import sys

ORDER = ['mac-appleclang-O2', 'mac-appleclang-O3', 'mac-gcc16-O2', 'mac-gcc16-O3',
         'linux-gcc-O2', 'linux-gcc-O3', 'linux-clang-O2', 'linux-clang-O3', 'windows-msvc-O2']


def label(run):
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
    """configs: {config: [run, ...]} in ORDER; asm: {config: {function: summary}}."""
    configs = {}
    for f in sorted(os.listdir(directory)):
        m = re.match(r'^(?!asm-)(.+)-r(\d+)\.json$', f)
        if m:
            with open(os.path.join(directory, f)) as fp:
                configs.setdefault(m.group(1), []).append(json.load(fp))
    asm = {}
    for f in sorted(os.listdir(directory)):
        if f.startswith('asm-') and f.endswith('.json'):
            with open(os.path.join(directory, f)) as fp:
                a = json.load(fp)
            cols = a['columns']
            asm[f[4:-5]] = {name: {'instructions': r['instructions'],
                                   'loops': [dict(zip(cols, lp)) for lp in r['loops']]}
                            for name, r in a['functions'].items()}
    names = [n for n in ORDER if n in configs] + sorted(n for n in configs if n not in ORDER)
    return names, configs, asm


def times(run):
    return {r['name']: r for r in run['results']}


def fmt_ns(x):
    return '%.3g' % x if x < 100 else '%.0f' % x


def cell(values, fmt):
    if not values:
        return '—'
    lo, hi = min(values), max(values)
    a, b = fmt(lo), fmt(hi)
    return a if a == b else '%s–%s' % (a, b)


def ratios(runs, num, den):
    out = []
    for r in runs:
        t = times(r)
        if num in t and den in t:
            out.append(t[num]['ns_min'] / t[den]['ns_min'])
    return out


def header(names, configs, title):
    labels = [label(configs[n][0]) for n in names]
    return ['| %s | %s |' % (title, ' | '.join(labels)), '|---|' + '---:|' * len(names)]


def ratio_table(names, configs, rows, title='Operation'):
    """rows: (text, numerator name, denominator name)."""
    out = header(names, configs, title)
    for text, num, den in rows:
        out.append('| %s | %s |' % (text, ' | '.join(cell(ratios(configs[n], num, den), lambda x: '%.2f' % x)
                                                    for n in names)))
    return '\n'.join(out)


def ns_table(names, configs, rows, title='Operation (ns)'):
    """rows: (text, name): minimum time per operation."""
    out = header(names, configs, title)
    for text, name in rows:
        cells = []
        for n in names:
            v = [times(r)[name]['ns_min'] for r in configs[n] if name in times(r)]
            cells.append(cell(v, fmt_ns))
        out.append('| %s | %s |' % (text, ' | '.join(cells)))
    return '\n'.join(out)


def configurations(names, configs):
    out = ['| Configuration | Machine | Compiler | Flags | Scalar fix-up | Runs | Spread: median, worst | Date, commit |',
           '|---|---|---|---|---|---:|---|---|']
    for n in names:
        rs = configs[n]
        r = rs[0]
        meds, worsts = [], []
        for x in rs:
            s = sorted(y['ns_median'] / y['ns_min'] - 1 for y in x['results'])
            meds.append(100 * s[len(s) // 2])
            worsts.append(100 * s[-1])
        fix = {0: 'inline', 1: 'a function of its own'}.get(r.get('fixup_call'), '?')
        out.append('| %s | %s | %s | `%s` | %s | %d | %s%%, %s%% | %s, `%s` |' % (
            label(r), r['machine']['description'], r['compiler'], r['flags'], fix, len(rs),
            cell(meds, lambda x: '%.1f' % x), cell(worsts, lambda x: '%.0f' % x), r['date'],
            ', '.join(sorted(set(x['commit'] for x in rs)))))
    return '\n'.join(out)


def checks(names, configs):
    out = ['| Configuration | Functions checked bit for bit, failed | Full kernels: cases; selects vs generated, packed vs scalar; not canonical or against the statement |',
           '|---|---:|---|']
    for n in names:
        c = configs[n][0]['checks']
        full = '; '.join('`%s` %d: %d, %d; %d' % (f['kernel'], f['cases'], f['sel_vs_full'], f['packed_vs_full'],
                                                  f['not_canonical'] + f['against_statement'])
                         for f in c['full_forms'])
        failed = sum(r['checks']['failed'] for r in configs[n])
        out.append('| %s | %d, %d | %s |' % (label(configs[n][0]), c['compared'], failed, full))
    return '\n'.join(out)


def vector_table(names, configs, asm, funcs):
    """Vector width of the widest loop of each throughput function, and its selects, branches, calls."""
    out = header(names, configs, 'Function')
    out[1] = '|---|' + '---|' * len(names)
    for f in funcs:
        cells = []
        for n in names:
            a = asm.get(n, {}).get(f)
            if not a or not a['loops']:
                cells.append('—')
                continue
            main = max(a['loops'], key=lambda lp: (lp['vector_bits'], lp['instructions']))
            v = '%d-bit' % main['vector_bits'] if main['vector_bits'] else 'scalar'
            cells.append('%s, %d insns; %d fma, %d sel, %d br, %d call' % (
                v, main['instructions'], main['fma'], main['select'], main['branch'] - 1, main['call']))
        out.append('| `%s` | %s |' % (f, ' | '.join(cells)))
    return '\n'.join(out)


def all_times(names, configs):
    every = []
    for n in names:
        for r in configs[n]:
            for x in r['results']:
                if x['name'] not in every:
                    every.append(x['name'])
    out = header(names, configs, 'Function (ns)')
    for name in every:
        cells = []
        for n in names:
            v = [times(r)[name]['ns_min'] for r in configs[n] if name in times(r)]
            cells.append(cell(v, fmt_ns))
        out.append('| `%s` | %s |' % (name, ' | '.join(cells)))
    return '\n'.join(out)


KIND = {'tp': 'throughput', 'sum': 'sum chain', 'prod': 'product chain', 'horner': 'Horner'}


def main(argv):
    directory = argv[0] if argv else 'results/milestone1/bench'
    names, configs, asm = load(directory)
    S, P, A, F, M = 'scalar', 'packed', 'api', 'apif', 'mpfr'

    def n(backend, kind, kernel, variant):
        return '%s/%s/%s/%s' % (backend, kind, kernel, variant)

    def table(rows):
        print(ratio_table(names, configs, rows))

    print('### Configurations\n')
    print(configurations(names, configs))
    print('\n### Checks\n')
    print(checks(names, configs))

    print('\n### 1. Opaque product over plain product\n')
    rows = []
    for b in (S, P):
        for k in ('two_prod', 'mul_2_1', 'mul_2_2', 'ball_mul_2'):
            rows.append(('%s throughput, `%s`' % (b, k), n(b, 'tp', k, 'kairn'), n(b, 'tp', k, 'plain')))
    for k in ('two_prod', 'mul_2_1', 'mul_2_2', 'ball_mul_2'):
        rows.append(('scalar product chain, `%s`' % k, n(S, 'prod', k, 'kairn'), n(S, 'prod', k, 'plain')))
    for k in ('mul_2_2', 'ball_mul_2'):
        rows.append(('packed product chain, `%s`' % k, n(P, 'prod', k, 'kairn'), n(P, 'prod', k, 'plain')))
    for b in (S, P):
        for k in ('mul_2_2+add_2_2', 'ball_mul_2+ball_add_2'):
            rows.append(('%s Horner, `%s`' % (b, k), n(b, 'horner', k, 'kairn'), n(b, 'horner', k, 'plain')))
    rows.append(('scalar product chain, one limb: `mul_1_1` over `double`', n(S, 'prod', 'mul_1_1', 'kairn'),
                 n(S, 'prod', 'mul_1_1', 'double')))
    table(rows)

    print('\n### 2. The fix-up\n')
    print('Public operator over `kairn::finite::`, `Expansion<double, 2>` (arrays of numbers):\n')
    ops = (('tp', 'add_2_2', '`x + y`'), ('tp', 'add_2_1', '`x + a`'), ('tp', 'add_fast_2_2', '`add_fast(x, y)`'),
           ('tp', 'mul_2_2', '`x * y`'), ('tp', 'mul_2_1', '`x * a`'),
           ('sum', 'add_2_2', '`s = s + x[i]`'), ('sum', 'add_2_1', '`s = s + a[i]`'),
           ('sum', 'add_fast_2_2', '`s = add_fast(s, x[i])`'),
           ('prod', 'mul_2_2', '`p = p * x[i]`'), ('prod', 'mul_2_1', '`p = p * a[i]`'),
           ('horner', 'mul_2_2+add_2_2', '`p = p * h + c[i]`, two-limb `h`, `c`'),
           ('horner', 'mul_2_1+add_2_1', '`p = p * h + c[i]`, one-limb `h`, `c`'))
    table([('%s, %s' % (KIND[kind], text), n(A, kind, k, 'op'), n(A, kind, k, 'finite')) for kind, k, text in ops])
    print('\nGenerated full kernel over its core, separate arrays of limbs (`scalar`) and packed (`packed`);'
          ' the listing with selects (`full_sel`) for comparison:\n')
    rows = []
    for kind, k in (('tp', 'add_2_2'), ('tp', 'add_2_1'), ('tp', 'add_fast_2_2'), ('tp', 'mul_2_2'), ('tp', 'mul_2_1'),
                    ('sum', 'add_2_2'), ('sum', 'add_2_1'), ('prod', 'mul_2_2'), ('prod', 'mul_2_1'),
                    ('horner', 'mul_2_2+add_2_2')):
        rows.append(('scalar %s, `%s`' % (KIND[kind], k), n(S, kind, k, 'full'), n(S, kind, k, 'kairn')))
        if k in ('add_2_2', 'mul_2_2', 'mul_2_2+add_2_2'):
            rows.append(('scalar %s, `%s`, selects' % (KIND[kind], k), n(S, kind, k, 'full_sel'), n(S, kind, k, 'kairn')))
        rows.append(('packed %s, `%s`' % (KIND[kind], k), n(P, kind, k, 'full'), n(P, kind, k, 'kairn')))
    table(rows)

    print('\n### 3. Ball operations\n')
    print('Times, `double` limbs, public types (ns per operation or per step):\n')
    rows = []
    for kind, k, text in (('tp', 'ball_add_2', '`X + Y`, `Ball<double, 2>`'), ('tp', 'add_2_2', '`x + y`, `Expansion<double, 2>`'),
                          ('tp', 'ball_mul_2', '`X * Y`, `Ball<double, 2>`'), ('tp', 'mul_2_2', '`x * y`, `Expansion<double, 2>`'),
                          ('tp', 'ball_scale_2', '`X * a`, `Ball<double, 2>`'), ('tp', 'mul_2_1', '`x * a`, `Expansion<double, 2>`'),
                          ('tp', 'ball_neg_2', '`-X`, `Ball<double, 2>`'), ('tp', 'neg_2', '`-x`, `Expansion<double, 2>`'),
                          ('tp', 'ball_add_1', '`X + Y`, `Ball<double, 1>`'), ('tp', 'ball_mul_1', '`X * Y`, `Ball<double, 1>`'),
                          ('tp', 'ball_scale_1', '`X * a`, `Ball<double, 1>`'), ('tp', 'ball_neg_1', '`-X`, `Ball<double, 1>`')):
        rows.append(('%s, %s' % (KIND[kind], text), n(A, kind, k, 'op')))
    rows += [('throughput, `double` addition', n(A, 'tp', 'add_1_1', 'limb')),
             ('throughput, `double` multiplication', n(A, 'tp', 'mul_1_1', 'limb'))]
    for kind, k, k1 in (('sum', 'ball_add_2', 'add_2_2'), ('prod', 'ball_mul_2', 'mul_2_2'), ('prod', 'ball_scale_2', 'mul_2_1'),
                        ('horner', 'ball_mul_2+ball_add_2', 'mul_2_2+add_2_2')):
        rows += [('%s, `%s`' % (KIND[kind], k), n(A, kind, k, 'op')), ('%s, `%s`' % (KIND[kind], k1), n(A, kind, k1, 'op'))]
    for kind, k, k1 in (('sum', 'ball_add_1', 'add_1_1'), ('prod', 'ball_mul_1', 'mul_1_1'),
                        ('horner', 'ball_mul_1+ball_add_1', 'mul_1_1+add_1_1')):
        rows += [('%s, `%s`' % (KIND[kind], k), n(A, kind, k, 'op')), ('%s, `double`' % KIND[kind], n(A, kind, k1, 'limb'))]
    print(ns_table(names, configs, rows))
    print('\nBall over the center\'s operation, public types (`op` over `op`, and over `kairn::finite::`):\n')
    rows = []
    for kind, kb, kc, text in (('tp', 'ball_add_2', 'add_2_2', '`X + Y`'), ('tp', 'ball_mul_2', 'mul_2_2', '`X * Y`'),
                               ('tp', 'ball_scale_2', 'mul_2_1', '`X * a`'),
                               ('sum', 'ball_add_2', 'add_2_2', '`X + Y`'), ('prod', 'ball_mul_2', 'mul_2_2', '`X * Y`'),
                               ('prod', 'ball_scale_2', 'mul_2_1', '`X * a`'),
                               ('horner', 'ball_mul_2+ball_add_2', 'mul_2_2+add_2_2', '`X * H + C`')):
        rows.append(('2 limbs, %s, %s over the operator' % (KIND[kind], text), n(A, kind, kb, 'op'), n(A, kind, kc, 'op')))
        rows.append(('2 limbs, %s, %s over `finite::`' % (KIND[kind], text), n(A, kind, kb, 'op'), n(A, kind, kc, 'finite')))
    rows.append(('2 limbs, throughput, `-X` over `-x`', n(A, 'tp', 'ball_neg_2', 'op'), n(A, 'tp', 'neg_2', 'op')))
    for kind, kb, kc, v, text in (('tp', 'ball_add_1', 'add_1_1', 'limb', '`X + Y`'), ('tp', 'ball_mul_1', 'mul_1_1', 'limb', '`X * Y`'),
                                  ('tp', 'ball_scale_1', 'mul_1_1', 'limb', '`X * a`'), ('tp', 'ball_neg_1', 'neg_1', 'kairn', '`-X`'),
                                  ('sum', 'ball_add_1', 'add_1_1', 'limb', '`X + Y`'), ('prod', 'ball_mul_1', 'mul_1_1', 'limb', '`X * Y`'),
                                  ('prod', 'ball_scale_1', 'mul_1_1', 'limb', '`X * a`'),
                                  ('horner', 'ball_mul_1+ball_add_1', 'mul_1_1+add_1_1', 'limb', '`X * H + C`')):
        rows.append(('1 limb, %s, %s over `double`' % (KIND[kind], text), n(A, kind, kb, 'op'), n(A, kind, kc, v)))
    table(rows)
    print('\nPacked Ball kernels over the packed center kernels (full over full, and full over the core):\n')
    rows = []
    for kind, kb, kc in (('tp', 'ball_add_2', 'add_2_2'), ('tp', 'ball_mul_2', 'mul_2_2'), ('tp', 'ball_scale_2', 'mul_2_1'),
                         ('sum', 'ball_add_2', 'add_2_2'), ('prod', 'ball_mul_2', 'mul_2_2'), ('prod', 'ball_scale_2', 'mul_2_1'),
                         ('horner', 'ball_mul_2+ball_add_2', 'mul_2_2+add_2_2')):
        rows.append(('%s, `%s` over `%s`' % (KIND[kind], kb, kc), n(P, kind, kb, 'full'), n(P, kind, kc, 'full')))
        rows.append(('%s, `%s` over the core `%s`' % (KIND[kind], kb, kc), n(P, kind, kb, 'full'), n(P, kind, kc, 'kairn')))
    rows.append(('throughput, `ball_neg_2` over `neg_2`', n(P, 'tp', 'ball_neg_2', 'kairn'), n(P, 'tp', 'neg_2', 'kairn')))
    for kind, kb, kc, v in (('tp', 'ball_add_1', 'add_1_1', 'kairn'), ('tp', 'ball_mul_1', 'mul_1_1', 'double'),
                            ('tp', 'ball_scale_1', 'mul_1_1', 'double'), ('sum', 'ball_add_1', 'add_1_1', 'kairn'),
                            ('prod', 'ball_mul_1', 'mul_1_1', 'double'), ('prod', 'ball_scale_1', 'mul_1_1', 'double')):
        rows.append(('%s, `%s` over a `double` operation' % (KIND[kind], kb), n(P, kind, kb, 'full'), n(P, kind, kc, v)))
    rows.append(('throughput, `ball_neg_1` over a `double` negation', n(P, 'tp', 'ball_neg_1', 'kairn'), n(P, 'tp', 'neg_1', 'kairn')))
    table(rows)
    print('\nFull Ball kernels over their cores (public operator over the core on the same arrays; generated'
          ' kernels on separate arrays, scalar and packed; the listing with selects):\n')
    rows = []
    for kind, k in (('tp', 'ball_add_2'), ('tp', 'ball_mul_2'), ('tp', 'ball_scale_2'), ('tp', 'ball_add_1'), ('tp', 'ball_mul_1'),
                    ('tp', 'ball_scale_1'), ('sum', 'ball_add_2'), ('prod', 'ball_mul_2'), ('prod', 'ball_scale_2'),
                    ('sum', 'ball_add_1'), ('prod', 'ball_mul_1'), ('prod', 'ball_scale_1'),
                    ('horner', 'ball_mul_2+ball_add_2'), ('horner', 'ball_mul_1+ball_add_1')):
        rows.append(('public, %s, `%s`' % (KIND[kind], k), n(A, kind, k, 'op'), n(A, kind, k, 'kairn')))
        rows.append(('scalar, %s, `%s`' % (KIND[kind], k), n(S, kind, k, 'full'), n(S, kind, k, 'kairn')))
        if k in ('ball_add_2', 'ball_mul_2', 'ball_mul_2+ball_add_2'):
            rows.append(('scalar, %s, `%s`, selects' % (KIND[kind], k), n(S, kind, k, 'full_sel'), n(S, kind, k, 'kairn')))
        rows.append(('packed, %s, `%s`' % (KIND[kind], k), n(P, kind, k, 'full'), n(P, kind, k, 'kairn')))
    table(rows)

    print('\n### 4. Kairn over the textbook baseline\n')
    rows = []
    for kind, k, text in ops:
        rows.append(('`finite::`, %s, %s' % (KIND[kind], text), n(A, kind, k, 'finite'), n(A, kind, k, 'textbook')))
    for kind, k, text in ops:
        rows.append(('operator, %s, %s' % (KIND[kind], text), n(A, kind, k, 'op'), n(A, kind, k, 'textbook')))
    for kind, k in (('tp', 'add_2_2'), ('tp', 'add_fast_2_2'), ('tp', 'mul_2_2'), ('sum', 'add_2_2'), ('sum', 'add_fast_2_2'),
                    ('prod', 'mul_2_2'), ('horner', 'mul_2_2+add_2_2')):
        rows.append(('separate arrays, core, %s, `%s`' % (KIND[kind], k), n(S, kind, k, 'kairn'), n(S, kind, k, 'textbook')))
        if k != 'add_fast_2_2':
            rows.append(('separate arrays, full, %s, `%s`' % (KIND[kind], k), n(S, kind, k, 'full'), n(S, kind, k, 'textbook')))
    table(rows)
    print('\nMPFR at 106 bits over Kairn (`kairn::finite::` on the same numbers):\n')
    rows = [('throughput, addition', n(M, 'tp', 'add_2_2', 'mpfr'), n(A, 'tp', 'add_2_2', 'finite')),
            ('throughput, multiplication', n(M, 'tp', 'mul_2_2', 'mpfr'), n(A, 'tp', 'mul_2_2', 'finite')),
            ('sum chain', n(M, 'sum', 'add_2_2', 'mpfr'), n(A, 'sum', 'add_2_2', 'finite')),
            ('product chain', n(M, 'prod', 'mul_2_2', 'mpfr'), n(A, 'prod', 'mul_2_2', 'finite')),
            ('Horner', n(M, 'horner', 'mul_2_2+add_2_2', 'mpfr'), n(A, 'horner', 'mul_2_2+add_2_2', 'finite')),
            ('throughput, addition over `X + Y`', n(M, 'tp', 'add_2_2', 'mpfr'), n(A, 'tp', 'ball_add_2', 'op')),
            ('throughput, multiplication over `X * Y`', n(M, 'tp', 'mul_2_2', 'mpfr'), n(A, 'tp', 'ball_mul_2', 'op'))]
    table(rows)

    print('\n### 5. `float` limbs\n')
    rows = []
    for kind, k, text in ops:
        rows.append(('operator over `finite::`, %s, %s' % (KIND[kind], text), n(F, kind, k, 'op'), n(F, kind, k, 'finite')))
    for kind, k, text in ops:
        rows.append(('`finite::` over textbook, %s, %s' % (KIND[kind], text), n(F, kind, k, 'finite'), n(F, kind, k, 'textbook')))
    for kind, k, text in ops:
        rows.append(('operator over textbook, %s, %s' % (KIND[kind], text), n(F, kind, k, 'op'), n(F, kind, k, 'textbook')))
    for kind, kb, kc, text in (('tp', 'ball_add_2', 'add_2_2', '`X + Y`'), ('tp', 'ball_mul_2', 'mul_2_2', '`X * Y`'),
                               ('tp', 'ball_scale_2', 'mul_2_1', '`X * a`'), ('sum', 'ball_add_2', 'add_2_2', '`X + Y`'),
                               ('prod', 'ball_mul_2', 'mul_2_2', '`X * Y`'),
                               ('horner', 'ball_mul_2+ball_add_2', 'mul_2_2+add_2_2', '`X * H + C`')):
        rows.append(('`Ball<float, 2>` over the center, %s, %s' % (KIND[kind], text), n(F, kind, kb, 'op'), n(F, kind, kc, 'op')))
    for kind, kb, kc, text in (('tp', 'ball_add_1', 'add_1_1', '`X + Y`'), ('tp', 'ball_mul_1', 'mul_1_1', '`X * Y`'),
                               ('sum', 'ball_add_1', 'add_1_1', '`X + Y`'), ('prod', 'ball_mul_1', 'mul_1_1', '`X * Y`')):
        rows.append(('`Ball<float, 1>` over `float`, %s, %s' % (KIND[kind], text), n(F, kind, kb, 'op'), n(F, kind, kc, 'limb')))
    for kind, k in (('tp', 'add_2_2'), ('tp', 'mul_2_2'), ('tp', 'ball_add_2'), ('tp', 'ball_mul_2'),
                    ('sum', 'add_2_2'), ('prod', 'mul_2_2'), ('sum', 'ball_add_2'), ('prod', 'ball_mul_2')):
        rows.append(('`float` over `double` (time per operation), %s, `%s`' % (KIND[kind], k), n(F, kind, k, 'op'),
                     n(A, kind, k, 'op')))
    table(rows)
    print('\nTimes, `float` limbs, public operators (ns):\n')
    rows = [('%s, `%s`' % (KIND[kind], k), n(F, kind, k, 'op'))
            for kind, k in (('tp', 'add_2_2'), ('tp', 'mul_2_2'), ('tp', 'ball_add_2'), ('tp', 'ball_mul_2'),
                            ('sum', 'add_2_2'), ('prod', 'mul_2_2'), ('sum', 'ball_add_2'), ('prod', 'ball_mul_2'))]
    print(ns_table(names, configs, rows))

    if asm:
        print('\n### Machine code of the throughput loops\n')
        funcs = ['kb_a64_tp_add_2_2__finite', 'kb_a64_tp_add_2_2__op', 'kb_a64_tp_add_2_2__textbook',
                 'kb_a64_tp_mul_2_2__finite', 'kb_a64_tp_mul_2_2__op', 'kb_a64_tp_mul_2_2__textbook',
                 'kb_a64_tp_add_2_1__op', 'kb_a64_tp_mul_2_1__op',
                 'kb_a64_tp_ball_add_2__kairn', 'kb_a64_tp_ball_add_2__op', 'kb_a64_tp_ball_mul_2__kairn',
                 'kb_a64_tp_ball_mul_2__op', 'kb_a64_tp_ball_add_1__op', 'kb_a64_tp_ball_mul_1__op',
                 'kb_tp_add_2_2__kairn', 'kb_tp_add_2_2__full', 'kb_tp_add_2_2__full_sel',
                 'kb_tp_mul_2_2__kairn', 'kb_tp_mul_2_2__full', 'kb_tp_mul_2_2__full_sel',
                 'kb_tp_mul_2_2__plain', 'kb_tp_two_prod__kairn', 'kb_tp_two_prod__plain',
                 'kb_ptp_add_2_2__full', 'kb_ptp_mul_2_2__full', 'kb_ptp_ball_add_2__full', 'kb_ptp_ball_mul_2__full',
                 'kb_a32_tp_add_2_2__op', 'kb_a32_tp_mul_2_2__op', 'kb_a32_tp_ball_add_2__op', 'kb_a32_tp_ball_mul_2__op']
        print(vector_table(names, configs, asm, funcs))

    print('\n### Every function\n')
    print(all_times(names, configs))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
