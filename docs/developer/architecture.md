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
| `prod a b` | $\mathrm{RN}(ab)$ | `fma(a, b, +0.0)`: the *opaque product* |
| `muladd a b c` | $\mathrm{RN}(ab + c)$ **or** $\mathrm{RN}(\mathrm{RN}(ab) + c)$, the compiler's choice | `a * b + c`; its theorem covers both |
| `lt`, `le`, `eq` | comparison, giving a mask | comparison; `lt(a, b)` and `le(a, b)` are written `b > a` and `b >= a`, which one compiler's constant evaluator gets right on a NaN where it gets `<` and `<=` wrong |
| `and`, `or`, `not` | on masks | |
| `select m a b` | $a$ if $m$, else $b$ | conditional move or blend, never a branch |
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
   `times_inf`, which is exact and whose result is only compared or selected.
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
in none, on those compilers and on the settings that do not contract. Clang 18 on x86-64 under
`-ffp-contract=fast` left those three forms alone and fused the radius and the one-limb center
given to a `Ball` instead; the guard covers these too
(`tests/api/boundary.cpp`, with a control that fails when the guard is taken out). The guard relies on what
the opaque product already relies on: the compiler honors the sign of zero, so it may not remove
`a + 0`. Until the generator emits `guard` and checks the rule, the public headers apply it by
hand in one helper.

One compiler does not fit that description. MSVC 19.52 removes the addition of zero for some
operands under `/O2`: a guarded $-0$ stays $-0$ (values are unaffected, and the sign of a zero is
unspecified). In every test so far it still kept the program's product out of the kernel under
`/fp:contract`, the one MSVC setting that contracts, which is not its default: 0 of 200 000 cases
differ with the guard and all of them without it. On MSVC the guard therefore rests on those
tests, which run on every change, and not on a rule of the language.

A kernel may name a second kernel as its **constant-evaluation variant**. The emitted C++
function then dispatches on `__builtin_is_constant_evaluated()`. Inside such a variant, `prod` is
emitted as `a * b`, because there is no FMA in constant evaluation and no contraction either. The
variant has its own statement and proof.

C++ emission rules: non-template functions, one overload per limb type; one operation per
statement; kernels of at most two limbs are force-inlined. A kernel is `constexpr` when it
contains no fused operation or names a constant-evaluation variant; a kernel that is not yet
`constexpr` is listed as such in the generator's output. `guard` and `times_inf` dispatch on
`__builtin_is_constant_evaluated()`, so the full kernels of the additions and the constructors
are `constexpr`; the product kernels are not yet, because their cores contain fused operations
and only `two_prod` has a constant-evaluation variant.

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
  over `R`. `prod a b` is `rnd (a * b + 0)`, `fms a b c` is `rnd (a * b + - c)`; a `call` stays a
  call (`let '(sh, sl) := two_sum x0 y0 in`), so that a proof can use the callee's theorem.
- `Statements.v`: one `Definition <kernel>_spec : Prop` per kernel, built from the kernel's
  claims. A hand-written proof must have exactly this type. A statement quantifies over every
  `emin` and every `prec` from the kernel's minimum on, and fixes the tie rule to ties-to-even.
  It assumes that every input limb is a number of the format and concludes, before the claims,
  that every output limb is one too (unless a `normalized` claim on that output already says
  so), so that the theorem of one kernel establishes the hypotheses of the next.
- `Audit.v`: for every kernel not marked `unverified`, a silent definition
  `<kernel>_audit : <kernel>_spec := <kernel>_correct`, which fails to compile unless the theorem
  has the generated statement as its type, followed by `Print Assumptions <kernel>_correct`. The
  file prints nothing else, so that the audit script can refuse any output it does not understand.

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
`[{"abs_le": "x", "exp": -2}, {"abs_le": "y", "exp": -2}]` and `mul_2_2_full` has
`[{"abs_le": "x*y", "exp": -1}]`. The list is empty when no condition is proved, and an empty
list claims nothing about when the result is finite: it does not say that it always is.

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

`status` and `theorem` keep referring to the real-model statement where there is one. A kernel
of the extended domain also carries `ieee_status` (`proved` or `unverified`) and, when proved,
`ieee_theorem`; for a full kernel or a constructor, which has no real-model statement, `status`
is its `ieee_status`. The oracle judges the claims whatever the statuses say.

Three entries in full, as the generator writes them (`source`, `flops` and the theorem fields
left out):

```json
{
  "name": "add_2_1_full", "domain": "extended",
  "inputs": [{"name": "x", "limbs": 2}, {"name": "a", "limbs": 1}],
  "outputs": [{"name": "w", "limbs": 2}],
  "value": "x+a",
  "requires": ["canonical(x)"],
  "ensures": [{"kind": "extends", "of": "w", "core": "add_2_1", "lead": "add", "finite_when": []}],
  "min_precision": 3, "status": "unverified", "ieee_status": "unverified",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_mul_2_full", "domain": "extended",
  "inputs": [{"name": "cx", "limbs": 2}, {"name": "rx", "limbs": 1},
             {"name": "cy", "limbs": 2}, {"name": "ry", "limbs": 1}],
  "outputs": [{"name": "cw", "limbs": 2}, {"name": "rw", "limbs": 1}],
  "value": "cx*cy",
  "requires": ["ball(cx, rx)", "ball(cy, ry)"],
  "ensures": [{"kind": "encloses", "center": "cw", "radius": "rw", "set": "x*y",
               "balls": {"x": {"center": "cx", "radius": "rx"}, "y": {"center": "cy", "radius": "ry"}},
               "finite_when": []}],
  "min_precision": 4, "status": "unverified", "ieee_status": "unverified",
  "instances": {"binary64": [], "binary32": []}
},
{
  "name": "ball_make_2", "domain": "extended",
  "inputs": [{"name": "c", "limbs": 2}, {"name": "r", "limbs": 1}],
  "outputs": [{"name": "cw", "limbs": 2}, {"name": "rw", "limbs": 1}],
  "requires": ["canonical(c)"],
  "ensures": [{"kind": "makes_ball", "center": "cw", "radius": "rw", "from": {"center": "c", "radius": "r"}}],
  "min_precision": 1, "status": "unverified", "ieee_status": "unverified",
  "instances": {"binary64": [], "binary32": []}
}
```

The minimum precision of a full kernel is that of its core. In the extended domain the scalar of
`ball_scale` is any value of the format, $\pm\infty$ or NaN, and one that is not finite gives the
whole line (the empty set if the ball operand is empty). `make_2_limbs` takes its two limbs as one
2-limb input with `canonical`.

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
4. Its compiled code contains the expected number of fused instructions across the flag matrix.
5. Its reference page is generated from the claims.
