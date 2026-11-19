// kairn::environment_ok() and kairn::self_test(): both pass in the default environment, and each
// detects what it is for. The test changes the rounding mode through <cfenv>, and sets flush to
// zero by writing the control register directly where the platform allows it (MXCSR on x86-64,
// FPCR on AArch64), then restores the environment it found.
#include <kairn/kairn.hpp>

#include <cfenv>
#include <cstdint>
#include <cstdio>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace {

int failures = 0;
int checks = 0;

void expect(bool ok, const char* what, const char* detail = nullptr) {
    ++checks;
    std::printf("%s: %s%s%s\n", ok ? "ok    " : "FAILED", what, detail ? " -- " : "", detail ? detail : "");
    if (!ok) ++failures;
}

// Both checks must reject the environment set by the caller; self_test() must say why.
void expect_rejected(const char* what) {
    const bool env = kairn::environment_ok();
    const kairn::Status s = kairn::self_test();
    char line[160];
    std::snprintf(line, sizeof line, "environment_ok() is false under %s", what);
    expect(!env, line);
    std::snprintf(line, sizeof line, "self_test() fails under %s", what);
    expect(!s.ok(), line, s.message());
}

#if defined(__x86_64__) || defined(_M_X64)
void flush_to_zero() {
    const unsigned csr = _mm_getcsr();
    _mm_setcsr(csr | 0x8000u);   // FTZ
    expect_rejected("flush-to-zero (MXCSR.FTZ)");
    _mm_setcsr(csr | 0x0040u);   // DAZ
    expect_rejected("denormals-are-zero (MXCSR.DAZ)");
    _mm_setcsr(csr);
}
#elif defined(__aarch64__) && defined(__clang__)
void flush_to_zero() {
    const std::uint64_t fpcr = __builtin_arm_rsr64("fpcr");
    __builtin_arm_wsr64("fpcr", fpcr | (std::uint64_t{1} << 24));   // FZ
    expect_rejected("flush-to-zero (FPCR.FZ)");
    __builtin_arm_wsr64("fpcr", fpcr);
}
#elif defined(__aarch64__) && defined(__GNUC__)
void flush_to_zero() {
    const std::uint64_t fpcr = __builtin_aarch64_get_fpcr64();
    __builtin_aarch64_set_fpcr64(fpcr | (std::uint64_t{1} << 24));  // FZ
    expect_rejected("flush-to-zero (FPCR.FZ)");
    __builtin_aarch64_set_fpcr64(fpcr);
}
#else
void flush_to_zero() { std::printf("skip  : no way to set flush-to-zero is written for this platform\n"); }
#endif

}  // namespace

int main() {
    const kairn::Status initial = kairn::self_test();
    expect(kairn::environment_ok(), "environment_ok() in the default environment");
    expect(initial.ok(), "self_test() in the default environment", initial.message());

    const struct {
        int mode;
        const char* name;
    } modes[] = {{FE_UPWARD, "rounding upward"}, {FE_DOWNWARD, "rounding downward"}, {FE_TOWARDZERO, "rounding toward zero"}};
    for (const auto& m : modes) {
        if (std::fesetround(m.mode) != 0) {
            std::printf("skip  : %s cannot be set here\n", m.name);
            continue;
        }
        expect_rejected(m.name);
        std::fesetround(FE_TONEAREST);
    }
    flush_to_zero();

    expect(kairn::environment_ok() && kairn::self_test().ok(), "both pass again once the environment is restored");
    std::printf("%d checks, %d failed\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
