// Measurement props for the benchmark of the round-up interval (bench/up_data.hpp): the classical
// interval with the rounding mode set upward once around a whole loop, as the variant fenv_loop of
// m2_fenv.cpp (two plain numbers per interval, the lower bound as RD(t) = -RU(-t), no special case:
// not an implementation of the empty set, of unbounded intervals or of 0 times infinity), for what
// m2_fenv.cpp does not have, double, backend m2:
//
//   tp/det3_i1/fenv_loop         the determinant of coordinate differences (up_data.hpp)
//   tp/interval_{add,sub,mul}_1/fenv_loop_x16
//                                the loops of m2_fenv.cpp 16 times between one change of mode and
//                                its reset, next to the round-up interval's native_x16
//   sum/interval_add_1/fenv_loop_x16, prod/interval_mul_1/fenv_loop_x16
//                                the chains of m2_fenv.cpp 16 times as long (16 kN steps)
//
// Not part of the library, not verified, not to be used outside bench/. Compiled as m2_fenv.cpp
// (-frounding-math, /fp:strict with MSVC; with Clang the pragma STDC FENV_ACCESS ON), and it does
// not include Kairn: the loads come after the call that sets the mode and the stores before the
// call that resets it, which every compiler must respect for memory that a call may read or write;
// between the passes of an _x16 a barrier of the compiler (no load or store crosses it). Each is
// checked against Kairn's default kernels before it is timed (up_check.cpp).
#include <cfenv>

#include "up_data.hpp"

#if defined(__clang__)
#pragma STDC FENV_ACCESS ON
#elif defined(_MSC_VER)
#pragma fenv_access(on)
#endif

namespace {

namespace up = kairn_bench::up;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;

// The greatest of four values, as m2_fenv.cpp chooses it (comparisons and selections).
template <class T>
KB_UP_INLINE T max4(T a, T b, T c, T e) {
    const T p = a < b ? b : a;
    const T q = c < e ? e : c;
    return p < q ? q : p;
}

// An interval under the mode upward: the operations of m2_fenv.cpp's iadd_up, isub_up, imul_up.
template <class T>
struct P {
    T l, u;
};
template <class T>
KB_UP_INLINE P<T> operator+(const P<T>& x, const P<T>& y) {
    return {-((-x.l) + (-y.l)), x.u + y.u};
}
template <class T>
KB_UP_INLINE P<T> operator-(const P<T>& x, const P<T>& y) {
    return {-(y.u - x.l), x.u - y.l};
}
template <class T>
KB_UP_INLINE P<T> operator*(const P<T>& x, const P<T>& y) {
    const T nl = -x.l, nu = -x.u;
    return {-max4(nl * y.l, nl * y.u, nu * y.l, nu * y.u), max4(x.l * y.l, x.l * y.u, x.u * y.l, x.u * y.u)};
}

struct Coordinates {
    const Raw<double>& r;
    P<double> at(const double* a, int j) const { return {a[2 * j], a[2 * j + 1]}; }
    P<double> x(int j) const { return at(r.xi, j); }
    P<double> y(int j) const { return at(r.yi, j); }
    P<double> f(int j) const { return at(r.fi, j); }
};

}  // namespace

#define XL r.xi[2 * i]
#define XU r.xi[2 * i + 1]
#define YL r.yi[2 * i]
#define YU r.yi[2 * i + 1]
#define KB_EACH(...)                                                                               \
    for (int i = 0; i < kN; ++i) {                                                                 \
        __VA_ARGS__;                                                                               \
    }

// X(KIND, KERNEL, VARIANT, OPS, BODY...): BODY between fesetround(FE_UPWARD) and fesetround(FE_TONEAREST).
#define KB_UPF_LIST(X)                                                                             \
    X(tp, det3_i1, fenv_loop, kN, const Coordinates g{r};                                              \
      KB_EACH(const P<double> z = up::det3_at<P<double>>(g, i); r.out[2 * i] = z.l; r.out[2 * i + 1] = z.u)) \
    X(tp, interval_add_1, fenv_loop_x16, up::kPasses * kN,                                             \
      for (int pass = 0; pass < up::kPasses; ++pass) {                                             \
          KB_EACH(const P<double> z = P<double>{XL, XU} + P<double>{YL, YU}; r.out[2 * i] = z.l;   \
                  r.out[2 * i + 1] = z.u)                                                          \
          KB_UP_FENCE();                                                                           \
      })                                                                                           \
    X(tp, interval_sub_1, fenv_loop_x16, up::kPasses * kN,                                         \
      for (int pass = 0; pass < up::kPasses; ++pass) {                                             \
          KB_EACH(const P<double> z = P<double>{XL, XU} - P<double>{YL, YU}; r.out[2 * i] = z.l;   \
                  r.out[2 * i + 1] = z.u)                                                          \
          KB_UP_FENCE();                                                                           \
      })                                                                                           \
    X(tp, interval_mul_1, fenv_loop_x16, up::kPasses * kN,                                         \
      for (int pass = 0; pass < up::kPasses; ++pass) {                                             \
          KB_EACH(const P<double> z = P<double>{XL, XU} * P<double>{YL, YU}; r.out[2 * i] = z.l;   \
                  r.out[2 * i + 1] = z.u)                                                          \
          KB_UP_FENCE();                                                                           \
      })                                                                                           \
    X(sum, interval_add_1, fenv_loop_x16, up::kPasses * kN, P<double> s{0, 0};                     \
      for (int pass = 0; pass < up::kPasses; ++pass) KB_EACH(s = s + P<double>{XL, XU})            \
      r.cout[0] = s.l; r.cout[1] = s.u;)                                                           \
    X(prod, interval_mul_1, fenv_loop_x16, up::kPasses * kN, P<double> p{1, 1};                    \
      for (int pass = 0; pass < up::kPasses; ++pass) KB_EACH(p = p * P<double>{r.fi[2 * i], r.fi[2 * i + 1]}) \
      r.cout[0] = p.l; r.cout[1] = p.u;)

#define KB_UPF_DEF(KIND, KERNEL, VAR, OPS, ...)                                                    \
    extern "C" KB_NOINLINE void kb_m2_64_##KIND##_##KERNEL##__##VAR(void* kb_data) {               \
        Raw<double>& r = *static_cast<Raw<double>*>(kb_data);                                      \
        std::fesetround(FE_UPWARD);                                                                \
        __VA_ARGS__                                                                                \
        std::fesetround(FE_TONEAREST);                                                             \
    }
#define KB_UPF_ROW(KIND, KERNEL, VAR, OPS, ...)                                                    \
    {"m2/" #KIND "/" #KERNEL "/" #VAR, kb_m2_64_##KIND##_##KERNEL##__##VAR, 64, 1, OPS, 0, 0, kairn_bench::up::check_raw_out},

KB_UPF_LIST(KB_UPF_DEF)

namespace {
const Entry table[] = {
    KB_UPF_LIST(KB_UPF_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
