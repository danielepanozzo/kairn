# Every kernel of gen/claims.json is either computed by some public operation (runner --list) or
# listed as internal by the runner (runner --internal), and tests/api/CMakeLists.txt has the same
# two lists: a kernel added to the generator fails here until someone decides which it is.
#
#   cmake -DRUNNER=... "-DMAPPED=a;b" "-DINTERNAL=c;d" -P coverage.cmake
cmake_minimum_required(VERSION 3.21)

foreach(_what list internal)
  execute_process(COMMAND "${RUNNER}" --${_what} OUTPUT_VARIABLE _out RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "${RUNNER} --${_what} failed: ${_status}")
  endif()
  string(STRIP "${_out}" _out)
  string(REPLACE "\n" ";" _runner_${_what} "${_out}")
  list(SORT _runner_${_what})
endforeach()
set(_mapped ${MAPPED})
set(_internal ${INTERNAL})
list(SORT _mapped)
list(SORT _internal)
set(_problems "")
if(NOT _runner_list STREQUAL _mapped)
  list(APPEND _problems "the kernels of gen/claims.json not listed as internal: ${_mapped}\n"
    "the kernels the runner maps to a public operation: ${_runner_list}")
endif()
if(NOT _runner_internal STREQUAL _internal)
  list(APPEND _problems "internal in tests/api/CMakeLists.txt: ${_internal}\n"
    "internal in tests/api/runner.cpp: ${_runner_internal}")
endif()
if(_problems)
  string(JOIN "\n" _problems ${_problems})
  message(FATAL_ERROR "${_problems}")
endif()
list(LENGTH _mapped _n)
list(LENGTH _internal _m)
message(STATUS "${_n} kernels mapped to public operations, ${_m} internal")
