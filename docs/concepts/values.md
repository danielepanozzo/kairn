# Values, threads and constant expressions

Kairn's numbers and sets are meant to be used the way `double` is: copied, stored in arrays and in a
program's own structures, sent through buffers, computed in several threads, and, where C++ allows
it, computed by the compiler. This page says what the headers and their tests establish of each,
and where the value computed at compile time can differ from the one computed at run time.

## Plain values

```cpp
--8<-- "docs/examples/cpp/concepts_values.cpp:values"
```

```text
--8<-- "docs/examples/cpp/concepts_values.txt::1"
```

`Expansion<T, k>`, `Ball<T, k>` and `Interval<T, k>` are trivially copyable; the numbers, the balls
of two limbs and the intervals are also asserted to be standard-layout and of exactly the size of
their limbs, $k$ for a number, 3 for a ball of two limbs, $2k$ for an interval
(`tests/api/constexpr.cpp`, `api.constexpr`). Of that size, they have no room for a pointer, so they
hold no heap memory, and a copy of their bytes is a copy of the value, which is what the program
above does. The same holds of the other types, each by its own tests: `BallVector<T, k, N>` (trivially copyable, standard-layout,
$kN + 1$ numbers of `T`; [Ball vectors](../reference/ball_vector.md#regular-type)), `Packed<T, k>`
and `PackedMask<T>` ($k$ registers; [Packed](../reference/packed.md#regular-type)), the views of
arrays, and `Accumulator<T, k>` ([The accumulator](../reference/accumulator.md#checks-and-constant-evaluation)).
`SoA<T, k>` is the one type that owns memory: it allocates its arrays, in one block, in the
functions that say so ([SoA](../reference/soa.md#soa)).

The value types default-construct to zero: `Expansion()` is 0, `Ball()` the point 0, `Interval()` the
interval $[0, 0]$, `BallVector()` the point 0 of $N$ entries, `Accumulator()` the empty sum. The
limbs of a number are public (`x.limb[i]`); a program that writes them must write a canonical pair,
and `Expansion<T, 2>::from_limbs(p)` builds a number from computed limbs with the guard and, in a
build with checks, the check ([Numbers of several limbs](expansions.md#normalized-numbers)).

**A set is rebuilt from the limbs read out of it with `from_limbs`**, for a program that keeps the
limbs in storage of its own:

```cpp
--8<-- "docs/examples/cpp/concepts_values.cpp:limbs"
```

```text
--8<-- "docs/examples/cpp/concepts_values.txt:2:3"
```

`Interval<T, k>::from_limbs(p)` takes the $k$ limbs of the lower bound, most significant first, then
those of the upper bound, as `X.lower().limb[i]` and `X.upper().limb[i]` read them;
`Ball<T, k>::from_limbs(p)` the $k$ limbs of the center, then the radius, as `X.center().limb[i]`
and `X.radius()` read them. Its contract is that of `Expansion<T, 2>::from_limbs`
([Limbs](../reference/enclosure.md#limbs), and the comments of `kairn/interval.hpp` and
`kairn/ball.hpp`):

- **The limbs must be those of a canonical set**, as an operation of Kairn returns it: for an
  interval the empty set $(+\infty, -\infty)$ or bounds $lo \le hi$, neither a NaN, with
  $lo < +\infty$ and $hi > -\infty$, each of two limbs a canonical pair; for a ball a finite ball
  (a finite center, canonical for two limbs, and a finite radius $r \ge 0$), the whole line or the
  empty set. In a build with checks (`KAIRN_CHECKS` 1) the environment is checked first, the
  rounding mode included, then the limbs, and limbs of no canonical set stop the program, or make a
  constant expression invalid. **In a release build (`KAIRN_CHECKS` 0) nothing is checked**: such
  limbs give a set with no guarantee for what is computed from it, and no undefined behavior.
- **Each limb passes through a guard** before an operation can add it, that of `make_2` for a value
  of `T` and that of `make_2_limbs` for a pair, so the limbs may be products the program computed.
  That the result is the set given is argued from the claims of those two kernels, not proved as
  one statement ([What is not machine-checked](correctness.md#what-is-not-machine-checked)).
- **The round trip**, `from_limbs` of the limbs read, gives every limb back bit for bit but for two
  things: a $-0$ may come back $+0$ (the guard computes $-0 + 0$, which is $+0$ under rounding to
  nearest; in constant evaluation the guard is not applied, and the $-0$ stays), and a NaN limb of the
  empty ball comes back a NaN whose payload Kairn does not specify.

The constructor is not the way back for a ball: `Ball<T, k>(c, r)` of the NaN center and radius of
the empty set makes the whole line, as it makes of every center that is not finite and every NaN
radius ([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)), and the
program above shows it. An accumulator is rebuilt with `Accumulator<T, k>::from_state(s, a, n)`,
whose bound is that of the history its state was read from.

## Threads

Kairn's design has no global mutable state and no lazily initialized tables, and an operation writes
nothing but its result; `kairn::environment_ok()` and `kairn::self_test()` only read
([Library](../developer/design/phase0/library.md#api-sketch), at its end; the reference pages of
[Packed](../reference/packed.md#regular-type) and [ball vectors](../reference/ball_vector.md#regular-type)
state it of their headers). So:

- **Operations on different objects may run in several threads at once**, and several threads may
  read the same object while none writes it, under the ordinary rules of C++ for the program's own
  objects. Kairn's values have no internal state to protect: a `Ball` is three numbers.
- **A sum computed in parallel** is what the accumulator is for: one `kairn::Accumulator` per
  thread, merged at the end in any order; its error bound holds for every history of additions and
  merges, the tree the program made ([The accumulator](../reference/accumulator.md#what-is-proved)).
- **The floating-point environment is the calling thread's**: `kairn::environment_ok()`, the check
  that every function on arrays and every operation on whole ball vectors makes in every build, and
  the checks of `KAIRN_CHECKS` read the control register as the thread that calls them sees it. A
  program that changes the rounding mode or flush to zero in a thread checks and restores it in that
  thread ([The floating-point environment](environment.md)).

No test of the repository runs Kairn from several threads: what is said here follows from the
design and from what the headers are (functions of their operands, values without pointers), not
from a measurement.

## Constant expressions

Much of Kairn is `constexpr`, so a program can build its constants at compile time:

```cpp
--8<-- "docs/examples/cpp/concepts_values.cpp:constexpr"
```

```text
--8<-- "docs/examples/cpp/concepts_values.txt:4:5"
```

What can be computed at compile time ([Constant evaluation](../getting-started/guarantees.md#constant-evaluation)
has the complete list):

- **Numbers**: the constructors, the sums and differences of two limbs, `ldexp` and `half` of two
  limbs and `kairn::finite::ldexp` (their kernels compute only products that constant evaluation
  computes with the same values, and the steps beyond the powers of two of `T` are integer
  bookkeeping), negation and absolute value, the comparisons and the conversions, every operation of
  one limb, and `kairn::finite::add`, `sub` and `add_fast`; `kairn::rational` and `kairn::integer`,
  which compute with integers only and give the same bits at compile time and at run time.
- **Sets**: the constructors and states of intervals and balls, a ball's negation and sign
  predicates, the ball of a constant; of intervals the bounds, the negation, the hull, the
  intersection, the predicates, the member and subset tests, the three-valued comparisons, the
  relations of IEEE 1788 and the split, and of one limb the midpoint, the radius and the
  conversions; of balls the functions of the shared interface, all but the split for one limb, and
  for two `lower_as`, `upper_as`, `midpoint`, `mid_rad`, the signs, `from_interval`, `from_bounds`
  and the narrowing to one limb; and of both types, every number of limbs, `from_bounds`,
  `from_limbs` and `is_finite()`.
- **The building blocks** but `mul_down` and `mul_up`; the bounds as functions of the length,
  `kairn::traits<X>::sum(n)` and `dot(n)`, with the same bits as at run time; and of the accumulator
  the constructor, `add`, `merge`, `sum()`, the accessors and `from_state`.

Not at compile time: the products of two limbs, `ldexp` and `half` of balls, the arithmetic of
balls and intervals, `mul_down` and `mul_up` (by design: their statements are about the
fused product), the functions on arrays, the operations of `Packed` and of ball vectors, and the
accumulator's `add_product`, `error_bound()` and `ball()`. Some special values are not constant
expressions though their functions are `constexpr` (the midpoint and the split of the empty set, the
bounds of the empty ball and of the whole line, whose listings compute a NaN or $\infty - \infty$
before selecting their result), and GCC and Clang refuse at compile time an operation that produces
an infinity from finite operands, or a NaN, which is evaluated as stated at run time.

**Where the value at compile time can differ.** "The same values" means the result of run time but
for the sign of a zero: in constant evaluation the guard is not applied, since nothing is fused
there, so a $-0$ keeps its sign, and Kairn leaves the sign of a zero unspecified anyway. The one
building block whose values can differ is `two_prod(a, b)`, the product rounded and its error term.
At run time the error term comes from a fused multiply-add, which C++20 cannot evaluate at compile
time; in constant evaluation it comes from Dekker's product, another algorithm, proved on its own
([`two_prod`](../reference/two_prod.md), [`two_prod_dekker`](../reference/two_prod_dekker.md)):

```cpp
--8<-- "docs/examples/cpp/concepts_values.cpp:two_prod"
```

```text
--8<-- "docs/examples/cpp/concepts_values.txt:6:7"
```

- When the product is zero or at least $2^{2p-1}\eta$ in magnitude ($2^{-969}$ for `double`,
  $2^{-102}$ for `float`), both error terms are exact, so wherever `two_prod` is a constant expression
  both executions give the same values.
- Below that threshold each error term is within its own bound of the exact one, $\tfrac12\eta$ at
  run time and $\tfrac{13}{8}\eta$ at compile time, and the two can differ: the program checks only
  that they are within $2\eta$ of each other, which the two bounds imply.
- Where an operation of Dekker's product would overflow (the product of the leading halves can
  overflow where $ab$ does not), `two_prod` is not a constant expression: a program that needs one
  does not compile, and the compiler's message names `two_prod_overflows_in_constant_evaluation`
  (with GCC, the operation that overflowed). It is one when $\lvert a\rvert, \lvert b\rvert \le 2^{996}$
  and $\lvert ab\rvert \le 2^{1023}$ ($2^{115}$ and $2^{127}$ for `float`), a sufficient condition,
  not an exact one ([Constant evaluation](../getting-started/guarantees.md#constant-evaluation)).
