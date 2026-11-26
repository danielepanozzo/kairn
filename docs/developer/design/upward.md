# The round-up interval: design

`<kairn/upward.hpp>` is to be an opt-in alternative to `Interval<T, 1>`, used only for speed: one
interval of `float` or `double` kept as two numbers in one SIMD register and computed under the
rounding mode upward, which the program sets through the header's scope objects and for which it
compiles with the options this page names. The default types do not change in any way. This page
is the contract that the generator, the proofs, the oracle, the library and the tests of this
feature are built against, before any of it is written: the values, the kernels and their
listings, the new operations of the IR and their meaning in each model, the statements, how a
listing becomes code in one register, the claims, the public interface, the self-check, the tests,
the documentation, and the order of the work. Notation is that of [Numbers](phase0/numbers.md) and
of the [Milestone 2 statements](milestone2.md#notation-and-vocabulary).

**What is decided, and by whom.** The owner decided what the section
[Decisions](#decisions) lists, with the dates. Everything else on this page is a choice of the
authors, marked *(a choice of the authors)* where it is made and listed again in
[Choices of the authors](#choices-of-the-authors) for the owner's review. Nothing on this page is
implemented, proved or measured in the repository yet: the listings were run in exact arithmetic on
every pair of canonical states of small formats ([Checked](#checked-before-this-page)), which is
evidence that the statements are not wrong, not a proof of them. A measurement step that preceded
this page (hand-written candidates, their checks, a matrix of compilers and options) is in the
authors' private notes; its timings are not quoted here, and the measurements that matter enter the
repository in the last step of the work, rerun on the shipped code.

## In short

- **The value.** An interval $[a, b]$ is the pair $(u, n) = (b, -a)$: lane 0, first in memory, the
  upper bound; lane 1 the lower bound negated. Under the mode upward both lanes round in the
  direction that widens the interval, since $\mathrm{RD}(t) = -\mathrm{RU}(-t)$. The empty set is
  $(\mathrm{NaN}, \mathrm{NaN})$, the whole line $(+\infty, +\infty)$.
- **The operations** answer every special case as the default `Interval<T, 1>` answers it: the empty
  set, unbounded intervals, overflow, $0 \cdot \infty$. A sum is one vector addition, a difference
  one addition and one swap, a negation one swap. A product is four vector multiplications and three
  maxima, with an exact answer in every case, empty set included, and **exactly rounded**: where
  the default product may be one number of `T` wider (products of bounds below $2^{2p-1}\eta$), this
  one is not.
- **The proofs.** Every kernel is a listing of the kernel IR with four new operations, `add_ru`,
  `mul_ru` (IEEE 754's sum and product rounded toward $+\infty$), `unord` (a NaN test) and
  `max_nl` (a maximum in which a NaN first operand loses), and has a statement in the IEEE model in
  the shape of `interval_add_1_spec`, proved in Rocq with Flocq. One statement covers both machine
  forms of the maximum, x86's `MAXPD` and arm64's `FMAXNM`. Nothing existing changes: the upward
  kernels have generated files of their own.
- **What is assumed outside the proofs** is new: that each generated operation runs as the IEEE
  operation rounded upward. The header makes that hold when the program sets the mode through its
  scopes and compiles with the options: barriers on the values on GCC and Clang, a barrier per scope
  on MSVC ([The environment](#the-environment)).
- **The interface.** `kairn::upward::Interval<T>` for `double` and `float`; the scopes
  `kairn::upward::Scope` and `kairn::upward::NearestScope`; `kairn::upward::self_test()`; functions on
  two plain arrays (upper bounds, negated lower bounds), each holding its own scope; a compile error
  where the header sees wrong options, with a documented macro that overrides it; a CMake target
  `kairn::upward` that adds the options. Not included by `<kairn/kairn.hpp>`.

## Decisions

The owner's decisions on this feature, each recorded in the
[decisions log](phase0/decisions.md#decisions-log) when the feature lands:

- **2026-11-24.** An opt-in alternative computed under the rounding mode upward, for speed, with the
  interval stored in one register if that is worth it; the user is responsible for the compilation
  options; a special flag is acceptable if it is marked in the documentation and in the files; a
  function that checks at run time whether there will be a problem. Every special case answered as
  the default interval answers it (the empty set, unbounded intervals, overflow, $0 \cdot \infty$).
  The scalar type and the arrays in the first delivery. A compile error where the header can see
  that the options are wrong, with a documented macro that overrides it. For this fast version only,
  the checks that are not strictly needed are assertions, off in a release build.
- **2026-11-25.** The product with exact special cases only (no form that leaves rare cases
  "unknown"); the sign of a zero bound unspecified; MSVC supported, with a barrier per scope
  ([MSVC](#msvc)).
- **This reverses, for this one opt-in header,** the line of the [brief](brief.md#floating-point-environment-non-negotiable)
  "No fesetround or dynamic rounding modes". The default types do not change.

## Choices of the authors

Each is made where the page says so; listed here for the owner's review.

1. The names: header `<kairn/upward.hpp>`, namespace `kairn::upward`, `Interval<T>`, `Scope`,
   `NearestScope`, `self_test()`, `View<T>`, the macro `KAIRN_UPWARD_OPTIONS_UNCHECKED`, the CMake
   target `kairn::upward`, kernels named `upward_*_1`.
2. The storage $(u, n)$, lane 0 the upper bound; the empty set $(\mathrm{NaN}, \mathrm{NaN})$.
3. The product listing ("Z1"): the first candidate with its NaN lanes made $+0$ as the seed, the
   other three folded in by a maximum in which a NaN candidate loses, then the empty set; the
   pairing of the eight products of [The product](#the-product).
4. One IR operation `max_nl` for the greatest of two, emitted as `MAXPD` on x86 and `FMAXNM` on
   arm64, and one statement over every maximum with the property `max_nl_ok`, with one lemma per
   machine form ([The maximum](#the-maximum)).
5. The listings stay scalar in the IR, with *pair lines* that tell the printers which two operations
   are the two lanes of one instruction ([The pair form](#the-pair-form)).
6. Barriers on the values of every operation on GCC and Clang; on MSVC the barrier per scope of the
   owner's decision; the mode set only through the header's scopes, on every compiler.
7. Internal linkage for every function whose result can depend on the options of the translation
   unit, and the class `Interval<T>` itself of external linkage ([Linkage](#linkage)).
8. A number $t$ that is infinite or a NaN, added to or multiplied by an interval, is handled as the
   default type handles `Interval(t)`, the whole line, by the kernel itself.
9. The scope: written only on change, flush to zero and denormals-are-zero forced off and restored,
   exception flags kept on exit, barriers at both ends; the user-facing scope also sets the C
   library's mode, the array functions write the register only. The check that the build honors the
   mode is made on entry of a scope that writes the mode, in a checked build only (it is not
   strictly needed: [Checks](#checks)).
10. Arrays: two plain arrays, each function holding its own scope; no second layout (an array of
    pairs) in the first delivery ([Arrays](#arrays)).
11. `kairn::upward::pass()`, and barriers on the results of `to_interval()`, for values that cross
    a scope's boundary into code that has no barrier, the default types among it
    ([Code around a scope](#code-around-a-scope)).
12. `-ffp-contract=off` is not required ([Contraction](#contraction)).
13. Generated files of their own for the Rocq models and statements, the C++ and the emulated
    kernels, so that every generated file that exists today stays byte for byte the same.
14. Version 0.4.0 for the first release with the header.

## Values

### States

`kairn::upward::Interval<T>` stores two numbers of `T`, $u$ and $n$, as the two lanes of one
register (on x86-64 the two low lanes of an `__m128d`, or of an `__m128` whose two upper lanes hold
$+0$; on arm64 a `float64x2_t` or a `float32x2_t`; on any other target two numbers). Lane 0 is
$u$, lane 1 is $n$; in memory $u$ comes first.

| State | $(u, n)$ | Members |
|---|---|---|
| the **empty set** | $(\mathrm{NaN}, \mathrm{NaN})$, both quiet | none |
| a **nonempty interval** $[a, b]$ | $(b, -a)$: neither lane a NaN, both in $(-\infty, +\infty]$, and $-n \le u$ | the real numbers $x$ with $a \le x \le b$ |
| among them the **whole line** | $(+\infty, +\infty)$ | every real number |
| $[a, +\infty]$, $a$ finite | $(+\infty, -a)$ | $x \ge a$ |
| $[-\infty, b]$, $b$ finite | $(b, +\infty)$ | $x \le b$ |

A state is **canonical** when it is one of these. As for the default interval, the members are real
numbers: $[1, +\infty]$ does not contain $+\infty$. No lane of a canonical state is $-\infty$, and a
NaN lane is never alone. Any other state (one NaN lane, a lane $-\infty$, crossed lanes $-n > u$, a
signaling NaN) is not canonical: no operation returns one, and one given through `from_limbs` or an
array is a broken precondition, which a checked build reports ([Checks](#checks)). A NaN lane of a
canonical state is quiet because every NaN the operations produce is: an IEEE operation that
delivers a NaN delivers a quiet one ([IEEE 754](phase0/references.md#ieee-754)), and the constant NaN
of the listings is `std::numeric_limits<T>::quiet_NaN()`. The machine form of the maximum on arm64
relies on it ([The maximum](#the-maximum)).

Why $(\mathrm{NaN}, \mathrm{NaN})$ and not the default's encoding: the default empty set
$[+\infty, -\infty]$ converted by negating the lower bound would be $(-\infty, -\infty)$, and a sum
with an operand whose lower bound is $-\infty$ would compute $-\infty + \infty$; a NaN in both lanes
makes the sum and the difference empty exactly when an operand is, with no test, since a NaN
propagates through an addition.

Why lane 0 is the upper bound: it is the order in which the first client and its device code store
the two numbers, so that a program can pass such pairs in without converting them.

### Conversions

From the default `Interval<T, 1>` $[\ell, h]$: $(h, -\ell)$, and the empty set $(+\infty, -\infty)$
becomes $(\mathrm{NaN}, \mathrm{NaN})$. To it: $[-n, u]$, and $(\mathrm{NaN}, \mathrm{NaN})$ becomes
$(+\infty, -\infty)$. Both are exact (a negation and selections), both preserve the set, and a
round trip gives the same set back; only the sign of a zero bound can differ. Neither conversion is
implicit.

### Differences from the default interval

1. **The sign of a zero bound** is unspecified (the owner's decision of 2026-11-25). It can differ
   from the default type's and between x86 and arm64, whose maxima order $-0$ and $+0$ differently;
   the values are the same.
2. **Products are exactly rounded** in every case: each bound is the rounding of the bound of the
   exact range. The default product may be one number of `T` wider when a product of bounds is
   nonzero and below $P = 2^{2p-1}\eta$ ([One limb](milestone2.md#one-limb)). The upward product is
   never wider than the default one.
3. **Operations with a number of `T`** exist: $x + t$, $x - t$, $t - x$, $x \cdot t$, $t \cdot x$
   (the default type has none and writes `Interval(t)`). Their values are those of the default
   $x \circ$ `Interval(t)`: for a $t$ that is infinite or a NaN, the operand is the whole line
   *(a choice of the authors)*.
4. **Nothing is `constexpr`** ([The interface](#the-interface)).
5. **No midpoint, radius, `mid_rad`, `split`**, no conversion to or from a `Ball`, no bounds of two
   limbs: each needs rounding to nearest; a program converts to the default type outside the scope.
6. **The operations that round run only inside an upward scope.** The exact ones (negation, hull,
   intersection, predicates, comparisons, conversions) give the same result in every mode.
7. **Storage and accessors.** `from_limbs` and `to_limbs` read and write $(u, n)$, where the
   default type's read $(\ell, h)$; `lower()` and `upper()` return the default type's convention,
   $+\infty$ and $-\infty$ for the empty set.

## The operations of the IR

Four operations are added to the [kernel IR](../architecture.md#the-kernel-ir). Only kernels marked
`rounding: upward` may use them, and those kernels use none of the operations that round to
nearest (rule U1, [The rules](#the-rules)).

| IR | Meaning | Interpreter | IEEE model | Real model |
|---|---|---|---|---|
| `add_ru a b` | IEEE 754's sum rounded toward $+\infty$ | exact integer arithmetic, rounding up in the format with overflow | `Bplus prec emax _ _ nan_plus mode_UP a b` | `round radix2 (FLT_exp emin prec) Zceil (a + b)` |
| `mul_ru a b` | IEEE 754's product rounded toward $+\infty$ | the same | `Bmult prec emax _ _ nan_mult mode_UP a b` | `round radix2 (FLT_exp emin prec) Zceil (a * b)` |
| `unord a b` | a mask: $a$ or $b$ is a NaN | the same | `orb (is_nan a) (is_nan b)` | none |
| `max_nl a b` | the greater of $a$ and $b$, $b$ when $a$ is a NaN ([below](#the-maximum)) | each machine form, chosen on the command line (`--max sel`, `--max nm`) | a section variable `max_nl` with the hypothesis `max_nl_ok` | none |

What "rounded toward $+\infty$ in the format with overflow" fixes, exactly, on every pair of values of
the format (signed zeros, subnormal numbers, the two infinities, NaN), as IEEE 754 defines it and
Flocq's `Bplus` and `Bmult` with `mode_UP` compute it:

- a finite result above $\Omega$ is $+\infty$; one below $-\Omega$ is $-\Omega$, never $-\infty$;
- $\infty - \infty$ and $0 \cdot \infty$ are a NaN, and so is any operation with a NaN operand;
- an exact zero sum of operands of opposite signs is $+0$ (it is $-0$ only under rounding toward
  $-\infty$); $x + x$ of a zero $x$ keeps its sign; a zero product has the sign of the product of
  the signs;
- a positive result below $\eta$ is $\eta$; a negative result above $-\eta$ is $-0$.

The existing operations keep their meaning in an upward kernel and need no rounding: `neg`, `abs`
(exact), `lt`, `le`, `eq` (IEEE comparisons, false with a NaN), `and`, `or`, `not`, `select`, `copy`,
`0`, `const inf`, `const nan`. A kernel of the upward family has no real-model statement (rule U1:
it is `ieee_only`), so the real-model column is the meaning for the record, for a kernel that may one
day need it (CUDA's `__dadd_ru` and `__dmul_ru`, and AVX-512's embedded rounding, compute these
operations with no mode at all); no file of the real model changes.

### The maximum

`max_nl a b` is specified by a property, not by one function, because the two machine instructions
that compute it in one instruction differ in the sign of a zero:

- x86 `MAXPD a, b` (`_mm_max_pd(a, b)`): $a$ when $a > b$, otherwise $b$: when either is a NaN, and
  when both are zeros, it returns its second operand
  ([Intel SDM](#references), volume 2, `MAXPD`);
- arm64 `FMAXNM` (`vmaxnmq_f64(a, b)`): when exactly one operand is a quiet NaN, the other; on two
  zeros of different signs, $+0$; otherwise the greater
  ([Arm ARM](#references), `FMAXNM` and its pseudocode `FPMaxNum`).

The property, `max_nl_ok` (in `proofs/theories/IeeeUpwardOperations.v`): for all $a$ and every $b$
that is **not a NaN**, the result is $b$ when $a$ is a NaN; otherwise it is $a$ or $b$, and it is at
least both as an extended real number. Nothing is said when $b$ is a NaN.

```coq
Definition max_nl_ok (m : float -> float -> float) : Prop :=
  forall a b : float, ~ nan b ->
  (nan a -> m a b = b) /\
  (~ nan a -> (m a b = a \/ m a b = b) /\
               xle (xval a) (xval (m a b)) = true /\ xle (xval b) (xval (m a b)) = true).
```

Two lemmas, in `proofs/theories/IeeeUpwardMax.v`, prove it of the models of the two instructions:
`max_sel_ok : max_nl_ok max_sel`, with `max_sel a b := if lt b a then a else b` (`MAXPD`, and the
C++ `a > b ? a : b` of the two-number form), and `max_num_ok : max_nl_ok max_num`, with `max_num` the
pseudocode `FPMaxNum` on operands whose NaNs are quiet. Every statement of a kernel that computes
`max_nl` quantifies over every `max_nl` with the property. So the one proved listing covers both
machine forms, and a third (a future backend) needs one lemma more, not a second set of kernels and
proofs *(a choice of the authors)*. The alternative, two kernels per operation that differ in one
instruction, would double the descriptions, claims, statements, proofs and tests for a difference
that no claim states.

What remains outside the proofs: that the instructions compute what `max_sel` and `max_num` say
(tested on the hardware against the interpreter on every special value, as for every operation),
and, for `FMAXNM`, that no operand is a signaling NaN, on which `FPMaxNum` returns a NaN rather than
the other operand. Every operand of a `max_nl` is a result of `mul_ru` or a lane of a canonical state
(rule U5), whose NaNs are quiet.

The order of the operands is part of the listing and not a detail: a maximum that returns the NaN
(`MAXPD` with the operands exchanged, or arm64's `FMAX`) gives intervals that miss the exact range.
The object-code check refuses an `FMAX` where `FMAXNM` is asked ([Object code](#object-code)).

## The kernels

Twenty-four kernels, named after the default type's (`interval_add_1` becomes `upward_add_1`), each a
listing of the IR, an entry kernel (the header calls it), of the extended domain, IEEE model only.
Inputs and outputs that are states are pairs, `x = xu xn`; a number of the program is one limb, `t`.

| Kernel | Inputs | Outputs | Claim | Default it mirrors |
|---|---|---|---|---|
| `upward_add_1`, `upward_sub_1` | `x`, `y` | `z` | `encloses_interval` `x+y`, `x-y`, tight `rounded`, bounded exactly when the range is within $\Omega$ | `interval_add_1`, `interval_sub_1` |
| `upward_neg_1` | `x` | `z` | `encloses_interval` `-x`, tight `exact` | `interval_neg_1` |
| `upward_mul_1` | `x`, `y` | `z` | `encloses_interval` `x*y`, tight `rounded` (no steps, no condition), bounded exactly | `interval_mul_1` |
| `upward_add_num_1` | `x`, `t` | `z` | `encloses_interval` `x+t`, `t` a number | none |
| `upward_mul_num_1` | `x`, `t` | `z` | `encloses_interval` `x*t`, `t` a number | none |
| `upward_hull_1`, `upward_intersection_1` | `x`, `y` | `z` | `interval_set` `union`, `intersection` | `interval_hull_1`, `interval_intersection_1` |
| `upward_make_1` | `lo`, `hi` | `z` | `makes_interval` | `interval_make_1` |
| `upward_from_interval_1` | `xl`, `xu` (a default interval) | `z` | `same_set` | none |
| `upward_to_interval_1` | `x` | `zl`, `zu` (a default interval) | `same_set` | none |
| `upward_empty_1`, `upward_entire_1`, `upward_contains_1`, `upward_subset_1`, `upward_positive_1`, `upward_negative_1`, `upward_zero_1` | `x` (and `t` or `y`) | a mask | `certain`, exact | `interval_*_1` of the same name |
| `upward_less_1`, `upward_less_equal_1`, `upward_equal_1` | `x`, `y` | `yes`, `no` | `trit`, exact | `interval_*_1` of the same name |
| `upward_rel_equal_1`, `upward_rel_interior_1`, `upward_rel_disjoint_1` | `x`, `y` | a mask | `certain`, exact | `interval_rel_*_1` |

**Requirements.** Every input that is a state is required canonical, `upward(xu, xn)`
([Claims and the oracle](#claims-and-the-oracle)); the default interval given to
`upward_from_interval_1` is required canonical as the default kernels require it, `interval(xl, xu)`;
the number `t` and the bounds given to `upward_make_1` are any values of `T`, infinities and NaN
included, with no requirement.

The five arithmetic kernels round; the other nineteen are exact (comparisons, selections, sign
changes, NaN tests) and give the same result in every rounding mode. The header writes $x - t$ as
`upward_add_num_1(x, -t)`, $t + x$ and $t \cdot x$ as the kernels with the operands exchanged, and
$t - x$ as `upward_neg_1` of `upward_add_num_1(x, -t)`: compositions of proved kernels through an
exact negation, argued and not machine-checked as one statement, as the default library records its
compositions. `contains(y)` of the interface is `upward_subset_1(y, x)`.

The listings below are written as the descriptions will hold them: one operation per statement, and a
**pair line**, two statements separated by ` | `, lane 0 on the left, where the two are the two lanes
of one instruction ([The pair form](#the-pair-form)). The comment at the end of a pair line names the
register operands.

### Sum, difference, negation

```
upward_add_1(x = xu xn, y = yu yn) -> z = zu zn
  zu = add_ru(xu, yu)  | zn = add_ru(xn, yn)          x + y

upward_sub_1(x = xu xn, y = yu yn) -> z = zu zn
  zu = add_ru(xu, yn)  | zn = add_ru(xn, yu)          x + swap(y)

upward_neg_1(x = xu xn) -> z = zu zn
  zu = copy(xn)        | zn = copy(xu)                swap(x)
```

For nonempty operands each lane is in $(-\infty, +\infty]$, so no lane sum is $-\infty + \infty$:
an overflow upward gives $+\infty$, a valid bound, and one downward gives $-\Omega$, never $-\infty$.
$z_u = \mathrm{RU}(b + d)$ and $z_n = \mathrm{RU}(-a - c) = -\mathrm{RD}(a + c)$: the tightest
interval of `T`, as `interval_add_1`. An empty operand has a NaN in both lanes, and so has the
result. No test, no selection.

### The product

The four products of bounds are $ac$, $ad$, $bc$, $bd$; the upper bound is the greatest of them and
the lower bound the least, with $0 \cdot \infty = 0$
([One limb](milestone2.md#one-limb)). Lane 0 takes candidates of the upper bound, lane 1 candidates of
the negated lower bound, $-\min = \max(-\cdot)$, eight products in four multiplications of two lanes:

```
upward_mul_1(x = xu xn, y = yu yn) -> z = zu zn
  nyu = neg(yu)               | nyn = neg(yn)                neg(y)
  q1u = mul_ru(xu, yu)        | q1n = mul_ru(xn, yu)         x       * bcast0(y)     (bd, -ad)
  q2u = mul_ru(xn, yn)        | q2n = mul_ru(xu, yn)         swap(x) * bcast1(y)     (ac, -bc)
  q3u = mul_ru(xn, nyu)       | q3n = mul_ru(xu, nyu)        swap(x) * bcast0(-y)    (ad, -bd)
  q4u = mul_ru(xu, nyn)       | q4n = mul_ru(xn, nyn)        x       * bcast1(-y)    (bc, -ac)
  e1u = unord(q1u, q1u)       | e1n = unord(q1n, q1n)
  m1u = select(e1u, 0, q1u)   | m1n = select(e1n, 0, q1n)    the seed: Q1, a NaN lane +0
  m2u = max_nl(q2u, m1u)      | m2n = max_nl(q2n, m1n)       a NaN candidate loses
  m3u = max_nl(q3u, m2u)      | m3n = max_nl(q3n, m2n)
  m4u = max_nl(q4u, m3u)      | m4n = max_nl(q4n, m3n)
  eu  = unord(xu, yu)         | en  = unord(xn, yn)          an operand is empty
  zu  = select(eu, const nan, m4u) | zn = select(en, const nan, m4n)
```

with $x = (b, -a)$ and $y = (d, -c)$: each product is rounded up, so lane 0 holds
$\mathrm{RU}$ of each candidate of the upper bound and lane 1 $\mathrm{RU}(-p) = -\mathrm{RD}(p)$ of
each candidate of the lower bound, and the greatest of roundings is the rounding of the greatest
(rounding is monotone). The negations are of the operands, never of a product (rule U3): under the
mode upward $-\mathrm{RU}(p)$ is $\mathrm{RD}(-p)$, a bound on the other side.

The special cases, which the owner asked to be answered as by the default type:

- For nonempty canonical operands a candidate is a NaN exactly when it is $0 \cdot \infty$. The seed
  $Q_1$ has its NaN lanes replaced by $+0$, so the running maximum $m$ is never a NaN, and the second
  operand of every `max_nl` is not one: a NaN candidate of $Q_2$, $Q_3$, $Q_4$ loses. That dropping
  such a candidate gives the same maximum as counting it as $0$ is a case analysis of the proof:
  whenever a candidate other than the seed is $0 \cdot \infty$, some candidate of the same lane, the
  zeroed seed included, is at least $0$ (a zero bound $a$ or $b$ puts $0$ in $X$, and with it a
  product of value $0$ or an infinite product of the right sign among the others, or a zero seed).
  For $[0, 0]$ times the whole line every candidate is a NaN and the result is the seed's $(+0, +0)$,
  $[0, 0]$.
- An empty operand has two NaN lanes, every candidate is then a NaN, and the last line makes the
  result $(\mathrm{NaN}, \mathrm{NaN})$; a nonempty operand has none.
- An infinite product is exact under every rounding; an overflowing finite product is $+\infty$ or
  $-\Omega$, as for the sum.

The pairing of the eight products is the one the measurement step found cheapest: one sign change of
$y$, one swap of $x$, and four broadcasts of a lane of $y$ or $-y$, which on arm64 are no
instructions at all (a product by an element, `vmulq_laneq_f64`). Its seed $Q_1$ and the set of
candidates of each lane are those of the listing that the measurement step checked on every pair of
states of five small formats; the folding order of the other three differs, which can change the
sign of a zero only, and the gate of the generator reruns that check on this listing.

### Operations with a number

```
upward_add_num_1(x = xu xn, t) -> z = zu zn
  nt = neg(t)
  su = add_ru(xu, t)          | sn = add_ru(xn, nt)          x + (t, -t)          make
  wu = add_ru(xu, const inf)  | wn = add_ru(xn, const inf)   x + (inf, inf): the whole line, or empty
  ta = abs(t)
  ft = lt(ta, const inf)                                     t is finite
  zu = select(ft, su, wu)     | zn = select(ft, sn, wn)      ft broadcast

upward_mul_num_1(x = xu xn, t) -> z = zu zn
  nt  = neg(t)
  p1u = mul_ru(xu, t)         | p1n = mul_ru(xn, t)          x       * (t, t)     (bt, -at)
  p2u = mul_ru(xn, nt)        | p2n = mul_ru(xu, nt)         swap(x) * (-t, -t)   (at, -bt)
  e1u = unord(p1u, p1u)       | e1n = unord(p1n, p1n)
  m1u = select(e1u, 0, p1u)   | m1n = select(e1n, 0, p1n)    the seed: P1, a NaN lane +0
  mu  = max_nl(p2u, m1u)      | mn  = max_nl(p2n, m1n)
  eu  = unord(xu, xu)         | en  = unord(xn, xn)          x is empty
  fu  = select(eu, const nan, mu) | fn = select(en, const nan, mn)
  axu = abs(xu)               | axn = abs(xn)
  su  = add_ru(axu, axn)      | sn  = add_ru(axn, axu)       |x_u| + |x_n| in both lanes
  gu  = lt(0, su)             | gn  = lt(0, sn)
  wu  = select(gu, const inf, su) | wn = select(gn, const inf, sn)   x * whole line
  ta  = abs(t)
  ft  = lt(ta, const inf)                                    t is finite
  zu  = select(ft, fu, wu)    | zn  = select(ft, fn, wn)
```

For a finite $t$ these are the sum with $[t, t]$ and the product by $[t, t]$ with two candidates per
lane, by the same argument as the product. For a $t$ that is infinite or a NaN the operand is the
whole line, as `Interval(t)` makes it: $x$ + whole line is the whole line, or the empty set for an
empty $x$, which `add_ru` with $+\infty$ gives lane by lane; $x \cdot$ whole line is $[0, 0]$ for
$x = [0, 0]$, the empty set for an empty $x$, and the whole line otherwise, which the sum of the
absolute values of the lanes tells ($0$, a NaN, or positive). Without the last selection a $t$ that
is infinite or a NaN gives a state that does not contain the true range: a silent wrong interval,
which an assertion would not have caught in a release build *(a choice of the authors)*.

### Hull and intersection

```
upward_hull_1(x = xu xn, y = yu yn) -> z = zu zn
  eu = unord(xu, xu)          | en = unord(xn, xn)           x is empty
  tu = max_nl(yu, xu)         | tn = max_nl(yn, xn)          y empty: x
  zu = select(eu, yu, tu)     | zn = select(en, yn, tn)

upward_intersection_1(x = xu xn, y = yu yn) -> z = zu zn
  mu = lt(yu, xu)             | mn = lt(yn, xn)
  lu = select(mu, yu, xu)     | ln = select(mn, yn, xn)      the smaller lanes
  nu = neg(lu)                | nn = neg(ln)
  cu = lt(lu, nn)             | cn = lt(ln, nu)              u < -n: crossed (one mask, both lanes)
  eu = unord(xu, yu)          | en = unord(xn, yn)           an operand is empty
  bu = or(eu, cu)             | bn = or(en, cn)
  zu = select(bu, const nan, lu) | zn = select(bn, const nan, ln)
```

The hull is the larger lane of each, the empty set its identity; its `max_nl` may see a NaN second
operand (an empty $x$), and that result is then discarded by the selection. The intersection is the
smaller lane of each: $\min(b, d)$ and $\min(-a, -c) = -\max(a, c)$; it is empty when an operand is,
or when the lanes cross. Both are exact: no operation of either rounds. The crossing is tested on the
negated lane, exactly, rather than on a rounded sum of the lanes.

### Constructor and conversions

```
upward_make_1(lo, hi) -> z = zu zn                           two values of T from the program
  ok = le(lo, hi)                                            false with a NaN
  nl = lt(lo, const inf)
  mi = neg(const inf)
  nu = lt(mi, hi)
  va = and(ok, nl)
  v  = and(va, nu)                                           the pair describes an interval
  rv = lt(hi, lo)                                            reversed; false with a NaN
  nlo = neg(lo)
  ou = select(rv, const nan, const inf) | on = select(rv, const nan, const inf)   rv broadcast
  zu = select(v, hi, ou)      | zn = select(v, nlo, on)      (hi, -lo) made of two scalars

upward_from_interval_1(xl, xu) -> z = zu zn                  a canonical default interval
  e  = eq(xl, const inf)                                     its empty set
  nl = neg(xl)
  zu = select(e, const nan, xu) | zn = select(e, const nan, nl)

upward_to_interval_1(x = xu xn) -> (zl, zu)
  e  = unord(xu, xu)
  nl = neg(xn)
  mi = neg(const inf)
  zl = select(e, const inf, nl)
  zu = select(e, mi, xu)
```

`upward_make_1` has the cases of `interval_make_1` ([Values of an
interval](milestone2.md#values-of-an-interval)): the whole line for a NaN bound and for the same
infinity twice, the empty set for reversed bounds, $[lo, hi]$ otherwise. It has no guard: the barrier
on its inputs takes the place of rule R3 ([The rules](#the-rules)). `Interval(t)` of the interface is
`upward_make_1(t, t)`.

### Predicates and comparisons

Each is the default kernel's listing on $\ell = -n$, $h = u$, with the comparisons written on the
lanes as they are stored (a negation is exact, so $\ell < h'$ is `lt(neg(xn), yu)`) and the empty set
told by a NaN instead of a bound $+\infty$. A comparison with a NaN is false, which gives the default
answers for an empty operand with no test, but where the default answer for the empty set is true.

```
upward_empty_1(x)       m = unord(xu, xu)
upward_entire_1(x)      a = eq(xu, const inf);  b = eq(xn, const inf);  m = and(a, b)
upward_contains_1(x, t) a = le(t, xu);  nt = neg(t);  b = le(nt, xn);  ta = abs(t);
                        ft = lt(ta, const inf);  ab = and(a, b);  m = and(ab, ft)
upward_subset_1(x, y)   ex = unord(xu, xu);  a = le(xn, yn);  b = le(xu, yu);  c = and(a, b);  m = or(ex, c)
upward_positive_1(x)    m = lt(xn, 0)                     0 < lower; xn is never -inf
upward_negative_1(x)    m = lt(xu, 0)
upward_zero_1(x)        a = eq(xn, 0);  b = eq(xu, 0);  m = and(a, b)
upward_less_1(x, y)     ny = neg(yn);  nx = neg(xn);  yes = lt(xu, ny);  no = le(yu, nx)
upward_less_equal_1     the same with yes = le(xu, ny), no = lt(yu, nx)
upward_equal_1(x, y)    nx = neg(xn);  ny = neg(yn);  ea = eq(nx, xu);  eb = eq(xu, ny);  ec = eq(ny, yu);
                        eab = and(ea, eb);  yes = and(eab, ec);
                        da = lt(xu, ny);  db = lt(yu, nx);  no = or(da, db)
upward_rel_equal_1      a = eq(xu, yu);  b = eq(xn, yn);  c = and(a, b);
                        ex = unord(xu, xu);  ey = unord(yu, yu);  ee = and(ex, ey);  m = or(c, ee)
upward_rel_interior_1   ex = unord(xu, xu);  la = lt(xn, yn);  lb = eq(yn, const inf);  lc = eq(xn, const inf);
                        ld = and(lb, lc);  lo = or(la, ld);  ua = lt(xu, yu);  ub = eq(xu, const inf);
                        uc = eq(yu, const inf);  ud = and(ub, uc);  hi = or(ua, ud);  lu = and(lo, hi);  m = or(ex, lu)
upward_rel_disjoint_1   ee = unord(xu, yu);  nx = neg(xn);  ny = neg(yn);  da = lt(xu, ny);  db = lt(yu, nx);
                        dd = or(da, db);  m = or(ee, dd)
```

These are scalar statements: the printers read each lane of the register as a number of `T` and
compare numbers ([The pair form](#the-pair-form)), which is also what keeps them off the vector
comparisons that Clang on arm64 turns into scalar code under strict floating point.

### Checked before this page

Every listing of this page was run, written out lane by lane in the exact model of binary formats
under rounding upward that the measurement step built (IEEE 754's rules from exact rationals,
independent of the machine), on **every pair of canonical states** of the formats
$(p, q_{\min}, q_{\max})$ = (1, 0, 1), (1, -1, 1), (2, -2, 1), (3, -4, 1) and (3, -5, 2) (up to 7.7
million pairs), and for the kernels with a number on every state and every value: with both machine
forms of the maximum, each arithmetic result is the tightest interval of the format around the exact
range ($0 \cdot \infty = 0$), the empty set exactly when an operand is empty; the hull, the
intersection, the conversions and every predicate equal the default kernels on the meanings, and the
constructor follows the table of `makes_interval` on every pair of values. No case failed. The model
was compared with the hardware by the measurement step, with no difference. This is the evidence
behind the statements below, not their proof; the gate of the generator repeats it on the
descriptions as written, through the interpreter and the oracle, on formats up to precision 4.

## The rules

The generator refuses an upward kernel that breaks one of these, as it refuses the others
([The rules](https://github.com/danielepanozzo/kairn/blob/main/gen/README.md#the-rules) of the
generator):

- **U1. The family.** A kernel with `rounding: upward` uses only `add_ru`, `mul_ru`, `max_nl`,
  `unord`, `neg`, `abs`, `copy`, `lt`, `le`, `eq`, `and`, `or`, `not`, `select`, `0`, `const inf`,
  `const nan` and calls of other upward kernels; no operation that rounds to nearest, no `guard`, no
  `succ` or `pred`, no other constant. It is `ieee_only`, `domain: extended`. No kernel outside the
  family uses the four new operations. Its C++ goes into `include/kairn/gen/upward.hpp` and its
  models into the files of [Statements](#statements) only.
- **U2. Pair lines** ([below](#the-pair-form)): P1 to P5.
- **U3. No negated rounded result.** No value is the negation of a result of `add_ru` or `mul_ru`,
  directly or through `select`, `copy` or `max_nl`, nor of a lane of such a pair line. Under the mode
  upward $-\mathrm{RU}(t)$ is $\mathrm{RD}(-t)$, a bound on the other side; the listings negate
  operands instead, and compilers rewrite a negation next to a product in ways that are valid only
  under rounding to nearest (the measurement step saw it on arm64 without the options; arm64's
  `FNMUL` negates after rounding).
- **U4. Barriers instead of guards.** Rule R3 ([the kernel IR](../architecture.md#the-kernel-ir)) does
  not apply: an upward kernel has no `guard`, and the printer emits a barrier on every input instead,
  through which nothing the program computed can be fused into the kernel ([Barriers](#barriers)).
- **U5. The operands of `max_nl`.** The first operand of every `max_nl` is a result of `mul_ru` or a
  lane of an input; so every NaN that reaches a `max_nl` is quiet, which the arm64 form needs.
- **U6. Every rounded operation depends on the first input.** Each `add_ru` and `mul_ru` has the
  kernel's first pair input in its data flow. On MSVC the barrier of a scope reaches the operations
  through that input alone ([MSVC](#msvc)).
- **U7. Outputs.** A pair output is the result of one pair line; a mask or a number output is the
  result of a scalar statement.

## The pair form

**The IR stays scalar** *(a choice of the authors)*. A listing is the scalar SSA of the existing IR;
a pair line is two of its statements written on one line, and the Rocq printer, the interpreter, the
claims and the counts read it as those two statements, lane 0 first. Only the printers of the
register form read the pairing. The reasons: the proofs and the statements are about scalar listings,
as for every interval kernel today, with nothing new in the model but the four operations; the same
listing gives the array form, where a pair is two registers of $W$ lanes and the pairing is ignored;
and the generator checks the pairing mechanically, so that the code in one register computes in
lane 0 exactly the lane-0 statements and in lane 1 the lane-1 statements. A pair type in the IR would
put lanes, swaps and broadcasts into the formal model, where they mean nothing.

The description declares pair inputs and outputs, `input: pair stored x = xu xn` and
`output: pair z = zu zn`; a number of the program is `input: t`. The rules of a pair line:

- **P1.** Both statements apply the same operation (a `copy` of each lane is a move of lanes), with
  two exceptions, one instruction each: `neg | copy` and `copy | neg` (a sign change of one lane, an
  exclusive or with a constant), and two different constants (a constant register).
- **P2.** Each operand position names a pair $(a | b)$ that one register holds, in one of these
  forms: a pair defined by a pair line or an input, in its order; the same swapped; a broadcast of
  one of its lanes; a broadcast of a scalar (a number input, a scalar result, or a mask of a scalar
  comparison); or two scalars (a *make*, one instruction more; used by the constructors).
- **P3.** A pair input is the two lanes of one register, and a pair output the result of one pair
  line (U7).
- **P4.** A scalar statement reads lanes of pairs (lane 0 costs nothing, lane 1 one move) and scalars;
  a scalar enters a pair line only through P2's broadcast or make.
- **P5.** A pair line of comparisons or of `unord` gives a mask register, every bit of a lane set or
  clear; `and`, `or`, `not` and `select` act lane by lane on such masks.

### The printers

| IR | x86-64: `__m128d` (`__m128`, lanes 0 and 1) | arm64: `float64x2_t` (`float32x2_t`) | two numbers | arrays, AVX2 / NEON |
|---|---|---|---|---|
| `add_ru`, `mul_ru` | `_mm_add_pd`, `_mm_mul_pd` | `vaddq_f64`, `vmulq_f64`; a broadcast operand as `vmulq_laneq_f64` | `a + b`, `a * b` | `_mm256_add_pd`, ... / `vaddq_f64`, ... |
| `max_nl a b` | `_mm_max_pd(a, b)` | `vmaxnmq_f64(a, b)` | `a > b ? a : b` | `_mm256_max_pd(a, b)` / `vmaxnmq_f64(a, b)` |
| `unord a b` | `_mm_cmpunord_pd(a, b)` | a test of the bits of each (exponent all ones, fraction not zero), then `vorrq_u64` | `a != a \|\| b != b` | `_mm256_cmp_pd(a, b, _CMP_UNORD_Q)` / the bit test |
| `neg`, `abs` | exclusive or, and-not with $-0$ | `vnegq_f64`, `vabsq_f64` | `-a`, `abs_bits(a)` | as the existing packed printers |
| `lt`, `le`, `eq` (pair lines) | `_mm_cmplt_pd` and the others, `lt(a, b)` as `b > a` | `vcltq_f64` and the others | as the scalar printer | as the existing packed printers |
| `select m a b` | `_mm_blendv_pd(b, a, m)` with SSE4.1 or AVX, else and, and-not, or; an arm `0` as one and or and-not; an arm `const nan` as one or with the mask | `vbslq_f64`; an arm `0` as `vbicq_u64` or `vandq_u64`; an arm `const nan` as `vorrq_u64` | `m ? a : b` | blend / `vbslq` |
| swap, broadcast, make | `_mm_shuffle_pd(a, a, 1)`, `_mm_unpacklo_pd`, `_mm_unpackhi_pd` | `vextq_f64(a, a, 1)`, `vdupq_laneq_f64` | nothing | nothing |

A selection with an arm `const nan` printed as an or with the mask gives the NaN with every bit set,
which is quiet; the models' `const nan` is any NaN, and no claim compares NaNs. A selection with an
arm `0` printed as an and gives $+0$, the IR's `0`, bit for bit. Both rewrites are exact for every
input.

- **x86-64**: SSE2 intrinsics, compiled to the VEX encoding where the file has `-mavx`. `float` uses
  the two low lanes of an `__m128`, the two upper lanes $+0$ in every value (constants are made with
  zeros there), so that the unused lanes hold no NaN or subnormal number.
- **arm64**: `float64x2_t` and `float32x2_t`; `unord` by integer tests on the bits, because Clang
  under strict floating point turns a vector comparison of doubles into scalar code. The other
  comparisons in pair lines (the hull, the intersection) keep `vcltq_f64`: correct, and slower with
  Clang under the options.
- **Two numbers**, on every other target, and on any target with `KAIRN_UPWARD_FORM` set to
  `KAIRN_UPWARD_FORM_NUMBERS` (so that the tests run it everywhere): each pair line is its two scalar
  statements, the scalar printer's code; `max_nl` is `a > b ? a : b`, the `MAXPD` form.
- **Arrays**: the existing packed printers on the scalar listing, the lane-0 values in one register of
  $W$ lanes and the lane-1 values in another, so that a swap or a broadcast costs nothing: AVX2 where
  the file has `-mavx2` (4 `double`, 8 `float`), NEON on arm64 (2 and 4); elsewhere the loop calls the
  register form element by element. `max_nl` is `_mm256_max_pd` (the `MAXPD` form) and `vmaxnmq`.

### Barriers

On GCC and Clang (clang-cl included, untested until CI runs it) a **barrier** is an empty assembly
statement that takes the value as an input and an output, `__asm__ __volatile__("" : "+x"(v))` on
x86-64 and `"+w"(v)` on arm64 (for the two-number form on other targets, `"+m"(v)`): it emits no
instruction, and the compiler must assume that it reads and changes the value. The printer emits one
on every input of a kernel after its register is formed, on every output before it leaves, and on the
result of every sign change (`neg`, `abs`, a sign pair line) that is an operand of `add_ru` or
`mul_ru`. With them:

- no operation is folded at compile time, in rounding to nearest, from constant operands;
- no operation is merged with the same operation computed before a change of mode;
- no operation is moved above the scope's write of the mode or below its restoring write, since its
  inputs come from a volatile assembly statement after the scope's own and its result goes to one
  before the scope's end, and volatile assembly statements keep their order;
- nothing is fused into a kernel's first operation (which is why U4 needs no guard), and no negation
  is folded into a product.

The measurement step found the options alone insufficient on every compiler (GCC with
`-frounding-math` moved a product out of a loop above the write of the mode, and merged a sum computed
before and after the change), and the header's operations, with these barriers, right on GCC 13, GCC
16, Clang 18 and Apple clang 21 at every optimization level, even with no option. The generated code
names the barrier through a macro of `upward.hpp`, `KAIRN_DETAIL_UPWARD_BARRIER(v)`, and the first
input through `KAIRN_DETAIL_UPWARD_PIN(v)`, which is the same barrier on GCC and Clang and the barrier
per scope on MSVC: one printer for every compiler *(a choice of the authors)*.

### The interpreter and the emulated formats

The interpreter (`kairn-gen interp`, exact integer arithmetic on any format $(p, q_{\min},
q_{\max})$) computes `add_ru` and `mul_ru` as the rounding up of the exact result in the format with
overflow, with the zero signs of [The operations of the IR](#the-operations-of-the-ir), `unord`
exactly, and `max_nl` in the form the command line names (`--max sel`, `MAXPD`'s, the default;
`--max nm`, `FMAXNM`'s on quiet NaNs). It reads a pair line as its two statements. The emulated limb
type of the tests, `kairn::emulated::Number` ([The emulated formats](../testing.md#the-emulated-formats)),
gets the same four operations, computed with integers, so that the generated code of the upward
kernels runs on any small format without touching the floating-point environment; its form of
`max_nl` is a switch of its runner. Neither needs a mode, a barrier or a scope. The formats: every
format of the statements for the exhaustive runs ([Tests and CI](#tests-and-ci)); the upward kernels
have no constant but `0`, `const inf` and `const nan`, so every format qualifies.

### Object code

`gen/objcode.json` gets, per upward kernel, form (the register form on x86-64 and on arm64, two
numbers, the two array forms) and limb type, the expected counts, and `tests/objcode/objcode.py`
checks them on the flag matrix of each compiler with the options of the target `kairn::upward`
(contraction off, on and fast; `-O0` to `-O3`; `/Od`, `/O2`, `/O2 /GL`):

- **no fused multiply-add** of any kind (`vfmadd*`, `fmla`, `fmadd`, ...): there is none in the IR;
- **no negated multiplication** (`fnmul`, `vfnmadd*`, `fnmadd`, ...): rule U3's reason, in the code;
- **the multiplications**: one per pair line of `mul_ru` in the register form, one per statement in
  the two-number and the array forms;
- **the maxima**: one `maxpd` (`vmaxpd`) or `fmaxnm` per `max_nl`, and no `fmax`, which returns the
  NaN and would make the product wrong;
- **no call**: every kernel is inlined into its caller.

## Statements

### Where they are

The upward kernels get generated files of their own *(a choice of the authors)*:
`proofs/gen/UpwardModel.v` (the kernels as functions of Flocq's `binary_float`, in a section over
`prec emax`, the NaN functions of the operations they use and `max_nl`),
`proofs/gen/UpwardStatements.v` (one `K_spec` per kernel) and `proofs/gen/UpwardAudit.v`
(`K_audit : K_spec := theorem` and `Print Assumptions`, for every kernel whose `ieee_status` is
`proved`). They import two hand-written files: `proofs/theories/IeeeUpwardOperations.v` (`add_ru`,
`mul_ru`, `unord`, `max_nl_ok`, `max_sel`, `max_num`; the existing operations from
`IeeeOperations.v`, unchanged) and `proofs/theories/IeeeUpwardVocabulary.v`. So `Model.v`,
`Statements.v`, `Audit.v`, `IeeeModel.v`, `IeeeStatements.v`, `IeeeAudit.v`, `IeeeWith.v` and the
fold files stay byte for byte what they are; a test of the generator pins their digests, `make -C
proofs` builds and audits both sets, and the audit's four allowed axioms do not change. `max_nl` and
the NaN functions are binders of the statements, as the NaN functions are today, not parameters or
axioms. No file of `proofs/` may contain `Axiom`, `Parameter`, `Admitted` or `admit`, as before.

### The vocabulary

```coq
(* proofs/theories/IeeeUpwardVocabulary.v, over binary_float prec emax *)
Definition upward_empty_1 (u n : float) : Prop := nan u /\ nan n.
Definition upward_nonempty_1 (u n : float) : Prop := xnonempty (xopp (xval n)) (xval u).
Definition upward_1 (u n : float) : Prop := upward_empty_1 u n \/ upward_nonempty_1 u n.
Definition in_upward_1 (u n : float) (x : R) : Prop := xmember (xopp (xval n)) (xval u) x.
Definition upward_bounded_1 (u n : float) : Prop := finite u /\ finite n.
Definition in_number_1 (t : float) (x : R) : Prop := finite t -> x = val t.
```

`xnonempty`, `xmember`, `range_1`, `range_2`, `range_lower`, `range_upper` are those of
`IeeeIntervalVocabulary.v`. `upward_nonempty_1` is the table of [States](#states): the lower bound
$-n$ below $+\infty$ is $n > -\infty$, the upper bound above $-\infty$ is $u > -\infty$, and `xle` is
false on a NaN. `in_upward_1` of the empty set has no member, since `xopp XNaN` is `XNaN`.
`in_number_1 t` is the members of `Interval(t)`: $\{t\}$ for a finite $t$, every real number
otherwise.

### The statements

The sum, in the shape of `interval_add_1_spec` for the stored pair:

```coq
Definition upward_add_1_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax),
  forall xu xn yu yn : binary_float prec emax,
  upward_1 xu xn ->
  upward_1 yu yn ->
  let '(zu, zn) := UpwardModel.upward_add_1 prec emax nan_plus xu xn yu yn in
  upward_1 zu zn /\
  (upward_empty_1 zu zn <-> upward_empty_1 xu xn \/ upward_empty_1 yu yn) /\
  (forall x y : R, in_upward_1 xu xn x -> in_upward_1 yu yn y ->
   in_upward_1 zu zn (x + y)) /\
  (upward_nonempty_1 xu xn -> upward_nonempty_1 yu yn ->
   forall lo hi : xreal,
   range_lower (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_upward_1 yu yn)) lo ->
   range_upper (range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_upward_1 yu yn)) hi ->
   xopp (xval zn) = xrd prec emax lo /\ xval zu = xru prec emax hi) /\
  (upward_bounded_1 xu xn -> upward_bounded_1 yu yn ->
   (upward_bounded_1 zu zn <->
    forall z : R,
    range_2 (fun x y : R => x + y) (in_upward_1 xu xn) (in_upward_1 yu yn) z ->
    Rabs z <= omega prec emax)).
```

In words: I1, the result is canonical; I2, empty exactly when an operand is; I3, every sum of members
is a member; I4, for nonempty operands the lower bound $-z_n$ is the lower bound of the exact range
rounded down and $z_u$ the upper bound rounded up, in the format with overflow (an infinite bound of
the range stays); I5, for bounded operands the result is bounded exactly when the range is within
$\Omega$. The others:

- `upward_sub_1_spec`, `upward_neg_1_spec`: the same with `x - y`, and with `- x` and
  `xopp (xval zn) = lo /\ xval zu = hi` (exact), as `interval_neg_1_spec`.
- **`upward_mul_1_spec`**: the same as the sum with `x * y`, with the binders `nan_mult`, `nan_opp`,
  `nan_const` and `(max_nl : binary_float prec emax -> binary_float prec emax -> binary_float prec
  emax) (max_nl_ok_ : max_nl_ok prec emax max_nl)` before the operands. Its I4 is the sum's:
  **exactly the roundings**, where `interval_mul_1_spec` has one step of slack unless each product of
  finite bounds is zero or at least $P$. The members are real numbers, so $[0, 0] \cdot X = [0, 0]$
  for every nonempty $X$, unbounded included, is part of I3 and I4 (the range is $\{0\}$) and needs no
  clause of its own.
- `upward_add_num_1_spec`, `upward_mul_num_1_spec`: the operand $y$ replaced by the number $t$, its
  members `in_number_1 t`; I2 is `upward_empty_1 zu zn <-> upward_empty_1 xu xn`; I4 for a nonempty
  $x$; I5 under `upward_bounded_1 xu xn -> finite t ->`.
- `upward_hull_1_spec`, `upward_intersection_1_spec`: `interval_hull_1_spec` and
  `interval_intersection_1_spec` with `upward_1`, `upward_empty_1`, `in_upward_1`, and the bounds
  `xopp (xval zn) = lo /\ xval zu = hi`.
- `upward_make_1_spec`: `interval_make_1_spec` with `upward_1 zu zn`,
  `xopp (xval zn) = xval lo /\ xval zu = xval hi` for a nonempty pair, the whole line
  `zu = infinity prec emax false /\ zn = infinity prec emax false` for a NaN or the same infinity
  twice, and `upward_empty_1 zu zn` for reversed bounds.
- `upward_from_interval_1_spec`: for `interval_1 xl xu`: `upward_1 zu zn`,
  `(upward_empty_1 zu zn <-> interval_empty_1 xl xu)`, `(forall z, in_upward_1 zu zn z <->
  in_interval_1 xl xu z)`, and for a nonempty operand `xopp (xval zn) = xval xl /\ xval zu = xval xu`;
  `upward_to_interval_1_spec` the converse.
- The predicates and comparisons: the statements of `interval_*_1_spec` of the same name with the
  vocabulary above (`m = true <-> upward_nonempty_1 xu xn /\ forall x, in_upward_1 xu xn x -> 0 < x`
  for `upward_positive_1`, and so on), every one exact.

The smallest precision is the one each proof needs; the listings were checked from precision 1, and
the target is 1 for every kernel. A statement has a hypothesis on the precision only when its minimum
is above 1, as for the interval kernels.

### How they are to be proved

From Flocq: `Bplus_correct` and `Bmult_correct` with `mode_UP` and their overflow case
(`binary_overflow`: $+\infty$ upward, $-\Omega$ downward), the special values of `Bplus` and `Bmult`
(NaN, infinities, the sign of a zero), `round_opp` ($\mathrm{RU}(-t) = -\mathrm{RD}(t)$) and the
monotony of rounding. From the existing proofs: the bounds of the exact range of a sum and of a
product of intervals, the second spanned by the four products of bounds with $0 \cdot \infty = 0$
(the lemma behind `interval_mul_1`, `IeeeInterval1.v` and `Rectangle.v`), and `IeeeExt.v`'s handling
of selections and comparisons. New: `max_nl_ok` and its two lemmas; the case analysis of the product
(a candidate other than the seed that is $0 \cdot \infty$ is matched by a candidate of the same lane at
least $0$); the greatest of roundings as the rounding of the greatest. *Risk:* low for the sums, the
exact kernels and the conversions; **medium** for the two products, for the number of cases (each
candidate finite, zero, infinite or NaN), as for `interval_mul_1`.

### What is assumed outside the proofs

That **each `add_ru` and `mul_ru` of a generated kernel runs as IEEE 754's operation rounded toward
$+\infty$** in the format of `T` on the values the listing names, and each `max_nl` as one of the two
machine forms on quiet NaNs; the other operations as today. That holds when the thread's mode is
upward with flush to zero and denormals-are-zero off (which the scopes make so) and the compiler
emits the operations as written inside the scope (which the options, the barriers and, on MSVC, the
barrier per scope make so, with the limit of [MSVC](#msvc)). It is the user's responsibility by the
owner's decision of 2026-11-24, the self-check and the checked build's assertions are its evidence,
and it is stated in `docs/concepts/correctness.md` ("What is not machine-checked") and in
`docs/concepts/environment.md`.

## Claims and the oracle

`gen/claims.json` gets one entry per upward kernel, and no entry that exists changes (a test of the
generator compares them with the committed file). Each new entry carries
`"rounding": "upward"`, a field written only in these entries: every operation of the kernel rounds
upward and its runner holds the mode. The vocabulary, by additions to the existing kinds
([Claims of the interval kernels](../architecture.md#claims-of-the-interval-kernels)):

- **`upward(U, N)`**, a requirement: the one-limb inputs U and N are the stored pair of a canonical
  state ([States](#states)).
- **A set named by its stored pair**: in `intervals`, a name may be given `{"upper": U, "nlower": N}`
  instead of `{"lower": L, "upper": U}`, its members those of the state.
- **An output pair**: `encloses_interval`, `interval_set` and `makes_interval` may name their outputs
  `"upper"` and `"nlower"` instead of `"lower"` and `"upper"`; I1 to I5 and the other readings are on
  the state they stand for: empty is two NaN, and the lower bound is $-$ `nlower`.
- **`numbers`**, a list of one-limb inputs of an `encloses_interval` entry: each ranges over the
  members of `Interval(t)`, $\{t\}$ for a finite $t$ and every real otherwise; such an input is never
  empty, and I5's bounded operands include a finite $t$.
- **`same_set`**, a new kind with `of` and `from`, each a set named as above: the output is
  canonical, empty exactly when the input is, and has the same members (so the same bounds, zero signs
  not claimed).

```json
{"name": "upward_mul_1", "domain": "extended", "ieee_only": true, "rounding": "upward",
 "inputs": [{"name": "xu", "limbs": 1}, {"name": "xn", "limbs": 1}, {"name": "yu", "limbs": 1}, {"name": "yn", "limbs": 1}],
 "outputs": [{"name": "zu", "limbs": 1}, {"name": "zn", "limbs": 1}],
 "requires": ["upward(xu, xn)", "upward(yu, yn)"],
 "ensures": [{"kind": "encloses_interval", "upper": "zu", "nlower": "zn", "set": "x*y",
              "intervals": {"x": {"upper": "xu", "nlower": "xn"}, "y": {"upper": "yu", "nlower": "yn"}},
              "tight": {"kind": "rounded"}, "bounded_when": [{"abs_le": "x*y", "omega": true}],
              "bounded_exactly": true}],
 "min_precision": 1, "status": "unverified", "ieee_status": "unverified",
 "instances": {"binary64": [], "binary32": []}},
{"name": "upward_to_interval_1", "domain": "extended", "ieee_only": true, "rounding": "upward",
 "inputs": [{"name": "xu", "limbs": 1}, {"name": "xn", "limbs": 1}],
 "outputs": [{"name": "zl", "limbs": 1}, {"name": "zu", "limbs": 1}],
 "requires": ["upward(xu, xn)"],
 "ensures": [{"kind": "same_set", "of": {"lower": "zl", "upper": "zu"}, "from": {"upper": "xu", "nlower": "xn"}}],
 "min_precision": 1, "status": "unverified", "ieee_status": "unverified",
 "instances": {"binary64": [], "binary32": []}}
```

`upward_add_num_1` claims `encloses_interval` of `x+t` with `"numbers": ["t"]`; `upward_make_1`
claims `makes_interval` with `"upper": "zu", "nlower": "zn"` and `"from": {"lower": "lo", "upper":
"hi"}`; the predicates claim `certain` and `trit` with `exact`, their sets named by stored pairs.

**The line protocol.** The limbs in the order of the kernel's inputs: a state is its two lanes as
stored, `upward_add_1 binary64 XU XN YU YN -> ZU ZN`; the empty set is `nan nan` and the whole line
`inf inf`. A runner of the upward kernels holds an upward scope around its evaluations.

**What the oracle must learn** (it shares no code with the generator, and learns only from
`gen/claims.json` and this page): the requirement `upward` and its strata for the case generator
(the empty set, the whole line, both half-lines, points, zero bounds of either sign, bounds near
$\Omega$, subnormal bounds, crossed sums near zero); the meaning of a stored pair, $[-n, u]$ or empty;
the naming `{"upper", "nlower"}` in sets and outputs; `numbers`; `same_set`; that a nonempty result
has no NaN lane and no lane $-\infty$ (I1); and the field `rounding`, for the request lines it writes.
Its self-test gets injected faults that each reading must catch: a product one step wide (the claim is
exact), an empty result for nonempty operands, one NaN lane, a lane $-\infty$, crossed lanes, a lower
bound read without its negation, a number $t = +\infty$ treated as a point.

## The environment

### What the program guarantees

1. **The options.** GCC and Clang: `-frounding-math`. MSVC: `/fp:strict` (which excludes
   `/fp:contract`). Kairn's existing refusals (fast-math and the others of `config.hpp`) hold. The
   CMake target `kairn::upward` adds the option; the file that includes the header is compiled with
   it, and so is the program's own code in that file.
2. **The mode only through the header's scopes.** Every operation that rounds runs inside a
   `kairn::upward::Scope` (or an array function, which holds its own). The mode is never set by hand
   (`fesetround`, `_mm_setcsr`, `_controlfp_s`) around the type's operations: on GCC and Clang the
   barriers are ordered against the scope's own barriers, not against an arbitrary call, and on MSVC
   the scope is what makes the operations right *(a choice of the authors, a rule on every compiler)*.
3. **One file, one set of options.** The files of a program that use the header are built with the
   same options (the function-level internal linkage removes the copies the linker would mix, but not
   a function of the program's own that is inline and included in files built differently).
4. **Each thread holds its own scope.** The mode is per thread. A thread started inside a scope
   inherits the mode on some systems (the measurement step saw it on Linux and not on macOS or
   Windows); the header never relies on it.
5. **Other code inside a scope runs under the mode**: the program's own arithmetic, the C library's
   mathematical functions, and the default Kairn types, whose kernels assume rounding to nearest
   (a checked build reports them; [Code around a scope](#code-around-a-scope)).

### The scopes

```cpp
namespace kairn::upward {
namespace {                                  // internal linkage: each file compiles its own
class Scope {                                // [[nodiscard]]; not copyable, not movable
public:
    Scope() noexcept;
    ~Scope();
};
class NearestScope { /* the same, to nearest */ };
}  // namespace
}  // namespace kairn::upward
```

- **Entry.** Read the control register (MXCSR on x86-64, FPCR on arm64); compute the wanted state:
  the rounding mode upward (nearest for `NearestScope`), flush to zero and denormals-are-zero off
  (MXCSR bits 15 and 6; FPCR's FZ, bit 24, and where FEAT_AFP is implemented AH and FIZ, bits 1 and 0,
  which read as zero otherwise); write the register **only when that differs** from what was read, so
  that a nested or repeated scope costs one read. The user-facing scopes also set the C library's mode
  (`std::fesetround`) when `std::fegetround()` reports another one, because on x86-64 the C library
  reads its own state (the x87 control word with glibc) and the program's code may ask it; on arm64
  the register is the C library's state and nothing more is done. Then a barrier (an empty assembly
  statement that clobbers memory, `_ReadWriteBarrier()` with MSVC); then, on MSVC, the refresh of
  [MSVC](#msvc); then, in a checked build and when the entry wrote the mode, the check that this
  file's build honors it ([Checks](#checks)).
- **Exit.** A barrier; the C library's mode restored if the entry changed it; the register restored
  if the entry wrote it or changed the C library's mode (glibc's `std::fesetround` writes MXCSR's
  rounding control too), keeping the exception flags raised inside (MXCSR bits 0 to 5 carried over;
  on arm64 the flags are in FPSR, which no scope touches); then, on MSVC, when the exit wrote the
  register, the refresh of [MSVC](#msvc) again, so that an operation after the end of a
  `NearestScope` inside an upward scope, and a value given to `pass()` after a scope, depend on a
  read made after the restoring write.
- **Targets without either register**: the C library's mode alone; flush to zero is left as it is.
- The array functions hold an internal scope of the same kind that writes the register only.
- A nested `NearestScope` inside a `Scope` is how a program calls the default types in an upward
  region; a `Scope` inside a `NearestScope` likewise.

### Code around a scope

The barriers order the header's own operations. Code without barriers can still be moved across a
scope's boundary: an operation of the program, or of a default Kairn type, whose operands are already
in registers may be computed before a `NearestScope` begins, in the mode upward, or before an upward
scope ends, while the program meant it after. This is the movement the measurement step saw the
options fail to prevent; it was measured on the header's operations, not on the default types, which
this design cannot give barriers (they do not change). So *(a choice of the authors)*:

- `kairn::upward::pass(v)` returns `v` after a barrier (on MSVC after the pin of the most recent
  scope), for a `T`, an upward `Interval<T>` and a default `Interval<T, 1>`; a computation on its
  result happens after the most recent scope boundary;
- `to_interval()` puts a barrier on its results, so that a default interval converted inside a
  `NearestScope` is computed on there;
- the concept page asks a program to bring values into a `NearestScope`, and out of an upward region,
  through memory, `to_interval()` or `pass()`, and the self-check and the tests probe both directions
  ([The self-check](#the-self-check)). That this is what the first delivery has, and not a rule
  that keeps the default types out of functions that hold a scope, is [question 1](#open-questions).

### MSVC

**MSVC is supported, with a barrier per scope: the owner's decision of 2026-11-25.** MSVC has no
inline assembly on x64, so the barrier of GCC and Clang does not exist there; `/fp:strict`,
`#pragma fenv_access(on)`, `float_control`, `#pragma optimize` and `_controlfp_s` as the switch of
the mode all left the header's operations wrong in the investigation that preceded the decision
(sums of literals folded, a sum merged across a scope). What made every probe of the pair right at
`/Od`, `/O2` and `/O2 /GL`, under `/fp:strict` and `/fp:precise`:

1. **The refresh.** Each scope, upward or to nearest, after writing the register (or reading it, when
   nothing changes), reads a zero from a `volatile` object and stores it in a `thread_local` variable
   of the header, `kairn::upward::detail::zero` (an `inline thread_local`, of external linkage: one
   per thread of the program, the same in every file).
2. **The pin.** Every rounding kernel ORs that zero into its first input (`KAIRN_DETAIL_UPWARD_PIN`:
   one load and one `orpd`); by rule U6 every rounded operation depends on that input.
3. **The write.** The scopes write MXCSR through a function of their own that is never inlined, on
   entry and on exit (an inline `_mm_setcsr` also made MSVC compile the enclosing loop markedly
   slower).

Why it works: an operation depends on a volatile read made after the mode was set, so it cannot be
folded, merged with one before the scope, or moved above the scope. **The gap**: nothing forces MSVC
to compute an operation before the scope ends rather than after its restoring write (sinking it below
the reset). It was never observed; on GCC and Clang the barrier on the result closes it. So the
assurance on MSVC is weaker, the concept page says so, and the tests and the self-check look for
exactly that movement. Also on MSVC: `/fp:strict` stays required and is checked with `_M_FP_STRICT`,
and `/fp:contract` is refused through `_M_FP_CONTRACT` ([The compile-time guard](#the-compile-time-guard)).

Not yet tested, and tests of step 5: a scope in one file and the operations in another
([Tests](#tests-and-ci), `api.upward.units`), and a program and a DLL: each module of Windows has its
own copy of an inline `thread_local`, so operations compiled into a DLL and run inside a scope of the
program read a copy that the program's scopes never write; until a test says otherwise the concept
page asks that the scopes and the operations be in the same module. A rejected alternative: a
volatile read in every operation instead of once per scope, independent of the scopes, cost several
times more on a sum in the investigation (to be measured and recorded in step 6).

### Contraction

`-ffp-contract=off` is **not required** *(a choice of the authors)*: no listing has a product that
feeds a sum (the products feed maxima), the inputs pass through barriers on GCC and Clang, so nothing
of the program can be fused into a kernel, and `/fp:strict` excludes contraction on MSVC. The
object-code check verifies it under `-ffp-contract=fast`. The program's own arithmetic in the scope
may be contracted, which is its business; the self-check reports it as advice.

### The compile-time guard

In `upward.hpp`, unless `KAIRN_UPWARD_OPTIONS_UNCHECKED` is defined:

| Compiler | The header stops the build when |
|---|---|
| GCC | `__ROUNDING_MATH__` is not defined (no `-frounding-math`) |
| MSVC (not clang-cl) | `_M_FP_STRICT` is not defined, or `_M_FP_CONTRACT` is |
| Clang, Apple clang, clang-cl | never: they define no macro for `-frounding-math` or for contraction; the self-check and a checked build's scope check report a missing option |
| any | `config.hpp`'s refusals (fast-math, finite-math-only, reassociation, ...), which the macro does not override |

The message names the option and the target `kairn::upward`. `KAIRN_UPWARD_OPTIONS_UNCHECKED` says
that the program takes the options on itself (a compiler the header does not know, or an option set
by a pragma it cannot see); it disables the rows of GCC and MSVC only, and is documented in
`config.hpp`'s style, in the concept page and in the header.

### The marks

Every file of the feature says, in its first paragraph, that it requires the mode upward set by
`kairn::upward::Scope` and the options of `docs/concepts/upward.md` (GCC and Clang
`-frounding-math`, MSVC `/fp:strict`): the public header, the generated header (the generator prints
the mark), each kernel description, the test files, the CMake target, the benchmarks. A test of the
generator checks the mark in the generated header and the descriptions; one of the tests checks the
others.

### The CMake target

`kairn::upward`: an `INTERFACE` library that links `kairn::kairn` and adds `-frounding-math` (GCC and
Clang, clang-cl's `/clang:-frounding-math`) or `/fp:strict` (MSVC) to the files of the targets that
link it, as `kairn::fma` adds its option today. It adds nothing else.

## The interface

### Linkage

Inline functions shared by files built with different options are mixed by the linker: the
measurement step saw a file built correctly run the other file's copy of an operation, on all five
compilers, and internal linkage fixed it everywhere. So **every function whose result can depend on
the options of its file has internal linkage**: every function that rounds (the arithmetic operators
and the operations with a number, `static` function templates at namespace scope, found by
argument-dependent lookup in `kairn::upward`), the scopes, `pass()`, `self_test()` and the array
functions (in an unnamed namespace). **The class `Interval<T>` has external linkage**, so that a
program can pass an interval between files (a type of internal linkage would be a different type in
every file); its member functions compute only exact operations (sign changes, comparisons, selections,
NaN tests), whose results are the same under every option `config.hpp` accepts and every mode, so the
linker may keep any copy *(a choice of the authors: the measured fix asks internal linkage of every
function, which a type usable across files cannot have)*.

### The type

A sketch, with the template headers and the overloads for `float` left out:

```cpp
namespace kairn::upward {
template <class T>                                    // float or double
class Interval {
public:
    Interval() noexcept;                              // [0, 0]
    Interval(T a) noexcept;                           // upward_make_1(a, a): [a, a]; the whole line for a NaN or an infinite a
    Interval(T lo, T hi) noexcept;                    // upward_make_1(lo, hi)
    static Interval from_bounds(T lo, T hi) noexcept; // the same, under the default type's name
    explicit Interval(const kairn::Interval<T, 1>& x) noexcept;   // upward_from_interval_1
    static Interval empty() noexcept;                 // (NaN, NaN)
    static Interval whole() noexcept;                 // (+inf, +inf)
    static Interval from_limbs(const T* p) noexcept;  // (p[0], p[1]) = (u, n) as stored; canonical (checked)
    void to_limbs(T* p) const noexcept;               // writes (u, n)
    kairn::Interval<T, 1> to_interval() const noexcept;   // upward_to_interval_1, barriers on the result
    T lower() const noexcept;  T upper() const noexcept;  // upward_to_interval_1's bounds
    bool is_empty() const noexcept;  bool is_whole() const noexcept;  bool is_finite() const noexcept;
    bool contains(T t) const noexcept;  bool contains(const Interval& y) const noexcept;
    bool certainly_positive() const noexcept;  bool certainly_negative() const noexcept;
    bool certainly_zero() const noexcept;
    Interval hull(const Interval& y) const noexcept;  Interval intersection(const Interval& y) const noexcept;
};
// internal linkage; each needs an upward scope
static Interval<T> operator+(Interval<T>, Interval<T>), operator-(...), operator*(...);
static Interval<T> operator+(Interval<T>, T), operator+(T, Interval<T>), operator-(Interval<T>, T),
                   operator-(T, Interval<T>), operator*(Interval<T>, T), operator*(T, Interval<T>);
static Interval<T>& operator+=(Interval<T>&, Interval<T>);   // and -=, *=, with an interval or a T
static Interval<T> operator-(Interval<T>);                    // exact
// exact, any mode
Trit less(x, y), less_equal(x, y), greater(x, y), greater_equal(x, y), equal(x, y), not_equal(x, y);
Trit member(T t, x);
namespace ieee1788 { bool equal(x, y), interior(x, y), disjoint(x, y); }
T pass(T), Interval<T> pass(Interval<T>), kairn::Interval<T, 1> pass(const kairn::Interval<T, 1>&);
}
```

Every member and every function forwards to one kernel of [The kernels](#the-kernels), but
`is_finite()` (a test of the bit patterns of the two lanes, as the default type's, not machine-checked),
`empty()`, `whole()`, the default constructor (constants), `from_limbs` and `to_limbs` (a load and a
store), and the compositions named there. Like the default type's, an operation compiles without
`kairn::unverified` only when its kernel is proved (`gen/upward.hpp` holds the status of each).
`kairn::Trit` is the default library's.

- **Nothing is `constexpr`** *(a choice of the authors)*: constant evaluation rounds to nearest, so an
  operation that rounds would give at compile time another result than at run time, a wrong bound;
  the exact operations could be, but the storage is a register type with no portable constant
  initialization, and the type exists for speed at run time. A constant interval is made with the
  default type and converted.
- **No implicit conversion between the two interval types**, in either direction, and no operation
  that mixes them: each conversion is a call by name. The default header has no knowledge of this
  one.
- **Deliberately absent**: midpoint, radius, `mid_rad`, `split`, conversions to and from `Ball`,
  `Interval<T, 2>`, comparison operators (as for the default type), `operator/`.

### Arrays

```cpp
namespace kairn::upward {
template <class T> struct View {        // T or const T; owns nothing
    T* upper; T* nlower; std::size_t size;
    View(T* upper, T* nlower, std::size_t size) noexcept;
};
namespace {
void add(View<T> z, View<const T> x, View<const T> y) noexcept;   // z = x + y, element by element
void sub(View<T> z, View<const T> x, View<const T> y) noexcept;
void mul(View<T> z, View<const T> x, View<const T> y) noexcept;
void neg(View<T> z, View<const T> x) noexcept;
void add(View<T> z, View<const T> x, T t) noexcept;               // z = x + t
void mul(View<T> z, View<const T> x, T t) noexcept;               // z = x * t
}
}
```

A **new interface** *(a choice of the authors: Kairn has no array interface for the one-limb interval
today)*: two plain arrays, the upper bounds and the negated lower bounds, element $i$ the state
$(u_i, n_i)$. Each function holds its own scope (register only) for the call, so a program may call
it from code that rounds to nearest; each loads after the scope is set and stores before it ends, and
runs the kernel's array form ([The printers](#the-printers)). A view may be the array written and an
array read, the same arrays (in place); otherwise the arrays written overlap none read. Each element
must be canonical. Short arrays cost the scope's write per call; a program that calls them on short
arrays in a loop holds one `Scope` around the loop, and the nested scopes then cost a read.

**No second layout in the first delivery** *(a choice of the authors)*: an array of pairs, $(u, n)$
interleaved, is what a client that stores the two numbers together has. The measurement step found
it slower than two arrays for products, and a loop of the scalar type over such an array, with
`from_limbs` and `to_limbs` (a load and a store of one register) inside one `Scope`, is the same code;
the scalar type serves that layout without a function of its own. One can be added later if a client
measures a need.

### Checks

`KAIRN_CHECKS`, as for the default types (1 without `NDEBUG`, 0 with it), and
`KAIRN_ENVIRONMENT_FAILURE` for every report. By the owner's decision of 2026-11-24 the checks that
are not strictly needed are assertions, made in a checked build only:

| Check | Checked build | Release build |
|---|---|---|
| before each operation that rounds: the mode is upward, flush to zero and denormals-are-zero off (one read of the register) | yes | no |
| before each exact operation: flush to zero and denormals-are-zero off (a comparison reads a subnormal number as zero under them) | yes | no |
| the operands are canonical (NaN tests and comparisons; a NaN lane quiet) | yes | no |
| `from_limbs`, `View` elements: canonical | yes | no |
| array functions: lengths, aliasing, every element canonical | yes | no |
| on entry of an upward scope that writes the mode: this file's build honors it, $1 + 2^{-60} > 1$ on literal operands, which a build that folds in rounding to nearest makes false, computed in a function of the file's own that is not inlined, after the barrier | yes | no |
| the default types used inside an upward scope (their own checks, unchanged) | yes | no |
| the scopes' work (write on change, flush to zero off and restored, flags kept, barriers, the MSVC refresh) and the array functions' own scopes | yes | yes |
| the special cases of the kernels (they are the listings, not checks) | yes | yes |

The scope's check of the build is not strictly needed: with the barriers the header's operations are
right on GCC and Clang without the option, and a missing option on GCC and MSVC stops the build. It
protects the program's own arithmetic, so it is an assertion *(a choice of the authors, by the owner's
rule; the earlier plan had kept it in release builds)*. The default `kairn::self_test()` fails inside
an upward scope, as it should.

## The self-check

`kairn::upward::self_test()` returns the existing `kairn::Status`. It has internal linkage, so it
tests the file that calls it, with that file's options; a program calls it from each file built with
other options. It holds its own scopes and restores the caller's state.

**Failures** (`ok()` false; `failure` the first, `kernel` the case):

1. the mode cannot be set upward, does not read back as upward inside a scope, or is not restored; the
   C library's mode does not follow the user-facing scope;
2. flush to zero or denormals-are-zero inside a scope: a product of normal numbers whose result is
   subnormal, a sum of subnormal numbers, and a tiny positive product that must round up to $\eta$,
   compared bit for bit;
3. every kernel, for `double` and `float`, on fixed operands read through `volatile` objects, against
   the values the generator's interpreter computed for them (stored in `gen/upward.hpp`, as
   `gen/selftest.hpp` stores the default kernels' results), a zero of either sign and a NaN as a NaN;
4. the same calls on literal operands written in the file (a build that folds them shows here);
5. pairs on which $(-a)\,b$ rounded up differs from $-(a\,b)$ rounded up, through the product's lower
   bound (a negation moved through a product shows here);
6. the special cases: unbounded operands, overflow both ways, $0 \cdot \infty$, $[0, 0]$ times the
   whole line, the empty set, a number $t$ infinite and NaN;
7. an operation on values held in registers computed before a scope and again inside it, and inside a
   scope in a loop of unknown length (a merge, or a move above the change of mode, shows here);
8. **an operation whose result is used only after its scope has ended** (a move below the restoring
   write: the gap of [MSVC](#msvc), probed on every compiler);
9. each array function on a short array.

**Advice** (`limitation` set, `ok()` still true): this file's own arithmetic ignores the mode (the
literal sum and $(-a)\,b$ of the file's own code, not the header's); a product of the program
contracted into a sum of the program; a default-type computation right after an upward scope, on
operands in registers, that came out as if computed inside it (the risk of [Code around a
scope](#code-around-a-scope)). The first two are advice because the header's results do not depend on
them; the third because the default types are the program's to place.

**Its limits**, which the concept page states: it tests its own copies of the operations, compiled in
the file that calls it, not every place where the program uses them; a compiler can move code in a
program where it did not in the self-check's own shapes (the measurement step needed several shapes
of the test loop before one caught GCC's movement of a product); on MSVC it probes the gap in its own
shapes only. It is evidence, not proof; with the barriers it is a second line of defence, not the
first.

## Tests and CI

All of the feature's tests have the label `upward` and are registered when `KAIRN_UPWARD_TESTS` is
on (the default); every target that builds them links `kairn::upward`.

**The generator's suite** (`gen/tests/test_upward.py`, its own module): refusals of each rule U1 to
U7 and P1 to P5; every upward kernel through the interpreter on every pair of canonical states of the
formats of the statements of precision 1 to 4, with both forms of `max_nl`, judged by the oracle with
no violation (**the gate of step 2**); the emulated kernels (`tests/emulated/gen/upward.hpp`, the
two-number printer with `kairn::emulated::Number`, which computes `add_ru` and `mul_ru` with
integers and needs no mode) on the same pairs, the same bytes as the interpreter with the same form of
the maximum; the compiled runner (`gen/tests/upward_runner.cpp`, holding an upward scope) in each form
(the register form, the two-number form forced, the AVX2 and NEON array forms) on the generator's
build matrix with the options, bit for bit the interpreter's with the backend's form of the maximum,
on random cases of every stratum and on the special operands; the existing generated files'
digests unchanged; the counts of the object-code check.

**The quick tier**: `crosscheck.compiled.upward_K.F` (each kernel through the compiled runners,
judged by the oracle); `api.oracle.upward_K.F` (every public operation through a runner of the line
protocol over `<kairn/upward.hpp>`, under the name every kernel's test of the public interface
has); `api.upward.differential` (each operation against the default
`Interval<T, 1>` on the same operands, random and the special pairs of every combination of special
intervals: equal bounds but zero signs for the sums, the exact kernels and the conversions; for the
product, inside the default's and equal to it outside the range below $P$; and every result judged by
the oracle in exact arithmetic); `api.upward.self_test`; `api.upward.scope` (nesting, restore, flags
kept, flush to zero forced off and restored, the C library's mode, a `NearestScope` inside); 
`api.upward.checks` (a checked build: an operation outside a scope reports, a default type inside one
reports, a non-canonical state reports, through a handler of `KAIRN_ENVIRONMENT_FAILURE`; a release
build makes none of them); `api.upward.reject.*` (cases from 119 on in `tests/api/reject.cpp`: GCC
without `-frounding-math`, MSVC without `/fp:strict`, MSVC with `/fp:contract`, each with a control
that defines `KAIRN_UPWARD_OPTIONS_UNCHECKED`; an implicit conversion between the two interval types;
an operation of the two types; an upward operation in a constant expression; `midpoint()`);
`api.upward.units` (two files built with different options, and on MSVC a scope in one file and the
operations in the other: the `thread_local` across files); `api.upward.moves` (the probes of the
self-check's items 7 and 8 and of [Code around a scope](#code-around-a-scope), in more shapes, at every
optimization level); `objcode.upward`.

**The full tier**, the flag matrix of the feature:

| Configuration | Expected |
|---|---|
| with the options: GCC 13 and 16, Clang 18, Apple clang 21, MSVC and clang-cl; `-O0` to `-O3` and `/Od`, `/O2`, `/O2 /GL`; contraction off, on and fast; with and without `-mavx2 -mfma` on x86-64; `KAIRN_CHECKS` 0 and 1; the two-number form forced | every test passes |
| GCC without `-frounding-math`, MSVC without `/fp:strict` | the build stops (a reject test); with `KAIRN_UPWARD_OPTIONS_UNCHECKED`, reported, not gated |
| Clang and Apple clang without `-frounding-math` | builds; the header's results right (the barriers), pinned by the api tests; `self_test().limitation` set; in a checked build the scope's check reports |
| x86-64 under Rosetta, and emulators | reported, not gated: whether they honor MXCSR's rounding mode is not established |

**CI.** The upward tests run in the existing jobs of `build.yml`, `full.yml` and `generator.yml` on
Linux and macOS. The MSVC job of the quick tier is near its time limit, so it configures
`-DKAIRN_UPWARD_TESTS=OFF`, and a new job of `build.yml`, "Windows x64, upward", builds and runs only
the label `upward` with MSVC and with clang-cl, so the long job does not get longer. The nightly brute
force gets the upward kernels through the runners it already drives. `proofs.yml` builds the new files
with the rest. `docs/developer/testing.md` gets the new tests, as for every addition.

## Documentation

- **New:** `docs/concepts/upward.md`, "The round-up interval": what it is for (one-limb intervals in
  hot loops, filters that decide a sign), what the program must guarantee (the options, the scopes
  only, one set of options per program, threads, other code under the mode, the default types inside
  a `NearestScope`, `pass()`), the cost of a scope and why it goes around regions of many operations,
  the differences from the default interval, the self-check and its limits, MSVC's weaker assurance;
  marked at its top as requiring the options. Reference pages of the upward kernels, written by
  `docs/tools/reference.py` from the claims (it learns the new naming and kinds), and a reference page
  of the header.
- **Changed:** `docs/concepts/environment.md` (the contract's first item: the default types never
  change the mode; the opt-in header sets it upward in its scopes; a section on the upward header's
  options and scopes); `docs/concepts/correctness.md` (the new assumption, in "What is not
  machine-checked"; the upward kernels in "What is proved in which model"); `docs/concepts/index.md`;
  `include/kairn/environment.hpp`'s comment ("Kairn never reads or writes the rounding mode" holds of
  the default types); `docs/developer/architecture.md` (the four operations, the family and its
  rules, the pair form, the claims, the new generated files); `gen/README.md` (the operations table,
  the description fields, the rules, the tests); `oracle/README.md`; `docs/developer/testing.md`;
  `docs/developer/design/phase0/references.md` (the references below).
- **The brief's section** "Floating-point environment (non-negotiable)" gets a dated note: the owner's
  decision of 2026-11-24 makes an exception for the opt-in header; the default types are unchanged.
- **In one commit**, as for every change of plan: a row of the
  [decisions log](phase0/decisions.md#decisions-log) with the owner's decisions of 2026-11-24 and
  2026-11-25, a row of the authors' choices of this page, and a deviation from the brief (the
  exception to "No fesetround or dynamic rounding modes", and the barriers in a public header, behind
  macros, with a path for each compiler, beside "No compiler extensions in public headers"); a row in
  the plan's table of milestones and one in the README's list, for the feature between Milestones 2
  and 3 (it is not Milestone 3, which is not started); the version 0.4.0, a new public interface.

## Work breakdown

Each package has its inputs, the files it owns, and its gate. Packages in the same wave can run in
parallel; at most four at once.

| Package | Inputs | Owns | Gate | After |
|---|---|---|---|---|
| **U0. Rulings** | this page | none | the open questions answered ([done](#open-questions)) | none |
| **U1. Generator: IR, rules, interpreter, claims, Rocq printer** | this page, U0 | `gen/kairn_gen/` (`ir.py`, `rules.py`, `interp.py`, `claims.py`, `rocq.py` or a module of its own, `build.py`), `gen/kernels/upward_*.kernel`, the generated `gen/claims.json` entries and `proofs/gen/Upward*.v`, `gen/tests/test_upward.py`, `gen/README.md` and the IR and claims sections of `architecture.md` | the generator's suite; the existing generated files byte for byte unchanged; the exhaustive interpreter runs on precision 1 to 4 judged by U3's oracle with no violation; every refusal tested | U0; the oracle's part of the gate needs U3 |
| **U2. Generator: C++ printers** | U1 | the C++ printers (`cpp.py`, `simd.py` or a module of their own), `emulated.py`, `objcode.py`, `library.py`, the generated `include/kairn/gen/upward.hpp`, `tests/emulated/number.hpp` (the new operations) and `tests/emulated/gen/upward.hpp`, `gen/tests/upward_runner.cpp`, `gen/objcode.json`, `tests/objcode/` | the compiled runners in every form bit for bit the interpreter's, on the generator's matrix with the options; the emulated runs identical to the interpreter's; the object-code counts on every compiler at hand | U1 |
| **U3. Oracle** | this page | `oracle/`, `oracle/README.md` | its self-test, the injected faults caught; it reads every new entry | none (wave 1) |
| **U4. Proofs** | this page for the vocabulary and the lemmas; U1's `UpwardStatements.v` for the theorems | `proofs/theories/IeeeUpward*.v`, the proofs' `Makefile` and audit script | `make -C proofs` green; the audit prints only the four allowed axioms; every upward kernel `ieee_status: proved`; the existing statements unchanged | the lemmas from wave 1; the theorems after U1 |
| **U5. Library: the scopes and the environment** | this page, U0 | the scope part of `include/kairn/upward.hpp` (`Scope`, `NearestScope`, `pass`, the MSVC refresh and write, the guard and its macro, the build check), the CMake target | the scope tests (nesting, restore, flags, flush to zero, C library), the reject tests of the guard, the two-file `thread_local` test on MSVC | U0 (wave 1) |
| **U6. Library: the type, the arrays, the self-check** | U2, U5 | the rest of `include/kairn/upward.hpp`, the marks | the api runner judged by the oracle for every kernel; the differential tests; `self_test()` passes with the options and gives advice without them on Clang | U2, U5 |
| **U7. Tests and CI** | U6 | `tests/api/upward/`, `tests/CMakeLists.txt` and `tests/full/`, `.github/workflows/build.yml` (the new job), `docs/developer/testing.md` | every workflow green, the new MSVC job included; the existing MSVC job's time unchanged | U6 |
| **U8. Documentation, benchmarks, report** | U7 | `docs/concepts/upward.md`, the changed pages, `docs/tools/reference.py`, the reference pages, the decisions log, the plan, the README, the version, the benchmarks under `bench/` | `mkdocs build --strict`, the reference check, the link check; the measurements rerun on the shipped type; the draft pull request and its report | U7 |

Waves: U1, U3, U4's lemmas and U5 first; then U2 and U4's theorems; then U6; then U7; then U8.

**The largest risks**, in order:

1. **The register printers** (U2): the pairing, the lane moves and the instruction selection are the
   largest new piece, and the printers are trusted. Mitigated by the bit-for-bit comparison of every
   form with the interpreter and with the two-number form, and by the object-code counts.
2. **Code around a scope**: the default types and the program's code can be moved across a scope's
   boundary, which no barrier of this header can prevent and nothing has measured yet.
3. **MSVC**: the gap (an operation sunk below the scope's end), the `thread_local` across files (not
   tested) and across modules (unsupported until tested).
4. **The products' proofs** (U4): the case analysis of the seed and the dropped candidates, for each of
   the two products, over every kind of candidate.
5. **The self-check's fragility**: a probe that misses a movement in its own shapes passes; with the
   barriers it is the second line, not the first.
6. **Clang on arm64** turns vector comparisons into scalar code under the options: the hull and the
   intersection are slower there; the predicates read lanes as numbers and are not affected.
7. **CI time** on the hosted Windows runner, handled by the separate job.

## Open questions

The questions this page left open when it was written, each settled before the implementation
started. Every answer is a choice of the authors, listed with the others for the owner's review.

1. **Code around a scope.** `pass()`, the barriers on `to_interval()` and the concept page's rule
   are what the first delivery has, and `NearestScope` is part of it. The header promises nothing
   about code without barriers that shares a function with a scope beyond that rule; the tests
   `api.upward.moves` measure the movement on every compiler, and the report records what they find.
2. **The scope's check of the build** is made in a checked build only ([Checks](#checks)).
3. **`-ffp-contract=off`** is not required ([Contraction](#contraction)).
4. **Linkage**: as [Linkage](#linkage) says: the class and its exact members of external linkage,
   everything that rounds of internal linkage.
5. **The operations with a number** exist, with $x - t$ and $t - x$ as compositions.
6. **Arrays**: two arrays only; an array of pairs is served by the scalar type.
7. **Where the feature goes**: a row between Milestones 2 and 3 in the plan's table and in the
   README's list, named "The round-up interval", with no milestone number; the version 0.4.0.
8. **MSVC and DLLs**: the tests get a case with the scope in the program and the operations in a DLL.
   Until it passes in CI, the concept page asks that the scopes and the operations be in the same
   module, and says that the other arrangement is not supported.
9. **The names** are those of [Choices of the authors](#choices-of-the-authors), item 1.

## References

- B. Lambov. *Interval Arithmetic Using SSE-2.* In W. Luther, P. Hertling, C. M. Hoffmann,
  N. Revol (eds.), *Reliable Implementation of Real Number Algorithms: Theory and Practice*, Lecture
  Notes in Computer Science 5045, Springer, 2008, pp. 102–113; first in Dagstuhl Seminar Proceedings
  06021, 2006, [doi:10.4230/DagSemProc.06021.6](https://doi.org/10.4230/DagSemProc.06021.6) (the
  version read). An interval in one SSE2 register as $\langle \ell, -h \rangle$ under rounding toward
  $-\infty$, set once for a computation: a sum is one addition, a negation one swap, the hull one
  minimum; the product selects four of the eight products by the signs of a bound. The storage of
  this page is the mirror image (the lower bound negated, rounding upward); its product has no branch
  and handles $0 \cdot \infty$ and the empty set. The paper also notes that compilers fold the pairs
  of negations that such code relies on, which rule U3 and the barriers address.
- M. Attene. *Indirect Predicates for Geometric Constructions.* Computer-Aided Design 126, 2020,
  [doi:10.1016/j.cad.2020.102856](https://doi.org/10.1016/j.cad.2020.102856). The paper that the
  library NFG ("Numbers For Geometry", [github.com/MarcoAttene/NFG](https://github.com/MarcoAttene/NFG),
  LGPL) asks to cite. The owner's request of 2026-11-24 named NFG's storage of an interval in one
  register as the model to adopt if worth it. No code of NFG is used or copied.
- IEEE Std 754-2019 ([references](phase0/references.md#ieee-754)): rounding toward $+\infty$, the
  sign of an exact zero sum under each rounding direction, the quiet NaN that an operation delivers.
- <a id="intel-sdm"></a>Intel 64 and IA-32 Architectures Software Developer's Manual, volume 2, `MAXPD`
  (the second operand returned when either operand is a NaN or both are zeros), and volume 1 for
  MXCSR; <a id="arm-arm"></a>Arm Architecture Reference Manual for A-profile, `FMAXNM` (vector) and
  its pseudocode `FPMaxNum`, and FPCR.
- Flocq ([references](phase0/references.md#proof-assistants)): `Bplus`, `Bmult`, `mode_UP`,
  `round_opp`.
