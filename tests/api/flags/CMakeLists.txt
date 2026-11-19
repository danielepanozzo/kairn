# The flag sets of a client (docs/developer/testing.md, "Flag sets"): the public interface and the
# generated kernels built as a program that includes Kairn may build them, at each optimization
# level, under each contraction setting, with -frounding-math (GCC, Clang) or /fp:strict (MSVC,
# clang-cl), and as a debug build, in which KAIRN_CHECKS is 1.
#
# For each flag set of this compiler, this directory builds, with the set's options:
#
#   kairn-api-runner-SET          tests/api/runner.cpp, the public interface on the line protocol,
#                                 which also runs kairn::self_test() (--self-test)
#   kairn-api-constexpr-SET       tests/api/constexpr.cpp, the interface's constant expressions
#
# and, for the debug build and the set marked "kernels" below, the kernels' runners:
#
#   kairn-gen-runner-SET          gen/tests/runner.cpp, the scalar kernels
#   kairn-gen-packed-runner-SET   gen/tests/packed_runner.cpp, the packed kernels of the target's
#                                 backend, where it has one
#
# and, for the debug build only, the programs of the checks: kairn-api-checks-debug
# (tests/api/checks.cpp) and kairn-api-checks-handler (tests/api/checks_handler.cpp). It registers
# no test: ../CMakeLists.txt registers the quick tier's, and ../../full/CMakeLists.txt the full
# tier's, from the variables set at the end.
#
# Each target gets exactly the options of its set, after CMAKE_CXX_FLAGS: the flags of the build's
# configuration (CMAKE_CXX_FLAGS_RELEASE and the others: -O3 -DNDEBUG, /O2 /Ob2 /DNDEBUG) are
# emptied in this directory, so that no optimization level and no NDEBUG comes from them. Every
# set but the debug build defines NDEBUG, as a release build does.

# The debug build is CMake's own Debug configuration: its flags (-g; /Zi /Ob0 /Od /RTC1), the debug
# C runtime with MSVC and clang-cl, and no NDEBUG, so that KAIRN_CHECKS is 1 by default.
separate_arguments(_flags_debug NATIVE_COMMAND "${CMAKE_CXX_FLAGS_DEBUG}")
set(_flags_configs DEBUG RELEASE RELWITHDEBINFO MINSIZEREL ${CMAKE_CONFIGURATION_TYPES} ${CMAKE_BUILD_TYPE})
foreach(_config IN LISTS _flags_configs)
  string(TOUPPER "${_config}" _config)
  set(CMAKE_CXX_FLAGS_${_config} "")
endforeach()

# The sets, each "NAME WHAT OPTIONS...", WHAT being "api" (the public interface's programs) or
# "kernels" (the kernels' runners as well), chosen so that every value of every flag is tested,
# and every combination Phase 0 found dangerous (docs/developer/testing.md, "Flag sets", says which
# and why). The build's own flags (Release) and each contraction setting at -O2 (GCC, Clang) or
# with /O2 (MSVC, clang-cl) are tested by the runners of ../../CMakeLists.txt and ../CMakeLists.txt.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_flags_sets
    "Od-fp-contract api /Od /fp:contract"
    "Od-fp-strict api /Od /fp:strict"
    "O1-fp-precise api /O1 /fp:precise"
    "O1-fp-contract kernels /O1 /fp:contract"
    "O1-fp-strict api /O1 /fp:strict"
    "O2-fp-strict api /O2 /fp:strict")
elseif(_msvc_style)
  # clang-cl: /fp:strict is -ffp-model=strict (contraction off, -frounding-math), /fp:precise and
  # /fp:contract are -ffp-contract=on, and =fast has only the /clang: spelling.
  set(_flags_sets
    "Od-contract-fast api /Od /clang:-ffp-contract=fast"
    "Od-fp-strict api /Od /fp:strict"
    "O1-fp-precise api /O1 /fp:precise"
    "O1-contract-fast-rounding-math kernels /O1 /clang:-ffp-contract=fast /clang:-frounding-math"
    "O2-fp-contract api /O2 /fp:contract"
    "O2-fp-strict api /O2 /fp:strict")
else()
  set(_flags_sets
    "O0-contract-fast-rounding-math api -O0 -ffp-contract=fast -frounding-math"
    "O1-contract-off api -O1 -ffp-contract=off"
    "O1-contract-fast kernels -O1 -ffp-contract=fast"
    "O2-contract-on-rounding-math api -O2 -ffp-contract=on -frounding-math"
    "O2-contract-fast-rounding-math api -O2 -ffp-contract=fast -frounding-math"
    "O3-contract-off-rounding-math api -O3 -ffp-contract=off -frounding-math"
    "O3-contract-fast api -O3 -ffp-contract=fast")
endif()
list(PREPEND _flags_sets "debug kernels")

function(_kairn_flags_target target source set_options debug)
  add_executable(${target} "${source}")
  target_link_libraries(${target} PRIVATE kairn::kairn kairn::fma)
  target_compile_options(${target} PRIVATE ${set_options} ${ARGN})
  if(debug)
    if(_msvc_style)
      set_target_properties(${target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDebugDLL)
    endif()
  else()
    target_compile_definitions(${target} PRIVATE NDEBUG)
    if(_msvc_style)
      set_target_properties(${target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDLL)
    endif()
  endif()
endfunction()

set(_api "${PROJECT_SOURCE_DIR}/tests/api")
set(_gen "${PROJECT_SOURCE_DIR}/gen/tests")
set(_names "")        # every set, the debug build first
set(_gen_runners "")  # the kernels' runners, and their labels for the cross-checks
set(_gen_labels "")
set(_described "")
foreach(_entry IN LISTS _flags_sets)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(POP_FRONT _words _set _what)
  set(_debug OFF)
  if(_set STREQUAL "debug")
    set(_debug ON)
    set(_words ${_flags_debug})
  endif()
  list(APPEND _names ${_set})
  list(JOIN _words " " _text)
  list(APPEND _described "${_set} (${_text})")

  _kairn_flags_target(kairn-api-runner-${_set} "${_api}/runner.cpp" "${_words}" ${_debug} ${_api_warnings})
  _kairn_flags_target(kairn-api-constexpr-${_set} "${_api}/constexpr.cpp" "${_words}" ${_debug} ${_api_warnings})
  if(_debug)
    # The runner leaves KAIRN_CHECKS to its default, 1 without NDEBUG (runner.cpp).
    target_compile_definitions(kairn-api-runner-${_set} PRIVATE KAIRN_TEST_CHECKS)
  endif()
  if(_what STREQUAL "kernels" AND EXISTS "${_gen}/runner.cpp")
    _kairn_flags_target(kairn-gen-runner-${_set} "${_gen}/runner.cpp" "${_words}" ${_debug} ${_warnings})
    target_include_directories(kairn-gen-runner-${_set} PRIVATE "${_gen}")
    list(APPEND _gen_runners kairn-gen-runner-${_set})
    list(APPEND _gen_labels cxx-${_set})
  endif()
  if(_what STREQUAL "kernels" AND _packed_backend AND EXISTS "${_gen}/packed_runner.cpp")
    _kairn_flags_target(kairn-gen-packed-runner-${_set} "${_gen}/packed_runner.cpp" "${_words}" ${_debug}
      ${_warnings} ${_isa_option})
    target_include_directories(kairn-gen-packed-runner-${_set} PRIVATE "${_gen}")
    list(APPEND _gen_runners kairn-gen-packed-runner-${_set})
    list(APPEND _gen_labels ${_packed_backend}-${_set})
  endif()
endforeach()

# The checks, in the debug build: KAIRN_CHECKS from its default (KAIRN_TEST_DEFAULT_CHECKS says
# so to checks.cpp), and a program that defines KAIRN_ENVIRONMENT_FAILURE.
_kairn_flags_target(kairn-api-checks-debug "${_api}/checks.cpp" "${_flags_debug}" ON ${_api_warnings})
target_compile_definitions(kairn-api-checks-debug PRIVATE KAIRN_TEST_DEFAULT_CHECKS)
_kairn_flags_target(kairn-api-checks-handler "${_api}/checks_handler.cpp" "${_flags_debug}" ON ${_api_warnings})

set(_flags_names ${_names} PARENT_SCOPE)
set(_flags_gen_runners ${_gen_runners} PARENT_SCOPE)
set(_flags_gen_labels ${_gen_labels} PARENT_SCOPE)
list(JOIN _described ", " _described)
list(JOIN _gen_labels ", " _gen_labels)
message(STATUS "Kairn tests: the flag sets ${_described}; the kernels' runners ${_gen_labels}")
