# The tests of <kairn/upward.hpp>, the round-up interval (docs/developer/design/upward.md, "Tests
# and CI"), labels upward and api, in the quick tier; registered when KAIRN_UPWARD_TESTS is on
# (../../CMakeLists.txt). Requires the rounding mode upward set by kairn::upward::Scope and the
# options of docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): every
# program here links kairn::upward, which adds them, but api.upward.checks.unhonored, which tests a
# build without them. The environment part of the header:
#
# - api.upward.scope: the scopes, observed from outside (scope.cpp): their mode with flush to zero
#   off from every starting state, and the state restored; a scope inside one of the same mode does
#   not write the register; the exception flags kept; the C library's mode set by the scopes of the
#   program and not by the register-only scope of the functions on arrays; a NearestScope inside a
#   Scope and the reverse; a thread started inside a scope; the barriers and the pin keep every bit.
# - api.upward.checks, .off, .unhonored: the assertions of a checked build (checks.cpp), with a
#   handler of KAIRN_ENVIRONMENT_FAILURE that records and returns: with KAIRN_CHECKS 1 and 0, and a
#   file built without the options, whose upward scopes report it; and the checks of the interval
#   type and the functions on arrays (an operation outside a scope, a default type inside one, a
#   state that is not canonical, views of different lengths or that overlap).
# - api.upward.units, api.upward.units.ipo: a scope in one file and the operation it runs in another
#   (units_a.cpp, units_b.cpp: a product of kairn::upward::Interval<double>), linked as they are and
#   with whole-program optimization where CMake supports it here (check_ipo_supported), which can
#   inline the operation into the scope's file: on MSVC the barrier per scope reaches it through the
#   inline thread_local kairn::upward::detail::zero, the same object in both files. Built with
#   KAIRN_CHECKS 0: some probes run the operation outside any scope on purpose.
# - api.upward.dll (MSVC only): the same with the operation in a DLL, which has a zero of its own
#   that the program's scopes never write; the test pins that, and runs the same probes.
# - api.upward.reject.*: the compile-time guard (case 119 of ../reject.cpp, through
#   ../compile_fail.cmake): GCC without -frounding-math, MSVC without /fp:strict and with
#   /fp:contract stop the build with the guard's message; each control, the same options with
#   KAIRN_UPWARD_OPTIONS_UNCHECKED defined, compiles.
#
# The interval type, the functions on arrays and the self-check:
#
# - api.oracle.upward_K.F, for each kernel K of gen/claims.json marked "rounding": "upward" and each
#   format F (which ../CMakeLists.txt leaves to this file): the oracle judges, against K's claims,
#   every public operation of <kairn/upward.hpp> that calls K (runner.cpp, a runner of the line
#   protocol over the header), on KAIRN_API_QUICK_CASES random cases, through the runners built
#   here: with the build's flags; with contraction forced on (not with MSVC, whose /fp:strict
#   excludes it and whose guard refuses /fp:contract); with the two-number form forced
#   (KAIRN_UPWARD_FORM_NUMBERS); in a checked build (KAIRN_CHECKS 1, which must report nothing on
#   the oracle's canonical operands); and, on x86-64 where the build's flags do not give AVX2 and
#   the compiler can, built for AVX2, so that the functions on arrays run their AVX2 form.
# - api.upward.differential, .numbers, .avx2: every operation and function on arrays against the
#   default kairn::Interval<T, 1> on the same operands (differential.cpp), and every upward result
#   judged by the oracle (differential.cmake); with the build's flags, the two-number form forced,
#   and built for AVX2 as above.
# - api.upward.self_test, .checked, .numbers, .without_options: kairn::upward::self_test() passes
#   and restores the caller's state, from every starting state (self_test.cpp); in a checked build;
#   with the two-number form forced; and, with Clang (which compiles the header without the
#   options), built without them, where it still passes and advises that the file's own arithmetic
#   ignores the mode.
# - api.upward.limbs.O2, .O3 (api.upward.limbs with MSVC): from_limbs and to_limbs on arrays read
#   and written as T around the calls (limbs.cpp), at -O2 and -O3 whatever the build's flags.
find_package(Threads REQUIRED)

function(_kairn_upward_program target)
  add_executable(${target} ${ARGN})
  target_link_libraries(${target} PRIVATE kairn::upward kairn::fma)
  target_compile_options(${target} PRIVATE ${_api_warnings})
endfunction()

_kairn_upward_program(kairn-api-upward-scope scope.cpp)
target_link_libraries(kairn-api-upward-scope PRIVATE Threads::Threads)
add_test(NAME api.upward.scope COMMAND kairn-api-upward-scope)

_kairn_upward_program(kairn-api-upward-checks checks.cpp)
target_compile_definitions(kairn-api-upward-checks PRIVATE KAIRN_CHECKS=1)
add_test(NAME api.upward.checks COMMAND kairn-api-upward-checks)
_kairn_upward_program(kairn-api-upward-checks-off checks.cpp)
target_compile_definitions(kairn-api-upward-checks-off PRIVATE KAIRN_CHECKS=0 KAIRN_TEST_CHECKS_OFF)
add_test(NAME api.upward.checks.off COMMAND kairn-api-upward-checks-off)
# Without the options: kairn::kairn, not kairn::upward. Each compiler measured computes the literal
# sum of the check at compile time without them, at every level of optimization (GCC 13 and 16,
# Clang 18 and Apple clang 21 at -O0 to -O3, MSVC at /Od, /O2 and /O2 /GL), so the build's own
# flags are enough.
add_executable(kairn-api-upward-checks-unhonored checks.cpp)
target_link_libraries(kairn-api-upward-checks-unhonored PRIVATE kairn::kairn kairn::fma)
target_compile_definitions(kairn-api-upward-checks-unhonored PRIVATE KAIRN_CHECKS=1 KAIRN_TEST_UNHONORED)
target_compile_options(kairn-api-upward-checks-unhonored PRIVATE ${_api_warnings})
add_test(NAME api.upward.checks.unhonored COMMAND kairn-api-upward-checks-unhonored)

_kairn_upward_program(kairn-api-upward-units units_a.cpp units_b.cpp)
target_compile_definitions(kairn-api-upward-units PRIVATE KAIRN_CHECKS=0)
add_test(NAME api.upward.units COMMAND kairn-api-upward-units)
include(CheckIPOSupported)
check_ipo_supported(RESULT _upward_ipo LANGUAGES CXX)
if(_upward_ipo)
  _kairn_upward_program(kairn-api-upward-units-ipo units_a.cpp units_b.cpp)
  target_compile_definitions(kairn-api-upward-units-ipo PRIVATE KAIRN_CHECKS=0)
  set_target_properties(kairn-api-upward-units-ipo PROPERTIES INTERPROCEDURAL_OPTIMIZATION ON)
  add_test(NAME api.upward.units.ipo COMMAND kairn-api-upward-units-ipo)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  add_library(kairn-api-upward-dll-operation SHARED units_b.cpp)
  target_link_libraries(kairn-api-upward-dll-operation PRIVATE kairn::upward kairn::fma)
  target_compile_definitions(kairn-api-upward-dll-operation PRIVATE UPWARD_TEST_DLL UPWARD_TEST_BUILDING_DLL
    KAIRN_CHECKS=0)
  target_compile_options(kairn-api-upward-dll-operation PRIVATE ${_api_warnings})
  _kairn_upward_program(kairn-api-upward-dll units_a.cpp)
  target_compile_definitions(kairn-api-upward-dll PRIVATE UPWARD_TEST_DLL KAIRN_CHECKS=0)
  target_link_libraries(kairn-api-upward-dll PRIVATE kairn-api-upward-dll-operation)
  add_test(NAME api.upward.dll COMMAND kairn-api-upward-dll)
endif()

# --- The interval type, the functions on arrays and the self-check --------------------------------
#
# The forms of the header that the tests build: the build's flags; the two-number form forced; and,
# on x86-64 where the build's flags do not give AVX2 and the compiler can (../CMakeLists.txt,
# _api_packed_avx2: the native form of Packed is the scalar one there), built for AVX2, so that the
# functions on arrays run their AVX2 form (KAIRN_UPWARD_ARRAYS_AVX2), as the hosted MSVC job's
# /arch:AVX2 and the Mac's NEON give it in the build's own flags.
if(_msvc_style)
  set(_upward_numbers /DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS)
else()
  set(_upward_numbers -DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS)
endif()
set(_upward_forms build numbers)
set(_upward_form_build_options "")
set(_upward_form_numbers_options ${_upward_numbers})
if(_api_packed_avx2)
  list(APPEND _upward_forms avx2)
  set(_upward_form_avx2_options ${_isa_option})
endif()

# The differential, judged by the oracle where Python is (differential.cmake).
foreach(_form IN LISTS _upward_forms)
  set(_suffix "")
  if(NOT _form STREQUAL "build")
    set(_suffix ".${_form}")
  endif()
  _kairn_upward_program(kairn-api-upward-differential-${_form} differential.cpp)
  target_compile_options(kairn-api-upward-differential-${_form} PRIVATE ${_upward_form_${_form}_options})
  if(Python3_Interpreter_FOUND)
    add_test(NAME api.upward.differential${_suffix}
      COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-api-upward-differential-${_form}>"
        "-DPYTHON=${Python3_EXECUTABLE}" "-DORACLE=${PROJECT_SOURCE_DIR}/oracle/kairn-oracle"
        "-DCLAIMS=${_oracle_claims}" "-DLINES=${CMAKE_CURRENT_BINARY_DIR}/differential-${_form}.txt"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/differential.cmake")
  else()
    add_test(NAME api.upward.differential${_suffix} COMMAND kairn-api-upward-differential-${_form}
      "${CMAKE_CURRENT_BINARY_DIR}/differential-${_form}.txt")
  endif()
  _kairn_upward_program(kairn-api-upward-self-test-${_form} self_test.cpp)
  target_compile_options(kairn-api-upward-self-test-${_form} PRIVATE ${_upward_form_${_form}_options})
  add_test(NAME api.upward.self_test${_suffix} COMMAND kairn-api-upward-self-test-${_form})
endforeach()
_kairn_upward_program(kairn-api-upward-self-test-checked self_test.cpp)
target_compile_definitions(kairn-api-upward-self-test-checked PRIVATE KAIRN_CHECKS=1)
add_test(NAME api.upward.self_test.checked COMMAND kairn-api-upward-self-test-checked)
# Without the options: kairn::kairn, not kairn::upward, with Clang only (GCC and MSVC refuse the
# header without them); a release build, since a checked build's scopes report the file.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_executable(kairn-api-upward-self-test-without-options self_test.cpp)
  target_link_libraries(kairn-api-upward-self-test-without-options PRIVATE kairn::kairn kairn::fma)
  target_compile_definitions(kairn-api-upward-self-test-without-options PRIVATE KAIRN_CHECKS=0
    UPWARD_TEST_WITHOUT_OPTIONS)
  target_compile_options(kairn-api-upward-self-test-without-options PRIVATE ${_api_warnings})
  add_test(NAME api.upward.self_test.without_options COMMAND kairn-api-upward-self-test-without-options)
endif()

# from_limbs and to_limbs at -O2 and -O3 whatever the build's flags (the later -O wins).
if(_msvc_style)
  _kairn_upward_program(kairn-api-upward-limbs limbs.cpp)
  add_test(NAME api.upward.limbs COMMAND kairn-api-upward-limbs)
else()
  foreach(_level 2 3)
    _kairn_upward_program(kairn-api-upward-limbs-O${_level} limbs.cpp)
    target_compile_options(kairn-api-upward-limbs-O${_level} PRIVATE -O${_level})
    add_test(NAME api.upward.limbs.O${_level} COMMAND kairn-api-upward-limbs-O${_level})
  endforeach()
endif()

# The runners of the line protocol over the header, as --runner LABEL EXECUTABLE for
# ../../crosscheck.py api. The runner with the build's flags also answers api.oracle.coverage
# (--list), which ../CMakeLists.txt registers.
_kairn_upward_program(kairn-api-upward-runner runner.cpp)
set(_upward_runners --runner build "$<TARGET_FILE:kairn-api-upward-runner>")
if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  if(_msvc_style)
    set(_upward_contract /clang:-ffp-contract=fast)
  else()
    # At -O2, like the contraction runners of the cross-checks (../../CMakeLists.txt says why).
    set(_upward_contract -ffp-contract=fast -O2)
  endif()
  _kairn_upward_program(kairn-api-upward-runner-contract-fast runner.cpp)
  target_compile_options(kairn-api-upward-runner-contract-fast PRIVATE ${_upward_contract})
  list(APPEND _upward_runners --runner contract-fast "$<TARGET_FILE:kairn-api-upward-runner-contract-fast>")
endif()
_kairn_upward_program(kairn-api-upward-runner-numbers runner.cpp)
target_compile_options(kairn-api-upward-runner-numbers PRIVATE ${_upward_numbers})
_kairn_upward_program(kairn-api-upward-runner-checked runner.cpp)
target_compile_definitions(kairn-api-upward-runner-checked PRIVATE KAIRN_TEST_CHECKS KAIRN_CHECKS=1)
list(APPEND _upward_runners --runner numbers "$<TARGET_FILE:kairn-api-upward-runner-numbers>"
  --runner checked "$<TARGET_FILE:kairn-api-upward-runner-checked>")
if(_api_packed_avx2)
  _kairn_upward_program(kairn-api-upward-runner-avx2 runner.cpp)
  target_compile_options(kairn-api-upward-runner-avx2 PRIVATE ${_isa_option})
  list(APPEND _upward_runners --runner avx2 "$<TARGET_FILE:kairn-api-upward-runner-avx2>")
endif()

get_property(_upward_programs DIRECTORY PROPERTY TESTS)
set_tests_properties(${_upward_programs} PROPERTIES TIMEOUT 120)

# The kernels of the round-up interval against the oracle, through the runners above: the names
# ../CMakeLists.txt gives every kernel (api.oracle.K.F), and its arguments, but these runners; it
# leaves these kernels out of its own loop and lists them in _api_upward_kernels. About a second
# each on the Mac with four runners.
foreach(_kernel IN LISTS _api_upward_kernels)
  foreach(_format binary64 binary32)
    set(_name api.oracle.${_kernel}.${_format})
    add_test(NAME ${_name}
      COMMAND ${_api_crosscheck} api --kernel ${_kernel} --format ${_format}
        --count ${KAIRN_API_QUICK_CASES} --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/oracle"
        --seed "${KAIRN_API_SEED}" ${_upward_runners} ${_oracle_claims_arg})
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "api;oracle")
  endforeach()
endforeach()

# The guard: reject.cpp's case 119 includes the header, and its control defines
# KAIRN_UPWARD_OPTIONS_UNCHECKED. The option under test is among the options of both compilations
# (COMMON), so that the control differs from the test only in the macro.
set(_upward_reject "-DCXX=${CMAKE_CXX_COMPILER}" "-DSTYLE=${_api_style}" "-DINCLUDE=${_api_include}"
  "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/../reject.cpp" "-DCASE=119")
if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
  list(APPEND _upward_reject "-DSYSROOT=${CMAKE_OSX_SYSROOT}")
endif()
function(_kairn_upward_reject name option expect)
  add_test(NAME api.upward.reject.${name}
    COMMAND "${CMAKE_COMMAND}" ${_upward_reject} "-DCOMMON=${_api_fma_bars}|${option}" "-DEXPECT=${expect}"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/../compile_fail.cmake")
  set_tests_properties(api.upward.reject.${name} PROPERTIES TIMEOUT 300 LABELS reject)
endfunction()
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  _kairn_upward_reject(gcc_without_rounding_math -fno-rounding-math "needs -frounding-math with GCC")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  _kairn_upward_reject(msvc_without_fp_strict /fp:precise "needs /fp:strict with MSVC")
  _kairn_upward_reject(msvc_fp_contract /fp:contract "does not work with /fp:contract")
endif()

get_property(_upward_tests DIRECTORY PROPERTY TESTS)
set_property(TEST ${_upward_tests} APPEND PROPERTY LABELS "api;upward;quick")
