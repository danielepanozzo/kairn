// api.upward.scope: the scopes of <kairn/upward.hpp> (the design page, "The scopes"), observed from
// outside through the control register, <cfenv> and the hardware's arithmetic (environment.hpp).
// Requires the rounding mode upward set by kairn::upward::Scope and the options of
// docs/concepts/upward.md (GCC and Clang -frounding-math, MSVC /fp:strict): built with kairn::upward.
//
// - Each scope sets its mode with flush to zero and denormals-are-zero off, from every starting
//   mode with flush to zero off and on, and restores the state it found when it ends.
// - A scope writes the register only when something must change: a scope inside one of the same
//   mode does not write it, which shows when the mode is changed by hand inside the inner scope and
//   is still changed after the inner scope ends (a scope that wrote would have restored it); a
//   NearestScope inside a Scope, which writes, restores it.
// - The exception flags raised inside a scope, and those raised before it, are kept after it.
// - The C library's mode follows the scopes of the program (std::fegetround() reports their mode
//   inside), and not the register-only scope of the functions on arrays, where the C library has a
//   state of its own (glibc on x86-64, which reads the x87 control word); where the C library reads
//   the register (AArch64, Microsoft's C runtime) it reports upward there too.
// - A NearestScope inside a Scope, and a Scope inside a NearestScope.
// - A thread started inside a scope holds its own scope and does not rely on inheriting the mode,
//   which it may or may not (printed).
// - The barriers and the pin of the generated kernels keep every bit of every value of every type
//   they take, and pass() too; the header's sum through them rounds upward in a Scope and to
//   nearest in a NearestScope, on literal operands too.
#include <kairn/upward.hpp>

#include "environment.hpp"

#include <thread>
#include <type_traits>

using namespace upward_test;
using kairn::upward::NearestScope;
using kairn::upward::Scope;
using kairn::upward::detail::RegisterScope;

static_assert(std::is_nothrow_default_constructible_v<Scope> && std::is_nothrow_default_constructible_v<NearestScope>);
static_assert(!std::is_copy_constructible_v<Scope> && !std::is_move_constructible_v<Scope> &&
              !std::is_copy_assignable_v<Scope> && !std::is_move_assignable_v<Scope>);
static_assert(!std::is_copy_constructible_v<NearestScope> && !std::is_move_constructible_v<NearestScope> &&
              !std::is_copy_assignable_v<NearestScope> && !std::is_move_assignable_v<NearestScope>);

namespace {

// What the C library reports inside the register-only scope: its own state where it has one
// (glibc on x86, which reads the x87 control word), the register where it reads that (AArch64,
// Microsoft's C runtime); -1 where this test does not know, and the value is only printed.
int library_in_register_scope(int before) {
#if defined(UPWARD_TEST_FPCR) || (defined(UPWARD_TEST_MXCSR) && defined(_MSC_VER))
    (void)before;
    return FE_UPWARD;
#elif defined(UPWARD_TEST_MXCSR) && defined(__GLIBC__)
    return before;
#else
    (void)before;
    return -1;
#endif
}

char line[256];

// The state inside a scope of mode `mode`: the register's mode and no flush bits, the hardware's
// rounding, subnormal numbers kept; the C library's mode `library` (-1: printed only).
void expect_inside(const char* what, int mode, int library) {
    std::snprintf(line, sizeof line, "%s: the register's mode is %s", what, mode_name(mode));
    expect(register_mode() == mode, line);
    std::snprintf(line, sizeof line, "%s: the hardware rounds %s", what, mode_name(mode));
    expect(hardware_mode() == mode, line);
    std::snprintf(line, sizeof line, "%s: no flush to zero, no denormals-are-zero (register, and subnormal results and operands kept)", what);
    expect(register_flush() == 0 && subnormals_kept(), line);
    if (library >= 0) {
        std::snprintf(line, sizeof line, "%s: the C library reports %s", what, mode_name(library));
        expect(std::fegetround() == library, line);
    } else {
        std::printf("note  : %s: the C library reports %s\n", what, mode_name(std::fegetround()));
    }
}

// The state after a scope: as set before it.
void expect_restored(const char* what, int mode, int library, bool flush) {
    std::snprintf(line, sizeof line, "%s: after it, the register's mode is %s again, and the C library's %s", what,
                  mode_name(mode), mode_name(library));
    expect(register_mode() == mode && std::fegetround() == library, line);
    std::snprintf(line, sizeof line, "%s: after it, flush to zero is %s again", what, flush ? "on" : "off");
    expect((register_flush() == flush_bits()) == flush && (register_flush() == 0) == !flush, line);
}

// Each scope from each starting state.
void starting_states() {
    const int modes[] = {FE_TONEAREST, FE_DOWNWARD, FE_TOWARDZERO, FE_UPWARD};
    for (int start : modes) {
        for (bool flush : {false, true}) {
            if constexpr (!has_register) {
                if (flush) continue;
            }
            char where[96];
            std::snprintf(where, sizeof where, "from %s, flush to zero %s", mode_name(start), flush ? "on" : "off");
            char what[160];

            set_environment(start, flush);
            {
                Scope s;
                std::snprintf(what, sizeof what, "Scope %s", where);
                expect_inside(what, FE_UPWARD, FE_UPWARD);
            }
            std::snprintf(what, sizeof what, "Scope %s", where);
            expect_restored(what, start, start, flush);

            set_environment(start, flush);
            {
                NearestScope s;
                std::snprintf(what, sizeof what, "NearestScope %s", where);
                expect_inside(what, FE_TONEAREST, FE_TONEAREST);
            }
            std::snprintf(what, sizeof what, "NearestScope %s", where);
            expect_restored(what, start, start, flush);

            set_environment(start, flush);
            {
                RegisterScope s;
                std::snprintf(what, sizeof what, "the register-only scope %s", where);
                expect_inside(what, FE_UPWARD, start == FE_UPWARD ? FE_UPWARD : library_in_register_scope(start));
            }
            std::snprintf(what, sizeof what, "the register-only scope %s", where);
            expect_restored(what, start, start, flush);
        }
    }
    set_environment(FE_TONEAREST, false);
}

// A scope inside one of the same mode does not write the register: the mode changed by hand inside
// it is still changed after it (a scope that wrote would restore what it read). A NearestScope
// inside a Scope writes, and restores.
template <class Outer, class Inner>
void nested_without_write(const char* what, int mode) {
    {
        Outer outer;
        {
            Inner inner;
            set_register_mode(FE_TOWARDZERO);
        }
        std::snprintf(line, sizeof line, "%s: the inner scope wrote nothing (the mode set by hand inside it stays)", what);
        expect(register_mode() == FE_TOWARDZERO, line);
        set_register_mode(mode);
    }
    std::snprintf(line, sizeof line, "%s: after both, to nearest", what);
    expect(register_mode() == FE_TONEAREST && std::fegetround() == FE_TONEAREST, line);
}

void nesting() {
    set_environment(FE_TONEAREST, false);
    nested_without_write<Scope, Scope>("a Scope inside a Scope", FE_UPWARD);
    nested_without_write<Scope, RegisterScope>("the register-only scope inside a Scope", FE_UPWARD);
    nested_without_write<RegisterScope, RegisterScope>("the register-only scope inside itself", FE_UPWARD);
    nested_without_write<NearestScope, NearestScope>("a NearestScope inside a NearestScope", FE_TONEAREST);
    nested_without_write<Scope, Scope>("a Scope inside a Scope, again", FE_UPWARD);
    {
        Scope outer;
        {
            NearestScope inner;
            set_register_mode(FE_TOWARDZERO);
        }
        expect(register_mode() == FE_UPWARD, "a NearestScope inside a Scope wrote the register, and restored it (the mode set by hand inside it is gone)");
    }
    expect(register_mode() == FE_TONEAREST, "after both, to nearest");

    // A NearestScope inside a Scope, and the reverse.
    {
        Scope outer;
        expect_inside("a Scope", FE_UPWARD, FE_UPWARD);
        {
            NearestScope inner;
            expect_inside("a NearestScope inside a Scope", FE_TONEAREST, FE_TONEAREST);
            {
                Scope again;
                expect_inside("a Scope inside that NearestScope", FE_UPWARD, FE_UPWARD);
            }
            expect_inside("the NearestScope again", FE_TONEAREST, FE_TONEAREST);
        }
        expect_inside("the Scope after the NearestScope", FE_UPWARD, FE_UPWARD);
    }
    expect_restored("a Scope around a NearestScope", FE_TONEAREST, FE_TONEAREST, false);
    {
        NearestScope outer;
        {
            Scope inner;
            expect_inside("a Scope inside a NearestScope", FE_UPWARD, FE_UPWARD);
        }
        expect_inside("the NearestScope after the Scope", FE_TONEAREST, FE_TONEAREST);
    }
    expect_restored("a NearestScope around a Scope", FE_TONEAREST, FE_TONEAREST, false);
    if constexpr (has_register) {
        set_environment(FE_DOWNWARD, true);
        {
            NearestScope outer;
            expect_inside("a NearestScope from downward with flush to zero", FE_TONEAREST, FE_TONEAREST);
            {
                Scope inner;
                expect_inside("a Scope inside it", FE_UPWARD, FE_UPWARD);
            }
            expect_inside("the NearestScope after it", FE_TONEAREST, FE_TONEAREST);
        }
        expect_restored("a NearestScope from downward with flush to zero", FE_DOWNWARD, FE_DOWNWARD, true);
        set_environment(FE_TONEAREST, false);
    }
}

// The exception flags raised inside a scope, and those raised before it, are kept after it.
template <class S>
void flags_kept(const char* what) {
    std::feclearexcept(FE_ALL_EXCEPT);
    {
        S s;
        raise_inexact();
    }
    std::snprintf(line, sizeof line, "%s: the inexact flag raised inside it is kept after it", what);
    expect(inexact_raised(), line);
    std::feclearexcept(FE_ALL_EXCEPT);
    raise_inexact();
    {
        S s;
    }
    std::snprintf(line, sizeof line, "%s: the inexact flag raised before it is kept after it", what);
    expect(inexact_raised(), line);
    std::feclearexcept(FE_ALL_EXCEPT);
    {
        Scope outer;
        {
            S s;
            raise_inexact();
        }
    }
    std::snprintf(line, sizeof line, "%s inside a Scope: the inexact flag raised inside it is kept after both", what);
    expect(inexact_raised(), line);
    std::feclearexcept(FE_ALL_EXCEPT);
}

void flags() {
    set_environment(FE_TONEAREST, false);
    flags_kept<Scope>("a Scope");
    flags_kept<NearestScope>("a NearestScope");
    flags_kept<RegisterScope>("the register-only scope");
    set_environment(FE_DOWNWARD, false);
    flags_kept<NearestScope>("a NearestScope from downward");
    set_environment(FE_TONEAREST, false);
}

// A thread started inside a scope: its own scopes set and restore its mode, whatever it inherited.
struct ThreadResult {
    int inherited = -1;
    bool scope_upward = false, scope_library = false, scope_restored = false;
    bool nearest = false, nearest_restored = false;
};

void thread_body(ThreadResult* r) {
    r->inherited = register_mode();
    {
        Scope s;
        r->scope_upward = register_mode() == FE_UPWARD && hardware_mode() == FE_UPWARD && subnormals_kept();
        r->scope_library = std::fegetround() == FE_UPWARD;
    }
    r->scope_restored = register_mode() == r->inherited;
    {
        NearestScope s;
        r->nearest = register_mode() == FE_TONEAREST && hardware_mode() == FE_TONEAREST;
    }
    r->nearest_restored = register_mode() == r->inherited;
}

void threads() {
    set_environment(FE_TONEAREST, false);
    ThreadResult r;
    {
        Scope s;
        std::thread t(thread_body, &r);
        t.join();
        expect_inside("the Scope of the thread that started another", FE_UPWARD, FE_UPWARD);
    }
    std::printf("note  : a thread started inside a Scope found the mode %s (inherited or not: the header does not rely on it)\n",
                mode_name(r.inherited));
    expect(r.scope_upward, "the thread's own Scope sets upward, flush to zero off");
    expect(r.scope_library, "the thread's own Scope sets the C library's mode");
    expect(r.scope_restored, "the thread's own Scope restores the mode the thread found");
    expect(r.nearest && r.nearest_restored, "the thread's own NearestScope sets to nearest and restores");
    expect_restored("a Scope that started a thread", FE_TONEAREST, FE_TONEAREST, false);
}

// The barriers, the pin and pass() keep every bit of every value.
template <class T>
bool kept(T v) {
    T b = v, p = v;
    KAIRN_DETAIL_UPWARD_BARRIER(b);
    KAIRN_DETAIL_UPWARD_PIN(p);
    return same_bits(b, v) && same_bits(p, v) && same_bits(kairn::upward::pass(v), v);
}

template <class T>
void values(const char* type) {
    using L = std::numeric_limits<T>;
    const T list[] = {T(0), -T(0), T(1), -T(1), T(0.1), L::min(), L::denorm_min(), -L::denorm_min(), L::max(),
                      -L::max(), L::infinity(), -L::infinity(), L::quiet_NaN(), -L::quiet_NaN(), L::epsilon()};
    bool all = true;
    for (T v : list) all = all && kept(v);
    std::snprintf(line, sizeof line, "the barrier, the pin and pass() keep every bit of %s values", type);
    expect(all, line);
    // A default interval through pass(): the same bounds, bit for bit.
    using I = kairn::Interval<T, 1>;
    const I sets[] = {I::from_bounds(T(1), T(2)), I::from_bounds(-L::infinity(), T(0.1)), I::empty(), I::whole(), I()};
    all = true;
    for (const I& x : sets) {
        const I y = kairn::upward::pass(x);
        all = all && same_bits(y.lower().limb[0], x.lower().limb[0]) && same_bits(y.upper().limb[0], x.upper().limb[0]);
    }
    std::snprintf(line, sizeof line, "pass() of a default Interval<%s, 1> keeps its bounds bit for bit", type);
    expect(all, line);
}

void registers() {
    values<double>("double");
    values<float>("float");
    {
        Scope s;
        values<double>("double, in a Scope");
    }
#if defined(UPWARD_TEST_MXCSR)
    {
        const double a = -0.0, b = std::numeric_limits<double>::denorm_min();
        __m128d v = _mm_set_pd(b, a), w = v, p = v;
        KAIRN_DETAIL_UPWARD_BARRIER(w);
        KAIRN_DETAIL_UPWARD_PIN(p);
        double out[2], outp[2];
        _mm_storeu_pd(out, w);
        _mm_storeu_pd(outp, p);
        expect(same_bits(out[0], a) && same_bits(out[1], b) && same_bits(outp[0], a) && same_bits(outp[1], b),
               "the barrier and the pin keep both lanes of an __m128d");
        const float f[4] = {-0.0f, std::numeric_limits<float>::denorm_min(), std::numeric_limits<float>::quiet_NaN(), 1.5f};
        __m128 u = _mm_loadu_ps(f), up = u;
        KAIRN_DETAIL_UPWARD_BARRIER(u);
        KAIRN_DETAIL_UPWARD_PIN(up);
        float g[4], gp[4];
        _mm_storeu_ps(g, u);
        _mm_storeu_ps(gp, up);
        bool all = true;
        for (int i = 0; i < 4; ++i) all = all && same_bits(g[i], f[i]) && same_bits(gp[i], f[i]);
        expect(all, "the barrier and the pin keep every lane of an __m128");
    }
#if defined(__AVX__)
    {
        const double d[4] = {-0.0, std::numeric_limits<double>::denorm_min(), std::numeric_limits<double>::infinity(), 3.0};
        __m256d v = _mm256_loadu_pd(d), p = v;
        KAIRN_DETAIL_UPWARD_BARRIER(v);
        KAIRN_DETAIL_UPWARD_PIN(p);
        double out[4], outp[4];
        _mm256_storeu_pd(out, v);
        _mm256_storeu_pd(outp, p);
        bool all = true;
        for (int i = 0; i < 4; ++i) all = all && same_bits(out[i], d[i]) && same_bits(outp[i], d[i]);
        expect(all, "the barrier and the pin keep every lane of an __m256d");
        const float f[8] = {-0.0f, 1.0f, 2.0f, 3.0f, std::numeric_limits<float>::denorm_min(), 5.0f, 6.0f, -7.0f};
        __m256 u = _mm256_loadu_ps(f), up = u;
        KAIRN_DETAIL_UPWARD_BARRIER(u);
        KAIRN_DETAIL_UPWARD_PIN(up);
        float g[8], gp[8];
        _mm256_storeu_ps(g, u);
        _mm256_storeu_ps(gp, up);
        all = true;
        for (int i = 0; i < 8; ++i) all = all && same_bits(g[i], f[i]) && same_bits(gp[i], f[i]);
        expect(all, "the barrier and the pin keep every lane of an __m256");
    }
#endif
#elif defined(__aarch64__)
    {
        const double d[2] = {-0.0, std::numeric_limits<double>::denorm_min()};
        float64x2_t v = vld1q_f64(d), p = v;
        KAIRN_DETAIL_UPWARD_BARRIER(v);
        KAIRN_DETAIL_UPWARD_PIN(p);
        double out[2], outp[2];
        vst1q_f64(out, v);
        vst1q_f64(outp, p);
        expect(same_bits(out[0], d[0]) && same_bits(out[1], d[1]) && same_bits(outp[0], d[0]) && same_bits(outp[1], d[1]),
               "the barrier and the pin keep both lanes of a float64x2_t");
        const float f[2] = {-0.0f, std::numeric_limits<float>::denorm_min()};
        float32x2_t u = vld1_f32(f), up = u;
        KAIRN_DETAIL_UPWARD_BARRIER(u);
        KAIRN_DETAIL_UPWARD_PIN(up);
        float g[2], gp[2];
        vst1_f32(g, u);
        vst1_f32(gp, up);
        expect(same_bits(g[0], f[0]) && same_bits(g[1], f[1]) && same_bits(gp[0], f[0]) && same_bits(gp[1], f[1]),
               "the barrier and the pin keep both lanes of a float32x2_t");
    }
#endif
}

// The header's sum, written as a generated kernel will be (the pin on the first input, barriers on
// the other and on the result), on literal operands and on operands read from volatile objects: 1
// + 2^-60 is 1 + 2^-52 in a Scope and 1 in a NearestScope, at every optimization level.
double kernel_sum(double a, double b) {
    KAIRN_DETAIL_UPWARD_PIN(a);
    KAIRN_DETAIL_UPWARD_BARRIER(b);
    double z = a + b;
    KAIRN_DETAIL_UPWARD_BARRIER(z);
    return z;
}

void arithmetic() {
    volatile double out = 0;
    {
        Scope s;
        out = kernel_sum(1.0, 0x1p-60);
    }
    expect(out == 1 + 0x1p-52, "the kernel's sum of literal operands in a Scope rounds upward");
    {
        Scope s;
        {
            NearestScope n;
            out = kernel_sum(1.0, 0x1p-60);
        }
    }
    expect(out == 1.0, "the same sum in a NearestScope inside a Scope rounds to nearest");
    {
        Scope s;
        out = kernel_sum(v_one, v_tiny);
    }
    expect(out == 1 + 0x1p-52, "the kernel's sum of operands read from volatile objects in a Scope rounds upward");
    out = kernel_sum(1.0, 0x1p-60);
    expect(out == 1.0, "the same sum outside any scope rounds to nearest");
}

}  // namespace

int main() {
    std::printf("the environment at the start: the register %s, flush to zero %s, the C library %s; the flush bits "
                "set and cleared here: 0x%llx\n",
                mode_name(register_mode()), register_flush() ? "on" : "off", mode_name(std::fegetround()),
                static_cast<unsigned long long>(flush_bits()));
    expect(register_mode() == FE_TONEAREST && register_flush() == 0 && std::fegetround() == FE_TONEAREST,
           "the program starts to nearest, without flush to zero");
    starting_states();
    nesting();
    flags();
    threads();
    registers();
    arithmetic();
    expect_restored("the whole test", FE_TONEAREST, FE_TONEAREST, false);
    return summary("api.upward.scope");
}
