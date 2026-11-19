# Phase 0: specification and feasibility report

**Status: for review.** Per the brief, work stops here until you have read this and answered the
[ten decisions](decisions.md#decisions-needed-from-you). No library code exists yet; what exists
is this report and the experiments behind it, all in the repository.

## Verdict

Kairn can be built as specified, with four qualifications:

1. **The brief's defense against FMA contraction is not sufficient, and a sufficient one exists.**
   A double-word product written with an explicit `fma` for TwoProd is silently reduced to
   single-limb accuracy by Clang on Apple silicon with `-ffp-contract=fast` and by MSVC with
   `/fp:contract`, in 20 000 of 20 000 test cases, and Clang's scoped pragma does not prevent it.
   Writing every rounded product as `fma(a, b, 0)` survives all 23 configurations tested and
   becomes a rule the generator checks.
2. **The proofs are the schedule.** Two limbs is engineering: machine-checked proofs exist, but
   all of them ignore underflow and have to be redone with it. Three and four limbs are high risk:
   the only fast branch-free algorithms are verified by an SMT solver on an abstraction, with no
   proof object. **For five limbs and more there is no algorithm with a correctness proof of any
   kind in the literature**; the one library that shipped them withdrew them as broken. Baked-in
   $k = 8$ and runtime $k$ are research.
3. **Three requirements cannot be met literally.** "No overhead at $k = 1$" holds on GCC, needs a
   choice on Clang, and fails for auto-vectorized loops on MSVC. An interval of plain doubles
   costs about ten operations per bound without a rounding mode, against one with it. And `float`
   k-numbers lose precision below $10^{-16}$ to $10^{-31}$ (below $10^{-9}$ to $10^{-24}$ on
   Metal): a property of the format that no algorithm can remove.
4. **The test hardware has gaps**: no AVX-512 machine, no clang-cl, no Windows ARM64 tools.

Everything else in the brief was either confirmed by experiment or has a design with no known
obstacle.

## What Phase 0 ran

Every number in this report comes from a run recorded under
[`experiments/phase0/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0),
on the M3 Max Mac, kirby, sonic and ci-windows.

| Experiment | Question | Answer |
|---|---|---|
| `contraction/` | Does contraction break error-free transformations in practice? | Yes, on two compilers; the opaque product is immune in all 23 configurations. [Details](environment.md#contraction) |
| `flags/` | Which unsafe flags can headers detect? | All of them on GCC 13+; on Clang three families have no macro, so the run-time self-test is the only detector. [Details](environment.md#compiler-flags) |
| `constexpr/` | Can one function body serve constant evaluation and run time, also under `-frounding-math`? | Yes: 22 configurations of GCC, Clang, Apple clang and MSVC, bit-identical. [Details](library.md#constant-evaluation) |
| `cuda/` | `__host__ __device__ constexpr` without the relaxed-constexpr flag? Device equal to host? `float` versus `double`? | Yes; yes on $2^{20}$ cases; `float` is 69 times faster, and a 2-limb `float` beats a plain `double` by 2.5. [Details](environment.md#cuda) |
| `metal/` | What does an Apple GPU actually do? | Rounds to nearest; flushes subnormals; the default compile destroys TwoSum; scoped pragmas fix that and survive inlining. [Details](environment.md#metal) |
| `k1/` | Is `Expansion<T, 1>` free? | On GCC yes; Clang and MSVC, see above. [Details](library.md#one-limb) |
| `tracer/` | Does the generator-to-proof pipeline work? | Yes: one description, a Rocq model and C++, four theorems checked by Rocq 9.0.1 + Flocq 4.2.2 in 7 seconds, exactly four standard axioms, an `Admitted` control rejected, generated code checked against exact rationals. [Details](verification.md#what-phase-0-ran) |
| `compile_time/` | What do 8-limb-sized kernels cost to compile? | 0.1 to 0.3 s out of line; 3 to 11 s if force-inlined at 64 sites; **MSVC cannot parse them as templates** (over 24 CPU-minutes; 0.1 s as plain functions). [Details](library.md#inlining-and-compile-time) |
| `ranges/` | Where does each $(T, k)$ keep its precision? | [Table](numbers.md#precision-depends-on-magnitude) |

The two mathematical pages ([Numbers](numbers.md), [Operations](operations.md)) were then checked
by an independent reviewer that tested their claims by exhaustive search over 4- to 6-bit
floating-point formats and on `double`. It confirmed the invariant's consequences, the conversion
and comparison rules, the error-free transformations and the one-limb constants, and it found a
dozen errors, all corrected in the text: the most serious was a `TwoSum` overflow corner at the
largest finite number that would have made a "rounded down" sum land above the exact one; the
others were off-by-one range thresholds, statements that hold only from three limbs on, and
bounds stated relative to the wrong quantity. The statements marked **K** remain targets until
their proofs exist.

## The report

| Page | Covers (items of the brief's Phase 0 list) |
|---|---|
| [Numbers](numbers.md) | Representation and invariants; canonical zero and signs; non-finite values; exponent-range analysis per $(T, k)$ |
| [Operations](operations.md) | Theorem statements in plain math for every operation, each with its status; semantics of `Interval`, `Ball`, `BallVector`; batch kernels; decimal I/O; elementary functions |
| [Environment](environment.md) | Per-backend floating-point guarantees, documented and measured; contraction; flags; self-test; environment check |
| [Verification](verification.md) | Proof assistant choice; proof plan per $k$; generator design; trusted base |
| [Library](library.md) | Header-only design, runtime dispatch, compile times, constant evaluation; API; the check against miso2 |
| [Plan](plan.md) | Testing; documentation outline; milestone plan; performance targets |
| [Decisions](decisions.md) | The decisions needed from you; deviations from the brief; decisions log |
| [References](references.md) | Sources, prior art, licenses |

## Decisions needed, in one line each

| | Question | Recommendation |
|---|---|---|
| [D1](decisions.md#d1-proof-assistant) | Proof assistant and allowed axioms | Rocq 9 + Flocq 4.2; the four axioms of Rocq's real numbers |
| [D2](decisions.md#d2-what-counts-as-machine-checked) | May an SMT answer count as a proof? Are per-format proofs acceptable? | No; yes, flagged |
| [D3](decisions.md#d3-eight-limbs-and-runtime-k) | $k = 8$ and runtime $k$, for which no proved algorithm exists | Keep in scope, late, selects allowed |
| [D4](decisions.md#d4-normalization-invariant) | The invariant $x_i = \mathrm{RN}(x_i + x_{i+1})$ | Confirm |
| [D5](decisions.md#d5-non-finite-results) | IEEE-like infinities and NaN, or only "not finite" | IEEE-like by default, fast variants available |
| [D6](decisions.md#d6-one-limb-and-contraction-under-clang) | $k = 1$ under Clang's default contraction | Unfused by default, opt-in pragma |
| [D7](decisions.md#d7-generated-headers) | Commit generated headers? | Yes, with a CI freshness check |
| [D8](decisions.md#d8-workload-priority) | Workload priority | Balls for miso2, linear algebra, GPU loops, predicates |
| [D9](decisions.md#d9-runtime-dispatch-state) | Where the CPU-detection result lives | A value the client holds |
| [D10](decisions.md#d10-test-infrastructure) | Runners, clang-cl, ARM64 tools, AVX-512 | Self-hosted runners; install the two components; SDE for AVX-512 |

## What I would do next

On your go-ahead, Milestone 1 ([Plan](plan.md#milestones)): `double`, one and two limbs,
addition and multiplication on scalar, AVX2 and NEON, `Ball`, the generator, the Rocq proofs with
gradual underflow, the oracle with both tiers, CI, and the website skeleton. Its first step is
the riskiest part of that milestone, porting the double-word addition proof to gradual underflow,
so that the estimate for the rest is grounded early.
