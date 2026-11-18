// constexpr_test.cpp: the same expression in constant evaluation and at run time.
// Note: the constant-evaluation product uses unfused cross terms, the run-time product uses FMAs,
// so the low words may differ by rounding; TwoProd/TwoSum must agree bit for bit. Both are printed.
#include <cstdio>
#include "proto.hpp"
using proto::Expansion;
using proto::pair;

constexpr pair<double> cp = proto::two_prod(0x1.123456789abcdp+3, 0x1.fedcba9876543p-7);
constexpr pair<double> cs = proto::two_sum(0x1.123456789abcdp+3, 0x1.fedcba9876543p-60);
constexpr pair<float> cpf = proto::two_prod(0x1.234568p+3f, 0x1.fedcbap-7f);
constexpr Expansion<double, 2> third{0x1.5555555555555p-2, 0x1.5555555555555p-56};
constexpr Expansion<double, 2> ch = proto::horner3(Expansion<double, 2>(1.0), third, third, third);
constexpr Expansion<double, 1> c1 = proto::horner3(Expansion<double, 1>(1.0), Expansion<double, 1>(0.1),
                                                   Expansion<double, 1>(0.2), Expansion<double, 1>(0.3));
static_assert(cp.hi + cp.lo == cp.hi, "TwoProd's error is below half an ulp of the product");
static_assert(std::is_trivially_copyable_v<Expansion<double, 2>> && std::is_standard_layout_v<Expansion<double, 2>>);
static_assert(sizeof(Expansion<double, 1>) == sizeof(double) && sizeof(Expansion<float, 2>) == 2 * sizeof(float));

int main() {
    volatile double a = 0x1.123456789abcdp+3, b = 0x1.fedcba9876543p-7, c = 0x1.fedcba9876543p-60;
    volatile float af = 0x1.234568p+3f, bf = 0x1.fedcbap-7f;
    volatile double th = 0x1.5555555555555p-2, tl = 0x1.5555555555555p-56, one = 1.0;
    const pair<double> rp = proto::two_prod<double>(a, b);
    const pair<double> rs = proto::two_sum<double>(a, c);
    const pair<float> rpf = proto::two_prod<float>(af, bf);
    const Expansion<double, 2> t{th, tl};
    const Expansion<double, 2> rh = proto::horner3(Expansion<double, 2>(one), t, t, t);
    int bad = 0;
    bad += !(rp.hi == cp.hi && rp.lo == cp.lo);
    bad += !(rs.hi == cs.hi && rs.lo == cs.lo);
    bad += !(rpf.hi == cpf.hi && rpf.lo == cpf.lo);
    std::printf("two_prod  constexpr %a %a   run time %a %a\n", cp.hi, cp.lo, rp.hi, rp.lo);
    std::printf("two_sum   constexpr %a %a   run time %a %a\n", cs.hi, cs.lo, rs.hi, rs.lo);
    std::printf("two_prodf constexpr %a %a   run time %a %a\n", cpf.hi, cpf.lo, rpf.hi, rpf.lo);
    std::printf("horner dd constexpr %a %a   run time %a %a\n", ch.limb[0], ch.limb[1], rh.limb[0], rh.limb[1]);
    std::printf("horner k1 constexpr %a\n", c1.limb[0]);
    std::printf("%s\n", bad ? "MISMATCH between constant evaluation and run time" : "error-free transformations: constant evaluation == run time");
    return bad;
}
