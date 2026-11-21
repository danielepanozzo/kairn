# Sums and dot products of arrays

This tutorial sums arrays and takes their dot product with the functions of `kairn/batch.hpp`, and
checks each result against the bound that `kairn::traits` gives for its length. Every fragment
below is part of one program,
[`docs/examples/cpp/arrays.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/arrays.cpp),
and the output shown is what it prints: ctest builds it in every form of `Packed` the platform
has, runs it, and compares its output with the text shown [at the end](#the-whole-output)
(`api.example.arrays.*`). The program also checks every result, in both orders of summation,
against its bound, with an exact reference computed in integer arithmetic, and fails if one is
outside it.

## The data

An array of numbers of one limb is a plain array of `double`; an array of two-limb numbers is two
arrays, the leading limbs and the second ones. The functions take *views* of them,
[`kairn::SoAView`](../reference/soa.md), which own nothing. Here the numbers have 26-bit
significands, so that each product is exact in `double` and the exact dot product can be computed
in integers:

```cpp
--8<-- "docs/examples/cpp/arrays.cpp:data"
```

`x1` sees `x` as $n$ numbers of one limb; `x2` sees the same array, with an array of zeros as the
second limbs, as $n$ numbers of two limbs.

## A dot product and its bound

```cpp
--8<-- "docs/examples/cpp/arrays.cpp:dot"
```

`kairn::dot` returns a `Reduction`: the number, and `finite`, true exactly when it is finite. An
infinite or NaN element, or an overflow, makes `finite` false and the number the canonical NaN; it
is never a finite wrong value.

Without an order argument, `dot` adds in the lane order of the build: the packed loop, which deals
the elements to the lanes of a register ($W$ = 4 for `double` with AVX2, 2 with NEON, 1 without
either), sums each lane, then adds the lanes. Its bits depend on the instruction set. With
`kairn::sequential` it adds element after element, and gives the same bits on every platform; the
program prints those. Both have **the same statement**, for every $n$
([Functions on arrays](../reference/batch.md#what-each-function-states)): a theorem bounds every
order of summation by the same expression of $n$.

`kairn::traits<X>::dot(n)` is that bound as numbers of `T`, computed by a proved kernel: with
`b = traits<X>::dot(n)`, whenever the result is finite,

$$\Bigl\lvert d - \sum_i x_i y_i\Bigr\rvert \le b.\mathit{unit}\,\sum_i\lvert x_i y_i\rvert +
b.\mathit{tiny}.$$

`b.unit` is at least $\gamma_n(e) = n e/(1 - n e)$, with $e = u/(1+u)$ for one limb (about
$n \cdot 2^{-53}$) and $4u^2$ for two (about $n \cdot 2^{-104}$); `b.tiny`, a few times the
smallest normal number, covers products that underflow. The inequality is between real numbers:
a program that evaluates its right side in floating point rounds it up (`kairn::rmul`,
`kairn::radd`). The program here evaluates it exactly enough to decide: the error and the sum of
magnitudes in integers, the error rounded up and the right side rounded down.

## A sum of an array the program fills

```cpp
--8<-- "docs/examples/cpp/arrays.cpp:sum"
```

`traits<X>::sum(n)` bounds a sum of $n$ numbers made by $n - 1$ additions in any tree: `kairn::sum`
in both orders, `kairn::sum_fast`, and a program's own tree of additions of Kairn. It has no
underflow term. The array `p` is filled with products in the same function that sums it: a
compiler that contracts across statements could fuse such a product into the first addition of an
inlined loop, and the sum would then not be that of the numbers in `p`. `kairn::sum` passes every
limb it adds through a guard first, so that it cannot ([What holds
today](../getting-started/guarantees.md#products-the-program-passes-in)).

## A map, in place

```cpp
--8<-- "docs/examples/cpp/arrays.cpp:map"
```

`kairn::axpy(a, x, y, z)` writes $z_i = a x_i + y_i$, each element within its own bound
(`traits<X>::axpy_limb`), and may write in place: `z` the same arrays as `y` (or as `x`). It
returns `true` exactly when every element written is finite; when it is false, each element that
is not finite is the canonical NaN and the others are as computed.

## The whole output

```text
--8<-- "docs/examples/cpp/arrays.txt"
```

The errors are far below the bounds: the bound holds for every array of $n$ terms, the worst one
included, and these sums have little cancellation. A bound for a length beyond what the kernel
bounds, about $n e = \tfrac14$ ($2^{51}$ terms of one limb of `double`, $2^{22}$ of `float`), is
$+\infty$, which claims nothing; in a constant expression it does not compile.
