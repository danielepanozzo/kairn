#!/usr/bin/env python3
"""rational(num, den): a model, in integer arithmetic only, of the constexpr function, judged
against its specification computed with exact rationals.

Specification (milestone2.md, "Constants at compile time"), for integers num and den != 0 and
q = num / den:

  k = 1   z = RN(q);
  k = 2   z is the normalized pair of value RN(q) + RN(q - RN(q)) (unique: the leading limb of a
          normalized pair is the rounding of its value);
  error   the smallest number of T not below |z - q|;
  exact   true exactly when z = q.

RN is the format's rounding, with gradual underflow (the second limb of a float pair can be
subnormal). The model below uses integers only: shifts, one division with remainder per limb,
comparisons. It also records the widest integer it forms, which is what the fixed capacity of
the C++ integer must hold.
"""
import random
import sys
from fractions import Fraction

from common import fmt, normalized, rn, ru

WIDEST = 0


def note(*ints):
    global WIDEST
    for i in ints:
        WIDEST = max(WIDEST, abs(i).bit_length())


def round_div(n, d, p, emin_q):
    """For integers n >= 0, d > 0: (Q, e, R, D) with n / d = (Q + R / D) 2^e exactly, Q the
    integer nearest to n / (d 2^e) (ties to even), 0 <= Q <= 2^p, |R| <= D / 2, and e the exponent
    that gives Q exactly p bits, or emin_q if that is larger (gradual underflow)."""
    if n == 0:
        return 0, emin_q, 0, d
    e = n.bit_length() - d.bit_length() - p          # then 2^(p-1) <= n / (d 2^e) < 2^(p+1)
    if (n << max(-e, 0)) >= ((d << max(e, 0)) << p):
        e += 1                                       # now 2^(p-1) <= n / (d 2^e) < 2^p
    e = max(e, emin_q)
    N, D = n << max(-e, 0), d << max(e, 0)
    note(N, D)
    Q, R = divmod(N, D)
    if 2 * R > D or (2 * R == D and Q % 2 == 1):
        Q, R = Q + 1, R - D
    note(2 * R)
    return Q, e, R, D


def round_up_div(n, d, p, emin_q):
    """The smallest number m 2^e of the format (m < 2^p, e >= emin_q) not below n / d, as (m, e)."""
    if n == 0:
        return 0, emin_q
    e = n.bit_length() - d.bit_length() - p
    if (n << max(-e, 0)) >= ((d << max(e, 0)) << p):
        e += 1
    e = max(e, emin_q)
    N, D = n << max(-e, 0), d << max(e, 0)
    note(N, D)
    return -((-N) // D), e                           # a carry to 2^p is 2^(p-1) 2^(e+1): still a number


def rational(num, den, p, qmin, k):
    """((limbs as (signed integer, exponent)), (error as (integer, exponent)), exact)."""
    s = -1 if (num < 0) != (den < 0) else 1
    n, d = abs(num), abs(den)
    Q0, e0, R0, D0 = round_div(n, d, p, qmin)
    if k == 1:
        return [(s * Q0, e0)], _error(abs(R0), D0, e0, p, qmin), R0 == 0
    if R0 == 0:
        return [(s * Q0, e0), (0, e0)], (0, e0), True
    # The second limb: RN of the remainder R0 2^e0 / D0, in the same format.
    s1 = s if R0 >= 0 else -s
    Q1, e1, R1, D1 = round_div(abs(R0), D0, p, qmin - e0)
    e1 += e0
    # Renormalize: the sum limb0 + limb1 as one integer times 2^e1 (e1 <= e0), rounded to p bits.
    S = s * (Q0 << (e0 - e1)) + s1 * Q1
    note(S)
    hi, lo = _round_int(S, e1, p, qmin)
    err = _error(abs(R1), D1, e1, p, qmin)
    return [hi, lo], err, R1 == 0


def _round_int(S, e, p, qmin):
    """The pair (RN(S 2^e), S 2^e - RN(S 2^e)) for an integer S, both as (integer, exponent)."""
    a = abs(S)
    drop = max(a.bit_length() - p, 0)
    if drop == 0:
        return (S, e), (0, e)
    Q, R = a >> drop, a & ((1 << drop) - 1)
    half = 1 << (drop - 1)
    if R > half or (R == half and Q % 2 == 1):
        Q, R = Q + 1, R - (1 << drop)
    sg = -1 if S < 0 else 1
    return (sg * Q, e + drop), (sg * R, e)


def _error(r, D, e, p, qmin):
    """The smallest number of the format not below r 2^e / D."""
    m, ee = round_up_div(r, D, p, qmin - e)
    return m, ee + e


def as_fraction(t):
    return Fraction(t[0]) * Fraction(2) ** t[1]


def spec(q, f, k):
    z0 = rn(f, q)
    if k == 1:
        z = [z0]
    else:
        z1 = rn(f, q - z0)
        s = rn(f, z0 + z1)
        z = [s, z0 + z1 - s]
    total = sum(z)
    return z, ru(f, abs(total - q)), total == q


def check(num, den, f, k):
    limbs, err, exact = rational(num, den, f.p, f.qmin, k)
    z, beta, ex = spec(Fraction(num, den), f, k)
    got = [as_fraction(t) for t in limbs]
    assert got == z, (f.name, k, num, den, got, z)
    assert as_fraction(err) == beta and exact == ex, (f.name, k, num, den)
    if k == 2:
        assert normalized(f, *got), (f.name, num, den)
    # Whether the renormalization moved the leading limb away from RN(q): the tie of the page.
    return k == 2 and got[0] != rn(f, Fraction(num, den))


def near_ties(p, rng, count, bits):
    """Fractions num / den within 1 / (den 2^j) of a midpoint of two numbers of precision p: the
    cases where the second limb rounds to half the gap of the first."""
    out = []
    while len(out) < count:
        j = rng.randint(p, min(bits - 2, p + 6))
        A = rng.randrange(1 << (j - 1), 1 << j) | 1            # the midpoint A / 2^j, A odd
        inv = pow(A, -1, 1 << j)
        sign = rng.choice((1, -1))
        base = (-sign * inv) % (1 << j)                         # den = base (mod 2^j) gives A den + sign = 0 (mod 2^j)
        top = ((1 << (bits - 1)) - 1 - base) >> j
        if top < 1:
            continue
        den = base + (rng.randrange(1, top + 1) << j)
        num = (A * den + sign) >> j
        if 0 < num < 1 << (bits - 1) and (num << j) - A * den == sign:
            out.append((num, den))
    return out


def main():
    global WIDEST
    rng = random.Random(20261119)
    # Every fraction with small terms, in toy formats whose second limb can underflow.
    for p, qmin in ((3, -9), (4, -11), (5, -14)):
        f = fmt(p, qmin, 60)
        n = moved = 0
        for den in range(1, 48):
            for num in range(-47, 48):
                for k in (1, 2):
                    moved += bool(check(num, den, f, k)) and k == 2
                    n += 1
        ties = near_ties(p, rng, 3000, 16)
        for num, den in ties:
            for k in (1, 2):
                moved += bool(check(num, den, f, k)) and k == 2
        print(f'{f.name:12} {n} results with |num|, den < 48 and {2 * len(ties)} near ties with 15-bit terms: '
              f'all equal to the specification; leading limb moved by the renormalization in {moved}')
    for name, p, qmin in (('binary64', 53, -1074), ('binary32', 24, -149)):
        f = fmt(p, qmin, 2000)
        WIDEST = 0
        cases = [(1, 3), (-1, 3), (1, 10), (2, 3), (1, 1), (0, 5), (7, -7), (2 ** 63 - 1, 1), (1, 2 ** 63 - 1),
                 (-2 ** 63, 2 ** 63 - 1), (2 ** 63 - 1, -2 ** 63), (-2 ** 63, 1), (1, -2 ** 63), (2 ** 53 + 1, 2 ** 53),
                 (2 ** 62 + 1, 2 ** 62), (1, 2 ** 53), (1, 2 ** 53 - 1), (3, 2 ** 53 + 2 ** 20)]
        cases += [(1, s) for s in (3, 5, 6, 7, 9, 10, 12, 100, 1000, 2 ** 20 + 1, 2 ** 40 - 87, 2 ** 53 - 111)]
        cases += [(rng.randrange(-2 ** 63, 2 ** 63), rng.randrange(1, 2 ** 63)) for _ in range(20000)]
        cases += [(rng.randrange(-2 ** 20, 2 ** 20), rng.randrange(1, 2 ** 53)) for _ in range(10000)]
        cases += near_ties(p, rng, 10000, 64)
        moved = 0
        for num, den in cases:
            for k in (1, 2):
                moved += bool(check(num, den, f, k)) and k == 2
        print(f'{name}: {2 * len(cases)} results with 64-bit terms, 20 000 of them near ties: all equal to '
              f'the specification; leading limb moved by the renormalization in {moved}; widest integer '
              f'formed: {WIDEST} bits')
    print('every statement held')


if __name__ == '__main__':
    sys.exit(main())
