# Milestone 2 report

**Status: complete, with the deviations and open issues listed below; reviewed by the owner on
2026-11-23 ([the owner's review](#the-owners-review), at the end, has each decision and what
changed after it).** Milestone 2 is the second row of the [plan](../design/phase0/plan.md#milestones): intervals, one interface shared by
intervals and balls, the building blocks as public functions, constants built at compile time,
vectors of balls with one radius and the functions on arrays, the packed type and the containers,
and an exhaustive tier of tests on small emulated formats. It ends when the first client's ball
path can be written against it. This page says what exists, what is proved, what the tests and the
benchmarks measured, what an audit found, and what is open. Each section links to the page that
has the details.

As for Milestone 1, an audit against the brief was made before this report, and it found
requirements that were neither met nor flagged: the exhaustive tier and the Concepts pages did not
exist, and the quick tier had outgrown its two minutes
([what the audit found](#what-an-audit-against-the-brief-found)). The first two were then built;
the third is a deviation. One guarantee of Milestone 1 was found to have a hole, and was repaired
([the factors of a fused operation](#a-hole-in-a-guarantee-of-milestone-1)).

## In short

- **Everything the plan lists for this milestone exists and is public**, for `float` and `double`
  limbs, one and two limbs: `Interval<T, k>`; the enclosure interface on `Interval` and `Ball`;
  the building blocks; `rational` and `integer`; `BallVector<T, k, N>`, the functions on arrays
  and the accumulator; `Packed<T, k>` and the containers in structure-of-arrays form. The version
  is 0.3.0. Two items moved to Milestone 3, both flagged: the conversions between limb types, and
  the flush-to-zero variant of the exhaustive tier.
- **Every kernel and every loop that ships has its statements proved.** 237 kernels and 51 loops
  over arrays (63 kernels at the end of Milestone 1), 1 563 theorems checked by Rocq with Flocq, the
  same four axioms, no admitted statement. Not every kernel is proved in both models: the
  [table](#bounds-proven) says which statements exist for which group.
- **The proofs found five statements false before anything shipped with them**, and the tests two
  more faults of the same kind; each was restated or repaired and proved
  ([below](#statements-found-false)).
- **A hole in a guarantee of Milestone 1 was found and closed.** With `-ffp-contract=fast`, Clang
  fused a product written by the program into `two_prod`, `mul_down`, `mul_up`, a product of a
  two-limb number by a `T`, and others, when the other factor was 1 or −1. The rule that guards
  values entering from the program was made strict, by the owner's decision; every public
  operation now passes; the price is one addition per factor at entry.
- **No claim was violated by any test.** The brute-force runs judged 25.1 billion results of the
  compiled kernels and loops on three machines with five compilers, and 2.3 billion of the
  generator's interpreter on every operand of 1 296 small formats; the exhaustive tier judged 1.2
  billion lines of the compiled kernels on formats of 8 to 11 bits; what the last change of the
  milestone added or changed was run again on the final code, 1.2 billion results. The runs
  found faults in the tests themselves (five, fixed), none in a statement or in the code
  ([below](#brute-force-results)).
- **Defects of compilers were found by the tests** (nine) and worked around, two of them
  miscompilations by MSVC reduced to programs that include no Kairn header
  ([below](#defects-of-compilers-found)).
- **What it costs.** A directed operation without changing the rounding mode costs 4.5 to 11
  plain operations in a loop. An interval of one limb costs 2.3 to 3.2 balls for a sum and 5.6 to
  10 for a product, for an enclosure up to 11% narrower. In a bisection written once for the four
  enclosure types, `Ball<double, 1>` is the fastest, an interval of one limb takes 1.6 to 3.9
  times as long for zeros up to six times narrower, a ball of two limbs 3.5 to 4.3 times for 30
  digits, an interval of two limbs 21 to 31 times. The packed type takes 0.25 to 0.37 of a scalar
  loop with four lanes and GCC, and gains nothing with Clang 18, which vectorizes the scalar loop
  itself. An accurate `sum` or `dot` of two limbs costs 1.7 to 1.8 times a compensated sum in
  the default order on the x86-64 machine (4.5 to 4.9 on the Mac, whose registers hold two
  lanes), for an error 3 to 900 times smaller on ill-conditioned data. A ball vector pays from
  about 16 entries: on the x86-64 machine 2 to 4 times faster than as many balls there, 3.3 to
  6.2 times at 64.
- **The first client's ball path is written against it**, in two draft pull requests: the first
  with a ball of two limbs per coefficient, the second with one radius per polynomial. The second
  gives the same answers and is faster, but its radii are larger than they need be, because the
  client's polynomial is a ball with one weight per coefficient, which `BallVector` cannot hold
  ([what the client needs](#what-the-first-client-needs-next)).
- **Not machine-checked**, each stated where it appears: `rational` and `integer` (deviation 22)
  and the ball of such a constant; a few compositions of two proved kernels in the headers; the
  tests of bit patterns written by hand; that the one radius of a ball vector is the largest of
  the radii its entries would have (measured, not claimed).
- **Nine decisions were the owner's**, and are listed at the end; **21 rulings were taken
  without the owner** while the work ran, each logged, and are listed after them for
  confirmation.

## What is done

| The plan asks for | State |
|---|---|
| `Interval` | `Interval<T, 1>` and `Interval<T, 2>` (`kairn/interval.hpp`): bounds rounded outward without changing the rounding mode; $+$, $-$, $\times$, negation; the empty set and the whole line; unbounded intervals. 33 kernels of interval arithmetic and 26 of predicates, comparisons and relations |
| One enclosure interface shared by `Interval` and `Ball` | `kairn/enclosure.hpp` and members of both types: `is_empty`, `is_whole`, `is_finite`, the signs, `contains` of a point and of a set; three-valued comparisons (`less`, `less_equal`, `equal`, ... returning `Trit`), `member`; the relations of IEEE 1788.1 on intervals (`kairn::ieee1788::equal`, `subset`, `interior`, `disjoint`); `hull`, `intersection`, `split`; `midpoint`, `radius`, `mid_rad`; conversions both ways; `from_bounds` on both types; `from_limbs`. An algorithm written once runs over both ([tutorial](../../tutorials/bisection.md)) |
| The building blocks as public functions | `kairn/blocks.hpp`: `two_sum`, `fast_two_sum`, `two_prod`, sums and products rounded down and up, `next_up`, `next_down`, 13 functions |
| Numbers built at compile time from an integer or a rational | `kairn::integer`, `kairn::rational`, `Ball(Constant)`; integer code, specified exactly and tested, not machine-checked (deviation 22) |
| `BallVector` and the batch kernels | `kairn/ball_vector.hpp`: `BallVector<T, k, N>`, `BallVectorView<T, k>`: negation, sum, difference, scaling by a `T`, exact scaling by a power of two, `axpy`, the product of polynomials, `norm_upper`. `kairn/batch.hpp`: `sum`, `sum_fast`, `dot`, `add`, `sub`, `scale`, `mul_pow2`, `axpy`, `conv`, `norm_upper`, in the build's lane order or in the sequential order (`kairn::sequential`). `kairn/accumulator.hpp`: `Accumulator<T, k>` with `add`, `add_product`, `merge`, a bound and a ball. The bounds as functions of the length: `traits<X>::sum(n)`, `sum_height(h)`, `dot(n)` |
| Containers in structure-of-arrays form and the packed SIMD type | `kairn/soa.hpp` (`SoA`, `SoAView`, `SoARef`) and `kairn/packed.hpp` (`Packed<T, k>`: AVX2, NEON, or one lane) |
| Exhaustive tests on small emulated formats | `tests/emulated/`: the C++ the generator prints, instantiated on a test-only number type of integer arithmetic in a format chosen at run time; formats of 8 to 11 bits; gradual underflow only (the flush-to-zero variant: Milestone 3, deviation 27) |
| Each cross-check of the quick tier in one process | Done ([Testing](../testing.md)) |
| The first client's ball path written against it | Two draft pull requests to the client ([below](#what-the-first-client-needs-next)) |

Added beyond the plan, because the work showed they were needed:

- **The strict rule for factors** ([below](#a-hole-in-a-guarantee-of-milestone-1)).
- **The two executions of a kernel.** A kernel that a constant expression can reach runs other C++
  there than at run time (no fused instruction, no guard). For 66 kernels it is now proved that
  both give the same values; `two_prod`, whose constant evaluation is another algorithm, refuses to
  compile where the two would differ.
- **A check of the floating-point environment at the entry of every function on arrays**, in every
  build, which the brief asks and the first version of the headers did only in debug builds.
- **A non-finite value from the program never makes the empty set**: a NaN bound, a NaN radius, an
  interval of an infinite point are the whole line (the owner's decisions; deviation 23).
- **The Concepts section of the site** and the pages of Milestone 1's concepts with it, which the
  brief asked of each milestone and Milestone 1 had not shipped.

## Bounds proven

What is proved of each group of operations of this milestone. $u$ is the unit roundoff of `T`,
$\eta$ its smallest positive number, $\Omega$ its largest finite one, $v$ the exact result; "the
threshold" is the overflow threshold $2^{e_{\max}}$ ($2^{1024}$ for `double`). The bounds of the
operations of Milestone 1 (sums and products of one and two limbs, the balls) are in
[its report](milestone1.md#bounds-proven) and did not change. Each row links to the page that gives
the statement in full; each kernel's reference page names its theorem and file.

| Operations | What is proved | Stated in |
|---|---|---|
| The building blocks: `two_sum`, `fast_two_sum`, `two_prod` | the two outputs are the rounded result and its error: their sum is the exact sum, and the exact product when it is zero or at least $\eta/(2u^2)$ in magnitude (always within $\tfrac12\eta$ of it); stated for finite operands | [Guarantees](../../getting-started/guarantees.md#the-operations), the kernels' pages |
| Sums and products rounded down and up (`add_down`, ..., `mul_up`), `next_up`, `next_down`; `radd`, `rmul` for a program's own bounds | sums and differences: the exact result rounded in that direction, for every operand, infinities included; products: the same outside the underflow range, and there that rounding or one number of `T` further; the neighbors on every input | the kernels' pages |
| `Interval<T, 1>`: $+$, $-$, $\times$, negation | canonical; empty exactly when an operand is; contains $x \circ y$ for every member, unbounded operands included; sums: the tightest interval of `T`; products: the tightest when no product of bounds is in the underflow range, otherwise at most one number of `T` wider on a side; bounded exactly when the exact range is within $\Omega$ | [Guarantees, Intervals](../../getting-started/guarantees.md#intervals) |
| `Interval<T, 2>`: the same | canonical, empty, containment as above; each bound within $A\lvert v\rvert + B$ of the exact bound, $A$ about $8u^2$ (sums) and $10u^2$ (products); a zero bound of a sum stays zero; bounded when the exact range is within a quarter of the threshold | the same |
| Hull and intersection of intervals; the predicates, `contains`, the three-valued comparisons and the four relations of IEEE 1788 on intervals | exact, for every canonical operand, the empty set and unbounded intervals included | [One enclosure interface](../../reference/enclosure.md#what-is-exact-what-is-certain-what-is-not-claimed) |
| Midpoint and radius of an interval; `split` | one limb: a midpoint in the interval within $u\lvert m\rvert + \eta$ of $m$, and the smallest radius of `T` for it; two limbs: a midpoint within $\frac{3u^2}{1-4u}$ relative and $2\eta$, a radius that covers the interval; the two parts of a split cover the set and meet at a point of it | [Guarantees, Intervals](../../getting-started/guarantees.md#intervals) |
| Interval to ball and back; `from_bounds` | `Ball<T, 1>(X)` contains $X$ with that midpoint and the smallest radius for it; `Interval<T, 1>(B)` is the smallest interval of `T` that contains the ball; two limbs: containment, and the exact midpoint when both halves of the bounds are numbers of `T`; the special values of every pair of bounds | the same; [Concepts](../../concepts/enclosures.md#one-algorithm-any-enclosure) |
| Predicates, `contains` and comparisons of balls | one limb: predicates and member tests exact, comparisons exact when the sum of the radii is at most $\Omega$; two limbs: signs exact, the rest *certain* (an answer given is right; near the boundary none may be given) | [One enclosure interface](../../reference/enclosure.md#what-is-exact-what-is-certain-what-is-not-claimed) |
| Hull, intersection and split of balls | canonical; containment of what they must contain; the special sets | the same (deviation 26: no tightness, no finite-result clause) |
| `sum`, `sum_fast` over an array, one and two limbs | when finite, $\lvert s - \sum x_i\rvert \le ((1+e)^{n-1} - 1)\sum\lvert x_i\rvert$ **for every tree of additions and every number of lanes**, $e$ the bound of one addition; the flag is true exactly when the result is finite, and a result that is not is the canonical NaN | [Functions on arrays](../../reference/batch.md#what-each-function-states) |
| `dot`, `conv` | when finite, the same shape with $\sum\lvert x_i y_i\rvert$ and an underflow term $(1+e)^{n-1}\,n\,\tau$, $\tau = \tfrac12\eta$ for one limb and $\tfrac32\eta$ for two; each coefficient of `conv` the statement of `dot` for its own terms | the same |
| The maps `add`, `sub`, `scale`, `mul_pow2`, `axpy` | of every element written that is finite, the bound of the operation on one element; the flag true exactly when every element written is finite; in both orders | the same |
| `norm_upper` | one limb: exactly the largest magnitude; two limbs: at most one step of `T` above the smallest number of `T` not below it | the same |
| `traits<X>::sum(n)`, `sum_height(h)`, `dot(n)` | the constants are at least the bounds above, as numbers of `T`, computed by proved kernels; $+\infty$ beyond the lengths they cover | [The bound as a function of the length](../../reference/batch.md#the-bound-as-a-function-of-the-length) |
| `Accumulator<T, k>`: `add`, `add_product`, `merge` | for every history of the three, a merge being a node of the tree: when the running sum is finite and the masks of the radius are true, the sum is within `error_bound()` of the exact sum of what was added | [Accumulator](../../reference/accumulator.md#what-is-proved) |
| `BallVector`: negation, sum, difference, scaling, scaling by a power of two, product of polynomials | V1 canonical; V2 containment entry by entry, in every case; V3 a finite result has the kernels' centers and the loop's radius; V4 finite under conditions on the entries and the radii (a quarter of the threshold), for every length; scaling by a power of two exact when nothing underflows | [Ball vectors](../../reference/ball_vector.md#the-operations) |
| The entry forms of the strict rule (`two_prod_entry`, `mul_2_1_entry`, `dot_2_entry`, ...) | the statements of the kernel each one guards, by reduction to it | [below](#a-hole-in-a-guarantee-of-milestone-1) |
| The two executions | for 66 kernels a constant expression can reach: the listing constant evaluation runs gives the values of the run-time listing, for every input | [Guarantees](../../getting-started/guarantees.md#constant-evaluation) |

**Which statements exist for which kernels.** "Proved" does not mean the same for every kernel,
and an earlier sentence of the record ("every kernel is proved in both models") was false. Of
the 237 kernels:

| Kernels | Statements |
|---|---|
| 109 | a generated statement in the IEEE model only: the interval kernels, the predicates, the full kernels of the balls. There is no separate real-model statement; with infinite bounds as ordinary values, the IEEE statement is the whole claim |
| 36 | generated statements in both models |
| 54 | a generated statement in the real model, and generated statements in the IEEE model for finite operands (the result is the real model's when it is finite; the leading limb is finite only if the operands' are): the steps of the loops, the accumulator's kernels, entry forms |
| 10 | a statement in the real model, and theorems of the IEEE model written by hand |
| 8 | a statement in the real model, and in the IEEE model only the theorem of the two executions |
| 20 | a statement in the real model only: the radius kernels of the ball vectors, the steps of `norm_upper`, and `two_sum_entry`, the kernel of the public `two_sum`. The IEEE-model theorems of the loops and kernels that contain them use their models |

The 51 loops have generated statements in both models, in both orders.
[The design page](../design/milestone2.md) has the list for the kernels as they stood on
2026-11-21 and the changes since; that 20 kernels, the public `two_sum` among them, have no
IEEE-model theorem of their own is an [open issue](#open-issues).

**What the proofs rest on.** 1 563 theorems pass the audit: 194 generated statements of the real
model, 400 of the IEEE model, 969 by hand. As in Milestone 1: the four axioms of Rocq's real
numbers; the meaning of each operation in Flocq's terms and the vocabulary of the statements,
written by hand; the generator, which prints the Rocq model and the C++ from one description.
New in this milestone and trusted in the same way: the model of a loop over an array
(`Folds.v`: a fold over any tree, lanes, the second pass), and for the two executions the listing
that constant evaluation runs, printed by the generator and compared with the C++ by tests.

**Not proved** (each is stated where it appears; [What holds today](../../getting-started/guarantees.md)):

- `rational` and `integer` (deviation 22), and so that the ball of such a constant contains it;
- a few compositions of proved kernels in the headers, each argued from the claims of its parts:
  `Interval<T, 2>(lo, hi)` from values of `T` and the member test of a point of `T` in a set of
  two limbs (each through `make_2`); `from_limbs`; `axpy` and `norm_upper` of a ball vector;
  `ldexp` beyond the powers of two of `T`;
- the integer bookkeeping of the bounds of arrays and of the accumulator: the count given to the
  kernels as a number of `T`, and what the accumulator returns when a mask is false (no bound,
  never a finite one the theorem does not give);
- the tests of bit patterns written by hand (`is_finite` of an interval, the states of a ball);
- of a loop: that the lane order writes the same elements as the sequential one, in-place use
  (both tested); the count of an accumulator as a machine integer;
- tightness of the hull, intersection and split of balls, and a finite-result clause for them
  (deviation 26); that a split is at the midpoint (the kernel does it; the claim says only that
  the parts meet at a point of the set);
- that the one radius of a ball vector equals the largest entrywise radius (held in 2 400 vectors
  × 5 operations; not claimed);
- anything under flush-to-zero (Milestone 3), and the IEEE statements outside formats shaped like
  `binary32` and `binary64` (deviation 25).

### Statements found false

The proofs are not a formality: five statements of this milestone were refuted while proving
them, each with a counterexample checked by Rocq or reproduced by the interpreter, and corrected
before any header called the kernel. The tests found two more.

| Statement | What was false | Found by | Now |
|---|---|---|---|
| Hull and intersection of balls (`ball_set`) | "the result is the other operand as it is" in both directions fails for two special operands that differ in a NaN payload or the sign of a zero | its proof | the second direction only when the first operand is not special; proved |
| V4 of the ball vectors ("finite operands within the limit give a finite result") | false for a vector of length 0 | the generator's author | stated with the radii's own condition, for every length |
| V4 of the one-limb ball vectors | false at precision 1 (a constant of the radius overflows) | its proof | from precision 2 |
| V4 of the product of two-limb ball vectors | the condition on the count let it exceed the largest number in small formats ($p \ge 8$, $p < e_{\max} \le 2p - 7$); `binary32` and `binary64` unaffected | its proof | the condition uses the smallest normal number |
| The flag of the product's last step (`bv_conv_finish`) | the generator's printer dropped two masks from the statement | its proof | printer fixed; proved |
| `ball_from_interval_1` on $[+\infty, +\infty]$ | the listing predated the rule that an infinite point is the whole line, and returned the empty set against its claim | a test of the generator | listing corrected, proved again |
| Midpoint of a two-limb interval in formats with $e_{\max} \le p$ | not finite for some bounded intervals (the sum of the halves overflows) | the nightly enumerations | not claimed in formats no statement covers (a ruling, below) |

### A hole in a guarantee of Milestone 1

Rule R3 of Milestone 1 guards every value that enters a kernel from the program before the kernel
adds it, so that a compiler allowed to contract cannot fuse the program's own product into the
kernel's first addition. It did not guard a value that the kernel only multiplies, on the premise
that nothing fuses into a multiplication. **The premise is false when the compiler can see that
the other factor is 1 or −1**: LLVM rewrites `fma(x, 1, s)` as `x + s` and then fuses the
program's product into it. It was found by the author of the functions on arrays, in the one-limb
`dot`. Measured then, always with `-ffp-contract=fast` and only with Clang and Apple clang, never
with GCC: `two_prod`, `mul_down`, `mul_up`, `finite::mul(Expansion<T, 2>, T)`, the product of a
packed two-limb number by a one-limb one, and, in a release build (`NDEBUG`), `Expansion<T, 2> * T`
and `Ball<T, 2> * T` too: 18 forms in all, with a wrong last limb in up to 20 000 of 20 000 cases
built to cancel. Milestone 1 shipped with this, and its tests of the boundary did not have a
factor of 1.

By the owner's decision of 2026-11-21 the rule is strict: a value the program supplies is guarded
before it is a factor of a fused operation with a non-zero addend, and the generator refuses a
description that leaves one exposed. Each public operation calls a guarded entry form
(`two_prod_entry`, `mul_2_1_entry`, ...) whose theorems reduce to those of the unguarded kernel,
which the library keeps for its own calls on limbs a kernel wrote. No statement of Milestone 1
changed. With the guards, a matrix of 960 builds and 132 480 cells (four compilers, three
optimization levels, four contraction settings, four factors, both limb types, scalar and packed,
with and without `NDEBUG`) has no difference.

Thirteen objects of the two-limb loops were left on a list of pending ones when the rule first
landed, none measured to fuse; they are closed too. `dot`, `conv`, `axpy` of two limbs and the
scaling of a ball vector of two limbs call guarded forms; a ball vector of two limbs built over
arrays of the program guards each limb of each center; and `Accumulator::from_state` guards the
values it takes, which *was* measured to fuse otherwise (GCC at its default setting among them).
The list is gone and the generator refuses any exposed factor. On the final headers a matrix of
240 builds and 40 320 cells has no difference.

The price, measured: `two_prod` in a dependent chain 1.5 to 1.8 times slower (the guard is on the
dependency) and 2 to 32% in a loop; `mul_down` and `mul_up` 3 to 18%; the products of a two-limb
number by a `T` 6 to 19% in a loop and nothing in a chain; `scale` of two limbs 10 to 22%;
`Expansion<T, 2> * Expansion<T, 2>`, whose `two_prod` runs on limbs, unchanged; `axpy` of two
limbs 6 to 13% (11 to 13% on the x86-64 machine in the benchmarks, which measured the changed
functions again on the final headers); `dot`, `conv` and the scaling of a ball vector of two
limbs within the noise; the constructor of a ball vector of two limbs about 0.5 ns per entry on
x86-64 (1.25 to 2.3 times) and nothing measurable on the Mac.

### Defects of compilers found

| Compiler | What it does | Found by | In Kairn |
|---|---|---|---|
| MSVC 19.52, `/O2 /arch:AVX2` | loses the write of one lane of a register that is stored, modified and reloaded in a loop | the first MSVC build of `Packed` | `set_lane` is a blend; reproduced with a program that includes no Kairn header (decisions log, 2026-11-21) |
| MSVC 19.52, `/O2` | an inlined function that selects three of its by-value struct parameters and returns them in a struct holding an array loses two of them | the exhaustive tier's first MSVC build | the fix-ups stay out of line with MSVC, as the shipped ones already were; `experiments/milestone2/msvc/select_inline.cpp` |
| MSVC 19.52 | cannot `bit_cast`, in constant evaluation, an element of a `float` array member initialized with `{}` | the tests of the signs of a ball | the limbs are initialized with zeros written out; latent since Milestone 1 |
| MSVC 19.52 | refuses in constant evaluation a `float` product whose exact value exceeds the largest `float` although it rounds to it | `two_prod`'s tests | one assertion is `double`-only with MSVC |
| MSVC | folds the packed guard (an addition of zero), so a −0 stays −0 in packed code; values unaffected, and the guard still blocks the fusion | the packed tests | tests compare zeros as zeros under MSVC |
| MSVC 19.52 | in constant evaluation, refuses a `float` sum whose exact value exceeds the largest `float` although it rounds to it (the test of a canonical pair in a debug build) | the first MSVC build of the interface additions | the compile-time test takes a pair below the largest number with MSVC |
| clang-cl (hosted CI) | under rounding downward, the one-limb constructor of a ball vector returned the whole space: its radius is −0 there, and the test of its sign came out false (the mechanism was not established: no clang-cl on a test machine) | the tests of the rounding modes | that constructor checks the rounding mode like the functions that round; the other one-limb constructors exempt by the same argument are an open issue |
| GCC 13, `-ffp-contract=fast` | rewrites `a + a` as `a * 2` and fuses it | the generator's tests | the generator refuses `add(a, a)` |
| Apple clang | negating a fused result emits a fused negate-multiply-add beside it | the object-code check | the generator refuses the negation of a fused result |

## Brute-force results

[Brute-force results, Milestone 2](brute-milestone2.md) has every number, per kernel and per
machine.

- **No claim was violated.** On the three machines (the Linux machine with GCC 13 and Clang 18,
  the Mac with Apple clang and GCC 16, the Windows machine with MSVC; 90 runners: scalar and
  packed code, every contraction setting, optimized and debug builds), the oracle judged
  25 107 129 600 results of the compiled kernels and loops over arrays, in `binary64` and
  `binary32`, and 2 340 035 716 results of the generator's interpreter, which enumerated every
  operand of 1 296 small-format domains. No case failed a claim and none was invalid. On each
  machine every runner gave the same counts and the same extremes. The Linux machine ran 9.4
  hours, the other two 5.9 each (the brief's default is 3 to 4 hours per machine).
- **The aim of $10^8$ results per kernel and format was reached for part of the kernels.**
  The milestone has 233 kernels and 47 loops at the commit of the runs, against 63 kernels in
  Milestone 1, and twice the runners per compiler; 190 kernels are new or changed since
  Milestone 1 (170 new, 20 changed) and 43 unchanged. The 116 kernels run to the aim, 115 of them
  new or changed and one unchanged, `to_nearest_2`, reached $10^8$ cases on each of their 232
  kernel and format pairs (176 pairs in results judged; the others 83 million or more, their
  overflowing cases not being judged). **The other 75 new or changed kernels and the other 42
  unchanged ones have 7.2 million cases per kernel and format, and the 47 loops 42 000 to 72 000
  arrays** of up to 4 096 elements. Nothing was dropped silently: the page lists each group by
  name. (Corrected on 2026-11-23: this report first said 191 new or changed and 42 unchanged. The
  comparison made for the campaign had taken the loops printed after `to_nearest_2`, the last
  kernel of each generated header, as its code; its code and its claims are those of Milestone 1.
  Found when the reference pages were made to compare the code of each run. By the code alone,
  the rule of those pages, 51 kernels are unchanged since Milestone 1: eight more have the same
  code under claims that gained a condition.)
- **The exhaustive tier on emulated formats**, run whole for the first time: 1 247 784 868
  lines of 1 120 entries: every operand at precision 8 of the 80 kernels of one or two limbs
  and at 9 to 11 of the 15 of one limb, and 407 million random cases, among them 3.8 million
  arrays of the loops in every order; 1 216 815 154 judged, none failed. It runs the C++ the generator prints, compiled for a limb type of integer arithmetic.
  Gradual underflow only: the flush-to-zero variant the brief names is proposed for Milestone 3
  (deviation 27).
- **Findings: five, all in the tests.** Two enumerations stopped on infinite radii of the
  accumulator at precision 2, which the oracle called suspicious: its rule of thumb (a correct
  kernel stays finite when operands and result are within a quarter of the largest number)
  does not hold for a kernel whose constant factor is the largest number of that format; an
  exact test shows every one of them an overflow, and no claim says the radius is finite. Four
  other enumerations were complete and failed no claim, but in formats where the quick tier's
  guards cannot be exercised (the plan had chosen formats too small for three kernels). All six
  were run again in fitting formats and pass. Three faults of the driver were fixed, each with a
  test. None is a fault of a statement, the generator, the code, a compiler or a machine.
- **How close the bounds came.** Attained exactly: the error bounds of the one-limb sums,
  differences and scalings by a power of two, of the kernel of the public `two_prod`, of the
  one-limb accumulator's sum and merge, the $\tfrac32$ gaps of `radd` and `rmul`, and the
  radius of `conv_radius`. The sums of one limb over arrays came within $1.8 \cdot 10^{-4}$ of their
  bounds at every length from 2 to 4 096. **Far from attained: the bounds of the sums of two
  limbs over arrays**, at most a third of the bound (a half for the fast sum), and about a
  sixth on long arrays: these bounds are proved, and not shown tight. The underflow term of the
  bounds of a dot product is larger than it must be by about $1/u$, by construction (so that
  its constant is a normal number).
- **The adversarial search**, on the 109 kernels it can climb, both formats, 20 000 cases per
  kernel and format, with the closest cases of the runs as seeds: no claim violated; it came
  closer to the claim than the runs on 135 of 234 quantities (the accurate addition of two
  limbs to within $10^{-15}$ of its bound, where the runs had reached 0.50 to 0.79 of it). It does not take the loops, nor 118 kernels of this
  milestone whose kinds it does not climb. 349 lines joined the regression cases.
- **The last change of the milestone, run again.** The runs above are of commit `5f597fb`.
  The close of rule R3 then added eight kernels and loops and changed the code of four. Those
  twelve were run on the three machines at the final code (1 157 445 582 results judged, their
  37 enumerations, 46.9 million indices, and their 48 entries of the emulated tier), with no
  failure. Every other kernel and loop was compared between the two commits, definition by
  definition, and is the same code.

Before this campaign: the nightly run of the brute-force tier on hosted runners exists since this
milestone (deviation 20 of Milestone 1 said nothing ran nightly): about 1 h 50 min per night, 2.25
billion results judged over five platforms in its first run, no finding. One nightly failed on a
fault of the driver (it took a runner with a planted fault for a runner of the library); fixed.

## Benchmarks

[Benchmarks, Milestone 2](bench-milestone2.md) has the tables, the machines and the noise.

- **A directed operation without changing the rounding mode** costs 0.7 to 1.6 ns in a loop, 4.5
  to 11 times a plain operation, and 3.6 to 7.3 ns per step of a chain. Changing the mode around
  each operation costs about 25 ns; a classical loop that sets the mode once is 4.5 to 11 times
  faster than Kairn's, and that is the price of leaving the mode alone.
- **`Interval<double, 1>` against `Ball<double, 1>`**: a sum 2.3 to 3.2 times, a product 5.6 to 10
  times, a polynomial of degree 8 by Horner 2.4 to 6.6 times. Both enclose 8.6 to 10.5 times the
  true range once the argument is wider than a few units in the last place, the interval up to 11%
  narrower; at a point the one-limb ball is 3.3 times wider than the interval.
- **`Interval<T, 2>`**: a sum 7.2 to 25 ns, a product 29 to 81 ns, 18 to 31 times the product of
  two-limb balls. For two limbs the ball is the type to use unless the bounds themselves matter.
- **Compile time** (`KAIRN_ENCLOSURE_CODE`): 1 000 operations inline take 3.4 s (Apple clang) to
  140 s (GCC 13); out of line, 0.3 to 1.8 s, with run time within 15%.
- **`rational`**: 95 to 195 ns per call on the Mac, 348 to 717 ns on the Linux machine; 0.23 to
  2.4 ms of compile time per two-limb constant.
- **Is `Packed` worth it?** With GCC and Apple clang, yes: a packed sum or product of two-limb
  `double` takes 0.25 to 0.37 of the scalar loop with four lanes (GCC 13, AVX2) and 0.59 to 0.89
  with two (Apple M3); `float` 0.12 to 0.45. With Clang 18 it gains nothing: Clang vectorizes the
  scalar loop over structure-of-arrays storage itself. One lane costs nothing; views and the
  element proxy cost nothing over raw pointers. Two things to know: `Packed<T, 1>` has no
  arithmetic, so `x + a*b` with one-limb data needs two passes or a promoted operand; and the
  packed dot product of the tutorial is 1.12 to 1.20 times *slower* on the M3 than scalar code
  with two running sums, because it is one dependent chain (open issue).
- **The enclosure interface**: predicates 0.16 to 1.9 ns; three-valued comparisons 0.7 to 3.3 ns
  for `Interval<double, 1>`, 1.7 to 7.0 for `Ball<double, 1>`, 1.0 to 7.0 for
  `Interval<double, 2>`, 3.8 to 19.6 for `Ball<double, 2>`. The hull and the intersection of
  two-limb balls cost 41 to 104 ns, 32 to 55 times the interval's: their kernel is three
  conversions. `midpoint()` then `radius()` of an interval costs up to 2.2 times `mid_rad()` with
  Apple clang, which does not inline the member.
- **Which type for a generic algorithm?** The tutorial's bisection, unchanged, over four types:
  `Ball<double, 1>` is fastest everywhere (3.2 to 8.8 µs to a width of $10^{-6}$);
  `Interval<double, 1>` takes 1.6 to 3.9 times as long for final zeros at most six times
  narrower; `Ball<double, 2>` 3.5 to 4.3 times to go as far as it can (radius $10^{-31}$ to
  $10^{-30}$); `Interval<double, 2>` 21 to 31 times, for zeros 3 to 4 times narrower than the
  two-limb ball's.
- **`KAIRN_CHECKS=1`**: interval sums of one limb take 2.1 to 3.5 times as long, products 1.1 to
  2.2. The functions that do not round are hit hardest, because they still read the environment:
  `contains(t)` of an interval goes from 0.53 to 7.5 ns on the x86-64 machine.
- **Compile time of the comparisons**, which are forced inline: 1 000 of them take 4.5 s with
  Apple clang, 5.5 s with GCC 16, 8.0 s with Clang 18 and 62 s with GCC 13; 10 000 take from 134 s
  (GCC 16) to more than half an hour (GCC 13, stopped). Open issue.
- **An accurate sum or dot product** (two limbs, default order) takes 2.6 to 2.9 ns per element
  on the x86-64 machine (four lanes) and 3.7 to 3.9 on the Mac (two): 1.7 to 1.8 times a
  compensated sum (Sum2; 1.5 to 1.7 times Dot2) on the first and 4.5 to 4.9 (4.0 to 4.6) on the
  second, and beyond a condition number of $10^{15}$ its error is 3 to 900 times smaller than
  theirs. One limb costs what a loop of `double` in the same order costs (0.87 to 1.13 times).
  **The sequential order, the same bits on every machine, costs about the number of lanes over
  the default: 3.7 to 4.5 times on the x86-64 machine and 1.9 to 2.5 on the Mac for `double`, 3.7
  to 9 for `float`.**
- **The check of the environment at entry** costs a call 5 to 6 ns on the x86-64 machine and
  about 0.5 ns on the Mac. On the first that is 64 to 82% of a `sum` or `dot` of one limb up to 8
  elements, 7 to 29% at 64 and under 5% from 1 024 (two limbs: under 5% from 4 to 16 elements).
  Four pages of the documentation said "within the noise from about 64 elements of one limb";
  they are corrected, and the log records it. On short ball vectors it costs most operations the
  read or less, and more where it changes what the compiler inlines
  ([open issue 2](#open-issues)).
- **The guards of the factors a program supplies** cost 0 to 29%: nothing where the loop waits
  for a dependent chain (`dot` of one or two limbs, `add_product`), 14 to 22% for `scale` of two
  limbs, 8 to 18% for `axpy` of two limbs, up to 29% for the product of short polynomials.
  Closing rule R3 made `axpy` of two limbs 11 to 13% slower and a constructor of a ball vector of
  two limbs about 0.5 ns per entry slower; `dot` and `conv` of two limbs did not move. The
  functions that the close changed were measured again on the final tree, and the page says
  which cell is of which tree.
- **The accumulator** costs what the sequential `sum` and `dot` cost, term by term: with two
  limbs about 10 ns per term on the x86-64 machine and 7 to 8 on the Mac.
- **One radius for many centers.** At 16 entries an operation on a `BallVector` is 2 to 4 times
  faster than on as many balls on the x86-64 machine (1.6 to 2.7 on the Mac), at 64 entries 3.3
  to 6.2 times (1.7 to 2.6), in 0.53 to 0.75 of the bytes; at 4 entries it is no faster. Where the
  entries have the same radius it is as wide; where they differ, the one radius is the worst
  entry's: 1 to 2 times the largest ball's radius after a sum, up to 118 times after a product,
  and up to $2 \times 10^6$ times the median ball's.
- **Compile time of the two headers**: `kairn/batch.hpp` or `kairn/ball_vector.hpp` costs a
  translation unit 1.2 to 1.7 s on the x86-64 machine and 0.3 to 0.7 s on the Mac; 1 000 calls of
  the functions on arrays, 2.7 to 12 s; of the operations of ball vectors, 2.3 to 4.2 s.
- **Not measured**: Windows and MSVC (this milestone's benchmarks have no Windows figures),
  Intel processors, AVX-512, GPUs, threads. The Mac was shared with the test campaign during
  part of the third part; the page gives the load of each run.

### Compile times and other costs

- Including `kairn/kairn.hpp` costs a translation unit 0.45 s with GCC 13 and 0.70 s with
  Clang 18 on the x86-64 machine. It includes the accumulator and not `kairn/batch.hpp` or
  `kairn/ball_vector.hpp`, each of which makes it 1.2 to 1.7 s (the packed forms of the generated
  kernels).
- **`kairn::self_test()` compiles in 6.4 to 6.5 s with GCC 13, against 1.1 s at the end of
  Milestone 1** (3.9 to 4.0 s with Clang 18 and GCC 16, 1.2 s with Apple clang): its generated
  header went from 76.5 KB and 84 tests per limb type to 311 KB and 330. Found by the client's
  build, confirmed by the benchmarks. At run time it costs 2.5 to 8.8 µs. Not remedied: an open
  issue with a proposal.

## Tests and CI

[Testing](../testing.md) has every tier and its measurements. On the final headers (`main` at
`788d45f`; the commits after it add measurements, regression cases and documentation):

- **Quick tier**: 1 218 tests with Apple clang (288 to 293 at the end of Milestone 1), none
  failing: every kernel and loop through every compiled runner on a sample, judged by the oracle
  in exact arithmetic; every public operation; the checks of a debug build; the object code of
  every kernel in five configurations; the examples of the site; 111 cases that must not
  compile (the count with MSVC); the consumer checks. Each cross-check now runs in one process,
  as the plan asked. The regression cases, which every runner replays, grew from 185 lines to
  534 with the lines of the brute-force runs and of the search that came closest to a claim.
- **Full tier**: 2 036 tests more (GCC 13): the same on more cases, every public operation under each
  flag set of a client, the kernels at `-O0` and `-O1`, the object code on the whole flag matrix,
  the interpreter's enumerations of toy formats, the emulated tier at 8 bits, and the tools' own
  tests.
- **The exhaustive tier on emulated formats** (new): the C++ the generator prints, instantiated
  on a number type of integer arithmetic in a format chosen at run time, compared line by line
  with the interpreter and judged by the oracle. Of 299 faults planted in the printed C++, the
  quick tier's `binary64` sample already catches 237 and no enumeration at 8 bits caught one of
  the rest; what the tier adds is the comparison with the interpreter (faults whose results still
  satisfy a claim with room), the path of constant evaluation, which no compiled cross-check
  runs, and dense samples of tiny formats (13 faults of four kernels that the quick sample
  passes).
- **The boundary with the program** (rule R3): tests that hand each public operation a product
  written by the program, with factors of 1 and −1, under every contraction setting, scalar,
  packed and over arrays; each has a control built without the guards that must differ where a
  compiler was measured to fuse.
- **The oracle is tested like the library**: every claim of every kernel and loop is judged;
  448 mutants of the oracle itself, all caught; planted faults in the runners; lines judged by
  hand.
- **The generator's suite**: 431 tests; it builds the generated code at `-O0` and `-O2`, with
  and without `-frounding-math`, under every contraction setting, and requires every build to be
  bit-identical to the interpreter.
- **MSVC and clang-cl** build and pass the quick and the full tier on hosted runners; before
  each landing that touched a header the quick tier was also run with MSVC on the Windows machine.

CI: the five workflows of Milestone 1 and the nightly run. **Hosted-runner time is now the
binding constraint.** The test step of the quick tier took 232 to 430 s on Linux, 381 s on macOS
and 442 to 719 s on Windows at `--parallel 4` on the final commit, 1.9 to 6 times the two minutes
of the brief (deviation 24), and the runners differ from one run to the next by as much as the
tier grew: on the commit before, with 16 tests fewer, Linux x86-64 with GCC took 292 s (430 s
now) and MSVC 746 s (442 s now). The full tier runs in three shards per compiler on Windows and
in two on Linux x86-64 and on macOS; the generator's suite in two shards per job; the interpreter's
enumerations in three. Every one of these splits was made after a job was cancelled at its limit
of 60 minutes with no test failing: the same job took 33 to 59 minutes from one run to the next.
One landing took eight rounds of CI, every failure a time limit sized for Milestone 1 and none a
failure of the library. Re-budgeting is an [open issue](#open-issues) for before Milestone 3.

## Documentation added

- **Concepts** (new section, eight pages): numbers of several limbs; precision and magnitude;
  intervals, balls and ball vectors and which to use; what "correct" means here; the
  floating-point environment; values, threads and constant expressions; arrays. Every statement on
  them was checked against the claim it paraphrases; 7 example programs run as tests.
- **Tutorials** (five new, six in all): the range of a polynomial; zeros of a polynomial by
  bisection, written once over intervals and balls; a vector loop with the packed type; sums and
  dot products of arrays; polynomials as ball vectors. Each is a program that ctest runs and
  compares with its stored output.
- **Reference**: generated pages for the 237 kernels and the 51 loops; hand-written pages for the
  enclosure interface, the packed type, the containers, the functions on arrays, the accumulator,
  ball vectors, `rational`.
- **Getting started** and **What holds today** brought up to the state of the tree.
- **Developer guide**: the design page of this milestone with dated notes where the build
  departed from it; architecture (the IR of loops, rule R3 strict, the two executions, the formats
  of the statements); testing (the tiers, the exhaustive tier, the guards).
- **Results**: benchmarks and costs of this milestone, brute force, this report.

## What an audit against the brief found

An independent audit of `main` was made on 2026-11-21, before the headers of the arrays landed,
and a second one on 2026-11-22. The first found the claims, proofs and code in agreement
where sampled, no axiom, no admitted statement, no license or privacy problem; and:

| Finding | Disposition |
|---|---|
| The exhaustive tier on emulated formats did not exist, and nothing said so | Built (gradual underflow); the flush-to-zero variant moved to Milestone 3: deviation 27 |
| The quick tier runs in 3 to 10 minutes on hosted runners, against "about two minutes" | Deviation 24; measured per platform; open issue |
| No Concepts pages | Written |
| Hull, intersection and split of balls: no tightness bound and no finite-result clause | Deviation 26; open issue |
| No public unchecked constructor from limbs for `Interval` and `Ball` | `from_limbs` added |
| The IEEE statements cover formats shaped like `binary32`/`binary64` only, while deviation 19 said every exponent range | Deviation 25; deviation 19 corrected |
| `ldexp` and `half` of two limbs not usable in constant expressions though their kernels are | Made `constexpr` |
| Places where the design page promised more than is claimed, not all in the log | Logged ((a) to (h)) |
| Four user-facing sentences stronger than their claims ("the answers are exact", "the exact midpoint", the status paragraphs, the ball of a fraction) | Corrected |
| Sources cited but missing from the bibliography; `source` fields saying "published" | Bibliography completed; 29 fields corrected |
| Eight contradictions in the record (what is public, the count of two-executions proofs, ...) | Corrected |
| `X(lo, hi)` means bounds for an interval and center and radius for a ball: no common way to build a set from bounds | `from_bounds` on both |
| `Interval` had no `is_finite()` | Added |

**The second audit** (2026-11-22, on the tree with the functions on arrays, the ball vectors and
the strict rule, before it landed) found the code in agreement with its headers wherever it probed
(nine compiled probes, two compilers: lengths 0 and 1, NaN and infinities, an overflowing partial
sum, the two orders of summation, aliasing, the classes of a radius, `from_bounds`, `from_limbs`),
the proofs clean, and almost every finding of the first audit fixed or flagged. What it found:

| Finding | Disposition |
|---|---|
| `axpy(a, x, y, y)` of ball vectors, in a build without the checks, returned a finite ball vector that does not contain the result; the same spelling is the in-place form of the functions on arrays | Fixed: the whole space in every build, a report in a debug build (a ruling, below) |
| No statement says when the result of a function on arrays, or the accumulator's radius, is finite: a loop that always answered "not finite" would satisfy the proofs. The oracle tests it | Deviation 26, extended; open issue |
| The accumulator checks the environment in a debug build only, where the brief asks the check at every batch entry | Deviation 28; confirmed by the owner on 2026-11-23 |
| Six user pages said a factor needs no guard, against the strict rule, for the 13 objects then pending | Corrected when those were closed |
| The count of terms up to which the accumulator gives a radius was misstated (one limb: fewer than $2^{22}$ of `float`, $2^{51}$ of `double`; two limbs: twice as many) | Corrected |
| A generated reference page promised the exact midpoint for the one-limb ball of an interval | Corrected in the tool |
| A ball vector of two limbs over arrays the program fills: no loop guards its centers (no compiler was seen to fuse through one) | Guarded (`bv_make_2_entry`) |
| Stale comments, counts, two deviations, the order of the log; a line of code on a reference page that would not compile | Corrected |
| The move of the flush-to-zero variant read as settled | Worded as a proposal, for the owner; decided on 2026-11-23: Milestone 3 |
| CI red on the audited commit (MSVC) | Fixed before landing (below) |

## Deviations flagged in this milestone

Full text in [the list](../design/phase0/decisions.md#deviations-from-the-brief-flagged).

| # | The brief asks | What exists |
|---|---|---|
| 22 | Shipped code is generated and every bound machine-checked | `rational` and `integer` are integer code written by hand, specified exactly, tested, and checked against their statement for each constant computed at compile time |
| 23 | Interval semantics modeled on IEEE 1788.1 | A NaN bound, a NaN radius, an interval of an infinite point give the whole line, not the empty set (the owner's decisions): a failure upstream must not become "no solution" |
| 24 | The quick tier in about two minutes per platform | 4 to 5 minutes on Linux and macOS, 12 on Windows, on hosted runners; 3.2 minutes on the Mac with four workers. Left as it is by the owner (2026-11-23) |
| 25 | Proofs parametric in the exponent range | The real-model statements are; the IEEE-model statements hold for formats shaped like `binary32` and `binary64` |
| 26 | A tightness bound per operation | None for the hull, intersection and split of balls, the radius of a two-limb interval, and two conversions |
| 27 | Exhaustive tier with gradual and flush-to-zero variants | Gradual only; the other proposed for Milestone 3, with the flush-to-zero proofs, and so decided by the owner (2026-11-23); those proofs, and the variant with them, are in Milestone 4 since the decision of that day on [the scope of Milestone 3](#the-scope-of-milestone-3) |
| 28 | The environment checked at every batch-API entry | The functions on arrays and the ball vectors check in every build; the accumulator's operations, called once per element, only in a debug build. Confirmed by the owner (2026-11-23) |
| 29 | Every header correct under any client flags, contraction included | Found on 2026-11-23, after this report: with Clang under `-ffp-contract=fast` a square the program passes straight in is not rounded first. Documented and not repaired, by the owner's decision ([below](#found-after-the-review-a-square-loses-its-guard)) |
| (plan) | Conversions between limb types in Milestone 2 | Moved to Milestone 3 with the device pass they serve (README, plan and log say so) |

## Open issues

Most important first; each with a proposal where there is one. Six of them were decided by the
owner on 2026-11-23 and say so at their end; [the owner's review](#the-owners-review) has the
whole list.

1. **`BallVector` cannot hold what the first client's polynomials are** (one weight per
   coefficient). [Below](#what-the-first-client-needs-next).
2. **The check of the environment at the entry of every function on arrays and of every
   operation on a ball vector costs short calls a large share of their time.** The brief calls
   the check non-negotiable, and it is made in every build. Measured by the benchmarks: one read
   of the control register, 5 to 6 ns per call on the x86-64 machine and about 0.5 ns on the Mac.
   That is 64 to 82% of a `sum` or `dot` of one limb up to 8 elements, 7 to 29% at 64 and under
   5% from 1 024; for operations on ball vectors of 3 entries, 1.2 to 1.8 times as long with one
   limb, and for 3 to 18 entries of two limbs 1.01 to 1.27 times. The first client, whose
   polynomials have 3 to 18 coefficients and whose every Kairn call is already inside its own
   guard of the rounding mode, measured it in
   its own code (GCC 13, x86-64, release build), with the headers as they are, with the report
   of a failure moved out of line ("cold"), and with the check removed:

   | The first client's code | As it is | Cold report | No check |
   |---|---|---|---|
   | Sum of 3 / 7 / 13 / 18 coefficients, ns | 35 / 63 / 79 / 76 | 22 / 38 / 30 / 63 | 19 / 35 / 27 / 62 |
   | Split of 3 / 7 / 13 / 18 coefficients, µs | 0.178 / 0.452 / 0.974 / 0.569 | 0.177 / 0.454 / 0.968 / 0.548 | 0.156 / 0.402 / 0.881 / 0.532 |
   | Five two-limb searches, µs | 7.67 / 1.61 / 8.61 / 0.73 / 3.08 | 7.75 / 1.57 / 8.66 / 0.69 / 3.06 | 7.20 / 1.52 / 8.05 / 0.65 / 2.84 |

   So the check costs the client's short sums 1.2 to 2.9 times, almost all of it not the read
   but the code of the report compiled into every call (three tests, two addresses of strings
   and the call of the handler): it lengthens the hot path, and in a large translation unit it
   uses up the compiler's budget for inlining, so that constructors of ball vectors stop being
   inlined (the compiler's own report says so, in the client's unit and in the benchmarks').
   With the report cold a sum costs about 3 ns more than without the check. The splits and the
   searches, which make several calls per step, stay 6 to 8% slower with the check in either
   form: that is the reads themselves.

   The benchmarks measured the same operations in a harness of their own, on both machines.
   They did not reproduce the size of the client's figure for sums (`x + y` of two limbs takes
   1.01 to 1.26 times as long with the check there), but found the same cause wherever the check
   costs more than the read: a constructor that the compiler no longer inlines (Clang 18: 18 to
   20 ns more for three entries of one limb; GCC 13 at `-O3` in a file of many operations: 6 to
   14 ns), and in two cases a loop that falls elsewhere in memory. With the report cold, GCC
   inlines the constructors again and its excess falls to the read; Clang 18 needs the
   constructors forced inline as well (read in the machine code, not timed). On the Mac a chain
   of short one-limb operations loses 3 to 7 ns per operation to the read itself, with the cold
   report too; why was not measured. Options, for the owner:
   - *keep it as it is*;
   - *make the report cold* (tried on copies of the headers by the benchmarks and by the client's
     pull request; not made): the hot path one read and one test, and the constructors of a ball
     vector forced inline. To settle with it:
     `KAIRN_ENVIRONMENT_FAILURE` is a macro a program may define, and out of line the linker
     keeps one copy of the report for the whole program, so the macro must then have one
     definition per program (which the language already requires, and forced inlining hides);
   - *a tag* by which a program states that it has checked (a scope object that checks once and
     hands out the tag), which keeps the default safe and removes the reads too: what the
     client's splits and searches would need;
   - *a macro that turns the check off* for a whole build.

   Recommended: the cold report in any case, as the first change after this report; the tag if
   the client's author wants the last 6 to 8%.
   **Decided by the owner on 2026-11-23: the report out of line; no tag and no macro.**
3. **`self_test()` compiles in 6.4 to 6.5 s with GCC 13** (1.1 s at Milestone 1). Proposal:
   cases for the kernels whose compiled code a flag can break in distinct ways, the rest behind
   a macro.
4. **A function with thousands of comparisons of sets compiles slowly**: 1 000 take 4.5 s (Apple
   clang) to 62 s (GCC 13). They are forced inline in every setting of `KAIRN_ENCLOSURE_CODE`,
   which moves only the arithmetic out of line. Proposal: the setting covers them too.
5. **CI time** (above). Proposal: before Milestone 3, measure each test on a hosted runner, shard
   by label, set limits at three times the measured time; run the nightly's compiled part on pull
   requests that touch the runners. **Decided by the owner on 2026-11-23: left as it is.**
6. **Split at the midpoint is not claimed**, for intervals or balls, though the kernels do it; a
   bisection's progress rests on it. Strengthen the claims.
7. **No statement says when a result is finite** for the hull, the intersection and the split
   of balls, for the functions on arrays, or for the accumulator's radius (deviation 26): a
   kernel that always answered "the whole line", or a loop that always answered "not finite",
   would satisfy the proofs. The oracle tests it on its cases; a regression would be noticed by
   those only. Proposal: finite-result clauses, as the ball vectors have (V4).
8. **Twenty kernels have no theorem of their own in the IEEE model**, the public `two_sum`'s
   kernel among them: their statements are for finite operands, and what they do on an infinity
   or a NaN is stated only where a loop or a kernel that contains them states it. Proposal:
   generated IEEE statements for the ones a program can call.
9. **The sum of two two-limb numbers is proved finite below half the range** (optimal), while its
   Milestone 1 claim says a quarter: the claim, and the conditions of the balls that rest on it,
   could be improved.
10. **`Packed<T, 1>` has no arithmetic** (its kernels are not entry kernels), so `x + a*b` on
   one-limb data needs two passes or a promoted operand. **Decided by the owner on 2026-11-23:
   it gets `+`, `-` and `*` now.**
11. **The product of ball vectors written over an operand is reported by a debug build only**:
   without the checks the result is not an enclosure. (`axpy` written into `y` now returns the
   whole space in every build; the functions on arrays have the same precondition for arrays
   that overlap in part.) Proposal: the whole space in every build here too.
12. **Values that enter without a kernel of their own.** `from_limbs` and
   `Accumulator::from_state` guard their values through a composition that is argued, not
   proved: there is no kernel for a single guarded value. And `Ball(Expansion<T, 2>, r)`, of
   Milestone 1, takes its center as stored, while the constructors of a ball vector now guard
   the same kind of value, since a program can write an `Expansion`'s limbs. Proposal: guard it
   too (one kernel, proved by reduction), for one rule everywhere. **So decided by the owner on
   2026-11-23**, for `Ball(Expansion<T, 2>, r)`.
13. **One-limb constructors exempt from the rounding-mode check** on the argument "it only
    guards": after the clang-cl finding each needs a look: `Ball<T, 1>(a)`, `Ball<T, 1>(c)`,
    `Ball<T, 1>(c, r)`, `Ball<T, 1>(q)`, `Ball<T, 2>(a)`, and the constructors of an interval of
    one limb and of two limbs from a `T`. They were tested under the three directed modes on
    every platform of the CI and passed; the finding was of one constructor with one compiler.
14. **Radii**: `ldexp` and `half` of a ball can return a subnormal radius (performance only); the
    accumulator's radius is given only while $m u \le 1/2$; the two-limb sums' bounds are not
    shown tight (the brute-force runs reached at most a third of the bound, a half for the fast
    sum, and about a sixth on long arrays).
15. **The brute-force runs did not reach $10^8$ results for every kernel.** 115 of the 190
    kernels new or changed since Milestone 1 reached it, and one unchanged kernel with them (the
    counts were first given as 116 of 191, [corrected above](#brute-force-results)); the other
    75, and the other 42 unchanged
    ones, have 7.2 million cases per kernel and format, and the 47 loops 42 000 to 72 000 arrays
    ([above](#brute-force-results)). The brief sizes the tier by time, 3 to 4 hours per machine,
    and the runs took 5.9 to 9.4; about nine more hours of the Linux machine would bring the 75
    kernels to $10^8$, and no such budget brings the loops there. Also: the reference page of a
    kernel shows its latest run only, so the 42 kernels whose code did not change now show 7
    million cases where Milestone 1's run had 110 to 122 million. Proposal: the page shows
    every stored run of a kernel whose code is unchanged. **Decided by the owner on 2026-11-23:
    the pages are changed so; no further runs are made for this milestone.** Done: a page counts
    a stored run when the kernel's generated code at the run's commit is its code now, and the
    51 kernels whose code is that of Milestone 1's runs show those runs' 110 to 122 million
    cases per format next to this milestone's 7.2 million.
16. **The oracle's arrays have few non-finite elements** (6 of 100 map arrays in the quick tier).
17. **No test runs Kairn from several threads**: thread safety is by design (no global state).
18. **Not measured**: Windows, MSVC and clang-cl in the benchmarks of this milestone (the tests
    and the brute-force runs ran there, the timings did not); an Intel processor and AVX-512;
    the functions on arrays from several threads.
19. **Bibliography**: Knuth's edition and theorem, the clause of IEEE 754 for `nextUp`, Veltkamp's
    report, to complete.
20. **Seen twice on hosted macOS runners, never on a test machine: a wrong value in x86-64 code
    run under Rosetta.** On 2026-11-20 the scalar x86-64 runner printed `nan` for one output of
    one line of 299 450 (`two_sum`, `binary32`), while the other output, computed from it, was
    right. On 2026-11-22 the same kind of runner refused one of its *inputs*: for the `binary32`
    number `0x1.7bb55cp-20`, converting the parsed `double` to `float` and back did not give the
    same value, before any kernel ran. Both are in the conversions between `float` and `double`
    of the test's runner, not in a kernel; each rerun passed; 400 local runs of the first never
    differed. The cause is not established (the hosted runners are virtual machines; the test
    machines are not). Proposal: for the builds run under Rosetta only, rerun a failing run once
    on the same input and fail only if it fails again, printing a note when it does not; a real
    fault of the compiler or the library is deterministic and would still fail. Not done: it
    relaxes a test, so it is the owner's to decide. **Decided by the owner on 2026-11-23: no
    retry; the tests stay strict, and such a failure is rerun by hand and counted.**
21. **Smaller items.** The test cases of ITF1788 under the Apache license were to be converted
    and stored (a decision of the design review): not done, and with them the four relations of
    the full standard (`less`, `precedes` and their strict forms) are not provided. In
    `proofs/gen/IeeeStatements.v`, 38 comments say "IEEE-model status: unverified" above kernels
    whose IEEE-model theorems are proved and audited by hand: the generator has no field to name
    such a theorem. The NEON form of `Packed` writes one lane through memory, the pattern MSVC
    miscompiled on x86-64: it matters only for MSVC on ARM64, which was never built. No operation
    mixes a set with a number (`X + a`). A debug build does not report reversed bounds given to
    an interval (they are the empty set), as it reports a negative radius of a ball. The packed
    dot product of the tutorial [A vector loop](../../tutorials/vector-loop.md) is 1.12 to 1.20
    times slower on the M3 than scalar code with two running sums, because it is one dependent
    chain. The lines of code inside the reference pages written by hand are not compiled by a
    test, as the tutorials' programs are: the second audit found one that would not compile.
    The comment of the check at entry in `kairn/environment.hpp` says "two tests"; there are
    three on x86-64 and four on AArch64 (corrected in the log; the comment waits for the next
    change of the header, so that the commit the client's pull requests are pinned to stays the
    last that changes one). In the benchmarks, the guards of the product of short one-limb
    polynomials cost up to 29% with GCC 13 at `-O2` in the last run and 10% in the one before,
    on code that did not change: not looked into.

### What the first client needs next

Two draft pull requests are open against the first client (Kairn is used as a CMake subproject,
its two-limb code in translation units of its own). **The first**: a ball of two limbs per
coefficient; the client's whole suite passes, its double path is byte-identical, radii up to 21%
smaller after two switches to this milestone's building blocks. **The second**, stacked on it: one
radius per polynomial with `BallVector`; the same answers on every query (one lower bound differs
by one bit of its `double` view); at the present pin, sums 1.1 to 4.6 times faster than with a ball
per coefficient, squares 1.7 to 4.9 times, splits up to 20% faster from 7 coefficients and 38%
slower at 3, builds 11 to 31% slower.
Both are pinned to `main` at `788d45f` (version 0.3.0, the last commit of this milestone that
changes a header): the client's suites pass (35 and 36 of them, and 13 on the GPU), its double
path is byte-identical to its main branch (42 objects), and the six two-limb queries give the same
bits at every pin of Kairn they were run with. Nothing in the client had to change for the strict
rule; its guards cost the client 0 to 8% in splits and builds and nothing measurable elsewhere.
What the check at entry costs it is [open issue 2](#open-issues). The client's author has not
answered yet.

What the second showed is missing, in the order the client would use it:

1. a ball vector with one weight per entry (the client's polynomial is $\sum (c_i \pm w_i r)$):
   with one radius the radii are 1.7 to $2^{25}$ times larger than the client's own;
2. the product over multi-indices; scaling entry by entry; a weighted difference of gathers (a
   derivative); a gather with the shared radius;
3. a ball vector from N balls; narrowing a ball vector from two limbs to one; a mutable subview;
   a level of de Casteljau in one call;
4. a constructor of a two-limb ball vector from `T` values that is exempt from the check of the
   rounding mode, as `Ball<T, 2>(a)` is (the client runs under rounding upward).

Also from the client: no ball operation returns radius zero for exact inputs (every radius is at
least a constant), which one of its tests relied on; `KAIRN_CHECKS` in debug builds costs 36 to
60 µs against 14 to 39 µs.

## Decided by the owner

Each is a row of [the log](../design/phase0/decisions.md#decisions-log) that names the owner.

1. After the report of Milestone 1: the default operators keep their handling of overflow,
   infinities and NaN (2026-11-20).
2. The brute-force tier runs nightly on the hosted runners; the long runs on the test machines stay
   by hand, before a milestone's report (2026-11-20).
3. The site is published from every push to `main` (2026-11-20).
4. Milestone 2 also makes the building blocks public and builds numbers at compile time from an
   integer or a rational; the enclosure interface of `Ball` arrives with `Interval` (2026-11-20).
5. The two open questions of the design page that were the owner's: a NaN bound gives the whole
   line (deviation 23), and `rational` ships tested and checked at compile time, flagged as not
   machine-checked (deviation 22) (2026-11-20).
6. A NaN radius gives the whole line too; a negative radius stays the empty set (2026-11-20).
7. An interval of an infinite point is the whole line (2026-11-20).
8. The first client gets two pull requests: a ball per coefficient, then one radius per polynomial
   (2026-11-20).
9. The strict rule for the factors of a fused operation (2026-11-21).

The other answers to the open questions of the design page followed its recommendations
([Decisions adopted and changed](../design/milestone2.md#decisions-adopted-and-changed)).

## Rulings taken without the owner, for confirmation

Taken by the authors while the work ran, each logged with its reason; an earlier state of the
tree attributed some of them to the owner, which was corrected in 32 places. Each can be reversed.
**On 2026-11-23 the owner confirmed every row but one, and reversed that one: `Packed<T, 1>`
gets its arithmetic now** ([the owner's review](#the-owners-review)).

| Ruling | Why |
|---|---|
| The radius of the product of two ball vectors (`conv_radius`) claims its bound of finite results only | at the kernel a non-finite result is $+\infty$ or NaN and the callers' statements cover it |
| The IEEE statements quantify over formats shaped like `binary32`/`binary64`; in other toy formats the oracle counts their finiteness clauses as not claimed | they are false as written in formats with $e_{\max} \le p$ (deviation 25) |
| In those formats the midpoint of a two-limb interval and the parts of a split are judged by containment only | 144 lines of the nightly enumerations |
| `ball_set` restated; V4 restated three times; `ball_from_interval_1` relisted | found false ([above](#statements-found-false)) |
| The predicate is `is_whole()` on both types (IEEE 1788 says `isEntire`) | `Ball` shipped it in 0.2.0 |
| No comparison operators on sets; the relations live in `kairn::ieee1788`; `member(t, X)` added | a three-valued answer must not convert to `bool` |
| `Packed<T, 1>` has no arithmetic in this milestone | its kernels are not entry kernels |
| Under MSVC a packed −0 may stay −0 | the compiler folds the guard; values unaffected |
| The conversions between limb types move to Milestone 3 | they need a second format in the generator, the model and the oracle; the exit criterion does not need them |
| The flush-to-zero variant of the exhaustive tier moves to Milestone 3 | no statement exists under flush-to-zero until then (deviation 27) |
| `two_prod` in a constant expression refuses to compile where its value would differ from run time | a promise narrowed, flagged |
| `kairn::sequential` is the first argument of every function that takes it | as the execution policies of the standard library; it was last in one header and first in another |
| The one-limb constructor of a ball vector checks the rounding mode | the clang-cl finding |
| `axpy` of ball vectors written into `y` returns the whole space in every build | it returned a finite wrong enclosure without the checks; found by the second audit |
| The accumulator's operations check the environment in a debug build only (deviation 28) | a check per element would cost several times the operation |
| The axpy of ball vectors is the composition of scaling and sum in place | bit-equal in every case run to a one-pass kernel, which stays a proposal |
| The object-code check compiles scalar forms with the vectorizer off; the radius and the last step of a ball-vector loop are a function never inlined | compilers packed or folded them |
| CI: shards and limits | above |
| The two steps of `axpy` of two limbs were changed in place to guard the scalar's limbs, not given twins | their statements did not change; they were proved again |
| The constructors of a ball vector of two limbs guard every limb of every center, the one from an array of `Expansion<T, 2>` included | a program can write an `Expansion`'s limbs; the second audit's finding |
| `Accumulator::from_state` guards the values it takes | measured to fuse without |

## The owner's review

On 2026-11-23 the owner reviewed this report and answered, one question each with the options
and a recommendation, everything it put to them. Each answer is a row of
[the log](../design/phase0/decisions.md#decisions-log) of that date.

| Question | The owner's decision | Recommended at the review |
|---|---|---|
| The cost of the environment check at a batch entry ([open issue 2](#open-issues)) | The check stays in every build; its report of a failure moves out of line, and the constructors of short ball vectors are forced inline. No tag, no macro that turns it off | the same |
| The accumulator checks the environment in a debug build only (deviation 28) | Confirmed as built | a check in every build where the bound is asked for |
| The flush-to-zero variant of the exhaustive tier (deviation 27) | With the flush-to-zero proofs, then Milestone 3's; they moved to Milestone 4 the same day ([below](#the-scope-of-milestone-3)) | the same |
| Failures under Rosetta that a rerun does not repeat ([open issue 20](#open-issues)) | The tests stay strict: no retry | one retry, with a note |
| `Ball(Expansion<T, 2>, r)` takes its center unguarded ([open issue 12](#open-issues)) | It guards it: one kernel, proved by reduction | the same |
| CI time (deviation 24, [open issue 5](#open-issues)) | Left as it is | measure, split by label, limits at three times the measured time |
| Brute-force coverage below $10^8$ for 75 new or changed kernels ([open issue 15](#open-issues)) | No further runs; the reference pages show every stored run of unchanged code | the nine more hours, and the pages |
| The 21 [rulings of the authors](#rulings-taken-without-the-owner-for-confirmation) | 20 confirmed. Reversed: `Packed<T, 1>` gets `+`, `-` and `*` now, before Milestone 3 ([open issue 10](#open-issues)) | all 21 confirmed |
| When the changes are made | Now, as a follow-up of this milestone; then one commit on each of the client's pull requests moves its pin. Milestone 3 is not started | the same |
| A square the program passes straight in loses its guard with Clang under `-ffp-contract=fast` ([found after the review](#found-after-the-review-a-square-loses-its-guard)) | Documented, not repaired; the four changes land first | a barrier in the generated guard, under Clang |

The open issues the review did not decide stay open as listed.

### What changed after the review

Version 0.3.1. Kernels: 239 (237 at the report). Theorems checked by Rocq: 1 574 (1 563): 194
generated in the real model, 404 generated in the IEEE model, 976 by hand; the same four axioms,
nothing admitted.

- **The check of the environment at a batch entry** ([open issue 2](#open-issues)) is one read of
  the control register and one test of a mask at the place of the check, and the report is one
  function that is never inlined; the checks of a debug build share it. With Clang the
  constructors of a ball vector from centers and a radius are forced inline while the centers
  have at most 14 limbs; with other compilers never. `KAIRN_ENVIRONMENT_FAILURE` must now be
  defined the same way in every translation unit of a program, or in none. Measured again on both
  machines ([benchmarks](bench-milestone2.md)): Clang 18's constructor of a ball vector of three
  entries of one limb takes 9.0 ns where it took 24 (6.0 without the check), Apple clang's 4.4
  where it took 5 to 13; on the Mac a `sum` of one element takes 0.59 ns where it took 1.10. On
  the x86-64 machine a short array still pays the read itself, 4.6 to 5.7 ns, which is 62 to 82%
  of a `sum` or `dot` of one limb up to 8 elements, as before: only the tag or the macro that the
  owner did not choose would remove it. Over the 240 functions of ball vectors measured, the
  median time is 0.98 to 1.00 of what it was.
- **`Ball(Expansion<T, 2>, r)` guards its center** ([open issue 12](#open-issues)), through
  `ball_make_2_entry`, proved by reduction to `ball_make_2`, which stays for centers that a
  kernel wrote. Its statement gives the center of a finite ball as the values given, where
  `ball_make_2` gives the limbs themselves: a limb $-0$ comes back $+0$. By a choice of the
  authors the constructors of an interval from numbers of two limbs guard their limbs the same
  way (`interval_make_2_entry`, whose statement is `interval_make_2`'s word for word), and
  `Accumulator::from_state` of two limbs guards its running sum. Cost: 0 to 14% of a
  construction of a ball (under 0.1 ns), up to 15% of an interval's (0.33 ns). No compiler was
  seen to fuse through these constructors: the copy without the guards gave the same results in
  200 000 cases with each of the four compilers. The guards are there by the rule.
- **`Packed<T, 1>` has `+`, `-`, `*` and their compound forms** ([open issue 10](#open-issues)).
  They call the steps of the functions on arrays (`add_entry_step_1`, `sub_entry_step_1`,
  `scale_step_1`), which were proved in both models already: no kernel, claim or theorem was
  added. Unlike `Expansion<T, 1>`, whose operators are those of `T`, a sum guards its operands,
  so `x * y + z` is two roundings under every contraction setting, and a sum of two $-0$ is $+0$.
  In a loop the operators cost what the bare instruction costs (0.97 to 1.02); in a dependent
  chain a sum costs up to 2.2 times as much with GCC, which keeps the guard of the running value.
- **The reference page of a kernel shows every stored brute-force run of its code as it is now**
  ([open issue 15](#open-issues)): 51 kernels show the runs of both milestones, 186 those of this
  milestone only, and the two kernels added after the review say that no stored run has judged
  them (the quick and the full tier, the exhaustive tier on emulated formats and the nightly runs
  do). 34 pages had said that a run judged other claims when the claims had not changed; they
  understated, and are corrected.

Slower than before, and not explained: with GCC 13 at `-O3` the constructor of a ball vector of
three entries of two limbs takes 20.7 to 22.1 ns alone in a translation unit where it took 16.4
to 17.1 (19.3 to 20.8 in a unit of many operations), from the code GCC makes around the new form
of the check, while the other sizes measured with GCC 13 are 3 to 14% faster; on the M3 with
Apple clang, chains of `add` and `sub` of ball vectors of 13 entries of one limb take 12 to 15 ns
where they took 8.3 to 9.6, with and without the check. Both are on the benchmarks page.

Also found, and open: Clang accepts `p - p.limb[0]`, a `Packed` minus a register of its form, as
an operation of its own vector types, where GCC refuses it; and `-fno-signed-zeros`, which Kairn
does not support and Clang accepts without a macro, is reported by `kairn::self_test()` with
Apple clang and not with Clang 18 when it is combined with `-ffp-contract=fast`.

### Found after the review: a square loses its guard

One guarantee of this report is false as it was stated: that a product the program computes and
passes straight in is rounded first under every contraction setting
([a hole in a guarantee of Milestone 1](#a-hole-in-a-guarantee-of-milestone-1) describes the
guard). With Clang under `-ffp-contract=fast`, a square is not: LLVM proves that `a * a` is never
$-0$, removes the guard `a * a + 0`, and fuses the square into the kernel's first addition. It was
found on 2026-11-23 by the author of the operators of `Packed<T, 1>`, whose tests pass a square,
and reproduced: `kairn::two_sum(c, a * a)` returned a pair that is not the error-free sum of
anything. The pairs of `two_sum`, `fast_two_sum` and `two_prod`, the directed sums, the
operations of two limbs with such a `T`, and two enclosures were measured wrong; GCC 13 and 16,
MSVC 19.52 in the modes the headers accept, and Clang under its default setting do not do it.
The theorems are not concerned: they are about the value a kernel receives, and what fails is
that the compiled program hands it that value.

The owner decided on 2026-11-23 that the limitation is documented and not repaired (deviation
29): [The exception: a square](../../getting-started/guarantees.md#the-exception-a-square) says
where it happens, what is then wrong and what a program does about it, and the probes with their
results are in `experiments/milestone2/square/`. Three repairs were built as patches and
measured, and not made; the log has what each costs. `kairn::self_test()` reports the limitation,
without failing, in `Status::limitation`, for the file that calls it (version 0.3.2; a choice of
the authors that it is a report: a program that never passes a square is within the guarantees),
and it adds no measurable compile time to `self_test()` ([open issue 3](#open-issues)). The tests
`api.boundary.square.*` and `api.square_probe.*` pin what the pages say, the ways to round a
square among them.

### The scope of Milestone 3

Decided by the owner on 2026-11-23, after this review ([the log](../design/phase0/decisions.md#decisions-log)
has the grounds): Milestone 3 is the CUDA backend for the kernels and loops that are proved today,
with `float` and with `double` limbs, and plans no new theorem, since CUDA's default arithmetic is
the IEEE arithmetic the proofs are about. The conversions between limb types, the Metal backend
with the proofs for flush-to-zero arithmetic, and the flush-to-zero variant of the exhaustive
tier move to Milestone 4, beside the numbers of three and four limbs. Where this report says that
something moved to Milestone 3 (the conversions, the flush-to-zero variant), it is now there.
Milestone 3 is not started.
