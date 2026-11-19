# What holds today

Kairn's public headers cover `Expansion<T, 1>`, `Expansion<T, 2>` and `Ball<T, 1>`, `Ball<T, 2>`
for `T` = `float` and `double`. This page says, for each operation, what is proved, and what is
not written yet. It describes the repository as `gen/claims.json` stands in this version; the
compiler enforces the current status on its own (below), so the code cannot fall behind it. The
design is in the [Phase 0 report](../developer/design/phase0/index.md) and the
[Milestone 1 statements](../developer/design/milestone1.md).

Notation, from [Numbers](../developer/design/phase0/numbers.md#notation): $u = 2^{-p}$ is the unit
roundoff of a limb ($2^{-53}$ for `double`, $2^{-24}$ for `float`) and $\eta$ its smallest
subnormal number ($2^{-1074}$, $2^{-149}$). A k-number is *normalized* when each limb is the sum
of itself and the next one rounded to nearest; every operation requires normalized operands.

## Proved, and UNVERIFIED

Every operation is computed by one generated kernel, and `gen/claims.json` says what that kernel
claims and whether its claims are **proved**: Rocq accepts a proof of the generated statement, and
the audit finds no axiom beyond the four allowed
([Architecture](../developer/architecture.md#the-formal-model)). Any other kernel is
**UNVERIFIED**: its statement is a target, tested by the oracle in exact arithmetic but not proved.

An UNVERIFIED operation compiles only when one of its operands carries the marker
`kairn::unverified(...)`: `kairn::unverified(x) - y`, `kairn::unverified(x) < y`,
`kairn::to_down(kairn::unverified(x))`, `x -= kairn::unverified(y)`. The marker applies to the one
operation it is an operand of, and the result is an ordinary value, so each unproved step of a
computation is visible in the source. It may be put on a `float` or `double` operand too (it
converts back to that type), so that code generic over `T` and the k-numbers can be written once,
and it is accepted on proved operations as well, so that code written with it keeps compiling when
a proof lands. A marked left operand of `+=` does not compile: it would modify a copy.

Which kernels are proved is read from `include/kairn/gen/bounds.hpp`, which the generator writes
from `gen/claims.json`. When a proof is checked and the generator is rerun, the operation compiles
without the marker. `kairn::traits` exports error constants only for proved operations: the entry
of an UNVERIFIED one has `verified == false` and no constants to read, so that no client bound can
be built on a number that is only a target.

In this version every kernel of one and two limbs is proved, so no operation of these headers
needs the marker. It is how the operations still to come (three and four limbs, division, square
root) will ship before their proofs.

## The operations

For normalized operands $x$, $y$ and a limb $a$, with $z$ the result. "Exact" rows have no kernel:
they are IEEE 754 operations on one limb, or read limbs, and need no proof of Kairn's. The second
column is the claim of the kernel, proved in the *real model*, where no operation overflows. The
third says what is proved in Flocq's model of IEEE 754, where operations overflow
([Milestone 1](../developer/design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)).

| Operation (kernel) | Claim, proved in the real model | In the IEEE model |
|---|---|---|
| `x + y` (`add_2_2`) | $z$ normalized, $\lvert z - (x + y)\rvert \le \frac{3u^2}{1 - 4u}\lvert x + y\rvert$ | either $z_0$ is not finite or the claim holds; $z_0$ finite when $\lvert x_0\rvert, \lvert y_0\rvert \le 2^{1022}$ (`double`) |
| `x * y` (`mul_2_2`) | $z$ normalized, $\lvert z - xy\rvert \le 4u^2\lvert xy\rvert + \tfrac32\eta$ | either $z_0$ is not finite or the claim holds; $z_0$ finite when $\lvert xy\rvert \le 2^{1023}$ (`double`) |
| `x + a`, `a + x` (`add_2_1`) | $z$ normalized, $\lvert z - (x + a)\rvert \le 2u^2\lvert x + a\rvert$ | either $z_0$ is not finite or the claim holds |
| `x * a`, `a * x` (`mul_2_1`) | $z$ normalized, $\lvert z - xa\rvert \le 2u^2\lvert xa\rvert + \eta$ | either $z_0$ is not finite or the claim holds |
| `add_fast(x, y)` (`add_fast_2_2`) | $z$ normalized, $\lvert z - (x + y)\rvert \le 3u^2(\lvert x\rvert + \lvert y\rvert)$ | either $z_0$ is not finite or the claim holds |
| `x - y` (`sub_2_2`) | that of `x + y` | not instantiated |
| `x - a`, `a - x` (`sub_2_1`, `sub_1_2`) | that of `x + a` | not instantiated |
| `ldexp(x, n)`, `half(x)` (`mul_pow2_2`) | $z$ normalized, $\lvert z - 2^n x\rvert \le \eta$ | not instantiated |
| `-x`, `abs(x)` (`neg_2`, `abs_2`) | exact, normalized | no statement yet |
| `<`, `<=`, `>`, `>=`, `==`, `!=` (`lt`, `le`, `eq` kernels) | the truth about the exact values | no statement yet |
| `to_nearest`, `to_down`, `to_up`, `abs_upper` (`to_nearest_2`, `to_down_2`, `to_up_2`, `abs_upper_2`) | the exact rounding to `T` | no statement yet |
| one limb: `+`, `-`, `*`, `add_fast`, `ldexp`, `half` (`add_1_1`, `mul_1_1`) | one rounding to nearest: $\lvert z - v\rvert \le \frac{u}{1 + u}\lvert v\rvert$, plus $\tfrac12\eta$ for products | the IEEE 754 operation |
| one limb: `-x`, `abs`, comparisons, conversions | exact (no kernel) | the IEEE 754 operation |
| `Ball`: `+`, `-`, `*`, scaling by a `T`, `-X` (`ball_add_1`, ..., `ball_neg_2`) | containment: $x \circ y \in Z$ for all $x \in X$, $y \in Y$; for two limbs the center is normalized | no statement yet |
| construction, `limb`, `sign`, `isfinite`, `is_normalized` | exact (no kernel) | |

The claims hold for every precision from the kernel's minimum on (at most 4), so for `float` and
`double` alike; the thresholds of the third column are $2^{126}$ and $2^{127}$ for `float`. The
IEEE-model theorems are checked against statements written by hand; the generator does not print
them yet. The constants of every row with an error bound, rounded up to `T`, are in
`kairn::traits<kairn::Expansion<T, 2>>` (`add`, `add_limb`, `add_fast`, `sub`, `sub_limb`, `mul`,
`mul_limb`, `ldexp`) and `kairn::traits<T>`.

## Overflow and non-finite values

The design returns canonical infinities and NaN the way `T` does
([D5](../developer/design/phase0/decisions.md#d5-non-finite-results)), through *full kernels* that
follow each core with a fix-up ([IEEE-like results](../developer/design/milestone1.md#ieee-like-results)).
**Those are not generated yet**: every operation today calls the *finite core* of its kernel. What
holds:

- Where the third column of the table says so, an intermediate overflow never produces a finite
  wrong result: either the leading limb of the result is not finite, or the result is normalized
  and within its bound.
- For `x - y`, `x - a`, `a - x` and `ldexp`, the same is expected by the same argument but not
  proved; for the operations with comparisons, selects or steps to a neighbor (negation, `abs`,
  comparisons, conversions, the Ball operations), nothing is stated in the IEEE model yet.
- When the leading limb of a result is not finite, the limbs may hold any non-finite pattern, such
  as $(+\infty, \mathrm{NaN})$, not the canonical forms. With an operand that is not finite,
  nothing is claimed about the result.
- The constructor from a `T` already returns the canonical forms: $(\pm\infty, 0)$ and
  $(\mathrm{NaN}, \mathrm{NaN})$.
- A `Ball` has no special states yet (a NaN radius for the empty set; the whole line, radius
  $+\infty$ and center 0), and a center or radius that is not finite is returned as the kernel
  computed it.
- `ldexp(x, n)` takes only an `n` for which $2^n$ is a number of `T` ($-1074 \le n \le 1023$ for
  `double`); for any other `n` the result is NaN. The two-step scaling of
  [Milestone 1](../developer/design/milestone1.md#second-wave-kernels) is not written.

## A product written into a call

Kairn's kernels are written so that no compiler can fuse a product into one of their additions
(rules R1 and R2 of [Environment](../developer/design/phase0/environment.md#the-rule-no-product-feeds-an-addition)),
and the tests check that under every contraction setting. That protects each kernel and every
combination of Kairn's operations, **but not a product computed by the program itself**: in
`x + a * b`, with `a` and `b` of type `double`, a compiler that contracts across statements can
fuse `a * b` into the error-free sums inside the kernel, which are then not error-free. Measured
with `x` $= -\texttt{0x1.4ba3c12d3e764p-1}$, `a` $= \texttt{0x1.f2d212ebf7bc2p-1}$, `b` $=
\texttt{0x1.5466e6af5c598p-1}$: the result should be $x + \mathrm{RN}(ab) =
-\texttt{0x1.c7d548p-32}$ exactly, and is $(-\texttt{0x1.c7d546b5bb8fcp-32},
\texttt{0x1.7c53p-86})$, normalized and wrong by about $2^{-24}$ relative to the result, whether
the product is taken rounded or exact.

| Compiler and setting | `x + a * b` |
|---|---|
| GCC 13 (x86-64), GCC 16 (AArch64), default (`-ffp-contract=fast` for C++) | **wrong** |
| GCC, `-ffp-contract=off` | correct |
| Apple clang 21 (AArch64), default (`-ffp-contract=on`) | correct |
| Apple clang 21, `-ffp-contract=fast` | **wrong**, also when the product is one of `Expansion<double, 1>` |
| Clang 18 (x86-64), every setting | correct |
| MSVC 19.52, `/fp:precise` (default) | correct |
| MSVC 19.52, `/fp:contract` | **wrong** |

The same holds when the product is first stored in a variable, since these compilers contract
across statements. Until this is resolved, compile code that passes its own products to Kairn
with `-ffp-contract=off` (GCC, Clang) or without `/fp:contract` (MSVC), or let Kairn compute the
product, as in `x + kairn::Expansion<double, 2>(a) * b`.

## Constant evaluation

Every operation is `constexpr` except those whose kernel has a fused multiply-add and no
constant-evaluation variant yet: `x * y`, `x * a`, `ldexp` and `half` on two limbs, and every
`Ball` operation but the negation. With Clang, an operation that produces a NaN is not a constant
expression, so `ldexp` with an exponent out of range cannot be evaluated at compile time there.

## One limb

`Expansion<T, 1>` is meant to cost what `T` costs. Measured by the test `api.k1.zero_cost`, which
compares the instructions emitted for three loops over `double` and over `Expansion<double, 1>`:
identical or fewer with GCC, and with Clang under `-ffp-contract=off` or `=fast`; under Clang's
default contraction a product followed by a sum is fused for `double` and not for
`Expansion<double, 1>` (decision
[D6](../developer/design/phase0/decisions.md#d6-one-limb-and-contraction-under-clang)), unless the
program defines `KAIRN_K1_CONTRACT`. MSVC does not vectorize a loop over the wrapper where it
vectorizes the loop over `double`.

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
flush-to-zero are in their default state; Kairn never changes them. In a build without `NDEBUG`
(or with `KAIRN_CHECKS` defined to 1), every operation checks the environment and that its
operands are normalized, and stops the program with a message if not.
