# A negative link test of KAIRN_ENCLOSURE_CODE (include/kairn/config.hpp): link_main.cpp compiled
# with the options MAIN, definitions.cpp with the options DEFINITIONS (or left out when it is
# NONE), linked together, must not link, with a message that matches EXPECT. The control, both
# compiled with MAIN, must link and run, and print "ok".
#
#   cmake -DCXX=... -DSTYLE=gnu|msvc -DINCLUDE=DIR -DSOURCE_DIR=DIR -DWORK=DIR "-DCOMMON=a|b"
#         "-DMAIN=a|b" "-DDEFINITIONS=a|b|NONE" "-DEXPECT=regex" [-DSYSROOT=...] -P link_fail.cmake
#
# The options separate with |, which survives being passed through add_test.
cmake_minimum_required(VERSION 3.21)

foreach(_var CXX STYLE INCLUDE SOURCE_DIR WORK MAIN DEFINITIONS EXPECT)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "link_fail.cmake: ${_var} is not set")
  endif()
endforeach()
foreach(_var COMMON MAIN DEFINITIONS)
  string(REPLACE "|" ";" ${_var} "${${_var}}")
endforeach()
file(REMOVE_RECURSE "${WORK}")
file(MAKE_DIRECTORY "${WORK}")

if(STYLE STREQUAL "msvc")
  set(_obj obj)
  set(_exe ".exe")
else()
  set(_obj o)
  set(_exe "")
endif()

# Compiles SOURCE with OPTIONS into WORK/NAME.obj; fails the test if it does not compile.
function(_kairn_compile name source options)
  if(STYLE STREQUAL "msvc")
    set(_cmd "${CXX}" /nologo /std:c++20 /EHsc /c "/I${INCLUDE}" ${COMMON} ${options} "${source}"
      "/Fo${WORK}/${name}.${_obj}")
  else()
    set(_cmd "${CXX}" -std=c++20 -c -I "${INCLUDE}" ${COMMON} ${options} "${source}" -o "${WORK}/${name}.${_obj}")
    if(SYSROOT)
      list(APPEND _cmd -isysroot "${SYSROOT}")
    endif()
  endif()
  execute_process(COMMAND ${_cmd} OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "${name} does not compile, so the test proves nothing:\n${_out}${_err}")
  endif()
endfunction()

# Links the objects NAMES into WORK/EXE; the status and the output in the caller's variables.
function(_kairn_link exe status output)
  set(_objects "")
  foreach(_name IN LISTS ARGN)
    list(APPEND _objects "${WORK}/${_name}.${_obj}")
  endforeach()
  if(STYLE STREQUAL "msvc")
    set(_cmd "${CXX}" /nologo ${_objects} "/Fe${WORK}/${exe}${_exe}")
  else()
    set(_cmd "${CXX}" ${COMMON} ${_objects} -o "${WORK}/${exe}${_exe}")
    if(SYSROOT)
      list(APPEND _cmd -isysroot "${SYSROOT}")
    endif()
  endif()
  execute_process(COMMAND ${_cmd} OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status
    WORKING_DIRECTORY "${WORK}")
  set(${status} "${_status}" PARENT_SCOPE)
  set(${output} "${_out}${_err}" PARENT_SCOPE)
endfunction()

# The control: both translation units with MAIN.
_kairn_compile(main "${SOURCE_DIR}/link_main.cpp" "${MAIN}")
_kairn_compile(control-definitions "${SOURCE_DIR}/definitions.cpp" "${MAIN}")
_kairn_link(control _status _output main control-definitions)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "the control does not link, so the test proves nothing:\n${_output}")
endif()
execute_process(COMMAND "${WORK}/control${_exe}" OUTPUT_VARIABLE _out RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0" OR NOT _out MATCHES "^ok")
  message(FATAL_ERROR "the control links but does not compute what it must (${_status}): ${_out}")
endif()

# The test: the definitions with DEFINITIONS, or none.
set(_objects main)
if(NOT DEFINITIONS STREQUAL "NONE")
  _kairn_compile(definitions "${SOURCE_DIR}/definitions.cpp" "${DEFINITIONS}")
  list(APPEND _objects definitions)
endif()
_kairn_link(test _status _output ${_objects})
if(_status STREQUAL "0")
  message(FATAL_ERROR "linked, but must not (main: ${MAIN}; definitions: ${DEFINITIONS})")
endif()
if(NOT "${_output}" MATCHES "${EXPECT}")
  message(FATAL_ERROR "did not link, but without the expected message (${EXPECT}):\n${_output}")
endif()
string(REGEX MATCH "[^\n]*(${EXPECT})[^\n]*" _line "${_output}")
message(STATUS "the control links and runs; the test does not link, as expected: ${_line}")
