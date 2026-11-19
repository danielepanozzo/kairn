# Kairn C++ API

These pages list the classes, functions and macros of Kairn's public headers,
`include/kairn/*.hpp`, with the comments written in them; Doxygen generates them. Include
`kairn/kairn.hpp` for all of it. Everything is in namespace `kairn`, and the operations without
the fix-up of infinities and NaN are in `kairn::finite`. The namespaces `kairn::detail` and
`kairn::gen`, and the generated kernels of `include/kairn/gen/`, are not part of the interface and
are not listed.

The comment of each operation names the kernel it calls. What that kernel requires, what is
proved about it and with which theorem, and what the brute-force runs measured, are on the
kernel's page of the [reference](../reference/). The rest of the documentation is on the
[site](../) these pages are part of.
