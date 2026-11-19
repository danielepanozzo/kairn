"""Judging completed lines against claims.

Every verdict is decided with Python integers: limbs are fixed values (multiples of
eta, see fmt.py), the exact value of a sum lives at scale eta and the exact value of a
product at scale eta^2, and bounds are compared after clearing denominators.
"""

import json
import math
import sys
from fractions import Fraction

from . import fmt as F
from .claims import ClaimsError

SUMMARY_VERSION = 1


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


class EntryStats:
    __slots__ = ("label", "kind", "applicable", "failures", "max_ratio", "max_ratio_case",
                 "profile", "b_max", "b_case", "bound_source")

    def __init__(self, label, kind):
        self.label = label
        self.kind = kind
        self.applicable = 0
        self.failures = 0
        self.max_ratio = None          # largest |error| / allowed, as (num, den)
        self.max_ratio_case = None
        # Observed constant (a) by distance from underflow: D = floor(log2(u^k rho / eta))
        # maps to the largest |error| / (u^k rho) among cases at that distance.
        self.profile = {}
        self.b_max = None              # largest (|error| - rel*rho) / eta
        self.b_case = None
        self.bound_source = None

    def merge(self, o):
        self.applicable += o.applicable
        self.failures += o.failures
        if o.max_ratio is not None and (self.max_ratio is None or _gt(o.max_ratio, self.max_ratio)):
            self.max_ratio, self.max_ratio_case = o.max_ratio, o.max_ratio_case
        for d, (r, case) in o.profile.items():
            cur = self.profile.get(d)
            if cur is None or _gt(r, cur[0]):
                self.profile[d] = (r, case)
        if o.b_max is not None and (self.b_max is None or _gt(o.b_max, self.b_max)):
            self.b_max, self.b_case = o.b_max, o.b_case
        self.bound_source = self.bound_source or o.bound_source

    def observed_a(self, far):
        best = None
        for d, (r, case) in self.profile.items():
            if d >= far and (best is None or _gt(r, best[0])):
                best = (r, case)
        return best

    def to_json(self):
        enc = lambda r: None if r is None else [str(r[0]), str(r[1])]
        return {"label": self.label, "kind": self.kind, "applicable": self.applicable,
                "failures": self.failures, "max_ratio": enc(self.max_ratio),
                "max_ratio_case": self.max_ratio_case,
                "profile": {str(d): [enc(r), c] for d, (r, c) in sorted(self.profile.items())},
                "b_max": enc(self.b_max), "b_case": self.b_case,
                "bound_source": self.bound_source}

    @classmethod
    def from_json(cls, j):
        dec = lambda r: None if r is None else (int(r[0]), int(r[1]))
        s = cls(j["label"], j["kind"])
        s.applicable = j["applicable"]
        s.failures = j["failures"]
        s.max_ratio = dec(j["max_ratio"])
        s.max_ratio_case = j["max_ratio_case"]
        s.profile = {int(d): (dec(v[0]), v[1]) for d, v in j["profile"].items()}
        s.b_max = dec(j["b_max"])
        s.b_case = j["b_case"]
        s.bound_source = j.get("bound_source")
        return s


COUNTERS = ("cases", "judged", "passed", "failed", "invalid", "out_of_scope", "nonfinite",
            "nonfinite_tail", "suspicious")


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

class Plan:
    """Everything about one (kernel, format) that does not depend on the operands."""

    def __init__(self, kernel, fmt, ignore_min_precision):
        self.kernel = kernel
        self.fmt = fmt
        q = fmt.qmin
        self.in_slices, self.n_in = self._slices(kernel.inputs)
        self.out_slices, self.n_out = self._slices(kernel.outputs)
        op, a, b = kernel.value
        self.op = op
        self.lhs = self.in_slices[a]
        self.rhs = self.in_slices[b]
        self.sv = 2 * q if op == "*" else q          # scale of the exact value
        # op "=": the outputs approximate the input itself; lhs and rhs name the same input.
        self.sc = min(q, self.sv)                    # common scale for comparisons
        self.sh_out = q - self.sc
        self.sh_val = self.sv - self.sc
        self.in_scope = ignore_min_precision or fmt.p >= kernel.min_precision
        self.requires = []
        for r in kernel.requires:
            if r[0] == "normalized":
                self.requires.append(("normalized", r[1], self.in_slices[r[1]]))
            else:
                self.requires.append(("abs_ge", r, self.in_slices[r[1]], self.in_slices[r[2]]))
        # product_large: value = 0 or |value| >= 2^(2p-1) eta, as a fixed value at scale sv.
        self.pl_thr = 1 << max(2 * fmt.p - 1 + q - self.sv, 0)
        self.entries = []
        for e in kernel.ensures:
            ranges = [self.out_slices[n] for n in e.of]
            c = {"kind": e.kind, "ranges": ranges, "first": ranges[0][0]}
            if e.kind == "error":
                rel, ab, src = kernel.bound(fmt, e)
                # The bound is rel*rho + ab; with rho and the error at scale sc it reads
                # rel*rho + ab*2^-sc in those units.
                abs_sc = ab * (Fraction(1 << -self.sc) if self.sc < 0 else Fraction(1, 1 << self.sc))
                c.update(rel_n=rel.numerator, rel_d=rel.denominator,
                         abs_n=abs_sc.numerator, abs_d=abs_sc.denominator,
                         k=e.k, kp=e.k * fmt.p, form=e.form, when=e.when, source=src)
            self.entries.append(c)

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
        for k in claims.kernels.values():
            if k.unknown_fields:
                self.summary.claims_warnings.append(
                    "%s: fields not read by the oracle: %s" % (k.name, ", ".join(k.unknown_fields)))
        self.max_examples = max_examples
        self.plans = {}
        self.open_header = None     # (descriptor, expected lines, kernel, format, seen)
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
                    pl = Plan(kernel, f, self.ignore_min_precision)
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
            return
        if self.open_header is not None:
            self.stream_error("generator header inside another generator's output (truncated?)")
        try:
            start = int(fields.pop("start"))
            count = int(fields.pop("count"))
        except (KeyError, ValueError):
            self.stream_error("malformed generator header: %s" % line)
            self.open_header = None
            return
        fields.pop("event", None)
        self.open_header = [tuple(sorted(fields.items())), start, start + count, 0]

    def finish(self):
        if self.open_header is not None:
            self.stream_error("stream ended before the generator's trailer: the runner stopped "
                              "early or the stream was truncated")
            self.open_header = None
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
        lt = left.split(" ")
        kname = lt[0]
        fname = lt[1] if len(lt) > 1 else "?"
        tag = ""
        if len(lt) > 2 and lt[-1].startswith("#"):
            tag = lt[-1][1:].split(":", 1)[0]
            lt = lt[:-1]
        pl = self.plan(kname, fname)
        fmt = pl.fmt if pl else None
        st = self.summary.stats((kname, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
        if pl is not None and not st.entries:
            st.entries = [EntryStats(e.label, e.kind) for e in pl.kernel.ensures]
            for es, pe in zip(st.entries, pl.entries):
                es.bound_source = pe.get("source")
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
            return
        # Requirements first: a case outside them is never counted as passed.
        try:
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
        for r in pl.requires:
            if r[0] == "normalized":
                lo, hi = r[2]
                if not F.normalized_limbs(fmt, x[lo:hi]):
                    self._invalid(st, line, "requires normalized(%s)" % r[1])
                    return
            else:
                (alo, ahi), (blo, bhi) = r[2], r[3]
                if abs(sum(x[alo:ahi])) < abs(sum(x[blo:bhi])):
                    self._invalid(st, line, "requires abs_ge(%s, %s)" % (r[1][1], r[1][2]))
                    return
        try:
            z = [F.parse_limb(fmt, t) for t in outs]
        except F.LimbError as ex:
            self._fail(st, line, "output limb malformed: %s" % ex)
            return
        lo, hi = pl.lhs
        X = sum(x[lo:hi])
        lo, hi = pl.rhs
        Y = sum(x[lo:hi])
        op = pl.op
        V = X + Y if op == "+" else X - Y if op == "-" else X * Y if op == "*" else X
        if type(z[0]) is not int or any(type(v) is not int for v in z):
            if any(v == F.OUTSIDE for v in z):
                self._fail(st, line, "output limb not a number of the format")
                return
            lead = type(z[0]) is not int
            st.c["nonfinite" if lead else "nonfinite_tail"] += 1
            q4 = fmt.omega
            small = all(4 * abs(v) < q4 for v in x) and 4 * abs(X) < q4 and 4 * abs(Y) < q4
            if small:
                d = pl.sv - fmt.qmin
                small = ((4 * abs(V)) << d) < q4 if d >= 0 else 4 * abs(V) < (q4 << -d)
            if small:
                st.c["suspicious"] += 1
                st.example("suspicious", line, "non-finite %s with operands and exact value "
                           "below Omega/4" % ("leading limb" if lead else "lower limb"),
                           self.max_examples)
            return
        for v in z:
            if not F.is_member(fmt, v):
                self._fail(st, line, "output limb not a number of the format")
                return
        st.c["judged"] += 1
        reasons = []
        for i, e in enumerate(pl.entries):
            es = st.entries[i]
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
            else:
                if e["when"] == "product_large" and not (V == 0 or abs(V) >= pl.pl_thr):
                    continue
                es.applicable += 1
                O = 0
                for lo, hi in e["ranges"]:
                    O += sum(z[lo:hi])
                Vc = V << pl.sh_val
                Err = abs((O << pl.sh_out) - Vc)
                if e["form"] == "R":
                    rho = abs(Vc)
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
                    es.failures += 1
                    reasons.append("error above bound (%s)" % es.label)
                # A zero bound gives the ratio 0 for an exact result and (1, 0), which
                # compares above every finite ratio, for an inexact one.
                ratio = (num, den) if den else ((0, 1) if num == 0 else (1, 0))
                if es.max_ratio is None or _gt(ratio, es.max_ratio):
                    es.max_ratio, es.max_ratio_case = _reduce(*ratio), line
                if rho:
                    a = (Err << e["kp"], rho)
                    dd = rho.bit_length() - 1 + pl.sc - e["kp"] - fmt.qmin
                    cur = es.profile.get(dd)
                    if cur is None or _gt(a, cur[0]):
                        es.profile[dd] = (_reduce(*a), line)
                bn = Err * rd - rn_ * rho
                sh = pl.sc - fmt.qmin
                b = (bn << sh, rd) if sh >= 0 else (bn, rd << -sh)
                if es.b_max is None or _gt(b, es.b_max):
                    es.b_max, es.b_case = _reduce(*b), line
        if reasons:
            st.c["failed"] += 1
            for r in reasons:
                st.reason(r)
            st.example("failure", line, "; ".join(reasons), self.max_examples)
        else:
            st.c["passed"] += 1

    def _fail(self, st, line, why):
        st.c["failed"] += 1
        st.reason(why)
        st.example("failure", line, why, self.max_examples)

    def _invalid(self, st, line, why):
        st.c["invalid"] += 1
        st.reason("invalid: " + why)
        st.example("invalid", line, why, self.max_examples)


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
      "limb only), %d suspicious, %d out of scope (precision below min_precision)"
      % (t["cases"], t["passed"], t["failed"], t["invalid"], t["nonfinite"] + t["nonfinite_tail"],
         t["nonfinite_tail"], t["suspicious"], t["out_of_scope"]))
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
            if es.kind != "error":
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
                for d, (r, _) in sorted(es.profile.items()):
                    w("      D=%4d  %s" % (d, frac_dec(r)))
        for kind in ("failure", "invalid", "suspicious"):
            for line, why in agg.examples[kind]:
                w("  %s: %s" % (kind.upper(), why))
                w("    %s" % line)


def _short(s, n=80):
    return s if len(s) <= n else s[:n // 2] + "..." + s[-n // 2:]


def load_summary(path, max_examples=5):
    with open(path, "r", encoding="utf-8") as fh:
        return Summary.from_json(json.load(fh), max_examples)


def write_summary(summary, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary.to_json(), fh)
        fh.write("\n")
