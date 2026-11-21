"""What the functions on arrays, their bounds and the accumulator claim, checked in exact rational
arithmetic on what tests/api/arrays_exact.cpp computes through the public headers.

    python3 tests/api/arrays_exact.py PROGRAM bounds | accumulator

bounds: for each line "sum|dot K T n unit tiny" (kairn::traits<X>::sum(n) and dot(n)), with u the
unit roundoff of T and eta its smallest positive subnormal number:
- sum, when unit is finite: tiny = 0 and unit >= gamma_(n-1)(e) = (n-1) e / (1 - (n-1) e), with
  e = u / (1 + u) for one limb and 3u^2 / (1 - 4u) for two (the bounds of add_1_1 and add_2_2),
  and (n - 1) e < 1; the bound of a sum of n numbers in any order (milestone2.md, "Summation over
  any tree"). The kernel is given n - 1 as a count of T, rounded up where it is not one, so these
  lines check the header's conversion too;
- dot, when unit is finite: unit >= gamma_n(e) with e = u / (1 + u) (one limb) or 4u^2 (two), and
  tiny >= n tau (1 + unit), tau = eta / 2 or 3/2 eta: the two terms that dominate the proved
  statement of dot_k for n terms;
- when unit is +infinity (no bound given), tiny is +infinity too, and the length is beyond what the
  kernel was found to bound in binary64 and binary32: (n - 1) e, or n e, above 1/5. A bound that is
  not given is never a finite number.
The checker fails on a line that breaks one of these, and on a stream without a line given and a
line not given for each kind, number of limbs and format (that is, one that did not test the edge).

accumulator: for each history of kairn::Accumulator, with Sigma the exact sum of its terms (each
with its multiplicity), what the header adds to its kernels and what the theorem gives:
- the count is the number of terms (or 2^64 - 1 for the one that saturates);
- when error_bound() r is finite: the running sum s is finite, every term finite, sum() finite,
  |s - Sigma| <= r exactly, and ball() is the ball of center s and radius r;
- when s is not finite, or the count saturated, or a term is not finite: r is +inf and ball() the
  whole line (center 0, radius +inf); a finite radius is never given that the theorem does not give;
- when the sum of magnitudes is +inf: r is +inf;
- and the header is not too pessimistic: r is finite when every term and s are finite, the
  magnitudes are below the largest finite number over 16, and the count is well within the lengths
  bounded (count u <= 1/16, u of T: the radius kernel acc_radius_k sums the magnitudes in T, for
  one and for two limbs, and bounds counts up to m u <= 1/2).
It fails also on a stream without a finite radius and an infinite one of each kind of history that
should have one (random, counts beyond 2^p, the empty one; saturated, overflows, not finite).
"""
import subprocess
import sys
from fractions import Fraction

PRECISION = {"binary64": 53, "binary32": 24}
EMIN = {"binary64": -1074, "binary32": -149}


def value(text):
    if text == "inf":
        return None
    if text == "nan":
        raise ValueError("a NaN")
    return Fraction(float.fromhex(text))


def gamma(m, e):
    return m * e / (1 - m * e)


def check_bounds(lines):
    failures = []
    seen = set()
    for line in lines:
        kind, k, fmt, n, unit, tiny = line.split()
        k, n = int(k), int(n)
        u = Fraction(1, 2 ** PRECISION[fmt])
        eta = Fraction(2) ** EMIN[fmt]
        g, t = value(unit), value(tiny)
        if kind == "sum":
            e = u / (1 + u) if k == 1 else 3 * u * u / (1 - 4 * u)
            m = max(n, 1) - 1
        else:
            e = u / (1 + u) if k == 1 else 4 * u * u
            m = n
        if g is None:
            seen.add((kind, k, fmt, False))
            if t is not None:
                failures.append("%s: unit is +inf but tiny is finite" % line)
            if m * e <= Fraction(1, 5):
                failures.append("%s: no bound given, though m e = %.3g <= 1/5" % (line, float(m * e)))
            continue
        seen.add((kind, k, fmt, True))
        if t is None:
            failures.append("%s: unit is finite but tiny is +inf" % line)
            continue
        if m * e >= 1:
            failures.append("%s: a finite bound where m e >= 1" % line)
            continue
        if g < gamma(m, e):
            failures.append("%s: unit below gamma_%d(e) by %.3g of it" % (line, m, float(1 - g / gamma(m, e))))
        if kind == "sum" and t != 0:
            failures.append("%s: a sum has no underflow term, but tiny is not 0" % line)
        if kind == "dot":
            tau = eta / 2 if k == 1 else 3 * eta / 2
            if t < n * tau * (1 + g):
                failures.append("%s: tiny below n tau (1 + unit)" % line)
    for kind in ("sum", "dot"):
        for k in (1, 2):
            for fmt in ("binary64", "binary32"):
                for given in (True, False):
                    if k == 2 and fmt == "binary64" and not given:
                        continue  # no std::size_t is beyond 2^101 terms
                    if (kind, k, fmt, given) not in seen:
                        failures.append("no line of %s, %d limbs, %s, with the bound %s" % (
                            kind, k, fmt, "given" if given else "not given"))
    return failures


def number(fields, k):
    """The exact value of k limbs, or None if one is not finite."""
    vals = [value(f) if f != "nan" else None for f in fields[:k]]
    if any(v is None for v in vals):
        return None
    return sum(vals)


def check_accumulator(lines):
    failures = []
    seen = set()
    i = 0
    while i < len(lines):
        head = lines[i].split()
        if head[0] != "acc":
            return failures + ["line %d: expected a history, got %r" % (i + 1, lines[i])]
        k, fmt, what, nterms = int(head[1]), head[2], head[3], int(head[4])
        where = "%s (%d limbs, %s)" % (what, k, fmt)
        terms = [line.split() for line in lines[i + 1:i + 1 + nterms]]
        result = lines[i + 1 + nterms].split()
        i += 2 + nterms
        u = Fraction(1, 2 ** PRECISION[fmt])
        total = Fraction(0)
        finite_terms = True
        times_total = 0
        for t in terms:
            times = int(t[1])
            times_total += times
            x = number(t[2:], k)
            y = number(t[2 + k:], k) if t[0] == "*" else Fraction(1)
            if x is None or y is None:
                finite_terms = False
                continue
            total += times * x * y
        count = int(result[1])
        s = number(result[2:], k)
        a = value(result[2 + k]) if result[2 + k] != "nan" else None
        r = value(result[3 + k]) if result[3 + k] != "nan" else "nan"
        flag = result[4 + k] == "1"
        center = number(result[5 + k:], k)
        radius = value(result[5 + 2 * k]) if result[5 + 2 * k] != "nan" else "nan"
        if r == "nan" or radius == "nan":
            failures.append("%s: a NaN radius" % where)
            continue
        if what == "saturated":
            if count != 2 ** 64 - 1:
                failures.append("%s: count %d, not saturated" % (where, count))
        elif count != times_total:
            failures.append("%s: count %d, but %d terms" % (where, count, times_total))
        if r is not None:
            seen.add((what, True))
            if s is None or not finite_terms or not flag:
                failures.append("%s: a finite radius with a running sum or a term that is not finite" % where)
            elif what == "saturated":
                failures.append("%s: a finite radius with a count that saturated" % where)
            elif abs(s - total) > r:
                failures.append("%s: |s - Sigma| = %.3g exceeds the radius %.3g" % (where, float(abs(s - total)), float(r)))
            if center != s or radius != r:
                failures.append("%s: ball() is not the ball of center s and radius error_bound()" % where)
        else:
            seen.add((what, False))
            if radius is not None or center != 0:
                failures.append("%s: error_bound() is +inf, but ball() is not the whole line" % where)
            # The radius kernel bounds counts up to m u <= 1/2 (u of T, for both numbers of limbs:
            # the magnitudes are summed in T), bound_dot_k up to m e about 1/4.
            e = u
            big = Fraction(float.fromhex("0x1.fffffep+127" if fmt == "binary32" else "0x1.fffffffffffffp+1023"))
            if (s is not None and finite_terms and flag and a is not None and a < big / 16
                    and count * e <= Fraction(1, 16) and what != "saturated"):
                failures.append("%s: no bound given, though count e = %.3g and every value finite" % (
                    where, float(count * e)))
        if (s is None or not finite_terms) and flag:
            failures.append("%s: sum() finite with a running sum or a term that is not finite" % where)
    for what, given in (("random", True), ("count_2k", True), ("empty", True), ("saturated", False),
                        ("overflow", False), ("magnitudes_overflow", False), ("not_finite", False)):
        if (what, given) not in seen:
            failures.append("no history %s with the radius %s" % (what, "finite" if given else "+inf"))
    return failures


def main(argv):
    if len(argv) != 3 or argv[2] not in ("bounds", "accumulator"):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    p = subprocess.run([argv[1], argv[2]], stdout=subprocess.PIPE, check=False)
    if p.returncode != 0:
        print("arrays_exact: %s %s failed (%s)" % (argv[1], argv[2], p.returncode))
        return 1
    lines = [line for line in p.stdout.decode().splitlines() if line.strip()]
    failures = check_bounds(lines) if argv[2] == "bounds" else check_accumulator(lines)
    for f in failures[:40]:
        print("FAILED " + f)
    print("arrays_exact %s: %d lines, %d failures" % (argv[2], len(lines), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
