# Decisions

## Decisions from the Phase 0 review

Ten questions were put to the project owner at the end of Phase 0, each with a recommendation.
All ten were answered on 2026-11-18. Each section below keeps the question and its reasoning and
ends with the decision.

| | Question | Decision |
|---|---|---|
| D1 | Proof assistant and allowed axioms | Rocq 9 with Flocq 4.2; exactly the four axioms of Rocq's real numbers |
| D2 | May an SMT answer count as a proof? Are per-format proofs acceptable? | No. Yes, flagged per operation |
| D3 | $k = 8$ and runtime $k$ | In scope, late (Milestone 6); selects allowed; constants may grow with $k$ |
| D4 | Normalization invariant | $x_i = \mathrm{RN}(x_i + x_{i+1})$, confirmed |
| D5 | Non-finite results | IEEE-like by default, with `kairn::finite::` variants |
| D6 | One limb under Clang's default contraction | Unfused by default; `KAIRN_K1_CONTRACT` opts in |
| D7 | Generated headers | Committed, with a CI freshness check |
| D8 | Workload priority | Balls, linear algebra, elementwise GPU loops, predicates |
| D9 | Runtime dispatch state | A `Backend` value the client holds |
| D10 | Test infrastructure | No self-hosted runners: experiments run directly on the test machines, CI is separate; clang-cl and the ARM64 tools are installed on the Windows machine; Intel SDE for AVX-512 |

### D1 Proof assistant

**Rocq 9 with Flocq 4.2, and an axiom allow-list of exactly four entries**
(`ClassicalDedekindReals.sig_forall_dec`, `ClassicalDedekindReals.sig_not_dec`,
`FunctionalExtensionality.functional_extensionality_dep`, `Classical_Prop.classic`).
Reasons and the comparison with Lean 4 and Isabelle are in
[Verification](verification.md#proof-assistant-rocq-with-flocq); the pipeline was run end to end
in Phase 0 and these four are what every theorem about real numbers in Rocq depends on.
*Recommended: approve both.*

**Decision: both approved.** A fifth axiom needs the owner's approval before any proof uses it;
CI fails on anything outside the list.

### D2 What counts as machine-checked

The only existing verification of the 3- and 4-limb networks is an SMT solver's unchecked answer
on an abstraction. Two questions:

1. May a solver's `unsat` without a certificate checked by Rocq ever stand in for a proof?
   *Recommended: no.* It would put Z3 and an unpublished lemma base in the trusted base.
2. If a proof parametric in the precision is not achieved for some operation, is a pair of
   kernel-checked proofs, one for `float` and one for `double`, acceptable? *Recommended: yes*,
   flagged on that operation's reference page. It will certainly be the case for elementary
   functions, whose polynomials and tables depend on the target precision.

**Decision: no to the first, yes to the second.** Only a proof checked by Rocq's kernel counts;
the 3- and 4-limb operations carry `UNVERIFIED` until one exists, and the SMT result is cited as
evidence, not as a status. Per-format proofs are accepted where a parametric one is not achieved,
and the operation's reference page says so.

### D3 Eight limbs and runtime k

No algorithm for five or more limbs has a correctness proof of any kind in the literature, and the
one library that shipped them withdrew them as broken
([Operations](operations.md#eight-limbs-and-runtime-k)). Kairn has to invent and prove one.
Options:

- **(a) Recommended.** Keep $k = 8$ and runtime $k$ in scope but late (Milestone 6), after the
  first client's path and the $k \le 4$ proofs; accept selects (branch-free conditional moves)
  inside the kernels; accept constants that grow with $k$.
- (b) Ship them early behind `UNVERIFIED` with a branching algorithm, so that clients can
  experiment, and prove later. Fast to deliver, but a long-lived unverified path in a library
  whose point is verification.
- (c) Drop baked-in $k = 8$ from the first release.

**Decision: (a).**

### D4 Normalization invariant

$x_i = \mathrm{RN}(x_i + x_{i+1})$ for every $i$ ([Numbers](numbers.md#the-normalization-invariant)).
*Recommended: confirm.* The consequence to be aware of: representations are not unique, so
equality and ordering are computed, not read off the limbs.

**Decision: confirmed.**

### D5 Non-finite results

Should `Expansion` arithmetic return canonical $\pm\infty$ and NaN the way IEEE does
(an estimated 10 to 20% on a 2-limb addition, to be measured), or only promise "not finite"?
*Recommended: IEEE-like by default, with `kairn::finite::` variants and the batch kernels skipping
the canonicalization.* Generic client code compares against infinities and expects
$\infty + 1 = \infty$; kernels in hot loops do not need it.

**Decision: as recommended.** Milestone 1 measures the cost and reports it.

### D6 One limb and contraction under Clang

Under Clang's default (`-ffp-contract=on`), `a * x + y` on `double` is fused and the same
expression on `Expansion<double, 1>` is not ([Library](library.md#one-limb)). Options:

- **(a) Recommended.** Leave $k = 1$ unfused under Clang's default and document it;
  `KAIRN_K1_CONTRACT` opts into a pragma that restores identical code. Rationale: with the pragma
  on, a client who passed `-ffp-contract=off` to get reproducible results would get fused $k = 1$
  arithmetic anyway.
- (b) Pragma on by default, macro to turn it off: matches the brief's "no overhead" literally.

On GCC there is nothing to decide (identical code), and on MSVC the auto-vectorization gap cannot
be closed by either option.

**Decision: (a).**

### D7 Generated headers

*Recommended: commit the generated kernel headers* under `include/kairn/gen/`, with CI
regenerating them and failing on any difference. A header-only library should work from a plain
clone, and no client build should need Python. The alternative is to generate at CMake configure
time and commit nothing generated.

**Decision: commit them.**

### D8 Workload priority

*Recommended order:* verified computation with balls (the first client's workload), linear
algebra, elementwise GPU loops, geometric predicates ([Plan](plan.md#performance-targets)).

**Decision: that order.**

### D9 Runtime dispatch state

Choosing AVX-512 at run time needs the result of CPU detection. *Recommended: a `Backend` value
the client obtains once and passes* (default: the compile-time baseline), which keeps the "no
global mutable state" rule intact. The alternative is one idempotent atomic cache inside the
headers: more convenient, and a deliberate exception to that rule.

**Decision: the `Backend` value.**

### D10 Test infrastructure

Things only the owner can provide or approve:

1. **CI runners.** The brute-force tier, CUDA and Metal need real machines. The question was
   whether the four test machines may be registered as self-hosted runners.
2. **clang-cl and the MSVC ARM64 tools** are not installed on the Windows machine. The brief lists
   clang-cl as a supported compiler and Windows AArch64 as compile-only; may both be installed?
3. **AVX-512.** None of the four machines has it. Options: correctness under Intel SDE only
   (recommended for now), a hosted runner, or access to another machine.
4. **The consumer-GPU machine** is shared and heavily loaded. It is used for GPU correctness and
   the float-versus-double numbers only, and the other Linux machine for anything timed on the
   CPU.
5. **Linux AArch64** runs under QEMU user-mode on a hosted runner, as the brief says.

**Decision:**

1. **No self-hosted runners.** Experiments, the brute-force tier, GPU runs and benchmarks are run
   directly on the test machines, and their results are recorded in the repository as in Phase 0.
   CI is set up separately on hosted runners and covers what those can run: the flag matrix, the
   quick tier, the proofs, the generated-header freshness check and the documentation build. The
   repository becomes public when CI is set up.
2. Both components are installed.
3. Intel SDE.
4. and 5. As stated.

## Deviations from the brief, flagged

Per the ground rules, everything in this report that weakens, changes or cannot meet a statement
of the brief:

| # | The brief says | What Phase 0 found | Proposed handling |
|---|---|---|---|
| 1 | TwoSum, Fast2Sum and TwoProd with an explicit `fma` are patterns contraction cannot change | False once inlined together: Clang on AArch64 with `-ffp-contract=fast` and MSVC with `/fp:contract` duplicate the rounded product into later additions and silently reduce the result to single-limb accuracy | Rule R1/R2: no product feeds an addition; TwoProd is two FMAs ([Environment](environment.md#contraction)). A strengthening, at the cost of an FMA per product |
| 2 | Use Clang's scoped `fp contract(off)` as extra protection | It is ignored under `-ffp-contract=fast`, the one case that needs it | Not relied on. Milestone 1 does not emit it either (recorded at the Milestone 1 audit): by rule R1 a generated kernel contains no plain product for it to protect, and the product of the program at a kernel's boundary is handled by the guard of rule R3, which the pragma would not replace |
| 3 | Raw intrinsics for AVX2, AVX-512, NEON | Intrinsics are contracted like scalar code | Same rule in the SIMD backends |
| 4 | $k = 1$ has no overhead over plain `T` | True on GCC; on Clang's default one instruction per multiply-add unless a pragma is used; MSVC does not auto-vectorize loops over the wrapper | [D6](#d6-one-limb-and-contraction-under-clang); batch kernels for loops |
| 5 | Every bound has a machine-checked proof; verify every baked-in instance | No published proof of any kind exists for $k \ge 5$; $k = 3, 4$ are SMT-only; every existing proof ignores underflow | [D2](#d2-what-counts-as-machine-checked), [D3](#d3-eight-limbs-and-runtime-k); operations stay `UNVERIFIED` until proved |
| 6 | Proofs parametric in $p$, so one proof covers `float`, `double` and Metal | Achievable for the arithmetic kernels (planned); not for elementary functions; possibly not for $k = 3, 4$ | [D2](#d2-what-counts-as-machine-checked) |
| 7 | Core arithmetic is `constexpr` with a Dekker product, proven like the run-time path | Feasible and prototyped; consequence: compile-time and run-time results of one expression can differ in the last bits, both within the bound | Documented |
| 8 | Signs of zeros specified | The networks do not preserve the sign of a zero | Specified as unspecified ([Numbers](numbers.md#zero-and-signs)) |
| 9 | Interval and Ball at every $k$ | An `Interval<T, 1>` bound costs about ten operations against one with a hardware rounding mode, which Kairn may not use | Fast paths on CUDA and AVX-512; clients keep native intervals at $k = 1$ on other targets |
| 10 | `float` limbs on GPUs, including Metal | `float` k-numbers keep full precision only above $10^{-31}$ ($k = 2$) to $10^{-16}$ ($k = 4$), and on Metal above $10^{-24}$ to $10^{-9}$ | Inherent to the format; documented prominently |
| 11 | AVX-512 path, clang-cl, Windows AArch64 | No AVX-512 machine; clang-cl and ARM64 tools not installed; none of the three was run in Phase 0 | [D10](#d10-test-infrastructure). State after Milestone 1: clang-cl is tested in CI on the hosted runners; Windows on AArch64 is not supported, the headers stop the build with MSVC on that architecture because no FMA primitive has been chosen and measured there, and CI has no compile-only job for it; AVX-512 belongs to Milestone 5 |
| 12 | Interval semantics modeled on IEEE 1788.1 | The standard is paywalled; semantics were taken from the P1788 drafts and implementations | To be checked against the standard before Milestone 2 |
| 1b | (the same statement, at the boundary with the program) | Found in Milestone 1: R1 and R2 protect Kairn's own code, not a product the program computes and passes in. `x + a * b` was fused into the kernel's addition by GCC at its default, Apple clang on AArch64 with `-ffp-contract=fast` and MSVC with `/fp:contract`, giving a wrong, normalized result | Rule R3: every value that enters from the program passes through a guard, one addition of zero ([Architecture](../../architecture.md#the-kernel-ir)) |
| 13 | The oracle computes with GMP or FLINT integers and rationals | Milestone 1's oracle uses Python's built-in exact integers and fractions: the same exactness, no dependency, and code that is easy to audit; it is slower than a compiled oracle would be | Kept for $+$, $-$, $\times$, conversions and comparisons. MPFR or Arb enclosures come with division and square root (Milestone 5), where exact rationals no longer suffice |
| 14 | Core arithmetic is `constexpr`, with a Dekker product | Additions, subtractions, negation, absolute value, comparisons, conversions and constructors are, and every operation on one limb. Not yet `constexpr`: the products of two limbs, `ldexp` and `half` on two limbs, and every arithmetic operation of `Ball` (sums, differences, products, scalings). Their kernels contain fused operations (the two-limb products and scalings, and the radius of every ball), and only the exact product has a variant for constant evaluation with its proof. The first statement of this deviation named the two-limb products only; the Milestone 1 audit corrected it | Variant kernels for those operations with their own proofs, in a later milestone; until then they are run-time operations |
| 15 | Reference pages are generated when the site is built | They are generated by a tool and committed, with a check in CI that they are fresh, like the generated headers ([D7](#d7-generated-headers)) | Kept: a reader of the repository sees them, and a stale page fails CI. The site's requirements therefore list neither `mkdocs-gen-files` nor `mkdocs-literate-nav`: the tool also writes the Reference part of the navigation into `mkdocs.yml` |
| 16 | The fix-up for non-finite results costs 10 to 20% of a 2-limb addition (the estimate behind [D5](#d5-non-finite-results)) | Measured first on props of the harness: 19 to 58% of a packed addition and 70 to 106% of a packed multiplication as listed; 0 to 6% in a chain of dependent scalar operations when placed behind a branch. Remeasured on the generated kernels and the public operators ([Benchmarks](../../results/bench-milestone1.md#2-the-fix-up-for-non-finite-results), commit `f26e4c2`): `x + y` over `kairn::finite::add` costs at most 7% in a scalar chain on the three machines; 8 to 19% in a scalar loop where the compiler treats the two loops alike (MSVC, GCC 13 -O2, Clang 18, GCC 16) and 1.65 to 2.24 times where it vectorizes the core's loop and not the operator's (Apple clang, GCC 13 -O3); the packed `add_2_2` 16 to 21% in a loop and 11 to 17% in a chain on Zen 2, 33 to 54% and 21 to 28% on the M3, 27% and 53% on the i5. The estimate holds for scalar chains everywhere, for scalar loops with GCC 16, Clang 18, MSVC and GCC 13 at -O2, and for packed code on Zen 2 only (at its upper edge in a loop); a multiplication costs more (packed `mul_2_2`: 70 to 105% in a loop) | D5 stands until the owner says otherwise; `kairn::finite::` is the opt-out, and batch kernels will skip the fix-up and canonicalize once |
| 17 | Shipped code is generated from the descriptions the proofs are about, and every bound is machine-checked | One composition is written by hand in the public header: `ldexp(x, n)` when $2^n$ is not a number of `T`, which calls the proved kernel two or three times. Each call has its proved statement, but what the composition returns ($2^n x$ exactly or an infinity when scaling up; within $\eta$ when scaling down) is argued in the design and tested through the oracle, not machine-checked ([Milestone 1 statements](../milestone1.md#scaling-beyond-the-powers-of-two-of-the-format)). The same holds for one limb: `ldexp` on `Expansion<T, 1>` beyond the powers of two of `T` is two or three products by powers of two written in the header, arranged so that only one of them rounds; that it returns what one correctly rounded product would is argued in a comment and tested, not machine-checked. By design ([D6](#d6-one-limb-and-contraction-under-clang)) the one-limb type is a thin layer over the operations of `T`, whose statements `add_1_1` and `mul_1_1` describe one rounded operation. Also written by hand, with no generated statement: `sign`, `isfinite` and `is_normalized` (tests of bit patterns, and for two limbs one addition compared with the leading limb) | Documented as not machine-checked wherever it is stated; to become a generated kernel with a proved statement |
| 18 | The quick tier is a fixed, checked-in corpus | Its random cases are not stored: the oracle generates them at test time from a fixed seed, every stratum and edge case included, and each case is a function of the kernel, the format, the seed and its index alone. Since the Milestone 1 audit, the cases that found a problem and those that came closest to a claim are stored in `tests/regression/cases.txt` and run through every runner of the quick tier (`regression.cases`); a problem the line protocol cannot carry (a product of the program fused into a kernel) has a test of its own | Kept for the random sample: it is the same on every run and every machine, and no file can go stale. A case that fails is shrunk (`kairn-oracle shrink`) and added to that file with where it was found and the class of its fault (statement, generator, code, compiler or hardware) |
| 19 | Proofs are parametric in precision, exponent range and underflow model (gradual or flush-to-zero), so one proof covers `float`, `double` and Metal | Found at the Milestone 1 audit. The proofs of Milestone 1 hold for every precision and every exponent range, and for gradual underflow only. Phase 0 planned to prove each kernel once with the underflow error of its building blocks kept symbolic, starting in Milestone 1 ([Verification](verification.md#underflow-models)); that was not built. The models and proofs use Flocq's format with gradual underflow and its properties directly, among them that a sum which lands in the subnormal range is exact, which is false when results are flushed to zero. The statements differ too: with gradual underflow a sum has no underflow term in its bound, with flushing it has one | `float` and `double` with gradual underflow, which is every backend of Milestones 1 and 2, are covered. The flush-to-zero statements that Metal needs (Milestone 3) need proofs of their own, or the building blocks' lemmas restated with a symbolic underflow error first; the plan names that framework as the risk of Milestone 3, and none of it exists yet |
| 20 | The brute-force tier runs nightly and before every milestone report, on each real test machine | Found at the Milestone 1 audit. It runs by hand before a milestone report, on the Mac, the Linux machine and the Windows machine; nothing runs it nightly, and the fourth machine, the GPU workstation, was not used for these CPU-only runs. Decision [D10](#d10-test-infrastructure) keeps CI on hosted runners and off the test machines | For the owner: a nightly run with a small budget on the hosted runners, a scheduled job on the test machines themselves, or by hand as now |

## Decisions log

Decisions taken within Phase 0, at its review, and since, each reversible at the owner's word.

| Date | Decision | Reason |
|---|---|---|
| 2026-11-18 | Repository `danielepanozzo/kairn`, MIT, copyright Daniele Panozzo; private until CI is set up | The owner's instruction |
| 2026-11-18 | D1 to D10 decided as recorded [above](#decisions-from-the-phase-0-review) | Phase 0 review |
| 2026-11-18 | No self-hosted runners; experiments run directly on the test machines; CI on hosted runners | Phase 0 review (D10) |
| 2026-11-18 | A rounded product is always `fma(a, b, +0.0)`; generator rules R1 and R2 | Contraction experiment, 23 configurations |
| 2026-11-18 | Fast-math sub-flags are rejected by `#error` where a macro exists and by the self-test elsewhere | Clang defines no macro for three of them |
| 2026-11-18 | `__builtin_is_constant_evaluated()` instead of `std::is_constant_evaluated()`; no `nextafter` in device code | nvcc diagnostics |
| 2026-11-18 | Kernels are emitted as non-template functions, one statement per operation | MSVC template parsing time; Clang per-expression contraction |
| 2026-11-18 | Kernels above $k = 2$ are never force-inlined | Compile-time measurement |
| 2026-11-18 | Scalar FMA on MSVC through `_mm_fmadd_sd` | `std::fma` is a library call under `/fp:strict` and `/Od` |
| 2026-11-18 | Directed sums on $T$ use `Fast2Sum` on operands ordered by magnitude, not `TwoSum` | `TwoSum` can return a NaN error term at $\lvert a\rvert = \Omega$ with a finite sum, which would turn into a wrong-side bound (found by the independent review) |
| 2026-11-18 | MSL functions start with `#pragma METAL fp math_mode(safe)` and `fp contract(off)` and use `precise::` functions | Metal probe |
| 2026-11-18 | Generator in Python, standard library only | Small, auditable, shared with the documentation tooling |
| 2026-11-18 | Phase 0 experiments are kept, with their recorded outputs, under `experiments/phase0/` | Every number in this report can be rerun |
| 2026-11-19 | The repository is public, with its history; CI runs on hosted runners in four workflows (build and test, proofs, generated files and documentation, the generator's full suite) | The owner's instruction; CI was set up |
| 2026-11-19 | The oracle is written in Python, standard library only, with exact integers and fractions | Deviation 13 above |
| 2026-11-19 | `add_fast_2_2` is claimed with $3u^2(\lvert x\rvert + \lvert y\rvert)$, a bound relative to the operands, and ends with `Fast2Sum` | What is proved; no bound relative to $\lvert x + y\rvert$ exists for this algorithm when the operands have opposite signs |
| 2026-11-19 | The directed steps `radd` and `rmul` are claimed for nonnegative operands only, with an excess of at most $\tfrac32$ gaps | Every use in the `Ball` kernels has nonnegative operands; for operands of any sign the excess reaches 2 gaps, and the first target ("at most 2 gaps, any sign") was dropped as unused. A narrowing of a target, flagged in the Milestone 1 report |
| 2026-11-19 | The one-limb sum and product are kernels (`add_1_1`, `mul_1_1`) with theorems of their own | The one-limb `Ball` then takes its constants from a proved bound, like the two-limb one |
| 2026-11-19 | Every proved statement records the smallest precision it is proved for (1 to 4 in Milestone 1) | Proofs are for every precision from that minimum, and tests on toy formats must not run below it |
| 2026-11-19 | Overflow and non-finite operands are handled by *full kernels*: a finite core followed by a fix-up; a NaN radius is the empty ball, an infinite radius or a non-finite center the whole line | [Milestone 1 statements](../milestone1.md#ieee-like-results); D5 |
| 2026-11-19 | Rule R3: a `T` value that enters from the program is guarded by an addition of zero before a kernel adds or subtracts it; one-limb arithmetic stays unguarded and behaves like `T` | Deviation 1b above; cost: one addition per incoming value |
| 2026-11-19 | The quick tier runs every kernel through the interpreter and through scalar and packed runners; the generator's own C++ tests run in a separate workflow | The quick tier must stay within a few minutes |
| 2026-11-19 | A full kernel is named `K_full`; canonical values are a finite normalized pair, $(\pm\infty, 0)$ or all NaN; a ball is finite, the whole line (center 0, radius $+\infty$) or empty (all NaN); a NaN or negative radius given to a constructor is the empty set, a non-finite center the whole line | [Milestone 1 statements](../milestone1.md#ieee-like-results); a negative radius describes no ball, and a center that is not a number says nothing about where the set is |
| 2026-11-19 | The fix-up multiplies by $+\infty$ with a plain multiplication (`times_inf`), the one exception to "no plain multiplication" | The product is exact, its result is only compared or selected, and a fused operation there kept the full kernels out of constant evaluation |
| 2026-11-19 | The radius of a ball is computed with operations rounded to nearest and inflated once at the end (constants $E$, $G$, $H$), not by steps to the next number | Benchmarks: the radius of the first design cost 13 to 20 times the center's multiplication in packed code; containment is unchanged and proved |
| 2026-11-19 | Comparisons are emitted as `b > a` and `b >= a` | One compiler's constant evaluator returns true for `<` and `<=` with a NaN operand |
| 2026-11-19 | The claims gain the extended domain (`canonical`, `ball`, `extends`, `finite_when`, `represents`, `makes_ball`, `ieee_status`, `ieee_only`); the generator prints the IEEE model and its statements; the only hand-written parts of the formal model are the meaning of each operation in Flocq's terms and the vocabulary of the statements | So that the proofs about overflow and non-finite values are about generated code, as the real-model ones are |
| 2026-11-19 | Work that changes the generator, the oracle, the proofs and the headers together is combined on an integration branch and reaches `main` only when every check passes there | `main` is public and its CI runs on every push |
| 2026-11-19 | The public operators call the full kernels; `kairn::finite::` calls the cores; constructors are the generated constructor kernels; the headers contain no arithmetic of their own on two limbs except the steps of `ldexp` | Decision D5; deviation 17 above for `ldexp` |
| 2026-11-19 | An operation on a two-limb and a one-limb number calls the kernel of that mixed form (`add_2_1`, `sub_2_1`, `sub_1_2`, `mul_2_1`) instead of widening the one-limb operand | Its bound is tighter and it costs less; the value computed is still an approximation of the same exact result ([Operations](operations.md)) |
| 2026-11-19 | Operators are function templates in which no operand converts, and each is gated on the kernel it calls | An operation must not compile through a conversion to a kernel other than its own, or an unproved kernel could be reached without the marker |
| 2026-11-19 | Scalar code puts the fix-up of the full kernels and of the constructors of balls behind a branch, by a rule of the printer on the listing: inline, except with Clang on AArch64, where it is a cold function of its own; packed code keeps the selects | As selects, the fix-up made a chain of dependent operations take up to 1.91 times as long as the core (Apple clang) and 1.77 times (MSVC); behind the branch, 0.95 to 1.04 times ([Milestone 1 statements](../milestone1.md#ieee-like-results), "Emission") |
| 2026-11-19 | A `Ball` reports its state with `is_finite()`, `is_whole()` and `is_empty()`, and `Ball::whole()` and `Ball::empty()` make the two special states; a point operand of a Ball operation is the ball of radius 0 that the constructor makes | The three states of the design need names in the interface |
| 2026-11-19 | The constant $H$ of every Ball core contains the smallest normal number of the format, $N = \eta/(2u)$ ($2^{-1022}$ for `double`): $H$ is its expression plus $N$, rounded up, so that $H$ and every radius a core returns are normal numbers. $E$, $G$ and every statement are unchanged, and so are the precisions they are proved from | A fused multiply-add with a subnormal operand takes a microcode assist on Intel processors. Measured on an Intel Core i5-13500T with MSVC: 27 ns for that operation against 1.4 ns, and 31.8 and 35.0 ns for a step of a chain of `ball_add_2` and of `ball_mul_2`, against 5.2 and 7.0 ns with the normal $H$; no difference on an Apple M3 Max or an AMD EPYC 7452. Radii grow by about $2^{-1022}$ ([Milestone 1 statements](../milestone1.md#the-radius-second-design)) |
| 2026-11-19 | The tests are in two tiers: a quick tier, which is what `ctest` runs after the three commands of Getting started, and a full tier under `tests/full` of the build directory; both run on every push and pull request, in separate jobs. Every runner of a kernel completes the same generated cases, and identical outputs are judged once | The brief asks for a quick tier under two minutes per platform; with the kernels of the non-finite layer the single tier took 3.5 minutes on a workstation and 17 to 34 minutes on the hosted runners. The quick tier takes 48 s to 113 s on the three test machines |
| 2026-11-19 | With GCC and Clang the runners of a contraction setting are built at `-O2` whatever the build's level | Apple clang 21 fuses the textbook product of the Phase 0 experiment at `-O2` and leaves it alone at `-O3`, the level of a `Release` build, so the runners could not have caught the fault they exist for |
| 2026-11-19 | Linux on AArch64 is tested in CI on the hosted arm64 runners, with GCC and with Clang, in all three tiers, not under QEMU | The brief asks for Linux AArch64 under QEMU on a hosted runner; native runners exist and are faster. The first run found one test whose expectation held for Apple clang only: with Clang 18, `-fno-signed-zeros` with `-ffp-contract=fast` breaks no kernel |
| 2026-11-19 | Statement B4, "finite operands under the kernel's condition give a finite ball", is claimed and proved for the eight full Ball kernels. Each condition is one bound on the largest magnitude of a member of the exact result: at most a quarter of the overflow threshold for the sums, the differences, the scalings and the product of two-limb balls, and a sixteenth for the product of one-limb balls. The language of conditions (`abs_le`, with one exponent for every format) is unchanged, and so is every minimum precision | Without B4 a program could not rely on a finite ball ever coming out, since the whole line satisfies containment. The fractions are what holds from each kernel's minimum precision: in the smallest format of two bits the constants of the radius are large ($G = 4$ for the one-limb product) and the whole line appears at 0.34 of the threshold for the one-limb sums, 0.375 for the scalings and 0.094 for the one-limb product; in a format of four bits, at 0.55 to 0.81 for every kernel ([Milestone 1 statements](../milestone1.md#when-the-result-is-a-finite-ball)) |
| 2026-11-19 | In the brute-force tier, the enumeration of `ball_mul_1` at precision 1 does not fail on a result the oracle shows as suspicious; `tests/brute/widen.py` is the exact check in its place. The one-limb sums and the product have exponent ranges of their own at precision 1 (`fp:1:-5:5`, `fp:1:-6:5`) | At precision 1, $u = 1/2$ and the factor of the radius of a product, $\mathrm{up}((1+u)^5)$, is 8. The oracle calls a non-finite result suspicious when the operands and the exact set are within a quarter of the largest number, which supposes a factor of at most 4: with 8, a radius beyond the largest number is an overflow and no sign of a fault, in any exponent range. `widen.py` repeats every case in a wider exponent range and requires the result to be infinite exactly when the wide one exceeds the largest number; it held for every case of the four one-limb Ball kernels at precision 1. No claim and no theorem is involved: the claims of these kernels say nothing of a result that is not finite ([results](../../results/brute-milestone1.md#supplementary-run-precision-1)) |
| 2026-11-19 | The object-code check (`tests/objcode/`) requires, for every kernel, form of its C++ and limb type, as many fused multiply-adds as the FMA nodes of its IR, counted each or with identical nodes of one function merged, and as many plain multiplications as its products with infinity (`times_inf`), plus the products of the branch of constant evaluation where a compiler emits that branch; and no call outside the object but the stack protector's. The generator writes the numbers (`gen/objcode.json`) from the IR; the check runs on the whole flag matrix of each compiler in the full tier and on five configurations in the quick tier, with a control in which the textbook `a * b + c` must fail it exactly where it is fused | Measured on the whole matrix of GCC 13 and 16, Clang 18, Apple clang 21 and MSVC 19.52, on x86-64 and AArch64. Equality with the FMA nodes fails only where a fix-up recomputes the core's leading product (`mul_2_1_full`, `mul_2_2_full`, `mul_pow2_2_full`), which an optimizing compiler merges with it (MSVC under `/fp:strict` in packed code only), and "no plain multiplication" fails only for `times_inf`, which R1 allows, and with MSVC at `/Od`, which compiles `two_prod`'s never-taken branch of `__builtin_is_constant_evaluated()`. Neither is a contraction, and each allowed number is one the generator gives, so the check still fails on one fused instruction or one multiplication more ([Testing](../../testing.md#object-code)) |
| 2026-11-19 | The tests gain an adversarial search (`kairn-oracle search`), a shrinker (`kairn-oracle shrink`) and a file of regression cases (`tests/regression/cases.txt`). The regression cases run in the quick tier through every runner it builds and every public form of their kernels; the search runs by hand and in the full tier, with 5 000 cases per kernel and format through the scalar runner. A failure is shrunk, added to the file with where it was found and its class (statement, generator, code, compiler or hardware), and stays there | The brief's "Adversarial search" and "Failures", which Milestone 1 had not built. With 20 000 cases per kernel and format, the search came closer to the claim than the 13.8 billion results of the brute-force runs on 86 of 116 quantities and farther on none; it attained the bounds of the accurate sum, of the sums with one limb and of the fast sum to within $10^{-6}$, and that of the double-word product to within $10^{-8}$; no claim was violated ([Testing](../../testing.md#the-adversarial-search)) |
