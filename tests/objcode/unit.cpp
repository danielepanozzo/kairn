// The translation unit of the object-code check (objcode.py, docs/developer/testing.md, "Object
// code"): one function per kernel and limb type, externally visible and never inlined, that loads
// the kernel's operands, calls it and stores its results. objcode.py compiles this file with a
// client's compiler and flags, disassembles the object file and counts, in each function and in
// the functions it calls, the fused multiply-adds and the plain floating-point multiplications.
//
// The kernels are those of the runners' table, gen/tests/runner_kernels.inc, which the generator
// writes with the kernels: the same call text serves every limb type, as in runner.cpp.
//
//   kairn_objcode_scalar_double_K, kairn_objcode_scalar_float_K    scalar.hpp
//   kairn_objcode_packed_double_K, kairn_objcode_packed_float_K    avx2.hpp or neon.hpp, with
//                                                                  -DKAIRN_OBJCODE_PACKED
//
// The form of the scalar fix-ups is the compiler's own unless KAIRN_GEN_FIXUP_CALL is given.
// extern "C" keeps the names unmangled, so that objcode.py finds them in every object format.
#include "kairn/gen/scalar.hpp"

#if defined(KAIRN_OBJCODE_PACKED)
#if defined(__AVX2__)
#include "kairn/gen/avx2.hpp"
#elif defined(__aarch64__) || defined(_M_ARM64)
#include "kairn/gen/neon.hpp"
#else
#error "objcode unit: KAIRN_OBJCODE_PACKED without AVX2 or NEON"
#endif
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#define KAIRN_OBJCODE_NOINLINE __declspec(noinline)
#else
#define KAIRN_OBJCODE_NOINLINE __attribute__((noinline))
#endif

// The parameters of a function of the unit: limbs and masks in, limbs and masks out.
#define KAIRN_OBJCODE_ARGS(L, M) \
    [[maybe_unused]] const L* in, [[maybe_unused]] L* out, [[maybe_unused]] const M* mi, [[maybe_unused]] M* mo

#define KAIRN_OBJCODE_FUNCTION(PREFIX, NAME, L, M, CALL) \
    extern "C" KAIRN_OBJCODE_NOINLINE void PREFIX##NAME(KAIRN_OBJCODE_ARGS(L, M)) noexcept { CALL; }

// The form of the scalar fix-ups this unit is compiled with, which objcode.py reads from the
// name of this function.
#if KAIRN_GEN_FIXUP_CALL
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixups_call() noexcept {}
#else
extern "C" KAIRN_OBJCODE_NOINLINE void kairn_objcode_fixups_inline() noexcept {}
#endif

#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    KAIRN_OBJCODE_FUNCTION(kairn_objcode_scalar_double_, NAME, double, bool, CALL) \
    KAIRN_OBJCODE_FUNCTION(kairn_objcode_scalar_float_, NAME, float, bool, CALL)
#include "runner_kernels.inc"
#undef KAIRN_RUNNER_KERNEL

#if defined(KAIRN_OBJCODE_PACKED)
#if defined(__AVX2__)
using kairn_objcode_d = __m256d;
using kairn_objcode_dm = __m256d;
using kairn_objcode_f = __m256;
using kairn_objcode_fm = __m256;
#else
using kairn_objcode_d = float64x2_t;
using kairn_objcode_dm = uint64x2_t;
using kairn_objcode_f = float32x4_t;
using kairn_objcode_fm = uint32x4_t;
#endif
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    KAIRN_OBJCODE_FUNCTION(kairn_objcode_packed_double_, NAME, kairn_objcode_d, kairn_objcode_dm, CALL) \
    KAIRN_OBJCODE_FUNCTION(kairn_objcode_packed_float_, NAME, kairn_objcode_f, kairn_objcode_fm, CALL)
#include "runner_kernels.inc"
#undef KAIRN_RUNNER_KERNEL
#endif
