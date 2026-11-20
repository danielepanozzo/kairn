"""search: an adversarial search for the operands that bring a kernel closest to its claims.

For one kernel and one format, a population of cases evolves through a runner of the line
protocol, and every completed line is judged by the oracle's own checker (check.py). The checker's
statistics of one line give, for each `ensures` entry, the quantity the claim bounds:

- `error`: the error over the bound it is allowed, and the observed constant far from the
  underflow range (|err| / (u^k rho) where u^k rho >= 2^p eta), both to be made large;
- `upper`: the excess of the result over the exact value, in gaps of the result, to be made large;
- `encloses`: the slack of the returned radius over the smallest enclosing radius, in gaps of the
  radius, to be made small (below zero the set is not enclosed).

A full kernel of the extended domain is searched on finite operands, where `extends` applies its
core's entries (F2), and those are its quantities. Each quantity keeps an elite of the best cases
found. A generation is a batch of children of elites: each takes one to three moves natural for
floating-point operands (a bit of a significand flipped, a limb stepped by units in the last place
or given an extreme significand, a second limb moved to the edge of the normalization invariant, an
exponent changed, an operand negated, operands swapped or crossed between parents, a sum moved to
a tie or toward cancellation, a case scaled toward the underflow or the overflow threshold) and is
then repaired into the kernel's requirements (a pair renormalized, a radius made nonnegative, a
power of two snapped, operands ordered for abs_ge) and checked against them by the generator's own
test (gen.valid), so that every case written is in the kernel's domain. The first generation is
made of the seeds: lines from files (the attaining lines of stored brute-force summaries, the
regression cases), the cases of the literature in tight.py, and cases of every stratum of the
oracle's generator.

The search is deterministic: its random choices come from a keyed hash of (seed, kernel, format)
and the generation number, so the same runner gives the same search. A line it reports is an
ordinary completed line, which `check` judges alike. Any failure stops the search of that kernel
and format and is reported with the command that reproduces it.
"""

import concurrent.futures as cf
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from fractions import Fraction

from . import check as C
from . import fmt as F
from . import gen as G
from . import gen2 as G2
from . import tight
from .claims import load_claims, ClaimsError

ORACLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(ORACLE_DIR)
INTERP = os.path.join(REPO_DIR, "gen", "kairn-gen")
REGRESSION = os.path.join(REPO_DIR, "tests", "regression", "cases.txt")
TAILS = ("near", "any", "half+", "half-", "quarter-", "max", "eta", "tiny", "zero")
# What stands for an infinite ratio (an inexact result where the bound is zero), which is a
# failure anyway: above every finite score the search can meet.
HUGE = Fraction(1 << 64)
SEARCHED = ("error", "upper", "encloses")


class SearchError(ValueError):
    pass


class RunnerError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Numbers

def _round(fmt, n):
    """A fixed value rounded to the nearest number of the format, or None beyond Omega."""
    r = F.rn_fixed(fmt, n)
    return r if type(r) is int else None


def _scale(fmt, v, d):
    """v * 2^d rounded to nearest (exact when it is a number of the format), or None. An infinity
    or a NaN (the shrinker's cases of the extended domain) stays as it is."""
    if type(v) is not int or v == 0:
        return v
    r = F.rn(fmt, v, fmt.qmin + d)
    return r if type(r) is int else None


def _sig(fmt, v):
    """(M, unit): |v| = M * unit with unit the ulp of v, so M has at most p bits."""
    u = F.ulp(fmt, v)
    return abs(v) // u, u


def _sign(v):
    return -1 if v < 0 else 1


def _pow2(fmt, e):
    e = max(fmt.qmin, min(fmt.emax, e))
    return 1 << (e - fmt.qmin)


# ---------------------------------------------------------------------------
# A kernel in a format

class Problem:
    """A kernel in a format as the search and the shrinker see it: its operands and their roles,
    the requirements every case must satisfy, and the text of a case. A kernel of the extended
    domain is seen through its finite view (gen3.FiniteView): canonical() as normalized(), a ball
    as a normalized center and a nonnegative radius."""

    def __init__(self, kernel, fmt):
        self.kernel = kernel
        self.fmt = fmt
        from . import gen5, gen6
        self.valid5 = None
        try:
            if gen6.family_of(kernel) is not None:
                # The steps of axpy and of the folds of maxima (gen6.py).
                self.view = kernel
                self.shape = gen6.Shape6(kernel)
                self.make, self.strata = gen6.make_case, tuple(self.shape.strata)
            elif gen5.family_of(kernel) is not None:
                # The kernels of the folds' stage: their own families (the bounds' count, the
                # steps of the dot products, the finishes).
                self.view = kernel
                self.shape = gen5.Shape5(kernel)
                self.make, self.strata = gen5.make_case, tuple(self.shape.strata)
                self.valid5 = gen5.valid5
            elif kernel.extended:
                from . import gen3
                ext = gen3.ExtShape(kernel)
                self.view = gen3.FiniteView(kernel)
                self.shape, self.make, self.strata = ext.fshape, ext.fmake, tuple(ext.fstrata)
            elif G.first_wave_shape(kernel):
                self.view = kernel
                self.shape, self.make, self.strata = G.Shape(kernel), G.make_case, G.STRATA
            else:
                self.view = kernel
                self.shape = G2.Shape2(kernel)
                self.make, self.strata = G2.make_case, tuple(self.shape.strata)
        except G.GenError as ex:
            raise SearchError("%s: %s" % (kernel.name, ex))
        req = self.view.requires
        self.names = [n for n, _ in kernel.inputs]
        self.limbs = dict(kernel.inputs)
        self.roles = {}
        for n, l in kernel.inputs:
            if n in kernel.masks:
                role = "mask"
            elif l == 2:
                role = "x2"
            elif l > 2:
                raise SearchError("%s: inputs of more than two limbs are not searched" % kernel.name)
            elif ("power_of_two", n) in req:
                role = "pow2"
            elif ("nonneg", n) in req:
                role = "radius"
            elif ("count", n) in req:
                role = "count"
            else:
                role = "limb"
            self.roles[n] = role
        self.abs_ge = [(r[1], r[2]) for r in req if r[0] == "abs_ge"]
        tree = kernel.value_tree
        self.center_of = {}
        for e in kernel.ensures:
            if e.kind == "encloses":
                tree = e.set_tree
                for c, r in e.balls.values():
                    self.center_of[r] = c
        # The operation that joins the operands (of the value, or of a Ball kernel's set).
        self.op = tree[0] if tree is not None and tree[0] in ("+", "-", "*") else None
        # Operands that carry a value (limbs and pairs, a ball's center among them), and the
        # units a move takes as a whole: an operand, or a ball (its center and radius).
        self.values = [n for n in self.names if self.roles[n] in ("x2", "limb")]
        radius_of = {c: r for r, c in self.center_of.items()}
        self.units = []
        for n in self.names:
            if self.roles[n] == "radius" and n in self.center_of:
                continue
            self.units.append((n, radius_of[n]) if n in radius_of else (n,))

    # -- text ----------------------------------------------------------------------------------

    def text(self, vals, negz=(), tag=None):
        fmt = self.fmt
        toks = [self.kernel.name, fmt.name]
        for n in self.names:
            if self.roles[n] == "mask":
                toks.append(str(vals[n][0]))
                continue
            for i, v in enumerate(vals[n]):
                # A limb may be infinite or NaN in the shrinker's cases of the extended domain.
                toks.append(v if type(v) is not int else "-0x0p+0" if v == 0 and (n, i) in negz
                            else F.to_hex(v, fmt.qmin))
        if tag:
            toks.append("#" + tag)
        return " ".join(toks)

    def parse(self, line):
        """(vals, negz) of a line of this kernel and format (a request or a completed line: the
        tag and the result are ignored), or None when it is not a case of finite operands that
        satisfy the requirements."""
        left = line.strip().partition(" -> ")[0].split()
        if len(left) < 2 or left[0] != self.kernel.name:
            return None
        try:
            if F.parse_format(left[1]) != self.fmt:
                return None
        except F.FormatError:
            return None
        toks = [t for t in left[2:] if not t.startswith("#")]
        if len(toks) != sum(self.limbs.values()):
            return None
        vals, negz, k = {}, set(), 0
        for n in self.names:
            limbs = []
            for i in range(self.limbs[n]):
                t = toks[k]
                k += 1
                if self.roles[n] == "mask":
                    if t not in ("0", "1"):
                        return None
                    limbs.append(int(t))
                    continue
                try:
                    v = F.parse_limb(self.fmt, t)
                except F.LimbError:
                    return None
                if type(v) is not int or not F.is_member(self.fmt, v):
                    return None
                if v == 0 and t.startswith("-"):
                    negz.add((n, i))
                limbs.append(v)
            vals[n] = limbs
        return (vals, negz) if self.valid(vals) else None

    def valid(self, vals):
        if self.valid5 is not None:
            return (all(type(v) is int for vs in vals.values() for v in vs)
                    and self.valid5(self.fmt, self.kernel, vals))
        return all(type(v) is int for vs in vals.values() for v in vs) and G.valid(
            self.fmt, self.view, vals)

    # -- cases ---------------------------------------------------------------------------------

    def random_case(self, rng, stratum=None):
        """A case of a stratum of the oracle's generator (any, when None), or None."""
        if stratum is None:
            stratum = self.strata[rng.below(len(self.strata))]
        for _ in range(16):
            vals, negz = self.make(self.fmt, self.shape, rng, stratum)
            if self.valid(vals):
                return vals, set(negz)
        return None

    def repair(self, vals, negz):
        """The case brought back into the requirements, or None: a pair that is no longer
        normalized becomes the TwoSum of its limbs (exact), a radius its magnitude, a power of two
        the power of two of its leading bit; operands under abs_ge are ordered."""
        fmt = self.fmt
        for n in self.names:
            role = self.roles[n]
            v = vals[n]
            if any(type(t) is not int for t in v):
                return None
            if role == "x2":
                if not F.normalized_limbs(fmt, v):
                    s = _round(fmt, v[0] + v[1])
                    if s is None:
                        return None
                    v = [s, v[0] + v[1] - s]
            elif role == "radius":
                v = [abs(v[0])]
            elif role == "pow2":
                a = abs(v[0])
                v = [1 << (a.bit_length() - 1) if a else _pow2(fmt, 0)]
            elif role == "count":
                # count(m): m = 0 or m >= 1; a magnitude below 1 becomes 1.
                a = abs(v[0])
                one = (1 << -fmt.qmin) if fmt.qmin < 0 else 1
                v = [a if a == 0 or a >= one else one]
            elif role == "mask":
                v = [v[0] & 1]
            vals[n] = v
        for big, small in self.abs_ge:
            if abs(sum(vals[big])) < abs(sum(vals[small])) and self.limbs[big] == self.limbs[small]:
                vals[big], vals[small] = vals[small], vals[big]
        if not self.valid(vals):
            return None
        return vals, {(n, i) for n, i in negz if vals[n][i] == 0}

    # -- moves ---------------------------------------------------------------------------------

    def limb_move(self, rng, v):
        """A new value for one limb, or None."""
        fmt = self.fmt
        p = fmt.p
        k = rng.below(10)
        if v == 0 and k < 7:
            k = 8
        if k <= 2:
            # Flip one bit of the significand below its leading bit, the low bits more often.
            M, u = _sig(fmt, v)
            nb = M.bit_length()
            if nb < 2:
                return _round(fmt, v + (u if rng.bits(1) else -u))
            j = rng.below(min(nb - 1, 6)) if rng.bits(1) else rng.below(nb - 1)
            return _sign(v) * (M ^ (1 << j)) * u
        if k <= 4:
            # A few units in the last place up or down.
            M, u = _sig(fmt, v)
            n = (1, 1, 2, 3)[rng.below(4)] if rng.chance(3, 4) else 1 << rng.below(p)
            return _round(fmt, v + (n if rng.bits(1) else -n) * u)
        if k == 5:
            # An extreme significand in the same binade: a power of two, all ones, and their
            # neighbours.
            M, u = _sig(fmt, v)
            nb = M.bit_length()
            top = 1 << (nb - 1)
            pats = (top, (1 << nb) - 1, top | 1, max(top, (1 << nb) - 2),
                    top | (top >> 1) if nb > 1 else top)
            return _sign(v) * pats[rng.below(len(pats))] * u
        if k == 6:
            # Another exponent.
            d = rng.between(1, 3) if rng.chance(3, 4) else rng.between(1, 2 * p + 2)
            return _scale(fmt, v, d if rng.bits(1) else -d)
        if k == 7:
            return -v
        e = rng.between(fmt.qmin, fmt.emax) if v == 0 or k == 8 else \
            max(fmt.qmin, min(fmt.emax, fmt.binade(v) + rng.between(-2, 2)))
        return rng.sign() * G.in_binade(fmt, rng, e, "short" if rng.chance(1, 4) else "uniform")

    def operand_move(self, rng, vals, negz):
        """One move on one operand."""
        fmt = self.fmt
        n = self.names[rng.below(len(self.names))]
        role = self.roles[n]
        v = list(vals[n])
        if role == "x2":
            k = rng.below(9)
            if k <= 3:
                v[1] = self.limb_move(rng, v[1])
            elif k <= 5:
                v[0] = self.limb_move(rng, v[0])
            elif k == 6:
                # The second limb at an extreme of the invariant, or anywhere below.
                mode = TAILS[rng.below(len(TAILS))]
                x0 = v[0]
                if mode in ("half+", "half-") and x0:
                    e = G.even_lead(fmt, x0)
                    x0 = e if type(e) is int else x0
                v = [x0, G.tail_for(fmt, rng, x0, mode)]
            elif k == 7:
                d = rng.between(1, 3) if rng.chance(3, 4) else rng.between(1, 2 * fmt.p + 2)
                d = d if rng.bits(1) else -d
                v = [_scale(fmt, t, d) for t in v]
            else:
                v = [-v[0], -v[1]]
        elif role == "pow2":
            e = fmt.binade(v[0]) + (rng.between(-3, 3) if rng.chance(3, 4) else
                                    rng.between(-2 * fmt.p, 2 * fmt.p))
            v = [_pow2(fmt, e)]
        elif role == "radius":
            c = self.center_of.get(n)
            if rng.chance(1, 3) and c is not None:
                v = [G2.radius(fmt, rng, vals[c][0], G2.RADIUS_MODES[rng.below(len(G2.RADIUS_MODES))])]
            else:
                t = self.limb_move(rng, v[0])
                v = [None if t is None else abs(t)]
        elif role == "mask":
            v = [1 - v[0]]
        else:
            v = [self.limb_move(rng, v[0])]
        if any(t is None for t in v):
            return False
        vals[n] = v
        return True

    def case_move(self, rng, vals, negz):
        """One move on the case as a whole."""
        k = rng.below(8)
        if k == 0:
            return self._swap(rng, vals, negz)
        if k == 1:
            return self._cancel(rng, vals)
        if k == 2:
            return self._align(rng, vals)
        if k == 3:
            return self._tie(rng, vals)
        if k in (4, 5):
            return self._scale_case(rng, vals)
        if k == 6:
            zeros = [(n, i) for n in self.names if self.roles[n] != "mask"
                     for i, v in enumerate(vals[n]) if v == 0]
            if not zeros:
                return False
            z = zeros[rng.below(len(zeros))]
            negz ^= {z}
            return True
        fresh = self.random_case(rng)
        if fresh is None:
            return False
        unit = self.units[rng.below(len(self.units))]
        for n in unit:
            vals[n] = list(fresh[0][n])
        return True

    def crossover(self, rng, vals, negz, other):
        """Units taken from another case, each with probability 1/2."""
        took = False
        for unit in self.units:
            if rng.bits(1):
                for n in unit:
                    vals[n] = list(other.vals[n])
                took = True
        if took:
            negz |= {(n, i) for n, i in other.negz}
        return True

    def _two_values(self, rng):
        if len(self.values) < 2:
            return None
        i = rng.below(len(self.values))
        j = rng.below(len(self.values) - 1)
        j += j >= i
        return self.values[i], self.values[j]

    def _swap(self, rng, vals, negz):
        sig = {}
        for u in self.units:
            sig.setdefault(tuple((self.roles[n], self.limbs[n]) for n in u), []).append(u)
        pairs = [us for us in sig.values() if len(us) > 1]
        if not pairs:
            return False
        a, b = pairs[rng.below(len(pairs))][:2]
        for x, y in zip(a, b):
            vals[x], vals[y] = vals[y], vals[x]
        return True

    def _cancel(self, rng, vals):
        """A second operand that nearly cancels the first: its negation (for a sum) or itself
        (for a difference), a few units away; for a product, a second limb whose cross term
        nearly cancels the other's (x0 y1 against x1 y0)."""
        fmt = self.fmt
        ab = self._two_values(rng)
        if ab is None or self.op is None:
            return False
        a, b = ab
        if self.op == "*":
            if self.roles[a] != "x2" or self.roles[b] != "x2" or not vals[a][0] or not vals[b][0]:
                return False
            t = _round(fmt, -(vals[a][1] * vals[b][0]) // vals[a][0])
            if t is None:
                return False
            vals[b] = [vals[b][0], t]
            return True
        s = 1 if self.op == "-" else -1
        src = vals[a]
        out = []
        for i in range(self.limbs[b]):
            t = s * src[i] if i < len(src) else 0
            for _ in range(rng.below(3) if i == 0 or rng.bits(1) else 0):
                n = F.succ(fmt, t) if rng.bits(1) else F.pred(fmt, t)
                t = n if type(n) is int else t
            out.append(t)
        vals[b] = out
        return True

    def _align(self, rng, vals):
        """A second operand moved to an exponent near the first's."""
        fmt = self.fmt
        ab = self._two_values(rng)
        if ab is None:
            return False
        a, b = ab
        if not vals[a][0] or not vals[b][0]:
            return False
        p = fmt.p
        d = fmt.binade(vals[a][0]) - fmt.binade(vals[b][0]) + (
            rng.between(-3, 3) if rng.chance(3, 4) else rng.between(-2 * p - 2, 2 * p + 2))
        vals[b] = [_scale(fmt, t, d) for t in vals[b]]
        return all(t is not None for t in vals[b])

    def _tie(self, rng, vals):
        """A limb set to an odd multiple of half an ulp of another, so that their sum is a tie."""
        fmt = self.fmt
        slots = [(n, i) for n in self.values for i in range(len(vals[n]))]
        refs = [s for s in slots if F.ulp(fmt, vals[s[0]][s[1]]) >= 2]
        if not refs or len(slots) < 2:
            return False
        r = refs[rng.below(len(refs))]
        t = slots[rng.below(len(slots))]
        if t == r:
            return False
        h = F.ulp(fmt, vals[r[0]][r[1]]) >> 1
        v = rng.sign() * (2 * rng.below(4) + 1) * h
        vals[t[0]][t[1]] = v if F.is_member(fmt, v) else rng.sign() * h
        return True

    def _scale_case(self, rng, vals):
        """The case scaled toward a target exponent: near the underflow threshold, near the
        overflow threshold, just above the normal range, or anywhere. For a sum every operand
        (and radius) moves; for a product one factor (or the power of two)."""
        fmt = self.fmt
        p = fmt.p
        vs = [n for n in self.values if vals[n][0]]
        if not vs:
            return False
        k = rng.below(4)
        if k == 0:
            target = rng.between(fmt.qmin - 1, fmt.emin_normal + 2 * p)
        elif k == 1:
            target = rng.between(fmt.emax - 2, fmt.emax)
        elif k == 2:
            target = rng.between(fmt.emin_normal, fmt.emin_normal + 3 * p)
        else:
            target = rng.between(fmt.qmin, fmt.emax)
        pw = [n for n in self.names if self.roles[n] == "pow2"]
        if self.op == "*" or pw:
            factors = vs + pw
            cur = sum(fmt.binade(vals[n][0]) for n in factors)
            n = factors[rng.below(len(factors))]
            move = [n] + [r for r, c in self.center_of.items() if c == n]
        else:
            cur = max(fmt.binade(vals[n][0]) for n in vs)
            move = vs + [n for n in self.names if self.roles[n] == "radius"]
        d = target - cur
        for n in move:
            if self.roles[n] == "pow2":
                vals[n] = [_pow2(fmt, fmt.binade(vals[n][0]) + d)]
            else:
                vals[n] = [_scale(fmt, t, d) for t in vals[n]]
                if any(t is None for t in vals[n]):
                    return False
        return True


# ---------------------------------------------------------------------------
# The verdict on one line

class Objective:
    __slots__ = ("entry", "label", "kind", "what", "sign")

    def __init__(self, entry, label, kind, what, sign):
        self.entry = entry
        self.label = label
        self.kind = kind
        self.what = what
        self.sign = sign            # +1: larger is closer to the claim; -1: smaller is

    def better(self, a, b):
        return a > b if self.sign > 0 else a < b

    def describe(self, p):
        return {"ratio": "largest error/allowed",
                "c": "largest observed c (where u^k rho >= 2^%d eta)" % p,
                "excess": "largest excess in gaps",
                "slack": "smallest slack in gaps of the radius",
                "stated": "smallest excess over the stated value, in gaps"}[self.what]


def _frac(r):
    n, d = r
    return HUGE if d == 0 else Fraction(n, d)


class Judge:
    """The oracle's checker on one completed line at a time: its verdict, the keys of the
    entries it failed, and the quantities of the objectives."""

    def __init__(self, claims, kernel, fmt, fail_on_suspicious=False):
        self.ck = C.Checker(claims, False, 3)
        self.kernel = kernel
        self.fmt = fmt
        pl = self.ck.plan(kernel.name, fmt.name)
        if pl is None:
            raise SearchError("%s %s: %s" % (kernel.name, fmt.name, "; ".join(
                self.ck.summary.claims_errors) or "the claims cannot be read"))
        if not pl.in_scope:
            raise SearchError("%s: %s is below its min_precision %d" % (
                kernel.name, fmt.name, kernel.min_precision))
        self.entries = [(e.label, e.kind) for e in kernel.ensures]
        if pl.ext is not None:
            self.entries += [(label, kind) for label, kind, _ in pl.ext.extra]
        self.n_own = len(kernel.ensures)
        self.objectives = []
        for i, (label, kind) in enumerate(self.entries):
            if kind == "error":
                self.objectives.append(Objective(i, label, kind, "ratio", 1))
                self.objectives.append(Objective(i, label, kind, "c", 1))
            elif kind == "upper" and i < self.n_own and kernel.ensures[i].cond is not None:
                # An upper bound with a value of its own (the bounds of the folds' stage): how
                # close the output comes to its stated value, in gaps (below zero: under it).
                self.objectives.append(Objective(i, label, kind, "stated", -1))
            elif kind == "upper":
                self.objectives.append(Objective(i, label, kind, "excess", 1))
            elif kind == "encloses":
                self.objectives.append(Objective(i, label, kind, "slack", -1))
        self.fail_on_suspicious = fail_on_suspicious

    def judge(self, line):
        ck = self.ck
        ck.summary = C.Summary(3)
        ck.line(line)
        (st,) = ck.summary.keys.values()
        return Verdict(self, st, line)


class Verdict:
    __slots__ = ("line", "failed", "invalid", "judged", "why", "keys", "scores")

    def __init__(self, judge, st, line):
        c = st.c
        self.line = line
        self.invalid = c["invalid"] > 0
        self.judged = c["judged"] > 0
        susp = c["suspicious"] > 0 and judge.fail_on_suspicious
        self.failed = c["failed"] > 0 or susp
        why = [w for _, w in st.examples["failure"]]
        if susp:
            why += ["suspicious: " + w for _, w in st.examples["suspicious"]]
        if self.invalid:
            why += ["invalid: " + w for _, w in st.examples["invalid"]]
        self.why = "; ".join(why)
        self.keys = failure_keys(judge, st, susp) if self.failed else []
        p = judge.fmt.p
        self.scores = []
        for o in judge.objectives:
            es = st.entries[o.entry] if st.entries else None
            s = None
            if es is not None:
                if o.what == "ratio":
                    s = None if es.max_ratio is None else _frac(es.max_ratio)
                elif o.what == "c":
                    a = es.observed_a(p)
                    s = None if a is None else _frac(a[0])
                elif o.what == "excess":
                    m = es.maxima.get("excess in gaps")
                    s = None if m is None else _frac(m[0])
                elif o.what == "stated":
                    m = es.minima.get("excess over a positive stated value, in gaps of the output")
                    s = None if m is None else _frac(m[0])
                else:
                    m = es.minima.get("slack in gaps of the radius")
                    s = None if m is None else _frac(m[0])
            self.scores.append(s)


def failure_keys(judge, st, susp=False):
    """What a failing line failed, as stable keys: the label of each `ensures` entry that failed,
    with the statement (F1 to F5, B1 to B4, ...) in the extended domain; the reason of a failure
    that belongs to no entry (an output that is not a number of the format, ...); `suspicious`.
    An `extends` entry that failed only F2 because an entry of its core failed is named by that
    entry, the more precise of the two."""
    keys = []
    ents = st.entries
    core_failed = any(es.failures for es in ents[judge.n_own:])
    for es in ents:
        if not es.failures:
            continue
        stmts = sorted(k[len("failed"):].lstrip(": ") for k in es.counts if k.startswith("failed"))
        if es.kind == "extends" and stmts == ["F2"] and core_failed:
            continue
        if stmts:
            keys.extend("%s [%s]" % (es.label, s) for s in stmts)
        else:
            keys.append(es.label)
    if st.c["failed"] and not any(es.failures for es in ents):
        keys.extend("line: %s" % r for r in sorted(st.reasons) if not r.startswith("invalid"))
    if susp:
        keys.append("suspicious")
    return keys


# ---------------------------------------------------------------------------
# Runners

class Runner:
    """A runner of the line protocol: the generator's interpreter (`interp`, the default), the
    oracle's reference runner in this process (`refrun` or `refrun:VARIANT`), or any shell
    command. One process per batch of requests."""

    def __init__(self, spec=None, radius="first", center_claims=None):
        self.spec = spec or "interp"
        self.ref = None
        self.argv = None
        self.shell = None
        if self.spec == "interp":
            self.argv = [sys.executable, INTERP, "interp"]
            self.text = "python3 gen/kairn-gen interp"
        elif self.spec == "refrun" or self.spec.startswith("refrun:"):
            from . import refrun
            variant = self.spec.split(":", 1)[1] if ":" in self.spec else "correct"
            self.ref = refrun.Runner(variant, center_claims, radius)
            self.text = "python3 oracle/kairn-oracle refrun --variant %s%s" % (
                variant, " --radius second" if radius == "second" else "")
        elif os.path.isfile(self.spec):
            # An executable named by its path, which may hold spaces: no shell.
            self.argv = [self.spec]
            self.text = self.spec
        else:
            self.shell = self.spec
            self.text = self.spec
        self.calls = 0

    def run(self, requests):
        """The completed lines of the requests, in their order. Comment lines are dropped; a
        runner that fails, or drops, adds or reorders lines, raises RunnerError."""
        self.calls += 1
        if self.ref is not None:
            out = []
            try:
                for r in requests:
                    out.extend(ln for ln in self.ref.complete(r) if ln and ln[0] != "#")
            except ValueError as ex:
                raise RunnerError("the reference runner: %s" % ex)
        else:
            data = ("\n".join(requests) + "\n").encode("utf-8")
            try:
                proc = subprocess.run(self.argv or self.shell, shell=self.argv is None, input=data,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError as ex:
                raise RunnerError("cannot run %s: %s" % (self.text, ex))
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", "replace").strip().splitlines()
                raise RunnerError("%s exited with %d%s" % (self.text, proc.returncode,
                                                           ": " + err[-1] if err else ""))
            out = [ln for ln in proc.stdout.decode("utf-8", "replace").splitlines()
                   if ln and ln[0] != "#"]
        if len(out) != len(requests) or any(o.partition(" -> ")[0] != r
                                            for o, r in zip(out, requests)):
            raise RunnerError("%s returned %d lines for %d requests, or not in their order"
                              % (self.text, len(out), len(requests)))
        return out


def check_command(claims_path):
    cmd = "python3 oracle/kairn-oracle check"
    if claims_path and os.path.abspath(claims_path) != os.path.join(REPO_DIR, "gen", "claims.json"):
        cmd += " --claims %s" % claims_path
    return cmd


def reproduce(line, runner, claims_path, suspicious=False):
    """The command that reruns one request line through the runner and the oracle."""
    req = line.partition(" -> ")[0]
    return "echo '%s' | %s | %s%s" % (req, runner.text, check_command(claims_path),
                                      " --fail-on-suspicious" if suspicious else "")


# ---------------------------------------------------------------------------
# Seeds

_SEED_CACHE = {}


def default_seed_files():
    """The attaining lines of the brute-force summaries stored in the repository, and the
    regression cases."""
    out = sorted(glob.glob(os.path.join(REPO_DIR, "results", "*", "brute", "*.json")))
    out += sorted(glob.glob(os.path.join(REPO_DIR, "results", "*", "brute", "supplementary",
                                         "*.json")))
    if os.path.exists(REGRESSION):
        out.append(REGRESSION)
    return out


def seed_lines(path):
    """Every case line in a file: a text file of lines, or a JSON summary (of check, brute or
    tests/brute/brute.py), whose strings that look like lines are taken."""
    lines = _SEED_CACHE.get(path)
    if lines is not None:
        return lines
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    lines = []
    try:
        data = json.loads(text)
    except ValueError:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    else:
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                stack.extend(x.values())
            elif isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, str) and " -> " in x and x.count(" ") > 2:
                lines.append(x)
        lines.sort()
    _SEED_CACHE[path] = lines
    return lines


# ---------------------------------------------------------------------------
# The search

class Candidate:
    __slots__ = ("vals", "negz", "key", "origin")

    def __init__(self, problem, vals, negz, origin):
        self.vals = vals
        self.negz = frozenset(negz)
        self.key = problem.text(vals, self.negz)
        self.origin = origin


class Elite:
    __slots__ = ("score", "cand", "line")

    def __init__(self, score, cand, line):
        self.score = score
        self.cand = cand
        self.line = line


class Search:
    def __init__(self, claims, kernel, fmt, runner, seed="0", evals=20000, batch=256, elite=16,
                 seed_files=(), literature=True, per_stratum=8, fail_on_suspicious=False):
        self.problem = Problem(kernel, fmt)
        self.judge = Judge(claims, kernel, fmt, fail_on_suspicious)
        self.claims_path = claims.path
        self.kernel = kernel
        self.fmt = fmt
        self.runner = runner
        self.seed = seed
        self.budget = evals
        self.batch = batch
        self.elite = elite
        self.seed_files = list(seed_files)
        self.literature = literature
        self.per_stratum = per_stratum
        self.key = hashlib.blake2b(("kairn-oracle/search|%s|%s|%s" % (seed, kernel.name, fmt.name))
                                   .encode(), digest_size=32).digest()
        n = len(self.judge.objectives)
        self.elites = [[] for _ in range(n)]
        self.best = [None] * n          # Elite of the best case, over the whole search
        self.best_seed = [None] * n     # and over the seeds alone
        self.seen = set()
        self.evals = 0
        self.generations = 0
        self.failures = []              # the first three failing lines
        self.n_failures = 0             # and how many lines failed (the search stops at the
        self.seconds = 0.0              # end of the batch where the first did)
        self.n_seeds = 0

    def initial(self):
        pr = self.problem
        out = []
        for path in self.seed_files:
            name = os.path.relpath(path, REPO_DIR) if path.startswith(REPO_DIR) else path
            for ln in seed_lines(path):
                c = pr.parse(ln)
                if c is not None:
                    out.append(Candidate(pr, c[0], c[1], "a line of %s: %s" % (
                        name, ln.partition(" -> ")[0])))
        if self.literature:
            for name, ops in tight.cases(self.kernel.name, self.fmt):
                out.append(Candidate(pr, dict(zip(pr.names, ops)), (), "literature: %s" % name))
        rng = G.CaseRandom(self.key, 0)
        for s in pr.strata:
            for i in range(self.per_stratum):
                c = pr.random_case(rng, s)
                if c is not None:
                    out.append(Candidate(pr, c[0], c[1], "stratum %s, case %d" % (s, i)))
        uniq = []
        for c in out:
            if c.key not in self.seen:
                self.seen.add(c.key)
                uniq.append(c)
        return uniq

    def child(self, rng):
        pr = self.problem
        live = [el for el in self.elites if el]
        if not live or rng.chance(1, 16):
            c = pr.random_case(rng)
            return None if c is None else Candidate(
                pr, c[0], c[1], "stratum, generation %d" % self.generations)
        el = live[rng.below(len(live))]
        par = el[min(rng.below(len(el)), rng.below(len(el)))].cand
        vals = {n: list(v) for n, v in par.vals.items()}
        negz = set(par.negz)
        if rng.chance(1, 8):
            el2 = live[rng.below(len(live))]
            pr.crossover(rng, vals, negz, el2[rng.below(len(el2))].cand)
        for _ in range(1 + rng.chance(1, 2) + rng.chance(1, 4)):
            ok = pr.operand_move(rng, vals, negz) if rng.chance(3, 5) else \
                pr.case_move(rng, vals, negz)
            if not ok:
                return None
        r = pr.repair(vals, negz)
        if r is None:
            return None
        origin = par.origin
        if not origin.startswith("search"):
            origin = "search from %s" % origin
        return Candidate(pr, r[0], r[1], origin)

    def offer(self, j, score, cand, line, seed):
        o = self.judge.objectives[j]
        e = Elite(score, cand, line)
        if self.best[j] is None or o.better(score, self.best[j].score):
            self.best[j] = e
        if seed and (self.best_seed[j] is None or o.better(score, self.best_seed[j].score)):
            self.best_seed[j] = e
        el = self.elites[j]
        if len(el) >= self.elite and not o.better(score, el[-1].score):
            return
        if any(x.cand.key == cand.key for x in el):
            return
        # At most a quarter of an elite descends from one seed, so that the descendants of the
        # best seed do not crowd out every other start.
        kin = [x for x in el if x.cand.origin == cand.origin]
        if len(kin) >= max(1, self.elite // 4):
            if not o.better(score, kin[-1].score):
                return
            el.remove(kin[-1])
        el.append(e)
        # Best first; ties in the order they came.
        el.sort(key=lambda x: -x.score if o.sign > 0 else x.score)
        del el[self.elite:]

    def evaluate(self, cands, seed=False):
        pr = self.problem
        for i in range(0, len(cands), self.batch):
            part = cands[i:i + self.batch]
            reqs = [pr.text(c.vals, c.negz, "search:%d" % (self.evals + k))
                    for k, c in enumerate(part)]
            done = self.runner.run(reqs)
            for c, line in zip(part, done):
                self.evals += 1
                v = self.judge.judge(line)
                if v.invalid:
                    raise SearchError("the search wrote a case outside the requirements: %s (%s)"
                                      % (line, v.why))
                if v.failed:
                    self.n_failures += 1
                    if len(self.failures) < 3:
                        self.failures.append({"line": line, "why": v.why, "keys": v.keys,
                                              "origin": c.origin})
                for j, s in enumerate(v.scores):
                    if s is not None:
                        self.offer(j, s, c, line, seed)
            if self.failures:
                return

    def run(self):
        t0 = time.time()
        init = self.initial()
        self.n_seeds = len(init)
        self.evaluate(init, seed=True)
        while not self.failures and self.evals < self.budget:
            self.generations += 1
            rng = G.CaseRandom(self.key, self.generations)
            want = min(self.batch, self.budget - self.evals)
            kids = []
            tries = 0
            while len(kids) < want and tries < 20 * want:
                tries += 1
                c = self.child(rng)
                if c is not None and c.key not in self.seen:
                    self.seen.add(c.key)
                    kids.append(c)
            if not kids:
                break
            self.evaluate(kids)
        self.seconds = time.time() - t0
        return self

    def result(self):
        objs = []
        for o, b, s in zip(self.judge.objectives, self.best, self.best_seed):
            objs.append({
                "entry": o.label, "kind": o.kind, "what": o.what,
                "best": None if b is None else [str(b.score.numerator), str(b.score.denominator)],
                "line": None if b is None else b.line,
                "origin": None if b is None else b.cand.origin,
                "seed_best": None if s is None else [str(s.score.numerator),
                                                     str(s.score.denominator)],
                "seed_line": None if s is None else s.line,
                "seed_origin": None if s is None else s.cand.origin})
        return {"kernel": self.kernel.name, "format": self.fmt.name, "runner": self.runner.text,
                "seed": self.seed, "budget": self.budget, "evals": self.evals,
                "seeds": self.n_seeds, "generations": self.generations,
                "seconds": round(self.seconds, 2), "objectives": objs,
                "failures": self.failures, "failed_lines": self.n_failures,
                "reproduce": [reproduce(f["line"], self.runner, self.claims_path,
                                        self.judge.fail_on_suspicious) for f in self.failures]}


# ---------------------------------------------------------------------------
# Command line

def searched_kernels(claims):
    """The kernels with a quantity to search: an error, upper or encloses entry, or an extends
    entry (whose core has error entries)."""
    out = []
    for name, k in claims.kernels.items():
        kinds = {e.kind for e in k.ensures}
        if kinds & set(SEARCHED) or "extends" in kinds:
            out.append(name)
    return sorted(out)


def dec(r):
    """A fraction for reading: close to 1 from below, as 1 - eps."""
    if r is None:
        return "-"
    if r == HUGE:
        return "infinite"
    if 0 < 1 - r < Fraction(1, 10**6):
        return "1 - %s" % C.frac_dec(((1 - r).numerator, (1 - r).denominator), 3)
    return C.frac_dec((r.numerator, r.denominator), 10)


def _one(task):
    try:
        claims = load_claims(task["claims"])
        kernel = claims.get(task["kernel"])
        if kernel is None:
            return {"kernel": task["kernel"], "format": task["format"], "error": claims.broken.get(
                task["kernel"], "no claims for kernel %r" % task["kernel"])}
        runner = Runner(task["runner"], task["radius"], task.get("center_claims"))
        s = Search(claims, kernel, F.parse_format(task["format"]), runner, task["seed"],
                   task["evals"], task["batch"], task["elite"], task["seed_files"],
                   task["literature"], fail_on_suspicious=task["fail_on_suspicious"])
        return s.run().result()
    except (SearchError, RunnerError, F.FormatError, ClaimsError, G.GenError) as ex:
        return {"kernel": task["kernel"], "format": task["format"], "error": str(ex)}


def print_result(r, out=sys.stdout):
    w = lambda s="": print(s, file=out)
    if r.get("error"):
        w("== %s %s: ERROR %s" % (r["kernel"], r["format"], r["error"]))
        return
    w("== %s %s: %d cases (%d seeds, %d generations) in %.1f s; runner %s" % (
        r["kernel"], r["format"], r["evals"], r["seeds"], r["generations"], r["seconds"],
        r["runner"]))
    p = F.parse_format(r["format"]).p
    label = None
    for o in r["objectives"]:
        if o["entry"] != label:
            label = o["entry"]
            w("  %s" % label)
        ob = Objective(0, o["entry"], o["kind"], o["what"], 1)
        frac = lambda v: None if v is None else Fraction(int(v[0]), int(v[1]))
        b, s = frac(o["best"]), frac(o["seed_best"])
        if b is None:
            w("    %s: no case" % ob.describe(p))
            continue
        w("    %s: %s (best seed: %s)" % (ob.describe(p), dec(b), dec(s)))
        w("      %s" % o["line"])
        w("      from: %s" % o["origin"])
    if r["failures"]:
        w("  FAILED: %d lines of the last batch fail; the first %d:" % (
            r["failed_lines"], len(r["failures"])))
    for f, cmd in zip(r["failures"], r["reproduce"]):
        w("  FAILURE: %s" % f["why"])
        w("    %s" % f["line"])
        w("    failed: %s" % "; ".join(f["keys"]))
        w("    from: %s" % f["origin"])
        w("    to run it again: %s" % cmd)
        w("    to shrink it: python3 oracle/kairn-oracle shrink '%s' --runner '%s'" % (
            f["line"].partition(" -> ")[0], r["runner"]))


def main(a):
    claims_path = a.claims or os.path.join(REPO_DIR, "gen", "claims.json")
    try:
        claims = load_claims(claims_path)
    except ClaimsError as ex:
        print("kairn-oracle search: %s" % ex, file=sys.stderr)
        return 2
    kernels = searched_kernels(claims) if a.kernels == "all" else a.kernels.split(",")
    formats = a.formats.split(",")
    for k in kernels:
        if claims.get(k) is None:
            print("kairn-oracle search: %s" % claims.broken.get(k, "no claims for %r" % k),
                  file=sys.stderr)
            return 2
    for f in formats:
        try:
            F.parse_format(f)
        except F.FormatError as ex:
            print("kairn-oracle search: %s" % ex, file=sys.stderr)
            return 2
    seed_files = [] if a.no_default_seeds else default_seed_files()
    seed_files += a.seeds or []
    allowed = set(a.suspicious_ok.split(",")) if a.suspicious_ok else set()
    tasks = [{"claims": claims_path, "kernel": k, "format": f, "runner": a.runner,
              "radius": a.radius, "seed": a.seed, "evals": a.evals, "batch": a.batch,
              "elite": a.elite, "seed_files": seed_files, "literature": not a.no_literature,
              "fail_on_suspicious": a.fail_on_suspicious and k not in allowed}
             for k in kernels for f in formats]
    t0 = time.time()
    if a.jobs > 1 and len(tasks) > 1:
        with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
            results = list(ex.map(_one, tasks))
    else:
        results = [_one(t) for t in tasks]
    bad = 0
    for r in results:
        failed = bool(r.get("error") or r.get("failures"))
        if not a.quiet or failed:
            print_result(r)
        if failed:
            bad = 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"kairn_oracle_search": 1, "claims": claims_path, "results": results}, fh,
                      indent=1)
            fh.write("\n")
    n = sum(r.get("evals", 0) for r in results)
    fails = sum(r.get("failed_lines", 0) for r in results)
    errors = sum(1 for r in results if r.get("error"))
    print("kairn-oracle search: %s: %d kernel and format pairs, %d cases in %.1f s; %d failing "
          "lines%s"
          % ("FAIL" if bad else "PASS", len(results), n, time.time() - t0, fails,
             ", %d errors" % errors if errors else ""))
    return bad
