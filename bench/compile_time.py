#!/usr/bin/env python3
"""compile_time.py: what Kairn costs a client at compile time (bench/README.md, "Compile time").

  compile_time.py run --cxx CXX [--msvc] [--flags "..."] [--reps R] [--cpu N] [--units a,b]
                      [--configs O0,O2] --machine TEXT --commit TEXT --json FILE
      Compiles each translation unit of bench/compile_time/ (and the runners of gen/tests/) under
      each configuration, R times, in rounds over all of them, and records the wall time, the
      processor time and the peak memory of each compilation.
  compile_time.py per-kernel --cxx CXX [--msvc] [--flags "..."] [--config O2] [--reps R] ...
      The time of kernels_scalar.cpp and kernels_packed.cpp with one kernel at a time in the table,
      against the same file with an empty table: what each kernel adds.
  compile_time.py phases --cxx CXX [--msvc] [--flags "..."] [--config O2] ... --json FILE
      Where the time of each unit goes, from the compiler's own report: front end and back end
      (GCC -ftime-report, Clang -ftime-trace, MSVC /Bt+).
  compile_time.py kernels [--json FILE]
      The size of every generated kernel in include/kairn/gen/scalar.hpp: lines, operations, fused
      operations.
  compile_time.py report DIR
      The tables of docs/developer/results/costs-milestone1.md from the JSON files in DIR.

Every compilation has a timeout (--timeout, 600 s); on a timeout only the process this script
started is terminated, by its handle. Nothing is linked. Run from the repository root. On Linux and
Windows --cpu N pins this script, and so every compiler it starts, to logical processor N; macOS
has no affinity.
"""
import argparse
import ctypes
import datetime
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CT = os.path.join('bench', 'compile_time')
WINDOWS = os.name == 'nt'

# name: (source, uses the packed backend, what it is)
UNITS = {
    'empty': (os.path.join(CT, 'empty.cpp'), False, 'an empty translation unit'),
    'std_headers': (os.path.join(CT, 'std_headers.cpp'), False,
                    '<cmath> and the standard headers kairn.hpp includes'),
    'kairn_std': (os.path.join(CT, 'kairn_std.cpp'), False,
                  'the standard headers kairn.hpp includes, without <cmath>'),
    'iostream': (os.path.join(CT, 'iostream.cpp'), False, '<iostream> alone'),
    'include': (os.path.join(CT, 'include.cpp'), False, 'kairn/kairn.hpp alone'),
    'use_e2': (os.path.join(CT, 'use_e2.cpp'), False,
               'kairn.hpp, every operation of Expansion<double, 2> and Ball<double, 2>'),
    'use_all': (os.path.join(CT, 'use_all.cpp'), False,
                'kairn.hpp, every operation of Expansion and Ball, float and double, 1 and 2 limbs'),
    'self_test': (os.path.join(CT, 'self_test.cpp'), False, 'kairn.hpp and one call of kairn::self_test()'),
    'kernels_scalar': (os.path.join(CT, 'kernels_scalar.cpp'), False,
                       'gen/scalar.hpp, every kernel for double and float'),
    'kernels_packed': (os.path.join(CT, 'kernels_packed.cpp'), True,
                       'gen/avx2.hpp or gen/neon.hpp, every kernel for double and float'),
    'runner': (os.path.join('gen', 'tests', 'runner.cpp'), False,
               'gen/tests/runner.cpp, the scalar runner of the quick tier'),
    'packed_runner': (os.path.join('gen', 'tests', 'packed_runner.cpp'), True,
                      'gen/tests/packed_runner.cpp, the packed runner of the quick tier'),
}

# Configurations: the optimization level, with NDEBUG (so KAIRN_CHECKS is 0), and a debug build
# as CMake's Debug configuration makes it (no NDEBUG, so KAIRN_CHECKS is 1, and debug information;
# /Z7 rather than CMake's /Zi, which would start a PDB server).
CONFIGS = {
    'gnu': {'O0': ['-O0', '-DNDEBUG'], 'O2': ['-O2', '-DNDEBUG'], 'O3': ['-O3', '-DNDEBUG'],
            'debug': ['-O0', '-g']},
    'msvc': {'Od': ['/Od', '/DNDEBUG'], 'O2': ['/O2', '/DNDEBUG'], 'debug': ['/Od', '/Z7', '/RTC1']},
}


def x86():
    return platform.machine().lower() in ('x86_64', 'amd64', 'i386', 'i686')


def base_flags(args, packed):
    """The options of every compilation except the configuration's, the source and the output."""
    extra = args.flags.split() if args.flags else []
    if args.msvc:
        return ['/nologo', '/std:c++20', '/EHsc', '/arch:AVX2', '/I', 'include', '/I',
                os.path.join('gen', 'tests')] + extra
    isa = []
    if x86():
        isa = ['-mavx2', '-mfma'] if packed else ['-mfma']   # kairn::fma; avx2.hpp needs AVX2 too
    return ['-std=c++20', '-I', 'include', '-I', os.path.join('gen', 'tests')] + isa + extra


def command(args, unit_src, packed, config, obj, more=()):
    family = 'msvc' if args.msvc else 'gnu'
    flags = base_flags(args, packed) + CONFIGS[family][config] + list(more)
    if args.msvc:
        return [args.cxx] + flags + ['/c', unit_src, '/Fo' + obj]
    return [args.cxx] + flags + ['-c', unit_src, '-o', obj]


# --- Measuring one process ----------------------------------------------------------------------

if WINDOWS:
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]

    _psapi = ctypes.WinDLL('psapi')
    _kernel32 = ctypes.WinDLL('kernel32')
    _psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    _kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4

    def _ft(f):
        return ((f.dwHighDateTime << 32) | f.dwLowDateTime) * 1e-7


def _kill(p):
    """Kills p at a timeout; on POSIX first its children (pkill -P: the direct children of p only,
    which this script started through it)."""
    if not WINDOWS:
        subprocess.run(['pkill', '-KILL', '-P', str(p.pid)], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
    p.kill()


def measure(cmd, timeout, cwd=ROOT):
    """Runs cmd; returns (status, wall seconds, processor seconds, peak memory in MB, output).
    The peak is the largest resident set of the process and of the processes it waited for
    (GCC's driver runs cc1plus and as), or for MSVC the peak working set of cl.exe, which compiles
    in its own process. The output goes to a file, so that a long one cannot block the compiler."""
    with tempfile.TemporaryFile() as out:
        t0 = time.perf_counter()
        p = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT)
        # On a timeout, only the process this script started is terminated, by its handle, and on
        # POSIX first the processes it started (GCC's and Clang's drivers run the compiler proper
        # as a child, which killing the driver alone leaves running).
        timer = threading.Timer(timeout, _kill, (p,))
        timer.start()
        if WINDOWS:
            p.wait()
            wall = time.perf_counter() - t0
            timer.cancel()
            h = wintypes.HANDLE(int(p._handle))
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(pmc)
            peak = 0.0
            if _psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                peak = pmc.PeakWorkingSetSize / 1e6
            c, e, k, u = (wintypes.FILETIME() for _ in range(4))
            cpu = 0.0
            if _kernel32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(k), ctypes.byref(u)):
                cpu = _ft(k) + _ft(u)
            status = p.returncode
        else:
            _, st, ru = os.wait4(p.pid, 0)
            wall = time.perf_counter() - t0
            timer.cancel()
            status = p.returncode = os.waitstatus_to_exitcode(st)
            scale = 1e-6 if sys.platform == 'darwin' else 1e-3   # bytes on macOS, KiB on Linux
            cpu, peak = ru.ru_utime + ru.ru_stime, ru.ru_maxrss * scale
        out.seek(0)
        text = out.read().decode(errors='replace')
    if wall >= timeout:
        return -1, wall, cpu, peak, 'TIMEOUT\n' + text
    return status, wall, cpu, peak, text


def pin(cpu):
    if cpu is None:
        return 'not pinned'
    if sys.platform.startswith('linux'):
        os.sched_setaffinity(0, {cpu})
        return 'pinned to logical CPU %d' % cpu
    if WINDOWS:
        k = ctypes.WinDLL('kernel32')
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        ok = k.SetProcessAffinityMask(k.GetCurrentProcess(), 1 << cpu)
        return ('pinned to logical processor %d' % cpu) if ok else 'pinning FAILED'
    return 'not pinned (no affinity on macOS)'


def compiler_version(args):
    if args.msvc:
        r = subprocess.run([args.cxx], capture_output=True, text=True, timeout=60)
        return (r.stderr or r.stdout).strip().splitlines()[0]
    r = subprocess.run([args.cxx, '--version'] + (args.flags.split() if args.flags else []),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip().splitlines()[0]


def cpu_brand():
    try:
        if sys.platform == 'darwin':
            return subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True,
                                  text=True).stdout.strip()
        if sys.platform.startswith('linux'):
            for line in open('/proc/cpuinfo'):
                if line.startswith('model name'):
                    return line.split(':', 1)[1].strip()
        if WINDOWS:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            return winreg.QueryValueEx(k, 'ProcessorNameString')[0].strip()
    except OSError:
        pass
    return 'unknown'


def header(args, what):
    return {
        'schema': 1, 'what': what, 'date': args.date or datetime.date.today().isoformat(),
        'commit': args.commit, 'machine': {'description': args.machine, 'cpu': cpu_brand(),
                                           'os': platform.system(), 'arch': platform.machine()},
        'compiler': compiler_version(args), 'cxx': os.path.basename(args.cxx),
        'family': 'msvc' if args.msvc else 'gnu', 'flags': args.flags or '',
        'pinning': args.pinning, 'reps': args.reps,
    }


def write(args, data):
    text = json.dumps(data, indent=1) + '\n'
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, 'w') as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def summary(values):
    v = sorted(values)
    return {'min': v[0], 'median': statistics.median(v), 'max': v[-1]}


# --- run ----------------------------------------------------------------------------------------

def cmd_run(args):
    family = 'msvc' if args.msvc else 'gnu'
    configs = args.configs.split(',') if args.configs else list(CONFIGS[family])
    units = args.units.split(',') if args.units else list(UNITS)
    units = [u for u in units if args.packed or not UNITS[u][1]]
    work = args.workdir or tempfile.mkdtemp(prefix='kct-')
    os.makedirs(work, exist_ok=True)
    obj_ext = '.obj' if args.msvc else '.o'
    jobs = [(u, c) for u in units for c in configs]
    res = {(u, c): {'wall': [], 'cpu': [], 'peak_mb': []} for u, c in jobs}
    cmds = {}
    for rnd in range(args.reps + 1):   # round 0 warms the caches and is discarded
        for u, c in jobs:
            src, packed, _ = UNITS[u]
            obj = os.path.join(work, '%s-%s%s' % (u, c, obj_ext))
            cmd = command(args, src, packed, c, obj)
            cmds[(u, c)] = cmd
            st, wall, cpu, peak, text = measure(cmd, args.timeout)
            if st != 0:
                sys.exit('%s (%s) failed (%s):\n%s\n%s' % (u, c, st, ' '.join(cmd), text[-3000:]))
            if rnd:
                r = res[(u, c)]
                r['wall'].append(round(wall, 4))
                r['cpu'].append(round(cpu, 4))
                r['peak_mb'].append(round(peak, 1))
                r['object_bytes'] = os.path.getsize(obj)
        if rnd:
            print('round %d of %d done' % (rnd, args.reps), file=sys.stderr, flush=True)
    data = header(args, 'run')
    data['configs'] = {c: CONFIGS[family][c] for c in configs}
    data['units'] = {u: {'source': UNITS[u][0].replace('\\', '/'), 'packed': UNITS[u][1],
                         'description': UNITS[u][2]} for u in units}
    data['common_flags'] = {'scalar': base_flags(args, False), 'packed': base_flags(args, True)}
    data['results'] = []
    for u, c in jobs:
        r = res[(u, c)]
        data['results'].append({'unit': u, 'config': c, 'wall_s': r['wall'], 'cpu_s': r['cpu'],
                                'peak_mb': r['peak_mb'], 'object_bytes': r['object_bytes'],
                                'command': ' '.join(os.path.basename(x) if i == 0 else x
                                                    for i, x in enumerate(cmds[(u, c)]))})
        s = summary(r['wall'])
        print('%-15s %-6s %7.3f s (median %7.3f, max %7.3f)  %7.1f MB  %8d bytes' % (
            u, c, s['min'], s['median'], s['max'], max(r['peak_mb']), r['object_bytes']), file=sys.stderr)
    write(args, data)


# --- per-kernel ---------------------------------------------------------------------------------

def kernel_lines():
    """[(name, line)] of gen/tests/runner_kernels.inc."""
    out = []
    for line in open(os.path.join(ROOT, 'gen', 'tests', 'runner_kernels.inc')):
        m = re.match(r'KAIRN_RUNNER_KERNEL\((\w+),', line)
        if m:
            out.append((m.group(1), line))
    return out


def cmd_per_kernel(args):
    work = args.workdir or tempfile.mkdtemp(prefix='kct-')
    os.makedirs(work, exist_ok=True)
    kernels = kernel_lines()
    lists = {'none': ''}
    for i, (name, line) in enumerate(kernels):
        lists[name] = line
    for key, text in lists.items():
        with open(os.path.join(work, 'kct_%s.inc' % key), 'w') as f:
            f.write(text)
    backends = ['scalar'] + (['packed'] if args.packed else [])
    obj_ext = '.obj' if args.msvc else '.o'
    res = {}
    for rnd in range(args.reps + 1):
        for b in backends:
            src = os.path.join(CT, 'kernels_%s.cpp' % b)
            for key in lists:
                obj = os.path.join(work, 'k-%s-%s%s' % (b, key, obj_ext))
                define = ('/DKCT_KERNELS=kct_%s.inc' if args.msvc else '-DKCT_KERNELS=kct_%s.inc') % key
                inc = ['/I', work] if args.msvc else ['-I', work]
                cmd = command(args, src, b == 'packed', args.config, obj, inc + [define])
                st, wall, cpu, peak, text = measure(cmd, args.timeout)
                if st != 0:
                    sys.exit('%s %s failed:\n%s\n%s' % (b, key, ' '.join(cmd), text[-3000:]))
                if rnd:
                    res.setdefault((b, key), []).append(round(wall, 4))
        if rnd:
            print('round %d of %d done' % (rnd, args.reps), file=sys.stderr, flush=True)
    data = header(args, 'per-kernel')
    data['config'] = args.config
    data['config_flags'] = CONFIGS['msvc' if args.msvc else 'gnu'][args.config]
    data['common_flags'] = {'scalar': base_flags(args, False), 'packed': base_flags(args, True)}
    data['results'] = [{'backend': b, 'kernel': key, 'wall_s': res[(b, key)]} for b in backends for key in lists]
    write(args, data)
    for b in backends:
        base = min(res[(b, 'none')])
        rows = sorted(((min(res[(b, k)]) - base, k) for k in lists if k != 'none'), reverse=True)
        print('%s: empty table %.3f s; the ten largest increments:' % (b, base), file=sys.stderr)
        for d, k in rows[:10]:
            print('  %-20s %+.3f s' % (k, d), file=sys.stderr)


# --- phases -------------------------------------------------------------------------------------

def gnu_phases(text):
    """GCC -ftime-report: the wall seconds of each phase ('phase parsing', 'phase opt and generate',
    ...), of the total, and of the other timers above 5 ms. GCC 13 prints the columns usr, sys,
    wall and GGC; GCC 16 wall and GGC."""
    phases, others, wall = {}, {}, None
    for line in text.splitlines():
        if line.startswith('Time variable'):
            cols = [c for c in line[len('Time variable'):].split() if c != 'GGC']
            wall = cols.index('wall') if 'wall' in cols else None
            continue
        m = re.match(r'\s*([^:]+?)\s*:\s*(.*)$', line)
        if wall is None or not m:
            continue
        nums = re.findall(r'(\d+\.\d+)(?:\s*\(\s*\d+%\))?', m.group(2))
        if len(nums) <= wall:
            continue
        name, v = m.group(1).strip(), float(nums[wall])
        if name.startswith('phase ') or name == 'TOTAL':
            phases[name] = v
        elif v >= 0.005:
            others[name] = v
    phases.update({'(timer) ' + k: v for k, v in sorted(others.items(), key=lambda kv: -kv[1])[:8]})
    return phases


def clang_phases(trace_path):
    """Clang -ftime-trace: the total of Frontend and Backend, and the backend time of the largest
    functions (OptFunction, CodeGen Function), in seconds."""
    with open(trace_path) as f:
        data = json.load(f)
    totals, funcs = {}, {}
    for ev in data.get('traceEvents', []):
        name = ev.get('name', '')
        if name.startswith('Total '):
            totals[name[6:]] = ev.get('dur', 0) / 1e6
        if name in ('OptFunction', 'RunPass', 'CodeGen Function') and 'args' in ev:
            d = ev['args'].get('detail', '')
            if name != 'RunPass':
                funcs[d] = funcs.get(d, 0) + ev.get('dur', 0) / 1e6
    keep = ('Frontend', 'Backend', 'Source', 'ParseClass', 'InstantiateFunction', 'InstantiateClass',
            'PerformPendingInstantiations', 'CodeGen Function', 'OptFunction', 'OptModule', 'CodeGenPasses',
            'ExecuteCompiler')
    top = sorted(funcs.items(), key=lambda kv: -kv[1])[:10]
    return {k: round(v, 4) for k, v in totals.items() if k in keep}, [(k, round(v, 4)) for k, v in top]


def msvc_phases(text):
    """MSVC /Bt+: the time of c1xx.dll (front end) and c2.dll (back end)."""
    phases = {}
    for line in text.splitlines():
        m = re.search(r'time\((.*?\\(c1xx|c2)\.dll)\)=(\d+\.\d+)s', line)   # the path has "(x86)"
        if m:
            phases[m.group(2)] = float(m.group(3))
    return phases


def cmd_phases(args):
    family = 'msvc' if args.msvc else 'gnu'
    units = args.units.split(',') if args.units else list(UNITS)
    units = [u for u in units if args.packed or not UNITS[u][1]]
    work = args.workdir or tempfile.mkdtemp(prefix='kct-')
    os.makedirs(work, exist_ok=True)
    clang = 'clang' in compiler_version(args).lower()
    data = header(args, 'phases')
    data['config'] = args.config
    data['config_flags'] = CONFIGS[family][args.config]
    data['tool'] = '/Bt+' if args.msvc else ('-ftime-trace' if clang else '-ftime-report')
    data['results'] = []
    for u in units:
        src, packed, _ = UNITS[u]
        obj = os.path.join(work, '%s-phases%s' % (u, '.obj' if args.msvc else '.o'))
        if args.msvc:
            more = ['/Bt+']
        elif clang:
            more = ['-ftime-trace', '-ftime-trace-granularity=0']
        else:
            more = ['-ftime-report']
        best = None
        for _ in range(args.reps):
            st, wall, cpu, peak, text = measure(command(args, src, packed, args.config, obj, more), args.timeout)
            if st != 0:
                sys.exit('%s failed:\n%s' % (u, text[-3000:]))
            if args.msvc:
                ph, top = msvc_phases(text), []
            elif clang:
                ph, top = clang_phases(os.path.splitext(obj)[0] + '.json')
            else:
                ph, top = gnu_phases(text), []
            if best is None or wall < best['wall_s']:
                best = {'unit': u, 'wall_s': round(wall, 4), 'phases_s': ph, 'largest_functions_s': top}
        data['results'].append(best)
        print('%-15s %.3f s %s' % (u, best['wall_s'], json.dumps(best['phases_s'])), file=sys.stderr)
    write(args, data)


# --- kernels ------------------------------------------------------------------------------------

def kernel_sizes():
    """For each kernel of runner_kernels.inc: lines of scalar.hpp (both limb types, the fix-up
    function included), the value statements of its double function on the path that the inline
    fix-up takes (the core, the tests, the fix-up's selects), and how many are fused operations."""
    text = open(os.path.join(ROOT, 'include', 'kairn', 'gen', 'scalar.hpp')).read().splitlines()
    starts = [i for i, l in enumerate(text) if re.match(r'^// (\w+)\(.*\) -> ', l)]
    blocks = {}
    for j, s in enumerate(starts):
        name = re.match(r'^// (\w+)\(', text[s]).group(1)
        end = starts[j + 1] if j + 1 < len(starts) else len(text)
        blocks[name] = text[s:end]
    out = []
    for name, _ in kernel_lines():
        block = blocks[name]
        lines = sum(1 for l in block if l.strip() and not l.lstrip().startswith('//'))
        # The double function (not the one of namespace fixup), without the FIXUP_CALL branch and
        # without the variant for constant evaluation.
        body, inside, skip, ce = [], False, False, None
        for l in block:
            if re.match(r'^KAIRN_GEN_FORCEINLINE (constexpr )?void %s\(double' % name, l):
                inside = True
                continue
            if inside:
                if l.startswith('}'):
                    break
                if ce is not None:
                    if l.rstrip() == ce + '}':
                        ce = None
                    continue
                if l.strip() == 'if (__builtin_is_constant_evaluated()) {':
                    ce = l[:len(l) - len(l.lstrip())]
                    continue
                if l.strip() == '#if KAIRN_GEN_FIXUP_CALL' and body is not None:
                    skip = True
                    continue
                if l.strip() == '#else' and skip:
                    skip = False
                    continue
                if l.strip() == '#endif':
                    skip = False
                    continue
                if not skip:
                    body.append(l)
        stmts = [l for l in body if re.match(r'\s*const (double|bool|std::uint64_t) \w+ = ', l)]
        fused = sum(l.count('fma_rn(') for l in stmts)
        out.append({'kernel': name, 'lines': lines, 'operations': len(stmts), 'fused': fused})
    return out


def cmd_kernels(args):
    sizes = kernel_sizes()
    if args.json:
        with open(args.json, 'w') as f:
            json.dump({'schema': 1, 'what': 'kernel sizes', 'source': 'include/kairn/gen/scalar.hpp',
                       'kernels': sizes}, f, indent=1)
            f.write('\n')
    for k in sorted(sizes, key=lambda k: -k['operations']):
        print('%-20s %4d lines %4d operations %3d fused' % (k['kernel'], k['lines'], k['operations'], k['fused']))


# --- report -------------------------------------------------------------------------------------

def fmt_s(v):
    return '%.2f' % v if v >= 0.995 else '%.3f' % v


# The configurations of the results page, in its order: (file stem, column title).
COLUMNS = [('macos-clang', 'M3, Apple clang'), ('macos-gcc', 'M3, GCC 16'), ('linux-gcc', 'Zen 2, GCC 13'),
           ('linux-clang', 'Zen 2, Clang 18'), ('windows-msvc', 'i5, MSVC')]
LEVELS = [('O0', ('O0', 'Od'), '-O0 (MSVC /Od), NDEBUG'), ('O2', ('O2',), '-O2 (/O2), NDEBUG'),
          ('O3', ('O3',), '-O3, NDEBUG'), ('debug', ('debug',), 'debug: -O0 -g (MSVC /Od /Z7 /RTC1), no NDEBUG')]
BASE_UNITS = ['empty', 'kairn_std', 'std_headers', 'iostream', 'include']
API_UNITS = ['include', 'use_e2', 'use_all', 'self_test', 'kernels_scalar', 'kernels_packed', 'runner', 'packed_runner']


def cmd_report(args):
    """Markdown tables: the baselines (from the baselines run where there is one), the time of each
    unit per level and configuration, the peak memory, the spread, the kernels and the phases."""
    def get(stem, what):
        path = os.path.join(args.dir, '%s-%s.json' % (what, stem))
        return json.load(open(path)) if os.path.exists(path) else None

    def table(data, unit, config):
        if not data:
            return None
        for r in data['results']:
            if r['unit'] == unit and r['config'] in config:
                return r
        return None

    main_runs = {s: get(s, 'compile') for s, _ in COLUMNS}
    base_runs = {s: get(s + '-baselines', 'compile') or main_runs[s] for s, _ in COLUMNS}
    cols = [(s, t) for s, t in COLUMNS if main_runs[s]]

    print('#### Baselines, at -O2 (s; peak MB)\n')
    print('| Unit | ' + ' | '.join(t for _, t in cols) + ' |')
    print('|---|' + '---:|' * len(cols))
    for u in BASE_UNITS:
        cells = []
        for s, _ in cols:
            r = table(base_runs[s], u, ('O2',))
            cells.append('%s; %d' % (fmt_s(min(r['wall_s'])), round(max(r['peak_mb']))) if r else '-')
        print('| `%s` | %s |' % (u, ' | '.join(cells)))
    print()
    for _, names, title in LEVELS:
        print('#### %s: time (s)\n' % title)
        print('| Unit | ' + ' | '.join(t for _, t in cols) + ' |')
        print('|---|' + '---:|' * len(cols))
        for u in API_UNITS:
            cells = []
            for s, _ in cols:
                r = table(main_runs[s], u, names)
                cells.append(fmt_s(min(r['wall_s'])) if r else '-')
            print('| `%s` | %s |' % (u, ' | '.join(cells)))
        print()
    for _, names, title in (LEVELS[1], LEVELS[3]):
        print('#### %s: peak memory (MB)\n' % title)
        print('| Unit | ' + ' | '.join(t for _, t in cols) + ' |')
        print('|---|' + '---:|' * len(cols))
        for u in API_UNITS:
            cells = []
            for s, _ in cols:
                r = table(main_runs[s], u, names)
                cells.append('%d' % round(max(r['peak_mb'])) if r else '-')
            print('| `%s` | %s |' % (u, ' | '.join(cells)))
        print()
    print('#### Spread: median and maximum over the minimum, over every unit and level\n')
    print('| Configuration | Runs | Median over minimum | Maximum over minimum |')
    print('|---|---|---|---|')
    for s, t in cols:
        d = main_runs[s]
        med = [statistics.median(r['wall_s']) / min(r['wall_s']) - 1 for r in d['results']]
        mx = [max(r['wall_s']) / min(r['wall_s']) - 1 for r in d['results']]
        print('| %s | %d | %d to %d%% (median %d%%) | %d to %d%% |' % (
            t, d['reps'], round(100 * min(med)), round(100 * max(med)), round(100 * statistics.median(med)),
            round(100 * min(mx)), round(100 * max(mx))))
    print()
    # The kernels: the size of each, and what it adds to kernels_scalar and kernels_packed alone.
    sizes = get_sizes(args.dir)
    pk = {s: get(s, 'perkernel') for s, _ in COLUMNS}
    pcols = [(s, t) for s, t in COLUMNS if pk[s]]
    if pk and sizes:
        for backend in ('scalar', 'packed'):
            print('#### What one kernel adds to `kernels_%s` alone, at -O2 (ms)\n' % backend)
            print('| Kernel | Operations | Lines | ' + ' | '.join(t for _, t in pcols) + ' |')
            print('|---|---:|---:|' + '---:|' * len(pcols))
            order = sorted(sizes, key=lambda k: (-k['operations'], k['kernel']))
            pick = order[:10] + [k for k in order if k['kernel'] == 'add_1_1']
            base = {}
            for s, _ in pcols:
                rs = {r['kernel']: min(r['wall_s']) for r in pk[s]['results'] if r['backend'] == backend}
                base[s] = rs
            for k in pick:
                cells = ['%+.0f' % (1000 * (base[s][k['kernel']] - base[s]['none'])) if k['kernel'] in base[s] else '-'
                         for s, _ in pcols]
                print('| `%s` | %d | %d | %s |' % (k['kernel'], k['operations'], k['lines'], ' | '.join(cells)))
            cells = []
            for s, _ in pcols:
                main = main_runs.get(s)
                r = table(main, 'kernels_%s' % backend, ('O2',))
                cells.append('%+.0f' % (1000 * (min(r['wall_s']) - base[s]['none'])) if r else '-')
            total_ops = sum(k['operations'] for k in sizes)
            total_lines = sum(k['lines'] for k in sizes)
            print('| all %d (the unit, from the main run) | %d | %d | %s |' % (len(sizes), total_ops, total_lines,
                                                                            ' | '.join(cells)))
            cells = ['%.0f' % (1000 * base[s]['none']) for s, _ in pcols]
            print('| none (the empty table) | | | %s |' % ' | '.join(cells))
            # The five largest kernels by operations: their share of the sum of the 63 increments,
            # and of that sum less 63 times the increment of the smallest kernel (add_1_1), which
            # is roughly what any kernel costs, the instantiation of its two functions.
            top5 = [k['kernel'] for k in order[:5]]
            cells = []
            for s, _ in pcols:
                inc = {k: v - base[s]['none'] for k, v in base[s].items() if k != 'none'}
                total, floor = sum(inc.values()), inc.get('add_1_1', 0.0)
                t5 = sum(inc[k] for k in top5)
                cells.append('%.0f%%, %.0f%%' % (100 * t5 / total, 100 * (t5 - 5 * floor) / (total - len(inc) * floor)))
            print('| the five largest: share of the sum of the increments; the same less the smallest\'s | | | %s |'
                  % ' | '.join(cells))
            print()
    ph = {s: get(s, 'phases') for s, _ in COLUMNS}
    for s, t in COLUMNS:
        d = ph[s]
        if not d:
            continue
        print('#### Phases, %s, %s (%s; s)\n' % (t, d['config'], d['tool']))
        keys = []
        for r in d['results']:
            for k in r['phases_s']:
                if k not in keys:
                    keys.append(k)
        keys = [k for k in keys if not k.startswith('(timer)')][:8]
        print('| Unit | wall | ' + ' | '.join(keys) + ' |')
        print('|---|---:|' + '---:|' * len(keys))
        for r in d['results']:
            print('| `%s` | %s | %s |' % (r['unit'], fmt_s(r['wall_s']),
                                         ' | '.join(fmt_s(r['phases_s'][k]) if k in r['phases_s'] else '-' for k in keys)))
        print()


def get_sizes(directory):
    path = os.path.join(directory, 'kernel-sizes.json')
    if os.path.exists(path):
        return json.load(open(path))['kernels']
    return kernel_sizes()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='what', required=True)
    for name in ('run', 'per-kernel', 'phases'):
        s = sub.add_parser(name)
        s.add_argument('--cxx', required=True)
        s.add_argument('--msvc', action='store_true', help='the compiler takes MSVC-style options')
        s.add_argument('--flags', default='', help='more options for every compilation')
        s.add_argument('--reps', type=int, default=5)
        s.add_argument('--cpu', type=int)
        s.add_argument('--units')
        s.add_argument('--configs')
        s.add_argument('--config', default='O2')
        s.add_argument('--no-packed', dest='packed', action='store_false')
        s.add_argument('--timeout', type=float, default=600)
        s.add_argument('--machine', default='')
        s.add_argument('--commit', default='unknown')
        s.add_argument('--date')
        s.add_argument('--workdir')
        s.add_argument('--json')
    s = sub.add_parser('kernels')
    s.add_argument('--json')
    s = sub.add_parser('report')
    s.add_argument('dir')
    args = p.parse_args()
    os.chdir(ROOT)
    if args.what in ('run', 'per-kernel', 'phases'):
        args.pinning = pin(args.cpu)
    {'run': cmd_run, 'per-kernel': cmd_per_kernel, 'phases': cmd_phases, 'kernels': cmd_kernels,
     'report': cmd_report}[args.what](args)


if __name__ == '__main__':
    main()
