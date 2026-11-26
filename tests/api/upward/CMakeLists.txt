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
#   file built without the options, whose upward scopes report it.
# - api.upward.units, api.upward.units.ipo: a scope in one file and the operation it runs in another
#   (units_a.cpp, units_b.cpp), linked as they are and with whole-program optimization where CMake
#   supports it here (check_ipo_supported), which can inline the operation into the scope's file:
#   on MSVC the barrier per scope reaches it through the inline thread_local
#   kairn::upward::detail::zero, the same object in both files.
# - api.upward.dll (MSVC only): the same with the operation in a DLL, which has a zero of its own
#   that the program's scopes never write; the test pins that, and runs the same probes.
# - api.upward.reject.*: the compile-time guard (case 119 of ../reject.cpp, through
#   ../compile_fail.cmake): GCC without -frounding-math, MSVC without /fp:strict and with
#   /fp:contract stop the build with the guard's message; each control, the same options with
#   KAIRN_UPWARD_OPTIONS_UNCHECKED defined, compiles.
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
add_test(NAME api.upward.units COMMAND kairn-api-upward-units)
include(CheckIPOSupported)
check_ipo_supported(RESULT _upward_ipo LANGUAGES CXX)
if(_upward_ipo)
  _kairn_upward_program(kairn-api-upward-units-ipo units_a.cpp units_b.cpp)
  set_target_properties(kairn-api-upward-units-ipo PROPERTIES INTERPROCEDURAL_OPTIMIZATION ON)
  add_test(NAME api.upward.units.ipo COMMAND kairn-api-upward-units-ipo)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  add_library(kairn-api-upward-dll-operation SHARED units_b.cpp)
  target_link_libraries(kairn-api-upward-dll-operation PRIVATE kairn::upward kairn::fma)
  target_compile_definitions(kairn-api-upward-dll-operation PRIVATE UPWARD_TEST_DLL UPWARD_TEST_BUILDING_DLL)
  target_compile_options(kairn-api-upward-dll-operation PRIVATE ${_api_warnings})
  _kairn_upward_program(kairn-api-upward-dll units_a.cpp)
  target_compile_definitions(kairn-api-upward-dll PRIVATE UPWARD_TEST_DLL)
  target_link_libraries(kairn-api-upward-dll PRIVATE kairn-api-upward-dll-operation)
  add_test(NAME api.upward.dll COMMAND kairn-api-upward-dll)
endif()

get_property(_upward_programs DIRECTORY PROPERTY TESTS)
set_tests_properties(${_upward_programs} PROPERTIES TIMEOUT 120)

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
