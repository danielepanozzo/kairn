/// @file
/// BallVector<T, k, N> and BallVectorView<T, k>: N centers of k limbs and ONE radius of type T
/// (float or double), the set of the vectors each of whose entries is within the radius of its
/// center (docs/developer/design/milestone2.md, "BallVector"; docs/developer/architecture.md, "Ball
/// vectors").
///
/// A ball vector is in one of two states: a finite ball vector (every center finite, canonical for
/// two limbs; the radius finite and nonnegative) or the whole space (every center zero, the radius
/// +inf). There is no empty state. The constructors make the whole space of a radius that is
/// negative, a NaN or +inf, or of a center that is not finite; every operation returns it when its
/// result cannot be a finite ball vector. A BallVector is not N independent balls: one radius
/// bounds every entry, and entry(i) is the ball of center i and that radius, a copy.
///
/// The header adds no arithmetic. Each operation is one generated loop over the arrays of the
/// centers, proved in Rocq for each of its orders (the files named by gen/kernels/bv_*.fold): the
/// constructor bv_make_k, the negation bv_neg_k, the sum bv_add_k, the difference bv_sub_k, the
/// scaling by a T bv_scale_k, the scaling by a power of two bv_mul_pow2_k (two or three calls of it
/// in ldexp when 2^n is not a number of T, a composition argued as for a Ball), the product of
/// polynomials bv_conv_k. Two operations are compositions made here, and say so: axpy (bv_scale_k,
/// then bv_add_k in place) and norm_upper (the fold of maxima norm_upper_k on the centers, then
/// add_up of blocks.hpp with the radius). None of the compositions is machine-checked as one. What
/// each loop claims, for canonical operands, in the IEEE model with overflow:
/// - V1: the result is canonical (a finite ball vector or the whole space);
/// - V2: containment, in every case: for every member x of X (and y of Y), f(x, y) is a member of
///   the result, entry by entry; the whole space contains everything;
/// - V3: if the result is finite, every operand and every scalar is, each center is the generated
///   kernel's on the entry (add_k, sub_k, ...) and the radius the loop's radius kernel at the
///   largest magnitude of a center;
/// - V4: the result is finite when every operand is, every scalar is, and the stated conditions on
///   the entries and on the radii hold (each operation says which).
///
/// The loops are generated in two orders (order.hpp): every function here computes in the fast
/// order of the translation unit (the lane order of Packed's register where it has more than one
/// lane, the sequential order where it has one), and in the sequential order when kairn::sequential
/// is its first argument. The statements are those of both orders. The state of every loop but the
/// product is a maximum and a conjunction, which do not depend on the order, and each center is
/// computed from its own entry, so the two orders give the same results; the tests compare them bit
/// for bit, a zero center compared as a zero under MSVC (whose packed code drops the guard's +0,
/// packed.hpp). The product of polynomials has the sequential order only.
///
/// The environment, in every build. Each operation on whole ball vectors, the constructors from
/// centers and a radius included, is a batch entry: before its loop it reads the floating-point
/// environment as kairn::environment_ok() does, with KAIRN_CHECKS 1 or 0, and if it is not the
/// default one calls KAIRN_ENVIRONMENT_FAILURE with the message of the checks of a debug build,
/// which by default prints it and stops the program (config.hpp): the precondition of every such
/// operation, checked, one read of the control register per call. What it reads is what a debug
/// build reads there: the negation, which computes no sum (a change of sign, the radius copied),
/// leaves the rounding mode out; every other operation reads it too, the constructors of one limb
/// among them, whose guards and m - m give zeros whose sign depends on the mode. The accessors (center(i), entry(i), radius(), the views), which copy, check nothing.
/// The other checks of a debug build (canonical operands, lengths, arrays that alias) stay with
/// KAIRN_CHECKS.
///
/// The centers are stored as one array per limb, as the loops read them: limb j of center i is
/// element i of array j (soa.hpp's layout). In a BallVector the arrays are inside the object; a
/// BallVectorView refers to arrays and a radius that another owns, a BallVector or the program.
///
/// Not here: an empty state; a radius per entry or weights (a program writes those on the functions
/// on arrays); a packed or lane-parallel form of the product; operations of a BallVector with a Ball
/// or a number, but the scaling by a T; dispatch at run time; constant evaluation of any operation
/// (the generated loops are not constexpr; the accessors are). Every loop called here is proved
/// (gen/claims.json): no operation needs the kairn::unverified marker, and each compiles only while
/// its loop is proved for T (kairn::gen::bounds::loops, as the functions of batch.hpp). The operations are ordinary
/// inline functions in every setting of KAIRN_ENCLOSURE_CODE: each calls one loop, itself an
/// ordinary inline function whose end (the radius and the finish) is never inlined.
///
/// Including this header includes soa.hpp, packed.hpp, ball.hpp and blocks.hpp; kairn/kairn.hpp
/// does not include it (docs/reference/ball_vector.md, "Compile time").
#pragma once

#include "ball.hpp"
#include "blocks.hpp"
#include "order.hpp"
#include "soa.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <type_traits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

template <class T, int K, std::size_t N>
class BallVector;
template <class T, int K>
class BallVectorView;

namespace detail {

// What a ball vector may hold: float or double limbs, const for a read-only view; one or two limbs.
template <class T, int K>
concept bv_element = limb<std::remove_const_t<T>> && (K == 1 || K == 2);

// What a loop takes of a ball vector: the limb arrays of its centers, its length, where its radius
// is. T is const for an operand.
template <class T, int K>
struct bv_parts {
    T* limb[K];
    std::size_t size;
    T* radius;
};

// The ball vectors a function accepts: a BallVector or a BallVectorView, of which the limb type,
// the limbs, the length when the type fixes it (0 when it does not: a view), and whether the
// function may write it. A BallVector given as an output is written only through an lvalue that
// is not const; a view through every view of mutable limbs (its constness is shallow).
template <class X>
struct bv_info {
    static constexpr bool ball_vector = false;
};
template <class T, int K, std::size_t N>
struct bv_info<BallVector<T, K, N>> {
    static constexpr bool ball_vector = true;
    static constexpr bool view = false;
    using limb_type = T;
    static constexpr int limbs = K;
    static constexpr std::size_t extent = N;
    static constexpr bool mutable_limbs = true;
};
template <class T, int K>
struct bv_info<BallVectorView<T, K>> {
    static constexpr bool ball_vector = true;
    static constexpr bool view = true;
    using limb_type = std::remove_const_t<T>;
    static constexpr int limbs = K;
    static constexpr std::size_t extent = 0;
    static constexpr bool mutable_limbs = !std::is_const_v<T>;
};
template <class X>
using bv_info_of = bv_info<std::remove_cvref_t<X>>;
template <class X>
concept bv_operand = bv_info_of<X>::ball_vector;
template <class Z>
concept bv_output = bv_operand<Z> && bv_info_of<Z>::mutable_limbs &&
                    (bv_info_of<Z>::view || (std::is_lvalue_reference_v<Z> && !std::is_const_v<std::remove_reference_t<Z>>));
// Operands of one limb type and one number of limbs, whose lengths agree where their types fix them.
template <class X, class Y>
concept bv_alike = bv_operand<X> && bv_operand<Y> &&
                   std::is_same_v<typename bv_info_of<X>::limb_type, typename bv_info_of<Y>::limb_type> &&
                   bv_info_of<X>::limbs == bv_info_of<Y>::limbs &&
                   (bv_info_of<X>::extent == 0 || bv_info_of<Y>::extent == 0 ||
                    bv_info_of<X>::extent == bv_info_of<Y>::extent);
template <class X, class Z>
concept bv_unary = bv_alike<X, Z> && bv_output<Z>;
template <class X, class Y, class Z>
concept bv_binary = bv_alike<X, Y> && bv_alike<X, Z> && bv_alike<Y, Z> && bv_output<Z>;
// The product of polynomials: x of n_x entries, y of n_y, z of n_x + n_y - 1, where the types fix
// the three lengths.
template <class X, class Y, class Z>
concept bv_product = bv_operand<X> && bv_operand<Y> && bv_output<Z> &&
                     std::is_same_v<typename bv_info_of<X>::limb_type, typename bv_info_of<Y>::limb_type> &&
                     std::is_same_v<typename bv_info_of<X>::limb_type, typename bv_info_of<Z>::limb_type> &&
                     bv_info_of<X>::limbs == bv_info_of<Y>::limbs && bv_info_of<X>::limbs == bv_info_of<Z>::limbs &&
                     (bv_info_of<X>::extent == 0 || bv_info_of<Y>::extent == 0 || bv_info_of<Z>::extent == 0 ||
                      bv_info_of<Z>::extent == bv_info_of<X>::extent + bv_info_of<Y>::extent - 1);
template <class X>
using bv_limb_t = typename bv_info_of<X>::limb_type;

// The parts of a BallVector and of a view, for the loops.
struct bv_access {
    template <class T, int K, std::size_t N>
    static KAIRN_FORCEINLINE bv_parts<const T, K> read(const BallVector<T, K, N>& x) noexcept {
        bv_parts<const T, K> p{};
        for (int j = 0; j < K; ++j) p.limb[j] = x.c_[j];
        p.size = N;
        p.radius = &x.r_;
        return p;
    }
    template <class T, int K, std::size_t N>
    static KAIRN_FORCEINLINE bv_parts<T, K> write(BallVector<T, K, N>& x) noexcept {
        bv_parts<T, K> p{};
        for (int j = 0; j < K; ++j) p.limb[j] = x.c_[j];
        p.size = N;
        p.radius = &x.r_;
        return p;
    }
    template <class T, int K>
    static KAIRN_FORCEINLINE bv_parts<const std::remove_const_t<T>, K> read(const BallVectorView<T, K>& x) noexcept {
        bv_parts<const std::remove_const_t<T>, K> p{};
        for (int j = 0; j < K; ++j) p.limb[j] = x.limb_[j];
        p.size = x.size_;
        p.radius = x.radius_;
        return p;
    }
    template <class T, int K>
        requires(!std::is_const_v<T>)
    static KAIRN_FORCEINLINE bv_parts<T, K> write(const BallVectorView<T, K>& x) noexcept {
        bv_parts<T, K> p{};
        for (int j = 0; j < K; ++j) p.limb[j] = x.limb_[j];
        p.size = x.size_;
        p.radius = x.radius_;
        return p;
    }
};
template <class T, int K>
KAIRN_FORCEINLINE bv_parts<const T, K> as_operand(const bv_parts<T, K>& z) noexcept {
    bv_parts<const T, K> p{};
    for (int j = 0; j < K; ++j) p.limb[j] = z.limb[j];
    p.size = z.size;
    p.radius = z.radius;
    return p;
}

// Whether a ball vector is canonical: a finite ball vector (every center finite, canonical for
// two limbs, the radius finite and r >= 0) or the whole space (every limb of every center zero, the
// radius +inf). For two limbs the test of a canonical center rounds (x0 + x1 == x0); for one it
// does not. Comparisons are written b > a and b >= a, as in detail::canonical.
template <class T, int K>
KAIRN_FORCEINLINE bool canonical_bv(const bv_parts<const T, K>& x) noexcept {
    const T r = *x.radius;
    if (r != r) return false;
    if (r == std::numeric_limits<T>::infinity()) {
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < x.size; ++i)
                if (x.limb[j][i] != 0) return false;
        return true;
    }
    if (!(finite(r) && r >= 0)) return false;
    for (std::size_t i = 0; i < x.size; ++i) {
        if (!finite(x.limb[0][i])) return false;
        if constexpr (K == 2) {
            Expansion<T, 2> c;
            c.limb[0] = x.limb[0][i];
            c.limb[1] = x.limb[1][i];
            if (!canonical(c)) return false;
        }
    }
    return true;
}

// The checks of an operation that rounds: the environment, the rounding mode included, in every
// build (check_batch_environment, environment.hpp: every operation on whole ball vectors is a
// batch entry); then, with KAIRN_CHECKS (config.hpp), every operand canonical, which is not checked
// when the environment is not the default one and KAIRN_ENVIRONMENT_FAILURE returned.
template <class T, int K, class... More>
KAIRN_FORCEINLINE void check_bv([[maybe_unused]] const bv_parts<const T, K>& x,
                                [[maybe_unused]] const More&... more) noexcept {
    [[maybe_unused]] bool operands = check_batch_environment();
#if KAIRN_CHECKS
    if (operands && !(canonical_bv(x) && ... && canonical_bv(more)))
        fail("a ball vector", "is not canonical (finite centers, canonical for two limbs, with a finite radius r >= 0, "
                              "or every center zero with the radius +inf), so no guarantee applies to the result");
#endif
}
// The same for an operation that does not round (the negation): the environment without the
// rounding mode, in every build; then, with KAIRN_CHECKS, the operand, which for two limbs is
// tested only when the rounding mode is to nearest, since that test rounds.
template <class T, int K>
KAIRN_FORCEINLINE void check_bv_exact([[maybe_unused]] const bv_parts<const T, K>& x) noexcept {
    [[maybe_unused]] bool operand = check_batch_environment(false);
#if KAIRN_CHECKS
    if (operand && (K == 1 || rounding_to_nearest()) && !canonical_bv(x))
        fail("a ball vector", "is not canonical (finite centers, canonical for two limbs, with a finite radius r >= 0, "
                              "or every center zero with the radius +inf), so no guarantee applies to the result");
#endif
}
// The lengths of the operands of a function given views: checked with KAIRN_CHECKS, in every
// environment (an integer comparison), and not otherwise.
KAIRN_FORCEINLINE void check_lengths([[maybe_unused]] bool agree) noexcept {
#if KAIRN_CHECKS
    if (!agree) fail("ball vectors", "of lengths that do not match the operation");
#endif
}
// Whether two arrays of n and m limbs overlap, their addresses compared as integers (< is not
// defined between pointers into different arrays); for the checks of KAIRN_CHECKS only.
template <class T>
KAIRN_FORCEINLINE bool overlap(const T* a, std::size_t n, const T* b, std::size_t m) noexcept {
    if (n == 0 || m == 0) return false;
    const std::uintptr_t p = reinterpret_cast<std::uintptr_t>(a), q = reinterpret_cast<std::uintptr_t>(b);
    return p < q + m * sizeof(T) && q < p + n * sizeof(T);
}

// The constructor, in the sequential order in every build, so that BallVector and the views are
// the same code in every translation unit (the lane order computes the same bits): the centers c
// and the radius r given, written into the arrays z (which may be those of c, in place) and *rr.
// Checked in every build, as a batch entry (check_batch_environment, environment.hpp): the
// environment, the rounding mode included, for one limb as for two. The constructor of one limb
// rounds nothing but its guards (c + 0 and r + 0) and m - m, whose values are the same under every
// rounding mode; but m - m is -0 when rounding downward, which makes the radius -0, and a compiler
// that assumes rounding to nearest may then decide the kernel's test of the radius's sign
// otherwise: with clang-cl (2026-11-21) the constructor returned the whole space for finite centers
// and a zero radius under rounding downward. So its result is not independent of the rounding mode
// in practice, and the mode is checked. Then with KAIRN_CHECKS a negative radius, reported as
// almost surely a mistake (the constructor makes it the whole space), and for two limbs each center
// canonical, whose test rounds.
template <class T, int K>
KAIRN_FORCEINLINE void bv_make(const T* const* c, std::size_t n, T r, T* const* z, T* rr) noexcept {
    [[maybe_unused]] bool operands = check_batch_environment();
#if KAIRN_CHECKS
    if constexpr (K == 1) {
        if (operands && 0 > r)
            fail("a ball vector", "has a negative radius (it would make the whole space)");
    } else {
        if (operands) {
            for (std::size_t i = 0; i < n; ++i) {
                Expansion<T, 2> e;
                e.limb[0] = c[0][i];
                e.limb[1] = c[1][i];
                if (!canonical(e)) fail("a ball vector", "has a center that is not canonical");
            }
            if (0 > r) fail("a ball vector", "has a negative radius (it would make the whole space)");
        }
    }
#endif
    bool finite_ = false;
    if constexpr (K == 1) {
        static_assert(::kairn::gen::bounds::loops::bv_make_1<T>::proved, "kairn: the loop bv_make_1 is not proved for this T");
        gen::bv_make_1_seq(c[0], n, r, z[0], *rr, finite_);
    } else {
        static_assert(::kairn::gen::bounds::loops::bv_make_2<T>::proved, "kairn: the loop bv_make_2 is not proved for this T");
        gen::bv_make_2_seq(c[0], c[1], n, r, z[0], z[1], *rr, finite_);
    }
}

}  // namespace detail

/// A view of a ball vector of K limbs whose length is known at run time: K pointers to the arrays
/// of the centers (limb j of center i is element i of array j), a length, and a pointer to the
/// radius, all owned by someone else, a BallVector or the program. T is float or double for a view
/// through which the operations of this header write (the arrays and the radius both), const float
/// or const double for a read-only one; a view of T converts to a view of const T. Owns nothing,
/// allocates nothing; trivially copyable, cheap to pass by value. Constness is shallow, as for
/// std::span: a const BallVectorView<double, 1> is still written by an operation given it.
///
/// A view is a canonical ball vector as long as only Kairn writes its arrays and its radius. Its
/// own accessors only read: nothing writes through a view but the operations of this header, which
/// write a canonical result. A program that writes the arrays or the radius of a view itself must
/// make the view again (the constructor below), which makes them canonical; with KAIRN_CHECKS 1 every
/// operation checks that its operands are canonical, and stops the program if not.
template <class T, int K>
class BallVectorView {
    static_assert(detail::bv_element<T, K>, "BallVectorView<T, k>: T is float or double, or const, and k is 1 or 2");
    using V = std::remove_const_t<T>;

public:
    /// The limb type, float or double.
    using limb_type = V;
    /// T: the limb type, const for a read-only view.
    using element_type = T;
    /// What center(i) returns.
    using center_type = Expansion<V, K>;
    /// What entry(i) returns: a ball of one center and the shared radius.
    using value_type = Ball<V, K>;
    /// K.
    static constexpr int limbs = K;

    /// The program's arrays as a ball vector: makes them one in place, then sees them (loop bv_make_1
    /// or bv_make_2, sequential order). c sees the n centers given, and radius is the radius given;
    /// afterwards c's arrays hold the centers and radius the radius of a canonical ball vector,
    /// which this view sees. For one limb each center is guarded (rule R3: the program may have
    /// written a product there). For two limbs the centers must be canonical pairs (written as
    /// Expansion<T, 2>, through SoAView::set for instance; limbs of the program's own, not normalized,
    /// are not covered). Proved, in the IEEE model, for any radius and any centers (canonical pairs
    /// for two limbs): the result is canonical; it is the whole space (every center zero, the radius
    /// +inf) exactly when the radius given is negative, a NaN or +inf, or the leading limb of a
    /// center is not finite; otherwise the centers and the radius are the values given (a zero may
    /// come back with the other sign). Checked as BallVector's constructor: the environment in every
    /// build, the radius and the centers with KAIRN_CHECKS. Not constexpr.
    BallVectorView(SoAView<V, K> c, V& radius) noexcept
        requires(!std::is_const_v<T>)
        : size_(c.size()), radius_(&radius) {
        for (int j = 0; j < K; ++j) limb_[j] = c.limb(j);
        const V* in[K];
        for (int j = 0; j < K; ++j) in[j] = limb_[j];
        detail::bv_make<V, K>(in, size_, radius, limb_, radius_);
    }
    /// A read-only view of what v sees.
    template <class U>
        requires(std::is_const_v<T> && std::is_same_v<const U, T>)
    constexpr BallVectorView(const BallVectorView<U, K>& v) noexcept : size_(v.size_), radius_(v.radius_) {
        for (int j = 0; j < K; ++j) limb_[j] = v.limb_[j];
    }

    /// The number of entries.
    constexpr std::size_t size() const noexcept { return size_; }
    /// Whether there is no entry.
    constexpr bool empty() const noexcept { return size_ == 0; }
    /// The radius: of a finite ball vector, a bound on the distance of every entry of every member to
    /// its center; +inf for the whole space.
    constexpr V radius() const noexcept { return *radius_; }
    /// Whether this is a finite ball vector (for a canonical one: its radius is finite).
    constexpr bool is_finite() const noexcept { return std::numeric_limits<V>::infinity() > *radius_; }
    /// Whether this is the whole space (radius +inf).
    constexpr bool is_whole() const noexcept { return *radius_ == std::numeric_limits<V>::infinity(); }
    /// Center i, i < size(), as a number: its limbs, copied (0 for the whole space).
    constexpr center_type center(std::size_t i) const noexcept {
        center_type c;
        for (int j = 0; j < K; ++j) c.limb[j] = limb_[j][i];
        return c;
    }
    /// Entry i, i < size(), as a Ball: center i and the shared radius, a copy (the whole line for the
    /// whole space). A ball vector is not size() independent balls: writing the ball changes nothing
    /// here, and the radius is that of every entry.
    constexpr value_type entry(std::size_t i) const noexcept {
        return value_type(detail::kernel_result, center(i), *radius_);
    }
    /// The centers, as a read-only view of their arrays.
    constexpr SoAView<const V, K> centers() const noexcept {
        if constexpr (K == 1) {
            return SoAView<const V, K>(limb_[0], size_);
        } else {
            return SoAView<const V, K>(limb_[0], limb_[1], size_);
        }
    }
    /// The array of limb j of the centers (0 for the leading limbs), of size() elements, read-only.
    constexpr const V* limb(int j) const noexcept { return limb_[j]; }
    /// The count entries from offset on, offset + count <= size() (not checked, as for std::span),
    /// with the same radius: a ball vector of count entries that contains the part of every member,
    /// as the shifted operands of a subdivision need. Only for a view of const limbs: an operation
    /// that wrote a part of a ball vector would change the one radius of every entry.
    constexpr BallVectorView subview(std::size_t offset, std::size_t count) const noexcept
        requires(std::is_const_v<T>)
    {
        T* arrays[K];
        for (int j = 0; j < K; ++j) arrays[j] = limb_[j] + offset;
        return BallVectorView(arrays, count, radius_);
    }

private:
    template <class U, int J>
    friend class BallVectorView;
    template <class U, int J, std::size_t M>
    friend class BallVector;
    friend struct detail::bv_access;
    // The parts of a BallVector, as they are.
    constexpr BallVectorView(T* const* arrays, std::size_t n, T* radius) noexcept : size_(n), radius_(radius) {
        for (int j = 0; j < K; ++j) limb_[j] = arrays[j];
    }
    T* limb_[K] = {};
    std::size_t size_ = 0;
    T* radius_ = nullptr;
};

/// N centers of K limbs of type T (float or double) and one radius of type T: the set of the
/// vectors of N reals each of whose entries is within the radius of its center. Defined for K = 1
/// and K = 2 and N >= 1. The storage is inside the object, the centers as K arrays of N limbs (limb
/// j of center i is element i of array j) followed by the radius: a regular value type, trivially
/// copyable and standard-layout, usable in arrays and as a member, with no heap memory. Its value is
/// always canonical: a finite ball vector or the whole space (every center zero, the radius +inf).
///
/// A BallVector is not N independent balls. Its one radius is a bound for every entry, so it is as
/// wide as the widest entry needs, and every operation adds to the one radius what the worst entry
/// adds. In exchange each operation costs one kernel per entry for the centers and a few
/// operations for the radius, once. entry(i) is the ball of center i and the shared radius, a copy.
///
/// The constructors and the operations are those of this header's functions; the operations are
/// free functions and operators (below), not members.
template <class T, int K, std::size_t N>
class BallVector {
    static_assert(detail::limb<T>, "BallVector<T, k, N>: the limb type T is float or double");
    static_assert(K == 1 || K == 2, "BallVector<T, k, N>: k is 1 or 2");
    static_assert(N >= 1, "BallVector<T, k, N>: N is at least 1 (a view may have no entry)");

    T c_[K][N] = {};
    T r_ = T(0);

    friend struct detail::bv_access;

public:
    /// The limb type.
    using limb_type = T;
    /// What center(i) returns.
    using center_type = Expansion<T, K>;
    /// What entry(i) returns: a ball of one center and the shared radius.
    using value_type = Ball<T, K>;
    /// K.
    static constexpr int limbs = K;

    /// The point 0 of N entries: every center 0, the radius 0. Does not round.
    constexpr BallVector() noexcept = default;
    /// The ball vector of the centers c and the radius r (loop bv_make_1 or bv_make_2, in the
    /// sequential order in every build), each value guarded where the loop adds it (rule R3). For one
    /// limb any centers; for two, canonical ones (Expansion<T, 2> made by Kairn). Proved, in the IEEE
    /// model: the result is canonical; it is the whole space exactly when r is negative (-inf
    /// included), a NaN or +inf, or the leading limb of a center is not finite; otherwise the centers
    /// are c and the radius r, as values (a zero may come back with the other sign). So the
    /// constructor never makes an empty set: a NaN or a negative radius says that something failed
    /// upstream, and the whole space is what is always true.
    /// The environment is checked first, in every build, the rounding mode included, for one limb
    /// as for two (a batch entry: the top of this file; for one limb the only rounded operations
    /// are the guards, c + 0 and r + 0, and the loop's m - m, whose values are the same under every
    /// rounding mode, but the sign of whose zeros is not). Then, when KAIRN_CHECKS is 1, a negative
    /// r is reported (it is almost surely a mistake) and, for two limbs, a center that is not
    /// canonical. Not constexpr.
    BallVector(const std::array<center_type, N>& c, T r) noexcept {
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < N; ++i) c_[j][i] = c[i].limb[j];
        make(r);
    }
    /// The same from the arrays of a view of N centers, c.size() == N (checked with KAIRN_CHECKS, not
    /// otherwise): the centers are copied in, then made a ball vector of radius r as above.
    BallVector(SoAView<const T, K> c, T r) noexcept {
        detail::check_lengths(c.size() == N);
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < N; ++i) c_[j][i] = c.limb(j)[i];
        make(r);
    }
    /// A copy of what the view v sees, v.size() == N (checked with KAIRN_CHECKS, not otherwise): its
    /// centers' limbs and its radius, as they are (a canonical view gives a canonical BallVector).
    /// Explicit: the length is checked at run time only. Does not round.
    explicit BallVector(BallVectorView<const T, K> v) noexcept {
        detail::check_lengths(v.size() == N);
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < N; ++i) c_[j][i] = v.limb(j)[i];
        r_ = v.radius();
    }

    /// The whole space: every center 0, the radius +inf. Does not round.
    [[nodiscard]] static constexpr BallVector whole() noexcept {
        BallVector x;
        x.r_ = std::numeric_limits<T>::infinity();
        return x;
    }

    /// N.
    static constexpr std::size_t size() noexcept { return N; }
    /// The radius: of a finite ball vector, a bound on the distance of every entry of every member to
    /// its center; +inf for the whole space.
    constexpr T radius() const noexcept { return r_; }
    /// Whether this is a finite ball vector (its radius is finite).
    constexpr bool is_finite() const noexcept { return std::numeric_limits<T>::infinity() > r_; }
    /// Whether this is the whole space (radius +inf).
    constexpr bool is_whole() const noexcept { return r_ == std::numeric_limits<T>::infinity(); }
    /// Center i, i < N, as a number: its limbs, copied (0 for the whole space).
    constexpr center_type center(std::size_t i) const noexcept {
        center_type c;
        for (int j = 0; j < K; ++j) c.limb[j] = c_[j][i];
        return c;
    }
    /// Entry i, i < N, as a Ball: center i and the shared radius, a copy (the whole line for the
    /// whole space). A BallVector is not N independent balls: writing the ball changes nothing here,
    /// and the radius is that of every entry.
    constexpr value_type entry(std::size_t i) const noexcept {
        return value_type(detail::kernel_result, center(i), r_);
    }
    /// The centers, as a read-only view of their arrays.
    constexpr SoAView<const T, K> centers() const noexcept {
        if constexpr (K == 1) {
            return SoAView<const T, K>(c_[0], N);
        } else {
            return SoAView<const T, K>(c_[0], c_[1], N);
        }
    }
    /// The array of limb j of the centers (0 for the leading limbs), of N elements, read-only.
    constexpr const T* limb(int j) const noexcept { return c_[j]; }

    /// A view through which the operations of this header write this ball vector.
    constexpr BallVectorView<T, K> view() noexcept {
        T* arrays[K];
        for (int j = 0; j < K; ++j) arrays[j] = c_[j];
        return BallVectorView<T, K>(arrays, N, &r_);
    }
    /// A read-only view.
    constexpr BallVectorView<const T, K> view() const noexcept {
        const T* arrays[K];
        for (int j = 0; j < K; ++j) arrays[j] = c_[j];
        return BallVectorView<const T, K>(arrays, N, &r_);
    }
    /// view().
    constexpr operator BallVectorView<T, K>() noexcept { return view(); }
    /// view(), read-only.
    constexpr operator BallVectorView<const T, K>() const noexcept { return view(); }

private:
    // The centers in c_ and the radius r made a ball vector, in place.
    void make(T r) noexcept {
        const T* in[K];
        T* out[K];
        for (int j = 0; j < K; ++j) {
            in[j] = c_[j];
            out[j] = c_[j];
        }
        detail::bv_make<T, K>(in, N, r, out, &r_);
    }
};

KAIRN_DETAIL_PACKED_BEGIN
namespace packed_detail {

// The loops, in the order Seq names: NAME_seq, or the fast one, NAME_packed where Packed has more
// than one lane and NAME_seq where it has one (order.hpp). They live in the namespace of the form
// of Packed (packed.hpp), so that translation units compiled for different instruction sets, each
// with its own fast order, can be linked into one program.
#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_SCALAR
#define KAIRN_DETAIL_BV_FAST(NAME) NAME##_seq
#else
#define KAIRN_DETAIL_BV_FAST(NAME) NAME##_packed
#endif
// Each call is gated on the loop's proof status for T (gen/bounds.hpp, kairn::gen::bounds::loops:
// the loop's own statements, its minimum precision and every kernel it runs), as kairn/batch.hpp
// gates its functions: an operation compiles only while its loop is proved.
#define KAIRN_DETAIL_BV_LOOP(SEQ, NAME, ...)                                                       \
    static_assert(::kairn::gen::bounds::loops::NAME<T>::proved, "kairn: the loop " #NAME " is not proved for this T"); \
    if constexpr (SEQ) {                                                                            \
        gen::NAME##_seq(__VA_ARGS__);                                                               \
    } else {                                                                                        \
        gen::KAIRN_DETAIL_BV_FAST(NAME)(__VA_ARGS__);                                               \
    }

// Each takes the operands' parts, reads every radius by value before the loop writes, and writes
// the centers and the radius of z (the arrays of z may be exactly those of an operand: in place).
// The loop's flag says whether the result is finite, which its radius says too.
template <bool Seq, class T, int K>
inline void bv_neg(const kairn::detail::bv_parts<const T, K>& x, const kairn::detail::bv_parts<T, K>& z) noexcept {
    const T rx = *x.radius;
    bool f = false;
    if constexpr (K == 1) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_neg_1, x.limb[0], x.size, rx, z.limb[0], *z.radius, f)
    } else {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_neg_2, x.limb[0], x.limb[1], x.size, rx, z.limb[0], z.limb[1], *z.radius, f)
    }
}
template <bool Seq, bool Sub, class T, int K>
inline void bv_add(const kairn::detail::bv_parts<const T, K>& x, const kairn::detail::bv_parts<const T, K>& y,
                   const kairn::detail::bv_parts<T, K>& z) noexcept {
    const T rx = *x.radius, ry = *y.radius;
    bool f = false;
    if constexpr (K == 1 && !Sub) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_add_1, x.limb[0], y.limb[0], x.size, rx, ry, z.limb[0], *z.radius, f)
    } else if constexpr (K == 1) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_sub_1, x.limb[0], y.limb[0], x.size, rx, ry, z.limb[0], *z.radius, f)
    } else if constexpr (!Sub) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_add_2, x.limb[0], x.limb[1], y.limb[0], y.limb[1], x.size, rx, ry, z.limb[0],
                             z.limb[1], *z.radius, f)
    } else {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_sub_2, x.limb[0], x.limb[1], y.limb[0], y.limb[1], x.size, rx, ry, z.limb[0],
                             z.limb[1], *z.radius, f)
    }
}
template <bool Seq, class T, int K>
inline void bv_scale(const kairn::detail::bv_parts<const T, K>& x, T a, const kairn::detail::bv_parts<T, K>& z) noexcept {
    const T rx = *x.radius;
    bool f = false;
    if constexpr (K == 1) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_scale_1, x.limb[0], x.size, rx, a, z.limb[0], *z.radius, f)
    } else {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_scale_2, x.limb[0], x.limb[1], x.size, rx, a, z.limb[0], z.limb[1], *z.radius, f)
    }
}
// By c, a positive power of two of T.
template <bool Seq, class T, int K>
inline void bv_mul_pow2(const kairn::detail::bv_parts<const T, K>& x, T c, const kairn::detail::bv_parts<T, K>& z) noexcept {
    const T rx = *x.radius;
    bool f = false;
    if constexpr (K == 1) {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_mul_pow2_1, x.limb[0], x.size, rx, c, z.limb[0], *z.radius, f)
    } else {
        KAIRN_DETAIL_BV_LOOP(Seq, bv_mul_pow2_2, x.limb[0], x.limb[1], x.size, rx, c, z.limb[0], z.limb[1], *z.radius,
                             f)
    }
}
// X 2^n, as kairn::detail::ldexp does for a Ball (ball.hpp): one call of the scaling by a power of two when
// 2^n is a number of T, otherwise two or three, the first from x into z and the others in place. For
// a ball vector the composition needs no argument of its own (milestone2.md, "Scaling a ball by a
// power of two"): each call returns a canonical ball vector that contains c times every member of
// its operand, so the last contains 2^n times every member of X; and each call is exact when nothing
// it scales underflows, so the whole is exact when every limb of every center of 2^n X and its
// radius is zero or above the smallest normal number N in magnitude (the steps up only make values
// larger, and a nonzero value of T times 2^pow2_max is above N; of the two steps down, the first
// keeps every value above the final one). What is argued and not machine-checked is the clamp of n,
// as for a Ball: above pow2_max + 1 - pow2_min (2098 for double) each step is exact until one
// overflows, so any ball vector but the point 0 becomes the whole space, which also contains X 2^n
// for the larger n, and the point 0 stays the point 0; below pow2_min - pow2_max - 2 (-2099), every
// entry of every member of X 2^n is below eta/4 in magnitude, and the result for the clamped n is
// the point 0 for the point 0 and otherwise centers 0 and a radius of at least 2 eta (the second step
// scales values below 1/2 by eta, which rounds them to zero, clears the mask of exactness and steps
// the radius twice from zero).
template <bool Seq, class T, int K>
inline void bv_ldexp(const kairn::detail::bv_parts<const T, K>& x, int n, const kairn::detail::bv_parts<T, K>& z) noexcept {
    constexpr int lo = kairn::detail::pow2_min<T>, hi = kairn::detail::pow2_max<T>;
    constexpr int up = hi + 1 - lo, down = lo - hi - 2;
    if (n > up) n = up;
    if (down > n) n = down;
    kairn::detail::bv_parts<const T, K> from = x;
    if (lo > n) {
        bv_mul_pow2<Seq>(from, kairn::detail::pow2<T>(n - lo), z);
        from = kairn::detail::as_operand(z);
        n = lo;
    }
    while (n > hi) {
        bv_mul_pow2<Seq>(from, kairn::detail::pow2<T>(hi), z);
        from = kairn::detail::as_operand(z);
        n -= hi;
    }
    bv_mul_pow2<Seq>(from, kairn::detail::pow2<T>(n), z);
}
// The bound of the magnitudes of the centers (norm_upper_k), and whether it is given.
template <bool Seq, class T, int K>
inline T bv_centers_upper(const kairn::detail::bv_parts<const T, K>& x, bool& ok) noexcept {
    T b = T(0);
    if constexpr (K == 1) {
        KAIRN_DETAIL_BV_LOOP(Seq, norm_upper_1, x.limb[0], x.size, b, ok)
    } else {
        KAIRN_DETAIL_BV_LOOP(Seq, norm_upper_2, x.limb[0], x.limb[1], x.size, b, ok)
    }
    return b;
}

#undef KAIRN_DETAIL_BV_LOOP
#undef KAIRN_DETAIL_BV_FAST

// The functions below, without their constraints: the parts of the operands, the checks of
// KAIRN_CHECKS, the loop.
template <bool Seq, class X, class Z>
inline void neg(const X& x, Z& z) noexcept {
    const auto xp = kairn::detail::bv_access::read(x);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv_exact(xp);
    kairn::detail::check_lengths(xp.size == zp.size);
    bv_neg<Seq>(xp, zp);
}
template <bool Seq, bool Sub, class X, class Y, class Z>
inline void add(const X& x, const Y& y, Z& z) noexcept {
    const auto xp = kairn::detail::bv_access::read(x);
    const auto yp = kairn::detail::bv_access::read(y);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp, yp);
    kairn::detail::check_lengths(xp.size == yp.size && xp.size == zp.size);
    bv_add<Seq, Sub>(xp, yp, zp);
}
template <bool Seq, class X, class Z, class T>
inline void scale(const X& x, T a, Z& z) noexcept {
    const auto xp = kairn::detail::bv_access::read(x);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp);
    kairn::detail::check_lengths(xp.size == zp.size);
    bv_scale<Seq>(xp, a, zp);
}
template <bool Seq, class X, class Z>
inline void ldexp(const X& x, int n, Z& z) noexcept {
    const auto xp = kairn::detail::bv_access::read(x);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp);
    kairn::detail::check_lengths(xp.size == zp.size);
    bv_ldexp<Seq>(xp, n, zp);
}
template <bool Seq, class X, class Z>
inline void half(const X& x, Z& z) noexcept {
    using T = kairn::detail::bv_limb_t<X>;
    const auto xp = kairn::detail::bv_access::read(x);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp);
    kairn::detail::check_lengths(xp.size == zp.size);
    bv_mul_pow2<Seq>(xp, T(0.5), zp);
}
// a X + Y as the composition of two loops (architecture.md, "axpy of ball vectors"): S = bv_scale_k(X,
// a) written into z, then bv_add_k(S, Y) into z, in place. Y's radius is read before the first loop
// writes z's, which may be the same object; z's arrays may be exactly those of x, not those of y,
// which the first loop would overwrite before the second reads them: the result would then be a
// finite ball vector around 2 a X, which does not contain a X + Y. That case is told in every
// build, by one comparison of pointers: a debug build reports it (KAIRN_CHECKS), and the result is
// the whole space, which contains everything: the constructor's loop on z's own arrays with a
// radius of +infinity (bv_make_k makes the whole space of such a radius, whatever the centers).
template <bool Seq, class X, class Y, class Z, class T>
inline void axpy(T a, const X& x, const Y& y, Z& z) noexcept {
    const auto xp = kairn::detail::bv_access::read(x);
    auto yp = kairn::detail::bv_access::read(y);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp, yp);
    kairn::detail::check_lengths(xp.size == yp.size && xp.size == zp.size);
    if (yp.size > 0 && static_cast<const T*>(zp.limb[0]) == yp.limb[0]) {
        // The whole space first and the report after it, with no statement after the report: the
        // default handler does not return, and one compiler (MSVC, C4702) warns of code that
        // follows a call that does not; with a handler that returns, the result is the whole space.
        constexpr int K = kairn::detail::bv_info_of<X>::limbs;
        const T* in[K];
        for (int j = 0; j < K; ++j) in[j] = zp.limb[j];
        kairn::detail::bv_make<T, K>(in, zp.size, std::numeric_limits<T>::infinity(), zp.limb, zp.radius);
#if KAIRN_CHECKS
        kairn::detail::fail("axpy", "writes the array of y, which it reads after writing (z must not be y)");
#endif
    } else {
        const T ry = *yp.radius;
        yp.radius = &ry;
        bv_scale<Seq>(xp, a, zp);
        bv_add<Seq, false>(kairn::detail::as_operand(zp), yp, zp);
    }
}
// The product of polynomials (loop bv_conv_k, the sequential order only).
template <class X, class Y, class Z>
inline void convolution(const X& x, const Y& y, Z& z) noexcept {
    using T = kairn::detail::bv_limb_t<X>;
    constexpr int K = kairn::detail::bv_info_of<X>::limbs;
    const auto xp = kairn::detail::bv_access::read(x);
    const auto yp = kairn::detail::bv_access::read(y);
    const auto zp = kairn::detail::bv_access::write(z);
    kairn::detail::check_bv(xp, yp);
    const std::size_t nz = xp.size == 0 || yp.size == 0 ? 0 : xp.size + yp.size - 1;
    kairn::detail::check_lengths(zp.size == nz);
#if KAIRN_CHECKS
    for (int j = 0; j < K; ++j)
        for (int l = 0; l < K; ++l)
            if (kairn::detail::overlap<T>(zp.limb[j], nz, xp.limb[l], xp.size) ||
                kairn::detail::overlap<T>(zp.limb[j], nz, yp.limb[l], yp.size))
                kairn::detail::fail("convolution", "writes an array that it reads (z must overlap neither x nor y)");
#endif
    const T rx = *xp.radius, ry = *yp.radius;
    bool f = false;
    if constexpr (K == 1) {
        static_assert(::kairn::gen::bounds::loops::bv_conv_1<T>::proved, "kairn: the loop bv_conv_1 is not proved for this T");
        gen::bv_conv_1_seq(xp.limb[0], xp.size, yp.limb[0], yp.size, rx, ry, zp.limb[0], *zp.radius, f);
    } else {
        static_assert(::kairn::gen::bounds::loops::bv_conv_2<T>::proved, "kairn: the loop bv_conv_2 is not proved for this T");
        gen::bv_conv_2_seq(xp.limb[0], xp.limb[1], xp.size, yp.limb[0], yp.limb[1], yp.size, rx, ry, zp.limb[0],
                           zp.limb[1], *zp.radius, f);
    }
}
// The bound of the members (architecture.md, "Ball vectors", bv_norm_upper_k): the composition of
// two calls, norm_upper_k on the centers and add_up (blocks.hpp, kernel add_up_entry) with the
// radius, or +inf when the first is not given.
template <bool Seq, class X>
inline kairn::detail::bv_limb_t<X> norm_upper(const X& x) noexcept {
    using T = kairn::detail::bv_limb_t<X>;
    const auto xp = kairn::detail::bv_access::read(x);
    kairn::detail::check_bv(xp);
    bool ok = false;
    const T n = bv_centers_upper<Seq>(xp, ok);
    return ok ? kairn::detail::add_up(n, *xp.radius) : std::numeric_limits<T>::infinity();
}

}  // namespace packed_detail

// --- The functions, on BallVector and BallVectorView -------------------------------------------
//
// Each takes its operands as a BallVector or a BallVectorView (a view of const limbs or not), of one
// limb type and one number of limbs, and writes its result into z, a BallVector (an lvalue that is
// not const) or a view of mutable limbs. Where the types fix the lengths they must agree, or the
// call does not compile; where a view is given, the lengths are checked with KAIRN_CHECKS and not
// otherwise. Without a first argument kairn::sequential, each computes in the fast order of the
// translation unit (order.hpp); with it, in the sequential order. All are noexcept, allocate
// nothing and are not constexpr (the generated loops are not).

/// Z = -X, exactly (loop bv_neg_1 or bv_neg_2: neg_k on each center, the radius copied). Proved, in
/// the IEEE model, for a canonical X: the result is exactly the set of the negated members (V1, V2
/// and exactness); the whole space stays the whole space; a finite X gives a finite result. z may
/// be x itself (in place). Does not round: with KAIRN_CHECKS the environment is checked without the
/// rounding mode, and X, for two limbs, only under rounding to nearest (config.hpp).
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void neg(const X& x, Z&& z) noexcept {
    packed_detail::neg<false>(x, z);
}
/// neg in the sequential order.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void neg(Sequential, const X& x, Z&& z) noexcept {
    packed_detail::neg<true>(x, z);
}

/// Z = X + Y (loop bv_add_1 or bv_add_2): each center the k-number sum of the two (add_1_1, add_2_2),
/// the radius that of ball_add_k at the largest magnitude M of a center written, bv_add_radius_k(M,
/// rx, ry). Proved, in the IEEE model, for canonical X and Y: the result is canonical (V1); for every
/// member x of X and y of Y, x + y is a member of it, entry by entry (V2); if it is finite, X and Y
/// are, and its centers and radius are those just said (V3); it is finite when X and Y are finite,
/// rx + ry <= 2^(e_max - 2) and every entry has |x_i + y_i| + rx + ry <= 2^(e_max - 2), a quarter of
/// the overflow threshold (2^1022 for double, 2^126 for float) (V4). Not claimed, though it is what
/// the loop computes and what the tests find in every case: that the one radius equals the largest of
/// the N radii the entrywise Ball sums would have. z may be exactly x or exactly y (in place). Rounds:
/// with KAIRN_CHECKS, the environment and both operands are checked (config.hpp).
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void add(const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::add<false, false>(x, y, z);
}
/// add in the sequential order.
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void add(Sequential, const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::add<true, false>(x, y, z);
}
/// Z = X - Y (loop bv_sub_1 or bv_sub_2): as add, with the differences of the centers (sub_1_1,
/// sub_2_2), the same radius kernel, and the conditions of V4 on |x_i - y_i| + rx + ry.
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void sub(const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::add<false, true>(x, y, z);
}
/// sub in the sequential order.
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void sub(Sequential, const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::add<true, true>(x, y, z);
}

/// Z = X a, a of T (loop bv_scale_1 or bv_scale_2): each center scaled by a (scale_step_k, the
/// products mul_1_1 and mul_2_1), the radius that of ball_scale_k at the largest magnitude of a
/// center written, bv_scale_radius_k(M, rx, a). a is a value of the program: for one limb the loop
/// only rounds its products, which needs no guard; for two limbs a is a factor of the fused
/// operations of mul_2_1, unguarded (bv_scale_2 is on the generator's pending list of rule R3, the
/// factors of a fused operation; no compiler was measured to fuse a product of the program into
/// it). Proved, in the IEEE model, for a canonical X and any a: canonical (V1); x a is a member for
/// every member x (V2); a finite result has a finite X and a finite a (V3); it is finite when X is
/// finite, a is finite, |a| rx <= 2^(e_max - 2) and every entry has (|x_i| + rx) |a| <=
/// 2^(e_max - 2) (V4). An infinite or NaN a gives the whole space. Not claimed: that the radius
/// equals the largest of the entrywise radii. For a power of two known as such, ldexp and half keep
/// the result exact; this scaling's radius grows. z may be x (in place). Rounds; checked as add.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void scale(const X& x, std::type_identity_t<kairn::detail::bv_limb_t<X>> a, Z&& z) noexcept {
    packed_detail::scale<false>(x, a, z);
}
/// scale in the sequential order.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void scale(Sequential, const X& x, std::type_identity_t<kairn::detail::bv_limb_t<X>> a, Z&& z) noexcept {
    packed_detail::scale<true>(x, a, z);
}

/// Z = X 2^n, for every n (loop bv_mul_pow2_1 or bv_mul_pow2_2: the scaling by a power of two c of
/// T, called once when 2^n is a number of T, two or three times otherwise, as ldexp of a Ball).
/// Exact when nothing underflows: when every limb of every center of 2^n X and its radius is zero or
/// above the smallest normal number of T in magnitude (2^-1022 for double, 2^-126 for float), the
/// result is 2^n X itself, centers 2^n c_i and radius 2^n r exactly, and nothing is added; otherwise
/// the radius is the second number of T after 2^n r rounded to nearest, which covers what the
/// centers lost. Proved for each call, in the IEEE model, for a canonical X: canonical (V1); c x is
/// a member for every member x (V2); exactly c X under the condition above; finite when X is and
/// c r <= 2^(e_max - 2) and every entry has (|x_i| + r) c <= 2^(e_max - 2) (V4). Containment and
/// exactness of each call give those of the whole; the clamp of n near +-2098 (for double) is argued,
/// not machine-checked (packed_detail::bv_ldexp). z may be x (in place). Rounds; checked as add.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void ldexp(const X& x, int n, Z&& z) noexcept {
    packed_detail::ldexp<false>(x, n, z);
}
/// ldexp in the sequential order.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void ldexp(Sequential, const X& x, int n, Z&& z) noexcept {
    packed_detail::ldexp<true>(x, n, z);
}
/// Z = X / 2 (loop bv_mul_pow2_k with c = 1/2, one call): exact when every limb of every center of
/// X / 2 and its radius is zero or above the smallest normal number in magnitude (for double: every
/// nonzero limb of X above 2^-1021, and the radius zero or above 2^-1021). The halving of a
/// subdivision. As ldexp(x, -1, z) otherwise. z may be x (in place). Rounds; checked as add.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void half(const X& x, Z&& z) noexcept {
    packed_detail::half<false>(x, z);
}
/// half in the sequential order.
template <class X, class Z>
    requires kairn::detail::bv_unary<X, Z>
inline void half(Sequential, const X& x, Z&& z) noexcept {
    packed_detail::half<true>(x, z);
}

/// Z = a X + Y, a of T: the composition of two loops, made here and not machine-checked as one
/// (architecture.md, "axpy of ball vectors"): S = X a (scale, loop bv_scale_k) written into z, then
/// S + Y (add, loop bv_add_k) into z in place. What holds is the two loops' statements, composed:
/// containment, because for x in entry i of X and y in entry i of Y, a x is in entry i of S (the
/// scaling's V2), so a x + y is in entry i of Z (the sum's V2); the result is canonical (the sum's
/// V1); the whole space propagates (an operand of the sum that is the whole space gives it); a finite
/// Z has a finite S, hence finite X, a and Y. When it is finite is the V4 of each loop in turn, the
/// second on the computed S: (|x_i| + rx) |a| and |a| rx within 2^(e_max - 2), then |s_i + y_i| +
/// r_S + ry and r_S + ry within it; it is not stated once of X, Y and a. Not claimed: that the radius
/// is the largest of the entrywise radii of a Ball axpy (it is at least that, and equal when one
/// entry has both largest magnitudes, of the scaled centers and of the results). z may be exactly x.
/// It must not be y: the scaling would overwrite y before the sum reads it. When z's arrays are
/// those of y, a debug build reports it (KAIRN_CHECKS) and every build returns the whole space,
/// which contains the result, never a finite ball vector that does not; a X + Y written into Y
/// itself needs a loop that computes each entry in one pass, which does not exist yet (the
/// functions on arrays have one: kairn::axpy of batch.hpp accepts z = y). Rounds; checked as add.
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void axpy(std::type_identity_t<kairn::detail::bv_limb_t<X>> a, const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::axpy<false>(a, x, y, z);
}
/// axpy in the sequential order.
template <class X, class Y, class Z>
    requires kairn::detail::bv_binary<X, Y, Z>
inline void axpy(Sequential, std::type_identity_t<kairn::detail::bv_limb_t<X>> a, const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::axpy<true>(a, x, y, z);
}

/// Z = X Y as polynomials: coefficient j of Z is the sum over i of x_i y_(j-i), X of n_x
/// coefficients, Y of n_y, Z of n_x + n_y - 1 (none when a length is 0), in whatever basis the
/// product of polynomials is the convolution of their coefficients (the monomial basis; for the
/// Bernstein basis, the coefficients scaled by their binomials). Loop bv_conv_1 or bv_conv_2, the
/// sequential order only: the centers are the convolution conv_k (each coefficient the dot product
/// dot_k of its terms), the radius conv_radius(Ma, Mb, rx, ry, m, g, t), with Ma and Mb the largest
/// magnitudes of the leading limbs of the operands' centers, m = min(n_x, n_y) and (g, t) the bound
/// of a dot product of m terms (bound_dot_k): at least m ((1 + u) Ma ry + (1 + u) Mb rx + rx ry) +
/// g m (1 + u)^2 Ma Mb + t. Proved, in the IEEE model, for canonical X and Y: canonical (V1); for all
/// members x of X and y of Y, each entry ranging over its ball independently of the others, the exact
/// coefficient j of the product of x and y is within the radius of coefficient j (V2); a finite result
/// has finite operands (V3); and it is finite (V4) when X and Y are finite and, with n = min(n_x, n_y):
/// n (unit(K) + eta) <= 1/16 for one limb, n (unit(K) + eta / (2u)) <= 1/16 for two (unit(K) that of
/// the product mul_1_1 or mul_2_2), a condition on the length (above about 2^(p - 4) for one limb,
/// 2^42 - 1 for two limbs of float and 2^100 - 1 of double, the product is the whole space whatever
/// the values); rx ry <= 2^(e_max - 2); every entry of X has (|x_i| + rx) ry and every entry of Y
/// (|y_k| + ry) rx within 2^(e_max - 2); and every pair n (|x_i| + rx)(|y_k| + ry) within 2^(e_max -
/// 2). The radius uses the largest centers of each operand for every coefficient: for coefficients
/// that differ much in size it is pessimistic, by up to the factor m. z overlaps neither x nor y
/// (checked with KAIRN_CHECKS, not otherwise). Rounds; checked as add.
template <class X, class Y, class Z>
    requires kairn::detail::bv_product<X, Y, Z>
inline void convolution(const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::convolution(x, y, z);
}
/// convolution: the product has the sequential order only, and the tag changes nothing.
template <class X, class Y, class Z>
    requires kairn::detail::bv_product<X, Y, Z>
inline void convolution(Sequential, const X& x, const Y& y, Z&& z) noexcept {
    packed_detail::convolution(x, y, z);
}

/// An upper bound b of the magnitude of every entry of every member of X: b >= |x_i| for every i and
/// every member x. The composition of two calls, made here (architecture.md, "Ball vectors",
/// bv_norm_upper_k): n = norm_upper_k of the centers (the fold of maxima, which claims V <= n <=
/// RU(V) stepped up s times, V the largest magnitude of a center, s = 0 for one limb and 1 for two,
/// with a flag), then b = add_up(n, r) (blocks.hpp, kernel add_up_entry: RU(n + r)), or +inf when the
/// flag is false (two limbs, a leading limb of magnitude the largest finite number). Every member x
/// of entry i has |x| <= |c_i| + r <= V + r <= n + r <= b: the inequality is this header's argument
/// from the two claims, not the claim of one kernel; b is at most one rounding up and s steps above
/// the smallest such number of T. +inf for the whole space; for no entry, add_up(n, r) of the n of
/// no element (0, or the smallest subnormal number for two limbs). Rounds; checked as add.
template <class X>
    requires kairn::detail::bv_operand<X>
inline kairn::detail::bv_limb_t<X> norm_upper(const X& x) noexcept {
    return packed_detail::norm_upper<false>(x);
}
/// norm_upper in the sequential order.
template <class X>
    requires kairn::detail::bv_operand<X>
inline kairn::detail::bv_limb_t<X> norm_upper(Sequential, const X& x) noexcept {
    return packed_detail::norm_upper<true>(x);
}

// --- The operators and the functions that return a BallVector ----------------------------------

/// -X (neg), exactly.
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> operator-(const BallVector<T, K, N>& x) noexcept {
    BallVector<T, K, N> z;
    neg(x, z);
    return z;
}
/// X + Y (add).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> operator+(const BallVector<T, K, N>& x, const BallVector<T, K, N>& y) noexcept {
    BallVector<T, K, N> z;
    add(x, y, z);
    return z;
}
/// X - Y (sub).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> operator-(const BallVector<T, K, N>& x, const BallVector<T, K, N>& y) noexcept {
    BallVector<T, K, N> z;
    sub(x, y, z);
    return z;
}
/// X a (scale).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> operator*(const BallVector<T, K, N>& x, std::type_identity_t<T> a) noexcept {
    BallVector<T, K, N> z;
    scale(x, a, z);
    return z;
}
/// a X (scale).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> operator*(std::type_identity_t<T> a, const BallVector<T, K, N>& x) noexcept {
    BallVector<T, K, N> z;
    scale(x, a, z);
    return z;
}
/// X = X + Y (add, in place).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N>& operator+=(BallVector<T, K, N>& x, const BallVector<T, K, N>& y) noexcept {
    add(x, y, x);
    return x;
}
/// X = X - Y (sub, in place).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N>& operator-=(BallVector<T, K, N>& x, const BallVector<T, K, N>& y) noexcept {
    sub(x, y, x);
    return x;
}
/// X = X a (scale, in place).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N>& operator*=(BallVector<T, K, N>& x, std::type_identity_t<T> a) noexcept {
    scale(x, a, x);
    return x;
}
/// X 2^n (ldexp).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> ldexp(const BallVector<T, K, N>& x, int n) noexcept {
    BallVector<T, K, N> z;
    ldexp(x, n, z);
    return z;
}
/// X 2^n (ldexp), in the sequential order.
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> ldexp(Sequential s, const BallVector<T, K, N>& x, int n) noexcept {
    BallVector<T, K, N> z;
    ldexp(s, x, n, z);
    return z;
}
/// X / 2 (half).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> half(const BallVector<T, K, N>& x) noexcept {
    BallVector<T, K, N> z;
    half(x, z);
    return z;
}
/// X / 2 (half), in the sequential order.
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> half(Sequential s, const BallVector<T, K, N>& x) noexcept {
    BallVector<T, K, N> z;
    half(s, x, z);
    return z;
}
/// a X + Y (axpy: the composition of the scaling and the sum).
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> axpy(std::type_identity_t<T> a, const BallVector<T, K, N>& x,
                                const BallVector<T, K, N>& y) noexcept {
    BallVector<T, K, N> z;
    axpy(a, x, y, z);
    return z;
}
/// a X + Y (axpy), in the sequential order.
template <class T, int K, std::size_t N>
inline BallVector<T, K, N> axpy(Sequential s, std::type_identity_t<T> a, const BallVector<T, K, N>& x,
                                const BallVector<T, K, N>& y) noexcept {
    BallVector<T, K, N> z;
    axpy(s, a, x, y, z);
    return z;
}
/// X Y as polynomials (convolution), of N + M - 1 coefficients.
template <class T, int K, std::size_t N, std::size_t M>
inline BallVector<T, K, N + M - 1> convolution(const BallVector<T, K, N>& x, const BallVector<T, K, M>& y) noexcept {
    BallVector<T, K, N + M - 1> z;
    convolution(x, y, z);
    return z;
}
/// X Y as polynomials (convolution); the tag changes nothing.
template <class T, int K, std::size_t N, std::size_t M>
inline BallVector<T, K, N + M - 1> convolution(Sequential, const BallVector<T, K, N>& x,
                                               const BallVector<T, K, M>& y) noexcept {
    BallVector<T, K, N + M - 1> z;
    convolution(x, y, z);
    return z;
}

KAIRN_DETAIL_PACKED_END
}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
