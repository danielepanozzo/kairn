// The forms of the public functions on arrays (kairn/batch.hpp) for the runner of the public
// interface (runner.cpp, which includes this file once, in its unnamed namespace): the requests of
// the folds, maps, convolutions and folds of maxima of the line protocol
// (docs/developer/architecture.md, "The line protocol": FOLD FORMAT ORDER N [inplace=I] SCALAR...
// LIMB... and CONV FORMAT seq N_X N_Y LIMB...), each completed through the public function that
// calls that loop, with views of the line's arrays (kairn::SoAView), as a program calls it.
//
// The order. A public function chooses its order by its own argument, not by the request: the form
// `sum` calls kairn::sum(x), the lane order of this build's form of Packed (the packed loop), and
// `sum_sequential` calls kairn::sum(kairn::sequential, x), whatever ORDER the line gives. The claims
// of every fold are the same in both of its orders (gen/claims.json gives each order the same
// heights), so the oracle's verdict on a line does not depend on which order computed it; the
// requests of the tests ask for seq.
//
// In place. A request with inplace=I passes array I's buffers as the array written, as a program
// writes y = a x + y with axpy(a, x, y, y): the map then reads and writes the same arrays.
//
// The loops on stored arrays (sum_1, sum_2, sum_fast_2, add_k, sub_k, axpy_1, axpy_2, axpy_2_1) have
// no public caller (batch.hpp says why) and are listed with the reason (--folds-not-public); the
// folds of BallVector have the forms of runner_ball_vector.hpp (--loops), and norm_upper_k the forms
// of both files. api/coverage.cmake checks that every fold of gen/claims.json is in one of these.
// Included once, by runner.cpp: its names are in an unnamed namespace.
#pragma once

#include <kairn/batch.hpp>

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <limits>
#include <string>
#include <vector>

namespace {

// One request of a loop over arrays, parsed: the lengths, the scalars' limbs, and every limb array
// read (array 0 limb 0, array 0 limb 1, array 1 limb 0, ...); the result's limbs and mask.
template <class T>
struct ArrayLine {
    std::size_t n = 0, nx = 0, ny = 0;  // n: every array's length; a convolution: nx and ny
    int inplace = -1;                   // the array read that is also written, or -1
    std::vector<T> scalars;
    std::vector<std::vector<T>> limbs;
    std::vector<T> out;  // a number's limbs, or each limb array written in turn
    bool mask = true;
};

// A view of array a of the line, of K limbs, read-only.
template <int K, class T>
kairn::SoAView<const T, K> in_view(const ArrayLine<T>& l, int a) {
    const std::size_t n = l.limbs[std::size_t(a * K)].size();
    if constexpr (K == 1) {
        return kairn::SoAView<const T, 1>(l.limbs[std::size_t(a)].data(), n);
    } else {
        return kairn::SoAView<const T, 2>(l.limbs[std::size_t(2 * a)].data(), l.limbs[std::size_t(2 * a + 1)].data(), n);
    }
}
// The array a map writes, of n elements: array I of the line itself in place, otherwise new
// arrays, into w.
template <int K, class T>
kairn::SoAView<T, K> out_view(ArrayLine<T>& l, std::vector<std::vector<T>>& w, std::size_t n) {
    T* p[K];
    for (int j = 0; j < K; ++j) {
        if (l.inplace >= 0) {
            p[j] = l.limbs[std::size_t(l.inplace * K + j)].data();
        } else {
            w.emplace_back(n, T(0));
            p[j] = w.back().data();
        }
    }
    if constexpr (K == 1) {
        return kairn::SoAView<T, 1>(p[0], n);
    } else {
        return kairn::SoAView<T, 2>(p[0], p[1], n);
    }
}
template <int K, class T>
void put_number(ArrayLine<T>& l, const kairn::Reduction<kairn::Expansion<T, K>>& r) {
    for (int j = 0; j < K; ++j) l.out.push_back(r.value.limb[j]);
    l.mask = r.finite;
}
template <int K, class T>
void put_array(ArrayLine<T>& l, const kairn::SoAView<T, K>& z, bool finite) {
    for (int j = 0; j < K; ++j)
        for (std::size_t i = 0; i < z.size(); ++i) l.out.push_back(z.limb(j)[i]);
    l.mask = finite;
}

// The forms. Each is a function template of the limb type, instantiated for double and float.
template <int K, bool Seq, class T>
void af_sum(ArrayLine<T>& l) {
    if constexpr (Seq) put_number<K>(l, kairn::sum(kairn::sequential, in_view<K>(l, 0)));
    else put_number<K>(l, kairn::sum(in_view<K>(l, 0)));
}
template <int K, bool Seq, class T>
void af_sum_fast(ArrayLine<T>& l) {
    if constexpr (Seq) put_number<K>(l, kairn::sum_fast(kairn::sequential, in_view<K>(l, 0)));
    else put_number<K>(l, kairn::sum_fast(in_view<K>(l, 0)));
}
template <int K, bool Seq, class T>
void af_dot(ArrayLine<T>& l) {
    if constexpr (Seq) put_number<K>(l, kairn::dot(kairn::sequential, in_view<K>(l, 0), in_view<K>(l, 1)));
    else put_number<K>(l, kairn::dot(in_view<K>(l, 0), in_view<K>(l, 1)));
}
// The maps, with a view of the arrays written (in place for inplace=I).
template <int K, class T>
void af_add(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const auto x = in_view<K>(l, 0), y = in_view<K>(l, 1);
    const auto z = out_view<K>(l, w, l.n);
    put_array(l, z, kairn::add(x, y, z));
}
template <int K, class T>
void af_sub(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const auto x = in_view<K>(l, 0), y = in_view<K>(l, 1);
    const auto z = out_view<K>(l, w, l.n);
    put_array(l, z, kairn::sub(x, y, z));
}
template <int K, class T>
void af_scale(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const auto x = in_view<K>(l, 0);
    const auto z = out_view<K>(l, w, l.n);
    put_array(l, z, kairn::scale(x, l.scalars[0], z));
}
template <int K, class T>
void af_mul_pow2(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const auto x = in_view<K>(l, 0);
    const auto z = out_view<K>(l, w, l.n);
    put_array(l, z, kairn::mul_pow2(x, l.scalars[0], z));
}
// axpy with a scalar of T (axpy_1_entry, axpy_2_1_entry), and of two limbs (axpy_2_entry), built
// with from_limbs as a program builds a number.
template <int K, class T>
void af_axpy(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const auto x = in_view<K>(l, 0), y = in_view<K>(l, 1);
    const auto z = out_view<K>(l, w, l.n);
    put_array(l, z, kairn::axpy(l.scalars[0], x, y, z));
}
template <int K, class T>
void af_axpy_2(ArrayLine<T>& l) {
    static_assert(K == 2, "a scalar of two limbs");
    std::vector<std::vector<T>> w;
    const auto x = in_view<2>(l, 0), y = in_view<2>(l, 1);
    const auto z = out_view<2>(l, w, l.n);
    const T a[2] = {l.scalars[0], l.scalars[1]};
    put_array(l, z, kairn::axpy(kairn::Expansion<T, 2>::from_limbs(a), x, y, z));
}
template <int K, class T>
void af_conv(ArrayLine<T>& l) {
    std::vector<std::vector<T>> w;
    const std::size_t nz = l.nx == 0 || l.ny == 0 ? 0 : l.nx + l.ny - 1;
    const auto z = out_view<K>(l, w, nz);
    put_array(l, z, kairn::conv(in_view<K>(l, 0), in_view<K>(l, 1), z));
}
template <int K, class T>
void af_norm_upper(ArrayLine<T>& l) {
    const kairn::Reduction<T> r = kairn::norm_upper(in_view<K>(l, 0));
    l.out.push_back(r.value);
    l.mask = r.finite;
}

struct ArrayForm {
    const char* fold;
    const char* name;
    char kind;            // r: a number of k limbs; n: a T (a fold of maxima); m: a map; c: a convolution
    int k;                // the limbs of every array
    int arrays;           // the arrays read
    const char* scalars;  // the limbs of each scalar, in order
    bool packed;          // calls the packed loop: also a form of the runner of the packed forms alone
    void (*binary64)(ArrayLine<double>&);
    void (*binary32)(ArrayLine<float>&);
};
#define AROW(FOLD, NAME, KIND, K, ARRAYS, SCALARS, PACKED, FN, ...) \
    {#FOLD, #NAME, KIND, K, ARRAYS, SCALARS, PACKED, FN<__VA_ARGS__, double>, FN<__VA_ARGS__, float>},
// The sums and dot products in both orders; the maps, whose results do not depend on the order;
// the convolutions (sequential only) and the folds of maxima (the same state in every order).
const ArrayForm array_forms[] = {
    AROW(sum_1_entry, sum, 'r', 1, 1, "", true, af_sum, 1, false)
    AROW(sum_1_entry, sum_sequential, 'r', 1, 1, "", false, af_sum, 1, true)
    AROW(sum_1_entry, sum_fast, 'r', 1, 1, "", true, af_sum_fast, 1, false)
    AROW(sum_1_entry, sum_fast_sequential, 'r', 1, 1, "", false, af_sum_fast, 1, true)
    AROW(sum_2_entry, sum, 'r', 2, 1, "", true, af_sum, 2, false)
    AROW(sum_2_entry, sum_sequential, 'r', 2, 1, "", false, af_sum, 2, true)
    AROW(sum_fast_2_entry, sum_fast, 'r', 2, 1, "", true, af_sum_fast, 2, false)
    AROW(sum_fast_2_entry, sum_fast_sequential, 'r', 2, 1, "", false, af_sum_fast, 2, true)
    AROW(dot_1_entry, dot, 'r', 1, 2, "", true, af_dot, 1, false)
    AROW(dot_1_entry, dot_sequential, 'r', 1, 2, "", false, af_dot, 1, true)
    AROW(dot_2, dot, 'r', 2, 2, "", true, af_dot, 2, false)
    AROW(dot_2, dot_sequential, 'r', 2, 2, "", false, af_dot, 2, true)
    AROW(add_1_entry, add, 'm', 1, 2, "", true, af_add, 1)
    AROW(add_2_entry, add, 'm', 2, 2, "", true, af_add, 2)
    AROW(sub_1_entry, sub, 'm', 1, 2, "", true, af_sub, 1)
    AROW(sub_2_entry, sub, 'm', 2, 2, "", true, af_sub, 2)
    AROW(scale_1, scale, 'm', 1, 1, "1", true, af_scale, 1)
    AROW(scale_2, scale, 'm', 2, 1, "1", true, af_scale, 2)
    AROW(mul_pow2_map_1, mul_pow2, 'm', 1, 1, "1", true, af_mul_pow2, 1)
    AROW(mul_pow2_map_2, mul_pow2, 'm', 2, 1, "1", true, af_mul_pow2, 2)
    AROW(axpy_1_entry, axpy, 'm', 1, 2, "1", true, af_axpy, 1)
    AROW(axpy_2_1_entry, axpy, 'm', 2, 2, "1", true, af_axpy, 2)
    AROW(axpy_2_entry, axpy, 'm', 2, 2, "2", true, af_axpy_2, 2)
    AROW(conv_1, conv, 'c', 1, 2, "", false, af_conv, 1)
    AROW(conv_2, conv, 'c', 2, 2, "", false, af_conv, 2)
    AROW(norm_upper_1, norm_upper, 'n', 1, 1, "", true, af_norm_upper, 1)
    AROW(norm_upper_2, norm_upper, 'n', 2, 1, "", true, af_norm_upper, 2)
};
#undef AROW

// The folds of gen/claims.json that no public function calls, and why (api/coverage.cmake).
struct FoldNotPublic {
    const char* fold;
    const char* why;
};
const char* const stored_fold = "the loop on stored arrays, written through Kairn only: no container of the library "
                                "holds such arrays, and the functions of kairn/batch.hpp call the loop on supplied "
                                "arrays (_entry)";
const char* const factors_fold = "the dot product of one limb with its factors unguarded: kairn::dot of one limb "
                                 "calls dot_1_entry, whose step guards both factors (rule R3, the factors of a fused "
                                 "operation), and conv_1 runs dot_1's step for each coefficient";
const FoldNotPublic folds_not_public[] = {
    {"sum_1", stored_fold},  {"sum_2", stored_fold}, {"sum_fast_2", stored_fold}, {"add_1", stored_fold},
    {"add_2", stored_fold},  {"sub_1", stored_fold}, {"sub_2", stored_fold},      {"axpy_1", stored_fold},
    {"axpy_2", stored_fold}, {"axpy_2_1", stored_fold}, {"dot_1", factors_fold},
};

// Whether a form of the array forms is listed by this runner: all of them, but in the runner of the
// packed forms alone (KAIRN_TEST_PACKED_ONLY) only those that call a packed loop.
inline bool array_form_listed(const ArrayForm& f) {
#if defined(KAIRN_TEST_PACKED_ONLY)
    return f.packed;
#else
    (void)f;
    return true;
#endif
}

// A decimal count, as the line protocol writes it: digits, without a sign or a leading zero.
inline bool parse_count(const std::string& s, std::size_t& n) {
    if (s.empty() || s.size() > 18 || (s.size() > 1 && s[0] == '0')) return false;
    n = 0;
    for (char c : s) {
        if (c < '0' || c > '9') return false;
        n = n * 10 + std::size_t(c - '0');
    }
    return true;
}

// Completes one request of a loop over arrays: fields as runner.cpp splits them (the tag removed),
// out the line as completed so far (the request and " ->"). Returns the reason the line is refused,
// or an empty string.
template <class T>
std::string complete_array_line(const ArrayForm& f, const std::vector<std::string>& fields, std::string& out,
                                double (*parse_limb)(const std::string&), void (*put)(double, std::string&)) {
    ArrayLine<T> l;
    std::size_t at = 3;
    if (f.kind == 'c') {
        if (fields.size() < 5 || !parse_count(fields[3], l.nx) || !parse_count(fields[4], l.ny))
            return "a convolution's request is CONV FORMAT seq N_X N_Y LIMB...";
        at = 5;
    } else {
        if (fields.size() < 4 || !parse_count(fields[3], l.n)) return "a fold's request is FOLD FORMAT ORDER N ...";
        at = 4;
        if (at < fields.size() && fields[at].rfind("inplace=", 0) == 0) {
            std::size_t i = 0;
            if (f.kind != 'm' || !parse_count(fields[at].substr(8), i) || int(i) >= f.arrays)
                return "inplace=I: I is an array that the map reads";
            l.inplace = int(i);
            ++at;
        }
    }
    const std::string order = fields[2];
    if (order != "seq" && order.rfind("lanes:", 0) != 0) return "the order is seq or lanes:W";
    if (f.kind == 'c' && order != "seq") return "a convolution has the sequential order only";
    // The scalars, then each limb of each array.
    std::size_t limbs = 0;
    for (const char* s = f.scalars; *s; ++s) limbs += std::size_t(*s - '0');
    std::size_t entries = 0;
    for (int a = 0; a < f.arrays; ++a)
        entries += std::size_t(f.k) * (f.kind == 'c' ? (a == 0 ? l.nx : l.ny) : l.n);
    if (fields.size() - at != limbs + entries)
        return "the request has " + std::to_string(fields.size() - at) + " limbs, not " + std::to_string(limbs + entries);
    auto read = [&](std::size_t i, T& v) -> bool {
        const double d = parse_limb(fields[i]);
        if constexpr (sizeof(T) == 4) {
            const double top = std::numeric_limits<float>::max();
            if (d == d && d - d == 0 && (d > top || d < -top)) return false;
            v = static_cast<float>(d);
            if (static_cast<double>(v) != d && d == d) return false;
        } else {
            v = d;
        }
        return true;
    };
    for (std::size_t i = 0; i < limbs; ++i) {
        T v{};
        if (!read(at + i, v)) return fields[at + i] + " is not a binary32 number";
        l.scalars.push_back(v);
    }
    std::size_t i = at + limbs;
    for (int a = 0; a < f.arrays; ++a) {
        const std::size_t n = f.kind == 'c' ? (a == 0 ? l.nx : l.ny) : l.n;
        for (int j = 0; j < f.k; ++j) {
            l.limbs.emplace_back(n);
            for (std::size_t e = 0; e < n; ++e, ++i)
                if (!read(i, l.limbs.back()[e])) return fields[i] + " is not a binary32 number";
        }
    }
    if constexpr (sizeof(T) == 8) {
        f.binary64(l);
    } else {
        f.binary32(l);
    }
    for (T v : l.out) {
        out += ' ';
        put(static_cast<double>(v), out);
    }
    out += l.mask ? " 1" : " 0";
    return "";
}

}  // namespace
