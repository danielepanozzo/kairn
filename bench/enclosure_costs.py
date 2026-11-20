#!/usr/bin/env python3
"""enclosure_costs.py: what the settings of KAIRN_ENCLOSURE_CODE cost and save (include/kairn/config.hpp;
docs/developer/results/costs-milestone2.md).

  enclosure_costs.py source N
      Prints a translation unit with N operations of Ball<double, 2> in straight-line code, in one
      function: a mix of +, -, * and the scaling by a double, in turn, each on two of the eight
      values computed last (chosen by a fixed seed), each result stored, so that none is dead.
  enclosure_costs.py compile --cxx CXX [--msvc] [--sizes 100,1000,10000] [--configs O2,O3]
                     [--settings inline,outlined,external] [--reps R] [--timeout S]
                     --workdir DIR --machine TEXT --commit TEXT --json FILE
      Writes those units into DIR and compiles each (nothing is linked) with each configuration and
      setting, R times in rounds over all of them (once for the units of the largest size), and
      records the wall time, the processor time and the peak memory of each compilation, and the
      size of the object; and the same for bench/definitions.cpp, the translation unit that defines
      the operations for the external setting, which a program compiles once.
  enclosure_costs.py report DIR
      The tables of docs/developer/results/costs-milestone2.md from DIR: compile-*.json, written by
      compile, and run-COMPILER-SETTING-LEVEL.json, written by kairn-bench-LEVEL,
      kairn-bench-outlined-LEVEL and kairn-bench-external-LEVEL (bench/README.md).

Measured as bench/compile_time.py measures (its measure()): the largest resident set of the
compiler and the processes it waits for. On a timeout only the process this script started is
terminated, and the compilation is recorded as such. Run from the repository root.
"""
import argparse
import datetime
import glob
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import compile_time  # noqa: E402

SETTINGS = {'inline': 'KAIRN_ENCLOSURE_CODE_INLINE', 'outlined': 'KAIRN_ENCLOSURE_CODE_OUTLINED',
            'external': 'KAIRN_ENCLOSURE_CODE_EXTERNAL'}
CONFIGS = {'gnu': {'O2': ['-O2', '-DNDEBUG'], 'O3': ['-O3', '-DNDEBUG']},
           'msvc': {'O2': ['/O2', '/DNDEBUG']}}


def source(n, seed=1):
    """A translation unit with n operations of Ball<double, 2> in one function."""
    rng = random.Random(seed)
    out = ['// Written by bench/enclosure_costs.py: %d operations of kairn::Ball<double, 2> in straight-line'
           % n,
           '// code, each result stored.',
           '#include <kairn/kairn.hpp>',
           '',
           'using B = kairn::Ball<double, 2>;',
           '',
           'void enclosure_unit(const B* in, const double* s, B* out) {']
    live = []
    for i in range(8):
        out.append('    const B v%d = in[%d];' % (i, i))
        live.append('v%d' % i)
    for i in range(n):
        a = live[-1 - rng.randrange(8)]
        b = live[-1 - rng.randrange(8)]
        op = i % 4
        if op == 0:
            expr = '%s + %s' % (a, b)
        elif op == 1:
            expr = '%s - %s' % (a, b)
        elif op == 2:
            expr = '%s * %s' % (a, b)
        else:
            expr = '%s * s[%d]' % (a, i % 8)
        out.append('    const B t%d = %s;' % (i, expr))
        out.append('    out[%d] = t%d;' % (i, i))
        live.append('t%d' % i)
    out.append('}')
    return '\n'.join(out) + '\n'


def cmd_source(args):
    sys.stdout.write(source(args.n))
    return 0


def compile_command(args, src, config, setting, obj):
    family = 'msvc' if args.msvc else 'gnu'
    define = 'KAIRN_ENCLOSURE_CODE=' + SETTINGS[setting]
    include = os.path.join(ROOT, 'include')
    if args.msvc:
        return [args.cxx, '/nologo', '/std:c++20', '/EHsc', '/arch:AVX2', '/I', include, '/D' + define] + \
            CONFIGS[family][config] + ['/c', src, '/Fo' + obj]
    isa = ['-mfma'] if compile_time.x86() else []
    return [args.cxx, '-std=c++20', '-I', include, '-D' + define] + isa + CONFIGS[family][config] + \
        ['-c', src, '-o', obj]


def cmd_compile(args):
    os.makedirs(args.workdir, exist_ok=True)
    sizes = [int(x) for x in args.sizes.split(',')]
    configs = args.configs.split(',')
    settings = args.settings.split(',')
    units = []
    for n in sizes:
        path = os.path.join(args.workdir, 'unit-%d.cpp' % n)
        with open(path, 'w') as f:
            f.write(source(n))
        for config in configs:
            for setting in settings:
                units.append(('unit', n, config, setting, path))
    for config in configs:
        units.append(('definitions', 0, config, 'external', os.path.join(HERE, 'definitions.cpp')))
    results = {}
    largest = max(sizes)
    for rep in range(args.reps):
        for kind, n, config, setting, path in units:
            if rep > 0 and n == largest:
                continue
            key = '%s %d %s %s' % (kind, n, config, setting)
            r = results.setdefault(key, {'kind': kind, 'operations': n, 'config': config, 'setting': setting,
                                         'wall': [], 'cpu': [], 'peak_mb': [], 'status': []})
            obj = os.path.join(args.workdir, '%s-%d-%s-%s.%s' % (kind, n, config, setting,
                                                                 'obj' if args.msvc else 'o'))
            cmd = compile_command(args, path, config, setting, obj)
            status, wall, cpu, peak, text = compile_time.measure(cmd, args.timeout, cwd=args.workdir)
            r['wall'].append(round(wall, 3))
            r['cpu'].append(round(cpu, 3))
            r['peak_mb'].append(round(peak, 1))
            r['status'].append(status)
            if status == 0:
                r['object_bytes'] = os.path.getsize(obj)
            else:
                r['error'] = text[-2000:]
            print('%-40s %8.2f s %8.1f MB %s' % (key, wall, peak, 'ok' if status == 0 else
                                                  ('TIMEOUT' if status == -1 else 'FAILED %s' % status)),
                  flush=True)
    data = {'schema': 1, 'what': 'enclosure compile', 'date': args.date or datetime.date.today().isoformat(),
            'commit': args.commit,
            'machine': {'description': args.machine, 'cpu': compile_time.cpu_brand()},
            'compiler': compile_time.compiler_version(argparse.Namespace(msvc=args.msvc, cxx=args.cxx, flags='')),
            'cxx': os.path.basename(args.cxx), 'timeout': args.timeout, 'reps': args.reps,
            'results': list(results.values())}
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w') as f:
        f.write(json.dumps(data, indent=1) + '\n')
    return 0 if all(s == 0 for r in results.values() for s in r['status']) else 1


def fmt_s(v):
    return '%.2f' % v if v < 10 else '%.1f' % v if v < 100 else '%.0f' % v


def cmd_report(args):
    for path in sorted(glob.glob(os.path.join(args.dir, 'compile-*.json'))):
        d = json.load(open(path))
        print('\n%s (%s), compile: the median wall time in seconds, and the peak memory in MB (of %d runs, '
              'one for the largest units); timeout %d s\n' % (d['compiler'], d['cxx'], d['reps'], d['timeout']))
        rows = [r for r in d['results'] if r['kind'] == 'unit']
        configs = sorted({r['config'] for r in rows})
        sizes = sorted({r['operations'] for r in rows})
        print('| Operations | ' + ' | '.join('%s %s' % (c, s) for c in configs for s in SETTINGS) + ' |')
        print('|---' * (1 + len(configs) * len(SETTINGS)) + '|')
        for n in sizes:
            cells = []
            for c in configs:
                for s in SETTINGS:
                    r = next((x for x in rows if x['operations'] == n and x['config'] == c and x['setting'] == s), None)
                    if r is None:
                        cells.append('')
                    elif any(st != 0 for st in r['status']):
                        cells.append('> %d s' % d['timeout'] if -1 in r['status'] else 'failed')
                    else:
                        w = sorted(r['wall'])[len(r['wall']) // 2]
                        m = sorted(r['peak_mb'])[len(r['peak_mb']) // 2]
                        cells.append('%s s, %d MB' % (fmt_s(w), round(m)))
            print('| %d | ' % n + ' | '.join(cells) + ' |')
        for r in d['results']:
            if r['kind'] == 'definitions':
                w = sorted(r['wall'])[len(r['wall']) // 2]
                print('\nbench/definitions.cpp (the external definitions), %s: %s s, %d MB, object %d bytes'
                      % (r['config'], fmt_s(w), round(sorted(r['peak_mb'])[len(r['peak_mb']) // 2]),
                         r.get('object_bytes', 0)))
        print('\nObject sizes in bytes: ' + '; '.join(
            '%d %s %s: %d' % (r['operations'], r['config'], r['setting'], r.get('object_bytes', 0)) for r in rows))
    runs = {}
    for path in sorted(glob.glob(os.path.join(args.dir, 'run-*.json'))):
        stem = os.path.basename(path)[len('run-'):-len('.json')]
        compiler, setting, level = stem.rsplit('-', 2)
        d = json.load(open(path))
        runs.setdefault((compiler, level), {})[setting] = {r['name']: r for r in d['results']}
    names = ['api/tp/ball_add_2/op', 'api/tp/ball_mul_2/op', 'api/tp/ball_scale_2/op', 'api/sum/ball_add_2/op',
             'api/prod/ball_mul_2/op', 'api/prod/ball_scale_2/op', 'api/horner/ball_2/op',
             'api/tp/ball_add_1/op', 'api/tp/ball_mul_1/op', 'api/sum/ball_add_1/op', 'api/prod/ball_mul_1/op',
             'api/horner/ball_1/op']
    for (compiler, level), by in sorted(runs.items()):
        print('\n%s %s, run time: the minimum time per operation or step in ns, inline, outlined, external\n'
              % (compiler, level))
        print('| Function | inline | outlined | external | outlined / inline | external / inline |')
        print('|---|---|---|---|---|---|')
        for name in names:
            if not all(name in by.get(s, {}) for s in SETTINGS):
                continue
            v = [by[s][name]['ns_min'] for s in SETTINGS]
            print('| `%s` | %.2f | %.2f | %.2f | %.2f | %.2f |' % (name, v[0], v[1], v[2], v[1] / v[0], v[2] / v[0]))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('source')
    s.add_argument('n', type=int)
    c = sub.add_parser('compile')
    c.add_argument('--cxx', required=True)
    c.add_argument('--msvc', action='store_true')
    c.add_argument('--sizes', default='100,1000,10000')
    c.add_argument('--configs', default='O2,O3')
    c.add_argument('--settings', default='inline,outlined,external')
    c.add_argument('--reps', type=int, default=3)
    c.add_argument('--timeout', type=int, default=3600)
    c.add_argument('--workdir', required=True)
    c.add_argument('--machine', required=True)
    c.add_argument('--commit', required=True)
    c.add_argument('--date')
    c.add_argument('--json', required=True)
    r = sub.add_parser('report')
    r.add_argument('dir')
    args = p.parse_args()
    return {'source': cmd_source, 'compile': cmd_compile, 'report': cmd_report}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
