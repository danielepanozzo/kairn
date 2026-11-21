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
        "extended.py", "if r == NINF or (type(r) is int and r < 0):",
        "if r == NINF:"),
    # The rule of 2026-11-20: a NaN radius gives the whole line, a negative one the empty set
    # whatever the center.
    "makes_ball: a NaN radius read as the empty set (the old rule)": (
        "extended.py", "if r == NINF or (type(r) is int and r < 0):",
        "if r == NAN or r == NINF or (type(r) is int and r < 0):"),
    "makes_ball: the center tested before the radius": (
        "extended.py", "if r == NINF or (type(r) is int and r < 0):",
        "if finite_center and (r == NINF or (type(r) is int and r < 0)):"),
    "makes_ball: the class of the radius not counted": (
        "extended.py", "es.count(\"given radius %s, center %s\" % (radius_class(r, token),",
        "es.count(\"given radius %s, center %s\" % (\"positive\","),
    "makes_ball: the sign of a zero radius not read": (
        "extended.py", "return \"-0\" if token.startswith(\"-\") else \"+0\"", "return \"+0\""),
    "badradius: a center never left finite": (
        "gen3.py", "        if rng.bits(1):\n            vals[c] = _nonfinite(",
        "        if False:\n            vals[c] = _nonfinite("),
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
    # The constructors under the rule of 2026-11-20: a NaN bound or the same infinity twice gives
    # the whole line, reversed bounds the empty set.
    "makes_interval: a NaN bound gives the empty set": (
        "intervals.py", "    if given in (MAKE_NAN, MAKE_EQUAL_INF):\n        want = (\"nonempty\", NINF, INF)\n    elif given == MAKE_REVERSED:",
        "    if given == MAKE_EQUAL_INF:\n        want = (\"nonempty\", NINF, INF)\n    elif given in (MAKE_REVERSED, MAKE_NAN):"),
    "makes_interval: the same infinity twice gives the empty set (the old rule)": (
        "intervals.py", "    if given in (MAKE_NAN, MAKE_EQUAL_INF):\n        want = (\"nonempty\", NINF, INF)\n    elif given == MAKE_REVERSED:",
        "    if given == MAKE_NAN:\n        want = (\"nonempty\", NINF, INF)\n    elif given in (MAKE_REVERSED, MAKE_EQUAL_INF):"),
    "makes_interval: reversed bounds give the whole line": (
        "intervals.py", "    if given in (MAKE_NAN, MAKE_EQUAL_INF):\n        want = (\"nonempty\", NINF, INF)\n    elif given == MAKE_REVERSED:",
        "    if given in (MAKE_NAN, MAKE_EQUAL_INF, MAKE_REVERSED):\n        want = (\"nonempty\", NINF, INF)\n    elif False:"),
    "makes_interval: bounds of two limbs compared by their leading limbs": (
        "intervals.py", "    L, U = bound_value(fmt, x[a0:a1]), bound_value(fmt, x[b0:b1])\n    es.applicable += 1\n    given",
        "    L, U = x[a0], x[b0]\n    es.applicable += 1\n    given"),
    "makes_ball from an interval: the same infinity twice gives the empty set (the old rule)": (
        "intervals.py", "    if given == MAKE_REVERSED:\n        want = \"empty\"",
        "    if given in (MAKE_REVERSED, MAKE_EQUAL_INF):\n        want = \"empty\""),
    "makes_ball from an interval: a NaN bound gives the empty set": (
        "intervals.py", "    if given == MAKE_REVERSED:\n        want = \"empty\"",
        "    if given in (MAKE_REVERSED, MAKE_NAN):\n        want = \"empty\""),
    "constructors: the same infinity twice classed as reversed bounds": (
        "intervals.py", "    if L == U and type(L) is not int:\n        return MAKE_EQUAL_INF",
        "    if L == U and type(L) is not int:\n        return MAKE_REVERSED"),
    "constructors: a NaN bound tested after the same infinity": (
        "intervals.py", "    if L == NAN or U == NAN:\n        return MAKE_NAN\n    if L == U and type(L) is not int:\n        return MAKE_EQUAL_INF",
        "    if L == U and type(L) is not int:\n        return MAKE_EQUAL_INF\n    if L == NAN or U == NAN:\n        return MAKE_NAN"),
    # The cells of the table of the constructors, and the classes of two limbs, that the guards
    # ask for.
    "constructors: a <= b and a > b swapped in the cells": (
        "intervals.py", "        s += \", a <= b\" if L <= U else \", a > b\"",
        "        s += \", a <= b\" if L >= U else \", a > b\""),
    "constructors: lo and hi of a cell exchanged": (
        "intervals.py", "    s = MAKE_CELL % (name(L, \"a\"), name(U, \"b\"))",
        "    s = MAKE_CELL % (name(U, \"a\"), name(L, \"b\"))"),
    "makes_interval: the cell not counted": (
        "intervals.py", "    es.count(make_cell(L, U))\n", "\n"),
    "makes_ball from an interval: the cell not counted": (
        "intervals.py", "    es.count(make_cell(lo, hi))\n", "\n"),
    "makes_interval: zeros of opposite signs not read": (
        "intervals.py", "            if toks[a0 + 1].startswith(\"-\") != toks[b0 + 1].startswith(\"-\"):",
        "            if False:"),
    "makes_interval: reversed bounds of equal leading limbs not counted": (
        "intervals.py", "        elif given == MAKE_REVERSED and x[a0] == x[b0]:", "        elif False:"),
    "gen6: the infinities stratum never gives the same infinity twice": (
        "gen6.py", "        a = _inf(k, rng.sign()) if rng.chance(2, 3) else _number(fmt, rng, k, \"uniform\")\n        b = _inf(k, rng.sign())",
        "        a = _inf(k, -1) if rng.chance(2, 3) else _number(fmt, rng, k, \"uniform\")\n        b = _inf(k, 1)"),
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
    # Stage B of Milestone 2: the maps, the folds of maxima, the convolutions, their kernels.
    "map: a finite element from a non-finite operand accepted": (
        "maps.py", '                bad_e.append("element %d is finite although an operand is not" % i)',
        "                pass"),
    "map: the canonical NaN of the second pass not required": (
        "maps.py", "        if not all(t == NAN for t in z):\n            reasons.append(\"finite_or_nan: element",
        "        if False:\n            reasons.append(\"finite_or_nan: element"),
    "map and conv: the flag not compared": (
        "maps.py", "    if flag != want:", "    if False:"),
    "map: the step's verdict on an element ignored": (
        "maps.py", '                bad_e.extend("element %d: %s" % (i, r) for r in v[1])',
        "                pass"),
    "map: a finite element beyond Omega accepted": (
        "maps.py", '                bad_e.append("element %d: %s" % (i, "the step\'s exact result rounds beyond Omega, "',
        '                ("element %d: %s" % (i, "the step\'s exact result rounds beyond Omega, "'),
    "map: power_of_two of a scalar not checked": (
        "maps.py", "        if type(v) is not int or v <= 0 or v & (v - 1):", "        if False:"),
    "map: canonical of an element not checked": (
        "maps.py", "            if not XT.canonical(fmt, x[lo:lo + 2]):", "            if False:"),
    "map: the step's arguments in the reverse order": (
        "maps.py", "        self.args = [pos[n] for n in m.step_args]",
        "        self.args = [pos[n] for n in reversed(m.step_args)]"),
    "map: a step requirement the map lacks accepted": (
        "maps.py", '            raise ClaimsError("%s: the step requires %s(%s), which the map does not require of %s"\n                              % (nm, r[0], ", ".join(r[1:]), arg))',
        "            pass"),
    "map: the value not compared with the step's": (
        "maps.py", "        if k.value_tree is None or not _same_value(k.value_tree, self.value_tree, rename):",
        "        if k.value_tree is None:"),
    "conv: each coefficient without its last term": (
        "maps.py", "    return [(i, j - i) for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1)]",
        "    return [(i, j - i) for i in range(max(0, j - ny + 1), min(j, nx - 1))]"),
    "conv: a coefficient's fold_error not judged": (
        "maps.py", "                    why = FO._fold_error(dot, e, es, case, zz, line)\n                    if why:",
        "                    why = FO._fold_error(dot, e, es, case, zz, line)\n                    if False:"),
    "conv: the canonical NaN not required": (
        "maps.py", "        if not all(t == NAN for t in z):\n            reasons.append(\"finite_or_nan: coefficient",
        "        if False:\n            reasons.append(\"finite_or_nan: coefficient"),
    "conv: canonical() of an entry not checked": (
        "maps.py", "            if not XT.canonical(fmt, e[lo - off:hi - off]):", "            if False:"),
    "conv: the two lengths read swapped": (
        "maps.py", "    nx, ny = int(lt[3]), int(lt[4])", "    ny, nx = int(lt[3]), int(lt[4])"),
    "claims: a convolution read in the order of the list": (
        "claims.py", "            for raw in [r for r in fl if not any(r is c for c in later)] + later:",
        "            for raw in fl:"),
    "maxima: a result below V accepted": (
        "folds.py", "    if rc < Vc:\n        # (Beyond Omega too", "    if False:\n        # (Beyond Omega too"),
    "maxima: a step more allowed": (
        "folds.py", '    while t != r and k < c["steps"]:', '    while t != r and k < c["steps"] + 1:'),
    "maxima: a false flag with a finite top accepted": (
        "folds.py", "        if type(top) is int:\n            return (\"the flag is false although every element is finite and the bound",
        "        if False:\n            return (\"the flag is false although every element is finite and the bound"),
    "maxima: V the value of the first element": (
        "folds.py", "    return max(case.vals) if case.vals else 0", "    return case.vals[0] if case.vals else 0"),
    "maxima: over not read": (
        "folds.py", '            if raw["over"] != "max":', "            if False:"),
    "maximum: the output not compared": (
        "check.py", '        if z[e["first"]] << e["sh_out"] != max(a, b):', "        if False:"),
    "maximum: the smaller argument expected": (
        "check.py", '        if z[e["first"]] << e["sh_out"] != max(a, b):', '        if z[e["first"]] << e["sh_out"] != min(a, b):'),
    "maximum: the outcomes swapped": (
        "check.py", 'es.count("first argument larger" if a > b else "second argument larger" if b > a',
        'es.count("second argument larger" if a > b else "first argument larger" if b > a'),
    "finite_or_nan with if: the mask ignored": (
        "extended.py", '    on = c["cond_in"] is None or x[c["cond_in"]] == 1', "    on = True"),
    "finite_or_nan with steps: the steps ignored": (
        "extended.py", '    for _ in range(c["steps"]):\n        t = next_up(fmt, t)', "    for _ in range(0):\n        t = next_up(fmt, t)"),
    "finite_or_nan with steps: nextUp of -inf is -inf": (
        "extended.py", "    if v == NINF:\n        return -fmt.omega", "    if v == NINF:\n        return v"),
    "claims: steps 0 of finite_or_nan accepted": (
        "claims.py", "            if not isinstance(st, int) or isinstance(st, bool) or st < 1:",
        "            if not isinstance(st, int) or isinstance(st, bool) or st < 0:"),
    "claims: if of finite_or_nan naming an output accepted": (
        "claims.py", "            if not isinstance(m, str) or m not in kernel.input_names or m not in kernel.masks:",
        "            if not isinstance(m, str):"),
    "genmap: no overflow among the elements of a sum": (
        "genmap.py", '    elif mode == "overflow":\n        t = rng.below(3)', '    elif mode == "no overflow":\n        t = rng.below(3)'),
    "genmap: no convolution of an empty array": (
        "genmap.py", 'CONV_LENGTHS = ((0, 0), (0, "s"), ("s", 0),', 'CONV_LENGTHS = ((1, 1), (1, "s"), ("s", 1),'),
    "gen7: the tight case of axpy off the tie": (
        "gen7.py", "        y = _scaled_exact(fmt, (4 * j + 1) * u, E)", "        y = _scaled_exact(fmt, (4 * j + 3) * u, E)"),
    # What a summary keeps (oracle/README.md, "The size of a summary").
    "summary: the step's statistics keep the map's line": (
        "maps.py", "            v = ck.verdict(pl.step, sub, x, z, ElementLine(m.step, fname, pl, ins, outs, n, i,\n"
        "                                                           etag))",
        "            v = ck.verdict(pl.step, sub, x, z, line)"),
    "summary: an element line with the outputs of the next element": (
        "maps.py", "        z = self.z or [self.outs[j * n + i] for j in range(pl.W)]",
        "        z = self.z or [self.outs[j * n + i + 1] for j in range(pl.W)]"),
    "summary: the profile keeps every distance": (
        "check.py", "            if best is None or not _gt(best, v[0]):", "            if True:"),
    "summary: a record only when strictly larger": (
        "check.py", "            if best is None or not _gt(best, v[0]):",
        "            if best is None or _gt(v[0], best):"),
    "summary: a distance without its ratio loses its place in a merge": (
        "check.py", "                self.profile.setdefault(d, None)", "                pass"),
    "summary: the distances not read back": (
        "check.py", "            present.update(range(lo, hi + 1))", "            pass"),
    "gen2: the one-limb scale family's operand of two limbs": (
        "gen2.py", "    vals[xn] = [x]\n    vals[cn] = [_pow2(fmt, n)]\n    return vals",
        "    vals[xn] = [x, 0]\n    vals[cn] = [_pow2(fmt, n)]\n    return vals"),
    # The kernels of the ball vectors and of the accumulator (bvec.py, gen8.py, cexpr.py).
    "radius: an output below the stated value accepted": (
        "bvec.py", "            if ov < v:\n                es.count(\"below the stated value\")",
        "            if False:\n                es.count(\"below the stated value\")"),
    "radius: a NaN output accepted": (
        "bvec.py", "        if o == NAN or o == NINF:\n            why = \"upper: the output is",
        "        if o == NINF:\n            why = \"upper: the output is"),
    "radius: -inf accepted": (
        "bvec.py", "        if o == NAN or o == NINF:\n            why = \"upper: the output is",
        "        if o == NAN:\n            why = \"upper: the output is"),
    "radius: unless ignored": (
        "bvec.py", '        if c["unless"] is not None and x[c["unless"]] == 1:',
        "        if False:"),
    "radius: unless read the other way": (
        "bvec.py", '        if c["unless"] is not None and x[c["unless"]] == 1:',
        '        if c["unless"] is not None and x[c["unless"]] == 0:'),
    "radius: the equality of exact_when not judged": (
        "bvec.py", "                if conds_hold and d != 0:", "                if False:"),
    "radius: +inf accepted where exact_when holds": (
        "bvec.py", "            if conds_hold:\n                why = \"upper: exact_when holds but the output is +inf",
        "            if False:\n                why = \"upper: exact_when holds but the output is +inf"),
    "radius: a mask condition always true": (
        "bvec.py", "conds.append((lambda x, slot=slot: x[slot] == 1,",
        "conds.append((lambda x, slot=slot: x[slot] >= 0,"),
    "radius: the equality judged beyond Omega": (
        "bvec.py", "                if v > Fraction(fmt.omega) * eta:", "                if False:"),
    "radius: +inf from small operands not suspicious": (
        "bvec.py", "            elif _small(pl, x, v):", "            elif False:"),
    "radius: abs( ) of a value ignored": (
        "cexpr.py", "        return abs(evaluate(tree[1], env))", "        return evaluate(tree[1], env)"),
    "exact_flag: not compared": (
        "bvec.py", "    if f != (1 if holds else 0):", "    if False:"),
    "exact_flag: read inverted": (
        "bvec.py", '    holds = all(h(x) for h, _t in e["exact"])',
        '    holds = not all(h(x) for h, _t in e["exact"])'),
    "finish: nonneg ignored": (
        "bvec.py", "    want = not off and type(v) is int and (not nonneg or v >= 0)",
        "    want = not off and type(v) is int"),
    "finish: a zero read as below zero": (
        "bvec.py", "    want = not off and type(v) is int and (not nonneg or v >= 0)",
        "    want = not off and type(v) is int and (not nonneg or v > 0)"),
    "finish: if_all read as its first mask": (
        "bvec.py", "    off = [n for n, i in zip(names, slots) if x[i] != 1]",
        "    off = [n for n, i in zip(names[:1], slots[:1]) if x[i] != 1]"),
    "finish: the output not compared": (
        "bvec.py", "        if len(w) != 1 or w[0] != v:", "        if False:"),
    "finish: the NaN of a false flag not required": (
        "bvec.py", "    elif not all(t == NAN for t in w):\n        out.append(\"finite_or_nan: the flag is false, and the output is not a NaN\")",
        "    elif False:\n        out.append(\"finite_or_nan: the flag is false, and the output is not a NaN\")"),
    "acc: a value of its own read as the kernel's": (
        "bvec.py", '        if c["kind"] == "rounded" and "own" in c:', "        if False:"),
    "acc: a finite b beyond Omega accepted": (
        "bvec.py", "        es.count(ACC_BEYOND)\n        return (\"rounded(%s): the output is finite, and its value",
        "        es.count(ACC_BEYOND)\n        return None and (\"rounded(%s): the output is finite, and its value"),
    "acc: its own rounding not compared": (
        "bvec.py", "    if o != r:\n        return \"rounded(%s): the output is not its value",
        "    if False:\n        return \"rounded(%s): the output is not its value"),
    "acc: judged where its group is not finite": (
        "bvec.py", "        if type(z[rg[0][0]]) is not int:\n            es.count(GROUP_NONFINITE)",
        "        if False:\n            es.count(GROUP_NONFINITE)"),
    "at_most not checked": (
        "check.py", "                if BV.at_most_violated(r, x):", "                if False:"),
    "at_most: the bound one more": (
        "bvec.py", "    return (v << q) > k if q >= 0 else v > (k << -q)",
        "    return (v << q) > k + 1 if q >= 0 else v > ((k + 1) << -q)"),
    "at_most: the enumeration up to twice the bound": (
        "gen.py", "                    d = [t for t in d if not ((sum(t) << q) > r[2] if q >= 0\n                                              else sum(t) > (r[2] << -q))]",
        "                    d = [t for t in d if not ((sum(t) << q) > 2 * r[2] if q >= 0\n                                              else sum(t) > (2 * r[2] << -q))]"),
    "conditional: an infinite output with ok true never suspicious": (
        "check.py", "                if BV.small_inputs(pl, x) and BV.small_stated(pl, c, x, z):",
        "                if False:"),
    "claims: unless naming any input accepted": (
        "bvec.py", "    if not isinstance(name, str) or name not in kernel.input_names or name not in kernel.masks:",
        "    if not isinstance(name, str) or name not in kernel.input_names:"),
    "claims: exact_flag naming any output accepted": (
        "bvec.py", "    if not isinstance(m, str) or m not in dict(kernel.outputs) or m not in kernel.masks:",
        "    if not isinstance(m, str) or m not in dict(kernel.outputs):"),
    "claims: nonneg false accepted": (
        "bvec.py", '        if raw["nonneg"] is not True:', "        if False:"),
    "claims: if_all of one mask accepted": (
        "bvec.py", "        if not isinstance(lst, list) or len(lst) < 2 or",
        "        if not isinstance(lst, list) or len(lst) < 1 or"),
    "claims: a limb of the value of rounded beyond the input's": (
        "bvec.py", "            raise ClaimsError(\"%s: value: %s[%d] is not a limb of %s, which has %d\" % (",
        "            pass\n        if False:\n            raise ClaimsError(\"%s: value: %s[%d] is not a limb of %s, which has %d\" % ("),
    "claims: an upper entry with gaps and a value of its own accepted": (
        "bvec.py", "    if \"gaps\" in raw:\n        raise ClaimsError(\"%s: an upper entry has gaps, or a value of its own",
        "    if False:\n        raise ClaimsError(\"%s: an upper entry has gaps, or a value of its own"),
    "claims: a radius kernel with entries of other kinds accepted": (
        "bvec.py", "    if radius and len(radius) != len(kernel.ensures):", "    if False:"),
    "claims: exact_when of masks alone accepted": (
        "bvec.py", '    if masks and all(c[0] == "mask" for c in out):', "    if False:"),
    "claims: at_most of 0 accepted": (
        "bvec.py", "    if k < 1:\n        raise ClaimsError(\"%s: requirement %r: the bound of at_most()",
        "    if k < 0:\n        raise ClaimsError(\"%s: requirement %r: the bound of at_most()"),
    "gen8: huge without the top binades": (
        "gen8.py", "        v = G2._top(fmt, rng) if rng.chance(2, 3) else _pos(fmt, rng, rng.between(\n            max(fmt.qmin, fmt.emax - fmt.p), fmt.emax))",
        "        v = _pos(fmt, rng, G2._e_any(fmt, rng))"),
    "gen8: zeros not zero": (
        "gen8.py", '        v = 0 if rng.chance(3, 4) else _pos(fmt, rng, G2._e_any(fmt, rng))',
        '        v = _pos(fmt, rng, G2._e_any(fmt, rng))'),
    "gen8: atnormal off N": (
        "gen8.py", "            N = fmt.lam\n", "            N = 3 * fmt.lam\n"),
    "gen8: mixed of one magnitude": (
        "gen8.py", "            d = 0 if n == big else rng.between(fmt.p, 3 * fmt.p + 4)",
        "            d = 0"),
    "gen8: atop not at the top": (
        "gen8.py", "            vals[n] = [abs(G2._top(fmt, rng))]",
        "            vals[n] = [abs(G2.limb(fmt, rng, \"uniform\")) >> 8]"),
    "gen8: cancel not cancelling": (
        "gen8.py", "            t = [-v for v in s]\n", "            t = [v for v in s]\n"),
    "gen8: tie off the tie": (
        "gen8.py", "                h = (u0 // 2) * (2 * rng.below(3) + 1)",
        "                h = (u0 // 4) * (2 * rng.below(3) + 1)"),
    "gen8: apart not apart": (
        "gen8.py", "        d = rng.between(p + 2, 3 * p + 4) * (1 if rng.bits(1) else -1)",
        "        d = 0"),
    "gen8: exactprod of long significands": (
        "gen8.py", '            vals[n] = [_pos(fmt, rng, e, "short" if stratum in ("exactprod", "tie") else "uniform")]',
        '            vals[n] = [_pos(fmt, rng, e, "short" if stratum in ("tie",) else "uniform")]'),
    "gen8: limit far from the limit": (
        "gen8.py", "                x = Fraction(1, 2) * (1 + Fraction(rng.between(-64, 64), 256))",
        "                x = Fraction(1, 8) * (1 + Fraction(rng.between(-64, 64), 256))"),
    "gen8: beyond below the limit": (
        "gen8.py", "                x = Fraction(1, 2) * (2 ** rng.between(1, max(1, fmt.p)))",
        "                x = Fraction(1, 4)"),
    "gen8: integer counts not integers": (
        "gen8.py", '    if stratum == "integer" or rng.chance(1, 2):',
        '    if rng.chance(1, 2):'),
    "gen8: abig not big": (
        "gen8.py", "            vals[a] = [_pos(fmt, rng, rng.between(max(fmt.qmin, fmt.emax - fmt.p), fmt.emax - 4))]",
        "            vals[a] = [_pos(fmt, rng, G2._e_any(fmt, rng) // 2)]"),
    "gen8: negative not negative": (
        "gen8.py", "        x = -(1 if k == 0 else fmt.lam if k == 1 else fmt.omega if k == 2 else",
        "        x = +(1 if k == 0 else fmt.lam if k == 1 else fmt.omega if k == 2 else"),
    "gen8: nonfinite finite": (
        "gen8.py", "        x = (INF, NINF, NAN)[rng.below(3)]", "        x = fmt.lam"),
    "gen8: zeros of the finishes not zero": (
        "gen8.py", '    elif stratum == "zeros":\n        x = 0\n', '    elif stratum == "zeros":\n        x = 1\n'),
    "gen8: top not at the top": (
        "gen8.py", "        x = fmt.omega if rng.bits(1) else F.pred(fmt, fmt.omega)", "        x = fmt.lam"),
    "gen8: masks always true": (
        "gen8.py", "            vals[n] = [1 if rng.chance(2, 3) else 0]", "            vals[n] = [1]"),
    # The folds of the ball vectors and the requests in place (bvfolds.py, genbv.py, maps.py,
    # genmap.py).
    "bv: V1 not judged": (
        "bvfolds.py", "    # V1: canonical; the flag.\n    res = _state(fmt, zs, r)\n    if res is None:",
        "    # V1: canonical; the flag.\n    res = _state(fmt, zs, r)\n    if False:"),
    "bv: the flag not judged": (
        "bvfolds.py", "            flag, \"finite\" if type(r) is int else F.fixed_hex(fmt, r)))\n"
        "    if f.kind == \"makes_ball_vector\":",
        "            flag, \"finite\" if type(r) is int else F.fixed_hex(fmt, r))) if False else "
        "None\n    if f.kind == \"makes_ball_vector\":"),
    "bv: the flag read the other way": (
        "bvfolds.py", "    if flag != (1 if type(r) is int else 0):\n        fail(\"flag\", \"the flag is %d "
        "although the radius is %s\" % (\n            flag, \"finite\" if type(r) is int else "
        "F.fixed_hex(fmt, r)))\n    if f.kind",
        "    if flag != (0 if type(r) is int else 1):\n        fail(\"flag\", \"the flag is %d "
        "although the radius is %s\" % (\n            flag, \"finite\" if type(r) is int else "
        "F.fixed_hex(fmt, r)))\n    if f.kind"),
    "bv: conv: the flag not judged": (
        "bvfolds.py", "    if flag != (1 if type(r) is int else 0):\n        fail(\"flag\", \"the flag is %d "
        "although the radius is %s\" % (\n            flag, \"finite\" if type(r) is int else "
        "F.fixed_hex(fmt, r)))\n    whole = ",
        "    if False:\n        fail(\"flag\", \"the flag is %d "
        "although the radius is %s\" % (\n            flag, \"finite\" if type(r) is int else "
        "F.fixed_hex(fmt, r)))\n    whole = "),
    "bv: conv: V1 not judged": (
        "bvfolds.py", "    res = _state(fmt, zs, r)\n    if res is None:\n        fail(\"V1\", \"the result is "
        "neither a finite ball vector nor the whole space\")",
        "    res = _state(fmt, zs, r)\n    if False:\n        fail(\"V1\", \"the result is "
        "neither a finite ball vector nor the whole space\")"),
    "bv: inplace= beyond the arrays accepted": (
        "bvfolds.py", "        if m is None or int(m.group(1)) >= len(f.arrays) or",
        "        if m is None or int(m.group(1)) > len(f.arrays) or"),
    "bv: inplace= not a number accepted": (
        "bvfolds.py", '_INPLACE = re.compile(r"inplace=(0|[1-9][0-9]*)\\Z")',
        '_INPLACE = re.compile(r"inplace=([0-9]+)\\Z")'),
    "bv: in place not counted": (
        "bvfolds.py", "        es.count(INPLACE % inplace)", "        pass"),
    "bv: a finite result beside a whole operand accepted": (
        "bvfolds.py", "    if finite and (whole_op or not scal_fin):\n        fail(\"V3\"",
        "    if False:\n        fail(\"V3\""),
    "bv: V2 not judged": (
        "bvfolds.py", "            if rmin > rr:\n                fail(\"V2\", \"entry %d: the set",
        "            if False:\n                fail(\"V2\", \"entry %d: the set"),
    "bv: V2 on one side of the center": (
        "bvfolds.py", "            rmin = max(c - lo, hi - c)\n            if rmin > rr:",
        "            rmin = hi - c\n            if rmin > rr:"),
    "bv: V2 an unbounded set accepted": (
        "bvfolds.py", "            if type(lo) is not int or type(hi) is not int:\n                "
        "fail(\"V2\", \"entry %d: the set is unbounded",
        "            if False:\n                fail(\"V2\", \"entry %d: the set is unbounded"),
    "bv: V3 of the step not judged": (
        "bvfolds.py", "        v = ck.verdict(sp, sub, xs, z, el)", "        v = (\"ok\", [])"),
    "bv: V3 of the radius kernel not judged": (
        "bvfolds.py", "    for w in BV.radius_reasons(rk, sub_r, xr, [r], line):\n        fail(\"V3\"",
        "    for w in []:\n        fail(\"V3\""),
    "bv: the radius kernel at m = +0": (
        "bvfolds.py", "    m = max((abs(z[0]) for z in zs), default=0)\n    rk = pl.radius",
        "    m = 0\n    rk = pl.radius"),
    "bv: V4 not judged": (
        "bvfolds.py", "            if not finite:\n                fail(\"V4\", \"every operand",
        "            if False:\n                fail(\"V4\", \"every operand"),
    "bv: V4 without radii_when": (
        "bvfolds.py", "        elif all(h(tuple(sc) + (0,) * pl.L) for h in pl.rw) and all(",
        "        elif all("),
    "bv: V4 without finite_when": (
        "bvfolds.py", "                h(x) for x in elems for h in pl.fw):",
        "                True for x in elems):"),
    "bv: V4 claimed below finite_from": (
        "bvfolds.py", "        elif not pl.v4:\n            es.count(V4_BELOW)",
        "        elif False:\n            es.count(V4_BELOW)"),
    "bv: V4 judged in every format": (
        "bvfolds.py", "    return fmt.qmax >= 1 and fmt.qmin <= 3 - fmt.qmax - 2 * fmt.p",
        "    return True"),
    "bv: V4 judged where eta is above binary_float's": (
        "bvfolds.py", "    return fmt.qmax >= 1 and fmt.qmin <= 3 - fmt.qmax - 2 * fmt.p",
        "    return fmt.qmax >= 1"),
    "bv: exactness not judged": (
        "bvfolds.py", "                if c - rr != lo or c + rr != hi:",
        "                if False:"),
    "bv: exactness judged where exact_when fails": (
        "bvfolds.py", "        if not failing and elems:\n            es.count(EXACT_HOLDS)",
        "        if elems:\n            es.count(EXACT_HOLDS)"),
    "bv: makes: a center not finite ignored": (
        "bvfolds.py", "    whole = rg == NAN or rg == INF or rg == NINF or (type(rg) is int and rg < 0) "
        "or nonfin",
        "    whole = rg == NAN or rg == INF or rg == NINF or (type(rg) is int and rg < 0)"),
    "bv: makes: a negative radius kept": (
        "bvfolds.py", "    whole = rg == NAN or rg == INF or rg == NINF or (type(rg) is int and rg < 0) "
        "or nonfin",
        "    whole = rg == NAN or rg == INF or rg == NINF or nonfin"),
    "bv: makes: a NaN radius kept": (
        "bvfolds.py", "    whole = rg == NAN or rg == INF or rg == NINF or (type(rg) is int and rg < 0) "
        "or nonfin",
        "    whole = rg == INF or rg == NINF or (type(rg) is int and rg < 0) or nonfin"),
    "bv: makes: the radius not compared": (
        "bvfolds.py", "    if r != rg:\n        fail(\"makes_ball_vector\"",
        "    if False:\n        fail(\"makes_ball_vector\""),
    "bv: makes: the centers not compared": (
        "bvfolds.py", "        if list(z) != list(x[lo:hi]):", "        if False:"),
    "bv: makes: the sign of a zero radius not read": (
        "bvfolds.py", "        rcls = \"-0\" if tok[i].startswith(\"-\") else \"+0\"",
        "        rcls = \"+0\""),
    "bv: conv: V2 not judged": (
        "bvfolds.py", "            if max(c - lo, hi - c) > rr:\n                fail(\"V2\", \"coefficient",
        "            if False:\n                fail(\"V2\", \"coefficient"),
    "bv: conv: count_when ignored": (
        "bvfolds.py", "            if CX.evaluate(tree, env) > CX.evaluate(kt, env):\n                cw = False",
        "            if False:\n                cw = False"),
    "bv: conv: the count the larger length": (
        "bvfolds.py", "        n = min(nx, ny)\n        cw = True",
        "        n = max(nx, ny)\n        cw = True"),
    "bv: conv: V3 the radius below the stated value accepted": (
        "bvfolds.py", "    if r * eta < v:\n        fail(\"V3\", \"the radius is below",
        "    if False:\n        fail(\"V3\", \"the radius is below"),
    "bv: conv: the bound's stated values taken zero": (
        "bvfolds.py", "                bnames[out] = CX.evaluate(pl.bound_values[out], pl.env(dict(bnames)))",
        "                bnames[out] = Fraction(0)"),
    "bv: conv: V4 not judged": (
        "bvfolds.py", "            if not finite:\n                fail(\"V4\", \"both operands",
        "            if False:\n                fail(\"V4\", \"both operands"),
    "genbv: the count stratum away from the edge": (
        "genbv.py", "        if g._edge < L and rng.chance(3, 4):", "        if False:"),
    "genbv: in place, array 0 only": (
        "genbv.py", "        self.inplace = [i for i, (_n, l) in enumerate(f.arrays) if l == f.wlimbs] "
        "if inplace else []",
        "        self.inplace = [0] if inplace else []"),
    "genbv: the stratum whole without the whole space": (
        "genbv.py", "            vals[a] = [[0] * k for _ in range(n)]\n            sc[radius_of[a]] = INF",
        "            vals[a] = [[0] * k for _ in range(n)]\n            sc[radius_of[a]] = 0"),
    "genbv: the enumeration without the whole space": (
        "genbv.py", "        return len(self.radii) * len(self.entries) ** n + 1",
        "        return len(self.radii) * len(self.entries) ** n"),
    "genbv: the enumeration without the lane orders": (
        "genbv.py", "            orders = [\"seq\"] + ([] if self.conv else [\"lanes:%d\" % W",
        "            orders = [\"seq\"] + ([] if True else [\"lanes:%d\" % W"),
    "maps: in place not counted": (
        "maps.py", "        es_e.count(\"in place: array %d\" % inplace)", "        pass"),
    "genmap: in place, array 0 only": (
        "genmap.py", "        self.inplace = [i for i, (_n, l) in enumerate(m.arrays) if l == m.wlimbs] "
        "if inplace else []",
        "        self.inplace = [0] if inplace else []"),
    "genmap: the header of a run in place": (
        "genmap.py", "(\" inplace=yes\" if getattr(g, \"inplace\", None)",
        "(\"\" if getattr(g, \"inplace\", None)"),
}


# The selftest's longest tests (the exhaustive ones, the planted faults on every case), which
# --fail-fast runs after the others: a mutant is caught at the first test that fails, and most
# fail in a short one. A survivor still runs every test.
LONG = ("correct_runner_toy_exhaustive", "exhaustive_wave2", "injected_wave2_exhaustive",
        "injected_wave3_exhaustive", "exhaustive_wave3", "iv_planted", "fold_planted",
        "injected_wave3", "injected_exhaustive", "fold_brackets", "fold_reference", "iv_exhaustive")
FAIL_FAST = False


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
    fast = ["--fail-fast", "--last", ",".join(LONG)] if FAIL_FAST else []
    r = subprocess.run([sys.executable, os.path.join(copy, "kairn-oracle"), "selftest",
                        "--quick", "--workdir", os.path.join(os.path.dirname(copy), "wd")] + fast,
                       capture_output=True, text=True)
    if "selftest: no test named" in r.stdout:
        return "STALE", "(%s)" % r.stdout.strip()   # a name of LONG that is no test's
    failing = [ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
    return ("caught" if r.returncode else "SURVIVED"), ", ".join(failing)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=1, help="mutants run at the same time")
    ap.add_argument("--only", help="comma-separated mutant names")
    ap.add_argument("--fail-fast", action="store_true",
                    help="stop each mutant's selftest at its first failing test, the longest "
                         "tests last (the failing tests listed are then the first only)")
    a = ap.parse_args()
    global FAIL_FAST
    FAIL_FAST = a.fail_fast
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
