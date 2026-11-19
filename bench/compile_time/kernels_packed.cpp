// The generated packed kernels, kairn/gen/avx2.hpp or kairn/gen/neon.hpp, without the rest of
// Kairn: every kernel of gen/tests/runner_kernels.inc called once on registers of double and once
// on registers of float, each call in a function of its own, the functions in a table that the
// program could call (bench/compile_time.py). It is the table of gen/tests/packed_runner.cpp
// without the runner around it. KCT_KERNELS names another list of the same form, for the time of
// one kernel alone.
#if defined(__AVX2__)
#include <kairn/gen/avx2.hpp>
struct KctD {
    using V = __m256d;
    using M = __m256d;
};
struct KctF {
    using V = __m256;
    using M = __m256;
};
#elif defined(__aarch64__) || defined(_M_ARM64)
#include <kairn/gen/neon.hpp>
struct KctD {
    using V = float64x2_t;
    using M = uint64x2_t;
};
struct KctF {
    using V = float32x4_t;
    using M = uint32x4_t;
};
#else
#error "kernels_packed.cpp: no packed backend for this target"
#endif

#ifndef KCT_KERNELS
#define KCT_KERNELS runner_kernels.inc
#endif
#define KCT_STR(x) #x
#define KCT_XSTR(x) KCT_STR(x)

struct KctKernel {
    const char* name;
    void (*binary64)(const KctD::V* in, KctD::V* out, const KctD::M* mi, KctD::M* mo);
    void (*binary32)(const KctF::V* in, KctF::V* out, const KctF::M* mi, KctF::M* mo);
};

#define KCT_ARGS(P) \
    [[maybe_unused]] const P::V* in, [[maybe_unused]] P::V* out, [[maybe_unused]] const P::M* mi, [[maybe_unused]] P::M* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    {#NAME, [](KCT_ARGS(KctD)) { CALL; }, [](KCT_ARGS(KctF)) { CALL; }},

extern const KctKernel kct_kernels[] = {
#include KCT_XSTR(KCT_KERNELS)
    {nullptr, nullptr, nullptr},
};
