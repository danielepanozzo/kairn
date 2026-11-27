# api.upward.moves.LEVEL: ../moves.cpp, what the compiler does to code next to the boundary of a
# scope of <kairn/upward.hpp>, at each optimization level of the compiler whatever the build's own
# flags (docs/developer/testing.md, "Code next to a scope's boundary"). Requires the rounding mode
# upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
# -frounding-math, MSVC /fp:strict): every program here links kairn::upward.
#
# The flags of the build's configuration (CMAKE_CXX_FLAGS_RELEASE and the others: -O3 -DNDEBUG,
# /O2 /Ob2 /DNDEBUG, and Debug's /RTC1, which refuses /O2) are emptied in this directory, as in
# ../../flags/, so that each program gets its level, NDEBUG and KAIRN_CHECKS 0 and nothing else:
#
#   GCC, Clang, Apple clang   -O0, -O1, -O2, -O3
#   MSVC                      /Od, /O1, /O2, and /O2 /GL linked with /LTCG (whole-program
#                             optimization at link time, where MSVC sees the whole program)
#   clang-cl                  /Od, /O1, /O2
#
# ../CMakeLists.txt builds the other forms of moves.cpp with the build's flags: the two-number form,
# the AVX2 form of the functions on arrays, a checked build, and with Clang a build without the
# options.
set(_moves_configs DEBUG RELEASE RELWITHDEBINFO MINSIZEREL ${CMAKE_CONFIGURATION_TYPES} ${CMAKE_BUILD_TYPE})
foreach(_config IN LISTS _moves_configs)
  string(TOUPPER "${_config}" _config)
  set(CMAKE_CXX_FLAGS_${_config} "")
endforeach()

# Each "NAME OPTIONS...".
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_moves_levels "Od /Od" "O1 /O1" "O2 /O2" "O2_GL /O2 /GL")
elseif(_msvc_style)
  set(_moves_levels "Od /Od" "O1 /O1" "O2 /O2")
else()
  set(_moves_levels "O0 -O0" "O1 -O1" "O2 -O2" "O3 -O3")
endif()

set(_moves_tests "")
foreach(_entry IN LISTS _moves_levels)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(POP_FRONT _words _name)
  list(JOIN _words " " _text)
  set(_target kairn-api-upward-moves-${_name})
  _kairn_upward_program(${_target} ../moves.cpp)
  target_compile_options(${_target} PRIVATE ${_words})
  target_compile_definitions(${_target} PRIVATE NDEBUG KAIRN_CHECKS=0 "UPWARD_TEST_LEVEL=\"${_text}\"")
  if(_msvc_style)
    set_target_properties(${_target} PROPERTIES MSVC_RUNTIME_LIBRARY MultiThreadedDLL)
  endif()
  if("/GL" IN_LIST _words)
    target_link_options(${_target} PRIVATE /LTCG)
  endif()
  add_test(NAME api.upward.moves.${_name} COMMAND ${_target})
  list(APPEND _moves_tests api.upward.moves.${_name})
endforeach()
set_tests_properties(${_moves_tests} PROPERTIES TIMEOUT 120 LABELS "api;upward;quick")
