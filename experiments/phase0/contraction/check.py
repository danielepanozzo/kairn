#!/usr/bin/env python3
"""Exact check of contraction.cpp's output (stdin): see that file. Shares no code with it."""
import sys
from fractions import Fraction
from math import frexp, ldexp

def ulp(x):
    if x == 0.0:
        return Fraction(float.fromhex("0x1p-1074"))
    _, e = frexp(abs(x))
    return Fraction(ldexp(1.0, max(e - 53, -1074)))

stats, ref = {}, {}
for line in sys.stdin:
    name, *h = line.split()
    xh, xl, yh, yl, zh, zl = (float.fromhex(t) for t in h)
    key = (xh, xl, yh, yl)
    if name == "reference":
        ref[key] = (zh, zl)
    exact = (Fraction(xh) + Fraction(xl)) * (Fraction(yh) + Fraction(yl))
    err = abs(Fraction(zh) + Fraction(zl) - exact) / abs(exact)
    s = stats.setdefault(name, {"n": 0, "diff": 0, "maxerr": Fraction(0), "overlap": 0})
    s["n"] += 1
    s["diff"] += (zh, zl) != ref[key]
    s["maxerr"] = max(s["maxerr"], err)
    s["overlap"] += abs(Fraction(zl)) > ulp(zh) / 2
u2 = Fraction(1, 2**106)
for name, s in stats.items():
    print(f"  {name:13s} cases={s['n']:6d}  differ_from_reference={s['diff']:6d}  "
          f"max_rel_err={float(s['maxerr'] / u2):8.3f} u^2  not_normalized={s['overlap']:6d}")
