# Kairn: rigorous floating-point expansions with interval and ball arithmetic

*This copy of the original brief is lightly edited so that the first client project is not named.*

## Goal
Build Kairn, a fast C++20 library for floating-point expansions ("k-numbers"): unevaluated
sums of k IEEE-754 floats or doubles (generalizing double-double / quad-double), with
rigorous interval and ball (midpoint-radius) arithmetic on top. Every error bound has a
machine-checked proof, and the shipped code is generated from the same source the proofs
are about. Namespace `kairn`, CMake target `kairn::kairn`.

## Number types
- `Expansion<T, k>`, T ∈ {float, double}. Baked-in k: 1, 2, 3, 4, 8 (double); 1, 2, 3, 4
  (float). Plus a runtime-k generic path up to the exponent-range limit.
- k = 1 is a first-class instance with the same API and no overhead over plain T, so a
  client templated on k runs its first pass at k = 1 and reruns at k = 2, 4, 8.
- Define the normalization invariant precisely (which "nonoverlapping" notion), what each
  op requires and guarantees, and the canonical form of zero and signs.
- Precision depends on magnitude (the tail underflows: ~20 double / ~6 float components
  near |x| = 1). Document effective precision per (T, k) and magnitude; every bound
  includes an absolute (underflow) term.
- `Interval<T, k>`: inf-sup, k-number endpoints, modeled on IEEE 1788.1 set-based semantics:
  empty and unbounded intervals, defined division by intervals containing 0, no
  decorations. Comparisons are three-valued.
- `Ball<T, k>`: k-number center + one low-precision radius, rounded upward.
- `BallVector<T, k>`: N k-number centers sharing one radius (max-norm ball), for linear
  algebra. Define its semantics precisely in Phase 0.

## What "correct" means
- Containment: the exact real result is always inside the returned interval or ball, for
  all finite inputs, including near overflow and underflow and with subnormals.
- Tightness: for each op, state and prove an explicit bound of the form
  c(k,p)·2^(-kp)·|result| + η(k,p,emin). "Correct rounding" means outward rounding
  with this tightness, not rounding to a nearest k-number.
- Specify behavior for NaN, ±∞, ±0, overflow, and non-normalized inputs.

## Operations
- Core: + − × ÷ sqrt fma, abs, neg; conversions float/double ↔ k-number and k ↔ k'
  (mixed-k arithmetic = convert first). Mixed operands with plain T (k-number × T,
  k-number + T) as cheaper ops with their own bounds; exact scaling by powers of 2
  (ldexp, half), exact except on underflow, with that bound.
- Exact comparisons and sign: k-number vs k-number and k-number vs T, never
  approximated. Directed conversions to T (down, up, nearest) and an upper bound of |x|
  in T, all exact roundings.
- Accuracy variants where they differ in cost (e.g. fast vs accurate addition), each with
  its own proven bound; the default is the accurate one.
- Decimal string parsing and printing (outward-rounded for intervals and balls).
- Elementary functions (exp, log, sin, cos, tan, atan, sinpi, cospi, pow, …) with proven
  bounds: high-precision constants, argument reduction, polynomial error bounds.
- Batch kernels: sum, dot, axpy, convolution (polynomial product), gemv, gemm,
  elementwise maps. Fused, skipping renormalization inside loops where the proof allows.

## Platforms
- CPU: Windows (MSVC, clang-cl), macOS, Linux (GCC, Clang); x86-64 and AArch64, 64-bit only.
  Baseline: x86-64-v3 (AVX2+FMA) and AArch64 NEON; optional AVX-512 path for batch
  kernels, chosen at runtime; a scalar reference path always exists. SVE is out of scope
  for v1.
- GPU: CUDA (float and double), Metal (float only).
- Test hardware: Apple Silicon Mac, NVIDIA consumer (GeForce) GPU, Windows x64,
  Linux x86-64. Linux AArch64: build in CI and test under QEMU user-mode emulation
  (correctness only; no performance numbers from QEMU). Windows AArch64: compile-only
  in CI.

## Floating-point environment (non-negotiable)
- All arithmetic in round-to-nearest-even. No fesetround or dynamic rounding modes.
  Directed results come from exact error terms and round-to-nearest successor emulation.
  CUDA directed-rounding intrinsics and AVX-512 embedded rounding are allowed as fast
  paths only if proven equivalent.
- Kairn is header-only, so all of its code (C++, CUDA device code, MSL) is compiled in
  the client's translation units with the client's flags, and clients may enable FMA contraction (GCC contracts by
  default in C++; nvcc by default on the device). Such code must be correct either way:
  error-free transformations use only patterns contraction cannot change (TwoSum,
  Fast2Sum, TwoProd via an explicit fma), and every other proof covers each a·b + c both
  fused and unfused. CUDA device code uses `__fadd_rn`/`__fmul_rn`/`__fma_rn` (and the
  float versions), which nvcc never contracts. Where a compiler offers a reliable scoped
  switch (Clang's `#pragma clang fp contract(off)` inside function bodies), use it as
  extra protection, never as the only one: GCC has none.
- CI builds the test suite across a matrix of client-like flags (contraction off and
  forced on, -O0 to -O3, -frounding-math, GCC/Clang/MSVC/nvcc) and checks the
  disassembly of the generated networks for fused instructions the IR didn't ask for.
- x86 headers stop the build with `#error` unless hardware FMA is enabled (`__FMA__`, or
  `__AVX2__` on MSVC): without it std::fma becomes a slow software call.
- No fast-math anywhere. Headers stop the build with `#error` under `__FAST_MATH__`,
  `__FINITE_MATH_ONLY__`, MSVC `/fp:fast`, or nvcc `--use_fast_math`. A client compiling
  with `-frounding-math` must still work.
- Inline self-test: a header function the client calls once at startup (host, CUDA
  device and Metal), compiled with the client's own flags, that checks rounding,
  subnormal handling and contraction behavior where they can be observed, and returns
  a clear error instead of running with broken assumptions.
- SSE2+ only (no x87). Hardware FMA required for TwoProd.
- CPU: check MXCSR/FPCR (FTZ/DAZ, rounding mode) at every batch-API entry and in debug
  builds for scalar ops; fail loudly if wrong. Document it as a precondition. Kairn never
  changes the FP environment itself; it provides a cheap `kairn::environment_ok()` query,
  so a client that runs other code in a directed rounding mode can verify that it
  switched back to nearest before calling Kairn.
- Metal may flush float denormals and may round toward zero, with no way to disable
  either. Prove Metal bounds under a flush-to-zero model. A startup self-test refuses to
  run if the device rounds toward zero or breaks any other assumption.
- CUDA: no --use_fast_math; -ftz=false -prec-div=true -prec-sqrt=true.

## Architecture
- Single source of truth: each kernel is written once as a branch-free straight-line
  network of add/sub/mul/fma (minimal control flow only where proven necessary) in a
  small IR/DSL. A generator emits (a) the formal model + theorem per kernel and
  (b) scalar C++, raw intrinsics for AVX2 / AVX-512 / NEON, CUDA, and MSL.
  The generator is part of the trusted base: keep it small and auditable.
- Batch APIs use structure-of-arrays layout (component i of all numbers contiguous),
  one number per SIMD lane / GPU thread.
- C++20, CMake, License: MIT. No compiler extensions in public headers (no `__int128`:
  MSVC lacks it).

### Delivery: header-only
Kairn is a header-only library (CMake INTERFACE target `kairn::kairn`). Reasons: scalar
ops at k = 1–2 are a few dozen flops and must inline (k = 1 must cost the same as plain
T), `constexpr` needs headers, and client GPU kernels need the source. Consequences to
handle:
- Every header is correct under any client flags (the contraction rule above).
- Scalar and inline code targets the ISA the client compiles for. Batch kernels may also
  dispatch at runtime to wider ISAs (AVX-512) via per-function target attributes and CPU
  detection, all inside the headers (GCC/Clang `target` attribute; MSVC needs no flag
  for intrinsics).
- Keep client compile times reasonable: explicit instantiation helpers, one header per
  feature, large k networks only instantiated when used. Report compile times for the
  largest networks.
- The C ABI for Python/Julia/Rust bindings is a thin, optional shim compiled from the
  headers by the bindings' own build (bindings need a binary anyway); it is not part of
  the C++ library and adds no code of its own.

## API for generic clients
Kairn's main users will be numerical libraries that are templated on their scalar and
want to swap float/double for k-numbers to tighten their own error bounds. Design for
that, with no client-specific code in Kairn:
- Regular value types: Expansion, Interval and Ball are trivially copyable,
  standard-layout, default-construct to zero, hold no heap memory, and work in
  `std::array` and plain C arrays. Public read access to the limbs, and an unchecked
  constructor from limbs (precondition: normalized), so clients can move them through
  their own storage, GPU buffers and warp shuffles.
- One scalar-traits interface, `kairn::traits<X>`, specialized for float, double and every
  `Expansion<T, k>`: limb type, k, precision, and the error-model constants below, so client
  code reads the same for all of them.
- Error model exported as data. For every op and accuracy variant, a proven bound in
  standard-model form: |computed − exact| ≤ unit·|exact| + tiny (or ≤ unit·(|a| + |b|) +
  tiny where that is all that holds; say which), with unit and tiny as constexpr
  constants rounded up. For batch kernels, the bound as a constexpr function of n in
  Higham's form (γ(n)·Σ|terms| + n·tiny). A client's existing proofs written for
  u = 2^-53 then carry over by substituting Kairn's constants.
- Compile-time constants: `constexpr` construction of a k-number from an integer or a
  rational p/q, with its error bound and an exactness flag, computed with integer
  arithmetic only (so it works in constant evaluation under `-frounding-math`). Core
  arithmetic is `constexpr` too, using a Dekker-split product at compile time (std::fma
  isn't constexpr in C++20), proven like the runtime path.
- Same API on host and device: scalar types and ops are `__host__ __device__ constexpr` in
  CUDA (no `--expt-relaxed-constexpr` needed) and available in MSL, usable inside the
  client's own kernels, not only through Kairn's batch launches. Device code has no
  recursion, no allocation and a small, fixed stack. Provide warp-level helpers for CUDA
  (shuffle, broadcast, min/max reductions of Expansion, Interval and Ball).
- `Interval<T, k>` and `Ball<T, k>` share one enclosure interface (lower, upper as k-numbers,
  directed conversions of the bounds to T, midpoint, radius, contains, certainly
  positive/negative/zero, hull, intersection, split), plus conversions both ways
  (interval → ball, ball → interval, outward), so client algorithms can be generic over
  the enclosure type and pick the faster one per k.
- A packed SIMD type (W lanes of k-numbers in registers, from the generator's per-ISA
  code) and SoA containers/views with proxy element access, so clients can write their
  own vector loops over the same proven networks.
- Phase 0 checks this API against a real client: the first client, a branch-and-bound solver
  over Bernstein polynomials that already plans k-number reruns of its precision-limited
  queries. Report what the first client would need that Kairn doesn't provide.

## Verification
- Pick the proof assistant in Phase 0 and justify it (e.g. Rocq + Flocq, which has
  existing double-word proofs to reuse, vs Lean 4 or Isabelle).
- Proofs are parametric in precision p, exponent range, and underflow model (gradual vs
  flush-to-zero), so one proof covers float, double, and Metal.
- Baked-in k: verify every generated instance (automatic/SMT-assisted where possible).
  Runtime k: parametric proof by induction on k; looser bounds are acceptable.
- Also prove: ball radius propagation, interval outward rounding, conversions, decimal
  I/O, and batch kernels (for the reduction orders actually used).
- ÷, sqrt and elementary functions may land early behind an UNVERIFIED flag; no release
  until their bounds are machine-checked.
- CI rejects admits/sorry and any axiom not on an approved list, and prints the
  assumptions of every theorem.
- Prior art to study and cite: QD, CAMPARY, MultiFloats.jl, CCCL fpmp2, FLINT/Arb, kv,
  Muller–Rideau's Coq double-word formalization, Zhang–Aiken FPAN verification.

## Testing (experimental validation, independent of the proofs)
Proofs are the guarantee; testing catches errors in theorem statements, the generator,
compilers, and hardware. Build a test system around an exact-arithmetic oracle, with a
quick tier and a brute-force tier.

### Oracle
- Shares no code with the library. Exact dyadic-rational arithmetic (GMP/FLINT big
  integers or rationals) for + − × fma, conversions, and exact sums/dot products.
  Rigorous high-precision enclosures (MPFR with directed rounding, or FLINT/Arb at far
  higher precision) for ÷, sqrt, elementary functions and decimal I/O, raising the
  precision until every verdict is decisive.
- Cross-check the oracles against each other on a sample, and inject deliberately wrong
  results to prove the checker catches them.

### Checks on every case
- Containment: the exact result (or the oracle's enclosure of it) lies inside the
  returned interval or ball. For interval/ball inputs, also sample exact points inside
  the inputs and check that their exact images are contained.
- Bound: measured error ≤ the proven bound for that (op, T, k). Record max(error / bound)
  per op, so loose bounds show up as well as violations.
- Invariants: every output satisfies the normalization invariant; special values (NaN,
  ±∞, ±0, empty, unbounded) behave as specified.
- Every backend (scalar, AVX2, AVX-512, NEON, CUDA, Metal) runs the same cases and is
  checked against the oracle, never against another backend.

### Case generation
- Cases are stored as exact bit patterns (hex floats), never decimal: op, (T, k), inputs,
  oracle result or enclosure, bound. Generation is deterministic and seeded, so any case
  can be regenerated from (generator, seed, index).
- Strata, each with its own share of cases: random across the full exponent range;
  catastrophic cancellation; near overflow; near underflow and subnormals (plus
  flush-to-zero for Metal); powers of two and round-to-even ties; components at the
  extremes of the normalization invariant; long carry chains; ill-conditioned sums and
  dot products with prescribed condition numbers; intervals and balls that contain 0
  or are degenerate, huge, empty or unbounded; for elementary functions, hard-to-round
  arguments, large trig arguments, and inputs near overflow/underflow thresholds.
- Adversarial search: a fuzzer/optimizer that maximizes error / bound, seeded with
  near-misses from the proofs and any SMT counterexamples.

### Tiers
- Quick tier: a fixed, checked-in corpus (edge cases from every stratum, all regression
  cases, a small random sample) that runs in under ~2 minutes per platform. Runs on
  every commit in CI, including under QEMU.
- Brute-force tier: generated on the fly from seeds and sized by a time budget (default
  ~3–4 hours per machine), parallel across all CPU cores and GPU batches. Runs nightly
  and before every milestone report and release, on each real test machine. Reports
  cases run per stratum, cases/second, max error/bound per (op, T, k, backend), and the
  worst inputs found.
- Exhaustive tier (part of the brute-force run): the scalar core instantiated on tiny
  emulated formats (p = 8–11, small exponent range, gradual and flush-to-zero variants),
  covering all input combinations for small k where feasible and dense sampling
  otherwise.

### Failures
- Any containment failure or bound violation blocks release. Shrink the failing case
  automatically, add it to the quick tier as a regression test, and report whether the
  fault is in the theorem statement, the generator, the code, the compiler, or the
  hardware.
- For ops still marked UNVERIFIED, brute-force results are empirical maxima only; never
  publish them as the bound.
- Performance benchmarks run separately from correctness runs.

## Performance
- At each k: within ~1.2× of the fastest of QD, CAMPARY, MultiFloats.jl, CCCL fpmp2 for
  non-rigorous ops; faster than MPFR and FLINT/Arb for rigorous ops. Publish benchmarks.
- The CUDA target is a consumer GPU, where FP64 runs at a small fraction of FP32
  throughput (1/64 on recent GeForce). For each precision target, benchmark
  float-limb vs double-limb expansions on CUDA and report the crossover; account for
  float's narrower exponent range when recommending one.
- Workloads (propose a priority order in Phase 0): linear algebra (dot/gemv/gemm),
  GPU simulation/ODE elementwise loops, verified computation (balls/intervals),
  geometry predicates.
- Bitwise reproducibility across backends is not required; only the bounds must hold.

## Thread safety
- No global mutable state, no lazily initialized tables (constexpr only), never modify
  the FP environment, fully reentrant. GPU kernels share no mutable state but outputs.

## Documentation and website
Extensive user documentation and tutorials, published as a website that builds locally.
Follow the wildmeshing-toolkit site as the template: study
https://wildmeshing.github.io/wildmeshing-toolkit/ and, in
https://github.com/wildmeshing/wildmeshing-toolkit, its `mkdocs.yml`, `docs/`,
`docs/developer/documentation.md` and `.github/workflows/docs.yml`. Copy its structure and
conventions, not its content.

### Tooling (as in the template)
- MkDocs + Material for MkDocs, built from `docs/` by `mkdocs.yml`, with pinned versions in
  `docs/requirements.txt` (mkdocs, mkdocs-material, mkdocs-gen-files, mkdocs-literate-nav).
- Theme features: light/dark palette toggle, navigation tabs and sections, search with
  suggestions, code copy buttons, edit-this-page links, per-heading permalinks.
- Markdown extensions: admonitions, details, content tabs (show the same example in
  C++ / CUDA / Metal / Python side by side), footnotes, tables, `pymdownx.snippets`, and
  MathJax via `pymdownx.arithmatex` (the docs are math-heavy: bounds, invariants).
- C++ API reference generated by Doxygen and served under `/api/`.
- Build locally with `pip install -r docs/requirements.txt`, then `mkdocs serve` (live
  preview at http://127.0.0.1:8000) and `mkdocs build --strict` (any broken link or
  anchor fails the build). CI runs the strict build on every commit and keeps the built
  site as an artifact. Deploying to GitHub Pages is optional, for later.

### Site structure
- Home: what the library is, what it guarantees, where to go next.
- Getting started: installation per platform (CMake package, required compiler
  flags), a first program, choosing T and k, troubleshooting (fast-math, FMA contraction,
  FTZ/DAZ detected, Metal self-test failure, UNVERIFIED ops).
- Concepts: floating-point expansions and normalization; precision vs magnitude (table per
  (T, k)); intervals vs balls vs BallVector and when to use which; what "correct" means
  (containment, tightness, bound formulas); the FP-environment contract; thread safety;
  verified vs UNVERIFIED ops; CPU vs GPU and float vs double limbs.
- Tutorials, one per target workload at least: accurate sum and dot product; dense linear
  algebra (gemv/gemm, verified solve with balls); ODE time-stepping on CUDA and Metal;
  rigorous root enclosure (interval Newton); robust geometric predicates (orientation
  test); elementary functions; decimal I/O; making a templated numerical library generic
  over float, double and k-numbers (traits, error-model constants, rerunning at higher k);
  calling the library from Python, Julia and Rust through the C ABI.
- Gallery: accuracy and performance plots (error vs bound, throughput per backend and k),
  generated at build time from stored brute-force and benchmark results.
- Reference: one page per operation with the proven bound formula, its preconditions, the
  formal theorem's name and source file, verification status, and the max error/bound
  measured by the latest brute-force run. Plus the C ABI reference and the Doxygen C++ API.
- Proofs: how to check the proofs locally, and a map from every plain-math theorem on the
  site to its formal statement.
- Developer guide: architecture and the generator, adding an operation end to end (IR,
  proof, backends, tests, docs), the testing tiers, benchmarks, writing documentation,
  contributing, design notes and the decisions log.
- About: citing (CITATION.cff), changelog, license (MIT), related libraries.

### Conventions (as in the template)
- Single source of truth: reference pages are generated at build time (with
  mkdocs-gen-files) from the generator's IR and metadata, the proof files, and the latest
  test results. Nothing generated is committed. A `--check` mode, run in CI, fails when an
  op lacks a doc, a bound, or a reference entry.
- Every code example is a file under `docs/examples/` (`cpp/`, `cuda/`, `metal/`,
  `python/`, `c/`), included into pages with snippet section markers. A page never
  contains example code that isn't in one of those files. Every example is built and run
  by ctest as part of the quick tier (GPU examples on machines that have the GPU) and
  checks its own output.
- Every public API entity has a Doxygen comment; Doxygen warnings fail the docs build.
- Write for a user who knows C++ but not floating-point error analysis: introduce each
  concept before using it, and link every claim about a bound to its reference page.

## Workflow
- Phase 0, then STOP for my review: spec and feasibility report covering representation
  and invariants, theorem statements in plain math for every op, exponent-range analysis
  per (T, k), per-backend FP guarantees, proof assistant choice, generator design,
  header-only design (runtime dispatch, compile times), the API check
  against the first client, documentation outline, milestone plan, and the decisions you need
  from me.
- Milestone 1 (vertical slice): double, k=1 and k=2, scalar + AVX2 + NEON, + − ×, Ball, proofs,
  the oracle with both test tiers, CI, and the website skeleton (Home, Getting started,
  one tutorial, generated reference pages for the ops that exist).
- Then widen: more k, float, runtime k, Interval, BallVector, CUDA, Metal, ÷ and sqrt,
  batch kernels, decimal I/O, elementary functions. Each milestone ships its docs:
  concepts, tutorials, reference and examples for what it added.
- After each milestone, a short report: what's done, bounds proven, brute-force results,
  benchmarks, docs added, open issues. Keep a decisions log.
- No release until the site covers every public op, every tutorial example runs in CI,
  and `mkdocs build --strict` passes.

## Ground rules
- Never weaken a theorem, add an axiom, or relax a guarantee without flagging it.
- Cite the source of every algorithm and bound; check licenses before reusing code.
- If a requirement is infeasible, say so in Phase 0 with evidence instead of quietly
  working around it.
