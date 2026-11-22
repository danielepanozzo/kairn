# Arrays

Most numerical work is on arrays: a sum of a million terms, a dot product, an update
$y \leftarrow ax + y$. Kairn stores an array of numbers of $k$ limbs as $k$ arrays, one per limb
(*structure of arrays*), because that is the layout in which SIMD registers load several numbers at
once. On top of that layout it has four things: containers and views, the packed type for loops a
program writes itself, functions on whole arrays with a bound for the whole loop, and an
accumulator for sums built term by term. This page says what each is for, how the error of a sum or
a dot product grows with its length and how a program gets its bound, and what the order of
summation changes.

## Arrays and views

```cpp
--8<-- "docs/examples/cpp/concepts_arrays.cpp:views"
```

- **`kairn::SoAView<T, k>`** sees $k$ arrays of `T` and a length that the program owns (or an
  `SoA` does), and `SoAView<const T, k>` sees them read-only. It owns nothing, never allocates, and
  is cheap to pass by value. At $k = 1$ it is one plain array of `T`. `v[i]` is a proxy that reads
  element $i$ as an `Expansion<T, k>` and writes one; a read of two limbs passes the limbs through
  the guard and, in a build with checks, checks that they are a canonical pair
  ([SoA and its views](../reference/soa.md)).
- **`kairn::SoA<T, k>`** owns its arrays, in one allocation, each aligned to 64 bytes, and allocates
  only in the functions that say so (the constructors that take a size, the copy, `resize`).

## Four ways to loop

| | For | What is guaranteed |
|---|---|---|
| A plain loop of `Expansion<T, k>` | any data structure, one number at a time; the simplest | each operation's bound; the loop's own analysis is the program's |
| [`kairn::Packed<T, k>`](../reference/packed.md) | a loop the program writes itself, $W$ numbers at a time in SIMD registers: $W$ = 4 `double` or 8 `float` with AVX2, 2 or 4 with AArch64's Advanced SIMD, 1 elsewhere | in each lane, the statement of the operation of `Expansion` of the same name, which is proved; nothing across lanes, nothing about the loop |
| The functions on arrays of [`kairn/batch.hpp`](../reference/batch.md) | `sum`, `sum_fast`, `dot`, the maps `add`, `sub`, `scale`, `mul_pow2`, `axpy`, the coefficients of a product of polynomials `conv`, and `norm_upper`, an upper bound of the largest magnitude | each calls one generated loop whose statement is proved for every length of array and every number of lanes, in the real model and in the IEEE model |
| [`kairn::Accumulator<T, k>`](../reference/accumulator.md) | a sum or a dot product computed term by term, in an order of the program's own or in parts merged at the end | a bound for every history of additions, products and merges |

A sum, a dot product and an `axpy` over whole arrays are what the functions on arrays are for: their
bound covers the whole loop, where a loop the program writes, with `Packed` or without, has to make
its own analysis of the order it chose ([A vector loop](../tutorials/vector-loop.md) makes one).
`kairn/packed.hpp`, `kairn/soa.hpp` and `kairn/batch.hpp` are not included by `kairn/kairn.hpp`:
where the target has SIMD the first two double or triple the time it takes to compile a file that
includes `kairn/kairn.hpp`, 0.218 s instead of 0.106 s with Apple clang and 1.001 s instead of 0.318 s
with GCC 13 on AVX2 ([Packed, Compile time](../reference/packed.md#compile-time)). There is no choice of
instruction set at run time: the form of `Packed` is the one of the instruction set a file is
compiled for, and on x86-64 the AVX2 form needs `-mavx2 -mfma` or `-march=x86-64-v3`.

## How the error of a sum grows with its length

```cpp
--8<-- "docs/examples/cpp/concepts_arrays.cpp:sum"
```

```text
--8<-- "docs/examples/cpp/concepts_arrays.txt::4"
```

A sum of $n$ numbers made by $n - 1$ additions, each with a relative error of at most $e$, is proved
to be within

$$\Bigl\lvert s - \sum_i x_i\Bigr\rvert \le \bigl((1 + e)^{n-1} - 1\bigr)\sum_i\lvert x_i\rvert
\le \gamma_{n-1}(e)\sum_i\lvert x_i\rvert, \qquad \gamma_m(e) = \frac{m e}{1 - m e},$$

of the exact sum, whenever the result is finite, **in whatever order the loop adds**
([What each function states](../reference/batch.md#what-each-function-states)). In words: for
$n e$ small the bound is about $(n - 1)\,e$ times the sum of the magnitudes, so it grows linearly
with the length. $e$ is the bound of one addition: $\frac{u}{1+u}$ for one limb, $\frac{3u^2}{1-4u}$
for two, $3u^2$ for `sum_fast`. The bound is relative to $\sum_i\lvert x_i\rvert$, not to the sum:
where the terms cancel, the error relative to the sum itself is larger by the condition number
$\sum_i\lvert x_i\rvert / \lvert\sum_i x_i\rvert$, which [Accurate sums](../tutorials/accurate-sums.md)
shows on a sum that `double` gets entirely wrong. A dot product has its own statement, of the same
shape with $\sum_i\lvert x_i y_i\rvert$ and an underflow term of $\tfrac12\eta$ (one limb) or $\tfrac32\eta$
(two limbs) per term; `axpy` and the other maps claim, of each element, the bound of the operation on
one element.

**A program gets the bound as numbers of `T`** from `kairn::traits<X>`: `sum(n)` for a sum of $n$
numbers in any tree of additions, `sum_height(h)` for a tree of height $h$, and `dot(n)` for a dot
product of $n$ terms, each a `Bound` with `unit` at least $\gamma_{n-1}(e)$ (or $\gamma_n$ for a dot
product) and `tiny` for the underflow term, computed by proved kernels
([The bound as a function of the length](../reference/batch.md#the-bound-as-a-function-of-the-length)).
They are `constexpr`, with the same bits at compile time and at run time:

```cpp
--8<-- "docs/examples/cpp/concepts_arrays.cpp:growth"
```

```text
--8<-- "docs/examples/cpp/concepts_arrays.txt:5:9"
```

Beyond the lengths the kernels bound, about $n e = \tfrac14$, where the bound would be a third of the
sum of magnitudes anyway, `unit` and `tiny` are $+\infty$, which claims nothing, and a constant
expression asking for one does not compile: for one limb that is about $2^{51}$ terms of `double` and
$2^{22}$ of `float`, for two limbs of `float` about $2^{44}$, and for two limbs of `double` more than
$2^{101}$, so every length a `std::size_t` holds. These numbers are not claimed to be the smallest
bounds: `unit` exceeds $\gamma$ by a factor of about $(1 + 2x)(1 - x)$, $x = n e$, a few $u$ for short
arrays and an eighth at $x = \tfrac14$. And the bounds are inequalities between real numbers: a
program that evaluates `unit` times its own sum of magnitudes in floating point rounds the product
up (`kairn::rmul`) to keep it a bound. How the header gives the kernels the count $n$, as the smallest
number of `T` not below it, is integer code that is tested and not machine-checked
([What is not machine-checked](correctness.md#what-is-not-machine-checked)).

## The order of summation

The result of `sum`, `sum_fast` and `dot` depends on the order of their additions, and each is
computed in one of two orders, with **the same statement in both**: one theorem bounds every order
by the same expression of the length.

- **By default, the lane order** of the build's form of `Packed`: with $W$ lanes, element $i$ goes to
  lane $i \bmod W$, each lane is summed from zero, the lanes are added from lane 0 upward, and the rest
  is added in order. It is the packed loop, the fast one, and **its bits depend on the instruction
  set** the file is compiled for: the same program can give other bits with AVX2, with NEON and
  without either, each within the bound.
- **With `kairn::sequential`**, element after element. **Its bits are the same on every platform**
  and in every form of `Packed`, so a program that needs the same result everywhere asks for it.

The program above prints only the results of the sequential order, which ctest compares on every
platform; it checks those of the lane order against the bound too. In this version the tag is the
last argument of `sum`, `sum_fast` and `dot`, `kairn::sum(x, kairn::sequential)`, and the first of an
operation of ball vectors, `kairn::add(kairn::sequential, x, y, z)` (`kairn/order.hpp`). The maps write
each element from the elements of the same index alone, so their results do not depend on the order;
`norm_upper` computes the same result in every order; `conv` has the sequential order only. What is
claimed of the two orders is the statement, not the bits: that they agree where they do is not
claimed.

## Finite results, and arrays in place

A function that returns a number returns a `kairn::Reduction`, the number and a flag `finite`, true
exactly when the number is finite; when it is false the number is the canonical NaN, every limb a
NaN, never a finite wrong value. A map returns `true` exactly when every element it wrote is finite.
A map may write in place, into exactly the arrays it reads (`axpy(a, x, y, y)` is
$y \leftarrow ax + y$); no other overlap is supported. Every value the loops add passes through the
guard, so arrays the program fills with products in the same function may be passed straight in
([The floating-point environment](environment.md#contraction-and-fast-math)). With `KAIRN_CHECKS`
each function checks the environment, the lengths, the arrays that alias and its elements
([Functions on arrays](../reference/batch.md#checks)).

## The accumulator

For a sum that no function computes, or one computed in parts:

```cpp
--8<-- "docs/examples/cpp/concepts_arrays.cpp:accumulator"
```

```text
--8<-- "docs/examples/cpp/concepts_arrays.txt:11:12"
```

An accumulator holds a running sum of $k$ limbs, the running sum in `T` of the magnitudes of what was
added, and the count. `add`, `add_product` and `merge` are proved kernels, and **what is proved is a
bound for every history** of them, a merge being a node of the summation tree: whenever the running
sum is finite and the masks of the kernels of the radius are true, the sum is within `error_bound()`
of the exact sum of what was added, whatever the order, and `ball()` is the ball of the two
([What is proved](../reference/accumulator.md#what-is-proved)). So a program can sum in parallel,
one accumulator per thread, and merge at the end. A radius is given up to about $2^{22}$ terms of
`float` and $2^{51}$ of `double`, for one limb and two, since the magnitudes are summed in `T`;
beyond, and when something is not finite, `error_bound()` is $+\infty$ and `ball()` the whole line,
never a finite ball the theorem does not give. The count, its conversion to `T` and those returns are
the header's, tested and not machine-checked
([What the header adds](../reference/accumulator.md#what-the-header-adds-which-is-not-machine-checked)).

## What they cost

**Not measured yet.** The functions on arrays, the ball vectors and the accumulator have not been
benchmarked: their benchmarks are still to come
([Benchmarks, Milestone 2](../developer/results/bench-milestone2.md#still-to-come)). What has been
measured is the operations they are made of ([Precision and magnitude](precision.md),
[Intervals, balls and ball vectors](enclosures.md#what-they-cost-and-how-wide-they-are)) and the
compile time of the headers (above).

## Not provided

A product of an array of two limbs by a two-limb scalar without an addition (`axpy` with `y` zero
computes it, with the bound of `axpy`); an order of a number of lanes other than the build's;
constant evaluation of the functions on arrays; a packed `Ball` or `Interval`; the reduction of the
lanes of a `Packed` (a program writes it, in the order it chooses). The tutorial
[Sums and dot products of arrays](../tutorials/arrays.md) uses the functions on arrays and the
accumulator on longer data, and checks each result against its bound in exact arithmetic.
