// The timed functions of Packed<T, k> and the containers of soa.hpp (bench/m2_data.hpp; bench/README.md,
// "Milestone 2", second part), for double limbs (backend m2v) and float limbs (m2vf): loops over arrays
// of two-limb numbers held in structure-of-arrays form, one array per limb, as kairn::SoA<T, 2> holds
// them, in the first-level cache (KIND tp, 512 elements) and in arrays that do not fit the last-level
// cache (KIND mem, 4 Mi elements of double, 8 Mi of float: 192 MB for a loop over three two-limb
// arrays), the time per element. Compiled with the flags of packed code (-mavx2 -mfma on x86-64,
// bench/CMakeLists.txt), all of it, the scalar loops too: a client's translation unit that uses Packed
// is compiled so, and its scalar loops with it.
//
// Kernels (the operation on one element):
//   add22, mul22   z = x + y, z = x * y, two-limb operands
//   mul21          z = x * a, a of one limb
//   add11, mul11   the same loops on plain T (the leading limbs): the control on plain T
//   dot22          the sum of x * y with one accumulator (a dependent chain of two-limb sums)
//   dotw           the same with W accumulators, W = Packed<T, 2>::lanes, added in lane order at the
//                  end: the dot product of docs/tutorials/vector-loop.md, packed, and the same order of
//                  operations in scalar code
//   dot11          the sum of x0 * y0 in plain T, one accumulator
//   mix            z = x + a * b, a and b of one limb: the product a * b rounded to T, as
//                  Expansion<T, 1> computes it, then the mixed sum; Packed<T, 1> has no arithmetic, so
//                  the packed loop computes a * b in a plain loop of T first (two passes)
//   mixp           z = x + Expansion<T, 2>(a) * b: what a packed loop can write in one pass, the
//                  one-limb operand made a two-limb one (more work, and a more accurate product)
//   copy           z = x, read and written through each interface
// Variants:
//   kairn   the generated scalar kernels on the arrays of limbs: the reference of the others
//   op      Expansion<T, 2> made from the arrays through raw pointers (from_limbs), its operator, the
//           limbs stored back
//   view    the same through SoAView and its element proxy SoARef (v[i] read and assigned)
//   packed  Packed<T, 2> loaded and stored through SoAView (load, store, and the tail with
//           load_partial and store_partial)
//   aos     an array of Expansion<T, 2> (an array of structures), for scale
//   plain   the same loop on T
// Every function is checked before it is timed against BACKEND/KIND/KERNEL/kairn, byte for byte,
// on its own outputs (check() below). Compiled again with KB_SOA_SCALAR_FORM (m2_soa_scalar.cpp), the
// packed loops are in the scalar form of Packed, one lane (KAIRN_PACKED_FORM_SCALAR), as backends
// m2v1 and m2vf1, checked against m2v and m2vf.
#if !defined(KB_SOA_SCALAR_FORM)
#define KB_SOA_SCALAR_FORM 0
#endif

#include <kairn/kairn.hpp>
#include <kairn/soa.hpp>

#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#include "bench_util.hpp"
#include "m2_data.hpp"

// What the two translation units share: the arrays, made once by m2_soa.cpp, and its check.
namespace kairn_bench::m2soa {

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;

// Elements of a loop in L1, and of one that does not fit the last-level cache.
constexpr std::size_t kSmall = 512;
template <class T>
constexpr std::size_t big() {
    return sizeof(T) == 8 ? std::size_t(1) << 22 : std::size_t(1) << 23;
}

// The arrays of one limb type and one size.
template <class T>
struct Set {
    std::size_t n = 0;
    kairn::SoA<T, 2> x, y, z;         // two-limb operands and result
    kairn::SoA<T, 1> a, b, p, zp;     // one-limb operands, the products of the first pass of mix, a plain result
    std::vector<E2<T>> xe, ye, ze;    // the same x and y as arrays of Expansion<T, 2>
    T cout[2] = {0, 0};               // the result of a reduction
};

// [0] in L1, [1] in memory; made by check() (m2_soa.cpp) before the first function is run.
extern Set<double>* g64[2];
extern Set<float>* g32[2];
template <class T>
inline Set<T>& set_of(int size) {
    if constexpr (sizeof(T) == 8) {
        return *g64[size];
    } else {
        return *g32[size];
    }
}

// Where a function writes (Entry::region), and how many values of T (Entry::values).
enum Out : int { O_SOA2 = 0, O_AOS2 = 1, O_PLAIN = 2, O_COUT = 3 };

bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size);   // m2_soa.cpp

// The lanes of a timed function, for its row: W for a packed loop, 1 otherwise.
constexpr int lanes_of(const char* variant, int w) {
    const char* p = "packed";
    for (; *variant && *variant == *p; ++variant, ++p) {}
    return *variant == 0 && *p == 0 ? w : 1;
}

}  // namespace kairn_bench::m2soa

namespace {

namespace kg = kairn::gen;
using kairn_bench::m2::Entry;
using namespace kairn_bench::m2soa;

template <class T>
constexpr int W = kairn::Packed<T, 2>::lanes;

// --- The loops ----------------------------------------------------------------------------------
// Each is forced inline into its timed function (KB_SDEF), so that the loop is in that function.

#define KB_SI KAIRN_GEN_FORCEINLINE

// Raw pointers to the arrays, as a program that keeps its own arrays has them.
template <class T>
struct P {
    const T *x0, *x1, *y0, *y1, *a, *b;
    T *z0, *z1, *zp, *p;
    std::size_t n;
    explicit P(Set<T>& d)
        : x0(d.x.view().limb(0)), x1(d.x.view().limb(1)), y0(d.y.view().limb(0)), y1(d.y.view().limb(1)),
          a(d.a.view().limb(0)), b(d.b.view().limb(0)), z0(d.z.view().limb(0)), z1(d.z.view().limb(1)),
          zp(d.zp.view().limb(0)), p(d.p.view().limb(0)), n(d.n) {}
};
template <class T>
KB_SI E2<T> load2(const T* l0, const T* l1, std::size_t i) {
    const T l[2] = {l0[i], l1[i]};
    return E2<T>::from_limbs(l);
}
template <class T>
KB_SI void store2(T* l0, T* l1, std::size_t i, const E2<T>& v) {
    l0[i] = v.limb[0];
    l1[i] = v.limb[1];
}

// The packed loop over the views, with its tail: z = f(i, count) for count lanes.
template <class T, class F>
KB_SI void packed_loop(const kairn::SoAView<T, 2>& z, std::size_t n, F f) {
    std::size_t i = 0;
    for (; i + W<T> <= n; i += W<T>) z.store(i, f(i, W<T>));
    if (i < n) {
        const int rest = int(n - i);
        z.store_partial(i, f(i, rest), rest);
    }
}
template <class T>
KB_SI kairn::Packed<T, 2> load2p(const kairn::SoAView<const T, 2>& v, std::size_t i, int count) {
    return count == W<T> ? v.load(i) : v.load_partial(i, count);
}
template <class T>
KB_SI kairn::Packed<T, 1> load1p(const kairn::SoAView<const T, 1>& v, std::size_t i, int count) {
    return count == W<T> ? v.load(i) : v.load_partial(i, count);
}

// add22, mul22
#define KB_BINARY(NAME, OP, KERNEL)                                                                \
    template <class T>                                                                             \
    KB_SI void NAME##_kairn(Set<T>& d) {                                                           \
        const P<T> r(d);                                                                           \
        for (std::size_t i = 0; i < r.n; ++i) kg::KERNEL(r.x0[i], r.x1[i], r.y0[i], r.y1[i], r.z0[i], r.z1[i]); \
    }                                                                                              \
    template <class T>                                                                             \
    KB_SI void NAME##_op(Set<T>& d) {                                                              \
        const P<T> r(d);                                                                           \
        for (std::size_t i = 0; i < r.n; ++i) store2(r.z0, r.z1, i, load2(r.x0, r.x1, i) OP load2(r.y0, r.y1, i)); \
    }                                                                                              \
    template <class T>                                                                             \
    KB_SI void NAME##_view(Set<T>& d) {                                                            \
        const kairn::SoAView<const T, 2> x = d.x.view(), y = d.y.view();                           \
        const kairn::SoAView<T, 2> z = d.z.view();                                                 \
        for (std::size_t i = 0; i < d.n; ++i) {                                                    \
            const E2<T> u = x[i], v = y[i];                                                        \
            z[i] = u OP v;                                                                         \
        }                                                                                          \
    }                                                                                              \
    template <class T>                                                                             \
    KB_SI void NAME##_packed(Set<T>& d) {                                                          \
        const kairn::SoAView<const T, 2> x = d.x.view(), y = d.y.view();                           \
        packed_loop<T>(d.z.view(), d.n, [&](std::size_t i, int c) { return load2p(x, i, c) OP load2p(y, i, c); }); \
    }                                                                                              \
    template <class T>                                                                             \
    KB_SI void NAME##_aos(Set<T>& d) {                                                             \
        const E2<T>* x = d.xe.data();                                                              \
        const E2<T>* y = d.ye.data();                                                              \
        E2<T>* z = d.ze.data();                                                                    \
        for (std::size_t i = 0; i < d.n; ++i) z[i] = x[i] OP y[i];                                 \
    }
KB_BINARY(add22, +, add_2_2_full)
KB_BINARY(mul22, *, mul_2_2_full)

// add11, mul11: plain T, and the same with the one-limb kernels.
#define KB_PLAIN(NAME, OP, KERNEL)                                                                 \
    template <class T>                                                                             \
    KB_SI void NAME##_kairn(Set<T>& d) {                                                           \
        const P<T> r(d);                                                                           \
        for (std::size_t i = 0; i < r.n; ++i) kg::KERNEL(r.x0[i], r.y0[i], r.zp[i]);               \
    }                                                                                              \
    template <class T>                                                                             \
    KB_SI void NAME##_plain(Set<T>& d) {                                                           \
        const P<T> r(d);                                                                           \
        for (std::size_t i = 0; i < r.n; ++i) r.zp[i] = r.x0[i] OP r.y0[i];                        \
    }
KB_PLAIN(add11, +, add_1_1)
KB_PLAIN(mul11, *, mul_1_1)

// mul21: z = x * a.
template <class T>
KB_SI void mul21_kairn(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) kg::mul_2_1_full(r.x0[i], r.x1[i], r.a[i], r.z0[i], r.z1[i]);
}
template <class T>
KB_SI void mul21_op(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) store2(r.z0, r.z1, i, load2(r.x0, r.x1, i) * r.a[i]);
}
template <class T>
KB_SI void mul21_view(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view();
    const kairn::SoAView<const T, 1> a = d.a.view();
    const kairn::SoAView<T, 2> z = d.z.view();
    for (std::size_t i = 0; i < d.n; ++i) {
        const E2<T> u = x[i];
        const E1<T> v = a[i];
        z[i] = u * v;
    }
}
template <class T>
KB_SI void mul21_packed(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view();
    const kairn::SoAView<const T, 1> a = d.a.view();
    packed_loop<T>(d.z.view(), d.n, [&](std::size_t i, int c) { return load2p(x, i, c) * load1p(a, i, c); });
}

// dot22: one accumulator.
template <class T>
KB_SI void dot22_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0 = 0, s1 = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T p0, p1;
        kg::mul_2_2_full(r.x0[i], r.x1[i], r.y0[i], r.y1[i], p0, p1);
        kg::add_2_2_full(s0, s1, p0, p1, s0, s1);
    }
    d.cout[0] = s0;
    d.cout[1] = s1;
}
template <class T>
KB_SI void dot22_op(Set<T>& d) {
    const P<T> r(d);
    E2<T> s;
    for (std::size_t i = 0; i < r.n; ++i) s = s + load2(r.x0, r.x1, i) * load2(r.y0, r.y1, i);
    d.cout[0] = s.limb[0];
    d.cout[1] = s.limb[1];
}
template <class T>
KB_SI void dot22_view(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view(), y = d.y.view();
    E2<T> s;
    for (std::size_t i = 0; i < d.n; ++i) {
        const E2<T> u = x[i], v = y[i];
        s = s + u * v;
    }
    d.cout[0] = s.limb[0];
    d.cout[1] = s.limb[1];
}

// dotw: the dot product of docs/tutorials/vector-loop.md (docs/examples/cpp/packed_dot.cpp, dot()),
// written there for double and here for T, unchanged otherwise: W products at a time, each lane with
// its own sum, then the lanes added in the order 0, 1, ..., W - 1.
template <class T>
KB_SI E2<T> tutorial_dot(kairn::SoAView<const T, 2> x, kairn::SoAView<const T, 2> y) {
    using Pack = kairn::Packed<T, 2>;
    using Number = E2<T>;
    constexpr int W = Pack::lanes;   // 4 with AVX2, 2 with NEON, 1 without either (8 and 4 for float)
    Pack sum;                        // zero in every lane
    std::size_t i = 0;
    for (; i + W <= x.size(); i += W) sum = sum + x.load(i) * y.load(i);
    if (i < x.size()) {              // the last x.size() % W elements; zero in the other lanes
        const int rest = int(x.size() - i);
        sum = sum + x.load_partial(i, rest) * y.load_partial(i, rest);
    }
    Number total;
    for (int lane = 0; lane < W; ++lane) total = total + sum.lane(lane);
    return total;
}
template <class T>
KB_SI void dotw_packed(Set<T>& d) {
    const E2<T> s = tutorial_dot<T>(d.x.view(), d.y.view());
    d.cout[0] = s.limb[0];
    d.cout[1] = s.limb[1];
}
// The same order of operations with the scalar kernels: W sums, then the lanes in order.
template <class T>
KB_SI void dotw_kairn(Set<T>& d) {
    const P<T> r(d);
    T s0[W<T>], s1[W<T>];
    for (int l = 0; l < W<T>; ++l) s0[l] = s1[l] = 0;
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) {
            T p0, p1;
            kg::mul_2_2_full(r.x0[i + l], r.x1[i + l], r.y0[i + l], r.y1[i + l], p0, p1);
            kg::add_2_2_full(s0[l], s1[l], p0, p1, s0[l], s1[l]);
        }
    for (int l = 0; i + std::size_t(l) < r.n; ++l) {
        T p0, p1;
        kg::mul_2_2_full(r.x0[i + l], r.x1[i + l], r.y0[i + l], r.y1[i + l], p0, p1);
        kg::add_2_2_full(s0[l], s1[l], p0, p1, s0[l], s1[l]);
    }
    T t0 = 0, t1 = 0;
    for (int l = 0; l < W<T>; ++l) kg::add_2_2_full(t0, t1, s0[l], s1[l], t0, t1);
    d.cout[0] = t0;
    d.cout[1] = t1;
}
// The same in scalar code with Expansion<T, 2>, W accumulators.
template <class T>
KB_SI void dotw_op(Set<T>& d) {
    const P<T> r(d);
    E2<T> s[W<T>];
    std::size_t i = 0;
    for (; i + W<T> <= r.n; i += W<T>)
        for (int l = 0; l < W<T>; ++l) s[l] = s[l] + load2(r.x0, r.x1, i + l) * load2(r.y0, r.y1, i + l);
    for (int l = 0; i + std::size_t(l) < r.n; ++l) s[l] = s[l] + load2(r.x0, r.x1, i + l) * load2(r.y0, r.y1, i + l);
    E2<T> t;
    for (int l = 0; l < W<T>; ++l) t = t + s[l];
    d.cout[0] = t.limb[0];
    d.cout[1] = t.limb[1];
}

// dot11: plain T, one accumulator.
template <class T>
KB_SI void dot11_kairn(Set<T>& d) {
    const P<T> r(d);
    T s = 0;
    for (std::size_t i = 0; i < r.n; ++i) {
        T q;
        kg::mul_1_1(r.x0[i], r.y0[i], q);
        kg::add_1_1(s, q, s);
    }
    d.cout[0] = s;
}
template <class T>
KB_SI void dot11_plain(Set<T>& d) {
    const P<T> r(d);
    T s = 0;
    for (std::size_t i = 0; i < r.n; ++i) s = s + r.x0[i] * r.y0[i];
    d.cout[0] = s;
}

// mix: z = x + a * b, the product of the one-limb a and b rounded to T.
template <class T>
KB_SI void mix_kairn(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) {
        T q;
        kg::mul_1_1(r.a[i], r.b[i], q);
        kg::add_2_1_full(r.x0[i], r.x1[i], q, r.z0[i], r.z1[i]);
    }
}
template <class T>
KB_SI void mix_op(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) store2(r.z0, r.z1, i, load2(r.x0, r.x1, i) + E1<T>(r.a[i]) * E1<T>(r.b[i]));
}
// Packed<T, 1> has no product: the products in a plain loop of T first, then the packed sums.
template <class T>
KB_SI void mix_packed(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) r.p[i] = r.a[i] * r.b[i];
    const kairn::SoAView<const T, 2> x = d.x.view();
    const kairn::SoAView<const T, 1> q = d.p.view();
    packed_loop<T>(d.z.view(), d.n, [&](std::size_t i, int c) { return load2p(x, i, c) + load1p(q, i, c); });
}

// mixp: z = x + Expansion<T, 2>(a) * b, in one pass.
template <class T>
KB_SI void mixp_kairn(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) {
        T a0, a1, q0, q1;
        kg::make_2(r.a[i], a0, a1);
        kg::mul_2_1_full(a0, a1, r.b[i], q0, q1);
        kg::add_2_2_full(r.x0[i], r.x1[i], q0, q1, r.z0[i], r.z1[i]);
    }
}
template <class T>
KB_SI void mixp_op(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) store2(r.z0, r.z1, i, load2(r.x0, r.x1, i) + E2<T>(r.a[i]) * r.b[i]);
}
template <class T>
KB_SI void mixp_packed(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view();
    const kairn::SoAView<const T, 1> a = d.a.view(), b = d.b.view();
    packed_loop<T>(d.z.view(), d.n, [&](std::size_t i, int c) {
        return load2p(x, i, c) + kairn::Packed<T, 2>(load1p(a, i, c)) * load1p(b, i, c);
    });
}

// copy: z = x.
template <class T>
KB_SI void copy_kairn(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) {
        r.z0[i] = r.x0[i];
        r.z1[i] = r.x1[i];
    }
}
template <class T>
KB_SI void copy_op(Set<T>& d) {
    const P<T> r(d);
    for (std::size_t i = 0; i < r.n; ++i) store2(r.z0, r.z1, i, load2(r.x0, r.x1, i));
}
template <class T>
KB_SI void copy_view(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view();
    const kairn::SoAView<T, 2> z = d.z.view();
    for (std::size_t i = 0; i < d.n; ++i) z[i] = x[i];
}
template <class T>
KB_SI void copy_packed(Set<T>& d) {
    const kairn::SoAView<const T, 2> x = d.x.view();
    packed_loop<T>(d.z.view(), d.n, [&](std::size_t i, int c) { return load2p(x, i, c); });
}

}  // namespace

// --- The timed functions ------------------------------------------------------------------------
// X(B, SUF, T, KIND, SIZE, KERNEL, VARIANT, OUT, VALUES): SIZE 0 (L1, kind tp) or 1 (memory, kind
// mem); VALUES the values of T written to OUT per element (2 for two limbs), or, negative, for a
// reduction (OUT O_COUT), minus the number of values.

#define KB_VSIZE(X, B, SUF, T, KIND, SIZE)                                                         \
    X(B, SUF, T, KIND, SIZE, add22, kairn, O_SOA2, 2)                                              \
    X(B, SUF, T, KIND, SIZE, add22, op, O_SOA2, 2)                                                 \
    X(B, SUF, T, KIND, SIZE, add22, view, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, add22, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, add22, aos, O_AOS2, 2)                                                \
    X(B, SUF, T, KIND, SIZE, add11, kairn, O_PLAIN, 1)                                             \
    X(B, SUF, T, KIND, SIZE, add11, plain, O_PLAIN, 1)                                             \
    X(B, SUF, T, KIND, SIZE, mul22, kairn, O_SOA2, 2)                                              \
    X(B, SUF, T, KIND, SIZE, mul22, op, O_SOA2, 2)                                                 \
    X(B, SUF, T, KIND, SIZE, mul22, view, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, mul22, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, mul22, aos, O_AOS2, 2)                                                \
    X(B, SUF, T, KIND, SIZE, mul11, kairn, O_PLAIN, 1)                                             \
    X(B, SUF, T, KIND, SIZE, mul11, plain, O_PLAIN, 1)                                             \
    X(B, SUF, T, KIND, SIZE, mul21, kairn, O_SOA2, 2)                                              \
    X(B, SUF, T, KIND, SIZE, mul21, op, O_SOA2, 2)                                                 \
    X(B, SUF, T, KIND, SIZE, mul21, view, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, mul21, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, dot22, kairn, O_COUT, -2)                                             \
    X(B, SUF, T, KIND, SIZE, dot22, op, O_COUT, -2)                                                \
    X(B, SUF, T, KIND, SIZE, dot22, view, O_COUT, -2)                                              \
    X(B, SUF, T, KIND, SIZE, dotw, kairn, O_COUT, -2)                                              \
    X(B, SUF, T, KIND, SIZE, dotw, op, O_COUT, -2)                                                 \
    X(B, SUF, T, KIND, SIZE, dotw, packed, O_COUT, -2)                                             \
    X(B, SUF, T, KIND, SIZE, dot11, kairn, O_COUT, -1)                                             \
    X(B, SUF, T, KIND, SIZE, dot11, plain, O_COUT, -1)                                             \
    X(B, SUF, T, KIND, SIZE, mix, kairn, O_SOA2, 2)                                                \
    X(B, SUF, T, KIND, SIZE, mix, op, O_SOA2, 2)                                                   \
    X(B, SUF, T, KIND, SIZE, mix, packed, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, mixp, kairn, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, mixp, op, O_SOA2, 2)                                                  \
    X(B, SUF, T, KIND, SIZE, mixp, packed, O_SOA2, 2)                                              \
    X(B, SUF, T, KIND, SIZE, copy, kairn, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, copy, op, O_SOA2, 2)                                                  \
    X(B, SUF, T, KIND, SIZE, copy, view, O_SOA2, 2)                                                \
    X(B, SUF, T, KIND, SIZE, copy, packed, O_SOA2, 2)

// The packed loops alone, in the scalar form of Packed: dotw with one lane is one accumulator, and is
// checked against dot22.
#define KB_VSIZE_SCALAR(X, B, SUF, T, KIND, SIZE)                                                  \
    X(B, SUF, T, KIND, SIZE, add22, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, mul22, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, mul21, packed, O_SOA2, 2)                                             \
    X(B, SUF, T, KIND, SIZE, dotw, packed, O_COUT, -2)                                             \
    X(B, SUF, T, KIND, SIZE, mix, packed, O_SOA2, 2)                                               \
    X(B, SUF, T, KIND, SIZE, mixp, packed, O_SOA2, 2)                                              \
    X(B, SUF, T, KIND, SIZE, copy, packed, O_SOA2, 2)

#if KB_SOA_SCALAR_FORM
#define KB_VLIST(X)                                                                                \
    KB_VSIZE_SCALAR(X, "m2v1", v1_64, double, tp, 0) KB_VSIZE_SCALAR(X, "m2v1", v1_64, double, mem, 1) \
    KB_VSIZE_SCALAR(X, "m2vf1", v1_32, float, tp, 0) KB_VSIZE_SCALAR(X, "m2vf1", v1_32, float, mem, 1)
#define KB_SOA_TABLE m2_soa_scalar_entries
#else
#define KB_VLIST(X)                                                                                \
    KB_VSIZE(X, "m2v", v64, double, tp, 0) KB_VSIZE(X, "m2v", v64, double, mem, 1)                 \
    KB_VSIZE(X, "m2vf", v32, float, tp, 0) KB_VSIZE(X, "m2vf", v32, float, mem, 1)
#define KB_SOA_TABLE m2_soa_entries
#endif

#define KB_SDEF(B, SUF, T, KIND, SIZE, KERNEL, VAR, OUT, VALUES)                                   \
    extern "C" KB_NOINLINE void kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR(void*) { KERNEL##_##VAR<T>(set_of<T>(SIZE)); }
KB_VLIST(KB_SDEF)

#define KB_SROW(B, SUF, T, KIND, SIZE, KERNEL, VAR, OUT, VALUES)                                   \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_m2_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)),  \
     lanes_of(#VAR, W<T>), int(SIZE ? big<T>() : kSmall), OUT, VALUES, &kairn_bench::m2soa::check},

namespace kairn_bench::m2 {

const Entry KB_SOA_TABLE[] = {
    KB_VLIST(KB_SROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};

}  // namespace kairn_bench::m2

#if !KB_SOA_SCALAR_FORM

namespace {

template <class T>
void fill(Set<T>& d, std::size_t n, std::uint64_t seed) {
    kairn_bench::util::Rng g{seed};
    d.n = n;
    d.x = kairn::SoA<T, 2>(n);
    d.y = kairn::SoA<T, 2>(n);
    d.z = kairn::SoA<T, 2>(n);
    d.a = kairn::SoA<T, 1>(n);
    d.b = kairn::SoA<T, 1>(n);
    d.p = kairn::SoA<T, 1>(n);
    d.zp = kairn::SoA<T, 1>(n);
    d.xe.assign(n, E2<T>());
    d.ye.assign(n, E2<T>());
    d.ze.assign(n, E2<T>());
    // Two-limb numbers +-[1, 2) 2^k, k in [-8, 8], the second limb about u times the first (as
    // m2.cpp makes them); one-limb factors near 1, so that the products stay in range.
    auto number = [&g]() {
        const double s = g.sign();
        const double m = 1.0 + g.u01();
        const T a = T(s * std::ldexp(m, g.range(-8, 8)));
        const T b = T(double(a) * g.sym() * std::ldexp(1.0, -std::numeric_limits<T>::digits));
        std::array<T, 2> l{};
        kg::fast_two_sum(a, b, l[0], l[1]);
        return E2<T>::from_limbs(l.data());
    };
    for (std::size_t i = 0; i < n; ++i) {
        d.x[i] = number();
        d.y[i] = number();
        d.a.set(i, E1<T>(T(std::exp2(0.25 * g.sym()))));
        d.b.set(i, E1<T>(T(std::exp2(0.25 * g.sym()))));
        d.xe[i] = d.x.get(i);
        d.ye[i] = d.y.get(i);
    }
}

template <class T>
void make_sets(Set<T>** sets) {
    if (sets[0]) return;
    sets[0] = new Set<T>();
    sets[1] = new Set<T>();
    fill(*sets[0], kSmall, sizeof(T) == 8 ? 101 : 102);
    fill(*sets[1], big<T>(), sizeof(T) == 8 ? 103 : 104);
}

template <class T>
void clear(Set<T>& d) {
    const auto wipe = [](void* p, std::size_t bytes) { std::memset(p, 0xff, bytes); };
    wipe(d.z.view().limb(0), d.n * sizeof(T));
    wipe(d.z.view().limb(1), d.n * sizeof(T));
    wipe(d.zp.view().limb(0), d.n * sizeof(T));
    wipe(d.ze.data(), d.n * sizeof(E2<T>));
    wipe(d.cout, sizeof d.cout);
}

// The values written, from the row's VALUES.
template <class T>
int values_of(int size, int values) {
    return values < 0 ? -values : values * int(set_of<T>(size).n);
}

// The values a function wrote, in one order for every layout: the first limbs, then the second.
template <class T>
std::vector<T> read(Set<T>& d, int out, int values) {
    std::vector<T> v;
    v.reserve(std::size_t(values));
    switch (out) {
        case O_SOA2:
            for (int j = 0; j < 2; ++j) v.insert(v.end(), d.z.view().limb(j), d.z.view().limb(j) + d.n);
            break;
        case O_AOS2:
            for (int j = 0; j < 2; ++j)
                for (std::size_t i = 0; i < d.n; ++i) v.push_back(d.ze[i].limb[j]);
            break;
        case O_PLAIN: v.insert(v.end(), d.zp.view().limb(0), d.zp.view().limb(0) + d.n); break;
        default: v.insert(v.end(), d.cout, d.cout + values); break;
    }
    return v;
}

const Entry* find_entry(const std::string& name) {
    for (const Entry* t : {kairn_bench::m2::m2_soa_entries, kairn_bench::m2::m2_soa_scalar_entries})
        for (const Entry* e = t; e->name; ++e)
            if (name == e->name) return e;
    return nullptr;
}

template <class T>
bool check_typed(const Entry& e, char* why, std::size_t size) {
    // The reference: BACKEND/KIND/KERNEL/kairn, the backend of the scalar form taken as the native
    // one, and dotw of the scalar form, one accumulator, checked against dot22.
    const std::string name = e.name;
    const std::string own = name.substr(0, name.find('/'));
    std::string backend = own == "m2v1" ? "m2v" : own == "m2vf1" ? "m2vf" : own;
    std::string path = name.substr(name.find('/'));
    path = path.substr(0, path.rfind('/'));
    if (backend != own && path.find("/dotw") != std::string::npos) path.replace(path.find("/dotw"), 5, "/dot22");
    const std::string ref_name = backend + path + "/kairn";
    const Entry* ref = find_entry(ref_name);
    if (!ref) {
        std::snprintf(why, size, "no reference %s", ref_name.c_str());
        return false;
    }
    if (ref == &e) return true;
    const int sz = e.ops == int(kSmall) ? 0 : 1;
    Set<T>& d = set_of<T>(sz);
    const int nv = values_of<T>(sz, e.values);
    if (nv != values_of<T>(sz, ref->values)) {
        std::snprintf(why, size, "not the same number of values as %s", ref_name.c_str());
        return false;
    }
    clear(d);
    ref->fn(nullptr);
    const std::vector<T> want = read(d, ref->region, nv);
    clear(d);
    e.fn(nullptr);
    const std::vector<T> got = read(d, e.region, nv);
    for (std::size_t i = 0; i < want.size(); ++i)
        if (std::memcmp(&want[i], &got[i], sizeof(T)) != 0) {
            std::snprintf(why, size, "value %zu: %a != %a (%s)", i, double(got[i]), double(want[i]), ref_name.c_str());
            return false;
        }
    // Every value finite: the arrays were made so that nothing overflows.
    for (const T v : got)
        if (!std::isfinite(v)) {
            std::snprintf(why, size, "a value is not finite");
            return false;
        }
    return true;
}

}  // namespace

namespace kairn_bench::m2soa {

Set<double>* g64[2] = {nullptr, nullptr};
Set<float>* g32[2] = {nullptr, nullptr};

// The arrays are made the first time a function is checked, so that a run of the harness that
// checks none of these does not allocate them.
bool check(const kairn_bench::m2::Entry& e, char* why, std::size_t size) {
    make_sets(g64);
    make_sets(g32);
    return e.bits == 32 ? check_typed<float>(e, why, size) : check_typed<double>(e, why, size);
}

}  // namespace kairn_bench::m2soa

#endif  // !KB_SOA_SCALAR_FORM
