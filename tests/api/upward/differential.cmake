# api.upward.differential: runs the differential program (differential.cpp), which compares every
# operation of <kairn/upward.hpp> with the default kairn::Interval<T, 1> and writes every upward
# result as a completed line of the line protocol, then the oracle's check on those lines, in exact
# arithmetic: every case valid and passed, nothing suspicious. Fails if either fails; removes the
# lines on a pass. Requires the rounding mode upward set by kairn::upward::Scope and the options of
# docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict), with which the program
# is built.
#
#   cmake -DPROGRAM=path -DPYTHON=path -DORACLE=oracle/kairn-oracle -DCLAIMS=gen/claims.json
#         -DLINES=path -P differential.cmake
execute_process(COMMAND "${PROGRAM}" "${LINES}" RESULT_VARIABLE _rc)
if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "${PROGRAM} exited with ${_rc}: a comparison with the default type failed (above)")
endif()
execute_process(COMMAND "${PYTHON}" "${ORACLE}" check --claims "${CLAIMS}" --expect-valid --fail-on-suspicious
  "${LINES}" OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _rc)
string(REGEX MATCH "[0-9]+ cases: [^\n]*" _summary "${_out}")
if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "the oracle failed the upward results (status ${_rc}); the lines are kept in ${LINES}:\n"
    "${_out}${_err}")
endif()
if(NOT _summary)
  message(FATAL_ERROR "the oracle printed no summary of its cases:\n${_out}${_err}")
endif()
message(STATUS "the oracle: ${_summary}")
file(REMOVE "${LINES}")
