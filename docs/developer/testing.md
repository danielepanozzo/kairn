# Testing

How Kairn's code is tested, what each test is for, and how to rerun one case of a failing test
by hand. The parts named here (generator, interpreter, oracle, runner, claims) are described in
[Architecture](architecture.md#the-pipeline).

## The tiers

| Tier | What | Where it runs | Time |
|---|---|---|---|
| Quick | `ctest`: the generator's and the oracle's own tests, the cross-checks below, the consumer checks | every push and pull request, on every platform of the CI; and by anyone, with the three commands of [Getting started](../getting-started/index.md#configure-build-and-test) | one to two minutes |
| Proofs | `make -C proofs`: every Rocq proof, then the axiom audit | every push and pull request | a minute or two, with four cores |
| Brute force | `kairn-oracle brute`: long random runs, and exhaustive runs on larger toy formats, with a time budget | by hand, for now (`oracle/README.md`) | as long as it is given |

A kernel's claims are only as good as the tests that could have refuted them, so every cross-check
fails when it checked nothing: when the oracle judged no case, when an exhaustive run did not
cover the whole enumeration, or when a random run missed a stratum.

## The quick tier

The tests that `ctest` runs, by name:

| Test | Checks |
|---|---|
| `kairn-gen.check` | Every committed generated file is what `python3 gen/kairn-gen build` writes. |
| `kairn-gen.test` | The generator's own tests. Its C++ tests compile with the build's compiler; with MSVC and clang-cl they are skipped, since they pass GCC-style options. |
| `kairn-oracle.selftest` | The oracle's own tests (`--quick`), including injected errors it must catch. It compiles its own C++ reference runner with the build's compiler; if that fails, the test fails. |
| `kairn-oracle.claims` | The oracle can read every claim in `gen/claims.json`. |
| `crosscheck.interp.K` | Kernel K run by the generator's interpreter on **every** operand combination of a toy format. |
| `crosscheck.cxx.K.F` | Kernel K compiled with the build's compiler and flags, on random cases of format F (`binary64`, `binary32`) from every stratum. |
| `crosscheck.cxx-S.K.F` | The same, compiled with the contraction setting S added to the flags (below). |
| `consume.*` | A CMake project that uses Kairn through `add_subdirectory`, and one through `find_package` after `cmake --install`, build and run a kernel. |

Labels select groups: `ctest -L crosscheck`, `ctest -L contraction`, `ctest -L interp`; `-R` selects
by name, for example `ctest -R mul_2_2`.

### Cross-checks

A cross-check is one pipeline: the oracle writes requests, a runner completes them, and the oracle
judges every completed line against the kernel's claims in exact arithmetic
([the line protocol](architecture.md#the-line-protocol)). The test prints the oracle's report,
pass or fail; on failure it also prints the command that reruns one case (below).

- **Every kernel** in `gen/claims.json` gets its tests: adding a kernel to the generator adds them.
- **The toy formats** depend on the kernel's operands, so that each enumeration is 50 000 to
  250 000 cases. Products use a range below 1, so that most products neither overflow nor vanish.
  The table is in `tests/CMakeLists.txt`; a kernel whose minimum precision is above its toy
  format's gets a test that fails and says so, rather than a run where nothing is claimed.

    | Operands | Sums | Products |
    |---|---|---|
    | one limb (`split`) | `fp:11:-30:10` | |
    | one limb and one limb | `fp:5:-7:4` | `fp:5:-12:-1` |
    | two limbs and one limb | `fp:4:-4:2` | `fp:4:-8:-2` |
    | two limbs and two limbs | `fp:3:-3:2` | `fp:4:-7:-3` |

- **Random cases**: 20 000 per kernel and format (`KAIRN_CROSSCHECK_CASES`), seed 0
  (`KAIRN_CROSSCHECK_SEED`), so that a run is the same everywhere and can be repeated.
- **Non-finite results.** A claim says nothing about a case whose leading output limb is not
  finite, so the oracle does not judge such a case; a runner that returned NaN for everything
  would pass. The cross-checks therefore pass `--fail-on-suspicious`, which fails a non-finite
  result whose operands and exact value are all far below the overflow threshold. The exceptions
  are `split` and `two_prod_dekker`, whose multiplication by the splitter overflows for such
  operands, as their requirement of no intermediate overflow allows; for them only the "nothing
  judged" check stands guard.

### Contraction

A compiler may fuse a product and an addition into one FMA ("contraction"), which changes the
result. In Phase 0 that broke the textbook double-word product under some settings
([Environment](design/phase0/environment.md#contraction)); the generator's rules R1 and R2 are
meant to make every kernel immune. The contraction tests check that the compiled kernels still
satisfy their claims under each setting that matters to the compiler:

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

## A cross-check by hand

From the repository root, a toy format with the interpreter, and binary64 with a compiled runner
from a build tree:

```sh
python3 oracle/kairn-oracle gen mul_2_2 fp:4:-7:-3 --exhaustive \
  | python3 gen/kairn-gen interp | python3 oracle/kairn-oracle check

python3 oracle/kairn-oracle gen mul_2_2 binary64 --seed 0 --count 20000 \
  | build/tests/kairn-gen-runner | python3 oracle/kairn-oracle check --fail-on-suspicious
```

`check` exits with 1 on any violated claim, invalid case or broken stream, and its report lists
the worst cases with their tags. `--verbose` adds the profile of the error by distance from the
underflow range; `--json FILE` writes everything. A toy format below a kernel's minimum precision
is not judged unless `check` is given `--ignore-min-precision`.

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

and for an exhaustive case, `--exhaustive --start INDEX --count 1`. A failing cross-check prints
this command with its own runner and arguments filled in. The request line alone is also a valid
input: `echo 'add_2_2 binary64 ... #extreme:462' | build/tests/kairn-gen-runner` shows the result
without the oracle, and `python3 gen/kairn-gen interp` the exact one.

## Continuous integration

Three workflows under `.github/workflows/`, each on pushes to `main` and on pull requests, one run
per branch at a time (a new push cancels the run in progress):

| Workflow | Jobs |
|---|---|
| `build.yml`, "Build and test" | Configure, build and `ctest` with Ninja, `Release` and warnings as errors, on Linux x86-64 with GCC and with Clang, macOS arm64 with Apple clang, and Windows x64 with MSVC and with clang-cl |
| `proofs.yml`, "Proofs" | `make -C proofs` in the Rocq team's image `rocq/rocq-prover:9.0` (Rocq 9.0.1), with Flocq 4.2.2 from opam, cached between runs |
| `checks.yml`, "Generated files and documentation" | `gen/kairn-gen check`, `mkdocs build --strict`, `docs/tools/check_links.py` |
