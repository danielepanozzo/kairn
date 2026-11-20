// The program of the link tests of KAIRN_ENCLOSURE_CODE (link_fail.cmake): one operation of each
// kind of Ball, whose definitions, in the external setting, are those of definitions.cpp, the
// program's other translation unit. Exits 0 when the results are what they must be.
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
                    (p * p).center().limb[0] == 4.0 && (f + f).center().limb[0] == 2.0f;
    std::printf("%s\n", ok ? "ok" : "FAILED: a result is not what it must be");
    return ok ? 0 : 1;
}
