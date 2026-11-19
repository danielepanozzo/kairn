# Getting started

**The library does not exist yet.** Milestone 1 has started: the first kernels are generated and
some of their proofs are checked, but there is no public interface, and nothing in the repository
should be relied on. What can be done with it today is to configure it with CMake, run its tests,
install the CMake package, and build this site.

## What you need

- CMake 3.21 or later and a C++20 compiler.
- On x86-64, a CPU with FMA (Intel Haswell, AMD Piledriver or later) to run the kernels and their
  tests ([Hardware FMA](#hardware-fma)).
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
the whole run takes one to two minutes.

The tests:

| Test | Checks |
|---|---|
| `kairn-gen.check` | `python3 gen/kairn-gen check`: every committed generated file is what the generator writes. |
| `kairn-gen.test` | `python3 gen/kairn-gen test`: the generator's own tests, compiling the C++ with the build's compiler (skipped for MSVC and clang-cl). |
| `kairn-oracle.selftest` | `python3 oracle/kairn-oracle selftest --quick`: the oracle's own tests, including injected errors that it must catch. |
| `kairn-oracle.claims` | `python3 oracle/kairn-oracle check --claims-only`: the oracle can read every claim in `gen/claims.json`. |
| `crosscheck.interp.*` | Each kernel, run by the generator's interpreter on every operand of a small format, judged by the oracle against its claims. |
| `crosscheck.cxx.*` | Each kernel, compiled with the build's compiler and flags, on random `binary64` and `binary32` operands, judged by the oracle. |
| `crosscheck.cxx-*.*` | The same, under each contraction setting that matters to the compiler. |
| `consume.add_subdirectory` | A CMake project that adds Kairn with `add_subdirectory` and links `kairn::kairn` and `kairn::fma` builds, compiles as C++20, and runs a kernel. |
| `consume.install` | `cmake --install` of the build tree into a prefix inside the build directory. |
| `consume.find_package` | A CMake project that finds that installed copy with `find_package(kairn)` builds, compiles as C++20, and runs a kernel. |

[Testing](../developer/testing.md) explains the cross-checks, how to run one by hand, and how to
rerun one failing case. The entry points of the
[Architecture](../developer/architecture.md#layout-and-ownership) page and the cross-checks are
registered only if Python 3 is found, and each entry point only if its script exists when CMake
runs; configuring prints which were registered. The consumer checks build with the same generator
and compiler as the main build.

Tests are on by default when Kairn is the top-level project and off when another project adds it;
the option `KAIRN_BUILD_TESTS` overrides that.

## Use it from CMake

`kairn::kairn` is an `INTERFACE` target: it adds `include/` to the include path and requires
C++20, and there is nothing to compile. Its headers today are `kairn/version.hpp`, which defines
`KAIRN_VERSION_MAJOR`, `KAIRN_VERSION_MINOR`, `KAIRN_VERSION_PATCH`, `KAIRN_VERSION_STRING` and
`KAIRN_VERSION` (configuring fails if they disagree with the version in `CMakeLists.txt`), and the
generated kernels under `kairn/gen/`, which are not yet an interface to rely on.

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
