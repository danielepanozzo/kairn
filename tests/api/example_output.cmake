# Runs one of the documentation's examples and compares what it prints with the file the page
# shows (docs/examples/cpp/NAME.txt), line ends aside. Fails if the program exits with a status
# other than 0, which it does when one of its own checks fails, or if it prints anything else.
#
#   cmake -DPROGRAM=path -DEXPECTED=path -P example_output.cmake
execute_process(COMMAND "${PROGRAM}" OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _rc)
if(NOT _rc EQUAL 0)
  message(FATAL_ERROR "${PROGRAM} exited with ${_rc}:\n${_out}${_err}")
endif()
file(READ "${EXPECTED}" _expected)
string(REPLACE "\r\n" "\n" _expected "${_expected}")
string(REPLACE "\r\n" "\n" _out "${_out}")
if(NOT _out STREQUAL _expected)
  message(FATAL_ERROR "what the program printed differs from ${EXPECTED}, which the documentation shows:\n"
    "--- printed\n${_out}--- expected\n${_expected}")
endif()
message(STATUS "the output is the one ${EXPECTED} shows")
