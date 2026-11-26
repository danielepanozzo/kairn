// The translation unit of the object-code check of the round-up interval (objcode.py --upward;
// docs/developer/design/upward.md, "Object code"). It requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict), with which objcode.py compiles it; nothing here runs. One function per kernel and
// limb type, externally visible and never inlined, that makes the kernel's operands from memory,
// calls it and stores its results, and one per array form:
//
//   kairn_objcode_upward_kernel_double_K, ..._float_K      the form of include/kairn/gen/upward.hpp
//   kairn_objcode_upward_arrays_double_K, ..._float_K      K_arrays, for the kernels that have one
//
// The form is the build's (KAIRN_UPWARD_FORM, KAIRN_UPWARD_ARRAYS), which objcode.py reads from the
// names of the two marker functions. The calls are those of the runner's table,
// gen/tests/upward_kernels.inc. extern "C" keeps the names unmangled in every object format.
#include <cstddef>

#include "kairn/upward.hpp"
#include "kairn/gen/upward.hpp"

#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_OBJCODE_NOINLINE __declspec(noinline)
#else
#define KAIRN_OBJCODE_NOINLINE __attribute__((noinline))
#endif

using namespace kairn::gen::upward;

// The forms this unit is compiled with.
#if KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_SSE2
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_form_sse2() noexcept {}
#elif KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_NEON
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_form_neon() noexcept {}
#else
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_form_numbers() noexcept {}
#endif
#if KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_AVX2
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_arrays_form_avx2() noexcept {}
#elif KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_NEON
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_arrays_form_neon() noexcept {}
#else
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_arrays_form_loop() noexcept {}
#endif

#define KAIRN_OBJCODE_ARGS(L) \
    [[maybe_unused]] const L* in, [[maybe_unused]] L* out, [[maybe_unused]] const bool* mi, [[maybe_unused]] bool* mo
#define KAIRN_OBJCODE_KERNEL(L, NAME, ...)                                                                     \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_kernel_##L##_##NAME(KAIRN_OBJCODE_ARGS(L)) noexcept { \
        using T [[maybe_unused]] = L;                                                                        \
        using P [[maybe_unused]] = pair<L>;                                                                  \
        __VA_ARGS__                                                                                          \
    }
#define KAIRN_UPWARD_KERNEL(NAME, IN, OUT, ...) \
    KAIRN_OBJCODE_KERNEL(double, NAME, __VA_ARGS__) KAIRN_OBJCODE_KERNEL(float, NAME, __VA_ARGS__)

#define KAIRN_OBJCODE_ARRAY_ARGS(L)                                                                   \
    [[maybe_unused]] const L* const* a, [[maybe_unused]] const L* s, [[maybe_unused]] L* const* w, \
        [[maybe_unused]] std::size_t n
#define KAIRN_OBJCODE_ARRAY(L, NAME, CALL) \
    extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_upward_arrays_##L##_##NAME(KAIRN_OBJCODE_ARRAY_ARGS(L)) noexcept { CALL; }
#define KAIRN_UPWARD_ARRAY(NAME, READS, NUMBERS, WRITES, CALL) \
    KAIRN_OBJCODE_ARRAY(double, NAME, CALL) KAIRN_OBJCODE_ARRAY(float, NAME, CALL)

#include "upward_kernels.inc"
