# Testing

How Kairn's code is tested, what each test is for, and how to rerun one case of a failing test
by hand. The parts named here (generator, interpreter, oracle, runner, claims) are described in
[Architecture](architecture.md#the-pipeline).

## The tiers

| Tier | What | Where it runs | Time |
|---|---|---|---|
| Quick | `ctest`: the generator's tests without their C++ part, the oracle's own tests, the cross-checks below, the consumer checks | every push and pull request, on every platform of the CI; and by anyone, with the three commands of [Getting started](../getting-started/index.md#configure-build-and-test) | about two minutes on a recent machine with `--parallel 4` |
| Generator | `python3 gen/kairn-gen test`: the generator's whole suite, C++ included | every push and pull request, with each GCC-style compiler of the CI | a few minutes per compiler |
| Proofs | `make -C proofs`: every Rocq proof, then the axiom audit | every push and pull request | a minute or two, with four cores |
| Brute force | `tests/brute/brute.py`: the cross-checks of the compiled runners on millions of random cases per kernel, format and machine (every runner of a machine on the same cases), and the interpreter on every operand of larger toy formats, with the quick tier's guards and a time budget | by hand, on the test machines, never in CI (`tests/brute/README.md`); results in [Brute force, Milestone 1](results/brute-milestone1.md) | about 90 minutes per machine for Milestone 1 |

A kernel's claims are only as good as the tests that could have refuted them, so every cross-check
fails when it checked nothing, or less than it says: when the oracle judged no case, when an
enumeration did not cover the domain it names, when a random run missed a stratum, or when a claim
was never put to the test ([below](#what-a-pass-requires)).

## The quick tier

The tests that `ctest` runs, by name:

| Test | Checks |
|---|---|
| `kairn-gen.check` | Every committed generated file is what `python3 gen/kairn-gen build` writes. |
| `kairn-gen.test` | The generator's own tests, without those that compile C++ (`--no-cxx`): see [the generator's tier](#the-generators-tier). |
| `kairn-oracle.selftest` | The oracle's own tests (`--quick`), including injected errors it must catch. It compiles its own C++ reference runner with the build's compiler; if that fails, the test fails. |
| `kairn-oracle.claims` | The oracle can read every claim in `gen/claims.json`. |
| `docs.reference.check`, `docs.reference.test` | The reference pages of the site are what `docs/tools/reference.py` writes, and that script's own tests ([Documentation](documentation.md#reference-pages)). |
| `crosscheck.interp.K` | Kernel K run by the generator's interpreter on **every** operand combination of a toy format. |
| `crosscheck.interp-restricted.K` | Kernel K run by the interpreter on every operand of a **restricted** domain of a toy format, for the kernels whose whole enumeration is too long. |
| `crosscheck.interp-sampled.K` | The same kernels on random cases of the whole toy format, from every stratum. |
| `crosscheck.cxx.K.F` | Kernel K compiled with the build's compiler and flags (the scalar kernels, `gen/tests/runner.cpp`), on random cases of format F (`binary64`, `binary32`) from every stratum. |
| `crosscheck.cxx-S.K.F` | The same, compiled with the contraction setting S added to the flags ([below](#contraction)). |
| `crosscheck.B.K.F`, `crosscheck.B-S.K.F` | The same for the packed kernels of backend B, `neon` on AArch64 and `avx2` on x86-64 ([below](#packed-kernels)). |
| `crosscheck.guards` | The cross-checks' guards fail the runs they are there to fail (`tests/test_crosscheck_guards.py`). |
| `consume.*` | A CMake project that uses Kairn through `add_subdirectory`, and one through `find_package` after `cmake --install`, build and run a kernel. |

The tests of the public interface (`tests/api/`, label `api`):

| Test | Checks |
|---|---|
| `api.oracle.K.F`, `api.oracle.K.F.contract-fast` | Every public operation whose results must satisfy the claims of kernel K, computed through the operators and functions of `kairn/kairn.hpp` (`tests/api/runner.cpp`, a runner of the line protocol), on random cases of format F, judged by the oracle; once with the build's flags and once with contraction forced on. Each form of the operation (`x + a` and `a + x`, `x += a`, the marked and the unmarked operator) is a pipeline of its own. |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is computed by a public operation or listed by the runner as internal to others. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, the same results at run time, the properties of the types, and that an operation compiles without `kairn::unverified` exactly when its kernel is proved. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass in the default environment and fail under each directed rounding mode and under flush-to-zero. |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break the kernels and define no macro (reassociation; `-ffp-model=fast`; on AArch64 `-fno-signed-zeros` with `-ffp-contract=fast`): `kairn::self_test()` must fail. |
| `api.reject.*` | What must not compile, each with a control that compiles: the flags `config.hpp` rejects, and each kind of operation written without the marker while its kernel is unverified (against a copy of the headers in which every kernel is). |
| `api.boundary.S`, `api.boundary.unguarded.S` | A product the program computes and passes in (`x + a * b`, `E2(a * b)`, `from_limbs`, a ball's center or radius) gives the result of the same operation on the rounded product, bit for bit, under contraction setting S; with the guard turned off, it must not where the compiler was measured to fuse across statements (`tests/api/boundary.cpp`). |
| `api.k1.zero_cost` | The instructions emitted for loops over `Expansion<double, 1>` against the same loops over `double` (`tests/api/k1/zero_cost.py`). |
| `api.example.*` | The examples of the documentation (`docs/examples/cpp/`), which check their own output; `api.example.accurate_sums.*`, built under each contraction setting, also compares it with the text its tutorial shows ([Documentation](documentation.md#examples)). |

Labels select groups: `ctest -L crosscheck`, `-L interp` (with `-L restricted` and `-L sampled`
among them), `-L cxx` (the scalar runners), `-L packed`, `-L contraction`, `-L api` (with
`-L oracle`, `-L reject` and `-L boundary` among them); `-R` selects by name, for example
`ctest -R mul_2_2`.

### Cross-checks

A cross-check is one pipeline: the oracle writes requests, a runner completes them, and the oracle
judges every completed line against the kernel's claims in exact arithmetic
([the line protocol](architecture.md#the-line-protocol)). The test prints the oracle's report,
pass or fail; on failure it also prints the command that reruns one case (below).

- **Every kernel** in `gen/claims.json` gets its tests: adding a kernel to the generator adds them.
- **Random cases**: 20 000 per kernel and format (`KAIRN_CROSSCHECK_CASES`), seed 0
  (`KAIRN_CROSSCHECK_SEED`), so that a run is the same everywhere and can be repeated. The
  oracle's generator chooses the strata from the kernel's family (`oracle/README.md`): those of
  the first wave for sums and products, and the families of the second wave (conversions,
  comparisons, directed steps, scaling, balls) each with strata of its own.
- **The toy formats** depend on the kernel's inputs, each written as its role: `1` a limb, `2` a
  normalized pair, `r` a radius (`nonneg()`), `c` a power of two (`power_of_two()`). They are
  chosen so that each enumeration is 50 000 to 250 000 cases, with the range of products below 1
  so that most products neither overflow nor vanish, and at least the kernel's minimum
  precision. The table is in `tests/CMakeLists.txt`; a kernel whose inputs have no entry, or
  whose minimum precision is above its toy format's, gets a test that fails and says so, rather
  than a run where nothing is claimed.

    | Inputs | Kernels | Toy format | Cases |
    |---|---|---|---|
    | `1` | `split` | `fp:11:-30:10` | 86 015 |
    | `1 1` | `two_sum`, `fast_two_sum`, `add_1_1` | `fp:5:-7:4` | 172 225 |
    | `1 1` | `two_prod`, `two_prod_dekker`, `mul_1_1` | `fp:5:-12:-1` | 172 225 |
    | `r r` | `radd` | `fp:6:-8:4` | 200 704 |
    | `r r` | `rmul` | `fp:6:-13:-2` | 173 056 |
    | `2` | `neg_2`, `abs_2`, the conversions | `fp:6:-8:4` | 118 335 |
    | `2 1`, `1 2` | `add_2_1`, the subtractions, the comparisons | `fp:4:-4:2` | 221 361 |
    | `2 1` | `mul_2_1` | `fp:4:-8:-2` | 221 361 |
    | `2 2` | `add_2_2`, `add_fast_2_2`, `sub_2_2`, the comparisons | `fp:3:-3:2` | 178 929 |
    | `2 2` | `mul_2_2` | `fp:4:-7:-3` | 245 025 |
    | `2 c` | `mul_pow2_2` | `fp:5:-6:2` | 144 755 |
    | `1 r` | `ball_neg_1` | `fp:5:-7:4` | 86 320 |
    | `2 r` | `ball_neg_2` | `fp:4:-4:2` | 111 552 |
    | `1 r 1` | `ball_scale_1` | `fp:3:-5:0` | 84 700 |
    | `2 r 1` | `ball_scale_2` | `fp:2:-4:1` | 60 102 |
    | `1 r 1 r` | `ball_add_1`, `ball_sub_1` | `fp:2:-3:1` | 76 176 |
    | `1 r 1 r` | `ball_mul_1` | `fp:2:-4:0` | 76 176 |

- **Restricted enumerations.** The two-limb balls with two operands have far too many operand
  combinations at their minimum precision (140 million for `ball_add_2` at `fp:3:-3:2`, 12.4
  billion for `ball_mul_2` at `fp:4:-5:1`). Their `interp-restricted` test enumerates every
  operand of a domain restricted by the oracle's `--restrict`, and says so in its report
  ("complete over a RESTRICTED domain"); their `interp-sampled` test runs 20 000 random cases of
  the whole format from every stratum of the ball family.

    | Kernels | Toy format | Restricted to | Cases |
    |---|---|---|---|
    | `ball_add_2`, `ball_sub_2` | `fp:3:-3:2` | both radii in {0, 1/8, 1/2, 5/2}, `cx` in [1/2, 2) | 148 896 |
    | `ball_mul_2` | `fp:4:-5:1` | both radii in {0, η, 3/2}, `cx` in [1, 2), `cy` in [1/8, 2) | 64 728 |

- **Non-finite results.** A claim says nothing about a case whose leading output limb is not
  finite, so the oracle does not judge such a case; a runner that returned NaN for everything
  would pass. The cross-checks therefore pass `--fail-on-suspicious`, which fails a non-finite
  result whose operands and exact value are all far below the overflow threshold. The exceptions
  are `split` and `two_prod_dekker`, whose multiplication by the splitter overflows for such
  operands, as their requirement of no intermediate overflow allows; for them the guards below
  stand guard.

### What a pass requires

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

`crosscheck.guards` runs pipelines that the oracle passes but these guards must fail (a partial
enumeration, a restricted one passed off as complete, missing strata, nothing judged, a comparison
that was never true), and summaries altered where no stream can produce the fault.

### Packed kernels

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

### Contraction

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
`-ffp-contract=off` and `on` and fails 14 148 of 20 000 binary64 cases with `=fast`.

### Hardware FMA

The kernels assume that an FMA is one rounding done by the hardware, and on x86-64 the headers
refuse to compile without it. The tests' runners link `kairn::fma`, which adds `-mfma` (GCC and
Clang) or `/arch:AVX2` (MSVC and clang-cl) when the build's flags do not already enable FMA; see
[Getting started](../getting-started/index.md#hardware-fma).

### Time

About two minutes with `--parallel 4` on a recent machine: 110 to 133 seconds on an Apple M3 Max,
with Apple clang or GCC 16, for 742 tests whose times add up to about 490 seconds. Elsewhere, as
measured: 271 seconds on 16 cores of a 2019 x86-64 server and 453 seconds on 4 of them; with
MSVC, 369 seconds on 8 logical processors of a Windows machine and 533 seconds on 4. On the Mac a
cross-check of a compiled runner takes 0.3 to 0.6 seconds, one of the interpreter 1 to 7 seconds,
and the generator's and the oracle's own tests about 45 seconds each. `KAIRN_CROSSCHECK_CASES`
sets the share of the compiled runners, about three fifths of the total.

## The generator's tier

`python3 gen/kairn-gen test` is the generator's own suite (`gen/README.md`, "The tests"). About
two thirds of its time goes to its C++ tests, which build the generated code at `-O0` and
`-O2`, with and without `-frounding-math`, under every contraction setting, and require every
build, scalar and packed, to be bit-identical to the interpreter, with special operands in every
lane. In the quick tier it runs without them (`--no-cxx`): with them it took 148 seconds on its
own on the machine above, longer than the rest of `ctest` together, and the cross-checks already
compile the same code with the build's compiler and flags. The whole suite runs in the workflow
`generator.yml`, once per GCC-style compiler of the CI, and by hand:

```sh
python3 gen/kairn-gen test                  # c++ and g++-16, those that exist
python3 gen/kairn-gen test --cxx clang++    # another compiler
python3 gen/kairn-gen test --full           # a few hundred thousand cases per kernel
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

Four workflows under `.github/workflows/`, each on pushes to `main` and on pull requests, one run
per branch at a time (a new push cancels the run in progress):

| Workflow | Jobs |
|---|---|
| `build.yml`, "Build and test" | Configure, build and `ctest` with Ninja, `Release` and warnings as errors, on Linux x86-64 with GCC and with Clang (packed: AVX2), macOS arm64 with Apple clang (NEON), and Windows x64 with MSVC and with clang-cl (AVX2) |
| `generator.yml`, "Generator's full suite" | `python3 gen/kairn-gen test --cxx CXX`, C++ included, on Linux x86-64 with GCC and with Clang, and macOS arm64 with Apple clang |
| `proofs.yml`, "Proofs" | `make -C proofs` in the Rocq team's image `rocq/rocq-prover:9.0` (Rocq 9.0.1), with Flocq 4.2.2 from opam, cached between runs |
| `checks.yml`, "Generated files and documentation" | `gen/kairn-gen check`, `docs/tools/reference.py --check` and its tests, `mkdocs build --strict`, `docs/tools/check_links.py` |
