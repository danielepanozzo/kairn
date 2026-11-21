// The containers of include/kairn/soa.hpp: SoA<T, k>, SoAView<T, k>, SoAView<const T, k> and the
// proxy SoARef, for T = double and float and k = 1 and 2.
//
// - An element read is the value written, for every index of arrays of every length around the
//   lanes of Packed (0, 1, W - 1, W, W + 1, 2W - 1, 2W + 1, 37): read through the proxy, get(),
//   a const view and load(), it has exactly the limbs of Expansion<T, k>::from_limbs of the limbs
//   written (for one limb, the limbs written), and the value written (a zero limb may change sign);
//   the corpus has zeros of both signs, subnormal numbers, the largest finite number, the
//   infinities and NaN.
// - The tail: load(i) and store(i, p) at i = 0, W, 2W, ..., then load_partial and store_partial
//   on the last N % W elements, read and write exactly the N elements, and fill the other lanes.
// - Views over the program's own arrays (std::vector, plain arrays): writes through the view are in
//   the arrays, limb(j) is the array, subview() a part of it; at k = 1, a view of a plain array.
// - What must be true of the types: views are trivially copyable; a view of T converts to a view
//   of const T and not back; nothing writes through a view of const T or a const SoA (the
//   compile-fail cases of tests/api/reject.cpp check the same with the compiler's messages).
// - Allocations, counted by the global operator new of this program: views, proxies, element
//   access, load and store allocate nothing; an SoA allocates once in each constructor that takes
//   a size, its copy and resize, and never otherwise; its arrays start at multiples of 64 bytes.
//
// The check of an element that is not canonical, with KAIRN_CHECKS 1, is in tests/api/checks.cpp.
#include <kairn/kairn.hpp>
#include <kairn/soa.hpp>

#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <new>
#include <type_traits>
#include <utility>
#include <vector>

// Every allocation of the program, counted. GCC pairs the std::free of the replaced operator delete
// with the replaced operator new it inlines, and reports a mismatch that is not one.
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic ignored "-Wmismatched-new-delete"
#endif
// MSVC compares the annotations of a replaced operator new with those of its declaration (C28251).
#if defined(_MSC_VER)
#pragma warning(disable : 28251)
#endif
namespace {
long allocations = 0;
}
void* operator new(std::size_t n) {
    ++allocations;
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t n) {
    ++allocations;
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void* operator new(std::size_t n, std::align_val_t a) {
    ++allocations;
    const std::size_t al = static_cast<std::size_t>(a);
    // aligned_alloc wants a size that is a multiple of the alignment.
    const std::size_t size = (n + al - 1) / al * al;
#if defined(_MSC_VER)
    if (void* p = _aligned_malloc(size ? size : al, al)) return p;
#else
    if (void* p = std::aligned_alloc(al, size ? size : al)) return p;
#endif
    throw std::bad_alloc();
}
void* operator new[](std::size_t n, std::align_val_t a) { return operator new(n, a); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
#if defined(_MSC_VER)
void operator delete(void* p, std::align_val_t) noexcept { _aligned_free(p); }
void operator delete[](void* p, std::align_val_t) noexcept { _aligned_free(p); }
void operator delete(void* p, std::size_t, std::align_val_t) noexcept { _aligned_free(p); }
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept { _aligned_free(p); }
#else
void operator delete(void* p, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void* p, std::align_val_t) noexcept { std::free(p); }
void operator delete(void* p, std::size_t, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept { std::free(p); }
#endif

namespace {

long failures = 0, checked = 0;
void expect(bool ok, const char* what, const char* type = "", long index = -1) {
    ++checked;
    if (ok) return;
    ++failures;
    if (failures <= 20) std::printf("FAILED %s (%s, element %ld)\n", what, type, index);
}

template <class T>
using Bits = std::conditional_t<sizeof(T) == 8, std::uint64_t, std::uint32_t>;
template <class T>
bool same_limb(T a, T b) {
    return std::bit_cast<Bits<T>>(a) == std::bit_cast<Bits<T>>(b);
}
template <class T, int K>
bool same(const kairn::Expansion<T, K>& a, const kairn::Expansion<T, K>& b) {
    for (int j = 0; j < K; ++j)
        if (!same_limb(a.limb[j], b.limb[j])) return false;
    return true;
}
// The same value: every limb equal, or both NaN.
template <class T, int K>
bool same_value(const kairn::Expansion<T, K>& a, const kairn::Expansion<T, K>& b) {
    for (int j = 0; j < K; ++j)
        if (!(a.limb[j] == b.limb[j] || (a.limb[j] != a.limb[j] && b.limb[j] != b.limb[j]))) return false;
    return true;
}
template <class T>
const char* type_name() {
    return sizeof(T) == 8 ? "double" : "float";
}

// Canonical numbers of every kind, written into the containers in turn.
template <class T, int K>
std::vector<kairn::Expansion<T, K>> corpus() {
    using L = std::numeric_limits<T>;
    const T values[] = {T(0), -T(0), L::denorm_min(), -(L::min)(), T(1), T(-1.5), T(3.25), (L::max)(), -(L::max)(),
                        L::infinity(), -L::infinity(), L::quiet_NaN()};
    std::vector<kairn::Expansion<T, K>> c;
    for (T a : values) c.push_back(kairn::Expansion<T, K>(a));
    if constexpr (K == 2) {
        const T u = L::epsilon() / 2;
        const T pairs[][2] = {{T(1), u}, {T(1), -u / 2}, {T(-2.25), u / 8}, {T(0), -T(0)}, {T(1.5), -T(0)},
                              {L::infinity(), -T(0)}, {(L::max)(), std::ldexp(T(1), L::max_exponent - L::digits - 2)}};
        for (const auto& p : pairs) {
            kairn::Expansion<T, 2> x;  // written directly, so that a limb -0 stays -0
            x.limb[0] = p[0];
            x.limb[1] = p[1];
            c.push_back(x);
        }
    }
    return c;
}

template <class T, int K>
kairn::Expansion<T, K> expected_read(const kairn::Expansion<T, K>& x) {
    return kairn::Expansion<T, K>::from_limbs(x.limb);
}

// Every element written through the proxy, read through every path, for arrays of length n.
template <class T, int K>
void elements(std::size_t n) {
    using E = kairn::Expansion<T, K>;
    using P = kairn::Packed<T, K>;
    constexpr int W = P::lanes;
    const std::vector<E> c = corpus<T, K>();
    kairn::SoA<T, K> s(n);
    for (std::size_t i = 0; i < n; ++i) expect(same(E(s[i]), E()), "a new SoA is zero", type_name<T>(), long(i));
    for (std::size_t i = 0; i < n; ++i) s[i] = c[i % c.size()];
    const kairn::SoA<T, K>& cs = s;
    const kairn::SoAView<const T, K> cv = s;
    for (std::size_t i = 0; i < n; ++i) {
        const E& x = c[i % c.size()];
        const E want = expected_read(x);
        expect(same(E(s[i]), want), "the proxy reads as from_limbs", type_name<T>(), long(i));
        expect(same(s.get(i), want), "get reads as from_limbs", type_name<T>(), long(i));
        expect(same(E(cs[i]), want), "a const SoA reads as from_limbs", type_name<T>(), long(i));
        expect(same(cv.get(i), want), "a const view reads as from_limbs", type_name<T>(), long(i));
        expect(same_value(E(cv[i]), x), "the value written is read", type_name<T>(), long(i));
        // The limbs in the arrays are those written, bit for bit.
        for (int j = 0; j < K; ++j)
            expect(same_limb(s.limb(j)[i], x.limb[j]), "the arrays hold the limbs written", type_name<T>(), long(i));
        if constexpr (K == 1) expect(same(E(s[i]), x), "one limb reads bit for bit", type_name<T>(), long(i));
    }
    // load: every full group of W elements, then the tail with fill in the other lanes.
    const E fill = E(T(-0.5));
    std::size_t i = 0;
    for (; i + W <= n; i += W) {
        const P p = cv.load(i);
        for (int l = 0; l < W; ++l)
            expect(same(p.lane(l), expected_read(c[(i + std::size_t(l)) % c.size()])), "load", type_name<T>(), long(i) + l);
    }
    if (i < n) {
        const int rest = int(n - i);
        const P p = cv.load_partial(i, rest, fill);
        for (int l = 0; l < W; ++l)
            expect(same(p.lane(l), l < rest ? expected_read(c[(i + std::size_t(l)) % c.size()]) : expected_read(fill)),
                   "load_partial", type_name<T>(), long(i) + l);
    }
    // store into a second SoA, with the tail rule, then every element read back; nothing beyond n.
    kairn::SoA<T, K> t(n + 3, E(T(7)));
    kairn::SoAView<T, K> tv = t.view().subview(0, n);
    for (i = 0; i + W <= n; i += W) tv.store(i, cv.load(i));
    if (i < n) tv.store_partial(i, cv.load_partial(i, int(n - i), fill), int(n - i));
    for (std::size_t k = 0; k < n; ++k) expect(same(t.get(k), s.get(k)), "store and store_partial", type_name<T>(), long(k));
    for (std::size_t k = n; k < n + 3; ++k) expect(same(t.get(k), E(T(7))), "nothing written beyond the end", type_name<T>(), long(k));
}

// Views over arrays of the program.
template <class T>
void program_arrays() {
    using E2 = kairn::Expansion<T, 2>;
    using E1 = kairn::Expansion<T, 1>;
    std::vector<T> hi(10, T(1)), lo(10, T(0));
    kairn::SoAView<T, 2> v(hi.data(), lo.data(), hi.size());
    expect(v.size() == 10 && !v.empty() && v.limb(0) == hi.data() && v.limb(1) == lo.data(), "a view of vectors",
           type_name<T>());
    const T u = std::numeric_limits<T>::epsilon() / 2;
    v[3] = E2(T(1)) + u;  // (1, u)
    expect(hi[3] == T(1) && lo[3] == u, "a write through the view is in the arrays", type_name<T>(), 3);
    v.set(4, E2(T(-2)));
    expect(hi[4] == T(-2) && lo[4] == 0, "set writes the arrays", type_name<T>(), 4);
    v[5] = v[3];  // the value, not the reference
    expect(hi[5] == T(1) && lo[5] == u && same(E2(v[3]), E2(v[5])), "an element assigned from another", type_name<T>(), 5);
    const kairn::SoAView<T, 2> part = v.subview(3, 4);
    expect(part.size() == 4 && part.limb(0) == hi.data() + 3 && same(part.get(0), v.get(3)), "subview", type_name<T>());
    T plain[7] = {T(1), T(2), T(3), T(4), T(5), T(6), T(7)};
    const kairn::SoAView<T, 1> one(plain, 7);
    for (std::size_t i = 0; i < 7; ++i) expect(same(one.get(i), E1(plain[i])), "a view of a plain array", type_name<T>(), long(i));
    one[6] = E1(T(-1));
    expect(plain[6] == T(-1), "a write through a view of a plain array", type_name<T>(), 6);
    const kairn::SoAView<T, 1> none;
    expect(none.size() == 0 && none.empty() && none.limb(0) == nullptr, "an empty view", type_name<T>());
}

// The types.
template <class V, class X>
concept can_set = requires(V v, X x) { v.set(0, x); };
template <class V, class P>
concept can_store = requires(V v, P p) { v.store(0, p); };
template <class T, int K>
constexpr bool types() {
    using V = kairn::SoAView<T, K>;
    using C = kairn::SoAView<const T, K>;
    using E = kairn::Expansion<T, K>;
    using P = kairn::Packed<T, K>;
    return std::is_trivially_copyable_v<V> && std::is_trivially_copyable_v<C> && std::is_convertible_v<V, C> &&
           !std::is_convertible_v<C, V> && !std::is_constructible_v<V, C> && std::is_convertible_v<kairn::SoA<T, K>&, V> &&
           std::is_convertible_v<const kairn::SoA<T, K>&, C> && !std::is_convertible_v<const kairn::SoA<T, K>&, V> &&
           std::is_assignable_v<kairn::SoARef<T, K>, E> && !std::is_assignable_v<kairn::SoARef<const T, K>, E> &&
           !std::is_assignable_v<kairn::SoARef<const T, K>, kairn::SoARef<const T, K>> &&
           std::is_convertible_v<kairn::SoARef<const T, K>, E> && can_set<V, E> && !can_set<C, E> && can_store<V, P> &&
           !can_store<C, P> &&
           std::is_same_v<decltype(std::declval<const kairn::SoA<T, K>&>()[0]), kairn::SoARef<const T, K>> &&
           std::is_nothrow_move_constructible_v<kairn::SoA<T, K>> && std::is_nothrow_move_assignable_v<kairn::SoA<T, K>> &&
           !std::is_nothrow_constructible_v<kairn::SoA<T, K>, std::size_t> &&
           std::is_nothrow_default_constructible_v<kairn::SoA<T, K>>;
}
static_assert(types<double, 1>() && types<double, 2>() && types<float, 1>() && types<float, 2>());

// Allocations, and the alignment of the arrays of an SoA.
template <class T, int K>
void allocation() {
    using E = kairn::Expansion<T, K>;
    using P = kairn::Packed<T, K>;
    constexpr int W = P::lanes;
    T a0[40] = {}, a1[40] = {};
    long before = allocations;
    {
        kairn::SoAView<T, K> v;
        if constexpr (K == 1) v = kairn::SoAView<T, K>(a0, 40);
        else v = kairn::SoAView<T, K>(a0, a1, 40);
        const kairn::SoAView<const T, K> c = v;
        kairn::SoAView<T, K> copy = v;
        for (std::size_t i = 0; i < 40; ++i) {
            copy[i] = E(T(i));
            v.set(i, c.get(i));
        }
        P p = c.load(0);
        p = kairn::select(p < c.load_partial(W, 3), p, c.load_partial(W, 3));
        v.store(8, p);
        v.store_partial(0, p, 2);
        const E e = v[1];
        v[2] = e;
        (void)v.subview(1, 2);
    }
    expect(allocations == before, "a view, its elements, load and store allocate nothing", type_name<T>());
    before = allocations;
    kairn::SoA<T, K> empty;
    kairn::SoA<T, K> zero(0);
    expect(allocations == before && empty.size() == 0 && zero.empty(), "an empty SoA allocates nothing", type_name<T>());
    kairn::SoA<T, K> s(37);
    expect(allocations == before + 1, "SoA(n) allocates once", type_name<T>());
    for (int j = 0; j < K; ++j)
        expect(reinterpret_cast<std::uintptr_t>(s.limb(j)) % 64 == 0, "each array starts at a multiple of 64 bytes",
               type_name<T>(), j);
    before = allocations;
    s[3] = E(T(3));
    (void)s.load(0);
    s.store(4, s.load(0));
    kairn::SoA<T, K> moved(std::move(s));
    expect(allocations == before && s.empty() && moved.size() == 37 && moved.get(3).limb[0] == T(3),
           "element access, load, store and a move allocate nothing; moved from, an SoA is empty", type_name<T>());
    before = allocations;
    kairn::SoA<T, K> copy = moved;
    expect(allocations == before + 1 && copy.size() == 37 && same(copy.get(3), moved.get(3)), "a copy allocates once",
           type_name<T>());
    before = allocations;
    copy.resize(50);
    bool kept = copy.size() == 50;
    for (std::size_t i = 0; i < 37; ++i) kept = kept && same(copy.get(i), moved.get(i));
    for (std::size_t i = 37; i < 50; ++i) kept = kept && same(copy.get(i), E());
    expect(allocations == before + 1 && kept, "resize allocates once, keeps the elements, and makes the new ones zero",
           type_name<T>());
    before = allocations;
    copy.resize(50);
    copy = std::move(moved);
    expect(allocations == before && copy.size() == 37, "resize to the same size and a move assignment allocate nothing",
           type_name<T>());
    copy.resize(5);
    expect(copy.size() == 5 && copy.get(3).limb[0] == T(3), "resize down keeps the first elements", type_name<T>());
}

template <class T>
void all_of_one_type() {
    constexpr int W = kairn::Packed<T, 2>::lanes;
    for (std::size_t n : {std::size_t(0), std::size_t(1), std::size_t(W > 1 ? W - 1 : 0), std::size_t(W),
                          std::size_t(W + 1), std::size_t(2 * W - 1), std::size_t(2 * W + 1), std::size_t(37)}) {
        elements<T, 1>(n);
        elements<T, 2>(n);
    }
    program_arrays<T>();
    allocation<T, 1>();
    allocation<T, 2>();
}

}  // namespace

int main() {
    all_of_one_type<double>();
    all_of_one_type<float>();
    std::printf("%ld checks of SoA, SoAView and SoARef (Packed with %d lanes of double), %ld failed\n", checked,
                kairn::Packed<double, 2>::lanes, failures);
    return failures == 0 ? 0 : 1;
}
