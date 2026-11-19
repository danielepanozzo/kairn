// What a program can do when Kairn's checks fail: report what kairn::self_test() found, put back
// the floating-point environment that another part of the program changed, and handle a failed
// check of KAIRN_CHECKS itself. The program changes the environment on purpose, as a library might,
// and checks that Kairn reports it with the messages the "Getting started" page quotes. Built and
// run by ctest (tests/api/CMakeLists.txt), which fails if a check fails.

// --8<-- [start:handler]
// Before including Kairn: check the environment and the operands before every operation, also in a
// build with NDEBUG, and on a changed environment call this function instead of stopping.
#define KAIRN_CHECKS 1
#define KAIRN_ENVIRONMENT_FAILURE(reason) ::on_environment_failure(reason)
void on_environment_failure(const char* reason) noexcept;
// --8<-- [end:handler]

#include <kairn/kairn.hpp>

#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
#include <pmmintrin.h>  // _MM_SET_DENORMALS_ZERO_MODE; through <xmmintrin.h>, _MM_SET_FLUSH_ZERO_MODE
#define EXAMPLE_X86 1
#elif defined(__aarch64__) && (defined(__clang__) || defined(__GNUC__))
#define EXAMPLE_AARCH64 1
#endif

namespace {

int failures = 0;
const char* last_reason = nullptr;

void check(bool ok, const char* what, const char* detail = nullptr) {
    std::printf("%s %s%s%s\n", ok ? "ok    " : "FAILED", what, detail ? ": " : "", detail ? detail : "");
    failures += ok ? 0 : 1;
}

bool starts_with(const char* text, const char* prefix) {
    return text != nullptr && std::strncmp(text, prefix, std::strlen(prefix)) == 0;
}

#if defined(EXAMPLE_AARCH64)
std::uint64_t read_fpcr() {
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
void write_fpcr(std::uint64_t value) {
#if defined(__clang__)
    __builtin_arm_wsr64("fpcr", value);
#else
    __builtin_aarch64_set_fpcr64(value);
#endif
}
#endif

// --8<-- [start:restore]
// Puts back the floating-point environment that Kairn assumes: rounding to nearest, and subnormal
// numbers neither flushed to zero as results nor read as zero as operands.
void restore_default_environment() {
    std::fesetround(FE_TONEAREST);
#if defined(EXAMPLE_X86)
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_OFF);        // MXCSR.FTZ
    _MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_OFF);  // MXCSR.DAZ
#elif defined(EXAMPLE_AARCH64)
    write_fpcr(read_fpcr() & ~((std::uint64_t{1} << 24) | 3));  // FPCR.FZ, and FPCR.AH and FIZ
#endif
}
// --8<-- [end:restore]

// What a library compiled with -ffast-math can do at startup: flush subnormal results to zero.
// Returns false where this program has no way to do it.
bool set_flush_to_zero() {
#if defined(EXAMPLE_X86)
    _MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);
    return true;
#elif defined(EXAMPLE_AARCH64)
    write_fpcr(read_fpcr() | (std::uint64_t{1} << 24));
    return true;
#else
    return false;
#endif
}

}  // namespace

void on_environment_failure(const char* reason) noexcept {
    last_reason = reason;  // a program would log it; the operation goes on, without a guarantee
}

int main() {
    // --8<-- [start:report]
    const kairn::Status status = kairn::self_test();
    if (!status) {
        // The first check that failed and, for a generated kernel, which one, such as "split (double)".
        std::fprintf(stderr, "kairn::self_test: %s%s%s\n", status.message(), status.kernel ? ": " : "",
                     status.kernel ? status.kernel : "");
        return 1;
    }
    // --8<-- [end:report]
    check(kairn::environment_ok(), "the environment is the default one at startup");

    using Number = kairn::Expansion<double, 2>;
    volatile double tiny = 0x1p-60;

    // Another part of the program rounds upward, as an interval library might, and leaves it so.
    if (std::fesetround(FE_UPWARD) == 0) {
        check(!kairn::environment_ok(), "environment_ok() sees the rounding mode");
        check(std::strcmp(kairn::self_test().message(), "rounding is not to nearest with ties to even") == 0,
              "self_test() says so", kairn::self_test().message());
        const Number x = Number(1.0) + double(tiny);  // checked first: the handler is called
        check(starts_with(last_reason, "the rounding mode is not to nearest"), "KAIRN_CHECKS calls the handler",
              last_reason);
        (void)x;
        // --8<-- [start:check]
        if (!kairn::environment_ok()) {
            restore_default_environment();
        }
        // --8<-- [end:check]
        check(kairn::environment_ok() && kairn::self_test().ok(), "both pass again once it is restored");
    } else {
        std::printf("skip   rounding upward cannot be set here\n");
    }

    // A library sets flush-to-zero.
    if (set_flush_to_zero()) {
        check(!kairn::environment_ok(), "environment_ok() sees flush-to-zero");
        check(std::strcmp(kairn::self_test().message(), "subnormal results are flushed to zero") == 0,
              "self_test() says so", kairn::self_test().message());
        last_reason = nullptr;
        const Number x = Number(1.0) + double(tiny);
        check(last_reason != nullptr && std::strstr(last_reason, "flushed to zero") != nullptr,
              "KAIRN_CHECKS calls the handler", last_reason);
        (void)x;
        restore_default_environment();
        check(kairn::environment_ok() && kairn::self_test().ok(), "both pass again once it is restored");
    } else {
        std::printf("skip   flush-to-zero cannot be set here\n");
    }
    return failures == 0 ? 0 : 1;
}
