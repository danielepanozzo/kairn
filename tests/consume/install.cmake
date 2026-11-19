# cmake -DBUILD_DIR=... -DPREFIX=... [-DCONFIG=...] -P install.cmake
#
# Installs the build tree BUILD_DIR into PREFIX, after removing what an earlier run left there:
# the setup of the find_package consumer check (tests/CMakeLists.txt).
file(REMOVE_RECURSE "${PREFIX}")
set(_config "")
if(CONFIG)
  set(_config --config "${CONFIG}")
endif()
execute_process(
  COMMAND "${CMAKE_COMMAND}" --install "${BUILD_DIR}" --prefix "${PREFIX}" ${_config}
  COMMAND_ERROR_IS_FATAL ANY)
