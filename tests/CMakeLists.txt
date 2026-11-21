# Kairn's tests, registered with ctest when KAIRN_BUILD_TESTS is on, in two tiers
# (docs/developer/testing.md); add -C CONFIG for a multi-config generator:
#
#   ctest --test-dir build --output-on-failure               the quick tier
#   ctest --test-dir build/tests/full --output-on-failure    the full tier
#
# The quick tier is the tests of this directory and of api/: the library, with this build's
# compiler and flags. The full tier is what left it to keep it quick: the same cross-checks on more
# cases, the interpreter's enumerations of toy formats, and the tools' own tests (the generator's,
# the oracle's, those of the cross-checks' guards, of the script of the reference pages and of the
# brute-force driver). Its tests are registered in full/ and named full.*; the file
# CTestCustom.cmake written at the top of the build tree leaves them out of a ctest run there
# (CTEST_CUSTOM_TESTS_IGNORE), and both tiers say which they are when ctest starts and ends. A
# ctest run in tests/ of the build tree runs both.
#
# - The entry points of docs/developer/architecture.md that run tests, each registered only if its
#   script exists when CMake runs (configure again after one is added): two here, two in the full
#   tier (full/). They need Python 3; without it they are left out, as are the cross-checks and the
#   full tier, and nothing else changes.
# - The cross-checks: the oracle judges every kernel of gen/claims.json as compiled with this
#   build's compiler and flags, on random binary64 and binary32 cases, once as the flags stand and
#   once per contraction setting that matters to this compiler: the scalar kernels
#   (gen/tests/runner.cpp), and the packed kernels of the target's backend, NEON or AVX2
#   (gen/tests/packed_runner.cpp), with the lanes of each register assigned by a seeded
#   permutation and consecutively; in the full tier on more cases, and also as run by the
#   generator's interpreter on every operand of a toy format (or, where that is too many, on every
#   operand of a restricted domain and on random cases of the whole format).
# - The consumer checks (consume/): a project that uses kairn::kairn and kairn::fma through
#   add_subdirectory, in which Kairn prints nothing when configured and installs nothing unless
#   asked (KAIRN_INSTALL), and one that uses them through find_package after this build tree is
#   installed into a prefix under the build directory.

find_package(Python3 COMPONENTS Interpreter)
include(CheckCXXSourceCompiles)
include(CMakePushCheckState)

# MSVC and clang-cl take MSVC-style options; everything else here takes GCC-style ones.
if(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC" OR
   (MSVC AND NOT CMAKE_CXX_COMPILER_FRONTEND_VARIANT))
  set(_msvc_style ON)
else()
  set(_msvc_style OFF)
endif()

# Whether this build registers the full tier: when Kairn is the top-level project, whose build tree
# holds the CTestCustom.cmake that keeps it out of the quick tier. A project that adds Kairn with
# KAIRN_BUILD_TESTS on gets the quick tier.
if(PROJECT_IS_TOP_LEVEL AND Python3_Interpreter_FOUND)
  set(_full_tier ON)
else()
  set(_full_tier OFF)
endif()

# The claims the oracle judges against, gen/claims.json unless KAIRN_ORACLE_CLAIMS names another
# file of the same form: the kernels and folds this file and api/ register tests for are read from
# it, and every test that runs the oracle passes it on (--claims to crosscheck.py, run.py, the
# oracle's check and search; -DCLAIMS= to crosscheck.cmake). For a branch of the oracle that reads
# some of the claims only: its tests run against a copy of gen/claims.json without the objects it
# does not read yet, and the objects removed are simply absent (docs/developer/testing.md, "Against
# other claims").
set(KAIRN_ORACLE_CLAIMS "" CACHE FILEPATH
  "The claims file of the oracle's tests (empty: gen/claims.json)")
if(KAIRN_ORACLE_CLAIMS)
  get_filename_component(_oracle_claims "${KAIRN_ORACLE_CLAIMS}" ABSOLUTE)
  set(_oracle_claims_arg --claims "${_oracle_claims}")
  set(_oracle_claims_define "-DCLAIMS=${_oracle_claims}")
else()
  set(_oracle_claims "${PROJECT_SOURCE_DIR}/gen/claims.json")
  set(_oracle_claims_arg "")
  set(_oracle_claims_define "")
endif()

# --- The entry points ---------------------------------------------------------------------------
#
# Each is "SCRIPT COMMAND" from the repository root, run as python3 SCRIPT COMMAND ARGS:
# - gen/kairn-gen check (kairn-gen.check): every committed generated file is what the generator
#   writes.
# - oracle/kairn-oracle check --claims-only (kairn-oracle.claims) reads every claim of
#   gen/claims.json.
# - gen/kairn-gen test and oracle/kairn-oracle selftest, the generator's and the oracle's own
#   tests, are in the full tier, each in two parts (full/, "The tools' own tests"): the names below
#   are those of their longest parts, full.kairn-gen.test and full.kairn-oracle.selftest, which the
#   other parts leave out. The four test classes of _gen_full judge the interpreter and the
#   statements on thousands of cases per kernel, about 95% of the time of the generator's tests
#   without C++ (266 of 277 seconds of processor time on an Apple M3 Max); the six tests of
#   _oracle_full are the oracle's enumerations of toy formats through its Python runner, three
#   quarters of its time (62 of 82 seconds on one core of the same Mac). Both tools fail if a name
#   given matches no test.
set(_gen_full test_interp.ToyRounding. test_interp.AgainstHardware. test_statements.Statements.
  test_nonfinite.NonFinite.)
set(_oracle_full correct_runner_toy_exhaustive injected_exhaustive exhaustive_wave2
  injected_wave2_exhaustive exhaustive_wave3 injected_wave3_exhaustive)
list(JOIN _oracle_full "," _oracle_full_names)
set(_entries "gen/kairn-gen check" "gen/kairn-gen test" "oracle/kairn-oracle selftest"
  "oracle/kairn-oracle claims")
set(_full_entries "gen/kairn-gen test" "oracle/kairn-oracle selftest")
set(_present "")
set(_present_full "")
set(_absent "")
foreach(_entry IN LISTS _entries)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(GET _words 0 _script)
  list(GET _words 1 _command)
  if(NOT EXISTS "${PROJECT_SOURCE_DIR}/${_script}")
    list(APPEND _absent "${_entry}")
    continue()
  endif()
  if(_entry IN_LIST _full_entries)
    list(APPEND _present_full "${_entry}")
    continue()
  endif()
  list(APPEND _present "${_entry}")
  if(NOT Python3_Interpreter_FOUND)
    continue()
  endif()
  get_filename_component(_name "${_script}" NAME)
  set(_args "${_command}")
  if(_entry STREQUAL "oracle/kairn-oracle claims")
    set(_args check --claims "${_oracle_claims}" --claims-only)
  endif()
  add_test(NAME "${_name}.${_command}"
    COMMAND "${Python3_EXECUTABLE}" "${_script}" ${_args}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
endforeach()
list(JOIN _present ", " _present)
list(JOIN _present_full ", " _present_full)
list(JOIN _absent ", " _absent)
if(NOT _present)
  set(_present "none")
endif()
if(NOT Python3_Interpreter_FOUND)
  set(_line "Kairn tests: Python 3 not found, so not registered: ${_present}, nor the cross-checks")
  if(_present_full)
    string(APPEND _line ", nor the full tier's ${_present_full}")
  endif()
else()
  set(_line "Kairn tests: registered: ${_present}")
  if(_present_full AND _full_tier)
    string(APPEND _line "; in the full tier: ${_present_full}")
  elseif(_present_full)
    string(APPEND _line "; not registered, as the full tier is not: ${_present_full}")
  endif()
endif()
if(_absent)
  string(APPEND _line "; not present yet: ${_absent}")
endif()
message(STATUS "${_line}")

# --- The reference pages of the site ------------------------------------------------------------
#
# docs.reference.check: the pages under docs/reference/ and the Reference part of the nav in
# mkdocs.yml are what docs/tools/reference.py writes from gen/claims.json, the kernel
# descriptions and the stored brute-force results, as kairn-gen.check is for the generated code.
# The script's own tests are in the full tier (full.tools.docs.reference.test). Python only.
if(Python3_Interpreter_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/docs/tools/reference.py")
  add_test(NAME docs.reference.check
    COMMAND "${Python3_EXECUTABLE}" docs/tools/reference.py --check
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(docs.reference.check PROPERTIES LABELS docs)
endif()

# --- The compiled runners -----------------------------------------------------------------------
#
# gen/tests/runner.cpp runs the generated scalar kernels on the line protocol, and
# gen/tests/packed_runner.cpp the packed ones, one request per lane, the requests assigned to the
# lanes by a seeded permutation (or consecutively, --lanes consecutive). Each is built
# with this build's compiler and flags (kairn-gen-runner, kairn-gen-packed-runner), and once more
# for each contraction setting that matters to the compiler, appended to those flags: the
# regression test of the contraction experiment of docs/developer/design/phase0/environment.md.
# A compiler only contracts when it optimizes, which is why a top-level build defaults to Release.
if(_msvc_style)
  set(_warnings /W4)
else()
  set(_warnings -Wall -Wextra -Wpedantic)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  # /fp:precise does not contract (since Visual Studio 2022), /fp:contract does, and /fp:strict
  # does not either; it is where std::fma becomes a library call, which is why the kernels use
  # the FMA intrinsic on MSVC.
  set(_settings fp-precise /fp:precise fp-contract /fp:contract fp-strict /fp:strict)
elseif(_msvc_style)
  # clang-cl: /fp:strict is -ffp-contract=off, /fp:precise and /fp:contract are =on, and =fast,
  # the setting that broke the textbook product in Phase 0, has no /fp: spelling but /fp:fast,
  # which also assumes there are no NaNs.
  set(_settings fp-strict /fp:strict fp-precise /fp:precise fp-contract /fp:contract
    contract-fast /clang:-ffp-contract=fast)
else()
  set(_settings contract-off -ffp-contract=off contract-on -ffp-contract=on
    contract-fast -ffp-contract=fast)
endif()
# With GCC and Clang the runners of a contraction setting are built at -O2, whatever the build's
# level: Apple clang 21 fuses the textbook product of the Phase 0 experiment at -O2 and leaves it
# alone at -O3, which is what Release gives (docs/developer/testing.md, "Contraction"). The runner
# with the build's flags keeps the build's level, so both levels are tested.
if(_msvc_style)
  set(_contraction_level "")
else()
  set(_contraction_level -O2)
endif()
set(_variants "" "")    # name, option: the runner with the build's flags first
list(APPEND _variants ${_settings})
list(LENGTH _variants _n)
math(EXPR _variants_last "${_n} - 1")

# The packed backend: NEON where the target has it (AArch64), otherwise AVX2 with FMA, and its
# option chosen as kairn::fma's is (cmake/kairn_fma.cmake): nothing if CMAKE_CXX_FLAGS already
# enable it, otherwise /arch:AVX2 (MSVC, clang-cl) or -mavx2 -mfma (GCC, Clang), each tried by
# compiling the backend's header as C++20. With neither, there are no packed kernels for this
# target, no packed runner is built, and configuring says so. The results are cached
# (KAIRN_TESTS_NEON, KAIRN_TESTS_AVX2_WITHOUT_OPTION, KAIRN_TESTS_AVX2_WITH_OPTION). A CPU without
# AVX2 fails the AVX2 cross-checks with an illegal instruction, as one without FMA fails all.
function(_kairn_packed_backend out_backend out_option)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  cmake_push_check_state(RESET)
  set(CMAKE_REQUIRED_INCLUDES "${PROJECT_SOURCE_DIR}/include")
  set(CMAKE_REQUIRED_QUIET ON)
  set(_main "int main() { return 0; }\n")
  set(_backend "")
  set(_option "")
  check_cxx_source_compiles("#include <kairn/gen/neon.hpp>\n${_main}" KAIRN_TESTS_NEON)
  if(KAIRN_TESTS_NEON)
    set(_backend neon)
  else()
    set(_source "#include <kairn/gen/avx2.hpp>\n${_main}")
    check_cxx_source_compiles("${_source}" KAIRN_TESTS_AVX2_WITHOUT_OPTION)
    if(KAIRN_TESTS_AVX2_WITHOUT_OPTION)
      set(_backend avx2)
    else()
      if(_msvc_style)
        set(_candidate /arch:AVX2)
      else()
        set(_candidate -mavx2 -mfma)
      endif()
      list(JOIN _candidate " " CMAKE_REQUIRED_FLAGS)
      check_cxx_source_compiles("${_source}" KAIRN_TESTS_AVX2_WITH_OPTION)
      if(KAIRN_TESTS_AVX2_WITH_OPTION)
        set(_backend avx2)
        set(_option ${_candidate})
      endif()
    endif()
  endif()
  cmake_pop_check_state()
  set(${out_backend} "${_backend}" PARENT_SCOPE)
  set(${out_option} "${_option}" PARENT_SCOPE)
endfunction()

set(_runners "")          # target names
set(_runner_labels "")    # the same, as the cross-checks name them
foreach(_kind scalar packed)
  if(_kind STREQUAL "scalar")
    set(_source "${PROJECT_SOURCE_DIR}/gen/tests/runner.cpp")
    set(_base kairn-gen-runner)
    set(_prefix cxx)
    set(_isa_option "")
  else()
    set(_source "${PROJECT_SOURCE_DIR}/gen/tests/packed_runner.cpp")
    set(_base kairn-gen-packed-runner)
    set(_packed_backend "")
    if(EXISTS "${_source}")
      _kairn_packed_backend(_packed_backend _isa_option)
    endif()
    set(_prefix "${_packed_backend}")
  endif()
  if(NOT EXISTS "${_source}" OR NOT _prefix)
    continue()
  endif()
  foreach(_i RANGE 0 ${_variants_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _variants ${_i} _variant)
    list(GET _variants ${_j} _option)
    if(_variant STREQUAL "")
      set(_target ${_base})
      set(_label ${_prefix})
    else()
      set(_target ${_base}-${_variant})
      set(_label ${_prefix}-${_variant})
    endif()
    add_executable(${_target} "${_source}")
    target_include_directories(${_target} PRIVATE "${PROJECT_SOURCE_DIR}/gen/tests")
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_warnings} ${_isa_option} ${_option})
    if(NOT _variant STREQUAL "")
      target_compile_options(${_target} PRIVATE ${_contraction_level})
    endif()
    list(APPEND _runners ${_target})
    list(APPEND _runner_labels ${_label})
  endforeach()
endforeach()

# --- The object code ----------------------------------------------------------------------------
#
# objcode/objcode.py compiles objcode/unit.cpp, which has a function for every kernel and limb
# type, scalar and packed (the backend above), with this build's compiler in each configuration of
# its flag matrix (contraction settings, optimization levels, -frounding-math; both forms of the
# scalar fix-ups), disassembles each object file, and checks the fused multiply-adds and plain
# multiplications of every kernel against gen/objcode.json, which the generator writes from the
# kernels' IR (docs/developer/testing.md, "Object code"). A disassembler that cannot be found is a
# failure: dumpbin next to cl, llvm-objdump next to clang-cl, objdump otherwise.
# - objcode.check: the quick tier's configurations of the matrix; full.objcode.check (full/) all.
# - objcode.controls: the negative controls, in the same configurations; full.objcode.controls in
#   all: the textbook a * b + c of objcode/fixture.cpp must fail the check exactly where its
#   program sees the compiler fuse it, and somewhere; counts changed on purpose must fail.
# - objcode.test: the checker's own tests, on stored disassemblies of every format (Python only).
# The compilations take the options of CMAKE_CXX_FLAGS and kairn::fma's, as api.k1.zero_cost's do,
# and two of them run at once in the quick tier, four in the full tier (PROCESSORS).
set(_objcode_command "")
if(Python3_Interpreter_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/tests/objcode/objcode.py")
  get_target_property(_objcode_flags kairn::fma INTERFACE_COMPILE_OPTIONS)
  if(NOT _objcode_flags)
    set(_objcode_flags "")
  endif()
  separate_arguments(_objcode_cxx_flags NATIVE_COMMAND "${CMAKE_CXX_FLAGS}")
  list(PREPEND _objcode_flags ${_objcode_cxx_flags})
  if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
    list(APPEND _objcode_flags -isysroot "${CMAKE_OSX_SYSROOT}")
  endif()
  list(JOIN _objcode_flags " " _objcode_flags)
  list(JOIN _isa_option " " _objcode_isa)
  if(_msvc_style)
    set(_objcode_style msvc)
  else()
    set(_objcode_style gnu)
  endif()
  if(_packed_backend)
    set(_objcode_packed "${_packed_backend}")
  else()
    set(_objcode_packed none)
  endif()
  set(_objcode_command "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/objcode/objcode.py"
    --cxx "${CMAKE_CXX_COMPILER}" --style ${_objcode_style} --compiler-id "${CMAKE_CXX_COMPILER_ID}"
    "--flags=${_objcode_flags}" --packed ${_objcode_packed} "--packed-flags=${_objcode_isa}")
  add_test(NAME objcode.check
    COMMAND ${_objcode_command} --tier quick --jobs 2
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/objcode/check")
  add_test(NAME objcode.controls
    COMMAND ${_objcode_command} --controls --tier quick --jobs 2
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/objcode/controls")
  set_tests_properties(objcode.check objcode.controls PROPERTIES TIMEOUT 600 PROCESSORS 2
    LABELS objcode)
  add_test(NAME objcode.test
    COMMAND "${Python3_EXECUTABLE}" tests/objcode/test_objcode.py
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(objcode.test PROPERTIES LABELS "objcode;python")
  message(STATUS "Kairn tests: the object code of every kernel with ${CMAKE_CXX_COMPILER_ID} "
    "(packed: ${_objcode_packed})")
endif()

# --- The cross-checks ---------------------------------------------------------------------------
#
# Each prints the oracle's report and fails when the run did not check what it set out to
# (crosscheck_guards.py):
# - crosscheck.compiled.KERNEL.FORMAT (quick tier) and full.crosscheck.compiled.KERNEL.FORMAT
#   (full tier), run by crosscheck.py in one Python process (the oracle's gen and check, and the
#   guards, in that process; each runner in its own): every compiled runner above on the same
#   random cases of every stratum, the requests generated once and every output judged (an output
#   identical byte for byte to one judged before has its verdict). The quick tier has
#   KAIRN_CROSSCHECK_QUICK_CASES cases, the full tier KAIRN_CROSSCHECK_CASES, from case 0 of the
#   same seed: the quick tier's cases are the first of the full tier's. 6000, because with 2000
#   two more of the faults planted in the kernels that the full tier caught went unseen
#   (docs/developer/testing.md, "Time").
# - full.crosscheck.interp.KERNEL (or interp-restricted and interp-sampled, below), run by
#   crosscheck.cmake as the pipeline gen | interp | check, its three processes at once: the
#   interpreter on a toy format, whose choice depends on the kernel's inputs (below). A kernel
#   without a toy format, or whose toy format is below its min_precision, gets a test that fails
#   and says so, instead of a format where its claims are not stated.
set(KAIRN_CROSSCHECK_CASES 20000 CACHE STRING
  "Random cases in each cross-check of the compiled runners of the full tier, and in each sampled one of the interpreter")
set(KAIRN_CROSSCHECK_QUICK_CASES 6000 CACHE STRING
  "Random cases in each cross-check of the compiled runners of the quick tier")
set(KAIRN_CROSSCHECK_SEED 0 CACHE STRING "Seed of the random cases of the cross-checks")
# The interval kernels of Milestone 2 (the 33 below, their building blocks among them) have fewer
# cases in the quick tier, to keep its time on the hosted runners:
# 2000, the first of the full tier's 20 000, on which their guards still see every class
# (docs/developer/testing.md, "Time").
set(KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES 2000 CACHE STRING
  "Random cases in each cross-check of the compiled runners of an interval kernel, quick tier")
set(_interval_kernels
  mul_dir_1 add_ball_2_2 mul_ball_2_2 add_down_2_2 add_up_2_2 sub_down_2_2 sub_up_2_2 mul_dir_2_2 mul_ext_2_2
  interval_make_1 interval_neg_1 interval_add_1 interval_sub_1 interval_mul_1 interval_add_2 ball_lower_as_1
  ball_upper_as_1 ball_lower_as_2 ball_upper_as_2 ball_from_interval_2 ball_narrow_2_1 interval_neg_2 interval_sub_2
  interval_make_2 interval_mul_2 interval_hull_1 interval_intersection_1 interval_hull_2 interval_intersection_2
  interval_mid_rad_1 interval_to_ball_1 interval_split_1 ball_to_interval_1)
# The kernels of the enclosure interface of stage B2 (architecture.md, "Claims of the enclosure
# interface: predicates and comparisons", "... the set operations of a ball", "... the conversions
# of two limbs"): the same KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES in the quick tier, on which their
# guards see every class.
set(_enclosure_kernels
  interval_empty_1 interval_entire_1 interval_contains_1 interval_subset_1 interval_positive_1 interval_negative_1
  interval_zero_1 interval_less_1 interval_less_equal_1 interval_equal_1 interval_rel_equal_1 interval_rel_interior_1
  interval_rel_disjoint_1 interval_empty_2 interval_entire_2 interval_contains_2 interval_subset_2 interval_positive_2
  interval_negative_2 interval_zero_2 interval_less_2 interval_less_equal_2 interval_equal_2 interval_rel_equal_2
  interval_rel_interior_2 interval_rel_disjoint_2
  ball_contains_point_1 ball_contains_ball_1 ball_positive_1 ball_negative_1 ball_zero_1 ball_less_1
  ball_less_equal_1 ball_equal_1 ball_contains_point_2 ball_contains_ball_2 ball_positive_2 ball_negative_2
  ball_zero_2 ball_less_2 ball_less_equal_2 ball_equal_2
  ball_hull_1 ball_intersection_1 ball_split_1 ball_split_2
  interval_mid_rad_2 interval_to_ball_2 interval_split_2 ball_to_interval_2 ball_from_interval_1 ball_hull_2
  ball_intersection_2)

# The toy formats of the interpreter, by the kernel's inputs, each written as its role: 1 a limb,
# 2 a normalized pair of limbs, r a radius (a limb with nonneg()), c a power of two (a limb with
# power_of_two()), m a mask; and then, for more than one input, sum or product: product when the
# kernel's value has a multiplication. Each is chosen so that the enumeration of every operand
# is 50 000 to 250 000 cases (gen --exhaustive --total), with the range of products below 1 so
# that most products neither overflow nor vanish, and at least the kernel's min_precision. Where
# no such format exists, the entry also names restrictions of the oracle (gen --restrict,
# comma-separated): the test then enumerates that restricted domain, and a second test runs
# KAIRN_CROSSCHECK_CASES random cases of the oracle's generator on the whole format. The kernels
# of the extended domain have a table of their own, further below.
#
#   inputs   kernels                                  format         cases
#   1        split                                    fp:11:-30:10    86 015
#   1 1      two_sum, fast_two_sum, add_1_1,          fp:5:-7:4      172 225
#            two_sum_ord, two_sum_entry,
#            fast_two_sum_entry
#            two_prod, two_prod_dekker, mul_1_1       fp:5:-12:-1    172 225
#   2 1      add_2_1, sub_2_1                         fp:4:-4:2      221 361
#   1 2      sub_1_2                                  fp:4:-4:2      221 361
#   2 1      mul_2_1                                  fp:4:-8:-2     221 361
#   2 2      add_2_2, add_fast_2_2, sub_2_2           fp:3:-3:2      178 929
#   2 2      mul_2_2                                  fp:4:-7:-3     245 025
#   2 c      mul_pow2_2                               fp:5:-6:2      144 755
#   1 r c    ball_mul_pow2_1                          fp:4:-6:1      113 256
#   2 r c    ball_mul_pow2_2                          fp:3:-4:1       94 752
#   1 r 1    ball_scale_1                             fp:3:-5:0       84 700
#   2 r 1    ball_scale_2                             fp:2:-4:1       60 102
#   1 r 1 r  ball_add_1, ball_sub_1                   fp:2:-3:1       76 176
#            ball_mul_1 (its constant (1+u)^5 must    fp:2:-4:1      142 884
#            be a number of the format, so qmax >= 1)
#   2 r 2 r  ball_add_2, ball_sub_2: radii 0, 1/8,    fp:3:-3:2      148 896 of 140 million
#            1/2, 5/2 and cx in [1/2, 2)
#            ball_mul_2: radii 0, eta, 3/2, cx in     fp:4:-5:1       64 728 of 12.4 billion
#            [1, 2) and cy in [1/8, 2)
set(_toy_1 fp:11:-30:10)
set(_toy_1_1_sum fp:5:-7:4)
set(_toy_1_1_product fp:5:-12:-1)
set(_toy_2_1_sum fp:4:-4:2)
set(_toy_1_2_sum fp:4:-4:2)
set(_toy_2_1_product fp:4:-8:-2)
set(_toy_2_2_sum fp:3:-3:2)
set(_toy_2_2_product fp:4:-7:-3)
set(_toy_2_c_product fp:5:-6:2)
set(_toy_1_r_c_product fp:4:-6:1)
set(_toy_2_r_c_product fp:3:-4:1)
set(_toy_1_r_1_product fp:3:-5:0)
set(_toy_2_r_1_product fp:2:-4:1)
set(_toy_1_r_1_r_sum fp:2:-3:1)
set(_toy_1_r_1_r_product fp:2:-4:1)
set(_radii "0x0p+0/0x1p-3/0x1p-1/0x1.4p+1")
set(_toy_2_r_2_r_sum fp:3:-3:2 "rx.in=${_radii},ry.in=${_radii},cx.lead=-1:0")
set(_radii "0x0p+0/0x1p-5/0x1.8p+0")
set(_toy_2_r_2_r_product fp:4:-5:1 "rx.in=${_radii},ry.in=${_radii},cx.lead=0:0,cy.lead=-3:0")

# The kernels of the extended domain (the non-finite layer, "domain": "extended") have toy formats
# of their own, by the same roles read in that domain: 1 any value of the format, infinities and
# NaN included; 2 a canonical pair (finite and normalized, (+-inf, 0) or NaN); r a radius
# (nonneg(), +inf and NaN included); c a power of two (finite); b1 and b2 a ball, its center of one
# or two limbs and its radius together (ball()), which the oracle enumerates as one operand: every
# finite center with every finite radius >= 0, the whole line and the empty set. Every
# enumeration includes the non-finite values of each operand (and a restriction shrinks only the
# finite part of a domain), and every format has the shape the statements of the IEEE model are
# proved for, qmin + qmax = 3 - 2p, as binary64 and binary32 have: an overflow threshold
# 2^(qmax+p) and a smallest number 2^qmin whose product is 2^(3-p). Each enumeration is in the
# same range of 50 000 to 250 000 cases; at these sizes a format of that shape has few exponents
# (two to twelve, and forty for make_2), so overflow is common, which the layer is about.
#
#   inputs   kernels                                  format         cases
#   1        make_2, next_up, next_down               fp:11:-29:10    83 970
#   2        neg_2, abs_2, the conversions,           fp:6:-10:1      89 730
#            make_2_limbs
#   r r      radd, rmul, radd_entry                   fp:6:-10:1     174 724
#   1 1      ball_make_1, the directed sums of one    fp:5:-7:0       84 100
#            limb and their entry forms
#            mul_down_1, mul_up_1 (their constant     fp:5:-7:0       84 100
#            2^(2p-1) eta must be a number of the
#            format)
#   2 1      add_2_1_full, sub_2_1_full, mul_2_1_full, fp:4:-5:0     113 316
#            comparisons, ball_make_2
#   1 2      sub_1_2_full, comparisons                fp:4:-5:0      113 316
#   2 c      mul_pow2_2_full                          fp:5:-7:0       84 888
#   2 2      add_2_2_full, add_fast_2_2_full,         fp:3:-4:1      181 476
#            sub_2_2_full, comparisons
#   2 2      mul_2_2_full                             fp:4:-4:-1      62 500
#   b1       ball_neg_1                               fp:5:-9:2       86 322
#   b2       ball_neg_2                               fp:4:-6:1      198 074
#   b1 b1    ball_add_1_full, ball_sub_1_full,        fp:2:-3:2      144 400
#            ball_mul_1_full
#   b1 1     ball_scale_1_full                        fp:3:-4:1       89 436
#   b2 1     ball_scale_2_full                        fp:3:-3:0      100 044
#   b1 c     ball_mul_pow2_1_full                     fp:4:-6:1      113 278
#   b2 c     ball_mul_pow2_2_full                     fp:3:-4:1       94 768
#   b2 b2    ball_add_2_full, ball_sub_2_full         fp:3:-2:-1     122 500
#            ball_mul_2_full: radii 0, eta, 1/2, 3/2  fp:4:-4:-1     120 780 of 97.6 million
#            and cx in [1, 2)
set(_toy_ext_1 fp:11:-29:10)
set(_toy_ext_2 fp:6:-10:1)
set(_toy_ext_r_r_sum fp:6:-10:1)
set(_toy_ext_r_r_product fp:6:-10:1)
set(_toy_ext_1_1_sum fp:5:-7:0)
set(_toy_ext_1_1_product fp:5:-7:0)
set(_toy_ext_2_1_sum fp:4:-5:0)
set(_toy_ext_1_2_sum fp:4:-5:0)
set(_toy_ext_2_1_product fp:4:-5:0)
set(_toy_ext_2_c_product fp:5:-7:0)
set(_toy_ext_2_2_sum fp:3:-4:1)
set(_toy_ext_2_2_product fp:4:-4:-1)
set(_toy_ext_b1 fp:5:-9:2)
set(_toy_ext_b2 fp:4:-6:1)
set(_toy_ext_b1_b1_sum fp:2:-3:2)
set(_toy_ext_b1_b1_product fp:2:-3:2)
set(_toy_ext_b1_1_product fp:3:-4:1)
set(_toy_ext_b2_1_product fp:3:-3:0)
set(_toy_ext_b1_c_product fp:4:-6:1)
set(_toy_ext_b2_c_product fp:3:-4:1)
set(_toy_ext_b2_b2_sum fp:3:-2:-1)
set(_radii "0x0p+0/0x1p-4/0x1p-1/0x1.8p+0")
set(_toy_ext_b2_b2_product fp:4:-4:-1 "rx.in=${_radii},ry.in=${_radii},cx.lead=0:0")

#   inputs   kernels of the folds' stage of Milestone 2   format         cases
#   n        bound_sum_k, bound_dot_k (count(m) and        fp:12:-30:12    49 153
#            format(half): m*unit(K) up to past 1)
#   1 1 1    dot_step_1, axpy_step_1, axpy_entry_step_1   fp:3:-6:-1     166 375
#   2 2 2    dot_step_2, axpy_step_2, axpy_entry_step_2   fp:4:-3:-2     226 981
#   ext a2   fold_finish_2 (two limbs, any values)        fp:5:-7:0       84 100
#
# The steps of the maps (architecture.md, "Maps") that claim what a kernel above claims have its
# format (add_entry_step_k, sub_1_1, sub_entry_step_k, scale_step_k, mul_pow2_step_2), and:
#
#   1 c      mul_pow2_step_1 (x c, rounded where it       fp:7:-14:6      76 005
#            leaves the normal range)
#   1 2 2    axpy_step_2_1, axpy_entry_step_2_1 (a of     fp:3:-5:-3     107 911
#            one limb; products below 1)
#
# The kernels of the folds of maxima (architecture.md, "Folds of maxima"), m a mask:
#
#   1 m 1 m  norm_combine                                 fp:4:-6:1       81 796
#   1 m 1    norm_step_1                                  fp:5:-7:0      164 738
#   1 m 2    norm_step_2                                  fp:3:-6:2      214 722
#   ext 1 m  norm_finish_1, norm_finish_2 (any value of   fp:11:-29:10   167 940
#            the state's limb, the mask both ways)
set(_toy_n fp:12:-30:12)
set(_toy_1_1_1_product fp:3:-6:-1)
set(_toy_2_2_2_product fp:4:-3:-2)
set(_toy_ext_a2 fp:5:-7:0)
set(_toy_1_c_product fp:7:-14:6)
set(_toy_1_2_2_product fp:3:-5:-3)
set(_toy_1_m_1_m_sum fp:4:-6:1)
set(_toy_1_m_1_sum fp:5:-7:0)
set(_toy_1_m_2_sum fp:3:-6:2)
set(_toy_ext_1_m_sum fp:11:-29:10)

# The kernels of the ball vectors and of the accumulator (architecture.md, "Ball vectors", "The
# accumulator"), with the steps of the scalings, the copies and bv_make_finish in the shapes above
# (mul_pow2_step_k's, split's, the sums of one limb, neg_2's, norm_finish_1's); every constant of
# their listings a finite number of these formats, and the radius of an accumulator at p >= 3 (at
# p = 2 its factor (1+u)^8 rounded up is 6, and from a stated value of Omega/6 the radius
# overflows inside, a non-finite result from small operands that the cross-checks fail):
#
#   inputs       kernels                                  format         cases
#   r r r        bv_add_radius_k (m, rx, ry)              fp:3:-5:3       64 000
#   r r 1        bv_scale_radius_k (m, rx, a)             fp:3:-5:3      126 400
#   r m r c      bv_mul_pow2_radius (m, ex, rx, c)        fp:4:-4:2       81 920
#   ext 1 m m    bv_conv_finish (rz, okc, okg)            fp:10:-27:9    155 656
#   1 r 1        acc_add_1 (s, a, x)                      fp:3:-3:1       53 016
#   2 r 2        acc_add_2                                fp:3:-2:0       55 696
#   1 r 1 1 *    acc_mul_1                                fp:2:-2:1       68 590
#   2 r 2 2 *    acc_mul_2: a in {0, 1/2, 3/2}, s and x   fp:4:-3:-2     105 408 of 5.4 million
#                with leading limbs in [1/2, 2)
#   1 r 1 r      acc_merge_1 (ball_add_1's shape)         fp:2:-3:1       76 176
#   2 r 2 r      acc_merge_2 (of its own, against         fp:3:-2:0       55 696 of 891 136
#                ball_add_2's): a in {0, 1/4, 5/4, 3/2},
#                c in {0, 1/2, 5/4, 7/4}
#   r n r r      acc_radius_k (a, m, g, t)                fp:3:-2:0       53 248
#   r r r r n    conv_radius (ma, mb, rx, ry, m, g, t):   fp:3:-4:4       23 040 of 3.9 10^10
#     r r        a few values each, ma up to Omega
#
# conv_radius: by the ruling of 2026-11-21 its claim is of finite results, and a result
# that is not finite is +inf or a NaN (architecture.md, "Claims of the non-finite layer"). In
# fp:3:-4:4 its constants are 5/2 (up((1+u)^7)) and 15/16 (that of hm), and Omega is 112: ma = Omega
# beside a nonzero mb overflows ma mb, which gives +inf, or a NaN where g or m is zero, and the
# other values keep nine tenths of the results finite (the guards ask three quarters; at precision
# 2, in fp:2:-2:2, where every constant is a number, hm = prod(m, 8) overflows from the count 2).
# A kernel whose shape is another's, with another domain, has an entry _toy_kernel_KERNEL, read
# first.
set(_toy_r_r_r_sum fp:3:-5:3)
set(_toy_r_r_1_sum fp:3:-5:3)
set(_toy_r_m_r_c_sum fp:4:-4:2)
set(_toy_ext_1_m_m_sum fp:10:-27:9)
set(_toy_1_r_1_sum fp:3:-3:1)
set(_toy_2_r_2_sum fp:3:-2:0)
set(_toy_1_r_1_1_product fp:2:-2:1)
set(_toy_2_r_2_2_product fp:4:-3:-2 "a.in=0x0p+0/0x1p-1/0x1.8p+0,s.lead=-1:0,x.lead=-1:0")
# The sums of magnitudes of acc_merge_2 a few values each, among them 5 beside 1.25, whose sum
# 6.25 rounds to 6 by more than a quarter of a gap: an inexact case that is not a tie (the guards
# ask for one), beside the ties 2.75 and 3.25 (69 620 cases).
set(_toy_kernel_acc_merge_2 fp:3:-2:0 "a.in=0x0p+0/0x1p-2/0x1.4p+0/0x1.8p+0,c.in=0x0p+0/0x1p-1/0x1.4p+0/0x1.cp+0/0x1.4p+2")
set(_toy_r_n_r_r_sum fp:3:-2:0)
set(_toy_kernel_conv_radius fp:3:-4:4 "ma.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1/0x1.cp+6,mb.in=0x0p+0/0x1p-4/0x1p-1/0x1p+0/0x1.8p+1,rx.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0,ry.in=0x0p+0/0x1p-4/0x1p-2/0x1p+0,m.in=0x0p+0/0x1p+0/0x1p+1/0x1.8p+1,g.in=0x0p+0/0x1p-3/0x1p-1/0x1p+0,t.in=0x0p+0/0x1p-4/0x1p+0")

# The interval kernels of Milestone 2, in the extended domain: i1 and i2 an interval of one limb
# and of two, its two bounds together (interval()), which the oracle enumerates as one operand:
# the empty set, and every pair l <= h of bounds with l a number or -inf and h a number or +inf.
# The shapes of the other kernels of the interval work are those above: ext 1 1 (interval_make_1,
# ball_from_interval_2, fp:5:-7:0, 84 100 pairs of any values; mul_dir_1, the same format, 83 521
# without NaN), ext 2 2 (interval_make_2 fp:3:-4:1, 181 476; mul_ext_2_2 fp:4:-4:-1, 62 001
# without NaN), ext b1 (ball_lower_as_1, ball_upper_as_1, ball_to_interval_1, fp:5:-9:2, 86 322),
# ext b2 (ball_lower_as_2, ball_upper_as_2, ball_narrow_2_1, fp:4:-6:1, 198 074), and the finite
# 2 2 (add_ball_2_2 and the bounds of two-limb sums at fp:3:-3:2, 178 929; mul_ball_2_2 and
# mul_dir_2_2 at fp:4:-7:-3, 245 025). Where a sampled format is named (_toy_sampled...), the full
# tier also runs the interpreter on KAIRN_CROSSCHECK_CASES random cases of it, from every stratum
# (full.crosscheck.interp-sampled.K): the enumerations of two intervals are of tiny formats, of
# two or three exponents for two limbs, where a sum of pairs is exact.
#
#   inputs       kernels                                      format        cases     sampled
#   ext i1       interval_neg_1, interval_mid_rad_1,          fp:5:-9:2      86 737   -
#                interval_to_ball_1, interval_split_1
#   ext i1 i1    interval_add_1, interval_sub_1,              fp:2:-3:2     165 649   fp:5:-7:0
#                interval_hull_1, interval_intersection_1
#   ext i1 i1 *  interval_mul_1                               fp:2:-3:2     165 649   fp:5:-12:5
#   ext i2       interval_neg_2                               fp:3:-4:1      90 101   -
#   ext i2 i2    interval_add_2, interval_sub_2,              fp:3:-2:-1    217 156   fp:4:-10:5
#                interval_hull_2, interval_intersection_2
#   ext i2 i2 *  interval_mul_2: x's bounds with leading      fp:4:-3:-2    see the   fp:5:-12:5
#                limbs in {0, 1/8, 1, 3/2, 3}, of either sign                 table
set(_toy_ext_i1 fp:5:-9:2)
set(_toy_ext_i1_i1_sum fp:2:-3:2)
set(_toy_sampled_ext_i1_i1_sum fp:5:-7:0)
set(_toy_ext_i1_i1_product fp:2:-3:2)
set(_toy_sampled_ext_i1_i1_product fp:5:-12:5)
set(_toy_ext_i2 fp:3:-4:1)
set(_toy_ext_i2_i2_sum fp:3:-2:-1)
set(_toy_sampled_ext_i2_i2_sum fp:4:-10:5)
set(_bounds "0x0p+0/0x1p-3/-0x1p-3/0x1p+0/-0x1p+0/0x1.8p+0/-0x1.8p+0/0x1.8p+1/-0x1.8p+1")
set(_toy_ext_i2_i2_product fp:4:-3:-2 "xl.in=${_bounds},xu.in=${_bounds}")
set(_toy_sampled_ext_i2_i2_product fp:5:-12:5)
# The enclosure interface of stage B2 has the shapes above (ext i1, i1 i1, i2, i2 i2, b1, b1 b1,
# b2, b2 b2, 1 1: the predicates and comparisons of one set or two, the set operations of a ball,
# the conversions of two limbs) and four of its own, a set and a point (member):
#
#   inputs       kernels                                      format        cases
#   ext i1 1     interval_contains_1                          fp:3:-4:1      95 816
#   ext i2 2     interval_contains_2                          fp:2:-2:1      95 816
#   ext b1 1     ball_contains_point_1                        fp:3:-4:1      89 436
#   ext b2 2     ball_contains_point_2                        fp:3:-3:0     290 604
#
# (two balls of two limbs, ball_less_2 ... ball_intersection_2: fp:3:-2:-1, 122 500; two intervals
# of two limbs: fp:3:-2:-1, 245 025, and random cases of fp:4:-10:5).
set(_toy_ext_i1_1_sum fp:3:-4:1)
set(_toy_ext_i2_2_sum fp:2:-2:1)
set(_toy_ext_b1_1_sum fp:3:-4:1)
set(_toy_ext_b2_2_sum fp:3:-3:0)

# --- Not yet cross-checked by the oracle ------------------------------------------------------
#
# Kernels of gen/claims.json and folds of its list "folds" that the oracle does not judge yet: no
# cross-check, no enumeration of a toy format and no test of the public interface is registered for
# a name of these lists, and configuring says how many are left out. A kernel or a fold added to the
# generator with claims the oracle cannot read goes here until the oracle reads them. Since the
# folds' stage of Milestone 2 the oracle judges every claim of that stage (folds, their steps,
# finishes and bounds included; oracle/README.md).
#
# Since the interval stage of Milestone 2 the oracle reads and judges every claim of the interval
# kernels and of the kernels of their bounds (architecture.md, "Claims of the interval kernels" and
# "... two limbs and the enclosure interface"; oracle/README.md, "The kinds of the interval
# kernels"), and since stage B every claim of the maps and their steps, the folds of maxima and
# their kernels, and the convolutions (oracle/README.md, "Maps", "Folds of maxima",
# "Convolutions"), and since the ball vectors' stage the folds with "bv": true and "bv_conv": true
# (their requests, the requirement ball_vector, the claims encloses_entries, makes_ball_vector and
# encloses_coefficients with count_when), their kernels and those of the accumulator
# (oracle/README.md, "Ball vectors and the accumulator"), and since stage B2 of the enclosure
# interface the predicates and three-valued comparisons of an interval and of a ball (the claims
# certain and trit, the condition abs_le of their exact_when), the set operations of a ball
# (ball_set, ball_splits) and the conversions of two limbs with the hull and the intersection of
# balls of two limbs (finite_when of ball_of_interval, interval_of_ball of two limbs, rel, abs and
# smallest_radius of a makes_ball from an interval; architecture.md, "Claims of the enclosure
# interface: predicates and comparisons", "... the set operations of a ball", "... the conversions
# of two limbs"; oracle/README.md, "The kinds of the enclosure interface"): none of those is on the
# lists. conv_radius left them with the ruling of 2026-11-21 (architecture.md, "Claims of
# the non-finite layer"): its claim is of finite results, and a result that is not finite is +inf
# or a NaN, as its listing's are (a NaN where ma*mb overflows and g or m is zero, 0 * inf; +inf
# from small operands and a huge count).
#
# Both lists are empty: the oracle reads every claim of gen/claims.json, and configuring says that
# none is left out. They stay, for the objects of a later stage whose claims the oracle cannot read
# yet.
#
# Each list is written out in full here, the one place that says which (tests/brute/brute.py reads
# them as written).
set(KAIRN_NOT_YET_CROSS_CHECKED)
set(KAIRN_NOT_YET_CROSS_CHECKED_FOLDS)
# The folds that no public function calls yet and that the public interface's runner lists in none
# of its lists (api/coverage.cmake): those of BallVector (architecture.md, "Ball vectors"), whose
# header comes later. Cross-checked like every fold; the public interface has no form of them.
set(KAIRN_NOT_PUBLIC_YET_FOLDS
  bv_add_1 bv_add_2 bv_sub_1 bv_sub_2 bv_scale_1 bv_scale_2 bv_neg_1 bv_neg_2 bv_mul_pow2_1 bv_mul_pow2_2
  bv_make_1 bv_make_2 bv_conv_1 bv_conv_2)
# The kernels that no public operation calls yet and that the public interface's runner lists in
# none of its lists (api/CMakeLists.txt, api/coverage.cmake): the steps of the maps on stored
# arrays, which no public function calls (include/kairn/batch.hpp calls the maps on supplied
# arrays: sub_1_1 is the step of sub_1, axpy_step_k of axpy_k); and the kernels of the ball vectors
# (architecture.md, "Ball vectors"), which only the folds of BallVector call. They are cross-checked like every kernel; the public interface has no form of
# them. (The interval kernels left this list with include/kairn/interval.hpp; the steps, finishes
# and kernels of the folds of maxima that kairn/batch.hpp calls with it, the public interface
# reaching each through its fold, which api.oracle.FOLD.FORMAT judges, and listing it as a
# building block or as not public on its own; the bounds as functions of n with
# kairn::traits<X>::sum(n), sum_height(h) and dot(n), the forms of api.oracle.bound_*; the kernels
# of the accumulator with include/kairn/accumulator.hpp, acc_radius_k as a building block; and the
# 53 kernels of the enclosure interface of stage B2, _enclosure_kernels above, with the functions
# of interval.hpp and ball.hpp that call them: predicates, comparisons, relations of IEEE 1788, set
# operations of a ball, conversions of two limbs; runner.cpp maps a public form to each.)
set(KAIRN_NOT_PUBLIC_YET
  sub_1_1 axpy_step_1 axpy_step_2 axpy_step_2_1
  bv_add_radius_1 bv_add_radius_2 bv_scale_radius_1 bv_scale_radius_2 bv_center_entry_1 bv_center_2
  bv_make_radius bv_make_finish neg_1 bv_neg_radius bv_mul_pow2_step_1 bv_mul_pow2_step_2
  bv_mul_pow2_radius conv_radius bv_conv_finish)

# The folds (gen/claims.json, "folds"): random arrays through every compiled runner in the quick
# tier, the scalar runners on every order (seq, lanes:0, 1, 2, 3, 4, 5, 8 and more lanes than
# elements) and the packed runners on the lane order of their register, KAIRN_CROSSCHECK_FOLD_
# QUICK_CASES and KAIRN_CROSSCHECK_FOLD_PACKED_QUICK_CASES arrays of lengths 0 to
# KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH; in the full tier more and longer arrays, and the interpreter
# on every array of a tiny format up to a small length and on random arrays of a toy format, by the
# fold's arrays (a sum of one or two limbs, a dot product of one or two):
#
#   arrays   folds                         every array of                      random arrays of
#   1        sum_1, sum_1_entry            fp:3:-3:0 up to 3 elements: 225 835 fp:5:-7:4
#   2        sum_2, sum_fast_2, entries    fp:3:-4:1 up to 2:          363 379 fp:4:-7:2
#   1 1      dot_1                         fp:2:-1:0 up to 2:           77 029 fp:5:-12:-1
#   2 2      dot_2                         fp:4:-4:-1, one element:     62 501 fp:4:-7:-3
#
# (each format of the shape qmin + qmax = 3 - 2p of the extended domain, which every fold has, and
# at least the fold's min_precision).
set(_fold_toy_1 fp:3:-3:0 3 fp:5:-7:4)
set(_fold_toy_2 fp:3:-4:1 2 fp:4:-7:2)
set(_fold_toy_1_1 fp:2:-1:0 2 fp:5:-12:-1)
set(_fold_toy_2_2 fp:4:-4:-1 1 fp:4:-7:-3)
set(KAIRN_CROSSCHECK_FOLD_QUICK_CASES 300 CACHE STRING
  "Random arrays in each cross-check of a fold through the scalar runners, quick tier")
set(KAIRN_CROSSCHECK_FOLD_PACKED_QUICK_CASES 200 CACHE STRING
  "Random arrays in each cross-check of a fold through the packed runners, quick tier")
set(KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH 256 CACHE STRING
  "The longest random array of the quick tier's cross-checks of folds")
# (Arrays of up to 4 096 elements are 265 elements on average: 1 000 of dot_2 take the oracle's
# generator 7 seconds and its judge 3, per stream; the generator, not the judge, is the slower.)
set(KAIRN_CROSSCHECK_FOLD_CASES 1000 CACHE STRING
  "Random arrays in each cross-check of a fold (and each sampled run of the interpreter), full tier")
set(KAIRN_CROSSCHECK_FOLD_PACKED_CASES 500 CACHE STRING
  "Random arrays in each cross-check of a fold through the packed runners, full tier")
set(KAIRN_CROSSCHECK_FOLD_LENGTH 4096 CACHE STRING
  "The longest random array of the full tier's cross-checks of folds")

# The maps, the convolutions and the folds of maxima of stage B (architecture.md, "Maps",
# "Convolutions", "Folds of maxima"), in the same tests, by the same drivers; in the quick tier on
# fewer and shorter arrays (reading a long line is what costs, and these have the weight of their
# tests in the full tier), and a convolution, whose lines hold n_x n_y terms, on shorter ones in
# both tiers. Their toy formats, by the kind, the scalars (s1 a scalar of one limb, s2 of two, sc a
# power of two) and the arrays, each enumeration a complete one of the tiny format up to the
# length given (for a convolution, both lengths up to it):
#
#   shape        folds                          every array of                  random arrays of
#   map 1 1      add_1, sub_1, entries          fp:2:-1:0 up to 2:      77 029  fp:5:-7:4
#   map 2 2      add_2, sub_2, entries          fp:3:-4:1, one element: 181 477 fp:4:-7:2
#   map s1 1 1   axpy_1, axpy_1_entry           fp:3:-3:0, one:          74 130 fp:5:-12:-1
#   map s2 2 2   axpy_2, axpy_2_entry           fp:4:-3:-2, one:        262 208 fp:4:-7:-3
#   map s1 2 2   axpy_2_1, axpy_2_1_entry       fp:3:-2:-1, one:         26 650 fp:4:-7:-3
#   map s1 1     scale_1                        fp:3:-3:0 up to 2:     149 982  fp:5:-12:-1
#   map s1 2     scale_2                        fp:2:-2:1 up to 2:     149 314  fp:4:-8:-2
#   map sc 1     mul_pow2_map_1                 fp:4:-5:0 up to 2:     234 963  fp:5:-6:2
#   map sc 2     mul_pow2_map_2                 fp:3:-3:0 up to 2:     179 346  fp:5:-6:2
#   max 1        norm_upper_1                   fp:3:-3:0 up to 3:     225 835  fp:5:-7:4
#   max 2        norm_upper_2                   fp:3:-4:1 up to 2:     363 379  fp:4:-7:2
#   conv 1 1     conv_1                         fp:2:-1:0 up to 2, 2:   44 521  fp:5:-12:-1
#   conv 2 2     conv_2                         fp:4:-4:-1 up to 1, 1:  63 001  fp:4:-7:-3
#
# Two elements of the maps of pairs, and of axpy, are more than ten million arrays in any format of
# their precision: their single elements are every case of the step (with every flag and second
# pass of one element), and the sampled runs and the compiled runners have the rest.
set(_fold_toy_map_1_1 fp:2:-1:0 2 fp:5:-7:4)
set(_fold_toy_map_2_2 fp:3:-4:1 1 fp:4:-7:2)
set(_fold_toy_map_s1_1_1 fp:3:-3:0 1 fp:5:-12:-1)
set(_fold_toy_map_s2_2_2 fp:4:-3:-2 1 fp:4:-7:-3)
set(_fold_toy_map_s1_2_2 fp:3:-2:-1 1 fp:4:-7:-3)
set(_fold_toy_map_s1_1 fp:3:-3:0 2 fp:5:-12:-1)
set(_fold_toy_map_s1_2 fp:2:-2:1 2 fp:4:-8:-2)
set(_fold_toy_map_sc_1 fp:4:-5:0 2 fp:5:-6:2)
set(_fold_toy_map_sc_2 fp:3:-3:0 2 fp:5:-6:2)
set(_fold_toy_max_1 fp:3:-3:0 3 fp:5:-7:4)
set(_fold_toy_max_2 fp:3:-4:1 2 fp:4:-7:2)
set(_fold_toy_conv_1_1 fp:2:-1:0 2 fp:5:-12:-1)
set(_fold_toy_conv_2_2 fp:4:-4:-1 1 fp:4:-7:-3)

# The ball vectors (architecture.md, "Ball vectors"), each its own toy formats (_fold_toy_kernel_F,
# read first): every canonical BallVector (every nonnegative radius with every entry, and the
# whole space) up to the length given, every value of the other scalars, every order that differs,
# and random arrays of a format of more bits; their quick tier is the maps' (KAIRN_CROSSCHECK_MAP_*),
# a product of BallVectors the convolutions' lengths. "-" for the enumeration: none, where every
# format of the fold's minimum precision has more than a few million cases (a product of
# BallVectors, at p = 4 10 million arrays of one entry each), and the random runs alone. The
# oracle judges V4 in the formats of its statements, binary_float (q_max >= 1, q_min =
# 3 - q_max - 2p) or of a wider subnormal range (architecture.md, "From which precision each clause
# holds"; oracle/README.md, "Ball vectors and the accumulator"): every format below but
# fp:3:-2:-1, where the smallest such format of precision 3, fp:3:-4:1, has some 10^8 requests of
# one entry each (V4 of bv_add_2 and bv_sub_2 is judged in their random arrays).
#
#   folds                          every operand of                    random arrays of
#   bv_add_1, bv_sub_1             fp:2:-2:1, one entry:        36 602 fp:5:-11:4
#   bv_add_2, bv_sub_2             fp:3:-2:-1, one entry:      121 970 fp:4:-7:2
#   bv_scale_1                     fp:2:-2:1 up to 2:          163 328 fp:5:-12:5
#   bv_scale_2                     fp:2:-2:1, one entry:        12 364 fp:4:-8:2
#   bv_neg_1                       fp:2:-2:1 up to 2:            7 424 fp:5:-11:4
#   bv_neg_2                       fp:2:-2:1 up to 2:           61 064 fp:4:-7:2
#   bv_mul_pow2_1                  fp:2:-2:1 up to 2:           37 120 fp:5:-9:2
#   bv_mul_pow2_2                  fp:2:-2:1 up to 2:          305 320 fp:5:-9:2
#   bv_make_1                      fp:2:-2:1 up to 2:           21 802 fp:5:-11:4
#   bv_make_2                      fp:2:-2:1 up to 2:          149 314 fp:4:-7:2
#   bv_conv_1, bv_conv_2           -                                   fp:5:-12:5
set(_fold_toy_kernel_bv_add_1 fp:2:-2:1 1 fp:5:-11:4)
set(_fold_toy_kernel_bv_sub_1 fp:2:-2:1 1 fp:5:-11:4)
set(_fold_toy_kernel_bv_add_2 fp:3:-2:-1 1 fp:4:-7:2)
set(_fold_toy_kernel_bv_sub_2 fp:3:-2:-1 1 fp:4:-7:2)
set(_fold_toy_kernel_bv_scale_1 fp:2:-2:1 2 fp:5:-12:5)
set(_fold_toy_kernel_bv_scale_2 fp:2:-2:1 1 fp:4:-8:2)
set(_fold_toy_kernel_bv_neg_1 fp:2:-2:1 2 fp:5:-11:4)
set(_fold_toy_kernel_bv_neg_2 fp:2:-2:1 2 fp:4:-7:2)
set(_fold_toy_kernel_bv_mul_pow2_1 fp:2:-2:1 2 fp:5:-9:2)
set(_fold_toy_kernel_bv_mul_pow2_2 fp:2:-2:1 2 fp:5:-9:2)
set(_fold_toy_kernel_bv_make_1 fp:2:-2:1 2 fp:5:-11:4)
set(_fold_toy_kernel_bv_make_2 fp:2:-2:1 2 fp:4:-7:2)
set(_fold_toy_kernel_bv_conv_1 - 0 fp:5:-12:5)
set(_fold_toy_kernel_bv_conv_2 - 0 fp:5:-12:5)
set(KAIRN_CROSSCHECK_MAP_QUICK_CASES 100 CACHE STRING
  "Random arrays in each cross-check of a map, a convolution or a fold of maxima, quick tier")
set(KAIRN_CROSSCHECK_MAP_QUICK_LENGTH 24 CACHE STRING
  "The longest random array of the quick tier's cross-checks of maps and folds of maxima")
set(KAIRN_CROSSCHECK_MAP_LENGTH 1024 CACHE STRING
  "The longest random array of the full tier's cross-checks of maps")
set(KAIRN_CROSSCHECK_CONV_QUICK_LENGTH 20 CACHE STRING
  "The longest polynomial of the quick tier's cross-checks of convolutions")
set(KAIRN_CROSSCHECK_CONV_CASES 300 CACHE STRING
  "Random pairs of polynomials in each cross-check of a convolution, full tier")
set(KAIRN_CROSSCHECK_CONV_LENGTH 64 CACHE STRING
  "The longest polynomial of the full tier's cross-checks of convolutions")

# Kernels whose intermediate values can overflow for operands far below the largest number (the
# product by the splitter), as their requirement of no intermediate overflow allows. The oracle
# counts the non-finite results of such operands as suspicious; any other kernel that returns one
# fails its cross-check (--fail-on-suspicious).
set(_intermediate_overflow split two_prod_dekker)

set(_claims_file "${_oracle_claims}")
if(Python3_Interpreter_FOUND AND EXISTS "${_claims_file}")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_claims_file}")
  file(READ "${_claims_file}" _claims)
  string(JSON _count LENGTH "${_claims}" kernels)
  math(EXPR _last "${_count} - 1")
  set(_driver "${CMAKE_CURRENT_SOURCE_DIR}/crosscheck.cmake")
  set(_crosscheck "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/crosscheck.py")
  set(_summaries "${CMAKE_CURRENT_BINARY_DIR}/crosscheck")
  set(_common "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}"
    ${_oracle_claims_define})
  set(_random "-DCOUNT=${KAIRN_CROSSCHECK_CASES}" "-DSEED=${KAIRN_CROSSCHECK_SEED}")
  set(_random_args --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_CASES}")
  set(_random_quick_args --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_QUICK_CASES}")
  # Every compiled runner for crosscheck.py: the scalar ones as --runner LABEL EXECUTABLE, the
  # packed ones as --packed-kernels LABEL EXECUTABLE ASSIGNMENTS, with the lanes of their
  # registers assigned by the seeded permutation (each under the guard that the lanes mixed), and
  # also consecutively (LABEL.consecutive, registers of one kind): in the quick tier the second
  # for the runner with the build's flags only, in the full tier (_compiled_both) for every one
  # (docs/developer/testing.md, "Packed kernels").
  set(_compiled "")
  set(_compiled_both "")
  foreach(_runner _label IN ZIP_LISTS _runners _runner_labels)
    if(_label MATCHES "^cxx")
      list(APPEND _compiled --runner "${_label}" "$<TARGET_FILE:${_runner}>")
      list(APPEND _compiled_both --runner "${_label}" "$<TARGET_FILE:${_runner}>")
    else()
      set(_assignments permuted)
      if(_label STREQUAL "${_packed_backend}")
        set(_assignments "permuted,consecutive")
      endif()
      list(APPEND _compiled --packed-kernels "${_label}" "$<TARGET_FILE:${_runner}>" "${_assignments}")
      list(APPEND _compiled_both --packed-kernels "${_label}" "$<TARGET_FILE:${_runner}>"
        "permuted,consecutive")
    endif()
  endforeach()
  # What full/CMakeLists.txt registers, kernel by kernel, for the full tier.
  set(_full_kernels "")
  set(_n_complete 0)
  set(_n_restricted 0)
  set(_n_not_checked 0)
  foreach(_i RANGE ${_last})
    string(JSON _kernel GET "${_claims}" kernels ${_i} name)
    if(_kernel IN_LIST KAIRN_NOT_YET_CROSS_CHECKED)
      math(EXPR _n_not_checked "${_n_not_checked} + 1")
      continue()
    endif()
    string(JSON _value ERROR_VARIABLE _no_value GET "${_claims}" kernels ${_i} value)
    string(JSON _min ERROR_VARIABLE _no_min GET "${_claims}" kernels ${_i} min_precision)
    string(JSON _domain ERROR_VARIABLE _no_domain GET "${_claims}" kernels ${_i} domain)
    if(NOT _domain STREQUAL "extended")
      set(_domain finite)
    endif()
    set(_requires "")
    set(_ball_centers "")
    set(_ball_radii "")
    set(_iv_lowers "")
    set(_iv_uppers "")
    string(JSON _n_requires LENGTH "${_claims}" kernels ${_i} requires)
    if(_n_requires GREATER 0)
      math(EXPR _req_last "${_n_requires} - 1")
      foreach(_j RANGE ${_req_last})
        string(JSON _req GET "${_claims}" kernels ${_i} requires ${_j})
        string(REPLACE " " "" _req "${_req}")
        list(APPEND _requires "${_req}")
        if(_req MATCHES "^ball\\(([^,]+),([^)]+)\\)$")
          list(APPEND _ball_centers "${CMAKE_MATCH_1}")
          list(APPEND _ball_radii "${CMAKE_MATCH_2}")
        endif()
        # An interval (the interval kernels): its lower bound stands for it, its upper is left out.
        if(_req MATCHES "^interval\\(([^,]+),([^)]+)\\)$")
          list(APPEND _iv_lowers "${CMAKE_MATCH_1}")
          list(APPEND _iv_uppers "${CMAKE_MATCH_2}")
        endif()
      endforeach()
    endif()
    # The roles of the inputs, then the operation; in the extended domain, after "ext", with a
    # ball's center standing for the ball and its radius left out.
    string(JSON _inputs LENGTH "${_claims}" kernels ${_i} inputs)
    if(_domain STREQUAL "extended")
      set(_shape "_ext")
    else()
      set(_shape "")
    endif()
    set(_n_roles 0)
    math(EXPR _in_last "${_inputs} - 1")
    foreach(_j RANGE ${_in_last})
      string(JSON _input GET "${_claims}" kernels ${_i} inputs ${_j} name)
      string(JSON _type ERROR_VARIABLE _no_type GET "${_claims}" kernels ${_i} inputs ${_j} type)
      string(JSON _limbs ERROR_VARIABLE _no_limbs GET "${_claims}" kernels ${_i} inputs ${_j} limbs)
      if(_input IN_LIST _ball_radii OR _input IN_LIST _iv_uppers)
        continue()
      elseif(_type STREQUAL "mask")
        set(_role m)
      elseif(_input IN_LIST _ball_centers)
        set(_role "b${_limbs}")
      elseif(_input IN_LIST _iv_lowers)
        set(_role "i${_limbs}")
      elseif(NOT _limbs STREQUAL "1" AND _domain STREQUAL "extended"
             AND NOT "canonical(${_input})" IN_LIST _requires)
        # Several limbs of any values (the state a fold's finish takes).
        set(_role "a${_limbs}")
      elseif(NOT _limbs STREQUAL "1")
        set(_role "${_limbs}")
      elseif("count(${_input})" IN_LIST _requires)
        set(_role n)
      elseif("nonneg(${_input})" IN_LIST _requires)
        set(_role r)
      elseif("power_of_two(${_input})" IN_LIST _requires)
        set(_role c)
      else()
        set(_role 1)
      endif()
      string(APPEND _shape "_${_role}")
      math(EXPR _n_roles "${_n_roles} + 1")
    endforeach()
    if(_n_roles GREATER 1)
      # A kernel without a value (an interval kernel) is a product when the set of an entry is.
      set(_product OFF)
      if(_value MATCHES "\\*" AND NOT _no_value)
        set(_product ON)
      elseif(_no_value)
        string(JSON _n_ensures LENGTH "${_claims}" kernels ${_i} ensures)
        math(EXPR _ens_last "${_n_ensures} - 1")
        foreach(_j RANGE ${_ens_last})
          string(JSON _set ERROR_VARIABLE _no_set GET "${_claims}" kernels ${_i} ensures ${_j} set)
          if(NOT _no_set AND _set MATCHES "\\*")
            set(_product ON)
          endif()
        endforeach()
      endif()
      if(_product)
        string(APPEND _shape "_product")
      else()
        string(APPEND _shape "_sum")
      endif()
    endif()
    set(_fail_on_suspicious ON)
    set(_suspicious_arg --fail-on-suspicious)
    if(_kernel IN_LIST _intermediate_overflow)
      set(_fail_on_suspicious OFF)
      set(_suspicious_arg "")
    endif()
    set(_this ${_common} "-DKERNEL=${_kernel}" "-DFAIL_ON_SUSPICIOUS=${_fail_on_suspicious}")
    set(_this_compiled compiled --kernel "${_kernel}" ${_suspicious_arg} ${_oracle_claims_arg})

    # The interpreter, on every operand of the toy format, or of a restricted domain of it and
    # on random cases of all of it.
    set(_toy "${_toy${_shape}}")
    if(DEFINED _toy_kernel_${_kernel})
      set(_toy "${_toy_kernel_${_kernel}}")
    endif()
    list(LENGTH _toy _toy_length)
    set(_restrict "")
    if(_toy_length GREATER 1)
      list(GET _toy 1 _restrict)
      list(GET _toy 0 _toy)
    endif()
    set(_error "")
    if(NOT _toy)
      string(REPLACE "_" " " _operands "${_shape}")
      set(_error "no toy format is chosen for the inputs of ${_kernel} (${_operands}): "
        "add one in tests/CMakeLists.txt")
    elseif(_min MATCHES "^[0-9]+$")
      string(REGEX REPLACE "^fp:([0-9]+):.*" "\\1" _p "${_toy}")
      if(_p LESS _min)
        set(_error "the toy format ${_toy} of ${_kernel} is below its min_precision ${_min}: "
          "choose another in tests/CMakeLists.txt")
      endif()
    endif()
    if(_restrict)
      math(EXPR _n_restricted "${_n_restricted} + 1")
    else()
      math(EXPR _n_complete "${_n_complete} + 1")
    endif()
    string(JOIN "" _error ${_error})
    # For full/CMakeLists.txt, which registers the interpreter's tests and the compiled runners'
    # on KAIRN_CROSSCHECK_CASES cases.
    list(APPEND _full_kernels ${_kernel})
    set(_full_${_kernel}_this ${_this})
    set(_full_${_kernel}_this_compiled ${_this_compiled})
    set(_full_${_kernel}_toy "${_toy}")
    set(_full_${_kernel}_restrict "${_restrict}")
    set(_full_${_kernel}_error "${_error}")
    # A sampled format of its own (the interval kernels): random cases of it in the full tier.
    set(_full_${_kernel}_sampled "${_toy_sampled${_shape}}")

    # The compiled runners, on random cases of every stratum.
    if(_compiled)
      set(_quick_args ${_random_quick_args})
      if(_kernel IN_LIST _interval_kernels OR _kernel IN_LIST _enclosure_kernels)
        set(_quick_args --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES}")
      endif()
      foreach(_format binary64 binary32)
        set(_name crosscheck.compiled.${_kernel}.${_format})
        add_test(NAME ${_name} COMMAND ${_crosscheck} ${_this_compiled} --format ${_format}
          ${_quick_args} --summary "${_summaries}/${_name}.json" ${_compiled})
        set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;compiled")
      endforeach()
    endif()
  endforeach()
  # That the guards fail the runs they are there to fail, and that crosscheck.py and
  # crosscheck.cmake fail with them, is tested in the full tier (full.tools.crosscheck.guards).

  # The folds: the scalar runners (labels cxx*) on requests of every order, the packed runners on
  # requests of the lane order of their register (packed_lanes of the fold's claims, for the
  # target's backend), each stream with its own guards (crosscheck.py compiled --packed-runner).
  set(_compiled_scalar "")
  set(_compiled_packed "")
  foreach(_runner _label IN ZIP_LISTS _runners _runner_labels)
    if(_label MATCHES "^cxx")
      list(APPEND _compiled_scalar --runner "${_label}" "$<TARGET_FILE:${_runner}>")
    else()
      list(APPEND _compiled_packed --packed-runner "${_label}" "$<TARGET_FILE:${_runner}>")
    endif()
  endforeach()
  set(_full_folds "")
  set(_n_folds 0)
  set(_n_folds_not_checked 0)
  string(JSON _fold_count ERROR_VARIABLE _no_folds LENGTH "${_claims}" folds)
  if(_no_folds)
    set(_fold_count 0)
  endif()
  if(_fold_count GREATER 0)
    math(EXPR _fold_last "${_fold_count} - 1")
    foreach(_i RANGE ${_fold_last})
      string(JSON _fold GET "${_claims}" folds ${_i} name)
      if(_fold IN_LIST KAIRN_NOT_YET_CROSS_CHECKED_FOLDS)
        math(EXPR _n_folds_not_checked "${_n_folds_not_checked} + 1")
        continue()
      endif()
      math(EXPR _n_folds "${_n_folds} + 1")
      string(JSON _min ERROR_VARIABLE _no_min GET "${_claims}" folds ${_i} min_precision)
      string(JSON _value GET "${_claims}" folds ${_i} value)
      string(JSON _n_arrays LENGTH "${_claims}" folds ${_i} arrays)
      # A map ("map": true), a convolution ("conv": true) or a fold of maxima (an upper entry):
      # its kind first, then for a map its scalars, in the shape of its toy formats; and its
      # counts and lengths in both tiers.
      string(JSON _is_map ERROR_VARIABLE _no_map GET "${_claims}" folds ${_i} map)
      string(JSON _is_conv ERROR_VARIABLE _no_conv GET "${_claims}" folds ${_i} conv)
      string(JSON _kind0 ERROR_VARIABLE _no_kind0 GET "${_claims}" folds ${_i} ensures 0 kind)
      string(JSON _is_bv ERROR_VARIABLE _no_bv GET "${_claims}" folds ${_i} bv)
      string(JSON _is_bvconv ERROR_VARIABLE _no_bvconv GET "${_claims}" folds ${_i} bv_conv)
      if(_no_bv)
        set(_is_bv OFF)
      endif()
      if(_no_bvconv)
        set(_is_bvconv OFF)
      endif()
      set(_shape "")
      set(_quick_count ${KAIRN_CROSSCHECK_FOLD_QUICK_CASES})
      set(_quick_packed ${KAIRN_CROSSCHECK_FOLD_PACKED_QUICK_CASES})
      set(_quick_length ${KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH})
      set(_full_fold_${_fold}_cases ${KAIRN_CROSSCHECK_FOLD_CASES})
      set(_full_fold_${_fold}_length ${KAIRN_CROSSCHECK_FOLD_LENGTH})
      set(_full_fold_${_fold}_sampled_length 1024)
      if(_is_map OR _is_conv OR _kind0 STREQUAL "upper" OR _is_bv OR _is_bvconv)
        set(_quick_count ${KAIRN_CROSSCHECK_MAP_QUICK_CASES})
        set(_quick_packed ${KAIRN_CROSSCHECK_MAP_QUICK_CASES})
        set(_quick_length ${KAIRN_CROSSCHECK_MAP_QUICK_LENGTH})
      endif()
      if(_is_map)
        set(_shape "_map")
        set(_full_fold_${_fold}_length ${KAIRN_CROSSCHECK_MAP_LENGTH})
        string(JSON _n_scalars LENGTH "${_claims}" folds ${_i} scalars)
        string(JSON _requires GET "${_claims}" folds ${_i} requires)
        if(_n_scalars GREATER 0)
          math(EXPR _s_last "${_n_scalars} - 1")
          foreach(_j RANGE ${_s_last})
            string(JSON _sname GET "${_claims}" folds ${_i} scalars ${_j} name)
            string(JSON _limbs GET "${_claims}" folds ${_i} scalars ${_j} limbs)
            if(_requires MATCHES "power_of_two\\(${_sname}\\)")
              string(APPEND _shape "_sc")
            else()
              string(APPEND _shape "_s${_limbs}")
            endif()
          endforeach()
        endif()
      elseif(_is_bv)
        set(_shape "_bv")
        set(_full_fold_${_fold}_length ${KAIRN_CROSSCHECK_MAP_LENGTH})
      elseif(_is_conv OR _is_bvconv)
        set(_shape "_conv")
        set(_quick_length ${KAIRN_CROSSCHECK_CONV_QUICK_LENGTH})
        set(_full_fold_${_fold}_cases ${KAIRN_CROSSCHECK_CONV_CASES})
        set(_full_fold_${_fold}_length ${KAIRN_CROSSCHECK_CONV_LENGTH})
        set(_full_fold_${_fold}_sampled_length ${KAIRN_CROSSCHECK_CONV_LENGTH})
      elseif(_kind0 STREQUAL "upper")
        set(_shape "_max")
      endif()
      math(EXPR _a_last "${_n_arrays} - 1")
      foreach(_j RANGE ${_a_last})
        string(JSON _limbs GET "${_claims}" folds ${_i} arrays ${_j} limbs)
        string(APPEND _shape "_${_limbs}")
      endforeach()
      # The toy formats of the full tier: the enumeration's format and length, the sampled format.
      set(_toy "${_fold_toy${_shape}}")
      if(DEFINED _fold_toy_kernel_${_fold})
        set(_toy "${_fold_toy_kernel_${_fold}}")
      endif()
      set(_error "")
      if(NOT _toy)
        string(REPLACE "_" " " _operands "${_shape}")
        set(_error "no toy format is chosen for the arrays of ${_fold} (${_operands}): add one in "
          "tests/CMakeLists.txt")
      else()
        list(GET _toy 0 _toy_enum)
        list(GET _toy 1 _toy_length)
        list(GET _toy 2 _toy_sampled)
        foreach(_f IN ITEMS ${_toy_enum} ${_toy_sampled})
          if(_f STREQUAL "-")
            continue()
          endif()
          string(REGEX REPLACE "^fp:([0-9]+):.*" "\\1" _p "${_f}")
          if(_min MATCHES "^[0-9]+$" AND _p LESS _min)
            set(_error "the toy format ${_f} of ${_fold} is below its min_precision ${_min}: "
              "choose another in tests/CMakeLists.txt")
          endif()
        endforeach()
      endif()
      string(JOIN "" _error ${_error})
      list(APPEND _full_folds ${_fold})
      set(_full_fold_${_fold}_toy "${_toy}")
      set(_full_fold_${_fold}_error "${_error}")
      set(_this_fold compiled --kernel "${_fold}" --fail-on-suspicious ${_oracle_claims_arg})
      # A map or a ball vector writes an array that may be one it reads: its requests in place
      # too, a stream of their own through every runner (crosscheck.py --inplace).
      if(_is_map OR _is_bv)
        list(APPEND _this_fold --inplace)
      endif()
      set(_full_fold_${_fold}_compiled ${_this_fold})
      foreach(_format binary64 binary32)
        set(_packed_args "")
        set(_full_fold_${_fold}_${_format}_lanes "")
        if(_packed_backend AND _compiled_packed)
          string(JSON _w ERROR_VARIABLE _no_w GET "${_claims}" folds ${_i} packed_lanes ${_format}
            ${_packed_backend})
          if(NOT _no_w)
            set(_packed_args ${_compiled_packed} --packed-lanes ${_w} --packed-count ${_quick_packed})
            set(_full_fold_${_fold}_${_format}_lanes ${_w})
          endif()
        endif()
        if(_compiled_scalar)
          set(_name crosscheck.compiled.${_fold}.${_format})
          add_test(NAME ${_name} COMMAND ${_crosscheck} ${_this_fold} --format ${_format}
            --seed "${KAIRN_CROSSCHECK_SEED}" --count "${_quick_count}"
            --max-length "${_quick_length}"
            --summary "${_summaries}/${_name}.json" ${_compiled_scalar} ${_packed_args})
          set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;compiled;fold")
        endif()
      endforeach()
    endforeach()
  endif()

  # The planted fault of the packed lanes (lanes/lane_fault.py): the packed runner built with
  # lanes/lane_fault.hpp, a copy of mul_2_2_full whose special-value select reads the mask of the
  # neighboring lane, in place of the backend's kernels. crosscheck.lanes.fault.FORMAT runs the
  # cross-check of mul_2_2_full with it on the quick tier's cases: it must pass with the
  # consecutive assignment where no register mixes a non-finite operand with finite ones (W = 2
  # and 4 on the oracle's stream) and fail, by the oracle's verdict, with the permuted one; and
  # the runner must refuse the consecutive assignment under the guard. The oracle reads the claims
  # of KAIRN_ORACLE_CLAIMS, as every other cross-check.
  if(_packed_backend AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/lanes/lane_fault.py")
    add_executable(kairn-gen-packed-runner-lane-fault "${PROJECT_SOURCE_DIR}/gen/tests/packed_runner.cpp")
    target_include_directories(kairn-gen-packed-runner-lane-fault PRIVATE
      "${PROJECT_SOURCE_DIR}/gen/tests" "${CMAKE_CURRENT_SOURCE_DIR}/lanes")
    target_compile_definitions(kairn-gen-packed-runner-lane-fault PRIVATE
      KAIRN_RUNNER_HEADER="lane_fault.hpp" KAIRN_RUNNER_TABLE="lane_fault.inc")
    target_link_libraries(kairn-gen-packed-runner-lane-fault PRIVATE kairn::kairn kairn::fma)
    target_compile_options(kairn-gen-packed-runner-lane-fault PRIVATE ${_warnings} ${_isa_option})
    foreach(_format binary64 binary32)
      set(_name crosscheck.lanes.fault.${_format})
      add_test(NAME ${_name}
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/lanes/lane_fault.py"
          --runner "$<TARGET_FILE:kairn-gen-packed-runner-lane-fault>" --format ${_format}
          --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_QUICK_CASES}"
          --summary-dir "${_summaries}/lanes" ${_oracle_claims_arg})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;compiled;lanes")
    endforeach()
  endif()

  set(_packed "no packed runners (no packed backend for this target)")
  if(_packed_backend)
    if(_isa_option)
      list(JOIN _isa_option " " _packed)
      set(_packed "packed runners for ${_packed_backend}, with ${_packed}")
    else()
      set(_packed "packed runners for ${_packed_backend}")
    endif()
  endif()
  list(JOIN _runner_labels ", " _labels)
  math(EXPR _count "${_count} - ${_n_not_checked}")
  if(_n_not_checked GREATER 0 OR _n_folds_not_checked GREATER 0)
    message(STATUS "Kairn tests: not yet cross-checked by the oracle (KAIRN_NOT_YET_CROSS_CHECKED): "
      "${_n_not_checked} kernels and ${_n_folds_not_checked} folds, tested by the generator's tier")
  else()
    message(STATUS "Kairn tests: the oracle judges every kernel and fold of the claims "
      "(KAIRN_NOT_YET_CROSS_CHECKED and KAIRN_NOT_YET_CROSS_CHECKED_FOLDS name none of them)")
  endif()
  message(STATUS "Kairn tests: cross-checks of ${_count} kernels and ${_n_folds} folds: the compiled runners ${_labels} "
    "(${_packed}), on ${KAIRN_CROSSCHECK_QUICK_CASES} cases per kernel and format in the quick "
    "tier and ${KAIRN_CROSSCHECK_CASES} in the full tier; and, in the full tier, the interpreter "
    "on ${_n_complete} complete enumerations of toy formats and ${_n_restricted} restricted ones "
    "(each with a sampled run)")
endif()

# --- The consumer checks ------------------------------------------------------------------------
#
# They build their project with this build's generator and compiler, and run its program, which
# checks the version it is given against version.hpp and runs a kernel: consume.add_subdirectory
# through consume/subproject.cmake, which also checks that Kairn, added with add_subdirectory,
# prints no notice when configured and adds no install rule unless KAIRN_INSTALL is on (and that
# both checks can fail: the notice made necessary is printed at the VERBOSE log level, and the
# option installs Kairn's headers); consume.find_package with ctest --build-and-test, after
# consume.install has installed this build tree, which needs KAIRN_INSTALL (on by default here).
set(_consume_dir "${CMAKE_CURRENT_BINARY_DIR}/consume")
set(_build_and_test --build-generator "${CMAKE_GENERATOR}" --build-project kairn_consume)
if(CMAKE_GENERATOR_PLATFORM)
  list(APPEND _build_and_test --build-generator-platform "${CMAKE_GENERATOR_PLATFORM}")
endif()
if(CMAKE_GENERATOR_TOOLSET)
  list(APPEND _build_and_test --build-generator-toolset "${CMAKE_GENERATOR_TOOLSET}")
endif()
if(CMAKE_MAKE_PROGRAM)
  list(APPEND _build_and_test --build-makeprogram "${CMAKE_MAKE_PROGRAM}")
endif()
set(_config "")
set(_build_type "")
get_property(_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(_multi_config)
  set(_config -C "$<CONFIG>")
elseif(CMAKE_BUILD_TYPE)
  set(_build_type "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()
set(_build_options --build-options "-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}" ${_build_type})
set(_run --test-command consume "${PROJECT_VERSION}")

set(_subproject "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/consume/add_subdirectory"
  "-DWORK=${_consume_dir}/add_subdirectory" "-DKAIRN_SOURCE_DIR=${PROJECT_SOURCE_DIR}"
  "-DVERSION=${PROJECT_VERSION}" "-DCXX=${CMAKE_CXX_COMPILER}" "-DGENERATOR=${CMAKE_GENERATOR}"
  "-DPLATFORM=${CMAKE_GENERATOR_PLATFORM}" "-DTOOLSET=${CMAKE_GENERATOR_TOOLSET}"
  "-DMAKE_PROGRAM=${CMAKE_MAKE_PROGRAM}")
if(_multi_config)
  list(APPEND _subproject "-DCONFIG=$<CONFIG>")
elseif(CMAKE_BUILD_TYPE)
  list(APPEND _subproject "-DBUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()
add_test(NAME consume.add_subdirectory
  COMMAND "${CMAKE_COMMAND}" ${_subproject} -P "${CMAKE_CURRENT_SOURCE_DIR}/consume/subproject.cmake")
set_tests_properties(consume.add_subdirectory PROPERTIES TIMEOUT 600)

if(KAIRN_INSTALL)
  add_test(NAME consume.install
    COMMAND "${CMAKE_COMMAND}" "-DBUILD_DIR=${PROJECT_BINARY_DIR}" "-DPREFIX=${_consume_dir}/prefix"
      "-DLICENSE=${PROJECT_SOURCE_DIR}/LICENSE" "-DLICENSE_DIR=${CMAKE_INSTALL_DATADIR}/licenses/kairn"
      "-DCONFIG=$<CONFIG>" -P "${CMAKE_CURRENT_SOURCE_DIR}/consume/install.cmake")
  set_tests_properties(consume.install PROPERTIES FIXTURES_SETUP kairn_installed)

  add_test(NAME consume.find_package
    COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
      "${CMAKE_CURRENT_SOURCE_DIR}/consume/find_package" "${_consume_dir}/find_package"
      ${_build_and_test} ${_build_options} "-DCMAKE_PREFIX_PATH=${_consume_dir}/prefix" ${_run})
  set_tests_properties(consume.find_package PROPERTIES FIXTURES_REQUIRED kairn_installed)
endif()
add_subdirectory(api)

# --- The regression cases (begin) ---------------------------------------------------------------
#
# regression.cases: the lines of tests/regression/cases.txt (the cases that found a problem, and
# those that came closest to a claim) through every compiled runner above, the generator's
# interpreter, and both runners of the public interface (api/), every form of each public kernel,
# judged by the oracle (tests/regression/run.py). A few seconds; the file says how a line is added.
if(Python3_Interpreter_FOUND AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/regression/cases.txt")
  set(_regression_args "")
  foreach(_runner _label IN ZIP_LISTS _runners _runner_labels)
    list(APPEND _regression_args --runner "${_label}=$<TARGET_FILE:${_runner}>")
  endforeach()
  list(APPEND _regression_args --interp
    --api "build=$<TARGET_FILE:kairn-api-runner>"
    --api "contract-fast=$<TARGET_FILE:kairn-api-runner-contract-fast>")
  add_test(NAME regression.cases
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/regression/run.py"
      "${CMAKE_CURRENT_SOURCE_DIR}/regression/cases.txt" ${_regression_args}
      ${_oracle_claims_arg}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(regression.cases PROPERTIES TIMEOUT 300 LABELS regression)
endif()
# --- The regression cases (end) -----------------------------------------------------------------

# --- The two tiers ------------------------------------------------------------------------------
#
# Every test of this directory and of api/ is in the quick tier, with the label quick; the full
# tier is registered in full/, with the label full. When Kairn is the top-level project, the
# CTestCustom.cmake that ctest reads at the top of the build tree leaves the full tier out of a run
# there (CTEST_CUSTOM_TESTS_IGNORE), and each tier's CTestCustom.cmake has ctest say which tier it
# runs, before the first test and after the summary (CTEST_CUSTOM_PRE_TEST, CTEST_CUSTOM_POST_TEST:
# commands, here cmake -E echo, so a message has no semicolon).
get_property(_quick_tests DIRECTORY PROPERTY TESTS)
if(_quick_tests)
  set_property(TEST ${_quick_tests} APPEND PROPERTY LABELS quick)
endif()
get_property(_api_tests DIRECTORY api PROPERTY TESTS)
list(APPEND _quick_tests ${_api_tests})
list(LENGTH _quick_tests _n_quick)

function(_kairn_ctest_custom dir left_out pre post)
  set(_echo "\\\"${CMAKE_COMMAND}\\\" -E echo")
  set(_text "# Written by tests/CMakeLists.txt when CMake runs: read by ctest in this directory.\n")
  if(left_out)
    string(APPEND _text "set(CTEST_CUSTOM_TESTS_IGNORE \${CTEST_CUSTOM_TESTS_IGNORE}\n")
    foreach(_test IN LISTS left_out)
      string(APPEND _text "  \"${_test}\"\n")
    endforeach()
    string(APPEND _text ")\n")
  endif()
  string(APPEND _text "set(CTEST_CUSTOM_PRE_TEST \"${_echo} ${pre}\")\n"
    "set(CTEST_CUSTOM_POST_TEST \"${_echo} ${post}\")\n")
  file(CONFIGURE OUTPUT "${dir}/CTestCustom.cmake" CONTENT "${_text}" @ONLY)
endfunction()

if(_full_tier)
  add_subdirectory(full)
  get_property(_full_tests DIRECTORY full PROPERTY TESTS)
  list(LENGTH _full_tests _n_full)
  set(_quick_run "ctest --test-dir ${PROJECT_BINARY_DIR}")
  set(_full_run "ctest --test-dir ${CMAKE_CURRENT_BINARY_DIR}/full")
  _kairn_ctest_custom("${PROJECT_BINARY_DIR}" "${_full_tests}"
    "Kairn tests: the quick tier, ${_n_quick} tests. The full tier, ${_n_full} tests more: ${_full_run}"
    "Kairn tests: that was the quick tier, ${_n_quick} tests. The full tier: ${_full_run}")
  _kairn_ctest_custom("${CMAKE_CURRENT_BINARY_DIR}/full" ""
    "Kairn tests: the full tier, ${_n_full} tests, those that left the quick tier: ${_quick_run}"
    "Kairn tests: that was the full tier, ${_n_full} tests")
  message(STATUS "Kairn tests: the quick tier, ${_n_quick} tests (${_quick_run}), and the full "
    "tier, ${_n_full} tests (${_full_run})")
elseif(PROJECT_IS_TOP_LEVEL)
  _kairn_ctest_custom("${PROJECT_BINARY_DIR}" ""
    "Kairn tests: the quick tier, ${_n_quick} tests. No full tier without Python 3."
    "Kairn tests: that was the quick tier, ${_n_quick} tests")
  message(STATUS "Kairn tests: the quick tier, ${_n_quick} tests; no full tier without Python 3")
else()
  message(STATUS "Kairn tests: the quick tier, ${_n_quick} tests; the full tier only when Kairn "
    "is the top-level project")
endif()
