# The benchmark harness (bench/README.md), added when KAIRN_BUILD_BENCHMARKS is ON. Nothing here is
# part of the library, and nothing here is built or tested by default.
#
# One executable per optimization level: kairn-bench-O2 and kairn-bench-O3 with GCC-style
# compilers, kairn-bench-O2 (/O2) with MSVC. Every file links kairn::fma, which gives the scalar
# kernels hardware FMA the way it does for a client; packed.cpp is compiled for AVX2 as well on
# x86-64, because kairn/gen/avx2.hpp needs it. Every file is compiled without contraction
# (-ffp-contract=off, or /fp:precise, which does not contract): the measurement props with a
# plain multiplication need it to compute the values of the generated kernels, and the generated
# kernels have no plain multiplication for it to change.

if(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC" OR
   (MSVC AND NOT CMAKE_CXX_COMPILER_FRONTEND_VARIANT))
  set(_levels O2)
  set(_opt_O2 /O2)
  set(_no_contract /fp:precise)
  set(_packed_isa "")
else()
  set(_levels O2 O3)
  set(_opt_O2 -O2)
  set(_opt_O3 -O3)
  set(_no_contract -ffp-contract=off)
  if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64|i[3-6]86)$")
    set(_packed_isa -mavx2 -mfma)
  else()
    set(_packed_isa "")
  endif()
endif()
set_source_files_properties(packed.cpp PROPERTIES COMPILE_OPTIONS "${_packed_isa}")

# MPFR and GMP, only if they are already installed (Homebrew: -DCMAKE_PREFIX_PATH=/opt/homebrew).
find_path(KAIRN_BENCH_MPFR_INCLUDE_DIR mpfr.h HINTS "$ENV{HOMEBREW_PREFIX}/include")
find_path(KAIRN_BENCH_GMP_INCLUDE_DIR gmp.h HINTS "$ENV{HOMEBREW_PREFIX}/include")
find_library(KAIRN_BENCH_MPFR_LIBRARY mpfr HINTS "$ENV{HOMEBREW_PREFIX}/lib")
find_library(KAIRN_BENCH_GMP_LIBRARY gmp HINTS "$ENV{HOMEBREW_PREFIX}/lib")
if(KAIRN_BENCH_MPFR_INCLUDE_DIR AND KAIRN_BENCH_GMP_INCLUDE_DIR AND KAIRN_BENCH_MPFR_LIBRARY AND
   KAIRN_BENCH_GMP_LIBRARY)
  set(_mpfr ON)
  message(STATUS "Kairn benchmarks: with MPFR (${KAIRN_BENCH_MPFR_LIBRARY})")
else()
  set(_mpfr OFF)
  message(STATUS "Kairn benchmarks: without MPFR (mpfr.h, gmp.h or the libraries not found)")
endif()

# The flags as the compiler sees them, recorded in the measurements.
get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
if(NOT _fma)
  set(_fma "")
endif()
if(CMAKE_BUILD_TYPE)
  string(TOUPPER "${CMAKE_BUILD_TYPE}" _config)
else()
  set(_config RELEASE)
endif()
string(REPLACE ";" " " _packed_isa_text "${_packed_isa}")

foreach(_level IN LISTS _levels)
  set(_target kairn-bench-${_level})
  add_executable(${_target} main.cpp scalar.cpp packed.cpp api.cpp mpfr.cpp)
  target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
  target_compile_options(${_target} PRIVATE ${_opt_${_level}} ${_no_contract})
  string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_${_level}} ${_no_contract} ${_fma}" _flags)
  string(REGEX REPLACE " +" " " _flags "${_flags}")
  if(_packed_isa_text)
    string(APPEND _flags " (packed code also ${_packed_isa_text})")
  endif()
  target_compile_definitions(${_target} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\"")
  if(_mpfr)
    target_compile_definitions(${_target} PRIVATE KAIRN_BENCH_MPFR)
    target_include_directories(${_target} PRIVATE "${KAIRN_BENCH_MPFR_INCLUDE_DIR}" "${KAIRN_BENCH_GMP_INCLUDE_DIR}")
    target_link_libraries(${_target} PRIVATE "${KAIRN_BENCH_MPFR_LIBRARY}" "${KAIRN_BENCH_GMP_LIBRARY}")
  endif()
endforeach()

# The same harness with the operations of Ball outlined and external (KAIRN_ENCLOSURE_CODE,
# include/kairn/config.hpp), which must be the same in every translation unit of a program:
# kairn-bench-outlined-LEVEL and kairn-bench-external-LEVEL, the second with definitions.cpp, the
# translation unit that defines the operations. bench/README.md, "The settings of
# KAIRN_ENCLOSURE_CODE", says how they are compared.
foreach(_code OUTLINED EXTERNAL)
  string(TOLOWER "${_code}" _name)
  foreach(_level IN LISTS _levels)
    set(_target kairn-bench-${_name}-${_level})
    add_executable(${_target} main.cpp scalar.cpp packed.cpp api.cpp mpfr.cpp)
    if(_code STREQUAL "EXTERNAL")
      target_sources(${_target} PRIVATE definitions.cpp)
    endif()
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_opt_${_level}} ${_no_contract})
    string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_${_level}} ${_no_contract} ${_fma} -DKAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_code}" _flags)
    string(REGEX REPLACE " +" " " _flags "${_flags}")
    target_compile_definitions(${_target} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\""
      KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_code})
    if(_mpfr)
      target_compile_definitions(${_target} PRIVATE KAIRN_BENCH_MPFR)
      target_include_directories(${_target} PRIVATE "${KAIRN_BENCH_MPFR_INCLUDE_DIR}" "${KAIRN_BENCH_GMP_INCLUDE_DIR}")
      target_link_libraries(${_target} PRIVATE "${KAIRN_BENCH_MPFR_LIBRARY}" "${KAIRN_BENCH_GMP_LIBRARY}")
    endif()
  endforeach()
endforeach()

# The cost of the checks of KAIRN_CHECKS and of MSVC's stack cookie (costs.cpp): one program per
# value of KAIRN_CHECKS, which must be the same in every translation unit of a program,
# kairn-bench-costs-LEVEL (0) and kairn-bench-costs-checks-LEVEL (1), at the levels above and
# without optimization (-O0, /Od), as a debug build has it.
if(_opt_O2 STREQUAL "/O2")
  set(_opt_O0 /Od /Ob0)   # /Ob0 too: the Release flags have /Ob2, which /Od alone leaves on
else()
  set(_opt_O0 -O0)
endif()
foreach(_level IN ITEMS O0 ${_levels})
  foreach(_checks IN ITEMS 0 1)
    if(_checks)
      set(_target kairn-bench-costs-checks-${_level})
    else()
      set(_target kairn-bench-costs-${_level})
    endif()
    add_executable(${_target} costs.cpp)
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_opt_${_level}} ${_no_contract})
    string(REPLACE ";" " " _opt_text "${_opt_${_level}}")
    string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_text} ${_no_contract} ${_fma} -DKAIRN_CHECKS=${_checks}" _flags)
    string(REGEX REPLACE " +" " " _flags "${_flags}")
    target_compile_definitions(${_target} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\"" KAIRN_CHECKS=${_checks})
  endforeach()
endforeach()
