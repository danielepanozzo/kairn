# The generator

Every arithmetic kernel of Kairn is described once, in `gen/kernels/`. From those descriptions
this generator prints the formal model that the proofs are about and the C++ that ships, so that
both say the same thing. Nothing proves that its two printers agree, which puts the generator in
the trusted base: it is written to be read in one sitting, uses only Python's standard library, and
is tested against the hardware, the compilers and Rocq. The contract it implements is
[`docs/developer/architecture.md`](../docs/developer/architecture.md).

```
python3 gen/kairn-gen build     # regenerate every generated file
python3 gen/kairn-gen check     # fail if a committed generated file is stale or was edited by hand
python3 gen/kairn-gen test      # the tests below; --full for the long sizes
python3 gen/kairn-gen interp    # the exact interpreter, as a runner of the line protocol
```

## What it writes

| File | Content |
|---|---|
| `proofs/gen/Model.v` | One Rocq `Definition` per kernel over the reals, each operation one rounding by Flocq's `round`, calls kept as calls |
| `proofs/gen/Statements.v` | `Definition K_spec : Prop` per kernel, from its claims; the proof `K_correct` must have this type |
| `proofs/gen/Audit.v` | For each kernel not marked unverified, checks `K_correct : K_spec` and prints its assumptions |
| `proofs/gen/IeeeModel.v` | One Rocq `Definition` per kernel that has an IEEE-model statement, over Flocq's binary floating-point numbers (signed zeros, infinities, NaN), each operation the one of `proofs/theories/IeeeOperations.v` |
| `proofs/gen/IeeeStatements.v` | `Definition K_ieee_spec : Prop` (and the finite-domain forms) per such kernel, from its claims, in the vocabulary of `proofs/theories/IeeeVocabulary.v` |
| `proofs/gen/IeeeAudit.v` | For each kernel whose IEEE-model status is not unverified, checks that its theorem has the generated statement as its type and prints its assumptions |
| `proofs/gen/FoldModel.v` | Per fold, its step and combination over tuples of reals and its two orders, `fold_seq` and `fold_lanes` of `proofs/theories/Folds.v` |
| `proofs/gen/FoldStatements.v` | `Definition F_seq_spec : Prop` and `F_lanes_spec` per fold, from its claims; the proofs `F_seq_correct` and `F_lanes_correct` must have these types |
| `include/kairn/gen/prelude.hpp` | The force-inline macro, the FMA primitive per compiler, `abs_bits`, `next_up_bits`, `next_down_bits`, the form of the scalar fix-ups per compiler (`KAIRN_GEN_FIXUP_CALL`), the pragmas that every header puts around its declarations so that a program's globals of the same names raise no warning (`KAIRN_GEN_PUSH_WARNINGS`, `KAIRN_GEN_POP_WARNINGS`); refuses x86 without hardware FMA |
| `include/kairn/gen/scalar.hpp` | Every kernel for `double` and `float`, in `kairn::gen`; where the fix-up is a function of its own, that function, in `kairn::gen::fixup`; then every fold, `F_seq` and `F_lanes` |
| `include/kairn/gen/avx2.hpp` | Every kernel for `__m256d` and `__m256` (4 doubles, 8 floats), then every fold's `F_packed`; refuses a target without AVX2 and FMA |
| `include/kairn/gen/neon.hpp` | Every kernel for `float64x2_t` and `float32x4_t` (2 doubles, 4 floats), then every fold's `F_packed`; AArch64 only |
| `include/kairn/gen/bounds.hpp` | Per kernel and limb type, whether it is proved and, only then, the constants of its error claim rounded up (`unit`, `tiny`, and for the form relative to the result `unit_computed`, `tiny_computed`) and its form: `result` (R), `operands` (A) or `terms` (T, the terms of the value: `dot_step_2`); what the public headers gate on and export through `kairn::traits` |
| `include/kairn/gen/selftest.hpp` | Every kernel on fixed operands, with the results the interpreter computes: the stored bit patterns of `kairn::self_test()` |
| `gen/claims.json` | What every kernel and every fold claims, with the constants per format as exact fractions |
| `gen/objcode.json` | Per kernel, form of its C++ (scalar with the fix-up inline, scalar with the fix-up a function of its own, packed) and limb type, the fused multiply-adds and plain multiplications its code asks for; per fold, form and limb type, those of each part of its loop: the expectations of the object-code check (`tests/objcode/`) |
| `gen/tests/runner_kernels.inc` | The table of kernels and folds of the C++ runners `gen/tests/runner.cpp` and `packed_runner.cpp` |

`Model.v`, `Statements.v` and `Audit.v` are the real model only. The full kernels and the
constructors of the non-finite layer have no real-model statement and are not in them; a kernel of
the extended domain that has one (the comparisons, the conversions, `neg_2`, `abs_2`, `radd`,
`rmul`) is printed there with its requirement `canonical` read as `normalized`.

`build` also lists the kernels that are unverified (in the real model, and in the IEEE model), those
without a real-model statement, those that are not `constexpr`, those exempt from the non-finite
cone, the entry kernels, the guards of rule R3 that are pending, the kernels accepted only
through a pending guard, the folds and those of them that are unverified. `proofs/gen` is mapped
to the logical path `Kairn.Gen`, and `proofs/theories` to `Kairn`.

## The code

| Module | Does |
|---|---|
| `kairn_gen/ir.py` | The IR: its operations, kernels, the description format, inlining of calls |
| `kairn_gen/expr.py` | The parser of the rational expressions of the claims (`3/(1-4*u)`); nothing is ever `eval`-ed |
| `kairn_gen/rules.py` | The checks every kernel passes before anything is printed |
| `kairn_gen/rocq.py` | The Rocq printer (trusted) |
| `kairn_gen/cpp.py` | The C++ printer (trusted) |
| `kairn_gen/simd.py` | The AVX2 and NEON printers (trusted; tested lane by lane against the scalar code) |
| `kairn_gen/consts.py` | The exact value of every constant in any format, `unit_computed(K)` and `tiny_computed(K)` included |
| `kairn_gen/claims.py` | `gen/claims.json` |
| `kairn_gen/objcode.py` | `gen/objcode.json`: the counts below |
| `kairn_gen/library.py` | `bounds.hpp` and `selftest.hpp`, for the hand-written public headers |
| `kairn_gen/interp.py` | The interpreter: exact integer arithmetic on any format `(p, qmin, qmax)` |
| `kairn_gen/build.py` | What `build` writes and `check` compares |

## A kernel description

One file per kernel, `gen/kernels/NAME.kernel`; the format is documented at the top of `ir.py`.

```
kernel:        add_2_1
input:         x = x0 x1
input:         a
output:        z = z0 z1
value:         x+a
requires:      normalized x
ensures:       normalized z
ensures:       error z R c=2 k=2 t=0
theorem:       proofs/theories/Add21.v add_2_1_correct
source:        JMP17 Alg. 4 (DWPlusFP); bound from MR22
license:       algorithm: published; proof: MIT
status:        unverified

(sh, sl) = two_sum(x0, a)
v        = add(x1, sl)
(z0, z1) = fast_two_sum(sh, v)
```

Value names are normative: the model, the C++ and the proofs use them. In C++ a call is inlined
and a value defined inside the callee is named `SITE_VALUE` (`sh_bb` above), which is why a value
name has no underscore.

The non-finite layer (architecture.md, "Claims of the non-finite layer"; milestone1.md, "IEEE-like
results") adds, for example:

```
kernel:        add_2_2_full
input:         x = x0 x1
input:         y = y0 y1
output:        w = w0 w1
value:         x+y
requires:      canonical x                  finite and normalized, (±inf, ±0) or all NaN
requires:      canonical y
ensures:       extends w core=add_2_2 lead=add finite_when=abs_le(x,-2);abs_le(y,-2)
min_precision: 3
status:        unverified                   no real-model statement: status is ieee_status
domain:        extended                     operands may be infinite or NaN
ieee_status:   unverified                   the IEEE-model statement; ieee_theorem once proved
entry:         yes                          the public headers may call it (rule R3)
cone_exempt:   the fix-up selects, after an explicit test that z0 is finite (f), ...

(z0, z1) = add_2_2(x0, x1, y0, y1)
t        = add(x0, y0)
...
```

- `input: stored rx` (a one-limb input that is a limb of an object, in an entry kernel) and
  `input: supplied y = h l` (a multi-limb input whose limbs the program gives, as in
  `make_2_limbs`).
- `requires: ball cx rx`; `ensures: encloses cw rw x*y x=cx,rx y=cy,ry [finite_when=...]`;
  `ensures: represents x`; `ensures: makes_ball cw rw from=c,r`.
- A condition of `finite_when` is `abs_le(EXPR,E)`, meaning $|EXPR| \le 2^{q_{\max} + p + E}$;
  several are separated by `;`, and an empty list is written by leaving `finite_when` out.
- Milestone 2 (architecture.md, "Claims of Milestone 2"): `ensures: neighbor r up` (or `down`);
  `ensures: bound r below steps=1` (or `above`); `ensures: rounded r down when=product_large`; and
  `exact_when=CONDITIONS` after an `error` or an `encloses` entry, a condition being
  `zero_or_abs_gt(EXPR,K)` or `zero_or_abs_ge(EXPR,K)` (EXPR $= 0$ or $|EXPR| > K$, or $\ge K$),
  with EXPR over the input names and their limbs, `cx[1]` the second limb of `cx`, and K an exact
  expression over `u`, `eta` and integers; several are separated by `;`, as in
  `exact_when=zero_or_abs_gt(cx[0]*c,eta/(2*u));zero_or_abs_gt(rx*c,eta/(2*u))`.
- `guard_pending: a REASON`: an input of an entry kernel whose guard is not written yet (only
  `add_2_1`, whose guard changes the formal model of a proved kernel and lands with its proof).
- The folds' stage (architecture.md, "Claims of Milestone 2"): `requires: count m` ($m = 0$ or
  $m \ge 1$) and `requires: format half` ($\eta \le \tfrac12$); `error t T c=... k=2 t=2`, the
  form relative to the terms of `value`; `upper g value=EXPR if=ok`, the output at least EXPR when
  the mask `ok` is true, EXPR over the inputs, the one-limb outputs, `u`, `eta`, `unit(K)` and
  `tiny(K)`, with `^`; `holds le EXPR EXPR if=ok`; and `finite_or_nan r flag=f`, a fold's finish.
  A kernel whose every entry has its own value (`bound_sum_k`, `bound_dot_k`) has no `value:`.

## A fold description

One file per fold, `gen/kernels/NAME.fold`, beside the kernels; the format is documented at the top
of `ir.py`, and what it means in architecture.md, "Folds".

```
fold:          sum_2_entry
arrays:        supplied x = x0 x1                one array per limb; stored or supplied (rule R3)
state:         s = s0 s1                         starts at zero, every limb +0
step:          s = sum_entry_step_2(s, x)        a kernel: the state and one element, to the next state
combine:       s = add_2_2(s, s)                 a kernel: two states into one (the lane order)
orders:        sequential, lanes
writes:        none                              a map's written arrays: not in this stage
output:        r = r0 r1
output:        mask flag
finish:        (r, flag) = fold_finish_2(s)      a kernel on the final state, or none
value:         x                                 the value of one element; the fold's is their sum
requires:      canonical x                       of every element
ensures:       normalized r
ensures:       fold_error r eps=3*u^2/(1-4*u) rel=n-1     abs= is rel's when left out
ensures:       finite_or_nan r flag=flag
min_precision: 3
status:        unverified                        or proved, with theorem: FILE
domain:        extended
source:        Higham's bound for summation over any tree, with the bound of add_2_2 (MR22)
license:       bound: published; proof: MIT
```

`fold_error r eps=E term=T tau=A rel=H abs=H'` claims
$\lvert r - \sum_i v_i\rvert \le ((1 + T)(1 + E)^{H} - 1)\sum_i\lvert v_i\rvert + (1 + E)^{H'}\,n\,A$,
$H$ and $H'$ being `n` or `n-1`, natural numbers; `term` and `tau` are 0 when left out, and
`abs` is `rel`. A fold has
no listing: its step, combination and finish are kernels, checked by every rule of a kernel, and
the generator checks the fold itself as architecture.md, "Folds", says (`rules.fold_rules`): its
names, the shapes of its parts, rule R3 on a supplied array (`rules._fold_r3`), the four
properties of the zero state (`rules.zero_state`, with a lemma of `SummationKernels.v` per
combination, `rules.ZERO_LEMMAS`), its claims, and `eps` against the combination's bound
(`rules._eps_of_combination`). The printers are `cpp.folds` (`F_seq`, `F_lanes`), `simd.fold_packed`
(`F_packed`), `rocq.fold_model` and `rocq.fold_statements`, `claims.fold_claims` and
`objcode.fold_counts`; the interpreter evaluates a fold with `Machine.run_fold` in either order and
any number of lanes, and completes its requests (architecture.md, "The line protocol").

## The operations

| IR | Interpreter | Rocq (`rnd` rounds to nearest) | C++ | AVX2 (`pd`; `ps` for float) | NEON (`f64`; `f32`) |
|---|---|---|---|---|---|
| `add a b`, `sub a b` | RN(a ± b) | `rnd (a + b)`, `rnd (a - b)` | `a + b`, `a - b` | `_mm256_add_pd`, `_sub_` | `vaddq_f64`, `vsubq_` |
| `neg a`, `abs a` | exact | `- a`, `Rabs a` | `-a`, `abs_bits(a)` | xor, andnot with `-0.0` | `vnegq`, `vabsq` |
| `fma a b c` | RN(ab + c) | `rnd (a * b + c)` | `fma_rn(a, b, c)` | `_mm256_fmadd_pd` | `vfmaq(c, a, b)` |
| `fms a b c` | RN(ab − c) | `rnd (a * b + - c)` | `fma_rn(a, b, -c)` | `_mm256_fmsub_pd` | `vfmaq(vnegq(c), a, b)` |
| `fnma a b c` | RN(−ab + c) | `rnd (- (a * b) + c)` | `fma_rn(-a, b, c)` | `_mm256_fnmadd_pd` | `vfmsq(c, a, b)` |
| `prod a b` | RN(ab + 0); RN(ab), the plain product, in constant evaluation | `rnd (a * b + 0)` | `fma_rn(a, b, 0.0)`; in a kernel `constexpr` by the rule of the product `__builtin_is_constant_evaluated() ? a * b : fma_rn(a, b, 0.0)` | `fmadd` with `setzero` | `vfmaq` with `+0.0` |
| `muladd a b c` | RN(ab + c) or RN(RN(ab) + c), by `--muladd` | `if fuse_V then … else …` | `a * b + c` | `add(mul(a, b), c)` | `vaddq(vmulq(a, b), c)` |
| `lt`, `le`, `eq` | IEEE comparisons | `Rlt_bool`, `Rle_bool`, `Req_bool` | `lt(a, b)` as `b > a`, `le(a, b)` as `b >= a` (MSVC's constant evaluator takes `<`, `<=` with a NaN for true), `==` | `_mm256_cmp_pd`, `_CMP_*_OQ` | `vcltq`, `vcleq`, `vceqq` |
| `and`, `or`, `not` | on masks | `andb`, `orb`, `negb` | `&`, `\|`, `!` | `and`, `or`, `not_mask` | `vandq_u64`, `vorrq_u64`, `not_mask` |
| `select m a b` | a if m else b | `if m then a else b` | `m ? a : b` | `_mm256_blendv_pd(b, a, m)` | `vbslq(m, a, b)` |
| `succ a`, `pred a` | IEEE nextUp, nextDown | Flocq's `succ`, `pred` | `next_up_bits(a)`, `next_down_bits(a)` | `next_up_bits`, `next_down_bits` on integer lanes | the same |
| `copy a` | a | `a` | `a` | `a` | `a` |
| `guard a` | RN(a + 0): a, with −0 made +0; a itself in constant evaluation | `rnd (a + 0)` | `a + 0.0` (never `a - 0`); in a `constexpr` kernel `__builtin_is_constant_evaluated() ? a : a + 0.0` | `_mm256_add_pd(a, _mm256_setzero_pd())` | `vaddq_f64(a, vdupq_n_f64(0.0))` |
| `times_inf t` | t · (+∞), exact: NaN for a NaN or a zero, else ±∞ with t's sign | none (no infinity in the real model) | `t * std::numeric_limits<double>::infinity()`; in a `constexpr` kernel `times_inf_ce(t)` (comparisons) in constant evaluation | `_mm256_mul_pd(t, _mm256_set1_pd(` +∞ `))` | `vmulq_f64(t, vdupq_n_f64(` +∞ `))` |
| `0` | +0 | `0` | `0.0` | `_mm256_setzero_pd()` | `vdupq_n_f64(0.0)` |
| `const NAME` | `consts.value` | `rocq.CONSTANTS`, or `unit_computed_K` | a hexadecimal literal | `_mm256_set1_pd(literal)` | `vdupq_n_f64(literal)` |
| `const up(EXPR)` | EXPR rounded up (`consts.value`) | `up_K_i := round … Zceil (EXPR)` | a hexadecimal literal | `_mm256_set1_pd(literal)` | `vdupq_n_f64(literal)` |
| `const inf`, `const nan` | +∞, a quiet NaN | none: only kernels without a real-model statement name them | `std::numeric_limits<double>::infinity()`, `quiet_NaN()` | `_mm256_set1_pd(` that `)` | `vdupq_n_f64(` that `)` |
| `K(args)` | evaluated as a call | `let '(…) := K args in` | inlined | inlined | inlined |

A mask is a `bool` in Rocq and in scalar C++, a lane mask (every bit of a lane set or clear) in
the packed code: `__m256d`/`__m256` for AVX2, `uint64x2_t`/`uint32x4_t` for NEON. In the line
protocol it is `0` or `1`.

`const unit_computed(K)` and `const tiny_computed(K)` are the constants of K's one error entry
(of form R, unconditional), unit/(1 − unit) and tiny/(1 − unit) with unit = c u^k and tiny = t η,
rounded up to the format; the ball kernels add them to a radius to cover the error of the center.
They are computed exactly for every format, toy formats included (`consts.py`), and in Rocq they
are definitions over the reals with Flocq's `round … Zceil`. A kernel may use them only if K is
proved, or if it is itself unverified, and only from K's minimum precision on.

`const up(EXPR)` is the smallest number of the format not below EXPR, which must be positive: an
exact expression over `u`, `eta`, integers, `unit(K)` and `tiny(K)` (K's c u^k and t η, from its
one error entry, of form R and unconditional), with `+ - * /`, parentheses and integer powers
(`^`, also negative). For example `const up((1+u)^6)`,
`const up(unit(mul_2_2)/(1-unit(mul_2_2))*(1+u))`, and with spaces, which mean nothing,
`const up((1+u)*((1+u)^5*2*eta + tiny(mul_2_2)/(1-unit(mul_2_2)) + eta/2))`. It is computed exactly
for every format (`consts.py`, below η it is η); C++ prints it as an exact hexadecimal literal per
type; Rocq as one definition per distinct constant, `up_K_i` after the first kernel K that uses it,
`round radix2 (FLT_exp emin prec) Zceil (EXPR)` with u, η, `unit(K)` and `tiny(K)` spelled out. The
rules of `unit_computed` apply (K proved unless the kernel is unverified, its minimum precision at
least K's), and the expression is checked to be positive in binary64 and binary32.

The Rocq model is one section over `emin prec choice`. Closing it abstracts each definition over
the section variables it uses and only those (`lt_2_2` takes four reals, `to_down_2` takes
`emin prec` first), and the statements apply each kernel accordingly (`rocq.section_args`).

The conclusion of a statement starts with `fmt` of every output limb that no `normalized` claim
covers, in output order (`rocq._output_formats`); the claims follow. Statements then compose: the
hypotheses of a statement say `fmt` of every input limb, and the theorem of the kernel that
computed that limb provides it. A mask output gets nothing.

A kernel with a constant-evaluation variant (`ce_variant:`) is `constexpr` and dispatches on
`__builtin_is_constant_evaluated()`: in constant evaluation it runs the variant's body with each
`prod` a plain product. A kernel whose only fused operations are `prod` is `constexpr` without a
variant, by the rule of the product (milestone2.md, "The two executions of a product"): each
`prod` is the plain product in constant evaluation and the opaque product otherwise, which as real
numbers are the same rounding, so that the real model is one definition for both; as values of T
they differ only in the sign of an exact zero product. `interp --ce` does the same, and the tests
check that the two executions give the same bits, or the same values where a zero product can be an
output (`test_interp.TwoExecutionsOfAProduct`). `build` lists the kernels constexpr by the rule. A
kernel with an `fma`, `fms` or `fnma` and no variant is not constexpr: the products of two limbs,
the Ball cores, and `mul_down_1` and `mul_up_1`, which trust the sign of two_prod's error term and
must not run through its variant. In constant evaluation `guard` returns its
operand and `times_inf` compares instead of multiplying (`times_inf_ce`): GCC and Clang refuse an
operation that produces a NaN there (NaN + 0, 0 · ∞), even one whose result is not selected. The
full kernels are then constexpr where their cores are (the additions and the scalings by a power of
two; not the products of two limbs, nor the other full Ball kernels). Constant evaluation still
stops at what the core cannot compute there: an overflow (GCC) or the NaN that TwoSum then makes
(Clang) is a compile error, never a wrong constant.

The scalar printer puts the fix-up of the full kernels, the full Ball kernels and the
constructors of balls behind a branch (`cpp.branch`; the rule and its measurements are in
milestone1.md, "Emission"). When every output is a `select` on one mask, and while the first
arms are all selects on one mask, those masks are what the branch tests; the operations that the
masks and the final arms need are printed first; `if (m1 & m2) [[likely]]` the outputs are the
arms; `else` the rest of the listing runs, in its order. The `else` part has two spellings under
`KAIRN_GEN_FIXUP_CALL` (`prelude.hpp`): inline, or a call of `fixup::K`, a function of its own
(cold, never inlined, constexpr where the kernel is) that takes the values the fix-up uses and
returns the outputs in a `fixup::result`. The call is what Clang on AArch64 gets, the inline form
what every other compiler gets; the tests may set the macro to build either. No other kernel
changes, and the packed printers keep the selects as blends.

## The counts of the object-code check

`gen/objcode.json` gives, for every kernel, each form of its C++ (`scalar`, with the fix-up inline;
`scalar_call`, with the fix-up a function of its own, `fixup::K`; `packed`) and each limb type, six
numbers, in the order of the file's `counts`:

- `fma`, `mul`: the operations printed as a fused multiply-add (`fma`, `fms`, `fnma`, `prod`) and as
  a plain multiplication (`times_inf`, a product with +infinity), one per node of the flattened
  listing. Every form prints each operation of the listing once.
- `fma_distinct`, `mul_distinct`: the same, with the operations of one function that compute the
  same thing from the same operands counted once, as a compiler that eliminates common
  subexpressions does. The same thing means the same operation up to the order of two factors or of
  the operands of a sum, an `fms` being an FMA of the negated addend, an `fnma` one of a negated
  factor and a `prod` one with the addend +0; constants are the same when their literals of the
  limb type are. In `scalar_call` the kernel and its fix-up are numbered apart.
- `consteval_mul`: the plain products of what the scalar code computes only in constant
  evaluation: the branch that a kernel with a constant-evaluation variant takes there (two_prod: 7,
  Dekker's product), and in a kernel constexpr by the rule of the product the first arm of each
  `prod` (one per prod), which a compiler that does not optimize may emit although no execution
  takes it.
- `muladd`: the declared contractable multiply-adds (none so far; the check has no rule for them).

For a fold, `gen/objcode.json` has `"fold_forms"` (`seq`, `lanes`, `packed`), `"fold_parts"` and
`"folds"`: per fold, form and limb type, a list of parts, each `[part, least, counts...]`, the
counts those of the part's kernel inlined (`step`, `combine`, `finish`, and `packed step`, the
step in packed code), and `least` the number of times the printed function holds that part: the
step once in `seq`, twice in `lanes` (the loop over the lanes and the loop over the remainder) with
the combination once, and in `packed` the packed step, the combination and the scalar step once
each; every form holds the finish once. What the check makes of them, a loop being unrolled or
not, is in [Testing](../docs/developer/testing.md#the-rule).

The forms differ for three kernels, `mul_2_1_full`, `mul_2_2_full` and `mul_pow2_2_full`, whose
fix-up computes the core's leading product again (`t = prod(x0, y0)`): one FMA node more than
`fma_distinct` in the inline form and in packed code, and as many in `scalar_call`, where the
recomputation is in the fix-up function; for `two_prod`, whose scalar forms have the branch of
constant evaluation; and for the kernels constexpr by the rule of the product, whose scalar forms
have a plain product for constant evaluation per `prod` and whose packed form has none. The limb
types differ for no kernel today, but they could: two constants of
different expressions can be one number in binary32 and two in binary64. What the check makes of
these numbers is in [Testing](../docs/developer/testing.md#object-code).

## The rules

`build`, `check` and `interp` refuse a kernel that breaks one, naming the kernel, the value and the
rule:

1. Static single assignment: every value assigned once, used after its definition, and used. An
   input that the computation does not need but the claims do (`to_nearest_2`'s `x1`) is
   declared with `unused:` and the reason; C++ marks it `[[maybe_unused]]`.
2. R1: there is no plain multiplication (`mul` is parsed only to be refused, with the route by
   which it reaches an addition). `times_inf`, a multiplication by infinity and exact, is one only
   in C++: its result may be an operand of a comparison or of `select` and nothing else, and an
   output only through `select`. Nor is a value added to itself (`rules.doubling`, on the listing
   with its calls inlined, through copies): GCC 13 writes `a + a` as `a * 2` and contracts it into
   the addition that follows under `-ffp-contract=fast`; a doubling is `prod(a, const up(2))`.
3. R2: no output is the result of a `muladd`, or an input (an input is returned through `copy`).
4. The non-finite cone: every limb value reaches output limb 0 through operations that keep a
   non-finite operand non-finite (not `select`, `succ`, `pred` or comparisons), unless it is
   computed from output limb 0. A kernel that cannot comply declares `cone_exempt:` with the
   reason and what stands in for the check (`two_prod_dekker`; in the second wave, every kernel
   that selects, steps to a neighbor, returns a mask, or computes a radius).
5. Every kernel names its theorem, source and license, or is marked `unverified`. A kernel of the
   extended domain also gives `ieee_status` (and `ieee_theorem` once that is proved); a kernel
   without a real-model statement has no `theorem`, and its `status` is its `ieee_status`.
6. R3: in a kernel marked `entry`, an input that enters from the program (a one-limb input not
   declared `stored`, or the limbs of an input declared `supplied`), and whatever `neg`, `abs`,
   `select` or `copy` alone make of it, is never an operand of `add` or `sub` nor the addend of an
   FMA-family operation before it has passed through `guard`. It may be a factor and an operand of
   a comparison. A value passed to another kernel is followed into that kernel's body, and so is
   what that kernel returns of it. Nor is such a value an output of the entry kernel as it is (it
   would be stored in an object, unguarded). `guard_pending: INPUT REASON` excuses one input of one
   kernel, and every kernel that passes a value into it, of the first part; `build` prints both
   lists, and the declaration is refused once the input is guarded.

There are also checks of names (none may shadow what the printers use), kinds, arity, the closed
vocabulary of the claims (that of architecture.md, "Claims of the second wave", "Claims of the
non-finite layer" and "Claims of Milestone 2" included, each kind in its domain), of the two models (a kernel with a
real-model statement names no `const inf` or `const nan`, has no `times_inf`, and calls no kernel
without one), of
`extends` (its core has the same inputs, value, minimum precision, and requirements with
`normalized` for `canonical`), of constant-evaluation variants (same signature, no FMA), and of
computed constants (above). A kernel has no real-model statement when it claims `extends`,
`represents` or `makes_ball`, or requires `ball`: the full kernels and the constructors.

## The tests

`python3 gen/kairn-gen test` needs no network and no Rocq:

- refusals: a deliberately wrong kernel for each rule, with its message;
- `check` catches a hand edit of each generated file, a missing file and a stray one;
- the interpreter against the host: bit identity with Python's `float` and `math.fma` for
  `binary64`, and with values rounded through `struct` for `binary32`, on random and edge
  operands (subnormals, signed zeros, overflow, NaN), for every kernel and every operation;
- the interpreter against rounding by enumeration on toy formats, and as a line-protocol runner;
- the C++: `gen/tests/runner.cpp` built with each compiler of `$KAIRN_GEN_CXX` (default: `c++` and
  `g++-16`, those that exist) at `-O0` and `-O2`, with `-ffp-contract=off`, `on` and `fast`, with
  and without `-frounding-math`, with each form of the fix-ups (`-DKAIRN_GEN_FIXUP_CALL=0` and
  `1`), and for x86-64 under Rosetta where available; every build must be bit-identical to the
  interpreter, on random cases from several strata, non-finite operands for the kernels of the
  extended domain, and the operands of `SPECIAL_CASES`, which tell faults planted by
  `tests/kernel_mutants.py` apart that the random cases miss (`results/milestone1/mutants/`);
  `static_assert`s check two_prod in constant evaluation, and every kernel without a
  fused operation (succ and pred included) or whose only fused operations are `prod` (the rule of
  the product) against the bits the interpreter computes in constant evaluation, in both forms;
- the two executions of a product (`test_interp.py`, `TwoExecutionsOfAProduct`): every kernel
  constexpr by the rule of the product gives in constant evaluation the bits it gives at run time,
  or, for those whose outputs can be an exact zero product (`mul_pow2_2`, the scalings of a ball,
  `mul_1_1`, `two_prod_dekker`), the same values, on the corpus of the interpreter's comparison with
  the host;
- the branch over a fix-up (`test_printers.py`, `FixupBranch`): the kernels it applies to and the
  masks it tests, each case of the rule on the toy kernel `ops_branch` and on variants of it (one
  mask, two, an arm that is no select, outputs on different masks, a kernel with a real-model
  statement), and that both forms print every operation of the listing once;
- the packed code: `gen/tests/packed_runner.cpp`, which evaluates consecutive requests one per
  lane, built on the same matrix (NEON on AArch64; AVX2 with `-mavx2 -mfma` on x86-64, and under
  Rosetta where it runs AVX2); special operands sit in one lane of a register at a time and at
  random, and every build must print exactly what the scalar runner built with the same flags
  prints;
- the headers for the library (`test_library.py`): every constant of `bounds.hpp` is the smallest
  number of its type not below the exact rational, checked with fractions and by stepping bit
  patterns; unverified kernels have no constants; every self-test case satisfies its requirements
  and stores what the interpreter computes; both headers compile with each compiler, the stored
  results match the compiled kernels, and a stored result one unit off is caught;
- the statements: every claim, in exact arithmetic, on every operand of formats with precisions
  1 to 6 (a sample where there are too many), with nothing overflowing (the Rocq statement, which
  also says that every output limb is a number of the format) and in the format itself whenever
  output limb 0 is finite (what the oracle checks). `test_statements.py` lists the corners where
  the two differ;
- the non-finite layer (`test_nonfinite.py`): a reading of milestone1.md of its own, on formats of
  the IEEE shape ($q_{\min} + q_{\max} = 3 - 2p$) with precisions 2 to 5: F1 to F5 of the full
  kernels (F2 against the core's claims), B1 to B4 and containment of the full Ball kernels, the
  claims of the constructors, and the extended reading of the kernels that need no fix-up, on
  every non-finite operand against a sample of the other, and on finite operands near overflow;
  what fails is printed and pinned in `KNOWN`;
- rule R3 (`test_rules.py`): each way of breaking it is refused, each allowed use accepted; the
  entry kernels are those the public headers call (read from `include/kairn/*.hpp`) and the full
  kernels and constructors; the pending guards are exactly `add_2_1`'s, and without it exactly
  the kernels that pass it their scalar are refused;
- the real model: `Model.v`, `Statements.v` and `Audit.v` are what they were before the non-finite
  layer, byte for byte (pinned digests), and the same as with the layer stripped;
- the runners read `inf`, `-inf` and `nan` and print non-finite outputs as exactly those words,
  in every scalar and packed build;
- the counts of the object-code check (`test_objcode.py`): each form counts every operation of the
  listing once, the counts of known kernels, the kernels where forms differ, the numbering of
  identical operations on a toy kernel (factors swapped, `fms` and `fnma` written as FMAs, constants
  equal in one format only), and the committed `gen/objcode.json`;
- the folds (`test_folds.py`; [Testing](../docs/developer/testing.md#the-generators-tier) says
  what it covers, these being tested by this suite only for now): the rules of a fold, the
  interpreter in exact arithmetic on toy formats in both orders and against an implementation of
  the lane order of its own, the compiled `F_seq`, `F_lanes` and `F_packed` bit for bit against the
  interpreter on lengths around every packed width and up to a few thousand, non-finite elements
  included, rule R3 on a supplied array with each compiler, and the printers.

`--full` raises the sizes to a few hundred thousand requests per kernel; `--jobs N` (or
`$KAIRN_GEN_JOBS`) caps the processes and compilers that run at once, on a shared machine.
`-k TEXT` runs only the tests whose name (`module.Class.test`) contains TEXT, and `--skip TEXT`
leaves them out; either fails if no test's name contains TEXT. ctest's full tier runs the suite
without C++ in two tests, with `--skip` for its four longest classes and those four with `-k`
(`tests/full/CMakeLists.txt`, [Testing](../docs/developer/testing.md#the-generators-tier)).

One difference is allowed, and reported each time it occurs: compilers fold the negation of an FMA
result into one negated FMA (`fnmadd` on AArch64 with GCC 16 and Apple clang 21 at `-O2`, and
`vfnmsub` on x86-64 with GCC 13 under `-ffp-contract=fast`), which returns +0 where the negation of
an exact zero is −0. A kernel that negates a fused result therefore has no single bit-exact result;
the tests accept exactly a different sign of a zero for such kernels (the first wave has none).

The Rocq output is checked by hand on a machine with Rocq 9.0.1 and Flocq 4.2.2: `make -C proofs`
builds `Model.v`, `Statements.v` and the proofs, and runs the audit.
