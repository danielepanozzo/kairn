# Plan: testing, documentation, milestones, performance

## Testing

Proofs are the guarantee. Tests look for what proofs do not cover: a wrong theorem statement, a
generator bug, a compiler, the hardware ([trusted base](verification.md#trusted-base)).

**Oracle.** A separate program under `oracle/`, sharing no code with the library or the
generator. Exact dyadic rationals on GMP for $+$, $-$, $\times$, `fma`, conversions, sums and dot
products; MPFR and Arb enclosures for quotients, square roots, elementary functions and decimal
I/O, with the precision doubled until the verdict is decisive. The two are cross-checked on a
sample, and the checker is itself tested by injecting wrong results and wrong bounds. Phase 0
already works this way at small scale: every experiment's numbers come from a checker written
with Python rationals, separate from the code under test, and the tracer includes a negative
control.

**Cases** are text lines of hexadecimal floats: operation, $(T, k)$, operands, oracle result or
enclosure, bound. Generation is counter-based, so case $i$ of a generator and seed is computed
without generating the others.

**Checks on every case**: containment (for enclosure operands, also sampled exact points inside
them); measured error against the proven bound, recording the largest error-to-bound ratio per
operation so that loose bounds show up too; the normalization invariant on every result; special
values. Every backend is checked against the oracle, never against another backend.

**Strata**: the full exponent range; catastrophic cancellation; near overflow; near underflow and
subnormals (and below $\lambda$ for Metal); powers of two and ties; limbs at the extremes of the
invariant ($x_{i+1} = \pm\tfrac12\mathrm{ulp}(x_i)$, and the non-unique representations); long
carry chains; sums and dot products with prescribed condition numbers; enclosures that contain
zero or are degenerate, huge, empty or unbounded; for elementary functions, hard-to-round and
large arguments. An adversarial search maximizes error over bound, seeded with near-misses from
the proofs.

| Tier | Content | Runs |
|---|---|---|
| Quick | A checked-in corpus: edge cases of every stratum, all regressions, a small random sample. Under 2 minutes per platform. Includes every documentation example. | Every commit, every platform, also under QEMU |
| Brute force | Generated from seeds, sized by a time budget (3 to 4 hours per machine), all cores and GPU batches. Reports cases per stratum, cases per second, the largest error-to-bound ratio per (operation, T, k, backend), and the worst operands. | Nightly and before each milestone report, on each real machine |
| Exhaustive | The generated scalar kernels instantiated on an emulated format ($p = 8$ to $11$, a small exponent range, gradual and flushing variants): all operand combinations for small $k$ where feasible, dense sampling otherwise. | Part of the brute-force run |

A containment failure or a bound violation blocks release; the failing case is shrunk, added to
the quick corpus, and classified (statement, generator, code, compiler, hardware). For
`UNVERIFIED` operations the brute-force maxima are reported as empirical and never as bounds.
Benchmarks run separately.

**Machines.**

| Machine | Covers | Gap |
|---|---|---|
| Apple M3 Max | AArch64 NEON, Apple clang, GCC, Metal | — |
| Linux workstation (Threadripper 3995WX, GeForce RTX 3080 Ti) | x86-64 AVX2, GCC, Clang, CUDA on a consumer GPU | Shared and loaded (load average 117 during Phase 0) and its disk is 98% full: fine for GPU runs, poor for timing |
| Linux server (EPYC 7452, RTX A5000 and RTX 6000 Ada) | x86-64 AVX2, CUDA, containers (the Rocq toolchain ran here) | Workstation GPUs, same 64:1 `double` penalty as GeForce |
| Windows machine (Intel, 20 threads) | MSVC 19.52 | No clang-cl, no ARM64 cross tools, no GPU |
| — | **AVX-512** | **None of the four machines has AVX-512.** The AVX-512 path can be tested for correctness under Intel SDE or on a hosted runner, but not benchmarked |

See [D10](decisions.md#d10-test-infrastructure).

## Documentation outline

MkDocs with Material, following the wildmeshing-toolkit site's structure and conventions
(`mkdocs.yml`, pinned `docs/requirements.txt`, `gen-files` and `literate-nav`, MathJax through
`pymdownx.arithmatex`, snippets with section markers, tabs linked across the site, `--strict`
builds in CI, Doxygen under `/api/`).

```
Home                      what it is, what it guarantees, where to go next
Getting started           installation (CMake package, flags per compiler) · a first program ·
                          choosing T and k (leads with the range table) · troubleshooting
                          (fast-math, contraction, FTZ/DAZ, Metal self-test, UNVERIFIED)
Concepts                  expansions and normalization · precision versus magnitude · intervals,
                          balls, BallVector · what "correct" means · the floating-point contract ·
                          thread safety · verified versus UNVERIFIED · CPU versus GPU, float versus double
Tutorials                 accurate sum and dot product · dense linear algebra and a verified solve ·
                          ODE stepping on CUDA and Metal · interval Newton · orientation predicate ·
                          elementary functions · decimal I/O · making a templated library generic
                          over float, double and k-numbers · Python, Julia and Rust through the C ABI
Gallery                   error versus bound, throughput per backend and k, from stored results
Reference                 one generated page per operation · C ABI · Doxygen C++ API
Proofs                    how to check them locally · map from each plain-math theorem to its
                          formal statement · the axioms
Developer guide           architecture and the generator · adding an operation end to end ·
                          testing tiers · benchmarks · writing documentation · contributing ·
                          design notes (this report) and the decisions log
About                     citing · changelog · license · related libraries
```

Conventions carried over from the template:

- **Reference pages are generated at build time** from the generator's metadata (algorithm,
  citation, bound, preconditions, theorem name and file, verification status, the printed axioms)
  and from the latest stored brute-force results. A `--check` mode fails CI when an operation
  lacks a doc, a bound or a reference entry.
- **Every example is a file** under `docs/examples/{cpp,cuda,metal,python,c}/`, included with
  snippet markers, built and run by ctest in the quick tier, and checking its own output. A page
  never contains example code that is not in one of those files.
- Every public entity has a Doxygen comment, and Doxygen warnings fail the build.
- Pages are written for a reader who knows C++ but not error analysis, and every claim about a
  bound links to its reference page.

This report lives under *Developer guide → design notes*. It is written in Markdown that both
GitHub and MkDocs render; the site skeleton itself is a Milestone 1 deliverable.

## Milestones

Each milestone ends with a short report (what is done, bounds proven, brute-force results,
benchmarks, docs added, open issues) and ships the documentation for what it added.

| # | Content | Exit criteria | Main risk |
|---|---|---|---|
| 0 | This report | Your review | — |
| **1** | **Vertical slice**: `double`, $k = 1, 2$; $+$, $-$, $\times$ (accurate and fast addition, operations with a `T` operand, `ldexp`, comparisons, conversions to `T`); scalar, AVX2, NEON; `Ball`; generator; Rocq proofs with gradual underflow; oracle with quick and brute-force tiers; CI with the flag matrix and the object-code check; self-test and environment check; site skeleton (Home, Getting started, one tutorial, generated reference) | Every shipped operation has a checked theorem; brute force clean on Mac, Linux, Windows; `mkdocs build --strict` passes | Porting the double-word proofs to gradual underflow is the unknown in the estimate |
| 2 | `float` limbs; `Interval`; `BallVector` and the first batch kernels (sum, dot, axpy, convolution, `norm_upper`, accumulator); SoA containers and the packed SIMD type; exhaustive tier on emulated formats. Added at the review of Milestone 1 (2026-11-20): the enclosure interface shared by `Interval` and `Ball`; the building blocks as public functions; k-numbers built at compile time from an integer or a rational; each cross-check of the quick tier in one process | Same, plus the first client's ball path can be written against it | Interval tightness constants |
| 3 | CUDA and Metal backends: device code, warp helpers, device self-tests, flush-to-zero proofs, float-versus-double benchmarks on the GPUs. Moved from Milestone 2 on 2026-11-20: the conversions of numbers and balls between limb types, which need a second format in the generator's IR, in the Rocq model and in the oracle ([design](../milestone2.md#limbs-of-another-type)), and `lower_as<U>`, `upper_as<U>` for a limb type other than the enclosure's | Same on the three GPUs and the M3 | The flush-to-zero proof framework |
| 4 | $k = 3, 4$: networks first behind `UNVERIFIED`, then their Rocq proofs | Proofs checked, or an explicit report that a route failed and which is next | **Highest proof risk of the plan** |
| 5 | Division and square root ($k = 2$ from the existing proofs; $k = 3, 4$ by Newton iteration); gemv, gemm; AVX-512 dispatch | Proofs checked for $k = 2$; others may stay `UNVERIFIED` | No AVX-512 hardware |
| 6 | $k = 8$ and runtime $k$ | An algorithm with an induction proof, or a documented negative result | **Research** |
| 7 | Decimal I/O; elementary functions; C ABI and bindings | One checked proof per function and format | Volume |
| 8 | Release hardening: benchmarks against QD, CAMPARY, MultiFloats.jl, CCCL fpmp2, MPFR and Arb; full tutorials and gallery | The brief's release conditions | — |

Milestones 2 and 3 do not depend on 4, so the first client's use case (balls with 2-limb centers
on CPU and GPU) is served before the risky proofs. No release happens before every public
operation is proved, documented and exercised by a tutorial example in CI; milestones before that
are development snapshots.

## Performance targets

**Workload priority** (proposal, [D8](decisions.md#d8-workload-priority)):

1. **Verified computation with balls**: `BallVector` sums, scalings, convolutions and norms at
   $k = 2, 4$ on CPU and GPU. It is the only workload with a real client waiting.
2. **Linear algebra**: dot, gemv, gemm. It is where published baselines exist to compare with.
3. **Elementwise GPU loops** (simulation, ODE steps): the float-versus-double question lives here.
4. **Geometric predicates**: last, because a predicate wants the sign of one expression, which
   adaptive exact arithmetic already does well; k-numbers help mostly as the filter stage.

**Non-rigorous operations within 1.2× of the fastest library.** The fastest published scalar
algorithms at $k = 2, 3, 4$ are the networks Kairn adopts, so parity of the networks is by
construction. Three things Kairn does that the baselines do not, and whose cost Milestone 1 must
measure against the 1.2× budget: the opaque product (an FMA in place of a multiplication), the
canonicalization of non-finite results ([D5](decisions.md#d5-non-finite-results)), and the
environment check at batch entry. If the default configuration misses the target, the
`kairn::finite::` variants are the like-for-like comparison, and the report will show both.

**Rigorous operations faster than MPFR and Arb.** A 2-limb ball product is one 9-flop kernel and
about ten `T` operations for the radius. The baselines' authors report their unverified 2- to
4-limb arithmetic at 35 to 41 times the speed of MPFR and FLINT on BLAS kernels
([ZA-SC25](references.md#za-sc25)); a factor of two or three for rigor leaves a wide margin. Not
measured in Phase 0.

**GPU: float limbs or double limbs.** Measured on the three NVIDIA cards: `float` runs 69 times
faster than `double`; a 2-limb `float` multiply-add is 2.5 times faster than a plain `double`
one, and 72 times faster than a 2-limb `double` one. For a precision target of about 48 bits or
90 bits the `float`-limb number wins by a large factor *as long as the data stays above the range
thresholds of [Numbers](numbers.md#precision-depends-on-magnitude)*; the per-precision crossover
with all $k$ and with memory-bound kernels is a Milestone 3 benchmark. These are compute-bound
numbers from one synthetic kernel, not predictions for real workloads.
