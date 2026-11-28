// EXPERIMENTAL, NOT VERIFIED: no bound stated in this file is proved. Kairn's rule is that every
// bound it ships is machine-checked; by the owner's decision recorded on 2026-11-28 (the decisions
// log, docs/developer/design/phase0/decisions.md) this header is an exception, shipped without
// proofs so that clients can experiment while the proofs are worked on. What protects a user
// meanwhile: this banner, the opt-in below, and the exact checks of its tests (label experimental),
// which are tests, not proofs. Its interface may change or disappear in any version. GCC and Clang
// only: MSVC is refused, and no Windows build was ever tested. A file that includes it defines
// KAIRN_EXPERIMENTAL_UNVERIFIED first, so that the choice is written in the client's code
// (docs/concepts/experimental.md).
#if !defined(KAIRN_EXPERIMENTAL_UNVERIFIED)
#error "kairn/experimental/upward2_arrays.hpp is EXPERIMENTAL and NOT VERIFIED (no bound in it is proved): define KAIRN_EXPERIMENTAL_UNVERIFIED before including it to accept that (docs/concepts/experimental.md)"
#endif

/// @file
/// EXPERIMENTAL, NOT VERIFIED, opt-in: no bound stated here is proved (the banner above). The
/// functions on arrays of the two-limb interval rounded upward (experiments/upward2/README.md):
/// element by element sum, difference and product of intervals held as four plain arrays (uh, ul,
/// nh, nl). Requires the options of docs/concepts/upward.md (GCC and Clang -frounding-math); each
/// function holds its own scope of the mode upward (the register only, as the functions on arrays
/// of kairn/upward.hpp), so it may be called where the mode is to nearest.
///
/// Vectorized across elements: on AVX2 four elements per register, elsewhere two (NEON, SSE2, or
/// the two numbers of the fallback); the upper pairs (uh, ul) and the negated lower pairs (nh, nl)
/// in registers of their own, each lane one element, the kernels those of upward2.hpp on such
/// registers. A remainder, and an element whose leading products are not finite or reach MAX (the
/// special values), go through the type's operators one element at a time.
#pragma once

#include <cstddef>

#include "upward2.hpp"

namespace kairn::experimental::upward2 {

/// Four plain arrays of n intervals, element i (uh[i] + ul[i] >= hi, nh[i] + nl[i] >= -lo), each
/// element a canonical state. Owns nothing.
template <class T>
struct View {
    T* uh;
    T* ul;
    T* nh;
    T* nl;
    std::size_t size;
};

namespace detail {
namespace {

#if KAIRN_UPWARD2_AVX2
using AP = V4;
inline constexpr std::size_t kW = 4;
KAIRN_FORCEINLINE AP ld(const double* p) noexcept { return _mm256_loadu_pd(p); }
KAIRN_FORCEINLINE void st(double* p, AP v) noexcept { _mm256_storeu_pd(p, v); }
KAIRN_FORCEINLINE AP aset(double a) noexcept { return _mm256_set1_pd(a); }
#else
using AP = V;
inline constexpr std::size_t kW = 2;
KAIRN_FORCEINLINE AP ld(const double* p) noexcept { return vload(p); }
KAIRN_FORCEINLINE void st(double* p, AP v) noexcept { vstore(p, v); }
KAIRN_FORCEINLINE AP aset(double a) noexcept { return vset(a); }
#endif

// One bound of kW sums: add_r's steps (and reasons) on registers of elements.
KAIRN_FORCEINLINE void sum_bound(AP xh, AP xl, AP yh, AP yl, AP& zh, AP& zl) noexcept {
    AP s, e, t, f, v, g;
    two_sum(xh, yh, s, e);
    two_sum_nonpos(xl, yl, t, f);
    two_sum(s, add(e, t), v, g);
    two_sum(v, add(f, g), zh, zl);
    zh = blend(ispinf(s), aset(kInf), zh);
    zl = clear(big(zh), zl);
}

// One interval of the arrays through the type's operators (the remainder and the special values).
KAIRN_FORCEINLINE Interval element(const View<const double>& x, std::size_t i) noexcept {
    const double p[4] = {x.uh[i], x.nh[i], x.ul[i], x.nl[i]};
    return Interval::from_limbs(p);
}
KAIRN_FORCEINLINE void put(const View<double>& z, std::size_t i, const Interval& v) noexcept {
    double q[4];
    v.to_limbs(q);
    z.uh[i] = q[0];
    z.nh[i] = q[1];
    z.ul[i] = q[2];
    z.nl[i] = q[3];
}

struct Pack {
    AP uh, ul, nh, nl;
};
KAIRN_FORCEINLINE Pack load(const View<const double>& x, std::size_t i) noexcept {
    return Pack{ld(x.uh + i), ld(x.ul + i), ld(x.nh + i), ld(x.nl + i)};
}
KAIRN_FORCEINLINE void store(const View<double>& z, std::size_t i, Pack p) noexcept {
    bar(p.uh);
    bar(p.ul);
    bar(p.nh);
    bar(p.nl);
    st(z.uh + i, p.uh);
    st(z.ul + i, p.ul);
    st(z.nh + i, p.nh);
    st(z.nl + i, p.nl);
}
KAIRN_FORCEINLINE void barriers(Pack& x, Pack& y) noexcept {
    pin(x.uh);
    pin(x.ul);
    pin(x.nh);
    pin(x.nl);
    bar(y.uh);
    bar(y.ul);
    bar(y.nh);
    bar(y.nl);
}

// The product of kW elements: mul_sel2's two candidates per bound (its argument, element by
// element), with x = (xu, xn), y = (yu, yn) in registers of their own:
//   upper:  max((ma ? xu : xn) * (ma ? -yn : yn), (mb ? xn : xu) * (mb ? -yu : yu)),
//           ma = (b <= 0 and c > 0), mb = (a >= 0 and d < 0)
//   -lower: max((ma' ? xu : xn) * (ma' ? -yu : yu), (mb' ? xn : xu) * (mb' ? -yn : yn)),
//           ma' = (b <= 0 and d < 0), mb' = (a >= 0 and c > 0).
// special is set when a leading product is not finite or reaches MAX: the caller then computes
// these elements one at a time with the type's product.
KAIRN_FORCEINLINE Pack mul_pack(const Pack& x, const Pack& y, bool& special) noexcept {
    const auto b0 = le0(x.uh), a0 = le0(x.nh), cp = lt0(y.nh), dn = lt0(y.uh);
    const auto ma = mand(b0, cp), mb = mand(a0, dn), ma2 = mand(b0, dn), mb2 = mand(a0, cp);
    AP q1h = flip(ma, y.nh), q1l = flip(ma, y.nl), q2h = flip(mb, y.uh), q2l = flip(mb, y.ul);
    AP q3h = flip(ma2, y.uh), q3l = flip(ma2, y.ul), q4h = flip(mb2, y.nh), q4l = flip(mb2, y.nl);
    bar(q1h);
    bar(q1l);
    bar(q2h);
    bar(q2l);
    bar(q3h);
    bar(q3l);
    bar(q4h);
    bar(q4l);
    AP p1, p2, p3, p4, ah, al, bh, bl, ch, cl, dh, dl;
    pair_mul(blend(ma, x.uh, x.nh), blend(ma, x.ul, x.nl), q1h, q1l, p1, ah, al);
    pair_mul(blend(mb, x.nh, x.uh), blend(mb, x.nl, x.ul), q2h, q2l, p2, bh, bl);
    pair_mul(blend(ma2, x.uh, x.nh), blend(ma2, x.ul, x.nl), q3h, q3l, p3, ch, cl);
    pair_mul(blend(mb2, x.nh, x.uh), blend(mb2, x.nl, x.ul), q4h, q4l, p4, dh, dl);
    special = any(mor(mor(big(p1), big(p2)), mor(big(p3), big(p4))));
    Pack z;
    lexmax(ah, al, bh, bl, z.uh, z.ul);
    lexmax(ch, cl, dh, dl, z.nh, z.nl);
    return z;
}

enum class ArrayOp { add, sub, mul };
template <ArrayOp Op>
KAIRN_FORCEINLINE void apply(const View<double>& z, const View<const double>& x, const View<const double>& y) noexcept {
    // The length is read before the scope, whose barriers clobber memory: after them GCC no longer
    // knows a length it could see, and warns (-Warray-bounds) of the loads of the vector loop on a
    // shorter array, a loop that never runs there.
    const std::size_t n = z.size;
    ::kairn::upward::detail::RegisterScope scope;
    std::size_t i = 0;
    for (; i + kW <= n; i += kW) {
        Pack a = load(x, i), b = load(y, i);
        barriers(a, b);
        Pack c;
        if constexpr (Op == ArrayOp::mul) {
            bool special = false;
            c = mul_pack(a, b, special);
            if (special) [[unlikely]] {
                for (std::size_t k = i; k < i + kW; ++k) put(z, k, element(x, k) * element(y, k));
                continue;
            }
        } else if constexpr (Op == ArrayOp::add) {
            sum_bound(a.uh, a.ul, b.uh, b.ul, c.uh, c.ul);
            sum_bound(a.nh, a.nl, b.nh, b.nl, c.nh, c.nl);
        } else {   // x - y: the pairs of y exchanged
            sum_bound(a.uh, a.ul, b.nh, b.nl, c.uh, c.ul);
            sum_bound(a.nh, a.nl, b.uh, b.ul, c.nh, c.nl);
        }
        store(z, i, c);
    }
    for (; i < n; ++i) {
        const Interval a = element(x, i), b = element(y, i);
        put(z, i, Op == ArrayOp::add ? a + b : Op == ArrayOp::sub ? a - b : a * b);
    }
}

}  // namespace
}  // namespace detail

namespace {
/// z = x + y, x - y, x * y element by element (views of the same length; z may be x or y, or
/// arrays that overlap neither). Each holds its own scope of the mode upward.
[[maybe_unused]] void add(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::add>(z, x, y);
}
[[maybe_unused]] void sub(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::sub>(z, x, y);
}
[[maybe_unused]] void mul(View<double> z, View<const double> x, View<const double> y) noexcept {
    detail::apply<detail::ArrayOp::mul>(z, x, y);
}
}  // namespace

}  // namespace kairn::experimental::upward2
