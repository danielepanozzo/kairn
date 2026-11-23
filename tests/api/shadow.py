#!/usr/bin/env python3
"""A program's global variables against the names of Kairn's headers (api.shadow).

A program may have a global variable with the name of any parameter or local variable of Kairn's
headers. MSVC reports each such declaration of a header, at /W4 (C4459, "declaration hides global
declaration") and under /analyze (C6244), and GCC 11 and 13 report under -Wshadow the parameters
of a constructor of a class template and of a lambda; a program built with warnings as errors then
fails to build. The headers turn these warnings off for their own declarations
(include/kairn/gen/prelude.hpp, KAIRN_GEN_PUSH_WARNINGS). Clang's -Wshadow-all, and GCC 16's
-Wshadow, report no declaration in a namespace that hides a global variable, only one that hides a
name of its own namespace or block.

This script reads the names of every parameter and local variable from the headers, writes
shadow_globals.hpp with a global variable of each name, and compiles tests/api/shadow.cpp, every
public operation once, with the strictest warnings of the compiler about a declaration that hides
another, as errors (the front end only):

  own       without the globals and with KAIRN_GEN_KEEP_SHADOW_WARNINGS, which keeps the two
            warnings on in the headers: Kairn's own declarations hide nothing; must compile, also
            with the operations of Ball external and their definitions (kairn/definitions.hpp)
  program   with the globals, as a program builds it: must compile, with each form of the scalar
            fix-ups (KAIRN_GEN_FIXUP_CALL 0 and 1), and with the operations of Ball outlined, and
            external with their definitions (KAIRN_ENCLOSURE_CODE)
  control   with the globals and KAIRN_GEN_KEEP_SHADOW_WARNINGS: what a program saw before the
            headers turned the warnings off. With MSVC it must fail with C4459 (C6244 too under
            /analyze), so that the program build cannot pass for want of a name the compiler
            reports; with the other compilers it is only reported, since what they report
            depends on their version (GCC 13 rejects it, GCC 16 and Clang accept it).

  shadow.py --cxx CXX --compiler msvc|clang-cl|gcc|clang --include DIR --source FILE --workdir DIR
            [--options "a|b"] [--sysroot DIR]
  shadow.py --names --include DIR      the names, one per line

The names are found by a scan of the tokens of each header, which knows the forms of declaration
that Kairn's headers use: a parameter, `TYPE name` before `,`, `)` or `=` in parentheses; a local
variable, `TYPE name` before `=`, `;`, `,`, `{`, `[` or `:`, and the names after it in the same
declaration. It finds a few names that are not declarations (`a * b` reads as one); a global of
that name is harmless.
"""
import argparse
import os
import re
import subprocess
import sys

KEYWORDS = frozenset('''
    alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t char16_t
    char32_t class compl concept const consteval constexpr constinit const_cast continue co_await
    co_return co_yield decltype default delete do double dynamic_cast else enum explicit export
    extern false float for friend goto if inline int long mutable namespace new noexcept not
    not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires
    return short signed sizeof static static_assert static_cast struct switch template this
    thread_local throw true try typedef typeid typename union unsigned using virtual void volatile
    wchar_t while xor xor_eq final override
'''.split())
# The tokens that can end a type, before the name it declares.
TYPE_WORDS = frozenset('auto bool char double float int long short signed unsigned void'.split())
# Names that a program cannot give a global variable, since the C library declares them in the
# global namespace (MSVC's <cstdlib> brings in <math.h>): the Bessel functions y0 and y1, and nan
# and ldexp, which GCC also knows as builtins. Kairn's namespaces, and std, cannot be either.
NOT_A_GLOBAL = frozenset('y0 y1 nan ldexp kairn std'.split())
PREFIX = 'use_'  # the names of tests/api/shadow.cpp

TOKEN = re.compile(r'[A-Za-z_]\w*|\d[\w.]*(?:[eEpP][+-]\d+)?|::|->|&&|\|\||\.\.\.|[<>=!+\-*/%&|^]=|<<|>>|\S')


def code(text):
    """The text without comments, string and character literals, and preprocessor lines other
    than the bodies of #define (where a macro may define functions)."""
    text = re.sub(r'\\\n', ' ', text)
    text = re.sub(r'//[^\n]*|/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', ' 0 ', text)
    lines = []
    for line in text.split('\n'):
        m = re.match(r'\s*#\s*define\s+\w+(?:\([^)]*\))?(.*)$', line)
        if m:
            lines.append(m.group(1))
        elif not re.match(r'\s*#', line):
            lines.append(line)
    return '\n'.join(lines)


def is_name(t):
    return re.fullmatch(r'[A-Za-z_]\w*', t) is not None and t not in KEYWORDS


def ends_type(t):
    return is_name(t) or t in TYPE_WORDS or t in ('>', '&', '*', '&&', '...', '>>')


def declared_names(text):
    toks = TOKEN.findall(code(text))
    names = set()
    depth = 0             # parentheses
    declaring = False     # in a declaration statement at depth 0, after its first name
    for i, t in enumerate(toks):
        prev = toks[i - 1] if i else ''
        nxt = toks[i + 1] if i + 1 < len(toks) else ''
        if t == '(':
            depth += 1
        elif t == ')':
            depth = max(0, depth - 1)
        elif t in (';', '{', '}'):
            declaring = False
        if not is_name(t) or prev in ('.', '->', '::') or nxt == '::':
            continue
        if ends_type(prev) and prev not in ('return', 'case', 'goto', 'throw'):
            if depth > 0 and nxt in (',', ')', '=', '[', ':'):
                names.add(t)          # a parameter, or a variable declared in a for or an if
            elif depth == 0 and nxt in ('=', ';', ',', '{', '[', ':'):
                names.add(t)          # a variable
                declaring = depth == 0 and nxt in ('=', ',', '{', '[')
        elif prev == ',' and declaring and depth == 0 and nxt in ('=', ';', ',', '{', '['):
            names.add(t)              # a further name of the same declaration
    return names


def header_names(include):
    names = set()
    root = os.path.join(include, 'kairn')
    for sub in ('', 'gen'):
        d = os.path.join(root, sub)
        for f in sorted(os.listdir(d)):
            if f.endswith('.hpp') and not f.startswith('.'):
                with open(os.path.join(d, f), encoding='utf-8') as h:
                    names |= declared_names(h.read())
    return sorted(n for n in names if not n.startswith('_') and n not in NOT_A_GLOBAL)


def write_globals(path, names):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// Written by tests/api/shadow.py: a global variable for each name of a parameter or a local\n'
                "// variable of Kairn's headers, as a program may have.\n#pragma once\n\n")
        for n in names:
            f.write(f'double {n} = 0;\n')


def strict(compiler):
    """The warnings about a declaration that hides another, the strictest of each compiler, and the
    usual ones, as errors."""
    if compiler == 'msvc':
        return ['/W4', '/WX', '/w14456', '/w14457', '/w14458', '/w14459']
    if compiler == 'clang-cl':
        return ['/W4', '/WX', '-Wshadow-all']
    if compiler == 'clang':
        return ['-Wall', '-Wextra', '-Wpedantic', '-Wshadow-all', '-Werror']
    return ['-Wall', '-Wextra', '-Wpedantic', '-Wshadow', '-Werror']


def compile_once(a, label, defines, analyze=False, extra=()):
    msvc_style = a.compiler in ('msvc', 'clang-cl')
    if msvc_style:
        cmd = [a.cxx, '/nologo', '/std:c++20', '/EHsc', f'/I{a.include}', f'/I{a.workdir}']
        cmd += [f'/D{d}' for d in defines]
        if analyze:
            cmd += ['/analyze', '/c', f'/Fo{os.path.join(a.workdir, label + ".obj")}']
        else:
            cmd += ['/Zs']
    else:
        cmd = [a.cxx, '-std=c++20', '-fsyntax-only', '-I', a.include, '-I', a.workdir]
        cmd += [f'-D{d}' for d in defines]
        if a.sysroot:
            cmd += ['-isysroot', a.sysroot]
    cmd += [o for o in a.options.split('|') if o] + strict(a.compiler) + list(extra) + [a.source]
    p = subprocess.run(cmd, cwd=a.workdir, capture_output=True, text=True, errors='replace', timeout=600)
    out = p.stdout + p.stderr
    return p.returncode, out


def reports(out):
    """The warnings about a hidden declaration, by number or option, and how many of each."""
    found = {}
    for m in re.finditer(r'warning (C4456|C4457|C4458|C4459|C6244|C6246)|\[-W(?:error=)?(shadow[\w=-]*)', out):
        key = m.group(1) or m.group(2)
        found[key] = found.get(key, 0) + 1
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cxx')
    ap.add_argument('--compiler', choices=['msvc', 'clang-cl', 'gcc', 'clang'])
    ap.add_argument('--include', required=True)
    ap.add_argument('--source')
    ap.add_argument('--workdir')
    ap.add_argument('--options', default='')
    ap.add_argument('--sysroot', default='')
    ap.add_argument('--names', action='store_true')
    a = ap.parse_args()
    names = header_names(a.include)
    if a.names:
        print('\n'.join(names))
        return 0
    for required in ('cxx', 'compiler', 'source', 'workdir'):
        if not getattr(a, required):
            ap.error(f'--{required} is required')
    a.include, a.source, a.workdir = (os.path.abspath(p) for p in (a.include, a.source, a.workdir))
    if os.sep in a.cxx or '/' in a.cxx:
        a.cxx = os.path.abspath(a.cxx)  # the compilations run in the work directory
    clash = [n for n in names if n.startswith(PREFIX)]
    if clash:
        print(f'FAILED: names of the headers start with {PREFIX}, the prefix of shadow.cpp\'s own: {clash}')
        return 1
    # A scan that found almost nothing would make the test pass for nothing: the headers declare
    # several hundred names, of every kind below.
    expected = {'inf': 'ball.hpp, a local', 'limbs': 'expansion.hpp, a parameter of from_limbs',
                'differs': 'environment.hpp, a local of a condition', 'what': 'config.hpp, a parameter',
                'i': 'ball.hpp, the variable of a for', 'te': 'environment.hpp, a further name',
                's_out': 'gen/scalar.hpp, an output', 'cz0': 'gen/scalar.hpp, a local'}
    missing = [f'{n} ({where})' for n, where in expected.items() if n not in names]
    if missing or len(names) < 200:
        print(f'FAILED: the scan of the headers found {len(names)} names, without {", ".join(missing) or "-"}')
        return 1
    os.makedirs(a.workdir, exist_ok=True)
    write_globals(os.path.join(a.workdir, 'shadow_globals.hpp'), names)
    print(f'{len(names)} names of parameters and local variables of the headers, each a global variable '
          f'of the program: {" ".join(names[:40])} ...')

    keep, globals_ = 'KAIRN_GEN_KEEP_SHADOW_WARNINGS', 'KAIRN_TEST_GLOBALS'
    # Each build: its name, its macros, whether under /analyze, its options, and what it must give:
    # 'pass', to compile without a warning about a hidden name; 'report', to compile or be rejected
    # for a hidden name only; or the warning it must be rejected with.
    outlined = 'KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_OUTLINED'
    external = ['KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL', 'KAIRN_TEST_DEFINITIONS']
    builds = [('own', [keep], False, (), 'pass'),
              ('own, the operations of Ball external, with their definitions', [keep] + external, False, (),
               'pass'),
              ('program', [globals_, 'KAIRN_GEN_FIXUP_CALL=0'], False, (), 'pass'),
              ('program, the fix-ups called', [globals_, 'KAIRN_GEN_FIXUP_CALL=1'], False, (), 'pass'),
              ('program, the operations of Ball outlined', [globals_, outlined], False, (), 'pass'),
              ('program, the operations of Ball external, with their definitions', [globals_] + external, False,
               (), 'pass')]
    if a.compiler == 'msvc':
        # The control under /analyze without C4459, which would stop the compilation first.
        builds += [('own, /analyze', [keep], True, (), 'pass'),
                   ('program, /analyze', [globals_], True, (), 'pass'),
                   ('control', [globals_, keep], False, (), 'C4459'),
                   ('control, /analyze', [globals_, keep], True, ('/wd4459',), 'C6244')]
    else:
        builds += [('control', [globals_, keep], False, (), 'report')]
    failed = []
    for label, defines, analyze, extra, expect in builds:
        status, out = compile_once(a, re.sub(r'\W+', '-', label), defines, analyze, extra)
        found = reports(out)
        summary = ', '.join(f'{k} {v} times' for k, v in sorted(found.items())) or 'no warning about a hidden name'
        if expect == 'pass':
            ok = status == 0 and not found
        elif expect == 'report':
            ok = status == 0 or bool(found)  # rejected, if at all, for a hidden name
        else:
            ok = status != 0 and found.get(expect, 0) > 0
        print(f'{"ok    " if ok else "FAILED"} {label}: {"compiled" if status == 0 else "rejected"}; {summary}')
        if not ok:
            failed.append(label)
            print(out[-6000:])
    if failed:
        print(f'FAILED: {", ".join(failed)}')
        return 1
    print('ok: no declaration of the headers fails a program that has globals of the same names')
    return 0


if __name__ == '__main__':
    sys.exit(main())
