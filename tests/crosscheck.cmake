# One cross-check (tests/CMakeLists.txt): the oracle's requests for one kernel and format, a
# runner, and the oracle's verdict, as the pipeline
#
#   python3 oracle/kairn-oracle gen KERNEL FORMAT ... | RUNNER | python3 oracle/kairn-oracle check
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DKERNEL=... -DFORMAT=... -DRUNNER=interp|EXECUTABLE
#         -DSUMMARY=FILE (-DEXHAUSTIVE=ON | -DCOUNT=N -DSEED=S) [-DFAIL_ON_SUSPICIOUS=ON]
#         -P crosscheck.cmake
#
# The oracle's report is printed whatever happens. The test fails if a stage of the pipeline
# fails (the oracle exits non-zero on any violated claim, invalid case or broken stream), and also
# if nothing was judged, or an exhaustive run did not cover the whole enumeration, or a random run
# missed a stratum: a pass must mean that the claims were checked.
#
# With -DERROR=MESSAGE instead, it only fails with that message: the test that stands in for a
# cross-check tests/CMakeLists.txt cannot set up.
cmake_minimum_required(VERSION 3.21)

if(DEFINED ERROR)
  message(FATAL_ERROR "${ERROR}")
endif()
foreach(_var PYTHON SOURCE_DIR KERNEL FORMAT RUNNER SUMMARY)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "crosscheck.cmake: ${_var} is not set")
  endif()
endforeach()

set(_oracle "${PYTHON}" "${SOURCE_DIR}/oracle/kairn-oracle")
set(_gen ${_oracle} gen "${KERNEL}" "${FORMAT}")
if(EXHAUSTIVE)
  list(APPEND _gen --exhaustive)
else()
  list(APPEND _gen --seed "${SEED}" --count "${COUNT}")
endif()
if(RUNNER STREQUAL "interp")
  set(_runner "${PYTHON}" "${SOURCE_DIR}/gen/kairn-gen" interp)
else()
  set(_runner "${RUNNER}")
endif()
set(_check ${_oracle} check)
if(FAIL_ON_SUSPICIOUS)
  list(APPEND _check --fail-on-suspicious)
endif()

file(REMOVE "${SUMMARY}")
get_filename_component(_summary_dir "${SUMMARY}" DIRECTORY)
file(MAKE_DIRECTORY "${_summary_dir}")
execute_process(
  COMMAND ${_gen}
  COMMAND ${_runner}
  COMMAND ${_check} --json "${SUMMARY}"
  WORKING_DIRECTORY "${SOURCE_DIR}"
  RESULTS_VARIABLE _results)

# How to run one case again, from the tag of its line in the report: #STRATUM:INDEX or
# #exhaustive:INDEX.
list(JOIN _gen " " _gen_text)
list(JOIN _runner " " _runner_text)
list(JOIN _check " " _check_text)
if(EXHAUSTIVE)
  set(_one "${_gen_text} --start INDEX --count 1")
else()
  string(REPLACE "--count ${COUNT}" "--start INDEX --count 1" _one "${_gen_text}")
endif()
string(CONCAT _again "To run one case again, with INDEX from its tag:\n"
  "  ${_one} | ${_runner_text} | ${_check_text}")

list(GET _results 0 _gen_status)
list(GET _results 1 _runner_status)
list(GET _results 2 _check_status)
if(NOT _gen_status STREQUAL "0" OR NOT _runner_status STREQUAL "0" OR
   NOT _check_status STREQUAL "0")
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER} failed: request "
    "generator ${_gen_status}, runner ${_runner_status}, oracle check ${_check_status} "
    "(0 is success)\n${_again}")
endif()

# A pass must have judged something, and covered what it set out to cover.
file(READ "${SUMMARY}" _json)
string(JSON _keys LENGTH "${_json}" keys)
set(_judged 0)
set(_tags "")
if(_keys GREATER 0)
  math(EXPR _last "${_keys} - 1")
  foreach(_i RANGE ${_last})
    string(JSON _n GET "${_json}" keys ${_i} stats counts judged)
    math(EXPR _judged "${_judged} + ${_n}")
    string(JSON _tag GET "${_json}" keys ${_i} tag)
    list(APPEND _tags "${_tag}")
  endforeach()
endif()
if(_judged EQUAL 0)
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER}: the oracle passed it, "
    "but judged no case (every result non-finite or out of scope), so nothing was checked")
endif()
if(EXHAUSTIVE)
  string(JSON _total GET "${_json}" coverage 0 desc total)
  string(JSON _ranges LENGTH "${_json}" coverage 0 ranges)
  string(JSON _from GET "${_json}" coverage 0 ranges 0 0)
  string(JSON _to GET "${_json}" coverage 0 ranges 0 1)
  if(NOT _ranges EQUAL 1 OR NOT _from EQUAL 0 OR NOT _to EQUAL _total)
    message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER}: the enumeration of "
      "${_total} cases was not covered")
  endif()
else()
  foreach(_stratum uniform close cancel overflow underflow pow2 extreme zero)
    if(NOT _stratum IN_LIST _tags)
      message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER}: no case of stratum "
        "${_stratum} in ${COUNT} cases")
    endif()
  endforeach()
endif()
message(STATUS "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER}: passed, ${_judged} cases judged")
