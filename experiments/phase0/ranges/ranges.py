#!/usr/bin/env python3
"""Exponent-range analysis per (T, k): the numbers behind the tables of the Phase 0 report.

Every bound has the form  |error| <= unit * |x| + tiny  with unit ~ 2^(-k*p).

Gradual underflow (model G): tiny ~ eta/2, where eta = 2^qmin is the smallest subnormal. The
relative term dominates, i.e. the k-number delivers its full k*p bits, when
    |x| >= 2^(k*p - 1) * eta,
which is also exactly where the last limb's unit in the last place reaches eta, and for k = 1 it
is the smallest normal number. Below it, a value with 2^E <= |x| < 2^(E+1) has
    min(k*p, E - qmin + 1)  bits.

Flush to zero (model Z, Metal): tiny ~ lambda, the smallest normal number, so the threshold is
    |x| >= 2^(k*p) * lambda        and below it    min(k*p, E - log2(lambda))  bits,
except for k = 1, where a normal result is never flushed and plain T keeps its p bits down to
lambda.

At magnitude 2^E at most floor((E - qmin) / p) + 1 limbs of a normalized number can be nonzero.
The small constants in front of eta and lambda are ignored. Prints Markdown tables."""
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
        g, z = f["qmin"] + bits - 1, (f["lam"] if k == 1 else f["lam"] + bits)
        E = -100  # 2^-100 <= 1e-30 < 2^-99
        eg = max(0, min(bits, E - f["qmin"] + 1))
        ez = (bits if k == 1 and E >= f["lam"] else max(0, min(bits, E - f["lam"])))
        print(f"| {t} | {k} | {bits} | {bits * log10(2):.1f} | 2^{g} ≈ {dec(g)} | 2^{z} ≈ {dec(z)} | {eg} | {ez} |")

print("\n### Other thresholds\n")
print("| T | u = 2^-p | smallest subnormal η | smallest normal λ | largest Ω | TwoProd error-free for ab = 0 or \\|ab\\| ≥ | nonzero limbs possible at \\|x\\| = 1 |")
print("|---|---|---|---|---|---|---|")
for t, f in FORMATS.items():
    tp = f["qmin"] + 2 * f["p"] - 1
    print(f"| {t} | 2^-{f['p']} | 2^{f['qmin']} ≈ {dec(f['qmin'])} | 2^{f['lam']} ≈ {dec(f['lam'])} | (2 − 2^{1 - f['p']})·2^{f['emax']} ≈ {dec(f['emax'] + 1)} | 2^{tp} ≈ {dec(tp)} | {(0 - f['qmin']) // f['p'] + 1} |")

print("\n### Largest number of nonzero limbs of a normalized number at a given magnitude (gradual underflow)\n")
print("| T | top of the range | \\|x\\| = 1 | \\|x\\| ≈ 1e-10 | \\|x\\| ≈ 1e-30 |")
print("|---|---|---|---|---|")
for t, f in FORMATS.items():
    cells = [(E - f["qmin"]) // f["p"] + 1 for E in (f["emax"], 0, -34, -100)]
    print(f"| {t} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
