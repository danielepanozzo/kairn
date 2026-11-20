#!/usr/bin/env python3
"""costs_report.py DIR [GSDIR]: the tables of the checks of KAIRN_CHECKS and of MSVC's stack cookie
on docs/developer/results/costs-milestone1.md, from the JSON files that kairn-bench-costs-* and
kairn-bench write in DIR, and those of gs_probe.py in GSDIR (bench/README.md, "Other costs").

A file is named MACHINE-COMPILER[-GS]-PROGRAM-LEVEL-rN.json: PROGRAM costs (KAIRN_CHECKS 0),
costs-checks (1) or api (kairn-bench --filter api/), GS gs or nogs (MSVC, with /GS or /GS-), N the
run. A ratio is of minimum times of two programs of the same run, which ran one after the other; a
cell is the lowest and highest value over the runs.

GSDIR/fix holds the measurements of the fix of the cookie: the probes and listings of gs_probe.py
named by the headers they were compiled against (before, A for f7ac43e, which passed every
one-limb parameter by const reference, H for 3672c2a, the operators alone), and the runs of
costs.cpp in times-A/{before,A} and times-H/{before,H}, each run of both one after the other.
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
            print('| `KAIRN_CHECKS` %d, `%s` | %s |' % (prog == 'costs-checks', level_name('windows', l), ' | '.join(cells)))
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


SHAPES = ['ret_add', 'ret_mul', 'add', 'mul', 'tp_add', 'tp_mul', 'sum', 'prod', 'dot', 'axpy', 'horner']
TYPES = [('double', '`double`'), ('e1', '`Expansion<double, 1>`'), ('e2', '`Expansion<double, 2>`'),
         ('b1', '`Ball<double, 1>`'), ('b2', '`Ball<double, 2>`'), ('p1', 'plain, `double limb[1]`'),
         ('p2', 'plain, `double limb[2]`'), ('pb2', 'plain, a ball of two limbs')]


def cell(f, g=None):
    """'cookie' or '-', with the instructions, and those of the /GS- build when given."""
    if f is None:
        return 'not found'
    text = ('**cookie**, ' if f['cookie_checks'] else '') + '%d' % f['instructions']
    if g is not None and g['instructions'] != f['instructions']:
        text += ' (%d)' % g['instructions']
    return text


def gs_probe_tables(directory):
    def get(name):
        path = os.path.join(directory, name)
        return json.load(open(path)) if os.path.exists(path) else None
    probe, fix, iso, objs = get('gs-probe.json'), get('gs-fix.json'), get('gs-isolate.json'), get('gs-objects.json')
    if probe:
        gs, nogs = probe['results']['/GS'], probe['results']['/GS-']
        print('### Which functions get the cookie (%s; instructions with /GS, and with /GS- where they differ)\n'
              % probe['compiler'])
        print('| Shape | ' + ' | '.join(t for _, t in TYPES) + ' |')
        print('|---|' + '---|' * len(TYPES))
        for s in SHAPES:
            cells = [cell(gs.get('gs_%s_%s' % (t, s)), nogs.get('gs_%s_%s' % (t, s))) for t, _ in TYPES]
            print('| `%s` | %s |' % (s, ' | '.join(cells)))
        n = sum(1 for f in gs.values() if f['cookie_checks'])
        print('\n%d of %d functions read the cookie with /GS, %d with /GS-.\n' % (
            n, len(gs), sum(1 for f in nogs.values() if f['cookie_checks'])))
    if fix:
        r = fix['results']['/GS, by reference']
        print('### Expansion<T, 1> passed by const reference (%s)\n' % fix.get('patch', ''))
        print('| Shape | `Expansion<double, 1>`, /GS, the headers as they are | the same, by const reference |')
        print('|---|---|---|')
        for s in SHAPES:
            print('| `%s` | %s | %s |' % (s, cell(probe['results']['/GS'].get('gs_e1_%s' % s)) if probe else '-',
                                         cell(r.get('gs_e1_%s' % s))))
        print('\nWith the change, %d of %d functions read the cookie.\n' % (
            sum(1 for f in r.values() if f['cookie_checks']), len(r)))
    if iso:
        print('### What triggers it (gs_isolate.cpp, /GS; instructions)\n')
        names = ['gs_add', 'gs_add_value', 'gs_dot', 'gs_tp_add']
        print('| Variant | ' + ' | '.join('`%s`' % n[3:] for n in names) + ' |')
        print('|---|' + '---|' * len(names))
        for v, what in iso['variants'].items():
            r = iso['results']['variant %s' % v]
            what = what.replace('<', '&lt;').replace('>', '&gt;')   # Expansion<T, 1> is no HTML tag
            print('| %s: %s | %s |' % (v, what, ' | '.join(cell(r.get(n)) for n in names)))
        print()
    if objs:
        for label, r in objs['results'].items():
            n = sum(1 for f in r.values() if f['cookie_checks'])
            print('%s: %d functions, %d read the cookie.' % (label, len(r), n))
        print()


# The fix (GSDIR/fix): before, A (every one-limb parameter by const reference, f7ac43e) and H (the
# hidden friends of Expansion<T, 1> alone, 3672c2a, what the headers have).
VARIANTS = ['before', 'A', 'H']
COMPILERS = [('macos', 'clang', 'M3, Apple clang'), ('macos', 'gcc', 'M3, GCC 16'), ('linux', 'gcc', 'Zen 2, GCC 13'),
             ('linux', 'clang', 'Zen 2, Clang 18')]


def fix_probe_table(probes, types, title):
    print(title + '\n')
    heads = ['%s, %s' % (t, v) for _, t in types for v in VARIANTS]
    print('| Shape | ' + ' | '.join(heads) + ' |')
    print('|---|' + '---|' * len(heads))
    for s in SHAPES:
        cells = []
        for tag, _ in types:
            for v in VARIANTS:
                r = probes[v]['results']
                n = 'gs_%s_%s' % (tag, s)
                cells.append(cell(r['/GS'].get(n), r['/GS-'].get(n)))
        print('| `%s` | %s |' % (s, ' | '.join(cells)))
    print()


def cookies(probe):
    """'n of m', and Kairn's own functions among them by their declaration."""
    r = probe['results']['/GS']
    ck = [n for n, f in r.items() if f['cookie_checks']]
    own = sorted(r[n].get('declaration', n) for n in ck if not n.startswith('gs_'))
    return '%d of %d' % (len(ck), len(r)), own


def fix_tables(directory):
    def get(name):
        path = os.path.join(directory, name)
        return json.load(open(path)) if os.path.exists(path) else None
    types = [('e1', '`Expansion<double, 1>`'), ('e1f', '`Expansion<float, 1>`')]
    for level, label in (('O2', '/O2'), ('Od', '/Od')):
        probes = {v: get('probe-%s-%s.json' % (level, v)) for v in VARIANTS}
        if all(probes.values()):
            fix_probe_table(probes, types, '### The fix, MSVC `%s` (%s; instructions with /GS, and with /GS- where '
                                           'they differ)' % (label, probes['H']['compiler']))
            for v in VARIANTS:
                n, own = cookies(probes[v])
                print('%s, %s: %s functions read the cookie%s.' % (label, v, n, (
                    '; of Kairn: ' + '; '.join(own)) if own and level == 'O2' else ''))
            print()
    for name, label in (('probe-O2Ob0-before.json', '/O2 /Ob0, before'), ('probe-O2Ob0-H.json', '/O2 /Ob0, H'),
                        ('probe-O2-H-safebuffers.json', '/O2, H with __declspec(safebuffers) on the operators'),
                        ('probe-O2-H-detail-by-reference.json',
                         '/O2, H with the seven functions of detail the operators call by const reference')):
        p = get(name)
        if p:
            n, own = cookies(p)
            e1 = ', '.join('%s %s' % (s, cell(p['results']['/GS'].get('gs_e1_' + s))) for s in ('add', 'sum', 'dot'))
            print('%s: %s functions read the cookie%s; `Expansion<double, 1>`: %s.' % (
                label, n, ('; of Kairn: ' + '; '.join(own)) if own else '', e1))
    print()
    # GCC and Clang: the probe's listings, each variant against before.
    print('### The fix, GCC and Clang (the 143 functions of the probe, against the headers before the fix)\n')
    print('| | ' + ' | '.join('%s, %s' % (lvl, v) for lvl in ('-O2', '-O0') for v in ('A', 'H')) + ' |')
    print('|---|' + '---|' * 4)
    for m, c, label in COMPILERS:
        cells = []
        for lvl in ('O2', 'O0'):
            b = get('listing-%s-%s-%s-before.json' % (m, c, lvl))
            for v in ('A', 'H'):
                x = get('listing-%s-%s-%s-%s.json' % (m, c, lvl, v))
                if not (b and x):
                    cells.append('-')
                    continue
                b_, x_ = b['results'], x['results']
                probe = [n for n in b_ if n.startswith('gs_')]
                diff = [n for n in probe if b_[n]['sha256'] != x_[n]['sha256']]
                if not diff:
                    cells.append('identical')
                    continue
                d = [x_[n]['instructions'] - b_[n]['instructions'] for n in diff]
                types_ = ', '.join(sorted(set(n.split('_')[1] for n in diff)))
                if min(d) == max(d) == 0:
                    cells.append('%d differ (%s), as many instructions' % (len(diff), types_))
                else:
                    cells.append('%d differ (%s): %+d to %+d instructions each' % (len(diff), types_, min(d), max(d)))
        print('| %s | %s |' % (label, ' | '.join(cells)))
    print()
    # The one-limb rows of costs.cpp: each variant over before, in the same runs.
    names = ['k1/loop', 'k1/sum', 'k1/call']
    print('### The fix, the one-limb rows of `costs.cpp` (the variant over before, in the same runs)\n')
    print('| Configuration | ' + ' | '.join('%s, %s' % (n, v) for v in ('A', 'H') for n in names) + ' |')
    print('|---|' + '---|' * (2 * len(names)))
    sets = {v: (load(os.path.join(directory, 'times-' + v, 'before')), load(os.path.join(directory, 'times-' + v, v)))
            for v in ('A', 'H')}
    keys = sorted({(m, c, g, p, l) for v in sets for (m, c, g, p, l, _) in sets[v][1] if p != 'api'},
                  key=lambda k: (ORDER.index(k[0]), k[1] != ('clang' if k[0] == 'macos' else 'gcc'), k[2], k[3], k[4]))
    for m, c, g, p, l in keys:
        cells = []
        for v in ('A', 'H'):
            before, after = sets[v]
            for n in names:
                vals = [after[(m, c, g, p, l, r)]['ns'][n] / before[(m, c, g, p, l, r)]['ns'][n]
                        for (mm, cc, gg, pp, ll, r) in after if (mm, cc, gg, pp, ll) == (m, c, g, p, l)
                        and (m, c, g, p, l, r) in before]
                cells.append(rng(vals) if vals else '-')
        gs = '' if m != 'windows' else (' /GS' if g == 'gs' else ' /GS-')
        print('| %s%s, `KAIRN_CHECKS` %d | %s |' % (label_of(m, c, l), gs, p == 'costs-checks', ' | '.join(cells)))
    print()
    print('### The fix, /GS over /GS- on the i5\n')
    names = ['k1/loop', 'k1/sum', 'k1/call', 'double/call', 'add/sum']
    print('| Headers, program | ' + ' | '.join('`%s`' % n for n in names) + ' |')
    print('|---|' + '---|' * len(names))
    for v, runs in (('before', sets['H'][0]), ('A', sets['A'][1]), ('H', sets['H'][1])):
        for prog in ('costs', 'costs-checks'):
            for l in ('O2', 'O0'):
                cells = []
                for n in names:
                    vals = [runs[('windows', 'msvc', 'gs', prog, l, r)]['ns'][n] / w['ns'][n]
                            for (m, c, g, p, ll, r), w in runs.items()
                            if (m, g, p, ll) == ('windows', 'nogs', prog, l) and ('windows', 'msvc', 'gs', prog, l, r) in runs]
                    cells.append(rng(vals) if vals else '-')
                print('| %s, `KAIRN_CHECKS` %d, `%s` | %s |' % (v, prog == 'costs-checks', level_name('windows', l),
                                                               ' | '.join(cells)))
    print()


def label_of(m, c, l):
    return '%s, %s %s' % (MACHINE[m], COMPILER[(m, c)], level_name(m, l))


def main():
    runs = load(sys.argv[1])
    checks_tables(runs)
    gs_tables(runs)
    if len(sys.argv) > 2:
        gs_probe_tables(sys.argv[2])
        if os.path.isdir(os.path.join(sys.argv[2], 'fix')):
            fix_tables(os.path.join(sys.argv[2], 'fix'))


if __name__ == '__main__':
    main()
