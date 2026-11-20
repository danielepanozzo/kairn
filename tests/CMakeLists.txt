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
#   (gen/tests/packed_runner.cpp); in the full tier on more cases, and also as run by the
#   generator's interpreter on every operand of a toy format (or, where that is too many, on every
#   operand of a restricted domain and on random cases of the whole format).
# - The consumer checks (consume/): a project that uses kairn::kairn and kairn::fma through
#   add_subdirectory, and one that uses them through find_package after this build tree is
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
    set(_args check --claims gen/claims.json --claims-only)
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
# gen/tests/packed_runner.cpp the packed ones, consecutive requests one per lane. Each is built
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
#   1 1 1    dot_step_1                                   fp:3:-6:-1     166 375
#   2 2 2    dot_step_2                                   fp:4:-3:-2     226 981
#   ext a2   fold_finish_2 (two limbs, any values)        fp:5:-7:0       84 100
set(_toy_n fp:12:-30:12)
set(_toy_1_1_1_product fp:3:-6:-1)
set(_toy_2_2_2_product fp:4:-3:-2)
set(_toy_ext_a2 fp:5:-7:0)

# --- Not yet cross-checked by the oracle ------------------------------------------------------
#
# Kernels of gen/claims.json and folds of its list "folds" that the oracle does not judge yet: no
# cross-check, no enumeration of a toy format and no test of the public interface is registered for
# a name of these lists, and configuring says how many are left out. A kernel or a fold added to the
# generator with claims the oracle cannot read goes here until the oracle reads them. Since the
# folds' stage of Milestone 2 the oracle judges every claim of that stage (folds, their steps,
# finishes and bounds included; oracle/README.md). On the lists:
#
# - the maps of stage B, part 1 (architecture.md, "Maps"), and their steps: the oracle reads neither
#   the requests of written arrays nor the claim entries yet (it refuses a map, "a fold that writes
#   arrays"); the steps, whose claims it reads, are on the list with their maps until it reads them;
# - the folds of maxima of stage B, part 2 (architecture.md, "Folds of maxima"), and their kernels:
#   the oracle reads neither the claim maximum, nor finite_or_nan with if and steps, nor a fold's
#   upper entry yet;
# - the convolutions (architecture.md, "Convolutions"): the oracle reads neither requests of two
#   lengths nor the claim coefficients yet (it refuses them as folds that write arrays).
#
# Each list is written out in full here, the one place that says which (tests/brute/brute.py reads
# them as written).
set(KAIRN_NOT_YET_CROSS_CHECKED
  sub_1_1 add_entry_step_1 sub_entry_step_1 add_entry_step_2 sub_entry_step_2 scale_step_1 scale_step_2
  mul_pow2_step_1 mul_pow2_step_2 axpy_step_1 axpy_entry_step_1 axpy_step_2 axpy_entry_step_2 axpy_step_2_1
  axpy_entry_step_2_1
  norm_combine norm_step_1 norm_step_2 norm_finish_1 norm_finish_2)
set(KAIRN_NOT_YET_CROSS_CHECKED_FOLDS
  add_1 add_1_entry add_2 add_2_entry sub_1 sub_1_entry sub_2 sub_2_entry axpy_1 axpy_1_entry axpy_2 axpy_2_entry
  axpy_2_1 axpy_2_1_entry scale_1 scale_2 mul_pow2_map_1 mul_pow2_map_2
  norm_upper_1 norm_upper_2
  conv_1 conv_2)
# The kernels that no public operation calls yet and that the public interface's runner lists in
# none of its lists (api/CMakeLists.txt, api/coverage.cmake): the kernels of the folds' stage,
# whose public functions (sum, dot, the bounds as functions of n) come with BallVector. They are
# cross-checked like every kernel; the public interface has no form of them.
set(KAIRN_NOT_PUBLIC_YET
  bound_sum_1 bound_sum_2 bound_dot_1 bound_dot_2 dot_step_1 dot_step_2 sum_entry_step_1 sum_entry_step_2
  sum_fast_entry_step_2 fold_finish_1 fold_finish_2)

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

# Kernels whose intermediate values can overflow for operands far below the largest number (the
# product by the splitter), as their requirement of no intermediate overflow allows. The oracle
# counts the non-finite results of such operands as suspicious; any other kernel that returns one
# fails its cross-check (--fail-on-suspicious).
set(_intermediate_overflow split two_prod_dekker)

set(_claims_file "${PROJECT_SOURCE_DIR}/gen/claims.json")
if(Python3_Interpreter_FOUND AND EXISTS "${_claims_file}")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_claims_file}")
  file(READ "${_claims_file}" _claims)
  string(JSON _count LENGTH "${_claims}" kernels)
  math(EXPR _last "${_count} - 1")
  set(_driver "${CMAKE_CURRENT_SOURCE_DIR}/crosscheck.cmake")
  set(_crosscheck "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/crosscheck.py")
  set(_summaries "${CMAKE_CURRENT_BINARY_DIR}/crosscheck")
  set(_common "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}")
  set(_random "-DCOUNT=${KAIRN_CROSSCHECK_CASES}" "-DSEED=${KAIRN_CROSSCHECK_SEED}")
  set(_random_args --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_CASES}")
  set(_random_quick_args --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_QUICK_CASES}")
  # Every compiled runner, as --runner LABEL EXECUTABLE for crosscheck.py.
  set(_compiled "")
  foreach(_runner _label IN ZIP_LISTS _runners _runner_labels)
    list(APPEND _compiled --runner "${_label}" "$<TARGET_FILE:${_runner}>")
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
      if(_input IN_LIST _ball_radii)
        continue()
      elseif(_type STREQUAL "mask")
        set(_role m)
      elseif(_input IN_LIST _ball_centers)
        set(_role "b${_limbs}")
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
      if(_value MATCHES "\\*")
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
    set(_this_compiled compiled --kernel "${_kernel}" ${_suspicious_arg})

    # The interpreter, on every operand of the toy format, or of a restricted domain of it and
    # on random cases of all of it.
    set(_toy "${_toy${_shape}}")
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

    # The compiled runners, on random cases of every stratum.
    if(_compiled)
      foreach(_format binary64 binary32)
        set(_name crosscheck.compiled.${_kernel}.${_format})
        add_test(NAME ${_name} COMMAND ${_crosscheck} ${_this_compiled} --format ${_format}
          ${_random_quick_args} --summary "${_summaries}/${_name}.json" ${_compiled})
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
      set(_shape "")
      math(EXPR _a_last "${_n_arrays} - 1")
      foreach(_j RANGE ${_a_last})
        string(JSON _limbs GET "${_claims}" folds ${_i} arrays ${_j} limbs)
        string(APPEND _shape "_${_limbs}")
      endforeach()
      # The toy formats of the full tier: the enumeration's format and length, the sampled format.
      set(_toy "${_fold_toy${_shape}}")
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
      set(_this_fold compiled --kernel "${_fold}" --fail-on-suspicious)
      set(_full_fold_${_fold}_compiled ${_this_fold})
      foreach(_format binary64 binary32)
        set(_packed_args "")
        set(_full_fold_${_fold}_${_format}_lanes "")
        if(_packed_backend AND _compiled_packed)
          string(JSON _w ERROR_VARIABLE _no_w GET "${_claims}" folds ${_i} packed_lanes ${_format}
            ${_packed_backend})
          if(NOT _no_w)
            set(_packed_args ${_compiled_packed} --packed-lanes ${_w}
              --packed-count ${KAIRN_CROSSCHECK_FOLD_PACKED_QUICK_CASES})
            set(_full_fold_${_fold}_${_format}_lanes ${_w})
          endif()
        endif()
        if(_compiled_scalar)
          set(_name crosscheck.compiled.${_fold}.${_format})
          add_test(NAME ${_name} COMMAND ${_crosscheck} ${_this_fold} --format ${_format}
            --seed "${KAIRN_CROSSCHECK_SEED}" --count "${KAIRN_CROSSCHECK_FOLD_QUICK_CASES}"
            --max-length "${KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH}"
            --summary "${_summaries}/${_name}.json" ${_compiled_scalar} ${_packed_args})
          set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;compiled;fold")
        endif()
      endforeach()
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
  endif()
  message(STATUS "Kairn tests: cross-checks of ${_count} kernels and ${_n_folds} folds: the compiled runners ${_labels} "
    "(${_packed}), on ${KAIRN_CROSSCHECK_QUICK_CASES} cases per kernel and format in the quick "
    "tier and ${KAIRN_CROSSCHECK_CASES} in the full tier; and, in the full tier, the interpreter "
    "on ${_n_complete} complete enumerations of toy formats and ${_n_restricted} restricted ones "
    "(each with a sampled run)")
endif()

# --- The consumer checks ------------------------------------------------------------------------
#
# They build their project with ctest --build-and-test, with this build's generator and compiler,
# and run its program, which checks the version it is given against version.hpp and runs a kernel.
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

add_test(NAME consume.add_subdirectory
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${CMAKE_CURRENT_SOURCE_DIR}/consume/add_subdirectory" "${_consume_dir}/add_subdirectory"
    ${_build_and_test} ${_build_options} "-DKAIRN_SOURCE_DIR=${PROJECT_SOURCE_DIR}" ${_run})

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
