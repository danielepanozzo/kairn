// The consumer checks' program (tests/CMakeLists.txt). It compiles only if linking kairn::kairn
// is enough to find Kairn's headers and to compile as C++20, and it fails unless version.hpp
// states the version it is given on the command line, the one in CMakeLists.txt.
#include <kairn/version.hpp>

#include <cstdio>
#include <cstring>

#if (defined(_MSVC_LANG) ? _MSVC_LANG : __cplusplus) < 202002L
#error "kairn::kairn must make its users compile as C++20"
#endif

int main(int argc, char** argv) {
  if (argc != 2 || std::strcmp(argv[1], KAIRN_VERSION_STRING) != 0) {
    std::fprintf(stderr, "version.hpp says %s, expected %s\n", KAIRN_VERSION_STRING,
                 argc == 2 ? argv[1] : "a version argument");
    return 1;
  }
  std::printf("kairn %s\n", KAIRN_VERSION_STRING);
  return 0;
}
