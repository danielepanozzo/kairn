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
| `include/kairn/gen/prelude.hpp` | The force-inline macro, the FMA primitive per compiler, `abs_bits`, `next_up`, `next_down`; refuses x86 without hardware FMA |
| `include/kairn/gen/scalar.hpp` | Every kernel for `double` and `float`, in `kairn::gen` |
| `include/kairn/gen/avx2.hpp` | Every kernel for `__m256d` and `__m256` (4 doubles, 8 floats); refuses a target without AVX2 and FMA |
| `include/kairn/gen/neon.hpp` | Every kernel for `float64x2_t` and `float32x4_t` (2 doubles, 4 floats); AArch64 only |
| `include/kairn/gen/bounds.hpp` | Per kernel and limb type, whether it is proved and, only then, the constants of its error claim rounded up (`unit`, `tiny`, `unit_computed`, `tiny_computed`) and its form; what the public headers gate on and export through `kairn::traits` |
| `include/kairn/gen/selftest.hpp` | Every kernel on fixed operands, with the results the interpreter computes: the stored bit patterns of `kairn::self_test()` |
| `gen/claims.json` | What every kernel claims, with the constants per format as exact fractions |
| `gen/tests/runner_kernels.inc` | The table of kernels of the C++ runners `gen/tests/runner.cpp` and `packed_runner.cpp` |

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
| `kairn_gen/simd.py` | The AVX2 and NEON printers (trusted; tested lane by lane against the scalar code) |
| `kairn_gen/consts.py` | The exact value of every constant in any format, `unit_computed(K)` and `tiny_computed(K)` included |
| `kairn_gen/claims.py` | `gen/claims.json` |
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

## The operations

| IR | Interpreter | Rocq (`rnd` rounds to nearest) | C++ | AVX2 (`pd`; `ps` for float) | NEON (`f64`; `f32`) |
|---|---|---|---|---|---|
| `add a b`, `sub a b` | RN(a ± b) | `rnd (a + b)`, `rnd (a - b)` | `a + b`, `a - b` | `_mm256_add_pd`, `_sub_` | `vaddq_f64`, `vsubq_` |
| `neg a`, `abs a` | exact | `- a`, `Rabs a` | `-a`, `abs_bits(a)` | xor, andnot with `-0.0` | `vnegq`, `vabsq` |
| `fma a b c` | RN(ab + c) | `rnd (a * b + c)` | `fma_rn(a, b, c)` | `_mm256_fmadd_pd` | `vfmaq(c, a, b)` |
| `fms a b c` | RN(ab − c) | `rnd (a * b + - c)` | `fma_rn(a, b, -c)` | `_mm256_fmsub_pd` | `vfmaq(vnegq(c), a, b)` |
| `fnma a b c` | RN(−ab + c) | `rnd (- (a * b) + c)` | `fma_rn(-a, b, c)` | `_mm256_fnmadd_pd` | `vfmsq(c, a, b)` |
| `prod a b` | RN(ab + 0) | `rnd (a * b + 0)` | `fma_rn(a, b, 0.0)` | `fmadd` with `setzero` | `vfmaq` with `+0.0` |
| `muladd a b c` | RN(ab + c) or RN(RN(ab) + c), by `--muladd` | `if fuse_V then … else …` | `a * b + c` | `add(mul(a, b), c)` | `vaddq(vmulq(a, b), c)` |
| `lt`, `le`, `eq` | IEEE comparisons | `Rlt_bool`, `Rle_bool`, `Req_bool` | `<`, `<=`, `==` | `_mm256_cmp_pd`, `_CMP_*_OQ` | `vcltq`, `vcleq`, `vceqq` |
| `and`, `or`, `not` | on masks | `andb`, `orb`, `negb` | `&`, `\|`, `!` | `and`, `or`, `not_mask` | `vandq_u64`, `vorrq_u64`, `not_mask` |
| `select m a b` | a if m else b | `if m then a else b` | `m ? a : b` | `_mm256_blendv_pd(b, a, m)` | `vbslq(m, a, b)` |
| `succ a`, `pred a` | IEEE nextUp, nextDown | Flocq's `succ`, `pred` | `next_up(a)`, `next_down(a)` | `next_up`, `next_down` on integer lanes | the same |
| `copy a` | a | `a` | `a` | `a` | `a` |
| `0` | +0 | `0` | `0.0` | `_mm256_setzero_pd()` | `vdupq_n_f64(0.0)` |
| `const NAME` | `consts.value` | `rocq.CONSTANTS`, or `unit_computed_K` | a hexadecimal literal | `_mm256_set1_pd(literal)` | `vdupq_n_f64(literal)` |
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

The Rocq model is one section over `emin prec choice`. Closing it abstracts each definition over
the section variables it uses and only those (`lt_2_2` takes four reals, `to_down_2` takes
`emin prec` first), and the statements apply each kernel accordingly (`rocq.section_args`).

A kernel with a constant-evaluation variant (`ce_variant:`) is `constexpr` and dispatches on
`__builtin_is_constant_evaluated()`: in constant evaluation it runs the variant's body with each
`prod` a plain product. `interp --ce` does the same.

## The rules

`build`, `check` and `interp` refuse a kernel that breaks one, naming the kernel, the value and the
rule:

1. Static single assignment: every value assigned once, used after its definition, and used. An
   input that the computation does not need but the claims do (`to_nearest_2`'s `x1`) is
   declared with `unused:` and the reason; C++ marks it `[[maybe_unused]]`.
2. R1: there is no plain multiplication (`mul` is parsed only to be refused, with the route by
   which it reaches an addition).
3. R2: no output is the result of a `muladd`, or an input (an input is returned through `copy`).
4. The non-finite cone: every limb value reaches output limb 0 through operations that keep a
   non-finite operand non-finite (not `select`, `succ`, `pred` or comparisons), unless it is
   computed from output limb 0. A kernel that cannot comply declares `cone_exempt:` with the
   reason and what stands in for the check (`two_prod_dekker`; in the second wave, every kernel
   that selects, steps to a neighbor, returns a mask, or computes a radius).
5. Every kernel names its theorem, source and license, or is marked `unverified`.

There are also checks of names (none may shadow what the printers use), kinds, arity, the closed
vocabulary of the claims (that of architecture.md, "Claims of the second wave" included), of
constant-evaluation variants (same signature, no FMA), and of computed constants (above).

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
  bit-identical to the interpreter; `static_assert`s check two_prod in constant evaluation, and
  every kernel without a fused operation (succ and pred included) against its run-time bits;
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
  1 to 6 (a sample where there are too many), with nothing overflowing (the Rocq statement) and in
  the format itself whenever output limb 0 is finite (what the oracle checks). `test_statements.py`
  lists the corners where the two differ.

`--full` raises the sizes to a few hundred thousand requests per kernel; `--jobs N` (or
`$KAIRN_GEN_JOBS`) caps the processes and compilers that run at once, on a shared machine.

One difference is allowed, and reported each time it occurs: compilers fold the negation of an FMA
result into one negated FMA (`fnmadd` on AArch64 with GCC 16 and Apple clang 21 at `-O2`, and
`vfnmsub` on x86-64 with GCC 13 under `-ffp-contract=fast`), which returns +0 where the negation of
an exact zero is −0. A kernel that negates a fused result therefore has no single bit-exact result;
the tests accept exactly a different sign of a zero for such kernels (the first wave has none).

The Rocq output is checked by hand on a machine with Rocq 9.0.1 and Flocq 4.2.2: `make -C proofs`
builds `Model.v`, `Statements.v` and the proofs, and runs the audit.
