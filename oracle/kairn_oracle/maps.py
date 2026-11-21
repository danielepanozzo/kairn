"""Maps and convolutions: their claims and the judge of their completed lines.

architecture.md, "Maps", "Convolutions", "Claims of Milestone 2" (the list "folds" of
gen/claims.json, with "map": true or "conv": true) and "The line protocol"; milestone2.md, "sum,
dot, axpy, convolution" and "When something is not finite".

A map writes an array: written element z_i is its step, a kernel of the claims, on the scalars and
element i of each array read (step_args, in order).  Its claims are `entries` (every written
element whose leading limb is finite comes from finite operands and satisfies every `ensures` entry
of the step on them) and `finite_or_nan` (the flag is true exactly when the leading limb of every
written element is finite; when it is false, every element whose leading limb is not finite is
the canonical NaN, the others as computed).  Each written element is judged by the code that
judges a line of the step (check.Checker.verdict), with statistics of its own per entry of the
step.

A convolution writes the coefficients of the product of two polynomials: coefficient j, when its
leading limb is finite, satisfies every `ensures` entry of the fold `coefficients` (a dot product)
other than finite_or_nan, in that fold's sequential order, on the terms (x_i, y_{j-i}) for i from
max(0, j - n_y + 1) to min(j, n_x - 1) in increasing order; its flag is a map's.  Each coefficient
is judged by the code that judges a line of that fold (folds.py: the same plan, the same entries).

Lines (architecture.md, "The line protocol"):

    MAP FORMAT ORDER N SCALAR... LIMB... [#TAG] -> Z... MASK
    CONV FORMAT seq N_X N_Y LIMB... [#TAG] -> Z... MASK
"""

import re

from . import expr as EX
from . import extended as XT
from . import fmt as F
from . import folds as FO
from .claims import ClaimsError, DOMAINS, _CANONICAL_RE, _NAME

MAP_FIELDS = {"name", "map", "domain", "arrays", "scalars", "writes", "outputs", "value",
              "requires", "ensures", "orders", "packed_lanes", "step", "step_args", "check",
              "min_precision", "status", "theorem", "source"}
CONV_FIELDS = {"name", "conv", "domain", "arrays", "writes", "outputs", "value", "requires",
               "ensures", "orders", "coefficients", "check", "min_precision", "status", "theorem",
               "source"}
MASK_TEXT = FO.MASK_TEXT
INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
_POW2_RE = re.compile(r"\s*power_of_two\s*\(\s*(%s)\s*\)\s*\Z" % _NAME)
_COUNT_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


# ---------------------------------------------------------------------------
# Reading

def _groups(nm, lst, what, roles=True):
    """[(name, limbs)] and {name: role} of a list of arrays, scalars or written arrays."""
    if not isinstance(lst, list):
        raise ClaimsError("%s: %s must be a list" % (nm, what))
    out, role = [], {}
    keys = {"name", "limbs", "role"} if roles else {"name", "limbs"}
    for a in lst:
        if (not isinstance(a, dict) or set(a) != keys or not isinstance(a["name"], str)
                or not re.fullmatch(_NAME, a["name"])):
            raise ClaimsError("%s: bad %s entry %r (%s)" % (nm, what, a, ", ".join(sorted(keys))))
        l = a["limbs"]
        if not isinstance(l, int) or isinstance(l, bool) or l < 1:
            raise ClaimsError("%s: %s %s has limbs %r" % (nm, what, a["name"], l))
        if roles and a["role"] not in FO.ROLES:
            raise ClaimsError("%s: %s %s has the role %r (stored or supplied)"
                              % (nm, what, a["name"], a["role"]))
        out.append((a["name"], l))
        if roles:
            role[a["name"]] = a["role"]
    return out, role


def _mask_output(nm, raw):
    outs = raw.get("outputs")
    if (not isinstance(outs, list) or len(outs) != 1 or not isinstance(outs[0], dict)
            or outs[0].get("type") != "mask" or outs[0].get("limbs", 1) != 1
            or not isinstance(outs[0].get("name"), str)
            or set(outs[0]) - {"name", "limbs", "type"}):
        raise ClaimsError("%s: outputs must be one mask (the flag), got %r" % (nm, outs))
    return outs[0]["name"]


def _common(obj, raw, claims, kind):
    """What a map and a convolution share: name, domain, arrays, written array, flag, value,
    orders, minimum precision, status, check."""
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
        raise ClaimsError("%s without a name" % kind)
    nm = obj.name = raw["name"]
    obj.raw = raw
    obj.claims = claims
    if not re.fullmatch(_NAME, nm):
        raise ClaimsError("%s: not a name" % nm)
    obj.domain = raw.get("domain", "finite")
    if obj.domain not in DOMAINS:
        raise ClaimsError("%s: unknown domain %r (finite or extended)" % (nm, obj.domain))
    if obj.domain != "extended":
        raise ClaimsError("%s: a %s of the %s domain, whose reading architecture.md does not give"
                          % (nm, kind, obj.domain))
    obj.extended = True
    obj.arrays, obj.roles = _groups(nm, raw.get("arrays"), "arrays")
    if not obj.arrays:
        raise ClaimsError("%s: arrays must be a nonempty list" % nm)
    writes, _ = _groups(nm, raw.get("writes"), "writes", roles=False)
    if len(writes) != 1:
        raise ClaimsError("%s: a %s writes one array, not %d" % (nm, kind, len(writes)))
    obj.written, obj.wlimbs = writes[0]
    obj.flag_name = _mask_output(nm, raw)
    obj.masks = {obj.flag_name}
    obj.outputs = [(obj.flag_name, 1)]
    obj.orders = raw.get("orders")
    if (not isinstance(obj.orders, list) or not obj.orders
            or len(set(map(str, obj.orders))) != len(obj.orders)
            or any(o not in FO.ORDERS for o in obj.orders)):
        raise ClaimsError("%s: orders must be a nonempty list of sequential and lanes, got %r"
                          % (nm, obj.orders))
    mp = raw.get("min_precision", 1)
    if mp is None:
        mp = 1
    if not isinstance(mp, int) or isinstance(mp, bool) or mp < 1:
        raise ClaimsError("%s: min_precision must be an integer" % nm)
    obj.min_precision = mp
    obj.status = raw.get("status")
    if obj.status not in FO.STATUSES:
        raise ClaimsError("%s: status must be proved or unverified, got %r" % (nm, obj.status))
    th = raw.get("theorem")
    if th is not None and not isinstance(th, dict):
        raise ClaimsError("%s: theorem must be an object or null" % nm)
    ck = raw.get("check")
    k = claims.kernels.get(ck) if isinstance(ck, str) else None
    if k is None:
        raise ClaimsError("%s: check %r is not a readable kernel of the claims%s" % (
            nm, ck, " (%s)" % claims.broken[ck] if isinstance(ck, str) and ck in claims.broken
            else ""))
    if (not any(e.kind == "finite_or_nan" for e in k.ensures) or len(k.inputs) != 1
            or k.inputs[0][1] != obj.wlimbs):
        raise ClaimsError("%s: check %s is not a finish of the shape of fold_finish_k (one input "
                          "of %d limbs, a finite_or_nan entry)" % (nm, ck, obj.wlimbs))
    obj.check = ck
    obj.warnings = []


def _ensures(obj, raw, kind_entries, target_field):
    """The two entries of a map or a convolution: KIND (entries or coefficients) of the written
    array, naming the step or the fold, and finite_or_nan of the written array with the flag."""
    nm = obj.name
    ens = raw.get("ensures")
    if not isinstance(ens, list) or len(ens) != 2:
        raise ClaimsError("%s: ensures must be [%s, finite_or_nan], got %r" % (nm, kind_entries,
                                                                              ens))
    kinds = [e.get("kind") if isinstance(e, dict) else None for e in ens]
    if sorted(kinds) != sorted([kind_entries, "finite_or_nan"]):
        raise ClaimsError("%s: ensures must be one %s and one finite_or_nan entry, got %s"
                          % (nm, kind_entries, kinds))
    obj.ensures = []
    for i, e in enumerate(ens):
        where = "%s: ensures entry %d (%s)" % (nm, i, e["kind"])
        if e["kind"] == kind_entries:
            if set(e) != {"kind", "of", target_field}:
                raise ClaimsError("%s: fields must be kind, of and %s, got %s"
                                  % (where, target_field, sorted(e)))
        elif set(e) != {"kind", "of", "flag"}:
            raise ClaimsError("%s: fields must be kind, of and flag, got %s" % (where, sorted(e)))
        if e["of"] != obj.written:
            raise ClaimsError("%s: of must name the array written, %s, got %r"
                              % (where, obj.written, e["of"]))
        if e["kind"] == "finite_or_nan" and e["flag"] != obj.flag_name:
            raise ClaimsError("%s: flag must name the mask output %s, got %r"
                              % (where, obj.flag_name, e["flag"]))
        obj.ensures.append(e)
    return ens


class Entry:
    """A map's or a convolution's entry, as FoldEntry: kind, label."""

    def __init__(self, kind, label):
        self.kind = kind
        self.label = label


class Map:
    def __init__(self, raw, claims):
        _common(self, raw, claims, "map")
        nm = self.name
        self.scalars, srole = _groups(nm, raw.get("scalars", []), "scalars")
        self.roles.update(srole)
        names = [n for n, _ in self.scalars] + [n for n, _ in self.arrays] + [self.written,
                                                                            self.flag_name]
        if len(set(names)) != len(names):
            raise ClaimsError("%s: the names of the scalars, arrays, written array and flag must "
                              "be distinct" % nm)
        self.limbs = dict(self.scalars + self.arrays)
        v = raw.get("value")
        try:
            self.value_tree = EX.parse(v)
        except EX.ExprError as ex:
            raise ClaimsError("%s: value %r: %s" % (nm, v, ex))
        for n in EX.names(self.value_tree):
            if n not in self.limbs:
                raise ClaimsError("%s: value names %r, which is not an array or a scalar" % (nm, n))
        self.value_text = v.strip()
        # Requirements: canonical() of every group of two limbs, power_of_two() of a one-limb
        # scalar (a finite power of two in the extended domain).
        reqs = raw.get("requires", [])
        if not isinstance(reqs, list):
            raise ClaimsError("%s: requires must be a list" % nm)
        self.canonical, self.pow2 = [], []
        for r in reqs:
            m = _CANONICAL_RE.match(r) if isinstance(r, str) else None
            m2 = _POW2_RE.match(r) if isinstance(r, str) else None
            if m and m.group(1) in self.limbs and self.limbs[m.group(1)] >= 2:
                if m.group(1) in self.canonical:
                    raise ClaimsError("%s: requirement %r listed twice" % (nm, r))
                self.canonical.append(m.group(1))
            elif m2 and m2.group(1) in dict(self.scalars) and self.limbs[m2.group(1)] == 1:
                if m2.group(1) in self.pow2:
                    raise ClaimsError("%s: requirement %r listed twice" % (nm, r))
                self.pow2.append(m2.group(1))
            else:
                raise ClaimsError("%s: requirement %r is outside the vocabulary of a map "
                                  "(canonical(NAME) of a group of two limbs, power_of_two(NAME) "
                                  "of a one-limb scalar)" % (nm, r))
        for n, l in self.scalars + self.arrays:
            if l > 1 and n not in self.canonical:
                raise ClaimsError("%s: the %d-limb group %s has no canonical(%s)" % (nm, l, n, n))
        _ensures(self, raw, "entries", "kernel")
        ent = next(e for e in self.ensures if e["kind"] == "entries")
        self.step = raw.get("step")
        if ent["kernel"] != self.step:
            raise ClaimsError("%s: entries names the kernel %r, the step is %r"
                              % (nm, ent["kernel"], self.step))
        k = claims.kernels.get(self.step) if isinstance(self.step, str) else None
        if k is None:
            raise ClaimsError("%s: the step %r is not a readable kernel of the claims%s" % (
                nm, self.step, " (%s)" % claims.broken[self.step]
                if isinstance(self.step, str) and self.step in claims.broken else ""))
        if k.extended or getattr(k, "conditional", False):
            raise ClaimsError("%s: the step %s is not a kernel of the finite domain whose entries "
                              "hold on every line" % (nm, self.step))
        self.step_kernel = k
        sa = raw.get("step_args")
        if (not isinstance(sa, list) or sorted(map(str, sa)) != sorted(self.limbs)
                or len(sa) != len(self.limbs)):
            raise ClaimsError("%s: step_args must name every scalar and array once, got %r"
                              % (nm, sa))
        self.step_args = list(sa)
        if [l for _, l in k.inputs] != [self.limbs[n] for n in sa] or k.masks:
            raise ClaimsError("%s: the step %s takes %s, step_args give %s" % (
                nm, self.step, ", ".join("%s:%d" % io for io in k.inputs),
                ", ".join("%s:%d" % (n, self.limbs[n]) for n in sa)))
        if len(k.outputs) != 1 or k.outputs[0][1] != self.wlimbs:
            raise ClaimsError("%s: the step %s does not return one element of %d limbs"
                              % (nm, self.step, self.wlimbs))
        # The map's value is the step's, the step's inputs named as the map passes them.
        rename = {kn: an for (kn, _), an in zip(k.inputs, sa)}
        if k.value_tree is None or not _same_value(k.value_tree, self.value_tree, rename):
            raise ClaimsError("%s: value %r is not the value %r of the step %s on step_args"
                              % (nm, self.value_text, k.value_text, self.step))
        # Every requirement of the step on what the map passes is a requirement of the map.
        for r in k.requires:
            arg = rename.get(r[1]) if len(r) == 2 else None
            if r[0] == "normalized" and arg in self.canonical:
                continue
            if r[0] == "power_of_two" and arg in self.pow2:
                continue
            raise ClaimsError("%s: the step requires %s(%s), which the map does not require of %s"
                              % (nm, r[0], ", ".join(r[1:]), arg))
        if self.min_precision < k.min_precision:
            raise ClaimsError("%s: min_precision %d is below the step's, %d"
                              % (nm, self.min_precision, k.min_precision))
        self.packed_lanes = _packed(nm, raw.get("packed_lanes", {}))
        self.entry_labels = [Entry(e["kind"], ("entries(%s) of the step %s on %s" % (
            self.written, self.step, ", ".join(self.step_args))) if e["kind"] == "entries" else
            "finite_or_nan(%s) flag %s" % (self.written, self.flag_name)) for e in self.ensures]
        self.unknown_fields = sorted(set(raw) - MAP_FIELDS)
        if raw.get("map") is not True:
            raise ClaimsError("%s: map must be true" % nm)


class Conv:
    def __init__(self, raw, claims):
        _common(self, raw, claims, "convolution")
        nm = self.name
        if raw.get("conv") is not True:
            raise ClaimsError("%s: conv must be true" % nm)
        if len(self.arrays) != 2:
            raise ClaimsError("%s: a convolution has two arrays, not %d" % (nm, len(self.arrays)))
        if "scalars" in raw or "step" in raw or "step_args" in raw:
            raise ClaimsError("%s: a convolution has no step and no scalar" % nm)
        if self.orders != ["sequential"]:
            raise ClaimsError("%s: a convolution has the sequential order only, got %r"
                              % (nm, self.orders))
        _ensures(self, raw, "coefficients", "fold")
        ent = next(e for e in self.ensures if e["kind"] == "coefficients")
        fname = raw.get("coefficients")
        if ent["fold"] != fname:
            raise ClaimsError("%s: coefficients names the fold %r, the field coefficients %r"
                              % (nm, ent["fold"], fname))
        f = claims.folds.get(fname) if isinstance(fname, str) else None
        if not isinstance(f, FO.Fold) or f.maxima:
            raise ClaimsError("%s: the fold of the coefficients %r is not a readable sum of the "
                              "claims%s" % (nm, fname, " (%s)" % claims.broken[fname]
                                            if isinstance(fname, str) and fname in claims.broken
                                            else ""))
        if "sequential" not in f.orders:
            raise ClaimsError("%s: the fold %s has no sequential order" % (nm, fname))
        if f.arrays != self.arrays:
            raise ClaimsError("%s: the arrays %s are not those of the fold %s" % (nm, self.arrays,
                                                                                  fname))
        if raw.get("value") != f.raw.get("value") or sorted(raw.get("requires", [])) != sorted(
                f.raw.get("requires", [])):
            raise ClaimsError("%s: the value and requirements are not those of the fold %s"
                              % (nm, fname))
        limb_outs = [(n, l) for n, l in f.outputs if n not in f.masks]
        if len(limb_outs) != 1 or limb_outs[0][1] != self.wlimbs:
            raise ClaimsError("%s: the fold %s does not return one group of %d limbs"
                              % (nm, fname, self.wlimbs))
        if self.min_precision < f.min_precision:
            raise ClaimsError("%s: min_precision %d is below the fold's, %d"
                              % (nm, self.min_precision, f.min_precision))
        self.fold = f
        self.requires = f.requires
        self.value_text = f.value_text
        self.entry_labels = [Entry(e["kind"], ("coefficients(%s) of the fold %s, sequential"
                                               % (self.written, fname))
                                   if e["kind"] == "coefficients" else
                                   "finite_or_nan(%s) flag %s" % (self.written, self.flag_name))
                             for e in self.ensures]
        self.unknown_fields = sorted(set(raw) - CONV_FIELDS)


def _packed(nm, pk):
    out = {}
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
            out[(fm.name, be)] = w
    return out


def _same_value(a, b, rename):
    """True when the tree a, its names renamed, is the same polynomial as the tree b: compared at
    random integer points (fixed seed), as claims._same_polynomial compares the values of a full
    kernel and its core."""
    import random
    names = sorted(set(EX.names(b)) | set(rename.values()))
    pos = {n: i for i, n in enumerate(names)}
    fa = EX.make_function(["v"], EX.compile_tree(a, lambda n: ("v[%d]" % pos[rename[n]], 0))[0])
    fb = EX.make_function(["v"], EX.compile_tree(b, lambda n: ("v[%d]" % pos[n], 0))[0])
    rnd = random.Random(20261120)
    for _ in range(12):
        v = [rnd.randrange(-(1 << 80), 1 << 80) for _ in names]
        if fa(v) != fb(v):
            return False
    return True


# ---------------------------------------------------------------------------
# Judging

class MapPlan:
    def __init__(self, ck, m, fmt):
        self.m = m
        self.fmt = fmt
        self.in_scope = ck.ignore_min_precision or fmt.p >= m.min_precision
        self.step = ck.plan(m.step, fmt.name) if self.in_scope else None
        if self.in_scope and self.step is None:
            raise ClaimsError("%s: the plan of the step %s in %s cannot be made" % (
                m.name, m.step, fmt.name))
        self.n_scalar = sum(l for _, l in m.scalars)
        self.L = sum(l for _, l in m.arrays)
        self.W = m.wlimbs
        # Where each step argument comes from: ("s", start) in the scalars, ("a", start) in an
        # element; and how many limbs.
        pos, k = {}, 0
        for n, l in m.scalars:
            pos[n] = ("s", k, l)
            k += l
        k = 0
        for n, l in m.arrays:
            pos[n] = ("a", k, l)
            k += l
        self.args = [pos[n] for n in m.step_args]
        self.canon_s = [pos[n][1] for n in m.canonical if pos[n][0] == "s"]
        self.canon_a = [pos[n][1] for n in m.canonical if pos[n][0] == "a"]
        self.pow2_s = [pos[n][1] for n in m.pow2]
        self.n_step = len(m.step_kernel.ensures)


def _plan(ck, obj, fmt, cls):
    key = ("fold", obj.name, fmt.name)
    pl = ck.plans.get(key)
    if pl is None and key not in ck.plans:
        try:
            pl = cls(ck, obj, fmt)
        except ClaimsError as ex:
            ck.claims.mark_broken(obj.name, str(ex))
            ck.claims.folds.pop(obj.name, None)
            if str(ex) not in ck.summary.claims_errors:
                ck.summary.claims_errors.append(str(ex))
        ck.plans[key] = pl
    return pl


def _stats(ck, obj, pl, fmt, fname, tag, extra):
    st = ck.summary.stats((obj.name, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
    if pl is not None and not st.entries:
        from .check import EntryStats
        st.entries = [EntryStats(e.label, e.kind) for e in obj.entry_labels]
        for label, kind, source in extra(pl):
            st.entries.append(EntryStats(label, kind))
            st.entries[-1].bound_source = source
    st.c["cases"] += 1
    return st


def _parse_inputs(ck, st, line, fmt, toks):
    """The limbs of a line's inputs: [fixed or non-finite], or None (the line was counted)."""
    vals = []
    try:
        for t in toks:
            vals.append(F.parse_limb(fmt, t))
    except F.LimbError as ex:
        ck._invalid(st, line, "input limb malformed: %s" % ex)
        return None
    for v in vals:
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._invalid(st, line, "input limb not a number of the format")
            return None
    return vals


def _parse_outputs(ck, st, line, fmt, toks):
    """The written limbs and the flag, or None (the line was counted as failed)."""
    if toks[-1] not in MASK_TEXT:
        ck._fail(st, line, "mask output %r is not 0 or 1" % toks[-1])
        return None
    try:
        z = [F.parse_limb(fmt, t) for t in toks[:-1]]
    except F.LimbError as ex:
        ck._fail(st, line, "output limb malformed: %s" % ex)
        return None
    for v in z:
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._fail(st, line, "output limb not a number of the format")
            return None
    return z, MASK_TEXT[toks[-1]]


def _finish(ck, st, line, reasons, sus):
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


def _flag(es, flag, leads, kinds, nonfinite_ops):
    """The flag of a map or a convolution: true exactly when the leading limb of every written
    element is finite; the counts of its classes.  The reason of a failure, or None."""
    es.applicable += 1
    want = 1 if all(leads) else 0
    if flag != want:
        return ("the flag is %d although %s" % (flag, "every written element is finite" if want
                                                 else "a written element is not finite"))
    if flag:
        es.count("flag true")
    else:
        if nonfinite_ops:
            es.count("flag false: a non-finite operand")
        if any(k == "overflow" for k in kinds):
            es.count("flag false: finite operands, an overflow")
    return None


class ElementLine:
    """Element I of a map's line as a completed line of the map's step, its tokens as the map's
    line spells them (the step's operands from the scalars and the arrays, its outputs those
    written, or Z):

        STEP FORMAT OPERAND... #MAP:STRATUM:INDEX:element:I -> OUTPUT...

    It is the case that the statistics of the step's entries keep where the element attains an
    extreme (check.EntryStats): a few limbs, which run again as a line of the step, where the
    map's line holds thousands and would be kept once per distance of the profile.  Its text is
    made only when it is kept (str())."""

    __slots__ = ("step", "fname", "pl", "ins", "outs", "n", "i", "tag", "z")

    def __init__(self, step, fname, pl, ins, outs, n, i, tag, z=None):
        self.step, self.fname, self.pl, self.ins, self.outs = step, fname, pl, ins, outs
        self.n, self.i, self.tag, self.z = n, i, tag, z

    def __str__(self):
        pl, ins, n, i = self.pl, self.ins, self.n, self.i
        x = []
        for where, lo, l in pl.args:
            x.extend(ins[lo:lo + l] if where == "s" else
                     [ins[pl.n_scalar + k * n + i] for k in range(lo, lo + l)])
        z = self.z or [self.outs[j * n + i] for j in range(pl.W)]
        return "%s %s %s #%s:element:%d -> %s" % (self.step, self.fname, " ".join(x), self.tag,
                                                   i, " ".join(z))


def _map_tag(m, line):
    """The tag of a map's line, MAP:STRATUM:INDEX (the map's name and its own tag)."""
    last = line.partition(" -> ")[0].rsplit(" ", 1)[-1]
    return m.name + (":" + last[1:] if last.startswith("#") else "")


def judge_map_line(ck, line, lt, sep, right, tag):
    m = ck.claims.get_fold(lt[0])
    fname = lt[1] if len(lt) > 1 else "?"
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    pl = _plan(ck, m, fmt, MapPlan) if fmt is not None else None

    def extra(pl):
        k = m.step_kernel
        sp = pl.step
        return [("entries(%s), step %s: %s" % (m.written, k.name, e.label), e.kind,
                 sp.entries[i].get("source") if sp is not None else None)
                for i, e in enumerate(k.ensures)]
    st = _stats(ck, m, pl, fmt, fname, tag, extra)
    if pl is None:
        ck._fail(st, line, "unknown format %r" % fname if fmt is None else
                 "the claims of %s cannot be read" % m.name)
        return
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    if len(lt) < 4:
        ck._fail(st, line, "malformed: a map's request is MAP FORMAT ORDER N SCALAR... LIMB ...")
        return
    try:
        order = FO.parse_order(lt[2])
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
    if len(ins) != pl.n_scalar + n * pl.L or "" in ins:
        ck._fail(st, line, "malformed: %d input limbs, %d of scalars and %d elements of %d limbs "
                 "take %d" % (len(ins), pl.n_scalar, n, pl.L, pl.n_scalar + n * pl.L))
        return
    if len(outs) != n * pl.W + 1 or "" in outs:
        ck._fail(st, line, "malformed: %d results, the map writes %d and the flag"
                 % (len(outs), n * pl.W))
        return
    if order_name not in m.orders:
        ck._fail(st, line, "the map claims no %s order" % order_name)
        return
    if not pl.in_scope:
        st.c["out_of_scope"] += 1
        return
    vals = _parse_inputs(ck, st, line, fmt, ins)
    if vals is None:
        return
    sc = vals[:pl.n_scalar]
    cols = [vals[pl.n_scalar + j * n:pl.n_scalar + (j + 1) * n] for j in range(pl.L)]
    elems = list(zip(*cols)) if n else []
    for lo in pl.canon_s:
        if not XT.canonical(fmt, sc[lo:lo + 2]):
            ck._invalid(st, line, "requires canonical() of a scalar")
            return
    for lo in pl.pow2_s:
        v = sc[lo]
        if type(v) is not int or v <= 0 or v & (v - 1):
            ck._invalid(st, line, "requires power_of_two() of a scalar")
            return
    for lo in pl.canon_a:
        for i, x in enumerate(elems):
            if not XT.canonical(fmt, x[lo:lo + 2]):
                ck._invalid(st, line, "requires canonical(): element %d" % i)
                return
    got = _parse_outputs(ck, st, line, fmt, outs)
    if got is None:
        return
    zl, flag = got
    W = pl.W
    st.c["judged"] += 1
    es_e, es_f = st.entries[0], st.entries[1]
    if m.ensures[0]["kind"] != "entries":
        es_e, es_f = es_f, es_e
    sub = st.entries[2:]
    reasons, sus = [], []
    leads, kinds = [], []
    nonfinite_ops = False
    es_e.applicable += 1
    etag = _map_tag(m, line)
    for k in [FO.length_class(n)] + FO.order_classes(order, n):
        es_e.count(k)
    bad_e = []
    for i in range(n):
        x = []
        for where, lo, l in pl.args:
            x.extend(sc[lo:lo + l] if where == "s" else elems[i][lo:lo + l])
        z = [zl[j * n + i] for j in range(W)]
        fin = all(type(v) is int for v in x)
        lead = type(z[0]) is int
        leads.append(lead)
        if not fin:
            nonfinite_ops = True
        if lead:
            if not fin:
                kinds.append("bad")
                es_e.count("element: a non-finite operand, a finite result")
                bad_e.append("element %d is finite although an operand is not" % i)
                continue
            why = ck.violated(pl.step, x)
            if why:
                # The map's requirements give the step's on finite operands: a claims error.
                bad_e.append("element %d: its operands violate the step's %s" % (i, why))
                continue
            v = ck.verdict(pl.step, sub, x, z, ElementLine(m.step, fname, pl, ins, outs, n, i,
                                                           etag))
            if v[0] == "fail":
                bad_e.append("element %d: %s" % (i, v[1]))
            elif v[0] == "nonfinite":
                _k, _lead, beyond, _small = v
                bad_e.append("element %d: %s" % (i, "the step's exact result rounds beyond Omega, "
                                                 "and the written element is finite" if beyond
                                                 else "a finite leading limb with a lower limb "
                                                 "that is not finite"))
            else:
                kinds.append("finite")
                es_e.count("element: finite operands, finite result")
                bad_e.extend("element %d: %s" % (i, r) for r in v[1])
            continue
        # Not finite: the canonical NaN once the flag is false (the second pass).
        if not all(t == NAN for t in z):
            reasons.append("finite_or_nan: element %d is not finite, and not the canonical NaN"
                           % i)
        if fin:
            kinds.append("overflow")
            es_e.count("element: finite operands, not finite (an overflow)")
            nan = [NAN] * W
            v = ck.verdict(pl.step, sub, x, nan, ElementLine(m.step, fname, pl, ins, outs, n, i,
                                                             etag, nan))
            if v[0] == "nonfinite" and v[3]:
                sus.append("element %d is not finite although its operands and its exact value "
                           "are below Omega/4" % i)
        else:
            kinds.append("nonfinite")
            es_e.count("element: a non-finite operand")
    if bad_e:
        es_e.failures += 1
        reasons = ["entries: " + r for r in bad_e] + reasons
    why = _flag(es_f, flag, leads, kinds, nonfinite_ops)
    if why or any(r.startswith("finite_or_nan") for r in reasons):
        es_f.failures += 1
    if why:
        reasons.append("finite_or_nan: " + why)
    _finish(ck, st, line, reasons, sus)


# ---------------------------------------------------------------------------

class ConvPlan:
    def __init__(self, ck, c, fmt):
        self.c = c
        self.fmt = fmt
        self.in_scope = ck.ignore_min_precision or fmt.p >= c.min_precision
        self.dot = FO.FoldPlan(c.fold, fmt, ck.ignore_min_precision) if self.in_scope else None
        (nx, lx), (ny, ly) = c.arrays
        self.lx, self.ly = lx, ly
        self.W = c.wlimbs
        self.canon = [(0, lx) if n == nx else (lx, lx + ly) for n in c.requires]
        # The entries of the fold the coefficients satisfy: all but finite_or_nan.
        self.idx = [i for i, e in enumerate(c.fold.ensures) if e.kind != "finite_or_nan"]


def conv_terms(nx, ny, j):
    """The indices (i, j - i) of the terms of coefficient j, in increasing i."""
    return [(i, j - i) for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1)]


def judge_conv_line(ck, line, lt, sep, right, tag):
    c = ck.claims.get_fold(lt[0])
    fname = lt[1] if len(lt) > 1 else "?"
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    pl = _plan(ck, c, fmt, ConvPlan) if fmt is not None else None

    def extra(pl):
        return [("coefficients(%s), fold %s: %s" % (c.written, c.fold.name, c.fold.ensures[i].label),
                 c.fold.ensures[i].kind, pl.dot.entries[i].get("source") if pl.dot else None)
                for i in pl.idx]
    st = _stats(ck, c, pl, fmt, fname, tag, extra)
    if pl is None:
        ck._fail(st, line, "unknown format %r" % fname if fmt is None else
                 "the claims of %s cannot be read" % c.name)
        return
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    if len(lt) < 5:
        ck._fail(st, line, "malformed: a convolution's request is CONV FORMAT seq N_X N_Y LIMB ...")
        return
    if lt[2] != "seq":
        ck._fail(st, line, "a convolution has the sequential order only, not %r" % lt[2])
        return
    if not _COUNT_RE.match(lt[3]) or not _COUNT_RE.match(lt[4]):
        ck._fail(st, line, "malformed: lengths %r %r" % (lt[3], lt[4]))
        return
    nx, ny = int(lt[3]), int(lt[4])
    nz = nx + ny - 1 if nx and ny else 0
    ins = lt[5:]
    outs = right.split(" ")
    if len(ins) != nx * pl.lx + ny * pl.ly or "" in ins:
        ck._fail(st, line, "malformed: %d input limbs, arrays of %d and %d elements take %d"
                 % (len(ins), nx, ny, nx * pl.lx + ny * pl.ly))
        return
    if len(outs) != nz * pl.W + 1 or "" in outs:
        ck._fail(st, line, "malformed: %d results, the convolution writes %d coefficients of %d "
                 "limbs and the flag" % (len(outs), nz, pl.W))
        return
    if not pl.in_scope:
        st.c["out_of_scope"] += 1
        return
    vals = _parse_inputs(ck, st, line, fmt, ins)
    if vals is None:
        return
    xs = list(zip(*[vals[j * nx:(j + 1) * nx] for j in range(pl.lx)])) if nx else []
    base = nx * pl.lx
    ys = list(zip(*[vals[base + j * ny:base + (j + 1) * ny] for j in range(pl.ly)])) if ny else []
    for lo, hi in pl.canon:
        arr, off = (xs, 0) if lo == 0 else (ys, pl.lx)
        for i, e in enumerate(arr):
            if not XT.canonical(fmt, e[lo - off:hi - off]):
                ck._invalid(st, line, "requires canonical(): entry %d of %s" % (
                    i, "x" if lo == 0 else "y"))
                return
    got = _parse_outputs(ck, st, line, fmt, outs)
    if got is None:
        return
    zl, flag = got
    W = pl.W
    st.c["judged"] += 1
    es_c, es_f = st.entries[0], st.entries[1]
    if c.ensures[0]["kind"] != "coefficients":
        es_c, es_f = es_f, es_c
    sub = st.entries[2:]
    dot = pl.dot
    reasons, sus, bad = [], [], []
    leads, kinds = [], []
    nonfinite_ops = False
    es_c.applicable += 1
    for k in ("n_x = %d" % nx if nx <= 2 else "n_x above 2", "n_y = %d" % ny if ny <= 2 else
              "n_y above 2", "n_x = n_y" if nx == ny else "n_x != n_y",
              FO.length_class(min(nx, ny)).replace("length", "terms at most")):
        es_c.count(k)
    flag_slot = [i for i in range(dot.n_out) if i in dot.out_masks]
    for j in range(nz):
        terms = conv_terms(nx, ny, j)
        elems = [xs[i] + ys[k] for i, k in terms]
        z = [zl[t * nz + j] for t in range(W)]
        fin = all(type(v) is int for e in elems for v in e)
        lead = type(z[0]) is int
        leads.append(lead)
        if not fin:
            nonfinite_ops = True
        if lead:
            if not fin:
                kinds.append("bad")
                bad.append("coefficient %d is finite although a term is not" % j)
                continue
            if not all(type(v) is int for v in z):
                bad.append("coefficient %d: a finite leading limb with a lower limb that is not "
                           "finite" % j)
                continue
            kinds.append("finite")
            es_c.count("coefficient: finite terms, finite result")
            case = FO._Case(dot, elems, len(elems), None, "sequential", True)
            # The fold's outputs: the coefficient's limbs, and a true flag where the fold has one.
            zz = list(z) + [1] * len(flag_slot)
            for s_i, i in enumerate(pl.idx):
                e = dot.entries[i]
                es = sub[s_i]
                if e["kind"] == "normalized":
                    es.applicable += 1
                    w = []
                    for lo, hi in e["ranges"]:
                        w.extend(zz[lo:hi])
                    if not F.normalized_limbs(fmt, w):
                        es.failures += 1
                        bad.append("coefficient %d: not normalized" % j)
                elif e["kind"] == "fold_error":
                    why = FO._fold_error(dot, e, es, case, zz, line)
                    if why:
                        es.failures += 1
                        bad.append("coefficient %d: %s" % (j, why))
            continue
        if not all(t == NAN for t in z):
            reasons.append("finite_or_nan: coefficient %d is not finite, and not the canonical NaN"
                           % j)
        if fin:
            kinds.append("overflow")
            es_c.count("coefficient: finite terms, not finite (an overflow)")
            case = FO._Case(dot, elems, len(elems), None, "sequential", True)
            if FO._far(dot, case):
                sus.append("coefficient %d is not finite although every partial sum of its terms "
                           "is below an eighth of the overflow threshold" % j)
        else:
            kinds.append("nonfinite")
            es_c.count("coefficient: a non-finite term")
    if bad:
        es_c.failures += 1
        reasons = ["coefficients: " + r for r in bad] + reasons
    why = _flag(es_f, flag, leads, kinds, nonfinite_ops)
    if why or any(r.startswith("finite_or_nan") for r in reasons):
        es_f.failures += 1
    if why:
        reasons.append("finite_or_nan: " + why)
    _finish(ck, st, line, reasons, sus)
