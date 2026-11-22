# One enclosure interface: intervals and balls

`Interval<T, k>` and `Ball<T, k>` are both sets of real numbers that contain every exact result of
the computation that made them, and they answer the same questions under the same names, so that
an algorithm can be written once and run on either, with one limb or two
([One enclosure interface](../developer/design/milestone2.md#one-enclosure-interface); the
[tutorial on bisection](../tutorials/bisection.md) is such an algorithm). Every function is one
generated kernel, proved in Rocq and judged by the oracle through the public interface, or one of
the two compositions said below. What each answer means differs by the type and the number of
limbs: for an interval the predicates and comparisons are **exact**; for a ball of one limb the
predicates are exact, and the comparisons exact when the sum of the radii is at most $\Omega$,
the largest finite number of `T`; for a ball of two limbs most are only **certain**, an answer
that is right when it is given and that may not be given near the boundary. This page says which,
function by function, and what is not claimed. Each kernel's own page has its statement in full.

The functions are in `kairn/interval.hpp` and `kairn/ball.hpp`, and the three types they share
(`kairn::Trit`, `kairn::Split`, `kairn::MidRad`) in `kairn/enclosure.hpp`; `kairn/kairn.hpp`
includes all three. `T` is `float` or `double`, `X` and `Y` two sets of the same type, `T` and $k$,
and `t` a point: a value of `T` or a number of $k$ limbs.

## The interface

| Function | `Interval<T, k>` | `Ball<T, k>` |
|---|---|---|
| `X.lower()`, `X.upper()`: bounds of $k$ limbs | the stored bounds | one limb: $\mathrm{RD}(c - r)$, $\mathrm{RU}(c + r)$ ([`ball_lower_as_1`](ball_lower_as_1.md), [`ball_upper_as_1`](ball_upper_as_1.md)); two limbs: the bounds of [`ball_to_interval_2`](ball_to_interval_2.md), each computing both |
| `X.lower_as<T>()`, `X.upper_as<T>()`: bounds of `T` | one limb the bounds; two limbs rounded outward ([`to_down_2`](to_down_2.md), [`to_up_2`](to_up_2.md)) | [`ball_lower_as_k`](ball_lower_as_1.md), [`ball_upper_as_k`](ball_upper_as_1.md) |
| `X.midpoint()`, `X.radius()`, `X.mid_rad()` | [`interval_mid_rad_k`](interval_mid_rad_1.md), one call for `mid_rad()`, one each for the others | the center and the radius, stored |
| `X.is_empty()`, `X.is_whole()` | [`interval_empty_k`](interval_empty_1.md), [`interval_entire_k`](interval_entire_1.md) | tests of the radius (a NaN, $+\infty$), no kernel |
| `X.contains(t)`; `member(t, X)`, a `Trit` | [`interval_contains_k`](interval_contains_1.md) | [`ball_contains_point_k`](ball_contains_point_1.md) |
| `X.contains(Y)`: $Y \subseteq X$ | [`interval_subset_k`](interval_subset_1.md) | [`ball_contains_ball_k`](ball_contains_ball_1.md) |
| `X.certainly_positive()`, `X.certainly_negative()`, `X.certainly_zero()` | [`interval_positive_k`](interval_positive_1.md), [`interval_negative_k`](interval_negative_1.md), [`interval_zero_k`](interval_zero_1.md) | [`ball_positive_k`](ball_positive_1.md), [`ball_negative_k`](ball_negative_1.md), [`ball_zero_k`](ball_zero_1.md) |
| `less(X, Y)`, `less_equal(X, Y)`, `equal(X, Y)`, and `greater`, `greater_equal`, `not_equal`: a `Trit` | [`interval_less_k`](interval_less_1.md), [`interval_less_equal_k`](interval_less_equal_1.md), [`interval_equal_k`](interval_equal_1.md) | [`ball_less_k`](ball_less_1.md), [`ball_less_equal_k`](ball_less_equal_1.md), [`ball_equal_k`](ball_equal_1.md) |
| `X.hull(Y)`, `X.intersection(Y)` | [`interval_hull_k`](interval_hull_1.md), [`interval_intersection_k`](interval_intersection_1.md) | [`ball_hull_k`](ball_hull_1.md), [`ball_intersection_k`](ball_intersection_1.md) |
| `X.split()`: a `Split` | [`interval_split_k`](interval_split_1.md) | [`ball_split_k`](ball_split_1.md) |
| to the other type, explicit | `Ball<T, k>(X)`: [`interval_to_ball_k`](interval_to_ball_1.md) | `Interval<T, k>(X)`: [`ball_to_interval_k`](ball_to_interval_1.md) |
| from two values of `T` | `Interval<T, k>(lo, hi)` | `Ball<T, k>::from_interval(lo, hi)`: [`ball_from_interval_k`](ball_from_interval_1.md) |
| the relations of IEEE 1788: `ieee1788::equal`, `subset`, `interior`, `disjoint` | [`interval_rel_equal_k`](interval_rel_equal_1.md), [`interval_subset_k`](interval_subset_1.md), [`interval_rel_interior_k`](interval_rel_interior_1.md), [`interval_rel_disjoint_k`](interval_rel_disjoint_1.md) | none ([below](#ieee-1788)) |

`greater(X, Y)` is `less(Y, X)` and `greater_equal(X, Y)` is `less_equal(Y, X)`, the same kernels
with the operands exchanged; `not_equal(X, Y)` is `equal(X, Y)` with yes and no exchanged. Each
function takes two sets of one type, `T` and $k$ and nothing else: a point given to `contains` is a
member test, never made a set, so that `X.contains(+inf)` is false on the whole line while
`X.contains(Interval(+inf))`, the whole line in the whole line, is true. Each also accepts the
marker `kairn::unverified` on an operand, which it would need while its kernel were UNVERIFIED
([What holds today](../getting-started/guarantees.md#proved-and-unverified)).

## What is exact, what is certain, what is not claimed

*Exact*: the answer is the truth about the members, for every canonical operand. *Certain*: an
answer that is given is right, and the function may decline to give it (a `bool` false, a `Trit`
unknown) when the operands are near the boundary of the relation; how near is measured, not
claimed ([Claims of the enclosure interface](../developer/architecture.md#claims-of-the-enclosure-interface-predicates-and-comparisons)).
On the empty set, the whole line and a point that is not finite, every answer of this table is
exact, of every type.

| Function | `Interval<T, 1>` | `Interval<T, 2>` | `Ball<T, 1>` | `Ball<T, 2>` |
|---|---|---|---|---|
| `is_empty`, `is_whole` | exact | exact | exact (no kernel) | exact (no kernel) |
| signs `certainly_*` | exact | exact | exact | exact |
| `contains(t)`, `member(t, X)` | exact | exact; for `t` of `T` composed with `make_2` | exact, by exact pairs | certain: `contains` true only for a member; `member` yes, no or unknown, which it may be within about $2e + 3G$ of $\lvert t - c\rvert = r$ |
| `contains(Y)` | exact | exact | exact, by exact pairs | certain: true only if $Y \subseteq X$; may be false within about $2e + 4G$ of the boundary |
| `less`, `less_equal`, `equal` and mirrors | exact | exact | exact when $r_x + r_y \le \Omega$; beyond, unknown where the sum of the radii and the difference of the centers both overflow, never wrong | certain: may be unknown when the gap between the balls is within about $2e + 4G$ of zero |
| relations of IEEE 1788 | exact | exact | not provided | not provided |
| `hull`, `intersection` | exact: the smallest interval | exact | contains what it must; not claimed the smallest | the same |
| `split` | two parts that are the interval and meet at a point of it, **not claimed the midpoint** | the same | two parts that cover $[c - r, c]$ and $[c, c + r]$; not claimed inside $X$, nor smaller | the same |
| `midpoint`, `radius` | within one rounding and $\eta$ of the midpoint, inside $X$; the smallest radius of `T` for it | within $\frac{3u^2}{1 - 4u}$ relative and $2\eta$, inside $X$; a radius that covers $X$, not claimed the smallest | the center and the radius | the same |
| to the other type | the ball of the midpoint with the smallest radius | a ball that contains $X$, finite when its bounds are at most $2^{e_{\max}-2}$ | the smallest interval of `T`, $[\mathrm{RD}(c - r), \mathrm{RU}(c + r)]$ | each bound within $A\lvert v\rvert + B$ of $c \mp r$, $A \approx 8u^2$ |

Here $\Omega$ is the largest finite number of `T`, $\eta$ its smallest subnormal number, $u$ its
unit roundoff; for a ball of two limbs $e$ is the bound of the error of the difference of the
centers (or of the point and the center), a few $u^2$ times it plus twice the smallest normal
number, and $G$ a gap of `T` at the larger of the radii and that distance, about $2u$ times it. The
band is dominated by $G$ unless the radius is small against the distance; neither $e$ nor the band
is claimed, and nothing is said of an answer not given.

The signs of a ball of two limbs are exact although its other predicates are not: $c - r > 0$ is
$r < c$, a comparison of a limb with a number of two limbs, which is exact
([`lt_1_2`](lt_1_2.md)). The *yes* of `equal` of two balls of two limbs, both balls the same point,
is decided exactly by its kernel, but no claim says so: like every answer of that kernel, it is
only certain.

## Three-valued answers

The comparisons answer about every choice of members: `less(X, Y)` is *yes* when every member of
$X$ is below every member of $Y$, *no* when none is, and *unknown* otherwise. The answer is a
`kairn::Trit`:

```cpp
enum class Trit : signed char { no = -1, unknown = 0, yes = 1 };
```

| | yes | no |
|---|---|---|
| `less(X, Y)` | $x_u < y_\ell$ | $x_\ell \ge y_u$ |
| `less_equal(X, Y)` | $x_u \le y_\ell$ | $x_\ell > y_u$ |
| `equal(X, Y)` | $x_\ell = x_u = y_\ell = y_u$: both the same point | $x_u < y_\ell$ or $y_u < x_\ell$: disjoint |
| `greater`, `greater_equal` | those of $(Y, X)$ | |
| `not_equal(X, Y)` | the *no* of `equal` | the *yes* of `equal` |

For a ball the bounds are $c \mp r$. With an operand that is the empty set or the whole line the
answer is *unknown*: a query about nothing answers neither, and the whole line has members on both
sides of everything. `member(t, X)` answers *no* for the empty set, which has no member.

A `Trit` does not convert to `bool`, so a comparison cannot be read as a `bool` by mistake:
`if (kairn::less(x, y))` and `bool b = kairn::less(x, y);` do not compile (`api.reject.enclosure.*`).
A program says which answer it acts on:

| Write | Means |
|---|---|
| `kairn::certainly(less(x, y))` | the answer is *yes*: every member of $X$ is below every member of $Y$ |
| `kairn::possibly(less(x, y))` | the answer is not *no*: some member of $X$ may be below some member of $Y$ |
| `less(x, y) == kairn::Trit::unknown`, or a `switch` | the three cases apart |

Intervals and balls have **no comparison operators**: `x < y` and `x == y` do not compile. An
operator that returns a `Trit` would still be read as a `bool` by every reader of `x < y`, and
`==` of two sets has two meanings that Kairn keeps apart: `equal(X, Y)`, the three-valued equality
of members, and `ieee1788::equal(X, Y)`, the equality of the sets. That is the smallest honest set:
six functions with the names of the design page, `certainly` and `possibly`, and the enumerators.
A `static_cast<bool>` of a `Trit` compiles, as for every scoped enumeration, and is true for *no*
as for *yes*: it is never the question a program means.

## The empty set and the whole line

The empty set is stored as $(+\infty, -\infty)$ in an interval and as NaN limbs in a ball; the
whole line as $[-\infty, +\infty]$ and as center 0 with radius $+\infty$
([The empty set and the whole line](../developer/design/milestone2.md#the-empty-set-and-the-whole-line)).
Members are real numbers: $\pm\infty$ is a bound, never a member.

| Function | On the empty set | On the whole line |
|---|---|---|
| `lower()`, `upper()`, `lower_as`, `upper_as` | $+\infty$, $-\infty$ | $-\infty$, $+\infty$ |
| `midpoint()` | a NaN (every limb) | $0$ |
| `radius()` | a NaN | $+\infty$ |
| `is_empty()`, `is_whole()` | true, false | false, true |
| `contains(t)` | false | true for a finite $t$; false for $\pm\infty$ and a NaN |
| `member(t, X)` | no | yes for a finite $t$; no otherwise |
| `X.contains(Y)` | true exactly when $Y$ is empty | true |
| `Y.contains(X)` for this $X$ | true | true exactly when $Y$ is the whole line |
| `certainly_positive()`, `certainly_negative()`, `certainly_zero()` | false | false |
| the three-valued comparisons | unknown | unknown |
| `hull(Y)` | $Y$ (for a ball, $Y$ as it is) | the whole line |
| `intersection(Y)` | the empty set | $Y$ (for a ball, $Y$ as it is) |
| `split()` | the empty set, twice | `Interval`: $[-\infty, p]$ and $[p, +\infty]$; `Ball`: the whole line, twice |
| the conversion to the other type | the empty set | the whole line |

For a half-line $[\ell, +\infty]$, which only an interval can be, `midpoint()` is $\Omega$ for
every finite $\ell$, `radius()` is $+\infty$, and the conversion to a ball is the whole line. A
finite bound of two limbs can exceed $\Omega$, by less than half a gap of `T` (the pair
$(\Omega, \mathrm{ulp}(\Omega)/4)$, for example): then the midpoint $\Omega$ is not a member of the
half-line, which is what [`interval_mid_rad_2`](interval_mid_rad_2.md) claims, and `split()` splits
it at $\ell$ itself.
`certainly_positive()` is false on the empty set although "every member is positive" is vacuously
true of it: a query about nothing answers no, and `is_empty()` is the query to make first. The
relations of IEEE 1788 keep the standard's vacuous readings instead ([below](#ieee-1788)).

## Split, and a test of progress

`X.split()` returns two sets, `left` and `right`. What is claimed is less than "the two halves":

- **An interval** is split into two nonempty intervals that together are $X$ and meet at a point
  $p$ of $X$: `left` is $[x_\ell, p]$ and `right` is $[p, x_u]$
  ([`splits`](../developer/architecture.md#claims-of-the-interval-kernels-two-limbs-and-the-enclosure-interface)).
  Which point $p$ is, is not claimed. The kernels split at the midpoint of `mid_rad()`, which for
  two limbs is first moved into $X$ (a bound of two limbs can lie beyond $\Omega$), but no claim
  says so, and $p$ can be a bound: $[a, b]$ with $b$ the number of `T` after $a$ is split into
  itself and a point.
- **A ball** is split into two balls of which `left` contains $[c - r, c]$ and `right`
  $[c, c + r]$, so that together they cover $X$. They are not claimed to be inside $X$, nor to be
  smaller than $X$: each is a sum of balls, with its own error bound, and when the radius is near
  $u\lvert c\rvert$ (for two limbs $u^2\lvert c\rvert$) or the smallest normal number, the parts
  can be as wide as $X$. The whole line splits into the whole line twice.

A bisection therefore needs a test of progress of its own: stop refining a set whose parts are
not clearly smaller, for example when a part has more than three quarters of its radius. "Smaller"
alone is not enough for balls: near the limit the parts of a split are smaller than the ball by a
little only, both are kept, and the work doubles at each step for nothing (the first version of
the tutorial's program, with `part.radius() < x.radius()`, did not end). The
[tutorial](../tutorials/bisection.md) shows the test, and where each type reaches it.

## The hull and the intersection of balls

The hull converts both balls to intervals, takes the hull of the intervals and converts that back;
the intersection the same with the intersection
([`ball_set`](../developer/architecture.md#claims-of-the-enclosure-interface-the-set-operations-of-a-ball)).
Each result contains what it must (every member of either operand, or of both), and is not claimed
to be the smallest such ball; the intersection is not claimed to be inside either operand (the two
outward conversions can make it stick out by a rounding), nor empty whenever the balls are
disjoint. When an operand is special the other is returned **as it is**, its limbs themselves, the
sign of a zero included, in this conditional form: for the hull, $Y$ when $X$ is empty, and $X$
when $Y$ is empty and $X$ is not; for the intersection, $Y$ when $X$ is the whole line, and $X$
when $Y$ is the whole line and $X$ is not. When both are special the result is one of them, $Y$:
two empty balls can differ in their NaNs and two whole lines in the sign of the zero of their
centers, so no result could be both as they are.

## Compositions

Two functions compose two proved kernels in the header, each argued and not machine-checked as one
statement:

- `X.contains(t)` and `member(t, X)` with a point `t` of `T` and two limbs (an interval or a ball):
  `make_2` makes `t` a number of two limbs, which its claim says is `t` exactly (or $(\pm\infty, 0)$,
  (NaN, NaN)), and the kernel of two limbs answers for that number; so the answer is about `t`.
  The constructors of two limbs from a `T` compose the same way
  ([What holds today](../getting-started/guarantees.md#intervals)).
- `greater`, `greater_equal` and `not_equal` exchange the operands or the answers of one kernel,
  which composes nothing.

No function of this page writes arithmetic of its own: moves, selects on masks (a `Trit` from the
two masks of a kernel, or from one exact mask) and nothing else.

## IEEE 1788

Kairn's intervals are modeled on the set-based intervals of IEEE Std 1788.1-2017 and are not a
conforming implementation: the standard requires decorations, exceptions, text input and output
and functions Kairn does not have, and its one interval type has bounds of `binary64`
([IEEE 1788](../developer/design/milestone2.md#ieee-1788)). What follows the standard:

- the empty set and its bounds, $(+\infty, -\infty)$; members are real numbers, infinities are
  bounds;
- an operation on an empty operand is empty; $[0, 0] \cdot X = [0, 0]$ for nonempty $X$, unbounded
  included;
- the hull and the intersection, exact, with the empty set the other operand and the empty set;
- `mid` and `rad`: on the special intervals the same values (0 and $+\infty$ for the whole line,
  $\pm\Omega$ and $+\infty$ for a half-line, NaN for the empty set); the radius of one limb the
  smallest for Kairn's midpoint;
- the predicates `isEmpty` and `isEntire`, which are `is_empty()` and `is_whole()` here (the name
  of `Ball::is_whole()`, public since Milestone 1, in version 0.0.0, for both types);
- the four relations of IEEE Std 1788.1-2017, under the standard's names in the namespace
  `kairn::ieee1788`, each returning a `bool` with the standard's readings of the empty set (it is a
  subset of every interval, interior to every interval, disjoint from every interval, and equal to
  the empty set only), exact, compared entry by entry with Tables 4.5 and 4.6 of the standard:

| Relation | On the stored bounds | Kernel |
|---|---|---|
| `ieee1788::equal(X, Y)` | $x_\ell = y_\ell$ and $x_u = y_u$ | [`interval_rel_equal_k`](interval_rel_equal_1.md) |
| `ieee1788::subset(X, Y)` | $y_\ell \le x_\ell$ and $x_u \le y_u$: also `Y.contains(X)` | [`interval_subset_k`](interval_subset_1.md) |
| `ieee1788::interior(X, Y)` | $X$ empty, or ($y_\ell < x_\ell$ or both $-\infty$) and ($x_u < y_u$ or both $+\infty$) | [`interval_rel_interior_k`](interval_rel_interior_1.md) |
| `ieee1788::disjoint(X, Y)` | an operand empty, or $x_u < y_\ell$, or $y_u < x_\ell$ | [`interval_rel_disjoint_k`](interval_rel_disjoint_1.md) |

They live in a namespace of their own because two names are also those of Kairn's three-valued
comparisons, which answer another question: `kairn::equal(X, Y)` is *yes* when both are the same
point, `kairn::ieee1788::equal(X, Y)` true when they have the same members. An unqualified
`equal(x, y)` finds `kairn::equal`. Balls have none of the four: `contains`, the three-valued
comparisons and the conversion to an interval answer for them.

**Where Kairn departs, on purpose, in four points.** A NaN bound given to the constructor gives the
whole line, where the standard returns the empty set and signals; the same infinity given as both
bounds, $[+\infty, +\infty]$ or $[-\infty, -\infty]$, and so the interval of an infinite point, gives
the whole line, where the standard returns the empty set (Kairn reads a value that is not finite as
something that failed or overflowed upstream, and the empty set would discard it); the sign of a
zero bound is not specified, where the standard returns $-0$ for a zero lower bound and $+0$
otherwise; and a product of one limb in the underflow range (products of bounds below
$2^{2p-1}\eta$, $2^{-969}$ for `double`) is *accurate* in the standard's sense, the tightest result
widened by at most one number of `T` on each side, where the standard asks for the tightest. For a
bounded interval of one limb with a bound that is an odd multiple of $\eta$, the midpoint need not
be the midpoint rounded to nearest, which `mid` asks for: it is within $\eta$ and one rounding of
the midpoint.

**Not provided.** Decorations, the "not an interval" value, exceptions; text input and output;
`wid`, `mag`, `mig`, the cancellative operations, division, the square root and the other required
functions; the relations `less`, `precedes`, `strict_less` and `strict_precedes` of the full
standard, IEEE Std 1788-2015, which the simplified one does not require (their definitions were to
be checked against the test cases of ITF1788 first, which are not in the repository). Intervals of
two limbs and of `float` are not types of the standard: for them the standard gives the special
values and the conventions, not the bounds.

## Checks of a debug build

With `KAIRN_CHECKS` 1, each function checks the environment and then its operands as every
operation does ([Getting started](../getting-started/index.md#when-a-check-of-a-build-without-ndebug-fails)).
Those that do not round do not check the rounding mode: every function of an interval in this
page but the midpoint, the radius, the split and the conversions (comparisons and selects), and of
a ball the signs. The others round and check it: the member and subset tests and the comparisons of
balls (exact pairs by `two_sum_ord`, bounds by `add_ball_2_2`), the hull, the intersection and the
split of balls, the midpoint, radius, split and conversions of intervals, and the ball from an
interval of two `T`. The states of a ball (`is_empty`, `is_whole`) and `mid_rad()` of a ball, which
read stored values, check nothing.

## Constant evaluation

`constexpr`: every function of this page on intervals of one and two limbs but the midpoint, the
radius, `mid_rad()` and the conversions of two limbs (the split of two limbs is `constexpr`); on
balls of one limb every function but the split; on balls of two limbs `lower_as`, `upper_as`,
`midpoint()`, `mid_rad()`, the signs, the states and `from_interval`, and the narrowing
`Ball<T, 1>(X)` of a ball of two limbs. The others compute with fused operations that have no
variant for constant evaluation (`add_ball_2_2`, the sums of balls). On the empty set and the
whole line the listings of balls compute a NaN or $\infty - \infty$ before the selects that
return their result, and so do the midpoint, the radius and the split of the empty interval,
which GCC and Clang refuse in constant evaluation: those calls are not constant expressions,
though they are evaluated as stated at run time (`api.constexpr` checks them at run time).

## What is tested

- `api.oracle.K.F` for each of the 53 kernels of the interface: every public form above, judged by
  the oracle against the kernel's claims on 2 000 random cases of `binary64` and `binary32` in the
  quick tier and 10 000 in the full tier, the empty set, the whole line, half-lines, infinite and
  NaN points among them; a `Trit` as the two masks of its kernel, and `member` on a kernel of one
  exact mask never *unknown* ([Testing](../developer/testing.md#the-quick-tier)).
- `api.constexpr`: every `constexpr` function against values computed by hand, and the others at
  run time; the types, which exist exactly when their kernel is proved, take sets of one type only,
  and have no comparison operators.
- `api.reject.enclosure.*`: what must not compile (a `Trit` as a `bool`, a comparison operator,
  sets of two types or numbers of limbs, a point converted to a set), each with its control.
- `api.checks.*`, `api.boundary.*`, `api.shadow`: the checks of a debug build, a product the
  program passes in as a point or as bounds, and the names of the headers.
