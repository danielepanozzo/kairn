# Accurate sums and dot products

This tutorial sums 2001 numbers and computes a dot product of 2001 pairs, in `double`, then with
two-limb numbers, then with balls that come with a guaranteed error bound. It is for a reader who
knows floating point (rounding, the unit roundoff, cancellation) and has not used expansions. Every
fragment below is part of one program,
[`docs/examples/cpp/accurate_sums.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/accurate_sums.cpp),
and every result shown is what it prints: ctest builds and runs it on every platform of the CI,
under each contraction setting of the compiler, and compares its output with the text shown
[at the end](#the-whole-output) (`api.example.accurate_sums`). To build your own program, follow
[Getting started](../getting-started/index.md#use-it-from-cmake).

## A sum that cancels

The data: 1, then a thousand numbers between $2^{-20}$ and $2^{60}$ in magnitude, each with a full
53-bit significand, then the same thousand numbers negated, in another order. The exact sum is 1,
which is what lets the program print its errors.

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:sum_data"
```

How hard a sum is to compute is measured by its *condition number*,
$\kappa = \sum_i \lvert x_i\rvert / \lvert \sum_i x_i\rvert$: how much the sum moves, relative to
itself, when every term moves by a small relative amount. Here $\kappa \approx 6.3 \times 10^{19}$.
Roughly, a sum computed with unit roundoff $u$ has a relative error of the order of $\kappa u$
(more in the worst case, by up to a factor of the number of terms). For `double`,
$u = 2^{-53} \approx 1.1 \times 10^{-16}$, and $\kappa u \approx 7000$: no digit of the result can
be trusted. The plain loop:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:sum_double"
```

returns $-6347.5$ instead of 1.

## Two limbs

`kairn::Expansion<double, 2>` stores a value as the exact sum of two `double`s, its *limbs*:
$t = t_0 + t_1$, with $t_1$ at most half a unit in the last place of $t_0$ (the number is then
*normalized*, and $t_0$ is $t$ rounded to `double`). That is 106 significant bits, about 32 decimal
digits, for values above about $10^{-292}$, and the unit roundoff becomes about
$u^2 \approx 1.2 \times 10^{-32}$.

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:types"
```

Only the type of the accumulator changes:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:sum_two"
```

`t += v` adds a `double` to a two-limb number. Its result is normalized and within
$2u^2\lvert t + v\rvert$ of the exact sum $t + v$, a bound with a machine-checked proof
([`add_2_1_full`](../reference/add_2_1_full.md), whose finite results are those of its core
[`add_2_1`](../reference/add_2_1.md)). The program prints

```text
  Expansion<double, 2>  0.99999999999939948 + 1.3877787807814457e-17 (error -6.0e-13)
```

the two limbs, and the error: 12 correct digits where `double` had none. The rule of thumb predicts
it: $\kappa u^2 \approx 6.3 \times 10^{19} \times 1.2 \times 10^{-32} \approx 8 \times 10^{-13}$.
Two limbs move the limit from condition numbers of about $10^{16}$ to about $10^{32}$; they do not
remove it. (Kairn has no decimal output yet, so the program prints each limb with `%.17g`, and the
error as `to_nearest(t - 1.0)`, the two-limb difference rounded to `double`.)

## A dot product

The second data set is a pair of `float` vectors, as a single-precision source would store them:
the pair $(1, 1)$, a thousand pairs between $2^{-30}$ and $2^{30}$, and the same pairs with the second
number negated, in another order. The exact dot product is 1, and $\kappa \approx 6.7 \times 10^{18}$.

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:dot_data"
```

Accumulating in `double` is common practice for `float` data, and it makes every product exact,
since $24 + 24$ significant bits fit in 53. The additions still cancel:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:dot_double"
```

gives $-730.54$. Because the products are exact, this loop gives the same wrong answer whether or
not the compiler fuses the multiplication and the addition into one FMA, which is why the tutorial
uses `float` data: its output is the same on every compiler. With two limbs:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:dot_two"
```

The error is $5.1 \times 10^{-14}$. `Number(a[i]) * double(b[i])` multiplies a two-limb number by a
`double` ([`mul_2_1_full`](../reference/mul_2_1_full.md)), which keeps the rounding error of the product as
well; with `double` data, whose products are not exact, that is what makes the dot product
accurate. Writing `e += x * y` with two `double` factors instead would round each product to one
`double` before the two-limb addition sees it (and here `a[i] * b[i]`, a product of two `float`s,
would round it to a `float`).

## A guaranteed enclosure

The errors above were printed because the exact answer was known. In general it is not, and a
bound is what one needs. `kairn::Ball<double, 2>` is the set of reals within a radius $r$ of a
center $c$, $\{\, x : \lvert x - c\rvert \le r \,\}$, with a two-limb center and a `double` radius.
Every operation on balls returns a ball that contains every result of the operation on points of its
operands, and that containment is proved for each operation
([`ball_add_2_full`](../reference/ball_add_2_full.md)). A `double` passed to a ball operation is a
ball of radius 0. The sum:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:sum_ball"
```

ends with a center whose error is $-6.0 \times 10^{-13}$, as before, and a radius of
$2.82 \times 10^{-10}$: the ball says that the sum is within $2.82 \times 10^{-10}$ of
$1 - 6.0 \times 10^{-13}$, and it is (the program checks that the ball contains 1). The radius is a
bound, not an estimate: here it is about 470 times the actual error. Unlike the error, it is known
without knowing the answer.

### What the radius is made of

Each addition of balls computes the new center with the two-limb addition
([`add_2_2`](../reference/add_2_2.md)), and the new radius as the sum of

1. the radii of the two operands, which carry what was already uncertain;
2. a bound on the rounding error of the new center: $U\,\lvert c\rvert$, where $c$ is the new center
   and $U$ the proved bound of [`add_2_2`](../reference/add_2_2.md) relative to the computed
   result, rounded up to `double` (`kairn::traits<Expansion<double, 2>>::add.unit_computed`);

and that sum, computed with ordinary operations, is then inflated once, by a factor a few units
of $u$ above 1 and a tiny constant (about $2^{-1022}$, which covers underflow), so that the radius
never comes out too small
([the second radius design](../developer/design/milestone1.md#the-radius-second-design)). Here the
data are exact, the radii start at 0, and the radius is the sum of the second terms, which the
program recomputes by hand:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:radius"
```

```text
    U = 3.698e-32, times the sum of |center| 7.616e+21: 2.82e-10
```

The radius is large because the centers are: before the second half of the data cancels the first,
the running sum is about $4 \times 10^{18}$ on average over the 2001 steps. An order of the terms
that cancels earlier would give a smaller radius.

The first term matters as soon as the data are not exact. If each $x_i$ were known only to within
half a unit in its last place, as a value read from a decimal file would be, the balls would carry
that from the start:

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:uncertain"
```

```text
    with data known to half a unit in the last place: radius 7.01e+03
```

The ball still contains 1, and it says that such data do not determine the sum: a condition number
of $6.3 \times 10^{19}$ multiplies the errors of the data as it multiplies rounding errors. More
limbs reduce rounding errors; they cannot recover what the data do not hold.

The dot product works the same way, with `Ball * double` for the products
([`ball_scale_2_full`](../reference/ball_scale_2_full.md)):

```cpp
--8<-- "docs/examples/cpp/accurate_sums.cpp:dot_ball"
```

Its radius is $5.14 \times 10^{-11}$, for an actual error of $5.1 \times 10^{-14}$.

## The whole output

```text
--8<-- "docs/examples/cpp/accurate_sums.txt"
```

## What it costs

From the [benchmarks of Milestone 1](../developer/results/bench-milestone1.md), on an Apple M3, an
AMD Zen 2 and an Intel Core i5, with nine compiler configurations, timing the operators used here
(each with its check for infinities and NaN, below):

- **Two limbs.** One step of a dependent sum `s = s + a` (`x + a`, the sum loop above) took 3.3
  to 6.6 ns, against 0.29 to 0.79 ns for a `double` addition: 8.2 to 12.6 times longer, per
  configuration. With a two-limb summand, `s = s + x` took 5.1 to 10.4 ns. Loops of independent
  operations cost less per operation, because the processor overlaps them and the compiler can
  vectorize them: 0.89 to 2.9 ns for `x + a`.
- **Balls.** A step of a dependent sum of balls `S = S + X` took 0.93 to 1.04 times as long as the
  same sum of their two-limb centers, and a product of balls 0.97 to 1.14 times as long as the
  product of the centers: in a chain the radius costs almost nothing. In loops of independent
  operations it shows: 1.1 to 1.4 times for a sum, 1.2 to 2.6 times for a product.

These are figures for the second design of the radius, which computes it with ordinary operations
and inflates it once at the end
([Milestone 1 statements](../developer/design/milestone1.md#the-radius-second-design)); with the
first, a product of balls took 3.0 to 4.4 times as long as its center in a chain.

## What can go wrong

In short, below; [Troubleshooting](../getting-started/index.md#troubleshooting) has every message
that Kairn's checks print, with its cause and what to do.

**Compiler flags.** Kairn's results depend on every floating-point operation being done as
written. Including `kairn/kairn.hpp` fails with an `#error` under the flags a compiler announces with
a macro: `-ffast-math` (and `-Ofast`), `-ffinite-math-only`, GCC's `-fassociative-math`,
`-fno-signed-zeros` and `-freciprocal-math`, MSVC's `/fp:fast`, and evaluation in a wider format
(x87). On x86-64 it also needs a target with hardware FMA ("Kairn needs hardware FMA"; link
`kairn::fma`, [Getting started](../getting-started/index.md#hardware-fma)).

**`kairn::self_test()`.** Some flags leave no macro to check: Clang's `-fassociative-math`,
`-fno-signed-zeros` and `-freciprocal-math`, Apple clang's `-ffp-model=fast`. Call
`kairn::self_test()` once at startup, as this program does; it computes known results with the
flags of the file that calls it, runs every kernel on fixed operands, and says what is wrong:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:self_test"
```

It also catches a rounding mode other than to nearest, and subnormal numbers flushed to zero,
which a library compiled with `-ffast-math` can turn on for the whole program.
`kairn::environment_ok()` checks those two later, and a build without `NDEBUG` checks them before
every operation ([The environment](../getting-started/guarantees.md#the-environment)).

**Rounding a product too early.** In `e += a[i] * b[i]` with `double` operands, the product is a
`double`, rounded before Kairn sees it. Make one factor a two-limb number:
`e += Number(a[i]) * b[i]`.

**Overflow.** The bounds above hold whenever the result is finite. When an intermediate result
overflows, a two-limb operation returns $(\pm\infty, 0)$, as `double` would return $\pm\infty$,
never a finite wrong value; an infinite or NaN operand gives what `double` gives on the leading
limbs. A ball that cannot be bounded becomes the whole line, which still contains the exact
result; a ball made with a negative radius is the empty set, and one made with a NaN radius the
whole line. All of this is proved
([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)). It is also
proved when finite operands give a finite ball: when no member of the exact result exceeds a
quarter of the overflow threshold ($2^{1022}$ for `double`; a sixteenth of it for a product of
one-limb balls), the condition B4 on the page of each Ball kernel, such as
[`ball_add_2_full`](../reference/ball_add_2_full.md) and
[`ball_mul_1_full`](../reference/ball_mul_1_full.md). Where results may come nearer to the top of the range than that, test them:
`kairn::isfinite(x)` for a number, `X.is_finite()` for a ball.

## What the headers do not provide yet

This tutorial uses all there is for an accurate sum: numbers of one and two limbs, balls around
them, addition, subtraction and multiplication. Not yet: division and square root, three or more
limbs, decimal input and output (print the limbs, as here), an interval type, and vectors of
balls. The [Plan](../developer/design/phase0/plan.md#milestones) says when each is to come.
