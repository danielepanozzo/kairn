#!/usr/bin/env python3
"""gs_probe.py: which functions MSVC protects with a /GS stack cookie (bench/README.md, "MSVC's
stack cookie"). Run from the repository root in a Visual Studio x64 developer prompt (or with
--vcvars PATH to vcvars64.bat).

  gs_probe.py probe --json FILE
      Compiles bench/gs_probe.cpp (with GS_PLAIN) with cl /O2 /arch:AVX2, once with the default
      /GS and once with /GS-, disassembles the objects with dumpbin, and reports for every function
      whether it reads __security_cookie and calls __security_check_cookie, and its number of
      instructions.
  gs_probe.py objects OBJ... [--prefix kb_a64_] [--json FILE]
      The same report for objects compiled elsewhere (kairn-bench's api.cpp.obj), for the functions
      whose names start with the prefix.
  gs_probe.py isolate --json FILE
      Compiles bench/gs_isolate.cpp once per variant (GS_VARIANT=0, 1, ...) with /O2, and reports
      which variants get the cookie in which shapes.
  gs_probe.py fix --json FILE
      Compiles bench/gs_probe.cpp against a copy of include/ in the work directory in which every
      parameter of type Expansion<T, 1> of kairn/expansion.hpp is passed by const reference instead
      of by value (the repository's headers are not changed), and reports as probe does.

Every compilation and disassembly has a timeout; on a timeout only the process this script started
is terminated, by its handle.
"""
import argparse
import datetime
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
    dumpbin /disasm listing."""
    funcs, cur = {}, None
    for line in disasm.splitlines():
        m = re.match(r'^(\S+)(?: \(.*\))?:\s*$', line)
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


def compile_and_read(src, obj, flags, env, prefix, include=os.path.join(ROOT, 'include')):
    run([tool('cl', env)] + FLAGS + ['/I', include] + flags + ['/c', src, '/Fo' + obj], env)
    return functions(run([tool('dumpbin', env), '/disasm:nobytes', obj], env), prefix)


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
    p.add_argument('what', choices=['probe', 'objects', 'isolate', 'fix'])
    p.add_argument('objs', nargs='*')
    p.add_argument('--prefix', default='')
    p.add_argument('--vcvars')
    p.add_argument('--workdir', default='.')
    p.add_argument('--commit', default='unknown')
    p.add_argument('--machine', default='')
    p.add_argument('--json')
    args = p.parse_args()
    env = vs_env(args.vcvars)
    os.makedirs(args.workdir, exist_ok=True)
    data = {'schema': 1, 'what': args.what, 'date': datetime.date.today().isoformat(), 'commit': args.commit,
            'machine': args.machine, 'compiler': compiler(env), 'flags': FLAGS + ['/I', 'include'],
            'results': {}}
    if args.what == 'probe':
        src = os.path.join(ROOT, 'bench', 'gs_probe.cpp')
        for label, flags in (('/GS', ['/DGS_PLAIN']), ('/GS-', ['/DGS_PLAIN', '/GS-'])):
            obj = os.path.join(args.workdir, 'gs_probe%s.obj' % ('_nogs' if label == '/GS-' else ''))
            data['results'][label] = compile_and_read(src, obj, flags, env, 'gs_')
    elif args.what == 'fix':
        # A copy of include/ in which every parameter of type Expansion<T, 1> in expansion.hpp is
        # passed by const reference instead of by value; the headers themselves are not changed.
        dst = os.path.join(os.path.abspath(args.workdir), 'include-by-reference')
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(ROOT, 'include'), dst)
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
        for obj in args.objs:
            data['results'][os.path.basename(obj)] = functions(
                run([tool('dumpbin', env), '/disasm:nobytes', obj], env), args.prefix)
    else:
        src = os.path.join(ROOT, 'bench', 'gs_isolate.cpp')
        text = open(src).read()
        data['variants'] = {}
        for v, what in re.findall(r'^// (\d+): (.*)$', text, re.M):
            data['variants'][v] = what
            obj = os.path.join(args.workdir, 'gs_isolate_%s.obj' % v)
            data['results']['variant %s' % v] = compile_and_read(src, obj, ['/DGS_VARIANT=%s' % v], env, 'gs_')
    table(data['results'])
    write(args.json, data)


if __name__ == '__main__':
    main()
