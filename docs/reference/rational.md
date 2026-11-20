# Constants from fractions

`kairn::rational<X>(num, den)` makes the number $q = \mathrm{num}/\mathrm{den}$ of two 64-bit
integers into a number of type `X`, with a bound of the error it made and whether it made none.
It works in constant expressions and at run time and gives the same bits in both, because it does
no floating-point operation. `kairn::integer<X>(n)` is `rational<X>(n, 1)`.
`kairn::is_rational_result(c, num, den)` checks a result against the statement below. They are
in `kairn/rational.hpp`, which `kairn/kairn.hpp` includes.

**Status: specified exactly; tested for equality with an independent oracle; not
machine-checked.** This is integer code written by hand in the header, not a generated kernel:
there is no generated model of it and no Rocq theorem about it, unlike every kernel of the other
reference pages ([What holds today](../getting-started/guarantees.md#constants-from-fractions)).
What stands in for a proof is said [below](#what-is-tested), with what [the check](#the-check)
adds.

```cpp
template <class X> struct Constant { X value; typename traits<X>::limb_type error; bool exact; };
template <class X> constexpr Constant<X> rational(long long num, long long den) noexcept;
template <class X> constexpr Constant<X> integer(long long n) noexcept;
template <class X> constexpr bool is_rational_result(const Constant<X>& c, long long num, long long den) noexcept;
```

`X` is `Expansion<T, 1>`, `Expansion<T, 2>` or `T` itself, with `T` = `float` or `double`; any
other type does not compile.

## What it returns

For `X` of limb type `T` and $k$ limbs, $\mathrm{RN}$ the rounding to nearest of `T`, ties to even,
with gradual underflow, and $\mathrm{den} \ne 0$:

- $k = 1$: `value` $= \mathrm{RN}(q)$.
- $k = 2$: `value` is the normalized pair whose value is $\mathrm{RN}(q) + \mathrm{RN}(q - \mathrm{RN}(q))$.
  There is exactly one: the leading limb of a normalized pair is the rounding of its value.
- `error` is the smallest number of `T` that is at least $\lvert\mathrm{value} - q\rvert$.
- `exact` is true exactly when $\mathrm{value} = q$, that is when `error` is zero.

Every bit of the result is fixed: the limbs, the error and the flag. A zero limb is $+0$.

**Arguments.** Any two values of `long long`, $-2^{63}$ included. Then $q$ is zero or between
$2^{-63}$ and $2^{63}$ in magnitude, so the value never overflows and its leading limb is never
subnormal; the second limb of a `float` pair can be. Consequently
$\lvert\mathrm{value} - q\rvert \le \frac{u}{1+u}\lvert q\rvert$ for one limb and
$\le u^2\lvert q\rvert$ for two, $u = 2^{-p}$, with no term for underflow: where the second limb
of a `float` pair is subnormal, its error is at most $2^{-150}$, and $u^2\lvert q\rvert$ is at least
$2^{-111}$.

**A zero denominator.** In a constant expression the call does not compile; the compiler's
message names `kairn::detail::rational_denominator_is_zero`. At run time the result is the
canonical NaN (every limb a NaN), `error` is $+\infty$ and `exact` is false.

**The rounding mode, and a debug build.** The result does not depend on the rounding mode, on
contraction, or on any flag that `config.hpp` accepts. A build with `KAIRN_CHECKS` does not check
the floating-point environment before `rational`, as it does before every operation that rounds,
so a program may call it under a directed rounding mode.

## Why the second limb is not simply the rounding of the rest

The pair $(\mathrm{RN}(q),\ \mathrm{RN}(q - \mathrm{RN}(q)))$ is not always normalized. When $q$ is
very close to the midpoint of two neighbors in `T`, the rest $q - \mathrm{RN}(q)$ rounds to exactly
half their gap; if $\mathrm{RN}(q)$ has an odd significand, the sum of the two limbs then rounds to
the other neighbor, the even one. The normalized pair of the same value is then
$(\mathrm{RN}(q) + 2b,\ -b)$ with $b$ the rounded rest, and its leading limb is not $\mathrm{RN}(q)$.
With 64-bit terms this happens: for
$q = 760870173599572325 / 1255282706658693927$, $\mathrm{RN}(q)$ is `0x1.365743570964bp-1` for
`double`, the rest rounds to $2^{-54}$, half the gap there, and `rational<Expansion<double, 2>>`
gives `(0x1.365743570964cp-1, -0x1p-54)`. `tests/api/rational.cpp` has this case for `double` and
one for `float`.

## How it is computed

With integers only, in 64-bit words, no `__int128`:

1. $\mathrm{RN}(q)$: $\lvert\mathrm{num}\rvert$ divided by $\lvert\mathrm{den}\rvert$, aligned so that
   the quotient has $p$ bits (fewer in the subnormal range), with the remainder; twice the
   remainder compared with the divisor decides the rounding, ties to even. The quotient is computed
   one bit at a time after one division of words, so the remainder stays below the divisor, at
   most $2^{63}$, and every integer fits in one 64-bit word.
2. For two limbs, the rest $q - \mathrm{RN}(q)$ is that remainder over the divisor, times a power
   of two: the same division gives $\mathrm{RN}$ of it, and the case above is recognized from the
   two results (the rest is half the gap, the significand odd) and renormalized.
3. The error: the remainder of the last division, rounded up the same way.
4. Each limb, and the error, assembled from its sign, significand and exponent with
   `std::bit_cast`.

[The design of Milestone 2](../developer/design/milestone2.md#constants-at-compile-time) forms the dividend of the second
division and the sum of the two limbs as integers of up to three words, below $2^{180}$ (168 bits
observed); computing the quotient bit by bit keeps the remainder below the divisor instead, and
recognizing the one case that needs renormalization replaces the sum, so that no integer is wider
than 64 bits. The results are the same.

## The check

`kairn::is_rational_result(c, num, den)` decides whether `c` is exactly what the statement above
says, by other means than the computation: multiplications (by $\lvert\mathrm{den}\rvert$ and by
powers of two), additions and comparisons of integers, and no division. It reads the limbs and the
error back from their bit patterns, so that their assembly is checked too, then checks, with
$d = \lvert\mathrm{den}\rvert$:

- that every limb and the error are finite and the error is not negative;
- one limb: that it is $\mathrm{RN}(q)$, that is $\lvert q - \mathrm{value}\rvert$ is below half
  the gap of `value` on the side of $q$, or equal to it with `value` even;
- two limbs: that the pair is normalized, and that it is $(a, b)$ or $(a + 2b, -b)$ with
  $a = \mathrm{RN}(q)$ and $b = \mathrm{RN}(q - a)$, each checked as for one limb;
- that $\lvert\mathrm{value} \cdot d - \mathrm{num}\rvert \le \mathrm{error} \cdot d$ (with the
  sign of $\mathrm{den}$ on $\mathrm{num}$), that the number of `T` before `error` fails it when
  `error` is not zero, and that `exact` says whether the left side is zero;
- for $\mathrm{den} = 0$: every limb a NaN, `error` $+\infty$, `exact` false.

Every number is an integer times a power of two; the check scales each residual so that it is an
integer, in three 64-bit words. For a correct result every integer has fewer than 118 bits (116
were seen); a result whose integers do not fit is refused. Every result computed in a constant
expression is checked so, and a result that fails makes the expression invalid: the constant does
not compile, and the message names `kairn::detail::rational_result_fails_its_specification`
(`KAIRN_RATIONAL_CHECK`, 1 by default; 0 turns this off). At run time, a build with `KAIRN_CHECKS`
checks every result the same way and stops the program with a message on a failure.

What it adds: a constant that compiles has been checked against the whole statement, by code that
shares with the computation only the description of the format (its precision and exponents) and
the absolute value of a term, and that divides nothing. Both are written by hand and neither is
proved, so a wrong constant would need the two to be wrong on the same fraction in the same way.
`api.reject.rational.result_fails_its_check` plants a wrong flag in a copy of the header and
requires the constant not to compile; the same constant compiles with `KAIRN_RATIONAL_CHECK` 0.

**What it costs**, measured on an Apple M3 Max with other jobs running (`bench/rational_cost.py`):
a translation unit with $N$ distinct constants of `Expansion<double, 2>`, `-O2`, the median of
five compilations, after the 0.07 s (Apple clang 21) or 0.14 s (GCC 16) of including the header:

| Compiler | $N = 1$ | $N = 100$ | $N = 1000$ | per constant |
|---|---|---|---|---|
| Apple clang 21, without the check | +0.002 s | +0.025 s | +0.24 s | 0.24 ms |
| Apple clang 21, with it | +0.001 s | +0.062 s | +0.62 s | 0.62 ms |
| GCC 16, without the check | +0.002 s | +0.035 s | +0.34 s | 0.34 ms |
| GCC 16, with it | +0.007 s | +0.064 s | +0.63 s | 0.63 ms |

At run time, per call, on 4096 random fractions of 64-bit terms, the minimum of 31 samples:

| Compiler | `rational`, `double`: one limb, two | `float`: one, two | the check, one limb, two |
|---|---|---|---|
| Apple clang 21, `-O2` | 145 ns, 222 ns | 73 ns, 115 ns | 46 ns, 73 ns |
| GCC 16, `-O2` | 102 ns, 155 ns | 51 ns, 81 ns | 54 ns, 85 ns |

## What is tested

- **Against the oracle, for equality** (`api.rational.K.FORMAT`, `full.api.rational.K.FORMAT`):
  the oracle, which computes with exact rationals and shares no code with the header, generates
  fractions and compares every limb, the error and the flag of each result with its own: a result
  one unit off anywhere is a failure. The runner `tests/api/rational_runner.cpp` computes at run
  time, and also requires `is_rational_result` to accept each result. The full tier runs the
  runner of every [flag set](../developer/testing.md#flag-sets), whose outputs must be the same
  bytes.
- **Constants** (`api.rational.constexpr`): `static_assert`s of the limbs, the error and the flag
  of two dozen fractions and six integers, for `float` and `double`, one and two limbs (1/3, 1/10,
  $2^{53} + 1$, $-2^{63}$ as either term, the near ties above, second limbs and errors in the
  subnormal range of `float`), computed from the statement with Python's `fractions` by code that
  shares nothing with the header; that `is_rational_result` refuses each changed by one unit (a
  limb or the error moved to the next number of `T`, the flag flipped); and that a corpus of 104
  fractions gives the same bits at run time as in constant expressions, under each of the four
  rounding modes, built with every flag set (`api.flags.debug.rational`,
  `full.api.flags.SET.rational`), the debug build's included, where `KAIRN_CHECKS` is 1.
- **What must not compile** (`api.reject.rational.*`): a zero denominator in a constant
  expression, and a result that fails its check.
