#!/usr/bin/env python3
"""gs_probe.py: which functions MSVC protects with a /GS stack cookie (bench/README.md, "MSVC's
stack cookie"). Run from the repository root in a Visual Studio x64 developer prompt (or with
--vcvars PATH to vcvars64.bat).

  gs_probe.py probe --json FILE
      Compiles bench/gs_probe.cpp (with GS_PLAIN) with cl /O2 /arch:AVX2, once with the default
      /GS and once with /GS-, disassembles the objects with dumpbin, and reports for every function
      whether it reads __security_cookie and calls __security_check_cookie, and its number of
      instructions.
  gs_probe.py objects OBJ... [--labels A,B] [--prefix kb_a64_] [--json FILE]
      The same report for objects compiled elsewhere (kairn-bench's api.cpp.obj), for the functions
      whose names start with the prefix.
  gs_probe.py isolate --json FILE
      Compiles bench/gs_isolate.cpp once per variant (GS_VARIANT=0, 1, ...) with /O2, and reports
      which variants get the cookie in which shapes.
  gs_probe.py fix --json FILE
      Compiles bench/gs_probe.cpp against a copy of include/ in the work directory in which every
      parameter of type Expansion<T, 1> of kairn/expansion.hpp is passed by const reference instead
      of by value (the repository's headers are not changed), and reports as probe does. Since the
      fix the operators of Expansion<T, 1> (22 parameters) take it by const reference and the
      functions of detail by value: the copy changes those 59 parameters of detail and of the
      mixed forms, so fix measures the variant that passes all 81 by const reference ("A" on
      docs/developer/results/costs-milestone1.md), and probe the headers as they are.
  gs_probe.py listing --cxx COMPILER --json FILE [--flags "..."]
      For GCC and Clang: compiles bench/gs_probe.cpp (with GS_PLAIN) to assembly at --level
      (default -O2) and records, for every function of the listing, its number of instructions and
      a hash of them, with labels and the names of the probe's functions anonymized, so that two
      versions of the headers can be compared; and the instructions themselves of the functions
      of --lines (default: one operation, a loop and Horner, on double and Expansion<double, 1>).

probe, fix, isolate and listing take --include DIR, the headers to compile against (default:
include/ of this tree). probe takes --level, the options in place of /O2 (/Od, or "/O2 /Ob0"),
and --all, which reports every function of the object, those of Kairn that are not inlined
included; listing takes --level=-O0 and the like (default -O2).
Every compilation and disassembly has a timeout; on a timeout only the process this script started
is terminated, by its handle.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = ['/nologo', '/std:c++20', '/EHsc', '/O2', '/DNDEBUG', '/arch:AVX2', '/fp:precise', '/wd4190']


def vs_env(vcvars):
    if not vcvars:
        return None
    out = subprocess.run('cmd /d /c "call "%s" >nul && set"' % vcvars, capture_output=True, text=True,
                         timeout=120)
    env = {}
    for line in out.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            env[k] = v
    if 'VCToolsInstallDir' not in env:
        sys.exit('vcvars64.bat failed: ' + out.stderr[-2000:])
    return env


def run(cmd, env, timeout=600, stdout=None):
    p = subprocess.Popen(cmd, env=env, stdout=stdout or subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()   # the process this script started, by its handle
        p.communicate()
        sys.exit('timeout: ' + ' '.join(cmd))
    if p.returncode != 0:
        sys.exit('failed (%d): %s\n%s' % (p.returncode, ' '.join(cmd), (out or b'').decode(errors='replace')[-3000:]))
    return (out or b'').decode(errors='replace')


def tool(name, env):
    path = env.get('PATH') or env.get('Path') if env else None
    return shutil.which(name, path=path) or name


def functions(disasm, prefix=''):
    """{name: {'instructions': n, 'cookie_reads': n, 'cookie_checks': n, 'frame': bytes}} of a
    dumpbin /disasm listing; a function named by its decorated name (one of Kairn's) also has its
    'declaration'."""
    funcs, cur = {}, None
    for line in disasm.splitlines():
        m = re.match(r'^(\S+)(?: \((.*)\))?:\s*$', line)
        if m:
            # A name with C linkage as it is; a decorated C++ name, which dumpbin follows with its
            # declaration in parentheses, by its identifier (?gs_x@@...).
            name = m.group(1)
            d = re.match(r'^\?(\w+)@', name)
            if d:
                name = d.group(1)
            cur = name if name.startswith(prefix) else None
            if cur:
                funcs[cur] = {'instructions': 0, 'cookie_reads': 0, 'cookie_checks': 0, 'frame': 0}
                if m.group(2) and not d:
                    funcs[cur]['declaration'] = m.group(2)
            continue
        if cur is None:
            continue
        m = re.match(r'^\s+[0-9A-F]{8,16}:\s+(\S.*)$', line)
        if not m:
            continue
        ins = m.group(1)
        f = funcs[cur]
        f['instructions'] += 1
        if '__security_check_cookie' in ins:
            f['cookie_checks'] += 1
        elif '__security_cookie' in ins:
            f['cookie_reads'] += 1
        s = re.match(r'sub\s+rsp,([0-9A-F]+)h', ins)
        if s and f['frame'] == 0:
            f['frame'] = int(s.group(1), 16)
    return funcs


def compile_and_read(src, obj, flags, env, prefix, include=os.path.join(ROOT, 'include'), level='/O2'):
    base = [g for f in FLAGS for g in (level.split() if f == '/O2' else [f])]
    run([tool('cl', env)] + base + ['/I', include] + flags + ['/c', src, '/Fo' + obj], env)
    return functions(run([tool('dumpbin', env), '/disasm:nobytes', obj], env), prefix)


def asm_functions(path):
    """{name: [instruction lines]} of a GCC or Clang assembly listing (x86-64 or AArch64, ELF or
    Mach-O): every function from its label to .cfi_endproc, without directives, labels and
    comments, local labels written <label>. A function of the probe is named by its identifier
    (gs_...) whatever its linkage, any other by its symbol."""
    funcs, cur = {}, None
    for raw in open(path, errors='replace').read().splitlines():
        line = re.sub(r'\s*(//|;).*$', '', raw)                  # AArch64 and Apple comments
        line = re.sub(r'(^|\s)#(\s.*)?$', '', line).rstrip()     # x86 comments, not an #immediate
        m = re.match(r'^([A-Za-z_][\w.$]*):$', line)
        if m and not re.match(r'^(L|\.L|ltmp|lCPI)', m.group(1)):
            name = m.group(1)
            z = re.match(r'^_{1,2}Z(\d+)(\w+)$', name)
            if z and z.group(2)[:int(z.group(1))].startswith('gs_'):
                name = z.group(2)[:int(z.group(1))]
            elif re.match(r'^_?gs_\w+$', name):
                name = name.lstrip('_')
            cur = name
            funcs[cur] = []
            continue
        if cur is None:
            continue
        s = line.strip()
        if s == '.cfi_endproc':
            cur = None
            continue
        if not s or s.startswith('.') or s.endswith(':'):
            continue   # a directive or a label
        s = re.sub(r'\b(\.?L[A-Za-z_]*\d+(_\d+)?|Ltmp\d+|LBB\d+_\d+|l?LCPI\d+_\d+)\b', '<label>', s)
        s = re.sub(r'\b_*(Z\d+)?gs_\w+', '<probe>', s)
        funcs[cur].append(re.sub(r'\s+', ' ', s))
    return {n: v for n, v in funcs.items() if v}


# The functions of a listing whose instructions are recorded by default: one operation, a loop
# and a Horner evaluation, on double and on Expansion<double, 1>.
LINES = ['gs_double_add', 'gs_e1_add', 'gs_double_tp_add', 'gs_e1_tp_add', 'gs_double_horner', 'gs_e1_horner']


def summary(lines, keep):
    """A function of a listing as recorded: its number of instructions and the SHA-256 of their
    lines, which is the same for the same code; the lines themselves when keep."""
    s = {'instructions': len(lines), 'sha256': hashlib.sha256('\n'.join(lines).encode()).hexdigest()}
    if keep:
        s['lines'] = lines
    return s


def gnu_listing(args):
    """listing: gs_probe.cpp compiled by GCC or Clang to assembly, and its functions."""
    out = os.path.join(args.workdir, 'gs_probe%s.s' % args.level)
    cmd = [args.cxx, '-std=c++20', '-DNDEBUG', args.level, '-DGS_PLAIN', '-I', args.include] + \
        args.flags.split() + ['-S', os.path.join(ROOT, 'bench', 'gs_probe.cpp'), '-o', out]
    run(cmd, None)
    version = subprocess.run([args.cxx, '--version'], capture_output=True, text=True, timeout=60).stdout
    # The command as recorded: the headers, the source and the output by role, not by their paths.
    shown = [{args.include: 'INCLUDE', cmd[-3]: 'bench/gs_probe.cpp', out: 'OUT.s'}.get(c, c) for c in cmd]
    return shown, version.strip().splitlines()[0], asm_functions(out)


def compiler(env):
    p = subprocess.run([tool('cl', env)], env=env, capture_output=True, text=True, timeout=60)
    return (p.stderr or p.stdout).strip().splitlines()[0]


def write(path, data):
    text = json.dumps(data, indent=1) + '\n'
    if path:
        with open(path, 'w') as f:
            f.write(text)
    else:
        sys.stdout.write(text)


def table(results):
    names = sorted(set(n for r in results.values() for n in r))
    print('%-22s' % 'function' + ''.join('%26s' % k for k in results))
    for n in names:
        cells = []
        for r in results.values():
            f = r.get(n)
            cells.append('%26s' % ('-' if f is None else '%s %3d ins, frame %3d' % (
                'COOKIE' if f['cookie_checks'] else '      ', f['instructions'], f['frame'])))
        print('%-22s' % n + ''.join(cells))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('what', choices=['probe', 'objects', 'isolate', 'fix', 'listing'])
    p.add_argument('objs', nargs='*')
    p.add_argument('--prefix', default='')
    p.add_argument('--labels', help='objects: the names of the objects in the report, comma-separated')
    p.add_argument('--include', default=os.path.join(ROOT, 'include'), help='the headers to compile against')
    p.add_argument('--level', help='probe: the options in place of /O2 (/Od, "/O2 /Ob0"); listing: -O2, -O0, ...')
    p.add_argument('--all', action='store_true', help="probe: every function of the object, not only the probe's")
    p.add_argument('--cxx', help='listing: the compiler, GCC or Clang')
    p.add_argument('--flags', default='', help='listing: more options (the FMA option)')
    p.add_argument('--lines', default=','.join(LINES),
                   help='listing: the functions whose instructions are recorded, comma-separated (of the others, '
                        'their number and a hash)')
    p.add_argument('--vcvars')
    p.add_argument('--workdir', default='.')
    p.add_argument('--commit', default='unknown')
    p.add_argument('--machine', default='')
    p.add_argument('--json')
    args = p.parse_args()
    args.include = os.path.abspath(args.include)
    os.makedirs(args.workdir, exist_ok=True)
    if args.what == 'listing':
        args.level = args.level or '-O2'
        cmd, version, funcs = gnu_listing(args)
        keep = set(args.lines.split(','))
        data = {'schema': 1, 'what': 'listing', 'date': datetime.date.today().isoformat(), 'commit': args.commit,
                'machine': args.machine, 'compiler': version, 'level': args.level, 'flags': args.flags,
                'command': cmd, 'results': {n: summary(v, n in keep) for n, v in funcs.items()}}
        for n in sorted(funcs):
            if n.startswith('gs_'):
                print('%-24s %4d instructions' % (n, len(funcs[n])))
        write(args.json, data)
        return
    env = vs_env(args.vcvars)
    args.level = args.level or '/O2'
    data = {'schema': 1, 'what': args.what, 'date': datetime.date.today().isoformat(), 'commit': args.commit,
            'machine': args.machine, 'compiler': compiler(env),
            'flags': [g for f in FLAGS for g in (args.level.split() if f == '/O2' else [f])] + ['/I', 'include'],
            'results': {}}
    if args.what == 'probe':
        src = os.path.join(ROOT, 'bench', 'gs_probe.cpp')
        for label, flags in (('/GS', ['/DGS_PLAIN']), ('/GS-', ['/DGS_PLAIN', '/GS-'])):
            obj = os.path.join(args.workdir, 'gs_probe%s.obj' % ('_nogs' if label == '/GS-' else ''))
            data['results'][label] = compile_and_read(src, obj, flags, env, '' if args.all else 'gs_', args.include,
                                                      args.level)
    elif args.what == 'fix':
        # A copy of include/ in which every parameter of type Expansion<T, 1> in expansion.hpp is
        # passed by const reference instead of by value; the headers themselves are not changed.
        dst = os.path.join(os.path.abspath(args.workdir), 'include-by-reference')
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(args.include, dst)
        path = os.path.join(dst, 'kairn', 'expansion.hpp')
        text = open(path).read()
        text, n1 = re.subn(r'([(]|, )Expansion<T, 1> (\w+)(?=[,)])', r'\1const Expansion<T, 1>& \2', text)
        text, n2 = re.subn(r'([(]|, )Expansion (\w+)(?=[,)])', r'\1const Expansion& \2', text)
        with open(path, 'w') as f:
            f.write(text)
        data['patch'] = ('include/kairn/expansion.hpp with %d parameters Expansion<T, 1> and %d parameters '
                         'Expansion of the class Expansion<T, 1> passed by const reference' % (n1, n2))
        src = os.path.join(ROOT, 'bench', 'gs_probe.cpp')
        obj = os.path.join(args.workdir, 'gs_probe_by_reference.obj')
        data['results']['/GS, by reference'] = compile_and_read(src, obj, ['/DGS_PLAIN'], env, 'gs_', include=dst)
    elif args.what == 'objects':
        labels = args.labels.split(',') if args.labels else [os.path.basename(o) for o in args.objs]
        for label, obj in zip(labels, args.objs):
            data['results'][label] = functions(run([tool('dumpbin', env), '/disasm:nobytes', obj], env), args.prefix)
    else:
        src = os.path.join(ROOT, 'bench', 'gs_isolate.cpp')
        text = open(src).read()
        data['variants'] = {}
        for v, what in re.findall(r'^// (\d+): (.*)$', text, re.M):
            data['variants'][v] = what
            obj = os.path.join(args.workdir, 'gs_isolate_%s.obj' % v)
            data['results']['variant %s' % v] = compile_and_read(src, obj, ['/DGS_VARIANT=%s' % v], env, 'gs_',
                                                                 args.include)
    table(data['results'])
    write(args.json, data)


if __name__ == '__main__':
    main()
