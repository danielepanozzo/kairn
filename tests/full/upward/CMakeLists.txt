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
# with the build's flags (../../CMakeLists.txt, _upward_compiled). It registers no test.
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
