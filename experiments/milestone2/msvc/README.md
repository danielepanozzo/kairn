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
