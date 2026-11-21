// The emulated limb type of the exhaustive tier (docs/developer/testing.md, "The emulated
// formats"): a floating-point number of a binary format chosen at run time, computed with integers
// only. Test code: nothing under include/ uses it.
//
// It is written from the definition of a format (docs/developer/architecture.md, "Number formats"):
// the numbers of (p, qmin, qmax) are m 2^q with integers |m| < 2^p and qmin <= q <= qmax; every
// operation is computed exactly and rounded once, to nearest with ties to even, with gradual
// underflow, to an infinity when the rounding in an unbounded exponent range exceeds the largest
// number; signed zeros, infinities and NaN follow IEEE 754. It shares no code with the oracle or
// with the generator's interpreter, which implement the same definition in Python: this is a third
// implementation, held to the machine's float and double (p = 24 and 53 in their exponent ranges)
// and to the oracle's exact rounding by its tests (tests/emulated/selftest.cpp,
// tests/emulated/test_emulated.py).
//
// The generated kernels for this type (tests/emulated/gen/kernels.hpp, written by
// python3 gen/kairn-gen build through the printer of include/kairn/gen/scalar.hpp) use exactly the
// operations declared here: + - * and the comparisons, fma_rn, abs_bits, next_up_bits,
// next_down_bits, times_inf_ce, the constants of the format (constant), the test of constant
// evaluation (constant_evaluation: a mode of the runner here, since nothing of this type is
// evaluated at compile time), the conversions of a count (a std::size_t), and copies through a
// volatile object (the ends of the ball vectors).
#pragma once

#include <cstddef>
#include <cstdint>
#include <limits>
#include <string>

namespace kairn::emulated {

// A binary format: precision p >= 1, and the exponents qmin <= qmax of the last place.
struct Format {
    int p = 0;
    int qmin = 0;
    int qmax = 0;
};

// The largest precision held: a significand is a std::uint64_t and the product of two is computed
// exactly in two words.
inline constexpr int max_precision = 62;

// The format of every Number. It is a property of the program, as the format of double is, set
// before any arithmetic and changed only between computations (the runner sets it from each
// request's FORMAT). set_format refuses a format the arithmetic cannot hold (p out of 1 ..
// max_precision, qmin > qmax, or an exponent range too wide for its exact intermediate results)
// and says why.
bool set_format(const Format& f, std::string* why = nullptr);
const Format& format() noexcept;

class Number {
public:
    enum class Kind : unsigned char { finite, infinite, nan };

    // +0.
    constexpr Number() noexcept = default;
    // A count rounded to nearest in the format (the product of two BallVectors converts its number
    // of terms so).
    explicit Number(std::size_t n) noexcept;
    Number(const Number&) = default;
    Number& operator=(const Number&) = default;
    // Copies through a volatile object (the generated ends of the ball vectors).
    Number(const volatile Number& o) noexcept : kind_(o.kind_), neg_(o.neg_), m_(o.m_), q_(o.q_) {}
    volatile Number& operator=(const Number& o) volatile noexcept {
        kind_ = o.kind_;
        neg_ = o.neg_;
        m_ = o.m_;
        q_ = o.q_;
        return *this;
    }
    // The integer part of a finite value in [0, 2^64), and 0 for any other (C++ leaves the
    // conversion of such a double undefined; the generated code converts only counts below 2^64).
    explicit operator std::size_t() const noexcept;

    static constexpr Number infinity(bool negative) noexcept { return Number(Kind::infinite, negative, 0, 0); }
    static constexpr Number nan() noexcept { return Number(Kind::nan, false, 0, 0); }
    // (-1)^negative m 2^q, which must be a number of the format: returns false, and leaves out
    // unchanged, when it is not. Any representation is accepted (m need not be in [2^(p-1), 2^p)).
    static bool make(bool negative, std::uint64_t m, int q, Number& out) noexcept;

    Kind kind() const noexcept { return kind_; }
    bool negative() const noexcept { return neg_; }
    bool is_finite() const noexcept { return kind_ == Kind::finite; }
    bool is_nan() const noexcept { return kind_ == Kind::nan; }
    bool is_zero() const noexcept { return kind_ == Kind::finite && m_ == 0; }
    // A finite value as m 2^q with m in [2^(p-1), 2^p), or q = qmin and m below 2^(p-1) (the
    // subnormal numbers; zero is m = 0).
    std::uint64_t significand() const noexcept { return m_; }
    int exponent() const noexcept { return q_; }

private:
    constexpr Number(Kind k, bool negative, std::uint64_t m, int q) noexcept : kind_(k), neg_(negative), m_(m), q_(q) {}
    friend struct Access;

    Kind kind_ = Kind::finite;
    bool neg_ = false;
    std::uint64_t m_ = 0;
    int q_ = 0;
};

// The operations of a limb in the generated code, each one rounding of the exact result.
Number operator+(Number a, Number b) noexcept;
Number operator-(Number a, Number b) noexcept;
Number operator-(Number a) noexcept;           // exact: the sign flipped
Number operator*(Number a, Number b) noexcept; // RN(ab): the plain product
bool operator==(Number a, Number b) noexcept;  // IEEE comparisons: false with a NaN, the two zeros equal
bool operator!=(Number a, Number b) noexcept;
bool operator<(Number a, Number b) noexcept;
bool operator<=(Number a, Number b) noexcept;
bool operator>(Number a, Number b) noexcept;
bool operator>=(Number a, Number b) noexcept;
Number fma_rn(Number a, Number b, Number c) noexcept;  // RN(ab + c), one rounding
Number abs_bits(Number a) noexcept;                    // exact: the sign cleared
Number next_up_bits(Number a) noexcept;                // IEEE 754 nextUp in the format
Number next_down_bits(Number a) noexcept;              // IEEE 754 nextDown in the format
Number times_inf_ce(Number t) noexcept;                // t times +infinity, from comparisons
Number pow2(int k) noexcept;                           // RN(2^k) in the format

// The constants of the generated kernels in the current format: constant(i) is the value of the
// i-th of the constants that tests/emulated/gen/kernels.hpp lists, which the runner loads for each
// format (set_constants). A constant that is not defined in the format stops the program; the
// runner refuses such a kernel before it runs (as the interpreter does).
const Number& constant(int i) noexcept;
void set_constants(const Number* values, const bool* defined, int n);

// The test of constant evaluation in the generated kernels (where the double kernels have
// __builtin_is_constant_evaluated()): false unless the runner was asked for the path of constant
// evaluation (--ce).
bool constant_evaluation() noexcept;
void set_constant_evaluation(bool on) noexcept;

// The line protocol (docs/developer/architecture.md, "The line protocol"): a limb is inf, -inf,
// nan or a C99 hexadecimal literal. parse returns false, with the reason, for text that is not a
// limb or not a number of the format; to_text writes the shortest normalized literal
// (0x1.8p+1, -0x0p+0, 0x1p-14), every NaN as nan.
bool parse(const std::string& text, Number& out, std::string* why = nullptr);
std::string to_text(Number v);

// A fault planted on purpose, to show that the tests of this arithmetic catch one
// (tests/emulated/test_emulated.py): "tie-away" rounds every tie away from zero, "subnormal-trunc"
// truncates every result in the subnormal range; "" removes it. Returns false for an unknown name.
bool plant_fault(const std::string& name) noexcept;

}  // namespace kairn::emulated

template <>
class std::numeric_limits<kairn::emulated::Number> {
public:
    static constexpr bool is_specialized = true;
    static constexpr bool has_infinity = true;
    static constexpr bool has_quiet_NaN = true;
    static constexpr kairn::emulated::Number infinity() noexcept { return kairn::emulated::Number::infinity(false); }
    static constexpr kairn::emulated::Number quiet_NaN() noexcept { return kairn::emulated::Number::nan(); }
};
