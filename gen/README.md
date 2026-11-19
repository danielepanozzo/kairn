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
| `include/kairn/gen/prelude.hpp` | The force-inline macro and the FMA primitive per compiler; refuses x86 without hardware FMA |
| `include/kairn/gen/scalar.hpp` | Every kernel for `double` and `float`, in `kairn::gen` |
| `gen/claims.json` | What every kernel claims, with the constants per format as exact fractions |
| `gen/tests/runner_kernels.inc` | The table of kernels of the minimal C++ runner `gen/tests/runner.cpp` |

`build` also lists the kernels that are unverified, those that are not `constexpr`, and those
exempt from the non-finite cone. `proofs/gen` is mapped to the logical path `Kairn.Gen`, and
`proofs/theories` to `Kairn`.

## The code

| Module | Does |
|---|---|
| `kairn_gen/ir.py` | The IR: its operations, kernels, the description format, inlining of calls |
| `kairn_gen/expr.py` | The parser of the rational expressions of the claims (`3/(1-4*u)`); nothing is ever `eval`-ed |
| `kairn_gen/rules.py` | The checks every kernel passes before anything is printed |
| `kairn_gen/rocq.py` | The Rocq printer (trusted) |
| `kairn_gen/cpp.py` | The C++ printer (trusted) |
| `kairn_gen/claims.py` | `gen/claims.json` |
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

## The operations

| IR | Interpreter | Rocq (`rnd` rounds to nearest) | C++ |
|---|---|---|---|
| `add a b`, `sub a b` | RN(a ± b) | `rnd (a + b)`, `rnd (a - b)` | `a + b`, `a - b` |
| `neg a`, `abs a` | exact | `- a`, `Rabs a` | `-a`, `abs_bits(a)` |
| `fma a b c` | RN(ab + c) | `rnd (a * b + c)` | `fma_rn(a, b, c)` |
| `fms a b c` | RN(ab − c) | `rnd (a * b + - c)` | `fma_rn(a, b, -c)` |
| `fnma a b c` | RN(−ab + c) | `rnd (- (a * b) + c)` | `fma_rn(-a, b, c)` |
| `prod a b` | RN(ab + 0) | `rnd (a * b + 0)` | `fma_rn(a, b, 0.0)` |
| `muladd a b c` | RN(ab + c) or RN(RN(ab) + c), by `--muladd` | `if fuse_V then … else …` | `a * b + c` |
| `lt`, `le`, `eq` | IEEE comparisons | `Rlt_bool`, `Rle_bool`, `Req_bool` | `<`, `<=`, `==` |
| `and`, `or`, `not` | on masks | `andb`, `orb`, `negb` | `&`, `\|`, `!` |
| `select m a b` | a if m else b | `if m then a else b` | `m ? a : b` |
| `succ a`, `pred a` | IEEE nextUp, nextDown | Flocq's `succ`, `pred` | `next_up(a)`, `next_down(a)` |
| `const NAME` | `ir.CONSTANTS` | `rocq.CONSTANTS` | a hexadecimal literal |
| `K(args)` | evaluated as a call | `let '(…) := K args in` | inlined |

A kernel with a constant-evaluation variant (`ce_variant:`) is `constexpr` and dispatches on
`__builtin_is_constant_evaluated()`: in constant evaluation it runs the variant's body with each
`prod` a plain product. `interp --ce` does the same.

## The rules

`build`, `check` and `interp` refuse a kernel that breaks one, naming the kernel, the value and the
rule:

1. Static single assignment: every value assigned once, used after its definition, and used.
2. R1: there is no plain multiplication (`mul` is parsed only to be refused, with the route by
   which it reaches an addition).
3. R2: no output is the result of a `muladd`, or an input.
4. The non-finite cone: every limb value reaches output limb 0 through operations that keep a
   non-finite operand non-finite (not `select`, `succ`, `pred` or comparisons), unless it is
   computed from output limb 0. A kernel that cannot comply declares `cone_exempt:` with the
   reason and what stands in for the check (`two_prod_dekker`).
5. Every kernel names its theorem, source and license, or is marked `unverified`.

There are also checks of names (none may shadow what the printers use), kinds, arity, the closed
vocabulary of the claims, and of constant-evaluation variants (same signature, no FMA).

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
  and without `-frounding-math`, and for x86-64 under Rosetta where available; every build must be
  bit-identical to the interpreter; `static_assert`s check two_prod in constant evaluation.

`--full` raises the sizes to a few hundred thousand requests per kernel; `--jobs N` (or
`$KAIRN_GEN_JOBS`) caps the processes and compilers that run at once, on a shared machine.

One difference is allowed, and reported each time it occurs: compilers fold the negation of an FMA
result into one negated FMA (`fnmadd` on AArch64 with GCC 16 and Apple clang 21 at `-O2`, and
`vfnmsub` on x86-64 with GCC 13 under `-ffp-contract=fast`), which returns +0 where the negation of
an exact zero is −0. A kernel that negates a fused result therefore has no single bit-exact result;
the tests accept exactly a different sign of a zero for such kernels (the first wave has none).

The Rocq output is checked by hand on a machine with Rocq 9.0.1 and Flocq 4.2.2: compile `Model.v`
and `Statements.v` with `-Q proofs/gen Kairn.Gen`, and `Audit.v` against stub theorems
(`Theorem K_correct : K_spec. Admitted.`) that are not committed.
