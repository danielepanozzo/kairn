// The benchmark of Milestone 2 (bench/README.md, "Milestone 2"): what its translation units share.
//
// - m2.cpp times what a client gets: the building blocks of kairn/blocks.hpp, Interval<T, 1> and
//   Interval<T, 2>, Ball<T, 1> and Ball<T, 2> with the additions of Milestone 2, a Horner
//   evaluation, and kairn::rational; the generated kernels on the same numbers (variant kairn), the
//   reference every other variant is checked against; and the plain floors of T.
// - m2_fenv.cpp, compiled so that the compiler honors a change of the rounding mode
//   (bench/CMakeLists.txt), times the classical alternative: the same directed results obtained by
//   switching the rounding mode with std::fesetround, or by writing the control register, around
//   one operation or once around a loop. It does not include Kairn.
// - m2_packed.cpp (and m2_fenv_packed.cpp) time the packed kernels of kairn/gen/avx2.hpp or
//   neon.hpp, and the packed classical alternative, binary64 only.
// - m2_main.cpp is the driver: it makes the inputs, checks every timed function against its
//   reference, times them, measures the tightness of the Horner evaluation, and writes the JSON.
//
// The numbers of one limb type live in one structure, Data<T> (m2.cpp), whose first member is the
// plain part below, Raw<T>: every operand as plain arrays of T, laid out as the public types lay out
// their limbs (an Interval<T, 1> as lo, hi; an Interval<T, 2> as l0, l1, h0, h1; a Ball<T, 1> as
// c, r; a Ball<T, 2> as c0, c1, r), the same numbers again one array per limb for packed code, and
// the plain outputs. Every timed function takes a pointer to that structure.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

#include "bench.hpp"   // KB_NOINLINE, KB_RESTRICT

namespace kairn_bench::m2 {

inline constexpr int kN = 256;   // elements per array; the arrays of one function fit in any L1
inline constexpr int kDeg = 8;   // the degree of the Horner polynomial

template <class T>
struct Raw {
    // Numbers of T: x, y of moderate magnitude (+-[1, 2) 2^k, k in [-8, 8]), u the same positive,
    // f factors near 1, p powers of two 2^n with n in [-8, 8] (and n), s the factors of a chain of
    // scalings that alternate 2 and 1/2 (and +1, -1).
    T xa[kN], ya[kN], ua[kN], fa[kN], pa[kN], sa[kN];
    int na[kN], sn[kN];
    // Intervals of one limb, lo, hi: X, Y, F (factors near 1, positive), W (overlapping X).
    T xi[2 * kN], yi[2 * kN], fi[2 * kN], wi[2 * kN];
    // Intervals of two limbs, l0, l1, h0, h1.
    T xi2[4 * kN], yi2[4 * kN], fi2[4 * kN], wi2[4 * kN];
    // Balls of one limb (c, r) and of two (c0, c1, r): the balls of X, Y, F.
    T xb1[2 * kN], yb1[2 * kN], fb1[2 * kN];
    T xb2[3 * kN], yb2[3 * kN], fb2[3 * kN];
    // Two-limb numbers (x0, x1): the lower bounds of X, Y, F of two limbs.
    T xe2[2 * kN], ye2[2 * kN], fe2[2 * kN];
    // The Horner polynomial, its coefficients from degree 0 up, exact in T, and its arguments: the
    // same kN sets as intervals of one and two limbs, balls of one and two limbs, and their
    // midpoints as numbers of one and two limbs.
    T hc[kDeg + 1];
    T hi1[2 * kN], hi2[4 * kN], hb1[2 * kN], hb2[3 * kN], ht[kN], he2[2 * kN];
    // Fractions for kairn::rational: small terms (|num| <= 1000, 1 <= |den| <= 1000) and large ones
    // (64-bit).
    long long qns[kN], qds[kN], qnl[kN], qdl[kN];
    // The same intervals and balls one array per limb, for packed code: sx (lower, upper), s2x (l0,
    // l1, h0, h1), sb1 (c, r), sb2 (c0, c1, r), for X and Y.
    T sxi[2][kN], syi[2][kN], sxi2[4][kN], syi2[4][kN], sxb1[2][kN], syb1[2][kN], sxb2[3][kN], syb2[3][kN];
    // Plain outputs: of a loop, up to four values of T per element, element after element; of a
    // chain, up to four values; of packed code, one array per output.
    T out[4 * kN];
    T cout[4];
    T sout[4][kN];
};

// Where a timed function writes its result (m2_region, in m2.cpp): the plain outputs above, or an
// array of a public type in Data<T>. A function and its reference write the same number of values of
// T, in the same layout, and are compared byte for byte.
enum Region : int {
    R_OUT,     // Raw::out
    R_COUT,    // Raw::cout
    R_SOUT,    // Raw::sout
    R_I1,      // Interval<T, 1>[kN]
    R_I2,      // Interval<T, 2>[kN]
    R_B1,      // Ball<T, 1>[kN]
    R_B2,      // Ball<T, 2>[kN]
    R_E2,      // Expansion<T, 2>[kN]
    R_SPLIT,   // Split<Interval<T, 1>>[kN]
    R_SE,      // SumAndError<T>[kN]
    R_PE,      // ProductAndError<T>[kN]
    R_CI1,     // one Interval<T, 1>: the end of a chain
    R_CI2,
    R_CB1,
    R_CB2,
    R_CE2,
    R_Q1,      // Constant<Expansion<T, 1>>[kN], checked by kairn::is_rational_result
    R_Q2,      // Constant<Expansion<T, 2>>[kN]
    R_COUNT
};

using Fn = void (*)(void* data);

// One timed function. name is "BACKEND/KIND/KERNEL/VARIANT": BACKEND m2 (double limbs), m2f
// (float limbs), m2s (generated scalar kernels on one array per limb, double) or m2p (packed code,
// double); KIND tp (a loop of independent operations, time per operation), sum, prod (a dependent
// chain, time per step), lat (dependent evaluations, time per evaluation); KERNEL what is computed;
// VARIANT kairn for the generated kernel called on the limbs (the reference), op for the public
// operation, and the name of a prop otherwise (fenv, fenv_loop, csr, plain, ...). Every entry is
// checked before it is timed against BACKEND/KIND/KERNEL/kairn (m2p against m2s), the values of
// `values` values of T in `region`, byte for byte, unless `check` is set, which then decides.
struct Entry {
    const char* name;
    Fn fn;
    int bits;      // 64 or 32: the limb type
    int lanes;     // 1, or the lanes of a packed register
    int ops;       // operations, steps or evaluations per call
    int region;    // Region
    int values;    // values of T written there
    bool (*check)(const Entry& e, char* why, std::size_t why_size);   // nullptr: against the reference
};

// The tables, each ended by an entry with a null name.
extern const Entry m2_entries[];          // m2.cpp
extern const Entry m2_fenv_entries[];     // m2_fenv.cpp
extern const Entry m2_packed_entries[];   // m2_packed.cpp (empty without a packed backend)
extern const Entry m2_fenv_packed_entries[];   // m2_fenv_packed.cpp (likewise)
extern const char* const m2_packed_backend;    // "avx2", "neon" or "none"

// The data (m2.cpp).
void m2_setup(std::uint64_t seed);
void* m2_data(int bits);
void m2_clear(int bits);
const unsigned char* m2_region(int bits, int region, std::size_t* bytes);

// The rounding-mode props on a wide sample (m2_fenv.cpp), and the same results from Kairn (m2.cpp):
// op 0 to 5 is add_down, add_up, sub_down, sub_up, mul_down, mul_up; variant 0 switches with
// std::fesetround around each operation, 1 writes the control register. kairn_rn gives the result
// rounded to nearest, so that the driver can count how many results a prop that ignored the mode
// would have got wrong.
void m2_wide_fenv(int bits, int op, int variant, int n, const void* a, const void* b, void* out);
void m2_wide_kairn(int bits, int op, int n, const void* a, const void* b, void* out, void* rn);

// The tightness of the Horner evaluation (m2.cpp): the widths of the enclosures of p(X) for X in
// three regimes, as a JSON array.
std::string m2_tightness_json();

// The macro that hides a value from the optimizer: after it the compiler knows nothing of v, and
// must have computed it before. In m2_fenv.cpp it is what keeps an operation between the two changes
// of the rounding mode around it.
#if defined(__GNUC__) && (defined(__x86_64__) || defined(__i386__))
#define KB_OPAQUE(v) __asm__ volatile("" : "+x"(v))
#elif defined(__GNUC__) && defined(__aarch64__)
#define KB_OPAQUE(v) __asm__ volatile("" : "+w"(v))
#else
#define KB_OPAQUE(v) ((void)(v))
#endif

}  // namespace kairn_bench::m2
