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
| `gen/objcode.json` | Generated and committed: the fused multiply-adds and plain multiplications that each kernel's code asks for, for the object-code check. | — |
| `include/kairn/gen/` | Generated and committed C++ kernels. | — |
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
both executions. What is proved (`proofs/theories/IeeeTwoExecutions.v`) is that the eight kernels
of the rule that are more than one product give outputs of the same value in both executions, on
all operands (finite, infinite and NaN): each listing is written there once more with the
product as a parameter, which with the FMA is the generated model by `reflexivity`, and with the
plain product is the execution of constant evaluation (`IeeeProduct.v` compares the two products
of `rmul` and `mul_1_1`); what is tested rather than proved is that the C++ compiled for
constant evaluation is that listing: the generator's tests check that the two executions give
the same bits, or for the kernels whose outputs can be an exact zero product the same values
(`gen/tests/test_interp.py`, `TwoExecutionsOfAProduct`; `test_cxx.py` ties the C++ to them). The
kernels `constexpr` by this rule are `rmul`, `mul_1_1`, `split`, `two_prod_dekker`, `mul_pow2_2`,
`mul_pow2_2_full`, `ball_mul_pow2_k` with its full form, and the bound kernels of the folds,
`bound_sum_k` and `bound_dot_k`; `build` lists them.

C++ emission rules: non-template functions, one overload per limb type; one operation per
statement; kernels of at most two limbs are force-inlined. The public operations of `Ball` that
round are functions of `ball_operations.hpp` that force-inline their kernel and are themselves
forced inline (the default), outlined or external, as `KAIRN_ENCLOSURE_CODE` says
([Getting started](../getting-started/index.md#compile-time-and-the-operations-of-ball)); the code
of the kernel is the same in each, and the generated files do not depend on the setting. A kernel is `constexpr` when its only
fused operations are `prod` or it names a constant-evaluation variant; a kernel that is not
`constexpr` is listed as such in the generator's output. `guard` and `times_inf` dispatch on
`__builtin_is_constant_evaluated()` too, so the full kernels of the additions and the constructors
are `constexpr`; the products of two limbs, the Ball cores and their full kernels are not, because
they contain FMAs with an addend that is not zero, and so are not the directed products of one
limb, `mul_down_1` and `mul_up_1`, which must not be evaluated through `two_prod`'s variant
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
status:        unverified
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
  and the fold returns its state). `writes: none`: a map, whose step also returns elements of
  arrays it writes, is not in this stage of the generator.
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
element through `guard`, and `dot_1` (the fused step `dot_step_1`, `t = fma(x, y, s)`) and `dot_2`
(`dot_step_2`: `p = mul_2_2(x, y); t = add_2_2(s, p)`), whose arrays are supplied and need no
guard: their steps only multiply their elements. The finishes `fold_finish_1` and
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
   no guard (`dot_k`). The state is not a value of the program. A stored array is asked nothing.
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
- `Audit.v`: for every kernel not marked `unverified`, a silent definition
  `<kernel>_audit : <kernel>_spec := <kernel>_correct`, which fails to compile unless the theorem
  has the generated statement as its type, followed by `Print Assumptions <kernel>_correct`. The
  file prints nothing else, so that the audit script can refuse any output it does not understand.
  A fold marked `proved` adds the same two lines for each of its orders (`<fold>_seq_correct`,
  `<fold>_lanes_correct`); `FoldStatements.v` is imported only then, so that the file does not
  change while every fold is `unverified`.
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
| `upper` | as before | the output is a NaN exactly when an operand is a NaN or the operation is $0 \cdot \infty$; otherwise it is not below `value`, and `gaps` applies when it is finite |

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
kernel has a condition; `ball_neg_k` has none.

The `core` of `extends` has the inputs of the full kernel, by name, and outputs of the same shape
under other names; they correspond by position. Its requirements are the full kernel's with
`normalized` for `canonical`.

Two more kinds serve the constructors
([values that enter from the program](design/milestone1.md#values-that-enter-from-the-program)):

| Kind | Fields | Meaning |
|---|---|---|
| `represents` | `of` | the output is canonical and is `value` exactly: a finite `value` gives a finite normalized output of that value, $\pm\infty$ gives $(\pm\infty, 0)$, a NaN gives all NaN |
| `makes_ball` | `center`, `radius`: the outputs; `from`: the inputs given as center and radius | the output ball is canonical: empty when the given radius is a NaN or negative; otherwise the whole line when the given center is not finite or the given radius is $+\infty$; otherwise the given center and radius, exactly |

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

`steps` is a JSON integer; `when` of `rounded` is absent when there is no condition (an `error`
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
  "min_precision": 4, "status": "unverified",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "bound_sum_1",
  "inputs": [{"name": "m", "limbs": 1}],
  "outputs": [{"name": "g", "limbs": 1}, {"name": "ok", "limbs": 1, "type": "mask"}],
  "requires": ["count(m)", "format(half)"],
  "ensures": [{"kind": "holds", "rel": "le", "args": ["m*unit(add_1_1)", "1/2"], "if": "ok"},
              {"kind": "upper", "of": "g", "value": "m*unit(add_1_1)/(1-m*unit(add_1_1))", "if": "ok"}],
  "min_precision": 1, "status": "unverified",
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
  "min_precision": 4, "status": "unverified", "theorems": {"sequential": null, "lanes": null},
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

## The line protocol

Runners and the oracle exchange text lines, the same on every platform and for every format.

```
request:    KERNEL FORMAT LIMB ... [#TAG]
completed:  KERNEL FORMAT LIMB ... [#TAG] -> LIMB ...
```

- Fields are separated by single spaces. A limb is a C99 hexadecimal floating-point literal as
  printed by `printf("%a")` or Python's `float.hex()`, or `inf`, `-inf`, `nan`.
- Input limbs are in the order of the kernel's `inputs`, most significant limb first; output
  limbs likewise.
- A runner reads requests on standard input and, for each, writes the same line followed by
  ` -> ` and the output limbs. It copies everything before the arrow unchanged, including an
  optional `#TAG`. The oracle's tags are `#STRATUM:INDEX`: the stratum the case belongs to and
  its index in the stream, from which the case can be regenerated. Lines starting with `#` are
  comments and are copied through; the oracle brackets a stream with two of them and uses them to
  detect dropped or added lines.
- The sign of a zero is never compared: Kairn leaves it unspecified.
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
