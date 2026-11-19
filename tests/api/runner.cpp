// A runner of the line protocol (docs/developer/architecture.md, "The line protocol") that computes
// every result through Kairn's public interface, so that the oracle judges what a client calls:
// the operators and functions of Expansion and Ball, not the generated kernels.
//
//   runner [--form NAME]      request lines on standard input, completed lines on standard output
//   runner --forms KERNEL     the forms that must satisfy KERNEL's claims, one per line
//   runner --list             every kernel that some form maps to
//   runner --internal         the kernels no public operation computes on its own
//
// Each public operation is mapped to the kernel whose claims it must satisfy; a kernel can have
// several forms (x + a and a + x, x += y, the marked and the unmarked operator). A form uses the
// operator without kairn::unverified when gen/claims.json says the kernel is proved, as a client
// would, and with the marker otherwise, so that the runner follows the proofs as they land.
// binary64 requests run on double limbs, binary32 requests on float limbs; a mask is 0 or 1.
#include <kairn/kairn.hpp>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

template <class T>
using E1 = kairn::Expansion<T, 1>;
template <class T>
using E2 = kairn::Expansion<T, 2>;
template <class T>
using B1 = kairn::Ball<T, 1>;
template <class T>
using B2 = kairn::Ball<T, 2>;
namespace bounds = kairn::gen::bounds;
using kairn::unverified;

// Operands, from the limbs of a request.
template <class T>
E1<T> one(const T* in) {
    return E1<T>(in[0]);
}
template <class T>
E2<T> two(const T* in) {
    return E2<T>::from_limbs(in);
}
template <class T>
B1<T> ball1(const T* in) {
    return B1<T>(one(in), in[1]);
}
template <class T>
B2<T> ball2(const T* in) {
    return B2<T>(two(in), in[2]);
}
// Results, into the limbs of the completed line.
template <class T>
void put(T* out, const E1<T>& z) {
    out[0] = z.limb[0];
}
template <class T>
void put(T* out, const E2<T>& z) {
    out[0] = z.limb[0];
    out[1] = z.limb[1];
}
template <class T, int K>
void put(T* out, const kairn::Ball<T, K>& z) {
    put(out, z.center());
    out[K] = z.radius();
}

// One form: a function template, instantiated for double and float in the table below.
#define FORM(NAME, ...)                                                                    \
    template <class T>                                                                     \
    void NAME([[maybe_unused]] const T* in, [[maybe_unused]] T* out, [[maybe_unused]] bool* mo) { \
        __VA_ARGS__;                                                                       \
    }
// The operator as a client writes it: unmarked if the kernel is proved, marked otherwise.
#define PROVED(KERNEL) bounds::KERNEL<T>::proved

// One limb. -b and E1(-b) are exact, so x - (-b) asks for the rounded sum the claims of add_1_1
// are about.
FORM(add_1_1_plus, if constexpr (PROVED(add_1_1)) put(out, one(in) + one(in + 1)); else put(out, unverified(one(in)) + one(in + 1)))
FORM(add_1_1_plus_limb, if constexpr (PROVED(add_1_1)) put(out, one(in) + in[1]); else put(out, unverified(one(in)) + in[1]))
FORM(add_1_1_limb_plus, if constexpr (PROVED(add_1_1)) put(out, in[0] + one(in + 1)); else put(out, in[0] + unverified(one(in + 1))))
FORM(add_1_1_plus_assign, E1<T> x = one(in); if constexpr (PROVED(add_1_1)) x += one(in + 1); else x += unverified(one(in + 1)); put(out, x))
FORM(add_1_1_minus, if constexpr (PROVED(add_1_1)) put(out, one(in) - E1<T>(-in[1])); else put(out, unverified(one(in)) - E1<T>(-in[1])))
FORM(add_1_1_minus_assign, E1<T> x = one(in); if constexpr (PROVED(add_1_1)) x -= E1<T>(-in[1]); else x -= unverified(E1<T>(-in[1])); put(out, x))
FORM(add_1_1_add_fast, if constexpr (PROVED(add_1_1)) put(out, kairn::add_fast(one(in), one(in + 1))); else put(out, kairn::add_fast(unverified(one(in)), one(in + 1))))
FORM(add_1_1_marked, put(out, unverified(one(in)) + unverified(one(in + 1))))
FORM(mul_1_1_times, if constexpr (PROVED(mul_1_1)) put(out, one(in) * one(in + 1)); else put(out, unverified(one(in)) * one(in + 1)))
FORM(mul_1_1_times_limb, if constexpr (PROVED(mul_1_1)) put(out, one(in) * in[1]); else put(out, unverified(one(in)) * in[1]))
FORM(mul_1_1_limb_times, if constexpr (PROVED(mul_1_1)) put(out, in[0] * one(in + 1)); else put(out, in[0] * unverified(one(in + 1))))
FORM(mul_1_1_times_assign, E1<T> x = one(in); if constexpr (PROVED(mul_1_1)) x *= one(in + 1); else x *= unverified(one(in + 1)); put(out, x))
FORM(mul_1_1_marked, put(out, unverified(one(in)) * unverified(one(in + 1))))

// Two limbs: arithmetic.
FORM(add_2_2_plus, if constexpr (PROVED(add_2_2)) put(out, two(in) + two(in + 2)); else put(out, unverified(two(in)) + two(in + 2)))
FORM(add_2_2_plus_assign, E2<T> x = two(in); if constexpr (PROVED(add_2_2)) x += two(in + 2); else x += unverified(two(in + 2)); put(out, x))
FORM(add_2_2_marked, put(out, two(in) + unverified(two(in + 2))))
FORM(add_2_1_plus, if constexpr (PROVED(add_2_1)) put(out, two(in) + in[2]); else put(out, unverified(two(in)) + in[2]))
FORM(add_2_1_limb_plus, if constexpr (PROVED(add_2_1)) put(out, in[2] + two(in)); else put(out, in[2] + unverified(two(in))))
FORM(add_2_1_plus_assign, E2<T> x = two(in); if constexpr (PROVED(add_2_1)) x += in[2]; else x += unverified(in[2]); put(out, x))
FORM(add_2_1_marked, put(out, two(in) + unverified(in[2])))
FORM(sub_2_2_minus, if constexpr (PROVED(sub_2_2)) put(out, two(in) - two(in + 2)); else put(out, unverified(two(in)) - two(in + 2)))
FORM(sub_2_2_minus_assign, E2<T> x = two(in); if constexpr (PROVED(sub_2_2)) x -= two(in + 2); else x -= unverified(two(in + 2)); put(out, x))
FORM(sub_2_2_marked, put(out, two(in) - unverified(two(in + 2))))
FORM(sub_2_1_minus, if constexpr (PROVED(sub_2_1)) put(out, two(in) - in[2]); else put(out, unverified(two(in)) - in[2]))
FORM(sub_2_1_minus_assign, E2<T> x = two(in); if constexpr (PROVED(sub_2_1)) x -= in[2]; else x -= unverified(in[2]); put(out, x))
FORM(sub_2_1_marked, put(out, two(in) - unverified(in[2])))
FORM(sub_1_2_minus, if constexpr (PROVED(sub_1_2)) put(out, in[0] - two(in + 1)); else put(out, in[0] - unverified(two(in + 1))))
FORM(sub_1_2_marked, put(out, unverified(in[0]) - two(in + 1)))
FORM(mul_2_2_times, if constexpr (PROVED(mul_2_2)) put(out, two(in) * two(in + 2)); else put(out, unverified(two(in)) * two(in + 2)))
FORM(mul_2_2_times_assign, E2<T> x = two(in); if constexpr (PROVED(mul_2_2)) x *= two(in + 2); else x *= unverified(two(in + 2)); put(out, x))
FORM(mul_2_2_marked, put(out, two(in) * unverified(two(in + 2))))
FORM(mul_2_1_times, if constexpr (PROVED(mul_2_1)) put(out, two(in) * in[2]); else put(out, unverified(two(in)) * in[2]))
FORM(mul_2_1_limb_times, if constexpr (PROVED(mul_2_1)) put(out, in[2] * two(in)); else put(out, in[2] * unverified(two(in))))
FORM(mul_2_1_times_assign, E2<T> x = two(in); if constexpr (PROVED(mul_2_1)) x *= in[2]; else x *= unverified(in[2]); put(out, x))
FORM(mul_2_1_marked, put(out, unverified(two(in)) * in[2]))
FORM(neg_2_negate, if constexpr (PROVED(neg_2)) put(out, -two(in)); else put(out, -unverified(two(in))))
FORM(abs_2_abs, if constexpr (PROVED(abs_2)) put(out, kairn::abs(two(in))); else put(out, kairn::abs(unverified(two(in)))))
FORM(add_fast_2_2_add_fast, if constexpr (PROVED(add_fast_2_2)) put(out, kairn::add_fast(two(in), two(in + 2))); else put(out, kairn::add_fast(unverified(two(in)), two(in + 2))))
// c is a positive power of two, 2^n with n = ilogb(c) (subnormal powers included).
FORM(mul_pow2_2_ldexp, const int n = std::ilogb(in[2]); if constexpr (PROVED(mul_pow2_2)) put(out, kairn::ldexp(two(in), n)); else put(out, kairn::ldexp(unverified(two(in)), n)))

// Two limbs: comparisons. The reversed forms ask the same question with the operands swapped.
FORM(lt_2_2_less, if constexpr (PROVED(lt_2_2)) mo[0] = two(in) < two(in + 2); else mo[0] = unverified(two(in)) < two(in + 2))
FORM(lt_2_2_greater, if constexpr (PROVED(lt_2_2)) mo[0] = two(in + 2) > two(in); else mo[0] = two(in + 2) > unverified(two(in)))
FORM(le_2_2_less_equal, if constexpr (PROVED(le_2_2)) mo[0] = two(in) <= two(in + 2); else mo[0] = unverified(two(in)) <= two(in + 2))
FORM(le_2_2_greater_equal, if constexpr (PROVED(le_2_2)) mo[0] = two(in + 2) >= two(in); else mo[0] = two(in + 2) >= unverified(two(in)))
FORM(eq_2_2_equal, if constexpr (PROVED(eq_2_2)) mo[0] = two(in) == two(in + 2); else mo[0] = unverified(two(in)) == two(in + 2))
FORM(eq_2_2_not_unequal, if constexpr (PROVED(eq_2_2)) mo[0] = !(two(in) != two(in + 2)); else mo[0] = !(two(in) != unverified(two(in + 2))))
FORM(lt_2_1_less, if constexpr (PROVED(lt_2_1)) mo[0] = two(in) < in[2]; else mo[0] = unverified(two(in)) < in[2])
FORM(lt_2_1_greater, if constexpr (PROVED(lt_2_1)) mo[0] = in[2] > two(in); else mo[0] = unverified(in[2]) > two(in))
FORM(le_2_1_less_equal, if constexpr (PROVED(le_2_1)) mo[0] = two(in) <= in[2]; else mo[0] = unverified(two(in)) <= in[2])
FORM(le_2_1_greater_equal, if constexpr (PROVED(le_2_1)) mo[0] = in[2] >= two(in); else mo[0] = in[2] >= unverified(two(in)))
FORM(eq_2_1_equal, if constexpr (PROVED(eq_2_1)) mo[0] = two(in) == in[2]; else mo[0] = unverified(two(in)) == in[2])
FORM(eq_2_1_equal_rev, if constexpr (PROVED(eq_2_1)) mo[0] = in[2] == two(in); else mo[0] = in[2] == unverified(two(in)))
FORM(eq_2_1_not_unequal, if constexpr (PROVED(eq_2_1)) mo[0] = !(two(in) != in[2]); else mo[0] = !(two(in) != unverified(in[2])))
FORM(eq_2_1_not_unequal_rev, if constexpr (PROVED(eq_2_1)) mo[0] = !(in[2] != two(in)); else mo[0] = !(unverified(in[2]) != two(in)))
FORM(lt_1_2_less, if constexpr (PROVED(lt_1_2)) mo[0] = in[0] < two(in + 1); else mo[0] = in[0] < unverified(two(in + 1)))
FORM(lt_1_2_greater, if constexpr (PROVED(lt_1_2)) mo[0] = two(in + 1) > in[0]; else mo[0] = unverified(two(in + 1)) > in[0])
FORM(le_1_2_less_equal, if constexpr (PROVED(le_1_2)) mo[0] = in[0] <= two(in + 1); else mo[0] = in[0] <= unverified(two(in + 1)))
FORM(le_1_2_greater_equal, if constexpr (PROVED(le_1_2)) mo[0] = two(in + 1) >= in[0]; else mo[0] = unverified(two(in + 1)) >= in[0])

// Two limbs: conversions to T. Narrowing an Expansion<T, 2> keeps its leading limb, which is the
// claim of to_nearest_2.
FORM(to_nearest_2_to_nearest, if constexpr (PROVED(to_nearest_2)) out[0] = kairn::to_nearest(two(in)); else out[0] = kairn::to_nearest(unverified(two(in))))
FORM(to_nearest_2_narrow, out[0] = E1<T>(two(in)).limb[0])
FORM(to_down_2_to_down, if constexpr (PROVED(to_down_2)) out[0] = kairn::to_down(two(in)); else out[0] = kairn::to_down(unverified(two(in))))
FORM(to_up_2_to_up, if constexpr (PROVED(to_up_2)) out[0] = kairn::to_up(two(in)); else out[0] = kairn::to_up(unverified(two(in))))
FORM(abs_upper_2_abs_upper, if constexpr (PROVED(abs_upper_2)) out[0] = kairn::abs_upper(two(in)); else out[0] = kairn::abs_upper(unverified(two(in))))

// Balls. Operands are (center limbs, radius); a scaling's third operand is the exact T.
#define BALL_FORMS(K, BALL)                                                                                                    \
    FORM(ball_add_##K##_plus, if constexpr (PROVED(ball_add_##K)) put(out, BALL(in) + BALL(in + K + 1)); else put(out, unverified(BALL(in)) + BALL(in + K + 1))) \
    FORM(ball_add_##K##_plus_assign, auto x = BALL(in); if constexpr (PROVED(ball_add_##K)) x += BALL(in + K + 1); else x += unverified(BALL(in + K + 1)); put(out, x)) \
    FORM(ball_sub_##K##_minus, if constexpr (PROVED(ball_sub_##K)) put(out, BALL(in) - BALL(in + K + 1)); else put(out, unverified(BALL(in)) - BALL(in + K + 1))) \
    FORM(ball_sub_##K##_minus_assign, auto x = BALL(in); if constexpr (PROVED(ball_sub_##K)) x -= BALL(in + K + 1); else x -= unverified(BALL(in + K + 1)); put(out, x)) \
    FORM(ball_mul_##K##_times, if constexpr (PROVED(ball_mul_##K)) put(out, BALL(in) * BALL(in + K + 1)); else put(out, unverified(BALL(in)) * BALL(in + K + 1))) \
    FORM(ball_mul_##K##_times_assign, auto x = BALL(in); if constexpr (PROVED(ball_mul_##K)) x *= BALL(in + K + 1); else x *= unverified(BALL(in + K + 1)); put(out, x)) \
    FORM(ball_scale_##K##_scale, if constexpr (PROVED(ball_scale_##K)) put(out, BALL(in) * in[K + 1]); else put(out, unverified(BALL(in)) * in[K + 1])) \
    FORM(ball_scale_##K##_scale_rev, if constexpr (PROVED(ball_scale_##K)) put(out, in[K + 1] * BALL(in)); else put(out, in[K + 1] * unverified(BALL(in)))) \
    FORM(ball_scale_##K##_scale_assign, auto x = BALL(in); if constexpr (PROVED(ball_scale_##K)) x *= in[K + 1]; else x *= unverified(in[K + 1]); put(out, x)) \
    FORM(ball_neg_##K##_negate, if constexpr (PROVED(ball_neg_##K)) put(out, -BALL(in)); else put(out, -unverified(BALL(in))))
BALL_FORMS(1, ball1)
BALL_FORMS(2, ball2)

struct Form {
    const char* kernel;
    const char* name;
    const char* in_kinds;   // one letter per input value: l a limb, m a mask
    const char* out_kinds;
    void (*binary64)(const double*, double*, bool*);
    void (*binary32)(const float*, float*, bool*);
};

#define ROW(KERNEL, NAME, IN, OUT) {#KERNEL, #NAME, IN, OUT, KERNEL##_##NAME<double>, KERNEL##_##NAME<float>},
#define BALL_ROWS(K, IN, OUT, IN_SCALE, IN_NEG)            \
    ROW(ball_add_##K, plus, IN, OUT)                     \
    ROW(ball_add_##K, plus_assign, IN, OUT)              \
    ROW(ball_sub_##K, minus, IN, OUT)                    \
    ROW(ball_sub_##K, minus_assign, IN, OUT)             \
    ROW(ball_mul_##K, times, IN, OUT)                    \
    ROW(ball_mul_##K, times_assign, IN, OUT)             \
    ROW(ball_scale_##K, scale, IN_SCALE, OUT)            \
    ROW(ball_scale_##K, scale_rev, IN_SCALE, OUT)        \
    ROW(ball_scale_##K, scale_assign, IN_SCALE, OUT)     \
    ROW(ball_neg_##K, negate, IN_NEG, OUT)

// The first form of each kernel is its canonical one.
const Form forms[] = {
    ROW(add_1_1, plus, "ll", "l")
    ROW(add_1_1, plus_limb, "ll", "l")
    ROW(add_1_1, limb_plus, "ll", "l")
    ROW(add_1_1, plus_assign, "ll", "l")
    ROW(add_1_1, minus, "ll", "l")
    ROW(add_1_1, minus_assign, "ll", "l")
    ROW(add_1_1, add_fast, "ll", "l")
    ROW(add_1_1, marked, "ll", "l")
    ROW(mul_1_1, times, "ll", "l")
    ROW(mul_1_1, times_limb, "ll", "l")
    ROW(mul_1_1, limb_times, "ll", "l")
    ROW(mul_1_1, times_assign, "ll", "l")
    ROW(mul_1_1, marked, "ll", "l")
    ROW(add_2_2, plus, "llll", "ll")
    ROW(add_2_2, plus_assign, "llll", "ll")
    ROW(add_2_2, marked, "llll", "ll")
    ROW(add_2_1, plus, "lll", "ll")
    ROW(add_2_1, limb_plus, "lll", "ll")
    ROW(add_2_1, plus_assign, "lll", "ll")
    ROW(add_2_1, marked, "lll", "ll")
    ROW(sub_2_2, minus, "llll", "ll")
    ROW(sub_2_2, minus_assign, "llll", "ll")
    ROW(sub_2_2, marked, "llll", "ll")
    ROW(sub_2_1, minus, "lll", "ll")
    ROW(sub_2_1, minus_assign, "lll", "ll")
    ROW(sub_2_1, marked, "lll", "ll")
    ROW(sub_1_2, minus, "lll", "ll")
    ROW(sub_1_2, marked, "lll", "ll")
    ROW(mul_2_2, times, "llll", "ll")
    ROW(mul_2_2, times_assign, "llll", "ll")
    ROW(mul_2_2, marked, "llll", "ll")
    ROW(mul_2_1, times, "lll", "ll")
    ROW(mul_2_1, limb_times, "lll", "ll")
    ROW(mul_2_1, times_assign, "lll", "ll")
    ROW(mul_2_1, marked, "lll", "ll")
    ROW(neg_2, negate, "ll", "ll")
    ROW(abs_2, abs, "ll", "ll")
    ROW(add_fast_2_2, add_fast, "llll", "ll")
    ROW(mul_pow2_2, ldexp, "lll", "ll")
    ROW(lt_2_2, less, "llll", "m")
    ROW(lt_2_2, greater, "llll", "m")
    ROW(le_2_2, less_equal, "llll", "m")
    ROW(le_2_2, greater_equal, "llll", "m")
    ROW(eq_2_2, equal, "llll", "m")
    ROW(eq_2_2, not_unequal, "llll", "m")
    ROW(lt_2_1, less, "lll", "m")
    ROW(lt_2_1, greater, "lll", "m")
    ROW(le_2_1, less_equal, "lll", "m")
    ROW(le_2_1, greater_equal, "lll", "m")
    ROW(eq_2_1, equal, "lll", "m")
    ROW(eq_2_1, equal_rev, "lll", "m")
    ROW(eq_2_1, not_unequal, "lll", "m")
    ROW(eq_2_1, not_unequal_rev, "lll", "m")
    ROW(lt_1_2, less, "lll", "m")
    ROW(lt_1_2, greater, "lll", "m")
    ROW(le_1_2, less_equal, "lll", "m")
    ROW(le_1_2, greater_equal, "lll", "m")
    ROW(to_nearest_2, to_nearest, "ll", "l")
    ROW(to_nearest_2, narrow, "ll", "l")
    ROW(to_down_2, to_down, "ll", "l")
    ROW(to_up_2, to_up, "ll", "l")
    ROW(abs_upper_2, abs_upper, "ll", "l")
    BALL_ROWS(1, "llll", "ll", "lll", "ll")
    BALL_ROWS(2, "llllll", "lll", "llll", "lll")
};

// Kernels that no public operation computes on its own, and why. Every kernel of gen/claims.json
// is either mapped above or listed here (tests/api/CMakeLists.txt checks it).
const char* const internal[] = {
    "two_sum", "fast_two_sum", "two_prod",        // building blocks of the kernels above
    "split", "two_prod_dekker",                   // the constant-evaluation variant of two_prod
    "radd", "rmul",                               // radius arithmetic inside the Ball kernels
};

constexpr int max_limbs = 16;
long lineno = 0;

[[noreturn]] void fail(const std::string& why) {
    std::fflush(stdout);
    std::fprintf(stderr, "runner: line %ld: %s\n", lineno, why.c_str());
    std::exit(2);
}

// A limb is a C99 hexadecimal literal, inf, -inf or nan; strtod alone would also take decimals.
double parse(const std::string& text) {
    if (text == "inf") return std::numeric_limits<double>::infinity();
    if (text == "-inf") return -std::numeric_limits<double>::infinity();
    if (text == "nan") return std::numeric_limits<double>::quiet_NaN();
    const std::size_t x = text.find_first_of("xX");
    if (x == std::string::npos || x == 0 || text[x - 1] != '0' || text.find_first_of("pP") == std::string::npos)
        fail("not a limb: " + text);
    char* end = nullptr;
    const double v = std::strtod(text.c_str(), &end);
    if (*end != '\0') fail("not a limb: " + text);
    return v;
}

void put_limb(double v, std::string& out) {
    if (v != v) {
        out += "nan";
    } else if (v == std::numeric_limits<double>::infinity()) {
        out += "inf";
    } else if (v == -std::numeric_limits<double>::infinity()) {
        out += "-inf";
    } else {
        char buf[64];
        std::snprintf(buf, sizeof buf, "%a", v);
        out += buf;
    }
}

int usage() {
    std::fprintf(stderr, "usage: runner [--form NAME] | --forms KERNEL | --list | --internal\n");
    return 2;
}

}  // namespace

int main(int argc, char** argv) {
    const char* form_name = nullptr;
    if (argc == 3 && std::strcmp(argv[1], "--forms") == 0) {
        for (const Form& f : forms)
            if (std::strcmp(f.kernel, argv[2]) == 0) std::printf("%s\n", f.name);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--list") == 0) {
        const char* last = "";
        for (const Form& f : forms)
            if (std::strcmp(f.kernel, last) != 0) std::printf("%s\n", last = f.kernel);
        return 0;
    }
    if (argc == 2 && std::strcmp(argv[1], "--internal") == 0) {
        for (const char* k : internal) std::printf("%s\n", k);
        return 0;
    }
    if (argc == 3 && std::strcmp(argv[1], "--form") == 0) {
        form_name = argv[2];
    } else if (argc != 1) {
        return usage();
    }

    std::ios::sync_with_stdio(false);
    std::string line, out;
    std::vector<std::string> fields;
    while (std::getline(std::cin, line)) {
        ++lineno;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        out = line;
        if (line.empty() || line[0] == '#') {
            out += '\n';
            std::fwrite(out.data(), 1, out.size(), stdout);
            continue;
        }
        fields.clear();
        for (std::size_t start = 0;;) {
            const std::size_t space = line.find(' ', start);
            fields.push_back(line.substr(start, space - start));
            if (fields.back().empty()) fail("fields are separated by single spaces");
            if (space == std::string::npos) break;
            start = space + 1;
        }
        if (fields.back()[0] == '#') fields.pop_back();  // the tag
        if (fields.size() < 2) fail("expected KERNEL FORMAT LIMB ... [#TAG]");
        const Form* k = nullptr;
        for (const Form& f : forms) {
            if (fields[0] != f.kernel) continue;
            if (form_name ? std::strcmp(form_name, f.name) == 0 : k == nullptr) k = &f;
        }
        if (!k) fail("no public operation maps to " + fields[0] + (form_name ? std::string(" as form ") + form_name : ""));
        const int inputs = int(std::strlen(k->in_kinds)), outputs = int(std::strlen(k->out_kinds));
        if (int(fields.size()) - 2 != inputs) fail(fields[0] + " takes " + std::to_string(inputs) + " limbs");
        bool mo[max_limbs] = {};
        out += " ->";
        if (fields[1] == "binary64") {
            double in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) in[i] = parse(fields[2 + i]);
            k->binary64(in, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(res[i], out);
            }
        } else if (fields[1] == "binary32") {
            float in[max_limbs] = {}, res[max_limbs] = {};
            for (int i = 0; i < inputs; ++i) {
                const double v = parse(fields[2 + i]);
                const double top = std::numeric_limits<float>::max();
                if (v == v && v - v == 0 && (v > top || v < -top)) fail(fields[2 + i] + " is not a binary32 number");
                in[i] = static_cast<float>(v);
                if (static_cast<double>(in[i]) != v && v == v) fail(fields[2 + i] + " is not a binary32 number");
            }
            k->binary32(in, res, mo);
            for (int i = 0; i < outputs; ++i) {
                out += ' ';
                if (k->out_kinds[i] == 'm') out += mo[i] ? '1' : '0';
                else put_limb(static_cast<double>(res[i]), out);
            }
        } else {
            fail("this runner knows binary64 and binary32, not " + fields[1]);
        }
        out += '\n';
        std::fwrite(out.data(), 1, out.size(), stdout);
    }
    return 0;
}
