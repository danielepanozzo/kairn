# One cross-check (tests/CMakeLists.txt): the oracle's requests for one kernel and format, a
# runner, and the oracle's verdict, as the pipeline
#
#   python3 oracle/kairn-oracle gen KERNEL FORMAT ... | RUNNER | python3 oracle/kairn-oracle check
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DKERNEL=... -DFORMAT=... -DSUMMARY=FILE
#         (-DRUNNER=interp | -DRUNNERS=LABEL|EXECUTABLE|LABEL|EXECUTABLE...)
#         (-DEXHAUSTIVE=ON [-DRESTRICT=R1,R2,...] | -DCOUNT=N -DSEED=S)
#         [-DFAIL_ON_SUSPICIOUS=ON] -P crosscheck.cmake
#
# RESTRICT is a comma-separated list of the oracle's restrictions (NAME.lead=LO:HI,
# NAME.sign=+|-, NAME.in=V1/V2/...), as the generator's header writes them.
#
# RUNNERS names the compiled runners of this build, each with a label: the requests are generated
# once, into a file, and every runner completes the same file (run_runners.py). Every output is
# judged, but an output identical byte for byte to one judged before is not judged again: the
# oracle's verdict and its summary depend on nothing but the lines it reads (and the claims), so
# the verdict of the first is that of every runner that wrote the same bytes, and the report says
# which runners share it. Each summary judged is written next to SUMMARY, as SUMMARY's name with
# the label of the first runner that wrote that output.
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
foreach(_var PYTHON SOURCE_DIR KERNEL FORMAT SUMMARY)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "crosscheck.cmake: ${_var} is not set")
  endif()
endforeach()
if(NOT DEFINED RUNNER AND NOT DEFINED RUNNERS)
  message(FATAL_ERROR "crosscheck.cmake: RUNNER or RUNNERS is not set")
endif()
# The stages run in SOURCE_DIR: a relative SUMMARY is taken from where cmake runs.
get_filename_component(SUMMARY "${SUMMARY}" ABSOLUTE)

set(_oracle "${PYTHON}" "${SOURCE_DIR}/oracle/kairn-oracle")
set(_gen ${_oracle} gen "${KERNEL}" "${FORMAT}")
set(_guards "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/crosscheck_guards.py")
set(_guard_args --kernel "${KERNEL}" --format "${FORMAT}")
if(EXHAUSTIVE)
  list(APPEND _gen --exhaustive)
  list(APPEND _guard_args --exhaustive)
  if(RESTRICT)
    string(REPLACE "," ";" _restrictions "${RESTRICT}")
    foreach(_r IN LISTS _restrictions)
      list(APPEND _gen --restrict "${_r}")
    endforeach()
    list(APPEND _guard_args --restrict "${RESTRICT}")
  endif()
else()
  foreach(_var COUNT SEED)
    if(NOT DEFINED ${_var})
      message(FATAL_ERROR "crosscheck.cmake: ${_var} is not set")
    endif()
  endforeach()
  list(APPEND _gen --seed "${SEED}" --count "${COUNT}")
  list(APPEND _guard_args --seed "${SEED}" --count "${COUNT}")
endif()
set(_check ${_oracle} check)
if(FAIL_ON_SUSPICIOUS)
  list(APPEND _check --fail-on-suspicious)
endif()

# How to run one case again, from the tag of its line in the report: #STRATUM:INDEX or
# #exhaustive:INDEX.
list(JOIN _gen " " _gen_text)
list(JOIN _check " " _check_text)
if(EXHAUSTIVE)
  set(_one "${_gen_text} --start INDEX --count 1")
else()
  string(REPLACE "--count ${COUNT}" "--start INDEX --count 1" _one "${_gen_text}")
endif()

# The guards on the summary of a run the oracle passed: "" if they pass, their reason otherwise.
function(_kairn_guards summary out_failure out_report)
  execute_process(
    COMMAND ${_guards} "${summary}" ${_guard_args}
    WORKING_DIRECTORY "${SOURCE_DIR}"
    RESULT_VARIABLE _status
    OUTPUT_VARIABLE _output
    ERROR_VARIABLE _output)
  string(STRIP "${_output}" _output)
  if(_status STREQUAL "0")
    set(${out_failure} "" PARENT_SCOPE)
  else()
    set(${out_failure} "${_output}" PARENT_SCOPE)
  endif()
  set(${out_report} "${_output}" PARENT_SCOPE)
endfunction()

# --- The interpreter: one pipeline, its three stages at once ------------------------------------
if(DEFINED RUNNER)
  if(RUNNER STREQUAL "interp")
    set(_runner "${PYTHON}" "${SOURCE_DIR}/gen/kairn-gen" interp)
  else()
    set(_runner "${RUNNER}")
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

  list(JOIN _runner " " _runner_text)
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
  _kairn_guards("${SUMMARY}" _failure _report)
  if(_failure)
    message(FATAL_ERROR "${_what}: the oracle passed it, but it did not check what it set out "
      "to:\n${_failure}")
  endif()
  message(STATUS "${_what}: passed, ${_report}")
  return()
endif()

# --- The compiled runners: the same requests for every runner -----------------------------------
string(REPLACE "|" ";" _pairs "${RUNNERS}")
list(LENGTH _pairs _n)
math(EXPR _odd "${_n} % 2")
if(_n EQUAL 0 OR _odd)
  message(FATAL_ERROR "crosscheck.cmake: RUNNERS must be LABEL|EXECUTABLE pairs, not '${RUNNERS}'")
endif()
get_filename_component(_summary_dir "${SUMMARY}" DIRECTORY)
get_filename_component(_summary_base "${SUMMARY}" NAME_WLE)
set(_work "${_summary_dir}/${_summary_base}.work")
file(REMOVE_RECURSE "${_work}")
file(MAKE_DIRECTORY "${_work}")
set(_requests "${_work}/requests.txt")

execute_process(
  COMMAND ${_gen}
  OUTPUT_FILE "${_requests}"
  WORKING_DIRECTORY "${SOURCE_DIR}"
  RESULT_VARIABLE _gen_status)
if(NOT _gen_status STREQUAL "0")
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT}: the request generator failed "
    "(${_gen_status}): ${_gen_text}")
endif()

# Every runner on the same requests (run_runners.py), then the oracle on each distinct output.
set(_commands "")
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _pairs ${_i} _label)
  list(GET _pairs ${_j} _exe)
  set(_exe_of_${_label} "${_exe}")
  if(_commands)
    list(APPEND _commands --)
  endif()
  list(APPEND _commands "${_label}" "${_exe}")
endforeach()
execute_process(
  COMMAND "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/run_runners.py" "${_requests}" "${_work}" ${_commands}
  WORKING_DIRECTORY "${SOURCE_DIR}"
  OUTPUT_VARIABLE _ran
  RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT}: run_runners.py failed (${_status})")
endif()
string(STRIP "${_ran}" _ran)
string(REPLACE "\n" ";" _ran "${_ran}")
list(LENGTH _ran _n_ran)
math(EXPR _n_runners "${_n} / 2")
if(NOT _n_ran EQUAL _n_runners)
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT}: run_runners.py reported ${_n_ran} runners "
    "of ${_n_runners}")
endif()

set(_failed "")         # one line per runner that failed
set(_passed "")         # the runners whose output passed, each the first of those that wrote it
foreach(_line IN LISTS _ran)
  string(REPLACE " " ";" _line "${_line}")
  list(GET _line 0 _label)
  list(GET _line 1 _runner_status)
  list(GET _line 2 _first)
  set(_exe "${_exe_of_${_label}}")
  set(_what "cross-check of ${KERNEL} ${FORMAT} with ${_label}")
  set(_again "  ${_one} | ${_exe} | ${_check_text}")
  if(NOT _runner_status STREQUAL "0")
    message(STATUS "${_what}: the runner failed (${_runner_status})")
    list(APPEND _failed "${_label}: the runner failed (${_runner_status}); to run one case again:\n${_again}")
    continue()
  endif()
  if(NOT _first STREQUAL _label)
    # The same bytes as an output judged above: the same verdict.
    message(STATUS "${_what}: the same output, byte for byte, as ${_first}'s, judged above")
    if(_failed_${_first})
      list(APPEND _failed "${_label}: the same output as ${_first}, which failed")
    endif()
    list(APPEND _sharing_${_first} "${_label}")
    continue()
  endif()
  set(_sharing_${_label} "${_label}")
  set(_output "${_work}/${_label}.txt")
  set(_summary "${_summary_dir}/${_summary_base}.${_label}.json")
  file(REMOVE "${_summary}")
  message(STATUS "== ${_what}: the oracle's report")
  execute_process(
    COMMAND ${_check} --json "${_summary}"
    INPUT_FILE "${_output}"
    WORKING_DIRECTORY "${SOURCE_DIR}"
    RESULT_VARIABLE _check_status)
  if(NOT _check_status STREQUAL "0")
    set(_failed_${_label} ON)
    list(APPEND _failed "${_label}: oracle check ${_check_status} (0 is success); to run one case "
      "again, with INDEX from its tag:\n${_again}")
    continue()
  endif()
  # A pass must have checked what it set out to check.
  _kairn_guards("${_summary}" _failure _report)
  if(_failure)
    set(_failed_${_label} ON)
    list(APPEND _failed "${_label}: the oracle passed it, but it did not check what it set out to:\n${_failure}")
    continue()
  endif()
  file(REMOVE "${_output}")
  list(APPEND _passed "${_label}")
  set(_report_of_${_label} "${_report}")
endforeach()

if(_failed)
  string(JOIN "\n" _failed ${_failed})
  message(FATAL_ERROR "cross-check of ${KERNEL} ${FORMAT} failed for:\n${_failed}\n"
    "The requests and the outputs that failed are in ${_work}")
endif()
foreach(_label IN LISTS _passed)
  list(JOIN _sharing_${_label} ", " _who)
  message(STATUS "cross-check of ${KERNEL} ${FORMAT} with ${_who}: passed, ${_report_of_${_label}}")
endforeach()
file(REMOVE_RECURSE "${_work}")
