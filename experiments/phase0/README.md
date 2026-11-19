# Phase 0 experiments

The measurements behind the [Phase 0 report](../../docs/developer/design/phase0/index.md). Each
directory has its sources, a script that reruns it, and the output recorded on 2026-11-18. Nothing
here is library code: `constexpr/proto.hpp` is a throwaway prototype.

Machines: an Apple M3 Max (macOS 26, Apple clang 21, Homebrew GCC 16); a Linux server (EPYC 7452, GCC 13,
Clang 18, CUDA 13.2, RTX A5000 and RTX 6000 Ada, Docker); a Linux workstation (Threadripper 3995WX, CUDA 13.2,
GeForce RTX 3080 Ti); a Windows machine (Windows 11, Visual Studio 2026 Build Tools, MSVC 19.52).

| Directory | Question | Rerun |
|---|---|---|
| `contraction/` | What does FMA contraction do to a double-word product written five ways? Results are checked against exact rationals by `check.py`; `count_fma.sh` counts fused instructions per function. | `./matrix_macos.sh`, `./matrix_linux.sh`, `matrix_windows.bat` |
| `flags/` | Which predefined macros reveal each floating-point flag? | `./macros.sh COMPILER [FLAGS]` |
| `constexpr/` | One function body for constant evaluation and run time: same bits? Also under `-frounding-math`, on MSVC, under nvcc. | `./run.sh COMPILER FLAGS...` |
| `k1/` | Does `Expansion<double, 1>` compile to the instructions of `double`? `compare.py` compares the listings; `k1_layout.cpp` and `k1_gs.cpp` are the MSVC follow-ups. | `./run.sh COMPILER FLAGS...` |
| `cuda/` | Host, device and constant evaluation agree? Subnormals, directed-rounding intrinsics, and `float` against `double` throughput. Includes `../constexpr/proto.hpp`. | `nvcc -std=c++20 -O3 cuda_test.cu && ./a.out`; same for `bench_fp.cu` |
| `metal/` | Rounding, subnormals, fusion and reassociation on a Metal device under each math mode, with and without scoped pragmas. | `swiftc -O probe.swift && ./probe` |
| `tracer/` | The single-source pipeline in miniature: kernel descriptions to a Rocq model and C++, proofs, axiom audit, exact test. | `./run.sh` (needs Rocq 9 with Flocq 4.2: the `rocq/rocq-prover:9.0` image plus `opam install coq-flocq`) |
| `compile_time/` | Compile time of 8-limb-sized networks under three inlining policies (`run.sh`, `run_msvc.py`), of one network as its size grows (`scaling.py`, `scaling_mul.py`), and as a function template (`scaling_template.py`, `probe2_msvc.py`). | see each script's header |
| `ranges/` | The precision-versus-magnitude tables. | `python3 ranges.py` |

`vs.bat` runs a command inside the Visual Studio developer environment on the Windows machine.
