# What holds today

Kairn's public headers cover `Expansion<T, 1>`, `Expansion<T, 2>`, `Ball<T, 1>`, `Ball<T, 2>` and
`Interval<T, 1>`, `Interval<T, 2>` for `T` = `float` and `double`, `Packed` and the arrays of
numbers, the functions on arrays and the accumulator. This page says, for each
operation, what is proved, what the
library returns at overflow and for infinite and NaN values, and what is not proved yet. It
describes the repository as `gen/claims.json` stands in this version; the compiler enforces the
current status on its own (below), so the code cannot fall behind it. The design is in the
[Phase 0 report](../developer/design/phase0/index.md) and the
[Milestone 1 statements](../developer/design/milestone1.md).

Notation, from [Numbers](../developer/design/phase0/numbers.md#notation): $u = 2^{-p}$ is the unit
roundoff of a limb ($2^{-53}$ for `double`, $2^{-24}$ for `float`), $\eta$ its smallest
subnormal number ($2^{-1074}$, $2^{-149}$), and $2^{e_{\max}}$ its overflow threshold ($2^{1024}$,
$2^{128}$). A two-limb number is *normalized* when its leading limb is the sum of the two rounded
to nearest, and *canonical* when it is finite and normalized, or $(\pm\infty, 0)$, or
$(\mathrm{NaN}, \mathrm{NaN})$. Every constructor and operation returns canonical numbers and
requires canonical operands; a one-limb number is any value of `T`.

## Proved, and UNVERIFIED

Every operation is computed by one generated kernel, and `gen/claims.json` says what that kernel
claims and whether its claims are **proved**: Rocq accepts a proof of the generated statement, and
the audit finds no axiom beyond the four allowed
([Architecture](../developer/architecture.md#the-formal-model)). Any other kernel is
**UNVERIFIED**: its statement is a target, tested by the oracle in exact arithmetic but not proved.

An UNVERIFIED operation compiles only when one of its operands carries the marker
`kairn::unverified(...)`: `kairn::unverified(x) - y`, `kairn::unverified(x) < y`,
`kairn::to_down(kairn::unverified(x))`, `x -= kairn::unverified(y)`,
`kairn::Expansion<double, 2>(kairn::unverified(a))`. The marker applies to the one operation it is
an operand of, and the result is an ordinary value, so each unproved step of a computation is
visible in the source. It may be put on a `float` or `double` operand too (it converts back to that
type), so that code generic over `T` and the k-numbers can be written once, and it is accepted on
proved operations as well, so that code written with it keeps compiling when a proof lands. A
marked left operand of `+=` does not compile: it would modify a copy. `from_limbs` has no marked
form, since its operand is a pointer.

Each operation is gated on the kernel it really calls, constructors and the narrowing to one limb
included, and no operation can compile through a conversion to another kernel: `x + a` with a
limb `a` is the form of `add_2_1_full`, never `x + Expansion(a)` with `add_2_2_full`, and a ball
times a `T` is the scaling, never a product with a point ball. The tests compile each such case
against a copy of the headers in which only that kernel is UNVERIFIED (`api.reject.*`).

Which kernels are proved is read from `include/kairn/gen/bounds.hpp`, which the generator writes
from `gen/claims.json`. When a proof is checked and the generator is rerun, the operation compiles
without the marker. `kairn::traits` exports error constants only for proved operations: the entry
of an UNVERIFIED one has `verified == false` and no constants to read, so that no client bound can
be built on a number that is only a target.

In this version every kernel that an operation of these headers calls is proved, so no operation
needs the marker; the kernels of Milestone 2 written so far are proved too, and the functions on
arrays call loops all of whose kernels are proved ([below](#sums-dot-products-and-maps-of-arrays));
a function on arrays has no marked form, and compiles only while the kernels of its loop are. It is how the
operations still to come (three and four limbs, division, square root) will ship before their
proofs.

## The operations

Each kernel has a page in the [reference](../reference/index.md), generated from
`gen/claims.json`: its statement, the theorem and file that prove it, its constants for `float`
and `double`, and what the brute-force runs measured. In short, for canonical operands $x$, $y$
and a limb $a$, with $z$ the result. The second column is the claim of the kernel's finite core,
proved in the *real model*, where no operation overflows; it is what a result satisfies whenever
it is finite. The third column is proved in Flocq's model of IEEE 754, where operations overflow
and values may be infinite or NaN ([below](#overflow-and-non-finite-values)).

| Operation (kernel) | When the result is finite, proved in the real model | Infinities, NaN and overflow, proved in the IEEE model |
|---|---|---|
| `x + y` ([`add_2_2_full`](../reference/add_2_2_full.md)) | $z$ normalized, $\lvert z - (x + y)\rvert \le \frac{3u^2}{1 - 4u}\lvert x + y\rvert$ | F1 to F5; finite when $\lvert x\rvert, \lvert y\rvert \le 2^{e_{\max}-2}$ |
| `x * y` ([`mul_2_2_full`](../reference/mul_2_2_full.md)) | $z$ normalized, $\lvert z - xy\rvert \le 4u^2\lvert xy\rvert + \tfrac32\eta$ | F1 to F5; finite when $\lvert xy\rvert \le 2^{e_{\max}-1}$ |
| `x + a`, `a + x` ([`add_2_1_full`](../reference/add_2_1_full.md)) | $z$ normalized, $\lvert z - (x + a)\rvert \le 2u^2\lvert x + a\rvert$ | F1 to F5; finite when $\lvert x\rvert, \lvert a\rvert \le 2^{e_{\max}-2}$ |
| `x * a`, `a * x` ([`mul_2_1_full_entry`](../reference/mul_2_1_full_entry.md)) | $z$ normalized, $\lvert z - xa\rvert \le 2u^2\lvert xa\rvert + \eta$ | F1 to F5; finite when $\lvert xa\rvert \le 2^{e_{\max}-1}$ |
| `add_fast(x, y)` ([`add_fast_2_2_full`](../reference/add_fast_2_2_full.md)) | $z$ normalized, $\lvert z - (x + y)\rvert \le 3u^2(\lvert x\rvert + \lvert y\rvert)$ | F1 to F5; finite as for `x + y` |
| `x - y`, `x - a`, `a - x` ([`sub_2_2_full`](../reference/sub_2_2_full.md), [`sub_2_1_full`](../reference/sub_2_1_full.md), [`sub_1_2_full`](../reference/sub_1_2_full.md)) | those of `x + y` and `x + a` | F1 to F5; finite as for `x + y` and `x + a` |
| `ldexp(x, n)`, `half(x)` ([`mul_pow2_2_full`](../reference/mul_pow2_2_full.md)) | $z$ normalized, $\lvert z - 2^n x\rvert \le \eta$, when $2^n$ is a number of `T` ([below](#overflow-and-non-finite-values) for the other $n$) | F1 to F5; finite when $\lvert 2^n x\rvert \le 2^{e_{\max}-1}$ |
| `-x`, `abs(x)` ([`neg_2`](../reference/neg_2.md), [`abs_2`](../reference/abs_2.md)) | exact, normalized | exact: the infinity with its sign changed or removed; NaN stays NaN |
| `<`, `<=`, `>`, `>=`, `==`, `!=` (the `lt`, `le` and `eq` kernels of [Comparisons](../reference/index.md#comparisons)) | the truth about the exact values | the truth in the extended reals; false with a NaN, as for `T` (`!=` true) |
| `to_nearest`, `to_down`, `to_up`, `abs_upper` ([`to_nearest_2`](../reference/to_nearest_2.md), [`to_down_2`](../reference/to_down_2.md), [`to_up_2`](../reference/to_up_2.md), [`abs_upper_2`](../reference/abs_upper_2.md)) | the exact rounding to `T` | the rounding with overflow ($\pm\infty$ beyond the largest finite `T`); an infinity or NaN gives itself |
| constructors ([`make_2`](../reference/make_2.md), [`make_2_limbs`](../reference/make_2_limbs.md), [`ball_make_1`](../reference/ball_make_1.md), [`ball_make_2`](../reference/ball_make_2.md)) | | the value given, canonical; for a ball, below |
| one limb: `+`, `-`, `*`, `add_fast`, `ldexp`, `half` ([`add_1_1`](../reference/add_1_1.md), [`mul_1_1`](../reference/mul_1_1.md)) | one rounding to nearest: $\lvert z - v\rvert \le \frac{u}{1 + u}\lvert v\rvert$, plus $\tfrac12\eta$ for products (`ldexp`: when $2^n$ is a number of `T`, [below](#overflow-and-non-finite-values) for the other $n$) | the IEEE 754 operation |
| one limb: `-x`, `abs`, comparisons, conversions | exact (no kernel) | the IEEE 754 operation |
| `Ball`: `+`, `-`, `*`, scaling by a `T`, `-X` (the kernels of [Ball operations](../reference/index.md#ball-operations)) | containment: $x \circ y \in Z$ for all $x \in X$, $y \in Y$; for two limbs the center is normalized | B1 to B4 (B1 to B3 for `-X`): containment in every case, the empty set and the whole line included; a finite ball when no $x \circ y$ exceeds $2^{e_{\max}-2}$ in magnitude ($2^{e_{\max}-4}$ for the product of one-limb balls) |
| `Ball`: `ldexp(X, n)`, `half(X)` ([`ball_mul_pow2_1_full`](../reference/ball_mul_pow2_1_full.md), [`ball_mul_pow2_2_full`](../reference/ball_mul_pow2_2_full.md)) | containment of $2^n x$ for all $x \in X$, and the result is $2^n X$ exactly when each limb of its center and its radius is zero or above the smallest normal number of `T`; when $2^n$ is a number of `T` ([below](#overflow-and-non-finite-values) for the other $n$) | B1 to B4; a finite ball when $(\lvert c\rvert + r)\,2^n \le 2^{e_{\max}-2}$ |
| `Ball`: `X.certainly_positive()`, `X.certainly_negative()`, `X.certainly_zero()` ([`ball_positive_k`](../reference/ball_positive_1.md), [`ball_negative_k`](../reference/ball_negative_1.md), [`ball_zero_k`](../reference/ball_zero_1.md)) | exactly whether every member is positive, negative, or zero | false for the empty set and for the whole line |
| the building blocks on `T`: `two_sum`, `fast_two_sum`, `two_prod`, `next_up`, `next_down`, `radd`, `rmul`, `add_down`, `add_up`, `sub_down`, `sub_up`, `mul_down`, `mul_up` ([Building blocks on T](../reference/index.md#building-blocks-on-t)) | each its kernel's statement: an exact sum, an exact product above $2^{2p-1}\eta$, an upper bound for radii, the exact rounding down or up of a sum, a bound of a product on the side asked for | the neighbors, the directed sums and the directed products on every value of `T`; `radd`, `rmul` a NaN for a NaN or $0 \cdot \infty$; `two_sum`, `fast_two_sum`, `two_prod` stated for finite operands, which their pages say more of |
| `Interval`: constructors, `-X`, `X.hull(Y)`, `X.intersection(Y)` (the `interval_make`, `interval_neg`, `interval_hull` and `interval_intersection` kernels of [Interval operations](../reference/index.md#interval-operations)) | | the interval given, or the whole line for a NaN bound and the empty set for reversed bounds ([below](#intervals)); the negation, the hull and the intersection exactly |
| `Interval`: `X + Y`, `X - Y`, `X * Y` (`interval_add_k`, `interval_sub_k`, `interval_mul_k`) | | I1 to I5 ([below](#intervals)): containment in every case, unbounded and empty operands included; one limb: the tightest interval of `T` for sums and differences, for products the tightest or one number of `T` wider on each side; two limbs: each bound within about $8u^2$ (sums) or $10u^2$ (products) of the exact one, relative to it, plus about twice the smallest normal number |
| `Interval`: `X.midpoint()`, `X.radius()`, `X.mid_rad()`, `X.split()`, `Ball<T, k>(X)`, `Interval<T, k>(B)` ([`interval_mid_rad_k`](../reference/interval_mid_rad_1.md), [`interval_split_k`](../reference/interval_split_1.md), [`interval_to_ball_k`](../reference/interval_to_ball_1.md), [`ball_to_interval_k`](../reference/ball_to_interval_1.md)) | | one limb: the midpoint within one rounding and $\eta$ of the exact one, inside the interval, with the smallest radius of `T` for it; two limbs: within $\frac{3u^2}{1-4u}$ relative and $2\eta$, inside, with a radius that covers the interval; the values of `mid` and `rad` of IEEE 1788 on the special intervals; two nonempty parts that are the interval and meet at a point of it, **not claimed the midpoint**; the conversions contain what they convert, the interval of a ball of one limb being the smallest of `T` |
| `Interval`: `is_empty()`, `is_whole()`, `contains(t)`, `contains(Y)`, the signs, `less`, `less_equal`, `equal` and mirrors, `member`, `ieee1788::equal`, `subset`, `interior`, `disjoint` (the `interval_` kernels of [One enclosure interface](../reference/enclosure.md)) | | exact, one limb and two; the three-valued comparisons return a `Trit`, unknown with an empty operand; the relations of IEEE 1788 with the standard's readings of the empty set |
| `Ball`: `contains(t)`, `contains(Y)`, `less`, `less_equal`, `equal` and mirrors, `member`, `hull`, `intersection`, `split`, `from_interval` and `from_bounds` of one limb, `lower()` and `upper()` of two (the `ball_` kernels of [One enclosure interface](../reference/enclosure.md)) | | one limb: the tests exact, the comparisons exact when $r_x + r_y \le \Omega$; two limbs: certain, an answer given is right, none is claimed near the boundary; the hull and the intersection contain what they must, an operand returned as it is when the other is special; the split covers $[c - r, c]$ and $[c, c + r]$, not claimed inside or smaller |
| `Ball`: `X.lower_as<T>()`, `X.upper_as<T>()`, `lower()`, `upper()` of one limb, `Ball<T, 2>::from_interval(lo, hi)` and `from_bounds(lo, hi)`, `Ball<T, 1>(X)` of a ball of two limbs ([`ball_lower_as_1`](../reference/ball_lower_as_1.md), [`ball_lower_as_2`](../reference/ball_lower_as_2.md), [`ball_from_interval_2`](../reference/ball_from_interval_2.md), [`ball_narrow_2_1`](../reference/ball_narrow_2_1.md)) | | a bound of every member, $+\infty$ and $-\infty$ for the empty set: for one limb exactly $\mathrm{RD}(c - r)$ and $\mathrm{RU}(c + r)$, for two within $5u(\lvert c\rvert + r) + 3\eta$ of $c \mp r$; a ball of two limbs that contains $[lo, hi]$, with the exact midpoint for its center when the halves are; a ball of one limb that contains the ball of two |
| `BallVector`: constructors, `-x`, `x + y`, `x - y`, `x * a`, `ldexp`, `half`, `convolution` (the loops `bv_make_k`, `bv_neg_k`, `bv_add_k`, `bv_sub_k`, `bv_scale_k`, `bv_mul_pow2_k`, `bv_conv_k`: [Ball vectors](../reference/ball_vector.md)); `axpy` and `norm_upper`, compositions of two loops | containment of every result on members, entry by entry or coefficient by coefficient | V1 to V4 ([below](#ball-vectors)): canonical, containment in every case, a finite result from finite operands under the stated conditions; the negation exact, the scaling by a power of two exact when nothing underflows |
| `limb`, `sign`, `isfinite`, `is_normalized`, a ball's states (`is_finite()`, `is_whole()`, `is_empty()`), an interval's bounds and its `is_finite()` | exact (no kernel): reads or tests of the stored limbs, written by hand in the headers and not machine-checked | |
| `rational<X>(num, den)`, `integer<X>(n)` (no kernel: [Constants from fractions](../reference/rational.md)) | specified exactly, bit for bit; tested for equality with the oracle; **not machine-checked** ([below](#constants-from-fractions)) | integer arithmetic only: the same result in every environment; for `den` = 0, the canonical NaN at run time |

A one-limb operand next to a two-limb one is its limb: `x + y` with `y` an `Expansion<T, 1>` is
`x + a`, through [`add_2_1_full`](../reference/add_2_1_full.md). The claims hold for every
precision from the kernel's minimum on (at most 4), so for `float` and `double` alike. The constants of every row with an error bound,
rounded up to `T`, are in `kairn::traits<kairn::Expansion<T, 2>>` (`add`, `add_limb`, `add_fast`,
`sub`, `sub_limb`, `mul`, `mul_limb`, `ldexp`) and `kairn::traits<T>`: they are the bounds of the
cores, which a result satisfies whenever it is finite.

## Overflow and non-finite values

**Two-limb arithmetic returns IEEE-like results** (decision
[D5](../developer/design/phase0/decisions.md#d5-non-finite-results)): every operator calls a
*full kernel*, the finite core of the operation followed by a fix-up of one operation of `T` on
the leading limbs, two tests and selects
([IEEE-like results](../developer/design/milestone1.md#ieee-like-results)). For canonical
operands, with $w$ the result:

- **F1.** $w$ is canonical.
- **F2.** If $w_0$ is finite, every operand is finite and $w$ satisfies the claim of the core: no
  overflow inside the kernel can produce a finite wrong result.
- **F3.** If every operand is finite and the condition of the table holds, $w_0$ is finite.
- **F4.** If every operand is finite and $w_0$ is not, $w = (\pm\infty, 0)$ with the sign of the
  exact result.
- **F5.** If an operand is not finite, $w$ is the canonical form of the operation of `T` on the
  leading limbs: $+\infty + 1 = +\infty$, $\infty - \infty = \mathrm{NaN}$,
  $0 \cdot \infty = \mathrm{NaN}$; which NaN is not specified.

**`kairn::finite::`** is the opt-out: `add`, `sub`, `mul`, `add_fast` and `ldexp` on the same
operand types as the operators, calling the cores without the fix-up. Their contract is the
cores': either the leading limb of the result is not finite, or the result is normalized and
within its bound; which non-finite pattern comes out (it may be $(+\infty, \mathrm{NaN})$) is not
specified, and such a result is not canonical, so test it with `kairn::isfinite` before passing it
to an operator. For one limb they are the operators themselves.

**`ldexp(x, n)` is defined for every $n$.** When $2^n$ is a number of `T` it is one call of the
kernel ([`mul_pow2_2_full`](../reference/mul_pow2_2_full.md)), with the proved statements of the
table. Otherwise ($n$ above 1023 or below $-1074$ for `double`) the header calls the kernel two or
three times, each time with a power of two of `T`. The result is canonical, and normalized when it
is finite; that much follows from the proved statements of each call. Two more statements hold by
an argument that is written out in the design and tested through the oracle, but is **not
machine-checked**
([Scaling beyond the powers of two of the format](../developer/design/milestone1.md#scaling-beyond-the-powers-of-two-of-the-format)):
scaling up, the result is $2^n x$ exactly or $(\pm\infty, 0)$ on overflow; scaling down,
$\lvert z - 2^n x\rvert \le \eta$, the bound of one call. For one limb, whose kernel is one rounded
product ([`mul_1_1`](../reference/mul_1_1.md)), the header multiplies two or three times by powers
of two of `T`, so that only one of the products rounds; that the result is $\mathrm{RN}(2^n x)$,
what `std::ldexp` returns, holds by the same argument, tested and not machine-checked either. For
a ball, `ldexp(X, n)` calls its kernel ([`ball_mul_pow2_2_full`](../reference/ball_mul_pow2_2_full.md))
in the same steps, and that composition needs no argument of its own: each call returns a ball
that contains $c$ times every member of its operand, so the last contains $2^n$ times every member
of $X$, and each call is exact when nothing it scales underflows, which the steps up and the first
step down keep if the whole scaling does. What is argued and not machine-checked is that the steps
may stop at $n = \pm 2098$ or so for `double`, as for a number: beyond, every ball but the point 0
is the whole line, or a ball of radius at least $2\eta$ around 0.

**A `Ball` is in one of three states**, each a set of real numbers: a *finite ball*, the reals
within its radius of its center (center finite, radius finite and $\ge 0$); the *whole line*,
every real (center 0, radius $+\infty$); the *empty set* (every limb a NaN). `X.is_finite()`,
`X.is_whole()` and `X.is_empty()` say which, and `Ball<T, K>::whole()` and `Ball<T, K>::empty()`
make the last two. A constructor gives the empty set for a negative radius, and the whole line
for a center that is not finite or a radius that is $+\infty$ or a NaN (a NaN says that something
failed upstream, as for a NaN bound given to an interval; until 2026-11-20 it gave the empty
set); in a build with `KAIRN_CHECKS`, a
negative radius is reported, since it is almost surely a mistake. Every Ball operation calls a
*full Ball kernel*, which proves, for canonical operands: **B1** the result is canonical; **B2**
it is empty exactly when an operand is empty; **B3** if it is a finite ball, every operand is a
finite ball, every scalar finite, and the result contains $x \circ y$ for every $x$, $y$ of the
operands. So in every case the result contains every $x \circ y$, the whole line counting as
containing everything ([Ball kernels](../developer/design/milestone1.md#ball-kernels)). A point
operand, a `T` or an `Expansion` of as many limbs, is the ball of radius 0 its constructor makes;
times a ball, a `T` (and for one limb, an `Expansion<T, 1>`) is the scaling, a kernel of its own.

**When a finite ball comes out.** The whole line is always a correct answer, so the statements
above would hold of an operation that returned nothing else. **B4** is the guarantee that this
does not happen far from overflow: if every operand is a finite ball, every scalar finite, and no
member of the exact result is larger in magnitude than a quarter of the overflow threshold (a
sixteenth for the product of two one-limb balls), the result is a finite ball. With centers
$c_x$, $c_y$ and radii $r_x$, $r_y$, and $2^{e_{\max}-2}$ that quarter ($2^{1022}$ for `double`,
$2^{126}$ for `float`):

| Operation (kernels) | The result is a finite ball when |
|---|---|
| `X + Y`, `X - Y` ([`ball_add_1_full`](../reference/ball_add_1_full.md), [`ball_add_2_full`](../reference/ball_add_2_full.md), [`ball_sub_1_full`](../reference/ball_sub_1_full.md), [`ball_sub_2_full`](../reference/ball_sub_2_full.md)) | $\lvert c_x \pm c_y\rvert + r_x + r_y \le 2^{e_{\max}-2}$ |
| `X * a`, `a * X` with a `T` (and, for one limb, an `Expansion<T, 1>`) ([`ball_scale_1_full`](../reference/ball_scale_1_full.md), [`ball_scale_2_full`](../reference/ball_scale_2_full.md)) | $(\lvert c_x\rvert + r_x)\,\lvert a\rvert \le 2^{e_{\max}-2}$ |
| `X * Y`, two-limb centers ([`ball_mul_2_full`](../reference/ball_mul_2_full.md)) | $(\lvert c_x\rvert + r_x)(\lvert c_y\rvert + r_y) \le 2^{e_{\max}-2}$ |
| `X * Y`, one-limb centers ([`ball_mul_1_full`](../reference/ball_mul_1_full.md)) | $(\lvert c_x\rvert + r_x)(\lvert c_y\rvert + r_y) \le 2^{e_{\max}-4}$, a sixteenth of the threshold ($2^{1020}$, $2^{124}$) |

Each left side is the largest magnitude that $x \circ y$ takes over the operands. In particular,
for `double`, a sum of balls whose members are all at most $2^{1021}$ in magnitude is a finite
ball, and so is a product of balls whose members are all at most $2^{510}$. The conditions are
sufficient, not necessary; how far they are from the first whole line seen in small formats is in
[Milestone 1](../developer/design/milestone1.md#when-the-result-is-a-finite-ball). No such
statement is claimed for `-X`, whose kernel only changes the sign of the center.

**What is proved, and in which model.** Every error bound, normalization, exact comparison,
rounding and ball containment is proved in the real model, where nothing overflows; F1 to F5, B1
to B4, and what the comparisons, conversions and constructors return for infinities and NaN are
proved in Flocq's model of IEEE 754, against statements the generator prints from the same kernel
descriptions as the C++ ([Proofs](../proofs/index.md#what-is-proved-and-in-which-model); each
kernel's page in the [reference](../reference/index.md) gives its theorem).

**Not proved yet.** The two statements about `ldexp` when $2^n$ is not a number of `T`, above,
the one about `ldexp` on one limb, and the end of the steps of `ldexp` of a ball; `rational`
([below](#constants-from-fractions)), and with it that the ball of a constant, `Ball<T, k>(q)`
for a result `q` of `rational` or `integer`, contains the fraction: its constructor is a proved
kernel, but the center and the radius it is given are those of `rational`.
And thresholds sharper than those stated. For the two-limb arithmetic, exhaustive runs on small
formats first see an overflow at 0.55 of the overflow threshold or above for the additions and
0.86 or above for the products, where the proved conditions are a quarter and a half of it
([Milestone 1](../developer/design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)).
For the Ball operations, complete searches of small formats first see the whole line at 0.34 of
the threshold for the sums and the differences, 0.375 for the scalings, 0.094 for the product
of one-limb balls and 0.61 for the product of two-limb balls, where the proved conditions are a
quarter, a quarter, a sixteenth and a quarter. The first three of those are in the smallest
format, of two bits of precision; in a format of four bits the same searches give 0.55 to 0.81
([Milestone 1](../developer/design/milestone1.md#when-the-result-is-a-finite-ball)).

**Cost.** Measured on the final code with `double` limbs on an Apple M3 (Apple clang 21, GCC 16),
an AMD Zen 2 (GCC 13, Clang 18) and an Intel i5 (MSVC)
([Benchmarks](../developer/results/bench-milestone1.md#2-the-fix-up-for-non-finite-results)). In
a chain of dependent operations, `x + y`, `x * y`, `x + a` and `x * a` take 0.94 to 1.07 times as
long as the cores (`kairn::finite::`), and the same on two-limb balls 0.89 to 1.06 times as long
as the Ball kernels without the fix-up: in scalar code the generator puts the fix-up behind a
branch, taken only when a result is not finite
([Milestone 1](../developer/design/milestone1.md#ieee-like-results), "Emission"). In loops of
independent operations they take 1.08 to 2.60 times as long as the cores, the most where the
compiler vectorizes the core's loop and not the operator's (Apple clang; GCC 13 at `-O3`). The
packed kernels, which compute the fix-up in every lane, cost 16 to 54% more on `add_2_2` and 70 to
105% more on `mul_2_2` with it. Loops of independent operations are what the packed kernels, and
the batch kernels that D5 plans without the fix-up, are for.

## Intervals

**An `Interval<T, k>` is one of two kinds of set**
([Values of an interval](../developer/design/milestone2.md#values-of-an-interval)): a *nonempty
interval* $[\ell, h]$, the real numbers between two bounds, each a number of `T` or of two limbs,
or $-\infty$ below and $+\infty$ above ($[1, +\infty]$ is a half-line, and does not contain
$+\infty$: the members are real numbers); or the *empty set*, stored as $(+\infty, -\infty)$. There
is no NaN interval. `Interval(lo, hi)` makes, by the first case that applies: **the whole line
when a bound is a NaN**, whatever the other bound is, **or when both bounds are the same
infinity**, $[+\infty, +\infty]$ or $[-\infty, -\infty]$; the empty set when the bounds are
reversed, $lo > hi$ ($[+\infty, -\infty]$ and $+\infty$ with a finite upper bound among them); and
otherwise $[lo, hi]$, the half-lines and $[-\infty, +\infty]$ included. A value from the program
that is not finite says that something failed or overflowed upstream, and nothing about where the
true value is: the whole line is the answer that is always true, and the empty set, which says that
there is no value, never comes out of a NaN or of an infinite point; only reversed bounds give it.
So `Interval(a)` of an infinite `a` is the whole line, as
`Ball(a)` is: its `lower()` is $-\infty$, its `upper()` $+\infty$. `Interval()` is $[0, 0]$.
`Interval<T, k>::from_bounds(lo, hi)` is `Interval(lo, hi)` under the name that
`Ball<T, k>::from_bounds` has too, the one spelling of a set from two bounds for code written for
both types: `X(a, b)` is $[a, b]$ for an interval but the ball of center $a$ and radius $b$.
[The case analysis](../developer/architecture.md#the-constructors-on-every-pair-of-values) gives
every pair of values.

**What is proved of every operation**, in Flocq's model of IEEE 754 with overflow, infinities and
NaN, for canonical operands $X$, $Y$ and the result $Z$ of `X + Y`, `X - Y`, `X * Y` or `-X`
(statements I1 to I5 of
[What is stated of an interval kernel](../developer/design/milestone2.md#what-is-stated-of-an-interval-kernel)):
**I1** $Z$ is canonical; **I2** it is empty exactly when an operand is; **I3** it contains
$x \circ y$ for every real $x \in X$ and $y \in Y$, unbounded operands included; **I4** how far its
bounds are from those of the exact range $\{x \circ y\}$; **I5** when it is bounded. The interval
kernels have no statement of their own in the real model: their statements are the IEEE model's,
since infinite bounds are ordinary values of an interval.

| | One limb | Two limbs |
|---|---|---|
| `X + Y`, `X - Y` | the tightest interval of `T`: the exact bounds rounded outward, $\mathrm{RD}(\ell)$ and $\mathrm{RU}(h)$; for bounded operands, bounded exactly when the exact range is within $\Omega$, and $[\Omega, +\infty]$ when a sum of bounds overflows | each bound within $A\lvert v\rvert + B$ of the exact bound $v$, $A$ about $8u^2$ and $B$ about $2^{-1021}$ for `double` ([`interval_add_2`](../reference/interval_add_2.md) gives them); a bound of the exact range that is zero is returned as zero, so $[0, 0] + [0, 0] = [0, 0]$; bounded when the exact range is within $2^{e_{\max}-2}$ |
| `X * Y` | the tightest interval of `T` when each product of a finite bound of $X$ and one of $Y$ is zero or at least $2^{2p-1}\eta$ in magnitude ($2^{-969}$ for `double`); otherwise each bound that rounding outward or one number of `T` further; bounded exactly when the exact range is within $\Omega$ | each bound within $A\lvert v\rvert + B$ of $v$, $A$ about $10u^2$ ([`interval_mul_2`](../reference/interval_mul_2.md)), no bound claimed exact; $[0, 0] \cdot X = [0, 0]$ for every nonempty $X$, unbounded included; bounded when the exact range is within $2^{e_{\max}-2}$ |
| `-X` | exact | exact |
| `X.hull(Y)`, `X.intersection(Y)` | exact: the smallest interval that contains both, and the common part, the empty set included | the same |

For two limbs the result is an enclosure within a stated bound of the exact range, not the
tightest interval of two limbs: each bound is the round-to-nearest result moved outward by a bound
of its own error, so $[1, 1] + [1, 1]$ is not $[2, 2]$ but an interval of width $2d$ around 2, $d$
being that bound for the sum of two-limb numbers (about $3u^2$ relative to the sum), and only a
zero is kept exact. Bounded operands whose sum or product overflows give the
infinite bound on that side, or the whole line, where one limb gives $[\Omega, +\infty]$.

**Midpoint, radius, split and conversions**
([Midpoint, radius and the conversions](../developer/design/milestone2.md#midpoint-radius-and-the-conversions);
for two limbs, [`interval_mid_rad_2`](../reference/interval_mid_rad_2.md) and the pages after it:
the same special values, a midpoint within $\frac{3u^2}{1-4u}$ relative and $2\eta$, a radius that
covers the interval and is not claimed the smallest; `midpoint()` and `radius()` each run the
whole kernel, and `mid_rad()` gives both from one call). For one limb:
For a bounded $[\ell, h]$, `X.midpoint()` is a number of `T` in $[\ell, h]$ within
$u\,\lvert\tfrac{\ell+h}{2}\rvert + \eta$ of the midpoint, and `X.radius()` the smallest number of
`T` for which the midpoint plus or minus it covers $X$; the whole line gives $0$ and $+\infty$,
$[\ell, +\infty]$ gives $\Omega$ and $+\infty$, $[-\infty, h]$ gives $-\Omega$ and $+\infty$, the
empty set two NaN, as `mid` and `rad` of IEEE 1788. `X.split()` returns two intervals whose union
is $X$, both empty for the empty set; the point at which they meet is a point of $X$, the midpoint
of the listing ($0$ for the whole line), and only that it is a point of $X$ is claimed.
`Ball<T, 1>(X)` contains $X$, with the midpoint and the smallest radius, and is the whole line for
an unbounded $X$ (a ball cannot be a half-line); `Interval<T, 1>(B)` is the smallest interval of `T`
that contains the ball, $[\mathrm{RD}(c - r), \mathrm{RU}(c + r)]$. Both conversions are explicit:
each widens the set. Of a `Ball`, `X.lower_as<T>()` and `X.upper_as<T>()` are bounds of every
member as numbers of `T`, $+\infty$ and $-\infty$ for the empty set: exactly $\mathrm{RD}(c - r)$
and $\mathrm{RU}(c + r)$ for one limb, and for two within $5u(\lvert c\rvert + r) + 3\eta$ of
$c \mp r$, no number of steps of `T` being claimed (the center is rounded to `T` first, which moves
the bound by up to a gap of `T` at $c$); `Ball<T, 2>::from_interval(lo, hi)`, also spelled
`from_bounds(lo, hi)`, the name `Interval<T, k>::from_bounds` has too, contains $[lo, hi]$,
with the exact midpoint for its center when $lo/2$ and $hi/2$ are numbers of `T`, and has the
special states of `Interval(lo, hi)`; `Ball<T, 1>(X)` of a ball of two limbs contains it.

**The interface intervals and balls share**: the predicates, the member and subset tests, the
three-valued comparisons, the relations of IEEE 1788, and the hull, the intersection and the split
of balls, each one kernel ([One enclosure interface](../reference/enclosure.md), which has the
table of what is exact, what is certain and what is not claimed). For an interval every answer is
exact. For a ball of one limb the member and subset tests are exact (the distances are compared as
exact pairs) and the comparisons are exact when the sum of the radii is at most $\Omega$. For a
ball of two limbs only the signs are exact; the member and subset tests and the comparisons are
*certain*: an answer given is right, and near the boundary an answer may not be given (a `bool`
false, a `Trit` unknown), within a band that is measured, not claimed. The comparisons return a
`kairn::Trit`, *yes*, *no* or *unknown*, which converts to no `bool`: a program writes
`kairn::certainly(less(x, y))` or `kairn::possibly(...)`, and intervals and balls have no
comparison operators. On the empty set and the whole line every answer is exact: the comparisons
are *unknown*, the signs false, a member test false, the set operations the values of
[The empty set and the whole line](../developer/design/milestone2.md#the-empty-set-and-the-whole-line).

**Not claimed.** The sign of a zero bound. The tightest interval of a product of one limb in the
underflow range above, or of any operation of two limbs. That a product of two limbs whose exact
range has a bound at zero keeps it: $[0, a] \cdot [b, c]$ gets the lower bound of $ab$ moved
outward. That `split()` splits at the midpoint: only that the two parts meet at a point of the
interval, which can be a bound, so a bisection tests its progress itself
([Zeros of a polynomial by bisection](../tutorials/bisection.md)); for a ball, that its parts are
inside it or smaller than it. That the hull and the intersection of balls are the smallest balls
that contain what they must. An answer of a comparison of balls of two limbs near the boundary.
The constructor of two limbs from a `T` is `make_2`, which gives the number exactly, followed by
the constructor of an interval of two limbs, and the member test of a point of `T` in an interval
or a ball of two limbs is `make_2` followed by the member test of two limbs: compositions of two
proved kernels, argued and not machine-checked as one statement. No operation takes a number as an
operand of an arithmetic operation (`X + a`), since no kernel does: `X + Interval(a)` is what a
program writes.

**Where Kairn departs from IEEE 1788** ([IEEE 1788](../developer/design/milestone2.md#ieee-1788)).
Kairn is modeled on the set-based intervals of IEEE Std 1788.1-2017 and is not a conforming
implementation: it has no decorations, no exceptions, no text input or output, and not the
standard's required functions (division, square root, `wid`, `mag`, ...). It differs on purpose in
four points: a NaN bound given to the constructor gives the whole line, where the standard returns
the empty set and signals; the same infinity given as both bounds, $[+\infty, +\infty]$ or
$[-\infty, -\infty]$, and so `Interval(a)` of an infinite `a`, gives the whole line, where the
standard returns the empty set because no real number is infinite (Kairn reads an infinity from the
program as a value that overflowed or failed, whose true value may be anywhere, and does not make
the empty set of an infinite point, as it does not of a NaN bound; reversed bounds, with an infinite
bound or not, stay the empty set, as in the standard);
the sign of a zero bound is not specified, where the standard returns
$-0$ for a zero lower bound and $+0$ otherwise; and a product of one limb in the underflow range is
*accurate* in the standard's sense, the tightest result widened by at most one number on each side,
where the standard asks for the tightest. Intervals of two limbs and of `float` are not types of the
standard, whose one interval type has bounds of `binary64`. The four relations of IEEE Std
1788.1-2017 are `kairn::ieee1788::equal`, `subset`, `interior` and `disjoint`, exact, with the
standard's readings of the empty set; its predicates `isEmpty` and `isEntire` are `is_empty()` and
`is_whole()` ([One enclosure interface](../reference/enclosure.md#ieee-1788)).

## Products the program passes in

Kairn's kernels are written so that no compiler can fuse a product into one of their additions
(rules R1 and R2 of [Environment](../developer/design/phase0/environment.md#the-rule-no-product-feeds-an-addition)),
and the tests check that under every contraction setting. A product computed by the program
itself and passed in, as in `x + a * b`, needs one more step: a compiler that contracts across
statements (GCC's default for C++, `-ffp-contract=fast`, MSVC's `/fp:contract`) could otherwise
fuse `a * b` into the error-free sums inside the kernel, which would then not be error-free.
Without that step, the result was measured normalized and wrong by about $2^{-24}$ relative to
itself, on GCC 13 and 16 by default, on Apple clang with `-ffp-contract=fast`, and on MSVC with
`/fp:contract`.

So every value of type `T` that the program supplies passes through a *guard*, an addition of
$+0$, before any kernel adds it: rule R3 of the
[kernel IR](../developer/architecture.md#the-kernel-ir), which the generator enforces. A product
plus $+0$ is at most fused into one FMA that rounds the product, and its result is a sum, which
nothing later can fuse; a compiler that honors signed zeros cannot remove the addition. The guard
is in the kernels that receive such a value: `add_2_1` (and through it `sub_2_1`, `sub_1_2` and
their full kernels) on its limb operand, the constructors `make_2`, `make_2_limbs`,
`ball_make_1`, `ball_make_2` and `interval_make_1` and the ball from an interval of two `T`
(`ball_from_interval_1`, `ball_from_interval_2`, which `from_interval` and `from_bounds` call) on what
they are given, and the entry forms of the building blocks
that add their operands (`two_sum_entry`, `fast_two_sum_entry`, `radd_entry` and the four directed
sums), on both: `two_sum(a * b, c)` would otherwise not be error-free. A limb operand that is a
factor of a fused operation is guarded too, because a compiler that sees the other factor to be 1
rewrites `fma(x, 1, s)` as `x + s` and fuses the program's product into it: `x * a`, `a * x`,
`x *= a` and `finite::mul(x, a)` of two limbs and of `Packed`, the scaling `X * a` of a ball of two
limbs, `two_prod`, `mul_down` and `mul_up` call entry forms that guard it (`mul_2_1_full_entry`,
`mul_2_1_entry`, `ball_scale_2_full_entry`, `two_prod_entry`, `mul_down_entry`, `mul_up_entry`). A
limb operand that a kernel only rounds as a product alone, compares or steps needs none
(comparisons, the scaling of a ball of one limb, `ldexp`, `rmul`, `next_up` and `next_down`). Limbs
written directly into `limb[]` are not guarded: a limb written that way must not be a product the
compiler can see being computed; `from_limbs` is the way to build a number from computed values,
and `Interval<T, k>::from_limbs` and `Ball<T, k>::from_limbs` the way to build a set from limbs
read out of one, each limb through the guard of `make_2` (a value of `T`, of which they keep the
leading limb) or `make_2_limbs` (a pair): a composition argued from those claims, not
machine-checked as one statement ([Limbs](../reference/enclosure.md#limbs)); the limbs come back
bit for bit but the sign of a zero and the payload of a NaN.

So the program may pass its own products to Kairn under every contraction setting. The test
`api.boundary.*` checks each guarded form with the product written in the call against the same
operation on the rounded product, bit for bit, under each contraction setting of the compiler, and
`api.boundary.unguarded.*` builds the same test against a copy of the headers with the guard taken
out of the generated kernels, and checks that the compilers above do fuse then. `api.boundary.packed.*`
does the same for the products a program passes into `Packed` and the containers, computed in
registers with the intrinsics of the form or in `T` into arrays, in each form of `Packed`, the
guard of the packed kernels taken out of the copy as well
([Testing](../developer/testing.md#packed-and-the-containers)). A guarded $-0$
enters as $+0$; Kairn leaves the sign of a zero unspecified anyway.

One-limb values themselves are not guarded: they behave like `T`, contraction included, so an
expression such as `p * q + r` on `Expansion<double, 1>` may be evaluated with one rounding where
the compiler contracts, exactly as for `double`.

The flag `-fno-signed-zeros` lets a compiler remove the guard and fold the opaque products of the
kernels back into plain ones. GCC rejects it at compile time (`config.hpp`); Clang defines no
macro for it. With `-ffp-contract=fast` and Apple clang 21 on AArch64 it breaks the two-limb
products, which `kairn::self_test()` reports; with Clang 18, on x86-64 and on AArch64 Linux, the
same flags were measured to break nothing. It is not supported with any compiler.

## Constant evaluation

`constexpr`: the constructors, the ball of a constant among them, the sums and differences of two
limbs (their full kernels, whose fix-up evaluates at compile time), `ldexp` and `half` of two limbs
and `kairn::finite::ldexp` (their kernels compute only opaque products, which constant evaluation
computes as plain products with the same values, and the steps beyond the powers of two of `T` are
integer bookkeeping; a scaling that overflows is not a constant expression with GCC and Clang, as
a sum that overflows is not), negation and absolute value,
the comparisons and conversions, every operation of one limb, a ball's negation, states, sign
predicates and constants, `kairn::finite::add`, `sub` and `add_fast`, `rational` and `integer`
(below), and the building blocks on `T` but `mul_down` and `mul_up`: `next_up`, `next_down`,
`radd` and `rmul` with the same bits as at run time, the others with the same values (`two_prod`
through Dekker's product: the same values when its product is exact, each its own error term
below the threshold). `two_prod` is a constant expression only where Dekker's product computes
the run-time result: on finite operands on which a split or one of its products overflows (the
product of the leading halves can overflow where $ab$ does not) it is not one, a program that
needs one does not compile, and the compiler's message names
`two_prod_overflows_in_constant_evaluation`, or with GCC, which refuses an overflow itself, the
operation. It is one when $\lvert a\rvert, \lvert b\rvert \le 2^{996}$ and
$\lvert ab\rvert \le 2^{1023}$ ($2^{115}$ and $2^{127}$ for `float`), a sufficient condition, not
an exact one (the square of `0x1.ffffffbffffffp+511`, above $2^{1023}$, is one; beyond the
condition a compiler may be stricter than IEEE 754: MSVC refuses in constant evaluation a `float`
product whose exact value exceeds the largest finite number although it rounds to it);
`two_prod(0x1.fffffffffffffp+511, 0x1.fffffffffffffp+511)`, whose run-time error term is
$2^{918}$, is not. A variable of static storage duration that is not `constexpr`, initialized with
such a call, which the compiler first tries as a constant expression, is then initialized at run
time, with the run-time result. A product that overflows is not one either, nor, with GCC or
Clang, an infinite operand; a NaN operand is not with Clang and gives two NaN with GCC, as at run
time. Of intervals: the
constructors and states, the bounds, the negation, the hull, the intersection, the predicates, the
member and subset tests, the three-valued comparisons and the relations of IEEE 1788, the split,
and of one limb the midpoint, the radius and the conversions; and of a ball the functions of the
interface it shares with intervals, of one limb all but the split, of two limbs `lower_as`,
`upper_as`, `midpoint`, `mid_rad`, the signs, `from_interval`, `from_bounds` and the narrowing; of
both types `from_limbs` and `is_finite()`
([One enclosure interface](../reference/enclosure.md#constant-evaluation)).
Not yet: the products of two limbs, whose kernels contain fused operations without a
constant-evaluation variant; `ldexp` and `half` of balls and the Ball and Interval arithmetic, whose
code is where `KAIRN_ENCLOSURE_CODE` puts it, or whose kernels contain such fused operations (the sum and the difference of intervals of
one limb, whose kernels are `constexpr`, among them); and, by design, `mul_down` and `mul_up`, whose
statements are about the fused product, which constant evaluation does not have. Some special
values are not constant expressions, though their functions are `constexpr`: the midpoint, the
radius, the split and the conversion to a ball of the empty set, and the bounds and conversions of
the empty ball and of the whole line, whose listings compute a NaN or $\infty - \infty$ before
selecting their result, which GCC and Clang refuse at compile time.
The canonical infinities and NaN come out of the constructors at compile time
(`Expansion<double, 2>(INFINITY)` is $(+\infty, 0)$), and so do the states of a ball. What a
compiler evaluates at compile time differs at these edges (measured with GCC 13 and 16, Clang 18
and Apple clang 21). GCC refuses an operation that produces an infinity from finite operands, which
Clang computes; both refuse one that produces a NaN from operands that are not. An operation of two
limbs computes such a NaN on the way, before it selects its result, when it overflows or an operand
is infinite: so with either compiler an overflowing sum of two limbs, or one of an infinity, is not
a constant expression (of one limb, an overflowing sum is one with Clang, the infinity, and is not
with GCC). MSVC refuses more, for `float`: a sum or a product whose exact value exceeds the largest
finite number although it rounds to it, which is no overflow (seen with MSVC 19.52, in `two_prod`
and in the check of a canonical pair of a debug build). Each of these is evaluated as stated at run
time. In constant evaluation the guard is not applied
(nothing is fused there), so a $-0$ keeps its sign. One compiler's constant evaluator takes
`a < b` for true when an operand is a NaN: every comparison that can run at compile time, in the
generated kernels and in the headers, is written `b > a` or `b >= a`, and `api.constexpr` checks
the comparisons with NaN operands.

## Constants from fractions

`kairn::rational<X>(num, den)` gives $\mathrm{num}/\mathrm{den}$, for any two `long long`, as a
number of one or two limbs, with the smallest bound of its error that is a number of `T` and
whether it is exact; `kairn::integer<X>(n)` is `rational<X>(n, 1)`. It computes with integers only,
so it gives the same bits in a constant expression and at run time, under every rounding mode and
every accepted flag, and a debug build does not check the environment before it. Its result is
**specified exactly, and tested for equality with the oracle, but not machine-checked**: it is
integer code written by hand in the header, not a generated kernel, so no Rocq theorem is about
it. Every result computed in a constant expression is checked against the whole statement by a
second piece of integer code that divides nothing (`kairn::is_rational_result`), so that a constant
that would be wrong does not compile; a build with `KAIRN_CHECKS` checks the results computed at
run time too ([Constants from fractions](../reference/rational.md); an example is in
[Getting started](index.md#constants-from-fractions)).

## One limb

`Expansion<T, 1>` is meant to cost what `T` costs. Measured by the test `api.k1.zero_cost`, which
compares the instructions emitted for three loops over `double` and over `Expansion<double, 1>`:
identical or fewer with GCC, and with Clang under `-ffp-contract=off` or `=fast`; under Clang's
default contraction a product followed by a sum is fused for `double` and not for
`Expansion<double, 1>` (decision
[D6](../developer/design/phase0/decisions.md#d6-one-limb-and-contraction-under-clang)), unless the
program defines `KAIRN_K1_CONTRACT`. MSVC does not vectorize a loop over the wrapper where it
vectorizes the loop over `double`.

## Packed numbers and arrays

`Packed<T, k>` ([reference](../reference/packed.md)) holds $W$ numbers in registers ($W$ = 4 for
`double` and 8 for `float` with AVX2, 2 and 4 on AArch64, 1 elsewhere). **Each of its operations
has, in each lane, the statement of the operation of `Expansion` of the same name, which is
proved**: it is the packed form of that operation's kernel, which the generator writes from the
same description as the scalar kernel and tests lane by lane against it, bit for bit. The oracle
also judges every packed operation through the public interface, one oracle case per lane, beside
the other lanes, in the quick and the full tier, and a test compares every operation with the
scalar one on every pair of a corpus of special values. Nothing is stated across lanes, and
nothing about a loop as a whole: a program composes the bounds of its operations over the order it
wrote, which depends on $W$, so that the same loop can give different bits on different targets,
each within its own bound ([A vector loop](../tutorials/vector-loop.md)).

The operations are those of two limbs, and of one limb those that do not round (negation, `abs`,
the comparisons, the conversions): `Packed<T, 1>` has no arithmetic, because the kernels of the
arithmetic of one limb are not entry kernels, the only kernels a public header may call
([Packed](../reference/packed.md#the-operations)). One composition is written by hand, as for
`Expansion`: `ldexp` and `half` beyond the powers of two of `T` (argued and tested, not
machine-checked, [above](#overflow-and-non-finite-values)).

`SoA<T, k>` and its views ([reference](../reference/soa.md)) hold numbers as one array per limb and
compute nothing: an element read is the value written (its limbs, but that a zero limb of two may
come back with the other sign, through the guard of `from_limbs`); with `KAIRN_CHECKS` each read of
two limbs is `from_limbs`, checked; a view never allocates, and an `SoA` allocates only in the
functions that say so. Not provided: a packed `Ball` or `Interval`, dispatch at run time, and an
alignment requirement (loads and stores are unaligned; an `SoA` aligns its arrays to 64 bytes).

## Sums, dot products and maps of arrays

The functions of `kairn/batch.hpp` ([reference](../reference/batch.md)) take arrays as views,
`SoAView<T, k>`, and each calls one generated loop: `sum`, `sum_fast` and `dot` (a number), the
maps `add`, `sub`, `scale`, `mul_pow2` and `axpy` (an array, element by element), `conv` (the
coefficients of the product of two polynomials) and `norm_upper` (at least the largest magnitude).
**The statement of each loop is proved, in the real model and in the IEEE model, for every length
of array and every number of lanes**: a sum of $n$ numbers is within
$\gamma_{n-1}(e)\sum_i\lvert x_i\rvert$ of the exact sum, $e = u/(1+u)$ for one limb and
$3u^2/(1-4u)$ for two, in whatever order the loop adds; a dot product within its own bound, of the
same shape relative to $\sum_i\lvert x_i y_i\rvert$, with an underflow term of
$(1+e)^{n-1}\,n\,\tau$, about $\tau$ per term, $\tau = \tfrac12\eta$ for one limb and
$\tfrac32\eta$ for two ([`dot`](../reference/batch.md#what-each-function-states)); every element a
map writes satisfies the claims of the operation on one element; a coefficient of a convolution the
statement of a dot product of its terms;
`norm_upper` is the largest magnitude for one limb and at most one step of `T` above it for two.
The header adds nothing to the arithmetic.

By default a sum and a dot product use the lane order of the build's form of `Packed`, the packed
loop, whose bits depend on the instruction set; with `kairn::sequential` the sequential order,
whose bits are the same everywhere. Both have the same statement. A result that is not finite (an
infinite or NaN element, an overflow) is the canonical NaN with the flag `finite` false; a map's
flag is false exactly when an element it wrote is not finite, and those elements are the canonical
NaN. Arrays that the program fills with products may be passed straight in: the loops guard every
limb they add ([above](#products-the-program-passes-in)). A map may write in place, an array it
reads exactly; no other overlap is supported. Each function checks the environment before its
loop, in every build ([below](#the-environment)), and with `KAIRN_CHECKS` the lengths, the arrays
that alias and its elements.

**The bound as a function of the length.** `kairn::traits<X>::sum(n)` and `dot(n)` give the bound
of a sum and of a dot product of $n$ terms as numbers of `T` (`unit`, and `tiny` for the underflow
term of a dot product), computed by the proved kernels `bound_sum_k` and `bound_dot_k`: at least
$\gamma_{n-1}(e)$ and $\gamma_n(e)$, so that $\lvert s - \sum_i x_i\rvert \le
\mathit{unit}\sum_i\lvert x_i\rvert$ for a sum returned finite, and likewise for a dot product
with `tiny` added ([reference](../reference/batch.md#the-bound-as-a-function-of-the-length)).
They are `constexpr`. Beyond the lengths the kernels bound, about $n e = \tfrac14$, they are
$+\infty$, which claims nothing (a compile error in a constant expression). **Not
machine-checked**: the header gives the kernel the count $n$ as the smallest number of `T` not
below it, in integer code, rounded up where it is not a number of `T` (beyond $2^{24}$ for
`float`), which is safe because what the kernels bound grows with the count; argued in the header
and tested at and beyond those counts in exact arithmetic.

Not provided: a product by a two-limb scalar without an addition (`axpy` with `y` zero), an order
of a number of lanes other than the build's, and constant evaluation of the functions on arrays
(the loops are not `constexpr`).

**The accumulator.** `kairn::Accumulator<T, k>` ([reference](../reference/accumulator.md)) holds a
running sum, the running sum of the magnitudes of what was added, and the count; `add`,
`add_product` and `merge` are proved kernels, and **what is proved is a bound for every history**
of them, a merge being a node of the summation tree: whenever the running sum is finite and the
kernels' masks are true, $\lvert s - \Sigma\rvert \le$ `error_bound()`, $\Sigma$ the exact sum of
what was added, whatever the order. **Not machine-checked**, and tested hard instead: the count,
an integer of the header that saturates at $2^{64} - 1$ (no bound then), its conversion to `T`
(rounded up; exact wherever a radius is given), and what is returned when a mask is false or a
value is not finite: `error_bound()` $+\infty$ and `ball()` the whole line, never a finite ball the
theorem does not give. A radius is given up to about $2^{22}$ terms of `float` and $2^{51}$ of
`double` with one limb, and twice as many with two, since the magnitudes are summed in `T`.

## Ball vectors

`BallVector<T, k, N>` and `BallVectorView<T, k>` ([reference](../reference/ball_vector.md)) hold
$N$ centers and one radius. **Each operation is one generated loop, proved in the real and the IEEE
model in each of its orders** (the sequential one, and the lane order of every number of lanes but
for the product of polynomials, which has the sequential order only), and judged by the
oracle through the public interface: the constructors (`bv_make_k`), the negation, the sum, the
difference, the scaling by a `T`, the scaling by a power of two and the product of polynomials. What
each states, for canonical operands: the result is canonical, a finite ball vector or the whole
space (V1); it contains $f(x, y)$ for every member $x$ of $X$ and $y$ of $Y$, entry by entry, in
every case (V2); if it is finite, so are the operands, and its centers and radius are those of the
loop's kernels (V3); and it is finite under conditions that each operation states, a quarter of the
overflow threshold on its entries and on its radii, and for the product a condition on the length
(V4). The negation is exact, and the scaling by a power of two is exact when nothing underflows.
The constructors make the whole space of a radius that is negative, a NaN or $+\infty$, or of a
center that is not finite: there is no empty ball vector.

Three operations are compositions made in the header, whose statements are those of their calls
composed, argued and tested and not machine-checked as one: `axpy` (the scaling, then the sum in
place), `norm_upper` (the bound of the centers, then the radius added, rounded up), and `ldexp`
beyond the powers of two of `T`, as for a `Ball`. **Not claimed**: that the one radius of a sum, a
difference or a scaling equals the largest of the radii of the entrywise `Ball` operations (it does
in every case the tests compare); that the two orders give the same bits (they do on this tree, a
zero compared as a zero under MSVC). Not provided: an empty state, a radius per entry, the product
in the lane order, operations with a `Ball` or a number but the scaling, constant evaluation of any
operation.

## The environment

Every guarantee assumes rounding to nearest, no flush to zero, and compiler flags that do not
rewrite floating-point expressions ([Environment](../developer/design/phase0/environment.md)).
Including Kairn fails with `#error` under the flags a macro reveals (`-ffast-math`,
`-ffinite-math-only`, and on GCC `-fassociative-math`, `-fno-signed-zeros`, `-freciprocal-math`;
`/fp:fast` on MSVC). For the rest a program calls `kairn::self_test()` once at startup:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:self_test"
```

`kairn::environment_ok()` reads the control register and says whether the rounding mode and
flush-to-zero are in their default state; Kairn never changes them. **The default environment is
the precondition of every function, and the batch entries check it in every build**, with or
without `NDEBUG`: each function on arrays of `kairn/batch.hpp` (`sum`, `sum_fast`, `dot`, the maps,
`conv`, `norm_upper`) and each operation on whole ball vectors of `kairn/ball_vector.hpp` (the
constructors from centers and a radius among them) reads the register once before its loop, as
`environment_ok()` does, and if the environment is not the default one calls
`KAIRN_ENVIRONMENT_FAILURE` with the message of a debug build, which by default prints it and
stops the program. `norm_upper` of an array and the negation of a ball vector, which compute no
sum, leave the rounding mode out (flush to zero still changes their comparisons); every other batch
entry reads it. Measured, the check costs under a nanosecond a call on an Apple M3 and about 6
nanoseconds on an AMD Zen 2, where reading MXCSR is slow; it is within the noise of the loop from
about 64 elements of one limb, or a few of two
([Testing](../developer/testing.md#the-checks-of-a-debug-build)).
The scalar operations, `Packed` and the accumulator, whose operations take one term at a time,
check the environment in a debug build only, as below. In a build without `NDEBUG`
(or with `KAIRN_CHECKS` defined to 1), every operation checks the environment, then its operands:
an operator or a function of `kairn::` requires canonical two-limb operands (finite and
normalized, $(\pm\infty, 0)$ or (NaN, NaN)), a function of `kairn::finite::` normalized ones or a
leading limb that is not finite, a `Ball` operation canonical balls, an `Interval` operation
canonical intervals; `from_limbs` (of a number, an interval and a ball) and the constructors of `Ball` and of `Interval` check what they
are given in the same way (reversed bounds and a NaN bound are not reported: they make the empty
set and the whole line). A failed check stops the
program with a message, the environment's when the environment is wrong. A program that defines
`KAIRN_ENVIRONMENT_FAILURE` to a statement that returns gets that statement instead, and the
operation then goes on without checking its operands, with no guarantee for its result. A function
whose result cannot depend on the rounding mode (negation, `abs`, the comparisons, the
conversions to `T`, the accessors and the negation of a `Ball`, the constructors of a `Ball` from a
`T` or a one-limb number, the constructors, the bounds, the negation, the hull and the intersection
of an `Interval`) does not check the rounding mode, so that a program may call it under a
directed one; [Getting started](index.md#when-a-check-of-a-build-without-ndebug-fails) lists them.
The midpoint, the radius and the split of an interval, the conversions between an interval and a
ball, and the bounds of a ball as numbers of `T` compute sums and halvings under rounding to
nearest, and are checked as every operation that rounds; so are the member and subset tests, the
comparisons, the hull, the intersection and the split of a ball. The predicates, the member and
subset tests, the comparisons and the relations of an interval compare and select, and do not
check the rounding mode.
