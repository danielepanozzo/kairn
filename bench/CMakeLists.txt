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

# The benchmark of Milestone 2 (bench/m2_data.hpp; bench/README.md, "Milestone 2"):
# kairn-bench-m2-LEVEL, and the same with the operations of Ball and Interval outlined and external
# (kairn-bench-m2-outlined-LEVEL, kairn-bench-m2-external-LEVEL). m2_fenv.cpp and
# m2_fenv_packed.cpp hold the props that change the rounding mode: they are compiled so that the
# compiler honors a change of mode (-frounding-math; /fp:strict with MSVC), and they do not include
# Kairn. The packed files are compiled for AVX2 on x86-64, as packed.cpp.
if(_opt_O2 STREQUAL "/O2")
  set(_rounding_math /fp:strict)
else()
  set(_rounding_math -frounding-math)
endif()
set_source_files_properties(m2_fenv.cpp PROPERTIES COMPILE_OPTIONS "${_rounding_math}")
set_source_files_properties(m2_fenv_packed.cpp PROPERTIES COMPILE_OPTIONS "${_rounding_math};${_packed_isa}")
set_source_files_properties(m2_packed.cpp PROPERTIES COMPILE_OPTIONS "${_packed_isa}")
# The second part: Packed and the containers (m2_soa.cpp, and m2_soa_scalar.cpp, the same packed loops
# in the scalar form of Packed) are compiled as packed code, their scalar loops with them; the
# enclosure interface (m2_enc.cpp) and the whole computations (m2_run.cpp) as scalar code.
set_source_files_properties(m2_soa.cpp m2_soa_scalar.cpp PROPERTIES COMPILE_OPTIONS "${_packed_isa}")
# The third part: the functions on arrays, the accumulator (m2_batch.cpp) and the ball vectors
# (m2_bv.cpp, m2_bvs.cpp) are compiled as packed code, as a client's unit that wants their fast order is.
set_source_files_properties(m2_batch.cpp m2_bv.cpp m2_bvs.cpp m2_accuracy.cpp PROPERTIES COMPILE_OPTIONS "${_packed_isa}")
string(REPLACE ";" " " _rounding_math_text "${_rounding_math}")
set(_m2_sources m2_main.cpp m2.cpp m2_fenv.cpp m2_packed.cpp m2_fenv_packed.cpp m2_soa.cpp m2_soa_scalar.cpp
    m2_enc.cpp m2_run.cpp m2_batch.cpp m2_bv.cpp m2_bvs.cpp)
# m2_bvs.cpp again, one operation of one size per unit (backend m2y), as a client's file holds a few:
# the units are written here into the build directory, each defining KB_BVS_ONE and including it.
foreach(_op IN ITEMS add addop sub scale half make)
  foreach(_k IN ITEMS 1 2)
    foreach(_n IN ITEMS 3 7 13 18 80)
      set(_unit "${CMAKE_CURRENT_BINARY_DIR}/m2y/m2_bvs_${_op}_${_k}_${_n}.cpp")
      file(WRITE "${_unit}.in" "// Written by bench/CMakeLists.txt: one unit of m2_bvs.cpp.\n#define KB_BVS_ONE 1\n"
           "#define KB_BVS_OP ${_op}\n#define KB_BVS_K ${_k}\n#define KB_BVS_N ${_n}\n"
           "#include \"${CMAKE_CURRENT_SOURCE_DIR}/m2_bvs.cpp\"\n")
      configure_file("${_unit}.in" "${_unit}" COPYONLY)
      set_source_files_properties("${_unit}" PROPERTIES COMPILE_OPTIONS "${_packed_isa}")
      list(APPEND _m2_sources "${_unit}")
    endforeach()
  endforeach()
endforeach()
# kairn-bench-m2-nocheck-LEVEL, only when KAIRN_BENCH_NOCHECK_INCLUDE names a directory: the same
# program compiled against the copy of the headers there, which bench/entry_check.py makes from
# include/ with the check of the environment of the batch entries compiled out (never committed):
# what that check costs is the ratio of a function's time in kairn-bench-m2-LEVEL to its time here.
set(KAIRN_BENCH_NOCHECK_INCLUDE "" CACHE PATH
    "A copy of include/ made by bench/entry_check.py: builds kairn-bench-m2-nocheck-LEVEL against it")
# kairn-bench-m2-before-LEVEL likewise against KAIRN_BENCH_BEFORE_INCLUDE, the headers of an earlier
# commit (bench/entry_check.py before DEST: by default 25ebe3d6, with the report of the check inline at
# every check): the same harness with the headers as they were. (Until 2026-11-23 a third copy,
# KAIRN_BENCH_COLD_INCLUDE, held the report out of line and cold as a candidate; the header now has
# that form.)
set(KAIRN_BENCH_BEFORE_INCLUDE "" CACHE PATH
    "The headers of an earlier commit, from bench/entry_check.py before: builds kairn-bench-m2-before-LEVEL against them")
set(_m2_codes INLINE OUTLINED EXTERNAL CHECKS)
if(KAIRN_BENCH_NOCHECK_INCLUDE)
  list(APPEND _m2_codes NOCHECK)
endif()
if(KAIRN_BENCH_BEFORE_INCLUDE)
  list(APPEND _m2_codes BEFORE)
endif()
# kairn-bench-m2-checks-LEVEL: the inline setting with KAIRN_CHECKS 1 in every translation unit, for
# what the checks cost (bench/README.md, "Milestone 2").
foreach(_code IN LISTS _m2_codes)
  string(TOLOWER "${_code}" _name)
  foreach(_level IN LISTS _levels)
    if(_code STREQUAL "INLINE")
      set(_target kairn-bench-m2-${_level})
    else()
      set(_target kairn-bench-m2-${_name}-${_level})
    endif()
    add_executable(${_target} ${_m2_sources})
    if(_code STREQUAL "EXTERNAL")
      target_sources(${_target} PRIVATE definitions.cpp)
    endif()
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_opt_${_level}} ${_no_contract})
    string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_${_level}} ${_no_contract} ${_fma}" _flags)
    if(_code STREQUAL "CHECKS")
      string(APPEND _flags " -DKAIRN_CHECKS=1")
      set(_setting INLINE)
      target_compile_definitions(${_target} PRIVATE KAIRN_CHECKS=1)
    elseif(_code STREQUAL "NOCHECK")
      string(APPEND _flags " (headers: a copy with the check of the environment of the batch entries compiled out)")
      set(_setting INLINE)
      target_include_directories(${_target} BEFORE PRIVATE "${KAIRN_BENCH_NOCHECK_INCLUDE}")
    elseif(_code STREQUAL "BEFORE")
      string(APPEND _flags " (headers: those of an earlier commit, from bench/entry_check.py before)")
      set(_setting INLINE)
      target_include_directories(${_target} BEFORE PRIVATE "${KAIRN_BENCH_BEFORE_INCLUDE}")
    else()
      set(_setting ${_code})
    endif()
    if(_setting STREQUAL "OUTLINED" OR _setting STREQUAL "EXTERNAL")
      string(APPEND _flags " -DKAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_setting}")
    endif()
    string(REGEX REPLACE " +" " " _flags "${_flags}")
    if(_packed_isa_text)
      string(APPEND _flags " (packed code also ${_packed_isa_text})")
    endif()
    target_compile_definitions(${_target} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\""
      "KAIRN_BENCH_FENV_FLAGS=\"${_flags} ${_rounding_math_text}\"" "KAIRN_BENCH_SETTING=\"${_name}\""
      KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_setting})
  endforeach()
endforeach()

# kairn-bench-m2-accuracy-LEVEL (bench/m2_accuracy.cpp): the errors of the sums and dot products
# against the condition number and the stated bounds, third part; nothing timed.
foreach(_level IN LISTS _levels)
  add_executable(kairn-bench-m2-accuracy-${_level} m2_accuracy.cpp)
  target_link_libraries(kairn-bench-m2-accuracy-${_level} PRIVATE kairn::kairn kairn::fma)
  target_compile_options(kairn-bench-m2-accuracy-${_level} PRIVATE ${_opt_${_level}} ${_no_contract})
  string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_${_level}} ${_no_contract} ${_fma} ${_packed_isa_text}" _flags)
  string(REGEX REPLACE " +" " " _flags "${_flags}")
  target_compile_definitions(kairn-bench-m2-accuracy-${_level} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\"")
endforeach()

# kairn-bench-m2-modes-LEVEL (bench/m2_modes.cpp): a loop of additions and one of products timed under
# each rounding mode, compiled as plain code; no Kairn header.
foreach(_level IN LISTS _levels)
  add_executable(kairn-bench-m2-modes-${_level} m2_modes.cpp)
  target_compile_options(kairn-bench-m2-modes-${_level} PRIVATE ${_opt_${_level}} ${_no_contract})
  target_compile_features(kairn-bench-m2-modes-${_level} PRIVATE cxx_std_20)
  string(STRIP "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${_config}} ${_opt_${_level}} ${_no_contract}" _flags)
  string(REGEX REPLACE " +" " " _flags "${_flags}")
  target_compile_definitions(kairn-bench-m2-modes-${_level} PRIVATE "KAIRN_BENCH_FLAGS=\"${_flags}\"")
endforeach()
