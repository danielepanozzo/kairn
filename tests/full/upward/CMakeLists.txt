# The flag matrix of the round-up interval at the level of its kernels (docs/developer/design/upward.md,
# "Tests and CI", the full tier): the runner of the family, gen/tests/upward_runner.cpp, which requires
# the rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC
# and Clang -frounding-math, MSVC /fp:strict) and holds a scope around each evaluation, built with each
# flag set below, in each form:
#
#   kairn-gen-upward-runner-SET-register   the form the target chooses (one register: SSE2 or NEON)
#   kairn-gen-upward-runner-SET-arrays     the same, the six kernels with an array form through it, with
#                                          the packed backend's option (AVX2 on x86-64, NEON)
#   kairn-gen-upward-runner-SET-numbers    the two-number form forced (KAIRN_UPWARD_FORM_NUMBERS), its
#                                          loop of arrays too
#
# for full.crosscheck.compiled.upward_*.FORMAT (../CMakeLists.txt), beside the quick tier's three runners
# with the build's flags (../../CMakeLists.txt, _upward_compiled); and the programs of the public type
# through the same sets, with their tests (below, "The public type").
#
# Each target gets exactly the options of its set, after CMAKE_CXX_FLAGS and the option of kairn::upward
# (-frounding-math, /clang:-frounding-math, /fp:strict), but the sets "no option", which link kairn::kairn
# alone: the flags of the build's configuration are emptied in this directory, as in ../../api/flags/.
# Every set but the debug build defines NDEBUG; KAIRN_CHECKS is 1 in the debug build and in the sets
# "checks" (a checked build: the scopes' check that the file's build honors the mode, the assertions of
# the header). The sets give every value of every flag of the design page's table with the options:
# each optimization level, each contraction setting, KAIRN_CHECKS 0 and 1, the two-number form, on
# x86-64 with and without the packed option (the arrays runner has it), and with MSVC /O2 /GL (whole
# program optimization: INTERPROCEDURAL_OPTIMIZATION, which gives /GL and /LTCG); and, for Clang, Apple
# clang and clang-cl, a release build without the option, whose results the barriers alone keep right.
# GCC without -frounding-math and MSVC without /fp:strict stop the build at the header's guard (the
# type's reject tests, api.upward.reject.*): no set here.
separate_arguments(_up_debug NATIVE_COMMAND "${CMAKE_CXX_FLAGS_DEBUG}")
set(_up_configs DEBUG RELEASE RELWITHDEBINFO MINSIZEREL ${CMAKE_CONFIGURATION_TYPES} ${CMAKE_BUILD_TYPE})
foreach(_config IN LISTS _up_configs)
  string(TOUPPER "${_config}" _config)
  set(CMAKE_CXX_FLAGS_${_config} "")
endforeach()

# "NAME OPTIONS...": a set with "checks" in its name defines KAIRN_CHECKS=1, one with "no-option" links
# kairn::kairn and not kairn::upward, one with "GL" is built with whole-program optimization.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_up_sets
    "O1 /O1"
    "O2-GL /O2"
    "O2-checks /O2")
elseif(_msvc_style)
  set(_up_sets
    "Od-contract-fast /Od /clang:-ffp-contract=fast"
    "O1-fp-precise /O1 /fp:precise"
    "O2-fp-strict /O2 /fp:strict"
    "O2-contract-fast-checks /O2 /clang:-ffp-contract=fast"
    "O2-no-option /O2")
else()
  set(_up_sets
    "O1-contract-fast -O1 -ffp-contract=fast"
    "O2-contract-off -O2 -ffp-contract=off"
    "O2-contract-on -O2 -ffp-contract=on"
    "O2-contract-fast-checks -O2 -ffp-contract=fast"
    "O3-contract-fast -O3 -ffp-contract=fast")
  if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    list(APPEND _up_sets "O2-no-option -O2")
  endif()
endif()
list(PREPEND _up_sets "debug")

set(_up_ipo OFF)
if(_up_sets MATCHES "GL")
  include(CheckIPOSupported)
  check_ipo_supported(RESULT _up_ipo OUTPUT _up_ipo_why LANGUAGES CXX)
  if(NOT _up_ipo)
    message(STATUS "Kairn tests: no whole-program optimization with this compiler: the round-up "
      "interval's set O2-GL is built without it (${_up_ipo_why})")
  endif()
endif()
set(_runner "${PROJECT_SOURCE_DIR}/gen/tests/upward_runner.cpp")
set(_up_runners "")     # --runner LABEL EXECUTABLE, for crosscheck.py
set(_up_targets "")
set(_up_described "")
foreach(_entry IN LISTS _up_sets)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(POP_FRONT _words _set)
  set(_debug OFF)
  if(_set STREQUAL "debug")
    set(_debug ON)
    set(_words ${_up_debug})
  endif()
  list(JOIN _words " " _text)
  list(APPEND _up_described "${_set} (${_text})")
  foreach(_form register arrays numbers)
    set(_target kairn-gen-upward-runner-${_set}-${_form})
    add_executable(${_target} "${_runner}")
    target_include_directories(${_target} PRIVATE "${PROJECT_SOURCE_DIR}/gen/tests")
    if(_set MATCHES "no-option")
      # Clang defines no macro for -frounding-math, so the header compiles without it; the barriers
      # keep the kernels' operations as written (the design page, "Barriers").
      target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    else()
      target_link_libraries(${_target} PRIVATE kairn::upward kairn::fma)
    endif()
    target_compile_options(${_target} PRIVATE ${_words} ${_warnings})
    if(_form STREQUAL "arrays")
      target_compile_options(${_target} PRIVATE ${_isa_option})
      target_compile_definitions(${_target} PRIVATE KAIRN_UPWARD_RUNNER_ARRAYS)
    elseif(_form STREQUAL "numbers")
      target_compile_definitions(${_target} PRIVATE KAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS
        KAIRN_UPWARD_RUNNER_ARRAYS)
    endif()
    if(_debug)
      if(_msvc_style)
        set_target_properties(${_target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDebugDLL)
      endif()
    else()
      target_compile_definitions(${_target} PRIVATE NDEBUG)
      if(_set MATCHES "checks")
        target_compile_definitions(${_target} PRIVATE KAIRN_CHECKS=1)
      endif()
      if(_msvc_style)
        set_target_properties(${_target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDLL)
      endif()
    endif()
    if(_set MATCHES "GL" AND _up_ipo)
      set_target_properties(${_target} PROPERTIES INTERPROCEDURAL_OPTIMIZATION ON)
    endif()
    list(APPEND _up_runners --runner "upward-${_set}-${_form}" "$<TARGET_FILE:${_target}>")
    list(APPEND _up_targets ${_target})
  endforeach()
endforeach()

set(_upward_flags_runners ${_up_runners} PARENT_SCOPE)
list(JOIN _up_described ", " _up_described)
list(LENGTH _up_targets _n)
message(STATUS "Kairn tests: the round-up interval's flag sets ${_up_described}: ${_n} runners for the "
  "full tier")

# --- The public type: the same flag sets -------------------------------------------------------------
#
# The tests of kairn/upward.hpp's public type (../../api/upward/), which require the rounding mode upward
# set by kairn::upward::Scope and the options of docs/concepts/upward.md, through the same sets: for
# each set, built with its options as the runners above (kairn::kairn alone for "no-option", KAIRN_CHECKS
# 1 in the debug build and in the sets "checks", whole-program optimization for "GL"),
#
#   kairn-api-upward-flags-SET-runner        ../../api/upward/runner.cpp, the line protocol over the
#                                            header (KAIRN_TEST_CHECKS where the checks are on)
#   kairn-api-upward-flags-SET-self-test     ../../api/upward/self_test.cpp
#   kairn-api-upward-flags-SET-moves         ../../api/upward/moves.cpp (its checked form, which records
#                                            the reports, where the checks are on)
#   kairn-api-upward-flags-SET-differential  ../../api/upward/differential.cpp
#
# and the tests, each with the label upward:
#
#   full.api.oracle.upward_K.F         api.oracle.upward_K.F on KAIRN_API_CASES cases instead of
#                                      KAIRN_API_QUICK_CASES (the quick tier's among them, the same seed),
#                                      through the quick tier's runners (../../api/upward/) and the
#                                      debug build's, on its first form only, as full.api.oracle.K.F
#   full.api.flags.oracle.upward_K.F   every form through the runner of each set, on the quick tier's
#                                      cases
#   full.api.upward.flags.SET.self_test, .moves, .differential
#                                      the quick tier's tests of those names, built with the set (the
#                                      differential judged by the oracle where Python is); with
#                                      "no-option" as without the options in the quick tier: the
#                                      self-check's advice checked, moves.cpp's first group gated and the
#                                      others reported
set(_api_up "${PROJECT_SOURCE_DIR}/tests/api/upward")
set(_api_up_flag_runners "")
set(_api_up_debug_runner "")
set(_api_up_tests "")
foreach(_entry IN LISTS _up_sets)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(POP_FRONT _words _set)
  set(_debug OFF)
  if(_set STREQUAL "debug")
    set(_debug ON)
    set(_words ${_up_debug})
  endif()
  list(JOIN _words " " _text)
  set(_checked OFF)
  if(_debug OR _set MATCHES "checks")
    set(_checked ON)
  endif()
  foreach(_program runner self-test moves differential)
    string(REPLACE "-" "_" _source "${_program}")
    set(_target kairn-api-upward-flags-${_set}-${_program})
    add_executable(${_target} "${_api_up}/${_source}.cpp")
    if(_set MATCHES "no-option")
      target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
      target_compile_definitions(${_target} PRIVATE UPWARD_TEST_WITHOUT_OPTIONS)
    else()
      target_link_libraries(${_target} PRIVATE kairn::upward kairn::fma)
    endif()
    target_compile_options(${_target} PRIVATE ${_words} ${_warnings})
    target_compile_definitions(${_target} PRIVATE "UPWARD_TEST_LEVEL=\"the set ${_set} (${_text})\"")
    if(_debug)
      if(_msvc_style)
        set_target_properties(${_target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDebugDLL)
      endif()
    else()
      target_compile_definitions(${_target} PRIVATE NDEBUG)
      if(_set MATCHES "checks")
        target_compile_definitions(${_target} PRIVATE KAIRN_CHECKS=1)
      endif()
      if(_msvc_style)
        set_target_properties(${_target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDLL)
      endif()
    endif()
    if(_checked AND _program STREQUAL "runner")
      target_compile_definitions(${_target} PRIVATE KAIRN_TEST_CHECKS)
    elseif(_checked AND _program STREQUAL "moves")
      target_compile_definitions(${_target} PRIVATE UPWARD_TEST_MOVES_CHECKED)
    endif()
    if(_set MATCHES "GL" AND _up_ipo)
      set_target_properties(${_target} PROPERTIES INTERPROCEDURAL_OPTIMIZATION ON)
    endif()
  endforeach()
  list(APPEND _api_up_flag_runners --runner ${_set} "$<TARGET_FILE:kairn-api-upward-flags-${_set}-runner>")
  if(_debug)
    set(_api_up_debug_runner --runner debug "$<TARGET_FILE:kairn-api-upward-flags-debug-runner>" --first-form debug)
  endif()
  set(_prefix full.api.upward.flags.${_set})
  add_test(NAME ${_prefix}.self_test COMMAND kairn-api-upward-flags-${_set}-self-test)
  add_test(NAME ${_prefix}.moves COMMAND kairn-api-upward-flags-${_set}-moves)
  if(Python3_Interpreter_FOUND)
    add_test(NAME ${_prefix}.differential
      COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-api-upward-flags-${_set}-differential>"
        "-DPYTHON=${Python3_EXECUTABLE}" "-DORACLE=${PROJECT_SOURCE_DIR}/oracle/kairn-oracle"
        "-DCLAIMS=${_oracle_claims}" "-DLINES=${CMAKE_CURRENT_BINARY_DIR}/differential-${_set}.txt"
        -P "${_api_up}/differential.cmake")
  else()
    add_test(NAME ${_prefix}.differential COMMAND kairn-api-upward-flags-${_set}-differential
      "${CMAKE_CURRENT_BINARY_DIR}/differential-${_set}.txt")
  endif()
  list(APPEND _api_up_tests ${_prefix}.self_test ${_prefix}.moves ${_prefix}.differential)
endforeach()
set_tests_properties(${_api_up_tests} PROPERTIES TIMEOUT 300 LABELS "full;api;upward;flags")

if(_crosscheck AND _api_upward_kernels AND _api_upward_runners)
  foreach(_kernel IN LISTS _api_upward_kernels)
    foreach(_format binary64 binary32)
      set(_name full.api.oracle.${_kernel}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_crosscheck} api --kernel ${_kernel} --format ${_format} --count ${KAIRN_API_CASES}
          --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/api-oracle" --seed "${KAIRN_API_SEED}"
          ${_api_upward_runners} ${_api_up_debug_runner} ${_oracle_claims_arg})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle;upward")
      set(_name full.api.flags.oracle.${_kernel}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_crosscheck} api --kernel ${_kernel} --format ${_format} --count ${KAIRN_API_QUICK_CASES}
          --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/api-flags" --seed "${KAIRN_API_SEED}"
          ${_api_up_flag_runners} ${_oracle_claims_arg})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle;flags;upward")
    endforeach()
  endforeach()
endif()
list(LENGTH _api_up_tests _n_api)
message(STATUS "Kairn tests: the round-up interval's public type through the same sets: ${_n_api} tests of "
  "its programs, and its kernels through the runner of each set")
