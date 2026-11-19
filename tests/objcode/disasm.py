"""Reading a disassembly: functions, their instructions, and what they call (objcode.py).

Reads the output of GNU objdump and LLVM objdump (`-d -r`, ELF, Mach-O or COFF objects, x86-64 or
AArch64) and of MSVC's dumpbin (`/disasm`), for an object file that has not been linked. Standard
library only; tested on stored samples of every format by test_objcode.py.

Of the instructions it knows three kinds:

- fused multiply-adds: x86 `vfmadd`, `vfmsub`, `vfnmadd`, `vfnmsub` (132, 213, 231; scalar and
  packed), `vfmaddsub`, `vfmsubadd`; AArch64 `fmadd`, `fmsub`, `fnmadd`, `fnmsub`, `fmla`, `fmls`;
- plain floating-point multiplications: x86 `mulsd`, `mulss`, `mulpd`, `mulps` and their `v` forms,
  x87 `fmul`; AArch64 `fmul`, `fnmul`, `fmulx`;
- calls and jumps. Where one goes is read from the relocation on the instruction when there is
  one (in an object file, a call to another function always has one, which GNU and LLVM objdump
  print with -r and dumpbin prints as the operand), and otherwise from the target the disassembler
  printed. A jump within the function is not a call.

The mnemonics are those of every syntax these tools print: AT&T and Intel for x86, and both GNU's
`fmla v0.2d, ...` and LLVM's Apple form `fmla.2d v0, ...` for AArch64.

A function's counts include those of every function of the object it calls or jumps to, once per
call site, and of its parts that GCC moves to a section of their own (`F.cold`, hot and cold
splitting): what the code of a kernel executes may be spread over several symbols (a fix-up of its
own, `fixup::K`; without optimization, the helpers `fma_rn`, `std::bit_cast`, ...).
"""
import re
from dataclasses import dataclass, field

FUSED = re.compile(r'^(v?fn?m(add|sub)(132|213|231)?[sp][sd]|vfm(addsub|subadd)(132|213|231)?p[sd]'
                   r'|fn?m(add|sub)|fml[as]l?2?)(\.\w+)?$')
MUL = re.compile(r'^(v?mul[sp][sd]|fmulp?|fimul|fn?mulx?)(\.\w+)?$')
CALL = re.compile(r'^(callq?|bl|blr)$')
JUMP = re.compile(r'^(jmpq?|j[a-z]{1,4}|b|br|b\.[a-z]{2}|cbn?z|tbn?z)$')
PREFIXES = frozenset({'notrack', 'bnd', 'rep', 'repz', 'repe', 'repnz', 'repne', 'lock', 'data16',
                      'addr32', 'cs', 'ds', 'es', 'ss', 'fs', 'gs', '{vex}', '{evex}', '{vex3}'})

# Routines a function may call outside the object without making its count incomplete, none of
# which computes with floating-point numbers: the stack protector's, which compare a canary and
# abort (Ubuntu's GCC protects functions by default, MSVC and clang-cl with /GS), and Windows' stack
# probe for a large frame. Leading underscores are not part of the comparison.
ALLOWED_EXTERNAL = frozenset({'stack_chk_fail', 'security_check_cookie', 'chkstk'})

# GNU and LLVM objdump
SECTION = re.compile(r'^Disassembly of section (.+?):?\s*$')
LABEL = re.compile(r'^([0-9a-fA-F]+) <(.+)>:\s*$')
RELOC = re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:R_|ARM64_RELOC_|X86_64_RELOC_|IMAGE_REL_)\w+)\s+(\S+)')
INSN = re.compile(r'^\s*([0-9a-fA-F]+):\s+(.*?)\s*$')
TARGET = re.compile(r'(?:^|[\s,])(?:0x)?([0-9a-fA-F]+) <[^<>]+>')
# dumpbin
DUMPBIN = re.compile(r'^Dump of file ', re.M)
DUMPBIN_LABEL = re.compile(r'^(\S+?)(?: \(.*\))?:\s*$')
DUMPBIN_INSN = re.compile(r'^\s+([0-9A-Fa-f]{8,16}):\s+(.*?)\s*$')
DUMPBIN_BYTES = re.compile(r'^(?:[0-9A-F]{2} )+\s*')
ADDRESS = re.compile(r'^(?:0x)?[0-9a-fA-F]+h?$')
REGISTER = re.compile(r'^(?:[xw]\d+|[re]?(?:ax|bx|cx|dx|si|di|bp|sp)|r\d+[dwb]?|%\w+)$')

# A part of a function that GCC moved to a section of its own: its code is the function's.
COLD = re.compile(r'^(.+?)\.cold(?:\.\d+)?$')
# Labels that LLVM objdump prints with --show-all-symbols and that are no function: MSVC's local
# labels ($LN3), Mach-O's temporary ones (ltmp0), and section symbols (.text$mn). Each is at the
# address of a function's own symbol, or within a function.
LOCAL = re.compile(r'^(?:\$LN\d+|ltmp\d+|\..*)$')


@dataclass
class Insn:
    addr: int
    mnemonic: str
    operands: str
    relocs: list = field(default_factory=list)   # the relocations within the instruction


@dataclass
class Function:
    names: list
    section: str     # its section's name
    segment: int     # which section: several may have one name (COFF's COMDAT sections, .text$mn)
    addr: int
    line: int        # the line of the disassembly with its first label, from 1
    insns: list = field(default_factory=list)


@dataclass
class Count:
    """What one function executes, with what it calls: the instructions of each kind as
    (function, mnemonic and operands), and the calls the count cannot follow."""
    fma: list = field(default_factory=list)
    mul: list = field(default_factory=list)
    external: list = field(default_factory=list)     # (function, symbol) outside the object
    unknown: list = field(default_factory=list)      # (function, instruction): indirect, unresolved
    calls: list = field(default_factory=list)        # names of the functions it calls, per site

    def add(self, other):
        for name in ('fma', 'mul', 'external', 'unknown', 'calls'):
            getattr(self, name).extend(getattr(other, name))


def _split(text):
    """(mnemonic, operands) of an instruction's text, prefixes dropped, the mnemonic in lower
    case."""
    words = text.split(None, 1)
    while len(words) > 1 and words[0].lower() in PREFIXES:
        words = words[1].split(None, 1)
    if not words:
        return '', ''
    return words[0].lower(), (words[1] if len(words) > 1 else '')


def _symbol(text):
    """The symbol of a relocation, without its addend or a GOT or PLT suffix: foo-0x4 -> foo.
    (An MSVC name ends with @Z, which is part of it.)"""
    return re.sub(r'@(?:PLT|plt|GOT\w*|got\w*)$', '', re.sub(r'[+-]0x[0-9a-fA-F]+$', '', text))


def _addend(text):
    m = re.search(r'([+-])0x([0-9a-fA-F]+)$', text)
    return 0 if not m else int(m.group(2), 16) * (-1 if m.group(1) == '-' else 1)


def parse(text):
    """The functions of a disassembly, in order. Labels at one address with no instruction
    between them name one function (aliases); local labels are not functions (LOCAL)."""
    if DUMPBIN.search(text):
        return _parse_dumpbin(text)
    return _parse_objdump(text)


def _parse_objdump(text):
    funcs = []
    section, segment = '', 0
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        m = SECTION.match(line)
        if m:
            section, segment, current = m.group(1), segment + 1, None
            continue
        m = LABEL.match(line)
        if m:
            addr, name = int(m.group(1), 16), m.group(2)
            if LOCAL.match(name):
                continue
            if current is not None and not current.insns and current.addr == addr:
                current.names.append(name)
            else:
                current = Function([name], section, segment, addr, number)
                funcs.append(current)
            continue
        if current is None:
            continue
        m = RELOC.match(line)
        if m:
            if current.insns:
                current.insns[-1].relocs.append(m.group(3))
            continue
        m = INSN.match(line)
        if m:
            mnemonic, operands = _split(m.group(2))
            if mnemonic and mnemonic != '...':
                current.insns.append(Insn(int(m.group(1), 16), mnemonic, operands))
    return funcs


def _parse_dumpbin(text):
    funcs = []
    current = None
    for number, line in enumerate(text.splitlines(), 1):
        m = DUMPBIN_LABEL.match(line)
        if m and not line.startswith(('Dump of file', 'File Type', 'Summary')):
            name = m.group(1)
            if current is not None and not current.insns:
                current.names.append(name)
            else:
                current = Function([name], '', 0, 0, number)
                funcs.append(current)
            continue
        if current is None:
            continue
        m = DUMPBIN_INSN.match(line)
        if m:
            mnemonic, operands = _split(DUMPBIN_BYTES.sub('', m.group(2)))
            if mnemonic:
                current.insns.append(Insn(int(m.group(1), 16), mnemonic, operands))
    return funcs


def kind(mnemonic):
    """'fma', 'mul', 'call', 'jump' or None."""
    if FUSED.match(mnemonic):
        return 'fma'
    if MUL.match(mnemonic):
        return 'mul'
    if CALL.match(mnemonic):
        return 'call'
    if JUMP.match(mnemonic):
        return 'jump'
    return None


def allowed_external(symbol):
    return symbol.lstrip('_') in ALLOWED_EXTERNAL


class Program:
    """The functions of one disassembly, by name, and what each executes (count)."""

    def __init__(self, text):
        self.functions = parse(text)
        self.by_name = {}
        for f in self.functions:
            for n in f.names:
                self.by_name.setdefault(n, f)
        self.by_segment = {}
        self.segments = {}       # section name -> the segments of that name
        for f in self.functions:
            self.by_segment.setdefault(f.segment, []).append(f)
            self.segments.setdefault(f.section, set()).add(f.segment)
        self.parts = {}          # id of a function -> it and its parts (F.cold)
        for f in self.functions:
            self.parts.setdefault(id(self.owner(f)), []).append(f)
        self._counts = {}

    def find(self, name):
        """The function of that name, also with Mach-O's leading underscore, or None."""
        return self.by_name.get(name) or self.by_name.get('_' + name)

    def owner(self, f):
        """The function that a part belongs to: GCC's F.cold belongs to F."""
        for n in f.names:
            m = COLD.match(n)
            if m and self.by_name.get(m.group(1)) is not None:
                return self.by_name[m.group(1)]
        return f

    def _at(self, segment, offset):
        """The function of a section that contains an offset, or None."""
        best = None
        for f in self.by_segment.get(segment, []):
            if f.addr <= offset and (best is None or f.addr > best.addr):
                best = f
        return best

    def target(self, f, insn):
        """Where a call or a jump goes: ('internal', None), ('function', Function),
        ('external', symbol) or ('unknown', text)."""
        if insn.relocs:
            text = insn.relocs[0]
            sym = _symbol(text)
            if sym.startswith('__imp_'):
                sym = sym[len('__imp_'):]
            g = self.by_name.get(sym)
            if g is None and (sym.startswith('.') or sym in self.segments):
                # Relocated against a section: the target is the section plus the addend, plus 4
                # on x86-64, whose displacement counts from the end of its 4 bytes.
                segments = self.segments.get(sym, set())
                if len(segments) != 1:
                    return 'unknown', text
                g = self._at(next(iter(segments)),
                             _addend(text) + (4 if insn.mnemonic.startswith(('call', 'j')) else 0))
                if g is None:
                    return 'unknown', text
            if g is None:
                return 'external', sym
            return self._edge(f, g)
        m = TARGET.search(insn.operands)
        if m:
            # objdump prints the target's address, then the nearest symbol before it: the
            # address says which function of the section it is in.
            g = self._at(f.segment, int(m.group(1), 16))
            if g is None:
                return 'unknown', insn.operands
            if g.addr != int(m.group(1), 16) and self.owner(g) is not self.owner(f):
                return 'unknown', insn.operands      # into the middle of another function
            return self._edge(f, g)
        last = insn.operands.split(',')[-1].strip()
        if not last or ADDRESS.match(last):
            return 'internal', None                  # an address in the function (dumpbin)
        if REGISTER.match(last) or '[' in insn.operands or '*' in insn.operands:
            return 'unknown', insn.operands          # indirect
        g = self.by_name.get(last)
        if g is None:
            return 'external', last[len('__imp_'):] if last.startswith('__imp_') else last
        return self._edge(f, g)

    def _edge(self, f, g):
        if self.owner(g) is self.owner(f):
            return 'internal', None
        return 'function', self.owner(g)

    def count(self, f, _active=()):
        """The Count of function f: its instructions, those of its parts, and those of every
        function it calls or jumps to, once per call site."""
        key = id(f)
        if key in self._counts:
            return self._counts[key]
        if key in _active:
            raise ValueError(f'{f.names[0]} calls itself, directly or not: nothing to count')
        c = Count()
        for part in self.parts.get(id(f), [f]):
            name = part.names[0]
            for insn in part.insns:
                k = kind(insn.mnemonic)
                if k in ('fma', 'mul'):
                    getattr(c, k).append((name, f'{insn.mnemonic} {insn.operands}'.strip()))
                elif k in ('call', 'jump'):
                    what, t = self.target(part, insn)
                    if what == 'function':
                        c.calls.append(t.names[0])
                        c.add(self.count(t, _active + (key,)))
                    elif what == 'external' and not allowed_external(t):
                        c.external.append((name, t))
                    elif what == 'unknown':
                        c.unknown.append((name, f'{insn.mnemonic} {insn.operands}'.strip()))
        self._counts[key] = c
        return c
