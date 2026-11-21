"""tests/emulated/gen/kernels.hpp: every kernel and fold for the emulated limb type of the
exhaustive tier (tests/emulated/number.hpp; docs/developer/testing.md, "The emulated formats").

The kernels are printed by the printer of include/kairn/gen/scalar.hpp (cpp.scalar), with the limb
type kairn::emulated::Number (cpp.Limb) in place of double and float: the same functions, in the
same order, with the same statements, the same fix-up branches and the same inlined calls. What
the type changes is only what depends on the type: its name, the literals (a constant of the
format is the format's own value, constant(i), since the format is chosen at run time),
__builtin_is_constant_evaluated() (a mode of the runner), and constexpr, which a type computed at
run time has no use for (gen/tests/test_emulated.py compares the two listings token for token).
It is a test file, written under tests/ and not shipped.

After the kernels, the tables the runner (tests/emulated/runner.cpp) needs: the names of the
constants by index, their exact values in each format of FORMATS, computed by consts.py as the
literals of double and float are, and the kernels that have no path of constant evaluation.
"""
from fractions import Fraction

from . import consts, cpp, ir

PATH = 'tests/emulated/gen/kernels.hpp'
NAME = 'kairn::emulated::Number'

# The formats whose constants the runner has: binary64 and binary32 (where the emulated kernels are
# compared with the compiled ones, bit for bit), and the formats of the statements (architecture.md,
# "The formats of the statements": qmax >= 1 and qmin = 3 - qmax - 2p) of precision 8 to 11 with
# a few exponent ranges, the smallest first. Every constant of every kernel must be a number of
# each (header() refuses one that is not), so that the runner never meets a kernel it must refuse.
PRECISIONS = (8, 9, 10, 11)
QMAX = (1, 2, 3, 4, 6, 8, 12, 16)


def formats():
    """[(name, p, qmin, qmax)]: the formats of the runner, in the order of the table."""
    out = [('binary64', 53, -1074, 971), ('binary32', 24, -149, 104)]
    for p in PRECISIONS:
        for qmax in QMAX:
            qmin = 3 - qmax - 2 * p
            out.append((f'fp:{p}:{qmin}:{qmax}', p, qmin, qmax))
    return out


def constant_names(kernels):
    """Every constant the kernels name, the zero first, then in sorted order (+inf and NaN are
    spelled through std::numeric_limits, as for double)."""
    names = {a.name for k in kernels.values() for st in k.body for a in st.args if a.const}
    return [ir.ZERO] + sorted(names - {ir.ZERO} - set(ir.SPECIAL))


def limb(kernels):
    names = constant_names(kernels)
    return cpp.Limb(NAME, 'kairn::emulated::constant({0})', {n: i for i, n in enumerate(names)},
                    'kairn::emulated::constant_evaluation()', 'kairn::emulated::pow2(64)')


def _literal(v):
    v = Fraction(v)
    return '0x0p+0' if v == 0 else cpp.hex_literal(v, '')


def _string(text):
    if '"' in text or '\\' in text:
        raise cpp.PrintError(f'constant {text!r} cannot be written as a C++ string')
    return f'"{text}"'


INTRO = [
    '// Scalar kernels for the emulated limb type kairn::emulated::Number (tests/emulated/number.hpp),',
    '// a format chosen at run time: the kernels of include/kairn/gen/scalar.hpp, printed by the same',
    '// printer (gen/kairn_gen/cpp.py) with this type in place of double and float. A constant of the',
    '// format is kairn::emulated::constant(i), the value of the i-th of the constants listed at the',
    '// end in the runner\'s format; kairn::emulated::constant_evaluation() stands for',
    '// __builtin_is_constant_evaluated(), a mode of the runner; nothing is constexpr. A test file',
    '// (docs/developer/testing.md, "The emulated formats"), not shipped. Inputs are passed by value;',
    '// outputs by reference, each written once on the path']


def header(kernels):
    names = constant_names(kernels)
    text = cpp.scalar(kernels, prelude_name='../prelude.hpp', types=(limb(kernels),), intro=INTRO)
    lines = ['', '// --- The tables of the runner (tests/emulated/runner.cpp).',
             'namespace kairn::emulated::generated {', '',
             '// The constants the kernels above name, by index: constant(i) is constant_names[i].',
             f'inline constexpr int constant_count = {len(names)};',
             'inline constexpr const char* constant_names[constant_count] = {']
    lines += [f'    {_string(n)},' for n in names]
    lines += ['};', '',
              '// Their exact values in each format of the runner (gen/kairn_gen/emulated.py, FORMATS),',
              '// as consts.py computes them for the literals of double and float.',
              'struct FormatConstants {',
              '    const char* name;',
              '    int p, qmin, qmax;',
              '    const char* values[constant_count];',
              '};',
              f'inline constexpr int format_count = {len(formats())};',
              'inline constexpr FormatConstants formats[format_count] = {']
    for fname, p, qmin, qmax in formats():
        values = []
        for n in names:
            try:
                values.append(_literal(consts.value(n, kernels, p, qmin, qmax)))
            except consts.ConstError as e:
                raise cpp.PrintError(f'constant {n} in {fname}, a format of the emulated runner: {e}')
        lines.append(f'    {{"{fname}", {p}, {qmin}, {qmax}, {{')
        lines += [f'        "{v}",' for v in values]
        lines.append('    }},')
    plain = [k.name for k in kernels.values() if cpp.constexpr_kind(k, kernels) is None]
    lines += ['};', '',
              '// The kernels that have no path of constant evaluation (a fused operation other than prod',
              '// and no constant-evaluation variant): the runner refuses them with --ce, as the',
              '// interpreter does with --ce, and every fold.',
              f'inline constexpr int not_constexpr_count = {len(plain)};',
              'inline constexpr const char* not_constexpr[not_constexpr_count + 1] = {']
    lines += [f'    "{n}",' for n in plain] + ['    nullptr,', '};', '',
              '}  // namespace kairn::emulated::generated']
    return text + '\n'.join(lines) + '\n'
