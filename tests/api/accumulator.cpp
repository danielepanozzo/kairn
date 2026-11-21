// kairn::Accumulator (include/kairn/accumulator.hpp), beside what the oracle judges of its kernels
// (api.oracle.acc_add_k, acc_mul_k, acc_merge_k, through from_state and the accessors) and what
// tests/api/arrays_exact.py checks of its histories in exact arithmetic (api.arrays.exact.accumulator):
//
// - constant evaluation: the constructor, add, merge, sum, count, magnitudes, running_sum and
//   from_state in static_asserts, with the same bits at run time;
// - the type: trivially copyable, an empty accumulator when default-constructed;
// - merges: with itself the same as with a copy; with an empty one the same state, bit for bit (the
//   kernels' sums with a zero are exact); of empty ones, an empty one with a finite radius;
// - from_state of the state read back gives the same sum, radius and ball;
// - the count: exact, +1 per term, added on a merge, saturated at 2^64 - 1, where no bound is given;
//   the radius given at counts well within m u <= 1/2 and not beyond (u of T, for both numbers of
//   limbs: the magnitudes are summed in T);
// - what is returned when something is not finite: the running sum overflows, the sum of
//   magnitudes overflows while the running sum stays finite, a term is an infinity, a NaN, or an
//   infinity times zero: error_bound() +inf and ball() the whole line, sum() finite exactly when the
//   running sum is.
#include <kairn/accumulator.hpp>
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <type_traits>

namespace {

int failures = 0;
void check(bool ok, const char* what, const char* type, int k) {
    if (ok) return;
    ++failures;
    std::printf("FAILED %s (%s, %d limbs)\n", what, type, k);
}

template <class T, int K>
constexpr kairn::Accumulator<T, K> constant_history() {
    kairn::Accumulator<T, K> a, b;
    a.add(T(1));
    a.add(kairn::Expansion<T, K>(T(0.375)));
    b.add(T(-0.25));
    a.merge(b);
    a.merge(a);
    return a;
}

template <class T, int K>
bool same_state(const kairn::Accumulator<T, K>& x, const kairn::Accumulator<T, K>& y) {
    return std::memcmp(&x.running_sum(), &y.running_sum(), sizeof(T) * K) == 0 && x.count() == y.count() &&
           x.magnitudes() == y.magnitudes();
}

template <class T, int K>
void run(const char* type) {
    using A = kairn::Accumulator<T, K>;
    using E = kairn::Expansion<T, K>;
    constexpr T inf = std::numeric_limits<T>::infinity();
    static_assert(std::is_trivially_copyable_v<A> && std::is_default_constructible_v<A>);
    // Constant evaluation.
    constexpr A c = constant_history<T, K>();
    static_assert(c.count() == 6 && c.sum().finite && c.sum().value.limb[0] == T(2.25));
    static_assert(c.magnitudes() == T(3.25));
    static_assert(A().count() == 0 && A().sum().value.limb[0] == T(0) && A().magnitudes() == T(0));
    static_assert(A::from_state(E(T(2)), T(3), 7).count() == 7 && A::from_state(E(T(2)), T(3), 7).magnitudes() == T(3));
    // The same at run time.
    volatile T vone = T(1), vq = T(0.375), vm = T(-0.25);
    A a, b;
    a.add(T(vone));
    a.add(E(T(vq)));
    b.add(T(vm));
    a.merge(b);
    a.merge(a);
    check(same_state(a, c), "the same state at run time as in constant evaluation", type, K);

    // Merges: with itself as with a copy; with an empty one, the same state; empty ones.
    A x;
    for (int i = 1; i < 50; ++i) {
        x.add(T(1) / T(i));
        x.add_product(T(i), T(1) / T(3));
    }
    A y = x, z = x;
    y.merge(y);
    const A copy = z;
    z.merge(copy);
    check(same_state(y, z), "a merge with itself is a merge with a copy", type, K);
    A w = x;
    w.merge(A());
    check(same_state(w, x), "a merge with an empty accumulator changes nothing", type, K);
    A e;
    e.merge(A());
    const T re = e.error_bound();
    check(e.count() == 0 && e.sum().finite && e.sum().value.limb[0] == T(0) && re > T(0) && re < T(1e-30),
          "empty accumulators merged: no term, a radius of a few smallest normal numbers", type, K);
    A f;
    f.merge(x);
    check(f.count() == x.count() && f.sum().value.limb[0] == x.sum().value.limb[0], "an empty one merged with x", type, K);

    // from_state of the state read back.
    const A back = A::from_state(x.running_sum(), x.magnitudes(), x.count());
    check(back.error_bound() == x.error_bound() && back.sum().value.limb[0] == x.sum().value.limb[0] &&
              back.ball().radius() == x.ball().radius(),
          "from_state of the state read back", type, K);
    check(x.ball().radius() == x.error_bound() && x.ball().center().limb[0] == x.running_sum().limb[0],
          "ball() is the running sum and error_bound()", type, K);

    // The count: +1 per term, saturated, and where a radius is given.
    check(x.count() == 98, "the count of the terms", type, K);
    A s = x;
    for (int i = 0; i < 70; ++i) s.merge(s);
    check(s.count() == ~std::uint64_t{0} && s.error_bound() == inf && s.ball().is_whole(),
          "a count that saturates: no bound", type, K);
    constexpr int p = std::numeric_limits<T>::digits;
    A g;
    g.add(T(1));
    for (int i = 0; i < p - 4; ++i) g.merge(g);  // 2^(p-4) terms: m u = 1/16
    check(g.count() == (std::uint64_t{1} << (p - 4)) && g.error_bound() < inf, "a radius at m u = 1/16", type, K);
    for (int i = 0; i < 4; ++i) g.merge(g);  // 2^p terms: m u = 1
    check(g.error_bound() == inf && g.ball().is_whole(), "no radius at m u = 1", type, K);

    // What is returned when something is not finite.
    const T big = std::numeric_limits<T>::max();
    A o;
    o.add(big);
    o.add(big);
    check(!o.sum().finite && o.error_bound() == inf && o.ball().is_whole(), "the running sum overflows", type, K);
    A m;
    m.add(big);
    m.add(-big);
    m.add(big);
    m.add(-big);
    check(m.sum().finite && m.magnitudes() == inf && m.error_bound() == inf && m.ball().is_whole(),
          "the sum of magnitudes overflows, the running sum does not", type, K);
    for (const T bad : {inf, -inf, std::numeric_limits<T>::quiet_NaN()}) {
        A n = x;
        n.add(bad);
        n.add(T(1));
        A q = x;
        q.merge(n);
        check(!n.sum().finite && n.error_bound() == inf && n.ball().is_whole() && !q.sum().finite &&
                  q.error_bound() == inf,
              "a term that is not finite, and a merge with it", type, K);
    }
    A zinf;
    zinf.add_product(inf, T(0));
    zinf.add(T(1));
    check(!zinf.sum().finite && zinf.error_bound() == inf && zinf.ball().is_whole(), "an infinity times zero", type, K);
}

}  // namespace

int main() {
    run<double, 1>("double");
    run<double, 2>("double");
    run<float, 1>("float");
    run<float, 2>("float");
    if (failures) {
        std::printf("%d failures\n", failures);
        return 1;
    }
    std::printf("accumulator: every check passed\n");
    return 0;
}
