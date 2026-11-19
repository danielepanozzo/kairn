# A negative compile test: SOURCE must compile with the control options and fail, with a message
# matching EXPECT, with the test options (tests/api/reject.cpp).
#
#   cmake -DCXX=... -DSTYLE=gnu|msvc -DINCLUDE=DIR -DSOURCE=FILE -DCASE=N "-DOPTIONS=a|b"
#         "-DCOMMON=a|b" "-DEXPECT=regex" [-DSYSROOT=...] -P compile_fail.cmake
#
# OPTIONS and COMMON separate their options with |, which survives being passed through add_test.
# Only the front end runs (-fsyntax-only, /Zs): what is tested is whether the program is accepted.
cmake_minimum_required(VERSION 3.21)

foreach(_var CXX STYLE INCLUDE SOURCE CASE EXPECT)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "compile_fail.cmake: ${_var} is not set")
  endif()
endforeach()
string(REPLACE "|" ";" OPTIONS "${OPTIONS}")
string(REPLACE "|" ";" COMMON "${COMMON}")

if(STYLE STREQUAL "msvc")
  set(_base /nologo /std:c++20 /EHsc /Zs "/I${INCLUDE}" "/DKAIRN_TEST_CASE=${CASE}")
  set(_control /DKAIRN_TEST_CONTROL)
else()
  set(_base -std=c++20 -fsyntax-only -I "${INCLUDE}" "-DKAIRN_TEST_CASE=${CASE}")
  if(SYSROOT)
    list(APPEND _base -isysroot "${SYSROOT}")
  endif()
  set(_control -DKAIRN_TEST_CONTROL)
endif()

# The control: the same file, with the marker (or without the rejected option), must compile.
execute_process(COMMAND "${CXX}" ${_base} ${COMMON} ${_control} "${SOURCE}"
  OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "the control does not compile, so the test proves nothing:\n${_out}${_err}")
endif()

execute_process(COMMAND "${CXX}" ${_base} ${COMMON} ${OPTIONS} "${SOURCE}"
  OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
if(_status STREQUAL "0")
  message(FATAL_ERROR "compiled, but must be rejected (case ${CASE}, options: ${OPTIONS})")
endif()
if(NOT "${_out}${_err}" MATCHES "${EXPECT}")
  message(FATAL_ERROR "rejected, but without the expected message (${EXPECT}):\n${_out}${_err}")
endif()
string(REGEX MATCH "[^\n]*(${EXPECT})[^\n]*" _line "${_out}${_err}")
message(STATUS "rejected as expected: ${_line}")
