// The checks of the benchmark of the round-up interval (bench/up_data.hpp), made before anything is
// timed: ordinary code, compiled as m2.cpp is and run under rounding to nearest.
//
// run_and_check runs a function on cleared outputs, from rounding to nearest, and refuses it if the
// rounding mode (the C library's, and the control register: MXCSR's or FPCR's rounding control and
// flush to zero) is not what it was before the call; reads its results as (lower, upper) pairs; and
// compares them with the same computation by Kairn's default kernels on the same operands (the
// variant kairn of m2.cpp, written with the types of up_kernels.hpp): every bound equal, a zero of
// the other sign counted and not refused; for one product of intervals, a bound one number tighter
// than the default's counted and not refused where the default's may be one number wider (its
// magnitude below P = 2^(2p-1) eta); any other difference refused. On these operands no product is
// below P, so every function that computes what it claims gives the default's bounds. It counts the
// values that differ from the same computation rounded to nearest, and refuses a function that
// rounds and has none (the mode would not have been honored). Each check prints its counts on the
// standard error ("up check: ...").
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <string>
#include <vector>

#if defined(__x86_64__) || defined(_M_X64)
#include <xmmintrin.h>
#endif

#include "up_kernels.hpp"

namespace kairn_bench::up {

namespace {

// The same computations rounded to nearest, plain arithmetic of T: what a function that ignored
// the rounding mode would have computed. (Compiled without contraction, as every file here.)
template <class T>
struct N {
    T l, u;
};
template <class T>
N<T> operator+(const N<T>& x, const N<T>& y) {
    return {x.l + y.l, x.u + y.u};
}
template <class T>
N<T> operator-(const N<T>& x, const N<T>& y) {
    return {x.l - y.u, x.u - y.l};
}
template <class T>
N<T> operator*(const N<T>& x, const N<T>& y) {
    const T p1 = x.l * y.l, p2 = x.l * y.u, p3 = x.u * y.l, p4 = x.u * y.u;
    return {std::fmin(std::fmin(p1, p2), std::fmin(p3, p4)), std::fmax(std::fmax(p1, p2), std::fmax(p3, p4))};
}

// What a function computes, from its name BACKEND/KIND/KERNEL/VARIANT.
struct What {
    std::string op;    // add, sub, mul, sum, prod, horner, lat, det3, copy
    int n = 0;         // results: elements, or 1 for a chain
    bool products = false;
    bool rounds = true;
};

bool what_of(const std::string& name, What& w) {
    std::string part[4];
    std::size_t at = 0;
    for (int k = 0; k < 4; ++k) {
        const std::size_t slash = k < 3 ? name.find('/', at) : std::string::npos;
        part[k] = name.substr(at, slash == std::string::npos ? std::string::npos : slash - at);
        at = slash + 1;
    }
    const std::string &kind = part[1], &kernel = part[2];
    auto binary = [&](const std::string& op, int n) {
        w.op = op;
        w.n = n;
        w.products = op == "mul";
        return true;
    };
    if (kind == "tp") {
        if (kernel == "interval_add_1") return binary("add", kN);
        if (kernel == "interval_sub_1") return binary("sub", kN);
        if (kernel == "interval_mul_1") return binary("mul", kN);
        if (kernel == "horner_i1" || kernel == "det3_i1") {
            w.op = kernel == "horner_i1" ? "horner" : "det3";
            w.n = kN;
            w.products = true;
            return true;
        }
        if (kernel == "from_interval_1" || kernel == "to_interval_1") {
            w.op = "copy";
            w.n = kN;
            w.rounds = false;
            return true;
        }
        return false;
    }
    if (kind == "call") {
        // The scopes' calls, one sum each; the functions on arrays per length, add_L and mul_L.
        if (kernel == "scope_add_1" || kernel == "regscope_add_1" || kernel == "nearest_add_1") return binary("add", kN);
        const std::size_t us = kernel.find('_');
        if (us == std::string::npos) return false;
        const std::string op = kernel.substr(0, us);
        const int length = std::atoi(kernel.c_str() + us + 1);
        if ((op != "add" && op != "mul") || length < 1 || length > kLong) return false;
        return binary(op, covered(length));
    }
    if (kind == "sum" && kernel == "interval_add_1") {
        w.op = "sum";
        w.n = 1;
        return true;
    }
    if (kind == "prod" && kernel == "interval_mul_1") {
        w.op = "prod";
        w.n = 1;
        w.products = true;
        return true;
    }
    if (kind == "lat" && kernel == "horner_i1") {
        w.op = "lat";
        w.n = 1;
        w.products = true;
        return true;
    }
    return false;
}

// The computation w on the benchmark's operands (Raw<T>, the intervals X, Y, F of one limb, the
// arguments and coefficients of Horner) with the operations of I: K1<T> (Kairn's default kernels)
// or N<T> (rounded to nearest).
template <class T, class I>
std::vector<I> compute(const Raw<T>& r, const What& w) {
    auto X = [&](int j) { return I{r.xi[2 * j], r.xi[2 * j + 1]}; };
    auto Y = [&](int j) { return I{r.yi[2 * j], r.yi[2 * j + 1]}; };
    auto F = [&](int j) { return I{r.fi[2 * j], r.fi[2 * j + 1]}; };
    auto H = [&](int j) { return I{r.hi1[2 * j], r.hi1[2 * j + 1]}; };
    std::vector<I> out;
    I c[kDeg + 1];
    for (int k = 0; k <= kDeg; ++k) c[k] = I{r.hc[k], r.hc[k]};
    if (w.op == "add" || w.op == "sub" || w.op == "mul") {
        for (int i = 0; i < w.n; ++i) {
            const I x = X(x_index(i)), y = Y(y_index(i));
            out.push_back(w.op == "add" ? x + y : w.op == "sub" ? x - y : x * y);
        }
    } else if (w.op == "sum") {
        I s{T(0), T(0)};
        for (int i = 0; i < kN; ++i) s = s + X(i);
        out.push_back(s);
    } else if (w.op == "prod") {
        I p{T(1), T(1)};
        for (int i = 0; i < kN; ++i) p = p * F(i);
        out.push_back(p);
    } else if (w.op == "horner") {
        for (int i = 0; i < kN; ++i) out.push_back(horner(c, H(i)));
    } else if (w.op == "lat") {
        // As the timed functions: each argument plus a zero, (a bound of the evaluation before) * 0.
        T z = 0;
        I p{T(0), T(0)};
        for (int i = 0; i < kN; ++i) {
            const I h = H(i);
            p = horner(c, I{h.l + z, h.u + z});
            z = p.u * T(0);
        }
        out.push_back(p);
    } else if (w.op == "det3") {
        struct G {
            decltype(X)& gx;
            decltype(Y)& gy;
            decltype(F)& gf;
            I x(int j) const { return gx(j); }
            I y(int j) const { return gy(j); }
            I f(int j) const { return gf(j); }
        };
        const G g{X, Y, F};
        for (int i = 0; i < kN; ++i) out.push_back(det3_at<I>(g, i));
    } else if (w.op == "copy") {
        for (int i = 0; i < w.n; ++i) out.push_back(X(i));
    }
    return out;
}

template <class T>
bool same_bits(T a, T b) {
    return std::memcmp(&a, &b, sizeof(T)) == 0;
}

template <class T>
bool compare(const Entry& e, const What& w, const T* got, int n, char* why, std::size_t size) {
    const Raw<T>& r = *static_cast<const Raw<T>*>(m2::m2_data(e.bits));
    if (n != w.n) {
        std::snprintf(why, size, "%d results, expected %d", n, w.n);
        return false;
    }
    const std::vector<K1<T>> ref = compute<T, K1<T>>(r, w);
    const std::vector<N<T>> rn = compute<T, N<T>>(r, w);
    if (int(ref.size()) != n || int(rn.size()) != n) {
        std::snprintf(why, size, "no reference");
        return false;
    }
    // P = 2^(2p - 1) eta: below it a product of the default kernels may be one number wider.
    const T P = sizeof(T) == 8 ? T(0x1p-969) : T(0x1p-102);
    constexpr T inf = std::numeric_limits<T>::infinity();
    long equal = 0, zero_sign = 0, tighter = 0, differ_rn = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < 2; ++j) {
            const T g = got[2 * i + j];
            const T k = j == 0 ? ref[std::size_t(i)].l : ref[std::size_t(i)].u;
            const T q = j == 0 ? rn[std::size_t(i)].l : rn[std::size_t(i)].u;
            differ_rn += !same_bits(g, q);
            if (g == k) {
                if (same_bits(g, k))
                    ++equal;
                else
                    ++zero_sign;   // the sign of a zero bound, which no claim fixes
                continue;
            }
            const T outward = j == 0 ? -inf : inf;
            if (w.op == "mul" && std::fabs(g) < P && k == std::nextafter(g, outward)) {
                ++tighter;
                continue;
            }
            std::snprintf(why, size, "element %d, %s bound: %a, Kairn's default kernels %a", i, j == 0 ? "lower" : "upper",
                          double(g), double(k));
            return false;
        }
    }
    std::fprintf(stderr,
                 "up check: %s: %d values: %ld equal to Kairn's default kernels, %ld zeros of the other sign, %ld one "
                 "number tighter below P; %ld differ from rounding to nearest\n",
                 e.name, 2 * n, equal, zero_sign, tighter, differ_rn);
    if (w.rounds && differ_rn == 0) {
        std::snprintf(why, size, "every value is the one rounded to nearest: the rounding mode was not honored");
        return false;
    }
    return true;
}

// The rounding mode to nearest everywhere a function can leave it otherwise: the C library's, and
// the rounding control and flush to zero of the control register.
#if defined(__x86_64__) || defined(_M_X64)
using Control = unsigned int;
Control read_control() { return _mm_getcsr() & 0xE040u; }   // RC, FZ, DAZ
#elif defined(__aarch64__) && defined(__GNUC__)
using Control = std::uint64_t;
Control read_control() {
    std::uint64_t v;
    __asm__ __volatile__("mrs %0, fpcr" : "=r"(v));
    return v & ((std::uint64_t(3) << 22) | (std::uint64_t(1) << 24) | std::uint64_t(3));   // RMode, FZ, AH, FIZ
}
#else
using Control = int;
Control read_control() { return 0; }
#endif

template <class T>
bool run_and_check_t(const Entry& e, ClearFn clear, ReadFn read, char* why, std::size_t size) {
    What w;
    if (!what_of(e.name, w)) {
        std::snprintf(why, size, "no reference for this name");
        return false;
    }
    const Control before = read_control();
    if (std::fegetround() != FE_TONEAREST) {
        std::snprintf(why, size, "the rounding mode was not to nearest before the call");
        return false;
    }
    clear(e.bits);
    e.fn(m2::m2_data(e.bits));
    const bool library = std::fegetround() == FE_TONEAREST;
    const bool control = read_control() == before;
    if (!library || !control) {
        std::fesetround(FE_TONEAREST);
        std::snprintf(why, size, "the function left the %s other than it found it",
                      library ? "control register" : "rounding mode of the C library");
        return false;
    }
    std::vector<T> got(2 * kLong);
    const int n = read(e, got.data());
    return compare<T>(e, w, got.data(), n, why, size);
}

// Raw<T>'s outputs: r.out as (lower, upper) pairs, or a chain's r.cout[0], r.cout[1].
template <class T>
int read_out(const Entry& e, void* lohi) {
    const Raw<T>& r = *static_cast<const Raw<T>*>(m2::m2_data(e.bits));
    T* o = static_cast<T*>(lohi);
    What w;
    what_of(e.name, w);
    if (w.n == 1) {
        o[0] = r.cout[0];
        o[1] = r.cout[1];
        return 1;
    }
    for (int i = 0; i < 2 * kN; ++i) o[i] = r.out[i];
    return kN;
}
template <class T>
int read_sout(const Entry& e, void* lohi) {
    const Raw<T>& r = *static_cast<const Raw<T>*>(m2::m2_data(e.bits));
    T* o = static_cast<T*>(lohi);
    for (int i = 0; i < kN; ++i) {
        o[2 * i] = r.sout[0][i];
        o[2 * i + 1] = r.sout[1][i];
    }
    return kN;
}

}  // namespace

bool run_and_check(const Entry& e, ClearFn clear, ReadFn read, char* why, std::size_t size) {
    return e.bits == 32 ? run_and_check_t<float>(e, clear, read, why, size)
                        : run_and_check_t<double>(e, clear, read, why, size);
}

bool check_raw_out(const Entry& e, char* why, std::size_t size) {
    return run_and_check(e, m2::m2_clear, e.bits == 32 ? read_out<float> : read_out<double>, why, size);
}

bool check_raw_sout(const Entry& e, char* why, std::size_t size) {
    return run_and_check(e, m2::m2_clear, e.bits == 32 ? read_sout<float> : read_sout<double>, why, size);
}

}  // namespace kairn_bench::up
