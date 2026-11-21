#!/usr/bin/env python3
"""The emulated arithmetic (tests/emulated/number.hpp) against the oracle's exact rounding, and
against the machine's float and double, each with the faults planted on purpose that it must catch
(docs/developer/testing.md, "The emulated formats").

    python3 tests/emulated/test_emulated.py --selftest EXE [--full] [--only oracle|hardware]

EXE is the program tests/emulated/selftest.cpp. Two parts:

- oracle: every operation of the emulated type in toy formats, against the reference arithmetic of
  the oracle (oracle/kairn_oracle/refrun.py, Arith, and fmt.py: the rounding, succ and pred of
  oracle/README.md), which is written apart from both the emulated type and the generator's
  interpreter. Every pair of operands (and every triple for the fused operations) of formats of
  one to five bits, finite, infinite and NaN; random operands of the formats of the exhaustive
  tier, fp:8:-14:1 to fp:11:-20:1, drawn from every binade, the subnormal ones and the top, with
  the special values. Values are compared, and the class of a value that is not finite; the sign
  of a zero is not (the oracle's fixed values have none), and is compared in the other part.
- hardware: selftest --hardware binary32 and binary64, every operation in the format of float and
  of double against the machine's own, bit for bit, the sign of a zero included.

Each part is then run again with each fault of number.hpp (plant_fault: a tie rounded away from
zero, a result in the subnormal range truncated), and must fail with each: a fault the comparisons
do not see fails this test.

Python's standard library and the oracle's modules only; nothing of the generator.
"""
import argparse
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(REPO, "oracle"))
from kairn_oracle import fmt as F  # noqa: E402
from kairn_oracle import refrun  # noqa: E402

INF = float("inf")
FAULTS = ("tie-away", "subnormal-trunc")

# Formats of every pair (and triple) of operands: precision 1 to 5, the subnormal range and
# overflow within reach of every operation.
EXHAUSTIVE = ["fp:1:-3:3", "fp:2:-3:2", "fp:3:-4:2", "fp:4:-6:3", "fp:5:-7:0"]
EXHAUSTIVE_TRIPLES = ["fp:1:-3:3", "fp:2:-2:1", "fp:3:-4:2"]
# The formats of the exhaustive tier (formats of the statements, qmax = 1, qmin = 3 - qmax - 2p),
# and one of a wider range, on random operands.
SAMPLED = ["fp:8:-14:1", "fp:9:-16:1", "fp:10:-18:1", "fp:11:-20:1", "fp:8:-22:9"]


def value_of(f, tok):
    """('num', N) for a finite limb (N the fixed value), ('inf', sign) or ('nan',)."""
    v = F.parse_limb(f, tok)
    if v == F.POS_INF:
        return ("inf", 1)
    if v == F.NEG_INF:
        return ("inf", -1)
    if v == F.NAN:
        return ("nan",)
    if v == F.OUTSIDE:
        return ("outside", tok)
    return ("num", v)


def expected(v):
    """The same from the oracle: an int, a float infinity or NaN (Arith), or the infinities of
    fmt.py (POS_INF, NEG_INF)."""
    if type(v) is int:
        return ("num", v)
    if v == F.POS_INF:
        return ("inf", 1)
    if v == F.NEG_INF:
        return ("inf", -1)
    if v != v:
        return ("nan",)
    return ("inf", 1 if v > 0 else -1)


def operand(f, v):
    """A literal of a fixed value or a float infinity or NaN."""
    if type(v) is int:
        return F.to_hex(v, f.qmin)
    return "nan" if v != v else ("inf" if v > 0 else "-inf")


def special_values(f):
    """Every value of a toy format, the non-finite ones included."""
    return F.all_values(f) + [INF, -INF, float("nan")]


def sample_values(f, rng, n):
    """Random values from every binade, the subnormal range and the top, and the special ones."""
    out = []
    top = f.omega
    lam = 1 << (f.p - 1)
    for _ in range(n):
        k = rng.randrange(8)
        if k == 0:
            v = rng.randrange(1, lam) if f.p > 1 else 1                  # subnormal
        elif k == 1:
            v = rng.randrange(lam, 1 << f.p) << (f.qmax - f.qmin)        # the top binade
        elif k == 2:
            v = rng.choice([0, 1, lam, max(lam - 1, 1), top, 1 << max(-f.qmin, 0)])
        else:
            e = rng.randrange(f.qmax - f.qmin + 1)
            m = rng.randrange(lam, 1 << f.p)
            if rng.randrange(3) == 0:
                m = lam | (m & 3) | ((m & 3) << max(f.p - 3, 0))         # a short significand
            v = m << e
        v = v if rng.randrange(2) else -v
        if not F.is_member(f, v):
            v = F.rn_fixed(f, v)
            v = v if type(v) is int else 0
        out.append(v)
        if rng.randrange(40) == 0:
            out[-1] = rng.choice([INF, -INF, float("nan")])
    return out


def reference(f, ar, op, xs):
    """The oracle's answer for one operation: a value (as expected()) or a mask or an integer."""
    a = xs[0] if xs else None
    b = xs[1] if len(xs) > 1 else None
    c = xs[2] if len(xs) > 2 else None
    nan = float("nan")
    fin = [type(x) is int for x in xs]
    if op in ("add", "sub", "prod", "fma", "fms", "fnma"):
        return expected(getattr(ar, op)(*xs))
    if op == "mul":
        if all(fin):
            return expected(F.rn(f, a * b, 2 * f.qmin))
        return expected(ar.prod(a, b))
    if op in ("neg", "abs"):
        if a != a:
            return ("nan",)
        return expected(-a if op == "neg" else abs(a))
    if op == "times_inf":
        return expected(ar.times_inf(a))
    if op == "times_inf_ce":
        return expected(nan if a != a or a == 0 else (INF if a > 0 else -INF))
    if op in ("next_up", "next_down"):
        up = op == "next_up"
        if type(a) is not int:
            if a != a:
                return ("nan",)
            if (a > 0) == up:
                return ("inf", 1 if a > 0 else -1)
            return ("num", f.omega if a > 0 else -f.omega)
        return expected(F.succ(f, a) if up else F.pred(f, a))
    if op in ("lt", "le", "gt", "ge", "eq", "ne"):
        if a != a or b != b:
            return "1" if op == "ne" else "0"
        r = {"lt": a < b, "le": a <= b, "gt": a > b, "ge": a >= b, "eq": a == b, "ne": a != b}[op]
        return "1" if r else "0"
    if op == "to_size":
        if type(a) is not int or a <= 0:
            return "0"
        n = (a << f.qmin) if f.qmin >= 0 else a >> -f.qmin
        return str(n) if n < (1 << 64) else "0"
    raise ValueError(op)


def run_ops(exe, f, lines, fault):
    cmd = [exe, "--ops", f.name if f.name.startswith("fp:") else "fp:%d:%d:%d" % f.triple]
    if fault:
        cmd += ["--fault", fault]
    p = subprocess.run(cmd, input="\n".join(lines) + "\n", capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("%s failed (%d): %s" % (" ".join(cmd), p.returncode, p.stderr.strip()))
    return p.stdout.split("\n")[:len(lines)]


UNARY = ["neg", "abs", "next_up", "next_down", "times_inf", "times_inf_ce", "to_size"]
BINARY = ["add", "sub", "mul", "prod", "lt", "le", "gt", "ge", "eq", "ne"]
TERNARY = ["fma", "fms", "fnma"]


def cases(f, values, rng, sampled, triples):
    """(op, operands) to compare: every unary operation on every value; the binary ones on every
    pair, or on random pairs; the fused ones on every triple, or on random triples."""
    out = [(op, [a]) for op in UNARY for a in values]
    if sampled:
        for _ in range(sampled):
            a, b = rng.choice(values), rng.choice(values)
            out += [(op, [a, b]) for op in BINARY]
            out += [(op, [a, b, rng.choice(values)]) for op in TERNARY]
            if type(a) is int and type(b) is int and rng.randrange(2):
                # an addend that cancels the product, or sits at a tie of it
                p = F.rn(f, a * b, 2 * f.qmin)
                if type(p) is int:
                    out += [(op, [a, b, -p]) for op in TERNARY]
        return out
    out += [(op, [a, b]) for op in BINARY for a in values for b in values]
    if triples:
        out += [(op, [a, b, c]) for op in TERNARY for a in values for b in values for c in values]
    return out


def compare_format(exe, name, rng, sampled, triples, fault):
    """The number of differences between the emulated type and the oracle in one format, and the
    first few, and the number of cases."""
    f = F.parse_format(name)
    ar = refrun.Arith(f.triple)
    values = special_values(f) if not sampled else sample_values(f, rng, 4000) + [0, INF, -INF, float("nan")]
    todo = cases(f, values, rng, sampled, triples)
    # The counts and the powers of two, as numbers of the format.
    extra = [("from_size", str(n)) for n in list(range(0, 300)) + [rng.randrange(1 << 64) for _ in range(500)]]
    extra += [("pow2", str(k)) for k in range(f.qmin - f.p - 3, f.qmax + f.p + 3)]
    lines = ["%s %s" % (op, " ".join(operand(f, x) for x in xs)) for op, xs in todo]
    lines += ["%s %s" % (op, arg) for op, arg in extra]
    got = run_ops(exe, f, lines, fault)
    diffs = []
    for (op, xs), line, g in zip(todo, lines, got):
        want = reference(f, ar, op, xs)
        have = g if isinstance(want, str) else value_of(f, g)
        if have != want:
            diffs.append("%s %s: emulated %s, oracle %s" % (name, line, g, want))
    for (op, arg), line, g in zip(extra, lines[len(todo):], got[len(todo):]):
        want = expected(F.rn(f, int(arg), 0) if op == "from_size" else F.rn(f, 1, int(arg)))
        if value_of(f, g) != want:
            diffs.append("%s %s: emulated %s, oracle %s" % (name, line, g, want))
    return len(diffs), diffs[:5], len(lines)


def oracle_part(exe, size, fault):
    """size: full (every format above, 4 000 random pairs and triples in each sampled one), quick
    (the formats of one to three bits, every triple of the first two, 1 000 random cases in each
    sampled format) or fault (fp:3:-4:2 and fp:8:-14:1 only)."""
    rng = random.Random(20261121)
    total, n = 0, 0
    shown = []
    exhaustive = {"full": EXHAUSTIVE, "quick": EXHAUSTIVE[:3], "fault": ["fp:3:-4:2"]}[size]
    triples = {"full": EXHAUSTIVE_TRIPLES, "quick": EXHAUSTIVE_TRIPLES[:2], "fault": []}[size]
    sampled = {"full": SAMPLED, "quick": SAMPLED, "fault": SAMPLED[:1]}[size]
    for name in exhaustive:
        d, first, k = compare_format(exe, name, rng, 0, name in triples, fault)
        total, n, shown = total + d, n + k, shown + first
    for name in sampled:
        d, first, k = compare_format(exe, name, rng, 4000 if size == "full" else 1000, False, fault)
        total, n, shown = total + d, n + k, shown + first
    return total, n, shown, len(exhaustive) + len(sampled)


def hardware_part(exe, full, fault):
    total, report = 0, []
    for fmt in ("binary32", "binary64"):
        cmd = [exe, "--hardware", fmt, "--count", str(2000000 if full else 100000), "--seed", "1"]
        if fault:
            cmd += ["--fault", fault]
        p = subprocess.run(cmd, capture_output=True, text=True)
        last = p.stdout.strip().split("\n")[-1] if p.stdout.strip() else "(no output)"
        if p.returncode not in (0, 1):
            raise RuntimeError("%s failed (%d): %s" % (" ".join(cmd), p.returncode, p.stderr.strip()))
        report.append(last)
        if p.returncode == 1:
            total += 1
            if not fault:
                print(p.stdout)
    return total, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", required=True, help="the program tests/emulated/selftest.cpp")
    ap.add_argument("--full", action="store_true", help="the full tier's sizes")
    ap.add_argument("--only", choices=("oracle", "hardware"))
    a = ap.parse_args(argv)
    failed = False
    if a.only in (None, "oracle"):
        d, n, shown, formats = oracle_part(a.selftest, "full" if a.full else "quick", "")
        print("against the oracle: %d cases in %d formats, %d different" % (n, formats, d))
        for s in shown:
            print("  DIFFERENT " + s)
        failed |= d > 0
        for fault in FAULTS:
            d, n, shown, _ = oracle_part(a.selftest, "fault", fault)
            print("against the oracle, with the fault %s planted: %d of %d cases different%s"
                  % (fault, d, n, "" if d else ": NOT CAUGHT"))
            failed |= d == 0
    if a.only in (None, "hardware"):
        d, report = hardware_part(a.selftest, a.full, "")
        for line in report:
            print("against the machine: " + line)
        failed |= d > 0
        for fault in FAULTS:
            d, report = hardware_part(a.selftest, False, fault)
            print("against the machine, with the fault %s planted: %s%s"
                  % (fault, "; ".join(report), "" if d == 2 else ": NOT CAUGHT in every format"))
            failed |= d != 2
    print("test_emulated: %s" % ("FAILED" if failed else "passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
