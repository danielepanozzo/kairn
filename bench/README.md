# Benchmarks

The harness behind [Benchmarks, Milestone 1](../docs/developer/results/bench-milestone1.md). It
times the generated kernels of `include/kairn/gen/` next to measurement props that exist only
here, and answers four questions: what the opaque product costs, what the fix-up for non-finite
results costs, what a `Ball` operation costs, and how Kairn compares with textbook double-word
arithmetic. No external benchmark library; MPFR is timed for scale when it is already installed.

Nothing here is part of the library. The props (`props.hpp`, `props_packed.hpp`) are not
verified and must not be used elsewhere.

## Build

`KAIRN_BUILD_BENCHMARKS` (default `OFF`) adds this directory. With GCC, Clang or Apple clang it
builds `kairn-bench-O2` and `kairn-bench-O3`; with MSVC, `kairn-bench-O2` (`/O2`). Every file
links `kairn::fma`, so the scalar code gets hardware FMA exactly as a client's would (`-mfma` on
x86-64, `/arch:AVX2` with MSVC, nothing on AArch64); `packed.cpp` is also compiled with
`-mavx2 -mfma` on x86-64. Everything is compiled without contraction (`-ffp-contract=off`;
MSVC's `/fp:precise` does not contract): the props with a plain multiplication need it, and the
generated kernels contain no plain multiplication for it to change. Never `-ffast-math` or
`/fp:fast`.

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
taskset -c 56 build-bench/bench/kairn-bench-O2 --cpu 56 --reps 31 \
    --machine "Linux x86-64, AMD EPYC 7452 (Zen 2); one logical CPU, its SMT sibling idle" \
    --commit "$(git rev-parse --short HEAD)" --json results/milestone1/bench/linux-gcc-O2.json
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

A run takes 15 to 30 seconds. On a shared machine, pin to a core whose SMT sibling is idle and
check with `mpstat` (Linux) or `typeperf` (Windows) that it stays so.

What one run does:

1. **Inputs**, at run time from a fixed seed, the same with every compiler: 256 normalized
   2-limb numbers per operand, leading limbs $\pm[1, 2) \cdot 2^k$ with $k \in [-8, 8]$, tails
   about $2^{-53}$ of them; radii about $2^{-80}$ of the centers; factors in
   $[2^{-1/4}, 2^{1/4})$ for products; Horner coefficients with $k \in [-2, 2]$ and argument
   about $0.8$. Nothing overflows or underflows in a timed loop (the one subnormal operand is
   the constant $V$ of `ball_mul_k`, added once per call). Nine arrays of 2 KB fit in any L1.
2. **Checks**, before anything is timed: every function against the generated kernel on these
   inputs, bit for bit (MPFR within $2^{-100}$ for one operation and $2^{-90}$ for a chain); and
   the forms of the full kernels against each other, and packed against scalar, on 8192
   random and special operands per kernel (infinities, NaN, sums and products that overflow),
   bit for bit apart from NaN payloads and the sign of zeros, with the result canonical and,
   for the 2-limb kernels, F4 and F5 of `docs/developer/design/milestone1.md` checked. A
   failed check stops the run.
3. **Timing**: each function is calibrated to samples of about 4 ms; then rounds over all
   functions, one sample each per round, so that a disturbance spreads over all of them. The
   JSON has the minimum, median and maximum time per operation. Ratios on the results page are
   of minimum times.

## The functions

A function's name is `BACKEND/KIND/KERNEL/VARIANT`:

- `BACKEND`: `scalar` (the loop of `scalar.hpp` kernels, which the compiler may vectorize),
  `packed` (`avx2.hpp` or `neon.hpp`, one number per lane), `mpfr`.
- `KIND`: `tp`, independent operations over the arrays, time per operation; `sum`, `prod`,
  `horner`, a dependent chain (a running sum, a running product of factors near 1, a Horner
  evaluation), time per step. A packed chain runs one chain per lane.
- `VARIANT`: `kairn`, the generated kernel; `plain`, the same with every opaque product written
  `a * b`; `full_sel` and `full_br`, the full kernels of milestone1.md as listed with selects
  and with a branch and the fix-up out of line; `full_fabs` and `full_inl`, variants of these
  that test two explanations (`std::fabs` in place of `abs_bits`; the fix-up inline);
  `textbook`, double-word arithmetic written from the listings of Joldes, Muller and Popescu
  (2017); `double`, one `double` operation; `mpfr`, MPFR at 106 bits.

Each is a non-inlined function with C linkage named `kb_KIND_KERNEL__VARIANT` (`kb_ptp_...` and
so on for packed code), so that its loop can be found in a disassembly.

## Machine code

```sh
objdump -d --no-show-raw-insn build-bench/bench/kairn-bench-O2 \
    | python3 bench/asm_summary.py --json results/milestone1/bench/asm-linux-gcc-O2.json
dumpbin /disasm:nobytes build-bench\bench\CMakeFiles\kairn-bench-O2.dir\scalar.cpp.obj ^
    build-bench\bench\CMakeFiles\kairn-bench-O2.dir\packed.cpp.obj ^
    | python bench\asm_summary.py --json results\milestone1\bench\asm-windows-msvc-O2.json
```

`asm_summary.py` finds the loops of every timed function and counts, per loop, fused
multiply-adds, multiplications, additions, comparisons, selects, mask logic, branches and calls,
and the width of the registers the arithmetic uses (scalar, 128 or 256 bits).

## Tables

```sh
python3 bench/report.py results/milestone1/bench
```

prints the tables of the results page from the stored JSON.
