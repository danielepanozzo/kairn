# Testing

How Kairn's code is tested, what each test is for, and how to rerun one case of a failing test
by hand. The parts named here (generator, interpreter, oracle, runner, claims) are described in
[Architecture](architecture.md#the-pipeline).

## The tiers

| Tier | What | Where it runs | Time |
|---|---|---|---|
| Quick | `ctest --test-dir build`: the library, with the build's compiler and flags: every kernel through every compiled runner on a small sample, every public operation on a small sample, the stored regression cases, the checks of a debug build, the object code of every kernel in five configurations of the compiler's flag matrix ([below](#object-code)), the examples, the negative controls, the consumer checks, and that the generated files and the reference pages are fresh ([below](#the-quick-tier)) | every push and pull request, on every platform of the CI (`build.yml`); and by anyone, with the three commands of [Getting started](../getting-started/index.md#configure-build-and-test) | on 2026-11-21, with `two_prod` refused in constant evaluation where Dekker's product overflows ([Time](#time)), 988 tests and 91 seconds on the Mac with Apple clang and 989 and 94 with GCC 16 (`--parallel 8`), 992 tests and 68 seconds with GCC 13 and 989 and 74 with Clang 18 on the Linux machine, and with `-mavx2 -mfma` 989 and 74 with GCC 13 and 986 and 108 with Clang 18 (`--parallel 16`); before it, with the public functions of the enclosure interface, 984 tests and 81 seconds on the Mac with Apple clang and 985 and 85 with GCC 16 (`--parallel 8`), 988 tests and 67 seconds with GCC 13 and 985 and 74 with Clang 18 on the Linux machine, and with `-mavx2 -mfma` 985 and 73 with GCC 13 and 982 and 108 with Clang 18, a run with the pauses of ctest that [Time](#time) describes (`--parallel 16`); before them, on the tree that joins the oracle of stage B2 to the join (against `gen/claims.json`, nothing left out), 851 tests and 90 seconds on the Mac with Apple clang and 852 and 99 with GCC 16 (`--parallel 8`, with another session's jobs running), 855 tests and 66 seconds with GCC 13 and 852 and 66 with Clang 18 on the Linux machine, and with `-mavx2 -mfma` 852 and 69 with GCC 13 and 849 and 73 with Clang 18 (`--parallel 16`, under a load average of 20 to 50 from other jobs), the largest summary 0.98 MB (`two_prod_dekker`); before it, on the tree that joins the ball vectors, the lanes of the packed runners assigned by a seeded permutation and `Packed` and the containers (against claims without the 53 objects of stage B2), 745 tests and 119 seconds on the Mac with Apple clang (`--parallel 4`) and 746 and 131 with GCC 16 (with other jobs of ours running), 749 tests and 119 seconds with GCC 13 and 746 and 114 with Clang 18 on the Linux machine (`--parallel 16`, under a load average of about 50 from other jobs); with the ball vectors and the accumulator judged (against claims without the 53 objects of stage B2 of the intervals, `KAIRN_ORACLE_CLAIMS`), 705 tests and 127 seconds on the Mac with Apple clang (`--parallel 4`; 633 tests and 92 seconds before them), 706 tests and 48 seconds with GCC 13 and 703 and 54 with Clang 18 on the Linux machine (`--parallel 16`; 634 tests and 46 seconds before them with GCC 13); with `--parallel 4`, on 2026-11-20 with 571 and 572 tests, 79 seconds on the Mac with Apple clang, 97 with GCC 16 and 125 to 127 on 16 threads of the Linux machine with GCC 13 ([The size of the summaries](#the-size-of-the-summaries)); with 421 to 452 tests, 25 to 34 seconds on the Mac, 37 to 47 on the Linux machine and 52 to 58 on the Windows machine (73 on 4 logical processors); on the hosted runners, measured before each cross-check ran in one process, 31 to 45 seconds on Linux and 69 to 75 on macOS, and on Windows estimated since 56 to 80, 126 on the slowest runner seen ([Time](#each-cross-check-in-one-process)) |
| Full | `ctest --test-dir build/tests/full`: everything that left the quick tier, named `full.*`: the same cross-checks on more cases, every public operation built with each [flag set](#flag-sets) of a client, the kernels built at `-O0` and `-O1` (`/Od`, `/O1`), the object code on the compiler's whole flag matrix, the interpreter's enumerations of toy formats, and the tools' own tests: the generator's, the oracle's, and those of the cross-checks' guards, of the script of the reference pages and of the brute-force driver ([below](#the-full-tier)) | every push and pull request, in jobs beside the quick tier's (`full.yml`, and `generator.yml` for the generator's part); and by hand | on 2026-11-21, with `two_prod` refused in constant evaluation where Dekker's product overflows, the same 1 497 tests and 18 minutes with GCC 13 on the Linux machine (`--parallel 16`, the tools held to one worker, the oracle's own quick selftest among the rest); before it, with the public functions of the enclosure interface, 1 497 tests and 18 minutes with GCC 13 on the Linux machine (`--parallel 16`, the tools held to one worker, and the oracle's own quick selftest alone after the rest, 4 minutes more; [Time](#time)); before them, on the tree that joins the oracle of stage B2 to the join (against `gen/claims.json`, nothing left out), 1 285 tests and 17 minutes with GCC 13 on the Linux machine (`--parallel 16`, under a load average of about 40 from other jobs), the largest summary 2.7 MB (`mul_pow2_map_1`); before it, on the tree that joins the ball vectors, the lanes of the packed runners and `Packed` and the containers (against claims without the 53 objects of stage B2), 1 110 tests and 17 minutes with GCC 13 on the Linux machine (`--parallel 16`, under a load average of about 50 from other jobs); with the ball vectors and the accumulator judged (against claims without the 53 objects of stage B2 of the intervals), 1 105 tests and 14 minutes with GCC 13 on the Linux machine (`--parallel 16`; 980 tests and 12 minutes before them), the largest summary 2.7 MB (`mul_pow2_map_1`; of the ball vectors 0.9 MB, `bv_neg_2`); with `--parallel 4`, on 2026-11-20 with 884 tests, 20 minutes on the Mac with Apple clang and 32 on 16 threads of the Linux machine with GCC 13; it leaves a build tree of about 0.5 GB ([The size of the summaries](#the-size-of-the-summaries)) |
| Generator | `python3 gen/kairn-gen test`: the generator's whole suite, C++ included | every push and pull request, with each GCC-style compiler of the CI, and without its C++ tests on Windows | a few minutes per compiler |
| Proofs | `make -C proofs`: every Rocq proof, then the axiom audit | every push and pull request | a minute or two, with four cores |
| Brute force | `tests/brute/brute.py`: the cross-checks of the compiled runners on millions of random cases per kernel, format and machine (every runner of a machine on the same cases, both forms of the scalar fix-ups), and the interpreter on every operand of larger toy formats, with the same guards and a time budget. Many of those formats are of no statement ($q_{\max} < 1$, or $\eta$ above `binary_float`'s: 582 of the plan's 1 239 enumerations, [The formats of the statements](architecture.md#number-formats); 104 more have a wider subnormal range, where such a clause is judged and a failure is a finding), and there a clause that promises a finite result is counted as not claimed (V4 of the ball vectors, the `finite_when` of `ball_of_interval` and the `bounded_when` of `interval_of_ball` of two limbs, the midpoint of a bounded interval of `ball_of_interval` with `ieee1788` and the parts of a split that rest on it; F3, B4 and I5 are judged there too, below): in `fp:4:-4:-1` and `fp:4:-5:0` the sum of the two halves of a bounded interval beside $\pm\Omega$ overflows, and the midpoint of `interval_mid_rad_2` and the point of split of `interval_split_2` are a NaN (12 and 60 lines), counted as not claimed | by hand on the test machines before each milestone report (`tests/brute/README.md`; results in [Brute force, Milestone 1](results/brute-milestone1.md)); and every night on the hosted runners with a smaller budget (`nightly.yml`), on new random cases and one fortieth of the enumerations | for the final code of Milestone 1, 3.5 hours on the Linux machine and 3 hours each on the Mac and the Windows machine; a night on the hosted runners, under two hours per platform |

ctest runs the quick tier in the build directory and the full tier in `tests/full` of it, and says
which before the first test and after the summary (with Apple clang: `Kairn tests: the quick
tier, 988 tests. The full tier, 1497 tests more: ctest --test-dir .../tests/full`); every test of
the quick tier also has the label `quick`, and every test of the full tier the label `full`. Both
are registered by the same configuration: the file `CTestCustom.cmake` that configuring writes at
the top of the build tree leaves the full tier out of a run there (`CTEST_CUSTOM_TESTS_IGNORE`),
so that `ctest -R` in the build directory never selects a `full.*` test, and a run in
`build/tests` runs both. The full tier is registered only when Kairn is the top-level project and
Python 3 is found: a project that adds Kairn with `KAIRN_BUILD_TESTS` on gets the quick tier, the
tests of the library with that project's compiler and flags, among its own tests (without the
messages, which are written into the top of Kairn's own build tree only).

A kernel's claims are only as good as the tests that could have refuted them, so every cross-check
fails when it checked nothing, or less than it says: when the oracle judged no case, when an
enumeration did not cover the domain it names, when a random run missed a stratum, or when a claim
was never put to the test ([below](#what-a-pass-requires)).

## The quick tier

The tests that `ctest` runs in the build directory, by name:

| Test | Checks |
|---|---|
| `kairn-gen.check` | Every committed generated file is what `python3 gen/kairn-gen build` writes. |
| `kairn-oracle.claims` | The oracle can read every claim in `gen/claims.json` (the claims file `KAIRN_ORACLE_CLAIMS`, [below](#against-other-claims)). |
| `docs.reference.check` | The reference pages of the site are what `docs/tools/reference.py` writes ([Documentation](documentation.md#reference-pages)). |
| `crosscheck.compiled.K.F` | Kernel K compiled with the build's compiler and flags, scalar (`gen/tests/runner.cpp`) and packed (`gen/tests/packed_runner.cpp`, the backend of the target, [below](#packed-kernels)), once as the flags stand and once with each contraction setting added to them ([below](#contraction)): each of these runners on the same 6 000 random cases of format F (`binary64`, `binary32`) from every stratum; the packed runners with the requests assigned to the lanes by a seeded permutation, under the guard that the registers mixed kinds, and the one with the build's flags also consecutively ([below](#packed-kernels)). |
| `crosscheck.lanes.fault.F` | A packed runner with a fault planted in a copy of `mul_2_2_full` (its special-value select reads the mask of the neighboring lane, `tests/lanes/`) passes the cross-check of format F with the consecutive assignment where no register mixes a non-finite operand with finite ones, and fails it, by the oracle's verdict, with the permuted one; the guard refuses the consecutive assignment of the same stream ([below](#packed-kernels)). |
| `crosscheck.compiled.FOLD.F` | A fold (a sum or a dot product over arrays) compiled likewise: the scalar runners on 300 random arrays of format F, of every length class and in every order, and the packed runners on 200 arrays in the lane order of their register ([below](#cross-checks)). A map, a fold of maxima and a convolution likewise, on 100 arrays of up to 24 elements (pairs of polynomials of up to 20 coefficients for a convolution, which has no packed form). |
| `objcode.check` | Every kernel compiled with the build's compiler in five configurations of its flag matrix, scalar and packed, for `double` and `float`: the fused multiply-adds and the plain multiplications of its object code are what `gen/objcode.json` says the IR asks for ([below](#object-code)); and in one of them the operations of `Ball` outlined and external, each a call of a function with the counts of its kernel ([below](#the-operations-of-ball-outlined-and-external)). |
| `objcode.controls` | The textbook `a * b + c` fails that check in exactly the configurations where its program sees the compiler fuse it, and in at least one; counts changed on purpose fail it. |
| `objcode.test` | The checker's own tests, on stored disassemblies of every format it reads (Python only). |
| `regression.cases` | The stored cases of `tests/regression/cases.txt` (the cases that found a problem, and those that came closest to a claim, [below](#the-regression-cases)) through every compiled runner of the build, the generator's interpreter, and both runners of the public interface with every form of each public kernel, judged by the oracle (`tests/regression/run.py`). |
| `consume.*` | A CMake project that uses Kairn through `add_subdirectory`, and one through `find_package` after `cmake --install`, build and run a kernel. The first (`tests/consume/subproject.cmake`) also checks that Kairn as a subproject prints no line of its own when configured and that `cmake --install` installs nothing of Kairn's; and that both checks can fail: its notice about `kairn::fma`, made necessary by giving the results of its two compile checks on the command line, appears with `--log-level=VERBOSE`, and with `-DKAIRN_INSTALL=ON` the headers are installed. |

The tools' own tests, which test the generator, the oracle and the other tools rather than the
library, were in the quick tier until they set its time on the hosted runners ([Time](#time)):
they are in the full tier, each under its name there with `full.tools.` in front
([below](#the-full-tier)).

The tests of the public interface (`tests/api/`, label `api`):

| Test | Checks |
|---|---|
| `api.oracle.K.F` | Every public operation that calls kernel K, computed through the constructors, operators and functions of `kairn/kairn.hpp` (`tests/api/runner.cpp`, a runner of the line protocol), on 2 000 random cases of format F, judged by the oracle against K's claims; by two runners on the same cases, one built with the build's flags and one with contraction forced on. For a kernel of the extended domain the cases include infinite and NaN operands and empty and whole balls and intervals, built through the public constructors (an interval through `Interval(lo, hi)`, the empty set as its reversed bounds). Each form of the operation (`x + a` and `a + x`, `x += a`, `x + y` with a one-limb `y`, the marked and the unmarked operator, `kairn::finite::add`, `X.midpoint()` and `X.radius()` together for `interval_mid_rad_1`) is judged on its own. A few forms can compute only some lines of their kernel (`ldexp` needs a power of two among the operands of `mul_1_1`, a point form a ball of radius 0, the steps of `ldexp` an operand that can be scaled exactly, the conversion of the result of `two_sum` to two limbs a finite error term, the interval of a point a line whose two bounds are one value, the bounds of an interval of two limbs as numbers of `T` a line of `to_down_2` or `to_up_2` whose operand is not a NaN, the member test of a point of `T` in an interval or a ball of two limbs a line whose point is a value of `T`); they compute the plain operation on the others, and fail if a stream of 1000 lines or more reached their own operation on none, which is why the quick tier has at least 1 000 cases. The building blocks on `T` are their kernels' forms as they are (`two_sum` is the form of `two_sum_entry`), and the scalings of a ball by a power of two are reached through `ldexp(X, n)` with $2^n$ the case's power of two, through `half` of a ball scaled first by $2^{n+1}$ exactly, and through the steps of `ldexp` from a ball scaled exactly by another power. The forms of the enclosure interface ([One enclosure interface](../reference/enclosure.md)): a three-valued answer, a `kairn::Trit`, is printed as the two masks of its kernel, *yes* then *no* (`not_equal` exchanged back); `kairn::member` on a kernel of one exact mask prints the mask, and stops the runner if it ever answers *unknown*; `contains(t)` of a ball of two limbs prints its answer as the *yes* and the *no* of `kairn::member`; the hull and the intersection of balls take their operands as the line gives them, through the constructor that keeps a kernel's result, since their claim compares limbs, the sign of a zero included, which the public constructor's guard would change. |
| `api.oracle.K.F`, the packed forms | The same cases through `Packed` and the views of `kairn/soa.hpp` (the runner's forms `packed_NAME`, after the scalar ones): each line completed in one lane of a register whose other lanes hold other lines of the stream, the form of `Packed` being that of the build (AVX2, NEON or one lane) and, where the build's flags give the scalar form on x86-64, also AVX2, through a third runner of the packed forms alone, on the kernels that `kairn/packed.hpp` calls ([below](#packed-and-the-containers)). |
| `api.oracle.coverage` | Every kernel of `gen/claims.json` is called by a public form of the runner, or is a building block, or is an entry kernel (`entry: yes` in `gen/kernels`) on the runner's short list of those not public yet, each with its reason (today the ten finite cores of the Ball operations, those of the scalings by a power of two among them: the operators and `ldexp` call the full kernels, and `kairn::finite` has no Ball forms); no entry kernel is a building block. The building blocks include the nine of the interval kernels (`mul_dir_1`, the bounds of two limbs, `mul_ext_2_2`). The kernels of the folds' stage and of the maps, which no public operation calls yet (`KAIRN_NOT_PUBLIC_YET`, [Cross-checks](#cross-checks)), are on none of the runner's lists. The kernels that `kairn/packed.hpp` calls are exactly those of the runner's packed forms (`runner --packed-list`), each with a scalar form too. |
| `api.constexpr` | `static_assert`s of every operation usable in constant evaluation, infinities, NaN and the states of a ball included, comparisons with a NaN among them, the building blocks on `T` against values computed by hand (every row of the table of `next_up` and `next_down`); of intervals the constructors (an infinite point and the same infinity twice the whole line, reversed bounds the empty set), the states, the bounds, the negation, the hull, the intersection, the midpoint, the radius, the split and the conversions, and of a ball the functions of the interface it shares with intervals, with the empty set and the whole line where constant evaluation takes them (on the empty set the midpoint, the radius, the split and the conversion to a ball, and on the states of a ball its bounds, the conversion to an interval, the narrowing and the ball from an infinite or NaN bound, compute a NaN or $\infty - \infty$ on the way, which GCC and Clang refuse at compile time: those are checked at run time); the same results at run time, with the same bits where Milestone 2 says so and the same values where a zero can differ in sign; `two_prod` at the largest operands on which constant evaluation, which runs Dekker's product, computes it (the largest square, the largest operand whose split is finite, a product of $\Omega$; where an operation of Dekker's product overflows it is not a constant expression, `api.reject.two_prod.*`) and just above $2^{2p-1}\eta$, against the run-time results, with the same bits at run time; at run time, the finite error term of `two_prod(0x1.fffffffffffffp+511, 0x1.fffffffffffffp+511)` and of its `float` analogue, also through a variable of static storage duration that is not `constexpr`, whose initialization the compiler tries as a constant expression first (but with MSVC, with which it was not run); `mul_down`, `mul_up`, `ldexp` and `half` of a ball, and the arithmetic of intervals of one and two limbs, which are not `constexpr`, at run time against values computed by hand (the tightest interval of `T` for a sum of one limb, $[\Omega, +\infty]$ at an overflow, $[0, 0] \cdot X = [0, 0]$ for an unbounded $X$, two limbs within $8.1u^2$ and $10.1u^2$ of the exact bounds, $[0, 0] + [0, 0] = [0, 0]$); the properties of the types; that an operation compiles without `kairn::unverified` exactly when the kernel it calls is proved; that a building block is not found by argument-dependent lookup for a `T` and does not hide a program's own function of the same name; of the enclosure interface the predicates, the member and subset tests, the three-valued comparisons, the relations of IEEE 1788 and the set operations of a ball where they are `constexpr`, against values computed by hand, and the others (the balls of two limbs, the split of a ball, the midpoint, radius and conversions of two limbs, the special states of a ball) at run time, with the types (a `Trit` that converts to no `bool`, no comparison operator of sets, no operation of two kinds of set or two numbers of limbs); and `KAIRN_VERSION_AT_LEAST`. |
| `api.environment` | `kairn::environment_ok()` and `kairn::self_test()` pass in the default environment and fail under each directed rounding mode and under flush-to-zero. |
| `api.flags.debug.self_test`, `api.flags.debug.constexpr`, `api.flags.debug.rational` | `kairn::self_test()` and `kairn::environment_ok()`, compiled as the [debug build](#flag-sets), pass (`runner.cpp --self-test`); `tests/api/constexpr.cpp` and `tests/api/rational.cpp` built so, their constant expressions evaluated with the checks on; `kairn::rational`, which does not round, runs under each directed rounding mode without the checks stopping the program. |
| `api.checks.debug.G`, `api.checks.release.G`, `api.checks.handler` | The [checks of a debug build](#the-checks-of-a-debug-build), in the debug build and with the build's own flags and `KAIRN_CHECKS` defined to 1, on a table of every public function: in the default environment each runs (G = `default`); under each directed rounding mode (`rounding`) `environment_ok()` is false and each function that rounds stops the program with the environment's message, while each function that does not round gives the same bits as to nearest on its corpus, without a report; under each state of flush to zero (`flush`) each function that checks anything stops it; every operand that is not canonical, and every negative radius, stops it (`operands`); a `KAIRN_ENVIRONMENT_FAILURE` of the program's own is called instead, by exactly the functions that must report the state, and every function goes on, without the checks of its operands (`handler`). |
| `api.shadow` | A program whose global variables have the name of every parameter and local variable of the headers, calling every public operation, compiles with the compiler's strictest warnings about a declaration that hides another, as errors; without the headers' suppression of those warnings (MSVC's C4459 and C6244, GCC's `-Wshadow`) it must not compile with MSVC, and without the globals it must compile with every warning on ([The program's names](#the-programs-names)). |
| `api.platform_macros` | The headers compile and work after a platform header that defines `min`, `max`, `small`, `near`, `far`, `hyper` and `interface` as macros: `<windows.h>` itself on Windows, without `NOMINMAX`, and the same macros defined by the test on every platform. |
| `api.self_test.unsafe.*` | With Clang, programs built with flags that break the kernels and define no macro (reassociation; `-ffp-model=fast`; with Apple clang on AArch64, `-fno-signed-zeros` with `-ffp-contract=fast`, which Clang 18 was measured not to break the kernels with): `kairn::self_test()` must fail. |
| `api.link.external.S` | With `KAIRN_ENCLOSURE_CODE_EXTERNAL`, `tests/api/link_main.cpp` linked with the definitions (`tests/api/definitions.cpp`) compiled with another `KAIRN_CHECKS` (S = `checks`), with the outlined setting (`setting`), or without them (`missing`) must not link, with the undefined operation in the message (`kairn::detail::external_checked::` or `external::`, or MSVC's LNK2038); its control, both files with the same options, links and runs (`tests/api/link_fail.cmake`). |
| `api.reject.*` | What must not compile, each with a control that compiles: the flags `config.hpp` rejects; a value of `KAIRN_ENCLOSURE_CODE` that is not one of its three (`enclosure_code.*`: an unknown name, nothing, a bare `-D`); each kind of operation and constructor written without the marker while its kernel is unverified (`unverified.*`, against a copy of the headers in which every kernel is); and an operation whose kernel alone is unverified, which must not compile through a conversion to another, proved kernel (`unverified_only.*`: `x + a` through `x + Expansion(a)`, a ball times a `T` through a point ball); with `KAIRN_CHECKS`, a constant expression given a pair that is not canonical (`from_limbs`, an operator) or a negative radius (`checks.*`); `mul_down` and `mul_up` in a constant expression, whose control computes the same at run time (`not_constexpr.*`), so that a change cannot make them `constexpr` by accident, and the sum of intervals likewise (`not_constexpr.interval_add`); of intervals (`interval.*`, `ball.implicit_narrowing`), an operation of intervals of one and of two limbs, an interval and a number (no kernel takes one), the implicit conversions of a ball to an interval, of an interval to a ball and of a ball of two limbs to one (each widens the set, so each is explicit), and an interval of two limbs from one of one limb, each control writing what compiles instead; an interval operation, constructor and conversion written without the marker against the copy of the headers in which every kernel is unverified (`unverified.interval_add_1`, `.interval_make_1`, `.interval_to_ball_1`); `kairn::rational` in a constant expression with a zero denominator, and with a result that fails its check, against a copy of the headers with a wrong flag planted in it, whose control turns `KAIRN_RATIONAL_CHECK` off (`rational.*`); `kairn::two_prod` in a constant expression on finite operands where an operation of Dekker's product, which constant evaluation runs, overflows: the partial product of the leading halves while the product is finite (`0x1.fffffffffffffp+511` squared, and `0x1.fffffep+63f`) and the product itself with no NaN on the way (`two_prod.overflows_in_constant_evaluation.*`), each control the neighboring operand where it compiles, against the run-time result; Clang's message names `two_prod_overflows_in_constant_evaluation`, GCC refuses the overflow itself, and MSVC's message was not seen (any failed constant expression); of the containers (`soa.*`), a write through a view of `const T` (an element, `set`, `store`, an element assigned from another) and a view of mutable limbs made of a view of `const T` or of a const `SoA`; of `Packed` (`packed.*`), an operation with an `Expansion` or a `T` operand (no packed kernel takes one), the narrowing to one limb written as an implicit conversion, and an operation of two limb types; the arithmetic of `Packed<T, 1>`, which has none (`packed.one_limb_arithmetic`); and a `KAIRN_PACKED_FORM` that is not a form (`packed_form.unknown`, `.bare`) or the form of another target (`packed_form.other_target`, which the generated header's `#error` refuses); of the enclosure interface (`enclosure.*`, cases 70 to 81), a `Trit` in a condition and as a `bool`, a comparison operator of intervals and of balls, a comparison of intervals of one and two limbs and of an interval and a ball, `contains` of a ball in an interval and of an interval of the other number of limbs, a relation of IEEE 1788 of balls, the implicit conversions between `Interval<T, 2>` and `Ball<T, 2>`, the hull of balls of one and two limbs, each control writing what compiles instead; the new kinds written without the marker (`unverified.interval_less_1` and six more), and the member test of a point of `T` whose kernel alone is unverified, which must not compile through the interval or the ball of the point (`unverified_only.interval_contains_1.point` and three more). |
| `api.boundary.S`, `api.boundary.unguarded.S` | A product the program computes and passes in (`x + a * b`, `E2(a * b)`, `from_limbs`, `kairn::finite::add`, a ball's center, radius or point) gives the result of the same operation on the rounded product, bit for bit, under contraction setting S (and, of the enclosure interface, the point of the member test of a ball, which adds it, the bounds of `from_interval`, and the point of the member test of an interval, which only compares it and needs no guard); built against a copy of the headers in which the generated guard is taken out of `gen/scalar.hpp` (made at configure time, which fails if it finds no guard), it must not where the compiler was measured to fuse across statements (`tests/api/boundary.cpp`). |
| `api.boundary.packed.FORM.S`, `api.boundary.packed.unguarded.FORM.S` | The same for `Packed` and the containers, in each form FORM of `Packed` ([below](#packed-and-the-containers)): a product the program computes in the registers of the form, or in `T` into an array, passed into `Packed<T, 1>::from_limbs` and then the mixed forms, into `Packed<T, 2>::from_limbs`, a load, a view or an `SoA` (`tests/api/boundary_packed.cpp`); the copy without the guard also takes it out of `gen/avx2.hpp` and `gen/neon.hpp`. |
| `api.k1.zero_cost` | The instructions emitted for one operation and for loops over `Expansion<double, 1>` against the same code over `double` (`tests/api/k1/zero_cost.py`); with MSVC it also fails when one of these functions has a `/GS` stack cookie ([costs](results/costs-milestone1.md#3-msvc-and-the-gs-stack-cookie)). |
| `api.rational.K.F` | `kairn::rational` with K limbs of format F ([Constants from fractions](../reference/rational.md)) on 2 000 cases of the oracle's generator of `rational_K` (`KAIRN_RATIONAL_QUICK_CASES`, seed `KAIRN_API_SEED`), computed at run time by `tests/api/rational_runner.cpp`, which also requires `kairn::is_rational_result` to accept each result; the oracle compares every limb, the error and the flag with its own, for equality, and the guards require what the cross-checks of `rational_K` must have seen ([Cross-checks](#cross-checks); `tests/crosscheck.py compiled --kernel rational_K`, one process, as for a kernel). |
| `api.rational.constexpr` | `tests/api/rational.cpp`: `static_assert`s of the results of two dozen fractions and six integers, for `float` and `double`, one and two limbs, against values computed from the specification with exact rationals; `kairn::is_rational_result` refusing each result changed by one unit; and a corpus of 104 fractions, each computed in a constant expression and at run time under each of the four rounding modes, with the same bits. |
| `api.example.*` | The examples of the documentation (`docs/examples/cpp/`), which check their own output; `api.example.accurate_sums.*`, `api.example.intervals.*` and `api.example.bisection.*`, built under each contraction setting, also compare it with the text their tutorials show ([Documentation](documentation.md#examples)). `api.example.packed_dot.FORM`, the tutorial's vector loop in each form of `Packed`, compares it too, and checks each result against the bound the tutorial states ([below](#packed-and-the-containers)). |
| `api.packed.FORM`, `api.soa.FORM` | `Packed` against the scalar operations, lane by lane and bit for bit, and the containers of `kairn/soa.hpp` ([below](#packed-and-the-containers)). |

## The full tier

The tests that `ctest --test-dir build/tests/full` runs, by name, each named as the quick tier's
test it extends, with `full.` in front, or as the quick tier's test it was, with `full.tools.` in
front:

| Test | Checks |
|---|---|
| `full.crosscheck.compiled.K.F` | `crosscheck.compiled.K.F` on 20 000 cases instead of 6 000: the cases of the same seed from case 0, so that the quick tier's are the first 6 000 of these; with the kernels' runners, scalar and packed, of two [flag sets](#flag-sets) as well: the debug build (`-O0`, `/Od`) and one at `-O1` (`/O1`); every packed runner with both assignments of the lanes, the permuted and the consecutive one ([Packed kernels](#packed-kernels)). |
| `full.api.oracle.K.F` | `api.oracle.K.F` on 10 000 cases instead of 2 000, the quick tier's among them, and by a third runner, the [debug build](#flag-sets)'s, with the checks, on the first form of K only; and by the runners of the [flag sets](#flag-sets) `O3-outlined` and `O3-external` (`O2-` with MSVC and clang-cl), the operations of `Ball` outlined and external, every form of which must write the same bytes as the same form of the runner with the build's flags (`tests/crosscheck.py api --same-as`). |
| `full.api.flags.oracle.K.F` | Every public form of kernel K through the runner of each [flag set](#flag-sets), the debug build's included, on the quick tier's 2 000 cases of format F. |
| `full.api.flags.S.self_test`, `full.api.flags.S.constexpr`, `full.api.flags.S.rational` | `api.flags.debug.*` for each other flag set S, the outlined and external ones among them. |
| `full.api.checks.S.G`, `full.api.checks.handler.S` | `api.checks.release.G` and `api.checks.handler` with the operations of `Ball` outlined (S = `outlined`) and external (`external`), whose checks are then in functions of their own: the same cases, the same verdicts. |
| `full.api.rational.K.F` | `api.rational.K.F` on 20 000 cases instead of 2 000 (`KAIRN_RATIONAL_CASES`), the quick tier's among them, through the runner with the build's flags and the runner of every [flag set](#flag-sets), the debug build's included; the code is integer code, so every output must be the same bytes; the oracle judges each distinct output once. |
| `full.objcode.check`, `full.objcode.controls` | `objcode.check` and `objcode.controls` in every configuration of the compiler's flag matrix: 24 for GCC, Clang and Apple clang and for clang-cl, 9 for MSVC; the operations of `Ball` outlined and external in each. |
| `full.crosscheck.interp.K` | Kernel K run by the generator's interpreter on **every** operand combination of a toy format. |
| `full.crosscheck.interp-restricted.K` | Kernel K run by the interpreter on every operand of a **restricted** domain of a toy format, for the kernels whose whole enumeration is too long. |
| `full.crosscheck.interp-sampled.K` | The same kernels on 20 000 random cases of the whole toy format, from every stratum; and the interval kernels whose shape names a sampled format of its own (`_toy_sampled...` of `tests/CMakeLists.txt`), on 20 000 random cases of that format. |
| `full.crosscheck.compiled.FOLD.F`, `full.crosscheck.interp.FOLD`, `full.crosscheck.interp-sampled.FOLD` | A fold: the compiled runners on 1 000 random arrays of up to 4 096 elements (the packed runners on 500), the flag sets' runners among them; the interpreter on every array of a tiny format up to a small length, in every order that differs, and on 1 000 random arrays of a toy format of up to 1 024 elements ([Cross-checks](#cross-checks)). A map the same on arrays of up to 1 024 elements, a fold of maxima as a fold, a convolution on 300 pairs of polynomials of up to 64 coefficients. |
| `full.kairn-gen.test` | The four test classes of the generator that `full.tools.kairn-gen.test` leaves out (`-k`): the interpreter against the machine's own arithmetic (Python's float and `math.fma`) on thousands of cases per kernel and format and against every rounding of toy formats, and the statements of the IEEE model and of the non-finite layer on every operand of small formats. With four worker processes. |
| `full.kairn-oracle.selftest` | The six tests of the oracle that `full.tools.kairn-oracle.selftest` leaves out (`--only`): its Python reference runner, correct and with injected errors, on every case of tiny formats. With four worker processes. |
| `full.search.compiled` | The adversarial search ([below](#the-adversarial-search)) on every kernel with an `error`, `upper`, `encloses` or `extends` entry, `binary64` and `binary32`, through the scalar runner with the build's flags, 5 000 cases per kernel and format from its seeds; fails on any violated claim. With four worker processes. |
| `full.tools.kairn-gen.test` | The generator's own tests, without those that compile C++ (`--no-cxx`, see [the generator's tier](#the-generators-tier)) and without the four test classes of `full.kairn-gen.test` (`--skip`). |
| `full.tools.kairn-oracle.selftest` | The oracle's own tests (`--quick`), including injected errors it must catch, without the six enumerations of toy formats of `full.kairn-oracle.selftest` (`--skip`). It compiles its own C++ reference runner with the build's compiler; if that fails, the test fails. |
| `full.tools.crosscheck.guards.CLASS` | One test per class of `tests/test_crosscheck_guards.py` (written `full.tools.crosscheck.guards` below), so that they run side by side and none nears its time limit. The cross-checks' guards fail the runs they are there to fail, and so do the drivers of the cross-checks with them ([What a pass requires](#what-a-pass-requires), `tests/test_crosscheck_guards.py`). |
| `full.tools.docs.reference.test` | The tests of `docs/tools/reference.py`, the script of the reference pages ([Documentation](documentation.md#reference-pages)). |
| `full.tools.brute.driver.test` | The tests of the [brute-force](#the-tiers) driver `tests/brute/brute.py`: the plan of its enumerations, the forms of the fix-ups, `widen.py` on one small format (`tests/brute/test_brute.py`). |

The names of the parts that each of the generator's and the oracle's two tests leaves to the other
are in `tests/CMakeLists.txt` (`_gen_full`, `_oracle_full`), and both tools fail when a name they
are given matches no test, so that a test renamed cannot drop out of both. A label says what a
test of the full tier depends on, which is how the CI runs each where it must and no more
([Continuous integration](#continuous-integration)): `python`, on Python alone, in exact
arithmetic, the same everywhere (run once, on Linux); `generator`, on the machine's arithmetic as
well (run on every operating system, inside the generator's whole suite in `generator.yml`);
neither, on the compiler (run on every platform and compiler of the CI). The tools' own tests have
the label `tools`; but for the generator's, which is labelled `generator` too, they run with every
compiler, as they did in the quick tier.

Labels select groups in either tier: `-L crosscheck`, `-L compiled`, `-L interp` (with
`-L restricted` and `-L sampled` among them), `-L api` (with `-L oracle`, `-L reject` and
`-L boundary` among them), `-L objcode`, `-L python`, `-L generator`, `-L tools`; `-R` selects by
name, for example `ctest --test-dir build -R mul_2_2` for the quick tier's tests of `mul_2_2`.

## Cross-checks

A cross-check is one pipeline: the oracle writes requests, a runner completes them, and the oracle
judges every completed line against the kernel's claims in exact arithmetic
([the line protocol](architecture.md#the-line-protocol)). The test prints the oracle's report,
pass or fail; on failure it also prints the command that reruns one case (below).

The tests of the compiled runners and of the public interface run that pipeline in one Python
process, `tests/crosscheck.py`: the oracle's `gen` and `check` run in it, through the oracle's
own command line (`kairn_oracle.cli.main`, the code, options and exit status of
`kairn-oracle gen` and `kairn-oracle check`), and so do the guards
([below](#what-a-pass-requires)); each runner runs in a process of its own and sees nothing but
the requests, which are generated once, into a file with the bytes `gen` writes (lines that end
with CR LF on Windows), and read by each runner in turn. The oracle reads each output as its
standard input would read the same bytes. The interpreter's enumerations of the full tier stay
three processes at once (`tests/crosscheck.cmake`, `gen | kairn-gen interp | check`), so that the
oracle's work overlaps the interpreter's. A test's whole cross-check runs by hand as ctest runs it:
`ctest -V -R NAME` prints its command.

- **Every kernel** in `gen/claims.json` gets its tests: adding a kernel to the generator adds them.
  The exceptions are listed in one place, `KAIRN_NOT_YET_CROSS_CHECKED` of
  `tests/CMakeLists.txt`, kernels whose claims the oracle cannot read yet; with them
  `KAIRN_NOT_YET_CROSS_CHECKED_FOLDS` for folds. No cross-check, no enumeration of a toy format,
  no brute-force run and no test of the public interface is registered for a name of these lists,
  and configuring says how many are left out, or, when none is, that the oracle judges every kernel
  and fold of the claims. **On them today**: nothing. Both lists are empty, and stay for the objects
  of a later stage whose claims the oracle cannot read yet; what was on them left them with the
  interval stage, stage B, the ball vectors' stage and stage B2 of Milestone 2. Since stage B2 the
  oracle reads and judges the 53 kernels of the predicates and comparisons of an interval and of a
  ball, the set operations of a ball and the conversions of two limbs ([Claims of the enclosure
  interface: predicates and
  comparisons](architecture.md#claims-of-the-enclosure-interface-predicates-and-comparisons) and the
  two sections after it: the kinds `certain`, `trit`, `ball_set` and `ball_splits`, the condition
  `abs_le` of their `exact_when`, and the new fields of `ball_of_interval`, `interval_of_ball` and
  `makes_ball`; `oracle/README.md`, "The kinds of the enclosure interface"): they are
  cross-checked by every compiled runner, scalar and packed, on 2 000 cases per format in the quick
  tier (`KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES`) and 20 000 in the full tier, and the interpreter
  enumerates their toy formats; they left `KAIRN_NOT_PUBLIC_YET` with the functions of
  `kairn/interval.hpp` and `kairn/ball.hpp` that call them, and each has its `api.oracle` tests
  ([One enclosure interface](../reference/enclosure.md)). Their guards ask for every class of
  each claim, and hold the answers that the comparisons of balls of two limbs leave unknown to the
  band architecture.md gives, $2e + 4G$ (`ENC_BAND_LIMIT`: an answer is not claimed there, but a
  run that leaves one far from the boundary does not pass). Since the ball vectors' stage the
  oracle reads and judges the ball vectors, their constructors, the products of two BallVectors and
  their kernels, and the accumulator's kernels (`oracle/README.md`, "Ball vectors and the
  accumulator", "Their kernels", "Their folds"): they are cross-checked as the maps are, V4 in the
  formats its statements quantify over. `conv_radius`, the radius kernel of the
  products of two BallVectors, stayed on the list for the oracle's finding (a NaN where
  `prod(ma, mb)` overflows and `g` or `m` is zero, $+\infty$ from a small stated value) until the ruling of 2026-11-21 made its claim one of finite results, a result that is not finite
  being $+\infty$ or a NaN ([`upper` of a kernel of the finite domain with several
  operations](architecture.md#claims-of-the-non-finite-layer)): it is cross-checked as the other
  radius kernels are, its results that are not finite counted. Every map and every ball vector is
  cross-checked in place too (`tests/crosscheck.py --inplace`, a stream of requests `inplace=I`
  through every runner, the packed ones included, with its guards). Since stage B of
  Milestone 2 the oracle reads and judges the maps, the folds of maxima and the convolutions, and
  their kernels (`oracle/README.md`, "Maps", "Folds of maxima", "Convolutions"): they are
  cross-checked as the folds are, and the steps of the maps and the kernels of the folds of maxima
  are on `KAIRN_NOT_PUBLIC_YET` with those of the folds' stage. Since the folds' stage of
  Milestone 2 the oracle reads and judges every claim of that stage, the kinds of that stage
  included (`upper` with a value of its own and `holds` under a mask, the error of form `T`,
  `count()` and `format(half)`, `finite_or_nan`, and the folds' `fold_error` on requests of
  arrays; `oracle/README.md`, "The kinds of the folds' stage" and "Folds"). The kernels of that
  stage (the bounds `bound_sum_k` and `bound_dot_k`, the steps `dot_step_k`, `sum_entry_step_k`
  and `sum_fast_entry_step_2`, the finishes `fold_finish_k`) are cross-checked as every kernel is;
  no public operation calls them yet, and `KAIRN_NOT_PUBLIC_YET` names them for the public
  interface's tests, which register no form of them and require the runner to list them nowhere
  (`tests/api/coverage.cmake`). Since the interval stage of Milestone 2 the oracle also reads and
  judges every claim of the 33 kernels of the interval stage, the intervals of one and two limbs,
  the bounds of two limbs they are built on and the conversions between an interval and a ball
  (the requirements `interval()` and `not_nan()`, the kinds `outward`, `makes_interval`,
  `encloses_interval`, `set_bound`, `interval_set`, `ball_of_interval`, `interval_of_ball` and
  `splits`, `encloses` with no ball, `makes_ball` from an interval, `zero_factor`, the constants
  of a claim with `up( )`, and an entry about an output group other than the first;
  `oracle/README.md`, "The kinds of the interval kernels"). They are cross-checked as every
  kernel is, on fewer cases in the quick tier (`KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES`, 2 000, the
  first of the full tier's 20 000: [Time](#time)). They left `KAIRN_NOT_PUBLIC_YET` with
  `kairn/interval.hpp`: the public interface reaches the 24 entry kernels among them through
  `Interval` and the functions of a `Ball` of the enclosure interface, and lists the other nine
  (`mul_dir_1`, the bounds of two limbs `add_ball_2_2` to `mul_dir_2_2`, and `mul_ext_2_2`) as
  building blocks.
- **The formats of the statements** (the ruling of 2026-11-21; [Number
  formats](architecture.md#number-formats)), in the same words in `oracle/README.md`: *the
  generated statements quantify over the formats of `binary_float` ($e_{\max} > p$, smallest
  exponent $3 - e_{\max} - p$; in the oracle's terms $q_{\max} \ge 1$ and
  $q_{\min} = 3 - q_{\max} - 2p$); a clause that promises a finite result (V4, `finite_when`,
  `radii_when`, `count_when`) is claimed there, and the oracle may also judge it in a format with a
  wider subnormal range, where nothing is proved and a failure would be a finding to report, not a
  violated claim; in any other toy format it is not claimed, and the oracle counts that.* V4 of the
  ball vectors and of the products of two BallVectors follows it (counted `V4 not claimed: a format
  of no statement` outside, which the guards ask a run in such a format to say), and so do
  `finite_when` of `ball_of_interval` and `bounded_when` of `interval_of_ball` with bounds of two
  limbs, the conversions of two limbs of stage B2 (counted `finite_when not claimed: ...` and
  `bounded_when not claimed: ...` outside, the guards asking for those counts there; every format
  of their cross-checks is of `binary_float`'s shape), and, by a second ruling of that
  day, the midpoint of a bounded interval of `ball_of_interval` with `ieee1788`, a finite canonical
  number, and what `splits` claims of the parts that rest on it (counted `a finite center not
  claimed: ...` and `a split at a point of X not claimed: ...` outside, the guards asking for those
  counts there). The `finite_when`
  of the Milestone 1 kernels (F3, B4) and the `bounded_when` of the interval kernels (I5) are
  judged in every format, those outside `binary_float`'s included, where 13 of the 28 kernels
  judged with such a clause have the toy format of their full tier (`mul_2_2_full` in
  `fp:4:-4:-1`, `ball_add_2_full` in `fp:3:-2:-1`, ...) and pass: stricter than the rule, and left
  so, since counting those lines as not claimed would stop judging lines that pass today
  (`oracle/README.md`, "The formats of V4").
- **Every fold** in the list `"folds"` of `gen/claims.json` gets tests of its own, under the same
  names: `crosscheck.compiled.F.FORMAT` in the quick tier runs the scalar runners on 300 random
  arrays (`KAIRN_CROSSCHECK_FOLD_QUICK_CASES`) of lengths 0 to 256
  (`KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH`) in every order (`seq`, `lanes:W` for W = 0, 1, 2, 3, 4,
  5, 8 and more lanes than elements), and the packed runners on 200 arrays
  (`KAIRN_CROSSCHECK_FOLD_PACKED_QUICK_CASES`) of their one order, `lanes:W` with the W of their
  register (`packed_lanes` of the fold's claims), each stream generated once and judged with its
  own guards (`tests/crosscheck.py compiled --packed-runner LABEL EXE --packed-lanes W`). In the
  full tier, `full.crosscheck.compiled.F.FORMAT` has 1 000 arrays (`KAIRN_CROSSCHECK_FOLD_CASES`; 500 for the packed runners)
  of lengths up to 4 096 (`KAIRN_CROSSCHECK_FOLD_LENGTH`) and the flag sets' runners too;
  `full.crosscheck.interp.F` runs the interpreter on every array of a tiny format up to a small
  length, in every order that differs, and `full.crosscheck.interp-sampled.F` on 1 000 random
  arrays of a toy format, up to 1 024 elements (`crosscheck.cmake -DMAX_LENGTH`):

    | Arrays | Folds | Every array of | Random arrays of |
    |---|---|---|---|
    | one limb | `sum_1`, `sum_1_entry` | `fp:3:-3:0` up to 3 elements: 225 835 | `fp:5:-7:4` |
    | two limbs | `sum_2`, `sum_2_entry`, `sum_fast_2`, `sum_fast_2_entry` | `fp:3:-4:1` up to 2: 363 379 | `fp:4:-7:2` |
    | one limb, two arrays | `dot_1` | `fp:2:-1:0` up to 2: 77 029 | `fp:5:-12:-1` |
    | two limbs, two arrays | `dot_2` | `fp:4:-4:-1`, one element: 62 501 | `fp:4:-7:-3` |

    Two elements of `dot_2` are more than $10^8$ arrays in any format of its precision 4; its
    sums of products are in the sampled runs and in the compiled runners' lengths. The sums of
    pairs need exponents: in a format of fewer binades than twice its precision (`fp:3:-2:-1`,
    `fp:4:-4:-1`) every sum of up to three pairs is itself a pair, exact, and the guards fail
    such a run (it puts nothing of the bound to the test); `fp:3:-4:1` has eight binades for
    three bits.

    The maps, the folds of maxima and the convolutions of stage B, by their kind, their scalars
    (`s1` of one limb, `s2` of two, `sc` a power of two) and their arrays; an enumeration of a map
    is every value of each scalar with every array up to the length, of a convolution both lengths
    up to it:

    | Shape | Objects | Every array of | Random arrays of |
    |---|---|---|---|
    | map 1 1 | `add_1`, `sub_1` and their entry forms | `fp:2:-1:0` up to 2: 77 029 | `fp:5:-7:4` |
    | map 2 2 | `add_2`, `sub_2` and their entry forms | `fp:3:-4:1`, one element: 181 477 | `fp:4:-7:2` |
    | map s1 1 1 | `axpy_1`, `axpy_1_entry` | `fp:3:-3:0`, one: 74 130 | `fp:5:-12:-1` |
    | map s2 2 2 | `axpy_2`, `axpy_2_entry` | `fp:4:-3:-2`, one: 262 208 | `fp:4:-7:-3` |
    | map s1 2 2 | `axpy_2_1`, `axpy_2_1_entry` | `fp:3:-2:-1`, one: 26 650 | `fp:4:-7:-3` |
    | map s1 1 | `scale_1` | `fp:3:-3:0` up to 2: 149 982 | `fp:5:-12:-1` |
    | map s1 2 | `scale_2` | `fp:2:-2:1` up to 2: 149 314 | `fp:4:-8:-2` |
    | map sc 1 | `mul_pow2_map_1` | `fp:4:-5:0` up to 2: 234 963 | `fp:5:-6:2` |
    | map sc 2 | `mul_pow2_map_2` | `fp:3:-3:0` up to 2: 179 346 | `fp:5:-6:2` |
    | max 1 | `norm_upper_1` | `fp:3:-3:0` up to 3: 225 835 | `fp:5:-7:4` |
    | max 2 | `norm_upper_2` | `fp:3:-4:1` up to 2: 363 379 | `fp:4:-7:2` |
    | conv 1 1 | `conv_1` | `fp:2:-1:0` up to 2 and 2: 44 521 | `fp:5:-12:-1` |
    | conv 2 2 | `conv_2` | `fp:4:-4:-1` up to 1 and 1: 63 001 | `fp:4:-7:-3` |

    Two elements of a map of pairs, or of axpy, are more than ten million arrays in any format of
    its precision: the enumeration of one element is every case of the step, with every flag and
    second pass of one element, and the sampled runs and the compiled runners have the rest. The
    quick tier's cross-checks of these objects have 100 arrays of up to 24 elements
    (`KAIRN_CROSSCHECK_MAP_QUICK_CASES`, `KAIRN_CROSSCHECK_MAP_QUICK_LENGTH`; a convolution two
    polynomials of up to 20 coefficients each, `KAIRN_CROSSCHECK_CONV_QUICK_LENGTH`), each group
    of runners; the full tier's 1 000 of up to 1 024 for a map (`KAIRN_CROSSCHECK_MAP_LENGTH`), a
    fold of maxima as a fold, and 300 pairs of up to 64 coefficients for a convolution
    (`KAIRN_CROSSCHECK_CONV_CASES`, `KAIRN_CROSSCHECK_CONV_LENGTH`), whose lines hold $n_x n_y$
    terms.
- **Random cases**: 6 000 per kernel and format in the quick tier (`KAIRN_CROSSCHECK_QUICK_CASES`)
  and 20 000 in the full tier (`KAIRN_CROSSCHECK_CASES`), seed 0 (`KAIRN_CROSSCHECK_SEED`), so
  that a run is the same everywhere and can be repeated. The oracle's generator chooses the strata
  from the kernel's family (`oracle/README.md`): those of the first wave for sums and products,
  and the families of the second wave (conversions, comparisons, directed steps, scaling, balls)
  each with strata of its own; a kernel of the extended domain also gets those of the non-finite
  layer (non-finite operands, $0 \cdot \infty$, overflow, the `finite_when` thresholds, the states
  of balls, the radii of constructors). It takes the strata in turn, by a fixed schedule, so that
  every sample longer than the schedule has cases of each; the quick tier's 6 000 cases have 261 to
  1 500 per stratum, of 7 to 16 strata.
- **Every compiled runner on the same cases**: a test of the compiled runners
  (`tests/crosscheck.py compiled`) generates the requests once and has each runner of the build
  complete them. Every output is judged, but one that is the
  same, byte for byte, as an output judged before is not judged again: the oracle's verdict and
  summary depend on nothing but the lines it reads and the claims, so the first runner's verdict
  is that of every runner that wrote the same bytes, and the report says which runners share it.
  With GCC 13, Clang 18 and Apple clang 21, every runner of a build writes the same bytes, scalar
  and packed, under every contraction setting, so the oracle judges one output per test. With
  MSVC, four kernels (`make_2`, `make_2_limbs`, `ball_make_1`, `ball_make_2`) have two: the
  packed runner, or the one built with `/fp:strict`, returns a zero of the other sign on some
  lines, which the claims allow. `api.oracle.K.F` does the same with its two runners and the
  forms of each (`tests/crosscheck.py api`): one output per test there too, but for
  `mul_pow2_2`, whose two forms differ on the lines where one computes the plain operation, and,
  with MSVC, a few forms that return a zero of the other sign (`mul_2_1_full`, `to_nearest_2`,
  and on the full tier's cases `mul_2_2_full` and `ball_mul_2_full`).
- **The toy formats** depend on the kernel's domain and inputs, each written as its role: `1` a
  limb, `2` a normalized pair, `r` a radius (`nonneg()`), `c` a power of two (`power_of_two()`).
  They are chosen so that each enumeration is 50 000 to 250 000 cases and at least the kernel's
  minimum precision. The tables are in `tests/CMakeLists.txt`; a kernel whose inputs have no
  entry, or whose minimum precision is above its toy format's, gets a test that fails and says
  so, rather than a run where nothing is claimed. For the kernels of the finite domain, the
  range of products is below 1, so that most products neither overflow nor vanish:

    | Inputs | Kernels | Toy format | Cases |
    |---|---|---|---|
    | `1` | `split` | `fp:11:-30:10` | 86 015 |
    | `1 1` | `two_sum`, `fast_two_sum`, `add_1_1` | `fp:5:-7:4` | 172 225 |
    | `1 1` | `two_prod`, `two_prod_dekker`, `mul_1_1` | `fp:5:-12:-1` | 172 225 |
    | `2 1`, `1 2` | `add_2_1`, `sub_2_1`, `sub_1_2` | `fp:4:-4:2` | 221 361 |
    | `2 1` | `mul_2_1` | `fp:4:-8:-2` | 221 361 |
    | `2 2` | `add_2_2`, `add_fast_2_2`, `sub_2_2` | `fp:3:-3:2` | 178 929 |
    | `2 2` | `mul_2_2` | `fp:4:-7:-3` | 245 025 |
    | `2 c` | `mul_pow2_2` | `fp:5:-6:2` | 144 755 |
    | `1 r 1` | `ball_scale_1` | `fp:3:-5:0` | 84 700 |
    | `2 r 1` | `ball_scale_2` | `fp:2:-4:1` | 60 102 |
    | `1 r 1 r` | `ball_add_1`, `ball_sub_1` | `fp:2:-3:1` | 76 176 |
    | `1 r 1 r` | `ball_mul_1` | `fp:2:-4:1` | 142 884 |

    The kernels of the extended domain (the non-finite layer, [Claims of the non-finite
    layer](architecture.md#claims-of-the-non-finite-layer)) read the roles in that domain: `1`
    is any value of the format, infinities and NaN included; `2` a canonical pair (finite and
    normalized, $(\pm\infty, 0)$ or NaN); `r` a radius that may also be $+\infty$ or NaN; `b1`
    and `b2` a ball, its center of one or two limbs and its radius together, which the oracle
    enumerates as one operand: every finite center with every finite radius $\ge 0$, the whole
    line and the empty set. Every enumeration includes the non-finite values of each operand
    (`oracle/README.md`, "gen"), and every format has the shape the statements of the IEEE model
    are proved for, $q_{\min} + q_{\max} = 3 - 2p$, which `binary64` and `binary32` have: one
    fits the budget for every kernel. The theorems also assume $q_{\max} \ge 1$, which some of
    these formats do not have (`fp:3:-2:-1`, for example): there the tests judge the statements
    where no theorem covers them
    ([which formats](design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)). At these sizes a format of that shape has few exponents
    (two to twelve, and forty for the one limb of `make_2`), so overflow is common, which is what
    the layer is about.

    | Inputs | Kernels | Toy format | $q_{\min} + q_{\max} = 3 - 2p$ | Cases |
    |---|---|---|---|---|
    | `1` | `make_2` | `fp:11:-29:10` | yes | 83 970 |
    | `2` | `neg_2`, `abs_2`, the conversions, `make_2_limbs` | `fp:6:-10:1` | yes | 89 730 |
    | `r r` | `radd`, `rmul` | `fp:6:-10:1` | yes | 174 724 |
    | `1 1` | `ball_make_1` | `fp:5:-7:0` | yes | 84 100 |
    | `2 1`, `1 2` | `add_2_1_full`, `sub_2_1_full`, `sub_1_2_full`, `mul_2_1_full`, the comparisons, `ball_make_2` | `fp:4:-5:0` | yes | 113 316 |
    | `2 c` | `mul_pow2_2_full` | `fp:5:-7:0` | yes | 84 888 |
    | `2 2` | `add_2_2_full`, `add_fast_2_2_full`, `sub_2_2_full`, the comparisons | `fp:3:-4:1` | yes | 181 476 |
    | `2 2` | `mul_2_2_full` | `fp:4:-4:-1` | yes | 62 500 |
    | `b1` | `ball_neg_1` | `fp:5:-9:2` | yes | 86 322 |
    | `b2` | `ball_neg_2` | `fp:4:-6:1` | yes | 198 074 |
    | `b1 b1` | `ball_add_1_full`, `ball_sub_1_full`, `ball_mul_1_full` | `fp:2:-3:2` | yes | 144 400 |
    | `b1 1` | `ball_scale_1_full` | `fp:3:-4:1` | yes | 89 436 |
    | `b2 1` | `ball_scale_2_full` | `fp:3:-3:0` | yes | 100 044 |
    | `b2 b2` | `ball_add_2_full`, `ball_sub_2_full` | `fp:3:-2:-1` | yes | 122 500 |
    | `a2` | `fold_finish_2` (two limbs of any values: the state of a fold) | `fp:5:-7:0` | yes | 84 100 |

    The kernels of the folds' stage of the finite domain: `n` is a count (`count()`, with
    `format(half)`), the bounds `bound_sum_k` and `bound_dot_k` on every count of `fp:12:-30:12`
    (49 153 cases, counts with $m \cdot \mathrm{unit}(K)$ from 0 to past 1); `dot_step_1` (`1 1 1`)
    on every operand of `fp:3:-6:-1` (166 375) and `dot_step_2` (`2 2 2`) of `fp:4:-3:-2`
    (226 981); the steps of the sums of supplied arrays have the formats of `add_1_1` and `add_2_2`.
    Stage B: the steps of the maps that claim what a kernel above claims have its format
    (`add_entry_step_k`, `sub_1_1`, `sub_entry_step_k`, `scale_step_k`, `mul_pow2_step_2`), the
    steps of axpy those of the dot products' steps (`1 1 1`, `2 2 2`), and `mul_pow2_step_1`
    (`1 c`) every operand of `fp:7:-14:6` (76 005), `axpy_step_2_1` and its entry form (`1 2 2`) of
    `fp:3:-5:-3` (107 911); the kernels of the folds of maxima, `m` a mask: `norm_combine`
    (`1 m 1 m`) on `fp:4:-6:1` (81 796), `norm_step_1` (`1 m 1`) on `fp:5:-7:0` (164 738),
    `norm_step_2` (`1 m 2`) on `fp:3:-6:2` (214 722), and the finishes `norm_finish_k` (extended,
    `1 m`) on every value of `fp:11:-29:10` with the mask both ways (167 940).

    The interval kernels of Milestone 2: `i1` and `i2` are an interval of one limb and of two, its
    two bounds together (`interval()`), which the oracle enumerates as one operand: the empty set,
    and every pair $l \le h$ of bounds, $l$ a number or $-\infty$, $h$ a number or $+\infty$. A
    kernel without a value whose set is a product (`interval_mul_k`) has the shape of a product.
    The kernels of the bounds of the interval work have shapes that exist: `ext 1 1`
    (`interval_make_1` and `ball_from_interval_2` at `fp:5:-7:0`, 84 100 pairs of any values;
    `mul_dir_1` there too, 83 521 without NaN), `ext 2 2` (`interval_make_2` at `fp:3:-4:1`,
    181 476; `mul_ext_2_2` at `fp:4:-4:-1`, 62 001 without NaN), `ext b1` (`ball_lower_as_1`,
    `ball_upper_as_1`, `ball_to_interval_1` at `fp:5:-9:2`, 86 322), `ext b2` (`ball_lower_as_2`,
    `ball_upper_as_2`, `ball_narrow_2_1` at `fp:4:-6:1`, 198 074), and the finite `2 2`
    (`add_ball_2_2` and the bounds of two-limb sums at `fp:3:-3:2`, 178 929; `mul_ball_2_2` and
    `mul_dir_2_2` at `fp:4:-7:-3`, 245 025). Where a sampled format is named, the full tier also
    runs the interpreter on 20 000 random cases of it (`full.crosscheck.interp-sampled.K`): an
    enumeration of two intervals is of a tiny format, of two or three exponents for two limbs,
    where every sum of pairs is exact.

    | Inputs | Kernels | Toy format | Cases | Sampled |
    |---|---|---|---|---|
    | `ext i1` | `interval_neg_1`, `interval_mid_rad_1`, `interval_to_ball_1`, `interval_split_1` | `fp:5:-9:2` | 87 152 | |
    | `ext i1 i1` | `interval_add_1`, `interval_sub_1`, `interval_hull_1`, `interval_intersection_1` | `fp:2:-3:2` | 188 356 | `fp:5:-7:0` |
    | `ext i1 i1`, a product | `interval_mul_1` | `fp:2:-3:2` | 188 356 | `fp:5:-12:5` |
    | `ext i2` | `interval_neg_2` | `fp:3:-4:1` | 90 524 | |
    | `ext i2 i2` | `interval_add_2`, `interval_sub_2`, `interval_hull_2`, `interval_intersection_2` | `fp:3:-2:-1` | 245 025 | `fp:4:-10:5` |
    | `ext i2 i2`, a product | `interval_mul_2`: the bounds of $x$ with leading limbs in $\{0, \pm\tfrac18, \pm 1, \pm\tfrac32, \pm 3\}$ (RESTRICTED) | `fp:4:-3:-2` | 239 785 | `fp:5:-12:5` |

    Every format of a kernel of the extended domain has the shape $q_{\min} + q_{\max} = 3 - 2p$,
    and every constant of the kernel a number of it (at `fp:2:-1:0` the constant $P = 2^{2p-1}\eta$
    of the directed products is not, and the interpreter refuses `interval_mul_1` there). On the
    Mac the 33 enumerations take 6 to 129 seconds each through the interpreter, 20 to 40 for most.

- **Restricted enumerations.** The two-limb balls with two operands have far too many operand
  combinations at their minimum precision (140 million for `ball_add_2` at `fp:3:-3:2`, 12.4
  billion for `ball_mul_2` at `fp:4:-5:1`, 97.6 million for `ball_mul_2_full` at `fp:4:-4:-1`).
  Their `interp-restricted` test enumerates every operand of a domain restricted by the oracle's
  `--restrict`, and says so in its report ("complete over a RESTRICTED domain"); their
  `interp-sampled` test runs 20 000 random cases of the whole format from every stratum of the
  ball family. A restriction shrinks the finite part of a domain only: the whole line and the
  empty set are always enumerated, and for `ball_mul_2_full` the zero ball too, since `cy` is
  not restricted.

    | Kernels | Toy format | Restricted to | Cases |
    |---|---|---|---|
    | `ball_add_2`, `ball_sub_2` | `fp:3:-3:2` | both radii in {0, 1/8, 1/2, 5/2}, `cx` in [1/2, 2) | 148 896 |
    | `ball_mul_2` | `fp:4:-5:1` | both radii in {0, η, 3/2}, `cx` in [1, 2), `cy` in [1/8, 2) | 64 728 |
    | `ball_mul_2_full` | `fp:4:-4:-1` (of the shape above) | both finite radii in {0, η, 1/2, 3/2}, a finite `cx` in [1, 2) | 120 780 |

- **Non-finite results.** A claim of the finite domain says nothing about a case whose leading
  output limb is not finite, so the oracle does not judge such a case; a runner that returned NaN
  for everything would pass. The cross-checks therefore pass `--fail-on-suspicious`, which fails
  a non-finite result whose operands and exact value are all far below the overflow threshold.
  A kernel of the extended domain (the non-finite layer) is judged on every line, non-finite
  results included, and the same option fails its non-finite results on such operands where its
  claims leave them open (`oracle/README.md`, "The extended domain"). The exceptions, for every
  runner, are `split` and `two_prod_dekker`, whose multiplication by the splitter overflows for
  such operands, as their requirement of no intermediate overflow allows; for them the guards
  below stand guard.
- **`kairn::rational`**: `rational_1` and `rational_2`, `kairn::rational<X>(num, den)` for one
  limb and for two, are not kernels of `gen/claims.json`. Their specification
  ([Milestone 2 statements](design/milestone2.md#constants-at-compile-time)) fixes every bit of the
  result, and the oracle knows them itself (`oracle/README.md`, "rational"): `gen rational_K F`
  writes requests of two 64-bit integers from strata of their own (every pair of small terms,
  random terms, powers of two, the extremes, $den = 0$, exact values, near-ties of either
  rounding built with the extended Euclidean algorithm, tiny second limbs), and `check` computes
  the answer in exact rationals and compares the limbs, the error and the flag for equality: one
  unit off anywhere is a failure. `tests/crosscheck.py compiled --kernel rational_K` runs them as
  it runs a kernel, without claims, and the guards ask, besides the stream and a judged case of
  every stratum, for no invalid request, exact and inexact cases and $den = 0$, and for
  `rational_2` a near-tie whose naive pair $(\mathrm{RN}(q), \mathrm{RN}(q - \mathrm{RN}(q)))$ is
  not normalized; `full.tools.crosscheck.guards` runs them on the oracle's reference runner.

## What a pass requires

Beyond the oracle's verdict (no claim violated, no line dropped or added, no invalid case, and
with `--fail-on-suspicious` no suspicious non-finite result), a cross-check passes only if the run
checked what it set out to check. An invalid case is one whose operands are outside the kernel's
requirements: the oracle counts it, shows it in its report (`INVALID`) and does not judge it. The
oracle's generator writes none, so one in a runner's output means that the runner changed an
operand, and since 2026-11-20 it fails the run (the cross-checks pass `check --expect-valid`;
before, such a case was shown and the run passed). `tests/crosscheck_guards.py` decides from the
oracle's summary (`check --json`) whether the run checked what it set out to; `tests/crosscheck.py`
calls it in its own process (`run`), `tests/crosscheck.cmake` runs it:

- **The summary stays small**: at most 4 MiB (`SUMMARY_BYTES`), checked before anything else and
  also by `tests/crosscheck.py api`. What the oracle keeps of a run is bounded by the claims and
  the format, whatever the number of lines or elements it judged (`oracle/README.md`, "The size
  of a summary"); the largest summaries of the full tier take 2.0 to 2.7 MB, and a larger summary
  means that something grows with the lines, as a map's once did ([The size of the
  summaries](#the-size-of-the-summaries)).
- **The stream is the one asked for**: one generator header, for this kernel, format and mode (and
  seed), and every index of it seen.
- **An enumeration is what it claims**: it covers every index of its enumeration, over every
  operand when no restriction is given and over exactly the restricted domain asked for
  otherwise.
- **A random run has every stratum its generator promised**: a case of every stratum the oracle's
  generator lists in its header for the kernel, and of no other; and that list includes the
  strata every family has (`uniform`, `underflow`, `overflow`, `zero`, `pow2`, `extreme`).
- **Every claim was put to the test**: at least one case was judged; every `ensures` entry applied
  to at least one judged case (an `error` entry with a `when` condition, for instance); a
  comparison saw both outcomes; a rounding to nearest saw an inexact case; a rounding down or up
  saw a case where it differs from the rounding to nearest.
- **The statements of Milestone 2** ([Claims of Milestone 2](architecture.md#claims-of-milestone-2)),
  in either domain, by the oracle's counts for each entry of the kernel's claims
  (`oracle/README.md`, "The kinds of Milestone 2"); and a random run's header lists the strata of
  the kernel's family (`special`, `binade` and `subnormal` for the neighbors; `apart`, `cancel`,
  `exact`, `close`, `beyond` and `omega` for the directed sums; `aroundp`, `tiny`, `exactprod` and
  `beyond` for the directed products; `atnormal`, `sides`, `into` and `outof` for the scalings of a
  ball by a power of two):

    | Kind | Kernels | Cases the run must have seen |
    |---|---|---|
    | `neighbor` | `next_up`, `next_down` | every row of the table of next_up and next_down: a NaN, $+\infty$, $\Omega$, a positive finite number, $\eta$, a zero, $-\eta$, a negative finite number, $-\Omega$, $-\infty$ (in the finite domain the rows it judges); a step toward zero from a power of two above the smallest normal number; a step between the subnormal and the normal range |
    | `rounded` of two operands, extended domain | the directed sums and their entry forms, `mul_down_1`, `mul_up_1` | an exact result, an inexact one that differs from the rounding to nearest, an overflow above $\Omega$ and one below $-\Omega$, a NaN operand, an infinite operand without a NaN |
    | `rounded` with `when` | `mul_down_1`, `mul_up_1` | cases where the condition holds and cases where it does not |
    | `bound` | `mul_down_1`, `mul_up_1` | a result at the directed rounding, one a step beyond it (`steps` is 1, and the listing steps below $P$), a value that is not a number of the format; in the extended domain a non-finite operand, both overflows, a NaN operand and an infinite one |
    | `exact_when` | the scalings of a ball by a power of two and their full forms | cases where every condition holds, and for each condition cases where it fails |

    The interpreter's output meets each of them on the quick and full tiers' random cases and on
    the toy formats of the enumerations; `full.tools.crosscheck.guards` has runs that miss each
    kind of class (no infinity for `next_up`, no row or step of `next_down`, a sum that cannot
    overflow, no NaN operand, products whose condition always holds, `exact_when` whose conditions
    never fail or never hold, a header without a stratum of the family) and must fail them.
- **The folds' stage of Milestone 2** (`oracle/README.md`, "The kinds of the folds' stage" and
  "Folds"). A random run's header lists the strata of the family (`integer`, `fraction`, `limit`,
  `beyond` for the bounds; `cancel`, `state`, `zerostate`, `tie`, `exactprod` for the steps of the
  dot products; `nonfinite`, `tails` for the finishes) and has a case of each. Then:

    | Kernels | Cases the run must have seen |
    |---|---|
    | the bounds `bound_sum_k`, `bound_dot_k` | for each entry, its mask true at $m \cdot \mathrm{unit}(K) = 0$, at most 1/5, and between 1/5 and 1/4 (just below the limit); false between 1/4 and 1/2 and beyond 1/2 (where `holds` cannot be true); a count that is not an integer; the first bound, $g$, within 8 gaps of its stated value somewhere (the interpreter and the compiled kernels come within 1.3 to 2.9 gaps; a $g$ twice as large would be $2^p$ gaps away), except in a format of fewer than 8 bits that has no count with the mask true and a positive stated value (at one bit the mask is true at $m = 0$ only), where there is nothing to come close to; in `binary64` and `binary32` no false mask at or below 1/5 (milestone2.md: ok is true there for every $m\varepsilon \le 0.24$) |
    | the finishes `fold_finish_k` | a finite state, an infinite and a NaN leading limb; for two limbs a finite leading limb with a lower limb that is not finite |

    **A fold** must have seen, on its judged arrays with a true flag (the counts of `fold_error`):
    every length class, 0, 1, 2, 3, 4, 5, 7, 8, 9, 16, 17 and a random length above 17 (in an
    enumeration every length up to its largest); every order its header asks for (`seq`, each
    `lanes:W`, and more lanes than elements for `lanes:big`; a stream of the packed runners asks
    for its `lanes:W` only); heavy cancellation, an exact sum within $u$ of the sum of magnitudes
    (but in an enumeration of arrays of one element); for a dot product, where $\tau > 0$, a case
    where the absolute term is the larger part of the bound and one whose error is above the
    relative term alone; and an error that is a visible fraction of the bound: at least 1/2 of it
    for the folds of one limb and 1/16 for those of two, so that a bound a thousand times too
    loose cannot pass. What the interpreter reaches, in the quick tier's 300 arrays and in toy
    formats: 0.76 to 1.00 of the bound with one limb (an addition that drops an element just
    below half a unit of the sum attains the bound), 0.15 to 0.33 with two (the literature's tight
    case of `add_2_2` makes a third: its error is $3u^2$ of $\lvert x+y\rvert$, a third of
    $\lvert x\rvert + \lvert y\rvert$) and up to 0.9995 for `dot_2` in `binary64` (MR22's case of
    `mul_2_2`). In the full tier (1 000 arrays per format and scalar runner of the compiled folds,
    500 per packed one, 1 000 sampled in a toy format, every array of the enumerations): 0.83 to 1.00 with one limb, 0.11 to 0.47 for
    the sums of two, 0.21 to 0.9995 for `dot_2`. And of the flag (the counts of `finite_or_nan`): a true flag, a false one from an
    element that is not finite, a false one from finite elements near the overflow threshold; and
    no false flag from finite elements far from overflow (every node of any summation tree below
    an eighth of the threshold; the oracle also counts such a line suspicious, which fails the
    cross-checks by itself). The stream is the one asked for: its orders and its largest length
    are those of the header (`--orders`, `--max-length` of the drivers and of the guards).
    `full.tools.crosscheck.guards` has runs and altered summaries that miss each of these (a
    length, an order, a flag outcome, cancellation, the term $\tau$, a ratio a thousand times
    smaller; the bounds on one side of the limit, never close, ok false early; a finish without a
    NaN or a lower limb not finite; a stratum of a family) and must fail them.
- **Stage B of Milestone 2** (`oracle/README.md`, "Maps", "Folds of maxima", "Convolutions"). A
  random run's header lists the strata of the generator (`genmap.py`): for a map `one`, `wide`,
  `cancel`, `tie`, `exact`, `overflow`, `underflow`, `zeros`, `nonfinite`, `tight` and, for groups of
  two limbs, `tail`; for a fold of maxima `one`, `wide`, `ties`, `position`, `zeros`, `underflow`,
  `top`, `nonfinite` (and `tail`); for a convolution those of a dot product; for the kernels the
  families `axpy` (`cancel`, `state`, `tie`, `exactprod`, `tight`), `maxof` (`equal`,
  `neighbor`, `negative`) and `maxfinish` (`nonfinite`, `top`, `smallstep`). Then:

    | Objects | Cases the run must have seen |
    |---|---|
    | a map | every length class and order asked for (as a fold); an element of finite operands with a finite result, one of finite operands that is not finite (an overflow), one with an operand that is not finite; the flag true, false from a non-finite operand, false from an overflow; every entry of the step applied, a rounding to nearest inexact, and the step's error at least 1/2 of its bound for one limb and 1/16 for two (the compiled runners reach 1 with one limb, $1 - 8u$ for the sums of two, 0.39 to 0.99 for the products and axpy of two in the quick tier, 0.61 to 0.99 in the full tier) |
    | a fold of maxima | every length class and order; the largest at the first, the last and another element, attained more than once; every element zero, no element; the result at $\mathrm{RU}(V)$ and, for two limbs, one step above it, and $V$ not a number of the format; the flag true and false from a non-finite element, and for two limbs false from finite elements whose bound's top is beyond $\Omega$ (in an enumeration only what its lengths can have) |
    | a convolution | lengths 0 and 1 of each array, unequal lengths, lengths above 2 of each (in a random run); a coefficient of finite terms with a finite result, one that overflows, one with a term that is not finite; the flags of a map; coefficients of one and of two terms, heavy cancellation, for the products the term $\tau$ mattering both ways, and the fold's error at least 1/2 of its bound for one limb and 1/16 for two |
    | the steps of axpy | the error at least 1/2 of its bound for one limb and 1/64 for two (the interpreter: $1 - O(u)$ with one limb, 0.25 to 0.73 with two) |
    | `norm_combine`, `norm_step_k` | each argument larger, and both equal |
    | `norm_finish_k` | the mask true and false, a finite value stepped up to a finite one, a NaN, an infinity, and for `norm_finish_2` a finite value stepped up to $+\infty$ |

    `full.tools.crosscheck.guards` has runs and altered summaries that miss each of these (a class
    of elements or of the flag, a step far from its bound, entries other than the step's; where the
    largest is, the result one step above $\mathrm{RU}(V)$, the bound's top beyond $\Omega$; a
    length of a convolution, a coefficient's class, cancellation, its error far from the bound, an
    order other than `seq`; the strata of the families of the kernels, axpy far from its bound, a
    class of a finish or of a maximum) and must fail them.

- **The ball vectors and the accumulator** (`oracle/README.md`, "Ball vectors and the
  accumulator", "Their kernels", "Their folds"). A random run's header lists the strata of the
  generator: for the kernels the families of `gen8.py` (`radius`: `huge`, `zeros`, `mixed`,
  `atnormal`; `acc`: `cancel`, `tie`, `exactprod`, `apart`, `atop`; `accradius`: `integer`, `limit`,
  `beyond`, `abig`; `bvfinish`: `nonfinite`, `negative`, `zeros`, `top`, `masks`); for the folds
  those of `genbv.py` by shape (a ball vector `one`, `wide`, `zeroradius`, `whole`, `overflow`,
  `threshold`, `cancel`, `underflow`, `zeros`, and `nonfinite`, `exact` and `tail` where they apply;
  a constructor `one`, `badradius`, `badcenter`, `zeros`, `overflow`, `underflow`; a product those
  of a ball vector, `count` among them). Then:

    | Objects | Cases the run must have seen |
    |---|---|
    | a radius kernel | an output $+\infty$ and a finite one at least the stated value; with `exact_when`, the conditions holding and each failing, the output exactly the stated value, the mask true where nothing is claimed; whose claim is of finite results (`conv_radius`, whose results that are not finite are counted and judged no further), finite results at least three quarters of those judged |
    | a step of a scaling | `exact_flag` true and false, `exact_when` holding |
    | a finish | every mask true and each false, a value zero, below zero, above zero, a NaN, $\pm\infty$ |
    | a step of the accumulator | a rounding inexact, an output group not finite (nothing claimed) |
    | a ball vector | every length class and order asked for (as a fold); a finite result and the whole space; an operand that is the whole space and finite operands; V4 applying, of no entry too, or the count `V4 not claimed` below `finite_from` or in a format of no statement of V4; with `exact_when`, every condition holding and each failing; in place (`--inplace`), every array of the limbs of the array written |
    | a constructor | each class of the radius given (negative, $-\infty$, NaN, $+\infty$, $\pm 0$, positive) with finite centers, and a positive radius with centers not all finite |
    | a product of BallVectors | lengths 0 and 1 of each array, unequal lengths; both results, a whole-space operand, V4 applying; the radius at least `conv_radius`'s stated value; in a toy format `count_when` failing |

    `full.tools.crosscheck.guards` has runs and altered summaries that miss each of these (a
    class of a radius, `conv_radius` with too few finite results, a stratum, a mask of a step, a
    cell of a finish or of an accumulator; a
    class of results, of operands, of V4 or of exactness of a ball vector, a class of radius of a
    constructor, a length, the count or the radius of a product, `count_when` never failing, V4
    outside its formats or below `finite_from` not said; a stream in place without its arrays, or
    in place when it was not asked, and the reverse) and must fail them.

- **The interval kernels of Milestone 2** (`oracle/README.md`, "The kinds of the interval
  kernels"). A random run's header lists the strata of the family (`gen6.py`: `special`, `point`,
  and `threshold`, `cancel`, `zerosum` for the sums, `threshold`, `zeroinf`, `aroundp` for the
  products of intervals; `special`, `point`, `disjoint`, `touch`, `nested` for the hulls and
  intersections; `nanbound`, `reversed`, `infinities`, `point`, and `oddeta`, `top` for a ball,
  for the constructors; `special`, `point`, `step`, `oddeta`, `top` for the midpoint, the
  conversion and the split; `ballstates`, `radii`, `cross`, `beyond`, `exactend` for the bounds of
  a ball; `cancel`, `zerosum`, `close`, `apart`, `tiny` for the bounds of two-limb sums, `close`,
  `tiny`, `aroundp`, `exactprod` for the products, with `nonfinite`, `zeroinf`, `edge` in the
  extended domain; the directed products' strata and `nonfinite`, `zeroinf`, `zerofactor` for
  `mul_dir_1`), and a case of each (they replace the strata the non-finite layer adds). Then:

    | Kind | Kernels | Cases the run must have seen |
    |---|---|---|
    | `encloses_interval` | `interval_neg_k`, `interval_add_k`, `interval_sub_k`, `interval_mul_k` | an empty operand, an unbounded one, bounded operands; an empty, a bounded and an unbounded result; `bounded_when` holding and, for two operands, failing, with a range within a factor 2 below its limit and one within a factor 2 above it (the results near the overflow threshold on each side); with `tight` rounded, each bound of the range a number of the format, not one, and infinite, one step beyond the rounding where `steps` is 1 and `product_large` both ways; with `tight` outward, an infinite bound of the range, each side's `exact_when` holding and each of its conditions failing, and a distance of at least 1/4 of $\mathrm{rel}\lvert v\rvert + \mathrm{abs}$ on each side; with `zero_factor`, an operand $[0, 0]$, against an unbounded one too |
    | `outward` | the bounds of two limbs, `mul_ext_2_2` | `exact_when` holding and each condition failing; a distance of at least 1/4 of $\mathrm{rel}\lvert v\rvert + \mathrm{abs}$; in the extended domain a zero operand, an infinite one, a finite and an infinite output from finite operands |
    | `makes_interval`, `makes_ball` from an interval | `interval_make_k`, `ball_from_interval_2` | each given class of the [case analysis](architecture.md#the-constructors-on-every-pair-of-values): an interval, a point, an unbounded interval; a NaN bound and equal infinities, $[+\infty, +\infty]$ or $[-\infty, -\infty]$ (both the whole line, the second since the owner's decision of 2026-11-20); reversed bounds (the empty set); and every cell of its table, each of the four kinds of lower bound (a NaN, $-\infty$, a finite number, $+\infty$) with each of the four kinds of upper bound, two finite bounds both ways ($a \le b$ and $a > b$): 17 cells, each seen by the quick tier's runs and by every enumeration; for bounds of two limbs (`interval_make_2`) also reversed bounds with equal leading limbs, such as $(1, 2^{-4})$ and $(1, 0)$, and, but in an enumeration, which has one zero, the same infinity with second limbs that are zeros of opposite signs, $(+\infty, 0)$ and $(+\infty, -0)$; `midpoint_when` holding and failing |
    | `set_bound`, `interval_of_ball` | the bounds of a ball, `ball_to_interval_1` | the empty ball, the whole line, a finite ball; each bound of the set a number of the format and not one |
    | `interval_set` | the hulls and intersections | an empty operand, both empty, disjoint, touching and overlapping operands; an empty, a bounded and an unbounded result |
    | `ball_of_interval`, `splits` | `interval_mid_rad_1`, `interval_to_ball_1`, `interval_split_1` | $X$ empty, the whole line, a half-line on each side, bounded, a point; for the midpoint a bound an odd multiple of $\eta$ below $2N$ and a distance of at least 1/2 of $u\lvert m\rvert + \eta$ |
    | `bound`, `rounded` with `zero_factor` | `mul_dir_1` | a zero operand, a zero against an infinite one; the classes of the directed products, but a NaN operand (`not_nan()`) |

    The floors: the interpreter and the compiled kernels come to 0.60 to 0.70 of the bounds of two
    limbs in `binary64` and `binary32` and 0.36 to 0.49 in the toy formats, and to 0.97 to 1 of
    the midpoint's bound; 1/4 and 1/2 let a bound four (two) times too loose fail. The
    interpreter's output meets every one of these on the quick and full tiers' random cases and on
    the enumerations of the toy formats; `full.tools.crosscheck.guards` has runs and summaries
    that miss each (no empty operand, `bounded_when` that never fails or a range never near its
    limit, a rounding never a step beyond or never inexact, `product_large` one way, a bound or a
    midpoint far from its bound, `exact_when` that never holds or never fails, I6 never applied,
    no zero against an infinity, a constructor never given a NaN bound, never the same infinity
    twice (a run without the stratum `infinities`) or without a cell of the table, no empty ball,
    no disjoint intervals, no odd bound, no half-line, a header without a stratum of the family)
    and must fail them.

For a kernel of the extended domain the run must also have seen what that layer is about. The
guards read the kernel's claims (the file the oracle's summary names) and the oracle's counts of
the classes of each statement (`oracle/README.md`, "The extended domain"):

- **The strata of the layer**: a random run's header lists, besides those of the kernel's
  family, the strata the oracle's generator adds for it: `nonfinite` for every kernel, `zeroinf`
  where the value or the set has a product, `edge` for `extends`, `threshold` where
  `finite_when` is not empty, `ballstates`, `zerowhole` and `hugeradius` for `encloses`,
  `badradius` for `makes_ball`; and, as for every stratum, a case of each.
- **Every class of every statement**, counted by the oracle for each entry of the kernel's own
  claims:

    | Kind | Kernels | Cases the run must have seen |
    |---|---|---|
    | `extends` | the nine full kernels | a finite result (F2), an overflow on finite operands (F4), a non-finite operand (F5); where `finite_when` is not empty, a case where every condition holds (F3 applies) |
    | `encloses` | the eight full Ball kernels, `ball_neg_1`, `ball_neg_2` | each of the three results: a finite ball, the whole line, the empty set; where `finite_when` is not empty (the eight full Ball kernels), a case where every condition holds (B4 applies) |
    | `represents` | `make_2`, `make_2_limbs`, `neg_2`, `abs_2` | a finite, an infinite and a NaN value |
    | `makes_ball` | `ball_make_1`, `ball_make_2` | each given state: a finite ball, the whole line (a center that is not finite, or a radius $+\infty$ or NaN), the empty set (a negative radius, $-\infty$ included, whatever the center); and each class of the given radius (negative, $-\infty$, NaN, $+\infty$, $+0$, $-0$, positive) with a finite center and with one that is not, $-0$ but in an enumeration, which has one zero |
    | `normalized`, `error` | `neg_2`, `abs_2`, `ball_neg_2` | a non-finite operand |
    | `rounded` | the conversions | a non-finite operand |
    | `predicate` | the comparisons | a non-finite operand with each outcome |
    | `upper` | `radd`, `rmul` | a NaN (a NaN operand, or $0 \cdot \infty$) and $+\infty$ from a non-finite operand |

    The guards of the finite domain apply to these kernels as before, to their finite cases and
    to the entries of the core that F2 applies. The oracle does not count the corner where a zero
    ball meets the whole line ($0 \cdot \infty$ in a radius, which must give the whole line, not
    the empty set) separately, so no guard asks for it: the complete enumerations contain it, as
    does the restricted one of `ball_mul_2_full`, and a random run has the `zerowhole` stratum.

`full.tools.crosscheck.guards` runs pipelines that the oracle passes but these guards must fail (a partial
enumeration, a restricted one passed off as complete, missing strata, nothing judged, a comparison
that was never true; in the extended domain, an enumeration of `add_2_2_full` without an overflow
or where `finite_when` never holds, one of `ball_add_1_full` whose radius makes every result from
finite operands the whole line, random runs without non-finite operands, without the empty set or
without one of a constructor's outcomes, a constructor's good run with one class of radius taken out of its summary, headers without the strata of the layer), and summaries
altered where no stream can produce the fault (entries that are not those of the claims, claims
that cannot be read, a summary padded beyond the bound on its size); and both drivers on such runs, which they must fail with the guards'
reason, and on good ones: `tests/crosscheck.py compiled` with the interpreter as its runner
(`--interp`), `tests/crosscheck.py api` with the build's runner of the public interface (a good
run, one of 5 cases, which misses strata, and a kernel it maps no form to), and
`tests/crosscheck.cmake`; and `tests/crosscheck.py compiled` on the reports of a packed runner's
lanes (`LaneReports`): a good one passes, and one of another assignment, of no segment or of
another stream, one whose guard failed and one that cannot be read fail
([Packed kernels](#packed-kernels)).

## Packed kernels

`gen/tests/packed_runner.cpp` runs the packed kernels of `kairn/gen/neon.hpp` (two doubles or four
floats per register) or `kairn/gen/avx2.hpp` (four or eight), whichever the target has: the
requests for one kernel and format are evaluated $W$ at a time, one per lane of a register of
$W$ lanes, and the completed lines are printed in the order of the requests. The oracle judges
its output like the scalar runner's, on the same cases, under the same contraction settings, and
needs to know nothing of the lanes.

The backend and its option are chosen as `kairn::fma`'s option is: NEON if the backend's header
compiles with the build's flags (AArch64), otherwise AVX2 with nothing added if the flags already
enable it, or with `-mavx2 -mfma` (GCC, Clang) or `/arch:AVX2` (MSVC, clang-cl), each tried by
compiling the header. On a target with neither, no packed runner is built, and configuring says
so. On x86-64 the CPU that runs the tests needs AVX2 as well as FMA.

### The two assignments of the lanes

A packed kernel selects in each lane between its ordinary result and its special results (an
infinity, a NaN, the whole line). A fault that lets one lane's selection reach another (a mask
built from the wrong lane, a blend with the lanes exchanged, a horizontal test where a per-lane
one is needed) changes a result only in a register whose lanes hold different kinds of values.
Until 2026-11-21 the runner filled each register with consecutive requests, and the oracle's
stream takes its strata in turn, so a register held requests of one kind. Counted on the
quick tier's stream of each kernel (seed 0, 6 000 cases), a register mixing a request with a
non-finite limb and one whose limbs are all finite, for W = 2 / 4 / 8:

| Kernel | Consecutive | Permuted (seed 0) |
|---|---|---|
| `mul_2_2_full` | 0 / 0 / 300 | 942 / 882 / 625 |
| `add_2_2_full` | 0 / 333 / 333 | 588 / 553 / 464 |
| `neg_2`, `to_down_2`, `abs_2` | 0 / 600 / 600 | 970 / 875 / 637 |
| `lt_2_2` | 0 / 375 / 375 | 646 / 611 / 486 |

of 3 000, 1 500 and 750 registers (the same counts in `binary64` and `binary32`, whose streams
have the same strata). With the consecutive assignment no register mixed at W = 2, the NEON form
of `double`; and some kinds (a stratum with finite or non-finite limbs) never reached some lanes:
5 to 12 of the pairs of a kind and a lane at W = 2, 20 to 88 at W = 8. With the permuted one,
every kind of at least W requests reaches every lane.

The runner now reads a whole **segment**, a run of requests for one kernel and one format (a
comment, an empty line, a fold, a map, a request of another kernel or format, or the end of the
input ends it), assigns its $n$ requests to the slots of $R = \lceil n/W \rceil$ registers, calls
the packed kernel once per register, and prints the $n$ lines in order. The **kind** of a request
is its stratum (the label of its tag `#STRATUM:INDEX`; none for another tag) and whether one of
its limbs is not finite. Two assignments, chosen by `--lanes`:

- **permuted** (the default): the requests grouped by kind, in the order the kinds first appear,
  the requests of each kind shuffled; the groups, one after the other, fill the slots register by
  register, so that a kind of $c$ requests takes $c$ consecutive slots and is in every lane once
  $c \ge W$; then the slots of each lane are shuffled among the registers, an independent
  permutation of the $R$ registers per lane, so that the lanes of a register hold kinds drawn
  independently. The random numbers are SplitMix64 on 64-bit unsigned integers, seeded from
  `--lane-seed` (default 0; the cross-checks pass their `--seed`) and the segment's number, an
  integer below $m$ drawn by rejection of the draws below $2^{64} \bmod m$, and Fisher–Yates
  shuffles: integer arithmetic only, no `std::shuffle` or distribution of the standard library,
  so the same requests and seed give the same assignment with every compiler and on every target.
  The generator's tests compute the plan again in Python and require every build to report the
  same one (`Lanes` of `gen/tests/test_simd.py`).
- **consecutive**: request $k$ in lane $k \bmod W$ of register $\lfloor k/W \rfloor$, the old
  assignment. Registers of one kind are a case too, and the generator's special groups (one
  special operand in each lane in turn) are aligned with these registers.

The quick tier runs every packed runner with the permuted assignment (labelled as before:
`neon`, `neon-contract-off`, ...) and the runner with the build's flags also with the
consecutive one (`neon.consecutive`); the full tier runs every packed runner, the flag sets'
included, with both. A correct runner writes the same bytes with both, which then share the
verdict of the scalar runner's output and cost the oracle nothing; each run costs the runner's
own time, some 70 ms on 6 000 lines. The generator's tests run both on every build of their
matrix. `tests/regression/run.py` and the brute-force driver run the default, permuted.

**The guard.** Under the permuted assignment (and under the consecutive one with
`--lane-guard`), on a segment of at least 256 requests, every kind of at least W requests must
have been in every lane, and if at least 16 requests have a non-finite limb and 16 only finite
ones, at least one register must have held both. Otherwise the runner prints the segment's lines,
says which kind missed which lane or that no register mixed, and exits with 3. A kind of fewer
than W requests cannot reach every lane and is not asked to. The construction makes the first
condition hold whenever the assignment is the one described; the second fails by chance with a
probability below $10^{-12}$ at these sizes. Applied to the consecutive assignment of the oracle's
stream of `mul_2_2_full`, the guard refuses it at every W (`crosscheck.lanes.fault.F` checks
so).

**What a test keeps.** `--lane-report FILE` writes, per segment, the kernel, format, requests,
lanes, registers, padding, the registers that mixed (non-finite with finite, and two strata), the
requests of each kind in each lane, and the guard's verdict. `tests/crosscheck.py` gives each
packed run such a file, fails the test unless it reports one segment of every request with the
assignment asked for and, for the permuted one, the guard passed (or not applied to a stream of
fewer than 256 requests), keeps it next to the summaries as `crosscheck.compiled.K.F.LABEL.lanes.json`
(1 to 2 KB), and prints its counts with the pass, for example `lanes of neon: 2 lanes, the
permuted assignment (seed 0): 3000 registers, 942 of them mixing a non-finite limb with finite
ones (1200 and 4800 requests), ...`. `--lane-plan FILE` writes the slot of every request
(`SEGMENT REGISTER LANE LINE`): a case that fails only beside the other lanes of its register
fails only in the whole stream with the same seed, not alone, and the plan says which requests
shared its register (the failure text of a packed run says how).

**A register that is not full.** The last $RW - n < W$ slots (at the end of the last register
with the consecutive assignment, in random registers and lanes with the permuted one) are
padding. Until 2026-11-21 they repeated the batch's first request, which could have a non-finite
limb, and their results were dropped; the cross-checks never had one (6 000 and 2 000 are
multiples of 8). They now hold a copy of the segment's first request whose limbs are all finite
(its first request if none is: a request the kernel accepts in any case), and their results are
dropped; the report names the line copied. The generator's tests run streams of 1, $W - 1$,
$W + 1$, $2W + 1$ and 257 requests whose first request is non-finite, with both assignments,
on every build: every line as the scalar runner completes it, the padding the first finite
request (the only request, in a stream of one).

**The planted fault.** `tests/lanes/lane_fault.hpp` is a copy of the generated `mul_2_2_full`
whose select returns the core's product where its leading limb is finite and the four limbs of
the operands are finite, the second mask taken from the neighboring lane (lane $i$ reads lane
$i + 1$). The second condition is redundant in the correct kernel, so the copy is right in every
lane whose neighbor's operands are of its kind, and gives an infinity or a NaN in place of the
product of finite operands beside a non-finite one. `crosscheck.lanes.fault.F` builds the packed
runner with it (`KAIRN_RUNNER_HEADER`, and `KAIRN_RUNNER_TABLE` for a table of this kernel alone)
and runs the cross-check of the quick tier's 6 000 cases (`tests/lanes/lane_fault.py`):

| Form | W | Consecutive | Permuted |
|---|---|---|---|
| NEON, `binary64` | 2 | 0 of 3 000 registers mix: passes | 942 mix: the oracle fails 768 lines |
| NEON, `binary32` | 4 | 0 of 1 500: passes | 882 mix: fails 792 lines |
| AVX2, `binary64` | 4 | 0 of 1 500: passes | 882 mix: fails 806 lines |
| AVX2, `binary32` | 8 | 300 of 750 mix: fails 251 lines (printed, not required) | 625 mix: fails 795 lines |

(the oracle's failures are F3, a result that is not finite although every `finite_when`
condition holds, and F4). The test requires the consecutive cross-check to pass where no register
mixed and the permuted one to fail by the oracle's verdict, not the runner's or the guards'. The
verdict is read from the oracle's summary of the output, failed lines and no claims error: the
oracle's check exits with 1 also when it refuses the claims (a kernel whose claims it cannot read
fails every run), and such a refusal is an error of the test in either assignment, never the
failure it expects (`full.tools.crosscheck.guards.LaneFaultVerdicts` checks the reading on real
summaries of both). The
fault is planted in the operands' mask and not in the generated one (the core's product finite)
because that one also fails for finite operands whose product overflows, which the strata
`edge`, `threshold` and `overflow` put next to products that do not in consecutive lines: the
same neighbor's mask planted there is caught by both assignments (598 lines with the consecutive
one at W = 2).

The runner built with that kernel, `kairn-gen-packed-runner-lane-fault`, is not a runner of the
library, and the brute-force tier does not run it: `brute.py` takes as runners the targets
`kairn-gen-runner` and `kairn-gen-packed-runner` with their suffixes, except those whose suffix
ends in `fault` (`runner_target`, with tests in `tests/brute/test_brute.py`). For one night it did:
the scheduled run of 2026-11-21 took the planted fault for the library and failed on every
platform.

**The folds and the maps** have no such assignment: `F_packed` deals the elements of one array
to the lanes, $W$ consecutive elements per register, and runs the last $n \bmod W$ in a scalar
loop (no padding), and the runner calls it once per request line. Counted on the streams the
packed runners get (seed 0, every fold and map with a packed form, both formats, both backends),
the lengths are not the weakness: in the quick tier (200 arrays of up to 256 elements for a fold,
100 of up to 24 for a map or a fold of maxima) 6 to 12 arrays are empty, 6 to 72 shorter than W,
and 45 to 81 % leave a remainder. Nor are arrays of one kind: almost every array with a
non-finite element has finite ones too. The weakness is how few non-finite elements there are: in
the quick tier 6 of 100 arrays of a map have one (15 of 200 for a sum or a dot product, 14 to 16
of 100 for a fold of maxima), 7 to 34 elements of a stream, and 3 to 27 registers of a stream mix
one with finite ones; so at W = 8 (`binary32` with AVX2) 27 of the 28 streams leave one to six of
the eight lanes without a non-finite element in a register (`axpy_1_entry`: 1 and 3 elements in
two lanes, none in the other six), and at W = 4 14 of 56 leave one or two. In the full tier (500
arrays) every lane has some at W = 2 and 4 (46 to 144 elements per stream), and 2 of 28 streams
leave one lane without at W = 8. A fix belongs to the oracle's generator of arrays (more arrays
with non-finite elements, or their positions spread over the lanes), not to the runner, and is
left for it; the packed loops' own tests in the generator's suite (lengths 0, 1, $W - 1$, $W$,
$W + 1$, $2W$ and random ones, non-finite elements among them) also reach those lanes.

## Packed and the containers

`Packed<T, k>` ([reference](../reference/packed.md)) and the containers of `kairn/soa.hpp`
([reference](../reference/soa.md)) are tested in every form of `Packed` the build can make: the
form of the build's flags (`native`: AVX2, NEON, or the scalar form of one lane), the scalar form
forced with `KAIRN_PACKED_FORM_SCALAR` (`scalar`), and, on x86-64 where the build's flags give the
scalar form and the compiler can target AVX2 with the packed backend's option (`-mavx2 -mfma`, as
for the packed runner above), `avx2`. That is the case of the default build with GCC and Clang
there, whose `kairn::fma` adds `-mfma` alone; with MSVC and clang-cl `/arch:AVX2` gives the AVX2
form natively, and on AArch64 NEON.

- **The oracle, through the public interface.** The runner of the public interface has a packed
  form for each of its forms that `Packed` or a view has (`packed_plus` of `add_2_2_full`,
  `packed_less` of `lt_2_2`, `packed_soa_load` of `make_2_limbs`, ...): 64, for the 34 kernels that
  `kairn/packed.hpp` calls. A packed form holds the stream until its end, puts its lines in an order
  drawn by a fixed pseudo-random sequence, and fills the registers $W$ lines at a time in that
  order: the oracle writes its strata in a fixed pattern, so that consecutive or strided lines would
  put the non-finite cases together and a stratum always in one lane position. Each operand is loaded
  from arrays as a program loads it (`Packed::load`), each result stored and written on its line;
  the oracle judges the output against the claims of the scalar kernel, as for any form, and an
  output identical byte for byte to the scalar form's is not judged again. The runner prints, per
  packed form, the lines per lane position and the registers that mixed finite and non-finite
  operands and results, and fails a stream of 1 000 lines or more that left a lane position without
  a line, or whose non-finite operands or results never shared a register with finite ones. The
  packed forms are in every runner of the public interface: the quick tier's two (the build's flags,
  contraction forced on), the full tier's flag sets and settings of `KAIRN_ENCLOSURE_CODE`, and,
  where the `avx2` form applies, a third, `kairn-api-runner-avx2`, built for AVX2 with
  `KAIRN_TEST_PACKED_ONLY` so that it lists only its packed forms, in `api.oracle.K.F` and
  `full.api.oracle.K.F` of the kernels K that `kairn/packed.hpp` calls (found in its text at
  configure time, the set `api.oracle.coverage` checks against the runner's packed forms).
- **Bit for bit against the scalar operations** (`api.packed.FORM`, `tests/api/packed.cpp`). Every
  operation of `Packed`, for `float` and `double`, one and two limbs, against the public operation
  of `Expansion` of the same name, lane by lane: on every pair (or operand) of a corpus of zeros of
  both signs, subnormal numbers, the smallest normal number, ordinary and random numbers across the
  range, the largest finite number and pairs near it whose results overflow, the infinities and
  NaN, the pair in lane $k mod W$ for the $k$-th pair and the other lanes filled from the corpus
  by a fixed sequence; every limb of every lane compared, a NaN as a NaN, and with MSVC a zero as
  a zero of either sign: MSVC removes the addition of $+0$ that guards an operand of a packed
  kernel, so a limb $-0$ keeps its sign there
  ([Packed](../reference/packed.md#packed-numbers-in-registers); the reads of `api.soa.FORM`
  through `Packed` are compared the same way, and what a store writes to an array bit for bit
  with every compiler). It fails if an operation of the extended domain met no register mixing finite and non-finite
  operands (or results, an overflow in one lane only). Also the masks (`any`, `all`, `lane`, `&`,
  `|`, `!`, `select`, a mask with each lane alone set), the moves against the scalar constructors
  (`broadcast`, `lane`, `set_lane`, `load` and `store` from arrays one element off any register
  alignment, `load_partial` and `store_partial` for every count, `from_limbs`), and the type's
  properties.
- **A product of the program** (`api.boundary.packed.FORM.S`, `tests/api/boundary_packed.cpp`),
  what `api.boundary.S` checks for `Expansion` and `Ball`
  ([above](#the-quick-tier)), for each way a register or a value enters
  `Packed`: `Packed<T, 1>::from_limbs` of a register followed by `x + a`, `a + x`, `x - a`, `a - x`,
  `+=`, `-=`, `Packed<T, 2>(a)`, `add_fast`, the functions of `kairn::finite`, after a negation, an
  `abs` or a `select`; `Packed<T, 2>::from_limbs` and `from_limbs_unchecked` with the product as the
  leading limb; `broadcast` and `set_lane` of a number made from a product in `T`; `load`,
  `load_unchecked` and `load_partial` (the product as `fill` too) of arrays the program fills with
  products, or stores a register of products into; views of those arrays (`load`, `load_partial`,
  the proxy, `get`, `set`, an assignment through the proxy, `store`); and an `SoA` whose limbs or
  elements the program writes. Each form is computed with the product written in place (`a * b`
  in `T`, or the form's own intrinsic, `_mm256_mul_pd`, `vmulq_f64` and their `float` forms) and
  with the rounded product (through a `volatile`, in a function that is not inlined), on factors
  in $[1/2, 1)$ and a leading limb within a few units of $\mp$ their product, so that the sums
  cancel, a different pair in each lane; every limb of every lane is compared bit for bit, a zero
  as a zero with MSVC. `double` and `float`, 40 000 registers of each per form, in the forms
  `native` (where it has more than one lane), `scalar` and `avx2` (where it applies), at `-O2`
  under each contraction setting of `api.boundary.S`. Products that are only multiplied or
  compared (`x * a`, `a * x`, `*=`, `kairn::finite::mul`, the comparisons) need no guard and must
  agree in every build. The control, `api.boundary.packed.unguarded.FORM.S`, builds the test
  against the copy of the headers without the guard, which also keeps only `a` of every
  `_mm256_add_pd(a, _mm256_setzero_pd())` of `gen/avx2.hpp` and `vaddq_f64(a, vdupq_n_f64(0.0))`
  of `gen/neon.hpp` (and their `float` forms), and requires that some form differ where the
  compiler was measured to fuse: GCC by default and under `-ffp-contract=fast` (GCC 16 on
  AArch64 in the forms NEON and scalar, GCC 13 on x86-64 in AVX2 and scalar), and Clang under
  `-ffp-contract=fast` on AArch64 (Apple clang 21, NEON and scalar; Clang 18 on Linux in the
  scalar form only: it fused no product written with the NEON intrinsics, in any of 40 000
  registers of any form, so its NEON build only reports). A form that differs there
  differs in every register, in every lane position. Which forms differ depends on the compiler
  and the form (with GCC 13 and AVX2, 18 of the 42 that need the guard; with Apple clang and NEON,
  35), and each of the 42 differs on one of them at least, but `abs` and the four forms of
  `load_partial`, which none of them fused even without the guard: for those, the test shows only
  that nothing fused them. Clang 18 on x86-64 fused nothing without the guard, in either form and under every
  setting, and MSVC and clang-cl were not measured with `Packed`: their controls only report,
  and say that nothing differed when nothing did. With the guard no form differs, on any of these
  compilers, in any form or setting.
- **The containers** (`api.soa.FORM`, `tests/api/soa.cpp`): an element read is the value written,
  for every index of arrays of 0, 1, $W - 1$, $W$, $W + 1$, $2W - 1$, $2W + 1$ and 37 elements,
  through the proxy, `get`, a const view, a const `SoA` and `load` (the limbs of `from_limbs` of the
  limbs written, which are in the arrays bit for bit); the tail rule, which reads and writes exactly
  the $N$ elements; views of `std::vector` and plain arrays, `subview`, a view of one limb over a
  plain array; the properties of the types (trivially copyable views, the conversions that exist
  and those that must not, `set` and `store` absent from a view of `const T`); and allocations,
  counted by the program's own replacement of `operator new`: views, proxies, element access, load
  and store allocate nothing, an `SoA` once per constructor with a size, copy and `resize`, never
  in a move, and its arrays start at multiples of 64 bytes.
- **What must not compile** (`api.reject.soa.*`, `api.reject.packed.*`,
  `api.reject.packed_form.*`, in the table above; `tests/api/reject.cpp` includes the two headers
  in their cases only, since every case is compiled twice).
- **The checks** (`api.checks.*`): the table of `checks_cases.hpp` has operations of `Packed` and
  of the views of each kind: eleven that round (sums and products of two limbs and their mixed
  forms with a limb, `float` and `double`, `ldexp`, a finite core, a load, `from_limbs` and three
  reads of an element, which are `from_limbs`), each of which must stop the program under each state of the
  environment, every operation of a kind having the same check (`packed.hpp`); the comparisons,
  negations, `abs` and conversions to one limb, run on the corpus $W$ values at a time, which must
  give the same bits under every rounding mode; and the moves and the constructor from one limb,
  checked for nothing; and the operand cases have a lane that is not canonical among canonical ones given
  to a load, `from_limbs`, an operator, a comparison and a finite core, and an element of a view
  read through `get`, the proxy and `load`, each of which must stop the program with its message.
- **The tutorial's vector loop** (`api.example.packed_dot.FORM`, `docs/examples/cpp/packed_dot.cpp`),
  in each form: its output, which is the same in every form, against `packed_dot.txt`, and each of
  its results against the bound the tutorial states, decided against an exact reference in 192-bit
  integer arithmetic.

## Contraction

A compiler may fuse a product and an addition into one FMA ("contraction"), which changes the
result. In Phase 0 that broke the textbook double-word product under some settings
([Environment](design/phase0/environment.md#contraction)); the generator's rules R1 and R2 are
meant to make every kernel immune. The contraction tests check that the compiled kernels, scalar
and packed, still satisfy their claims under each setting that matters to the compiler:

| Compiler | Settings, as added to the build's flags |
|---|---|
| GCC, Clang, Apple clang | `-ffp-contract=off`, `-ffp-contract=on`, `-ffp-contract=fast` |
| MSVC | `/fp:precise`, `/fp:contract`, `/fp:strict` |
| clang-cl | `/fp:strict` (off), `/fp:precise` and `/fp:contract` (on), `/clang:-ffp-contract=fast` |

Compilers contract across statements only when they optimize, which is why a build of Kairn on
its own defaults to `Release` (within one expression, Clang and GCC 16 under `-ffp-contract=on` fuse
at `-O0` too: [Object code](#object-code); the kernels have one operation per statement). These tests can tell: a copy of `mul_2_2` with the textbook product `p = a * b` in place
of the generated `fma(a, b, 0)`, compiled by Apple clang 21 at `-O2`, passes with
`-ffp-contract=off` and `on` and fails 14 148 of 20 000 binary64 cases with `=fast` (1 429 of the
first 2 000). At `-O3`, which is what `Release` gives GCC and Clang, the same compiler leaves
the copy as it is under every setting, and it passes. So with GCC and Clang the runners of a
contraction setting are built at `-O2` whatever the build's level, and the runner with the
build's flags keeps the build's level: both levels are tested.

## Object code

The tests above judge what the compiled kernels compute. This one reads what the compiler
emitted: rules R1 and R2 ([Architecture](architecture.md#the-kernel-ir)) write every product of a
kernel as an FMA, so that a compiler that contracts finds nothing to contract, and the check
verifies that in the object code of every kernel, on the flag matrix of each compiler of the CI.
It is criterion 4 of [When an operation is done](architecture.md#when-an-operation-is-done).

`tests/objcode/objcode.py` compiles `tests/objcode/unit.cpp`, which has one function per kernel and
limb type, externally visible and never inlined, that loads the operands, calls the kernel and
stores its results: scalar (`kairn/gen/scalar.hpp`) and packed (`avx2.hpp` on x86-64, `neon.hpp`
on AArch64). It disassembles the object file and counts, in each of these functions and in every
function of the object that it calls or jumps to, once per call site, two kinds of instructions:
fused multiply-adds (x86 `vfmadd`, `vfmsub`, `vfnmadd`, `vfnmsub` in all their forms; AArch64
`fmadd`, `fmsub`, `fnmadd`, `fnmsub`, `fmla`, `fmls`) and plain floating-point multiplications
(`mulsd`, `mulss`, `mulpd`, `mulps` and their `v` forms; `fmul`, `fnmul`, `fmulx`). A part of a
function that GCC moves to a section of its own (`F.cold`) is counted with the function. It
compares the two numbers with `gen/objcode.json`, which the generator writes from the IR the code
and the proofs are printed from (`gen/README.md`, "The counts of the object-code check"), for the
form the unit was compiled in: scalar with the fix-up inline, scalar with the fix-up a function of
its own, or packed.

### The rule

**The compiler's own vectorization is off** in every compilation of the check: with Clang and
Apple clang `-fno-vectorize -fno-slp-vectorize`, with clang-cl the same through `/clang:`, with GCC
`-fno-tree-vectorize` (which covers loop and SLP vectorization). Automatic vectorization packs
independent operations into one instruction without changing any of them, so a count of
instructions cannot see through it. Clang 18 on x86-64 vectorizes the loop of the map `axpy_2`,
and in its scalar rest packs two of the step's five independent FMAs into one 128-bit
`vfmadd231pd`: nine fused instructions for two copies of a five-FMA step, with exactly the step's
operations. Clang 18 packs two independent scalar FMAs of a straight-line kernel into one
`vfmadd213ps` too, two live lanes in a four-lane register, so the number of lanes an instruction
computes cannot be read off the instruction either. The check exists to catch a compiler fusing
or splitting operations, and a compiler decides that independently of the packing. Whether results
change when the compiler vectorizes is the business of the cross-checks, which run with the
compiler's defaults and compare bits ([Cross-checks](#cross-checks)). The explicit SIMD
forms (`F_packed`, the AVX2 and NEON kernels) are intrinsics, which these options leave as they
are written, and are checked as before. MSVC has no option that turns its vectorizer off: the
check compiles with `/Qvec-report:1`, under which MSVC names every loop it vectorized (`info
C5001: loop vectorized`), and fails on any, naming them. The vectorization control below shows
what the options are for.

For each kernel, form and limb type:

- **Fused multiply-adds**: one per FMA node of the flattened IR (`fma`, `fms`, `fnma`, `prod`),
  with identical nodes of one function (the same operation on the same operands) each compiled or
  merged into one. The generator gives both numbers, `fma` and `fma_distinct`, and they differ in
  five kernels only: the fix-ups of `mul_2_1_full`, `mul_2_2_full` and `mul_pow2_2_full` compute
  the core's leading product again, `t = prod(x0, y0)`, and so does `mul_ext_2_2`, whose product of
  an infinite operand is the leading product of its `mul_2_2`, with `interval_mul_2`, which has four
  `mul_ext_2_2` (32 FMA nodes, 28 distinct). A compiler that eliminates common
  subexpressions computes it once. Every compiler measured does so when it optimizes, in the
  inline form and in packed code, except MSVC under `/fp:strict` for the scalar code; none does
  without optimization; and in the form where the fix-up is a function of its own, which receives
  `x0` and `y0` as parameters, none can.
- **Plain multiplications**: one per product with $+\infty$ of a fix-up (`times_inf`, which R1
  allows: exact, and only compared or selected), in the nine full kernels that have one. In
  addition, in the scalar forms of `two_prod`, the seven products of Dekker's product, in the
  branch `if (__builtin_is_constant_evaluated())` that only constant evaluation takes, where a
  compiler emits that branch: MSVC at `/Od` compiles the test as that of a register which is always
  zero, and the branch after it. No execution reaches it. The kernels `constexpr` by the rule of
  the product ([Architecture](architecture.md#the-kernel-ir)) have the same kind of branch per
  `prod`, `__builtin_is_constant_evaluated() ? a * b : fma_rn(a, b, 0)`, and the same allowance:
  one plain product per `prod`, where a compiler emits the first arm.
- **Folds**: `unit.cpp` has a function per fold, form (`F_seq`, `F_lanes`, `F_packed`) and limb
  type, and `gen/objcode.json` gives, under `"folds"`, the counts of each *part* of that form (the
  step, the combination, the packed step, the finish) with the number of times the printed
  function holds it at least: `F_seq` the step once, `F_lanes` the step twice (lanes and
  remainder) and the combination once, `F_packed` the packed step, the combination and the scalar
  step once each, and every form the finish once. A compiler may unroll a loop, or peel it, and so
  hold a part more often: the rule is that the function's fused multiply-adds, and its plain
  multiplications, are a sum of each part's counts (`fma`, or `fma_distinct` for a copy whose
  identical operations were merged) taken at least that number of times and at most 64 times,
  and nothing else. A part that asks for none may appear any number of times. So `dot_2`, whose
  step has five FMAs, may have 5, 10, 15, ... in `F_seq` and 10, 15, ... in `F_lanes`, never 4
  or 11; a contraction in a loop body adds one that no number of copies makes, unless it is
  repeated in exactly a step's worth of copies, which the check cannot tell from an unrolled
  step. The sums ask for none at all. A map's parts are its step and its check (the kernel that
  tests each written element): `F_seq` the step once and the check twice (the first pass and the
  second), `F_lanes` the step twice and the check three times, `F_packed` the packed step and the
  packed check once and the scalar step once and the check twice. The copies are those of
  unrolling and peeling: with the compiler's vectorization off, every copy is a scalar copy, and in
  `F_packed` the packed step is the one the intrinsics write.
- **Nothing else**: every kernel has its function and every function of the unit its counts; it
  calls nothing outside the object but the stack protector's routines and the stack probes of
  Windows and of Darwin, which do no arithmetic (Ubuntu's GCC protects functions by default; Apple
  clang at `-O0` probes the stack of a frame above a page, through a register loaded from the
  GOT, which `disasm.py` follows to its symbol: the packed scalings of a ball by a power of two);
  there is no other indirect call; and no kernel has a declared contractable multiply-add
  (`muladd`), for which the check has no rule yet.

So the static count does not always equal the number of FMA nodes, and a kernel does not always
have no plain multiplication: what holds is the rule above, which allows these two differences
and no other. On every compiler and flag set measured, no other kernel has a plain
multiplication, in scalar or in packed code: the scalings by a power of two (`mul_pow2_2`) and the
products by the constants of the radii are FMAs, and the constructors multiply nothing. (These
measurements are of Milestone 1. The plain products that the rule of the product adds are in arms
that run time never takes; the check allows them where a compiler emits them, as above.)

A failure says what was found, function by function. One fused instruction more, with one
multiplication fewer or none, is a contraction; a multiplication more and an FMA fewer is an FMA
computed as a product and a sum, or an opaque product folded back into a plain one (as
`-fno-signed-zeros` with contraction does with Apple clang); a call outside the object, to a
library's `fma` for example, is arithmetic that the check cannot see.

What it does not check: the order of the operations and what they compute (the cross-checks and
the generator's comparison with the interpreter do); the code a compiler makes when it vectorizes
on its own (the cross-checks run it, with the compiler's defaults, and compare bits); instructions
of other kinds; a kernel inlined
into a caller, which a compiler may optimize differently (the unit's functions are not inlined; R1
and R2 are what make that harmless for contraction,
[Environment](design/phase0/environment.md#the-self-test)); the public headers' operators, which
call these kernels; nvcc, Metal and AVX-512, which have no backend yet.

### The operations of Ball outlined and external

With `KAIRN_ENCLOSURE_CODE` set to `KAIRN_ENCLOSURE_CODE_OUTLINED` or
`KAIRN_ENCLOSURE_CODE_EXTERNAL` ([Getting started](../getting-started/index.md#compile-time-and-the-operations-of-ball)),
the operations of `Ball` that round, and the arithmetic of `Interval`, are functions of their own,
into which the generated kernel is inlined (but `interval_mul_2`, an ordinary inline function,
which the compiler may call from them). `tests/objcode/enclosure_unit.cpp` has one function per
operation (of a ball `+`, `-`, `*`, `half` and the scaling, of an interval `+`, `-`, `*`, one and two
limbs) and limb type, 32 in all, externally visible and never inlined, that applies the public
operator, and the check compiles it three times in each configuration that compiles both
forms of the fix-ups (every configuration of the full tier, the one with contraction forced on at
`-O2` or `/O2` of the quick tier), with `KAIRN_CHECKS` 0, as a release build has it:

- **outlined**: each function has no fused multiply-add and no multiplication of its own, and the
  count with the functions it calls is that of its full Ball kernel by the rule above: the call is
  a call, and the function it calls has exactly the fused operations of the kernel;
- **external**: each has none, calls the operation outside the object once (a symbol of
  `kairn::detail::external`), and nothing of the object that it executes computes;
- **external, with its definitions**: the same unit with `kairn/definitions.hpp`, whose explicit
  instantiations are then in the object, and each function as in the outlined form.

`objcode.controls` compiles the same unit with the operations inline, the default, judged as the
outlined form: the check must fail on every function, the operation not being a call, but two
kinds, whose expectation the data give. The sum and the difference of intervals of one limb have
no fused multiply-add and no product (`gen/objcode.json`), so nothing tells their inline code from
a call, and they are not judged. The product of intervals of two limbs has a kernel that is an
ordinary inline function (`ordinary_inline` in its description), so in the inline setting too the
compiler may call it rather than inline it: what it did is reported, not judged. On the Mac
on 2026-11-20 the 72 checks of the full tier (24 configurations, three forms) passed with Apple clang
21 and GCC 16, and the control failed on 16 of 16 functions with each; with `half` of a ball of one
and of two limbs in the unit, 20 functions, the same day, the same 72 passed and the control failed
on 20 of 20, with each compiler. With the arithmetic of intervals in the unit, 32 functions, the
72 checks of the full tier passed with Apple clang 21 and GCC 16 on the Mac, and the control failed
on 26 of the 26 functions it judges with each, as with GCC 13 and Clang 18 on x86-64; all four, at
`-O2`, called `interval_mul_2` from the inline product, for `double` and `float`, rather than
inline it.

### The flag matrix

| Compiler | Full tier: every combination of | Quick tier |
|---|---|---|
| GCC, Clang, Apple clang | `-O0`, `-O1`, `-O2`, `-O3`; `-ffp-contract=off`, `on`, `fast`; without and with `-frounding-math`: 24 | `-O0 -ffp-contract=fast`; `-O2` with each contraction setting; `-O3 -ffp-contract=fast -frounding-math` |
| MSVC | `/Od`, `/O1`, `/O2`; `/fp:precise`, `/fp:contract`, `/fp:strict`: 9 | `/Od /fp:precise`; `/O2` with each setting |
| clang-cl | `/Od`, `/O1`, `/O2`; `/fp:strict`, `/fp:precise`, `/fp:contract`, `/clang:-ffp-contract=fast`; without and with `/clang:-frounding-math`: 24 | `/Od /fp:precise`; `/O2` with `/fp:strict`, `/fp:precise` and `/clang:-ffp-contract=fast`; `/O2 /fp:contract /clang:-frounding-math` |

Each configuration is compiled once with the compiler's own form of the scalar fix-ups and with
the packed kernels, and once more with the other form, scalar only; in the quick tier only the
configuration with contraction forced on at `/O2` or `-O2` has the second compilation. The options
come after those of `CMAKE_CXX_FLAGS` and `kairn::fma`'s, as in `api.k1.zero_cost`, and the packed
kernels get the backend's option (`-mavx2 -mfma`, `/arch:AVX2`). Each object file and its
disassembly stay in the test's work directory (`tests/objcode/` of the build tree).

Every compilation of the check turns the compiler's automatic vectorization off
([The rule](#the-rule)), with the options of `NO_VECTORIZE` in `objcode.py`, after every other
option so that no flag of the build turns it back on: Clang and Apple clang `-fno-vectorize
-fno-slp-vectorize`, clang-cl the same through `/clang:`, GCC `-fno-tree-vectorize`, MSVC
`/Qvec-report:1`, which turns nothing off but makes MSVC name every loop it vectorized, and the
check fails on any. Automatic vectorization packs independent operations into one instruction
without changing any of them: besides the loop of `axpy_2`, Clang 18 at `-O2` on x86-64 computes
two of the four directed products of `interval_mul_1`, and the two directed sums of
`interval_add_2`, in one `vfmadd213pd` or `vfmadd213ps` of the scalar code. The number of
operations of a packed instruction cannot be read off it (two live lanes in a four-lane `ps`
register), so such an instruction cannot be counted. The explicit SIMD forms, written with
intrinsics, are checked as before: the options do not touch them. No packing by MSVC has been
seen.

The disassembler is found as follows, and the check fails without one and says where it looked:

| Compiler | Disassembler | Object files |
|---|---|---|
| GCC and Clang on Linux | `objdump` of GNU binutils, `-d -r` | ELF |
| Apple clang | `objdump` of the Xcode tools, which is LLVM's, `-d -r --show-all-symbols` | Mach-O |
| MSVC | `dumpbin /disasm` next to `cl.exe`, else on the PATH | COFF |
| clang-cl | `llvm-objdump` next to `clang-cl.exe`, else on the PATH | COFF |

The hosted runners have each one: binutils on the Ubuntu images, the Xcode tools on macOS, the
Visual Studio tools and LLVM on Windows. The checker's own tests (`objcode.test`) read stored
excerpts of each format (`tests/objcode/samples/`: GNU objdump for x86-64 and AArch64, LLVM objdump
for Mach-O and for COFF, dumpbin), so the reading of every format is tested on every platform.

### The controls

`objcode.controls` shows the check catching what it is for. `tests/objcode/fixture.cpp` computes
the textbook `a * b + c` in functions of its own: as two statements (`p = a * b; s = p + c`) and as
one expression, for `double` and `float`, and as two statements with the packed backend's
intrinsics. The check judges each against its source, one product and one sum, so it fails exactly
where the compiler fused it; the fixture's program, run on operands whose product is not a number
of the format, says independently where the compiler fused it. The test requires the two to agree
in every configuration of the tier, and at least one configuration to fuse. It also judges the
unit against counts changed on purpose (one FMA more for `mul_2_2`, one multiplication fewer for
`add_2_2_full`) and requires exactly those two kernels to fail. These controls run with automatic
vectorization off, as the check does, and fail as they did without the options. Two more record
why the options are there, each compiling the unit at `-O2 -ffp-contract=off` with the vectorizer
on, the compiler's default (the vectorization control and the packing control, below). The packing
control judges the scalar functions of the kernels: with Clang on x86-64 the check must fail there,
on `interval_mul_1` among others, and only for the packing: each failing scalar function has fewer
fused instructions than the IR has FMAs, at least one of them on a vector register, and the right
number of multiplications. This is an expected failure, so a compiler that stops packing shows.
With the other compilers what happens is reported and not judged: GCC 16 on the Mac packs nothing
there, and Apple clang 21 packs two FMAs of `interval_add_2` and of `interval_sub_2` into one
`fmla` (measured on 2026-11-20, on the tip of the intervals' line as on the joined tree).

The fixture has a loop too, the step of a map: `t = fma_rn(x[i], a, y[i]); z[i] = t * b + c`, its
first product written as the generator writes every product and its second as the textbook
product and sum, compiled like the unit (vectorization off), with contraction allowed where the
configuration allows it. The check judges it by the rule of the loops of folds, its step one FMA
and one product per element, so a contraction shows as an FMA more and a multiplication fewer in
every copy, which no number of copies of the step makes; its program, on 67 elements, says where
the compiler fused it (all of them, none, or some). The test requires the two to agree, and at
least one configuration of the tier to fuse the loop.

The vectorization control compiles the unit once more, in the first optimized configuration of
the quick tier, *with* the compiler's own vectorization, and judges every function of it by the
same rule. It records what the check then finds, per compiler and version measured: with Clang 18
on x86-64, the packing alone fails `F_seq` and `F_packed` of `axpy_2` and `axpy_2_entry` for
`double`, and the scalar functions of `acc_mul_1`, `ball_from_interval_2`, `interval_add_2`,
`interval_mul_1` and `interval_sub_2` (those the packing control finds), and of the kernels of
stage B2 of the intervals that make the bounds of a ball of two limbs by the directed sums
(`ball_to_interval_2`, `ball_hull_2`, `ball_intersection_2`), the midpoint and radius of two limbs
(`interval_mid_rad_2`, `interval_to_ball_2`) and the split of a ball (`ball_split_1`,
`ball_split_2`), for `double` and `float`; with Apple clang 21 on AArch64, the scalar functions of
`interval_add_2`, `interval_sub_2`, `ball_to_interval_2`, `ball_hull_2`, `ball_intersection_2`,
`interval_mid_rad_2` and `interval_to_ball_2` for `double` and `float`, in the form of the fix-ups
that is a call; with GCC 13 on x86-64 and GCC 16 on AArch64, nothing. Their vectorized loops hold
whole copies of the step. Measured on 2026-11-20 with each line of work and again on the tree that
joins them, where both Clangs pack exactly these and nothing else.
With one of these versions, a compiler that stops packing, or one that starts, fails the control,
so that we learn it. With any other version, and with a compiler never measured, the control
reports what the check finds and does not judge it: what a vectorizer packs changes from one
version to the next, and the hosted runners of CI showed it the first time this control ran there
(their Apple clang packs `interval_mul_1` and not the two above; Clang on AArch64 packs
`interval_add_2`, `interval_mul_1` and `interval_sub_2`; clang-cl, in its first optimized
configuration, which is `/fp:strict`, packs nothing, against what had been assumed of it by
analogy). The check itself does not depend on any of this: it compiles with the vectorization off.

Where each compiler fused the textbook product in the configurations of the full tier, measured on
2026-11-19; it fused nowhere else, and the check failed on exactly these:

| Compiler | Where it fused | Configurations |
|---|---|---|
| GCC 13, x86-64 and AArch64 | both forms with `-ffp-contract=fast` at `-O2` and `-O3`, also with `-frounding-math` (GCC 13 takes `on` as `off`) | 4 of 24 |
| GCC 16, AArch64 (the Mac) | the one expression with `-ffp-contract=on` at every level, `-O0` included; both forms with `fast` at `-O2` and `-O3` | 12 of 24 |
| Clang 18, x86-64 | the one expression with `on` at every level, `-O0` included; both forms with `fast` from `-O1`, but not with `-frounding-math` | 11 of 24 |
| Clang 18, AArch64; Apple clang 21 | the one expression with `on` at every level; both forms with `fast` from `-O1`, with `-frounding-math` too | 14 of 24 |
| MSVC 19.52, x64 | both forms with `/fp:contract` at `/O1` and `/O2` | 2 of 9 |

GCC 13 and Clang 18 on AArch64 were run as the cross compilers of Ubuntu 24.04 (the versions of the
hosted arm64 runner), with binutils' AArch64 `objdump` and the fixture's program under QEMU's user
mode (`--emulator`). clang-cl has not been run: the Windows machine has none.

### The kernels, as measured

On 2026-11-19 the full tier's check passed with GCC 13 and Clang 18 on x86-64 and on AArch64 (as
the cross compilers above), with Apple clang 21 and GCC 16 on the Mac, and with MSVC 19.52 on x64: every configuration of the
matrix, both forms of the fix-ups, 252 functions per compilation with the packed kernels and 126
without. The fused instructions were every FMA node without optimization, and with optimization
the identical ones merged, but for MSVC under `/fp:strict`, which merges them in packed code only;
the branch of constant evaluation appeared with MSVC at `/Od` only. At `-O2` and `-O3` GCC 13 on
x86-64 put the call of the fix-up function in a part of its own (`F.cold`), and without
optimization every compiler called helpers (`std::bit_cast`, `std::numeric_limits<T>::infinity()`, and with MSVC
`fma_rn` and the kernel itself), all counted through the calls. No kernel called a library's
`fma`: with `-mfma`, `/arch:AVX2` and on AArch64 the FMA is an instruction at every level, `-O0`
and `/Od` included.

On 2026-11-20 the check found two things in the code of the folds' stage, on x86-64. GCC 13 at
`-O2` and `-O3` with `-ffp-contract=fast` compiled the first listings of `bound_sum_2` and
`bound_dot_2` with one FMA more than they ask for: it wrote `d = a + a` as `a * 2` and contracted
that product into `w = d + k`. The value was the same here (`2a` is exact), but not in general at
an overflow, and rule R1 now refuses an addition of a value to itself
([Architecture](architecture.md#the-kernel-ir)); the bound kernels double with the opaque
product. And Clang 18 at `-O0` called `memset` to zero the 32-byte array into which `F_packed`
stores the lane states, a call outside the object that the check cannot count; the array is now
left uninitialized, since the store writes every lane before any is read.

The first code of the ball vectors ([Architecture](architecture.md#ball-vectors)) failed the check
in three ways, at `-O2`, none of them a change of value. Its second pass, which writes the zeros of
the whole space, was a call of `bzero` (Apple clang) or `memset`, outside the object. And the radius
at the end of the loop was copied into the paths that leave it with part of a copy changed: Apple
clang folded the product by the largest magnitude, which is the $+0$ of the zero state on the path
where the loop runs no element, into an addition (three fused instructions for two copies of a
radius of two, in `bv_add_2` and `bv_sub_2`), and GCC 13 hoisted the product by $\lvert a\rvert$ of
`bv_scale_radius_2` out of the loop and duplicated the rest (eight for a step of three and a radius
of three). No number of whole copies of the parts makes those counts. The radius and the finish
are now a function of their own, never inlined, which the check follows once per call; the largest
magnitude enters it through a volatile copy, and the zeros are volatile stores. With that the check
and its controls pass with Apple clang 21 and GCC 16 on the Mac and with GCC 13 and Clang 18 on
x86-64, and no compiler packs a loop of a ball vector in the vectorization control.

The check takes seconds, on the machines of [Time](#time), with `--parallel 4`:

| Where | `objcode.check`, `objcode.controls` | The quick tier, in all | `full.objcode.check`, `full.objcode.controls` |
|---|---|---|---|
| Mac, Apple clang 21 | 1.2 s, 1.2 s | 50 s | 4.2 s, 4.4 s |
| Linux, 16 threads, GCC 13 | 4.3 s, 2.8 s | 78 s | 14.2 s, 4.9 s |
| Linux, 16 threads, Clang 18 | 4.2 s, 2.6 s | 76 s | 14.4 s, 4.9 s |
| Linux, 4 threads, GCC 13 | 4.3 s, 2.8 s | | 14.1 s, 5.0 s |
| Windows, 8 logical processors, MSVC | 2.0 s, 1.8 s | 88 s | 4.0 s, 1.7 s |

In these first runs ctest, which had no record of their times yet, started the two tests of the
quick tier near its end, so that they added up to their own length to it: the quick tier took 50,
78 and 76 seconds on the Mac and the Linux machine, against 44 to 47 and 70 to 75 before the check,
and 88 on the Windows machine, against 85 to 113. On a hosted runner, four times as slow by the
cautious rule of [Time](#time), the two would take about 17 and 11 seconds, and those of the full
tier about a minute and 20 seconds.

### By hand

```sh
python3 tests/objcode/objcode.py --cxx c++ --workdir objcode            # the quick tier's configurations
python3 tests/objcode/objcode.py --cxx g++ --flags=-mfma --packed-flags="-mavx2 -mfma" \
    --tier full --jobs 8 --workdir objcode                              # the whole matrix
python3 tests/objcode/objcode.py --cxx cl --flags=/arch:AVX2 --controls --workdir objcode
```

`--disassembler` names another disassembler, and `--emulator` the command that runs the controls'
program for a cross compiler.

## Flag sets

A program that includes Kairn compiles the public interface and the kernels with its own flags.
The runners above are built with the build's flags (`Release`: `-O3`, or `/O2`) and with each
contraction setting at `-O2`. The public interface and the kernels are also built with each flag
set below, the sets of a client (`tests/api/flags/`): each target gets exactly the options of its
set after `CMAKE_CXX_FLAGS`, since the flags of the build's configuration (`-O3 -DNDEBUG`,
`/O2 /Ob2 /DNDEBUG`) are emptied there; every set but the debug build defines `NDEBUG`, as a
release build does. A full cross product is not needed: the sets give every value of every flag,
and the combinations that Phase 0 found dangerous ([Environment](design/phase0/environment.md)):
forced contraction at each optimization level, since whether a compiler fuses depends on the
level (Apple clang 21 fuses the textbook product at `-O2` and not at `-O3`); `-frounding-math`,
which changes what a compiler may fold, with forced contraction and optimization; and, with MSVC,
`/Od` and `/fp:strict`, where `std::fma` is a library call and the kernels' FMA intrinsic must
still be one fused operation.

| Compiler | Set | Options | Why |
|---|---|---|---|
| every one | `debug` | CMake's `Debug` configuration: `-g` (GCC, Clang), `/Zi /Ob0 /Od /RTC1` and the debug C runtime (MSVC, clang-cl); no `NDEBUG`, so `KAIRN_CHECKS` is 1 | a client's debug build: no optimization, the compiler's default contraction (`fast` for GCC in GNU mode, `on` for Clang, `/fp:precise` for MSVC), and the [checks](#the-checks-of-a-debug-build) |
| GCC, Clang, Apple clang | `O0-contract-fast-rounding-math` | `-O0 -ffp-contract=fast -frounding-math` | no optimization, with the two other flags at their riskier values |
| | `O1-contract-off` | `-O1 -ffp-contract=off` | `-O1`, which no other test built, without contraction |
| | `O1-contract-fast` | `-O1 -ffp-contract=fast` | forced contraction at `-O1`; also the kernels |
| | `O2-contract-on-rounding-math` | `-O2 -ffp-contract=on -frounding-math` | contraction within expressions (Clang's default) with `-frounding-math` |
| | `O2-contract-fast-rounding-math` | `-O2 -ffp-contract=fast -frounding-math` | forced contraction and `-frounding-math` at the level where Apple clang fuses (the flag set of the generator's tests of constant evaluation) |
| | `O3-contract-off-rounding-math` | `-O3 -ffp-contract=off -frounding-math` | the level of `Release` without contraction, with `-frounding-math` |
| | `O3-contract-fast` | `-O3 -ffp-contract=fast` | forced contraction at the level of `Release` (Clang's runner with the build's flags contracts only within expressions) |
| MSVC | `Od-fp-contract` | `/Od /fp:contract` | contraction allowed, without optimization |
| | `Od-fp-strict` | `/Od /fp:strict` | the two settings where `std::fma` is a library call; `/fp:strict` is MSVC's `-frounding-math` |
| | `O1-fp-precise`, `O1-fp-contract`, `O1-fp-strict` | `/O1` and each `/fp:` setting | `/O1`, which no other test built; `O1-fp-contract` also the kernels |
| | `O2-fp-strict` | `/O2 /fp:strict` | the level of `Release` with `/fp:strict` |
| clang-cl | `Od-contract-fast` | `/Od /clang:-ffp-contract=fast` | forced contraction without optimization |
| | `Od-fp-strict` | `/Od /fp:strict` | `/fp:strict` is `-ffp-model=strict`: no contraction, and `-frounding-math` |
| | `O1-fp-precise` | `/O1 /fp:precise` | `/O1` (Clang's `-Os`), contraction within expressions |
| | `O1-contract-fast-rounding-math` | `/O1 /clang:-ffp-contract=fast /clang:-frounding-math` | forced contraction with `-frounding-math`; also the kernels |
| | `O2-fp-contract`, `O2-fp-strict` | `/O2` with `/fp:contract`, with `/fp:strict` | the level of `Release` with contraction within expressions, and with `/fp:strict` |
| GCC, Clang, Apple clang | `O3-outlined`, `O3-external` | `-O3` and `KAIRN_ENCLOSURE_CODE` set to `KAIRN_ENCLOSURE_CODE_OUTLINED`, to `KAIRN_ENCLOSURE_CODE_EXTERNAL` | the operations of `Ball` as functions of their own, and only declared, defined in one more file of each program, `tests/api/definitions.cpp` ([Getting started](../getting-started/index.md#compile-time-and-the-operations-of-ball)), at the level of `Release` |
| MSVC, clang-cl | `O2-outlined`, `O2-external` | `/O2` and the same | the same |

With the runners of the build's flags and of the contraction settings at `-O2` or `/O2`, every
optimization level meets every `/fp:` setting with MSVC, and forced contraction with every
compiler. For each set, `tests/api/flags/` builds the public interface's runner and
`tests/api/constexpr.cpp`, and for the debug build and the set marked "also the kernels" the
kernels' runners, scalar and packed; and `tests/api/rational.cpp` and `tests/api/rational_runner.cpp`
for `kairn::rational`. They are tested as follows:

| What | Quick tier | Full tier |
|---|---|---|
| The public interface against the oracle | | the debug build's runner, on the first form of each kernel, on 10 000 cases (`full.api.oracle.K.F`); every form, through the runner of every set, on the quick tier's 2 000 cases (`full.api.flags.oracle.K.F`) |
| `kairn::self_test()` and `environment_ok()`, compiled with the set's flags | `api.flags.debug.self_test` | `full.api.flags.S.self_test` |
| `constexpr.cpp`: its constant expressions, and the same at run time | `api.flags.debug.constexpr` | `full.api.flags.S.constexpr` |
| `kairn::rational`: `rational.cpp`, and the runner of `rational_K` | `api.flags.debug.rational` | `full.api.flags.S.rational`; every set's runner in `full.api.rational.K.F` |
| The kernels' runners, in the cross-checks | | the debug build and the `-O1` or `/O1` set, in `full.crosscheck.compiled.K.F` |
| The checks of `KAIRN_CHECKS` | `api.checks.*` ([below](#the-checks-of-a-debug-build)) | |

The quick tier has so little of it because a debug build's runners take two to three times as long
as optimized ones, most of it in the text of the line protocol: on the Mac, the debug build's
runner on every form added 21 seconds of test time to `api.oracle`, and its kernels' runners 35 to
the cross-checks, against about 5 for the first forms ([Time](#time)). The first forms were in the
quick tier's `api.oracle.K.F` too, until the hosted Windows runners showed that the quick tier
could not keep to two minutes there with them ([Time](#time)). The generator's own suite
builds the kernels at `-O0` too, with GCC and Clang only ([below](#the-generators-tier)): these
are the tests that build them at `/Od` with MSVC and clang-cl, and at `-O1` with any compiler.

## The checks of a debug build

`KAIRN_CHECKS` is 1 when `NDEBUG` is not defined (or when a program defines it to 1); what it then
does, as the headers are written (`config.hpp` says the same):

- Before every operation of `Expansion` and `Ball` that rounds (the arithmetic, `ldexp` and
  `half`, `kairn::finite::`, `is_normalized` of two limbs), and in the constructors that check
  what they are given and round (`from_limbs`, and the constructors of `Ball<T, 2>` from a
  center), first `kairn::environment_ok()`; if it fails, `KAIRN_ENVIRONMENT_FAILURE` with the
  reason, by default a message and `std::abort()`.
- Before a function that does not round, whose result is the same under every rounding mode
  (negation and `abs`, the comparisons, the conversions to `T` and the narrowing to one limb, the
  negation of a `Ball`, and the constructors of a `Ball` from a `T` or a number of one limb, whose
  guard `a + 0` has the value `a` under every mode: the list of [Milestone 2
  statements](design/milestone2.md#functions-that-do-not-round), which `config.hpp` and Getting
  started repeat), the same without the rounding mode, so that a program may call it under a
  directed one: flush to zero is still checked, since a comparison reads a subnormal operand as
  zero there. Its operands are checked as below, but those checks that round (the test of a
  canonical pair) only when the rounding mode is to nearest. The functions that had no check at all
  (`sign`, `isfinite`, the accessors of a `Ball`, the constructors of two limbs from a `T`, ...)
  still have none.
- Then the operands: an operation of two limbs requires canonical operands, a function of
  `kairn::finite::` normalized ones or a leading limb that is not finite (what a core returns), a
  `Ball` operation canonical balls, `from_limbs` a canonical pair, and a constructor of `Ball` a
  radius that is not negative and, for two limbs, a canonical center; if one is not, a message
  and `std::abort()`.
- If the environment is not the default one and a `KAIRN_ENVIRONMENT_FAILURE` of the program's
  own returns, the operation goes on without checking its operands: those checks compute in that
  environment, where the test of a canonical pair, $x_0 + x_1 = x_0$, can be false (for
  $(1.5, 2^{-60})$ under rounding upward). So a program stopped in a wrong environment is stopped
  with the environment's message, and a handler that returns lets every operation go on, with no
  guarantee for its result.
- In constant evaluation the environment is not checked, and an operand that fails a check makes
  the constant expression invalid.

`tests/api/checks.cpp` runs them, on the cases of `tests/api/checks_cases.hpp`, built as the
[debug build](#flag-sets) (`api.checks.debug.*`) and with the build's own flags and `KAIRN_CHECKS`
defined to 1 (`api.checks.release.*`, where an optimizer could move or drop a check), and
`tests/api/checks.cmake` judges each case from the program's exit status and output:

The cases are a table of every public function of the headers, one entry per form that reaches a
function of its own in `kairn::detail` (131 today), each marked with what the checks do before it:
`rounds` (93: every operation that rounds, the compound assignments, the functions of
`kairn::finite::`, `is_normalized` of two limbs, the constructors whose checks round, and the
functions of the enclosure interface that compute bounds or centers: the midpoint, the radius
and the split of an interval, the conversions between an interval and a ball, the ball from an
interval of two `T`, the bounds of a ball as numbers of `T` and its narrowing),
`exact` (29: the functions that do not round and are checked without the rounding mode, the
negation, the hull and the intersection of intervals, the bounds of an interval of two limbs as
numbers of `T` and the constructors of intervals among them) or
`unchecked` (9: the functions with no check at all, the accessors of an interval and its states
among them). A function that rounds is run on the operands
below; one that does not round, on a corpus, for `double` and for `float`: zeros of both signs,
subnormal numbers, the smallest normal number, the largest finite number, the infinities and NaN,
alone and in canonical pairs (a zero of either sign in each limb, a subnormal leading limb and a
subnormal tail, the ties of the test of a canonical pair, tails next to the largest finite
number), balls of one and two limbs with radii from 0 to the largest finite number, the whole
line and the empty set, and the intervals of one and two limbs that the constructor makes of the
pairs of those values and pairs, the empty set and the whole line among them; the comparisons on
every pair of it, the hull and the intersection on every pair of intervals, the constructors of a
ball on every center and every radius that is not negative, those of an interval on every pair of
bounds.

- `default`: in the default environment `environment_ok()` is true, and every function of the
  table runs, as do 23 operands the checks must let through: the canonical infinities and NaN,
  the empty set and the whole line, a NaN and a $-0$ radius, what a finite core returns, given
  back to `kairn::finite::`, the bounds of an interval that are a NaN or reversed (which make the
  whole line and the empty set without a report), and the two states of an interval as operands.
- `rounding`: for each directed rounding mode and each function of the table, a run of its own:
  `environment_ok()` is true, the mode is set and `environment_ok()` is false. A function that
  rounds must stop the program, with an exit status other than 0 (`SIGABRT`; exit status 3 with
  Microsoft's C runtime), after the line in which the program says it calls it, and with Kairn's
  message on the standard error ("the rounding mode is not to nearest"), not one about an operand.
  The two-limb operands, $(1.5, 2^{-60})$ and $(2.25, -2^{-58})$, are canonical pairs whose test
  is false under rounding upward, and under rounding downward and toward zero; those of the
  operations are made before the mode is set, so that each operation is what meets it, and the
  constructors meet it in cases of their own. A function that does not round must not stop it: it
  runs on its corpus to nearest, then under the mode, and must exit 0, with nothing of Kairn's on
  the standard error, and with the same bits in every result (a constructor: the same values,
  zeros compared without their sign, since its guard gives $-0 + 0 = -0$ when rounding downward).
  The sign of a zero is cleared on the bit pattern of a copy read back from memory: written in
  floating point, `x == 0 ? 0 : x` runs under the mode too, and a compiler that assumes rounding
  to nearest may drop it where `x` is a guard's `a + 0`, never $-0$ to nearest; on the hosted
  runner, MSVC 19.51 at `/O2` let the guard's $-0$ through that rule under rounding downward
  (19.52 compiles it as a comparison and a blend). On a difference the program prints both bit
  patterns. So the table cannot rot either way: a function marked as not rounding that checks the
  mode, or rounds, fails, and so does one marked as rounding that does not check it. 393 runs.
- `flush`: the same with FTZ and with DAZ of MXCSR on x86-64, and FZ of FPCR on AArch64, under
  which every function that rounds and every function that does not round but is checked must
  stop the program; the 9 with no check at all are not run. On those targets a program that can
  set no such state fails the test.
- `operands`: 23 operands that are not canonical, each given to an operation, must stop the
  program with their message: pairs that are not canonical given to `from_limbs`, to an operator,
  a comparison, a conversion, a negation, `ldexp` and `kairn::finite::add`, what a finite core
  returns after an overflow given to an operator, negative radii ($-\infty$ among them), a center
  that is not canonical, and a ball that is not canonical, made by the internal constructor that
  takes a kernel's result as it is, the only way to make one, given to a sum and to a negation;
  an interval that is not canonical, made the same way (reversed bounds, a NaN bound, a bound of
  two limbs that is not canonical), given to a sum, a negation and a hull, and a bound of two limbs
  that is not canonical given to the constructor of an interval; and the two operands of the building blocks that a debug build refuses: `fast_two_sum` with
  $\lvert a\rvert < \lvert b\rvert$, and the conversion to two limbs of the result of `two_sum`
  whose error term is a NaN although its sum is finite ($b = \Omega$, $a = -1.5$ ulps of $\Omega$).

`api.checks.handler` (`tests/api/checks_handler.cpp`) defines `KAIRN_ENVIRONMENT_FAILURE` as a
function that records the reason and returns. In the default environment it is not called; under
each state of `rounding` and `flush`, each function of the table that rounds calls it with the
reason and goes on, and so does `x + y` with an `x` that is not canonical, which stops the
program in the default environment; under each rounding mode no function that does not round
calls it, and each gives the same bits as to nearest; under flush to zero each that is checked
calls it. `api.reject.checks.*` are the constant expressions, and
`api.oracle.K.F` judges the debug build's runner: the checks let every canonical case through and
change no result. On the lines of `ball_make_1` and `ball_make_2` whose radius is negative, about
40% of their cases, which the checks stop by design, the debug build's runner computes
`Ball::empty()`, the set the constructor makes of such a radius, and says on how many lines. The
test programs keep Microsoft's C runtime from opening a dialog on `abort()`, and Linux from
writing a core dump, which took 0.3 seconds per case on the Linux machine
(`tests/api/no_crash_reports.hpp`).

## The program's names

A program may have a global variable with the name of a parameter or a local variable of Kairn's
headers: `x`, `a`, `limbs`, `inf`, or any of the few hundred names of the generated kernels. MSVC
reports every such declaration of a header, at `/W4` (C4459, "declaration of 'x' hides global
declaration") and under `/analyze` (C6244), and a program built with `/WX` then fails to build.
Measured with MSVC 19.52, it reports every parameter and local variable of a function that is not
a template; and of a template, once instantiated, every local variable, and the parameters of the
members of a class template (constructors, `from_limbs`), but not those of a function template;
for a template, whether the program declares the global before or after it includes Kairn.
GCC's `-Wshadow` and Clang's `-Wshadow-all`, which `-Wall -Wextra` do not enable, report a
declaration that hides a variable of its own namespace or of an enclosing block, and not one of
the global namespace from inside `namespace kairn`, with one exception: GCC 11 and 13 report the
parameters of a constructor of a class template and of a lambda, once instantiated, as hiding a
global (21 declarations of Kairn's headers: the constructors of `Expansion` and `Ball`, and a
lambda of `traits.hpp`). GCC 16, Clang 18 and Apple clang 21 report none. Renaming cannot help:
any name of Kairn's can be the name of a program's global. Each header of Kairn, generated or
not, therefore turns these warnings off for its own declarations, between
`KAIRN_GEN_PUSH_WARNINGS` and `KAIRN_GEN_POP_WARNINGS`, defined in `gen/prelude.hpp`: a pushed
and popped `#pragma warning(disable : 4459 6244)` with MSVC, and
`#pragma GCC diagnostic ignored "-Wshadow"` with GCC; nothing with Clang, clang-cl included. Each
compiler applies the state of the header to the templates the program instantiates later.

`api.shadow` (`tests/api/shadow.py`) reads the name of every parameter and local variable of the
headers (1440 today, the generated headers included, by a scan of their tokens, which found every name of Clang's AST of the
headers), writes a global variable of each name, and compiles `tests/api/shadow.cpp`, which calls
every public operation once for `float` and for `double`, with the build's flags and the
strictest warnings of the compiler about a declaration that hides another, as errors, the front
end only: `/W4 /WX` with C4456 to C4459 at level 1, and again under `/analyze` (MSVC);
`-Wall -Wextra -Wpedantic -Wshadow -Werror` (GCC); `-Wall -Wextra -Wpedantic -Wshadow-all -Werror`
(Clang; `/W4 /WX -Wshadow-all` with clang-cl). With the globals, the program must compile, with
each form of the fix-ups (`KAIRN_GEN_FIXUP_CALL` 0 and 1), and with the operations of `Ball`
outlined, and external with their definitions (`KAIRN_ENCLOSURE_CODE`, `kairn/definitions.hpp`
included at the end of the file). Without them, and with
`KAIRN_GEN_KEEP_SHADOW_WARNINGS`, which keeps the warnings on in the headers, it must compile too
(with MSVC, under `/analyze` as well), also external with the definitions: Kairn's own declarations hide nothing, so the warnings stay
as strong as they were for Kairn's own code. With both, which is what a program saw before the headers turned them off, MSVC must reject
it, with C4459, and with C6244 under `/analyze`; with GCC and Clang it is only reported, since
whether they reject it depends on their version (GCC 13 rejects it, GCC 16 and Clang accept it).
Kairn's other tests are built as a program is, with the warnings off in the headers, and with
their own `/W4 /WX` or `-Wall -Wextra -Wpedantic -Werror` unchanged.

## Hardware FMA

The kernels assume that an FMA is one rounding done by the hardware, and on x86-64 the headers
refuse to compile without it. The tests' runners link `kairn::fma`, which adds `-mfma` (GCC and
Clang) or `/arch:AVX2` (MSVC and clang-cl) when the build's flags do not already enable FMA; see
[Getting started](../getting-started/index.md#hardware-fma).

## Time

**The quick tier at the end of Milestone 2** (`main` at `7e12621`, 2026-11-21, 984 to 988 tests
by platform). On the hosted runners of the CI the test step of the quick tier,
`ctest --parallel 4`, took 227 s with GCC and 233 s with Clang on Linux x86-64, 174 s and 183 s
on Linux arm64, 205 s on macOS arm64, and 599 s with MSVC and 503 s with clang-cl on Windows (the
times of the CI's logs of that commit; no copy is stored under `results/`). The brief and the
plan ask for under about two minutes per platform: the quick tier is over that on every
platform, from 1.45 to 5 times the budget
([deviation 24](design/phase0/decisions.md#deviations-from-the-brief-flagged)). It had 288 to 293
tests at the Milestone 1 report ([report](results/milestone1.md#tests-and-ci)): the work of
Milestone 2 more than tripled them. No time of the quick tier with `--parallel 4` on a developer
machine with the present number of tests is recorded. The last measured with `--parallel 4`,
below, are those of the oracle of stage B2, 737 to 740 tests: 105.1 s on the Mac with Apple clang,
164.6 s and 182.2 s on 16 threads of the Linux machine with GCC 13 and Clang 18. With 982 to 988
tests, the times below are with `--parallel 8` on the Mac (81.2 s and 84.6 s) and `--parallel 16`
on the Linux machine (67.3 s to 108 s). The paragraphs that follow are the history, in order, each
with its date.

Each time below is the wall time of one ctest run after the build, with `--parallel 4` unless
noted: `ctest --test-dir build --output-on-failure --parallel 4` for the quick tier, and the same
with `build/tests/full` for the full tier, measured when the full tier was introduced. The Mac is
an Apple M3 Max (16 cores) with Apple clang 21, on which other jobs were running (load average 8 to
26); the Linux machine a 2019 x86-64 server (AMD EPYC 7452) with GCC 13 and Clang 18, each run
pinned with `taskset` to 16 of its hardware threads, or to 4 to stand for a hosted runner; the
Windows machine an Intel i5-13500T with MSVC, each run held to 8 of its logical processors, or to
4 (`SetProcessAffinityMask`). The times of the one tier are those of the commits just before.

| Where | Quick tier | Full tier | The one tier before |
|---|---|---|---|
| Mac | 44 to 47 s | 292 s | 213 to 218 s (`--parallel 6`) |
| Linux, 16 threads, GCC 13 | 70 to 75 s | 452 s | 545 s |
| Linux, 16 threads, Clang 18 | 71 to 75 s | 454 s | 545 s |
| Linux, 4 threads, GCC 13 | 67 s | 88 s for the tests that depend on the compiler, 281 s for those in exact arithmetic, 147 s for the generator's | 948 s |
| Linux, 4 threads, Clang 18 | 69 s | 87 s for the tests that depend on the compiler | |
| Windows, 8 logical processors | 85 to 113 s | 456 s | 818 s |
| Windows, 4 logical processors | 138 s | 181 s for the tests that depend on the compiler | |

Without `--parallel`, as the three commands of [Getting started](../getting-started/index.md)
stand, the quick tier took 166 seconds on the Mac and 287 on 16 threads of the Linux machine.

The folds' stage of Milestone 2 added 38 tests to the quick tier: the 22 cross-checks of its
eleven kernels, 0.78 seconds of test time each as every kernel's (17 seconds), and the 16 of its
eight folds, 0.72 seconds each (11.5 seconds: 300 arrays through the scalar runners and 200
through the packed ones, of 36 elements on average). On the Mac under a load of about 25, the
quick tier took 58 seconds with them and 46 without, 228 and 180 seconds of test time.

The interval stage of Milestone 2 added 66 tests to the quick tier, the cross-checks of its 33
kernels in `binary64` and `binary32`, on 2 000 cases each (`KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES`)
where every other kernel has 6 000: a case of an interval kernel costs the oracle about twice what
one of a first-milestone kernel does (two intervals, the exact range of the set and the classes of
each side), so 6 000 would have doubled their share. On 2026-11-20, with the claims of this stage
alone, they took 37.3 of the quick tier's 375.1 seconds of test time on the Mac with GCC 16
(9.9 %, under a load of 60 to 75 from other jobs), and on 16 threads of the Linux machine 57.3 of
451.8 with GCC 13 (12.7 %) and 36.6 of 373.8 with Clang 18 (9.8 %). Run back to back, the quick
tier took 93.5 seconds with them and 82.2 without (452 and 386 tests) with GCC 13 on 16 threads
of the Linux machine, and 91.3 and 84.9 with GCC 16 on the Mac (load 24 to 41). The full tier keeps
20 000 cases per kernel and format and adds the 33 enumerations of toy formats and the 10 sampled
runs: 109 tests, 894.6 of its 3 921.9 seconds of test time on the Linux machine with GCC 13
(22.8 %), 1 468 seconds of wall time in all.

Stage B of Milestone 2 added 84 tests to the quick tier: the 40 cross-checks of its twenty
kernels (the steps of the maps and the kernels of the folds of maxima), 0.9 seconds of test time
each as every kernel's (36 seconds), and the 44 of its eighteen maps, two folds of maxima and two
convolutions, 0.52 seconds each (23 seconds: 100 arrays of up to 24 elements through the scalar
runners and 100 through the packed ones, pairs of polynomials of up to 20 coefficients for a
convolution). On 16 threads of the Linux machine, shared with other runs, with `--parallel 4`, the
quick tier took 97 to 98 seconds with them and 83 without, 351 and 291 seconds of test time; they
alone took 15 seconds.

With both stages merged (and every kernel and fold of `gen/claims.json` judged), measured on
2026-11-20 back to back on 16 threads of the Linux machine with GCC 13, `--parallel 4`, load 5 to
8: `main` (0622f99) ran 423 tests in 68 seconds (258 and 259 seconds of test time), the merged
tree 573 tests in 115 to 118 seconds (426 to 439). Of the difference in test time, 37 seconds are
the interval kernels' 66 tests, 63 stage B's 84, and about 69 the 422 tests both have: their
cross-checks of the compiled runners 24 seconds (the merged oracle imports more and reads a larger
claims file, 0.03 to 0.04 seconds more per check of 6 000 lines on the Mac), the public
interface's 11, and the object code's tests and `api.reject` 29, which do not run the oracle
(they compile the headers, which the joined branch extended). The guards' tests (`full.tools.crosscheck.guards`, 74 tests)
took 300 seconds there with each compiler and 170 to 201 on the Mac, under their timeout of 900
but close to a third of it.

On 16 threads of the Linux machine, the quick tier's 278 seconds of test time were then: the
compiled runners' cross-checks 105 (126 tests), the oracle's own tests 54, the public interface
against the oracle 51 (96 tests), the guards' tests 32, the generator's own tests 17, the
reference script's tests 9, and 11 for the 50 others. The oracle's tests were the longest single
test, and set a floor of about a minute to the wall time there, until the tools' own tests left
the quick tier ([below](#the-tools-tests-leave-the-quick-tier)). In the full tier, the pools of four workers
of the generator's and the oracle's longest tests are counted by ctest (`PROCESSORS`), so with
`--parallel 4` each runs alone; a larger `--parallel` shortens the full tier on a machine with
more cores.

**The hosted runners** of the CI have four cores, three on macOS. Estimated as four times the time
on 4 threads of the Linux machine, a cautious rule: the quick tier about 4.5 minutes on Linux,
the full tier's job of the compiled runners about 6 minutes after its build, its two jobs in
exact arithmetic about 11 minutes for the interpreter's enumerations (161 seconds of the 281
above, after the oracle's 120) and 8 for the oracle's; on Windows, four times the time on 4
logical processors, 9 minutes for the quick tier and 12 for the compiled runners. (Those were the
times with the kernels of Milestone 1. With those of Milestone 2 the interpreter's enumerations
are 340 tests and no longer fit one job: on a hosted runner they were cancelled at 30 minutes
with 258 done, and are three jobs of a third each since. The compiled runners' job, 939 tests,
takes 22 to 38 minutes on the hosted Linux and macOS runners and did not finish in 60 on the
Windows ones, where a cross-check takes 18 seconds against 7 on Linux and the oracle's self-test
17 minutes against 9: each Windows compiler runs it as three jobs of a third each, every one
with its own build.) The one tier
suggests the rule is cautious indeed: it took 1 040 seconds with GCC on a hosted Linux runner
against 948 on 4 threads of the Linux machine, a ratio of 1.1, which would make the quick tier
about 75 seconds there and the compiled runners' job about 100; and 1 011 seconds on a hosted
macOS runner against 213 to 218 on the Mac, a ratio of 4.6, which would make the quick tier about
3.5 minutes there.

**The flag sets and the checks** ([Flag sets](#flag-sets), [The checks of a debug
build](#the-checks-of-a-debug-build)) were measured on 2026-11-19 against the commit before them,
each pair run back to back on the same machine, as above; the Mac was loaded by other jobs (load
average 5 to 9), and the Linux machine by other users:

| Where | Quick tier, before and after | Full tier, the tests that depend on the compiler, before and after | Whole full tier, after | Build, before and after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 49.9 and 52.5 s; 46.6 and 48.3 s | 95.6 and 154.1 s | 346 s | 2.3 and 4.8 s |
| Mac, GCC 16 | 42.9 and 44.9 s; 40.2 and 42.1 s | 56.4 and 88.1 s | 273 s | 3.8 and 9.1 s |
| Linux, 16 threads, GCC 13 | 77.3 and 84.4 s | 111.6 and 148.8 s | 520 s | 4.3 and 8.6 s |
| Linux, 16 threads, Clang 18 | 81.6 and 80.3 s | 110.9 and 146.0 s | 517 s | 3.2 and 6.7 s |
| Linux, 4 threads, GCC 13 | | 110.3 and 141.1 s | | |
| Linux, 4 threads, Clang 18 | | 105.4 and 136.3 s | | |
| Windows, 8 logical processors, MSVC | 86.1, 89.2, 95.1 and 100.3, 102.0, 102.9 s | 125.6 and 227.1 s | 604 s | 6.7 and 13.8 s |

In test time, the quick tier gained 7 to 11 seconds on the Mac, 13 on the Linux machine (once 28,
when one test of a few milliseconds took 10 seconds there) and 28 to 56 on the Windows machine, of
which the debug build's runner in `api.oracle` is 4 to 6 seconds on the Mac and the Linux machine
and 11 to 14 on the Windows machine, the checks 3 to 7, and the rest the other tests slowed by these
beside them. The full tier's tests that depend on the compiler gained 127 to 236 seconds on the
Mac, 143 to 149 on the Linux machine and 407 on the Windows machine: 85 to 101 seconds for
`full.api.flags.oracle` (175 on Windows), 34 to 120 for the kernels' runners in the cross-checks
(192 on Windows, where the debug build's packed runner, at `/Od` with `/RTC1` and the debug C
runtime, takes 0.2 seconds per 6 000 lines, five times the optimized one), and the rest the tests
beside them. On the hosted runners the quick tier's ctest step took about as long as on the Linux
machine on Linux x86-64 and 1.4 to 2.2 times as long as on the Windows machine on Windows
([Costs, Milestone 1](results/costs-milestone1.md)): by those ratios, these add about 40 seconds
to the full tier's job on Linux and 2.5 to 4 minutes on Windows, and 15 to 30 seconds to the quick
tier on Windows, whose ctest step is already over two minutes there.

**The program's names** ([above](#the-programs-names)): `api.shadow` took 0.5 seconds with Apple
clang 21 and 0.7 with GCC 16 on the Mac, 1.8 with Clang 18 and 1.1 with GCC 13 on 16 threads of
the Linux machine, and 5.3 with MSVC on the Windows machine, where it compiles the program seven
times, three of them under `/analyze`; measured on 2026-11-19 in a quick tier run with
`--parallel 4`.
The 8 calls of constructors that the same change added to the cases of the checks add 8 runs per
state of the environment to each `api.checks.*.rounding` and `api.checks.*.flush`, under a second
on every machine.

**The settings of `KAIRN_ENCLOSURE_CODE`** ([Flag sets](#flag-sets), [The operations of Ball
outlined and external](#the-operations-of-ball-outlined-and-external)) were measured on 2026-11-20
on the Mac with Apple clang 21, against the commit before them, back to back, `--parallel 4`; other
jobs loaded the machine, much more during the second full tier (load average 7 to 8 for the
first, up to 59 during the second):

| Mac, Apple clang 21 | Before | After |
|---|---|---|
| Quick tier | 301 tests, 39.2 s (152.9 s of test time) | 307 tests, 34.1 s (132.6 s) |
| Full tier | 420 tests, 384 s (996 s of test time) | 436 tests, 552 s (1 269 s) |
| Build | 7 s | 9 s |

The quick tier gains six tests, 1.8 seconds of test time (`api.link.external.*`, 0.4 to 0.5 s each,
and `api.reject.enclosure_code.*`), and `objcode.check` compiles three more units in one
configuration. The full tier's difference is mostly the load: tests that this change does not
touch took longer too (`full.kairn-gen.test` 115.7 and 213.2 s, `full.kairn-oracle.selftest` 47.8
and 69.3 s). What the change adds is: two more runners on every form of every kernel in
`full.api.oracle` (372 runs of a runner on 10 000 lines each, 85 ms per run on that machine, so
about 63 s of test time; measured 112.7 and 189.3 s in all), two more of ten flag sets in
`full.api.flags.oracle` (93.1 and 135.8 s), 72 compilations of the enclosure unit in
`full.objcode.check` (8.1 and 16.6 s for the two tests of the object code), and 16 tests of 3.9 s
in all (`full.api.checks.outlined.*`, `full.api.checks.external.*`, `full.api.checks.handler.*`,
`full.api.flags.O3-outlined.*`, `full.api.flags.O3-external.*`): about 100 seconds of test time by
these estimates, some 25 seconds of wall time with `--parallel 4`.

**The public functions of the first wave of Milestone 2** (the building blocks on `T`, `ldexp` and
`half` of a ball, the ball of a constant and the signs of a ball) were measured on 2026-11-20 on
the Mac against the commit before them, each pair back to back, `--parallel 4`, both builds with
the times of an earlier run (other jobs loaded the machine, load average 6 to 14):

| Mac | Quick tier, before | Quick tier, after | Test time, before and after | Full tier, after |
|---|---|---|---|---|
| Apple clang 21 | 347 tests, 37.3 s | 383 tests, 39.4 s | 148.9 and 157.3 s | 556 tests, 471 s |
| GCC 16 | 348 tests, 32.9 s | 384 tests, 35.8 s | 131.4 and 142.7 s | 556 tests, 402 s |

The quick tier gains 36 tests: `api.oracle.K.F` for the fifteen kernels that became public (7.1 and
7.4 seconds of test time), five of `api.reject.*`, and `api.example.building_blocks`; the checks of
a debug build run 22 functions more (0.7 and 1.2 s). The full tier gains 60, the same fifteen
kernels in `full.api.oracle.K.F` and `full.api.flags.oracle.K.F`.

Those numbers are of the commit before them on `main`, before the folds' stage. Joined to the
folds' stage the same day, the change adds the same 36 and 60 tests: with Apple clang the quick
tier has 385 tests before and 421 after, the full tier 561 and 621. Two runs of the quick tier of
each, back to back on the Mac under a load average of 18 to 42, took 80.4 and 75.3 s before and
74.2 and 64.3 s after (314 and 295, 288 and 250 s of test time): at that load the difference is
the load's, not the change's. The full tier after took 1 059 s with Apple clang and 752 s with
GCC 16 (load 13 to 36).

**`Interval` and the functions of a `Ball` of the enclosure interface** were measured on
2026-11-20 against the commit before them, the quick tiers back to back on the Mac,
`--parallel 4`, under a load average of 12 to 49 from other jobs:

| Where | Quick tier, before | Quick tier, after | Full tier, after |
|---|---|---|---|
| Mac, Apple clang 21 | 571 tests, 84.2 s | 633 tests, 109.8 s (load 49 at its end) | 980 tests, 1 236 s |
| Mac, GCC 16 | 572 tests, 87.2 s | 634 tests, 91.3 s | 980 tests, 1 276 s |
| Linux, 16 threads, GCC 13 | | 634 tests, 179.8 s | 980 tests, 1 985 s |
| Linux, 16 threads, Clang 18 | | 631 tests, 183.2 s | 980 tests, 1 980 s |

The quick tier gains 62 tests: `api.oracle.K.F` for the 24 kernels that became public (48), ten
of `api.reject.*` (five `interval.*`, `ball.implicit_narrowing`, `not_constexpr.interval_add` and
three `unverified.*`), and `api.example.intervals` under each contraction setting (4); the checks
of a debug build run 29 functions more. The full tier gains 96, the same 24 kernels in
`full.api.oracle.K.F` and `full.api.flags.oracle.K.F`.

**`Packed` and the containers** were measured on 2026-11-21 against the commit before them, the
quick tiers on the Mac under a load average of 8 to 13 from other jobs, and those of the Linux
machine on 16 of its threads:

| Where | Quick tier, before | Quick tier, after | Full tier, before | Full tier, after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 633 tests, 88 s | 653 tests, 89 s | | |
| Mac, GCC 16 | 634 tests, 82 s | 654 tests, 95 s | | |
| Linux, 16 threads, GCC 13 | 634 tests, 137 s | 657 tests, 169 s | 980 tests, 1 894 s | 980 tests, 1 924 s |
| Linux, 16 threads, Clang 18 | | 654 tests, 196 s | | |

The quick tier gains 20 tests on the Mac (`api.packed.FORM`, `api.soa.FORM` and
`api.example.packed_dot.FORM` in two forms, and 14 of `api.reject.*`) and 23 on x86-64 with GCC 13,
whose default build makes the AVX2 form as well. The packed forms of the kernels add no test of their
own but longer runs of the runner in `api.oracle.*` (4 to 7 seconds of test time on the Mac) and of
the checks. The test time of the quick tier grew from 336 to 346 seconds with Apple clang and from
305 to 353 with GCC 16, 20 of those 48 seconds in `api.reject.*`, whose new cases compile
`kairn/packed.hpp` twice each (GCC parses `arm_neon.h` and the generated header slowly:
[Packed](../reference/packed.md#compile-time)). On the Linux machine with GCC 13 it grew from 504 to
615 seconds: 61 in `api.oracle.*`, where the packed forms run in three runners (the third built for
AVX2), 26 for the new tests, 22 in `api.checks.*` and 9 in `api.reject.*`. The full tier has the same
980 tests, the packed forms joining `full.api.oracle.*` and `full.api.flags.oracle.*`.

**The test of a product passed into `Packed`** (`api.boundary.packed.*`) was measured the same day
against the commit before it, on the Linux machine in the default build and with `-mavx2 -mfma`
in the build's flags:

| Where | Quick tier, before | Quick tier, after | Of which `api.boundary.packed.*` | Full tier, before | Full tier, after |
|---|---|---|---|---|---|
| Mac, Apple clang 21 | 653 tests, 89 s | 669 tests, 93 s | 11.0 s of test time | | |
| Mac, GCC 16 | 654 tests, 89 s | 670 tests, 94 s | 10.9 s | | |
| Linux, 16 threads, GCC 13 | 657 tests, 145 s | 673 tests, 174 s | 24.9 s | 980 tests, 1 939 s | 980 tests, 2 009 s |
| Linux, 16 threads, Clang 18 | 654 tests, 150 s | 670 tests, 200 s | 21.0 s | | |
| Linux, 16 threads, GCC 13, `-mavx2 -mfma` | 654 tests, 152 s | 670 tests, 178 s | 32.5 s | | |
| Linux, 16 threads, Clang 18, `-mavx2 -mfma` | 651 tests, 151 s | 667 tests, 193 s | 22.1 s | | |

It adds 16 tests to every quick tier (two forms, four contraction settings, the test and its
control), each under two seconds, and none to the full tier. On the Linux machine the other tests
took 60 to 160 seconds of test time more in the runs after than in the runs before, which ran
later: the machine's load (a load average of 24 to 27 from other jobs), since none of those
tests changed.

The full tier's cross-checks of the maps and folds write a summary of each run of up to 1.7 GB
(`full.crosscheck.compiled.add_2.binary64`, `axpy_2`), some 18 GB in all for one run on the Mac. In
both runs above the Mac's disk was nearly full, from other jobs too, and some of these
cross-checks failed for want of space: 79 of 980 with Apple clang (the disk had 105 MB free) and 7
with GCC 16; each passed when rerun (`ctest --rerun-failed`) with the summaries of finished runs
deleted as they came. None of them is about intervals. Summaries of that size were a defect,
fixed since ([The size of the summaries](#the-size-of-the-summaries)): a full-tier build tree is
now about half a GB.

**The oracle of stage B2 of the enclosure interface** (the predicates and comparisons of an
interval and of a ball, the set operations of a ball, the conversions of two limbs: 53 kernels)
was measured on 2026-11-21 against the commit before it, `--parallel 4`, the Linux machine on 16
threads. Before it, the claims of two families were unreadable and every test that runs the
oracle failed for that alone; after it, the tiers ran against `gen/claims.json` without the other
family, the accumulator and the ball vectors (`-DKAIRN_ORACLE_CLAIMS=FILE`, [Against other
claims](#against-other-claims)),
so that the counts below lack that family's tests. A test that fails on the claims fails at once,
so the times before are short of what those tests take; and the Linux machine was shared with
other jobs, so its times vary from run to run (its quick tier with GCC took 178 s and 165 s on two
runs of the stage, a commit apart that adds only a guard):

| Where | Quick tier, before | Quick tier, after | Full tier, before | Full tier, after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 633 tests, 534 failing, 90.9 s | 739 tests, 105.1 s | | |
| Linux, GCC 13 | 634 tests, 534 failing, 161.1 s | 740 tests, 164.6 s | 980 tests, 934 failing, 2 482 s | 1 154 tests, 2 874 s |
| Linux, Clang 18 | 631 tests, 534 failing, 159.6 s | 737 tests, 182.2 s | | |

The quick tier gains 106 tests, `crosscheck.compiled.K.F` of the 53 kernels in two formats, on
2 000 cases each (`KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES`); the full tier 174: the same on 20 000
cases (106), the interpreter's enumerations of their toy formats (53) and the sampled runs of
the kernels of two intervals (14), and `full.tools.crosscheck.guards.EnclosureGuards`. The largest
summary of a kernel of the stage in the quick tier is 36 KB (`interval_mid_rad_2`), and in the full
tier none is among the ten largest (the tenth is 0.96 MB); the largest of the quick tier is still
`two_prod_dekker`'s, 0.98 MB, and of the full tier `mul_pow2_map_1`'s, 2.7 MB (`binary64`, `cxx`). The oracle's whole selftest
takes 529 s on the Mac with 8 workers (103 tests, nine of them the stage's), and of its 338
mutants (`oracle/selftest/mutants.py`) 90 are the stage's.

**The public functions of the enclosure interface** (the 53 kernels of stage B2 made public by
`kairn/interval.hpp` and `kairn/ball.hpp`: [One enclosure interface](../reference/enclosure.md))
were measured on 2026-11-21 against the commit before them, the tree that joins the oracle of
stage B2: the Mac with `--parallel 8`, the Linux machine with `--parallel 16`, both shared with
other jobs; on the Linux machine with the tools that would take every processor held to one worker
(`KAIRN_GEN_JOBS=1`, `KAIRN_ORACLE_JOBS=1`), so that the full tier's `full.tools.kairn-oracle.selftest`,
which then passes its limit of 600 s, ran alone after the rest with 16 (the second time of that
column). A first run of each quick tier on the Linux machine after the change took 143 to 151 s:
ctest noticed nothing for 10 s at a time, so that every test then running reported a multiple of
10 s (tests of under a second reported 10 to 60). The pauses came and went: a second run had none
with GCC 13, with and without `-mavx2 -mfma`, one at the very end with Clang 18 (four examples of
0.02 s that reported 10.02), and some with Clang 18 and `-mavx2 -mfma`, in a second run and a third
(110 s and 108 s; `api.oracle.coverage`, under a second elsewhere, reported 29.5 s), each pause in
tests that the change does not touch; the times below are those of the last run of each.

| Where | Quick tier, before | Quick tier, after | Full tier, before | Full tier, after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 851 tests, 75.0 s | 984 tests, 81.2 s | | |
| Mac, GCC 16 | 852 tests, 83.3 s | 985 tests, 84.6 s | | |
| Linux, GCC 13 | 855 tests, 80.3 s (60.5 s on a second run) | 988 tests, 67.3 s | 1 285 tests, 996 s and 267 s | 1 497 tests, 1 050 s and 263 s |
| Linux, GCC 13, `-mavx2 -mfma` | 852 tests, 68.3 s | 985 tests, 73 s | | |
| Linux, Clang 18 | 852 tests, 76.4 s | 985 tests, 74 s | | |
| Linux, Clang 18, `-mavx2 -mfma` | 849 tests, 72.1 s | 982 tests, 108 s, with the pauses (below) | | |

The quick tier gains 133 tests: `api.oracle.K.F` of the 53 kernels in two formats (106), each with
two to ten forms, the 2 000 cases of `KAIRN_API_QUICK_CASES`; `api.example.bisection` under each
contraction setting (4); and 23 of `api.reject` (`enclosure.*` 12, `unverified.*` 7 and
`unverified_only.*` 4). The full tier gains 212: `full.api.oracle.K.F` and
`full.api.flags.oracle.K.F` of the 53 kernels in two formats. Of the full tier after, every test
passed but `full.tools.kairn-gen.test`, whose rule test
`test_every_kernel_the_public_headers_call_is_an_entry_kernel` (`gen/tests/test_rules.py`) lists
the kernels the public headers call, and lists those of stage B2 as not called yet; with the 53
added to that list (`TheKernels.WAVE_2_B2`) it passes.

**`two_prod` in constant evaluation and the two executions of 63 kernels** (`kairn::two_prod`
refused in constant evaluation on finite operands where an operation of Dekker's product
overflows; a theorem of the two executions for every kernel whose C++ dispatches on constant
evaluation) were measured on 2026-11-21 against the commit before them, the tree with the public
functions of the enclosure interface: the Mac with `--parallel 8`, the Linux machine with
`--parallel 16`, both shared with other jobs; the full tier with the tools that would take every
processor held to one worker (`KAIRN_GEN_JOBS=1`, `KAIRN_ORACLE_JOBS=1`), with which
`full.tools.kairn-oracle.selftest` took 963 s and passed among the rest. The counts before are
those of `ctest -N` on that commit, the times before those of the paragraph above.

| Where | Quick tier, before | Quick tier, after | Full tier, before | Full tier, after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 984 tests, 81.2 s | 988 tests, 91.0 s | | |
| Mac, GCC 16 | 985 tests, 84.6 s | 989 tests, 93.6 s | | |
| Linux, GCC 13 | 988 tests, 67.3 s | 992 tests, 68.4 s | 1 497 tests, 1 050 s and 263 s | 1 497 tests, 1 071 s |
| Linux, GCC 13, `-mavx2 -mfma` | 985 tests, 73 s | 989 tests, 74.0 s | | |
| Linux, Clang 18 | 985 tests, 74 s | 989 tests, 74.4 s | | |
| Linux, Clang 18, `-mavx2 -mfma` | 982 tests, 108 s | 986 tests, 108.1 s | | |

The quick tier gains 4 tests, `api.reject.two_prod.overflows_in_constant_evaluation.*` (a
partial product and the product, for `double` and `float`, cases 93 to 96), each under a second;
the full tier none (`api.constexpr`, which the flag sets build too, gained its checks, not tests).
The generator's whole suite passed with 413 tests in 3 179 s on the Mac (Apple clang and GCC 16,
`--jobs 8`) and 409 in 2 675 s on the Linux machine (GCC 13 and Clang 18, `--jobs 10`, one test
skipped), the proofs with 1 495 audited theorems (173 of `Audit.v`, 957 of `HandAudit.v`, 365 of
`IeeeAudit.v`; 1 378 before: 173, 903, 302), and the oracle's whole selftest with its 119 tests in
614 s on the Mac (`--jobs 6`).

**The joined tree**, the oracle of stage B2 merged into the join of the ball vectors, the lanes of
the packed runners and `Packed` (2026-11-21): the first tree whose oracle reads every claim of
`gen/claims.json`, so that every tier runs against it with nothing left out
(`KAIRN_NOT_YET_CROSS_CHECKED` empty). Every test passes: the quick tier with 851 tests in 90 s on
the Mac with Apple clang and 852 in 99 s with GCC 16 (`--parallel 8`), 855 in 66 s with GCC 13 and
852 in 66 s with Clang 18 on the Linux machine, 852 in 69 s and 849 in 73 s with `-mavx2 -mfma`
(`--parallel 16`); the full tier with 1 285 tests in 1 006 s with GCC 13 there. The 53 kernels of
stage B2 run in every packed runner with the lanes permuted under the guard (and consecutively
where the tier asks), their masks all ones or zero in each lane (the packed runner refuses any
other): per runner and format, 53 kernels and 106 000 requests in the quick tier, 1 060 000 in the
full tier, with these registers and registers that mixed a request with a non-finite limb beside
one with finite limbs (permuted):

| Form | Quick tier: registers, mixed | Full tier: registers, mixed |
|---|---|---|
| NEON, `binary64` (W = 2) | 53 000, 14 914 | not measured (no full tier on the Mac) |
| NEON, `binary32` (W = 4) | 26 500, 13 791 | not measured (no full tier on the Mac) |
| AVX2, `binary64` (W = 4) | 26 500, 13 852 | 265 000, 138 165 |
| AVX2, `binary32` (W = 8) | 13 250, 10 202 | 132 500, 100 090 |

Every guard passed, and the oracle failed none of the 212 000 lines of the quick tier's
summaries of these kernels (2 120 000 in the full tier). The largest summary of the quick tier is
0.98 MB (`two_prod_dekker`, `binary64`), of the full tier 2.7 MB (`mul_pow2_map_1`), under the
guards' 4 MiB. The oracle's whole selftest took 566 s on the Mac (119 tests, beside another
session's jobs), and its 448 mutants 3 580 s on the Linux machine (`--jobs 16 --fail-fast`, one
worker each), all caught.

**Waste removed** before anything left the quick tier, as measured on 16 threads of the Linux
machine with GCC 13:

- *The same requests, generated and judged again for every runner.* Each kernel and format had
  one test per compiled runner (8 on each platform but clang-cl, which has 10), each generating
  the same 20 000 requests and judging its own output: 1 008 tests, 20.2 million cases generated
  and judged, 957 seconds of test time. Now one test per kernel and format generates the requests
  once and has every runner complete them; the outputs were the same, byte for byte (but for four
  kernels with MSVC, [above](#cross-checks)), so the oracle judges one per test: on the same 20 000
  cases, 126 tests, 2.5 million cases, 251 seconds (`full.crosscheck.compiled`).
- *The same requests, generated and judged again for every form of the public interface.*
  `api.oracle` had a pipeline per form, per runner and per format: 744 pipelines of 10 000 cases
  (186 forms of 48 kernels), each generating and judging its own requests, 451 seconds. Now each
  test generates its requests once, both runners complete them with every form, and the oracle
  judges each distinct output, one per test but a few: on the same 10 000 cases,
  122 seconds (`full.api.oracle`).
- *Runner outputs written line by line to a file.* On the Windows machine, a file as the scalar
  runner's standard output, or cmake's `OUTPUT_FILE`, cost 0.09 to 0.1 seconds per run on 2 000
  requests against 0.02 through a pipe; the driver of the tests (then `tests/run_runners.py`, now
  `tests/crosscheck.py`) reads the outputs through pipes, which brought a test of the full tier's
  compiled runners there from 6.2 to 1.9 seconds.
- *Python processes.* The two groups above started about 4 500 Python processes per run; then 794
  in the quick tier (four per test of the compiled runners, three per test of the public
  interface, and the second output of `mul_pow2_2`), and since each cross-check runs in one
  process ([below](#each-cross-check-in-one-process)), one per test: 222.
- *Suites that used every core beside three other tests.* The generator's tests and the oracle's
  started one worker process per processor while ctest ran three more tests beside them: on a
  hosted runner, four workers and three other tests on four cores. The parts with a pool are now
  in the full tier, with four workers that ctest counts.
- *Work repeated across the CI.* The generator's tests without C++ ran in each of the five jobs
  of `build.yml` and again, inside the whole suite, in each of the three of `generator.yml`; the
  interpreter's 67 enumerations, which are Python alone in exact arithmetic, ran in each of the
  five. Now the generator's longest tests run once per operating system and the enumerations
  once; since the tools' tests left the quick tier ([below](#the-tools-tests-leave-the-quick-tier)),
  the rest of the generator's tests without C++ do too.

**What left the quick tier**, and what that costs. The interpreter's enumerations of toy formats,
the generator's four longest test classes and the oracle's six enumerations left whole; the
cross-checks of the compiled runners keep 6 000 of their 20 000 cases and the public interface
2 000 of its 10 000. To see what the smaller samples still catch, every applicable one-statement
change of each kernel's generated scalar code was planted in turn (`tests/kernel_mutants.py`: an
operator turned, an operand dropped, an FMA made a product or given a zero addend, a comparison
loosened, a constant shortened, a selection swapped: 1 052 changes of the 63 kernels, in their
`double` and `float` code alike, and a statement of a fix-up in both of its forms), built into
three scalar runners (the build's flags, `-ffp-contract=off` and `=fast`, all at `-O3`) and the
public interface's runner, and put through the cross-checks and the public interface's tests of
its kernel with each tier's samples. On the Linux machine with GCC 13 (results in
`results/milestone1/mutants/`), the full tier catches 865 and the quick tier 863 of them, and
nothing the full tier misses. The two it misses fail on one or two cases of the full tier's
20 000: `ball_scale_2` with one FMA computed as a product and a sum (only the `-ffp-contract=off`
runner shows it), and `add_fast_2_2_full` with its finiteness test `inf > a` loosened to
`inf >= a`, first at case 9 280. The samples were chosen by this experiment, when it was first run
on the Mac (863 and 861 then, with the same two between the tiers): with 2 000 cases for the
compiled runners two more went unseen, and with 1 000 for the public interface three more. The
oracle's own mutants (`oracle/selftest/mutants.py`, 65 of them) are all caught by the part of its
selftest that was then in the quick tier (now `full.tools.kairn-oracle.selftest`) but one,
`exhaustive: -inf left out of a one-limb domain`, which only an enumeration can see and
`full.kairn-oracle.selftest` catches.

**What neither tier catches.** The tiers judge results against the kernels' claims, so a change
that alters a result while keeping every claim passes them by design: 187 of the 1 052 do. What
guards the listing itself is the generator's comparison with the interpreter
([below](#the-generators-tier)), which the same tool runs with `--bits`: the generator's scalar
runner with the changed kernel alone, built in the 15 configurations of that test with GCC 13 and
again with Clang 18, on that test's cases, every result required to be bit-identical to the
interpreter's. With both, each change falls in one class:

| Class | Changes |
|---|---|
| Caught by the quick tier | 863 |
| Caught by the full tier only | 2 |
| Caught by the comparison with the interpreter only | 122 |
| Caught by nothing | 65 |

Of the 122, 70 are FMAs computed as a product and a sum, 18 FMAs of a zero addend computed as a
plain product, 12 FMAs given a zero addend, 8 shortened constants and 14 others; GCC's builds catch
all of them, Clang's 119. Each of the 65 was then examined by hand, with two searches for an operand
on which it differs from the kernel: the changed and the original kernel compiled side by side, on
every combination of the special values of the format in every position (or 4 million of them),
4 million random cases per format from strata like the tests' and from numbers just above and below
a power of two, as many with non-finite operands for a kernel of the extended domain and with any
value anywhere, and every binary32 number for a one-input kernel; and 500 000 cases per format of
the oracle's own generator, which keeps to the kernel's domain. The verdicts, with the reasons and
the operands, are in `results/milestone1/mutants/survivors.json`:

- **48 are equivalent**: they cannot change a result. 9 guards `a + 0.0` (which turns −0 into +0)
  made `a - 0.0`: the guarded value only enters a TwoSum whose error term is +0 for both zeros, or
  in a fix-up a product with infinity. 8 finiteness tests of a Ball's center loosened to `>=`: an
  infinite center also makes the radius infinite or NaN, which the test beside it catches. 31 FMAs
  of a zero addend computed as a product, or as a product and a sum: these change only the sign of
  a zero result, and that zero goes into a radius that ends with the addition of a positive
  constant, into `next_up`, into a product with infinity, into Dekker's error sum, where the sign
  of a zero cannot survive, or, in Veltkamp's split, cannot occur.
- **17 were blind spots**: an operand tells them apart, and no test supplied it. 7 on operands of
  the kernel's domain: in `mul_2_2`, `mul_2_2_full`, `ball_mul_2` and `ball_mul_2_full`, `x1 * y1`
  for the FMA gives a low limb −0 instead of +0 for a pair with a negative tail times zero; `split`
  with its splitter $2^s + 1$ shortened to $2^s$ gives a high half of 13 bits instead of 12 to a
  binary32 number just above a power of two; and Dekker's product with either splitter shortened
  has another error term near underflow in binary32. 10 only on operands outside the domain (a pair
  that is not normalized, or not canonical), which the comparison takes too: bit identity holds on
  any operand. None breaks a claim: on every operand of the domain found, the oracle passes the
  changed result, since Kairn leaves the sign of a zero unspecified, the error term stays within
  the claim's allowance for underflow, and `split` claims only $a = a_h + a_l$ (that its high half
  has at most half the precision, which Dekker's product relies on, is in its description but is
  not a claim).

Those operands are now among the comparison's cases (`SPECIAL_CASES` in `gen/tests/test_cxx.py`),
and it catches all 17: of the 1 052 changes, the tests now catch 1 004, and the 48 they miss cannot
change a result. With `--jobs 32` the whole run took 47 minutes on 32 hardware threads of the Linux
machine; the comparison alone (`--no-tiers`) takes about a minute per change and core, and
`--ids` reruns given changes (`results/milestone1/mutants/README.md`).

The stopgap of the one tier, a timeout of 1 800 seconds for the generator's and the oracle's tests
and of 60 minutes for the jobs of `build.yml`, is gone: their timeouts are 600 seconds and 30
minutes again.

### The tools' tests leave the quick tier

On the hosted runners the quick tier's ctest step took 128 to 202 seconds on Windows (167 and 172
on the median runs with MSVC and clang-cl), over the two minutes of the brief, and 54 to 126
elsewhere ([Costs, Milestone 1](results/costs-milestone1.md#4-the-quick-tier-on-the-hosted-runners)).
Five tests of the tools set that time, two fifths of the quick tier's test time there, and none
builds anything of Kairn's with the build's compiler: the oracle's selftest (34 to 105 seconds),
the guards' tests (23 to 58), the generator's (14 to 36), the reference script's (8 to 49) and
the brute-force driver's (1 to 4). On 2026-11-19 they moved to the full tier as `full.tools.*`,
and run in CI where they ran before ([Continuous integration](#continuous-integration)); the
debug build's runner left the quick tier's `api.oracle.K.F` (below). Measured as above, the
builds of before (the commit before) and after one after the other on the same machine; a second
run of a build reads ctest's times of the first and starts the longest tests first. The Mac was
loaded by other jobs (load average 4 to 14); the runs on the Windows machine during another job's
builds and tests there are left out. Seconds, the first run of a build, then the later ones:

| Where | Quick tier, before | The tools' tests out | After: the debug build's runner out too | Full tier, before and after |
|---|---|---|---|---|
| Mac, Apple clang 21 | 56.0; 51.0, 51.4 | 41.7; 36.2 | 40.1, 41.4; 35.1 | 357 and 374 |
| Mac, GCC 16 | 50.1; 50.1, 47.0 | 36.8; 32.4 | 36.4; 30.9 | 294 and 320 |
| Linux, 16 threads, GCC 13 | 82.6; 79.2 | 53.0; 48.3, 48.6 | 52.2, 53.5; 48.7 | 534 and 563 |
| Linux, 16 threads, Clang 18 | 83.3; 80.5 | 54.1; 48.9, 48.1 | 52.7; 47.4 | 531 and 561 |
| Windows, 8 logical processors, MSVC | 110.3; 123.0, 105.7 | 76.7; 69.6 | 71.2, 69.1; 66.1, 63.8, 63.3 | 608 and 652 |
| Windows, 4 logical processors, MSVC | 136.1, 144.7 | 93.8, 87.6 | 84.1, 85.6 | |

The runs on 4 logical processors followed runs on 8 of the same builds, and read their times.
The full tier after is the same with or without the debug build's runner in the quick tier: the
Windows machine's is that of the build with the tools' tests out, since the run of the last
build there shared the machine with another job's full tier (1 024 seconds; it passed). Without
`--parallel`, the quick tier took 133 seconds on the Mac (194 before) and 189 on 16 threads of
the Linux machine.

The quick tier's test time is now that of the tests of the library: on 16 threads of the Linux
machine with GCC 13, 198 seconds, of which the compiled runners' cross-checks 106 (126 tests),
the public interface against the oracle 52 (97 tests), the checks of a debug build 17 (9), what
must not compile 9 (29), the object code 7 (3) and the 27 others 7; on the Windows machine 279,
of which 155 and 77 for the first two. No test takes more than five seconds, so with
`--parallel 4` the wall time is a quarter of the test time. The full tier gained the five tests,
60 seconds of test time on the Mac and 166 on the Windows machine, which run beside its longest
tests; in CI, the jobs of `full.yml` that build gain the four that are not the generator's (206
seconds of test time on the median hosted Windows run, about a minute of wall time on four
slots).

**On the hosted runners.** The stored per-test times of the median runs
(`results/milestone1/costs/ci/`), replayed on four slots without the five tests
(`python3 bench/ci_times.py tables`), give 102 seconds for the ctest step with MSVC and 106 with
clang-cl, 40 to 41 on Linux x86-64, 29 to 30 on arm64 and 51 on macOS. But the quick tier has
gained tests since those runs: the regression cases, the object code, the checks of a debug build
and its self-test and constant expressions, more of what must not compile, two examples, and the
debug build's runner in `api.oracle.K.F`. Each was put at its time on the Windows machine times
the ratio of the hosted to the local time of the tests the two runs share, the stored hosted
time kept for the others, and the quick tier replayed as ctest schedules it without its times of
an earlier run (in the order the tests are registered, a test of `PROCESSORS 2` on two slots); a
second estimate put every test at its local time times its family's ratio. The ratio is 1.58
with MSVC and 1.66 with clang-cl against the Windows machine on 8 logical processors (1.5 to 1.75
by family for the cross-checks and the public interface), 1.27 and 1.33 against it on 4, whose
times are closer to the hosted runners'; the four estimates agree within 3 seconds. With the
debug build's runner, the ctest step comes to 115 to 116 seconds with MSVC and 120 to 121 with
clang-cl; without it, 108 to 110 and 113 to 116. On Linux x86-64 the same estimates give 48
seconds with GCC, and on macOS 54.

**The debug build's runner** in `api.oracle.K.F` took 14 to 16 seconds of the quick tier's test
time on the Windows machine (5%; its forms run at `/Od`, with `/RTC1` and the debug C runtime),
an estimated 19 to 21 on a hosted Windows runner, 5 to 6 of the ctest step: with clang-cl, the
difference between two minutes and less. On the Mac and the Linux machine it took 3 to 4 seconds
of test time, one or two of wall time. The full tier judges the same runner on every form, on
the same 2 000 cases (`full.api.flags.oracle.K.F`), and keeps it in `full.api.oracle.K.F` on the
first form of each kernel on 10 000; the quick tier keeps the debug build's self-test, constant
expressions and checks. It left the quick tier.

**The margin** is small: 4 to 12 seconds by these estimates, while the hosted runners of one
platform differ by a fifth from run to run (the five runs of each Windows job of
[Costs, Milestone 1](results/costs-milestone1.md) ranged from 23% under their median to 18% over
it), so a slow Windows runner can still take more than two minutes. Each 1 000 cases fewer per
compiled cross-check would save about 8 seconds of the ctest step with MSVC and 6 with clang-cl,
each 1 000 fewer per test of the public interface 7 and 4 (by the fixed and per-case costs of the
same page); the samples are those that the planted faults chose ([above](#time)). Fewer
processes would not change what is checked: on the Windows machine one compiled cross-check
(`add_2_2`, `binary64`, eight runners) took 1.6 to 1.7 seconds, of which the oracle's generator
0.36 (0.11 for one case), the eight runners through `run_runners.py` 0.66 to 0.69 (0.05 to 0.08
each, on 6 000 lines), the oracle's check 0.36 and the guards 0.08, and a Python process started
in 0.05. Generating, checking and guarding in the process of `run_runners.py` would save about a
quarter of a second per compiled cross-check there and a fifth per test of the public interface,
by the ratios above 15 to 20 seconds of the hosted ctest step. It was done next
([below](#each-cross-check-in-one-process)).

### Each cross-check in one process

After the tools' tests left the quick tier, its ctest step on the hosted Windows runners took 71
to 154 seconds with MSVC and 70 to 96 with clang-cl in the first three runs (`1bd3182`, `eed45fe`,
`d31a81a`): over two minutes on one of the six, and the whole job over two minutes on five; 44 to
45 on Linux x86-64, 31 to 35 on arm64, 69 to 75 on macOS. On 2026-11-20 running each cross-check
in one process, which loses no check, rather than fewer cases, was put to the owner as a default
and not objected to ([Milestone 1 report](results/milestone1.md#decided-by-the-owner), item 5).
Since then each test
`crosscheck.compiled.K.F` and `api.oracle.K.F`, and each of the full tier's tests of the same
families, is one Python process, `tests/crosscheck.py` ([Cross-checks](#cross-checks)); before, it
was a CMake script that started the oracle's `gen`, `tests/run_runners.py` (which ran the
runners), the oracle's `check` for each distinct output and the guards, each a Python process.

**Where the time went**, before the change: each stage of `crosscheck.compiled.add_2_2.binary64`
(eight runners on 6 000 cases) and of `api.oracle.add_2_2.binary64` (two runners, two forms each,
on 2 000 cases) alone, on each test machine, the median of seven runs; and the whole tests and
those of the full tier through ctest, alone, before and after alternating, four times. The Linux
machine on 16 of its threads, the Windows machine held to 8 logical processors. Seconds:

| Stage | Mac, Apple clang 21 | Linux, GCC 13 | Windows, MSVC |
|---|---:|---:|---:|
| Starting Python (`python3 -c pass`) | 0.013 | 0.031 | 0.030 |
| Starting cmake (`cmake -P` of an empty file) | 0.006 | 0.007 | 0.023 |
| The oracle's `gen` of one case: its start, imports and claims | 0.041 | 0.086 | 0.095 |
| `gen` of the test's 6 000 cases, into a file | 0.121 | 0.289 | 0.213 |
| A runner on no input: starting it | 0.003 to 0.006 | 0.004 to 0.005 | 0.013 to 0.017 |
| A runner on the 6 000 lines | 0.050 to 0.054 | 0.022 to 0.033 | 0.041 to 0.044 |
| `run_runners.py` with the eight runners | 0.440 | 0.278 | 0.395 |
| The oracle's `check` of no input: its start, imports and claims | 0.045 | 0.088 | 0.094 |
| `check --json` of the 6 000 lines | 0.135 | 0.326 | 0.224 |
| The guards | 0.025 | 0.055 | 0.063 |
| In one process: importing the oracle's modules | 0.023 | 0.046 | 0.047 |
| In one process: generating the 6 000 cases; judging them | 0.079; 0.076 | 0.215; 0.209 | 0.117; 0.112 |
| `crosscheck.compiled.add_2_2.binary64`, before; after | 0.77 to 0.78; 0.69 to 0.70 | 0.98 to 0.99; 0.85 to 0.87 | 0.93 to 0.99; 0.73 to 0.77 |
| `api.oracle.add_2_2.binary64`, before; after | 0.33 to 0.34; 0.22 | 0.58 to 0.59; 0.35 to 0.40 | 0.54 to 0.63; 0.35 to 0.36 |
| `full.crosscheck.compiled.add_2_2.binary64` (twelve runners, 20 000 cases), before; after | 3.38 to 3.39; 3.31 to 3.32 | 2.79 to 2.84; 2.66 to 2.69 | 3.11 to 3.29; 2.94 to 3.13 |
| `full.api.oracle.add_2_2.binary64` (three runners, 10 000 cases), before; after | 1.23 to 1.24; 0.97 | 1.55 to 1.59; 1.20 to 1.22 | 1.43 to 1.49; 1.07 to 1.13 |

The earlier profile ([above](#the-tools-tests-leave-the-quick-tier)) holds in its shape; its times
were those of the test beside three others, as in a run of the quick tier, where held to 8 logical
processors it takes 1.3 to 1.7 seconds on the Windows machine, and alone three fifths of that.
One correction: starting a runner is a third of its time there (0.013 to 0.017 seconds of 0.041
to 0.044), not most of it; the rest is reading its 6 000 lines and printing its results.
One process removes what is fixed per test: the start of cmake and of three Python processes (two
for the public interface), the second import of the oracle's modules and reading of the claims,
and the guards' process. It leaves generating, the runners and judging: 75 to 90% of a compiled
cross-check, 60 to 70% of one of the public interface, alone.

**Before and after**, the builds of the commit before and of the change, one after the other on the
same machine, alternating; seconds, the first run of a build, then the later ones, which read
ctest's times of the first. The Mac was loaded by other jobs (load average 4 to 10), the Linux
machine by other users (7 to 15):

| Where | Quick tier, before | Quick tier, after | Full tier, before and after |
|---|---|---|---|
| Mac, Apple clang 21 | 34.6; 33.0, 33.0 | 34.2; 28.6, 28.6 | 358 and 359 |
| Mac, GCC 16 | 34.1; 29.5, 29.2 | 28.0; 24.8, 24.7 | 299 and 293 |
| Linux, 16 threads, GCC 13 | 53.7; 47.8, 47.4 | 45.3; 40.1, 39.5 | 564 and 556 |
| Linux, 16 threads, Clang 18 | 55.0; 48.6, 48.5 | 47.2; 40.2, 40.5 | 561 and 554 |
| Linux, 4 threads, GCC 13 | 44.3 | 36.8 | |
| Linux, 4 threads, Clang 18 | 45.0 | 38.0 | |
| Windows, MSVC, 8 logical processors | 68.5, 69.0, 71.4 | 58.2, 57.4, 58.4 | 648 and 637 |
| Windows, MSVC, 4 logical processors | 89.9, 87.4 | 73.8, 73.2 | |
| Windows, MSVC, all 20 logical processors | 66.7; 66.6, 64.0, 64.5 | 55.7; 53.3, 52.4, 52.2 | 664 and 653 |

The runs on 4 threads and on 8 and 4 logical processors followed others of the same builds, and
read their times; the first runs of the Windows machine read ctest's times of a run of two tests.

The tests of the two families, summed over a run of the quick tier (each test the median of its
runs above), and what each test gained:

| Where | `crosscheck.compiled.*`, 126 tests | `api.oracle.*`, 96 tests | The quick tier's test time |
|---|---|---|---|
| Mac, Apple clang 21 | 84.1 to 73.7 s, 0.08 a test | 35.0 to 27.3 s, 0.08 a test | 129.9 to 111.8 s |
| Mac, GCC 16 | 57.8 to 47.4 s, 0.08 | 34.4 to 26.5 s, 0.08 | 112.7 to 94.2 s |
| Linux, 16 threads, GCC 13 | 106.3 to 89.3 s, 0.13 | 51.5 to 36.1 s, 0.16 | 182.9 to 150.2 s |
| Linux, 16 threads, Clang 18 | 105.8 to 88.8 s, 0.13 | 51.5 to 36.2 s, 0.16 | 186.8 to 154.7 s |
| Windows, MSVC, 8 logical processors | 152.5 to 124.9 s, 0.22 | 77.1 to 58.3 s, 0.20 | 271.6 to 223.9 s |
| Windows, MSVC, 4 logical processors | 195.7 to 161.8 s, 0.27 | 95.7 to 71.7 s, 0.25 | 347.0 to 286.8 s |
| Windows, MSVC, all 20 logical processors | 139.2 to 110.3 s, 0.23 | 72.8 to 54.2 s, 0.19 | 250.6 to 202.9 s |

The full tier's wall time is set by its longest tests, the oracle's and the generator's pools and
the interpreter's enumerations, which did not change: it gained 0 to 2%. Its tests of the public
interface gained 0.12 to 0.25 seconds a test (`full.api.oracle.*`, and 0.08 to 0.28 for
`full.api.flags.oracle.*`, which runs every flag set's runner) on the Mac with GCC 16, the Linux
machine and the Windows machine on 8 logical processors, and its compiled cross-checks 0.08 to
0.11, a smaller share of their 1 to 4.5 seconds; in these single runs beside the longest tests the
noise is of the same size (with Apple clang the compiled cross-checks took 0.03 seconds more a
test, alone 0.07 less).

**On the hosted runners**, estimated as the cost page estimates (`bench/ci_times.py`,
[Costs, Milestone 1](results/costs-milestone1.md#the-tests-that-take-the-time)): the per-test
times of each of the three runs, read from their logs, each test of the two families scaled by
its ratio of after to before on the Windows machine held to 4 logical processors (the median of
its runs), replayed in the order ctest started them on four slots. Scaling each family by its
ratio of sums instead gives the same within 0.1 second, and the ratios of 8 or 20 logical
processors within 2 seconds; clang-cl takes MSVC's ratios (the Windows machine has no clang-cl).
Seconds of the ctest step:

| Run | MSVC: ctest's total; the replay; after | clang-cl: ctest's total; the replay; after |
|---|---|---|
| `1bd3182` | 153.2; 150.9; 126.4 (-24.5) | 89.0; 88.5; 73.8 (-14.7) |
| `eed45fe` | 69.8; 68.6; 57.7 (-10.9) | 94.9; 92.5; 77.5 (-14.9) |
| `d31a81a` | 96.3; 94.7; 79.6 (-15.1) | 68.1; 66.6; 55.8 (-10.9) |

The estimate is 56 to 80 seconds on five of the six runners and 126 on the slowest, whose runner
took 2.2 times as long as the fastest for the same tests: the saving is 11 to 25 seconds, a sixth
of the step, as the profile of the earlier estimate (15 to 20) had it. On such a runner the step
would stay at about two minutes; on the others it has a margin of 40 seconds or more.

**Measured in CI.** In the first two runs after the change the quick tier's test step took 73
and 80 seconds with MSVC and 81 and 93 with clang-cl on the hosted Windows runners (before: 71
to 154), 26 to 66 on Linux and 50 and 58 on macOS.

**Nothing was lost.** On each machine and compiler (the Mac with Apple clang 21 and GCC 16, the
Linux machine with GCC 13 and Clang 18, the Windows machine with MSVC), on the builds of before and
after: the lists of tests of both tiers are identical (names, order, labels, timeouts); the
oracle's summaries of every output judged are identical but for the path of the claims, which is
the source tree's (the cases, the strata, every count and extreme the guards read: per build on
the Mac and the Linux machine 224 summaries of the quick tier, 952 000 cases, and 389 of the full
tier, 12.2 million cases, the interpreter's among them; on the Windows machine, whose runners
give two outputs for four kernels, 234 and 419); and in ctest's logs every test of the two
families has the same result and the same lines
of verdict (the guards' line with the cases judged, the strata and the counts of the extended
domain; which runners and forms share an output). On the Mac, 32 runs with broken runners fail, or
pass, alike under both drivers: a runner that crashes, exits with an error, prints a line of
garbage, drops, repeats or cuts lines, prints nothing, returns a wrong result, or a non-finite one
on small operands, changes a tag, prints bytes that are not ASCII, ends its lines with CR LF,
leaves out the generator's headers, or does not exist; a stratum missing; for the public
interface, a list of forms that fails or is empty, a form that crashes, and the like. A runner
that changes an operand so that a case is outside the kernel's requirements passed under both,
the case shown as invalid; it fails since the cross-checks pass `check --expect-valid`
([What a pass requires](#what-a-pass-requires)). Of the faults planted
by `tests/kernel_mutants.py`, 42 (40 that the quick tier caught, of 36 kernels and every kind of
change, and the 2 that only the full tier caught) fail the same tests of each tier with both
drivers, as in the stored run of the whole experiment, on the Linux machine with GCC 13. The
oracle's own injected faults do not go through the drivers; `kairn-oracle selftest` passes.

**What is left** of a compiled cross-check is mostly its runners: on the Windows machine about
0.36 of its 0.75 seconds, on the Mac 0.43 of 0.70, beyond starting each runner 3 to 8
microseconds a line, which is handling text (splitting the line, parsing each limb with `strtod`
and printing each result with `printf`'s `%a`); the kernels themselves take nanoseconds
([Benchmarks](results/bench-milestone1.md)). A runner
that read and wrote its limbs itself would shorten every compiled cross-check without changing
what is checked; it would change the runners' code, and their output, which only has to be the
same among the runners of one build. Smaller: one process per runner of the public interface for
all of its forms, instead of one per form (0.013 to 0.017 seconds a process on the Windows
machine), and a cache of the oracle's compiled modules in the build tree (their import from
source takes 0.04 to 0.07 seconds a process, 0.01 to 0.03 from a cache).

### The size of the summaries

Until 2026-11-20 a map's summary in the full tier took up to 1.7 GB: on the Linux machine with
GCC 13, 17 summaries of the full tier were above 1 GB
(`full.crosscheck.compiled.sub_2.binary64.cxx.json` 1.70 GB) and 73 above 4 MiB, and a build
tree after both tiers took 41.0 GB, 40.6 GB of it in its 1 041 summaries. It filled a disk, made
another agent's tests fail, and was suspected of lengthening the hosted Windows full tier (27 to
40 minutes); on the Linux machine it did not change the full tier's time
([below](#before-and-after)).

**The cause**, measured on a summary of `sub_2` in `binary64` of 60 arrays of up to 256 elements
(44.8 MB, 11 strata, each with the map's two entries and the step's `normalized` and `error`):
99.1% of it (44.3 MB) was the profile of (a) of the step's `error` entries, 1 902 distances each
with its case, and the case was the whole map line (23 KB on average: the longest lines set most
of the extremes); the cases of the largest ratio and of (b) took 0.4 MB more, the ratios 0.3 MB,
everything else 25 KB. In the full tier, arrays of up to 1 024 elements, the profile holds up to
some 2 000 distances per stratum, each with a line of up to 150 KB.

**The fix** (`oracle/README.md`, "The size of a summary"): the statistics of a map's step keep
the line of the element of the step that attains them, `STEP FORMAT OPERAND...
#MAP:STRATUM:INDEX:element:I -> OUTPUT...` (a few limbs, which runs again as a line of the step),
and a summary keeps the profile's records only, the distances whose ratio is at least every ratio
at a larger distance, which give (a) for every $F$, value and case, as the whole profile did,
also through merges. The same summary takes 0.11 MB (232 records with their cases, 72 KB, and
the distances seen, 9 KB). What a summary keeps is a fixed set of statistics, each with at most
one case, whose number the claims and the format fix; each case is a line of a kernel or of a
step, or (a fold's or a convolution's own statistics, one per statistic) a fold's line. Equal
ratios are all records, so that the case of (a) stays the whole profile's: a profile whose
ratios are all equal, that of an exact operation (every ratio 0), keeps every distance seen,
which the range of $D$ bounds (some 3 200 values in binary64), not the number of lines. These
are now the largest summaries: 2.0 MB for `two_prod` and 2.7 MB for the map `mul_pow2_map_1` in
the full tier, every other one below 1.2 MB (`oracle/README.md`, "The size of a summary"). The
guards fail a summary above 4 MiB ([What a pass requires](#what-a-pass-requires)), 1.55 times
the largest of the full tier.

**What changed shape**: in a summary, the profile (its records only, and `profile_distances`, the
distances seen) and, for a map, the cases of the step's entries (the element's line, not the
map's); in a report, those cases (`at` under the step's entries of a map), and with `--verbose`
after a merge, the profile's rows (its records). Nothing else: on 215 runs of the old and the new
oracle on the same outputs of the reference runner (every map, fold of maxima and convolution in
`binary64`, `binary32` and a toy format; each of them with the planted faults of stage B; a
quarter of the kernels, the steps, the kernels of the folds of maxima, and kernels and folds with
planted faults; two seeds each, then merged), the exit status and the report were the same, byte
for byte, but for 1 134 lines, each the case of a map's step; every counter, reason, example,
value of a statistic and every other case was the same, and the new profile was the records of the
old; the guards, old and new, decided the same on the old and the new summaries, with the same
output, the new ones failing the 91 old summaries above 4 MiB for their size alone (on 14 runs of
planted faults both crashed alike, on a ratio beyond the range of a float, which the guards now
print); and the brute-force driver's statistics of the merged summaries (`entry_stats`) were the
same but for the cases of the maps' steps.

#### Before and after

Measured on 2026-11-20 on the Linux machine: `main` (`e2edab5`) and the fix (`5d0177b`), one
after the other, each configured with GCC 13 (Ninja, `Release`), both tiers run with
`--parallel 4` on 16 hardware threads (`taskset`); other users loaded the machine (load average
8 to 18), and the oracle's mutants ran on 14 other threads during the fix's tiers and the last
minutes of `main`'s full tier. The oracle's time and memory are those of its `check` alone, on
the output of the first runner of `full.crosscheck.compiled.sub_2.binary64` (1 000 arrays of up
to 1 024 elements), on one thread. MB and GB are $10^6$ and $10^9$ bytes.

| Linux machine, GCC 13 | `main` | The fix |
|---|---|---|
| Quick tier: tests, wall time | 572 passed, 125 s | 572 passed, 127 s |
| Build tree after the quick tier | 334 MB | 210 MB |
| Its summaries: number, total, largest | 410, 144 MB, 2.25 MB (`axpy_2_entry`; 47 above 1 MiB) | 410, 28.4 MB, 0.98 MB (`two_prod_dekker`) |
| Full tier: tests, wall time | 884 passed, 1 906 s | 884 passed, 1 920 s |
| Build tree after the full tier | 41.0 GB | 0.46 GB |
| The full tier's summaries: number, total, largest | 631, 40.5 GB, 1.70 GB (`sub_2`; 17 above 1 GB, 73 above 4 MiB) | 631, 63.7 MB, 2.70 MB (`mul_pow2_map_1`; 5 above 1 MiB) |
| The oracle on `sub_2`'s stream: time, peak memory, summary | 9.5 s, 51 MB, 1.70 GB | 4.8 s, 37 MB, 0.12 MB |

The full tier took as long: its wall time is set by its longest tests (the generator's and the
oracle's pools, the interpreter's enumerations), beside which the machine wrote the 40 GB. Nor
was memory the cost: the old profile held one reference to each map line, which only the JSON
repeated, once per distance. On the Mac with Apple clang 21 (the fix and the change to the guards
after it, under the load of other jobs), the quick tier (571 tests) took 79 seconds and left a
build tree of 219 MB, the full tier (884 tests) 1 180 seconds and a build tree of 476 MB, 92 MB of
it in 1 041 summaries, the largest 2.70 MB; with GCC 16 the quick tier (572 tests) took 97
seconds and left 209 MB.

The old and the new oracle were also compared, as above, at the full tier's size: the maps
`sub_2`, `add_2_entry`, `axpy_2_entry` and `axpy_2_1` and the fold of maxima `norm_upper_2` on
1 000 arrays of up to 1 024 elements, the convolution `conv_2` on 300 pairs of up to 64
coefficients, in binary64, through the reference runner, two seeds each and then merged. The exit
status (0), every counter, statistic and case but those of the maps' steps, the guards' decisions
and output, and the brute-force driver's statistics but the steps' cases were the same; the
reports (18 448 lines) differed in 36 lines, the cases of the maps' steps. The old maps'
summaries took 1.50 to 1.72 GB, the new ones 0.12 to 0.39 MB, and the new guards failed the 8
old ones for their size alone.

## The generator's tier

`python3 gen/kairn-gen test` is the generator's own suite (`gen/README.md`, "The tests"). About
two thirds of its time goes to its C++ tests, which build the generated code at `-O0` and
`-O2`, with and without `-frounding-math`, under every contraction setting, and with both forms of
the scalar fix-ups (inline, and a function of its own: `KAIRN_GEN_FIXUP_CALL`), and require every
build, scalar and packed, to be bit-identical to the interpreter, with special operands in every
lane. It is what sees a change of the listing that keeps every claim: of the 187 planted faults
that neither tier catches, it caught 122, and with the special operands it now adds for eight
kernels (`SPECIAL_CASES`), 139; the other 48 cannot change a result
([What neither tier catches](#time)). The cross-checks build each compiler's own form only. ctest runs it without them (`--no-cxx`): with them it took 148 seconds on its own on the
Linux machine of [Time](#time), and the cross-checks already compile the same code with the build's
compiler and flags. Of the rest, four test classes take about 95% of the time; the full tier runs
them alone (`-k`, `full.kairn-gen.test`) and the others in a test of their own (`--skip`,
`full.tools.kairn-gen.test`, the quick tier's `kairn-gen.test` until it left the quick tier). The
whole suite runs in the workflow `generator.yml`, once per GCC-style compiler of the CI and once
without C++ on Windows: its C++ tests are written for a GCC-style driver (`-O0`, `-ffp-contract=`,
`-frounding-math`, `-fsyntax-only`, `-o`, `-mfma`, and the text of Clang's and GCC's errors), which
neither compiler of the Windows jobs is, and they require every build to be bit-identical to the
interpreter, which MSVC's `/fp:strict` is not for the sign of some zeros
([Cross-checks](#cross-checks)). On Windows the [flag sets](#flag-sets) build the kernels at `/Od`
and `/O1` instead. By hand:

```sh
python3 gen/kairn-gen test                  # c++ and g++-16, those that exist
python3 gen/kairn-gen test --cxx clang++    # another compiler
python3 gen/kairn-gen test --full           # a few hundred thousand cases per kernel
python3 gen/kairn-gen test --no-cxx --skip test_statements.   # without C++, without a module
python3 gen/kairn-gen test --shard 1/2      # every second test: the two shards are the suite
python3 gen/kairn-gen test --durations 20   # and the 20 slowest tests with their times
```

**The maps, and their steps, are tested here too** (the oracle judges them since stage B,
[above](#cross-checks)).
`gen/tests/test_maps.py` checks the rules of a map; that the interpreter writes the step of each
element, the same elements and mask in both orders for every number of lanes, the canonical NaN
for an element that is not finite and keeps the others; the compiled `F_seq`, `F_lanes` (0 to 8
lanes) and `F_packed` of every build bit for bit against the interpreter, on the lengths of the
folds, with non-finite elements; every map in place (the array written being one of those read,
with each form, at `-O0` and `-O2` with each compiler); and rule R3 on a supplied `y` of `add`,
`sub` and `axpy`, the maps of stored arrays as the control (fused under `-ffp-contract=fast` by
Apple clang and GCC 16 on the Mac, and GCC 13 and Clang 18 on x86-64).

**The statements of the maps and the convolutions in the IEEE model**
([Architecture](architecture.md#maps-and-convolutions-in-the-ieee-model)), which no proof
establishes yet, are read against the code by `gen/tests/test_ieee_writers.py` before anyone tries
to prove them: the interpreter on formats of the IEEE shape of two to five bits whose largest number
is below $2^{p+3}$, so that overflows are frequent, and in `binary64` and `binary32`, on canonical
scalars and elements with infinities, NaN and numbers near the top among them, in the sequential
order and with 0 to 4 lanes; every element written (every coefficient), every limb and the mask
against the statement, the claims of the step in exact arithmetic with the exponent range widened;
the lead statement of the step of every map on operands of any value; and every build of the
runner on the same requests in `binary64` and `binary32`. No case contradicts a statement.

**The ball vectors** ([Architecture](architecture.md#ball-vectors)), which the oracle also judges
([Cross-checks](#cross-checks); `oracle/README.md`, "Their folds"), are tested here by
`gen/tests/test_bv.py`: each check of `rules.bv_rules` refuses what it is for; the
interpreter, on formats of the IEEE shape of two to five bits and in `binary64` and `binary32`, on
canonical BallVectors with the whole space among them and any value of a scalar that is not a
radius, in the sequential order and with 0 to 4 lanes, satisfies V1 to V4 and the flag in exact
arithmetic (containment entry by entry against the exact range of the operation on the balls; V4 of
every length, and of the vector with no entry with its radii on each side of the limit of
`radii_when`, which the conditions of an entry imply), every order the same; on finite operands the one radius equals the largest radius the entrywise Ball kernel
returns, in every case compared; the scalings by a power of two, `bv_mul_pow2_k`, are exactly the set,
their radius exactly $c\,r_x$, in every case where their conditions of `exact_when` hold, and a BallVector
halved sixty times in a row keeps a radius of exactly $r_x/2^i$ (where `bv_scale_k` by $\tfrac12$ grows
it), and gets the second number after the halved radius once a center falls below the smallest normal
number; the compiled `F_seq`, `F_lanes` (0 to 8 lanes) and `F_packed` of
every build are bit for bit the interpreter's, on the lengths of the folds; the line protocol, the
printers, the counts of the loops and the claims (with the entries of architecture.md). The same file
tests the constructors (`makes_ball_vector` on every small case and at random, every order), the
negations (exactness), and `bv_norm_upper_k` as the header writes it, `norm_upper_k` then `add_up_1`
of the radius: every member at most the bound, the bound at most one rounding up above the claims of
the two calls, in exact arithmetic. And the request form `inplace=I` of the line protocol: every map
and every ball vector, with each array read that can be the array written, through every build of
the runner and of the packed runner, completes exactly as the same request without the field.

**The products of two BallVectors** `bv_conv_1` and `bv_conv_2` ([Architecture](architecture.md#ball-vectors)),
which the oracle judges too (and `conv_radius` since the ruling of 2026-11-21, [Cross-checks](#cross-checks)),
are tested by `gen/tests/test_bv_conv.py`: each check of
`rules.bv_conv_rules` refuses what it is for, and the rules of the claims refuse `at_most` and `if_all`
where they do not belong; the interpreter, on six formats of the IEEE shape of four to six bits
(precision 4 to 6, $e_{\max}$ 7 to 14) and in `binary64` and `binary32`, on canonical BallVectors of
lengths 0 to 4 with the whole space among them, satisfies V1 to V4 and the flag in exact arithmetic
(containment coefficient by coefficient against the exact range of the sum of the products, each
entry ranging independently over its ball; the coefficients those of `conv_k`); and on cases drawn at
the limits of the conditions of V4 (entries and radii near the bound of each condition, a quarter of
them with $n_x = 0$ and a quarter with $n_y = 0$), V4 holds; the count rounded up is the least number of
the format at least $n$; `count_when` gives the bound, for every $n$ within it (up to 3 000 of them) in 36
formats of precisions 4 to 9; an empty operand with a radius whose product with the other's maximum
overflows gives the whole space, and does not meet the condition of V4 of that array. The compiled
`F_seq` of every build is bit for bit the interpreter's, in `binary64` and `binary32`, on every pair of
lengths 0 to 5, on longer operands (up to 60, and a few of up to 300 entries, 2 000 in the full tier) and
on cases near the limits of V4; the line protocol, through the interpreter and the runner; the printers
(the C++, the counts of the loops, the claims with the entries of architecture.md, the models and the
statements).

**The folds, and the kernels of their stage**, are cross-checked by the oracle like every kernel
([above](#cross-checks)), and tested here too. `gen/tests/test_folds.py` checks:

- the rules: the folds of `gen/kernels` are accepted, and each check of a fold refuses what it is
  for (shapes, names, the zero state, rule R3 on a supplied array, the claims, `eps` against the
  combination's bound); property 3 of the zero state on every normalized pair of three small
  formats;
- the interpreter: the lane order is its definition in `proofs/theories/Folds.v`, written again
  in the test (deal, fold each lane, combine from lane 0, the remainder), for several widths; a
  list shorter than the lanes, one lane and none give the sequential order; the empty list gives
  the zero state with the flag true; an infinite or NaN element, or an overflow, gives the
  canonical NaN with the flag false; every fold in both orders, on toy formats of precision 3 to
  6, holds its claims in exact arithmetic (`fold_error` with the heights of the order, validity,
  the flag), more than 10 000 cases, with the exponent range widened as the Rocq statements are
  and in the format itself; the line protocol of arrays;
- the compiled C++: `F_seq` and `F_lanes` of every build of the runner (the matrix above) are bit
  for bit the interpreter's, on the lengths 0, 1, $W - 1$, $W$, $W + 1$, $2W$ for every packed
  width ($W$ = 2, 4, 8) and random lengths up to a few thousand (`--full`: twenty thousand), with
  non-finite elements in some, in the sequential order and with 0, 1, 2, 3, 4 and 8 lanes; `F_packed` of every
  packed build prints what `F_lanes` with its register's lanes prints, and the packed runner
  refuses another width;
- rule R3 on a supplied array: a program that writes `a * b + c` into the array of a sum, built
  at `-O2` with each contraction setting and every compiler, gets from the `_entry` folds the sum
  of the rounded products in every case; the folds of stored arrays, whose steps do not guard,
  are the control, and must differ in some case where a compiler fuses (GCC and Apple clang with
  `-ffp-contract=fast`, measured);
- the printers: the model, the statements and the audit of a fold made `proved`, the C++ text and
  the counts of the loops;
- the folds of maxima, `norm_upper_1` and `norm_upper_2` ([Architecture](architecture.md#folds-of-maxima)),
  which the oracle also judges since stage B ([Cross-checks](#cross-checks)),
  in all of the above but the claims of `fold_error`, and on their own: each check of
  `rules.max_rules` refuses what it is for (a combination that claims a maximum and computes
  something else is refused by evaluation, as not commutative); no element gives $0$ for one limb
  and $\eta$ for two, with the flag true; a NaN or infinite element at any position, in every
  order, the canonical NaN and the flag false, and so does a leading limb of $\Omega$ for two
  limbs; and the claim `upper r max steps=S` in exact arithmetic on toy formats of precision 1 to
  6, in both orders and several numbers of lanes, more than 10 000 cases, with the exponent range
  widened (the Rocq statement) and in the format itself (the flag);
- the convolutions, `conv_1` and `conv_2` ([Architecture](architecture.md#convolutions)), which
  the oracle also judges since stage B, in `gen/tests/test_conv.py`: each check of `rules.conv_rules` refuses what it is for; in the
  interpreter every coefficient is the fold of its coefficients run on its own terms, there are
  $n_x + n_y - 1$ of them (none for an empty array), a term that is not finite makes the
  coefficients it is in the canonical NaN and the mask false and keeps the others; on toy formats
  of precision 3 to 6, in exact arithmetic, every coefficient is within the bound of `dot` for its
  own number of terms, with the exponent range widened and in the format itself; the compiled
  `F_seq` of every build of the runner is bit for bit the interpreter's on every pair of lengths up
  to 5 and random ones up to a few hundred, non-finite terms in some; the line protocol with two
  lengths; and `conv_terms` of the Rocq model, written in Python as the model writes it, is the list
  of the terms of coefficient $j$ for every pair of lengths up to 7.

The kernels of the stage (the steps, the finishes, the bounds) are in the suite's other tests like
every kernel: the interpreter against the host, the claims in exact arithmetic on toy formats
(`test_statements.py`; `upper` with its own value, `holds`, the form `T`, `maximum`), the
non-finite reading of the finishes (`test_nonfinite.py`, the finishes of the folds of maxima with
both values of their mask), the compiled runners bit for bit, and the self-test.
## A cross-check by hand

From the repository root, a toy format with the interpreter, and binary64 with a compiled runner
from a build tree:

```sh
python3 oracle/kairn-oracle gen mul_2_2 fp:4:-7:-3 --exhaustive \
  | python3 gen/kairn-gen interp | python3 oracle/kairn-oracle check

python3 oracle/kairn-oracle gen mul_2_2 binary64 --seed 0 --count 20000 \
  | build/tests/kairn-gen-runner | python3 oracle/kairn-oracle check --fail-on-suspicious
```

The packed runner is `build/tests/kairn-gen-packed-runner`, and a restricted enumeration adds
`--restrict` to `gen`, as the test's report shows:

```sh
python3 oracle/kairn-oracle gen ball_mul_2 fp:4:-5:1 --exhaustive \
  --restrict rx.in=0x0p+0/0x1p-5/0x1.8p+0 --restrict ry.in=0x0p+0/0x1p-5/0x1.8p+0 \
  --restrict cx.lead=0:0 --restrict cy.lead=-3:0 \
  | python3 gen/kairn-gen interp | python3 oracle/kairn-oracle check
```

`check` exits with 1 on any violated claim or broken stream (with `--fail-on-suspicious`, on a
suspicious non-finite result; with `--expect-valid`, on an invalid case), and its report lists
the worst cases with their tags. `--verbose` adds the profile of the error by distance from the
underflow range; `--json FILE` writes everything, which `tests/crosscheck_guards.py` reads. A toy
format below a kernel's minimum precision is not judged unless `check` is given
`--ignore-min-precision`.

A test's whole cross-check, every runner and the guards, as ctest runs it in one process
(`ctest -V -R NAME` prints its command):

```sh
python3 tests/crosscheck.py compiled --kernel mul_2_2 --format binary64 --seed 0 --count 6000 \
  --fail-on-suspicious --summary build/by-hand/mul_2_2.json \
  --runner cxx build/tests/kairn-gen-runner --runner packed build/tests/kairn-gen-packed-runner

python3 tests/crosscheck.py api --kernel mul_2_2 --format binary64 --seed 1 --count 2000 \
  --summary-dir build/by-hand --runner build build/tests/api/kairn-api-runner
```

The first writes the oracle's summary of each distinct output next to `--summary`, named with
the label of the first runner that wrote it, the second `K.F.LABEL.FORM.json` in `--summary-dir`;
`--interp` adds the generator's interpreter as one more runner, and `--exhaustive` with
`--restrict` an enumeration, as for `gen`.

### Against other claims

The tests judge against `gen/claims.json` unless the CMake variable `KAIRN_ORACLE_CLAIMS` names
another file of the same form. `tests/CMakeLists.txt` and `tests/api/CMakeLists.txt` then read the
kernels and folds they register tests for from that file, and every test that runs the oracle
passes it on: `--claims FILE` to `tests/crosscheck.py` (both modes), `tests/regression/run.py`,
`tests/lanes/lane_fault.py` (`crosscheck.lanes.fault.F`, which gives it to its cross-checks and to
the requests of its run under the guard), the oracle's `check --claims-only`
(`kairn-oracle.claims`) and `search` (`full.search.compiled`);
`-DCLAIMS=FILE` to `tests/crosscheck.cmake`; and the environment variable `KAIRN_ORACLE_CLAIMS` to
`tests/test_crosscheck_guards.py` (`full.tools.crosscheck.guards.*`), which passes it to every run
of the oracle and of the drivers. It is for a branch of the oracle that reads only some of the
claims of `gen/claims.json` (the oracle fails every run while the claims hold anything it cannot
read): its tiers run against a copy of the claims without the objects it does not read yet, which
are then simply absent, and the objects it does read are judged as they will be against the whole
file.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DKAIRN_ORACLE_CLAIMS=/path/to/claims.json
KAIRN_ORACLE_CLAIMS=/path/to/claims.json python3 tests/test_crosscheck_guards.py
```

## Rerunning one case

Every request line carries a tag, copied by the runner, that says which case it is:
`#STRATUM:INDEX` for random cases and `#exhaustive:INDEX` for an enumeration. Case INDEX is
computed from the kernel, format, seed and index alone, so `--start INDEX --count 1` with the same
arguments regenerates it and nothing else. For the line

```
add_2_2 binary64 0x1.0000082p-333 -0x1p-387 0x1.ffffffffffffep+1023 0x1p+970 #extreme:462 -> ...
```

of a test run with seed 0:

```sh
python3 oracle/kairn-oracle gen add_2_2 binary64 --seed 0 --start 462 --count 1 \
  | build/tests/kairn-gen-runner | python3 oracle/kairn-oracle check --fail-on-suspicious
```

and for an exhaustive case, `--exhaustive --start INDEX --count 1` (with the same restrictions,
if any). A failing cross-check of the compiled runners prints this command with its own runner and
arguments filled in, and one of the public interface with `RUNNER --form F` for the runner, the
list of its runners, and the forms that failed; both keep the work directory with the requests and
the outputs that failed, and say where it is.
The request line alone is also a valid input: `echo 'add_2_2 binary64 ... #extreme:462' |
build/tests/kairn-gen-runner` shows the result without the oracle, and `python3 gen/kairn-gen
interp` the exact one. The packed runner evaluates a lone line in every lane.

## The adversarial search

The cross-checks and the brute-force tier draw their cases at random from strata; how close a
claim came then depends on what the draws met. `python3 oracle/kairn-oracle search` looks for
the cases that bring a kernel closest to its claims, or past them: for a kernel and a format it
evolves a population of cases through a runner (the interpreter by default, any compiled runner
too) and judges every completed line with the oracle's own checker, keeping the best cases for
each quantity a claim bounds (the error over its bound and the observed constant for `error`, the
excess in gaps for `upper`, the smallest slack of the radius for `encloses`). Its moves are those
of floating-point operands (bits of a significand, units in the last place, extreme significands,
second limbs at the edges of the normalization invariant, exponents, signs, swaps, ties,
cancellation, the underflow and overflow thresholds); every case stays inside the kernel's
requirements; its seeds are the attaining lines of the stored brute-force runs, the regression
cases, the operands the literature gives for the double-word algorithms (`oracle/kairn_oracle/tight.py`,
transcribed with the page) and cases of every stratum. It is deterministic, and a case it reports
is an ordinary line that `check` judges alike (`oracle/README.md`, "search").

**What it found** in Milestone 1. Each kernel with an `error`, `upper`, `encloses` or `extends`
entry, in `binary64` and `binary32`, got 20 000 cases (seed 0), seeds included, through the
interpreter on the Mac: 94 searches in 141 seconds with six worker processes, 825 seconds of
process time. Through the scalar runner of an Apple clang build instead, the 94 searches gave the
same values case for case, in 26 seconds. Its seeds were the brute-force lines, the literature and
the strata (the regression cases came after, from this run). A second run started from the strata
alone, to see what the search adds by itself. **No claim was violated.** The table compares the extreme of each quantity with that of the brute-force runs of
[Brute force, Milestone 1](results/brute-milestone1.md) (13.8 billion results of the compiled
runners, recomputed exactly from their attaining lines): bold where the search came closer to the
claim, ↓ where it stayed farther. Exact claims ($c = 0$, $t = 0$) are left out: the search has
nothing to climb there and found no inexact result.

| Kernel | Quantity | `binary64` brute force | from the strata | with every seed | `binary32` brute force | from the strata | with every seed |
|---|---|---|---|---|---|---|---|
| `add_1_1` | observed c | 1 − 1.1·10<sup>-16</sup> | 1 − 1.1·10<sup>-16</sup> | 1 − 1.1·10<sup>-16</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> |
| `add_1_1` | error / bound | 1 | 1 | 1 | 1 | 1 | 1 |
| `add_2_1` | observed c | 1.9663 | 1 − 5.6·10<sup>-17</sup> ↓ | **2 − 4.4·10<sup>-16</sup>** | 1.9754 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `add_2_1` | error / bound | 0.9832 | 0.5 ↓ | **1 − 2.2·10<sup>-16</sup>** | 0.9877 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `add_2_1_full` | core's observed c | 1.9684 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.9693 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `add_2_1_full` | core's error / bound | 0.9842 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9846 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `add_2_2` | observed c | 1.9966 | **2.5** | **3 − 1.1·10<sup>-15</sup>** | 2.0668 | **2.25** | **3 − 6.0·10<sup>-7</sup>** |
| `add_2_2` | error / bound | 0.6655 | **0.8333** | **1 − 8.1·10<sup>-16</sup>** | 0.6889 | **0.75** | **1 − 4.4·10<sup>-7</sup>** |
| `add_2_2_full` | core's observed c | 2 − 4.4·10<sup>-16</sup> | **2.5** | **3 − 1.1·10<sup>-15</sup>** | 2.1541 | **2.5** | **3 − 6.0·10<sup>-7</sup>** |
| `add_2_2_full` | core's error / bound | 0.6667 | **0.8333** | **1 − 8.1·10<sup>-16</sup>** | 0.718 | **0.8333** | **1 − 4.4·10<sup>-7</sup>** |
| `add_fast_2_2` | observed c | 2.2284 | 2.1693 ↓ | **2.8717** | 1.7874 | **2.8212** | **3 − 1.3·10<sup>-6</sup>** |
| `add_fast_2_2` | error / bound | 0.7428 | 0.7231 ↓ | **0.9577** | 0.5958 | **0.9404** | **1 − 4.4·10<sup>-7</sup>** |
| `add_fast_2_2_full` | core's observed c | 1.5711 | **2.2964** | **2.3628** | 2.2991 | **3 − 1.3·10<sup>-6</sup>** | **2.7641** |
| `add_fast_2_2_full` | core's error / bound | 0.5237 | **0.7655** | **0.7876** | 0.7664 | **1 − 4.4·10<sup>-7</sup>** | **0.9214** |
| `ball_add_1` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1 | 1 |
| `ball_add_1_full` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1.125 ↓ | 1 |
| `ball_add_2` | slack, gaps | 1.2524 | **1.1758** | **1.1719** | 1.2501 | **1.1563** | **1.125** |
| `ball_add_2_full` | slack, gaps | 1.2589 | **1.1602** | **1.1719** | 1.2501 | **1.1094** | **1.1582** |
| `ball_mul_1` | slack, gaps | 1.5581 | **1.5001** | **1.5037** | 1.5353 | **1.5001** | **1.5** |
| `ball_mul_1_full` | slack, gaps | 1.5987 | **1.5** | **1.5061** | 1.5907 | **1.508** | **1.5** |
| `ball_mul_2` | slack, gaps | 2.5041 | **2.4965** | **2.4915** | 2.5015 | 2.5327 ↓ | **2.4618** |
| `ball_mul_2_full` | slack, gaps | 2.5 | **2.4482** | **2.4421** | 2.5608 | **2.5** | **2.5** |
| `ball_scale_1` | slack, gaps | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 1.2·10<sup>-7</sup> | 1.25 ↓ | 1 + 1.2·10<sup>-7</sup> |
| `ball_scale_1_full` | slack, gaps | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 2.2·10<sup>-16</sup> | 1 + 1.2·10<sup>-7</sup> | 1 + 1.2·10<sup>-7</sup> | 1 + 1.2·10<sup>-7</sup> |
| `ball_scale_2` | slack, gaps | 1.375 | **1.25** | **1.25** | 1.375 | **1.2501** | 1.375 |
| `ball_scale_2_full` | slack, gaps | 1.329 | 1.5 ↓ | **1.2511** | 1.375 | **1.2512** | **1.2534** |
| `ball_sub_1` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1 | 1 |
| `ball_sub_1_full` | slack, gaps | 1 | 1.125 ↓ | 1 | 1 | 1.125 ↓ | 1 |
| `ball_sub_2` | slack, gaps | 1.2511 | **1.2109** | **1.1564** | 1.25 | **1.1563** | **1.1563** |
| `ball_sub_2_full` | slack, gaps | 1.2509 | **1.1602** | **1.1582** | 1.2513 | **1.1719** | **1.1719** |
| `mul_1_1` | observed c | 1 − 3.3·10<sup>-16</sup> | 1 − 3.3·10<sup>-16</sup> | 1 − 3.3·10<sup>-16</sup> | 1 − 1.8·10<sup>-7</sup> | 1 − 1.8·10<sup>-7</sup> | 1 − 1.8·10<sup>-7</sup> |
| `mul_1_1` | error / bound | 1 − 1.1·10<sup>-16</sup> | 1 − 2.2·10<sup>-16</sup> ↓ | 1 − 1.1·10<sup>-16</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> | 1 − 6.0·10<sup>-8</sup> |
| `mul_2_1` | observed c | 1.9533 | 1.6 ↓ | **1.9956** | 1.9105 | 1.8925 ↓ | **1.9697** |
| `mul_2_1` | error / bound | 1 − 2.2·10<sup>-16</sup> | 0.9908 ↓ | **1 − 1.7·10<sup>-16</sup>** | 1 − 1.5·10<sup>-7</sup> | 0.9998 ↓ | **1 − 8.9·10<sup>-8</sup>** |
| `mul_2_1_full` | core's observed c | 1.9561 | 1.9026 ↓ | **1.9956** | 1.9122 | 1.648 ↓ | **1.9697** |
| `mul_2_1_full` | core's error / bound | 1 − 2.8·10<sup>-16</sup> | 0.995 ↓ | **1 − 1.7·10<sup>-16</sup>** | 1 − 2.1·10<sup>-7</sup> | 1 − 4.2·10<sup>-6</sup> ↓ | **1 − 1.2·10<sup>-7</sup>** |
| `mul_2_2` | observed c | 3.3361 | **3.9959** | **4 − 3.5·10<sup>-8</sup>** | 3.4428 | **3.4993** | **3.5392** |
| `mul_2_2` | error / bound | 0.9772 | **0.999** | **1 − 8.7·10<sup>-9</sup>** | 0.9738 | **0.9939** | **0.9961** |
| `mul_2_2_full` | core's observed c | 3.4873 | 3.1298 ↓ | **4 − 1.3·10<sup>-8</sup>** | 3.4886 | 2.8815 ↓ | 3.4886 |
| `mul_2_2_full` | core's error / bound | 0.9809 | 0.9765 ↓ | **1 − 3.1·10<sup>-9</sup>** | 0.9689 | **0.9963** | **0.999** |
| `mul_pow2_2` | error / bound | 0.7385 | **0.75** | **0.75** | 0.75 | 0.75 | 0.75 |
| `mul_pow2_2_full` | core's error / bound | 0.7489 | 0.7422 ↓ | **0.75** | 0.75 | 0.75 | 0.75 |
| `radd` | excess, gaps | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `rmul` | excess, gaps | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| `sub_1_2` | observed c | 1.6201 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.7841 | **2 − 6.0·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_1_2` | error / bound | 0.81 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.8921 | **1 − 3.0·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_1_2_full` | core's observed c | 1.6244 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.7425 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_1_2_full` | core's error / bound | 0.8122 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9167 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_1` | observed c | 1.9947 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.9724 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_2_1` | error / bound | 0.9974 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9862 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_1_full` | core's observed c | 1.8264 | **2 − 4.4·10<sup>-16</sup>** | **2 − 4.4·10<sup>-16</sup>** | 1.8864 | **2 − 2.4·10<sup>-7</sup>** | **2 − 2.4·10<sup>-7</sup>** |
| `sub_2_1_full` | core's error / bound | 0.9132 | **1 − 2.2·10<sup>-16</sup>** | **1 − 2.2·10<sup>-16</sup>** | 0.9432 | **1 − 1.2·10<sup>-7</sup>** | **1 − 1.2·10<sup>-7</sup>** |
| `sub_2_2` | observed c | 2.1094 | 1.5 ↓ | **3 − 1.1·10<sup>-15</sup>** | 2.2401 | **2.5** | **3 − 6.0·10<sup>-7</sup>** |
| `sub_2_2` | error / bound | 0.7031 | 0.5 ↓ | **1 − 8.1·10<sup>-16</sup>** | 0.7467 | **0.8333** | **1 − 4.4·10<sup>-7</sup>** |
| `sub_2_2_full` | core's observed c | 2 − 4.4·10<sup>-16</sup> | **2.0046** | **3 − 1.1·10<sup>-15</sup>** | 2 − 2.4·10<sup>-7</sup> | **2 − 2.4·10<sup>-7</sup>** | **3 − 6.0·10<sup>-7</sup>** |
| `sub_2_2_full` | core's error / bound | 0.6667 | **0.6682** | **1 − 8.1·10<sup>-16</sup>** | 0.6667 | **0.6667** | **1 − 4.4·10<sup>-7</sup>** |
| `two_prod` | error / bound | 1 | 1 | 1 | 1 | 1 | 1 |
| `two_prod_dekker` | error / bound | 0.9239 | 0.885 ↓ | **0.9696** | 0.9259 | 0.9056 ↓ | **0.9687** |

Over the 116 quantities, the search with every seed came closer to the claim on 86 and as close
on 30; from the strata alone, closer on 66, as close on 20 and farther on 30 (it missed, for
example, the structured case of `add_2_1` in `binary64`, which it found for `sub_2_1`, `sub_1_2`
and the core of `add_2_1_full`, and the corner of the underflow range where the brute-force runs
had met the bound of `mul_2_1`). What it brought closest:

- **The accurate sum** (`add_2_2`, `sub_2_2`, the cores of their full kernels) comes within
  $8.1 \cdot 10^{-16}$ of its bound $3u^2/(1 - 4u)$ in `binary64` and $4.4 \cdot 10^{-7}$ in
  `binary32`, with an observed constant of $3 - \epsilon$; the brute-force runs had found 2.0 to
  2.24, 0.67 to 0.75 of the bound. The case is the one with which
  [MR22](design/phase0/references.md#mr22) prove the bound asymptotically optimal (Property
  2.1, which they say random testing cannot find); from the strata alone the search reached 2.25
  to 2.5, but 1.5 for `sub_2_2` in `binary64`.
- **The sums with one limb** (`add_2_1`, `sub_2_1`, `sub_1_2` and their cores) come within
  $2.2 \cdot 10^{-16}$ and $1.2 \cdot 10^{-7}$ of $2u^2$, found from the strata (but for `add_2_1`
  in `binary64`) as well as from [JMP17](design/phase0/references.md#jmp17)'s case of DWPlusFP;
  before, 0.81 to 0.997.
- **The double-word product** `mul_2_2` comes within $8.7 \cdot 10^{-9}$ of $4u^2 + \tfrac32\eta$
  in `binary64`, with an observed constant of $4 - 3.5 \cdot 10^{-8}$ (3.34 in the brute-force
  runs; the case MR22 give for their Theorem 2.8 has 3.997, which the search carried further); in
  `binary32` 0.996 and 3.54.
- **The fast sum** `add_fast_2_2` comes within $4.4 \cdot 10^{-7}$ of its bound of form A in
  `binary32` (0.60 before), from a brute-force line, and the core of `add_fast_2_2_full` from the
  strata alone: the bound $3u^2(\lvert x\rvert + \lvert y\rvert)$ proved for Kairn is attained.
- **The radii** of the two-limb Ball sums keep 1.11 to 1.18 gaps of slack at the closest
  (1.25 before), those of the one-limb product 1.5 (1.54 to 1.60), of the two-limb scaling 1.25
  (1.33 to 1.375) and of the two-limb product 2.44 to 2.5 (2.5 to 2.56); those of the one-limb
  sums and scaling stay at one gap, as before.
- `two_prod_dekker` comes to 0.97 of its bound near underflow (0.92 before) and `mul_pow2_2` to
  0.75 in `binary64` (0.74).

**A longer run**, on the Linux machine: 1 000 000 cases per kernel and format (94 million in all,
seed 0, batches of 1 024) through the scalar runner of a GCC 13 build, 48 processes, 405 seconds,
starting from the regression cases below. No claim was violated. It came closer still on 42 of the
116 quantities: `mul_2_2` and the core of `mul_2_2_full` to within $1.9 \cdot 10^{-15}$ of their
bound in `binary64`, with an observed constant of $4 - \epsilon$ (from a case of the stratum
`pow2`, not from the literature), and in `binary32` to 0.998 (`mul_2_2`) and $1 - 1.9 \cdot
10^{-7}$ (the core of `mul_2_2_full`); `add_fast_2_2` and its core to within $8.1 \cdot 10^{-16}$
in `binary64` (0.96 at 20 000 cases); `two_prod_dekker` to 0.992 and 0.986; and the smallest
slack of the two-limb Ball
radii to 1.11 to 1.16 gaps for the sums, 1.25 for the scaling and 2.20 for the product in
`binary64`. Its best lines replaced those of the shorter run in the regression cases where they
came closer.

**What it did not find.** A search climbs the quantities of the claims, and a fault that breaks a
claim only where the correct kernel is far from its bound gives it nothing to climb. Of the
planted faults of `tests/kernel_mutants.py` that the full tier catches and the quick tier misses,
it found the loosened finiteness test of `add_fast_2_2_full` after 9 025 cases of `binary64`
(the full tier's random cases meet it at case 9 280), and missed the FMA of `ball_scale_2`
computed as a product and a sum in 100 000 cases per format: that fault breaks the radius where
the input radius is zero and the center's error is near its bound, where the correct kernel's
slack is large, and the full tier's 20 000 random cases met it once or twice. The search is a
complement to the random tiers, not a replacement.

**Where it runs.** By hand, as above, with any runner; and in the full tier,
`full.search.compiled`: every kernel, both formats, 5 000 cases each through the scalar runner of
the build, four worker processes; 10 seconds on the Mac, 16 on the Linux machine (GCC 13 and Clang
18 alike) and 27 to 33 on the Windows machine. Its seeds then include the regression cases, so it
starts from the closest cases known.

### The shrinker

A failing case found anywhere is first made as simple as it can be:
`python3 oracle/kairn-oracle shrink 'LINE' --runner RUNNER` keeps the failure of the same `ensures`
entry (in the extended domain, the same statement), as the oracle judges it, while it replaces
operands by zero or powers of two, cuts significands, moves exponents toward zero, and looks for
the smallest toy format in which the same runner fails the same way (the interpreter runs every
format; a compiled runner `binary64` and `binary32` only). It is deterministic, ends, and prints
the shrunk line with the command that reruns it (`oracle/README.md`, "shrink"). On the planted
faults of the oracle's self-tests it takes, for example, a `binary64` case of `mul_2_2` with the
cross term dropped from 195 significant bits to $1 \cdot (1 + 2^{-53})$, and to a case of
`fp:5:-5:-2`; through a compiled runner with a planted fault of `add_fast_2_2_full`, the line the
search found to $(-\Omega, -2^{969}) + (-2^{969}, 0)$, whose result $(-\infty, +\infty)$ is not
canonical.

### The regression cases

`tests/regression/cases.txt` holds request lines that the quick tier runs through every runner it
builds (`regression.cases`): the cases that found a problem in Milestone 1, as far as the
repository records them with operands (the operands that the planted faults of
`tests/kernel_mutants.py` showed no test supplied, which the generator's comparison now has in
`SPECIAL_CASES`, where they are in their kernel's domain; the corner where TwoSum's error term
overflows); the operands of the literature; the attaining lines of the brute-force runs for every
claim that came within 2% of its bound; and the search's best lines where it came at least as
close as the brute-force runs. Each line has a comment: where it came from and what it showed.
The rule for adding one is at the top of the file: a failure is shrunk, and goes in with where it
was found, the entry it failed, and the class of the fault (statement, generator, code, compiler or
hardware). A case the line protocol cannot carry has a test of its own, named there: the product
of the program fused into a kernel is `api.boundary.*`. Every line of `binary64` and `binary32`
runs through every compiled runner and through every form of the public interface that calls its
kernel, and every line, toy formats included, through the interpreter; the oracle judges each
result as in the cross-checks. 185 lines today (16 from the history, 38 of the literature, 62 of
the brute-force runs, 69 of the two searches); in the quick tier's run, 0.5 to 1.1 seconds on the Mac,
1.1 on the Linux machine and 2.6 to 6 on the Windows machine, where starting a process costs most (one
run of each compiled runner, of the interpreter, and of each runner of the public interface per
name of a form).

## Continuous integration

Six workflows under `.github/workflows/`, one run per branch at a time (a new push cancels the run
in progress). Five run on pushes to `main` and on pull requests, and their jobs all start at once;
the sixth, `nightly.yml`, runs every night, by hand, and on a pull request that changes it or its
driver:

| Workflow | Jobs |
|---|---|
| `build.yml`, "Build and test" | The quick tier: configure, build and `ctest` with Ninja, `Release` and warnings as errors, on Linux x86-64 with GCC and with Clang (packed: AVX2), Linux arm64 with GCC and with Clang (NEON), macOS arm64 with Apple clang (NEON), and Windows x64 with MSVC and with clang-cl (AVX2) |
| `full.yml`, "Full tier" | The full tier's tests that depend on the compiler, and the tools' own tests but the generator's (`ctest --test-dir build/tests/full` with `-LE` of the labels `python` and `generator`: the compiled runners' cross-checks and the public interface on more cases, the [flag sets](#flag-sets), the object code on the whole flag matrix, the adversarial search, and the tests labelled `tools`), on the same seven platforms and compilers, configured and built as in `build.yml`; and those in exact arithmetic (`-L python`), once, on Linux, configured but not built, in two jobs: the interpreter's enumerations (`-L interp`) and the oracle's (`-L python -LE interp`) |
| `generator.yml`, "Generator's full suite" | `python gen/kairn-gen test --cxx CXX`, C++ included, on Linux x86-64 and Linux arm64 with GCC and with Clang, and macOS arm64 with Apple clang, there as two jobs of every second test (`--shard 1/2`, `--shard 2/2`: as one job it took 58 of its 60 minutes on the hosted runner at the end of Milestone 2, and was cancelled once); and `--no-cxx` on Windows x64. It contains the full tier's `full.kairn-gen.test` and `full.tools.kairn-gen.test` (label `generator`), which `full.yml` leaves out |
| `proofs.yml`, "Proofs" | `make -C proofs` in the Rocq team's image `rocq/rocq-prover:9.0` (Rocq 9.0.1), with Flocq 4.2.2 from opam, cached between runs; what the audit printed is kept as the run's artifact `proof-audit` |
| `checks.yml`, "Generated files and documentation" | `gen/kairn-gen check`, `docs/tools/reference.py --check` and its tests, `mkdocs build --strict`, Doxygen 1.18.0 on `docs/Doxyfile` with warnings as errors into the site's `api/`, `docs/tools/check_links.py`; the built site is kept as the run's artifact `site`, and on a push to `main` published at <https://danielepanozzo.github.io/kairn/> |
| `nightly.yml`, "Nightly brute force" | Every night, not on a push: `tests/brute/brute.py` for 100 minutes per job on Linux x86-64 and arm64 (GCC and Clang), macOS arm64 (Apple clang) and Windows x64 (MSVC and clang-cl), every kernel on new random cases (the seed is the number of the run) through every runner of the quick tier, and one job that enumerates one fortieth of the toy-format domains of the plan, a different one each night; each job fails on a violated claim or a failed guard and keeps its summary as an artifact. A pull request that changes the workflow or the driver runs it for a few minutes on a few kernels |

Every test of the full tier thus runs on every push and pull request: a test that depends on the
compiler with every compiler, a test in exact arithmetic once, and the generator's tests, which
compare the interpreter with the machine's arithmetic (Python's float and `math.fma`), once on each
operating system and processor of the CI (x86-64 Linux, arm64 Linux, arm64 macOS, x86-64 Windows).
The tools' own tests run where they ran when they were in the quick tier: the oracle's, the
guards', the reference script's and the brute-force driver's in each job of `full.yml` that
builds, on every platform and compiler; the generator's, which compiles nothing, on every operating
system and processor, in `generator.yml`, which ran it already inside the whole suite. The tests
of the reference script also run in `checks.yml`, beside the pages they test, as before: they take
seconds there, and that job is the one that reports on the documentation.
