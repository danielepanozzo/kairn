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
