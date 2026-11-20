# A negative compile test: SOURCE must compile with the control options and fail, with a message
# matching EXPECT, with the test options (tests/api/reject.cpp).
#
#   cmake -DCXX=... -DSTYLE=gnu|msvc -DINCLUDE=DIR -DSOURCE=FILE -DCASE=N "-DOPTIONS=a|b"
#         "-DCOMMON=a|b" "-DEXPECT=regex" [-DSYSROOT=...] [-DUNVERIFIED_FIXTURE=DIR ...]
#         [-DRATIONAL_FAULT_FIXTURE=DIR] -P compile_fail.cmake
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

# With -DUNVERIFIED_FIXTURE=DIR, the headers are first copied into DIR with every kernel of
# kairn/gen/bounds.hpp marked unverified, so that the marker is tested whatever the proofs say;
# with -DUNVERIFIED_ONLY=a|b as well, only those kernels, so that what another, proved kernel
# would let compile through a conversion is tested too.
if(UNVERIFIED_FIXTURE)
  file(REMOVE_RECURSE "${UNVERIFIED_FIXTURE}")
  file(COPY "${INCLUDE}/kairn" DESTINATION "${UNVERIFIED_FIXTURE}")
  set(_bounds "${UNVERIFIED_FIXTURE}/kairn/gen/bounds.hpp")
  file(READ "${_bounds}" _text)
  if(UNVERIFIED_ONLY)
    string(REPLACE "|" ";" _only "${UNVERIFIED_ONLY}")
    set(_fixture "${_text}")
    foreach(_k IN LISTS _only)
      string(REGEX MATCHALL "template <> struct ${_k}<(double|float)> {" _found "${_fixture}")
      list(LENGTH _found _n)
      if(NOT _n EQUAL 2)
        message(FATAL_ERROR "could not find the two specializations of ${_k} in ${_bounds}")
      endif()
      string(REGEX REPLACE "template <> struct ${_k}<(double|float)> {[^}]*};"
        "template <> struct ${_k}<\\1> { static constexpr bool proved = false; };" _fixture "${_fixture}")
    endforeach()
    string(REGEX MATCHALL "proved = true" _left "${_fixture}")
    if(NOT _left)
      message(FATAL_ERROR "marking ${UNVERIFIED_ONLY} unverified left no kernel proved")
    endif()
  else()
    string(REGEX REPLACE "template <> struct ([a-z0-9_]+)<(double|float)> {[^}]*};"
      "template <> struct \\1<\\2> { static constexpr bool proved = false; };" _fixture "${_text}")
    string(REGEX MATCHALL "proved = true" _left "${_fixture}")
    string(REGEX MATCHALL "proved = false" _all "${_fixture}")
    list(LENGTH _all _n)
    if(_left OR _n EQUAL 0)
      message(FATAL_ERROR "could not mark every kernel of ${_bounds} unverified")
    endif()
  endif()
  file(WRITE "${_bounds}" "${_fixture}")
  set(INCLUDE "${UNVERIFIED_FIXTURE}")
endif()

# With -DRATIONAL_FAULT_FIXTURE=DIR, the headers are first copied into DIR with a fault planted in
# kairn::rational: the flag exact of every result inverted, so that the check of KAIRN_RATIONAL_CHECK
# has a wrong result to refuse.
if(RATIONAL_FAULT_FIXTURE)
  file(REMOVE_RECURSE "${RATIONAL_FAULT_FIXTURE}")
  file(COPY "${INCLUDE}/kairn" DESTINATION "${RATIONAL_FAULT_FIXTURE}")
  set(_rational "${RATIONAL_FAULT_FIXTURE}/kairn/rational.hpp")
  file(READ "${_rational}" _text)
  # The pattern stops before the semicolon, which would split the match as a CMake list.
  string(REGEX MATCHALL "\n    c\\.exact = r\\.exact" _found "${_text}")
  list(LENGTH _found _n)
  if(NOT _n EQUAL 1)
    message(FATAL_ERROR "could not find the one line 'c.exact = r.exact;' in ${_rational} (${_n} found)")
  endif()
  # Without the line ends, which a checkout on Windows may have as CR LF.
  string(REPLACE "    c.exact = r.exact;" "    c.exact = !r.exact;  // the fault" _text "${_text}")
  file(WRITE "${_rational}" "${_text}")
  set(INCLUDE "${RATIONAL_FAULT_FIXTURE}")
endif()

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
