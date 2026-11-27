// api.upward.units, api.upward.units.ipo and api.upward.dll: the scopes in this file, the operation
// in another (units_b.cpp), linked into this program, with whole-program optimization (which can
// inline it here: IPO, /GL with MSVC), or built into a DLL (MSVC only; UPWARD_TEST_DLL). Requires
// the rounding mode upward set by kairn::upward::Scope and the options of docs/concepts/upward.md
// (GCC and Clang -frounding-math, MSVC /fp:strict).
//
// The probes, each on the product (1 + 2^-52)^2 = 1 + 2^-51 + 2^-104, which is 1 + 3 2^-52 rounded
// upward and 1 + 2^-51 rounded to nearest: on literal operands (a build that folds them shows),
// before a scope and again inside it (a merge, or a move above the change of mode), in a loop of a
// length the compiler does not know, inside a NearestScope inside a Scope and again after it (the
// refresh after the restoring write), and used only after its scope has ended (a move below the
// restoring write: the gap of the design page's section "MSVC", which this probes and does not
// close). On MSVC also where the operation's file finds kairn::upward::detail::zero: the same object
// as this file's within one program, another one in a DLL (each module has its own).
//
// Two arrangements: the scope in this file around calls into the other file (the probes above, and
// the type's sum, its product by a number and a function on arrays called inside a Scope); and the
// scope held by the function of the other file (a product in a kairn::upward::Scope of its own, the
// function on arrays with the scope it holds), called from rounding to nearest, inside a
// NearestScope inside a Scope, and in a loop, this file's code to nearest again after each call.
#include <kairn/upward.hpp>

#include "environment.hpp"
#include "units.hpp"

using namespace upward_test;
using kairn::upward::NearestScope;
using kairn::upward::Scope;

namespace {

constexpr double x_lit = 1 + 0x1p-52;
constexpr double up = 1 + 0x3p-52;
constexpr double nearest = 1 + 0x1p-51;
volatile double v_x = x_lit;
volatile int v_count = 5;
volatile double out = 0;

char line[256];

void probe(const char* what, double got, double want) {
    std::snprintf(line, sizeof line, "%s: %a (%s)", what, got, got == want ? "as expected" : want == up ? "expected upward" : "expected to nearest");
    expect(got == want, line);
}

// The sum 1 + 2^-60 (environment.hpp's v_one and v_tiny): 1 + 2^-52 upward, 1 to nearest.
constexpr double sum_up = 1 + 0x1p-52;
void probe_sum(const char* what, double got, double want) {
    std::snprintf(line, sizeof line, "%s: %a (%s)", what, got, got == want ? "as expected" : want == sum_up ? "expected upward" : "expected to nearest");
    expect(got == want, line);
}

}  // namespace

int main() {
#if defined(UPWARD_TEST_DLL)
    const char* name = "api.upward.dll";
#else
    const char* name = "api.upward.units";
#endif
    {
        Scope s;
        out = units::mul(x_lit, x_lit);
    }
    probe("literal operands in a Scope", out, up);
    out = units::mul(x_lit, x_lit);
    probe("literal operands outside any scope", out, nearest);

    double a = 0, b = 0, c = 0;
    a = units::mul(x_lit, x_lit);
    {
        Scope s;
        b = units::mul(x_lit, x_lit);
        out = b;
    }
    c = units::mul(x_lit, x_lit);
    out = a;
    probe("literal operands before a Scope", out, nearest);
    probe("the same inside it", b, up);
    out = c;
    probe("the same after it", out, nearest);

    const double x = v_x;
    const double before = units::mul(x, x);
    out = before;
    {
        Scope s;
        out = units::mul(x, x);
    }
    probe("an operand in a register, inside a Scope, after the same product before it", out, up);
    probe("that product before it", before, nearest);

    {
        Scope s;
        const int n = v_count;
        bool all = true;
        for (int i = 0; i < n; ++i) {
            const double r = units::mul(x_lit, x_lit);
            out = r;
            all = all && r == up;
        }
        out = all ? up : 0.0;
    }
    probe("literal operands in a loop of unknown length in a Scope", out, up);

    {
        const int n = v_count;
        bool inside = true, outside = true;
        for (int i = 0; i < n; ++i) {
            {
                Scope s;
                out = units::mul(x_lit, x_lit);
            }
            inside = inside && out == up;
            out = units::mul(x_lit, x_lit);
            outside = outside && out == nearest;
        }
        probe("literal operands in a Scope in a loop of unknown length", inside ? up : 0.0, up);
        probe("the same product after each of those scopes", outside ? nearest : 0.0, nearest);
    }

    double in_nearest = 0, after_nearest = 0;
    {
        Scope s;
        {
            NearestScope n;
            in_nearest = units::mul(x_lit, x_lit);
            out = in_nearest;
        }
        after_nearest = units::mul(x_lit, x_lit);
        out = after_nearest;
    }
    probe("literal operands in a NearestScope inside a Scope", in_nearest, nearest);
    probe("the same in the Scope after the NearestScope", after_nearest, up);

    double late = 0;
    {
        Scope s;
        late = units::mul(x, x);
    }
    out = late;
    probe("a product of a Scope used only after the Scope ended", out, up);

    // The first arrangement, the scope in this file around calls into the other file (or the DLL):
    // the type's sum and its product by a number, as the product above, and the function on arrays
    // called inside the Scope (its own scope then only reads).
    {
        const double one = v_one, t = v_tiny;
        double s_in = 0, s_out = 0, n_in = 0, n_out = 0;
        {
            Scope s;
            s_in = units::add(one, t);
            n_in = units::mul_number(x, x);
        }
        s_out = units::add(one, t);
        n_out = units::mul_number(x, x);
        probe_sum("the type's sum in a Scope", s_in, sum_up);
        probe_sum("the same after the Scope", s_out, 1.0);
        probe("the type's product by a number in a Scope", n_in, up);
        probe("the same after the Scope", n_out, nearest);
        double z[9] = {};
        {
            Scope s;
            units::square_array(x, z, 9);
        }
        bool all = true;
        for (double e : z) all = all && e == up;
        probe("a function on arrays called in a Scope, every element", all ? up : 0.0, up);
    }

    // The second arrangement, the scope held by the function of the other file (or the DLL), called
    // from rounding to nearest, inside a NearestScope inside a Scope, and in a loop; after each call
    // this file's code is to nearest again.
    {
        double z[9] = {};
        probe("a product in a Scope held by the other file, called to nearest", units::held_mul(x, x), up);
        probe("this file's product after that call", units::mul(x, x), nearest);
        units::square_array(x, z, 9);
        bool all = true;
        for (double e : z) all = all && e == up;
        probe("a function on arrays (its own scope) called to nearest, every element", all ? up : 0.0, up);
        probe("this file's product after that call", units::mul(x, x), nearest);
        double held = 0, after = 0;
        {
            Scope s;
            {
                NearestScope n;
                held = units::held_mul(x, x);
                after = units::mul(x, x);
            }
        }
        probe("a product in a Scope held by the other file, called in a NearestScope inside a Scope", held, up);
        probe("the NearestScope's product after that call", after, nearest);
        const int n = v_count;
        bool loop = true;
        for (int i = 0; i < n; ++i) loop = loop && units::held_mul(x, x) == up && units::mul(x, x) == nearest;
        probe("held Scopes in a loop of unknown length, and to nearest between them", loop ? up : 0.0, up);
    }

#if defined(KAIRN_DETAIL_UPWARD_MSVC)
    const void* here = &kairn::upward::detail::zero;
    const void* there = units::zero_address();
#if defined(UPWARD_TEST_DLL)
    std::printf("note  : kairn::upward::detail::zero is at %p in the program and at %p in the DLL\n", here, there);
    expect(here != there, "the DLL has its own kairn::upward::detail::zero, which the program's scopes never write");
#else
    expect(here == there, "kairn::upward::detail::zero is the same object in both files of the program");
#endif
#else
    expect(units::zero_address() == nullptr, "no kairn::upward::detail::zero outside MSVC: the barriers are on the values");
#endif
    return summary(name);
}
