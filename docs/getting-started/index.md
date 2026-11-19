# Getting started

**The library does not exist yet.** Milestone 1 has started, no operation is proved yet, and
nothing in the repository should be relied on. What can be done with it today is to configure it
with CMake, run its tests, install the CMake package (which holds only a version header), and
build this site.

## What you need

- CMake 3.21 or later and a C++20 compiler.
- Python 3, for the generator's and the oracle's tests and for building the site. Building Kairn
  as a client will never need it ([Architecture](../developer/architecture.md#layout-and-ownership)).

## Configure, build and test

From the repository root:

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

The tests:

| Test | Checks |
|---|---|
| `kairn-gen.check` | `python3 gen/kairn-gen check`: every committed generated file is what the generator writes. |
| `kairn-gen.test` | `python3 gen/kairn-gen test`: the generator's own tests. |
| `kairn-oracle.selftest` | `python3 oracle/kairn-oracle selftest`: the oracle's own tests, including injected errors that it must catch. |
| `consume.add_subdirectory` | A CMake project that adds Kairn with `add_subdirectory` and links `kairn::kairn` builds, compiles as C++20, and runs. |
| `consume.install` | `cmake --install` of the build tree into a prefix inside the build directory. |
| `consume.find_package` | A CMake project that finds that installed copy with `find_package(kairn)` builds, compiles as C++20, and runs. |

The first three run the entry points of the [Architecture](../developer/architecture.md#layout-and-ownership)
page. Each is registered only if its script exists when CMake runs and Python 3 is found, and
configuring prints one line saying which were registered and which scripts are not there yet;
configure again after one is added. The consumer checks build with the same generator and compiler
as the main build.

Tests are on by default when Kairn is the top-level project and off when another project adds it;
the option `KAIRN_BUILD_TESTS` overrides that.

## Use it from CMake

`kairn::kairn` is an `INTERFACE` target: it adds `include/` to the include path and requires
C++20, and there is nothing to compile. Its only header today is `kairn/version.hpp`, which defines
`KAIRN_VERSION_MAJOR`, `KAIRN_VERSION_MINOR`, `KAIRN_VERSION_PATCH`, `KAIRN_VERSION_STRING` and
`KAIRN_VERSION`; configuring fails if they disagree with the version in `CMakeLists.txt`.

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

## Build the documentation

```sh
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve
```

The site is then at <http://127.0.0.1:8000>. [Documentation](../developer/documentation.md) has the
rest: the strict build, the link checker and how pages are written.
