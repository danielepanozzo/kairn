#!/usr/bin/env python3
"""Whether the non-finite results of a kernel in a toy format are overflows and nothing else.

    python3 tests/brute/widen.py KERNEL FORMAT [--more N]

Every operand of FORMAT goes through the generator's interpreter twice: in FORMAT, and in the
format of the same precision and the same smallest exponent with N more exponents above (default
|QMAX| + 12, enough for a product of two operands and its radius), where the constants of the
kernel are the same and nothing of these operands overflows. The
two computations agree until a result exceeds the largest number of FORMAT, so for a kernel whose
outputs do not decrease along its operations (the radius of a Ball kernel of the finite domain,
whose constants are positive) the result in FORMAT is

- equal to the wide one when every output of the wide one is at most the largest number of
  FORMAT, and
- non-finite when an output of the wide one is beyond it.

The script checks both, case by case, and exits with 1 on any case that is neither. It is the
exact test that takes the place of the oracle's test of a suspicious non-finite result where
that one does not apply (RADIUS_OVERFLOW in brute.py: the oracle's test supposes that a set
within a quarter of the largest number has a finite radius, which fails for `ball_mul_1` at
precision 1, whose radius has a factor of 8). Python 3 standard library only.
"""
import argparse
import os
import subprocess
import sys
from fractions import Fraction

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = sys.executable


def lines_of(text):
    return [line for line in text.splitlines() if line and not line.startswith("#")]


def interp(lines):
    r = subprocess.run([PY, os.path.join(REPO, "gen", "kairn-gen"), "interp"],
                       input="\n".join(lines) + "\n", capture_output=True, text=True, check=True,
                       cwd=REPO)
    return lines_of(r.stdout)


def outputs(line):
    return [t if t in ("inf", "-inf", "nan") else Fraction(float.fromhex(t))
            for t in line.split("->")[1].split()]


def compare(kernel, fmt, more):
    """(cases, finite and equal, non-finite, wide format, bad lines)."""
    p, qmin, qmax = (int(x) for x in fmt.split(":")[1:])
    wide = "fp:%d:%d:%d" % (p, qmin, qmax + more)
    omega = Fraction(2 ** p - 1) * Fraction(2) ** qmax
    r = subprocess.run([PY, os.path.join(REPO, "oracle", "kairn-oracle"), "gen", kernel, fmt,
                        "--exhaustive"], capture_output=True, text=True, check=True, cwd=REPO)
    lines = lines_of(r.stdout)
    narrow = interp(lines)
    widened = interp([line.replace(" %s " % fmt, " %s " % wide, 1) for line in lines])
    if not len(lines) == len(narrow) == len(widened):
        raise SystemExit("widen.py: the interpreter did not answer every line")
    equal = nonfinite = 0
    bad = []
    for a, b in zip(narrow, widened):
        za, zb = outputs(a), outputs(b)
        if any(isinstance(v, str) for v in zb):
            bad.append("the wide result is not finite (more exponents needed): %s" % b)
            continue
        beyond = any(abs(v) > omega for v in zb)
        if any(isinstance(v, str) for v in za):
            nonfinite += 1
            if not beyond:
                bad.append("non-finite although the wide result is within range: %s | %s" % (a, b))
        else:
            equal += 1
            if beyond or za != zb:
                bad.append("finite and not the wide result: %s | %s" % (a, b))
    return len(lines), equal, nonfinite, wide, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kernel")
    ap.add_argument("format", help="a toy format, fp:P:QMIN:QMAX")
    ap.add_argument("--more", type=int, help="exponents added above (default |QMAX| + 12)")
    a = ap.parse_args()
    more = a.more if a.more is not None else abs(int(a.format.split(":")[3])) + 12
    cases, equal, nonfinite, wide, bad = compare(a.kernel, a.format, more)
    for line in bad[:20]:
        print("BAD: " + line)
    print("%s %s against %s: %d cases, %d finite and equal to the wide result, %d non-finite "
          "with a wide result beyond the largest number, %d that are neither"
          % (a.kernel, a.format, wide, cases, equal, nonfinite - sum("non-finite" in b for b in bad),
             len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
