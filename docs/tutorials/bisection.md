# Zeros of a polynomial by bisection

This tutorial finds the real zeros of a polynomial in an interval with one algorithm, written once,
and runs it on three types: `Interval<double, 1>`, `Ball<double, 1>` and `Ball<double, 2>`. It
shows the interface the two kinds of set share
([One enclosure interface](../reference/enclosure.md)), what `split()` promises and what it does
not, and why a bisection needs a test of progress of its own. It is for a reader who has met
intervals or balls before; [The range of a polynomial](intervals.md) is the first step. Every
fragment below is part of one program,
[`docs/examples/cpp/bisection.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/bisection.cpp),
and every result shown is what it prints: ctest builds and runs it on every platform of the CI,
under each contraction setting of the compiler, and compares its output with the text shown
[at the end](#the-whole-output) (`api.example.bisection`).

## The idea

An enclosure of $p$ over a set $X$ contains $p(x)$ for every $x$ in $X$. If that enclosure is
certainly positive, or certainly negative, then $p$ has no zero in $X$, and $X$ can be dropped.
Otherwise $X$ may hold a zero: split it and look at each part. What is left at the end is a list
of small sets outside of which $p$ has no zero. Nothing in this says that each set kept holds a
zero: it says that every zero is in one of them.

## Evaluation

$p$ is evaluated by Horner's rule, on any set type `X`. A coefficient is a number of the program,
which no operation of Kairn takes as an operand of a set: it is written as the set of one point,
`X(c[i])`.

```cpp
--8<-- "docs/examples/cpp/bisection.cpp:evaluate"
```

Each operation returns a set that contains every result on members of its operands, so `evaluate`
returns a set that contains $p(x)$ for every $x$ in `x`, for an interval and for a ball alike.

## The bisection

```cpp
--8<-- "docs/examples/cpp/bisection.cpp:bisect"
```

Three functions of the shared interface do the work:

- **`y.certainly_positive()`** and **`y.certainly_negative()`**: whether every member of `y` is
  positive (negative). They are exact for every type here: for a ball of two limbs too, since
  $c - r > 0$ is the comparison $r < c$ of a limb with a number of two limbs. False for the empty
  set and the whole line, so that such a part is never dropped by mistake.
- **`x.radius()`**: for an interval, the smallest number of `double` that, with the interval's
  midpoint, covers it; for a ball, its radius. The width test is `x.radius() <= width`.
- **`x.split()`**: two sets, `left` and `right`, that together cover `x`. For an interval they meet
  at a point of `x`; for a ball, `left` covers $[c - r, c]$ and `right` $[c, c + r]$.

What `split()` does **not** promise is that the parts are smaller. For an interval the point at
which it splits is only claimed to be a point of the interval, and for the interval $[a, b]$ with
$b$ the number of `double` after $a$ it is a bound: the parts are a point and the interval itself.
For a ball each part is a sum of balls, with its own error bound, and once the radius is near
$u\lvert c\rvert$ ($u = 2^{-53}$; for two limbs $u^2\lvert c\rvert$) the parts are about as wide as
the ball. A bisection that splits until the width test holds would then split forever, or, with
parts only slightly smaller and both kept, double its work at every step. The test of progress,
that each part have at most three quarters of the radius of `x`, stops it there: such a set is kept
as it is, and counted.

## The zeros found

The sets kept are in order, left to right, and adjacent ones overlap. They are joined into one set
per zero with two more functions of the interface:

```cpp
--8<-- "docs/examples/cpp/bisection.cpp:clusters"
```

`kairn::equal(a, b)` is a three-valued answer, a `kairn::Trit`: *yes* when both sets are the same
point, *no* when they are disjoint, *unknown* otherwise. It does not convert to `bool`;
`kairn::possibly(t)` is "not *no*", here "the two sets may share a point". `a.hull(b)` covers both
(for intervals the smallest such interval, for balls a ball that contains both).

The polynomial is $p(x) = x^4 - 10x^2 + 1$, whose zeros are the four numbers $\pm\sqrt2 \pm\sqrt3$,
about $\pm 0.3178$ and $\pm 3.1463$, searched in $[-4, 4]$:

```cpp
--8<-- "docs/examples/cpp/bisection.cpp:run"
```

```cpp
--8<-- "docs/examples/cpp/bisection.cpp:main"
```

The domain is made from its two bounds, in `run`, with the one spelling that both kinds of set
have: `X::from_bounds(lo, hi)` is the interval $[lo, hi]$ for an interval, and for a ball a ball
that contains it, here center 0 and radius 4 exactly. `X(lo, hi)` would not do: it is the interval
$[-4, 4]$ for an interval, but for a ball the ball of center $-4$ and radius 4
([One enclosure interface](../reference/enclosure.md#the-interface)). The only lines that name a
type are the three calls of `run`.

## Down to a width of $10^{-6}$

```text
--8<-- "docs/examples/cpp/bisection.txt::15"
```

The three types find the same four zeros with about as many evaluations, and the parts kept have
the radius of the domain halved 22 times, $4 \cdot 2^{-22} \approx 9.5 \times 10^{-7}$. The
balls need a few more evaluations than the interval: a product of wide balls covers more than the
product of the intervals it stands for, so a few more parts are undecided near the start.

## As far as each type can go

With a width of 0 only the test of progress stops the bisection: each type refines as far as its
own arithmetic decides.

```text
--8<-- "docs/examples/cpp/bisection.txt:16:30"
```

- **`Interval<double, 1>`** stops at the precision of `double`: a zero near $3.15$ is left in a set
  of radius $4.4 \times 10^{-16}$, a few numbers of `double` wide, because there each split leaves a
  part that is the interval itself, or $p$ evaluated on a part is no longer of one sign.
- **`Ball<double, 1>`** stops a little wider, $2.7 \times 10^{-15}$: the center of each part is
  rounded to `double`, and its radius covers that rounding, so the parts stop shrinking once the
  radius is a few units of $u\lvert c\rvert$.
- **`Ball<double, 2>`** goes on to a radius of $10^{-30}$, about 30 digits: its center has two
  limbs, so the same limit is at $u^2\lvert c\rvert$. It takes twice the evaluations of the others,
  the price of the 50 more halvings per zero.

Each run counts the sets kept because `split()` could not narrow them: with a width of $10^{-6}$
none, with a width of 0 every one. Without the test of progress the program would not end.

## What to take from it

- Code written with the shared interface runs on every enclosure type; choose the type per
  problem: intervals for wide sets and unbounded ones, balls of two limbs where the answer is
  wanted to more digits than `double` has
  ([Intervals and balls](../getting-started/index.md#intervals-and-balls)).
- `certainly_positive()` and `certainly_negative()` are the safe way to discard: they never say yes
  wrongly. For a ball of two limbs the comparisons (`less`, `equal`, `contains`) are only *certain*:
  an answer given is right, and an answer may not be given near the boundary
  ([What is exact, what is certain](../reference/enclosure.md#what-is-exact-what-is-certain-what-is-not-claimed)).
- `split()` covers the set; it is not claimed to halve it. Test the progress yourself.

## The whole output

```text
--8<-- "docs/examples/cpp/bisection.txt"
```
