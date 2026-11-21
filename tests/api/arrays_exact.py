"""What the functions on arrays, their bounds and the accumulator claim, checked in exact rational
arithmetic on what tests/api/arrays_exact.cpp computes through the public headers.

    python3 tests/api/arrays_exact.py PROGRAM bounds

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


def main(argv):
    if len(argv) != 3 or argv[2] not in ("bounds",):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    p = subprocess.run([argv[1], argv[2]], stdout=subprocess.PIPE, check=False)
    if p.returncode != 0:
        print("arrays_exact: %s %s failed (%s)" % (argv[1], argv[2], p.returncode))
        return 1
    lines = [line for line in p.stdout.decode().splitlines() if line.strip()]
    failures = check_bounds(lines)
    for f in failures[:40]:
        print("FAILED " + f)
    print("arrays_exact %s: %d lines, %d failures" % (argv[2], len(lines), len(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
