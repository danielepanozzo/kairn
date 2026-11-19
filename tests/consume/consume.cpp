// The consumer checks' program (tests/CMakeLists.txt). It compiles only if linking kairn::kairn
// is enough to find Kairn's headers and to compile as C++20, and kairn::fma enough to compile the
// kernels; it fails unless version.hpp states the version it is given on the command line, the one
// in CMakeLists.txt, and unless a kernel with a fused operation computes what it must.
#include <kairn/gen/scalar.hpp>
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
  // (1 + 2^-52)(1 - 2^-52) = 1 - 2^-104: rounded to 1, with the error term exact.
  volatile double a = 1 + 0x1p-52, b = 1 - 0x1p-52;
  double p = 0, e = 0;
  kairn::gen::two_prod(a, b, p, e);
  if (p != 1 || e != -0x1p-104) {
    std::fprintf(stderr, "two_prod gave %a %a, expected 0x1p+0 -0x1p-104\n", p, e);
    return 1;
  }
  std::printf("kairn %s\n", KAIRN_VERSION_STRING);
  return 0;
}
