# cmake -DBUILD_DIR=... -DPREFIX=... -DLICENSE=... -DLICENSE_DIR=... [-DCONFIG=...] -P install.cmake
#
# Installs the build tree BUILD_DIR into PREFIX, after removing what an earlier run left there:
# the setup of the find_package consumer check (tests/CMakeLists.txt). Then checks that the
# installation carries the license: PREFIX/LICENSE_DIR/LICENSE, the same as the file LICENSE.
file(REMOVE_RECURSE "${PREFIX}")
set(_config "")
if(CONFIG)
  set(_config --config "${CONFIG}")
endif()
execute_process(
  COMMAND "${CMAKE_COMMAND}" --install "${BUILD_DIR}" --prefix "${PREFIX}" ${_config}
  COMMAND_ERROR_IS_FATAL ANY)

set(_installed "${PREFIX}/${LICENSE_DIR}/LICENSE")
if(NOT EXISTS "${_installed}")
  message(FATAL_ERROR "the installation has no license: ${_installed} does not exist")
endif()
file(READ "${LICENSE}" _expected)
file(READ "${_installed}" _found)
if(NOT _found STREQUAL _expected)
  message(FATAL_ERROR "${_installed} differs from ${LICENSE}")
endif()
message(STATUS "the license is installed as ${LICENSE_DIR}/LICENSE")
