#!/usr/bin/env python3
"""Tests the selftest: copies the oracle into a temporary directory once per mutant, plants one
deliberate bug, and runs `selftest --quick` on the copy, which must fail.  A mutant whose text no
longer occurs in the source is reported as stale rather than skipped silently.

    python3 oracle/selftest/mutants.py              # one mutant at a time
    python3 oracle/selftest/mutants.py --jobs 4     # four at a time
"""

import argparse
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys
import tempfile

ORACLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# name: (file, text, replacement)
MUTANTS = {
    "rn ties away from zero": (
        "fmt.py", "if rem > half or (rem == half and m & 1):", "if rem >= half:"),
    "rn without gradual underflow": (
        "fmt.py", "    if q < fmt.qmin:\n        q = fmt.qmin\n    if q <= s:",
        "    if q < fmt.qmin - 3:\n        q = fmt.qmin - 3\n    if q <= s:"),
    "membership accepts p+1 bits": (
        "fmt.py", ".bit_length() <= fmt.p\n", ".bit_length() <= fmt.p + 1\n"),
    "requirements not checked": (
        "check.py", "        for r in pl.requires:\n", "        for r in []:\n"),
    "normalized entry always passes": (
        "check.py", "                if not F.normalized_limbs(fmt, zz):", "                if False:"),
    "bound lenient by a factor 2": (
        "check.py", "                if num > den:", "                if num > 2 * den:"),
    "when condition ignored": (
        "check.py", 'if e["when"] == "product_large" and not', "if False and not"),
    "outputs not checked for membership": (
        "check.py", "        for v in z:\n            if not F.is_member(fmt, v):",
        "        for v in []:\n            if not F.is_member(fmt, v):"),
    "leading_rounded not checked": (
        "check.py", '                if r != z[e["first"]]:', "                if False:"),
    "dropped lines not detected": (
        "check.py", "            if seen != want:", "            if False:"),
    "form A read as form R": (
        "check.py", '                if e["form"] == "R":', "                if True:"),
    "absolute term ignored": (
        "check.py", "                den = rn_ * rho * ad + an * rd", "                den = rn_ * rho * ad"),
    # Second wave.
    "predicate: le read as lt": (
        "check.py", 'a <= b if rel == "le"', 'a < b if rel == "le"'),
    "predicate: mask not compared": (
        "check.py", '        if z[e["first"]] != (1 if truth else 0):', "        if False:"),
    "predicate: outcomes swapped": (
        "check.py", 'es.count("true" if truth else "false")', 'es.count("false" if truth else "true")'),
    "mask output 2 read as 1": (
        "check.py", 'MASK_TEXT = {"0": 0, "1": 1}', 'MASK_TEXT = {"0": 0, "1": 1, "2": 1}'),
    "directed rounding ignores its direction": (
        "fmt.py", "(m << sh) != a and (n > 0) == up:", "(m << sh) != a and n < 0:"),
    "directed rounding without gradual underflow": (
        "fmt.py", "q = max(s + a.bit_length() - fmt.p, fmt.qmin)",
        "q = max(s + a.bit_length() - fmt.p, fmt.qmin - 3)"),
    "gap below a power of two taken above it": (
        "fmt.py", "1 << max((n - 1).bit_length() - fmt.p, 0)", "1 << max(n.bit_length() - fmt.p, 0)"),
    "rounded: beyond Omega judged": (
        "check.py", "beyond = beyond or abs(r) > fmt.omega", "beyond = beyond or abs(r) > 2 * fmt.omega"),
    "upper: beyond Omega judged": (
        "check.py", "        if pl.uppers and abs(F.rdir(fmt, V, pl.sv, True)) > fmt.omega:",
        "        if False:"),
    "upper: output below the value accepted": (
        "check.py", "        if exc < 0:", "        if False:"),
    "upper: gaps not checked": (
        "check.py", '        if exc * e["gd"] > e["gn"] * g:', "        if False:"),
    "upper: gap taken above the output": (
        "check.py", "        g = F.gap_below(fmt, o) << pl.sh_out", "        g = F.ulp(fmt, o) << pl.sh_out"),
    "upper: nonnegative statistic over all operands": (
        "check.py", "        if all(sum(x[lo:hi]) >= 0 for lo, hi in pl.groups):", "        if True:"),
    "encloses: input radii ignored": (
        "check.py", "            ends.append((ctr - r, ctr + r))", "            ends.append((ctr, ctr))"),
    "encloses: upper side only": (
        "check.py", "        rmin = max(cz - lo, hi - cz)", "        rmin = hi - cz"),
    "encloses: two corners only": (
        "check.py", 'for corner in c["corners"]]',
        'for corner in c["corners"][::max(1, len(c["corners"]) - 1)]]'),
    "encloses: center tail ignored": (
        "check.py", "        cz = sum(z[clo:chi]) << sh", "        cz = z[clo] << sh"),
    "encloses: slack measured from zero": (
        "check.py", '("slack in gaps of the radius", (rz - rmin, g), line)',
        '("slack in gaps of the radius", (rz, g), line)'),
    "nonneg not checked": (
        "check.py", "                if sum(x[lo:hi]) < 0:", "                if False:"),
    "power_of_two not checked": (
        "check.py", "                if v <= 0 or v & (v - 1):", "                if False:"),
    "limb_products_normal ignored": (
        "check.py", 'if e["when"] == "limb_products_normal" and not', "if False and not"),
    "expressions: abs ignored": (
        "expr.py", '        return "abs(%s)" % c, s', "        return c, s"),
    "expressions: unary minus ignored": (
        "expr.py", '        return "(-%s)" % c, s', "        return c, s"),
    "instances list read in reverse": (
        "claims.py", "                for fmtname, d in per.items():\n                    put(fmtname, j, d)",
        "                for fmtname, d in per.items():\n"
        "                    put(fmtname, len(inst) - 1 - j, d)"),
    # The non-finite layer.
    "F1: canonical output not checked": (
        "extended.py", '    if not canonical(fmt, w):\n        fail("F1"',
        '    if False:\n        fail("F1"'),
    "F2: core entries not applied": (
        "extended.py", '                    fail("F2", "core %s: %s" % (it["core_name"], r))',
        "                    pass"),
    "F2: finite result for a non-finite operand accepted": (
        "extended.py", '        fail("F2", "a finite result although an operand is not finite")',
        "        pass"),
    "F3 not checked": (
        "extended.py", '        if conds_hold:\n            fail("F3"', '        if False:\n            fail("F3"'),
    "F4: sign of the exact value ignored": (
        "extended.py", "want = INF if v > 0 else NINF", "want = INF"),
    "F4: tail after the infinity not checked": (
        "extended.py", "if w0 != want or any(t != 0 for t in w[1:]):", "if w0 != want:"),
    "F5: lead not applied": (
        "extended.py", '    if w != want:\n        fail("F5"', '    if False:\n        fail("F5"'),
    "F4: overflow on small operands not shown": (
        "extended.py", '        if ep.small(x, V):\n            sus.append("F4',
        '        if False:\n            sus.append("F4'),
    "extended reals: 0 * inf is not NaN": (
        "extended.py", "if sa is None or sb is None or sa == 0 or sb == 0:",
        "if sa is None or sb is None:"),
    "extended reals: inf - inf is not NaN": (
        "extended.py", "    if type(a) is not int and type(b) is not int and a != b:\n        return NAN",
        "    if False:\n        return NAN"),
    "canonical: any tail after an infinity": (
        "extended.py", "    return all(v == 0 for v in limbs[1:])\n", "    return True\n"),
    "canonical: a NaN with any tail": (
        "extended.py", "        return all(v == NAN for v in limbs)\n    return all(v == 0",
        "        return True\n    return all(v == 0"),
    "ball: whole line with any center": (
        "extended.py", "if r == INF and all(v == 0 for v in c):", "if r == INF:"),
    "ball: negative radius accepted": (
        "extended.py", 'return "finite" if r >= 0 and F.normalized_limbs(fmt, c) else None',
        'return "finite" if F.normalized_limbs(fmt, c) else None'),
    "B2 not checked": (
        "extended.py", '    if (so == "empty") != empty_in:', "    if False:"),
    "B3: finite ball from a non-finite operand accepted": (
        "extended.py", '        if not fin_ops:\n            es.applicable += 1\n            fail("B3"',
        '        if False:\n            es.applicable += 1\n            fail("B3"'),
    "requirements of the extended domain not checked": (
        "extended.py", "    why = ep.violated(x)\n", "    why = None\n"),
    "nonneg admits -inf": (
        "extended.py", "ok = v in (INF, NAN) or", "ok = v in (INF, NAN, NINF) or"),
    "makes_ball: negative radius not empty": (
        "extended.py", "if r == NAN or r == NINF or (type(r) is int and r < 0):",
        "if r == NAN or r == NINF:"),
    "represents: value not compared": (
        "extended.py", '    if not ok:\n        es.count("failed: not the value")',
        '    if False:\n        es.count("failed: not the value")'),
    "predicate: a NaN compares equal": (
        "extended.py", "truth = d is not None and (", 'truth = (d is None and rel != "lt") or d is not None and ('),
    "rounded: down below -Omega kept finite": (
        "extended.py", "r = NINF if r < -om else om if r > om else r",
        "r = -om if r < -om else om if r > om else r"),
    "upper: any output accepted for a NaN value": (
        "extended.py", '        return [] if o == NAN else ["upper: the output is not a NaN although the value is"]',
        "        return []"),
    "exhaustive: -inf left out of a one-limb domain": (
        "gen3.py", "dom = fin + [(INF,), (NINF,), (NAN,)]", "dom = fin + [(INF,), (NAN,)]"),
    "claims: core inputs not compared": (
        "claims.py", "        if shape(c.inputs, c.masks, True) != shape(k.inputs, k.masks, True):",
        "        if False:"),
    "claims: finite_when names not checked": (
        "claims.py", '            tree = kernel.input_expression(cond["abs_le"], w.split(": ", 1)[1])',
        '            tree = X.parse(cond["abs_le"])'),
    "bounds evaluated below min_precision": (
        "check.py", '            if e.kind == "error" and not self.in_scope:', "            if False:"),
    "represents: pinned outputs still shown as suspicious": (
        "extended.py", "    pinned = all(i in ep.pinned for lo, hi in c[\"ranges\"] for i in range(lo, hi))",
        "    pinned = False"),
    "claims: lead not compared with the value": (
        "claims.py", "        if (t[0] != LEADS[self.lead] or", "        if False and (t[0] != LEADS[self.lead] or"),
}


def run_one(work, name, fn, old, new):
    """(status, failing tests) of one mutant in its own copy of the oracle."""
    copy = os.path.join(work, "m%d" % sorted(MUTANTS).index(name), "oracle")
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(ORACLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
    path = os.path.join(copy, "kairn_oracle", fn)
    with open(path) as fh:
        src = fh.read()
    if src.count(old) != 1:
        return "STALE", "(the text to mutate is not in %s once)" % fn
    with open(path, "w") as fh:
        fh.write(src.replace(old, new))
    r = subprocess.run([sys.executable, os.path.join(copy, "kairn-oracle"), "selftest",
                        "--quick", "--workdir", os.path.join(os.path.dirname(copy), "wd")],
                       capture_output=True, text=True)
    failing = [ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    return ("caught" if r.returncode else "SURVIVED"), ", ".join(failing)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=1, help="mutants run at the same time")
    ap.add_argument("--only", help="comma-separated mutant names")
    a = ap.parse_args()
    names = [n for n in MUTANTS if not a.only or n in a.only.split(",")]
    work = tempfile.mkdtemp(prefix="kairn-oracle-mutants-")
    survivors, stale = [], []
    try:
        with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            futs = {ex.submit(run_one, work, n, *MUTANTS[n]): n for n in names}
            for fu in cf.as_completed(futs):
                name = futs[fu]
                status, note = fu.result()
                if status == "STALE":
                    stale.append(name)
                elif status == "SURVIVED":
                    survivors.append(name)
                print("%-8s %-46s %s" % (status, name, note))
                sys.stdout.flush()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("mutants: %d caught, %d survived, %d stale" % (
        len(names) - len(survivors) - len(stale), len(survivors), len(stale)))
    return 1 if survivors or stale else 0


if __name__ == "__main__":
    sys.exit(main())
