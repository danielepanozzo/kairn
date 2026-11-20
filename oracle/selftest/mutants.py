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
    # The kinds of Milestone 2.
    "neighbor: up and down swapped": (
        "directed.py", "    return F.succ(fmt, a) if up else F.pred(fmt, a)",
        "    return F.pred(fmt, a) if up else F.succ(fmt, a)"),
    "neighbor: next_up(-inf) is -inf": (
        "directed.py", "        return -fmt.omega if up else NINF", "        return NINF"),
    "neighbor: next_down(+inf) is +inf": (
        "directed.py", "        return INF if up else fmt.omega", "        return INF"),
    "neighbor: output not compared (extended domain)": (
        "extended.py", '    if z[c["first"]] != r:\n        return ["neighbor:',
        '    if False:\n        return ["neighbor:'),
    "neighbor: output not compared (finite domain)": (
        "check.py", '        if z[e["first"]] != r:\n            return "output is not the next number',
        '        if False:\n            return "output is not the next number'),
    "neighbor: the row of eta miscounted": (
        "directed.py", "    if a == 1:\n        return ROW_ETA", "    if a == 2:\n        return ROW_ETA"),
    "neighbor: a step from N counted as from a power of two above it": (
        "directed.py", "if toward_zero and m > fmt.lam and", "if toward_zero and m >= fmt.lam and"),
    # (The test of the side alone is redundant: an output on the wrong side is not reached by the
    # steps outward from the directed rounding, and fails there.)
    "bound: the steps taken toward the value (extended domain)": (
        "extended.py", "        t = D.neighbor(fmt, t, not below)", "        t = D.neighbor(fmt, t, below)"),
    "bound: the steps taken toward the value (finite domain)": (
        "check.py", "            t = D.step_unbounded(fmt, t, below)",
        "            t = D.step_unbounded(fmt, t, not below)"),
    "bound: one step more allowed (extended domain)": (
        "extended.py", '        if k == c["steps"]:', '        if k == c["steps"] + 1:'),
    "bound: one step more allowed (finite domain)": (
        "check.py", '            if k == e["steps"]:', '            if k == e["steps"] + 1:'),
    "bound: beyond Omega judged (finite domain)": (
        "check.py", "            beyond = abs(r) > fmt.omega or beyond",
        "            beyond = abs(r) > 2 * fmt.omega or beyond"),
    "bound: rounded up above Omega kept finite": (
        "directed.py", "    return INF if r > om else -om if r < -om else r",
        "    return om if r > om else -om if r < -om else r"),
    "bound: an infinite or NaN value not compared": (
        "extended.py", "        if o != v:\n            return [\"bound: the output is not",
        "        if False:\n            return [\"bound: the output is not"),
    "bound: steps of the finite domain taken above a power of two": (
        "directed.py", "        return t - F.gap_below(fmt, t)", "        return t - F.ulp(fmt, t)"),
    "rounded when: the condition ignored (extended domain)": (
        "extended.py", "            if not (v == 0 or abs(v) >= pl.pl_thr):\n                es.count(D.WHEN_FAILS)",
        "            if False:\n                es.count(D.WHEN_FAILS)"),
    "rounded when: the condition ignored (finite domain)": (
        "check.py", 'if pl.entries[i]["when"] == "product_large" and not', "if False and not"),
    "rounded when: the threshold P halved": (
        "check.py", "self.pl_thr = 1 << max(2 * fmt.p - 1 + q - self.sv, 0)",
        "self.pl_thr = 1 << max(2 * fmt.p - 2 + q - self.sv, 0)"),
    "rounded of two operands: the overflow classes swapped": (
        "directed.py", "    return OVER_ABOVE if v > 0 else OVER_BELOW",
        "    return OVER_BELOW if v > 0 else OVER_ABOVE"),
    "rounded of two operands: a NaN operand never counted": (
        "extended.py", "    if NAN in ops:\n        es.count(D.NAN_OPERAND)",
        "    if False:\n        es.count(D.NAN_OPERAND)"),
    "exact_when: encloses not judged": (
        "check.py", '        if "exact" not in e or self._exact_failing(e, es, x):', "        if True:"),
    "exact_when: error not judged": (
        "check.py", "        if (O << pl.sh_out) != (V << pl.sh_val):\n            return \"exact_when holds",
        "        if False:\n            return \"exact_when holds"),
    "exact_when: a strict condition read as >=": (
        "check.py", "                return a > b if strict else a >= b", "                return a >= b"),
    "exact_when: a zero does not satisfy a condition": (
        "check.py", "                if v == 0:\n                    return True",
        "                if v == 0:\n                    return False"),
    "exact_when: a limb reference reads the leading limb": (
        "check.py", '            return "x[%d]" % (self.in_slices[n][0] + i), self.fmt.qmin',
        '            return "x[%d]" % (self.in_slices[n][0]), self.fmt.qmin'),
    "exact_when: eta read as u in a threshold": (
        "claims.py", '            elif m.group(3) == "eta":\n                toks.append(("num", eta))',
        '            elif m.group(3) == "eta":\n                toks.append(("num", u))'),
    "exact_when: a threshold that is not positive accepted": (
        "claims.py", "            if eval_const(k, u, eta) <= 0:", "            if False:"),
    "claims: the value of neighbor not checked": (
        "claims.py", '            if t[0] != "name" or kernel.limbs_of(t[1]) != 1:',
        "            if False:"),
    "gen: the products around P aimed three binades higher": (
        "gen4.py", "    ep = _p_exponent(fmt)\n    P2", "    ep = _p_exponent(fmt) + 3\n    P2"),
    "gen: the scaled values at N aimed at 2N": (
        "gen4.py", "    x0 = lam >> k if k >= 0 else lam << -k",
        "    x0 = (lam >> k if k >= 0 else lam << -k) * 2"),
    "gen: the special values without Omega": (
        "gen4.py", "2 * lam, 2 * lam - 1, om, F.pred(fmt, om),", "2 * lam, 2 * lam - 1, F.pred(fmt, om),"),
    # rational_1 and rational_2 (kairn::rational).
    "rational: the naive pair": (
        "rational.py", "        z0 = F.rn_fixed(fmt, v)\n", "        z0 = a\n"),
    "rational: the error rounded to nearest": (
        "rational.py", "    err, _ = round_fraction(fmt, d, up=True)", "    err, _ = round_fraction(fmt, d)"),
    "rational: ties away from zero": (
        "rational.py", "    elif 2 * rem > den or (2 * rem == den and m & 1):", "    elif 2 * rem >= den:"),
    "rational: the binade of q one too high": (
        "rational.py", "    if (a << max(-e, 0)) < (d << max(e, 0)):\n        e -= 1",
        "    if False:\n        e -= 1"),
    "rational: overflow at twice Omega": (
        "rational.py", "    r = m << (last - fmt.qmin)\n    if r > fmt.omega:",
        "    r = m << (last - fmt.qmin)\n    if r > 2 * fmt.omega:"),
    "rational: exact never 1": (
        "rational.py", "return Answer(limbs, 0, 1, classes + [EXACT])",
        "return Answer(limbs, 0, 0, classes + [EXACT])"),
    "rational: den = 0 gives zero limbs": (
        "rational.py", "return Answer([F.NAN] * k, F.POS_INF, 0, [DEN0])",
        "return Answer([0] * k, F.POS_INF, 0, [DEN0])"),
    "rational: anything equals a NaN": (
        "rational.py", "    if want == F.NAN or found == F.NAN:\n        return want == found",
        "    if want == F.NAN or found == F.NAN:\n        return True"),
    "rational: the second limb not compared": (
        "rational.py", "zip(found[:k], ans.limbs)", "zip(found[:1], ans.limbs)"),
    "rational: the error not compared": (
        "rational.py", "    if not _same(found[k], e):", "    if False:"),
    "rational: exact not compared": (
        "rational.py", "    if flag != ans.exact:", "    if False:"),
    "rational: terms beyond 64 bits accepted": (
        "rational.py", "        if not INT64_MIN <= v <= INT64_MAX:", "        if False:"),
    "rational: the echo of requests not checked": (
        "rational.py", "        if self.broken:\n            return\n        i = self.start",
        "        if True:\n            return\n        i = self.start"),
    "rational: near-ties never aimed at a pair to renormalize": (
        "rational.py", "        aim = rng.bits(1) and self.window1", "        aim = rng.bits(1) and []"),
    # The folds' stage of Milestone 2: the folds, the bound kernels, form T, finite_or_nan.
    "fold_error: height n-1 read as n": (
        "folds.py", '    return n if h == "n" else max(n - 1, 0)', "    return n"),
    "fold_error: absolute term left out": (
        "folds.py", "    abs_lo, abs_hi = h.al * n * tn * tdd, h.ah * n * tn * tdd",
        "    abs_lo, abs_hi = 0, 0"),
    "fold_error: term left out": (
        "folds.py", "        self.gl = (td + tn) * xl - (td << P)\n        self.gh = (td + tn) * xh - (td << P)",
        "        self.gl = td * xl - (td << P)\n        self.gh = td * xh - (td << P)"),
    "fold_error: the bracket's upper end rounded down": (
        "folds.py", "        hi = -((-(hi * hi)) >> P)", "        hi = (hi * hi) >> P"),
    "fold: the value of an element without its second limbs": (
        "folds.py", '        return "(%s)" % "+".join("x[%d]" % i for i in range(lo, hi)), self.fmt.qmin',
        '        return "x[%d]" % lo, self.fmt.qmin'),
    "fold: a true flag with a non-finite element accepted": (
        "folds.py", "        if not case.finite:\n            return \"the flag is true although an element",
        "        if False:\n            return \"the flag is true although an element"),
    "fold: a false flag with a limb that is not a NaN accepted": (
        "folds.py", "    if not all(v == NAN for v in w):\n        return \"the flag is false",
        "    if False:\n        return \"the flag is false"),
    "fold: the flag not compared with limb 0": (
        "folds.py", "    if flag != (1 if lead else 0):", "    if False:"),
    "fold: normalized not judged": (
        "folds.py", "            if not F.normalized_limbs(fmt, w):\n                why = \"not normalized\"",
        "            if False:\n                why = \"not normalized\""),
    "fold: canonical elements not required": (
        "folds.py", "            if not XT.canonical(fmt, x[lo:hi]):", "            if False:"),
    "fold: a false flag far from overflow not suspicious": (
        "folds.py", "        if far:\n            es.count(\"flag false: finite elements far",
        "        if False:\n            es.count(\"flag false: finite elements far"),
    "fold: the lane order counted as the sequential one": (
        "folds.py", "    if order is None:\n        return [\"order: sequential\"]",
        "    if True:\n        return [\"order: sequential\"]"),
    "fold: more lanes than elements counted at W = n": (
        "folds.py", "    if W > n >= 1:", "    if W >= n >= 1:"),
    "fold: lengths counted one off": (
        "folds.py", '        return "length %d" % n', '        return "length %d" % (n + 1)'),
    "fold: heavy cancellation counted without u": (
        "folds.py", "    if S and (abs(sig) << pl.p) <= S:", "    if S and 2 * abs(sig) <= S:"),
    "fold claims: heights not checked against the orders": (
        "folds.py", "            if not isinstance(h, dict) or set(h) != set(fold.orders):",
        "            if not isinstance(h, dict):"),
    "fold claims: instances not compared with the expressions": (
        "folds.py", "                if li != ev:", "                if False:"),
    "fold claims: a fold without finite_or_nan read": (
        "folds.py", "        if len(flags) != 1:", "        if len(flags) > 1:"),
    "genfold: the tight stratum aimed elsewhere": (
        "genfold.py", "        return _tight_sum(gen, rng, n, k)",
        '        return _sum_values(gen, rng, "one", n, k)'),
    "genfold: lanes:big not above the length": (
        "genfold.py", '            o = "lanes:%d" % (n + 1 + rng.below(8))',
        '            o = "lanes:%d" % (n + rng.below(8))'),
    "bound kernels: the mask ignored": (
        "check.py", '            on = z[c["cond"]] == 1', "            on = True"),
    "bound kernels: upper not compared": (
        "check.py", "        if ov < v:", "        if False:"),
    "bound kernels: holds not judged": (
        "check.py", '                es.count("holds" if truth else "does not hold")',
        '                truth = True\n                es.count("holds")'),
    "bound kernels: an output not finite under a true mask not suspicious": (
        "check.py", '                sus.append("%s: an output is not finite although %s is true" % (',
        '                (lambda *a: None)("%s: an output is not finite although %s is true" % ('),
    "bound kernels: tiny(K) read as unit(K)": (
        "check.py", '"tiny": lambda k: pl.units[k][1]}', '"tiny": lambda k: pl.units[k][0]}'),
    "bound kernels: unit(K) read as tiny(K)": (
        "check.py", '"unit": lambda k: pl.units[k][0], ', '"unit": lambda k: pl.units[k][1], '),
    "count(m) not checked": (
        "check.py", "                if v != 0 and v < pl.one:", "                if False:"),
    "format(half) ignored": (
        "check.py", "        if self.format_missing:\n            self.in_scope = False",
        "        if False:\n            self.in_scope = False"),
    "form T read as form R": (
        "check.py", "                    for fn, sh in e[\"terms\"]:\n                        rho += abs(fn(x)) << sh",
        "                    rho = abs(Vc)"),
    "form T: the terms' magnitudes not taken": (
        "check.py", "                        rho += abs(fn(x)) << sh", "                        rho += fn(x) << sh"),
    "claims: count() of a two-limb input accepted": (
        "claims.py", "                if limbs[m.group(1)] != 1:\n                    raise ClaimsError(\"%s: requirement %r: count()",
        "                if False:\n                    raise ClaimsError(\"%s: requirement %r: count()"),
    "cexpr: unary minus binds tighter than ^": (
        "cexpr.py", '            return ("neg", unary_())', '            return ("neg", atom_())'),
    "cexpr: division read as a product": (
        "cexpr.py", "        return a / b", "        return a * b"),
    "finite_or_nan: the output not compared with the value": (
        "extended.py", "        if len(w) != len(s) or not all(same_limb(a, b) for a, b in zip(w, s)):",
        "        if False:"),
    "finite_or_nan: the flag not compared": (
        "extended.py", "    if f != (1 if lead else 0):", "    if False:"),
    "finite_or_nan: a non-NaN output of a non-finite value accepted": (
        "extended.py", "    elif not all(v == NAN for v in w):\n        out.append(\"finite_or_nan: limb 0",
        "    elif False:\n        out.append(\"finite_or_nan: limb 0"),
    # The interval kernels: the requirements, the exact range, I1 to I6, the other kinds, the
    # constants of a claim, the reading of an output group other than the first, the generator.
    "interval: reversed bounds read as an interval": (
        "intervals.py", "    if XT.x_cmp(L, 0, U, 0) > 0:\n        return None\n    return (\"nonempty\"",
        "    if False:\n        return None\n    return (\"nonempty\""),
    "interval: the empty set not read": (
        "intervals.py", "    if L == INF and U == NINF:\n        return (\"empty\", L, U)",
        "    if False:\n        return (\"empty\", L, U)"),
    "interval: requirement interval() not checked": (
        "intervals.py", "        return r[1] if interval_state(fmt, x[alo:ahi], x[blo:bhi]) is None else None",
        "        return None"),
    "interval: requirement not_nan() not checked": (
        "intervals.py", "    return r[1] if x[lo] == NAN else None", "    return None"),
    "range: a product of bounds without 0 * inf = 0": (
        "intervals.py", "    if a == 0 or b == 0:\n        return 0\n    if a == NAN", "    if False:\n        return 0\n    if a == NAN"),
    "range: the upper bound of a sum from the lower ones": (
        "intervals.py", "    hi = _xadd(_align(a[1], a[2], s), _align(b[1], b[2], s))",
        "    hi = _xadd(_align(a[0], a[2], s), _align(b[1], b[2], s))"),
    "range: a negation without exchanging the bounds": (
        "intervals.py", "        return XT.x_neg(hi), XT.x_neg(lo), s", "        return XT.x_neg(lo), XT.x_neg(hi), s"),
    "I2: an empty operand with a result that is not empty accepted": (
        "intervals.py", "        if zs[0] != \"empty\":\n            fail(\"I2\"", "        if False:\n            fail(\"I2\""),
    "I3: the lower bound not compared with the range": (
        "intervals.py", "    if _cmp(zl, q, lo, s) > 0:\n        fail(\"I3\"", "    if False:\n        fail(\"I3\""),
    "I4: tight exact not judged": (
        "intervals.py", "        if _cmp(zl, q, lo, s) != 0 or _cmp(zu, q, hi, s) != 0:",
        "        if False:"),
    "I4: one step more allowed beyond the rounding": (
        "intervals.py", "    limit = 0 if exact_needed else steps", "    limit = 0 if exact_needed else steps + 1"),
    "I4: product_large ignored": (
        "intervals.py", "            exact = _product_large(c, fmt, x, list(c[\"ivs\"].values()))",
        "            exact = False"),
    "I4: the relative term of outward doubled": (
        "intervals.py", "            ok, r = ratio_le(dist, abs(Vv), rel, ab, m)",
        "            ok, r = ratio_le(dist, abs(Vv), 2 * rel, ab, m)"),
    "I5: an unbounded result from a range within the limit accepted": (
        "intervals.py", "                if not bounded(zs):\n                    fail(\"I5\"",
        "                if False:\n                    fail(\"I5\""),
    "I5: bounded_exactly not judged": (
        "intervals.py", "                if c[\"bexact\"] and bounded(zs):", "                if False:"),
    "I5: the limit Omega read as twice Omega": (
        "intervals.py", "        lim_n, lim_s = fmt.omega, fmt.qmin", "        lim_n, lim_s = 2 * fmt.omega, fmt.qmin"),
    "I6: [0, 0] times anything not judged": (
        "intervals.py", "            if not (zl == 0 and zu == 0):\n                fail(\"I6\"",
        "            if False:\n                fail(\"I6\""),
    "outward: the side not judged": (
        "intervals.py", "    if (Oc > Vc) if below else (Oc < Vc):", "    if False:"),
    "outward: the relative term doubled": (
        "intervals.py", "    ok, r = ratio_le(abs(Oc - Vc), abs(Vc), rel, ab, scale)",
        "    ok, r = ratio_le(abs(Oc - Vc), abs(Vc), 2 * rel, ab, scale)"),
    "outward: the absolute term left out": (
        "intervals.py", "    den = rn * mag * ad + an * rd", "    den = rn * mag * ad"),
    "outward: exact_when not judged": (
        "intervals.py", "        if not failing(e[\"conds\"], x, es, OUT_EW_FAILS, OUT_EW_HOLDS) and Oc != Vc:",
        "        if False:"),
    "outward: the zero condition read as holding always": (
        "intervals.py", "            out.append((lambda x, fn=fn: fn(x) == 0, condition_text(text, op, k)))",
        "            out.append((lambda x, fn=fn: True, condition_text(text, op, k)))"),
    "outward: a zero factor need not give zero": (
        "intervals.py", "        if not all(v == 0 for v in w):\n            fail(\"zero_factor\"",
        "        if False:\n            fail(\"zero_factor\""),
    "outward: the infinity of an infinite operand not compared": (
        "intervals.py", "        if w != want:\n            fail(\"infinite operand\"",
        "        if False:\n            fail(\"infinite operand\""),
    "outward: an infinity on the wrong side accepted": (
        "intervals.py", "        if w0 != (NINF if below else INF) or any(t != 0 for t in w[1:]):",
        "        if any(t != 0 for t in w[1:]):"),
    "makes_interval: a NaN bound gives the empty set": (
        "intervals.py", "        want = (\"nonempty\", NINF, INF)\n    elif L != INF",
        "        want = (\"empty\", INF, NINF)\n    elif L != INF"),
    "set_bound: an empty ball not judged": (
        "intervals.py", "        if o != want:\n            es.count(\"failed: empty ball\")",
        "        if False:\n            es.count(\"failed: empty ball\")"),
    "set_bound: the side not judged": (
        "intervals.py", "    if (side > 0) if below else (side < 0):\n        es.count(\"failed: wrong side\")",
        "    if False:\n        es.count(\"failed: wrong side\")"),
    "interval_of_ball: tight not judged": (
        "intervals.py", "        why = _judge_rounded_side(fmt, es, name, zv, v, s, c[\"steps\"], False, down)\n        if why:\n            fail(\"tight\", why)",
        "        why = None\n        if why:\n            fail(\"tight\", why)"),
    "interval_set: the union read as the intersection": (
        "intervals.py", "    if c[\"op\"] == \"union\":", "    if c[\"op\"] == \"intersection\":"),
    "ball_of_interval: the smallest radius not judged": (
        "intervals.py", "        if r != want:\n            fail(\"smallest_radius\"",
        "        if False:\n            fail(\"smallest_radius\""),
    "ball_of_interval: the midpoint not judged": (
        "intervals.py", "    if not ok:\n        fail(\"midpoint\"", "    if False:\n        fail(\"midpoint\""),
    "ball_of_interval: the half-lines' centers exchanged": (
        "intervals.py", "else fmt.omega if U == INF else -fmt.omega", "else -fmt.omega if U == INF else fmt.omega"),
    "makes_ball from an interval: midpoint_when not judged": (
        "intervals.py", "            if 2 * cv != lo + hi:", "            if False:"),
    "makes_ball from an interval: containment not judged": (
        "intervals.py", "    if cv - r > lo or cv + r < hi:\n        es.count(\"failed: does not contain",
        "    if False:\n        es.count(\"failed: does not contain"),
    "zero_factor: a zero factor need not give zero": (
        "intervals.py", "    if z[c[\"first\"]] != 0:", "    if False:"),
    "groups: an entry judged only where the first group is finite": (
        "intervals.py", "        if type(z[lead]) is not int:\n            es.count(GROUP_NONFINITE)",
        "        if type(z[pl.lead]) is not int:\n            es.count(GROUP_NONFINITE)"),
    "constants: up( ) read as its argument": (
        "intervals.py", "            r = round_up_format(fmt, ev(t[1]))", "            r = ev(t[1])"),
    "claims: an interval of bounds of other limbs accepted": (
        "intervals.py", "        if limbs[lo] != limbs[hi] or limbs[lo] not in (1, 2):",
        "        if limbs[lo] not in (1, 2):"),
    "claims: bounded_when over another set accepted": (
        "intervals.py", "        if ct != e.set_tree:", "        if False:"),
    "claims: balls {} accepted in the extended domain": (
        "claims.py", "        if not isinstance(balls, dict) or (not balls and kernel.extended):",
        "        if not isinstance(balls, dict):"),
    "gen6: the threshold stratum aimed elsewhere": (
        "gen6.py", "        r = _threshold_pair(fmt, rng, sh) if n == 2 else None", "        r = None"),
    "gen6: halving never inexact in oddeta": (
        "gen6.py", "    v = 2 * rng.below(fmt.lam) + 1", "    v = 2 * rng.below(fmt.lam) + 2"),
    "gen6: no empty interval among the special ones": (
        "gen6.py", "    if kind == \"empty\":\n        return _inf(k, 1), _inf(k, -1)",
        "    if kind == \"empty\":\n        return _inf(k, -1), _inf(k, 1)"),
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
