/// @file
/// Accumulator<T, k>: the state of a sum or a dot product given to the program, for loops that
/// Kairn does not provide (a product of polynomials over several indices, a sum computed in parallel
/// and merged), with a radius that bounds the error of the result after any history of additions,
/// products and merges (docs/developer/design/milestone2.md, "The accumulator"). For T float or
/// double and k = 1 or 2.
///
/// An accumulator holds the running sum s, a number of k limbs; the running sum a, in T, of the
/// magnitudes of the leading limbs of what was added; and the count n of terms. Each operation that
/// changes s and a is one generated, proved kernel:
/// - add(x): acc_add_1 or acc_add_2, s = s + x (add_1_1, add_2_2 on x guarded, rule R3), a = a + |x0|;
/// - add_product(x, y): acc_mul_entry_1 or acc_mul_entry_2, s = s + x y (the step of the dot product: one
///   fused operation of x and y guarded for one limb, mul_2_2 then add_2_2 for two),
///   a = a + |x0| |y0|;
/// - merge(other): acc_merge_1 or acc_merge_2, s = s + s' (a node of the summation tree), a = a + a';
/// - error_bound(): bound_dot_1 or bound_dot_2 of the count m, then acc_radius_1 or acc_radius_2 of
///   (a, m, g, t).
///
/// What is proved (proofs/theories/Accumulator.v, IeeeAccumulator.v), in plain words: for every
/// history of add, add_product and merge (a merge being a node of the tree, and the other
/// accumulator's history a subtree), whose elements are finite (canonical pairs for two limbs), if
/// the running sum s is finite and both masks of the kernels of the radius are true, then the
/// radius r that acc_radius_k computes from bound_dot_k(m), for a count m of T that is 0 or at least
/// 1 and at least the number n of terms, satisfies |s - Sigma| <= r, Sigma the exact sum of the
/// numbers and products added. In the order the program chose, whatever it was.
///
/// What this header adds, which is NOT machine-checked, each with its argument:
/// - the count: a std::uint64_t of the header, +1 per add and add_product, the sum on a merge,
///   exact up to 2^64 - 2. A count that would reach 2^64 - 1 or beyond stays at 2^64 - 1, and that
///   value means "too many to count": no bound is given (error_bound() is +inf). The theorem asks a
///   count at least n, which an exact count is, and a saturated one may not be;
/// - its conversion to T, the m the kernels take: the smallest number of T not below n
///   (detail::count_up of traits.hpp, integer code), rounded up beyond 2^p: the theorem asks of m
///   only that it be a number of T, 0 or at least 1, and at least n, which rounding up gives and a
///   conversion to nearest may not;
/// - what is returned when a mask is false or a value is not finite: error_bound() is +inf, and
///   ball() the whole line, whenever the count saturated, the mask of bound_dot_k or of acc_radius_k
///   is false (a sum of magnitudes that is +inf or a NaN, or a count beyond the lengths bounded), the
///   running sum is not finite, or the radius is not; never a finite radius that the theorem does
///   not give. A term that is not finite (an infinity or a NaN, or a product of an infinity and a
///   zero) makes the running sum not finite, and it stays so: the kernels keep a NaN and turn an
///   infinity into an infinity or a NaN (the cone rule), so no history after it gives a finite s;
/// - that the header calls the kernels in this way (the theorem's run1, run2).
/// The tests of these parts are tests/api/accumulator.cpp and tests/api/arrays_exact.py: counts at
/// and beyond where the conversion rounds, overflow of the running sum and of the sum of magnitudes,
/// terms that are not finite, merges of empty accumulators and saturated counts, and random
/// histories checked against exact rational arithmetic.
///
/// The checks of a debug build (KAIRN_CHECKS 1): add, add_product, merge, error_bound and ball round,
/// and check the environment first, the rounding mode included, then that a two-limb operand is
/// canonical. from_state does not round: it checks the environment without the rounding mode, then
/// its state (magnitudes not negative and, under rounding to nearest, a canonical sum). sum(),
/// running_sum(), magnitudes() and count() do not round and check nothing.
///
/// constexpr: the constructor, add, merge, sum, the accessors and from_state (their kernels have no
/// fused operation). add_product, error_bound and ball are not: acc_mul_entry_1, acc_mul_entry_2 and
/// acc_radius_k have fused multiply-adds without a constant-evaluation variant.
#pragma once

#include "ball.hpp"
#include "expansion.hpp"
#include "reduction.hpp"
#include "traits.hpp"

#include <cstdint>
#include <limits>
#include <type_traits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

namespace detail {

// The kernels of an accumulator of K limbs are proved: what each operation calls.
template <class T, int K>
concept acc_add_proved = (K == 1 && gen::bounds::acc_add_1<T>::proved) || (K == 2 && gen::bounds::acc_add_2<T>::proved);
template <class T, int K>
concept acc_mul_proved =
    (K == 1 && gen::bounds::acc_mul_entry_1<T>::proved) || (K == 2 && gen::bounds::acc_mul_entry_2<T>::proved);
template <class T, int K>
concept acc_merge_proved =
    (K == 1 && gen::bounds::acc_merge_1<T>::proved) || (K == 2 && gen::bounds::acc_merge_2<T>::proved);
template <class T, int K>
concept acc_radius_proved =
    (K == 1 && gen::bounds::acc_radius_1<T>::proved && gen::bounds::bound_dot_1<T>::proved) ||
    (K == 2 && gen::bounds::acc_radius_2<T>::proved && gen::bounds::bound_dot_2<T>::proved);

// The count that means "too many to count": no bound is given.
inline constexpr std::uint64_t acc_saturated = ~std::uint64_t{0};
// n + m, or acc_saturated when it would reach it.
KAIRN_FORCEINLINE constexpr std::uint64_t acc_count_add(std::uint64_t n, std::uint64_t m) noexcept {
    return m >= acc_saturated - n ? acc_saturated : n + m;
}

// The checks of KAIRN_CHECKS of from_state, which does not round: the environment without the
// rounding mode, then the magnitudes not negative and, when the rounding mode is to nearest (the
// test of a canonical pair rounds), the running sum canonical.
template <class T, int K>
KAIRN_FORCEINLINE constexpr void check_acc_state([[maybe_unused]] const Expansion<T, K>& s, [[maybe_unused]] T a) noexcept {
#if KAIRN_CHECKS
    if (check_environment_except_rounding()) {
        if (rounding_to_nearest() && !admissible(s)) fail("Accumulator::from_state", "the running sum is not canonical");
        if (a < T(0)) fail("Accumulator::from_state", "the sum of magnitudes is negative");
    }
#endif
}

}  // namespace detail

/// The state of a sum or a dot product, with a radius for its error: see the file's comment for
/// what is proved and what this class adds. A value type: trivially copyable, no heap memory, an
/// empty accumulator when default-constructed (every limb +0, count 0).
template <class T, int K>
class Accumulator {
    static_assert(detail::limb<T>, "Accumulator<T, k>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "Accumulator<T, k>: k is 1 or 2");

    Expansion<T, K> s_{};
    T a_ = T(0);
    std::uint64_t n_ = 0;

public:
    /// An empty accumulator: no term, every limb +0.
    constexpr Accumulator() noexcept = default;

    /// Adds x (kernel acc_add_1 or acc_add_2): s = s + x, rounded as add_1_1 (to nearest) or add_2_2
    /// (normalized, within 3u^2/(1 - 4u) |s + x|) on x guarded (rule R3: a product of the program
    /// passed in is rounded first); a = a + |x0| rounded to nearest; one more term. Rounds; constexpr.
    /// Requires, with two limbs, x canonical (checked with KAIRN_CHECKS).
    constexpr void add(const Expansion<T, K>& x) noexcept
        requires detail::acc_add_proved<T, K>
    {
        detail::check(x);
        if constexpr (K == 1) {
            gen::acc_add_1(s_.limb[0], a_, x.limb[0], s_.limb[0], a_);
        } else {
            gen::acc_add_2(s_.limb[0], s_.limb[1], a_, x.limb[0], x.limb[1], s_.limb[0], s_.limb[1], a_);
        }
        n_ = detail::acc_count_add(n_, 1);
    }
    /// Adds a value of T: for one limb x itself, for two the number Expansion<T, 2>(x) (make_2,
    /// guarded), then add of it (kernel acc_add_1 or acc_add_2).
    constexpr void add(std::type_identity_t<T> x) noexcept
        requires detail::acc_add_proved<T, K>
    {
        add(Expansion<T, K>(x));
    }

    /// Adds the product x y (kernel acc_mul_entry_1 or acc_mul_entry_2): for one limb s = fma(x, y, s)
    /// on x and y guarded, one rounding of the exact product and the sum (the guards keep a product
    /// of the program out of the fused operation where the compiler sees the other factor to be 1,
    /// rule R3: measured with Apple clang 21 under -ffp-contract=fast); for two the step of the dot
    /// product, mul_2_2 then add_2_2, on the limbs of x and y guarded, for the same reason; a = a +
    /// |x0| |y0| rounded once.
    /// One more term. Rounds; not constexpr (fused multiply-adds). Requires, with two limbs, x and y
    /// canonical (checked with KAIRN_CHECKS).
    void add_product(const Expansion<T, K>& x, const Expansion<T, K>& y) noexcept
        requires detail::acc_mul_proved<T, K>
    {
        detail::check(x, y);
        if constexpr (K == 1) {
            gen::acc_mul_entry_1(s_.limb[0], a_, x.limb[0], y.limb[0], s_.limb[0], a_);
        } else {
            gen::acc_mul_entry_2(s_.limb[0], s_.limb[1], a_, x.limb[0], x.limb[1], y.limb[0], y.limb[1], s_.limb[0],
                           s_.limb[1], a_);
        }
        n_ = detail::acc_count_add(n_, 1);
    }
    /// The product of two values of T: as add_product of Expansion<T, K>(x) and Expansion<T, K>(y)
    /// (kernel acc_mul_entry_1 or acc_mul_entry_2).
    void add_product(std::type_identity_t<T> x, std::type_identity_t<T> y) noexcept
        requires detail::acc_mul_proved<T, K>
    {
        add_product(Expansion<T, K>(x), Expansion<T, K>(y));
    }

    /// Merges other into this one (kernel acc_merge_1 or acc_merge_2): s = s + s', a node of the
    /// summation tree, rounded as add_1_1 or add_2_2; a = a + a' rounded to nearest; the counts added
    /// (saturated at 2^64 - 1, which gives no bound). other may be this accumulator itself. Rounds;
    /// constexpr. So a program sums in parallel, one accumulator per thread, and merges them in any
    /// order: the bound holds for the tree it made.
    constexpr void merge(const Accumulator& other) noexcept
        requires detail::acc_merge_proved<T, K>
    {
        detail::check_environment();
        const Accumulator o = other;
        if constexpr (K == 1) {
            gen::acc_merge_1(s_.limb[0], a_, o.s_.limb[0], o.a_, s_.limb[0], a_);
        } else {
            gen::acc_merge_2(s_.limb[0], s_.limb[1], a_, o.s_.limb[0], o.s_.limb[1], o.a_, s_.limb[0], s_.limb[1], a_);
        }
        n_ = detail::acc_count_add(n_, o.n_);
    }

    /// The running sum, canonical, with whether it is finite (kernel fold_finish_1 or
    /// fold_finish_2): s when its leading limb is finite, otherwise the canonical NaN and finite =
    /// false. Its error is at most error_bound(). Does not round; constexpr.
    constexpr Reduction<Expansion<T, K>> sum() const noexcept {
        Reduction<Expansion<T, K>> r;
        if constexpr (K == 1) {
            gen::fold_finish_1(s_.limb[0], r.value.limb[0], r.finite);
        } else {
            gen::fold_finish_2(s_.limb[0], s_.limb[1], r.value.limb[0], r.value.limb[1], r.finite);
        }
        return r;
    }

    /// A bound of the error of the running sum: with Sigma the exact sum of what was added, when the
    /// result r is finite, |s - Sigma| <= r (kernels bound_dot_1 or bound_dot_2 of the count m, then
    /// acc_radius_1 or acc_radius_2 of (a, m, g, t)). m is the count as the smallest number of T not
    /// below it. +infinity, which claims nothing, when the count saturated, a mask of the two kernels
    /// is false (a sum of magnitudes that is +inf or a NaN; a count m with m u above about 1/4 to
    /// 1/2, u the unit roundoff of T: the sum of magnitudes is held in T for one and for two limbs,
    /// and acc_radius_k bounds counts up to m u <= 1/2, about 2^22 terms of float and 2^51 of
    /// double), the running sum is not finite, or the radius is not. The empty accumulator has a
    /// radius of a few times the smallest normal number. Rounds; not constexpr.
    T error_bound() const noexcept
        requires detail::acc_radius_proved<T, K>
    {
        detail::check_environment();
        constexpr T inf = std::numeric_limits<T>::infinity();
        if (n_ == detail::acc_saturated || !detail::finite(s_.limb[0])) return inf;
        const T m = detail::count_up<T>(n_);
        T g = T(0), t = T(0), r = T(0);
        bool ok = false, ok_r = false;
        if constexpr (K == 1) {
            gen::bound_dot_1(m, g, t, ok);
            if (!ok) return inf;
            gen::acc_radius_1(a_, m, g, t, r, ok_r);
        } else {
            gen::bound_dot_2(m, g, t, ok);
            if (!ok) return inf;
            gen::acc_radius_2(a_, m, g, t, r, ok_r);
        }
        return ok_r && detail::finite(r) ? r : inf;
    }

    /// The ball of center the running sum and radius error_bound() (kernel ball_make_1 or
    /// ball_make_2, the constructor Ball(c, r)): it contains the exact sum of what was added. The
    /// whole line when error_bound() is +infinity or the running sum is not finite: never a finite
    /// ball that the theorem does not give. Rounds; not constexpr.
    Ball<T, K> ball() const noexcept
        requires detail::acc_radius_proved<T, K> && detail::make_proved<T, K>
    {
        const T r = error_bound();
        if (r == std::numeric_limits<T>::infinity()) return Ball<T, K>::whole();
        return Ball<T, K>(s_, r);
    }

    /// The number of terms added: +1 per add and add_product, the sum on a merge; 2^64 - 1 means
    /// that it saturated (too many to count). Does not round; constexpr.
    constexpr std::uint64_t count() const noexcept { return n_; }
    /// a, the running sum of the magnitudes of the leading limbs of what was added (of the products
    /// of the leading limbs, for add_product), rounded to nearest at each step. Does not round;
    /// constexpr.
    constexpr T magnitudes() const noexcept { return a_; }
    /// s as the kernels left it, for a program that moves an accumulator through its own storage
    /// (with magnitudes() and count(), and from_state): when its leading limb is not finite it need
    /// not be canonical; sum() is the canonical form. Does not round; constexpr.
    constexpr const Expansion<T, K>& running_sum() const noexcept { return s_; }

    /// An accumulator with the state (s, a, n) read from another by running_sum(), magnitudes() and
    /// count(): a program moves accumulators through its own storage (a buffer of a device, a
    /// message) and back. Unchecked but for KAIRN_CHECKS: the guarantee of error_bound() is that of
    /// the history of the accumulator the state was read from, and holds only for such a state. With
    /// KAIRN_CHECKS, s must be canonical and a not negative. Does not round; constexpr.
    static constexpr Accumulator from_state(const Expansion<T, K>& s, T a, std::uint64_t n) noexcept {
        detail::check_acc_state(s, a);
        Accumulator acc;
        acc.s_ = s;
        acc.a_ = a;
        acc.n_ = n;
        return acc;
    }
};

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
