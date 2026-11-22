# Intervals, balls and ball vectors: which to use

A number of two limbs has a small error, but a program that holds one does not know how large.
When the program needs to know, it computes with *sets* of real numbers instead, each of which
contains the exact result of the computation that made it: then the size of the set is a bound on
the error, known without knowing the answer. Kairn has three such sets, called *enclosures* here:

- **`Interval<T, k>`**, two bounds, each a number of $k$ limbs of type `T`: the reals between them.
- **`Ball<T, k>`**, a center of $k$ limbs and a radius of type `T`: the reals within the radius of
  the center.
- **`BallVector<T, k, N>`**, $N$ centers and one radius: the vectors of $N$ reals each of whose
  entries is within the radius of its center.

This page says what each stores, what it guarantees, what it costs, and when to use which.

## One sum, four ways

The set of the one number 1, plus the set of the one number $2^{-60}$:

```cpp
--8<-- "docs/examples/cpp/concepts_enclosures.cpp:sum"
```

```text
--8<-- "docs/examples/cpp/concepts_enclosures.txt::5"
```

All four contain $1 + 2^{-60}$, and they get there in two different ways:

- **An interval rounds each bound outward.** With one limb, the exact sum $1 + 2^{-60}$ is not a
  `double`, so the lower bound is it rounded down, 1, and the upper bound it rounded up, the next
  `double`, $1 + 2^{-52}$: the tightest interval of `double` that contains the sum
  ([`interval_add_1`](../reference/interval_add_1.md)). With two limbs, each bound is the sum of two
  limbs rounded to nearest, moved outward by a bound of its own error, so even an exact sum gives an
  interval of positive width ([`interval_add_2`](../reference/interval_add_2.md)).
- **A ball rounds its center to nearest and lets the radius absorb the error.** With one limb the
  center is $\mathrm{RN}(1 + 2^{-60}) = 1$, and the radius, just above $2^{-53}$, covers the radii of
  the operands and the proved bound of that rounding, about $u\lvert c\rvert$; with two limbs the center is
  $1 + 2^{-60}$ itself, and the radius, about $3u^2 = 3 \cdot 2^{-106}$, covers the bound of the
  two-limb sum, which the operation adds whether or not the sum was exact
  ([`ball_add_1_full`](../reference/ball_add_1_full.md), [`ball_add_2_full`](../reference/ball_add_2_full.md)).

The program is
[`docs/examples/cpp/concepts_enclosures.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_enclosures.cpp)
(ctest: `api.example.concepts_enclosures`).

## What each stores and guarantees

The guarantee every arithmetic operation of the three types shares is **containment**: for every
member $x$ of the first operand and $y$ of the second, $x \circ y$ is a member of the result. It is
proved for each of them, in a model of IEEE 754 where values overflow and can be infinite or NaN,
for every canonical operand, the special sets included ([What "correct" means here](correctness.md)).
Beyond it the three differ:

| | `Interval<T, k>` | `Ball<T, k>` | `BallVector<T, k, N>` |
|---|---|---|---|
| Stores | two bounds of $k$ limbs | a center of $k$ limbs, a radius of `T` | $N$ centers of $k$ limbs, one radius of `T` |
| Can be | $[\ell, h]$, a half-line such as $[0, +\infty]$, the whole line, the empty set | a finite ball, the whole line, the empty set | a finite ball vector, the whole space; no empty set |
| How close a sum or product is to the exact range | one limb: the bounds of the exact range rounded outward (a product in the underflow range: at most one number of `T` further); two limbs: each bound within about $8u^2$ (sums) or $10u^2$ (products) of the exact bound, relative to it, plus about $2^{-1021}$ for `double` | the radius covers the operands' radii and the bound of the center's rounding, as its reference page lists; how much wider than the exact range the ball is, is not claimed | the centers as a ball's, entry by entry; one radius, as wide as the widest entry needs; how much wider, not claimed |
| When a bounded result is claimed | one limb: exactly when the exact range is within $\Omega$; two limbs: when it is within a quarter of the overflow threshold | when no member of the exact result exceeds a quarter of the overflow threshold (a sixteenth for the product of balls of one limb) | under conditions each operation states, a quarter of the threshold on its entries and radii |
| Sources | [What holds today, Intervals](../getting-started/guarantees.md#intervals) | [Overflow and non-finite values](../getting-started/guarantees.md#overflow-and-non-finite-values) | [Ball vectors](../reference/ball_vector.md) |

$\Omega$ is the largest finite number of `T`; the overflow threshold is $2^{1024}$ for `double` and
$2^{128}$ for `float`.

Neither an interval nor a ball removes the *dependency problem*: in an expression where a variable
appears twice, such as $x(1 - x)$, each occurrence is treated as if it could take its own value in
the set, and the result can be much wider than the exact range. Rewriting the expression and
splitting the set are the remedies; [The range of a polynomial](../tutorials/intervals.md) shows
both.

## What is exact, what is certain, what is not claimed

Beyond the arithmetic, both types answer the same questions (below), and how far each answer can be
trusted depends on the type and the number of limbs. The [interface's reference
page](../reference/enclosure.md#what-is-exact-what-is-certain-what-is-not-claimed) has the full
table; in short:

- **Exact** means the answer is the truth about the members, for every canonical operand.
  Everything an interval answers is exact: its predicates (`is_empty`, the signs), its member and
  subset tests (`contains`), its three-valued comparisons (`less`, `less_equal`, `equal`), the
  relations of IEEE 1788, its hull and its intersection.
- **A ball of one limb** answers its predicates and its member and subset tests exactly, and its
  comparisons exactly when the sum of the two radii is at most $\Omega$ (beyond, they can answer
  *unknown* where the answer is known, never a wrong answer).
- **A ball of two limbs** is exact only in its signs (`certainly_positive()` and the others). Its
  member and subset tests and its comparisons are **certain**: an answer given is right, and near
  the boundary an answer may not be given (a `bool` false, a `Trit` *unknown*), within a band that
  is measured, not claimed.
- **Not claimed**: that `split()` splits at the midpoint (only that the two parts meet at a point of
  the interval, or cover the ball); that a ball's hull or intersection is the smallest ball that
  contains what it must; the tightest interval of a product of one limb in the underflow range, or of
  any operation of two limbs; the sign of a zero bound.

The three-valued comparisons return a `kairn::Trit`, *yes*, *no* or *unknown*, which converts to no
`bool`: a program writes `kairn::certainly(less(x, y))` or `kairn::possibly(...)`, and the sets have
no comparison operators ([Three-valued answers](../reference/enclosure.md#three-valued-answers)).

## What they cost, and how wide they are

Measured in [Benchmarks, Milestone 2](../developer/results/bench-milestone2.md#in-short), on an Apple M3
(Apple clang 21, GCC 16) and an AMD Zen 2 (GCC 13, Clang 18), in loops of independent operations:

| | Sum | Product | A polynomial of degree 8 by Horner's rule |
|---|---|---|---|
| `Interval<double, 1>` over `Ball<double, 1>` | 2.3 to 3.2 times | 5.6 to 10 times | 2.4 to 6.6 times |
| `Interval<double, 2>` over `Ball<double, 2>` | 3.5 to 6.3 times | 18 to 31 times | 5.8 to 8.1 times |

In a chain of dependent operations the gaps are smaller: an interval of one limb took 1.4 to 2.1
times a ball for a sum and 1.8 to 2.4 times for a product, one of two limbs 2.0 to 2.8 and 7.0 to 10.6
times ([question 2](../developer/results/bench-milestone2.md#2-intervalt-1),
[question 3](../developer/results/bench-milestone2.md#3-intervalt-2)). A ball of two limbs costs
about what its center costs: in a chain a sum of balls took 0.93 to 1.04 times the sum of their
centers, in a loop 1.12 to 1.36 times, and a product 1.23 to 2.58 times in a loop
([Benchmarks, Milestone 1](../developer/results/bench-milestone1.md#3-the-cost-of-a-ball-operation));
the Horner evaluation on `Ball<double, 2>` took 1.06 to 1.34 times the same on
`Expansion<double, 2>` ([question 4](../developer/results/bench-milestone2.md#4-a-polynomial-cost-and-tightness)).
An interval's bound costs more than the operation it rounds because Kairn never changes the
rounding mode: it computes each directed rounding under rounding to nearest, a sum rounded down in
about fifteen operations
([question 1](../developer/results/bench-milestone2.md#1-rounding-down-and-up-without-a-rounding-mode),
which compares it with changing the mode).

What the interval gives back in width is small. In the same measurement, on the degree-8
polynomial ([question 4](../developer/results/bench-milestone2.md#4-a-polynomial-cost-and-tightness),
the table "Tightness"), on arguments wider than a few units in their last place the width was set by
the dependency problem and the types agreed: on narrow sets all four enclosures were 8.6 times the
exact range at the median, and on wide sets the intervals 9.4 times and the balls 10.5 times. Only at
a point did a ball of one limb come out wider than an interval of one limb, 3.3 times at the median
($3.5 \times 10^{-14}$ of $\lvert p(x)\rvert$ against $1.0 \times 10^{-14}$), and 19% wider within a
few units of the last place; with two limbs the two were as tight. A product of *wide* balls covers
more than the product of the intervals they stand for, which this example shows with an algorithm
written once for both.

## One algorithm, any enclosure

`Interval` and `Ball` answer the same questions under the same names: `lower()`, `upper()`,
`lower_as<T>()`, `upper_as<T>()`, `midpoint()`, `radius()`, `mid_rad()`, `is_empty()`, `is_whole()`,
`contains(t)`, `contains(Y)`, `certainly_positive()`, `certainly_negative()`, `certainly_zero()`,
`hull`, `intersection`, `split`, and `kairn::less`, `less_equal`, `equal` and their mirrors
([One enclosure interface](../reference/enclosure.md)). So an algorithm can be written once as a
template and run on the type that suits the problem:

```cpp
--8<-- "docs/examples/cpp/concepts_enclosures.cpp:generic"
```

```text
--8<-- "docs/examples/cpp/concepts_enclosures.txt:7:14"
```

On $[0.25, 0.75]$ the exact range of $x(1 - x)$ is $[0.1875, 0.25]$. The interval product
$[0.25, 0.75] \cdot [0.25, 0.75]$ gives $[0.0625, 0.5625]$, positive; the ball of center $0.5$ and
radius $0.25$, times itself, has a radius of $0.5 \cdot 0.25 + 0.5 \cdot 0.25 + 0.25^2 = 0.3125$
around $0.25$, and reaches below zero. On the narrow set $[0.49, 0.51]$ all three are positive.
Each set is made from two numbers of the program per type, `Interval(lo, hi)` and
`Ball::from_interval(lo, hi)`; [Zeros of a polynomial by bisection](../tutorials/bisection.md) is a
longer algorithm written this way.

## One radius for many centers

A `BallVector` keeps one radius for all its entries. Each operation computes the $N$ centers with one
kernel per entry and the radius once, from the largest magnitude among the entries, so the radius is
as wide as the widest entry needs, and the narrower entries get it too:

```cpp
--8<-- "docs/examples/cpp/concepts_enclosures.cpp:vector"
```

```text
--8<-- "docs/examples/cpp/concepts_enclosures.txt:16:20"
```

The entry 1 would have a radius of about $2^{-53}$ as a ball of its own; in the ball vector it has
the radius of the entry $10^6$, about $2^{-33}$. That the one radius of a sum, a difference or a
scaling equals the largest of the radii the entrywise `Ball` operations give is what the loops
compute and what the tests find in every case they compare, and it is not claimed: what is claimed
is containment, when the result is finite, and that halving or scaling by a power of two is exact
when nothing underflows ([Ball vectors](../reference/ball_vector.md#the-operations)). What a
`BallVector` costs next to $N$ balls has not been measured yet: the benchmarks of the functions on
arrays, the ball vectors and the accumulator are still to come
([Benchmarks, Milestone 2](../developer/results/bench-milestone2.md#still-to-come)). What is measured is
compile time: `kairn/ball_vector.hpp`, not included by `kairn/kairn.hpp`, adds to a file 0.02 s
(GCC 13) to 0.15 s (Apple clang) beyond `kairn/packed.hpp` and `kairn/soa.hpp`, which it includes
([Compile time](../reference/ball_vector.md#compile-time)).

## Which to use

Each line rests on a statement or a measurement above.

- **If your sets are wide**, such as the domain of a search, or unbounded on one side, use
  **`Interval`**: a ball cannot be a half-line (an unbounded ball is the whole line), and a product of
  wide balls covers more than that of intervals (the example above; on wide sets the intervals were
  9.4 times the exact range and the balls 10.5 times).
- **If you want the tightest bounds of `T`** for each sum and product, use **`Interval<T, 1>`**: its
  bounds are the exact ones rounded outward (in the underflow range a product's bound may be one number
  of `T` further).
- **If your values are known to within small errors**, such as results of a long computation on
  data with rounding errors, use **`Ball`**: an interval costs 2.3 to 31 times as much per operation in
  a loop, and on narrow sets it was no narrower (at a point, with one limb, the interval was the
  narrower one).
- **If you need more digits than `T` has**, use **`Ball<T, 2>`**: an interval of two limbs costs 3.5
  to 6.3 times as much for a sum and 18 to 31 times for a product, and was as tight.
- **If you need exact answers to comparisons with two limbs**, use **`Interval<T, 2>`**: those of a ball
  of two limbs are only certain.
- **If you hold $N$ values whose errors are of the same size**, such as the coefficients of a
  polynomial in the Bernstein basis, a **`BallVector`** computes one radius instead of $N$; if their
  errors differ much in size, hold them as **$N$ `Ball`s**, since every entry of a `BallVector` gets the
  widest radius.
- **If you cannot tell in advance**, write the algorithm once over the shared interface, as above,
  and run it on both.

The [tutorial on ball vectors](../tutorials/ball-vectors.md) subdivides and multiplies polynomials
held as `BallVector`s.
