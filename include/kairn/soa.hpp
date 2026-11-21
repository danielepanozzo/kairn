/// @file
/// Structure-of-arrays storage of k-numbers: SoA<T, k>, which owns N numbers as k arrays of N limbs
/// of type T (float or double), one per limb; SoAView<T, k> and SoAView<const T, k>, which own
/// nothing and see k arrays and a length, the program's own or an SoA's; and SoARef<T, k>, the
/// proxy of one element (docs/developer/design/milestone2.md, "Packed type and containers").
///
/// They move limbs and compute nothing, with one exception: reading an element, or a Packed,
/// goes through the constructor of Expansion from its limbs, which guards each limb (an addition of
/// +0, rule R3 of expansion.hpp: the program may have written a product there that the compiler
/// could still fuse into the next operation) and, with KAIRN_CHECKS 1, checks the pair. What holds:
/// - an element read is the value written: the limbs written, except that a zero limb of a
///   two-limb number may come back with the other sign (the guard), which does not change the
///   value; a one-limb element is read as written, bit for bit;
/// - with KAIRN_CHECKS 1 (config.hpp), every read of a two-limb element (operator[] converted, get,
///   load) is Expansion<T, 2>::from_limbs, which checks the environment and then that the limbs
///   form a canonical pair, and stops the program with its message if not; with KAIRN_CHECKS 0 it
///   is from_limbs_unchecked;
/// - a view does not own and never allocates; an SoA allocates in the functions that say so, and
///   nowhere else.
///
/// Not checked, in any build: indices and counts (as for std::span), and that the k arrays of a
/// view have the given length. No alignment is required anywhere: Packed loads and stores are
/// unaligned. An SoA starts each of its arrays at a multiple of 64 bytes; a view takes the arrays
/// as they are.
///
/// The tail of a loop: for N elements and W = Packed<T, k>::lanes, the elements 0 to
/// N - N % W - 1 are read with load(i) and written with store(i, p) at i = 0, W, 2W, ...; the last
/// N % W, if any, with load_partial(i, N - i, fill) and store_partial(i, p, N - i), which read and
/// write those elements only and put fill (zero by default) in the other lanes. Nothing is done to
/// the lanes beyond the end but what the program does to them.
#pragma once

#include "packed.hpp"

#include <cstddef>
#include <cstring>
#include <new>
#include <type_traits>
#include <utility>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn {

template <class T, int K>
class SoAView;

namespace detail {
// What an SoA or a view may hold: float or double limbs, const for a view of a read-only array.
template <class T, int K>
concept soa_element = limb<std::remove_const_t<T>> && (K == 1 || K == 2);

// Element i of K arrays as a number: from_limbs when KAIRN_CHECKS is 1, which checks it,
// from_limbs_unchecked otherwise; both guard the limbs.
template <class T, int K>
KAIRN_FORCEINLINE Expansion<T, K> read_element(const T* const* limbs, std::size_t i) noexcept {
    T x[K];
    for (int j = 0; j < K; ++j) x[j] = limbs[j][i];
#if KAIRN_CHECKS
    return Expansion<T, K>::from_limbs(x);
#else
    return Expansion<T, K>::from_limbs_unchecked(x);
#endif
}
}  // namespace detail

/// One element of K arrays of limbs: what operator[] of a view or of an SoA returns. It converts
/// to Expansion<T, K> (reading the element, as get() does) and, when T is not const, is assigned
/// from one (writing its limbs, copied). Assigning one SoARef to another assigns the value, never
/// the reference.
///
/// The operators of Expansion deduce their operands' types and see no conversion: convert an
/// element first, `Expansion<double, 2> x = v[i];` or `v.get(i)`, before using it in an operation.
/// An SoARef refers to the arrays, not to the view it came from, and is valid while they are.
template <class T, int K>
class SoARef {
    static_assert(detail::soa_element<T, K>, "SoARef<T, k>: T is float or double, or const, and k is 1 or 2");

public:
    /// The number of one element.
    using value_type = Expansion<std::remove_const_t<T>, K>;

    /// A copy refers to the same element. Assigning to a SoARef writes the element and never
    /// rebinds the reference, so a copy is made by construction only.
    SoARef(const SoARef&) noexcept = default;

    /// The element, as get() reads it.
    KAIRN_FORCEINLINE operator value_type() const noexcept { return get(); }
    /// The element: Expansion<T, K>::from_limbs of its limbs when KAIRN_CHECKS is 1 (checked),
    /// from_limbs_unchecked otherwise.
    KAIRN_FORCEINLINE value_type get() const noexcept {
        const std::remove_const_t<T>* p[K];
        for (int j = 0; j < K; ++j) p[j] = limb_[j];
        return detail::read_element<std::remove_const_t<T>, K>(p, 0);
    }
    /// Writes x: its limbs, copied. Only when T is not const.
    KAIRN_FORCEINLINE const SoARef& operator=(const value_type& x) const noexcept
        requires(!std::is_const_v<T>)
    {
        for (int j = 0; j < K; ++j) *limb_[j] = x.limb[j];
        return *this;
    }
    /// Writes the value of r (read as get() reads it), not the reference. Only when T is not const.
    KAIRN_FORCEINLINE const SoARef& operator=(const SoARef& r) const noexcept
        requires(!std::is_const_v<T>)
    {
        return *this = r.get();
    }

private:
    template <class U, int J>
    friend class SoAView;
    KAIRN_FORCEINLINE SoARef(T* const* limbs, std::size_t i) noexcept {
        for (int j = 0; j < K; ++j) limb_[j] = limbs[j] + i;
    }
    T* limb_[K];
};

/// N numbers of K limbs held as K arrays of N limbs of the program's, or of an SoA: K pointers and
/// a length. T is float or double, or const float or const double for a view through which
/// nothing can be written; a view of T converts to a view of const T. Owns nothing, allocates
/// nothing; trivially copyable, so cheap to pass by value. Constness is shallow, as for std::span:
/// a const SoAView<double, 2> still writes.
///
/// At K = 1 it is a view of one plain array of T: element i is the number x0[i].
template <class T, int K>
class SoAView {
    static_assert(detail::soa_element<T, K>, "SoAView<T, k>: T is float or double, or const, and k is 1 or 2");
    using V = std::remove_const_t<T>;

public:
    /// The limb type, float or double.
    using limb_type = V;
    /// T: the limb type, const for a read-only view.
    using element_type = T;
    /// The number of one element.
    using value_type = Expansion<V, K>;
    /// What operator[] returns.
    using reference = SoARef<T, K>;
    /// The packed numbers of load() and store().
    using packed_type = Packed<V, K>;
    /// K.
    static constexpr int limbs = K;

    /// No elements.
    constexpr SoAView() noexcept = default;
    /// One limb: the n numbers x0[0] .. x0[n - 1].
    constexpr SoAView(T* x0, std::size_t n) noexcept
        requires(K == 1)
        : limb_{x0}, size_(n) {}
    /// Two limbs: the n numbers whose limbs are x0[i] and x1[i]; both arrays have n elements.
    constexpr SoAView(T* x0, T* x1, std::size_t n) noexcept
        requires(K == 2)
        : limb_{x0, x1}, size_(n) {}
    /// A read-only view of the same arrays as v.
    template <class U>
        requires(std::is_const_v<T> && std::is_same_v<const U, T>)
    constexpr SoAView(const SoAView<U, K>& v) noexcept : size_(v.size()) {
        for (int j = 0; j < K; ++j) limb_[j] = v.limb(j);
    }

    /// N.
    constexpr std::size_t size() const noexcept { return size_; }
    /// Whether N is zero.
    constexpr bool empty() const noexcept { return size_ == 0; }
    /// The array of limb j, 0 for the leading limbs, of size() elements: with the length, what a
    /// view is made of; the functions on arrays of batch.hpp take the view itself.
    constexpr T* limb(int j) const noexcept { return limb_[j]; }
    /// The count elements from offset on, offset + count <= N.
    constexpr SoAView subview(std::size_t offset, std::size_t count) const noexcept {
        SoAView v;
        for (int j = 0; j < K; ++j) v.limb_[j] = limb_[j] + offset;
        v.size_ = count;
        return v;
    }

    /// Element i, i < N, as a proxy: it reads as get(i) and, unless T is const, writes as set(i, x).
    KAIRN_FORCEINLINE reference operator[](std::size_t i) const noexcept { return reference(limb_, i); }
    /// Element i as a number: Expansion<T, K>::from_limbs of its limbs when KAIRN_CHECKS is 1
    /// (for two limbs, checked: a pair that is not canonical stops the program), from_limbs_unchecked
    /// otherwise.
    KAIRN_FORCEINLINE value_type get(std::size_t i) const noexcept {
        const V* p[K];
        for (int j = 0; j < K; ++j) p[j] = limb_[j];
        return detail::read_element<V, K>(p, i);
    }
    /// Writes x into element i: its limbs, copied.
    KAIRN_FORCEINLINE void set(std::size_t i, const value_type& x) const noexcept
        requires(!std::is_const_v<T>)
    {
        for (int j = 0; j < K; ++j) limb_[j][i] = x.limb[j];
    }

    // load and load_partial are templates only so that their names, mangled with the return type,
    // differ between the forms of Packed (packed.hpp, KAIRN_PACKED_FORM): two translation units
    // compiled for different instruction sets may then use one view type in one program.

    /// Elements i to i + W - 1, i + W <= N, as Packed<T, K>::load reads them (with its check).
    template <class P = packed_type>
        requires std::is_same_v<P, packed_type>
    KAIRN_FORCEINLINE P load(std::size_t i) const noexcept {
        if constexpr (K == 1) {
            return P::load(limb_[0] + i);
        } else {
            return P::load(limb_[0] + i, limb_[1] + i);
        }
    }
    /// The tail: elements i to i + count - 1, count <= W and i + count <= N, in lanes 0 to
    /// count - 1, as Packed<T, K>::load_partial reads them, and fill in the other lanes.
    template <class P = packed_type>
        requires std::is_same_v<P, packed_type>
    KAIRN_FORCEINLINE P load_partial(std::size_t i, int count, const value_type& fill = value_type()) const noexcept {
        if constexpr (K == 1) {
            return P::load_partial(limb_[0] + i, count, fill);
        } else {
            return P::load_partial(limb_[0] + i, limb_[1] + i, count, fill);
        }
    }
    /// Writes the W lanes of p into elements i to i + W - 1, i + W <= N: the limbs, copied.
    KAIRN_FORCEINLINE void store(std::size_t i, const packed_type& p) const noexcept
        requires(!std::is_const_v<T>)
    {
        if constexpr (K == 1) {
            p.store(limb_[0] + i);
        } else {
            p.store(limb_[0] + i, limb_[1] + i);
        }
    }
    /// The tail: writes lanes 0 to count - 1 of p into elements i to i + count - 1, and nothing
    /// else.
    KAIRN_FORCEINLINE void store_partial(std::size_t i, const packed_type& p, int count) const noexcept
        requires(!std::is_const_v<T>)
    {
        if constexpr (K == 1) {
            p.store_partial(limb_[0] + i, count);
        } else {
            p.store_partial(limb_[0] + i, limb_[1] + i, count);
        }
    }

private:
    T* limb_[K] = {};
    std::size_t size_ = 0;
};

/// N numbers of K limbs of type T (float or double), owned, as K arrays of N limbs in one
/// allocation, each array starting at a multiple of 64 bytes. Elements are zero when made.
///
/// Allocates (and may throw std::bad_alloc, or std::bad_array_new_length when K N limbs do not fit
/// in a std::size_t): the constructors that take a size, the copy constructor, the copy assignment
/// and resize(). Nothing else allocates or throws: moving, element access, views, load and store
/// are noexcept. Moved from, an SoA is empty.
template <class T, int K>
class SoA {
    static_assert(detail::soa_element<T, K> && !std::is_const_v<T>, "SoA<T, k>: T is float or double, and k is 1 or 2");

public:
    /// The limb type.
    using limb_type = T;
    /// The number of one element.
    using value_type = Expansion<T, K>;
    /// What operator[] returns.
    using reference = SoARef<T, K>;
    /// What operator[] of a const SoA returns.
    using const_reference = SoARef<const T, K>;
    /// The packed numbers of load() and store().
    using packed_type = Packed<T, K>;
    /// K.
    static constexpr int limbs = K;
    /// The alignment of each array, in bytes.
    static constexpr std::size_t alignment = 64;

    /// No elements; allocates nothing.
    SoA() noexcept = default;
    /// n zeros.
    explicit SoA(std::size_t n) : SoA() { reset(n); }
    /// n copies of x.
    SoA(std::size_t n, const value_type& x) : SoA(n) {
        for (int j = 0; j < K; ++j)
            for (std::size_t i = 0; i < n; ++i) data_[j * stride_ + i] = x.limb[j];
    }
    /// A copy of every element.
    SoA(const SoA& other) : SoA(other.size_) {
        for (int j = 0; j < K; ++j) copy(other.limb(j), data_ + j * stride_, size_);
    }
    /// Takes other's arrays; other is left empty.
    SoA(SoA&& other) noexcept
        : data_(std::exchange(other.data_, nullptr)), size_(std::exchange(other.size_, 0)),
          stride_(std::exchange(other.stride_, 0)) {}
    /// A copy of every element of other; on an exception, *this is unchanged.
    SoA& operator=(const SoA& other) {
        if (this != &other) {
            SoA copy_of(other);
            swap(copy_of);
        }
        return *this;
    }
    /// Takes other's arrays; other is left empty.
    SoA& operator=(SoA&& other) noexcept {
        if (this != &other) {
            SoA taken(std::move(other));
            swap(taken);
        }
        return *this;
    }
    ~SoA() { release(data_); }

    /// N.
    std::size_t size() const noexcept { return size_; }
    /// Whether N is zero.
    bool empty() const noexcept { return size_ == 0; }
    /// N becomes n: the first min(n, N) elements are kept, the others are zero. Allocates new
    /// arrays (unless n == N), so views and SoARefs of the old ones are no longer valid; on an
    /// exception, nothing changes.
    void resize(std::size_t n) {
        if (n == size_) return;
        SoA bigger(n);
        const std::size_t kept = n < size_ ? n : size_;
        for (int j = 0; j < K; ++j) copy(data_ + j * stride_, bigger.data_ + j * bigger.stride_, kept);
        swap(bigger);
    }
    /// Exchanges the arrays of the two.
    void swap(SoA& other) noexcept {
        std::swap(data_, other.data_);
        std::swap(size_, other.size_);
        std::swap(stride_, other.stride_);
    }

    /// The array of limb j, of size() elements, starting at a multiple of 64 bytes (a null pointer
    /// when N is zero).
    T* limb(int j) noexcept { return data_ + j * stride_; }
    /// The array of limb j, read-only.
    const T* limb(int j) const noexcept { return data_ + j * stride_; }
    /// A view of every element.
    SoAView<T, K> view() noexcept {
        if constexpr (K == 1) {
            return SoAView<T, K>(data_, size_);
        } else {
            return SoAView<T, K>(data_, data_ + stride_, size_);
        }
    }
    /// A read-only view of every element.
    SoAView<const T, K> view() const noexcept {
        if constexpr (K == 1) {
            return SoAView<const T, K>(data_, size_);
        } else {
            return SoAView<const T, K>(data_, data_ + stride_, size_);
        }
    }
    /// view().
    operator SoAView<T, K>() noexcept { return view(); }
    /// view(), read-only.
    operator SoAView<const T, K>() const noexcept { return view(); }

    /// Element i, as view()[i].
    KAIRN_FORCEINLINE reference operator[](std::size_t i) noexcept { return view()[i]; }
    /// Element i, read-only, as view()[i].
    KAIRN_FORCEINLINE const_reference operator[](std::size_t i) const noexcept { return view()[i]; }
    /// Element i as a number, as SoAView::get.
    KAIRN_FORCEINLINE value_type get(std::size_t i) const noexcept { return view().get(i); }
    /// Writes x into element i.
    KAIRN_FORCEINLINE void set(std::size_t i, const value_type& x) noexcept { view().set(i, x); }
    /// As SoAView::load.
    template <class P = packed_type>
        requires std::is_same_v<P, packed_type>
    KAIRN_FORCEINLINE P load(std::size_t i) const noexcept {
        return view().template load<P>(i);
    }
    /// As SoAView::load_partial.
    template <class P = packed_type>
        requires std::is_same_v<P, packed_type>
    KAIRN_FORCEINLINE P load_partial(std::size_t i, int count, const value_type& fill = value_type()) const noexcept {
        return view().template load_partial<P>(i, count, fill);
    }
    /// As SoAView::store.
    KAIRN_FORCEINLINE void store(std::size_t i, const packed_type& p) noexcept { view().store(i, p); }
    /// As SoAView::store_partial.
    KAIRN_FORCEINLINE void store_partial(std::size_t i, const packed_type& p, int count) noexcept {
        view().store_partial(i, p, count);
    }

private:
    // n zero elements, in one block of K arrays of stride_ limbs, stride_ a multiple of 64 bytes.
    void reset(std::size_t n) {
        if (n == 0) return;
        constexpr std::size_t per_line = alignment / sizeof(T);
        constexpr std::size_t most = static_cast<std::size_t>(-1) / (K * sizeof(T));
        if (n > most - per_line) throw std::bad_array_new_length();
        const std::size_t stride = (n + per_line - 1) / per_line * per_line;
        void* block = ::operator new(K * stride * sizeof(T), std::align_val_t(alignment));
        std::memset(block, 0, K * stride * sizeof(T));
        data_ = static_cast<T*>(block);
        size_ = n;
        stride_ = stride;
    }
    static void release(T* p) noexcept {
        if (p) ::operator delete(p, std::align_val_t(alignment));
    }
    static void copy(const T* from, T* to, std::size_t n) noexcept {
        if (n) std::memcpy(to, from, n * sizeof(T));
    }

    T* data_ = nullptr;
    std::size_t size_ = 0;
    std::size_t stride_ = 0;
};

/// Exchanges the arrays of a and b.
template <class T, int K>
void swap(SoA<T, K>& a, SoA<T, K>& b) noexcept {
    a.swap(b);
}

}  // namespace kairn
KAIRN_GEN_POP_WARNINGS
