// The functions on arrays of kairn/upward.hpp (bench/up_data.hpp): kairn::upward::add, sub and mul
// on views of two plain arrays, the upper bounds and the negated lower bounds, for double (backend
// upwa) and float (upwaf). Requires the rounding mode upward set by kairn::upward::Scope and the
// options of docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict):
// bench/CMakeLists.txt compiles this file with the option of the target kairn::upward and with the
// flags of packed code (-mavx2 -mfma on x86-64), so that the functions run their AVX2 form there
// (NEON on arm64, as every file); each function holds its own scope.
//
// - tp/interval_{add,sub,mul}_1/op: one call on arrays of kN elements, called from code that rounds
//   to nearest, time per element: next to Kairn's packed kernels and the packed props that set the
//   mode once around a loop (m2_packed.cpp, m2_fenv_packed.cpp; up_packed.cpp and up_fenv_packed.cpp
//   for those that do not exist there).
// - call/{add,mul}_L/VARIANT, double, L = 4, 16, 64, 256, 1024, 4096: calls_of(L) calls on the
//   consecutive windows of L elements of arrays of kLong elements, passes_of(L) times, at least 64
//   calls in all (up_data.hpp), time per call:
//   nearest, the public function called from code that rounds to nearest (its scope writes the
//   control register on entry and on exit); nested, the same inside an outer kairn::upward::Scope
//   (its scope reads the register and writes nothing); none, the generated array kernel that the
//   function runs (kairn::gen::upward::upward_add_1_arrays, upward_mul_1_arrays) inside an outer
//   Scope: the same call without its scope. The scope's cost per call is nearest (or nested) minus
//   none.
#include <kairn/upward.hpp>

#include <cstdlib>
#include <cstring>
#include <string>

#include "up_data.hpp"

namespace {

namespace ku = kairn::upward;
namespace kgu = kairn::gen::upward;
namespace up = kairn_bench::up;
using kairn_bench::m2::Entry;
using kairn_bench::m2::kN;
using kairn_bench::m2::Raw;
using up::kLong;

// The arrays of kLong elements, placed as up_data.hpp says (Placed): read in the slots 0 to 3,
// written in the slots 8 and 9.
template <class T>
struct ArrayData {
    up::Placed place{kLong * sizeof(T)};
    T* xu = place.at<T>(0);
    T* xn = place.at<T>(1);
    T* yu = place.at<T>(2);
    T* yn = place.at<T>(3);
    T* zu = place.at<T>(8);
    T* zn = place.at<T>(9);
};
ArrayData<double>* g64 = nullptr;
ArrayData<float>* g32 = nullptr;

template <class T>
ArrayData<T>& data();
template <>
ArrayData<double>& data<double>() {
    return *g64;
}
template <>
ArrayData<float>& data<float>() {
    return *g32;
}

// The lanes of the array form in this file (gen/upward.hpp).
#if KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_AVX2
constexpr int kLanes64 = 4, kLanes32 = 8;
#elif KAIRN_UPWARD_ARRAYS == KAIRN_UPWARD_ARRAYS_NEON
constexpr int kLanes64 = 2, kLanes32 = 4;
#else
constexpr int kLanes64 = 1, kLanes32 = 1;
#endif

// Element i: X[x_index(i)] and Y[y_index(i)] as the stored pairs (u, n) = (upper, -lower).
template <class T>
void fill(ArrayData<T>*& p, const Raw<T>& r) {
    if (!p) p = new ArrayData<T>();
    ArrayData<T>& d = *p;
    for (int i = 0; i < kLong; ++i) {
        const int a = up::x_index(i), b = up::y_index(i);
        d.xu[i] = r.xi[2 * a + 1];
        d.xn[i] = -r.xi[2 * a];
        d.yu[i] = r.yi[2 * b + 1];
        d.yn[i] = -r.yi[2 * b];
    }
}

template <class T>
void clear_t(ArrayData<T>& d) {
    std::memset(d.zu, 0xff, kLong * sizeof(T));
    std::memset(d.zn, 0xff, kLong * sizeof(T));
}
void clear(int bits) {
    if (bits == 32)
        clear_t(*g32);
    else
        clear_t(*g64);
}

// The results as (lower, upper): (-n, u) of each element written, kN of them for tp, covered(L)
// for call/OP_L.
template <class T>
int read_t(const Entry& e, T* o) {
    const ArrayData<T>& d = data<T>();
    const std::string name = e.name;
    int n = kN;
    const std::size_t call = name.find("/call/");
    if (call != std::string::npos) {
        const std::size_t us = name.find('_', call);
        n = up::covered(std::atoi(name.c_str() + us + 1));
    }
    for (int i = 0; i < n; ++i) {
        o[2 * i] = -d.zn[i];
        o[2 * i + 1] = d.zu[i];
    }
    return n;
}
int read(const Entry& e, void* lohi) {
    return e.bits == 32 ? read_t(e, static_cast<float*>(lohi)) : read_t(e, static_cast<double*>(lohi));
}

bool check(const Entry& e, char* why, std::size_t size) {
    const void* raw = kairn_bench::m2::m2_data(e.bits);
    if (e.bits == 32)
        fill(g32, *static_cast<const Raw<float>*>(raw));
    else
        fill(g64, *static_cast<const Raw<double>*>(raw));
    return up::run_and_check(e, clear, read, why, size);
}

}  // namespace

// --- The timed functions ------------------------------------------------------------------------

// The views of n elements from element o: written (z) and read (x, y).
#define VZ(o, n) ku::View<T>(d.zu + (o), d.zn + (o), std::size_t(n))
#define VX(o, n) ku::View<const T>(d.xu + (o), d.xn + (o), std::size_t(n))
#define VY(o, n) ku::View<const T>(d.yu + (o), d.yn + (o), std::size_t(n))
// The calls of length L on consecutive windows, passes_of(L) times.
#define KB_CALLS(L, ...)                                                                           \
    for (int pass = 0; pass < up::passes_of(L); ++pass) {                                          \
        for (int k = 0; k < up::calls_of(L); ++k) {                                                \
            const int o = k * (L);                                                                 \
            __VA_ARGS__;                                                                           \
        }                                                                                          \
        KB_UP_FENCE();                                                                             \
    }

// X(B, SUF, T, KIND, KERNEL, VARIANT, LANES, OPS, BODY...)
#define KB_ARRAYS_TP(X, B, SUF, T, LANES)                                                          \
    X(B, SUF, T, tp, interval_add_1, op, LANES, kN, ku::add(VZ(0, kN), VX(0, kN), VY(0, kN)))     \
    X(B, SUF, T, tp, interval_sub_1, op, LANES, kN, ku::sub(VZ(0, kN), VX(0, kN), VY(0, kN)))     \
    X(B, SUF, T, tp, interval_mul_1, op, LANES, kN, ku::mul(VZ(0, kN), VX(0, kN), VY(0, kN)))
#define KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, L)                                                 \
    X(B, SUF, T, call, OP##_##L, nearest, LANES, up::calls_of(L) * up::passes_of(L), KB_CALLS(L, ku::OP(VZ(o, L), VX(o, L), VY(o, L)))) \
    X(B, SUF, T, call, OP##_##L, nested, LANES, up::calls_of(L) * up::passes_of(L), ku::Scope scope;                  \
      KB_CALLS(L, ku::OP(VZ(o, L), VX(o, L), VY(o, L))))                                           \
    X(B, SUF, T, call, OP##_##L, none, LANES, up::calls_of(L) * up::passes_of(L), ku::Scope scope;                    \
      KB_CALLS(L, kgu::upward_##OP##_1_arrays(d.xu + o, d.xn + o, d.yu + o, d.yn + o, d.zu + o, d.zn + o, std::size_t(L))))
#define KB_ARRAYS_LENGTHS(X, B, SUF, T, LANES, OP)                                                 \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 4)                                                     \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 16)                                                    \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 64)                                                    \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 256)                                                   \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 1024)                                                  \
    KB_ARRAYS_CALL(X, B, SUF, T, LANES, OP, 4096)
#define KB_ARRAYS_LIST(X)                                                                          \
    KB_ARRAYS_TP(X, "upwa", upwa, double, kLanes64)                                                \
    KB_ARRAYS_TP(X, "upwaf", upwaf, float, kLanes32)                                               \
    KB_ARRAYS_LENGTHS(X, "upwa", upwa, double, kLanes64, add)                                      \
    KB_ARRAYS_LENGTHS(X, "upwa", upwa, double, kLanes64, mul)

#define KB_DEF(B, SUF, TYPE, KIND, KERNEL, VAR, LANES, OPS, ...)                                   \
    extern "C" KB_NOINLINE void kb_##SUF##_##KIND##_##KERNEL##__##VAR(void*) {                     \
        using T = TYPE;                                                                            \
        [[maybe_unused]] ArrayData<T>& d = data<T>();                                              \
        __VA_ARGS__;                                                                               \
    }
#define KB_ROW(B, SUF, T, KIND, KERNEL, VAR, LANES, OPS, ...)                                      \
    {B "/" #KIND "/" #KERNEL "/" #VAR, kb_##SUF##_##KIND##_##KERNEL##__##VAR, int(8 * sizeof(T)), LANES, OPS, 0, 0, check},

KB_ARRAYS_LIST(KB_DEF)

namespace {
const Entry table[] = {
    KB_ARRAYS_LIST(KB_ROW)
    {nullptr, nullptr, 0, 0, 0, 0, 0, nullptr},
};
kairn_bench::m2::TableLink link{table, nullptr};
[[maybe_unused]] const bool registered =
    (link.next = kairn_bench::m2::m2_extra_tables, kairn_bench::m2::m2_extra_tables = &link, true);
}  // namespace
