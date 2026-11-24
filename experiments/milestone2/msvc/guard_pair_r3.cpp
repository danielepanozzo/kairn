// guard_pair_r3.cpp: rule R3 where MSVC removes the addition of zero of a constructor's guard
// (guard_pair_constructors.cpp). Each form writes a product of the program, a * b, into a position
// whose guard MSVC 19.52 at /O2 was seen to remove (limb 1 and the radius of Ball(Constant) and of
// Ball(c, r) with c and r in one struct, the limbs of from_limbs of Expansion, Ball and Interval of
// two limbs, the running sum of Accumulator::from_state), and limb 0 for comparison, then adds an
// operand that cancels it; the same form is computed on the product rounded first (through a
// volatile, in a function that is not inlined). The results are compared limb by limb, a zero as a
// zero of either sign; differences of the sign of a zero alone are counted apart. The cases of
// tests/api/boundary.cpp: factors in [1, 2) (scaled by a power of two for a low limb), the
// cancelling operand -p * (1 + k u'), k = 0..6.
//   guard_pair_r3 [CASES]   (200 000 by default) exit 1 if a form of Kairn differs; the control,
//                           without Kairn, only reports
// Built against the headers (cl /std:c++20 /O2 /arch:AVX2 /DNDEBUG /I include), every form must
// agree; against the copy without the guard (python3 unguard.py include DIR, then /I DIR) a
// compiler that fuses across statements makes some differ. See README.md beside this file.
#include <kairn/accumulator.hpp>
#include <kairn/ball_vector.hpp>
#include <kairn/kairn.hpp>

#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <type_traits>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#else
#define NOINLINE __attribute__((noinline))
#endif

template <class T> using E2 = kairn::Expansion<T, 2>;
template <class T> using B2 = kairn::Ball<T, 2>;
template <class T> using I2 = kairn::Interval<T, 2>;
template <class T> using A2 = kairn::Accumulator<T, 2>;
template <class T> using V2 = kairn::BallVector<T, 2, 2>;

template <class T> struct Scale;
template <> struct Scale<double> { static constexpr double low = 0x1p-30, tiny = 0x1p-40, step = 0x1p-30; };
template <> struct Scale<float> { static constexpr float low = 0x1p-14f, tiny = 0x1p-40f, step = 0x1p-14f; };

template <class T> E2<T> e2(T h, T l) { E2<T> c; c.limb[0] = h; c.limb[1] = l; return c; }
template <class T> struct CR { E2<T> c; T r; };

// The cancelling operands of a case: for a product p0 of factors in [1, 2) (a leading limb) and p1
// of scaled factors (a low limb under a leading 1).
template <class T> struct Ops {
    B2<T> y0, y1;
    E2<T> x0, x1;
    I2<T> i0, i1;
    T m0, m1;
    V2<T> v;
};
template <class T> Ops<T> ops(T p0, T p1, T near) {
    const T tiny = Scale<T>::tiny;
    return {B2<T>(e2<T>(-p0 * near, T(0)), tiny), B2<T>(e2<T>(T(-1), -p1 * near), tiny),
            e2<T>(-p0 * near, T(0)), e2<T>(T(-1), -p1 * near),
            I2<T>(e2<T>(-p0 * near, T(0))), I2<T>(e2<T>(T(-1), -p1 * near)),
            -p0 * near, -p1 * near,
            V2<T>(std::array<E2<T>, 2>{e2<T>(T(-1), -p1 * near), e2<T>(-p1 * near, T(0))}, tiny)};
}

template <class T> NOINLINE T rounded(T a, T b) {
    volatile T p = a * b;
    return p;
}

// Each form twice: NAME_in with the product a * b written where X stands, NAME_ref with the rounded
// product p passed as a (b is then 1 and unused).
#define PAIR(NAME, R, BODY)                                                                          \
    template <class T> NOINLINE R NAME##_in(const Ops<T>& o, T a, T b) { BODY((a * b)) }             \
    template <class T> NOINLINE R NAME##_ref(const Ops<T>& o, T a, [[maybe_unused]] T b) { BODY((a)) }

// Limb 1 and the radius (scaled factors), limb 0 (factors in [1, 2)).
#define F_CONST_L1R(X) E2<T> c; c.limb[0] = T(1); c.limb[1] = X; return B2<T>(kairn::Constant<E2<T>>{c, X, false}) + o.y1;
#define F_CONST_L0(X) E2<T> c; c.limb[0] = X; c.limb[1] = T(0); return B2<T>(kairn::Constant<E2<T>>{c, Scale<T>::tiny, false}) + o.y0;
#define F_CR_L1R(X) CR<T> s; s.c.limb[0] = T(1); s.c.limb[1] = X; s.r = X; return B2<T>(s.c, s.r) + o.y1;
#define F_CR_L0(X) CR<T> s; s.c.limb[0] = X; s.c.limb[1] = T(0); s.r = Scale<T>::tiny; return B2<T>(s.c, s.r) + o.y0;
#define F_BLIMBS_L1R(X) const T l[3] = {T(1), X, X}; return B2<T>::from_limbs(l) + o.y1;
#define F_BLIMBS_L0(X) const T l[3] = {X, T(0), Scale<T>::tiny}; return B2<T>::from_limbs(l) + o.y0;
#define F_ELIMBS_L1(X) const T l[2] = {T(1), X}; return E2<T>::from_limbs(l) + o.x1;
#define F_ELIMBS_L0(X) const T l[2] = {X, T(0)}; return E2<T>::from_limbs(l) + o.x0;
#define F_ILIMBS_L1(X) const T l[4] = {T(1), X, T(1), X}; return I2<T>::from_limbs(l) + o.i1;
#define F_ILIMBS_L0(X) const T l[4] = {X, T(0), X, T(0)}; return I2<T>::from_limbs(l) + o.i0;
#define F_ACC_L1(X) A2<T> acc = A2<T>::from_state(e2<T>(T(1), X), T(1), 1); acc.add(T(-1)); acc.add(o.m1); return acc;
#define F_ACC_L0(X) A2<T> acc = A2<T>::from_state(e2<T>(X, T(0)), X, 1); acc.add(o.m0); return acc;
#define F_BV2(X) std::array<E2<T>, 2> c{e2<T>(T(1), X), e2<T>(X, T(0))}; return V2<T>(c, X) + o.v;
// The same three constructors, the struct written by the caller and read by a function that is
// not inlined (the shape of guard_pair_constructors.cpp), the result then added.
template <class T> NOINLINE B2<T> const_callee(const kairn::Constant<E2<T>>& q, const B2<T>& y) { return B2<T>(q) + y; }
template <class T> NOINLINE B2<T> cr_callee(const CR<T>& s, const B2<T>& y) { return B2<T>(s.c, s.r) + y; }
template <class T> NOINLINE A2<T> acc_callee(const E2<T>& s, T m, T x) { A2<T> acc = A2<T>::from_state(s, m, 1); acc.add(x); return acc; }
#define F_CONST_MEM(X) const kairn::Constant<E2<T>> q{e2<T>(T(1), X), X, false}; return const_callee<T>(q, o.y1);
#define F_CR_MEM(X) CR<T> s; s.c = e2<T>(T(1), X); s.r = X; return cr_callee<T>(s, o.y1);
#define F_ACC_MEM(X) const E2<T> s = e2<T>(X, T(0)); return acc_callee<T>(s, X, o.m0);
// The control, without Kairn: the program's own product and sum across statements, which a compiler
// that contracts across statements fuses.
#define F_CONTROL(X) const T s = X; return s + o.m0;

PAIR(const_l1r, B2<T>, F_CONST_L1R)
PAIR(const_l0, B2<T>, F_CONST_L0)
PAIR(cr_l1r, B2<T>, F_CR_L1R)
PAIR(cr_l0, B2<T>, F_CR_L0)
PAIR(blimbs_l1r, B2<T>, F_BLIMBS_L1R)
PAIR(blimbs_l0, B2<T>, F_BLIMBS_L0)
PAIR(elimbs_l1, E2<T>, F_ELIMBS_L1)
PAIR(elimbs_l0, E2<T>, F_ELIMBS_L0)
PAIR(ilimbs_l1, I2<T>, F_ILIMBS_L1)
PAIR(ilimbs_l0, I2<T>, F_ILIMBS_L0)
PAIR(acc_l1, A2<T>, F_ACC_L1)
PAIR(acc_l0, A2<T>, F_ACC_L0)
PAIR(bv2, V2<T>, F_BV2)
PAIR(const_mem, B2<T>, F_CONST_MEM)
PAIR(cr_mem, B2<T>, F_CR_MEM)
PAIR(acc_mem, A2<T>, F_ACC_MEM)
PAIR(control, T, F_CONTROL)

// The limbs of each result, in a list.
template <class T> struct Limbs { T v[8]; int n = 0; void put(T x) { v[n++] = x; } };
template <class T> void put(Limbs<T>& l, T x) { l.put(x); }
template <class T, int K> void put(Limbs<T>& l, const kairn::Expansion<T, K>& e) { for (int j = 0; j < K; ++j) l.put(e.limb[j]); }
template <class T, int K> void put(Limbs<T>& l, const kairn::Ball<T, K>& b) { put(l, b.center()); l.put(b.radius()); }
template <class T, int K> void put(Limbs<T>& l, const kairn::Interval<T, K>& x) { put(l, x.lower()); put(l, x.upper()); }
template <class T, int K> void put(Limbs<T>& l, const kairn::Accumulator<T, K>& a) {
    put(l, a.running_sum());
    l.put(a.magnitudes());
    l.put(T(a.count()));
}
template <class T, int K, std::size_t N> void put(Limbs<T>& l, const kairn::BallVector<T, K, N>& v) {
    for (std::size_t i = 0; i < N; ++i) put(l, v.center(i));
    l.put(v.radius());
}
template <class T> auto bits(T x) { return std::bit_cast<std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>>(x); }

struct Count { long differ = 0, zero_sign_only = 0; };
// 0: the same bits; 1: the same values but the sign of a zero; 2: different.
template <class T, class X> int compare(const X& u, const X& w) {
    Limbs<T> a, b;
    put(a, u);
    put(b, w);
    int worst = 0;
    for (int i = 0; i < a.n; ++i) {
        const T x = a.v[i], y = b.v[i];
        if (bits(x) == bits(y) || (x != x && y != y)) continue;
        worst = (x == 0 && y == 0) ? (worst > 1 ? worst : 1) : 2;
        if (worst == 2) break;
    }
    return worst;
}

std::uint64_t state = 0x9e3779b97f4a7c15u;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T> T unit() {
    if constexpr (sizeof(T) == 8) return 1.0 + double(next() >> 11) * 0x1p-53;
    else return 1.0f + float(next() >> 40) * 0x1p-24f;
}

template <class T> int run(const char* type, long cases) {
    enum { n_forms = 17 };
    const char* names[n_forms] = {"Ball2(Constant{(1, a*b), a*b}) + Y", "Ball2(Constant{(a*b, 0), r}) + Y",
                                  "Ball2(s.c = (1, a*b), s.r = a*b) + Y", "Ball2(s.c = (a*b, 0), s.r) + Y",
                                  "Ball2::from_limbs({1, a*b, a*b}) + Y", "Ball2::from_limbs({a*b, 0, r}) + Y",
                                  "E2::from_limbs({1, a*b}) + x", "E2::from_limbs({a*b, 0}) + x",
                                  "I2::from_limbs({1, a*b, 1, a*b}) + X", "I2::from_limbs({a*b, 0, a*b, 0}) + X",
                                  "from_state((1, a*b), 1).add(-1).add(x)", "from_state((a*b, 0), a*b).add(x)",
                                  "BallVector2{(1, a*b), (a*b, 0)}, a*b) + V", "callee(Constant{(1, a*b), a*b})",
                                  "callee(CR{(1, a*b), a*b})", "callee(from_state((a*b, 0), a*b))",
                                  "control: s = a*b; s + x (no Kairn)"};
    Count c[n_forms];
    for (long i = 0; i < cases; ++i) {
        const T a0 = unit<T>(), b0 = unit<T>();
        const T a1 = unit<T>() * Scale<T>::low, b1 = unit<T>() * Scale<T>::low;
        const T p0 = rounded(a0, b0), p1 = rounded(a1, b1);
        const T near = T(1) + T(i % 7) * Scale<T>::step;
        const Ops<T> o = ops(p0, p1, near);
        int r[n_forms];
        int f = 0;
        r[f++] = compare<T>(const_l1r_in(o, a1, b1), const_l1r_ref(o, p1, T(1)));
        r[f++] = compare<T>(const_l0_in(o, a0, b0), const_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(cr_l1r_in(o, a1, b1), cr_l1r_ref(o, p1, T(1)));
        r[f++] = compare<T>(cr_l0_in(o, a0, b0), cr_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(blimbs_l1r_in(o, a1, b1), blimbs_l1r_ref(o, p1, T(1)));
        r[f++] = compare<T>(blimbs_l0_in(o, a0, b0), blimbs_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(elimbs_l1_in(o, a1, b1), elimbs_l1_ref(o, p1, T(1)));
        r[f++] = compare<T>(elimbs_l0_in(o, a0, b0), elimbs_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(ilimbs_l1_in(o, a1, b1), ilimbs_l1_ref(o, p1, T(1)));
        r[f++] = compare<T>(ilimbs_l0_in(o, a0, b0), ilimbs_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(acc_l1_in(o, a1, b1), acc_l1_ref(o, p1, T(1)));
        r[f++] = compare<T>(acc_l0_in(o, a0, b0), acc_l0_ref(o, p0, T(1)));
        r[f++] = compare<T>(bv2_in(o, a1, b1), bv2_ref(o, p1, T(1)));
        r[f++] = compare<T>(const_mem_in(o, a1, b1), const_mem_ref(o, p1, T(1)));
        r[f++] = compare<T>(cr_mem_in(o, a1, b1), cr_mem_ref(o, p1, T(1)));
        r[f++] = compare<T>(acc_mem_in(o, a0, b0), acc_mem_ref(o, p0, T(1)));
        r[f++] = compare<T>(control_in(o, a0, b0), control_ref(o, p0, T(1)));
        for (int k = 0; k < n_forms; ++k) {
            c[k].differ += r[k] == 2;
            c[k].zero_sign_only += r[k] == 1;
        }
    }
    int bad = 0;
    for (int k = 0; k < n_forms; ++k) {
        std::printf("  %-6s %-44s differs in %6ld of %ld (the sign of a zero alone in %ld)\n", type, names[k],
                    c[k].differ, cases, c[k].zero_sign_only);
        if (k != n_forms - 1 && c[k].differ) ++bad;
    }
    return bad;
}

int main(int argc, char** argv) {
    const long cases = argc > 1 ? std::atol(argv[1]) : 200000;
    int bad = run<double>("double", cases);
    bad += run<float>("float", cases);
    std::printf("%d forms of Kairn differ%s\n", bad, bad ? "" : " (none)");
    return bad ? 1 : 0;
}
