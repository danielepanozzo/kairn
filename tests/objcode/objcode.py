#!/usr/bin/env python3
"""objcode.py: the object-code check (docs/developer/testing.md, "Object code").

    python3 tests/objcode/objcode.py --cxx COMPILER --workdir DIR [--tier quick|full]
        [--style gnu|msvc] [--compiler-id ID] [--flags "..."] [--packed neon|avx2|none]
        [--packed-flags "..."] [--disassembler PATH] [--jobs N]
    python3 tests/objcode/objcode.py --controls ...      the negative controls (below)

For each configuration of a compiler's flag matrix, compiles unit.cpp, which has one function per
kernel and limb type, scalar and packed, disassembles the object file, and checks every kernel
against what the generator says its code asks for (gen/objcode.json, from the same IR the code and
the proofs are printed from). The rule, for a kernel in one form (scalar with its fix-up inline,
scalar with its fix-up a function of its own, packed) and one limb type, where F and M are the
fused multiply-add and plain floating-point multiplication instructions of its function and of the
functions of the object that it calls, once per call site (disasm.py):

- F is `fma` or `fma_distinct`: one fused instruction per FMA node of the IR, with identical ones
  (the same operation on the same operands, in one function) counted once or each. They differ in
  three kernels only, whose fix-up recomputes the core's leading product: a compiler that
  eliminates common subexpressions computes it once, one that does not (without optimization, and
  MSVC under /fp:strict for the scalar code) twice.
- M is `mul` or `mul_distinct`, or that plus `consteval_mul`: a plain multiplication only for the
  products with infinity of the fix-ups (times_inf, exact, and only compared or selected), plus,
  where a compiler emits the branch that only constant evaluation takes (MSVC at /Od), the plain
  products of that branch (two_prod's Dekker product), never executed.
- Nothing else: no call outside the object but the stack protector's, no indirect call, no
  kernel without its function, no function of the unit without its kernel's counts, no `muladd`
  (a declared contractable multiply-add, for which the check has no rule yet).

A contraction the IR did not ask for shows as a fused instruction more, with a multiplication less
or none; an FMA computed as a product and a sum, or an opaque product folded back into a plain one,
as a multiplication more. The forms and the counts are described in gen/kairn_gen/objcode.py.

In each configuration that compiles both forms of the fix-ups, enclosure_unit.cpp, the public
operations of Ball, is compiled with KAIRN_ENCLOSURE_CODE outlined, external, and external with
kairn/definitions.hpp (include/kairn/config.hpp): each of its functions must have no fused
multiply-add or multiplication of its own, and call a function with the counts of the operation's
full Ball kernel by the rule above, or, external without the definitions, the operation outside the
object and nothing that computes (check_enclosure_program).

The negative controls (--controls), each in every configuration of the tier:

- fixture.cpp has the textbook `a * b + c`, as two statements and as one expression, scalar and
  packed. Each function is judged by the same rule against its own source, one product and one
  sum, and the program says at run time whether the compiler fused it. The check must fail on a
  function exactly when it was fused, and at least one configuration must fuse something.
- the unit, compiled once, is judged against counts with two kernels changed (one FMA more for
  mul_2_2, one multiplication fewer for add_2_2_full): exactly those kernels must fail.
- enclosure_unit.cpp, compiled once with the operations of Ball inline (the default), is judged
  as the outlined form: every function must fail, its operation not being a call.

Standard library only. Exits 1 on any failure, with what was found; a compiler or disassembler that
cannot be run is a failure, never a skip.
"""
import argparse
import concurrent.futures
import copy
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # nothing of a run is written into the source tree
import disasm  # noqa: E402

UNIT = os.path.join(HERE, 'unit.cpp')
FIXTURE = os.path.join(HERE, 'fixture.cpp')
ENCLOSURE_UNIT = os.path.join(HERE, 'enclosure_unit.cpp')

# The operations of Ball that KAIRN_ENCLOSURE_CODE takes out of their callers, by the full Ball
# kernel each calls (include/kairn/config.hpp), and the forms of enclosure_unit.cpp: a label, its
# macros, and whether the operation's definition is in the object ('in') or outside it ('out').
ENCLOSURE_KERNELS = ['ball_add_1_full', 'ball_sub_1_full', 'ball_mul_1_full', 'ball_scale_1_full',
                     'ball_add_2_full', 'ball_sub_2_full', 'ball_mul_2_full', 'ball_scale_2_full',
                     'ball_mul_pow2_1_full', 'ball_mul_pow2_2_full']
ENCLOSURE_FORMS = [
    ('outlined', ['KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_OUTLINED'], 'in'),
    ('external', ['KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL'], 'out'),
    ('external with its definitions', ['KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL',
                                       'KAIRN_OBJCODE_DEFINITIONS'], 'in'),
]
# The namespace of the external operations with KAIRN_CHECKS 0, which the unit is compiled with.
EXTERNAL_NAMESPACE = 'external'
TIMEOUT = 600   # seconds per compilation: MSVC has been seen to spin on generated code

# The flag matrix of each compiler family: optimization levels, contraction settings, and with and
# without the flag that makes the compiler respect a dynamic rounding mode. Every combination is
# a configuration of the full tier; QUICK lists those of the quick tier. The last field of a quick
# configuration says whether both forms of the scalar fix-ups are compiled, or only the compiler's
# own; the full tier compiles both everywhere.
MATRIX = {
    'gnu': {'levels': ['-O0', '-O1', '-O2', '-O3'],
            'contraction': [('-ffp-contract=off',), ('-ffp-contract=on',), ('-ffp-contract=fast',)],
            'rounding': [(), ('-frounding-math',)]},
    'msvc': {'levels': ['/Od', '/O1', '/O2'],
             'contraction': [('/fp:precise',), ('/fp:contract',), ('/fp:strict',)],
             'rounding': [()]},
    # clang-cl: /fp:strict is -ffp-contract=off, /fp:precise and /fp:contract are =on, and =fast
    # has no /fp: spelling (tests/CMakeLists.txt).
    'clang-cl': {'levels': ['/Od', '/O1', '/O2'],
                 'contraction': [('/fp:strict',), ('/fp:precise',), ('/fp:contract',),
                                 ('/clang:-ffp-contract=fast',)],
                 'rounding': [(), ('/clang:-frounding-math',)]},
}
QUICK = {
    'gnu': [('-O0', ('-ffp-contract=fast',), (), False),
            ('-O2', ('-ffp-contract=off',), (), False),
            ('-O2', ('-ffp-contract=on',), (), False),
            ('-O2', ('-ffp-contract=fast',), (), True),
            ('-O3', ('-ffp-contract=fast',), ('-frounding-math',), False)],
    'msvc': [('/Od', ('/fp:precise',), (), False),
             ('/O2', ('/fp:precise',), (), False),
             ('/O2', ('/fp:contract',), (), True),
             ('/O2', ('/fp:strict',), (), False)],
    'clang-cl': [('/Od', ('/fp:precise',), (), False),
                 ('/O2', ('/fp:strict',), (), False),
                 ('/O2', ('/fp:precise',), (), False),
                 ('/O2', ('/clang:-ffp-contract=fast',), (), True),
                 ('/O2', ('/fp:contract',), ('/clang:-frounding-math',), False)],
}


def configurations(family, tier):
    """[(level, contraction options, rounding options, both fix-up forms)] of a tier."""
    if tier == 'quick':
        return QUICK[family]
    m = MATRIX[family]
    return [(level, c, r, True) for level in m['levels'] for c in m['contraction'] for r in m['rounding']]


def label(config):
    level, contraction, rounding, _ = config
    return ' '.join((level,) + contraction + rounding)


class Failure(Exception):
    pass


# --- The tools ------------------------------------------------------------------------------------

class Tools:
    """The compiler, its family, its options, and the disassembler."""

    def __init__(self, args):
        self.cxx = args.cxx
        path = shutil.which(args.cxx)
        if path is None:
            raise Failure(f'no compiler {args.cxx}')
        self.cxx_path = path
        base = os.path.basename(path).lower()
        style = args.style or ('msvc' if re.match(r'^(cl|clang-cl)(\.exe)?$', base) else 'gnu')
        self.msvc_style = style == 'msvc'
        if self.msvc_style:
            clang = (args.compiler_id or '').lower() == 'clang' or base.startswith('clang')
            self.family = 'clang-cl' if clang else 'msvc'
        else:
            self.family = 'gnu'
        self.name = args.compiler_id or {'msvc': 'MSVC', 'clang-cl': 'clang-cl'}.get(self.family)
        if not self.name:
            version = subprocess.run([path, '--version'], capture_output=True, text=True, errors='replace',
                                     timeout=60).stdout
            self.name = (version.splitlines() or ['unknown compiler'])[0]
        self.flags = args.flags.split()
        self.packed = args.packed or default_packed()
        self.packed_flags = args.packed_flags.split()
        self.emulator = args.emulator.split()
        self.disassembler, self.flavor = find_disassembler(args.disassembler, self.family, path)

    def compile(self, source, obj, options, defines, packed, cwd):
        include = os.path.join(ROOT, 'include')
        table = os.path.join(ROOT, 'gen', 'tests')
        defs = list(defines) + (['KAIRN_OBJCODE_PACKED'] if packed else [])
        isa = self.packed_flags if packed else []
        if self.msvc_style:
            cmd = ([self.cxx, '/nologo', '/std:c++20', '/c'] + list(options) + [f'/D{d}' for d in defs]
                   + self.flags + isa + ['/I', include, '/I', table, source, f'/Fo{obj}'])
        else:
            cmd = ([self.cxx, '-std=c++20', '-c'] + list(options) + [f'-D{d}' for d in defs]
                   + self.flags + isa + ['-I', include, '-I', table, source, '-o', obj])
        run(cmd, cwd, 'compiling')
        return cmd

    def link(self, obj, exe, cwd):
        if self.msvc_style:
            cmd = [self.cxx, '/nologo', obj, f'/Fe{exe}']
        else:
            cmd = [self.cxx] + self.flags + [obj, '-o', exe]
        run(cmd, cwd, 'linking')

    def disassemble(self, obj, cwd):
        if self.flavor == 'dumpbin':
            cmd = [self.disassembler, '/nologo', '/disasm:nobytes', obj]
        else:
            cmd = [self.disassembler, '-d', '-r', '--no-show-raw-insn'] + \
                (['--show-all-symbols'] if self.flavor == 'llvm' else []) + [obj]
        text = run(cmd, cwd, 'disassembling')
        with open(obj + '.dis', 'w', encoding='utf-8') as f:
            f.write(text)
        return text


def default_packed():
    machine = platform.machine().lower()
    if machine in ('arm64', 'aarch64'):
        return 'neon'
    if machine in ('x86_64', 'amd64'):
        return 'avx2'
    return 'none'


def find_disassembler(given, family, cxx_path):
    """(path, flavor): flavor is 'gnu' or 'llvm' (objdump) or 'dumpbin'."""
    looked = []
    if given:
        candidates = [given]
    elif family == 'msvc':
        candidates = [os.path.join(os.path.dirname(cxx_path), 'dumpbin.exe'), 'dumpbin']
    elif family == 'clang-cl':
        candidates = [os.path.join(os.path.dirname(cxx_path), 'llvm-objdump.exe'), 'llvm-objdump']
    else:
        candidates = ['objdump', 'llvm-objdump']
    for c in candidates:
        looked.append(c)
        path = c if os.path.isfile(c) else shutil.which(c)
        if not path:
            continue
        if os.path.basename(path).lower().startswith('dumpbin'):
            return path, 'dumpbin'
        version = subprocess.run([path, '--version'], capture_output=True, text=True, errors='replace',
                                 timeout=60).stdout
        if 'GNU objdump' in version:
            return path, 'gnu'
        if 'LLVM' in version:
            return path, 'llvm'
        raise Failure(f'{path} is neither GNU objdump, LLVM objdump nor dumpbin: {version[:200]!r}')
    raise Failure('no disassembler: looked for ' + ', '.join(looked) + '. The check cannot run '
                  'without one (docs/developer/testing.md, "Object code").')


def run(cmd, cwd, what):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors='replace', timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise Failure(f'{what} took more than {TIMEOUT} s: {" ".join(cmd)}')
    except OSError as e:
        raise Failure(f'{what}: {e}: {" ".join(cmd)}')
    if r.returncode != 0:
        raise Failure(f'{what} failed ({r.returncode}): {" ".join(cmd)}\n{r.stdout}{r.stderr}')
    return r.stdout


# --- The rule -------------------------------------------------------------------------------------

def load_expected(path):
    with open(path, encoding='utf-8') as f:
        doc = json.load(f)
    names = doc['counts']
    kernels = {k: {form: {t: dict(zip(names, row)) for t, row in types.items()}
                   for form, types in forms.items()}
               for k, forms in doc['kernels'].items()}
    return kernels, doc['limb_types']


def load_fold_expected(path):
    """{fold: {form: {limb type: [{'part', 'least', counts...}]}}} of gen/objcode.json ("folds"), or
    {} when it has none."""
    with open(path, encoding='utf-8') as f:
        doc = json.load(f)
    names = doc.get('fold_parts', [])
    return {fd: {form: {t: [dict(zip(names, part)) for part in parts] for t, parts in types.items()}
                 for form, types in forms.items()}
            for fd, forms in doc.get('folds', {}).items()}


# The most copies of one part of a fold's function that a compiler is taken to make (unrolling
# and peeling of its loops): the counts are judged against every number of copies up to it.
FOLD_COPIES = 64


def _sums(parts, key, alt, limit):
    """Every total, up to limit, of the counts `key` (or `alt`, for a copy whose identical
    operations a compiler merged) of each part taken at least `least` times and at most
    FOLD_COPIES."""
    totals = {0}
    for p in parts:
        values = {p[key], p[alt]}
        nxt = set()
        for t in totals:
            if values == {0}:            # any number of copies of a part that asks for none
                nxt.add(t)
                continue
            if p['least'] == 0:
                nxt.add(t)
            frontier = {t}
            for copy in range(1, FOLD_COPIES + 1):
                frontier = {x + v for x in frontier for v in values if x + v <= limit}
                if not frontier:
                    break
                if copy >= p['least']:
                    nxt |= frontier
        totals = nxt
    return totals


def judge_fold(count, parts):
    """(failure text or None, how) for a fold's function: its fused instructions and its plain
    multiplications are what some number of copies of its parts ask for, each part at least as
    often as the printed function has it (a loop unrolled holds its step several times), and
    nothing else: no call outside the object, no declared contractable multiply-add."""
    f, m = len(count.fma), len(count.mul)
    problems = []
    if any(p['muladd'] for p in parts):
        problems.append('a part has declared contractable multiply-adds (muladd), for which the check has no rule yet')
    if any(p['consteval_mul'] for p in parts):
        problems.append('a part has a branch of constant evaluation, which a fold has not')
    described = ', '.join(f'{p["part"]} {p["fma"]}' + (f' or {p["fma_distinct"]}' if p['fma_distinct'] != p['fma'] else '')
                          + f' at least {p["least"]} times' for p in parts)
    if f not in _sums(parts, 'fma', 'fma_distinct', f):
        problems.append(f'{f} fused multiply-adds, which no number of copies of the parts makes ({described})')
    if m not in _sums(parts, 'mul', 'mul_distinct', m):
        muls = ', '.join(f'{p["part"]} {p["mul"]}' for p in parts)
        problems.append(f'{m} plain multiplications, which no number of copies of the parts makes ({muls})')
    for fn, sym in count.external:
        problems.append(f'calls {sym} outside the object (in {fn}): what it executes cannot be counted')
    for fn, insn in count.unknown:
        problems.append(f'a call or jump whose target is not known (in {fn}: {insn})')
    if problems:
        detail = []
        if count.fma:
            detail.append('fused: ' + '; '.join(f'{fn}: {i}' for fn, i in count.fma))
        if count.mul:
            detail.append('multiplications: ' + '; '.join(f'{fn}: {i}' for fn, i in count.mul))
        return '; '.join(problems) + ''.join(f'\n        {d}' for d in detail), set()
    return None, set()


def judge(count, e):
    """(failure text or None, how): how says which alternatives of the rule held, for the tally:
    'each' or 'distinct' where the two counts of FMAs differ, and 'consteval' where the
    constant-evaluation branch was emitted."""
    f, m = len(count.fma), len(count.mul)
    problems = []
    if e['muladd']:
        problems.append(f'{e["muladd"]} declared contractable multiply-adds (muladd), for which the '
                        f'check has no rule yet')
    if f not in (e['fma'], e['fma_distinct']):
        alt = '' if e['fma'] == e['fma_distinct'] else f' or {e["fma_distinct"]} (identical ones once)'
        problems.append(f'{f} fused multiply-adds, expected {e["fma"]}{alt}')
    plain = {e['mul'], e['mul_distinct']}
    with_ce = {x + e['consteval_mul'] for x in plain} if e['consteval_mul'] else set()
    if m not in plain | with_ce:
        alt = ''.join(f' or {x} (identical ones once)' for x in sorted(plain - {e['mul']}))
        alt += ''.join(f' or {x} (with the branch of constant evaluation)' for x in sorted(with_ce))
        problems.append(f'{m} plain multiplications, expected {e["mul"]}{alt}')
    for fn, sym in count.external:
        problems.append(f'calls {sym} outside the object (in {fn}): what it executes cannot be counted')
    for fn, insn in count.unknown:
        problems.append(f'a call or jump whose target is not known (in {fn}: {insn})')
    how = set()
    if e['fma'] != e['fma_distinct']:
        how.add('each' if f == e['fma'] else 'distinct')
    if m in with_ce and m not in plain:
        how.add('consteval')
    if problems:
        detail = []
        if count.fma:
            detail.append('fused: ' + '; '.join(f'{fn}: {i}' for fn, i in count.fma))
        if count.mul:
            detail.append('multiplications: ' + '; '.join(f'{fn}: {i}' for fn, i in count.mul))
        return '; '.join(problems) + ''.join(f'\n        {d}' for d in detail), how
    return None, how


def unit_form(program):
    """The form of the scalar fix-ups the unit was compiled with: its marker function says."""
    call = program.find('kairn_objcode_fixups_call') is not None
    inline = program.find('kairn_objcode_fixups_inline') is not None
    if call == inline:
        raise Failure('the unit has neither or both markers of the form of its fix-ups')
    return 'scalar_call' if call else 'scalar'


def check_program(program, expected, limb_types, packed, folds=None):
    """(failures, tally, functions checked) of one object file of the unit; a failure is (kernel
    or fold, or None, text). `folds` are the expectations of the folds (load_fold_expected)."""
    form = unit_form(program)
    failures, tally, n = [], {}, 0
    folds = folds or {}
    fold_forms = ['seq', 'lanes'] + (['packed'] if packed else [])
    for fold, forms in folds.items():
        for fform in fold_forms:
            if fform not in forms:
                continue
            for t in limb_types:
                name = f'kairn_objcode_fold_{fform}_{t}_{fold}'
                f = program.find(name)
                if f is None:
                    failures.append((fold, f'fold {fold} {fform} {t}: no function {name} in the disassembly'))
                    continue
                n += 1
                count = program.count(f)
                text, _ = judge_fold(count, forms[fform][t])
                if count.calls:
                    tally['calls'] = tally.get('calls', 0) + 1
                if text:
                    failures.append((fold, f'fold {fold} {fform} {t}: {text}'))
    known_folds = {f'kairn_objcode_fold_{ff}_{t}_{fd}' for fd, forms in folds.items() for ff in fold_forms
                   if ff in forms for t in limb_types}
    for fn in program.functions:
        if program.owner(fn) is not fn:
            continue
        for fname in fn.names:
            plain = fname[1:] if fname.startswith('_kairn_objcode_') else fname
            if re.match(r'^kairn_objcode_fold_(seq|lanes|packed)_', plain) and plain not in known_folds:
                failures.append((None, f'{plain}: a function of the unit with no counts in gen/objcode.json'))
    families = ['scalar'] + (['packed'] if packed else [])
    for kernel, forms in expected.items():
        for family in families:
            for t in limb_types:
                name = f'kairn_objcode_{family}_{t}_{kernel}'
                f = program.find(name)
                where = f'{family} {t} {kernel}' + (f' ({form})' if family == 'scalar' else '')
                if f is None:
                    failures.append((kernel, f'{where}: no function {name} in the disassembly'))
                    continue
                n += 1
                count = program.count(f)
                text, how = judge(count, forms[form if family == 'scalar' else 'packed'][t])
                if count.calls:
                    how.add('calls')
                if any(program.owner(g) is f and g is not f for g in program.functions):
                    how.add('split')
                for h in how:
                    tally[h] = tally.get(h, 0) + 1
                if text:
                    failures.append((kernel, f'{where}: {text}'))
    # Every function of the unit is a kernel of the expectations: a stale gen/objcode.json, or
    # runner_kernels.inc ahead of it, is a failure too.
    known = {f'kairn_objcode_{fam}_{t}_{k}' for k in expected for fam in families for t in limb_types}
    for fn in program.functions:
        if program.owner(fn) is not fn:
            continue                        # a part of a function (F.cold), counted with it
        for name in fn.names:
            plain = name[1:] if name.startswith('_kairn_objcode_') else name
            if re.match(r'^kairn_objcode_(scalar|packed)_', plain) and plain not in known:
                failures.append((None, f'{plain}: a function of the unit with no counts in gen/objcode.json'))
    return failures, tally, n


def check_enclosure_program(program, expected, limb_types, where):
    """(failures, functions checked) of one object file of enclosure_unit.cpp. Each function of the
    unit must have no fused multiply-add and no multiplication of its own: the operation is a call.
    With where 'in', the function it calls is in the object, and with it the counts are those of the
    operation's kernel, by the rule of judge(); with 'out', it calls the operation outside the object
    (a symbol of the namespace kairn::detail::external), once, and nothing it executes in the object
    has a fused multiply-add or a multiplication."""
    form = unit_form(program)
    failures, n = [], 0
    for kernel in ENCLOSURE_KERNELS:
        for t in limb_types:
            name = f'kairn_objcode_enclosure_{t}_{kernel}'
            f = program.find(name)
            where_text = f'{t} {kernel} ({form})'
            if f is None:
                failures.append((kernel, f'{where_text}: no function {name} in the disassembly'))
                continue
            n += 1
            count = program.count(f)
            own_names = {p.names[0] for p in program.parts.get(id(f), [f])}
            own = [i for fn, i in count.fma + count.mul if fn in own_names]
            problems = []
            if own:
                problems.append(f'{len(own)} fused multiply-adds or multiplications of its own '
                                f'({"; ".join(own)}): the operation is not a call')
            if where == 'in':
                text, _ = judge(count, expected[kernel][form][t])
                if text:
                    problems.append(text)
                if not count.calls:
                    problems.append('it calls no function of the object')
            else:
                ops = [sym for _, sym in count.external if EXTERNAL_NAMESPACE in sym]
                others = [sym for _, sym in count.external if EXTERNAL_NAMESPACE not in sym]
                if len(ops) != 1:
                    problems.append(f'{len(ops)} calls of an external operation (kairn::detail::'
                                    f'{EXTERNAL_NAMESPACE}), expected one')
                if others:
                    problems.append('calls outside the object that are not the operation: ' + ', '.join(others))
                if count.fma or count.mul:
                    problems.append(f'{len(count.fma)} fused multiply-adds and {len(count.mul)} '
                                    f'multiplications in the object, expected none')
                for fn, insn in count.unknown:
                    problems.append(f'a call or jump whose target is not known (in {fn}: {insn})')
            if problems:
                failures.append((kernel, f'{where_text}: ' + '; '.join(problems)))
    return failures, n


def check_enclosures(tools, config, index, workdir, expected, limb_types):
    """[(text, ok)] of enclosure_unit.cpp in one configuration, in each of its forms."""
    level, contraction, rounding, _ = config
    options = (level,) + contraction + rounding
    out = []
    for i, (label_, defines, where) in enumerate(ENCLOSURE_FORMS):
        obj = os.path.join(workdir, f'enclosure-{index}-{i}.{"obj" if tools.msvc_style else "o"}')
        t0 = time.time()
        try:
            tools.compile(ENCLOSURE_UNIT, obj, options, defines + ['KAIRN_CHECKS=0'], False, workdir)
            program = disasm.Program(tools.disassemble(obj, workdir))
            failures, n = check_enclosure_program(program, expected, limb_types, where)
        except (Failure, ValueError) as e:
            out.append((f'{label(config)}, operations of Ball {label_}: FAILED: {e}', False))
            continue
        took = f'{time.time() - t0:.1f} s'
        head = f'{label(config)}, operations of Ball {label_}'
        if failures:
            out.append((f'{head}: FAILED, {len(failures)} of {n} functions ({took}):', False))
            out += [(f'    {text}', False) for _, text in failures]
        else:
            what = ('each a call of a function of the object with the counts of its kernel' if where == 'in'
                    else 'each a call of the external operation, nothing computed in the object')
            out.append((f'{head}: {n} functions, {what}: ok ({took})', True))
    return out


def describe(tally, n):
    parts = []
    if tally.get('each') or tally.get('distinct'):
        parts.append(f'where identical FMAs could be merged, each compiled in {tally.get("each", 0)} '
                     f'and merged in {tally.get("distinct", 0)}')
    if tally.get('consteval'):
        parts.append(f'the constant-evaluation branch emitted in {tally["consteval"]}')
    if tally.get('calls'):
        parts.append(f'{tally["calls"]} call other functions of the object')
    if tally.get('split'):
        parts.append(f'{tally["split"]} have a part of their own (F.cold)')
    return f'{n} functions' + (f' ({"; ".join(parts)})' if parts else '')


# --- The check ------------------------------------------------------------------------------------

def check_configuration(tools, config, index, workdir, expected, limb_types, folds=None):
    """[(text, ok)] of one configuration: the compiler's own form of the fix-ups, with the packed
    kernels, and where asked the other form, scalar only."""
    level, contraction, rounding, both = config
    options = (level,) + contraction + rounding
    out = []
    first = None
    packed = tools.packed != 'none'
    for pass_ in (0, 1) if both else (0,):
        obj = os.path.join(workdir, f'unit-{index}-{pass_}.{"obj" if tools.msvc_style else "o"}')
        t0 = time.time()
        if pass_ == 0:
            defines, with_packed = [], packed
        else:
            defines, with_packed = [f'KAIRN_GEN_FIXUP_CALL={0 if first == "scalar_call" else 1}'], False
        try:
            tools.compile(UNIT, obj, options, defines, with_packed, workdir)
            program = disasm.Program(tools.disassemble(obj, workdir))
            form = unit_form(program)
            failures, tally, n = check_program(program, expected, limb_types, with_packed, folds)
        except (Failure, ValueError) as e:
            out.append((f'{label(config)}: FAILED: {e}', False))
            continue
        first = first or form
        which = 'as calls' if form == 'scalar_call' else 'inline'
        own = "the compiler's own" if pass_ == 0 else 'the other'
        head = f'{label(config)}, fix-ups {which} ({own} form){", packed " + tools.packed if with_packed else ""}'
        took = f'{time.time() - t0:.1f} s'
        if failures:
            out.append((f'{head}: FAILED, {len(failures)} of {n} functions ({took}):', False))
            out += [(f'    {text}', False) for _, text in failures]
        else:
            out.append((f'{head}: {describe(tally, n)}: ok ({took})', True))
    # The operations of Ball outlined and external, in the configurations that compile both forms
    # of the fix-ups: every one of the full tier, and in the quick tier the one with contraction
    # forced on at -O2 or /O2.
    if both:
        out += check_enclosures(tools, config, index, workdir, expected, limb_types)
    return out


def check(tools, args, expected, limb_types, folds=None):
    configs = configurations(tools.family, args.tier)
    print(f'objcode: {tools.cxx_path} ({tools.name}, {tools.family} matrix, {args.tier} tier: '
          f'{len(configs)} configurations); disassembler {tools.disassembler} ({tools.flavor}); '
          f'packed: {tools.packed}{" with " + " ".join(tools.packed_flags) if tools.packed_flags else ""}; '
          f'options for every compilation: {" ".join(tools.flags) or "none"}', flush=True)
    if tools.packed == 'none':
        print('objcode: no packed backend for this target: the packed kernels are NOT checked')
    ok = True
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        jobs = [pool.submit(check_configuration, tools, c, i, args.workdir, expected, limb_types, folds)
                for i, c in enumerate(configs)]
        for job in jobs:
            for text, good in job.result():
                print('  ' + text, flush=True)
                ok = ok and good
    return ok


# --- The negative controls ------------------------------------------------------------------------

FIXTURE_COUNTS = {'fma': 0, 'fma_distinct': 0, 'mul': 1, 'mul_distinct': 1, 'consteval_mul': 0,
                  'muladd': 0}


def control_fixture(tools, config, index, workdir):
    """(lines, ok, fused functions) of the textbook fixture in one configuration."""
    level, contraction, rounding, _ = config
    options = (level,) + contraction + rounding
    obj = os.path.join(workdir, f'fixture-{index}.{"obj" if tools.msvc_style else "o"}')
    exe = os.path.join(workdir, f'fixture-{index}{".exe" if os.name == "nt" else ""}')
    packed = tools.packed != 'none'
    try:
        tools.compile(FIXTURE, obj, options, [], packed, workdir)
        tools.link(obj, exe, workdir)
        observed = {}
        for line in run(tools.emulator + [exe], workdir, 'running the fixture').splitlines():
            name, verdict = line.split()
            observed[name] = verdict
        program = disasm.Program(tools.disassemble(obj, workdir))
    except (Failure, ValueError) as e:
        return [f'{label(config)}: FAILED: {e}'], False, []
    lines, ok, fused = [], True, []
    for name, verdict in sorted(observed.items()):
        f = program.find(name)
        if f is None:
            lines.append(f'{name}: no such function in the disassembly')
            ok = False
            continue
        text, _ = judge(program.count(f), FIXTURE_COUNTS)
        if verdict not in ('fused', 'unfused'):
            lines.append(f'{name}: the program computed neither result ({verdict})')
            ok = False
        elif (text is not None) != (verdict == 'fused'):
            ok = False
            lines.append(f'{name}: {verdict} at run time, but the check '
                         f'{"failed: " + text if text else "passed"}')
        if verdict == 'fused':
            fused.append(name.replace('kairn_objcode_fixture_', ''))
    head = f'{label(config)}: ' + (f'fused {", ".join(fused)}; the check fails on exactly those'
                                   if fused else 'nothing fused; the check passes')
    return [head + ('' if ok else ': FAILED')] + ['    ' + x for x in lines], ok, fused


def control_counts(tools, workdir, expected, limb_types, folds=None):
    """(lines, ok): the unit judged against counts with two kernels changed."""
    config = next(c for c in configurations(tools.family, 'quick') if c[0] not in ('-O0', '/Od'))
    changed = copy.deepcopy(expected)
    for forms in changed['mul_2_2'].values():
        for e in forms.values():
            e['fma'] += 1
            e['fma_distinct'] += 1
    for forms in changed['add_2_2_full'].values():
        for e in forms.values():
            e['mul'] -= 1
            e['mul_distinct'] -= 1
    obj = os.path.join(workdir, f'unit-counts.{"obj" if tools.msvc_style else "o"}')
    packed = tools.packed != 'none'
    try:
        level, contraction, rounding, _ = config
        tools.compile(UNIT, obj, (level,) + contraction + rounding, [], packed, workdir)
        program = disasm.Program(tools.disassemble(obj, workdir))
        failures, _, n = check_program(program, changed, limb_types, packed, folds)
    except (Failure, ValueError) as e:
        return [f'wrong counts, {label(config)}: FAILED: {e}'], False
    failed = sorted({str(kernel) for kernel, _ in failures})
    ok = failed == ['add_2_2_full', 'mul_2_2'] and len(failures) == 2 * len(limb_types) * (1 + packed)
    return [f'wrong counts (mul_2_2 one FMA more, add_2_2_full one multiplication fewer), '
            f'{label(config)}: the check fails on {len(failures)} of {n} functions, of '
            f'{", ".join(failed) or "no kernel"}' + ('' if ok else ': FAILED, expected exactly the '
                                                      'functions of those two kernels')], ok


def control_enclosures(tools, workdir, expected, limb_types):
    """(lines, ok): enclosure_unit.cpp compiled with the operations of Ball inline, as by default,
    and judged as the outlined form: every function must fail, its operation not being a call."""
    config = next(c for c in configurations(tools.family, 'quick') if c[0] not in ('-O0', '/Od'))
    obj = os.path.join(workdir, f'enclosure-inline.{"obj" if tools.msvc_style else "o"}')
    try:
        level, contraction, rounding, _ = config
        tools.compile(ENCLOSURE_UNIT, obj, (level,) + contraction + rounding,
                      ['KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_INLINE', 'KAIRN_CHECKS=0'], False, workdir)
        program = disasm.Program(tools.disassemble(obj, workdir))
        failures, n = check_enclosure_program(program, expected, limb_types, 'in')
    except (Failure, ValueError) as e:
        return [f'the operations of Ball inline, judged as outlined, {label(config)}: FAILED: {e}'], False
    not_calls = [text for _, text in failures if 'the operation is not a call' in text]
    ok = n == len(ENCLOSURE_KERNELS) * len(limb_types) and len(not_calls) == n
    return [f'the operations of Ball inline (KAIRN_ENCLOSURE_CODE_INLINE), judged as outlined, {label(config)}: '
            f'the check fails on {len(not_calls)} of {n} functions as not a call'
            + ('' if ok else ': FAILED, expected every one')], ok


def controls(tools, args, expected, limb_types, folds=None):
    configs = configurations(tools.family, args.tier)
    print(f'objcode controls: {tools.cxx_path} ({tools.name}, {args.tier} tier: {len(configs)} '
          f'configurations); disassembler {tools.disassembler} ({tools.flavor})', flush=True)
    ok = True
    contracted = 0
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        jobs = [pool.submit(control_fixture, tools, c, i, args.workdir) for i, c in enumerate(configs)]
        counts = pool.submit(control_counts, tools, args.workdir, expected, limb_types, folds)
        enclosures = pool.submit(control_enclosures, tools, args.workdir, expected, limb_types)
        print('  The textbook a * b + c (fixture.cpp), judged against its source:')
        for job in jobs:
            lines, good, fused = job.result()
            contracted += bool(fused)
            ok = ok and good
            for line in lines:
                print('    ' + line, flush=True)
        lines, good = counts.result()
        ok = ok and good
        for line in lines:
            print('  ' + line)
        lines, good = enclosures.result()
        ok = ok and good
        for line in lines:
            print('  ' + line)
    if contracted == 0:
        ok = False
        print(f'  FAILED: no configuration fused the textbook product, so nothing shows that the '
              f'check catches a contraction with {tools.name}')
    else:
        print(f'  {contracted} of {len(configs)} configurations fused it, and the check failed on '
              f'exactly what was fused')
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cxx', required=True)
    p.add_argument('--style', choices=('gnu', 'msvc'), help='option style (default: from the name)')
    p.add_argument('--compiler-id', help="CMake's CMAKE_CXX_COMPILER_ID (tells clang-cl from cl)")
    p.add_argument('--flags', default='', help='options for every compilation (the FMA option, ...)')
    p.add_argument('--packed', choices=('neon', 'avx2', 'none'), help='the packed backend '
                   '(default: from the machine)')
    p.add_argument('--packed-flags', default='', help='the options the packed backend needs')
    p.add_argument('--disassembler', help='objdump, llvm-objdump or dumpbin (default: found)')
    p.add_argument('--workdir', required=True)
    p.add_argument('--tier', choices=('quick', 'full'), default='quick')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--expected', default=os.path.join(ROOT, 'gen', 'objcode.json'))
    p.add_argument('--controls', action='store_true', help='run the negative controls instead')
    p.add_argument('--emulator', default='', help='a command that runs the controls\' program, for a '
                   'compiler whose programs this machine cannot run (qemu-aarch64 -L SYSROOT)')
    args = p.parse_args()
    args.workdir = os.path.normpath(os.path.abspath(args.workdir))
    os.makedirs(args.workdir, exist_ok=True)
    t0 = time.time()
    try:
        tools = Tools(args)
        expected, limb_types = load_expected(args.expected)
        folds = load_fold_expected(args.expected)
        ok = (controls if args.controls else check)(tools, args, expected, limb_types, folds)
    except Failure as e:
        print(f'objcode: FAILED: {e}')
        return 1
    print(f'objcode: {"ok" if ok else "FAILED"} ({time.time() - t0:.0f} s)')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
