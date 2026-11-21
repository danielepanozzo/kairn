# Arrays of numbers: SoA and its views

`kairn/soa.hpp` holds numbers of $k$ limbs as one array per limb (structure of arrays), the
layout in which [`Packed<T, k>`](packed.md) loads $W$ of them at once:

- `kairn::SoA<T, k>` owns $N$ numbers, $k$ arrays of $N$ limbs of type `T`;
- `kairn::SoAView<T, k>` sees $k$ arrays and a length that someone else owns, the program or an
  `SoA`, and `kairn::SoAView<const T, k>` sees them read-only;
- `kairn::SoARef<T, k>` is what `v[i]` returns: element $i$, which converts to
  `Expansion<T, k>` and is assigned from one.

`T` is `float` or `double` and $k$ is 1 or 2. `kairn/kairn.hpp` does not include the header
([Packed](packed.md#compile-time) says why); `kairn/soa.hpp` includes `kairn/packed.hpp`.

**Status: they move limbs and compute nothing, but the guard of a read.** What holds:

- **An element read is the value written.** Read through `v[i]` (converted), `get(i)`, a const
  view or `load(i)`, a two-limb element is `Expansion<T, 2>::from_limbs` of its limbs, which
  guards each limb (an addition of $+0$, [rule R3](../developer/architecture.md#the-kernel-ir):
  the program may have written a product there that the compiler could still fuse into the next
  operation): the limbs written, except that a zero limb may come back with the other sign, which
  does not change the value. A one-limb element is read as written, bit for bit.
- **A read is checked in a build with checks.** With `KAIRN_CHECKS` 1, every read of a two-limb
  element is `from_limbs`, which checks the environment and then that the limbs form a canonical
  pair, and stops the program with `kairn: from_limbs: the limbs are not a canonical pair ...` if
  they do not; with `KAIRN_CHECKS` 0 it is `from_limbs_unchecked`. A write copies the limbs and
  checks nothing.
- **A view owns nothing and never allocates.** An `SoA` allocates in the functions that say so,
  and nowhere else.

```cpp
template <class T, int K> class SoAView {        // T may be const
    SoAView();                                   // no elements
    SoAView(T* x0, std::size_t n);               // K = 1: a plain array of T
    SoAView(T* x0, T* x1, std::size_t n);        // K = 2
    SoAView(const SoAView<U, K>&);               // a view of U converts to one of const U
    std::size_t size() const;  bool empty() const;
    T* limb(int j) const;                        // the array of limb j
    SoAView subview(std::size_t offset, std::size_t count) const;
    SoARef<T, K> operator[](std::size_t i) const;
    Expansion<T, K> get(std::size_t i) const;    void set(std::size_t i, const Expansion<T, K>&) const;
    Packed<T, K> load(std::size_t i) const;      void store(std::size_t i, const Packed<T, K>&) const;
    Packed<T, K> load_partial(std::size_t i, int count, const Expansion<T, K>& fill = {}) const;
    void store_partial(std::size_t i, const Packed<T, K>&, int count) const;
};
template <class T, int K> class SoA {            // the same element access, and:
    SoA();  explicit SoA(std::size_t n);  SoA(std::size_t n, const Expansion<T, K>& x);
    void resize(std::size_t n);  void swap(SoA&);
    SoAView<T, K> view();  SoAView<const T, K> view() const;   // and the conversions to them
};
```

## Views

A view is $k$ pointers and a length, trivially copyable, cheap to pass by value. It is how a
program maps its own buffers: `SoAView<double, 2> v(hi.data(), lo.data(), n)` sees the numbers
whose limbs are `hi[i]` and `lo[i]`, and writes through `v` go to those arrays. At $k = 1$ a view
is one plain array of `T`. `limb(j)` gives the array back, and `subview(offset, count)` sees a
part; the functions on arrays of [`kairn/batch.hpp`](batch.md) take the view itself.

A view of `T` converts to a view of `const T`, not back; through a view of `const T` nothing
can be written (`v[i] = x`, `set`, `store` do not compile, nor does one element of it assigned
from another). Constness of the view itself is shallow, as for `std::span`: a
`const SoAView<double, 2>` still writes.

The proxy. `Expansion<double, 2> x = v[i];` reads element $i$ as `get(i)` does, and `v[i] = x`
writes its limbs. Assigning `v[i] = v[j]` copies the value, never the reference. The operators of
`Expansion` deduce their operands' types and see no conversion, so an element is converted first
(`Expansion<T, k>(v[i])` or `v.get(i)`) before it is an operand. An `SoARef` refers to the
arrays, not to the view it came from.

## Packed numbers at an index

`load(i)` reads elements $i$ to $i + W - 1$ as [`Packed<T, k>::load`](packed.md#moves-loads-and-stores)
does, with its check; `store(i, p)` writes them. **The tail of a loop**: for $N$ elements, the
elements up to $N - (N \bmod W) - 1$ are read with `load(i)` and written with `store(i, p)` at
$i = 0, W, 2W, \ldots$; the last $N \bmod W$, if any, with `load_partial(i, N - i, fill)` and
`store_partial(i, p, N - i)`, which read and write those elements only and put `fill`, zero by
default, in the other lanes. What happens to those lanes is what the program does to them: zero
lanes add nothing to a sum, and a product wants `fill` 1.

No alignment is required: the loads and stores of `Packed` are unaligned, and a view takes the
arrays as they are. Indices and counts are not checked, in any build, as for `std::span`, nor is
the length of the arrays given to a view.

## SoA

An `SoA<T, k>` owns its $k$ arrays in one allocation, each array starting at a multiple of 64
bytes (`SoA::alignment`), so that a load of `Packed` from a group starting at a multiple of $W$
never straddles a cache line it could avoid. Elements are zero when made. One allocation rather
than $k$: the arrays always have the same length, so one block is made, moved and freed as one,
and a constructor fails as a whole or not at all.

Allocates, and may throw `std::bad_alloc` (or `std::bad_array_new_length` when $k N$ limbs do not
fit in a `std::size_t`): the constructors that take a size, the copy constructor, the copy
assignment and `resize`. Nothing else allocates or throws: moving, element access, views, `load`
and `store` are `noexcept`. `resize(n)` keeps the first $\min(n, N)$ elements and makes the new
ones zero, in new arrays (views of the old ones are then invalid); on an exception nothing
changes. A moved-from `SoA` is empty. An `SoA` converts to its views, mutable and read-only, and
a const `SoA` to a read-only one only.

## What is tested

`tests/api/soa.cpp`, in every form of `Packed` (the build's, the scalar one and, on x86-64 where
the build lacks it, AVX2): every element written and read back through every path, for lengths
around the lanes (0, 1, $W - 1$, $W$, $W + 1$, $2W - 1$, $2W + 1$, 37), with zeros of both signs,
subnormal numbers, the largest finite number, infinities and NaN; the tail rule, reading and
writing exactly $N$ elements; views of `std::vector` and plain arrays; the properties of the types
(trivially copyable views, the conversions that exist and those that do not, what cannot be
written); and every allocation, counted by the program's own `operator new`. The compile-fail
cases (`api.reject.soa.*`), the checks of a non-canonical element (`api.checks.*`) and the reads of
the oracle's lines through a view (the runner's packed forms `soa_get`, `soa_load`,
`soa_load_partial` of `make_2_limbs`) are in [Testing](../developer/testing.md#packed-and-the-containers).
