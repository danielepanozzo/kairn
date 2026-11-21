"""The kernel IR: operations, kernels, the description format, and flattening.

A kernel is a straight-line program in static single assignment form over two kinds of values,
limbs (numbers of the format) and masks (docs/developer/architecture.md, "The kernel IR"). Each
kernel is described in one file, gen/kernels/NAME.kernel:

    # comment
    kernel:        NAME
    input:         x = x0 x1          a group and its limbs, most significant first
    input:         a                  a one-limb group: the limb has the group's name
    input:         mask m             a mask: one value, true or false
    input:         stored rx          entry kernels: a one-limb input that is a limb of an object
    input:         supplied y = h l   entry kernels: a multi-limb input whose limbs the program gives
    output:        z = z0 z1          (outputs likewise)
    value:         x+y                the exact real function the output approximates: names,
                                      + - *, unary minus, abs( ), parentheses
    requires:      normalized x       or: abs_ge a b, power_of_two c, nonneg r
    requires:      canonical x        (domain extended) or: ball cx rx
    requires:      count m            m is zero or at least 1 (a number of terms or additions)
    requires:      format half        the format contains 1/2 (eta <= 1/2)
    ensures:       normalized z       or: leading_rounded z
    ensures:       error z R c=3/(1-4*u) k=2 t=0 [when=product_large] [exact_when=CONDITIONS]
                                      the form: R, relative to |value|; A, to the sum of the
                                      magnitudes of the inputs; T, to the sum of the magnitudes of
                                      the terms of value (s+x*y: |s| + |x*y|)
    ensures:       rounded t down [when=product_large]
                                      the mode: nearest, down or up
    ensures:       rounded b nearest value=a+abs(x[0])
                                      of a value of its own (as in value, and NAME[I] limb I of an
                                      input) instead of the kernel's
    ensures:       upper r gaps=2
    ensures:       upper g value=m*unit(add_2_2)/(1-m*unit(add_2_2)) if=ok
                                      the value of the entry (an exact expression over the inputs,
                                      the one-limb outputs, u, eta, unit(K), tiny(K)) is at most the
                                      output whenever the mask output ok is true; no gaps: nothing
                                      is said of how far above
    ensures:       upper rz value=rx*c+eta unless=ex
                                      the same when the mask input ex is false
    ensures:       upper rz value=rx*c exact_when=mask(ex);zero_or_abs_gt(rx*c,eta/(2*u))
                                      and the output is the value exactly when the mask input ex
                                      is true and the other conditions hold
    ensures:       error z R c=0 k=1 t=1/2 exact_when=zero_or_abs_gt(x*c,eta/(2*u)) exact_flag=e
                                      the mask output e is true exactly when the conditions of
                                      exact_when hold
    ensures:       holds le m*unit(add_2_2) 1/2 if=ok
                                      the relation lt, le or eq between two such expressions, when
                                      the mask ok is true
    ensures:       finite_or_nan r flag=f
                                      the finish of a fold: f is true exactly when limb 0 of the
                                      value is finite, and r is then the value, limb for limb;
                                      otherwise every limb of r is a NaN
    ensures:       finite_or_nan r flag=f if=ok steps=1
                                      the finish of a fold of maxima: the same of the value stepped
                                      up that many times (steps, 0 when left out), and f false, r
                                      a NaN, when the mask input ok is false
    ensures:       maximum r m abs(x[0])
                                      the one-limb output is the larger of the exact values of the
                                      two expressions (as in value, and NAME[I] limb I of an input)
    ensures:       neighbor r up      the next number of the format above (down: below) the value
    ensures:       bound r below steps=1
                                      on that side of the value (below or above), and at most
                                      that many steps beyond its directed rounding
    ensures:       predicate m lt x y the relation lt, le or eq between two expressions
    ensures:       encloses cz rz x+y x=cx,rx y=cy,ry [finite_when=CONDITIONS] [exact_when=CONDITIONS]
                                      center, radius, the set, and each ball's center and radius
    ensures:       extends w core=add_2_2 lead=add [finite_when=abs_le(x,-2);abs_le(y,-2)]
                                      a full kernel: its core, the operation of T on the leading
                                      limbs, and the conditions under which the output is finite
    ensures:       represents x       a constructor: the output is the value, canonical
    ensures:       makes_ball cw rw from=c,r
                                      a constructor of a ball: center and radius outputs, from
                                      the center and radius inputs
    ensures:       makes_ball cw rw from_interval=lo,hi [midpoint_when=half_in_format(lo);...]
                                      a ball from the bounds of an interval (Milestone 2)
    requires:      interval xl xu     the bounds of a canonical interval; or: not_nan a
    ensures:       makes_interval zl zu from=lo,hi
    ensures:       encloses_interval zl zu x+y x=xl,xu y=yl,yu tight=rounded [exact_lower=...]
                   [exact_upper=...] [bounded_when=abs_le(x+y,omega)] [bounded_exactly]
                                      I1 to I5 of an interval kernel; tight is exact, rounded
                                      [;steps=N][;when=product_large], or outward;rel=EXPR;abs=EXPR
    ensures:       set_bound l below x x=c,r [tight=rounded]
                                      a bound of a set, as a number of T
    ensures:       outward l below rel=EXPR abs=EXPR [exact_when=zero(x+y)]
                                      on that side of the value, within rel |value| + abs; EXPR
                                      may name a constant up(EXPR) as the format rounds it
    ensures:       bound d below steps=1 zero_factor
                                      zero_factor: a zero operand gives zero (0 times inf is 0);
                                      also on outward (extended domain: mul_ext_2_2) and as the
                                      last word of encloses_interval (an operand [0, 0] gives [0, 0])
    ensures:       interval_set zl zu union x=xl,xu y=yl,yu
                                      the hull (union) or the intersection of two intervals, exact
    ensures:       ball_of_interval m r from=xl,xu special=ieee1788 rel=u abs=eta [smallest_radius]
                                      a ball made from an interval: special is ieee1788 (the mid and
                                      rad of IEEE 1788) or ball (a canonical ball)
    ensures:       interval_of_ball zl zu x x=c,r tight=rounded
                                      an interval that encloses a ball
    ensures:       splits al au bl bu from=xl,xu
                                      two intervals that together are the interval split
    ensures:       certain m lt 0 x x=xl,xu [exact | exact_when=abs_le(EXPR,omega)]
                                      a predicate of sets (intervals or balls, as the requirements
                                      say): the mask is true only if the relation holds (lt, le,
                                      eq of every choice of members, or member, subset, equal,
                                      interior, disjoint, empty, entire); exact: and whenever it
                                      holds
    ensures:       trit yes no lt x y x=xl,xu y=yl,yu [exact | exact_when=...]
                                      a three-valued comparison: yes only if the relation holds for
                                      every choice of members, no only if it fails for every one
    ensures:       ball_set cz rz union x=cx,rx y=cy,ry
                                      a ball that contains the union (or intersection) of two balls
    ensures:       ball_splits ca ra cb rb from=c,r
                                      two balls, the first containing [c - r, c], the second
                                      [c, c + r]
    ensures:       ball_of_interval m r from=xl,xu ... finite_when=abs_le(xl,-2);abs_le(xu,-2)
                                      the radius may be +inf for a bounded interval, and is finite
                                      under the conditions (two limbs)
    ensures:       interval_of_ball zl zu x x=c,r tight=outward;rel=EXPR;abs=EXPR
                   [exact_lower=zero(c-r)] [exact_upper=zero(c+r)] [bounded_when=abs_le(x,-2)]
                                      an interval of two limbs that encloses a ball
    ensures:       makes_ball cw rw from_interval=lo,hi rel=u abs=eta [smallest_radius]
                                      the center near the midpoint and the smallest radius
    min_precision: 3                  optional
    theorem:       proofs/theories/Add22.v add_2_2_correct
    source:        free text
    license:       free text
    status:        unverified         or: proved
    domain:        extended           optional (default finite): operands may be infinite or NaN
    ieee_status:   unverified         the domain extended only: the IEEE-model statement's status
    ieee_theorem:  FILE NAME          the domain extended only, once that statement is proved
    entry:         yes                optional: the public headers may call it (rule R3)
    ieee_only:     yes                optional: no real-model statement (a full Ball kernel; the
                                      other full kernels and the constructors are recognized
                                      by their claims)
    ieee:          bridge spec        optional, the finite domain only: the IEEE-model statements
                                      of the kernel (proofs/gen/IeeeStatements.v): `spec`, its
                                      claims for finite operands and a finite output limb 0;
                                      `bridge`, that every value it computes is then finite and
                                      its outputs are the real model's
    ieee_bridge_theorem: FILE K_ieee_bridge   the finite domain only, once K_ieee_bridge_spec is
                                      proved (with `ieee: bridge`)
    ieee_spec_theorem: FILE K_ieee_correct    likewise for K_ieee_spec (with `ieee: spec`)
    ieee_lead_theorem: FILE K_ieee_lead       likewise for K_ieee_lead_spec of
                                      proofs/gen/IeeeFoldStatements.v (a step or a combination
                                      of a fold); a statement whose theorem is not named is
                                      unverified
    ieee_finite:   abs_le(x0,-2);abs_le(y0,-2)
                                      optional, the finite domain only: conditions as in
                                      finite_when (over input names and limb names) under which
                                      every value the kernel computes is finite
    ieee_finite_result: abs_le(x+y,-2)
                                      optional: another such set of conditions
    guard_pending: a free text       optional: an entry kernel's input that is not guarded yet,
                                      and why (rule R3)
    ce_variant:    KERNEL             optional: its constant-evaluation variant
    cone_exempt:   free text          optional: why rule 4 cannot hold, and what stands in for it
    ordinary_inline: free text        optional: the C++ is an ordinary inline function, not forced
                                      inline though it has at most two limbs, and why
    unused:        x1 free text       optional: an input the computation does not need, and why

    sh = add(x0, y0)                  one operation per line
    (s, e) = two_sum(a, b)            a call of another kernel
    g = prod(const splitter, a)       a format-dependent constant as an operand
    d = rmul(const unit_computed(add_2_2), mz)
                                      a constant computed from another kernel's claims
    m = lt(x1, 0)                     the literal zero (+0) as an operand
    f = lt(a, const inf)              +infinity; `const nan` is a quiet NaN
    g = guard(a)                      RN(a + 0): a value that enters from the program (R3)
    r0 = times_inf(t)                 t times +infinity, exact: compared or selected only (R1)
    k = prod(const up((1+u)^6), a)    an exact expression rounded up to the format: over u,
                                      eta, integers, unit(K) and tiny(K) (the constants c u^k
                                      and t eta of K's error claim), + - * / ^ and parentheses

Expressions in `ensures` are written without spaces. A condition of finite_when is
abs_le(EXPR,E), meaning |EXPR| <= 2^(qmax + p + E); several are separated by `;`, and none is
written by leaving finite_when out. A condition of exact_when is zero_or_abs_gt(EXPR,K) or
zero_or_abs_ge(EXPR,K), meaning EXPR = 0 or |EXPR| > K (>= K), with EXPR over the input names
and their limbs (`cx[1]`, limb 1 of the input cx) and K an exact expression over u, eta and
integers (`eta/(2*u)`); several are separated by `;`, and all must hold. This module only reads
and represents descriptions; rules.py decides whether they are acceptable.

A fold (docs/developer/design/milestone2.md, "Folds, the extension of the IR") is a loop of kernels
along arrays, described in gen/kernels/NAME.fold:

    fold:          dot_2
    arrays:        supplied x = x0 x1, supplied y = y0 y1
                                      the arrays read, one array per limb, each declared stored (a
                                      container written through Kairn) or supplied (the program's)
    state:         s = s0 s1          the state; it starts at zero, every limb +0
    step:          s = dot_step_2(s, x, y)
                                      a kernel: the state and one element of each array, in the
                                      order the kernel's inputs take them, to the next state
    combine:       s = add_2_2(s, s)  a kernel: two states into one (the lane order)
    orders:        sequential, lanes  the orders emitted
    writes:        none               the array written, for a map (below)
    output:        r = r0 r1          the fold's results: the outputs of the finish
    output:        mask flag
    finish:        (r, flag) = fold_finish_2(s)
                                      a kernel on the final state, or `none` (the state is returned)
    value:         x*y                the exact value of one element; the fold's is their sum
    requires:      canonical x        of every element
    ensures:       normalized r
    ensures:       fold_error r eps=3*u^2/(1-4*u) term=4*u^2 tau=3/2*eta rel=n-1 abs=n-1
                                      |r - sum v_i| <= ((1 + term) (1 + eps)^rel - 1) sum |v_i|
                                                       + (1 + eps)^abs n tau, n the length; rel
                                                       and abs are n or n-1 (natural numbers: 0 -
                                                       1 is 0), the same in both orders; term and
                                                       tau are 0 when left out
    ensures:       finite_or_nan r flag=flag
    min_precision: 4
    status:        unverified         or proved, with theorem: FILE (F_seq_correct, F_lanes_correct)
    ieee_theorem:  FILE               optional, once the statements of proofs/gen/IeeeFoldStatements.v
                                      are proved: F_seq_ieee_correct and F_lanes_ieee_correct, of
                                      the orders the fold (or the map) has; F_ieee_correct, of a
                                      convolution
    domain:        extended           elements may be infinite or NaN (the flag says what comes out)

A map is a fold that writes an array (docs/developer/architecture.md, "Maps"):

    fold:          axpy_2
    arrays:        supplied x = x0 x1, stored y = y0 y1
    scalars:       supplied a = a0 a1  given once, passed to every step
    state:         mask finite        true at the start
    step:          z = axpy_step_2(a, x, y)
                                      the scalars and one element to the element written; no state
    combine:       finite = and(finite, finite)
    orders:        sequential, lanes
    writes:        z = z0 z1          the array written
    check:         fold_finish_2      the test of a written element, and its canonical NaN
    finish:        none               a map returns its mask
    value:         a*x+y              the step's value
    requires:      canonical a
    ensures:       entries z          each written element satisfies the step's claims
    ensures:       finite_or_nan z flag=finite

A fold of maxima (docs/developer/architecture.md, "Folds of maxima") has a state of a value and a
mask, several groups given in order, and claims an upper bound of the largest value of an element:

    fold:          norm_upper_2
    arrays:        stored x = x0 x1
    state:         m, mask ok         a limb that starts at +0 and a mask that starts true
    step:          (m, ok) = norm_step_2(m, ok, x)
    combine:       (m, ok) = norm_combine(m, ok, m, ok)
    finish:        (r, flag) = norm_finish_2(m, ok)
    value:         abs(x)
    ensures:       upper r max steps=1
                                      max_i v_i <= r <= RU(max_i v_i) stepped up that many times

A convolution (docs/developer/architecture.md, "Convolutions") writes the coefficients of the
product of two polynomials, one array per polynomial, of lengths of their own: coefficient j is a
fold of the dot product (named, in its sequential order) on the terms (x_i, y_(j-i)), i increasing.
It has no step of its own, and is otherwise described as a map:

    fold:          conv_2
    arrays:        supplied x = x0 x1, supplied y = y0 y1
    coefficients:  dot_2              the fold of each coefficient; its arrays are these
    state:         mask finite
    combine:       finite = and(finite, finite)
    orders:        sequential
    writes:        z = z0 z1          n_x + n_y - 1 coefficients (none when an array is empty)
    check:         fold_finish_2      the finish of the fold of the coefficients
    finish:        none
    value:         x*y
    ensures:       coefficients z     each coefficient satisfies that fold's claims on its terms
    ensures:       finite_or_nan z flag=finite

A ball vector (docs/developer/architecture.md, "Ball vectors"; milestone2.md, "BallVector") is a map
of the centers of BallVectors whose state is that of a fold of maxima, the largest magnitude of a
leading limb written and the mask that none was a NaN, and whose finish gives the one radius of the
result; when the result is not a finite ball vector, every center written is zero and the radius
+infinity, the whole space:

    fold:          bv_add_2
    arrays:        stored x = x0 x1, stored y = y0 y1
    scalars:       stored rx, stored ry
    state:         m, mask ok
    step:          z = add_2_2(x, y)
    record:        (m, ok) = norm_step_2(m, ok, z)
                                      the step of a fold of maxima, on each element written
    combine:       (m, ok) = norm_combine(m, ok, m, ok)
    radius:        rz = bv_add_radius_2(m, rx, ry)
                                      the radius from the largest magnitude and scalars
    finish:        (r, finite) = norm_finish_1(rz, ok)
                                      the radius, or a NaN and the flag false
    writes:        z = z0 z1
    output:        r
    output:        mask finite
    requires:      ball_vector x rx   the centers x with the radius rx: canonical (finite, or the
                                      whole space: every center zero and the radius +infinity)
    ensures:       encloses_entries z r x+y x=x,rx y=y,ry flag=finite finite_when=abs_le(abs(x+y)+rx+ry,-2)
                   radii_when=abs_le(rx+ry,-2)
                                      V4 for every length: the radii's own condition (over the
                                      scalars), which finite_when at any entry implies

A ball vector exact under conditions (bv_mul_pow2_k: exact when nothing underflows) has a third group
of the state, a mask from true; its step returns the center and a mask that its entry is exact, and a
second record line and a second combine line and that mask into the state; its radius takes the
state's mask after its limb; its claim has exact_when with conditions of an entry and of the scalars:

    state:         m, mask ok, mask ex
    step:          (z, e) = bv_mul_pow2_step_2(x, c)
    record:        (m, ok) = norm_step_2(m, ok, z)
    record:        ex = and(ex, e)
    combine:       (m, ok) = norm_combine(m, ok, m, ok)
    combine:       ex = and(ex, ex)
    radius:        rz = bv_mul_pow2_radius(m, ex, rx, c)
    ensures:       encloses_entries z r x*c x=x,rx flag=finite ... exact_when=zero_or_abs_gt(x[0]*c,eta/(2*u));...
"""
import json
import os
import re
from dataclasses import dataclass, field

LIMB, MASK = 'limb', 'mask'

# Every operation: the kinds of its operands and of its result. Their meaning is in the
# interpreter, and their spelling in the two printers, each in one table.
OPS = {
    'add': ((LIMB, LIMB), LIMB),
    'sub': ((LIMB, LIMB), LIMB),
    'neg': ((LIMB,), LIMB),
    'abs': ((LIMB,), LIMB),
    'fma': ((LIMB, LIMB, LIMB), LIMB),
    'fms': ((LIMB, LIMB, LIMB), LIMB),
    'fnma': ((LIMB, LIMB, LIMB), LIMB),
    'prod': ((LIMB, LIMB), LIMB),
    'muladd': ((LIMB, LIMB, LIMB), LIMB),
    'lt': ((LIMB, LIMB), MASK),
    'le': ((LIMB, LIMB), MASK),
    'eq': ((LIMB, LIMB), MASK),
    'and': ((MASK, MASK), MASK),
    'or': ((MASK, MASK), MASK),
    'not': ((MASK,), MASK),
    'select': ((MASK, LIMB, LIMB), LIMB),
    'succ': ((LIMB,), LIMB),
    'pred': ((LIMB,), LIMB),
    # The value itself, under another name: how a kernel returns one of its inputs (to_nearest_2
    # returns x0), since an output must be computed by an operation (rule 3).
    'copy': ((LIMB,), LIMB),
    # RN(a + 0): the value of a, a zero made positive. A value that enters from the program passes
    # through it before any addition (rule R3); its result is an addition, which nothing can fuse.
    'guard': ((LIMB,), LIMB),
    # t times +infinity, which is exact: a NaN when t is a NaN or a zero, otherwise the infinity
    # with the sign of t. A plain multiplication, so its result may only be compared or selected
    # (rule R1); the fix-ups of the non-finite layer turn t into its infinity with it.
    'times_inf': ((LIMB,), LIMB),
    # A plain multiplication. It is accepted by the parser only so that rule R1 refuses it with a
    # reason; no printer and no interpreter knows it.
    'mul': ((LIMB, LIMB), LIMB),
}

# Operations emitted as a fused multiply-add instruction, which constant evaluation does not have.
FUSED = frozenset({'fma', 'fms', 'fnma', 'prod'})

# Format-dependent constants, as a function of the precision p. The Rocq printer spells the same
# definition in Rocq (rocq.py, CONSTANTS); the two must be read side by side.
CONSTANTS = {
    'splitter': lambda p: 2 ** ((p + 1) // 2) + 1,   # Veltkamp's multiplier 2^ceil(p/2) + 1
}
# The literal zero of a description (`lt(x1, 0)`) is the constant of this name, +0 in every format.
ZERO = '0'
# The constants that are not numbers: +infinity and a quiet NaN, which only the fix-ups of the
# non-finite layer use (docs/developer/design/milestone1.md, "IEEE-like results"). The real model
# has neither, so a kernel that names one has no real-model statement.
SPECIAL = ('inf', 'nan')
# Constants computed from the claims of another kernel K (consts.py): written `const F(K)`.
COMPUTED = ('unit_computed', 'tiny_computed')
_COMPUTED = re.compile(r'(unit_computed|tiny_computed)\(([a-z][a-z0-9_]*)\)\Z')


def computed(name):
    """(F, K) for the name of a computed constant F(K), or None."""
    m = _COMPUTED.match(name)
    return (m.group(1), m.group(2)) if m else None


# A constant defined by an exact expression, rounded up to the format: written `const up(EXPR)`,
# EXPR over u, eta, integers, unit(K) and tiny(K), with + - * /, parentheses and integer powers
# (consts.py computes it; expr.py parses EXPR).
_UP = re.compile(r'up\((.+)\)\Z')


def up(name):
    """The expression of a constant up(EXPR), or None."""
    m = _UP.match(name)
    return m.group(1) if m else None


KERNEL_NAME = re.compile(r'[a-z][a-z0-9_]*\Z')
# Value names have no underscore: flattening names an inlined value CALLER_CALLEE, which can then
# never collide with a name written in a description.
VALUE_NAME = re.compile(r'[a-z][a-z0-9]*\Z')


class DescriptionError(Exception):
    pass


@dataclass(frozen=True)
class Operand:
    name: str
    const: bool = False   # a constant of the format: a name of CONSTANTS, ZERO, or computed

    def __str__(self):
        if self.const and self.name != ZERO:
            return f'const {self.name}'
        return self.name


@dataclass(frozen=True)
class Stmt:
    dsts: tuple   # names it defines: one for an operation, one per callee output limb for a call
    op: str       # a key of OPS, or the name of the called kernel
    args: tuple   # Operands
    line: int

    @property
    def is_call(self):
        return self.op not in OPS


@dataclass(frozen=True)
class Group:
    name: str
    limbs: tuple
    kind: str = LIMB     # MASK: one value, the group's name


@dataclass
class Kernel:
    name: str
    path: str
    inputs: list = field(default_factory=list)     # Groups
    outputs: list = field(default_factory=list)    # Groups
    body: list = field(default_factory=list)       # Stmts
    value: str = None
    requires: list = field(default_factory=list)   # tuples: ('normalized', g), ('abs_ge', g, h), ...
    ensures: list = field(default_factory=list)    # dicts in the claims schema's shape
    min_precision: int = None
    theorem: tuple = None                          # (file, name)
    source: str = None
    license: str = None
    status: str = None
    ce_variant: str = None
    cone_exempt: str = None
    # The C++ function is an ordinary inline function, not forced inline (milestone2.md, "Inlining
    # and compile time"): why, or None for the rule (forced inline up to two limbs).
    ordinary_inline: str = None
    unused: dict = field(default_factory=dict)     # input value -> why the computation ignores it
    # The non-finite layer (architecture.md, "Claims of the non-finite layer").
    domain: str = None                             # None (finite) or 'extended', as written
    ieee_status: str = None
    ieee_theorem: tuple = None                     # (file, name)
    ieee_only: bool = False                        # no real-model statement (a full Ball kernel)
    # The theorems of the IEEE-model statements of a kernel of the finite domain, (file, name), once
    # each is proved: K_ieee_bridge_spec, K_ieee_spec and K_ieee_lead_spec.
    ieee_bridge_theorem: tuple = None
    ieee_spec_theorem: tuple = None
    ieee_lead_theorem: tuple = None
    # The IEEE-model statements of a kernel of the finite domain (ieee.py): which of `bridge` and
    # `spec`, and the thresholds under which every value it computes is finite.
    ieee: tuple = ()
    ieee_finite: list = field(default_factory=list)          # conditions, as in finite_when
    ieee_finite_result: list = field(default_factory=list)
    # Rule R3 (architecture.md, "The kernel IR").
    entry: bool = False
    stored: set = field(default_factory=set)       # one-limb input groups that are limbs of objects
    supplied: set = field(default_factory=set)     # multi-limb input groups the program gives
    guard_pending: dict = field(default_factory=dict)   # input value -> why it is not guarded yet
    # The record of the names of the constants up(EXPR) of the set the kernel was loaded with
    # (load_kernels), shared by its kernels: {EXPR: name}. None for a kernel read on its own.
    constant_names: dict = field(default=None, repr=False, compare=False)

    @property
    def extended(self):
        return self.domain == 'extended'

    @property
    def real_model(self):
        """Whether the kernel has a statement in the real model. A full kernel or a constructor
        (architecture.md, "Claims of the non-finite layer") has the IEEE-model statement only: it
        says how non-finite values come out, which the real model cannot. They are recognized by
        what they claim: nothing but `extends`, `represents` and `makes_ball` (neg_2 and abs_2
        claim `represents` next to `normalized` and `error`, and keep their real-model
        statement), or, for the full Ball kernels, whose claims have the shape of ball_neg_k's,
        by `ieee_only: yes`."""
        return not (self.ieee_only or (bool(self.ensures) and
                                       all(e['kind'] in NON_FINITE_ONLY for e in self.ensures)))

    def program_values(self):
        """The input values that enter from the program, for rule R3: in an entry kernel, every
        one-limb limb input not declared stored, and the limbs of multi-limb inputs declared
        supplied. Empty for a kernel that is not an entry kernel."""
        if not self.entry:
            return []
        out = []
        for g in self.inputs:
            if g.kind != LIMB:
                continue
            if (len(g.limbs) == 1 and g.name not in self.stored) or g.name in self.supplied:
                out += list(g.limbs)
        return out

    @property
    def input_limbs(self):
        """Every input value, masks included, in order: the kernel's parameters."""
        return [v for g in self.inputs for v in g.limbs]

    @property
    def output_limbs(self):
        return [v for g in self.outputs for v in g.limbs]

    @property
    def input_kinds(self):
        return [g.kind for g in self.inputs for _ in g.limbs]

    @property
    def output_kinds(self):
        return [g.kind for g in self.outputs for _ in g.limbs]

    @property
    def limbs(self):
        return max(len(g.limbs) for g in self.inputs + self.outputs)

    @property
    def forced_inline(self):
        """Whether the C++ function is forced inline: a kernel of at most two limbs, unless it says
        `ordinary_inline:`."""
        return self.limbs <= 2 and self.ordinary_inline is None


# The IEEE-model statements a kernel of the finite domain may ask for (ieee.py, `ieee:`).
IEEE_STATEMENTS = ('bridge', 'spec')

# The fields that name the theorems of the IEEE-model statements of a kernel of the finite domain,
# and the name each theorem has (K standing for the kernel's name).
IEEE_THEOREM_KEYS = ('ieee_bridge_theorem', 'ieee_spec_theorem', 'ieee_lead_theorem')
IEEE_THEOREM_NAMES = {'ieee_bridge_theorem': '{}_ieee_bridge', 'ieee_spec_theorem': '{}_ieee_correct',
                      'ieee_lead_theorem': '{}_ieee_lead'}

# The claims that only the non-finite layer has: a kernel that claims nothing else has no
# real-model statement (Kernel.real_model). The interval kinds of Milestone 2 are among them: an
# interval has infinite bounds as ordinary values, so its kernels are stated in the IEEE model only.
NON_FINITE_ONLY = ('extends', 'represents', 'makes_ball', 'finite_or_nan', 'makes_interval', 'encloses_interval',
                   'set_bound', 'interval_set', 'ball_of_interval', 'interval_of_ball', 'splits', 'certain', 'trit',
                   'ball_set', 'ball_splits')

INPUT_CLASSES = ('stored', 'supplied')   # rule R3: where an entry kernel's input comes from


def _group(text, where, classes=()):
    """A group, and the class written before it (one of `classes`, or None)."""
    words = text.split()
    if len(words) == 2 and words[0] == 'mask' and VALUE_NAME.match(words[1]):
        return Group(words[1], (words[1],), MASK), None
    cls = None
    if len(words) > 1 and words[0] in classes:
        cls, text = words[0], text.strip()[len(words[0]):]
    m = re.fullmatch(r'([a-z][a-z0-9]*)(?:\s*=\s*([a-z0-9 ]+))?', text.strip())
    if not m:
        raise DescriptionError(f'{where}: expected "NAME", "NAME = LIMB LIMB ..." or "mask NAME"'
                               f'{", after stored or supplied" if classes else ""}, got {text!r}')
    limbs = tuple(m.group(2).split()) if m.group(2) else (m.group(1),)
    return Group(m.group(1), limbs), cls


def _finite_from(text, where):
    """finite_from=P of a ball vector's claim: the precision from which V4 is claimed, a positive
    integer."""
    if not re.fullmatch(r'[1-9][0-9]*', text):
        raise DescriptionError(f'{where}: finite_from is a precision, a positive integer, got {text!r}')
    return int(text)


def _finite_when(text, where):
    """abs_le(EXPR,E);abs_le(EXPR,E) as [{'abs_le': EXPR, 'exp': E}, ...]."""
    out = []
    for part in text.split(';') if text else ():
        m = re.fullmatch(r'abs_le\((.+),(-?[0-9]+)\)', part)
        if not m:
            raise DescriptionError(f'{where}: a condition of finite_when is abs_le(EXPR,E), got {part!r}')
        out.append({'abs_le': m.group(1), 'exp': int(m.group(2))})
    return out


# The conditions of exact_when: EXPR = 0 or |EXPR| > K, and EXPR = 0 or |EXPR| >= K; and, on
# outward and on the outward tightness of an interval (Milestone 2), EXPR = 0; and, on an upper
# entry of a radius kernel (the scaling of a BallVector by a power of two), that a mask input is
# true.
EXACT_CONDITIONS = ('zero_or_abs_gt', 'zero_or_abs_ge')
ZERO_CONDITION = 'zero'
MASK_CONDITION = 'mask'


def _exact_when(text, where):
    """zero_or_abs_gt(EXPR,K);zero_or_abs_ge(EXPR,K);zero(EXPR);mask(NAME) as
    [{'zero_or_abs_gt': EXPR, 'than': K}, ..., {'zero': EXPR}, {'mask': NAME}]; and abs_le(EXPR,omega),
    |EXPR| <= Omega, as {'abs_le': EXPR, 'omega': True} (a condition of certain and trit only: rules.py)."""
    out = []
    for part in text.split(';'):
        m = re.fullmatch(r'([a-z_]+)\((.+)\)', part)
        args = _arguments(m.group(2), where) if m else []
        if m and m.group(1) == ZERO_CONDITION and len(args) == 1 and args[0]:
            out.append({ZERO_CONDITION: args[0]})
            continue
        if m and m.group(1) == MASK_CONDITION and len(args) == 1 and VALUE_NAME.match(args[0]):
            out.append({MASK_CONDITION: args[0]})
            continue
        if m and m.group(1) == 'abs_le' and len(args) == 2 and args[0] and args[1] == 'omega':
            out.append({'abs_le': args[0], 'omega': True})
            continue
        if not m or m.group(1) not in EXACT_CONDITIONS or len(args) != 2 or not all(args):
            raise DescriptionError(f'{where}: a condition of exact_when is zero_or_abs_gt(EXPR,K), '
                                   f'zero_or_abs_ge(EXPR,K), zero(EXPR) or mask(NAME), got {part!r}')
        out.append({m.group(1): args[0], 'than': args[1]})
    return out


def _steps(text, where):
    if not re.fullmatch(r'[0-9]+', text):
        raise DescriptionError(f'{where}: steps must be an integer, got {text!r}')
    return int(text)


def _bounded_when(text, where):
    """abs_le(EXPR,omega);abs_le(EXPR,E) as [{'abs_le': EXPR, 'omega': True}, {'abs_le': EXPR, 'exp': E}]."""
    out = []
    for part in text.split(';') if text else ():
        m = re.fullmatch(r'abs_le\((.+),(omega|-?[0-9]+)\)', part)
        if not m:
            raise DescriptionError(f'{where}: a condition of bounded_when is abs_le(EXPR,omega) or '
                                   f'abs_le(EXPR,E), got {part!r}')
        out.append({'abs_le': m.group(1), 'omega': True} if m.group(2) == 'omega'
                   else {'abs_le': m.group(1), 'exp': int(m.group(2))})
    return out


# The tightness of an interval or of a bound of a set (Milestone 2): rounded (with optional steps
# and when), exact, or outward with rel and abs.
TIGHT_KINDS = ('rounded', 'exact', 'outward')


def _tight(text, where):
    """rounded[;steps=N][;when=COND], exact, or outward;rel=EXPR;abs=EXPR, as a dict."""
    parts = text.split(';')
    kind = parts[0]
    if kind not in TIGHT_KINDS:
        raise DescriptionError(f'{where}: tight is {", ".join(TIGHT_KINDS)}, got {kind!r}')
    out = {'kind': kind}
    allowed = {'rounded': ('steps', 'when'), 'exact': (), 'outward': ('rel', 'abs')}[kind]
    for p in parts[1:]:
        key, eq, val = p.partition('=')
        if not eq or key not in allowed or key in out or not val:
            raise DescriptionError(f'{where}: bad or repeated field {p!r} of tight={kind}')
        if key == 'steps':
            if not re.fullmatch(r'[0-9]+', val):
                raise DescriptionError(f'{where}: steps must be an integer, got {val!r}')
            val = int(val)
        out[key] = val
    if kind == 'outward' and ('rel' not in out or 'abs' not in out):
        raise DescriptionError(f'{where}: tight=outward needs rel= and abs=')
    return out


# The relations of the predicates of sets, certain and trit (Milestone 2, the enclosure interface),
# and their number of arguments: empty and entire take one set, the others two arguments.
SET_RELATION_ARITY = {'empty': 1, 'entire': 1, 'member': 2, 'subset': 2, 'equal': 2, 'interior': 2,
                      'disjoint': 2, 'lt': 2, 'le': 2, 'eq': 2}


def _set_kinds(e, k):
    """A certain or trit entry with its sets named as what the requirements say they are: the
    bounds of an interval ("intervals", NAME: {lower, upper}) or a ball ("balls", NAME: {center,
    radius}). The sets of an entry are of one kind; a set that is neither is written as an interval,
    which rules.py then refuses for want of its requirement."""
    sets = e.pop('sets')
    balls = bool(sets) and all(('ball', s['a'], s['b']) in k.requires for s in sets.values())
    key, names = ('balls', ('center', 'radius')) if balls else ('intervals', ('lower', 'upper'))
    out = {x: v for x, v in e.items() if x not in ('exact', 'exact_when')}
    out[key] = {x: {names[0]: s['a'], names[1]: s['b']} for x, s in sets.items()}
    out.update({x: v for x, v in e.items() if x in ('exact', 'exact_when')})
    return out


def _pairs(words, where, what, keys):
    """NAME=A,B words as {NAME: {keys[0]: A, keys[1]: B}}."""
    out = {}
    for w in words:
        m = re.fullmatch(r'([a-z][a-z0-9]*)=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', w)
        if not m or m.group(1) in out:
            raise DescriptionError(f'{where}: bad or repeated {what} {w!r}: NAME={keys[0].upper()},{keys[1].upper()}')
        out[m.group(1)] = {keys[0]: m.group(2), keys[1]: m.group(3)}
    return out


def _ensures(words, where):
    kind = words[0] if words else None
    if kind in ('normalized', 'leading_rounded', 'represents') and len(words) == 2:
        return {'kind': kind, 'of': words[1]}
    if kind == 'extends' and len(words) >= 2:
        entry = {'kind': kind, 'of': words[1], 'core': None, 'lead': None, 'finite_when': None}
        for w in words[2:]:
            key, eq, val = w.partition('=')
            if not eq or key not in ('core', 'lead', 'finite_when') or entry[key] is not None:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in extends entry')
            entry[key] = _finite_when(val, where) if key == 'finite_when' else val
        for key in ('core', 'lead'):
            if not entry[key]:
                raise DescriptionError(f'{where}: an extends entry needs {key}=')
        if entry['finite_when'] is None:
            entry['finite_when'] = []
        return entry
    if kind == 'makes_ball' and len(words) == 4 and words[3].startswith('from='):
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        if not m:
            raise DescriptionError(f'{where}: expected "makes_ball CENTER RADIUS from=CENTER,RADIUS"')
        return {'kind': kind, 'center': words[1], 'radius': words[2],
                'from': {'center': m.group(1), 'radius': m.group(2)}}
    if kind == 'makes_ball' and len(words) >= 4 and words[3].startswith('from_interval='):
        # A ball from the bounds of an interval (Milestone 2): `from` names a lower and an upper
        # input, and midpoint_when the conditions under which the center is the exact midpoint; or
        # (stage B2, ball_from_interval_1) rel and abs, the distance of the center to the midpoint,
        # and smallest_radius, as ball_of_interval has them.
        m = re.fullmatch(r'from_interval=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        opts = {}
        for w in words[4:]:
            key, eq, val = w.partition('=')
            if key in ('midpoint_when', 'rel', 'abs') and eq and val and key not in opts:
                opts[key] = val
            elif w == 'smallest_radius' and w not in opts:
                opts[w] = True
            else:
                m = None
        if not m:
            raise DescriptionError(f'{where}: expected "makes_ball CENTER RADIUS from_interval=LOWER,UPPER '
                                   '[midpoint_when=CONDITIONS] [rel=EXPR abs=EXPR] [smallest_radius]"')
        entry = {'kind': kind, 'center': words[1], 'radius': words[2],
                 'from': {'lower': m.group(1), 'upper': m.group(2)}}
        for key in ('rel', 'abs', 'smallest_radius'):
            if key in opts:
                entry[key] = opts[key]
        if 'midpoint_when' in opts:
            conds = []
            for part in opts['midpoint_when'].split(';'):
                c = re.fullmatch(r'half_in_format\(([a-z][a-z0-9]*)\)', part)
                if not c:
                    raise DescriptionError(f'{where}: a condition of midpoint_when is half_in_format(INPUT), '
                                           f'got {part!r}')
                conds.append({'half_in_format': c.group(1)})
            entry = {key: v for key, v in entry.items() if key not in ('rel', 'abs', 'smallest_radius')} | \
                {'midpoint_when': conds} | {key: v for key, v in entry.items() if key in ('rel', 'abs', 'smallest_radius')}
        return entry
    if kind == 'makes_interval' and len(words) == 4:
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        if not m:
            raise DescriptionError(f'{where}: expected "makes_interval LOWER UPPER from=LOWER,UPPER"')
        return {'kind': kind, 'lower': words[1], 'upper': words[2],
                'from': {'lower': m.group(1), 'upper': m.group(2)}}
    if kind in ('rounded', 'bound', 'outward') and words[-1] == 'zero_factor' and len(words) > 3:
        # The extended reading of a product with a zero factor: zero (Milestone 2, mul_dir_1, and
        # the bounds of two limbs of mul_ext_2_2). Written only when it is claimed, after the entry's
        # other fields.
        entry = _ensures(words[:-1], where)
        entry['zero_factor'] = True
        return entry
    if kind == 'rounded' and len(words) == 3:
        return {'kind': kind, 'of': words[1], 'mode': words[2]}
    if kind == 'rounded' and len(words) == 4 and words[3].startswith('when='):
        # The condition is written only when there is one: a rounded entry without it has the
        # shape it always had.
        return {'kind': kind, 'of': words[1], 'mode': words[2], 'when': words[3][len('when='):]}
    if kind == 'rounded' and len(words) == 4 and words[3].startswith('value='):
        # A value of its own (the accumulator's sum of magnitudes, beside the kernel's value):
        # written only when there is one.
        return {'kind': kind, 'of': words[1], 'mode': words[2], 'value': words[3][len('value='):]}
    if kind == 'upper' and len(words) == 3 and words[2].startswith('gaps='):
        return {'kind': kind, 'of': words[1], 'gaps': words[2][len('gaps='):]}
    if kind == 'upper' and len(words) == 4 and words[2] == 'max' and words[3].startswith('steps='):
        # A fold of maxima: an upper bound of the largest value of an element.
        return {'kind': kind, 'of': words[1], 'over': 'max', 'steps': _steps(words[3][len('steps='):], where)}
    if kind == 'upper' and len(words) >= 3:
        # Milestone 2: an upper bound of an expression of its own, under the condition of a mask
        # output. The fields are written only when there are: an upper entry with gaps alone has
        # the shape it always had.
        entry = {'kind': kind, 'of': words[1]}
        for w in words[2:]:
            key, eq, val = w.partition('=')
            if not eq or key not in ('gaps', 'value', 'if', 'unless', 'exact_when') or key in entry or not val:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in upper entry')
            # unless: the bound holds when that mask input is false; exact_when: the output is the
            # value exactly when the conditions hold (the radius of the scaling of a BallVector by a
            # power of two). Written only in the entries that have them.
            entry[key] = _exact_when(val, where) if key == 'exact_when' else val
        return entry
    if kind == 'holds' and len(words) == 5 and words[4].startswith('if='):
        return {'kind': kind, 'rel': words[1], 'args': words[2:4], 'if': words[4][len('if='):]}
    if kind == 'finite_or_nan' and len(words) == 3 and words[2].startswith('flag='):
        return {'kind': kind, 'of': words[1], 'flag': words[2][len('flag='):]}
    if kind == 'finite_or_nan' and len(words) > 3 and words[2].startswith('flag='):
        # The finish of a fold of maxima: a mask input that must be true (if=), and the number of
        # steps up from the value (steps=). The fields are written only when there are.
        entry = {'kind': kind, 'of': words[1], 'flag': words[2][len('flag='):]}
        for w in words[3:]:
            if w == 'nonneg' and 'nonneg' not in entry:
                # The finish of a constructor of a BallVector: the value is also not negative.
                entry['nonneg'] = True
                continue
            if w.startswith('if_all=') and 'if_all' not in entry and 'if' not in entry:
                # The finish of the product of two BallVectors: under several mask inputs, all true.
                names = w[len('if_all='):].split(',')
                if len(names) < 2 or not all(VALUE_NAME.match(n) for n in names):
                    raise DescriptionError(f'{where}: if_all=MASK,MASK,...: the names of two mask inputs or more')
                entry['if_all'] = names
                continue
            key, eq, val = w.partition('=')
            if not eq or key not in ('if', 'steps') or key in entry or not val or 'nonneg' in entry:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in finite_or_nan entry')
            entry[key] = _steps(val, where) if key == 'steps' else val
        return entry
    if kind == 'maximum' and len(words) == 4:
        return {'kind': kind, 'of': words[1], 'args': words[2:4]}
    if kind in ('entries', 'coefficients') and len(words) == 2:
        return {'kind': kind, 'of': words[1]}
    if kind == 'fold_error' and len(words) >= 3:
        entry = {'kind': kind, 'of': words[1], 'eps': None, 'term': '0', 'tau': '0', 'rel': None, 'abs': None}
        seen = set()
        for w in words[2:]:
            key, eq, val = w.partition('=')
            if not eq or key not in ('eps', 'term', 'tau', 'rel', 'abs') or key in seen or not val:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in fold_error entry')
            seen.add(key)
            entry[key] = val
        for key in ('eps', 'rel'):
            if entry[key] is None:
                raise DescriptionError(f'{where}: a fold_error entry needs {key}=')
        if entry['abs'] is None:
            entry['abs'] = entry['rel']
        return entry
    if kind == 'neighbor' and len(words) == 3:
        return {'kind': kind, 'of': words[1], 'side': words[2]}
    if kind == 'bound' and len(words) == 4 and words[3].startswith('steps='):
        return {'kind': kind, 'of': words[1], 'side': words[2], 'steps': _steps(words[3][len('steps='):], where)}
    if kind == 'outward' and len(words) in (5, 6):
        entry = {'kind': kind, 'of': words[1], 'side': words[2], 'rel': None, 'abs': None}
        for w in words[3:]:
            key, eq, val = w.partition('=')
            if key == 'exact_when' and eq and 'exact_when' not in entry:
                entry['exact_when'] = _exact_when(val, where)
            elif key in ('rel', 'abs') and eq and val and entry[key] is None:
                entry[key] = val
            else:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in outward entry')
        if entry['rel'] is None or entry['abs'] is None:
            raise DescriptionError(f'{where}: an outward entry needs rel= and abs=')
        return entry
    if kind in ('encloses_interval', 'set_bound') and len(words) >= 5:
        # encloses_interval LOWER UPPER SET NAME=LOWER,UPPER ... [tight=...] [exact_lower=...]
        #   [exact_upper=...] [bounded_when=...] [bounded_exactly]
        # set_bound OUTPUT SIDE SET NAME=CENTER,RADIUS ... [tight=...]
        names, opts = [], {}
        for w in words[4:]:
            key, eq, val = w.partition('=')
            if key in ('tight', 'exact_lower', 'exact_upper', 'bounded_when') and eq:
                if key in opts:
                    raise DescriptionError(f'{where}: {key} given twice')
                opts[key] = val
            elif w in ('bounded_exactly', 'zero_factor') and kind == 'encloses_interval' and w not in opts:
                opts[w] = True
            else:
                names.append(w)
        if kind == 'set_bound':
            if set(opts) - {'tight'}:
                raise DescriptionError(f'{where}: set_bound has tight= and nothing else of an interval')
            entry = {'kind': kind, 'of': words[1], 'side': words[2], 'set': words[3],
                     'balls': _pairs(names, where, 'ball', ('center', 'radius'))}
            if 'tight' in opts:
                entry['tight'] = _tight(opts['tight'], where)
            return entry
        entry = {'kind': kind, 'lower': words[1], 'upper': words[2], 'set': words[3],
                 'intervals': _pairs(names, where, 'interval', ('lower', 'upper'))}
        if 'tight' not in opts:
            raise DescriptionError(f'{where}: an encloses_interval entry needs tight=')
        entry['tight'] = _tight(opts['tight'], where)
        sides = {s: _exact_when(opts[f'exact_{s}'], where) for s in ('lower', 'upper') if f'exact_{s}' in opts}
        if sides:
            if entry['tight']['kind'] != 'outward':
                raise DescriptionError(f'{where}: exact_lower and exact_upper belong to tight=outward')
            entry['tight']['exact_when'] = sides
        entry['bounded_when'] = _bounded_when(opts.get('bounded_when', ''), where)
        if opts.get('bounded_exactly'):
            entry['bounded_exactly'] = True
        if opts.get('zero_factor'):
            # A nonempty operand [0, 0] gives [0, 0] (interval_mul_2): only when it is claimed.
            entry['zero_factor'] = True
        return entry
    if kind == 'interval_set' and len(words) == 6:
        # The hull (union) or the intersection of two intervals (Milestone 2): exact.
        return {'kind': kind, 'lower': words[1], 'upper': words[2], 'set': words[3],
                'intervals': _pairs(words[4:], where, 'interval', ('lower', 'upper'))}
    if kind == 'ball_of_interval' and len(words) >= 4:
        # ball_of_interval CENTER RADIUS from=LOWER,UPPER special=S rel=EXPR abs=EXPR [smallest_radius]
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        if not m:
            raise DescriptionError(f'{where}: expected "ball_of_interval CENTER RADIUS from=LOWER,UPPER special=... '
                                   'rel=EXPR abs=EXPR [smallest_radius]"')
        entry = {'kind': kind, 'center': words[1], 'radius': words[2],
                 'from': {'lower': m.group(1), 'upper': m.group(2)}, 'special': None, 'rel': None, 'abs': None}
        for w in words[4:]:
            key, eq, val = w.partition('=')
            if key in ('special', 'rel', 'abs') and eq and val and entry[key] is None:
                entry[key] = val
            elif w == 'smallest_radius' and w not in entry:
                entry[w] = True
            elif key == 'finite_when' and eq and val and key not in entry:
                # Stage B2 (interval_mid_rad_2): the radius is finite when the conditions hold.
                entry[key] = _finite_when(val, where)
            else:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in ball_of_interval entry')
        if None in (entry['special'], entry['rel'], entry['abs']):
            raise DescriptionError(f'{where}: a ball_of_interval entry needs special=, rel= and abs=')
        if 'smallest_radius' in entry:
            entry['smallest_radius'] = entry.pop('smallest_radius')     # last, after the constants
        if 'finite_when' in entry:
            entry['finite_when'] = entry.pop('finite_when')
        return entry
    if kind == 'interval_of_ball' and len(words) >= 6 and words[5].startswith('tight='):
        # interval_of_ball LOWER UPPER SET NAME=CENTER,RADIUS tight=... [exact_lower=...]
        #   [exact_upper=...] [bounded_when=...]: an interval that encloses a ball; the tightness
        #   outward, with the exactness of each side and the condition of a bounded result, of two
        #   limbs (stage B2).
        entry = {'kind': kind, 'lower': words[1], 'upper': words[2], 'set': words[3],
                 'balls': _pairs(words[4:5], where, 'ball', ('center', 'radius')),
                 'tight': _tight(words[5][len('tight='):], where)}
        opts = {}
        for w in words[6:]:
            key, eq, val = w.partition('=')
            if key not in ('exact_lower', 'exact_upper', 'bounded_when') or not eq or key in opts:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in interval_of_ball entry')
            opts[key] = val
        sides = {s: _exact_when(opts[f'exact_{s}'], where) for s in ('lower', 'upper') if f'exact_{s}' in opts}
        if sides:
            if entry['tight']['kind'] != 'outward':
                raise DescriptionError(f'{where}: exact_lower and exact_upper belong to tight=outward')
            entry['tight']['exact_when'] = sides
        if 'bounded_when' in opts:
            entry['bounded_when'] = _bounded_when(opts['bounded_when'], where)
        return entry
    if kind == 'splits' and len(words) == 6:
        # splits AL AU BL BU from=LOWER,UPPER: two intervals that together are the operand.
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[5])
        if not m:
            raise DescriptionError(f'{where}: expected "splits AL AU BL BU from=LOWER,UPPER"')
        return {'kind': kind, 'parts': [{'lower': words[1], 'upper': words[2]}, {'lower': words[3], 'upper': words[4]}],
                'from': {'lower': m.group(1), 'upper': m.group(2)}}
    if kind == 'ball_set' and len(words) == 6:
        # ball_set CENTER RADIUS union|intersection NAME=CENTER,RADIUS NAME=CENTER,RADIUS: a ball that
        # contains the union or the intersection of two balls (Milestone 2, the enclosure interface).
        return {'kind': kind, 'center': words[1], 'radius': words[2], 'set': words[3],
                'balls': _pairs(words[4:], where, 'ball', ('center', 'radius'))}
    if kind == 'ball_splits' and len(words) == 6:
        # ball_splits CA RA CB RB from=CENTER,RADIUS: two balls that cover the two halves of a ball.
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[5])
        if not m:
            raise DescriptionError(f'{where}: expected "ball_splits CA RA CB RB from=CENTER,RADIUS"')
        return {'kind': kind, 'parts': [{'center': words[1], 'radius': words[2]},
                                        {'center': words[3], 'radius': words[4]}],
                'from': {'center': m.group(1), 'radius': m.group(2)}}
    if kind in ('certain', 'trit') and len(words) >= 4:
        # certain MASK REL ARG... NAME=A,B ... [exact | exact_when=CONDITIONS]
        # trit YES NO REL ARG ARG NAME=A,B ... [exact | exact_when=CONDITIONS]
        # A predicate of sets of real numbers, intervals or balls (Milestone 2, the enclosure
        # interface). The sets are written NAME=A,B as elsewhere; parse_kernel says, from the
        # requirements, whether they are intervals or balls (_set_kinds).
        masks = words[1:3] if kind == 'trit' else words[1:2]
        rest = words[1 + len(masks):]
        if not rest:
            raise DescriptionError(f'{where}: a {kind} entry needs a relation')
        rel = rest[0]
        n = SET_RELATION_ARITY.get(rel, 2)
        args, tail = rest[1:1 + n], rest[1 + n:]
        if len(args) != n:
            raise DescriptionError(f'{where}: {kind} {rel} has {n} argument{"s" if n > 1 else ""}')
        pairs, exact = [], None
        for w in tail:
            if w == 'exact' and exact is None:
                exact = True
            elif w.startswith('exact_when=') and exact is None:
                exact = _exact_when(w[len('exact_when='):], where)
            else:
                pairs.append(w)
        entry = {'kind': kind}
        if kind == 'trit':
            entry.update(yes=masks[0], no=masks[1])
        else:
            entry['of'] = masks[0]
        entry.update(rel=rel, args=args, sets=_pairs(pairs, where, 'set', ('a', 'b')))
        if exact is True:
            entry['exact'] = True
        elif exact is not None:
            entry['exact_when'] = exact
        return entry
    if kind == 'predicate' and len(words) == 5:
        return {'kind': kind, 'of': words[1], 'rel': words[2], 'args': words[3:5]}
    if kind == 'encloses' and len(words) >= 4:
        # Without a NAME=CENTER,RADIUS word the operands are points (Milestone 2, add_ball_2_2).
        balls, finite_when, exact_when = {}, None, None
        for w in words[4:]:
            if w.startswith('finite_when=') and finite_when is None:
                finite_when = _finite_when(w[len('finite_when='):], where)
                continue
            if w.startswith('exact_when=') and exact_when is None:
                exact_when = _exact_when(w[len('exact_when='):], where)
                continue
            m = re.fullmatch(r'([a-z][a-z0-9]*)=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', w)
            if not m or m.group(1) in balls:
                raise DescriptionError(f'{where}: bad or repeated ball {w!r}: NAME=CENTER,RADIUS')
            balls[m.group(1)] = {'center': m.group(2), 'radius': m.group(3)}
        entry = {'kind': kind, 'center': words[1], 'radius': words[2], 'set': words[3], 'balls': balls}
        if finite_when is not None:
            entry['finite_when'] = finite_when
        if exact_when is not None:
            entry['exact_when'] = exact_when
        return entry
    if kind == 'makes_ball_vector' and len(words) == 5:
        # The constructor of a BallVector (milestone2.md, "BallVector", "Values"): the centers written,
        # the radius and the flag, from the centers and the radius given.
        m = re.fullmatch(r'from=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', words[3])
        if not m or not words[4].startswith('flag=') or not words[4][len('flag='):]:
            raise DescriptionError(f'{where}: expected "makes_ball_vector CENTERS RADIUS from=CENTERS,RADIUS '
                                   f'flag=MASK", got {" ".join(words)!r}')
        return {'kind': kind, 'center': words[1], 'radius': words[2], 'flag': words[4][len('flag='):],
                'from': {'center': m.group(1), 'radius': m.group(2)}}
    if kind == 'encloses_entries' and len(words) >= 5:
        # A ball vector (milestone2.md, "BallVector"): the centers written, the one radius and the
        # mask that the result is a finite ball vector; each ball name an array of centers and a
        # radius (a scalar). radii_when: the conditions of V4 on the scalars alone, which make it
        # a statement of every length, the empty vector included (finite_when at any entry implies
        # them).
        balls, finite_when, radii_when, flag, exact, finite_from = {}, None, None, None, False, None
        for w in words[4:]:
            if w.startswith('finite_when=') and finite_when is None:
                finite_when = _finite_when(w[len('finite_when='):], where)
                continue
            if w.startswith('radii_when=') and radii_when is None:
                radii_when = _finite_when(w[len('radii_when='):], where)
                continue
            if w.startswith('finite_from=') and finite_from is None:
                # The precision from which V4 is claimed, when above the fold's minimum precision
                # (a constant of the radius kernel overflows the smallest formats below it).
                finite_from = _finite_from(w[len('finite_from='):], where)
                continue
            if w == 'exact' and not exact:
                # Exact (bv_neg_k): the result is exactly the set, entry by entry, always (the empty
                # list of conditions of exact_when).
                exact = True
                continue
            if w.startswith('exact_when=') and not exact:
                # Exact under conditions (bv_mul_pow2_k): those of every entry and of the scalars.
                exact = _exact_when(w[len('exact_when='):], where)
                continue
            if w.startswith('flag=') and flag is None:
                flag = w[len('flag='):]
                continue
            m = re.fullmatch(r'([a-z][a-z0-9]*)=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', w)
            if not m or m.group(1) in balls:
                raise DescriptionError(f'{where}: bad or repeated ball vector {w!r}: NAME=CENTERS,RADIUS')
            balls[m.group(1)] = {'center': m.group(2), 'radius': m.group(3)}
        if not flag:
            raise DescriptionError(f'{where}: an encloses_entries entry needs flag=MASK')
        entry = {'kind': kind, 'center': words[1], 'radius': words[2], 'flag': flag, 'set': words[3],
                 'balls': balls, 'finite_when': finite_when or []}
        if radii_when is not None:
            entry['radii_when'] = radii_when
        if finite_from is not None:
            entry['finite_from'] = finite_from
        if exact:
            entry['exact_when'] = [] if exact is True else exact
        return entry
    if kind == 'encloses_coefficients' and len(words) >= 5:
        # The product of two BallVectors (milestone2.md, "The product of polynomials"): the coefficients
        # written, the one radius and the flag; each ball name an array of centers and its radius.
        # finite_when: conditions of V4 over a pair of entries, one of each array (EXPR names both),
        # an entry of one array, or the count n = min(n_x, n_y); radii_when over the scalars alone;
        # count_when, conditions on the count, n, under which the bound of dot for n terms is given.
        balls, opts, flag = {}, {}, None
        for w in words[4:]:
            key, eq, val = w.partition('=')
            if key in ('finite_when', 'radii_when', 'count_when', 'finite_from') and eq and key not in opts:
                opts[key] = val
                continue
            if key == 'flag' and eq and val and flag is None:
                flag = val
                continue
            m = re.fullmatch(r'([a-z][a-z0-9]*)=([a-z][a-z0-9]*),([a-z][a-z0-9]*)', w)
            if not m or m.group(1) in balls:
                raise DescriptionError(f'{where}: bad or repeated ball vector {w!r}: NAME=CENTERS,RADIUS')
            balls[m.group(1)] = {'center': m.group(2), 'radius': m.group(3)}
        if not flag:
            raise DescriptionError(f'{where}: an encloses_coefficients entry needs flag=MASK')
        entry = {'kind': kind, 'center': words[1], 'radius': words[2], 'flag': flag, 'set': words[3], 'balls': balls,
                 'finite_when': _finite_when(opts.get('finite_when', ''), where)}
        if 'radii_when' in opts:
            entry['radii_when'] = _finite_when(opts['radii_when'], where)
        if 'count_when' in opts:
            conds = []
            for part in opts['count_when'].split(';'):
                c = re.fullmatch(r'le\((.+)\)', part)
                args = _arguments(c.group(1), where) if c else []
                if len(args) != 2 or not all(args):
                    raise DescriptionError(f'{where}: a condition of count_when is le(EXPR,K), got {part!r}')
                conds.append({'le': args[0], 'than': args[1]})
            entry['count_when'] = conds
        if 'finite_from' in opts:
            entry['finite_from'] = _finite_from(opts['finite_from'], where)
        return entry
    if kind == 'error' and len(words) >= 3:
        entry = {'kind': 'error', 'of': words[1], 'form': words[2],
                 'c': None, 'k': None, 't': None, 'when': None}
        for w in words[3:]:
            key, eq, val = w.partition('=')
            if key == 'exact_when' and eq and 'exact_when' not in entry:
                # Only when there is one: an error entry without it has the shape it always had.
                entry['exact_when'] = _exact_when(val, where)
                continue
            if key == 'exact_flag' and eq and val and 'exact_flag' not in entry:
                # A mask output that is true exactly when the conditions of exact_when hold (the step
                # of the scaling of a BallVector by a power of two): only where there is one.
                entry['exact_flag'] = val
                continue
            if not eq or key not in ('c', 'k', 't', 'when') or entry[key] is not None:
                raise DescriptionError(f'{where}: bad or repeated field {w!r} in error entry')
            entry[key] = val
        if entry['k'] is not None:
            if not re.fullmatch(r'[0-9]+', entry['k']):
                raise DescriptionError(f'{where}: k must be an integer, got {entry["k"]!r}')
            entry['k'] = int(entry['k'])
        return entry
    raise DescriptionError(f'{where}: cannot read ensures entry {" ".join(words)!r}')


# The operands may hold one level of parentheses, for `const unit_computed(K)`.
_HEAD = re.compile(r'(?:\(\s*(?P<many>[^()]*)\)|(?P<one>\S+))\s*=\s*(?P<op>[a-z][a-z0-9_]*)\(')


def _arguments(text, where):
    """The operands between a call's parentheses, split at the commas outside any parentheses (an
    operand `const up(EXPR)` holds an expression with parentheses of its own)."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                raise DescriptionError(f'{where}: unbalanced parentheses in {text!r}')
        elif ch == ',' and depth == 0:
            out.append(text[start:i])
            start = i + 1
    if depth:
        raise DescriptionError(f'{where}: unbalanced parentheses in {text!r}')
    out.append(text[start:])
    return [x.strip() for x in out] if text.strip() else []


def _stmt(text, where, lineno):
    m = _HEAD.match(text)
    if not m or not text.endswith(')'):
        raise DescriptionError(f'{where}: expected "DST = OP(ARGS)" or "(DST, ...) = KERNEL(ARGS)", got {text!r}')
    dsts = tuple(d.strip() for d in (m.group('many') or m.group('one')).split(','))
    args = []
    for a in _arguments(text[m.end():-1], where):
        words = a.split()
        if len(words) >= 2 and words[0] == 'const':
            # A constant's name holds no space: one inside an expression means nothing.
            args.append(Operand(''.join(words[1:]), const=True))
        elif words == [ZERO]:
            args.append(Operand(ZERO, const=True))
        elif len(words) == 1:
            args.append(Operand(words[0]))
        else:
            raise DescriptionError(f'{where}: bad operand {a!r}')
    return Stmt(dsts, m.group('op'), tuple(args), lineno)


def parse_kernel(text, path):
    k = Kernel(name=None, path=path)
    single = {'kernel', 'value', 'min_precision', 'theorem', 'source', 'license', 'status',
              'ce_variant', 'cone_exempt', 'domain', 'ieee_status', 'ieee_theorem', 'entry', 'ieee_only',
              'ieee', 'ieee_finite', 'ieee_finite_result', 'ordinary_inline'} | set(IEEE_THEOREM_KEYS)
    seen = set()
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        where = f'{path}:{lineno}'
        if not line:
            continue
        header = re.fullmatch(r'([a-z_]+):\s*(.*)', line)
        if not header:
            k.body.append(_stmt(line, where, lineno))
            continue
        key, val = header.group(1), header.group(2).strip()
        if key in single:
            if key in seen:
                raise DescriptionError(f'{where}: {key} given twice')
            seen.add(key)
        if key == 'kernel':
            k.name = val
        elif key == 'input':
            g, cls = _group(val, where, INPUT_CLASSES)
            k.inputs.append(g)
            if cls:
                getattr(k, cls).add(g.name)
        elif key == 'output':
            k.outputs.append(_group(val, where)[0])
        elif key == 'value':
            k.value = val
        elif key == 'requires':
            words = val.split()
            if not words:
                raise DescriptionError(f'{where}: empty requires')
            k.requires.append(tuple(words))
        elif key == 'ensures':
            k.ensures.append(_ensures(val.split(), where))
        elif key == 'min_precision':
            if not re.fullmatch(r'[0-9]+', val):
                raise DescriptionError(f'{where}: min_precision must be an integer')
            k.min_precision = int(val)
        elif key in ('theorem', 'ieee_theorem') + IEEE_THEOREM_KEYS:
            parts = val.split()
            if len(parts) != 2:
                raise DescriptionError(f'{where}: expected "{key}: FILE NAME"')
            setattr(k, key, tuple(parts))
        elif key in ('source', 'license', 'status', 'ce_variant', 'cone_exempt', 'domain', 'ieee_status'):
            setattr(k, key, val)
        elif key == 'ordinary_inline':
            if not val:
                raise DescriptionError(f'{where}: expected "ordinary_inline: REASON"')
            k.ordinary_inline = val
        elif key == 'ieee':
            words = val.split()
            if not words or any(w not in IEEE_STATEMENTS for w in words) or len(set(words)) < len(words):
                raise DescriptionError(f'{where}: expected "ieee: " and some of {", ".join(IEEE_STATEMENTS)}')
            k.ieee = tuple(w for w in IEEE_STATEMENTS if w in words)
        elif key in ('ieee_finite', 'ieee_finite_result'):
            conditions = _finite_when(val.replace(' ', ''), where)
            if not conditions:
                raise DescriptionError(f'{where}: {key} needs at least one condition')
            setattr(k, key, conditions)
        elif key in ('entry', 'ieee_only'):
            if val != 'yes':
                raise DescriptionError(f'{where}: expected "{key}: yes" (leave the line out otherwise)')
            setattr(k, key, True)
        elif key in ('unused', 'guard_pending'):
            name, _, why = val.partition(' ')
            table = getattr(k, key)
            if not name or not why.strip() or name in table:
                raise DescriptionError(f'{where}: expected "{key}: INPUT REASON", once per input')
            table[name] = why.strip()
        else:
            raise DescriptionError(f'{where}: unknown key {key!r}')
    if k.name is None:
        raise DescriptionError(f'{path}: no "kernel:" line')
    if k.extended:
        # In the extended domain an encloses entry always says when the ball is finite (an empty
        # list when no condition is proved), as extends does.
        for e in k.ensures:
            if e['kind'] == 'encloses':
                e.setdefault('finite_when', [])
    for i, e in enumerate(k.ensures):
        if e['kind'] in ('certain', 'trit'):
            k.ensures[i] = _set_kinds(e, k)
    if not KERNEL_NAME.match(k.name):
        raise DescriptionError(f'{path}: bad kernel name {k.name!r}')
    if not k.inputs or not k.outputs:
        raise DescriptionError(f'{path}: a kernel needs at least one input and one output')
    return k


class KernelSet(dict):
    """{name: Kernel} in output order, and the folds of the same directory, {name: Fold} by name,
    in `folds`. Printers read the folds from here, so that a set of kernels without folds (the
    test kernels, a dict built by hand) prints exactly what it printed before folds existed."""

    def __init__(self, *args, folds=None):
        super().__init__(*args)
        self.folds = dict(folds or {})


# The two orders of a fold (proofs/theories/Folds.v): fold_seq and fold_lanes.
ORDERS = ('sequential', 'lanes')


@dataclass
class Fold:
    """A loop of kernels along arrays (milestone2.md, "Folds, the extension of the IR")."""
    name: str
    path: str
    arrays: list = field(default_factory=list)      # Groups, in order
    roles: dict = field(default_factory=dict)       # array name -> 'stored' or 'supplied'
    scalars: list = field(default_factory=list)     # Groups given once and passed to every step (a map)
    state: Group = None         # the first group of the state (a map's mask)
    states: list = field(default_factory=list)      # every group of the state, in order (a fold of maxima: two)
    step: tuple = None          # (kernel, argument group names, the line's destination)
    combine: tuple = None       # the same (for a map, the operation and), or None
    record: tuple = None        # a ball vector: the state's update from the element written (a step of a fold of maxima)
    # Every record line and every combine line, in order (record and combine are the first): a ball
    # vector that is exact under conditions has a second of each, the and of the step's mask into a
    # mask of the state (records[1]) and of two such masks (combines[1]).
    records: list = field(default_factory=list)
    combines: list = field(default_factory=list)
    radius: tuple = None        # a ball vector: the kernel of its radius, on the state's limb and scalars
    # The product of two BallVectors (bv_conv_k): the convolution of its centers (a fold with
    # coefficients:), the count min(n_x, n_y) as a number of T (its name), and the kernel of the bound
    # of a dot product of that many terms, run once (a call on the count).
    centers: str = None
    count: str = None
    bound: tuple = None
    finish: tuple = None        # (kernel, argument group names, destination group names), or None
    orders: tuple = ()
    writes: list = field(default_factory=list)      # Groups: the arrays a map writes, one element per step
    check: str = None           # a map: the kernel that tests a written element and gives its canonical NaN
    coefficients: str = None    # a convolution: the fold of each coefficient (a dot product)
    outputs: list = field(default_factory=list)     # Groups: the finish's outputs as the fold names them
    value: str = None
    requires: list = field(default_factory=list)
    ensures: list = field(default_factory=list)
    min_precision: int = None
    theorem: str = None         # the file of F_seq_correct and F_lanes_correct
    ieee_theorem: str = None    # the file of F_seq_ieee_correct and F_lanes_ieee_correct
    source: str = None
    license: str = None
    status: str = None
    domain: str = None
    declared: set = field(default_factory=set)      # the header lines given

    @property
    def extended(self):
        return self.domain == 'extended'

    @property
    def is_map(self):
        """A map: the step writes an element of each written array, from the elements read."""
        return bool(self.writes) and not self.coefficients and not self.record

    @property
    def is_bv(self):
        """A ball vector (milestone2.md, "BallVector"): a map whose state is that of a fold of maxima,
        updated by `record` from each element written, and whose finish gives one radius."""
        return bool(self.record) and not self.centers

    @property
    def is_bv_conv(self):
        """The product of two BallVectors (milestone2.md, "The product of polynomials"): the
        convolution `centers` of their centers, the maxima of the operands' centers by `record` lines
        on the arrays read, the count, the bound, the radius and a finish of two masks."""
        return bool(self.centers)

    @property
    def exact_mask(self):
        """A ball vector exact under conditions (bv_mul_pow2_k): (the state's third group, a mask that
        starts true, and the step's second output, the mask that its entry is exact), which the
        second record line and-s together; None for every other fold."""
        if self.is_bv and len(self.states) == 3 and self.step and len(self.step[2]) == 2:
            return self.states[2].name, self.step[2][1]
        return None

    @property
    def is_conv(self):
        """A convolution: each element written is a fold of the dot product on terms of the two
        arrays read."""
        return bool(self.coefficients)

    def results(self):
        """The groups the fold returns: the finish's outputs, or the state when there is none (for
        a map, its mask; the written arrays are apart, write_limbs)."""
        return self.outputs if self.finish else list(self.states)

    @property
    def is_max(self):
        """A fold of maxima: it claims an upper bound of the largest value of an element."""
        return any(e['kind'] == 'upper' and e.get('over') == 'max' for e in self.ensures)

    def state_names(self):
        return tuple(g.name for g in self.states)

    def state_limbs(self):
        return [v for g in self.states for v in g.limbs]

    def state_kinds(self):
        return [g.kind for g in self.states for _ in g.limbs]

    def array_limbs(self):
        return [v for g in self.arrays for v in g.limbs]

    def scalar_limbs(self):
        return [v for g in self.scalars for v in g.limbs]

    def write_limbs(self):
        return [v for g in self.writes for v in g.limbs]

    def theorem_name(self, order):
        return f'{self.name}_{ORDER_SUFFIX[order]}_correct'

    def ieee_theorem_name(self, order):
        """The theorem of the IEEE-model statement of one order (of a convolution, of its one
        statement: F_ieee_correct)."""
        if self.is_conv or self.is_bv_conv:
            return f'{self.name}_ieee_correct'
        return f'{self.name}_{ORDER_SUFFIX[order]}_ieee_correct'


# What each order is called in the names of the C++ functions, the Rocq definitions and the
# statements: F_seq and F_lanes (F_packed is the packed form of the lane order).
ORDER_SUFFIX = {'sequential': 'seq', 'lanes': 'lanes'}

_CALL = re.compile(r'(?:\(\s*(?P<many>[^()]*)\)|(?P<one>[a-z][a-z0-9]*))\s*=\s*'
                   r'(?P<op>[a-z][a-z0-9_]*)\((?P<args>[^()]*)\)\Z')


def _fold_call(text, where, key):
    m = _CALL.match(text.strip())
    if not m:
        raise DescriptionError(f'{where}: expected "{key}: DST = KERNEL(GROUP, ...)", got {text!r}')
    dsts = tuple(d.strip() for d in (m.group('many') or m.group('one')).split(','))
    args = tuple(a.strip() for a in m.group('args').split(',')) if m.group('args').strip() else ()
    for n in dsts + args:
        if not VALUE_NAME.match(n):
            raise DescriptionError(f'{where}: {n!r} is not the name of a group')
    return m.group('op'), args, dsts


def parse_fold(text, path):
    fd = Fold(name=None, path=path)
    # record and combine may be given more than once (a ball vector exact under conditions: the and of
    # a mask of the step into the state); the rules say which folds may.
    single = {'fold', 'arrays', 'scalars', 'state', 'step', 'orders', 'writes', 'check', 'finish',
              'value', 'min_precision', 'theorem', 'source', 'license', 'status', 'domain', 'coefficients',
              'radius', 'centers', 'count', 'bound'}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        where = f'{path}:{lineno}'
        if not line:
            continue
        header = re.fullmatch(r'([a-z_]+):\s*(.*)', line)
        if not header:
            raise DescriptionError(f'{where}: a fold has no listing of its own (its step, combination '
                                   f'and finish are kernels): {line!r}')
        key, val = header.group(1), header.group(2).strip()
        if key in single:
            if key in fd.declared:
                raise DescriptionError(f'{where}: {key} given twice')
            fd.declared.add(key)
        if key == 'fold':
            fd.name = val
        elif key in ('arrays', 'scalars'):
            what = 'an array' if key == 'arrays' else 'a scalar'
            for part in val.split(','):
                g, cls = _group(part, where, INPUT_CLASSES)
                if cls is None:
                    raise DescriptionError(f'{where}: {what} is declared stored (written through Kairn) or '
                                           f'supplied (the program\'s): {part.strip()!r}')
                if g.kind != LIMB:
                    raise DescriptionError(f'{where}: {what} holds limbs, not masks')
                (fd.arrays if key == 'arrays' else fd.scalars).append(g)
                fd.roles[g.name] = cls
        elif key == 'state':
            fd.states = [_group(part, where)[0] for part in val.split(',')]
            fd.state = fd.states[0]
        elif key in ('combine', 'record'):
            call = _fold_call(val, where, key)
            (fd.combines if key == 'combine' else fd.records).append(call)
            if key not in fd.declared:
                fd.declared.add(key)
                setattr(fd, key, call)
        elif key in ('step', 'radius', 'bound'):
            setattr(fd, key, _fold_call(val, where, key))
        elif key == 'centers':
            if not KERNEL_NAME.match(val):
                raise DescriptionError(f'{where}: expected "centers: CONVOLUTION", got {val!r}')
            fd.centers = val
        elif key == 'count':
            # The one count a fold may make: the smaller of the lengths of its two arrays, as a number
            # of T rounded up (exact below 2^p), the largest number of terms of a coefficient.
            m = re.fullmatch(r'([a-z][a-z0-9]*)\s*=\s*min\(n_x,\s*n_y\)', val)
            if not m:
                raise DescriptionError(f'{where}: expected "count: NAME = min(n_x, n_y)", got {val!r}')
            fd.count = m.group(1)
        elif key == 'finish':
            fd.finish = None if val == 'none' else _fold_call(val, where, key)
        elif key == 'orders':
            fd.orders = tuple(w.strip() for w in val.split(','))
        elif key == 'writes':
            fd.writes = [] if val == 'none' else [_group(part, where)[0] for part in val.split(',')]
        elif key == 'check':
            if not KERNEL_NAME.match(val):
                raise DescriptionError(f'{where}: expected "check: KERNEL", got {val!r}')
            fd.check = val
        elif key == 'coefficients':
            if not KERNEL_NAME.match(val):
                raise DescriptionError(f'{where}: expected "coefficients: FOLD", got {val!r}')
            fd.coefficients = val
        elif key == 'output':
            fd.outputs.append(_group(val, where)[0])
        elif key == 'value':
            fd.value = val
        elif key == 'requires':
            words = val.split()
            if not words:
                raise DescriptionError(f'{where}: empty requires')
            fd.requires.append(tuple(words))
        elif key == 'ensures':
            fd.ensures.append(_ensures(val.split(), where))
        elif key == 'min_precision':
            if not re.fullmatch(r'[0-9]+', val):
                raise DescriptionError(f'{where}: min_precision must be an integer')
            fd.min_precision = int(val)
        elif key == 'theorem':
            if len(val.split()) != 1:
                raise DescriptionError(f'{where}: expected "theorem: FILE" (its theorems are F_seq_correct '
                                       'and F_lanes_correct)')
            fd.theorem = val
        elif key == 'ieee_theorem':
            if len(val.split()) != 1:
                raise DescriptionError(f'{where}: expected "ieee_theorem: FILE" (its theorems are '
                                       'F_seq_ieee_correct and F_lanes_ieee_correct)')
            fd.ieee_theorem = val
        elif key in ('source', 'license', 'status', 'domain'):
            setattr(fd, key, val)
        else:
            raise DescriptionError(f'{where}: unknown key {key!r} in a fold')
    if fd.name is None:
        raise DescriptionError(f'{path}: no "fold:" line')
    if not KERNEL_NAME.match(fd.name):
        raise DescriptionError(f'{path}: bad fold name {fd.name!r}')
    # A convolution has no step of its own: that of the fold of its coefficients; nor has the product
    # of two BallVectors, whose centers are a convolution's.
    for key in ('arrays', 'state', 'orders', 'writes', 'finish') + (() if fd.coefficients or fd.centers else ('step',)):
        if key not in fd.declared:
            raise DescriptionError(f'{path}: a fold needs "{key}:"' +
                                   (' (none, when there is none)' if key in ('writes', 'finish') else ''))
    return fd


# The record of the names of the constants up(EXPR) in the Rocq models: a file next to the
# directory of the kernel descriptions (gen/constant_names.json for gen/kernels), read by
# load_kernels and written by build (rocq.constant_names_file). EXPR is written as the
# descriptions write it, without spaces (the text of ir.up of the operand).
CONSTANT_NAMES = 'constant_names.json'
CONSTANT_NAMES_ABOUT = (
    'The names of the constants up(EXPR) in proofs/gen/Model.v and IeeeModel.v, by EXPR as the kernel '
    'descriptions write it, without spaces. Hand-written proofs use these names, so a name never '
    'changes: the generator consults this record first, build adds an entry only for a constant that '
    'is new, and nothing removes one (gen/README.md, "The operations").')


def constant_names_path(directory):
    return os.path.join(os.path.dirname(os.path.abspath(directory)), CONSTANT_NAMES)


def load_constant_names(directory):
    """The record next to a directory of descriptions, {EXPR: name}, or None when there is none."""
    path = constant_names_path(directory)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        try:
            doc = json.load(f)
        except ValueError as e:
            raise DescriptionError(f'{path}: {e}')
    names = doc.get('names') if isinstance(doc, dict) else None
    if not isinstance(names, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in names.items()):
        raise DescriptionError(f'{path}: expected {{"about": ..., "names": {{EXPR: NAME, ...}}}}')
    if len(set(names.values())) != len(names):
        raise DescriptionError(f'{path}: a name is given to two constants')
    for text, name in names.items():
        if not re.fullmatch(r'up_[a-z][a-z0-9_]*_[0-9]+', name) or ' ' in text:
            raise DescriptionError(f'{path}: {text!r}: {name!r} is not a name up_K_i, or EXPR has a space')
    return names


def constant_names_text(record):
    """The record as build writes it: its entries in the order of their names."""
    entries = sorted(record.items(), key=lambda kv: (kv[1].rsplit('_', 1)[0], int(kv[1].rsplit('_', 1)[1])))
    lines = ['{', f'  "about": {json.dumps(CONSTANT_NAMES_ABOUT)},', '  "names": {']
    lines += [f'    {json.dumps(text)}: {json.dumps(name)}{"," if i + 1 < len(entries) else ""}'
              for i, (text, name) in enumerate(entries)]
    lines += ['  }', '}']
    return '\n'.join(lines) + '\n'


def load_kernels(directory):
    """Every *.kernel file of a directory, as {name: Kernel} in output order (see `ordered`), each
    with the record of constant names next to the directory, if there is one, and every *.fold file,
    in the set's `folds`."""
    kernels, folds = {}, {}
    record = load_constant_names(directory)
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(('.kernel', '.fold')):
            continue
        path = os.path.join(directory, fn)
        with open(path, encoding='utf-8') as f:
            text = f.read()
        if fn.endswith('.fold'):
            fd = parse_fold(text, fn)
            if fn != fd.name + '.fold':
                raise DescriptionError(f'{fn}: fold {fd.name} must be in {fd.name}.fold')
            folds[fd.name] = fd
            continue
        k = parse_kernel(text, fn)
        if k.name in kernels:
            raise DescriptionError(f'{fn}: kernel {k.name} is also defined in {kernels[k.name].path}')
        if fn != k.name + '.kernel':
            raise DescriptionError(f'{fn}: kernel {k.name} must be in {k.name}.kernel')
        k.constant_names = record
        kernels[k.name] = k
    for name in folds:
        if name in kernels:
            raise DescriptionError(f'{name}.fold: {name} is also the name of a kernel')
    return ordered(kernels, folds)


def ordered(kernels, folds=None):
    """Callees before callers (Rocq needs it), otherwise by input limb count, then by name. The
    folds are kept: those given, or those of `kernels` if it is a KernelSet."""
    if folds is None:
        folds = getattr(kernels, 'folds', {})
    out = KernelSet(folds=folds)

    def visit(name, path):
        if name in out:
            return
        if name in path:
            raise DescriptionError(f'kernel {name}: calls itself through {" -> ".join(path)}')
        for st in kernels[name].body:
            if st.is_call and st.op in kernels:
                visit(st.op, path + (name,))
        out[name] = kernels[name]

    for name in sorted(kernels, key=lambda n: (max(len(g.limbs) for g in kernels[n].inputs), n)):
        visit(name, ())
    return out


@dataclass(frozen=True)
class Prim:
    """One operation of a flattened kernel."""
    dst: str
    op: str
    args: tuple


@dataclass(frozen=True)
class CallMark:
    """Where an inlined call starts, in flattened names (the C++ printer writes it as a comment)."""
    dsts: tuple
    callee: str
    args: tuple


def flatten(kernel, kernels):
    """The kernel's body with every call replaced by the callee's body, as the C++ is emitted.

    Names the kernel defines are kept. A value defined inside a callee is renamed D_V, where D is
    the first name the call site defines and V the value's name in the callee (recursively), so
    that every name of the result is unique. Returns a list of Prim and CallMark.
    """
    items = []
    _inline(items, kernel, kernels, {v: Operand(v) for v in kernel.input_limbs},
            {v: v for v in kernel.output_limbs}, '')
    return items


def _inline(items, k, kernels, env, outnames, prefix):
    local = dict(env)

    def name_of(v):
        return outnames[v] if v in outnames else (f'{prefix}_{v}' if prefix else v)

    for st in k.body:
        args = tuple(a if a.const else local[a.name] for a in st.args)
        names = tuple(name_of(d) for d in st.dsts)
        for d, n in zip(st.dsts, names):
            local[d] = Operand(n)
        if st.is_call:
            callee = kernels[st.op]
            items.append(CallMark(names, st.op, args))
            _inline(items, callee, kernels, dict(zip(callee.input_limbs, args)),
                    dict(zip(callee.output_limbs, names)), names[0])
        else:
            items.append(Prim(names[0], st.op, args))


def inline_call(kernel, kernels, args, prefix):
    """One call of `kernel` on the operands `args` (one per input value), flattened as a call
    site of a fold's loop: every value it defines, its outputs included, is named PREFIX_V, so
    that no name of the result can be a name of the fold (which have no underscore). Returns
    (items, the names of the outputs)."""
    items = [CallMark(tuple(f'{prefix}_{v}' for v in kernel.output_limbs), kernel.name, tuple(args))]
    _inline(items, kernel, kernels, dict(zip(kernel.input_limbs, args)), {}, prefix)
    return items, [f'{prefix}_{v}' for v in kernel.output_limbs]


def prims(kernel, kernels):
    return [it for it in flatten(kernel, kernels) if isinstance(it, Prim)]


def muladd_sites(kernel, kernels):
    """Flattened names of the kernel's muladd values: each is a choice the compiler makes."""
    return [p.dst for p in prims(kernel, kernels) if p.op == 'muladd']


def kinds(kernel, kernels):
    """The kind (LIMB or MASK) of every flattened value."""
    out = dict(zip(kernel.input_limbs, kernel.input_kinds))
    for p in prims(kernel, kernels):
        out[p.dst] = OPS[p.op][1]
    return out


def constants(kernel):
    """The names of the constants the kernel's own statements use (not its callees')."""
    return sorted({a.name for st in kernel.body for a in st.args if a.const})


def flops(kernel, kernels):
    """Floating-point operations after inlining; an FMA counts as one, and so do a guard and a
    multiplication by infinity."""
    arith = {'add', 'sub', 'fma', 'fms', 'fnma', 'prod', 'muladd', 'guard', 'times_inf'}
    return sum(1 for p in prims(kernel, kernels) if p.op in arith)
