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
#include <kairn/packed.hpp>
#include <kairn/soa.hpp>

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
    // The scaling by a power of two, the sign predicates and the ball of a constant.
    use_add(kairn::ldexp(use_b1, 3).radius() + kairn::ldexp(use_b2, -3000).radius() + kairn::half(use_b1).radius() +
            kairn::half(use_b2).radius() + kairn::ldexp(unverified(use_b2), 2).radius() +
            kairn::half(unverified(use_b1)).radius());
    use_add(use_b1.certainly_positive() + use_b1.certainly_negative() + use_b1.certainly_zero() +
            use_b2.certainly_positive() + use_b2.certainly_negative() + use_b2.certainly_zero());
    const B1 use_k1(kairn::rational<E1>(1, 3));
    const B2 use_k2(kairn::integer<E2>(7));
    use_add(use_k1.radius() + use_k2.center().limb[0]);

    // Intervals of one and two limbs: the constructors, the states, every operator and function,
    // with and without the marker; and the functions of a Ball of the interface the two share.
    using I1 = kairn::Interval<UseT, 1>;
    using I2 = kairn::Interval<UseT, 2>;
    const I1 use_v1(use_a, use_a + 1), use_v1p(use_a), use_v1e{E1(use_b), E1(use_a)}, use_v1m(unverified(use_b), use_a);
    const I2 use_v2(use_x, use_x + UseT(1)), use_v2p(use_a), use_v2t(use_b, use_a), use_v2m(unverified(use_x), use_x);
    use_add((use_v1 + use_v1p).lower().limb[0] + (use_v1 - use_v1e).upper().limb[0] + (use_v1 * use_v1m).lower().limb[0] +
            (-use_v1).upper().limb[0] + (unverified(use_v1) + use_v1).lower().limb[0] + (-unverified(use_v1)).lower().limb[0]);
    use_add((use_v2 + use_v2p).lower().limb[1] + (use_v2 - use_v2t).upper().limb[1] + (use_v2 * use_v2m).lower().limb[1] +
            (-use_v2).upper().limb[1] + (use_v2 * unverified(use_v2)).lower().limb[1]);
    I1 use_v1a = use_v1;
    use_v1a += use_v1p;
    use_v1a -= unverified(use_v1p);
    use_v1a *= use_v1e;
    I2 use_v2a = use_v2;
    use_v2a += unverified(use_v2p);
    use_v2a -= use_v2p;
    use_v2a *= use_v2t;
    use_add(use_v1a.lower().limb[0] + use_v2a.upper().limb[1] + I1::empty().lower().limb[0] + I2::whole().upper().limb[1] +
            I1().lower().limb[0]);
    use_add(use_v1.hull(use_v1e).lower().limb[0] + use_v1.intersection(unverified(use_v1e)).upper().limb[0] +
            use_v2.hull(unverified(use_v2t)).lower().limb[1] + use_v2.intersection(use_v2t).upper().limb[1]);
    const kairn::Split<I1> use_halves = use_v1.split();
    use_add(use_v1.midpoint().limb[0] + use_v1.radius() + use_halves.left.upper().limb[0] + use_halves.right.lower().limb[0] +
            use_v1.template lower_as<UseT>() + use_v2.template upper_as<UseT>() + use_v2.template lower_as<UseT>());
    const B1 use_ib(use_v1), use_ibm(unverified(use_v1)), use_nb(use_b2), use_nbm(unverified(use_b2));
    const I1 use_bi(use_b1), use_bim(unverified(use_b1));
    const B2 use_fi = B2::from_interval(use_a, use_a + 1), use_fim = B2::from_interval(unverified(use_b), use_a);
    use_add(use_ib.radius() + use_ibm.radius() + use_nb.radius() + use_nbm.radius() + use_bi.lower().limb[0] +
            use_bim.upper().limb[0] + use_fi.radius() + use_fim.center().limb[1]);
    use_add(use_b1.template lower_as<UseT>() + use_b1.template upper_as<UseT>() + use_b1.lower().limb[0] +
            use_b1.upper().limb[0] + use_b2.template lower_as<UseT>() + use_b2.template upper_as<UseT>() +
            use_b2.midpoint().limb[0] + use_b1.midpoint().limb[0]);

    // The enclosure interface of stage B2 (headers-pred): the predicates, the member and subset
    // tests, the three-valued comparisons and the relations of IEEE 1788, of both types and both
    // numbers of limbs, with and without the marker; the set operations of a ball; the midpoint,
    // radius, split and conversions of two limbs.
    use_add(use_v1.is_empty() + use_v1.is_whole() + use_v2.is_empty() + use_v2.is_whole() + use_v1.certainly_positive() +
            use_v1.certainly_negative() + use_v1.certainly_zero() + use_v2.certainly_positive() +
            use_v2.certainly_negative() + use_v2.certainly_zero());
    use_add(use_v1.contains(use_a) + use_v1.contains(E1(use_a)) + use_v1.contains(unverified(use_a)) +
            use_v1.contains(unverified(E1(use_a))) + use_v1.contains(use_v1e) + use_v1.contains(unverified(use_v1e)) +
            use_v2.contains(use_a) + use_v2.contains(use_x) + use_v2.contains(use_v2t) + use_v2.contains(unverified(use_x)));
    use_add(use_b1.contains(use_a) + use_b1.contains(E1(use_a)) + use_b1.contains(use_b1) +
            use_b1.contains(unverified(use_b1)) + use_b2.contains(use_a) + use_b2.contains(use_x) +
            use_b2.contains(use_b2) + use_b2.contains(unverified(use_a)));
    use_add(int(kairn::member(use_a, use_v1)) + int(kairn::member(use_x, use_v2)) + int(kairn::member(use_a, use_b1)) +
            int(kairn::member(use_x, use_b2)) + int(kairn::member(unverified(use_a), use_b2)) +
            int(kairn::member(E1(use_a), unverified(use_v1))));
    use_add(int(kairn::less(use_v1, use_v1e)) + int(kairn::less_equal(use_v2, use_v2t)) +
            int(kairn::equal(use_v1, unverified(use_v1e))) + int(kairn::greater(use_v2, use_v2t)) +
            int(kairn::greater_equal(unverified(use_v1), use_v1e)) + int(kairn::not_equal(use_v2, use_v2t)));
    use_add(int(kairn::less(use_b1, use_k1)) + int(kairn::less_equal(use_b2, use_k2)) +
            int(kairn::equal(use_b1, unverified(use_k1))) + int(kairn::greater(use_b2, use_k2)) +
            int(kairn::greater_equal(use_b1, use_k1)) + int(kairn::not_equal(unverified(use_b2), use_k2)));
    use_add(kairn::certainly(kairn::less(use_v1, use_v1)) + kairn::possibly(kairn::equal(use_b2, use_b2)));
    use_add(kairn::ieee1788::equal(use_v1, use_v1e) + kairn::ieee1788::subset(use_v2, use_v2t) +
            kairn::ieee1788::interior(use_v1, unverified(use_v1e)) + kairn::ieee1788::disjoint(unverified(use_v2), use_v2t));
    const kairn::Split<B1> use_bs1 = use_b1.split();
    const kairn::Split<B2> use_bs2 = use_b2.split();
    use_add(use_b1.hull(use_k1).radius() + use_b1.intersection(unverified(use_k1)).radius() +
            use_b2.hull(unverified(use_k2)).radius() + use_b2.intersection(use_k2).radius() + use_bs1.left.radius() +
            use_bs2.right.radius() + use_b1.mid_rad().radius + use_b2.mid_rad().midpoint.limb[1]);
    const kairn::MidRad<UseT, 2> use_mr2 = use_v2.mid_rad();
    const kairn::Split<I2> use_halves2 = use_v2.split();
    use_add(use_v2.midpoint().limb[1] + use_v2.radius() + use_mr2.radius + use_v1.mid_rad().radius +
            use_halves2.left.upper().limb[0]);
    const B2 use_ib2(use_v2), use_ib2m(unverified(use_v2));
    const I2 use_bi2(use_b2), use_bi2m(unverified(use_b2));
    const B1 use_fi1 = B1::from_interval(use_a, use_a + 1), use_fi1m = B1::from_interval(unverified(use_b), use_a);
    use_add(use_ib2.radius() + use_ib2m.radius() + use_bi2.lower().limb[1] + use_bi2m.upper().limb[0] +
            use_b2.lower().limb[0] + use_b2.upper().limb[1] + use_fi1.radius() + use_fi1m.center().limb[0]);

    // The building blocks on T, each with and without the marker, and the conversion of a sum.
    const kairn::SumAndError<UseT> use_sum2 = kairn::two_sum(use_a, use_b);
    const auto [use_fs, use_fe] = kairn::fast_two_sum(use_a, use_b);
    const kairn::ProductAndError<UseT> use_prod = kairn::two_prod(use_a, use_b);
    use_add(use_sum2.sum + use_sum2.error + use_fs + use_fe + use_prod.product + use_prod.error +
            E2(use_sum2).limb[1]);
    use_add(kairn::next_up(use_a) + kairn::next_down(use_a) + kairn::radd(use_a, use_b) + kairn::rmul(use_a, use_b) +
            kairn::add_down(use_a, use_b) + kairn::add_up(use_a, use_b) + kairn::sub_down(use_a, use_b) +
            kairn::sub_up(use_a, use_b) + kairn::mul_down(use_a, use_b) + kairn::mul_up(use_a, use_b));
    use_add(kairn::two_sum(unverified(use_a), use_b).sum + kairn::fast_two_sum(use_a, unverified(use_b)).sum +
            kairn::two_prod(unverified(use_a), use_b).error + kairn::next_up(unverified(use_a)) +
            kairn::next_down(unverified(use_a)) + kairn::radd(unverified(use_a), use_b) +
            kairn::rmul(use_a, unverified(use_b)) + kairn::add_down(unverified(use_a), use_b) +
            kairn::add_up(unverified(use_a), use_b) + kairn::sub_down(unverified(use_a), use_b) +
            kairn::sub_up(unverified(use_a), use_b) + kairn::mul_down(unverified(use_a), use_b) +
            kairn::mul_up(unverified(use_a), use_b));

    // The traits, and the markers of a limb.
    using TE1 = kairn::traits<E1>;
    using TE2 = kairn::traits<E2>;
    using TT = kairn::traits<UseT>;
    use_add(TE1::limbs + TE2::precision + TT::precision + TE2::add.verified + TE2::add_limb.verified +
            TE2::add_fast.verified + TE2::sub.verified + TE2::sub_limb.verified + TE2::mul.verified +
            TE2::mul_limb.verified + TE2::ldexp.verified + TE1::mul.verified);
    use_add(UseT(unverified(use_a)));

    // Packed (kairn/packed.hpp) and the containers (kairn/soa.hpp): every operation once.
    {
        using P1 = kairn::Packed<UseT, 1>;
        using P2 = kairn::Packed<UseT, 2>;
        constexpr int use_lanes = P2::lanes;
        UseT use_h[2 * use_lanes] = {}, use_k[2 * use_lanes] = {};
        for (int use_i = 0; use_i < 2 * use_lanes; ++use_i) use_h[use_i] = use_a + UseT(use_i);
        P2 use_px = P2::load(use_h, use_k), use_py = P2::load_unchecked(use_h, use_k);
        P2 use_pz = P2::load_partial(use_h, use_k, use_lanes - 1, use_x);
        const P1 use_pa = P1::load(use_h), use_pb = P1::load_partial(use_h, 1, use_p), use_pc = P1::load_unchecked(use_k);
        use_px = P2::from_limbs(use_px.limb[0], use_px.limb[1]) + P2::from_limbs_unchecked(use_py.limb[0], use_py.limb[1]);
        use_pz = use_px + use_py + use_pa + (use_pa + use_px) - use_py - use_pa + (use_pa - use_px) * use_py * use_pa;
        use_pz += use_py;
        use_pz += use_pa;
        use_pz -= use_py;
        use_pz -= use_pa;
        use_pz *= use_py;
        use_pz *= use_pa;
        use_pz = (use_pa * use_pz) + (-use_pz) + kairn::abs(use_pz) + kairn::add_fast(use_pz, use_px) +
                 kairn::ldexp(use_pz, 3) + kairn::half(use_pz) + P2(use_pa) + P2::broadcast(use_x);
        use_pz = kairn::finite::add(use_px, use_py) + kairn::finite::add(use_px, use_pa) +
                 kairn::finite::add(use_pa, use_px) + kairn::finite::sub(use_px, use_py) +
                 kairn::finite::sub(use_px, use_pa) + kairn::finite::sub(use_pa, use_px) +
                 kairn::finite::mul(use_px, use_py) + kairn::finite::mul(use_px, use_pa) +
                 kairn::finite::mul(use_pa, use_px) + kairn::finite::add_fast(use_px, use_py) +
                 kairn::finite::ldexp(use_px, -2) + use_pz;
        P1 use_pq = -use_pa;
        use_pq = -use_pq;
        use_pq = kairn::abs(use_pq);
        use_pq = kairn::to_nearest(use_pq);
        use_pq = kairn::to_down(use_pq);
        use_pq = kairn::to_up(use_pq);
        use_pq = kairn::abs_upper(use_pq);
        use_pq = kairn::select(use_pq < use_pc, use_pq, kairn::to_nearest(use_px));
        use_pq = kairn::select(use_pq < use_pc, kairn::to_down(use_px), kairn::to_up(use_px));
        use_pq = kairn::select(use_pq < use_pc, kairn::abs_upper(use_px), P1(use_px));
        const kairn::PackedMask<UseT> use_mask = (use_px < use_py) | (use_px > use_py) | (use_px <= use_py) |
                                                 (use_px >= use_py) | (use_px == use_py) | (use_px != use_py) |
                                                 (use_px < use_pa) | (use_px > use_pa) | (use_px <= use_pa) |
                                                 (use_px >= use_pa) | (use_px == use_pa) | (use_px != use_pa) |
                                                 (use_pa < use_px) | (use_pa > use_px) | (use_pa <= use_px) |
                                                 (use_pa >= use_px) | (use_pa == use_px) | (use_pa != use_px) |
                                                 (use_pa < use_pb) | (use_pa > use_pb) | (use_pa <= use_pb) |
                                                 (use_pa >= use_pb) | (use_pa == use_pb) | !(use_pa != use_pb);
        use_pz = kairn::select(use_mask & use_mask, use_pz, use_px);
        use_pz.set_lane(0, use_x);
        use_pz.store(use_h, use_k);
        use_pz.store_partial(use_h, use_k, 1);
        use_pq.store(use_h);
        use_pq.store_partial(use_h, 1);
        use_add(use_pz.lane(0).limb[1] + use_pq.lane(0).limb[0] + kairn::any(use_mask) + kairn::all(use_mask) +
                use_mask.lane(0));
        kairn::SoA<UseT, 2> use_soa(std::size_t(2 * use_lanes), use_x), use_copy = use_soa;
        use_copy.resize(std::size_t(2 * use_lanes + 1));
        const kairn::SoAView<UseT, 2> use_view = use_soa;
        const kairn::SoAView<const UseT, 2> use_read = use_view;
        const kairn::SoAView<UseT, 1> use_plain(use_h, std::size_t(2 * use_lanes));
        use_view[0] = use_y;
        use_view[1] = use_view[0];
        use_view.set(2, use_read.get(1));
        use_view.store(0, use_read.load(1));
        use_view.store_partial(1, use_read.load_partial(0, 1, use_x), 1);
        use_plain[0] = E1(use_read.get(0));
        use_copy.swap(use_soa);
        use_add(E2(use_read[1]).limb[0] + use_read.subview(1, 1).get(0).limb[0] + double(use_read.size()) +
                use_plain.get(0).limb[0] + use_copy.get(0).limb[0] + use_soa.limb(0)[0] + use_soa.view().limb(1)[0] +
                E2(use_copy[0]).limb[0] + use_copy.load(0).lane(0).limb[0] + double(use_soa.empty()));
    }

    // Constants from fractions: rational and integer, in constant evaluation and at run time, and
    // the checker.
    constexpr kairn::Constant<E2> use_third = kairn::rational<E2>(1, 3);
    const kairn::Constant<E1> use_int = kairn::integer<E1>(static_cast<long long>(use_a));
    const kairn::Constant<UseT> use_tenth = kairn::rational<UseT>(-1, 10);
    use_add(use_third.value.limb[1] + use_third.error + use_third.exact + use_int.value.limb[0] + use_tenth.value);
    use_add(kairn::is_rational_result(use_int, static_cast<long long>(use_a), 1) +
            kairn::is_rational_result(use_third, 1, 3));
    return use_sum;
}

}  // namespace use_test

int main() {
    const kairn::Status use_status = kairn::self_test();
    const double use_total = use_test::use_every_operation<double>(1.5, 0x1p-60) +
                             use_test::use_every_operation<float>(1.5f, 0x1p-30f);
    return use_status.ok() && kairn::environment_ok() && use_total == use_total ? 0 : 1;
}

// With KAIRN_TEST_DEFINITIONS (and KAIRN_ENCLOSURE_CODE_EXTERNAL), the definitions of the
// operations of Ball, which a program compiles in one of its translation units.
#if defined(KAIRN_TEST_DEFINITIONS)
#include <kairn/definitions.hpp>
#endif
