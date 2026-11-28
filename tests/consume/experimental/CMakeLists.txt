# The consumer project of the experimental headers (EXPERIMENTAL, NOT VERIFIED, opt-in;
# tests/experimental/CMakeLists.txt, experimental.consume.*): Kairn added with add_subdirectory
# when KAIRN_SOURCE_DIR is given, found with find_package otherwise, and a program that includes
# every experimental header through the targets that docs/concepts/experimental.md names, compiled
# with -Wall -Wextra -Wpedantic -Werror as a client may compile (GCC and Clang only, as the headers).
cmake_minimum_required(VERSION 3.18...3.21)
project(kairn_consume CXX)
if(KAIRN_SOURCE_DIR)
  add_subdirectory("${KAIRN_SOURCE_DIR}" kairn)
else()
  find_package(kairn REQUIRED)
endif()
add_executable(consume_experimental ../consume_experimental.cpp)
target_link_libraries(consume_experimental PRIVATE kairn::upward kairn::fma)
target_compile_options(consume_experimental PRIVATE -Wall -Wextra -Wpedantic -Werror)
