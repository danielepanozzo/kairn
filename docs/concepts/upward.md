# The round-up interval

**This header requires compiler options and scopes.** A file that includes `kairn/upward.hpp` is
compiled with `-frounding-math` (GCC and Clang) or `/fp:strict` (MSVC), which the CMake target
`kairn::upward` adds, and every operation of the header that rounds runs inside an upward scope of
the header, a `kairn::upward::Scope` or the one that each function on arrays holds, which sets the
rounding mode upward. The default types of Kairn do not change in any way: they round to nearest,
never change the floating-point environment, and need no option
([The floating-point environment](environment.md)).

`kairn/upward.hpp` is an opt-in alternative to `Interval<T, 1>`, the interval of one limb, used
only for speed: one interval of `float` or `double` kept as two numbers in one SIMD register and
computed under the rounding mode upward. `kairn/kairn.hpp` does not include it. Its interface, in
namespace `kairn::upward`, is the interval type `Interval<T>`; the functions on arrays, on views
`View<T>` of two plain arrays; the scopes `Scope` and `NearestScope`; `pass()`; and `self_test()`
([The interface](../developer/design/upward.md#the-interface), in the design page; the
[reference](../reference/index.md#the-round-up-interval) has every operation, with the kernel it
calls). This page says what it is for, how its intervals are stored, what a program must
guarantee for its results to hold, how it differs from the default interval, and what its checks
see and do not see.

Intervals of two and four limbs of `double` computed the same way, with these scopes and options,
are in the headers `kairn/experimental/upward2.hpp` and `kairn/experimental/upward4.hpp`, which are
**EXPERIMENTAL and NOT VERIFIED**: no bound of theirs is proved, and a file opts in to include them
([Two and four limbs rounded upward](experimental.md)). Everything this page says of proofs is
about `kairn/upward.hpp` alone.

## What it is for

For intervals of one limb in a hot loop, where the default interval's bounds cost more than the
operations they round: the default types compute each bound rounded down or up under rounding to
nearest, in several operations, because they never change the mode
([What they cost](enclosures.md#what-they-cost-and-how-wide-they-are)). Under the mode upward the
hardware rounds both bounds in the direction that widens the interval, and the two are computed
together: a sum is one vector addition, a difference one addition and one exchange of the two lanes,
a negation one exchange, and a product four vector multiplications and three maxima, with
selections for the special cases and no branch ([The kernels](../developer/design/upward.md#the-kernels)).
A sum and a product, next to the same with the default interval:

```cpp
--8<-- "docs/examples/cpp/concepts_upward.cpp:scope"
```

```text
--8<-- "docs/examples/cpp/concepts_upward.txt:2:5"
```

The two types give the same bounds here; they always do for sums, differences and the exact
operations, and for products wherever no product of finite bounds is nonzero and below
$2^{2p-1}\eta$, where the default product may be one number of `T` wider. The program is
[`docs/examples/cpp/concepts_upward.cpp`](https://github.com/danielepanozzo/kairn/blob/main/docs/examples/cpp/concepts_upward.cpp),
which ctest builds with `kairn::upward`, with the build's flags and under each contraction setting
of the compiler but MSVC's, and whose output it compares with the text on this page each time
(`api.example.concepts_upward`).

How much faster, measured on the shipped header on the two test machines
([Benchmarks](../developer/results/bench-upward.md#1-the-type-against-the-default-interval)): in a
loop inside one scope a sum of `double` was 2.5 to 7.5 times faster than the default
`Interval<double, 1>`'s, a product 4.3 to 8.5 times, and a 3 by 3 determinant of differences, the
filter of an orientation test, 8.4 to 22 times. Converting from and to the default interval inside
the loop gives most of that back (a sum 1.2 to 1.7 times faster, a product 1.8 to 3.9 times): keep
the values in the round-up type across a computation.

A typical use is a *filter* that decides a sign: an expression evaluated on intervals whose result
excludes zero has a known sign, and only the cases where it does not fall back to something slower
and exact:

```cpp
--8<-- "docs/examples/cpp/concepts_upward.cpp:filter"
```

```text
--8<-- "docs/examples/cpp/concepts_upward.txt:8:8"
```

The third call is $a = 1 + 2^{-52}$, $d = 1 - 2^{-52}$, $b = c = 1$: $ad - bc = -2^{-104}$, and the
interval of $ad$ rounded outward, $[1 - 2^{-53}, 1]$, contains $bc = 1$, so the result's interval
contains zero and the sign is the program's to find another way.

What it does not have: a midpoint, a radius, `mid_rad`, `split`, conversions to or from a `Ball`,
and bounds of two limbs, since each of them needs rounding to nearest. A program converts to the
default interval for those, in a `NearestScope` or outside an upward scope
([below](#a-nearestscope-inside-a-scope)).

## How an interval is stored

The interval $[a, b]$ is the pair $(u, n) = (b, -a)$: lane 0, first in memory, the upper bound, and
lane 1 the lower bound negated. Under the mode upward both lanes then round in the direction that
widens the interval, since rounding down is rounding up of the negation,
$\mathrm{RD}(t) = -\mathrm{RU}(-t)$. The empty set is $(\mathrm{NaN}, \mathrm{NaN})$ and the whole
line $(+\infty, +\infty)$; the members are real numbers, as for the default interval, so
$[1, +\infty]$ does not contain $+\infty$. Lane 0 is the upper bound because that is the order in
which the first client stores the two numbers, so that such pairs can be passed in as they are
([The stored pair](../reference/upward.md#the-stored-pair) has the table of states).
`Interval<T>::from_limbs(p)` reads the pair $(p_0, p_1) = (u, n)$ in one load, and `to_limbs(p)`
writes it in one store; the round trip gives every bit back. What `from_limbs` is given must be a
canonical state, as an operation returns it: the empty set with both lanes quiet NaNs, or no NaN
lane, no lane $-\infty$ and $-n \le u$; a checked build checks it ([Checks](#checks)).

The conversions from and to the default `Interval<T, 1>`, the constructor
`kairn::upward::Interval<T>(x)` and `x.to_interval()`, are exact (a negation and selections) and
keep the set; neither is implicit, and only the sign of a zero bound can differ
([Conversions](../developer/design/upward.md#conversions)).

## What the program guarantees

The header's results are what the statements of its kernels say only where the program does the
following ([What the program guarantees](../developer/design/upward.md#what-the-program-guarantees),
in the design page).

1. **The options.** GCC and Clang: `-frounding-math`. MSVC: `/fp:strict`, which excludes
   `/fp:contract`. Every file that includes the header is compiled with them, and so is the
   program's own code in that file. They are the program's responsibility, by the owner's decision
   of 2026-11-24. The refusals of the default types hold as well: no fast-math, no
   finite-math-only, no reassociation
   ([Contraction and fast-math](environment.md#contraction-and-fast-math)). Both options are ones
   the default types accept, so a file may use the two kinds of interval.
2. **The mode only through the header's scopes.** Every operation that rounds runs inside a
   `kairn::upward::Scope`, or inside a function on arrays, which holds a scope of its own. The mode
   is never set by hand around the header's operations, with `fesetround`, `_mm_setcsr` or
   `_controlfp_s`: on GCC and Clang the header's barriers keep its operations in order with the
   scopes' own barriers, not with an arbitrary call, and on MSVC the scope is what makes the
   operations right ([MSVC](#msvc)).
3. **One set of options per program.** The files of a program that use the header are built with
   the same options. Every function of the header whose result can depend on the options has
   internal linkage, so that each file runs its own copy; that does not cover a function of the
   program's own that is inline and included in files built differently, of which the linker keeps
   one copy for all of them. The class `Interval<T>` and `View<T>` have external linkage, so that
   files pass intervals to one another; the member functions of `Interval<T>` compute only exact
   operations, whose results do not depend on the options.
4. **Each thread holds its own scope.** The mode belongs to the thread. A thread started inside a
   scope inherits the mode on some systems and not on others; the header never relies on it.
5. **Other code inside a scope runs under the mode**: the program's own arithmetic, the C library's
   mathematical functions, and the default Kairn types, whose kernels assume rounding to nearest. A
   program calls the default types inside a `NearestScope` ([The scopes](#the-scopes)). A build with
   `KAIRN_CHECKS` reports a default type called under the mode upward, and so does the check that
   the default functions on arrays make in every build, but for the two that compute no sum
   ([The checks](environment.md#the-checks)).

### Code next to a scope's boundary

The header's barriers order its own operations against its scopes. Code without them can still be
moved across a scope's boundary by the compiler: an operation of the program, or of a default type,
whose operands are already in registers may be computed before a `NearestScope` begins, so under the
mode upward, or before an upward scope ends while the program meant it after. So a program brings
values **into a `NearestScope`**, and **out of an upward region**, through memory, `to_interval()` or
`kairn::upward::pass()`:

- `kairn::upward::pass(v)` returns `v`, the same bits, after a barrier (on MSVC, after the refresh
  of the most recent scope that wrote the mode), so that a computation on its result happens after
  the most recent boundary of a scope; for a `T`, a default `Interval<T, 1>` and the round-up
  interval;
- `to_interval()`, the conversion to the default interval, puts a barrier on its results, so that a
  default interval converted inside a `NearestScope` is computed on there.

The header promises nothing more about code without barriers that shares a function with a scope;
the self-check probes both directions in its own shapes ([The self-check](#the-self-check)), and
its advice says when a computation of the default types right after an upward scope came out as if
computed inside it.

The movement is real. The tests `api.upward.moves` probe it in more shapes, at every optimization
level ([Testing](../developer/testing.md#code-next-to-a-scopes-boundary)). With the options, when
the values crossed the boundary in registers: GCC 13 and GCC 16, from `-O1` on, computed once a sum
of the program, or of an `Expansion<T, 1>`, that the program wrote on both sides of a boundary, and
computed a sum that does not change in a loop once, before the loop, although each iteration held
its own scope; MSVC 19.52, from `/O1` on, did the second, for a `Scope` and for a `NearestScope` in
each iteration; Clang 18 and Apple clang 21 moved nothing. No compiler moved a computation whose
values crossed the boundary through memory, `to_interval()` or `pass()`, at any level, and none
moved an operation of the header.

## The scopes

`kairn::upward::Scope` sets the rounding mode upward for its lifetime, and
`kairn::upward::NearestScope` sets it to nearest; each restores what it found when it ends. Both
have internal linkage, so that each file compiles its own, and neither can be copied or moved.

- **On entry** a scope reads the control register (MXCSR on x86-64, FPCR on AArch64) and writes it
  only when something must change: the mode, and flush to zero and denormals-are-zero, which it
  turns off. It also makes the C library's mode (`std::fegetround()`) the same, so that the
  program's own code sees that mode: on AArch64 the register is the C library's state, and on x86-64,
  where the C library may keep its own, the scope calls `std::fesetround` when it reports another
  mode. Then a barrier; on MSVC, the refresh of [MSVC](#msvc); and, in a checked build, when an
  upward scope wrote the mode, the check that the file's build honors it ([Checks](#checks)).
- **On exit**, a barrier, then the register and the C library's mode restored as the entry found
  them, but for the exception flags raised inside, which are kept (on AArch64 they are in FPSR,
  which no scope touches); on MSVC, the refresh again when the exit wrote the register.
- On a target with neither register the scope sets the C library's mode alone, and leaves flush to
  zero as it is.

A scope inside one of the same mode only reads. So a scope goes **around a region of many
operations**, a loop for example, not around each operation: a scope that changes the mode writes
the register on entry and again on exit, and every scope nested in it of the same mode only reads
it. The functions on arrays each hold a scope of their own, which sets the register only, not the
C library's mode; a program that calls them on short arrays in a loop holds one `Scope` around the
loop, so that theirs only read.

What a scope costs, measured on the shipped header
([Benchmarks](../developer/results/bench-upward.md#5-the-scopes)), entry and exit together: a
`Scope` that writes the mode took 21 to 23 ns on an Apple M3, and about 50 ns on an x86-64 machine
(a Zen 2 with glibc), where it also sets the C library's mode (122 ns in one program, where the code
of the call lay elsewhere); the scope of a function on arrays, which writes the register only, took
about 19 ns there. A nested scope of the same mode took under 1 ns on the M3; on the Zen 2 12 to 14
ns, and about 5 ns for the one that writes the register only.
So a scope goes around a region of many operations, not around each one.

### A NearestScope inside a Scope

A `NearestScope` inside a `Scope` is how a program calls the default types, or other code that
assumes rounding to nearest, in an upward region; a `Scope` inside a `NearestScope` works the same
way. Values cross the boundaries as [above](#code-next-to-a-scopes-boundary):

```cpp
--8<-- "docs/examples/cpp/concepts_upward.cpp:nearest"
```

```text
--8<-- "docs/examples/cpp/concepts_upward.txt:6:7"
```

## The functions on arrays

`kairn::upward::add`, `sub`, `mul` and `neg`, and `add` and `mul` with one number `t` for every
element, compute $z = x + y$, $x - y$, $x y$, $-x$, $x + t$ and $x t$ element by element, on views
of two plain arrays: `View<T>(upper, nlower, n)` holds the upper bounds and the negated lower
bounds of $n$ intervals, element $i$ the state $(u_i, n_i)$, and owns nothing; the view written is a
`View<T>`, the views read are `View<const T>`, to which a `View<T>` converts. Each element is the
set the operator of `Interval<T>` gives on it (the bits of the NaNs of an empty set may differ).

```cpp
--8<-- "docs/examples/cpp/concepts_upward.cpp:arrays"
```

```text
--8<-- "docs/examples/cpp/concepts_upward.txt:9:12"
```

- **Each holds its own scope** for the call (upward, the register only), so a program may call it
  where the mode is to nearest; it loads after the scope is set and stores before it ends. Inside a
  `kairn::upward::Scope` that scope costs one read. Called where the mode is to nearest, the
  scope was about 10% of a call or less from 256 elements of `double` on the Zen 2, and under 10% on
  the M3 from about 256 elements for a product and about 1024 for a sum
  ([Benchmarks](../developer/results/bench-upward.md#4-the-scope-of-a-function-on-arrays-by-length));
  below that, hold one `Scope` around the loop of calls.
- **The views have the same length**; for each view read, the view written has the same two
  arrays (in place, as `add(zs, zs, 1.0)` above) or arrays that overlap neither of them, and the two
  arrays it writes do not overlap each other. Every element read is a canonical state. A checked
  build checks all three; a view of another length is reported, and where the report returns the
  shortest length is used.
- **They are called by their qualified names**, `kairn::upward::add(z, x, y)`: they have internal
  linkage, in an unnamed namespace, which argument-dependent lookup does not search.
- Each runs the array form of its kernel: AVX2 where the file is compiled for it, NEON on AArch64,
  and elsewhere, or where the two-number form is forced, the kernel of one interval element by
  element ([The printers](../developer/design/upward.md#the-printers)).

An array of pairs, $(u, n)$ interleaved, has no function of its own: a loop of the interval type over
it, with `from_limbs` and `to_limbs` inside one `Scope`, is the same code
([Arrays](../developer/design/upward.md#arrays)).

## Differences from the default interval

1. **The sign of a zero bound** is unspecified, by the owner's decision of 2026-11-25. It can differ
   from the default type's, and between x86-64 and arm64, whose maximum instructions order $-0$ and
   $+0$ differently; the values are the same.
2. **Products are exactly rounded**: each bound is the rounding of the bound of the exact range. The
   default product of one limb may be one number of `T` wider when a product of bounds is nonzero
   and below $2^{2p-1}\eta$; this one is not. Every special case is answered as the default type
   answers it: the empty set, unbounded intervals, overflow, and $0 \cdot \infty = 0$.
3. **Operations with a number of `T`**: $x + t$, $t + x$, $x - t$, $t - x$, $x \cdot t$ and
   $t \cdot x$, and their compound forms `x += t`, `x -= t`, `x *= t`, with the values of the
   default $x \circ$ `Interval(t)`; an infinite $t$ or a NaN is the whole line. $x - t$ and $t - x$
   are compositions of proved kernels through an exact negation
   ([What is not machine-checked](correctness.md#what-is-not-machine-checked)).
4. **Nothing is `constexpr`**: constant evaluation rounds to nearest, so an operation that rounds
   would give another, wrong bound at compile time. A constant interval is made with the default
   type and converted.
5. **No midpoint, radius, `mid_rad`, `split`, `Ball` or bounds of two limbs** ([What it is
   for](#what-it-is-for)); no comparison operators, as for the default type (the three-valued
   `less`, `less_equal`, `greater`, `greater_equal`, `equal` and `not_equal`, and the relations of
   `kairn::upward::ieee1788`, as the default type has them), and no division.
6. **The operations that round run only inside an upward scope.** The exact ones (the negation, the
   hull, the intersection, the predicates, the comparisons, the conversions, the constructors) give
   the same result in every rounding mode.
7. **Storage and accessors.** `from_limbs` and `to_limbs` read and write $(u, n)$, where the default
   type's `from_limbs` reads the limbs of the bounds, the lower first; `lower()` and `upper()`
   return the default type's convention, $+\infty$ and $-\infty$ for the empty set.
8. **No implicit conversion** between the two interval types, in either direction, and no operation
   that mixes them.

The statements of its kernels, in the IEEE model only, and the status of each are on their reference
pages ([The round-up interval: its kernels](../reference/upward.md)). As for the default types, an
operation compiles without the marker `kairn::unverified` only when its kernel is proved
([Unverified](correctness.md#unverified)); with the marker on an operand it compiles in every
state: `kairn::unverified(x) + y`, `x.hull(kairn::unverified(y))`, and, for the members without an
operand, on the marked interval itself, `kairn::unverified(x).is_empty()`; a function on arrays on a
marked first input, `kairn::upward::add(z, kairn::unverified(x), y)`. In this version every kernel
of the round-up interval is proved, so no operation needs the marker.

## Checks

In a build with `KAIRN_CHECKS` (1 by default without `NDEBUG`), the header asserts what it needs and
reports through `KAIRN_ENVIRONMENT_FAILURE`, as the default types report the environment
([When the environment is wrong](environment.md#when-the-environment-is-wrong)): by default the
reason is printed and the program stopped, and a program may define the macro to a statement of its
own. By the owner's decision of 2026-11-24 the checks that are not strictly needed are assertions,
made in a checked build only:

- before each operation that rounds: the mode is upward, and flush to zero and denormals-are-zero
  are off (one read of the register; on a target with neither register, the C library's mode);
- before each exact operation: flush to zero and denormals-are-zero are off, under which a
  comparison reads a subnormal number as zero;
- after either, the interval operands are canonical, and so are what `from_limbs` is given and the
  default interval that the conversion is given; when the check of the environment reported and
  `KAIRN_ENVIRONMENT_FAILURE` returned, the operands are not checked;
- in a function on arrays, inside its scope: the lengths of the views, the arrays that overlap, and
  that every element read is canonical;
- on entry of an upward scope that writes the mode: that the file's build honors it, by computing
  $1 + 2^{-60} > 1$ on literal operands in a function of its own, which a build that computes it at
  compile time, to nearest, makes false.

Unlike the default types, whose operands that are not canonical stop the program, every report of
this header goes through `KAIRN_ENVIRONMENT_FAILURE`, that of an operand included. A release build
makes none of these checks. What a scope does, and the special cases of the kernels, are the same
in both. The default `kairn::self_test()` fails inside an upward scope, as it should: it checks the
environment of the default types.

## The self-check

```cpp
--8<-- "docs/examples/cpp/concepts_upward.cpp:self_test"
```

```text
--8<-- "docs/examples/cpp/concepts_upward.txt:1:1"
```

`kairn::upward::self_test()` returns a `kairn::Status`, as `kairn::self_test()` does: `ok()` and
`message()`, `failure` the first probe that failed and `kernel` its case (a kernel and limb type with
its operands, or the scope that failed), and `limitation`, with `limited()`, its advice. It holds its
own scopes, a `NearestScope` around it all, and restores the caller's state, so it may be called
inside a `Scope`. It has internal linkage, so it tests the file that calls it, with that file's
options; a program calls it from each file built with other options. It fails, in this order:

1. when the mode does not read back as upward with flush to zero off inside a `Scope` or the scope
   of the functions on arrays, when the C library's mode does not follow a `Scope`, when the
   hardware does not round upward inside them ($1 + 2^{-60}$ through the header's sum), and when a
   scope does not restore the caller's mode and flush to zero;
2. when results below the normal range are flushed to zero, subnormal operands read as zero, or a
   tiny positive product not rounded up to the smallest subnormal number, inside a scope;
3. when a kernel, for `double` and `float`, gives another result than the generator's exact
   interpreter on fixed operands read through `volatile` objects, and again written as literals,
   which a build that computes them while it compiles, to nearest, shows;
4. when a negation was moved through a product (the product's negated lower bound);
5. when a special case differs from the default `Interval<T, 1>`: unbounded operands, overflow,
   $0 \cdot \infty$, $[0, 0]$ times the whole line, the empty set, a number that is not finite;
6. when an operation was merged with one before its scope, moved above the scope's change of mode,
   or **moved below its end**, its result being used only after the scope, each in several shapes;
7. when a function on arrays differs from the operators of `Interval<T>` on a short array.

It gives advice in `limitation`, without failing, when the file's own arithmetic ignores the mode
(a sum of literals, $(-a)\,b$, or $a + b$ against $-((-a) - b)$, of the file's own code, computed
as if to nearest), when a product
of the file's own code was contracted with a sum into one fused multiply-add, and when a
computation of a default type right after an upward scope, on operands in registers, came out as if
computed inside it. The first two do not make the header's results wrong; the third is about the
default types, which are the program's to place
([The self-check](../developer/design/upward.md#the-self-check)). Which advice a build gets depends
on the compiler and its options: a build that contracts the file's own `a * b + c` gets the
second.

**Its limits.** It tests its own copies of the operations, compiled in the file that calls it, not
every place where the program uses them; a compiler can move code in a program where it did not in
the self-check's own shapes; and on MSVC it probes the gap below in its own shapes only. It is
evidence, not proof: with the barriers it is a second line of defence, not the first.

## MSVC

MSVC is supported, with a barrier per scope, by the owner's decision of 2026-11-25, and **its
assurance is weaker than on GCC and Clang**. MSVC has no inline assembly on x64, so the barrier that
orders the operations on GCC and Clang does not exist there. Instead each scope, after writing the
register (or reading it, when nothing changes), reads a zero from a `volatile` object into a
per-thread variable of the header, and every kernel that rounds ORs that zero into its first input,
on which every one of its rounded operations depends; the scopes write MXCSR through a function that
is never inlined. An operation therefore depends on a read made after the mode was set: it cannot be
computed at compile time, merged with one before the scope, or moved above the scope.

**The gap.** Nothing forces MSVC to compute an operation before the scope ends rather than after the
scope's restoring write, under the mode the scope restores. It was not observed in the investigation
that preceded the decision, and the self-check and the tests look for exactly that movement; but on
MSVC no barrier of the header prevents it, where on GCC and Clang the barrier on each result does.

Also on MSVC: `/fp:strict` is required and `/fp:contract` refused, both by the guard
([below](#the-compile-time-guard)). The per-thread zero is one object in all the files of a module:
the test `api.upward.units` checks it with a scope in one file and the operation in another, linked
as they are and, where CMake supports it, with whole-program optimization. Each module of Windows, a
program or a DLL, has its own copy of it, which the scopes of another module never write. Of two
modules one arrangement is tested, by `api.upward.dll`: a scope of the program around calls of a
function that a DLL exports and that runs the header's operations (a product of
`kairn::upward::Interval<double>`, a sum, a product by a number and a function on arrays). The
probes of `api.upward.units` passed there at `/Od`, `/O2` and `/O2 /GL`. They pass because the call
into the DLL is opaque to the compiler, not through the barrier per scope: the DLL's operations
read the DLL's own copy of the zero, which no scope of the program refreshes. So **keep a scope and
the operations it holds in one module**: that is the arrangement the barrier per scope protects
(a function of a DLL that holds its own scope is such a case, and is tested too). The arrangement
across two modules is tested as described, and not promised beyond that test.

## Contraction

`-ffp-contract=off` is not required. No listing has a product that feeds a sum (the products feed
maxima), the inputs of every kernel pass through barriers on GCC and Clang, so that nothing of the
program can be fused into a kernel, and `/fp:strict` excludes contraction on MSVC. The program's own
arithmetic inside a scope may be contracted, which is the program's business; the self-check reports
it as advice ([Contraction](../developer/design/upward.md#contraction)).

## The compile-time guard

Unless the program defines `KAIRN_UPWARD_OPTIONS_UNCHECKED` before including it, the header stops the
build where the compiler shows that the options are missing:

| Compiler | The header stops the build when |
|---|---|
| GCC | `__ROUNDING_MATH__` is not defined (no `-frounding-math`) |
| MSVC (not clang-cl) | `_M_FP_STRICT` is not defined, or `_M_FP_CONTRACT` is |
| Clang, Apple clang, clang-cl | never: they define no macro for `-frounding-math` or for contraction |
| any | `config.hpp`'s refusals (fast-math, finite-math-only, reassociation, ...), which the macro does not override |

The message names the option and the target `kairn::upward`:
`kairn/upward.hpp needs -frounding-math with GCC (the CMake target kairn::upward adds it)`,
`kairn/upward.hpp needs /fp:strict with MSVC`, and
`kairn/upward.hpp does not work with /fp:contract: compile with /fp:strict`, each followed by what
the option does and how to take the options on oneself. `KAIRN_UPWARD_OPTIONS_UNCHECKED` says that
the program takes the options on itself, for a compiler the header does not know or an option set by
a pragma it cannot see; it turns off the rows of GCC and MSVC and nothing else. Where the header
cannot see a missing option (Clang always, the others with the macro), an upward scope that writes
the mode reports, in a checked build, a file whose build ignores the mode, and the self-check
reports it as advice. Without the options the header's own operations are still right on GCC and
Clang, through their barriers, and they were right in the tests with MSVC under `/fp:precise` too,
through the barrier per scope; `/fp:strict` stays required with MSVC, and the program's own
arithmetic inside a scope is right on no compiler without the options.

## The CMake target

`kairn::upward` links `kairn::kairn` and adds the option to the files of the targets that link it:
`-frounding-math` for GCC and Clang, `/clang:-frounding-math` for clang-cl, `/fp:strict` for MSVC.
It adds nothing else: on x86-64 the headers that `kairn/upward.hpp` includes, those of the default
interval, compile only for a processor with fused multiply-add, which a target gets from
`kairn::fma` or its own flags ([Hardware FMA](../getting-started/index.md#hardware-fma)).
`kairn::kairn` itself never gains the option. Kairn added with `add_subdirectory`, and
`find_package(kairn)` in a project that has enabled C++, both define the target; the consumer
checks build a program with it so:

```cmake
--8<-- "tests/consume/add_subdirectory/CMakeLists.txt:6:7"
```
