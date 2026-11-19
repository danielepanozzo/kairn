# Kairn

Rigorous floating-point expansions ("k-numbers") with interval and ball arithmetic, in
header-only C++20. Every error bound is meant to carry a machine-checked proof, and the shipped
code is generated from the same source the proofs are about.

**Status: Phase 0 (specification and feasibility) is complete and reviewed. Milestone 1 is in progress,
and nothing here should be relied on yet.** The first public headers exist: `kairn/kairn.hpp`, with
`kairn::Expansion<T, 1>`, `kairn::Expansion<T, 2>` and `kairn::Ball<T, 1>`, `kairn::Ball<T, 2>` for
`T` = `float` or `double`. [What holds today](docs/getting-started/guarantees.md) says which of
their statements are proved and what is not written yet.

- [Phase 0 report](docs/developer/design/phase0/index.md): what Kairn will be, what was measured,
  and the decisions taken at its review.
- [Experiments](experiments/phase0/README.md) behind the report.
- [The original brief](docs/developer/design/brief.md).

## Build and test

Needs CMake 3.21 or later and a C++20 compiler, and on x86-64 a CPU with FMA; the tests also need
Python 3. From the repository root:

```sh
cmake -S . -B build                      # Release unless CMAKE_BUILD_TYPE says otherwise
cmake --build build
ctest --test-dir build --output-on-failure
cmake --install build --prefix PREFIX    # optional: then find_package(kairn) with PREFIX in CMAKE_PREFIX_PATH
```

With Visual Studio or Xcode, add `--config Release` to the build and `-C Release` to `ctest`. The
tests take a few minutes: the generator's and the oracle's own tests, cross-checks in which the
oracle judges every kernel, run by the generator's interpreter on every operand of a small format
and compiled on random `binary64` and `binary32` operands, under each contraction setting of the
compiler, and the tests of the public interface, whose every operation the oracle judges too. They
are listed in [Getting started](docs/getting-started/index.md#configure-build-and-test) and
explained in [Testing](docs/developer/testing.md).

The CMake target `kairn::kairn` holds the headers; a program includes `kairn/kairn.hpp`
([a first program](docs/getting-started/index.md#a-first-program)). On x86-64 the kernels need
hardware FMA: compile for such a CPU, or also link `kairn::fma`, which adds the option for your
compiler ([Hardware FMA](docs/getting-started/index.md#hardware-fma)).

## Documentation

The site is built with MkDocs from `docs/` ([how](docs/developer/documentation.md)):

```sh
python3 -m venv .venv
.venv/bin/pip install -r docs/requirements.txt
.venv/bin/mkdocs serve             # http://127.0.0.1:8000
.venv/bin/mkdocs build --strict    # writes site/
python3 docs/tools/check_links.py
```

License: MIT.
