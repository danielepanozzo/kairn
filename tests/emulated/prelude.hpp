// What the generated kernels for the emulated limb type (gen/kernels.hpp) need besides the type
// itself, in place of include/kairn/gen/prelude.hpp, which is the double and float version: the
// macros the printer writes and the result of a fix-up that is a function of its own. Nothing here
// is about the machine's floating point: the emulated type computes with integers, so there is no
// FMA to require, no contraction to prevent and no inlining to force (the kernels are ordinary
// inline functions, which keeps the compilation of 223 of them short).
#pragma once

#include <cstddef>
#include <limits>

#include "number.hpp"

#define KAIRN_GEN_FORCEINLINE inline
#define KAIRN_GEN_NOINLINE inline
#define KAIRN_GEN_PUSH_WARNINGS
#define KAIRN_GEN_POP_WARNINGS

// The form of the fix-ups of the full kernels and the constructors (milestone1.md, "Emission"):
// inline unless the build says otherwise; the tests build both (tests/CMakeLists.txt).
#if !defined(KAIRN_GEN_FIXUP_CALL)
#define KAIRN_GEN_FIXUP_CALL 0
#endif
#if KAIRN_GEN_FIXUP_CALL
#define KAIRN_GEN_COLD inline
namespace kairn::gen::fixup {
template <class T, int N>
struct result {
    T limb[N];
};
}  // namespace kairn::gen::fixup
#endif
