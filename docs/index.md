# Kairn

Kairn is a header-only C++20 library, in development, for floating-point expansions with interval
and ball arithmetic. Its aim is that every error bound it states carries a machine-checked proof,
and that the code it ships is generated from the same description the proofs are about.

**Status: pre-release. Milestone 1 is complete
([report](developer/results/milestone1.md)), Milestone 2 is in progress
([what each milestone adds](developer/design/phase0/plan.md#milestones)), and nothing in this
repository should be relied on yet.** The first public headers exist, for k-numbers of one and two limbs and balls around them,
and the statement of each of their operations has a checked proof in a model where nothing
overflows; the [reference](reference/index.md) has each statement and its theorem. One exception:
`ldexp` by a power of two outside the limb type's range is composed from proved steps by an
argument that is tested, not machine-checked ([`mul_pow2_2_full`](reference/mul_pow2_2_full.md),
[`mul_1_1`](reference/mul_1_1.md)). At overflow and for infinities and NaN they return results
like those of `float` and `double`, which is proved in a model of IEEE 754
([What holds today](getting-started/guarantees.md)).

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
  Rocq proofs with gradual underflow, the oracle and CI. Every kernel is proved. At overflow and
  for infinities and NaN the operations return IEEE-like results and the special states of a
  ball, which is proved in a model of IEEE 754, with a condition under which a `Ball` operation
  stays finite. The report lists what is open.
- The later milestones are in the [Plan](developer/design/phase0/plan.md#milestones).

## Where to go next

- [Getting started](getting-started/index.md): build and test the repository, and a first program.
- [Accurate sums and dot products](tutorials/accurate-sums.md): a tutorial with two-limb numbers
  and balls, on a sum that `double` gets entirely wrong.
- [The range of a polynomial](tutorials/intervals.md): a tutorial with intervals and balls, on the
  dependency problem and how splitting the interval narrows the result.
- [Zeros of a polynomial by bisection](tutorials/bisection.md): one algorithm, written once with the
  interface intervals and balls share, run on an interval of one limb and balls of one and two
  limbs, and why it tests its own progress.
- [A vector loop](tutorials/vector-loop.md): a dot product of two-limb numbers written once for
  AVX2, AArch64 and targets with neither, with `Packed`, and what can be claimed about its result.
- [Reference](reference/index.md): every operation, with its proved statement, its theorem, and
  what the brute-force runs measured.
- [What holds today](getting-started/guarantees.md): which operations are proved, and what is not
  written yet.
- [Proofs](proofs/index.md): how to check the proofs yourself, and what they rest on.
- [Architecture](developer/architecture.md): how the repository is organized and how its parts
  connect.
- [The Phase 0 report](developer/design/phase0/index.md): the design, and the measurements behind
  it.
