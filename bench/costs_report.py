#!/usr/bin/env python3
"""costs_report.py DIR: the tables of the checks of KAIRN_CHECKS and of MSVC's stack cookie on
docs/developer/results/costs-milestone1.md, from the JSON files that kairn-bench-costs-* and
kairn-bench write (bench/README.md, "Other costs").

A file is named MACHINE-COMPILER[-GS]-PROGRAM-LEVEL-rN.json: PROGRAM costs (KAIRN_CHECKS 0),
costs-checks (1) or api (kairn-bench --filter api/), GS gs or nogs (MSVC, with /GS or /GS-), N the
run. A ratio is of minimum times of two programs of the same run, which ran one after the other; a
cell is the lowest and highest value over the runs.
"""
import json
import os
import re
import statistics
import sys

NAME = re.compile(r'^(linux|macos|windows)-(gcc|clang|msvc)(?:-(gs|nogs))?-(costs-checks|costs|api)-(O0|O2|O3)-r(\d+)\.json$')
MACHINE = {'macos': 'M3', 'linux': 'Zen 2', 'windows': 'i5'}
COMPILER = {('macos', 'clang'): 'Apple clang', ('macos', 'gcc'): 'GCC 16', ('linux', 'gcc'): 'GCC 13',
            ('linux', 'clang'): 'Clang 18', ('windows', 'msvc'): 'MSVC'}
# The highest clock of each processor, in GHz, as its vendor gives it: a performance core of the
# M3 Max, the boost of the EPYC 7452, the turbo of a performance core of the i5-13500T. A time
# times this clock is the most cycles it can be.
MAX_GHZ = {'macos': 4.05, 'linux': 3.35, 'windows': 4.6}
ORDER = ['macos', 'linux', 'windows']


def level_name(machine, level):
    if machine == 'windows':
        return {'O0': '/Od', 'O2': '/O2'}[level]
    return '-' + level


def load(directory):
    runs = {}
    for f in sorted(os.listdir(directory)):
        m = NAME.match(f)
        if not m:
            continue
        machine, compiler, gs, prog, level, r = m.groups()
        with open(os.path.join(directory, f)) as fh:
            data = json.load(fh)
        times = {e['name']: e['ns_min'] for e in data['results']}
        sums = {e['name']: e.get('checksum') for e in data['results']}
        runs[(machine, compiler, gs or 'gs', prog, level, int(r))] = {'ns': times, 'sum': sums, 'data': data}
    return runs


def rng(values, fmt='%.2f'):
    lo, hi = min(values), max(values)
    a, b = fmt % lo, fmt % hi
    return a if a == b else '%s to %s' % (a, b)


def configs(runs, prog, gs='gs'):
    keys = sorted({(m, c, l) for (m, c, g, p, l, _) in runs if p == prog and g == gs},
                  key=lambda k: (ORDER.index(k[0]), k[1] != ('clang' if k[0] == 'macos' else 'gcc'), k[2]))
    return keys


def label(m, c, l):
    return '%s, %s %s' % (MACHINE[m], COMPILER[(m, c)], level_name(m, l))


def checks_tables(runs):
    print('### The environment check and the scale\n')
    print('| Configuration | `environment_ok()`, loop (ns) | cycles at the highest clock | `double` addition, loop (ns) | `double` addition, chain step (ns) | FMA, chain step (ns) |')
    print('|---|---|---|---|---|---|')
    for m, c, l in configs(runs, 'costs'):
        rs = sorted(r for (mm, cc, g, p, ll, r) in runs if (mm, cc, g, p, ll) == (m, c, 'gs', 'costs', l))
        get = lambda n: [runs[(m, c, 'gs', 'costs', l, r)]['ns'][n] for r in rs]
        env = get('env/loop')
        cyc = rng([e * MAX_GHZ[m] for e in env], '%.1f')
        print('| %s | %s | %s | %s | %s | %s |' % (label(m, c, l), rng(env, '%.3g'), cyc, rng(get('double/loop'), '%.3g'),
                                                  rng(get('double/sum'), '%.3g'), rng(get('fma/chain'), '%.3g')))
    print()
    names = [('add/loop', '`x + y`, loop'), ('add/sum', '`x + y`, chain'), ('mul/loop', '`x * y`, loop'),
             ('mul/prod', '`x * y`, chain'), ('k1/loop', 'one limb, `x + y`, loop'),
             ('k1/sum', 'one limb, `x + y`, chain'), ('k1/call', 'one limb, `x + y`, a call each')]
    print('### `KAIRN_CHECKS` 1 over 0\n')
    print('| Configuration | ' + ' | '.join(n for _, n in names) + ' |')
    print('|---|' + '---|' * len(names))
    mismatch = []
    for m, c, l in configs(runs, 'costs'):
        cells = []
        for key, _ in names:
            vals = []
            for (mm, cc, g, p, ll, r), v in runs.items():
                if (mm, cc, g, p, ll) != (m, c, 'gs', 'costs', l):
                    continue
                w = runs.get((m, c, 'gs', 'costs-checks', l, r))
                if w:
                    vals.append(w['ns'][key] / v['ns'][key])
                    if w['sum'][key] != v['sum'][key]:
                        mismatch.append((m, c, l, r, key))
            cells.append(rng(vals) if vals else '-')
        print('| %s | %s |' % (label(m, c, l), ' | '.join(cells)))
    print()
    print('### Times (ns), `KAIRN_CHECKS` 0 and 1\n')
    print('| Configuration | ' + ' | '.join(n for _, n in names) + ' |')
    print('|---|' + '---|' * len(names))
    for m, c, l in configs(runs, 'costs'):
        for prog in ('costs', 'costs-checks'):
            cells = []
            for key, _ in names:
                vals = [v['ns'][key] for (mm, cc, g, p, ll, r), v in runs.items() if (mm, cc, g, p, ll) == (m, c, 'gs', prog, l)]
                cells.append(rng(vals, '%.3g') if vals else '-')
            print('| %s, checks %d | %s |' % (label(m, c, l), prog == 'costs-checks', ' | '.join(cells)))
    print()
    print('Checksums of KAIRN_CHECKS 1 that differ from those of 0: %s\n' % (mismatch or 'none'))


def gs_tables(runs):
    have = [k for k in runs if k[2] == 'nogs']
    if not have:
        return
    print('### /GS over /GS-\n')
    names = ['k1/loop', 'k1/sum', 'k1/call', 'double/loop', 'double/call', 'add/loop', 'add/sum', 'mul/loop', 'mul/prod',
             'env/loop']
    print('| Program | ' + ' | '.join('`%s`' % n for n in names) + ' |')
    print('|---|' + '---|' * len(names))
    for prog in ('costs', 'costs-checks'):
        for l in ('O2', 'O0'):
            cells = []
            for n in names:
                vals = []
                for (m, c, g, p, ll, r), v in runs.items():
                    if (g, p, ll) == ('nogs', prog, l):
                        w = runs.get((m, c, 'gs', p, ll, r))
                        if w:
                            vals.append(w['ns'][n] / v['ns'][n])
                cells.append(rng(vals) if vals else '-')
            print('| kairn-bench-%s-%s | %s |' % (prog, level_name('windows', l), ' | '.join(cells)))
    print()
    ratios = {}
    for (m, c, g, p, ll, r), v in runs.items():
        if (g, p) == ('nogs', 'api'):
            w = runs.get((m, c, 'gs', p, ll, r))
            if w:
                for n, t in v['ns'].items():
                    ratios.setdefault(n, []).append(w['ns'][n] / t)
    if ratios:
        meds = sorted(statistics.median(v) for v in ratios.values())
        print('kairn-bench --filter api/, %d functions: /GS over /GS-, the median over the runs of each function: '
              'lowest %.3f, median %.3f, highest %.3f; beyond 3%%: %s\n' % (
                  len(meds), meds[0], statistics.median(meds), meds[-1],
                  ', '.join('%s %s' % (n, rng(v, '%.3f')) for n, v in sorted(ratios.items())
                            if abs(statistics.median(v) - 1) > 0.03) or 'none'))


def main():
    runs = load(sys.argv[1])
    checks_tables(runs)
    gs_tables(runs)


if __name__ == '__main__':
    main()
