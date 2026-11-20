# The tests of the public interface (include/kairn/*.hpp), with ctest labels "api":
#
# - api.constexpr: static_asserts of everything constexpr, and the same expressions at run time.
# - api.oracle.KERNEL.FORMAT: the oracle judges, against KERNEL's claims, every public operation
#   that calls KERNEL (runner.cpp), computed through the constructors, operators and functions a
#   client calls, on random binary64 and binary32 cases (in the extended domain, infinities, NaN
#   and the special balls included, for the kernels that have it); with this build's flags and
#   with contraction forced on, two runners on the same cases, and the debug build's runner
#   (flags/) on the first form of each kernel. full.api.oracle.KERNEL.FORMAT, in the full tier
#   (../full/), does the same on more cases, and full.api.flags.oracle.KERNEL.FORMAT every form
#   through the runner of every flag set of flags/.
# - api.oracle.coverage: every kernel of gen/claims.json is reached by a public form of the
#   runner, or is a building block, or is an entry kernel on the runner's short list of those not
#   public yet; no entry kernel is a building block; and the lists below agree.
# - api.boundary.*: a product the program computes and passes in gives the result of the same
#   operation on the rounded product, under each contraction setting; with the generated guard
#   taken out of a copy of the headers, it must not where the compiler fuses.
# - api.environment: environment_ok() and self_test() pass in the default environment and detect
#   a changed rounding mode and flush-to-zero.
# - api.self_test.unsafe.*: with Clang, a build whose flags break Kairn without a macro to show it,
#   which self_test() must detect.
# - api.flags.debug.*: self_test() and constexpr.cpp in the debug build of flags/.
# - api.checks.*: the checks of KAIRN_CHECKS, which must stop the program under a changed rounding
#   mode or flush to zero, with the environment's message, and on an operand that is not
#   canonical, and let the rest through; with a handler that returns, every operation goes on.
# - api.reject.*: what must not compile: rejected flags, UNVERIFIED operations without the
#   marker, and with KAIRN_CHECKS constant expressions that the checks refuse (each with a control
#   that compiles).
# - api.k1.zero_cost: the code of Expansion<double, 1> against that of double (k1/zero_cost.py).
# - api.example.*: the documentation's examples (docs/examples/cpp/), which check their own output;
#   api.example.accurate_sums.* also compares it with the text its tutorial shows.

set(_api_include "${PROJECT_SOURCE_DIR}/include")
if(_msvc_style)
  set(_api_warnings /W4 /WX)
else()
  set(_api_warnings -Wall -Wextra -Wpedantic -Werror)
endif()

function(_kairn_api_program target source)
  add_executable(${target} "${source}")
  target_link_libraries(${target} PRIVATE kairn::kairn kairn::fma)
  target_compile_options(${target} PRIVATE ${_api_warnings} ${ARGN})
endfunction()

# --- Compile time -----------------------------------------------------------------------------
_kairn_api_program(kairn-api-constexpr constexpr.cpp)
add_test(NAME api.constexpr COMMAND kairn-api-constexpr)

# --- The public interface against the oracle --------------------------------------------------
#
# The building blocks, which no public operation computes on its own, and the entry kernels that no
# public operation calls yet; runner.cpp lists the same, with why.
set(_api_internal two_sum fast_two_sum two_prod split two_prod_dekker radd rmul)
set(_api_not_public ball_add_1 ball_sub_1 ball_mul_1 ball_scale_1 ball_add_2 ball_sub_2 ball_mul_2 ball_scale_2)
set(KAIRN_API_CASES 10000 CACHE STRING
  "Random cases per kernel, format and form of the public interface judged by the oracle, in the full tier")
set(KAIRN_API_QUICK_CASES 2000 CACHE STRING
  "Random cases per kernel, format and form of the public interface judged by the oracle, in the quick tier")
set(KAIRN_API_SEED 1 CACHE STRING "Seed of the random cases of the public interface's tests")

_kairn_api_program(kairn-api-runner runner.cpp)
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contract /fp:contract)
elseif(_msvc_style)
  set(_api_contract /clang:-ffp-contract=fast)
else()
  # At -O2, like the contraction runners of the cross-checks (tests/CMakeLists.txt says why).
  set(_api_contract -ffp-contract=fast -O2)
endif()
_kairn_api_program(kairn-api-runner-contract-fast runner.cpp ${_api_contract})

# Each test runs the runners, the one with the build's flags and the one with contraction forced
# on (and the debug build's, below), on the same requests, generated once (pipeline.cmake). The
# quick tier's KAIRN_API_QUICK_CASES are at least 1000, the length of stream at which a form that
# computes only some lines of its kernel must have computed one (runner.cpp); 2000, because with
# 1000 three more of the faults planted in the kernels that the full tier caught went unseen
# (docs/developer/testing.md, "Time").
set(_api_claims "${PROJECT_SOURCE_DIR}/gen/claims.json")
# --- The flag sets (flags/) -------------------------------------------------------------------
#
# flags/ builds the public interface's runner and programs once per flag set of
# docs/developer/testing.md ("Flag sets"), and the kernels' runners for two of them, each with
# exactly the options of its set. In the quick tier the debug build's runner joins the two above in
# api.oracle.*, on the first form of each kernel only (FIRST_FORM): built without optimization and
# with the checks, it takes two to three times as long. The full tier runs every form of every
# set's runner on KAIRN_API_QUICK_CASES cases (full.api.flags.oracle.*) and the kernels' runners
# in its cross-checks (../full/CMakeLists.txt, from the variables _flags_* passed up below).
add_subdirectory(flags)
set(_api_runners "build|$<TARGET_FILE:kairn-api-runner>|contract-fast|$<TARGET_FILE:kairn-api-runner-contract-fast>")
string(APPEND _api_runners "|debug|$<TARGET_FILE:kairn-api-runner-debug>")
set(_flags_runners "")
foreach(_set IN LISTS _flags_names)
  list(APPEND _flags_runners "${_set}|$<TARGET_FILE:kairn-api-runner-${_set}>")
endforeach()
list(JOIN _flags_runners "|" _flags_runners)
set(_flags_names ${_flags_names} PARENT_SCOPE)
set(_flags_gen_runners ${_flags_gen_runners} PARENT_SCOPE)
set(_flags_gen_labels ${_flags_gen_labels} PARENT_SCOPE)
# --- The end of the flag sets' runners ---------------------------------------------------------
if(Python3_Interpreter_FOUND AND EXISTS "${_api_claims}")
  set(_api_common "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}"
    "-DRUNNERS=${_api_runners}" "-DFIRST_FORM=debug" "-DSEED=${KAIRN_API_SEED}")
  file(READ "${_api_claims}" _api_json)
  string(JSON _api_count LENGTH "${_api_json}" kernels)
  math(EXPR _api_last "${_api_count} - 1")
  set(_api_mapped "")
  foreach(_i RANGE ${_api_last})
    string(JSON _kernel GET "${_api_json}" kernels ${_i} name)
    if(_kernel IN_LIST _api_internal OR _kernel IN_LIST _api_not_public)
      continue()
    endif()
    list(APPEND _api_mapped ${_kernel})
    foreach(_format binary64 binary32)
      set(_name api.oracle.${_kernel}.${_format})
      add_test(NAME ${_name}
        COMMAND "${CMAKE_COMMAND}" ${_api_common} "-DKERNEL=${_kernel}" "-DFORMAT=${_format}"
          "-DCOUNT=${KAIRN_API_QUICK_CASES}" "-DSUMMARY_DIR=${CMAKE_CURRENT_BINARY_DIR}/oracle"
          -P "${CMAKE_CURRENT_SOURCE_DIR}/pipeline.cmake")
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle")
    endforeach()
  endforeach()
  # For ../full/CMakeLists.txt, which registers the same on KAIRN_API_CASES cases, and every form of
  # the flag sets' runners on KAIRN_API_QUICK_CASES.
  set(_api_oracle_kernels ${_api_mapped} PARENT_SCOPE)
  set(_api_oracle_common ${_api_common} PARENT_SCOPE)
  set(_api_flags_common "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}"
    "-DRUNNERS=${_flags_runners}" "-DSEED=${KAIRN_API_SEED}" PARENT_SCOPE)
  add_test(NAME api.oracle.coverage
    COMMAND "${CMAKE_COMMAND}" "-DRUNNER=$<TARGET_FILE:kairn-api-runner>" "-DCLAIMS=${_api_claims}"
      "-DKERNELS=${PROJECT_SOURCE_DIR}/gen/kernels" "-DINTERNAL=${_api_internal}"
      "-DNOT_PUBLIC=${_api_not_public}" -P "${CMAKE_CURRENT_SOURCE_DIR}/coverage.cmake")
  set_tests_properties(api.oracle.coverage PROPERTIES LABELS "api;oracle")
  list(LENGTH _api_mapped _n)
  list(LENGTH _flags_names _n_flags)
  message(STATUS "Kairn tests: the public interface of ${_n} kernels against the oracle, with 2 runners "
    "and the debug build's on the first form of each, and in the full tier the runners of ${_n_flags} flag sets")
endif()

# --- Products of the program passed into Kairn ------------------------------------------------
#
# boundary.cpp, under the build's flags and each contraction setting that matters to the compiler:
# with the guard, every form must agree with the same operation on the rounded product
# (api.boundary.*). Built again with the guard taken out (api.boundary.unguarded.*), some form
# must differ where the compiler was measured to fuse across statements, so that the first test
# cannot pass for want of a compiler that fuses; elsewhere that build only reports.
#
# The guard is an operation of the generated kernels (rule R3), emitted as
# `__builtin_is_constant_evaluated() ? a : a + 0.0`. The unguarded build compiles against a copy of
# the headers in which every such line of include/kairn/gen/scalar.hpp keeps only `a`: the
# generator has no switch for it, and needs none for anything but this test. The copy is made at
# configure time, and fails the configuration if it finds no guard to take out or leaves one.
set(_api_unguarded "${CMAKE_CURRENT_BINARY_DIR}/unguarded-fixture")
set(_api_scalar "${_api_include}/kairn/gen/scalar.hpp")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_api_scalar}")
file(REMOVE_RECURSE "${_api_unguarded}")
file(COPY "${_api_include}/kairn" DESTINATION "${_api_unguarded}")
file(READ "${_api_scalar}" _api_text)
string(REGEX MATCHALL "__builtin_is_constant_evaluated\\(\\) \\? ([A-Za-z0-9_]+) : [A-Za-z0-9_]+ \\+ 0\\.0f?;"
  _api_guards "${_api_text}")
list(LENGTH _api_guards _api_n)
string(REGEX REPLACE "__builtin_is_constant_evaluated\\(\\) \\? ([A-Za-z0-9_]+) : ([A-Za-z0-9_]+) \\+ 0\\.0f?;"
  "\\1;" _api_text "${_api_text}")
string(REGEX MATCHALL "\\+ 0\\.0f?;" _api_left "${_api_text}")
if(_api_n EQUAL 0 OR _api_left)
  message(FATAL_ERROR "tests/api: could not take the guard out of ${_api_scalar} (${_api_n} found)")
endif()
file(WRITE "${_api_unguarded}/kairn/gen/scalar.hpp" "${_api_text}")
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contraction "" "" fp-precise /fp:precise fp-contract /fp:contract fp-strict /fp:strict)
elseif(_msvc_style)
  set(_api_contraction "" "" fp-strict /fp:strict fp-precise /fp:precise fp-contract /fp:contract
    contract-fast /clang:-ffp-contract=fast)
else()
  set(_api_contraction "" "" contract-off -ffp-contract=off contract-on -ffp-contract=on
    contract-fast -ffp-contract=fast)
endif()
list(LENGTH _api_contraction _n)
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _api_contraction ${_i} _variant)
  list(GET _api_contraction ${_j} _option)
  if(_variant STREQUAL "")
    set(_suffix "")
  else()
    set(_suffix ".${_variant}")
  endif()
  # Where the unguarded build was measured to fuse: GCC by default (it contracts across statements
  # in C++) and with =fast; Clang with =fast on AArch64 (every two-limb form); MSVC with
  # /fp:contract. Clang 18 on x86-64 fused nothing without the guard, and clang-cl was not
  # measured: their builds only report.
  set(_fuses OFF)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND (_variant STREQUAL "" OR _variant STREQUAL "contract-fast"))
    set(_fuses ON)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style AND _variant STREQUAL "contract-fast"
         AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
    set(_fuses ON)
  elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" AND _variant STREQUAL "fp-contract")
    set(_fuses ON)
  endif()
  string(REPLACE "." "-" _target_suffix "${_suffix}")
  # At -O2, where Clang was measured to fuse every form without the guard (at -O3 fewer); MSVC's
  # Release is /O2 already.
  set(_level "")
  if(NOT _msvc_style)
    set(_level -O2)
  endif()
  _kairn_api_program(kairn-api-boundary${_target_suffix} boundary.cpp ${_level} ${_option})
  add_test(NAME api.boundary${_suffix} COMMAND kairn-api-boundary${_target_suffix} --expect none)
  add_executable(kairn-api-boundary-unguarded${_target_suffix} boundary.cpp)
  target_include_directories(kairn-api-boundary-unguarded${_target_suffix} BEFORE PRIVATE "${_api_unguarded}")
  target_link_libraries(kairn-api-boundary-unguarded${_target_suffix} PRIVATE kairn::fma)
  target_compile_features(kairn-api-boundary-unguarded${_target_suffix} PRIVATE cxx_std_20)
  target_compile_options(kairn-api-boundary-unguarded${_target_suffix} PRIVATE ${_api_warnings} ${_level} ${_option})
  target_compile_definitions(kairn-api-boundary-unguarded${_target_suffix} PRIVATE KAIRN_TEST_UNGUARDED_COPY)
  if(_fuses)
    add_test(NAME api.boundary.unguarded${_suffix} COMMAND kairn-api-boundary-unguarded${_target_suffix} --expect some)
  else()
    add_test(NAME api.boundary.unguarded${_suffix} COMMAND kairn-api-boundary-unguarded${_target_suffix} --expect report)
  endif()
  set_tests_properties(api.boundary${_suffix} api.boundary.unguarded${_suffix} PROPERTIES LABELS "api;boundary")
endforeach()

# --- The environment and the self-test --------------------------------------------------------
_kairn_api_program(kairn-api-environment environment.cpp)
add_test(NAME api.environment COMMAND kairn-api-environment)

# Clang has no macro for these flag sets, so config.hpp cannot reject them, and the self-test must
# catch them at run time. Each is built only if it compiles here (Clang 18 defines __FAST_MATH__ for
# -ffp-model=fast, which config.hpp rejects), and only where the oracle found that it breaks the
# kernels: -fno-signed-zeros with -ffp-contract=fast breaks x * y with Apple clang 21 on AArch64,
# where an opaque product is folded back into a plain one and contracted. With Clang 18 it breaks
# nothing, on x86-64 and on AArch64 Linux alike (there, 4 000 cases of each of eight kernels pass
# the oracle at -O2 and -O3), and the self-test then rightly passes: the case is registered for
# Apple clang only. A later Clang on AArch64 Linux has not been measured.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style)
  include(CheckCXXSourceCompiles)
  include(CMakePushCheckState)
  set(_api_unsafe
    reassociation "-O2 -fassociative-math -fno-signed-zeros -fno-trapping-math"
    fp-model-fast "-O2 -ffp-model=fast")
  if(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
    list(APPEND _api_unsafe signed-zeros-contraction "-O2 -fno-signed-zeros -ffp-contract=fast")
  endif()
  list(LENGTH _api_unsafe _n)
  math(EXPR _last "${_n} - 1")
  get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
  if(NOT _fma)
    set(_fma "")
  endif()
  list(JOIN _fma " " _fma_text)
  foreach(_i RANGE 0 ${_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _api_unsafe ${_i} _label)
    list(GET _api_unsafe ${_j} _flags_text)
    separate_arguments(_flags UNIX_COMMAND "${_flags_text}")
    cmake_push_check_state(RESET)
    set(CMAKE_REQUIRED_INCLUDES "${_api_include}")
    set(CMAKE_REQUIRED_FLAGS "-std=c++20 ${_flags_text} ${_fma_text}")
    set(CMAKE_REQUIRED_QUIET ON)
    check_cxx_source_compiles("#include <kairn/kairn.hpp>\nint main() { return 0; }\n" KAIRN_API_UNSAFE_${_i})
    cmake_pop_check_state()
    if(KAIRN_API_UNSAFE_${_i})
      add_executable(kairn-api-unsafe-${_label} selftest_unsafe.cpp)
      target_link_libraries(kairn-api-unsafe-${_label} PRIVATE kairn::kairn kairn::fma)
      target_compile_options(kairn-api-unsafe-${_label} PRIVATE ${_flags})
      add_test(NAME api.self_test.unsafe.${_label} COMMAND kairn-api-unsafe-${_label})
      set_tests_properties(api.self_test.unsafe.${_label} PROPERTIES LABELS api)
    endif()
  endforeach()
endif()

# --- The debug build and the checks of KAIRN_CHECKS -------------------------------------------
#
# api.flags.debug.self_test: kairn::self_test() and kairn::environment_ok() compiled as the debug
# build of flags/ (runner.cpp --self-test), which must pass; api.flags.debug.constexpr:
# constexpr.cpp built so, with the checks. The full tier registers the same for the other flag
# sets (../full/).
#
# The checks of KAIRN_CHECKS (checks.cpp, run by checks.cmake), in the debug build
# (api.checks.debug.*) and with the build's own flags and KAIRN_CHECKS defined to 1
# (api.checks.release.*): .default, in the default environment every operation runs and so does
# every operand the checks must accept; .rounding, under each directed rounding mode
# environment_ok() is false and every operation stops the program with Kairn's message; .flush, the
# same under flush to zero (FTZ and DAZ on x86-64, FZ on AArch64); .operands, every operand that is
# not canonical, and every negative radius, stops the program with its message.
# api.checks.handler: a KAIRN_ENVIRONMENT_FAILURE of the program's own is called instead
# (checks_handler.cpp).
add_test(NAME api.flags.debug.self_test COMMAND kairn-api-runner-debug --self-test)
add_test(NAME api.flags.debug.constexpr COMMAND kairn-api-constexpr-debug)
set_tests_properties(api.flags.debug.self_test api.flags.debug.constexpr PROPERTIES
  TIMEOUT 120 LABELS "api;flags")
_kairn_api_program(kairn-api-checks-release checks.cpp)
target_compile_definitions(kairn-api-checks-release PRIVATE KAIRN_CHECKS=1)
set(_api_expect_flush OFF)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64|aarch64|arm64|ARM64)$")
  set(_api_expect_flush ON)
endif()
foreach(_build debug release)
  foreach(_group default rounding flush operands)
    add_test(NAME api.checks.${_build}.${_group}
      COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-api-checks-${_build}>" "-DGROUP=${_group}"
        "-DEXPECT_FLUSH=${_api_expect_flush}" -P "${CMAKE_CURRENT_SOURCE_DIR}/checks.cmake")
    set_tests_properties(api.checks.${_build}.${_group} PROPERTIES TIMEOUT 300 LABELS "api;checks")
  endforeach()
endforeach()
add_test(NAME api.checks.handler COMMAND kairn-api-checks-handler)
set_tests_properties(api.checks.handler PROPERTIES TIMEOUT 120 LABELS "api;checks")
# --- The end of the debug build and the checks -------------------------------------------------

# --- What must not compile --------------------------------------------------------------------
# The compilations below run the compiler directly, with the build's own flags and kairn::fma's.
get_target_property(_api_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
if(NOT _api_fma)
  set(_api_fma "")
endif()
separate_arguments(_api_cxx_flags NATIVE_COMMAND "${CMAKE_CXX_FLAGS}")
list(PREPEND _api_fma ${_api_cxx_flags})
if(_msvc_style)
  set(_api_style msvc)
else()
  set(_api_style gnu)
endif()
list(JOIN _api_fma "|" _api_fma_bars)
set(_api_reject_common "-DCXX=${CMAKE_CXX_COMPILER}" "-DSTYLE=${_api_style}" "-DINCLUDE=${_api_include}"
  "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/reject.cpp" "-DCOMMON=${_api_fma_bars}")
if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
  list(APPEND _api_reject_common "-DSYSROOT=${CMAKE_OSX_SYSROOT}")
endif()

function(_kairn_api_reject name case expect)
  add_test(NAME api.reject.${name}
    COMMAND "${CMAKE_COMMAND}" ${_api_reject_common} "-DCASE=${case}" "-DEXPECT=${expect}" ${ARGN}
      -P "${CMAKE_CURRENT_SOURCE_DIR}/compile_fail.cmake")
  set_tests_properties(api.reject.${name} PROPERTIES LABELS "api;reject")
endfunction()

# Compiler flags (docs/developer/design/phase0/environment.md, "Compiler flags").
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  _kairn_api_reject(fp_fast 0 "Kairn does not work with /fp:fast" "-DOPTIONS=/fp:fast")
elseif(NOT _msvc_style)
  _kairn_api_reject(fast_math 0 "Kairn does not work with -ffast-math" "-DOPTIONS=-ffast-math")
  _kairn_api_reject(finite_math_only 0 "Kairn does not work with -ffinite-math-only" "-DOPTIONS=-ffinite-math-only")
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    _kairn_api_reject(associative_math 0 "Kairn does not work with -fassociative-math"
      "-DOPTIONS=-fassociative-math|-fno-signed-zeros|-fno-trapping-math")
    _kairn_api_reject(unsafe_math 0 "Kairn does not work with -fassociative-math"
      "-DOPTIONS=-funsafe-math-optimizations")
    _kairn_api_reject(no_signed_zeros 0 "Kairn does not work with -fno-signed-zeros" "-DOPTIONS=-fno-signed-zeros")
    _kairn_api_reject(reciprocal_math 0 "Kairn does not work with -freciprocal-math" "-DOPTIONS=-freciprocal-math")
  endif()
endif()

# UNVERIFIED operations written without the marker, compiled against a copy of the headers in which
# every kernel is marked unverified (compile_fail.cmake), so that the mechanism is tested whatever
# gen/claims.json says today. Where the compiler explains, the message names the concept whose
# constraint failed; Clang does not for a unary operator.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_unmarked "constraint")
else()
  set(_api_unmarked "proof_checked|invalid argument type")
endif()
foreach(_case_name IN ITEMS 1:sub_2_2_full 2:lt_2_2 3:neg_2 4:to_down_2 5:add_1_1 6:ball_add_2_full
                            7:sub_2_2_full_assign 8:mul_pow2_2_full 9:ball_scale_2_full 10:traits_constant
                            12:to_nearest_2_narrowing 13:make_2 14:ball_make_2)
  string(REPLACE ":" ";" _pair "${_case_name}")
  list(GET _pair 0 _case)
  list(GET _pair 1 _name)
  set(_expect "${_api_unmarked}")
  if(_name STREQUAL "traits_constant")
    set(_expect "unit")
  endif()
  _kairn_api_reject(unverified.${_name} ${_case} "${_expect}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/${_name}")
endforeach()
# One kernel unverified, the others proved: the operation must not compile through a conversion to
# another, proved kernel (x + a as x + Expansion(a), a scaling as a product with a point ball).
foreach(_case_name IN ITEMS 20:add_2_1_full:limb 21:add_2_1_full:one_limb 22:sub_1_2_full:limb
                            23:mul_2_1_full:limb 24:ball_scale_2_full:limb 25:ball_make_2:point
                            26:lt_2_1:limb)
  string(REPLACE ":" ";" _triple "${_case_name}")
  list(GET _triple 0 _case)
  list(GET _triple 1 _kernel)
  list(GET _triple 2 _what)
  _kairn_api_reject(unverified_only.${_kernel}.${_what} ${_case} "${_api_unmarked}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/only-${_kernel}-${_what}"
    "-DUNVERIFIED_ONLY=${_kernel}")
endforeach()
_kairn_api_reject(checks.from_limbs_not_canonical 11 "constant|constexpr")
_kairn_api_reject(checks.operator_not_canonical 15 "constant|constexpr")
_kairn_api_reject(checks.ball_negative_radius 16 "constant|constexpr")

# --- One limb against T -----------------------------------------------------------------------
if(Python3_Interpreter_FOUND)
  set(_api_k1 "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/k1/zero_cost.py" --cxx "${CMAKE_CXX_COMPILER}"
    --include "${_api_include}" --workdir "${CMAKE_CURRENT_BINARY_DIR}/k1")
  set(_api_k1_flags "${_api_fma}")
  if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
    list(APPEND _api_k1_flags -isysroot "${CMAKE_OSX_SYSROOT}")
  endif()
  list(JOIN _api_k1_flags " " _api_k1_flags)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    list(APPEND _api_k1 --msvc)
  endif()
  if(NOT _msvc_style OR CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    add_test(NAME api.k1.zero_cost COMMAND ${_api_k1} "--flags=${_api_k1_flags}")
    set_tests_properties(api.k1.zero_cost PROPERTIES LABELS api)
  endif()
endif()

# --- The documentation's examples -------------------------------------------------------------
_kairn_api_program(kairn-example-first-steps "${PROJECT_SOURCE_DIR}/docs/examples/cpp/first_steps.cpp")
add_test(NAME api.example.first_steps COMMAND kairn-example-first-steps)
# The examples of "Choosing T and k" and "Troubleshooting" in Getting started; the second changes
# the rounding mode and flush-to-zero, and checks the messages the page quotes.
_kairn_api_program(kairn-example-choosing "${PROJECT_SOURCE_DIR}/docs/examples/cpp/choosing.cpp")
add_test(NAME api.example.choosing COMMAND kairn-example-choosing)
_kairn_api_program(kairn-example-troubleshooting "${PROJECT_SOURCE_DIR}/docs/examples/cpp/troubleshooting.cpp")
add_test(NAME api.example.troubleshooting COMMAND kairn-example-troubleshooting)
set_tests_properties(api.example.first_steps api.example.choosing api.example.troubleshooting
  PROPERTIES LABELS "api;example")

# The tutorial's program prints the same text on every platform and under every contraction
# setting (its data are chosen so that even its double loops give one answer), and the tutorial
# shows that text: it is built with the build's flags and once per contraction setting, as
# api.boundary.* is, and each build's output is compared with accurate_sums.txt.
list(LENGTH _api_contraction _n)
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _api_contraction ${_i} _variant)
  list(GET _api_contraction ${_j} _option)
  if(_variant STREQUAL "")
    set(_suffix "")
  else()
    set(_suffix ".${_variant}")
  endif()
  string(REPLACE "." "-" _target_suffix "${_suffix}")
  _kairn_api_program(kairn-example-accurate-sums${_target_suffix}
    "${PROJECT_SOURCE_DIR}/docs/examples/cpp/accurate_sums.cpp" ${_option})
  add_test(NAME api.example.accurate_sums${_suffix}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-accurate-sums${_target_suffix}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/accurate_sums.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.accurate_sums${_suffix} PROPERTIES LABELS "api;example")
endforeach()
set_tests_properties(api.constexpr api.environment PROPERTIES LABELS api)

# Every test here is in the quick tier (../CMakeLists.txt, "The two tiers").
get_property(_api_tests DIRECTORY PROPERTY TESTS)
set_property(TEST ${_api_tests} APPEND PROPERTY LABELS quick)
