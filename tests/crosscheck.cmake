# One cross-check (tests/CMakeLists.txt): the oracle's requests for one kernel and format, a
# runner, and the oracle's verdict, as the pipeline
#
#   python3 oracle/kairn-oracle gen KERNEL FORMAT ... | RUNNER | python3 oracle/kairn-oracle check
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DKERNEL=... -DFORMAT=... -DRUNNER=interp|EXECUTABLE
#         -DSUMMARY=FILE (-DEXHAUSTIVE=ON [-DRESTRICT=R1,R2,...] | -DCOUNT=N -DSEED=S)
#         [-DFAIL_ON_SUSPICIOUS=ON] -P crosscheck.cmake
#
# RESTRICT is a comma-separated list of the oracle's restrictions (NAME.lead=LO:HI,
# NAME.sign=+|-, NAME.in=V1/V2/...), as the generator's header writes them.
#
# The oracle's report is printed whatever happens. The test fails if a stage of the pipeline
# fails (the oracle exits non-zero on any violated claim, invalid case or broken stream), and also
# when the run did not check what it set out to check, which crosscheck_guards.py decides from
# the oracle's summary: a pass must mean that the claims were checked. In short, the stream must
# be the one asked for and be seen whole; an exhaustive run must cover its enumeration, over
# every operand or exactly the restricted domain asked for; a random run must have a case of
# every stratum the oracle's generator lists for the kernel; something must be judged, every
# claim must apply to some judged case, a comparison must see both outcomes and a directed
# rounding must step.
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
set(_guards "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/crosscheck_guards.py" "${SUMMARY}"
  --kernel "${KERNEL}" --format "${FORMAT}")
if(EXHAUSTIVE)
  list(APPEND _gen --exhaustive)
  list(APPEND _guards --exhaustive)
  if(RESTRICT)
    string(REPLACE "," ";" _restrictions "${RESTRICT}")
    foreach(_r IN LISTS _restrictions)
      list(APPEND _gen --restrict "${_r}")
    endforeach()
    list(APPEND _guards --restrict "${RESTRICT}")
  endif()
else()
  foreach(_var COUNT SEED)
    if(NOT DEFINED ${_var})
      message(FATAL_ERROR "crosscheck.cmake: ${_var} is not set")
    endif()
  endforeach()
  list(APPEND _gen --seed "${SEED}" --count "${COUNT}")
  list(APPEND _guards --seed "${SEED}" --count "${COUNT}")
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

set(_what "cross-check of ${KERNEL} ${FORMAT} with ${RUNNER}")
list(GET _results 0 _gen_status)
list(GET _results 1 _runner_status)
list(GET _results 2 _check_status)
if(NOT _gen_status STREQUAL "0" OR NOT _runner_status STREQUAL "0" OR
   NOT _check_status STREQUAL "0")
  message(FATAL_ERROR "${_what} failed: request generator ${_gen_status}, runner "
    "${_runner_status}, oracle check ${_check_status} (0 is success)\n${_again}")
endif()

# A pass must have checked what it set out to check.
execute_process(
  COMMAND ${_guards}
  WORKING_DIRECTORY "${SOURCE_DIR}"
  RESULT_VARIABLE _guard_status
  OUTPUT_VARIABLE _guard_output
  ERROR_VARIABLE _guard_output)
string(STRIP "${_guard_output}" _guard_output)
if(NOT _guard_status STREQUAL "0")
  message(FATAL_ERROR "${_what}: the oracle passed it, but it did not check what it set out "
    "to:\n${_guard_output}")
endif()
message(STATUS "${_what}: passed, ${_guard_output}")
