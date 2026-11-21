"""Ball vectors: their claims and the judge of their completed lines.

architecture.md, "Ball vectors", "Claims of Milestone 2" (the list "folds" with "bv": true or
"bv_conv": true) and "The line protocol" (BV, BV_CONV, inplace=).  A BallVector is N centers and one
radius: the set of the vectors each of whose entries is within the radius of its center; canonical
when it is a finite ball vector (every center finite, normalized for two limbs, the radius finite
and nonnegative) or the whole space (every center zero, the radius +inf).

    encloses_entries (bv_add_k, bv_sub_k, bv_scale_k, bv_neg_k, bv_mul_pow2_k), for canonical
    operands:
      V1   the result is canonical;
      flag true exactly when the radius is finite;
      V2   entry by entry, every value of `set` over the balls of the operands' entries (every real
           for the whole space) and the other scalars is within the radius of the entry written;
      V3   if the result is a finite ball vector, every operand is one and every scalar is finite;
           and (architecture.md, "Ball vectors": the centers are the step's, the radius the radius
           kernel's on the largest magnitude) each center written satisfies the claims of the step
           on its entry, and the radius those of the radius kernel at m, the largest magnitude of a
           leading limb written, and the scalars;
      V4   from the precision finite_from: every operand a finite ball vector, every scalar finite,
           radii_when on the scalars and finite_when at every entry: the result is finite;
      exact (exact_when): where the result is finite and every condition holds, the result is
           exactly the set at every entry.
    makes_ball_vector (bv_make_k): the result canonical; the whole space exactly when the radius
    given is negative, a NaN or +inf, or the leading limb of a center given is not finite;
    otherwise the centers and the radius given, as values.
    encloses_coefficients (bv_conv_k): V1 of n_x + n_y - 1 coefficients; the flag; V2 coefficient
    by coefficient, the exact range of sum_i x_i y_{j-i} with every entry ranging over its ball;
    V3 a finite result has finite operands, coefficients that satisfy the claims of the fold of the
    convolution's coefficients on their terms, and a radius at least conv_radius's stated value at
    the maxima of the operands' leading limbs, the count and the smallest g and t its bound
    claims; V4 under count_when (an expression evaluated with n), radii_when and finite_when at
    every pair, every entry or once.

Lines:

    BV FORMAT ORDER N [inplace=I] SCALAR... LIMB... [#TAG] -> Z... R FLAG
    BV_CONV FORMAT seq N_X N_Y RX RY LIMB... [#TAG] -> Z... R FLAG
"""

import re
from fractions import Fraction

from . import cexpr as CX
from . import expr as EX
from . import extended as XT
from . import fmt as F
from . import folds as FO
from . import intervals as IV
from . import maps as MP
from .claims import ClaimsError, DOMAINS, EXACT_CONDITIONS, Format, eval_const, format_u_eta, _NAME

INF, NINF, NAN = F.POS_INF, F.NEG_INF, F.NAN
MASK_TEXT = FO.MASK_TEXT
BV_FIELDS = {"name", "bv", "domain", "arrays", "scalars", "writes", "outputs", "value", "requires",
             "ensures", "orders", "packed_lanes", "step", "step_args", "record", "exactness",
             "combine", "radius", "radius_args", "finish", "min_precision", "status", "theorem",
             "source"}
CONV_FIELDS = {"name", "bv_conv", "domain", "arrays", "scalars", "writes", "outputs", "value",
               "requires", "ensures", "orders", "centers", "records", "count", "bound", "radius",
               "radius_args", "finish", "min_precision", "status", "theorem", "source"}
_BV_REQ = re.compile(r"\s*ball_vector\(\s*(%s)\s*,\s*(%s)\s*\)\s*\Z" % (_NAME, _NAME))
_POW2 = re.compile(r"\s*power_of_two\(\s*(%s)\s*\)\s*\Z" % _NAME)
_CANON = re.compile(r"\s*canonical\(\s*(%s)\s*\)\s*\Z" % _NAME)
_INPLACE = re.compile(r"inplace=(0|[1-9][0-9]*)\Z")

# Statistics (the guards read them).
RES_FINITE = "result: finite ball vector"
RES_WHOLE = "result: whole space"
OP_WHOLE = "operands: a whole-space operand"
OP_SCALAR = "operands: a scalar not finite"
OP_FINITE = "operands: finite ball vectors, finite scalars"
V4_APPLIES = "V4 applies"
V4_EMPTY = "V4 applies, no entry"
V4_BELOW = "V4 not claimed: below finite_from"
V4_RANGE = "V4 not claimed: a format of no statement (e_max <= p, or eta above binary_float's)"
EXACT_HOLDS = "exact: every condition holds"
EXACT_FAILS = "exact_when fails: "
INPLACE = "in place: array %d"
SLACK = "slack in gaps of the radius (the worst entry)"
RATIO = "radius / the largest smallest enclosing radius"


# ---------------------------------------------------------------------------
# Reading

def _expr(nm, text, names, where, limbs=False, abs_ok=True):
    if not isinstance(text, str):
        raise ClaimsError("%s: %r is not an expression" % (where, text))
    try:
        tree = EX.parse(text, limbs=limbs)
    except EX.ExprError as ex:
        raise ClaimsError("%s: %s" % (where, ex))
    for n in EX.names(tree):
        if n not in names:
            raise ClaimsError("%s: %r is not a name of %s here" % (where, n, nm))
    if not abs_ok and EX.uses(tree, "abs"):
        raise ClaimsError("%s: abs() is not allowed here" % where)
    return tree


def _abs_le(nm, lst, names, where):
    """[(tree, text, E)] of a list of {"abs_le": EXPR, "exp": E}."""
    if not isinstance(lst, list):
        raise ClaimsError("%s must be a list" % where)
    out = []
    for j, c in enumerate(lst):
        w = "%s[%d]" % (where, j)
        if not isinstance(c, dict) or set(c) != {"abs_le", "exp"}:
            raise ClaimsError("%s must be {\"abs_le\": EXPR, \"exp\": E}, got %r" % (w, c))
        if not isinstance(c["exp"], int) or isinstance(c["exp"], bool):
            raise ClaimsError("%s: exp must be an integer" % w)
        out.append((_expr(nm, c["abs_le"], names, w), c["abs_le"].strip(), c["exp"]))
    return out


def _exact_conds(nm, lst, limbs, where):
    """[(tree, text, op, K)] of exact_when conditions over the arrays (their limbs NAME[I]) and the
    scalars."""
    if not isinstance(lst, list):
        raise ClaimsError("%s: exact_when must be a list" % where)
    out = []
    for j, c in enumerate(lst):
        w = "%s: exact_when[%d]" % (where, j)
        ops = [k for k in EXACT_CONDITIONS if isinstance(c, dict) and k in c]
        if len(ops) != 1 or set(c) != {ops[0], "than"}:
            raise ClaimsError("%s must be {\"zero_or_abs_gt\": EXPR, \"than\": K} or "
                              "{\"zero_or_abs_ge\": EXPR, \"than\": K}, got %r" % (w, c))
        tree = _expr(nm, c[ops[0]], limbs, w, limbs=True)
        for n, i in EX.limb_refs(tree):
            if i >= limbs[n]:
                raise ClaimsError("%s: %s[%d] is not a limb of %s, which has %d" % (
                    w, n, i, n, limbs[n]))
        u, eta = format_u_eta(Format(53, -1074, 971))
        if eval_const(c["than"], u, eta) <= 0:
            raise ClaimsError("%s: than %r is not positive" % (w, c["than"]))
        out.append((tree, c[ops[0]].strip(), ops[0], c["than"]))
    return out


def _common(obj, raw, claims, kind, flag_key):
    if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
        raise ClaimsError("%s without a name" % kind)
    nm = obj.name = raw["name"]
    obj.raw = raw
    obj.claims = claims
    if not re.fullmatch(_NAME, nm):
        raise ClaimsError("%s: not a name" % nm)
    if raw.get(flag_key) is not True:
        raise ClaimsError("%s: %s must be true" % (nm, flag_key))
    for other in ("bv", "bv_conv", "map", "conv"):
        if other != flag_key and other in raw:
            raise ClaimsError("%s: a %s has no field %s" % (nm, kind, other))
    obj.domain = raw.get("domain", "finite")
    if obj.domain not in DOMAINS or obj.domain != "extended":
        raise ClaimsError("%s: a %s of the %s domain, whose reading architecture.md does not give"
                          % (nm, kind, obj.domain))
    obj.extended = True
    obj.arrays, obj.roles = MP._groups(nm, raw.get("arrays"), "arrays")
    if not obj.arrays:
        raise ClaimsError("%s: arrays must be a nonempty list" % nm)
    obj.scalars, srole = MP._groups(nm, raw.get("scalars", []), "scalars")
    obj.roles.update(srole)
    writes, _ = MP._groups(nm, raw.get("writes"), "writes", roles=False)
    if len(writes) != 1:
        raise ClaimsError("%s: a %s writes one array, not %d" % (nm, kind, len(writes)))
    obj.written, obj.wlimbs = writes[0]
    outs = raw.get("outputs")
    if (not isinstance(outs, list) or len(outs) != 2 or not all(isinstance(o, dict) for o in outs)
            or set(outs[0]) - {"name", "limbs"} or outs[0].get("limbs") != 1
            or outs[1].get("type") != "mask" or set(outs[1]) - {"name", "limbs", "type"}
            or outs[1].get("limbs", 1) != 1):
        raise ClaimsError("%s: outputs must be the radius (one limb) and the flag (a mask), got %r"
                          % (nm, outs))
    obj.radius_name, obj.flag_name = outs[0]["name"], outs[1]["name"]
    names = ([n for n, _ in obj.arrays] + [n for n, _ in obj.scalars]
             + [obj.written, obj.radius_name, obj.flag_name])
    if len(set(names)) != len(names) or any(n in CX.RESERVED or n == "n" for n in names):
        raise ClaimsError("%s: the names of the arrays, scalars, written array and outputs must be "
                          "distinct, and none u, eta, n, unit or tiny" % nm)
    obj.limbs = dict(obj.scalars + obj.arrays)
    for n, l in obj.scalars:
        if l != 1:
            raise ClaimsError("%s: the scalar %s has %d limbs (a scalar of a ball vector is one)"
                              % (nm, n, l))
    if any(l != obj.wlimbs for _, l in obj.arrays):
        raise ClaimsError("%s: the arrays have other limbs than the array written" % nm)
    v = raw.get("value")
    obj.value_tree = _expr(nm, v, obj.limbs, "%s: value" % nm)
    obj.value_text = v.strip()
    obj.orders = raw.get("orders")
    if (not isinstance(obj.orders, list) or not obj.orders
            or len(set(map(str, obj.orders))) != len(obj.orders)
            or any(o not in FO.ORDERS for o in obj.orders)):
        raise ClaimsError("%s: orders must be a nonempty list of sequential and lanes, got %r"
                          % (nm, obj.orders))
    mp = raw.get("min_precision", 1)
    if not isinstance(mp, int) or isinstance(mp, bool) or mp < 1:
        raise ClaimsError("%s: min_precision must be an integer" % nm)
    obj.min_precision = mp
    obj.status = raw.get("status")
    if obj.status not in FO.STATUSES:
        raise ClaimsError("%s: status must be proved or unverified, got %r" % (nm, obj.status))
    th = raw.get("theorem")
    if th is not None and not isinstance(th, dict):
        raise ClaimsError("%s: theorem must be an object or null" % nm)
    # Requirements: ball_vector(ARRAY, SCALAR) of each array (a stored one-limb scalar its radius),
    # power_of_two(SCALAR) of a one-limb scalar, canonical(ARRAY) of an array of two limbs (the
    # constructor).
    reqs = raw.get("requires", [])
    if not isinstance(reqs, list):
        raise ClaimsError("%s: requires must be a list" % nm)
    obj.bvs, obj.pow2, obj.canonical = [], [], []
    sc = dict(obj.scalars)
    for r in reqs:
        m = _BV_REQ.match(r) if isinstance(r, str) else None
        m2 = _POW2.match(r) if isinstance(r, str) else None
        m3 = _CANON.match(r) if isinstance(r, str) else None
        if m and m.group(1) in dict(obj.arrays) and m.group(2) in sc:
            if any(m.group(1) == a or m.group(2) == b for a, b in obj.bvs):
                raise ClaimsError("%s: requirement %r shares an array or a radius with another"
                                  % (nm, r))
            if obj.roles[m.group(2)] != "stored":
                raise ClaimsError("%s: requirement %r: the radius of a BallVector is stored"
                                  % (nm, r))
            obj.bvs.append((m.group(1), m.group(2)))
        elif m2 and m2.group(1) in sc:
            if m2.group(1) in obj.pow2:
                raise ClaimsError("%s: requirement %r listed twice" % (nm, r))
            obj.pow2.append(m2.group(1))
        elif m3 and m3.group(1) in dict(obj.arrays) and obj.limbs[m3.group(1)] >= 2:
            if m3.group(1) in obj.canonical:
                raise ClaimsError("%s: requirement %r listed twice" % (nm, r))
            obj.canonical.append(m3.group(1))
        else:
            raise ClaimsError("%s: requirement %r is outside the vocabulary of a %s "
                              "(ball_vector(ARRAY, RADIUS), power_of_two(SCALAR), canonical(ARRAY) "
                              "of a constructor)" % (nm, r, kind))
    if set(obj.pow2) & {b for _a, b in obj.bvs}:
        raise ClaimsError("%s: a radius required power_of_two()" % nm)
    obj.radii = {b for _a, b in obj.bvs}
    obj.warnings = []


def _parts(obj, raw, fields):
    """The parts, for reading: kernels (and folds) of the claims by name."""
    nm = obj.name
    for f in fields:
        v = raw.get(f)
        vs = v if isinstance(v, list) else [v]
        for x in vs:
            if not isinstance(x, str) or (x not in obj.claims.kernel_names
                                          and x not in obj.claims.folds):
                raise ClaimsError("%s: %s %r is not a kernel of the claims" % (nm, f, x))


class Entry:
    def __init__(self, kind, label):
        self.kind = kind
        self.label = label


class BallVector:
    """A fold with "bv": true: encloses_entries, or makes_ball_vector (the constructor)."""

    def __init__(self, raw, claims):
        _common(self, raw, claims, "ball vector", "bv")
        nm = self.name
        ens = raw.get("ensures")
        if not isinstance(ens, list) or len(ens) != 1 or not isinstance(ens[0], dict):
            raise ClaimsError("%s: ensures must be one entry, encloses_entries or "
                              "makes_ball_vector, got %r" % (nm, ens))
        e = ens[0]
        self.kind = e.get("kind")
        where = "%s: ensures entry 0 (%s)" % (nm, self.kind)
        if self.kind == "encloses_entries":
            self._read_encloses(e, where)
        elif self.kind == "makes_ball_vector":
            self._read_makes(e, where)
        else:
            raise ClaimsError("%s: unknown kind (a ball vector has encloses_entries or "
                              "makes_ball_vector)" % where)
        self.packed_lanes = MP._packed(nm, raw.get("packed_lanes", {}))
        _parts(self, raw, ("step", "record", "combine", "radius", "finish"))
        if "lanes" in self.orders and "combine" not in raw:
            raise ClaimsError("%s: the lane order needs a combination" % nm)
        sa, ra = raw.get("step_args"), raw.get("radius_args")
        # The step's operands: every array once, and scalars that are not radii (the radius given
        # of a constructor is not the step's either).
        given = {self.from_radius} if self.kind == "makes_ball_vector" else set()
        others = {n for n, _ in self.scalars} - self.radii - given
        if (not isinstance(sa, list) or len(set(map(str, sa))) != len(sa)
                or not {n for n, _ in self.arrays} <= set(sa) <= {n for n, _ in self.arrays} | others):
            raise ClaimsError("%s: step_args must name every array once and scalars that are not "
                              "radii, got %r" % (nm, sa))
        self.step_args = list(sa)
        self.exactness = raw.get("exactness")
        if self.exactness is not None and (not isinstance(self.exactness, dict)
                                           or set(self.exactness) != {"mask", "state"}):
            raise ClaimsError("%s: exactness must be {\"mask\": E, \"state\": EX}, got %r"
                              % (nm, self.exactness))
        if (not isinstance(ra, list) or not ra or ra[0] != "m"
                or any(not isinstance(x, str) for x in ra)):
            raise ClaimsError("%s: radius_args must be m, then scalars, got %r" % (nm, ra))
        rest = ra[1:]
        if self.exactness is not None:
            if rest[:1] != [self.exactness["state"]]:
                raise ClaimsError("%s: radius_args must be m, the state's mask %s, then scalars"
                                  % (nm, self.exactness["state"]))
            rest = rest[1:]
        if any(x not in dict(self.scalars) for x in rest):
            raise ClaimsError("%s: radius_args must be m, then scalars, got %r" % (nm, ra))
        self.radius_args = list(ra)
        self.step = raw.get("step")
        self.radius = raw.get("radius")
        self.unknown_fields = sorted(set(raw) - BV_FIELDS)
        self.entry_labels = [Entry(self.kind, self.label)]

    def _read_encloses(self, e, where):
        nm = self.name
        need = {"kind", "center", "radius", "flag", "set", "balls", "finite_when"}
        allowed = need | {"radii_when", "finite_from", "exact_when"}
        if set(e) - allowed or need - set(e):
            raise ClaimsError("%s: fields must be %s (and radii_when, finite_from, exact_when), got "
                              "%s" % (where, ", ".join(sorted(need)), sorted(e)))
        if not self.bvs or {a for a, _b in self.bvs} != {n for n, _ in self.arrays}:
            raise ClaimsError("%s: every array is the centers of a BallVector (ball_vector())"
                              % where)
        self._outputs(e, where)
        balls = e["balls"]
        if not isinstance(balls, dict) or not balls:
            raise ClaimsError("%s: balls must be a nonempty object" % where)
        self.balls = {}
        for b, spec in balls.items():
            if (not re.fullmatch(_NAME, b) or b in EX.FUNCTIONS or not isinstance(spec, dict)
                    or set(spec) != {"center", "radius"}
                    or (b in self.limbs and b != spec.get("center"))):
                raise ClaimsError("%s: ball %r must be {center, radius}, its name no array's or "
                                  "scalar's but its own center's" % (where, b))
            if (spec["center"], spec["radius"]) not in self.bvs:
                raise ClaimsError("%s: ball %s over (%s, %s) has no requirement ball_vector(%s, %s)"
                                  % (where, b, spec["center"], spec["radius"], spec["center"],
                                     spec["radius"]))
            self.balls[b] = (spec["center"], spec["radius"])
        if len(self.balls) != len(self.bvs):
            raise ClaimsError("%s: one ball per array" % where)
        names = set(self.balls) | {n for n in dict(self.scalars) if n not in self.radii}
        self.set_tree = _expr(nm, e["set"], names, "%s: set" % where, abs_ok=False)
        self.set_text = e["set"].strip()
        used = EX.names(self.set_tree)
        for b in self.balls:
            if used.count(b) != 1:
                raise ClaimsError("%s: ball %s must occur exactly once in set" % (where, b))
        # The set is the value over the balls: the value with each array for its ball.
        ren = {c: b for b, (c, _r) in self.balls.items()}
        if not MP._same_value(self.value_tree, self.set_tree, {n: ren.get(n, n)
                                                               for n in EX.names(self.value_tree)}):
            raise ClaimsError("%s: set %r is not the value %r over the balls" % (
                where, self.set_text, self.value_text))
        self.finite_when = _abs_le(nm, e["finite_when"], self.limbs, "%s: finite_when" % where)
        if self.finite_when:
            if "radii_when" not in e:
                raise ClaimsError("%s: radii_when is written exactly when finite_when is not empty"
                                  % where)
            self.radii_when = _abs_le(nm, e["radii_when"], dict(self.scalars),
                                      "%s: radii_when" % where)
            if not self.radii_when:
                raise ClaimsError("%s: radii_when is empty" % where)
        elif "radii_when" in e:
            raise ClaimsError("%s: radii_when is written exactly when finite_when is not empty"
                              % where)
        else:
            self.radii_when = []
        self.finite_from = self.min_precision
        if "finite_from" in e:
            ff = e["finite_from"]
            if not isinstance(ff, int) or isinstance(ff, bool) or ff <= self.min_precision:
                raise ClaimsError("%s: finite_from must be an integer above min_precision %d, got "
                                  "%r" % (where, self.min_precision, ff))
            self.finite_from = ff
        self.exact_when = None
        if "exact_when" in e:
            self.exact_when = _exact_conds(nm, e["exact_when"], self.limbs, where)
        arrays = {n for n, _ in self.arrays}
        self.entry_conds = [c for c in (self.exact_when or [])
                            if set(EX.names(c[0])) | {n for n, _i in EX.limb_refs(c[0])} & arrays
                            and (set(EX.names(c[0])) | {n for n, _i in EX.limb_refs(c[0])})
                            & arrays]
        self.scalar_conds = [c for c in (self.exact_when or []) if c not in self.entry_conds]
        self.label = "encloses_entries(%s, %s) %s over %s, V1-V4, flag %s, finite when %s%s" % (
            self.written, self.radius_name, self.set_text, ", ".join(
                "%s=[%s +- %s]" % (b, c, r) for b, (c, r) in self.balls.items()),
            self.flag_name, " and ".join("|%s| <= 2^(qmax+p%+d)" % (t, x) for _tr, t, x in
                                         self.finite_when) or "nothing",
            "" if self.exact_when is None else ", exactly the set" + (
                " when %s" % " and ".join("(%s = 0 or |%s| %s %s)" % (
                    t, t, ">" if op == "zero_or_abs_gt" else ">=", k)
                    for _tr, t, op, k in self.exact_when) if self.exact_when else ""))

    def _outputs(self, e, where):
        if e.get("center") != self.written:
            raise ClaimsError("%s: center must name the array written, %s" % (where, self.written))
        if e.get("radius") != self.radius_name:
            raise ClaimsError("%s: radius must name the output %s" % (where, self.radius_name))
        if e.get("flag") != self.flag_name:
            raise ClaimsError("%s: flag must name the mask output %s" % (where, self.flag_name))

    def _read_makes(self, e, where):
        if set(e) != {"kind", "center", "radius", "flag", "from"}:
            raise ClaimsError("%s: fields must be kind, center, radius, flag and from, got %s"
                              % (where, sorted(e)))
        self._outputs(e, where)
        fr = e["from"]
        if not isinstance(fr, dict) or set(fr) != {"center", "radius"}:
            raise ClaimsError("%s: from must be {\"center\": ARRAY, \"radius\": SCALAR}" % where)
        if len(self.arrays) != 1 or fr["center"] != self.arrays[0][0]:
            raise ClaimsError("%s: from center must name the one array" % where)
        if len(self.scalars) != 1 or fr["radius"] != self.scalars[0][0]:
            raise ClaimsError("%s: from radius must name the one scalar" % where)
        if self.bvs or self.pow2:
            raise ClaimsError("%s: a constructor requires no ball_vector() or power_of_two()" % where)
        two = [n for n, l in self.arrays if l >= 2]
        if sorted(two) != sorted(self.canonical):
            raise ClaimsError("%s: a constructor of two limbs requires canonical() of its centers, "
                              "and of one limb nothing" % where)
        self.from_center, self.from_radius = fr["center"], fr["radius"]
        self.finite_when, self.radii_when, self.exact_when = [], [], None
        self.finite_from = self.min_precision
        self.label = "makes_ball_vector(%s, %s) from centers %s, radius %s, flag %s" % (
            self.written, self.radius_name, self.from_center, self.from_radius, self.flag_name)


class BvConv:
    """A fold with "bv_conv": true, the product of two BallVectors: encloses_coefficients."""

    def __init__(self, raw, claims):
        _common(self, raw, claims, "product of BallVectors", "bv_conv")
        # The units of count_when's unit( ) and tiny( ) (count_edge, the generator's count stratum).
        self.unit_tiny = claims.unit_tiny
        nm = self.name
        if len(self.arrays) != 2 or len(self.scalars) != 2 or len(self.bvs) != 2:
            raise ClaimsError("%s: a product of BallVectors has two arrays, each with its radius"
                              % nm)
        if self.orders != ["sequential"]:
            raise ClaimsError("%s: a product of BallVectors has the sequential order only" % nm)
        ens = raw.get("ensures")
        if not isinstance(ens, list) or len(ens) != 1 or not isinstance(ens[0], dict):
            raise ClaimsError("%s: ensures must be one encloses_coefficients entry" % nm)
        e = ens[0]
        where = "%s: ensures entry 0 (%s)" % (nm, e.get("kind"))
        if e.get("kind") != "encloses_coefficients":
            raise ClaimsError("%s: unknown kind (a product of BallVectors has "
                              "encloses_coefficients)" % where)
        need = {"kind", "center", "radius", "flag", "set", "balls"}
        triple = {"finite_when", "radii_when", "count_when"}
        if set(e) - need - triple or need - set(e) or (set(e) & triple and set(e) & triple != triple):
            raise ClaimsError("%s: fields must be %s, and finite_when, radii_when and count_when "
                              "together or none, got %s" % (where, ", ".join(sorted(need)),
                                                            sorted(e)))
        BallVector._outputs(self, e, where)
        balls = e["balls"]
        if not isinstance(balls, dict) or len(balls) != 2:
            raise ClaimsError("%s: balls must name the two BallVectors" % where)
        self.balls = {}
        for b, spec in balls.items():
            if (not re.fullmatch(_NAME, b) or not isinstance(spec, dict)
                    or set(spec) != {"center", "radius"}
                    or (spec["center"], spec["radius"]) not in self.bvs
                    or (b in self.limbs and b != spec["center"])):
                raise ClaimsError("%s: ball %r must be {center, radius} of a ball_vector()"
                                  % (where, b))
            self.balls[b] = (spec["center"], spec["radius"])
        if len({c for c, _r in self.balls.values()}) != 2:
            raise ClaimsError("%s: one ball per array" % where)
        self.set_tree = _expr(nm, e["set"], set(self.balls), "%s: set" % where, abs_ok=False)
        self.set_text = e["set"].strip()
        t = self.set_tree
        if not (t[0] == "*" and t[1][0] == "name" and t[2][0] == "name"
                and {t[1][1], t[2][1]} == set(self.balls)):
            raise ClaimsError("%s: set must be the product of the two balls, got %r"
                              % (where, self.set_text))
        # The ball of the first array first (the order of the terms x_i y_{j-i}).
        first = next(b for b, (c, _r) in self.balls.items() if c == self.arrays[0][0])
        self.ball_order = [first, next(b for b in self.balls if b != first)]
        ren = {c: b for b, (c, _r) in self.balls.items()}
        if not MP._same_value(self.value_tree, self.set_tree, {n: ren.get(n, n)
                                                               for n in EX.names(self.value_tree)}):
            raise ClaimsError("%s: set %r is not the value %r over the balls"
                              % (where, self.set_text, self.value_text))
        names = dict(self.limbs)
        names["n"] = 1
        self.finite_when = _abs_le(nm, e.get("finite_when", []), names, "%s: finite_when" % where)
        self.radii_when = _abs_le(nm, e.get("radii_when", []), dict(self.scalars),
                                  "%s: radii_when" % where)
        self.count_when = []
        cw = e.get("count_when", [])
        if not isinstance(cw, list):
            raise ClaimsError("%s: count_when must be a list" % where)
        for j, c in enumerate(cw):
            w = "%s: count_when[%d]" % (where, j)
            if not isinstance(c, dict) or set(c) != {"le", "than"}:
                raise ClaimsError("%s must be {\"le\": EXPR, \"than\": K}, got %r" % (w, c))
            try:
                tree = CX.parse(c["le"])
                kt = CX.parse(c["than"])
            except CX.CExprError as ex:
                raise ClaimsError("%s: %s" % (w, ex))
            if any(n != "n" for n in CX.names(tree)) or CX.names(kt) or CX.calls(kt):
                raise ClaimsError("%s: EXPR is over n, u, eta, integers, unit( ), tiny( ); K a "
                                  "constant" % w)
            for _f, kn in CX.calls(tree):
                claims.check_unit_kernel(kn, w)
            k = CX.evaluate(kt, {"u": Fraction(1, 2), "eta": Fraction(1), "names": {}})
            if k <= 0:
                raise ClaimsError("%s: than is not positive" % w)
            self.count_when.append((tree, kt, str(c["le"]).strip(), str(c["than"]).strip()))
        if self.finite_when and not self.radii_when:
            raise ClaimsError("%s: radii_when is empty" % where)
        self.finite_from = self.min_precision
        self.exact_when = None
        _parts(self, raw, ("records", "bound", "radius", "finish"))
        cn = raw.get("centers")
        cf = claims.folds.get(cn) if isinstance(cn, str) else None
        if not isinstance(cf, MP.Conv):
            raise ClaimsError("%s: centers %r is not a readable convolution of the claims%s" % (
                nm, cn, " (%s)" % claims.broken[cn] if isinstance(cn, str) and cn in claims.broken
                else ""))
        if [l for _n, l in cf.arrays] != [l for _n, l in self.arrays] or cf.wlimbs != self.wlimbs:
            raise ClaimsError("%s: the convolution %s has other arrays than the product" % (nm, cn))
        if raw.get("count") != "min(n_x,n_y)":
            raise ClaimsError("%s: count must be min(n_x,n_y), got %r" % (nm, raw.get("count")))
        self.conv = cf
        self.radius = raw.get("radius")
        self.bound = raw.get("bound")
        self.radius_args = raw.get("radius_args")
        self.unknown_fields = sorted(set(raw) - CONV_FIELDS)
        self.label = ("encloses_coefficients(%s, %s) %s over %s, V1-V4, flag %s" % (
            self.written, self.radius_name, self.set_text, ", ".join(
                "%s=[%s +- %s]" % (b, c, r) for b, (c, r) in self.balls.items()), self.flag_name))
        self.entry_labels = [Entry("encloses_coefficients", self.label)]


# ---------------------------------------------------------------------------
# Judging

def _array_names(tree, arrays):
    return (set(EX.names(tree)) | {n for n, _i in EX.limb_refs(tree)}) & arrays


class BVPlan:
    """What the judge of a ball vector needs about one (fold, format)."""

    def __init__(self, ck, f, fmt):
        self.f = f
        self.fmt = fmt
        q = fmt.qmin
        self.in_scope = ck.ignore_min_precision or fmt.p >= f.min_precision
        self.T = fmt.qmax + fmt.p
        self.ns = len(f.scalars)
        self.L = sum(l for _, l in f.arrays)
        self.W = f.wlimbs
        # An operand vector: the scalars, then the limbs of one entry of each array.
        self.pos = {}
        k = 0
        for n, _l in f.scalars:
            self.pos[n] = (k, k + 1)
            k += 1
        for n, l in f.arrays:
            self.pos[n] = (k, k + l)
            k += l
        self.arrays = {n for n, _ in f.arrays}
        self.radius_slot = {r: self.pos[r][0] for _a, r in f.bvs}
        self.balls = [(b, self.pos[c], self.pos[r][0]) for b, (c, r) in f.balls.items()] \
            if hasattr(f, "balls") else []
        self.others = [n for n, _ in f.scalars if n not in f.radii]
        self.fw = [self._condition(t, e) for t, _x, e in f.finite_when]
        self.fw_text = [x for _t, x, _e in f.finite_when]
        self.rw = [self._condition(t, e) for t, _x, e in f.radii_when]
        self.exact = None
        self.entry_conds, self.scalar_conds = [], []
        if f.exact_when is not None and self.in_scope:
            for tree, text, op, kk in f.exact_when:
                h = (self._exact(tree, op, kk), "%s = 0 or |%s| %s %s" % (
                    text, text, ">" if op == "zero_or_abs_gt" else ">=", kk))
                (self.entry_conds if _array_names(tree, self.arrays) else
                 self.scalar_conds).append(h)
        self.v4 = fmt.p >= f.finite_from
        self.v4_range = v4_range(fmt)
        # V3: the step and the radius kernel (their plans), where the fold has them.
        self.step = self.radius = None
        if self.in_scope and f.kind == "encloses_entries":
            self.step = ck.plan(f.step, fmt.name)
            self.radius = ck.plan(f.radius, fmt.name)
            if self.step is None or self.radius is None:
                raise ClaimsError("%s: the plans of the step %s and the radius %s in %s cannot be "
                                  "made (a step of the finite domain and a radius kernel of the "
                                  "claims)" % (f.name, f.step, f.radius, fmt.name))
            sk = ck.claims.get(f.step)
            if [l for _n, l in sk.inputs if _n not in sk.masks] != [
                    f.limbs[n] for n in f.step_args]:
                raise ClaimsError("%s: the step %s does not take step_args" % (f.name, f.step))
            self.step_args = [self.pos[n] for n in f.step_args]
            self.step_masks = [i for i, (n, _l) in enumerate(sk.outputs) if n in sk.masks]
            # The mask the step returns beside the center (bv_mul_pow2_step_k): its exact_flag.
            self.step_flag = None
            for i, e in enumerate(sk.ensures):
                if getattr(e, "exact_flag", None):
                    self.step_flag = i
            rk = ck.claims.get(f.radius)
            if not all(getattr(e, "bv", False) or (e.kind == "rounded" and e.mode == "nearest"
                                                   and getattr(e, "own_tree", None) is None)
                       for e in rk.ensures):
                raise ClaimsError("%s: the radius %s claims neither upper with a value nor a "
                                  "rounding to nearest" % (f.name, f.radius))
            self.rargs = f.radius_args

    def _leaf(self, name):
        if isinstance(name, tuple):
            n, i = name
            return "x[%d]" % (self.pos[n][0] + i), self.fmt.qmin
        lo, hi = self.pos[name]
        return "(%s)" % "+".join("x[%d]" % i for i in range(lo, hi)), self.fmt.qmin

    def _condition(self, tree, e):
        src, s = EX.compile_tree(tree, self._leaf)
        fn = EX.make_function(["x"], src)
        k = self.T + e - s
        if k >= 0:
            lim = 1 << k
            return lambda x: abs(fn(x)) <= lim
        return lambda x: (abs(fn(x)) << -k) <= 1

    def _exact(self, tree, op, kk):
        src, s = EX.compile_tree(tree, self._leaf)
        fn = EX.make_function(["x"], src)
        u, eta = format_u_eta(self.fmt)
        K = eval_const(kk, u, eta)
        if K <= 0:
            raise ClaimsError("%s: exact_when: than %r is not positive in %s" % (
                self.f.name, kk, self.fmt.name))
        n, d = K.numerator, K.denominator
        ls, rs = (s, 0) if s >= 0 else (0, -s)
        strict = op == "zero_or_abs_gt"

        def holds(x):
            v = fn(x)
            if v == 0:
                return True
            a, b = (abs(v) * d) << ls, n << rs
            return a > b if strict else a >= b
        return holds

    def set_range(self, x, states, c, r):
        """(lo, hi, c, r) of the set at one entry (operand vector x), with the center c and the
        radius r written (fixed values), all four at one scale, exactly; a bound infinite for an
        operand that is the whole space."""
        q = self.fmt.qmin
        env = {}
        for b, (lo, hi), ri in self.balls:
            if states[b] == "whole":
                env[b] = (NINF, INF, q)
            else:
                cb = sum(x[lo:hi])
                env[b] = (cb - x[ri], cb + x[ri], q)
        for n in self.others:
            v = x[self.pos[n][0]]
            if type(v) is not int:
                return None
            env[n] = (v, v, q)
        lo, hi, s = IV.range_eval(self.f.set_tree, env)
        t = min(s, q)

        def at(v, w):
            return v << (w - t) if type(v) is int else v
        return at(lo, s), at(hi, s), at(c, q), at(r, q), 1 << (q - t)


def _plan(ck, f, fmt, cls):
    key = ("fold", f.name, fmt.name)
    pl = ck.plans.get(key)
    if pl is None and key not in ck.plans:
        try:
            pl = cls(ck, f, fmt)
        except ClaimsError as ex:
            ck.claims.mark_broken(f.name, str(ex))
            ck.claims.folds.pop(f.name, None)
            if str(ex) not in ck.summary.claims_errors:
                ck.summary.claims_errors.append(str(ex))
        ck.plans[key] = pl
    return pl


def _stats(ck, f, pl, fmt, fname, tag):
    st = ck.summary.stats((f.name, fmt.name if fmt else fname, tag), fmt.p if fmt else None)
    if pl is not None and not st.entries:
        from .check import EntryStats
        st.entries = [EntryStats(e.label, e.kind) for e in f.entry_labels]
        for label, kind, source in _extra(pl):
            st.entries.append(EntryStats(label, kind))
            st.entries[-1].bound_source = source
    st.c["cases"] += 1
    return st


def _extra(pl):
    """The statistics entries of V3's parts: the step's entries, the radius kernel's (a ball
    vector), the fold of the coefficients' (a product)."""
    out = []
    if getattr(pl, "step", None) is not None:
        k = pl.step.kernel
        out += [("V3, step %s: %s" % (k.name, e.label), e.kind, pl.step.entries[i].get("source"))
                for i, e in enumerate(k.ensures)]
    if getattr(pl, "radius", None) is not None:
        k = pl.radius.kernel
        out += [("V3, radius %s: %s" % (k.name, e.label), e.kind, None) for e in k.ensures]
    if getattr(pl, "dot", None) is not None:
        fo = pl.f.conv.fold
        out += [("V3, coefficients, fold %s: %s" % (fo.name, fo.ensures[i].label),
                 fo.ensures[i].kind, pl.dot.entries[i].get("source")) for i in pl.idx]
    return out


def _state(fmt, entries, r):
    """The state of a BallVector given as its entries (limb tuples) and its radius: 'finite',
    'whole', or None (not canonical)."""
    if type(r) is int:
        if r < 0:
            return None
        for e in entries:
            if not all(type(v) is int for v in e):
                return None
            if len(e) > 1 and not F.normalized_limbs(fmt, list(e)):
                return None
        return "finite"
    if r == INF and all(v == 0 for e in entries for v in e):
        return "whole"
    return None


def _read_tokens(ck, st, line, fmt, toks):
    vals = MP._parse_inputs(ck, st, line, fmt, toks)
    return vals


def _parse_out(ck, st, line, fmt, outs):
    """The limbs written, the radius and the flag; None when the line was counted as failed."""
    if outs[-1] not in MASK_TEXT:
        ck._fail(st, line, "mask output %r is not 0 or 1" % outs[-1])
        return None
    try:
        z = [F.parse_limb(fmt, t) for t in outs[:-1]]
    except F.LimbError as ex:
        ck._fail(st, line, "output limb malformed: %s" % ex)
        return None
    for v in z:
        if v == F.OUTSIDE or (type(v) is int and not F.is_member(fmt, v)):
            ck._fail(st, line, "output limb not a number of the format")
            return None
    return z[:-1], z[-1], MASK_TEXT[outs[-1]]


class _Failer:
    """fail(statement, why): counted once per line under "failed STATEMENT"."""

    def __init__(self, es):
        self.es = es
        self.seen = set()
        self.reasons = []

    def __call__(self, stmt, why):
        if stmt not in self.seen:
            self.seen.add(stmt)
            self.es.count("failed " + stmt)
        self.reasons.append("%s: %s" % (stmt, why))


def count_edge(f, fmt, largest):
    """The largest count n <= largest for which every condition of count_when of the product f
    holds in fmt (0 for none; largest when it holds of every count up to it): the conditions grow
    with n."""
    u, eta = format_u_eta(fmt)
    env = {"u": u, "eta": eta, "unit": lambda k: f.unit_tiny(k, fmt)[0],
           "tiny": lambda k: f.unit_tiny(k, fmt)[1]}

    def holds(n):
        e = dict(env, names={"n": Fraction(n)})
        return all(CX.evaluate(t, e) <= CX.evaluate(kt, e) for t, kt, _a, _b in f.count_when)
    if holds(largest):
        return largest
    lo, hi = 0, largest
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if holds(mid):
            lo = mid
        else:
            hi = mid
    return lo


def v4_range(fmt):
    """V4 is judged in the formats its statements quantify over (architecture.md, "From which
    precision each clause holds": binary_float prec emax, which asks p < emax, emax Flocq's, the
    finite numbers below 2^emax = 2^(q_max + p), and whose smallest positive number is
    eta = 2^(3 - emax - p)), and in those of a wider subnormal range: q_max >= 1 and
    q_min <= 3 - q_max - 2p.  Elsewhere the smallest normal number, eta/(2u), a constant of every
    radius kernel, is too close to Omega (fp:2:-1:0, fp:2:-1:1: oracle/README.md, "Ball vectors
    and the accumulator"), and nothing is claimed."""
    return fmt.qmax >= 1 and fmt.qmin <= 3 - fmt.qmax - 2 * fmt.p


def v4_beyond(fmt):
    """The text a failure of V4 carries in a format of a wider subnormal range than binary_float's
    (q_min below 3 - q_max - 2p), where V4 is judged and nothing is proved: by the owner's ruling
    of 2026-11-21 (architecture.md, "The formats of the statements") a failure there is a finding
    to report, not a violated claim."""
    if fmt.qmax >= 1 and fmt.qmin < 3 - fmt.qmax - 2 * fmt.p:
        return (" (in a format of a wider subnormal range than binary_float's, where nothing is "
                "proved: a finding to report, not a violated claim)")
    return ""


def judge_bv_line(ck, line, lt, sep, right, tag):
    """BV FORMAT ORDER N [inplace=I] SCALAR... LIMB... [#TAG] -> Z... R FLAG."""
    f = ck.claims.get_fold(lt[0])
    fname = lt[1] if len(lt) > 1 else "?"
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    pl = _plan(ck, f, fmt, BVPlan) if fmt is not None else None
    st = _stats(ck, f, pl, fmt, fname, tag)
    if pl is None:
        ck._fail(st, line, "unknown format %r" % fname if fmt is None else
                 "the claims of %s cannot be read" % f.name)
        return
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    if len(lt) < 4:
        ck._fail(st, line, "malformed: a ball vector's request is BV FORMAT ORDER N SCALAR... LIMB...")
        return
    try:
        order = FO.parse_order(lt[2])
    except ValueError:
        ck._fail(st, line, "malformed: order %r (seq or lanes:W)" % lt[2])
        return
    if not MP._COUNT_RE.match(lt[3]):
        ck._fail(st, line, "malformed: length %r" % lt[3])
        return
    n = int(lt[3])
    ins = lt[4:]
    inplace = None
    if ins and ins[0].startswith("inplace="):
        m = _INPLACE.match(ins[0])
        if m is None or int(m.group(1)) >= len(f.arrays) or f.arrays[int(m.group(1))][1] != f.wlimbs:
            ck._fail(st, line, "malformed: %s names no array read of the limbs of the array "
                     "written" % ins[0])
            return
        inplace = int(m.group(1))
        ins = ins[1:]
    order_name = "sequential" if order is None else "lanes"
    outs = right.split(" ")
    if len(ins) != pl.ns + n * pl.L or "" in ins:
        ck._fail(st, line, "malformed: %d input limbs, %d scalars and %d entries of %d limbs take %d"
                 % (len(ins), pl.ns, n, pl.L, pl.ns + n * pl.L))
        return
    if len(outs) != n * pl.W + 2 or "" in outs:
        ck._fail(st, line, "malformed: %d results, the ball vector writes %d, the radius and the "
                 "flag" % (len(outs), n * pl.W))
        return
    if order_name not in f.orders:
        ck._fail(st, line, "the ball vector claims no %s order" % order_name)
        return
    if not pl.in_scope:
        st.c["out_of_scope"] += 1
        return
    vals = MP._parse_inputs(ck, st, line, fmt, ins)
    if vals is None:
        return
    sc = vals[:pl.ns]
    cols = [vals[pl.ns + j * n:pl.ns + (j + 1) * n] for j in range(pl.L)]
    elems = [tuple(sc) + e for e in zip(*cols)] if n else []
    if f.kind == "makes_ball_vector":
        for lo, hi in [pl.pos[c] for c in f.canonical]:
            for i, x in enumerate(elems):
                if not XT.canonical(fmt, list(x[lo:hi])):
                    ck._invalid(st, line, "requires canonical(): entry %d" % i)
                    return
    else:
        states = {}
        for b, (c, r) in f.balls.items():
            lo, hi = pl.pos[c]
            s = _state(fmt, [x[lo:hi] for x in elems], sc[pl.pos[r][0]])
            if s is None:
                ck._invalid(st, line, "requires ball_vector(%s, %s)" % (c, r))
                return
            states[b] = s
    for name in f.pow2:
        v = sc[pl.pos[name][0]]
        if type(v) is not int or v <= 0 or v & (v - 1):
            ck._invalid(st, line, "requires power_of_two(%s)" % name)
            return
    got = _parse_out(ck, st, line, fmt, outs)
    if got is None:
        return
    zl, r, flag = got
    W = pl.W
    zs = [tuple(zl[t * n + i] for t in range(W)) for i in range(n)]
    st.c["judged"] += 1
    es = st.entries[0]
    es.applicable += 1
    for k in [FO.length_class(n)] + FO.order_classes(order, n):
        es.count(k)
    if inplace is not None:
        es.count(INPLACE % inplace)
    fail = _Failer(es)
    sus = []
    # V1: canonical; the flag.
    res = _state(fmt, zs, r)
    if res is None:
        fail("V1", "the result is neither a finite ball vector nor the whole space (radius %s)"
             % (F.fixed_hex(fmt, r) if type(r) is int else r))
    else:
        es.count(RES_FINITE if res == "finite" else RES_WHOLE)
    if flag != (1 if type(r) is int else 0):
        fail("flag", "the flag is %d although the radius is %s" % (
            flag, "finite" if type(r) is int else F.fixed_hex(fmt, r)))
    if f.kind == "makes_ball_vector":
        _makes(pl, es, fail, sc, elems, zs, r, res, line)
    else:
        _encloses(ck, pl, es, fail, sc, elems, zs, r, res, states, line, sus, st, ins, outs, n, tag)
    if fail.reasons:
        es.failures += 1
    MP._finish(ck, st, line, fail.reasons, sus)


def _makes(pl, es, fail, sc, elems, zs, r, res, line):
    """makes_ball_vector: the whole space exactly when the radius given is negative, a NaN or
    +inf, or the leading limb of a center given is not finite; otherwise the centers and the radius
    given, as values."""
    f = pl.f
    fmt = pl.fmt
    rg = sc[pl.pos[f.from_radius][0]]
    lo, hi = pl.pos[f.from_center]
    tok = line.partition(" -> ")[0].split(" ")
    nonfin = any(type(x[lo]) is not int for x in elems)
    rcls = ("NaN" if rg == NAN else "+inf" if rg == INF else "-inf" if rg == NINF else
            "negative" if rg < 0 else "positive" if rg > 0 else "zero")
    if rcls == "zero":
        # The sign of a zero radius, read from the line's text (the parser drops it).
        i = 4 + (1 if len(tok) > 4 and tok[4].startswith("inplace=") else 0)
        rcls = "-0" if tok[i].startswith("-") else "+0"
    es.count("given radius %s, centers %s" % (rcls, "not all finite" if nonfin else "finite"))
    whole = rg == NAN or rg == INF or rg == NINF or (type(rg) is int and rg < 0) or nonfin
    if whole:
        if res != "whole":
            fail("makes_ball_vector", "the result is not the whole space although %s" % (
                "a center given is not finite" if nonfin else "the radius given is %s" % rcls))
        return
    if res != "finite":
        fail("makes_ball_vector", "the result is not the finite ball vector of the centers and "
             "the radius given")
        return
    if r != rg:
        fail("makes_ball_vector", "the radius is not the radius given")
    for i, (x, z) in enumerate(zip(elems, zs)):
        if list(z) != list(x[lo:hi]):
            fail("makes_ball_vector", "entry %d is not the center given" % i)
            break


def _encloses(ck, pl, es, fail, sc, elems, zs, r, res, states, line, sus, st, ins, outs, n, tag):
    f = pl.f
    fmt = pl.fmt
    q = fmt.qmin
    whole_op = any(s == "whole" for s in states.values())
    # The scalars that are not radii (a radius belongs to its operand's state).
    scal_fin = all(type(sc[pl.pos[n][0]]) is int for n in pl.others)
    if whole_op:
        es.count(OP_WHOLE)
    if not scal_fin:
        es.count(OP_SCALAR)
    if not whole_op and scal_fin:
        es.count(OP_FINITE)
    finite = res == "finite"
    # V3: a finite result from finite ball vectors and finite scalars.
    if finite and (whole_op or not scal_fin):
        fail("V3", "the result is finite although %s" % ("an operand is the whole space"
                                                         if whole_op else "a scalar is not finite"))
    # V2: containment, entry by entry.
    worst = None
    if finite:
        for i, x in enumerate(elems):
            if not scal_fin:
                fail("V2", "entry %d: the set's values are not real numbers (a scalar is not "
                     "finite), and the result is finite" % i)
                break
            lo, hi, c, rr, k = pl.set_range(x, states, sum(zs[i]), r)
            if type(lo) is not int or type(hi) is not int:
                fail("V2", "entry %d: the set is unbounded, and the result is finite" % i)
                break
            rmin = max(c - lo, hi - c)
            if rmin > rr:
                fail("V2", "entry %d: the set is not within the radius" % i)
                break
            # The worst entry: the smallest slack, in gaps of the radius (at the scale of r).
            g = (F.gap_below(fmt, r) if r else 1) * k
            if worst is None or (rr - rmin) * worst[1] < worst[0] * g:
                worst = (rr - rmin, g, rr, rmin)
        if worst is not None and not fail.reasons:
            es.track_min(SLACK, (worst[0], worst[1]), line)
            if worst[3]:
                es.track_max(RATIO, (worst[2], worst[3]), line)
    # V3: the centers are the step's, the radius the radius kernel's at the largest magnitude.
    if finite and not whole_op and scal_fin and pl.step is not None:
        _v3_parts(ck, pl, es, fail, sc, elems, zs, r, line, st, ins, outs, n, tag)
    # V4: finite under the conditions, from finite_from.
    if f.finite_when and not whole_op and scal_fin:
        if not pl.v4_range:
            es.count(V4_RANGE)
        elif not pl.v4:
            es.count(V4_BELOW)
        elif all(h(tuple(sc) + (0,) * pl.L) for h in pl.rw) and all(
                h(x) for x in elems for h in pl.fw):
            es.count(V4_APPLIES)
            if not elems:
                es.count(V4_EMPTY)
            if not finite:
                fail("V4", "every operand is a finite ball vector, every scalar finite, every "
                     "condition holds (%s), and the result is the whole space%s"
                     % (" and ".join(pl.fw_text), v4_beyond(fmt)))
    # Exactness: where the operands and the result are finite and every condition holds.
    if f.exact_when is not None and finite and not whole_op and scal_fin:
        failing = [t for h, t in pl.scalar_conds if not h(tuple(sc) + (0,) * pl.L)]
        for x in elems:
            failing += [t for h, t in pl.entry_conds if not h(x) and t not in failing]
        for t in failing:
            es.count(EXACT_FAILS + t)
        if not failing and elems:
            es.count(EXACT_HOLDS)
            for i, x in enumerate(elems):
                lo, hi, c, rr, _k = pl.set_range(x, states, sum(zs[i]), r)
                if c - rr != lo or c + rr != hi:
                    fail("exact", "entry %d: the ball written is not exactly the set" % i)
                    break


def _v3_parts(ck, pl, es, fail, sc, elems, zs, r, line, st, ins, outs, n, tag):
    """Each center written satisfies the step's claims on its entry; the radius the radius
    kernel's at m, the largest magnitude of a leading limb written (+0 for none), and the
    scalars (and ex, the and of the step's masks, for a scaling)."""
    f = pl.f
    fmt = pl.fmt
    sp = pl.step
    nk = len(sp.kernel.ensures)
    sub = st.entries[1:1 + nk]
    sub_r = st.entries[1 + nk:]
    etag = MP._map_tag(f, line)
    ex = True
    for i, x in enumerate(elems):
        xs = []
        for lo, hi in pl.step_args:
            xs.extend(x[lo:hi])
        z = list(zs[i])
        if pl.step_flag is not None:
            e = all(h(xs) for h, _t in sp.entries[pl.step_flag]["exact"])
            ex = ex and e
            z.append(1 if e else 0)
        el = _ElementLine(f.step, fmt.name, xs, z, etag, i, sp.out_masks)
        if sp.ext is not None:
            # A step of the extended domain (neg_2): on finite operands and a finite center, the
            # entries of the finite domain's kinds (represents is then the exact error).
            if not all(type(t) is int for t in z):
                fail("V3", "entry %d: a lower limb of the center is not finite" % i)
                continue
            only = {j for j, e in enumerate(sp.kernel.ensures) if e.kind in (
                "normalized", "error", "leading_rounded", "rounded")}
            for w in ck._judge(sp, sub, xs, z, sp.value_fn(xs), {}, el, only=only):
                fail("V3", "entry %d: the step: %s" % (i, w))
            continue
        why = ck.violated(sp, xs)
        if why:
            fail("V3", "entry %d: its operands violate the step's %s" % (i, why))
            continue
        v = ck.verdict(sp, sub, xs, z, el)
        if v[0] == "fail":
            fail("V3", "entry %d: %s" % (i, v[1]))
        elif v[0] == "nonfinite":
            fail("V3", "entry %d: the step's exact result is beyond Omega and the center written "
                 "is finite" % i)
        else:
            for w in v[1]:
                fail("V3", "entry %d: the step: %s" % (i, w))
    m = max((abs(z[0]) for z in zs), default=0)
    rk = pl.radius
    xr = []
    for a in pl.rargs:
        if a == "m":
            xr.append(m)
        elif f.exactness is not None and a == f.exactness["state"]:
            xr.append(1 if ex else 0)
        else:
            xr.append(sc[pl.pos[a][0]])
    from . import bvec as BV
    for w in BV.radius_reasons(rk, sub_r, xr, [r], line):
        fail("V3", "the radius: %s" % w)


class _ElementLine:
    """An entry of a ball vector's line as a line of its step (the cases of the step's statistics:
    a few limbs, not the fold's line)."""

    __slots__ = ("step", "fname", "xs", "z", "tag", "i", "masks")

    def __init__(self, step, fname, xs, z, tag, i, masks):
        self.step, self.fname, self.xs, self.z, self.tag, self.i = step, fname, xs, z, tag, i
        self.masks = masks

    def __str__(self):
        fmt = F.parse_format(self.fname)

        def h(v):
            return F.fixed_hex(fmt, v) if type(v) is int else v
        return "%s %s %s #%s:entry:%d -> %s" % (self.step, self.fname, " ".join(
            h(v) for v in self.xs), self.tag, self.i, " ".join(
            str(v) if k in self.masks else h(v) for k, v in enumerate(self.z)))


# ---------------------------------------------------------------------------
# The products of two BallVectors

class ConvPlan:
    def __init__(self, ck, f, fmt):
        self.f = f
        self.fmt = fmt
        q = fmt.qmin
        self.in_scope = ck.ignore_min_precision or fmt.p >= f.min_precision
        self.T = fmt.qmax + fmt.p
        (nx, lx), (ny, ly) = f.arrays
        self.lx, self.ly = lx, ly
        self.W = f.wlimbs
        self.rx, self.ry = f.scalars[0][0], f.scalars[1][0]
        self.bx = next(r for c, r in f.bvs if c == nx)
        self.by = next(r for c, r in f.bvs if c == ny)
        # The operand vector of a pair: the scalars, the limbs of x_i, those of y_k, then n.
        self.pos = {f.scalars[0][0]: (0, 1), f.scalars[1][0]: (1, 2), nx: (2, 2 + lx),
                    ny: (2 + lx, 2 + lx + ly)}
        self.npos = 2 + lx + ly
        self.fw = []
        for tree, text, e in f.finite_when:
            names = set(EX.names(tree))
            which = ("pair" if {nx, ny} <= names else "x" if nx in names else
                     "y" if ny in names else "once")
            self.fw.append((which, self._condition(tree, e), text))
        self.rw = [self._condition(t, e) for t, _x, e in f.radii_when]
        self.dot = FO.FoldPlan(f.conv.fold, fmt, ck.ignore_min_precision) if self.in_scope else None
        self.idx = [i for i, e in enumerate(f.conv.fold.ensures) if e.kind != "finite_or_nan"]
        self.u, self.eta = format_u_eta(fmt)
        self.claims = ck.claims
        # V3's radius: the stated value of the radius kernel (one upper with a value), with the
        # smallest g and t the bound claims (its upper entries' values, nondecreasing in m).
        self.rk = ck.claims.get(f.radius)
        self.bk = ck.claims.get(f.bound)
        if self.rk is None or self.bk is None or len(self.rk.ensures) != 1 or not getattr(
                self.rk.ensures[0], "bv", False):
            raise ClaimsError("%s: the radius %s (one upper with a value) or the bound %s is not a "
                              "readable kernel" % (f.name, f.radius, f.bound))
        self.rargs = list(f.radius_args or [])
        if len(self.rargs) != len(self.rk.inputs):
            raise ClaimsError("%s: radius_args are not the inputs of %s" % (f.name, f.radius))
        outs = [n for n, _ in self.bk.outputs if n not in self.bk.masks]
        self.bound_values = {}
        for e in self.bk.ensures:
            if e.kind == "upper" and e.cond is not None and e.of[0] in outs:
                self.bound_values[e.of[0]] = e.cvalue

    def _condition(self, tree, e):
        def leaf(name):
            if name == "n":
                return "x[%d]" % self.npos, 0
            lo, hi = self.pos[name]
            return "(%s)" % "+".join("x[%d]" % i for i in range(lo, hi)), self.fmt.qmin
        src, s = EX.compile_tree(tree, leaf)
        fn = EX.make_function(["x"], src)
        k = self.T + e - s
        if k >= 0:
            lim = 1 << k
            return lambda x: abs(fn(x)) <= lim
        return lambda x: (abs(fn(x)) << -k) <= 1

    def env(self, names):
        claims, fmt = self.claims, self.fmt
        return {"u": self.u, "eta": self.eta, "names": names,
                "unit": lambda k: claims.unit_tiny(k, fmt)[0],
                "tiny": lambda k: claims.unit_tiny(k, fmt)[1]}


def judge_bvconv_line(ck, line, lt, sep, right, tag):
    """BV_CONV FORMAT seq N_X N_Y RX RY LIMB... [#TAG] -> Z... R FLAG."""
    f = ck.claims.get_fold(lt[0])
    fname = lt[1] if len(lt) > 1 else "?"
    try:
        fmt = F.parse_format(fname)
    except F.FormatError:
        fmt = None
    pl = _plan(ck, f, fmt, ConvPlan) if fmt is not None else None
    st = _stats(ck, f, pl, fmt, fname, tag)
    if pl is None:
        ck._fail(st, line, "unknown format %r" % fname if fmt is None else
                 "the claims of %s cannot be read" % f.name)
        return
    if not sep:
        ck._fail(st, line, "malformed: no ' -> ' (the runner did not complete the line)")
        return
    if len(lt) < 7:
        ck._fail(st, line, "malformed: a product's request is BV_CONV FORMAT seq N_X N_Y RX RY LIMB...")
        return
    if lt[2] != "seq":
        ck._fail(st, line, "a product of BallVectors has the sequential order only, not %r" % lt[2])
        return
    if not MP._COUNT_RE.match(lt[3]) or not MP._COUNT_RE.match(lt[4]):
        ck._fail(st, line, "malformed: lengths %r %r" % (lt[3], lt[4]))
        return
    nx, ny = int(lt[3]), int(lt[4])
    nz = nx + ny - 1 if nx and ny else 0
    ins = lt[5:]
    outs = right.split(" ")
    if len(ins) != 2 + nx * pl.lx + ny * pl.ly or "" in ins:
        ck._fail(st, line, "malformed: %d input limbs, two radii and arrays of %d and %d entries "
                 "take %d" % (len(ins), nx, ny, 2 + nx * pl.lx + ny * pl.ly))
        return
    if len(outs) != nz * pl.W + 2 or "" in outs:
        ck._fail(st, line, "malformed: %d results, the product writes %d coefficients of %d limbs, "
                 "the radius and the flag" % (len(outs), nz, pl.W))
        return
    if not pl.in_scope:
        st.c["out_of_scope"] += 1
        return
    vals = MP._parse_inputs(ck, st, line, fmt, ins)
    if vals is None:
        return
    rx, ry = vals[0], vals[1]
    base = 2
    xs = list(zip(*[vals[base + j * nx:base + (j + 1) * nx] for j in range(pl.lx)])) if nx else []
    base += nx * pl.lx
    ys = list(zip(*[vals[base + j * ny:base + (j + 1) * ny] for j in range(pl.ly)])) if ny else []
    sx = _state(fmt, xs, rx)
    sy = _state(fmt, ys, ry)
    if sx is None or sy is None:
        ck._invalid(st, line, "requires ball_vector(%s, %s)" % (
            (f.arrays[0][0], pl.rx) if sx is None else (f.arrays[1][0], pl.ry)))
        return
    got = _parse_out(ck, st, line, fmt, outs)
    if got is None:
        return
    zl, r, flag = got
    W = pl.W
    zs = [tuple(zl[t * nz + j] for t in range(W)) for j in range(nz)]
    st.c["judged"] += 1
    es = st.entries[0]
    es.applicable += 1
    for k in ("n_x = %d" % nx if nx <= 2 else "n_x above 2", "n_y = %d" % ny if ny <= 2 else
              "n_y above 2", "n_x = n_y" if nx == ny else "n_x != n_y",
              FO.length_class(min(nx, ny)).replace("length", "terms at most")):
        es.count(k)
    fail = _Failer(es)
    sus = []
    res = _state(fmt, zs, r)
    if res is None:
        fail("V1", "the result is neither a finite ball vector nor the whole space")
    else:
        es.count(RES_FINITE if res == "finite" else RES_WHOLE)
    if flag != (1 if type(r) is int else 0):
        fail("flag", "the flag is %d although the radius is %s" % (
            flag, "finite" if type(r) is int else F.fixed_hex(fmt, r)))
    whole = "whole" in (sx, sy)
    es.count(OP_WHOLE if whole else OP_FINITE)
    finite = res == "finite"
    q = fmt.qmin
    if finite and whole:
        fail("V3", "the result is finite although an operand is the whole space")
    # V2: coefficient by coefficient, the exact range of the sum of the products.
    if finite:
        bx, by = f.ball_order
        for j in range(nz):
            lo = hi = 0
            s = 2 * q
            for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1):
                env = {}
                for b, e, st_, rr in ((bx, xs[i], sx, rx), (by, ys[j - i], sy, ry)):
                    if st_ == "whole":
                        env[b] = (NINF, INF, q)
                    else:
                        env[b] = (sum(e) - rr, sum(e) + rr, q)
                a, b2, s2 = IV.range_eval(f.set_tree, env)
                lo, hi = IV._xadd(lo, a), IV._xadd(hi, b2)
            if type(lo) is not int or type(hi) is not int:
                fail("V2", "coefficient %d: the set is unbounded, and the result is finite" % j)
                break
            # The products at scale 2q, the coefficient and the radius at q: both at min(q, 2q).
            if q < 0:
                c, rr = sum(zs[j]) << -q, r << -q
            else:
                c, rr = sum(zs[j]), r
                lo, hi = lo << q, hi << q
            if max(c - lo, hi - c) > rr:
                fail("V2", "coefficient %d: the set is not within the radius" % j)
                break
    # V3: the coefficients are the fold's on their terms; the radius conv_radius's at the maxima.
    if finite and not whole:
        _conv_v3(ck, pl, es, fail, st, xs, ys, zs, rx, ry, r, nx, ny, nz, line)
    # V4.
    if f.finite_when and not whole and not v4_range(fmt):
        es.count(V4_RANGE)
    elif f.finite_when and not whole:
        n = min(nx, ny)
        cw = True
        for tree, kt, text, ktext in f.count_when:
            env = pl.env({"n": Fraction(n)})
            if CX.evaluate(tree, env) > CX.evaluate(kt, env):
                cw = False
                es.count("count_when fails: %s <= %s" % (text, ktext))
        holds = cw and all(h((rx, ry) + (0,) * (pl.lx + pl.ly) + (n,)) for h in pl.rw)
        for which, h, _t in pl.fw:
            if not holds:
                break
            if which == "pair":
                holds = all(h((rx, ry) + x + y + (n,)) for x in xs for y in ys)
            elif which == "x":
                holds = all(h((rx, ry) + x + (0,) * pl.ly + (n,)) for x in xs)
            elif which == "y":
                holds = all(h((rx, ry) + (0,) * pl.lx + y + (n,)) for y in ys)
            else:
                holds = h((rx, ry) + (0,) * (pl.lx + pl.ly) + (n,))
        if holds:
            es.count(V4_APPLIES)
            if not nx or not ny:
                es.count(V4_EMPTY)
            if not finite:
                fail("V4", "both operands are finite ball vectors, count_when, radii_when and "
                     "finite_when hold, and the result is the whole space" + v4_beyond(fmt))
    if fail.reasons:
        es.failures += 1
    MP._finish(ck, st, line, fail.reasons, sus)


def _conv_v3(ck, pl, es, fail, st, xs, ys, zs, rx, ry, r, nx, ny, nz, line):
    f, fmt, dot = pl.f, pl.fmt, pl.dot
    sub = st.entries[1:1 + len(pl.idx)]
    flag_slot = [i for i in range(dot.n_out) if i in dot.out_masks]
    for j in range(nz):
        terms = [(i, j - i) for i in range(max(0, j - ny + 1), min(j, nx - 1) + 1)]
        elems = [xs[i] + ys[k] for i, k in terms]
        case = FO._Case(dot, elems, len(elems), None, "sequential", True)
        zz = list(zs[j]) + [1] * len(flag_slot)
        for s_i, i in enumerate(pl.idx):
            e = dot.entries[i]
            es2 = sub[s_i]
            if e["kind"] == "normalized":
                es2.applicable += 1
                w = []
                for lo, hi in e["ranges"]:
                    w.extend(zz[lo:hi])
                if not F.normalized_limbs(fmt, w):
                    es2.failures += 1
                    fail("V3", "coefficient %d: not normalized" % j)
            elif e["kind"] == "fold_error":
                why = FO._fold_error(dot, e, es2, case, zz, line)
                if why:
                    es2.failures += 1
                    fail("V3", "coefficient %d: %s" % (j, why))
    # The radius: at least conv_radius's stated value at the maxima, the count rounded up and the
    # smallest g and t of the bound's claims.
    q = fmt.qmin
    eta = pl.eta
    n = min(nx, ny)
    mfix = F.rdir(fmt, n, 0, True) if n else 0
    if type(mfix) is not int or mfix > fmt.omega:
        es.count("V3: the count beyond Omega")
        return
    names = {"m": mfix * eta, "ma": max((abs(x[0]) for x in xs), default=0) * eta,
             "mb": max((abs(y[0]) for y in ys), default=0) * eta}
    bnames = {pl.bk.inputs[0][0]: names["m"]}
    try:
        for out in ("g", "t"):
            if out in pl.bound_values:
                bnames[out] = CX.evaluate(pl.bound_values[out], pl.env(dict(bnames)))
            else:
                bnames[out] = Fraction(0)
    except CX.CExprError:
        es.count("V3: the bound's stated values do not exist")
        return
    env = {}
    for a, (inp, _l) in zip(pl.rargs, pl.rk.inputs):
        if a in names:
            env[inp] = names[a]
        elif a == pl.rx or a == pl.ry:
            env[inp] = (rx if a == pl.rx else ry) * eta
        elif a in bnames:
            env[inp] = bnames[a]
        else:
            env[inp] = bnames.get(a, Fraction(0))
    v = CX.evaluate(pl.rk.ensures[0].cvalue, pl.env(env))
    es.count("V3: the radius at least conv_radius's stated value" if r * eta >= v else
             "V3: the radius below conv_radius's stated value")
    if r * eta < v:
        fail("V3", "the radius is below the stated value of %s at the maxima, the count and the "
             "bound" % f.radius)
