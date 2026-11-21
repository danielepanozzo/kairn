// The forms of the ball vectors (kairn/ball_vector.hpp) in the runner of the public interface,
// included by runner.cpp inside its anonymous namespace, after the helpers it uses (fail, parse,
// put_limb, reached, stopped_by_checks, two).
//
// A loop has requests of its own, with arrays (docs/developer/architecture.md, "The line
// protocol"): a ball vector BV FORMAT ORDER N SCALAR... LIMB..., completed with the centers written
// (each limb array's N entries), the radius and the flag; a product of two, BV_CONV FORMAT seq N_X N_Y
// RX RY LIMB..., completed with its N_X + N_Y - 1 coefficients, the radius and the flag; a fold of
// maxima, FOLD FORMAT ORDER N LIMB..., with its bound and flag. Each form builds its operands as a
// program does, through the public constructors: the line's arrays copied into arrays of the form's
// own and made a ball vector by BallVectorView's constructor (loop bv_make_k, which guards what it is
// given), or a BallVector made by its constructor from an std::array of numbers, from_limbs for two
// limbs. The flag is is_finite() of the result.
//
// The order. A line names one (seq, or lanes:W for any W); the public interface has two, the fast
// order of the build (the lane order of Packed's register, or the sequential order where Packed has
// one lane) and kairn::sequential. The statements of a loop are proved for the sequential order and
// for the lane order of every W, and the oracle judges each line by those statements, which do not
// depend on W: so each form computes every line in the order of the function it calls, whatever the
// line names, and the forms of both orders are judged on every line.
//
// In place. The forms named *_in_place_x (and _y) write the result into the arrays of the first
// (second) operand, as a program writes x = x + y through views; the forms of the operators +=, -=
// and *= into the BallVector they modify. The oracle's requests carry no inplace= field here.
//
// The value forms (a BallVector<T, k, N> of a length fixed at compile time) compute their own
// operation on the lines whose lengths are among those instantiated below, and on the others the
// form of views; as every conditional form, each fails at the end of a stream of at least 1000
// lines in which it computed none.
//
// Two operations are compositions of loops made in the header, not loops: axpy (the scaling, then the
// sum in place) and norm_upper (norm_upper_k on the centers, then add_up with the radius). Each is
// judged where its result must satisfy the claims of a loop: axpy(1, X, Y) those of X + Y, axpy(-1,
// Y, X) those of X - Y, axpy(a, X, 0) with Y the point 0 those of X a; norm_upper of a ball vector of
// radius 0, which is add_up(n, 0) = n, those of norm_upper_k on its centers (its bound, the canonical
// NaN with the flag 0 where it is +inf). That axpy for every a computes, bit for bit, the two calls it
// is made of is tested by tests/api/ball_vector.cpp.

namespace bv_forms {

template <class T>
using V1 = kairn::BallVectorView<T, 1>;
template <class T>
using V2 = kairn::BallVectorView<T, 2>;

// A request, parsed: the lengths, the scalars, the limb arrays read in order; and the results.
template <class T>
struct Line {
    std::size_t n = 0, nx = 0, ny = 0;
    std::vector<T> sc;
    std::vector<std::vector<T>> in;
    std::vector<std::vector<T>> out;
    T radius = T(0);
    bool flag = false;
};

// The arrays of one operand as a program holds them: K arrays of its own, a copy of the line's limb
// arrays from index `first`, and a radius. view() makes them a ball vector, in place, and sees them;
// the object stays where it is while the view is used.
template <class T, int K>
struct Held {
    std::vector<T> limb[K];
    T r = T(0);
    Held(const Line<T>& l, std::size_t first, T radius) : r(radius) {
        for (int j = 0; j < K; ++j) limb[j] = l.in[first + std::size_t(j)];
    }
    // n zero entries of radius 0: where a form writes its result.
    explicit Held(std::size_t n) {
        for (int j = 0; j < K; ++j) limb[j].assign(n, T(0));
    }
    Held(const Held&) = delete;
    Held& operator=(const Held&) = delete;
    kairn::SoAView<T, K> soa() {
        if constexpr (K == 1) {
            return kairn::SoAView<T, 1>(limb[0].data(), limb[0].size());
        } else {
            return kairn::SoAView<T, 2>(limb[0].data(), limb[1].data(), limb[0].size());
        }
    }
    kairn::BallVectorView<T, K> view() { return kairn::BallVectorView<T, K>(soa(), r); }
};

// The result of a form, into the line: the limbs of the centers written, the radius, the flag.
template <class X, class T>
void put(Line<T>& l, const X& z) {
    constexpr int K = X::limbs;
    l.out.assign(std::size_t(K), {});
    for (int j = 0; j < K; ++j) l.out[std::size_t(j)].assign(z.limb(j), z.limb(j) + z.size());
    l.radius = z.radius();
    l.flag = z.is_finite();
}

// The numbers of the line's limb arrays from index `first`, n of them.
template <class T, int K>
kairn::Expansion<T, K> number(const Line<T>& l, std::size_t first, std::size_t i) {
    if constexpr (K == 1) {
        return kairn::Expansion<T, 1>(l.in[first][i]);
    } else {
        const T limbs[2] = {l.in[first][i], l.in[first + 1][i]};
        return two(limbs);
    }
}
// A BallVector of the line's operand from index `first`, through the constructor from an std::array.
template <class T, int K, std::size_t N>
kairn::BallVector<T, K, N> value(const Line<T>& l, std::size_t first, T radius) {
    std::array<kairn::Expansion<T, K>, N> c;
    for (std::size_t i = 0; i < N; ++i) c[i] = number<T, K>(l, first, i);
    return kairn::BallVector<T, K, N>(c, radius);
}

// f(N) for the lengths that the value forms instantiate: those of the oracle's schedule of lengths up
// to 17 (oracle/kairn_oracle/genfold.py, LENGTH_SCHEDULE); false for the others. For the products,
// the pairs of 1 to 3.
template <class F>
bool with_length(std::size_t n, F f) {
    switch (n) {
        case 1: f(std::integral_constant<std::size_t, 1>()); return true;
        case 2: f(std::integral_constant<std::size_t, 2>()); return true;
        case 3: f(std::integral_constant<std::size_t, 3>()); return true;
        case 4: f(std::integral_constant<std::size_t, 4>()); return true;
        case 5: f(std::integral_constant<std::size_t, 5>()); return true;
        case 7: f(std::integral_constant<std::size_t, 7>()); return true;
        case 8: f(std::integral_constant<std::size_t, 8>()); return true;
        case 9: f(std::integral_constant<std::size_t, 9>()); return true;
        case 16: f(std::integral_constant<std::size_t, 16>()); return true;
        case 17: f(std::integral_constant<std::size_t, 17>()); return true;
        default: return false;
    }
}
template <class F>
bool with_lengths(std::size_t nx, std::size_t ny, F f) {
    if (nx == 0 || ny == 0 || nx > 3 || ny > 3) return false;
    return with_length(nx, [&](auto a) { with_length(ny, [&](auto b) { f(a, b); }); });
}

// The length of a value form, from the constant with_length passes.
#define NV(n) decltype(n)::value
// One form, a function template instantiated for double and float in the table below.
#define BV_FORM(NAME, ...)                       \
    template <class T>                          \
    void NAME([[maybe_unused]] Line<T>& l) {    \
        __VA_ARGS__;                            \
    }

// --- The constructor: bv_make_k (the centers c, the radius r, supplied) ---------------------------
// A negative radius stops a program with checks (KAIRN_CHECKS); there, as for Ball's constructor
// (runner.cpp), the forms compute what the constructor makes of it, the whole space, without it.
template <class T, int K>
bool whole_if_stopped(Line<T>& l, T r) {
    if (!stopped_by_checks(r)) return false;
    Held<T, K> z(l.n);
    put(l, z.view());  // zeros and radius 0, then the radius +inf of the whole space
    l.radius = std::numeric_limits<T>::infinity();
    l.flag = false;
    return true;
}
#define BV_MAKE_FORMS(K)                                                                                    \
    BV_FORM(bv_make_##K##_view, if (whole_if_stopped<T, K>(l, l.sc[0])) return; Held<T, K> c(l, 0, l.sc[0]); \
            put(l, c.view()))                                                                            \
    BV_FORM(bv_make_##K##_value, if (whole_if_stopped<T, K>(l, l.sc[0])) return;                         \
            if (!with_length(l.n, [&](auto n) { put(l, value<T, K, NV(n)>(l, 0, l.sc[0])); })) {             \
                Held<T, K> c(l, 0, l.sc[0]);                                                             \
                put(l, c.view());                                                                        \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_make_##K##_value_from_view, if (whole_if_stopped<T, K>(l, l.sc[0])) return;               \
            Held<T, K> c(l, 0, T(0));                                                                    \
            if (!with_length(l.n, [&](auto n) {                                                          \
                    put(l, kairn::BallVector<T, K, NV(n)>(kairn::SoAView<const T, K>(c.soa()), l.sc[0]));     \
                })) {                                                                                    \
                Held<T, K> d(l, 0, l.sc[0]);                                                             \
                put(l, d.view());                                                                        \
                return;                                                                                  \
            } ++reached)
BV_MAKE_FORMS(1)
BV_MAKE_FORMS(2)

// --- The negation: bv_neg_k (x, rx) -----------------------------------------------------------------
#define BV_NEG_FORMS(K)                                                                                     \
    BV_FORM(bv_neg_##K##_neg, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n); auto zv = z.view();        \
            kairn::neg(x.view(), zv); put(l, zv))                                                        \
    BV_FORM(bv_neg_##K##_neg_sequential, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n);                \
            auto zv = z.view(); kairn::neg(kairn::sequential, x.view(), zv); put(l, zv))                 \
    BV_FORM(bv_neg_##K##_neg_in_place_x, Held<T, K> x(l, 0, l.sc[0]); auto xv = x.view(); kairn::neg(xv, xv); \
            put(l, xv))                                                                                  \
    BV_FORM(bv_neg_##K##_negate, if (!with_length(l.n, [&](auto n) { put(l, -value<T, K, NV(n)>(l, 0, l.sc[0])); })) { \
                bv_neg_##K##_neg(l);                                                                     \
                return;                                                                                  \
            } ++reached)
BV_NEG_FORMS(1)
BV_NEG_FORMS(2)

// --- The sum and the difference: bv_add_k, bv_sub_k (x, y, rx, ry) ---------------------------------
// The operands' arrays: x from 0, y from K. The scalars: rx, ry. OP and OP_ASSIGN are the operator
// and its compound form, named by OP_NAME and OP_ASSIGN_NAME; PLUS says which loop it is.
#define BV_SUM_FORMS(K, LOOP, FN, OP_NAME, OP, OP_ASSIGN_NAME, OP_ASSIGN, A, PLUS)                          \
    BV_FORM(LOOP##_##FN, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l, K, l.sc[1]); Held<T, K> z(l.n);   \
            auto zv = z.view(); kairn::FN(x.view(), y.view(), zv); put(l, zv))                           \
    BV_FORM(LOOP##_##FN##_sequential, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l, K, l.sc[1]);         \
            Held<T, K> z(l.n); auto zv = z.view(); kairn::FN(kairn::sequential, x.view(), y.view(), zv); \
            put(l, zv))                                                                                  \
    BV_FORM(LOOP##_##FN##_in_place_x, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l, K, l.sc[1]);         \
            auto xv = x.view(); kairn::FN(xv, y.view(), xv); put(l, xv))                                 \
    BV_FORM(LOOP##_##FN##_in_place_y, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l, K, l.sc[1]);         \
            auto yv = y.view(); kairn::FN(x.view(), yv, yv); put(l, yv))                                 \
    BV_FORM(LOOP##_##FN##_mixed, Held<T, K> y(l, K, l.sc[1]);                                           \
            if (!with_length(l.n, [&](auto n) {                                                          \
                    auto x = value<T, K, NV(n)>(l, 0, l.sc[0]);                                          \
                    kairn::FN(x, y.view(), x);                                                           \
                    put(l, x);                                                                           \
                })) {                                                                                    \
                LOOP##_##FN(l);                                                                          \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(LOOP##_##OP_NAME, if (!with_length(l.n, [&](auto n) {                                        \
                    put(l, value<T, K, NV(n)>(l, 0, l.sc[0]) OP value<T, K, NV(n)>(l, K, l.sc[1]));      \
                })) {                                                                                    \
                LOOP##_##FN(l);                                                                          \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(LOOP##_##OP_ASSIGN_NAME, if (!with_length(l.n, [&](auto n) {                                 \
                    auto x = value<T, K, NV(n)>(l, 0, l.sc[0]);                                          \
                    x OP_ASSIGN value<T, K, NV(n)>(l, K, l.sc[1]);                                       \
                    put(l, x);                                                                           \
                })) {                                                                                    \
                LOOP##_##FN(l);                                                                          \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(LOOP##_##A, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l, K, l.sc[1]); Held<T, K> z(l.n);    \
            auto zv = z.view();                                                                          \
            if constexpr (PLUS) {                                                                        \
                kairn::axpy(T(1), x.view(), y.view(), zv);                                               \
            } else {                                                                                     \
                kairn::axpy(T(-1), y.view(), x.view(), zv);                                              \
            } put(l, zv))
BV_SUM_FORMS(1, bv_add_1, add, plus, +, plus_assign, +=, axpy_unit, true)
BV_SUM_FORMS(2, bv_add_2, add, plus, +, plus_assign, +=, axpy_unit, true)
BV_SUM_FORMS(1, bv_sub_1, sub, minus, -, minus_assign, -=, axpy_minus_one, false)
BV_SUM_FORMS(2, bv_sub_2, sub, minus, -, minus_assign, -=, axpy_minus_one, false)

// --- The scaling by a T: bv_scale_k (x, rx, a) ----------------------------------------------------
#define BV_SCALE_FORMS(K)                                                                                   \
    BV_FORM(bv_scale_##K##_scale, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n); auto zv = z.view();    \
            kairn::scale(x.view(), l.sc[1], zv); put(l, zv))                                             \
    BV_FORM(bv_scale_##K##_scale_sequential, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n);            \
            auto zv = z.view(); kairn::scale(kairn::sequential, x.view(), l.sc[1], zv); put(l, zv))      \
    BV_FORM(bv_scale_##K##_scale_in_place_x, Held<T, K> x(l, 0, l.sc[0]); auto xv = x.view();            \
            kairn::scale(xv, l.sc[1], xv); put(l, xv))                                                   \
    BV_FORM(bv_scale_##K##_times, if (!with_length(l.n, [&](auto n) { put(l, value<T, K, NV(n)>(l, 0, l.sc[0]) * l.sc[1]); })) { \
                bv_scale_##K##_scale(l);                                                                 \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_scale_##K##_times_rev, if (!with_length(l.n, [&](auto n) { put(l, l.sc[1] * value<T, K, NV(n)>(l, 0, l.sc[0])); })) { \
                bv_scale_##K##_scale(l);                                                                 \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_scale_##K##_times_assign, if (!with_length(l.n, [&](auto n) {                             \
                    auto x = value<T, K, NV(n)>(l, 0, l.sc[0]);                                              \
                    x *= l.sc[1];                                                                        \
                    put(l, x);                                                                           \
                })) {                                                                                    \
                bv_scale_##K##_scale(l);                                                                 \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_scale_##K##_axpy_zero_y, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l.n); Held<T, K> z(l.n); \
            auto zv = z.view(); kairn::axpy(l.sc[1], x.view(), y.view(), zv); put(l, zv))                \
    BV_FORM(bv_scale_##K##_axpy_in_place_x, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> y(l.n);              \
            auto xv = x.view(); kairn::axpy(kairn::sequential, l.sc[1], xv, y.view(), xv); put(l, xv))
BV_SCALE_FORMS(1)
BV_SCALE_FORMS(2)

// --- The scaling by a power of two: bv_mul_pow2_k (x, rx, c) -------------------------------------
// c is a positive power of two of T, 2^m with m = ilogb(c), so that ldexp(X, m) calls the loop once on
// the line's own operands. half(Y) with Y = X 2^(m + 1) exactly, where the line has such a Y (every
// limb and the radius scaled exactly), computes c X as well; and ldexp(Y, m - k) with Y = X 2^k
// exactly and m - k beyond the powers of two of T computes it in steps. On their other lines those two
// forms compute ldexp(X, m).
template <class T>
bool exact_scale_all(const Line<T>& l, int limbs, int k, Line<T>& y) {
    y = l;
    for (int j = 0; j < limbs; ++j) {
        for (std::size_t i = 0; i < l.n; ++i) {
            const T a = l.in[std::size_t(j)][i], b = std::ldexp(a, k);
            if (!std::isfinite(b) || std::ldexp(b, -k) != a) return false;
            y.in[std::size_t(j)][i] = b;
        }
    }
    if (limbs == 2)
        for (std::size_t i = 0; i < l.n; ++i)
            if (y.in[0][i] + y.in[1][i] != y.in[0][i]) return false;
    const T r = std::ldexp(l.sc[0], k);
    if (!std::isfinite(r) || std::ldexp(r, -k) != l.sc[0]) return false;
    y.sc[0] = r;
    return true;
}
#define BV_POW2_FORMS(K)                                                                                    \
    BV_FORM(bv_mul_pow2_##K##_ldexp, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n); auto zv = z.view(); \
            kairn::ldexp(x.view(), std::ilogb(l.sc[1]), zv); put(l, zv))                                 \
    BV_FORM(bv_mul_pow2_##K##_ldexp_sequential, Held<T, K> x(l, 0, l.sc[0]); Held<T, K> z(l.n);          \
            auto zv = z.view(); kairn::ldexp(kairn::sequential, x.view(), std::ilogb(l.sc[1]), zv); put(l, zv)) \
    BV_FORM(bv_mul_pow2_##K##_ldexp_in_place_x, Held<T, K> x(l, 0, l.sc[0]); auto xv = x.view();         \
            kairn::ldexp(xv, std::ilogb(l.sc[1]), xv); put(l, xv))                                       \
    BV_FORM(bv_mul_pow2_##K##_ldexp_value,                                                               \
            if (!with_length(l.n, [&](auto n) { put(l, kairn::ldexp(value<T, K, NV(n)>(l, 0, l.sc[0]), std::ilogb(l.sc[1]))); })) { \
                bv_mul_pow2_##K##_ldexp(l);                                                              \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_mul_pow2_##K##_half, const int m = std::ilogb(l.sc[1]); Line<T> y;                        \
            if (!std::isfinite(l.sc[0]) || !exact_scale_all(l, K, m + 1, y)) {                           \
                bv_mul_pow2_##K##_ldexp(l);                                                              \
                return;                                                                                  \
            } ++reached; Held<T, K> x(y, 0, y.sc[0]); Held<T, K> z(l.n); auto zv = z.view();             \
            kairn::half(x.view(), zv); put(l, zv))                                                       \
    BV_FORM(bv_mul_pow2_##K##_half_value, const int m = std::ilogb(l.sc[1]); Line<T> y;                  \
            if (!std::isfinite(l.sc[0]) || !exact_scale_all(l, K, m + 1, y) ||                           \
                !with_length(l.n, [&](auto n) { put(l, kairn::half(value<T, K, NV(n)>(y, 0, y.sc[0]))); })) { \
                bv_mul_pow2_##K##_ldexp(l);                                                              \
                return;                                                                                  \
            } ++reached)                                                                                 \
    BV_FORM(bv_mul_pow2_##K##_ldexp_far, const int m = std::ilogb(l.sc[1]); Line<T> y;                   \
            constexpr int lo = std::numeric_limits<T>::min_exponent - std::numeric_limits<T>::digits;    \
            constexpr int hi = std::numeric_limits<T>::max_exponent - 1;                                  \
            int n = 0; bool found = false;                                                               \
            if (std::isfinite(l.sc[0])) {                                                                \
                for (int k : {m - hi - 1, m - lo + 1, m - hi - 1 - 2 * std::numeric_limits<T>::digits, m - lo + 1 + hi}) { \
                    if (exact_scale_all(l, K, k, y)) {                                                   \
                        n = m - k;                                                                       \
                        found = true;                                                                    \
                        break;                                                                           \
                    }                                                                                    \
                }                                                                                        \
            }                                                                                            \
            if (!found) {                                                                                \
                bv_mul_pow2_##K##_ldexp(l);                                                              \
                return;                                                                                  \
            } ++reached; Held<T, K> x(y, 0, y.sc[0]); Held<T, K> z(l.n); auto zv = z.view();             \
            kairn::ldexp(x.view(), n, zv); put(l, zv))
BV_POW2_FORMS(1)
BV_POW2_FORMS(2)

// --- The product of polynomials: bv_conv_k (x of n_x, y of n_y, rx, ry) ----------------------------
template <class T, int K>
struct Product {
    Held<T, K> x, y, z;
    Product(const Line<T>& l)
        : x(l, 0, l.sc[0]), y(l, K, l.sc[1]), z(l.nx == 0 || l.ny == 0 ? 0 : l.nx + l.ny - 1) {}
};
#define BV_CONV_FORMS(K)                                                                                    \
    BV_FORM(bv_conv_##K##_convolution, Product<T, K> p(l); auto zv = p.z.view();                          \
            kairn::convolution(p.x.view(), p.y.view(), zv); put(l, zv))                                  \
    BV_FORM(bv_conv_##K##_convolution_sequential, Product<T, K> p(l); auto zv = p.z.view();               \
            kairn::convolution(kairn::sequential, p.x.view(), p.y.view(), zv); put(l, zv))               \
    BV_FORM(bv_conv_##K##_convolution_value,                                                             \
            if (!with_lengths(l.nx, l.ny, [&](auto a, auto b) {                                          \
                    put(l, kairn::convolution(value<T, K, NV(a)>(l, 0, l.sc[0]), value<T, K, NV(b)>(l, K, l.sc[1]))); \
                })) {                                                                                    \
                bv_conv_##K##_convolution(l);                                                            \
                return;                                                                                  \
            } ++reached)
BV_CONV_FORMS(1)
BV_CONV_FORMS(2)

// --- The bound of the members, norm_upper: a composition, judged on norm_upper_k ------------------
// A line of norm_upper_k: its centers as a ball vector of radius 0, whose norm_upper is add_up(n, 0) =
// n where the bound of the centers n is given, and +inf otherwise, which the line's protocol writes
// as the canonical NaN with the flag 0. Centers that are not finite make the whole space, of bound
// +inf: norm_upper_k's flag is 0 there too.
template <class T>
void put_bound(Line<T>& l, T b) {
    l.flag = std::numeric_limits<T>::infinity() > b;
    l.radius = l.flag ? b : std::numeric_limits<T>::quiet_NaN();
}
#define BV_NORM_FORMS(K)                                                                                    \
    BV_FORM(norm_upper_##K##_ball_vector_norm_upper, Held<T, K> x(l, 0, T(0));                           \
            put_bound(l, kairn::norm_upper(x.view())))                                                    \
    BV_FORM(norm_upper_##K##_ball_vector_norm_upper_sequential, Held<T, K> x(l, 0, T(0));                \
            put_bound(l, kairn::norm_upper(kairn::sequential, x.view())))
BV_NORM_FORMS(1)
BV_NORM_FORMS(2)

#undef BV_FORM
#undef NV
#undef BV_MAKE_FORMS
#undef BV_NEG_FORMS
#undef BV_SUM_FORMS
#undef BV_SCALE_FORMS
#undef BV_POW2_FORMS
#undef BV_CONV_FORMS
#undef BV_NORM_FORMS

// The kinds of request.
enum class Kind { ball_vector, product, maxima };
struct FoldForm {
    const char* loop;
    const char* name;
    Kind kind;
    int limbs;         // of each array read and of the array written
    int arrays;        // arrays read
    int scalars;       // limbs of the scalars, after the lengths
    bool conditional;  // computes its own operation on some lines only
    bool fast;         // in the fast order: listed by the runner of the packed forms alone
    void (*binary64)(Line<double>&);
    void (*binary32)(Line<float>&);
};
#define FROW(LOOP, NAME, KIND, K, A, S, COND, FAST) \
    {#LOOP, #NAME, Kind::KIND, K, A, S, COND, FAST, LOOP##_##NAME<double>, LOOP##_##NAME<float>},
#define SUM_ROWS(LOOP, K, FN, OP, OP_ASSIGN, A)                        \
    FROW(LOOP, FN, ball_vector, K, 2, 2, false, true)                  \
    FROW(LOOP, FN##_sequential, ball_vector, K, 2, 2, false, false)    \
    FROW(LOOP, FN##_in_place_x, ball_vector, K, 2, 2, false, true)     \
    FROW(LOOP, FN##_in_place_y, ball_vector, K, 2, 2, false, true)     \
    FROW(LOOP, FN##_mixed, ball_vector, K, 2, 2, true, true)           \
    FROW(LOOP, OP, ball_vector, K, 2, 2, true, true)                   \
    FROW(LOOP, OP_ASSIGN, ball_vector, K, 2, 2, true, true)            \
    FROW(LOOP, A, ball_vector, K, 2, 2, false, true)
#define K_ROWS(K)                                                                    \
    FROW(bv_make_##K, view, ball_vector, K, 1, 1, false, false)                      \
    FROW(bv_make_##K, value, ball_vector, K, 1, 1, true, false)                      \
    FROW(bv_make_##K, value_from_view, ball_vector, K, 1, 1, true, false)            \
    FROW(bv_neg_##K, neg, ball_vector, K, 1, 1, false, true)                         \
    FROW(bv_neg_##K, neg_sequential, ball_vector, K, 1, 1, false, false)             \
    FROW(bv_neg_##K, neg_in_place_x, ball_vector, K, 1, 1, false, true)              \
    FROW(bv_neg_##K, negate, ball_vector, K, 1, 1, true, true)                       \
    SUM_ROWS(bv_add_##K, K, add, plus, plus_assign, axpy_unit)                       \
    SUM_ROWS(bv_sub_##K, K, sub, minus, minus_assign, axpy_minus_one)                \
    FROW(bv_scale_##K, scale, ball_vector, K, 1, 2, false, true)                     \
    FROW(bv_scale_##K, scale_sequential, ball_vector, K, 1, 2, false, false)         \
    FROW(bv_scale_##K, scale_in_place_x, ball_vector, K, 1, 2, false, true)          \
    FROW(bv_scale_##K, times, ball_vector, K, 1, 2, true, true)                      \
    FROW(bv_scale_##K, times_rev, ball_vector, K, 1, 2, true, true)                  \
    FROW(bv_scale_##K, times_assign, ball_vector, K, 1, 2, true, true)               \
    FROW(bv_scale_##K, axpy_zero_y, ball_vector, K, 1, 2, false, true)               \
    FROW(bv_scale_##K, axpy_in_place_x, ball_vector, K, 1, 2, false, false)          \
    FROW(bv_mul_pow2_##K, ldexp, ball_vector, K, 1, 2, false, true)                  \
    FROW(bv_mul_pow2_##K, ldexp_sequential, ball_vector, K, 1, 2, false, false)      \
    FROW(bv_mul_pow2_##K, ldexp_in_place_x, ball_vector, K, 1, 2, false, true)       \
    FROW(bv_mul_pow2_##K, ldexp_value, ball_vector, K, 1, 2, true, true)             \
    FROW(bv_mul_pow2_##K, half, ball_vector, K, 1, 2, true, true)                    \
    FROW(bv_mul_pow2_##K, half_value, ball_vector, K, 1, 2, true, true)              \
    FROW(bv_mul_pow2_##K, ldexp_far, ball_vector, K, 1, 2, true, true)               \
    FROW(bv_conv_##K, convolution, product, K, 2, 2, false, false)                   \
    FROW(bv_conv_##K, convolution_sequential, product, K, 2, 2, false, false)        \
    FROW(bv_conv_##K, convolution_value, product, K, 2, 2, true, false)              \
    FROW(norm_upper_##K, ball_vector_norm_upper, maxima, K, 1, 0, false, true)       \
    FROW(norm_upper_##K, ball_vector_norm_upper_sequential, maxima, K, 1, 0, false, false)
// The first form of each loop is its canonical one (the debug build's runner runs that one only).
const FoldForm fold_forms[] = {K_ROWS(1) K_ROWS(2)};
#undef K_ROWS
#undef SUM_ROWS
#undef FROW

// The kernels that are parts of the loops above and that no public operation calls on its own,
// each with the loop that calls it (its step, record, combination, radius, finish, bound, or a part
// of the convolution its centers are): judged through the forms of their loops, and on their own by
// the cross-checks of the kernels (crosscheck.compiled.*). coverage.cmake checks each against the
// loop's description in gen/kernels.
struct LoopPart {
    const char* kernel;
    const char* loop;
};
const LoopPart loop_parts[] = {
    {"bv_center_entry_1", "bv_make_1"}, {"bv_center_2", "bv_make_2"}, {"bv_make_radius", "bv_make_1"},
    {"bv_make_finish", "bv_make_1"}, {"neg_1", "bv_neg_1"}, {"bv_neg_radius", "bv_neg_1"},
    {"sub_1_1", "bv_sub_1"}, {"bv_add_radius_1", "bv_add_1"}, {"bv_add_radius_2", "bv_add_2"},
    {"scale_step_1", "bv_scale_1"}, {"scale_step_2", "bv_scale_2"}, {"bv_scale_radius_1", "bv_scale_1"},
    {"bv_scale_radius_2", "bv_scale_2"}, {"bv_mul_pow2_step_1", "bv_mul_pow2_1"},
    {"bv_mul_pow2_step_2", "bv_mul_pow2_2"}, {"bv_mul_pow2_radius", "bv_mul_pow2_1"},
    {"norm_step_1", "bv_add_1"}, {"norm_step_2", "bv_add_2"}, {"norm_combine", "bv_add_1"},
    {"norm_finish_1", "bv_add_1"}, {"norm_finish_2", "norm_upper_2"}, {"conv_radius", "bv_conv_1"},
    {"bv_conv_finish", "bv_conv_1"}, {"bound_dot_1", "bv_conv_1"}, {"bound_dot_2", "bv_conv_2"},
    {"dot_step_1", "bv_conv_1"}, {"dot_step_2", "bv_conv_2"}, {"fold_finish_1", "bv_conv_1"},
    {"fold_finish_2", "bv_conv_2"},
};

// A limb of the line in T: a binary64 literal, which for binary32 must be a binary32 number.
template <class T>
T limb_of(const std::string& text) {
    const double v = parse(text);
    if constexpr (sizeof(T) == 4) {
        const double top = std::numeric_limits<float>::max();
        if (v == v && v - v == 0 && (v > top || v < -top)) fail(text + " is not a binary32 number");
        const float x = static_cast<float>(v);
        if (static_cast<double>(x) != v && v == v) fail(text + " is not a binary32 number");
        return x;
    } else {
        return v;
    }
}
inline std::size_t length_of(const std::string& text) {
    if (text.empty() || text.find_first_not_of("0123456789") != std::string::npos || (text[0] == '0' && text.size() > 1))
        fail("not a length: " + text);
    return std::stoull(text);
}

// Completes a line of a loop: parses it, runs the form, appends " -> RESULTS" to out.
template <class T>
void complete(const FoldForm& f, const std::vector<std::string>& fields, std::string& out,
              void (*run)(Line<T>&)) {
    Line<T> l;
    std::size_t at = 0;
    const std::string& order = fields[2];
    if (f.kind == Kind::product) {
        if (fields.size() < 5) fail(std::string(f.loop) + " FORMAT seq N_X N_Y RX RY LIMB...");
        if (order != "seq") fail(std::string(f.loop) + " has the sequential order only (seq)");
        l.nx = length_of(fields[3]);
        l.ny = length_of(fields[4]);
        at = 5;
    } else {
        if (fields.size() < 4) fail(std::string(f.loop) + " FORMAT ORDER N ...");
        if (order != "seq" && (order.compare(0, 6, "lanes:") != 0 || order.size() == 6 ||
                               order.find_first_not_of("0123456789", 6) != std::string::npos))
            fail("not an order: " + order + " (seq, or lanes:W)");
        l.n = length_of(fields[3]);
        at = 4;
        if (fields.size() > at && fields[at].compare(0, 8, "inplace=") == 0)
            fail("the forms of the public interface choose in place themselves: no inplace= field");
    }
    const std::size_t scalars = std::size_t(f.scalars), limbs = std::size_t(f.limbs);
    const std::size_t entries =
        f.kind == Kind::product ? limbs * (l.nx + l.ny) : limbs * std::size_t(f.arrays) * l.n;
    if (fields.size() - at != scalars + entries)
        fail(std::string(f.loop) + " takes " + std::to_string(scalars + entries) + " limbs here");
    for (std::size_t i = 0; i < scalars; ++i) l.sc.push_back(limb_of<T>(fields[at + i]));
    at += scalars;
    for (int a = 0; a < f.arrays; ++a) {
        const std::size_t len = f.kind != Kind::product ? l.n : a == 0 ? l.nx : l.ny;
        for (std::size_t j = 0; j < limbs; ++j) {
            std::vector<T> v(len);
            for (std::size_t i = 0; i < len; ++i) v[i] = limb_of<T>(fields[at + i]);
            at += len;
            l.in.push_back(v);
        }
    }
    l.sc.push_back(T(0));  // so that a form of no scalar may still name sc[0] in a branch it skips
    run(l);
    out += " ->";
    if (f.kind != Kind::maxima)
        for (const std::vector<T>& a : l.out)
            for (T v : a) {
                out += ' ';
                put_limb(static_cast<double>(v), out);
            }
    out += ' ';
    put_limb(static_cast<double>(l.radius), out);
    out += l.flag ? " 1" : " 0";
}

}  // namespace bv_forms
