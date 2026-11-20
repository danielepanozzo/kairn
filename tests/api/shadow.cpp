// Every public operation of Kairn once, for float and double limbs, so that every function of the
// headers that a program can reach is compiled: tests/api/shadow.py compiles this file with the
// strictest warnings each compiler has about a declaration that hides another, as errors.
//
// With KAIRN_TEST_GLOBALS defined, shadow_globals.hpp, which shadow.py writes, is included first:
// a global variable for each name of a parameter or a local variable of Kairn's headers, as a
// program may have. This file's own names all start with use_, which shadow.py checks no name of
// Kairn's starts with, so that none of them hides a global of shadow_globals.hpp.
#if defined(KAIRN_TEST_GLOBALS)
#include "shadow_globals.hpp"
#endif
#define KAIRN_CHECKS 1
#include <kairn/kairn.hpp>

namespace use_test {

template <class UseT>
double use_every_operation(UseT use_a, UseT use_b) {
    using E1 = kairn::Expansion<UseT, 1>;
    using E2 = kairn::Expansion<UseT, 2>;
    using B1 = kairn::Ball<UseT, 1>;
    using B2 = kairn::Ball<UseT, 2>;
    using kairn::unverified;
    double use_sum = 0;
    auto use_add = [&use_sum](auto use_v) { use_sum += double(use_v); };

    // One limb: the constructors, the operators, the named functions and kairn::finite::.
    const UseT use_l1[1] = {use_a};
    E1 use_p = E1(use_a), use_q(use_b), use_r = E1::from_limbs(use_l1), use_s = E1::from_limbs_unchecked(use_l1);
    use_add((use_p + use_q).limb[0] + (use_p - use_q).limb[0] + (use_p * use_q).limb[0] + (-use_p).limb[0]);
    use_add((use_p + use_a).limb[0] + (use_a - use_p).limb[0] + (use_p * use_a).limb[0]);
    use_r += use_q;
    use_r -= use_q;
    use_r *= use_q;
    use_s += use_a;
    use_add(use_r.limb[0] + use_s.limb[0]);
    use_add((use_p < use_q) + (use_p > use_q) + (use_p <= use_q) + (use_p >= use_q) + (use_p == use_q) +
            (use_p != use_q));
    use_add(kairn::abs(use_p).limb[0] + kairn::add_fast(use_p, use_q).limb[0] + kairn::ldexp(use_p, 3).limb[0] +
            kairn::half(use_p).limb[0]);
    use_add(kairn::to_nearest(use_p) + kairn::to_down(use_p) + kairn::to_up(use_p) + kairn::abs_upper(use_p));
    use_add(kairn::sign(use_p) + kairn::isfinite(use_p) + kairn::is_normalized(use_p));
    use_add(kairn::finite::add(use_p, use_q).limb[0] + kairn::finite::add(use_p, use_a).limb[0] +
            kairn::finite::add(use_a, use_p).limb[0] + kairn::finite::sub(use_p, use_q).limb[0] +
            kairn::finite::sub(use_p, use_a).limb[0] + kairn::finite::sub(use_a, use_p).limb[0] +
            kairn::finite::mul(use_p, use_q).limb[0] + kairn::finite::mul(use_p, use_a).limb[0] +
            kairn::finite::mul(use_a, use_p).limb[0] + kairn::finite::add_fast(use_p, use_q).limb[0] +
            kairn::finite::ldexp(use_p, -2).limb[0]);
    // The marked forms.
    use_add((unverified(use_p) + use_q).limb[0] + (use_p - unverified(use_q)).limb[0] +
            (unverified(use_p) * use_a).limb[0] + (-unverified(use_p)).limb[0]);
    use_r += unverified(use_q);
    use_r -= unverified(use_a);
    use_r *= unverified(use_q);
    use_add((unverified(use_p) < use_q) + (unverified(use_p) > use_q) + (unverified(use_p) <= use_q) +
            (unverified(use_p) >= use_q) + (unverified(use_p) == use_q) + (unverified(use_p) != use_q));
    use_add(kairn::abs(unverified(use_p)).limb[0] + kairn::add_fast(unverified(use_p), use_q).limb[0] +
            kairn::ldexp(unverified(use_p), 1).limb[0] + kairn::half(unverified(use_p)).limb[0]);
    use_add(kairn::to_nearest(unverified(use_p)) + kairn::to_down(unverified(use_p)) +
            kairn::to_up(unverified(use_p)) + kairn::abs_upper(unverified(use_p)));
    use_add(kairn::finite::add(unverified(use_p), use_q).limb[0] + kairn::finite::sub(use_p, unverified(use_a)).limb[0] +
            kairn::finite::mul(unverified(use_p), use_q).limb[0] +
            kairn::finite::add_fast(unverified(use_p), use_q).limb[0] + kairn::finite::ldexp(unverified(use_p), 1).limb[0]);

    // Two limbs: every form of every operator, with a two-limb, a one-limb and a limb operand.
    const UseT use_l2[2] = {use_a, UseT(0)};
    E2 use_x = E2(use_a), use_y(use_q), use_z = E2::from_limbs(use_l2), use_w = E2::from_limbs_unchecked(use_l2);
    E2 use_m(unverified(use_b)), use_n(unverified(use_p));
    use_add((use_x + use_y).limb[1] + (use_x + use_a).limb[1] + (use_a + use_x).limb[1] + (use_x + use_p).limb[1] +
            (use_p + use_x).limb[1]);
    use_add((use_x - use_y).limb[1] + (use_x - use_a).limb[1] + (use_a - use_x).limb[1] + (use_x - use_p).limb[1] +
            (use_p - use_x).limb[1]);
    use_add((use_x * use_y).limb[1] + (use_x * use_a).limb[1] + (use_a * use_x).limb[1] + (use_x * use_p).limb[1] +
            (use_p * use_x).limb[1] + (-use_x).limb[1]);
    use_z += use_y;
    use_z += use_a;
    use_z += use_p;
    use_z -= use_y;
    use_z -= use_a;
    use_z -= use_p;
    use_z *= use_y;
    use_z *= use_a;
    use_z *= use_p;
    use_add(use_z.limb[1] + use_w.limb[1] + use_m.limb[1] + use_n.limb[1]);
    use_add((use_x < use_y) + (use_x > use_y) + (use_x <= use_y) + (use_x >= use_y) + (use_x == use_y) +
            (use_x != use_y));
    use_add((use_x < use_a) + (use_x > use_a) + (use_x <= use_a) + (use_x >= use_a) + (use_x == use_a) +
            (use_x != use_a));
    use_add((use_a < use_x) + (use_a > use_x) + (use_a <= use_x) + (use_a >= use_x) + (use_a == use_x) +
            (use_a != use_x));
    use_add((use_x < use_p) + (use_x > use_p) + (use_x <= use_p) + (use_x >= use_p) + (use_x == use_p) +
            (use_x != use_p));
    use_add((use_p < use_x) + (use_p > use_x) + (use_p <= use_x) + (use_p >= use_x) + (use_p == use_x) +
            (use_p != use_x));
    use_add(kairn::abs(use_x).limb[1] + kairn::add_fast(use_x, use_y).limb[1] + kairn::ldexp(use_x, 3).limb[1] +
            kairn::ldexp(use_x, 3000).limb[0] + kairn::ldexp(use_x, -3000).limb[0] + kairn::half(use_x).limb[1]);
    use_add(kairn::to_nearest(use_x) + kairn::to_down(use_x) + kairn::to_up(use_x) + kairn::abs_upper(use_x) +
            E1(use_x).limb[0] + E1(unverified(use_x)).limb[0]);
    use_add(kairn::sign(use_x) + kairn::isfinite(use_x) + kairn::is_normalized(use_x));
    use_add(kairn::finite::add(use_x, use_y).limb[1] + kairn::finite::add(use_x, use_a).limb[1] +
            kairn::finite::add(use_a, use_x).limb[1] + kairn::finite::add(use_x, use_p).limb[1] +
            kairn::finite::add(use_p, use_x).limb[1]);
    use_add(kairn::finite::sub(use_x, use_y).limb[1] + kairn::finite::sub(use_x, use_a).limb[1] +
            kairn::finite::sub(use_a, use_x).limb[1] + kairn::finite::sub(use_x, use_p).limb[1] +
            kairn::finite::sub(use_p, use_x).limb[1]);
    use_add(kairn::finite::mul(use_x, use_y).limb[1] + kairn::finite::mul(use_x, use_a).limb[1] +
            kairn::finite::mul(use_a, use_x).limb[1] + kairn::finite::mul(use_x, use_p).limb[1] +
            kairn::finite::mul(use_p, use_x).limb[1]);
    use_add(kairn::finite::add_fast(use_x, use_y).limb[1] + kairn::finite::ldexp(use_x, 3000).limb[0] +
            kairn::finite::ldexp(use_x, -3000).limb[0]);
    // The marked forms.
    use_add((unverified(use_x) + use_y).limb[1] + (use_x - unverified(use_a)).limb[1] +
            (unverified(use_a) * use_x).limb[1] + (use_p + unverified(use_x)).limb[1] + (-unverified(use_x)).limb[1]);
    use_z += unverified(use_y);
    use_z -= unverified(use_a);
    use_z *= unverified(use_p);
    use_add((unverified(use_x) < use_y) + (use_x > unverified(use_a)) + (unverified(use_a) <= use_x) +
            (use_x >= unverified(use_p)) + (unverified(use_x) == use_y) + (unverified(use_x) != use_a));
    use_add(kairn::abs(unverified(use_x)).limb[1] + kairn::add_fast(unverified(use_x), use_y).limb[1] +
            kairn::ldexp(unverified(use_x), 1).limb[1] + kairn::half(unverified(use_x)).limb[1]);
    use_add(kairn::to_nearest(unverified(use_x)) + kairn::to_down(unverified(use_x)) +
            kairn::to_up(unverified(use_x)) + kairn::abs_upper(unverified(use_x)));
    use_add(kairn::finite::add(unverified(use_x), use_y).limb[1] + kairn::finite::sub(unverified(use_a), use_x).limb[1] +
            kairn::finite::mul(use_x, unverified(use_p)).limb[1] +
            kairn::finite::add_fast(unverified(use_x), use_y).limb[1] + kairn::finite::ldexp(unverified(use_x), 1).limb[1]);

    // Balls of one and two limbs: the constructors, the three states, every form of every operator.
    const UseT use_rad = UseT(0.25);
    B1 use_b1 = B1(use_p, use_rad), use_c1(use_a), use_d1(use_p), use_e1(unverified(use_a)), use_f1(unverified(use_p));
    B1 use_g1(unverified(use_p), use_rad), use_h1 = B1::empty(), use_i1 = B1::whole(), use_j1;
    B2 use_b2 = B2(use_x, use_rad), use_c2(use_a), use_d2(use_x), use_e2(unverified(use_a)), use_f2(unverified(use_x));
    B2 use_g2(unverified(use_x), use_rad), use_h2 = B2::empty(), use_i2 = B2::whole(), use_j2;
    use_add(use_b1.radius() + use_c1.center().limb[0] + use_d1.radius() + use_e1.radius() + use_f1.radius() +
            use_g1.radius() + use_h1.is_empty() + use_i1.is_whole() + use_j1.is_finite());
    use_add(use_b2.radius() + use_c2.center().limb[1] + use_d2.radius() + use_e2.radius() + use_f2.radius() +
            use_g2.radius() + use_h2.is_empty() + use_i2.is_whole() + use_j2.is_finite());
    use_add((use_b1 + use_c1).radius() + (use_b1 + use_a).radius() + (use_a + use_b1).radius() +
            (use_b1 + use_p).radius() + (use_p + use_b1).radius());
    use_add((use_b1 - use_c1).radius() + (use_b1 - use_a).radius() + (use_a - use_b1).radius() +
            (use_b1 - use_p).radius() + (use_p - use_b1).radius());
    use_add((use_b1 * use_c1).radius() + (use_b1 * use_a).radius() + (use_a * use_b1).radius() +
            (use_b1 * use_p).radius() + (use_p * use_b1).radius() + (-use_b1).radius());
    use_add((use_b2 + use_c2).radius() + (use_b2 + use_a).radius() + (use_a + use_b2).radius() +
            (use_b2 + use_x).radius() + (use_x + use_b2).radius());
    use_add((use_b2 - use_c2).radius() + (use_b2 - use_a).radius() + (use_a - use_b2).radius() +
            (use_b2 - use_x).radius() + (use_x - use_b2).radius());
    use_add((use_b2 * use_c2).radius() + (use_b2 * use_a).radius() + (use_a * use_b2).radius() +
            (use_b2 * use_x).radius() + (use_x * use_b2).radius() + (-use_b2).radius());
    use_j1 += use_b1;
    use_j1 += use_a;
    use_j1 += use_p;
    use_j1 -= use_b1;
    use_j1 -= use_a;
    use_j1 -= use_p;
    use_j1 *= use_b1;
    use_j1 *= use_a;
    use_j2 += use_b2;
    use_j2 += use_a;
    use_j2 += use_x;
    use_j2 -= use_b2;
    use_j2 -= use_a;
    use_j2 -= use_x;
    use_j2 *= use_b2;
    use_j2 *= use_a;
    use_add(use_j1.radius() + use_j2.radius());
    // The marked forms.
    use_add((unverified(use_b1) + use_c1).radius() + (use_b1 - unverified(use_a)).radius() +
            (unverified(use_p) * use_b1).radius() + (-unverified(use_b1)).radius());
    use_add((unverified(use_b2) + use_c2).radius() + (use_b2 - unverified(use_x)).radius() +
            (unverified(use_a) * use_b2).radius() + (-unverified(use_b2)).radius());
    use_j1 += unverified(use_b1);
    use_j1 -= unverified(use_a);
    use_j1 *= unverified(use_b1);
    use_j2 += unverified(use_x);
    use_j2 -= unverified(use_b2);
    use_j2 *= unverified(use_a);
    use_add(use_j1.radius() + use_j2.radius());

    // The traits, and the markers of a limb.
    using TE1 = kairn::traits<E1>;
    using TE2 = kairn::traits<E2>;
    using TT = kairn::traits<UseT>;
    use_add(TE1::limbs + TE2::precision + TT::precision + TE2::add.verified + TE2::add_limb.verified +
            TE2::add_fast.verified + TE2::sub.verified + TE2::sub_limb.verified + TE2::mul.verified +
            TE2::mul_limb.verified + TE2::ldexp.verified + TE1::mul.verified);
    use_add(UseT(unverified(use_a)));
    return use_sum;
}

}  // namespace use_test

int main() {
    const kairn::Status use_status = kairn::self_test();
    const double use_total = use_test::use_every_operation<double>(1.5, 0x1p-60) +
                             use_test::use_every_operation<float>(1.5f, 0x1p-30f);
    return use_status.ok() && kairn::environment_ok() && use_total == use_total ? 0 : 1;
}
