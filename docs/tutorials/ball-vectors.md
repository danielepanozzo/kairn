# Polynomials as ball vectors

This tutorial holds a polynomial whose coefficients are known to within a radius as a
`kairn::BallVector`: $N$ centers and one radius. It subdivides a polynomial in the Bernstein basis
at $t = \tfrac12$, the step of a branch-and-bound search over $[0, 1]$, bounds the polynomial on
each half, and multiplies two polynomials. It is for a reader who knows what a ball is
([Intervals and balls](../getting-started/index.md#intervals-and-balls)). Every fragment below is
part of one program,
[`docs/examples/cpp/ball_vectors.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/ball_vectors.cpp),
which checks each result against exact arithmetic; ctest builds and runs it under each contraction
setting of the compiler and compares its output with the text shown [at the end](#the-whole-output)
(`api.example.ball_vectors`).

## A polynomial as a ball vector

A polynomial of degree $n$ in the Bernstein basis on $[0, 1]$ is
$p(t) = \sum_i b_i \binom{n}{i} t^i (1 - t)^{n - i}$. Its coefficients come from a computation, and
are known to within some radius $r$: the true coefficients are some $x_i$ with
$\lvert x_i - b_i\rvert \le r$ for every $i$. A `BallVector<double, 1, 5>` is exactly that set:

```cpp
--8<-- "docs/examples/cpp/ball_vectors.cpp:data"
```

`kairn/ball_vector.hpp` is a header of its own, which `kairn/kairn.hpp` does not include. The
constructor takes the centers and the radius, guards each value it is given (a product the program
computed and passes in is rounded before it is used), and makes the whole space, every center zero
and the radius $+\infty$, of a radius that is negative, a NaN or $+\infty$, or of a center that is
not finite: there is no empty ball vector.

## Subdividing at one half

The coefficients of $p$ on $[0, \tfrac12]$ and on $[\tfrac12, 1]$ come from de Casteljau's
triangle: level $j$ is $b^{(j)}_i = \tfrac12\,(b^{(j-1)}_i + b^{(j-1)}_{i+1})$, the left half's
coefficients are $b^{(j)}_0$ and the right half's $b^{(n-j)}_j$. Each level is one sum of two ball
vectors, the level before without its last entry and without its first (two read-only views of
fewer entries, `subview`), and one halving:

```cpp
--8<-- "docs/examples/cpp/ball_vectors.cpp:halves"
```

The levels live in arrays of the program's own; `BallVectorView` sees them, and `kairn::add` and
`kairn::half` write through it, here in place. What each operation guarantees
([Ball vectors](../reference/ball_vector.md)):

- **Containment.** For every member $x$ of the level before, the sums of neighbours are members of
  the sum, entry by entry, and their halves of the half. So the exact triangle of every member of
  $p$ lies in the computed one, and each coefficient of each half in its ball.
- **The halving is exact.** `half(x)` gives centers $c_i / 2$ and the radius $r / 2$ exactly when
  nothing underflows; only the sums add to the radius, for the rounding of their centers.
- **One radius.** A level has one radius for all its entries, as wide as its widest entry needs. A
  half takes one entry of each level, so its radius is the largest of the levels' radii: a ball of a
  larger radius contains the ball of each level.

```cpp
--8<-- "docs/examples/cpp/ball_vectors.cpp:subdivide"
```

prints

```text
level 1: radius 0x1.0000024cccccfp-30
level 2: radius 0x1.000003f333337p-30
level 3: radius 0x1.0000053ccccd3p-30
level 4: radius 0x1.000006266666fp-30
left half:  radius 0x1.000006266666fp-30, |p| <= 0x1.8000000400002p+0 on [0, 1/2]
right half: radius 0x1.000006266666fp-30, |p| <= 0x1.0000000400002p+0 on [1/2, 1]
```

The radius grows from $2^{-30}$ by about $2^{-53}$ per level: the sum of two radii, halved, gives
the radius back, and the rounding of the sums of the centers adds $u = 2^{-53}$ times the largest
of them (2.3 at the first level), halved.

## A bound of the polynomial

On $[0, 1]$, each value of a polynomial in the Bernstein basis is a weighted mean of its
coefficients (the basis functions are nonnegative and sum to one), so
$\lvert p(t)\rvert \le \max_i \lvert x_i\rvert$ for each member. `kairn::norm_upper(x)` bounds
the magnitude of every entry of every member of a ball vector: it is the bound of the centers
(`norm_upper_k`, the largest magnitude, one step up for two limbs) plus the radius, rounded up. On
each half it bounds $\lvert p\rvert$ there, for every member of $p$: a branch-and-bound search
discards a half whose bound shows that it holds no root, or keeps it and subdivides again. This
bound is the composition of two proved calls, made in the header; the inequality from the two
claims to the bound of every member is the header's argument, checked in exact arithmetic by the
tests.

## The product of two polynomials

The coefficients of a product of two polynomials in the monomial basis are the convolution of their
coefficients. `kairn::convolution` of ball vectors of $N$ and $M$ coefficients gives one of
$N + M - 1$:

```cpp
--8<-- "docs/examples/cpp/ball_vectors.cpp:product"
```

prints `f g: 4 coefficients, radius 0x1.1830000000084p-39`. Each coefficient $j$ of the product of
any members $x$ of $f$ and $y$ of $g$, each coefficient of each ranging over its ball independently
of the others, is within the radius of coefficient $j$. The radius is computed once, from the
largest magnitudes of the centers of each operand, $M_f = 3$ and $M_g = 1$, and the number of
terms $m = \min(N, M) = 2$: about $m\,(M_f r_g + M_g r_f + r_f r_g) + \ldots$. For coefficients
of comparable size, as those of a polynomial in the Bernstein basis, that is the right order; for
coefficients that differ much in size it overestimates the coefficients near the small ones, up to
the factor $m$.

The product is finite only under conditions, one of which is on the length: with $n = \min(N, M)$,
$n\,(u + \eta) \le \tfrac1{16}$ for one limb, so about $n \le 2^{49}$ for `double` and $n \le 2^{20}$
for `float`; above, the product is the whole space whatever the values. In the Bernstein basis the
product is the convolution of the coefficients scaled by their binomials, $b_i \binom{n}{i}$, which
this tutorial does not do: the scaling by an integer that is not a power of two rounds, and the
program then owns the radius it adds.

## The check

The program checks every result against exact arithmetic, independent of Kairn: an exact number
$m\,2^e$ with an integer $m$ of any size, enough for every sum and product of doubles. For forty
members of $p$ (each coefficient moved from its center by $-r$, $-r/2$, $0$, $r/2$ or $r$) it
subdivides each exactly and finds every exact coefficient of each half in its ball; for 625 pairs
of members of $f$ and $g$, every exact coefficient of their product in the ball of $f g$; and, as
a control of the check itself, a point at one and a half radii from a center outside.

## When to use a BallVector, and when N balls

- **Cost.** An operation on a `BallVector` of $N$ entries is one kernel per entry, for the centers,
  and a few operations of `T` for the one radius, once. $N$ `Ball`s compute $N$ radii.
- **Tightness.** The one radius of a sum, a difference or a scaling is, in every case the tests
  measured, the largest of the $N$ radii that the entrywise `Ball` operations would give: nothing is
  lost on the widest entry, and the narrower entries get its radius. That equality is what the
  generated loops compute, not a claim; what is claimed is containment and when the result is
  finite. A product's radius uses the largest centers of each operand for every coefficient.
- **Exactness.** `ldexp` and `half` are exact when nothing underflows, so a subdivision that halves
  again and again keeps its radius $r / 2^i$.
- **What it is not.** A `BallVector` is not $N$ independent balls: `entry(i)` is the ball of center
  $i$ and the shared radius, a copy. A polynomial whose coefficients need radii of very different
  sizes, or one with weights, is better held as $N$ balls, or as arrays of centers with a radius
  theorem of the program's own.

## The whole output

```text
--8<-- "docs/examples/cpp/ball_vectors.txt"
```

## What the header does not provide

An empty ball vector; a radius per entry or weights; the product of polynomials in the lane order
or in packed code (it has the sequential order only); constant evaluation of any operation; an
operation of a ball vector with a `Ball` or a number but the scaling. The reference page,
[Ball vectors](../reference/ball_vector.md), says what each operation states.
