// The tests of the emulated arithmetic (number.hpp) that need no oracle, and the program through
// which tests/emulated/test_emulated.py holds it to the oracle's exact rounding.
//
//   selftest --hardware binary32|binary64 --count N [--seed S] [--fault NAME]
//       N stratified cases of every operation of number.hpp, in the format of float (p = 24,
//       qmin = -149, qmax = 104) or of double (53, -1074, 971), against the machine's own float or
//       double, bit for bit (a NaN against a NaN); exit 1 on any difference, with the first ones.
//   selftest --ops FORMAT [--fault NAME]
//       lines "OP A [B [C]]" on standard input, the result of each on standard output (a limb, a
//       mask 0 or 1, or a decimal integer), OP one of add sub mul fma fms fnma prod neg abs
//       next_up next_down lt le gt ge eq ne times_inf times_inf_ce to_size from_size pow2.
//
// --fault plants a fault in the rounding (number.hpp, plant_fault), which every comparison here
// must catch: test_emulated.py runs each with each fault and fails if a run passes.
#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <map>
#include <string>
#include <vector>

#include "number.hpp"

namespace {

using kairn::emulated::Number;

// splitmix64.
struct Random {
    std::uint64_t s;
    std::uint64_t next() {
        std::uint64_t z = (s += 0x9e3779b97f4a7c15u);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9u;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebu;
        return z ^ (z >> 31);
    }
    std::uint64_t below(std::uint64_t n) { return n ? next() % n : 0; }
    bool coin() { return next() & 1; }
};

// The IEEE layout of float and double: P bits of precision, E bits of exponent.
template <class T, class U, int P, int E>
struct Layout {
    using type = T;
    using bits_type = U;
    static constexpr int precision = P;
    static constexpr int exponent_bits = E;
    static constexpr int field_max = (1 << E) - 1;          // the exponent field of inf and NaN
    static constexpr int bias = (1 << (E - 1)) - 1;
    static constexpr int qmin = 1 - bias - (P - 1);
    static constexpr int qmax = field_max - 1 - bias - (P - 1);
    static constexpr U frac_mask = (U{1} << (P - 1)) - 1;

    static U bits(T x) { return std::bit_cast<U>(x); }
    static T value(U b) { return std::bit_cast<T>(b); }
    static U make(bool negative, int field, U frac) {
        return (U(negative) << (P - 1 + E)) | (U(field) << (P - 1)) | (frac & frac_mask);
    }
    // The emulated number of the same bits (the format is set to this layout's).
    static Number to_number(T x) {
        const U b = bits(x);
        const bool negative = (b >> (P - 1 + E)) & 1;
        const int field = int((b >> (P - 1)) & U(field_max));
        const U frac = b & frac_mask;
        if (field == field_max) return frac ? Number::nan() : Number::infinity(negative);
        Number out;
        const std::uint64_t m = field ? std::uint64_t(frac) | (std::uint64_t{1} << (P - 1)) : std::uint64_t(frac);
        const int q = field ? qmin + field - 1 : qmin;
        if (!Number::make(negative, m, q, out)) {
            std::fprintf(stderr, "selftest: the layout is wrong\n");
            std::exit(3);
        }
        return out;
    }
    // The bits of an emulated number of this format; a NaN as the default quiet NaN.
    static U from_number(Number v) {
        if (v.is_nan()) return bits(std::numeric_limits<T>::quiet_NaN());
        if (v.kind() == Number::Kind::infinite) return make(v.negative(), field_max, 0);
        const std::uint64_t m = v.significand();
        if (m == 0) return make(v.negative(), 0, 0);
        const bool normal = m >> (P - 1);
        const int field = normal ? v.exponent() - qmin + 1 : 0;
        return make(v.negative(), field, U(m));
    }
};
using L32 = Layout<float, std::uint32_t, 24, 8>;
using L64 = Layout<double, std::uint64_t, 53, 11>;

// Operands from strata, as bit patterns: every class of value and the corners of each operation.
template <class L>
struct Operands {
    using T = typename L::type;
    using U = typename L::bits_type;
    Random& r;

    U frac() { return U(r.next()) & L::frac_mask; }
    // A few significant bits only, at the top or the bottom.
    U short_frac() {
        const U f = frac() & U(r.below(16));
        return r.coin() ? f << (L::precision - 1 - 4) : f;
    }
    T finite_with_field(int field) { return L::value(L::make(r.coin(), field, r.coin() ? frac() : short_frac())); }
    T special() {
        const T inf = std::numeric_limits<T>::infinity();
        const T table[] = {T(0), -T(0), inf, -inf, std::numeric_limits<T>::quiet_NaN(),
                           std::numeric_limits<T>::denorm_min(), std::numeric_limits<T>::min(),
                           std::numeric_limits<T>::max(), T(1), T(2), T(0.5), T(3),
                           std::nextafter(T(1), T(0)), std::nextafter(T(1), T(2)),
                           std::nextafter(std::numeric_limits<T>::min(), T(0)),
                           std::nextafter(std::numeric_limits<T>::max(), T(0))};
        const T x = table[r.below(sizeof table / sizeof table[0])];
        return r.coin() ? x : -x;
    }
    T any(int stratum) {
        switch (stratum) {
        case 0: return L::value(U(r.next()));                                       // any bits
        case 1: return finite_with_field(int(r.below(L::field_max)));               // finite
        case 2: return finite_with_field(0);                                        // subnormal
        case 3: return finite_with_field(1 + int(r.below(3)));                      // just above
        case 4: return finite_with_field(L::field_max - 1 - int(r.below(3)));       // the top
        default: return special();
        }
    }
    // A second operand near the first: exponents within P + 3 binades, its negation within a few
    // places (cancellation), half a place of it (a tie of a sum), a quarter, or a place more.
    T near(T a) {
        const U b = L::bits(a);
        const int field = int((b >> (L::precision - 1)) & U(L::field_max));
        switch (r.below(5)) {
        case 0: {
            int f = field + int(r.below(2 * L::precision + 7)) - (L::precision + 3);
            f = f < 0 ? 0 : f >= L::field_max ? L::field_max - 1 : f;
            return finite_with_field(f);
        }
        case 1: return L::value((b ^ (U{1} << (L::precision - 1 + L::exponent_bits))) + U(r.below(5)) - U(2));
        case 2: {
            const int f = field - L::precision;     // ulp(a) / 2 and odd multiples, or a tail of a
            const U t = r.coin() ? 0 : frac();
            return f > 0 ? L::value(L::make(r.coin(), f, t)) : L::value(L::make(r.coin(), 0, U{1} << (r.below(4))));
        }
        case 3: {
            const int f = field - L::precision - 1 - int(r.below(3));
            return f > 0 ? L::value(L::make(r.coin(), f, frac())) : finite_with_field(0);
        }
        default: return L::value(b + U(r.below(3)) - U(1));
        }
    }
    // A factor whose product with a falls at the top, near the smallest normal number, in the
    // subnormal range, or below it.
    T factor(T a) {
        const U b = L::bits(a);
        const int field = int((b >> (L::precision - 1)) & U(L::field_max));
        const int targets[] = {L::field_max - 1, L::field_max, 1, 0, -L::precision, -2 * L::precision};
        const int target = targets[r.below(6)] + int(r.below(5)) - 2;
        int f = target - field + L::bias;
        f = f < 0 ? 0 : f >= L::field_max ? L::field_max - 1 : f;
        return finite_with_field(f);
    }
};

struct Tally {
    std::map<std::string, long> cases, failures;
    long shown = 0;
    void check(const std::string& op, bool same, const std::string& what) {
        ++cases[op];
        if (same) return;
        ++failures[op];
        if (shown++ < 20) std::printf("DIFFERENT %s\n", what.c_str());
    }
};

template <class L>
std::string text(typename L::type x) {
    return kairn::emulated::to_text(L::to_number(x));
}

template <class L>
bool same(typename L::type hw, Number em) {
    if (std::isnan(hw)) return em.is_nan();
    return L::bits(hw) == L::from_number(em);
}

// volatile, so that no operation of the machine is contracted with another or evaluated at another
// precision: each is one operation of T, stored.
template <class T>
T stored(T x) {
    volatile T v = x;
    return v;
}

template <class L>
int hardware(long count, std::uint64_t seed) {
    using T = typename L::type;
    using U = typename L::bits_type;
    std::string why;
    if (!kairn::emulated::set_format({L::precision, L::qmin, L::qmax}, &why)) {
        std::fprintf(stderr, "selftest: %s\n", why.c_str());
        return 2;
    }
    Random r{seed};
    Operands<L> g{r};
    Tally t;
    const T inf = std::numeric_limits<T>::infinity();
    std::map<int, long> strata;
    for (long i = 0; i < count; ++i) {
        const int s = int(i % 6);
        ++strata[s];
        const T a = g.any(s);
        const T b = (i / 6) % 3 == 0 ? g.any(int(r.below(6))) : (i / 6) % 3 == 1 ? g.near(a) : g.factor(a);
        T c;
        switch (r.below(4)) {
        case 0: c = g.any(int(r.below(6))); break;
        case 1: c = -stored(a * b); break;                       // cancels the product
        case 2: c = std::nextafter(-stored(a * b), r.coin() ? inf : -inf); break;
        default: c = g.near(stored(a * b)); break;
        }
        const Number ea = L::to_number(a), eb = L::to_number(b), ec = L::to_number(c);
        const std::string ab = text<L>(a) + " " + text<L>(b), abc = ab + " " + text<L>(c);
        t.check("add", same<L>(stored(a + b), ea + eb), "add " + ab);
        t.check("sub", same<L>(stored(a - b), ea - eb), "sub " + ab);
        t.check("mul", same<L>(stored(a * b), ea * eb), "mul " + ab);
        t.check("fma", same<L>(stored(std::fma(a, b, c)), kairn::emulated::fma_rn(ea, eb, ec)), "fma " + abc);
        t.check("fms", same<L>(stored(std::fma(a, b, -c)), kairn::emulated::fma_rn(ea, eb, -ec)), "fms " + abc);
        t.check("fnma", same<L>(stored(std::fma(-a, b, c)), kairn::emulated::fma_rn(-ea, eb, ec)), "fnma " + abc);
        t.check("prod", same<L>(stored(std::fma(a, b, T(0))), kairn::emulated::fma_rn(ea, eb, Number())), "prod " + ab);
        t.check("guard", same<L>(stored(a + T(0)), ea + Number()), "guard " + text<L>(a));
        t.check("neg", same<L>(stored(-a), -ea), "neg " + text<L>(a));
        t.check("abs", same<L>(std::bit_cast<T>(L::bits(a) & ~(U{1} << (L::precision - 1 + L::exponent_bits))),
                               kairn::emulated::abs_bits(ea)), "abs " + text<L>(a));
        t.check("next_up", same<L>(std::nextafter(a, inf), kairn::emulated::next_up_bits(ea)), "next_up " + text<L>(a));
        t.check("next_down", same<L>(std::nextafter(a, -inf), kairn::emulated::next_down_bits(ea)),
                "next_down " + text<L>(a));
        t.check("times_inf", same<L>(stored(a * inf), ea * std::numeric_limits<Number>::infinity()),
                "times_inf " + text<L>(a));
        t.check("times_inf_ce", same<L>(a > 0 ? inf : 0 > a ? -inf : std::numeric_limits<T>::quiet_NaN(),
                                        kairn::emulated::times_inf_ce(ea)), "times_inf_ce " + text<L>(a));
        t.check("lt", (a < b) == (ea < eb), "lt " + ab);
        t.check("le", (a <= b) == (ea <= eb), "le " + ab);
        t.check("gt", (a > b) == (ea > eb), "gt " + ab);
        t.check("ge", (a >= b) == (ea >= eb), "ge " + ab);
        t.check("eq", (a == b) == (ea == eb), "eq " + ab);
        t.check("ne", (a != b) == (ea != eb), "ne " + ab);
        // The text of a limb: read back as itself, and for float the text printf writes for the
        // same double (a float is never subnormal as a double).
        Number back;
        const std::string ta = kairn::emulated::to_text(ea);
        t.check("text", kairn::emulated::parse(ta, back) && (ea.is_nan() ? back.is_nan() : L::from_number(back) == L::bits(a)),
                "text " + ta);
        if (L::precision == 24 && !std::isnan(a)) {
            char buf[64];
            if (std::isinf(a)) std::snprintf(buf, sizeof buf, "%s", a > 0 ? "inf" : "-inf");
            else std::snprintf(buf, sizeof buf, "%a", double(a));
            t.check("printf", ta == buf, "printf " + ta + " against " + buf);
        }
        // A count to T and a value of T to a count.
        const std::uint64_t n = r.below(4) == 0 ? r.next() : r.next() >> r.below(64);
        t.check("from_size", same<L>(stored(static_cast<T>(std::size_t(n))), Number(std::size_t(n))),
                "from_size " + std::to_string(n));
        const T x = std::fabs(a);
        if (std::isfinite(x) && x < T(18446744073709551616.0))
            t.check("to_size", static_cast<std::size_t>(x) == static_cast<std::size_t>(L::to_number(x)),
                    "to_size " + text<L>(x));
        const int k = int(r.below(std::uint64_t(L::qmax - L::qmin + 2 * L::precision + 8))) + L::qmin - 4;
        t.check("pow2", same<L>(stored(std::ldexp(T(1), k)), kairn::emulated::pow2(k)), "pow2 " + std::to_string(k));
    }
    long failures = 0, cases = 0;
    for (auto& [op, n] : t.cases) {
        cases += n;
        failures += t.failures[op];
        std::printf("%-13s %10ld cases %8ld different\n", op.c_str(), n, t.failures[op]);
    }
    std::printf("strata of the first operand (any bits, finite, subnormal, lowest normal binades, top binades, "
                "special):");
    for (auto& [s, n] : strata) std::printf(" %ld", n);
    std::printf("\nselftest %s: %ld cases, %ld different\n", L::precision == 24 ? "binary32" : "binary64", cases,
                failures);
    return failures ? 1 : 0;
}

int ops(const std::string& name) {
    kairn::emulated::Format f;
    if (std::sscanf(name.c_str(), "fp:%d:%d:%d", &f.p, &f.qmin, &f.qmax) != 3) {
        std::fprintf(stderr, "selftest: not a format: %s\n", name.c_str());
        return 2;
    }
    std::string why;
    if (!kairn::emulated::set_format(f, &why)) {
        std::fprintf(stderr, "selftest: %s\n", why.c_str());
        return 2;
    }
    std::string line, out;
    std::vector<std::string> w;
    long lineno = 0;
    while (std::getline(std::cin, line)) {
        ++lineno;
        w.clear();
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            w.push_back(line.substr(start, space - start));
            if (space == std::string::npos) break;
            start = space + 1;
        }
        const std::string& op = w[0];
        Number x[3];
        if (op != "from_size" && op != "pow2")
            for (std::size_t i = 1; i < w.size() && i < 4; ++i)
                if (!kairn::emulated::parse(w[i], x[i - 1], &why)) {
                    std::fprintf(stderr, "selftest: line %ld: %s\n", lineno, why.c_str());
                    return 2;
                }
        const auto limb = [&](Number v) { out += kairn::emulated::to_text(v); };
        const auto mask = [&](bool m) { out += m ? '1' : '0'; };
        if (op == "add") limb(x[0] + x[1]);
        else if (op == "sub") limb(x[0] - x[1]);
        else if (op == "mul") limb(x[0] * x[1]);
        else if (op == "fma") limb(kairn::emulated::fma_rn(x[0], x[1], x[2]));
        else if (op == "fms") limb(kairn::emulated::fma_rn(x[0], x[1], -x[2]));
        else if (op == "fnma") limb(kairn::emulated::fma_rn(-x[0], x[1], x[2]));
        else if (op == "prod") limb(kairn::emulated::fma_rn(x[0], x[1], Number()));
        else if (op == "neg") limb(-x[0]);
        else if (op == "abs") limb(kairn::emulated::abs_bits(x[0]));
        else if (op == "next_up") limb(kairn::emulated::next_up_bits(x[0]));
        else if (op == "next_down") limb(kairn::emulated::next_down_bits(x[0]));
        else if (op == "times_inf") limb(x[0] * std::numeric_limits<Number>::infinity());
        else if (op == "times_inf_ce") limb(kairn::emulated::times_inf_ce(x[0]));
        else if (op == "lt") mask(x[0] < x[1]);
        else if (op == "le") mask(x[0] <= x[1]);
        else if (op == "gt") mask(x[0] > x[1]);
        else if (op == "ge") mask(x[0] >= x[1]);
        else if (op == "eq") mask(x[0] == x[1]);
        else if (op == "ne") mask(x[0] != x[1]);
        else if (op == "to_size") out += std::to_string(static_cast<std::size_t>(x[0]));
        else if (op == "from_size") limb(Number(std::size_t(std::stoull(w[1]))));
        else if (op == "pow2") limb(kairn::emulated::pow2(std::stoi(w[1])));
        else {
            std::fprintf(stderr, "selftest: line %ld: unknown operation %s\n", lineno, op.c_str());
            return 2;
        }
        out += '\n';
        if (out.size() > (1u << 16)) {
            std::fwrite(out.data(), 1, out.size(), stdout);
            out.clear();
        }
    }
    std::fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}

[[noreturn]] void usage() {
    std::fprintf(stderr, "usage: selftest --hardware binary32|binary64 --count N [--seed S] [--fault NAME]\n"
                         "       selftest --ops FORMAT [--fault NAME]\n");
    std::exit(2);
}

}  // namespace

int main(int argc, char** argv) {
    std::ios::sync_with_stdio(false);
    std::string hw, fmt;
    long count = 0;
    std::uint64_t seed = 0;
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (i + 1 >= argc) usage();
        const std::string v = argv[++i];
        if (a == "--hardware") hw = v;
        else if (a == "--count") count = std::stol(v);
        else if (a == "--seed") seed = std::stoull(v);
        else if (a == "--ops") fmt = v;
        else if (a == "--fault") {
            if (!kairn::emulated::plant_fault(v)) usage();
        } else usage();
    }
    if (!fmt.empty()) return ops(fmt);
    if (hw == "binary32") return hardware<L32>(count, seed);
    if (hw == "binary64") return hardware<L64>(count, seed);
    usage();
}
