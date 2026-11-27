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
python3 gen/kairn-gen test      # the tests below; --full for the long sizes; --shard K/N for
                                # every N-th test from the K-th; --durations N for the slowest
python3 gen/kairn-gen interp    # the exact interpreter, as a runner of the line protocol; --max sel
                                # or nm for the machine form of max_nl (the round-up interval)
```

## What it writes

| File | Content |
|---|---|
| `proofs/gen/Model.v` | One Rocq `Definition` per kernel over the reals, each operation one rounding by Flocq's `round`, calls kept as calls |
| `proofs/gen/Statements.v` | `Definition K_spec : Prop` per kernel, from its claims; the proof `K_correct` must have this type |
| `proofs/gen/Audit.v` | For each kernel not marked unverified, checks `K_correct : K_spec` and prints its assumptions |
| `proofs/gen/IeeeModel.v` | One Rocq `Definition` per kernel that has an IEEE-model statement, over Flocq's binary floating-point numbers (signed zeros, infinities, NaN), each operation the one of `proofs/theories/IeeeOperations.v` |
| `proofs/gen/IeeeStatements.v` | `Definition K_ieee_spec : Prop` (and the finite-domain forms) per such kernel, from its claims, in the vocabulary of `proofs/theories/IeeeVocabulary.v` |
| `proofs/gen/IeeeAudit.v` | For each kernel whose IEEE-model status is not unverified, checks that its theorem has the generated statement as its type and prints its assumptions; then the same for the statement of the two executions of each kernel of `IeeeWith.v`, against its theorem `IeeeTwoExecutions.K_two_executions` |
| `proofs/gen/IeeeFoldModel.v` | Per fold, its step and combination over tuples of floats (the IEEE models of IeeeModel.v) and its two orders with the finish, `fold_seq` and `fold_lanes` of `proofs/theories/Folds.v`; per map, its step, its check and its two orders (`map` of the step, the mask, the second pass); per convolution, its check and `F_conv` |
| `proofs/gen/IeeeFoldStatements.v` | `F_seq_ieee_spec` and `F_lanes_ieee_spec` per fold (the flag, and the real model's result when it is true) and per map (element by element, and the mask), `F_ieee_spec` per convolution (coefficient by coefficient, and the mask), and `K_ieee_lead_spec` per step and combination of a fold and per step of a map |
| `proofs/gen/IeeeWith.v` | Per kernel whose C++ dispatches on constant evaluation without a variant (`ieee.with_kernels`: those `constexpr` by the rule of the product, and those without a product that compute a `guard` or `times_inf`, 66), `K_with`: its IEEE-model definition with the operations that constant evaluation runs differently as arguments, `p_` for `prod`, and `g_` for `guard` and `t_` for `times_inf` where the kernel computes them, and those three operations as constant evaluation computes them, `prod_ce`, `guard_ce` and `times_inf_ce` (`ieee.with_model`); and per such kernel `K_two_executions_spec`, the statement of its two executions: on all operands and for any NaN in either, `K_with` at the operations of constant evaluation and `IeeeModel.K` return limbs of the same extended real values (`xval`) and the same masks (`ieee.two_executions_statement`) |
| `proofs/gen/UpwardModel.v` | The round-up interval ([below](#the-round-up-interval)): one Rocq `Definition` per kernel of the upward family over Flocq's binary floating-point numbers, with `add_ru` and `mul_ru` (`Bplus`, `Bmult` with `mode_UP`) and `unord` of `proofs/theories/IeeeUpwardOperations.v` and the exact operations of `IeeeOperations.v`, in a section whose variables are their NaN functions and `max_nl`; a pair line is its two statements, lane 0 first |
| `proofs/gen/UpwardStatements.v` | `Definition K_spec : Prop` per kernel of the upward family, from its claims, in the vocabulary of `proofs/theories/IeeeUpwardVocabulary.v`, over every `max_nl` with the property `max_nl_ok` |
| `proofs/gen/UpwardAudit.v` | For each kernel of the upward family whose `ieee_status` is proved, checks its `ieee_theorem` against its statement and prints its assumptions |
| `proofs/gen/FoldModel.v` | Per fold, its step and combination over tuples of reals and its two orders, `fold_seq` and `fold_lanes` of `proofs/theories/Folds.v` |
| `proofs/gen/FoldStatements.v` | `Definition F_seq_spec : Prop` and `F_lanes_spec` per fold, from its claims; the proofs `F_seq_correct` and `F_lanes_correct` must have these types |
| `include/kairn/gen/prelude.hpp` | The force-inline macro, the FMA primitive per compiler, `abs_bits`, `next_up_bits`, `next_down_bits`, the form of the scalar fix-ups per compiler (`KAIRN_GEN_FIXUP_CALL`), the pragmas that every header puts around its declarations so that a program's globals of the same names raise no warning (`KAIRN_GEN_PUSH_WARNINGS`, `KAIRN_GEN_POP_WARNINGS`); refuses x86 without hardware FMA |
| `include/kairn/gen/scalar.hpp` | Every kernel for `double` and `float`, in `kairn::gen`; where the fix-up is a function of its own, that function, in `kairn::gen::fixup`; then every fold, `F_seq` and `F_lanes` |
| `include/kairn/gen/avx2.hpp` | Every kernel for `__m256d` and `__m256` (4 doubles, 8 floats), then every fold's `F_packed`; refuses a target without AVX2 and FMA |
| `include/kairn/gen/neon.hpp` | Every kernel for `float64x2_t` and `float32x4_t` (2 doubles, 4 floats), then every fold's `F_packed`; AArch64 only |
| `include/kairn/gen/bounds.hpp` | Per kernel and limb type, whether it is proved and, only then, the constants of its error claim rounded up (`unit`, `tiny`, and for the form relative to the result `unit_computed`, `tiny_computed`) and its form: `result` (R), `operands` (A) or `terms` (T, the terms of the value: `dot_step_2`); what the public headers gate on and export through `kairn::traits`; then, in `kairn::gen::bounds::loops`, per loop and limb type whether it is proved (its own status and minimum precision, and every kernel it runs), what the functions on arrays gate on |
| `include/kairn/gen/selftest.hpp` | Every kernel on fixed operands, with the results the interpreter computes: the stored bit patterns of `kairn::self_test()` |
| `include/kairn/gen/upward.hpp` | The round-up interval ([below](#the-round-up-interval)), in `kairn::gen::upward`: every kernel of the upward family for `double` and `float` in the form `KAIRN_UPWARD_FORM` chooses (one register: `__m128d` and `__m128` on x86-64, `float64x2_t` and `float32x2_t` on arm64; two numbers on any target, or when it is `KAIRN_UPWARD_FORM_NUMBERS`), the barriers and the pin of `include/kairn/upward.hpp` on its values; the array forms of the six kernels the functions on arrays run (AVX2, NEON, or a loop); the status of each kernel; the tables of `kairn::upward::self_test()`. Included by `include/kairn/upward.hpp` after its barriers; requires the mode upward set by `kairn::upward::Scope` and the options of `docs/concepts/upward.md` |
| `tests/emulated/gen/upward.hpp` | The kernels of the upward family in the two-number form for the emulated limb type (`kairn::emulated::Number` with its operations rounded upward: no mode, no scope), `max_nl` in the form the runner sets; for `gen/tests/upward_runner.cpp` built with `KAIRN_UPWARD_RUNNER_EMULATED`. A test file, not shipped |
| `gen/tests/upward_kernels.inc` | The table of kernels (input and output kinds, the call) and of the array forms of the runner of the upward family, `gen/tests/upward_runner.cpp` |
| `gen/claims.json` | What every kernel and every fold claims, with the constants per format as exact fractions; the kernels of the upward family after the others, each with `"rounding": "upward"` |
| `gen/constant_names.json` | The names of the constants `up(EXPR)` in the Rocq models, read first and only added to (below, "The operations") |
| `gen/objcode.json` | Per kernel, form of its C++ (scalar with the fix-up inline, scalar with the fix-up a function of its own, packed) and limb type, the fused multiply-adds and plain multiplications its code asks for; per fold, form and limb type, those of each part of its loop: the expectations of the object-code check (`tests/objcode/`) |
| `gen/tests/runner_kernels.inc` | The table of kernels and folds of the C++ runners `gen/tests/runner.cpp` and `packed_runner.cpp` |
| `tests/emulated/gen/kernels.hpp` | Every kernel and fold of `scalar.hpp` for the emulated limb type of the tests, `kairn::emulated::Number` (`tests/emulated/number.hpp`, a format chosen at run time, integer arithmetic), printed by `cpp.scalar` with that type; then the tables of its runner: the constants by index, their exact values in `binary64`, `binary32` and the formats of the statements of precision 8 to 11 (`emulated.FORMATS`), the kernels without a path of constant evaluation, the variants. A test file, not shipped (docs/developer/testing.md, "The emulated formats") |

`Model.v`, `Statements.v` and `Audit.v` are the real model only. The full kernels and the
constructors of the non-finite layer have no real-model statement and are not in them; a kernel of
the extended domain that has one (the comparisons, the conversions, `neg_2`, `abs_2`, `radd`,
`rmul`) is printed there with its requirement `canonical` read as `normalized`.

`build` also lists the kernels that are unverified (in the real model, and in the IEEE model), those
without a real-model statement, those that are not `constexpr`, those exempt from the non-finite
cone, the entry kernels, the guards of rule R3 that are pending, the kernels accepted only
through a pending guard, the folds and those of them that are unverified; and then the report of
rule R3 on the factors of fused operations (`rules.exposed_operands`, below): every entry kernel
and every loop with an exposed operand, the route to each, its operations today and with a guard
on each, and the functions of the public headers that reach it (`build.header_calls`); R3 refuses
every exposed operand, so the report lists none in `gen/kernels` (`0 objects`). `proofs/gen`
is mapped to the logical path `Kairn.Gen`, and `proofs/theories` to
`Kairn`.

## The code

| Module | Does |
|---|---|
| `kairn_gen/ir.py` | The IR: its operations, kernels, the description format, inlining of calls |
| `kairn_gen/expr.py` | The parser of the rational expressions of the claims (`3/(1-4*u)`); nothing is ever `eval`-ed |
| `kairn_gen/rules.py` | The checks every kernel passes before anything is printed |
| `kairn_gen/rocq.py` | The Rocq printer (trusted) |
| `kairn_gen/upward.py` | The Rocq printer of the upward family, `proofs/gen/Upward*.v` (trusted), and the mark of the feature's files |
| `kairn_gen/cpp.py` | The C++ printer (trusted); its functions take the limb type as a parameter: `double`, `float`, or a `cpp.Limb`, a type of a format chosen at run time |
| `kairn_gen/emulated.py` | `tests/emulated/gen/kernels.hpp`: `cpp.scalar` with the emulated limb type, and the tables of its runner |
| `kairn_gen/simd.py` | The AVX2 and NEON printers (trusted; tested lane by lane against the scalar code) |
| `kairn_gen/upward_cpp.py` | The C++ printers of the upward family (trusted): `include/kairn/gen/upward.hpp` (the one-register form from the pair lines, the two-number form, the array forms, the self-check's tables), `tests/emulated/gen/upward.hpp` and `gen/tests/upward_kernels.inc`; tested bit for bit against the interpreter in every form (`test_upward_cxx.py`) |
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
- The interval kernels (architecture.md, "Claims of the interval kernels"): `requires: interval
  xl xu` and `requires: not_nan a`;
  `ensures: makes_interval zl zu from=lo,hi`;
  `ensures: encloses_interval zl zu x+y x=xl,xu y=yl,yu tight=TIGHT [exact_lower=CONDITIONS]
  [exact_upper=CONDITIONS] [bounded_when=CONDITIONS] [bounded_exactly]`, TIGHT being `exact`,
  `rounded`, `rounded;steps=1;when=product_large` or `outward;rel=EXPR;abs=EXPR`, a condition of
  bounded_when `abs_le(SET,omega)` or `abs_le(SET,E)`;
  `ensures: set_bound l below x x=c,r [tight=rounded]`;
  `ensures: outward l below rel=EXPR abs=EXPR [exact_when=zero(x+y)]`, the constants in the
  language of `const up(EXPR)` with `up(EXPR)` inside;
  `ensures: encloses z d x+y` with no ball (points, the finite domain);
  `ensures: makes_ball cw rw from_interval=lo,hi [midpoint_when=half_in_format(lo);half_in_format(hi)]`;
  and `zero_factor` as the last word of a `bound` or `rounded` entry.
- Stage B1 of the intervals (architecture.md, "Claims of the interval kernels: two limbs and the
  enclosure interface"): `requires: not_nan x` also of a canonical input of two limbs;
  `ensures: interval_set zl zu union x=xl,xu y=yl,yu` (or `intersection`);
  `ensures: ball_of_interval m r from=xl,xu special=ieee1788 rel=u abs=eta [smallest_radius]`
  (`special` is `ieee1788` or `ball`);
  `ensures: interval_of_ball zl zu x x=c,r tight=rounded`;
  `ensures: splits al au bl bu from=xl,xu`;
  `zero_factor` as the last word of an `outward` entry (of the extended domain) and of an
  `encloses_interval` entry whose set is a product;
  and `ordinary_inline: REASON`, for a kernel of at most two limbs whose C++ is an ordinary inline
  function rather than forced inline (`interval_mul_2`: milestone2.md, "Inlining and compile time").
- The accumulator (architecture.md, "The accumulator"): `ensures: rounded b nearest
  value=a+abs(x[0])`, the rounding of a value of its own over the inputs and their limbs, of the
  finite domain; and `requires: count m` in the IEEE-model statements (`ieee: spec`) too. An
  IEEE-model statement whose kernel has claims about an output group other than the first puts
  each group's claims under the finiteness of that group's leading limb.
- Stage B2 of the intervals (architecture.md, "Claims of the enclosure interface: predicates and
  comparisons"): `ensures: certain m REL ARG... x=xl,xu [exact | exact_when=abs_le(EXPR,omega)]`, a
  mask true only if the relation holds (`lt`, `le`, `eq` of every choice of members, an argument a
  set or `0`; `member t x`, `subset`, `equal`, `interior`, `disjoint`, `empty`, `entire`), and
  `ensures: trit yes no REL A B x=xl,xu y=yl,yu [exact | exact_when=...]`, the three-valued form of
  `lt`, `le`, `eq` and `member`. A set `x=A,B` is an interval or a ball as the requirements say
  (`requires: interval A B`, `requires: ball A B`), and parse_kernel writes it under `intervals` or
  `balls` (`ir._set_kinds`). The C++ parameter of an input the computation does not need
  (`unused:`) may be the first one (`interval_empty_1` reads only the lower bound). The set
  operations of a ball: `ensures: ball_set cz rz union x=cx,rx y=cy,ry` (or `intersection`) and
  `ensures: ball_splits ca ra cb rb from=c,r`. The conversions of two limbs: `finite_when=abs_le(xl,-2);
  abs_le(xu,-2)` after a `ball_of_interval` entry (the radius finite under the conditions);
  `interval_of_ball zl zu x x=c,r tight=outward;rel=EXPR;abs=EXPR [exact_lower=zero(c-r)]
  [exact_upper=zero(c+r)] [bounded_when=abs_le(x,-2)]` with bounds of two limbs; and `rel=EXPR
  abs=EXPR [smallest_radius]` after a `makes_ball ... from_interval=lo,hi` entry
  (`ball_from_interval_1`).
- `guard_pending: a REASON`: an input of an entry kernel whose guard is not written yet (only
  `add_2_1`, whose guard changes the formal model of a proved kernel and lands with its proof).
- The folds' stage (architecture.md, "Claims of Milestone 2"): `requires: count m` ($m = 0$ or
  $m \ge 1$) and `requires: format half` ($\eta \le \tfrac12$); `error t T c=... k=2 t=2`, the
  form relative to the terms of `value`; `upper g value=EXPR if=ok`, the output at least EXPR when
  the mask `ok` is true, EXPR over the inputs, the one-limb outputs, `u`, `eta`, `unit(K)` and
  `tiny(K)`, with `^`; `holds le EXPR EXPR if=ok`; and `finite_or_nan r flag=f`, a fold's finish.
  A kernel whose every entry has its own value (`bound_sum_k`, `bound_dot_k`) has no `value:`.
- The folds of maxima (architecture.md, "Folds of maxima"): `maximum r m abs(x[0])`, the one-limb
  output the larger of two expressions (over the inputs and their limbs `NAME[I]`), an entry with
  values of its own (`norm_combine`, `norm_step_k` have no `value:`); and
  `finite_or_nan r flag=f if=ok steps=1`, the finish of such a fold: the value stepped up that many
  times, a NaN when the mask input `ok` is false. A kernel may have mask inputs (`input: mask ok`).
- The scaling of a BallVector by a power of two (architecture.md, "Ball vectors" and "Claims of
  Milestone 2"): `exact_flag=e` after the `exact_when=` of an `error` entry, the mask output `e` true
  exactly when those conditions hold; and of an `upper` entry with a value of its own, `unless=ex`, the
  bound when the mask input `ex` is false, and `exact_when=mask(ex);zero_or_abs_gt(rx*c,eta/(2*u))`, the
  output the value exactly when the conditions hold, `mask(NAME)` a condition that a mask input is true.

## The round-up interval

The kernels of the opt-in round-up interval ([design page](../docs/developer/design/upward.md)) are
the **upward family**: a description that says `rounding: upward`. Each is `ieee_only`, of the
extended domain, and an entry kernel; `load` keeps the family apart from the other kernels
(`ir.KernelSet.upward`), so that every printer of the others, and every test that walks them, sees
what it saw before the family existed: the family is in `gen/claims.json`, after the other
kernels, and in `proofs/gen/Upward*.v`, and its C++ is to be a header of its own,
`include/kairn/gen/upward.hpp` (the design page, "The pair form"). A state of the
interval is the pair $(u, n) = (b, -a)$ of the upper bound and the negated lower bound, the two
lanes of one register, the empty set $(\mathrm{NaN}, \mathrm{NaN})$:

```
kernel:        upward_add_1
rounding:      upward
input:         pair stored x = xu xn         a pair: lane 0, then lane 1; each a one-limb input
input:         pair stored y = yu yn
output:        pair z = zu zn
requires:      upward xu xn                  a canonical state, its stored pair in order
requires:      upward yu yn
ensures:       encloses_interval zu zn x+y x=xu,xn y=yu,yn tight=rounded bounded_when=abs_le(x+y,omega) bounded_exactly
min_precision: 1
status:        unverified
domain:        extended
ieee_only:     yes
ieee_status:   unverified
entry:         yes
...

zu = add_ru(xu, yu) | zn = add_ru(xn, yn)    a pair line: the two lanes of one instruction
```

- The IR stays scalar: a pair input or output is a one-limb input or output per lane, named by the
  lane (`k.pair_inputs`, `k.pair_outputs` record the pairs), and a pair line is two statements,
  lane 0 on the left (`Stmt.lane`, `Kernel.pair_lines`), which the Rocq printer, the interpreter
  and the claims read as those two statements; only the printers of the register form read the
  pairing.
- In the claims a pair is written in stored order: an output pair of `encloses_interval`,
  `interval_set` and `makes_interval` is named `"upper"` and `"nlower"`, and so is a set `x=xu,xn`
  whose operand is required `upward xu xn`; `numbers=t` lists one-limb inputs that each range over
  the members of `Interval(t)` ($\{t\}$ for a finite $t$, every real otherwise); `same_set A B
  from=C,D` claims that the output names the set that the input names, each a pair or the bounds
  of a default interval (`requires: interval xl xu`). The predicates claim `certain` and `trit`,
  `exact`, of stored pairs.
- The rules U1 to U7 and P1 to P5 (below, "The rules") are `rules.upward_rules`,
  `rules.upward_claims` and, for every kernel and fold outside the family, `rules.outside_family`
  and `rules.fold_outside_family`; R3 does not apply to the family (U4), and every other rule does.
- Every description of the family says in its first paragraph that it requires the mode upward
  set by `kairn::upward::Scope` and the options of `docs/concepts/upward.md` (`upward.MARK`).

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
writes:        none                              a map's written array (below)
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

A map (architecture.md, "Maps") writes one array, `writes: z = z0 z1`; its step takes the scalars
(`scalars: supplied a = a0 a1`, given once) and one element of each array, never the state, and
returns the element written; its state is `mask finite`, combined by
`combine: finite = and(finite, finite)`; `check: fold_finish_k` names the kernel that tests each
element written and gives its canonical NaN; it has no finish and claims `entries z` (the step's
claims, element by element) and `finite_or_nan z flag=finite`. `rules.map_rules` checks it;
`cpp.map_seq`, `cpp.map_lanes` and `simd.map_packed` print it, with the second pass that makes an
element that is not finite the canonical NaN; `rocq.map_model` and `rocq.map_statement` give it a
model, `map` of its step, and a statement, `Forall2` of the elements and the elements written;
`ieee.map_model` and `ieee.map_statement` its IEEE model, the loops with the mask and the second pass,
and its statements there, element by element and of the mask (architecture.md, "Maps and
convolutions in the IEEE model");
`claims.map_claims`, its entry of `"folds"`, with `"map": true`; the interpreter runs it with the
scalars after the length (`Machine.run_fold`), and the runners complete its requests
(`KAIRN_RUNNER_MAP` of `runner_kernels.inc`).

A fold of maxima (architecture.md, "Folds of maxima") has a state of two groups,
`state: m, mask ok` (a limb from +0 and a mask from true), which its step, combination and finish
take and return in that order: `step: (m, ok) = norm_step_2(m, ok, x)`, `combine: (m, ok) =
norm_combine(m, ok, m, ok)`, `finish: (r, flag) = norm_finish_2(m, ok)`; its value is `abs(x)`
and it claims `upper r max steps=S`. `rules.max_rules` checks it (the claims of its combination
and step, the step a call of the combination, the zero state and the laws of the combination by
evaluation, the finish); the printers are those of the folds, with a mask of the state a `bool` in
scalar code and in Rocq and a lane mask in packed code, and `rocq.max_statement` its statement.
An array limb that the step declares `unused` (`norm_step_2`'s `x1`) is a parameter of the C++
functions, `[[maybe_unused]]`, and is not loaded (`cpp.loaded_limbs`).

A convolution (architecture.md, "Convolutions") names the fold of its coefficients,
`coefficients: dot_2`, and has no `step:`; it reads two arrays of their own lengths (those of that
fold), writes one array (`writes: z = z0 z1`), has the mask, the `and`, the check (that fold's
finish) and the second pass of a map, the order `sequential` only, and claims `coefficients z` and
`finite_or_nan z flag=finite`. `rules.conv_rules` checks it; `cpp.conv_seq` prints it (no packed
form); `rocq.conv_model` and `rocq.conv_statement` give it a model, a `map` over the indices of the
coefficients of that fold's sequential order on `conv_terms xs ys j`, and a statement, `Forall2` of
the indices and the coefficients; `ieee.conv_model` and `ieee.conv_statement` their IEEE
counterparts, with the mask and the second pass; `claims.conv_claims`, its entry of `"folds"`, with
`"conv": true`;
the interpreter runs it (`Machine.run_fold`) and completes its requests, which have two lengths
(`interp.complete_conv`), and so does the compiled runner (`KAIRN_RUNNER_CONV` of
`runner_kernels.inc`).

A ball vector (architecture.md, "Ball vectors") is a map of the centers of BallVectors with the state
of a fold of maxima: `record: (m, ok) = norm_step_k(m, ok, z)` updates the state from each center
written, `combine:` is that fold's combination, `radius: rz = bv_add_radius_k(m, rx, ry)` gives the
one radius from the largest magnitude and the scalars, and `finish: (r, finite) = norm_finish_1(rz,
ok)` tests it; when the flag is false a second pass writes every center zero and the radius is
+infinity, the whole space. Each array is required `ball_vector ARRAY RADIUS`, and the fold claims
`encloses_entries z r SET NAME=ARRAY,RADIUS... flag=F [finite_when=... radii_when=... finite_from=P]`,
`radii_when` the conditions of V4 on the scalars alone, so that V4 holds of every length, the empty vector
included (it comes with `finite_when`), `finite_from` the precision from which V4 is claimed when it is
above the fold's minimum precision (`rules._finite_from`: from that precision every constant of the
fold must be finite in the smallest format, emax = prec + 1; `bv_add_1`, `bv_sub_1`, `bv_scale_1` say
`finite_from=2`), and the word `exact` (`"exact_when": []`) for a ball vector that
is exactly the set (`bv_neg_k`), or `exact_when=CONDITIONS` for one exact under conditions
(`bv_mul_pow2_k`): its state has a third group, `mask ex`; its step returns the center and a mask, `(z, e)
= STEP(...)`; a second `record:` line `ex = and(ex, e)` and a second `combine:` line `ex = and(ex, ex)`
and the mask into the state; the radius takes `ex` after the state's limb; the conditions are those of
the step's `exact_flag` and of the radius's exact `upper` entry (`rules._bv_exact`); a scalar may be
required `power_of_two`. A constructor (`bv_make_k`) reads the centers and the radius
given and claims `makes_ball_vector z rr from=c,r flag=F`; its finish claims
`finite_or_nan r flag=flag if=ok nonneg`, the value also not negative (`rules._bv_make_claims`).
`rules.bv_rules` checks
it; `cpp.bv_seq`, `cpp.bv_lanes` and `simd.bv_packed` print it; `rocq.bv_model` and
`rocq.bv_statement` give it a model (the centers and the radius) and a statement (containment entry
by entry); `ieee.bv_model` and `ieee.bv_statement` its IEEE model and V1 to V4 of milestone2.md;
`claims.bv_claims`, its entry of `"folds"`, with `"bv": true`; the interpreter runs it
(`Machine.run_fold`), and the runners complete its requests (`KAIRN_RUNNER_BV` of
`runner_kernels.inc`), the centers written, then the radius and the flag. The requests of a map and of a
ball vector may say `inplace=I` after the length (architecture.md, "The line protocol"): the runners
then pass array I as the array written, and the interpreter computes as without the field.

The product of two BallVectors (architecture.md, "Ball vectors": `bv_conv_k`) names a convolution for
its centers (`centers: conv_2`) and has no step: one `record:` line per array read, the step of a fold
of maxima on that array's entries (`(ma, oka) = norm_step_2(ma, oka, x)`), a count made from the lengths
(`count: m = min(n_x, n_y)`, a number of `T` rounded up), a kernel of that count run once (`bound: (g,
t, okg) = bound_dot_2(m)`), the radius on the maxima, the radii, the count and the bound, and a finish
on the radius, the convolution's mask and the bound's (`finish: (r, flag) = bv_conv_finish(rz, finite,
okg)`, whose kernel claims `finite_or_nan r flag=flag if_all=okc,okg`). Its arrays are required
`ball_vector`, and it claims `encloses_coefficients z r SET NAME=ARRAY,RADIUS... flag=F
finite_when=... radii_when=... count_when=le(EXPR,K)...`, the conditions of `finite_when` on pairs of
entries, on one array's entries or on the scalars, and `count_when` on the count `n` with `unit(K)` of a
kernel, `u` and `eta` (`bv_conv_2` has the smallest normal number `eta/(2*u)` there, so that the count
is a number of the format: architecture.md, "Ball vectors"). Its radius kernel may require `at_most
NAME K`. `rules.bv_conv_rules` checks it (with
`rules._bv_conv_bound`, that the bound is that of the products of the convolution's dot product);
`cpp.bv_conv_seq` prints it (no packed form, with the end function `bv_conv_end_function`);
`rocq.bv_conv_model` and `rocq.bv_conv_statement` give it a model and a statement (containment
coefficient by coefficient for members chosen independently); `ieee.bv_conv_model` and
`ieee.bv_conv_statement` its IEEE model and V1 to V4; `claims.bv_conv_claims`, its entry of `"folds"`,
with `"bv_conv": true`; the interpreter runs it (`Machine.run_fold`) and completes its requests, which
have two lengths and two radii (`interp.complete_conv`), and so does the compiled runner
(`KAIRN_RUNNER_BV_CONV` of `runner_kernels.inc`).

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
| `add_ru a b`, `mul_ru a b` | RU(a + b), RU(ab): rounded toward +∞ in the format with overflow (`interp.rnd_up`) | `add_ru a b`, `mul_ru a b` of `UpwardModel.v`: `Bplus`, `Bmult` with `mode_UP` | the upward family only: the design page, "The printers" | the same | the same |
| `unord a b` | a or b is a NaN | `unord a b`: `orb (is_nan a) (is_nan b)` | the same | the same | the same |
| `max_nl a b` | MAXPD's `a > b ? a : b` (`--max sel`, the default) or FMAXNM's on quiet NaNs (`--max nm`) | `max_nl a b`, a variable of the section, with the hypothesis `max_nl_ok` | the same | the same | the same |

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
type; Rocq as one definition per distinct constant,
`round radix2 (FLT_exp emin prec) Zceil (EXPR)` with u, η, `unit(K)` and `tiny(K)` spelled out.
Its name is stable, because hand-written proofs use it: `gen/constant_names.json` records, for each
EXPR as the descriptions write it without spaces, the name of its definition (`{"about": ...,
"names": {EXPR: NAME}}`, ordered by name). The printers take a recorded name first; a constant that
is new is named `up_K_i` after the first kernel K that uses it, i being its place among K's
distinct constants (the next free place if the record has that name for another constant), and
`build` adds it to the record, which is one of the files it writes and `check` compares. Nothing
removes an entry, and a test pins every recorded name (`test_printers.ConstantNames`). The
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
milestone1.md, "Emission"). When every output is a `select` of the kernel's own listing on one
mask, and while the first arms are all such selects on one mask, those masks are what the branch
tests (a select inside a callee chooses on the data, and is computed: the directed difference that
is the arm of `ball_lower_as_1`); the operations that the
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

The forms differ for four kernels, `mul_2_1_full`, `mul_2_2_full`, `mul_pow2_2_full` and
`mul_ext_2_2`, whose fix-up computes the core's leading product again (`t = prod(x0, y0)`, in
`mul_ext_2_2` the infinite product of an infinite operand): one FMA node more than `fma_distinct`
in the inline form and in packed code, and as many in `scalar_call`, where the recomputation is in
the fix-up function; for `two_prod`, whose scalar forms have the branch of
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
   without a real-model statement has no `theorem`, and its `status` is its `ieee_status`. A
   kernel of the finite domain names the theorems of its IEEE-model statements once each is
   proved: `ieee_bridge_theorem: FILE K_ieee_bridge` (with `ieee: bridge`), `ieee_spec_theorem:
   FILE K_ieee_correct` (with `ieee: spec`), `ieee_lead_theorem: FILE K_ieee_lead` (the step or
   the combination of a fold, or the step of a map); `ieee_lead_theorem` is also that of a kernel
   of the extended domain that has a leading-limb statement, the step of a fold (`neg_2`,
   `bv_center_2`, `bv_center_entry_2`), whose other IEEE-model theorem is its `ieee_theorem`. A fold or a map names
   `ieee_theorem: FILE`, the file of `F_seq_ieee_correct` and `F_lanes_ieee_correct` (and, for a
   fold of maxima in both orders, of `F_orders_ieee_correct` and `F_flag_ieee_correct`, the
   theorems of its two statements more), and a convolution or a product of two BallVectors, which
   have one statement each (`F_ieee_spec`), the file of `F_ieee_correct`. A convolution also names
   `terms_theorem: FILE`, the file of `conv_terms_eq_correct`, `conv_terms_count_correct` and
   `conv_terms_length_correct`, the theorems of the three statements of `conv_terms` in
   `proofs/gen/FoldStatements.v`, which every convolution shares: the convolutions that name one
   name the same file, and `proofs/gen/Audit.v` checks the three once. Each names only a statement
   that is printed,
   by its conventional name, in `proofs/theories/`; a statement whose theorem is not named is
   printed as unverified, and only those that are named are in `proofs/gen/IeeeAudit.v` (those of
   `conv_terms`, of the real model, in `proofs/gen/Audit.v`).
6. R3: in a kernel marked `entry`, an input that enters from the program (a one-limb input not
   declared `stored`, or the limbs of an input declared `supplied`), and whatever `neg`, `abs`,
   `select` or `copy` alone make of it, is never an operand of `add` or `sub` nor the addend of an
   FMA-family operation before it has passed through `guard`. It may be a factor and an operand of
   a comparison. A value passed to another kernel is followed into that kernel's body, and so is
   what that kernel returns of it. Nor is such a value an output of the entry kernel as it is (it
   would be stored in an object, unguarded). `guard_pending: INPUT REASON` excuses one input of one
   kernel, and every kernel that passes a value into it, of the first part; `build` prints both
   lists, and the declaration is refused once the input is guarded. Nor is such a value (for a
   loop: an element of a supplied array or a supplied scalar, through its step, its radius and the
   step of the fold of its coefficients) a factor of `fma`, `fms`, `fnma` or `muladd` whose addend
   is not the literal zero before `guard`: it is *exposed* there, and refused with the operand,
   the operation and the route (`rules.factor_rule` on `rules.exposed_operands`), because a
   compiler that sees the other factor to be 1 rewrites `fma(x, 1, s)` as `x + s` and fuses the
   program's product into it. A factor of `prod`, `fma(a, b, +0)`, is accepted: its fusion is the
   product's own rounding (docs/developer/architecture.md, "R3", the factors of a fused
   operation).
7. No value is the negation of the result of a fused operation (`fma`, `fms`, `fnma`, `prod`),
   callees inlined: `sub_down_1(x, d)` and `sub_up_1(x, d)` negate `d`. Nor is it the negation of a
   `select` one of whose arms is such a result (or a `select` or `copy` of one, through any number
   of them): compilers push a negation through a select into its arms. Compilers fold such a
   negation into the fused instruction, which is one fused instruction more where the result is
   also used as it is, and +0 where the negation of an exact zero is −0 ("The tests"). Rounding to
   nearest being symmetric, the negation goes on an operand: `prod(neg(a), b)` for `-prod(a, b)`,
   and `neg(add_up_1(d, neg(x)))`, minus the rounding up of `d - x`, for the rounding down of
   `x - d`, as `mul_dir_2_2`, `add_down_2_2` and `ball_from_interval_2` do. The message says so.

8. The round-up interval ([design page](../docs/developer/design/upward.md#the-rules), "The rules"
   and "The pair form"), each refused with the rule's name:
   - **U1.** A kernel of the upward family uses only `add_ru`, `mul_ru`, `max_nl`, `unord`, `neg`,
     `abs`, `copy`, `lt`, `le`, `eq`, `and`, `or`, `not`, `select`, the constants `0`, `const inf`
     and `const nan`, and calls of kernels of the family; it is `ieee_only` and of the extended
     domain, and has no `ce_variant`. No kernel outside the family uses the four operations, a pair,
     a pair line, the family's vocabulary of claims or a call of one of its kernels, and no fold runs
     one.
   - **U2**, the pair lines: **P1**, both statements apply the same operation, but `neg | copy` and
     `copy | neg`, and a pair line has no call; **P2**, each operand position is one register: a
     pair (an input or a pair line) in its order, swapped, a broadcast of one of its lanes, two
     constants, a broadcast of a scalar, or two scalars (a make); **P3**, a pair has two lanes, and
     its name is no other name of the kernel; **P4**, a scalar enters a pair line only by a
     broadcast or a make, never beside a lane of a pair; **P5**, a mask of a pair line is the mask
     of a pair line of comparisons or `unord` (or `and`, `or`, `not` of such masks), or a broadcast
     of a scalar mask, never two scalar masks.
   - **U3.** No value is the negation of a result of `add_ru` or `mul_ru`, directly or through
     `select`, `copy` or `max_nl`, the callees inlined: under the mode upward $-\mathrm{RU}(t)$ is
     $\mathrm{RD}(-t)$.
   - **U4.** No `guard` and no `guard_pending`; R3 does not apply (the printer puts a barrier on
     every input instead).
   - **U5.** The first operand of every `max_nl` is a result of `mul_ru` or a lane of a pair input,
     so that every NaN that reaches it is quiet.
   - **U6.** Every `add_ru` and `mul_ru` has the kernel's first pair input in its data flow.
   - **U7.** A pair output is the result of one pair line, lane 0 and lane 1 in order; a mask or a
     number output is the result of a scalar statement.

   And the family's claims (`rules.upward_claims`): every pair input required `upward U N` (a
   default interval given as two one-limb inputs, `interval L U`); no value; one claim, of
   `encloses_interval` (tight `rounded` or `exact`, I5 as `bounded_when=abs_le(SET,omega)
   bounded_exactly`), `interval_set`, `makes_interval`, `same_set`, `certain` or `trit` (exact),
   its result an output pair named in stored order; the Rocq printer of the family must print each
   (`rules.upward_printable`).

There are also checks of names (none may shadow what the printers use), kinds, arity, the closed
vocabulary of the claims (that of architecture.md, "Claims of the second wave", "Claims of the
non-finite layer", "Claims of Milestone 2" and "Claims of the interval kernels" included, each kind in its domain; the
constants of a claim, `rel` and `abs`, name with `up( )` only constants of kernels with a real-model statement, are
nonnegative in binary64 and binary32, and use `unit(K)` and `tiny(K)` as a constant `up(EXPR)` does), of the two models (a kernel with a
real-model statement names no `const inf` or `const nan`, has no `times_inf`, and calls no kernel
without one), of
`extends` (its core has the same inputs, value, minimum precision, and requirements with
`normalized` for `canonical`), of constant-evaluation variants (same signature, no FMA), and of
computed constants (above). A kernel has no real-model statement when it claims `extends`,
`represents`, `makes_ball` or `finite_or_nan` (and the interval kinds `makes_interval`, `encloses_interval`,
`set_bound`, `interval_set`, `ball_of_interval`, `interval_of_ball`, `splits`, `certain`, `trit`, `ball_set`,
`ball_splits`) and nothing else, or
says `ieee_only: yes`: the full kernels, the constructors, the interval kernels, the finishes of
the folds. A constant `up(EXPR)` that only such kernels use (the halving of `ball_from_interval_2`
and `interval_mid_rad_1`) has no definition in `Model.v`; `IeeeModel.v` defines it from its
expression, and its name is in the record like any other. One that a kernel with a real-model
statement uses too is `Model.v`'s, under one name: the doubling of `ball_from_interval_2` is
`up_bound_dot_1_2`, a constant of `bound_dot_1`.

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
  the host; and `proofs/gen/IeeeWith.v` (`test_ieee.py`, `WithProduct`): each listing is the
  generated model with its arguments written back as the operations of run time, line for line;
  the arguments are exactly the operations whose C++ dispatches on constant evaluation, and a
  kernel with a guard (or `times_inf`) has it as an argument; a callee outside the file that
  computes one is refused; the kernels of the file are those whose C++ dispatches on constant
  evaluation without a variant (66: the 30 of the rule of the product and 36 without a product),
  and every function of `scalar.hpp` that dispatches is one of theirs or `two_prod`'s; the
  statements of the two executions are one per kernel of the file, in its order, each checked by
  `IeeeAudit.v` (a kernel added gets both), and the shape of one is pinned;
- the kernels for the emulated limb type (`test_emulated.py`, five tests, 5 seconds on the Mac):
  the emulated listing with the type's name replaced by `double` is the double listing token for
  token (some 106 000 tokens), every literal the same constant in the same place (its value at
  `binary64`, and at float's format against the float listing), the test of constant evaluation in
  the same places; a select's arms swapped, a constant replaced by another, a value inlined from
  the wrong operand and a statement added after a branch are each seen as a difference; the
  formats of the runner, and a format in which a constant is not a number refused;
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
  kernels and constructors, and a kernel a header calls that is not an entry kernel is on an
  argued list (`R3OfTheKernels.NOT_ENTRY_BUT_CALLED`: the header function that calls it, and for
  every input group why no value of the program reaches it: a count the header converts, the
  state of an object, the output of a kernel called just before, a constant of the self-test); the
  pending guards are exactly `add_2_1`'s, and without it exactly the kernels that pass it their
  scalar are refused; the report on the factors of fused operations (`R3Factors`): the criterion
  on small kernels, the list of `gen/kernels` pinned (`EXPOSED`), the calls of the headers;
- the real model: `Model.v`, `Statements.v` and `Audit.v` are what they were before the non-finite
  layer, byte for byte (pinned digests), and the same as with the layer stripped;
- the runners read `inf`, `-inf` and `nan` and print non-finite outputs as exactly those words,
  in every scalar and packed build;
- the counts of the object-code check (`test_objcode.py`): each form counts every operation of the
  listing once, the counts of known kernels, the kernels where forms differ, the numbering of
  identical operations on a toy kernel (factors swapped, `fms` and `fnma` written as FMAs, constants
  equal in one format only), and the committed `gen/objcode.json`;
- the maps (`test_maps.py`): the rules of a map; the interpreter, each element the step and every
  order the same, the canonical NaN and a false flag for what is not finite; the compiled `F_seq`,
  `F_lanes` and `F_packed` bit for bit against the interpreter; each map in place; rule R3 on a
  supplied array with each compiler; the printers;
- the folds (`test_folds.py`; [Testing](../docs/developer/testing.md#the-generators-tier) says
  what it covers, these being tested by this suite only for now): the rules of a fold, the
  interpreter in exact arithmetic on toy formats in both orders and against an implementation of
  the lane order of its own, the compiled `F_seq`, `F_lanes` and `F_packed` bit for bit against the
  interpreter on lengths around every packed width and up to a few thousand, non-finite elements
  included, rule R3 on a supplied array with each compiler, and the printers; the folds of maxima
  with them, and on their own the checks of `rules.max_rules`, the empty list and non-finite
  elements in every order, and their claim in exact arithmetic on random lists of toy formats of
  precision 1 to 6;
- the maps and the convolutions in the IEEE model (`test_ieee_writers.py`): their statements of
  `IeeeFoldStatements.v` read against the interpreter on formats of the IEEE shape of a few bits,
  where overflows are frequent, and in `binary64` and `binary32`, with infinities, NaN and numbers
  near the top among the scalars and elements, in every order; the lead statements of the steps of
  the maps on operands of any value; and the same statements against every build of the runner;
- the ball vectors (`test_bv.py`): the rules of a ball vector; V1 to V4 of milestone2.md and the
  flag in exact arithmetic on the interpreter, on formats of the IEEE shape of a few bits and in
  `binary64` and `binary32`, the whole space among the operands, in every order; the one radius
  equal to the largest of the entrywise radii of the Ball kernel; the scalings by a power of two
  exactly the set (and the radius $c\,r_x$) wherever their conditions hold, and sixty halvings in a row
  exact; the compiled `F_seq`, `F_lanes`
  and `F_packed` bit for bit against the interpreter; the line protocol; the printers and the claims,
  and the entries that architecture.md writes out;
- the convolutions (`test_conv.py`): the rules of a convolution; the interpreter, each coefficient
  the fold of its coefficients on its terms, their number, the canonical NaN of the coefficients a
  non-finite term reaches; the claims in exact arithmetic on toy formats, each coefficient within
  the bound of `dot` for its own number of terms; the compiled `F_seq` bit for bit against the
  interpreter on every pair of lengths up to 5 and random ones; the line protocol with two lengths;
  `conv_terms` of the model against its definition; the printers.

- the round-up interval (`test_upward.py`): the family and its descriptions, each listing the
  design page's statement for statement and each carrying the mark; a refusal of each rule U1 to U7
  and P1 to P5 and of the family's claims; `add_ru` and `mul_ru` against the number of the format
  found by search, on every pair of values of small formats (overflow and the signs of zeros
  included), and both forms of `max_nl` against MAXPD's and FMAXNM's definitions and against
  `max_nl_ok`; `interp --max`; the claims' entries and the two the design page writes out; the
  statement of the sum the page writes out, word for word, and the binders of `max_nl`; every
  generated file of the other kernels the same with the family and without it, and their pinned
  digests (of `gen/claims.json` without the family's entries); and every kernel through the
  interpreter on every pair of canonical states (every state and every value, for a kernel with a
  number) of formats of the statements, in both forms of `max_nl`, judged by a reading of its
  claims in exact arithmetic (I1 to I5, the set operations, the constructor, the conversions, the
  predicates): three formats of precision 1 and 2 in the quick suite, four of precision 2 and 3
  with `--full`, two of precision 4 with `KAIRN_GEN_UPWARD_PRECISION=4` (a run for a machine with
  many processors); and the same lines judged by the oracle's command line, the gate of the design
  page, in pieces (a range of the first operand's cases each, a process of the oracle's `check` of
  its own) that run side by side: the quick formats in the quick suite (some 1 million lines, 15
  seconds on the Mac with four jobs) and those of precision 3 with `--full` (160 million).
  Precision 4 (5.2 billion lines) is a run of `tests/brute/upward.py`, which keeps each piece's
  summary, resumes, and merges them (results in `results/upward/`);
- the C++ of the round-up interval (`test_upward_cxx.py`): the runner of the family
  (`gen/tests/upward_runner.cpp`, which holds a `kairn::upward::Scope` around each evaluation)
  built with each compiler at `-O0` and `-O2`, under each contraction setting, with
  `-frounding-math`, in the form the target chooses and in the two-number form forced, on x86-64
  with and without `-mavx2` (the AVX2 array form, or the loop), and with Clang once at `-O2`
  without `-frounding-math` (the barriers alone); every request one by one and, through the array
  forms of the six kernels that have one, in chunks of every length of a remainder, in place and
  not: the interpreter's lines byte for byte with the build's form of `max_nl` (`--max nm` for
  NEON, `sel` otherwise), on random cases of every stratum and on every combination of the special
  operands; the runner built with `KAIRN_UPWARD_RUNNER_EMULATED` (`tests/emulated/gen/upward.hpp`)
  on every canonical state of the quick formats, in both forms of `max_nl`, the interpreter's
  bytes; the loads and stores of pairs and an array form at `-O2` and `-O3`, where GCC applies the
  rules of aliasing, compiled with `-Wstrict-aliasing` as an error and run; and the
  printers: the pin on the first input of exactly the kernels that round, a barrier on every
  register and number given and returned, one instruction per pair line in the register form, the
  emulated listing the two-number listing of `double` with the type's operations. With one
  compiler and four jobs it takes some 26 seconds on the Mac.

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
the tests accept exactly a different sign of a zero for such kernels: the test kernels `ops_muladd`
and `ops_call`, which negate a `muladd` (the four results of the note the tests print), and no
kernel of `gen/kernels`. The same folding also costs one more fused instruction where the fused
result is used elsewhere as well (the compiler keeps the FMA and adds a negated one), which the
object-code check refuses; the rules therefore refuse the negation of an `fma`, `fms`, `fnma` or
`prod` result, directly or through a `select` ("The rules"), and
`test_cxx.EveryOperation.test_negated_fused_results_are_known` pins that no kernel of
`gen/kernels` negates a fused result of any kind, directly or through a select. The select is in
the rule because of what compilers did with the first listing of the directed sums of two limbs,
which negated `dd = select(zd, 0, d)` in `sub_down_1(z1, dd)`: Apple clang 21 (`fnmadd`) and GCC 13
on x86-64 (`vfnmsub`) pushed that negation through the select into the FMA of the radius `d` and
computed `-d` with one instruction, where GCC 16 on AArch64 and Clang 18 on x86-64 computed `d` and
flipped its sign. The object code was right only because `d` had no other use (the count stayed
that of the IR) and because `d` is at least the constant $H > 0$, never zero (the value was the
same). `add_down_2_2` now computes the rounding down of `z1 - dd` as minus the rounding up of
`dd - z1`, and negates no radius.

The Rocq output is checked by hand on a machine with Rocq 9.0.1 and Flocq 4.2.2: `make -C proofs`
builds `Model.v`, `Statements.v` and the proofs, and runs the audit. `UpwardModel.v` and
`UpwardStatements.v` import `proofs/theories/IeeeUpwardOperations.v` and `IeeeUpwardVocabulary.v`,
whose names they use as the design page writes them ("Statements").
