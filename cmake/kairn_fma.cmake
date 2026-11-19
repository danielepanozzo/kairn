# kairn::fma, the compile option that gives Kairn's kernels hardware FMA with the C++ compiler of
# the project that includes this file. Included by Kairn's CMakeLists.txt and by the installed
# package configuration, so that the choice is made with the client's compiler either way.
#
# Every kernel assumes that fma_rn is one rounding done by the hardware, and on x86 the generated
# headers refuse to compile without it (include/kairn/gen/prelude.hpp). kairn::kairn does not add
# an option for that itself: which CPUs a program runs on is the program's decision, and an option
# carried by a usage requirement would apply to every file of every target that links Kairn. A
# target that wants Kairn to choose links kairn::fma as well. Its option is
#
#   nothing       if the project's flags already give the kernels FMA (AArch64, -march=x86-64-v3,
#                 /arch:AVX2 in CMAKE_CXX_FLAGS, ...);
#   /arch:AVX2    otherwise, for MSVC and clang-cl;
#   -mfma         otherwise, for GCC- and Clang-style compilers;
#
# each tried by compiling the prelude as C++20 with CMAKE_CXX_FLAGS, and nothing, with a warning,
# if neither compiles. The results are cached (KAIRN_FMA_WITHOUT_OPTION, KAIRN_FMA_WITH_OPTION).
include_guard(GLOBAL)
include(CheckCXXSourceCompiles)
include(CMakePushCheckState)

# kairn_define_fma_target(INCLUDE_DIR [GLOBAL] [QUIET]): defines kairn::fma, whose prelude is
# INCLUDE_DIR/kairn/gen/prelude.hpp.
function(kairn_define_fma_target include_dir)
  cmake_parse_arguments(PARSE_ARGV 1 _arg "GLOBAL;QUIET" "" "")
  if(TARGET kairn::fma)
    return()
  endif()
  set(_source "#include <kairn/gen/prelude.hpp>\nint main() { return 0; }\n")
  # As C++20, as for every user of kairn::kairn (MSVC's default, C++14, rejects the prelude).
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  cmake_push_check_state(RESET)
  set(CMAKE_REQUIRED_INCLUDES "${include_dir}")
  set(CMAKE_REQUIRED_QUIET ON)
  check_cxx_source_compiles("${_source}" KAIRN_FMA_WITHOUT_OPTION)
  set(_option "")
  if(NOT KAIRN_FMA_WITHOUT_OPTION)
    if(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC" OR
       (MSVC AND NOT CMAKE_CXX_COMPILER_FRONTEND_VARIANT))
      set(_candidate "/arch:AVX2")
    else()
      set(_candidate "-mfma")
    endif()
    set(CMAKE_REQUIRED_FLAGS "${_candidate}")
    check_cxx_source_compiles("${_source}" KAIRN_FMA_WITH_OPTION)
    if(KAIRN_FMA_WITH_OPTION)
      set(_option "${_candidate}")
      if(NOT _arg_QUIET)
        message(STATUS "Kairn: this compiler does not target hardware FMA by default; targets that "
          "use the kernels must enable it, for example by linking kairn::fma (adds ${_option})")
      endif()
    else()
      message(WARNING "Kairn: neither CMAKE_CXX_FLAGS nor ${_candidate} lets "
        "kairn/gen/prelude.hpp compile with this compiler, so kairn::fma adds nothing and the "
        "kernels will not compile; their #error says what is missing")
    endif()
  endif()
  cmake_pop_check_state()
  if(_arg_GLOBAL)
    add_library(kairn::fma INTERFACE IMPORTED GLOBAL)
  else()
    add_library(kairn::fma INTERFACE IMPORTED)
  endif()
  if(_option)
    set_target_properties(kairn::fma PROPERTIES INTERFACE_COMPILE_OPTIONS "${_option}")
  endif()
endfunction()
