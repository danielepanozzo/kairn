// The generated scalar kernels, kairn/gen/scalar.hpp, without the rest of Kairn: every kernel of
// gen/tests/runner_kernels.inc called once for double and once for float limbs, each call in a
// function of its own, the functions in a table that the program could call (bench/compile_time.py).
// It is the table of gen/tests/runner.cpp without the runner around it. KCT_KERNELS names another
// list of the same form, for the time of one kernel alone.
#include <kairn/gen/scalar.hpp>

#ifndef KCT_KERNELS
#define KCT_KERNELS runner_kernels.inc
#endif
#define KCT_STR(x) #x
#define KCT_XSTR(x) KCT_STR(x)

struct KctKernel {
    const char* name;
    void (*binary64)(const double* in, double* out, const bool* mi, bool* mo);
    void (*binary32)(const float* in, float* out, const bool* mi, bool* mo);
};

#define KCT_ARGS(T) \
    [[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] const bool* mi, [[maybe_unused]] bool* mo
#define KAIRN_RUNNER_KERNEL(NAME, IN, OUT, CALL) \
    {#NAME, [](KCT_ARGS(double)) { CALL; }, [](KCT_ARGS(float)) { CALL; }},

extern const KctKernel kct_kernels[] = {
#include KCT_XSTR(KCT_KERNELS)
    {nullptr, nullptr, nullptr},
};
