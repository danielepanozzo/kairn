# What "correct" means here

Kairn's results are rounded: a product of two-limb numbers is in general not the exact product,
and a ball is in general wider than the exact set it encloses. What Kairn guarantees is a statement
about how far a result can be from the exact one, or that a set contains it, proved for the kernel
each operation calls, with the exceptions listed below. This page says what the kinds of statement
are and how to read one, how each is established, in which model it is proved, what is not
machine-checked, and what *unverified* means.

## An example: a product and its bound

```cpp
--8<-- "docs/examples/cpp/concepts_correctness.cpp:bound"
```

```text
--8<-- "docs/examples/cpp/concepts_correctness.txt::3"
```

The product of two two-limb numbers is proved to be within $4u^2\lvert xy\rvert + \tfrac32\eta$ of
the exact product $xy$, with $u = 2^{-53}$ and $\eta = 2^{-1074}$
([`mul_2_2_full`](../reference/mul_2_2_full.md), whose finite results are those of its core
[`mul_2_2`](../reference/mul_2_2.md)). The operands here are chosen so that the exact product is a
sum of eight powers of two, which the program compares with the result: the result is all of it
but the last, $2^{-170}$, an error far below the bound. A bound is a worst case over every pair of
operands, not an estimate of the error of a given one. The program is
[`docs/examples/cpp/concepts_correctness.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_correctness.cpp)
(ctest: `api.example.concepts_correctness`).

## Three kinds of statement

**Containment**, for sets. The result of an operation on intervals, balls or ball vectors contains
the exact result for every choice of members of the operands: if $x \in X$ and $y \in Y$ then
$x \circ y \in X \circ Y$. It holds in every case, unbounded sets and the empty set included, the
whole line being an answer that contains everything
([Intervals, balls and ball vectors](enclosures.md#what-each-stores-and-guarantees)):

```cpp
--8<-- "docs/examples/cpp/concepts_correctness.cpp:ball"
```

```text
--8<-- "docs/examples/cpp/concepts_correctness.txt:4:4"
```

The center is the product above and the radius, about $2^{-104}$, covers its error bound: the ball
contains $xy$, whose distance to the center is $2^{-170}$.

**Error bounds**, for numbers. A bound formula has the shape

$$\lvert z - v\rvert \le c\,u^k\,\lvert v\rvert + t\,\eta,$$

$z$ the result and $v$ the exact value. The first term is relative: the result has about
$k\,p - \log_2 c$ correct bits, $p$ the precision of `T`. The second is absolute and only matters
near the bottom of the range, where a number has fewer bits ([Precision and magnitude](precision.md)).
A few bounds are relative to something else, and say so: the fast addition to the operands,
$\lvert x\rvert + \lvert y\rvert$, and the functions on arrays to the magnitudes of the terms,
$\sum_i\lvert x_i\rvert$ ([Arrays](arrays.md)). Each bound is an inequality between real numbers.
`kairn::traits<X>` exports its two constants as numbers of `T` rounded up, `unit` $\ge c\,u^k$ and
`tiny` $\ge t\,\eta$, with `reference` saying what `unit` multiplies; a program that evaluates the
right side in floating point rounds it up too (`kairn::radd`, `kairn::rmul`,
[Building blocks](../getting-started/index.md#building-blocks)).

**Tightness**, how close the result is claimed to be to the best possible one. Kairn claims it
where it can and says where it does not:

- an interval of one limb: the exact bounds rounded outward, the tightest interval of `T`, for sums
  and differences, and for products but in the underflow range, where a bound may be one number of
  `T` further; of two limbs: each bound within a stated $A\lvert v\rvert + B$ of the exact one
  ([What holds today, Intervals](../getting-started/guarantees.md#intervals));
- a ball, a ball vector: no tightness is claimed of the radius, only containment; nor that the hull
  and the intersection of balls are the smallest balls that contain what they must, nor that
  `split()` splits at the midpoint
  ([One enclosure interface](../reference/enclosure.md#what-is-exact-what-is-certain-what-is-not-claimed));
- the conditions under which a result is claimed finite are sufficient, not necessary
  ([Precision and magnitude](precision.md#the-four-types));
- a bound itself is not claimed to be the smallest that holds. Each reference page shows, under
  *Measured*, the largest ratio of error to bound that the brute-force runs found, and whether the
  bound was attained in some format, in which case no smaller constant can be proved for it
  ([How to read a page](../reference/reading.md#what-the-measured-numbers-are)).

## How a guarantee is established

**A description, a statement and a proof.** Each operation is computed by one *kernel*, a short
straight-line sequence of operations of `T` written once as a description in the generator
(`gen/kernels/`). From that one description the generator prints the C++ of the headers, a formal
model of the kernel for the proof assistant Rocq, and the statement of its claims, which are also
in `gen/claims.json`. A kernel is *proved* when Rocq accepts a theorem whose type is exactly that
generated statement, and an audit finds that its proof uses no axiom beyond four allowed ones of
Rocq's standard library ([How to read a page](../reference/reading.md#what-proved-means);
[Proofs](../proofs/index.md) says how to check them yourself). The proof is about a model printed
from the same description as the C++, not about a transcription of the code made by hand; that the
two printings agree rests on the generator, which the next paragraph's checks test.

**An independent check of the compiled code.** A proof does not cover the generator that prints
both, the compiler that compiles the C++, or the hardware. For those, an *oracle*, a program that
shares no code with the library or the generator, computes in exact rational arithmetic and judges
results against the claims: of every kernel as compiled with the build's compiler, scalar and
packed, under each contraction setting, and of every public operation through the constructors
and operators a program calls, on random operands that include the hard cases (cancellation, ties,
underflow, overflow, infinities and NaN). Those checks run in every build's tests and, with far
more cases, in the brute-force runs on the test machines
([Testing](../developer/testing.md), [the pipeline](../developer/architecture.md#the-pipeline)).
`kairn::self_test()` checks, in a program itself, the last two links: the compiler's flags and the
hardware ([The floating-point environment](environment.md)).

## What is proved in which model

A statement is stated, and proved, in one of two models, or both
([Proofs](../proofs/index.md#what-is-proved-and-in-which-model)); those of the opt-in round-up
interval in the second only, with the status that `gen/claims.json` gives each:

- **The model of real numbers.** Every operation rounds its exact result to nearest, with gradual
  underflow, in a binary format of any precision from the kernel's minimum on and with no largest
  exponent, so nothing overflows. Every error bound, normalization, exact comparison, rounding and
  ball containment is proved here. For `float` and `double` it is the guarantee whenever nothing
  inside the operation overflows.
- **The model of IEEE values** (Flocq's model of IEEE 754): values overflow, and can be infinite or
  NaN. What the operations return at overflow and for infinities and NaN is proved here (F1 to F5 of
  the numbers, B1 to B4 of the balls), and so are the intervals and the interface intervals and
  balls share, whose statements are stated in this model only, since infinite bounds are ordinary
  values of an interval; and the functions on arrays and the ball vectors, whose loops are proved
  in both models, in each order they are computed in.
- **The kernels of the round-up interval** (the opt-in `kairn/upward.hpp`,
  [The round-up interval](upward.md)) are stated in the model of IEEE values only, with their sums
  and products rounded upward, toward $+\infty$ (Flocq's `Bplus` and `Bmult` with `mode_UP`), in
  files of their own (`proofs/gen/UpwardStatements.v`); no operation of theirs rounds to nearest.
  The status of each statement is the one `gen/claims.json` gives, on its reference page
  ([The round-up interval: its kernels](../reference/upward.md#the-model)).

Not every kernel has a statement in both. A note of the design page, dated 2026-11-21, counts them
for the 160 kernels and 44 loops of Milestone 2
([Milestone 2 statements](../developer/design/milestone2.md), at the top): 101 kernels have their
generated statement proved in the IEEE model (86 in that model only, 15 in both); of the 59 stated
in the real model, 34 also have generated statements for finite operands proved in the IEEE model
(that the result is the real model's whenever it is finite), 9 have theorems written by hand there
instead, 5 have only the theorems that the computation at compile time gives the values of the
computation at run time, and 11 have no theorem of their own in the IEEE model (`two_sum_entry`,
the kernel of the public `two_sum`, stated for finite operands, and parts of loops whose theorems in
that model use them); and every loop is proved in both models. The tree has grown since the note
was counted: [the reference](../reference/index.md) counts the kernels of `gen/claims.json` as they
are now, and gives the status of each.

## What is not machine-checked

What the program relies on and no Rocq theorem states, as
[What holds today](../getting-started/guarantees.md) lists it. Each is specified, argued where it
is written, and tested, often in exact arithmetic:

- **`ldexp` beyond the powers of two of `T`** ($n$ above 1023 or below $-1074$ for `double`): the
  header calls the proved kernel two or three times; that scaling up gives $2^n x$ exactly or
  $(\pm\infty, 0)$, and scaling down stays within $\eta$, is argued, as is that `ldexp` of one limb
  gives $\mathrm{RN}(2^n x)$, and, for a ball and a ball vector, that the steps may stop at
  $n = \pm 2098$ or so for `double`. The same for `Packed`
  ([Overflow and non-finite values](../getting-started/guarantees.md#overflow-and-non-finite-values)).
- **`kairn::rational` and `kairn::integer`**, integer code written by hand, specified exactly bit for
  bit, tested for equality with the oracle and checked against its specification for every constant
  computed at compile time; and with them, that the ball `Ball<T, k>(q)` of such a constant contains
  the fraction ([Constants from fractions](../reference/rational.md)).
- **A few compositions of proved kernels** in the headers, each argued from the claims of the
  kernels it composes and not proved as one statement: the constructor of an interval of two limbs
  from two values of `T` (`Interval<T, 2>(lo, hi)`, and `Interval<T, 2>::from_bounds(lo, hi)`, the
  same constructor under another name) and the member test of a point of `T` in an interval or a
  ball of two limbs, each `make_2` (which gives the point exactly) followed by the operation of two
  limbs ([Compositions](../reference/enclosure.md#compositions)); `from_limbs` of an interval and of
  a ball, each limb through the guard of `make_2` or `make_2_limbs`
  ([Limbs](../reference/enclosure.md#limbs)); and, for ball vectors, `axpy` (a scaling, then a sum)
  and `norm_upper` (the bound of the centers, then the radius added)
  ([Compositions made in the header](../reference/ball_vector.md#compositions-made-in-the-header)).
- **The integer bookkeeping of the bounds of arrays and of the accumulator**: the count $n$ given to
  the kernels of `traits<X>::sum(n)` and `dot(n)` as the smallest number of `T` not below it; the
  accumulator's count, which saturates at $2^{64} - 1$, its conversion to `T`, and what it returns
  when a mask of its kernels is false or a value is not finite (no bound, never a finite one the
  theorem does not give) ([The bound as a function of the length](../reference/batch.md#the-bound-as-a-function-of-the-length),
  [The accumulator](../reference/accumulator.md#what-the-header-adds-which-is-not-machine-checked)).
- **Tests of bit patterns written by hand**, with no kernel: `sign`, `isfinite`, `is_normalized`,
  the states of a ball (`is_finite()`, `is_whole()`, `is_empty()`), `is_finite()` of an interval
  (both bounds finite, tested on the bit patterns of their leading limbs), and the limbs of a number
  and the bounds of an interval, read as stored.
- **Thresholds sharper than those stated**: a condition under which a result is claimed finite is
  proved as stated, and how far it is from where an overflow is first seen is measured, not proved.
- **That each operation of the round-up interval that rounds runs as the IEEE operation rounded
  upward.** The statements of its kernels are about `add_ru` and `mul_ru`, IEEE 754's sum and
  product rounded toward $+\infty$, and about a maximum `max_nl` that each of two machine
  instructions computes on quiet NaNs. That the compiled code computes them so, in the format of
  `T` and on the values the listing names, is assumed. It holds when the program sets the mode
  through the header's scopes, which make it upward with flush to zero and denormals-are-zero off,
  and compiles with the header's options, which with the header's barriers (on MSVC a barrier per
  scope, whose assurance is weaker) make the compiler emit the operations as written inside the
  scope ([What the program guarantees](upward.md#what-the-program-guarantees)). The options are the
  program's responsibility, by the owner's decision of 2026-11-24; the header's self-check and the
  assertions of a checked build are evidence of the rest, not a proof of it
  ([The self-check](upward.md#the-self-check)).

One more thing is not machine-checked, by design: that what Kairn states of the functions named
after IEEE 1788 is the standard's meaning. Each statement is proved as it is written; that it is
what the standard means is a reading of its text and of drafts and public test cases
([Milestone 2 statements](../developer/design/milestone2.md#in-short);
[IEEE 1788](../reference/enclosure.md#ieee-1788) says where Kairn departs from it).

And, for every statement, the links a proof does not cover: that the generator prints the C++ and
the model faithfully, that the compiler keeps the C++ as written, and that the hardware rounds as
IEEE 754 says ([What a proof does not cover](../proofs/index.md#what-a-proof-does-not-cover)). The
oracle's cross-checks and `kairn::self_test()` are aimed at those.

## Unverified

A kernel's status is in `gen/claims.json`: *proved*, or **UNVERIFIED**, a kernel whose statement is
a target, tested by the oracle in exact arithmetic but not proved. An operation whose kernel is
UNVERIFIED compiles only when one of its operands carries the marker `kairn::unverified(...)`, so
that every unproved step of a computation is visible in the source, and its entry in
`kairn::traits` has `verified == false` and no constants, so that no client bound can be built on a
number that is only a target; its measured errors are reported as measurements, never as bounds
([Proved, and UNVERIFIED](../getting-started/guarantees.md#proved-and-unverified)). The marker is
also accepted on proved operations, where it changes nothing, so that code written with it keeps
compiling when a proof lands. The functions on arrays, the operations of ball vectors and `Packed`
have no marked form: each compiles only while its kernels are proved.

**In this version every kernel of the default types is proved**, so none of their operations needs
the marker; [the reference](../reference/index.md) gives the status of every kernel, those of the
opt-in round-up interval included. A program can ask all the same, at compile time:

```cpp
--8<-- "docs/examples/cpp/concepts_correctness.cpp:has_sum"
```

```cpp
--8<-- "docs/examples/cpp/concepts_correctness.cpp:ask"
```

```text
--8<-- "docs/examples/cpp/concepts_correctness.txt:5:6"
```

`kairn::traits<X>::mul.verified` and the other entries are constants; `traits<X>::sum(n)` and
`dot(n)` are a `Bound` only while their kernels are proved; and since a function on arrays compiles
only while the loop it calls is proved, a test of whether a call compiles, as `has_sum` above, is
that loop's status. The statuses the headers read are in the generated header
`kairn/gen/bounds.hpp`, written from `gen/claims.json`, which is not an interface to call directly.
