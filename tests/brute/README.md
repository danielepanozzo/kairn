# The brute-force tier

`brute.py` runs ctest's cross-checks ([testing.md](../../docs/developer/testing.md))
for much longer: the oracle's `gen | RUNNER | check` pipelines, judged by the oracle and held to
the same guards (`tests/crosscheck_guards.py`). It is run by hand on the test machines,
not in CI. Python 3, standard library only; macOS, Linux and Windows. Here and in `brute.py`,
"the quick tier" names the cross-checks as they were when ctest had one tier: "the quick tier's
format" is the toy format of a kernel's enumeration by the interpreter (`tests/CMakeLists.txt`),
which the full tier runs now.

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
  tier's exponent range (1, 2 and 3 when `min_precision` is 1; the main runs of Milestone 1
  below started at 2, from a plan written before the oracle read formats of precision 1, and a
  supplementary run made the enumerations of precision 1), the quick
  tier's format one and two bits more precise, and other exponent
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
  the counts). At precision 1 the one-limb balls with two operands have a range of their own
  (`PRECISION_ONE`: `fp:1:-5:5` for the sums, `fp:1:-6:5` for the product), because the constants
  of the radius are large there (u = 1/2: the factor of a sum is 4, that of the product 8) and a
  format of few exponents leaves a finite ball in a few percent of the cases.
  `--fail-on-suspicious` as in the compiled part, and not for `ball_mul_1` at precision 1 either
  (`RADIUS_OVERFLOW`): the oracle shows a non-finite result as suspicious when the operands and
  the exact set are within a quarter of the largest number, and with a factor of 8 the radius of
  such a set can be beyond the largest number in any exponent range; nor for `acc_radius_1` and
  `acc_radius_2` at precision 2, whose radius $\mathrm{RN}(sK + C)$ has the factor
  $K = \mathrm{up}((1+u)^8) = 6$ at $u = 1/4$, the largest number of their format of the plan
  (the run of Milestone 2 stopped on them: [its page](../../docs/developer/results/brute-milestone2.md)).
  `widen.py KERNEL FORMAT` is the exact test in its place: every operand of the format through
  the interpreter, in the format and in one with more exponents above, where nothing overflows;
  the result must be non-finite exactly when the wide one exceeds the format's largest number,
  and equal to it otherwise. An output that every claim of the kernel conditions on a mask
  (`if` in `gen/claims.json`, the radius of an accumulator under `ok`) is compared only where
  that mask is true.
  `--interp-bins N --interp-take LIST` splits the plan into N bins of about equal size and runs
  some of them, so that machines can share it; `--interp-match REGEX` keeps only the
  enumerations whose `KERNEL FORMAT` matches.

- **emulated** (`--part emulated`, not in the default `compiled,interp`): the kernels printed for
  the emulated limb type ([testing.md](../../docs/developer/testing.md#the-emulated-formats),
  `tests/emulated/`), the C++ of the scalar kernels on an integer arithmetic of the format, through
  `kairn-emulated-runner` (`--emulated-runner PATH`, or built in the first `--build`), judged by
  the oracle in the formats of the statements of precision 8 to 11 with the smallest exponent
  range, `fp:8:-14:1`, `fp:9:-16:1`, `fp:10:-18:1` and `fp:11:-20:1` (`bound_sum_2` and
  `bound_dot_2`, whose counts must reach about $2^{2p-2}$, in `qmax = 16`). Every operand where
  the enumeration has at most `EMULATED_EXHAUSTIVE` (2·10⁷) indices: each kernel that reads one
  limb at every precision, each kernel of two limbs at precision 8 (two numbers: 18 931 201 cases;
  a pair, an interval or a ball of one limb: 2 to 10 million). Otherwise `EMULATED_CASES` (500 000)
  random cases of every stratum of the oracle's generator, of the run's seed, and for each fold
  `EMULATED_FOLD_CASES` (20 000) random arrays of up to `EMULATED_FOLD_LENGTH` (256) elements in
  every order. A kernel of three limbs or more is not sized: its enumeration at precision 8 has
  more than 4·10¹⁰ indices. Pipelines of `--emulated-chunk` (10⁶) indices or cases (a hundredth of
  it for the arrays of a fold), each `gen | kairn-emulated-runner | check`, two busy processes;
  `--emulated-bins N --emulated-take LIST` and `--emulated-match REGEX` as for the interpreter's.
  `python3 tests/brute/brute.py plan` prints the part after the enumerations (`--part emulated`
  alone, which does not size those; `--sizes FILE` keeps the sizes): 1 068 entries, 122
  enumerations of 802 601 535 indices (77 kernels at precision 8, the 15 of one limb at 9, 10 and
  11) and 946 random series of 388 520 000 cases or arrays. `collect` holds each entry to the
  guards with `--emulated` (a format of the statements of precision 8 to 11, a quarter of the cases
  judged) and writes its counts under `"emulated"`. The part's run on the Linux machine, its rates
  and its results are in [testing.md](../../docs/developer/testing.md#the-emulated-formats).

The folds of `gen/claims.json` ("folds") take part in both: in the compiled part, random arrays of
up to 4 096 elements (`FOLD_LENGTH`; the products of BallVectors `bv_conv_k` up to 256 coefficients,
`PRODUCT_LENGTH`, since their judgment grows faster than the product of the two lengths: 200 of up
to 4 096 took the oracle more than seven minutes on the Linux machine, of up to 256 eight seconds)
in units of a hundredth of `--chunk`, one stream for the
scalar runners in every order and one per packed backend in the lane order of its register
(`packed_lanes` of the fold), each judged and guarded with its orders and length; in the interp
part, every array of the formats of `FOLD_SHAPES` up to a length, in every order that differs
(`gen --exhaustive --max-length`). A format of the sums of two limbs needs at least twice as
many binades as bits: with fewer (`fp:3:-2:-1`, `fp:4:-4:-1`), every sum of up to three pairs is
a pair, exact, and the guards fail the run.

A pipeline that fails (a violated claim, an invalid case, a suspicious non-finite result where
the quick tier fails on one, a broken stream, a runner or oracle error, a timeout) is a finding:
its series (one kernel, format and runner, or one enumeration) stops, and the finding goes to
`WORK/findings.jsonl` with the oracle's example lines and the command that reruns one of them.

## The round-up interval

The kernels of `kairn/upward.hpp` (`upward_*_1`, "rounding": "upward"; they require the rounding
mode upward set by `kairn::upward::Scope` and the options of `docs/concepts/upward.md`, GCC and Clang
`-frounding-math`, MSVC `/fp:strict`) are in the compiled part above, through the runners of their
family that each build produces (`kairn-gen-upward-runner*`) and through no other. Their
enumerations are not in the interpreter's part: `upward.py` here runs every case of the formats of
their statements of precision 1 to 4 through the interpreter, in each form of `max_nl` a kernel
computes, judged by the oracle (the gate of the generator's suite of
[the design page](../../docs/developer/design/upward.md), "Tests and CI";
[testing.md](../../docs/developer/testing.md#the-round-up-interval)). Nor are their emulated kernels
in the emulated part, whose runner has the other kernels.

```sh
python3 tests/brute/upward.py plan [--precision 1-4] [--kernels K,...]
python3 tests/brute/upward.py run --work WORK --jobs N [--precision 1-4] [--cpus LIST] [--nice N] \
    [--commit SHA --driver-commit SHA]
python3 tests/brute/upward.py status --work WORK
python3 tests/brute/upward.py collect --work WORK --out results/upward/exhaustive.json
```

The cases are those of `gen/tests/test_upward.py` (every canonical state with both zeros, every
canonical default interval, every value of a number), in pieces of about two million lines, each
the cases of a range of the first operand's: the interpreter completes a piece in a worker process,
and a process of the oracle's `check --fail-on-suspicious --expect-valid` of its own judges it and
writes its summary (`--jobs` counts both: two a piece). 243 kernels, formats and forms, 5 345 305 871
lines in 2 879 pieces. `run` writes `WORK/run.json` (the plan and the commits: a later `run` in WORK
must have the same), a summary and a record per piece in `WORK/pieces/` (the oracle's report too
for a piece that fails, and the piece in `WORK/findings.jsonl`), `WORK/run.log`, and
`WORK/status.txt`, rewritten after each piece: pieces and lines done, the rate over the last ten
minutes, the time left. It starts only the pieces without a record, so the same command resumes a
run that was stopped (a signal stops it, and its pieces run again next time; on Linux they also die
with it if it is killed). `status` writes and prints the status file from the records. `collect`
requires every piece of the plan to have passed, the pieces of each kernel, format and form to cover
every case once, the merged counts (`kairn-oracle check --merge`) to be the cases of the plan, all
judged, none failed, invalid or suspicious, and every claim applied, and writes the counts of every
kernel, format and form, and of each class of its claim, into one file.

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

### The supplementary run: B4

After these runs the eight full Ball kernels gained a condition on their `encloses` claim (B4).
A supplementary run judged them against the new claims, from a copy of commit
`f7e0b6df20f81c0dd77482f0a71528e889cfd759` (`CODE4`) with this driver of commit
`72f700fff5a610c82b37da05a9f55a5f0abee552` (`DRIVER4`), `BALLS` being
`ball_add_1_full,ball_sub_1_full,ball_mul_1_full,ball_scale_1_full,ball_add_2_full,ball_sub_2_full,ball_mul_2_full,ball_scale_2_full`:
on the Linux machine with all 128 hardware threads, both parts (every enumeration of the plan for
these kernels),

```sh
python3 tests/brute/brute.py run --work WORK4 --budget 1800 --jobs 144 --nice 10 --cpus 0-127 \
    --generator Ninja --build gcc13=g++ --build clang18=CLANG --seed m1r2b4-linux \
    --kernels BALLS --part compiled,interp --commit CODE4 --driver-commit DRIVER4
```

and the compiled part on the Mac and on Windows, with 20 minutes of budget each:

```sh
python3 tests/brute/brute.py run --work WORK4 --budget 1200 --jobs 8 --nice 10 \
    --build clang=c++ --build gcc16=g++-16 --seed m1r2b4-mac \
    --kernels BALLS --part compiled --commit CODE4 --driver-commit DRIVER4
```

```bat
python tests\brute\brute.py run --work WORK4 --budget 1200 --jobs 8 --nice 1 --cpus 0-7 ^
    --generator Ninja --build msvc=cl --seed m1r2b4-windows --part compiled ^
    --env-script "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" ^
    --kernels BALLS --commit CODE4 --driver-commit DRIVER4
```

each collected as above with NAME `linux-x86-64-b4`, `macos-arm64-b4` and `windows-x64-b4` into
`results/milestone1/brute/supplementary/`, and reported apart:

```sh
python3 tests/brute/brute.py report results/milestone1/brute/supplementary/*-b4.json
```

### The supplementary run: precision 1

The plan of the runs above started at precision 2. The 26 enumerations of precision 1 that the
plan has since then were run on the Mac, from the repository itself at the commit that added
`PRECISION_ONE`, `RADIUS_OVERFLOW` and `widen.py` to this driver (a few seconds):

```sh
python3 tests/brute/brute.py run --work WORK1 --budget 900 --jobs 8 --nice 10 \
    --part interp --interp-match ' fp:1:' --seed m1r2p1-mac
python3 tests/brute/brute.py collect --work WORK1 --name macos-arm64-p1 \
    --out results/milestone1/brute/supplementary/macos-arm64-p1.json --jobs 8
python3 tests/brute/brute.py report results/milestone1/brute/supplementary/*-p1.json
```

and, for the non-finite results of the one-limb balls with two operands and of the scaling,

```sh
python3 tests/brute/widen.py ball_add_1 fp:1:-5:5
python3 tests/brute/widen.py ball_sub_1 fp:1:-5:5
python3 tests/brute/widen.py ball_mul_1 fp:1:-6:5
python3 tests/brute/widen.py ball_scale_1 fp:1:-3:2
```

## The runs of Milestone 2

From copies of the tree made with `git archive` of commit
`1b370800e7e31c5bf85126a6ff0c215805dd83c9` (`DRIVER`), whose kernels, generator, claims and
oracle are those of `5f597fbcf2a7f5b077671e115487bc9515c0bb24` (`CODE`; the copy differs from it
in `tests/brute` alone), with `WORK` a directory outside it and `CLANG` the `clang++` above. The
Mac's first twenty minutes of enumerations ran from a copy of `CODE` itself, with the driver of
`346d2837ff7d4351be004c05897fd5e36956cec0`, whose enumerations are the same. The results are in
`results/milestone2/brute/` and
[docs/developer/results/brute-milestone2.md](../../docs/developer/results/brute-milestone2.md).

Each machine ran two phases in one work directory, with one seed. **Phase A**, every kernel and
loop and the machine's share of the enumerations (which a run does first), until every kernel
and format has one unit of random cases (`--cases` one `--chunk`). On the Linux machine, with 64
jobs while the emulated part below ran beside it and 80 after:

```sh
python3 tests/brute/brute.py run --work WORK --budget 36000 --jobs 80 --nice 10 \
    --cpus 0-31,64-95 --generator Ninja --build gcc13=g++ --build clang18=CLANG \
    --seed m2r1-linux --chunk 100000 --part compiled,interp --interp-bins 20 --interp-take 0-10 \
    --cases 100000 --commit CODE --driver-commit DRIVER
```

It was restarted on the same work directory as the rates were measured: with bins 0 to 12 for
the first twelve minutes, then 0 to 9, then 0 to 10 and `--cases 200000` (two units), at 64 and
then 80 jobs, and at last with `--cases 100000` above when the throughput under the machine's
load made a second unit of every pair too long; every restart keeps the pipelines finished, and
the units of a second round already finished count. On the Mac:

```sh
python3 tests/brute/brute.py run --work WORK --budget 21600 --jobs 8 --nice 10 \
    --build clang=c++ --build gcc16=g++-16 --seed m2r1-mac --chunk 50000 \
    --part compiled,interp --interp-bins 20 --interp-take 11-19 --cases 50000 \
    --commit CODE --driver-commit DRIVER
```

restarted likewise with bins 13 to 19, 13, 13 to 16 and 10 to 19 (with `--chunk 100000`, before
any unit of random cases) before the bins above. On Windows, started through WMI:

```bat
python tests\brute\brute.py run --work WORK --budget 10800 --jobs 8 --nice 1 --cpus 0-7 ^
    --generator Ninja --build msvc=cl --seed m2r1-windows --chunk 50000 --part compiled ^
    --env-script VCVARS --commit CODE --driver-commit DRIVER
```

with `VCVARS` "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat".

**The exhaustive tier on emulated formats**, the whole emulated part, on the Linux machine beside
phase A (`BUILD` the build `gcc13` above, `WORKE` a directory of its own):

```sh
python3 tests/brute/brute.py run --work WORKE --budget 36000 --jobs 16 --nice 10 \
    --cpus 0-31,64-95 --part emulated --seed m2r1-emulated-linux \
    --emulated-runner BUILD/tests/kairn-emulated-runner --commit CODE --driver-commit DRIVER
```

**Phase B**, the aim of $10^8$ results per kernel and format for the kernels `F` (below), with the
compiled part alone: a run whose parts include the interpreter's writes the plan of the
enumerations of its work directory again, and `--kernels` would restrict it. The same commands
as above (the same work directory and seed) with, in place of `--part compiled,interp ...
--cases N`: on the Linux machine `--part compiled --kernels F --cases 2200000` (`--budget
19000`), then `--part compiled --kernels FX --cases 2400000` (`--budget 1800`), then
`--part compiled --kernels S --cases 2300000` (`--budget 3600`), one unit more for the kernels
of the Windows machine, which did not reach its cap; on the Mac `--part compiled --kernels F
--cases 350000` (`--budget 6000`); on Windows `--kernels S --cases 500000` (`--budget 10500`).
`F` (116 kernels):

```
abs_upper_2,acc_add_1,acc_merge_1,acc_mul_1,acc_mul_entry_1,add_down_1,add_down_entry,
add_entry_step_1,add_entry_step_2,add_up_1,add_up_entry,axpy_entry_step_1,axpy_step_1,
ball_contains_ball_1,ball_contains_point_1,ball_contains_point_2,ball_equal_1,ball_equal_2,
ball_from_interval_1,ball_from_interval_2,ball_less_1,ball_less_equal_1,ball_lower_as_1,
ball_make_1,ball_make_2,ball_mul_pow2_1,ball_narrow_2_1,ball_negative_1,ball_negative_2,
ball_positive_1,ball_positive_2,ball_scale_1_full,ball_split_1,ball_to_interval_1,ball_upper_as_1,
ball_zero_1,ball_zero_2,bv_center_2,bv_center_entry_1,bv_conv_finish,bv_make_finish,
bv_make_radius,bv_mul_pow2_step_1,bv_neg_radius,dot_entry_step_1,dot_step_1,fast_two_sum_entry,
fold_finish_1,fold_finish_2,interval_contains_1,interval_empty_1,interval_empty_2,
interval_entire_1,interval_entire_2,interval_equal_1,interval_intersection_1,interval_less_1,
interval_less_equal_1,interval_make_1,interval_mid_rad_1,interval_neg_1,interval_negative_1,
interval_negative_2,interval_positive_1,interval_positive_2,interval_rel_disjoint_1,
interval_rel_equal_1,interval_rel_interior_1,interval_split_1,interval_subset_1,
interval_to_ball_1,interval_zero_1,interval_zero_2,mul_1_1,mul_2_1_entry,mul_dir_1,mul_down_1,
mul_down_entry,mul_pow2_2,mul_pow2_2_full,mul_pow2_step_1,mul_pow2_step_2,mul_up_1,mul_up_entry,
neg_1,next_down,next_up,norm_combine,norm_finish_1,norm_finish_2,norm_step_1,norm_step_2,radd,
radd_entry,rmul,scale_entry_step_2,scale_step_1,scale_step_2,split,sub_1_1,sub_down_1,
sub_down_entry,sub_entry_step_1,sub_entry_step_2,sub_up_1,sub_up_entry,sum_entry_step_1,
sum_entry_step_2,sum_fast_entry_step_2,to_down_2,to_nearest_2,to_up_2,two_prod_dekker,
two_prod_entry,two_sum_entry,two_sum_ord
```

`S` (107 kernels, the first set, which the Windows machine ran) is `F` but `FX`, the nine
kernels `acc_merge_1`, `ball_mul_pow2_1`, `interval_mid_rad_1`, `mul_pow2_step_2`,
`scale_entry_step_2`, `scale_step_2`, `sub_entry_step_2`, `sum_entry_step_2` and
`sum_fast_entry_step_2`.

Then, on each machine, with the driver of this commit:

```sh
python3 tests/brute/brute.py collect --work WORK --name NAME --out NAME.json --jobs N \
    [--cpus ... --nice ...]
```

with NAME `linux-x86-64`, `macos-arm64` and `windows-x64` (and `linux-x86-64-emulated` for
`WORKE`, stored as `results/milestone2/brute/emulated/linux-x86-64.json`), and from the files:

```sh
python3 tests/brute/brute.py report results/milestone2/brute/*.json
python3 tests/brute/brute.py report results/milestone2/brute/emulated/linux-x86-64.json
```

### The runs of Milestone 2: the radius of an accumulator at precision 2

The two enumerations the run stopped on (the results page has the finding) were run again on
the Mac from the repository at commit `0716b84248084f57dc6199268c82641c4240df0d`, which adds them
to `RADIUS_OVERFLOW`:

```sh
python3 tests/brute/brute.py run --work WORKR --budget 900 --jobs 2 --nice 10 --part interp \
    --interp-match '^acc_radius_[12] fp:2:-1:1$' --seed m2r1radius-mac
python3 tests/brute/brute.py collect --work WORKR --name macos-arm64-radius \
    --out results/milestone2/brute/supplementary/macos-arm64-radius.json --jobs 2
python3 tests/brute/widen.py acc_radius_1 fp:2:-1:1
python3 tests/brute/widen.py acc_radius_2 fp:2:-1:1
```

### The supplementary run: the close of rule R3

The twelve kernels and loops that the close of rule R3 added or changed (`R3`), from copies made
with `git archive` of the merge `76ebf33c60905d7e0ca811ad7d6dddd60f00135e` (`DRIVER3`), whose
code is that of `8ee5ed9d506489eb2e6b6549dbd1fc18e20fc586` (`CODE3`), each machine in a work
directory of its own (`WORK3`), the caps of phase B:

```
bv_center_entry_2,bv_make_2_entry,bv_scale_2_entry,bv_scale_radius_entry_2,bv_scale_step_2,
conv_2_entry,dot_2_entry,dot_entry_step_2,axpy_entry_step_2,axpy_entry_step_2_1,axpy_2_entry,
axpy_2_1_entry
```

On the Linux machine, compiled (new build trees, the code having changed), the six kernels of
`R3` (`R3K`: `bv_center_entry_2`, `bv_scale_radius_entry_2`, `bv_scale_step_2`,
`dot_entry_step_2`, `axpy_entry_step_2`, `axpy_entry_step_2_1`) to the aim, then its six loops
(`R3L`) to two units:

```sh
python3 tests/brute/brute.py run --work WORK3 --budget 5400 --jobs 80 --nice 10 \
    --cpus 0-31,64-95 --generator Ninja --build gcc13=g++ --build clang18=CLANG \
    --seed m2r1r3-linux --chunk 100000 --part compiled --kernels R3K --cases 2200000 \
    --commit CODE3 --driver-commit DRIVER3
```

and the same with `--kernels R3L --cases 200000`.

On the Mac, compiled, the interpreter's enumerations of the twelve (37, 46 931 460 indices) and
their entries of the emulated part (48):

```sh
python3 tests/brute/brute.py run --work WORK3 --budget 5400 --jobs 8 --nice 10 \
    --build clang=c++ --build gcc16=g++-16 --seed m2r1r3-mac --chunk 50000 \
    --part compiled,interp,emulated --kernels R3 --cases 350000 \
    --commit CODE3 --driver-commit DRIVER3
```

On Windows, started through WMI:

```bat
python tests\brute\brute.py run --work WORK3 --budget 5400 --jobs 8 --nice 1 --cpus 0-7 ^
    --generator Ninja --build msvc=cl --seed m2r1r3-windows --chunk 50000 --part compiled ^
    --env-script VCVARS --kernels R3 --cases 500000 --commit CODE3 --driver-commit DRIVER3
```

each collected as above with NAME `linux-x86-64-r3`, `macos-arm64-r3` and `windows-x64-r3` into
`results/milestone2/brute/supplementary/`, and reported apart:

```sh
python3 tests/brute/brute.py report results/milestone2/brute/supplementary/*-r3.json
```

### The runs of Milestone 2: four enumerations replaced, the loops by length

The four enumerations whose guards failed, in the formats the plan gives them since commit
`68da628c33837d4696eabbd7a621a3f9d3f01100`, from the repository at that commit (whose code of
these kernels is that of `CODE`), on the Mac:

```sh
python3 tests/brute/brute.py run --work WORKG --budget 3000 --jobs 4 --nice 10 --part interp \
    --interp-match '^(bound_sum_2|bound_dot_2) fp:16:-50:14$|^acc_merge_2 fp:(3:-3:-1|4:-3:-1)$' \
    --seed m2r1guards-mac --commit 8ee5ed9d506489eb2e6b6549dbd1fc18e20fc586
python3 tests/brute/brute.py collect --work WORKG --name macos-arm64-guards \
    --out results/milestone2/brute/supplementary/macos-arm64-guards.json --jobs 4
```

and the loops by the length of their arrays (`L` the 47 loops of `CODE`, `RUNNER` the scalar
runner `kairn-gen-runner` of the Mac's Apple clang build above):

```sh
python3 tests/brute/lengths.py --runner RUNNER --seed m2r1-mac --cases 5000 --folds L \
    --jobs 6 --out results/milestone2/brute/lengths/macos-arm64.json
python3 tests/brute/lengths.py table results/milestone2/brute/lengths/macos-arm64.json
```
