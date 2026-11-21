// The program of the link tests of KAIRN_ENCLOSURE_CODE (link_fail.cmake): one operation of each
// kind of Ball and of Interval, whose definitions, in the external setting, are those of
// definitions.cpp, the program's other translation unit. Exits 0 when the results are what they
// must be.
#include <kairn/kairn.hpp>

#include <cstdio>

int main() {
    volatile double one = 1.0, two = 2.0, r = 0x1p-30;
    const kairn::Ball<double, 2> x{kairn::Expansion<double, 2>{double(one)}, double(r)};
    const kairn::Ball<double, 2> y{double(two)};
    const kairn::Ball<double, 1> p{kairn::Expansion<double, 1>{double(two)}, double(r)};
    const kairn::Ball<float, 2> f{float(one)};
    const bool ok = (x + y).center().limb[0] == 3.0 && (x - y).center().limb[0] == -1.0 &&
                    (x * y).center().limb[0] == 2.0 && (x * double(two)).center().limb[0] == 2.0 &&
                    (p * p).center().limb[0] == 4.0 && (f + f).center().limb[0] == 2.0f &&
                    kairn::half(x).radius() == 0x1p-31 && kairn::ldexp(p, 3).center().limb[0] == 16.0;
    const kairn::Interval<double, 1> i{double(one), double(two)};
    const kairn::Interval<double, 2> j{double(one), double(two)};
    const kairn::Interval<float, 2> k{float(one), float(two)};
    const bool intervals = (i + i).upper().limb[0] == 4.0 && (i - i).lower().limb[0] == -1.0 &&
                           (i * i).upper().limb[0] == 4.0 && (j + j).upper().limb[0] == 4.0 &&
                           (j - j).lower().limb[0] == -1.0 && (j * j).lower().limb[0] == 1.0 &&
                           (k * k).upper().limb[0] == 4.0f;
    std::printf("%s\n", ok && intervals ? "ok" : "FAILED: a result is not what it must be");
    return ok && intervals ? 0 : 1;
}
