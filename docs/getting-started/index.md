# Getting started

**Kairn is in development, and nothing in it should be relied on yet.** Milestone 1 is in
progress: the first public headers exist, for numbers of one and two limbs of type `float` or
`double` and for balls around them, and the claims of all their operations have checked proofs in
a model of arithmetic where nothing overflows. What happens at overflow is proved for some
operations only, and the treatment of infinities and NaN is not written yet;
[What holds today](guarantees.md) has the details. This page shows how to build and test the
repository, write a first program, use the CMake package, and build this site.

## A first program

Include `kairn/kairn.hpp`, and call `kairn::self_test()` once at startup: it checks, with the
flags your program was compiled with, that the arithmetic behaves as Kairn's proofs assume, and
says why if it does not.

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:include"

--8<-- "docs/examples/cpp/first_steps.cpp:self_test"
```

`kairn::Expansion<double, 2>` stores a value as the exact sum of two `double`s, its *limbs*: about
106 significant bits instead of 53. Its operations have proved error bounds, which `kairn::traits`
exports as constants:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:expansion"
```

A `kairn::Ball` is a set: a center and a radius, and every operation returns a ball that contains
every result of the operation on points of its operands:

```cpp
--8<-- "docs/examples/cpp/first_steps.cpp:ball"
```

An operation whose proof is not checked compiles only with the marker `kairn::unverified` on one
of its operands; [What holds today](guarantees.md#proved-and-unverified) says which operations
those are.

The whole program is
[`docs/examples/cpp/first_steps.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/first_steps.cpp);
ctest builds and runs it (`api.example.first_steps`), and it checks the values it prints. To build
your own program, link `kairn::kairn` and `kairn::fma` ([Use it from CMake](#use-it-from-cmake)).
Next, the tutorial [Accurate sums and dot products](../tutorials/accurate-sums.md) puts these
types to work, and the [reference](../reference/index.md) has a page for every operation.

## What you need

- CMake 3.21 or later and a C++20 compiler.
- On x86-64, a CPU with FMA (Intel Haswell, AMD Piledriver or later) to run the kernels and their
  tests ([Hardware FMA](#hardware-fma)), and with AVX2 too (Intel Haswell, AMD Excavator or
  later) for the tests of the packed kernels.
- Python 3, for the generator's and the oracle's tests and for building the site. Building Kairn
  as a client will never need it ([Architecture](../developer/architecture.md#layout-and-ownership)).

## Configure, build and test

From the repository root:

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

Built on its own, Kairn defaults to a `Release` build, because its contraction tests check what an
optimizing compiler does. With a multi-configuration generator (Visual Studio, Xcode), name the
configuration instead: `cmake --build build --config Release` and `ctest --test-dir build -C
Release --output-on-failure`. Add `--parallel N` to both of the last two commands to use N cores;
with four, the whole run takes about two minutes on a recent machine.

The tests:

| Test | Checks |
|---|---|
| `kairn-gen.check` | `python3 gen/kairn-gen check`: every committed generated file is what the generator writes. |
| `kairn-gen.test` | `python3 gen/kairn-gen test --no-cxx`: the generator's own tests, without those that compile C++, which take longer than everything else together; run `python3 gen/kairn-gen test` for all of them. |
| `kairn-oracle.selftest` | `python3 oracle/kairn-oracle selftest --quick`: the oracle's own tests, including injected errors that it must catch. |
| `kairn-oracle.claims` | `python3 oracle/kairn-oracle check --claims-only`: the oracle can read every claim in `gen/claims.json`. |
| `docs.reference.check`, `docs.reference.test` | `python3 docs/tools/reference.py --check`: the reference pages of this site are what the script writes from the claims and the stored results; and the script's own tests. |
| `crosscheck.interp.*` | Each kernel, run by the generator's interpreter on every operand of a small format, judged by the oracle against its claims. |
| `crosscheck.interp-restricted.*`, `crosscheck.interp-sampled.*` | For the kernels with too many operands for that (the two-limb balls), every operand of a restricted domain of a small format, and random operands of the whole format. |
| `crosscheck.cxx.*` | Each kernel, compiled with the build's compiler and flags, on random `binary64` and `binary32` operands, judged by the oracle. |
| `crosscheck.neon.*`, `crosscheck.avx2.*` | The same for the packed kernels, NEON on AArch64 and AVX2 on x86-64, one operand per lane. |
| `crosscheck.cxx-*.*`, `crosscheck.neon-*.*`, `crosscheck.avx2-*.*` | The same, under each contraction setting that matters to the compiler. |
| `crosscheck.guards` | The cross-checks fail when they check less than they say: an incomplete enumeration, a missing stratum, nothing judged. |
| `consume.add_subdirectory` | A CMake project that adds Kairn with `add_subdirectory` and links `kairn::kairn` and `kairn::fma` builds, compiles as C++20, and runs a kernel. |
| `consume.install` | `cmake --install` of the build tree into a prefix inside the build directory. |
| `consume.find_package` | A CMake project that finds that installed copy with `find_package(kairn)` builds, compiles as C++20, and runs a kernel. |
| `api.oracle.*` | Each public operation, computed through the operators and functions of `kairn/kairn.hpp`, on random `binary64` and `binary32` operands, judged by the oracle against the claims of its kernel; also with contraction forced on (`.contract-fast`). |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is computed by some public operation or listed as internal to others. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, and the same results at run time. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass, and each detects a changed rounding mode and flush-to-zero. |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break Kairn and define no macro; `kairn::self_test()` must report a failure. |
| `api.reject.*` | What must not compile: the flags `config.hpp` rejects, and each kind of operation written without the marker while its kernel is UNVERIFIED (against a copy of the headers in which every kernel is). |
| `api.boundary.*` | A product the program computes and passes into an operation (`x + a * b`, a constructor, `from_limbs`, a ball's center or radius) gives, bit for bit, the result of the same operation on the rounded product, under each contraction setting; `api.boundary.unguarded.*` checks that without the guard the compilers that fuse across statements do change it. |
| `api.k1.zero_cost` | The instructions emitted for loops over `Expansion<double, 1>` against the same loops over `double`. |
| `api.example.*` | The examples of this site, which check their own output; the tutorial's, under each contraction setting, against the output its page shows. |

`ctest -L api` runs only the tests of the public interface. [Testing](../developer/testing.md)
explains the cross-checks, how to run one by hand, and how to rerun one failing case. The entry points of the
[Architecture](../developer/architecture.md#layout-and-ownership) page and the cross-checks are
registered only if Python 3 is found, and each entry point only if its script exists when CMake
runs; configuring prints which were registered. The consumer checks build with the same generator
and compiler as the main build.

Tests are on by default when Kairn is the top-level project and off when another project adds it;
the option `KAIRN_BUILD_TESTS` overrides that.

## Use it from CMake

`kairn::kairn` is an `INTERFACE` target: it adds `include/` to the include path and requires
C++20, and there is nothing to compile. Its headers today:

| Header | Content |
|---|---|
| `kairn/kairn.hpp` | All of the following. |
| `kairn/expansion.hpp` | `kairn::Expansion<T, 1>` and `kairn::Expansion<T, 2>`, `T` = `float` or `double`, and their operations. |
| `kairn/ball.hpp` | `kairn::Ball<T, 1>` and `kairn::Ball<T, 2>`. |
| `kairn/traits.hpp` | `kairn::traits<X>`: limb type, number of limbs, precision, and the error constants of the proved operations. |
| `kairn/environment.hpp` | `kairn::self_test()` and `kairn::environment_ok()`. |
| `kairn/config.hpp` | The checks of the compiler's flags, the marker `kairn::unverified`, and the macros `KAIRN_CHECKS`, `KAIRN_ENVIRONMENT_FAILURE`, `KAIRN_K1_CONTRACT`. |
| `kairn/version.hpp` | `KAIRN_VERSION_MAJOR`, `KAIRN_VERSION_MINOR`, `KAIRN_VERSION_PATCH`, `KAIRN_VERSION_STRING` and `KAIRN_VERSION` (configuring fails if they disagree with the version in `CMakeLists.txt`). |
| `kairn/gen/` | The generated kernels and data the headers above use; not an interface to call directly. |

A project can add the source tree (directly, or through `FetchContent`), as the
`consume.add_subdirectory` test does, with `KAIRN_SOURCE_DIR` the path of the checkout:

```cmake
--8<-- "tests/consume/add_subdirectory/CMakeLists.txt"
```

Or it can install Kairn first, with `cmake --install build --prefix PREFIX`, and find it with
`PREFIX` in `CMAKE_PREFIX_PATH`, as the `consume.find_package` test does:

```cmake
--8<-- "tests/consume/find_package/CMakeLists.txt"
```

The installed package accepts a request for a version with the same major and minor number that is
not newer than itself.

## Hardware FMA

Every kernel assumes that a fused multiply-add is one rounding done by the hardware. On x86-64 the
headers therefore refuse to compile unless the compiler targets a CPU with FMA, with the error
"Kairn needs hardware FMA". AArch64 always has it.

`kairn::kairn` does not choose the instruction set for you: which CPUs a program runs on is the
program's decision, and an option carried by `kairn::kairn` would apply to every file of every
target that links it. Either compile for such a CPU yourself (`-march=x86-64-v3` or `-mfma` with
GCC and Clang, `/arch:AVX2` with MSVC and clang-cl), or also link `kairn::fma`, as the examples
above do. `kairn::fma` adds that option for the compiler of your project, or nothing when your
flags already enable FMA or the target needs no option; configuring prints a line when it adds
one. Kairn's own tests link it.

## Build the documentation

```sh
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve
```

The site is then at <http://127.0.0.1:8000>. [Documentation](../developer/documentation.md) has the
rest: the strict build, the link checker and how pages are written.
