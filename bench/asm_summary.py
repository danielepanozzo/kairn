#!/usr/bin/env python3
"""Summarizes the loops of the benchmark's timed functions in a disassembly (bench/README.md).

    objdump -d --no-show-raw-insn BINARY | python3 bench/asm_summary.py [--json OUT] [PATTERN ...]
    dumpbin /disasm:nobytes OBJECT ... | python3 bench/asm_summary.py ...

Reads the output of GNU objdump or LLVM objdump (ELF or Mach-O, x86-64 or AArch64) or of MSVC's
dumpbin on standard input. For every function whose name starts with kb_ (and contains one of the
PATTERNs, if given) it finds the loops, as the spans closed by a backward branch, and counts in
each the instructions of a few kinds: fused multiply-adds, plain multiplications, additions and
subtractions, comparisons, selects (conditional moves, blends, bit selects), mask logic,
branches, calls. A loop is "vector" when its floating-point arithmetic is on packed registers;
the width is the widest register used. Standard library only.
"""
import json
import re
import sys

LABEL = [re.compile(r'^(?:[0-9a-fA-F]+\s+)?<_?(kb_\w+)>:\s*$'),   # objdump
         re.compile(r'^_?(kb_\w+):\s*$')]                            # dumpbin
INSN = re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:(?:[0-9a-fA-F]{2}\s)+\s*)?([a-zA-Z][\w.]*)\s*(.*)$')
TARGET = re.compile(r'\b(?:0x)?([0-9a-fA-F]{4,})\b')

KINDS = [
    ('fma', re.compile(r'^(vfn?m(add|sub)(sub|add)?\d{3}[sp][sd]|fn?madd|fn?msub|fmla|fmls)(\.\w+)?$')),
    ('mul', re.compile(r'^(v?mul[sp][sd]|fn?mul)(\.\w+)?$')),
    ('addsub', re.compile(r'^(v?(add|sub)[sp][sd]|fadd|fsub)(\.\w+)?$')),
    ('cmp', re.compile(r'^(v?u?comis[sd]|v?cmp\w*[sp][sd]|vpcmp\w+|pcmp\w+|fcm\w*|fcmp|fcmpe|fac\w+|cm(eq|gt|ge|hi|hs|lt|le)|cmp|test)(\.\w+)?$')),
    ('select', re.compile(r'^(v?p?blendv\w*|v?blend[sp][sd]|cmov\w+|fcsel|csel|csinc|csinv|csneg|bsl|bit|bif)(\.\w+)?$')),
    ('logic', re.compile(r'^(v?p?(and|andn|or|xor)([sp][sd]|q|d)?|and|orr|eor|bic|orn|mvn|not)(\.\w+)?$')),
    ('branch', re.compile(r'^(j[a-z]+|b\.\w+|b|cbn?z|tbn?z)$')),
    ('call', re.compile(r'^(call\w*|bl|blr)$')),
]
FP_ARITH = ('fma', 'mul', 'addsub')


def width(mnemonic, operands):
    """Bits of the widest FP register an arithmetic instruction uses, 64 for scalar."""
    text = mnemonic + ' ' + operands
    if 'ymm' in text:
        return 256
    if re.search(r'\.(2d|4s)\b', text):                      # AArch64 vector arrangement
        return 128
    if mnemonic.endswith(('pd', 'ps')) and 'xmm' in text:    # x86 packed, 128-bit
        return 128
    return 64


def parse(lines):
    funcs = {}
    current = None
    for line in lines:
        line = line.rstrip('\n')
        name = None
        for pattern in LABEL:
            m = pattern.match(line.strip()) if pattern is LABEL[1] else pattern.match(line)
            if m:
                name = m.group(1)
                break
        if name:
            current = funcs.setdefault(name, [])
            continue
        if current is None:
            continue
        m = INSN.match(line)
        if not m:
            if line.strip() == '' or line.startswith('Disassembly'):
                continue
            continue
        addr, mnemonic, operands = int(m.group(1), 16), m.group(2).lower(), m.group(3)
        current.append((addr, mnemonic, operands))
    return funcs


def kind_of(mnemonic):
    base = mnemonic
    for k, pattern in KINDS:
        if pattern.match(base):
            return k
    return None


def loops(insns):
    """(start, end) index spans closed by a backward branch, innermost first by size."""
    index = {a: i for i, (a, _, _) in enumerate(insns)}
    spans = []
    for i, (addr, mnemonic, operands) in enumerate(insns):
        if kind_of(mnemonic) != 'branch':
            continue
        for t in TARGET.findall(operands):
            target = int(t, 16)
            if target in index and target <= addr:
                spans.append((index[target], i))
                break
    return sorted(set(spans), key=lambda s: s[1] - s[0])


def summarize(insns, span):
    counts = {k: 0 for k, _ in KINDS}
    w = 64
    for addr, mnemonic, operands in insns[span[0]:span[1] + 1]:
        k = kind_of(mnemonic)
        if k:
            counts[k] += 1
        if k in FP_ARITH:
            w = max(w, width(mnemonic, operands))
    counts['instructions'] = span[1] - span[0] + 1
    counts['vector_bits'] = w if w > 64 else 0
    return counts


def main(argv):
    out = None
    patterns = []
    i = 0
    while i < len(argv):
        if argv[i] == '--json':
            out = argv[i + 1]
            i += 2
            continue
        patterns.append(argv[i])
        i += 1
    funcs = parse(sys.stdin)
    result = {}
    for name in sorted(funcs):
        if patterns and not any(p in name for p in patterns):
            continue
        insns = funcs[name]
        result[name] = {'instructions': len(insns),
                        'loops': [summarize(insns, s) for s in loops(insns)]}
    cols = ['instructions', 'vector_bits'] + [k for k, _ in KINDS]
    print('%-40s %5s  %s' % ('function / loop', 'total', '  '.join('%6s' % c[:6] for c in cols)))
    for name, r in result.items():
        if not r['loops']:
            print('%-40s %5d  (no loop)' % (name, r['instructions']))
        for j, lp in enumerate(r['loops']):
            print('%-40s %5s  %s' % (name if j == 0 else '', r['instructions'] if j == 0 else '',
                                     '  '.join('%6d' % lp[c] for c in cols)))
    if out:
        # Compact: one row of numbers per loop, in the order of "columns".
        items = sorted(result.items())
        with open(out, 'w') as f:
            f.write('{"columns": %s,\n "functions": {\n' % json.dumps(cols))
            for j, (name, r) in enumerate(items):
                row = {'instructions': r['instructions'], 'loops': [[lp[c] for c in cols] for lp in r['loops']]}
                f.write('  %s: %s%s\n' % (json.dumps(name), json.dumps(row), ',' if j + 1 < len(items) else ''))
            f.write(' }}\n')
    if not result:
        print('no kb_ function found', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
