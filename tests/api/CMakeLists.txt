# The tests of the public interface (include/kairn/*.hpp), with ctest labels "api":
#
# - api.constexpr: static_asserts of everything constexpr, and the same expressions at run time.
# - api.oracle.KERNEL.FORMAT[.contract-fast]: the oracle judges, against KERNEL's claims, every
#   public operation that must satisfy them (runner.cpp), computed through the operators and
#   functions a client calls, on random binary64 and binary32 cases; once with this build's flags
#   and once with contraction forced on.
# - api.oracle.coverage: every kernel of gen/claims.json is mapped to a public operation by the
#   runner or listed by it as internal, and the list below agrees.
# - api.environment: environment_ok() and self_test() pass in the default environment and detect
#   a changed rounding mode and flush-to-zero.
# - api.self_test.unsafe.*: with Clang, a build whose flags break Kairn without a macro to show it,
#   which self_test() must detect.
# - api.reject.*: what must not compile: rejected flags, and UNVERIFIED operations without the
#   marker (each with a control that compiles).
# - api.k1.zero_cost: the code of Expansion<double, 1> against that of double (k1/zero_cost.py).
# - api.example.*: the documentation's examples (docs/examples/cpp/), which check their own output.

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
# The kernels that no public operation computes on its own; runner.cpp lists the same, with why.
set(_api_internal two_sum fast_two_sum two_prod split two_prod_dekker radd rmul)
set(KAIRN_API_CASES 10000 CACHE STRING
  "Random cases per kernel, format and form of the public interface judged by the oracle")
set(KAIRN_API_SEED 1 CACHE STRING "Seed of the random cases of the public interface's tests")

_kairn_api_program(kairn-api-runner runner.cpp)
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contract /fp:contract)
elseif(_msvc_style)
  set(_api_contract /clang:-ffp-contract=fast)
else()
  set(_api_contract -ffp-contract=fast)
endif()
_kairn_api_program(kairn-api-runner-contract-fast runner.cpp ${_api_contract})

set(_api_claims "${PROJECT_SOURCE_DIR}/gen/claims.json")
if(Python3_Interpreter_FOUND AND EXISTS "${_api_claims}")
  file(READ "${_api_claims}" _api_json)
  string(JSON _api_count LENGTH "${_api_json}" kernels)
  math(EXPR _api_last "${_api_count} - 1")
  set(_api_mapped "")
  foreach(_i RANGE ${_api_last})
    string(JSON _kernel GET "${_api_json}" kernels ${_i} name)
    if(_kernel IN_LIST _api_internal)
      continue()
    endif()
    list(APPEND _api_mapped ${_kernel})
    foreach(_variant "" contract-fast)
      if(_variant STREQUAL "")
        set(_runner kairn-api-runner)
        set(_suffix "")
      else()
        set(_runner kairn-api-runner-${_variant})
        set(_suffix ".${_variant}")
      endif()
      foreach(_format binary64 binary32)
        set(_name api.oracle.${_kernel}.${_format}${_suffix})
        add_test(NAME ${_name}
          COMMAND "${CMAKE_COMMAND}" "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}"
            "-DRUNNER=$<TARGET_FILE:${_runner}>" "-DKERNEL=${_kernel}" "-DFORMAT=${_format}"
            "-DCOUNT=${KAIRN_API_CASES}" "-DSEED=${KAIRN_API_SEED}"
            "-DSUMMARY_DIR=${CMAKE_CURRENT_BINARY_DIR}/oracle${_suffix}"
            -P "${CMAKE_CURRENT_SOURCE_DIR}/pipeline.cmake")
        if(_variant STREQUAL "")
          set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle")
        else()
          set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle;contraction")
        endif()
      endforeach()
    endforeach()
  endforeach()
  add_test(NAME api.oracle.coverage
    COMMAND "${CMAKE_COMMAND}" "-DRUNNER=$<TARGET_FILE:kairn-api-runner>" "-DMAPPED=${_api_mapped}"
      "-DINTERNAL=${_api_internal}" -P "${CMAKE_CURRENT_SOURCE_DIR}/coverage.cmake")
  set_tests_properties(api.oracle.coverage PROPERTIES LABELS "api;oracle")
  list(LENGTH _api_mapped _n)
  message(STATUS "Kairn tests: the public interface of ${_n} kernels against the oracle, with 2 runners")
endif()

# --- Products of the program passed into Kairn ------------------------------------------------
#
# boundary.cpp, under the build's flags and each contraction setting that matters to the compiler:
# with the guard, every form must agree with the same operation on the rounded product
# (api.boundary.*). Built again with the guard turned off (api.boundary.unguarded.*), x + a * b
# must differ where the compiler was measured to fuse across statements, so that the first test
# cannot pass for want of a compiler that fuses; elsewhere that build only reports.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contraction "" "" fp-precise /fp:precise fp-contract /fp:contract fp-strict /fp:strict)
elseif(_msvc_style)
  set(_api_contraction "" "" fp-strict /fp:strict fp-precise /fp:precise fp-contract /fp:contract
    contract-fast /clang:-ffp-contract=fast)
else()
  set(_api_contraction "" "" contract-off -ffp-contract=off contract-on -ffp-contract=on
    contract-fast -ffp-contract=fast)
endif()
set(_api_aarch64 OFF)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
  set(_api_aarch64 ON)
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
  # Where the unguarded build was measured to fuse x + a * b: GCC by default (it contracts across
  # statements in C++) and with =fast, Clang on AArch64 with =fast (not on x86-64), MSVC with
  # /fp:contract.
  set(_fuses OFF)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND (_variant STREQUAL "" OR _variant STREQUAL "contract-fast"))
    set(_fuses ON)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND _variant STREQUAL "contract-fast" AND _api_aarch64)
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
  _kairn_api_program(kairn-api-boundary-unguarded${_target_suffix} boundary.cpp ${_level} ${_option})
  target_compile_definitions(kairn-api-boundary-unguarded${_target_suffix} PRIVATE KAIRN_DETAIL_TEST_UNGUARDED)
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
# kernels: -fno-signed-zeros with -ffp-contract=fast breaks x * y on AArch64 (Apple clang 21), where
# an opaque product is folded back into a plain one and contracted, and breaks nothing on x86-64
# (Clang 18), where the self-test then rightly passes.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style)
  include(CheckCXXSourceCompiles)
  include(CMakePushCheckState)
  set(_api_unsafe
    reassociation "-O2 -fassociative-math -fno-signed-zeros -fno-trapping-math"
    fp-model-fast "-O2 -ffp-model=fast")
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
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
foreach(_case_name IN ITEMS 1:sub_2_2 2:lt_2_2 3:neg_2 4:to_down_2 5:add_1_1 6:ball_add_2 7:sub_2_2_assign
                            8:mul_pow2_2 9:ball_scale_2 10:traits_constant)
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
_kairn_api_reject(checks.from_limbs_not_normalized 11 "constant|constexpr")

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
set_tests_properties(api.example.first_steps PROPERTIES LABELS "api;example")
set_tests_properties(api.constexpr api.environment PROPERTIES LABELS api)
