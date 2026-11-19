// <cmath> and the standard headers that kairn/kairn.hpp includes, with the intrinsics header it
// includes on this target, and nothing of Kairn: the baseline of include.cpp
// (bench/compile_time.py).
#include <bit>
#include <cfenv>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <type_traits>

#if defined(_MSC_VER) && !defined(__clang__) && (defined(_M_X64) || defined(_M_IX86))
#include <immintrin.h>  // kairn/gen/prelude.hpp, for MSVC's FMA intrinsics
#elif defined(__x86_64__) || defined(__i386__)
#include <xmmintrin.h>  // kairn/environment.hpp, for _mm_getcsr
#endif
