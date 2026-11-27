// api.upward.moves and its builds (levels/CMakeLists.txt): what compilers do to code next to the
// boundary of a scope of <kairn/upward.hpp> (the design page, "Code around a scope", "MSVC" and "The
// self-check", items 7 and 8), at each optimization level. Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict): built with kairn::upward, but api.upward.moves.without_options, which tests a
// file built without them (Clang only, where the header compiles without them).
//
// Three groups of probes, each in several shapes (operands in registers, literal operands, in a
// function of its own, a scope inside a loop of a length the compiler does not know and a loop
// inside a scope, results used only after the scope has ended), for double and float. Every probe
// computes a value whose bits differ between the mode upward and rounding to nearest: the square of
// [p, p] with p = 1 + u (u the gap of T at 1), 1 + 2^-60 (2^-30 for float), the midpoint of a default
// interval, the sum of an Expansion<T, 1>.
//
// 1. The header's own operations (the operators of kairn::upward::Interval, with an interval and
//    with a number, a compound assignment, the functions on arrays): never merged with the same
//    operation computed before the scope (or inside a NearestScope), never computed above the
//    scope's write of the mode, never below its restoring write. This is what the barriers
//    promise, and on MSVC the barrier per scope, whose gap is the last of the three: every probe
//    here that uses a result only after its scope (in the same function, in a branch, in a
//    NearestScope begun after it, after a loop of scopes, returned from the function that holds
//    the scope, with many results live at once) looks for exactly that movement. A probe whose
//    result is not the upward one, or for an operation outside the scopes not the one to nearest,
//    fails the test.
// 2. Values taken across a boundary through kairn::upward::pass(), to_interval() or memory (an
//    object of static storage duration): the program's own arithmetic, and the default types, on
//    them happen on the side of the boundary where the program wrote them, into a NearestScope
//    inside a Scope and out of an upward region (docs/concepts/upward.md, "Code next to a scope's
//    boundary"). Each result is written to memory on the side where it is computed. What the
//    concept page's rule promises: a probe that finds otherwise fails the test.
// 3. The same computations without pass(), the operands already in registers or in a local array
//    that no other code sees; and results of the program's own computations used only after the
//    scope that computed them (pass() promises nothing about a computation before it). The design
//    page promises nothing about these: each is reported, "moved" when its result is the one of the
//    other side of the boundary, and never fails the test, but when its result is neither of the
//    two (a defect of the probe). docs/developer/testing.md records what each compiler did.
//
// Built with KAIRN_CHECKS 0 (the levels) or 1 (api.upward.moves.checked, through a
// KAIRN_ENVIRONMENT_FAILURE of its own that records each report: groups 1 and 2 must report nothing,
// and what group 3 makes the default types report is printed). Without the options
// (UPWARD_TEST_WITHOUT_OPTIONS) group 1 is checked as here, groups 2 and 3 only reported: the
// concept page's rule is for a file built with the options.
#include <cstdio>
#include <cstring>

#if defined(UPWARD_TEST_MOVES_CHECKED)
namespace {
int reports = 0;
void record(const char*) { ++reports; }
}  // namespace
#define KAIRN_ENVIRONMENT_FAILURE(reason) record(reason)
#endif

#include <kairn/upward.hpp>

#include "environment.hpp"

#include <cstddef>

#if !defined(UPWARD_TEST_LEVEL)
#define UPWARD_TEST_LEVEL "the build's"
#endif

// The memory through which values cross a boundary in group 2, and the results of groups 2 and 3:
// objects of static storage duration with external linkage, as a program's are.
template <class T>
T moves_memory[8] = {};
template <class T>
T moves_out[32] = {};

namespace {

using namespace upward_test;
using kairn::upward::NearestScope;
using kairn::upward::Scope;
using kairn::upward::pass;
template <class T>
using I = kairn::upward::Interval<T>;
template <class T>
using D = kairn::Interval<T, 1>;
template <class T>
using E = kairn::Expansion<T, 1>;
namespace kernels = kairn::gen::upward;

// The values: p = 1 + u; its square 1 + 2u + u^2 is sq_up upward and sq_near to nearest; 1 + tiny is
// one_up upward and 1 to nearest; sq_up + tiny is sq_next upward and sq_up to nearest. The midpoint
// of [1, p] is p upward and 1 to nearest; that of [sq_near, sq_up] is sq_up upward and sq_near to
// nearest (a tie, to even).
template <class T>
struct V;
template <>
struct V<double> {
    static constexpr double u = 0x1p-52, p = 0x1.0000000000001p+0, sq_up = 0x1.0000000000003p+0,
                            sq_near = 0x1.0000000000002p+0, tiny = 0x1p-60, one_up = 0x1.0000000000001p+0,
                            sq_next = 0x1.0000000000004p+0;
    static constexpr const char* name = "double";
};
template <>
struct V<float> {
    static constexpr float u = 0x1p-23f, p = 0x1.000002p+0f, sq_up = 0x1.000006p+0f, sq_near = 0x1.000004p+0f,
                           tiny = 0x1p-30f, one_up = 0x1.000002p+0f, sq_next = 0x1.000008p+0f;
    static constexpr const char* name = "float";
};

// The operands, read from volatile objects into registers where a probe says so.
template <class T>
struct In {
    static inline volatile T p = V<T>::p;
    static inline volatile T one = T(1);
    static inline volatile T minus_one = T(-1);
    static inline volatile T tiny = V<T>::tiny;
};
volatile int v_count = 5;
volatile bool v_flag = true;

// --- The verdicts ---------------------------------------------------------------------------------

char line[512];
int reported = 0, moved = 0;
char moved_list[16384];

// The verdict on a result meant `meant` whose other side gives `other`.
template <class T>
void verdict(int group, const char* probe, T got, T meant, T other) {
    const bool in_place = same_bits(got, meant), across = same_bits(got, other);
    const char* seen = in_place ? "where written" : across ? "moved across the boundary" : "neither side's value";
    bool gated = group != 3;
#if defined(UPWARD_TEST_WITHOUT_OPTIONS)
    gated = group == 1;
#endif
    if (gated || !(in_place || across)) {
        std::snprintf(line, sizeof line, "%d. %s (%s): %a, %s", group, probe, V<T>::name, double(got), seen);
        expect(in_place, line);
        return;
    }
    ++reported;
    std::printf("report: %d. %s (%s): %s\n", group, probe, V<T>::name, in_place ? "in place" : "moved");
    if (across) {
        ++moved;
        // Each probe once in the list, however many of its iterations moved.
        char entry[256];
        std::snprintf(entry, sizeof entry, "%d. %s (%s)", group, probe, V<T>::name);
        if (!std::strstr(moved_list, entry)) {
            const std::size_t used = std::strlen(moved_list);
            std::snprintf(moved_list + used, sizeof moved_list - used, "%s%s", used ? "; " : "", entry);
        }
    }
}

// The state the program started in, which every scope restores: the register and the C library
// to nearest, flush to zero off.
void expect_restored_nearest() {
    expect(register_mode() == FE_TONEAREST && std::fegetround() == FE_TONEAREST && register_flush() == 0,
           "after the probes, the register and the C library are to nearest again, flush to zero off");
}

// --- Helpers --------------------------------------------------------------------------------------

// [a, a], through from_limbs; the upper bound of an interval, through to_limbs (a store: no barrier).
template <class T>
KAIRN_FORCEINLINE I<T> point(T a) {
    const T l[2] = {a, -a};
    return I<T>::from_limbs(l);
}
template <class T>
KAIRN_FORCEINLINE T upper_of(const I<T>& z) {
    T b[2] = {};
    z.to_limbs(b);
    return b[0];
}
// The type's operators, with the marker, which compiles whatever gen/upward.hpp says of the kernels.
template <class T>
KAIRN_FORCEINLINE I<T> mul(const I<T>& x, const I<T>& y) {
    return kairn::unverified(x) * y;
}
template <class T>
KAIRN_FORCEINLINE I<T> add(const I<T>& x, const I<T>& y) {
    return kairn::unverified(x) + y;
}
// The upper bound of [a, a]^2 through the generated kernel itself, which a probe calls outside the
// scopes, where the operators may not be (a checked build reports them): to nearest there.
template <class T>
KAIRN_FORCEINLINE T kernel_square(T a) {
    kernels::pair<T> z{};
    kernels::upward_mul_1(kernels::pair_make(a, -a), kernels::pair_make(a, -a), z);
    return kernels::pair_upper(z);
}
// The default interval [lo, hi], built to nearest (outside the upward scopes), and its midpoint.
template <class T>
KAIRN_FORCEINLINE D<T> make_default(T lo, T hi) {
    return D<T>(kairn::unverified(lo), hi);
}
template <class T>
KAIRN_FORCEINLINE T midpoint(const D<T>& d) {
    return d.midpoint().limb[0];
}

// ==================================================================================================
// 1. The header's own operations.
// ==================================================================================================

// Operands in registers: the product through the kernel before a scope, the type's inside it, the
// kernel's again after it, in one function (a merge, or a move above the change of mode).
template <class T>
KAIRN_DETAIL_NOINLINE void op_registers(T* r) {
    const T a = In<T>::p;
    const I<T> x = point(a);
    r[0] = kernel_square(a);
    {
        Scope up;
        r[1] = upper_of(mul(x, x));
    }
    r[2] = kernel_square(a);
}

// Literal operands, which a build that folds them computes while it compiles, to nearest.
template <class T>
KAIRN_DETAIL_NOINLINE void op_literals(T* r) {
    r[0] = kernel_square(V<T>::p);
    {
        Scope up;
        r[1] = upper_of(mul(point(V<T>::p), point(V<T>::p)));
        r[2] = upper_of(kairn::unverified(I<T>(kairn::unverified(V<T>::p))) * V<T>::p);
        r[3] = upper_of(add(point(T(1)), point(V<T>::tiny)));
        r[4] = upper_of(kairn::unverified(point(T(1))) + V<T>::tiny);
    }
    r[5] = kernel_square(V<T>::p);
}

// In a function of its own: the same product before the scope and inside it, the result of the
// scope used only after it.
template <class T>
KAIRN_DETAIL_NOINLINE void op_function(T a, T* r) {
    const I<T> x = point(a);
    r[0] = kernel_square(a);
    I<T> z;
    {
        Scope up;
        z = mul(x, x);
    }
    r[1] = upper_of(z);
}

// Returned from the function that holds the scope: the result is made before the scope's
// destructor runs, and the caller uses it after; the function not inlined, and inlined.
template <class T>
KAIRN_DETAIL_NOINLINE I<T> held_square(T a) {
    Scope up;
    return mul(point(a), point(a));
}
template <class T>
KAIRN_FORCEINLINE I<T> held_square_inline(T a) {
    Scope up;
    const I<T> z = mul(point(a), point(a));
    return z;
}
template <class T>
KAIRN_DETAIL_NOINLINE void op_returned(T* r) {
    const T a = In<T>::p;
    r[0] = upper_of(held_square(a));
    const I<T> z = held_square_inline(a);
    r[1] = v_flag ? upper_of(z) : T(0);
}

// A scope inside a loop of a length the compiler does not know, the same product before the loop
// (an invariant hoisted out of the loop would be computed before the first scope); the result in
// the scope, and only after the scope in each iteration.
template <class T>
KAIRN_DETAIL_NOINLINE void op_scope_in_loop(T a, T* r, int n) {
    const I<T> x = point(a);
    r[0] = kernel_square(a);
    for (int i = 0; i < n; ++i) {
        Scope up;
        r[1 + i] = upper_of(mul(x, x));
    }
    for (int i = 0; i < n; ++i) {
        I<T> z;
        {
            Scope up;
            z = mul(x, x);
        }
        r[6 + i] = upper_of(z);
    }
}

// A loop of a length the compiler does not know inside a scope.
template <class T>
KAIRN_DETAIL_NOINLINE void op_loop_in_scope(T a, T* r, int n) {
    const I<T> x = point(a);
    Scope up;
    for (int i = 0; i < n; ++i) r[i] = upper_of(mul(x, x));
}

// Used only after the scope: in a branch after it (a computation sunk into the branch that uses
// it), in a NearestScope begun after it inside the Scope (sunk below that scope's write), the
// operands loaded inside the scope, and the operands used after the scope as well (live across its
// end either way).
template <class T>
KAIRN_DETAIL_NOINLINE void op_after(T a, T* r) {
    const I<T> x = point(a);
    I<T> z1, z2, z3, z4;
    {
        Scope up;
        z1 = mul(x, x);
    }
    r[0] = v_flag ? upper_of(z1) : T(0);
    {
        Scope up;
        z2 = mul(x, x);
        {
            NearestScope n;
            r[1] = upper_of(z2);
        }
    }
    {
        Scope up;
        const T b = In<T>::p;
        z3 = mul(point(b), point(b));
    }
    r[2] = upper_of(z3);
    {
        Scope up;
        z4 = mul(x, x);
    }
    r[3] = upper_of(z4);
    r[4] = upper_of(x);
}

// After a loop of scopes: the last product (sunk out of the loop, after its last scope), and a sum
// accumulated over the scopes, 1 + n u upward and 1 to nearest.
template <class T>
KAIRN_DETAIL_NOINLINE void op_after_loop(T a, T t, T* r, int n) {
    const I<T> x = point(a);
    I<T> z, acc = point(T(In<T>::one));
    for (int i = 0; i < n; ++i) {
        Scope up;
        z = mul(x, x);
    }
    r[0] = upper_of(z);
    for (int i = 0; i < n; ++i) {
        Scope up;
        acc = kairn::unverified(acc) + t;
    }
    r[1] = upper_of(acc);
    const I<T> one = point(T(In<T>::one));
    I<T> late[5];
    for (int i = 0; i < n; ++i) {
        Scope up;
        late[i] = add(one, point(t));
    }
    for (int i = 0; i < n; ++i) r[2 + i] = upper_of(late[i]);
}

// Many results live at once, each used only after the scope: the squares of [1 + k u, 1 + k u] for
// k = 1 to 20, 1 + (2k + 1) u upward and 1 + 2k u to nearest; more than the registers that a call
// preserves on any target, so that a compiler keeps them across the scope's end by spilling them,
// or computes them again after it.
constexpr int pressure = 20;
template <class T>
KAIRN_DETAIL_NOINLINE void op_pressure(const T* a, T* r) {
    I<T> x[pressure], z[pressure];
    for (int k = 0; k < pressure; ++k) x[k] = point(a[k]);
    {
        Scope up;
        for (int k = 0; k < pressure; ++k) z[k] = mul(x[k], x[k]);
    }
    for (int k = 0; k < pressure; ++k) r[k] = upper_of(z[k]);
}

// A compound assignment, the operations with a number, and two scopes in a row (the first's result
// computed between them, or merged with the second's), each used only after the scopes.
template <class T>
KAIRN_DETAIL_NOINLINE void op_forms(T a, T t, T* r) {
    const I<T> x = point(a), one = point(T(In<T>::one)), minus_one = point(T(In<T>::minus_one));
    I<T> c = x, n1, n2, n3, n4, s1, s2;
    {
        Scope up;
        c *= kairn::unverified(x);
        n1 = kairn::unverified(x) * a;
        n2 = kairn::unverified(one) + t;
        n3 = kairn::unverified(one) - (-t);
        n4 = t - kairn::unverified(minus_one);
    }
    {
        Scope up;
        s1 = mul(x, x);
    }
    {
        Scope up;
        s2 = mul(x, x);
    }
    r[0] = upper_of(c);
    r[1] = upper_of(n1);
    r[2] = upper_of(n2);
    r[3] = upper_of(n3);
    r[4] = upper_of(n4);
    r[5] = upper_of(s1);
    r[6] = upper_of(s2);
}

// More shapes for the gap, each a product of a Scope used only after the Scope's end, where a
// compiler could find it cheaper to compute it later: on one path of a real branch, which calls a
// function; given to a function after the Scope, by reference and by value; used in the last
// iteration of a later loop; first in a Scope that does other work after it; in the iteration of a
// loop of Scopes that breaks out of it; stored into an object after the Scope; with its operand
// overwritten after the Scope.
template <class T>
KAIRN_DETAIL_NOINLINE void consume(const I<T>& z, T* r) {
    *r = upper_of(z);
}
template <class T>
KAIRN_DETAIL_NOINLINE void consume_value(I<T> z, T* r) {
    *r = upper_of(z);
}
template <class T>
struct Holder {
    I<T> z;
    int k;
};
template <class T>
KAIRN_DETAIL_NOINLINE void op_gap(T a, T* r, int n) {
    const I<T> x = point(a);
    I<T> z1, z2, z3, z4, z5, z6, w;
    {
        Scope up;
        z1 = mul(x, x);
    }
    if (v_flag) {
        consume(z1, r + 0);
    } else {
        r[0] = T(0);
        v_count = v_count + 1;
    }
    {
        Scope up;
        z2 = mul(x, x);
    }
    consume(z2, r + 1);
    {
        Scope up;
        z3 = mul(x, x);
    }
    consume_value(z3, r + 2);
    {
        Scope up;
        z4 = mul(x, x);
    }
    for (int i = 0; i < n; ++i)
        if (i == n - 1) r[3] = upper_of(z4);
    {
        Scope up;
        z5 = mul(x, x);
        for (int i = 0; i < n; ++i) moves_memory<T>[5] = upper_of(add(point(T(In<T>::one)), point(T(In<T>::tiny))));
    }
    r[4] = upper_of(z5);
    for (int i = 0; i < n; ++i) {
        Scope up;
        z6 = mul(x, x);
        if (v_flag) break;
    }
    r[5] = upper_of(z6);
    Holder<T> h{};
    {
        Scope up;
        w = mul(x, x);
    }
    h.z = w;
    h.k = n;
    r[6] = upper_of(h.z);
    I<T> y = x, z7;
    {
        Scope up;
        z7 = mul(y, y);
    }
    y = point(T(In<T>::one));
    r[7] = upper_of(z7);
    r[8] = upper_of(y);
}

// A NearestScope inside a Scope: the kernel's product inside the NearestScope (to nearest) and the
// type's after it in the Scope (upward), and the reverse order; the same product either side.
template <class T>
KAIRN_DETAIL_NOINLINE void op_nearest_inside(T a, T* r) {
    const I<T> x = point(a);
    {
        Scope up;
        {
            NearestScope n;
            r[0] = kernel_square(a);
        }
        r[1] = upper_of(mul(x, x));
    }
    {
        Scope up;
        r[2] = upper_of(mul(x, x));
        {
            NearestScope n;
            r[3] = kernel_square(a);
        }
    }
}

// The functions on arrays, each holding its own scope: called from rounding to nearest, on arrays
// the program filled from registers and on literal arrays, in a loop, and inside a NearestScope
// inside a Scope; the same product through the kernel before and after each call. 9 elements: the
// registers of the array form and the elements after them.
constexpr std::size_t elements = 9;
template <class T>
KAIRN_DETAIL_NOINLINE void op_arrays(T a, T t, T* r, int n) {
    using kairn::upward::View;
    T xu[elements], xn[elements], ou[elements], on[elements], zu[elements], zn[elements];
    for (std::size_t i = 0; i < elements; ++i) {
        xu[i] = a;
        xn[i] = -a;
        ou[i] = T(1);
        on[i] = T(-1);
    }
    const View<const T> x(xu, xn, elements), one(ou, on, elements);
    r[0] = kernel_square(a);
    kairn::upward::mul(View<T>(zu, zn, elements), kairn::unverified(x), x);
    for (std::size_t i = 0; i < elements; ++i) r[1 + i] = zu[i];
    kairn::upward::add(View<T>(zu, zn, elements), kairn::unverified(one), t);
    for (std::size_t i = 0; i < elements; ++i) r[10 + i] = zu[i];
    r[19] = kernel_square(a);
    static constexpr T lu[elements] = {V<T>::p, V<T>::p, V<T>::p, V<T>::p, V<T>::p, V<T>::p, V<T>::p, V<T>::p, V<T>::p};
    static constexpr T ln[elements] = {-V<T>::p, -V<T>::p, -V<T>::p, -V<T>::p, -V<T>::p, -V<T>::p, -V<T>::p, -V<T>::p,
                                       -V<T>::p};
    const View<const T> literal(lu, ln, elements);
    kairn::upward::mul(View<T>(zu, zn, elements), kairn::unverified(literal), literal);
    for (std::size_t i = 0; i < elements; ++i) r[20 + i] = zu[i];
    T last = 0;
    for (int k = 0; k < n; ++k) {
        kairn::upward::mul(View<T>(zu, zn, elements), kairn::unverified(x), x);
        last = zu[elements - 1];
        r[29 + k] = zu[0];
    }
    r[34] = last;
    {
        Scope up;
        NearestScope nearest;
        kairn::upward::mul(View<T>(zu, zn, elements), kairn::unverified(x), x);
        r[35] = zu[0];
        r[36] = zu[elements - 1];
        r[37] = kernel_square(a);
    }
}

template <class T>
void group1() {
    const T a = In<T>::p, t = In<T>::tiny;
    const int n = v_count < 5 ? v_count : 5;
    const T up = V<T>::sq_up, near = V<T>::sq_near, one_up = V<T>::one_up;
    T r[40] = {};

    op_registers<T>(r);
    verdict(1, "registers: the kernel's product before a Scope", r[0], near, up);
    verdict(1, "registers: the type's product inside the Scope", r[1], up, near);
    verdict(1, "registers: the kernel's product after the Scope", r[2], near, up);

    op_literals<T>(r);
    verdict(1, "literals: the product of two points", r[1], up, near);
    verdict(1, "literals: Interval(p) * p", r[2], up, near);
    verdict(1, "literals: the sum [1, 1] + [tiny, tiny]", r[3], one_up, T(1));
    verdict(1, "literals: [1, 1] + tiny", r[4], one_up, T(1));
    verdict(1, "literals: the kernel's product before and after the Scope", r[0] == r[5] ? r[0] : T(0), near, up);

    op_function<T>(a, r);
    verdict(1, "a function of its own: the kernel's product before the Scope", r[0], near, up);
    verdict(1, "a function of its own: the product of the Scope, used only after it", r[1], up, near);

    op_returned<T>(r);
    verdict(1, "returned from the function that holds the Scope", r[0], up, near);
    verdict(1, "returned from an inlined function that holds the Scope, used in a branch", r[1], up, near);

    op_scope_in_loop<T>(a, r, n);
    verdict(1, "a Scope in a loop: the kernel's product before the loop", r[0], near, up);
    for (int i = 0; i < n; ++i) {
        verdict(1, "a Scope in a loop of unknown length", r[1 + i], up, near);
        verdict(1, "a Scope in a loop of unknown length, the product used after the Scope", r[6 + i], up, near);
    }

    op_loop_in_scope<T>(a, r, n);
    for (int i = 0; i < n; ++i) verdict(1, "a loop of unknown length in a Scope", r[i], up, near);

    op_after<T>(a, r);
    verdict(1, "used only after the Scope, in a branch", r[0], up, near);
    verdict(1, "used only in a NearestScope begun after it in the Scope", r[1], up, near);
    verdict(1, "used only after the Scope, the operands loaded inside it", r[2], up, near);
    verdict(1, "used only after the Scope, the operands used after it too", r[3], up, near);

    op_after_loop<T>(a, t, r, n);
    verdict(1, "the last product of a loop of Scopes, used after the loop", r[0], up, near);
    verdict(1, "a sum accumulated over a loop of Scopes, used after the loop", r[1], T(1 + T(n) * V<T>::u), T(1));
    for (int i = 0; i < n; ++i) verdict(1, "sums of the Scopes of a loop, used after the loop", r[2 + i], one_up, T(1));

    T operands[pressure];
    for (int k = 0; k < pressure; ++k) operands[k] = T(1 + T(k + 1) * V<T>::u);
    op_pressure<T>(operands, r);
    for (int k = 0; k < pressure; ++k)
        verdict(1, "20 products live at once, used only after the Scope", r[k], T(1 + T(2 * k + 3) * V<T>::u),
                T(1 + T(2 * k + 2) * V<T>::u));

    op_forms<T>(a, t, r);
    verdict(1, "x *= y in a Scope, used only after it", r[0], up, near);
    verdict(1, "x * t in a Scope, used only after it", r[1], up, near);
    verdict(1, "x + t in a Scope, used only after it", r[2], one_up, T(1));
    verdict(1, "x - t in a Scope, used only after it", r[3], one_up, T(1));
    verdict(1, "t - x in a Scope, used only after it", r[4], one_up, T(1));
    verdict(1, "the first of two Scopes in a row, used only after both", r[5], up, near);
    verdict(1, "the second of two Scopes in a row", r[6], up, near);

    op_gap<T>(a, r, n);
    verdict(1, "used only after the Scope, on one path of a branch that calls a function", r[0], up, near);
    verdict(1, "given to a function by reference after the Scope", r[1], up, near);
    verdict(1, "given to a function by value after the Scope", r[2], up, near);
    verdict(1, "used in the last iteration of a loop after the Scope", r[3], up, near);
    verdict(1, "first in a Scope that does other work after it", r[4], up, near);
    verdict(1, "in a loop of Scopes that breaks out of its first iteration", r[5], up, near);
    verdict(1, "stored into an object after the Scope", r[6], up, near);
    verdict(1, "its operand overwritten after the Scope", r[7], up, near);
    verdict(1, "the operand overwritten after the Scope", r[8], T(1), V<T>::p);

    op_nearest_inside<T>(a, r);
    verdict(1, "the kernel's product in a NearestScope inside a Scope", r[0], near, up);
    verdict(1, "the type's product in the Scope after the NearestScope", r[1], up, near);
    verdict(1, "the type's product in a Scope before a NearestScope", r[2], up, near);
    verdict(1, "the kernel's product in the NearestScope after it", r[3], near, up);

    op_arrays<T>(a, t, r, n);
    verdict(1, "arrays: the kernel's product before kairn::upward::mul", r[0], near, up);
    for (std::size_t i = 0; i < elements; ++i) {
        verdict(1, "arrays: kairn::upward::mul called to nearest", r[1 + i], up, near);
        verdict(1, "arrays: kairn::upward::add with a number called to nearest", r[10 + i], one_up, T(1));
        verdict(1, "arrays: kairn::upward::mul on literal arrays", r[20 + i], up, near);
    }
    verdict(1, "arrays: the kernel's product after kairn::upward::add", r[19], near, up);
    for (int k = 0; k < n; ++k) verdict(1, "arrays: kairn::upward::mul called in a loop", r[29 + k], up, near);
    verdict(1, "arrays: the last element of the last call of a loop, used after it", r[34], up, near);
    verdict(1, "arrays: kairn::upward::mul in a NearestScope inside a Scope (first element)", r[35], up, near);
    verdict(1, "arrays: the same, last element", r[36], up, near);
    verdict(1, "arrays: the kernel's product in that NearestScope after the call", r[37], near, up);
}

// ==================================================================================================
// 2. Values taken across a boundary through pass(), to_interval() or memory.
// ==================================================================================================

// Into a NearestScope inside a Scope, the operands loaded in the upward region: the program's sum,
// the sum of an Expansion<T, 1> and the midpoint of a default interval on values given to pass();
// the midpoint of to_interval() of an upward interval; the program's sum of values that crossed
// through memory. Each 1 to nearest, and one_up or p had it been computed before the NearestScope.
// The program's own sum of the same registers in the Scope before it (out[6], meant upward: a
// merge with it would give the NearestScope's sum its value) is of group 3.
template <class T>
KAIRN_DETAIL_NOINLINE void pass_into(T* out) {
    const D<T> d = make_default(T(In<T>::one), T(In<T>::p));
    Scope up;
    const T a = In<T>::one, t = In<T>::tiny, b = In<T>::p;
    const I<T> z = point(a).hull(kairn::unverified(point(b)));
    moves_memory<T>[0] = a;
    moves_memory<T>[1] = t;
    out[6] = a + t;
    {
        NearestScope n;
        out[0] = pass(a) + pass(t);
        out[1] = (E<T>(pass(a)) + pass(t)).limb[0];
        out[2] = midpoint(pass(d));
        out[3] = midpoint(kairn::unverified(z).to_interval());
        out[4] = moves_memory<T>[0] + moves_memory<T>[1];
        out[5] = pass(T(1)) + pass(V<T>::tiny);
    }
}

// Out of an upward region: after a Scope, on values that were in registers before it or were
// computed in it, given to pass(); the midpoint of to_interval() of its product; the program's sum
// of values that crossed through memory; the limbs of an upward interval given to pass(). The
// program's own sum of the same registers in the Scope (out[8], meant upward) is of group 3.
template <class T>
KAIRN_DETAIL_NOINLINE void pass_out(T* out) {
    const D<T> d = make_default(T(In<T>::one), T(In<T>::p));
    const T a = In<T>::one, t = In<T>::tiny;
    const I<T> x = point(T(In<T>::p));
    T u = 0;
    I<T> z;
    {
        Scope up;
        z = mul(x, x);
        u = upper_of(z);
        moves_memory<T>[2] = u;
        moves_memory<T>[3] = t;
        out[8] = a + t;
    }
    out[0] = pass(a) + pass(t);
    out[1] = pass(u) + pass(t);
    out[2] = (E<T>(pass(a)) + pass(t)).limb[0];
    out[3] = midpoint(pass(d));
    out[4] = midpoint(kairn::unverified(z).to_interval());
    out[5] = moves_memory<T>[2] + moves_memory<T>[3];
    out[6] = upper_of(pass(z)) + t;
    out[7] = pass(T(1)) + pass(V<T>::tiny);
}

// The same in loops: the program's sum on passed values after each Scope of a loop, and in each
// NearestScope of a loop inside a Scope; and with the scope in a function of its own, inlined.
template <class T>
KAIRN_FORCEINLINE T upward_square_inline(T a) {
    Scope up;
    return upper_of(mul(point(a), point(a)));
}
template <class T>
KAIRN_DETAIL_NOINLINE void pass_loops(T* out, int n) {
    const T a = In<T>::one, t = In<T>::tiny, b = In<T>::p;
    for (int i = 0; i < n; ++i) {
        {
            Scope up;
            moves_memory<T>[4] = upper_of(mul(point(b), point(b)));
        }
        out[i] = pass(a) + pass(t);
    }
    {
        Scope up;
        for (int i = 0; i < n; ++i) {
            NearestScope near;
            out[8 + i] = pass(a) + pass(t);
        }
    }
    const T s = upward_square_inline(b);
    out[16] = pass(s) + pass(t);
}

template <class T>
void group2() {
    const int n = v_count < 5 ? v_count : 5;
    T* out = moves_out<T>;
    const T one_up = V<T>::one_up;

    pass_into<T>(out);
    verdict(2, "into a NearestScope: the program's sum on pass() of registers", out[0], T(1), one_up);
    verdict(2, "into a NearestScope: Expansion<T, 1> + T on pass()", out[1], T(1), one_up);
    verdict(2, "into a NearestScope: the midpoint of pass() of a default interval", out[2], T(1), V<T>::p);
    verdict(2, "into a NearestScope: the midpoint of to_interval()", out[3], T(1), V<T>::p);
    verdict(2, "into a NearestScope: the program's sum of values through memory", out[4], T(1), one_up);
    verdict(2, "into a NearestScope: the program's sum on pass() of literals", out[5], T(1), one_up);
    verdict(3, "the program's sum in a Scope before a NearestScope", out[6], one_up, T(1));

    pass_out<T>(out);
    verdict(2, "out of a Scope: the program's sum on pass() of registers", out[0], T(1), one_up);
    verdict(2, "out of a Scope: the program's sum on pass() of a result of the Scope", out[1], V<T>::sq_up, V<T>::sq_next);
    verdict(2, "out of a Scope: Expansion<T, 1> + T on pass()", out[2], T(1), one_up);
    verdict(2, "out of a Scope: the midpoint of pass() of a default interval", out[3], T(1), V<T>::p);
    verdict(2, "out of a Scope: the midpoint of to_interval() of its product", out[4], V<T>::sq_near, V<T>::sq_up);
    verdict(2, "out of a Scope: the program's sum of values through memory", out[5], V<T>::sq_up, V<T>::sq_next);
    verdict(2, "out of a Scope: the program's sum on the limbs of pass() of its product", out[6], V<T>::sq_up,
            V<T>::sq_next);
    verdict(2, "out of a Scope: the program's sum on pass() of literals", out[7], T(1), one_up);
    verdict(3, "the program's sum in a Scope, the same on pass() after it", out[8], one_up, T(1));

    pass_loops<T>(out, n);
    for (int i = 0; i < n; ++i) {
        verdict(2, "after each Scope of a loop: the program's sum on pass()", out[i], T(1), one_up);
        verdict(2, "in each NearestScope of a loop in a Scope: the program's sum on pass()", out[8 + i], T(1), one_up);
    }
    verdict(2, "after an inlined function that holds a Scope: the program's sum on pass()", out[16], V<T>::sq_up,
            V<T>::sq_next);
}

// ==================================================================================================
// 3. The same without pass(), and results used only after the scope that computed them: reported.
// ==================================================================================================

// Into a NearestScope inside a Scope, the operands in registers: the program's sum, the sum of an
// Expansion<T, 1>, the midpoint of a default interval, the midpoint of the default interval of the
// bounds of an upward interval (lower() and upper(), not to_interval()), and the sum of a local
// array that no other code sees; and the program's sum of the same registers in the Scope before
// the NearestScope (out[5], meant upward), with which the NearestScope's may be merged.
template <class T>
KAIRN_DETAIL_NOINLINE void bare_into(T* out) {
    const D<T> d = make_default(T(In<T>::one), T(In<T>::p));
    Scope up;
    const T a = In<T>::one, t = In<T>::tiny, b = In<T>::p;
    const I<T> z = point(a).hull(kairn::unverified(point(b)));
    T local[2] = {a, t};
    out[5] = a + t;
    {
        NearestScope n;
        out[0] = a + t;
        out[1] = (E<T>(a) + t).limb[0];
        out[2] = midpoint(d);
        out[3] = midpoint(make_default(kairn::unverified(z).lower(), kairn::unverified(z).upper()));
        out[4] = local[0] + local[1];
    }
}

// Out of an upward region, the operands in registers: the program's sum of values from before the
// Scope and of one computed in it, the sum of an Expansion<T, 1>, the midpoint of a default
// interval, of the default interval of the product's bounds, the sum of a local array, and the
// program's sum on upper(); and the program's sum of the same registers in the Scope (out[7], meant
// upward), with which the sum after it may be merged.
template <class T>
KAIRN_DETAIL_NOINLINE void bare_out(T* out) {
    const D<T> d = make_default(T(In<T>::one), T(In<T>::p));
    const T a = In<T>::one, t = In<T>::tiny;
    const I<T> x = point(T(In<T>::p));
    T u = 0, local[2] = {};
    I<T> z;
    {
        Scope up;
        z = mul(x, x);
        u = upper_of(z);
        local[0] = u;
        local[1] = t;
        out[7] = a + t;
    }
    out[0] = a + t;
    out[1] = u + t;
    out[2] = (E<T>(a) + t).limb[0];
    out[3] = midpoint(d);
    out[4] = midpoint(make_default(kairn::unverified(z).lower(), kairn::unverified(z).upper()));
    out[5] = local[0] + local[1];
    out[6] = kairn::unverified(z).upper() + t;
}

// Results of the program's own computations used only after the scope that computed them: a sum
// of an upward Scope (meant upward, to nearest if sunk below its end), the same on passed operands,
// and a sum and an Expansion<T, 1> of a NearestScope inside it on passed operands (meant to nearest,
// upward if sunk below the NearestScope's end).
template <class T>
KAIRN_DETAIL_NOINLINE void bare_sink(T* out) {
    const T a = In<T>::one, t = In<T>::tiny;
    T r0 = 0, r1 = 0, r2 = 0, r3 = 0;
    {
        Scope up;
        r0 = a + t;
        r1 = pass(a) + pass(t);
        {
            NearestScope n;
            r2 = pass(a) + pass(t);
            r3 = (E<T>(pass(a)) + pass(t)).limb[0];
        }
        out[2] = r2;
        out[3] = r3;
    }
    out[0] = r0;
    out[1] = r1;
}

// The program's own sum in an upward Scope: the same sum before it and after it (merged, or moved
// above the change of mode), on literal operands, in the Scope of each iteration of a loop (an
// invariant hoisted out of the loop), and in each NearestScope of a loop inside a Scope.
template <class T>
KAIRN_DETAIL_NOINLINE void bare_merge(T* out, int n) {
    const T a = In<T>::one, t = In<T>::tiny;
    out[0] = a + t;
    {
        Scope up;
        out[1] = a + t;
    }
    out[2] = a + t;
    {
        Scope up;
        out[3] = T(1) + V<T>::tiny;
    }
    for (int i = 0; i < n; ++i) {
        Scope up;
        out[4 + i] = a + t;
    }
    {
        Scope up;
        for (int i = 0; i < n; ++i) {
            NearestScope near;
            out[12 + i] = a + t;
        }
    }
}

// Out of a Scope held by an inlined function: the program's sum on its result, without pass().
template <class T>
KAIRN_DETAIL_NOINLINE void bare_function(T* out) {
    const T b = In<T>::p, t = In<T>::tiny;
    const T s = upward_square_inline(b);
    out[0] = s + t;
}

template <class T>
void group3() {
    const int n = v_count < 5 ? v_count : 5;
    T* out = moves_out<T>;
    const T one_up = V<T>::one_up;
#if defined(UPWARD_TEST_MOVES_CHECKED)
    const int reports_before = reports;
#endif

    bare_into<T>(out);
    verdict(3, "into a NearestScope: the program's sum of registers", out[0], T(1), one_up);
    verdict(3, "into a NearestScope: Expansion<T, 1> + T of registers", out[1], T(1), one_up);
    verdict(3, "into a NearestScope: the midpoint of a default interval in registers", out[2], T(1), V<T>::p);
    verdict(3, "into a NearestScope: the midpoint of the default interval of lower() and upper()", out[3], T(1), V<T>::p);
    verdict(3, "into a NearestScope: the program's sum of a local array", out[4], T(1), one_up);
    verdict(3, "the program's sum in a Scope, the same in a NearestScope after it", out[5], one_up, T(1));

    bare_out<T>(out);
    verdict(3, "out of a Scope: the program's sum of registers", out[0], T(1), one_up);
    verdict(3, "out of a Scope: the program's sum on a result of the Scope", out[1], V<T>::sq_up, V<T>::sq_next);
    verdict(3, "out of a Scope: Expansion<T, 1> + T of registers", out[2], T(1), one_up);
    verdict(3, "out of a Scope: the midpoint of a default interval in registers", out[3], T(1), V<T>::p);
    verdict(3, "out of a Scope: the midpoint of the default interval of lower() and upper()", out[4], V<T>::sq_near,
            V<T>::sq_up);
    verdict(3, "out of a Scope: the program's sum of a local array", out[5], V<T>::sq_up, V<T>::sq_next);
    verdict(3, "out of a Scope: the program's sum on upper()", out[6], V<T>::sq_up, V<T>::sq_next);
    verdict(3, "the program's sum in a Scope, the same after it", out[7], one_up, T(1));

    bare_sink<T>(out);
    verdict(3, "the program's sum of a Scope, used only after it", out[0], one_up, T(1));
    verdict(3, "the program's sum of a Scope on pass(), used only after it", out[1], one_up, T(1));
    verdict(3, "the program's sum of a NearestScope on pass(), used only after it", out[2], T(1), one_up);
    verdict(3, "Expansion<T, 1> + T of a NearestScope on pass(), used only after it", out[3], T(1), one_up);

    bare_merge<T>(out, n);
    verdict(3, "the program's sum before a Scope", out[0], T(1), one_up);
    verdict(3, "the program's sum in the Scope, the same before it", out[1], one_up, T(1));
    verdict(3, "the program's sum after the Scope", out[2], T(1), one_up);
    verdict(3, "the program's sum of literals in a Scope", out[3], one_up, T(1));
    for (int i = 0; i < n; ++i) {
        verdict(3, "the program's sum in the Scope of each iteration of a loop", out[4 + i], one_up, T(1));
        verdict(3, "the program's sum in each NearestScope of a loop in a Scope", out[12 + i], T(1), one_up);
    }

    bare_function<T>(out);
    verdict(3, "after an inlined function that holds a Scope: the program's sum on its result", out[0], V<T>::sq_up,
            V<T>::sq_next);
#if defined(UPWARD_TEST_MOVES_CHECKED)
    std::printf("note  : the checks of the default types reported %d times in group 3 (%s)\n", reports - reports_before,
                V<T>::name);
#endif
}

}  // namespace

int main() {
#if defined(__clang__)
    const char* compiler = "Clang " __clang_version__;
#elif defined(__GNUC__)
    const char* compiler = "GCC " __VERSION__;
#elif defined(_MSC_VER)
    char msvc[32];
    std::snprintf(msvc, sizeof msvc, "MSVC %d", _MSC_FULL_VER);
    const char* compiler = msvc;
#else
    const char* compiler = "an unknown compiler";
#endif
    std::printf("note  : %s, level %s, KAIRN_UPWARD_FORM %d, KAIRN_UPWARD_ARRAYS %d, KAIRN_CHECKS %d%s\n", compiler,
                UPWARD_TEST_LEVEL, KAIRN_UPWARD_FORM, KAIRN_UPWARD_ARRAYS, KAIRN_CHECKS,
#if defined(UPWARD_TEST_WITHOUT_OPTIONS)
                ", built without the options"
#else
                ""
#endif
    );
    group1<double>();
    group1<float>();
#if defined(UPWARD_TEST_MOVES_CHECKED)
    expect(reports == 0, "the header's own operations, in and out of their scopes, report nothing");
#endif
    group2<double>();
    group2<float>();
#if defined(UPWARD_TEST_MOVES_CHECKED)
    expect(reports == 0, "the default types on values taken across a boundary report nothing");
#endif
    group3<double>();
    group3<float>();
    expect_restored_nearest();
    std::printf("note  : without pass(), %d of %d computations next to a boundary moved across it%s%s\n", moved, reported,
                moved ? ": " : "", moved_list);
    return summary("api.upward.moves");
}
