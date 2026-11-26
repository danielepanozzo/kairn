// The tests of <kairn/upward.hpp>'s environment (tests/api/upward/), which require the rounding mode
// upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
// -frounding-math, MSVC /fp:strict), but where a test says otherwise: what they share. The state
// of the floating-point environment is read and written here directly, through the control
// register (MXCSR on x86, FPCR on AArch64) and <cfenv>, not through the header, so that what the
// scopes do is observed from outside; and arithmetic on operands read from volatile objects tells
// which rounding the hardware applied.
#pragma once

#include <bit>
#include <cfenv>
#include <cstdint>
#include <cstdio>
#include <limits>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__) || defined(_M_IX86)
#include <immintrin.h>
#define UPWARD_TEST_MXCSR 1
#elif defined(__aarch64__) && (defined(__GNUC__) || defined(__clang__))
#include <arm_neon.h>
#define UPWARD_TEST_FPCR 1
#endif

namespace upward_test {

inline int failures = 0;
inline int checks = 0;

inline void expect(bool ok, const char* what) {
    ++checks;
    std::printf("%s: %s\n", ok ? "ok    " : "FAILED", what);
    std::fflush(stdout);
    if (!ok) ++failures;
}

inline int summary(const char* name) {
    std::printf("%s: %d checks, %d failed\n", name, checks, failures);
    return failures == 0 ? 0 : 1;
}

inline const char* mode_name(int mode) {
    if (mode == FE_TONEAREST) return "to nearest";
    if (mode == FE_UPWARD) return "upward";
    if (mode == FE_DOWNWARD) return "downward";
    if (mode == FE_TOWARDZERO) return "toward zero";
    return "unknown";
}

// --- The control register ---------------------------------------------------------------------------
#if defined(UPWARD_TEST_MXCSR)
using reg_t = std::uint32_t;
inline reg_t read_reg() { return _mm_getcsr(); }
inline void write_reg(reg_t v) { _mm_setcsr(v); }
inline constexpr reg_t rounding_field = 0x6000u;
inline constexpr reg_t flag_inexact = 0x20u;  // PE
inline reg_t rounding_bits(int mode) {
    return mode == FE_UPWARD ? 0x4000u : mode == FE_DOWNWARD ? 0x2000u : mode == FE_TOWARDZERO ? 0x6000u : 0u;
}
inline int rounding_of(reg_t r) {
    const reg_t b = r & rounding_field;
    return b == 0x4000u ? FE_UPWARD : b == 0x2000u ? FE_DOWNWARD : b == 0x6000u ? FE_TOWARDZERO : FE_TONEAREST;
}
// FTZ and DAZ.
inline reg_t flush_bits() { return 0x8040u; }
#elif defined(UPWARD_TEST_FPCR)
using reg_t = std::uint64_t;
inline reg_t read_reg() {
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
inline void write_reg(reg_t v) {
#if defined(__clang__)
    __builtin_arm_wsr64("fpcr", v);
#else
    __builtin_aarch64_set_fpcr64(v);
#endif
}
inline constexpr reg_t rounding_field = reg_t{3} << 22;
inline reg_t rounding_bits(int mode) {
    return mode == FE_UPWARD ? reg_t{1} << 22 : mode == FE_DOWNWARD ? reg_t{2} << 22 : mode == FE_TOWARDZERO ? reg_t{3} << 22 : 0;
}
inline int rounding_of(reg_t r) {
    const reg_t b = (r & rounding_field) >> 22;
    return b == 1 ? FE_UPWARD : b == 2 ? FE_DOWNWARD : b == 3 ? FE_TOWARDZERO : FE_TONEAREST;
}
// FZ, and AH and FIZ where FEAT_AFP is implemented: those two are written once and kept only if
// they read back as set (otherwise they are RES0).
inline reg_t flush_bits() {
    static const reg_t bits = [] {
        const reg_t r = read_reg();
        write_reg(r | reg_t{3});
        const reg_t afp = read_reg() & reg_t{3};
        write_reg(r);
        return (reg_t{1} << 24) | afp;
    }();
    return bits;
}
#endif

#if defined(UPWARD_TEST_MXCSR) || defined(UPWARD_TEST_FPCR)
inline constexpr bool has_register = true;
// The rounding mode of the register.
inline int register_mode() { return rounding_of(read_reg()); }
// Sets the rounding mode of the register, and nothing else (not the C library's own state).
inline void set_register_mode(int mode) { write_reg((read_reg() & ~rounding_field) | rounding_bits(mode)); }
// The flush bits of the register that are set.
inline reg_t register_flush() { return read_reg() & flush_bits(); }
inline void set_register_flush(bool on) {
    const reg_t r = read_reg() & ~flush_bits();
    write_reg(on ? r | flush_bits() : r);
}
#else
inline constexpr bool has_register = false;
inline int register_mode() { return std::fegetround(); }
inline void set_register_mode(int mode) { std::fesetround(mode); }
inline unsigned flush_bits() { return 0; }
inline unsigned register_flush() { return 0; }
inline void set_register_flush(bool) {}
#endif

// Sets the C library's mode and the register's to mode, and flush to zero (with denormals-are-zero,
// and AH and FIZ where they exist) on or off.
inline void set_environment(int mode, bool flush) {
    std::fesetround(mode);
    set_register_mode(mode);
    set_register_flush(flush);
}

// --- What the hardware does -------------------------------------------------------------------------
inline volatile double v_one = 1.0, v_tiny = 0x1p-60, v_three_quarters = 0x1.8p-53, v_half = 0.5;
inline volatile double v_lambda = std::numeric_limits<double>::min(), v_eta = std::numeric_limits<double>::denorm_min();
inline volatile double v_sink = 0;

inline bool same_bits(double a, double b) { return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b); }
inline bool same_bits(float a, float b) { return std::bit_cast<std::uint32_t>(a) == std::bit_cast<std::uint32_t>(b); }

// The rounding the hardware applies to a sum of operands read from volatile objects: 1 + 2^-60 is
// above 1 only upward, -1 - 2^-60 below -1 only downward, and 1 + 0.75 2^-52 is 1 + 2^-52 to nearest
// and 1 toward zero.
inline int hardware_mode() {
    const double one = v_one, tiny = v_tiny, tq = v_three_quarters;
    const double up = one + tiny, down = -one - tiny, most = one + tq;
    v_sink = up + down + most;
    if (up > 1) return FE_UPWARD;
    if (down < -1) return FE_DOWNWARD;
    return most > 1 ? FE_TONEAREST : FE_TOWARDZERO;
}

// Whether a subnormal result is kept (no flush to zero: lambda / 2 is subnormal) and a subnormal
// operand read as itself (no denormals-are-zero: eta + eta is 2 eta), compared bit for bit.
inline bool subnormals_kept() {
    const double lambda = v_lambda, half = v_half, eta = v_eta;
    const double r = lambda * half, s = eta + eta;
    v_sink = r + s;
    return same_bits(r, std::numeric_limits<double>::min() / 2) && same_bits(s, 2 * std::numeric_limits<double>::denorm_min());
}

// An inexact operation, which raises the inexact flag.
inline void raise_inexact() { v_sink = v_one + v_tiny; }

inline bool inexact_raised() {
    bool raised = std::fetestexcept(FE_INEXACT) != 0;
#if defined(UPWARD_TEST_MXCSR)
    raised = raised && (read_reg() & flag_inexact) != 0;  // the flag of MXCSR itself
#endif
    return raised;
}

}  // namespace upward_test
