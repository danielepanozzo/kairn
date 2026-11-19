// What the translation units of the benchmark share: the signatures of the timed functions and
// the tables that list them (bench/README.md).
//
// Every timed function is a non-inlined function with C linkage, so that its machine code can be
// found by name in a disassembly (bench/asm_summary.py), and is called through a pointer, so that
// no compiler sees what it computes at the call site.
#pragma once

#include <cstddef>
#include <cstdint>

#if defined(_MSC_VER) && !defined(__clang__)
#define KB_NOINLINE __declspec(noinline)
#define KB_COLD
#define KB_RESTRICT __restrict
#else
#define KB_NOINLINE __attribute__((noinline))
#define KB_COLD __attribute__((cold))
#define KB_RESTRICT __restrict__
#endif

namespace kairn_bench {

// Throughput: z[i] = op(x[i], y[i]) for i < n, independent operations on arrays that fit in L1.
// A 2-limb operand is (x0, x1), a ball is (x0, x1, xr) or, with one limb, (x0, xr). A function
// uses the arrays it needs and leaves the others alone.
using TpFn = void (*)(int n, const double* x0, const double* x1, const double* xr,
                      const double* y0, const double* y1, const double* yr,
                      double* z0, double* z1, double* zr);

// Latency: one dependent chain per lane, over the n values of the operand stream. Lane j of a
// packed function with W lanes takes the elements j, j + W, j + 2W, ... and runs n / W steps.
//   sum:    s <- s + x[i]
//   prod:   p <- p * f[i]           (the factors are near 1, so p stays in range)
//   horner: p <- p * h + c[i]       (h fixed)
// The chain starts at s, and lane j writes its last value to out0[j], out1[j], outr[j].
struct ChainArgs {
    int n;
    const double *x0, *x1, *xr;   // summands
    const double *f0, *f1, *fr;   // factors
    const double *c0, *c1, *cr;   // Horner coefficients
    double h0, h1, hr;            // Horner argument
    double s0, s1, sr;            // start of the chain
    double *out0, *out1, *outr;
};
using ChainFn = void (*)(const ChainArgs* a);

// The public types (api.cpp): arrays of kairn::Expansion<T, 2>, kairn::Ball<T, 2> and
// kairn::Ball<T, 1>, as a client stores them, in a structure that api.cpp alone knows. A function
// runs one throughput loop or one chain over the structure of its limb type, and writes its
// results into the output part of the structure.
using ApiFn = void (*)(void* data);

// One timed function. name is "BACKEND/KIND/KERNEL/VARIANT": BACKEND scalar, packed, api (the
// public types, double limbs), apif (float limbs) or mpfr; KIND tp, sum, prod or horner; VARIANT
// kairn for the generated core, full for the generated full kernel, op for the public operator,
// finite for kairn::finite::, or the name of a measurement prop (props.hpp). Each variant is
// checked against scalar/KIND/KERNEL/kairn (api: api/KIND/KERNEL/kairn, apif: likewise) before it
// is timed.
struct Entry {
    const char* name;
    int lanes;        // 1 for scalar code; the register width for packed code
    TpFn tp;          // exactly one of tp, chain and api is set
    ChainFn chain;
    ApiFn api;
    int bits;         // api: the width of the limb type, 64 or 32; 0 otherwise
};

// The tables of the scalar, packed, public-type and MPFR translation units, each ended by an entry
// with a null name. The packed table is empty when the target has no packed backend, the MPFR one
// when MPFR was not found.
extern const Entry scalar_entries[];
extern const Entry packed_entries[];
extern const char* const packed_backend;   // "avx2", "neon" or "none"
extern const Entry api_entries[];

// The structures of api.cpp: api_setup makes the operands from a fixed seed (the same with every
// compiler), api_data returns the structure for limbs of `bits` bits, api_clear fills its outputs
// with a NaN pattern, and api_output returns the bytes of its outputs and their number.
void api_setup(std::uint64_t seed);
void* api_data(int bits);
void api_clear(int bits);
const unsigned char* api_output(int bits, std::size_t* size);

// MPFR keeps its numbers in its own arrays: mpfr_setup converts the operands of the chain and of
// the throughput arrays once; the entries then time 106-bit mpfr_add and mpfr_mul on them, and
// mpfr_result reads back result i of the last throughput call, or of the chain (i = -1), as a
// 2-limb number rounded to nearest.
extern const Entry mpfr_entries[];
extern const char* const mpfr_version_text;     // "" when MPFR was not found
void mpfr_setup(int n, const double* x0, const double* x1, const double* y0, const double* y1,
                const ChainArgs* chain);
void mpfr_result(int i, double* r0, double* r1);

}  // namespace kairn_bench
