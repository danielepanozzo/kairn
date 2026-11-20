# Testing

How Kairn's code is tested, what each test is for, and how to rerun one case of a failing test
by hand. The parts named here (generator, interpreter, oracle, runner, claims) are described in
[Architecture](architecture.md#the-pipeline).

## The tiers

| Tier | What | Where it runs | Time |
|---|---|---|---|
| Quick | `ctest --test-dir build`: the library, with the build's compiler and flags: every kernel through every compiled runner on a small sample, every public operation on a small sample, the stored regression cases, the checks of a debug build, the object code of every kernel in five configurations of the compiler's flag matrix ([below](#object-code)), the examples, the negative controls, the consumer checks, and that the generated files and the reference pages are fresh ([below](#the-quick-tier)) | every push and pull request, on every platform of the CI (`build.yml`); and by anyone, with the three commands of [Getting started](../getting-started/index.md#configure-build-and-test) | 31 to 54 seconds on the Mac and the Linux machine and 63 to 71 on the Windows machine with `--parallel 4`; on the hosted Windows runners an estimated 108 to 116 seconds, elsewhere under a minute ([Time](#the-tools-tests-leave-the-quick-tier)) |
| Full | `ctest --test-dir build/tests/full`: everything that left the quick tier, named `full.*`: the same cross-checks on more cases, every public operation built with each [flag set](#flag-sets) of a client, the kernels built at `-O0` and `-O1` (`/Od`, `/O1`), the object code on the compiler's whole flag matrix, the interpreter's enumerations of toy formats, and the tools' own tests: the generator's, the oracle's, and those of the cross-checks' guards, of the script of the reference pages and of the brute-force driver ([below](#the-full-tier)) | every push and pull request, in jobs beside the quick tier's (`full.yml`, and `generator.yml` for the generator's part); and by hand | five to eleven minutes with `--parallel 4` |
| Generator | `python3 gen/kairn-gen test`: the generator's whole suite, C++ included | every push and pull request, with each GCC-style compiler of the CI, and without its C++ tests on Windows | a few minutes per compiler |
| Proofs | `make -C proofs`: every Rocq proof, then the axiom audit | every push and pull request | a minute or two, with four cores |
| Brute force | `tests/brute/brute.py`: the cross-checks of the compiled runners on millions of random cases per kernel, format and machine (every runner of a machine on the same cases, both forms of the scalar fix-ups), and the interpreter on every operand of larger toy formats, with the same guards and a time budget | by hand, on the test machines, never in CI (`tests/brute/README.md`); results in [Brute force, Milestone 1](results/brute-milestone1.md) | for the final code of Milestone 1, 3.5 hours on the Linux machine and 3 hours each on the Mac and the Windows machine |

ctest runs the quick tier in the build directory and the full tier in `tests/full` of it, and says
which before the first test and after the summary (with Apple clang: `Kairn tests: the quick
tier, 290 tests. The full tier, 409 tests more: ctest --test-dir .../tests/full`); every test of
the quick tier also has the label `quick`, and every test of the full tier the label `full`. Both
are registered by the same configuration: the file `CTestCustom.cmake` that configuring writes at
the top of the build tree leaves the full tier out of a run there (`CTEST_CUSTOM_TESTS_IGNORE`),
so that `ctest -R` in the build directory never selects a `full.*` test, and a run in
`build/tests` runs both. The full tier is registered only when Kairn is the top-level project and
Python 3 is found: a project that adds Kairn with `KAIRN_BUILD_TESTS` on gets the quick tier, the
tests of the library with that project's compiler and flags, among its own tests (without the
messages, which are written into the top of Kairn's own build tree only).

A kernel's claims are only as good as the tests that could have refuted them, so every cross-check
fails when it checked nothing, or less than it says: when the oracle judged no case, when an
enumeration did not cover the domain it names, when a random run missed a stratum, or when a claim
was never put to the test ([below](#what-a-pass-requires)).

## The quick tier

The tests that `ctest` runs in the build directory, by name:

| Test | Checks |
|---|---|
| `kairn-gen.check` | Every committed generated file is what `python3 gen/kairn-gen build` writes. |
| `kairn-oracle.claims` | The oracle can read every claim in `gen/claims.json`. |
| `docs.reference.check` | The reference pages of the site are what `docs/tools/reference.py` writes ([Documentation](documentation.md#reference-pages)). |
| `crosscheck.compiled.K.F` | Kernel K compiled with the build's compiler and flags, scalar (`gen/tests/runner.cpp`) and packed (`gen/tests/packed_runner.cpp`, the backend of the target, [below](#packed-kernels)), once as the flags stand and once with each contraction setting added to them ([below](#contraction)): each of these runners on the same 6 000 random cases of format F (`binary64`, `binary32`) from every stratum. |
| `objcode.check` | Every kernel compiled with the build's compiler in five configurations of its flag matrix, scalar and packed, for `double` and `float`: the fused multiply-adds and the plain multiplications of its object code are what `gen/objcode.json` says the IR asks for ([below](#object-code)). |
| `objcode.controls` | The textbook `a * b + c` fails that check in exactly the configurations where its program sees the compiler fuse it, and in at least one; counts changed on purpose fail it. |
| `objcode.test` | The checker's own tests, on stored disassemblies of every format it reads (Python only). |
| `regression.cases` | The stored cases of `tests/regression/cases.txt` (the cases that found a problem, and those that came closest to a claim, [below](#the-regression-cases)) through every compiled runner of the build, the generator's interpreter, and both runners of the public interface with every form of each public kernel, judged by the oracle (`tests/regression/run.py`). |
| `consume.*` | A CMake project that uses Kairn through `add_subdirectory`, and one through `find_package` after `cmake --install`, build and run a kernel. |

The tools' own tests, which test the generator, the oracle and the other tools rather than the
library, were in the quick tier until they set its time on the hosted runners ([Time](#time)):
they are in the full tier, each under its name there with `full.tools.` in front
([below](#the-full-tier)).

The tests of the public interface (`tests/api/`, label `api`):

| Test | Checks |
|---|---|
| `api.oracle.K.F` | Every public operation that calls kernel K, computed through the constructors, operators and functions of `kairn/kairn.hpp` (`tests/api/runner.cpp`, a runner of the line protocol), on 2 000 random cases of format F, judged by the oracle against K's claims; by two runners on the same cases, one built with the build's flags and one with contraction forced on. For a kernel of the extended domain the cases include infinite and NaN operands and empty and whole balls, built through the public constructors. Each form of the operation (`x + a` and `a + x`, `x += a`, `x + y` with a one-limb `y`, the marked and the unmarked operator, `kairn::finite::add`) is judged on its own. A few forms can compute only some lines of their kernel (`ldexp` needs a power of two among the operands of `mul_1_1`, a point form a ball of radius 0, the steps of `ldexp` an operand that can be scaled exactly); they compute the plain operation on the others, and fail if a stream of 1000 lines or more reached their own operation on none, which is why the quick tier has at least 1 000 cases. |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is called by a public form of the runner, or is a building block, or is an entry kernel (`entry: yes` in `gen/kernels`) on the runner's short list of those not public yet, each with its reason (today the finite cores of the Ball operations); no entry kernel is a building block. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, infinities, NaN and the states of a ball included, comparisons with a NaN among them; the same results at run time; the properties of the types; and that an operation compiles without `kairn::unverified` exactly when the kernel it calls is proved. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass in the default environment and fail under each directed rounding mode and under flush-to-zero. |
| `api.flags.debug.self_test`, `api.flags.debug.constexpr` | `kairn::self_test()` and `kairn::environment_ok()`, compiled as the [debug build](#flag-sets), pass (`runner.cpp --self-test`); `tests/api/constexpr.cpp` built so, its constant expressions evaluated with the checks on. |
| `api.checks.debug.G`, `api.checks.release.G`, `api.checks.handler` | The [checks of a debug build](#the-checks-of-a-debug-build), in the debug build and with the build's own flags and `KAIRN_CHECKS` defined to 1: in the default environment every operation, and every constructor that checks its operands, runs (G = `default`); under each directed rounding mode (`rounding`) and each state of flush to zero (`flush`) `environment_ok()` is false and each of them stops the program with the environment's message; every operand that is not canonical, and every negative radius, stops it (`operands`); a `KAIRN_ENVIRONMENT_FAILURE` of the program's own is called instead, and every operation and constructor goes on, without the checks of its operands (`handler`). |
| `api.shadow` | A program whose global variables have the name of every parameter and local variable of the headers, calling every public operation, compiles with the compiler's strictest warnings about a declaration that hides another, as errors; without the headers' suppression of those warnings (MSVC's C4459 and C6244, GCC's `-Wshadow`) it must not compile with MSVC, and without the globals it must compile with every warning on ([The program's names](#the-programs-names)). |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break the kernels and define no macro (reassociation; `-ffp-model=fast`; with Apple clang on AArch64, `-fno-signed-zeros` with `-ffp-contract=fast`, which Clang 18 was measured not to break the kernels with): `kairn::self_test()` must fail. |
| `api.reject.*` | What must not compile, each with a control that compiles: the flags `config.hpp` rejects; each kind of operation and constructor written without the marker while its kernel is unverified (`unverified.*`, against a copy of the headers in which every kernel is); and an operation whose kernel alone is unverified, which must not compile through a conversion to another, proved kernel (`unverified_only.*`: `x + a` through `x + Expansion(a)`, a ball times a `T` through a point ball); with `KAIRN_CHECKS`, a constant expression given a pair that is not canonical (`from_limbs`, an operator) or a negative radius (`checks.*`). |
| `api.boundary.S`, `api.boundary.unguarded.S` | A product the program computes and passes in (`x + a * b`, `E2(a * b)`, `from_limbs`, `kairn::finite::add`, a ball's center, radius or point) gives the result of the same operation on the rounded product, bit for bit, under contraction setting S; built against a copy of the headers in which the generated guard is taken out of `gen/scalar.hpp` (made at configure time, which fails if it finds no guard), it must not where the compiler was measured to fuse across statements (`tests/api/boundary.cpp`). |
| `api.k1.zero_cost` | The instructions emitted for one operation and for loops over `Expansion<double, 1>` against the same code over `double` (`tests/api/k1/zero_cost.py`); with MSVC it also fails when one of these functions has a `/GS` stack cookie ([costs](results/costs-milestone1.md#3-msvc-and-the-gs-stack-cookie)). |
| `api.example.*` | The examples of the documentation (`docs/examples/cpp/`), which check their own output; `api.example.accurate_sums.*`, built under each contraction setting, also compares it with the text its tutorial shows ([Documentation](documentation.md#examples)). |

## The full tier

The tests that `ctest --test-dir build/tests/full` runs, by name, each named as the quick tier's
test it extends, with `full.` in front, or as the quick tier's test it was, with `full.tools.` in
front:

| Test | Checks |
|---|---|
| `full.crosscheck.compiled.K.F` | `crosscheck.compiled.K.F` on 20 000 cases instead of 6 000: the cases of the same seed from case 0, so that the quick tier's are the first 6 000 of these; with the kernels' runners, scalar and packed, of two [flag sets](#flag-sets) as well: the debug build (`-O0`, `/Od`) and one at `-O1` (`/O1`). |
| `full.api.oracle.K.F` | `api.oracle.K.F` on 10 000 cases instead of 2 000, the quick tier's among them, and by a third runner, the [debug build](#flag-sets)'s, with the checks, on the first form of K only. |
| `full.api.flags.oracle.K.F` | Every public form of kernel K through the runner of each [flag set](#flag-sets), the debug build's included, on the quick tier's 2 000 cases of format F. |
| `full.api.flags.S.self_test`, `full.api.flags.S.constexpr` | `api.flags.debug.*` for each other flag set S. |
| `full.objcode.check`, `full.objcode.controls` | `objcode.check` and `objcode.controls` in every configuration of the compiler's flag matrix: 24 for GCC, Clang and Apple clang and for clang-cl, 9 for MSVC. |
| `full.crosscheck.interp.K` | Kernel K run by the generator's interpreter on **every** operand combination of a toy format. |
| `full.crosscheck.interp-restricted.K` | Kernel K run by the interpreter on every operand of a **restricted** domain of a toy format, for the kernels whose whole enumeration is too long. |
| `full.crosscheck.interp-sampled.K` | The same kernels on 20 000 random cases of the whole toy format, from every stratum. |
| `full.kairn-gen.test` | The four test classes of the generator that `full.tools.kairn-gen.test` leaves out (`-k`): the interpreter against the machine's own arithmetic (Python's float and `math.fma`) on thousands of cases per kernel and format and against every rounding of toy formats, and the statements of the IEEE model and of the non-finite layer on every operand of small formats. With four worker processes. |
| `full.kairn-oracle.selftest` | The six tests of the oracle that `full.tools.kairn-oracle.selftest` leaves out (`--only`): its Python reference runner, correct and with injected errors, on every case of tiny formats. With four worker processes. |
| `full.search.compiled` | The adversarial search ([below](#the-adversarial-search)) on every kernel with an `error`, `upper`, `encloses` or `extends` entry, `binary64` and `binary32`, through the scalar runner with the build's flags, 5 000 cases per kernel and format from its seeds; fails on any violated claim. With four worker processes. |
| `full.tools.kairn-gen.test` | The generator's own tests, without those that compile C++ (`--no-cxx`, see [the generator's tier](#the-generators-tier)) and without the four test classes of `full.kairn-gen.test` (`--skip`). |
| `full.tools.kairn-oracle.selftest` | The oracle's own tests (`--quick`), including injected errors it must catch, without the six enumerations of toy formats of `full.kairn-oracle.selftest` (`--skip`). It compiles its own C++ reference runner with the build's compiler; if that fails, the test fails. |
| `full.tools.crosscheck.guards` | The cross-checks' guards fail the runs they are there to fail ([What a pass requires](#what-a-pass-requires), `tests/test_crosscheck_guards.py`). |
| `full.tools.docs.reference.test` | The tests of `docs/tools/reference.py`, the script of the reference pages ([Documentation](documentation.md#reference-pages)). |
| `full.tools.brute.driver.test` | The tests of the [brute-force](#the-tiers) driver `tests/brute/brute.py`: the plan of its enumerations, the forms of the fix-ups, `widen.py` on one small format (`tests/brute/test_brute.py`). |

The names of the parts that each of the generator's and the oracle's two tests leaves to the other
are in `tests/CMakeLists.txt` (`_gen_full`, `_oracle_full`), and both tools fail when a name they
are given matches no test, so that a test renamed cannot drop out of both. A label says what a
test of the full tier depends on, which is how the CI runs each where it must and no more
([Continuous integration](#continuous-integration)): `python`, on Python alone, in exact
arithmetic, the same everywhere (run once, on Linux); `generator`, on the machine's arithmetic as
well (run on every operating system, inside the generator's whole suite in `generator.yml`);
neither, on the compiler (run on every platform and compiler of the CI). The tools' own tests have
the label `tools`; but for the generator's, which is labelled `generator` too, they run with every
compiler, as they did in the quick tier.

Labels select groups in either tier: `-L crosscheck`, `-L compiled`, `-L interp` (with
`-L restricted` and `-L sampled` among them), `-L api` (with `-L oracle`, `-L reject` and
`-L boundary` among them), `-L objcode`, `-L python`, `-L generator`, `-L tools`; `-R` selects by
name, for example `ctest --test-dir build -R mul_2_2` for the quick tier's tests of `mul_2_2`.

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
    fits the budget for every kernel. The theorems also assume $q_{\max} \ge 1$, which some of
    these formats do not have (`fp:3:-2:-1`, for example): there the tests judge the statements
    where no theorem covers them
    ([which formats](design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)). At these sizes a format of that shape has few exponents
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
    | `encloses` | the eight full Ball kernels, `ball_neg_1`, `ball_neg_2` | each of the three results: a finite ball, the whole line, the empty set; where `finite_when` is not empty (the eight full Ball kernels), a case where every condition holds (B4 applies) |
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

`full.tools.crosscheck.guards` runs pipelines that the oracle passes but these guards must fail (a partial
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

Compilers contract across statements only when they optimize, which is why a build of Kairn on
its own defaults to `Release` (within one expression, Clang and GCC 16 under `-ffp-contract=on` fuse
at `-O0` too: [Object code](#object-code); the kernels have one operation per statement). These tests can tell: a copy of `mul_2_2` with the textbook product `p = a * b` in place
of the generated `fma(a, b, 0)`, compiled by Apple clang 21 at `-O2`, passes with
`-ffp-contract=off` and `on` and fails 14 148 of 20 000 binary64 cases with `=fast` (1 429 of the
first 2 000). At `-O3`, which is what `Release` gives GCC and Clang, the same compiler leaves
the copy as it is under every setting, and it passes. So with GCC and Clang the runners of a
contraction setting are built at `-O2` whatever the build's level, and the runner with the
build's flags keeps the build's level: both levels are tested.

## Object code

The tests above judge what the compiled kernels compute. This one reads what the compiler
emitted: rules R1 and R2 ([Architecture](architecture.md#the-kernel-ir)) write every product of a
kernel as an FMA, so that a compiler that contracts finds nothing to contract, and the check
verifies that in the object code of every kernel, on the flag matrix of each compiler of the CI.
It is criterion 4 of [When an operation is done](architecture.md#when-an-operation-is-done).

`tests/objcode/objcode.py` compiles `tests/objcode/unit.cpp`, which has one function per kernel and
limb type, externally visible and never inlined, that loads the operands, calls the kernel and
stores its results: scalar (`kairn/gen/scalar.hpp`) and packed (`avx2.hpp` on x86-64, `neon.hpp`
on AArch64). It disassembles the object file and counts, in each of these functions and in every
function of the object that it calls or jumps to, once per call site, two kinds of instructions:
fused multiply-adds (x86 `vfmadd`, `vfmsub`, `vfnmadd`, `vfnmsub` in all their forms; AArch64
`fmadd`, `fmsub`, `fnmadd`, `fnmsub`, `fmla`, `fmls`) and plain floating-point multiplications
(`mulsd`, `mulss`, `mulpd`, `mulps` and their `v` forms; `fmul`, `fnmul`, `fmulx`). A part of a
function that GCC moves to a section of its own (`F.cold`) is counted with the function. It
compares the two numbers with `gen/objcode.json`, which the generator writes from the IR the code
and the proofs are printed from (`gen/README.md`, "The counts of the object-code check"), for the
form the unit was compiled in: scalar with the fix-up inline, scalar with the fix-up a function of
its own, or packed.

### The rule

For each kernel, form and limb type:

- **Fused multiply-adds**: one per FMA node of the flattened IR (`fma`, `fms`, `fnma`, `prod`),
  with identical nodes of one function (the same operation on the same operands) each compiled or
  merged into one. The generator gives both numbers, `fma` and `fma_distinct`, and they differ in
  three kernels only: the fix-ups of `mul_2_1_full`, `mul_2_2_full` and `mul_pow2_2_full` compute
  the core's leading product again, `t = prod(x0, y0)`. A compiler that eliminates common
  subexpressions computes it once. Every compiler measured does so when it optimizes, in the
  inline form and in packed code, except MSVC under `/fp:strict` for the scalar code; none does
  without optimization; and in the form where the fix-up is a function of its own, which receives
  `x0` and `y0` as parameters, none can.
- **Plain multiplications**: one per product with $+\infty$ of a fix-up (`times_inf`, which R1
  allows: exact, and only compared or selected), in the nine full kernels that have one. In
  addition, in the scalar forms of `two_prod`, the seven products of Dekker's product, in the
  branch `if (__builtin_is_constant_evaluated())` that only constant evaluation takes, where a
  compiler emits that branch: MSVC at `/Od` compiles the test as that of a register which is always
  zero, and the branch after it. No execution reaches it.
- **Nothing else**: every kernel has its function and every function of the unit its counts; it
  calls nothing outside the object but the stack protector's routines and Windows' stack probe,
  which do no arithmetic (Ubuntu's GCC protects functions by default); there is no indirect call;
  and no kernel has a declared contractable multiply-add (`muladd`), for which the check has no
  rule yet.

So the static count does not always equal the number of FMA nodes, and a kernel does not always
have no plain multiplication: what holds is the rule above, which allows these two differences
and no other. On every compiler and flag set measured, no other kernel has a plain
multiplication, in scalar or in packed code: the scalings by a power of two (`mul_pow2_2`) and the
products by the constants of the radii are FMAs, and the constructors multiply nothing.

A failure says what was found, function by function. One fused instruction more, with one
multiplication fewer or none, is a contraction; a multiplication more and an FMA fewer is an FMA
computed as a product and a sum, or an opaque product folded back into a plain one (as
`-fno-signed-zeros` with contraction does with Apple clang); a call outside the object, to a
library's `fma` for example, is arithmetic that the check cannot see.

What it does not check: the order of the operations and what they compute (the cross-checks and
the generator's comparison with the interpreter do); instructions of other kinds; a kernel inlined
into a caller, which a compiler may optimize differently (the unit's functions are not inlined; R1
and R2 are what make that harmless for contraction,
[Environment](design/phase0/environment.md#the-self-test)); the public headers' operators, which
call these kernels; nvcc, Metal and AVX-512, which have no backend yet.

### The flag matrix

| Compiler | Full tier: every combination of | Quick tier |
|---|---|---|
| GCC, Clang, Apple clang | `-O0`, `-O1`, `-O2`, `-O3`; `-ffp-contract=off`, `on`, `fast`; without and with `-frounding-math`: 24 | `-O0 -ffp-contract=fast`; `-O2` with each contraction setting; `-O3 -ffp-contract=fast -frounding-math` |
| MSVC | `/Od`, `/O1`, `/O2`; `/fp:precise`, `/fp:contract`, `/fp:strict`: 9 | `/Od /fp:precise`; `/O2` with each setting |
| clang-cl | `/Od`, `/O1`, `/O2`; `/fp:strict`, `/fp:precise`, `/fp:contract`, `/clang:-ffp-contract=fast`; without and with `/clang:-frounding-math`: 24 | `/Od /fp:precise`; `/O2` with `/fp:strict`, `/fp:precise` and `/clang:-ffp-contract=fast`; `/O2 /fp:contract /clang:-frounding-math` |

Each configuration is compiled once with the compiler's own form of the scalar fix-ups and with
the packed kernels, and once more with the other form, scalar only; in the quick tier only the
configuration with contraction forced on at `/O2` or `-O2` has the second compilation. The options
come after those of `CMAKE_CXX_FLAGS` and `kairn::fma`'s, as in `api.k1.zero_cost`, and the packed
kernels get the backend's option (`-mavx2 -mfma`, `/arch:AVX2`). Each object file and its
disassembly stay in the test's work directory (`tests/objcode/` of the build tree).

The disassembler is found as follows, and the check fails without one and says where it looked:

| Compiler | Disassembler | Object files |
|---|---|---|
| GCC and Clang on Linux | `objdump` of GNU binutils, `-d -r` | ELF |
| Apple clang | `objdump` of the Xcode tools, which is LLVM's, `-d -r --show-all-symbols` | Mach-O |
| MSVC | `dumpbin /disasm` next to `cl.exe`, else on the PATH | COFF |
| clang-cl | `llvm-objdump` next to `clang-cl.exe`, else on the PATH | COFF |

The hosted runners have each one: binutils on the Ubuntu images, the Xcode tools on macOS, the
Visual Studio tools and LLVM on Windows. The checker's own tests (`objcode.test`) read stored
excerpts of each format (`tests/objcode/samples/`: GNU objdump for x86-64 and AArch64, LLVM objdump
for Mach-O and for COFF, dumpbin), so the reading of every format is tested on every platform.

### The controls

`objcode.controls` shows the check catching what it is for. `tests/objcode/fixture.cpp` computes
the textbook `a * b + c` in functions of its own: as two statements (`p = a * b; s = p + c`) and as
one expression, for `double` and `float`, and as two statements with the packed backend's
intrinsics. The check judges each against its source, one product and one sum, so it fails exactly
where the compiler fused it; the fixture's program, run on operands whose product is not a number
of the format, says independently where the compiler fused it. The test requires the two to agree
in every configuration of the tier, and at least one configuration to fuse. It also judges the
unit against counts changed on purpose (one FMA more for `mul_2_2`, one multiplication fewer for
`add_2_2_full`) and requires exactly those two kernels to fail.

Where each compiler fused the textbook product in the configurations of the full tier, measured on
2026-11-19; it fused nowhere else, and the check failed on exactly these:

| Compiler | Where it fused | Configurations |
|---|---|---|
| GCC 13, x86-64 and AArch64 | both forms with `-ffp-contract=fast` at `-O2` and `-O3`, also with `-frounding-math` (GCC 13 takes `on` as `off`) | 4 of 24 |
| GCC 16, AArch64 (the Mac) | the one expression with `-ffp-contract=on` at every level, `-O0` included; both forms with `fast` at `-O2` and `-O3` | 12 of 24 |
| Clang 18, x86-64 | the one expression with `on` at every level, `-O0` included; both forms with `fast` from `-O1`, but not with `-frounding-math` | 11 of 24 |
| Clang 18, AArch64; Apple clang 21 | the one expression with `on` at every level; both forms with `fast` from `-O1`, with `-frounding-math` too | 14 of 24 |
| MSVC 19.52, x64 | both forms with `/fp:contract` at `/O1` and `/O2` | 2 of 9 |

GCC 13 and Clang 18 on AArch64 were run as the cross compilers of Ubuntu 24.04 (the versions of the
hosted arm64 runner), with binutils' AArch64 `objdump` and the fixture's program under QEMU's user
mode (`--emulator`). clang-cl has not been run: the Windows machine has none.

### The kernels, as measured

On 2026-11-19 the full tier's check passed with GCC 13 and Clang 18 on x86-64 and on AArch64 (as
the cross compilers above), with Apple clang 21 and GCC 16 on the Mac, and with MSVC 19.52 on x64: every configuration of the
matrix, both forms of the fix-ups, 252 functions per compilation with the packed kernels and 126
without. The fused instructions were every FMA node without optimization, and with optimization
the identical ones merged, but for MSVC under `/fp:strict`, which merges them in packed code only;
the branch of constant evaluation appeared with MSVC at `/Od` only. At `-O2` and `-O3` GCC 13 on
x86-64 put the call of the fix-up function in a part of its own (`F.cold`), and without
optimization every compiler called helpers (`std::bit_cast`, `std::numeric_limits<T>::infinity()`, and with MSVC
`fma_rn` and the kernel itself), all counted through the calls. No kernel called a library's
`fma`: with `-mfma`, `/arch:AVX2` and on AArch64 the FMA is an instruction at every level, `-O0`
and `/Od` included.

The check takes seconds, on the machines of [Time](#time), with `--parallel 4`:

| Where | `objcode.check`, `objcode.controls` | The quick tier, in all | `full.objcode.check`, `full.objcode.controls` |
|---|---|---|---|
| Mac, Apple clang 21 | 1.2 s, 1.2 s | 50 s | 4.2 s, 4.4 s |
| Linux, 16 threads, GCC 13 | 4.3 s, 2.8 s | 78 s | 14.2 s, 4.9 s |
| Linux, 16 threads, Clang 18 | 4.2 s, 2.6 s | 76 s | 14.4 s, 4.9 s |
| Linux, 4 threads, GCC 13 | 4.3 s, 2.8 s | | 14.1 s, 5.0 s |
| Windows, 8 logical processors, MSVC | 2.0 s, 1.8 s | 88 s | 4.0 s, 1.7 s |

In these first runs ctest, which had no record of their times yet, started the two tests of the
quick tier near its end, so that they added up to their own length to it: the quick tier took 50,
78 and 76 seconds on the Mac and the Linux machine, against 44 to 47 and 70 to 75 before the check,
and 88 on the Windows machine, against 85 to 113. On a hosted runner, four times as slow by the
cautious rule of [Time](#time), the two would take about 17 and 11 seconds, and those of the full
tier about a minute and 20 seconds.

### By hand

```sh
python3 tests/objcode/objcode.py --cxx c++ --workdir objcode            # the quick tier's configurations
python3 tests/objcode/objcode.py --cxx g++ --flags=-mfma --packed-flags="-mavx2 -mfma" \
    --tier full --jobs 8 --workdir objcode                              # the whole matrix
python3 tests/objcode/objcode.py --cxx cl --flags=/arch:AVX2 --controls --workdir objcode
```

`--disassembler` names another disassembler, and `--emulator` the command that runs the controls'
program for a cross compiler.

## Flag sets

A program that includes Kairn compiles the public interface and the kernels with its own flags.
The runners above are built with the build's flags (`Release`: `-O3`, or `/O2`) and with each
contraction setting at `-O2`. The public interface and the kernels are also built with each flag
set below, the sets of a client (`tests/api/flags/`): each target gets exactly the options of its
set after `CMAKE_CXX_FLAGS`, since the flags of the build's configuration (`-O3 -DNDEBUG`,
`/O2 /Ob2 /DNDEBUG`) are emptied there; every set but the debug build defines `NDEBUG`, as a
release build does. A full cross product is not needed: the sets give every value of every flag,
and the combinations that Phase 0 found dangerous ([Environment](design/phase0/environment.md)):
forced contraction at each optimization level, since whether a compiler fuses depends on the
level (Apple clang 21 fuses the textbook product at `-O2` and not at `-O3`); `-frounding-math`,
which changes what a compiler may fold, with forced contraction and optimization; and, with MSVC,
`/Od` and `/fp:strict`, where `std::fma` is a library call and the kernels' FMA intrinsic must
still be one fused operation.

| Compiler | Set | Options | Why |
|---|---|---|---|
| every one | `debug` | CMake's `Debug` configuration: `-g` (GCC, Clang), `/Zi /Ob0 /Od /RTC1` and the debug C runtime (MSVC, clang-cl); no `NDEBUG`, so `KAIRN_CHECKS` is 1 | a client's debug build: no optimization, the compiler's default contraction (`fast` for GCC in GNU mode, `on` for Clang, `/fp:precise` for MSVC), and the [checks](#the-checks-of-a-debug-build) |
| GCC, Clang, Apple clang | `O0-contract-fast-rounding-math` | `-O0 -ffp-contract=fast -frounding-math` | no optimization, with the two other flags at their riskier values |
| | `O1-contract-off` | `-O1 -ffp-contract=off` | `-O1`, which no other test built, without contraction |
| | `O1-contract-fast` | `-O1 -ffp-contract=fast` | forced contraction at `-O1`; also the kernels |
| | `O2-contract-on-rounding-math` | `-O2 -ffp-contract=on -frounding-math` | contraction within expressions (Clang's default) with `-frounding-math` |
| | `O2-contract-fast-rounding-math` | `-O2 -ffp-contract=fast -frounding-math` | forced contraction and `-frounding-math` at the level where Apple clang fuses (the flag set of the generator's tests of constant evaluation) |
| | `O3-contract-off-rounding-math` | `-O3 -ffp-contract=off -frounding-math` | the level of `Release` without contraction, with `-frounding-math` |
| | `O3-contract-fast` | `-O3 -ffp-contract=fast` | forced contraction at the level of `Release` (Clang's runner with the build's flags contracts only within expressions) |
| MSVC | `Od-fp-contract` | `/Od /fp:contract` | contraction allowed, without optimization |
| | `Od-fp-strict` | `/Od /fp:strict` | the two settings where `std::fma` is a library call; `/fp:strict` is MSVC's `-frounding-math` |
| | `O1-fp-precise`, `O1-fp-contract`, `O1-fp-strict` | `/O1` and each `/fp:` setting | `/O1`, which no other test built; `O1-fp-contract` also the kernels |
| | `O2-fp-strict` | `/O2 /fp:strict` | the level of `Release` with `/fp:strict` |
| clang-cl | `Od-contract-fast` | `/Od /clang:-ffp-contract=fast` | forced contraction without optimization |
| | `Od-fp-strict` | `/Od /fp:strict` | `/fp:strict` is `-ffp-model=strict`: no contraction, and `-frounding-math` |
| | `O1-fp-precise` | `/O1 /fp:precise` | `/O1` (Clang's `-Os`), contraction within expressions |
| | `O1-contract-fast-rounding-math` | `/O1 /clang:-ffp-contract=fast /clang:-frounding-math` | forced contraction with `-frounding-math`; also the kernels |
| | `O2-fp-contract`, `O2-fp-strict` | `/O2` with `/fp:contract`, with `/fp:strict` | the level of `Release` with contraction within expressions, and with `/fp:strict` |

With the runners of the build's flags and of the contraction settings at `-O2` or `/O2`, every
optimization level meets every `/fp:` setting with MSVC, and forced contraction with every
compiler. For each set, `tests/api/flags/` builds the public interface's runner and
`tests/api/constexpr.cpp`, and for the debug build and the set marked "also the kernels" the
kernels' runners, scalar and packed. They are tested as follows:

| What | Quick tier | Full tier |
|---|---|---|
| The public interface against the oracle | | the debug build's runner, on the first form of each kernel, on 10 000 cases (`full.api.oracle.K.F`); every form, through the runner of every set, on the quick tier's 2 000 cases (`full.api.flags.oracle.K.F`) |
| `kairn::self_test()` and `environment_ok()`, compiled with the set's flags | `api.flags.debug.self_test` | `full.api.flags.S.self_test` |
| `constexpr.cpp`: its constant expressions, and the same at run time | `api.flags.debug.constexpr` | `full.api.flags.S.constexpr` |
| The kernels' runners, in the cross-checks | | the debug build and the `-O1` or `/O1` set, in `full.crosscheck.compiled.K.F` |
| The checks of `KAIRN_CHECKS` | `api.checks.*` ([below](#the-checks-of-a-debug-build)) | |

The quick tier has so little of it because a debug build's runners take two to three times as long
as optimized ones, most of it in the text of the line protocol: on the Mac, the debug build's
runner on every form added 21 seconds of test time to `api.oracle`, and its kernels' runners 35 to
the cross-checks, against about 5 for the first forms ([Time](#time)). The first forms were in the
quick tier's `api.oracle.K.F` too, until the hosted Windows runners showed that the quick tier
could not keep to two minutes there with them ([Time](#time)). The generator's own suite
builds the kernels at `-O0` too, with GCC and Clang only ([below](#the-generators-tier)): these
are the tests that build them at `/Od` with MSVC and clang-cl, and at `-O1` with any compiler.

## The checks of a debug build

`KAIRN_CHECKS` is 1 when `NDEBUG` is not defined (or when a program defines it to 1); what it then
does, as the headers are written (`config.hpp` says the same):

- Before every operation of `Expansion` and `Ball` (the arithmetic, `ldexp` and `half`, negation
  and `abs`, the comparisons, the conversions to `T` and the narrowing to one limb, and
  `kairn::finite::`), and in the constructors that check what they are given (`from_limbs`, and
  every constructor of `Ball` that is given a center, a radius or a `T`), first
  `kairn::environment_ok()`; if it fails, `KAIRN_ENVIRONMENT_FAILURE` with the reason, by default
  a message and `std::abort()`.
- Then the operands: an operation of two limbs requires canonical operands, a function of
  `kairn::finite::` normalized ones or a leading limb that is not finite (what a core returns), a
  `Ball` operation canonical balls, `from_limbs` a canonical pair, and a constructor of `Ball` a
  radius that is not negative and, for two limbs, a canonical center; if one is not, a message
  and `std::abort()`.
- If the environment is not the default one and a `KAIRN_ENVIRONMENT_FAILURE` of the program's
  own returns, the operation goes on without checking its operands: those checks compute in that
  environment, where the test of a canonical pair, $x_0 + x_1 = x_0$, can be false (for
  $(1.5, 2^{-60})$ under rounding upward). So a program stopped in a wrong environment is stopped
  with the environment's message, and a handler that returns lets every operation go on, with no
  guarantee for its result.
- In constant evaluation the environment is not checked, and an operand that fails a check makes
  the constant expression invalid.

`tests/api/checks.cpp` runs them, on the cases of `tests/api/checks_cases.hpp`, built as the
[debug build](#flag-sets) (`api.checks.debug.*`) and with the build's own flags and `KAIRN_CHECKS`
defined to 1 (`api.checks.release.*`, where an optimizer could move or drop a check), and
`tests/api/checks.cmake` judges each case from the program's exit status and output:

- `default`: in the default environment `environment_ok()` is true, and 29 operations run (a sum,
  a product, `ldexp` and a comparison of one limb; every kind above of two limbs, and a sum of
  `float` limbs; three of `kairn::finite::`; sums, products, scalings, negations and a point form
  of balls) and 8 calls of constructors (`from_limbs` twice; `Ball` of one limb from a center and
  a radius and from a `T`; of two limbs from a center and a radius twice, from a center and from a
  `T`), as do 13 operands the checks must let through: the
  canonical infinities and NaN, the empty set and the whole line, a NaN and a $-0$ radius, and
  what a finite core returns, given back to `kairn::finite::`.
- `rounding`: for each directed rounding mode and each of the 37 operations and constructors, a
  run of its own: `environment_ok()` is true, the mode is set and `environment_ok()` is false, and
  the operation must stop the program, with an exit status other than 0 (`SIGABRT`; exit status 3
  with Microsoft's C runtime), after the line in which the program says it calls it, and with
  Kairn's message on the standard error ("the rounding mode is not to nearest"), not one about an
  operand. The two-limb operands, $(1.5, 2^{-60})$ and $(2.25, -2^{-58})$, are canonical pairs
  whose test is false under rounding upward, and under rounding downward and toward zero; those of
  the operations are made before the mode is set, so that each operation is what meets it, and the
  constructors meet it in cases of their own.
- `flush`: the same with FTZ and with DAZ of MXCSR on x86-64, and FZ of FPCR on AArch64; on those
  targets a program that can set none fails the test.
- `operands`: 15 operands that are not canonical, each given to an operation, must stop the
  program with their message: pairs that are not canonical given to `from_limbs`, to an operator,
  a comparison, a conversion, `ldexp` and `kairn::finite::add`, what a finite core returns after
  an overflow given to an operator, negative radii ($-\infty$ among them), a center that is not
  canonical, and a ball that is not canonical, made by the internal constructor that takes a
  kernel's result as it is, the only way to make one.

`api.checks.handler` (`tests/api/checks_handler.cpp`) defines `KAIRN_ENVIRONMENT_FAILURE` as a
function that records the reason and returns. In the default environment it is not called; under
each state of `rounding` and `flush`, each of the 37 operations and constructors calls it with the
reason and goes on, and so does `x + y` with an `x` that is not canonical, which stops the
program in the default environment. `api.reject.checks.*` are the constant expressions, and
`api.oracle.K.F` judges the debug build's runner: the checks let every canonical case through and
change no result. On the lines of `ball_make_1` and `ball_make_2` whose radius is negative, about
40% of their cases, which the checks stop by design, the debug build's runner computes
`Ball::empty()`, the set the constructor makes of such a radius, and says on how many lines. The
test programs keep Microsoft's C runtime from opening a dialog on `abort()`, and Linux from
writing a core dump, which took 0.3 seconds per case on the Linux machine
(`tests/api/no_crash_reports.hpp`).

## The program's names

A program may have a global variable with the name of a parameter or a local variable of Kairn's
headers: `x`, `a`, `limbs`, `inf`, or any of the few hundred names of the generated kernels. MSVC
reports every such declaration of a header, at `/W4` (C4459, "declaration of 'x' hides global
declaration") and under `/analyze` (C6244), and a program built with `/WX` then fails to build.
Measured with MSVC 19.52, it reports every parameter and local variable of a function that is not
a template; and of a template, once instantiated, every local variable, and the parameters of the
members of a class template (constructors, `from_limbs`), but not those of a function template;
for a template, whether the program declares the global before or after it includes Kairn.
GCC's `-Wshadow` and Clang's `-Wshadow-all`, which `-Wall -Wextra` do not enable, report a
declaration that hides a variable of its own namespace or of an enclosing block, and not one of
the global namespace from inside `namespace kairn`, with one exception: GCC 11 and 13 report the
parameters of a constructor of a class template and of a lambda, once instantiated, as hiding a
global (21 declarations of Kairn's headers: the constructors of `Expansion` and `Ball`, and a
lambda of `traits.hpp`). GCC 16, Clang 18 and Apple clang 21 report none. Renaming cannot help:
any name of Kairn's can be the name of a program's global. Each header of Kairn, generated or
not, therefore turns these warnings off for its own declarations, between
`KAIRN_GEN_PUSH_WARNINGS` and `KAIRN_GEN_POP_WARNINGS`, defined in `gen/prelude.hpp`: a pushed
and popped `#pragma warning(disable : 4459 6244)` with MSVC, and
`#pragma GCC diagnostic ignored "-Wshadow"` with GCC; nothing with Clang, clang-cl included. Each
compiler applies the state of the header to the templates the program instantiates later.

`api.shadow` (`tests/api/shadow.py`) reads the name of every parameter and local variable of the
headers (283 today, by a scan of their tokens, which found every name of Clang's AST of the
headers), writes a global variable of each name, and compiles `tests/api/shadow.cpp`, which calls
every public operation once for `float` and for `double`, with the build's flags and the
strictest warnings of the compiler about a declaration that hides another, as errors, the front
end only: `/W4 /WX` with C4456 to C4459 at level 1, and again under `/analyze` (MSVC);
`-Wall -Wextra -Wpedantic -Wshadow -Werror` (GCC); `-Wall -Wextra -Wpedantic -Wshadow-all -Werror`
(Clang; `/W4 /WX -Wshadow-all` with clang-cl). With the globals, the program must compile, with
each form of the fix-ups (`KAIRN_GEN_FIXUP_CALL` 0 and 1). Without them, and with
`KAIRN_GEN_KEEP_SHADOW_WARNINGS`, which keeps the warnings on in the headers, it must compile too
(with MSVC, under `/analyze` as well): Kairn's own declarations hide nothing, so the warnings stay
as strong as they were for Kairn's own code. With both, which is what a program saw before the headers turned them off, MSVC must reject
it, with C4459, and with C6244 under `/analyze`; with GCC and Clang it is only reported, since
whether they reject it depends on their version (GCC 13 rejects it, GCC 16 and Clang accept it).
Kairn's other tests are built as a program is, with the warnings off in the headers, and with
their own `/W4 /WX` or `-Wall -Wextra -Wpedantic -Werror` unchanged.

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

On 16 threads of the Linux machine, the quick tier's 278 seconds of test time were then: the
compiled runners' cross-checks 105 (126 tests), the oracle's own tests 54, the public interface
against the oracle 51 (96 tests), the guards' tests 32, the generator's own tests 17, the
reference script's tests 9, and 11 for the 50 others. The oracle's tests were the longest single
test, and set a floor of about a minute to the wall time there, until the tools' own tests left
the quick tier ([below](#the-tools-tests-leave-the-quick-tier)). In the full tier, the pools of four workers
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

**The flag sets and the checks** ([Flag sets](#flag-sets), [The checks of a debug
build](#the-checks-of-a-debug-build)) were measured on 2026-11-19 against the commit before them,
each pair run back to back on the same machine, as above; the Mac was loaded by other jobs (load
average 5 to 9), and the Linux machine by other users:

| Where | Quick tier, before and after | Full tier, the tests that depend on the compiler, before and after | Whole full tier, after | Build, before and after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 49.9 and 52.5 s; 46.6 and 48.3 s | 95.6 and 154.1 s | 346 s | 2.3 and 4.8 s |
| Mac, GCC 16 | 42.9 and 44.9 s; 40.2 and 42.1 s | 56.4 and 88.1 s | 273 s | 3.8 and 9.1 s |
| Linux, 16 threads, GCC 13 | 77.3 and 84.4 s | 111.6 and 148.8 s | 520 s | 4.3 and 8.6 s |
| Linux, 16 threads, Clang 18 | 81.6 and 80.3 s | 110.9 and 146.0 s | 517 s | 3.2 and 6.7 s |
| Linux, 4 threads, GCC 13 | | 110.3 and 141.1 s | | |
| Linux, 4 threads, Clang 18 | | 105.4 and 136.3 s | | |
| Windows, 8 logical processors, MSVC | 86.1, 89.2, 95.1 and 100.3, 102.0, 102.9 s | 125.6 and 227.1 s | 604 s | 6.7 and 13.8 s |

In test time, the quick tier gained 7 to 11 seconds on the Mac, 13 on the Linux machine (once 28,
when one test of a few milliseconds took 10 seconds there) and 28 to 56 on the Windows machine, of
which the debug build's runner in `api.oracle` is 4 to 6 seconds on the Mac and the Linux machine
and 11 to 14 on the Windows machine, the checks 3 to 7, and the rest the other tests slowed by these
beside them. The full tier's tests that depend on the compiler gained 127 to 236 seconds on the
Mac, 143 to 149 on the Linux machine and 407 on the Windows machine: 85 to 101 seconds for
`full.api.flags.oracle` (175 on Windows), 34 to 120 for the kernels' runners in the cross-checks
(192 on Windows, where the debug build's packed runner, at `/Od` with `/RTC1` and the debug C
runtime, takes 0.2 seconds per 6 000 lines, five times the optimized one), and the rest the tests
beside them. On the hosted runners the quick tier's ctest step took about as long as on the Linux
machine on Linux x86-64 and 1.4 to 2.2 times as long as on the Windows machine on Windows
([Costs, Milestone 1](results/costs-milestone1.md)): by those ratios, these add about 40 seconds
to the full tier's job on Linux and 2.5 to 4 minutes on Windows, and 15 to 30 seconds to the quick
tier on Windows, whose ctest step is already over two minutes there.

**The program's names** ([above](#the-programs-names)): `api.shadow` took 0.5 seconds with Apple
clang 21 and 0.7 with GCC 16 on the Mac, 1.8 with Clang 18 and 1.1 with GCC 13 on 16 threads of
the Linux machine, and 5.3 with MSVC on the Windows machine, where it compiles the program seven
times, three of them under `/analyze`; measured on 2026-11-19 in a quick tier run with
`--parallel 4`.
The 8 calls of constructors that the same change added to the cases of the checks add 8 runs per
state of the environment to each `api.checks.*.rounding` and `api.checks.*.flush`, under a second
on every machine.

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
  once; since the tools' tests left the quick tier ([below](#the-tools-tests-leave-the-quick-tier)),
  the rest of the generator's tests without C++ do too.

**What left the quick tier**, and what that costs. The interpreter's enumerations of toy formats,
the generator's four longest test classes and the oracle's six enumerations left whole; the
cross-checks of the compiled runners keep 6 000 of their 20 000 cases and the public interface
2 000 of its 10 000. To see what the smaller samples still catch, every applicable one-statement
change of each kernel's generated scalar code was planted in turn (`tests/kernel_mutants.py`: an
operator turned, an operand dropped, an FMA made a product or given a zero addend, a comparison
loosened, a constant shortened, a selection swapped: 1 052 changes of the 63 kernels, in their
`double` and `float` code alike, and a statement of a fix-up in both of its forms), built into
three scalar runners (the build's flags, `-ffp-contract=off` and `=fast`, all at `-O3`) and the
public interface's runner, and put through the cross-checks and the public interface's tests of
its kernel with each tier's samples. On the Linux machine with GCC 13 (results in
`results/milestone1/mutants/`), the full tier catches 865 and the quick tier 863 of them, and
nothing the full tier misses. The two it misses fail on one or two cases of the full tier's
20 000: `ball_scale_2` with one FMA computed as a product and a sum (only the `-ffp-contract=off`
runner shows it), and `add_fast_2_2_full` with its finiteness test `inf > a` loosened to
`inf >= a`, first at case 9 280. The samples were chosen by this experiment, when it was first run
on the Mac (863 and 861 then, with the same two between the tiers): with 2 000 cases for the
compiled runners two more went unseen, and with 1 000 for the public interface three more. The
oracle's own mutants (`oracle/selftest/mutants.py`, 65 of them) are all caught by the part of its
selftest that was then in the quick tier (now `full.tools.kairn-oracle.selftest`) but one,
`exhaustive: -inf left out of a one-limb domain`, which only an enumeration can see and
`full.kairn-oracle.selftest` catches.

**What neither tier catches.** The tiers judge results against the kernels' claims, so a change
that alters a result while keeping every claim passes them by design: 187 of the 1 052 do. What
guards the listing itself is the generator's comparison with the interpreter
([below](#the-generators-tier)), which the same tool runs with `--bits`: the generator's scalar
runner with the changed kernel alone, built in the 15 configurations of that test with GCC 13 and
again with Clang 18, on that test's cases, every result required to be bit-identical to the
interpreter's. With both, each change falls in one class:

| Class | Changes |
|---|---|
| Caught by the quick tier | 863 |
| Caught by the full tier only | 2 |
| Caught by the comparison with the interpreter only | 122 |
| Caught by nothing | 65 |

Of the 122, 70 are FMAs computed as a product and a sum, 18 FMAs of a zero addend computed as a
plain product, 12 FMAs given a zero addend, 8 shortened constants and 14 others; GCC's builds catch
all of them, Clang's 119. Each of the 65 was then examined by hand, with two searches for an operand
on which it differs from the kernel: the changed and the original kernel compiled side by side, on
every combination of the special values of the format in every position (or 4 million of them),
4 million random cases per format from strata like the tests' and from numbers just above and below
a power of two, as many with non-finite operands for a kernel of the extended domain and with any
value anywhere, and every binary32 number for a one-input kernel; and 500 000 cases per format of
the oracle's own generator, which keeps to the kernel's domain. The verdicts, with the reasons and
the operands, are in `results/milestone1/mutants/survivors.json`:

- **48 are equivalent**: they cannot change a result. 9 guards `a + 0.0` (which turns −0 into +0)
  made `a - 0.0`: the guarded value only enters a TwoSum whose error term is +0 for both zeros, or
  in a fix-up a product with infinity. 8 finiteness tests of a Ball's center loosened to `>=`: an
  infinite center also makes the radius infinite or NaN, which the test beside it catches. 31 FMAs
  of a zero addend computed as a product, or as a product and a sum: these change only the sign of
  a zero result, and that zero goes into a radius that ends with the addition of a positive
  constant, into `next_up`, into a product with infinity, into Dekker's error sum, where the sign
  of a zero cannot survive, or, in Veltkamp's split, cannot occur.
- **17 were blind spots**: an operand tells them apart, and no test supplied it. 7 on operands of
  the kernel's domain: in `mul_2_2`, `mul_2_2_full`, `ball_mul_2` and `ball_mul_2_full`, `x1 * y1`
  for the FMA gives a low limb −0 instead of +0 for a pair with a negative tail times zero; `split`
  with its splitter $2^s + 1$ shortened to $2^s$ gives a high half of 13 bits instead of 12 to a
  binary32 number just above a power of two; and Dekker's product with either splitter shortened
  has another error term near underflow in binary32. 10 only on operands outside the domain (a pair
  that is not normalized, or not canonical), which the comparison takes too: bit identity holds on
  any operand. None breaks a claim: on every operand of the domain found, the oracle passes the
  changed result, since Kairn leaves the sign of a zero unspecified, the error term stays within
  the claim's allowance for underflow, and `split` claims only $a = a_h + a_l$ (that its high half
  has at most half the precision, which Dekker's product relies on, is in its description but is
  not a claim).

Those operands are now among the comparison's cases (`SPECIAL_CASES` in `gen/tests/test_cxx.py`),
and it catches all 17: of the 1 052 changes, the tests now catch 1 004, and the 48 they miss cannot
change a result. With `--jobs 32` the whole run took 47 minutes on 32 hardware threads of the Linux
machine; the comparison alone (`--no-tiers`) takes about a minute per change and core, and
`--ids` reruns given changes (`results/milestone1/mutants/README.md`).

The stopgap of the one tier, a timeout of 1 800 seconds for the generator's and the oracle's tests
and of 60 minutes for the jobs of `build.yml`, is gone: their timeouts are 600 seconds and 30
minutes again.

### The tools' tests leave the quick tier

On the hosted runners the quick tier's ctest step took 128 to 202 seconds on Windows (167 and 172
on the median runs with MSVC and clang-cl), over the two minutes of the brief, and 54 to 126
elsewhere ([Costs, Milestone 1](results/costs-milestone1.md#4-the-quick-tier-on-the-hosted-runners)).
Five tests of the tools set that time, two fifths of the quick tier's test time there, and none
builds anything of Kairn's with the build's compiler: the oracle's selftest (34 to 105 seconds),
the guards' tests (23 to 58), the generator's (14 to 36), the reference script's (8 to 49) and
the brute-force driver's (1 to 4). On 2026-11-19 they moved to the full tier as `full.tools.*`,
and run in CI where they ran before ([Continuous integration](#continuous-integration)); the
debug build's runner left the quick tier's `api.oracle.K.F` (below). Measured as above, the
builds of before (the commit before) and after one after the other on the same machine; a second
run of a build reads ctest's times of the first and starts the longest tests first. The Mac was
loaded by other jobs (load average 4 to 14); the runs on the Windows machine during another job's
builds and tests there are left out. Seconds, the first run of a build, then the later ones:

| Where | Quick tier, before | The tools' tests out | After: the debug build's runner out too | Full tier, before and after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 56.0; 51.0, 51.4 | 41.7; 36.2 | 40.1, 41.4; 35.1 | 357 and 374 |
| Mac, GCC 16 | 50.1; 50.1, 47.0 | 36.8; 32.4 | 36.4; 30.9 | 294 and 320 |
| Linux, 16 threads, GCC 13 | 82.6; 79.2 | 53.0; 48.3, 48.6 | 52.2, 53.5; 48.7 | 534 and 563 |
| Linux, 16 threads, Clang 18 | 83.3; 80.5 | 54.1; 48.9, 48.1 | 52.7; 47.4 | 531 and 561 |
| Windows, 8 logical processors, MSVC | 110.3; 123.0, 105.7 | 76.7; 69.6 | 71.2, 69.1; 66.1, 63.8, 63.3 | 608 and 652 |
| Windows, 4 logical processors, MSVC | 136.1, 144.7 | 93.8, 87.6 | 84.1, 85.6 | |

The runs on 4 logical processors followed runs on 8 of the same builds, and read their times.
The full tier after is the same with or without the debug build's runner in the quick tier: the
Windows machine's is that of the build with the tools' tests out, since the run of the last
build there shared the machine with another job's full tier (1 024 seconds; it passed). Without
`--parallel`, the quick tier took 133 seconds on the Mac (194 before) and 189 on 16 threads of
the Linux machine.

The quick tier's test time is now that of the tests of the library: on 16 threads of the Linux
machine with GCC 13, 198 seconds, of which the compiled runners' cross-checks 106 (126 tests),
the public interface against the oracle 52 (97 tests), the checks of a debug build 17 (9), what
must not compile 9 (29), the object code 7 (3) and the 27 others 7; on the Windows machine 279,
of which 155 and 77 for the first two. No test takes more than five seconds, so with
`--parallel 4` the wall time is a quarter of the test time. The full tier gained the five tests,
60 seconds of test time on the Mac and 166 on the Windows machine, which run beside its longest
tests; in CI, the jobs of `full.yml` that build gain the four that are not the generator's (206
seconds of test time on the median hosted Windows run, about a minute of wall time on four
slots).

**On the hosted runners.** The stored per-test times of the median runs
(`results/milestone1/costs/ci/`), replayed on four slots without the five tests
(`python3 bench/ci_times.py tables`), give 102 seconds for the ctest step with MSVC and 106 with
clang-cl, 40 to 41 on Linux x86-64, 29 to 30 on arm64 and 51 on macOS. But the quick tier has
gained tests since those runs: the regression cases, the object code, the checks of a debug build
and its self-test and constant expressions, more of what must not compile, two examples, and the
debug build's runner in `api.oracle.K.F`. Each was put at its time on the Windows machine times
the ratio of the hosted to the local time of the tests the two runs share, the stored hosted
time kept for the others, and the quick tier replayed as ctest schedules it without its times of
an earlier run (in the order the tests are registered, a test of `PROCESSORS 2` on two slots); a
second estimate put every test at its local time times its family's ratio. The ratio is 1.58
with MSVC and 1.66 with clang-cl against the Windows machine on 8 logical processors (1.5 to 1.75
by family for the cross-checks and the public interface), 1.27 and 1.33 against it on 4, whose
times are closer to the hosted runners'; the four estimates agree within 3 seconds. With the
debug build's runner, the ctest step comes to 115 to 116 seconds with MSVC and 120 to 121 with
clang-cl; without it, 108 to 110 and 113 to 116. On Linux x86-64 the same estimates give 48
seconds with GCC, and on macOS 54.

**The debug build's runner** in `api.oracle.K.F` took 14 to 16 seconds of the quick tier's test
time on the Windows machine (5%; its forms run at `/Od`, with `/RTC1` and the debug C runtime),
an estimated 19 to 21 on a hosted Windows runner, 5 to 6 of the ctest step: with clang-cl, the
difference between two minutes and less. On the Mac and the Linux machine it took 3 to 4 seconds
of test time, one or two of wall time. The full tier judges the same runner on every form, on
the same 2 000 cases (`full.api.flags.oracle.K.F`), and keeps it in `full.api.oracle.K.F` on the
first form of each kernel on 10 000; the quick tier keeps the debug build's self-test, constant
expressions and checks. It left the quick tier.

**The margin** is small: 4 to 12 seconds by these estimates, while the hosted runners of one
platform differ by a fifth from run to run (the five runs of each Windows job of
[Costs, Milestone 1](results/costs-milestone1.md) ranged from 23% under their median to 18% over
it), so a slow Windows runner can still take more than two minutes. Each 1 000 cases fewer per
compiled cross-check would save about 8 seconds of the ctest step with MSVC and 6 with clang-cl,
each 1 000 fewer per test of the public interface 7 and 4 (by the fixed and per-case costs of the
same page); the samples are those that the planted faults chose ([above](#time)). Fewer
processes would not change what is checked: on the Windows machine one compiled cross-check
(`add_2_2`, `binary64`, eight runners) takes 1.6 to 1.7 seconds, of which the oracle's generator
0.36 (0.11 for one case), the eight runners through `run_runners.py` 0.66 to 0.69 (0.05 to 0.08
each, most of it starting the process, on 6 000 lines), the oracle's check 0.36 and the guards
0.08, and a Python process starts in 0.05. Generating, checking and guarding in the process of
`run_runners.py` would save about a quarter of a second per compiled cross-check there and a
fifth per test of the public interface, by the ratios above 15 to 20 seconds of the hosted ctest
step; it is not done.

## The generator's tier

`python3 gen/kairn-gen test` is the generator's own suite (`gen/README.md`, "The tests"). About
two thirds of its time goes to its C++ tests, which build the generated code at `-O0` and
`-O2`, with and without `-frounding-math`, under every contraction setting, and with both forms of
the scalar fix-ups (inline, and a function of its own: `KAIRN_GEN_FIXUP_CALL`), and require every
build, scalar and packed, to be bit-identical to the interpreter, with special operands in every
lane. It is what sees a change of the listing that keeps every claim: of the 187 planted faults
that neither tier catches, it caught 122, and with the special operands it now adds for eight
kernels (`SPECIAL_CASES`), 139; the other 48 cannot change a result
([What neither tier catches](#time)). The cross-checks build each compiler's own form only. ctest runs it without them (`--no-cxx`): with them it took 148 seconds on its own on the
Linux machine of [Time](#time), and the cross-checks already compile the same code with the build's
compiler and flags. Of the rest, four test classes take about 95% of the time; the full tier runs
them alone (`-k`, `full.kairn-gen.test`) and the others in a test of their own (`--skip`,
`full.tools.kairn-gen.test`, the quick tier's `kairn-gen.test` until it left the quick tier). The
whole suite runs in the workflow `generator.yml`, once per GCC-style compiler of the CI and once
without C++ on Windows: its C++ tests are written for a GCC-style driver (`-O0`, `-ffp-contract=`,
`-frounding-math`, `-fsyntax-only`, `-o`, `-mfma`, and the text of Clang's and GCC's errors), which
neither compiler of the Windows jobs is, and they require every build to be bit-identical to the
interpreter, which MSVC's `/fp:strict` is not for the sign of some zeros
([Cross-checks](#cross-checks)). On Windows the [flag sets](#flag-sets) build the kernels at `/Od`
and `/O1` instead. By hand:

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

## The adversarial search

The cross-checks and the brute-force tier draw their cases at random from strata; how close a
claim came then depends on what the draws met. `python3 oracle/kairn-oracle search` looks for
the cases that bring a kernel closest to its claims, or past them: for a kernel and a format it
evolves a population of cases through a runner (the interpreter by default, any compiled runner
too) and judges every completed line with the oracle's own checker, keeping the best cases for
each quantity a claim bounds (the error over its bound and the observed constant for `error`, the
excess in gaps for `upper`, the smallest slack of the radius for `encloses`). Its moves are those
of floating-point operands (bits of a significand, units in the last place, extreme significands,
second limbs at the edges of the normalization invariant, exponents, signs, swaps, ties,
cancellation, the underflow and overflow thresholds); every case stays inside the kernel's
requirements; its seeds are the attaining lines of the stored brute-force runs, the regression
cases, the operands the literature gives for the double-word algorithms (`oracle/kairn_oracle/tight.py`,
transcribed with the page) and cases of every stratum. It is deterministic, and a case it reports
is an ordinary line that `check` judges alike (`oracle/README.md`, "search").

**What it found** in Milestone 1. Each kernel with an `error`, `upper`, `encloses` or `extends`
entry, in `binary64` and `binary32`, got 20 000 cases (seed 0), seeds included, through the
interpreter on the Mac: 94 searches in 141 seconds with six worker processes, 825 seconds of
process time. Through the scalar runner of an Apple clang build instead, the 94 searches gave the
same values case for case, in 26 seconds. Its seeds were the brute-force lines, the literature and
the strata (the regression cases came after, from this run). A second run started from the strata
alone, to see what the search adds by itself. **No claim was violated.** The table compares the extreme of each quantity with that of the brute-force runs of
[Brute force, Milestone 1](results/brute-milestone1.md) (13.8 billion results of the compiled
runners, recomputed exactly from their attaining lines): bold where the search came closer to the
claim, ↓ where it stayed farther. Exact claims ($c = 0$, $t = 0$) are left out: the search has
nothing to climb there and found no inexact result.

| Kernel | Quantity | `binary64` brute force | from the strata | with every seed | `binary32` brute force | from the strata | with every seed |
|---|---|---|---|---|---|---|---|
| `add_1_1` | observed c | 1 − 1.1·10<sup>-16</sup> | 1 − 1.1·10<sup>-16</sup> | 1 − 1.1·10<sup>-16</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> |
| `add_1_1` | error / bound | 1 | 1 | 1 | 1 | 1 | 1 |
| `add_2_1` | observed c | 1.9663 | 1 − 5.6·10<sup>-17</sup> ↓ | **2 − 4.4·10<sup>-16</sup>** | 1.9754 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `add_2_1` | error / bound | 0.9832 | 0.5 ↓ | **1 − 2.2·10<sup>-16</sup>** | 0.9877 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `add_2_1_full` | core's observed c | 1.9684 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.9693 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `add_2_1_full` | core's error / bound | 0.9842 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9846 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `add_2_2` | observed c | 1.9966 | **2.5** | **3 − 1.1·10<sup>-15</sup>** | 2.0668 | **2.25** | **3 − 6.0·10<sup>-7</sup>** |
| `add_2_2` | error / bound | 0.6655 | **0.8333** | **1 − 8.1·10<sup>-16</sup>** | 0.6889 | **0.75** | **1 − 4.4·10<sup>-7</sup>** |
| `add_2_2_full` | core's observed c | 2 − 4.4·10<sup>-16</sup> | **2.5** | **3 − 1.1·10<sup>-15</sup>** | 2.1541 | **2.5** | **3 − 6.0·10<sup>-7</sup>** |
| `add_2_2_full` | core's error / bound | 0.6667 | **0.8333** | **1 − 8.1·10<sup>-16</sup>** | 0.718 | **0.8333** | **1 − 4.4·10<sup>-7</sup>** |
| `add_fast_2_2` | observed c | 2.2284 | 2.1693 ↓ | **2.8717** | 1.7874 | **2.8212** | **3 − 1.3·10<sup>-6</sup>** |
| `add_fast_2_2` | error / bound | 0.7428 | 0.7231 ↓ | **0.9577** | 0.5958 | **0.9404** | **1 − 4.4·10<sup>-7</sup>** |
| `add_fast_2_2_full` | core's observed c | 1.5711 | **2.2964** | **2.3628** | 2.2991 | **3 − 1.3·10<sup>-6</sup>** | **2.7641** |
| `add_fast_2_2_full` | core's error / bound | 0.5237 | **0.7655** | **0.7876** | 0.7664 | **1 − 4.4·10<sup>-7</sup>** | **0.9214** |
| `ball_add_1` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1 | 1 |
| `ball_add_1_full` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1.125 ↓ | 1 |
| `ball_add_2` | slack, gaps | 1.2524 | **1.1758** | **1.1719** | 1.2501 | **1.1563** | **1.125** |
| `ball_add_2_full` | slack, gaps | 1.2589 | **1.1602** | **1.1719** | 1.2501 | **1.1094** | **1.1582** |
| `ball_mul_1` | slack, gaps | 1.5581 | **1.5001** | **1.5037** | 1.5353 | **1.5001** | **1.5** |
| `ball_mul_1_full` | slack, gaps | 1.5987 | **1.5** | **1.5061** | 1.5907 | **1.508** | **1.5** |
| `ball_mul_2` | slack, gaps | 2.5041 | **2.4965** | **2.4915** | 2.5015 | 2.5327 ↓ | **2.4618** |
| `ball_mul_2_full` | slack, gaps | 2.5 | **2.4482** | **2.4421** | 2.5608 | **2.5** | **2.5** |
| `ball_scale_1` | slack, gaps | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 1.2·10<sup>-7</sup> | 1.25 ↓ | 1 + 1.2·10<sup>-7</sup> |
| `ball_scale_1_full` | slack, gaps | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 1.2·10<sup>-7</sup> | 1 + 1.2·10<sup>-7</sup> | 1 + 1.2·10<sup>-7</sup> |
| `ball_scale_2` | slack, gaps | 1.375 | **1.25** | **1.25** | 1.375 | **1.2501** | 1.375 |
| `ball_scale_2_full` | slack, gaps | 1.329 | 1.5 ↓ | **1.2511** | 1.375 | **1.2512** | **1.2534** |
| `ball_sub_1` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1 | 1 |
| `ball_sub_1_full` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1.125 ↓ | 1 |
| `ball_sub_2` | slack, gaps | 1.2511 | **1.2109** | **1.1564** | 1.25 | **1.1563** | **1.1563** |
| `ball_sub_2_full` | slack, gaps | 1.2509 | **1.1602** | **1.1582** | 1.2513 | **1.1719** | **1.1719** |
| `mul_1_1` | observed c | 1 − 3.3·10<sup>-16</sup> | 1 − 3.3·10<sup>-16</sup> | 1 − 3.3·10<sup>-16</sup> | 1 − 1.8·10<sup>-7</sup> | 1 − 1.8·10<sup>-7</sup> | 1 − 1.8·10<sup>-7</sup> |
| `mul_1_1` | error / bound | 1 − 1.1·10<sup>-16</sup> | 1 − 2.2·10<sup>-16</sup> ↓ | 1 − 1.1·10<sup>-16</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> |
| `mul_2_1` | observed c | 1.9533 | 1.6 ↓ | **1.9956** | 1.9105 | 1.8925 ↓ | **1.9697** |
| `mul_2_1` | error / bound | 1 − 2.2·10<sup>-16</sup> | 0.9908 ↓ | **1 − 1.7·10<sup>-16</sup>** | 1 − 1.5·10<sup>-7</sup> | 0.9998 ↓ | **1 − 8.9·10<sup>-8</sup>** |
| `mul_2_1_full` | core's observed c | 1.9561 | 1.9026 ↓ | **1.9956** | 1.9122 | 1.648 ↓ | **1.9697** |
| `mul_2_1_full` | core's error / bound | 1 − 2.8·10<sup>-16</sup> | 0.995 ↓ | **1 − 1.7·10<sup>-16</sup>** | 1 − 2.1·10<sup>-7</sup> | 1 − 4.2·10<sup>-6</sup> ↓ | **1 − 1.2·10<sup>-7</sup>** |
| `mul_2_2` | observed c | 3.3361 | **3.9959** | **4 − 3.5·10<sup>-8</sup>** | 3.4428 | **3.4993** | **3.5392** |
| `mul_2_2` | error / bound | 0.9772 | **0.999** | **1 − 8.7·10<sup>-9</sup>** | 0.9738 | **0.9939** | **0.9961** |
| `mul_2_2_full` | core's observed c | 3.4873 | 3.1298 ↓ | **4 − 1.3·10<sup>-8</sup>** | 3.4886 | 2.8815 ↓ | 3.4886 |
| `mul_2_2_full` | core's error / bound | 0.9809 | 0.9765 ↓ | **1 − 3.1·10<sup>-9</sup>** | 0.9689 | **0.9963** | **0.999** |
| `mul_pow2_2` | error / bound | 0.7385 | **0.75** | **0.75** | 0.75 | 0.75 | 0.75 |
| `mul_pow2_2_full` | core's error / bound | 0.7489 | 0.7422 ↓ | **0.75** | 0.75 | 0.75 | 0.75 |
| `radd` | excess, gaps | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `rmul` | excess, gaps | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `sub_1_2` | observed c | 1.6201 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.7841 | **2 − 6.0·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_1_2` | error / bound | 0.81 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.8921 | **1 − 3.0·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_1_2_full` | core's observed c | 1.6244 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.7425 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_1_2_full` | core's error / bound | 0.8122 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9167 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_1` | observed c | 1.9947 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.9724 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_2_1` | error / bound | 0.9974 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9862 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_1_full` | core's observed c | 1.8264 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.8864 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_2_1_full` | core's error / bound | 0.9132 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9432 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_2` | observed c | 2.1094 | 1.5 ↓ | **3 − 1.1·10<sup>-15</sup>** | 2.2401 | **2.5** | **3 − 6.0·10<sup>-7</sup>** |
| `sub_2_2` | error / bound | 0.7031 | 0.5 ↓ | **1 − 8.1·10<sup>-16</sup>** | 0.7467 | **0.8333** | **1 − 4.4·10<sup>-7</sup>** |
| `sub_2_2_full` | core's observed c | 2 − 4.4·10<sup>-16</sup> | **2.0046** | **3 − 1.1·10<sup>-15</sup>** | 2 − 2.4·10<sup>-7</sup> | **2 − 2.4·10<sup>-7</sup>** | **3 − 6.0·10<sup>-7</sup>** |
| `sub_2_2_full` | core's error / bound | 0.6667 | **0.6682** | **1 − 8.1·10<sup>-16</sup>** | 0.6667 | **0.6667** | **1 − 4.4·10<sup>-7</sup>** |
| `two_prod` | error / bound | 1 | 1 | 1 | 1 | 1 | 1 |
| `two_prod_dekker` | error / bound | 0.9239 | 0.885 ↓ | **0.9696** | 0.9259 | 0.9056 ↓ | **0.9687** |

Over the 116 quantities, the search with every seed came closer to the claim on 86 and as close
on 30; from the strata alone, closer on 66, as close on 20 and farther on 30 (it missed, for
example, the structured case of `add_2_1` in `binary64`, which it found for `sub_2_1`, `sub_1_2`
and the core of `add_2_1_full`, and the corner of the underflow range where the brute-force runs
had met the bound of `mul_2_1`). What it brought closest:

- **The accurate sum** (`add_2_2`, `sub_2_2`, the cores of their full kernels) comes within
  $8.1 \cdot 10^{-16}$ of its bound $3u^2/(1 - 4u)$ in `binary64` and $4.4 \cdot 10^{-7}$ in
  `binary32`, with an observed constant of $3 - \epsilon$; the brute-force runs had found 2.0 to
  2.24, 0.67 to 0.75 of the bound. The case is the one with which
  [MR22](design/phase0/references.md#mr22) prove the bound asymptotically optimal (Property
  2.1, which they say random testing cannot find); from the strata alone the search reached 2.25
  to 2.5, but 1.5 for `sub_2_2` in `binary64`.
- **The sums with one limb** (`add_2_1`, `sub_2_1`, `sub_1_2` and their cores) come within
  $2.2 \cdot 10^{-16}$ and $1.2 \cdot 10^{-7}$ of $2u^2$, found from the strata (but for `add_2_1`
  in `binary64`) as well as from [JMP17](design/phase0/references.md#jmp17)'s case of DWPlusFP;
  before, 0.81 to 0.997.
- **The double-word product** `mul_2_2` comes within $8.7 \cdot 10^{-9}$ of $4u^2 + \tfrac32\eta$
  in `binary64`, with an observed constant of $4 - 3.5 \cdot 10^{-8}$ (3.34 in the brute-force
  runs; the case MR22 give for their Theorem 2.8 has 3.997, which the search carried further); in
  `binary32` 0.996 and 3.54.
- **The fast sum** `add_fast_2_2` comes within $4.4 \cdot 10^{-7}$ of its bound of form A in
  `binary32` (0.60 before), from a brute-force line, and the core of `add_fast_2_2_full` from the
  strata alone: the bound $3u^2(\lvert x\rvert + \lvert y\rvert)$ proved for Kairn is attained.
- **The radii** of the two-limb Ball sums keep 1.11 to 1.18 gaps of slack at the closest
  (1.25 before), those of the one-limb product 1.5 (1.54 to 1.60), of the two-limb scaling 1.25
  (1.33 to 1.375) and of the two-limb product 2.44 to 2.5 (2.5 to 2.56); those of the one-limb
  sums and scaling stay at one gap, as before.
- `two_prod_dekker` comes to 0.97 of its bound near underflow (0.92 before) and `mul_pow2_2` to
  0.75 in `binary64` (0.74).

**A longer run**, on the Linux machine: 1 000 000 cases per kernel and format (94 million in all,
seed 0, batches of 1 024) through the scalar runner of a GCC 13 build, 48 processes, 405 seconds,
starting from the regression cases below. No claim was violated. It came closer still on 42 of the
116 quantities: `mul_2_2` and the core of `mul_2_2_full` to within $1.9 \cdot 10^{-15}$ of their
bound in `binary64`, with an observed constant of $4 - \epsilon$ (from a case of the stratum
`pow2`, not from the literature), and in `binary32` to 0.998 (`mul_2_2`) and $1 - 1.9 \cdot
10^{-7}$ (the core of `mul_2_2_full`); `add_fast_2_2` and its core to within $8.1 \cdot 10^{-16}$
in `binary64` (0.96 at 20 000 cases); `two_prod_dekker` to 0.992 and 0.986; and the smallest
slack of the two-limb Ball
radii to 1.11 to 1.16 gaps for the sums, 1.25 for the scaling and 2.20 for the product in
`binary64`. Its best lines replaced those of the shorter run in the regression cases where they
came closer.

**What it did not find.** A search climbs the quantities of the claims, and a fault that breaks a
claim only where the correct kernel is far from its bound gives it nothing to climb. Of the
planted faults of `tests/kernel_mutants.py` that the full tier catches and the quick tier misses,
it found the loosened finiteness test of `add_fast_2_2_full` after 9 025 cases of `binary64`
(the full tier's random cases meet it at case 9 280), and missed the FMA of `ball_scale_2`
computed as a product and a sum in 100 000 cases per format: that fault breaks the radius where
the input radius is zero and the center's error is near its bound, where the correct kernel's
slack is large, and the full tier's 20 000 random cases met it once or twice. The search is a
complement to the random tiers, not a replacement.

**Where it runs.** By hand, as above, with any runner; and in the full tier,
`full.search.compiled`: every kernel, both formats, 5 000 cases each through the scalar runner of
the build, four worker processes; 10 seconds on the Mac, 16 on the Linux machine (GCC 13 and Clang
18 alike) and 27 to 33 on the Windows machine. Its seeds then include the regression cases, so it
starts from the closest cases known.

### The shrinker

A failing case found anywhere is first made as simple as it can be:
`python3 oracle/kairn-oracle shrink 'LINE' --runner RUNNER` keeps the failure of the same `ensures`
entry (in the extended domain, the same statement), as the oracle judges it, while it replaces
operands by zero or powers of two, cuts significands, moves exponents toward zero, and looks for
the smallest toy format in which the same runner fails the same way (the interpreter runs every
format; a compiled runner `binary64` and `binary32` only). It is deterministic, ends, and prints
the shrunk line with the command that reruns it (`oracle/README.md`, "shrink"). On the planted
faults of the oracle's self-tests it takes, for example, a `binary64` case of `mul_2_2` with the
cross term dropped from 195 significant bits to $1 \cdot (1 + 2^{-53})$, and to a case of
`fp:5:-5:-2`; through a compiled runner with a planted fault of `add_fast_2_2_full`, the line the
search found to $(-\Omega, -2^{969}) + (-2^{969}, 0)$, whose result $(-\infty, +\infty)$ is not
canonical.

### The regression cases

`tests/regression/cases.txt` holds request lines that the quick tier runs through every runner it
builds (`regression.cases`): the cases that found a problem in Milestone 1, as far as the
repository records them with operands (the operands that the planted faults of
`tests/kernel_mutants.py` showed no test supplied, which the generator's comparison now has in
`SPECIAL_CASES`, where they are in their kernel's domain; the corner where TwoSum's error term
overflows); the operands of the literature; the attaining lines of the brute-force runs for every
claim that came within 2% of its bound; and the search's best lines where it came at least as
close as the brute-force runs. Each line has a comment: where it came from and what it showed.
The rule for adding one is at the top of the file: a failure is shrunk, and goes in with where it
was found, the entry it failed, and the class of the fault (statement, generator, code, compiler or
hardware). A case the line protocol cannot carry has a test of its own, named there: the product
of the program fused into a kernel is `api.boundary.*`. Every line of `binary64` and `binary32`
runs through every compiled runner and through every form of the public interface that calls its
kernel, and every line, toy formats included, through the interpreter; the oracle judges each
result as in the cross-checks. 185 lines today (16 from the history, 38 of the literature, 62 of
the brute-force runs, 69 of the two searches); in the quick tier's run, 0.5 to 1.1 seconds on the Mac,
1.1 on the Linux machine and 2.6 to 6 on the Windows machine, where starting a process costs most (one
run of each compiled runner, of the interpreter, and of each runner of the public interface per
name of a form).

## Continuous integration

Five workflows under `.github/workflows/`, each on pushes to `main` and on pull requests, one run
per branch at a time (a new push cancels the run in progress); their jobs all start at once:

| Workflow | Jobs |
|---|---|
| `build.yml`, "Build and test" | The quick tier: configure, build and `ctest` with Ninja, `Release` and warnings as errors, on Linux x86-64 with GCC and with Clang (packed: AVX2), Linux arm64 with GCC and with Clang (NEON), macOS arm64 with Apple clang (NEON), and Windows x64 with MSVC and with clang-cl (AVX2) |
| `full.yml`, "Full tier" | The full tier's tests that depend on the compiler, and the tools' own tests but the generator's (`ctest --test-dir build/tests/full` with `-LE` of the labels `python` and `generator`: the compiled runners' cross-checks and the public interface on more cases, the [flag sets](#flag-sets), the object code on the whole flag matrix, the adversarial search, and the tests labelled `tools`), on the same seven platforms and compilers, configured and built as in `build.yml`; and those in exact arithmetic (`-L python`), once, on Linux, configured but not built, in two jobs: the interpreter's enumerations (`-L interp`) and the oracle's (`-L python -LE interp`) |
| `generator.yml`, "Generator's full suite" | `python gen/kairn-gen test --cxx CXX`, C++ included, on Linux x86-64 and Linux arm64 with GCC and with Clang, and macOS arm64 with Apple clang; and `--no-cxx` on Windows x64. It contains the full tier's `full.kairn-gen.test` and `full.tools.kairn-gen.test` (label `generator`), which `full.yml` leaves out |
| `proofs.yml`, "Proofs" | `make -C proofs` in the Rocq team's image `rocq/rocq-prover:9.0` (Rocq 9.0.1), with Flocq 4.2.2 from opam, cached between runs; what the audit printed is kept as the run's artifact `proof-audit` |
| `checks.yml`, "Generated files and documentation" | `gen/kairn-gen check`, `docs/tools/reference.py --check` and its tests, `mkdocs build --strict`, Doxygen 1.18.0 on `docs/Doxyfile` with warnings as errors into the site's `api/`, `docs/tools/check_links.py`; the built site is kept as the run's artifact `site` |

Every test of the full tier thus runs on every push and pull request: a test that depends on the
compiler with every compiler, a test in exact arithmetic once, and the generator's tests, which
compare the interpreter with the machine's arithmetic (Python's float and `math.fma`), once on each
operating system and processor of the CI (x86-64 Linux, arm64 Linux, arm64 macOS, x86-64 Windows).
The tools' own tests run where they ran when they were in the quick tier: the oracle's, the
guards', the reference script's and the brute-force driver's in each job of `full.yml` that
builds, on every platform and compiler; the generator's, which compiles nothing, on every operating
system and processor, in `generator.yml`, which ran it already inside the whole suite. The tests
of the reference script also run in `checks.yml`, beside the pages they test, as before: they take
seconds there, and that job is the one that reports on the documentation.
