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
  contraction setting of the quick tier. Cases come in units of `--chunk` (200 000); a unit is
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
  exponents and larger restricted domains (`SHAPES` and `EXPLICIT` in `brute.py`).
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
```

`run` configures and builds each `--build NAME=COMPILER` under `WORK/builds/NAME` (Release, with
`--generator` and `--cmake-arg` if given), then runs the parts given by `--part` (default both;
the enumerations first, as they must finish to count). `--jobs` counts busy processes: a compiled
pipeline is one, an interpreter's two. No pipeline starts after `--budget` seconds (counted from
the end of the build); those running finish. `--cpus` and `--nice` confine the driver and
everything it starts; `--env-script` runs everything in the environment a script sets up
(`vcvars64.bat` on Windows).

`run` is restartable: every finished pipeline leaves the oracle's summary under `WORK`, and
running the same command again starts only what is missing (a larger `--budget` or `--cases`
extends a run). It never leaves processes behind: on SIGINT, SIGTERM or SIGHUP it kills its
pipelines; on Linux they also die with it if it is killed (`PR_SET_PDEATHSIG`); on Windows it and
its pipelines run in a job object that kills them when it ends, however it ends. On macOS a
driver killed with SIGKILL leaves its pipelines to finish their chunk on their own.

`collect` merges each series' summaries with the oracle (`check --merge`), applies
`tests/crosscheck_guards.py` to each merged series (cases 0 to N of the machine's seed, every
stratum, every claim applied, both outcomes of every comparison, ...) and to each enumeration
(complete coverage of exactly the domain asked for), and writes one compact JSON file: per kernel
and format the counts, the largest error over its bound, the observed constants, the largest
`upper` excess and the smallest Ball radius slack, each with the line that attains it, and per
runner its counts. It exits 1 if a guard failed, an enumeration is incomplete or anything was
found.

## The runs of Milestone 1

From the repository root of a copy of the tree (`WORK` a directory outside it), with about 90
minutes of budget on each machine. The results are in `results/milestone1/brute/` and
[docs/developer/results/brute-milestone1.md](../../docs/developer/results/brute-milestone1.md).

Linux x86-64 (AMD EPYC 7452, GCC 13 and Clang 18; 64 of its 128 hardware threads; `CLANG` is a
`clang++` that finds GCC 13's libstdc++, through `--gcc-install-dir`):

```sh
python3 tests/brute/brute.py run --work WORK --budget 5400 --jobs 80 --nice 10 \
    --cpus 0-31,64-95 --generator Ninja --build gcc13=g++ --build clang18=CLANG \
    --seed m1-linux --interp-bins 20 --interp-take 3-19
```

macOS arm64 (Apple M3 Max, Apple clang 21 and GCC 16; 6 jobs):

```sh
python3 tests/brute/brute.py run --work WORK --budget 5400 --jobs 6 --nice 10 \
    --build clang=c++ --build gcc16=g++-16 --seed m1-mac --interp-bins 20 --interp-take 0-2
```

Windows x64 (Intel Core i5-13500T, MSVC 19.52; 8 logical processors):

```bat
python tests\brute\brute.py run --work WORK --budget 5400 --jobs 8 --nice 1 --cpus 0-7 ^
    --generator Ninja --build msvc=cl --seed m1-windows --part compiled ^
    --env-script "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
```

Each run was stopped and started again twice in its first twenty minutes, with the same command,
a newer driver (better scheduling) and the budget left, and the Windows run once more after a
network reset ended its ssh session; the work directory kept what was done. Then, on each machine:

```sh
python3 tests/brute/brute.py collect --work WORK --name NAME --out NAME.json --jobs N \
    [--cpus ... --nice ...]
```

with NAME `linux-x86-64`, `macos-arm64` and `windows-x64`, and on any machine, from the three files:

```sh
python3 tests/brute/brute.py report results/milestone1/brute/*.json
```

which prints the tables of the results page.
