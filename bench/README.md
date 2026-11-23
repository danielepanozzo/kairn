# Benchmarks

The harness behind [Benchmarks, Milestone 1](../docs/developer/results/bench-milestone1.md). It
times what a client gets, the generated kernels of `include/kairn/gen/` and the public operators of
`kairn::Expansion` and `kairn::Ball`, next to a few measurement props that exist only here, and
answers five questions: what the opaque product costs, what the fix-up for non-finite results
costs, what a `Ball` operation costs, how Kairn compares with textbook double-word arithmetic, and
how `float` limbs compare with `double` limbs. No external benchmark library; MPFR is timed for
scale when it is already installed. The harness of Milestone 2, a program of its own, is described
[below](#milestone-2).

Nothing here is part of the library. The props (`props.hpp`, `props_packed.hpp`) are not
verified and must not be used elsewhere. Each is the baseline of one comparison: a core with the
opaque product written as a plain multiplication; the full kernels written with every select
computed (the form the generator emitted for scalar code before the branch, and still emits for
packed code); the JMP17 algorithms with a plain multiplication and no guard or fix-up.

## Build

`KAIRN_BUILD_BENCHMARKS` (default `OFF`) adds this directory. With GCC, Clang or Apple clang it
builds `kairn-bench-O2` and `kairn-bench-O3`; with MSVC, `kairn-bench-O2` (`/O2`). Every file
links `kairn::fma`, so the scalar code gets hardware FMA exactly as a client's would (`-mfma` on
x86-64, `/arch:AVX2` with MSVC, nothing on AArch64); `packed.cpp` is also compiled with
`-mavx2 -mfma` on x86-64. Everything is compiled without contraction (`-ffp-contract=off`;
MSVC's `/fp:precise` does not contract): the props with a plain multiplication need it, and the
generated kernels contain no plain multiplication that it could change other than the
multiplication by $+\infty$ of the fix-up, which has no neighbor to fuse with. Never
`-ffast-math` or `/fp:fast`. The defaults a client gets apply: `KAIRN_CHECKS` is 0 under
`NDEBUG`, and `KAIRN_GEN_FIXUP_CALL` is what `kairn/gen/prelude.hpp` chooses (the fix-up in a
function of its own with Clang on AArch64, inline elsewhere); the JSON records it.

```sh
cmake -S . -B build-bench -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DKAIRN_BUILD_TESTS=OFF -DKAIRN_BUILD_BENCHMARKS=ON [-DCMAKE_CXX_COMPILER=g++]
cmake --build build-bench
```

On macOS add `-DCMAKE_PREFIX_PATH=/opt/homebrew` for Homebrew's MPFR. On Windows run the same
two commands in a Visual Studio x64 developer prompt, with `-DCMAKE_CXX_COMPILER=cl`.

## Run

```sh
build-bench/bench/kairn-bench-O2 --check-only        # the checks alone
taskset -c 34 build-bench/bench/kairn-bench-O2 --cpu 34 --reps 31 \
    --machine "Linux x86-64, AMD EPYC 7452 (Zen 2); one logical CPU, its SMT sibling idle" \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone1/bench/linux-gcc-O2-r1.json
```

| Option | Meaning |
|---|---|
| `--cpu N` | pin the thread to logical CPU `N` (Linux, Windows); on macOS the thread asks for the user-interactive class, which runs on performance cores |
| `--reps R` | samples per function (default 21; the stored runs use 31) |
| `--sample-ms MS` | length of one sample (default 4 ms) |
| `--filter TEXT` | time only the functions whose name contains `TEXT` |
| `--machine`, `--commit`, `--date` | recorded in the JSON; describe the machine generically, never by host name |
| `--json FILE` | where to write the measurements (standard output otherwise) |
| `--list`, `--check-only` | list the functions; run the checks and stop |

A run takes about 50 seconds. On a shared machine, pin to a core whose SMT sibling is idle and
check with `mpstat` (Linux) or `typeperf` (Windows) that it stays so; on macOS, which has no
affinity, run when the load is low and repeat a run whose median spread (median over minimum of a
function's samples, at the median function) exceeds 2%. Store each repeated run of a
configuration as `CONFIG-rN.json`.

What one run does:

1. **Inputs**, at run time from a fixed seed, the same with every compiler: 256 normalized
   2-limb numbers per operand, leading limbs $\pm[1, 2) \cdot 2^k$ with $k \in [-8, 8]$, tails
   about $u$ times them; radii about $2^{-80}$ of the centers ($2^{-40}$ for `float`); factors in
   $[2^{-1/4}, 2^{1/4})$ for products; Horner coefficients with $k \in [-2, 2]$ and argument
   about $0.8$. Nothing overflows or underflows in a timed loop, and no operand of a timed
   operation is subnormal. The same numbers twice: as separate arrays of limbs (for the generated
   kernels, scalar and packed), and as arrays of `Expansion<T, 2>`, `Ball<T, 2>`, `Ball<T, 1>`
   and `T` made by the public constructors (for the public operators). The arrays of one function
   fit in any L1.
2. **Checks**, before anything is timed: every function against the generated core on these
   inputs, bit for bit (the full kernels and the public operators return the core's result when
   nothing overflows; MPFR within $2^{-100}$ for one operation and $2^{-90}$ for a chain); and the
   forms of the full kernels against each other (the generated scalar kernel, the listing with
   selects, the generated packed kernel) on 8192 random and special operands per kernel
   (infinities, NaN, sums and products that overflow), bit for bit apart from NaN payloads and the
   sign of zeros, with the result canonical and, for the 2-limb kernels, F4 and F5 of
   `docs/developer/design/milestone1.md` checked. A failed check stops the run.
3. **Timing**: each function is calibrated to samples of about 4 ms; then rounds over all
   functions, one sample each per round, so that a disturbance spreads over all of them. The
   JSON has the minimum, median and maximum time per operation. Ratios on the results page are
   of minimum times within one run.

## The functions

A function's name is `BACKEND/KIND/KERNEL/VARIANT`:

- `BACKEND`: `scalar` (loops of the `scalar.hpp` kernels on separate arrays of limbs, which the
  compiler may vectorize), `packed` (`avx2.hpp` or `neon.hpp`, one number per lane), `api` and
  `apif` (the public types with `double` and `float` limbs, `api.cpp`), `mpfr`.
- `KIND`: `tp`, independent operations over the arrays, time per operation; `sum`, `prod`,
  `horner`, a dependent chain (a running sum, a running product of factors near 1, a Horner
  evaluation), time per step. A packed chain runs one chain per lane.
- `KERNEL`: the generated kernel's name (`add_2_1` is `x + a`, `ball_scale_2` is `X * a`).
- `VARIANT`: `kairn`, the generated core (for `api`, called on the limbs of the public types);
  `full`, the generated full kernel; `op`, the public operator; `finite`, `kairn::finite::`;
  `plain`, the core with every opaque product written `a * b`; `full_sel`, the full kernel as
  listed, every select computed; `textbook`, double-word arithmetic written from the listings of
  Joldes, Muller and Popescu (2017); `double` and `limb`, one operation of the limb type; `mpfr`,
  MPFR at 106 bits.

Each is a non-inlined function with C linkage named `kb_KIND_KERNEL__VARIANT` (`kb_ptp_...` for
packed code, `kb_a64_...` and `kb_a32_...` for the public types), so that its loop can be found in
a disassembly.

## Machine code

```sh
objdump -d --no-show-raw-insn build-bench/bench/kairn-bench-O2 \
    | python3 bench/asm_summary.py --json results/milestone1/bench/asm-linux-gcc-O2.json
dumpbin /disasm:nobytes build-bench\bench\CMakeFiles\kairn-bench-O2.dir\scalar.cpp.obj ^
    build-bench\bench\CMakeFiles\kairn-bench-O2.dir\packed.cpp.obj ^
    build-bench\bench\CMakeFiles\kairn-bench-O2.dir\api.cpp.obj ^
    | python bench\asm_summary.py --json results\milestone1\bench\asm-windows-msvc-O2.json
```

`asm_summary.py` finds the loops of every timed function and counts, per loop, fused
multiply-adds, multiplications, additions, comparisons, selects, mask logic, branches and calls,
and the width of the registers the arithmetic uses (scalar, 128 or 256 bits).

## Tables

```sh
python3 bench/report.py results/milestone1/bench
```

prints the tables of the results page from the stored JSON: a cell is the lowest and highest
value of a ratio over the repeated runs of a configuration.

## Milestone 2

The harness behind [Benchmarks, Milestone 2](../docs/developer/results/bench-milestone2.md): what
Milestone 2 has made public, next to the classical way of rounding down and up (changing the
rounding mode), plain floors of `T`, and `Ball`. Its own program, `kairn-bench-m2-LEVEL` (and
`kairn-bench-m2-outlined-LEVEL`, `kairn-bench-m2-external-LEVEL` in the other settings of
`KAIRN_ENCLOSURE_CODE`), built with the same option and flags as `kairn-bench`; the program of
Milestone 1 is unchanged.

| File | What it holds |
|---|---|
| `m2_data.hpp` | what the files share: `Raw<T>`, every operand as plain arrays of `T` laid out as the public types lay out their limbs, and the outputs; `Entry`, one timed function; the regions a function writes |
| `m2.cpp` | the functions that use Kairn, for `double` (backend `m2`) and `float` (`m2f`): the building blocks, `Interval<T, 1>` and `<T, 2>`, `Ball<T, 1>` and `<T, 2>`, Horner, the additions to `Ball`, `rational`; the generated scalar kernels on one array per limb (`m2s`); the data, and the tightness of Horner |
| `m2_fenv.cpp` | the props that change the rounding mode, compiled with `-frounding-math` (`/fp:strict`) and, with Clang, `#pragma STDC FENV_ACCESS ON`; it does not include Kairn |
| `m2_packed.cpp`, `m2_fenv_packed.cpp` | packed code (`m2p`), binary64: the generated kernels, and the props that change the mode once around a packed loop |
| `m2_main.cpp`, `bench_util.hpp` | the driver: checks, tightness, timing, JSON |

Every timed function is one row of an X-macro list (`KB_LIST` in `m2.cpp`, `KB_FLIST` in
`m2_fenv.cpp`, `KB_SLIST`, `KB_PLIST`, `KB_FPLIST`): `X(BACKEND, SUFFIX, T, KIND, KERNEL,
VARIANT, REGION, VALUES, CHECK, BODY)`, which the file expands twice, into the function
`kb_m2_SUFFIX_KIND_KERNEL__VARIANT` and into its row of the table. `KIND` is `tp` (a loop of
independent operations over arrays of 256, time per operation), `sum`, `prod`, `step` (a dependent
chain, time per step) or `lat` (dependent evaluations, time per evaluation). The variants:

| Variant | What it is |
|---|---|
| `kairn` | the generated kernel called on the limbs: the reference of every other variant of the kernel |
| `op` | the public operation, written as a client writes it, on arrays of the public types |
| `flat` | the public operation in a function compiled with `__attribute__((flatten))`, which inlines what the compiler would call: the product of intervals of two limbs is an ordinary function, not forced inline |
| `plain` | the same values with the operations of `T`; a kernel named `pair_*`, `plain4_*`, `plain_*` is a floor of plain arithmetic, whose `kairn` reference computes the same values with the generated one-limb kernels |
| `fenv` | `std::fesetround` to downward or upward around each operation, and back to nearest |
| `csr` | the same, writing MXCSR or FPCR directly with values computed once |
| `fenv_loop` | the mode set once around the whole loop or chain; intervals upward only, $\mathrm{RD}(t) = -\mathrm{RU}(-t)$ |
| `nextafter` | `std::nextafter` |

Before anything is timed, every function is checked against `BACKEND/KIND/KERNEL/kairn` (`m2p`
against `m2s`), byte for byte, or by its own check (`kairn::rational` by `is_rational_result`); for
each rounding-mode prop the driver counts how many of its values differ from the same operation
rounded to nearest (what a prop that ignored the mode would have returned); and the props of the
building blocks are compared with Kairn's on a wide sample, $2^{16}$ pairs per operation, limb type
and variant, half of them over every finite value of `T` (`--wide N`): equal, but for the sign of a
zero result and, below $2^{2p-1}\eta$, a product of Kairn one number wider on its side, as the
statement of `mul_down` allows. A failed check stops the run. The driver then measures the
tightness of the Horner evaluation in four regimes (a point, a few units in the last place, the
narrow sets of the timing, wide sets) against the exact range of $T_8$, and times.

```sh
build-bench/bench/kairn-bench-m2-O2 --check-only        # the checks and the tightness
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 \
    --machine "..." --commit "$(git rev-parse --short HEAD)" --json results/milestone2/bench/linux-gcc-O2-r1.json
python3 bench/m2_report.py results/milestone2/bench   # the tables of the results page
```

`kairn-bench-m2-modes-LEVEL` (`m2_modes.cpp`, no Kairn header) times a loop of additions and one
of products under each of the four rounding modes, compiled as plain code, and checks that they
computed under the mode set: whether a directed mode, once set, costs anything
(`--json results/milestone2/bench/modes-MACHINE-COMPILER-LEVEL.json`).

The options are those of `kairn-bench` (`--filter` takes several texts, separated by commas), and
`--wide N`. The JSON has, besides the times, the load average at the start and the end of the
timing, the checks (with the counts against rounding to nearest and the wide sample) and the
tightness.

**The second part** (the second part of the results page) adds four files to the same program, each
with its own table of functions and its own check, which runs the function and its reference on the
file's own arrays and compares their bytes:

| File | What it holds |
|---|---|
| `m2_soa.cpp` | `Packed<T, 2>`, `Packed<T, 1>` and the containers of `soa.hpp`, `double` (backend `m2v`) and `float` (`m2vf`): loops over arrays in structure-of-arrays form, in L1 (KIND `tp`, 512 elements) and in arrays that do not fit the last-level cache (KIND `mem`, 4 Mi elements of `double`, 8 Mi of `float`), time per element; compiled with the flags of packed code, its scalar loops too |
| `m2_soa_scalar.cpp` | the packed loops of `m2_soa.cpp` again in the scalar form of `Packed`, one lane (`m2v1`, `m2vf1`), checked against `m2v` and `m2vf` |
| `m2_enc.cpp` | the enclosure interface of `Interval<T, k>` and `Ball<T, k>` (`m2e`, `m2ef`; the kernel's name starts with the type, `i1_`, `i2_`, `b1_`, `b2_`): predicates, member and subset tests, three-valued comparisons, the relations of IEEE 1788, hull, intersection, split, the midpoint and the radius, the conversions; loops (`tp`) and, for the operations that return a set, chains (`step`) |
| `m2_run.cpp` | whole computations, time per call (`m2r`, KIND `run`): the bisection of `docs/tutorials/bisection.md` (its program included as it is) on four types and its two widths, and `kairn::self_test()` with its two parts |

Their variants, besides `kairn`, `op` and `plain`: `view`, the operation through `SoAView` and its
element proxy; `packed`, `Packed<T, 2>` loaded and stored through `SoAView`; `aos`, an array of
`Expansion<T, 2>`. The JSON has, in `bisection`, what each bisection found (evaluations, parts kept,
parts `split()` did not narrow, zeros, their radii), and `kairn_checks` and, with `--filter`, the
filter. With `--filter` the driver checks the functions it will time; without, every function.

`kairn-bench-m2-checks-LEVEL` is the same program, inline setting, with `KAIRN_CHECKS` 1 in every
translation unit: the cost of the checks is the ratio of a function's time in it to its time in
`kairn-bench-m2-LEVEL`, both run alternately with one filter (the method of `costs.cpp`). The runs of
the second part are stored as `ITEM-MACHINE-COMPILER-LEVEL-rN.json`, ITEM `soa`, `enc`, `bisect`,
and `checks-...-cK-rN.json` for the two programs, and printed by `m2_report.py --part 2`:

```sh
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 --filter m2v --machine "..." \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone2/bench/soa-linux-gcc-O2-r1.json
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 \
    --filter m2e,m2/tp/plain_midrad_1/,m2/tp/plain_bounds_1/,m2f/tp/plain_midrad_1/,m2f/tp/plain_bounds_1/ ... enc-...
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 --filter m2r/ ... bisect-...
F=m2/tp/interval_,m2/sum/interval_,m2/prod/interval_,m2/tp/horner_i,m2e/
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 --filter $F ... checks-linux-gcc-O2-c0-r1.json
taskset -c 50 build-bench/bench/kairn-bench-m2-checks-O2 --cpu 50 --reps 31 --filter $F ... checks-linux-gcc-O2-c1-r1.json
python3 bench/m2_report.py --part 2 results/milestone2/bench
```

The compile time of `kairn::self_test()` is `compile_time.py run --units empty,include,self_test`;
that of the enclosure interface is `enclosure_costs.py compile --kind compare`, `contains` or
`setops` (calls of the three-valued comparisons; of `contains` of a point and of a set; of `hull`,
`intersection` and `split`; on the four types in turn, each call on operands of its own), stored as
`compile-MACHINE-COMPILER-KIND.json` (1 000 calls, three compilations of each unit, `--once-from
10000`) and `compile-MACHINE-COMPILER-KIND-10000.json` (10 000 calls, `-O2`, one compilation), and
printed by `m2_report.py` with the first part's compile tables.

**The third part** (the functions on arrays, the accumulator and the ball vectors) adds two files
to the same program, in the manner of the second part's (each with its own table of functions and
its own check), a program of its own for the errors, a copy of the headers for the check at
entry, and units for the compile time:

| File | What it holds |
|---|---|
| `m2_batch.cpp` | the functions of `kairn/batch.hpp` (`m2a` for `double`, `m2af` for `float`): `sum`, `sum_fast`, `dot`, `add`, `scale`, `axpy`, `norm_upper` over arrays in L1 (KIND `tp`, 512 elements), in the last-level cache (`llc`, 128 Ki elements of `double`, 256 Ki of `float`) and in no cache (`mem`, 4 Mi and 8 Mi), and `conv` of 16, 64 and 512 coefficients, the time per element (per term for `conv`); short arrays (`m2k`, `double`): 256 calls of `sum` and `dot` on windows of 1 to 1024 elements of one array, independent (`tp`) or each waiting for the one before (`lat`), the length read at run time (kernel `NAME_nN`) or known to the compiler (`NAME_kN`), the time per call; the accumulator (`m2c`): `add` and `add_product` per element, partial accumulators merged, `merge`, `sum()`, `error_bound()` and `ball()` of 256 accumulators. Compiled as packed code: the default order is the lane order of the unit's form of `Packed` |
| `m2_bv.cpp` | `BallVector<double, k, N>` against `std::array<Ball<double, k>, N>` (`m2w`, kernel `OP_k_N`, N = 4, 8, 16, 64): `add`, `sub`, `scale`, `axpy`, the product of polynomials (`conv`) and `norm_upper` on 256 / N vectors, the time per operation on a whole vector; and the widths (`m2_bv_widths_json`, in the JSON as `ball_vector_widths`): the one radius against the largest and the median of the entries' radii after one operation and after chains of 10 and 100 |
| `m2_bvs.cpp` | short ball vectors of fixed length (`m2x`, kernel `OP_k_N`, N = 3, 7, 13, 18, 80): `add`, `x + y`, `sub`, `scale`, `half` and the constructor from centers and a radius, on many vectors (`tp`) and in a chain of 256 operations each on the result of the one before (`lat`), the time per operation, every size in one unit; compiled again with `KB_BVS_ONE` as 60 units of one operation and one size each (`m2y`, the same kernels; CMake generates them into the build tree), since what a compiler inlines depends on the size of the unit; with `kairn-bench-m2-nocheck-LEVEL` (and `kairn-bench-m2-before-LEVEL`), what the check at entry costs these operations |
| `m2_exact.hpp` | exact sums of `double` (a fixed-point accumulator of 2240 bits): the reference of the checks of the two files above and of the errors |
| `m2_accuracy.cpp` | `kairn-bench-m2-accuracy-LEVEL`: the errors of the sums and dot products of one and two limbs, the naive loop, Sum2 and Dot2 of Ogita, Rump and Oishi, and the accumulators, against the exact result, on data of chosen condition (GenDot of the same authors), and the stated bounds over the errors; nothing is timed |
| `entry_check.py` | `copy DEST`: a copy of `include/kairn` with the check of the environment at the batch entries compiled out (`detail::check_batch_environment` returns `true`), never committed; with `-DKAIRN_BENCH_NOCHECK_INCLUDE=DEST` CMake builds `kairn-bench-m2-nocheck-LEVEL`, the same program against it. `before DEST [--commit C]`: the headers of an earlier commit (by default `25ebe3d6`, the last whose checks compiled the report inline), from git; `-DKAIRN_BENCH_BEFORE_INCLUDE=DEST` builds `kairn-bench-m2-before-LEVEL`. `check`: whether the header has the form the script expects. Until 2026-11-23 a variant `cold` made a third copy with the report out of line and cold, a candidate change of the header, built as `kairn-bench-m2-cold-LEVEL` (the runs `entryx-...-cv-*`); the header now has that form, and the variant is gone |
| `compile_time/batch.cpp` ... | the include units of `compile_time.py` (`batch`, `ball_vector`, `accumulator`, `kairn_batch`, `kairn_ball_vector`, `include_packed`); `enclosure_costs.py --kind arrays` and `ballvectors`, units of N calls |

Their variants, besides `op`, `kairn` (the generated loop the public function calls, on the limbs:
the public function without its check at entry) and `plain` (the same loop on `T`, element after
element; for `dot` and `conv` of one limb with an FMA, as Kairn's step): `seq` (the public function
with `kairn::sequential`), `kseq` (the generated sequential loop, for a map the loop of one lane),
`bare` (the generated loop on stored arrays, the same steps without the guards of rule R3: `sum_1`,
`dot_k`, `add_k`, `scale_2`, `axpy_k`, `conv_k`, the kernels `acc_mul_1` and `acc_mul_2`),
`plainw` (the plain loop in the lane order of the default), `textbook` (Sum2 and Dot2 for one limb;
for two limbs the double-word arithmetic of `props.hpp` written out, element after element), and
for ball vectors `balls` (the operators of `Ball`, entry by entry). Every function is checked
before it is timed: `op` and `bare` against `kairn`, `seq` and `plain` against `kseq`, `plainw`
against `kairn`, byte for byte; the references and the textbook loops against the exact result
within their stated bounds; `balls` against `op` (the same centers; the one radius against the
entries'). The runs are stored as `ITEM-MACHINE-COMPILER-LEVEL-rN.json`, ITEM `arrays` (filter
`m2a/,m2af/`), `short` (`m2k/`), `acc` (`m2c/` and the sums and dot products of `m2a/tp/` and
`m2a/llc/`, for the ratios within one run) and `bv` (`m2w/`); the pairs of the check at entry as
`entry-MACHINE-COMPILER-LEVEL-cK-rN.json`, K 1 for `kairn-bench-m2-LEVEL` and 0 for
`kairn-bench-m2-nocheck-LEVEL`, run one after the other with the filter `m2k/,m2w/,m2a/tp/`; the
triplets of the short ball vectors as `entryx-MACHINE-COMPILER-LEVEL-cK-rN.json`, K 1, 0 and `v` for
`kairn-bench-m2-cold-LEVEL` (the cold copy of that day), with the filter `m2x/,m2y/`; the errors as `accuracy-MACHINE-COMPILER-LEVEL.json`; the compile times as
`headers-compile-MACHINE-COMPILER.json` and `compile-MACHINE-COMPILER-arrays.json`,
`-ballvectors.json`. Runs named `r3-ITEM-...` (the same items and programs) are the functions whose
code changed when rule R3 on the factors of a fused operation was closed (`dot`, `axpy` and `conv` of
two limbs, the scaling and the constructors of ball vectors of two limbs), measured again at that
tree with the functions their ratios divide by; `m2_report.py` puts each in place of the same
functions of the earlier run of the same index and configuration, and lists both in its table of the
runs. The filters of those runs:

| ITEM of `r3-` | Filter |
|---|---|
| `arrays` | `m2a/tp/dot`, `m2a/llc/dot`, `m2a/mem/dot` and the same for `axpy`, for `m2af/`, and `tp/conv1_`, `tp/conv2_` of both |
| `short` | `sdot2_,sdot1_n` |
| `acc` | `m2c/tp/acc2prod,m2c/llc/acc2prod,m2a/tp/dot2,m2a/llc/dot2` |
| `bv` | `m2w/tp/scale_2_` |
| `entry` (pairs) | `sdot2_,sdot1_n,m2w/tp/scale_2_,m2a/tp/dot2,m2a/tp/axpy2,m2a/tp/conv2_` |
| `entryx` (triplets) | `scale_2_` and `make_2_` of `m2x/` and `m2y/`, `tp` and `lat` |

`m2_report.py --part 3` prints the tables:

```sh
python3 bench/entry_check.py copy /tmp/nocheck      # then -DKAIRN_BENCH_NOCHECK_INCLUDE=/tmp/nocheck
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 --filter m2a/,m2af/ --machine "..." \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone2/bench/arrays-linux-gcc-O2-r1.json
F=m2k/,m2w/,m2a/tp/
taskset -c 50 build-bench/bench/kairn-bench-m2-O2 --cpu 50 --reps 31 --filter $F ... entry-linux-gcc-O2-c1-r1.json
taskset -c 50 build-bench/bench/kairn-bench-m2-nocheck-O2 --cpu 50 --reps 31 --filter $F ... entry-linux-gcc-O2-c0-r1.json
build-bench/bench/kairn-bench-m2-accuracy-O2 --machine "..." --commit "..." --json results/milestone2/bench/accuracy-linux-gcc-O2.json
python3 bench/compile_time.py run --cxx g++ --configs O2,O3 --reps 7 --cpu 40 \
    --units empty,include,include_packed,accumulator,batch,ball_vector,kairn_batch,kairn_ball_vector ... --json headers-compile-linux-gcc.json
python3 bench/enclosure_costs.py compile --cxx g++ --flags=-mavx2 --kind arrays --sizes 100,1000 \
    --settings inline,calls --reps 3 ... --json results/milestone2/bench/compile-linux-gcc-arrays.json
python3 bench/m2_report.py --part 3 results/milestone2/bench
```

**The check at entry measured again (2026-11-23).** When the report of the check moved out of line
and the short constructors of `BallVector` were forced inline, the same functions were measured
again, three programs per configuration built from one tree: `kairn-bench-m2-before-LEVEL` (the
headers of `25ebe3d6`, `entry_check.py before`), `kairn-bench-m2-LEVEL` (the headers of the tree) and
`kairn-bench-m2-nocheck-LEVEL` (`entry_check.py copy`), run one after the other in that order, three
rounds, with the filter `m2k/,m2x/,m2y/` (the short arrays and the short ball vectors), and stored as
`recheck-MACHINE-COMPILER-LEVEL-cK-rN.json`, K `b`, `1` and `0`. `m2_report.py --part 4` prints their
tables: each program's time minus the time without the check, in the same round, and the ratio of the
two headers.

```sh
python3 bench/entry_check.py copy /tmp/nocheck
python3 bench/entry_check.py before /tmp/before
cmake -S . -B build-bench -G Ninja -DCMAKE_BUILD_TYPE=Release -DKAIRN_BUILD_TESTS=OFF -DKAIRN_BUILD_BENCHMARKS=ON \
      -DKAIRN_BENCH_NOCHECK_INCLUDE=/tmp/nocheck -DKAIRN_BENCH_BEFORE_INCLUDE=/tmp/before
F=m2k/,m2x/,m2y/
taskset -c 12 build-bench/bench/kairn-bench-m2-before-O2 --cpu 12 --reps 31 --filter $F ... recheck-linux-gcc-O2-cb-r1.json
taskset -c 12 build-bench/bench/kairn-bench-m2-O2 --cpu 12 --reps 31 --filter $F ... recheck-linux-gcc-O2-c1-r1.json
taskset -c 12 build-bench/bench/kairn-bench-m2-nocheck-O2 --cpu 12 --reps 31 --filter $F ... recheck-linux-gcc-O2-c0-r1.json
python3 bench/m2_report.py --part 4 results/milestone2/bench
```

## Other costs

The tools behind [Compile times and other costs, Milestone
1](../docs/developer/results/costs-milestone1.md), whose measurements are in
`results/milestone1/costs/`. None of them is part of the library or of the tests.

### Compile time

`compile_time.py` compiles the translation units of `compile_time/` and the runners of
`gen/tests/` with one compiler, each under each configuration, several times in rounds over all
of them, and records the wall time, the processor time and the peak memory of every compilation
(the largest resident set of the compiler and the processes it waits for, or the peak working set
of `cl.exe`), and the size of the object. Nothing is linked.

| Unit | What it compiles |
|---|---|
| `empty` | nothing: what starting the compiler costs |
| `std_headers` | `<cmath>` and the standard and intrinsics headers that `kairn/kairn.hpp` includes |
| `kairn_std` | the same without `<cmath>`, which Kairn does not include |
| `iostream` | `<iostream>`, for scale |
| `include` | `kairn/kairn.hpp`, nothing used |
| `use_e2` | every public operation of `Expansion<double, 2>` and `Ball<double, 2>` once (`compile_time/use.hpp`) |
| `use_all` | the same for `Expansion` and `Ball` with `float` and `double` limbs, one and two limbs |
| `self_test` | one call of `kairn::self_test()`, which runs every kernel for both limb types |
| `kernels_scalar`, `kernels_packed` | `kairn/gen/scalar.hpp`, or `avx2.hpp` / `neon.hpp`, alone, every kernel of `gen/tests/runner_kernels.inc` called for both limb types |
| `runner`, `packed_runner` | `gen/tests/runner.cpp` and `gen/tests/packed_runner.cpp`, the runners of the quick tier |

In `use.hpp` each operation is a non-inlined function of its own, as a client's code is spread
over functions; an explicit instantiation emits all of them. The configurations are `-O0`, `-O2`
and `-O3` with `-DNDEBUG`, and `debug`, CMake's Debug (`-O0 -g`, no `NDEBUG`, so `KAIRN_CHECKS`
is 1); with MSVC `/Od` and `/O2` with `/DNDEBUG`, and `/Od /Z7 /RTC1` (`/Z7` rather than CMake's
`/Zi`, which would start a PDB server). Every compilation has `-std=c++20` and the FMA option of
`kairn::fma` (`-mfma` on x86-64, `/arch:AVX2`), the packed units `-mavx2 -mfma` on x86-64.

```sh
python3 bench/compile_time.py run --cxx g++ --reps 7 --cpu 40 --machine "..." \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone1/costs/compile/compile-linux-gcc.json
python3 bench/compile_time.py per-kernel --cxx g++ --reps 7 --cpu 40 --json ...   # -O2 by default
python3 bench/compile_time.py phases --cxx g++ --reps 3 --json ...
python3 bench/compile_time.py kernels --json results/milestone1/costs/compile/kernel-sizes.json
python3 bench/compile_time.py report results/milestone1/costs/compile
```

Clang on Linux takes `--flags "--gcc-install-dir=..."` where it needs one; MSVC `--cxx cl --msvc`
in a developer prompt. `per-kernel` compiles `kernels_scalar.cpp` and `kernels_packed.cpp` once
with an empty table and once per kernel with that kernel alone: the difference is what the kernel
costs. `phases` asks the compiler where the time goes (GCC `-ftime-report`, Clang `-ftime-trace`,
MSVC `/Bt+`). `kernels` counts the lines and operations of every generated kernel. `--cpu` pins
the script, and every compiler it starts, to one logical processor (Linux, Windows). Every
compilation has a timeout, and on a timeout only the process the script started is terminated,
after (on Linux and macOS) the processes it started itself: the compiler proper, which a driver
runs as its child and which would otherwise keep running on the same core.

### Constants from fractions

`rational_cost.py` measures `kairn::rational` (`include/kairn/rational.hpp`): `compile` compiles a
translation unit with 1, 100 and 1000 distinct constants of `Expansion<double, 2>`, with
`KAIRN_RATIONAL_CHECK` 0 and 1, and the same unit without constants, several times in rounds, and
prints the median times and what each constant adds; `run` builds a program that times one call of
`rational` and of `is_rational_result` per type, at run time. It writes its units into `--workdir`.

```sh
python3 bench/rational_cost.py compile --cxx g++ --reps 5 --flags=-mfma
python3 bench/rational_cost.py compile --cxx cl --msvc --flags=/arch:AVX2 --json rational-msvc.json
python3 bench/rational_cost.py run --cxx clang++ --flags=-mfma
```

`--types e1,e2` makes the units for `Expansion<double, 1>` as well, `--counts 10,100,1000` the
counts of Milestone 2's page (`results/milestone2/bench/rational-compile-*.json`, printed by
`m2_report.py`), `--cpu N` pins (Linux). The time of one call at run time is also timed by
`kairn-bench-m2` (`m2/tp/rational_*`), for small and 64-bit terms.

### The settings of `KAIRN_ENCLOSURE_CODE`

The tools behind [Compile times and other costs, Milestone
2](../docs/developer/results/costs-milestone2.md): what the operations of `Ball` inline, outlined
and external (`include/kairn/config.hpp`) cost at compile time and at run time, with the
measurements in `results/milestone2/costs/`.

`enclosure_costs.py compile` writes translation units with 100, 1 000 and 10 000 operations of
`Ball<double, 2>` in straight-line code in one function (`enclosure_costs.py source N` prints one: a
mix of `+`, `-`, `*` and the scaling by a `double`, each on two of the eight values computed last,
each result stored so that none is dead), compiles each at `-O2` and `-O3` (`/O2`) with `NDEBUG` in
each setting, three times in rounds (once for the largest), and records the wall time, the
processor time, the peak memory and the size of the object, as `compile_time.py` measures them;
and the same for `definitions.cpp`, the one file that defines the operations in the external
setting. Nothing is linked. `--settings calls` compiles the same units without Kairn, the
operations functions declared only on a structure of three `double`s: what the calls themselves
cost the compiler.

```sh
python3 bench/enclosure_costs.py compile --cxx g++-16 --reps 3 --workdir /tmp/enclosure \
    --machine "..." --commit "$(git rev-parse --short HEAD)" --json results/milestone2/costs/compile-gcc16.json
python3 bench/enclosure_costs.py report results/milestone2/costs
```

`--kind interval1`, `interval2` or `mixed` writes units of intervals, or of `Ball<double, 2>`,
`Interval<double, 1>` and `Interval<double, 2>` in turn, in which each operation takes one of the
eight values of its type computed last and one of eight inputs near 1, so that every value stays a
finite enclosure; with `--run` the object of the first compilation of each unit is linked with a
driver that `enclosure_costs.py` writes (and, external, with `definitions.cpp`) and run: the time
per operation of the unit itself, in each setting. `--flags` adds options to every compilation
(Clang 18 on Linux needs `--flags=--gcc-install-dir=...`), `--cpu N` pins the script and what it
starts (Linux). [Benchmarks, Milestone 2](../docs/developer/results/bench-milestone2.md) reports
these units, with the measurements in `results/milestone2/bench/compile-*.json`:

```sh
python3 bench/enclosure_costs.py compile --cxx g++ --kind mixed --cpu 26 --sizes 100,1000,10000 \
    --settings inline,outlined,external,calls --reps 3 --run --run-reps 21 --workdir ... \
    --machine "..." --commit "..." --json results/milestone2/bench/compile-linux-gcc-mixed.json
python3 bench/enclosure_costs.py report results/milestone2/bench
```

At run time, the harness above is built once more per setting, `kairn-bench-outlined-LEVEL` and
`kairn-bench-external-LEVEL` (with `definitions.cpp`), every translation unit with the setting;
`--filter ball` times the operations of `Ball` (`api/.../op`: the public operators, in a loop of
independent operations and in dependent chains) next to the generated kernels called directly
(`scalar/...`, `api/.../kairn`), which no setting changes. `report` reads the runs as
`run-COMPILER-SETTING-LEVEL.json`, SETTING `inline` for `kairn-bench-LEVEL`.

```sh
build-bench/bench/kairn-bench-outlined-O3 --filter ball --reps 31 --machine "..." \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone2/costs/run-gcc16-outlined-O3.json
```

### The checks of `KAIRN_CHECKS`, and MSVC's stack cookie

`costs.cpp` is a small benchmark of its own, timed as `kairn-bench` times (non-inlined functions
called through a pointer, loops over arrays in L1 per operation and chains per step, samples of
about 4 ms, the minimum over the samples): `kairn::environment_ok()` in a loop; `x + y` and
`x * y` on `Expansion<double, 2>` in a loop and in a chain; `x + y` on `Expansion<double, 1>` in a
loop, in a chain and as a call of a non-inlined function per element, next to the same on
`double`; and a chain of `double` additions and one of fused multiply-adds for scale.
`KAIRN_CHECKS` must be the same in every translation unit of a program, so each value is a
program: `kairn-bench-costs-LEVEL` (0) and `kairn-bench-costs-checks-LEVEL` (1), for `O0` and the
levels of `kairn-bench`. Each records a checksum of its outputs, which the two programs must agree
on. For the cookie, the same programs are built again with `/GS-` added to `CMAKE_CXX_FLAGS`.

```sh
taskset -c 40 build-bench/bench/kairn-bench-costs-checks-O2 --cpu 40 --reps 31 \
    --machine "..." --commit "$(git rev-parse --short HEAD)" --json results/milestone1/costs/checks/...
```

`gs_probe.py` (in a developer prompt) says which functions MSVC protects with a `/GS` stack
cookie: `probe` compiles `gs_probe.cpp`, the same shapes of code (one operation, a loop, a chain, a
dot product, `axpy`, Horner) on `double`, `Expansion<double, 1>`, `Expansion<double, 2>`,
`Ball<double, 1>` and `Ball<double, 2>`, and the same with `float` limbs, with `/GS` and `/GS-`,
and reads `dumpbin /disasm` for `__security_cookie` and `__security_check_cookie` (`--level`
replaces `/O2`, `--all` reports the functions of Kairn that are not inlined too, `--include` names
other headers); `objects` does the same on objects built elsewhere (`kairn-bench`'s
`api.cpp.obj`); `isolate` compiles `gs_isolate.cpp`, one-limb types that differ from
`Expansion<double, 1>` in one thing each; `fix` compiles `gs_probe.cpp` against a copy of the
headers in the work directory in which every parameter `Expansion<T, 1>` of `expansion.hpp` is
passed by const reference (the variant A of the results page; the headers pass it so in the
operators only). `listing`, with GCC or Clang, compiles `gs_probe.cpp` to assembly and records
each function's number of instructions and a hash of them, to compare two versions of the headers.

```sh
python3 bench/costs_report.py results/milestone1/costs/checks results/milestone1/costs/gs
```

prints the tables of the results page from the stored runs of `costs.cpp` and `kairn-bench`
(named `MACHINE-COMPILER[-GS]-PROGRAM-LEVEL-rN.json`) and of `gs_probe.py`, and those of the fix of
the cookie from `results/milestone1/costs/gs/fix/`.

### The quick tier on the hosted runners

`ci_times.py collect` reads, with read-only `gh` calls, the last runs of the workflow "Build and
test" on `main`: per job, the duration of each step and of the job, and from the job's log the
time of each test; `ci_times.py tables FILE` prints the tables of the results page.
