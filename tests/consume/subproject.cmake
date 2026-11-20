# The consumer check of Kairn as a subproject (tests/CMakeLists.txt, consume.add_subdirectory): the
# project add_subdirectory/, which adds Kairn with add_subdirectory and links kairn::kairn and
# kairn::fma, configured, built and run, and Kairn kept to itself there:
#
# 1. configured as a client would, with the build's generator, compiler and build type, it prints
#    no line of Kairn's (a STATUS notice, "-- Kairn..."), then builds, and its program runs, checks
#    the version it is given against version.hpp, and runs a kernel;
# 2. cmake --install of that build installs nothing: Kairn adds no install rule unless asked;
# 3. the notice about kairn::fma's option, forced to be needed (the results of its two compile
#    checks given on the command line, as if the compiler had no FMA by default), is not printed
#    at the default log level and is printed with --log-level=VERBOSE: the check of 1. would see
#    it, on every target, and not only where the compiler needs the option;
# 4. with -DKAIRN_INSTALL=ON, cmake --install installs Kairn's headers: the option is what decides.
#
#   cmake -DSOURCE=DIR -DWORK=DIR -DKAIRN_SOURCE_DIR=DIR -DVERSION=X.Y.Z -DCXX=... -DGENERATOR=...
#         [-DPLATFORM=...] [-DTOOLSET=...] [-DMAKE_PROGRAM=...] [-DBUILD_TYPE=...] [-DCONFIG=...]
#         -P subproject.cmake
cmake_minimum_required(VERSION 3.21)

foreach(_var SOURCE WORK KAIRN_SOURCE_DIR VERSION CXX GENERATOR)
  if(NOT DEFINED ${_var})
    message(FATAL_ERROR "subproject.cmake: ${_var} is not set")
  endif()
endforeach()
file(REMOVE_RECURSE "${WORK}")
file(MAKE_DIRECTORY "${WORK}")

set(_generator -G "${GENERATOR}")
if(PLATFORM)
  list(APPEND _generator -A "${PLATFORM}")
endif()
if(TOOLSET)
  list(APPEND _generator -T "${TOOLSET}")
endif()
if(MAKE_PROGRAM)
  list(APPEND _generator "-DCMAKE_MAKE_PROGRAM=${MAKE_PROGRAM}")
endif()
set(_options "-DCMAKE_CXX_COMPILER=${CXX}" "-DKAIRN_SOURCE_DIR=${KAIRN_SOURCE_DIR}")
if(BUILD_TYPE)
  list(APPEND _options "-DCMAKE_BUILD_TYPE=${BUILD_TYPE}")
endif()
set(_config "")
if(CONFIG)
  set(_config --config "${CONFIG}")
endif()

# Configures SOURCE into WORK/NAME with ARGN; the output (standard output and error) in OUT.
function(_kairn_configure name out)
  execute_process(COMMAND "${CMAKE_COMMAND}" -S "${SOURCE}" -B "${WORK}/${name}" ${_generator} ${_options} ${ARGN}
    OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "configuring ${SOURCE} into ${WORK}/${name} failed (${_status}):\n${_out}${_err}")
  endif()
  set(${out} "${_out}${_err}" PARENT_SCOPE)
endfunction()
# The lines of TEXT that are Kairn's: a message whose text starts with "Kairn", as every message of
# Kairn's configuration does (with "-- " before it for a STATUS line).
function(_kairn_lines text out)
  string(REGEX MATCHALL "(^|\n)(-- )?Kairn[^\n]*" _lines "${text}")
  set(${out} "${_lines}" PARENT_SCOPE)
endfunction()
# Installs WORK/NAME into WORK/NAME-prefix; the lines of its install_manifest.txt in OUT.
function(_kairn_install name out)
  execute_process(COMMAND "${CMAKE_COMMAND}" --install "${WORK}/${name}" --prefix "${WORK}/${name}-prefix" ${_config}
    OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
  if(NOT _status STREQUAL "0")
    message(FATAL_ERROR "cmake --install ${WORK}/${name} failed (${_status}):\n${_out}${_err}")
  endif()
  set(_manifest "")
  if(EXISTS "${WORK}/${name}/install_manifest.txt")
    file(STRINGS "${WORK}/${name}/install_manifest.txt" _manifest)
  endif()
  file(GLOB_RECURSE _files LIST_DIRECTORIES false "${WORK}/${name}-prefix/*")
  list(APPEND _manifest ${_files})
  list(REMOVE_DUPLICATES _manifest)
  set(${out} "${_manifest}" PARENT_SCOPE)
endfunction()

# 1. As a client would: no line of Kairn's, a build, and the program.
_kairn_configure(build _text)
_kairn_lines("${_text}" _lines)
if(_lines)
  message(FATAL_ERROR "added with add_subdirectory, Kairn printed when configured:${_lines}")
endif()
execute_process(COMMAND "${CMAKE_COMMAND}" --build "${WORK}/build" ${_config}
  OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "building ${WORK}/build failed (${_status}):\n${_out}${_err}")
endif()
# In the build directory, or in a directory of its configuration with a multi-configuration
# generator: the only file of that name.
file(GLOB_RECURSE _programs LIST_DIRECTORIES false "${WORK}/build/consume" "${WORK}/build/consume.exe")
list(REMOVE_DUPLICATES _programs)
list(LENGTH _programs _n)
if(NOT _n EQUAL 1)
  message(FATAL_ERROR "expected one program consume in ${WORK}/build, found ${_n}: ${_programs}")
endif()
execute_process(COMMAND ${_programs} "${VERSION}" OUTPUT_VARIABLE _out ERROR_VARIABLE _err RESULT_VARIABLE _status)
if(NOT _status STREQUAL "0")
  message(FATAL_ERROR "the program consume failed (${_status}):\n${_out}${_err}")
endif()
message(STATUS "configured without a line of Kairn's, built, and ran: ${_out}")

# 2. Nothing of Kairn's is installed.
_kairn_install(build _installed)
if(_installed)
  string(REPLACE ";" "\n  " _installed "${_installed}")
  message(FATAL_ERROR "added with add_subdirectory, Kairn installed files:\n  ${_installed}")
endif()
message(STATUS "cmake --install of the project installs nothing")

# 3. The notice of kairn::fma, made necessary: at the VERBOSE log level only.
set(_forced -DKAIRN_FMA_WITHOUT_OPTION=OFF -DKAIRN_FMA_WITH_OPTION=ON)
_kairn_configure(notice _text ${_forced})
_kairn_lines("${_text}" _lines)
if(_lines)
  message(FATAL_ERROR "with kairn::fma's option needed, Kairn printed at the default log level:${_lines}")
endif()
_kairn_configure(notice _text ${_forced} --log-level=VERBOSE)
_kairn_lines("${_text}" _lines)
if(NOT _lines MATCHES "Kairn: this compiler does not target hardware FMA")
  message(FATAL_ERROR "with kairn::fma's option needed, Kairn printed no notice at the VERBOSE log level, so "
    "the check of its absence proves nothing:\n${_text}")
endif()
string(STRIP "${_lines}" _lines)
message(STATUS "the notice, needed, only at the VERBOSE log level: ${_lines}")

# 4. Asked for, Kairn's files are installed.
_kairn_configure(install _text -DKAIRN_INSTALL=ON)
_kairn_install(install _installed)
if(NOT _installed MATCHES "include/kairn/kairn\\.hpp")
  message(FATAL_ERROR "with -DKAIRN_INSTALL=ON, cmake --install did not install include/kairn/kairn.hpp: ${_installed}")
endif()
list(LENGTH _installed _n)
message(STATUS "with -DKAIRN_INSTALL=ON, cmake --install installs Kairn's ${_n} files")
