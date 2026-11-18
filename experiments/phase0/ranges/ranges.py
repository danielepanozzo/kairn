#!/usr/bin/env python3
"""Exponent-range analysis per (T, k): the numbers behind the tables of the Phase 0 report.

Every bound has the form  |error| <= unit * |x| + tiny  with unit ~ 2^(-k*p) and tiny a small
multiple of the format's floor: eta = 2^qmin, the smallest subnormal, with gradual underflow, or
lambda, the smallest normal number, when subnormals are flushed to zero (Metal). The relative
term dominates, i.e. the k-number delivers its full k*p bits, when
    |x| >= 2^(k*p) * floor,
and below that the guaranteed precision at 2^E <= |x| < 2^(E+1) is
    min(k*p, E - log2(floor))  bits.
(k = 1 is the exception in both models: a normal result carries no absolute error, so plain T
keeps its p bits down to lambda.) The constant in front of the floor is ignored here. Prints Markdown tables."""
from fractions import Fraction
from math import log10

FORMATS = {"double": dict(p=53, qmin=-1074, lam=-1022, emax=1023), "float": dict(p=24, qmin=-149, lam=-126, emax=127)}
BAKED = {"double": [1, 2, 3, 4, 8], "float": [1, 2, 3, 4]}

def dec(e):
    """2^e as a decimal string with 2 significant digits."""
    x = e * log10(2)
    m, ex = 10 ** (x - int(x // 1)), int(x // 1)
    return f"{m:.1f}e{ex:+d}"

print("### Precision and full-precision range\n")
print("| T | k | bits (k·p) | decimal digits | full precision for \\|x\\| ≥ (gradual underflow) | (subnormals flushed) | bits at \\|x\\| = 1e-30 (gradual) | (flushed) |")
print("|---|---|---|---|---|---|---|---|")
for t, f in FORMATS.items():
    for k in BAKED[t]:
        bits = k * f["p"]
        g, z = (f["lam"] if k == 1 else f["qmin"] + bits), (f["lam"] if k == 1 else f["lam"] + bits)
        E = -100  # 2^-100 <= 1e-30 < 2^-99
        eg = max(0, min(bits, E - f["qmin"]))
        ez = (bits if k == 1 and E >= f["lam"] else max(0, min(bits, E - f["lam"])))
        print(f"| {t} | {k} | {bits} | {bits * log10(2):.1f} | 2^{g} ≈ {dec(g)} | 2^{z} ≈ {dec(z)} | {eg} | {ez} |")

print("\n### Other thresholds\n")
print("| T | u = 2^-p | smallest subnormal η | smallest normal λ | largest Ω | TwoProd error-free for ab = 0 or \\|ab\\| ≥ | limbs that fit above η at \\|x\\| = 1 |")
print("|---|---|---|---|---|---|---|")
for t, f in FORMATS.items():
    tp = f["qmin"] + 2 * f["p"] - 1
    print(f"| {t} | 2^-{f['p']} | 2^{f['qmin']} ≈ {dec(f['qmin'])} | 2^{f['lam']} ≈ {dec(f['lam'])} | (2 − 2^{1 - f['p']})·2^{f['emax']} ≈ {dec(f['emax'] + 1)} | 2^{tp} ≈ {dec(tp)} | {(1 - f['qmin']) / f['p']:.1f} |")

print("\n### Runtime k: largest useful k at a given magnitude (gradual underflow)\n")
print("| T | \\|x\\| ≈ 1e+300 / 1e+30 | \\|x\\| = 1 | \\|x\\| ≈ 1e-10 | \\|x\\| ≈ 1e-100 / 1e-20 |")
print("|---|---|---|---|---|")
for t, f in FORMATS.items():
    hi, lo = (996, -333) if t == "double" else (99, -67)
    cells = [(E - f["qmin"]) // f["p"] for E in (hi, 0, -34, lo)]
    print(f"| {t} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
