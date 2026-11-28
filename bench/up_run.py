#!/usr/bin/env python3
"""up_run.py: the timed runs of kairn-bench-up (bench/README.md, "The round-up interval").

    python3 bench/up_run.py runs --program build/bench/kairn-bench-up-O2 --name linux-gcc-O2 \\
        --runs 4 --out results/upward/bench --machine "..." --commit C [--cpus 32-63] [--item main]
    python3 bench/up_run.py pairs --program build/bench/kairn-bench-up-O2 \\
        --other build/bench/kairn-bench-up-checks-O2 --name linux-gcc-O2 --runs 4 --out ... --item checks

`runs` makes RUNS kept runs of one program with the filter of ITEM (FILTERS below), each written as
ITEM-NAME-rN.json (main-NAME-rN.json for the item main). `pairs` makes RUNS pairs, the program and
the other one alternately on the same logical CPU, written as ITEM-NAME-c0-rN.json (the program)
and ITEM-NAME-c1-rN.json (the other): for the checked build, the program without and with
KAIRN_CHECKS.

On Linux each run is pinned (taskset, and --cpu) to the logical CPU of --cpus whose usage and its
SMT sibling's (CPU + --sibling, 64 on the 2 x 32-core machine of the results) were the lowest over
the 2 s before it, and the usage of the two is sampled every 5 s during the run from /proc/stat.
A run is set aside and made again (up to --attempts times per kept run) when the sibling was busy
(above --busy, 10%, in one sample or more), or when its spread at the median function (the median
over the functions of the median over the minimum of a function's samples) is above --spread
(1.05). Elsewhere (macOS, which has no affinity; Windows, unpinned) only the spread decides. With
--max-load L each attempt starts when the 1-minute load average is under L (os.getloadavg, so
not on Windows), after waiting up to 30 minutes. Every
attempt, kept or set aside, is listed in ATTEMPTS-NAME-ITEM.json with its CPU, the sibling's
busiest sample and its mean, the spread and the reason; each kept run's JSON gets the same record
as "run_conditions". Standard library only.
"""
import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time

# The filters of the items: what each kind of run times (bench/README.md).
DEFAULT = ('m2/tp/interval_add_1/kairn,m2/tp/interval_add_1/op,m2/tp/interval_add_1/fenv_loop,'
           'm2/tp/interval_sub_1/kairn,m2/tp/interval_sub_1/op,m2/tp/interval_sub_1/fenv_loop,'
           'm2/tp/interval_mul_1/kairn,m2/tp/interval_mul_1/op,m2/tp/interval_mul_1/fenv_loop,'
           'm2/sum/interval_add_1/kairn,m2/sum/interval_add_1/op,m2/sum/interval_add_1/fenv_loop,'
           'm2/prod/interval_mul_1/kairn,m2/prod/interval_mul_1/op,m2/prod/interval_mul_1/fenv_loop,'
           'm2/tp/horner_i1/kairn,m2/tp/horner_i1/op,m2/tp/horner_i1/fenv_loop,'
           'm2/lat/horner_i1/kairn,m2/lat/horner_i1/op,m2/lat/horner_i1/fenv_loop,'
           'm2/tp/pair_add_1/,m2/tp/plain4_mul_1/,'
           'm2f/tp/interval_add_1/kairn,m2f/tp/interval_add_1/op,m2f/tp/interval_add_1/fenv_loop,'
           'm2f/tp/interval_mul_1/kairn,m2f/tp/interval_mul_1/op,m2f/tp/interval_mul_1/fenv_loop,'
           'm2p/tp/interval_add_1/,m2p/tp/interval_mul_1/,m2s/tp/interval_add_1/,m2s/tp/interval_mul_1/')
FILTERS = {
    # Everything of the round-up interval, and its comparisons.
    'main': 'upw/,upwf/,upws/,upwa/,upwaf/,m2/tp/det3_,' + DEFAULT,
    # The checked build: the sum and product loops and chains, the arrays, the scopes, and the
    # default type's sum and product.
    'checks': ('upw/tp/interval_add_1/,upw/tp/interval_mul_1/,upw/sum/,upw/prod/,upwf/tp/,upwa/tp/,upwaf/tp/,'
               'upws/,m2/tp/interval_add_1/op,m2/tp/interval_mul_1/op,m2/sum/interval_add_1/op,'
               'm2/prod/interval_mul_1/op,m2f/tp/interval_add_1/op,m2f/tp/interval_mul_1/op'),
    # The short table of MSVC: the type's sum, product and product chain, the scopes, the default.
    'msvc': ('upw/tp/interval_add_1/,upw/tp/interval_mul_1/,upw/prod/interval_mul_1/,upw/sum/interval_add_1/,upws/,'
             'm2/tp/interval_add_1/op,m2/tp/interval_add_1/kairn,m2/tp/interval_add_1/fenv_loop,'
             'm2/tp/interval_mul_1/op,m2/tp/interval_mul_1/kairn,m2/tp/interval_mul_1/fenv_loop,'
             'm2/prod/interval_mul_1/op,m2/prod/interval_mul_1/kairn,m2/prod/interval_mul_1/fenv_loop,'
             'm2/sum/interval_add_1/op,m2/sum/interval_add_1/kairn,m2/sum/interval_add_1/fenv_loop'),
}


def cpu_times():
    """{cpu: (busy, total)} from /proc/stat, or {} where there is none."""
    out = {}
    try:
        with open('/proc/stat') as f:
            for line in f:
                if line.startswith('cpu') and line[3].isdigit():
                    p = line.split()
                    v = [int(x) for x in p[1:]]
                    idle = v[3] + (v[4] if len(v) > 4 else 0)
                    out[int(p[0][3:])] = (sum(v) - idle, sum(v))
    except OSError:
        pass
    return out


def usage(a, b, cpu):
    if cpu not in a or cpu not in b:
        return 0.0
    db, dt = b[cpu][0] - a[cpu][0], b[cpu][1] - a[cpu][1]
    return db / dt if dt > 0 else 0.0


def choose_cpu(cpus, sibling):
    a = cpu_times()
    if not a:
        return None
    time.sleep(2.0)
    b = cpu_times()
    best = None
    for c in cpus:
        u = max(usage(a, b, c), usage(a, b, c + sibling))
        if best is None or u < best[0]:
            best = (u, c)
    return best[1]


CHECK = re.compile(r'^up check: (?P<name>\S+): (?P<values>\d+) values: (?P<equal>\d+) equal to Kairn\'s default '
                   r'kernels, (?P<zero>\d+) zeros of the other sign, (?P<tighter>\d+) one number tighter below P; '
                   r'(?P<rn>\d+) differ from rounding to nearest$')
BYTES = re.compile(r'^up check: (?P<name>\S+): (?P<values>\d+) values equal to (?P<ref>\S+), byte for byte$')


def checks_of(log_path):
    """The counts of the checks that the run printed (up_check.cpp, up_default.cpp): per function
    [values, equal, zeros of the other sign, one number tighter, differing from rounding to nearest],
    or [values, reference] for a comparison byte for byte."""
    out = {}
    with open(log_path) as f:
        for line in f:
            line = line.rstrip('\n')
            m = CHECK.match(line)
            if m:
                out[m.group('name')] = [int(m.group(k)) for k in ('values', 'equal', 'zero', 'tighter', 'rn')]
                continue
            m = BYTES.match(line)
            if m:
                out[m.group('name')] = [int(m.group('values')), m.group('ref')]
    return out


def spread_of(result):
    within = sorted(x['ns_median'] / x['ns_min'] for x in result['results'] if x['ns_min'] > 0)
    return within[len(within) // 2] if within else 0.0


def run_once(args, program, cpu, path, item):
    """One run of program into path; returns (ok, conditions)."""
    cmd = [program, '--reps', str(args.reps), '--filter', FILTERS[item], '--machine', args.machine,
           '--commit', args.commit, '--json', path]
    if args.date:
        cmd += ['--date', args.date]
    if cpu is not None:
        cmd = ['taskset', '-c', str(cpu)] + cmd + ['--cpu', str(cpu)]
    log = open(path + '.log', 'w')
    start = cpu_times()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    samples = []
    last = start
    while True:
        try:
            proc.wait(timeout=5.0)
            break
        except subprocess.TimeoutExpired:
            pass
        now = cpu_times()
        if cpu is not None and now:
            samples.append((usage(last, now, cpu), usage(last, now, cpu + args.sibling)))
        last = now
        if len(samples) * 5 > args.timeout:
            proc.kill()   # the process this script started, and only it
            proc.wait()
            log.close()
            return False, {'reason': 'timeout'}
    log.close()
    cond = {'cpu': cpu, 'sibling': None if cpu is None else cpu + args.sibling, 'samples': len(samples)}
    if proc.returncode != 0 or not os.path.exists(path):
        cond['reason'] = 'exit status %d' % proc.returncode
        return False, cond
    with open(path) as f:
        result = json.load(f)
    cond['spread'] = round(spread_of(result), 4)
    if samples:
        sib = [s[1] for s in samples]
        cond['sibling_busy_max'] = round(max(sib), 3)
        cond['sibling_busy_mean'] = round(sum(sib) / len(sib), 3)
        cond['cpu_busy_mean'] = round(sum(s[0] for s in samples) / len(samples), 3)
    reasons = []
    if samples and cond['sibling_busy_max'] > args.busy:
        reasons.append('sibling busy (%.0f%% in its busiest sample)' % (100 * cond['sibling_busy_max']))
    if cond['spread'] > args.spread:
        reasons.append('spread %.3f at the median function' % cond['spread'])
    cond['reason'] = '; '.join(reasons) if reasons else 'kept'
    result['run_conditions'] = cond
    result['up_checks'] = checks_of(path + '.log')
    with open(path, 'w') as f:
        json.dump(result, f, indent=1)
    return not reasons, cond


def wait_for_load(limit, most=1800):
    """Wait, up to `most` seconds, until the 1-minute load average is under limit (--max-load)."""
    start = time.time()
    while os.getloadavg()[0] >= limit and time.time() - start < most:
        time.sleep(10)


def parse_cpus(text):
    out = []
    for part in text.split(','):
        if '-' in part:
            a, b = part.split('-')
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['runs', 'pairs'])
    ap.add_argument('--program', required=True)
    ap.add_argument('--other', help='pairs: the second program')
    ap.add_argument('--name', required=True, help='MACHINE-COMPILER-LEVEL')
    ap.add_argument('--item', default='main', choices=sorted(FILTERS))
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--first', type=int, default=1, help='the index of the first kept run')
    ap.add_argument('--attempts', type=int, default=3, help='attempts per kept run')
    ap.add_argument('--out', required=True)
    ap.add_argument('--machine', required=True)
    ap.add_argument('--commit', required=True)
    ap.add_argument('--date')
    ap.add_argument('--reps', type=int, default=31)
    ap.add_argument('--cpus', help='Linux: the logical CPUs to choose from, e.g. 32-63')
    ap.add_argument('--sibling', type=int, default=64)
    ap.add_argument('--busy', type=float, default=0.10)
    ap.add_argument('--spread', type=float, default=1.05)
    ap.add_argument('--timeout', type=float, default=1800, help='seconds per run')
    ap.add_argument('--max-load', type=float, help='start each attempt when the 1-minute load average is under this')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    pin = platform.system() == 'Linux' and args.cpus
    cpus = parse_cpus(args.cpus) if pin else []
    attempts_path = os.path.join(args.out, 'attempts-%s-%s.json' % (args.name, args.item))
    attempts = json.load(open(attempts_path)) if os.path.exists(attempts_path) else []
    kept = 0
    index = args.first
    while kept < args.runs:
        done = False
        for attempt in range(1, args.attempts + 1):
            if args.max_load:
                wait_for_load(args.max_load)
            cpu = choose_cpu(cpus, args.sibling) if pin else None
            if args.mode == 'runs':
                stem = '%s-%s-r%d' % (args.item, args.name, index)
                paths = [(args.program, os.path.join(args.out, stem + '.json'))]
            else:
                paths = [(args.program, os.path.join(args.out, '%s-%s-c0-r%d.json' % (args.item, args.name, index))),
                         (args.other, os.path.join(args.out, '%s-%s-c1-r%d.json' % (args.item, args.name, index)))]
            ok_all = True
            for program, path in paths:
                ok, cond = run_once(args, program, cpu, path, args.item)
                cond.update({'file': os.path.basename(path), 'attempt': attempt,
                             'time': time.strftime('%Y-%m-%d %H:%M:%S')})
                attempts.append(cond)
                print('%s: %s' % (os.path.basename(path), json.dumps(cond)), flush=True)
                ok_all = ok_all and ok
            with open(attempts_path, 'w') as f:
                json.dump(attempts, f, indent=1)
            if ok_all:
                done = True
                break
            for _, path in paths:   # set aside: keep its record, not its file
                for p in (path, path + '.log'):
                    if os.path.exists(p):
                        os.replace(p, p.replace('.json', '.setaside%d.json' % attempt))
        if not done:
            print('no kept run for index %d after %d attempts' % (index, args.attempts), file=sys.stderr)
            return 1
        kept += 1
        index += 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
