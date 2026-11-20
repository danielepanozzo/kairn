# Benchmarks

The harness behind [Benchmarks, Milestone 1](../docs/developer/results/bench-milestone1.md). It
times what a client gets, the generated kernels of `include/kairn/gen/` and the public operators of
`kairn::Expansion` and `kairn::Ball`, next to a few measurement props that exist only here, and
answers five questions: what the opaque product costs, what the fix-up for non-finite results
costs, what a `Ball` operation costs, how Kairn compares with textbook double-word arithmetic, and
how `float` limbs compare with `double` limbs. No external benchmark library; MPFR is timed for
scale when it is already installed.

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
compilation has a timeout, and on a timeout only the process the script started is terminated.

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
