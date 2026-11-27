# Kairn

Rigorous floating-point expansions ("k-numbers") with interval and ball arithmetic, in
header-only C++20. Every error bound is meant to carry a machine-checked proof, and the shipped
code is generated from the same source the proofs are about.

**Status: pre-release (version 0.4.0). Phase 0 (specification and feasibility) and Milestone 1
are complete ([report](docs/developer/results/milestone1.md)); Milestone 2 is complete, and the
changes decided at the owner's review of 2026-11-23 are made
([report](docs/developer/results/milestone2.md#the-owners-review)); the opt-in round-up interval
is being completed; Milestone 3 has not started ([what each milestone adds](#milestones)). Nothing here should be relied on yet.** The
documentation is at <https://danielepanozzo.github.io/kairn/>.

Public on `main`, for `T` = `float` or `double`:

- in `kairn/kairn.hpp`: the numbers of one and two limbs, `kairn::Expansion<T, 1>` and
  `kairn::Expansion<T, 2>`; the balls `kairn::Ball<T, k>` and the intervals `kairn::Interval<T, k>`
  around them, with the enclosure interface the two share (predicates, three-valued comparisons,
  hull, intersection, split, midpoint and radius, the conversions between them); the building
  blocks on `T` (`two_sum`, `two_prod`, sums and products rounded down and up without changing the
  rounding mode); constants built at compile time from an integer or a fraction
  (`kairn::rational`, `kairn::integer`); and the accumulator `kairn::Accumulator<T, k>`, a running
  sum with its error bound;
- in `kairn/batch.hpp`: the functions on arrays (sum, dot product, `axpy`, scaling, convolution,
  an upper bound of the norm), with their error bounds as functions of the length;
- in `kairn/ball_vector.hpp`: `kairn::BallVector<T, k, N>`, N centers with one radius;
- in `kairn/packed.hpp` and `kairn/soa.hpp`: the packed SIMD type `kairn::Packed<T, k>` and the
  containers in structure-of-arrays form;
- in `kairn/upward.hpp`, opt-in: the round-up interval `kairn::upward::Interval<T>`, an interval of
  one limb kept in one SIMD register and computed under the rounding mode upward, for speed, with
  its functions on arrays, the scopes that set the mode, and a self-check. **It requires compiler
  options** (`-frounding-math` with GCC and Clang, `/fp:strict` with MSVC, which the CMake target
  `kairn::upward` adds) **and its scopes** around every operation that rounds
  ([The round-up interval](docs/concepts/upward.md)).

`kairn/kairn.hpp` does not include the last five headers. The later milestones are not built.

**What is proved.** The kernels these operations call have proved claims: error bounds and the
containment of ball arithmetic in a model where nothing overflows; what happens at overflow and
for infinities and NaN, every claim of the intervals and of the interface of the sets, and the
loops over arrays for every length and order of summation, in a model of IEEE 754; and every claim
of the 24 kernels of the round-up interval, in that model with their sums and products rounded
upward. The operators
return results like those of `T` at overflow and for infinities and NaN (a ball: the whole line or
the empty set; an interval: an infinite bound, or the whole line); `kairn::finite::` skips that
layer.

**Not machine-checked:** `ldexp` by a power of two that the limb type cannot represent, whose
steps are proved and whose composition is argued and tested; `kairn::rational` and
`kairn::integer`, integer code that is specified exactly, tested for equality and, by default,
checked against its statement for each constant computed at compile time, and with them that the
ball of such a constant contains it; a few compositions of two proved kernels in the headers,
argued and not proved as one statement; the integer bookkeeping of the bounds of arrays and of the
accumulator (the count of terms and its conversion to the limb type); the tests of bit
patterns written by hand (`sign`, `isfinite`, `is_normalized`, the states of a ball); and, for the
round-up interval, that each of its operations that rounds runs as the IEEE operation rounded
upward, which is the program's to arrange with the options and the scopes.
[What holds today](docs/getting-started/guarantees.md) says what is proved, in which model, and
what is not yet.

- [Milestone 1 report](docs/developer/results/milestone1.md): what exists, what is proved, what
  the tests and the benchmarks measured, and what is open.
- [Phase 0 report](docs/developer/design/phase0/index.md): what Kairn will be, what was measured,
  and the decisions taken at its review.
- [Experiments](experiments/phase0/README.md) behind the report.
- [The original brief](docs/developer/design/brief.md).

## Milestones

Kairn is built in milestones. Each ends with a short report (what is done, which bounds are proved,
what the brute-force runs found, benchmarks, documentation added, open issues) and ships the
documentation for what it added. The table with each milestone's exit criteria and main risk is in
[the plan](docs/developer/design/phase0/plan.md#milestones); what was decided since is in
[the decisions log](docs/developer/design/phase0/decisions.md#decisions-log).

| # | What it adds | State |
|---|---|---|
| 0 | Specification and feasibility: what Kairn will be, the experiments behind it, the decisions taken at its review | done ([report](docs/developer/design/phase0/index.md)) |
| 1 | The vertical slice: numbers of one and two limbs (`double`, and `float`, which came with the proofs); addition, subtraction, multiplication, operations with a `T` operand, `ldexp`, comparisons, conversions; scalar, AVX2 and NEON; `Ball`; the generator; the Rocq proofs, with gradual underflow; the oracle with its quick and brute-force tiers; CI with the matrix of compiler flags and the object-code check; the self-test and the check of the floating-point environment; the documentation site | done ([report](docs/developer/results/milestone1.md)) |
| 2 | `Interval`; one enclosure interface shared by `Interval` and `Ball` (predicates, comparisons, hull, intersection, midpoint and radius, conversions, split); the building blocks as public functions (`two_sum`, `two_prod`, sums and products rounded down and up without changing the rounding mode); numbers built at compile time from an integer or a rational; `BallVector`, arrays of centers with one radius, and the functions on arrays (sum, dot product, `axpy`, convolution, an upper bound of the norm, the accumulator) with their bounds as functions of the length; containers in structure-of-arrays form and the packed SIMD type; exhaustive tests on small emulated formats; each cross-check of the quick tier in one process. It ends when the first client's ball path can be written against it | done; reviewed by the owner on 2026-11-23, and the changes decided then are made: the operators of `Packed<T, 1>`, guards in the constructors of two limbs, the report of the environment check out of line, reference pages that show every stored run of unchanged code; one limitation found then is documented and not repaired, a square passed straight in under Clang's `-ffp-contract=fast` ([report](docs/developer/results/milestone2.md#the-owners-review), [design](docs/developer/design/milestone2.md)) |
| — | The round-up interval, between Milestones 2 and 3 and not a milestone: the opt-in header `kairn/upward.hpp`, an interval of one limb of `float` or `double` kept in one SIMD register and computed under the rounding mode upward, used only for speed, with every special case answered as `Interval<T, 1>` answers it; scopes that set the mode, functions on two plain arrays, a self-check, a compile-time guard of the options and the CMake target `kairn::upward`; 24 kernels of their own, proved in the model of IEEE 754 with their sums and products rounded upward. Decided by the owner on 2026-11-24 and 2026-11-25; the default types do not change. Version 0.4.0 | in progress: the header, its kernels and their proofs (all 24 proved), its tests and its documentation are in the repository; not yet the job of MSVC in CI and the measurements on the shipped code; then the owner's review ([design](docs/developer/design/upward.md)) |
| 3 | The CUDA backend, for the kernels and loops that are proved today, with `float` limbs and with `double` limbs: the generated code for the device; the public operations callable from device code, element by element, with helpers for a program that spreads an array over the threads of a warp; a self-test on the device; the oracle's cross-checks run on the devices; and benchmarks of `float` against `double` on the GPUs. No new theorem is planned: by default CUDA's arithmetic is the IEEE arithmetic the proofs are about, which Phase 0 measured on three cards ([environment](docs/developer/design/phase0/environment.md#cuda)). To be measured there: what the device compiler does with a product the program passes in. The scope is the owner's decision of 2026-11-23; what this row held besides is in Milestone 4 | planned; not started |
| 4 | Numbers of three and four limbs: the networks first, marked unverified, then their Rocq proofs. The highest proof risk of the plan. Moved here from Milestone 3 by the owner's decision of 2026-11-23: the conversions of numbers and balls between limb types (`double` limbs to `float` limbs with the enclosure kept, and back), which need a second number format in the generator, its Rocq model and the oracle, and with them the bounds of a ball or an interval as numbers of another limb type ([design](docs/developer/design/milestone2.md#limbs-of-another-type)): two `float` limbs hold 48 bits, fewer than one `double`, so numbers of `float` limbs pass `double` only with four; the Metal backend, with the proofs for flush-to-zero arithmetic that its devices need, its device code and its self-test; and the flush-to-zero variant of the exhaustive tests on emulated formats, which needs those statements to be judged against | planned |
| 5 | Division and square root (two limbs from the existing proofs; three and four limbs by Newton iteration); matrix-vector and matrix-matrix products; dispatch to AVX-512 | planned |
| 6 | Eight limbs, and a number of limbs chosen at run time. Research: it ends with an algorithm that has an induction proof, or with a documented negative result | planned |
| 7 | Decimal input and output; the elementary functions; a C interface and bindings | planned |
| 8 | Release hardening: benchmarks against QD, CAMPARY, MultiFloats.jl, CCCL fpmp2, MPFR and Arb; the full tutorials and the gallery | planned |

Milestones 2 and 3 do not depend on 4, so balls with two-limb centers on the CPU and on the GPU
come before the risky proofs. No release happens before every public operation is proved,
documented and exercised by a tutorial example in CI; the milestones before that are development
snapshots.

## Build and test

Needs CMake 3.21 or later and a C++20 compiler, and on x86-64 a CPU with FMA; the tests also need
Python 3. (A project that only uses the library needs CMake 3.18.) From the repository root:

```sh
cmake -S . -B build                      # Release unless CMAKE_BUILD_TYPE says otherwise
cmake --build build
ctest --test-dir build --output-on-failure
cmake --install build --prefix PREFIX    # optional: then find_package(kairn) with PREFIX in CMAKE_PREFIX_PATH
```

With Visual Studio or Xcode, add `--config Release` to the build and `-C Release` to `ctest`. The
tests are the quick tier, the library with this compiler and its flags: cross-checks in which the
oracle judges every kernel compiled on random `binary64` and `binary32` operands, under each
contraction setting of the compiler, the tests of the public interface, whose every operation the
oracle judges too, the stored regression cases and the examples of the documentation. On
2026-11-22, with about 1 200 tests, its test step took 228 to 746 seconds with `--parallel 4` on
the hosted runners of the CI (four to five minutes on Linux and macOS, twelve on Windows; 192
seconds on a developer's Mac), over the two minutes per platform that the plan asks
([Testing](docs/developer/testing.md#time)). The full tier, `ctest --test-dir build/tests/full`, runs the rest:
the same on more operands, every operand of small formats through the generator's interpreter, and
the own tests of the generator, the oracle and the other tools. They are listed in
[Getting started](docs/getting-started/index.md#configure-build-and-test) and explained in
[Testing](docs/developer/testing.md).

The CMake target `kairn::kairn` holds the headers; a program includes `kairn/kairn.hpp`
([a first program](docs/getting-started/index.md#a-first-program)). On x86-64 the kernels need
hardware FMA: compile for such a CPU, or also link `kairn::fma`, which adds the option for your
compiler ([Hardware FMA](docs/getting-started/index.md#hardware-fma)).

## Documentation

The site is built with MkDocs from `docs/` ([how](docs/developer/documentation.md)):

```sh
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve             # http://127.0.0.1:8000
.venv/bin/mkdocs build --strict    # writes site/
python3 docs/tools/check_links.py
```

License: MIT.
