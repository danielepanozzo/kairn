# The tests of the experimental intervals rounded upward of two and four limbs
# (include/kairn/experimental/upward2.hpp, upward2_arrays.hpp, upward4.hpp, upward4_arrays.hpp;
# docs/concepts/experimental.md): EXPERIMENTAL, NOT VERIFIED, opt-in. No bound of these headers is proved; these
# tests are exact checks on the cases they run, not proofs. Label experimental, in the quick tier
# (../CMakeLists.txt, "The two tiers"; this file labels its tests quick) and, through
# _kairn_experimental_full_tier below, in the full tier (../full/CMakeLists.txt, full.experimental.*).
# Registered when KAIRN_EXPERIMENTAL_TESTS is on, and only with GCC- and Clang-style compilers: the
# headers refuse MSVC, and clang-cl and Windows were never part of the experiments, so with MSVC or
# clang-cl nothing here is built (../CMakeLists.txt says so when CMake runs). Every program defines
# KAIRN_EXPERIMENTAL_UNVERIFIED, the opt-in, and links kairn::upward (-frounding-math, the option of
# docs/concepts/upward.md) and kairn::fma, and is built with the warnings of Kairn's tests, -Wall
# -Wextra -Wpedantic (as errors where the build asks for them, as the CI does).
#
# The quick tier:
#
# - experimental.upward2.check, experimental.upward4.check: the exact checks of the experiments
#   (experiments/upward2/tests/check.cpp, experiments/upward4/tests/check.cpp, the programs of the
#   experiments' own projects, which say what they check), with the build's flags, built for AVX2
#   where the packed kernels are (../CMakeLists.txt, _isa_option), on
#   KAIRN_EXPERIMENTAL_QUICK_CASES cases of each class of operands, seed 1, two threads: every
#   result must contain the exact range, computed in exact integer arithmetic
#   (experiments/upward2/tests/exact.hpp), and keep the type's invariant, on every operation; each
#   function on arrays (upward2_arrays.hpp, upward4_arrays.hpp) must give the type's operators'
#   results bit for bit; then every pair of a list of special values against the exact range in the
#   extended reals. The program's exit status is the test's.
# - experimental.headers (headers.cmake): every header of include/kairn/experimental/ starts with
#   the banner and the guard of the opt-in; nothing of the library includes one or defines the
#   opt-in; experiments/ holds only the forms of the measurements; no claim and no reference page
#   names them.
# - experimental.opt_in.HEADER (opt_in.cpp, through ../api/compile_fail.cmake): each header refuses
#   to compile without KAIRN_EXPERIMENTAL_UNVERIFIED, with its message, and compiles with it under
#   -Wall -Wextra -Wpedantic -Werror (built for AVX2 where the packed kernels are), as a client may
#   compile it.
# - experimental.example: the example of docs/concepts/experimental.md
#   (docs/examples/cpp/concepts_experimental.cpp), which checks its own results; what it prints must
#   be the text the page shows (../api/example_output.cmake).
# - experimental.consume.add_subdirectory, experimental.consume.find_package: a project
#   (../consume/experimental/) whose program includes every experimental header through
#   kairn::upward and kairn::fma in a file that defines the opt-in, as the page says, compiled with
#   -Wall -Wextra -Wpedantic -Werror, and runs an operation of each type and of each header of
#   functions on arrays: with Kairn added by add_subdirectory, and found by find_package after
#   consume.install has installed this build tree (KAIRN_INSTALL).
#
# The full tier: the same checks in each variant of the experiments' own projects, at -O2 and at -O3,
# on KAIRN_EXPERIMENTAL_CASES cases of each class, seed 2: native (as above), numbers (the form of
# plain doubles forced, KAIRN_UPWARD2_FORM_NUMBERS), checked (KAIRN_CHECKS 1) and, on x86-64, sse
# (FMA without AVX2: kairn::fma's option only).

set(KAIRN_EXPERIMENTAL_QUICK_CASES 20000 CACHE STRING
  "Cases per class of operands of the quick tier's exact checks of the experimental headers")
set(KAIRN_EXPERIMENTAL_CASES 100000 CACHE STRING
  "Cases per class of operands of the full tier's exact checks of the experimental headers")

# _kairn_experimental_check(TARGET LIMBS VARIANT LEVEL): the program TARGET of the exact checks of
# the experimental type of LIMBS limbs (2 or 4), in the variant VARIANT (native, numbers, checked,
# sse), at LEVEL (O2 or O3; empty: the build's flags alone). A function, so that the full tier
# (../full/CMakeLists.txt) builds its programs the same way.
function(_kairn_experimental_check target limbs variant level)
  find_package(Threads REQUIRED)
  add_executable(${target} "${PROJECT_SOURCE_DIR}/experiments/upward${limbs}/tests/check.cpp")
  target_link_libraries(${target} PRIVATE kairn::upward kairn::fma Threads::Threads)
  # The forms of the measurements, which the checks compare with the type's.
  target_include_directories(${target} PRIVATE "${PROJECT_SOURCE_DIR}/experiments/upward2/include")
  target_compile_definitions(${target} PRIVATE KAIRN_EXPERIMENTAL_UNVERIFIED)
  if(limbs EQUAL 4)
    target_include_directories(${target} PRIVATE "${PROJECT_SOURCE_DIR}/experiments/upward4/include")
    target_compile_definitions(${target} PRIVATE KAIRN_UPWARD4_COUNT=1)
  endif()
  set(_options ${_warnings})
  if(level)
    list(APPEND _options -${level})
  endif()
  if(variant STREQUAL "native" OR variant STREQUAL "checked")
    list(APPEND _options ${_isa_option})
  endif()
  if(variant STREQUAL "numbers")
    target_compile_definitions(${target} PRIVATE KAIRN_UPWARD2_FORM=KAIRN_UPWARD2_FORM_NUMBERS)
  elseif(variant STREQUAL "checked")
    target_compile_definitions(${target} PRIVATE KAIRN_CHECKS=1)
  endif()
  target_compile_options(${target} PRIVATE ${_options})
  # What the program prints first: the compiler and the options added here.
  get_target_property(_upward kairn::upward INTERFACE_COMPILE_OPTIONS)
  get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
  if(NOT _fma)
    set(_fma "")
  endif()
  string(REPLACE ";" " " _text "${CMAKE_CXX_FLAGS} the build's flags, ${_upward} ${_fma} ${_options}")
  string(REGEX REPLACE " +" " " _text "${_text}")
  target_compile_definitions(${target} PRIVATE
    "X${limbs}_FLAGS=\"${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION} ${_text} (${variant})\"")
endfunction()

# _kairn_experimental_full_tier(): the full tier's programs and tests, full.experimental.upwardL.
# VARIANT.LEVEL, registered in the directory that calls it (../full/).
function(_kairn_experimental_full_tier)
  set(_variants native numbers checked)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
    list(APPEND _variants sse)
  endif()
  foreach(_limbs 2 4)
    foreach(_variant IN LISTS _variants)
      foreach(_level O2 O3)
        set(_target kairn-experimental-check${_limbs}-${_variant}-${_level})
        _kairn_experimental_check(${_target} ${_limbs} ${_variant} ${_level})
        set(_name full.experimental.upward${_limbs}.${_variant}.${_level})
        add_test(NAME ${_name} COMMAND ${_target} ${KAIRN_EXPERIMENTAL_CASES} 2 2)
        set_tests_properties(${_name} PROPERTIES TIMEOUT 1200 PROCESSORS 2 LABELS "full;experimental")
      endforeach()
    endforeach()
  endforeach()
endfunction()

# --- The quick tier ------------------------------------------------------------------------------

foreach(_limbs 2 4)
  _kairn_experimental_check(kairn-experimental-check${_limbs} ${_limbs} native "")
  add_test(NAME experimental.upward${_limbs}.check
    COMMAND kairn-experimental-check${_limbs} ${KAIRN_EXPERIMENTAL_QUICK_CASES} 1 2)
  set_tests_properties(experimental.upward${_limbs}.check PROPERTIES TIMEOUT 600 PROCESSORS 2)
endforeach()

add_test(NAME experimental.headers
  COMMAND "${CMAKE_COMMAND}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}" -P "${CMAKE_CURRENT_SOURCE_DIR}/headers.cmake")

# The opt-in, through ../api/compile_fail.cmake: the front end only, with the options of
# kairn::upward and kairn::fma, the packed kernels' AVX2 where they use it, and the tests' warnings as
# errors, so that each control is compiled as a strict client would compile it.
get_target_property(_upward kairn::upward INTERFACE_COMPILE_OPTIONS)
get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
if(NOT _fma)
  set(_fma "")
endif()
list(JOIN _upward "|" _common)
foreach(_option IN LISTS _fma _isa_option _warnings ITEMS -Werror)
  string(APPEND _common "|${_option}")
endforeach()
set(_opt_in_common "-DCXX=${CMAKE_CXX_COMPILER}" -DSTYLE=gnu "-DINCLUDE=${PROJECT_SOURCE_DIR}/include"
  "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/opt_in.cpp" "-DCOMMON=${_common}" "-DOPTIONS=")
if(CMAKE_OSX_SYSROOT)
  list(APPEND _opt_in_common "-DSYSROOT=${CMAKE_OSX_SYSROOT}")
endif()
set(_opt_in_cases 1:upward2 2:upward2_arrays 3:upward4 4:upward4_arrays)
foreach(_case_name IN LISTS _opt_in_cases)
  string(REPLACE ":" ";" _pair "${_case_name}")
  list(GET _pair 0 _case)
  list(GET _pair 1 _header)
  add_test(NAME experimental.opt_in.${_header}
    COMMAND "${CMAKE_COMMAND}" ${_opt_in_common} "-DCASE=${_case}"
      "-DEXPECT=kairn/experimental/${_header}\\.hpp is EXPERIMENTAL and NOT VERIFIED"
      -P "${PROJECT_SOURCE_DIR}/tests/api/compile_fail.cmake")
endforeach()

# The example of the concept page, with the build's flags and the warnings of the tests as errors.
add_executable(kairn-experimental-example "${PROJECT_SOURCE_DIR}/docs/examples/cpp/concepts_experimental.cpp")
target_link_libraries(kairn-experimental-example PRIVATE kairn::upward kairn::fma)
target_compile_options(kairn-experimental-example PRIVATE ${_warnings} -Werror)
add_test(NAME experimental.example
  COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-experimental-example>"
    "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/concepts_experimental.txt"
    -P "${PROJECT_SOURCE_DIR}/tests/api/example_output.cmake")
set_tests_properties(experimental.example PROPERTIES TIMEOUT 120)

# The consumer checks, with the variables of the consumer checks of ../CMakeLists.txt: the build's
# generator, compiler and build type.
set(_experimental_consume "${CMAKE_CURRENT_SOURCE_DIR}/../consume/experimental")
add_test(NAME experimental.consume.add_subdirectory
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${_experimental_consume}" "${_consume_dir}/experimental-add_subdirectory"
    ${_build_and_test} ${_build_options} "-DKAIRN_SOURCE_DIR=${PROJECT_SOURCE_DIR}"
    --test-command consume_experimental)
set_tests_properties(experimental.consume.add_subdirectory PROPERTIES TIMEOUT 600)
if(KAIRN_INSTALL)
  add_test(NAME experimental.consume.find_package
    COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
      "${_experimental_consume}" "${_consume_dir}/experimental-find_package"
      ${_build_and_test} ${_build_options} "-DCMAKE_PREFIX_PATH=${_consume_dir}/prefix"
      --test-command consume_experimental)
  set_tests_properties(experimental.consume.find_package PROPERTIES TIMEOUT 600
    FIXTURES_REQUIRED kairn_installed)
endif()

# Every test here: label experimental, in the quick tier.
get_property(_experimental_tests DIRECTORY PROPERTY TESTS)
set_property(TEST ${_experimental_tests} APPEND PROPERTY LABELS experimental quick)
list(LENGTH _experimental_tests _n)
message(STATUS "Kairn tests: the experimental headers (NOT VERIFIED), ${_n} tests labelled "
  "experimental in the quick tier, their exact checks on ${KAIRN_EXPERIMENTAL_QUICK_CASES} cases per "
  "class, and in the full tier on ${KAIRN_EXPERIMENTAL_CASES}")
