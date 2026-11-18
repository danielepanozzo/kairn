# Verification: proof assistant, proof plan, generator, trusted base

## Proof assistant: Rocq with Flocq

**Recommendation: Rocq 9 with Flocq 4.2** ([D1](decisions.md#d1-proof-assistant)).

| Criterion | Rocq + Flocq | Lean 4 | Isabelle/HOL |
|---|---|---|---|
| Floating-point theory | Mature and generic in radix, precision and minimum exponent: formats with and without gradual underflow, `ulp`/`succ`/`pred`, rounding to nearest with a parametric tie rule, relative-error theorems with the underflow term | Three libraries, all started in 2025–26, none in Mathlib (whose own file is being removed), none with a track record | A bit-level IEEE model; no generic-format or `ulp` theory found |
| Error-free transformations | `TwoSum`, `Fast2Sum`, Veltkamp, Dekker with its underflow bound, representability of the product error, all with gradual underflow | Claimed in one new repository | None found |
| Double-word proofs to reuse | [MR22](references.md#mr22) (all of JMP17), [LLMPR23](references.md#llmpr23) (square root), both MIT; [ExpFloat](references.md#expfloat) (MIT, active) | None | None |
| Automation for error bounds | Gappa (aware of error-free transformations since 2026), CoqInterval, `lra`/`nra`/`lia` | A two-month-old tactic; `polyrith` is gone | An oracle-based `approximation` method |
| Parametric in $p$, minimum exponent, underflow model | Yes for the first two; the flush model has to be written (below) | Depends on the library; no flush model seen | Sizes are types |
| Axiom audit in CI | `Print Assumptions` per theorem; scripted allow-list | Best tooling (`axiom-audit`) | No per-theorem axiom report found |
| Risk | A small group at Inria maintains Flocq, Gappa and CoqInterval; all three had releases in 2026 and Flocq is in Rocq's own CI | Monthly toolchain churn; young libraries | Everything floating-point would be ours to build |

The comparison comes from a literature and repository survey ([research notes](references.md#proof-assistants)),
not from trying all three. What was tried is the recommended one.

### What Phase 0 ran

[`experiments/phase0/tracer/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/tracer)
is the whole pipeline in miniature, on Rocq 9.0.1 and Flocq 4.2.2 in the `rocq/rocq-prover:9.0`
container image (Flocq installs from opam in minutes):

1. `gen.py` holds three kernels (`TwoSum`, `Fast2Sum`, `TwoProd`) as straight-line operation
   lists and writes **both** `Model.v` (Rocq functions over Flocq's rounding operator, parametric
   in precision, minimum exponent and tie rule) **and** `kernels.hpp` (C++).
2. `Proofs.v`, written by hand, proves four theorems about the generated model: `TwoSum` and
   `Fast2Sum` are error-free with gradual underflow, `Fast2Sum`'s output is normalized, and
   `TwoProd` (as emitted, with the opaque product) is error-free above $2^{2p-1}\eta$. The last
   one is not in Flocq as such; it took ten lines from Flocq's `mult_error_FLT`.
3. `Audit.v` prints the assumptions of each theorem and `audit.py` compares them with an
   allow-list. **Result: exactly four axioms**, all from Rocq's standard library of classical
   real numbers; Flocq adds none:
   `ClassicalDedekindReals.sig_forall_dec`, `ClassicalDedekindReals.sig_not_dec`,
   `FunctionalExtensionality.functional_extensionality_dep`, `Classical_Prop.classic`.
4. A negative control, a false theorem closed with `Admitted`, is rejected by the audit (an
   admitted theorem shows up as an axiom named after itself).
5. The generated C++ is run on 60 000 operand pairs, a third of them in the subnormal range, and
   checked against exact rational arithmetic by a script that shares no code with the generator:
   no violation.

The whole run takes 7 seconds.

### Axiom policy for CI

- The allow-list is the four axioms above. Proofs over the real numbers in Rocq cannot be
  axiom-free, so this list is the floor, and it is what Flocq, CompCert's floating-point proofs
  and every double-word formalization rest on. **[D1](decisions.md#d1-proof-assistant) asks you to
  approve the list.**
- CI prints the assumptions of every exported theorem (the list of theorems comes from the
  generator's metadata, so a kernel without a theorem is itself an error) and fails on anything
  outside the list. `Admitted`, `Axiom`, `Parameter` and `admit` are also rejected by a plain
  text search, so that the failure is early and readable.
- The printed assumptions are kept as a CI artifact and shown on each operation's reference page.

## Underflow models

Flocq's `FLT` format is gradual underflow, and it is what the tracer used. For Metal the proofs
need flush-to-zero, and here the survey found a trap: **Flocq's `FTZ` format is not a usable
model.** It flushes before rounding, which matches what the M3 GPU was observed to do, but it has
no monotonicity instance, so Flocq's own theorems about addition errors, Sterbenz's lemma and the
error-free transformations do not apply to it; and one fixed convention is the wrong tool when the
Metal specification leaves the convention open.

The plan is therefore to make the proofs parametric in an **underflow budget** rather than in a
format:

- The kernel model is written against a small interface: each primitive operation returns a
  value related to its exact result by a specification (for model G, equality with
  $\mathrm{RN}$; for model Z, the nondeterministic relation of [Numbers](numbers.md#notation)).
- The building blocks are proved once per model in the form "exact up to a slack":
  `TwoSum` returns $s, e$ with $|s + e - (a + b)| \le \tau_{+}$, `TwoProd` with slack
  $\tau_{\times}$, where $\tau_{+} = 0$ and $\tau_{\times} = \eta/2$ in model G, and both are small
  multiples of $\lambda$ in model Z.
- Kernel theorems are proved once, carrying the slacks symbolically; instantiating them gives the
  `float`, `double` and Metal statements. This is how "one proof covers float, double and Metal"
  is met.

This design has not been tried yet. It is the first thing Milestone 1 does for $k = 2$ in model
G, and its extension to model Z is scheduled with the Metal backend.

## Proof plan per k

| k | Starting point | Work | Risk |
|---|---|---|---|
| 1 | Flocq has every statement | Package them in Kairn's form | none |
| 2 | [MR22](references.md#mr22): 19 000 lines, MIT, Rocq 8.12 era, **no underflow**, `TwoProd` exactness assumed as a hypothesis, normalization of the result stated for 3 of 15 algorithms. [LLMPR23](references.md#llmpr23) for the square root | Port to current Rocq and Flocq; restate with gradual underflow and the slack interface; discharge the `TwoProd` hypothesis (done in the tracer); add the missing normalization and no-overflow statements; cover the contraction variants | Moderate: known mathematics, real volume. First deliverable of Milestone 1 is the addition and the product |
| 3, 4 | Networks of [ZA-SC25](references.md#za-sc25) (MIT), verified only by SMT on an abstraction | See below | **High** |
| 8, runtime k | Nothing | New algorithm and an induction proof ([Operations](operations.md#eight-limbs-and-runtime-k)) | **High**, research |
| Enclosures | — | Containment follows from the kernel theorems and three lemmas about `next_up`; mostly bookkeeping | low |
| Batch kernels | Higham-style inductions | Induction on $n$ for each emitted reduction order | moderate |
| Decimal I/O | CompCert's `Bparse` (nearest only) | Integer-arithmetic proofs of digit generation with directed rounding | moderate |
| Elementary functions | CoqInterval, Gappa, [ExpFloat](references.md#expfloat) as a model | One proof per $(f, T, k)$ | high volume |

### Networks for three and four limbs

Three routes, none proven to work at this size, in the order they will be tried:

1. **Abstract interpretation checked inside Rocq.** Reimplement the abstraction of
   [ZA25](references.md#za25) (sign, exponent, leading and trailing bit counts) as Rocq
   definitions, prove its roughly 70 `TwoSum` lemmas once for all $p$ (the original checks them by
   bit-blasting at five precisions), and discharge each network's linear-integer obligations with
   `lia` or with solver certificates replayed in Rocq. Gives a fully kernel-checked,
   $p$-parametric proof, and powers of two as constants.
2. **Gappa per format.** Gappa learned to reason about error-free transformations in 2026 and has
   reproduced a triple-word product bound ([HM26](references.md#hm26), slides only). It works at a
   concrete precision, so this yields separate proofs for $p = 24$ and $p = 53$ rather than one
   parametric proof, and it does not prove normalization of the output.
3. **Manual proofs** in the style of MR22, for $k = 3$ first.

Two policy questions follow, and they are yours ([D2](decisions.md#d2-what-counts-as-machine-checked)):
whether an SMT solver's unchecked `unsat` may ever count as "machine-checked" (recommended: no),
and whether per-format proofs are an acceptable fallback where a $p$-parametric one is not
achieved (recommended: yes, flagged per operation, since `float` and `double` are the only limb
types).

Until one route succeeds, the 3- and 4-limb operations carry `UNVERIFIED`. The brute-force and
exhaustive test tiers apply to them from the first day, but their measured maxima are never
published as bounds.

## Generator

The generator is the single source of truth and part of the trusted base, so it is kept small:
**Python, standard library only, no templating engine** (the documentation tooling is Python
too, and reads the same metadata). The Phase 0 tracer's `gen.py` is 80 lines; the real one is
budgeted at 1 500 to 2 000, of which the two printers that matter for trust are a few hundred.

### The IR

A kernel is a straight-line program in static single assignment form over two value types, limbs
and masks:

| Operation | Meaning | Notes |
|---|---|---|
| `add`, `sub`, `neg`, `abs` | $\mathrm{RN}(a \pm b)$, exact sign changes | |
| `fma`, `fms`, `fnma` | $\mathrm{RN}(\pm ab \pm c)$ | always a fused instruction |
| `prod` | $\mathrm{RN}(ab)$, emitted as `fma(a, b, 0)` | the opaque product |
| `muladd` | $\mathrm{RN}(ab + c)$ **or** $\mathrm{RN}(\mathrm{RN}(ab) + c)$ | the declared contractable form; the theorem covers both |
| `div`, `sqrt` | correctly rounded | only in division and square-root kernels |
| `lt`, `le`, `eq` → mask; `select(mask, a, b)` | comparisons and branch-free choice | the only "control flow" |
| `succ`, `pred` | neighbors in the format | for directed rounding |
| calls to other kernels | inlined by the generator | `TwoSum` is a kernel |

Each kernel also carries metadata: name, $k$, operands and results, preconditions, the name and
file of its theorem, its constants $c$ and $t$ as exact rationals, operation count and depth, the
citation of the algorithm's source and its license, and its verification status.

**Checks the generator performs on every kernel**, each a few lines of graph traversal:

- single assignment and use-after-definition;
- **R1/R2** of [Environment](environment.md#the-rule-no-product-feeds-an-addition): no
  multiplication result reaches an addition, and no output is a bare product;
- **the non-finite cone**: every value reaches output limb 0 through operations that keep a
  non-finite value non-finite ([Numbers](numbers.md#non-finite-values));
- every kernel names a theorem, and every `UNVERIFIED` kernel is listed as such in the output.

### What it emits

| Output | Form |
|---|---|
| Formal model | One Rocq definition per kernel over the operation interface, plus the theorem *statement* (the proof is written by hand in a separate file and must match it) and the audit file |
| Scalar C++ | One **non-template** function per limb type, one operation per statement; `constexpr`, with the constant-evaluation variant (Dekker product, unfused `muladd`) selected by `__builtin_is_constant_evaluated()` |
| AVX2, AVX-512, NEON | Raw intrinsics, one number per lane; AVX-512 functions carry a `target` attribute |
| CUDA | `__host__ __device__` functions using `__dadd_rn`, `__fmul_rn`, `__fma_rn`, … on the device |
| MSL | Functions that start with the two scoped pragmas, using `fma` and `precise::` functions |
| Data | The `constexpr` error-model tables behind `kairn::traits`, the reference pages' metadata, the list of theorems for the audit, the per-kernel fused-instruction counts for the object-code check |

Two emission rules come straight from Phase 0 measurements: one statement per operation (so that
Clang's default per-expression contraction has nothing to fuse), and non-template functions (MSVC
needs more than 24 CPU-minutes to parse an 8-limb-sized network written as a function template,
and 0.1 s for the same network as a plain function).

## Trusted base

A Kairn bound is as trustworthy as the following, and no more:

1. The Rocq kernel and the four axioms.
2. The **statements** of the theorems (a proved theorem can still say the wrong thing); the
   plain-math versions on the website are mapped one to one to the formal statements so that they
   can be read against each other.
3. The generator: that the Rocq model and the C++/intrinsics/CUDA/MSL text it prints from one IR
   describe the same computation. No comparable project proves its printers either; for this
   reason the printers are tiny and the tests exist.
4. The compilers: that each emitted operation is executed with IEEE semantics, which R1/R2, the
   flag checks and the self-test defend ([Environment](environment.md)).
5. The hardware and the dynamic environment.

Testing is aimed at items 2 to 5, which no proof covers: an oracle that shares no code with the
library, on every backend ([Plan](plan.md#testing)).
