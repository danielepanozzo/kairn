#!/usr/bin/env python3
"""zero_cost.py --cxx COMPILER --include DIR --workdir DIR [--msvc] [--flags "..."]

Compiles k1.cpp to assembly under each contraction setting that matters to the compiler and
compares, for each pair of functions (add, sum, axpy, dot, horner), the instructions emitted for
double and for kairn::Expansion<double, 1> (docs/developer/design/phase0/library.md, "One limb").

A pair is "identical" (the same lines once labels and names are anonymized), "same instructions"
(the same multiset of mnemonics), "k1 has fewer" (no mnemonic more for Expansion<double, 1>),
"different code" (other loop control, but no floating-point arithmetic instruction more and no more
instructions in all), or DIFFERENT. The run fails on a DIFFERENT pair in a setting where the
documents say the costs must match; where they say they do not (Clang's default contraction without
KAIRN_K1_CONTRACT, decision D6, and every MSVC setting, which does not vectorize loops over a
wrapper), the result is reported.

With MSVC the run also fails, in every setting, when one of these functions has a /GS stack cookie
(reads __security_cookie or calls __security_check_cookie): functions holding an
Expansion<double, 1> got one while its operators took it by value, and the same code on double did
not (docs/developer/results/costs-milestone1.md, "MSVC and the /GS stack cookie"). add and sum
are shapes that got it; axpy, dot and horner did not.
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'k1.cpp')
NAMES = ('add', 'sum', 'axpy', 'dot', 'horner')


def functions(path):
    """{name_plain or name_k1: [instruction lines]} of a GCC/Clang .s or MSVC .asm listing."""
    text = open(path, errors='replace').read().splitlines()
    msvc = path.endswith('.asm')
    funcs, cur = {}, None
    for line in text:
        line = line.split(';')[0].rstrip() if msvc else line.split('//')[0].rstrip()
        m = re.match(r'^_?(?:_Z\w*?|\?)?(\w*?(add|sum|axpy|dot|horner)_(plain|k1))\w*(?:@@\S*)?\s*(?::|PROC)', line)
        if m:
            cur = m.group(2) + '_' + m.group(3)
            funcs[cur] = []
            continue
        if re.match(r'^\S+\s+ENDP', line) or re.match(r'^\s*\.cfi_endproc', line):
            cur = None
        if cur is None or not line.strip():
            continue
        s = line.strip()
        if s.startswith('.') and not s.endswith(':'):
            continue   # an assembler directive
        if re.match(r'^[.\w$@?]+:$', s) or s.startswith('$LN') or s.startswith('$LL'):
            continue   # a label
        s = re.sub(r'\.?L[A-Za-z_]*\d+\b|\$L[LN]\d+@\w+|Ltmp\d+|LBB\d+_\d+', '<label>', s)
        s = re.sub(r'\b\w*(add|sum|axpy|dot|horner)_(plain|k1)\w*', '<self>', s)
        funcs[cur].append(re.sub(r'\s+', ' ', s))
    return funcs


# Floating-point arithmetic, scalar or packed: x86 (SSE, AVX, FMA) and AArch64 mnemonics.
ARITHMETIC = re.compile(r'^(v?(add|sub|mul|div|sqrt|min|max)[sp][sd]|vf?n?m(add|sub)(132|213|231)?[sp][sd]'
                        r'|f(add|sub|mul|div|sqrt|madd|msub|nmadd|nmsub|nmul|mla|mls|neg|abs|min|max)(\.\w+)?)$')


def cookie(lines):
    """Whether an MSVC function has the /GS stack cookie: it reads __security_cookie at its entry
    and calls __security_check_cookie at its exit."""
    return any('__security_cookie' in x or '__security_check_cookie' in x for x in lines)


def listing(counter):
    return ', '.join(f'{n} {m}' for m, n in sorted(counter.items())) or 'nothing'


def packed(line):
    """Whether an arithmetic instruction works on a vector: an x86 p[sd] form, or an AArch64
    arrangement such as .2d (in the mnemonic with Apple's syntax, in the operands with GNU's)."""
    mnemonic = line.split()[0]
    if not ARITHMETIC.match(mnemonic):
        return False
    return bool(re.search(r'p[sd]$', mnemonic)) or bool(re.search(r'\.(2d|4s|2s)\b', line))


def verdict(a, b):
    """(text, ok): ok unless Expansion<double, 1> needs more floating-point arithmetic, more
    instructions in all, or fewer vector operations than double (a loop not vectorized)."""
    ma, mb = Counter(x.split()[0] for x in a), Counter(x.split()[0] for x in b)
    if a == b:
        return 'identical', True
    if ma == mb:
        return 'same instructions', True
    more, less = mb - ma, ma - mb
    if not more:
        return 'k1 has fewer: ' + listing(less), True
    text = f'double has {listing(less)} more; Expansion<double, 1> has {listing(more)} more'
    extra_arithmetic = Counter({m: n for m, n in more.items() if ARITHMETIC.match(m)})
    fewer_vector = sum(map(packed, a)) > sum(map(packed, b))
    if not extra_arithmetic and len(b) <= len(a) and not fewer_vector:
        return f'different code, no more arithmetic and no more instructions: {text}', True
    if fewer_vector:
        return f'DIFFERENT, fewer vector operations: {text}', False
    return f'DIFFERENT: {text}', False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cxx', required=True)
    p.add_argument('--include', required=True)
    p.add_argument('--workdir', required=True)
    p.add_argument('--msvc', action='store_true', help='the compiler takes MSVC-style options (cl)')
    p.add_argument('--flags', default='', help='more options for every compilation (the FMA option)')
    args = p.parse_args()
    # cl cannot write its listing to a path that mixes / and \.
    args.workdir = os.path.normpath(args.workdir)
    args.include = os.path.normpath(args.include)
    os.makedirs(args.workdir, exist_ok=True)
    extra = args.flags.split()

    if args.msvc:
        family = 'msvc'
        base = ['/nologo', '/std:c++20', '/EHsc', '/DNDEBUG', '/O2', f'/I{args.include}'] + extra
        settings = [('/fp:precise (default)', [], False), ('/fp:contract', ['/fp:contract'], False),
                    ('/fp:strict', ['/fp:strict'], False)]
    else:
        version = subprocess.run([args.cxx, '--version'], capture_output=True, text=True).stdout
        family = 'clang' if 'clang' in version.lower() else 'gcc'
        base = ['-std=c++20', '-DNDEBUG', '-O2', '-I', args.include] + extra
        # (label, options, whether the costs must match)
        settings = [('default contraction', [], family == 'gcc'),
                    ('-ffp-contract=off', ['-ffp-contract=off'], True),
                    ('-ffp-contract=fast', ['-ffp-contract=fast'], True),
                    ('default contraction, KAIRN_K1_CONTRACT', ['-DKAIRN_K1_CONTRACT'], True),
                    ('-O3, default contraction', ['-O3'], family == 'gcc')]
    print(f'== {args.cxx} ({family}), {" ".join(base)}')
    failed = False
    for i, (label, options, must) in enumerate(settings):
        if args.msvc:
            out = os.path.join(args.workdir, f'k1_{i}.asm')
            obj = os.path.join(args.workdir, f'k1_{i}.obj')
            cmd = [args.cxx] + base + options + ['/c', '/FA', f'/Fa{out}', f'/Fo{obj}', SOURCE]
        else:
            out = os.path.join(args.workdir, f'k1_{i}.s')
            cmd = [args.cxx] + base + options + ['-S', SOURCE, '-o', out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f'  {label}: compilation failed\n{r.stdout}{r.stderr}')
            failed = True
            continue
        funcs = functions(out)
        print(f'  {label}{"" if must else " (reported only)"}:')
        for name in NAMES:
            a, b = funcs.get(name + '_plain'), funcs.get(name + '_k1')
            if a is None or b is None:
                print(f'    {name}: functions not found in {out}')
                failed = True
                continue
            text, ok = verdict(a, b)
            print(f'    {name:7s} double: {len(a):3d} instructions   Expansion<double, 1>: {len(b):3d}   {text}')
            if must and not ok:
                failed = True
            if args.msvc:
                for which, lines in (('double', a), ('Expansion<double, 1>', b)):
                    if cookie(lines):
                        print(f'    {name:7s} FAILED: the function for {which} has a /GS stack cookie')
                        failed = True
    print('FAILED' if failed else 'ok')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
