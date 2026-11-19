# The brute-force tier

`brute.py` runs the quick tier's cross-checks ([testing.md](../../docs/developer/testing.md))
for much longer: the oracle's `gen | RUNNER | check` pipelines, judged by the oracle and held to
the quick tier's guards (`tests/crosscheck_guards.py`). It is run by hand on the test machines,
not in CI. Python 3, standard library only; macOS, Linux and Windows.

Two parts:

- **compiled**: every kernel of `gen/claims.json`, `binary64` and `binary32`, on random cases of
  the oracle's generator (every stratum, one seed per machine), through every runner that the
  CMake builds named by `--build` produce: `kairn-gen-runner*` (scalar) and
  `kairn-gen-packed-runner*` (NEON or AVX2), each with the build's flags and under each
  contraction setting of the quick tier. The quick tier's runners have the compiler's own form
  of the scalar fix-ups of the full kernels and constructors (`KAIRN_GEN_FIXUP_CALL` in
  `include/kairn/gen/prelude.hpp`: a function of its own with Clang on AArch64, inline
  elsewhere); with `--fixup-forms both` (the default) each build `NAME` has a second one,
  `NAME-fixup-call` or `NAME-fixup-inline`, configured with the other form
  (`CXXFLAGS=-DKAIRN_GEN_FIXUP_CALL=1` or `=0`), whose scalar runners run too (the packed kernels
  have no such branch). Cases come in units of `--chunk` (200 000); a unit is
  generated once and judged once per runner, so all the runners of a machine judge the same
  cases. Units are added round-robin over the kernels and formats until the budget is spent.
  `--fail-on-suspicious` everywhere except `split` and `two_prod_dekker`, as in the quick tier.
- **interp**: the generator's interpreter on every operand of the toy formats of the plan, in
  chunks of `--interp-chunk` (500 000) enumeration indices. `python3 tests/brute/brute.py plan`
  prints the plan with the size of every enumeration (`kairn-oracle gen --exhaustive --total`):
  for each kernel, the formats of precision `min_precision` and `min_precision + 1` in the quick
  tier's exponent range (2 and 3 when `min_precision` is 1: the oracle reads no format of
  precision 1), the quick tier's format one and two bits more precise, and other exponent
  ranges; for the two-limb balls with two operands, complete enumerations of formats with fewer
  exponents and larger restricted domains (`SHAPES` and `EXPLICIT` in `brute.py`). For the
  kernels of the extended domain (the non-finite layer) every format has the shape of the
  IEEE-model statements, `qmin + qmax = 3 - 2p`, as in the quick tier, so a format with more
  precision keeps the quick tier's number of exponents rather than its exponent range; their
  enumerations include the non-finite values of every operand. Every constant of a kernel and of
  its callees (the splitter of `split` and `two_prod_dekker`, the constants of the Ball radii) is
  evaluated in each format of the plan with the generator's own code (`gen/kairn_gen/consts.py`);
  a format in which one of them is not a number, which the interpreter would refuse, is replaced
  by the nearest that every one fits (the same precision and number of exponents, the range moved
  up; in the extended domain, two exponents more at a time), and the plan says so. The Ball
  formats are chosen so that a good share of each kernel's complete enumerations ends as a
  finite ball (the comment above `EXPLICIT` has the shares, estimated on samples; `report` prints
  the counts).
  `--interp-bins N --interp-take LIST` splits the plan into N bins of about equal size and runs
  some of them, so that machines can share it.

A pipeline that fails (a violated claim, an invalid case, a suspicious non-finite result where
the quick tier fails on one, a broken stream, a runner or oracle error, a timeout) is a finding:
its series (one kernel, format and runner, or one enumeration) stops, and the finding goes to
`WORK/findings.jsonl` with the oracle's example lines and the command that reruns one of them.

## Commands

```sh
python3 tests/brute/brute.py plan --bins 20               # the enumerations, their sizes, bins
python3 tests/brute/brute.py run --work WORK --budget SECONDS --jobs N [options]
python3 tests/brute/brute.py collect --work WORK --name NAME --out results/milestone1/brute/NAME.json
python3 tests/brute/brute.py report results/milestone1/brute/*.json     # Markdown tables
python3 tests/brute/test_brute.py                         # the driver's own tests
```

`run` configures and builds each `--build NAME=COMPILER` under `WORK/builds/NAME` (Release, with
`--generator` and `--cmake-arg` if given), then runs the parts given by `--part` (default both;
the enumerations first, as they must finish to count). `--jobs` counts busy processes: a compiled
pipeline is one, an interpreter's two. No pipeline starts after `--budget` seconds (counted from
the end of the build); those running finish. `--cpus` and `--nice` confine the driver and
everything it starts; `--env-script` runs everything in the environment a script sets up
(`vcvars64.bat` on Windows).

`run` records the commit of the code under test and of the driver (by default the last commits
that changed `include`, `gen`, `proofs` or `oracle`, and `tests/brute`; a copy of the tree made
with `git archive` has no history, so give them with `--commit` and `--driver-commit`, or `run`
refuses to start), and the wall time of every pipeline (`WORK/times.jsonl`).

`run` is restartable: every finished pipeline leaves the oracle's summary under `WORK`, and
running the same command again starts only what is missing (a larger `--budget` or `--cases`
extends a run). It never leaves processes behind: on SIGINT, SIGTERM or SIGHUP it kills its
pipelines; on Linux they also die with it if it is killed (`PR_SET_PDEATHSIG`); on Windows it and
its pipelines run in a job object that kills them when it ends, however it ends. On macOS a
driver killed with SIGKILL leaves its pipelines to finish their chunk on their own.

`collect` merges each series' summaries with the oracle (`check --merge`), applies
`tests/crosscheck_guards.py` to each merged series (cases 0 to N of the machine's seed, every
stratum, every claim applied, both outcomes of every comparison, ...) and to each enumeration
(complete coverage of exactly the domain asked for), and writes one compact JSON file: the
commits of the code under test and of the driver; per kernel and format its domain (finite or
extended), the counts, the cases per stratum, the seconds spent generating and judging, the
largest error over its bound, the observed constants, the largest `upper` excess and the
smallest Ball radius slack, each with the line that attains it, and per runner its counts and
form of the fix-ups; per enumeration its domain, counts and seconds. It exits 1 if a guard
failed, an enumeration is incomplete or anything was found.

`report` prints, from such files, the tables of the results page: the machines, the throughput
(results per second of wall time, cases per second of one pipeline), the cases per kernel and
format against the aim of 10^8, whether the runners of a machine agreed, the largest error over
its bound per kernel, format and backend, the share of finite balls in each Ball enumeration,
how close each claim came, and per kernel its rows, cases per stratum and the lines that attain
the extremes.

## The runs of Milestone 1

From the repository root of a copy of the tree made with `git archive` (`WORK` a directory
outside it), with 3.5 hours of budget on the Linux machine and 3 hours on the Mac and on Windows.
`CODE` is the commit of the code under test, `6f89054e8e027643001e4d003bdc45aed62a43d8` (its
kernels, generator, interpreter, claims and oracle judge are those of `b7a1fbb`), and `DRIVER`
the commit of the driver the copy was made from, `e226c9e473aa891e78a4ee103348152c273f331e`
(`d619f71715fb1cd21171ecc164552c95c7f2b562` for the Linux run's first ten minutes, below). The
results are in `results/milestone1/brute/` and
[docs/developer/results/brute-milestone1.md](../../docs/developer/results/brute-milestone1.md).

Linux x86-64 (AMD EPYC 7452, GCC 13 and Clang 18; socket 0, 64 of its 128 hardware threads;
`CLANG` is a `clang++` that finds GCC 13's libstdc++, through `--gcc-install-dir`). It started
with the compiled part alone while the plan of the enumerations was settled,

```sh
python3 tests/brute/brute.py run --work WORK --budget 12600 --jobs 80 --nice 10 \
    --cpus 0-31,64-95 --generator Ninja --build gcc13=g++ --build clang18=CLANG \
    --seed m1r2-linux --part compiled --commit CODE --driver-commit d619f71715fb1cd21171ecc164552c95c7f2b562
```

was stopped (SIGTERM) after 562 seconds of budget, and went on with both parts and the budget
left, on the same work directory:

```sh
python3 tests/brute/brute.py run --work WORK --budget 12000 --jobs 80 --nice 10 \
    --cpus 0-31,64-95 --generator Ninja --build gcc13=g++ --build clang18=CLANG \
    --seed m1r2-linux --part compiled,interp --interp-bins 20 --interp-take 0,3-19 \
    --commit CODE --driver-commit DRIVER
```

Its enumerations took 48 minutes, so it was stopped once more after 3 003 seconds of that
budget and given bin 2 of the Mac's share as well, with the budget left (the same command with
`--budget 8930 --interp-take 0,2-19`).

macOS arm64 (Apple M3 Max, Apple clang 21 and GCC 16; 8 jobs):

```sh
python3 tests/brute/brute.py run --work WORK --budget 10800 --jobs 8 --nice 10 \
    --build clang=c++ --build gcc16=g++-16 --seed m1r2-mac --interp-bins 20 --interp-take 1 \
    --commit CODE --driver-commit DRIVER
```

Windows x64 (Intel Core i5-13500T, MSVC 19.52; 8 logical processors), started through WMI so
that it does not depend on the ssh session:

```bat
python tests\brute\brute.py run --work WORK --budget 10800 --jobs 8 --nice 1 --cpus 0-7 ^
    --generator Ninja --build msvc=cl --seed m1r2-windows --part compiled ^
    --env-script "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" ^
    --commit CODE --driver-commit DRIVER
```

Then, on each machine, with the driver of this commit (`collect` and `report` read the work
directories of the driver above):

```sh
python3 tests/brute/brute.py collect --work WORK --name NAME --out NAME.json --jobs N \
    [--cpus ... --nice ...]
```

with NAME `linux-x86-64`, `macos-arm64` and `windows-x64`, and on any machine, from the three files:

```sh
python3 tests/brute/brute.py report results/milestone1/brute/*.json
```

which prints the tables of the results page.
