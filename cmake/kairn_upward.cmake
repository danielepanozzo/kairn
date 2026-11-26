# kairn::upward, the compile option of <kairn/upward.hpp>, the round-up interval, with the C++
# compiler of the project that includes this file. Included by Kairn's CMakeLists.txt and by the
# installed package configuration, so that the choice is made with the client's compiler either
# way, as for kairn::fma (kairn_fma.cmake).
#
# Requires the rounding mode upward set by kairn::upward::Scope and the options of
# docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): this target adds the
# option to the files of the targets that link it, and links kairn::kairn. It adds nothing else:
# on x86 the kernels need hardware FMA as well, which a target gets from kairn::fma or its own
# flags. kairn::kairn itself never gains the option: the default types assume rounding to nearest
# and need none. The option is
#
#   /fp:strict              for MSVC;
#   /clang:-frounding-math  for clang-cl;
#   -frounding-math         for GCC- and Clang-style compilers.
include_guard(GLOBAL)

# kairn_define_upward_target([GLOBAL]): defines kairn::upward. Prints nothing.
function(kairn_define_upward_target)
  cmake_parse_arguments(PARSE_ARGV 0 _arg "GLOBAL" "" "")
  if(TARGET kairn::upward)
    return()
  endif()
  if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    set(_option "/fp:strict")
  elseif(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC")
    set(_option "/clang:-frounding-math")
  else()
    set(_option "-frounding-math")
  endif()
  if(_arg_GLOBAL)
    add_library(kairn::upward INTERFACE IMPORTED GLOBAL)
  else()
    add_library(kairn::upward INTERFACE IMPORTED)
  endif()
  set_target_properties(kairn::upward PROPERTIES
    INTERFACE_LINK_LIBRARIES kairn::kairn
    INTERFACE_COMPILE_OPTIONS "${_option}")
endfunction()
