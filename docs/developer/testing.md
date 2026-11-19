# Testing

How Kairn's code is tested, what each test is for, and how to rerun one case of a failing test
by hand. The parts named here (generator, interpreter, oracle, runner, claims) are described in
[Architecture](architecture.md#the-pipeline).

## The tiers

| Tier | What | Where it runs | Time |
|---|---|---|---|
| Quick | `ctest --test-dir build`: every kernel through every compiled runner on a small sample, every public operation on a small sample, the examples, the negative controls, the consumer checks, and the fast parts of the generator's and the oracle's own tests ([below](#the-quick-tier)) | every push and pull request, on every platform of the CI (`build.yml`); and by anyone, with the three commands of [Getting started](../getting-started/index.md#configure-build-and-test) | 44 seconds to two minutes with `--parallel 4` ([Time](#time)) |
| Full | `ctest --test-dir build/tests/full`: everything that left the quick tier, named `full.*`: the same cross-checks on more cases, the interpreter's enumerations of toy formats, and the longest parts of the generator's and the oracle's own tests ([below](#the-full-tier)) | every push and pull request, in jobs beside the quick tier's (`full.yml`, and `generator.yml` for the generator's part); and by hand | five to eight minutes with `--parallel 4` |
| Generator | `python3 gen/kairn-gen test`: the generator's whole suite, C++ included | every push and pull request, with each GCC-style compiler of the CI, and without its C++ tests on Windows | a few minutes per compiler |
| Proofs | `make -C proofs`: every Rocq proof, then the axiom audit | every push and pull request | a minute or two, with four cores |
| Brute force | `tests/brute/brute.py`: the cross-checks of the compiled runners on millions of random cases per kernel, format and machine (every runner of a machine on the same cases), and the interpreter on every operand of larger toy formats, with the same guards and a time budget | by hand, on the test machines, never in CI (`tests/brute/README.md`); results in [Brute force, Milestone 1](results/brute-milestone1.md) | about 90 minutes per machine for Milestone 1 |

ctest runs the quick tier in the build directory and the full tier in `tests/full` of it, and says
which before the first test and after the summary (`Kairn tests: the quick tier, 276 tests. The
full tier, 291 tests more: ctest --test-dir .../tests/full`); every test of the quick tier also
has the label `quick`, and every test of the full tier the label `full`. Both are registered by
the same configuration: the file `CTestCustom.cmake` that configuring writes at the top of the
build tree leaves the full tier out of a run there (`CTEST_CUSTOM_TESTS_IGNORE`), so that
`ctest -R` in the build directory never selects a `full.*` test, and a run in `build/tests` runs
both. The full tier is registered only when Kairn is the top-level project and Python 3 is found.

A kernel's claims are only as good as the tests that could have refuted them, so every cross-check
fails when it checked nothing, or less than it says: when the oracle judged no case, when an
enumeration did not cover the domain it names, when a random run missed a stratum, or when a claim
was never put to the test ([below](#what-a-pass-requires)).

## The quick tier

The tests that `ctest` runs in the build directory, by name:

| Test | Checks |
|---|---|
| `kairn-gen.check` | Every committed generated file is what `python3 gen/kairn-gen build` writes. |
| `kairn-gen.test` | The generator's own tests, without those that compile C++ (`--no-cxx`, see [the generator's tier](#the-generators-tier)) and without its four longest test classes (`--skip`), which `full.kairn-gen.test` runs. |
| `kairn-oracle.selftest` | The oracle's own tests (`--quick`), including injected errors it must catch, without its six enumerations of toy formats (`--skip`), which `full.kairn-oracle.selftest` runs. It compiles its own C++ reference runner with the build's compiler; if that fails, the test fails. |
| `kairn-oracle.claims` | The oracle can read every claim in `gen/claims.json`. |
| `docs.reference.check`, `docs.reference.test` | The reference pages of the site are what `docs/tools/reference.py` writes, and that script's own tests ([Documentation](documentation.md#reference-pages)). |
| `crosscheck.compiled.K.F` | Kernel K compiled with the build's compiler and flags, scalar (`gen/tests/runner.cpp`) and packed (`gen/tests/packed_runner.cpp`, the backend of the target, [below](#packed-kernels)), once as the flags stand and once with each contraction setting added to them ([below](#contraction)): each of these runners on the same 6 000 random cases of format F (`binary64`, `binary32`) from every stratum. |
| `crosscheck.guards` | The cross-checks' guards fail the runs they are there to fail (`tests/test_crosscheck_guards.py`). |
| `consume.*` | A CMake project that uses Kairn through `add_subdirectory`, and one through `find_package` after `cmake --install`, build and run a kernel. |

The tests of the public interface (`tests/api/`, label `api`):

| Test | Checks |
|---|---|
| `api.oracle.K.F` | Every public operation that calls kernel K, computed through the constructors, operators and functions of `kairn/kairn.hpp` (`tests/api/runner.cpp`, a runner of the line protocol), on 2 000 random cases of format F, judged by the oracle against K's claims; by two runners on the same cases, one built with the build's flags and one with contraction forced on. For a kernel of the extended domain the cases include infinite and NaN operands and empty and whole balls, built through the public constructors. Each form of the operation (`x + a` and `a + x`, `x += a`, `x + y` with a one-limb `y`, the marked and the unmarked operator, `kairn::finite::add`) is judged on its own. A few forms can compute only some lines of their kernel (`ldexp` needs a power of two among the operands of `mul_1_1`, a point form a ball of radius 0, the steps of `ldexp` an operand that can be scaled exactly); they compute the plain operation on the others, and fail if a stream of 1000 lines or more reached their own operation on none, which is why the quick tier has at least 1 000 cases. |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is called by a public form of the runner, or is a building block, or is an entry kernel (`entry: yes` in `gen/kernels`) on the runner's short list of those not public yet, each with its reason (today the finite cores of the Ball operations); no entry kernel is a building block. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, infinities, NaN and the states of a ball included, comparisons with a NaN among them; the same results at run time; the properties of the types; and that an operation compiles without `kairn::unverified` exactly when the kernel it calls is proved. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass in the default environment and fail under each directed rounding mode and under flush-to-zero. |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break the kernels and define no macro (reassociation; `-ffp-model=fast`; on AArch64 `-fno-signed-zeros` with `-ffp-contract=fast`): `kairn::self_test()` must fail. |
| `api.reject.*` | What must not compile, each with a control that compiles: the flags `config.hpp` rejects; each kind of operation and constructor written without the marker while its kernel is unverified (`unverified.*`, against a copy of the headers in which every kernel is); and an operation whose kernel alone is unverified, which must not compile through a conversion to another, proved kernel (`unverified_only.*`: `x + a` through `x + Expansion(a)`, a ball times a `T` through a point ball). |
| `api.boundary.S`, `api.boundary.unguarded.S` | A product the program computes and passes in (`x + a * b`, `E2(a * b)`, `from_limbs`, `kairn::finite::add`, a ball's center, radius or point) gives the result of the same operation on the rounded product, bit for bit, under contraction setting S; built against a copy of the headers in which the generated guard is taken out of `gen/scalar.hpp` (made at configure time, which fails if it finds no guard), it must not where the compiler was measured to fuse across statements (`tests/api/boundary.cpp`). |
| `api.k1.zero_cost` | The instructions emitted for loops over `Expansion<double, 1>` against the same loops over `double` (`tests/api/k1/zero_cost.py`). |
| `api.example.*` | The examples of the documentation (`docs/examples/cpp/`), which check their own output; `api.example.accurate_sums.*`, built under each contraction setting, also compares it with the text its tutorial shows ([Documentation](documentation.md#examples)). |

## The full tier

The tests that `ctest --test-dir build/tests/full` runs, by name, each named as the quick tier's
test it extends, with `full.` in front:

| Test | Checks |
|---|---|
| `full.crosscheck.compiled.K.F` | `crosscheck.compiled.K.F` on 20 000 cases instead of 6 000: the cases of the same seed from case 0, so that the quick tier's are the first 6 000 of these. |
| `full.api.oracle.K.F` | `api.oracle.K.F` on 10 000 cases instead of 2 000, the quick tier's among them. |
| `full.crosscheck.interp.K` | Kernel K run by the generator's interpreter on **every** operand combination of a toy format. |
| `full.crosscheck.interp-restricted.K` | Kernel K run by the interpreter on every operand of a **restricted** domain of a toy format, for the kernels whose whole enumeration is too long. |
| `full.crosscheck.interp-sampled.K` | The same kernels on 20 000 random cases of the whole toy format, from every stratum. |
| `full.kairn-gen.test` | The four test classes of the generator that `kairn-gen.test` leaves out (`-k`): the interpreter against the machine's own arithmetic (Python's float and `math.fma`) on thousands of cases per kernel and format and against every rounding of toy formats, and the statements of the IEEE model and of the non-finite layer on every operand of small formats. With four worker processes. |
| `full.kairn-oracle.selftest` | The six tests of the oracle that `kairn-oracle.selftest` leaves out (`--only`): its Python reference runner, correct and with injected errors, on every case of tiny formats. With four worker processes. |

The names of the parts left out are in `tests/CMakeLists.txt` (`_gen_full`, `_oracle_full`), and
both tools fail when a name they are given matches no test, so that a test renamed cannot drop out
of both tiers. A label says what a test of the full tier depends on, which is how the CI runs each
where it must and no more ([Continuous integration](#continuous-integration)): `python`, on
Python alone, in exact arithmetic, the same everywhere (run once, on Linux); `generator`, on the
machine's arithmetic as well (run on every operating system, inside the generator's whole suite in
`generator.yml`); neither, on the compiler (run on every platform and compiler of the CI).

Labels select groups in either tier: `-L crosscheck`, `-L compiled`, `-L interp` (with
`-L restricted` and `-L sampled` among them), `-L api` (with `-L oracle`, `-L reject` and
`-L boundary` among them), `-L python`, `-L generator`; `-R` selects by name, for example
`ctest --test-dir build -R mul_2_2` for the quick tier's tests of `mul_2_2`.

## Cross-checks

A cross-check is one pipeline: the oracle writes requests, a runner completes them, and the oracle
judges every completed line against the kernel's claims in exact arithmetic
([the line protocol](architecture.md#the-line-protocol)). The test prints the oracle's report,
pass or fail; on failure it also prints the command that reruns one case (below).

- **Every kernel** in `gen/claims.json` gets its tests: adding a kernel to the generator adds them.
- **Random cases**: 6 000 per kernel and format in the quick tier (`KAIRN_CROSSCHECK_QUICK_CASES`)
  and 20 000 in the full tier (`KAIRN_CROSSCHECK_CASES`), seed 0 (`KAIRN_CROSSCHECK_SEED`), so
  that a run is the same everywhere and can be repeated. The oracle's generator chooses the strata
  from the kernel's family (`oracle/README.md`): those of the first wave for sums and products,
  and the families of the second wave (conversions, comparisons, directed steps, scaling, balls)
  each with strata of its own; a kernel of the extended domain also gets those of the non-finite
  layer (non-finite operands, $0 \cdot \infty$, overflow, the `finite_when` thresholds, the states
  of balls, the radii of constructors). It takes the strata in turn, by a fixed schedule, so that
  every sample longer than the schedule has cases of each; the quick tier's 6 000 cases have 261 to
  1 500 per stratum, of 7 to 16 strata.
- **Every compiled runner on the same cases**: a test of the compiled runners
  (`tests/crosscheck.cmake`) generates the requests once, into a file, and has each runner of the
  build complete that file (`tests/run_runners.py`). Every output is judged, but one that is the
  same, byte for byte, as an output judged before is not judged again: the oracle's verdict and
  summary depend on nothing but the lines it reads and the claims, so the first runner's verdict
  is that of every runner that wrote the same bytes, and the report says which runners share it.
  With GCC 13, Clang 18 and Apple clang 21, every runner of a build writes the same bytes, scalar
  and packed, under every contraction setting, so the oracle judges one output per test. With
  MSVC, four kernels (`make_2`, `make_2_limbs`, `ball_make_1`, `ball_make_2`) have two: the
  packed runner, or the one built with `/fp:strict`, returns a zero of the other sign on some
  lines, which the claims allow. `api.oracle.K.F` does the same with its two runners and the
  forms of each (`tests/api/pipeline.cmake`): one output per test there too, but for
  `mul_pow2_2`, whose two forms differ on the lines where one computes the plain operation, and,
  with MSVC, a few forms that return a zero of the other sign (`mul_2_1_full`, `to_nearest_2`,
  and on the full tier's cases `mul_2_2_full` and `ball_mul_2_full`).
- **The toy formats** depend on the kernel's domain and inputs, each written as its role: `1` a
  limb, `2` a normalized pair, `r` a radius (`nonneg()`), `c` a power of two (`power_of_two()`).
  They are chosen so that each enumeration is 50 000 to 250 000 cases and at least the kernel's
  minimum precision. The tables are in `tests/CMakeLists.txt`; a kernel whose inputs have no
  entry, or whose minimum precision is above its toy format's, gets a test that fails and says
  so, rather than a run where nothing is claimed. For the kernels of the finite domain, the
  range of products is below 1, so that most products neither overflow nor vanish:

    | Inputs | Kernels | Toy format | Cases |
    |---|---|---|---|
    | `1` | `split` | `fp:11:-30:10` | 86 015 |
    | `1 1` | `two_sum`, `fast_two_sum`, `add_1_1` | `fp:5:-7:4` | 172 225 |
    | `1 1` | `two_prod`, `two_prod_dekker`, `mul_1_1` | `fp:5:-12:-1` | 172 225 |
    | `2 1`, `1 2` | `add_2_1`, `sub_2_1`, `sub_1_2` | `fp:4:-4:2` | 221 361 |
    | `2 1` | `mul_2_1` | `fp:4:-8:-2` | 221 361 |
    | `2 2` | `add_2_2`, `add_fast_2_2`, `sub_2_2` | `fp:3:-3:2` | 178 929 |
    | `2 2` | `mul_2_2` | `fp:4:-7:-3` | 245 025 |
    | `2 c` | `mul_pow2_2` | `fp:5:-6:2` | 144 755 |
    | `1 r 1` | `ball_scale_1` | `fp:3:-5:0` | 84 700 |
    | `2 r 1` | `ball_scale_2` | `fp:2:-4:1` | 60 102 |
    | `1 r 1 r` | `ball_add_1`, `ball_sub_1` | `fp:2:-3:1` | 76 176 |
    | `1 r 1 r` | `ball_mul_1` | `fp:2:-4:1` | 142 884 |

    The kernels of the extended domain (the non-finite layer, [Claims of the non-finite
    layer](architecture.md#claims-of-the-non-finite-layer)) read the roles in that domain: `1`
    is any value of the format, infinities and NaN included; `2` a canonical pair (finite and
    normalized, $(\pm\infty, 0)$ or NaN); `r` a radius that may also be $+\infty$ or NaN; `b1`
    and `b2` a ball, its center of one or two limbs and its radius together, which the oracle
    enumerates as one operand: every finite center with every finite radius $\ge 0$, the whole
    line and the empty set. Every enumeration includes the non-finite values of each operand
    (`oracle/README.md`, "gen"), and every format has the shape the statements of the IEEE model
    are proved for, $q_{\min} + q_{\max} = 3 - 2p$, which `binary64` and `binary32` have: one
    fits the budget for every kernel. At these sizes a format of that shape has few exponents
    (two to twelve, and forty for the one limb of `make_2`), so overflow is common, which is what
    the layer is about.

    | Inputs | Kernels | Toy format | $q_{\min} + q_{\max} = 3 - 2p$ | Cases |
    |---|---|---|---|---|
    | `1` | `make_2` | `fp:11:-29:10` | yes | 83 970 |
    | `2` | `neg_2`, `abs_2`, the conversions, `make_2_limbs` | `fp:6:-10:1` | yes | 89 730 |
    | `r r` | `radd`, `rmul` | `fp:6:-10:1` | yes | 174 724 |
    | `1 1` | `ball_make_1` | `fp:5:-7:0` | yes | 84 100 |
    | `2 1`, `1 2` | `add_2_1_full`, `sub_2_1_full`, `sub_1_2_full`, `mul_2_1_full`, the comparisons, `ball_make_2` | `fp:4:-5:0` | yes | 113 316 |
    | `2 c` | `mul_pow2_2_full` | `fp:5:-7:0` | yes | 84 888 |
    | `2 2` | `add_2_2_full`, `add_fast_2_2_full`, `sub_2_2_full`, the comparisons | `fp:3:-4:1` | yes | 181 476 |
    | `2 2` | `mul_2_2_full` | `fp:4:-4:-1` | yes | 62 500 |
    | `b1` | `ball_neg_1` | `fp:5:-9:2` | yes | 86 322 |
    | `b2` | `ball_neg_2` | `fp:4:-6:1` | yes | 198 074 |
    | `b1 b1` | `ball_add_1_full`, `ball_sub_1_full`, `ball_mul_1_full` | `fp:2:-3:2` | yes | 144 400 |
    | `b1 1` | `ball_scale_1_full` | `fp:3:-4:1` | yes | 89 436 |
    | `b2 1` | `ball_scale_2_full` | `fp:3:-3:0` | yes | 100 044 |
    | `b2 b2` | `ball_add_2_full`, `ball_sub_2_full` | `fp:3:-2:-1` | yes | 122 500 |

- **Restricted enumerations.** The two-limb balls with two operands have far too many operand
  combinations at their minimum precision (140 million for `ball_add_2` at `fp:3:-3:2`, 12.4
  billion for `ball_mul_2` at `fp:4:-5:1`, 97.6 million for `ball_mul_2_full` at `fp:4:-4:-1`).
  Their `interp-restricted` test enumerates every operand of a domain restricted by the oracle's
  `--restrict`, and says so in its report ("complete over a RESTRICTED domain"); their
  `interp-sampled` test runs 20 000 random cases of the whole format from every stratum of the
  ball family. A restriction shrinks the finite part of a domain only: the whole line and the
  empty set are always enumerated, and for `ball_mul_2_full` the zero ball too, since `cy` is
  not restricted.

    | Kernels | Toy format | Restricted to | Cases |
    |---|---|---|---|
    | `ball_add_2`, `ball_sub_2` | `fp:3:-3:2` | both radii in {0, 1/8, 1/2, 5/2}, `cx` in [1/2, 2) | 148 896 |
    | `ball_mul_2` | `fp:4:-5:1` | both radii in {0, η, 3/2}, `cx` in [1, 2), `cy` in [1/8, 2) | 64 728 |
    | `ball_mul_2_full` | `fp:4:-4:-1` (of the shape above) | both finite radii in {0, η, 1/2, 3/2}, a finite `cx` in [1, 2) | 120 780 |

- **Non-finite results.** A claim of the finite domain says nothing about a case whose leading
  output limb is not finite, so the oracle does not judge such a case; a runner that returned NaN
  for everything would pass. The cross-checks therefore pass `--fail-on-suspicious`, which fails
  a non-finite result whose operands and exact value are all far below the overflow threshold.
  A kernel of the extended domain (the non-finite layer) is judged on every line, non-finite
  results included, and the same option fails its non-finite results on such operands where its
  claims leave them open (`oracle/README.md`, "The extended domain"). The exceptions, for every
  runner, are `split` and `two_prod_dekker`, whose multiplication by the splitter overflows for
  such operands, as their requirement of no intermediate overflow allows; for them the guards
  below stand guard.

## What a pass requires

Beyond the oracle's verdict (no claim violated, no invalid case, no line dropped or added), a
cross-check passes only if the run checked what it set out to check. `tests/crosscheck_guards.py`
decides that from the oracle's summary (`check --json`):

- **The stream is the one asked for**: one generator header, for this kernel, format and mode (and
  seed), and every index of it seen.
- **An enumeration is what it claims**: it covers every index of its enumeration, over every
  operand when no restriction is given and over exactly the restricted domain asked for
  otherwise.
- **A random run has every stratum its generator promised**: a case of every stratum the oracle's
  generator lists in its header for the kernel, and of no other; and that list includes the
  strata every family has (`uniform`, `underflow`, `overflow`, `zero`, `pow2`, `extreme`).
- **Every claim was put to the test**: at least one case was judged; every `ensures` entry applied
  to at least one judged case (an `error` entry with a `when` condition, for instance); a
  comparison saw both outcomes; a rounding to nearest saw an inexact case; a rounding down or up
  saw a case where it differs from the rounding to nearest.

For a kernel of the extended domain the run must also have seen what that layer is about. The
guards read the kernel's claims (the file the oracle's summary names) and the oracle's counts of
the classes of each statement (`oracle/README.md`, "The extended domain"):

- **The strata of the layer**: a random run's header lists, besides those of the kernel's
  family, the strata the oracle's generator adds for it: `nonfinite` for every kernel, `zeroinf`
  where the value or the set has a product, `edge` for `extends`, `threshold` where
  `finite_when` is not empty, `ballstates`, `zerowhole` and `hugeradius` for `encloses`,
  `badradius` for `makes_ball`; and, as for every stratum, a case of each.
- **Every class of every statement**, counted by the oracle for each entry of the kernel's own
  claims:

    | Kind | Kernels | Cases the run must have seen |
    |---|---|---|
    | `extends` | the nine full kernels | a finite result (F2), an overflow on finite operands (F4), a non-finite operand (F5); where `finite_when` is not empty, a case where every condition holds (F3 applies) |
    | `encloses` | the eight full Ball kernels, `ball_neg_1`, `ball_neg_2` | each of the three results: a finite ball, the whole line, the empty set (and B4 applying, once a `finite_when` is claimed) |
    | `represents` | `make_2`, `make_2_limbs`, `neg_2`, `abs_2` | a finite, an infinite and a NaN value |
    | `makes_ball` | `ball_make_1`, `ball_make_2` | each given state: a finite ball, the whole line (a center that is not finite or a radius $+\infty$), the empty set (a radius that is NaN or negative) |
    | `normalized`, `error` | `neg_2`, `abs_2`, `ball_neg_2` | a non-finite operand |
    | `rounded` | the conversions | a non-finite operand |
    | `predicate` | the comparisons | a non-finite operand with each outcome |
    | `upper` | `radd`, `rmul` | a NaN (a NaN operand, or $0 \cdot \infty$) and $+\infty$ from a non-finite operand |

    The guards of the finite domain apply to these kernels as before, to their finite cases and
    to the entries of the core that F2 applies. The oracle does not count the corner where a zero
    ball meets the whole line ($0 \cdot \infty$ in a radius, which must give the whole line, not
    the empty set) separately, so no guard asks for it: the complete enumerations contain it, as
    does the restricted one of `ball_mul_2_full`, and a random run has the `zerowhole` stratum.

`crosscheck.guards` runs pipelines that the oracle passes but these guards must fail (a partial
enumeration, a restricted one passed off as complete, missing strata, nothing judged, a comparison
that was never true; in the extended domain, an enumeration of `add_2_2_full` without an overflow
or where `finite_when` never holds, one of `ball_add_1_full` whose radius makes every result from
finite operands the whole line, random runs without non-finite operands, without the empty set or
without one of a constructor's outcomes, headers without the strata of the layer), and summaries
altered where no stream can produce the fault (entries that are not those of the claims, claims
that cannot be read).

## Packed kernels

`gen/tests/packed_runner.cpp` runs the packed kernels of `kairn/gen/neon.hpp` (two doubles or four
floats per register) or `kairn/gen/avx2.hpp` (four or eight), whichever the target has:
consecutive requests for one kernel and format are evaluated together, one per lane. The oracle
judges its output like the scalar runner's, on the same cases, under the same contraction
settings.

The backend and its option are chosen as `kairn::fma`'s option is: NEON if the backend's header
compiles with the build's flags (AArch64), otherwise AVX2 with nothing added if the flags already
enable it, or with `-mavx2 -mfma` (GCC, Clang) or `/arch:AVX2` (MSVC, clang-cl), each tried by
compiling the header. On a target with neither, no packed runner is built, and configuring says
so. On x86-64 the CPU that runs the tests needs AVX2 as well as FMA.

## Contraction

A compiler may fuse a product and an addition into one FMA ("contraction"), which changes the
result. In Phase 0 that broke the textbook double-word product under some settings
([Environment](design/phase0/environment.md#contraction)); the generator's rules R1 and R2 are
meant to make every kernel immune. The contraction tests check that the compiled kernels, scalar
and packed, still satisfy their claims under each setting that matters to the compiler:

| Compiler | Settings, as added to the build's flags |
|---|---|
| GCC, Clang, Apple clang | `-ffp-contract=off`, `-ffp-contract=on`, `-ffp-contract=fast` |
| MSVC | `/fp:precise`, `/fp:contract`, `/fp:strict` |
| clang-cl | `/fp:strict` (off), `/fp:precise` and `/fp:contract` (on), `/clang:-ffp-contract=fast` |

Compilers contract only when they optimize, which is why a build of Kairn on its own defaults to
`Release`. These tests can tell: a copy of `mul_2_2` with the textbook product `p = a * b` in place
of the generated `fma(a, b, 0)`, compiled by Apple clang 21 at `-O2`, passes with
`-ffp-contract=off` and `on` and fails 14 148 of 20 000 binary64 cases with `=fast` (1 429 of the
first 2 000). At `-O3`, which is what `Release` gives GCC and Clang and so what the cross-checks
are built with, the same compiler leaves the copy as it is under every setting, and it passes.

## Hardware FMA

The kernels assume that an FMA is one rounding done by the hardware, and on x86-64 the headers
refuse to compile without it. The tests' runners link `kairn::fma`, which adds `-mfma` (GCC and
Clang) or `/arch:AVX2` (MSVC and clang-cl) when the build's flags do not already enable FMA; see
[Getting started](../getting-started/index.md#hardware-fma).

## Time

Each time below is the wall time of one ctest run after the build, with `--parallel 4` unless
noted: `ctest --test-dir build --output-on-failure --parallel 4` for the quick tier, and the same
with `build/tests/full` for the full tier, measured when the full tier was introduced. The Mac is
an Apple M3 Max (16 cores) with Apple clang 21, on which other jobs were running (load average 8 to
26); the Linux machine a 2019 x86-64 server (AMD EPYC 7452) with GCC 13 and Clang 18, each run
pinned with `taskset` to 16 of its hardware threads, or to 4 to stand for a hosted runner; the
Windows machine an Intel i5-13500T with MSVC, each run held to 8 of its logical processors, or to
4 (`SetProcessAffinityMask`). The times of the one tier are those of the commits just before.

| Where | Quick tier | Full tier | The one tier before |
|---|---|---|---|
| Mac | 44 to 47 s | 292 s | 213 to 218 s (`--parallel 6`) |
| Linux, 16 threads, GCC 13 | 70 to 75 s | 452 s | 545 s |
| Linux, 16 threads, Clang 18 | 71 to 75 s | 454 s | 545 s |
| Linux, 4 threads, GCC 13 | 67 s | 88 s for the tests that depend on the compiler, 281 s for those in exact arithmetic, 147 s for the generator's | 948 s |
| Linux, 4 threads, Clang 18 | 69 s | 87 s for the tests that depend on the compiler | |
| Windows, 8 logical processors | 85 to 113 s | 456 s | 818 s |
| Windows, 4 logical processors | 138 s | 181 s for the tests that depend on the compiler | |

Without `--parallel`, as the three commands of [Getting started](../getting-started/index.md)
stand, the quick tier took 166 seconds on the Mac and 287 on 16 threads of the Linux machine.

On 16 threads of the Linux machine, the quick tier's 278 seconds of test time are: the compiled
runners' cross-checks 105 (126 tests), the oracle's own tests 54, the public interface against
the oracle 51 (96 tests), the guards' tests 32, the generator's own tests 17, the reference
script's tests 9, and 11 for the 50 others. The oracle's tests are the longest single test, and
set a floor of about a minute to the wall time there. In the full tier, the pools of four workers
of the generator's and the oracle's longest tests are counted by ctest (`PROCESSORS`), so with
`--parallel 4` each runs alone; a larger `--parallel` shortens the full tier on a machine with
more cores.

**The hosted runners** of the CI have four cores, three on macOS. Estimated as four times the time
on 4 threads of the Linux machine, a cautious rule: the quick tier about 4.5 minutes on Linux,
the full tier's job of the compiled runners about 6 minutes after its build, its two jobs in
exact arithmetic about 11 minutes for the interpreter's enumerations (161 seconds of the 281
above, after the oracle's 120) and 8 for the oracle's; on Windows, four times the time on 4
logical processors, 9 minutes for the quick tier and 12 for the compiled runners. The one tier
suggests the rule is cautious indeed: it took 1 040 seconds with GCC on a hosted Linux runner
against 948 on 4 threads of the Linux machine, a ratio of 1.1, which would make the quick tier
about 75 seconds there and the compiled runners' job about 100; and 1 011 seconds on a hosted
macOS runner against 213 to 218 on the Mac, a ratio of 4.6, which would make the quick tier about
3.5 minutes there.

**Waste removed** before anything left the quick tier, as measured on 16 threads of the Linux
machine with GCC 13:

- *The same requests, generated and judged again for every runner.* Each kernel and format had
  one test per compiled runner (8 on each platform but clang-cl, which has 10), each generating
  the same 20 000 requests and judging its own output: 1 008 tests, 20.2 million cases generated
  and judged, 957 seconds of test time. Now one test per kernel and format generates the requests
  once and has every runner complete them; the outputs were the same, byte for byte (but for four
  kernels with MSVC, [above](#cross-checks)), so the oracle judges one per test: on the same 20 000
  cases, 126 tests, 2.5 million cases, 251 seconds (`full.crosscheck.compiled`).
- *The same requests, generated and judged again for every form of the public interface.*
  `api.oracle` had a pipeline per form, per runner and per format: 744 pipelines of 10 000 cases
  (186 forms of 48 kernels), each generating and judging its own requests, 451 seconds. Now each
  test generates its requests once, both runners complete them with every form, and the oracle
  judges each distinct output, one per test but a few: on the same 10 000 cases,
  122 seconds (`full.api.oracle`).
- *Runner outputs written line by line to a file.* On the Windows machine, a file as the scalar
  runner's standard output, or cmake's `OUTPUT_FILE`, cost 0.09 to 0.1 seconds per run on 2 000
  requests against 0.02 through a pipe; `tests/run_runners.py` reads the outputs through pipes,
  which brought a test of the full tier's compiled runners there from 6.2 to 1.9 seconds.
- *Python processes.* The two groups above started about 4 500 Python processes per run; now 794
  in the quick tier (four per test of the compiled runners, three per test of the public
  interface, and the second output of `mul_pow2_2`).
- *Suites that used every core beside three other tests.* The generator's tests and the oracle's
  started one worker process per processor while ctest ran three more tests beside them: on a
  hosted runner, four workers and three other tests on four cores. The parts with a pool are now
  in the full tier, with four workers that ctest counts.
- *Work repeated across the CI.* The generator's tests without C++ ran in each of the five jobs
  of `build.yml` and again, inside the whole suite, in each of the three of `generator.yml`; the
  interpreter's 67 enumerations, which are Python alone in exact arithmetic, ran in each of the
  five. Now the generator's longest tests run once per operating system and the enumerations
  once.

**What left the quick tier**, and what that costs. The interpreter's enumerations of toy formats,
the generator's four longest test classes and the oracle's six enumerations left whole; the
cross-checks of the compiled runners keep 6 000 of their 20 000 cases and the public interface
2 000 of its 10 000. To see what the smaller samples still catch, every applicable one-statement
change of each kernel's generated scalar code was planted in turn (`tests/kernel_mutants.py`,
about 20 minutes on the Mac: an operator turned, an operand dropped, an FMA made a product or
given a zero addend, a comparison loosened, a constant shortened, a selection swapped: 1 052
changes of the 63 kernels, in their `double` and `float` code alike), built into three scalar
runners (the build's flags, `-ffp-contract=off` and `=fast`, at `-O3`) and the public
interface's runner, and put through the cross-checks and the public interface's tests of its
kernel with each tier's samples. The full tier caught 863; the quick tier 861 of them, and nothing
the full tier missed. The two it misses fail on one or two cases of the full tier's 20 000, the
first at case 8 908 and 9 280: `ball_scale_2` with one FMA computed as a product and a sum (only
the `-ffp-contract=off` runner shows it), and `add_fast_2_2_full` with its finiteness test
`inf > a` loosened to `inf >= a`. The samples were chosen by this experiment: with 2 000 cases
for the compiled runners two more went unseen, and with 1 000 for the public interface three
more. Neither tier catches 189 changes, 135 of them FMAs computed as a product and a sum. The
oracle's own mutants (`oracle/selftest/mutants.py`, 65 of them) are all caught by the quick
tier's part of its selftest but one, `exhaustive: -inf left out of a one-limb domain`, which only
an enumeration can see and the full tier catches.

The stopgap of the one tier, a timeout of 1 800 seconds for the generator's and the oracle's tests
and of 60 minutes for the jobs of `build.yml`, is gone: their timeouts are 600 seconds and 30
minutes again.

## The generator's tier

`python3 gen/kairn-gen test` is the generator's own suite (`gen/README.md`, "The tests"). About
two thirds of its time goes to its C++ tests, which build the generated code at `-O0` and
`-O2`, with and without `-frounding-math`, under every contraction setting, and with both forms of
the scalar fix-ups (inline, and a function of its own: `KAIRN_GEN_FIXUP_CALL`), and require every
build, scalar and packed, to be bit-identical to the interpreter, with special operands in every
lane. The cross-checks build each compiler's own form only. ctest runs it without them (`--no-cxx`): with them it took 148 seconds on its own on the
Linux machine of [Time](#time), and the cross-checks already compile the same code with the build's
compiler and flags. Of the rest, four test classes take about 95% of the time; the quick tier
leaves them out (`--skip`) and the full tier runs them alone (`-k`, `full.kairn-gen.test`). The
whole suite runs in the workflow `generator.yml`, once per GCC-style compiler of the CI and once
without C++ on Windows, and by hand:

```sh
python3 gen/kairn-gen test                  # c++ and g++-16, those that exist
python3 gen/kairn-gen test --cxx clang++    # another compiler
python3 gen/kairn-gen test --full           # a few hundred thousand cases per kernel
python3 gen/kairn-gen test --no-cxx --skip test_statements.   # without C++, without a module
```

## A cross-check by hand

From the repository root, a toy format with the interpreter, and binary64 with a compiled runner
from a build tree:

```sh
python3 oracle/kairn-oracle gen mul_2_2 fp:4:-7:-3 --exhaustive \
  | python3 gen/kairn-gen interp | python3 oracle/kairn-oracle check

python3 oracle/kairn-oracle gen mul_2_2 binary64 --seed 0 --count 20000 \
  | build/tests/kairn-gen-runner | python3 oracle/kairn-oracle check --fail-on-suspicious
```

The packed runner is `build/tests/kairn-gen-packed-runner`, and a restricted enumeration adds
`--restrict` to `gen`, as the test's report shows:

```sh
python3 oracle/kairn-oracle gen ball_mul_2 fp:4:-5:1 --exhaustive \
  --restrict rx.in=0x0p+0/0x1p-5/0x1.8p+0 --restrict ry.in=0x0p+0/0x1p-5/0x1.8p+0 \
  --restrict cx.lead=0:0 --restrict cy.lead=-3:0 \
  | python3 gen/kairn-gen interp | python3 oracle/kairn-oracle check
```

`check` exits with 1 on any violated claim, invalid case or broken stream, and its report lists
the worst cases with their tags. `--verbose` adds the profile of the error by distance from the
underflow range; `--json FILE` writes everything, which `tests/crosscheck_guards.py` reads. A toy
format below a kernel's minimum precision is not judged unless `check` is given
`--ignore-min-precision`.

## Rerunning one case

Every request line carries a tag, copied by the runner, that says which case it is:
`#STRATUM:INDEX` for random cases and `#exhaustive:INDEX` for an enumeration. Case INDEX is
computed from the kernel, format, seed and index alone, so `--start INDEX --count 1` with the same
arguments regenerates it and nothing else. For the line

```
add_2_2 binary64 0x1.0000082p-333 -0x1p-387 0x1.ffffffffffffep+1023 0x1p+970 #extreme:462 -> ...
```

of a test run with seed 0:

```sh
python3 oracle/kairn-oracle gen add_2_2 binary64 --seed 0 --start 462 --count 1 \
  | build/tests/kairn-gen-runner | python3 oracle/kairn-oracle check --fail-on-suspicious
```

and for an exhaustive case, `--exhaustive --start INDEX --count 1` (with the same restrictions,
if any). A failing cross-check prints this command with its own runner and arguments filled in.
The request line alone is also a valid input: `echo 'add_2_2 binary64 ... #extreme:462' |
build/tests/kairn-gen-runner` shows the result without the oracle, and `python3 gen/kairn-gen
interp` the exact one. The packed runner evaluates a lone line in every lane.

## Continuous integration

Five workflows under `.github/workflows/`, each on pushes to `main` and on pull requests, one run
per branch at a time (a new push cancels the run in progress); their jobs all start at once:

| Workflow | Jobs |
|---|---|
| `build.yml`, "Build and test" | The quick tier: configure, build and `ctest` with Ninja, `Release` and warnings as errors, on Linux x86-64 with GCC and with Clang (packed: AVX2), macOS arm64 with Apple clang (NEON), and Windows x64 with MSVC and with clang-cl (AVX2) |
| `full.yml`, "Full tier" | The full tier's tests that depend on the compiler (`ctest --test-dir build/tests/full` with `-LE` of the labels `python` and `generator`: the compiled runners' cross-checks and the public interface on more cases), on the same five platforms and compilers, configured and built as in `build.yml`; and those in exact arithmetic (`-L python`), once, on Linux, configured but not built, in two jobs: the interpreter's enumerations (`-L interp`) and the oracle's (`-L python -LE interp`) |
| `generator.yml`, "Generator's full suite" | `python gen/kairn-gen test --cxx CXX`, C++ included, on Linux x86-64 with GCC and with Clang, and macOS arm64 with Apple clang; and `--no-cxx` on Windows x64. It contains the full tier's `full.kairn-gen.test` (label `generator`), which `full.yml` leaves out |
| `proofs.yml`, "Proofs" | `make -C proofs` in the Rocq team's image `rocq/rocq-prover:9.0` (Rocq 9.0.1), with Flocq 4.2.2 from opam, cached between runs |
| `checks.yml`, "Generated files and documentation" | `gen/kairn-gen check`, `docs/tools/reference.py --check` and its tests, `mkdocs build --strict`, `docs/tools/check_links.py`; the built site is kept as the run's artifact `site` |

Every test of the full tier thus runs on every push and pull request: a test that depends on the
compiler with every compiler, a test in exact arithmetic once, and the generator's tests, which
compare the interpreter with the machine's arithmetic (Python's float and `math.fma`), once on each
operating system and processor of the CI (x86-64 Linux, arm64 macOS, x86-64 Windows).
