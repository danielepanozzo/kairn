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
computed under the rounding mode upward. `kairn/kairn.hpp` does not include it. Its interface is the
interval type `kairn::upward::Interval<T>`, functions on two plain arrays, the scopes
`kairn::upward::Scope` and `kairn::upward::NearestScope`, `kairn::upward::pass()` and
`kairn::upward::self_test()` ([The interface](../developer/design/upward.md#the-interface), in the
design page). This page says what it is for, how its intervals are stored, what a program must
guarantee for its results to hold, how it differs from the default interval, and what its checks see
and do not see.

## What it is for

For intervals of one limb in a hot loop, where the default interval's bounds cost more than the
operations they round: the default types compute each bound rounded down or up under rounding to
nearest, in several operations, because they never change the mode
([What they cost](enclosures.md#what-they-cost-and-how-wide-they-are)). Under the mode upward the
hardware rounds both bounds in the direction that widens the interval, and the two are computed
together: a sum is one vector addition, a difference one addition and one exchange of the two lanes,
a negation one exchange, and a product four vector multiplications and three maxima, with
selections for the special cases and no branch ([The kernels](../developer/design/upward.md#the-kernels)).
A typical use is a *filter* that decides a sign: an expression evaluated on intervals whose result
excludes zero has a known sign, and only the cases where it does not fall back to something slower
and exact.

What it does not have: a midpoint, a radius, `mid_rad`, `split`, conversions to or from a `Ball`,
and bounds of two limbs, since each of them needs rounding to nearest. A program converts to the
default interval for those, outside an upward scope.

## How an interval is stored

The interval $[a, b]$ is the pair $(u, n) = (b, -a)$: lane 0, first in memory, the upper bound, and
lane 1 the lower bound negated. Under the mode upward both lanes then round in the direction that
widens the interval, since rounding down is rounding up of the negation,
$\mathrm{RD}(t) = -\mathrm{RU}(-t)$. The empty set is $(\mathrm{NaN}, \mathrm{NaN})$ and the whole
line $(+\infty, +\infty)$; the members are real numbers, as for the default interval, so
$[1, +\infty]$ does not contain $+\infty$. Lane 0 is the upper bound because that is the order in
which the first client stores the two numbers, so that such pairs can be passed in as they are
([The stored pair](../reference/upward.md#the-stored-pair) has the table of states).

The conversions from and to the default `Interval<T, 1>` are exact (a negation and selections) and
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
   one copy for all of them.
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

- `kairn::upward::pass(v)` returns `v`, the same bits, after a barrier, so that a computation on its
  result happens after the most recent boundary of a scope; for a `T`, a default `Interval<T, 1>`
  and the round-up interval;
- `to_interval()`, the conversion to the default interval, puts a barrier on its results, so that a
  default interval converted inside a `NearestScope` is computed on there.

The header promises nothing more about code without barriers that shares a function with a scope;
the self-check probes both directions in its own shapes ([The self-check](#the-self-check)).

## The scopes

`kairn::upward::Scope` sets the rounding mode upward for its lifetime, and
`kairn::upward::NearestScope` sets it to nearest; each restores what it found when it ends. A
`NearestScope` inside a `Scope` is how a program calls the default types, or other code that
assumes rounding to nearest, in an upward region; a `Scope` inside a `NearestScope` works the same
way. Both have internal linkage, so that each file compiles its own, and neither can be copied or
moved.

- **On entry** a scope reads the control register (MXCSR on x86-64, FPCR on AArch64) and writes it
  only when something must change: the mode, and flush to zero and denormals-are-zero, which it
  turns off. It also makes the C library's mode (`std::fegetround()`) the same, so that the
  program's own code sees that mode: on AArch64 the register is the C library's state, and on x86-64,
  where the C library may keep its own, the scope calls `std::fesetround` when it reports another
  mode. Then a barrier.
- **On exit**, a barrier, then the register and the C library's mode restored as the entry found
  them, but for the exception flags raised inside, which are kept.
- On a target with neither register the scope sets the C library's mode alone.

A scope inside one of the same mode only reads. So a scope goes **around a region of many
operations**, a loop for example, not around each operation: a scope that changes the mode writes
the register on entry and again on exit, and every scope nested in it of the same mode only reads
it. The functions on arrays each hold a scope of their own, which sets the register only; a program
that calls them on short arrays in a loop holds one `Scope` around the loop, so that theirs only
read.

## Differences from the default interval

1. **The sign of a zero bound** is unspecified, by the owner's decision of 2026-11-25. It can differ
   from the default type's, and between x86-64 and arm64, whose maximum instructions order $-0$ and
   $+0$ differently; the values are the same.
2. **Products are exactly rounded**: each bound is the rounding of the bound of the exact range. The
   default product of one limb may be one number of `T` wider when a product of bounds is nonzero
   and below $2^{2p-1}\eta$; this one is not. Every special case is answered as the default type
   answers it: the empty set, unbounded intervals, overflow, and $0 \cdot \infty = 0$.
3. **Operations with a number of `T`**: $x + t$, $x - t$, $t - x$, $x \cdot t$ and $t \cdot x$, with
   the values of the default $x \circ$ `Interval(t)`; an infinite $t$ or a NaN is the whole line.
4. **Nothing is `constexpr`**: constant evaluation rounds to nearest, so an operation that rounds
   would give another, wrong bound at compile time. A constant interval is made with the default
   type and converted.
5. **No midpoint, radius, `mid_rad`, `split`, `Ball` or bounds of two limbs** ([What it is
   for](#what-it-is-for)); no comparison operators, as for the default type, and no division.
6. **The operations that round run only inside an upward scope.** The exact ones (the negation, the
   hull, the intersection, the predicates, the comparisons, the conversions) give the same result in
   every rounding mode.
7. **Storage and accessors.** `from_limbs` and `to_limbs` read and write $(u, n)$, where the default
   type's read and write the bounds; `lower()` and `upper()` return the default type's convention,
   $+\infty$ and $-\infty$ for the empty set.
8. **No implicit conversion** between the two interval types, in either direction, and no operation
   that mixes them.

The statements of its kernels, in the IEEE model only, and the status of each are on their reference
pages ([The round-up interval: its kernels](../reference/upward.md)). As for the default types, an
operation compiles without the marker `kairn::unverified` only when its kernel is proved
([Unverified](correctness.md#unverified)).

## Checks

In a build with `KAIRN_CHECKS` (1 by default without `NDEBUG`), the header asserts what it needs and
reports through `KAIRN_ENVIRONMENT_FAILURE`, as the default types do
([When the environment is wrong](environment.md#when-the-environment-is-wrong)). By the owner's
decision of 2026-11-24 the checks that are not strictly needed are assertions, made in a checked
build only:

- before each operation that rounds: the mode is upward, and flush to zero and denormals-are-zero
  are off (one read of the register);
- before each exact operation: flush to zero and denormals-are-zero are off, under which a
  comparison reads a subnormal number as zero;
- the operands are canonical, and so are the elements of arrays and what `from_limbs` is given; the
  functions on arrays also check the lengths and the arrays that alias;
- on entry of an upward scope that writes the mode: that the file's build honors it, by computing
  $1 + 2^{-60} > 1$ on literal operands in a function of its own, which a build that computes it at
  compile time, to nearest, makes false.

A release build makes none of these. What a scope does, and the special cases of the kernels, are
the same in both. The default `kairn::self_test()` fails inside an upward scope, as it should: it
checks the environment of the default types.

## The self-check

`kairn::upward::self_test()` returns a `kairn::Status`, as `kairn::self_test()` does, and holds its
own scopes. It has internal linkage, so it tests the file that calls it, with that file's options; a
program calls it from each file built with other options. It fails when the mode cannot be set
upward, does not read back as upward or is not restored, or the C library's mode does not follow;
when flush to zero acts inside a scope; when a kernel gives another result than the generator's
exact interpreter on fixed operands, read through `volatile` objects and again written as literals,
which a build that folds them shows; when a negation was moved through a product; when a special
case comes out wrong; when an operation was merged across a scope's entry, moved above it, or
**moved below its end**, its result being used only after the scope; and when a function on arrays
fails on a short array. It gives advice in `limitation`, without failing, when the file's own
arithmetic ignores the mode, when the program's products are contracted into its sums, and when a
computation of a default type right after an upward scope came out as if computed inside it
([The self-check](../developer/design/upward.md#the-self-check)).

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
([below](#the-compile-time-guard)). The per-thread zero is one object in all the files of a module,
but each module of Windows, a program or a DLL, has its own: keep the scopes and the operations they
hold in the same module. A scope of the program around operations compiled into a DLL is not
supported.

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

The message names the option and the target `kairn::upward`. `KAIRN_UPWARD_OPTIONS_UNCHECKED` says
that the program takes the options on itself, for a compiler the header does not know or an option
set by a pragma it cannot see; it turns off the rows of GCC and MSVC and nothing else. Where the
header cannot see a missing option (Clang always, the others with the macro), an upward scope that
writes the mode reports, in a checked build, a file whose build ignores the mode, and the self-check
reports it as advice.

## The CMake target

`kairn::upward` links `kairn::kairn` and adds the option to the files of the targets that link it:
`-frounding-math` for GCC and Clang, `/clang:-frounding-math` for clang-cl, `/fp:strict` for MSVC.
It adds nothing else: on x86-64 the kernels need the hardware fused multiply-add as well, which a
target gets from `kairn::fma` or its own flags
([Hardware FMA](../getting-started/index.md#hardware-fma)). `kairn::kairn` itself never gains the
option. Kairn added with `add_subdirectory`, and `find_package(kairn)` in a project that has enabled
C++, both define the target; the consumer checks build a program with it so:

```cmake
--8<-- "tests/consume/add_subdirectory/CMakeLists.txt:6:7"
```
