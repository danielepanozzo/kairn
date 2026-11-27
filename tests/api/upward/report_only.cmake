# A test that reports and is not gated (the design page's table of configurations, "Tests and CI"):
# runs PROGRAM, prints what it printed and its exit status, and passes whatever they are, but when
# the program does not exist. For the builds whose results the design page records without
# requiring them: GCC and MSVC without the options of kairn/upward.hpp (with
# KAIRN_UPWARD_OPTIONS_UNCHECKED), and x86-64 programs under an emulator (Rosetta on macOS).
#
#   cmake -DPROGRAM=FILE [-DARGS=a|b] -P report_only.cmake
cmake_minimum_required(VERSION 3.21)

if(NOT DEFINED PROGRAM)
  message(FATAL_ERROR "report_only.cmake: PROGRAM is not set")
endif()
string(REPLACE "|" ";" _args "${ARGS}")
if(NOT EXISTS "${PROGRAM}")
  message(FATAL_ERROR "report_only.cmake: ${PROGRAM} does not exist")
endif()
execute_process(COMMAND "${PROGRAM}" ${_args}
  OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
message("${_out}${_err}")
message(STATUS "reported, not gated: the program exited with status ${_status}")
