// The arithmetic of the emulated limb type (number.hpp), with integers only.
//
// A finite operand is (-1)^s m 2^q. Every operation forms its exact result as (-1)^s N 2^e, N an
// unsigned integer of as many 64-bit words as it needs (Wide), and rounds it once (round): the
// last place kept is 2^q with q = max(e + bits(N) - p, qmin), the bits below it decide (above
// half, or half and the kept significand odd: up), a carry to 2^p moves up one exponent, and an
// exponent above qmax is an overflow to the infinity of the sign. Nothing is ever truncated before
// that one rounding: the operands are aligned exactly, which is why N can be thousands of bits wide
// for binary64 and one word for the formats of the exhaustive tier.
#include "number.hpp"

#include <bit>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace kairn::emulated {

struct Access {
    static Number finite(bool negative, std::uint64_t m, int q) noexcept {
        return Number(Number::Kind::finite, negative, m, q);
    }
};

namespace {

Format current{53, -1074, 971};
bool consteval_mode = false;
std::vector<Number> constants_;
std::vector<bool> defined_;

enum class Fault { none, tie_away, subnormal_trunc };
Fault fault = Fault::none;

// --- Unsigned integers of up to Wide::capacity words -------------------------------------------

struct Wide {
    static constexpr int capacity = 80;   // 5120 bits: an FMA of binary64 needs about 4300
    int size = 0;                         // the words in use; the top one is not zero
    std::uint64_t w[capacity];

    void set(std::uint64_t v) noexcept {
        w[0] = v;
        size = v != 0 ? 1 : 0;
    }
    void trim() noexcept {
        while (size > 0 && w[size - 1] == 0) --size;
    }
    int bits() const noexcept {
        return size == 0 ? 0 : 64 * (size - 1) + int(std::bit_width(w[size - 1]));
    }
};

// The 128-bit product of two words, from 32-bit halves (no __int128, which MSVC lacks).
void mul_words(std::uint64_t a, std::uint64_t b, std::uint64_t& hi, std::uint64_t& lo) noexcept {
    const std::uint64_t a0 = a & 0xffffffffu, a1 = a >> 32, b0 = b & 0xffffffffu, b1 = b >> 32;
    const std::uint64_t p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
    const std::uint64_t mid = (p00 >> 32) + (p01 & 0xffffffffu) + (p10 & 0xffffffffu);
    lo = (p00 & 0xffffffffu) | (mid << 32);
    hi = p11 + (p01 >> 32) + (p10 >> 32) + (mid >> 32);
}

void set_product(Wide& out, std::uint64_t a, std::uint64_t b) noexcept {
    mul_words(a, b, out.w[1], out.w[0]);
    out.size = 2;
    out.trim();
}

// out = a 2^s, s >= 0. out may not be a.
void shift_left(const Wide& a, int s, Wide& out) noexcept {
    if (a.size == 0) {
        out.size = 0;
        return;
    }
    const int words = s / 64, bits = s % 64;
    const int size = a.size + words + 1;
    if (size > Wide::capacity) {
        std::fprintf(stderr, "kairn::emulated: an exact result is wider than %d bits\n", 64 * Wide::capacity);
        std::abort();
    }
    for (int i = 0; i < words; ++i) out.w[i] = 0;
    std::uint64_t carry = 0;
    for (int i = 0; i < a.size; ++i) {
        out.w[words + i] = bits ? (a.w[i] << bits) | carry : a.w[i];
        carry = bits ? a.w[i] >> (64 - bits) : 0;
    }
    out.w[words + a.size] = carry;
    out.size = size;
    out.trim();
}

int compare(const Wide& a, const Wide& b) noexcept {
    if (a.size != b.size) return a.size < b.size ? -1 : 1;
    for (int i = a.size - 1; i >= 0; --i)
        if (a.w[i] != b.w[i]) return a.w[i] < b.w[i] ? -1 : 1;
    return 0;
}

// out = a + b. out may be a or b.
void add(const Wide& a, const Wide& b, Wide& out) noexcept {
    const Wide& big = a.size >= b.size ? a : b;
    const Wide& small = a.size >= b.size ? b : a;
    const int n = big.size, m = small.size;
    if (n + 1 > Wide::capacity) {
        std::fprintf(stderr, "kairn::emulated: an exact sum is wider than %d bits\n", 64 * Wide::capacity);
        std::abort();
    }
    std::uint64_t carry = 0;
    for (int i = 0; i < n; ++i) {
        const std::uint64_t x = big.w[i], y = i < m ? small.w[i] : 0;
        const std::uint64_t s = x + y;
        const std::uint64_t c1 = s < x ? 1 : 0;
        const std::uint64_t t = s + carry;
        const std::uint64_t c2 = t < s ? 1 : 0;
        out.w[i] = t;
        carry = c1 + c2;
    }
    out.w[n] = carry;
    out.size = n + 1;
    out.trim();
}

// out = a - b, a >= b. out may be a or b.
void sub(const Wide& a, const Wide& b, Wide& out) noexcept {
    std::uint64_t borrow = 0;
    for (int i = 0; i < a.size; ++i) {
        const std::uint64_t x = a.w[i], y = i < b.size ? b.w[i] : 0;
        const std::uint64_t d = x - y;
        const std::uint64_t b1 = x < y ? 1 : 0;
        const std::uint64_t t = d - borrow;
        const std::uint64_t b2 = d < borrow ? 1 : 0;
        out.w[i] = t;
        borrow = b1 + b2;
    }
    out.size = a.size;
    out.trim();
}

bool bit(const Wide& a, int k) noexcept {
    if (k < 0 || k / 64 >= a.size) return false;
    return (a.w[k / 64] >> (k % 64)) & 1;
}

// Whether a bit of a below position k is set.
bool any_below(const Wide& a, int k) noexcept {
    if (k <= 0) return false;
    const int words = k / 64, bits = k % 64;
    for (int i = 0; i < words && i < a.size; ++i)
        if (a.w[i]) return true;
    if (bits && words < a.size && (a.w[words] & ((std::uint64_t{1} << bits) - 1))) return true;
    return false;
}

// The 64 bits of a from position lo up, lo >= 0.
std::uint64_t bits_from(const Wide& a, int lo) noexcept {
    const int words = lo / 64, bits = lo % 64;
    if (words >= a.size) return 0;
    std::uint64_t v = a.w[words] >> bits;
    if (bits && words + 1 < a.size) v |= a.w[words + 1] << (64 - bits);
    return v;
}

// --- One rounding ---------------------------------------------------------------------------------

Number zero(bool negative) noexcept { return negative ? -Number() : Number(); }

// RN((-1)^negative n 2^e) in the current format, n > 0.
Number round(bool negative, const Wide& n, int e) noexcept {
    const int p = current.p;
    const int top = e + n.bits() - 1;                    // 2^top <= n 2^e < 2^(top + 1)
    int q = top - p + 1 > current.qmin ? top - p + 1 : current.qmin;   // the last place kept
    std::uint64_t m;
    if (q <= e) {
        m = n.w[0] << (e - q);                           // exact; n has at most p - (e - q) bits
    } else {
        const int s = q - e;                             // the bits dropped
        m = bits_from(n, s);                             // at most p bits
        const bool half = bit(n, s - 1), rest = any_below(n, s - 1);
        bool up = half && (rest || (m & 1));
        if (fault == Fault::tie_away) up = half;
        if (fault == Fault::subnormal_trunc && q == current.qmin && m < (std::uint64_t{1} << (p - 1))) up = false;
        if (up) {
            ++m;
            if (m == std::uint64_t{1} << p) {            // a carry: the next binade
                m >>= 1;
                ++q;
            }
        }
    }
    if (m == 0) return zero(negative);                   // underflow keeps the sign of the exact value
    if (q > current.qmax) return Number::infinity(negative);
    return Access::finite(negative, m, q);
}

// The exact sum of two finite nonzero values (-1)^sa na 2^ea and (-1)^sb nb 2^eb, rounded.
Number round_sum(bool sa, const Wide& na, int ea, bool sb, const Wide& nb, int eb) noexcept {
    const int e = ea < eb ? ea : eb;
    Wide a, b;
    shift_left(na, ea - e, a);
    shift_left(nb, eb - e, b);
    if (sa == sb) {
        add(a, b, a);
        return round(sa, a, e);
    }
    const int c = compare(a, b);
    if (c == 0) return Number();                         // exact cancellation: +0 to nearest
    if (c > 0) {
        sub(a, b, a);
        return round(sa, a, e);
    }
    sub(b, a, b);
    return round(sb, b, e);
}

Wide wide(std::uint64_t v) noexcept {
    Wide w;
    w.set(v);
    return w;
}

// -1, 0, 1 for values that are not NaN; the two zeros are equal.
int compare_values(const Number& a, const Number& b) noexcept {
    const auto rank = [](const Number& x) {
        return x.kind() == Number::Kind::infinite ? (x.negative() ? -2 : 2) : 0;
    };
    const int ra = rank(a), rb = rank(b);
    if (ra != 0 || rb != 0) return ra < rb ? -1 : ra > rb ? 1 : 0;
    const int sa = a.is_zero() ? 0 : a.negative() ? -1 : 1;
    const int sb = b.is_zero() ? 0 : b.negative() ? -1 : 1;
    if (sa != sb || sa == 0) return sa < sb ? -1 : sa > sb ? 1 : 0;
    // One sign, both nonzero: the magnitudes, aligned exactly.
    const int e = a.exponent() < b.exponent() ? a.exponent() : b.exponent();
    Wide x, y;
    shift_left(wide(a.significand()), a.exponent() - e, x);
    shift_left(wide(b.significand()), b.exponent() - e, y);
    return compare(x, y) * sa;
}

}  // namespace

// --- The format -----------------------------------------------------------------------------------

bool set_format(const Format& f, std::string* why) {
    const auto refuse = [&](const std::string& text) {
        if (why) *why = text;
        return false;
    };
    if (f.p < 1 || f.p > max_precision) return refuse("the precision must be 1 to " + std::to_string(max_precision));
    if (f.qmin > f.qmax) return refuse("qmin is above qmax");
    // The widest exact result: an FMA, whose product's last place can be 2 qmin and whose addend's
    // top bit qmax + p, or the product's top bit 2 (qmax + p) above an addend's last place qmin.
    const long long spread = 2LL * f.qmax - 2LL * f.qmin + 4LL * f.p + 192;
    if (f.qmax > 1000000 || f.qmin < -1000000 || spread > 64LL * 80)
        return refuse("the exponent range is too wide for the exact results");
    current = f;
    return true;
}

const Format& format() noexcept { return current; }

bool plant_fault(const std::string& name) noexcept {
    if (name.empty()) fault = Fault::none;
    else if (name == "tie-away") fault = Fault::tie_away;
    else if (name == "subnormal-trunc") fault = Fault::subnormal_trunc;
    else return false;
    return true;
}

bool constant_evaluation() noexcept { return consteval_mode; }
void set_constant_evaluation(bool on) noexcept { consteval_mode = on; }

void set_constants(const Number* values, const bool* defined, int n) {
    constants_.assign(values, values + n);
    defined_.assign(defined, defined + n);
}

const Number& constant(int i) noexcept {
    if (i < 0 || std::size_t(i) >= constants_.size() || !defined_[std::size_t(i)]) {
        std::fprintf(stderr, "kairn::emulated: constant %d is not defined in the format\n", i);
        std::abort();
    }
    return constants_[std::size_t(i)];
}

// --- Numbers ----------------------------------------------------------------------------------------

bool Number::make(bool negative, std::uint64_t m, int q, Number& out) noexcept {
    if (m == 0) {
        out = zero(negative);
        return true;
    }
    // m 2^q = m' 2^q' with m' odd; a number of the format when it fits p bits at an exponent
    // from qmin to qmax: qmin <= q', bits(m') <= p, and q' + bits(m') - p <= qmax.
    const int tz = std::countr_zero(m);
    const std::uint64_t odd = m >> tz;
    const long long qo = (long long)q + tz;
    const int b = int(std::bit_width(odd));
    if (qo < current.qmin || b > current.p || qo + b - current.p > current.qmax) return false;
    // The canonical representation: the last place max(top - p + 1, qmin).
    const long long top = qo + b - 1;
    const long long last = top - current.p + 1 > current.qmin ? top - current.p + 1 : current.qmin;
    out = Access::finite(negative, odd << (qo - last), int(last));
    return true;
}

Number::Number(std::size_t n) noexcept {
    *this = n == 0 ? Number() : round(false, wide(std::uint64_t(n)), 0);
}

Number::operator std::size_t() const noexcept {
    if (kind_ != Kind::finite || neg_ || m_ == 0) return 0;
    const int b = int(std::bit_width(m_));
    if (q_ + b > 64) return 0;                           // 2^64 or more
    if (q_ >= 0) return std::size_t(m_ << q_);
    if (-q_ >= 64) return 0;
    return std::size_t(m_ >> -q_);
}

Number operator-(Number a) noexcept {
    Number r = a;
    if (a.is_nan()) return r;
    if (a.kind() == Number::Kind::infinite) return Number::infinity(!a.negative());
    return Access::finite(!a.negative(), a.significand(), a.exponent());
}

Number abs_bits(Number a) noexcept {
    if (a.is_nan()) return a;
    if (a.kind() == Number::Kind::infinite) return Number::infinity(false);
    return Access::finite(false, a.significand(), a.exponent());
}

Number operator+(Number a, Number b) noexcept {
    if (a.is_nan() || b.is_nan()) return Number::nan();
    if (a.kind() == Number::Kind::infinite) {
        if (b.kind() == Number::Kind::infinite && b.negative() != a.negative()) return Number::nan();
        return a;
    }
    if (b.kind() == Number::Kind::infinite) return b;
    if (a.is_zero() && b.is_zero()) return zero(a.negative() && b.negative());
    if (a.is_zero()) return b;
    if (b.is_zero()) return a;
    return round_sum(a.negative(), wide(a.significand()), a.exponent(), b.negative(), wide(b.significand()),
                     b.exponent());
}

Number operator-(Number a, Number b) noexcept { return a + -b; }

Number operator*(Number a, Number b) noexcept {
    if (a.is_nan() || b.is_nan()) return Number::nan();
    const bool negative = a.negative() != b.negative();
    if (a.kind() == Number::Kind::infinite || b.kind() == Number::Kind::infinite) {
        if (a.is_zero() || b.is_zero()) return Number::nan();
        return Number::infinity(negative);
    }
    if (a.is_zero() || b.is_zero()) return zero(negative);
    Wide n;
    set_product(n, a.significand(), b.significand());
    return round(negative, n, a.exponent() + b.exponent());
}

Number fma_rn(Number a, Number b, Number c) noexcept {
    if (a.is_nan() || b.is_nan() || c.is_nan()) return Number::nan();
    const bool sp = a.negative() != b.negative();
    if (a.kind() == Number::Kind::infinite || b.kind() == Number::Kind::infinite) {
        if (a.is_zero() || b.is_zero()) return Number::nan();
        if (c.kind() == Number::Kind::infinite && c.negative() != sp) return Number::nan();
        return Number::infinity(sp);
    }
    if (c.kind() == Number::Kind::infinite) return c;
    if (a.is_zero() || b.is_zero()) return c.is_zero() ? zero(sp && c.negative()) : c;
    Wide n;
    set_product(n, a.significand(), b.significand());
    const int e = a.exponent() + b.exponent();
    if (c.is_zero()) return round(sp, n, e);
    return round_sum(sp, n, e, c.negative(), wide(c.significand()), c.exponent());
}

bool operator==(Number a, Number b) noexcept { return !a.is_nan() && !b.is_nan() && compare_values(a, b) == 0; }
bool operator!=(Number a, Number b) noexcept { return !(a == b); }
bool operator<(Number a, Number b) noexcept { return !a.is_nan() && !b.is_nan() && compare_values(a, b) < 0; }
bool operator<=(Number a, Number b) noexcept { return !a.is_nan() && !b.is_nan() && compare_values(a, b) <= 0; }
bool operator>(Number a, Number b) noexcept { return !a.is_nan() && !b.is_nan() && compare_values(a, b) > 0; }
bool operator>=(Number a, Number b) noexcept { return !a.is_nan() && !b.is_nan() && compare_values(a, b) >= 0; }

Number next_up_bits(Number a) noexcept {
    const int p = current.p;
    const std::uint64_t low = std::uint64_t{1} << (p - 1), top = (std::uint64_t{1} << p) - 1;
    if (a.is_nan()) return a;
    if (a.kind() == Number::Kind::infinite)
        return a.negative() ? Access::finite(true, top, current.qmax) : a;   // -inf to -Omega
    if (a.is_zero()) return Access::finite(false, 1, current.qmin);          // either zero to +eta
    const std::uint64_t m = a.significand();
    const int q = a.exponent();
    if (!a.negative()) {
        if (m < top) return Access::finite(false, m + 1, q);
        return q == current.qmax ? Number::infinity(false) : Access::finite(false, low, q + 1);
    }
    // A negative number moves toward zero: one place down (-eta to -0), or, from the bottom of a
    // binade above the subnormal range, to the top of the binade below.
    if (m > low || q == current.qmin) return m == 1 ? zero(true) : Access::finite(true, m - 1, q);
    return Access::finite(true, top, q - 1);
}

Number next_down_bits(Number a) noexcept { return -next_up_bits(-a); }

Number times_inf_ce(Number t) noexcept {
    if (t > Number()) return Number::infinity(false);
    if (Number() > t) return Number::infinity(true);
    return Number::nan();
}

Number pow2(int k) noexcept { return round(false, wide(1), k); }

// --- The line protocol ------------------------------------------------------------------------------

bool parse(const std::string& text, Number& out, std::string* why) {
    const auto refuse = [&](const std::string& reason) {
        if (why) *why = reason;
        return false;
    };
    if (text == "inf") return out = Number::infinity(false), true;
    if (text == "-inf") return out = Number::infinity(true), true;
    if (text == "nan") return out = Number::nan(), true;
    std::size_t i = 0;
    bool negative = false;
    if (i < text.size() && (text[i] == '+' || text[i] == '-')) negative = text[i++] == '-';
    if (text.compare(i, 2, "0x") != 0 && text.compare(i, 2, "0X") != 0) return refuse("not a limb: " + text);
    i += 2;
    std::string digits;
    long long scale = 0;
    bool point = false, any = false;
    for (; i < text.size() && text[i] != 'p' && text[i] != 'P'; ++i) {
        const char c = text[i];
        if (c == '.' && !point) {
            point = true;
            continue;
        }
        const bool hex = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
        if (!hex) return refuse("not a limb: " + text);
        any = true;
        digits += c;
        if (point) scale -= 4;
    }
    if (!any || i == text.size()) return refuse("not a limb: " + text);
    ++i;
    std::size_t j = i;
    if (j < text.size() && (text[j] == '+' || text[j] == '-')) ++j;
    if (j == text.size() || j - i > 1 + 9) return refuse("not a limb: " + text);
    for (std::size_t k = j; k < text.size(); ++k)
        if (text[k] < '0' || text[k] > '9') return refuse("not a limb: " + text);
    const long long exp = std::stoll(text.substr(i)) + scale;
    // Leading zeros mean nothing, trailing zero digits move the exponent.
    std::size_t first = digits.find_first_not_of('0');
    if (first == std::string::npos) return out = zero(negative), true;
    std::size_t last = digits.find_last_not_of('0');
    long long e = exp + 4LL * (long long)(digits.size() - 1 - last);
    digits = digits.substr(first, last - first + 1);
    // More than 16 significant digits cannot be a number of any format held (p <= 62).
    if (digits.size() > 16) return refuse(text + " is not a number of the format");
    std::uint64_t m = std::stoull(digits, nullptr, 16);
    if (e < -2000000 || e > 2000000) return refuse(text + " is not a number of the format");
    Number v;
    if (!Number::make(negative, m, int(e), v)) return refuse(text + " is not a number of the format");
    out = v;
    return true;
}

std::string to_text(Number v) {
    if (v.is_nan()) return "nan";
    if (v.kind() == Number::Kind::infinite) return v.negative() ? "-inf" : "inf";
    std::string s = v.negative() ? "-" : "";
    std::uint64_t m = v.significand();
    if (m == 0) return s + "0x0p+0";
    long long e = v.exponent();
    const int tz = std::countr_zero(m);
    m >>= tz;
    e += tz;
    const int bits = int(std::bit_width(m)) - 1;         // the bits after the leading one
    const int digits = (bits + 3) / 4;
    char buf[64];
    if (bits == 0) {
        std::snprintf(buf, sizeof buf, "0x1p%+lld", e);
    } else {
        const std::uint64_t frac = (m - (std::uint64_t{1} << bits)) << (4 * digits - bits);
        std::snprintf(buf, sizeof buf, "0x1.%0*llxp%+lld", digits, (unsigned long long)frac, e + bits);
    }
    return s + buf;
}

}  // namespace kairn::emulated
