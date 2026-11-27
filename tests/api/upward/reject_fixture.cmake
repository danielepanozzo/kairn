# A negative compile test of kairn/upward.hpp against a copy of the headers in which kernels of the
# round-up interval are marked unverified (../reject.cpp, cases 137 to 146): the headers are copied
# into UPWARD_FIXTURE with every kernel of kairn/gen/upward.hpp marked unverified, or with
# -DUPWARD_ONLY=a|b only those, so that the marker kairn::unverified is tested whatever the proofs
# say, and what another, proved kernel would let compile through a conversion is tested too; then
# ../compile_fail.cmake runs on the copy. Requires the rounding mode upward set by
# kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
# MSVC /fp:strict), which CMakeLists.txt gives to both compilations.
#
#   cmake <the variables of ../compile_fail.cmake> -DUPWARD_FIXTURE=DIR [-DUPWARD_ONLY=a|b]
#         -P reject_fixture.cmake
#
# The kernels' statuses are the specializations of kairn::gen::upward::bounds, one line each,
# `template <> struct K<double> { static constexpr bool proved = true; };` and its float twin.
cmake_minimum_required(VERSION 3.21)

foreach(_var INCLUDE UPWARD_FIXTURE)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "reject_fixture.cmake: ${_var} is not set")
  endif()
endforeach()

file(REMOVE_RECURSE "${UPWARD_FIXTURE}")
file(COPY "${INCLUDE}/kairn" DESTINATION "${UPWARD_FIXTURE}")
set(_header "${UPWARD_FIXTURE}/kairn/gen/upward.hpp")
file(READ "${_header}" _text)
# The patterns stop before the semicolon, which would split a match as a CMake list.
set(_proved "{ static constexpr bool proved = true")
set(_unverified "{ static constexpr bool proved = false")
if(UPWARD_ONLY)
  string(REPLACE "|" ";" _only "${UPWARD_ONLY}")
  foreach(_k IN LISTS _only)
    string(REGEX MATCHALL "template <> struct ${_k}<(double|float)> ${_proved}" _found "${_text}")
    list(LENGTH _found _n)
    if(NOT _n EQUAL 2)
      message(FATAL_ERROR "could not find the two proved specializations of ${_k} in ${_header}")
    endif()
    string(REGEX REPLACE "template <> struct ${_k}<(double|float)> ${_proved}"
      "template <> struct ${_k}<\\1> ${_unverified}" _text "${_text}")
  endforeach()
  string(REGEX MATCHALL "template <> struct upward_[a-z0-9_]+<(double|float)> ${_proved}" _left "${_text}")
  if(NOT _left)
    message(FATAL_ERROR "marking ${UPWARD_ONLY} unverified left no kernel of the round-up interval proved")
  endif()
else()
  string(REGEX MATCHALL "template <> struct upward_[a-z0-9_]+<(double|float)> ${_proved}" _all "${_text}")
  list(LENGTH _all _n)
  if(_n EQUAL 0)
    message(FATAL_ERROR "found no proved kernel of the round-up interval in ${_header}")
  endif()
  string(REGEX REPLACE "template <> struct (upward_[a-z0-9_]+)<(double|float)> ${_proved}"
    "template <> struct \\1<\\2> ${_unverified}" _text "${_text}")
endif()
file(WRITE "${_header}" "${_text}")
set(INCLUDE "${UPWARD_FIXTURE}")
include("${CMAKE_CURRENT_LIST_DIR}/../compile_fail.cmake")
