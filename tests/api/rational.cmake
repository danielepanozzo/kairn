# The oracle's verdict on kairn::rational (rational.hpp): for each runner of rational_runner.cpp,
# the pipeline
#
#   python3 oracle/kairn-oracle gen KIND FORMAT --seed S --count N | runner
#     | python3 oracle/kairn-oracle check --json FILE
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DRUNNERS=LABEL|EXECUTABLE|LABEL|EXECUTABLE...
#         -DKIND=rational_1|rational_2 -DFORMAT=binary64|binary32 -DCOUNT=N -DSEED=S
#         -DSUMMARY_DIR=DIR -P rational.cmake
#
# The specification fixes every bit of the result, so the oracle compares each completed line for
# equality, not against a bound (docs/reference/rational.md). The requests are generated once, into
# a file, and every runner completes the same file (../run_runners.py); an output identical byte for
# byte to one judged before has its verdict. Before the oracle judges an output, this script checks
# its shape: as many completed lines as requests, each the request, " -> ", and K limbs, the error
# and 0 or 1. The test fails if a stage fails (the oracle exits non-zero on any wrong line or broken
# stream), if the generator wrote no request, or if an output has the wrong shape: a pass must mean
# that every line was judged.
cmake_minimum_required(VERSION 3.21)

foreach(_var PYTHON SOURCE_DIR RUNNERS KIND FORMAT COUNT SEED SUMMARY_DIR)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "rational.cmake: ${_var} is not set")
  endif()
endforeach()
if(KIND STREQUAL "rational_1")
  set(_limbs 1)
elseif(KIND STREQUAL "rational_2")
  set(_limbs 2)
else()
  message(FATAL_ERROR "rational.cmake: KIND is rational_1 or rational_2, not '${KIND}'")
endif()
get_filename_component(SUMMARY_DIR "${SUMMARY_DIR}" ABSOLUTE)
string(REPLACE "|" ";" _pairs "${RUNNERS}")
list(LENGTH _pairs _n)
math(EXPR _odd "${_n} % 2")
if(_n EQUAL 0 OR _odd)
  message(FATAL_ERROR "rational.cmake: RUNNERS must be LABEL|EXECUTABLE pairs, not '${RUNNERS}'")
endif()

set(_oracle "${PYTHON}" "${SOURCE_DIR}/oracle/kairn-oracle")
set(_work "${SUMMARY_DIR}/${KIND}.${FORMAT}.work")
file(REMOVE_RECURSE "${_work}")
file(MAKE_DIRECTORY "${_work}")
set(_requests "${_work}/requests.txt")
execute_process(
  COMMAND ${_oracle} gen "${KIND}" "${FORMAT}" --seed "${SEED}" --count "${COUNT}"
  OUTPUT_FILE "${_requests}"
  WORKING_DIRECTORY "${SOURCE_DIR}"
  RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "the request generator failed (${_status}) for ${KIND} ${FORMAT}")
endif()
file(STRINGS "${_requests}" _request_lines)
set(_n_requests 0)
foreach(_line IN LISTS _request_lines)
  string(REGEX REPLACE "\r$" "" _line "${_line}")  # a generator's CR LF on Windows
  if(NOT _line STREQUAL "" AND NOT _line MATCHES "^#")
    math(EXPR _n_requests "${_n_requests} + 1")
  endif()
endforeach()
if(_n_requests EQUAL 0)
  message(FATAL_ERROR "the request generator wrote no request for ${KIND} ${FORMAT}")
endif()

# The shape of a completed stream: "" if it is right, the reason otherwise.
set(_field "([-]?0x[0-9a-f]+(\\.[0-9a-f]*)?p[-+][0-9]+|inf|-inf|nan)")
set(_shape "^${KIND} ${FORMAT} -?[0-9]+ -?[0-9]+( #[^ ]+)? ->")
foreach(_i RANGE 1 ${_limbs})
  string(APPEND _shape " ${_field}")
endforeach()
string(APPEND _shape " ${_field} [01]$")
function(_kairn_rational_shape output out_reason)
  file(STRINGS "${output}" _lines)
  set(_completed 0)
  foreach(_line IN LISTS _lines)
    string(REGEX REPLACE "\r$" "" _line "${_line}")
    if(_line STREQUAL "" OR _line MATCHES "^#")
      continue()
    endif()
    if(NOT _line MATCHES "${_shape}")
      set(${out_reason} "a line is not a completed ${KIND} line: ${_line}" PARENT_SCOPE)
      return()
    endif()
    math(EXPR _completed "${_completed} + 1")
  endforeach()
  if(NOT _completed EQUAL _n_requests)
    set(${out_reason} "${_completed} completed lines for ${_n_requests} requests" PARENT_SCOPE)
    return()
  endif()
  set(${out_reason} "" PARENT_SCOPE)
endfunction()

set(_commands "")
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _pairs ${_i} _label)
  list(GET _pairs ${_j} _runner)
  if(_commands)
    list(APPEND _commands --)
  endif()
  list(APPEND _commands "${_label}" "${_runner}")
endforeach()
execute_process(
  COMMAND "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/../run_runners.py" "${_requests}" "${_work}" ${_commands}
  WORKING_DIRECTORY "${SOURCE_DIR}"
  OUTPUT_VARIABLE _ran
  RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "run_runners.py failed (${_status}) for ${KIND} ${FORMAT}")
endif()
string(STRIP "${_ran}" _ran)
string(REPLACE "\n" ";" _ran "${_ran}")

set(_failed "")
set(_n_judged 0)
foreach(_line IN LISTS _ran)
  string(REPLACE " " ";" _line "${_line}")
  list(GET _line 0 _name)
  list(GET _line 1 _run)
  list(GET _line 2 _first)
  if(NOT _run STREQUAL "0")
    message(STATUS "== ${KIND} ${FORMAT}, runner ${_name}: failed (${_run})")
    list(APPEND _failed "${_name} (runner ${_run}; 0 is success)")
    continue()
  endif()
  if(NOT _first STREQUAL _name)
    message(STATUS "== ${KIND} ${FORMAT}, runner ${_name}: the same output, byte for byte, as ${_first}")
    if(_failure_of_${_first})
      list(APPEND _failed "${_name} (the same output as ${_first}: ${_failure_of_${_first}})")
    endif()
    continue()
  endif()
  math(EXPR _n_judged "${_n_judged} + 1")
  message(STATUS "== ${KIND} ${FORMAT}, runner ${_name}")
  set(_output "${_work}/${_name}.txt")
  _kairn_rational_shape("${_output}" _failure)
  if(NOT _failure)
    set(_summary "${SUMMARY_DIR}/${KIND}.${FORMAT}.${_name}.json")
    file(REMOVE "${_summary}")
    execute_process(
      COMMAND ${_oracle} check --json "${_summary}"
      INPUT_FILE "${_output}"
      WORKING_DIRECTORY "${SOURCE_DIR}"
      RESULT_VARIABLE _check)
    if(NOT _check STREQUAL "0")
      set(_failure "oracle check ${_check}; 0 is success")
    endif()
  endif()
  set(_failure_of_${_name} "${_failure}")
  if(_failure)
    list(APPEND _failed "${_name} (${_failure})")
  else()
    file(REMOVE "${_output}")
  endif()
endforeach()

if(_failed)
  list(JOIN _failed "\n  " _failed)
  message(FATAL_ERROR "kairn::rational failed the oracle's ${KIND} ${FORMAT} in:\n  ${_failed}\n"
    "To rerun: ${PYTHON} oracle/kairn-oracle gen ${KIND} ${FORMAT} --seed ${SEED} --count ${COUNT} "
    "| RUNNER | ${PYTHON} oracle/kairn-oracle check\n"
    "The requests and the outputs that failed are in ${_work}")
endif()
file(REMOVE_RECURSE "${_work}")
message(STATUS "${KIND} ${FORMAT}: ${_n_requests} requests, every runner passed (distinct outputs judged: "
  "${_n_judged})")
