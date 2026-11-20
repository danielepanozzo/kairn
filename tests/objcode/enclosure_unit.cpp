// The translation unit of the object-code check of the settings of KAIRN_ENCLOSURE_CODE that take
// the operations of Ball out of their callers (include/kairn/config.hpp; objcode.py,
// docs/developer/testing.md, "Object code"): one function per operation and limb type, externally
// visible and never inlined, that applies the public operator to operands it loads and stores the
// result. The scaling by a power of two is half(X), one call of its kernel; ldexp(X, n) calls it two
// or three times when 2^n is not a number of T, from its inline steps, each a call of the same
// function.
//
//   kairn_objcode_enclosure_double_K, kairn_objcode_enclosure_float_K   K the full Ball kernel the
//                                                                       operator calls
//
// objcode.py compiles it three times, with KAIRN_CHECKS 0 (a release build):
// - with KAIRN_ENCLOSURE_CODE_OUTLINED: each function must have no fused multiply-add and no
//   multiplication of its own, and call one of the object that has exactly those of K;
// - with KAIRN_ENCLOSURE_CODE_EXTERNAL: each must have none, and call the operation, a function
//   outside the object (kairn::detail::external::...);
// - with KAIRN_ENCLOSURE_CODE_EXTERNAL and KAIRN_OBJCODE_DEFINITIONS, which includes
//   kairn/definitions.hpp: the same call, now to the definition in the object, which has those of
//   K, as in the outlined form.
// Its control (objcode.py --controls) compiles it with KAIRN_ENCLOSURE_CODE_INLINE, judged as the
// outlined form, which must fail for every function: the operation is not a call.
//
// The form of the scalar fix-ups is the compiler's own unless KAIRN_GEN_FIXUP_CALL is given, and
// the marker function says which, as in unit.cpp.
#include <kairn/kairn.hpp>
#if defined(KAIRN_OBJCODE_DEFINITIONS)
#include <kairn/definitions.hpp>
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_OBJCODE_NOINLINE __declspec(noinline)
#else
#define KAIRN_OBJCODE_NOINLINE __attribute__((noinline))
#endif

#if KAIRN_GEN_FIXUP_CALL
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixups_call() noexcept {}
#else
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixups_inline() noexcept {}
#endif

#define KAIRN_OBJCODE_ENCLOSURE(T, K, KERNEL, EXPR)                                                          \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_enclosure_##T##_##KERNEL(                           \
        const kairn::Ball<T, K>* x, const kairn::Ball<T, K>* y, const T* a, kairn::Ball<T, K>* z) noexcept { \
        (void)y;                                                                                             \
        (void)a;                                                                                             \
        *z = EXPR;                                                                                           \
    }
#define KAIRN_OBJCODE_ENCLOSURES(T)                                      \
    KAIRN_OBJCODE_ENCLOSURE(T, 1, ball_add_1_full, *x + *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 1, ball_sub_1_full, *x - *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 1, ball_mul_1_full, *x * *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 1, ball_scale_1_full, *x * *a)            \
    KAIRN_OBJCODE_ENCLOSURE(T, 2, ball_add_2_full, *x + *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 2, ball_sub_2_full, *x - *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 2, ball_mul_2_full, *x * *y)              \
    KAIRN_OBJCODE_ENCLOSURE(T, 2, ball_scale_2_full, *x * *a)            \
    KAIRN_OBJCODE_ENCLOSURE(T, 1, ball_mul_pow2_1_full, kairn::half(*x)) \
    KAIRN_OBJCODE_ENCLOSURE(T, 2, ball_mul_pow2_2_full, kairn::half(*x))
KAIRN_OBJCODE_ENCLOSURES(double)
KAIRN_OBJCODE_ENCLOSURES(float)
