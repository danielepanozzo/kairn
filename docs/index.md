# Kairn

Kairn is a header-only C++20 library, in development, for floating-point expansions with interval
and ball arithmetic. Its aim is that every error bound it states carries a machine-checked proof,
and that the code it ships is generated from the same description the proofs are about.

**Status: pre-release. Milestone 1 is complete
([report](developer/results/milestone1.md)), Milestone 2 is complete and was reviewed by the owner on 2026-11-23
([report](developer/results/milestone2.md#the-owners-review); [what each milestone adds](developer/design/phase0/plan.md#milestones)),
and nothing in this repository should be relied on yet.** The public headers of this version have k-numbers of one
and two limbs, balls and intervals around them with the interface the two share, the building
blocks on `float` and `double`, constants built at compile time from an integer or a fraction, and
the accumulator of a sum or a dot product, all included by `kairn/kairn.hpp`; and, in headers of
their own that it does not include, the packed SIMD type `Packed` and containers in
structure-of-arrays form (`kairn/packed.hpp`, `kairn/soa.hpp`), the functions on arrays
(`kairn/batch.hpp`), `BallVector` (`kairn/ball_vector.hpp`), and the opt-in round-up interval
(`kairn/upward.hpp`), an interval of one limb computed under the rounding mode upward, for speed,
which requires compiler options and the header's scopes ([The round-up interval](concepts/upward.md)).
The rest of the plan is to come.
The kernels these operations call have checked proofs of their
claims: the error bounds, normalization and the containment of ball arithmetic in a model where
nothing overflows, and in a model of IEEE 754 what they return at overflow and for infinities and
NaN, results like those of `float` and `double`, and every claim of the intervals and of the
interface of the sets; the loops of the functions on arrays and of `BallVector` are proved in both
models; the kernels of the round-up interval are proved in the model of IEEE 754 with their sums
and products rounded upward, and that the compiled code runs them so is assumed, the program's to
arrange ([What holds today](getting-started/guarantees.md); the
[reference](reference/index.md) has each statement and its theorem). Not machine-checked: `ldexp`
by a power of two outside the limb type's range, composed from proved steps by an argument that is
tested ([`mul_pow2_2_full`](reference/mul_pow2_2_full.md), [`mul_1_1`](reference/mul_1_1.md));
`kairn::rational` and `kairn::integer`, integer code that is specified exactly and tested, and with
them that the ball of such a constant contains it
([Constants from fractions](reference/rational.md)); a few compositions of proved kernels in the
headers, argued and not proved as one statement; the integer bookkeeping of the bounds of arrays
and of the accumulator (the count of terms, its conversion to the limb type); the tests of bit
patterns written by hand (`sign`, `isfinite`, `is_normalized`, the states of a ball, `is_finite()`
of an interval); and, for the round-up interval, that each of its operations that rounds runs as
the IEEE operation rounded upward.

## What it is

A *k-number* stores a value as an unevaluated sum of $k$ `double`s or $k$ `float`s, its *limbs*,
most significant first. Two `double` limbs carry up to $2 \times 53 = 106$ significant bits, but
only where the value is large enough for the lowest limb not to underflow: the precision of each
combination of limb type and $k$ depends on magnitude, and the
[Numbers](developer/design/phase0/numbers.md#precision-depends-on-magnitude) page gives the ranges.

On top of k-numbers the design has intervals, whose two endpoints are k-numbers, and balls, a
k-number center with a radius of the limb type. The library is to be used as the CMake target
`kairn::kairn`, in namespace `kairn`, under the MIT license.

## What it will guarantee

- **A theorem for every operation.** Each operation has a statement in plain mathematics: what its
  operands must satisfy, and a bound on the error of its result, of the form
  $|z - \text{exact}| \le c\,u^k\,|\text{exact}| + t\,\eta$ (for some operations relative to
  the operands rather than to the exact result), where $u$ is the unit roundoff of a limb
  ($2^{-53}$ for `double`) and $\eta$ its smallest subnormal number, so that the second term
  accounts for underflow ([Operations](developer/design/phase0/operations.md#the-shape-of-every-statement);
  the [reference](reference/index.md) has the statement of every operation that exists).
- **A machine-checked proof of it.** The statement is proved in Rocq with the Flocq library, about
  a formal model generated from the same kernel description as the C++ code, and an audit checks
  that each proof uses no axioms beyond the four allowed
  ([Architecture](developer/architecture.md#the-formal-model)).
- **Containment for intervals and balls.** The exact result of an operation on intervals or balls
  lies inside the interval or ball it returns
  ([Operations](developer/design/phase0/operations.md#enclosures)).
- **Tests for what proofs do not cover**: a wrong statement, a generator bug, a compiler or the
  hardware. Results are checked in exact arithmetic by an oracle that shares no code with the
  library or the generator ([Plan](developer/design/phase0/plan.md#testing)).
- **No unproved bound presented as one.** An operation whose proof is not checked yet is marked
  `UNVERIFIED`: it compiles only with the marker `kairn::unverified` on an operand, its error
  constants are not exported, and its measured errors are reported as measurements, never as
  bounds. No release
  happens before every public operation is proved, documented and exercised by a tutorial example
  in CI ([Plan](developer/design/phase0/plan.md#milestones)).

## What Phase 0 found

Phase 0 checked that Kairn can be built as specified, by experiment, before any library code was
written ([report](developer/design/phase0/index.md#verdict)). In short:

- With some flags, two compilers silently reduce a double-word product to the accuracy of one
  limb, by contracting a product and an addition into one fused operation. Writing every rounded
  product as `fma(a, b, 0)` survived all 23 configurations tested, and became a rule of the
  generator's design.
- Two limbs is engineering: machine-checked proofs exist, but all of them ignore underflow and have
  to be redone with it. Three and four limbs are the highest proof risk of the plan. For five limbs and
  more there is no algorithm with a correctness proof of any kind in the literature, so eight
  limbs and a $k$ chosen at run time are research.
- `float` k-numbers lose precision below magnitudes of $10^{-16}$ to $10^{-31}$, depending on $k$
  (higher on Apple GPUs): a property of the format that no algorithm can remove.

## Status

- **Phase 0**, specification and feasibility: complete, reviewed on 2026-11-18.
- **Milestone 1**, complete, with the owner's decisions of 2026-11-20
  ([report](developer/results/milestone1.md)): `double` and `float` limbs with $k = 1$ and $2$;
  addition, subtraction and multiplication; scalar, AVX2 and NEON code; `Ball`; the generator, the
  Rocq proofs with gradual underflow, the oracle and CI. Every kernel of the milestone is proved. At overflow and
  for infinities and NaN the operations return IEEE-like results and the special states of a
  ball, which is proved in a model of IEEE 754, with a condition under which a `Ball` operation
  stays finite. The report lists what is open.
- **Milestone 2**, complete, reviewed by the owner on 2026-11-23
  ([report](developer/results/milestone2.md), [design](developer/design/milestone2.md)):
  `Interval`, the interface intervals and balls share, the building blocks, constants at compile
  time, `Packed` and the containers, the functions on arrays, the accumulator and `BallVector`.
  Every kernel and every loop over arrays is proved; the report lists what is open, what was
  measured, and the rulings that await confirmation.
- **The round-up interval**, between Milestones 2 and 3 and not a milestone, complete and awaiting
  the owner's review ([design](developer/design/upward.md), [concept](concepts/upward.md),
  [measurements](developer/results/bench-upward.md)): the opt-in header
  `kairn/upward.hpp`, an interval of one limb computed under the rounding mode upward, for speed,
  with its scopes, its functions on arrays and its self-check. Its 24 kernels are proved, in the
  model of IEEE 754 with their sums and products rounded upward. Version 0.4.0.
- The later milestones are in the [Plan](developer/design/phase0/plan.md#milestones).

## Where to go next

- [Getting started](getting-started/index.md): build and test the repository, and a first program.
- [Concepts](concepts/index.md): what a number of several limbs is, how many digits it has at each
  magnitude, intervals, balls and ball vectors and when to use which, what a guarantee says and how
  it is established, what the library needs of the floating-point environment, arrays, and the
  opt-in round-up interval.
- [Accurate sums and dot products](tutorials/accurate-sums.md): a tutorial with two-limb numbers
  and balls, on a sum that `double` gets entirely wrong.
- [The range of a polynomial](tutorials/intervals.md): a tutorial with intervals and balls, on the
  dependency problem and how splitting the interval narrows the result.
- [Zeros of a polynomial by bisection](tutorials/bisection.md): one algorithm, written once with the
  interface intervals and balls share, run on an interval of one limb and balls of one and two
  limbs, and why it tests its own progress.
- [A vector loop](tutorials/vector-loop.md): a dot product of two-limb numbers written once for
  AVX2, AArch64 and targets with neither, with `Packed`, and what can be claimed about its result.
- [Sums and dot products of arrays](tutorials/arrays.md): the functions on arrays of
  `kairn/batch.hpp`, in both orders of summation, checked against the bound `kairn::traits` gives
  for their length.
- [Reference](reference/index.md): every operation, with its proved statement, its theorem, and
  what the brute-force runs measured.
- [What holds today](getting-started/guarantees.md): which operations are proved, and what is not
  written yet.
- [Proofs](proofs/index.md): how to check the proofs yourself, and what they rest on.
- [Architecture](developer/architecture.md): how the repository is organized and how its parts
  connect.
- [The Phase 0 report](developer/design/phase0/index.md): the design, and the measurements behind
  it.
