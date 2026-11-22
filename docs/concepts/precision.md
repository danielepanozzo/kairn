# Precision and magnitude

A floating-point type answers two questions: how many significant bits a number has (its
*precision*), and how large or how small a number it can hold (its *range*). A second limb changes
the first and not the second. `Expansion<double, 2>` has 106 bits where a `double` has 53, but it
overflows where `double` overflows, and near the bottom of the range, where its second limb falls
among the subnormal numbers of `double`, it has fewer bits than 106. This page gives both for the
four types that exist, `T` = `float` or `double` with one or two limbs, and the error bound of each
operation as it is proved.

## An example

```cpp
--8<-- "docs/examples/cpp/concepts_precision.cpp:range"
```

```text
--8<-- "docs/examples/cpp/concepts_precision.txt::4"
```

$2^{200}$ is a `double`, and no number of `float` limbs holds it: the largest finite `float` is about
$3.4 \times 10^{38}$, and a two-limb number overflows where its leading limb does. At the other end,
$(1 + 2^{-60}) \cdot 2^{-1030}$ would need a second limb of $2^{-1090}$, which is below the smallest
positive `double`, $2^{-1074}$: the product returns $2^{-1030}$ alone. That is within the bound of
the operation, $2u^2\lvert xa\rvert + \eta$ with $\eta = 2^{-1074}$
([`mul_2_1_full`](../reference/mul_2_1_full.md)): the term $\eta$ is there for exactly this. The
program is
[`docs/examples/cpp/concepts_precision.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_precision.cpp)
(ctest: `api.example.concepts_precision`).

## The four types

The notation of the rest of the site
([How to read a page](../reference/reading.md#notation)): $p$ is the precision of the limb type `T`
(53 for `double`, 24 for `float`), $u = 2^{-p}$ its *unit roundoff*, the largest relative error of
one rounding to nearest, $\eta$ its smallest positive number (a subnormal one), and $\Omega$ its
largest finite number. The second and third columns are what a number of the type holds; the last
two what its operations promise at the top of the range.

| Type | Bits | All bits for $\lvert x\rvert \ge$ | Largest finite | Sums finite when | Products finite when |
|---|---|---|---|---|---|
| `double`, `Expansion<double, 1>` | 53 | $2^{-1022} \approx 2.2\cdot10^{-308}$ | $\approx 1.8\cdot10^{308}$ | as `double` | as `double` |
| `Expansion<double, 2>` | 106 | $2^{-969} \approx 2.0\cdot10^{-292}$ | $\approx 1.8\cdot10^{308}$ | $\lvert x\rvert, \lvert y\rvert \le 2^{1022}$ | $\lvert xy\rvert \le 2^{1023}$ |
| `float`, `Expansion<float, 1>` | 24 | $2^{-126} \approx 1.2\cdot10^{-38}$ | $\approx 3.4\cdot10^{38}$ | as `float` | as `float` |
| `Expansion<float, 2>` | 48 | $2^{-102} \approx 2.0\cdot10^{-31}$ | $\approx 3.4\cdot10^{38}$ | $\lvert x\rvert, \lvert y\rvert \le 2^{126}$ | $\lvert xy\rvert \le 2^{127}$ |

- **Bits** is `kairn::traits<X>::precision`, $k\,p$ for $k$ limbs.
- **All bits** from the magnitude $2^{kp-1}\eta$: for one limb the smallest normal number of `T`;
  for two limbs the magnitude at which the second limb's last bit reaches $\eta$. Below it a number
  between $2^E$ and $2^{E+1}$ has $E - \log_2\eta + 1$ bits, one fewer per halving of the magnitude
  ([Choosing T and k](../getting-started/index.md#choosing-t-and-k), whose program checks these
  thresholds against `kairn::traits`).
- **Largest finite** is that of `T` for every number of limbs: a two-limb number is finite when its
  leading limb is.
- **Finite when** is what is proved of the operators of two limbs: if the operands satisfy it, the
  result is finite (statement F3 of [What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)).
  For sums and differences the condition is on the operands, a quarter of the overflow threshold
  $2^{e_{\max}}$ ($2^{1024}$ for `double`, $2^{128}$ for `float`); for products on the exact
  product, half of it. Above it the result is either correct or $(\pm\infty, 0)$, never a finite
  wrong number (F2). How far the conditions are from where an overflow is first seen: exhaustive
  runs on small formats first saw one at 0.55 of the threshold or above for the additions and 0.86
  or above for the products, a measurement on those formats and not a claim
  ([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values), "Not proved yet").
  One limb is `T` itself: a result overflows exactly when the IEEE 754 operation of `T` does.

So `Expansion<float, 2>` has fewer bits than a plain `double` (48 against 53) and a far narrower
range, and loses bits below about $2 \times 10^{-31}$; `Expansion<double, 2>` keeps its 106 bits down to
about $2 \times 10^{-292}$.

## The error bound of each operation

Each bound has the same shape, an error relative to the exact result $v$ plus an absolute term for
underflow:

$$\lvert z - v\rvert \le c\,u^k\,\lvert v\rvert + t\,\eta .$$

The first term says that the result has about $k\,p - \log_2 c$ correct bits; the second only matters
for results near the bottom of the range, where a number no longer has all its bits. These are the
statements of the kernels the operators call, proved in Rocq for every precision from the kernel's
minimum on (at most 4, so for `float` and `double` alike), for finite operands, and they hold
whenever the result is finite: there is no smallest magnitude below which they stop holding, since
the absolute term covers the subnormal range, and no largest other than the overflow of the
result. Each kernel's page gives the theorem and the file that prove it.

| Operation | One limb | Two limbs |
|---|---|---|
| `x + y`, `x - y` | $\frac{u}{1+u}\lvert v\rvert$ ([`add_1_1`](../reference/add_1_1.md)) | $\frac{3u^2}{1-4u}\lvert v\rvert$ ([`add_2_2`](../reference/add_2_2.md), [`sub_2_2`](../reference/sub_2_2.md); JMP17's AccurateDWPlusDW) |
| `x + a`, `x - a`, `a - x`, `a` of `T` | the same | $2u^2\lvert v\rvert$ ([`add_2_1`](../reference/add_2_1.md), [`sub_2_1`](../reference/sub_2_1.md), [`sub_1_2`](../reference/sub_1_2.md); DWPlusFP) |
| `add_fast(x, y)` | the same | $3u^2(\lvert x\rvert + \lvert y\rvert)$, relative to the operands ([`add_fast_2_2`](../reference/add_fast_2_2.md); SloppyDWPlusDW) |
| `x * y` | $\frac{u}{1+u}\lvert v\rvert + \tfrac12\eta$ ([`mul_1_1`](../reference/mul_1_1.md)) | $4u^2\lvert v\rvert + \tfrac32\eta$ ([`mul_2_2`](../reference/mul_2_2.md); DWTimesDW3) |
| `x * a`, `a` of `T` | the same | $2u^2\lvert v\rvert + \eta$ ([`mul_2_1`](../reference/mul_2_1.md); DWTimesFP3) |
| `ldexp(x, n)`, `half(x)` | one rounded product, as `x * y` | $\eta$, with no relative term ([`mul_pow2_2`](../reference/mul_pow2_2.md)) |
| `-x`, `abs(x)`, comparisons | exact | exact |
| `to_nearest`, `to_down`, `to_up` | the value itself | the exact rounding to `T` |

The algorithms of two limbs are those of Joldes, Muller and Popescu
([JMP17](../developer/design/phase0/references.md#jmp17)), with bounds from Muller and Rideau's
formalization or proved here, each page says which. The rows of `ldexp` hold when $2^n$ is a number of
`T`; beyond, the header calls the kernel two or three times, and what it then returns is argued and
tested, not machine-checked ([What "correct" means here](correctness.md#what-is-not-machine-checked)).
`add_fast` is the cheaper of the two additions, with a bound relative to $\lvert x\rvert + \lvert y\rvert$
rather than to the sum, so it can be much larger than the sum's when the operands cancel; the
operator `+` is the accurate one.

**In the underflow range.** The sums have no absolute term: their relative bound holds at every
magnitude. The products have one, $\tfrac12\eta$, $\eta$ or $\tfrac32\eta$: when the result is small,
that term is larger than the relative one, and the result can have only the few bits its magnitude
allows, as in the example above. A program that needs all its bits keeps its values above the
threshold of the table, scaling them by a power of two if it must (`ldexp`, whose error is at most
$\eta$).

**The constants as numbers.** `kairn::traits<X>` exports each bound as two numbers of `T`, `unit`
and `tiny`, the constants $c\,u^k$ and $t\,\eta$ rounded up, so that a program's own error analysis
can use them:

```cpp
--8<-- "docs/examples/cpp/concepts_precision.cpp:table"
```

```text
--8<-- "docs/examples/cpp/concepts_precision.txt:6:9"
```

$\frac{3u^2}{1-4u}$ for `double` is just above $3 \cdot 2^{-106}$, `0x1.8000000000004p-105`; the
$\tfrac32\eta$ of the product rounds up to $2\eta = 2^{-1073}$. The entries for `x + a`, `x * a`,
`add_fast` and the others are `add_limb`, `mul_limb`, `add_fast`, `sub`, `sub_limb` and `ldexp`. Each
entry also has `unit_computed` and `tiny_computed`, the same bound relative to the computed result,
which is what a running error analysis needs; for `add_fast`, whose bound is relative to the
operands, those two are $+\infty$ (the comments of `kairn/traits.hpp`, in the
[C++ API](../api/index.md)). An entry has constants only when the operation's kernel is proved
([What "correct" means here](correctness.md#unverified)).

## float limbs or double limbs

On a CPU, which is all Kairn has in this version, `double` limbs are the choice: `float` limbs have
the narrower range above, and they saved little or no time. Measured on three machines with five
compilers, an operation on `float` limbs took 0.83 to 1.08 times as long as the same on `double`
limbs in scalar code on the Apple M3, with GCC 13 and with MSVC, and 1.12 to 1.80 times as long with
Clang 18, which keeps a pair of `float` limbs in one vector register and shuffles it at every step
([Benchmarks, Milestone 1](../developer/results/bench-milestone1.md#5-float-limbs)). The second
measurement, of the intervals, the balls and a polynomial, found 0.83 to 1.08 in scalar code, half
where the compiler vectorizes a loop with twice the lanes, and 1.1 to 2.8 times for some loops with
Clang 18 ([Benchmarks, Milestone 2](../developer/results/bench-milestone2.md#packed-code-and-float-limbs)).
`float` limbs are meant for GPUs, where `float` arithmetic is much faster than `double`; Kairn has
no GPU code yet ([Concepts](index.md#what-the-library-does-not-have-yet)).
