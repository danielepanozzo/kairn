# The range of a polynomial

This tutorial encloses the range of a polynomial over an interval, first with intervals, then with
balls. It shows what an enclosure guarantees, why a direct evaluation can be much wider than the
range, and two ways to make it narrower. It is for a reader who knows floating point and has not
used interval arithmetic. Every fragment below is part of one program,
[`docs/examples/cpp/intervals.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/intervals.cpp),
and every result shown is what it prints: ctest builds and runs it on every platform of the CI,
under each contraction setting of the compiler, and compares its output with the text shown
[at the end](#the-whole-output) (`api.example.intervals`). To build your own program, follow
[Getting started](../getting-started/index.md#use-it-from-cmake).

## Intervals

An interval is a set of real numbers given by two bounds. `kairn::Interval<double, 1>` has bounds
of one `double` each, and `kairn::Interval<double, 2>` bounds of two limbs:

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:types"
```

Every operation on intervals returns an interval that contains the exact result for every choice
of members of its operands: if $x \in X$ and $y \in Y$, then $x + y \in X + Y$, and the same for
$-$ and $\times$. This is proved for every operation, in Flocq's model of IEEE 754, for unbounded
and empty operands too ([What holds today](../getting-started/guarantees.md#intervals)). For bounds
of one limb, a sum or a difference is the tightest interval of `double` that contains the exact
range: its bounds are the exact ones rounded outward.

## A polynomial over an interval

Take $p(x) = x^2 - 2x$ on $X = [0, 2]$. Its range is $[-1, 0]$: the minimum is at $x = 1$, and
$p(0) = p(2) = 0$. Here is $p$ written three ways, each a template that works on intervals and on
balls alike:

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:polynomial"
```

A number in an expression is written as the set of one point, `X(2.0)`: no operation of Kairn
takes an interval and a number, so a program says which set the number stands for. Evaluated on
$X$:

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:direct"
```

```text
p(x) = x^2 - 2x on X = [0, 2], whose range is [-1, 0]:
  x*x - 2*x              [-4, 4]
  x*(x - 2)              [-4, 0]
  (x - 1)*(x - 1) - 1    [-2, 0]
```

All three contain $[-1, 0]$, as they must, and none is it. The first is eight times as wide. Each
operation is exact here (the bounds are small integers), so the width is not rounding: it is the
*dependency problem*. In $x \cdot x - 2x$ the variable appears three times, and interval arithmetic
evaluates each occurrence as if it could take its own value in $X$: $x \cdot x$ is $[0, 4]$, which
it is, and $2x$ is $[0, 4]$, which it is, but their difference is computed as $[0 - 4, 4 - 0]$, as
if $x \cdot x$ could be 0 while $2x$ is 4. An enclosure is a guarantee about every member, not
about the members that can occur together.

Rewriting helps when it reduces the occurrences: $(x - 1)^2 - 1$ has $x$ once, but squaring
$[-1, 1]$ as a product of two intervals still gives $[-1, 1]$ and not $[0, 1]$, the product not
knowing that its two operands are one number. Kairn has no square of an interval yet.

## Splitting the interval

The other remedy is to split $X$ into pieces, evaluate on each, and take the hull of the results:

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:pieces"
```

`X.split()` returns two intervals whose union is $X$, split at a point of it (the midpoint, here,
which is exact for these bounds), and `X.hull(Y)` is the smallest interval that contains both;
`Interval::empty()`, the empty set, is the start of the hull. Both are exact.

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:split"
```

```text
The hull over n pieces of X:
  n      x*x - 2*x                      (x - 1)*(x - 1) - 1
  1      [-4, 4]                        [-2, 0]
  2      [-3, 2]                        [-1, 0]
  4      [-2, 1]                        [-1, 0]
  16     [-1.25, 0.25]                  [-1, 0]
  64     [-1.0625, 0.0625]              [-1, 0]
  256    [-1.015625, 0.015625]          [-1, 0]
  1024   [-1.00390625, 0.00390625]      [-1, 0]
```

On pieces of width $h = 2/n$, the first form gives $[-1 - 2h, 2h]$: the excess shrinks in
proportion to $h$, which is what to expect of a direct evaluation, and halving it doubles the
work. The second form is exact from two pieces on, because on each piece $x - 1$ no longer changes
sign, and the product of an interval by itself is then its square. Which form is better depends on
the expression; splitting works for every form, slowly.

## The same with balls

A ball stores a center and a radius. `Ball<double, 1>(X)` converts the interval to the ball that
contains it, center 1 and radius 1 here; `Interval<double, 1>(B)` converts back, to the smallest
interval of `double` that contains the ball. Both conversions are explicit, since each can widen
the set.

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:balls"
```

```text
The same with Ball<double, 1>(X), center 1 and radius 1:
  x*x - 2*x              [-6, 4]
  (x - 1)*(x - 1) - 1    [-2, 2.220446049e-15]
```

The ball has the same dependency problem, and more: the radius of a product of balls covers
$\lvert c_x\rvert r_y + \lvert c_y\rvert r_x + r_x r_y$, which for this wide set is more than the
product of intervals, and every radius is rounded up, which is why the second form ends a little
above 0. For a set that is wide compared with its numbers, as the domain of a search is, intervals
are the better enclosure: they also keep half-lines such as $[0, +\infty]$, which a ball cannot
(an unbounded ball is the whole line).

## Two limbs

With bounds of two limbs, each bound is the result of the operation on two limbs, rounded to
nearest, moved outward by a bound of that operation's own error. It is within about $8u^2$ (sums)
or $10u^2$ (products) of the exact bound, relative to it, with $u = 2^{-53}$, but it is not the
exact bound even when the exact bound is a number of `double`:

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:two_limbs"
```

```text
With Interval<double, 2>, x*x - 2*x is [-4 - 3.45e-31, 4 + 3.45e-31]
```

($8u^2 \cdot 4$ is about $3.9 \times 10^{-31}$.) A bound that is exactly zero is kept, by a rule
of the sums and of the product by $[0, 0]$; others are moved by a few units of $u^2$.

## A narrow set

The other kind of set is a value known to within a small error: the result of a computation on
data with rounding errors, or a constant such as $1/10$, which no `double` is. Here balls of two
limbs are the cheap enclosure: the center carries the value at 106 bits and the radius, a single
`double`, its error.

```cpp
--8<-- "docs/examples/cpp/intervals.cpp:narrow"
```

```text
p(1/10) = -0.19:
  Ball<double, 2>        center -0.19, radius 1.8e-32
  Interval<double, 1>    [-0.19000000000000006, -0.18999999999999997]
```

Both contain $p(1/10) = -0.19$ exactly, which the program checks by subtracting the enclosure of
$-19/100$ from each and finding 0 in the difference. The interval of one limb has the precision of
`double`; the ball of two limbs about 30 digits. An interval of two limbs would be about as
precise, at more than twice the cost: a sum of balls of two limbs is about 23 rounded operations,
a sum of intervals of two limbs about 56
([Bounds of two limbs](../developer/design/milestone2.md#bounds-of-two-limbs)).

## When to use which

- **Intervals** for wide sets, unbounded sets and searches (split, test, discard), and with one
  limb, where each bound is the tightest number of `T`.
- **Balls** for values with small errors, in long computations, and from two limbs on.
- **Neither** removes the dependency problem; rewriting an expression and splitting the set are the
  remedies, for both.

[Getting started](../getting-started/index.md#intervals-and-balls) says the same in more words, and
[What holds today](../getting-started/guarantees.md#intervals) what is proved of each function.

## The whole output

```text
--8<-- "docs/examples/cpp/intervals.txt"
```

## What the headers do not provide yet

The predicates and comparisons of intervals (`is_empty`, `contains`, the signs, the three-valued
comparisons, the relations of IEEE 1788), the midpoint, radius, split and conversions of intervals
of two limbs, and the hull, intersection and split of balls are in Milestone 2 and come next; so
does a square of an interval. Division, square roots and the elementary functions are for later
milestones ([Plan](../developer/design/phase0/plan.md#milestones)).
