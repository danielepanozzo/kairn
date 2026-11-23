# A miscompilation by MSVC, reduced

`select_inline.cpp` is 55 lines and includes no Kairn header. With MSVC 19.52 for x64 at `/O2` it
prints `0 0 102`; the right output, which it prints at `/O1`, at `/Od`, with `/DNOINLINE`, and
with Apple clang at `-O2`, is `100 101 102`.

The function `fix` takes eleven parameters by value, nine of them a small struct, selects three
of them, and returns them in a struct that holds an array. When MSVC inlines it into `kernel`,
which is called through a pointer to a function, two of the three values returned are lost. With
`double` in place of the struct the output is right; with three named members in place of the
array it is still wrong; with a selection between two triples only it is right.

It was found on 2026-11-22 by the tests of the generated kernels on emulated formats
(`tests/emulated/`): `fix` is the fix-up of the kernel `ball_intersection_2` as the generator
prints it for a limb type that is a class, in the form that calls the fix-up as a function. The
kernels that the library ships have the same functions for `double` and `float`, and are not
exposed: with MSVC their fix-ups are marked `__declspec(noinline)`
(`include/kairn/gen/prelude.hpp`, `KAIRN_GEN_COLD`), and the form that calls them is not the
default there. The emulated kernels now mark them the same way.

# The guard of two adjacent values

Measured on 2026-11-23 with MSVC 19.52 for x64, Apple clang 21 and GCC 16.

`guard_pair.cpp` includes no Kairn header. It guards two values `-0` as Kairn's generated kernels
guard a limb (`-0 + 0`, which is `+0` to nearest) and prints the sign of each. With MSVC at `/O2`,
under `/fp:precise` (the default) or `/fp:contract`, with or without `/arch:AVX2`, the pair read
from adjacent memory comes back `-0 -0` when it is written into a struct that holds an array (as
`Expansion<T, 2>` does) or through a pointer, for `double` and `float`, and into a struct of two
members for `float`: the listing moves the two as one register (`vmovupd` from the source to the
destination) with no addition left. One value alone, and a struct of two `double` members, keep
the addition (`vaddsd`, `vaddpd` with a zero register). The right output, `+0` on every line, is
what MSVC prints with `/fp:strict` and at `/Od`, and what Apple clang and GCC print at `-O2`.

`guard_pair_constructors.cpp` gives every constructor of Kairn that guards its operands a `-0` in
each, read from one struct by reference, in a function that is not inlined. With MSVC at
`/O2 /arch:AVX2`, under `/fp:precise` or `/fp:contract`, a `-0` comes back from `Ball<T, 2>(c, r)`,
`Ball<T, 2>(Constant)`, `from_limbs` of `Expansion<T, 2>`, `Ball<T, 2>` and `Interval<T, 2>`, and
`Accumulator<T, 2>::from_state` for `double`, and from `from_limbs` of `Ball<T, 2>` and
`Interval<T, 2>` for `float`; the constructors of one limb, those from values of `T`, those of an
interval of two limbs from its bounds, and those of the ball vectors give `+0` there, and every one
gives `+0` under `/fp:strict` and at `/Od`. Which values MSVC moves as one register depends on the
code around the constructor: given in registers, or computed in the function, the same operands
gave other constructors and other limbs (`Ball<T, 2>(c, r)` gave `+0` when its center was built in
a helper function), so the list is what was seen, not a bound. Values are not affected: `-0` and
`+0` are equal, and no statement of a kernel is about the sign of a zero.

`guard_pair_r3.cpp` asks whether a removed addition lets MSVC fuse a product of the program into
the kernel, the thing the guard is for (rule R3). Each of its 16 forms writes `a * b` where the
addition was seen to go (limb 1 and the radius of the two ball constructors, the limbs of the three
`from_limbs` and of `from_state`, limb 0 for comparison, the two-limb ball vector, and three in
which the struct is written by the caller and read by a function that is not inlined), adds an
operand that cancels it, and compares with the same form on the product rounded first, limb by
limb, on 200 000 cases per form and type. With MSVC at `/O2 /arch:AVX2` no form differs under
`/fp:precise`, `/fp:contract` or `/fp:strict`, nor at `/Od`, while the control in the same program
(`s = a * b; s + x`, without Kairn) differs in every case under `/fp:contract`, the setting under
which MSVC contracts across statements. Built against a copy of the headers without the guard
(`python3 unguard.py include DIR`, the transformation of `tests/api/CMakeLists.txt`), the six forms
of `from_limbs` differ in every case under `/fp:contract`, for both types. In the listings MSVC
multiplies the program's product on its own (`vmulsd`) and emits no fused instruction for it: the
addition of zero goes, but after the guard has kept the product out of the kernel. Without
`/arch:AVX2` Kairn does not compile with MSVC (`prelude.hpp`: hardware FMA is required).
