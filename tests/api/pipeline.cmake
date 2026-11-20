# The oracle's verdict on one kernel's claims, as computed through the public interface: for each
# runner and each form the runner maps to the kernel (runner --forms KERNEL), the pipeline
#
#   python3 oracle/kairn-oracle gen KERNEL FORMAT --seed S --count N | runner --form F
#     | python3 oracle/kairn-oracle check --fail-on-suspicious
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DRUNNERS=LABEL|EXECUTABLE|LABEL|EXECUTABLE...
#         -DKERNEL=... -DFORMAT=... -DCOUNT=N -DSEED=S -DSUMMARY_DIR=DIR
#         [-DFIRST_FORM=LABEL|LABEL...] -P pipeline.cmake
#
# The runners named in FIRST_FORM complete the requests with the kernel's first form only, its
# canonical one, and the others with every form (the debug build in the quick tier, whose runner
# takes two to three times as long: tests/api/CMakeLists.txt).
#
# The requests are generated once, into a file, and every runner completes the same file with
# every form (../run_runners.py). Every output is judged, but an output identical byte for byte to one judged before is
# not judged again: the oracle's verdict and summary depend on nothing but the lines it reads (and
# the claims), so the verdict of the first is that of every form that wrote the same bytes.
#
# The oracle's report is printed for every output judged. The test fails if a stage of a pipeline
# fails (the oracle exits non-zero on any violated claim, invalid case or broken stream; a runner,
# when a form that computes only some lines of its kernel computed none), if a runner maps no form
# to the kernel, if a form judged nothing, or if a form's cases missed a stratum the request
# generator announced: a pass must mean that the claims were checked.
cmake_minimum_required(VERSION 3.21)

foreach(_var PYTHON SOURCE_DIR RUNNERS KERNEL FORMAT COUNT SEED SUMMARY_DIR)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "pipeline.cmake: ${_var} is not set")
  endif()
endforeach()
# The stages run in SOURCE_DIR: a relative SUMMARY_DIR is taken from where cmake runs.
get_filename_component(SUMMARY_DIR "${SUMMARY_DIR}" ABSOLUTE)
string(REPLACE "|" ";" _pairs "${RUNNERS}")
string(REPLACE "|" ";" _first_form "${FIRST_FORM}")
list(LENGTH _pairs _n)
math(EXPR _odd "${_n} % 2")
if(_n EQUAL 0 OR _odd)
  message(FATAL_ERROR "pipeline.cmake: RUNNERS must be LABEL|EXECUTABLE pairs, not '${RUNNERS}'")
endif()

set(_oracle "${PYTHON}" "${SOURCE_DIR}/oracle/kairn-oracle")
set(_work "${SUMMARY_DIR}/${KERNEL}.${FORMAT}.work")
file(REMOVE_RECURSE "${_work}")
file(MAKE_DIRECTORY "${_work}")
set(_requests "${_work}/requests.txt")
execute_process(
  COMMAND ${_oracle} gen "${KERNEL}" "${FORMAT}" --seed "${SEED}" --count "${COUNT}"
  OUTPUT_FILE "${_requests}"
  WORKING_DIRECTORY "${SOURCE_DIR}"
  RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "the request generator failed (${_status}) for ${KERNEL} ${FORMAT}")
endif()

# The verdict on one output of a form: "" if it passed, the reason otherwise.
function(_kairn_judge output summary out_failure)
  file(REMOVE "${summary}")
  execute_process(
    COMMAND ${_oracle} check --fail-on-suspicious --json "${summary}"
    INPUT_FILE "${output}"
    WORKING_DIRECTORY "${SOURCE_DIR}"
    RESULT_VARIABLE _check)
  if(NOT _check STREQUAL "0")
    set(${out_failure} "oracle check ${_check}; 0 is success" PARENT_SCOPE)
    return()
  endif()
  # Something was judged, in every stratum the generator announced.
  file(READ "${summary}" _json)
  string(JSON _strata GET "${_json}" coverage 0 desc strata)
  string(REPLACE "," ";" _strata "${_strata}")
  string(JSON _keys LENGTH "${_json}" keys)
  set(_judged 0)
  set(_tags "")
  if(_keys GREATER 0)
    math(EXPR _last "${_keys} - 1")
    foreach(_i RANGE ${_last})
      string(JSON _k GET "${_json}" keys ${_i} stats counts judged)
      math(EXPR _judged "${_judged} + ${_k}")
      string(JSON _tag GET "${_json}" keys ${_i} tag)
      list(APPEND _tags "${_tag}")
    endforeach()
  endif()
  set(_reasons "")
  if(_judged EQUAL 0)
    list(APPEND _reasons "the oracle judged no case")
  endif()
  foreach(_stratum IN LISTS _strata)
    if(NOT _stratum IN_LIST _tags)
      list(APPEND _reasons "no case of stratum ${_stratum} in ${COUNT}")
    endif()
  endforeach()
  list(JOIN _reasons "; " _reasons)
  set(${out_failure} "${_reasons}" PARENT_SCOPE)
endfunction()

# Every form of every runner on the same requests (../run_runners.py), each named LABEL.FORM.
set(_commands "")
set(_n_forms 0)
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _pairs ${_i} _label)
  list(GET _pairs ${_j} _runner)
  execute_process(COMMAND "${_runner}" --forms "${KERNEL}"
    OUTPUT_VARIABLE _forms RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "${_runner} --forms ${KERNEL} failed: ${_status}")
  endif()
  string(STRIP "${_forms}" _forms)
  string(REPLACE "\n" ";" _forms "${_forms}")
  if(NOT _forms)
    message(FATAL_ERROR "no public operation of the API runner ${_label} maps to ${KERNEL}")
  endif()
  if(_label IN_LIST _first_form)
    list(GET _forms 0 _forms)
  endif()
  foreach(_form IN LISTS _forms)
    math(EXPR _n_forms "${_n_forms} + 1")
    set(_what_${_label}.${_form} "${_label}, form ${_form}")
    if(_commands)
      list(APPEND _commands --)
    endif()
    list(APPEND _commands "${_label}.${_form}" "${_runner}" --form "${_form}")
  endforeach()
endforeach()
execute_process(
  COMMAND "${PYTHON}" "${CMAKE_CURRENT_LIST_DIR}/../run_runners.py" "${_requests}" "${_work}" ${_commands}
  WORKING_DIRECTORY "${SOURCE_DIR}"
  OUTPUT_VARIABLE _ran
  RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "run_runners.py failed (${_status}) for ${KERNEL} ${FORMAT}")
endif()
string(STRIP "${_ran}" _ran)
string(REPLACE "\n" ";" _ran "${_ran}")
list(LENGTH _ran _n_ran)
if(NOT _n_ran EQUAL _n_forms)
  message(FATAL_ERROR "run_runners.py reported ${_n_ran} forms of ${_n_forms} for ${KERNEL} ${FORMAT}")
endif()

set(_failed "")
set(_n_judged 0)
foreach(_line IN LISTS _ran)
  string(REPLACE " " ";" _line "${_line}")
  list(GET _line 0 _name)
  list(GET _line 1 _run)
  list(GET _line 2 _first)
  set(_what "${_what_${_name}}")
  if(NOT _run STREQUAL "0")
    message(STATUS "== ${KERNEL} ${FORMAT}, ${_what}: the runner failed (${_run})")
    list(APPEND _failed "${_what} (runner ${_run}; 0 is success)")
    continue()
  endif()
  if(NOT _first STREQUAL _name)
    # The same bytes as an output judged above: the same verdict.
    message(STATUS "== ${KERNEL} ${FORMAT}, ${_what}: the same output, byte for byte, as "
      "${_what_${_first}}, judged above")
    if(_failure_of_${_first})
      list(APPEND _failed "${_what} (the same output as ${_what_${_first}}: ${_failure_of_${_first}})")
    endif()
    continue()
  endif()
  math(EXPR _n_judged "${_n_judged} + 1")
  message(STATUS "== ${KERNEL} ${FORMAT}, ${_what}")
  set(_output "${_work}/${_name}.txt")
  _kairn_judge("${_output}" "${SUMMARY_DIR}/${KERNEL}.${FORMAT}.${_name}.json" _failure)
  set(_failure_of_${_name} "${_failure}")
  if(_failure)
    list(APPEND _failed "${_what} (${_failure})")
  else()
    file(REMOVE "${_output}")
  endif()
endforeach()

if(_failed)
  list(JOIN _failed "\n  " _failed)
  set(_runners "")
  foreach(_i RANGE 0 ${_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _pairs ${_i} _label)
    list(GET _pairs ${_j} _runner)
    string(APPEND _runners "\n  ${_label}: ${_runner}")
  endforeach()
  message(FATAL_ERROR "the public interface failed the claims of ${KERNEL} ${FORMAT} in:\n  ${_failed}\n"
    "To rerun case INDEX of form F: ${PYTHON} oracle/kairn-oracle gen ${KERNEL} ${FORMAT} --seed ${SEED} "
    "--start INDEX --count 1 | RUNNER --form F | ${PYTHON} oracle/kairn-oracle check\n"
    "with RUNNER one of:${_runners}\n"
    "The requests and the outputs that failed are in ${_work}")
endif()
file(REMOVE_RECURSE "${_work}")
message(STATUS "${KERNEL} ${FORMAT}: ${_n_forms} forms of the public interface passed "
  "(distinct outputs judged: ${_n_judged})")
