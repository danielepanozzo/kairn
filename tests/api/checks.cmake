# One group of the cases of tests/api/checks.cpp, a program built with KAIRN_CHECKS 1:
#
#   cmake -DPROGRAM=... -DGROUP=default|rounding|flush|operands [-DEXPECT_FLUSH=ON] -P checks.cmake
#
# - default: `PROGRAM default` must exit 0: in the default environment every operation runs, as
#   does every operand the checks must let through.
# - rounding: for each directed rounding mode and each operation the program lists (the
#   constructors that check their operands among them), `PROGRAM MODE OPERATION` must stop the
#   program in the operation, with Kairn's message that the rounding mode is not to nearest, and
#   not with a message about an operand; before that, the program says that environment_ok() was
#   true in the default environment and false under the mode.
# - flush: the same for the states of flush to zero the program can set on this target (FTZ and
#   DAZ of MXCSR on x86-64, FZ of FPCR on AArch64). With EXPECT_FLUSH, a program that lists none
#   fails the test, so that a target where they should be tested cannot pass without them.
# - operands: each operand case the program lists must stop it with the message it gives.
#
# "Stop" means what a program built in debug mode sees: an exit status other than 0, after the
# line in which the program says it is calling the operation, with Kairn's message on the standard
# error and no line FAILED, which the program writes when an operation it called returned.
cmake_minimum_required(VERSION 3.21)

foreach(_var PROGRAM GROUP)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "checks.cmake: ${_var} is not set")
  endif()
endforeach()

# The lines the program prints for a listing option.
function(_kairn_list option out)
  execute_process(COMMAND "${PROGRAM}" ${option} OUTPUT_VARIABLE _text RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "${PROGRAM} ${option} failed: ${_status}")
  endif()
  string(STRIP "${_text}" _text)
  string(REPLACE "\r" "" _text "${_text}")
  string(REPLACE "\n" ";" _text "${_text}")
  set(${out} "${_text}" PARENT_SCOPE)
endfunction()

set(_failed "")
set(_n 0)
# Runs the program with ARGN; it must stop in WHAT, with MESSAGE (a regular expression) after
# "kairn: " on the standard error, and with every line of SAYS on the standard output.
function(_kairn_expect_stop what message says)
  execute_process(COMMAND "${PROGRAM}" ${ARGN} OUTPUT_VARIABLE _out ERROR_VARIABLE _err
    RESULT_VARIABLE _status TIMEOUT 60)
  set(_why "")
  if(_status STREQUAL "0")
    list(APPEND _why "it exited with status 0")
  endif()
  if(_out MATCHES "FAILED")
    string(REGEX MATCH "FAILED[^\n]*" _line "${_out}")
    list(APPEND _why "${_line}")
  endif()
  foreach(_say IN LISTS says)
    string(FIND "${_out}" "${_say}" _at)
    if(_at EQUAL -1)
      list(APPEND _why "it did not say '${_say}'")
    endif()
  endforeach()
  if(NOT _err MATCHES "kairn: ${message}")
    list(APPEND _why "no message 'kairn: ${message}' on the standard error")
  endif()
  string(STRIP "${_err}" _err_text)
  string(REPLACE "\n" " / " _err_text "${_err_text}")
  if(_why)
    # Joined with " / ": a semicolon would split the case in two in the list of failures.
    list(JOIN _why " / " _why)
    message(STATUS "FAILED ${what}: ${_why} (status ${_status}; standard error: ${_err_text})")
    set(_failed ${_failed} "${what}: ${_why}" PARENT_SCOPE)
  else()
    message(STATUS "ok ${what}: stopped (status ${_status}) with: ${_err_text}")
  endif()
endfunction()

if(GROUP STREQUAL "default")
  execute_process(COMMAND "${PROGRAM}" default OUTPUT_VARIABLE _out ERROR_VARIABLE _err
    RESULT_VARIABLE _status TIMEOUT 60)
  message(STATUS "${_out}${_err}")
  if(NOT _status STREQUAL "0" OR _out MATCHES "FAILED")
    message(FATAL_ERROR "${PROGRAM} default must exit 0 in the default environment (status ${_status})")
  endif()
  return()
endif()

if(GROUP STREQUAL "rounding" OR GROUP STREQUAL "flush")
  _kairn_list(--states _states)
  _kairn_list(--operations _operations)
  set(_rounding upward downward toward-zero)
  if(GROUP STREQUAL "rounding")
    foreach(_state IN LISTS _rounding)
      if(NOT _state IN_LIST _states)
        message(FATAL_ERROR "${PROGRAM} cannot set the rounding mode ${_state}")
      endif()
    endforeach()
    set(_states ${_rounding})
  else()
    list(REMOVE_ITEM _states ${_rounding})
    if(NOT _states)
      if(EXPECT_FLUSH)
        message(FATAL_ERROR "${PROGRAM} can set no state of flush to zero on a target that has them")
      endif()
      message(STATUS "no state of flush to zero is written for this target: nothing to test")
      return()
    endif()
  endif()
  foreach(_state IN LISTS _states)
    if(_state MATCHES "^(upward|downward|toward-zero)$")
      set(_message "the floating-point environment: the rounding mode is not to nearest")
    elseif(_state MATCHES "^(ftz|fz)$")
      set(_message "the floating-point environment: [^\n]*flushed to zero")
    elseif(_state STREQUAL "daz")
      set(_message "the floating-point environment: subnormal operands are read as zero")
    else()
      message(FATAL_ERROR "checks.cmake: no message is known for the state ${_state}")
    endif()
    foreach(_op IN LISTS _operations)
      math(EXPR _n "${_n} + 1")
      _kairn_expect_stop("${_op} under ${_state}" "${_message}"
        "ok: environment_ok() is true in the default environment;ok: environment_ok() is false under ${_state};calling ${_op} under ${_state}"
        "${_state}" "${_op}")
    endforeach()
  endforeach()
elseif(GROUP STREQUAL "operands")
  _kairn_list(--operand-cases _cases)
  foreach(_line IN LISTS _cases)
    string(REPLACE "\t" ";" _pair "${_line}")
    list(GET _pair 0 _case)
    list(GET _pair 1 _message)
    math(EXPR _n "${_n} + 1")
    _kairn_expect_stop("${_case}" "${_message}" "calling ${_case}" operand "${_case}")
  endforeach()
else()
  message(FATAL_ERROR "checks.cmake: unknown GROUP ${GROUP}")
endif()

if(_n EQUAL 0)
  message(FATAL_ERROR "checks.cmake: no case was run")
endif()
if(_failed)
  list(LENGTH _failed _n_failed)
  list(JOIN _failed "\n  " _failed)
  message(FATAL_ERROR "${_n_failed} of ${_n} cases of ${GROUP} did not stop as they must:\n  ${_failed}")
endif()
message(STATUS "${GROUP}: all ${_n} cases stopped as they must")
