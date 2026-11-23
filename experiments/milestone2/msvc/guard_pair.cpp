// MSVC 19.52 x64 at /O2 removes the addition of zero by which two adjacent values are guarded where
// it moves the two as one register: -0 + 0, which is +0 to nearest, comes back -0. The guard is
// written as Kairn's generated kernels write it (make_2_limbs) and as a plain x + 0.
// cl /std:c++20 /O2 guard_pair.cpp (with or without /arch:AVX2, /fp:precise or /fp:contract):
// "-0 -0" on the lines "into T limb[2]" and "through a pointer" (double and float) and on the two
// first lines of float (wrong); /fp:strict, /Od, Apple clang 21 and GCC 16 at -O2: "+0" everywhere.
// No Kairn header is included. See README.md beside this file.
#include <cmath>
#include <cstdio>
#include <initializer_list>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define FORCEINLINE __forceinline
#else
#define NOINLINE __attribute__((noinline))
#define FORCEINLINE inline __attribute__((always_inline))
#endif

template <class T> struct Pair { T h, l; };
template <class T> struct Limbs { T limb[2]; };

// The guard of two limbs as the generated kernel make_2_limbs writes it, and as a plain sum.
template <class T> FORCEINLINE constexpr void guarded(T h, T l, T& x0, T& x1) noexcept {
    x0 = __builtin_is_constant_evaluated() ? h : h + T(0);
    x1 = __builtin_is_constant_evaluated() ? l : l + T(0);
}
template <class T> FORCEINLINE void plain(T h, T l, T& x0, T& x1) noexcept {
    x0 = h + T(0);
    x1 = l + T(0);
}

// The two limbs read from adjacent memory, or given in registers, written into a struct of two
// members, a struct holding an array (as Kairn's Expansion<T, 2> does) or through a pointer; and
// one value alone.
template <class T> NOINLINE Pair<T> pair_guarded(const T* l) { Pair<T> p; guarded(l[0], l[1], p.h, p.l); return p; }
template <class T> NOINLINE Pair<T> pair_plain(const T* l) { Pair<T> p; plain(l[0], l[1], p.h, p.l); return p; }
template <class T> NOINLINE Pair<T> regs_guarded(T h, T l) { Pair<T> p; guarded(h, l, p.h, p.l); return p; }
template <class T> NOINLINE Limbs<T> array_guarded(const T* l) { Limbs<T> p; guarded(l[0], l[1], p.limb[0], p.limb[1]); return p; }
template <class T> NOINLINE void out_guarded(const T* l, T* out) { guarded(l[0], l[1], out[0], out[1]); }
template <class T> NOINLINE T one_guarded(const T* l) { return __builtin_is_constant_evaluated() ? l[0] : l[0] + T(0); }

template <class T> const char* s(T x) { return x != 0 ? "x" : std::signbit(x) ? "-0" : "+0"; }

template <class T> int run(const char* type) {
    volatile T v_zero = 0;
    const T m = -T(v_zero);
    const T limbs[2] = {m, m};
    const Pair<T> a = pair_guarded(limbs), b = pair_plain(limbs), c = regs_guarded(m, m);
    const Limbs<T> e = array_guarded(limbs);
    T f[2];
    out_guarded(limbs, f);
    const T d = one_guarded(limbs);
    std::printf("%-6s pair, from memory, the generated guard:  %s %s\n", type, s(a.h), s(a.l));
    std::printf("%-6s pair, from memory, x + 0:                %s %s\n", type, s(b.h), s(b.l));
    std::printf("%-6s pair, in registers, the generated guard: %s %s\n", type, s(c.h), s(c.l));
    std::printf("%-6s pair, from memory, into T limb[2]:       %s %s\n", type, s(e.limb[0]), s(e.limb[1]));
    std::printf("%-6s pair, from memory, through a pointer:    %s %s\n", type, s(f[0]), s(f[1]));
    std::printf("%-6s one value alone, the generated guard:    %s\n", type, s(d));
    int wrong = std::signbit(e.limb[0]) + std::signbit(e.limb[1]) + std::signbit(f[0]) + std::signbit(f[1]) + std::signbit(d);
    for (const Pair<T>& p : {a, b, c}) wrong += std::signbit(p.h) + std::signbit(p.l);
    return wrong;
}

int main() {
    int wrong = run<double>("double");
    wrong += run<float>("float");
    std::printf("%d limbs -0 kept (every one must be +0)\n", wrong);
    return wrong ? 1 : 0;
}
