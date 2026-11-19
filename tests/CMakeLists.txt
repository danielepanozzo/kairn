# Kairn's tests, registered with ctest when KAIRN_BUILD_TESTS is on:
#
#   ctest --test-dir build --output-on-failure
#
# - The entry points of docs/developer/architecture.md that run tests, each registered only if its
#   script exists when CMake runs (configure again after one is added). They need Python 3; without
#   it they are left out, and nothing else changes.
# - The consumer checks (consume/): a project that uses kairn::kairn through add_subdirectory, and
#   one that uses it through find_package after this build tree is installed into a prefix under
#   the build directory.

# Python 3 runs the generator's and the oracle's tests, from the repository root, as
# "python3 <script> <command>".
find_package(Python3 COMPONENTS Interpreter)
set(_present "")
set(_absent "")
foreach(_entry "gen/kairn-gen check" "gen/kairn-gen test" "oracle/kairn-oracle selftest")
  separate_arguments(_args UNIX_COMMAND "${_entry}")
  list(GET _args 0 _script)
  list(GET _args 1 _command)
  if(NOT EXISTS "${PROJECT_SOURCE_DIR}/${_script}")
    list(APPEND _absent "${_entry}")
    continue()
  endif()
  list(APPEND _present "${_entry}")
  if(Python3_Interpreter_FOUND)
    get_filename_component(_name "${_script}" NAME)
    add_test(NAME "${_name}.${_command}"
      COMMAND "${Python3_EXECUTABLE}" "${_script}" "${_command}"
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  endif()
endforeach()
list(JOIN _present ", " _present)
list(JOIN _absent ", " _absent)
if(NOT _present)
  set(_present "none")
endif()
if(Python3_Interpreter_FOUND)
  set(_line "Kairn tests: registered: ${_present}")
else()
  set(_line "Kairn tests: Python 3 not found, so not registered: ${_present}")
endif()
if(_absent)
  string(APPEND _line "; not present yet: ${_absent}")
endif()
message(STATUS "${_line}")

# The consumer checks build their project with ctest --build-and-test, with this build's generator
# and compiler, and run its program, which checks the version it is given against version.hpp.
set(_consume_dir "${CMAKE_CURRENT_BINARY_DIR}/consume")
set(_build_and_test --build-generator "${CMAKE_GENERATOR}" --build-project kairn_consume)
if(CMAKE_GENERATOR_PLATFORM)
  list(APPEND _build_and_test --build-generator-platform "${CMAKE_GENERATOR_PLATFORM}")
endif()
if(CMAKE_GENERATOR_TOOLSET)
  list(APPEND _build_and_test --build-generator-toolset "${CMAKE_GENERATOR_TOOLSET}")
endif()
if(CMAKE_MAKE_PROGRAM)
  list(APPEND _build_and_test --build-makeprogram "${CMAKE_MAKE_PROGRAM}")
endif()
set(_config "")
set(_build_type "")
get_property(_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(_multi_config)
  set(_config -C "$<CONFIG>")
elseif(CMAKE_BUILD_TYPE)
  set(_build_type "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()
set(_build_options --build-options "-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}" ${_build_type})
set(_run --test-command consume "${PROJECT_VERSION}")

add_test(NAME consume.add_subdirectory
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${CMAKE_CURRENT_SOURCE_DIR}/consume/add_subdirectory" "${_consume_dir}/add_subdirectory"
    ${_build_and_test} ${_build_options} "-DKAIRN_SOURCE_DIR=${PROJECT_SOURCE_DIR}" ${_run})

add_test(NAME consume.install
  COMMAND "${CMAKE_COMMAND}" "-DBUILD_DIR=${PROJECT_BINARY_DIR}" "-DPREFIX=${_consume_dir}/prefix"
    "-DCONFIG=$<CONFIG>" -P "${CMAKE_CURRENT_SOURCE_DIR}/consume/install.cmake")
set_tests_properties(consume.install PROPERTIES FIXTURES_SETUP kairn_installed)

add_test(NAME consume.find_package
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${CMAKE_CURRENT_SOURCE_DIR}/consume/find_package" "${_consume_dir}/find_package"
    ${_build_and_test} ${_build_options} "-DCMAKE_PREFIX_PATH=${_consume_dir}/prefix" ${_run})
set_tests_properties(consume.find_package PROPERTIES FIXTURES_REQUIRED kairn_installed)
