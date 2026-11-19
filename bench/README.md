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
