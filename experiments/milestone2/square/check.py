"""check.py: reads the output of square_kairn on standard input and judges, in exact arithmetic,
each line CASE against what its operation claims of the value v that the program passed in (the
rounded squares p and the operands c): whether the result computed with the squares in place
violates the claim, or only differs in bits. The result computed with the squares rounded first
is judged too, as a control (it must never violate).

  square_kairn | python3 check.py

Python 3 standard library only.
"""
import sys
from fractions import Fraction

FORMATS = {'double': (53, -1074), 'float': (24, -149)}


def hexf(s):
    return Fraction(float.fromhex(s))


def round_nearest(x, fmt):
    """x rounded to nearest, ties to even, in binary64 or binary32 (no overflow handled)."""
    p, emin_sub = FORMATS[fmt]
    if x == 0:
        return Fraction(0)
    sign = -1 if x < 0 else 1
    x = abs(x)
    e = x.numerator.bit_length() - x.denominator.bit_length()
    while Fraction(2) ** e > x:
        e -= 1
    while Fraction(2) ** (e + 1) <= x:
        e += 1
    q = max(e - p + 1, emin_sub)       # the exponent of the last place
    scaled = x / Fraction(2) ** q
    n = scaled.numerator // scaled.denominator
    r = scaled - n
    if r > Fraction(1, 2) or (r == Fraction(1, 2) and n % 2 == 1):
        n += 1
    return sign * n * Fraction(2) ** q


BOUNDS = {}  # (type, name) -> (unit, tiny), from the lines BOUND that square_kairn prints


def judge(kind, vop, fmt, p, c, z):
    """(whether z satisfies the claim kind of the exact value v, a phrase that says by how much).
    Every claim is read leniently (the larger constant where the statement has two), so that a
    verdict 'violates' is never an artefact of this check."""
    p_, _ = FORMATS[fmt]
    u = Fraction(1, 2 ** p_)
    if vop in ('+', '+f'):  # +f: the operands of fast_two_sum, |c| >= |p|
        v = p[0] + c[0]
    elif vop == '-':
        v = c[0] - p[0]
    elif vop == '1':
        v = p[0]
    elif vop == '+0':
        v = p[0] + c[0]
    elif vop == 'r':
        v = p[0] - c[0]
    elif vop == 'sum':
        v = sum(p) + sum(c)
    else:
        raise ValueError(vop)
    k = kind.split()
    if k[0] == 'pair':
        ok = z[0] + z[1] == v
        return ok, 'v0 + v1 - v = %s' % float(z[0] + z[1] - v)
    if k[0] == 'rn':
        ok = z[0] == round_nearest(v, fmt)
        return ok, 'v0 - RN(v) = %s' % float(z[0] - round_nearest(v, fmt))
    if k[0] == 'down':
        return z[0] <= v, 'v0 - v = %s' % float(z[0] - v)
    if k[0] == 'up':
        return z[0] >= v, 'v0 - v = %s' % float(z[0] - v)
    if k[0] == 'rel':
        K = Fraction(k[1])
        err = abs(z[0] + z[1] - v)
        lim = K * u * u * abs(v) / (1 - 4 * u)
        what = ('|error| / (u^2 |v|) = %.3g (claim %s/(1 - 4u))' % (float(err / (u * u * abs(v))), k[1]) if v
                else '|error| = %s with v = 0 (claim %s u^2 |v|)' % (float(err), k[1]))
        return err <= lim, what
    if k[0] == 'mulrel':
        # Expansion<T, 2>(1) * p (mul_2_1_entry, within 2u^2 |p|), then + Expansion<T, 2>(c) (add_2_2,
        # within 3u^2/(1 - 4u) of the sum of its operands).
        err = abs(z[0] + z[1] - v)
        lim = 2 * u * u * abs(p[0]) + 3 * u * u / (1 - 4 * u) * (abs(v) + 2 * u * u * abs(p[0]))
        return err <= lim, '|error| / bound = %.3g' % float(err / lim)
    if k[0] == 'set':
        return z[0] + z[1] <= v <= z[2] + z[3], 'lower - v = %s, upper - v = %s' % (
            float(z[0] + z[1] - v), float(z[2] + z[3] - v))
    if k[0] == 'ball':
        err = abs(v - z[0] - z[1])
        return err <= z[2], '|v - center| = %s, radius %s' % (float(err), float(z[2]))
    if k[0] == 'rad':
        return z[2] >= v, 'radius - (r1 + r2) = %s' % float(z[2] - v)
    if k[0] == 'sumb':
        unit, tiny = BOUNDS[(fmt, k[1])]
        terms = sum(abs(x) for x in p) + sum(abs(x) for x in c)
        lim = unit * terms + tiny
        err = abs(z[0] + z[1] - v)
        return err <= lim, '|error| = %s, bound %s' % (float(err), float(lim))
    raise ValueError(kind)


def main():
    """One line per row (form.family type) that has cases: how many violate, and one case (the
    first that violates, otherwise the first), followed by that case's line CASE."""
    rows = {}
    order = []
    controls = 0
    for line in sys.stdin:
        t = line.split()
        if line.startswith('BOUND '):
            BOUNDS[(t[1], t[2])] = (hexf(t[3]), hexf(t[4]))
            continue
        if not line.startswith('CASE '):
            continue
        name, fmt = t[1], t[2]
        try:
            i = t.index('p', 3)
            kind, vop = ' '.join(t[3:i - 1]), t[i - 1]
            j = t.index('c', i)
            p = [hexf(x) for x in t[i + 1:j]]
            k = t.index('in', j)
            c = [hexf(x) for x in t[j + 1:k]]
            r = t.index('rounded', k)
            z_in = [hexf(x) for x in t[k + 1:r]]
            z_ro = [hexf(x) for x in t[r + 1:]]
            if len(z_ro) != 4:
                raise ValueError('a short line')
        except ValueError:
            print('%-27s %-6s a truncated line CASE (the program stopped?), not judged' % (name, fmt))
            continue
        ok_in, what_in = judge(kind, vop, fmt, p, c, z_in)
        ok_ro, what_ro = judge(kind, vop, fmt, p, c, z_ro)
        key = (name, fmt)
        if key not in rows:
            rows[key] = []
            order.append(key)
        rows[key].append((ok_in, what_in, ok_ro, what_ro, line.strip()))
    for key in order:
        cases = rows[key]
        bad = [x for x in cases if not x[0]]
        ok_in, what_in, ok_ro, what_ro, line = (bad or cases)[0]
        failed = [x for x in cases if not x[2]]
        controls += len(failed)
        verdict = ('VIOLATES the claim in %d of %d cases judged' % (len(bad), len(cases)) if bad
                   else 'only the bits differ in %d cases judged' % len(cases))
        print('%-27s %-6s %s; in place: %s; rounded first: %s%s' % (
            key[0], key[1], verdict, what_in, what_ro,
            '' if not failed else ' (THE CONTROL VIOLATES in %d cases: a fault of this check)' % len(failed)))
        print('    %s' % line)
    return 1 if controls else 0


if __name__ == '__main__':
    sys.exit(main())
