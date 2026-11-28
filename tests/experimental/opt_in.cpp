// experimental.opt_in.HEADER (tests/experimental/CMakeLists.txt, through ../api/compile_fail.cmake):
// an experimental header, EXPERIMENTAL and NOT VERIFIED, must not compile in a file that has not
// defined KAIRN_EXPERIMENTAL_UNVERIFIED, and must compile in the control, which defines it. The
// header is the case: 1 upward2.hpp, 2 upward2_arrays.hpp, 3 upward4.hpp, 4 upward4_arrays.hpp.
#if defined(KAIRN_TEST_CONTROL)
#define KAIRN_EXPERIMENTAL_UNVERIFIED
#endif

#if KAIRN_TEST_CASE == 1
#include <kairn/experimental/upward2.hpp>
#elif KAIRN_TEST_CASE == 2
#include <kairn/experimental/upward2_arrays.hpp>
#elif KAIRN_TEST_CASE == 3
#include <kairn/experimental/upward4.hpp>
#elif KAIRN_TEST_CASE == 4
#include <kairn/experimental/upward4_arrays.hpp>
#else
#error "opt_in.cpp: no such case"
#endif

int main() { return 0; }
