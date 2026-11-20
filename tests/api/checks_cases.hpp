// The cases that tests/api/checks.cpp and tests/api/checks_handler.cpp share: the operands, every
// operation and constructor that the checks of KAIRN_CHECKS guard, written as a program writes it,
// and the states of the floating-point environment this target can set. A program that defines
// KAIRN_ENVIRONMENT_FAILURE does so before including this file.
#pragma once

#include <kairn/kairn.hpp>

#include <cfenv>
#include <cstdint>
#include <limits>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

namespace kairn_test {

using E1 = kairn::Expansion<double, 1>;
using E2 = kairn::Expansion<double, 2>;
using F2 = kairn::Expansion<float, 2>;
using B1 = kairn::Ball<double, 1>;
using B2 = kairn::Ball<double, 2>;
using kairn::unverified;

// Operands read from volatile objects, so that nothing is computed before the program asks. The
// two-limb ones are canonical pairs whose test, x0 + x1 == x0, is false under a directed rounding
// mode: (1.5, 2^-60) under rounding upward, (2.25, -2^-58) under rounding downward and toward
// zero.
inline volatile double v_a = 1.5, v_b = 0x1p-60, v_c = 2.25, v_d = -0x1p-58, v_r = 0x1p-20;
inline volatile float v_fa = 1.5f, v_fb = 0x1p-30f;
inline volatile double sink = 0;
inline constexpr double infinity = std::numeric_limits<double>::infinity();
inline constexpr double not_a_number = std::numeric_limits<double>::quiet_NaN();

inline E2 pair(double h, double l) {
    const double limbs[2] = {h, l};
    return E2::from_limbs(limbs);
}
// A pair whose limbs are written directly: the only way to make one that is not canonical.
inline E2 raw(double h, double l) {
    E2 x;
    x.limb[0] = h;
    x.limb[1] = l;
    return x;
}
// The operands of the operations, made in the default environment before any state is set, so
// that each operation below is what meets the state; the constructors meet it in cases of their
// own.
struct Operands {
    E2 x, y;
    F2 fx;
    B1 p, q;
    B2 bp, bq;
};
inline Operands o;
inline void make_operands() {
    const float limbs[2] = {v_fa, v_fb};
    o.x = pair(v_a, v_b);
    o.y = pair(v_c, v_d);
    o.fx = F2::from_limbs(limbs);
    o.p = B1(unverified(E1(v_a)), v_r);
    o.q = B1(unverified(E1(v_c)), v_r);
    o.bp = B2(unverified(o.x), v_r);
    o.bq = B2(unverified(o.y), v_r);
}

// Every operation, written as a program writes it, with kairn::unverified on the first operand so
// that it compiles whatever gen/claims.json says (the marker changes nothing else); then the
// constructors that check what they are given, on the canonical pairs above.
struct Operation {
    const char* name;
    double (*run)();
};
inline const Operation operations[] = {
    {"e1.add", [] { return (unverified(E1(v_a)) + E1(v_c)).limb[0]; }},
    {"e1.mul", [] { return (unverified(E1(v_a)) * E1(v_c)).limb[0]; }},
    {"e1.ldexp", [] { return kairn::ldexp(unverified(E1(v_a)), 3).limb[0]; }},
    {"e1.less", [] { return double(unverified(E1(v_a)) < E1(v_c)); }},
    {"e2.add", [] { return (unverified(o.x) + o.y).limb[1]; }},
    {"e2.add_limb", [] { return (unverified(o.x) + double(v_c)).limb[1]; }},
    {"e2.sub", [] { return (unverified(o.x) - o.y).limb[1]; }},
    {"e2.limb_sub", [] { return (unverified(double(v_c)) - o.x).limb[1]; }},
    {"e2.mul", [] { return (unverified(o.x) * o.y).limb[1]; }},
    {"e2.mul_limb", [] { return (unverified(o.x) * double(v_c)).limb[1]; }},
    {"e2.add_fast", [] { return kairn::add_fast(unverified(o.x), o.y).limb[1]; }},
    {"e2.ldexp", [] { return kairn::ldexp(unverified(o.x), -5).limb[1]; }},
    {"e2.half", [] { return kairn::half(unverified(o.x)).limb[1]; }},
    {"e2.neg", [] { return (-unverified(o.x)).limb[1]; }},
    {"e2.abs", [] { return kairn::abs(unverified(o.x)).limb[1]; }},
    {"e2.less", [] { return double(unverified(o.x) < o.y); }},
    {"e2.equal_limb", [] { return double(unverified(o.x) == double(v_c)); }},
    {"e2.to_nearest", [] { return kairn::to_nearest(unverified(o.x)); }},
    {"e2.to_up", [] { return kairn::to_up(unverified(o.x)); }},
    {"e2.narrow", [] { return E1(unverified(o.x)).limb[0]; }},
    {"f2.add", [] { return double((unverified(o.fx) + o.fx).limb[1]); }},
    {"finite.add", [] { return kairn::finite::add(unverified(o.x), o.y).limb[1]; }},
    {"finite.mul", [] { return kairn::finite::mul(unverified(o.x), o.y).limb[1]; }},
    {"finite.ldexp", [] { return kairn::finite::ldexp(unverified(o.x), 7).limb[1]; }},
    {"ball1.add", [] { return (unverified(o.p) + o.q).radius(); }},
    {"ball1.scale", [] { return (unverified(o.p) * double(v_c)).radius(); }},
    {"ball1.neg", [] { return (-unverified(o.p)).radius(); }},
    {"ball2.mul", [] { return (unverified(o.bp) * o.bq).radius(); }},
    {"ball2.sub_point", [] { return (unverified(o.bp) - double(v_c)).radius(); }},
    {"from_limbs.upward", [] { return pair(v_a, v_b).limb[1]; }},
    {"from_limbs.downward", [] { return pair(v_c, v_d).limb[1]; }},
    {"ball1.make", [] { return B1(unverified(E1(v_a)), v_r).radius(); }},
    {"ball1.point", [] { return B1(unverified(double(v_a))).radius(); }},
    {"ball2.make", [] { return B2(unverified(o.x), v_r).radius(); }},
    {"ball2.make_downward", [] { return B2(unverified(o.y), v_r).radius(); }},
    {"ball2.center", [] { return B2(unverified(o.y)).radius(); }},
    {"ball2.point", [] { return B2(unverified(double(v_c))).radius(); }},
};

// The states of the environment: set() changes it, restore() puts back what was found, and
// reason is what Kairn's message says of it.
struct State {
    const char* name;
    bool (*set)();
    void (*restore)();
    const char* reason;
};
inline int saved_round = FE_TONEAREST;
inline bool set_round(int mode) {
    saved_round = std::fegetround();
    return std::fesetround(mode) == 0 && std::fegetround() == mode;
}
inline void restore_round() { std::fesetround(saved_round); }
#if defined(__x86_64__) || defined(_M_X64)
inline unsigned saved_csr = 0;
inline bool set_csr(unsigned bits) {
    saved_csr = _mm_getcsr();
    _mm_setcsr(saved_csr | bits);
    return (_mm_getcsr() & bits) == bits;
}
inline void restore_csr() { _mm_setcsr(saved_csr); }
#elif defined(__aarch64__)
inline std::uint64_t saved_fpcr = 0;
inline std::uint64_t read_fpcr() {
#if defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
inline void write_fpcr(std::uint64_t v) {
#if defined(__clang__)
    __builtin_arm_wsr64("fpcr", v);
#else
    __builtin_aarch64_set_fpcr64(v);
#endif
}
inline bool set_fpcr(std::uint64_t bits) {
    saved_fpcr = read_fpcr();
    write_fpcr(saved_fpcr | bits);
    return (read_fpcr() & bits) == bits;
}
inline void restore_fpcr() { write_fpcr(saved_fpcr); }
#endif
inline const char* const not_to_nearest = "the rounding mode is not to nearest";
inline const State states[] = {
    {"upward", [] { return set_round(FE_UPWARD); }, restore_round, not_to_nearest},
    {"downward", [] { return set_round(FE_DOWNWARD); }, restore_round, not_to_nearest},
    {"toward-zero", [] { return set_round(FE_TOWARDZERO); }, restore_round, not_to_nearest},
#if defined(__x86_64__) || defined(_M_X64)
    {"ftz", [] { return set_csr(0x8000u); }, restore_csr, "flushed to zero"},  // MXCSR.FTZ
    {"daz", [] { return set_csr(0x0040u); }, restore_csr, "read as zero"},     // MXCSR.DAZ
#elif defined(__aarch64__)
    {"fz", [] { return set_fpcr(std::uint64_t{1} << 24); }, restore_fpcr, "flushed to zero"},  // FPCR.FZ
#endif
};

}  // namespace kairn_test
