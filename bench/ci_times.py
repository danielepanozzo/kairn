#!/usr/bin/env python3
"""The time of the quick tier on GitHub's hosted runners, from the workflow "Build and test".

    python3 bench/ci_times.py collect [--runs 12] [--full-runs 5] [--json results/milestone1/costs/ci/ci-build-and-test.json]
    python3 bench/ci_times.py tables results/milestone1/costs/ci/ci-build-and-test.json

collect reads, with the GitHub CLI (gh, logged in; read-only calls only), the last RUNS completed
runs of the workflow on the branch main, triggered by a push: for every job (one per platform and
compiler) its conclusion, its duration (started to completed, queueing excluded) and the duration
of each step, the ctest step ("Test") among them; and from each job's log, the line of the runner
image, how many tests ctest ran, its "Total Test time (real)" and its "Label Time Summary". For
each job it picks a representative run among those in which the job succeeded with the quick tier
as it is now (split from the full tier): the one whose ctest total is the median (the lower of
the two middle ones), since the hosted runners of one platform differ in speed from run to run;
for that run it keeps every test's name, status and seconds, in the order ctest started them.
Whole logs are not stored. Step times have the one-second resolution of the API; ctest's own
total is to a hundredth of a second.

collect also reads the last FULL_RUNS successful runs of the workflow "Full tier" on main and keeps,
per job, its "Label Time Summary". Two families run in both tiers on different numbers of cases
(crosscheck.compiled.*, label compiled, and api.oracle.*, label oracle): the median of a family's
time in each tier gives, by a straight line through the two, its fixed cost per test (starting
CMake, Python, the runners and the oracle) and its cost per case. The two tiers run on different
runners, so the line is only as good as the runners are alike; the range over the runs is printed.

tables prints Markdown: the step and job times per job over the runs, and per job on its
representative run the slowest tests, the time by label and by family of test, what the wall
time of the ctest step would become without each family and without a few sets of tests, and the
fixed cost per test of the cross-checks. ctest runs with --parallel 4 in the workflow, so the sum
of the tests' times exceeds the wall time; the wall time is estimated by replaying the tests in
the order ctest started them on four slots, each test on the first slot that frees up, which
reproduces ctest's own total to within a few percent (printed beside it). Standard library only.
"""
import argparse
import datetime
import json
import re
import statistics
import subprocess
import sys

REPO = 'danielepanozzo/kairn'
WORKFLOW = 'Build and test'
FULL_WORKFLOW = 'Full tier'
BRANCH = 'main'
# Cases per kernel and format of the families run in both tiers, quick and full: the defaults of
# KAIRN_CROSSCHECK_QUICK_CASES and KAIRN_CROSSCHECK_CASES (tests/CMakeLists.txt), and of
# KAIRN_API_QUICK_CASES and KAIRN_API_CASES (tests/api/CMakeLists.txt).
CASES = {'crosscheck.compiled.': (6000, 20000), 'api.oracle.': (2000, 10000)}
# Sets of tests whose removal from the quick tier tables() replays, beside each family alone.
WHATIF = [
    ('the Python tests of the tools that build nothing with the compiler (kairn-gen.test, '
     'crosscheck.guards, docs.reference.test, brute.driver.test)',
     ('kairn-gen.test', 'crosscheck.guards', 'docs.reference.test', 'brute.driver.test')),
    ('the same and kairn-oracle.selftest',
     ('kairn-gen.test', 'crosscheck.guards', 'docs.reference.test', 'brute.driver.test', 'kairn-oracle.selftest')),
    ('the same and crosscheck.compiled.*',
     ('kairn-gen.test', 'crosscheck.guards', 'docs.reference.test', 'brute.driver.test', 'kairn-oracle.selftest',
      'crosscheck.compiled.*')),
]
PARALLEL = 4   # ctest --parallel in .github/workflows/build.yml
STEPS = ('Configure', 'Build', 'Test')
JOB_ORDER = ['Linux x86-64, GCC', 'Linux x86-64, Clang', 'Linux arm64, GCC', 'Linux arm64, Clang',
             'macOS arm64, Apple clang', 'Windows x64, MSVC', 'Windows x64, clang-cl']

# Families of tests, by name (tests/CMakeLists.txt, tests/api/CMakeLists.txt): the first prefix
# that matches. A prefix ending in "." takes every test under it.
FAMILIES = [
    ('crosscheck.compiled.', 'the compiled runners against the oracle, per kernel and format'),
    ('crosscheck.guards', 'the guards of the cross-check driver'),
    ('api.oracle.', 'the public interface against the oracle, per kernel and format'),
    ('api.reject.', 'what must not compile'),
    ('api.boundary', 'the guard at the boundary of the public interface'),
    ('api.example.', 'the examples of the documentation'),
    ('api.k1.', 'Expansion<T, 1> against T, in assembly'),
    ('api.self_test.', 'self_test() under unsafe flags'),
    ('api.', 'other tests of the public interface (constexpr, environment)'),
    ('kairn-gen.test', "the generator's own tests, quick part"),
    ('kairn-gen.check', 'the generated files are up to date'),
    ('kairn-oracle.selftest', "the oracle's own tests, quick part"),
    ('kairn-oracle.claims', 'the oracle reads every claim'),
    ('docs.reference.test', "the reference generator's own tests"),
    ('docs.reference.check', 'the reference pages are up to date'),
    ('brute.', "the brute-force driver's own tests"),
    ('consume.', 'a project that uses Kairn through CMake'),
]

TIMESTAMP = re.compile(r'^\d{4}-\d\d-\d\dT[\d:.]+Z ?')
# "  5/272 Test   #7: NAME ......   Passed    3.14 sec", or "......***Timeout 600.05 sec".
DONE = re.compile(r'^\s*\d+/(\d+) Test\s+#(\d+): (\S+) \.*\s*(\*{3})?([A-Za-z][A-Za-z ()]*?)\s+([\d.]+) sec\s*$')
START = re.compile(r'^\s*Start\s+(\d+): (\S+)\s*$')
LABEL = re.compile(r'^(\S+)\s+=\s+([\d.]+) sec\*proc \((\d+) tests?\)\s*$')
TOTAL = re.compile(r'^Total Test time \(real\) =\s+([\d.]+) sec')


def gh(args, commands, raw=False):
    """Runs gh with args and returns its standard output; records the command (with ids as they are)."""
    commands.append('gh ' + ' '.join(a if ' ' not in a else '"%s"' % a for a in args))
    r = subprocess.run(['gh'] + args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('gh %s: %s' % (' '.join(args), r.stderr.strip()))
    return r.stdout if raw else json.loads(r.stdout)


def seconds(start, end):
    if not start or not end or start.startswith('0001') or end.startswith('0001'):
        return None
    f = '%Y-%m-%dT%H:%M:%SZ'
    return (datetime.datetime.strptime(end, f) - datetime.datetime.strptime(start, f)).total_seconds()


def family(name):
    for prefix, _ in FAMILIES:
        if name.startswith(prefix):
            return prefix + '*' if prefix.endswith('.') else prefix
    return name


def parse_log(text):
    """What the log of one job says about its ctest step: image, tests in start order, totals."""
    lines = [TIMESTAMP.sub('', l.rstrip('\r')) for l in text.splitlines()]
    out = {'image': None, 'tiered': False, 'total_real': None, 'count': None, 'labels': {}, 'tests': []}
    for i, l in enumerate(lines):
        if l.startswith('Image: ') and out['image'] is None:
            version = lines[i + 1][len('Version: '):] if i + 1 < len(lines) and lines[i + 1].startswith('Version: ') else ''
            out['image'] = (l[len('Image: '):] + ' ' + version).strip()
            break
    started, done, in_labels = [], {}, False
    for l in lines:
        if 'Kairn tests: the quick tier' in l and 'full tier' in l:
            out['tiered'] = True
        m = START.match(l)
        if m:
            started.append(m.group(2))
            continue
        m = DONE.match(l)
        if m:
            out['count'] = int(m.group(1))
            done[m.group(3)] = (m.group(5).strip(), float(m.group(6)))
            continue
        if l.startswith('Label Time Summary:'):
            in_labels = True
            continue
        if in_labels:
            m = LABEL.match(l.strip())
            if m:
                out['labels'][m.group(1)] = [float(m.group(2)), int(m.group(3))]
                continue
            in_labels = False
        m = TOTAL.match(l)
        if m:
            out['total_real'] = float(m.group(1))
    order = started + [n for n in done if n not in started]
    out['tests'] = [[n, done[n][0], done[n][1]] for n in order if n in done]
    out['started_not_done'] = [n for n in started if n not in done]
    return out


def collect(args):
    commands = []
    runs = gh(['run', 'list', '-R', REPO, '--workflow', WORKFLOW, '--branch', BRANCH, '--event', 'push',
               '--status', 'completed', '-L', str(args.runs), '--json',
               'databaseId,headSha,displayTitle,createdAt,updatedAt,conclusion,attempt'], commands)
    data = {'schema': 1, 'collected': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'repository': REPO, 'workflow': WORKFLOW, 'branch': BRANCH, 'event': 'push', 'ctest_parallel': PARALLEL,
            'commands': None, 'runs': [], 'representative': {}}
    candidates = {}   # job name: the runs in which it succeeded with the quick tier as it is now
    for run in runs:
        rid = run['databaseId']
        jobs = gh(['run', 'view', str(rid), '-R', REPO, '--json', 'jobs'], commands)['jobs']
        entry = {'run_id': rid, 'commit': run['headSha'][:7], 'title': run['displayTitle'],
                 'created': run['createdAt'], 'updated': run['updatedAt'], 'attempt': run['attempt'],
                 'conclusion': run['conclusion'], 'run_seconds': seconds(run['createdAt'], run['updatedAt']),
                 'jobs': []}
        for job in sorted(jobs, key=lambda j: JOB_ORDER.index(j['name']) if j['name'] in JOB_ORDER else 99):
            j = {'name': job['name'], 'job_id': job['databaseId'], 'conclusion': job['conclusion'],
                 'started': job['startedAt'], 'completed': job['completedAt'],
                 'seconds': seconds(job['startedAt'], job['completedAt']), 'steps': {}}
            for s in job['steps']:
                if s['name'] in STEPS:
                    j['steps'][s['name']] = {'conclusion': s['conclusion'], 'seconds': seconds(s['startedAt'], s['completedAt'])}
            try:
                log = parse_log(gh(['api', '--allow-escape-sequences',
                                    'repos/%s/actions/jobs/%d/logs' % (REPO, job['databaseId'])], commands, raw=True))
            except RuntimeError as e:
                log = None
                j['log_error'] = str(e)
            if log:
                j['image'] = log['image']
                j['tiered'] = log['tiered']
                j['ctest'] = {'total_real': log['total_real'], 'tests_run': len(log['tests']),
                              'tests_registered': log['count'],
                              'failed': [t for t in log['tests'] if t[1] != 'Passed'],
                              'not_finished': log['started_not_done'], 'labels': log['labels']}
                if job['conclusion'] == 'success' and log['tiered'] and log['total_real']:
                    candidates.setdefault(job['name'], []).append(
                        {'run_id': rid, 'commit': entry['commit'], 'total_real': log['total_real'], 'tests': log['tests']})
            entry['jobs'].append(j)
        data['runs'].append(entry)
        print('run %d %s %s: %d jobs' % (rid, entry['commit'], run['conclusion'], len(entry['jobs'])), file=sys.stderr)
    for name, c in candidates.items():
        c.sort(key=lambda x: x['total_real'])
        data['representative'][name] = dict(c[(len(c) - 1) // 2], of=len(c))
    # The full tier: the last FULL_RUNS successful runs, and the time of each label in each job.
    full = gh(['run', 'list', '-R', REPO, '--workflow', FULL_WORKFLOW, '--branch', BRANCH, '--event', 'push',
               '--status', 'success', '-L', str(args.full_runs), '--json', 'databaseId,headSha,createdAt'], commands)
    data['full_tier'] = {'workflow': FULL_WORKFLOW, 'cases': {k: list(v) for k, v in CASES.items()}, 'runs': []}
    for frun in full:
        fid = frun['databaseId']
        entry = {'run_id': fid, 'commit': frun['headSha'][:7], 'created': frun['createdAt'], 'jobs': {}}
        for job in gh(['run', 'view', str(fid), '-R', REPO, '--json', 'jobs'], commands)['jobs']:
            if job['name'] not in JOB_ORDER or job['conclusion'] != 'success':
                continue
            log = parse_log(gh(['api', '--allow-escape-sequences',
                                'repos/%s/actions/jobs/%d/logs' % (REPO, job['databaseId'])], commands, raw=True))
            entry['jobs'][job['name']] = {'job_id': job['databaseId'], 'seconds': seconds(job['startedAt'], job['completedAt']),
                                          'total_real': log['total_real'], 'image': log['image'], 'labels': log['labels']}
        data['full_tier']['runs'].append(entry)
        print('full tier run %d %s: %d jobs' % (fid, entry['commit'], len(entry['jobs'])), file=sys.stderr)
    # The commands, with the ids of each call replaced by a placeholder, once each.
    generic = []
    for c in commands:
        c = re.sub(r'run view \d+', 'run view RUN_ID', c)
        c = re.sub(r'jobs/\d+/logs', 'jobs/JOB_ID/logs', c)
        if c not in generic:
            generic.append(c)
    data['commands'] = generic
    text = json.dumps(data, indent=1, ensure_ascii=False)
    # Lists and objects of numbers and strings on one line each (a test is [name, status, seconds]).
    text = re.sub(r'\[\n\s+([^\[\]{}]*?)\n\s+\]', lambda m: '[' + re.sub(r',\n\s+', ', ', m.group(1)) + ']', text)
    text = re.sub(r'\{\n\s+([^\[\]{}]*?)\n\s+\}', lambda m: '{' + re.sub(r',\n\s+', ', ', m.group(1)) + '}', text)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    else:
        print(text)


# --- Tables -----------------------------------------------------------------------------------

def makespan(tests, slots=PARALLEL):
    """The wall time of the tests run in this order on `slots` slots, each on the first one free."""
    free = [0.0] * slots
    for t in tests:
        k = free.index(min(free))
        free[k] += t
    return max(free)


def spread(values):
    v = [x for x in values if x is not None]
    if not v:
        return '-'
    if len(v) == 1:
        return '%.0f' % v[0]
    return '%.0f / %.0f / %.0f' % (min(v), statistics.median(v), max(v))


def tables(path):
    data = json.load(open(path, encoding='utf-8'))
    runs = data['runs']
    print('Collected %s from %s, workflow "%s" on %s; %d runs, from %s to %s.\n' % (
        data['collected'], data['repository'], data['workflow'], data['branch'], len(runs),
        runs[-1]['created'][:16].replace('T', ' '), runs[0]['created'][:16].replace('T', ' ')))

    print('### Families of tests\n')
    print('| Family | What it is |')
    print('|---|---|')
    for prefix, text in FAMILIES:
        print('| `%s` | %s |' % (prefix + '*' if prefix.endswith('.') else prefix, text))

    print('\n### Runs\n')
    print('| Run | Commit | Created (UTC) | Conclusion | Run, wall (s) | Jobs | Quick tier split from the full tier |')
    print('|---|---|---|---|---:|---:|---|')
    for r in runs:
        tiered = {j.get('tiered') for j in r['jobs']}
        print('| %d | `%s` | %s | %s | %s | %d | %s |' % (
            r['run_id'], r['commit'], r['created'][:16].replace('T', ' '), r['conclusion'],
            '%.0f' % r['run_seconds'] if r['run_seconds'] else '-', len(r['jobs']),
            'yes' if tiered == {True} else 'no' if tiered == {False} else 'mixed or unknown'))

    for scope, keep in (('runs with the quick tier as it is now (split from the full tier)', True),
                        ('runs before the split (the quick tier held what is now the full tier)', False)):
        print('\n### Per job: %s\n' % scope)
        print('Seconds, min / median / max over the jobs that succeeded; ctest total is its "Total Test time (real)".\n')
        print('| Job | Jobs ok | Not ok | Configure | Build | Test step | ctest total | Whole job | Tests |')
        print('|---|---:|---|---|---|---|---|---|---|')
        for name in JOB_ORDER:
            ok, bad = [], []
            for r in runs:
                for j in r['jobs']:
                    if j['name'] != name or bool(j.get('tiered')) != keep:
                        continue
                    (ok if j['conclusion'] == 'success' else bad).append((r, j))
            if not ok and not bad:
                continue
            step = lambda s: spread([j['steps'].get(s, {}).get('seconds') for _, j in ok])
            counts = sorted({j.get('ctest', {}).get('tests_registered') for _, j in ok} - {None})
            def why(r, j):
                failed = j.get('ctest', {}).get('failed') or []
                step = next((s for s in STEPS if j['steps'].get(s, {}).get('conclusion') not in ('success', None)), None)
                text = '%s `%s`' % (j['conclusion'], r['commit'])
                if failed:
                    text += ' (%s)' % ', '.join('%s %s %.0f s' % tuple(t) for t in failed[:3])
                elif step:
                    text += ' (%s step %s)' % (step, j['steps'][step]['conclusion'])
                return text
            print('| %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
                name, len(ok), '; '.join(why(r, j) for r, j in bad) or '-',
                step('Configure'), step('Build'), step('Test'),
                spread([j.get('ctest', {}).get('total_real') for _, j in ok]),
                spread([j['seconds'] for _, j in ok]), ', '.join(map(str, counts)) or '-'))

    for name in JOB_ORDER:
        rep = data['representative'].get(name)
        if not rep:
            continue
        tests = rep['tests']
        total = sum(t[2] for t in tests)
        sim = makespan([t[2] for t in tests])
        image = next((j.get('image') for r in runs if r['run_id'] == rep['run_id'] for j in r['jobs'] if j['name'] == name), '')
        print('\n### %s: run %d (`%s`), image %s\n' % (name, rep['run_id'], rep['commit'], image))
        print('The run with the median ctest total of the %d in which this job succeeded with the quick tier '
              'as it is now.\n' % rep.get('of', 1))
        print('%d tests; ctest total (real) %.1f s; sum of the tests %.1f s; the replay on %d slots %.1f s.\n' % (
            len(tests), rep['total_real'] or 0, total, PARALLEL, sim))
        print('| Slowest tests | s | share of the sum |')
        print('|---|---:|---:|')
        for n, _, s in sorted(tests, key=lambda t: -t[2])[:10]:
            print('| `%s` | %.2f | %.1f%% |' % (n, s, 100 * s / total))
        labels = next((j.get('ctest', {}).get('labels') for r in runs if r['run_id'] == rep['run_id']
                       for j in r['jobs'] if j['name'] == name), {}) or {}
        if labels:
            print('\n| Label (a test has several) | Tests | s (sum) | share of the sum |')
            print('|---|---:|---:|---:|')
            for lab, (s, n) in sorted(labels.items(), key=lambda kv: -kv[1][0]):
                print('| %s | %d | %.1f | %.1f%% |' % (lab, n, s, 100 * s / total))
        fams = {}
        for n, _, s in tests:
            f = fams.setdefault(family(n), [0, 0.0, 0.0])
            f[0] += 1
            f[1] += s
            f[2] = max(f[2], s)
        print('\n| Family | Tests | s (sum) | share | longest | ctest wall time without it (replay) |')
        print('|---|---:|---:|---:|---:|---:|')
        for f, (n, s, mx) in sorted(fams.items(), key=lambda kv: -kv[1][1]):
            rest = [t[2] for t in tests if family(t[0]) != f]
            print('| `%s` | %d | %.1f | %.1f%% | %.2f | %.1f (-%.1f) |' % (f, n, s, 100 * s / total, mx, makespan(rest), sim - makespan(rest)))
        print('\n| Without | s (sum) left | longest left | ctest wall time (replay) |')
        print('|---|---:|---:|---:|')
        for text, names in WHATIF:
            rest = [t for t in tests if family(t[0]) not in names and t[0] not in names]
            print('| %s | %.1f | %.2f | %.1f (-%.1f) |' % (text, sum(t[2] for t in rest), max(t[2] for t in rest),
                                                         makespan([t[2] for t in rest]), sim - makespan([t[2] for t in rest])))
        fruns = [r for r in data.get('full_tier', {}).get('runs', []) if name in r['jobs']]
        if fruns:
            # Sums of a family's seconds, by its label, over the runs of each tier; a line through
            # the medians. The quick runs are those of the tiered layout.
            qruns = [j for r in runs for j in r['jobs'] if j['name'] == name and j.get('tiered')
                     and j['conclusion'] == 'success' and j.get('ctest', {}).get('labels')]
            print('\nThe same families on more cases in the full tier: the median over %d quick and %d full-tier '
                  'runs of their sum (by label), and a straight line through the two medians.\n' % (len(qruns), len(fruns)))
            print('| Family | Tests | Cases, quick / full | s (sum), quick / full: medians, and range | '
                  'fixed cost per test | s per 1000 cases per test | fixed share of the quick sum |')
            print('|---|---:|---|---|---:|---:|---:|')
            for prefix, (nq, nf) in CASES.items():
                lab = 'compiled' if prefix.startswith('crosscheck') else 'oracle'
                q = [j['ctest']['labels'][lab][0] for j in qruns if lab in j['ctest']['labels']]
                f = [r['jobs'][name]['labels'][lab][0] for r in fruns if lab in r['jobs'][name]['labels']]
                n = fruns[0]['jobs'][name]['labels'].get(lab, [0, 0])[1]
                if not q or not f or not n:
                    continue
                qm, fm = statistics.median(q), statistics.median(f)
                fixed = (qm * nf - fm * nq) / (nf - nq) / n
                slope = (fm - qm) / (nf - nq) / n
                print('| `%s*` | %d | %d / %d | %.0f / %.0f (%.0f-%.0f / %.0f-%.0f) | %.2f | %.3f | %.0f%% |' % (
                    prefix, n, nq, nf, qm, fm, min(q), max(q), min(f), max(f), fixed, 1000 * slope,
                    100 * fixed * n / qm))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--runs', type=int, default=12)
    c.add_argument('--full-runs', type=int, default=5)
    c.add_argument('--json')
    t = sub.add_parser('tables')
    t.add_argument('json')
    args = p.parse_args()
    if args.cmd == 'collect':
        collect(args)
    else:
        tables(args.json)


if __name__ == '__main__':
    main()
