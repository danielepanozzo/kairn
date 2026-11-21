# A vector loop

This tutorial writes one loop over arrays of two-limb numbers with `kairn::Packed`, the type that
holds several numbers in SIMD registers, and says exactly what is guaranteed about its result. The
loop is a dot product. It is written once and compiles for AVX2, for the Advanced SIMD of
AArch64, and for a target with neither. Every fragment below is part of one program,
[`docs/examples/cpp/packed_dot.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/packed_dot.cpp),
and the output shown is what it prints: ctest builds it in every form of `Packed` the platform
has, runs it, and compares its output with the text shown [at the end](#the-whole-output)
(`api.example.packed_dot.*`). The program also checks each result against the bound below, with
an exact reference computed in integer arithmetic, and fails if one is outside it.

## The data

Arrays of numbers are held as one array per limb: `hi[i]` and `lo[i]` are the two limbs of
number $i$. That is the layout `Packed` loads from, and a `kairn::SoAView` sees such arrays
without owning them. Here the numbers are integers near $2^{25}$, chosen so that the products are
exact in `double` and the sum cancels:

```cpp
--8<-- "docs/examples/cpp/packed_dot.cpp:data"
```

```cpp
--8<-- "docs/examples/cpp/packed_dot.cpp:call"
```

## The loop

```cpp
--8<-- "docs/examples/cpp/packed_dot.cpp:loop"
```

`Pack::lanes` is $W$: 4 with AVX2, 2 with NEON, 1 for a target with neither, so the same source is
a vector loop on the first two and a scalar loop on the third. `x.load(i)` reads elements $i$ to
$i + W - 1$ into one `Packed<double, 2>`; `x.load(i) * y.load(i)` is $W$ products of two limbs,
each the operation `x * y` of `Expansion<double, 2>`, side by side; and `sum + ...` is $W$ sums.
The last `x.size() % W` elements are loaded with `load_partial`, which reads only those and puts
zero in the other lanes, whose products and sums then add nothing. At the end the program adds
the lanes itself, in the order it chose: lane 0, then 1, and so on.

## What is guaranteed

Each operation of `Packed` has, in each lane, the statement of the operation of `Expansion` of the
same name ([Packed](../reference/packed.md)). For finite operands whose result is finite:

- a product $z$ of two-limb numbers has $|z - xy| \le u_m\,|xy| + \tau_m$
  ([`mul_2_2_full`](../reference/mul_2_2_full.md)), and a sum $|z - (a + b)| \le u_a\,|a + b|$
  ([`add_2_2_full`](../reference/add_2_2_full.md)), with $u_m$ = `traits<Number>::mul.unit`,
  $\tau_m$ = `traits<Number>::mul.tiny` and $u_a$ = `traits<Number>::add.unit` (for `double`,
  $u_m = 2^{-104}$, $\tau_m = 2^{-1073}$, the smallest `double` not below $\tfrac32\,2^{-1074}$, and
  $u_a$ just above $3 \cdot 2^{-106}$);
- an overflow anywhere makes the result infinite or NaN, never a finite wrong value.

That is all Kairn states. What follows for the loop is the program's own analysis, from those
bounds and from the order the loop wrote. Each product goes through at most
$d = \lceil n/W \rceil + W$ sums: those of its lane, from its own on, and those of the reduction.
With $e = \max(u_m, u_a)$ and $\gamma_m = m e/(1 - m e)$, the classical argument for a sum of
terms with relative errors (Higham, *Accuracy and Stability of Numerical Algorithms*, chapter 3)
gives, whenever the result is finite,

$$\Bigl\lvert \mathtt{dot}(x, y) - \sum_i x_i y_i \Bigr\rvert \le
\gamma_{d+1} \sum_i \lvert x_i y_i\rvert + (1 + \gamma_d)\, n\, \tau_m .$$

The program computes it so:

```cpp
--8<-- "docs/examples/cpp/packed_dot.cpp:bound"
```

Three things the bound does not say. It says nothing about the order of the additions beyond the
one the loop wrote: that order depends on $W$, so the same source gives different bits on
different targets (the program's random sets do, below its output), each within the bound computed
with its own $W$. It is not a bound Kairn proves: the theorems are about each operation, and the
composition is the program's, as it would be for `double`. And it assumes canonical operands, which
a build with checks verifies at each load (`from_limbs` in each lane).

## The whole output

```text
--8<-- "docs/examples/cpp/packed_dot.txt"
```

The `double` loop, `plain += a[i] * b[i]`, loses 43 in a result of 33 566 778: its partial sums
come near $2^{59}$, where the spacing of `double` is 64. The packed two-limb loop returns the exact
value in every form, since every partial sum of these integers fits in two limbs. The random sets
have sums that need far more than two limbs; their results differ between AVX2, NEON and the
scalar form, each within its bound: the largest error of the three sets was $1.4 \cdot 10^{-3}$ of
its bound with AVX2, $5.2 \cdot 10^{-4}$ with NEON and $5.0 \cdot 10^{-4}$ in the scalar form (the
program prints these on its standard error). The bound is a worst case over every possible
rounding, which these sums do not come near.

## When to use it

`Packed` is for a loop that a program writes itself and wants to run $W$ numbers at a time. For a
sum, a dot product or an `axpy` over whole arrays, the functions on arrays that Milestone 2 adds
will be loops of this kind with a bound proved as a function of $n$; until they are in the public
headers, a loop like this one is the way. A plain loop over `Expansion<double, 2>` gives the same
guarantee per operation, one number at a time: [Getting started](../getting-started/index.md#vector-loops)
compares the three.

## What the headers do not provide

No packed `Ball` or `Interval`; no dispatch at run time (the code is that of the instruction set
the file is compiled for); no reduction of the lanes (the program writes it, as here); and no
alignment requirement: the loads and stores are unaligned, and an `SoA` aligns its arrays to 64
bytes only so that they need not straddle cache lines.
