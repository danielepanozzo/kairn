"""Judging completed lines against claims.

Every verdict is decided with Python integers: limbs are fixed values (multiples of
eta, see fmt.py), the exact value of a sum lives at scale eta and the exact value of a
product at scale eta^2, and bounds are compared after clearing denominators.
"""

import json
import math
import re
import sys
from fractions import Fraction

from . import bvec as BV
from . import cexpr as CX
from . import directed as D
from . import expr as EX
from . import extended as XT
from . import fmt as F
from . import folds as FO
from . import intervals as IV
from . import rational as RAT
from .claims import ClaimsError, ew_condition_text, format_u_eta

SUMMARY_VERSION = 1
MASK_TEXT = {"0": 0, "1": 1}


def _gt(a, b):
    """a > b for fractions given as (num, den) with den >= 0 (den = 0 is infinity)."""
    an, ad = a
    bn, bd = b
    if an > 0 and bn > 0 and ad and bd:
        # The bit length of a product of positive integers is the sum of their bit lengths
        # or one less, which settles most comparisons without multiplying.
        la = an.bit_length() + bd.bit_length()
        lb = bn.bit_length() + ad.bit_length()
        if la < lb - 1:
            return False
        if la > lb + 1:
            return True
    return an * bd > bn * ad


def _relation(a, rel, b):
    """The truth of a REL b, REL one of lt, le, eq: the masks of the predicates and `holds`."""
    return a < b if rel == "lt" else a <= b if rel == "le" else a == b


def _reduce(num, den):
    g = math.gcd(num, den)
    return (num // g, den // g) if g > 1 else (num, den)


def frac_str(r):
    if r is None:
        return "-"
    n, d = r
    return str(n) if d == 1 else "%d/%d" % (n, d)


def frac_dec(r, digits=6):
    """A decimal approximation for display, computed with integers (any Python 3)."""
    if r is None:
        return "-"
    n, d = r
    if d == 0:
        return "inf"
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    e = len(str(n // d)) - 1 if n >= d else -len(str(d // n))
    while True:
        sh = digits - 1 - e
        num, den = (n * 10 ** sh, d) if sh >= 0 else (n, d * 10 ** -sh)
        q, rem = divmod(num, den)
        if q >= 10 ** digits:
            e += 1
        elif q < 10 ** (digits - 1):
            e -= 1
        else:
            if 2 * rem >= den:
                q += 1
            if q == 10 ** digits:
                q //= 10
                e += 1
            break
    s = str(q).rstrip("0") or "0"
    if -5 <= e < digits:
        if e >= 0:
            ip, fp = s[:e + 1].ljust(e + 1, "0"), s[e + 1:]
        else:
            ip, fp = "0", "0" * (-e - 1) + s
        return sign + ip + ("." + fp if fp else "")
    return "%s%s%se%+03d" % (sign, s[0], "." + s[1:] if len(s) > 1 else "", e)


def _case(line):
    """A case as stored: the line, or the text of an object that stands for one (a written
    element of a map, maps.ElementLine), made only when it is stored."""
    return line if line is None or type(line) is str else str(line)


def _ranges(ds):
    """The integers of ds as their runs in increasing order: an integer alone, or the inclusive
    range [lo, hi] of two or more."""
    runs = []
    for d in sorted(ds):
        if runs and runs[-1][1] == d - 1:
            runs[-1][1] = d
        else:
            runs.append([d, d])
    return [lo if lo == hi else [lo, hi] for lo, hi in runs]


class EntryStats:
    __slots__ = ("label", "kind", "applicable", "failures", "max_ratio", "max_ratio_case",
                 "profile", "b_max", "b_case", "bound_source", "counts", "maxima", "minima")

    def __init__(self, label, kind):
        self.label = label
        self.kind = kind
        self.applicable = 0
        self.failures = 0
        self.max_ratio = None          # largest |error| / allowed, as (num, den)
        self.max_ratio_case = None
        # Observed constant (a) by distance from underflow: D = floor(log2(u^k rho / eta))
        # maps to the largest |error| / (u^k rho) among cases at that distance, with its case; or
        # to None, in a summary read back, for a distance that was not a record (to_json).
        self.profile = {}
        self.b_max = None              # largest (|error| - rel*rho) / eta
        self.b_case = None
        self.bound_source = None
        # The kinds of the second wave: outcome and histogram counts by name, and named
        # extreme fractions with the line that attains them.
        self.counts = {}
        self.maxima = {}
        self.minima = {}

    def count(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1

    def track_max(self, name, r, line):
        cur = self.maxima.get(name)
        if cur is None or _gt(r, cur[0]):
            self.maxima[name] = (_reduce(*r), _case(line))

    def track_min(self, name, r, line):
        cur = self.minima.get(name)
        if cur is None or _gt(cur[0], r):
            self.minima[name] = (_reduce(*r), _case(line))

    def merge(self, o):
        self.applicable += o.applicable
        self.failures += o.failures
        if o.max_ratio is not None and (self.max_ratio is None or _gt(o.max_ratio, self.max_ratio)):
            self.max_ratio, self.max_ratio_case = o.max_ratio, o.max_ratio_case
        # A distance keeps its place in the order of first appearance, which decides between
        # equal ratios in observed_a, whether it comes with its ratio or without (None).
        for d, v in o.profile.items():
            cur = self.profile.get(d)
            if v is None:
                self.profile.setdefault(d, None)
            elif cur is None or _gt(v[0], cur[0]):
                self.profile[d] = v
        if o.b_max is not None and (self.b_max is None or _gt(o.b_max, self.b_max)):
            self.b_max, self.b_case = o.b_max, o.b_case
        self.bound_source = self.bound_source or o.bound_source
        for k, n in o.counts.items():
            self.counts[k] = self.counts.get(k, 0) + n
        for k, (r, case) in o.maxima.items():
            self.track_max(k, r, case)
        for k, (r, case) in o.minima.items():
            self.track_min(k, r, case)

    def observed_a(self, far):
        best = None
        for d, v in self.profile.items():
            if v is not None and d >= far and (best is None or _gt(v[0], best[0])):
                best = v
        return best

    def profile_records(self):
        """The distances of the profile whose ratio is at least every ratio at a larger
        distance, with their ratios and cases, in increasing order.  The largest ratio over the
        distances D >= F, and the first of its cases in increasing D, is a record's for every F,
        and the records of a merge are those of the merge of the records: a summary keeps these
        (to_json), at most one per distance whatever the number of lines."""
        out = []
        best = None
        for d, v in sorted(((d, v) for d, v in self.profile.items() if v is not None),
                           reverse=True):
            if best is None or not _gt(best, v[0]):
                out.append((d, v))
                best = v[0]
        out.reverse()
        return out

    def to_json(self):
        enc = lambda r: None if r is None else [str(r[0]), str(r[1])]
        return {"label": self.label, "kind": self.kind, "applicable": self.applicable,
                "failures": self.failures, "max_ratio": enc(self.max_ratio),
                "max_ratio_case": self.max_ratio_case,
                "profile": {str(d): [enc(r), c] for d, (r, c) in self.profile_records()},
                "profile_distances": _ranges(self.profile),
                "b_max": enc(self.b_max), "b_case": self.b_case,
                "bound_source": self.bound_source,
                "counts": dict(sorted(self.counts.items())),
                "maxima": {k: [enc(r), c] for k, (r, c) in sorted(self.maxima.items())},
                "minima": {k: [enc(r), c] for k, (r, c) in sorted(self.minima.items())}}

    @classmethod
    def from_json(cls, j):
        dec = lambda r: None if r is None else (int(r[0]), int(r[1]))
        s = cls(j["label"], j["kind"])
        s.applicable = j["applicable"]
        s.failures = j["failures"]
        s.max_ratio = dec(j["max_ratio"])
        s.max_ratio_case = j["max_ratio_case"]
        rec = {int(d): (dec(v[0]), v[1]) for d, v in j["profile"].items()}
        present = set(rec)
        for run in j.get("profile_distances", []):
            lo, hi = (run, run) if type(run) is int else run
            present.update(range(lo, hi + 1))
        s.profile = {d: rec.get(d) for d in sorted(present)}
        s.b_max = dec(j["b_max"])
        s.b_case = j["b_case"]
        s.bound_source = j.get("bound_source")
        s.counts = dict(j.get("counts", {}))
        s.maxima = {k: (dec(v[0]), v[1]) for k, v in j.get("maxima", {}).items()}
        s.minima = {k: (dec(v[0]), v[1]) for k, v in j.get("minima", {}).items()}
        return s


COUNTERS = ("cases", "judged", "passed", "failed", "invalid", "out_of_scope", "nonfinite",
            "nonfinite_tail", "suspicious", "beyond")


class KeyStats:
    def __init__(self, p=None):
        self.p = p
        self.c = dict.fromkeys(COUNTERS, 0)
        self.reasons = {}      # failure and invalid reasons -> count
        self.entries = []
        self.examples = {"failure": [], "invalid": [], "suspicious": []}

    def reason(self, r):
        self.reasons[r] = self.reasons.get(r, 0) + 1

    def example(self, kind, line, why, limit):
        lst = self.examples[kind]
        if len(lst) < limit:
            lst.append([line, why])

    def merge(self, o, limit):
        for k in COUNTERS:
            self.c[k] += o.c[k]
        for r, n in o.reasons.items():
            self.reasons[r] = self.reasons.get(r, 0) + n
        if not self.entries:
            self.entries = [EntryStats(e.label, e.kind) for e in o.entries]
        if len(self.entries) != len(o.entries) or any(
                a.label != b.label for a, b in zip(self.entries, o.entries)):
            raise ValueError("cannot merge statistics computed from different claims")
        for a, b in zip(self.entries, o.entries):
            a.merge(b)
        for kind in self.examples:
            for ex in o.examples[kind]:
                if len(self.examples[kind]) < limit:
                    self.examples[kind].append(ex)
        self.p = self.p or o.p

    def to_json(self):
        return {"p": self.p, "counts": self.c, "reasons": self.reasons,
                "entries": [e.to_json() for e in self.entries], "examples": self.examples}

    @classmethod
    def from_json(cls, j):
        s = cls(j.get("p"))
        s.c.update(j["counts"])
        s.reasons = dict(j["reasons"])
        s.entries = [EntryStats.from_json(e) for e in j["entries"]]
        s.examples = j["examples"]
        return s


class Coverage:
    """What the generator says it wrote, from its header comments.  Kept so that a report
    never calls a run exhaustive when it was restricted or partial."""

    def __init__(self):
        self.records = {}   # descriptor tuple -> list of [start, end)

    def add(self, desc, start, end):
        self.records.setdefault(desc, []).append([start, end])

    def merge(self, o):
        for d, iv in o.records.items():
            self.records.setdefault(d, []).extend(iv)

    @staticmethod
    def union(iv):
        out = []
        for a, b in sorted(iv):
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out

    def to_json(self):
        return [{"desc": dict(d), "ranges": self.union(iv)} for d, iv in self.records.items()]

    @classmethod
    def from_json(cls, j):
        c = cls()
        for r in j:
            c.records[tuple(sorted(r["desc"].items()))] = [list(x) for x in r["ranges"]]
        return c

    def describe(self):
        lines = []
        for d, iv in sorted(self.records.items()):
            dd = dict(d)
            u = self.union(iv)
            covered = sum(b - a for a, b in u)
            head = "%s %s %s" % (dd.get("kernel"), dd.get("format"), dd.get("mode"))
            if dd.get("mode") == "exhaustive":
                total = int(dd.get("total", -1))
                restr = dd.get("restrict", "none")
                full = (u == [[0, total]])
                if full and restr == "none":
                    what = "COMPLETE: every operand combination satisfying the requirements"
                elif full:
                    what = "complete over a RESTRICTED domain (%s)" % restr
                else:
                    what = "PARTIAL: %d of %d indices (restrictions: %s)" % (covered, total, restr)
                lines.append("%s: %s; enumeration indices %s" % (head, what, _ranges_str(u)))
            else:
                lines.append("%s seed=%s strata=%s: %d cases, indices %s" % (
                    head, dd.get("seed"), dd.get("strata"), covered, _ranges_str(u)))
        return lines


def _ranges_str(u):
    s = ", ".join("[%d, %d)" % (a, b) for a, b in u[:4])
    return s + (", ..." if len(u) > 4 else "")


class Summary:
    def __init__(self, max_examples=5):
        self.keys = {}
        self.coverage = Coverage()
        self.stream_errors = []
        self.claims_path = None
        self.claims_warnings = []
        self.claims_errors = []
        self.max_examples = max_examples

    def stats(self, key, p=None):
        s = self.keys.get(key)
        if s is None:
            s = self.keys[key] = KeyStats(p)
        return s

    def merge(self, o):
        for k, s in o.keys.items():
            if k in self.keys:
                self.keys[k].merge(s, self.max_examples)
            else:
                t = KeyStats(s.p)
                t.merge(s, self.max_examples)
                self.keys[k] = t
        self.coverage.merge(o.coverage)
        self.stream_errors.extend(o.stream_errors)
        if self.claims_path is None:
            self.claims_path = o.claims_path
        for w in o.claims_warnings:
            if w not in self.claims_warnings:
                self.claims_warnings.append(w)
        for w in o.claims_errors:
            if w not in self.claims_errors:
                self.claims_errors.append(w)

    def totals(self):
        t = dict.fromkeys(COUNTERS, 0)
        for s in self.keys.values():
            for k in COUNTERS:
                t[k] += s.c[k]
        return t

    def failed(self, fail_on_suspicious=False, expect_valid=False):
        t = self.totals()
        return (t["failed"] > 0 or bool(self.stream_errors) or bool(self.claims_errors)
                or (fail_on_suspicious and t["suspicious"] > 0)
                or (expect_valid and t["invalid"] > 0))

    def to_json(self):
        return {"kairn_oracle_summary": SUMMARY_VERSION, "claims": self.claims_path,
                "claims_warnings": self.claims_warnings, "claims_errors": self.claims_errors,
                "keys": [{"kernel": k[0], "format": k[1], "tag": k[2], "stats": s.to_json()}
                         for k, s in sorted(self.keys.items())],
                "coverage": self.coverage.to_json(), "stream_errors": self.stream_errors}

    @classmethod
    def from_json(cls, j, max_examples=5):
        if j.get("kairn_oracle_summary") != SUMMARY_VERSION:
            raise ValueError("not a kairn-oracle summary (version %r)"
                             % j.get("kairn_oracle_summary"))
        s = cls(max_examples)
        s.claims_path = j.get("claims")
        s.claims_warnings = list(j.get("claims_warnings", []))
        s.claims_errors = list(j.get("claims_errors", []))
        for e in j["keys"]:
            s.keys[(e["kernel"], e["format"], e["tag"])] = KeyStats.from_json(e["stats"])
        s.coverage = Coverage.from_json(j["coverage"])
        s.stream_errors = list(j.get("stream_errors", []))
        return s


# ---------------------------------------------------------------------------

def value_terms(tree):
    """The terms of a value, for an error entry of form T: the operands of its outermost sums and
    differences (a unary minus kept with its term): s and x*y for s+x*y."""
    if tree[0] in ("+", "-"):
        return value_terms(tree[1]) + value_terms(tree[2])
    if tree[0] == "neg":
        return value_terms(tree[1])
    return [tree]


def format_has(fmt, prop):
    """format(PROPERTY): half, the format contains 1/2, eta <= 1/2."""
    if prop == "half":
        return fmt.qmin <= -1
    raise ClaimsError("unknown format property %r" % prop)


# The classes of a count m against the unit of the kernel its bound is for (the bound kernels of
# the folds' stage): x = m * unit(K), by the limits of milestone2.md, "The bound as a function of
# n" (ok is true for m eps <= 0.24 in binary64 and binary32; the statement needs m eps <= 1/2).
COUNT_LIMITS = ((Fraction(1, 5), "1/5"), (Fraction(1, 4), "1/4"), (Fraction(1, 2), "1/2"),
                (Fraction(1), "1"))


class Plan:
    """Everything about one (kernel, format) that does not depend on the operands."""

    def __init__(self, kernel, fmt, ignore_min_precision, claims=None):
        self.kernel = kernel
        self.fmt = fmt
        q = fmt.qmin
        self.in_slices, self.n_in = self._slices(kernel.inputs)
        self.out_slices, self.n_out = self._slices(kernel.outputs)
        self.in_masks = frozenset(self.in_slices[n][0] for n in kernel.input_names
                                  if n in kernel.masks)
        self.out_masks = frozenset(self.out_slices[n][0] for n, _ in kernel.outputs
                                   if n in kernel.masks)
        # The limb groups of the inputs, whose values the suspicious test bounds.
        self.groups = [self.in_slices[n] for n in kernel.input_names if n not in kernel.masks]
        limb_slots = [i for i in range(self.n_out) if i not in self.out_masks]
        self.lead = limb_slots[0] if limb_slots else None
        # The exact value is the integer value_fn(x) times 2^sv: sv is q for sums of limbs and
        # 2q for products of two (a product of three would be 3q).
        if kernel.value_tree is not None:
            src, self.sv = EX.compile_tree(kernel.value_tree, self._leaf)
            self.value_fn = EX.make_function(["x"], src)
        else:
            self.value_fn, self.sv = None, q
        self.sc = min(q, self.sv)                    # common scale for comparisons
        self.sh_out = q - self.sc
        self.sh_val = self.sv - self.sc
        self.in_scope = ignore_min_precision or fmt.p >= kernel.min_precision
        # format(half): a format that does not contain 1/2 is outside the claims, whatever the
        # precision (--ignore-min-precision does not bring it in).
        self.format_missing = [r for r in getattr(kernel, "format_requires", ())
                               if not format_has(fmt, r)]
        if self.format_missing:
            self.in_scope = False
        # count(m): m = 0 or m >= 1, and 1 as a fixed value is 2^-qmin (a format with qmin > 0
        # has no number between 0 and 1).
        self.one = (1 << -q) if q < 0 else 1
        self.conditional = getattr(kernel, "conditional", False)
        self.requires = []
        for r in kernel.requires:
            if r[0] == "abs_ge":
                self.requires.append(("abs_ge", r, self.in_slices[r[1]], self.in_slices[r[2]]))
            elif r[0] == "at_most":
                # at_most(NAME, K) (bvec.py).
                self.requires.append(BV.plan_requirement(self, r))
            else:
                self.requires.append((r[0], r[1], self.in_slices[r[1]]))
        # product_large: value = 0 or |value| >= 2^(2p-1) eta, as a fixed value at scale sv.
        self.pl_thr = 1 << max(2 * fmt.p - 1 + q - self.sv, 0)
        # limb_products_normal: every product of a limb of one factor by a limb of the other
        # (at scale 2q) is zero or at least 2^(p-1) eta = 2^(p-1-q) * 2^(2q) in magnitude.
        self.lp = None
        if kernel.limb_products is not None:
            a, b = kernel.limb_products
            self.lp = (self.in_slices[a], self.in_slices[b], fmt.p - 1 - q)
        self.entries = []
        self.rounded = []                            # indices of the rounded entries
        self.neighbors = []                          # ... of the neighbor entries
        self.bounds = []                             # ... of the bound entries
        self.uppers = [e for e in kernel.ensures if e.kind == "upper" and e.cond is None
                       and not getattr(e, "bv", False)]
        self.balls = None
        # The kernels of the bounds (every entry under a mask): unit(K) and tiny(K) of the kernels
        # their expressions name, and the count whose classes the statistics give.
        self.units = {}
        self.count_stat = None
        if self.conditional and self.in_scope:
            names = sorted({kn for e in kernel.ensures
                            for t in ([e.cvalue] if e.cvalue is not None else [])
                            + list(getattr(e, "cargs", [])) for _f, kn in CX.calls(t)})
            for kn in names:
                if claims is None:
                    raise ClaimsError("%s: unit(%s) needs the claims" % (kernel.name, kn))
                self.units[kn] = claims.unit_tiny(kn, fmt)
            counts = [r[1] for r in kernel.requires if r[0] == "count"]
            if len(counts) == 1 and len(names) == 1:
                self.count_stat = (self.in_slices[counts[0]], names[0], self.units[names[0]][0])
            self.u, self.eta = format_u_eta(fmt)
        # A value of two operands, NAME op NAME (the directed sums and products of Milestone 2):
        # the input slots of its two operands, for the classes of the extended domain.
        t = kernel.value_tree
        self.two = None
        if (t is not None and t[0] in ("+", "-", "*") and t[1][0] == "name" and t[2][0] == "name"
                and t[1][1] != t[2][1]):
            self.two = (self.in_slices[t[1][1]], self.in_slices[t[2][1]])
        for e in kernel.ensures:
            ranges = [self.out_slices[n] for n in e.of]
            c = {"kind": e.kind, "ranges": ranges, "first": ranges[0][0] if ranges else None}
            if e.kind == "error" and not self.in_scope:
                # Below the kernel's minimum precision nothing is judged, and a bound may not
                # even exist there (3/(1 - 4u) at p = 2): it is not evaluated, so that such a
                # format cannot set the kernel aside for the others.
                c["source"] = None
            elif e.kind == "error":
                rel, ab, src = kernel.bound(fmt, e)
                # The bound is rel*rho + ab; with rho and the error at scale sc it reads
                # rel*rho + ab*2^-sc in those units.
                abs_sc = ab * (Fraction(1 << -self.sc) if self.sc < 0 else Fraction(1, 1 << self.sc))
                c.update(rel_n=rel.numerator, rel_d=rel.denominator,
                         abs_n=abs_sc.numerator, abs_d=abs_sc.denominator,
                         k=e.k, kp=e.k * fmt.p, form=e.form, when=e.when, source=src)
                if e.form == "T":
                    # rho is the sum of the magnitudes of the terms of value, each at its scale
                    # (at least the value's, so at least sc).
                    terms = []
                    for t in value_terms(kernel.value_tree):
                        tsrc, ts = EX.compile_tree(t, self._leaf)
                        terms.append((EX.make_function(["x"], tsrc), ts - self.sc))
                    c["terms"] = terms
                if e.exact_when is not None:
                    c["exact"] = self._exact_conditions(e)
                if getattr(e, "exact_flag", None):
                    c.update(BV.plan_exact_flag(self, e))
            elif e.kind == "rounded":
                c["mode"] = e.mode
                c["when"] = e.when
                self.rounded.append(len(self.entries))
                if getattr(e, "own_tree", None) is not None:
                    c.update(BV.plan_rounded(self, e))
            elif e.kind == "neighbor":
                c["side"] = e.side
                self.neighbors.append(len(self.entries))
            elif e.kind == "bound":
                c.update(side=e.side, steps=e.steps)
                self.bounds.append(len(self.entries))
            elif e.kind in ("upper", "holds") and e.cond is not None:
                # Under a mask: the outputs the entry names (its own and those of its
                # expressions), which must be numbers for the entry to say anything.
                trees = [e.cvalue] if e.kind == "upper" else e.cargs
                used = {self.out_slices[n][0] for t in trees for n in CX.names(t)
                        if n in self.out_slices}
                used |= {lo for lo, _hi in ranges}
                c.update(cond=self.out_slices[e.cond][0], cond_name=e.cond, used=sorted(used),
                         trees=trees)
                if e.kind == "holds":
                    c["rel"] = e.rel
            elif e.kind == "upper" and getattr(e, "bv", False):
                # A value of its own and no mask (bvec.py).
                c.update(BV.plan_upper(self, e, claims))
            elif e.kind == "upper":
                c.update(gn=e.gaps.numerator, gd=e.gaps.denominator)
            elif e.kind == "finite_or_nan":
                c.update(flag=self.out_slices[e.flag][0], operand=self.in_slices[e.operand])
                if e.cond_in is not None or e.steps:
                    # The finishes of the folds of maxima: the mask input and the steps up.
                    c.update(cond_in=(self.in_slices[e.cond_in][0] if e.cond_in is not None
                                      else None), steps=e.steps)
                if getattr(e, "nonneg", False) or getattr(e, "if_all", None):
                    c.update(BV.plan_finish(self, e))
            elif e.kind == "maximum":
                (a, sa), (b, sb) = [EX.compile_tree(t, self._leaf) for t in e.margs]
                s = min(sa, sb, q)
                # Both arguments and the output at their common scale: integers compared.
                c["fn"] = EX.make_function(["x"], "(%s<<%d, %s<<%d)" % (a, sa - s, b, sb - s))
                c["sh_out"] = q - s
            elif e.kind == "predicate":
                (a, sa), (b, sb) = [EX.compile_tree(t, self._leaf) for t in e.args]
                s = min(sa, sb)
                # Both sides at their common scale: a comparison of integers.
                c["fn"] = EX.make_function(["x"], "(%s<<%d, %s<<%d)" % (a, sa - s, b, sb - s))
                c["rel"] = e.rel
            elif e.kind == "encloses":
                c.update(self._encloses(e))
                if e.exact_when is not None and self.in_scope:
                    c["exact"] = self._exact_conditions(e)
            if getattr(e, "iv", False):
                # The kinds of the interval kernels and the fields they add (intervals.py).
                c.update(IV.plan_entry(self, e, claims))
            self.entries.append(c)
        # In the finite domain, a kernel with an entry about an output group other than the first
        # is judged entry by entry, each where its own group's leading limb is finite.
        self.by_groups = IV.by_groups(kernel)
        # The extended domain (the non-finite layer) is judged by extended.py.
        self.ext = XT.ExtPlan(self, Plan) if kernel.extended and self.in_scope else None

    def _exact_conditions(self, e):
        """[(holds, text)] for the conditions of an exact_when list: holds(x) on finite input
        limbs is EXPR = 0 or |EXPR| > K (>= K), decided with integers: EXPR is an integer E at a
        scale s and K = n/d exactly, so |E| 2^s > n/d is |E| d 2^s > n."""
        out = []
        for j, (tree, text, op, k) in enumerate(e.exact_when):
            src, s = EX.compile_tree(tree, self._leaf)
            fn = EX.make_function(["x"], src)
            K = e.exact_threshold(self.fmt, j)
            n, d = K.numerator, K.denominator
            ls, rs = (s, 0) if s >= 0 else (0, -s)

            def holds(x, fn=fn, n=n, d=d, ls=ls, rs=rs, strict=op == "zero_or_abs_gt"):
                v = fn(x)
                if v == 0:
                    return True
                a, b = (abs(v) * d) << ls, n << rs
                return a > b if strict else a >= b
            out.append((holds, ew_condition_text(text, op, k)))
        return out

    def limb_products_normal(self, x):
        (alo, ahi), (blo, bhi), te = self.lp
        thr = 1 << te if te > 0 else 1
        for a in x[alo:ahi]:
            for b in x[blo:bhi]:
                p = abs(a * b)
                if p and p < thr:
                    return False
        return True

    def _leaf(self, name):
        if isinstance(name, tuple):
            # NAME[I], limb I of an input (the conditions of exact_when).
            n, i = name
            return "x[%d]" % (self.in_slices[n][0] + i), self.fmt.qmin
        lo, hi = self.in_slices[name]
        return "(%s)" % "+".join("x[%d]" % i for i in range(lo, hi)), self.fmt.qmin

    def _encloses(self, e):
        """The set as a function of the inputs and of one endpoint per ball, and the corners
        of the box of the balls to evaluate it at."""
        q = self.fmt.qmin
        bnames = list(e.balls)
        idx = {b: i for i, b in enumerate(bnames)}

        def leaf(name):
            if name in idx:
                return "b[%d]" % idx[name], q
            return self._leaf(name)

        src, ss = EX.compile_tree(e.set_tree, leaf)
        cs = min(q, ss)
        lo, hi = self.out_slices[e.center]
        return {"set": EX.make_function(["x", "b"], src),
                "balls": [(self.in_slices[e.balls[b][0]], self.in_slices[e.balls[b][1]][0])
                          for b in bnames],
                "corners": [[(k >> i) & 1 for i in range(len(bnames))]
                            for k in range(1 << len(bnames))],
                # Set values at scale ss and outputs at scale q are compared at scale cs.
                "sh_set": ss - cs, "sh_q": q - cs, "center": (lo, hi),
                "radius": self.out_slices[e.radius][0]}

    def set_range(self, c, x):
        """(lo, hi) of the set at the entry's comparison scale, or None when a ball is empty
        (negative radius): every corner of the box gives a candidate endpoint."""
        ends = []
        for (lo, hi), ri in c["balls"]:
            ctr = sum(x[lo:hi])
            r = x[ri]
            if r < 0:
                return None
            ends.append((ctr - r, ctr + r))
        fn = c["set"]
        vals = [fn(x, [ends[i][bit] for i, bit in enumerate(corner)]) for corner in c["corners"]]
        sh = c["sh_set"]
        return min(vals) << sh, max(vals) << sh

    @staticmethod
    def _slices(io):
        d = {}
        pos = 0
        for name, n in io:
            d[name] = (pos, pos + n)
            pos += n
        return d, pos


class Checker:
    def __init__(self, claims, ignore_min_precision=False, max_examples=5):
        self.claims = claims
        self.ignore_min_precision = ignore_min_precision
        self.summary = Summary(max_examples)
        self.summary.claims_path = claims.path
        self.summary.claims_errors = claims.errors()
        for k in list(claims.kernels.values()) + list(getattr(claims, "folds", {}).values()):
            if k.unknown_fields:
                self.summary.claims_warnings.append(
                    "%s: fields not read by the oracle: %s" % (k.name, ", ".join(k.unknown_fields)))
            self.summary.claims_warnings.extend(k.warnings)
        self.max_examples = max_examples
        self.plans = {}
        self.open_header = None     # (descriptor, expected lines, kernel, format, seen)
        # Under a generator header of rational_K, the requests it announces (rational.Echo).
        self.echo = None
        self.lineno = 0

    def plan(self, kname, fname):
        key = (kname, fname)
        pl = self.plans.get(key)
        if pl is None and key not in self.plans:
            kernel = self.claims.get(kname)
            try:
                f = F.parse_format(fname)
            except F.FormatError:
                f = None
            pl = None
            if kernel is not None and f is not None:
                try:
                    pl = Plan(kernel, f, self.ignore_min_precision, self.claims)
                except ClaimsError as ex:
                    # For example c cannot be evaluated for a format that instances omit.
                    self.claims.mark_broken(kname, str(ex))
                    if str(ex) not in self.summary.claims_errors:
                        self.summary.claims_errors.append(str(ex))
            self.plans[key] = pl
        return pl

    def stream_error(self, msg):
        self.summary.stream_errors.append("line %d: %s" % (self.lineno, msg))

    def comment(self, line):
        if not line.startswith("# kairn-oracle gen "):
            return
        fields = dict(f.split("=", 1) for f in line[len("# kairn-oracle gen "):].split()
                      if "=" in f)
        if fields.get("event") == "end":
            if self.open_header is None:
                self.stream_error("generator trailer without a header")
                return
            desc, start, end, seen = self.open_header
            want = int(fields.get("lines", -1))
            if seen != want:
                self.stream_error("the generator wrote %d lines for %s but %d completed lines "
                                  "arrived: the runner dropped or added lines"
                                  % (want, dict(desc).get("kernel"), seen))
            else:
                self.summary.coverage.add(desc, start, end)
            self.open_header = None
            self.echo = None
            return
        if self.open_header is not None:
            self.stream_error("generator header inside another generator's output (truncated?)")
        self.echo = None
        try:
            start = int(fields.pop("start"))
            count = int(fields.pop("count"))
        except (KeyError, ValueError):
            self.stream_error("malformed generator header: %s" % line)
            self.open_header = None
            return
        fields.pop("event", None)
        self.open_header = [tuple(sorted(fields.items())), start, start + count, 0]
        self.echo = RAT.Echo.for_header(self, fields, start)

    def finish(self):
        if self.open_header is not None:
            self.stream_error("stream ended before the generator's trailer: the runner stopped "
                              "early or the stream was truncated")
            self.open_header = None
            self.echo = None
        return self.summary

    def feed(self, lines):
        for line in lines:
            self.line(line)

    def line(self, raw):
        self.lineno += 1
        line = raw.rstrip("\r\n")
        if not line:
            return
        if line[0] == "#":
            self.comment(line)
            return
        if self.open_header is not None:
            self.open_header[3] += 1
        left, sep, right = line.partition(" -> ")
        if self.echo is not None:
            self.echo.check(self, left, self.open_header[3])
        lt = left.split(" ")
        kname = lt[0]
        fname = lt[1] if len(lt) > 1 else "?"
        tag = ""
        if len(lt) > 2 and lt[-1].startswith("#"):
            tag = lt[-1][1:].split(":", 1)[0]
            lt = lt[:-1]
        if kname in RAT.KERNELS:
            # kairn::rational<X>(num, den), judged for equality without claims (rational.py).
            RAT.judge_line(self, line, kname, fname, tag, lt[2:], sep, right)
            return
        if kname in self.claims.folds:
            # A fold, whose request carries arrays (folds.py).
            FO.judge_line(self, line, lt, sep, right, tag)
            return
        pl = self.plan(kname, fname)
        fmt = pl.fmt if pl else None
        st = self.summary.stats((kname, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
        if pl is not None and not st.entries:
            st.entries = [EntryStats(e.label, e.kind) for e in pl.kernel.ensures]
            for es, pe in zip(st.entries, pl.entries):
                es.bound_source = pe.get("source")
            if pl.ext is not None:
                # The entries of the core of each `extends` entry, which F2 applies.
                for label, kind, source in pl.ext.extra:
                    st.entries.append(EntryStats(label, kind))
                    st.entries[-1].bound_source = source
        st.c["cases"] += 1
        if pl is None:
            if kname in self.claims.broken:
                why = "the claims of %s cannot be read" % kname
            elif self.claims.get(kname) is None:
                why = "no claims for kernel %r" % kname
            else:
                why = "unknown format %r" % fname
            self._fail(st, line, why)
            return
        if not sep:
            self._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
            return
        ins = lt[2:]
        outs = right.split(" ")
        if len(ins) != pl.n_in or "" in ins:
            self._fail(st, line, "malformed: %d input limbs, kernel takes %d" % (len(ins), pl.n_in))
            return
        if len(outs) != pl.n_out or "" in outs:
            self._fail(st, line, "malformed: %d output limbs, kernel returns %d"
                       % (len(outs), pl.n_out))
            return
        if not pl.in_scope:
            st.c["out_of_scope"] += 1
            if pl.format_missing:
                st.reason("out of scope: the format does not have %s (format(%s))" % (
                    ", ".join(pl.format_missing), ", ".join(pl.format_missing)))
            return
        if pl.ext is not None:
            XT.judge_line(self, st, pl, line, ins, outs)
            return
        # Requirements first: a case outside them is never counted as passed.
        for i in pl.in_masks:
            if ins[i] not in MASK_TEXT:
                self._invalid(st, line, "mask input %r is not 0 or 1" % ins[i])
                return
        try:
            if pl.in_masks:
                x = [MASK_TEXT[t] if i in pl.in_masks else F.parse_limb(fmt, t)
                     for i, t in enumerate(ins)]
            else:
                x = [F.parse_limb(fmt, t) for t in ins]
        except F.LimbError as ex:
            self._invalid(st, line, "input limb malformed: %s" % ex)
            return
        for v in x:
            if type(v) is not int:
                self._invalid(st, line, "input limb not finite" if v != F.OUTSIDE
                              else "input limb not a number of the format")
                return
            if not F.is_member(fmt, v):
                self._invalid(st, line, "input limb not a number of the format")
                return
        why = self.violated(pl, x)
        if why:
            self._invalid(st, line, why)
            return
        for i in pl.out_masks:
            if outs[i] not in MASK_TEXT:
                self._fail(st, line, "mask output %r is not 0 or 1" % outs[i])
                return
        try:
            if pl.out_masks:
                z = [MASK_TEXT[t] if i in pl.out_masks else F.parse_limb(fmt, t)
                     for i, t in enumerate(outs)]
            else:
                z = [F.parse_limb(fmt, t) for t in outs]
        except F.LimbError as ex:
            self._fail(st, line, "output limb malformed: %s" % ex)
            return
        if pl.conditional:
            # Every entry holds under a mask (the bounds of the folds' stage): judged on every
            # line, by the masks (_conditional).
            self._conditional(pl, st, x, z, line)
            return
        if getattr(pl.kernel, "bv_radius", False):
            # Every entry an upper with a value of its own and no mask (bvec.py).
            BV.judge_radius(self, pl, st, x, z, line)
            return
        if getattr(pl.kernel, "acc", False):
            # A rounded entry with a value of its own: the accumulator (bvec.py).
            BV.judge_acc(self, pl, st, x, z, line)
            return
        if pl.by_groups:
            # Entries about output groups other than the first (intervals.py).
            IV.judge_by_groups(self, pl, st, x, z, line)
            return
        v = self.verdict(pl, st.entries, x, z, line)
        if v[0] == "fail":
            self._fail(st, line, v[1])
        elif v[0] == "nonfinite":
            _kind, lead, beyond, small = v
            st.c["nonfinite" if lead else "nonfinite_tail"] += 1
            if beyond:
                st.c["beyond"] += 1
            if small:
                st.c["suspicious"] += 1
                st.example("suspicious", line, "non-finite %s with operands and exact value "
                           "below Omega/4" % ("leading limb" if lead else "lower limb"),
                           self.max_examples)
        else:
            st.c["judged"] += 1
            reasons = v[1]
            if reasons:
                st.c["failed"] += 1
                for r in reasons:
                    st.reason(r)
                st.example("failure", line, "; ".join(reasons), self.max_examples)
            else:
                st.c["passed"] += 1

    def violated(self, pl, x):
        """The first requirement of a kernel of the finite domain that finite operands violate,
        or None."""
        fmt = pl.fmt
        for r in pl.requires:
            if r[0] == "normalized":
                lo, hi = r[2]
                if not F.normalized_limbs(fmt, x[lo:hi]):
                    return "requires normalized(%s)" % r[1]
            elif r[0] == "nonneg":
                lo, hi = r[2]
                if sum(x[lo:hi]) < 0:
                    return "requires nonneg(%s)" % r[1]
            elif r[0] == "power_of_two":
                lo, hi = r[2]
                v = sum(x[lo:hi])
                if v <= 0 or v & (v - 1):
                    return "requires power_of_two(%s)" % r[1]
            elif r[0] == "count":
                lo, hi = r[2]
                v = sum(x[lo:hi])
                if v != 0 and v < pl.one:
                    return "requires count(%s)" % r[1]
            elif r[0] == "at_most":
                if BV.at_most_violated(r, x):
                    return "requires at_most(%s, %d)" % (r[1], r[3])
            else:
                (alo, ahi), (blo, bhi) = r[2], r[3]
                if abs(sum(x[alo:ahi])) < abs(sum(x[blo:bhi])):
                    return "requires abs_ge(%s, %s)" % (r[1][1], r[1][2])
        return None

    def verdict(self, pl, ents, x, z, line):
        """The verdict of a kernel of the finite domain (not conditional) on operands that satisfy
        its requirements and outputs read from the line, with the statistics of its entries in
        ents: ("fail", why) for an output that is not a number of the format; ("nonfinite", lead,
        beyond, small) for a case outside the statements (a non-finite output, in its leading limb
        or a lower one only, or an exact result beyond Omega), small when it is suspicious; or
        ("judged", reasons), the reasons of the failures of the entries."""
        fmt = pl.fmt
        V = pl.value_fn(x) if pl.value_fn is not None else None
        # A rounding whose exact result in unbounded range is beyond Omega is outside the
        # statement (no operation overflows): the case counts as non-finite, as an infinite
        # output would.  So is an upper bound when the smallest one in unbounded range is.
        expected = {}
        beyond = False
        for i in pl.rounded:
            mode = pl.entries[i]["mode"]
            if pl.entries[i]["when"] == "product_large" and not (V == 0 or abs(V) >= pl.pl_thr):
                # Nothing is claimed where the condition does not hold (None: not judged), and
                # so nothing makes the case non-finite either.
                expected[i] = None
                continue
            if mode == "nearest":
                r = F.rn(fmt, V, pl.sv)
                beyond = beyond or type(r) is not int
            else:
                r = F.rdir(fmt, V, pl.sv, mode == "up")
                beyond = beyond or abs(r) > fmt.omega
            expected[i] = r
        if pl.uppers and abs(F.rdir(fmt, V, pl.sv, True)) > fmt.omega:
            beyond = True
        # neighbor: the next number of the format, which beyond +-Omega does not exist in the
        # finite domain (the case is non-finite, as an overflow is); bound: the directed rounding
        # in the format unbounded above, beyond +-Omega likewise.
        for i in pl.neighbors:
            r = D.neighbor(fmt, V, pl.entries[i]["side"] == "up")
            beyond = beyond or type(r) is not int
            expected[i] = r
        for i in pl.bounds:
            r = F.rdir(fmt, V, pl.sv, pl.entries[i]["side"] == "above")
            beyond = abs(r) > fmt.omega or beyond
            expected[i] = r
        if beyond or any(type(v) is not int for v in z):
            if any(v == F.OUTSIDE for v in z):
                return ("fail", "output limb not a number of the format")
            lead = beyond or (pl.lead is not None and type(z[pl.lead]) is not int)
            q4 = fmt.omega
            small = not beyond and all(4 * abs(v) < q4 for v in x) and all(
                4 * abs(sum(x[lo:hi])) < q4 for lo, hi in pl.groups)
            if small and V is not None:
                d = pl.sv - fmt.qmin
                small = ((4 * abs(V)) << d) < q4 if d >= 0 else 4 * abs(V) < (q4 << -d)
            for e in pl.entries:
                if small and e["kind"] == "encloses":
                    rg = pl.set_range(e, x)
                    sh = e["sh_q"]
                    small = rg is None or all(4 * abs(v) < (q4 << sh) for v in rg)
            return ("nonfinite", lead, beyond, small)
        for v in z:
            if not F.is_member(fmt, v):
                return ("fail", "output limb not a number of the format")
        return ("judged", self._judge(pl, ents, x, z, V, expected, line))

    def _judge(self, pl, ents, x, z, V, expected, line, only=None):
        """The reasons of the failures of every `ensures` entry of the plan (those listed in
        `only`), on finite operands and finite outputs, with the statistics in ents.  F2 of the
        extended domain applies it to the core of a full kernel."""
        fmt = pl.fmt
        reasons = []
        for i, e in enumerate(pl.entries):
            if only is not None and i not in only:
                continue
            es = ents[i]
            kind = e["kind"]
            if kind == "normalized":
                es.applicable += 1
                zz = []
                for lo, hi in e["ranges"]:
                    zz.extend(z[lo:hi])
                if not F.normalized_limbs(fmt, zz):
                    es.failures += 1
                    reasons.append("not normalized")
            elif kind == "leading_rounded":
                es.applicable += 1
                r = F.rn(fmt, V, pl.sv)
                if r != z[e["first"]]:
                    es.failures += 1
                    reasons.append("leading limb is not RN(value)")
            elif kind in SECOND_WAVE_KINDS:
                why = SECOND_WAVE_KINDS[kind](self, pl, e, es, x, z, V, expected.get(i), line)
                if why:
                    es.failures += 1
                    reasons.append(why)
            else:
                inexact = None
                if "exact" in e:
                    # exact_when: when every condition holds, the output is the value exactly.
                    # Read as a claim of its own, whether or not `when` holds.
                    inexact = self._exact_error(pl, e, es, x, z, V)
                    if inexact:
                        es.failures += 1
                        es.count("failed exact_when")
                        reasons.append(inexact)
                    if "exact_flag" in e:
                        # The mask that says the conditions hold (bvec.py).
                        why = BV.judge_exact_flag(self, pl, e, es, x, z)
                        if why:
                            es.failures += 1
                            reasons.append(why)
                if e["when"] == "product_large" and not (V == 0 or abs(V) >= pl.pl_thr):
                    continue
                if e["when"] == "limb_products_normal" and not pl.limb_products_normal(x):
                    continue
                es.applicable += 1
                O = 0
                for lo, hi in e["ranges"]:
                    O += sum(z[lo:hi])
                Vc = V << pl.sh_val
                Err = abs((O << pl.sh_out) - Vc)
                if e["form"] == "R":
                    rho = abs(Vc)
                elif e["form"] == "T":
                    rho = 0
                    for fn, sh in e["terms"]:
                        rho += abs(fn(x)) << sh
                else:
                    rho = 0
                    for nm, (lo, hi) in pl.in_slices.items():
                        rho += abs(sum(x[lo:hi]))
                    rho <<= pl.sh_out
                rn_, rd = e["rel_n"], e["rel_d"]
                an, ad = e["abs_n"], e["abs_d"]
                num = Err * rd * ad
                den = rn_ * rho * ad + an * rd
                if num > den:
                    if not inexact:
                        es.failures += 1
                    if "exact" in e:
                        es.count("failed bound")
                    reasons.append("error above bound (%s)" % es.label)
                # A zero bound gives the ratio 0 for an exact result and (1, 0), which
                # compares above every finite ratio, for an inexact one.
                ratio = (num, den) if den else ((0, 1) if num == 0 else (1, 0))
                if es.max_ratio is None or _gt(ratio, es.max_ratio):
                    es.max_ratio, es.max_ratio_case = _reduce(*ratio), _case(line)
                if rho:
                    a = (Err << e["kp"], rho)
                    dd = rho.bit_length() - 1 + pl.sc - e["kp"] - fmt.qmin
                    cur = es.profile.get(dd)
                    if cur is None or _gt(a, cur[0]):
                        es.profile[dd] = (_reduce(*a), _case(line))
                bn = Err * rd - rn_ * rho
                sh = pl.sc - fmt.qmin
                b = (bn << sh, rd) if sh >= 0 else (bn, rd << -sh)
                if es.b_max is None or _gt(b, es.b_max):
                    es.b_max, es.b_case = _reduce(*b), _case(line)
        return reasons

    # -- the kinds of the second wave: each returns the reason of a failure, or None ----------

    def _rounded(self, pl, e, es, x, z, V, r, line):
        fmt = pl.fmt
        if e.get("when"):
            if r is None:
                # The condition does not hold: nothing is claimed (Milestone 2, `when`).
                es.count(D.WHEN_FAILS)
                return None
            es.count(D.WHEN_HOLDS)
        es.applicable += 1
        o = z[e["first"]]
        Vc = V << pl.sh_val
        if (r << pl.sh_out) == Vc:
            es.count("exact")
        elif e["mode"] == "nearest":
            d = F.rdir(fmt, V, pl.sv, False)
            u = F.rdir(fmt, V, pl.sv, True)
            es.count("tie" if (d + u) << pl.sh_out == 2 * Vc else "inexact")
        else:
            es.count("inexact, = RN" if r == F.rn(fmt, V, pl.sv) else "inexact, != RN")
        if o != r:
            return "output is not the value rounded %s" % e["mode"]
        return None

    def _upper(self, pl, e, es, x, z, V, _r, line):
        fmt = pl.fmt
        es.applicable += 1
        o = z[e["first"]]
        exc = (o << pl.sh_out) - (V << pl.sh_val)
        g = F.gap_below(fmt, o) << pl.sh_out
        if exc < 0:
            es.count("below value")
            return "output below the value"
        # A histogram of the excess by quarters of a gap.
        q4 = -((-4 * exc) // g)
        es.count("excess in (%s, %s] gaps" % (frac_str(_reduce(q4 - 1, 4)), frac_str(_reduce(q4, 4)))
                 if q4 else "exact")
        ratio = (exc, g)
        es.track_max("excess in gaps", ratio, line)
        if all(sum(x[lo:hi]) >= 0 for lo, hi in pl.groups):
            es.track_max("excess in gaps, nonnegative operands", ratio, line)
        if exc * e["gd"] > e["gn"] * g:
            return "output above the value by more than %s gaps" % frac_str((e["gn"], e["gd"]))
        return None

    def _predicate(self, pl, e, es, x, z, V, _r, line):
        es.applicable += 1
        a, b = e["fn"](x)
        rel = e["rel"]
        truth = _relation(a, rel, b)
        es.count("true" if truth else "false")
        if z[e["first"]] != (1 if truth else 0):
            return "mask is not the truth of %s" % rel
        return None

    def _encloses(self, pl, e, es, x, z, V, _r, line):
        es.applicable += 1
        contained = self._containment(pl, e, es, x, z, line)
        if "exact" not in e:
            return contained
        # With exact_when (Milestone 2), each of the two statements that fails is counted under
        # its name, as the statements of the extended domain are.
        exact = self._exactness(pl, e, es, x, z, line)
        if contained:
            es.count("failed containment")
        if exact:
            es.count("failed exact_when")
        return "; ".join(w for w in (contained, exact) if w) or None

    # -- the kinds of Milestone 2 (architecture.md, "Claims of Milestone 2") ------------------

    def _exact_failing(self, e, es, x):
        """The texts of the conditions of exact_when that do not hold, each counted."""
        failing = [t for holds, t in e["exact"] if not holds(x)]
        for t in failing:
            es.count(D.EXACT_FAILS + t)
        if not failing:
            es.count(D.EXACT_HOLDS)
        return failing

    def _exact_error(self, pl, e, es, x, z, V):
        """exact_when of an error entry: the output limbs sum to the value when every condition
        holds."""
        if self._exact_failing(e, es, x):
            return None
        O = 0
        for lo, hi in e["ranges"]:
            O += sum(z[lo:hi])
        if (O << pl.sh_out) != (V << pl.sh_val):
            return "exact_when holds but the output is not the value exactly (%s)" % es.label
        return None

    def _exactness(self, pl, e, es, x, z, line):
        """exact_when of an encloses entry: when every condition holds, the output ball is
        exactly the set, so center - radius and center + radius are the least and the greatest
        value of the set (with containment, which _containment judges)."""
        if "exact" not in e or self._exact_failing(e, es, x):
            return None
        rg = pl.set_range(e, x)
        if rg is None:
            # An empty set (a negative input radius, outside every requirement nonneg()).
            es.count("exact_when holds, the set empty (a negative input radius)")
            return None
        lo, hi = rg
        sh = e["sh_q"]
        c0, c1 = e["center"]
        cz = sum(z[c0:c1]) << sh
        rz = z[e["radius"]] << sh
        if cz - rz == lo and cz + rz == hi:
            return None
        unit = "units of 2^%d" % (pl.fmt.qmin - sh)
        if 2 * cz != lo + hi:
            return ("exact_when holds but the center is not the center of the set: it is %s, the "
                    "set's is %s/2 (%s)" % (cz, lo + hi, unit))
        return ("exact_when holds but the radius is not the radius of the set: it is %s, the "
                "set's is %s/2 (%s)" % (rz, hi - lo, unit))

    def _neighbor(self, pl, e, es, x, z, V, r, line):
        """The output is the next number of the format above (up) or below the operand."""
        fmt = pl.fmt
        es.applicable += 1
        up = e["side"] == "up"
        es.count(D.neighbor_row(fmt, V))
        for cl in D.neighbor_steps(fmt, V, r, up):
            es.count(cl)
        if z[e["first"]] != r:
            return "output is not the next number of the format %s the operand (%s)" % (
                "above" if up else "below", F.fixed_hex(fmt, r))
        return None

    def _bound(self, pl, e, es, x, z, V, d, line):
        """below: the value rounded down, stepped down `steps` times, <= output <= value;
        above, symmetrically; in the format unbounded above (beyond +-Omega the case is
        non-finite, not judged).  d is the directed rounding."""
        fmt = pl.fmt
        es.applicable += 1
        below = e["side"] == "below"
        o = z[e["first"]]
        Vc = V << pl.sh_val
        es.count(D.BOUND_EXACT if (d << pl.sh_out) == Vc else D.BOUND_INEXACT)
        oc = o << pl.sh_out
        if (oc > Vc) if below else (oc < Vc):
            return "output %s the value" % ("above" if below else "below")
        k, t = 0, d
        while t != o:
            if k == e["steps"]:
                return "output more than %d steps beyond the value rounded %s" % (
                    e["steps"], "down" if below else "up")
            t = D.step_unbounded(fmt, t, below)
            k += 1
        es.count(D.steps_text(k))
        return None

    def _containment(self, pl, e, es, x, z, line):
        """The set is within the returned radius of the returned center (finite operands and
        outputs), with the statistics of the radius."""
        fmt = pl.fmt
        rg = pl.set_range(e, x)
        if rg is None:
            es.count("empty set (a negative input radius)")
            return None
        lo, hi = rg
        clo, chi = e["center"]
        sh = e["sh_q"]
        cz = sum(z[clo:chi]) << sh
        rz = z[e["radius"]] << sh
        # The smallest radius around the returned center that encloses the set.
        rmin = max(cz - lo, hi - cz)
        if rmin > rz:
            return "set not enclosed: needs radius %s, has %s (%s units of 2^%d)" % (
                rmin, rz, "a deficit of %d" % (rmin - rz), fmt.qmin - sh)
        if rmin == 0:
            es.count("smallest radius 0, radius 0" if rz == 0 else "smallest radius 0, radius > 0")
        else:
            d = rz - rmin
            if d == 0:
                es.count("ratio 1")
            else:
                k = d.bit_length() - rmin.bit_length()
                if (d << max(-k, 0)) < (rmin << max(k, 0)):
                    k -= 1
                es.count("ratio - 1 in [2^%d, 2^%d)" % (k, k + 1))
            es.track_max("radius / smallest enclosing radius", (rz, rmin), line)
            es.track_min("radius / smallest enclosing radius", (rz, rmin), line)
        g = F.gap_below(fmt, z[e["radius"]]) << sh
        es.track_min("slack in gaps of the radius", (rz - rmin, g), line)
        return None

    # -- the entries under a mask: the bounds of the folds' stage ------------------------------

    def _conditional(self, pl, st, x, z, line):
        """upper with a value of its own, holds: when the entry's mask output is true, the output
        is at least the exact value of value (upper), or the relation holds between the exact
        values of the two args (holds); nothing is claimed when the mask is false.  An output the
        entry names that is not a number of the format is a failure if it is outside the format;
        if it is infinite or a NaN where the mask is true, the finite domain claims nothing of it
        (the output is not a number), and the line is suspicious: the kernel said its bound
        holds and gave none."""
        fmt = pl.fmt
        for i, v in enumerate(z):
            if i not in pl.out_masks and (v == F.OUTSIDE or (type(v) is int
                                                             and not F.is_member(fmt, v))):
                self._fail(st, line, "output limb not a number of the format")
                return
        st.c["judged"] += 1
        eta = pl.eta
        names = None
        reasons, sus = [], []
        for i, c in enumerate(pl.entries):
            es = st.entries[i]
            on = z[c["cond"]] == 1
            self._count_classes(pl, es, x, on, line)
            if not on:
                es.count("%s false: nothing claimed" % c["cond_name"])
                continue
            if any(type(z[s]) is not int for s in c["used"]):
                es.count("%s true, an output not finite: nothing claimed" % c["cond_name"])
                # Suspicious as everywhere in the finite domain: where every input limb and value
                # is below Omega/4 (the radius of an accumulator overflows inside for a sum of
                # magnitudes near Omega, a case of no bound kernel).
                if BV.small_inputs(pl, x) and BV.small_stated(pl, c, x, z):
                    sus.append("%s: an output is not finite although %s is true" % (
                        es.label, c["cond_name"]))
                continue
            es.applicable += 1
            if names is None:
                names = {}
                for n, (lo, hi) in pl.in_slices.items():
                    if n not in pl.kernel.masks:
                        names[n] = sum(x[lo:hi]) * eta
                for n, (lo, hi) in pl.out_slices.items():
                    if hi - lo == 1 and lo not in pl.out_masks and type(z[lo]) is int:
                        names[n] = z[lo] * eta
                env = {"u": pl.u, "eta": eta, "names": names,
                       "unit": lambda k: pl.units[k][0], "tiny": lambda k: pl.units[k][1]}
            try:
                vals = [CX.evaluate(t, env) for t in c["trees"]]
            except CX.CExprError as ex:
                es.failures += 1
                es.count("failed: the stated value does not exist")
                reasons.append("%s: the stated value does not exist where %s is true (%s)" % (
                    c["kind"], c["cond_name"], ex))
                continue
            if c["kind"] == "upper":
                why = self._upper_value(pl, c, es, z, vals[0], line)
            else:
                a, b = vals
                truth = _relation(a, c["rel"], b)
                es.count("holds" if truth else "does not hold")
                why = None if truth else "holds: %s is false where %s is true" % (
                    es.label.split(" if ")[0][len("holds "):], c["cond_name"])
            if why:
                es.failures += 1
                reasons.append(why)
        if sus:
            st.c["suspicious"] += 1
            st.example("suspicious", line, "; ".join(sus), self.max_examples)
        if reasons:
            st.c["failed"] += 1
            for r in reasons:
                st.reason(r)
            st.example("failure", line, "; ".join(reasons), self.max_examples)
        else:
            st.c["passed"] += 1

    def _upper_value(self, pl, c, es, z, v, line):
        """The output is at least v exactly; the statistics say how close it comes."""
        o = z[c["first"]]
        ov = o * pl.eta
        if ov < v:
            es.count("below the stated value")
            return "upper: the output is below its stated value where %s is true" % c["cond_name"]
        d = ov - v
        if d == 0:
            es.count("exactly the stated value")
        if v > 0:
            r = d / v
            es.track_min("(output - value) / value", (r.numerator, r.denominator), line)
            es.track_max("(output - value) / value", (r.numerator, r.denominator), line)
            g = F.gap_below(pl.fmt, o) * pl.eta
            r = d / g
            es.track_min("excess over a positive stated value, in gaps of the output",
                         (r.numerator, r.denominator), line)
        else:
            es.count("stated value not positive")
        return None

    def _count_classes(self, pl, es, x, on, line):
        """For a bound kernel with a count m: m * unit(K) against the limits of COUNT_LIMITS,
        whether m is an integer, with the mask; the largest m * unit(K) where the mask is true
        and the smallest where it is false."""
        if pl.count_stat is None:
            return
        (lo, hi), kn, unit = pl.count_stat
        m = sum(x[lo:hi])
        what = "%s %s" % (es.label.rsplit(" if ", 1)[-1], "true" if on else "false")
        mv = m * pl.eta
        t = mv * unit
        if t == 0:
            cls = "m*unit(%s) = 0" % kn
        else:
            cls = None
            prev = "0"
            for lim, text in COUNT_LIMITS:
                if t <= lim if lim < 1 else t < lim:
                    cls = "%s < m*unit(%s) %s %s" % (prev, kn, "<=" if lim < 1 else "<", text)
                    break
                prev = text
            if cls is None:
                cls = "m*unit(%s) >= 1" % kn
        es.count("%s, %s" % (what, cls))
        es.count("m an integer" if mv.denominator == 1 else "m not an integer")
        tt = (t.numerator, t.denominator)
        if on:
            es.track_max("m*unit(%s) where %s" % (kn, what), tt, line)
        else:
            es.track_min("m*unit(%s) where %s" % (kn, what), tt, line)

    def _maximum(self, pl, e, es, x, z, V, _r, line):
        """The output is the larger of the exact values of the two arguments (the folds of
        maxima): counts of which one it is."""
        es.applicable += 1
        a, b = e["fn"](x)
        es.count("first argument larger" if a > b else "second argument larger" if b > a
                 else "arguments equal")
        if (a < 0) != (b < 0):
            es.count("arguments of both signs")
        if z[e["first"]] << e["sh_out"] != max(a, b):
            return "maximum: the output is not the larger of %s" % es.label.split(" of ", 1)[-1]
        return None

    def _fail(self, st, line, why):
        st.c["failed"] += 1
        st.reason(why)
        st.example("failure", line, why, self.max_examples)

    def _invalid(self, st, line, why):
        st.c["invalid"] += 1
        st.reason("invalid: " + why)
        st.example("invalid", line, why, self.max_examples)


SECOND_WAVE_KINDS = {"rounded": Checker._rounded, "upper": Checker._upper,
                     "predicate": Checker._predicate, "encloses": Checker._encloses,
                     "neighbor": Checker._neighbor, "bound": Checker._bound,
                     "maximum": Checker._maximum}
# outward in the finite domain (the interval kernels, intervals.py).
SECOND_WAVE_KINDS.update(IV.FINITE_KINDS)


# ---------------------------------------------------------------------------
# Report

def report(summary, out=sys.stdout, far=None, fail_on_suspicious=False, expect_valid=False,
           verbose=False):
    w = lambda s="": print(s, file=out)
    t = summary.totals()
    bad = summary.failed(fail_on_suspicious, expect_valid)
    w("kairn-oracle check: %s" % ("FAIL" if bad else "PASS"))
    w("  claims: %s" % summary.claims_path)
    for ce in summary.claims_errors:
        w("  CLAIMS ERROR (the kernel is not judged and the run fails): %s" % ce)
    for cw in summary.claims_warnings:
        w("  claims warning: %s" % cw)
    w("  %d cases: %d passed, %d failed, %d invalid, %d non-finite (%d of them in a lower "
      "limb only, %d with an exact result beyond Omega), %d suspicious, %d out of scope "
      "(precision below min_precision)"
      % (t["cases"], t["passed"], t["failed"], t["invalid"], t["nonfinite"] + t["nonfinite_tail"],
         t["nonfinite_tail"], t["beyond"], t["suspicious"], t["out_of_scope"]))
    for e in summary.stream_errors:
        w("  STREAM ERROR: %s" % e)
    cov = summary.coverage.describe()
    if cov:
        w("coverage (from the generator's headers):")
        for c in cov:
            w("  " + c)
    # Rows per (kernel, format, tag), then one aggregate per (kernel, format).
    groups = {}
    for (k, f, tag), s in summary.keys.items():
        groups.setdefault((k, f), []).append((tag, s))
    for (k, f), rows in sorted(groups.items()):
        agg = KeyStats()
        for _, s in rows:
            agg.merge(s, summary.max_examples)
        p = agg.p
        farv = far if far is not None else p
        w()
        w("== %s %s" % (k, f))
        w("  %-12s %10s %10s %8s %8s %9s %6s %6s" % ("tag", "cases", "judged", "failed", "invalid",
                                                   "nonfinite", "susp", "oos"))
        for tag, s in sorted(rows, key=lambda r: r[0]) + ([("(all)", agg)] if len(rows) > 1 else []):
            c = s.c
            w("  %-12s %10d %10d %8d %8d %9d %6d %6d" % (
                tag or "(none)", c["cases"], c["judged"], c["failed"], c["invalid"],
                c["nonfinite"] + c["nonfinite_tail"], c["suspicious"], c["out_of_scope"]))
        if agg.reasons:
            for r, n in sorted(agg.reasons.items(), key=lambda x: -x[1]):
                w("    %8d  %s" % (n, r))
        for es in agg.entries:
            w("  %s%s: %d applicable, %d failures" % (
                es.label, "" if es.bound_source in (None, "instances") else
                " [bound %s]" % es.bound_source, es.applicable, es.failures))
            if es.kind == "fold_error" and es.max_ratio is not None:
                if es.max_ratio[1] == 0:
                    w("    largest error/allowed: infinite (nonzero error, zero bound) at")
                else:
                    w("    largest error/allowed: %s = %s at" % (frac_dec(es.max_ratio),
                                                               _short(frac_str(es.max_ratio))))
                w("      %s" % _short(es.max_ratio_case, 400))
            if es.kind != "error":
                _report_counts(w, es)
                continue
            if es.max_ratio is not None:
                if es.max_ratio[1] == 0:
                    w("    largest error/allowed: infinite (nonzero error, zero bound) at")
                else:
                    w("    largest error/allowed: %s = %s at" % (frac_dec(es.max_ratio),
                                                               _short(frac_str(es.max_ratio))))
                w("      %s" % es.max_ratio_case)
            a = es.observed_a(farv) if farv is not None else None
            w("    (a) largest |err|/(u^k rho) where u^k rho >= 2^%s eta: %s" % (
                farv, "no such case" if a is None else "%s = %s" % (frac_dec(a[0]),
                                                                   _short(frac_str(a[0])))))
            if a is not None:
                w("      %s" % a[1])
            if es.b_max is not None:
                w("    (b) largest (|err| - c u^k rho)/eta: %s = %s at" % (
                    frac_dec(es.b_max), _short(frac_str(es.b_max))))
                w("      %s" % es.b_case)
            if verbose and es.profile:
                w("    profile of (a) by D = floor(log2(u^k rho/eta)):")
                for d, v in sorted(es.profile.items()):
                    if v is not None:
                        w("      D=%4d  %s" % (d, frac_dec(v[0])))
        for kind in ("failure", "invalid", "suspicious"):
            for line, why in agg.examples[kind]:
                w("  %s: %s" % (kind.upper(), why))
                # A fold's line may hold thousands of limbs: its middle is left out.
                w("    %s" % _short(line, 1000))


def _count_order(key):
    # Histogram buckets in numeric order: "(a, b] gaps" by a, "[2^k, ...)" by k.
    m = re.search(r"\(([-0-9/]+),", key) or re.search(r"\[2\^(-?\d+),", key)
    if m:
        n, _, d = m.group(1).partition("/")
        return (1, Fraction(int(n), int(d or 1)), key)
    return (0, 0, key)


def _report_counts(w, es):
    """Outcomes, histograms and extremes of the second-wave kinds."""
    for k in sorted(es.counts, key=_count_order):
        w("    %10d  %s" % (es.counts[k], k))
    for what, d in (("largest", es.maxima), ("smallest", es.minima)):
        for k, (r, case) in sorted(d.items()):
            w("    %s %s: %s = %s at" % (what, k, frac_dec(r), _short(frac_str(r))))
            w("      %s" % _short(case, 400))


def _short(s, n=80):
    return s if len(s) <= n else s[:n // 2] + "..." + s[-n // 2:]


def load_summary(path, max_examples=5):
    with open(path, "r", encoding="utf-8") as fh:
        return Summary.from_json(json.load(fh), max_examples)


def write_summary(summary, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary.to_json(), fh)
        fh.write("\n")
