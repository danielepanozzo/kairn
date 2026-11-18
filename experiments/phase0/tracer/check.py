#!/usr/bin/env python3
"""Exact check of test.cpp's output against the theorems of Proofs.v (binary64: prec = 53,
emin = -1074). Shares no code with the generator or the kernels."""
import sys
from fractions import Fraction as Q
n = {"two_sum": [0, 0], "fast_two_sum": [0, 0], "two_prod": [0, 0, 0]}
threshold = Q(2) ** (-1074 + 2 * 53 - 1)
for line in sys.stdin:
    name, *h = line.split()
    a, b, hi, lo = (float.fromhex(t) for t in h)
    exact = Q(a) * Q(b) if name == "two_prod" else Q(a) + Q(b)
    rn = a * b if name == "two_prod" else a + b          # Python floats round to nearest even
    ok = hi == rn and Q(hi) + Q(lo) == exact
    if name == "two_prod" and exact != 0 and abs(exact) < threshold:
        n[name][2] += 1                                   # outside the theorem's hypothesis
        ok = hi == rn and abs(Q(hi) + Q(lo) - exact) < Q(2) ** -1074
    n[name][0] += 1
    n[name][1] += not ok
for name, c in n.items():
    extra = f"  ({c[2]} below the exactness threshold: checked |p + e - ab| < 2^-1074 instead)" if len(c) > 2 else ""
    print(f"  {name:13s} cases={c[0]}  violations={c[1]}{extra}")
sys.exit(any(c[1] for c in n.values()))
