// The timed functions of the functions on arrays (kairn/batch.hpp) and of the accumulator
// (kairn/accumulator.hpp) (bench/m2_data.hpp; bench/README.md, "Milestone 2", third part). Compiled with
// the flags of packed code (-mavx2 -mfma on x86-64, bench/CMakeLists.txt), as a client's translation
// unit that wants the fast order is: the default order of batch.hpp is the lane order of that unit's
// form of Packed (4 lanes of double, 8 of float with AVX2; 2 and 4 with NEON).
//
// Backends:
//   m2a, m2af   the functions on arrays, double and float limbs; KIND tp (512 elements, in L1), llc
//               (128 Ki elements of double, 256 Ki of float: 1 to 6 MB, in the last-level cache of
//               both machines) and mem (4 Mi and 8 Mi: 32 to 192 MB, in no cache); time per element,
//               per term for the convolution
//   m2k         short arrays, double: one call per array of n elements, n = 1 to 1024, 256 calls on
//               overlapping windows of one array in L1 (KIND tp, independent calls; KIND lat, each
//               call's window chosen from the previous result, so that the calls wait for each
//               other); time per call. The cost of the check of the environment at entry is this
//               program's time against that of kairn-bench-m2-nocheck-LEVEL, the same source
//               compiled against a copy of the headers in which the check is compiled out
//               (bench/entry_check.py)
//   m2c         the accumulator, double: per element over the arrays of m2a (tp, llc); the merge and
//               the results of 256 accumulators (KIND tp); time per element or per call
// Kernels (one limb unless named 2):
//   sum1, sum2, sumf2 (sum_fast), dot1, dot2; sum2z, dot2z: the two-limb sum and dot product of the
//   one-limb data, the second limbs zero (an accurate sum of doubles with Kairn); add1, add2; scale1,
//   scale2 (by a of T); axpy1, axpy2 (a of T), axpy22 (a of two limbs); norm1, norm2 (norm_upper);
//   conv1_N, conv2_N: the product of two polynomials of N coefficients (N = 16, 64, 512)
// Variants:
//   op        the public function, default order
//   seq       the public function with kairn::sequential
//   kairn     the generated loop that op calls, called directly on the limbs: the reference, and the
//             public function without its check of the environment
//   kseq      the generated sequential loop (the loop of seq; for a map, the loop of one lane)
//   bare      the generated loop on stored arrays, the same steps without the guards of rule R3
//             (sum_1, dot_1, add_1, scale_2, axpy_1, conv_1, ...; acc_mul_1, acc_mul_2): what the
//             guards cost
//   plain     the same loop on plain T, element after element (one chain for a reduction; for dot1
//             and conv1 with a fused multiply-add, as Kairn's step)
//   plainw    the same on plain T in the lane order of the default (W chains)
//   textbook  what a numerical programmer writes instead: for one limb the compensated sum and dot
//             product of Ogita, Rump and Oishi (Sum2, Dot2); for two limbs double-word arithmetic
//             written out from the listings of Joldes, Muller and Popescu (props.hpp: AccurateDWPlusDW,
//             SloppyDWPlusDW for sum_fast, DWTimesFP3, DWTimesDW3), element after element
// Every function is checked before it is timed (check() below): against its reference byte for byte
// (op and bare against kairn, seq and plain against kseq, plainw against kairn), and the references
// and the textbook loops against the exact result (m2_exact.hpp) within their stated bounds.
#include <kairn/accumulator.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>
#include <kairn/soa.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "bench_util.hpp"
#include "m2_data.hpp"
#include "m2_exact.hpp"
#include "props.hpp"

// What the rows, the checks and the data share.
namespace kairn_bench::m2a {

enum Out : int { O_C1 = 0, O_C2, O_Z1, O_Z2, O_ZC1, O_ZC2, O_ACC, O_OUT, O_SHORT };

struct Meta {
    const char* name;
    const char* ref;
    int size;     // the set
    int conv_n;   // the polynomials' coefficients, for a convolution
};

}  // namespace kairn_bench::m2a

namespace {

using namespace kairn_bench::m2a;
namespace kg = kairn::gen;
namespace tb = kairn_bench::textbook;
using kairn_bench::m2::Entry;
template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using V1 = kairn::SoAView<const T, 1>;
template <class T>
using V2 = kairn::SoAView<const T, 2>;
template <class T>
using W1 = kairn::SoAView<T, 1>;
template <class T>
using W2 = kairn::SoAView<T, 2>;

#define KB_SI KAIRN_GEN_FORCEINLINE

// The loop of the default order: packed where Packed has lanes, sequential otherwise (as batch.hpp).
#if KAIRN_DETAIL_BATCH_PACKED
#define KB_FAST(NAME) kg::NAME##_packed
#else
#define KB_FAST(NAME) kg::NAME##_seq
#endif

template <class T>
constexpr int W = kairn::Packed<T, 1>::lanes;

// The two-limb number of a normalized pair (from_limbs: each limb guarded).
template <class T>
E2<T> two(T h, T l) {
    const T limbs[2] = {h, l};
    return E2<T>::from_limbs(limbs);
}

// --- The arrays ---------------------------------------------------------------------------------

template <class T>
constexpr std::size_t size_of(int s) {
    return s == 0 ? 512 : s == 1 ? (sizeof(T) == 8 ? std::size_t(1) << 17 : std::size_t(1) << 18)
                                 : (sizeof(T) == 8 ? std::size_t(1) << 22 : std::size_t(1) << 23);
}

// The exact sums of one set's data, for the checks.
struct Sums {
    double s1 = 0, a1 = 0;   // sum and sum of magnitudes of x0
    double s2 = 0, a2 = 0;   // of x0 + x1 (a2: of |x0| + |x1|)
    double d1 = 0, p1 = 0;   // dot of x0, y0 and the sum of |x0 y0|
    double d2 = 0, p2 = 0;   // dot of (x0 + x1), (y0 + y1) and the sum of |x0 y0| + ...
    kairn_bench::exact::Exact es1, es2, ed1, ed2;
};

template <class T>
struct Set {
    std::size_t n = 0;
    kairn::SoA<T, 2> x, y, z;   // two-limb operands (their leading limbs: the one-limb data) and result
    kairn::SoA<T, 2> zc;        // the coefficients of a convolution, 2 * 512
    std::vector<T> zero;        // second limbs that are zero
    T a = T(1);                 // a scalar near 1
    E2<T> a2;                   // a two-limb scalar near 1
    T cout[4] = {0, 0, 0, 0};   // the result of a reduction, or the state of an accumulator
    Sums sums;
    // Accumulators for the merge and the results (256 of them, of one and two limbs).
    std::vector<kairn::Accumulator<T, 1>> acc1;
    std::vector<kairn::Accumulator<T, 2>> acc2;
    std::vector<T> out;         // 3 * 256 values written by the results of the accumulators
    // Short arrays: windows x0 + j, j < 256, of n <= 1024 elements, and the outputs.
    std::vector<T> s0, s1, t0, t1, sout;
};

template <class T>
Set<T>* g_sets[3] = {nullptr, nullptr, nullptr};
template <class T>
Set<T>& set_of(int s) {
    return *g_sets<T>[s];
}

template <class T>
struct P {
    const T *x0, *x1, *y0, *y1, *zr;
    T *z0, *z1, *c0, *c1;
    std::size_t n;
    explicit P(Set<T>& d)
        : x0(d.x.view().limb(0)), x1(d.x.view().limb(1)), y0(d.y.view().limb(0)), y1(d.y.view().limb(1)),
          zr(d.zero.data()), z0(d.z.view().limb(0)), z1(d.z.view().limb(1)), c0(d.zc.view().limb(0)),
          c1(d.zc.view().limb(1)), n(d.n) {}
};

template <class T, int K>
KB_SI void put(Set<T>& d, const kairn::Reduction<E1<T>>& r) {
    d.cout[0] = r.value.limb[0];
    d.cout[3] = T(r.finite);
}
template <class T>
KB_SI void put2(Set<T>& d, const kairn::Reduction<E2<T>>& r) {
    d.cout[0] = r.value.limb[0];
    d.cout[1] = r.value.limb[1];
    d.cout[3] = T(r.finite);
}

// --- Sums ---------------------------------------------------------------------------------------

template <class T> KB_SI void sum1_op(Set<T>& d) { put<T, 1>(d, kairn::sum(V1<T>(P<T>(d).x0, d.n))); }
template <class T> KB_SI void sum1_seq(Set<T>& d) { put<T, 1>(d, kairn::sum(kairn::sequential, V1<T>(P<T>(d).x0, d.n))); }
template <class T> KB_SI void sum1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(sum_1_entry)(r.x0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void sum1_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::sum_1_entry_seq(r.x0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void sum1_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(sum_1)(r.x0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void sum1_plain(Set<T>& d) {
    const P<T> r(d);
    T s = 0;
    for (std::size_t i = 0; i < r.n; ++i) s = s + r.x0[i];
    d.cout[0] = s;
    d.cout[3] = T(1);
}
template <class T> KB_SI void sum1_plainw(Set<T>& d) {
    const P<T> r(d);
    T s[W<T>];
    for (int l = 0; l < W<T>; ++l) s[l] = 0;
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) s[l] = s[l] + r.x0[i + l];
    T t = s[0];
    for (int l = 1; l < W<T>; ++l) t = t + s[l];
    for (; i < r.n; ++i) t = t + r.x0[i];
    d.cout[0] = t;
    d.cout[3] = T(1);
}
// Sum2 of Ogita, Rump and Oishi (2005): a cascade of TwoSum, the errors summed in T.
template <class T> KB_SI void sum1_textbook(Set<T>& d) {
    const P<T> r(d);
    T p = r.x0[0], s = 0;
    for (std::size_t i = 1; i < r.n; ++i) {
        T q;
        tb::two_sum(p, r.x0[i], p, q);
        s = s + q;
    }
    d.cout[0] = p + s;
    d.cout[3] = T(1);
}

#define KB_SUM2(NAME, LOOP, BARE, Y1)                                                              \
    template <class T> KB_SI void NAME##_op(Set<T>& d) {                                           \
        const P<T> r(d);                                                                           \
        put2(d, kairn::LOOP(V2<T>(r.x0, Y1, r.n)));                                                \
    }                                                                                              \
    template <class T> KB_SI void NAME##_seq(Set<T>& d) {                                          \
        const P<T> r(d);                                                                           \
        put2(d, kairn::LOOP(kairn::sequential, V2<T>(r.x0, Y1, r.n)));                             \
    }                                                                                              \
    template <class T> KB_SI void NAME##_kairn(Set<T>& d) {                                        \
        const P<T> r(d);                                                                           \
        bool f = false;                                                                            \
        KB_FAST(BARE##_entry)(r.x0, Y1, r.n, d.cout[0], d.cout[1], f);                             \
        d.cout[3] = T(f);                                                                          \
    }                                                                                              \
    template <class T> KB_SI void NAME##_kseq(Set<T>& d) {                                         \
        const P<T> r(d);                                                                           \
        bool f = false;                                                                            \
        kg::BARE##_entry_seq(r.x0, Y1, r.n, d.cout[0], d.cout[1], f);                              \
        d.cout[3] = T(f);                                                                          \
    }                                                                                              \
    template <class T> KB_SI void NAME##_bare(Set<T>& d) {                                         \
        const P<T> r(d);                                                                           \
        bool f = false;                                                                            \
        KB_FAST(BARE)(r.x0, Y1, r.n, d.cout[0], d.cout[1], f);                                     \
        d.cout[3] = T(f);                                                                          \
    }
KB_SUM2(sum2, sum, sum_2, r.x1)
KB_SUM2(sumf2, sum_fast, sum_fast_2, r.x1)
KB_SUM2(sum2z, sum, sum_2, r.zr)

// Double-word sums written out: AccurateDWPlusDW (sum2) and SloppyDWPlusDW (sumf2), one chain.
template <class T> KB_SI void sum2_textbook(Set<T>& d) {
    const P<T> r(d);
    T sh = 0, sl = 0;
    for (std::size_t i = 0; i < r.n; ++i) tb::accurate_dw_plus_dw(sh, sl, r.x0[i], r.x1[i], sh, sl);
    d.cout[0] = sh;
    d.cout[1] = sl;
    d.cout[3] = T(1);
}
template <class T> KB_SI void sumf2_textbook(Set<T>& d) {
    const P<T> r(d);
    T sh = 0, sl = 0;
    for (std::size_t i = 0; i < r.n; ++i) tb::sloppy_dw_plus_dw(sh, sl, r.x0[i], r.x1[i], sh, sl);
    d.cout[0] = sh;
    d.cout[1] = sl;
    d.cout[3] = T(1);
}

// --- Dot products -------------------------------------------------------------------------------

template <class T> KB_SI void dot1_op(Set<T>& d) {
    const P<T> r(d);
    put<T, 1>(d, kairn::dot(V1<T>(r.x0, r.n), V1<T>(r.y0, r.n)));
}
template <class T> KB_SI void dot1_seq(Set<T>& d) {
    const P<T> r(d);
    put<T, 1>(d, kairn::dot(kairn::sequential, V1<T>(r.x0, r.n), V1<T>(r.y0, r.n)));
}
template <class T> KB_SI void dot1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(dot_1_entry)(r.x0, r.y0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void dot1_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::dot_1_entry_seq(r.x0, r.y0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void dot1_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(dot_1)(r.x0, r.y0, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void dot1_plain(Set<T>& d) {
    const P<T> r(d);
    T s = 0;
    for (std::size_t i = 0; i < r.n; ++i) s = kg::fma_rn(r.x0[i], r.y0[i], s);
    d.cout[0] = s;
    d.cout[3] = T(1);
}
template <class T> KB_SI void dot1_plainw(Set<T>& d) {
    const P<T> r(d);
    T s[W<T>];
    for (int l = 0; l < W<T>; ++l) s[l] = 0;
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) s[l] = kg::fma_rn(r.x0[i + l], r.y0[i + l], s[l]);
    T t = s[0];
    for (int l = 1; l < W<T>; ++l) t = t + s[l];
    for (; i < r.n; ++i) t = kg::fma_rn(r.x0[i], r.y0[i], t);
    d.cout[0] = t;
    d.cout[3] = T(1);
}
// Dot2 of Ogita, Rump and Oishi (2005): TwoProduct (by an FMA) and a cascade of TwoSum.
template <class T> KB_SI void dot1_textbook(Set<T>& d) {
    const P<T> r(d);
    T p, s;
    tb::fast_two_mult(r.x0[0], r.y0[0], p, s);
    for (std::size_t i = 1; i < r.n; ++i) {
        T h, e, q;
        tb::fast_two_mult(r.x0[i], r.y0[i], h, e);
        tb::two_sum(p, h, p, q);
        s = s + (q + e);
    }
    d.cout[0] = p + s;
    d.cout[3] = T(1);
}

#define KB_DOT2(NAME, X1, Y1)                                                                      \
    template <class T> KB_SI void NAME##_op(Set<T>& d) {                                           \
        const P<T> r(d);                                                                           \
        put2(d, kairn::dot(V2<T>(r.x0, X1, r.n), V2<T>(r.y0, Y1, r.n)));                           \
    }                                                                                              \
    template <class T> KB_SI void NAME##_seq(Set<T>& d) {                                          \
        const P<T> r(d);                                                                           \
        put2(d, kairn::dot(kairn::sequential, V2<T>(r.x0, X1, r.n), V2<T>(r.y0, Y1, r.n)));        \
    }                                                                                              \
    template <class T> KB_SI void NAME##_kairn(Set<T>& d) {                                        \
        const P<T> r(d);                                                                           \
        bool f = false;                                                                            \
        KB_FAST(dot_2)(r.x0, X1, r.y0, Y1, r.n, d.cout[0], d.cout[1], f);                          \
        d.cout[3] = T(f);                                                                          \
    }                                                                                              \
    template <class T> KB_SI void NAME##_kseq(Set<T>& d) {                                         \
        const P<T> r(d);                                                                           \
        bool f = false;                                                                            \
        kg::dot_2_seq(r.x0, X1, r.y0, Y1, r.n, d.cout[0], d.cout[1], f);                           \
        d.cout[3] = T(f);                                                                          \
    }
KB_DOT2(dot2, r.x1, r.y1)
KB_DOT2(dot2z, r.zr, r.zr)
// The double-word dot product written out: DWTimesDW3, then AccurateDWPlusDW, one chain.
template <class T> KB_SI void dot2_textbook(Set<T>& d) {
    const P<T> r(d);
    T sh = 0, sl = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T ph, pl;
        tb::dw_times_dw3(r.x0[i], r.x1[i], r.y0[i], r.y1[i], ph, pl);
        tb::accurate_dw_plus_dw(sh, sl, ph, pl, sh, sl);
    }
    d.cout[0] = sh;
    d.cout[1] = sl;
    d.cout[3] = T(1);
}

// --- Maps ---------------------------------------------------------------------------------------

template <class T> KB_SI void add1_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::add(V1<T>(r.x0, r.n), V1<T>(r.y0, r.n), W1<T>(r.z0, r.n)));
}
template <class T> KB_SI void add1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(add_1_entry)(r.x0, r.y0, r.n, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add1_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::add_1_entry_seq(r.x0, r.y0, r.n, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add1_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(add_1)(r.x0, r.y0, r.n, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add1_plain(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) r.z0[i] = r.x0[i] + r.y0[i];
    d.cout[3] = T(1);
}

template <class T> KB_SI void add2_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::add(V2<T>(r.x0, r.x1, r.n), V2<T>(r.y0, r.y1, r.n), W2<T>(r.z0, r.z1, r.n)));
}
template <class T> KB_SI void add2_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(add_2_entry)(r.x0, r.x1, r.y0, r.y1, r.n, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add2_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::add_2_entry_seq(r.x0, r.x1, r.y0, r.y1, r.n, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add2_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(add_2)(r.x0, r.x1, r.y0, r.y1, r.n, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void add2_textbook(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) tb::accurate_dw_plus_dw(r.x0[i], r.x1[i], r.y0[i], r.y1[i], r.z0[i], r.z1[i]);
    d.cout[3] = T(1);
}

template <class T> KB_SI void scale1_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::scale(V1<T>(r.x0, r.n), d.a, W1<T>(r.z0, r.n)));
}
template <class T> KB_SI void scale1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(scale_1)(r.x0, r.n, d.a, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void scale1_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::scale_1_seq(r.x0, r.n, d.a, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void scale1_plain(Set<T>& d) {
    const P<T> r(d);
    const T a = d.a;
    for (std::size_t i = 0; i < r.n; ++i) r.z0[i] = r.x0[i] * a;
    d.cout[3] = T(1);
}

template <class T> KB_SI void scale2_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::scale(V2<T>(r.x0, r.x1, r.n), d.a, W2<T>(r.z0, r.z1, r.n)));
}
template <class T> KB_SI void scale2_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(scale_2_entry)(r.x0, r.x1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void scale2_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::scale_2_entry_seq(r.x0, r.x1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void scale2_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(scale_2)(r.x0, r.x1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void scale2_textbook(Set<T>& d) {
    const P<T> r(d);
    const T a = d.a;
    for (std::size_t i = 0; i < r.n; ++i) tb::dw_times_fp3(r.x0[i], r.x1[i], a, r.z0[i], r.z1[i]);
    d.cout[3] = T(1);
}

template <class T> KB_SI void axpy1_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::axpy(d.a, V1<T>(r.x0, r.n), V1<T>(r.y0, r.n), W1<T>(r.z0, r.n)));
}
template <class T> KB_SI void axpy1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_1_entry)(r.x0, r.y0, r.n, d.a, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy1_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::axpy_1_entry_seq(r.x0, r.y0, r.n, d.a, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy1_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_1)(r.x0, r.y0, r.n, d.a, r.z0, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy1_plain(Set<T>& d) {
    const P<T> r(d);
    const T a = d.a;
    for (std::size_t i = 0; i < r.n; ++i) r.z0[i] = a * r.x0[i] + r.y0[i];
    d.cout[3] = T(1);
}

template <class T> KB_SI void axpy2_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::axpy(d.a, V2<T>(r.x0, r.x1, r.n), V2<T>(r.y0, r.y1, r.n), W2<T>(r.z0, r.z1, r.n)));
}
template <class T> KB_SI void axpy2_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_2_1_entry)(r.x0, r.x1, r.y0, r.y1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy2_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::axpy_2_1_entry_seq(r.x0, r.x1, r.y0, r.y1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy2_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_2_1)(r.x0, r.x1, r.y0, r.y1, r.n, d.a, r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy2_textbook(Set<T>& d) {
    const P<T> r(d);
    const T a = d.a;
    for (std::size_t i = 0; i < r.n; ++i) {
        T ph, pl;
        tb::dw_times_fp3(r.x0[i], r.x1[i], a, ph, pl);
        tb::accurate_dw_plus_dw(ph, pl, r.y0[i], r.y1[i], r.z0[i], r.z1[i]);
    }
    d.cout[3] = T(1);
}

template <class T> KB_SI void axpy22_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::axpy(d.a2, V2<T>(r.x0, r.x1, r.n), V2<T>(r.y0, r.y1, r.n), W2<T>(r.z0, r.z1, r.n)));
}
template <class T> KB_SI void axpy22_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_2_entry)(r.x0, r.x1, r.y0, r.y1, r.n, d.a2.limb[0], d.a2.limb[1], r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy22_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::axpy_2_entry_seq(r.x0, r.x1, r.y0, r.y1, r.n, d.a2.limb[0], d.a2.limb[1], r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy22_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(axpy_2)(r.x0, r.x1, r.y0, r.y1, r.n, d.a2.limb[0], d.a2.limb[1], r.z0, r.z1, f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void axpy22_textbook(Set<T>& d) {
    const P<T> r(d);
    const T a0 = d.a2.limb[0], a1 = d.a2.limb[1];
    for (std::size_t i = 0; i < r.n; ++i) {
        T ph, pl;
        tb::dw_times_dw3(r.x0[i], r.x1[i], a0, a1, ph, pl);
        tb::accurate_dw_plus_dw(ph, pl, r.y0[i], r.y1[i], r.z0[i], r.z1[i]);
    }
    d.cout[3] = T(1);
}

// --- norm_upper ---------------------------------------------------------------------------------

template <class T> KB_SI void norm1_op(Set<T>& d) {
    const kairn::Reduction<T> r = kairn::norm_upper(V1<T>(P<T>(d).x0, d.n));
    d.cout[0] = r.value;
    d.cout[3] = T(r.finite);
}
template <class T> KB_SI void norm1_kairn(Set<T>& d) {
    bool f = false;
    KB_FAST(norm_upper_1)(P<T>(d).x0, d.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void norm1_kseq(Set<T>& d) {
    bool f = false;
    kg::norm_upper_1_seq(P<T>(d).x0, d.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void norm1_plain(Set<T>& d) {
    const P<T> r(d);
    T m = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        const T v = std::fabs(r.x0[i]);
        m = v > m ? v : m;
    }
    d.cout[0] = m;
    d.cout[3] = T(1);
}
template <class T> KB_SI void norm2_op(Set<T>& d) {
    const P<T> r(d);
    const kairn::Reduction<T> v = kairn::norm_upper(V2<T>(r.x0, r.x1, r.n));
    d.cout[0] = v.value;
    d.cout[3] = T(v.finite);
}
template <class T> KB_SI void norm2_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    KB_FAST(norm_upper_2)(r.x0, r.x1, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}
template <class T> KB_SI void norm2_kseq(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::norm_upper_2_seq(r.x0, r.x1, r.n, d.cout[0], f);
    d.cout[3] = T(f);
}

// --- Convolutions -------------------------------------------------------------------------------
// The product of the polynomials x[0, N) and y[0, N), 2N - 1 coefficients, on the arrays in L1.

template <class T, std::size_t N> KB_SI void conv1_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::conv(V1<T>(r.x0, N), V1<T>(r.y0, N), W1<T>(r.c0, 2 * N - 1)));
}
template <class T, std::size_t N> KB_SI void conv1_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::conv_1_entry_seq(r.x0, N, r.y0, N, r.c0, f);
    d.cout[3] = T(f);
}
template <class T, std::size_t N> KB_SI void conv1_bare(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::conv_1_seq(r.x0, N, r.y0, N, r.c0, f);
    d.cout[3] = T(f);
}
// The coefficients as dot products with a fused multiply-add, in increasing i, as conv_1 computes them.
template <class T, std::size_t N> KB_SI void conv1_plain(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t j = 0; j < 2 * N - 1; ++j) {
        const std::size_t lo = j < N ? 0 : j - N + 1, hi = j < N ? j : N - 1;
        T s = 0;
        for (std::size_t i = lo; i <= hi; ++i) s = kg::fma_rn(r.x0[i], r.y0[j - i], s);
        r.c0[j] = s;
    }
    d.cout[3] = T(1);
}
template <class T, std::size_t N> KB_SI void conv2_op(Set<T>& d) {
    const P<T> r(d);
    d.cout[3] = T(kairn::conv(V2<T>(r.x0, r.x1, N), V2<T>(r.y0, r.y1, N), W2<T>(r.c0, r.c1, 2 * N - 1)));
}
template <class T, std::size_t N> KB_SI void conv2_kairn(Set<T>& d) {
    const P<T> r(d);
    bool f = false;
    kg::conv_2_seq(r.x0, r.x1, N, r.y0, r.y1, N, r.c0, r.c1, f);
    d.cout[3] = T(f);
}
template <class T, std::size_t N> KB_SI void conv2_textbook(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t j = 0; j < 2 * N - 1; ++j) {
        const std::size_t lo = j < N ? 0 : j - N + 1, hi = j < N ? j : N - 1;
        T sh = 0, sl = 0;
        for (std::size_t i = lo; i <= hi; ++i) {
            T ph, pl;
            tb::dw_times_dw3(r.x0[i], r.x1[i], r.y0[j - i], r.y1[j - i], ph, pl);
            tb::accurate_dw_plus_dw(sh, sl, ph, pl, sh, sl);
        }
        r.c0[j] = sh;
        r.c1[j] = sl;
    }
    d.cout[3] = T(1);
}

// --- The accumulator ----------------------------------------------------------------------------
// Over the arrays of a set, element after element; the state (s0, s1, a) in cout.

template <class T, int K>
KB_SI void put_acc(Set<T>& d, const kairn::Accumulator<T, K>& acc) {
    d.cout[0] = acc.running_sum().limb[0];
    d.cout[1] = K == 2 ? acc.running_sum().limb[K - 1] : T(0);
    d.cout[2] = acc.magnitudes();
    d.cout[3] = T(acc.count());
}
template <class T>
KB_SI void put_state(Set<T>& d, T s0, T s1, T a, std::size_t n) {
    d.cout[0] = s0;
    d.cout[1] = s1;
    d.cout[2] = a;
    d.cout[3] = T(n);
}

template <class T> KB_SI void acc1add_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 1> acc;
    for (std::size_t i = 0; i < r.n; ++i) acc.add(r.x0[i]);
    put_acc(d, acc);
}
template <class T> KB_SI void acc1add_kairn(Set<T>& d) {
    const P<T> r(d);
    T s = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) kg::acc_add_1(s, a, r.x0[i], s, a);
    put_state(d, s, T(0), a, r.n);
}
template <class T> KB_SI void acc1prod_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 1> acc;
    for (std::size_t i = 0; i < r.n; ++i) acc.add_product(r.x0[i], r.y0[i]);
    put_acc(d, acc);
}
template <class T> KB_SI void acc1prod_kairn(Set<T>& d) {
    const P<T> r(d);
    T s = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) kg::acc_mul_entry_1(s, a, r.x0[i], r.y0[i], s, a);
    put_state(d, s, T(0), a, r.n);
}
template <class T> KB_SI void acc1prod_bare(Set<T>& d) {
    const P<T> r(d);
    T s = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) kg::acc_mul_1(s, a, r.x0[i], r.y0[i], s, a);
    put_state(d, s, T(0), a, r.n);
}
template <class T> KB_SI void acc2add_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 2> acc;
    for (std::size_t i = 0; i < r.n; ++i) {
        const T l[2] = {r.x0[i], r.x1[i]};
        acc.add(E2<T>::from_limbs(l));
    }
    put_acc(d, acc);
}
template <class T> KB_SI void acc2add_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T g0, g1;   // from_limbs guards the limbs it reads (kernel make_2_limbs, rule R3)
        kg::make_2_limbs(r.x0[i], r.x1[i], g0, g1);
        kg::acc_add_2(s0, s1, a, g0, g1, s0, s1, a);
    }
    put_state(d, s0, s1, a, r.n);
}
template <class T> KB_SI void acc2prod_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 2> acc;
    for (std::size_t i = 0; i < r.n; ++i) {
        const T lx[2] = {r.x0[i], r.x1[i]}, ly[2] = {r.y0[i], r.y1[i]};
        acc.add_product(E2<T>::from_limbs(lx), E2<T>::from_limbs(ly));
    }
    put_acc(d, acc);
}
template <class T> KB_SI void acc2prod_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T gx0, gx1, gy0, gy1;
        kg::make_2_limbs(r.x0[i], r.x1[i], gx0, gx1);
        kg::make_2_limbs(r.y0[i], r.y1[i], gy0, gy1);
        kg::acc_mul_entry_2(s0, s1, a, gx0, gx1, gy0, gy1, s0, s1, a);
    }
    put_state(d, s0, s1, a, r.n);
}
template <class T> KB_SI void acc2prod_bare(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T gx0, gx1, gy0, gy1;
        kg::make_2_limbs(r.x0[i], r.x1[i], gx0, gx1);
        kg::make_2_limbs(r.y0[i], r.y1[i], gy0, gy1);
        kg::acc_mul_2(s0, s1, a, gx0, gx1, gy0, gy1, s0, s1, a);
    }
    put_state(d, s0, s1, a, r.n);
}
// An accurate sum and dot product of one-limb data with Kairn: a two-limb accumulator fed values of T.
template <class T> KB_SI void acc2addd_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 2> acc;
    for (std::size_t i = 0; i < r.n; ++i) acc.add(r.x0[i]);
    put_acc(d, acc);
}
template <class T> KB_SI void acc2addd_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T g0, g1;
        kg::make_2(r.x0[i], g0, g1);
        kg::acc_add_2(s0, s1, a, g0, g1, s0, s1, a);
    }
    put_state(d, s0, s1, a, r.n);
}
template <class T> KB_SI void acc2prodd_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, 2> acc;
    for (std::size_t i = 0; i < r.n; ++i) acc.add_product(r.x0[i], r.y0[i]);
    put_acc(d, acc);
}
template <class T> KB_SI void acc2prodd_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0, a = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T x0, x1, y0, y1;
        kg::make_2(r.x0[i], x0, x1);
        kg::make_2(r.y0[i], y0, y1);
        kg::acc_mul_entry_2(s0, s1, a, x0, x1, y0, y1, s0, s1, a);
    }
    put_state(d, s0, s1, a, r.n);
}
// Partial sums, as threads would make them (here one after another, in one thread): the array cut
// into PARTS contiguous parts, one accumulator for each, merged in order; and LANES, element i to
// accumulator i mod W, as the lane order deals them, merged from accumulator 0 upward.
template <class T, int K, int PARTS> KB_SI void accpart_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, K> acc[PARTS];
    const std::size_t m = r.n / PARTS;
    for (int p = 0; p < PARTS; ++p)
        for (std::size_t i = std::size_t(p) * m; i < std::size_t(p + 1) * m; ++i) {
            if constexpr (K == 1) {
                acc[p].add(r.x0[i]);
            } else {
                const T l[2] = {r.x0[i], r.x1[i]};
                acc[p].add(E2<T>::from_limbs(l));
            }
        }
    for (int p = 1; p < PARTS; ++p) acc[0].merge(acc[p]);
    put_acc(d, acc[0]);
}
template <class T, int K, int PARTS> KB_SI void accpart_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0[PARTS], s1[PARTS], a[PARTS];
    const std::size_t m = r.n / PARTS;
    for (int p = 0; p < PARTS; ++p) {
        s0[p] = s1[p] = a[p] = 0;
        for (std::size_t i = std::size_t(p) * m; i < std::size_t(p + 1) * m; ++i) {
            if constexpr (K == 1) {
                kg::acc_add_1(s0[p], a[p], r.x0[i], s0[p], a[p]);
            } else {
                T g0, g1;
                kg::make_2_limbs(r.x0[i], r.x1[i], g0, g1);
                kg::acc_add_2(s0[p], s1[p], a[p], g0, g1, s0[p], s1[p], a[p]);
            }
        }
    }
    for (int p = 1; p < PARTS; ++p) {
        if constexpr (K == 1) {
            kg::acc_merge_1(s0[0], a[0], s0[p], a[p], s0[0], a[0]);
        } else {
            kg::acc_merge_2(s0[0], s1[0], a[0], s0[p], s1[p], a[p], s0[0], s1[0], a[0]);
        }
    }
    put_state(d, s0[0], s1[0], a[0], m * PARTS);
}
template <class T, int K> KB_SI void acclanes_op(Set<T>& d) {
    const P<T> r(d);
    kairn::Accumulator<T, K> acc[W<T>];
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) {
            if constexpr (K == 1) {
                acc[l].add(r.x0[i + l]);
            } else {
                const T lm[2] = {r.x0[i + l], r.x1[i + l]};
                acc[l].add(E2<T>::from_limbs(lm));
            }
        }
    for (int l = 1; l < W<T>; ++l) acc[0].merge(acc[l]);
    put_acc(d, acc[0]);
}
template <class T, int K> KB_SI void acclanes_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0[W<T>], s1[W<T>], a[W<T>];
    for (int l = 0; l < W<T>; ++l) s0[l] = s1[l] = a[l] = 0;
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) {
            if constexpr (K == 1) {
                kg::acc_add_1(s0[l], a[l], r.x0[i + l], s0[l], a[l]);
            } else {
                T g0, g1;
                kg::make_2_limbs(r.x0[i + l], r.x1[i + l], g0, g1);
                kg::acc_add_2(s0[l], s1[l], a[l], g0, g1, s0[l], s1[l], a[l]);
            }
        }
    for (int l = 1; l < W<T>; ++l) {
        if constexpr (K == 1) {
            kg::acc_merge_1(s0[0], a[0], s0[l], a[l], s0[0], a[0]);
        } else {
            kg::acc_merge_2(s0[0], s1[0], a[0], s0[l], s1[l], a[l], s0[0], s1[0], a[0]);
        }
    }
    put_state(d, s0[0], s1[0], a[0], i);
}
// The 256 accumulators of the set: merged into one (a chain), and each one's sum(), error_bound()
// and ball() (independent calls).
constexpr int kAcc = 256;
template <class T, int K> KB_SI const std::vector<kairn::Accumulator<T, K>>& accs(const Set<T>& d) {
    if constexpr (K == 1) {
        return d.acc1;
    } else {
        return d.acc2;
    }
}
template <class T, int K> KB_SI void accmerge_op(Set<T>& d) {
    kairn::Accumulator<T, K> acc;
    const auto& v = accs<T, K>(d);
    for (int j = 0; j < kAcc; ++j) acc.merge(v[std::size_t(j)]);
    put_acc(d, acc);
}
template <class T, int K> KB_SI void accmerge_kairn(Set<T>& d) {
    T s0 = 0, s1 = 0, a = 0;
    std::size_t n = 0;
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            const auto& o = d.acc1[std::size_t(j)];
            kg::acc_merge_1(s0, a, o.running_sum().limb[0], o.magnitudes(), s0, a);
            n += o.count();
        } else {
            const auto& o = d.acc2[std::size_t(j)];
            kg::acc_merge_2(s0, s1, a, o.running_sum().limb[0], o.running_sum().limb[1], o.magnitudes(), s0, s1, a);
            n += o.count();
        }
    }
    put_state(d, s0, s1, a, n);
}
template <class T, int K> KB_SI void accsum_op(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            const auto s = d.acc1[std::size_t(j)].sum();
            d.out[std::size_t(2 * j)] = s.value.limb[0];
            d.out[std::size_t(2 * j + 1)] = T(s.finite);
        } else {
            const auto s = d.acc2[std::size_t(j)].sum();
            d.out[std::size_t(3 * j)] = s.value.limb[0];
            d.out[std::size_t(3 * j + 1)] = s.value.limb[1];
            d.out[std::size_t(3 * j + 2)] = T(s.finite);
        }
    }
}
template <class T, int K> KB_SI void accsum_kairn(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        bool f = false;
        if constexpr (K == 1) {
            kg::fold_finish_1(d.acc1[std::size_t(j)].running_sum().limb[0], d.out[std::size_t(2 * j)], f);
            d.out[std::size_t(2 * j + 1)] = T(f);
        } else {
            const auto& s = d.acc2[std::size_t(j)].running_sum();
            kg::fold_finish_2(s.limb[0], s.limb[1], d.out[std::size_t(3 * j)], d.out[std::size_t(3 * j + 1)], f);
            d.out[std::size_t(3 * j + 2)] = T(f);
        }
    }
}
template <class T, int K> KB_SI void accbound_op(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            d.out[std::size_t(j)] = d.acc1[std::size_t(j)].error_bound();
        } else {
            d.out[std::size_t(j)] = d.acc2[std::size_t(j)].error_bound();
        }
    }
}
// error_bound() as accumulator.hpp computes it, with the generated kernels.
template <class T, int K> KB_SI T bound_of(T s0, T a, std::uint64_t n) {
    constexpr T inf = std::numeric_limits<T>::infinity();
    if (n == ~std::uint64_t{0} || !(std::fabs(s0) <= std::numeric_limits<T>::max())) return inf;
    const T m = kairn::detail::count_up<T>(n);
    T g = 0, t = 0, r = 0;
    bool ok = false, ok_r = false;
    if constexpr (K == 1) {
        kg::bound_dot_1(m, g, t, ok);
        if (!ok) return inf;
        kg::acc_radius_1(a, m, g, t, r, ok_r);
    } else {
        kg::bound_dot_2(m, g, t, ok);
        if (!ok) return inf;
        kg::acc_radius_2(a, m, g, t, r, ok_r);
    }
    return ok_r && std::fabs(r) <= std::numeric_limits<T>::max() ? r : inf;
}
template <class T, int K> KB_SI void accbound_kairn(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            const auto& o = d.acc1[std::size_t(j)];
            d.out[std::size_t(j)] = bound_of<T, 1>(o.running_sum().limb[0], o.magnitudes(), o.count());
        } else {
            const auto& o = d.acc2[std::size_t(j)];
            d.out[std::size_t(j)] = bound_of<T, 2>(o.running_sum().limb[0], o.magnitudes(), o.count());
        }
    }
}
template <class T, int K> KB_SI void accball_op(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            const kairn::Ball<T, 1> b = d.acc1[std::size_t(j)].ball();
            d.out[std::size_t(2 * j)] = b.center().limb[0];
            d.out[std::size_t(2 * j + 1)] = b.radius();
        } else {
            const kairn::Ball<T, 2> b = d.acc2[std::size_t(j)].ball();
            d.out[std::size_t(3 * j)] = b.center().limb[0];
            d.out[std::size_t(3 * j + 1)] = b.center().limb[1];
            d.out[std::size_t(3 * j + 2)] = b.radius();
        }
    }
}
template <class T, int K> KB_SI void accball_kairn(Set<T>& d) {
    for (int j = 0; j < kAcc; ++j) {
        if constexpr (K == 1) {
            const auto& o = d.acc1[std::size_t(j)];
            const T r = bound_of<T, 1>(o.running_sum().limb[0], o.magnitudes(), o.count());
            kg::ball_make_1(o.running_sum().limb[0], r, d.out[std::size_t(2 * j)], d.out[std::size_t(2 * j + 1)]);
        } else {
            const auto& o = d.acc2[std::size_t(j)];
            const T r = bound_of<T, 2>(o.running_sum().limb[0], o.magnitudes(), o.count());
            kg::ball_make_2(o.running_sum().limb[0], o.running_sum().limb[1], r, d.out[std::size_t(3 * j)],
                            d.out[std::size_t(3 * j + 1)], d.out[std::size_t(3 * j + 2)]);
        }
    }
}

// --- Short arrays -------------------------------------------------------------------------------
// 256 calls on the windows [j, j + n) of arrays of 1024 + 256 elements. tp: independent calls; lat:
// the window of call j + 1 starts at j + 1 + (r_j != r_j), r_j the result of call j, always j + 1,
// but the address waits for the result.

constexpr int kCalls = 256;
#define KB_SHORT(NAME, K, CALL_OP, CALL_KAIRN)                                                     \
    template <int N> KB_SI void NAME##_op_tp(Set<double>& d) {                                     \
        const double *x0 = d.s0.data(), *x1 = d.s1.data(), *y0 = d.t0.data(), *y1 = d.t1.data();  \
        (void)x1;                                                                                  \
        (void)y0;                                                                                  \
        (void)y1;                                                                                  \
        double* out = d.sout.data();                                                               \
        for (int j = 0; j < kCalls; ++j) {                                                         \
            const std::size_t o = std::size_t(j);                                                  \
            const auto r = CALL_OP;                                                                \
            out[K * j] = r.value.limb[0];                                                          \
            if (K == 2) out[K * j + K - 1] = r.value.limb[K - 1];                                  \
        }                                                                                          \
    }                                                                                              \
    template <int N> KB_SI void NAME##_op_lat(Set<double>& d) {                                    \
        const double *x0 = d.s0.data(), *x1 = d.s1.data(), *y0 = d.t0.data(), *y1 = d.t1.data();  \
        (void)x1;                                                                                  \
        (void)y0;                                                                                  \
        (void)y1;                                                                                  \
        double* out = d.sout.data();                                                               \
        std::size_t o = 0;                                                                         \
        for (int j = 0; j < kCalls; ++j) {                                                         \
            const auto r = CALL_OP;                                                                \
            out[K * j] = r.value.limb[0];                                                          \
            if (K == 2) out[K * j + K - 1] = r.value.limb[K - 1];                                  \
            o = std::size_t(j + 1) + std::size_t(r.value.limb[0] != r.value.limb[0]);             \
        }                                                                                          \
    }                                                                                              \
    template <int N> KB_SI void NAME##_kairn_tp(Set<double>& d) {                                  \
        const double *x0 = d.s0.data(), *x1 = d.s1.data(), *y0 = d.t0.data(), *y1 = d.t1.data();  \
        (void)x1;                                                                                  \
        (void)y0;                                                                                  \
        (void)y1;                                                                                  \
        double* out = d.sout.data();                                                               \
        for (int j = 0; j < kCalls; ++j) {                                                         \
            const std::size_t o = std::size_t(j);                                                  \
            double v[2] = {0, 0};                                                                  \
            bool f = false;                                                                        \
            CALL_KAIRN;                                                                            \
            out[K * j] = v[0];                                                                     \
            if (K == 2) out[K * j + K - 1] = v[K - 1];                                             \
        }                                                                                          \
    }                                                                                              \
    template <int N> KB_SI void NAME##_kairn_lat(Set<double>& d) {                                 \
        const double *x0 = d.s0.data(), *x1 = d.s1.data(), *y0 = d.t0.data(), *y1 = d.t1.data();  \
        (void)x1;                                                                                  \
        (void)y0;                                                                                  \
        (void)y1;                                                                                  \
        double* out = d.sout.data();                                                               \
        std::size_t o = 0;                                                                         \
        for (int j = 0; j < kCalls; ++j) {                                                         \
            double v[2] = {0, 0};                                                                  \
            bool f = false;                                                                        \
            CALL_KAIRN;                                                                            \
            out[K * j] = v[0];                                                                     \
            if (K == 2) out[K * j + K - 1] = v[K - 1];                                             \
            o = std::size_t(j + 1) + std::size_t(v[0] != v[0]);                                    \
        }                                                                                          \
    }
KB_SHORT(ssum1, 1, kairn::sum(V1<double>(x0 + o, N)), KB_FAST(sum_1_entry)(x0 + o, N, v[0], f))
KB_SHORT(ssum2, 2, kairn::sum(V2<double>(x0 + o, x1 + o, N)), KB_FAST(sum_2_entry)(x0 + o, x1 + o, N, v[0], v[1], f))
KB_SHORT(sdot1, 1, kairn::dot(V1<double>(x0 + o, N), V1<double>(y0 + o, N)),
         KB_FAST(dot_1_entry)(x0 + o, y0 + o, N, v[0], f))
KB_SHORT(sdot2, 2, kairn::dot(V2<double>(x0 + o, x1 + o, N), V2<double>(y0 + o, y1 + o, N)),
         KB_FAST(dot_2)(x0 + o, x1 + o, y0 + o, y1 + o, N, v[0], v[1], f))

}  // namespace

// --- The timed functions ------------------------------------------------------------------------
// X(B, SUF, T, KIND, SIZE, KERNEL, VARIANT, FN, OUT, VALUES, REF): FN the function template
// instance, OUT where it writes, VALUES how many values of T (0: the elements of the set, times the
// limbs of OUT), REF the variant it is checked against byte for byte ("" for a reference, which is
// checked against the exact result; "exact" for a textbook loop, checked within its own bound).


#define KB_RED1(X, B, SUF, T, KIND, SZ, K)                                                         \
    X(B, SUF, T, KIND, SZ, K, op, K##_op<T>, O_C1, 1, "kairn")                                     \
    X(B, SUF, T, KIND, SZ, K, seq, K##_seq<T>, O_C1, 1, "kseq")                                    \
    X(B, SUF, T, KIND, SZ, K, kairn, K##_kairn<T>, O_C1, 1, "")                                    \
    X(B, SUF, T, KIND, SZ, K, kseq, K##_kseq<T>, O_C1, 1, "")
#define KB_RED2(X, B, SUF, T, KIND, SZ, K)                                                         \
    X(B, SUF, T, KIND, SZ, K, op, K##_op<T>, O_C2, 2, "kairn")                                     \
    X(B, SUF, T, KIND, SZ, K, seq, K##_seq<T>, O_C2, 2, "kseq")                                    \
    X(B, SUF, T, KIND, SZ, K, kairn, K##_kairn<T>, O_C2, 2, "")                                    \
    X(B, SUF, T, KIND, SZ, K, kseq, K##_kseq<T>, O_C2, 2, "")
#define KB_MAP(X, B, SUF, T, KIND, SZ, K, OUT)                                                     \
    X(B, SUF, T, KIND, SZ, K, op, K##_op<T>, OUT, 0, "kairn")                                      \
    X(B, SUF, T, KIND, SZ, K, kairn, K##_kairn<T>, OUT, 0, "kseq")                                 \
    X(B, SUF, T, KIND, SZ, K, kseq, K##_kseq<T>, OUT, 0, "")

#define KB_ASIZE(X, B, SUF, T, KIND, SZ)                                                           \
    KB_RED1(X, B, SUF, T, KIND, SZ, sum1)                                                          \
    X(B, SUF, T, KIND, SZ, sum1, bare, sum1_bare<T>, O_C1, 1, "kairn")                             \
    X(B, SUF, T, KIND, SZ, sum1, plain, sum1_plain<T>, O_C1, 1, "kseq")                            \
    X(B, SUF, T, KIND, SZ, sum1, plainw, sum1_plainw<T>, O_C1, 1, "kairn")                         \
    X(B, SUF, T, KIND, SZ, sum1, textbook, sum1_textbook<T>, O_C1, 1, "exact")                     \
    KB_RED2(X, B, SUF, T, KIND, SZ, sum2)                                                          \
    X(B, SUF, T, KIND, SZ, sum2, bare, sum2_bare<T>, O_C2, 2, "kairn")                             \
    X(B, SUF, T, KIND, SZ, sum2, textbook, sum2_textbook<T>, O_C2, 2, "exact")                     \
    KB_RED2(X, B, SUF, T, KIND, SZ, sumf2)                                                         \
    X(B, SUF, T, KIND, SZ, sumf2, textbook, sumf2_textbook<T>, O_C2, 2, "exact")                   \
    KB_RED2(X, B, SUF, T, KIND, SZ, sum2z)                                                         \
    KB_RED1(X, B, SUF, T, KIND, SZ, dot1)                                                          \
    X(B, SUF, T, KIND, SZ, dot1, bare, dot1_bare<T>, O_C1, 1, "kairn")                             \
    X(B, SUF, T, KIND, SZ, dot1, plain, dot1_plain<T>, O_C1, 1, "kseq")                            \
    X(B, SUF, T, KIND, SZ, dot1, plainw, dot1_plainw<T>, O_C1, 1, "kairn")                         \
    X(B, SUF, T, KIND, SZ, dot1, textbook, dot1_textbook<T>, O_C1, 1, "exact")                     \
    KB_RED2(X, B, SUF, T, KIND, SZ, dot2)                                                          \
    X(B, SUF, T, KIND, SZ, dot2, textbook, dot2_textbook<T>, O_C2, 2, "exact")                     \
    KB_RED2(X, B, SUF, T, KIND, SZ, dot2z)                                                         \
    KB_MAP(X, B, SUF, T, KIND, SZ, add1, O_Z1)                                                     \
    X(B, SUF, T, KIND, SZ, add1, bare, add1_bare<T>, O_Z1, 0, "kairn")                             \
    X(B, SUF, T, KIND, SZ, add1, plain, add1_plain<T>, O_Z1, 0, "kseq")                            \
    KB_MAP(X, B, SUF, T, KIND, SZ, add2, O_Z2)                                                     \
    X(B, SUF, T, KIND, SZ, add2, bare, add2_bare<T>, O_Z2, 0, "kairn")                             \
    X(B, SUF, T, KIND, SZ, add2, textbook, add2_textbook<T>, O_Z2, 0, "exact")                     \
    KB_MAP(X, B, SUF, T, KIND, SZ, scale1, O_Z1)                                                   \
    X(B, SUF, T, KIND, SZ, scale1, plain, scale1_plain<T>, O_Z1, 0, "kseq")                        \
    KB_MAP(X, B, SUF, T, KIND, SZ, scale2, O_Z2)                                                   \
    X(B, SUF, T, KIND, SZ, scale2, bare, scale2_bare<T>, O_Z2, 0, "kairn")                         \
    X(B, SUF, T, KIND, SZ, scale2, textbook, scale2_textbook<T>, O_Z2, 0, "exact")                 \
    KB_MAP(X, B, SUF, T, KIND, SZ, axpy1, O_Z1)                                                    \
    X(B, SUF, T, KIND, SZ, axpy1, bare, axpy1_bare<T>, O_Z1, 0, "kairn")                           \
    X(B, SUF, T, KIND, SZ, axpy1, plain, axpy1_plain<T>, O_Z1, 0, "kseq")                          \
    KB_MAP(X, B, SUF, T, KIND, SZ, axpy2, O_Z2)                                                    \
    X(B, SUF, T, KIND, SZ, axpy2, bare, axpy2_bare<T>, O_Z2, 0, "kairn")                           \
    X(B, SUF, T, KIND, SZ, axpy2, textbook, axpy2_textbook<T>, O_Z2, 0, "exact")                   \
    KB_MAP(X, B, SUF, T, KIND, SZ, axpy22, O_Z2)                                                   \
    X(B, SUF, T, KIND, SZ, axpy22, bare, axpy22_bare<T>, O_Z2, 0, "kairn")                         \
    X(B, SUF, T, KIND, SZ, axpy22, textbook, axpy22_textbook<T>, O_Z2, 0, "exact")                 \
    X(B, SUF, T, KIND, SZ, norm1, op, norm1_op<T>, O_C1, 1, "kairn")                               \
    X(B, SUF, T, KIND, SZ, norm1, kairn, norm1_kairn<T>, O_C1, 1, "kseq")                          \
    X(B, SUF, T, KIND, SZ, norm1, kseq, norm1_kseq<T>, O_C1, 1, "")                                \
    X(B, SUF, T, KIND, SZ, norm1, plain, norm1_plain<T>, O_C1, 1, "kseq")                          \
    X(B, SUF, T, KIND, SZ, norm2, op, norm2_op<T>, O_C1, 1, "kairn")                               \
    X(B, SUF, T, KIND, SZ, norm2, kairn, norm2_kairn<T>, O_C1, 1, "kseq")                          \
    X(B, SUF, T, KIND, SZ, norm2, kseq, norm2_kseq<T>, O_C1, 1, "")

#define KB_CONV(X, B, SUF, T, N)                                                                   \
    X(B, SUF, T, tp, 0, conv1_##N, op, (conv1_op<T, N>), O_ZC1, 2 * N - 1, "kairn")               \
    X(B, SUF, T, tp, 0, conv1_##N, kairn, (conv1_kairn<T, N>), O_ZC1, 2 * N - 1, "plain")         \
    X(B, SUF, T, tp, 0, conv1_##N, bare, (conv1_bare<T, N>), O_ZC1, 2 * N - 1, "kairn")           \
    X(B, SUF, T, tp, 0, conv1_##N, plain, (conv1_plain<T, N>), O_ZC1, 2 * N - 1, "")              \
    X(B, SUF, T, tp, 0, conv2_##N, op, (conv2_op<T, N>), O_ZC2, 2 * (2 * N - 1), "kairn")         \
    X(B, SUF, T, tp, 0, conv2_##N, kairn, (conv2_kairn<T, N>), O_ZC2, 2 * (2 * N - 1), "")        \
    X(B, SUF, T, tp, 0, conv2_##N, textbook, (conv2_textbook<T, N>), O_ZC2, 2 * (2 * N - 1), "exact")

#define KB_ACC(X, KIND, SZ)                                                                        \
    X("m2c", c64, double, KIND, SZ, acc1add, op, acc1add_op<double>, O_ACC, 3, "kairn")            \
    X("m2c", c64, double, KIND, SZ, acc1add, kairn, acc1add_kairn<double>, O_ACC, 3, "")           \
    X("m2c", c64, double, KIND, SZ, acc1prod, op, acc1prod_op<double>, O_ACC, 3, "kairn")          \
    X("m2c", c64, double, KIND, SZ, acc1prod, kairn, acc1prod_kairn<double>, O_ACC, 3, "")         \
    X("m2c", c64, double, KIND, SZ, acc1prod, bare, acc1prod_bare<double>, O_ACC, 3, "kairn")      \
    X("m2c", c64, double, KIND, SZ, acc2add, op, acc2add_op<double>, O_ACC, 3, "kairn")            \
    X("m2c", c64, double, KIND, SZ, acc2add, kairn, acc2add_kairn<double>, O_ACC, 3, "")           \
    X("m2c", c64, double, KIND, SZ, acc2prod, op, acc2prod_op<double>, O_ACC, 3, "kairn")          \
    X("m2c", c64, double, KIND, SZ, acc2prod, kairn, acc2prod_kairn<double>, O_ACC, 3, "")         \
    X("m2c", c64, double, KIND, SZ, acc2prod, bare, acc2prod_bare<double>, O_ACC, 3, "kairn")      \
    X("m2c", c64, double, KIND, SZ, acc2addd, op, acc2addd_op<double>, O_ACC, 3, "kairn")          \
    X("m2c", c64, double, KIND, SZ, acc2addd, kairn, acc2addd_kairn<double>, O_ACC, 3, "")         \
    X("m2c", c64, double, KIND, SZ, acc2prodd, op, acc2prodd_op<double>, O_ACC, 3, "kairn")        \
    X("m2c", c64, double, KIND, SZ, acc2prodd, kairn, acc2prodd_kairn<double>, O_ACC, 3, "")       \
    X("m2c", c64, double, KIND, SZ, acc1part4, op, (accpart_op<double, 1, 4>), O_ACC, 3, "kairn")  \
    X("m2c", c64, double, KIND, SZ, acc1part4, kairn, (accpart_kairn<double, 1, 4>), O_ACC, 3, "")  \
    X("m2c", c64, double, KIND, SZ, acc1part16, op, (accpart_op<double, 1, 16>), O_ACC, 3, "kairn") \
    X("m2c", c64, double, KIND, SZ, acc1part16, kairn, (accpart_kairn<double, 1, 16>), O_ACC, 3, "") \
    X("m2c", c64, double, KIND, SZ, acc1lanes, op, (acclanes_op<double, 1>), O_ACC, 3, "kairn")    \
    X("m2c", c64, double, KIND, SZ, acc1lanes, kairn, (acclanes_kairn<double, 1>), O_ACC, 3, "")   \
    X("m2c", c64, double, KIND, SZ, acc2part4, op, (accpart_op<double, 2, 4>), O_ACC, 3, "kairn")  \
    X("m2c", c64, double, KIND, SZ, acc2part4, kairn, (accpart_kairn<double, 2, 4>), O_ACC, 3, "")  \
    X("m2c", c64, double, KIND, SZ, acc2part16, op, (accpart_op<double, 2, 16>), O_ACC, 3, "kairn") \
    X("m2c", c64, double, KIND, SZ, acc2part16, kairn, (accpart_kairn<double, 2, 16>), O_ACC, 3, "") \
    X("m2c", c64, double, KIND, SZ, acc2lanes, op, (acclanes_op<double, 2>), O_ACC, 3, "kairn")    \
    X("m2c", c64, double, KIND, SZ, acc2lanes, kairn, (acclanes_kairn<double, 2>), O_ACC, 3, "")

#define KB_ACCN(X)                                                                                 \
    X("m2c", c64, double, tp, 0, acc1merge, op, (accmerge_op<double, 1>), O_ACC, 3, "kairn")       \
    X("m2c", c64, double, tp, 0, acc1merge, kairn, (accmerge_kairn<double, 1>), O_ACC, 3, "")      \
    X("m2c", c64, double, tp, 0, acc2merge, op, (accmerge_op<double, 2>), O_ACC, 3, "kairn")       \
    X("m2c", c64, double, tp, 0, acc2merge, kairn, (accmerge_kairn<double, 2>), O_ACC, 3, "")      \
    X("m2c", c64, double, tp, 0, acc1sum, op, (accsum_op<double, 1>), O_OUT, 2 * 256, "kairn")     \
    X("m2c", c64, double, tp, 0, acc1sum, kairn, (accsum_kairn<double, 1>), O_OUT, 2 * 256, "")    \
    X("m2c", c64, double, tp, 0, acc2sum, op, (accsum_op<double, 2>), O_OUT, 3 * 256, "kairn")     \
    X("m2c", c64, double, tp, 0, acc2sum, kairn, (accsum_kairn<double, 2>), O_OUT, 3 * 256, "")    \
    X("m2c", c64, double, tp, 0, acc1bound, op, (accbound_op<double, 1>), O_OUT, 256, "kairn")     \
    X("m2c", c64, double, tp, 0, acc1bound, kairn, (accbound_kairn<double, 1>), O_OUT, 256, "")    \
    X("m2c", c64, double, tp, 0, acc2bound, op, (accbound_op<double, 2>), O_OUT, 256, "kairn")     \
    X("m2c", c64, double, tp, 0, acc2bound, kairn, (accbound_kairn<double, 2>), O_OUT, 256, "")    \
    X("m2c", c64, double, tp, 0, acc1ball, op, (accball_op<double, 1>), O_OUT, 2 * 256, "kairn")   \
    X("m2c", c64, double, tp, 0, acc1ball, kairn, (accball_kairn<double, 1>), O_OUT, 2 * 256, "")  \
    X("m2c", c64, double, tp, 0, acc2ball, op, (accball_op<double, 2>), O_OUT, 3 * 256, "kairn")   \
    X("m2c", c64, double, tp, 0, acc2ball, kairn, (accball_kairn<double, 2>), O_OUT, 3 * 256, "")

#define KB_SHORTN(X, KERN, K, N)                                                                   \
    X("m2k", k64, double, tp, 0, KERN##_n##N, op, (KERN##_op_tp<N>), O_SHORT, K * 256, "kairn")    \
    X("m2k", k64, double, tp, 0, KERN##_n##N, kairn, (KERN##_kairn_tp<N>), O_SHORT, K * 256, "")   \
    X("m2k", k64, double, lat, 0, KERN##_n##N, op, (KERN##_op_lat<N>), O_SHORT, K * 256, "kairn")  \
    X("m2k", k64, double, lat, 0, KERN##_n##N, kairn, (KERN##_kairn_lat<N>), O_SHORT, K * 256, "")
#define KB_SHORTK(X, KERN, K)                                                                      \
    KB_SHORTN(X, KERN, K, 1) KB_SHORTN(X, KERN, K, 2) KB_SHORTN(X, KERN, K, 4) KB_SHORTN(X, KERN, K, 8) \
    KB_SHORTN(X, KERN, K, 16) KB_SHORTN(X, KERN, K, 64) KB_SHORTN(X, KERN, K, 1024)

#define KB_ALIST(X)                                                                                \
    KB_ASIZE(X, "m2a", a64, double, tp, 0) KB_ASIZE(X, "m2a", a64, double, llc, 1)                 \
    KB_ASIZE(X, "m2a", a64, double, mem, 2) KB_ASIZE(X, "m2af", a32, float, tp, 0)                 \
    KB_ASIZE(X, "m2af", a32, float, llc, 1) KB_ASIZE(X, "m2af", a32, float, mem, 2)                \
    KB_CONV(X, "m2a", a64, double, 16) KB_CONV(X, "m2a", a64, double, 64) KB_CONV(X, "m2a", a64, double, 512) \
    KB_CONV(X, "m2af", a32, float, 16) KB_CONV(X, "m2af", a32, float, 64) KB_CONV(X, "m2af", a32, float, 512) \
    KB_ACC(X, tp, 0) KB_ACC(X, llc, 1) KB_ACCN(X)                                                  \
    KB_SHORTK(X, ssum1, 1) KB_SHORTK(X, ssum2, 2) KB_SHORTK(X, sdot1, 1) KB_SHORTK(X, sdot2, 2)

#define KB_ADEF(B, SUF, T, KIND, SZ, KERNEL, VAR, FN, OUT, VALUES, REF)                            \
    extern "C" KB_NOINLINE void kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR(void*) { FN(set_of<T>(SZ)); }
KB_ALIST(KB_ADEF)

namespace kairn_bench::m2a {
bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size);
}

// ops: the elements of the set for the functions on arrays and the accumulator over arrays; the
// terms of a convolution, N^2; the calls for the short arrays and the 256 accumulators.
namespace {
// The coefficients of each polynomial of a convolution (conv1_N, conv2_N), 0 for another kernel.
int conv_n_of(const char* kernel) {
    const std::string k = kernel;
    return k.rfind("conv", 0) == 0 ? std::atoi(k.c_str() + 6) : 0;
}
int ops_of(const char* backend, const char* kernel, std::size_t elements) {
    const std::string b = backend, k = kernel;
    if (b == "m2k") return kCalls;
    if (const int n = conv_n_of(kernel)) return n * n;
    for (const char* t : {"merge", "1sum", "2sum", "bound", "ball"})
        if (k.find(t) != std::string::npos) return kAcc;
    return int(elements);
}
}  // namespace

#define KB_AROW(B, SUF, T, KIND, SZ, KERNEL, VAR, FN, OUT, VALUES, REF)                            \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)), 1, \
     ops_of(B, #KERNEL, size_of<T>(SZ)), OUT, VALUES, &kairn_bench::m2a::check},
#define KB_AMETA(B, SUF, T, KIND, SZ, KERNEL, VAR, FN, OUT, VALUES, REF)                           \
    {B "/" #KIND "/" #KERNEL "/" #VAR, REF, SZ, conv_n_of(#KERNEL)},

namespace kairn_bench::m2 {
const Entry m2_batch_entries[] = {
    KB_ALIST(KB_AROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
}  // namespace kairn_bench::m2

namespace kairn_bench::m2a {
const Meta metas[] = {
    KB_ALIST(KB_AMETA)
    {nullptr, nullptr, 0, 0},
};
}  // namespace kairn_bench::m2a

// --- The data and the checks --------------------------------------------------------------------

namespace {

using kairn_bench::exact::Exact;

template <class T>
T number(kairn_bench::util::Rng& g, T& lo) {
    // +-[1, 2) 2^k, k in [-8, 8], and a second limb about u times it (normalized), as m2_soa.cpp.
    const double s = g.sign();
    const double m = 1.0 + g.u01();
    const T a = T(s * std::ldexp(m, g.range(-8, 8)));
    const T b = T(double(a) * g.sym() * std::ldexp(1.0, -std::numeric_limits<T>::digits));
    T h;
    kg::fast_two_sum(a, b, h, lo);
    return h;
}

template <class T>
void fill(Set<T>& d, std::size_t n, std::uint64_t seed) {
    kairn_bench::util::Rng g{seed};
    d.n = n;
    d.x = kairn::SoA<T, 2>(n);
    d.y = kairn::SoA<T, 2>(n);
    d.z = kairn::SoA<T, 2>(n);
    d.zc = kairn::SoA<T, 2>(1024);
    d.zero.assign(n, T(0));
    T* x0 = d.x.view().limb(0);
    T* x1 = d.x.view().limb(1);
    T* y0 = d.y.view().limb(0);
    T* y1 = d.y.view().limb(1);
    for (std::size_t i = 0; i < n; ++i) {
        x0[i] = number<T>(g, x1[i]);
        y0[i] = number<T>(g, y1[i]);
    }
    d.a = T(std::exp2(0.25 * g.sym()));
    T al = T(double(d.a) * g.sym() * std::ldexp(1.0, -std::numeric_limits<T>::digits));
    T ah;
    kg::fast_two_sum(d.a, al, ah, al);
    d.a2 = two<T>(ah, al);
    // The exact sums.
    Sums& e = d.sums;
    Exact es1, ea1, es2, ea2, ed1, ep1, ed2, ep2;
    for (std::size_t i = 0; i < n; ++i) {
        es1.add(x0[i]);
        ea1.add(std::fabs(x0[i]));
        es2.add(x0[i]);
        es2.add(x1[i]);
        ea2.add(std::fabs(x0[i]));
        ea2.add(std::fabs(x1[i]));
        ed1.add_product(x0[i], y0[i]);
        ep1.add(std::fabs(double(x0[i]) * double(y0[i])));
        ed2.add_product(x0[i], y0[i]);
        ed2.add_product(x0[i], y1[i]);
        ed2.add_product(x1[i], y0[i]);
        ed2.add_product(x1[i], y1[i]);
        ep2.add(std::fabs(double(x0[i]) * double(y0[i])) * (1 + 1e-6));
    }
    e.es1 = es1;
    e.es2 = es2;
    e.ed1 = ed1;
    e.ed2 = ed2;
    e.s1 = es1.value();
    e.a1 = ea1.value();
    e.s2 = es2.value();
    e.a2 = ea2.value();
    e.d1 = ed1.value();
    e.p1 = ep1.value();
    e.d2 = ed2.value();
    e.p2 = ep2.value();
    // 256 accumulators of 1 to 7 terms each, of one and of two limbs.
    d.acc1.assign(kAcc, kairn::Accumulator<T, 1>());
    d.acc2.assign(kAcc, kairn::Accumulator<T, 2>());
    for (int j = 0; j < kAcc; ++j)
        for (int t = 0; t <= j % 7; ++t) {
            T lo;
            const T h = number<T>(g, lo);
            d.acc1[std::size_t(j)].add(h);
            d.acc2[std::size_t(j)].add(two<T>(h, lo));
        }
    d.out.assign(3 * kAcc, T(0));
    // The short arrays: 1024 + 256 elements and one more, for the windows.
    const std::size_t m = 1024 + kCalls + 1;
    d.s0.resize(m);
    d.s1.resize(m);
    d.t0.resize(m);
    d.t1.resize(m);
    for (std::size_t i = 0; i < m; ++i) {
        d.s0[i] = number<T>(g, d.s1[i]);
        d.t0[i] = number<T>(g, d.t1[i]);
    }
    d.sout.assign(2 * kCalls, T(0));
}

template <class T>
void make_sets() {
    if (g_sets<T>[0]) return;
    for (int s = 0; s < 3; ++s) {
        g_sets<T>[s] = new Set<T>();
        fill(*g_sets<T>[s], size_of<T>(s), (sizeof(T) == 8 ? 201 : 202) + 10 * std::uint64_t(s));
    }
}

template <class T>
void clear(Set<T>& d) {
    const auto wipe = [](void* p, std::size_t bytes) { std::memset(p, 0xff, bytes); };
    wipe(d.z.view().limb(0), d.n * sizeof(T));
    wipe(d.z.view().limb(1), d.n * sizeof(T));
    wipe(d.zc.view().limb(0), 1024 * sizeof(T));
    wipe(d.zc.view().limb(1), 1024 * sizeof(T));
    wipe(d.cout, sizeof d.cout);
    wipe(d.out.data(), d.out.size() * sizeof(T));
    wipe(d.sout.data(), d.sout.size() * sizeof(T));
}

// The values a function wrote, and its flag (or count) last.
template <class T>
std::vector<T> read(Set<T>& d, int out, int values) {
    std::vector<T> v;
    const T* z0 = d.z.view().limb(0);
    const T* z1 = d.z.view().limb(1);
    const T* c0 = d.zc.view().limb(0);
    const T* c1 = d.zc.view().limb(1);
    switch (out) {
        case O_C1: v = {d.cout[0], d.cout[3]}; break;
        case O_C2: v = {d.cout[0], d.cout[1], d.cout[3]}; break;
        case O_ACC: v = {d.cout[0], d.cout[1], d.cout[2], d.cout[3]}; break;
        case O_Z1:
            v.assign(z0, z0 + d.n);
            v.push_back(d.cout[3]);
            break;
        case O_Z2:
            v.assign(z0, z0 + d.n);
            v.insert(v.end(), z1, z1 + d.n);
            v.push_back(d.cout[3]);
            break;
        case O_ZC1:
            v.assign(c0, c0 + values);
            v.push_back(d.cout[3]);
            break;
        case O_ZC2:
            v.assign(c0, c0 + values / 2);
            v.insert(v.end(), c1, c1 + values / 2);
            v.push_back(d.cout[3]);
            break;
        case O_OUT: v.assign(d.out.begin(), d.out.begin() + values); break;
        default: v.assign(d.sout.begin(), d.sout.begin() + values); break;
    }
    return v;
}

const Entry* find_entry(const std::string& name) {
    for (const Entry* e = kairn_bench::m2::m2_batch_entries; e->name; ++e)
        if (name == e->name) return e;
    return nullptr;
}
const Meta* find_meta(const std::string& name) {
    for (const Meta* m = metas; m->name; ++m)
        if (name == m->name) return m;
    return nullptr;
}

template <class T>
std::vector<T> run(const Entry& e, int size) {
    Set<T>& d = set_of<T>(size);
    clear(d);
    e.fn(nullptr);
    return read(d, e.region, e.values);
}

// |the value of the limbs v0 + v1 - the exact value|, through the exact sum.
double err_of(Exact x, double v0, double v1) {
    x.add(-v0);
    x.add(-v1);
    return std::fabs(x.value());
}

bool fail(char* why, std::size_t size, const char* what, double a, double b) {
    std::snprintf(why, size, "%s: %a, %a", what, a, b);
    return false;
}

// A reference against the exact result, within the bound the library states (or, for a textbook
// loop, within its own bound).
template <class T>
bool check_exact(const Entry& e, const Meta& m, const std::vector<T>& v, char* why, std::size_t size) {
    Set<T>& d = set_of<T>(m.size);
    const std::string name = e.name;
    const std::string tail = name.substr(name.find('/', name.find('/') + 1) + 1);
    const std::string k = tail.substr(0, tail.find('/'));
    const std::string var = tail.substr(tail.find('/') + 1);
    const double u = double(std::numeric_limits<T>::epsilon()) / 2, n = double(d.n);
    const bool textbook = var == "textbook";
    const Sums& s = d.sums;
    using X1 = kairn::traits<E1<T>>;
    using X2 = kairn::traits<E2<T>>;
    const double slack = 1 + 1e-9;
    auto within = [&](double err, double bound) {
        return err <= bound * slack ? true : fail(why, size, "error above the bound", err, bound);
    };
    if (name.rfind("m2k/", 0) == 0) {   // the short arrays: each call against its window's exact result
        const bool two = k[4] == '2', dot = k[1] == 'd';
        const std::size_t N = std::size_t(std::atoi(k.c_str() + k.find("_n") + 2));
        for (int j = 0; j < kCalls; ++j) {
            Exact ex;
            double mag = 0;
            for (std::size_t i = std::size_t(j); i < std::size_t(j) + N; ++i) {
                if (dot) {
                    ex.add_product(d.s0[i], d.t0[i]);
                    if (two) {
                        ex.add_product(d.s0[i], d.t1[i]);
                        ex.add_product(d.s1[i], d.t0[i]);
                        ex.add_product(d.s1[i], d.t1[i]);
                    }
                    mag += std::fabs(double(d.s0[i]) * double(d.t0[i])) * 1.01;
                } else {
                    ex.add(d.s0[i]);
                    if (two) ex.add(d.s1[i]);
                    mag += std::fabs(double(d.s0[i])) * 1.01;
                }
            }
            const std::size_t at = std::size_t(two ? 2 * j : j);
            const double err = err_of(ex, double(v[at]), two ? double(v[at + 1]) : 0.0);
            double bound;
            if (dot) {
                const auto b = two ? X2::dot(N) : X1::dot(N);
                bound = double(b.unit) * mag + double(b.tiny);
            } else {
                bound = double(two ? X2::sum(N).unit : X1::sum(N).unit) * mag;
            }
            if (!within(err, bound)) return false;
        }
        return true;
    }
    if (k == "sum1" || k == "sum2z") {
        const double err = err_of(s.es1, double(v[0]), k == "sum2z" ? double(v[1]) : 0.0);
        if (textbook) return within(err, 2 * (u * std::fabs(s.s1) + n * n * u * u * s.a1));
        return within(err, double(k == "sum1" ? X1::sum(d.n).unit : X2::sum(d.n).unit) * s.a1);
    }
    if (k == "sum2" || k == "sumf2") {
        const double err = err_of(s.es2, double(v[0]), double(v[1]));
        if (textbook) return within(err, (k == "sum2" ? 6 : 16) * n * u * u * s.a2 + u * u * std::fabs(s.s2));
        return within(err, double(X2::sum(d.n).unit) * s.a2);
    }
    if (k == "dot1" || k == "dot2z") {
        const double err = err_of(s.ed1, double(v[0]), k == "dot2z" ? double(v[1]) : 0.0);
        if (textbook) return within(err, 2 * (u * std::fabs(s.d1) + n * n * u * u * s.p1));
        const auto b = k == "dot1" ? X1::dot(d.n) : X2::dot(d.n);
        return within(err, double(b.unit) * s.p1 + double(b.tiny));
    }
    if (k == "dot2") {
        const double err = err_of(s.ed2, double(v[0]), double(v[1]));
        if (textbook) return within(err, 16 * n * u * u * s.p2 + u * u * std::fabs(s.d2));
        const auto b = X2::dot(d.n);
        return within(err, double(b.unit) * s.p2 + double(b.tiny));
    }
    if (k == "norm1" || k == "norm2") {
        double mx = 0;
        const T* x0 = d.x.view().limb(0);
        for (std::size_t i = 0; i < d.n; ++i) mx = std::max(mx, std::fabs(double(x0[i])));
        if (k == "norm1") return double(v[0]) == mx ? true : fail(why, size, "norm, largest magnitude", double(v[0]), mx);
        return double(v[0]) >= mx * (1 - 2 * u) && double(v[0]) <= mx * (1 + 4 * u)
                   ? true
                   : fail(why, size, "norm, largest magnitude", double(v[0]), mx);
    }
    if (k.rfind("conv", 0) == 0) {
        const std::size_t N = std::size_t(m.conv_n);
        const bool two = k[4] == '2';
        const T *x0 = d.x.view().limb(0), *x1 = d.x.view().limb(1), *y0 = d.y.view().limb(0), *y1 = d.y.view().limb(1);
        const auto b = two ? X2::dot(N) : X1::dot(N);
        for (std::size_t j = 0; j < 2 * N - 1; ++j) {
            const std::size_t lo = j < N ? 0 : j - N + 1, hi = j < N ? j : N - 1;
            Exact ex;
            double mag = 0;
            for (std::size_t i = lo; i <= hi; ++i) {
                ex.add_product(x0[i], y0[j - i]);
                if (two) {
                    ex.add_product(x0[i], y1[j - i]);
                    ex.add_product(x1[i], y0[j - i]);
                    ex.add_product(x1[i], y1[j - i]);
                }
                mag += std::fabs(double(x0[i]) * double(y0[j - i]));
            }
            const double c0 = double(v[j]), c1 = two ? double(v[2 * N - 1 + j]) : 0.0;
            const double err = err_of(ex, c0, c1);
            const double bound = textbook ? 16 * double(hi - lo + 1) * u * u * mag * 1.01 + u * u * std::fabs(c0)
                                          : double(b.unit) * mag * 1.01 + double(b.tiny);
            if (!(err <= bound)) return fail(why, size, "a coefficient's error above the bound", err, bound);
        }
        return true;
    }
    if (k == "add1" || k == "add2" || k == "scale1" || k == "scale2" || k == "axpy1" || k == "axpy2" || k == "axpy22") {
        // A map, element by element: the textbook loops at every size, the references in L1.
        if (m.size != 0 && !textbook) return true;
        const bool two = k.back() == '2';
        const double c = two ? 16 * u * u : 4 * u;
        const T *x0 = d.x.view().limb(0), *x1 = d.x.view().limb(1), *y0 = d.y.view().limb(0), *y1 = d.y.view().limb(1);
        for (std::size_t i = 0; i < d.n; ++i) {
            Exact ex;
            double mag = 0;
            const double z0 = double(v[i]), z1 = two ? double(v[d.n + i]) : 0.0;
            if (k.rfind("add", 0) == 0) {
                ex.add(x0[i]);
                ex.add(y0[i]);
                if (two) {
                    ex.add(x1[i]);
                    ex.add(y1[i]);
                }
                mag = std::fabs(double(x0[i])) + std::fabs(double(y0[i]));
            } else {
                const double a0 = k == "axpy22" ? double(d.a2.limb[0]) : double(d.a);
                const double a1 = k == "axpy22" ? double(d.a2.limb[1]) : 0.0;
                ex.add_product(double(x0[i]), a0);
                ex.add_product(double(x0[i]), a1);
                if (two) {
                    ex.add_product(double(x1[i]), a0);
                    ex.add_product(double(x1[i]), a1);
                }
                mag = std::fabs(double(x0[i]) * a0);
                if (k.rfind("axpy", 0) == 0) {
                    ex.add(y0[i]);
                    if (two) ex.add(y1[i]);
                    mag += std::fabs(double(y0[i]));
                }
            }
            const double err = err_of(ex, z0, z1);
            const double bound = c * mag * 1.01 + 1e-300;
            if (!(err <= bound)) return fail(why, size, "an element's error above the bound", err, bound);
        }
        return true;
    }
    if (k.rfind("acc", 0) == 0 && k.find("sum") == std::string::npos && k.find("bound") == std::string::npos &&
        k.find("ball") == std::string::npos) {
        // The accumulator: the running sum within its own error_bound() of the exact sum of its terms.
        const bool twol = k[3] == '2';
        const std::uint64_t cnt = std::uint64_t(v[3]);
        double r;
        if (!twol) {
            r = double(kairn::Accumulator<T, 1>::from_state(E1<T>(v[0]), v[2], cnt).error_bound());
        } else {
            r = double(kairn::Accumulator<T, 2>::from_state(two<T>(v[0], v[1]), v[2], cnt).error_bound());
        }
        if (k.find("merge") != std::string::npos)
            return std::isfinite(r) ? true : fail(why, size, "the radius of the merge is not finite", r, 0);
        const bool prod = k.find("prod") != std::string::npos;
        const bool oned = k == "acc2addd" || k == "acc2prodd" || !twol;
        const Exact& ex = prod ? (oned ? s.ed1 : s.ed2) : (oned ? s.es1 : s.es2);
        const std::size_t used = std::size_t(cnt);
        if (used != d.n) return true;   // the parts' tails left out: their count is checked by the reference
        const double err = err_of(ex, double(v[0]), twol ? double(v[1]) : 0.0);
        return within(err, r);
    }
    for (const T x : v)   // the results of 256 accumulators: checked against the kernels (the reference)
        if (std::isnan(x)) return fail(why, size, "a NaN", double(x), 0);
    return true;
}

template <class T>
bool check_typed(const Entry& e, char* why, std::size_t size) {
    const Meta* m = find_meta(e.name);
    if (!m) {
        std::snprintf(why, size, "no row");
        return false;
    }
    const std::vector<T> got = run<T>(e, m->size);
    for (const T x : got)
        if (!std::isfinite(x)) {
            std::snprintf(why, size, "a value is not finite");
            return false;
        }
    const std::string ref = m->ref;
    if (ref.empty() || ref == "exact") return check_exact<T>(e, *m, got, why, size);
    const std::string name = e.name;
    const std::string ref_name = name.substr(0, name.rfind('/') + 1) + ref;
    const Entry* r = find_entry(ref_name);
    if (!r) {
        std::snprintf(why, size, "no reference %s", ref_name.c_str());
        return false;
    }
    const std::vector<T> want = run<T>(*r, m->size);
    if (want.size() != got.size()) {
        std::snprintf(why, size, "not as many values as %s", ref_name.c_str());
        return false;
    }
    for (std::size_t i = 0; i < want.size(); ++i)
        if (std::memcmp(&want[i], &got[i], sizeof(T)) != 0) {
            std::snprintf(why, size, "value %zu: %a != %a (%s)", i, double(got[i]), double(want[i]), ref_name.c_str());
            return false;
        }
    return true;
}

}  // namespace

namespace kairn_bench::m2a {

// The arrays are made the first time a function is checked, so that a run of the harness that
// checks none of these does not allocate them (about 0.6 GB).
bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size) {
    make_sets<double>();
    make_sets<float>();
    return e.bits == 32 ? check_typed<float>(e, why, size) : check_typed<double>(e, why, size);
}

}  // namespace kairn_bench::m2a
