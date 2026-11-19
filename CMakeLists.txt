# Kairn is header-only: the library is the INTERFACE target kairn::kairn, which adds include/ to
# the include path and requires C++20. Building it as a client never needs Python or Rocq
# (docs/developer/architecture.md).
#
#   cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure
#
# A client uses it through add_subdirectory or FetchContent, or through find_package(kairn) after
# cmake --install. On x86-64 the kernels need hardware FMA, which kairn::kairn does not enable:
# a client compiles for such a CPU, or also links kairn::fma (cmake/kairn_fma.cmake).
cmake_minimum_required(VERSION 3.21)

project(kairn
  VERSION 0.0.0
  DESCRIPTION "Floating-point expansions with interval and ball arithmetic"
  LANGUAGES CXX)

option(KAIRN_BUILD_TESTS "Register Kairn's tests with ctest" ${PROJECT_IS_TOP_LEVEL})

# Built on its own, Kairn is built for testing, and its tests mean most with optimization on: the
# contraction tests check what an optimizer may do to the kernels (tests/CMakeLists.txt).
get_property(_kairn_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(PROJECT_IS_TOP_LEVEL AND NOT _kairn_multi_config AND NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type (Kairn's default: Release)" FORCE)
endif()

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

# include/kairn/version.hpp is committed, so that a client that only adds include/ to its include
# path has it too. It must state the version above.
set(_kairn_version_header "${PROJECT_SOURCE_DIR}/include/kairn/version.hpp")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_kairn_version_header}")
file(READ "${_kairn_version_header}" _kairn_version_text)
foreach(_part MAJOR MINOR PATCH STRING)
  if(_part STREQUAL "STRING")
    set(_expected "\"${PROJECT_VERSION}\"")
  else()
    set(_expected "${PROJECT_VERSION_${_part}}")
  endif()
  string(REGEX MATCH "#define KAIRN_VERSION_${_part} ([^\r\n]*)" _match "${_kairn_version_text}")
  if(NOT _match OR NOT CMAKE_MATCH_1 STREQUAL _expected)
    message(FATAL_ERROR "include/kairn/version.hpp must define KAIRN_VERSION_${_part} as "
      "${_expected}, the version in CMakeLists.txt")
  endif()
endforeach()

add_library(kairn INTERFACE)
add_library(kairn::kairn ALIAS kairn)
target_include_directories(kairn INTERFACE
  "$<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>"
  "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")
target_compile_features(kairn INTERFACE cxx_std_20)

# kairn::fma: the option that gives the kernels hardware FMA, for targets that want Kairn to choose
# it (cmake/kairn_fma.cmake). kairn::kairn itself never changes the instruction set.
include("${PROJECT_SOURCE_DIR}/cmake/kairn_fma.cmake")
kairn_define_fma_target("${PROJECT_SOURCE_DIR}/include" GLOBAL)

# Installation: the headers, and a package configuration with a version file under
# share/cmake/kairn, where find_package(kairn) looks. Nothing in it depends on the architecture:
# the installed configuration chooses kairn::fma's option with the client's compiler.
set(_kairn_cmake_dir "${CMAKE_INSTALL_DATADIR}/cmake/kairn")

install(TARGETS kairn EXPORT kairnTargets)
install(DIRECTORY include/ DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}" PATTERN ".*" EXCLUDE)
install(EXPORT kairnTargets NAMESPACE kairn:: DESTINATION "${_kairn_cmake_dir}")

configure_package_config_file(cmake/kairnConfig.cmake.in
  "${PROJECT_BINARY_DIR}/kairnConfig.cmake"
  INSTALL_DESTINATION "${_kairn_cmake_dir}"
  PATH_VARS CMAKE_INSTALL_INCLUDEDIR)
# Before 1.0 a minor version may change the interface, so only the same MAJOR.MINOR is accepted.
write_basic_package_version_file("${PROJECT_BINARY_DIR}/kairnConfigVersion.cmake"
  COMPATIBILITY SameMinorVersion
  ARCH_INDEPENDENT)
install(FILES
  "${PROJECT_BINARY_DIR}/kairnConfig.cmake"
  "${PROJECT_BINARY_DIR}/kairnConfigVersion.cmake"
  cmake/kairn_fma.cmake
  DESTINATION "${_kairn_cmake_dir}")

if(KAIRN_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
