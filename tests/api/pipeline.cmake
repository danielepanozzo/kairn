# The oracle's verdict on one kernel's claims, as computed through the public interface: for each
# form the API runner maps to the kernel (runner --forms KERNEL), the pipeline
#
#   python3 oracle/kairn-oracle gen KERNEL FORMAT --seed S --count N | runner --form F
#     | python3 oracle/kairn-oracle check --fail-on-suspicious
#
#   cmake -DPYTHON=... -DSOURCE_DIR=... -DRUNNER=... -DKERNEL=... -DFORMAT=... -DCOUNT=N -DSEED=S
#         -DSUMMARY_DIR=DIR -P pipeline.cmake
#
# The oracle's report is printed for every form. The test fails if a stage of a pipeline fails
# (the oracle exits non-zero on any violated claim, invalid case or broken stream), if the runner
# maps no form to the kernel, if a form judged nothing, or if a form's cases missed a stratum the
# request generator announced: a pass must mean that the claims were checked.
cmake_minimum_required(VERSION 3.21)

foreach(_var PYTHON SOURCE_DIR RUNNER KERNEL FORMAT COUNT SEED SUMMARY_DIR)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "pipeline.cmake: ${_var} is not set")
  endif()
endforeach()

execute_process(COMMAND "${RUNNER}" --forms "${KERNEL}"
  OUTPUT_VARIABLE _forms RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "${RUNNER} --forms ${KERNEL} failed: ${_status}")
endif()
string(STRIP "${_forms}" _forms)
string(REPLACE "\n" ";" _forms "${_forms}")
if(NOT _forms)
  message(FATAL_ERROR "no public operation of the API runner maps to ${KERNEL}")
endif()

set(_oracle "${PYTHON}" "${SOURCE_DIR}/oracle/kairn-oracle")
file(MAKE_DIRECTORY "${SUMMARY_DIR}")
set(_failed "")
foreach(_form IN LISTS _forms)
  set(_summary "${SUMMARY_DIR}/${KERNEL}.${FORMAT}.${_form}.json")
  file(REMOVE "${_summary}")
  message(STATUS "== ${KERNEL} ${FORMAT}, form ${_form}")
  execute_process(
    COMMAND ${_oracle} gen "${KERNEL}" "${FORMAT}" --seed "${SEED}" --count "${COUNT}"
    COMMAND "${RUNNER}" --form "${_form}"
    COMMAND ${_oracle} check --fail-on-suspicious --json "${_summary}"
    WORKING_DIRECTORY "${SOURCE_DIR}"
    RESULTS_VARIABLE _results)
  list(GET _results 0 _gen)
  list(GET _results 1 _run)
  list(GET _results 2 _check)
  if(NOT _gen STREQUAL "0" OR NOT _run STREQUAL "0" OR NOT _check STREQUAL "0")
    list(APPEND _failed "${_form} (request generator ${_gen}, runner ${_run}, oracle check ${_check}; 0 is success)")
    continue()
  endif()
  # Something was judged, in every stratum the generator announced.
  file(READ "${_summary}" _json)
  string(JSON _strata GET "${_json}" coverage 0 desc strata)
  string(REPLACE "," ";" _strata "${_strata}")
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
    list(APPEND _failed "${_form} (the oracle judged no case)")
  endif()
  foreach(_stratum IN LISTS _strata)
    if(NOT _stratum IN_LIST _tags)
      list(APPEND _failed "${_form} (no case of stratum ${_stratum} in ${COUNT})")
    endif()
  endforeach()
endforeach()

if(_failed)
  list(JOIN _failed "\n  " _failed)
  message(FATAL_ERROR "the public interface failed the claims of ${KERNEL} ${FORMAT} in:\n  ${_failed}\n"
    "To rerun case INDEX of form F: ${PYTHON} oracle/kairn-oracle gen ${KERNEL} ${FORMAT} --seed ${SEED} "
    "--start INDEX --count 1 | ${RUNNER} --form F | ${PYTHON} oracle/kairn-oracle check")
endif()
list(LENGTH _forms _n)
message(STATUS "${KERNEL} ${FORMAT}: ${_n} forms of the public interface passed")
