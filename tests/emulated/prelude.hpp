// What the generated kernels for the emulated limb type (gen/kernels.hpp) need besides the type
// itself, in place of include/kairn/gen/prelude.hpp, which is the double and float version: the
// macros the printer writes and the result of a fix-up that is a function of its own. Nothing here
// is about the machine's floating point: the emulated type computes with integers, so there is no
// FMA to require, no contraction to prevent and no inlining to force (the kernels are ordinary
// inline functions, which keeps the compilation of 223 of them short). What the shipped prelude
// keeps out of line stays out of line here too: a fix-up that is a function of its own and the end
// of a ball vector are never inlined, as in include/kairn/gen/prelude.hpp.
#pragma once

#include <cstddef>
#include <limits>

#include "number.hpp"

#define KAIRN_GEN_FORCEINLINE inline
#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_GEN_NOINLINE inline __declspec(noinline)
#else
#define KAIRN_GEN_NOINLINE inline __attribute__((noinline))
#endif
#define KAIRN_GEN_PUSH_WARNINGS
#define KAIRN_GEN_POP_WARNINGS

// The form of the fix-ups of the full kernels and the constructors (milestone1.md, "Emission"):
// inline unless the build says otherwise; the tests build both (tests/CMakeLists.txt).
#if !defined(KAIRN_GEN_FIXUP_CALL)
#define KAIRN_GEN_FIXUP_CALL 0
#endif
#if KAIRN_GEN_FIXUP_CALL
// Never inlined, as the shipped prelude has it, and for a second reason: MSVC 19.52 (19.52.37029,
// x64) at /O2 miscompiles such a fix-up when it inlines it. fixup::ball_intersection_2 selects
// three of its parameters (nx ? (ny ? c0 : cx0) : cy0, ...) and returns them in result<Number, 3>;
// inlined into the kernel, it returned its first limb three times, or zeros, where the inline
// form and every other compiler give the operand (full.crosscheck.emulated.ball_intersection_2,
// "emulated-fixup-call: other lines than emulated's"). A program with no Kairn code shows it: a
// struct of a uint64_t and an int, the same eleven parameters and selects, inlined at /O2, gives
// "0 0 102" for "100 101 102"; /O1, /Od, __declspec(noinline) and double limbs are right.
#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_GEN_COLD inline __declspec(noinline)
#else
#define KAIRN_GEN_COLD inline __attribute__((noinline, cold))
#endif
namespace kairn::gen::fixup {
template <class T, int N>
struct result {
    T limb[N];
};
}  // namespace kairn::gen::fixup
#endif
