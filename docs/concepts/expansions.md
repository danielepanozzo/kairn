# Numbers of several limbs

A `double` holds 53 significant bits. When a computation needs more, because a sum cancels or
because a result is wanted to more digits, Kairn stores a number as the exact, unevaluated sum of
two `double`s (or two `float`s): `kairn::Expansion<T, 2>`, a *floating-point expansion*, also
called a double-word or double-double number. Each of the two numbers is a *limb*. Arithmetic on
such numbers is done with ordinary operations of `T`, arranged so that the rounding error of each
step is caught and kept in the second limb. This page says what such a number is, what
"normalized" means and why it matters, and what the operators return when a value overflows or is
not a number.

## An example to check by hand

$1 + 2^{-60}$ is not a `double`: written in binary it is a 1, then 59 zeros, then a 1, which needs
61 significant bits. The sum of two `double`s rounds it to 1. Two limbs keep it:

```cpp
--8<-- "docs/examples/cpp/concepts_expansions.cpp:limbs"
```

The program prints the limbs in hexadecimal, where $2^{-60}$ is `0x1p-60`:

```text
--8<-- "docs/examples/cpp/concepts_expansions.txt::2"
```

The first limb is 1 and the second is $2^{-60}$, and their sum, in exact arithmetic, is the number.
The sum of the `Expansion` and the `double` is the operation `x + a` of a two-limb number and a
limb, whose result is claimed to be within $2u^2\lvert x + a\rvert$ of the exact sum, with
$u = 2^{-53}$ ([`add_2_1_full`](../reference/add_2_1_full.md)). Here the exact sum fits in two
limbs, and the result is that sum: the program checks it.

The whole program is
[`docs/examples/cpp/concepts_expansions.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_expansions.cpp);
ctest builds and runs it, checks the values it prints, and compares its output with the text on
this page (`api.example.concepts_expansions`).

## Normalized numbers

A pair of `double`s can stand for the same value in more than one way: $1 + 2^{-60}$ is also
$(1 + 2^{-52}) + (2^{-60} - 2^{-52})$. Kairn allows only one of them. A two-limb number
$x = x_0 + x_1$ is **normalized** when adding the second limb to the first and rounding to nearest
gives the first back:

$$x_0 = \mathrm{RN}(x_0 + x_1).$$

In words: the second limb is at most half a unit in the last place of the first, so it is too small
to change the first limb when the two are added, and the first limb is the value rounded to the
nearest `double` ([Numbers](../developer/design/phase0/numbers.md#the-normalization-invariant)).
For two limbs this fixes the representation: a value has one normalized pair, up to the signs of
zero limbs. Here $1 + 2^{-53}$ lies exactly halfway between 1 and the next `double`, $1 + 2^{-52}$;
rounding to nearest breaks the tie toward the even one, 1, so only the first of these two pairs is
normalized:

```cpp
--8<-- "docs/examples/cpp/concepts_expansions.cpp:normalized"
```

```text
--8<-- "docs/examples/cpp/concepts_expansions.txt:3:4"
```

Why it matters:

- **Every guarantee assumes it.** Each operation's proved statement requires normalized operands
  and gives a normalized result whenever the result is finite (each kernel's page in the
  [reference](../reference/index.md) lists it under "Requires"). Every constructor and operator
  returns such numbers, so a program that builds its numbers with them never sees another kind.
- **The leading limb is the value rounded to `T`.** `kairn::to_nearest(x)` is that rounding
  ([`to_nearest_2`](../reference/to_nearest_2.md)), and the sign of the value is the sign of the
  leading limb.
- **It is checked where a program could break it.** A program that writes the limbs itself, through
  `Expansion<T, 2>::from_limbs(p)`, gets a check in a build with checks (the default without
  `NDEBUG`), which stops the program on a pair that is not canonical (below);
  `from_limbs_unchecked(p)` and writing `x.limb[i]` directly are not checked. In a build with checks
  every operator checks its operands too; without them, an operation on a pair that is not
  normalized has no undefined behavior, and no guarantee for its result
  ([Troubleshooting](../getting-started/index.md#when-a-check-of-a-build-without-ndebug-fails)).
  `kairn::is_normalized(x)` tests a pair, exactly.

A number is **canonical** when it is finite and normalized, or one of the three values that stand
for something that is not a finite number: $(+\infty, 0)$, $(-\infty, 0)$ and
$(\mathrm{NaN}, \mathrm{NaN})$. Every operator requires canonical operands and returns canonical
results ([What holds today](../getting-started/guarantees.md)).

## One limb and two

`Expansion<T, 1>` is a value of `T` with Kairn's interface: every value of `T` is a one-limb number,
and each of its operations is the IEEE 754 operation of `T`. It is there so that code written for
k-numbers can run at the precision of `T`, and its operations are meant to cost what those of `T`
cost: the test `api.k1.zero_cost` finds the same machine instructions as for `T`, or fewer, in the
loops it compiles, with the exceptions that [One limb](../getting-started/guarantees.md#one-limb)
lists (under Clang's default contraction a product followed by a sum is fused for `double` and not
for `Expansion<double, 1>`; MSVC does not vectorize a loop over the wrapper).

`Expansion<T, 2>` has $2p$ significant bits, 106 for `double` and 48 for `float`, where its value is
large enough for the second limb not to fall into the subnormal range
([Precision and magnitude](precision.md)). Each of its operations is a short, fixed sequence of
operations of `T`, listed on its reference page: the sum of two two-limb numbers has twenty, the
product nine ([`add_2_2`](../reference/add_2_2.md), [`mul_2_2`](../reference/mul_2_2.md)). Measured
on three machines with five compilers, a two-limb sum `x + y` took 5.1 to 10.4 ns per step of a
chain of dependent sums, and 1.5 to 4.4 ns per operation in a loop of independent ones, where the
processor overlaps them; a `double` addition took 0.29 to 0.80 ns per step of a chain, a figure that
the page explains is below the latency of one addition
([Benchmarks, Milestone 1](../developer/results/bench-milestone1.md#3-the-cost-of-a-ball-operation),
the table "In absolute terms").

An operand of type `T` next to a two-limb number is a limb, and has operations of its own:
`x + a`, `x - a`, `a - x` and `x * a`, shorter than the operations of two two-limb numbers (eleven
operations of `T` for `x + a`, [`add_2_1`](../reference/add_2_1.md)), with bounds of their own:
`x + a` is within $2u^2\lvert x + a\rvert$, where `x + y` is within
$\frac{3u^2}{1-4u}\lvert x + y\rvert$ ([What holds today](../getting-started/guarantees.md#the-operations)
has the table). An `Expansion<T, 1>` next to an `Expansion<T, 2>` is the same: its limb.

## Overflow, infinities and NaN

The operators of two limbs return what `T` would return: an overflow gives an infinity with the
sign of the exact result, as $(\pm\infty, 0)$, and an operation with an infinite or NaN operand
gives the canonical form of the operation of `T` on the leading limbs:

```cpp
--8<-- "docs/examples/cpp/concepts_expansions.cpp:special"
```

```text
--8<-- "docs/examples/cpp/concepts_expansions.txt:5:7"
```

This is proved, in a model of IEEE 754 with overflow, as five statements about every operator's
result $w$, for canonical operands ([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values),
F1 to F5): $w$ is canonical; if its leading limb is finite, every operand was finite and $w$ is
normalized and within the operation's bound, so that an overflow inside the computation can never
give a finite wrong result; it is finite when the operands are below a stated threshold (a quarter
of the overflow threshold for sums, $2^{1022}$ for `double`; [Precision and magnitude](precision.md)
has the others); if every operand is finite and $w$ is not, $w$ is $(\pm\infty, 0)$; and with an
operand that is not finite, $w$ is what `T` gives ($+\infty + 1 = +\infty$,
$\infty - \infty = \mathrm{NaN}$, $0 \cdot \infty = \mathrm{NaN}$; which NaN is not specified). A
program tests a result with `kairn::isfinite(x)`, which reads the leading limb.

**`kairn::finite::`** is the same arithmetic without the step that makes infinities and NaN
canonical: `add`, `sub`, `mul`, `add_fast` and `ldexp`, on the same operands as the operators.
Each is the operation's *core*, and its contract is the core's: either the leading limb of the
result is not finite, or the result is normalized and within its bound. Which pattern of
non-finite limbs comes out is not specified (it may be $(+\infty, \mathrm{NaN})$), so such a result
is not canonical and must be tested with `kairn::isfinite` before it is given to an operator. For one
limb the functions are the operators themselves. The step they leave out costs little in a chain of
dependent operations and more in a loop of independent ones: the operators took 0.94 to 1.07 times
as long as the cores in a chain, and 1.08 to 2.60 times as long in a loop, most where the compiler
vectorized the core's loop and not the operator's
([Benchmarks, Milestone 1](../developer/results/bench-milestone1.md#2-the-fix-up-for-non-finite-results)).
`kairn::finite::` is for code that knows its values stay finite and wants those operations back.

## Where to go next

- [Precision and magnitude](precision.md): how many bits a number has at each magnitude, and the
  error bound of each operation.
- [What "correct" means here](correctness.md): what a bound such as $2u^2\lvert x + a\rvert$
  promises, and how it is established.
- [Accurate sums and dot products](../tutorials/accurate-sums.md): two limbs at work on a sum that
  `double` gets entirely wrong.
