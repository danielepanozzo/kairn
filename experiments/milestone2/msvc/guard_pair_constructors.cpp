// guard_pair_constructors.cpp: every constructor of Kairn that guards its operands, its operands
// every one -0, read from one struct by reference in the members' natural order (center then
// radius, lower then upper bound, running sum then magnitudes, the limbs of an array), in a
// function the compiler does not inline. Prints the sign of every limb of the result, for double
// and float. cl /std:c++20 /O2 /arch:AVX2 /DNDEBUG /I include (from the root of the repository),
// MSVC 19.52, /fp:precise or /fp:contract: "a -0 kept" on 8 lines (see README.md); /fp:strict,
// /Od, Apple clang 21 at -O2: "ok" on every line.
#include <kairn/accumulator.hpp>
#include <kairn/ball_vector.hpp>
#include <kairn/kairn.hpp>

#include <array>
#include <cmath>
#include <cstdio>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

template <class T> using E1 = kairn::Expansion<T, 1>;
template <class T> using E2 = kairn::Expansion<T, 2>;

template <class T, int K> struct CR { kairn::Expansion<T, K> c; T r; };
template <class T> struct LH1 { T lo, hi; };
template <class T> struct LH2 { E2<T> lo, hi; };
template <class T, int K> struct SA { kairn::Expansion<T, K> s; T a; };
template <class T, int N> struct L { T l[N]; };
template <class T, int K> struct AV { std::array<kairn::Expansion<T, K>, 4> c; T r; };

template <class T, int K> NOINLINE kairn::Ball<T, K> ball_cr(const CR<T, K>& x) { return kairn::Ball<T, K>(x.c, x.r); }
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_point(const CR<T, K>& x) { return kairn::Ball<T, K>(x.c); }
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_constant(const CR<T, K>& x) {
    return kairn::Ball<T, K>(kairn::Constant<kairn::Expansion<T, K>>{x.c, x.r, false});
}
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_point_t(const LH1<T>& x) { return kairn::Ball<T, K>(x.lo); }
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_from_bounds(const LH1<T>& x) { return kairn::Ball<T, K>::from_bounds(x.lo, x.hi); }
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_from_interval(const LH1<T>& x) { return kairn::Ball<T, K>::from_interval(x.lo, x.hi); }
template <class T, int K> NOINLINE kairn::Ball<T, K> ball_from_limbs(const L<T, K + 1>& x) { return kairn::Ball<T, K>::from_limbs(x.l); }
template <class T, int K> NOINLINE kairn::Interval<T, K> interval_lh1(const LH1<T>& x) { return kairn::Interval<T, K>(x.lo, x.hi); }
template <class T, int K> NOINLINE kairn::Interval<T, K> interval_point_t(const LH1<T>& x) { return kairn::Interval<T, K>(x.lo); }
template <class T, int K> NOINLINE kairn::Interval<T, K> interval_from_bounds_t(const LH1<T>& x) { return kairn::Interval<T, K>::from_bounds(x.lo, x.hi); }
template <class T> NOINLINE kairn::Interval<T, 2> interval_lh2(const LH2<T>& x) { return kairn::Interval<T, 2>(x.lo, x.hi); }
template <class T> NOINLINE kairn::Interval<T, 2> interval_point2(const LH2<T>& x) { return kairn::Interval<T, 2>(x.lo); }
template <class T> NOINLINE kairn::Interval<T, 2> interval_from_bounds2(const LH2<T>& x) { return kairn::Interval<T, 2>::from_bounds(x.lo, x.hi); }
template <class T, int K> NOINLINE kairn::Interval<T, K> interval_from_limbs(const L<T, 2 * K>& x) { return kairn::Interval<T, K>::from_limbs(x.l); }
template <class T> NOINLINE E2<T> expansion_from_limbs(const L<T, 2>& x) { return E2<T>::from_limbs(x.l); }
template <class T, int K> NOINLINE kairn::Accumulator<T, K> acc_from_state(const SA<T, K>& x) { return kairn::Accumulator<T, K>::from_state(x.s, x.a, 1); }
template <class T, int K> NOINLINE kairn::BallVector<T, K, 4> ball_vector(const AV<T, K>& x) { return kairn::BallVector<T, K, 4>(x.c, x.r); }

template <class T> char sign(T x) { return x != 0 ? 'x' : (std::signbit(x) ? '-' : '+'); }
template <class T, int K> void put(const kairn::Expansion<T, K>& e, char*& o) { for (int j = 0; j < K; ++j) *o++ = sign(e.limb[j]); }
template <class T, int K> void put(const kairn::Ball<T, K>& b, char*& o) { put(b.center(), o); *o++ = '|'; *o++ = sign(b.radius()); }
template <class T, int K> void put(const kairn::Interval<T, K>& x, char*& o) { put(x.lower(), o); *o++ = '|'; put(x.upper(), o); }
template <class T, int K> void put(const kairn::Accumulator<T, K>& a, char*& o) { put(a.running_sum(), o); *o++ = '|'; *o++ = sign(a.magnitudes()); }
template <class T, int K, std::size_t N> void put(const kairn::BallVector<T, K, N>& v, char*& o) {
    for (std::size_t i = 0; i < N; ++i) { put(v.center(i), o); *o++ = ' '; }
    *o++ = '|'; *o++ = sign(v.radius());
}
int wrong = 0;
template <class X> void row(const char* type, const char* what, const X& x) {
    char buf[64], *o = buf;
    put(x, o);
    *o = 0;
    bool minus = false;
    for (char* p = buf; *p; ++p) minus = minus || *p == '-';
    wrong += minus;
    std::printf("%-6s %-40s %-18s %s\n", type, what, buf, minus ? "a -0 kept" : "ok");
}

template <class T> void run(const char* type) {
    volatile T v_zero = 0;
    const T m = -T(v_zero);
    E1<T> m1;
    m1.limb[0] = m;
    E2<T> m2;
    m2.limb[0] = m;
    m2.limb[1] = m;
    const CR<T, 1> cr1{m1, m};
    const CR<T, 2> cr2{m2, m};
    const LH1<T> lh{m, m};
    const LH2<T> lh2{m2, m2};
    const L<T, 2> l2{{m, m}};
    const L<T, 3> l3{{m, m, m}};
    const L<T, 4> l4{{m, m, m, m}};
    const SA<T, 1> sa1{m1, m};
    const SA<T, 2> sa2{m2, m};
    const AV<T, 1> av1{{m1, m1, m1, m1}, m};
    const AV<T, 2> av2{{m2, m2, m2, m2}, m};
    row(type, "Ball<T, 1>(c, r)", ball_cr<T, 1>(cr1));
    row(type, "Ball<T, 1>(c)", ball_point<T, 1>(cr1));
    row(type, "Ball<T, 1>(Constant{c, r})", ball_constant<T, 1>(cr1));
    row(type, "Ball<T, 1>(a), a of T", ball_point_t<T, 1>(lh));
    row(type, "Ball<T, 1>::from_bounds(lo, hi)", ball_from_bounds<T, 1>(lh));
    row(type, "Ball<T, 1>::from_interval(lo, hi)", ball_from_interval<T, 1>(lh));
    row(type, "Ball<T, 1>::from_limbs", ball_from_limbs<T, 1>(l2));
    row(type, "Ball<T, 2>(c, r)", ball_cr<T, 2>(cr2));
    row(type, "Ball<T, 2>(c)", ball_point<T, 2>(cr2));
    row(type, "Ball<T, 2>(Constant{c, r})", ball_constant<T, 2>(cr2));
    row(type, "Ball<T, 2>(a), a of T", ball_point_t<T, 2>(lh));
    row(type, "Ball<T, 2>::from_bounds(lo, hi) of T", ball_from_bounds<T, 2>(lh));
    row(type, "Ball<T, 2>::from_interval(lo, hi) of T", ball_from_interval<T, 2>(lh));
    row(type, "Ball<T, 2>::from_limbs", ball_from_limbs<T, 2>(l3));
    row(type, "Interval<T, 1>(lo, hi)", interval_lh1<T, 1>(lh));
    row(type, "Interval<T, 1>(a)", interval_point_t<T, 1>(lh));
    row(type, "Interval<T, 1>::from_bounds(lo, hi)", interval_from_bounds_t<T, 1>(lh));
    row(type, "Interval<T, 1>::from_limbs", interval_from_limbs<T, 1>(l2));
    row(type, "Interval<T, 2>(lo, hi) of T", interval_lh1<T, 2>(lh));
    row(type, "Interval<T, 2>(a), a of T", interval_point_t<T, 2>(lh));
    row(type, "Interval<T, 2>::from_bounds(lo, hi) of T", interval_from_bounds_t<T, 2>(lh));
    row(type, "Interval<T, 2>(lo, hi) of two limbs", interval_lh2<T>(lh2));
    row(type, "Interval<T, 2>(a) of two limbs", interval_point2<T>(lh2));
    row(type, "Interval<T, 2>::from_bounds of two limbs", interval_from_bounds2<T>(lh2));
    row(type, "Interval<T, 2>::from_limbs", interval_from_limbs<T, 2>(l4));
    row(type, "Expansion<T, 2>::from_limbs (make_2)", expansion_from_limbs<T>(l2));
    row(type, "Accumulator<T, 1>::from_state", acc_from_state<T, 1>(sa1));
    row(type, "Accumulator<T, 2>::from_state", acc_from_state<T, 2>(sa2));
    row(type, "BallVector<T, 1, 4>(c, r)", ball_vector<T, 1>(av1));
    row(type, "BallVector<T, 2, 4>(c, r)", ball_vector<T, 2>(av2));
}

int main() {
    run<double>("double");
    run<float>("float");
    std::printf("%d results kept a -0\n", wrong);
    return 0;
}
