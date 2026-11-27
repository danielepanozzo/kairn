/// @file
/// The round-up interval: an opt-in alternative to Interval<T, 1>, used only for speed, computed
/// under the rounding mode upward (docs/developer/design/upward.md). Requires the rounding mode
/// upward set by kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang
/// -frounding-math, MSVC /fp:strict), which the CMake target kairn::upward adds.
///
/// Not included by kairn/kairn.hpp. The default types never read or write the rounding mode; this
/// header is the one place of Kairn that sets it, and only in its scopes:
///
/// - kairn::upward::Scope sets the rounding mode upward for its lifetime, with flush to zero and
///   denormals-are-zero off, and restores what it found; kairn::upward::NearestScope sets it to
///   nearest, so that the default types can be called inside an upward region. Every operation of
///   this header that rounds runs inside a Scope (or inside a function on arrays, which holds a
///   scope of its own); the mode is never set by hand around them (fesetround, _mm_setcsr,
///   _controlfp_s).
/// - A file that includes this header is compiled with the options above. Where the compiler shows
///   that they are missing, the header stops the build (GCC: no -frounding-math; MSVC: no
///   /fp:strict, or /fp:contract); KAIRN_UPWARD_OPTIONS_UNCHECKED says that the program takes the
///   options on itself. Clang defines no macro for -frounding-math: there, a checked build's scope
///   reports a file built without it.
/// - kairn::upward::pass(v) returns v after a barrier, for a value that crosses a scope's boundary
///   into code that has no barrier, such as the default types inside a NearestScope.
///
/// Everything here whose result can depend on the options of the file that compiles it has
/// internal linkage (an unnamed namespace): the scopes, pass(), and the check of the build, so
/// that each file runs its own copy, compiled with its own options (the design page, "Linkage").
///
/// The header is in two parts. The environment, here: the compile-time guard, the barriers that
/// the generated kernels name (KAIRN_DETAIL_UPWARD_BARRIER, KAIRN_DETAIL_UPWARD_PIN), the control
/// register, the scopes, the checks of a checked build, and pass() for T and for the default
/// Interval<T, 1>. Then the interval type, its operations, the functions on arrays and the
/// self-check, which use the first part.
#pragma once

#include "config.hpp"
#include "environment.hpp"
#include "interval.hpp"

#include <cfenv>
#include <cstdint>

// --- The compile-time guard -----------------------------------------------------------------------
//
// @def KAIRN_UPWARD_OPTIONS_UNCHECKED
// Defined by a program, before including this header, to say that it takes the options of the
// rounding mode upward on itself: a compiler the header does not know, or an option set by a
// pragma the header cannot see. It turns off the two rows of the guard below, GCC's and MSVC's,
// and nothing else: config.hpp's refusals (fast-math, finite-math-only, reassociation, ...) hold
// with it. Without the options the compiler may compute operations of the program at compile time
// or move them as if the mode were to nearest; the header's own operations are right on GCC and
// Clang without them (their barriers), but not on MSVC, and a checked build's scope reports a file
// whose build ignores the mode.
//
// - GCC: -frounding-math defines __ROUNDING_MATH__.
// - MSVC (not clang-cl): /fp:strict defines _M_FP_STRICT, and /fp:contract defines _M_FP_CONTRACT
//   (MSVC refuses the two options together; /fp:contract with /fp:precise defines both of theirs).
// - Clang, Apple clang and clang-cl define no macro for -frounding-math or for contraction: the
//   header cannot see them, and never stops the build.
#if !defined(KAIRN_UPWARD_OPTIONS_UNCHECKED)
#if defined(__GNUC__) && !defined(__clang__) && !defined(__ROUNDING_MATH__)
#error "kairn/upward.hpp needs -frounding-math with GCC (the CMake target kairn::upward adds it): without it GCC computes and moves floating-point operations as if the rounding mode were to nearest. Define KAIRN_UPWARD_OPTIONS_UNCHECKED to take the options on yourself (docs/concepts/upward.md)"
#endif
#if defined(_MSC_VER) && !defined(__clang__)
#if defined(_M_FP_CONTRACT)
#error "kairn/upward.hpp does not work with /fp:contract: compile with /fp:strict (the CMake target kairn::upward adds it). Define KAIRN_UPWARD_OPTIONS_UNCHECKED to take the options on yourself (docs/concepts/upward.md)"
#elif !defined(_M_FP_STRICT)
#error "kairn/upward.hpp needs /fp:strict with MSVC (the CMake target kairn::upward adds it): without it MSVC computes and moves floating-point operations as if the rounding mode were to nearest. Define KAIRN_UPWARD_OPTIONS_UNCHECKED to take the options on yourself (docs/concepts/upward.md)"
#endif
#endif
#endif

#if defined(_MSC_VER) && !defined(__clang__)
#include <intrin.h>  // _ReadWriteBarrier; the SSE and AVX intrinsics come with gen/prelude.hpp
// MSVC proper, which has no inline assembly on x64: the barrier per scope (below).
#define KAIRN_DETAIL_UPWARD_MSVC 1
#endif

// --- The barriers -----------------------------------------------------------------------------------
//
// KAIRN_DETAIL_UPWARD_BARRIER(v), on a variable v of a floating-point or a vector type (T, or a
// register of two or more lanes: __m128d, __m128, __m256d, __m256; float64x2_t, float32x2_t,
// float32x4_t): on GCC and Clang (clang-cl included) an empty assembly statement that takes v as an
// input and an output. It emits no instruction, and the compiler must assume that it reads v and
// changes it: no operation on v is folded at compile time, merged with the same operation before a
// change of mode, or moved across another volatile assembly statement, the scopes' among them
// (volatile assembly statements keep their order). The register class is that of the vector
// registers: "x" on x86 (xmm, or ymm for a 256-bit type), "w" on AArch64; on another target "m",
// a round trip through memory. On MSVC it is nothing: there the barrier is per scope.
//
// KAIRN_DETAIL_UPWARD_PIN(v): what a generated kernel applies to its first input. On GCC and Clang
// the barrier itself. On MSVC an OR with kairn::upward::detail::zero, the zero that each scope reads
// from a volatile object after it writes the mode (refresh_zero, below): one load and one OR, and
// every operation of the kernel that rounds depends on that input (rule U6 of the design page), so
// it depends on a volatile read made after the mode was written, and cannot be folded, merged
// with an operation before the scope, or moved above the scope. In the two-number form of a
// kernel, the printer pins each of the two numbers of the first input.
//
// KAIRN_DETAIL_UPWARD_FENCE(): the barrier at both ends of a scope, an empty assembly statement
// that clobbers memory (GCC, Clang), _ReadWriteBarrier() (MSVC): no load or store of memory crosses
// it.
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
#define KAIRN_DETAIL_UPWARD_BARRIER(v) ((void)(v))
#define KAIRN_DETAIL_UPWARD_PIN(v) ::kairn::upward::detail::pin(v)
#define KAIRN_DETAIL_UPWARD_FENCE() _ReadWriteBarrier()
#else
#if defined(__x86_64__) || defined(__i386__)
#define KAIRN_DETAIL_UPWARD_BARRIER(v) __asm__ __volatile__("" : "+x"(v))
#elif defined(__aarch64__)
#define KAIRN_DETAIL_UPWARD_BARRIER(v) __asm__ __volatile__("" : "+w"(v))
#else
#define KAIRN_DETAIL_UPWARD_BARRIER(v) __asm__ __volatile__("" : "+m"(v))
#endif
#define KAIRN_DETAIL_UPWARD_PIN(v) KAIRN_DETAIL_UPWARD_BARRIER(v)
#define KAIRN_DETAIL_UPWARD_FENCE() __asm__ __volatile__("" ::: "memory")
#endif

// A function of this file's own that is never inlined and that the compiler does not analyze from
// its callers (GCC's noipa: no constant result propagated, no "const" inferred, so that a call is
// never moved above a scope's write of the mode): the check of the build below.
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
#define KAIRN_DETAIL_UPWARD_OPAQUE __declspec(noinline)
#elif defined(__clang__)
#define KAIRN_DETAIL_UPWARD_OPAQUE __attribute__((noinline))
#else
#define KAIRN_DETAIL_UPWARD_OPAQUE __attribute__((noipa))
#endif

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::upward {

namespace detail {

// --- The control register ---------------------------------------------------------------------------
//
// The state a scope reads and writes: MXCSR on x86 (32 bits), FPCR on AArch64 with GCC or Clang;
// elsewhere the rounding mode of the C library (std::fegetround), and nothing else. The fields:
// - MXCSR: the rounding control RC in bits 13-14 (upward 10, nearest 00), flush to zero in bit 15
//   and denormals-are-zero in bit 6, the exception flags in bits 0-5;
// - FPCR: the rounding mode RMode in bits 22-23 (upward 01, nearest 00), flush to zero FZ in bit
//   24, and where FEAT_AFP is implemented the alternate handling AH in bit 1 and the flush of inputs
//   FIZ in bit 0 (otherwise both read as zero, and are written as zero); the exception flags are in
//   FPSR, which no scope reads or writes.
#if defined(KAIRN_DETAIL_MXCSR)
using control_t = std::uint32_t;
inline constexpr control_t rounding_field = 0x6000u;
inline constexpr control_t rounding_upward = 0x4000u;
inline constexpr control_t rounding_nearest = 0;
inline constexpr control_t flush_field = 0x8040u;
inline constexpr control_t exception_flags = 0x003Fu;
#elif defined(KAIRN_DETAIL_FPCR)
using control_t = std::uint64_t;
inline constexpr control_t rounding_field = control_t{3} << 22;
inline constexpr control_t rounding_upward = control_t{1} << 22;
inline constexpr control_t rounding_nearest = 0;
inline constexpr control_t flush_field = (control_t{1} << 24) | control_t{3};
inline constexpr control_t exception_flags = 0;
#else
using control_t = int;
#endif

#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
// One read of the control register.
KAIRN_FORCEINLINE control_t read_control() noexcept {
#if defined(KAIRN_DETAIL_MXCSR)
    return _mm_getcsr();
#elif defined(__clang__)
    return __builtin_arm_rsr64("fpcr");
#else
    return __builtin_aarch64_get_fpcr64();
#endif
}
#endif

#if defined(KAIRN_DETAIL_UPWARD_MSVC)
// The write of MXCSR in a function of its own that is never inlined, on entry and on exit of every
// scope (the design page, "MSVC"): with an inline _mm_setcsr MSVC compiled the loop of the function
// that held the scope markedly slower. Its result does not depend on the options of a file, so it
// is one function of the program (external linkage), as an inline function is.
__declspec(noinline) inline void write_mxcsr(unsigned int v) noexcept { _mm_setcsr(v); }

// The barrier per scope (the design page, "MSVC"). zero_source is a volatile object that holds 0;
// zero, one per thread and the same in every file of a module (an inline thread_local, of external
// linkage), holds what the most recent scope of the thread read from it after writing the mode, a
// register whose lanes are all zero, but which the compiler cannot know. Each module of Windows (a
// program, a DLL) has its own copy of both.
inline volatile int zero_source = 0;
inline thread_local __m128d zero = {};

// The refresh: zero read again from the volatile object, after the scope's write of the mode (or
// its read, when nothing changes) and its barrier. Every pin that follows depends on this read.
KAIRN_FORCEINLINE void refresh_zero() noexcept { zero = _mm_castsi128_pd(_mm_cvtsi32_si128(zero_source)); }

// The pin, KAIRN_DETAIL_UPWARD_PIN: v ORed with zero, the same bits.
KAIRN_FORCEINLINE void pin(__m128d& v) noexcept { v = _mm_or_pd(v, zero); }
KAIRN_FORCEINLINE void pin(__m128& v) noexcept { v = _mm_or_ps(v, _mm_castpd_ps(zero)); }
KAIRN_FORCEINLINE void pin(double& v) noexcept { v = _mm_cvtsd_f64(_mm_or_pd(_mm_set_sd(v), zero)); }
KAIRN_FORCEINLINE void pin(float& v) noexcept { v = _mm_cvtss_f32(_mm_or_ps(_mm_set_ss(v), _mm_castpd_ps(zero))); }
#if defined(__AVX__)
KAIRN_FORCEINLINE void pin(__m256d& v) noexcept { v = _mm256_or_pd(v, _mm256_broadcast_pd(&zero)); }
KAIRN_FORCEINLINE void pin(__m256& v) noexcept { v = _mm256_or_ps(v, _mm256_castpd_ps(_mm256_broadcast_pd(&zero))); }
#endif
#endif

#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
// One write of the control register.
KAIRN_FORCEINLINE void write_control(control_t v) noexcept {
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
    write_mxcsr(v);
#elif defined(KAIRN_DETAIL_MXCSR)
    _mm_setcsr(v);
#elif defined(__clang__)
    __builtin_arm_wsr64("fpcr", v);
#else
    __builtin_aarch64_set_fpcr64(v);
#endif
}
#endif

// --- The checks of a checked build (KAIRN_CHECKS) -----------------------------------------------------
//
// The report of a check of this header, through KAIRN_ENVIRONMENT_FAILURE (config.hpp), as
// kairn::detail::report_environment reports the default types' checks: a function of its own that
// the compiler is asked never to inline and to place with the code that rarely runs, so that a
// check costs its caller one read of the register, a test and a call on the path not taken. An
// inline function, one copy per program: the reason a program defines the macro the same way in
// every file.
KAIRN_DETAIL_COLD inline void report(const char* reason) noexcept { KAIRN_ENVIRONMENT_FAILURE(reason); }

// What a state of the control register differs in from the one an operation that rounds upward
// needs (the mode upward, flush to zero and denormals-are-zero off), in words; with rounding false
// only flush to zero (an exact operation: a comparison reads a subnormal operand as zero under it).
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
KAIRN_DETAIL_COLD inline void report_state(control_t state, bool rounding) noexcept {
    const char* reason = "the floating-point environment is not the one the round-up interval needs";
    if (rounding && (state & rounding_field) != rounding_upward) {
        reason = "an operation of kairn/upward.hpp that rounds runs where the rounding mode is not upward: outside a "
                 "kairn::upward::Scope, or inside a kairn::upward::NearestScope";
    } else if (const char* flush = ::kairn::detail::environment_message(state & flush_field)) {
        reason = flush;
    }
    report(reason);
}
#endif

// The assertion before each operation of this header that rounds, in a checked build only (the
// design page, "Checks"): the mode is upward, and flush to zero and denormals-are-zero are off.
// One read of the register and one test; the report out of line. Whether the checks of the
// operands may follow: false when the state is not that and KAIRN_ENVIRONMENT_FAILURE returned.
// Always true without the checks, where nothing is read. The report is the last statement of its
// branch: MSVC refuses a statement after a call that does not return (C4702, an error with /WX).
KAIRN_FORCEINLINE bool check_upward() noexcept {
    bool ok = true;
#if KAIRN_CHECKS
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
    const control_t state = read_control();
    if ((state & (rounding_field | flush_field)) != rounding_upward) [[unlikely]] {
        ok = false;
        report_state(state, true);
    }
#else
    if (std::fegetround() != FE_UPWARD) [[unlikely]] {
        ok = false;
        report("an operation of kairn/upward.hpp that rounds runs where the rounding mode is not upward: outside a "
               "kairn::upward::Scope, or inside a kairn::upward::NearestScope");
    }
#endif
#endif
    return ok;
}

// The same before each exact operation (a sign change, a comparison, a selection, a NaN test),
// whose result is the same in every rounding mode: only flush to zero and denormals-are-zero,
// which make a comparison read a subnormal operand as zero. Nothing is checked on a target without
// either register.
KAIRN_FORCEINLINE bool check_exact() noexcept {
    bool ok = true;
#if KAIRN_CHECKS && (defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR))
    const control_t state = read_control();
    if ((state & flush_field) != 0) [[unlikely]] {
        ok = false;
        report_state(state, false);
    }
#endif
    return ok;
}

// The check that this file's build honors the mode, made on entry of an upward scope that wrote the
// mode, in a checked build only: 1 + 2^-60 > 1 on literal operands, true under the mode upward when
// the sum is computed at run time, and false when the compiler computed it at compile time, to
// nearest, as a build without the options does (GCC and Clang without -frounding-math, MSVC without
// /fp:strict). A function of this file's own (internal linkage), compiled with its options, never
// inlined, called after the scope's barrier. It protects the program's own arithmetic in the scope,
// not the header's, which its barriers make right: so it is an assertion, made in a checked build
// only (the owner's decision of 2026-11-24 for this header: the checks that are not strictly needed
// are assertions).
namespace {
KAIRN_DETAIL_UPWARD_OPAQUE inline bool build_honors_mode() noexcept {
    const double one = 1.0, tiny = 0x1p-60;
    // A comparison of constants on purpose: a build that folds it while it compiles, to nearest, is
    // what the check reports. MSVC's code analysis warns of such a comparison (C6326), which here
    // is no fault.
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
#pragma warning(suppress : 6326)
#endif
    return one + tiny > one;
}
}  // namespace

// --- The scopes -------------------------------------------------------------------------------------

enum class Direction { upward, nearest };

namespace {

// The work of every scope (the design page, "The scopes"), for the mode of D; with Library, the
// C library's mode as well (the scopes of the program), without it the register only (the scope
// that the functions on arrays hold).
//
// Entry: one read of the control register; the state wanted, the mode of D with flush to zero and
// denormals-are-zero off and every other bit as read; one write, only when that differs from what
// was read, so that a scope inside one of the same mode costs one read. With Library on x86, also
// std::fesetround when std::fegetround() reports another mode: the C library may read its own
// state there (glibc reads the x87 control word), and the program's code may ask it. On AArch64
// the register is the C library's state and nothing more is done; on a target with neither
// register, the C library's mode is the whole state. Then the barrier; then, on MSVC, the refresh;
// then, in a checked build and when an upward scope wrote the mode, the check of the build.
//
// Exit: the barrier; the C library's mode restored if the entry changed it; the register restored
// if the entry wrote it, or if the entry changed the C library's mode (glibc's std::fesetround
// writes the rounding control of MXCSR too), keeping the exception flags raised inside (MXCSR's
// bits 0-5 carried over; on AArch64 they are in FPSR, which no scope touches); then, on MSVC, when
// the exit wrote, the refresh again, so that an operation after the end of a NearestScope inside an
// upward one, or a value passed out of an upward scope, depends on a read made after the restoring
// write.
template <Direction D, bool Library>
class BasicScope {
public:
    KAIRN_FORCEINLINE BasicScope() noexcept {
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
        saved_ = read_control();
        const control_t want = (saved_ & ~(rounding_field | flush_field)) | mode_bits;
        wrote_ = want != saved_;
        if (wrote_) write_control(want);
#if defined(KAIRN_DETAIL_MXCSR)
        if constexpr (Library) {
            library_saved_ = std::fegetround();
            if (library_saved_ != library_mode) library_changed_ = std::fesetround(library_mode) == 0;
        }
#endif
#else
        saved_ = std::fegetround();
        wrote_ = saved_ != library_mode && std::fesetround(library_mode) == 0;
#endif
        KAIRN_DETAIL_UPWARD_FENCE();
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
        refresh_zero();
#endif
#if KAIRN_CHECKS
        if constexpr (D == Direction::upward) {
            if (wrote_ && !build_honors_mode()) [[unlikely]]
                report("this file was compiled so that floating-point operations of the program ignore the rounding "
                       "mode: 1 + 2^-60 is 1 in an upward scope (GCC and Clang need -frounding-math, MSVC /fp:strict; "
                       "the CMake target kairn::upward adds them)");
        }
#endif
    }

    KAIRN_FORCEINLINE ~BasicScope() {
        KAIRN_DETAIL_UPWARD_FENCE();
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
        bool restore = wrote_;
#if defined(KAIRN_DETAIL_MXCSR)
        if constexpr (Library) {
            if (library_changed_) {
                std::fesetround(library_saved_);
                restore = true;
            }
        }
#endif
        if (restore) {
#if defined(KAIRN_DETAIL_MXCSR)
            write_control((saved_ & ~exception_flags) | (read_control() & exception_flags));
#else
            write_control(saved_);
#endif
#if defined(KAIRN_DETAIL_UPWARD_MSVC)
            refresh_zero();
#endif
        }
#else
        if (wrote_) std::fesetround(saved_);
#endif
    }

    BasicScope(const BasicScope&) = delete;
    BasicScope& operator=(const BasicScope&) = delete;

private:
    static constexpr int library_mode = D == Direction::upward ? FE_UPWARD : FE_TONEAREST;
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
    static constexpr control_t mode_bits = D == Direction::upward ? rounding_upward : rounding_nearest;
#endif
    control_t saved_;
    bool wrote_;
#if defined(KAIRN_DETAIL_MXCSR)
    int library_saved_ = 0;
    bool library_changed_ = false;
#endif
};

// The scope that each function on arrays holds for its call: upward, the register only (the C
// library's mode is not set), with the same check of the build in a checked build.
using RegisterScope = BasicScope<Direction::upward, false>;

}  // namespace
}  // namespace detail

namespace {

/// Sets the rounding mode upward for its lifetime, the one environment in which the operations of
/// this header that round are right; restores what it found when it ends.
///
/// On entry it reads the control register (MXCSR on x86-64, FPCR on AArch64) and writes it only
/// when something must change: the mode upward, flush to zero and denormals-are-zero off. A Scope
/// inside another (or inside a function's own) costs one read. It also sets the C library's mode
/// (std::fesetround) when std::fegetround() reports another one, so that the program's own code
/// sees upward there too. On exit it restores both, keeping the exception flags raised inside.
/// Barriers at both ends keep the operations of this header inside it. In a checked build
/// (KAIRN_CHECKS 1), an entry that writes the mode also checks that this file's build honors it,
/// and reports through KAIRN_ENVIRONMENT_FAILURE a file compiled without the options.
///
/// Each thread holds its own scope: the mode is per thread, and a thread started inside a scope
/// may or may not inherit it. Code without barriers (the program's own, the default types) can be
/// moved across a scope's boundary: bring values in and out through memory, to_interval() or
/// kairn::upward::pass(). Internal linkage: each file compiles its own. Not copyable, not movable.
class [[nodiscard]] Scope {
public:
    /// Sets the rounding mode upward, flush to zero and denormals-are-zero off.
    Scope() noexcept = default;
    /// Restores the control register and the C library's mode as the constructor found them, but for
    /// the exception flags raised inside, which are kept.
    ~Scope() = default;
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;

private:
    detail::BasicScope<detail::Direction::upward, true> scope_;
};

/// Sets the rounding mode to nearest for its lifetime, with flush to zero and denormals-are-zero
/// off, and restores what it found when it ends, as Scope does for upward: how a program calls the
/// default Kairn types, or code that assumes rounding to nearest, inside an upward region. Values
/// computed before it begins, in registers, are brought in through memory or kairn::upward::pass().
/// Internal linkage. Not copyable, not movable.
class [[nodiscard]] NearestScope {
public:
    /// Sets the rounding mode to nearest, flush to zero and denormals-are-zero off.
    NearestScope() noexcept = default;
    /// Restores the control register and the C library's mode as the constructor found them, but for
    /// the exception flags raised inside, which are kept.
    ~NearestScope() = default;
    NearestScope(const NearestScope&) = delete;
    NearestScope& operator=(const NearestScope&) = delete;

private:
    detail::BasicScope<detail::Direction::nearest, true> scope_;
};

// --- Values that cross a scope's boundary -----------------------------------------------------------

/// v, after a barrier: a computation on the result happens after the most recent boundary of a
/// scope (on MSVC, after the refresh of the most recent scope that wrote the mode), for a value
/// that crosses a scope's boundary into code that has no barrier: a value computed before a
/// NearestScope and used by the default types inside it, or one computed in an upward scope and
/// used after it. The same bits. Internal linkage.
template <class T>
    requires ::kairn::detail::limb<T>
KAIRN_FORCEINLINE T pass(T v) noexcept {
    KAIRN_DETAIL_UPWARD_PIN(v);
    return v;
}

/// The same for a default interval of one limb: the same bounds, each after a barrier.
template <class T>
KAIRN_FORCEINLINE ::kairn::Interval<T, 1> pass(const ::kairn::Interval<T, 1>& x) noexcept {
    T lo = x.lower().limb[0], hi = x.upper().limb[0];
    KAIRN_DETAIL_UPWARD_PIN(lo);
    KAIRN_DETAIL_UPWARD_PIN(hi);
    return ::kairn::Interval<T, 1>(::kairn::detail::kernel_result, ::kairn::Expansion<T, 1>(lo),
                                   ::kairn::Expansion<T, 1>(hi));
}

}  // namespace
}  // namespace kairn::upward
KAIRN_GEN_POP_WARNINGS

// ==================================================================================================
// The second part: the interval type, its operations, the functions on arrays and the self-check
// (the design page, "The interface" and "The self-check"). Requires the rounding mode upward set by
// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
// MSVC /fp:strict) for every operation that rounds.
//
// Every operation forwards to one generated kernel of gen/upward.hpp, included here after the
// barriers it names, or composes them as the design page says (x - t, t - x, contains(y)). The
// linkage (the design page, "Linkage"): kairn::upward::Interval<T> and kairn::upward::View<T> have
// external linkage, so that a program passes them between files, and every member function of
// Interval computes only exact operations (sign changes, comparisons, selections, NaN tests), the
// same under every option config.hpp accepts and every mode; every operation that rounds (the
// arithmetic operators, with an interval and with a number) is a static function template of
// kairn::upward, found by argument-dependent lookup, and pass(), the functions on arrays and
// self_test() are in an unnamed namespace: each file compiles its own copy, with its own options.
// The class holds the register type of gen/upward.hpp, of a named namespace.
//
// Like the default types, an operation compiles without the kairn::unverified marker only when
// gen/upward.hpp says that its kernel is proved (kairn::gen::upward::bounds::K<T>::proved, from
// gen/claims.json); with the marker on an operand it compiles in every state: kairn::unverified(x)
// + y, x.hull(kairn::unverified(y)), Interval<T>(kairn::unverified(lo), hi). The members without
// an operand (is_empty(), lower(), to_interval(), ...) are reached on the marked interval itself,
// kairn::unverified(x).is_empty(), and the functions on arrays on a marked first input,
// kairn::upward::add(z, kairn::unverified(x), y).
// ==================================================================================================

#include "gen/upward.hpp"

#include <bit>
#include <cstddef>
#include <limits>
#include <type_traits>

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::upward {

template <class T>
class Interval;
template <class T>
struct View;

namespace detail {

// The kernels of gen/upward.hpp, their register type and their statuses.
namespace kernels = ::kairn::gen::upward;
namespace status = ::kairn::gen::upward::bounds;
template <class T>
using pair = kernels::pair<T>;

// Whether kernel K of gen/upward.hpp is proved for T: the constraint of every operation that
// compiles without kairn::unverified, as kairn::detail::proof_checked is for the default types.
template <template <class> class K, class T>
concept proved = K<T>::proved;

// The register of an interval, which only the functions of this header read and write: a struct of
// external linkage whose members copy and nothing else.
struct raw_t {
    explicit raw_t() = default;
};
inline constexpr raw_t raw{};
struct access {
    template <class T>
    static KAIRN_FORCEINLINE pair<T> get(const Interval<T>& x) noexcept {
        return x.v_;
    }
    template <class T>
    static KAIRN_FORCEINLINE Interval<T> make(const pair<T>& v) noexcept {
        return Interval<T>(raw, v);
    }
};

// --- Canonical states -----------------------------------------------------------------------------

// Whether v is a quiet NaN: exponent all ones and the first bit of the fraction set.
template <class T>
KAIRN_FORCEINLINE bool quiet_nan(T v) noexcept {
    if constexpr (sizeof(T) == 8) {
        return (std::bit_cast<std::uint64_t>(v) & 0x7ff8000000000000u) == 0x7ff8000000000000u;
    } else {
        return (std::bit_cast<std::uint32_t>(v) & 0x7fc00000u) == 0x7fc00000u;
    }
}

// Whether (u, n) is a canonical state (the design page, "States"): the empty set, two quiet NaNs;
// or neither lane a NaN, neither -inf, and -n <= u. Comparisons, a bit test and a sign change, all
// exact; a comparison reads a subnormal lane as zero under flush to zero, which the callers check
// first (check_exact, check_upward).
template <class T>
KAIRN_FORCEINLINE bool canonical(T u, T n) noexcept {
    if (u != u || n != n) return quiet_nan(u) && quiet_nan(n);
    constexpr T inf = std::numeric_limits<T>::infinity();
    return u > -inf && n > -inf && -n <= u;
}
template <class T>
KAIRN_FORCEINLINE bool canonical(const Interval<T>& x) noexcept {
    const pair<T> v = access::get(x);
    return canonical(kernels::pair_upper(v), kernels::pair_nlower(v));
}

// --- The checks of a checked build (KAIRN_CHECKS) ---------------------------------------------------
//
// Before each operation that rounds, check_upward() (the mode upward, flush to zero and
// denormals-are-zero off), before each exact one check_exact() (flush to zero and
// denormals-are-zero off), then each interval operand canonical; every report through
// KAIRN_ENVIRONMENT_FAILURE (report, above), out of line. The operands are not checked when the
// environment is not the one asked and KAIRN_ENVIRONMENT_FAILURE returned. Nothing without the
// checks. Each report is the last statement of its branch (MSVC's C4702).

KAIRN_DETAIL_COLD inline void report_operand() noexcept {
    report("an interval given to an operation of kairn/upward.hpp is not canonical: its stored pair (u, n) is "
           "neither the empty set (NaN, NaN), both quiet, nor (b, -a) of an interval [a, b] (no NaN, no lane -inf, "
           "-n <= u), so no guarantee applies to the result");
}
KAIRN_DETAIL_COLD inline void report_limbs() noexcept {
    report("kairn::upward::Interval::from_limbs: the limbs (u, n) are not those of a canonical state (the empty set "
           "(NaN, NaN), both quiet, or (b, -a) of an interval [a, b]: no NaN, no lane -inf, -n <= u)");
}
KAIRN_DETAIL_COLD inline void report_default() noexcept {
    report("kairn::upward::Interval(kairn::Interval<T, 1>): the interval converted is not canonical (the empty set "
           "(+inf, -inf), or bounds lo <= hi, neither a NaN, with lo < +inf and hi > -inf)");
}
KAIRN_DETAIL_COLD inline void report_lengths() noexcept {
    report("a function on arrays of kairn/upward.hpp: the views have different lengths (the shortest is used)");
}
KAIRN_DETAIL_COLD inline void report_overlap() noexcept {
    report("a function on arrays of kairn/upward.hpp: an array written overlaps an array read, or the other array "
           "written (only the same view, in place, may be both written and read)");
}
KAIRN_DETAIL_COLD inline void report_element() noexcept {
    report("a function on arrays of kairn/upward.hpp: an element (upper[i], nlower[i]) of a view read is not a "
           "canonical state, so no guarantee applies to the result");
}

template <class T>
KAIRN_FORCEINLINE void check_rounding([[maybe_unused]] const Interval<T>& x) noexcept {
#if KAIRN_CHECKS
    if (check_upward() && !canonical(x)) report_operand();
#endif
}
template <class T>
KAIRN_FORCEINLINE void check_rounding([[maybe_unused]] const Interval<T>& x,
                                      [[maybe_unused]] const Interval<T>& y) noexcept {
#if KAIRN_CHECKS
    if (check_upward() && !(canonical(x) && canonical(y))) report_operand();
#endif
}
template <class T>
KAIRN_FORCEINLINE void check_operand([[maybe_unused]] const Interval<T>& x) noexcept {
#if KAIRN_CHECKS
    if (check_exact() && !canonical(x)) report_operand();
#endif
}
template <class T>
KAIRN_FORCEINLINE void check_operands([[maybe_unused]] const Interval<T>& x,
                                      [[maybe_unused]] const Interval<T>& y) noexcept {
#if KAIRN_CHECKS
    if (check_exact() && !(canonical(x) && canonical(y))) report_operand();
#endif
}

// --- The exact operations, one kernel each (external linkage: the same in every file) -------------

// The interval of two values of T (upward_make_1): every pair of values is accepted.
template <class T>
KAIRN_FORCEINLINE Interval<T> make(T lo, T hi) noexcept {
    check_exact();
    pair<T> z{};
    kernels::upward_make_1(lo, hi, z);
    return access::make<T>(z);
}
// The state of a canonical default interval (upward_from_interval_1).
template <class T>
KAIRN_FORCEINLINE Interval<T> from_interval(const ::kairn::Interval<T, 1>& x) noexcept {
#if KAIRN_CHECKS
    if (check_exact() && !::kairn::detail::canonical_interval(x.lower(), x.upper())) report_default();
#endif
    pair<T> z{};
    kernels::upward_from_interval_1(x.lower().limb[0], x.upper().limb[0], z);
    return access::make<T>(z);
}
// The bounds of the default interval of the same set (upward_to_interval_1): of a nonempty interval
// its lower and upper bound, +inf and -inf for the empty set.
template <class T>
KAIRN_FORCEINLINE void bounds(const Interval<T>& x, T& lo, T& hi) noexcept {
    check_operand(x);
    kernels::upward_to_interval_1(access::get(x), lo, hi);
}
// The default interval, its bounds after a barrier (on MSVC the pin of the most recent scope), so
// that a computation of the default types on the result happens after the most recent boundary of
// a scope (the design page, "Code around a scope").
template <class T>
KAIRN_FORCEINLINE ::kairn::Interval<T, 1> to_interval(const Interval<T>& x) noexcept {
    T lo = T(0), hi = T(0);
    bounds(x, lo, hi);
    KAIRN_DETAIL_UPWARD_PIN(lo);
    KAIRN_DETAIL_UPWARD_PIN(hi);
    return ::kairn::Interval<T, 1>(::kairn::detail::kernel_result, ::kairn::Expansion<T, 1>(lo),
                                   ::kairn::Expansion<T, 1>(hi));
}
template <class T>
KAIRN_FORCEINLINE T lower(const Interval<T>& x) noexcept {
    T lo = T(0), hi = T(0);
    bounds(x, lo, hi);
    return lo;
}
template <class T>
KAIRN_FORCEINLINE T upper(const Interval<T>& x) noexcept {
    T lo = T(0), hi = T(0);
    bounds(x, lo, hi);
    return hi;
}
// -X (upward_neg_1): the lanes exchanged.
template <class T>
KAIRN_FORCEINLINE Interval<T> neg(const Interval<T>& x) noexcept {
    check_operand(x);
    pair<T> z{};
    kernels::upward_neg_1(access::get(x), z);
    return access::make<T>(z);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> hull(const Interval<T>& x, const Interval<T>& y) noexcept {
    check_operands(x, y);
    pair<T> z{};
    kernels::upward_hull_1(access::get(x), access::get(y), z);
    return access::make<T>(z);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> intersection(const Interval<T>& x, const Interval<T>& y) noexcept {
    check_operands(x, y);
    pair<T> z{};
    kernels::upward_intersection_1(access::get(x), access::get(y), z);
    return access::make<T>(z);
}
// The predicates, each one kernel with one mask.
#define KAIRN_DETAIL_UPWARD_PREDICATE(NAME, KERNEL)                \
    template <class T>                                             \
    KAIRN_FORCEINLINE bool NAME(const Interval<T>& x) noexcept {   \
        check_operand(x);                                          \
        bool m = false;                                            \
        kernels::KERNEL(access::get(x), m);                        \
        return m;                                                  \
    }
KAIRN_DETAIL_UPWARD_PREDICATE(is_empty, upward_empty_1)
KAIRN_DETAIL_UPWARD_PREDICATE(is_whole, upward_entire_1)
KAIRN_DETAIL_UPWARD_PREDICATE(positive, upward_positive_1)
KAIRN_DETAIL_UPWARD_PREDICATE(negative, upward_negative_1)
KAIRN_DETAIL_UPWARD_PREDICATE(is_zero, upward_zero_1)
#undef KAIRN_DETAIL_UPWARD_PREDICATE
// Whether t is a member of X (upward_contains_1): every value of T is accepted.
template <class T>
KAIRN_FORCEINLINE bool contains(const Interval<T>& x, T t) noexcept {
    check_operand(x);
    bool m = false;
    kernels::upward_contains_1(access::get(x), t, m);
    return m;
}
// Whether X is a subset of Y (upward_subset_1(x, y)): Y.contains(X).
template <class T>
KAIRN_FORCEINLINE bool subset(const Interval<T>& x, const Interval<T>& y) noexcept {
    check_operands(x, y);
    bool m = false;
    kernels::upward_subset_1(access::get(x), access::get(y), m);
    return m;
}
// The relations of two intervals, each one kernel with one mask, and the three-valued comparisons,
// each one kernel with the two masks of a Trit.
#define KAIRN_DETAIL_UPWARD_RELATION(NAME, KERNEL)                                        \
    template <class T>                                                                    \
    KAIRN_FORCEINLINE bool NAME(const Interval<T>& x, const Interval<T>& y) noexcept {    \
        check_operands(x, y);                                                             \
        bool m = false;                                                                   \
        kernels::KERNEL(access::get(x), access::get(y), m);                               \
        return m;                                                                         \
    }
KAIRN_DETAIL_UPWARD_RELATION(rel_equal, upward_rel_equal_1)
KAIRN_DETAIL_UPWARD_RELATION(rel_interior, upward_rel_interior_1)
KAIRN_DETAIL_UPWARD_RELATION(rel_disjoint, upward_rel_disjoint_1)
#undef KAIRN_DETAIL_UPWARD_RELATION
#define KAIRN_DETAIL_UPWARD_COMPARISON(NAME, KERNEL)                                                 \
    template <class T>                                                                               \
    KAIRN_FORCEINLINE ::kairn::Trit NAME(const Interval<T>& x, const Interval<T>& y) noexcept {      \
        check_operands(x, y);                                                                        \
        bool yes = false, no = false;                                                                \
        kernels::KERNEL(access::get(x), access::get(y), yes, no);                                    \
        return ::kairn::detail::trit(yes, no);                                                       \
    }
KAIRN_DETAIL_UPWARD_COMPARISON(less, upward_less_1)
KAIRN_DETAIL_UPWARD_COMPARISON(less_equal, upward_less_equal_1)
KAIRN_DETAIL_UPWARD_COMPARISON(equal, upward_equal_1)
#undef KAIRN_DETAIL_UPWARD_COMPARISON
template <class T>
KAIRN_FORCEINLINE ::kairn::Trit greater(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::less(y, x);
}
template <class T>
KAIRN_FORCEINLINE ::kairn::Trit greater_equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::less_equal(y, x);
}
template <class T>
KAIRN_FORCEINLINE ::kairn::Trit not_equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return ::kairn::detail::opposite(detail::equal(x, y));
}
template <class T>
KAIRN_FORCEINLINE ::kairn::Trit member(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::contains(x, t) ? ::kairn::Trit::yes : ::kairn::Trit::no;
}

// --- The operations that round (internal linkage: each file compiles its own) ----------------------
//
// The compositions of the design page, "The kernels": x - t is x + (-t), t - x is -(x + (-t)), each
// a proved kernel and an exact negation, argued and not machine-checked as one statement; t + x and
// t x are the kernels with the operands exchanged. The number t passes through a barrier before it
// is negated, so that a product of the program that computed it is not rewritten with the negation.
namespace {
#define KAIRN_DETAIL_UPWARD_ROUNDED(NAME, KERNEL)                                                    \
    template <class T>                                                                               \
    KAIRN_FORCEINLINE Interval<T> NAME(const Interval<T>& x, const Interval<T>& y) noexcept {        \
        check_rounding(x, y);                                                                        \
        pair<T> z{};                                                                                 \
        kernels::KERNEL(access::get(x), access::get(y), z);                                          \
        return access::make<T>(z);                                                                      \
    }
KAIRN_DETAIL_UPWARD_ROUNDED(add, upward_add_1)
KAIRN_DETAIL_UPWARD_ROUNDED(sub, upward_sub_1)
KAIRN_DETAIL_UPWARD_ROUNDED(mul, upward_mul_1)
#undef KAIRN_DETAIL_UPWARD_ROUNDED
template <class T>
KAIRN_FORCEINLINE Interval<T> add(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    check_rounding(x);
    pair<T> z{};
    kernels::upward_add_num_1(access::get(x), t, z);
    return access::make<T>(z);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> add(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::add<T>(x, t);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> sub(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    T nt = t;
    KAIRN_DETAIL_UPWARD_BARRIER(nt);
    nt = -nt;
    return detail::add<T>(x, nt);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> sub(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::neg(detail::sub<T>(x, t));
}
template <class T>
KAIRN_FORCEINLINE Interval<T> mul(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    check_rounding(x);
    pair<T> z{};
    kernels::upward_mul_num_1(access::get(x), t, z);
    return access::make<T>(z);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> mul(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::mul<T>(x, t);
}
}  // namespace

}  // namespace detail

// --- The type -------------------------------------------------------------------------------------

/// An interval of float or double kept as two numbers of T in one register and computed under the
/// rounding mode upward: an opt-in alternative to kairn::Interval<T, 1>, used only for speed
/// (the design page, docs/developer/design/upward.md). Requires the rounding mode upward set by
/// kairn::upward::Scope and the options of docs/concepts/upward.md (GCC and Clang -frounding-math,
/// MSVC /fp:strict) for every operation that rounds.
///
/// A value is the pair (u, n) = (b, -a) of an interval [a, b], lane 0 (first in memory) the upper
/// bound and lane 1 the lower bound negated (the design page, "States"): a nonempty interval has no
/// NaN lane, no lane -inf and -n <= u; [a, +inf], [-inf, b] and the whole line (+inf, +inf) are
/// values; the empty set is (NaN, NaN), both quiet. As for the default interval, the members are
/// real numbers: [1, +inf] does not contain +inf. These are the canonical states; every operation
/// returns one and requires canonical operands (checked when KAIRN_CHECKS is 1).
///
/// Every operation answers every special case as kairn::Interval<T, 1> answers it (the empty set,
/// unbounded intervals, overflow, 0 times infinity), with these differences (the design page,
/// "Differences from the default interval"): the sign of a zero bound is unspecified, and can
/// differ from the default type's and between x86-64 and arm64; a product is exactly rounded in
/// every case, where the default one may be one number of T wider below 2^(2p-1) eta; a number of
/// T is an operand of +, - and * (the default type writes Interval(t)), a t that is infinite or a
/// NaN being the whole line; nothing is constexpr (constant evaluation rounds to nearest); there is
/// no midpoint, radius, split, Ball conversion or bound of two limbs (each needs rounding to
/// nearest: convert with to_interval() outside the scope); the operations that round run only
/// inside an upward scope, while the exact ones (negation, hull, intersection, predicates,
/// comparisons, conversions) give the same result in every mode; from_limbs and to_limbs read and
/// write (u, n), and lower() and upper() return the default type's convention, +inf and -inf for
/// the empty set.
///
/// No conversion between this type and kairn::Interval<T, 1> is implicit, in either direction, and
/// no operation mixes them: Interval<T>(x) and x.to_interval() are the conversions. Copyable;
/// external linkage, so that files pass intervals to one another; every member computes only exact
/// operations.
template <class T>
class Interval {
    static_assert(::kairn::detail::limb<T>, "kairn::upward::Interval<T>: T is float or double");

    using pair_type = detail::pair<T>;
    pair_type v_;

    friend struct detail::access;
    Interval(detail::raw_t, const pair_type& v) noexcept : v_(v) {}

public:
    /// The point 0: [0, 0], the pair (+0, +0). Exact; checks nothing.
    Interval() noexcept : v_(detail::kernels::pair_make(T(0), T(0))) {}
    /// [a, a] (kernel upward_make_1 on (a, a)): the whole line for a NaN or an infinite a, as
    /// Interval<T, 1>(a). Exact.
    Interval(T a) noexcept
        requires detail::proved<detail::status::upward_make_1, T>
        : Interval(detail::make<T>(a, a)) {}
    /// The same with a marked operand: see kairn::Unverified.
    explicit Interval(::kairn::Unverified<T> a) noexcept : Interval(detail::make<T>(a.value, a.value)) {}
    /// The interval of two bounds (kernel upward_make_1), with the cases of Interval<T, 1>(lo, hi):
    /// the whole line when a bound is a NaN and when both are the same infinity, the empty set when
    /// lo > hi, otherwise [lo, hi], the half-lines and the whole line included. Every pair of values
    /// of T is accepted. Exact.
    Interval(T lo, T hi) noexcept
        requires detail::proved<detail::status::upward_make_1, T>
        : Interval(detail::make<T>(lo, hi)) {}
    /// The same with a marked lower bound.
    Interval(::kairn::Unverified<T> lo, T hi) noexcept : Interval(detail::make<T>(lo.value, hi)) {}
    /// The same set as Interval(lo, hi), under the name of kairn::Interval<T, 1>::from_bounds.
    [[nodiscard]] static Interval from_bounds(T lo, T hi) noexcept
        requires detail::proved<detail::status::upward_make_1, T>
    {
        return detail::make<T>(lo, hi);
    }
    /// The same with a marked lower bound.
    [[nodiscard]] static Interval from_bounds(::kairn::Unverified<T> lo, T hi) noexcept {
        return detail::make<T>(lo.value, hi);
    }
    /// The state of the default interval X (kernel upward_from_interval_1): the same set, its empty
    /// set (+inf, -inf) the state (NaN, NaN), [l, h] the pair (h, -l). X must be canonical (checked
    /// when KAIRN_CHECKS is 1). Exact. Explicit: a conversion by name.
    explicit Interval(const ::kairn::Interval<T, 1>& x) noexcept
        requires detail::proved<detail::status::upward_from_interval_1, T>
        : Interval(detail::from_interval(x)) {}
    /// The same with a marked operand.
    explicit Interval(const ::kairn::Unverified<::kairn::Interval<T, 1>>& x) noexcept
        : Interval(detail::from_interval(x.value)) {}

    /// The empty set, (NaN, NaN). Checks nothing.
    [[nodiscard]] static Interval empty() noexcept {
        constexpr T nan = std::numeric_limits<T>::quiet_NaN();
        return detail::access::make<T>(detail::kernels::pair_make(nan, nan));
    }
    /// The whole line, (+inf, +inf). Checks nothing.
    [[nodiscard]] static Interval whole() noexcept {
        constexpr T inf = std::numeric_limits<T>::infinity();
        return detail::access::make<T>(detail::kernels::pair_make(inf, inf));
    }
    /// The interval whose stored pair is (p[0], p[1]) = (u, n), one load of the register: how a
    /// program moves an interval through its own storage (an array of pairs, a GPU buffer).
    /// Precondition: a canonical state, as an operation returns it (checked when KAIRN_CHECKS is
    /// 1, after flush to zero; not otherwise, and then no guarantee applies to the results, with no
    /// undefined behavior). The round trip to_limbs of from_limbs gives every bit back.
    [[nodiscard]] static Interval from_limbs(const T* p) noexcept {
#if KAIRN_CHECKS
        if (detail::check_exact() && !detail::canonical(p[0], p[1])) detail::report_limbs();
#endif
        return detail::access::make<T>(detail::kernels::pair_load(p));
    }
    /// Writes the stored pair (u, n) to p[0] and p[1], one store of the register. Checks nothing.
    void to_limbs(T* p) const noexcept { detail::kernels::pair_store(p, v_); }

    /// The default interval of the same set (kernel upward_to_interval_1): [-n, u], and the empty
    /// set (+inf, -inf) for (NaN, NaN). Exact; its bounds pass through a barrier (on MSVC the pin of
    /// the most recent scope), so that a computation of the default types on the result happens
    /// after the most recent boundary of a scope: the way to bring an interval into a NearestScope
    /// or out of an upward region (the design page, "Code around a scope").
    ::kairn::Interval<T, 1> to_interval() const noexcept
        requires detail::proved<detail::status::upward_to_interval_1, T>
    {
        return detail::to_interval(*this);
    }
    /// The lower bound (kernel upward_to_interval_1): -n, -inf when unbounded below, +inf for the
    /// empty set, as kairn::Interval<T, 1>::lower(). Exact.
    T lower() const noexcept
        requires detail::proved<detail::status::upward_to_interval_1, T>
    {
        return detail::lower(*this);
    }
    /// The upper bound (kernel upward_to_interval_1): u, +inf when unbounded above, -inf for the
    /// empty set. Exact.
    T upper() const noexcept
        requires detail::proved<detail::status::upward_to_interval_1, T>
    {
        return detail::upper(*this);
    }

    /// Whether this is the empty set (kernel upward_empty_1): a NaN lane. Exact.
    bool is_empty() const noexcept
        requires detail::proved<detail::status::upward_empty_1, T>
    {
        return detail::is_empty(*this);
    }
    /// Whether this is the whole line (kernel upward_entire_1): both lanes +inf. Exact.
    bool is_whole() const noexcept
        requires detail::proved<detail::status::upward_entire_1, T>
    {
        return detail::is_whole(*this);
    }
    /// Whether this is a nonempty bounded interval: both lanes finite, from their bit patterns, so
    /// false for the empty set, the whole line and the half-lines. A test written here, as the
    /// default type's, with no kernel, and not machine-checked. Checks nothing.
    bool is_finite() const noexcept {
        return ::kairn::detail::finite(detail::kernels::pair_upper(v_)) &&
               ::kairn::detail::finite(detail::kernels::pair_nlower(v_));
    }
    /// Whether t, a value of T, is a member (kernel upward_contains_1): -n <= t <= u and t finite;
    /// an infinite t or a NaN is a member of no interval, the whole line included. Exact.
    bool contains(T t) const noexcept
        requires detail::proved<detail::status::upward_contains_1, T>
    {
        return detail::contains(*this, t);
    }
    /// The same with a marked point.
    bool contains(::kairn::Unverified<T> t) const noexcept { return detail::contains(*this, t.value); }
    /// Whether Y is a subset of this interval (kernel upward_subset_1 with Y first): the empty set
    /// is a subset of every interval. Only an Interval of the same T. Exact.
    template <class U>
        requires(std::is_same_v<U, T> && detail::proved<detail::status::upward_subset_1, T>)
    bool contains(const Interval<U>& y) const noexcept {
        return detail::subset(y, *this);
    }
    /// The same with a marked operand.
    bool contains(const ::kairn::Unverified<Interval>& y) const noexcept { return detail::subset(y.value, *this); }
    /// Whether every member is positive and the interval is not empty (kernel upward_positive_1):
    /// n < 0. Exact; false for the empty set.
    bool certainly_positive() const noexcept
        requires detail::proved<detail::status::upward_positive_1, T>
    {
        return detail::positive(*this);
    }
    /// Whether every member is negative and the interval is not empty (kernel upward_negative_1):
    /// u < 0. Exact; false for the empty set.
    bool certainly_negative() const noexcept
        requires detail::proved<detail::status::upward_negative_1, T>
    {
        return detail::negative(*this);
    }
    /// Whether the interval is [0, 0] (kernel upward_zero_1). Exact; false for the empty set.
    bool certainly_zero() const noexcept
        requires detail::proved<detail::status::upward_zero_1, T>
    {
        return detail::is_zero(*this);
    }
    /// The hull of this interval and Y (kernel upward_hull_1): the larger lane of each; the hull with
    /// the empty set is the other operand. Exact.
    Interval hull(const Interval& y) const noexcept
        requires detail::proved<detail::status::upward_hull_1, T>
    {
        return detail::hull(*this, y);
    }
    /// The same with a marked operand.
    Interval hull(const ::kairn::Unverified<Interval>& y) const noexcept { return detail::hull(*this, y.value); }
    /// The intersection of this interval and Y (kernel upward_intersection_1): the smaller lane of
    /// each, the empty set when an operand is empty or the lanes cross. Exact.
    Interval intersection(const Interval& y) const noexcept
        requires detail::proved<detail::status::upward_intersection_1, T>
    {
        return detail::intersection(*this, y);
    }
    /// The same with a marked operand.
    Interval intersection(const ::kairn::Unverified<Interval>& y) const noexcept {
        return detail::intersection(*this, y.value);
    }
};

/// A view of n states in two plain arrays, owning nothing: upper[i] and nlower[i] are the stored pair
/// (u, n) of element i, the upper bounds and the negated lower bounds (the design page, "Arrays").
/// T is float or double for a view written, const float or const double for a view read; a view of
/// T converts to a view of const T. External linkage.
template <class T>
struct View {
    static_assert(::kairn::detail::limb<std::remove_const_t<T>>, "kairn::upward::View<T>: T is float or double, or const");
    T* upper;             ///< The upper bounds u.
    T* nlower;            ///< The negated lower bounds n.
    std::size_t size;     ///< The number of elements.
    /// The view of n elements of the two arrays.
    View(T* upper_bounds, T* negated_lower_bounds, std::size_t n) noexcept
        : upper(upper_bounds), nlower(negated_lower_bounds), size(n) {}
    /// A view read of the arrays of a view written.
    template <class U>
        requires(std::is_same_v<const U, T> && !std::is_same_v<U, T>)
    View(const View<U>& v) noexcept : upper(v.upper), nlower(v.nlower), size(v.size) {}
};

}  // namespace kairn::upward

namespace kairn {

/// The marked form of a round-up interval: see kairn::Unverified. The members without an operand,
/// reached on the marked interval itself: kairn::unverified(x).is_empty(), .lower(), ...
template <class T>
struct Unverified<upward::Interval<T>> {
    upward::Interval<T> value;  ///< The operand.
    /// x.to_interval(), x.lower(), x.upper(), x.is_empty(), x.is_whole(), x.certainly_positive(),
    /// x.certainly_negative(), x.certainly_zero() of the operand, in every state of their kernels.
    ::kairn::Interval<T, 1> to_interval() const noexcept { return upward::detail::to_interval(value); }
    T lower() const noexcept { return upward::detail::lower(value); }
    T upper() const noexcept { return upward::detail::upper(value); }
    bool is_empty() const noexcept { return upward::detail::is_empty(value); }
    bool is_whole() const noexcept { return upward::detail::is_whole(value); }
    bool certainly_positive() const noexcept { return upward::detail::positive(value); }
    bool certainly_negative() const noexcept { return upward::detail::negative(value); }
    bool certainly_zero() const noexcept { return upward::detail::is_zero(value); }
};
/// Marks x as an operand of an operation whose proof is not checked yet; see kairn::Unverified.
template <class T>
KAIRN_FORCEINLINE Unverified<upward::Interval<T>> unverified(const upward::Interval<T>& x) noexcept {
    return {x};
}

/// The marked form of a view read by a function on arrays of kairn/upward.hpp.
template <class T>
struct Unverified<upward::View<T>> {
    upward::View<T> value;  ///< The operand.
};
/// Marks the view x, read by a function on arrays (as its first input), as an operand of an
/// operation whose proof is not checked yet; a view of T becomes a view of const T.
template <class T>
KAIRN_FORCEINLINE Unverified<upward::View<const std::remove_const_t<T>>> unverified(const upward::View<T>& x) noexcept {
    return {x};
}

}  // namespace kairn

namespace kairn::upward {

namespace detail {
template <class X>
struct is_upward_t : std::false_type {};
template <class T>
struct is_upward_t<Interval<T>> : std::true_type {};
template <class X>
struct is_upward_t<::kairn::Unverified<X>> : is_upward_t<X> {};
// Whether X is a round-up interval, marked or not.
template <class X>
concept upward_interval = is_upward_t<std::remove_cvref_t<X>>::value;
template <class X, class Y>
concept marked_pair = (::kairn::detail::marked<X> || ::kairn::detail::marked<Y>) && (upward_interval<X> || upward_interval<Y>);
template <class X, class Y>
concept marked_rhs = ::kairn::detail::marked<Y> && !::kairn::detail::marked<X> && upward_interval<X>;
template <class P, class X>
concept marked_member = (::kairn::detail::marked<P> || ::kairn::detail::marked<X>) && !upward_interval<P> && upward_interval<X>;
}  // namespace detail

// --- The operators --------------------------------------------------------------------------------
//
// Function templates, so that no interval operand converts: two intervals of the same T, or an
// interval and a number (std::type_identity_t: a number converts to T). Every operator that rounds
// needs an upward scope (kairn::upward::Scope, or the scope of a function on arrays), and is static,
// of internal linkage: each file compiles its own. A product, sum or difference is, for nonempty
// operands, the tightest interval of T around the exact range: each bound the rounding outward of
// the bound of the exact range ({x op y : x in X, y in Y}, with 0 times infinity 0), in the format
// with overflow; empty exactly when an operand is; for a number t that is infinite or a NaN the
// operand is the whole line, as Interval<T, 1>(t) makes it. The statements are those of the
// kernels' claims (gen/claims.json, docs/reference/).

/// X + Y (kernel upward_add_1): one addition of the two lanes. Rounds.
template <class T>
    requires detail::proved<detail::status::upward_add_1, T>
static KAIRN_FORCEINLINE Interval<T> operator+(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::add(x, y);
}
/// X - Y (kernel upward_sub_1): one addition of X and Y's lanes exchanged. Rounds.
template <class T>
    requires detail::proved<detail::status::upward_sub_1, T>
static KAIRN_FORCEINLINE Interval<T> operator-(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::sub(x, y);
}
/// X * Y (kernel upward_mul_1): four products of two lanes and three maxima, exactly rounded in
/// every case, [0, 0] times every nonempty interval [0, 0]. Rounds.
template <class T>
    requires detail::proved<detail::status::upward_mul_1, T>
static KAIRN_FORCEINLINE Interval<T> operator*(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::mul(x, y);
}
/// X + t and t + X (kernel upward_add_num_1): the whole line for a t that is not finite (the empty
/// set for an empty X). Rounds.
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
static KAIRN_FORCEINLINE Interval<T> operator+(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return detail::add<T>(x, t);
}
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
static KAIRN_FORCEINLINE Interval<T> operator+(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::add<T>(t, x);
}
/// X - t: X + (-t) (kernel upward_add_num_1 and an exact negation). Rounds.
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
static KAIRN_FORCEINLINE Interval<T> operator-(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return detail::sub<T>(x, t);
}
/// t - X: -(X + (-t)) (kernels upward_add_num_1 and upward_neg_1, and an exact negation). Rounds.
template <class T>
    requires(detail::proved<detail::status::upward_add_num_1, T> && detail::proved<detail::status::upward_neg_1, T>)
static KAIRN_FORCEINLINE Interval<T> operator-(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::sub<T>(t, x);
}
/// X * t and t * X (kernel upward_mul_num_1): for a t that is not finite, [0, 0] for X = [0, 0],
/// the empty set for an empty X, the whole line otherwise. Rounds.
template <class T>
    requires detail::proved<detail::status::upward_mul_num_1, T>
static KAIRN_FORCEINLINE Interval<T> operator*(const Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return detail::mul<T>(x, t);
}
template <class T>
    requires detail::proved<detail::status::upward_mul_num_1, T>
static KAIRN_FORCEINLINE Interval<T> operator*(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::mul<T>(t, x);
}
/// -X (kernel upward_neg_1): the lanes exchanged. Exact.
template <class T>
    requires detail::proved<detail::status::upward_neg_1, T>
static KAIRN_FORCEINLINE Interval<T> operator-(const Interval<T>& x) noexcept {
    return detail::neg(x);
}
/// X = X + Y, X = X - Y, X = X * Y, and the same with a number. Round.
template <class T>
    requires detail::proved<detail::status::upward_add_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator+=(Interval<T>& x, const Interval<T>& y) noexcept {
    return x = detail::add(x, y);
}
template <class T>
    requires detail::proved<detail::status::upward_sub_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator-=(Interval<T>& x, const Interval<T>& y) noexcept {
    return x = detail::sub(x, y);
}
template <class T>
    requires detail::proved<detail::status::upward_mul_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator*=(Interval<T>& x, const Interval<T>& y) noexcept {
    return x = detail::mul(x, y);
}
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator+=(Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return x = detail::add<T>(x, t);
}
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator-=(Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return x = detail::sub<T>(x, t);
}
template <class T>
    requires detail::proved<detail::status::upward_mul_num_1, T>
static KAIRN_FORCEINLINE Interval<T>& operator*=(Interval<T>& x, std::type_identity_t<T> t) noexcept {
    return x = detail::mul<T>(x, t);
}

/// X + Y, X - Y, X * Y (with an interval or a number) and -X with a marked operand: the same
/// operations as without the marker.
template <class X, class Y>
    requires detail::marked_pair<X, Y>
static KAIRN_FORCEINLINE auto operator+(const X& x, const Y& y) noexcept
    -> decltype(detail::add(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::add(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
static KAIRN_FORCEINLINE auto operator-(const X& x, const Y& y) noexcept
    -> decltype(detail::sub(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::sub(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
static KAIRN_FORCEINLINE auto operator*(const X& x, const Y& y) noexcept
    -> decltype(detail::mul(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::mul(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X>
    requires(::kairn::detail::marked<X> && detail::upward_interval<X>)
static KAIRN_FORCEINLINE auto operator-(const X& x) noexcept -> decltype(detail::neg(::kairn::detail::unmark(x))) {
    return detail::neg(::kairn::detail::unmark(x));
}
/// X = X + Y, X - Y, X * Y with a marked right operand.
template <class X, class Y>
    requires detail::marked_rhs<X, Y>
static KAIRN_FORCEINLINE auto operator+=(X& x, const Y& y) noexcept -> decltype(x = detail::add(x, ::kairn::detail::unmark(y))) {
    return x = detail::add(x, ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_rhs<X, Y>
static KAIRN_FORCEINLINE auto operator-=(X& x, const Y& y) noexcept -> decltype(x = detail::sub(x, ::kairn::detail::unmark(y))) {
    return x = detail::sub(x, ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_rhs<X, Y>
static KAIRN_FORCEINLINE auto operator*=(X& x, const Y& y) noexcept -> decltype(x = detail::mul(x, ::kairn::detail::unmark(y))) {
    return x = detail::mul(x, ::kairn::detail::unmark(y));
}

// --- The three-valued comparisons and the relations (exact, any mode, external linkage) -----------
//
// As for the default type: kairn::Trit, which does not convert to bool; no comparison operators. A
// comparison with an empty operand is unknown.

/// The three-valued X < Y (kernel upward_less_1): yes when u_X < -n_Y, no when -n_X >= u_Y. Exact.
template <class T>
    requires detail::proved<detail::status::upward_less_1, T>
KAIRN_FORCEINLINE ::kairn::Trit less(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::less(x, y);
}
/// The three-valued X <= Y (kernel upward_less_equal_1). Exact.
template <class T>
    requires detail::proved<detail::status::upward_less_equal_1, T>
KAIRN_FORCEINLINE ::kairn::Trit less_equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::less_equal(x, y);
}
/// The three-valued X > Y: less(Y, X). Exact.
template <class T>
    requires detail::proved<detail::status::upward_less_1, T>
KAIRN_FORCEINLINE ::kairn::Trit greater(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::greater(x, y);
}
/// The three-valued X >= Y: less_equal(Y, X). Exact.
template <class T>
    requires detail::proved<detail::status::upward_less_equal_1, T>
KAIRN_FORCEINLINE ::kairn::Trit greater_equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::greater_equal(x, y);
}
/// The three-valued X = Y (kernel upward_equal_1): yes when both are the same point, no when they
/// are disjoint. Exact. Not the relation of IEEE 1788: that is kairn::upward::ieee1788::equal.
template <class T>
    requires detail::proved<detail::status::upward_equal_1, T>
KAIRN_FORCEINLINE ::kairn::Trit equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::equal(x, y);
}
/// The three-valued X != Y: equal(X, Y) with yes and no exchanged. Exact.
template <class T>
    requires detail::proved<detail::status::upward_equal_1, T>
KAIRN_FORCEINLINE ::kairn::Trit not_equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::not_equal(x, y);
}
/// Whether t is a member of X, as a Trit (kernel upward_contains_1, as X.contains(t)): yes or no,
/// never unknown. Exact.
template <class T>
    requires detail::proved<detail::status::upward_contains_1, T>
KAIRN_FORCEINLINE ::kairn::Trit member(std::type_identity_t<T> t, const Interval<T>& x) noexcept {
    return detail::member<T>(t, x);
}

/// The comparisons and member(t, X) with a marked operand.
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto less(const X& x, const Y& y) noexcept
    -> decltype(detail::less(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::less(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto less_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::less_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::less_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto greater(const X& x, const Y& y) noexcept
    -> decltype(detail::greater(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::greater(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto greater_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::greater_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::greater_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto equal(const X& x, const Y& y) noexcept
    -> decltype(detail::equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto not_equal(const X& x, const Y& y) noexcept
    -> decltype(detail::not_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::not_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class P, class X>
    requires detail::marked_member<P, X>
KAIRN_FORCEINLINE auto member(const P& t, const X& x) noexcept
    -> decltype(detail::member(::kairn::detail::unmark(t), ::kairn::detail::unmark(x))) {
    return detail::member(::kairn::detail::unmark(t), ::kairn::detail::unmark(x));
}

/// The relations of IEEE Std 1788.1-2017 of two intervals, under the standard's names, each a bool
/// with the standard's readings of the empty set, as kairn::ieee1788 has them for the default type.
namespace ieee1788 {
/// X and Y have the same members (kernel upward_rel_equal_1): the same lanes, or both empty. Exact.
template <class T>
    requires detail::proved<detail::status::upward_rel_equal_1, T>
KAIRN_FORCEINLINE bool equal(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::rel_equal(x, y);
}
/// Every member of X is a member of Y (kernel upward_subset_1), the answer of Y.contains(X). Exact.
template <class T>
    requires detail::proved<detail::status::upward_subset_1, T>
KAIRN_FORCEINLINE bool subset(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::subset(x, y);
}
/// Every member of X has a neighbourhood of members of Y (kernel upward_rel_interior_1), an infinite
/// bound being inside an equal one; the empty set is interior to every interval. Exact.
template <class T>
    requires detail::proved<detail::status::upward_rel_interior_1, T>
KAIRN_FORCEINLINE bool interior(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::rel_interior(x, y);
}
/// No real number is a member of both (kernel upward_rel_disjoint_1). Exact.
template <class T>
    requires detail::proved<detail::status::upward_rel_disjoint_1, T>
KAIRN_FORCEINLINE bool disjoint(const Interval<T>& x, const Interval<T>& y) noexcept {
    return detail::rel_disjoint(x, y);
}
/// The same with a marked operand.
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto equal(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::rel_equal(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto subset(const X& x, const Y& y) noexcept
    -> decltype(detail::subset(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::subset(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto interior(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_interior(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::rel_interior(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
template <class X, class Y>
    requires detail::marked_pair<X, Y>
KAIRN_FORCEINLINE auto disjoint(const X& x, const Y& y) noexcept
    -> decltype(detail::rel_disjoint(::kairn::detail::unmark(x), ::kairn::detail::unmark(y))) {
    return detail::rel_disjoint(::kairn::detail::unmark(x), ::kairn::detail::unmark(y));
}
}  // namespace ieee1788

// --- Values that cross a scope's boundary, the functions on arrays ---------------------------------

namespace detail {
// The pin of the most recent scope on each lane of a register (KAIRN_DETAIL_UPWARD_PIN): a barrier
// on GCC and Clang, an OR with the scope's zero on MSVC. The same bits.
template <class T>
KAIRN_FORCEINLINE void pin_pair(pair<T>& v) noexcept {
#if KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_NUMBERS
    KAIRN_DETAIL_UPWARD_PIN(v.u);
    KAIRN_DETAIL_UPWARD_PIN(v.n);
#else
    KAIRN_DETAIL_UPWARD_PIN(v);
#endif
}

// Whether the byte ranges [a, a + bytes) and [b, b + bytes) share a byte.
KAIRN_FORCEINLINE bool overlap(const void* a, const void* b, std::size_t bytes) noexcept {
    const std::uintptr_t p = reinterpret_cast<std::uintptr_t>(a), q = reinterpret_cast<std::uintptr_t>(b);
    return bytes != 0 && p < q + bytes && q < p + bytes;
}
// Whether the view written z and the view read x are the same view (in place) or apart.
template <class T>
KAIRN_FORCEINLINE bool apart_or_same(const View<T>& z, const View<const T>& x, std::size_t n) noexcept {
    if (z.upper == x.upper && z.nlower == x.nlower) return true;
    const std::size_t b = n * sizeof(T);
    return !overlap(z.upper, x.upper, b) && !overlap(z.upper, x.nlower, b) && !overlap(z.nlower, x.upper, b) &&
           !overlap(z.nlower, x.nlower, b);
}
template <class T>
KAIRN_FORCEINLINE bool elements_canonical(const View<const T>& x, std::size_t n) noexcept {
    bool ok = true;
    for (std::size_t i = 0; i < n; ++i) ok = ok && canonical(x.upper[i], x.nlower[i]);
    return ok;
}
// The checks of a function on arrays, in a checked build, inside its scope (flush to zero off): the
// lengths (a mismatch reported, then the shortest used, so that a KAIRN_ENVIRONMENT_FAILURE that
// returns reads and writes no element beyond a view), the arrays written apart from each other and
// from those read but in place, every element read canonical. The length the function computes.
template <class T>
KAIRN_FORCEINLINE std::size_t checked_length(const View<T>& z, const View<const T>& x, const View<const T>* y) noexcept {
    std::size_t n = z.size;
#if KAIRN_CHECKS
    if (x.size != n || (y && y->size != n)) {
        n = x.size < n ? x.size : n;
        if (y && y->size < n) n = y->size;
        report_lengths();
    }
    if (overlap(z.upper, z.nlower, n * sizeof(T)) || !apart_or_same(z, x, n) || (y && !apart_or_same(z, *y, n)))
        report_overlap();
    if (!elements_canonical(x, n) || (y && !elements_canonical(*y, n))) report_element();
#else
    (void)x;
    (void)y;
#endif
    return n;
}

namespace {
// The functions on arrays without their markers and constraints: each holds the register-only
// scope for its call (RegisterScope: upward, flush to zero and denormals-are-zero off, written only
// on change), loads after it is set and stores before it ends, and runs the kernel's array form.
#define KAIRN_DETAIL_UPWARD_ARRAYS2(NAME, KERNEL)                                                       \
    template <class T>                                                                                  \
    inline void NAME(View<T> z, View<const T> x, View<const T> y) noexcept {                            \
        static_assert(!std::is_const_v<T>, "kairn::upward: the view written is a View<T>, not View<const T>"); \
        RegisterScope scope;                                                                            \
        const std::size_t n = checked_length(z, x, &y);                                                 \
        kernels::KERNEL(x.upper, x.nlower, y.upper, y.nlower, z.upper, z.nlower, n);                    \
    }
KAIRN_DETAIL_UPWARD_ARRAYS2(arrays_add, upward_add_1_arrays)
KAIRN_DETAIL_UPWARD_ARRAYS2(arrays_sub, upward_sub_1_arrays)
KAIRN_DETAIL_UPWARD_ARRAYS2(arrays_mul, upward_mul_1_arrays)
#undef KAIRN_DETAIL_UPWARD_ARRAYS2
#define KAIRN_DETAIL_UPWARD_ARRAYS_NUMBER(NAME, KERNEL)                                                 \
    template <class T>                                                                                  \
    inline void NAME(View<T> z, View<const T> x, T t) noexcept {                                        \
        static_assert(!std::is_const_v<T>, "kairn::upward: the view written is a View<T>, not View<const T>"); \
        RegisterScope scope;                                                                            \
        const std::size_t n = checked_length(z, x, static_cast<const View<const T>*>(nullptr));         \
        kernels::KERNEL(x.upper, x.nlower, t, z.upper, z.nlower, n);                                    \
    }
KAIRN_DETAIL_UPWARD_ARRAYS_NUMBER(arrays_add_number, upward_add_num_1_arrays)
KAIRN_DETAIL_UPWARD_ARRAYS_NUMBER(arrays_mul_number, upward_mul_num_1_arrays)
#undef KAIRN_DETAIL_UPWARD_ARRAYS_NUMBER
template <class T>
inline void arrays_neg(View<T> z, View<const T> x) noexcept {
    static_assert(!std::is_const_v<T>, "kairn::upward: the view written is a View<T>, not View<const T>");
    RegisterScope scope;
    const std::size_t n = checked_length(z, x, static_cast<const View<const T>*>(nullptr));
    kernels::upward_neg_1_arrays(x.upper, x.nlower, z.upper, z.nlower, n);
}
}  // namespace
}  // namespace detail

namespace {

/// X after a barrier on its register (on MSVC the pin of the most recent scope), for a value that
/// crosses a scope's boundary into code that has no barrier; the same bits. Internal linkage.
template <class T>
KAIRN_FORCEINLINE Interval<T> pass(const Interval<T>& x) noexcept {
    detail::pair<T> v = detail::access::get(x);
    detail::pin_pair<T>(v);
    return detail::access::make<T>(v);
}

/// The functions on arrays (the design page, "Arrays"): z = x + y, x - y, x * y, -x, x + t, x * t,
/// element by element, on views of two plain arrays, the upper bounds and the negated lower bounds.
/// Each holds its own scope for the call (upward, the register only: the C library's mode is not
/// set), so a program may call it from code that rounds to nearest; inside a kairn::upward::Scope
/// that scope costs one read. The views have the same length; z may be x or y (in place), and
/// otherwise the arrays written overlap no array read; every element read is canonical (each
/// checked when KAIRN_CHECKS is 1, and reported through KAIRN_ENVIRONMENT_FAILURE). Each element is
/// what the operator of Interval<T> gives on it. Internal linkage; called by their qualified names
/// (kairn::upward::add(z, x, y)): argument-dependent lookup does not see an unnamed namespace. With
/// a marked first input when the kernel is not proved: kairn::upward::add(z, kairn::unverified(x), y).
template <class T>
    requires detail::proved<detail::status::upward_add_1, T>
inline void add(View<T> z, std::type_identity_t<View<const T>> x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_add<T>(z, x, y);
}
template <class T>
inline void add(View<T> z, const ::kairn::Unverified<View<const T>>& x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_add<T>(z, x.value, y);
}
template <class T>
    requires detail::proved<detail::status::upward_sub_1, T>
inline void sub(View<T> z, std::type_identity_t<View<const T>> x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_sub<T>(z, x, y);
}
template <class T>
inline void sub(View<T> z, const ::kairn::Unverified<View<const T>>& x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_sub<T>(z, x.value, y);
}
template <class T>
    requires detail::proved<detail::status::upward_mul_1, T>
inline void mul(View<T> z, std::type_identity_t<View<const T>> x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_mul<T>(z, x, y);
}
template <class T>
inline void mul(View<T> z, const ::kairn::Unverified<View<const T>>& x, std::type_identity_t<View<const T>> y) noexcept {
    detail::arrays_mul<T>(z, x.value, y);
}
template <class T>
    requires detail::proved<detail::status::upward_neg_1, T>
inline void neg(View<T> z, std::type_identity_t<View<const T>> x) noexcept {
    detail::arrays_neg<T>(z, x);
}
template <class T>
inline void neg(View<T> z, const ::kairn::Unverified<View<const T>>& x) noexcept {
    detail::arrays_neg<T>(z, x.value);
}
template <class T>
    requires detail::proved<detail::status::upward_add_num_1, T>
inline void add(View<T> z, std::type_identity_t<View<const T>> x, std::type_identity_t<T> t) noexcept {
    detail::arrays_add_number<T>(z, x, t);
}
template <class T>
inline void add(View<T> z, const ::kairn::Unverified<View<const T>>& x, std::type_identity_t<T> t) noexcept {
    detail::arrays_add_number<T>(z, x.value, t);
}
template <class T>
    requires detail::proved<detail::status::upward_mul_num_1, T>
inline void mul(View<T> z, std::type_identity_t<View<const T>> x, std::type_identity_t<T> t) noexcept {
    detail::arrays_mul_number<T>(z, x, t);
}
template <class T>
inline void mul(View<T> z, const ::kairn::Unverified<View<const T>>& x, std::type_identity_t<T> t) noexcept {
    detail::arrays_mul_number<T>(z, x.value, t);
}

}  // namespace

// --- The self-check -------------------------------------------------------------------------------

namespace detail {
namespace {

// The values of the probes, for each T: p = 1 + u, whose square 1 + 2u + u^2 is p2_down rounded to
// nearest and downward and p2_up upward; 1 + tiny is 1 to nearest and one_up upward, and p + tiny
// is p to nearest and p_up (the number after p) upward; lambda, the smallest normal number, times
// scale is the subnormal number product, exactly; eta, the smallest subnormal number, times 1/2 is
// eta upward.
template <class T>
struct probe;
template <>
struct probe<double> {
    static constexpr double p = 0x1.0000000000001p+0, p2_down = 0x1.0000000000002p+0, p2_up = 0x1.0000000000003p+0;
    static constexpr double tiny = 0x1p-60, one_up = 0x1.0000000000001p+0, p_up = 0x1.0000000000002p+0;
    static constexpr double lambda = 0x1p-1022, scale = 0x1p-30, product = 0x1p-1052, eta = 0x1p-1074;
};
template <>
struct probe<float> {
    static constexpr float p = 0x1.000002p+0f, p2_down = 0x1.000004p+0f, p2_up = 0x1.000006p+0f;
    static constexpr float tiny = 0x1p-30f, one_up = 0x1.000002p+0f, p_up = 0x1.000004p+0f;
    static constexpr float lambda = 0x1p-126f, scale = 0x1p-10f, product = 0x1p-136f, eta = 0x1p-149f;
};
// One of two names of a case, by T.
template <class T>
KAIRN_FORCEINLINE const char* name_of(const char* for_double, const char* for_float) noexcept {
    return sizeof(T) == 8 ? for_double : for_float;
}
template <class T>
KAIRN_FORCEINLINE bool same_bits(T a, T b) noexcept {
    if constexpr (sizeof(T) == 8) {
        return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
    } else {
        return std::bit_cast<std::uint32_t>(a) == std::bit_cast<std::uint32_t>(b);
    }
}
// The same member of a set: equal numbers (a zero of either sign), or two NaN.
template <class T>
KAIRN_FORCEINLINE bool same_value(T a, T b) noexcept {
    return a == b || (a != a && b != b);
}
inline bool fail(::kairn::Status& s, const char* failure, const char* kernel) noexcept {
    s.failure = failure;
    s.kernel = kernel;
    return false;
}
// The interval of (u, n) as the program gives it, for a probe: through from_limbs.
template <class T>
KAIRN_FORCEINLINE Interval<T> state(T u, T n) noexcept {
    const T p[2] = {u, n};
    return Interval<T>::from_limbs(p);
}
template <class T>
KAIRN_FORCEINLINE Interval<T> point(T a) noexcept {
    return state<T>(a, -a);
}

// 1. The mode: set upward by Scope and by the register-only scope of the functions on arrays, read
// back from the register (and from the C library for Scope), seen in the hardware's arithmetic
// (1 + tiny through the header's sum), and restored when the scope ends.
template <class T>
KAIRN_DETAIL_NOINLINE inline bool hardware_rounds_upward() noexcept {
    volatile T vone = T(1), vtiny = probe<T>::tiny;
    const T one = vone, tiny = vtiny;
    pair<T> z{};
    kernels::upward_add_1(kernels::pair_make(one, -one), kernels::pair_make(tiny, -tiny), z);
    return same_bits(kernels::pair_upper(z), probe<T>::one_up) && same_bits(kernels::pair_nlower(z), -one);
}
template <class S>
inline bool selftest_scope(::kairn::Status& s, bool library, const char* which) noexcept {
    const int library_before = std::fegetround();
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
    constexpr control_t fields = rounding_field | flush_field;
    const control_t before = read_control();
#endif
    bool reads_back = false, follows = false, hardware = false;
    {
        S up;
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
        reads_back = (read_control() & fields) == rounding_upward;
#else
        reads_back = std::fegetround() == FE_UPWARD;
#endif
        follows = !library || std::fegetround() == FE_UPWARD;
        hardware = hardware_rounds_upward<double>() && hardware_rounds_upward<float>();
    }
    bool restored = std::fegetround() == library_before;
#if defined(KAIRN_DETAIL_MXCSR) || defined(KAIRN_DETAIL_FPCR)
    restored = restored && ((read_control() ^ before) & fields) == 0;
#endif
    if (!reads_back) return fail(s, "the rounding mode does not read back as upward, with flush to zero off, inside a scope", which);
    if (!follows) return fail(s, "the C library's rounding mode does not follow kairn::upward::Scope", which);
    if (!hardware) return fail(s, "the hardware does not round upward inside a scope (1 + 2^-60 through upward_add_1)", which);
    if (!restored) return fail(s, "a scope does not restore the caller's rounding mode and flush to zero", which);
    return true;
}

// 2. Flush to zero and denormals-are-zero inside a scope, through the header's operations, bit for
// bit: a product of normal numbers whose result is subnormal, a sum of subnormal numbers, and a
// tiny positive product that must round up to eta.
template <class T>
inline bool selftest_subnormal(::kairn::Status& s) noexcept {
    volatile T vl = probe<T>::lambda, vs = probe<T>::scale, ve = probe<T>::eta, vh = T(0.5);
    T r[3][2] = {};
    {
        Scope up;
        const T l = vl, sc = vs, e = ve, h = vh;
        (::kairn::unverified(point(l)) * point(sc)).to_limbs(r[0]);
        (::kairn::unverified(point(e)) + point(e)).to_limbs(r[1]);
        (::kairn::unverified(point(e)) * h).to_limbs(r[2]);
    }
    if (!same_bits(r[0][0], probe<T>::product))
        return fail(s, "results below the normal range are flushed to zero inside a kairn::upward::Scope",
                    name_of<T>("upward_mul_1 (double): a product of normal numbers whose result is subnormal",
                               "upward_mul_1 (float): a product of normal numbers whose result is subnormal"));
    if (!same_bits(r[1][0], T(2) * probe<T>::eta))
        return fail(s, "subnormal operands are read as zero inside a kairn::upward::Scope",
                    name_of<T>("upward_add_1 (double): a sum of subnormal numbers",
                               "upward_add_1 (float): a sum of subnormal numbers"));
    if (!same_bits(r[2][0], probe<T>::eta))
        return fail(s, "a tiny positive product is not rounded up to the smallest subnormal number inside a kairn::upward::Scope",
                    name_of<T>("upward_mul_num_1 (double): eta times 1/2", "upward_mul_num_1 (float): eta times 1/2"));
    return true;
}

// 5. A negation moved through a product: for [p, p] [p, p] the lower bound is RD(p^2), held as
// RU((-p) p) = -RD(p^2), which -RU(p^2) would not be; and the same with signs exchanged and by a
// number. Operands in registers, on literals, and in a function of its own as a program's would be.
template <class T>
KAIRN_FORCEINLINE bool square_ok(const Interval<T>& z, bool negative) noexcept {
    T r[2] = {};
    z.to_limbs(r);
    return negative ? same_bits(r[0], -probe<T>::p2_down) && same_bits(r[1], probe<T>::p2_up)
                    : same_bits(r[0], probe<T>::p2_up) && same_bits(r[1], -probe<T>::p2_down);
}
template <class T>
KAIRN_DETAIL_NOINLINE inline bool negation_function(T a, T b) noexcept {
    bool ok = false;
    {
        Scope up;
        ok = square_ok(::kairn::unverified(point(a)) * point(b), false);
    }
    return ok;
}
template <class T>
inline bool selftest_negation(::kairn::Status& s) noexcept {
    volatile T vp = probe<T>::p;
    const T p = vp;
    bool registers = false, signs = false, number = false, literals = false;
    {
        Scope up;
        registers = square_ok(::kairn::unverified(point(p)) * point(p), false);
        signs = square_ok(::kairn::unverified(point(-p)) * point(p), true);
        number = square_ok(::kairn::unverified(point(p)) * p, false) && square_ok(p * ::kairn::unverified(point(-p)), true);
        literals = square_ok(::kairn::unverified(point(probe<T>::p)) * point(probe<T>::p), false);
    }
    const bool function = negation_function<T>(p, p);
    const char* failure = "a negation was moved through a rounded product (the product's negated lower bound)";
    if (!registers) return fail(s, failure, name_of<T>("upward_mul_1 (double): [p, p] [p, p], operands in registers", "upward_mul_1 (float): [p, p] [p, p], operands in registers"));
    if (!signs) return fail(s, failure, name_of<T>("upward_mul_1 (double): [-p, -p] [p, p]", "upward_mul_1 (float): [-p, -p] [p, p]"));
    if (!number) return fail(s, failure, name_of<T>("upward_mul_num_1 (double): [p, p] p and p [-p, -p]", "upward_mul_num_1 (float): [p, p] p and p [-p, -p]"));
    if (!literals) return fail(s, failure, name_of<T>("upward_mul_1 (double): [p, p] [p, p], literal operands", "upward_mul_1 (float): [p, p] [p, p], literal operands"));
    if (!function) return fail(s, failure, name_of<T>("upward_mul_1 (double): [p, p] [p, p] in a function of its own", "upward_mul_1 (float): [p, p] [p, p] in a function of its own"));
    return true;
}

// 6. The special cases against the default Interval<T, 1>, computed first outside any upward scope
// (the caller of self_test() holds a NearestScope): unbounded operands, overflow both ways,
// 0 times infinity, [0, 0] times the whole line, the empty set, and numbers that are infinite or a
// NaN (the default x op Interval<T, 1>(t)). The operands and results cross the scopes through
// volatile objects. Every result the same set (the sign of a zero aside): no product here is below
// 2^(2p-1) eta, where the default one may be wider. One row of operands at a time (an interval x
// with every interval and every number), so that the results held at once are one row's.
template <class T>
inline bool selftest_special(::kairn::Status& s) noexcept {
    constexpr T inf = std::numeric_limits<T>::infinity(), omega = std::numeric_limits<T>::max();
    constexpr T nan = std::numeric_limits<T>::quiet_NaN();
    constexpr int n = 11, m = 5;
    static constexpr T lo[n] = {1, -1, -inf, -2, omega, -omega, 2, 0, 0, -inf, inf};
    static constexpr T hi[n] = {inf, 2, -1, -1, omega, -omega, 2, 0, 1, inf, -inf};  // the last: the empty set
    static constexpr T numbers[m] = {inf, -inf, nan, 2, 0};
    using D = ::kairn::Interval<T, 1>;
    // The results of a row x: x + y, x - y, x y for each interval y, then x + t, x - t, t - x, x t for
    // each number t.
    constexpr int pairs = n * 3, row = pairs + m * 4;
    volatile T want[row][2];
    volatile T got[row][2];
    volatile T vlo[n], vhi[n], vt[m];
    for (int i = 0; i < n; ++i) {
        vlo[i] = lo[i];
        vhi[i] = hi[i];
    }
    for (int k = 0; k < m; ++k) vt[k] = numbers[k];
    for (int i = 0; i < n; ++i) {
        {
            int w = 0;
            auto put = [&](const D& z) {
                want[w][0] = z.lower().limb[0];
                want[w][1] = z.upper().limb[0];
                ++w;
            };
            const D x(::kairn::unverified(T(vlo[i])), T(vhi[i]));
            for (int j = 0; j < n; ++j) {
                const D y(::kairn::unverified(T(vlo[j])), T(vhi[j]));
                put(x + y);
                put(x - y);
                put(x * y);
            }
            for (int k = 0; k < m; ++k) {
                const D t(::kairn::unverified(T(vt[k])));
                put(x + t);
                put(x - t);
                put(t - x);
                put(x * t);
            }
        }
        {
            Scope up;
            int w = 0;
            auto put = [&](const Interval<T>& z) {
                T b[2] = {};
                z.to_limbs(b);
                got[w][0] = b[0];
                got[w][1] = b[1];
                ++w;
            };
            const Interval<T> x(::kairn::unverified(T(vlo[i])), T(vhi[i]));
            for (int j = 0; j < n; ++j) {
                const Interval<T> y(::kairn::unverified(T(vlo[j])), T(vhi[j]));
                put(::kairn::unverified(x) + y);
                put(::kairn::unverified(x) - y);
                put(::kairn::unverified(x) * y);
            }
            for (int k = 0; k < m; ++k) {
                const T t = vt[k];
                put(::kairn::unverified(x) + t);
                put(::kairn::unverified(x) - t);
                put(t - ::kairn::unverified(x));
                put(::kairn::unverified(x) * t);
            }
        }
        for (int w = 0; w < row; ++w) {
            const T u = got[w][0], nl = got[w][1];
            const bool empty = u != u;
            const T l = empty ? inf : -nl, h = empty ? -inf : u;
            if (!same_value(T(want[w][0]), l) || !same_value(T(want[w][1]), h)) {
                const char* failure = "a special case differs from the default kairn::Interval<T, 1> (unbounded "
                                      "operands, overflow, 0 times infinity, the empty set, a number that is not finite)";
                if (w < pairs) {
                    const int op = w % 3;
                    return fail(s, failure,
                                op == 0   ? name_of<T>("upward_add_1 (double)", "upward_add_1 (float)")
                                : op == 1 ? name_of<T>("upward_sub_1 (double)", "upward_sub_1 (float)")
                                          : name_of<T>("upward_mul_1 (double)", "upward_mul_1 (float)"));
                }
                const int op = (w - pairs) % 4;
                return fail(s, failure,
                            op == 3 ? name_of<T>("upward_mul_num_1 (double)", "upward_mul_num_1 (float)")
                                    : name_of<T>("upward_add_num_1 (double): x + t, x - t or t - x",
                                                 "upward_add_num_1 (float): x + t, x - t or t - x"));
            }
        }
    }
    return true;
}

// 7 and 8. Operations moved across a scope's boundary: computed on values held in registers before
// a scope and again inside it (a merge, or a move above the change of mode, gives the result to
// nearest inside); inside a scope in a loop of a length the compiler does not know, and around such
// a loop; and used only after the scope has ended (a move below the restoring write: the gap of the
// design page's section "MSVC", probed on every compiler). The caller holds a NearestScope, so the
// mode is nearest outside the scopes here. Before a scope the generated kernel is called directly,
// as the type's operators may not be outside one (a checked build reports them); inside, the type's
// operators. Each shape is ordinary code, as a program's is; several shapes, because a compiler
// that moves an operation in one may not in another.
template <class T>
KAIRN_DETAIL_NOINLINE inline void merge_function(T a, T b, T* r) noexcept {
    const pair<T> x = kernels::pair_make(a, -a), y = kernels::pair_make(b, -b);
    pair<T> before{}, inside{};
    kernels::upward_mul_1(x, y, before);
    {
        Scope up;
        kernels::upward_mul_1(x, y, inside);
    }
    r[0] = kernels::pair_upper(before);
    r[1] = kernels::pair_upper(inside);
}
template <class T>
KAIRN_DETAIL_NOINLINE inline void loop_function(T a, T* r, int n) noexcept {
    const Interval<T> x = point(a);
    for (int i = 0; i < n; ++i) {
        Scope up;
        r[i] = ::kairn::unverified(::kairn::unverified(x) * x).upper();
    }
}
template <class T>
KAIRN_DETAIL_NOINLINE inline void around_loop_function(T a, T* r, int n) noexcept {
    Scope up;
    const Interval<T> x = point(a);
    for (int i = 0; i < n; ++i) r[i] = ::kairn::unverified(::kairn::unverified(x) * x).upper();
}
template <class T>
KAIRN_DETAIL_NOINLINE inline T sink_function(T a, T b) noexcept {
    Interval<T> z;
    {
        Scope up;
        z = ::kairn::unverified(point(a)) * point(b);
    }
    T r[2] = {};
    z.to_limbs(r);
    return r[0];
}
template <class T>
inline bool selftest_moves(::kairn::Status& s) noexcept {
    volatile T vp = probe<T>::p, vone = T(1), vtiny = probe<T>::tiny;
    volatile int vn = 5;
    const T p = vp, one = vone, tiny = vtiny;
    const int n = vn < 5 ? vn : 5;
    const char* above = "an operation was merged with one before its scope, or moved above the scope's change of mode";
    const char* below = "an operation was moved below the end of its scope (computed after the restoring write)";
    // Before a scope and inside it, in this function: a sum and a product.
    {
        const pair<T> x = kernels::pair_make(one, -one), y = kernels::pair_make(tiny, -tiny), q = kernels::pair_make(p, -p);
        pair<T> sum_before{}, sum_inside{}, product_before{}, product_inside{};
        kernels::upward_add_1(x, y, sum_before);
        kernels::upward_mul_1(q, q, product_before);
        {
            Scope up;
            kernels::upward_add_1(x, y, sum_inside);
            kernels::upward_mul_1(q, q, product_inside);
        }
        if (!same_bits(kernels::pair_upper(sum_before), one) || !same_bits(kernels::pair_upper(sum_inside), probe<T>::one_up))
            return fail(s, above, name_of<T>("upward_add_1 (double): operands in registers, before a scope and inside it",
                                             "upward_add_1 (float): operands in registers, before a scope and inside it"));
        if (!same_bits(kernels::pair_upper(product_before), probe<T>::p2_down) ||
            !same_bits(kernels::pair_upper(product_inside), probe<T>::p2_up))
            return fail(s, above, name_of<T>("upward_mul_1 (double): operands in registers, before a scope and inside it",
                                             "upward_mul_1 (float): operands in registers, before a scope and inside it"));
    }
    // The same in a function of its own.
    {
        T r[2] = {};
        merge_function<T>(p, p, r);
        if (!same_bits(r[0], probe<T>::p2_down) || !same_bits(r[1], probe<T>::p2_up))
            return fail(s, above, name_of<T>("upward_mul_1 (double): before a scope and inside it, in a function of its own",
                                             "upward_mul_1 (float): before a scope and inside it, in a function of its own"));
    }
    // A scope inside a loop of unknown length, and a loop inside a scope: the results to an ordinary
    // array first (the measurement step saw a product hoisted out of a loop that stored to an
    // ordinary array, and not out of one that stored to volatile objects).
    {
        T inside[5] = {}, around[5] = {};
        loop_function<T>(p, inside, n);
        around_loop_function<T>(p, around, n);
        bool ok_inside = true, ok_around = true;
        for (int i = 0; i < n; ++i) {
            ok_inside = ok_inside && same_bits(inside[i], probe<T>::p2_up);
            ok_around = ok_around && same_bits(around[i], probe<T>::p2_up);
        }
        if (!ok_inside)
            return fail(s, above, name_of<T>("upward_mul_1 (double): a scope inside a loop of unknown length",
                                             "upward_mul_1 (float): a scope inside a loop of unknown length"));
        if (!ok_around)
            return fail(s, above, name_of<T>("upward_mul_1 (double): a loop of unknown length inside a scope",
                                             "upward_mul_1 (float): a loop of unknown length inside a scope"));
    }
    // Used only after the scope: in this function, in a function of its own, and in a loop.
    {
        Interval<T> z;
        {
            Scope up;
            z = ::kairn::unverified(point(p)) * point(p);
        }
        T r[2] = {};
        z.to_limbs(r);
        if (!same_bits(r[0], probe<T>::p2_up))
            return fail(s, below, name_of<T>("upward_mul_1 (double): a product used only after its scope",
                                             "upward_mul_1 (float): a product used only after its scope"));
        if (!same_bits(sink_function<T>(p, p), probe<T>::p2_up))
            return fail(s, below, name_of<T>("upward_mul_1 (double): used only after its scope, in a function of its own",
                                             "upward_mul_1 (float): used only after its scope, in a function of its own"));
        Interval<T> late[5];
        for (int i = 0; i < n; ++i) {
            Scope up;
            late[i] = ::kairn::unverified(point(p)) + point(tiny);
        }
        bool ok = true;
        for (int i = 0; i < n; ++i) {
            late[i].to_limbs(r);
            ok = ok && same_bits(r[0], probe<T>::p_up) && same_bits(r[1], -p);
        }
        if (!ok)
            return fail(s, below, name_of<T>("upward_add_1 (double): sums of scopes in a loop, used after the loop",
                                             "upward_add_1 (float): sums of scopes in a loop, used after the loop"));
    }
    return true;
}

// 9. Each function on arrays on a short array (both the registers of the array form and the
// elements after them), called where the mode is nearest so that its own scope sets it, against
// the operators of Interval<T> in a Scope: the same sets.
template <class T>
inline bool selftest_arrays(::kairn::Status& s) noexcept {
    constexpr T inf = std::numeric_limits<T>::infinity(), nan = std::numeric_limits<T>::quiet_NaN();
    constexpr std::size_t n = 9;
    // (u, n) of: [1, p], [-2, 3], [0, 0], [p, +inf], whole, empty, [-inf, -1], [-p, -p], [1/4, 1/2].
    static constexpr T xu[n] = {probe<T>::p, 3, 0, inf, inf, nan, -1, -probe<T>::p, T(0.5)};
    static constexpr T xn[n] = {-1, 2, 0, -probe<T>::p, inf, nan, inf, probe<T>::p, T(-0.25)};
    T au[n], an[n], bu[n], bn[n];
    for (std::size_t i = 0; i < n; ++i) {
        au[i] = xu[i];
        an[i] = xn[i];
        bu[i] = xu[n - 1 - i];
        bn[i] = xn[n - 1 - i];
    }
    volatile T vt = probe<T>::p;
    const T t = vt;
    const View<const T> a(au, an, n), b(bu, bn, n);
    T zu[6][n], zn[6][n];
    ::kairn::upward::add(View<T>(zu[0], zn[0], n), ::kairn::unverified(a), b);
    ::kairn::upward::sub(View<T>(zu[1], zn[1], n), ::kairn::unverified(a), b);
    ::kairn::upward::mul(View<T>(zu[2], zn[2], n), ::kairn::unverified(a), b);
    ::kairn::upward::neg(View<T>(zu[3], zn[3], n), ::kairn::unverified(a));
    ::kairn::upward::add(View<T>(zu[4], zn[4], n), ::kairn::unverified(a), t);
    ::kairn::upward::mul(View<T>(zu[5], zn[5], n), ::kairn::unverified(a), t);
    T want[6][n][2];
    {
        Scope up;
        for (std::size_t i = 0; i < n; ++i) {
            const Interval<T> x = state(au[i], an[i]), y = state(bu[i], bn[i]);
            (::kairn::unverified(x) + y).to_limbs(want[0][i]);
            (::kairn::unverified(x) - y).to_limbs(want[1][i]);
            (::kairn::unverified(x) * y).to_limbs(want[2][i]);
            (-::kairn::unverified(x)).to_limbs(want[3][i]);
            (::kairn::unverified(x) + t).to_limbs(want[4][i]);
            (::kairn::unverified(x) * t).to_limbs(want[5][i]);
        }
    }
    static constexpr const char* names_double[6] = {"kairn::upward::add (double)", "kairn::upward::sub (double)",
                                                    "kairn::upward::mul (double)", "kairn::upward::neg (double)",
                                                    "kairn::upward::add (double), a number", "kairn::upward::mul (double), a number"};
    static constexpr const char* names_float[6] = {"kairn::upward::add (float)", "kairn::upward::sub (float)",
                                                   "kairn::upward::mul (float)", "kairn::upward::neg (float)",
                                                   "kairn::upward::add (float), a number", "kairn::upward::mul (float), a number"};
    for (int f = 0; f < 6; ++f)
        for (std::size_t i = 0; i < n; ++i)
            if (!same_value(zu[f][i], want[f][i][0]) || !same_value(zn[f][i], want[f][i][1]))
                return fail(s, "a function on arrays differs from the operators of kairn::upward::Interval<T>",
                            name_of<T>(names_double[f], names_float[f]));
    return true;
}

// The advice (limitation set, ok() still true): this file's own arithmetic ignores the mode (a sum
// of literals, and (-a) b and a + b against -((-a) - b) on operands in registers, all the file's
// own code); a product of the file's own code contracted into a sum; a computation of the default
// types right after an upward scope, on operands in registers, that came out as if computed inside
// it. The first two because the header's results do not depend on them, the third because the
// default types are the program's to place.
KAIRN_DETAIL_NOINLINE inline const char* selftest_advice() noexcept {
    volatile double va = probe<double>::p, vone = 1, vtiny = probe<double>::tiny, vminus = -1;
    volatile double r[6] = {};
    {
        Scope up;
        const double a = va, one = vone, tiny = vtiny, minus = vminus;
        r[0] = 1.0 + 0x1p-60;
        r[1] = (-a) * a;
        r[2] = one + tiny;
        r[3] = -((-one) - tiny);
        r[4] = a * a + minus;
    }
    if (r[0] != probe<double>::one_up || r[1] != -probe<double>::p2_down || r[2] != probe<double>::one_up || r[3] != 1)
        return "this file's own arithmetic ignores the rounding mode upward (a sum of literals, (-a) b, or a + b against "
               "-((-a) - b), computed as if to nearest): the header's operations are right, the program's own code in a "
               "scope is not; GCC and Clang need -frounding-math, MSVC /fp:strict (the CMake target kairn::upward)";
    if (r[4] == 0x1.0000000000001p-51)
        return "a product of this file's own code was contracted with a sum into one fused multiply-add, rounded once: "
               "the header's operations are not affected; -ffp-contract=off keeps the program's own products apart";
    // The default types right after an upward scope, on operands in registers: the sum 1 + tiny of
    // Expansion<double, 1> and the midpoint of [1, p], each 1 to nearest and the number after 1
    // upward. (The sums and products of the default intervals are no probe: their error-free
    // transformations gave the right bounds on such operands under the mode upward too.)
    const double one = vone, tiny = vtiny, p = va;
    const ::kairn::Expansion<double, 1> e(one);
    const ::kairn::Interval<double, 1> x(::kairn::unverified(one), p);
    {
        Scope up;
        r[5] = ::kairn::unverified(::kairn::unverified(point(one)) + point(tiny)).upper();
    }
    const double sum = (e + tiny).limb[0], midpoint = x.midpoint().limb[0];
    if (sum != 1 || midpoint != 1)
        return "a computation of the default types right after an upward scope, on operands in registers, came out as if "
               "computed inside it: bring values out of an upward region through memory, to_interval() or "
               "kairn::upward::pass() (docs/concepts/upward.md)";
    return nullptr;
}

}  // namespace
}  // namespace detail

namespace {

/// The self-check of the round-up interval as this file is built (the design page, "The
/// self-check"): a kairn::Status whose ok() is true when every probe passed, failure the first that
/// did not and kernel its case, and limitation an advice about this file's own code that does not
/// make the header's results wrong. Internal linkage: it tests the copies of the operations compiled
/// in the file that calls it, with that file's options; a program calls it from each file built
/// with other options. It holds its own scopes (a NearestScope around it all) and restores the
/// caller's state, so it may be called inside a Scope.
///
/// The failures, in this order: the mode cannot be set upward, does not read back as upward inside a
/// scope, is not restored, or the C library's mode does not follow a Scope (and the same of the
/// scope of the functions on arrays); flush to zero or denormals-are-zero inside a scope; a kernel,
/// for double and float, on fixed operands read through volatile objects, then written as literals
/// (a build that computes them while it compiles), against the values of the generator's
/// interpreter (gen/upward.hpp); a negation moved through a product; the special cases against the
/// default kairn::Interval<T, 1>; an operation merged with one before its scope or moved above it,
/// in several shapes; an operation whose result is used only after its scope, moved below its end;
/// each function on arrays on a short array. The advice: this file's own arithmetic ignores the
/// mode; a product of the program contracted into a sum of the program; a computation of the
/// default types right after an upward scope that came out as if computed inside it.
///
/// Its limits: it tests its own copies of the operations, not every place where the program uses
/// them; a compiler can move code in a program where it did not in the self-check's own shapes; on
/// MSVC it probes the gap (an operation sunk below a scope's end) in its own shapes only. It is
/// evidence, not proof, and with the barriers a second line of defence. Not usable in constant
/// evaluation.
inline ::kairn::Status self_test() noexcept {
    ::kairn::Status s;
    NearestScope nearest;
    s.limitation = detail::selftest_advice();
    if (!detail::selftest_scope<Scope>(s, true, "kairn::upward::Scope")) return s;
    if (!detail::selftest_scope<detail::RegisterScope>(s, false, "the scope of the functions on arrays")) return s;
    if (!detail::selftest_subnormal<double>(s) || !detail::selftest_subnormal<float>(s)) return s;
    const char* label = nullptr;
    {
        Scope up;
        label = detail::kernels::selftest::run_volatile();
    }
    if (label)
        return {"a kernel of the round-up interval differs from the generator's interpreter, on operands read from "
                "volatile objects",
                label, s.limitation};
    {
        Scope up;
        label = detail::kernels::selftest::run_literal();
    }
    if (label)
        return {"a kernel of the round-up interval differs from the generator's interpreter on literal operands: the "
                "build computes them while it compiles, to nearest",
                label, s.limitation};
    if (!detail::selftest_negation<double>(s) || !detail::selftest_negation<float>(s)) return s;
    if (!detail::selftest_special<double>(s) || !detail::selftest_special<float>(s)) return s;
    if (!detail::selftest_moves<double>(s) || !detail::selftest_moves<float>(s)) return s;
    if (!detail::selftest_arrays<double>(s) || !detail::selftest_arrays<float>(s)) return s;
    return s;
}

}  // namespace
}  // namespace kairn::upward
KAIRN_GEN_POP_WARNINGS
