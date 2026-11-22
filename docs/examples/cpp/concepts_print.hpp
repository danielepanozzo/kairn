// The printing of the Concepts examples (docs/concepts/): a number of T in hexadecimal, written the
// same way on every platform, so that the text each program prints, which ctest compares with the
// .txt file its page shows (tests/api/example_output.cmake), does not depend on the C library's %a
// (which differs between C libraries in the digits it prints). Not part of what the pages show.
#pragma once

#include <bit>
#include <cstdint>
#include <limits>
#include <string>

namespace concepts {

// x exactly, as 0x1.hhhp+e with the trailing zero digits left out (0x1p-60, 0x1.8p+0), subnormal
// numbers normalized the same way (0x1p-1074); "inf", "-inf", "nan"; a zero as "0", whatever its
// sign, which Kairn leaves unspecified. A float is printed through its exact double.
inline std::string hex(double x) {
    if (x != x) return "nan";
    if (x == 0) return "0";
    std::string s = x < 0 ? "-" : "";
    if (x < 0) x = -x;
    if (x > std::numeric_limits<double>::max()) return s + "inf";
    const std::uint64_t bits = std::bit_cast<std::uint64_t>(x);
    int e = int(bits >> 52);
    std::uint64_t m = bits & ((std::uint64_t{1} << 52) - 1);
    if (e == 0) {  // subnormal: shift the significand up to its leading bit
        e = -1022;
        while ((m >> 52) == 0) {
            m <<= 1;
            --e;
        }
        m &= (std::uint64_t{1} << 52) - 1;
    } else {
        e -= 1023;
    }
    s += "0x1";
    if (m != 0) {
        s += '.';
        for (int shift = 48; m != 0; shift -= 4) {
            s += "0123456789abcdef"[(m >> shift) & 0xf];
            m &= (std::uint64_t{1} << shift) - 1;
        }
    }
    s += 'p';
    s += e < 0 ? '-' : '+';
    s += std::to_string(e < 0 ? -e : e);
    return s;
}

}  // namespace concepts
