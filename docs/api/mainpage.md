# Kairn C++ API

These pages list the classes, functions and macros of Kairn's public headers,
`include/kairn/*.hpp`, with the comments written in them; Doxygen generates them. Include
`kairn/kairn.hpp` for the numbers, the balls, the intervals and the rest it includes; the headers it
does not include (`kairn/packed.hpp`, `kairn/soa.hpp`, `kairn/batch.hpp`, `kairn/ball_vector.hpp`
and `kairn/upward.hpp`) are included on their own. Everything is in namespace `kairn`, the
operations without the fix-up of infinities and NaN are in `kairn::finite`, and the opt-in round-up
interval of `kairn/upward.hpp` is in `kairn::upward`. That header requires the rounding mode upward
set by `kairn::upward::Scope` and the options of its concept page (GCC and Clang
`-frounding-math`, MSVC `/fp:strict`); its scopes, `pass()`, its functions on arrays and its
`self_test()` have internal linkage, and are listed under
`kairn::upward::anonymous_namespace{upward.hpp}`, where a program names them `kairn::upward::Scope`
and so on. The namespaces `kairn::detail`, `kairn::gen` and `kairn::upward::detail`, and the
generated kernels of `include/kairn/gen/`, are not part of the interface and are not listed.

The comment of each operation names the kernel it calls. What that kernel requires, what is
proved about it and with which theorem, and what the brute-force runs measured, are on the
kernel's page of the [reference](../reference/). The rest of the documentation is on the
[site](../) these pages are part of.
