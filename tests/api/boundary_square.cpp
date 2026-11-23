// The exception of a square (docs/getting-started/guarantees.md, "The exception: a square"), pinned:
// what the page says of a square passed straight into an operation, of the ways it gives to round
// one first, and of the products that are not squares. Each form is an operation of the public
// interface computed twice, with the value written in the call and with it rounded first (returned
// through a volatile by a function that is not inlined), on operands chosen so that the operation
// cancels (and on operands of either sign), and the results are compared bit for bit.
//
// - The squares (a * a, pow(a, 2), (a - b) * (a - b)) through two_sum, a two-limb number plus a T,
//   the sum of Packed<T, 1> (broadcast and loaded), the two accumulators, and sum, add and axpy
//   over an array the program filled: --square none, they must not differ (GCC; Clang under
//   -ffp-contract=off, on and its default; MSVC where it does not contract), so that a compiler
//   that starts removing the guard fails here; --square report, they are printed without a verdict
//   (Clang under -ffp-contract=fast, where the page says they lose the guard).
// - The recipe of the page, through the same operations: kairn::two_prod(a, a).product and a
//   volatile give the rounded square, and Expansion<T, 2>(a) * a the exact one (through a two-limb
//   number plus it, Accumulator<T, 2> and the sum of two limbs). They must not differ, with every
//   compiler under every setting: a difference means the page is wrong.
// - The products that are not squares, of the list of experiments/milestone2/square/ (a product of
//   two absolute values, of factors known positive, of conversions from integers, of square roots,
//   of two squares, of a square and a value of unknown sign, of two exponentials): they must not
//   differ anywhere.
//
//   boundary_square --square none|report
#include <kairn/accumulator.hpp>
#include <kairn/batch.hpp>
#include <kairn/kairn.hpp>
#include <kairn/packed.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>

#if defined(_MSC_VER) && !defined(__clang__)
#define NOINLINE __declspec(noinline)
#define INLINE inline  // not __forceinline: /W4 warns (C4714) where MSVC declines, and /WX fails
#else
#define NOINLINE __attribute__((noinline))
#define INLINE inline __attribute__((always_inline))
#endif

namespace {

constexpr int N = 4;  // the values of one case (the arrays of sum have 2N elements)

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using P1 = kairn::Packed<T, 1>;

// The inputs of one value: a, b in [1/2, 1), sa, sb the same with random signs, ua, ub unsigned
// integers near 2^40 (an inexact product), ia, ib signed ones.
template <class T>
struct In {
    T a, b, sa, sb;
    std::uint64_t ua, ub;
    std::int64_t ia, ib;
};

template <class T>
struct Out {
    T v[4] = {};
};

// --- The expressions -----------------------------------------------------------------------------
// Each is a value of T computed from In: in place in the form, or rounded first by rounded<E>.
#define EXPR(NAME, ...)                                    \
    struct NAME {                                          \
        template <class T>                                 \
        static INLINE T f(const In<T>& in) {               \
            [[maybe_unused]] const T a = in.a, b = in.b;   \
            __VA_ARGS__                                    \
        }                                                  \
    };
EXPR(square, return a * a;)
EXPR(pow2, return std::pow(a, T(2));)
EXPR(square_of_difference, return (a - b) * (a - b);)
EXPR(two_prod_product, return kairn::two_prod(a, a).product;)
EXPR(volatile_square, volatile T v = a * a; return v;)
EXPR(product, return a * b;)
EXPR(product_of_abs, return std::fabs(in.sa) * std::fabs(in.sb);)
EXPR(product_if_positive, if (a > T(0) && b > T(0)) return a * b; return T(0);)
EXPR(constant_times_abs, return T(0.75) * std::fabs(in.sa);)
EXPR(constant_times_positive, if (a > T(0)) return T(0.75) * a; return T(0);)
EXPR(product_of_unsigned, return T(in.ua) * T(in.ub);)
EXPR(product_of_signed, return T(in.ia) * T(in.ib);)
EXPR(product_of_roots, return std::sqrt(a) * std::sqrt(b);)
EXPR(product_of_squares, return (a * a) * (b * b);)
EXPR(square_times_signed, return (a * a) * in.sb;)
EXPR(product_of_exponentials, return std::exp(a - T(1)) * std::exp(b - T(1));)

template <class E, class T>
NOINLINE T rounded(const In<T>& in) {
    volatile T v = E::template f<T>(in);
    return v;
}
// The rounded square, the reference of the first two ways of the recipe.
template <class T>
NOINLINE T rounded_square(const In<T>& in) {
    volatile T v = in.a * in.a;
    return v;
}

// The value of a form: written in the call (InPlace) or given rounded (Given).
template <class E, class T>
struct InPlace {
    const In<T>* in;
    INLINE T x(int i) const { return E::template f<T>(in[i]); }
};
template <class T>
struct Given {
    const T* v;
    INLINE T x(int i) const { return v[i]; }
};

// --- The operations ------------------------------------------------------------------------------
#define OP(NAME, ...)                                                                           \
    struct NAME {                                                                               \
        template <class T, class M>                                                             \
        static INLINE void run([[maybe_unused]] const M& m, [[maybe_unused]] const T* c, Out<T>& o) { \
            __VA_ARGS__                                                                         \
        }                                                                                       \
    };
#define X(i) m.x(i)
OP(op_two_sum, const auto r = kairn::two_sum(c[0], X(0)); o.v[0] = r.sum; o.v[1] = r.error;)
OP(op_two_limbs_plus_t, const E2<T> z = E2<T>(c[0]) + X(0); o.v[0] = z.limb[0]; o.v[1] = z.limb[1];)
OP(op_packed_broadcast, const P1<T> z = P1<T>::broadcast(E1<T>(c[0])) + P1<T>::broadcast(E1<T>(X(0)));
   o.v[0] = z.lane(0).limb[0];)
OP(op_packed_load, constexpr int W = P1<T>::lanes; T s[W], t[W];
   for (int l = 0; l < W; ++l) { s[l] = X(0); t[l] = c[0]; }
   const P1<T> z = P1<T>::load(t) + P1<T>::load(s); o.v[0] = z.lane(0).limb[0];)
OP(op_accumulator_1, kairn::Accumulator<T, 1> acc; acc.add(X(0)); acc.add(c[0]); const auto bl = acc.ball();
   o.v[0] = bl.center().limb[0]; o.v[2] = bl.radius();)
OP(op_accumulator_2, kairn::Accumulator<T, 2> acc; acc.add(X(0)); acc.add(c[0]); const auto bl = acc.ball();
   o.v[0] = bl.center().limb[0]; o.v[1] = bl.center().limb[1]; o.v[2] = bl.radius();)
OP(op_sum, T s[2 * N]; for (int i = 0; i < N; ++i) { s[2 * i] = X(i); s[2 * i + 1] = c[i]; }
   o.v[0] = kairn::sum(kairn::SoAView<const T, 1>(s, 2 * N)).value.limb[0];)
OP(op_add, T s[N], z[N]; for (int i = 0; i < N; ++i) s[i] = X(i);
   kairn::add(kairn::SoAView<const T, 1>(s, N), kairn::SoAView<const T, 1>(c, N), kairn::SoAView<T, 1>(z, N));
   o.v[0] = z[0]; o.v[1] = z[N - 1];)
OP(op_axpy, T s[N], z[N]; for (int i = 0; i < N; ++i) s[i] = X(i);
   kairn::axpy(T(1), kairn::SoAView<const T, 1>(c, N), kairn::SoAView<const T, 1>(s, N), kairn::SoAView<T, 1>(z, N));
   o.v[0] = z[0]; o.v[1] = z[N - 1];)

template <class Op, class E, class T>
NOINLINE Out<T> in_place(const In<T>* in, const T* c) {
    Out<T> o;
    Op::template run<T>(InPlace<E, T>{in}, c, o);
    return o;
}
template <class Op, class T>
NOINLINE Out<T> given(const T* v, const T* c) {
    Out<T> o;
    Op::template run<T>(Given<T>{v}, c, o);
    return o;
}

// --- The exact square, Expansion<T, 2>(a) * a, through the operations of two limbs ----------------
template <class T>
NOINLINE void exact_square_limbs(const In<T>& in, T* l0, T* l1) {  // rounded: through volatiles
    const E2<T> q = E2<T>(in.a) * in.a;
    volatile T h = q.limb[0], l = q.limb[1];
    *l0 = h;
    *l1 = l;
}
struct op2_two_limbs_plus {
    template <class T>
    static INLINE void run(const E2<T>& q, const T* c, Out<T>& o) {
        const E2<T> z = E2<T>(c[0]) + q;
        o.v[0] = z.limb[0];
        o.v[1] = z.limb[1];
    }
};
struct op2_accumulator {
    template <class T>
    static INLINE void run(const E2<T>& q, const T* c, Out<T>& o) {
        kairn::Accumulator<T, 2> acc;
        acc.add(q);
        acc.add(c[0]);
        const auto bl = acc.ball();
        o.v[0] = bl.center().limb[0];
        o.v[1] = bl.center().limb[1];
        o.v[2] = bl.radius();
    }
};
struct op2_sum {
    template <class T>
    static INLINE void run(const E2<T>& q, const T* c, Out<T>& o) {
        T h[2] = {q.limb[0], c[0]}, l[2] = {q.limb[1], T(0)};
        const auto r = kairn::sum(kairn::SoAView<const T, 2>(h, l, 2)).value;
        o.v[0] = r.limb[0];
        o.v[1] = r.limb[1];
    }
};
template <class Op, class T>
NOINLINE Out<T> exact_in_place(const In<T>* in, const T* c) {
    Out<T> o;
    Op::template run<T>(E2<T>(in[0].a) * in[0].a, c, o);
    return o;
}
template <class Op, class T>
NOINLINE Out<T> exact_given(const T* l0, const T* l1, const T* c) {
    Out<T> o;
    const T limbs[2] = {l0[0], l1[0]};
    Op::template run<T>(E2<T>::from_limbs(limbs), c, o);
    return o;
}

// --- The cases ---------------------------------------------------------------------------------
std::uint64_t state = 0x9E3779B97F4A7C15ull;
std::uint64_t next() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
}
template <class T>
T unit() {  // in [1/2, 1)
    if constexpr (sizeof(T) == 8) {
        return T(0.5 + double(next() >> 11) * 0x1p-54);
    } else {
        return T(0.5f + float(next() >> 40) * 0x1p-25f);
    }
}
template <class T>
In<T> draw() {
    In<T> in;
    in.a = unit<T>();
    in.b = unit<T>();
    in.sa = next() & 1 ? in.a : -in.a;
    in.sb = next() & 1 ? in.b : -in.b;
    in.ua = (std::uint64_t(1) << 40) + (next() >> 25);
    in.ub = (std::uint64_t(1) << 40) + (next() >> 25);
    in.ia = std::int64_t(in.ua) * (next() & 1 ? 1 : -1);
    in.ib = std::int64_t(in.ub);
    return in;
}
// The operand c of a value v: within a few units of -v (the operation cancels) in the first half of
// the cases, of either sign and within a factor 4 of v in the second.
template <class T>
T operand(T v, long i, long cases) {
    constexpr T step = sizeof(T) == 8 ? T(0x1p-30) : T(0x1p-12);
    if (i < cases / 2) return -v * (T(1) + T(i % 7 + 1) * step);
    const T m = v * unit<T>() * T(int(1) << int(next() % 4)) * T(0.5);
    return next() % 2 ? -m : m;
}
template <class T>
bool same(const Out<T>& x, const Out<T>& y) {
    return std::memcmp(x.v, y.v, sizeof x.v) == 0;
}

struct Tally {
    long squares = 0, recipe = 0, controls = 0, rows = 0;
};

enum Kind { kSquare, kRecipe, kControl };
const char* const kind_name[] = {"square", "recipe", "control"};

template <class T>
const char* type_name() {
    constexpr bool is_double = sizeof(T) == 8;
    return is_double ? "double" : "float";
}

// One row: operation Op with expression E. The reference of a square or a control is the same
// expression rounded; that of the first two ways of the recipe is the rounded square.
template <class Op, class E, class T>
void row(Kind kind, const char* op, const char* expr, long cases, bool verdict, Tally& t) {
    long differ = 0;
    for (long i = 0; i < cases; ++i) {
        In<T> in[N];
        T v[N], c[N];
        for (int j = 0; j < N; ++j) {
            in[j] = draw<T>();
            v[j] = kind == kRecipe ? rounded_square(in[j]) : rounded<E>(in[j]);
            c[j] = operand(v[j], i, cases);
        }
        differ += !same(in_place<Op, E, T>(in, c), given<Op, T>(v, c));
    }
    const bool bad = differ > 0 && (kind != kSquare || verdict);
    std::printf("  %-7s %-24s %-22s %-6s differs in %5ld of %ld%s\n", kind_name[kind], expr, op, type_name<T>(), differ,
                cases, bad ? "   FAIL" : (differ && kind == kSquare ? "   (reported only)" : ""));
    ++t.rows;
    if (bad) ++(kind == kSquare ? t.squares : kind == kRecipe ? t.recipe : t.controls);
}

template <class Op, class T>
void exact_row(const char* op, long cases, Tally& t) {
    long differ = 0;
    for (long i = 0; i < cases; ++i) {
        In<T> in[N];
        T l0[N], l1[N], c[N];
        for (int j = 0; j < N; ++j) {
            in[j] = draw<T>();
            exact_square_limbs(in[j], &l0[j], &l1[j]);
            c[j] = operand(l0[j], i, cases);
        }
        differ += !same(exact_in_place<Op, T>(in, c), exact_given<Op, T>(l0, l1, c));
    }
    std::printf("  %-7s %-24s %-22s %-6s differs in %5ld of %ld%s\n", "recipe", "Expansion<T, 2>(a) * a", op,
                type_name<T>(), differ, cases, differ ? "   FAIL" : "");
    ++t.rows;
    if (differ) ++t.recipe;
}

#define ROWS(E, KIND, TEXT)                                                                        \
    row<op_two_sum, E, T>(KIND, "two_sum(c, x)", TEXT, cases, verdict, t);                         \
    row<op_two_limbs_plus_t, E, T>(KIND, "Expansion<T, 2>(c) + x", TEXT, cases, verdict, t);       \
    row<op_packed_broadcast, E, T>(KIND, "Packed<T, 1> + (broadcast)", TEXT, cases, verdict, t);   \
    row<op_packed_load, E, T>(KIND, "Packed<T, 1> + (load)", TEXT, cases, verdict, t);             \
    row<op_accumulator_1, E, T>(KIND, "Accumulator<T, 1>", TEXT, cases, verdict, t);               \
    row<op_accumulator_2, E, T>(KIND, "Accumulator<T, 2>", TEXT, cases, verdict, t);               \
    row<op_sum, E, T>(KIND, "sum of an array", TEXT, cases, verdict, t);                           \
    row<op_add, E, T>(KIND, "add of arrays", TEXT, cases, verdict, t);                             \
    row<op_axpy, E, T>(KIND, "axpy of arrays", TEXT, cases, verdict, t);

template <class T>
void run(long cases, bool verdict, Tally& t) {
    ROWS(square, kSquare, "a * a")
    ROWS(pow2, kSquare, "pow(a, 2)")
    ROWS(square_of_difference, kSquare, "(a - b) * (a - b)")
    ROWS(two_prod_product, kRecipe, "two_prod(a, a).product")
    ROWS(volatile_square, kRecipe, "volatile a * a")
    exact_row<op2_two_limbs_plus, T>("Expansion<T, 2>(c) + q", cases, t);
    exact_row<op2_accumulator, T>("Accumulator<T, 2>", cases, t);
    exact_row<op2_sum, T>("sum of two limbs", cases, t);
    ROWS(product, kControl, "a * b")
    ROWS(product_of_abs, kControl, "fabs(a) * fabs(b)")
    ROWS(product_if_positive, kControl, "a * b if a, b > 0")
    ROWS(constant_times_abs, kControl, "0.75 * fabs(a)")
    ROWS(constant_times_positive, kControl, "0.75 * a if a > 0")
    ROWS(product_of_unsigned, kControl, "T(ua) * T(ub)")
    ROWS(product_of_signed, kControl, "T(ia) * T(ib)")
    ROWS(product_of_roots, kControl, "sqrt(a) * sqrt(b)")
    ROWS(product_of_squares, kControl, "(a * a) * (b * b)")
    ROWS(square_times_signed, kControl, "(a * a) * b")
    ROWS(product_of_exponentials, kControl, "exp(a - 1) * exp(b - 1)")
}

}  // namespace

int main(int argc, char** argv) {
    const char* square = argc == 3 && std::strcmp(argv[1], "--square") == 0 ? argv[2] : "";
    if (std::strcmp(square, "none") != 0 && std::strcmp(square, "report") != 0) {
        std::fprintf(stderr, "usage: boundary_square --square none|report\n");
        return 2;
    }
    const bool verdict = std::strcmp(square, "none") == 0;
    constexpr long cases = 2000;
    std::printf("Packed<double, 1>: %d lanes; the squares %s\n", kairn::Packed<double, 1>::lanes,
                verdict ? "must not differ" : "are reported only");
    Tally t;
    run<double>(cases, verdict, t);
    run<float>(cases, verdict, t);
    std::printf("%ld rows; failures: squares %ld, the recipe %ld, the controls %ld\n", t.rows, t.squares, t.recipe,
                t.controls);
    const bool ok = t.squares == 0 && t.recipe == 0 && t.controls == 0;
    std::printf("%s\n", ok ? "ok" : "FAILED");
    return ok ? 0 : 1;
}
