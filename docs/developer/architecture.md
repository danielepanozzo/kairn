# Architecture

How the repository is organized, what each part may depend on, and the interfaces between the
parts. The reasons behind these choices are in the [Phase 0 report](design/phase0/index.md); this
page states the rules that the code follows.

## The pipeline

Every arithmetic kernel exists once, as a description in the generator. Everything else is
derived from it or checked against it:

```
                       gen/kernels  (one description per kernel)
                              |
        +----------+----------+-----------+-------------+
        |          |          |           |             |
   proofs/gen  include/kairn/gen     gen/claims.json   toy-format
   (Rocq model,   (C++, later SIMD,   (what each       interpreter
    statements,    CUDA, MSL)          kernel claims)   (a runner)
    audit)             |                   |             |
        |              +---- runners ------+-------------+
   proofs/theories          (programs that compute)      |
   (hand-written proofs)             |                   |
                                   oracle/  (exact arithmetic; checks every
                                   result against the claims)
```

- A **proof** is about the generated Rocq model and establishes the generated statement.
- A **runner** is any program that evaluates kernels: the library on some backend, or the
  generator's interpreter on a toy format.
- The **oracle** decides, in exact arithmetic, whether a runner's results satisfy the claims.

## Layout and ownership

| Path | Content | May depend on |
|---|---|---|
| `gen/` | The generator: Python, standard library only. `gen/kernels/` holds the kernel descriptions. | nothing else in the repository |
| `gen/claims.json` | Generated and committed: what every kernel claims. | — |
| `gen/constant_names.json` | Committed, and only added to by `build`: the name of each constant `up(EXPR)` of the Rocq models, which hand-written proofs use and which a new kernel must not change (`gen/README.md`, "The operations"). | — |
| `gen/objcode.json` | Generated and committed: the fused multiply-adds and plain multiplications that each kernel's code asks for, for the object-code check. | — |
| `include/kairn/gen/` | Generated and committed C++ kernels. | — |
| `tests/emulated/gen/` | Generated and committed: the scalar kernels for the emulated limb type of the tests ([below](#the-kernel-ir), "A limb type of a format chosen at run time"), a test file that is not shipped. | — |
| `include/kairn/` | The hand-written public headers. | `include/kairn/gen/` |
| `proofs/gen/` | Generated Rocq files: model, statements, audit. | Flocq |
| `proofs/theories/` | Hand-written Rocq proofs and the lemma library. | `proofs/gen/`, Flocq |
| `oracle/` | The oracle: Python, standard library only. | `gen/claims.json` as data, and nothing else: **no code shared with `gen/` or the library** |
| `tests/` | Runners for the library, the quick corpus, CMake/ctest wiring. | library, oracle |
| `bench/` | Benchmarks. | library |
| `results/` | Stored summaries of brute-force runs and benchmarks, by milestone. | — |
| `docs/` | The MkDocs site; this page; the Phase 0 report. | — |
| `experiments/phase0/` | Phase 0 experiments, kept as recorded. | — |

Entry points, so that CMake, CI and people call the same thing:

| Command | Does |
|---|---|
| `python3 gen/kairn-gen build` | Regenerates every generated file. |
| `python3 gen/kairn-gen check` | Fails if a committed generated file differs from what `build` would write. |
| `python3 gen/kairn-gen test` | The generator's own tests. |
| `python3 gen/kairn-gen interp ...` | The toy-format interpreter, as a runner (below). |
| `python3 oracle/kairn-oracle gen ...` | Writes request lines (below). |
| `python3 oracle/kairn-oracle check ...` | Reads completed lines, prints a verdict and statistics, exits non-zero on any violation. |
| `python3 oracle/kairn-oracle selftest` | The oracle's own tests, including injected errors that it must catch. |
| `python3 tests/objcode/objcode.py --cxx CXX --workdir DIR` | The object-code check with one compiler (`--tier full` for its whole flag matrix, `--controls` for its negative controls). |
| `make -C proofs` | Builds all proofs and runs the axiom audit. |

Building the library as a client never needs Python or Rocq. Running Kairn's own tests needs
Python 3; checking the proofs needs Rocq 9 and Flocq 4.2.

## Number formats

A binary format is three integers $(p, q_{\min}, q_{\max})$: its numbers are $m \cdot 2^q$ with
integers $|m| < 2^p$ and $q_{\min} \le q \le q_{\max}$. So $u = 2^{-p}$, $\eta = 2^{q_{\min}}$ and
$\Omega = (2^p - 1)\,2^{q_{\max}}$. Rounding is to nearest, ties to even, with gradual underflow;
a result whose rounding in unbounded range exceeds $\Omega$ is $\pm\infty$.

| Name | $(p, q_{\min}, q_{\max})$ |
|---|---|
| `binary64` | $(53, -1074, 971)$ |
| `binary32` | $(24, -149, 104)$ |
| `fp:P:QMIN:QMAX` | any other, for example `fp:5:-12:6` (a toy format) |

Toy formats exist so that statements can be tested on *all* operands before anyone tries to prove
them. Every number of a toy format with $p \le 53$ inside `binary64`'s range is a `double`, so the
same tools and the same line protocol handle them.

**The formats of the statements** (the ruling of 2026-11-21). The generated statements of
the IEEE model quantify over the formats of Flocq's `binary_float prec emax`: $e_{\max} > p$, and
the smallest exponent $3 - e_{\max} - p$; with $q_{\max} = e_{\max} - p$ that is $q_{\max} \ge 1$
and $q_{\min} = 3 - q_{\max} - 2p$ (`binary64` and `binary32` are of that shape, and so is
`fp:8:-14:1`, precision 8 with $e_{\max} = 9$). A clause that promises a finite result (V4 of a
ball vector or of a product of two BallVectors with its `finite_when`, `radii_when` and
`count_when`; the `finite_when` of `extends`, `encloses` and `ball_of_interval`; the
`bounded_when` of the interval kernels) is claimed in those formats. So are the midpoint of a
bounded interval of `ball_of_interval` with `ieee1788`, a finite canonical number, and what
`splits` claims of the parts that rest on it (each a canonical interval, the two meeting at a point
of the interval), by a second ruling of the same day: what is proved is that the sum of the two
halves of two limbs cannot overflow where $e_{\max} > p \ge 3$, and below that it can, and the
midpoint is a NaN. A reader may also judge it in
a format of a wider subnormal range ($q_{\max} \ge 1$ and $q_{\min} < 3 - q_{\max} - 2p$), where
nothing is proved and a failure is a finding to report, not a violated claim; in any other toy
format it is not claimed, and a reader counts that it was not judged. In `fp:2:-1:0`
($e_{\max} = 1 < p$), for example, a constant of the radius of `bv_add_1` is the largest number of
the format, and V4 is false as written there.

## The kernel IR

A kernel is a straight-line program in static single assignment form. Values are limbs (numbers
of the format) or masks.

| Operation | Meaning | Emitted in C++ as |
|---|---|---|
| `add a b`, `sub a b` | $\mathrm{RN}(a \pm b)$ | `a + b`, `a - b` |
| `neg a`, `abs a` | exact | `-a`, a sign-bit operation |
| `fma a b c`, `fms a b c`, `fnma a b c` | $\mathrm{RN}(ab + c)$, $\mathrm{RN}(ab - c)$, $\mathrm{RN}(-ab + c)$: one rounding | always a fused operation |
| `prod a b` | $\mathrm{RN}(ab)$ | `fma(a, b, +0.0)`: the *opaque product*; in constant evaluation `a * b` (below) |
| `muladd a b c` | $\mathrm{RN}(ab + c)$ **or** $\mathrm{RN}(\mathrm{RN}(ab) + c)$, the compiler's choice | `a * b + c`; its theorem covers both |
| `lt`, `le`, `eq` | comparison, giving a mask | comparison; `lt(a, b)` and `le(a, b)` are written `b > a` and `b >= a`, which one compiler's constant evaluator gets right on a NaN where it gets `<` and `<=` wrong |
| `and`, `or`, `not` | on masks | |
| `select m a b` | $a$ if $m$, else $b$ | `m ? a : b`, or a blend; behind a branch only where the scalar printer puts a fix-up (below) |
| `succ a`, `pred a` | the neighbors of $a$ in the format | |
| `guard a` | $\mathrm{RN}(a + 0)$, which is $a$ (a zero comes out positive) | `a + 0.0`: see rule R3. In constant evaluation, where nothing is fused, the operand itself |
| `const name` | a constant that depends on the format (for example the splitter $2^{\lceil p/2\rceil} + 1$) | a literal |
| `0`, `const inf`, `const nan` | the literal zero, $+\infty$ and a quiet NaN (used by the non-finite layer only) | a literal; `std::numeric_limits` |
| `const up(EXPR)` | the smallest number of the format not below `EXPR`, an exact expression over $u$, $\eta$, integers and the constants `unit(K)`, `tiny(K)` of a proved kernel's bound | an exact literal per type |
| `times_inf a` | $a \times \infty$: a NaN for a NaN or a zero, otherwise the infinity with the sign of $a$ | a plain multiplication by infinity; its result may only be compared or selected |
| `call K args` | another kernel | inlined in C++, kept as a call in Rocq |

Rules the generator enforces on every kernel, and refuses to generate otherwise:

1. Single assignment; every use after its definition; no unused value.
2. **R1.** The result of `prod` is the only product-like value that may be an operand of `add`,
   `sub`, or the addend of an FMA. There is no plain multiplication in the run-time IR, except
   `times_inf`, which is exact and whose result is only compared or selected. The object-code
   check (`tests/objcode/`, [Testing](testing.md#object-code)) verifies the consequence in the
   compiled code of every kernel, on the flag matrix of each compiler: one fused multiply-add per
   FMA node (identical nodes of one function may be merged into one), and no plain multiplication
   but one per `times_inf` and, where a compiler emits the branch that only constant evaluation
   takes, the products of that branch. An addition of a value to itself, `add(a, a)`, is refused
   too, on the listing with its calls inlined and through copies: GCC 13 writes `a + a` as
   `a * 2` and, under `-ffp-contract=fast`, contracts that product into the addition that follows
   (the object-code check found it in the first listings of `bound_sum_2` and `bound_dot_2`, at
   `-O2` and `-O3` on x86-64). A doubling is written `prod(a, const up(2))`, exact and opaque.
3. **R2.** No kernel output is an expression the compiler could fuse into the caller: outputs are
   results of `add`, `sub`, `fma`-family, `prod`, `select`, `neg`, `abs`, `succ`, `pred`, never of
   `muladd`.
4. **The non-finite cone.** Every limb value reaches output limb 0 through operations that map a
   non-finite operand to a non-finite result, unless the value is itself computed from output
   limb 0 (the error term of a `two_sum`, the tail of a final `fast_two_sum`). For those values
   finiteness is not a matter of data flow: it is part of the kernel's proof, or a condition of
   its statement. A kernel that cannot satisfy the rule declares it and must come with an
   explicit finiteness test.
5. Every kernel names its theorem, its source and that source's license, or is marked
   `unverified`.
6. **R3. Values that enter from the program.** A kernel that the public headers may call with
   a value supplied by the program is marked `entry` (the self-test calls building blocks on
   constants of its own; that does not make them entry kernels). In an entry kernel, a one-limb input is a value of `T` supplied by the program
   (a scalar operand, a limb or a radius given to a constructor) unless the kernel declares it
   `stored`: a limb of an object, such as the radius of a ball. An input supplied by the program,
   and anything obtained from it by `neg`, `abs` or `select` alone, is never an operand of `add`
   or `sub` nor the addend of an FMA: it passes through `guard` first. It may be a factor of
   `prod` or of an FMA and an operand of a comparison as it is, and it is never an output as it
   is. The reason: the program may have
   written
   `x + a * b`, and a compiler that contracts across statements then fuses the program's own
   multiplication into the kernel's first addition, so that the kernel no longer computes with a
   number of the format. After `guard` nothing is left to fuse: the only thing a compiler can
   fuse is a multiplication feeding an addition, and `(a * b) + 0` fused is the rounded product
   itself. The limbs of a multi-limb operand and the `stored` inputs need no guard: they are
   outputs of kernels (R2) or were guarded when the object was constructed, by the constructor
   kernels of [Milestone 1 statements](design/milestone1.md#values-that-enter-from-the-program).
   One-limb arithmetic (`Expansion<T, 1>`) is outside this rule by decision
   [D6](design/phase0/decisions.md#d6-one-limb-and-contraction-under-clang): it behaves like `T`,
   contraction included.

   **The factors of a fused operation.** "Nothing can be fused into a product" holds of the product
   alone. It does not hold of a fused operation whose *other* factor the compiler sees to be 1 or -1
   after inlining: LLVM rewrites `fma(x, 1, s)` as `x + s` (and `fma(x, -1, s)` as `s - x`), and a
   product `x = a * b` that the program computed is then fused into that addition, so that the
   kernel computes with the exact product. The sound criterion: a value supplied by the program (an
   input of an entry kernel that is not `stored`, the limbs of a `supplied` input, the elements of a
   supplied array and a supplied scalar of a loop), reached directly or through a callee and through
   `neg`, `abs`, `select` and `copy` as for the rule above, is **exposed** where it is a factor of
   `fma`, `fms`, `fnma` or `muladd` whose addend is not the literal zero of the listing, on a path
   on which it has not passed through `guard`. A factor of `prod`, emitted `fma(a, b, +0.0)`, is not
   exposed: whatever a compiler does with the product `a * b` of the program inside it, fused it is
   $\mathrm{RN}(ab + 0)$, the rounding of the product itself, which is what the program's product is
   (and the same holds of a fused operation whose addend is the literal zero). A guarded value is a
   number of the format, the rounded product at most, and nothing is left to fuse.
   `rules.exposed_operands` lists, for every entry kernel and every loop, its exposed operands with
   the route to each, and `python3 gen/kairn-gen build` prints the list after its summary, with the
   operations of each object today and with a guard on each exposed operand, and the header
   functions that reach it (`build.header_calls`: the function of the public headers whose body
   calls the kernel or the loop, directly or through `KAIRN_DETAIL_BV_LOOP`, the macro with which
   `kairn/ball_vector.hpp` calls its loops). By the owner's decision of 2026-11-21 (the strict rule)
   an exposed operand is refused, with its operation and route (`rules.factor_rule`): an entry
   kernel guards each factor it takes from the program, and a kernel that other kernels also call on
   limbs that kernels wrote gets a guarded entry twin instead, whose listing is the unguarded one
   after a guard of each factor and whose proofs reduce to it (the guard is the identity on numbers
   of the format). The public operations call these entry forms: `two_prod_entry`
   (`kairn::two_prod`; in constant evaluation the variant `two_prod_dekker` on the operands as they
   are, since constant evaluation fuses nothing), `mul_down_entry` and `mul_up_entry` (`mul_down`,
   `mul_up`), `mul_2_1_entry` (`finite::mul(x, a)` of `Expansion<T, 2>` and of `Packed`),
   `mul_2_1_full_entry` (`x * a`, `a * x`, `x *= a` of both), `ball_scale_2_full_entry` (the scaling
   of a `Ball<T, 2>` by a `T`), `acc_mul_entry_1` and `acc_mul_entry_2`
   (`Accumulator::add_product`), and `dot_entry_step_1`, the step of `dot_1_entry` (`dot` of one
   limb) and of the coefficients of `conv_1_entry` (`conv` of one limb), and `scale_entry_step_2`,
   the step of `scale_2_entry` (`scale` of two limbs); `dot_1`, `conv_1` and `scale_2` are on stored
   arrays (`dot_1` and `conv_1` the loops of the centers of `bv_conv_1`). The kernels they guard for
   (`two_prod`, `mul_down_1`, `mul_up_1`, `mul_2_1`, `mul_2_1_full`, `ball_scale_2`,
   `ball_scale_2_full`, `acc_mul_1`, `acc_mul_2`, `dot_step_1`) are no longer entry kernels. The
   objects not closed yet are listed in `rules.FACTOR_PENDING`, each with its reason: the loops over
   arrays of two limbs (`dot`, `axpy`, `conv`) and the scaling of a ball vector, with their steps,
   into none of which a compiler was measured to fuse (Apple clang 21 under `-ffp-contract=fast` at
   `-O2` with `NDEBUG` fused a product of the program through a visible 1 into `conv` of one limb
   and `scale` of two limbs, every round, before they ran `conv_1_entry` and `scale_entry_step_2`).
   R3 accepts their exposed operands, and refuses an entry there that has none; `build` prints them
   as PENDING. The measurements are in [Testing](testing.md#the-functions-on-arrays), "A factor the
   compiler sees".

R3 was added in Milestone 1, after a test of the public headers found the failure it prevents:
with GCC 13 and 16 at their default setting, with Apple clang on AArch64 under
`-ffp-contract=fast` and with MSVC under `/fp:contract`, `x + a * b`, `x - a * b` and `a * b - x` for a 2-limb `x` differed from the same
operation on the rounded product in every one of 200 000 cases chosen to cancel; with the guard,
in none, on those compilers and on the settings that do not contract
(`tests/api/boundary.cpp`, with a control that builds the same test against a copy of the generated
kernels with the guard taken out, and fails if those compilers then fuse nothing). Clang 18 on
x86-64 under `-ffp-contract=fast` left those three forms alone. With the first headers it fused the
radius and the one-limb center given to a `Ball` instead; since the constructors are generated
kernels, it fuses nothing even without the guard (measured; no cause is claimed), and its control
only reports. The guard relies on what the opaque product
already relies on: the compiler honors the sign of zero, so it may not remove `a + 0`. The
generator emits every guard and checks the rule; the public headers contain none of their own.

One compiler does not fit that description. With the hand-written guard of the first headers,
MSVC 19.52 removed the addition of zero for some operands under `/O2`: a guarded $-0$ stayed $-0$
(values are unaffected, and the sign of a zero is unspecified). With the generated guard, a $-0$
given to a constructor, to `x + a` and to a `Ball` entered as $+0$ under `/O2`, `/Od`,
`/fp:contract` and `/fp:strict`, so the addition was kept in those cases. In every test so far
MSVC kept the program's product out of the kernel under `/fp:contract`, the one MSVC setting that
contracts, which is not its default: no case differs with the guard and all of them without it.
Since this compiler has been seen to remove such an addition, on MSVC the guard rests on those
tests, which run on every change, and not on a rule of the language.

A kernel may name a second kernel as its **constant-evaluation variant**. The emitted C++
function then dispatches on `__builtin_is_constant_evaluated()`. Inside such a variant, `prod` is
emitted as `a * b`, because there is no FMA in constant evaluation and no contraction either. The
variant has its own statement and proof.

**The rule of the product** ([Milestone 2 statements](design/milestone2.md#the-two-executions-of-a-product)).
A kernel whose only fused operations are `prod` is `constexpr` without a variant: each `prod` is
emitted as `__builtin_is_constant_evaluated() ? a * b : fma_rn(a, b, +0.0)`, the plain product in
constant evaluation and the opaque product at run time. As real numbers both are
$\mathrm{RN}(ab)$, so the real model is one definition for both (`rnd (a * b + 0)`) and every
real-model theorem holds of both. As values of `T` they differ in one case only: an exact zero
product of negative sign is $-0$ as `a * b` and $+0$ as `fma(a, b, +0)`. The IEEE model
(`proofs/theories/IeeeOperations.v`) defines `prod` as the FMA. Its statements hold of the plain
product too because they are about values, in which the two zeros are the same, except where a
fix-up returns its own literal zero, which no product reaches: F4 and F5 of `mul_pow2_2_full`
say that its second limb is the `+0` of the fix-up, a constant of the listing and the same in
both executions. What is proved (`proofs/theories/IeeeTwoExecutions.v`) is that every kernel of
the rule, and every kernel listed further down, gives outputs of the same value, and the same masks, in both executions, on all operands
(finite, infinite and NaN) and for every choice of NaN in each, with no hypothesis: each listing
is written there once more with the operations that constant evaluation computes otherwise as
parameters (`proofs/gen/IeeeWith.v`: the product, and the guard and `times_inf` where the kernel
has them), which with the operations of run time is the generated model by `reflexivity`, and
with those of constant evaluation (`prod_ce`, the plain product; `guard_ce`, the operand itself;
`times_inf_ce`, the comparisons of `prelude.hpp`) is the execution of constant evaluation; each
of the three gives the value of its form of run time on every operand. The theorem of each kernel
has the generated statement `K_two_executions_spec` as its type, which `proofs/gen/IeeeAudit.v`
checks, so that a kernel that comes to compute such an operation without its theorem fails the
proofs build (`IeeeProduct.v` compares the two products of `rmul` and `mul_1_1` bit by bit). What is tested
rather than proved is that the C++ compiled for constant evaluation is that listing: the generator
prints the C++, `IeeeModel.v` and `IeeeWith.v` from one listing, and its tests check that the two
executions give the same bits, or for the kernels whose outputs can be an exact zero product the
same values (`gen/tests/test_interp.py`, `TwoExecutionsOfAProduct`; `test_cxx.py` ties the C++ to
them). The kernels `constexpr` by this rule are thirty, which `build` lists: `rmul`, `mul_1_1`,
`split`, `two_prod_dekker`, `mul_pow2_2`, `mul_pow2_2_full`, `ball_mul_pow2_k` with its full form,
and the bound kernels of the folds, `bound_sum_k` and `bound_dot_k`; the steps of `axpy` and of
the scalings, `axpy_step_1`, `axpy_entry_step_1`, `mul_pow2_step_k`, `scale_step_1` and the three
of `bv_mul_pow2_k`; and of Milestone 2, `ball_from_interval_2`, `interval_mid_rad_1` and the two
kernels that call it, `interval_to_ball_1` and `interval_split_1`, which halve with `prod`, and of
stage B2, through `interval_to_ball_1`, `ball_hull_1`, `ball_intersection_1` and
`ball_from_interval_1`, and `interval_split_2`, whose midpoint halves the bounds with `mul_pow2_2`.
Thirty-three kernels that are `constexpr` without any product compute a `guard` or a `times_inf`,
and so compute it otherwise in constant evaluation too: the entry kernels and constructors that
guard their operands (among them the public constructors and the sums and differences of
`Expansion` that take a `T`), and the full sums and differences, whose fix-ups use `times_inf`.
They are in `IeeeWith.v` too, with the same theorem: 63 kernels in all, every kernel `constexpr`
without a variant whose C++ dispatches on constant evaluation, so that none computes otherwise
in constant evaluation without a proof that the values are the same. The two kernels that
dispatch and are not among them are `two_prod` and its entry form `two_prod_entry` (rule R3, the
factors of a fused operation), `constexpr` through their variant: in constant evaluation each runs
another algorithm, Dekker's product (`two_prod_dekker`, on the operands as they are), whose
results are not always the values of its run-time form ([The two executions of a
product](design/milestone2.md#the-two-executions-of-a-product)); what is proved of each is a
theorem written by hand (`two_prod_two_executions_exact`, `two_prod_entry_two_executions_exact`:
the same values when the error term of constant evaluation is finite and the product is exact),
audited in `proofs/audit/HandAudit.v`. The other entry forms of the products are not `constexpr`.

C++ emission rules: non-template functions, one overload per limb type; one operation per
statement; kernels of at most two limbs are force-inlined, but a kernel that says
`ordinary_inline:` in its description (today `interval_mul_2`, the largest listing of Milestone 2,
some four hundred operations after inlining: [Inlining and compile
time](design/milestone2.md#inlining-and-compile-time) and its question 13), which is an ordinary
inline function that a compiler may call rather than inline into every caller. Its callees are
inlined into it as always. The public operations of `Ball` that
round are functions of `ball_operations.hpp` that force-inline their kernel and are themselves
forced inline (the default), outlined or external, as `KAIRN_ENCLOSURE_CODE` says
([Getting started](../getting-started/index.md#compile-time-and-the-operations-of-ball)); the code
of the kernel is the same in each, and the generated files do not depend on the setting. A kernel is `constexpr` when its only
fused operations are `prod` or it names a constant-evaluation variant; a kernel that is not
`constexpr` is listed as such in the generator's output. `guard` and `times_inf` dispatch on
`__builtin_is_constant_evaluated()` too, so the full kernels of the additions and the constructors
are `constexpr`; the products of two limbs, the Ball cores and their full kernels are not, because
they contain FMAs with an addend that is not zero, and so are not the directed products of one
limb, `mul_down_1` and `mul_up_1` (and their entry forms), which must not be evaluated through
`two_prod`'s variant
([Building blocks on T](design/milestone2.md#building-blocks-on-t)), nor the steps of the dot
products, `dot_step_1` (an FMA with the state as addend) and `dot_step_2` (`mul_2_2`).

The operations of the IR have no side effects. Kairn does not specify the floating-point
exception flags that a kernel raises, so a printer may leave out of a path of execution any
operation whose value that path does not use: the outputs, which are all that a statement or a
proof is about, do not change. The scalar printer does so for the fix-up of a full kernel, a
full Ball kernel and a constructor of a ball: the operations that its masks and the first arms of
its selects need come first; when the masks are true the outputs are those arms; otherwise the
rest of the listing runs. With Clang on AArch64 that rest is a function of its own, never
inlined; elsewhere it is inline. The rule, which kernels it applies to and the measurements behind
the two forms are in [Milestone 1 statements](design/milestone1.md#ieee-like-results), under
"Emission". Packed code keeps every select, as a blend. Each path computes operations of the
listing and nothing else, so R1 holds of it as it holds of the listing; an output on the first
path is the first arm of a select of the listing, the result of an addition, a subtraction, a
fused operation or a guard, or in `ball_make_2` a limb of the center it was given, which R3
already counts as safe to add.

**A limb type of a format chosen at run time.** The scalar printer writes every kernel and fold
for one more limb type, used by the tests only: `kairn::emulated::Number`
(`tests/emulated/number.hpp`), a number of a binary format $(p, q_{\min}, q_{\max})$ set when the
program runs, computed with integers alone ([Testing](testing.md#the-emulated-formats)). Its
kernels are `tests/emulated/gen/kernels.hpp`, which `build` writes and `check` compares, in a
generated directory of its own (`gen/kairn_gen/emulated.py`). They are printed by the functions
that print `include/kairn/gen/scalar.hpp`, with the limb type as their parameter (`cpp.Limb`):
the same functions in the same order, the same statements, fix-up branches, inlined calls and
selects. The type changes only what depends on it: its name; each literal, which for double is
the constant's value in `binary64` and here is the constant's value in the run-time format,
`kairn::emulated::constant(i)`, the values of every constant in every format the runner knows
being tables at the end of the file, computed by `consts.py` as the literals of double and float
are; the test of constant evaluation, which there is a mode of the runner,
`kairn::emulated::constant_evaluation()`, since nothing of the type is evaluated at compile time;
and `constexpr`, which it does not need. The generator's tests compare the two listings token for
token outside those places (`gen/tests/test_emulated.py`). The formats it knows are `binary64`,
`binary32` and formats of the statements of precision 8 to 11 (above, "Number formats"); every
constant of every kernel must be a number of each, or `build` refuses to write the file.

### Folds

A fold ([Folds, the extension of the IR](design/milestone2.md#folds-the-extension-of-the-ir)) is
a loop of kernels along arrays: a sum, a dot product. It is a description of its own,
`gen/kernels/NAME.fold`, beside the kernels, and has no listing: its step, its combination and its
finish are kernels, with their own descriptions, listings, models and statements, and every rule
above applies to them as to any kernel. `dot_2` in full:

```
fold:          dot_2
arrays:        supplied x = x0 x1, supplied y = y0 y1
state:         s = s0 s1
step:          s = dot_step_2(s, x, y)
combine:       s = add_2_2(s, s)
orders:        sequential, lanes
writes:        none
output:        r = r0 r1
output:        mask flag
finish:        (r, flag) = fold_finish_2(s)
value:         x*y
requires:      canonical x
requires:      canonical y
ensures:       normalized r
ensures:       fold_error r eps=3*u^2/(1-4*u) term=4*u^2 tau=3/2*eta rel=n-1 abs=n-1
ensures:       finite_or_nan r flag=flag
min_precision: 4
theorem:       proofs/theories/FoldSums.v
ieee_theorem:  proofs/theories/IeeeFolds.v
status:        proved
domain:        extended
source:        Higham's bound for summation over any tree, with the bounds of add_2_2 and mul_2_2 (MR22)
license:       bound: published; proof: MIT
```

- **The arrays** are read one array per limb (`x0`, `x1`, ...), each declared `stored`, a container
  whose elements were written through Kairn, or `supplied`, the program's own array. An *element*
  is one entry of every array.
- **The state** starts at zero, every limb $+0$. **The step** is a kernel whose inputs are the
  state and one element of each array, in the order the line gives them, and whose one output is
  the next state. **The combination** takes two states, the accumulated one first, and returns
  one. **The finish** takes the final state and returns the fold's outputs (or `finish: none`,
  and the fold returns its state). `writes: none`: a fold that writes an array is a map
  ([Maps](#maps), below).
- **The orders**, those of `proofs/theories/Folds.v`. *Sequential* (`fold_seq`): the step
  applied element after element. *Lanes* with $W$ lanes (`fold_lanes`): the first
  $W\lfloor n/W\rfloor$ elements dealt to $W$ lanes, element $i$ to lane $i \bmod W$; each lane
  folded sequentially from the zero state; the lane states combined from lane 0 upward,
  $((l_0 \oplus l_1) \oplus l_2) \oplus \dots$; the remaining $n \bmod W$ elements folded into
  the result. With $W = 0$, or one lane, or fewer elements than lanes, that is the sequential
  order (with fewer elements than lanes because $0 \oplus 0$ is the zero state).

The folds of this stage are the sums and dot products of the page: `sum_1`, `sum_2` and
`sum_fast_2` (the fast addition) on stored arrays, their `_entry` forms on supplied ones, whose
steps (`sum_entry_step_1`, `sum_entry_step_2`, `sum_fast_entry_step_2`) pass each limb of the
element through `guard`, and `dot_1` (the fused step `dot_step_1`, `t = fma(x, y, s)`) on stored
arrays and `dot_2` (`dot_step_2`: `p = mul_2_2(x, y); t = add_2_2(s, p)`) on supplied ones, whose
steps only multiply their elements, which the addition part of rule R3 asks no guard of.
`dot_1_entry` is `dot_1` with the step `dot_entry_step_1` on supplied arrays, which guards both
factors before the fused operation (R3, the factors of a fused operation, above): the dot product
of one limb of `kairn/batch.hpp` calls it; `dot_2`, whose elements are factors of the fused
operations of `mul_2_2`, unguarded, is on the pending list of that rule (`rules.FACTOR_PENDING`).
The finishes `fold_finish_1` and
`fold_finish_2` return the state with the flag true when its leading limb is finite, and
otherwise the canonical NaN, every limb a NaN, with the flag false
([When something is not finite](design/milestone2.md#sum-dot-axpy-convolution)).

**What the generator checks of a fold**, and refuses it otherwise:

1. Its names: no name it prints (`F_step`, `F_combine`, `F_seq`, `F_lanes`, `F_packed`, the
   statements and theorems) is a kernel's; its groups and limbs are distinct names, none one the
   printers use.
2. The shapes: the step takes the state and every array once, each with the number of limbs of
   the group passed, and returns one group of the shape of the state; the combination takes two
   groups of that shape and returns one; the finish takes one and returns the fold's outputs.
   The step and the combination have real-model statements (the finish need not). The lane
   order needs a combination.
3. Rule R3 on a supplied array: the step is an entry kernel that takes the element's limbs as
   values of the program (one-limb inputs not `stored`, or a multi-limb input `supplied`), and
   the analysis of an entry kernel, `rules.r3_analysis`, run on the step with exactly those
   limbs as values of the program, finds no addition or FMA addend reached before `guard`, and
   no next state that is such a limb as it is. A limb the step only multiplies or compares needs
   no guard of this analysis (`dot_k`); a factor of a fused operation is the factor rule's (R3,
   the factors of a fused operation, above). The state is not a value of the program. A stored
   array is asked nothing.
4. The zero state, with the combination of the lane order, has the four properties that the
   theorems take as one hypothesis (`zero_identity`, `proofs/theories/Summation.v`):
   (1) it is valid; (2) its value is 0; (3) $0 \oplus x$ has the value of $x$ for every valid
   $x$; (4) $0 \oplus 0$ is the zero state, limb for limb. That they hold in every format is a
   lemma about the combination, proved once (`add_1_1_zero`, `add_2_2_zero`,
   `add_fast_2_2_zero` of `proofs/theories/SummationKernels.v`): a combination without such a
   lemma is refused (`rules.ZERO_LEMMAS`). The generator then checks property 2 syntactically
   (every limb of the zero state is the literal $+0$) and properties 1, 3 and 4 by evaluation,
   with the interpreter, in `binary64`, `binary32` and five small formats (precision 1 to 5):
   (1) against the combination's requirements on its operands, (4) exactly, (3) on every number
   of the small formats and, for two limbs, every number with the second limbs at the ends of
   what a normalized pair allows; the generator's tests also try property 3 on every normalized
   pair of three formats. What holds for every format and every operand is the proof's.
5. The claims: `value` over the arrays' names, `requires` of each element (`canonical` of an
   array of two limbs), `ensures` of the kinds `normalized`, `fold_error` and `finite_or_nan`
   (the last only with a finish that claims it); the constants of `fold_error` in the language
   of `const up(EXPR)`, `eps` positive, `term` and `tau` nonnegative in both formats of the
   library, the heights `n` or `n-1`; and `eps` is the relative error of the combination,
   $c\,u^k$ of its error entry (of form R or A, without an absolute term), compared exactly at
   every precision from the fold's minimum to 64. The minimum precision is at least the step's
   and the combination's.
6. The status: `unverified`, or `proved` with `theorem: FILE`, `source` and `license`; the file
   then holds `F_seq_correct` and `F_lanes_correct`.

What a fold's proof establishes beyond these: that the generated step and combination are those
the theorems of `SummationKernels.v` name (`add22`, `dot_step_2`, `dot_step_1`) on every state
and element, and from there the bound in both orders, for every width.

**In C++** a fold is three ordinary inline functions per limb type, not forced inline
([Inlining and compile time](design/milestone2.md#inlining-and-compile-time)), none `constexpr`:

```
void F_seq(const T* x0_in, const T* x1_in, ..., std::size_t n, T& r0_out, ..., bool& flag_out)    scalar.hpp
void F_lanes(const T* x0_in, ..., std::size_t n, std::size_t lanes, T& r0_out, ..., bool& flag_out) scalar.hpp
void F_packed(const T* x0_in, ..., std::size_t n, T& r0_out, ..., bool& flag_out)      avx2.hpp, neon.hpp
```

Whether a loop is proved is in `include/kairn/gen/bounds.hpp`, beside the kernels':
`kairn::gen::bounds::loops::F<T>::proved` is true exactly when the claims give the fold the status
proved (the theorems of its statements in both models), `T` has at least its minimum precision,
and every kernel it runs (step, combination, record, check, radius, bound, finish, and those of
the fold of its coefficients or centers, itself proved) is proved for `T` (`library.loop_lines`).
A public function on arrays gates on the status of its loop, not on those of its parts.

One pointer per limb array and a length; nothing is allocated; `n = 0` gives the finish of the
zero state, every limb $+0$ and the flag true. `F_seq` is a loop over the scalar step. `F_lanes`
is the lane order for any number of lanes, computed one lane after the other: lane $j$ folded from
the zero state over elements $j, j + W, \dots$ of the first $W\lfloor n/W\rfloor$, combined into
the result as soon as it is done (the result is lane 0's at $j = 0$), then a loop over the rest:
the operations of the definition, in its order, with no storage but two states. It is the
reference. `F_packed` is the lane order with $W$ the lanes of the register (AVX2: 4 doubles, 8
floats; NEON: 2 and 4): a loop over the packed step on blocks of $W$ elements, the $W$ lane states
stored and combined in scalar code from lane 0 upward, the scalar step on the remainder, the
finish. In every lane the packed step computes what the scalar step computes, so `F_packed` is,
bit for bit, `F_lanes` with that $W$; for $n < W$ both combine $W$ zero states. The step, the
combination and the finish are inlined as calls are in a kernel, one operation per statement,
their values named `step_V`, `comb_V` and `fin_V`; the loop's own variables end with an
underscore, and the parameters are the limbs' names with `_in` and `_out`, so that no name of the
generated text can be one of the fold's, which have no underscore. A guard in a fold is
`a + 0.0`, as in a kernel that is not `constexpr`.

The model of a fold in Rocq, its statements and its claims are below ([The formal
model](#the-formal-model), [Claims of Milestone 2](#claims-of-milestone-2)); its requests in the
line protocol too ([The line protocol](#the-line-protocol)).

### Maps

A map is a fold that writes an array: $z_i$ is the step on element $i$ and on scalars given once,
$z = a\,x + y$ entry by entry for `axpy_2`. `axpy_2` in full:

```
fold:          axpy_2
arrays:        supplied x = x0 x1, stored y = y0 y1
scalars:       supplied a = a0 a1
state:         mask finite
step:          z = axpy_step_2(a, x, y)
combine:       finite = and(finite, finite)
orders:        sequential, lanes
writes:        z = z0 z1
check:         fold_finish_2
finish:        none
value:         a*x+y
requires:      canonical a
requires:      canonical x
requires:      canonical y
ensures:       entries z
ensures:       finite_or_nan z flag=finite
min_precision: 4
theorem:       proofs/theories/FoldMaps.v
ieee_theorem:  proofs/theories/IeeeFoldMaps.v
status:        proved
domain:        extended
```

- **The scalars** are groups given once, each declared `stored` or `supplied` as an array is, and
  passed to every step.
- **The step** takes the scalars and one element of each array, in the order of the line, and
  never the state, so that no written element depends on the order; it returns one element of the
  array written (`writes`, one array). It is an ordinary kernel with a real-model statement.
- **The state** is one mask, true at the start; **the combination** is the operation `and`, exact,
  associative and commutative; its left identity and its own conjunction, `true`, stand for the
  zero state (`andb_true_l` of Rocq's `Bool`). **The check** is a kernel such as `fold_finish_k`,
  which takes a written element and returns it, or its canonical NaN, with the mask that its
  leading limb is finite: the state is the `and` of the check's mask on every element written.
  When it is false at the end, a second pass rewrites every element as the check returns it: an
  element that is not finite becomes the canonical NaN, the others stay ([When something is not
  finite](design/milestone2.md#sum-dot-axpy-convolution)). The map returns the mask.
- **What the generator checks** besides the names (`rules.map_rules`): one array written, the shapes
  of the step's operands and result, a state of one mask combined by `and`, a check of the shape of
  `fold_finish_k`, no finish and no output; rule R3 on the supplied arrays and scalars, as for a
  fold (`_map_r3`: the step takes them as values of the program, guards what it adds of them, and
  writes none of them as it is); its value is the step's, with the step's inputs renamed to what
  the map passes; every requirement of the step on what the map passes (`normalized`,
  `power_of_two`) is a requirement of the map (`canonical`, `power_of_two`); its claims are
  `entries` and `finite_or_nan` with the state as the flag; the extended domain; the minimum
  precision; the status.

The maps of this stage are `add_k`, `sub_k` (on stored arrays: `add_1_1`, `sub_1_1`, `add_2_2`,
`sub_2_2`) and their `_entry` forms on supplied arrays (`add_entry_step_k`, `sub_entry_step_k`,
which guard every limb of both operands); `axpy_1` ($a$ of `T`, `mul_1_1` then `add_1_1`),
`axpy_2` ($a$ of two limbs, `mul_2_2` then `add_2_2`) and `axpy_2_1` ($a$ of `T`, `mul_2_1`), with
`x` supplied (only multiplied, so unguarded by the addition part of R3; of two limbs, a factor
of the fused operations of `mul_2_1` and `mul_2_2`, on the pending list of the factor rule) and
`y` stored, and their `_entry` forms with `y` supplied and guarded; `scale_1` and `scale_2` (by
$a$ of `T`: `mul_1_1`, `mul_2_1`), `scale_2` on stored arrays and its `_entry` form `scale_2_entry`
on supplied ones, whose step `scale_entry_step_2` guards the limbs of the element and $a$ (R3,
the factors of a fused operation); and
`mul_pow2_map_1`, `mul_pow2_map_2` (by a power of two; the name `mul_pow2_2` is a kernel's). The
steps of `axpy` claim an error of form `T`, relative to $\lvert a x\rvert + \lvert y\rvert$, the
form in which the page exports the bound of `axpy`.

**In C++** a map has the three functions of a fold, with the scalars by value and one pointer per
limb array written:

```
void axpy_2_seq(const T* x0_in, const T* x1_in, const T* y0_in, const T* y1_in, std::size_t n,
                T a0, T a1, T* z0_out, T* z1_out, bool& finite_out)
void axpy_2_lanes(..., std::size_t n, std::size_t lanes, T a0, T a1, T* z0_out, T* z1_out, bool& finite_out)
void axpy_2_packed(..., std::size_t n, T a0, T a1, T* z0_out, T* z1_out, bool& finite_out)
```

`F_seq` loops over the elements: the step, the element written, the check's mask and-ed into the
state. `F_lanes` is the lane order, lane after lane, and writes the same elements. `F_packed`
loads blocks of $W$ elements, computes the packed step with the scalars broadcast, stores the
elements, ands the packed check's mask into a lane mask, reduces it (`movemask` on AVX2, `vminvq`
on NEON) and does the rest with the scalar step. All three end with the same second pass. Only
what the check's mask needs of the check is printed in the first pass. **Aliasing**: an array
written may be exactly one of the arrays read (the same pointer, $z = x$ or $z = y$, in place),
since every element is read whole before it is written and nothing else reads it; otherwise it
overlaps no array read or written, nor the other arrays written. A partial overlap is not
supported. The generated comment of each map says so, and `test_maps.Aliasing` runs every map in
place in each of its forms.

### Folds of maxima

A fold of maxima computes the largest magnitude of the elements of an array, or a bound of it:
`norm_upper_k` ([sum, dot, axpy, convolution](design/milestone2.md#sum-dot-axpy-convolution),
and `bv_norm_upper_k` of [BallVector](design/milestone2.md#ballvector), which applies it to the
centers). `norm_upper_2` in full:

```
fold:          norm_upper_2
arrays:        stored x = x0 x1
state:         m, mask ok
step:          (m, ok) = norm_step_2(m, ok, x)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
orders:        sequential, lanes
writes:        none
output:        r
output:        mask flag
finish:        (r, flag) = norm_finish_2(m, ok)
value:         abs(x)
requires:      canonical x
ensures:       upper r max steps=1
ensures:       finite_or_nan r flag=flag
min_precision: 1
theorem:       proofs/theories/FoldNorm.v
ieee_theorem:  proofs/theories/IeeeFoldNorm.v
status:        proved
domain:        extended
```

- **The state** is two groups: a limb `m`, the largest magnitude so far, which starts at $+0$, and
  a mask `ok`, which starts true (`state: m, mask ok`; the step, the combination and the finish
  take and return the groups in that order). A maximum computed by a comparison,
  `select(lt(m, a), a, m)`, keeps `m` when `a` is a NaN, so the NaN would be lost: the mask is
  the `and`, over the elements, of `eq(a, a)`, false for a NaN only, and the finish tests it
  ([When something is not finite](design/milestone2.md#sum-dot-axpy-convolution)). An infinite
  element needs no mask: the comparison keeps it in `m`.
- **The combination** `norm_combine` is the maximum of the two limbs and the `and` of the two
  masks, and claims `maximum r m n`. **The step** is the combination applied to the state and to
  what the element gives: `norm_step_1(m, ok, x)` is `a = abs(x); e = eq(a, a); (r, okr) =
  norm_combine(m, ok, a, e)`, and `norm_step_2` is `norm_step_1` on the leading limb $x_0$ (its
  $x_1$ is `unused`, and its limb array is a parameter of the C++ functions that is not loaded).
  So the step is the combination of the state and of a function of the element, and the
  combination is associative, commutative and idempotent on every state: every order computes
  the same final state.
- **The masks of the combination and of the step are claimed by nothing.** Their outputs `okr` are
  the `and` of the incoming masks (`norm_combine`) and that and "the element's leading limb is not a
  NaN" (`norm_step_k`), and no kind of the vocabulary says that of a mask: `predicate` is a relation
  between the exact values of two expressions, false for a NaN operand, and a mask input is no value.
  The entries of `gen/claims.json` for these two kernels have only `maximum` of the limb. It is
  safe: the masks are only ever combined and given to a finish, and what comes out of the finish is
  claimed (`finite_or_nan` with `if=ok` of `norm_finish_k`, `upper r max` and `finite_or_nan` of the
  fold, `encloses_entries` of a ball vector), so a wrong mask makes a claim of the fold or of the
  ball vector false wherever it matters (a NaN element whose mask stayed true gives a finite result
  from a NaN element, which the fold's reading forbids). And the generator checks the definitions by
  rule (`rules.max_rules`: the operation that defines the combination's mask is the `and` of its two
  masks, and the step is the combination on the state and on `(abs(x0), eq(abs(x0), abs(x0)))`, its
  listing with its calls inlined). A reader that judges these kernels alone can judge the limb, and
  may check the masks against that definition as a test of its own, not as a claim.
- **The finish** returns the limb when the mask is true and its result is finite, stepped up
  `steps` times: `norm_finish_1` returns $m$, `norm_finish_2` returns $\mathrm{succ}(m)$, which is
  above every element (a normalized pair is strictly between the neighbors of its leading limb,
  `normalized_2_between` of `proofs/theories/Convert.v`, and a step is monotone) and at most one
  step above the smallest number of `T` not below the largest of them; otherwise the canonical
  NaN and the flag false. Each finish claims `finite_or_nan r flag=flag if=ok`, with `steps=1`
  for two limbs.
- **The claim** `upper r max steps=S`: with $v_i$ the value of element $i$ (`abs(x)`, the exact
  magnitude of the element) and $V = \max_i v_i$ ($0$ for no element), $V \le r \le
  \mathrm{RU}(V)$ stepped up $S$ times; for one limb ($S = 0$) $r$ is $V$ itself.

**What the generator checks of a fold of maxima** (`rules.max_rules`, and the claims in
`_fold_claims`), besides the names, the shapes and rule R3 of every fold: the state is a limb and
a mask; the fold reads one array, and its value is `abs(ARRAY)`; the combination claims the
maximum of its two limb operands, and the operation that defines its mask in its listing is the
`and` of its two masks; the step takes the state first, claims the maximum of the state and of the
magnitude of the leading limb of the element, and is, on its listing with its calls inlined, a call
of the combination on the state whose outputs are the step's; the finish claims `finite_or_nan`
with `if=` the state's mask, and the `steps` of the fold's `upper` claim are those of the finish.
Of the zero state, $(+0, \text{true})$, it checks syntactically that every limb is $+0$ and every
mask true, and by evaluation in the formats of `ZERO_FORMATS` that $0 \oplus 0$ is the zero state,
limb for limb (what the lane order with fewer elements than lanes needs); and by evaluation, on
every pair and triple of states of two small formats ($p = 2$ and $3$; every magnitude, both values
of the mask), that the combination is commutative, associative and idempotent, the hypotheses of
the order lemma. Left to the proofs: those laws in every format (from the claim `maximum` and the
definition of `and`), that the step is the combination of the state and of a function of the
element (by unfolding), and the bound. No lemma of `SummationKernels.v` is asked for: the zero
state of a maximum is not an identity of an addition, and `ZERO_LEMMAS` is about additions.

**The order lemmas** are in `proofs/theories/Folds.v`. The first, for a step that is the
combination of the state and of a function `g` of the element:

```coq
Lemma fold_lanes_aci :
  forall (A B : Type) (P : A -> Prop) (combine : A -> A -> A) (g : B -> A) (zero : A),
  P zero ->
  (forall a b : A, P a -> P b -> P (combine a b)) ->
  (forall a b : A, P a -> P b -> combine a b = combine b a) ->
  (forall a b c : A, P a -> P b -> P c -> combine (combine a b) c = combine a (combine b c)) ->
  combine zero zero = zero ->
  forall (W : nat) (xs : list B), Forall (fun x => P (g x)) xs ->
  fold_lanes (fun s x => combine s (g x)) combine zero W xs =
  fold_seq (fun s x => combine s (g x)) zero xs.
```

It asks the laws only on a set $P$ (in the real model the states whose limb is a number of the
format, where the claim `maximum` gives the combination), and of the zero state only that
$0 \oplus 0 = 0$, which idempotence gives: the $W$ lanes all start from it. It cannot be applied in
the IEEE model to a list with a NaN element: the step combines the state with the pair the
element gives, $(\mathrm{NaN}, \text{false})$ for a NaN, and that pair lies outside every set on
which the maximum by comparison is commutative. The proofs use the second lemma,
`fold_lanes_aci_step`, which takes the step separately: of each element $x$ it asks that $g(x)$ be
in $P$ and that, on every state of $P$, the step be the combination with $g(x)$. In the IEEE model
$P$ is the set of states whose limb is not a NaN and not $-0$, and $g$ of a NaN element is
$(+0, \text{false})$, with which the step agrees on $P$ though its listing combines with
$(\mathrm{NaN}, \text{false})$.

**In C++, in Rocq, in the claims**: as every fold, with the state's mask a `bool` (true at the
start) in scalar code, a lane mask in packed code (all bits set at the start, its lanes stored
after the loop with `movemask` on AVX2 and `vst1q_u64`, `vst1q_u32` on NEON, and read one by one
as `bool`s for the combination from lane 0), and a `bool` of the tuple of the state in Rocq
(`R * bool`, from `(0, true)`). The real-model statement (`FoldStatements.v`) is about the result
that the finish computes from the final state, its limb stepped up `S` times ($r$; Flocq's `succ`),
which the finish's claim says is what it returns when its flag is true:

```coq
Definition norm_upper_2_seq_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall xs : list (R * R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  let mok := norm_upper_2_seq xs in
  let r_ := succ radix2 (FLT_exp emin prec) (fst mok) in
  let v_ := fold_right Rmax 0 (map (fun x => (Rabs (fst x + snd x))) xs) in
  fmt emin prec r_ /\
  v_ <= r_ /\
  r_ <= succ radix2 (FLT_exp emin prec) (RU emin prec v_).
```

The IEEE-model statement (`IeeeFoldStatements.v`) says that a true flag means finite elements, a
finite result whose value is that $r$ of the real model on the values of the elements, and these
claims; a false flag, a NaN. The steps and the combination of a fold of maxima have no lead
statement (`K_ieee_lead_spec`): their maximum keeps a finite state when the element is a NaN, so
the statement would be false of them, and the mask says it instead.

Two more statements of the IEEE model, for each fold of maxima of both orders (`ieee.max_orders_statement`,
`ieee.max_flag_statement`), with no requirement on the elements (any value, NaNs and infinities
included) and for every precision: `F_orders_ieee_spec`, that the lane order computes the state of the
sequential order, for every number of lanes $W$ (so its finish gives the same result and the same flag),

```coq
Definition norm_upper_2_orders_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax),
  forall (W : nat) (xs : list (binary_float prec emax * binary_float prec emax)),
  fold_lanes (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) (IeeeFoldModel.norm_upper_2_combine prec emax) (IeeeOperations.pzero prec emax, true) W xs =
  fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) (IeeeOperations.pzero prec emax, true) xs.
```

and `F_flag_ieee_spec`, when exactly the flag of the sequential order is true: when the leading limb
of every element is finite and the largest magnitude, the limb of the final state stepped up as the
finish does (`steps` of its `finite_or_nan`), is finite; with no step (`norm_upper_1`), when every
element is finite:

```coq
Definition norm_upper_2_flag_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  forall xs : list (binary_float prec emax * binary_float prec emax),
  snd (IeeeFoldModel.norm_upper_2_seq prec emax nan_abs nan_const xs) = true <->
  Forall (fun x => finite (fst x)) xs /\
  finite (IeeeOperations.succ prec emax (fst (fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) (IeeeOperations.pzero prec emax, true) xs))).
```

Their theorems, `F_orders_ieee_correct` and `F_flag_ieee_correct`, are in the file the fold's
`ieee_theorem` names, with those of its orders (`ieee.proved_statements`): the comments above the
two statements say proved when it does, and `IeeeAudit.v` checks them after those of the orders.

Both are unverified until a proof is pointed at them: they are the types of the hand-written
theorems of these facts (`norm_upper_k_lanes_seq_state`, `norm_upper_k_seq_ieee_flag`) once their
section's variables are bound, so that those theorems can prove generated statements rather than
statements of their own. No audit lists them yet.

### Convolutions

A convolution writes the coefficients of the product of two polynomials: `conv_k`
([sum, dot, axpy, convolution](design/milestone2.md#sum-dot-axpy-convolution)), which
`bv_conv_k` of [BallVector](design/milestone2.md#the-product-of-polynomials) applies to the
centers. `conv_2` in full:

```
fold:          conv_2
arrays:        supplied x = x0 x1, supplied y = y0 y1
coefficients:  dot_2
state:         mask finite
combine:       finite = and(finite, finite)
orders:        sequential
writes:        z = z0 z1
check:         fold_finish_2
finish:        none
value:         x*y
requires:      canonical x
requires:      canonical y
ensures:       coefficients z
ensures:       finite_or_nan z flag=finite
min_precision: 4
theorem:       proofs/theories/FoldConv.v
ieee_theorem:  proofs/theories/IeeeFoldConv.v
terms_theorem: proofs/theories/FoldConv.v
status:        proved
domain:        extended
```

- **The arrays** are the two polynomials, $x$ of $n_x$ coefficients and $y$ of $n_y$, each of its
  own length. **The array written**, $z$, has $n_x + n_y - 1$ coefficients, none when a length is
  $0$.
- **Coefficient $j$** is the fold `coefficients:` (`dot_2`, `dot_1` for one limb) in its
  sequential order on the terms $(x_i, y_{j-i})$, $i$ from $\max(0, j - n_y + 1)$ to
  $\min(j, n_x - 1)$ in increasing order: its zero state, its step on each term, its final state
  written as the coefficient. A convolution has no step of its own. The number of terms of a
  coefficient, $m_j$, is at most $\min(n_x, n_y)$, so the exported bound of `dot` for
  $\min(n_x, n_y)$ terms covers every coefficient; the statement of each is the one for its own
  $m_j$.
- **The mask and the second pass** are a map's: the mask is the `and` of the check's flag on every
  coefficient, the check is the finish of the fold of the coefficients (`fold_finish_k`), and when
  the mask is false a second pass makes every coefficient that is not finite the canonical NaN.
- **The order** is the sequential one only, and there is no packed form. The lanes of a register
  would compute $W$ consecutive coefficients, whose ranges of terms differ at both ends: each lane
  would need a blend at every step near the ends, or zero terms that the coefficient does not have,
  which add terms to what its statement is about and change the sign of a zero. That is not a
  plain use of the packed step, so it is left out.
- **Aliasing**: the array written overlaps neither array read (a coefficient reads several entries
  of each, after earlier coefficients were written), nor itself. The generated comment says so;
  the generated code has no check of it, as the maps have none.

**What the generator checks of a convolution** (`rules.conv_rules`): the fold of its coefficients
is a fold of a sum with a finish and a combination, not a map, a convolution or a fold of maxima,
and has the sequential order; the convolution's two arrays are that fold's, names, limbs and roles
included (so that rule R3, which that fold passes, holds of the convolution); it has no step and
no scalar; it writes one array of the shape of that fold's state; its state is one mask combined
by `and`; its order is `sequential`; its check is that fold's finish; no name of that fold's state
is one of its own; its value and requirements are that fold's; it claims `coefficients` and
`finite_or_nan` of the array written, with its mask as the flag; it is of the extended domain, and
its minimum precision is at least that fold's.

**In C++** a convolution is one function per limb type, with each array's length after its limb
pointers:

```
void conv_2_seq(const T* x0_in, const T* x1_in, std::size_t n_x, const T* y0_in, const T* y1_in,
                std::size_t n_y, T* z0_out, T* z1_out, bool& finite_out)
```

A loop over the coefficients: the state of the fold of the coefficients from zero, a loop over the
terms (`lo_` to `hi_`, `x` at `i_` and `y` at `j_ - i_`) with the step inlined, the coefficient
written, the check's flag and-ed into the mask; then the second pass of a map over the
$n_x + n_y - 1$ coefficients.

**In Rocq** (`FoldModel.v`) the terms of coefficient $j$ are a list built with stdlib's list
functions, and the coefficients a `map` over their indices:

```coq
Definition conv_terms {A B : Type} (xs : list A) (ys : list B) (j : nat) : list (A * B) :=
  combine (skipn (j - (length ys - 1)) (firstn (S j) xs)) (rev (firstn (S j) ys)).

Definition conv_length (nx ny : nat) : nat :=
  match nx, ny with
  | O, _ | _, O => O
  | _, _ => (nx + ny - 1)%nat
  end.

Definition conv_2_conv (xs : list (R * R)) (ys : list (R * R)) : list (R * R) :=
  map (fun j => dot_2_seq (conv_terms xs ys j)) (seq 0 (conv_length (length xs) (length ys))).
```

and its statement (`FoldStatements.v`) is, coefficient by coefficient (`Forall2` of the indices and
the coefficients), the conclusion of `dot_2_seq_spec` on the list of its own terms:

```coq
Definition conv_2_spec : Prop :=
  forall emin prec : Z, (4 <= prec)%Z ->
  forall xs ys : list (R * R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  Forall (fun y => normalized_2 emin prec (fst y) (snd y)) ys ->
  Forall2 (fun j s =>
    let xys := conv_terms xs ys j in
    normalized_2 emin prec (fst s) (snd s) /\
    Rabs ((fst s + snd s) - sumR (map (fun xy => ...) xys)) <= ... (length xys - 1) ... (INR (length xys) * ...))
    (seq 0 (conv_length (length xs) (length ys))) (conv_2_conv emin prec tie_even xs ys).
```

Its proof is `dot_2_seq_correct` on each coefficient, through the lemma `Forall2_map_r` of
`Folds.v` (that of the maps, with the list `seq 0 (conv_length ...)`) and two lemmas about
`conv_terms` of `proofs/theories/FoldConv.v` (not of `Folds.v`: `conv_terms` is defined in the
generated `FoldModel.v`, which imports `Folds.v`):

```coq
Lemma conv_terms_Forall :
  forall (A B : Type) (P : A -> Prop) (Q : B -> Prop) (xs : list A) (ys : list B) (j : nat),
  Forall P xs -> Forall Q ys -> Forall (fun ab => P (fst ab) /\ Q (snd ab)) (conv_terms xs ys j).

Lemma conv_terms_length :
  forall (A B : Type) (xs : list A) (ys : list B) (j : nat),
  (length (conv_terms xs ys j) <= Nat.min (length xs) (length ys))%nat.
```

The first gives each coefficient the hypothesis of `dot_2_seq_spec`; the second is what lets a
program bound every coefficient by `dot(min(n_x, n_y))`. That `conv_terms xs ys j` is exactly the
list of the pairs $(x_i, y_{j-i})$ in increasing $i$ is what makes the model the convolution:

```coq
Lemma conv_terms_nth :
  forall (A B : Type) (xs : list A) (ys : list B) (j k : nat) (a : A) (b : B),
  (k < length (conv_terms xs ys j))%nat ->
  nth k (conv_terms xs ys j) (a, b) =
  (nth (j - (length ys - 1) + k) xs a, nth (j - (j - (length ys - 1) + k)) ys b).
```

(`FoldConv.v` again, with `conv_terms_eq`, the list as a `map` over the consecutive $i$; the
generator's tests check that list against the definition on every pair of lengths up to 7,
`test_conv.Printers.test_conv_terms_is_the_terms`). The statements of a convolution and of a map in
the IEEE model are below ([In the IEEE model](#maps-and-convolutions-in-the-ieee-model)).

`FoldStatements.v` states three of these facts about `conv_terms` itself, after the folds, when there
is a convolution or a product of BallVectors (`rocq.conv_terms_statements`), with the types of the
lemmas of `FoldConv.v` so that they can prove them: `conv_terms_eq_spec` (the list is `map (fun i =>
(nth i xs a, nth (j - i)%nat ys b)) (seq (j - (length ys - 1))%nat (length (conv_terms xs ys j)))`),
`conv_terms_count_spec` (with at least one $y$, coefficient $j$ has $\min(j + 1, n_x) - (j - (n_y -
1))$ terms, a subtraction of natural numbers) and `conv_terms_length_spec` (at most $\min(n_x, n_y)$,
which the products of two BallVectors need). They are statements of no kernel or fold: their
theorems (`conv_terms_eq_correct`, `conv_terms_count_correct`, `conv_terms_length_correct`, in
`FoldConv.v`) are named by the convolutions, `terms_theorem: FILE`, the same file by every
convolution that names one (`rules.conv_rules`); then the three comments say proved and `Audit.v`
checks the three theorems once, after the folds (`rocq.CONV_TERMS`); otherwise they say unverified.

### Maps and convolutions in the IEEE model

A map and a convolution have, besides the real-model statement above, a model and a statement in
the IEEE model (`proofs/gen/IeeeFoldModel.v`, `IeeeFoldStatements.v`), in the shape of what is
printed for the sums and dot products: the code they describe is that of the scalar loops, the
first pass, the mask and the second pass included.

**The steps.** The step of every map has the bridge of its core (`ieee: bridge`, and `spec` for
those of two limbs): `K_prog`, the step as a straight-line program, `K_ieee_bridge_spec`, that a
finite leading limb of its result from finite operands means that every value it computes is
finite and that the result is the real model's, and `K_ieee_spec`, its claims under the same
hypotheses (`add_2_2` and `sub_2_2`, steps of `add_2` and `sub_2`, had them already). And each
step has a lead statement, `K_ieee_lead_spec`, printed with those of the folds: for any operands,
with no requirement, a finite leading limb of the result means a finite leading limb of every
operand, the scalars included. The step of a fold of maxima has none (above); the convolutions
use the step of the fold of their coefficients, which has one.

**The model.** For a map `F` (`axpy_2` in full):

```coq
Definition axpy_2_step (a : float * float) (xy : (float * float) * (float * float)) : float * float :=
  IeeeModel.axpy_step_2 prec emax nan_plus nan_minus nan_opp nan_fma (fst a) (snd a) (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) (snd (snd xy)).

Definition axpy_2_check (w_ : float * float) : float * float * bool :=
  IeeeModel.fold_finish_2 prec emax nan_abs nan_const (fst w_) (snd w_).

Definition axpy_2_seq (a : float * float) (xys : list ((float * float) * (float * float))) : list (float * float) * bool :=
  let ws_ := map (axpy_2_step a) xys in
  let m_ := fold_seq (fun m_ w_ => andb m_ (snd (axpy_2_check w_))) true ws_ in
  (if m_ then ws_ else map (fun w_ => fst (axpy_2_check w_)) ws_, m_).

Definition axpy_2_lanes (W : nat) (a : float * float) (xys : list ((float * float) * (float * float))) : list (float * float) * bool :=
  let ws_ := map (axpy_2_step a) xys in
  let m_ := fold_lanes (fun m_ w_ => andb m_ (snd (axpy_2_check w_))) andb true W ws_ in
  (if m_ then ws_ else map (fun w_ => fst (axpy_2_check w_)) ws_, m_).
```

`F_step` is the IEEE model of the step on the scalars and one element, `F_check` the check on one
element written (`fold_finish_k`: the element or its canonical NaN, and the mask that its leading
limb is finite); the mask is `fold_seq` (`fold_lanes` with `andb`, from `true`) of the check's mask
over the elements written, the form of `fold_seq_and` and `fold_lanes_and` of `Folds.v`; when it is
false every element written is what the check returns of it. The names of the model's own binders
end with an underscore, so that none is a name of a description. A convolution `F` has `F_check`
and `F_conv`, with `D` the fold of its coefficients (`conv_2`, `D` = `dot_2`):

```coq
Definition conv_2_conv (xs : list (float * float)) (ys : list (float * float)) : list (float * float) * bool :=
  let ws_ := map (fun j => fold_seq dot_2_step (pzero, pzero) (FoldModel.conv_terms xs ys j))
                 (seq 0 (FoldModel.conv_length (length xs) (length ys))) in
  let m_ := fold_seq (fun m_ w_ => andb m_ (snd (conv_2_check w_))) true ws_ in
  (if m_ then ws_ else map (fun w_ => fst (conv_2_check w_)) ws_, m_).
```

where `dot_2_step` is the IEEE step of `dot_2` (`IeeeFoldModel.v`, above it) and `conv_terms`,
`conv_length` those of `FoldModel.v`, on lists of floats.

**The statements.** `F_seq_ieee_spec` and `F_lanes_ieee_spec` of a map (the second for every `W`),
for every precision from the map's minimum, every `emax` and every choice of NaN, for canonical
scalars and elements (`canonical_2` for two limbs, any value for one, a finite power of two for a
scalar `power_of_two`), with `(ws_, flag_)` the result: `Forall2` of the elements and the elements
written of

- if the leading limb written is finite: every limb of the scalars, of the element and of the
  element written is finite; the values written are those of the real-model step (`Model.v`, at
  `ieee_emin prec emax`) on the values given; and the step's claims hold of them, as its
  `K_ieee_spec` prints them;
- otherwise: every limb written is a NaN, and `flag_` is false;

and `flag_ = true` exactly when the leading limb of every element written is finite. The finiteness
of the scalars is stated element by element, not once: of an empty list nothing is said of them,
and the mask is true. `axpy_2` in full:

```coq
Definition axpy_2_seq_ieee_spec : Prop :=
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax) (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (a0 a1 : binary_float prec emax) (xys : list ((binary_float prec emax * binary_float prec emax) * (binary_float prec emax * binary_float prec emax))),
  canonical_2 a0 a1 ->
  Forall (fun xy => canonical_2 (fst (fst xy)) (snd (fst xy)) /\ canonical_2 (fst (snd xy)) (snd (snd xy))) xys ->
  let '(ws_, flag_) := IeeeFoldModel.axpy_2_seq prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const (a0, a1) xys in
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    (finite z0 ->
     finite a0 /\ finite a1 /\ finite x0 /\ finite x1 /\ finite y0 /\ finite y1 /\ finite z1 /\
     (val z0, val z1) = axpy_step_2 (ieee_emin prec emax) prec tie_even (val a0) (val a1) (val x0) (val x1) (val y0) (val y1) /\
     normalized_2 (ieee_emin prec emax) prec (val z0) (val z1) /\
     Rabs ((val z0 + val z1) - (((val a0 + val a1) * (val x0 + val x1)) + (val y0 + val y1))) <= ...) /\
    (~ finite z0 -> nan z0 /\ nan z1 /\ flag_ = false))
    xys ws_ /\
  (flag_ = true <-> Forall (fun w_ => finite (fst w_)) ws_).
```

`F_ieee_spec` of a convolution, for canonical entries of the two arrays: `Forall2` of the indices
`seq 0 (conv_length ...)` and the coefficients of

- if the leading limb of coefficient $j$ is finite: every limb of every term of `conv_terms xs ys j`
  and of the coefficient is finite, its values are those of the real model `D_seq` (`FoldModel.v`)
  on the values of those terms, and the conclusions of `D_seq_spec` hold of them;
- otherwise: every limb of the coefficient is a NaN, and `flag_ = false` (as in a map's statement;
  until 2026-11-20 the convolution's left the flag out of this branch, which the last line implies);

and `flag_ = true` exactly when the leading limb of every coefficient is finite.

**What the generator checks** of them, besides the rules of a map and of a convolution: that the
names it prints (`F_check`, `F_O_ieee_spec`, `F_ieee_spec` and their theorems and audits) are no
kernel's. **Their theorems**: a map or a convolution may name `ieee_theorem: FILE`, which holds
`F_seq_ieee_correct` and `F_lanes_ieee_correct` (a map) or `F_ieee_correct` (a convolution), checked
in `IeeeAudit.v` against the statements, after the other theorems of `IeeeFoldStatements.v`.

**Judged before they are proved.** `gen/tests/test_ieee_writers.py` reads these statements against
what the code computes: the interpreter on formats of the IEEE shape of two to five bits, whose
largest number is below $2^{p+3}$, so that overflows are frequent, and in `binary64` and `binary32`,
on canonical scalars and elements drawn with infinities, NaN and numbers near the top, in every
order and for several numbers of lanes, the claims of the step in exact arithmetic with the
exponent range widened; the lead statement of every step of a map on operands of any value; and
every build of the compiled runner on the same requests in `binary64` and `binary32`. No case
contradicts a statement.

**What their proofs need**, besides the theorems of the steps: `fold_seq_and` and `fold_lanes_and`
(`Folds.v`: the mask is `forallb` of the check's mask, in both orders); the theorem of
`fold_finish_k` (`IeeeFoldFinish.v`) on each element; `Forall2_map_r` and its converse; and for a
convolution, `conv_terms_Forall` (each term canonical) and the theorem `D_seq_ieee_correct` of the
fold of the coefficients, read on the final state rather than on the finish (a lemma: when the
leading limb of the final state is finite, the finish returns it, so the statement of `D_seq` gives
the claims of the state; when it is not, the check returns the canonical NaN).

### Ball vectors

A `BallVector` ([milestone2.md, "BallVector"](design/milestone2.md#ballvector)) is $N$ centers and
one radius: the set of the vectors each of whose entries is within the radius of its center. It is
*canonical* when it is a **finite ball vector** (every center finite, normalized for two limbs, and
the radius finite and nonnegative) or the **whole space** (every center zero, the radius
$+\infty$); there is no empty state. A ball vector kernel is a fold of its own kind: a map of the
centers whose state is that of a fold of maxima, and whose finish gives the one radius. `bv_add_2`
in full:

```
fold:          bv_add_2
arrays:        stored x = x0 x1, stored y = y0 y1
scalars:       stored rx, stored ry
state:         m, mask ok
step:          z = add_2_2(x, y)
record:        (m, ok) = norm_step_2(m, ok, z)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
radius:        rz = bv_add_radius_2(m, rx, ry)
finish:        (r, finite) = norm_finish_1(rz, ok)
orders:        sequential, lanes
writes:        z = z0 z1
output:        r
output:        mask finite
value:         x+y
requires:      ball_vector x rx
requires:      ball_vector y ry
ensures:       encloses_entries z r x+y x=x,rx y=y,ry flag=finite finite_when=abs_le(abs(x+y)+rx+ry,-2) radii_when=abs_le(rx+ry,-2)
min_precision: 3
theorem:       proofs/theories/BvReal.v
ieee_theorem:  proofs/theories/IeeeBv.v
status:        proved
domain:        extended
```

- **The arrays** are the centers of the operands, stored (written through Kairn), and **the
  scalars** their radii, stored too, and any other operand of `T` (`a`, supplied, for `bv_scale_k`).
  Each array is the centers of one BallVector, whose radius is a scalar (`ball_vector ARRAY
  RADIUS`).
- **The step** writes the center of each entry, as a map's step does: `bv_add_k` is the map `add_k`
  on the centers, `bv_sub_k` the map `sub_k`, `bv_scale_k` the map `scale_k`.
- **The state** is that of the fold of maxima of the centers written: `m`, the largest magnitude of
  a leading limb written, from $+0$, and `ok`, that none was a NaN, from true. **The record** is the
  step of that fold (`norm_step_k`) on each center written, and **the combination** its combination
  (`norm_combine`), in the lane order. So the final state is what `norm_upper_k` on the centers
  written would have before its finish, and both orders give the same.
- **The radius** is a straight-line kernel on `m` and scalars: `bv_add_radius_k(m, rx, ry)`, the
  radius lines of `ball_add_k` with `m` in place of one entry's $\lvert c_{z,0}\rvert$, and
  `bv_scale_radius_k(m, rx, a)`, those of `ball_scale_k`. Every operation of those lines is a
  rounding of a nondecreasing function of `m` on nonnegative values, so at the largest
  $\lvert c_{z,0}\rvert$ the radius is the largest of the $N$ radii the Ball kernel returns entry by
  entry: equal, not only at least (the page's table; `test_bv.py` finds it equal in every case it
  compares).
- **The finish** is `norm_finish_1` on the radius and the state's mask: the radius, with the flag
  true, when no center was a NaN and the radius is finite. A center that is infinite makes `m`
  infinite and with it the radius. **When the flag is false** a second pass writes every center
  zero and the radius returned is $+\infty$: the whole space. An operand that is the whole space
  (radius $+\infty$), a scalar that is not finite, or an overflow anywhere, give the whole space.

**What the generator checks of a ball vector** (`rules.bv_rules`), besides the names: one array
written; a step of a map, every array once and scalars, with a real-model statement, its
requirements given by those of the fold (a normalized center of a canonical BallVector); the record
and the combination are the step and the combination of a fold of maxima of the set whose array has
the shape of the centers (`norm_upper_k`, whose laws `rules.max_rules` checks); the radius takes the
state's limb, then scalars, and has a real-model statement; the finish takes the radius and the
state's mask and claims `finite_or_nan` under that mask with no step (`norm_finish_1`); the
outputs are the radius and the flag; rule R3 on the step (supplied arrays and scalars, as for a
map) and on the radius (a supplied scalar it takes is a value of the program there); each array is
required `ball_vector` with a stored scalar of one limb as its radius; the one claim is
`encloses_entries` of the centers written, the radius and the flag, over the fold's value, one ball
name per array, with `radii_when` over the scalars alone exactly when `finite_when` is not empty;
the extended domain; the minimum precision, at least that of the step, the record and
the radius; the status. A ball vector exact under conditions ([below](#ball-vectors),
`bv_mul_pow2_k`) is checked for the rest of its shape: the state's third group a mask; the step's two
destinations the center and a mask of a name of its own, its outputs a center and a mask; the second
record line `EX = and(EX, E)` and the second combine line `EX = and(EX, EX)`; the radius's arguments
the state's limb, then `EX`, then scalars; a scalar it requires `power_of_two` supplied and of one limb;
and the coherence of the conditions of `exact_when` with those of the step and of the radius
(`rules._bv_exact`). A second record or combine line in any other fold is refused.

**In C++** a ball vector has the three functions of a map, with the radius and the flag by
reference after the arrays written:

```
void bv_add_2_seq(const T* x0_in, const T* x1_in, const T* y0_in, const T* y1_in, std::size_t n,
                  T rx, T ry, T* z0_out, T* z1_out, T& r_out, bool& finite_out)
void bv_add_2_lanes(..., std::size_t n, std::size_t lanes, T rx, T ry, T* z0_out, T* z1_out, T& r_out, bool& finite_out)
void bv_add_2_packed(..., std::size_t n, T rx, T ry, T* z0_out, T* z1_out, T& r_out, bool& finite_out)
```

`F_seq` loops over the elements: the step, the center written, the record on the state. `F_lanes`
folds each lane from the zero state and combines the lanes from lane 0 upward, then the rest.
`F_packed` computes the packed step and the packed record on $W$ lane states, stores the lane
states and combines them in scalar code from lane 0, then the rest. All three end with a call of
`F_end` (`F_packed_end` in a packed header, which does not include `scalar.hpp`), the radius and the
finish, a function of its own that is never inlined (`KAIRN_GEN_NOINLINE`), and with the second
pass. Inline, compilers duplicated the end into the paths that leave the loop and folded or hoisted
part of a copy (GCC 13 at `-O2` hoisted the product by $\lvert a\rvert$ of `bv_scale_radius_2` and
duplicated the rest; Apple clang at `-O2` folded the product by the $+0$ of the zero state on the
path where the loop runs no element), so that the fused instructions of the function were no number
of whole copies of the parts, which the object-code check refuses; a call is one copy. The largest
magnitude enters the end through a volatile copy, against a clone for the constant $+0$, and the
zeros of the whole space are volatile stores, which no compiler turns into a call of `memset` or
`bzero` (outside the object, which the check also refuses) or vectorizes. Neither computes anything.
Aliasing is a map's: the array written may be exactly one of the arrays read.

**In Rocq.** `FoldModel.v` has `F_step` and `F_map`, the centers, `F_record`, and `F_radius`, the
radius kernel on the limb of `fold_seq F_record (0, true)` over the centers written and on the
scalars. `FoldStatements.v` has `F_spec`: for nonnegative radii and valid centers, the radius is a
number of the format and, entry by entry, the center written is valid and the value of the fold on
any members of the balls of the operands' entries is within the radius of it:

```coq
Definition bv_add_2_spec : Prop :=
  forall emin prec : Z, (3 <= prec)%Z ->
  forall (rx ry : R) (xys : list ((R * R) * (R * R))),
  fmt emin prec rx ->
  0 <= rx ->
  fmt emin prec ry ->
  0 <= ry ->
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\ normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
  let r_ := bv_add_2_radius emin prec tie_even rx ry xys in
  fmt emin prec r_ /\
  Forall2 (fun xy w_ =>
    let '((x0, x1), (y0, y1)) := xy in
    let '(z0, z1) := w_ in
    normalized_2 emin prec z0 z1 /\
    forall x_ y_ : R, Rabs (x_ - (x0 + x1)) <= rx -> Rabs (y_ - (y0 + y1)) <= ry -> Rabs ((x_ + y_) - (z0 + z1)) <= r_)
    xys (bv_add_2_map emin prec tie_even xys).
```

Its proof: the claim `maximum` of the record on each center written (the limb of the final state is
the largest $\lvert z_{i,0}\rvert$), the claim `upper` of the radius kernel, and the error bound of
the step entry by entry (`add_2_2_correct`: $\lvert z - s\rvert \le U\lvert z\rvert$ with
$U = \mathrm{unit}/(1-\mathrm{unit})$, and $\lvert z\rvert \le (1+u)\lvert z_0\rvert$ for a
normalized pair).

`IeeeFoldModel.v` has `F_step`, `F_map`, `F_record`, `F_combine`, and `F_seq` and `F_lanes W`,
which return the centers, the radius and the flag:

```coq
Definition bv_add_2_seq (rx : float) (ry : float) (xys : list ((float * float) * (float * float))) : list (float * float) * float * bool :=
  let ws_ := map bv_add_2_step xys in
  let s_ := fold_seq bv_add_2_record (pzero, true) ws_ in
  let rz_ := IeeeModel.bv_add_radius_2 prec emax nan_plus nan_fma (fst s_) rx ry in
  let f_ := IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz_ (snd s_) in
  (if snd f_ then (ws_, fst f_) else (map (fun _ => (pzero, pzero)) ws_, pinf), snd f_).
```

(`F_lanes W` with `fold_lanes F_record F_combine (pzero, true) W ws_`). `IeeeFoldStatements.v` has
`F_seq_ieee_spec` and `F_lanes_ieee_spec` (every `W`), V1 to V4 of the page and the flag, for
canonical BallVectors (`ball_finite_k` of every center with the radius, a finite nonnegative radius;
or `ball_whole_k` of every center with the radius $+\infty$) and any value of a scalar that is not a
radius, with `(ws_, r_, flag_)` the result:

- **V1** the result is canonical: a finite nonnegative `r_` and every center a finite ball with it,
  or `r_` $= +\infty$ and every center zero;
- the flag: `flag_ = true` exactly when `r_` is finite;
- **V2** entry by entry, for all reals in the balls of the operands' entries (`in_ball_k`, the whole
  line for the whole space), the value of the fold on them is in the ball of the center written
  (`in_ball_k`, for the whole space every real);
- **V3** if `r_` is finite, every scalar is finite, the centers' values are those of the real-model
  step on the values given, and the radius is `FoldModel.F_radius` on the values;
- **V4** if every scalar is finite, the scalars satisfy the conditions of `radii_when`, and every
  entry satisfies the conditions of `finite_when` ($\lvert$EXPR$\rvert \le 2^{e_{\max} + E}$ with
  EXPR over the values of the entry's centers and the scalars, and for `radii_when` over the scalars
  alone), `r_` is finite. It is stated for every length, the empty list included.

V4 has the condition on the radii as a hypothesis of its own, `radii_when`: with no entry the
conditions of `finite_when` say nothing, and a radius computed from radii near the overflow
threshold alone can overflow (`bv_add_radius_k` of two radii of about $\Omega/2$), so the page's V4,
read for $N = 0$ with the entries' conditions alone, would be false. `radii_when` is
$r_x + r_y$ within $2^{e_{\max}-2}$ for `bv_add_k` and `bv_sub_k`, and $\lvert a\rvert r_x$ for
`bv_scale_k`: what the condition of an entry says with its centers zero. At any entry the conditions
of `finite_when` imply it (EXPR of `finite_when` is at least EXPR of `radii_when` in magnitude), so for
a vector with entries V4 is the statement it was, and the hypothesis adds nothing; for the empty
vector it is the whole condition. The first form of V4, of 2026-11-20, assumed the vector not empty
instead.

**What their proofs need**: the theorems of the step (bridge and claims, as for a map), of the
record and the combination (`maximum`, and in the IEEE model that the record keeps a finite state on
a finite center and records a NaN or an infinity), of the radius kernel (`upper`, and in the IEEE
model that a finite radius from finite operands is the real model's), of `norm_finish_1`; for the
lane order, `fold_lanes_aci_step` (the state of the lane order is that of the sequential order); and
for V4, B4 of the entrywise full Ball kernel at the entry of the largest magnitude, whose radius is
the one radius (`ball_add_k_full`, `ball_scale_k_full`: the same lines), and for the empty vector the
same at the magnitude $+0$ of the zero state: the radius kernel on $+0$ and radii within `radii_when`
is finite (each of its roundings is of a nonnegative value at most a few units above $2^{e_{\max}-2}$).

**`bv_norm_upper_k`** ([BallVector](design/milestone2.md#ballvector)), an upper bound of the largest
magnitude of any member of a BallVector $X$ of centers $c_i$ and radius $r$, needs no kernel and no
fold of its own: it is two calls that exist, and the header of `BallVector` writes it as

```
(n, ok) = norm_upper_k(c)                 the fold of maxima on the centers, stored and canonical
b       = ok ? add_up_1(n, r) : +infinity
```

(`include/kairn/ball_vector.hpp` calls `add_up_1` through its entry form `add_up_entry`, the public
`add_up` of `blocks.hpp`: a public header calls only entry kernels, and the guard of each operand is
the identity on its value.)

What is claimed, and by what: `norm_upper_k` claims `upper n max steps=S` with its flag
([Folds of maxima](#folds-of-maxima)): when `ok` is true, $V \le n \le \mathrm{RU}(V)$ stepped up $S$
times, $V = \max_i \lvert c_i\rvert$ ($S = 0$ for one limb, $1$ for two); `add_up_1` claims `rounded b
up` of $n + r$ in the extended domain (the sum of a finite $n$ and $r = +\infty$, the whole space, is
$+\infty$). Every member $x$ of entry $i$ has $\lvert x\rvert \le \lvert c_i\rvert + r \le V + r \le n
+ r \le b$: so $b$ is an upper bound of every member, and $b \le \mathrm{RU}(\mathrm{RU}(V)\uparrow^S +
r)$, at most one rounding up and $S$ steps above the smallest. The inequality chain is the header's
argument from the two claims, not a claim of one kernel; the test of the composition is
`test_bv.Interp.test_the_norm_of_a_ball_vector`, in exact arithmetic. `ok` is false for a vector of
finite centers only when the step up from the largest leading limb is $+\infty$ (two limbs, a leading
limb of magnitude $\Omega$): there the bound is $+\infty$, which bounds everything. For the whole space
$n$ is $0$ (one limb) or $\eta$ (two) and $b = +\infty$. `norm_upper_k` alone bounds the magnitudes of
the centers, not of the members.

**The constructor**, `bv_make_1` and `bv_make_2` (the page says what a constructor returns and gives no
listing: "a constructor given a radius that is negative or a NaN, or a center that is not finite,
returns the whole space"), is a ball vector of the same kind, first proposed in
`experiments/milestone2/kernels/` and checked there by `ballvector.py`, which now runs the generated
descriptions:

```
fold:          bv_make_1
arrays:        supplied c
scalars:       supplied r
state:         m, mask ok
step:          z = bv_center_entry_1(c)          z = guard(c)
record:        (m, ok) = norm_step_1(m, ok, z)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
radius:        rz = bv_make_radius(m, r)         g = guard(r); d = sub(m, m); rz = add(g, d)
finish:        (rr, finite) = bv_make_finish(rz, ok)
                                                 p = le(0, rz); q = and(ok, p); (r, flag) = norm_finish_1(rz, q)
orders:        sequential, lanes
writes:        z
output:        rr
output:        mask finite
value:         c
ensures:       makes_ball_vector z rr from=c,r flag=finite
```

The centers and the radius come from the program (rule R3), so the step and the radius guard them;
`bv_make_2` takes its centers as `Expansion<T, 2>`, canonical and stored, and copies them
(`bv_center_2`, the claims of `neg_2` with the value `x`), and requires `canonical c`. A center that is
not finite makes `m` infinite or the mask false; `m - m` carries an infinite `m` into the radius as a
NaN; and the finish tests, besides the mask and the finiteness of the radius, its sign: `le(0, rz)` is
false for a negative radius and for a NaN, true for either zero. That is the one thing a finish of the
other ball vectors does not do (their radii are nonnegative by construction), and its claim is
`finite_or_nan` with the field `nonneg` ([Claims of Milestone 2](#claims-of-milestone-2)). A radius of
$+\infty$ is not finite: the whole space. The rules of a ball vector apply, with these differences
(`rules._bv_make_claims`): one array and one scalar of one limb, supplied, the radius; the value the
array's name; `canonical` of the centers for two limbs and nothing for one; the radius kernel requires
nothing and takes `(m, r)`; the finish claims `nonneg` (and a finish that claims it is refused in any
other ball vector); the one claim is `makes_ball_vector`. Centers given as two arrays of limbs of the
program's own, which need not be normalized, are not covered: their step would be `make_2_limbs`, which
has no real-model statement.

In Rocq the model is that of every ball vector. `FoldStatements.v` has `F_spec`: for a radius and
centers that are numbers of the format (normalized pairs for two limbs), `F_radius r cs = r` and the
centers written are those given, `Forall2 (fun c w_ => w_ = c) cs (F_map cs)`. `IeeeFoldStatements.v`
has `F_seq_ieee_spec` and `F_lanes_ieee_spec`, for any radius and any centers (canonical pairs for two
limbs): the result is canonical (V1); `flag_ = true` exactly when `r_` is finite; `flag_ = true` exactly
when `finite r /\ 0 <= val r` and the leading limb of every center is finite; and then the values of
the centers written are those given, limb for limb, and `val r_ = val r`:

```coq
  let '(ws_, r_, flag_) := IeeeFoldModel.bv_make_2_seq prec emax ... r cs in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  (flag_ = true <-> finite r_) /\
  (flag_ = true <-> finite r /\ 0 <= val r /\ Forall (fun c => finite (fst c)) cs) /\
  Forall2 (fun c w_ =>
    let '(c0, c1) := c in
    let '(z0, z1) := w_ in
    flag_ = true -> val z0 = val c0 /\ val z1 = val c1) cs ws_ /\
  (flag_ = true -> val r_ = val r).
```

Their proofs need: the claims of the step (a guard is the value; a copy is the pair), of the record
and the combination (as for every ball vector), of `bv_make_radius` in the IEEE model ($m - m$ is $+0$
for a finite $m$ and a NaN otherwise, and the guarded radius plus $+0$ is the radius, a $-0$ made
$+0$), and of `bv_make_finish` (`finite_or_nan` with `nonneg`).

**The negation**, `bv_neg_1` and `bv_neg_2`, is a ball vector of the same kind: the step `neg_1`
(`z = neg(x)`, value `-x`, `rounded z nearest`) or `neg_2`, the radius kernel `bv_neg_radius`
(`rz = copy(rx)`, value `rx`, `m` unused), the finish `norm_finish_1`. It is exact, which its claim
says with the word `exact` (`"exact_when": []`, [below](#claims-of-milestone-2)): the result is exactly
the set of the negated members, entry by entry. Its `finite_when` is `abs_le(abs(x)+rx,1)` and its
`radii_when` `abs_le(rx,1)`, which every finite operand satisfies ($\lvert x\rvert + r_x \le 2\Omega
< 2^{q_{\max} + p + 1}$): a finite operand gives a finite result. The statements of an exact ball
vector have one more conjunct: in the real model, entry by entry, every real within `r_` of the center
written is the set's value at some members of the operands' balls (`exists x_ : R, Rabs (x_ - (x0 +
x1)) <= rx /\ v_ = (- x_)`); in the IEEE model the same under `finite r_`, with `in_ball_k`.

**The scaling by a power of two**, `bv_mul_pow2_1` and `bv_mul_pow2_2`
([milestone2.md, "BallVector"](design/milestone2.md#ballvector), `bv_mul_pow2_k`; [Scaling a ball by a
power of two](design/milestone2.md#scaling-a-ball-by-a-power-of-two)), is exact when nothing underflows,
so that a polynomial halved again and again (subdivision by de Casteljau) keeps its radius $r/2^i$
exactly. Its radius needs the exactness of every entry ("with `ec` over all entries"), which the centers
written cannot tell (a second limb scaled to zero leaves a pair that looks exact), so the ball vector
has, **as the one extension of the shape**, a mask of exactness: a third group of the state, a mask from
true; a step that returns the center and a mask; a second record line and a second combine line, the
`and` of that mask into the state and of two such states, as a map's mask; and a radius kernel that
takes the state's mask after its limb. `bv_mul_pow2_2` in full:

```
fold:          bv_mul_pow2_2
arrays:        stored x = x0 x1
scalars:       stored rx, supplied c
state:         m, mask ok, mask ex
step:          (z, e) = bv_mul_pow2_step_2(x, c)
record:        (m, ok) = norm_step_2(m, ok, z)
record:        ex = and(ex, e)
combine:       (m, ok) = norm_combine(m, ok, m, ok)
combine:       ex = and(ex, ex)
radius:        rz = bv_mul_pow2_radius(m, ex, rx, c)
finish:        (r, finite) = norm_finish_1(rz, ok)
orders:        sequential, lanes
writes:        z = z0 z1
output:        r
output:        mask finite
value:         x*c
requires:      ball_vector x rx
requires:      power_of_two c
ensures:       encloses_entries z r x*c x=x,rx flag=finite finite_when=abs_le((abs(x)+rx)*c,-2) radii_when=abs_le(rx*c,-2) exact_when=zero_or_abs_gt(x[0]*c,eta/(2*u));zero_or_abs_gt(x[1]*c,eta/(2*u));zero_or_abs_gt(rx*c,eta/(2*u))
min_precision: 2
theorem:       proofs/theories/BvPow2.v
ieee_theorem:  proofs/theories/IeeeBvPow2.v
status:        proved
domain:        extended
```

- **The step** `bv_mul_pow2_step_2` is `ball_mul_pow2_2` without its radius: the center as `mul_pow2_2`
  scales it ($h = c\,x_0$, $l = c\,x_1$, `fast_two_sum`), and the mask `ec` of that kernel, `e`: the
  scaled last nonzero limb above the smallest normal number $N = \eta/(2u)$ in magnitude, or the center
  zero. `bv_mul_pow2_step_1` is `z = prod(x, c)` with `e` the same test of `z`. Each claims what the
  step of the map `mul_pow2_map_k` claims (`normalized`, or `rounded z nearest`, and the error of
  `mul_pow2_2`, $\eta$ for two limbs and $\tfrac12\eta$ for one), with `exact_when` the conditions of
  `ball_mul_pow2_k` on the center (each limb times $c$ zero or above $N$: `zero_or_abs_gt(x[0]*c,
  eta/(2*u))` and the same of `x[1]`, or of `x` for one limb), and **`exact_flag=e`**: the mask is true
  exactly when those conditions hold ([below](#claims-of-milestone-2)). That is true because a product
  by a power of two above $N$ in magnitude is a number of the format, so its rounding is above $N$
  exactly when the product is; for two limbs, a nonzero second limb of a normalized pair makes the first
  nonzero and larger. The steps have `ieee: spec` (their claims for finite operands) and no bridge,
  which a kernel with a mask output or a constant operand cannot have (`ieee.program`).
- **The record** of `m, ok` is that of every ball vector (`norm_step_k` on the center written); the
  second, `ex = and(ex, e)`, ands the step's mask into the state; the combination of the lanes ands two
  of them. So the final `ex` is true exactly when every entry's mask is, in every order.
- **The radius** `bv_mul_pow2_radius(m, ex, rx, c)` is the radius lines of `ball_mul_pow2_k` with `ex` in
  place of one entry's `ec`: `rr = prod(rx, c)`; `er` its exactness, $c\,r_x$ zero or above $N$; `rs =
  select(and(ex, er), rr, succ(succ(rr)))`; and `rz = add(rs, sub(m, m))`. The radius does not grow
  with the centers, so the largest magnitude enters only as $m - m$, $+0$ for a finite $m$ and a NaN for
  an infinite one (a center that overflowed), which the addition carries into the radius and the finish
  tests (`bv_make_radius` does the same). Its claims are two entries `upper` of new forms
  ([below](#claims-of-milestone-2)): `upper rz value=rx*c exact_when=mask(ex);zero_or_abs_gt(rx*c,
  eta/(2*u))`, at least $c\,r_x$, and exactly $c\,r_x$ when `ex` is true and $c\,r_x$ is zero or above
  $N$; and `upper rz value=rx*c+eta unless=ex`, at least $c\,r_x + \eta$ when `ex` is false. The second
  number after $\mathrm{RN}(c\,r_x)$ is above $c\,r_x + \eta$: the number after $\mathrm{RN}(y)$ is above
  $y$ for every $y \ge 0$, and the next adds at least $\eta$.
- **The claim** is `encloses_entries` with `exact_when` and conditions: when the result is a finite ball
  vector, the scalars satisfy the conditions that name only scalars ($c\,r_x$ zero or above $N$) and every
  entry those that name an array, the result is exactly the set, $c\,X$ itself: each center $c\,x_i$
  and the radius $c\,r_x$. The rules (`rules._bv_exact`) require that the conditions of an entry are,
  renamed to what the fold passes, those of the `exact_when` of the step's error entry whose
  `exact_flag` is the step's mask, and the conditions of the scalars those of the radius kernel's
  `upper` entry whose `exact_when` holds `mask(EX)` of its mask input. `finite_when` and `radii_when` are
  those of `ball_mul_pow2_k_full` (B4) and of `bv_scale_k`: $(\lvert x\rvert + r_x)\,c$ and $r_x\,c$
  within $2^{e_{\max}-2}$.
- **Against `ball_mul_pow2_k`**, the page's "equal: $c\,r_x$ when every entry is exact": with at least one
  entry, the one radius *is* the largest of the radii that `ball_mul_pow2_k` returns entry by entry,
  because that kernel's radius is `select(and(ec, er), rr, succ(succ(rr)))` of the same `rr`, and the
  second arm is the larger; the largest over the entries is `rr` exactly when every `ec` is true, which is
  `ex`. What is **claimed** of it is the equality where the page states one, $c\,r_x$ when every entry
  and the radius satisfy the conditions (the exactness of the result), and the upper bounds of the radius
  kernel; the equality with the entrywise radii in the other case is what the listing computes and what
  `test_bv.py` finds in every case it compares, not a claim (no claim names another kernel's
  computation, as for `bv_add_k`).

In C++ the state's mask `ex` is a `bool` (a lane mask in packed code) declared after `ok`, and-ed after
the record (`ex = ex & step_e;`), and-ed in the combination of the lanes, passed to `F_end` after `ok`
and to the radius after the largest magnitude. In Rocq the model keeps the state of the fold of maxima
as it is for every ball vector and computes the mask apart, as a map's: `FoldModel.F_exact c xs`, the
`forallb` of the step's masks, is the radius kernel's second argument in `F_radius`; `F_step` returns the
center and the mask, and `F_map` the centers (`map (fun x => fst (F_step c x)) xs`). In `IeeeFoldModel.v`,
`F_seq` and `F_lanes W` compute `es_ := map F_step xs`, `ws_ := map fst es_`, the state of `m, ok` on
`ws_` as for every ball vector, and `ex_ := fold_seq (fun m_ e_ => andb m_ (snd e_)) true es_` (in the
lane order `fold_lanes (...) andb true W es_`, the form of a map's mask), which the radius takes. Their
statements: the real model's `F_spec` has, after containment entry by entry, the conjunct of exactness
under the conditions (the conditions of the scalars, then those of an entry at every entry, `Forall`, then
for every entry every real within `r_` of the center written is $c\,x$ for some member $x$ of the ball);
the IEEE model's has the same under `finite r_` with `in_ball_k`, the requirement `finite c /\ (exists n :
Z, val c = bpow radix2 n)` of the power of two, and in V3 the center the first component of the real
model's step (`fst (bv_mul_pow2_step_2 ...)`). The line protocol is that of every ball vector:
`bv_mul_pow2_2 binary64 seq 2 0x1p-4 0x1p-1 0x1p+0 0x1p+1 0x1p-60 0x0p+0` ($r_x = \tfrac1{16}$, $c =
\tfrac12$, $x = (1, 2^{-60}), (2, 0)$) is completed with ` -> 0x1p-1 0x1p+0 0x1p-61 0x0p+0 0x1p-5 1`,
the radius exactly $\tfrac1{32}$.

**What their proofs need** besides those of every ball vector: of the step, its claims in both models
(the error of `mul_pow2_2`, `mul_pow2_2_exact` under the conditions, and that the mask is true exactly
when they hold: `round_abs_le`, a rounded product above $N$ comes from an exact product above $N$, and
`normalized_2_tail_rel` for two limbs), and in the IEEE model a lemma in place of the bridge it cannot
have (a finite center from finite operands is the real model's, center and mask); of the radius, its two
`upper` entries (`up_above` of `Directed.v` and the smallest gap $\eta$, as for `ball_mul_pow2_k`) and in
the IEEE model that a finite radius from finite operands is the real model's ($m - m$ is $+0$ for a
finite $m$); `fold_seq_and` and `fold_lanes_and` (`Folds.v`) for the mask; and for exactness, that the
conditions of every entry make `ex` true (the step's `exact_flag`), hence the radius $c\,r_x$, and every
center $c\,x_i$ (the step's `exact_when`), so that the ball of each center written is $c$ times the ball
of the operand's.

**The product of polynomials**, `bv_conv_1` and `bv_conv_2` ([milestone2.md, "The product of
polynomials"](design/milestone2.md#the-product-of-polynomials): `bv_conv_k` with `conv_radius`), first
proposed in `experiments/milestone2/kernels/` and checked there by `bv_conv.py`, which now runs the
generated descriptions. It is a fold of a kind of its own, *the product of two BallVectors*: the
convolution of the centers, named and not described again, with what a ball vector adds to it.
`bv_conv_2` in full:

```
fold:          bv_conv_2
arrays:        stored x = x0 x1, stored y = y0 y1
scalars:       stored rx, stored ry
centers:       conv_2
state:         ma, mask oka, mb, mask okb
record:        (ma, oka) = norm_step_2(ma, oka, x)
record:        (mb, okb) = norm_step_2(mb, okb, y)
count:         m = min(n_x, n_y)
bound:         (g, t, okg) = bound_dot_2(m)
radius:        rz = conv_radius(ma, mb, rx, ry, m, g, t)
finish:        (r, flag) = bv_conv_finish(rz, finite, okg)
orders:        sequential
writes:        z = z0 z1
output:        r
output:        mask flag
value:         x*y
requires:      ball_vector x rx
requires:      ball_vector y ry
ensures:       encloses_coefficients z r x*y x=x,rx y=y,ry flag=flag finite_when=abs_le(n*(abs(x)+rx)*(abs(y)+ry),-2);abs_le((abs(x)+rx)*ry,-2);abs_le((abs(y)+ry)*rx,-2) radii_when=abs_le(rx*ry,-2) count_when=le(n*(unit(mul_2_2)+eta/(2*u)),1/16)
min_precision: 4
theorem:       proofs/theories/BvConv.v
ieee_theorem:  proofs/theories/IeeeBvConvFinite2.v
status:        proved
domain:        extended
```

- **The centers** are the coefficients of the convolution `centers:` (`conv_2`, `conv_1` for one limb),
  its arrays and its array written (names and limbs), its mask `finite` included: coefficient $j$ is
  `dot_k` in its sequential order on the terms $(x_i, y_{j-i})$. The arrays are `stored` (centers of
  BallVectors), where the convolution's are `supplied` (rule R3 asks nothing of a stored array).
- **The records**, one per array read, in the order of the arrays: the step of a fold of maxima on the
  entries of that array (`norm_step_k`), from $(+0, \text{true})$; $M_a$ = `ma` and $M_b$ = `mb` are the
  largest magnitudes of the leading limbs of the operands' centers. These are maxima of what is read,
  not of what is written. (`oka` and `okb` are carried, as in every fold of maxima, and used by nothing
  else: a canonical BallVector has no NaN center.)
- **The count** `m = min(n_x, n_y)`, the largest number of terms of a coefficient (`conv_terms_length`),
  is a number of `T` rounded up: $n$ itself below $2^p$, otherwise the smallest number of `T` above it
  (`interp.count_up`; in C++ the conversion of the integer, then one step up when it is below $n$,
  compared as integers below $2^{64}$).
- **The bound** is one call of `bound_dot_k(m)`, `(g, t, okg)`, whose bound covers every coefficient (each
  has at most $m$ terms). The rules check that it covers the dot product of the coefficients:
  `unit(K)` and `tiny(K)` of its claims are at least the `term` (or `eps`) and `tau` of that fold's
  `fold_error`, in `binary64` and `binary32` (its $g$ and $t$ grow with both; `bound_dot_k` has exactly
  those of `dot_k`, and `bound_dot_1` for the coefficients of `dot_2`, or `bound_dot_2` for those of
  `dot_1`, is refused).
- **The radius** is the page's `conv_radius(ma, mb, rx, ry, m, g, t)` (`gen/kernels/conv_radius.kernel`,
  the listing of the page): $r_z \ge m\bigl((1+u)M_a r_y + (1+u)M_b r_x + r_x r_y\bigr) + g\,m\,(1+u)^2 M_a
  M_b + t$, claimed as `upper rz value=...`, with the requirements that every input is nonnegative,
  `count m`, and the new requirement **`at_most(g, 1)`** (below), from precision 2 (below it the
  constant of `hm` is above the largest number of formats of few exponents). The claim is of finite
  results (the ruling of 2026-11-21, [Claims of the non-finite
  layer](#claims-of-the-non-finite-layer)): a radius that is not finite is $+\infty$ or a NaN, never
  a negative number or $-\infty$, and the finish below turns it into the whole space.
- **The finish** `bv_conv_finish(rz, finite, okg)` is `norm_finish_1` under the `and` of the
  convolution's mask and the bound's: the radius, with the flag true, when every coefficient is finite,
  the bound is given and the radius is finite; it claims `finite_or_nan r flag=flag if_all=finite,okg`
  (below). **When the flag is false** every coefficient written is zero and the radius $+\infty$: the
  whole space. An operand that is the whole space, a bound not given (the count too large for the
  format), or an overflow anywhere, give the whole space.

**What the generator checks of it** (`rules.bv_conv_rules`), besides the names: the convolution named is
one; no step, coefficients, check or combination of its own; the order `sequential`; the arrays those
of the convolution, stored; the array written the convolution's; the state two folds of maxima, one per
array, each record the step of a fold of maxima of an array of that array's shape, the same step for
both (the models have one `F_record`; with arrays of one shape there is one such step today); the count, the
bound's destinations and the radius's of names of their own; the bound a kernel of the count (required
`count`) to two limbs and a mask, covering the coefficients' dot product; the radius on the
maxima, the radii, the count and the bound's two limbs, to one limb, with a real-model statement;
each scalar a stored radius of one limb that the radius takes; the finish on the radius, the
convolution's mask and the bound's, claiming `finite_or_nan` under both (`if_all`); rule R3 on the
radius; the claim below; the extended domain; the minimum precision, at least that of the convolution
and of every part.

**The claim**, `encloses_coefficients` ([below](#claims-of-milestone-2)): V1 (canonical, $n_x + n_y - 1$
coefficients, none when a length is $0$), the flag, V2 coefficient by coefficient for the set $\sum_i
x_i y_{j-i}$ with every $x_i$ and $y_k$ ranging independently over its ball (each entry appears once in
a coefficient, so the exact range of the sum is the sum of the ranges of the products), V3 (a finite
result has finite radii, the convolution's coefficients and the radius kernel's radius on the values),
and **V4**, which the page left to the proof and which is now, exactly: *if both operands are finite
ball vectors, $n\,(\mathrm{unit}(K) + \eta/(2u)) \le \tfrac1{16}$ for `bv_conv_2` and $n\,(\mathrm{unit}(K)
+ \eta) \le \tfrac1{16}$ for `bv_conv_1`, with $n = \min(n_x, n_y)$ and $K$ the products' kernel (`mul_2_2`,
`mul_1_1`), $r_x r_y \le 2^{e_{\max}-2}$, every entry $x_i$ has $(\lvert
x_i\rvert + r_x)\,r_y \le 2^{e_{\max}-2}$, every entry $y_k$ has $(\lvert y_k\rvert + r_y)\,r_x \le
2^{e_{\max}-2}$, and every pair has $n\,(\lvert x_i\rvert + r_x)(\lvert y_k\rvert + r_y) \le
2^{e_{\max}-2}$, then the result is a finite ball vector.* The condition of the pairs is the bound of the
radius and of the coefficients: every value `conv_radius` and the dot products compute is at most
$(1+u)^{14}(1+2u)(1-u)^{-2}\,n\,A\,B$, with $A$ and $B$ the largest $\lvert x_i\rvert + r_x$ and $\lvert
y_k\rvert + r_y$, which is below $0.75 \cdot 2^{e_{\max}}$ from $p = 4$ (hence the minimum precision 4
of both folds; at $p = 3$ the factor is 6.5 and $2^{e_{\max}-2}$ would not do). The conditions of each
array alone are what an empty operand needs: with $n_x = 0$ there is no coefficient and no pair, $m =
0$, and yet `conv_radius` computes $M_b r_x + r_x r_y$ before multiplying it by $m$, and $0 \cdot
\infty$ is a NaN: `test_bv_conv.Interp.test_an_empty_operand_with_a_large_radius` runs that case
($n_x = 0$, $y_0 = r_x = 2^{600}$ in `binary64`: the whole space, and the condition $(\lvert y\rvert +
r_y)\,r_x$ not met). The radii's own condition is the case of two empty operands. With both operands not
empty the condition of the pairs implies the others, as `finite_when` implies `radii_when` for every
ball vector. The condition on the count is the bound's: `bound_dot_k(m)` refuses a count beyond about
$\tfrac14 / \mathrm{unit}(K)$ (in formats of few bits, a few terms), and then the result is the whole
space whatever the values; the condition makes it given in every format from $p = 4$, and it makes the
count a number of the format. That second part is why `bv_conv_2` has the smallest normal number
$\eta/(2u) = 2^{2 - e_{\max}}$ where `bv_conv_1` has $\eta$: the count is $m$, $n$ rounded up, and when $n$
is above the largest number $m$ is $+\infty$, `bound_dot_k(+\infty)` is not given, and the product is the
whole space. $n\,\eta/(2u) \le \tfrac1{16}$ bounds $n$ by $2^{e_{\max} - 6}$ whatever the precision. With
$\eta$ in its place, as first stated, $n\,(4u^2 + \eta) \le \tfrac1{16}$ bounds $n$ by about $\min(2^{2p-6},
2^{e_{\max}+p-7})$, which is above the largest number in every format with $p \ge 8$ and $p < e_{\max} \le
2p - 7$: there finite operands meeting every condition gave the whole space ($p = 8$, $e_{\max} = 9$, both
operands 511 entries $(+0, +0)$ with radii $+0$; `test_bv_conv.Interp.test_the_count_overflowed`), and V4
was false. In `binary32` and `binary64` the two forms admit the same counts, up to $2^{42} - 1$ and $2^{100}
- 1$ (the $4u^2$ is what bounds them). For `bv_conv_1` the term $u/(1+u)$ already bounds $n$ by about
$2^{p-4}$, a number of the format, and $\eta$ is kept. `test_bv_conv.Interp.test_the_count_gives_the_bound`
checks, for every $n$ the condition admits (up to 3 000 of them and the largest), that the count rounded up
is finite and `ok` true, in 36 formats of precisions 4 to 9 with room above (the $\eta$ covers formats whose
$\eta$ is not small against $\mathrm{unit}(K)$) and in formats of the IEEE shape of precisions 4 to 12, each
with its smallest exponent range and, from $p = 8$ on, those with $e_{\max} \le 2p - 7$, where it checks
too that the first form admitted a count whose rounding up overflows. How it was checked: in exact arithmetic on the interpreter, at random
(`test_v1_to_v4`) and on cases aimed at the limits of the conditions, a quarter with $n_x = 0$ and a
quarter with $n_y = 0$ (`test_v4_at_its_limits`), in six formats of the IEEE shape of four to six bits
and in `binary64` and `binary32`, with no failure; and the compiled code computes what the interpreter
computes on the same corpus, bit for bit (`test_bv_conv.Cxx`), cases near the limits among them. The
first experiments put the fraction at $2^{e_{\max}-1}$ without a failure, but the bound above does not
reach it at $p = 4$, so $-2$ is what is stated.

**In C++** one function per limb type, with each array's length after its limb pointers and the radii
after the arrays, as a convolution's with the radius and the flag of a ball vector:

```
void bv_conv_2_seq(const T* x0_in, const T* x1_in, std::size_t n_x, const T* y0_in, const T* y1_in,
                   std::size_t n_y, T rx, T ry, T* z0_out, T* z1_out, T& r_out, bool& flag_out)
```

Two loops, the maxima of each operand's centers; the loop of `conv_seq` (its mask, not its second
pass); then a call of `bv_conv_2_end(ma, mb, min(n_x, n_y), finite, rx, ry, ...)`, never inlined as
every end of a ball vector, which computes the count, the bound, the radius and the finish (the maxima
through volatile copies); and the zeros of the whole space as volatile stores. No packed form: that of
a convolution has none. Aliasing: a convolution's, the array written overlaps neither array read.

**In Rocq**, `FoldModel.v` has `F_record`, `F_count` (`round radix2 (FLT_exp emin prec) Zceil (INR
(Nat.min (length xs) (length ys)))`), `F_bound`, `F_ok` (the bound's mask) and `F_radius`; the
coefficients are `F_conv` of the convolution named. `FoldStatements.v` has `F_spec`: for nonnegative
radii, valid centers, a format that contains $\tfrac12$ and the bound given (`F_ok xs ys = true`), the
radius is a number of the format, every coefficient is valid, and for all lists of members `xs_`,
`ys_` within the radii of the centers, entry by entry (`Forall2`), coefficient $j$ of their exact
product, `sumR (map (fun xy => fst xy * snd xy) (conv_terms xs_ ys_ j))`, is within `r_` of coefficient
$j$ written. `IeeeFoldModel.v` has `F_record`, `F_count` (`binary_normalize ... BinarySingleNaN.mode_UP
(Z.of_nat (Nat.min (length xs) (length ys))) 0 false`, the count rounded up) and `F_conv rx ry xs ys`,
which returns the coefficients, the radius and the flag, the code above; `IeeeFoldStatements.v` has
`F_ieee_spec`, V1 to V4 and the flag as above, with `in_ball_k` for the members and the whole space, and
the length of the coefficients `FoldModel.conv_length`. **What their proofs need**: the theorems of the
convolution (`conv_k_spec` and `conv_k_ieee_spec`), of the records (`maximum`, and in the IEEE model
that the record keeps a finite state on a finite center), of `bound_dot_k` (its claims, and that its
`ok` true gives $g \le 1$, the requirement `at_most` of `conv_radius`: a lemma by unfolding its listing,
`ob = le(g, 1)`), of `conv_radius` (`upper`, and in the IEEE model that a finite radius from finite
operands is the real model's), of `bv_conv_finish`; `conv_terms_Forall` and `conv_terms_length`, and the
containment of a sum of products of independent members (each $\lvert x_i y_{j-i} - c_{x,i} c_{y,j-i}
\rvert \le \lvert c_{x,i}\rvert r_y + \lvert c_{y,j-i}\rvert r_x + r_x r_y$, summed over at most $m$ terms,
with $\lvert c\rvert \le (1+u)\lvert c_0\rvert \le (1+u)M$ for a normalized pair); for V4, the bound of
the values above, and that `count_when` makes the bound given.

The line protocol is a convolution's with the two radii between the lengths and the arrays:
`bv_conv_K FORMAT seq N_X N_Y RX RY LIMB...`, completed with the $N_Z$ coefficients (limb array after
limb array), the radius and the flag ([The line protocol](#the-line-protocol)).

**Not yet generated: a proposal.** One kernel of the page is not generated (`experiments/milestone2/
kernels/`, checked there): `bv_axpy_k` (`bv_axpy_2.fold`, `bv_axpy_step_k`, `bv_axpy_radius_k`;
`bv_proposals.py`), whose radius $\mathrm{bv\_add\_radius}_k(M, \mathrm{bv\_scale\_radius}_k(M', r_x, a),
r_y)$ needs a second maximum, of the scaled centers. See [`axpy` of ball vectors](#axpy-of-ball-vectors),
below.

#### axpy of ball vectors

**`bv_axpy_k(a, X, Y)` $= aX + Y$ is the composition** of two ball vectors that are generated: the
public header of `BallVector` calls `bv_scale_k(X, a)`, then `bv_add_k` of what it
wrote and $Y$, in place (the centers written may be exactly one of the arrays read, [Maps](#maps)): the
scaled centers into the array of the result, then their sum with $Y$ into that same array, or into the
array of $Y$ when $Y$ is the one to overwrite. No kernel of the generator is `axpy` of ball vectors.

*As built (2026-11-22).* The header writes the scaled centers into the array of the result, which
may be the array of $X$ and must not be that of $Y$: the scaling would overwrite $Y$ before the sum
reads it, and the two loops would return a finite ball vector around $2aX$, which does not contain
$aX + Y$. The header tells that case by one comparison of pointers, in every build: a debug build
reports it, and the result is the whole space, from the constructor's loop with a radius of
$+\infty$. Until 2026-11-22 a build without the checks returned the wrong finite ball vector, where
the same call of the functions on arrays, `axpy(a, x, y, y)`, is the documented in-place form: an
audit found it. Writing $aX + Y$ into $Y$ is what the one-pass kernel below would allow.

**What is claimed of it** is the two kernels' claims, composed, and nothing of its own: $S$ =
`bv_scale_k(X, a)` (`encloses_entries` of `x*a`: V1 to V4 with `finite_when=abs_le((abs(x)+rx)*a,-2)`
and `radii_when=abs_le(rx*a,-2)`), then $Z$ = `bv_add_k(S, Y)` (`encloses_entries` of `x+y`, its V4 with
`abs(x+y)+rx+ry` and `rx+ry` within $2^{e_{\max}-2}$, read on the values of $S$ and its radius). V2
composes: for $x$ in the ball of entry $i$ of $X$ and $y$ in that of $Y$, $a x$ is in the ball of entry
$i$ of $S$, so $a x + y$ is in the ball of entry $i$ of $Z$. V1 and the flag are $Z$'s; the whole space
propagates (an operand of `bv_add_k` that is the whole space gives the whole space). V3: a finite $Z$
has a finite $S$, so finite $X$, $Y$ and $a$. V4 is that of each call in turn, the second on the
computed $S$: it is not stated once of $X$, $Y$ and $a$; `bv_proposals.py` finds that
$(\lvert x\rvert + r_x)\lvert a\rvert \le 2^{e_{\max}-2}$ and $\lvert a x + y\rvert + \lvert a\rvert r_x +
r_y \le 2^{e_{\max}-3}$ at every entry, with the radii's conditions, give a finite result, on every case it
runs. The radius is at least the largest of the entrywise radii of `ball_add_k(ball_scale_k(x_i, r_x, a),
y_i, r_y)`, and equal to it when one entry has both maxima, of the scaled centers and of the results
(the page's "at least the largest; equal when one entry has both maxima"), tested by `bv_proposals.py`,
not claimed.

**What the one-pass kernel would add**: one pass over memory in place of two (it reads $X$ and $Y$
once and writes $Z$ once; the composition reads $X$, writes $S$, reads $S$ and $Y$ and writes $Z$), and
no temporary array when neither $X$ nor $Y$ may be overwritten. Its results are those of the
composition, bit for bit: the centers, the radius and the flag, in every case `bv_proposals.py` runs (1 500
per toy format, 400 in `binary64` and `binary32`, lengths 0 to 5, the whole space and non-finite `a`
among them), because its radius is `bv_add_radius_k` of the largest result and of `bv_scale_radius_k` of
the largest scaled center, which is what the second call computes from the first's radius. What it needs
of the generator, and what the extension of `bv_mul_pow2_k` (a mask and-ed into the state) does not give:
a second fold of maxima in the state, of a second *limb* output of the step (the scaled center), its
record and its combination (`norm_step_k`, `norm_combine` again), and a radius kernel on two maxima. That
is not done: the composition computes the same.

### The accumulator

`Accumulator<T, k>` ([milestone2.md, "The accumulator"](design/milestone2.md#the-accumulator)) is
the state of `sum_k` and `dot_k` given to the program: the running k-number $s$, the running sum
$a$ in `T` of the magnitudes of the leading limbs of what was added, and the count $n$. Its
operations are straight-line kernels on that state, passed in and returned; no kernel is a fold.
The count is not a limb of any kernel: it is an integer of the header (`std::size_t`), exact where
a count in `T` would round past $2^p$, added on a merge, and converted to `T` only for
`bound_dot_k(n)` and `acc_radius_k`, which require a count of `T`.

| Kernel | Inputs | Outputs | Listing |
|---|---|---|---|
| `acc_add_k` | `s`, `a`, `x` (supplied) | `t`, `b` | `add_1_1` (`add_2_2`) on the guarded `x`; `b = add(a, abs(x0))` |
| `acc_mul_k` | `s`, `a`, `x`, `y` (supplied) | `t`, `b` | the step of `dot_k`; `b = fma(abs(x0), abs(y0), a)` |
| `acc_mul_entry_1` | `s`, `a`, `x`, `y` (supplied) | `t`, `b` | `acc_mul_1` on `x` and `y` guarded (R3, the factors of a fused operation): what `add_product` of one limb calls |
| `acc_mul_entry_2` | `s`, `a`, `x`, `y` (supplied) | `t`, `b` | `acc_mul_2` on the limbs of `x` and `y` guarded (the same rule): what `add_product` of two limbs calls |
| `acc_merge_k` | `s`, `a`, `v`, `c` (another accumulator) | `t`, `b` | `add_1_1` (`add_2_2`) of the sums; `b = add(a, c)` |
| `acc_radius_k` | `a`, `m`, `g`, `t` | `r`, mask `ok` | in the form of `conv_radius`; `(g, t) = bound_dot_k(m)` |

**What is claimed of each output, and where.** The requirements: every limb finite, `s`, `x`, `y`,
`v` normalized for two limbs, and `a`, `c` nonnegative (a sum of magnitudes never is negative).

- `t`, the running sum, output limb 0 and the first group: what `add_1_1`, `add_2_2` or the step of
  `dot_k` claims of its result, in the claims file whenever `t`'s leading limb is finite, as for
  every kernel. With one limb `rounded t nearest` (and `error t R`), with two limbs `normalized t`
  and the bound of `add_2_2` or `dot_step_2`.
- `b`, the sum of magnitudes, the second group: `rounded b nearest value=a+abs(x)` (`a+abs(x[0])`,
  `a+abs(x[0])*abs(y[0])`, `a+c`), the rounding to nearest of a value of its own, over the inputs and
  their limbs, rather than of the kernel's value. An entry about an output group other than the
  first holds where that group's leading limb is finite ([below](#claims-of-the-interval-kernels)):
  so in the format itself the claim says nothing of `b` where it is $+\infty$, which happens while
  `t` is finite (`b` does not reach `t`: the kernels are exempt from the non-finite cone).
  `experiments/milestone2/accumulator.py` counts those cases (A4) and checks that `b` is then the
  rounding with overflow.
- `r`, the radius, under the mask: `upper r value=g*(1+u)^2*(1+m*u+2*m^2*u^2)*(a+m*eta/2)+t if=ok`
  and `holds le m*u 1/2 if=ok`. Where `ok` is false nothing is claimed of `r`, and the header
  returns the whole line. `ok` is false when $mu$ may exceed $\tfrac12$ and when `a` is not finite:
  a sum of magnitudes that overflowed, from which no radius may be believed. The test is
  `z = sub(a, a)`, $+0$ for a finite `a` and a NaN otherwise, then `eq(z, z)`, without the constant
  `inf` that the real model does not have. `acc_radius_2` is `acc_radius_1`: the magnitudes are
  summed in `T` for both numbers of limbs, and only the `(g, t)` passed in differ.

The page gives `acc_radius_k` no listing; the one in `gen/kernels/acc_radius_1.kernel` is proposed
and checked in exact arithmetic by `accumulator.py`: the inequality the radius rests on,
$\sum_i\lvert x_i y_i\rvert \le (1+u)^{n+2}(a + \tfrac12 n\eta)$, after random sequences of `add`,
`add_product` and `merge` (A1); the claim of the radius (A2); the chain
$\lvert s - \Sigma\rvert \le g\sum_i\lvert x_i y_i\rvert + t \le r$ with `bound_dot_k` (A3); the mask
false for `a` $= +\infty$ or a NaN (A5).

**In Rocq.** The real-model statements are those of every kernel (`Statements.v`), the claim of `b`
`b = RN emin prec (a + Rabs x0)`. The IEEE-model statements (`ieee: spec`, `K_ieee_spec`) put each
group's claims under the finiteness of its own leading limb:

```coq
  let '(t0, t1, b) := IeeeModel.acc_add_2 prec emax ... s0 s1 a x0 x1 in
  (finite t0 ->
   finite t1 /\
   normalized_2 (ieee_emin prec emax) prec (val t0) (val t1) /\
   Rabs ((val t0 + val t1) - ((val s0 + val s1) + (val x0 + val x1))) <= ...) /\
  (finite b ->
   val b = RN (ieee_emin prec emax) prec (val a + (Rabs (val x0)))).
```

and for `acc_radius_k`, `finite r -> (ok = true -> ... <= val r) /\ (ok = true -> val m * u prec <=
1 / 2)`. A kernel whose claims are all about its first group keeps the statement it had. No
accumulator kernel has a bridge (`ieee: bridge`): the bridge says that a finite output limb 0
means a finite run of the whole program, which `b` breaks.

## Kernels of the first wave

Names of values are normative: the Rocq model, the C++ and the proofs use the same ones. Each
line is one rounding. Sources: [JMP17](design/phase0/references.md#jmp17) for the algorithms,
[MR22](design/phase0/references.md#mr22) for the corrected bounds. "Target" is what Kairn sets
out to prove; nothing here is a guarantee until its proof is checked.

**Error-free transformations.**

```
two_sum(a, b) -> (s, e)                 fast_two_sum(a, b) -> (s, e)      two_prod(a, b) -> (p, e)
  s  = a + b                              s = a + b                         p = prod(a, b)
  bb = s - a                              z = s - a                         e = fms(a, b, p)
  t0 = s - bb                             e = b - z
  t1 = a - t0
  t2 = b - bb
  e  = t1 + t2
```

```
split(a) -> (ah, al)                    two_prod_dekker(a, b) -> (p, e)   (constant-evaluation
  g  = prod(const splitter, a)            (ah, al) = split(a)              variant of two_prod)
  d  = a - g                              (bh, bl) = split(b)
  ah = g + d                              p  = prod(a, b)
  al = a - ah                             q0 = prod(ah, bh)
                                          t1 = q0 - p
                                          q1 = prod(ah, bl)
                                          t2 = t1 + q1
                                          q2 = prod(al, bh)
                                          t3 = t2 + q2
                                          q3 = prod(al, bl)
                                          e  = t3 + q3
```

**Two limbs.** A 2-limb operand `x` is `(x0, x1)`; a one-limb operand is `a`.

```
add_2_2(x, y) -> z      JMP17 Alg. 6        add_2_1(x, a) -> z      JMP17 Alg. 4
  (sh, sl) = two_sum(x0, y0)                  (sh, sl) = two_sum(x0, a)
  (th, tl) = two_sum(x1, y1)                  v        = x1 + sl
  c        = sl + th                          (z0, z1) = fast_two_sum(sh, v)
  (vh, vl) = fast_two_sum(sh, c)
  w        = tl + vl
  (z0, z1) = fast_two_sum(vh, w)

mul_2_2(x, y) -> z      JMP17 Alg. 12       mul_2_1(x, a) -> z      JMP17 Alg. 9
  (ch, cl1) = two_prod(x0, y0)                (ch, cl1) = two_prod(x0, a)
  tl0       = prod(x1, y1)                    cl3       = fma(x1, a, cl1)
  tl1       = fma(x0, y1, tl0)                (z0, z1)  = fast_two_sum(ch, cl3)
  cl2       = fma(x1, y0, tl1)
  cl3       = cl1 + cl2
  (z0, z1)  = fast_two_sum(ch, cl3)

add_fast_2_2(x, y) -> z   JMP17 Alg. 5
  (sh, sl) = two_sum(x0, y0)
  v        = x1 + y1
  w        = sl + v
  (z0, z1) = fast_two_sum(sh, w)
```

| Kernel | Requires | Statement | Holds for | Status |
|---|---|---|---|---|
| `two_sum` | — | $s = \mathrm{RN}(a + b)$ and $s + e = a + b$ | $p \ge 2$ | proved |
| `fast_two_sum` | $\lvert a\rvert \ge \lvert b\rvert$ | the same, and $(s, e)$ is normalized | $p \ge 2$ | proved |
| `two_prod` | — | $p = \mathrm{RN}(ab)$; $\lvert p + e - ab\rvert \le \eta/2$; and $p + e = ab$ when $ab = 0$ or $\lvert ab\rvert \ge 2^{2p-1}\eta$ | $p \ge 2$ | proved |
| `add_2_2` | $x$, $y$ normalized | $z$ normalized; $\lvert z - (x + y)\rvert \le \frac{3u^2}{1 - 4u}\lvert x + y\rvert$ | $p \ge 3$ | proved |
| `add_2_1` | $x$ normalized | $z$ normalized; $\lvert z - (x + a)\rvert \le 2u^2\lvert x + a\rvert$ | $p \ge 3$ | proved |
| `mul_2_2` | $x$, $y$ normalized | $z$ normalized; $\lvert z - xy\rvert \le 4u^2\lvert xy\rvert + \tfrac32\eta$ | $p \ge 4$ | proved |
| `mul_2_1` | $x$ normalized | $z$ normalized; $\lvert z - xa\rvert \le 2u^2\lvert xa\rvert + \eta$ | $p \ge 2$ | proved |
| `split` | — | $a_h + a_l = a$ | $p \ge 4$ | proved |
| `two_prod_dekker` | — | $p = \mathrm{RN}(ab)$; $\lvert p + e - ab\rvert \le \tfrac{13}{8}\eta$; exact under the same condition as `two_prod` | $p \ge 4$ | proved |
| `add_fast_2_2` | $x$, $y$ normalized | $z$ normalized; $\lvert z - (x + y)\rvert \le 3u^2(\lvert x\rvert + \lvert y\rvert)$ | $p \ge 2$ | proved |

"Proved" means: Rocq accepts a proof of the generated statement, and the audit finds only the
four allowed axioms (`make -C proofs`). Every kernel of this table is proved.

All statements are for every format with $p$ at least the minimum shown, for every $q_{\min}$,
with ties to even and gradual underflow, and under the hypothesis that no operation overflows.
The treatment of overflow and of non-finite operands is added on top of these statements, not
inside them ([Milestone 1 statements](design/milestone1.md)).

The two additions carry over from the machine-checked proofs of
[MR22](design/phase0/references.md#mr22), which have no underflow, through one lemma: the sum of
two numbers of the format rounds to the same number with and without gradual underflow. The two
products are new proofs; their underflow terms $\tfrac32\eta$ and $\eta$ are approached, and not
exceeded, by exhaustive runs on toy formats.

Three points that were open are settled by proofs:

- `add_fast_2_2` ends with `fast_two_sum` and its result is normalized, also when the leading
  limbs cancel. Its bound is relative to $\lvert x\rvert + \lvert y\rvert$, not to
  $\lvert x + y\rvert$: use it when the operands have the same sign, or when a bound of that
  form is enough.
- `split` and `two_prod_dekker` are proved from $p = 4$. Enumerating one small format each at
  $p = 2$ and at $p = 3$ finds no failure; those precisions are not proved and not claimed. In
  this model no
  operation overflows, so they have no requirement here; the conditions under which their
  product by the splitter does not overflow belong to the layer described next.
- The underflow term of `two_prod_dekker` is $\tfrac{13}{8}\eta$, below the $\tfrac72\eta$ first
  set as a target.

The remaining Milestone 1 kernels (subtraction, comparisons, conversions, the directed-rounding
primitives, scaling by a power of two, and the `Ball` operations) are stated in
[Milestone 1 statements](design/milestone1.md), with the treatment of overflow and of non-finite
values.

## The formal model

Generated into `proofs/gen/`, following the Phase 0 tracer
([`experiments/phase0/tracer/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/tracer)):

- `Model.v`: inside a section with `Variable emin prec : Z` and `Variable choice : Z -> bool`,
  with `rnd := round radix2 (FLT_exp emin prec) (Znearest choice)`, one `Definition` per kernel
  over `R`. `prod a b` is `rnd (a * b + 0)`, for both of its executions in C++ (the rule of the
  product, above), `fms a b c` is `rnd (a * b + - c)`; a `call` stays a call
  (`let '(sh, sl) := two_sum x0 y0 in`), so that a proof can use the callee's theorem.
- `Statements.v`: one `Definition <kernel>_spec : Prop` per kernel, built from the kernel's
  claims. A hand-written proof must have exactly this type. A statement quantifies over every
  `emin` and every `prec` from the kernel's minimum on, and fixes the tie rule to ties-to-even.
  It assumes that every input limb is a number of the format and concludes, before the claims,
  that every output limb is one too (unless a `normalized` claim on that output already says
  so), so that the theorem of one kernel establishes the hypotheses of the next.
- `IeeeModel.v` and `IeeeStatements.v`: the same for the IEEE model
  ([Milestone 1 statements](design/milestone1.md#two-formal-models-of-one-kernel)): every kernel
  as a function of Flocq's binary floating-point numbers, with one binder per operation for the
  NaN it may return, and the IEEE-model statements of each kernel. They import two hand-written
  files: `proofs/theories/IeeeOperations.v`, which gives each operation of the IR its meaning in
  Flocq's terms, and `IeeeVocabulary.v`, the definitions the statements are written with.
  `IeeeAudit.v` is to them what `Audit.v` is to the real model, for the kernels of the extended
  domain.
- `IeeeFoldModel.v` and `IeeeFoldStatements.v`: the folds in the IEEE model, in the section of
  `IeeeModel.v`. `F_step` and `F_combine` apply the IEEE models of the step and the combination
  to the limbs of tuples of floats, as `FoldModel.v` does over the reals; `F_seq xs` is the finish
  on `fold_seq F_step zero xs` and `F_lanes W xs` the finish on `fold_lanes`, the zero state every
  limb $+0$. `F_seq_ieee_spec` and `F_lanes_ieee_spec` (the second for every `W`) say, for every
  precision from the fold's minimum, every `emax` and every choice of NaN, of every list of
  elements (`canonical_2` of an array of two limbs, any value for one limb): when the flag is
  true, every limb of every element and of the result is finite, the values of the result are
  those of the real model of the fold on the values of the elements (`FoldModel.F_O` at
  `ieee_emin prec emax`), and they are valid and within the bound of the fold's claims; when it is
  false, every limb of the result is a NaN ([When something is not
  finite](design/milestone2.md#sum-dot-axpy-convolution)). With them, for each kernel that is the
  step or the combination of a fold, `K_ieee_lead_spec`: if limb 0 of its result is finite, so is
  limb 0 of each operand, the non-finite cone of the rules as a statement. The steps of the folds
  have the bridge of their cores (`ieee: bridge`, and `spec` for those of two limbs), which the
  proof of a fold uses step by step. The maps and the convolutions follow, with their statements
  `F_seq_ieee_spec`, `F_lanes_ieee_spec` and `F_ieee_spec`, and the steps of the maps have their
  lead statements and bridges too ([Maps and convolutions in the IEEE
  model](#maps-and-convolutions-in-the-ieee-model)).
- **Their theorems.** A kernel of the finite domain names the theorem of each IEEE-model
  statement once it is proved: `ieee_bridge_theorem` (`K_ieee_bridge`, of `K_ieee_bridge_spec`),
  `ieee_spec_theorem` (`K_ieee_correct`, of `K_ieee_spec`) and `ieee_lead_theorem`
  (`K_ieee_lead`, of `K_ieee_lead_spec`), each as `FILE NAME`. A kernel of the extended domain names
  no bridge or spec theorem (its IEEE-model statement is its `ieee_theorem`'s), but one with a lead
  statement, the step of a fold (`neg_2`, `bv_center_2`), names its `ieee_lead_theorem`. A fold or a
  map names `ieee_theorem: FILE`, whose theorems are `F_seq_ieee_correct` and
  `F_lanes_ieee_correct` (and `F_orders_ieee_correct` and `F_flag_ieee_correct` for a fold of
  maxima in both orders), and a convolution or a product of two BallVectors the same field, whose
  theorem is `F_ieee_correct` (each has one statement, `F_ieee_spec`; until 2026-11-21 the audit
  printed a product's check against `F_seq_ieee_spec`, which does not exist). The comment above a
  statement
  says `proved` when its theorem is named and `unverified` otherwise. The comment above a fold's C++
  function gives both, as a kernel's does: `Status: proved (real model), unverified (IEEE model)` for
  `sum_2` (`cpp.fold_status`; until 2026-11-20 it gave the real model's alone). `IeeeAudit.v` checks
  every named theorem against its statement (`Definition S_audit : S := theorem.` and `Print
  Assumptions`), after the theorems of the extended domain, importing `IeeeFoldStatements` only
  when one of them is about a fold. Without any of these fields every generated file is what it
  was before they existed. Last, `IeeeAudit.v` checks the theorem of the two executions of every
  kernel of `IeeeWith.v` against its statement `K_two_executions_spec` (below), which no field
  names.
- `IeeeWith.v`: the kernels whose C++ computes an operation otherwise in constant evaluation than
  at run time (`ieee.with_kernels`): every kernel `constexpr` without a variant that computes, in
  its listing or a callee's, an operation whose spelling dispatches on constant evaluation; the
  thirty that `build` lists as `constexpr` by the rule of the product and 33 without a product,
  63 in all. They are in the IEEE model with the operations that constant evaluation runs
  differently as arguments. These
  are the operations whose C++ in a kernel `constexpr` without a variant dispatches on
  `__builtin_is_constant_evaluated()` (`cpp.SPELL_PLAIN`): `prod`, `guard` and `times_inf`
  (`ieee.CE_OPERATIONS`; the printer refuses to print the file if the C++ printer dispatches on
  any other). `K_with` is the definition of `IeeeModel.K` with every `prod a b` written `p_ a b`,
  every `guard a` written `g_ a` and every `times_inf t` written `t_ t`, for those of the three
  that the kernel computes, in its listing or a callee's (`K_with p_` for most of the rule of the
  product, `K_with p_ g_` for `axpy_entry_step_1`, `ball_from_interval_1` and
  `ball_from_interval_2`, `K_with p_ t_` for `mul_pow2_2_full`; `K_with g_`, `K_with t_` or
  `K_with g_ t_` for the kernels without a product), and every call of another such kernel written as its `K_with` on the
  arguments it takes; any other call stays a call of `IeeeModel`, and the printer refuses one
  whose callee computes `guard` or `times_inf` (its listing would keep the form of run time
  there). The section defines the three operations as constant evaluation computes them:
  `prod_ce`, the plain product `a * b` (Flocq's `Bmult`, rounded to nearest); `guard_ce`, the
  identity (the C++ is `h` where run time computes `h + 0.0`); and `times_inf_ce`, the function
  of the same name of `prelude.hpp`, comparison by comparison:
  `t > 0 ? +inf : 0 > t ? -inf : quiet_NaN()` is
  `if lt pzero t then pinf else if lt t pzero then B754_infinity prec emax true else cnan`, the
  NaN being that of `const nan`, which the C++ writes the same way. With the operations of run
  time (`IeeeOperations.prod`, `guard`, `times_inf`) `K_with` is `IeeeModel.K` by conversion (the
  lemmas `K_with_prod` of `proofs/theories/IeeeTwoExecutions.v`); with `prod_ce`, `guard_ce` and
  `times_inf_ce` it is the listing that constant evaluation runs, which the theorems
  `K_two_executions` compare with the run-time one. The definitions of `IeeeModel.v` are not
  changed by it, and the arguments' names have an underscore, which no value of a listing has.
  After the section, for each of these kernels, the statement of its two executions,
  `K_two_executions_spec`, in the shape of its theorem `K_two_executions` (the lines of the file
  are longer):

  ```coq
  Definition mul_pow2_2_full_two_executions_spec : Prop :=
    forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
           (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
           (nan_plus nan_plus' nan_minus nan_minus' : nan2 prec emax) (nan_abs nan_abs' : nan1 prec emax)
           (nan_fma' : nan3 prec emax) (nan_mult nan_mult' : nan2 prec emax)
           (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
    forall x0 x1 c : binary_float prec emax,
    let '(w0, w1) := mul_pow2_2_full_with prec emax nan_plus nan_minus nan_abs
                       (prod_ce prec emax nan_mult) (times_inf_ce prec emax nan_const) x0 x1 c in
    let '(w0', w1') := IeeeModel.mul_pow2_2_full prec emax nan_plus' nan_minus' nan_abs' nan_fma' nan_mult' x0 x1 c in
    xval w0 = xval w0' /\ xval w1 = xval w1'.
  ```

  For every format and its two instances, and for two families of NaN functions, the first for
  constant evaluation and the second (primed) for run time, each variable followed by its primed
  copy and only those that a side uses (`two_executions_nans`: those of `K_with`, `nan_mult` for
  `prod_ce` and `nan_const` for `times_inf_ce`; those of `IeeeModel.K`), on all operands in the
  order of the kernel's arguments (a mask among them in its place, `bv_mul_pow2_radius`), the
  listing at the operations of constant evaluation and the generated kernel return limbs that
  stand for the same extended real numbers (`xval`: equal, two zeros or two NaN) and the same
  masks; a kernel of one output has the two calls side by side, without a `let`. No description
  names its theorem: `IeeeAudit.v` checks `K_two_executions_audit : K_two_executions_spec :=
  IeeeTwoExecutions.K_two_executions` (the qualified name: `IeeeProduct.v` has an
  `rmul_two_executions` and a `mul_1_1_two_executions` of its own) for every kernel of the file,
  after the other checks, so that a kernel that joins the file without its theorem, or with a
  theorem of another statement, fails the proofs build by itself.
- `Audit.v`: for every kernel not marked `unverified`, a silent definition
  `<kernel>_audit : <kernel>_spec := <kernel>_correct`, which fails to compile unless the theorem
  has the generated statement as its type, followed by `Print Assumptions <kernel>_correct`. The
  file prints nothing else, so that the audit script can refuse any output it does not understand.
  A fold marked `proved` adds the same two lines for each of its orders (`<fold>_seq_correct`,
  `<fold>_lanes_correct`), a map or a convolution marked `proved` once, for its one statement
  (`<map>_audit : <map>_spec := <map>_correct`); `FoldStatements.v` is imported only then, so
  that the file does not change while every fold is `unverified`.
- `FoldModel.v`: inside a section with the variables of `Model.v`, four definitions per fold, over
  tuples of reals: an element is one entry of every array (for `dot_2`, `(R * R) * (R * R)`, read
  with `fst` and `snd`), the state the tuple of its limbs. `F_step` and `F_combine` apply the
  models of the step and the combination to those limbs; `F_seq xs` is
  `fold_seq F_step zero xs` and `F_lanes W xs` is `fold_lanes F_step F_combine zero W xs`, with the
  zero state `(0, 0)` (`0` for one limb) and the functions of `proofs/theories/Folds.v`:

  ```coq
  Definition dot_2_step (s : R * R) (xy : (R * R) * (R * R)) : R * R :=
    dot_step_2 emin prec choice (fst s) (snd s) (fst (fst xy)) (snd (fst xy)) (fst (snd xy)) (snd (snd xy)).
  Definition dot_2_combine (a b : R * R) : R * R :=
    add_2_2 emin prec choice (fst a) (snd a) (fst b) (snd b).
  Definition dot_2_seq (xs : list ((R * R) * (R * R))) : R * R :=
    fold_seq dot_2_step (0, 0) xs.
  Definition dot_2_lanes (W : nat) (xs : list ((R * R) * (R * R))) : R * R :=
    fold_lanes dot_2_step dot_2_combine (0, 0) W xs.
  ```

  The finish has no real-model statement (it is a kernel of the extended domain, like a full
  kernel) and is not in the model: in the real model nothing is infinite, and a fold's statement
  is about its final state.
- `FoldModel.v` has, for a map, `F_step`, the step on the scalars and one element, and
  `F_map`, `map` of it on the list of elements: in the real model a map has no state and no
  order. `FoldStatements.v` has its `F_spec`: for all scalars and lists of elements that satisfy
  the map's requirements, every limb a number of the format, `Forall2` of the elements and of
  `F_map` of them says, entry by entry, what the step's statement concludes (the formats of the
  output limbs and the step's claims), with the step's own names for the limbs:

  ```coq
  Definition axpy_2_spec : Prop :=
    forall emin prec : Z, (4 <= prec)%Z ->
    forall (a0 a1 : R) (xys : list ((R * R) * (R * R))),
    normalized_2 emin prec a0 a1 ->
    Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                      normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
    Forall2 (fun xy w_ =>
      let '((x0, x1), (y0, y1)) := xy in
      let '(z0, z1) := w_ in
      normalized_2 emin prec z0 z1 /\
      Rabs ((z0 + z1) - (((a0 + a1) * (x0 + x1)) + (y0 + y1))) <= ...)
      xys (axpy_2_map emin prec tie_even (a0, a1) xys).
  ```

  Its proof is the step's theorem on each element, through the lemma `Forall2_map_r` of
  `Folds.v`: `Forall2_map_r : forall (A B : Type) (P : A -> B -> Prop) (f : A -> B) (xs : list A),
  Forall (fun x => P x (f x)) xs -> Forall2 P xs (map f xs)`.
- `FoldStatements.v`: `<fold>_seq_spec` and `<fold>_lanes_spec`, the second for every number of
  lanes `W`. For every list of elements whose limbs are numbers of the format and that satisfy the
  fold's requirements (`normalized_2` for `canonical`), the final state is valid (`fmt`, or
  `normalized_2` for two limbs) and within the bound of `fold_error`, written with `sumR` and
  `sumabs` of `proofs/theories/Summation.v`, in the form with powers of the page:

  ```coq
  Definition dot_2_seq_spec : Prop :=
    forall emin prec : Z, (4 <= prec)%Z ->
    forall xys : list ((R * R) * (R * R)),
    Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                      normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
    let s := dot_2_seq emin prec tie_even xys in
    normalized_2 emin prec (fst s) (snd s) /\
    Rabs ((fst s + snd s) - sumR (map (fun xy => ((fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))) xys)) <=
      ((1 + (4 * (u prec ^ 2))) * (1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length xys - 1) - 1) *
        sumabs (map (fun xy => ((fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))) xys) +
      (1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length xys - 1) * (INR (length xys) * ((3 / 2) * eta emin)).
  ```

  (The generated text has each conjunct on one line.) The heights are natural numbers
  (`length xys - 1` is 0 for the empty list). The statements do not use $\gamma$: the form with
  $\gamma_{n-1}(\varepsilon)$ is a corollary when $(n-1)\,\varepsilon < 1$
  (`pow_minus_1_le_gamma` of `Summation.v`), and the exported bounds below are stated against the
  power form's constants.

`make -C proofs` fails if any theorem depends on anything other than the four allowed axioms
(`ClassicalDedekindReals.sig_forall_dec`, `ClassicalDedekindReals.sig_not_dec`,
`FunctionalExtensionality.functional_extensionality_dep`, `Classical_Prop.classic`), or if a
proof file contains `Admitted`, `admit`, `Axiom` or `Parameter`.

## Claims

`gen/claims.json` is the only thing the oracle and the documentation learn from the generator.

```json
{
  "schema": 1,
  "kernels": [
    {
      "name": "mul_2_2",
      "inputs":  [{"name": "x", "limbs": 2}, {"name": "y", "limbs": 2}],
      "outputs": [{"name": "z", "limbs": 2}],
      "value": "x*y",
      "requires": ["normalized(x)", "normalized(y)"],
      "ensures": [
        {"kind": "normalized", "of": "z"},
        {"kind": "error", "of": "z", "form": "R", "c": "4", "k": 2, "t": "3/2", "when": null}
      ],
      "min_precision": 4,
      "status": "proved",
      "theorem": {"file": "proofs/theories/Mul22.v", "name": "mul_2_2_correct"},
      "source": {"cite": "JMP17 Alg. 12; bound from MR22", "license": "algorithm: published; proof: MIT"},
      "flops": 9,
      "instances": {
        "binary64": [{"rel": "1/20282409603651670423947251286016", "abs": "..."}],
        "binary32": [{"rel": "...", "abs": "..."}]
      }
    }
  ]
}
```

- `value` is the exact real function the output approximates: `x+y`, `x-y` or `x*y` of the input
  values, or one input by name (the value of a multi-limb input is the exact sum of its limbs).
- `min_precision` is the smallest precision for which the claims hold, or `null` when it is not
  known yet; the oracle then judges every format.
- `requires` uses a closed vocabulary: `normalized(NAME)`, `abs_ge(NAME, NAME)`. Operands are
  always finite.
- `ensures` holds whenever the requirements hold and output limb 0 is finite:
    - `normalized`: the output satisfies the invariant;
    - `error`: $\lvert \text{output} - \text{value}\rvert \le c\,u^k\,\rho + t\,\eta$ where $\rho$ is
      $\lvert\text{value}\rvert$ for form `R` and the sum of the absolute values of the inputs for
      form `A`. `c` is a rational expression in `u`, `t` a rational. `when` is `null` or a
      condition from a closed vocabulary; in this wave only `product_large`, meaning
      $\text{value} = 0$ or $\lvert\text{value}\rvert \ge 2^{2p-1}\eta$;
    - `leading_rounded`: output limb 0 equals $\mathrm{RN}(\text{value})$.
- `instances` gives, per named format, `rel` $= c\,u^k$ and `abs` $= t\,\eta$ of each `error`
  entry as exact fractions (a list, in the order of the entries). For
  a named format the oracle uses these numbers; it also evaluates `c` and `t` itself, which is
  what it does for toy formats, and refuses a kernel on which the two disagree.
- `status` is `proved` only when the audit has passed for that kernel.

### Claims of the second wave

The kernels of [Milestone 1 statements](design/milestone1.md) return masks, single limbs rounded
in a direction, upper bounds and balls, so the vocabulary grows. Everything above stays as it is.

- **Inputs and outputs** may carry `"type": "mask"` (one value, written `0` or `1` in the line
  protocol). The default type is a limb group.
- **`value`** is an expression over the inputs: names, `+`, `-`, `*`, unary minus, `abs( )` and
  parentheses. Examples: `x-y`, `-x`, `abs(x)`, `c*x`.
- **`requires`** gains `power_of_two(NAME)` and `nonneg(NAME)`.
- **`instances`** holds, for each named format, a list with one object per `error` entry, in
  order; the list is empty for a kernel without `error` entries.
- **`min_precision`** is an integer for every proved kernel: the smallest $p$ of its theorem.
- **`ensures`** gains:

| Kind | Fields | Meaning |
|---|---|---|
| `rounded` | `of`, `mode`: `nearest`, `down` or `up` | the one-limb output is `value` rounded that way: to nearest with ties to even, to the largest number of the format not above it, to the smallest not below it |
| `upper` | `of`, `gaps` | `value` $\le$ output, and the output exceeds `value` by at most `gaps` times (output $-$ `pred`(output)) |
| `predicate` | `of` (a mask), `rel`: `lt`, `le` or `eq`, `args`: two expressions | the mask is true exactly when the relation holds between the exact values of the two expressions |
| `encloses` | `center`, `radius`, `set`: an expression over ball names, `balls`: for each name its center and radius inputs | every value of `set`, with each ball name ranging over its ball, is within `radius` of `center` |

A kernel may use `const unit_computed(K)` and `const tiny_computed(K)`: the constants of kernel
`K`'s proved bound in the form relative to the computed result, $\mathrm{unit}/(1 - \mathrm{unit})$
and $\mathrm{tiny}/(1 - \mathrm{unit})$ with $\mathrm{unit} = c\,u^k$ and $\mathrm{tiny} = t\,\eta$,
each rounded up to a number of the format. The generator computes them exactly, for every format,
from `K`'s claims; they may be used only if `K` is `proved`, or the kernel using them is itself
`unverified`.

In the formal model: a mask is a `bool` (`Rlt_bool`, `Rle_bool`, `Req_bool`), `select` is
`if ... then ... else`, `succ` and `pred` are Flocq's, a value rounded down or up is Flocq's
`round` with `Zfloor` or `Zceil`, and `encloses` quantifies over all real numbers within the
radii of the centers.

### Claims of the non-finite layer

The claims above are about finite operands, and say nothing when output limb 0 is not finite. The
kernels that define what happens otherwise ([IEEE-like results](design/milestone1.md#ieee-like-results),
[special states of a ball](design/milestone1.md#ball-kernels)) carry `"domain": "extended"`:
their operands may be infinite or NaN, and every completed line is judged. A kernel without the
field has the domain `finite`, as before.

- **`requires`** gains `canonical(NAME)` for a 2-limb operand (finite and normalized, or
  $(\pm\infty, \pm 0)$, or all NaN) and `ball(CENTER, RADIUS)` for a ball (a finite ball with a
  canonical finite center and a finite nonnegative radius, or center 0 and radius $+\infty$, or
  all NaN). A one-limb operand with no requirement is any value of the format, $\pm\infty$ or
  NaN; `power_of_two(NAME)` and `nonneg(NAME)` keep excluding everything else, except that
  `nonneg` admits $+\infty$ and NaN in this domain.
- **`ensures`** gains `extends`, and `encloses`, `predicate`, `rounded`, `upper`, `normalized`
  and `error` are read as follows in this domain.

| Kind | Fields | Meaning in the extended domain |
|---|---|---|
| `extends` | `of`, `core`: a kernel with the same inputs and outputs, `lead`: `add`, `sub` or `mul`, `finite_when`: a list of conditions | F1 to F5 of [IEEE-like results](design/milestone1.md#ieee-like-results): the output is canonical; if it is finite, every operand is finite and every `ensures` entry of `core` holds; if every operand is finite and every condition holds, the output is finite; if every operand is finite and the output is not, it is $(\pm\infty, 0)$ with the sign of `value` (the proofs give $+0$; the sign of a zero is not part of a claim); if an operand is not finite, the output is the canonical form of `lead` applied to the leading limbs of the inputs, in order, by the rules of IEEE 754 |
| `encloses` | as before, and `finite_when` | B1 to B4 of [Ball kernels](design/milestone1.md#ball-kernels): the output ball is canonical; it is empty exactly when a ball operand is empty; if it is a finite ball, every operand is finite and the containment holds; if every operand is finite and every condition holds, it is a finite ball |
| `normalized`, `error` | as before | apply when every operand and the output are finite; the output is canonical in every case |
| `predicate` | as before | the relation between the two values as extended real numbers; false when an operand is a NaN |
| `rounded` | as before | for a finite operand, the rounding of `value` in the sense of the format with overflow: a result beyond $\Omega$ in the direction of rounding is the infinity; for an infinite or NaN operand, `value` of it (the operand itself, or its absolute value for `abs_upper_2`) |
| `upper` | as before | (the building blocks of one operation of this domain, `radd`, `rmul` and `radd_entry`) the output is a NaN exactly when an operand is a NaN or the operation is $0 \cdot \infty$; otherwise it is not below `value`, and `gaps` applies when it is finite |

A condition of `finite_when` is `{"abs_le": EXPR, "exp": E}`: $\lvert \mathrm{EXPR}\rvert \le
2^{q_{\max} + p + E}$, with `EXPR` an expression over the input names as in `value` and $E$ an
integer; $2^{q_{\max} + p}$ is the overflow threshold. For example `add_2_2_full` has
`[{"abs_le": "x", "exp": -2}, {"abs_le": "y", "exp": -2}]`, `mul_2_2_full` has
`[{"abs_le": "x*y", "exp": -1}]`, and `ball_add_2_full` has
`[{"abs_le": "abs(cx+cy)+rx+ry", "exp": -2}]`: for a ball the names are those of the centers and
the radii, and the expression is the largest magnitude of a member of the exact result
([when the result is a finite ball](design/milestone1.md#when-the-result-is-a-finite-ball)). The
list is empty when no condition is claimed, and an empty list claims nothing about when the
result is finite: it does not say that it always is. Every full kernel and every full Ball
kernel has a condition; `ball_neg_k` has none. The promise of a finite result (F3, B4) is claimed
in the formats of the statements, `binary_float`'s ([The formats of the
statements](#number-formats)), not in every toy format.

**`upper` of a kernel of the finite domain with several operations.** The row of `upper` above is
about the building blocks of one operation of the extended domain. A kernel of the finite domain
with several operations, such as `conv_radius`, the radius of a product of two BallVectors, claims
`upper` as a statement of the real-number model: by the ruling of 2026-11-21 its claim is
of finite results, and a result that is not finite claims only that it is $+\infty$ or a NaN,
never a negative number, never $-\infty$. That is what is proved of `conv_radius` in the model with
infinities and NaN, a hand lemma (`conv_radius_ieee`, `proofs/theories/IeeeBvConv.v`): on
nonnegative operands the result is nonnegative, $+\infty$ or a NaN, and when it is finite the
operands are finite and it is the real model's value. Its listing returns a NaN where `prod(ma, mb)`
overflows and `g` or `m` is zero (an infinity times zero inside), and $+\infty$ where it overflows
and `g` is small, from a stated value far below the largest number. The loop that calls it,
`bv_conv_k`, turns any radius that is not finite into the whole space, and its own statement covers
those cases. The radius kernels of the other ball vectors are read as [their entries
are](#claims-of-milestone-2): at least `value`, finite or $+\infty$.

The `core` of `extends` has the inputs of the full kernel, by name, and outputs of the same shape
under other names; they correspond by position. Its requirements are the full kernel's with
`normalized` for `canonical`.

Two more kinds serve the constructors
([values that enter from the program](design/milestone1.md#values-that-enter-from-the-program)):

| Kind | Fields | Meaning |
|---|---|---|
| `represents` | `of` | the output is canonical and is `value` exactly: a finite `value` gives a finite normalized output of that value, $\pm\infty$ gives $(\pm\infty, 0)$, a NaN gives all NaN |
| `makes_ball` | `center`, `radius`: the outputs; `from`: the inputs given as center and radius | the output ball is canonical: empty when the given radius is negative, $-\infty$ included; otherwise the whole line when the given radius is a NaN or $+\infty$ or the given center is not finite; otherwise the given center and radius, exactly. (A NaN radius gave the empty set until the owner's decision of 2026-11-20, which made it the whole line, as a NaN bound given to an interval is.) |

`value` may be an expression there too: `neg_2` and `abs_2` carry `represents` next to their
`normalized` and `error` entries, with the values `-x` and `abs(x)`, and that entry is what says
which canonical value comes out for an infinite or NaN operand (the infinity with its sign
changed or removed; a NaN for a NaN). In the real model `represents` adds nothing to
`normalized` with an exact `error`, and the generated real-model statement does not print it.
`ball_neg_k`, which needs no fix-up, carries the extended-domain `encloses` like the full Ball
kernels.

A kernel of this domain has a statement in the IEEE model, generated like the real-model
statements and proved the same way. A kernel that also makes sense on finite operands alone
(the comparisons, the conversions, `neg_2`, `abs_2`, `radd`, `rmul`) keeps its real-model
statement and gains the IEEE-model one: its `requires` say `canonical` where they said
`normalized`, which is the same thing for a finite operand. A full kernel or a constructor has
the IEEE-model statement only, and a core keeps the real-model one and the domain `finite`.

A kernel without a real-model statement (a full kernel, a full Ball kernel, a constructor)
carries `"ieee_only": true`; the field is absent otherwise. `status` and `theorem` keep referring
to the real-model statement where there is one. A kernel
of the extended domain also carries `ieee_status` (`proved` or `unverified`) and, when proved,
`ieee_theorem`; for a full kernel or a constructor, which has no real-model statement, `status`
is its `ieee_status`. The oracle judges the claims whatever the statuses say.

Three entries in full, as the generator writes them (`source`, `flops` and the theorem fields
left out):

```json
{
  "name": "add_2_1_full", "domain": "extended", "ieee_only": true,
  "inputs": [{"name": "x", "limbs": 2}, {"name": "a", "limbs": 1}],
  "outputs": [{"name": "w", "limbs": 2}],
  "value": "x+a",
  "requires": ["canonical(x)"],
  "ensures": [{"kind": "extends", "of": "w", "core": "add_2_1", "lead": "add",
               "finite_when": [{"abs_le": "x", "exp": -2}, {"abs_le": "a", "exp": -2}]}],
  "min_precision": 3, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_mul_2_full", "domain": "extended", "ieee_only": true,
  "inputs": [{"name": "cx", "limbs": 2}, {"name": "rx", "limbs": 1},
             {"name": "cy", "limbs": 2}, {"name": "ry", "limbs": 1}],
  "outputs": [{"name": "cw", "limbs": 2}, {"name": "rw", "limbs": 1}],
  "value": "cx*cy",
  "requires": ["ball(cx, rx)", "ball(cy, ry)"],
  "ensures": [{"kind": "encloses", "center": "cw", "radius": "rw", "set": "x*y",
               "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}},
               "finite_when": [{"abs_le": "(abs(cx)+rx)*(abs(cy)+ry)", "exp": -2}]}],
  "min_precision": 4, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_make_2", "domain": "extended", "ieee_only": true,
  "inputs": [{"name": "c", "limbs": 2}, {"name": "r", "limbs": 1}],
  "outputs": [{"name": "cw", "limbs": 2}, {"name": "rw", "limbs": 1}],
  "requires": ["canonical(c)"],
  "ensures": [{"kind": "makes_ball", "center": "cw", "radius": "rw", "from": {"center": "c", "radius": "r"}}],
  "min_precision": 1, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
}
```

A kernel description also has fields that drive the IEEE-model printer and are not written to
the claims: `ieee`, `ieee_finite` and `ieee_finite_result` name the IEEE-model statements of a
finite core (the bridge, and the two forms of "no overflow below a threshold"), and `ieee_only`
marks a kernel that has no real-model statement (`gen/README.md`).

The minimum precision of a full kernel is that of its core (2 for the one-limb full Ball
kernels, whose constants must stay below the overflow threshold). In the extended domain the scalar of
`ball_scale` is any value of the format, $\pm\infty$ or NaN, and one that is not finite gives the
whole line (the empty set if the ball operand is empty). `make_2_limbs` takes its two limbs as one
2-limb input with `canonical`.

### Claims of Milestone 2

The kernels of [Milestone 2 statements](design/milestone2.md) that are written so far (its first
wave: "Building blocks on T" and "Scaling a ball by a power of two"; and the folds' stage of "Batch
kernels": the sums and dot products, their steps and finishes, and the bounds as functions of $n$)
need the additions below.
Everything above keeps its meaning and its JSON shape: a field that is new to a kind that exists
is written only in an entry that uses it, so that no entry without it changes.

Two definitions that the readings use, from the page's
[notation](design/milestone2.md#notation-and-vocabulary). A *step* is to the next number of the
format above or below. A finite $t$ *rounded down in the format with overflow* is the largest
number of the format not above $t$, except that it is $\Omega$ when $t > \Omega$ and $-\infty$ when
$t < -\Omega$; *rounded up*, symmetrically, the smallest not below $t$, $+\infty$ when
$t > \Omega$ and $-\Omega$ when $t < -\Omega$. Rounded to nearest it is $\mathrm{RN}(t)$, the
infinity of its sign when the rounding in unbounded range reaches $2^{q_{\max} + p}$, as before.
In the extended domain a step from $\pm\Omega$ outward is the infinity, and a step from an
infinity is the one of the table of `neighbor` below.

| Kind | Fields | Finite domain, and finite operands in the extended domain | With an infinite or NaN operand, in the extended domain |
|---|---|---|---|
| `neighbor` | `of` (a one-limb output), `side`: `up` or `down` | `value` is the name of a one-limb input; the output is the next number of the format above it (`up`) or below it (`down`) | the table below |
| `bound` | `of` (a one-limb output), `side`: `below` or `above`, `steps`: an integer $\ge 0$ | `below`: the output is at most `value`, and at least `value` rounded down, then stepped down `steps` times; `above`: at least `value`, and at most `value` rounded up, then stepped up `steps` times. In the extended domain the roundings are in the format with overflow, and the output may be an infinity | the output is `value` as IEEE 754 defines it on the operands (below) |
| `rounded`, with `when` | as before, and `when`: `product_large` | when the condition holds (`value` $= 0$ or $\lvert\text{value}\rvert \ge 2^{2p-1}\eta$, as for `error`), the output is `value` rounded that way, in the format with overflow in the extended domain; nothing is claimed otherwise | as `rounded` without `when` |
| `rounded`, of the value of two operands | as before | in the extended domain, `value` rounded in the format with overflow; for `down` a sum beyond $\Omega$ gives $\Omega$, not $+\infty$ | the output is `value` as IEEE 754 defines it on the operands |
| `rounded`, with `value` | as before, and `value`: an expression of the inputs and their limbs `NAME[I]` (`+ - *`, unary minus, `abs( )`), in the finite domain | the output is that expression rounded that way, in place of the kernel's `value` (the accumulator's sum of magnitudes, [The accumulator](#the-accumulator)); of an output group other than the first, where its leading limb is finite | none: of the finite domain only |
| `exact_when`, a field of `error` | a list of conditions (below) | when every condition holds, the output equals `value` exactly (in the extended domain: when every operand and the output are finite, as for `error`) | nothing more |
| `exact_when`, a field of `encloses` | a list of conditions | when every condition holds, the output ball is exactly the set: besides containing every value of `set` (the claim of `encloses`), every number within `radius` of `center` is a value of `set`, with each ball name ranging over its ball. With containment this says that center $-$ radius and center $+$ radius are the least and the greatest value of `set`. In the extended domain it applies when the output is a finite ball (every operand is then finite) | nothing more |

`value` *as IEEE 754 defines it on the operands*, for `value` an expression of one or two input
names: a NaN when an operand is a NaN, for the sum of $+\infty$ and $-\infty$ (or the difference of
two equal infinities) and for the product of a zero and an infinity; otherwise an infinity when an
operand is one, the infinity of the sum, or of the product of the signs; `neg` and `abs` of an
infinity are the infinities they give. As always, the sign of a zero is not part of a claim and a
NaN is any NaN.

The table of `neighbor` ([next_up and next_down on every input](design/milestone2.md#next_up-and-next_down-on-every-input)),
which in the extended domain covers every value of the format:

| `value` | `side` `up` | `side` `down` |
|---|---|---|
| a NaN | a NaN | a NaN |
| $+\infty$ | $+\infty$ | $\Omega$ |
| $\Omega$ | $+\infty$ | the number before $\Omega$ |
| a finite number $x$ | the smallest number of the format above $x$ | the largest number of the format below $x$ |
| $-\Omega$ | the number after $-\Omega$ | $-\infty$ |
| $-\infty$ | $-\Omega$ | $-\infty$ |

Either zero is followed by $\eta$ and preceded by $-\eta$; $-\eta$ is followed by a zero and
$\eta$ preceded by one.

**A condition of `exact_when`** is one of

- `{"zero_or_abs_gt": EXPR, "than": K}`: EXPR $= 0$ or $\lvert\mathrm{EXPR}\rvert > K$;
- `{"zero_or_abs_ge": EXPR, "than": K}`: EXPR $= 0$ or $\lvert\mathrm{EXPR}\rvert \ge K$;
- `{"mask": NAME}`, in the `exact_when` of an `upper` entry only (the radius of the scaling of a
  BallVector by a power of two, [below](#claims-of-milestone-2)): the mask input NAME is true;

and the list holds when every condition does. EXPR is an expression of the language of `value`
(input names, `+`, `-`, `*`, unary minus, `abs( )`, parentheses) in which, besides an input's
name (the exact sum of its limbs), `NAME[I]` is limb I of the input NAME, the leading limb being
`NAME[0]`. K is an exact expression over `u`, `eta` and integers, with `+`, `-`, `*`, `/`,
parentheses and integer powers `^` (possibly negative, `2^-3`), positive in every format: the
language of `const up(EXPR)` without `unit( )`, `tiny( )` or a rounding. Both are evaluated
exactly, with $u = 2^{-p}$ and $\eta = 2^{q_{\min}}$ of the format; `eta/(2*u)` is $N$, the
smallest normal number.

The fields of each new entry, in this order (`instances` is unchanged: one object per `error`
entry, `exact_when` or not):

```json
{"kind": "neighbor", "of": "r", "side": "up"}
{"kind": "bound", "of": "r", "side": "below", "steps": 1}
{"kind": "rounded", "of": "r", "mode": "down", "when": "product_large"}
{"kind": "error", "of": "z", "form": "R", "c": "0", "k": 2, "t": "1", "when": null,
 "exact_when": [{"zero_or_abs_ge": "x[0]*c", "than": "eta/(2*u)"}]}
{"kind": "encloses", "center": "cz", "radius": "rz", "set": "x*c",
 "balls": {"x": {"center": "cx", "radius": "rx"}}, "finite_when": [...],
 "exact_when": [{"zero_or_abs_gt": "cx[0]*c", "than": "eta/(2*u)"}]}
```

`steps` is a JSON integer; `when` and `value` of `rounded` are absent when there is none (an `error`
entry keeps its `"when": null`); `exact_when` is absent when there is none; `finite_when` is
written, as before, for an `encloses` entry of the extended domain only. Four entries in full, as
the generator writes them (`source`, `flops` and the theorem fields left out):

```json
{
  "name": "next_up", "domain": "extended",
  "inputs": [{"name": "a", "limbs": 1}], "outputs": [{"name": "r", "limbs": 1}],
  "value": "a", "requires": [],
  "ensures": [{"kind": "neighbor", "of": "r", "side": "up"}],
  "min_precision": 1, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "mul_down_1", "domain": "extended",
  "inputs": [{"name": "a", "limbs": 1}, {"name": "b", "limbs": 1}], "outputs": [{"name": "r", "limbs": 1}],
  "value": "a*b", "requires": [],
  "ensures": [{"kind": "bound", "of": "r", "side": "below", "steps": 1},
              {"kind": "rounded", "of": "r", "mode": "down", "when": "product_large"}],
  "min_precision": 2, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_mul_pow2_2",
  "inputs": [{"name": "cx", "limbs": 2}, {"name": "rx", "limbs": 1}, {"name": "c", "limbs": 1}],
  "outputs": [{"name": "cz", "limbs": 2}, {"name": "rz", "limbs": 1}],
  "value": "cx*c", "requires": ["normalized(cx)", "nonneg(rx)", "power_of_two(c)"],
  "ensures": [{"kind": "normalized", "of": "cz"},
              {"kind": "encloses", "center": "cz", "radius": "rz", "set": "x*c",
               "balls": {"x": {"center": "cx", "radius": "rx"}},
               "exact_when": [{"zero_or_abs_gt": "cx[0]*c", "than": "eta/(2*u)"},
                              {"zero_or_abs_gt": "cx[1]*c", "than": "eta/(2*u)"},
                              {"zero_or_abs_gt": "rx*c", "than": "eta/(2*u)"}]}],
  "min_precision": 2, "status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_mul_pow2_1_full", "domain": "extended", "ieee_only": true,
  "inputs": [{"name": "cx", "limbs": 1}, {"name": "rx", "limbs": 1}, {"name": "c", "limbs": 1}],
  "outputs": [{"name": "cw", "limbs": 1}, {"name": "rw", "limbs": 1}],
  "value": "cx*c", "requires": ["ball(cx, rx)", "power_of_two(c)"],
  "ensures": [{"kind": "encloses", "center": "cw", "radius": "rw", "set": "x*c",
               "balls": {"x": {"center": "cx", "radius": "rx"}},
               "finite_when": [{"abs_le": "(abs(cx)+rx)*c", "exp": -2}],
               "exact_when": [{"zero_or_abs_gt": "cx*c", "than": "eta/(2*u)"},
                              {"zero_or_abs_gt": "rx*c", "than": "eta/(2*u)"}]}],
  "min_precision": 2, "status": "proved", "ieee_status": "proved",
  "instances": {"binary64": [], "binary32": []}
}
```

The other kernels of the wave use kinds that exist: `two_sum_ord` claims `leading_rounded`, an
exact `error` and `normalized`, as `fast_two_sum` does, in the finite domain; `add_down_1`,
`add_up_1`, `sub_down_1`, `sub_up_1` claim `rounded` of the value of two operands, in the extended
domain; and each entry form claims exactly what the kernel it calls claims, in the same domain
(`two_sum_entry` and `fast_two_sum_entry` in the finite one, `radd_entry` and the four directed
sums in the extended one).

How they are stated in the formal models: in the real model `neighbor` is Flocq's `succ` or `pred`
of `value`, `bound` brackets the output between `value` and `RD` (or `RU`) of `value` stepped by
`pred` (or `succ`), and `exact_when` adds a conjunct to the claim it belongs to: `error` then says
that the output limbs sum to `value`, `encloses` that every real within the radius of the center
is a value of the set. In the IEEE model the claims of a kernel that needs no fix-up are read over
extended reals (`proofs/theories/IeeeVocabulary.v`: `xsucc`, `xpred`, `xrd`, `xru`, `xadd`, `xmul`),
and a full Ball kernel's statement has the exactness between B3 and B4. `rounded` of a value of one
operand is printed as before (`xround`), which is the same thing for a value below $2^{q_{\max}+p}$
in magnitude, as a canonical one is.

**Not expressible, and so not claimed, in this wave:** what `two_sum_ord` returns at an overflow
and for infinite or NaN operands (the page's table of its IEEE model: $(+\infty, -\infty)$ and
$(\pm\infty, \mathrm{NaN})$, pairs that are not canonical); its IEEE-model statement is that of a
finite core, as `fast_two_sum`'s (finite operands and a finite sum give a finite error term and
the claims). `mul_pow2_2` keeps its claims and its statement: an `exact_when` on its `error` entry
would change the generated statement `mul_pow2_2_spec` that `mul_pow2_2_correct` proves, so its
exactness stays the hand-written `mul_pow2_2_exact` ([Milestone 1](design/milestone1.md#second-wave-kernels)).

**The kernels of the folds' stage.** Their claims need the following, in the same way (a field
exists only in an entry that uses it):

- **`requires`** gains `count(NAME)`: the one-limb input is $0$ or at least $1$ (a number of terms
  or of additions; it need not be an integer), and `format(half)`, which names no input: the
  format contains $\tfrac12$, that is $\eta \le \tfrac12$, as `binary64`, `binary32` and every
  toy format with $q_{\min} \le -1$ do.
- **`error`** gains the form `T`: $\rho$ is the sum of the magnitudes of the *terms* of `value`;
  for `s+x*y` (`dot_step_2`), $\lvert s\rvert + \lvert x y\rvert$. `instances` are as for the
  forms `R` and `A`. Once such a kernel is proved, `include/kairn/gen/bounds.hpp` exports its
  `unit` and `tiny` with the form `terms` (`Form::terms`), and, as for the form `A`, no constants
  relative to the computed value.
- **`upper`** may carry `value` and `if` in place of `gaps`: `value` is an exact expression over
  the inputs, the one-limb outputs, `u`, `eta`, integers, `^` and the constants `unit(K)` and
  `tiny(K)` of kernel K's bound ($c\,u^k$ and $t\,\eta$ of its `error` entry), and replaces the
  kernel's `value` for this entry; `if` names a mask output. When the mask is true, the output is
  at least the exact value of `value`; nothing is said of how far above, and nothing at all when
  the mask is false.
- **`holds`**, `{"kind": "holds", "rel": "lt" | "le" | "eq", "args": [A, B], "if": MASK}`: when the
  mask output is true, the relation holds between the exact values of A and B, expressions as in
  `value` of `upper`.
- **`finite_or_nan`**, `{"kind": "finite_or_nan", "of": R, "flag": F}`, the extended domain only:
  the mask F is true exactly when limb 0 of `value` (the kernel's input) is finite, and the output
  R is then `value`, limb for limb; otherwise every limb of R is a NaN.

The kernels are `dot_step_1` (`rounded` of `s+x*y` to nearest, in the finite domain, as
`fma(x, y, s)` computes it), `dot_step_2` (`normalized`, and `error` of form `T`), the steps of
the sums of supplied arrays `sum_entry_step_1`, `sum_entry_step_2` and `sum_fast_entry_step_2`
(the claims of `add_1_1`, `add_2_2` and `add_fast_2_2`, which they call after their guards), the
finishes `fold_finish_1` and `fold_finish_2` (`finite_or_nan`, `ieee_only`), and the bounds:

```json
{
  "name": "bound_dot_2",
  "inputs": [{"name": "m", "limbs": 1}],
  "outputs": [{"name": "g", "limbs": 1}, {"name": "t", "limbs": 1}, {"name": "ok", "limbs": 1, "type": "mask"}],
  "requires": ["count(m)", "format(half)"],
  "ensures": [{"kind": "holds", "rel": "le", "args": ["m*unit(mul_2_2)", "1/2"], "if": "ok"},
              {"kind": "upper", "of": "g", "value": "m*unit(mul_2_2)/(1-m*unit(mul_2_2))", "if": "ok"},
              {"kind": "upper", "of": "t", "value": "m*tiny(mul_2_2)*(1+g)", "if": "ok"}],
  "min_precision": 4, "status": "proved",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "bound_sum_1",
  "inputs": [{"name": "m", "limbs": 1}],
  "outputs": [{"name": "g", "limbs": 1}, {"name": "ok", "limbs": 1, "type": "mask"}],
  "requires": ["count(m)", "format(half)"],
  "ensures": [{"kind": "holds", "rel": "le", "args": ["m*unit(add_1_1)", "1/2"], "if": "ok"},
              {"kind": "upper", "of": "g", "value": "m*unit(add_1_1)/(1-m*unit(add_1_1))", "if": "ok"}],
  "min_precision": 1, "status": "proved",
  "instances": {"binary64": [], "binary32": []}
}
```

`bound_sum_2` is `bound_sum_1` with `add_2_2` (minimum precision 3), and `bound_dot_1` is
`bound_dot_2` with `mul_1_1` (minimum precision 1). These kernels have no `value`: every entry has
its own. In the formal model `count(m)` is `(m = 0 \/ 1 <= m)`, `format(half)` is
`eta emin <= / 2`, and an entry with `if` is `(ok = true -> ...)`. The statements are the first
link of the page's chain only, that the outputs cover these exact values; that $g$ then covers
$\gamma_m$ of the bound of the fold, for $m$ the number of terms, is a lemma about natural numbers
left to the proofs.

**Folds.** `gen/claims.json` has a second list, `"folds"`, absent when there is no fold (so that a
reader of the kernels alone sees nothing new). Each entry, as the generator writes it (`tau` cut
short here):

```json
{
  "name": "dot_2", "domain": "extended",
  "arrays": [{"name": "x", "limbs": 2, "role": "supplied"}, {"name": "y", "limbs": 2, "role": "supplied"}],
  "outputs": [{"name": "r", "limbs": 2}, {"name": "flag", "limbs": 1, "type": "mask"}],
  "value": "x*y",
  "requires": ["canonical(x)", "canonical(y)"],
  "ensures": [{"kind": "normalized", "of": "r"},
              {"kind": "fold_error", "of": "r", "eps": "3*u^2/(1-4*u)", "term": "4*u^2", "tau": "3/2*eta",
               "heights": {"sequential": {"rel": "n-1", "abs": "n-1"}, "lanes": {"rel": "n-1", "abs": "n-1"}}},
              {"kind": "finite_or_nan", "of": "r", "flag": "flag"}],
  "orders": ["sequential", "lanes"],
  "packed_lanes": {"binary64": {"avx2": 4, "neon": 2}, "binary32": {"avx2": 8, "neon": 4}},
  "step": "dot_step_2", "combine": "add_2_2", "finish": "fold_finish_2",
  "min_precision": 4, "status": "proved", "theorems": {"sequential": {"file": "proofs/theories/FoldSums.v", "name": "dot_2_seq_correct"}, "lanes": {"file": "proofs/theories/FoldSums.v", "name": "dot_2_lanes_correct"}},
  "source": {"cite": "Higham's bound for summation over any tree, with the bounds of add_2_2 and mul_2_2 (MR22)",
             "license": "bound: published; proof: MIT"},
  "instances": {"binary64": [{"eps": "3/81129638414606645666991986180096",
                              "term": "1/20282409603651670423947251286016", "tau": "3/4048...9568"}],
                "binary32": [{"eps": "1/93824969867264", "term": "1/70368744177664",
                              "tau": "3/1427247692705959881058285969449495136382746624"}]}
}
```

- `arrays` are the arrays an element is read from, in order, each with its limbs and its role
  (`stored` or `supplied`, which matters to rule R3 only); `outputs` are the fold's results, as
  the outputs of a kernel. `value` is the exact value of one element, over the arrays' names (the
  value of a multi-limb entry is the sum of its limbs); the fold approximates $\sum_i v_i$ over
  its $n$ elements, and `requires` applies to every element.
- `fold_error`: with $v_i$ the value of element $i$,
  $\bigl\lvert r - \sum_i v_i\bigr\rvert \le \bigl((1 + \mathit{term})(1 + \varepsilon)^{h_r} - 1\bigr)\sum_i\lvert v_i\rvert + (1 + \varepsilon)^{h_a}\,n\,\tau$,
  where $\varepsilon$ is `eps`, and $h_r$ and $h_a$ are `rel` and `abs` of the order's `heights`:
  `n` or `n-1`, natural numbers ($0 - 1$ is $0$). `eps`, `term` and `tau` are exact expressions
  in the language of `const up( )` (over `u`, `eta`, integers and `^`), and `instances` gives them
  per named format as exact fractions, one object per `fold_error` entry.
- `orders`: `sequential`, and `lanes`, whose claims hold for every number of lanes $W$;
  `packed_lanes` is the $W$ of the packed form, per format and backend.
- `step`, `combine` and `finish` are kernels of the list `"kernels"` (`combine` and `finish` may
  be `null`); `theorems` is, per order, `{"file": ..., "name": ...}` once the fold is proved and
  `null` before.
- **Reading, in the extended domain** (every fold of this stage). An element is any value that
  satisfies `requires` there: for one limb any value of the format, $\pm\infty$ or NaN; for two
  limbs a canonical pair. The flag is true exactly when limb 0 of the result is finite, and when
  it is false every limb of the result is a NaN ([When something is not
  finite](design/milestone2.md#sum-dot-axpy-convolution)). An element that is not finite, or an
  overflow anywhere, makes the flag false. When the flag is true every element is finite, and
  `normalized` and `fold_error` hold of the result. The sign of a zero is not part of a claim.

**Maps** are in the same list, with `"map": true`:

```json
{
  "name": "axpy_2", "map": true, "domain": "extended",
  "arrays": [{"name": "x", "limbs": 2, "role": "supplied"}, {"name": "y", "limbs": 2, "role": "stored"}],
  "scalars": [{"name": "a", "limbs": 2, "role": "supplied"}],
  "writes": [{"name": "z", "limbs": 2}],
  "outputs": [{"name": "finite", "limbs": 1, "type": "mask"}],
  "value": "a*x+y",
  "requires": ["canonical(a)", "canonical(x)", "canonical(y)"],
  "ensures": [{"kind": "entries", "of": "z", "kernel": "axpy_step_2"},
              {"kind": "finite_or_nan", "of": "z", "flag": "finite"}],
  "orders": ["sequential", "lanes"],
  "packed_lanes": {"binary64": {"avx2": 4, "neon": 2}, "binary32": {"avx2": 8, "neon": 4}},
  "step": "axpy_step_2", "step_args": ["a", "x", "y"], "check": "fold_finish_2",
  "min_precision": 4, "status": "proved", "theorem": {"file": "proofs/theories/FoldMaps.v", "name": "axpy_2_correct"},
  "source": {"cite": "axpy_step_2 on each element", "license": "algorithm: published; proof: MIT"}
}
```

- `entries`, the claim kind of a map: every written element $z_i$ satisfies every `ensures` entry
  of the kernel `kernel` (the step), whose inputs are given, in order, the groups of `step_args`:
  the scalars, and element $i$ of each array. `value` is the step's value of those.
- **The map's `value` and `requires` are the step's**, a rule of the generator (`rules.map_rules`)
  that a reader may rely on: the map's `value` is the step's `value` with each input of the step
  renamed to the group of `step_args` at its position (`axpy_step_2(a, x, y)` has the value
  `a*x+y` over its own inputs `a`, `x`, `y`; a step `scale_step_1(x, a)` with `step_args`
  `["x", "a"]` gives `x*a`), as expressions, not only as values; and every requirement of the step on
  what the map passes is a requirement of the map, `normalized` read as `canonical`, `power_of_two`
  as it is. So the claims of `entries` are about exactly the operands the map's `requires` describe.
- `finite_or_nan` of a written array: the flag is true exactly when the leading limb of every
  written element is finite; when it is false, every element whose leading limb is not finite has
  every limb a NaN, and the others are as computed.
- **Reading, in the extended domain.** An element or a scalar is any value that satisfies
  `requires`: for one limb any value of the format, for two limbs a canonical pair. A written
  element whose leading limb is finite comes from finite operands and satisfies `entries`; one
  that is not finite (an operand not finite, or an overflow) is the canonical NaN. The order makes
  no difference: `F_seq`, `F_lanes` with any $W$ and `F_packed` write the same elements and the
  same flag.
- **What is a violation**, for a reader that judges a written element. A written element whose
  leading limb is finite and that has a lower limb that is not finite violates the claim: it is not
  canonical (`entries` includes `normalized` of the step, and the IEEE-model statement says that a
  finite leading limb means every limb finite). So does a written element whose leading limb is
  finite though a rounding inside the step overflowed, or though an operand is not finite: in the
  extended domain a finite leading limb claims finite operands and a computation in which nothing
  overflowed, so that the values are those the step computes without overflow (the IEEE-model
  statement: those of the real model) and the step's claims hold; a reader that cannot see inside
  the step judges this through those claims, `normalized` and `error`, in exact arithmetic. A
  written element that is not finite (the canonical NaN) from finite operands far below
  the overflow threshold violates nothing: a map claims nothing about when its elements are finite
  (it has no `finite_when`), so that is at most suspicious; the same holds of a coefficient of a
  convolution. The flag that is false while every element written is finite, or true while one is
  not, violates `finite_or_nan`.

**The folds of maxima** ([Folds of maxima](#folds-of-maxima)) and their kernels add one kind of
claim of a kernel, two fields of `finite_or_nan`, and one kind of claim of a fold:

| Kind | Fields | Meaning |
|---|---|---|
| `maximum` (a kernel, the finite domain) | `of` (a one-limb output), `args`: two expressions | the output is the larger of the exact values of the two expressions, which are expressions of the language of `value` in which `NAME[I]` is limb I of an input, as in `exact_when`: `{"kind": "maximum", "of": "r", "args": ["m", "abs(x[0])"]}` |
| `finite_or_nan` with `if` and `steps` (a kernel, the extended domain) | `if`: a mask input; `steps`: an integer $S \ge 1$ | let $t$ be `value` stepped up $S$ times ($S = 0$ when the field is absent), each step IEEE 754's nextUp (a NaN stays a NaN, $+\infty$ stays $+\infty$, $\Omega$ goes to $+\infty$, and $-\infty$ goes to $-\Omega$, the most negative finite number, which is finite: the table of `neighbor`). The flag is true exactly when the mask `if` is true and $t$ is finite; the output is then $t$; otherwise it is a NaN. `{"kind": "finite_or_nan", "of": "r", "flag": "flag", "if": "ok", "steps": 1}` |
| `upper` with `over` (a fold) | `of`, `over`: `max`, `steps`: an integer $S \ge 0$ | with $v_i$ the value of element $i$ and $V = \max_i v_i$ ($0$ for no element): $V \le r \le \mathrm{RU}(V)$ stepped up $S$ times, $\mathrm{RU}$ in the format with overflow (so that a $V$ above $\Omega$ makes the bound $+\infty$, and then no finite $r$ satisfies the first inequality). `{"kind": "upper", "of": "r", "over": "max", "steps": 1}` |

A fold with an `upper` entry has no `fold_error` entry, and its `instances` are empty lists. Its
reading in the extended domain is that of the other folds: the flag is true exactly when the
result is finite, and then every element is finite and the claim holds; a NaN or infinite element,
or a result whose step up is infinite, gives the flag false and a NaN. As a rule: **the flag is true
exactly when the leading limb of every element is finite and the largest of their magnitudes,
stepped up $S$ times, is finite**. So with finite elements the flag is false exactly when that step
up is $+\infty$: never for one limb ($S = 0$), and for two limbs ($S = 1$) exactly when a leading
limb is $\pm\Omega$ (the step up from $\Omega$ is $+\infty$). The proofs established it in this form
(for two limbs, the flag is true exactly when every leading limb is finite and the step up from the
largest is finite); the generator's tests check it in every order (`test_folds.py`, the folds of
maxima).

**Convolutions** ([Convolutions](#convolutions)) are in the list `"folds"` too, with `"conv":
true` (and no `"map"`):

```json
{
  "name": "conv_2", "conv": true, "domain": "extended",
  "arrays": [{"name": "x", "limbs": 2, "role": "supplied"}, {"name": "y", "limbs": 2, "role": "supplied"}],
  "writes": [{"name": "z", "limbs": 2}],
  "outputs": [{"name": "finite", "limbs": 1, "type": "mask"}],
  "value": "x*y",
  "requires": ["canonical(x)", "canonical(y)"],
  "ensures": [{"kind": "coefficients", "of": "z", "fold": "dot_2"},
              {"kind": "finite_or_nan", "of": "z", "flag": "finite"}],
  "orders": ["sequential"],
  "coefficients": "dot_2", "check": "fold_finish_2",
  "min_precision": 4, "status": "proved", "theorem": {"file": "proofs/theories/FoldConv.v", "name": "conv_2_correct"},
  "source": {"cite": "dot_2 on the terms of each coefficient", "license": "bound: published; proof: MIT"}
}
```

- `arrays` are the two polynomials, each of its own length, $n_x$ and $n_y$ (the line protocol
  gives both); `writes` has $n_x + n_y - 1$ entries, none when a length is $0$; `value` and
  `requires` are those of a term, of each entry of either array.
- `coefficients`, the claim kind of a convolution: written entry $j$, when its leading limb is
  finite, satisfies every `ensures` entry of the fold `fold` (here `dot_2`) other than
  `finite_or_nan`, in that fold's `sequential` order (its heights), on the list of the terms
  $(x_i, y_{j-i})$ for $i$ from $\max(0, j - n_y + 1)$ to $\min(j, n_x - 1)$, in increasing order:
  $n$ in its claims is the number of those terms, at most $\min(n_x, n_y)$.
- `finite_or_nan` and the reading in the extended domain are a map's: the flag is true exactly when
  the leading limb of every coefficient is finite; a coefficient that is not finite (a term not
  finite, or an overflow) is the canonical NaN, the others are as computed.

**Ball vectors** ([Ball vectors](#ball-vectors)) are in the list `"folds"` too, with `"bv": true`
(and no `"map"` or `"conv"`). Two entries as the generator writes them:

```json
{
  "name": "bv_add_2", "bv": true, "domain": "extended",
  "arrays": [{"name": "x", "limbs": 2, "role": "stored"}, {"name": "y", "limbs": 2, "role": "stored"}],
  "scalars": [{"name": "rx", "limbs": 1, "role": "stored"}, {"name": "ry", "limbs": 1, "role": "stored"}],
  "writes": [{"name": "z", "limbs": 2}],
  "outputs": [{"name": "r", "limbs": 1}, {"name": "finite", "limbs": 1, "type": "mask"}],
  "value": "x+y",
  "requires": ["ball_vector(x, rx)", "ball_vector(y, ry)"],
  "ensures": [{"kind": "encloses_entries", "center": "z", "radius": "r", "flag": "finite", "set": "x+y",
               "balls": {"x": {"center": "x", "radius": "rx"}, "y": {"center": "y", "radius": "ry"}},
               "finite_when": [{"abs_le": "abs(x+y)+rx+ry", "exp": -2}],
               "radii_when": [{"abs_le": "rx+ry", "exp": -2}]}],
  "orders": ["sequential", "lanes"],
  "packed_lanes": {"binary64": {"avx2": 4, "neon": 2}, "binary32": {"avx2": 8, "neon": 4}},
  "step": "add_2_2", "step_args": ["x", "y"], "record": "norm_step_2", "combine": "norm_combine",
  "radius": "bv_add_radius_2", "radius_args": ["m", "rx", "ry"], "finish": "norm_finish_1",
  "min_precision": 3, "status": "proved", "theorem": {"file": "proofs/theories/BvReal.v", "name": "bv_add_2_correct"},
  "source": {"cite": "add_2_2 on the centers, the radius of ball_add_2 at the largest center (milestone2.md, BallVector)",
             "license": "algorithm and proof: MIT"}
},
{
  "name": "bv_scale_1", "bv": true, "domain": "extended",
  "arrays": [{"name": "x", "limbs": 1, "role": "stored"}],
  "scalars": [{"name": "rx", "limbs": 1, "role": "stored"}, {"name": "a", "limbs": 1, "role": "supplied"}],
  "writes": [{"name": "z", "limbs": 1}],
  "outputs": [{"name": "r", "limbs": 1}, {"name": "finite", "limbs": 1, "type": "mask"}],
  "value": "x*a",
  "requires": ["ball_vector(x, rx)"],
  "ensures": [{"kind": "encloses_entries", "center": "z", "radius": "r", "flag": "finite", "set": "x*a",
               "balls": {"x": {"center": "x", "radius": "rx"}},
               "finite_when": [{"abs_le": "(abs(x)+rx)*a", "exp": -2}],
               "radii_when": [{"abs_le": "rx*a", "exp": -2}], "finite_from": 2}],
  "orders": ["sequential", "lanes"],
  "packed_lanes": {"binary64": {"avx2": 4, "neon": 2}, "binary32": {"avx2": 8, "neon": 4}},
  "step": "scale_step_1", "step_args": ["x", "a"], "record": "norm_step_1", "combine": "norm_combine",
  "radius": "bv_scale_radius_1", "radius_args": ["m", "rx", "a"], "finish": "norm_finish_1",
  "min_precision": 1, "status": "proved", "theorem": {"file": "proofs/theories/BvReal.v", "name": "bv_scale_1_correct"},
  "source": {"cite": "mul_1_1 on the centers, the radius of ball_scale_1 at the largest center (milestone2.md, BallVector)",
             "license": "algorithm and proof: MIT"}
}
```

- `arrays` are the centers of the operands, one array per BallVector, all of the length $n$;
  `scalars` are given once: the radii of the operands and any other operand of `T`; `writes` is the
  centers of the result, $n$ of them; `outputs` are its radius and the flag.
- **`ball_vector(ARRAY, RADIUS)`**, a requirement: the entries of ARRAY and the scalar RADIUS are a
  canonical BallVector: either every entry finite (a finite normalized pair for two limbs) and RADIUS
  finite and nonnegative, or every entry zero (every limb a zero) and RADIUS $= +\infty$, the whole
  space. A scalar with no requirement (`a` of `bv_scale_k`) is any value of the format, $\pm\infty$
  or NaN.
- **`encloses_entries`**, the claim of a ball vector, `center` the array written, `radius` and
  `flag` the outputs, `set` an expression over the ball names and the other scalars (the language of
  `value`), `balls` for each ball name its `center` (an array read) and `radius` (a scalar), and
  `finite_when` a list of conditions `{"abs_le": EXPR, "exp": E}` as for `encloses`, EXPR over the
  arrays' names (an entry's value) and the scalars', and `radii_when` a list of the same conditions
  with EXPR over the scalars' names alone (the radii and the other scalars), present exactly when
  `finite_when` is not empty. For canonical operands:
    - **V1**: the result is canonical: a finite ball vector (`radius` finite and nonnegative, every
      entry written finite and, for two limbs, normalized) or the whole space (`radius` $= +\infty$,
      every limb of every entry written a zero);
    - the flag is true exactly when `radius` is finite;
    - **V2**, containment, entry by entry: for every $i$, every value of `set` with each ball name
      ranging over the reals within its radius of entry $i$ of its center (every real, for an
      operand that is the whole space) and each other scalar its value is within `radius` of entry
      $i$ written; for the whole space, trivially;
    - **V3**: if the result is a finite ball vector, every operand is one and every scalar is
      finite;
    - **V4**, for every $n$, $0$ included: if every operand is a finite ball vector, every scalar is
      finite, the scalars satisfy every condition of `radii_when` ($\lvert$EXPR$\rvert \le 2^{q_{\max}
      + p + E}$, EXPR evaluated on the scalars), and every entry $i$ satisfies every condition of
      `finite_when` (EXPR evaluated on the values of entry $i$ of the arrays and on the scalars), the
      result is a finite ball vector. For $n = 0$ only `radii_when` is a condition. An empty
      `finite_when` (and so no `radii_when`) claims nothing about when the result is finite. At any
      entry the conditions of `finite_when` imply those of `radii_when`: for `bv_add_2`,
      $\lvert x + y\rvert + r_x + r_y \ge r_x + r_y$, and for `bv_scale_1`,
      $(\lvert x\rvert + r_x)\lvert a\rvert \ge r_x\lvert a\rvert$. (Until 2026-11-20 V4 was stated
      for $n \ge 1$ only and `radii_when` did not exist.)
    - **`finite_from`**, an integer, written after `radii_when` and only in an entry that has it
      (`bv_add_1`, `bv_sub_1`, `bv_scale_1`: `"finite_from": 2`): the precision from which V4 is
      claimed, above the fold's `min_precision`. V1 to V3 and the flag are claimed from `min_precision`,
      V4 from `finite_from` (from `min_precision` when there is none). A reader judges V4 only in
      formats of at least that precision.

**From which precision each clause holds.** The statements quantify over every `emax` above the
precision (`binary_float` asks $p < e_{\max}$; V4 is claimed in those formats only, [The formats
of the statements](#number-formats)), so the smallest format of precision $p$ has
$e_{\max} = p + 1$: the finite numbers below $2^{p+1}$. V1 to V3 and the flag hold from the fold's
minimum precision, whatever the constants: a constant of the radius kernel that overflows is
$+\infty$ in the IEEE model, so the radius it enters is $+\infty$ or a NaN (an FMA of $+0$ and
$+\infty$), the finish returns the whole space with the flag false, and V1 (the whole space is
canonical), the flag, V2 (the whole space contains every set) and V3 (its premise is a finite result)
hold of it. V4 alone promises a finite result, so it needs every constant of the fold's kernels to be
finite in the smallest format: at precision 1, $e_{\max} = 2$ (the finite numbers $0$, $1$, $2$),
`up((1+u)^3)` of `bv_add_radius_1` and `bv_scale_radius_1` is $27/8$ rounded up, $4 = 2^{e_{\max}}$,
and so is `up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u))`: `bv_add_1` of one entry $(+0, +0)$ with the radii
$+0$ meets every premise of V4 and returns the whole space. The rules check it
(`rules._finite_from`): from the precision V4 is claimed from, every constant of the fold's step,
records, radius and finish (and of the bound, the coefficients' step and check of a product of
BallVectors), their callees included, must be a finite number of the smallest format of that
precision; otherwise the description must say `finite_from=P`. The precisions:

| Ball vectors | V1 to V3, the flag | V4 |
|---|---|---|
| `bv_add_1`, `bv_sub_1`, `bv_scale_1` | 1 | 2 (`finite_from=2`) |
| `bv_neg_1`, `bv_neg_2` (no constant) | 1 | 1 |
| `bv_make_1`, `bv_make_2` (`makes_ball_vector`: the whole space exactly when, no constant) | 1 | 1 |
| `bv_scale_2`, `bv_mul_pow2_1`, `bv_mul_pow2_2` | 2 | 2 |
| `bv_add_2`, `bv_sub_2` | 3 | 3 |
| `bv_conv_1`, `bv_conv_2` | 4 | 4 |

The tests of V4 (`test_bv.py`, `test_bv_conv.py`) run, besides their toy formats, the smallest format
of the precision V4 is claimed from ($e_{\max} = p + 1$); below `finite_from` the interpreter refuses
the format, whose constant overflows (an `InterpError`), and `test_bv.Interp.test_v4_is_false_at_precision_1`
checks that overflow. (Until 2026-11-20 V4 of the three was claimed from precision 1, which is false.)

    - **Exact**, with `"exact_when": []` (written last, only in an entry that has it: `bv_neg_k`, the
      word `exact` of the description): if the result is a finite ball vector, it is exactly the set,
      entry by entry: besides V2, every real within `radius` of entry $i$ written is a value of `set`
      with each ball name at some real within its radius of entry $i$ of its center. The list is
      that of the conditions of `exact_when` of `encloses`, and the empty list always holds.
    - **Exact under conditions**, with `"exact_when": [CONDITION, ...]`, a list that is not empty
      (`bv_mul_pow2_k`), written last like the empty list. Each condition is
      `{"zero_or_abs_gt": EXPR, "than": K}` or `{"zero_or_abs_ge": EXPR, "than": K}`, as for `encloses`
      ([the conditions of `exact_when`](#claims-of-milestone-2), below the table of `neighbor`): EXPR $= 0$
      or $\lvert\mathrm{EXPR}\rvert > K$ (or $\ge K$), K an exact positive expression over `u`, `eta` and
      integers, EXPR an expression of the language of `value` over the arrays' names (the exact value of
      an entry, the sum of its limbs), their limbs `NAME[I]` (limb I of the entry, the leading limb
      `NAME[0]`) and the scalars' names. A condition whose EXPR names an array is **a condition of an
      entry**, evaluated at each entry $i$ on the limbs of entry $i$ and on the scalars; one whose EXPR
      names scalars only is **a condition of the scalars**. The claim: if the result is a finite ball
      vector, every condition of the scalars holds, and every entry satisfies every condition of an
      entry, then the result is exactly the set at every entry, as for the empty list. One entry that
      fails its conditions takes the exactness from every entry (the radius is one for all), so nothing
      is claimed then beyond V1 to V4; for $n = 0$ nothing is claimed beyond them either. For
      `bv_mul_pow2_2` the conditions are `x[0]*c` and `x[1]*c` (of an entry) and `rx*c` (of the
      scalars), each zero or above $N = \eta/(2u)$ in magnitude: when they hold the centers written are
      $c\,x_i$ and the radius $c\,r_x$, exactly. A reader judges it by computing, in exact arithmetic,
      whether every condition holds, and if so whether $[z_i - r, z_i + r]$ is exactly the exact range of
      `set` over the operands' balls at every entry (for a product by a positive $c$, the endpoints
      $c(x_i \mp r_x)$).

    What is claimed of the one radius is that and nothing more: containment (V2) and when it is
    finite (V4). That it is the largest of the $n$ radii the entrywise Ball kernel (`ball_add_k`,
    `ball_sub_k`, `ball_scale_k`) returns, and so no larger than the radius of $N$ balls, is what
    the listing computes and what the generator's tests find, and is not a claim: no claim names
    another kernel's computation.
- `step`, `step_args`, `record`, `combine`, `radius`, `radius_args` and `finish` name the parts:
  the step on the scalars and arrays of `step_args`, the record and the combination of the state
  `m, ok`, the radius kernel on `radius_args` (`m`, the limb of the state, then scalars), the finish.
  They are for reading; the oracle judges the claim. A ball vector exact under conditions also has
  `"exactness": {"mask": "e", "state": "ex"}`, after `record` and only there: the step's second
  output `e` (the mask that its entry is exact, claimed by the step's `exact_flag`) and-ed over the
  entries into the state's mask `ex`, which `radius_args` names after `m`.
- **`power_of_two(SCALAR)`**, a requirement of a scalar the program supplies (`c` of `bv_mul_pow2_k`):
  the scalar is a positive power of two of the format, finite, $c = 2^k$, as for a map; no other value
  is a valid operand.
- In the extended domain, as for a map: the order makes no difference, `F_seq`, `F_lanes` with any
  $W$ and `F_packed` write the same centers and return the same radius and flag.

**The products of two BallVectors** `bv_conv_1` and `bv_conv_2` ([the product of
polynomials](#ball-vectors)) are in the list `"folds"` with `"bv_conv": true` (and no `"bv"`, `"conv"`
or `"map"`: their requests have two lengths, and two radii). The entry of `bv_conv_2` as the generator
writes it (`source` left out):

```json
{
  "name": "bv_conv_2", "bv_conv": true, "domain": "extended",
  "arrays": [{"name": "x", "limbs": 2, "role": "stored"}, {"name": "y", "limbs": 2, "role": "stored"}],
  "scalars": [{"name": "rx", "limbs": 1, "role": "stored"}, {"name": "ry", "limbs": 1, "role": "stored"}],
  "writes": [{"name": "z", "limbs": 2}],
  "outputs": [{"name": "r", "limbs": 1}, {"name": "flag", "limbs": 1, "type": "mask"}],
  "value": "x*y",
  "requires": ["ball_vector(x, rx)", "ball_vector(y, ry)"],
  "ensures": [{"kind": "encloses_coefficients", "center": "z", "radius": "r", "flag": "flag", "set": "x*y",
               "balls": {"x": {"center": "x", "radius": "rx"}, "y": {"center": "y", "radius": "ry"}},
               "finite_when": [{"abs_le": "n*(abs(x)+rx)*(abs(y)+ry)", "exp": -2}, {"abs_le": "(abs(x)+rx)*ry", "exp": -2},
                               {"abs_le": "(abs(y)+ry)*rx", "exp": -2}],
               "radii_when": [{"abs_le": "rx*ry", "exp": -2}],
               "count_when": [{"le": "n*(unit(mul_2_2)+eta/(2*u))", "than": "1/16"}]}],
  "orders": ["sequential"],
  "centers": "conv_2", "records": ["norm_step_2", "norm_step_2"], "count": "min(n_x,n_y)", "bound": "bound_dot_2",
  "radius": "conv_radius", "radius_args": ["ma", "mb", "rx", "ry", "m", "g", "t"], "finish": "bv_conv_finish",
  "min_precision": 4, "status": "proved", "theorem": {"file": "proofs/theories/BvConv.v", "name": "bv_conv_2_correct"}
}
```

- `arrays` are the two polynomials, the centers of two BallVectors $X$ of $n_x$ entries and $Y$ of $n_y$,
  each of its own length (the line protocol gives both); `scalars` their radii; `writes` the $n_z = n_x +
  n_y - 1$ coefficients of the product, none when a length is $0$; `outputs` its radius and the flag.
  `ball_vector(ARRAY, RADIUS)` as for the other ball vectors.
- **`encloses_coefficients`**, `center` the array written, `radius` and `flag` the outputs, `set` an
  expression of the ball names (the value of a term, `x*y`), `balls` for each ball name its array and
  radius. For canonical operands:
    - **V1**: the result is canonical, a finite ball vector or the whole space (every limb of every
      coefficient a zero, the radius $+\infty$), of $n_z$ coefficients;
    - the flag is true exactly when `radius` is finite;
    - **V2**, coefficient by coefficient: for all reals $x_i$ within $r_x$ of entry $i$ of $X$ and $y_k$
      within $r_y$ of entry $k$ of $Y$, each chosen independently (for an operand that is the whole
      space, any reals), coefficient $j$ of their product, $\sum_i x_i y_{j-i}$ over $i$ from $\max(0, j -
      n_y + 1)$ to $\min(j, n_x - 1)$, is within `radius` of coefficient $j$ written. Each entry occurs
      once in a coefficient, so a reader computes the exact range of that sum as the sum of the ranges
      of its products (each the least and the greatest of the four products of the ends of the two
      balls) and checks it against $[z_j - r, z_j + r]$;
    - **V3**: if the result is a finite ball vector, both operands are (finite radii);
    - **V4**: if both operands are finite ball vectors, every condition of `count_when` holds, every
      condition of `radii_when` holds, and every condition of `finite_when` holds where it applies, the
      result is a finite ball vector. A condition `{"abs_le": EXPR, "exp": E}` is $\lvert
      \mathrm{EXPR}\rvert \le 2^{q_{\max} + p + E}$, EXPR in the language of `value` over the arrays'
      names (the exact value of an entry), the scalars' names and **`n`**, the count $\min(n_x, n_y)$, an
      integer. It applies at **every pair of entries** $(x_i, y_k)$, $0 \le i < n_x$, $0 \le k < n_y$,
      when EXPR names both arrays (every such pair is a term of coefficient $i + k$); at every entry of
      one array when it names that array only; once when it names neither (`radii_when` names scalars
      only). A condition of **`count_when`**, `{"le": EXPR, "than": K}`, is EXPR $\le$ K, EXPR an exact
      expression over `n`, `u`, `eta`, integers and `unit(K)`, `tiny(K)` of a kernel's bound, K a positive
      rational: here $n\,(4u^2 + \eta/(2u)) \le \tfrac1{16}$, $\eta/(2u)$ the smallest normal number
      (for `bv_conv_1`, $n\,(u/(1+u) + \eta) \le \tfrac1{16}$, `unit(mul_1_1)` $= u/(1+u)$), which makes the
      count $n$ rounded up a number of the format and the bound of `dot` for that many terms given
      (`bound_dot_k`'s mask true). For $n_x = 0$ or $n_y = 0$
      there is no pair, and the conditions of the other array and of the radii are the whole of V4.
  `finite_when`, `radii_when` and `count_when` are present together or not at all.
- `centers` (the convolution of the centers, an entry of the list with `"conv": true`), `records`,
  `count`, `bound`, `radius`, `radius_args` (the maxima `ma`, `mb` of the records, the radii, the count
  `m`, the bound's `g` and `t`) and `finish` name the parts, for reading; the oracle judges the claim.
- The order makes no difference: there is one, `sequential`, and no packed form.

Two new forms in the entries of their kernels:

- **`at_most(NAME, K)`**, a requirement of `conv_radius`: the one-limb input NAME is at most the positive
  integer K (`at_most(g, 1)`: the bound of `dot` is at most 1, which `bound_dot_k` gives when its mask is
  true). A reader draws no operand beyond it. In the formal model, `g <= 1`.
- **`finite_or_nan` with `if_all`**, `{"kind": "finite_or_nan", "of": "r", "flag": "flag", "if_all": ["okc",
  "okg"]}`, of `bv_conv_finish`: as `finite_or_nan` with `if` of one mask, with the list of two mask inputs
  or more: the flag is true exactly when every mask of the list is true and the value is finite, and the
  output is then the value; otherwise a NaN. The field is written only where it is, without `if`, `steps`
  or `nonneg`.

**The constructors** `bv_make_1` and `bv_make_2` are ball vectors too (`"bv": true`), with one array of
the centers given and one scalar, the radius given, both `supplied` for one limb (`bv_make_2` reads its
centers `stored`: they are `Expansion<T, 2>`), and a claim of a kind of their own:

```json
{"kind": "makes_ball_vector", "center": "z", "radius": "rr", "flag": "finite", "from": {"center": "c", "radius": "r"}}
```

- **`makes_ball_vector`**, `center` the array written, `radius` and `flag` the outputs, `from` the array
  read (the centers given) and the scalar (the radius given). `requires` is empty for one limb, where a
  center is any value of the format, and `canonical(c)` for two limbs; the radius is any value of the
  format. The result is canonical (V1 above). The flag is true exactly when the radius returned is
  finite. The result is the whole space (every limb of every center written a zero, the radius
  $+\infty$, the flag false) exactly when the radius given is negative, a NaN or $+\infty$ (so $-\infty$
  too), or the leading limb of a center given is not finite. Otherwise the centers written are those
  given, limb for limb, and the radius is the radius given, as values: the sign of a zero is not part
  of the claim (a center or a radius of $-0$ comes out as $+0$ for one limb, through the guard).
- **`finite_or_nan` with `nonneg`**, `{"kind": "finite_or_nan", "of": "r", "flag": "flag", "if": "ok",
  "nonneg": true}`, of `bv_make_finish`: as `finite_or_nan` with `if`, and the value must also not be
  negative: the flag is true exactly when the mask `if` is true, the value is finite and it is not below
  zero (either zero is not); the output is then the value, otherwise a NaN. The field is written only
  where it is true, with `if` and without `steps`.

The other kernels of the constructors claim kinds that exist: `bv_center_entry_1` (`guard(c)`) and
`bv_make_radius` (`rz = guard(r) + (m - m)`, value `r`) claim `rounded` to nearest of their value,
which is the value itself, in the finite domain; `bv_center_2` (a copy) claims what `neg_2` claims with
the value `x`.

The radius kernels are kernels with an entry `upper` with a value of its own, as the bound kernels
are, whose value may hold `abs( )` of an input (`abs(a)*rx`), now in the language of that value:
`bv_add_radius_2` claims `{"kind": "upper", "of": "rz", "value":
"rx+ry+m*unit(add_2_2)/(1-unit(add_2_2))*(1+u)"}` (for one limb `unit(add_1_1)`, without the
$(1+u)$), and `bv_scale_radius_1` `{"kind": "upper", "of": "rz", "value":
"abs(a)*rx+m*unit(mul_1_1)/(1-unit(mul_1_1))+tiny(mul_1_1)/(1-unit(mul_1_1))"}` (for two limbs
with `mul_2_1` and the factor $(1+u)$ on `m`), with the requirements `nonneg(m)`, `nonneg(rx)`
(and `nonneg(ry)`), in the finite domain.

Two things in those entries are new forms, which a reader of the claims must learn. The entry has a
`value` and **no `if`**: no mask is named, and the claim holds unconditionally (under the
requirements): the output is at least the exact value of `value`, whether it is finite or the
rounding has overflowed to $+\infty$. Nothing is said of how far above. (Not of `conv_radius`,
whose claim is of finite results, by the ruling of 2026-11-21: a result of it that is not
finite is $+\infty$ or a NaN, [Claims of the non-finite layer](#claims-of-the-non-finite-layer).)
And `value` may hold `abs(X)` of an input `X`, its exact magnitude.

**The kernels of the scaling of a BallVector by a power of two** (`bv_mul_pow2_k`) add three fields, each
written only in an entry that has it, in the finite domain:

| Field | Of | Meaning |
|---|---|---|
| `exact_flag`: a mask output | an `error` entry with `exact_when` | the mask output is true exactly when every condition of the entry's `exact_when` holds (and then, by `exact_when`, the output is `value` exactly); like the rest of the entry, it holds where output limb 0 is finite |
| `unless`: a mask input | an `upper` entry with `value` and without `if` or `gaps` | when the mask input is false, the output is at least the exact value of `value`; when it is true, the entry says nothing |
| `exact_when`: a list of conditions | an `upper` entry with `value` and without `if`, `gaps` or `unless` | the output is at least `value`, as without the field, and equals it exactly when every condition holds |

and one condition of `exact_when`, **`{"mask": NAME}`**, in the `exact_when` of an `upper` entry only:
NAME is a mask input, and the condition holds when it is true. The two steps and the radius, as the
generator writes them:

```json
{"kind": "error", "of": "z", "form": "R", "c": "0", "k": 2, "t": "1", "when": null,
 "exact_when": [{"zero_or_abs_gt": "x[0]*c", "than": "eta/(2*u)"}, {"zero_or_abs_gt": "x[1]*c", "than": "eta/(2*u)"}],
 "exact_flag": "e"}
{"kind": "upper", "of": "rz", "value": "rx*c",
 "exact_when": [{"mask": "ex"}, {"zero_or_abs_gt": "rx*c", "than": "eta/(2*u)"}]}
{"kind": "upper", "of": "rz", "value": "rx*c+eta", "unless": "ex"}
```

The first is of `bv_mul_pow2_step_2` (with `normalized z` before it; `bv_mul_pow2_step_1` has `rounded z
nearest` and the error `t=1/2` with the one condition `x*c`), whose outputs are the center `z` and the
mask `e`; the others are the two entries of `bv_mul_pow2_radius`, whose inputs are `m`, the mask `ex`, `rx`
and `c`, and which requires `nonneg(m)`, `nonneg(rx)`, `power_of_two(c)`. A reader judges them as the
other entries of their kinds: the mask `e` against the conditions, evaluated exactly on the input limbs
($x_1 c = 0$ or $\lvert x_1 c\rvert > \eta/(2u)$, $\eta/(2u)$ the smallest normal number of the format);
`rz` against $r_x c$ always, against $r_x c + \eta$ when the input `ex` is `0`, and for equality with $r_x
c$ when `ex` is `1` and the condition on $r_x c$ holds. In the formal models: `(e = true <-> CONDITIONS)`,
`(ex = false -> rx * c + eta emin <= rz)`, and `(ex = true /\ CONDITIONS -> rz = rx * c)` after `rx * c <= rz`.

### Claims of the interval kernels

The first kernels of the interval work ([Interval kernels](design/milestone2.md#interval-kernels):
the kernels of one limb, the bounds of two limbs and the sum of intervals of two limbs; and from
[One enclosure interface](design/milestone2.md#one-enclosure-interface) the bounds of a ball as
numbers of `T`, the ball from an interval of two `T` and the narrowing of a ball of two limbs)
need the additions below. Everything above keeps its meaning and its JSON shape: a field that is
new to a kind that exists is written only in an entry that uses it.

Three listings differ from the page's in form, not in value, because the generator refuses the
negation of a fused result, directly or through a select (gen/README.md, "The rules"): the lower
bound of `mul_dir_2_2` is $\mathrm{RD}(z_1 - d)$ written as $-\mathrm{RU}(d - z_1)$
(`nz = neg(z1); t = add_up_1(d, nz); wl = neg(t)`); the lower bound of `add_down_2_2`, and so of
`sub_down_2_2`, which calls it, is $\mathrm{RD}(z_1 - dd)$ written the same way
(`nz = neg(z1); t = add_up_1(dd, nz); w = neg(t)`), $dd$ being the select of the radius or zero;
and the radius of `ball_from_interval_2` adds minus the lower half as its own exact product of
the negated guarded bound (`gn = neg(gl); hn = prod(gn, const up(1/2)); d = add_up_1(hu, hn)`).
Rounding to nearest is symmetric, so all three are the page's values, and their claims and
statements are those of the page.

**Requirements**, both of the extended domain:

- `interval(L, U)`: the input groups L and U, of one limb each or of two each, are the bounds of a
  canonical interval ([Values of an interval](design/milestone2.md#values-of-an-interval)): the
  **empty set**, L $= +\infty$ and U $= -\infty$ (for two limbs $(+\infty, \pm 0)$ and
  $(-\infty, \pm 0)$), or a **nonempty interval**: neither bound is a NaN, L $\le$ U as extended
  real numbers, L $< +\infty$, U $> -\infty$, and each bound is a number of the format or an
  infinity (for two limbs: canonical, so a finite normalized pair or $(\pm\infty, \pm 0)$). Its
  *members* are the real numbers $x$ with L $\le x \le$ U: $[1, +\infty]$ does not contain
  $+\infty$, and the empty set has none. It is *bounded* when both bounds are finite.
- `not_nan(NAME)`: the one-limb input is not a NaN (an infinity is allowed).

**Ensures:**

| Kind | Fields | Meaning |
|---|---|---|
| `makes_interval` | `lower`, `upper`: the outputs; `from`: the inputs given as `lower` and `upper` | the output is a canonical interval, and with lo and hi the given bounds it is, by the first case that applies: the whole line $(-\infty, +\infty)$ when lo or hi is a NaN, whatever the other, or when lo and hi are the same infinity, both $+\infty$ or both $-\infty$; otherwise the empty set when the bounds are reversed, lo $>$ hi; otherwise the interval of the given bounds, the same extended real numbers. [The case analysis](#the-constructors-on-every-pair-of-values) below gives every pair. (The same infinity twice gave the empty set, as in IEEE 1788, until the owner's decision of 2026-11-20, which made it the whole line, as a NaN bound is.) |
| `encloses_interval` | `lower`, `upper`: the outputs; `set`: an expression over interval names; `intervals`: for each name its `lower` and `upper` inputs; `tight`; `bounded_when`: a list of conditions; `bounded_exactly`: `true`, only when it is so | I1 to I5 below |
| `set_bound` | `of` (a one-limb output), `side`: `below` or `above`, `set` and `balls` as in `encloses`, `tight` (optional): `{"kind": "rounded"}`, with an optional `steps` | if a ball operand is empty the output is $+\infty$ (`below`) or $-\infty$ (`above`); otherwise it is at most (at least) every value of `set`, each ball name ranging over the members of its ball: below or at the set's greatest lower bound $t$, an extended real number, $-\infty$ for a set that is unbounded below. With `tight`, the output is $t$ rounded down (up) in the format with overflow, or, with `steps` $s$, between that rounding stepped $s$ times outward and the rounding |
| `outward` | `of` (a 2-limb output), `side`: `below` or `above`, `rel`, `abs`: constants (below); `exact_when` (optional) | the output is on that side of `value`, and $\lvert\text{output} - \text{value}\rvert \le \mathrm{rel}\cdot\lvert\text{value}\rvert + \mathrm{abs}$; when every condition of `exact_when` holds, the output equals `value`. Of the finite domain: it holds whenever the requirements hold and the output's leading limb is finite |
| `encloses`, with `"balls": {}` | as before | the operands are points: $\lvert \text{set} - \text{center}\rvert \le$ radius, `set` an expression over the inputs. Of the finite domain only |
| `makes_ball`, from an interval | `center`, `radius`; `from`: the inputs given as `lower` and `upper` (one limb each); `midpoint_when` (optional): a list of conditions `{"half_in_format": NAME}`, NAME/2 is a number of the format | the output ball is canonical, and with lo and hi the given bounds it is, by the first case that applies: the whole line when lo or hi is a NaN, whatever the other, or when lo and hi are the same infinity; otherwise the empty set when the bounds are reversed, lo $>$ hi; otherwise (lo $\le$ hi) the whole line when a bound is infinite (a ball cannot be a half-line), and when both are finite a finite ball that contains $[lo, hi]$, whose center is $(lo + hi)/2$ exactly and radius $(hi - lo)/2$ rounded up when every condition of `midpoint_when` holds. [The case analysis](#the-constructors-on-every-pair-of-values) below gives every pair. (The same infinity twice gave the empty set until the owner's decision of 2026-11-20.) |
| `bound`, `rounded`, with `"zero_factor": true` | as before, `value` the product of two one-limb inputs, the extended domain | when an operand is a zero, the output is a zero (0 · ∞ = 0: the product of two bounds in interval arithmetic); otherwise as without the field |

The **I1 to I5** of `encloses_interval`, for canonical operands; $Z$ is the output interval. The
*exact range* is the set of the values of `set` with each interval name ranging over the members
of its interval, and $lo$, $hi$ are its greatest lower bound and least upper bound as extended
real numbers. For the sets of these kernels they are the sums and differences of bounds, the
opposites of the bounds exchanged for `-x`, and for `x*y` the least and the greatest of the four
products of a bound of $x$ and a bound of $y$ taken with $0 \cdot \infty = 0$.

- **I1.** $Z$ is canonical. **I2.** $Z$ is empty exactly when an operand is.
- **I3.** For nonempty operands, $Z$'s lower bound is at most every member of the exact range and
  its upper bound at least every member (so an unbounded range gives the infinite bound).
- **I4**, for nonempty operands, by `tight`:
    - `{"kind": "exact"}`: $Z$'s bounds are $lo$ and $hi$;
    - `{"kind": "rounded"}`: $Z$'s lower bound is $lo$ rounded down in the format with overflow,
      its upper bound $hi$ rounded up (an infinite bound stays); with `"steps"` $s$, the lower
      bound is between that rounding stepped down $s$ times and that rounding, and symmetrically
      the upper one; with `"when": "product_large"` (a set `x*y`), exactly the roundings when
      each product of a finite bound of $x$ and a finite bound of $y$ is zero or at least
      $2^{2p-1}\eta$ in magnitude;
    - `{"kind": "outward", "rel": ..., "abs": ..., "exact_when": {"lower": [...], "upper": [...]}}`:
      for bounded operands and a bounded $Z$ with bounds of values $z_\ell$, $z_u$:
      $lo - z_\ell \le \mathrm{rel}\cdot\lvert lo\rvert + \mathrm{abs}$ and
      $z_u - hi \le \mathrm{rel}\cdot\lvert hi\rvert + \mathrm{abs}$; for bounded operands, when
      every condition of a side holds, that bound of $Z$ is that bound of the exact range; and an
      infinite bound of the exact range is that bound of $Z$.
- **I5.** For bounded operands, $Z$ is bounded when (with `bounded_exactly`, exactly when) every
  member $z$ of the exact range satisfies every condition of `bounded_when`:
  `{"abs_le": SET, "omega": true}` is $\lvert z\rvert \le \Omega$, `{"abs_le": SET, "exp": E}` is
  $\lvert z\rvert \le 2^{q_{\max} + p + E}$, SET being the entry's `set`. An empty list claims
  nothing.

**Conditions.** `exact_when` of `outward`, and of the outward `tight`, has one more kind,
`{"zero": EXPR}`: EXPR $= 0$, EXPR an expression of the language of `exact_when` over the inputs
(the zero rule of the directed sums: a sum whose exact value is zero is returned as zero, and so
is a bound of an interval sum whose exact bound is zero; for `tight`, EXPR is the bound of the
exact range written over the bounds of the operands, `xl+yl` for the lower bound of `x+y`).

**Constants of a claim**, `rel` and `abs`: the language of `const up(EXPR)` (`u`, `eta`,
integers, `unit(K)`, `tiny(K)`, the four operations and integer powers), and `up(EXPR)` inside,
the smallest number of the format not below EXPR (below $\eta$ it is $\eta$): the constant as the
format rounds it, so that a bound can name the constants $E$, $G$, $H$ of a radius. Each `up(EXPR)`
is a constant of a kernel with a real-model statement. The oracle evaluates them per format;
`instances` is unchanged: one object per `error` entry.

**An output group other than the first.** In the finite domain an entry without a mask whose
`of` is an output group other than the first holds whenever the requirements hold and that group's
leading limb is finite (the two bounds of `mul_dir_2_2` overflow apart; the second output of
`mul_dir_1`, of the extended domain, has the infinity that its claims say). No earlier kernel has
such an entry. An entry with a mask (`if=MASK`) is read by its mask, whatever output group it is
about: `upper t … if=ok` of `bound_dot_k` holds whenever the requirements hold, output limb 0 is
finite and `ok` is true.

Entries as the generator writes them (`source`, `flops` and the theorem fields left out; the
constants of `outward` are those of
[Bounds of two limbs](design/milestone2.md#bounds-of-two-limbs), $A$ and $B$ with the $E$, $G$,
$H$ of `ball_add_2` and the $\mathrm{rel}$, $\mathrm{tiny}$ of `add_2_2`):

```json
{"name": "interval_add_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 1}, {"name": "xu", "limbs": 1}, {"name": "yl", "limbs": 1}, {"name": "yu", "limbs": 1}],
 "outputs": [{"name": "zl", "limbs": 1}, {"name": "zu", "limbs": 1}],
 "requires": ["interval(xl, xu)", "interval(yl, yu)"],
 "ensures": [{"kind": "encloses_interval", "lower": "zl", "upper": "zu", "set": "x+y",
              "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}},
              "tight": {"kind": "rounded"}, "bounded_when": [{"abs_le": "x+y", "omega": true}],
              "bounded_exactly": true}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "interval_make_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "lo", "limbs": 1}, {"name": "hi", "limbs": 1}],
 "outputs": [{"name": "zl", "limbs": 1}, {"name": "zu", "limbs": 1}],
 "requires": [],
 "ensures": [{"kind": "makes_interval", "lower": "zl", "upper": "zu", "from": {"lower": "lo", "upper": "hi"}}],
 "min_precision": 1, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "mul_dir_1", "domain": "extended",
 "inputs": [{"name": "a", "limbs": 1}, {"name": "b", "limbs": 1}],
 "outputs": [{"name": "d", "limbs": 1}, {"name": "v", "limbs": 1}],
 "value": "a*b", "requires": ["not_nan(a)", "not_nan(b)"],
 "ensures": [{"kind": "bound", "of": "d", "side": "below", "steps": 1, "zero_factor": true},
             {"kind": "rounded", "of": "d", "mode": "down", "when": "product_large", "zero_factor": true},
             {"kind": "bound", "of": "v", "side": "above", "steps": 1, "zero_factor": true},
             {"kind": "rounded", "of": "v", "mode": "up", "when": "product_large", "zero_factor": true}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "add_ball_2_2",
 "inputs": [{"name": "x", "limbs": 2}, {"name": "y", "limbs": 2}],
 "outputs": [{"name": "z", "limbs": 2}, {"name": "d", "limbs": 1}],
 "value": "x+y", "requires": ["normalized(x)", "normalized(y)"],
 "ensures": [{"kind": "normalized", "of": "z"},
             {"kind": "error", "of": "z", "form": "R", "c": "3/(1-4*u)", "k": 2, "t": "0", "when": null},
             {"kind": "encloses", "center": "z", "radius": "d", "set": "x+y", "balls": {}}],
 "min_precision": 3, "status": "proved",
 "instances": {"binary64": [{"rel": "3/81129638414606645666991986180096", "abs": "0"}],
               "binary32": [{"rel": "1/93824969867264", "abs": "0"}]}},
{"name": "ball_lower_as_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "c", "limbs": 1}, {"name": "r", "limbs": 1}],
 "outputs": [{"name": "l", "limbs": 1}],
 "requires": ["ball(c, r)"],
 "ensures": [{"kind": "set_bound", "of": "l", "side": "below", "set": "x",
              "balls": {"x": {"center": "c", "radius": "r"}}, "tight": {"kind": "rounded"}}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

and the `ensures` of three more:

```json
[{"kind": "normalized", "of": "l"},
 {"kind": "outward", "of": "l", "side": "below",
  "rel": "(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)*(1+unit(add_2_2))/(1-u)",
  "abs": "2*(1+u)^2*(1/2*up((1+u)^3)*eta+up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)/(1-u)*tiny(add_2_2)",
  "exact_when": [{"zero": "x+y"}]}],
[{"kind": "encloses_interval", "lower": "zl", "upper": "zu", "set": "x*y",
  "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}},
  "tight": {"kind": "rounded", "steps": 1, "when": "product_large"},
  "bounded_when": [{"abs_le": "x*y", "omega": true}], "bounded_exactly": true}],
[{"kind": "encloses_interval", "lower": "zl", "upper": "zu", "set": "x+y",
  "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}},
  "tight": {"kind": "outward",
            "rel": "(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)*(1+unit(add_2_2))/(1-u)",
            "abs": "2*(1+u)^2*(1/2*up((1+u)^3)*eta+up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)/(1-u)*tiny(add_2_2)",
            "exact_when": {"lower": [{"zero": "xl+yl"}], "upper": [{"zero": "xu+yu"}]}},
  "bounded_when": [{"abs_le": "x+y", "exp": -2}]}]
```

those of `add_down_2_2`, `interval_mul_1` and `interval_add_2`. The other kernels:
`interval_sub_1` is `interval_add_1` with `x-y`; `interval_neg_1` has the set `-x`, `"tight":
{"kind": "exact"}` and `bounded_when` `abs_le(-x, omega)`, exactly; `add_up_2_2`, `sub_down_2_2`,
`sub_up_2_2` are `add_down_2_2` on their side and value, and `mul_dir_2_2` claims `normalized` of
`l` and `h` and `outward` of each, below and above, with the constants of `ball_mul_2` and
`mul_2_2` and no `exact_when`; `ball_from_interval_2` claims
`{"kind": "makes_ball", "center": "cw", "radius": "rw", "from": {"lower": "lo", "upper": "hi"},
"midpoint_when": [{"half_in_format": "lo"}, {"half_in_format": "hi"}]}`, with no `value`;
`mul_ball_2_2` is `add_ball_2_2` with the claims of `mul_2_2`;
`ball_upper_as_1` is `ball_lower_as_1` above. `ball_lower_as_2` and `ball_upper_as_2` claim
`set_bound` without `tight`, a bound on its side, and
`{"kind": "error", "of": "l", "form": "A", "c": "5", "k": 1, "t": "3", "when": null}` with the value
`c-r` (`c+r`): $\lvert l - (c - r)\rvert \le 5u(\lvert c\rvert + r) + 3\eta$. No number of steps
from the rounding of $c - r$ bounds that output when $c - r$ is much smaller than $c$ in
magnitude: the page's "less than one gap of `T` at $c$ plus one at the result" is a distance in
the gaps at $c$. `ball_narrow_2_1` claims `encloses` of the ball of its inputs, with
`finite_when` `abs_le(abs(c)+r, -2)`.

**In the formal models.** In the real model `outward` is the side, the bound and the exactness,
in the shape of the theorems of `proofs/theories/Directed2.v`, with each `up(EXPR)` of a constant
printed as its definition of `Model.v` applied to `emin prec`, and the constants in the forms of
that file's `outward_rel` and `outward_abs` ($1/X$ as Rocq's `/ X`, a `tiny(K)` that is zero as
`0`), so that a theorem stated with them has the statement as its type by unfolding them;
`encloses` without a ball is the
error bound by the radius; `zero_factor` and `not_nan` print nothing (a zero factor gives a zero
product, which `rounded` with `product_large` already says). In the IEEE model the statements use
`proofs/theories/IeeeIntervalVocabulary.v` (`interval_1`, `interval_empty_1`,
`interval_nonempty_1`, `in_interval_1`, `interval_bounded_1`, the two-limb forms, `xnonempty`,
`range_1`, `range_2`, `range_lower`, `range_upper`) in the shapes of the theorems of
`IeeeInterval1.v`; I4 with `tight` rounded, `steps` and `when` is the shape of
`interval_mul_1_tight_range`, with the condition `product_large` of that file unfolded. A
statement about intervals has a hypothesis on the precision only when its minimum is above 1.

#### The constructors on every pair of values

`makes_interval` and `makes_ball` from an interval, for every pair (lo, hi) of values of the
format. Each given bound is a NaN, $-\infty$, a finite number ($-0$ and $+0$ are both the number
0, so $[+0, -0]$ is $[0, 0]$), or $+\infty$; for two limbs (`interval_make_2`) each is a canonical
2-limb value: a NaN when its leading limb is a NaN (a canonical NaN is all NaN), an infinity when
its leading limb is one (followed by a zero of either sign), and otherwise the finite number
$\ell_0 + \ell_1$. Comparisons are of these extended real numbers, and a comparison with a NaN is
false. *The same infinity*: both $+\infty$ or both $-\infty$. *Reversed*: lo $>$ hi, neither a
NaN. With $a$ and $b$ finite:

| lo (row), hi (column) | NaN | $-\infty$ | $b$ | $+\infty$ |
|---|---|---|---|---|
| NaN | whole line | whole line | whole line | whole line |
| $-\infty$ | whole line | whole line (the same infinity) | $[-\infty, b]$ | $[-\infty, +\infty]$, the whole line |
| $a$ | whole line | empty set (reversed) | $[a, b]$ for $a \le b$; the empty set (reversed) for $a > b$ | $[a, +\infty]$ |
| $+\infty$ | whole line | empty set (reversed) | empty set (reversed) | whole line (the same infinity) |

That is the table of `makes_interval`. For `makes_ball` from an interval it is the same table with
every interval that is not empty and not bounded, $[-\infty, b]$, $[a, +\infty]$ and
$[-\infty, +\infty]$, made the whole line, and $[a, b]$ a finite ball that contains it: a ball
from an interval is the empty set exactly for reversed bounds, a finite ball exactly for finite
$a \le b$, and the whole line in every other case. The three conditions of the statements, *a
NaN or the same infinity*, *reversed*, and *neither* (lo $\le$ hi, lo $< +\infty$ and
hi $> -\infty$: a nonempty interval), are disjoint, and together they cover every pair. The
outputs: the whole line is $(-\infty, +\infty)$ for an interval of one limb,
$((-\infty, 0), (+\infty, 0))$ for one of two, and center $(0, 0)$ with radius $+\infty$ for a
ball of two limbs; the empty set is $(+\infty, -\infty)$, $((+\infty, 0), (-\infty, 0))$, and
every limb a NaN for a ball; each of these zeros may be of either sign. A finite bound of an
interval is returned as the same number, the sign of a zero not claimed; an infinite bound as that
infinity, for two limbs followed by a zero.

### Claims of the interval kernels: two limbs and the enclosure interface

The second stage of the interval work needs the additions below:
- from [Two limbs](design/milestone2.md#two-limbs), the negation, difference, constructor and product of intervals of two limbs and `mul_ext_2_2`;
- from [One enclosure interface](design/milestone2.md#one-enclosure-interface), the hull and the intersection of one limb and of two, and the midpoint and radius, the conversions and the split of an interval of one limb.

Everything above keeps its meaning and its JSON shape: a field that is new to a kind is written only in an entry that uses it.

**Requirements.** `not_nan(NAME)` may also name an input of two limbs that is required `canonical`. Its leading limb is then not a NaN, so the value is a finite normalized pair or $(\pm\infty, \pm 0)$: a bound of an interval of two limbs, as `mul_ext_2_2` takes it. In the IEEE model this is `~ nan x0`.

**Kinds that exist, read on two limbs or with a new field.**

- `makes_interval` whose `from` names inputs of two limbs, each required `canonical` (`interval_make_2`). The meaning is that of one limb, over the values of the 2-limb numbers ([the case analysis](#the-constructors-on-every-pair-of-values)): a bound is a NaN when its leading limb is one and an infinity when its leading limb is one, so that $(+\infty, 0)$ and $(+\infty, -0)$ are the same infinity twice, the whole line. The whole line is $((-\infty, 0), (+\infty, 0))$ and the empty set $((+\infty, 0), (-\infty, 0))$, the zeros of either sign. A finite bound is returned as given. An infinite bound is returned as $(\pm\infty, \pm 0)$.
- `encloses_interval` with bounds of two limbs and `"tight": {"kind": "exact"}` (`interval_neg_2`): I1 to I5 as above. Its I5 condition is `{"abs_le": "-x", "exp": 0}` with `bounded_exactly`, that is $\lvert z\rvert \le 2^{q_{\max}+p}$, the overflow threshold. Every finite canonical pair is below that threshold, so the condition says that a bounded operand gives a bounded result.
- `encloses_interval` with `"zero_factor": true` (`interval_mul_2`, whose `set` is a product of two interval names). It adds **I6**: for nonempty operands, when one operand is $[0, 0]$ (both bounds zero), $Z$ is $[0, 0]$, even when the other operand is unbounded ($0 \cdot \infty = 0$). The field comes after `bounded_when` and `bounded_exactly`. The tightness of the product is `outward`, with the constants of `mul_dir_2_2` and no `exact_when`; its I5 is `{"abs_le": "x*y", "exp": -2}`, not exactly.
- `outward` in the extended domain (`mul_ext_2_2`). The operands of several limbs are required `canonical` and `not_nan`, and the entry may carry `zero_factor` (the value is then the product of two inputs).
  - The output is never a NaN. That it is canonical is said by the kernel's `normalized` entries, read as in the extended domain: canonical always, normalized when every operand and the output are finite.
  - With `zero_factor`, a zero operand gives a zero output, every limb zero, whatever the other operand.
  - Otherwise, an infinite operand gives `value` as IEEE 754 defines it on the leading limbs: the infinity of the sign of the product, followed by a zero.
  - With every operand finite, the output is on its side of `value` as an extended real number: $-\infty$ is always below and $+\infty$ always above, which is what the kernel returns when `mul_dir_2_2` does not give a finite bound. When the output is finite, $\lvert\text{output} - \text{value}\rvert \le \mathrm{rel}\cdot\lvert\text{value}\rvert + \mathrm{abs}$, and `exact_when` reads as in the finite domain.

**New kinds**, for canonical operands:

| Kind | Fields | Meaning |
|---|---|---|
| `interval_set` | `lower`, `upper`: the outputs; `set`: `union` or `intersection`; `intervals`: two names, each with its `lower` and `upper` inputs (of an `interval` requirement) | $Z$ is canonical. The set is the real numbers that are members of $X$ or of $Y$ (`union`), or of both (`intersection`). $Z$ is empty exactly when the set has no member: for `union` when both operands are empty; for `intersection` when an operand is empty or the larger lower bound is above the smaller upper bound. Otherwise the bounds of $Z$ are the greatest lower bound and the least upper bound of the set, as extended real numbers: for the union, the smaller lower bound and the larger upper bound of the nonempty operands (the hull, the smallest interval that contains both); for the intersection, the larger lower bound and the smaller upper bound. Exact. |
| `ball_of_interval` | `center` (one limb or two) and `radius` (one limb): the outputs; `from`: the `lower` and `upper` inputs of an `interval` requirement; `special`: `ieee1788` or `ball`; `rel`, `abs`: constants of a claim; `smallest_radius` (optional): `true` | For a bounded $X = [\ell, h]$, with $m = (\ell + h)/2$: the center $c$ and the radius $r$ are finite, $\ell \le c \le h$, $\lvert c - m\rvert \le \mathrm{rel}\cdot\lvert m\rvert + \mathrm{abs}$, and $[c - r, c + r] \supseteq X$. With `smallest_radius`, $r$ is the smallest number of the format with that property, $\mathrm{RU}(\max(c - \ell, h - c))$. For an unbounded or empty $X$ the outputs depend on `special`. With `ieee1788` they are the values of `mid` and `rad` of IEEE 1788: the whole line gives $(0, +\infty)$, $[\ell, +\infty]$ with $\ell$ finite gives $(\Omega, +\infty)$, $[-\infty, h]$ gives $(-\Omega, +\infty)$, and the empty set gives two NaN. With `ball` they are a canonical ball: the whole line for every unbounded interval, the empty ball (every limb a NaN) for the empty set, and a finite ball for a bounded interval. With `ieee1788` and a center of two limbs, the center is also a canonical value of two limbs for every $X$ ([the conversions of two limbs](#claims-of-the-enclosure-interface-the-conversions-of-two-limbs)). |
| `interval_of_ball` | `lower`, `upper` (one limb each): the outputs; `set`, `balls`: as in `encloses`, one ball name of a `ball` requirement; `tight`: `{"kind": "rounded"}`, with optional `steps` | $Z$ is canonical, and empty exactly when a ball operand is empty. Every value of `set`, with each ball name ranging over the members of its ball, is a member of $Z$. For balls that are not empty, the lower bound of $Z$ is the set's greatest lower bound rounded down in the format with overflow, and its upper bound the least upper bound rounded up; with `steps` $s$, each is between that rounding and $s$ steps beyond it. The whole line gives $[-\infty, +\infty]$. |
| `splits` | `parts`: two objects, each with the `lower` and `upper` outputs of an interval; `from`: the `lower` and `upper` inputs of an `interval` requirement | Both parts are canonical intervals. If $X$ is empty, both are empty. Otherwise neither is: the first part's lower bound is $X$'s lower bound, the second part's upper bound is $X$'s upper bound, and the first part's upper bound equals the second part's lower bound, a point of $X$. Together the two parts are $X$. |

`rel` and `abs` of `ball_of_interval` are in the language of the constants of a claim (above). For the midpoint of one limb they are `u` and `eta`.

The oracle reads an interval of one limb in the line protocol as two limbs, the lower bound first. `interval_split_1` returns four limbs: the bounds of the first part, then those of the second.

Entries as the generator writes them (`source`, `flops` and the theorem fields left out):

```json
{"name": "interval_hull_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 1}, {"name": "xu", "limbs": 1}, {"name": "yl", "limbs": 1}, {"name": "yu", "limbs": 1}],
 "outputs": [{"name": "zl", "limbs": 1}, {"name": "zu", "limbs": 1}],
 "requires": ["interval(xl, xu)", "interval(yl, yu)"],
 "ensures": [{"kind": "interval_set", "lower": "zl", "upper": "zu", "set": "union", "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}}],
 "min_precision": 1, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "interval_mid_rad_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 1}, {"name": "xu", "limbs": 1}],
 "outputs": [{"name": "m", "limbs": 1}, {"name": "r", "limbs": 1}],
 "requires": ["interval(xl, xu)"],
 "ensures": [{"kind": "ball_of_interval", "center": "m", "radius": "r", "from": {"lower": "xl", "upper": "xu"}, "special": "ieee1788", "rel": "u", "abs": "eta", "smallest_radius": true}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "ball_to_interval_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "c", "limbs": 1}, {"name": "r", "limbs": 1}],
 "outputs": [{"name": "zl", "limbs": 1}, {"name": "zu", "limbs": 1}],
 "requires": ["ball(c, r)"],
 "ensures": [{"kind": "interval_of_ball", "lower": "zl", "upper": "zu", "set": "x", "balls": {"x": {"center": "c", "radius": "r"}}, "tight": {"kind": "rounded"}}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "interval_split_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 1}, {"name": "xu", "limbs": 1}],
 "outputs": [{"name": "al", "limbs": 1}, {"name": "au", "limbs": 1}, {"name": "bl", "limbs": 1}, {"name": "bu", "limbs": 1}],
 "requires": ["interval(xl, xu)"],
 "ensures": [{"kind": "splits", "parts": [{"lower": "al", "upper": "au"}, {"lower": "bl", "upper": "bu"}], "from": {"lower": "xl", "upper": "xu"}}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "interval_make_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "lo", "limbs": 2}, {"name": "hi", "limbs": 2}],
 "outputs": [{"name": "zl", "limbs": 2}, {"name": "zu", "limbs": 2}],
 "requires": ["canonical(lo)", "canonical(hi)"],
 "ensures": [{"kind": "makes_interval", "lower": "zl", "upper": "zu", "from": {"lower": "lo", "upper": "hi"}}],
 "min_precision": 1, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "mul_ext_2_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "x", "limbs": 2}, {"name": "y", "limbs": 2}],
 "outputs": [{"name": "l", "limbs": 2}, {"name": "h", "limbs": 2}],
 "value": "x*y", "requires": ["canonical(x)", "canonical(y)", "not_nan(x)", "not_nan(y)"],
 "ensures": [{"kind": "normalized", "of": "l"}, {"kind": "normalized", "of": "h"}, {"kind": "outward", "of": "l", "side": "below", "rel": "(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)*(1+unit(mul_2_2))/(1-u)", "abs": "2*(1+u)^2*(1/2*up((1+u)^6)*eta+up((1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)/(1-u)*tiny(mul_2_2)", "zero_factor": true}, {"kind": "outward", "of": "h", "side": "above", "rel": "(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)*(1+unit(mul_2_2))/(1-u)", "abs": "2*(1+u)^2*(1/2*up((1+u)^6)*eta+up((1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)/(1-u)*tiny(mul_2_2)", "zero_factor": true}],
 "min_precision": 4, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

and the `ensures` of four more:

```json
[{"kind": "interval_set", "lower": "zl", "upper": "zu", "set": "intersection", "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}}],
[{"kind": "ball_of_interval", "center": "c", "radius": "r", "from": {"lower": "xl", "upper": "xu"}, "special": "ball", "rel": "u", "abs": "eta", "smallest_radius": true}],
[{"kind": "encloses_interval", "lower": "zl", "upper": "zu", "set": "-x", "intervals": {"x": {"lower": "xl", "upper": "xu"}}, "tight": {"kind": "exact"}, "bounded_when": [{"abs_le": "-x", "exp": 0}], "bounded_exactly": true}],
[{"kind": "encloses_interval", "lower": "zl", "upper": "zu", "set": "x*y", "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}, "tight": {"kind": "outward", "rel": "(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)*(1+unit(mul_2_2))/(1-u)", "abs": "2*(1+u)^2*(1/2*up((1+u)^6)*eta+up((1+u)*(2*(1+u)^5*eta+tiny(mul_2_2)/(1-unit(mul_2_2))+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^6)*up(unit(mul_2_2)/(1-unit(mul_2_2)))+2*u^2)/(1-u)*tiny(mul_2_2)"}, "bounded_when": [{"abs_le": "x*y", "exp": -2}], "zero_factor": true}]
```

those of `interval_intersection_2`, `interval_to_ball_1`, `interval_neg_2` and `interval_mul_2`. The other kernels of this stage:
- `interval_hull_2` is `interval_hull_1` with bounds of two limbs, and `interval_intersection_1` is `interval_intersection_2` with bounds of one limb.
- `interval_sub_2` is `interval_add_2` with the set `x-y` and `exact_when` `{"lower": [{"zero": "xl-yu"}], "upper": [{"zero": "xu-yl"}]}`. Its `bounded_when` is `{"abs_le": "x-y", "exp": -2}`, not exactly.

**Not claimed.** A two-limb form is part of this stage only where it is the listing of one limb on the comparisons of two limbs: the hull and the intersection. `interval_mid_rad_2`, `interval_to_ball_2`, `ball_to_interval_2` and `interval_split_2` are other listings (the halves by `mul_pow2_2`, the radius by `add_ball_2_2`), with claims that this vocabulary would state with `ball_of_interval` without `smallest_radius` and `interval_of_ball` with an outward tightness. They are claimed so since: [the conversions of two limbs](#claims-of-the-enclosure-interface-the-conversions-of-two-limbs).

**In the formal models.** IEEE model only, in the vocabulary of `IeeeIntervalVocabulary.v` and `IeeeVocabulary.v`:
- `interval_set`: the set is the predicate `(fun z : R => in_interval_n X z \/ in_interval_n Y z)`, with `/\` for the intersection. Containment is a `forall z`. The emptiness rule is `interval_empty_n X /\ interval_empty_n Y` for the union and `~ (exists z : R, ...)` for the intersection. Exactness is that a result that is not empty has the bounds `range_lower` and `range_upper` of the set.
- `ball_of_interval`: `ball_1`, `ball_empty_1`, `ball_whole_1` and `ball_finite_1` for `ball`; the special values written with `nan`, `zero`, `infinity` and `omega prec emax`; the smallest radius written as `RU (ieee_emin prec emax) prec (Rmax (c - l) (h - c))`.
- `interval_of_ball`: I1 to I4 with `in_ball_1`, `range_lower`, `range_upper`, `xrd` and `xru`.
- `splits`: equalities of `xval` (`xval_2` for two limbs) of the bounds.
- `outward` of the extended domain: `xval_2`, `xle` and `xmul` for the side and the infinite operands, and the bound of the finite domain for a finite output.
- `zero_factor`: an input is zero when its leading limb is, an output when every limb is. I6 is `(zero xl0 /\ zero xu0) \/ (zero yl0 /\ zero yu0)`, for nonempty operands, implying the four limbs of $Z$ zero.

A statement about intervals or balls made from them has a hypothesis on the precision only when its minimum is above 1, as before. These kernels have no real-model statement.

### Claims of the enclosure interface: predicates and comparisons

The third stage of the interval work (stage B2) needs the additions below, for these kernels of [One enclosure interface](design/milestone2.md#one-enclosure-interface), each of one limb and of two (`_1`, `_2`):
- the predicates of an interval: `interval_empty_k`, `interval_entire_k`, `interval_contains_k` (a point), `interval_subset_k`, `interval_positive_k`, `interval_negative_k`, `interval_zero_k`;
- its three-valued comparisons: `interval_less_k`, `interval_less_equal_k`, `interval_equal_k`;
- the relations of IEEE 1788 that are not one of those: `interval_rel_equal_k`, `interval_rel_interior_k`, `interval_rel_disjoint_k`;
- the predicates and three-valued comparisons of a ball (below): `ball_contains_point_k`, `ball_contains_ball_k`, `ball_positive_k`, `ball_negative_k`, `ball_zero_k`, `ball_less_k`, `ball_less_equal_k`, `ball_equal_k`.

Everything above keeps its meaning and its JSON shape: the two kinds below are new, and `abs_le` with `omega`, a condition of `bounded_when`, is also a condition of their `exact_when`.

**New kinds.** Both are about *sets*, named in the entry as the interval and ball operands are named elsewhere, by one of two fields: `intervals`, each name with the `lower` and `upper` inputs of an `interval` requirement; or `balls`, each name with the `center` and `radius` inputs of a `ball` requirement. The sets of one entry are all intervals or all balls. The *members* of a set are real numbers: those between the bounds of an interval ($[1, +\infty]$ does not contain $+\infty$), those within the radius of a finite ball's center, every real number for the whole line, none for the empty set.

| Kind | Fields | Meaning |
|---|---|---|
| `certain` | `of`: a mask output; `rel`, `args` (below); `intervals` or `balls`; `exact` (optional): `true`; `exact_when` (optional): a list of conditions | The mask is true only if the relation holds. When an operand is not finite (a set that is the empty set or the whole line, a point that is not a finite number), it is true exactly when the relation holds. With `exact`, it is true exactly when the relation holds, for every operand. With `exact_when`, it is so when every operand is finite (a bounded interval, a finite ball, a finite point) and every condition holds. Without either, nothing more is claimed: the mask may be false although the relation holds. A half-line is neither: it is not one of the special states that make the claim exact (the generated statements' disjunction names the empty set and the whole line of each interval, and for `member` a point that is not finite), nor a bounded interval of `exact_when`, so on a half-line a claim without `exact` says only that a true mask is right (every claim over intervals has `exact` today) |
| `trit` | `yes`, `no`: two mask outputs; `rel`, `args`; `intervals` or `balls`; `exact` or `exact_when` (optional), as for `certain` | `yes` is true only if the relation holds *for every choice of members* (below), `no` only if it fails for every choice; they are never both true, and both false is the answer *unknown*. When an operand is not finite, and with `exact` always, `yes` is true exactly when the relation holds for every choice and `no` exactly when it fails for every choice; `exact_when` as for `certain` |

The relations, `rel` and its `args` (a set is named by its name in `intervals` or `balls`):

| `rel` | `args` | Holds when | Of `trit`: fails for every choice when |
|---|---|---|---|
| `lt`, `le`, `eq` | two, each a set or the integer `0`, one of them a set | every set named is nonempty, and $a < b$ ($\le$, $=$) for every choice of a member $a$ of the first and $b$ of the second (`0` stands for the number 0) | every set named is nonempty, and $a < b$ ($\le$, $=$) is false for every choice |
| `member` | a point and a set: the point an input of one limb, or of two required `canonical` | the point is a finite number and a member of the set | the point is not a finite number, or not a member |
| `subset` | two sets | every member of the first is a member of the second | (no `trit`) |
| `equal` | two sets | they have the same members | (no `trit`) |
| `interior` | two sets | every member of the first has a neighbourhood, an open interval around it, made of members of the second | (no `trit`) |
| `disjoint` | two sets | no real number is a member of both | (no `trit`) |
| `empty` | one set | it has no member | (no `trit`) |
| `entire` | one set | every real number is a member | (no `trit`) |

So, on the special sets: `lt`, `le` and `eq` neither hold nor fail for every choice when a set is empty (a three-valued comparison with the empty set is *unknown*, and so is `certainly_positive`, which is `lt` with `0`: [The empty set and the whole line](design/milestone2.md#the-empty-set-and-the-whole-line)); with the whole line they never hold and never fail for every choice either. `subset`, `equal`, `interior` and `disjoint` have the vacuous readings of the empty set, which are those of IEEE 1788: the empty set is a subset of every set, interior to every set, disjoint from every set, and equal to the empty set only.

**A condition of `exact_when`** of these kinds is `{"abs_le": EXPR, "omega": true}`, $\lvert \mathrm{EXPR}\rvert \le \Omega$, EXPR an expression of the language of `value` over the inputs (for a ball, its center and radius inputs), evaluated on finite operands. No other condition is one of these kinds.

**The relations of IEEE 1788.** The standard IEEE Std 1788.1-2017 has four relations of two intervals, `equal`, `subset`, `interior` and `disjoint` ([IEEE 1788](design/milestone2.md#ieee-1788)). Each is a kernel, exact, with the standard's conventions for the empty set, which are the readings of the table above: `subset(X, Y)` is `interval_subset_k`, which is also Kairn's predicate `Y.contains(X)` with the operands exchanged; `equal(X, Y)` is `interval_rel_equal_k`, which is *not* Kairn's three-valued `equal`; `interior(X, Y)` is `interval_rel_interior_k`; `disjoint(X, Y)` is `interval_rel_disjoint_k`, which for nonempty operands is the *no* of Kairn's three-valued `equal`, and is also true when an operand is empty. The four relations that only the full standard has, `less`, `precedes`, `strict_less` and `strict_precedes`, are not kernels of this stage: the page asks that their definitions be checked against the test cases of ITF1788 first, and those are not in the repository.

Entries as the generator writes them (`source`, `flops` and the theorem fields left out):

```json
{"name": "interval_contains_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 1}, {"name": "xu", "limbs": 1}, {"name": "t", "limbs": 1}],
 "outputs": [{"name": "m", "limbs": 1, "type": "mask"}],
 "requires": ["interval(xl, xu)"],
 "ensures": [{"kind": "certain", "of": "m", "rel": "member", "args": ["t", "x"], "intervals": {"x": {"lower": "xl", "upper": "xu"}}, "exact": true}],
 "min_precision": 1, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "interval_less_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 2}, {"name": "xu", "limbs": 2}, {"name": "yl", "limbs": 2}, {"name": "yu", "limbs": 2}],
 "outputs": [{"name": "yes", "limbs": 1, "type": "mask"}, {"name": "no", "limbs": 1, "type": "mask"}],
 "requires": ["interval(xl, xu)", "interval(yl, yu)"],
 "ensures": [{"kind": "trit", "yes": "yes", "no": "no", "rel": "lt", "args": ["x", "y"], "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}, "exact": true}],
 "min_precision": 1, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

and the `ensures` of six more:

```json
[{"kind": "certain", "of": "m", "rel": "lt", "args": ["0", "x"], "intervals": {"x": {"lower": "xl", "upper": "xu"}}, "exact": true}],
[{"kind": "certain", "of": "m", "rel": "eq", "args": ["x", "0"], "intervals": {"x": {"lower": "xl", "upper": "xu"}}, "exact": true}],
[{"kind": "certain", "of": "m", "rel": "empty", "args": ["x"], "intervals": {"x": {"lower": "xl", "upper": "xu"}}, "exact": true}],
[{"kind": "certain", "of": "m", "rel": "subset", "args": ["x", "y"], "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}, "exact": true}],
[{"kind": "certain", "of": "m", "rel": "interior", "args": ["x", "y"], "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}, "exact": true}],
[{"kind": "trit", "yes": "yes", "no": "no", "rel": "eq", "args": ["x", "y"], "intervals": {"x": {"lower": "xl", "upper": "xu"}, "y": {"lower": "yl", "upper": "yu"}}, "exact": true}]
```

those of `interval_positive_1`, `interval_zero_1`, `interval_empty_2`, `interval_subset_1`, `interval_rel_interior_2` and `interval_equal_1`. The other kernels of this part:
- `interval_negative_k` is `lt` with the arguments `["x", "0"]`; `interval_entire_k` is `entire`; `interval_contains_2` is `interval_contains_1` with bounds of two limbs and a point of two limbs, required `canonical`; `interval_rel_equal_k` and `interval_rel_disjoint_k` are `equal` and `disjoint`; `interval_less_equal_k` is `interval_less_k` with `le`. Every one is `exact`, and each kernel of two limbs claims what the kernel of one limb claims.
- The masks of a `trit` are the outputs `yes` and `no`, in that order; in the line protocol each is `0` or `1`, as every mask.

**The predicates and comparisons of a ball**, the same kinds with `balls`: `ball_contains_point_k`, `ball_contains_ball_k` (Y inside X: `subset` with the arguments `["y", "x"]`), `ball_positive_k`, `ball_negative_k`, `ball_zero_k`, `ball_less_k`, `ball_less_equal_k`, `ball_equal_k`. The bounds $c \mp r$ of a ball are not numbers of `T` in general, and what each kernel claims differs by the number of limbs:
- One limb: exact. The kernels compare exact pairs (`two_sum_ord` of a difference or a sum of two numbers of `T`) by the comparisons of two limbs ([Exact pairs](design/milestone2.md#one-enclosure-interface)). `ball_contains_point_1`, `ball_contains_ball_1` and the signs are `exact`. The three comparisons are exact unless the sum of the radii and the difference of the centers both overflow, when the answer is *unknown*; the claim states the half that a condition can, `"exact_when": [{"abs_le": "rx+ry", "omega": true}]`, and a sum of the radii that does not overflow is enough.
- Two limbs: certain, not exact, but `ball_positive_2`, `ball_negative_2` and `ball_zero_2` (the comparisons `lt_1_2`, `lt_2_1`, `eq_2_1` with the radius), which are `exact`. The others compare a one-limb bound of a distance with the radius: with $(z, e)$ = `add_ball_2_2` of the difference of the centers (or of the point and the center), $\lvert d - z\rvert \le e$, and an upper bound by `abs_upper_2` and `radd`, or a lower bound by `to_down_2` and a directed difference with $e$. Every answer given is right; an answer not given is near the boundary. With $G$ the gap of `T` at the largest of the radii and the distance: `contains(t)` answers unless $\bigl\lvert\lvert t - c\rvert - r\bigr\rvert < 2e + 3G$; `contains(Y)` gives true unless $r_x - (\lvert c_y - c_x\rvert + r_y) < 2e + 4G$; `less` and `less_equal` give *yes* (*no*) unless the gap between the balls, $(c_y - c_x) - (r_x + r_y)$ (or $(c_x - c_y) - (r_x + r_y)$), is below $2e + 4G$; `equal` gives *no* unless $\lvert c_y - c_x\rvert - (r_x + r_y) < 2e + 4G$. Of its *yes* (both balls the same point) the claim says what it says of every answer and no more: the generated statement (`ball_equal_2_spec` in `proofs/gen/IeeeStatements.v`) has a *yes* only where every member of X equals every member of Y, a *no* only where none does, never both, and both exact when an operand is empty or the whole line; on two finite balls that are the same point it claims no answer, and *unknown* there violates nothing. The band is not claimed: the reasoning is in `experiments/milestone2/predicates_2.py`, which asserts it on 20 000 cases at three, four and five bits and measures the largest margin of an answer not given (2.3 units of $2e + G$). It is $G$, a gap of `T` at the radius, about $2u\,r$, that dominates unless the radius is small compared with the distance: $e$ is about $3u^2$ times the distance plus twice the smallest normal number. $e$ is inside the kernel and no output shows it, so the oracle measures the band in what a line does show (`oracle/README.md`, "The kinds of the enclosure interface"): the margin of an answer not given, its distance from the boundary of the relation ($\bigl\lvert\lvert t - c\rvert - r\bigr\rvert$ for `contains(t)`, $r_x - (\lvert c_y - c_x\rvert + r_y)$ for `contains(Y)`, the gap between the balls for the comparisons), in units of $2e + G$, with $e$ estimated from the operands as $3u^2$ times the distance of the centers (or of the point and the center) plus twice the smallest normal number, and $G$ the gap of `T` at the larger of the largest radius and the distance, where both are below $\Omega/4$ (above, $e$ or the difference itself may overflow and the band is the whole line). Nothing is claimed of the band: an answer not given passes the oracle wherever it is, and is counted. The cross-checks' guards hold the largest margin of a run to 4 such units, $2e + 4G \le 4(2e + G)$, the widest band above (`tests/crosscheck_guards.py`, `ENC_BAND_LIMIT`): a test that the kernels keep to the band described here, not a claim.
- Special states: on the empty set and the whole line every kernel gives the exact answers, those of [The empty set and the whole line](design/milestone2.md#the-empty-set-and-the-whole-line): `contains(t)` is false on the empty set and true on the whole line for a finite $t$, `contains(Y)` true when X is the whole line or Y empty, the signs false, the comparisons *unknown*. A point that is not a finite number is a member of nothing: the *no* of `ball_contains_point_2` is then true.

`ball_contains_point_2` returns *yes* and *no*, as the page's listing does (`contains` returns *yes*), and `ball_contains_point_1` one mask, exact. The signs are the comparisons that `Ball::certainly_positive`, `certainly_negative` and `certainly_zero` of `include/kairn/ball.hpp` made by hand before (for two limbs the same calls of `lt_1_2`, `lt_2_1` and `eq_2_1`, for one limb the same comparisons of `T`), now with statements of their own about the members of the ball; those functions call these kernels since the enclosure interface was completed, with the same results. The public forms of every kernel of this section are in [One enclosure interface](../reference/enclosure.md).

Two entries in full, and the `ensures` of four more (`ball_contains_point_1`, `ball_contains_ball_2`, `ball_positive_2`, `ball_equal_2`):

```json
{"name": "ball_less_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "cx", "limbs": 1}, {"name": "rx", "limbs": 1}, {"name": "cy", "limbs": 1}, {"name": "ry", "limbs": 1}],
 "outputs": [{"name": "yes", "limbs": 1, "type": "mask"}, {"name": "no", "limbs": 1, "type": "mask"}],
 "requires": ["ball(cx, rx)", "ball(cy, ry)"],
 "ensures": [{"kind": "trit", "yes": "yes", "no": "no", "rel": "lt", "args": ["x", "y"], "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}}, "exact_when": [{"abs_le": "rx+ry", "omega": true}]}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "ball_contains_point_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "c", "limbs": 2}, {"name": "r", "limbs": 1}, {"name": "t", "limbs": 2}],
 "outputs": [{"name": "yes", "limbs": 1, "type": "mask"}, {"name": "no", "limbs": 1, "type": "mask"}],
 "requires": ["ball(c, r)", "canonical(t)"],
 "ensures": [{"kind": "trit", "yes": "yes", "no": "no", "rel": "member", "args": ["t", "x"], "balls": {"x": {"center": "c", "radius": "r"}}}],
 "min_precision": 3, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

```json
[{"kind": "certain", "of": "m", "rel": "member", "args": ["t", "x"], "balls": {"x": {"center": "c", "radius": "r"}}, "exact": true}],
[{"kind": "certain", "of": "m", "rel": "subset", "args": ["y", "x"], "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}}}],
[{"kind": "certain", "of": "m", "rel": "lt", "args": ["0", "x"], "balls": {"x": {"center": "c", "radius": "r"}}, "exact": true}],
[{"kind": "trit", "yes": "yes", "no": "no", "rel": "eq", "args": ["x", "y"], "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}}}]
```

The other kernels: `ball_contains_ball_1` is `ball_contains_ball_2` with one-limb centers and `exact`; `ball_negative_k` and `ball_zero_k` are `lt` with `["x", "0"]` and `eq` with `["x", "0"]`, `exact`, and `ball_positive_1` is `ball_positive_2` with one limb; `ball_less_equal_1` and `ball_equal_1` are `ball_less_1` with `le` and `eq`; `ball_less_2` and `ball_less_equal_2` are `ball_equal_2` with `lt` and `le`.

Two listings differ from the page's in form, not in value, by the rule against negating a fused result (gen/README.md, "The rules"): where the page writes `sub_down_1(x, e)` with $e$ the radius of `add_ball_2_2`, an FMA, the listing writes `neg(add_up_1(e, neg(x)))`, minus the rounding up of $e - x$, which is the rounding down of $x - e$: the lower bound `lo` of `ball_contains_point_2` (`nw = neg(wd); tl = add_up_1(e, nw); lo = neg(tl)`) and the lower bounds of the comparisons of two limbs, which the page describes without a listing ("bounded below and above as in `ball_contains_point_2`").

**In the formal models.** IEEE model only, in the vocabulary of `IeeeIntervalVocabulary.v` and `IeeeVocabulary.v`. A mask is a `bool`, and the claims are about `m = true`:
- the relation, with the members `in_interval_n` (or `in_ball_n`) of the sets: for `lt`, `le` and `eq`, `interval_nonempty_n` of each set named (for a ball, `~ ball_empty_n`) and `forall x y : R, in X x -> in Y y -> x < y` (the failure of `trit`: `~ (x < y)`); for `member`, `finite t0 /\ in X (val t0 + val t1)`; for `subset`, `forall z : R, in X z -> in Y z`; for `equal`, the same with `<->`; for `interior`, `forall z : R, in X z -> exists d : R, 0 < d /\ (forall w : R, Rabs (w - z) < d -> in Y w)`; for `disjoint`, `~ (exists z : R, in X z /\ in Y z)`; for `empty`, `interval_empty_n` (`ball_empty_n`); for `entire`, `forall z : R, in X z`;
- `certain`: `(m = true -> R)`; then, without `exact`, `(S -> (m = true <-> R))` with S the disjunction of `interval_empty_n X \/ (xval xl = XInf true /\ xval xu = XInf false)` of each interval (for a ball, `ball_empty_n \/ ball_whole_n`) and, for `member`, `~ finite t0`; and with `exact_when`, `(F -> C -> (m = true <-> R))`, F the conjunction of `interval_bounded_n` (for a ball, `ball_finite_n`) of each set and, for `member`, `finite t0`, C the conditions (`Rabs E <= omega prec emax`). With `exact`, the statement is `(m = true <-> R)` alone;
- `trit`: `(yes = true -> R)`, `(no = true -> N)` and `~ (yes = true /\ no = true)`, N the failure for every choice; then as for `certain`, with `(yes = true <-> R) /\ (no = true <-> N)` for each equivalence.

### Claims of the enclosure interface: the set operations of a ball

The hull, the intersection and the split of a ball ([Hull, intersection and split of balls](design/milestone2.md#hull-intersection-and-split-of-balls)), stage B2: `ball_hull_1`, `ball_intersection_1`, `ball_split_1` and `ball_split_2`. (`ball_hull_2` and `ball_intersection_2` convert balls of two limbs to intervals and back, and come with the conversions of two limbs, in the next section.) Two kinds are new; everything above keeps its meaning and its shape.

| Kind | Fields | Meaning |
|---|---|---|
| `ball_set` | `center`, `radius`: the outputs; `set`: `union` or `intersection`; `balls`: two names, each with its `center` and `radius` inputs (of a `ball` requirement) | The result Z is a canonical ball, and every real number that is a member of X or of Y (`union`), or of both (`intersection`), is a member of Z. For `union`: Z is empty exactly when X and Y both are; when X is empty, Z is Y as it is (the same limbs); when Y is empty and X is not, Z is X as it is. For `intersection`: Z is empty when an operand is; when X is the whole line, Z is Y as it is; when Y is the whole line and X is not, Z is X as it is. Nothing more: Z need not be the smallest such ball, nor inside X or Y, nor empty for disjoint balls |
| `ball_splits` | `parts`: two objects, each with the `center` and `radius` outputs of a ball; `from`: the `center` and `radius` inputs of a `ball` requirement | Both parts are canonical balls. The empty set gives the empty set twice, the whole line the whole line twice (a ball cannot be a half-line). For a finite ball X of center $c$ and radius $r$: every real in $[c - r, c]$ is a member of the first part, and every real in $[c, c + r]$ a member of the second; together they cover X. Nothing more: the parts need not be inside X, nor their radii close to $r/2$ |

"As it is" is the operand's limbs themselves, the same floating-point data: the sign of a zero is part of the claim, and in the formal model so are the sign and the payload of a NaN. The line protocol prints every NaN as `nan`, so a judge of its lines compares a NaN with a NaN as equal and every other limb exactly, $-0$ differing from $+0$. The clause that gives X has the condition that X is not itself empty (for `union`) or the whole line (for `intersection`): when both operands are special the result is one of them, Y, and two empty balls may differ in their NaNs and two whole lines in the sign of the zero of their centers, so no result is both operands as they are. With one operand empty and the other the whole line, in either order, one of the two clauses applies: the hull is the whole line and the intersection the empty set, each that operand as it is.

Entries as the generator writes them (`source`, `flops` and the theorem fields left out):

```json
{"name": "ball_hull_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "cx", "limbs": 1}, {"name": "rx", "limbs": 1}, {"name": "cy", "limbs": 1}, {"name": "ry", "limbs": 1}],
 "outputs": [{"name": "cz", "limbs": 1}, {"name": "rz", "limbs": 1}],
 "requires": ["ball(cx, rx)", "ball(cy, ry)"],
 "ensures": [{"kind": "ball_set", "center": "cz", "radius": "rz", "set": "union", "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}}}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "ball_split_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "c", "limbs": 2}, {"name": "r", "limbs": 1}],
 "outputs": [{"name": "ca", "limbs": 2}, {"name": "ra", "limbs": 1}, {"name": "cb", "limbs": 2}, {"name": "rb", "limbs": 1}],
 "requires": ["ball(c, r)"],
 "ensures": [{"kind": "ball_splits", "parts": [{"center": "ca", "radius": "ra"}, {"center": "cb", "radius": "rb"}], "from": {"center": "c", "radius": "r"}}],
 "min_precision": 3, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

`ball_intersection_1` is `ball_hull_1` with `"set": "intersection"`, and `ball_split_1` is `ball_split_2` with one-limb centers (minimum precision 2). The line protocol: a ball is its center limbs then its radius, and `ball_split_k` returns the first part, then the second.

The listings: `ball_hull_1` is `ball_to_interval_1` of each operand, `interval_hull_1`, `interval_to_ball_1`, then selects on the tests of the radii for the operands returned as they are (a NaN radius is the empty set, $+\infty$ the whole line). `ball_intersection_1` computes the values of the same composition with `interval_intersection_1`, in another order: the directed bounds of both balls and their intersection $[\ell, h]$ as they are, `interval_to_ball_1` of $[\ell, h]$, and only then the empty ball (a NaN center and radius, what `interval_to_ball_1` makes of the empty interval) where a radius is a NaN or $\ell > h$, before the same selects for the whole line. The reason is the object-code check: where the conversions select the constants of the empty interval before the halving of `interval_mid_rad_1`, GCC 13 on x86-64 duplicates the halving, its two products included, on the path of those constants (four fused multiply-adds for two, at every optimization level); selected after the halving, the products are computed once. `ball_from_interval_1` is rewritten the same way (below). A comparison of the two listings on 480 968 cases, at run time and in constant evaluation, in binary64, binary32 and two toy formats, found every output the same, bit for bit. `ball_split_k` is the page's listing, the point $c$ plus the balls of center $\mp h$ and radius $\max(h, r - h)$, $h = \mathrm{RN}(r/2)$, by `ball_add_k_full`, with one change of form: the page negates `hs = select(fr, h, 0)`, whose first arm is the product `h`, which the generator refuses (gen/README.md, "The rules"); the listing computes $-h$ as its own product, `nh = select(fr, prod(neg(r), const up(1/2)), 0)`, the same value, rounding to nearest being symmetric.

**In the formal models.** IEEE model only: `ball_n` of the result; for `union`, `(ball_empty_n Z <-> ball_empty_n X /\ ball_empty_n Y)`, `(ball_empty_n X -> cz = cy /\ rz = ry)` and `(ball_empty_n Y /\ ~ ball_empty_n X -> cz = cx /\ rz = rx)`; for `intersection`, `(ball_empty_n X \/ ball_empty_n Y -> ball_empty_n Z)`, `(ball_whole_n X -> cz = cy /\ rz = ry)` and `(ball_whole_n Y /\ ~ ball_whole_n X -> cz = cx /\ rz = rx)`. Each equality is of the limbs themselves, values of `binary_float` (with a center of two limbs, `cz0 = cy0 /\ cz1 = cy1 /\ rz = ry`); then `forall z : R, in_ball_n X z \/ in_ball_n Y z -> in_ball_n Z z` (`/\` for the intersection). For `ball_splits`: `ball_n` of each part, the empty set and the whole line twice (`ball_empty_n`, `ball_whole_n`), and for `ball_finite_n X`, `forall z : R, c - r <= z <= c -> in_ball_n A z` and `forall z : R, c <= z <= c + r -> in_ball_n B z`, $c$ the value of the center limbs.

### Claims of the enclosure interface: the conversions of two limbs

The conversions between an interval and a ball of two limbs ([Midpoint, radius and the conversions](design/milestone2.md#midpoint-radius-and-the-conversions)), stage B2: `interval_mid_rad_2`, `interval_to_ball_2`, `interval_split_2`, `ball_to_interval_2`; the ball of one limb from an interval of two `T`, `ball_from_interval_1`; and the hull and the intersection of balls of two limbs, `ball_hull_2` and `ball_intersection_2`, which convert them (their claims are those of `ball_hull_1` and `ball_intersection_1`, [above](#claims-of-the-enclosure-interface-the-set-operations-of-a-ball)). These are other listings than those of one limb (the halves by `mul_pow2_2`, the sum by `add_2_2`, each side of the radius by `radd(to_up_2(z), e)` with $(z, e)$ = `add_ball_2_2`; the bounds of a ball by `add_down_2_2` and `add_up_2_2`), and their claims use kinds that exist, three of them with a field that is new. Everything above keeps its meaning and its shape: each new field is written only in an entry that uses it.

**Fields new to existing kinds:**
- `ball_of_interval` with `finite_when`: a list of conditions `{"abs_le": BOUND, "exp": E}`, BOUND one of the inputs of `from`, $\lvert \mathrm{BOUND}\rvert \le 2^{q_{\max} + p + E}$ (the conditions of `finite_when` of the other kinds). The radius of two limbs is the larger of two upper bounds, each `radd` of the rounding up of a difference by `add_ball_2_2`: near the top of the range `radd` steps past $\Omega$, or a TwoSum inside `add_2_2` overflows and gives a NaN, and the listing makes such a side $+\infty$, so that for a bounded interval the radius can be $+\infty$. It is finite when both bounds are at most $2^{q_{\max}+p-2}$ in magnitude, where the sums of two limbs are finite (`interval_mid_rad_2` and `interval_to_ball_2` claim `[{"abs_le": "xl", "exp": -2}, {"abs_le": "xu", "exp": -2}]`). So, for a bounded $X$: with `ieee1788`, the center is finite, between the bounds and within `rel` $\cdot\lvert m\rvert$ + `abs` of the midpoint $m$, as without the field, and the radius is $+\infty$ or a finite number with which the center contains $X$; it is finite when every condition holds. With `ball`, the result is a canonical ball that contains $X$, and, when every condition holds, a finite ball whose center and radius are as without the field; otherwise it may be the whole line. The unbounded and the empty $X$ are as without the field.
- `interval_of_ball` with bounds of two limbs: `tight` is `{"kind": "outward", "rel": ..., "abs": ..., "exact_when": {"lower": [...], "upper": [...]}}`, the outward tightness of `encloses_interval`, and an optional `bounded_when`, a list of conditions `{"abs_le": SET, "exp": E}`. $Z$ is canonical, empty exactly when the ball is, and contains every value of `set` (I1 to I3, as before). For a finite ball and a bounded $Z$, with $lo$ and $hi$ the greatest lower and least upper bounds of the set ($c - r$ and $c + r$ for the set `x`): $lo - z_\ell \le \mathrm{rel}\cdot\lvert lo\rvert + \mathrm{abs}$ and $z_u - hi \le \mathrm{rel}\cdot\lvert hi\rvert + \mathrm{abs}$; when every condition of a side holds (`{"zero": EXPR}` over the inputs, $c - r = 0$ for the lower bound), that bound of $Z$ is exactly that bound of the set, zero. For a finite ball, $Z$ is bounded when every member $z$ of the set has $\lvert z\rvert \le 2^{q_{\max} + p + E}$.
- `makes_ball` from an interval with `rel`, `abs` and `smallest_radius` (all three optional, `smallest_radius` only with the other two): for finite bounds $lo \le hi$, the center $c$ is between them and within `rel` $\cdot\lvert m\rvert$ + `abs` of the midpoint $m = (lo + hi)/2$, and with `smallest_radius` the radius is $\mathrm{RU}(\max(c - lo, hi - c))$, the smallest number of the format with which the ball contains $[lo, hi]$. They come after `midpoint_when` when an entry has both.

**The midpoint of two limbs is a canonical number.** With `ieee1788` the center is a number given back as a number (the `midpoint()` of an interval), not the center of a ball, and a number of two limbs has an invariant of its own: it is canonical, a finite normalized pair, an infinity followed by a zero, or two NaN (`canonical` of the requirements, [Claims of the non-finite layer](#claims-of-the-non-finite-layer)). So `ball_of_interval` with `ieee1788` and a center of two limbs also claims that the center is canonical, for every canonical $X$: the two NaN of the empty set are canonical; the whole line gives two zeros, a half-line $(\pm\Omega, +0)$, and a bounded $X$ a normalized pair. Nothing is added for a center of one limb, where every value is a number of `T`: the special values above are the whole claim on the empty set and the unbounded intervals, and a bounded $X$ gives a finite center. With `ball` the center is part of a canonical ball, which says it already. `interval_split_2` needs no such clause: its point of split is a bound of both parts, and each part is a canonical interval, whose bounds are canonical.

The constants of the midpoint of two limbs are those of the page: `rel` $3u^2/(1 - 4u)$, the bound of `add_2_2`, and `abs` $2\eta$. They need one fact beyond the claims of the kernels called: `mul_pow2_2` by $\tfrac12$ loses at most $\tfrac12\eta$, not the $\eta$ of its claim, because of a normalized pair at most one limb is an odd multiple of $\eta$ (a leading limb below $2^p\eta$ has a zero tail); so the two halves are within $\eta$ of their sum together, and $\eta(1 + 3u^2/(1-4u)) \le 2\eta$. The move into $[\ell, h]$ only brings the center closer.

Entries as the generator writes them (`source`, `flops` and the theorem fields left out):

```json
{"name": "interval_mid_rad_2", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "xl", "limbs": 2}, {"name": "xu", "limbs": 2}],
 "outputs": [{"name": "m", "limbs": 2}, {"name": "r", "limbs": 1}],
 "requires": ["interval(xl, xu)"],
 "ensures": [{"kind": "ball_of_interval", "center": "m", "radius": "r", "from": {"lower": "xl", "upper": "xu"}, "special": "ieee1788", "rel": "3*u^2/(1-4*u)", "abs": "2*eta", "finite_when": [{"abs_le": "xl", "exp": -2}, {"abs_le": "xu", "exp": -2}]}],
 "min_precision": 3, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}},
{"name": "ball_from_interval_1", "domain": "extended", "ieee_only": true,
 "inputs": [{"name": "lo", "limbs": 1}, {"name": "hi", "limbs": 1}],
 "outputs": [{"name": "cw", "limbs": 1}, {"name": "rw", "limbs": 1}],
 "requires": [],
 "ensures": [{"kind": "makes_ball", "center": "cw", "radius": "rw", "from": {"lower": "lo", "upper": "hi"}, "rel": "u", "abs": "eta", "smallest_radius": true}],
 "min_precision": 2, "status": "proved", "ieee_status": "proved",
 "instances": {"binary64": [], "binary32": []}}
```

and the `ensures` of two more:

```json
[{"kind": "interval_of_ball", "lower": "zl", "upper": "zu", "set": "x", "balls": {"x": {"center": "c", "radius": "r"}}, "tight": {"kind": "outward", "rel": "(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)*(1+unit(add_2_2))/(1-u)", "abs": "2*(1+u)^2*(1/2*up((1+u)^3)*eta+up((1+u)*((1+u)^2*eta+eta/2)+eta/(2*u)))+eta+(2*(1+u)^3*up((1+u)^3)*up(unit(add_2_2)/(1-unit(add_2_2))*(1+u))+2*u^2)/(1-u)*tiny(add_2_2)", "exact_when": {"lower": [{"zero": "c-r"}], "upper": [{"zero": "c+r"}]}}, "bounded_when": [{"abs_le": "x", "exp": -2}]}],
[{"kind": "ball_of_interval", "center": "c", "radius": "r", "from": {"lower": "xl", "upper": "xu"}, "special": "ball", "rel": "3*u^2/(1-4*u)", "abs": "2*eta", "finite_when": [{"abs_le": "xl", "exp": -2}, {"abs_le": "xu", "exp": -2}]}]
```

those of `ball_to_interval_2` (whose constants are those of `interval_add_2`, the sum of two limbs) and `interval_to_ball_2`. `interval_split_2` claims what `interval_split_1` claims, on bounds of two limbs; its listing has one step more, the midpoint moved into $[x_\ell, x_u]$ by `lt_2_2`: a bound of two limbs can lie beyond $\Omega$ (by less than half a gap of `T`), and the midpoint $\pm\Omega$ of a half-line is then outside the interval, where the bound itself is the point of the split.

`ball_from_interval_1` computes the values of `interval_make_1` followed by `interval_to_ball_1`, in another order: `interval_to_ball_1` of the guarded bounds where `interval_make_1` returns them, of $[0, 0]$ otherwise, then, where `interval_make_1` would not return them, the ball that `interval_to_ball_1` makes of the empty interval (a NaN center and radius) where the bounds are reversed, `lt(gu, gl)` as in `interval_make_1`, and of the whole line (center 0, radius $+\infty$) otherwise, for a NaN bound and for the same infinity twice. Selecting the whole line or the empty interval first, as `interval_make_1` does, makes GCC 13 on x86-64 duplicate the halving on the path of a constant bound (three fused multiply-adds for two), which the object-code check refuses ([above](#claims-of-the-enclosure-interface-the-set-operations-of-a-ball), for `ball_intersection_1`). $[0, 0]$ rather than the bounds as they are: constant evaluation then computes nothing of a NaN bound (Clang 18 refuses an operation whose result is a NaN, even of a NaN operand) nor of the empty interval ($+\infty - \infty$), so that the ball of every pair of bounds is a constant expression (`test_cxx.py` has a case of each kind).

Two listings differ from the page's in form, not in value: the page writes the radius of `ball_to_interval_2` as the 2-limb numbers $(-r, 0)$ and $(r, 0)$, and the listing makes them by `make_2` (whose guard leaves a radius as it is), so that no limb is added to a literal zero, which the C++ printer would write as an addition of $+0$, the form of a guard; `ball_split_2`, above, does the same with $\mp h$.

**In the formal models.** IEEE model only. `ball_of_interval` with `ieee1788` and a center of two limbs: `canonical_2 m0 m1`, the first conjunct, with no hypothesis beyond the requirement `interval_2` of $X$. `ball_of_interval` with `finite_when`: for `ieee1788`, `(interval_bounded_n X -> finite c /\ l <= c <= h /\ Rabs (c - m) <= ... /\ (r = infinity prec emax false \/ (finite r /\ forall z : R, in_interval_n X z -> Rabs (z - c) <= val r)) /\ (C -> finite r))`; for `ball`, `(interval_bounded_n X -> forall z : R, in_interval_n X z -> in_ball_n B z)` and `(interval_bounded_n X -> C -> ball_finite_n B /\ ...)`, C the conditions `Rabs (val xl0 + val xl1) <= bpow radix2 (emax - 2)` and the same of the upper bound. `interval_of_ball` of two limbs: the shape of the outward tightness of `encloses_interval` (`range_lower S (XFin lo)`, `range_upper S (XFin hi)`, the exact bound as `xval_2 zl0 zl1 = XFin lo`, and an infinite bound of the set as the infinity of $Z$), under `ball_finite_n` of the ball, and `bounded_when` as I5. `makes_ball` with `rel`: one conjunct more, for `xnonempty` finite bounds, `val lo <= c <= val hi /\ Rabs (c - m) <= ...` and the radius as `RU`.

## The line protocol

Runners and the oracle exchange text lines, the same on every platform and for every format.

```
request:    KERNEL FORMAT LIMB ... [#TAG]
completed:  KERNEL FORMAT LIMB ... [#TAG] -> LIMB ...
```

- Fields are separated by single spaces. A limb is a C99 hexadecimal floating-point literal as
  printed by `printf("%a")` or Python's `float.hex()`, or `inf`, `-inf`, `nan`. Every NaN is
  written `nan`, whatever its sign and payload: a line tells a NaN from a number, never one NaN
  from another, so where a claim compares limbs as they are (`ball_set`, "Y as it is") a NaN
  matches a NaN with neither sign nor payload compared, while a zero is written with its sign
  (`-0x0p+0`), which is compared where a claim says so.
- Input limbs are in the order of the kernel's `inputs`, most significant limb first; output
  limbs likewise. An interval is its two bounds, each a group, the lower first: the sum of two
  intervals of one limb is the line `interval_add_1 FORMAT xl xu yl yu`, completed with
  `-> zl zu`, and one of two limbs `interval_add_2 FORMAT xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1`,
  completed with `-> zl0 zl1 zu0 zu1`; the empty set of one limb is `inf -inf`, the whole line
  `-inf inf`. A mask is `0` or `1` as before (no kernel of the intervals has one).
- A runner reads requests on standard input and, for each, writes the same line followed by
  ` -> ` and the output limbs. It copies everything before the arrow unchanged, including an
  optional `#TAG`. The oracle's tags are `#STRATUM:INDEX`: the stratum the case belongs to and
  its index in the stream, from which the case can be regenerated. Lines starting with `#` are
  comments and are copied through; the oracle brackets a stream with two of them and uses them to
  detect dropped or added lines.
- The sign of a zero is compared only where a claim says so (the operands as they are of
  `ball_set`); everywhere else Kairn leaves it unspecified.
- Which backend or variant a runner uses is chosen on its command line, never in the stream.

**Folds** have requests of their own, with the arrays in the line:

```
request:    FOLD FORMAT ORDER N LIMB ... [#TAG]
completed:  FOLD FORMAT ORDER N LIMB ... [#TAG] -> RESULT ...
```

- `ORDER` is `seq` (the sequential order) or `lanes:W`, the lane order with $W$ lanes, $W$ a
  decimal number without leading zeros, `0` and `1` included (both are the sequential order).
- `N` is the number of elements, a decimal number; `0` is allowed.
- Then, for each array of the fold in the order of its `arrays`, and for each limb of that array,
  most significant first, the N entries of that limb: for `dot_2` of length 3,
  `x0[0] x0[1] x0[2] x1[0] x1[1] x1[2] y0[0] y0[1] y0[2] y1[0] y1[1] y1[2]`, $4N$ limbs in all,
  written as above.
- The results are the fold's `outputs` in order, limbs as above and a mask as `0` or `1`: for
  `dot_2` the two limbs of `r`, then `flag`.

For example, `dot_1 fp:5:-12:6 lanes:2 3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p+0 0x1p+0` is completed
with ` -> 0x1.cp+2 1`, and `sum_2 binary64 seq 0` with ` -> 0x0p+0 0x0p+0 1`. The interpreter
(`kairn-gen interp`) completes every order in every format, toy formats included. The compiled
runner (`gen/tests/runner.cpp`) completes `seq` with `F_seq` and `lanes:W` with `F_lanes`, for
any $W$, in `binary64` and `binary32`; the packed runner completes `lanes:W` with `F_packed` for
the one $W$ of its register and format (`packed_lanes`), and refuses any other order. The same
request gives the same bits from all three.

**Maps** have the requests of folds, with the limbs of the scalars, in the order of the map's
`scalars`, between the length and the arrays: `MAP FORMAT ORDER N SCALAR... LIMB...`. The result
is, for each limb array written, most significant first, its N entries, then the mask: for
`axpy_1 fp:5:-12:6 lanes:2 3 0x1p+1 0x1p+0 0x1p+1 0x1p+2 0x1p-1 0x1p-1 0x1p-1` (a = 2, x = 1, 2, 4,
y = 1/2, 1/2, 1/2) the completion ` -> 0x1.4p+1 0x1.2p+2 0x1.1p+3 1`. The interpreter, the
compiled runner (`F_seq`, `F_lanes` for any W) and the packed runner (`F_packed`, its register's W
only) complete them, with the same bits.

**Ball vectors** have the requests of maps, `BV FORMAT ORDER N SCALAR... LIMB...`, the scalars (the
radii and the others, in the order of the fold's `scalars`) between the length and the arrays of
centers. The result is, for each limb array of centers written, most significant first, its N
entries, then the radius, then the flag: for `bv_add_1 binary64 seq 2 0x1p-4 0x1p-4 0x1p+0 0x1p+1
0x1p+0 0x1p+0` ($x = (1, 2)$, $y = (1, 1)$, both of radius $\tfrac1{16}$) the completion
` -> 0x1p+1 0x1.8p+1 R 1`, R the radius, a little above $\tfrac18$; when the flag is `0` the centers
are `0x0p+0` and the radius `inf`, the whole space. The constructor has the same form, its one scalar
the radius given: `bv_make_1 binary64 seq 2 0x1p-4 -0x1p+0 0x1p+1` is completed with
` -> -0x1p+0 0x1p+1 0x1p-4 1`, and the same request with the radius `-0x1p-4` with
` -> 0x0p+0 0x0p+0 inf 0`. The interpreter, the compiled runner (`F_seq`, `F_lanes` for any W) and the
packed runner (`F_packed`, its register's W only) complete them, with the same bits.

**In place.** A map or a ball vector may write the array it reads (the array written being exactly
one of the arrays read, [Maps](#maps)). A request asks for that with one more field, `inplace=I`,
right after the length: `MAP FORMAT ORDER N inplace=I SCALAR... LIMB...`, I the index (from 0, in the
order of the fold's `arrays`) of an array read whose limbs are as many as those of the array written.
The compiled runners and the packed runner then pass that array's buffers as the array written; the
interpreter computes as without the field. The completion is that of the request without the field,
the field copied with the rest of the line before the arrow, and every claim is judged as for that
request: in place changes nothing that is claimed. For example `add_2 binary64 seq 2 inplace=1 0x1p+0
0x1p+1 0x0p+0 0x0p+0 0x1p-1 0x1p-1 0x0p+0 0x0p+0` ($y \leftarrow x + y$, $x = (1, 2)$, $y = (\tfrac12,
\tfrac12)$) is completed with ` -> 0x1.8p+0 0x1.4p+1 0x0p+0 0x0p+0 1`, and `bv_add_1 binary64 lanes:2 2
inplace=0 0x1p-4 0x1p-4 0x1p+0 0x1p+1 0x1p+0 0x1p+0` ($x \leftarrow x + y$) as the same request without
`inplace=0`. A request whose I is not such an array, or of a fold that is not a map or a ball vector,
is refused. The generator's tests (`test_bv.Cxx.test_in_place`, `test_bv.Packed.test_in_place`) run
every map and every ball vector in place this way, with each array that can be written, through every
build of the runners, and find the completions of the requests without the field.

**Convolutions** have two lengths, and the sequential order only:

```
request:    CONV FORMAT seq N_X N_Y LIMB ... [#TAG]
completed:  CONV FORMAT seq N_X N_Y LIMB ... [#TAG] -> RESULT ...
```

- `ORDER` is `seq`; any other order is refused. `N_X` and `N_Y` are the lengths of the two arrays,
  decimal numbers, `0` allowed.
- Then, for each limb of the first array, most significant first, its `N_X` entries; then, for each
  limb of the second, its `N_Y` entries: for `conv_2` of lengths 2 and 3,
  `x0[0] x0[1] x1[0] x1[1] y0[0] y0[1] y0[2] y1[0] y1[1] y1[2]`.
- The result is, for each limb array written, most significant first, its $N_Z$ entries, with
  $N_Z = N_X + N_Y - 1$, or $0$ when `N_X` or `N_Y` is $0$; then the mask, `0` or `1`.

For example `conv_1 fp:5:-12:6 seq 3 2 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1` ($x = 1, 2, 4$ and
$y = 1, \tfrac12$: the product of $1 + 2t + 4t^2$ and $1 + \tfrac12 t$) is completed with
` -> 0x1p+0 0x1.4p+1 0x1.4p+2 0x1p+1 1` ($1, \tfrac52, 5, 2$), and `conv_2 binary64 seq 0 1 0x1p+0
0x0p+0` with ` -> 1`. The interpreter and the compiled runner (`F_seq`) complete them, with the same
bits; the packed runner refuses them, a convolution having no packed form.

**The products of two BallVectors** have the requests of convolutions, with the limbs of the scalars,
the two radii in the order of the fold's `scalars`, between the lengths and the arrays:

```
request:    BV_CONV FORMAT seq N_X N_Y RX RY LIMB ... [#TAG]
completed:  BV_CONV FORMAT seq N_X N_Y RX RY LIMB ... [#TAG] -> RESULT ...
```

The result is, for each limb array written, most significant first, its $N_Z$ coefficients, then the
radius, then the flag; when the flag is `0` the coefficients are `0x0p+0` and the radius `inf`, the whole
space. For example `bv_conv_1 binary64 seq 3 2 0x1p-4 0x1p-3 0x1p+0 0x1p+1 0x1p+2 0x1p+0 0x1p-1` ($x = 1,
2, 4$ of radius $\tfrac1{16}$ and $y = 1, \tfrac12$ of radius $\tfrac18$) is completed with ` -> 0x1p+0
0x1.4p+1 0x1.4p+2 0x1p+1 R 1`, R the radius, `0x1.240000000000dp+0`, a little above $2(4 \cdot \tfrac18 +
1 \cdot \tfrac1{16} + \tfrac1{128}) = 1.140625$ ($m = 2$, $M_a = 4$, $M_b = 1$); and
`bv_conv_2 binary64 seq 0 1 0x1p-4 0x1p-3 0x1p+0 0x0p+0`, an empty operand, with ` -> 0x0p+0 1`, no
coefficient and the radius $+0$. The interpreter and the compiled runner (`F_seq`) complete them, with the
same bits; the packed runner refuses them.

The constants of `include/kairn/rational.hpp`, which are not kernels, have lines of their own
([Constants from fractions](../reference/rational.md)): `rational_K FORMAT NUM DEN [#TAG]`, with K
the number of limbs (1 or 2) and NUM and DEN decimal signed 64-bit integers (DEN may be 0); the
runner (`tests/api/rational_runner.cpp`) adds ` -> `, the K limbs of the value, the error, and `0`
or `1` for exact, the limbs written as above. The specification fixes every bit, so the oracle
compares each completed line for equality.

The oracle generates requests (case $i$ of a given generator and seed is computed without
generating the others; for toy formats it can enumerate every operand combination), and checks
completed lines: the requirements first (a case that violates them is reported as invalid, never
as passed), then every `ensures` entry, in exact arithmetic.

## When an operation is done

1. Its statement has survived exhaustive testing on toy formats (interpreter as the runner,
   oracle as the judge).
2. Rocq accepts the proof of the generated statement, and the audit passes.
3. The generated code passes the quick and brute-force tiers against the oracle on every
   supported platform.
4. Its compiled code contains the expected number of fused instructions across the flag matrix:
   the object-code check (`tests/objcode/objcode.py`, tests `objcode.*` and `full.objcode.*`)
   compares the fused multiply-adds and the plain multiplications of every kernel, scalar and
   packed, with what `gen/objcode.json` says its IR asks for, under every setting of contraction,
   optimization level and `-frounding-math` of each compiler of the CI
   ([Testing](testing.md#object-code)).
5. Its reference page is generated from the claims.
