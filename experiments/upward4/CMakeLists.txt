# The checks of the experimental four-limb interval rounded upward (experiments/upward4/README.md):
# EXPERIMENTAL, NOT VERIFIED, not part of the library and not part of Kairn's build. A project of
# its own:
#
#   cmake -S experiments/upward4 -B build-x4 -DCMAKE_BUILD_TYPE=Release [-DCMAKE_CXX_COMPILER=g++]
#   cmake --build build-x4
#   build-x4/x4-check-native-O2 2000000
#
# Requires the rounding mode upward set by kairn::upward::Scope and the options of
# docs/concepts/upward.md (GCC and Clang -frounding-math): every program here is compiled with
# -frounding-math. Programs, at -O2 and -O3: x4-check-native-LEVEL (the form of the target: NEON on
# AArch64; SSE with AVX2 and FMA on x86-64), x4-check-numbers-LEVEL (the fallback of plain doubles,
# forced), x4-check-checked-LEVEL (the form of the target with KAIRN_CHECKS 1), and on x86-64
# x4-check-sse-LEVEL (SSE and FMA without AVX2). Every one counts the calls of the cold paths
# (KAIRN_UPWARD4_COUNT 1).
cmake_minimum_required(VERSION 3.20)
project(kairn_upward4_experiment CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(_root "${CMAKE_CURRENT_SOURCE_DIR}/../..")
find_package(Threads REQUIRED)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
  set(_x86 ON)
else()
  set(_x86 OFF)
endif()

set(_variants native numbers checked)
if(_x86)
  list(APPEND _variants sse)
endif()

foreach(_level O2 O3)
  foreach(_variant IN LISTS _variants)
    set(_target x4-check-${_variant}-${_level})
    add_executable(${_target} tests/check.cpp)
    target_include_directories(${_target} PRIVATE "${_root}/include" "${_root}/experiments/upward2/include"
                               "${CMAKE_CURRENT_SOURCE_DIR}/include")
    target_link_libraries(${_target} PRIVATE Threads::Threads)
    target_compile_definitions(${_target} PRIVATE KAIRN_UPWARD4_COUNT=1)
    set(_flags -${_level} -frounding-math -Wall -Wextra)
    if(_x86)
      if(_variant STREQUAL "sse")
        list(APPEND _flags -mfma)
      else()
        list(APPEND _flags -mavx2 -mfma)
      endif()
    endif()
    if(_variant STREQUAL "numbers")
      target_compile_definitions(${_target} PRIVATE KAIRN_UPWARD2_FORM=KAIRN_UPWARD2_FORM_NUMBERS)
    endif()
    if(_variant STREQUAL "checked")
      target_compile_definitions(${_target} PRIVATE KAIRN_CHECKS=1)
    endif()
    target_compile_options(${_target} PRIVATE ${_flags})
    string(REPLACE ";" " " _text "${_flags}")
    target_compile_definitions(${_target} PRIVATE "X4_FLAGS=\"${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION} ${_text} (${_variant})\"")
  endforeach()
endforeach()
