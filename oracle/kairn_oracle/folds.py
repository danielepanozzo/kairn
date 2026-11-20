"""Folds: their claims and the judge of their completed lines.

architecture.md, "Folds", "Claims of Milestone 2" (the list "folds" of gen/claims.json) and "The
line protocol" (requests with arrays); milestone2.md, "Batch kernels".  A fold is a loop of
kernels along arrays (a sum, a dot product); its claims are about the result of the whole loop,
in either order of summation, for any number of lanes:

    |r - sum_i v_i| <= ((1 + term)(1 + eps)^h_r - 1) sum_i |v_i| + (1 + eps)^h_a n tau

with v_i the exact value of element i (the fold's `value` over the arrays' names), h_r and h_a
the heights `rel` and `abs` of the order (n or n - 1, natural numbers), and, in the extended
domain (every fold of this stage), the flag: true exactly when limb 0 of the result is finite;
false, then every limb of the result is a NaN; true, then every element is finite and
`normalized` and `fold_error` hold of the result.

Every verdict is decided with Python integers: the elements' values are integers at the scale
of the value expression (eta for a sum of limbs, eta^2 for a product of two), and the bound is
compared with the error after clearing denominators.  The powers (1 + eps)^h of a long array are
bracketed between two integers at a fixed binary scale 2^P, computed by squaring with the
roundings directed outward (pow_bracket): a case whose error is below the lower end of the
bound's bracket passes, one above its upper end fails, and the few in between (none so far) are
decided with the exact powers, Fractions of thousands of bits.  The bracket of each height is
computed once per plan.
"""

import math
import re
from fractions import Fraction

from . import cexpr as CX
from . import expr as EX
from . import extended as XT
from . import fmt as F
from .claims import (ClaimsError, DOMAINS, parse_fraction, format_u_eta, _CANONICAL_RE,
                     _NAME)

FOLD_FIELDS = {"name", "domain", "arrays", "outputs", "value", "requires", "ensures", "orders",
               "packed_lanes", "step", "combine", "finish", "min_precision", "status",
               "theorems", "source", "instances"}
ORDERS = ("sequential", "lanes")
ROLES = ("stored", "supplied")
HEIGHTS = ("n", "n-1")
STATUSES = ("proved", "unverified")
MASK_TEXT = {"0": 0, "1": 1}
INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN

_ORDER_RE = re.compile(r"(?:seq|lanes:(0|[1-9][0-9]*))\Z")
_COUNT_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")

# The classes of lengths and of lane counts that the statistics count (and the guards ask for).
FIXED_LENGTHS = tuple(range(18))
LENGTH_BUCKETS = ((18, 64), (65, 256), (257, 1024), (1025, 4096))


def length_class(n):
    if n in FIXED_LENGTHS:
        return "length %d" % n
    for lo, hi in LENGTH_BUCKETS:
        if lo <= n <= hi:
            return "length %d to %d" % (lo, hi)
    return "length above %d" % LENGTH_BUCKETS[-1][1]


def order_classes(order, n):
    """The counts of an order: its kind and lane count, and whether there are more lanes than
    elements (the lane order is then the sequential one)."""
    if order is None:
        return ["order: sequential"]
    W = order
    if W <= 8:
        out = ["order: lanes, W = %d" % W]
    elif W <= 64:
        out = ["order: lanes, W = 9 to 64"]
    else:
        out = ["order: lanes, W above 64"]
    if W > n >= 1:
        out.append("order: lanes, more lanes than elements (W > n >= 1)")
    return out


# ---------------------------------------------------------------------------
# The claims of a fold

class FoldEntry:
    KNOWN = {"normalized": {"kind", "of"},
             "fold_error": {"kind", "of", "eps", "term", "tau", "heights"},
             "finite_or_nan": {"kind", "of", "flag"}}

    def __init__(self, fold, raw, index, ferr_index):
        self.raw = raw
        self.index = index
        if not isinstance(raw, dict) or "kind" not in raw:
            raise ClaimsError("%s: ensures entry %d has no kind" % (fold.name, index))
        self.kind = raw["kind"]
        where = "%s: ensures entry %d (%s)" % (fold.name, index, self.kind)
        if self.kind not in self.KNOWN:
            raise ClaimsError("%s: unknown kind (a fold has normalized, fold_error and "
                              "finite_or_nan)" % where)
        extra = set(raw) - self.KNOWN[self.kind]
        if extra:
            raise ClaimsError("%s: unknown fields %s" % (where, sorted(extra)))
        for f in self.KNOWN[self.kind] - {"kind"}:
            if f not in raw:
                raise ClaimsError("%s: missing %s" % (where, f))
        self.of = fold.resolve_outputs(raw["of"], where)
        self.ferr_index = None
        if self.kind == "fold_error":
            self.ferr_index = ferr_index
            self.consts = {}
            for c in ("eps", "term", "tau"):
                try:
                    tree = CX.parse(raw[c])
                except CX.CExprError as ex:
                    raise ClaimsError("%s: %s: %s" % (where, c, ex))
                if CX.names(tree):
                    raise ClaimsError("%s: %s names %s; it is a constant over u, eta and integers"
                                      % (where, c, CX.names(tree)[0]))
                self.consts[c] = (tree, str(raw[c]).strip())
            h = raw["heights"]
            if not isinstance(h, dict) or set(h) != set(fold.orders):
                raise ClaimsError("%s: heights must give each order of the fold (%s), got %r"
                                  % (where, ", ".join(fold.orders), h))
            self.heights = {}
            for o, hh in h.items():
                if not isinstance(hh, dict) or set(hh) != {"rel", "abs"}:
                    raise ClaimsError("%s: heights of %s must be {\"rel\": H, \"abs\": H}" % (
                        where, o))
                for k in ("rel", "abs"):
                    if hh[k] not in HEIGHTS:
                        raise ClaimsError("%s: height %s of %s must be n or n-1, got %r" % (
                            where, k, o, hh[k]))
                self.heights[o] = (hh["rel"], hh["abs"])
        elif self.kind == "finite_or_nan":
            f = raw["flag"]
            if not isinstance(f, str) or f not in fold.masks:
                raise ClaimsError("%s: flag must name a mask output, got %r" % (where, f))
            self.flag = f
        self.label = self._label()

    def _label(self):
        of = "+".join(self.of)
        if self.kind == "fold_error":
            hs = ", ".join("%s rel %s abs %s" % (o, r, a) for o, (r, a) in self.heights.items())
            return "fold_error(%s) eps=%s, term=%s, tau=%s; heights %s" % (
                of, self.consts["eps"][1], self.consts["term"][1], self.consts["tau"][1], hs)
        if self.kind == "finite_or_nan":
            return "finite_or_nan(%s) flag %s" % (of, self.flag)
        return "normalized(%s)" % of


class Fold:
    def __init__(self, raw, claims):
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise ClaimsError("fold entry without a name")
        self.name = raw["name"]
        self.raw = raw
        self.claims = claims
        nm = self.name
        if not re.fullmatch(_NAME, nm):
            raise ClaimsError("%s: not a name" % nm)
        self.domain = raw.get("domain", "finite")
        if self.domain not in DOMAINS:
            raise ClaimsError("%s: unknown domain %r (finite or extended)" % (nm, self.domain))
        if self.domain != "extended":
            # architecture.md reads a fold in the extended domain only ("Reading, in the extended
            # domain (every fold of this stage)"); a finite reading is not defined.
            raise ClaimsError("%s: a fold of the %s domain, whose reading architecture.md does not "
                              "give (every fold of this stage is extended)" % (nm, self.domain))
        self.extended = True
        arrays = raw.get("arrays")
        if not isinstance(arrays, list) or not arrays:
            raise ClaimsError("%s: arrays must be a nonempty list" % nm)
        self.arrays = []
        self.roles = {}
        for a in arrays:
            if (not isinstance(a, dict) or set(a) != {"name", "limbs", "role"}
                    or not isinstance(a["name"], str) or not re.fullmatch(_NAME, a["name"])):
                raise ClaimsError("%s: bad array %r (name, limbs, role)" % (nm, a))
            l = a["limbs"]
            if not isinstance(l, int) or isinstance(l, bool) or l < 1:
                raise ClaimsError("%s: array %s has limbs %r" % (nm, a["name"], l))
            if a["role"] not in ROLES:
                raise ClaimsError("%s: array %s has the role %r (stored or supplied)"
                                  % (nm, a["name"], a["role"]))
            if a["name"] in self.roles or a["name"] in CX.RESERVED:
                raise ClaimsError("%s: array name %r listed twice or reserved" % (nm, a["name"]))
            self.arrays.append((a["name"], l))
            self.roles[a["name"]] = a["role"]
        self.array_names = [n for n, _ in self.arrays]
        self.masks = set()
        self.outputs = self._outputs(raw.get("outputs"))
        names = self.array_names + [n for n, _ in self.outputs]
        if len(set(names)) != len(names):
            raise ClaimsError("%s: array and output names must be distinct" % nm)
        v = raw.get("value")
        try:
            self.value_tree = EX.parse(v)
        except EX.ExprError as ex:
            raise ClaimsError("%s: value %r: %s" % (nm, v, ex))
        for n in EX.names(self.value_tree):
            if n not in self.roles:
                raise ClaimsError("%s: value names %r, which is not an array" % (nm, n))
        self.value_text = v.strip()
        # Requirements on every element: canonical(NAME) of an array of two limbs or more (the
        # extended domain); a one-limb element is any value of the format.
        reqs = raw.get("requires", [])
        if not isinstance(reqs, list):
            raise ClaimsError("%s: requires must be a list" % nm)
        self.requires = []
        limbs = dict(self.arrays)
        for r in reqs:
            m = _CANONICAL_RE.match(r) if isinstance(r, str) else None
            if m is None or m.group(1) not in limbs or limbs[m.group(1)] < 2:
                raise ClaimsError("%s: requirement %r is outside the vocabulary of a fold "
                                  "(canonical(NAME) of an array of two limbs)" % (nm, r))
            if m.group(1) in self.requires:
                raise ClaimsError("%s: requirement %r listed twice" % (nm, r))
            self.requires.append(m.group(1))
        for n, l in self.arrays:
            if l > 1 and n not in self.requires:
                raise ClaimsError("%s: the %d-limb array %s has no canonical(%s)" % (nm, l, n, n))
        orders = raw.get("orders")
        if (not isinstance(orders, list) or not orders or len(set(map(str, orders))) != len(orders)
                or any(o not in ORDERS for o in orders)):
            raise ClaimsError("%s: orders must be a nonempty list of sequential and lanes, got %r"
                              % (nm, orders))
        self.orders = list(orders)
        ens = raw.get("ensures")
        if not isinstance(ens, list):
            raise ClaimsError("%s: ensures must be a list" % nm)
        self.ensures = []
        nfe = 0
        for i, e in enumerate(ens):
            ent = FoldEntry(self, e, i, nfe)
            if ent.kind == "fold_error":
                nfe += 1
            self.ensures.append(ent)
        flags = [e for e in self.ensures if e.kind == "finite_or_nan"]
        if len(flags) != 1:
            # The reading of the extended domain is the flag's: without one, nothing says when
            # the other entries hold.
            raise ClaimsError("%s: a fold of the extended domain has one finite_or_nan entry, "
                              "not %d" % (nm, len(flags)))
        self.flag_entry = flags[0]
        for k in ("step", "combine", "finish"):
            s = raw.get(k)
            if s is None and k != "step":
                setattr(self, k, None)
                continue
            if not isinstance(s, str) or s not in claims.kernel_names:
                raise ClaimsError("%s: %s %r is not a kernel of the claims" % (nm, k, s))
            setattr(self, k, s)
        if "lanes" in self.orders and self.combine is None:
            raise ClaimsError("%s: the lane order needs a combination" % nm)
        mp = raw.get("min_precision", 1)
        if mp is None:
            mp = 1
        if not isinstance(mp, int) or isinstance(mp, bool) or mp < 1:
            raise ClaimsError("%s: min_precision must be an integer" % nm)
        self.min_precision = mp
        self.status = raw.get("status")
        if self.status not in STATUSES:
            raise ClaimsError("%s: status must be proved or unverified, got %r" % (nm, self.status))
        th = raw.get("theorems")
        if th is not None and (not isinstance(th, dict) or set(th) != set(self.orders)
                               or any(t is not None and not isinstance(t, dict)
                                      for t in th.values())):
            raise ClaimsError("%s: theorems must give each order a theorem object or null" % nm)
        pk = raw.get("packed_lanes", {})
        self.packed_lanes = {}
        if not isinstance(pk, dict):
            raise ClaimsError("%s: packed_lanes must be an object" % nm)
        for fname, per in pk.items():
            try:
                fm = F.parse_format(fname)
            except F.FormatError as ex:
                raise ClaimsError("%s: packed_lanes: %s" % (nm, ex))
            if not isinstance(per, dict):
                raise ClaimsError("%s: packed_lanes[%s] must map backends to lanes" % (nm, fname))
            for be, w in per.items():
                if not isinstance(w, int) or isinstance(w, bool) or w < 1:
                    raise ClaimsError("%s: packed_lanes[%s][%s] = %r" % (nm, fname, be, w))
                self.packed_lanes[(fm.name, be)] = w
        # unit(K), tiny(K) in the constants: kernels of the claims with one error entry.
        for e in self.ensures:
            if e.kind == "fold_error":
                for tree, _t in e.consts.values():
                    for _f, kn in CX.calls(tree):
                        claims.check_unit_kernel(kn, "%s: %s" % (nm, e.label))
        self._instances = self._read_instances(raw.get("instances", {}))
        self._consts = {}
        for triple in self._instances:
            self.constants(F.Format(*triple))
        self.unknown_fields = sorted(set(raw) - FOLD_FIELDS)
        self.warnings = []

    def _outputs(self, lst):
        if not isinstance(lst, list) or not lst:
            raise ClaimsError("%s: outputs must be a nonempty list" % self.name)
        out = []
        for d in lst:
            if not isinstance(d, dict) or not isinstance(d.get("name"), str):
                raise ClaimsError("%s: bad output %r" % (self.name, d))
            ty = d.get("type", "limbs")
            if ty == "mask":
                if d.get("limbs", 1) != 1 or isinstance(d.get("limbs", 1), bool):
                    raise ClaimsError("%s: mask %s has limbs %r" % (self.name, d["name"],
                                                                    d.get("limbs")))
                self.masks.add(d["name"])
                out.append((d["name"], 1))
                continue
            if ty != "limbs":
                raise ClaimsError("%s: output %s has the unknown type %r" % (self.name, d["name"], ty))
            l = d.get("limbs")
            if not isinstance(l, int) or isinstance(l, bool) or l < 1:
                raise ClaimsError("%s: bad output %r" % (self.name, d))
            out.append((d["name"], l))
        return out

    def resolve_outputs(self, of, where):
        outs = dict(self.outputs)
        if isinstance(of, str):
            names = [x.strip() for x in of.split("+")]
        elif isinstance(of, list) and all(isinstance(x, str) for x in of):
            names = of
        else:
            raise ClaimsError("%s: bad 'of' %r" % (where, of))
        for n in names:
            if n not in outs or n in self.masks:
                raise ClaimsError("%s: 'of' names %r, which is not a limb output" % (where, n))
        return names

    def _read_instances(self, inst):
        """{(p, qmin, qmax): [(eps, term, tau) per fold_error entry]}: instances maps each named
        format to a list with one {eps, term, tau} per fold_error entry, in their order."""
        n = sum(1 for e in self.ensures if e.kind == "fold_error")
        out = {}
        if not isinstance(inst, dict):
            raise ClaimsError("%s: instances must be an object" % self.name)
        for fname, lst in inst.items():
            try:
                f = F.parse_format(fname)
            except F.FormatError as ex:
                raise ClaimsError("%s: instances: %s" % (self.name, ex))
            if not isinstance(lst, list) or len(lst) != n:
                raise ClaimsError("%s: instances[%s] must list one object per fold_error entry "
                                  "(%d)" % (self.name, fname, n))
            vals = []
            for d in lst:
                if not isinstance(d, dict) or set(d) != {"eps", "term", "tau"}:
                    raise ClaimsError("%s: instances[%s] entries have eps, term and tau"
                                      % (self.name, fname))
                vals.append(tuple(parse_fraction(d[c], "%s %s %s" % (self.name, fname, c))
                                  for c in ("eps", "term", "tau")))
            out[f.triple] = vals
        return out

    def constants(self, fmt):
        """[(eps, term, tau, source)] per fold_error entry in a format: the listed instance in a
        named format, which must equal the constants evaluated exactly; the evaluation in a
        format that is not listed.  eps must be positive, term and tau nonnegative."""
        c = self._consts.get(fmt.triple)
        if c is not None:
            return c
        u, eta = format_u_eta(fmt)
        claims = self.claims
        env = {"u": u, "eta": eta, "names": {},
               "unit": lambda k: claims.unit_tiny(k, fmt)[0],
               "tiny": lambda k: claims.unit_tiny(k, fmt)[1]}
        listed = self._instances.get(fmt.triple)
        out = []
        for e in self.ensures:
            if e.kind != "fold_error":
                continue
            try:
                ev = tuple(CX.evaluate(e.consts[k][0], env) for k in ("eps", "term", "tau"))
            except CX.CExprError as ex:
                raise ClaimsError("%s, %s, %s: %s" % (self.name, fmt.name, e.label, ex))
            src = "evaluated (format not in instances)"
            if listed is not None:
                li = listed[e.ferr_index]
                if li != ev:
                    raise ClaimsError("%s, %s, %s: instances give eps=%s term=%s tau=%s but the "
                                      "expressions give %s, %s, %s" % (
                                          self.name, fmt.name, e.label, li[0], li[1], li[2],
                                          ev[0], ev[1], ev[2]))
                src = "instances"
            if ev[0] <= 0 or ev[1] < 0 or ev[2] < 0:
                raise ClaimsError("%s, %s, %s: eps must be positive and term, tau nonnegative "
                                  "(eps=%s term=%s tau=%s)" % (self.name, fmt.name, e.label,
                                                               ev[0], ev[1], ev[2]))
            out.append(ev + (src,))
        self._consts[fmt.triple] = out
        return out


# ---------------------------------------------------------------------------
# Powers, bracketed

def pow_bracket(num, den, h, P):
    """(lo, hi) with lo <= (num/den)^h 2^P <= hi, for num >= den > 0: binary powering with every
    product rounded down for lo and up for hi."""
    one = 1 << P
    if h == 0:
        return one, one
    blo = (num << P) // den
    bhi = -((-(num << P)) // den)
    lo = hi = one
    for bit in bin(h)[2:]:
        lo = (lo * lo) >> P
        hi = -((-(hi * hi)) >> P)
        if bit == "1":
            lo = (lo * blo) >> P
            hi = -((-(hi * bhi)) >> P)
    return lo, hi


class Heights:
    """The bound of one fold_error entry at one pair of heights (h_r, h_a), bracketed:
    with G = (1 + term)(1 + eps)^h_r - 1 and A = (1 + eps)^h_a, gl <= G 2^P td <= gh and
    al <= A 2^P <= ah, td the denominator of term."""

    __slots__ = ("hr", "ha", "P", "gl", "gh", "al", "ah", "_exact")

    def __init__(self, eps, term, hr, ha):
        self.hr, self.ha = hr, ha
        en, ed = eps.numerator, eps.denominator
        tn, td = term.numerator, term.denominator
        self.P = P = ed.bit_length() + td.bit_length() + 96 + 2 * max(hr, ha, 1).bit_length()
        xl, xh = pow_bracket(ed + en, ed, hr, P)
        self.gl = (td + tn) * xl - (td << P)
        self.gh = (td + tn) * xh - (td << P)
        self.al, self.ah = pow_bracket(ed + en, ed, ha, P)
        self._exact = None

    def exact(self, eps, term):
        """(Gn, Gd, An, Ad): G = Gn/Gd and A = An/Ad exactly, as integers (not reduced: a
        Fraction would reduce numbers of thousands of bits at every operation)."""
        if self._exact is None:
            en, ed = eps.numerator, eps.denominator
            tn, td = term.numerator, term.denominator
            dr = ed ** self.hr
            self._exact = ((td + tn) * (ed + en) ** self.hr - td * dr, td * dr,
                           (ed + en) ** self.ha, ed ** self.ha)
        return self._exact


def exact_compare(h, c, err, S, n, tau):
    """(num, den) of err / bound, exactly as integers (den = 0 when the bound is zero)."""
    Gn, Gd, An, Ad = h.exact(c["eps"], c["term"])
    tn, td = tau.numerator, tau.denominator
    # bound = Gn S / Gd + An n tn / (Ad td) = (Gn S Ad td + An n tn Gd) / (Gd Ad td).
    return err * Gd * Ad * td, Gn * S * Ad * td + An * n * tn * Gd


def _height(h, n):
    return n if h == "n" else max(n - 1, 0)


# ---------------------------------------------------------------------------
# One (fold, format)

class FoldPlan:
    def __init__(self, fold, fmt, ignore_min_precision):
        self.fold = fold
        self.fmt = fmt
        q = fmt.qmin
        self.in_scope = ignore_min_precision or fmt.p >= fold.min_precision
        self.slices = {}
        pos = 0
        for n, l in fold.arrays:
            self.slices[n] = (pos, pos + l)
            pos += l
        self.L = pos
        # Which limb columns of an element are the leading limbs of a multi-limb array (for the
        # requirement canonical()).
        self.canon = [self.slices[n] for n in fold.requires]
        src, self.sv = EX.compile_tree(fold.value_tree, self._leaf)
        self.value_fn = EX.make_function(["x"], src)
        self.out_slices = {}
        pos = 0
        for n, l in fold.outputs:
            self.out_slices[n] = (pos, pos + l)
            pos += l
        self.n_out = pos
        self.out_masks = frozenset(self.out_slices[n][0] for n in fold.masks)
        self.sc = min(q, self.sv)
        self.sh_out = q - self.sc
        self.sh_val = self.sv - self.sc
        self.T = fmt.qmax + fmt.p
        # 2^(T-3), an eighth of the overflow threshold, at scale sc: "far from overflow".
        k = self.T - 3 - self.sc
        self.far = (1 << k, 1) if k >= 0 else (1, 1 << -k)
        # u * sum of magnitudes at the comparison scale, for the heavy cancellation count.
        self.p = fmt.p
        self.entries = []
        consts = fold.constants(fmt) if self.in_scope else None
        for e in fold.ensures:
            c = {"kind": e.kind, "ranges": [self.out_slices[n] for n in e.of]}
            if e.kind == "fold_error" and consts is not None:
                eps, term, tau, src = consts[e.ferr_index]
                # tau at the comparison scale: tau / 2^sc.
                tsc = tau * (Fraction(1 << -self.sc) if self.sc < 0 else Fraction(1, 1 << self.sc))
                c.update(eps=eps, term=term, tau=tau, tsc=tsc, source=src,
                         heights=e.heights, cache={})
            elif e.kind == "finite_or_nan":
                c["flag"] = self.out_slices[e.flag][0]
            self.entries.append(c)
        self.flag_index = fold.ensures.index(fold.flag_entry)

    def _leaf(self, name):
        lo, hi = self.slices[name]
        return "(%s)" % "+".join("x[%d]" % i for i in range(lo, hi)), self.fmt.qmin

    def heights(self, c, order_name, n):
        hr, ha = c["heights"][order_name]
        key = (_height(hr, n), _height(ha, n))
        h = c["cache"].get(key)
        if h is None:
            h = c["cache"][key] = Heights(c["eps"], c["term"], key[0], key[1])
        return h


def parse_order(text):
    """None for seq, W for lanes:W; or raises ValueError."""
    m = _ORDER_RE.match(text)
    if m is None:
        raise ValueError(text)
    return None if m.group(1) is None else int(m.group(1))


# ---------------------------------------------------------------------------
# One completed line

def judge_line(ck, line, lt, sep, right, tag):
    """The verdict on one completed line of a fold: FOLD FORMAT ORDER N LIMB ... [#TAG] -> RESULT
    ... (the tag already taken off lt)."""
    fold = ck.claims.get_fold(lt[0])
    fname = lt[1] if len(lt) > 1 else "?"
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    pl = None
    if fmt is not None:
        key = ("fold", fold.name, fmt.name)
        pl = ck.plans.get(key)
        if pl is None and key not in ck.plans:
            try:
                pl = FoldPlan(fold, fmt, ck.ignore_min_precision)
            except ClaimsError as ex:
                ck.claims.mark_broken(fold.name, str(ex))
                ck.claims.folds.pop(fold.name, None)
                if str(ex) not in ck.summary.claims_errors:
                    ck.summary.claims_errors.append(str(ex))
            ck.plans[key] = pl
    st = ck.summary.stats((fold.name, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
    if pl is not None and not st.entries:
        from .check import EntryStats
        st.entries = [EntryStats(e.label, e.kind) for e in fold.ensures]
        for es, c in zip(st.entries, pl.entries):
            es.bound_source = c.get("source")
    st.c["cases"] += 1
    if pl is None:
        ck._fail(st, line, "unknown format %r" % fname if fmt is None else
                 "the claims of %s cannot be read" % fold.name)
        return
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    if len(lt) < 4:
        ck._fail(st, line, "malformed: a fold's request is FOLD FORMAT ORDER N LIMB ...")
        return
    try:
        order = parse_order(lt[2])
    except ValueError:
        ck._fail(st, line, "malformed: order %r (seq or lanes:W)" % lt[2])
        return
    if not _COUNT_RE.match(lt[3]):
        ck._fail(st, line, "malformed: length %r" % lt[3])
        return
    n = int(lt[3])
    order_name = "sequential" if order is None else "lanes"
    ins = lt[4:]
    outs = right.split(" ")
    if len(ins) != n * pl.L or "" in ins:
        ck._fail(st, line, "malformed: %d input limbs, %d elements of %d limbs take %d"
                 % (len(ins), n, pl.L, n * pl.L))
        return
    if len(outs) != pl.n_out or "" in outs:
        ck._fail(st, line, "malformed: %d results, the fold returns %d" % (len(outs), pl.n_out))
        return
    if order_name not in fold.orders:
        ck._fail(st, line, "the fold claims no %s order" % order_name)
        return
    if not pl.in_scope:
        st.c["out_of_scope"] += 1
        return
    fmt = pl.fmt
    # Requirements first: every limb a number of the format or a non-finite value, every element
    # of a multi-limb array canonical.  A line outside them is invalid, never passed.
    try:
        cols = []
        for j in range(pl.L):
            cols.append([F.parse_limb(fmt, t) for t in ins[j * n:(j + 1) * n]])
    except F.LimbError as ex:
        ck._invalid(st, line, "input limb malformed: %s" % ex)
        return
    finite = True
    member = F.is_member
    for col in cols:
        for v in col:
            if type(v) is int:
                if not member(fmt, v):
                    ck._invalid(st, line, "input limb not a number of the format")
                    return
            elif v == F.OUTSIDE:
                ck._invalid(st, line, "input limb not a number of the format")
                return
            else:
                finite = False
    elems = list(zip(*cols)) if n else []
    for name, (lo, hi) in zip(fold.requires, pl.canon):
        for i, x in enumerate(elems):
            if not XT.canonical(fmt, x[lo:hi]):
                ck._invalid(st, line, "requires canonical(%s): element %d" % (name, i))
                return
    for i in pl.out_masks:
        if outs[i] not in MASK_TEXT:
            ck._fail(st, line, "mask output %r is not 0 or 1" % outs[i])
            return
    try:
        z = [MASK_TEXT[t] if i in pl.out_masks else F.parse_limb(fmt, t) for i, t in enumerate(outs)]
    except F.LimbError as ex:
        ck._fail(st, line, "output limb malformed: %s" % ex)
        return
    for i, v in enumerate(z):
        if i not in pl.out_masks and (v == F.OUTSIDE or (type(v) is int and not member(fmt, v))):
            ck._fail(st, line, "output limb not a number of the format")
            return
    st.c["judged"] += 1
    case = _Case(pl, elems, n, order, order_name, finite)
    reasons, sus = [], []
    fe = pl.entries[pl.flag_index]
    flag = z[fe["flag"]]
    for i, c in enumerate(pl.entries):
        es = st.entries[i]
        kind = c["kind"]
        if kind == "finite_or_nan":
            why = _finite_or_nan(pl, c, es, case, z, line, sus)
        elif flag != 1 or not case.finite or not _all_finite(z, c["ranges"]):
            # Claimed only with a true flag, every element and the result finite (the flag's
            # entry fails the other combinations).
            es.count("not claimed: the flag false, or a non-finite element or result")
            continue
        elif kind == "normalized":
            es.applicable += 1
            why = None
            w = []
            for lo, hi in c["ranges"]:
                w.extend(z[lo:hi])
            if not F.normalized_limbs(fmt, w):
                why = "not normalized"
        else:
            why = _fold_error(pl, c, es, case, z, line)
        if why:
            es.failures += 1
            reasons.append(why)
    if sus:
        st.c["suspicious"] += 1
        st.example("suspicious", line, "; ".join(sus), ck.max_examples)
    if reasons:
        st.c["failed"] += 1
        for r in reasons:
            st.reason(r)
        st.example("failure", line, "; ".join(reasons), ck.max_examples)
    else:
        st.c["passed"] += 1


def _all_finite(z, ranges):
    return all(type(v) is int for lo, hi in ranges for v in z[lo:hi])


class _Case:
    """The exact values of one line's elements, computed once for its entries."""

    __slots__ = ("n", "order", "order_name", "finite", "vals", "sigma", "S", "classes")

    def __init__(self, pl, elems, n, order, order_name, finite):
        self.n = n
        self.order = order
        self.order_name = order_name
        self.finite = finite
        if finite:
            fn = pl.value_fn
            self.vals = vals = [fn(x) for x in elems]
            self.sigma = sum(vals)
            self.S = sum(map(abs, vals))
        else:
            self.vals = self.sigma = self.S = None
        self.classes = [length_class(n)] + order_classes(order, n)


def _finite_or_nan(pl, c, es, case, z, line, sus):
    """The flag is true exactly when limb 0 of the result is finite; false, every limb is a NaN;
    true, every element and every limb of the result are finite."""
    es.applicable += 1
    for k in case.classes:
        es.count(k)
    w = []
    for lo, hi in c["ranges"]:
        w.extend(z[lo:hi])
    flag = z[c["flag"]]
    lead = type(w[0]) is int
    if flag != (1 if lead else 0):
        return "the flag is %d although limb 0 of the result is %s" % (
            flag, "finite" if lead else F.fixed_hex(pl.fmt, w[0]))
    if flag:
        es.count("flag true")
        if not case.finite:
            return "the flag is true although an element is not finite"
        if not all(type(v) is int for v in w):
            return "the flag is true although a lower limb of the result is not finite"
        return None
    if not case.finite:
        es.count("flag false: a non-finite element")
    else:
        far = _far(pl, case)
        if far:
            es.count("flag false: finite elements far from overflow")
            sus.append("finite_or_nan: the flag is false although every element is finite and "
                       "every partial sum is below an eighth of the overflow threshold")
        else:
            es.count("flag false: finite elements, near overflow")
        v = abs(case.sigma) << pl.sh_val
        if v <= (pl.fmt.omega << pl.sh_out):
            es.count("flag false: finite elements, |exact sum| <= Omega")
    if not all(v == NAN for v in w):
        return "the flag is false but a limb of the result is not a NaN"
    return None


def _far(pl, case):
    """Every partial sum, of any order, certainly below 2^(T-3): (1 + term)(1 + eps)^h_r S +
    (1 + eps)^h_a n tau, the largest magnitude of a node of the tree of the sum, with the upper
    ends of the brackets, for the first fold_error entry (True when the fold has none and S is
    below the threshold)."""
    S = case.S << pl.sh_val
    fe = [c for c in pl.entries if c["kind"] == "fold_error"]
    tn, td = pl.far
    if not fe:
        return S * td < tn
    c = fe[0]
    h = pl.heights(c, case.order_name, case.n)
    t = c["term"]
    # (1 + term) X_r = (gh + td 2^P) / (td 2^P) at most; A = ah / 2^P at most.
    tdd = t.denominator
    tau = c["tsc"]
    lhs = ((h.gh + (tdd << h.P)) * S * tau.denominator + h.ah * case.n * tau.numerator * tdd) * td
    return lhs < (tn * tdd * tau.denominator) << h.P


def _fold_error(pl, c, es, case, z, line):
    es.applicable += 1
    for k in case.classes:
        es.count(k)
    n = case.n
    R = 0
    for lo, hi in c["ranges"]:
        R += sum(z[lo:hi])
    sig = case.sigma << pl.sh_val
    S = case.S << pl.sh_val
    err = abs((R << pl.sh_out) - sig)
    fmt = pl.fmt
    if S and 2 * abs(sig) <= S:
        es.count("cancellation: |sum| <= sum of magnitudes / 2")
    if S and (abs(sig) << pl.p) <= S:
        es.count("heavy cancellation: |sum| <= u * sum of magnitudes")
    if S and sig == 0:
        es.count("exact sum zero, an element not zero")
    if abs(sig) > (fmt.omega << pl.sh_out):
        es.count("|exact sum| > Omega")
    es.count("result exact" if err == 0 else "result inexact")
    h = pl.heights(c, case.order_name, n)
    tau = c["tsc"]
    tn, td = tau.numerator, tau.denominator
    tdd = c["term"].denominator
    P = h.P
    lhs = (err * tdd * td) << P
    rel_lo, rel_hi = h.gl * S * td, h.gh * S * td
    abs_lo, abs_hi = h.al * n * tn * tdd, h.ah * n * tn * tdd
    if tn:
        if abs_lo > rel_hi:
            es.count("absolute term larger than the relative term")
        if lhs > rel_hi:
            es.count("error above the relative term alone")
    blo, bhi = rel_lo + abs_lo, rel_hi + abs_hi
    if lhs <= blo:
        bad = False
    elif lhs > bhi:
        bad = True
    else:
        es.count("decided with the exact powers")
        num, den = exact_compare(h, c, err, S, n, tau)
        bad = num > den
    # The largest error / allowed: an upper estimate from the bracket first, the exact ratio
    # when it may be a new maximum.
    names = ("error / allowed, order %s" % case.order_name,)
    cur = es.max_ratio
    curo = es.maxima.get(names[0])
    if blo > 0:
        cand = (lhs, blo)
        new = cur is None or _gt(cand, cur)
        newo = curo is None or _gt(cand, curo[0])
    else:
        new = newo = cur is None or curo is None or err > 0
    if new or newo:
        ratio = _exact_ratio(c, h, err, S, n, tau)
        if new and (cur is None or _gt(ratio, cur)):
            es.max_ratio, es.max_ratio_case = ratio, line
        if newo:
            es.track_max(names[0], ratio, line)
    if bad:
        return "error above the bound (%s): %s" % (es.label, _ratio_text(err, h, c, S, n, tau))
    return None


_BIG_BITS = 4096


def _exact_ratio(c, h, err, S, n, tau):
    """err / bound as (num, den), exactly; a zero bound gives (0, 1) for an exact result and
    (1, 0), above every finite ratio, otherwise.  A fraction whose terms have more than 4096 bits
    (the powers of long arrays) is rounded down to a multiple of 2^-128: a statistic, never a
    verdict."""
    num, den = exact_compare(h, c, err, S, n, tau)
    if den == 0:
        return (0, 1) if num == 0 else (1, 0)
    if max(num.bit_length(), den.bit_length()) > _BIG_BITS:
        return ((num << 128) // den, 1 << 128)
    g = math.gcd(num, den)
    return (num // g, den // g)


def _ratio_text(err, h, c, S, n, tau):
    num, den = _exact_ratio(c, h, err, S, n, tau)
    if den == 0:
        return "a nonzero error and a zero bound"
    from .check import frac_dec
    return "error/allowed = %s" % frac_dec((num, den))


def _gt(a, b):
    from .check import _gt as gt
    return gt(a, b)
