# The tests of the public interface (include/kairn/*.hpp), with ctest labels "api":
#
# - api.constexpr: static_asserts of everything constexpr, and the same expressions at run time.
# - api.oracle.KERNEL.FORMAT: the oracle judges, against KERNEL's claims, every public operation
#   that calls KERNEL (runner.cpp), computed through the constructors, operators and functions a
#   client calls, on random binary64 and binary32 cases (in the extended domain, infinities, NaN
#   and the special balls included, for the kernels that have it); with this build's flags and
#   with contraction forced on, two runners on the same cases. full.api.oracle.KERNEL.FORMAT, in
#   the full tier (../full/), does the same on more cases, with the debug build's runner (flags/)
#   on the first form of each kernel, and full.api.flags.oracle.KERNEL.FORMAT every form through
#   the runner of every flag set of flags/.
# - api.oracle.coverage: every kernel of gen/claims.json is reached by a public form of the
#   runner, or is a building block, or is an entry kernel on the runner's short list of those not
#   public yet; no entry kernel is a building block; and the lists below agree.
# - api.boundary.*: a product the program computes and passes in gives the result of the same
#   operation on the rounded product, under each contraction setting; with the generated guard
#   taken out of a copy of the headers, it must not where the compiler fuses.
#   api.boundary.packed.FORM.*: the same for a product the program computes in registers or arrays
#   and passes into Packed and the containers, in each form of Packed.
# - api.environment: environment_ok() and self_test() pass in the default environment and detect
#   a changed rounding mode and flush-to-zero.
# - api.self_test.unsafe.*: with Clang, a build whose flags break Kairn without a macro to show it,
#   which self_test() must detect.
# - api.flags.debug.*: self_test() and constexpr.cpp in the debug build of flags/.
# - api.checks.*: the checks of KAIRN_CHECKS, which must stop the program under a changed rounding
#   mode or flush to zero, with the environment's message, and on an operand that is not
#   canonical, and let the rest through; with a handler that returns, every operation goes on.
# - api.shadow: a program with global variables named as the headers' parameters and locals,
#   compiled with the compiler's warnings about hidden declarations as errors.
# - api.reject.*: what must not compile: rejected flags, UNVERIFIED operations without the
#   marker, and with KAIRN_CHECKS constant expressions that the checks refuse (each with a control
#   that compiles).
# - api.k1.zero_cost: the code of Expansion<double, 1> against that of double (k1/zero_cost.py).
# - api.rational.constexpr: kairn::rational and kairn::integer (rational.cpp): constants computed
#   independently, the checker against results changed by one unit, and the same bits at run time
#   under the four rounding modes; api.rational.K.FORMAT: the oracle's cases of rational_K through
#   rational_runner.cpp (../crosscheck.py compiled). The full tier has more cases, through the runner of every
#   flag set too, and rational.cpp built with every flag set.
# - api.example.*: the documentation's examples (docs/examples/cpp/), which check their own output;
#   api.example.accurate_sums.*, api.example.intervals.*, api.example.bisection.*,
#   api.example.ball_vectors.* and api.example.packed_dot.* also compare it with the text their
#   tutorials show.
# - api.ball_vector.FORM, api.boundary.ball_vector.*, api.reject.ball_vector.*: BallVector
#   (ball_vector.hpp), below; its loops join api.oracle.* as api.oracle.LOOP.FORMAT.
# - api.packed.FORM, api.soa.FORM, api.example.packed_dot.FORM: Packed (packed.hpp) against the
#   scalar operations, bit for bit, lane by lane (packed.cpp); the containers of soa.hpp (soa.cpp);
#   and the tutorial's vector loop, whose results are checked against the bound it states; each in
#   every form of Packed this compiler can build here: native (the build's flags), scalar (one
#   lane, KAIRN_PACKED_FORM_SCALAR) and, on x86-64 where the build's flags do not give AVX2,
#   avx2. The runner's packed forms (runner.cpp) join api.oracle.*; where the build's flags do not
#   give AVX2 and the compiler can, a runner of the packed forms alone built for AVX2 joins those of
#   the kernels that packed.hpp calls.

set(_api_include "${PROJECT_SOURCE_DIR}/include")
if(_msvc_style)
  set(_api_warnings /W4 /WX)
else()
  set(_api_warnings -Wall -Wextra -Wpedantic -Werror)
endif()

function(_kairn_api_program target source)
  add_executable(${target} "${source}")
  target_link_libraries(${target} PRIVATE kairn::kairn kairn::fma)
  target_compile_options(${target} PRIVATE ${_api_warnings} ${ARGN})
endfunction()

# --- Compile time -----------------------------------------------------------------------------
_kairn_api_program(kairn-api-constexpr constexpr.cpp)
add_test(NAME api.constexpr COMMAND kairn-api-constexpr)

# api.platform_macros: the headers after a platform header that defines min, max, small, near, far,
# hyper and interface as macros (<windows.h> without NOMINMAX, included for real on Windows).
_kairn_api_program(kairn-api-platform-macros platform_macros.cpp)
add_test(NAME api.platform_macros COMMAND kairn-api-platform-macros)
set_tests_properties(api.platform_macros PROPERTIES LABELS api)

# --- The public interface against the oracle --------------------------------------------------
#
# The building blocks, which no public operation computes on its own, and the entry kernels that no
# public operation calls yet; runner.cpp lists the same, with why. The building blocks of the
# interval kernels of Milestone 2 (mul_dir_1, the bounds of two limbs, mul_ext_2_2) are in the
# first; every other interval kernel is reached by a public form. The functions on arrays
# (kairn/batch.hpp) reach the kernels of their loops only inside the loops, which the oracle judges
# (api.oracle.FOLD.FORMAT, below): the finishes and the kernels of the folds of maxima, which are
# not entry kernels, are building blocks, and the steps, which are, are on the second list.
set(_api_internal two_sum fast_two_sum split two_prod_dekker radd two_sum_ord add_down_1 add_up_1 sub_down_1
  sub_up_1 mul_dir_1 add_ball_2_2 mul_ball_2_2 add_down_2_2 add_up_2_2 sub_down_2_2 sub_up_2_2 mul_dir_2_2
  mul_ext_2_2 fold_finish_1 fold_finish_2 norm_combine norm_step_1 norm_step_2 norm_finish_1 norm_finish_2
  acc_radius_1 acc_radius_2)
set(_api_not_public ball_add_1 ball_sub_1 ball_mul_1 ball_scale_1 ball_add_2 ball_sub_2 ball_mul_2 ball_scale_2
  ball_mul_pow2_1 ball_mul_pow2_2 sum_entry_step_1 sum_entry_step_2 sum_fast_entry_step_2 add_entry_step_1
  add_entry_step_2 sub_entry_step_1 sub_entry_step_2 mul_pow2_step_1 mul_pow2_step_2 axpy_entry_step_1
  axpy_entry_step_2_1 axpy_entry_step_2 dot_entry_step_1 acc_mul_1)
# The folds that no public function calls (runner_arrays.hpp lists the same, with why): the loops
# on stored arrays, whose callers here call the loops on supplied arrays instead (kairn/batch.hpp),
# and dot_1, whose caller calls dot_1_entry, the same loop with its factors guarded.
set(_api_folds_not_public sum_1 sum_2 sum_fast_2 add_1 add_2 sub_1 sub_2 axpy_1 axpy_2 axpy_2_1 dot_1)
# The loops over arrays that public operations call (kairn/ball_vector.hpp; runner_ball_vector.hpp
# has their forms), each judged as a kernel is, api.oracle.LOOP.FORMAT, on KAIRN_API_LOOP_QUICK_CASES
# requests (KAIRN_API_LOOP_CASES in the full tier); those of them that have forms in the fast order,
# which the runner of the packed forms alone also runs; and the kernels that are parts of those
# loops and that no public operation calls on its own (runner --loop-parts, with the loop of each),
# judged through the loops' forms and, on their own, by the kernels' cross-checks. norm_upper_1 and
# norm_upper_2, which kairn/batch.hpp calls too, are registered here once, with the forms of both
# headers. A kernel that the parts of these loops and the lists above both name is in one list: the
# steps of the scalings and of the dot products (scale_step_k, dot_step_k) are parts of the loops of
# ball_vector.hpp; the kernels of the folds of maxima and the finishes of the folds are building
# blocks (_api_internal), as kairn/batch.hpp has them; bound_dot_k has a public form,
# traits<X>::dot(n).
set(_api_loops bv_make_1 bv_make_2 bv_neg_1 bv_neg_2 bv_add_1 bv_add_2 bv_sub_1 bv_sub_2 bv_scale_1 bv_scale_2
  bv_mul_pow2_1 bv_mul_pow2_2 bv_conv_1 bv_conv_2 norm_upper_1 norm_upper_2)
set(_api_loops_fast bv_neg_1 bv_neg_2 bv_add_1 bv_add_2 bv_sub_1 bv_sub_2 bv_scale_1 bv_scale_2 bv_mul_pow2_1
  bv_mul_pow2_2 norm_upper_1 norm_upper_2)
set(_api_loop_parts bv_center_entry_1 bv_center_2 bv_make_radius bv_make_finish neg_1 bv_neg_radius sub_1_1
  bv_add_radius_1 bv_add_radius_2 scale_step_1 scale_step_2 bv_scale_radius_1 bv_scale_radius_2
  bv_mul_pow2_step_1 bv_mul_pow2_step_2 bv_mul_pow2_radius conv_radius bv_conv_finish dot_step_1 dot_step_2)
set(KAIRN_API_LOOP_CASES 4000 CACHE STRING
  "Random requests per loop, format and form of the public interface judged by the oracle, in the full tier")
set(KAIRN_API_LOOP_QUICK_CASES 1000 CACHE STRING
  "Random requests per loop, format and form of the public interface judged by the oracle, in the quick tier")
# The random arrays are of at most KAIRN_API_LOOP_QUICK_LENGTH entries in the quick tier and of the
# oracle's 256 in the full tier, every length class below them included: on the Mac a test of 1 000
# requests of bv_add_2 took 7.8 seconds with 256 and 2.8 with 64, and the 32 tests of the loops 160
# seconds of test time with 256. The products of polynomials, whose judgment costs the product of the
# two lengths per request, have at most KAIRN_API_LOOP_PRODUCT_LENGTH in both tiers (with 256 a test
# of 1 000 requests took 40 to 50 seconds, with 64 three to four).
set(_api_loops_product bv_conv_1 bv_conv_2)
set(KAIRN_API_LOOP_QUICK_LENGTH 64 CACHE STRING
  "The longest random array of the loops of BallVector judged through the public interface, quick tier")
set(KAIRN_API_LOOP_PRODUCT_LENGTH 64 CACHE STRING
  "The longest random array of the products of polynomials of BallVector judged through the public interface")
set(KAIRN_API_CASES 10000 CACHE STRING
  "Random cases per kernel, format and form of the public interface judged by the oracle, in the full tier")
set(KAIRN_API_QUICK_CASES 2000 CACHE STRING
  "Random cases per kernel, format and form of the public interface judged by the oracle, in the quick tier")
set(KAIRN_API_SEED 1 CACHE STRING "Seed of the random cases of the public interface's tests")

_kairn_api_program(kairn-api-runner runner.cpp)
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contract /fp:contract)
elseif(_msvc_style)
  set(_api_contract /clang:-ffp-contract=fast)
else()
  # At -O2, like the contraction runners of the cross-checks (tests/CMakeLists.txt says why).
  set(_api_contract -ffp-contract=fast -O2)
endif()
_kairn_api_program(kairn-api-runner-contract-fast runner.cpp ${_api_contract})

# The forms of Packed (include/kairn/packed.hpp) that the tests build: native, with the build's
# flags and kairn::fma's option (AVX2, NEON, or the scalar form of one lane, by what they give),
# scalar (forced), and avx2 where the native form is the scalar one on x86-64 and the compiler
# can target AVX2 with the packed backend's option (../CMakeLists.txt, _kairn_packed_backend, as
# for the generator's packed runner: -mavx2 -mfma), which is the case with GCC and Clang there,
# whose kairn::fma adds -mfma alone. KAIRN_TESTS_API_PACKED_SIMD: whether the native form has
# more than one lane.
function(_kairn_api_packed_native out)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  cmake_push_check_state(RESET)
  set(CMAKE_REQUIRED_INCLUDES "${_api_include}")
  get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
  if(_fma)
    list(JOIN _fma " " CMAKE_REQUIRED_FLAGS)
  endif()
  set(CMAKE_REQUIRED_QUIET ON)
  check_cxx_source_compiles("#include <kairn/packed.hpp>
#if KAIRN_PACKED_FORM == KAIRN_PACKED_FORM_SCALAR
#error the scalar form
#endif
int main() { return 0; }
" KAIRN_TESTS_API_PACKED_SIMD)
  cmake_pop_check_state()
  set(${out} "${KAIRN_TESTS_API_PACKED_SIMD}" PARENT_SCOPE)
endfunction()
include(CheckCXXSourceCompiles)
include(CMakePushCheckState)
_kairn_api_packed_native(_api_packed_simd)
if(_msvc_style)
  set(_api_scalar_form /DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR)
else()
  set(_api_scalar_form -DKAIRN_PACKED_FORM=KAIRN_PACKED_FORM_SCALAR)
endif()
set(_api_packed_forms native scalar)
set(_api_packed_avx2 OFF)
if(NOT _api_packed_simd AND _packed_backend STREQUAL "avx2" AND _isa_option)
  set(_api_packed_avx2 ON)
  list(APPEND _api_packed_forms avx2)
  # The packed forms alone, for AVX2, beside the build's runners in api.oracle.* and full.api.oracle.*.
  _kairn_api_program(kairn-api-runner-avx2 runner.cpp ${_isa_option})
  target_compile_definitions(kairn-api-runner-avx2 PRIVATE KAIRN_TEST_PACKED_ONLY)
endif()

# Each test runs the runners, the one with the build's flags and the one with contraction forced
# on (in the full tier, the debug build's too, below), on the same requests, generated once, and
# the oracle on each distinct output, in one Python process (../crosscheck.py api: the oracle's
# gen and check in that process, each runner in its own). The quick tier's KAIRN_API_QUICK_CASES
# are at least 1000, the length of stream at which a form that computes only some lines of its
# kernel must have computed one (runner.cpp); 2000, because with 1000 three more of the faults
# planted in the kernels that the full tier caught went unseen (docs/developer/testing.md,
# "Time").
set(_api_claims "${_oracle_claims}")
# --- The flag sets (flags/) -------------------------------------------------------------------
#
# flags/ builds the public interface's runner and programs once per flag set of
# docs/developer/testing.md ("Flag sets"), and the kernels' runners for two of them, each with
# exactly the options of its set. In the full tier the debug build's runner (_api_debug_runner)
# joins the two above in full.api.oracle.*, on the first form of each kernel only (FIRST_FORM):
# built without optimization and with the checks, it takes two to three times as long, and the
# quick tier leaves it out (docs/developer/testing.md, "Time"). The full tier also runs every form
# of every set's runner, the debug build's included, on the quick tier's KAIRN_API_QUICK_CASES
# cases (full.api.flags.oracle.*) and the kernels' runners in its cross-checks
# (../full/CMakeLists.txt, from the variables _flags_* passed up below).
add_subdirectory(flags)
# The runners as --runner LABEL EXECUTABLE for ../crosscheck.py.
set(_api_runners --runner build "$<TARGET_FILE:kairn-api-runner>"
  --runner contract-fast "$<TARGET_FILE:kairn-api-runner-contract-fast>")
# The runner of the packed forms alone, for the kernels that packed.hpp calls (gen::NAME( in its
# text; api.oracle.coverage checks that they are those of the packed forms), the only ones it has
# forms for.
set(_api_packed_runner "")
if(_api_packed_avx2)
  set(_api_packed_runner --runner avx2 "$<TARGET_FILE:kairn-api-runner-avx2>")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_api_include}/kairn/packed.hpp")
file(READ "${_api_include}/kairn/packed.hpp" _api_packed_text)
string(REGEX MATCHALL "gen::[a-z0-9_]+\\(" _api_packed_calls "${_api_packed_text}")
set(_api_packed_kernels "")
foreach(_call IN LISTS _api_packed_calls)
  string(REGEX REPLACE "gen::([a-z0-9_]+)\\(" "\\1" _k "${_call}")
  list(APPEND _api_packed_kernels ${_k})
endforeach()
list(REMOVE_DUPLICATES _api_packed_kernels)
set(_api_packed_runner ${_api_packed_runner} PARENT_SCOPE)
set(_api_packed_kernels ${_api_packed_kernels} PARENT_SCOPE)
set(_api_debug_runner --runner debug "$<TARGET_FILE:kairn-api-runner-debug>" PARENT_SCOPE)
set(_flags_runners "")
foreach(_set IN LISTS _flags_names)
  list(APPEND _flags_runners --runner "${_set}" "$<TARGET_FILE:kairn-api-runner-${_set}>")
endforeach()
set(_flags_names ${_flags_names} PARENT_SCOPE)
set(_flags_enclosure_sets ${_flags_enclosure_sets} PARENT_SCOPE)
set(_flags_gen_runners ${_flags_gen_runners} PARENT_SCOPE)
set(_flags_gen_labels ${_flags_gen_labels} PARENT_SCOPE)
# --- The end of the flag sets' runners ---------------------------------------------------------
if(Python3_Interpreter_FOUND AND EXISTS "${_api_claims}")
  set(_api_crosscheck "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/crosscheck.py")
  set(_api_common --seed "${KAIRN_API_SEED}" ${_api_runners} ${_oracle_claims_arg})
  file(READ "${_api_claims}" _api_json)
  string(JSON _api_count LENGTH "${_api_json}" kernels)
  math(EXPR _api_last "${_api_count} - 1")
  set(_api_mapped "")
  foreach(_i RANGE ${_api_last})
    string(JSON _kernel GET "${_api_json}" kernels ${_i} name)
    if(_kernel IN_LIST _api_internal OR _kernel IN_LIST _api_not_public OR _kernel IN_LIST _api_loop_parts)
      continue()
    endif()
    # The kernels the oracle does not judge yet (KAIRN_NOT_YET_CROSS_CHECKED, ../CMakeLists.txt),
    # and those that no public operation calls yet and the runner does not list
    # (KAIRN_NOT_PUBLIC_YET, there: the folds' stage of Milestone 2): no form to judge.
    if(_kernel IN_LIST KAIRN_NOT_YET_CROSS_CHECKED OR _kernel IN_LIST KAIRN_NOT_PUBLIC_YET)
      continue()
    endif()
    list(APPEND _api_mapped ${_kernel})
    set(_extra "")
    if(_kernel IN_LIST _api_packed_kernels)
      set(_extra ${_api_packed_runner})
    endif()
    foreach(_format binary64 binary32)
      set(_name api.oracle.${_kernel}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_api_crosscheck} api --kernel ${_kernel} --format ${_format}
          --count ${KAIRN_API_QUICK_CASES} --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/oracle"
          ${_api_common} ${_extra})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle")
    endforeach()
  endforeach()
  # The functions on arrays (kairn/batch.hpp): api.oracle.FOLD.FORMAT, every public form of each fold
  # of gen/claims.json that a public function calls (runner_arrays.hpp), on random arrays of the
  # oracle's generator in the sequential order (each form computes its own order: the claims of a
  # fold are the same in both), as many and as long as the quick tier's cross-checks of that kind
  # of fold (../CMakeLists.txt: KAIRN_CROSSCHECK_FOLD_QUICK_*, _MAP_QUICK_*, _CONV_QUICK_LENGTH);
  # a map also on a second stream in place (crosscheck.py api --inplace). The runner of the packed
  # forms alone, for AVX2, joins every fold but the convolutions, which have no packed loop. The
  # folds on stored arrays have no public caller (_api_folds_not_public, with the runner's
  # --folds-not-public), and neither have the folds of KAIRN_NOT_PUBLIC_YET_FOLDS (../CMakeLists.txt). The loops of
  # kairn/ball_vector.hpp (_api_loops, norm_upper_k among them) are registered below, once.
  string(JSON _api_fold_count ERROR_VARIABLE _api_no_folds LENGTH "${_api_json}" folds)
  if(_api_no_folds)
    set(_api_fold_count 0)
  endif()
  set(_api_folds "")
  if(_api_fold_count GREATER 0)
    math(EXPR _api_fold_last "${_api_fold_count} - 1")
    foreach(_i RANGE ${_api_fold_last})
      string(JSON _fold GET "${_api_json}" folds ${_i} name)
      if(_fold IN_LIST _api_folds_not_public OR _fold IN_LIST KAIRN_NOT_PUBLIC_YET_FOLDS
         OR _fold IN_LIST KAIRN_NOT_YET_CROSS_CHECKED_FOLDS OR _fold IN_LIST _api_loops)
        continue()
      endif()
      list(APPEND _api_folds ${_fold})
      string(JSON _is_map ERROR_VARIABLE _no_map GET "${_api_json}" folds ${_i} map)
      string(JSON _is_conv ERROR_VARIABLE _no_conv GET "${_api_json}" folds ${_i} conv)
      string(JSON _kind0 ERROR_VARIABLE _no_kind0 GET "${_api_json}" folds ${_i} ensures 0 kind)
      set(_count ${KAIRN_CROSSCHECK_FOLD_QUICK_CASES})
      set(_length ${KAIRN_CROSSCHECK_FOLD_QUICK_LENGTH})
      set(_full_count ${KAIRN_CROSSCHECK_FOLD_CASES})
      set(_full_length ${KAIRN_CROSSCHECK_FOLD_LENGTH})
      set(_inplace "")
      set(_extra ${_api_packed_runner})
      if(_is_map AND NOT _no_map)
        set(_count ${KAIRN_CROSSCHECK_MAP_QUICK_CASES})
        set(_length ${KAIRN_CROSSCHECK_MAP_QUICK_LENGTH})
        set(_full_length ${KAIRN_CROSSCHECK_MAP_LENGTH})
        set(_inplace --inplace)
      elseif(_is_conv AND NOT _no_conv)
        set(_count ${KAIRN_CROSSCHECK_MAP_QUICK_CASES})
        set(_length ${KAIRN_CROSSCHECK_CONV_QUICK_LENGTH})
        set(_full_count ${KAIRN_CROSSCHECK_CONV_CASES})
        set(_full_length ${KAIRN_CROSSCHECK_CONV_LENGTH})
        set(_extra "")
      elseif(_kind0 STREQUAL "upper")
        set(_count ${KAIRN_CROSSCHECK_MAP_QUICK_CASES})
        set(_length ${KAIRN_CROSSCHECK_MAP_QUICK_LENGTH})
        set(_full_length ${KAIRN_CROSSCHECK_MAP_LENGTH})
      endif()
      set(_api_fold_${_fold}_args --orders seq ${_inplace} PARENT_SCOPE)
      set(_api_fold_${_fold}_quick --count ${_count} --max-length ${_length} PARENT_SCOPE)
      set(_api_fold_${_fold}_extra ${_extra} PARENT_SCOPE)
      set(_api_fold_${_fold}_full_count ${_full_count} PARENT_SCOPE)
      set(_api_fold_${_fold}_full_length ${_full_length} PARENT_SCOPE)
      foreach(_format binary64 binary32)
        set(_name api.oracle.${_fold}.${_format})
        add_test(NAME ${_name}
          COMMAND ${_api_crosscheck} api --kernel ${_fold} --format ${_format} --count ${_count}
            --orders seq --max-length ${_length} ${_inplace} --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/oracle"
            ${_api_common} ${_extra})
        set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle;arrays")
      endforeach()
    endforeach()
  endif()
  set(_api_oracle_folds ${_api_folds} PARENT_SCOPE)
  # The loops, by their names in the claims' "folds" (a loop the claims in use do not have is left
  # out, as a kernel is).
  string(JSON _api_n_folds LENGTH "${_api_json}" folds)
  math(EXPR _api_last_fold "${_api_n_folds} - 1")
  set(_api_claim_folds "")
  foreach(_i RANGE ${_api_last_fold})
    string(JSON _fold GET "${_api_json}" folds ${_i} name)
    list(APPEND _api_claim_folds ${_fold})
  endforeach()
  set(_api_mapped_loops "")
  foreach(_loop IN LISTS _api_loops)
    if(NOT _loop IN_LIST _api_claim_folds OR _loop IN_LIST KAIRN_NOT_YET_CROSS_CHECKED_FOLDS)
      continue()
    endif()
    list(APPEND _api_mapped_loops ${_loop})
    set(_extra "")
    if(_loop IN_LIST _api_loops_fast)
      set(_extra ${_api_packed_runner})
    endif()
    set(_length ${KAIRN_API_LOOP_QUICK_LENGTH})
    if(_loop IN_LIST _api_loops_product AND KAIRN_API_LOOP_PRODUCT_LENGTH LESS _length)
      set(_length ${KAIRN_API_LOOP_PRODUCT_LENGTH})
    endif()
    list(APPEND _extra --max-length ${_length})
    foreach(_format binary64 binary32)
      set(_name api.oracle.${_loop}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_api_crosscheck} api --kernel ${_loop} --format ${_format}
          --count ${KAIRN_API_LOOP_QUICK_CASES} --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/oracle"
          ${_api_common} ${_extra})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle")
    endforeach()
  endforeach()
  set(_api_oracle_loops ${_api_mapped_loops} PARENT_SCOPE)
  set(_api_loops_fast ${_api_loops_fast} PARENT_SCOPE)
  set(_api_loops_product ${_api_loops_product} PARENT_SCOPE)
  # For ../full/CMakeLists.txt, which registers the same on KAIRN_API_CASES cases, and every form of
  # the flag sets' runners on KAIRN_API_QUICK_CASES.
  set(_api_oracle_kernels ${_api_mapped} PARENT_SCOPE)
  set(_api_oracle_common ${_api_common} PARENT_SCOPE)
  set(_api_flags_common --seed "${KAIRN_API_SEED}" ${_flags_runners} ${_oracle_claims_arg}
    PARENT_SCOPE)
  set(_api_unlisted ${KAIRN_NOT_YET_CROSS_CHECKED} ${KAIRN_NOT_PUBLIC_YET})
  # The runner's lists against the listings of gen/kernels and every kernel of gen/claims.json,
  # whatever claims the oracle reads (KAIRN_ORACLE_CLAIMS): the runner is built from them all.
  add_test(NAME api.oracle.coverage
    COMMAND "${CMAKE_COMMAND}" "-DRUNNER=$<TARGET_FILE:kairn-api-runner>"
      "-DCLAIMS=${PROJECT_SOURCE_DIR}/gen/claims.json"
      "-DKERNELS=${PROJECT_SOURCE_DIR}/gen/kernels" "-DINTERNAL=${_api_internal}"
      "-DNOT_PUBLIC=${_api_not_public}" "-DNOT_CHECKED=${_api_unlisted}"
      "-DFOLDS_NOT_PUBLIC=${_api_folds_not_public}"
      "-DFOLDS_NOT_CHECKED=${KAIRN_NOT_YET_CROSS_CHECKED_FOLDS};${KAIRN_NOT_PUBLIC_YET_FOLDS}"
      "-DLOOPS=${_api_loops}" "-DLOOP_PARTS=${_api_loop_parts}"
      "-DPACKED_HEADER=${_api_include}/kairn/packed.hpp" -P "${CMAKE_CURRENT_SOURCE_DIR}/coverage.cmake")
  set_tests_properties(api.oracle.coverage PROPERTIES LABELS "api;oracle")
  list(LENGTH _api_mapped _n)
  list(LENGTH _flags_names _n_flags)
  set(_api_n_runners 2)
  set(_api_packed_note "")
  if(_api_packed_avx2)
    set(_api_n_runners 3)
    set(_api_packed_note " (the third, of the packed forms alone, for AVX2, on the kernels of packed.hpp)")
  endif()
  list(JOIN _api_packed_forms ", " _api_forms_text)
  list(LENGTH _api_mapped_loops _n_loops)
  message(STATUS "Kairn tests: the public interface of ${_n} kernels and ${_n_loops} loops against the oracle, with ${_api_n_runners} "
    "runners${_api_packed_note}, and in the full tier the debug build's on the first form of each and the runners "
    "of ${_n_flags} flag sets; Packed in the forms ${_api_forms_text}")
endif()

# --- Packed and the containers ----------------------------------------------------------------
#
# api.packed.FORM (packed.cpp): every operation of Packed against the scalar operation of
# Expansion, lane by lane, bit for bit (the products of one limb but for the sign of a zero), on a
# corpus with every kind of value; api.soa.FORM (soa.cpp): the containers, element read equals
# value written, the tail rule, views of the program's arrays, the types' properties and the
# allocations. FORM as above (native, scalar, and avx2 where it applies). Their compile-fail cases
# are api.reject.soa.* and api.reject.packed.* (below), their checks with KAIRN_CHECKS
# api.checks.* (checks.cpp, checks_cases.hpp).
foreach(_form IN LISTS _api_packed_forms)
  set(_options "")
  if(_form STREQUAL "scalar")
    set(_options ${_api_scalar_form})
  elseif(_form STREQUAL "avx2")
    set(_options ${_isa_option})
  endif()
  _kairn_api_program(kairn-api-packed-${_form} packed.cpp ${_options})
  add_test(NAME api.packed.${_form} COMMAND kairn-api-packed-${_form})
  _kairn_api_program(kairn-api-soa-${_form} soa.cpp ${_options})
  add_test(NAME api.soa.${_form} COMMAND kairn-api-soa-${_form})
  set_tests_properties(api.packed.${_form} api.soa.${_form} PROPERTIES TIMEOUT 120 LABELS "api;packed")
  # The functions on arrays (batch.cpp): each calls its loop, in its order; the flags; the edges.
  _kairn_api_program(kairn-api-batch-${_form} batch.cpp ${_options})
  add_test(NAME api.batch.${_form} COMMAND kairn-api-batch-${_form})
  set_tests_properties(api.batch.${_form} PROPERTIES TIMEOUT 120 LABELS "api;packed;arrays")
  # api.ball_vector.FORM (ball_vector.cpp): BallVector and its views, in this form of Packed, whose
  # lane order is the fast order of the functions on arrays: the types, the constructors, the two
  # orders bit for bit, in place, the value forms, Ball entry by entry, the composition of axpy, the
  # argument of norm_upper, the exact scaling by a power of two.
  _kairn_api_program(kairn-api-ball-vector-${_form} ball_vector.cpp ${_options})
  add_test(NAME api.ball_vector.${_form} COMMAND kairn-api-ball-vector-${_form})
  set_tests_properties(api.ball_vector.${_form} PROPERTIES TIMEOUT 120 LABELS "api;packed;ball_vector")
endforeach()

# --- The bounds as functions of the length, and the accumulator, in exact arithmetic -----------
#
# api.arrays.exact.KIND (arrays_exact.cpp computes through the public headers, arrays_exact.py
# checks with Python's fractions): bounds, kairn::traits<X>::sum(n) and dot(n) at the lengths where
# the count is converted to T exactly and where it is rounded up, against gamma_m(e) and the
# underflow term of the proved statements, +infinity exactly where no bound is given; accumulator,
# histories of kairn::Accumulator (random trees of add, add_product and merge, empty ones, counts
# where their conversion to T rounds, a count that saturates, overflows, terms that are not finite)
# against their exact sums, the radius never finite where the theorem gives none.
_kairn_api_program(kairn-api-arrays-exact arrays_exact.cpp)
# api.accumulator (accumulator.cpp): the accumulator in constant evaluation, its merges, from_state,
# the count and what it returns when something is not finite.
_kairn_api_program(kairn-api-accumulator accumulator.cpp)
add_test(NAME api.accumulator COMMAND kairn-api-accumulator)
set_tests_properties(api.accumulator PROPERTIES TIMEOUT 120 LABELS "api;arrays")
if(Python3_Interpreter_FOUND)
  foreach(_kind bounds accumulator)
    add_test(NAME api.arrays.exact.${_kind}
      COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/arrays_exact.py"
        "$<TARGET_FILE:kairn-api-arrays-exact>" ${_kind})
    set_tests_properties(api.arrays.exact.${_kind} PROPERTIES TIMEOUT 300 LABELS "api;arrays")
  endforeach()
endif()

# --- kairn::rational -------------------------------------------------------------------------
#
# rational.hpp computes with integers only, so contraction and the other flags cannot change its
# result: one runner here, with the build's flags; the full tier adds the runner of every flag set
# (flags/), whose outputs must be the same bytes. The specification fixes every bit, so the oracle
# judges each line for equality (docs/reference/rational.md). KAIRN_RATIONAL_QUICK_CASES: the
# runner completes 2 000 lines in a few hundredths of a second; the rest of each test is the
# oracle's Python.
_kairn_api_program(kairn-api-rational rational.cpp)
add_test(NAME api.rational.constexpr COMMAND kairn-api-rational)
set_tests_properties(api.rational.constexpr PROPERTIES LABELS "api;rational")
_kairn_api_program(kairn-api-rational-runner rational_runner.cpp)
set(KAIRN_RATIONAL_CASES 20000 CACHE STRING "Cases per kind and format of kairn::rational judged by the oracle, in the full tier")
set(KAIRN_RATIONAL_QUICK_CASES 2000 CACHE STRING
  "Cases per kind and format of kairn::rational judged by the oracle, in the quick tier")
if(Python3_Interpreter_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/oracle/kairn-oracle")
  # The driver of the kernels' cross-checks, in one process: the oracle's requests, the runner,
  # the oracle's verdict and the guards (../crosscheck.py compiled, which knows rational_K without
  # claims; ../crosscheck_guards.py: every stratum, exact and inexact cases, den = 0 and, for two
  # limbs, a pair that the two roundings alone do not normalize).
  set(_api_rational_common "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/crosscheck.py" compiled
    --seed "${KAIRN_API_SEED}" --fail-on-suspicious ${_oracle_claims_arg})
  foreach(_kind 1 2)
    foreach(_format binary64 binary32)
      set(_name api.rational.${_kind}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_api_rational_common} --kernel rational_${_kind} --format ${_format}
          --count ${KAIRN_RATIONAL_QUICK_CASES}
          --summary "${CMAKE_CURRENT_BINARY_DIR}/rational/rational_${_kind}.${_format}.json"
          --runner build "$<TARGET_FILE:kairn-api-rational-runner>")
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "api;oracle;rational")
    endforeach()
  endforeach()
  # For ../full/CMakeLists.txt.
  set(_api_rational_common ${_api_rational_common} PARENT_SCOPE)
endif()

# --- Products of the program passed into Kairn ------------------------------------------------
#
# boundary.cpp, under the build's flags and each contraction setting that matters to the compiler:
# with the guard, every form must agree with the same operation on the rounded product
# (api.boundary.*). Built again with the guard taken out (api.boundary.unguarded.*), some form
# must differ where the compiler was measured to fuse across statements, so that the first test
# cannot pass for want of a compiler that fuses; elsewhere that build only reports.
#
# The guard is an operation of the generated kernels (rule R3), emitted as
# `__builtin_is_constant_evaluated() ? a : a + 0.0`. The unguarded build compiles against a copy of
# the headers in which every such line of include/kairn/gen/scalar.hpp keeps only `a`: the
# generator has no switch for it, and needs none for anything but this test. The copy is made at
# configure time, and fails the configuration if it finds no guard to take out or leaves one.
set(_api_unguarded "${CMAKE_CURRENT_BINARY_DIR}/unguarded-fixture")
set(_api_scalar "${_api_include}/kairn/gen/scalar.hpp")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_api_scalar}")
file(REMOVE_RECURSE "${_api_unguarded}")
file(COPY "${_api_include}/kairn" DESTINATION "${_api_unguarded}")
file(READ "${_api_scalar}" _api_text)
string(REGEX MATCHALL "__builtin_is_constant_evaluated\\(\\) \\? ([A-Za-z0-9_]+) : [A-Za-z0-9_]+ \\+ 0\\.0f?;"
  _api_guards "${_api_text}")
list(LENGTH _api_guards _api_n)
string(REGEX REPLACE "__builtin_is_constant_evaluated\\(\\) \\? ([A-Za-z0-9_]+) : ([A-Za-z0-9_]+) \\+ 0\\.0f?;"
  "\\1;" _api_text "${_api_text}")
# The folds over arrays of the program (the loops at the end of the file) are not constexpr, and
# write their guards `a + 0.0`: those are taken out too, though no form here calls them yet.
string(REGEX MATCHALL "= [A-Za-z0-9_]+ \\+ 0\\.0f?;" _api_fold_guards "${_api_text}")
list(LENGTH _api_fold_guards _api_n_folds)
math(EXPR _api_n "${_api_n} + ${_api_n_folds}")
string(REGEX REPLACE "= ([A-Za-z0-9_]+) \\+ 0\\.0f?;" "= \\1;" _api_text "${_api_text}")
string(REGEX MATCHALL "\\+ 0\\.0f?;" _api_left "${_api_text}")
if(_api_n EQUAL 0 OR _api_left)
  message(FATAL_ERROR "tests/api: could not take the guard out of ${_api_scalar} (${_api_n} found)")
endif()
file(WRITE "${_api_unguarded}/kairn/gen/scalar.hpp" "${_api_text}")
# The packed kernels write the same guard with the intrinsics of their form:
# `_mm256_add_pd(a, _mm256_setzero_pd())` in include/kairn/gen/avx2.hpp and
# `vaddq_f64(a, vdupq_n_f64(0.0))` in gen/neon.hpp, and the same for float. Each such addition keeps
# only `a` in the copy, for boundary_packed.cpp (below), with the same failure if a header has none
# or keeps one. Neither header has another addition of zero.
foreach(_api_form avx2 neon)
  set(_api_header "${_api_include}/kairn/gen/${_api_form}.hpp")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_api_header}")
  file(READ "${_api_header}" _api_text)
  if(_api_form STREQUAL "avx2")
    set(_api_guard "_mm256_add_p[sd]\\(([A-Za-z0-9_]+), _mm256_setzero_p[sd]\\(\\)\\)")
    set(_api_kept "\\1")
    set(_api_rest "_mm256_add_p[sd]\\([A-Za-z0-9_]+, _mm256_setzero_p[sd]\\(\\)\\)")
  else()
    set(_api_guard "vaddq_f(64|32)\\(([A-Za-z0-9_]+), vdupq_n_f(64|32)\\(0\\.0f?\\)\\)")
    set(_api_kept "\\2")
    set(_api_rest "vaddq_f(64|32)\\([A-Za-z0-9_]+, vdupq_n_f(64|32)\\(0\\.0f?\\)\\)")
  endif()
  string(REGEX MATCHALL "${_api_guard}" _api_guards "${_api_text}")
  list(LENGTH _api_guards _api_n)
  string(REGEX REPLACE "${_api_guard}" "${_api_kept}" _api_text "${_api_text}")
  string(REGEX MATCHALL "${_api_rest}" _api_left "${_api_text}")
  if(_api_n EQUAL 0 OR _api_left)
    message(FATAL_ERROR "tests/api: could not take the guard out of ${_api_header} (${_api_n} found)")
  endif()
  file(WRITE "${_api_unguarded}/kairn/gen/${_api_form}.hpp" "${_api_text}")
endforeach()
# The forms of Packed for boundary_packed.cpp: native where it has more than one lane (elsewhere it
# is the scalar form), scalar, and avx2 where it applies (above).
set(_api_boundary_forms scalar)
if(_api_packed_simd)
  list(PREPEND _api_boundary_forms native)
endif()
if(_api_packed_avx2)
  list(APPEND _api_boundary_forms avx2)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_contraction "" "" fp-precise /fp:precise fp-contract /fp:contract fp-strict /fp:strict)
elseif(_msvc_style)
  set(_api_contraction "" "" fp-strict /fp:strict fp-precise /fp:precise fp-contract /fp:contract
    contract-fast /clang:-ffp-contract=fast)
else()
  set(_api_contraction "" "" contract-off -ffp-contract=off contract-on -ffp-contract=on
    contract-fast -ffp-contract=fast)
endif()
list(LENGTH _api_contraction _n)
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _api_contraction ${_i} _variant)
  list(GET _api_contraction ${_j} _option)
  if(_variant STREQUAL "")
    set(_suffix "")
  else()
    set(_suffix ".${_variant}")
  endif()
  # Where the unguarded build was measured to fuse: GCC by default (it contracts across statements
  # in C++) and with =fast; Clang with =fast on AArch64 (every two-limb form); MSVC with
  # /fp:contract. Clang 18 on x86-64 fused nothing without the guard, and clang-cl was not
  # measured: their builds only report.
  set(_fuses OFF)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND (_variant STREQUAL "" OR _variant STREQUAL "contract-fast"))
    set(_fuses ON)
  elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style AND _variant STREQUAL "contract-fast"
         AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
    set(_fuses ON)
  elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" AND _variant STREQUAL "fp-contract")
    set(_fuses ON)
  endif()
  string(REPLACE "." "-" _target_suffix "${_suffix}")
  # The third kind of form, the other factor a constant the compiler sees (rule R3, the factors of a
  # fused operation; boundary.cpp, --factor): with the guard every form must agree (--factor none);
  # the copy without the guard requires a difference where a compiler was measured to fuse such a
  # product. Measured (docs/developer/testing.md, "Products of the program passed into Kairn"): Apple
  # clang 21 on AArch64 with =fast, at -O1 and -O2, in two_prod, mul_down, mul_up and
  # finite::mul(E2, T), whose kernels have no guard on their factors, so that this build fails with
  # the guard too, a finding kept failing until the owner decides; GCC 13 and 16 and Clang 18 on
  # x86-64 fused none of these forms, at any setting. Elsewhere the copy only reports.
  set(_factor report)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND _variant STREQUAL "contract-fast")
    set(_factor some)
  endif()
  # At -O2, where Clang was measured to fuse every form without the guard (at -O3 fewer); MSVC's
  # Release is /O2 already.
  set(_level "")
  if(NOT _msvc_style)
    set(_level -O2)
  endif()
  _kairn_api_program(kairn-api-boundary${_target_suffix} boundary.cpp ${_level} ${_option})
  add_test(NAME api.boundary${_suffix} COMMAND kairn-api-boundary${_target_suffix} --expect none --factor none)
  add_executable(kairn-api-boundary-unguarded${_target_suffix} boundary.cpp)
  target_include_directories(kairn-api-boundary-unguarded${_target_suffix} BEFORE PRIVATE "${_api_unguarded}")
  target_link_libraries(kairn-api-boundary-unguarded${_target_suffix} PRIVATE kairn::fma)
  target_compile_features(kairn-api-boundary-unguarded${_target_suffix} PRIVATE cxx_std_20)
  target_compile_options(kairn-api-boundary-unguarded${_target_suffix} PRIVATE ${_api_warnings} ${_level} ${_option})
  target_compile_definitions(kairn-api-boundary-unguarded${_target_suffix} PRIVATE KAIRN_TEST_UNGUARDED_COPY)
  if(_fuses)
    add_test(NAME api.boundary.unguarded${_suffix} COMMAND kairn-api-boundary-unguarded${_target_suffix} --expect some
      --factor ${_factor})
  else()
    add_test(NAME api.boundary.unguarded${_suffix} COMMAND kairn-api-boundary-unguarded${_target_suffix} --expect report
      --factor ${_factor})
  endif()
  set_tests_properties(api.boundary${_suffix} api.boundary.unguarded${_suffix} PROPERTIES LABELS "api;boundary")
  # The same for BallVector (boundary_ball_vector.cpp, in the build's form of Packed): a center, a
  # radius and arrays of centers that the program computes as products, into each constructor.
  # Against the copy without the guards no compiler measured fused a product into a ball vector
  # (GCC 13 and 16, Apple clang 21 and Clang 18, at -O2 and -O3, each contraction setting: the
  # loops of the constructors and of the operations are calls of their own there), so that build
  # only reports. Its forms of the third kind, a product of the program as a factor beside a
  # constant the compiler sees (the scalings and axpy, --factor): with the guards every form must
  # agree; without them the copy reports, no compiler having been measured to fuse one.
  _kairn_api_program(kairn-api-boundary-ball-vector${_target_suffix} boundary_ball_vector.cpp ${_level} ${_option})
  add_test(NAME api.boundary.ball_vector${_suffix}
    COMMAND kairn-api-boundary-ball-vector${_target_suffix} --expect none --factor none)
  add_executable(kairn-api-boundary-ball-vector-unguarded${_target_suffix} boundary_ball_vector.cpp)
  target_include_directories(kairn-api-boundary-ball-vector-unguarded${_target_suffix} BEFORE PRIVATE "${_api_unguarded}")
  target_link_libraries(kairn-api-boundary-ball-vector-unguarded${_target_suffix} PRIVATE kairn::fma)
  target_compile_features(kairn-api-boundary-ball-vector-unguarded${_target_suffix} PRIVATE cxx_std_20)
  target_compile_options(kairn-api-boundary-ball-vector-unguarded${_target_suffix} PRIVATE ${_api_warnings} ${_level}
    ${_option})
  target_compile_definitions(kairn-api-boundary-ball-vector-unguarded${_target_suffix} PRIVATE KAIRN_TEST_UNGUARDED_COPY)
  add_test(NAME api.boundary.ball_vector.unguarded${_suffix}
    COMMAND kairn-api-boundary-ball-vector-unguarded${_target_suffix} --expect report --factor report)
  set_tests_properties(api.boundary.ball_vector${_suffix} api.boundary.ball_vector.unguarded${_suffix}
    PROPERTIES LABELS "api;boundary;ball_vector")
  # The same for Packed and the containers (boundary_packed.cpp), in each form above:
  # api.boundary.packed.FORM.*, and against the copy without the guard, the packed guards taken out
  # too, api.boundary.packed.unguarded.FORM.*.
  foreach(_form IN LISTS _api_boundary_forms)
    set(_form_options "")
    if(_form STREQUAL "scalar")
      set(_form_options ${_api_scalar_form})
    elseif(_form STREQUAL "avx2")
      set(_form_options ${_isa_option})
    endif()
    set(_target kairn-api-boundary-packed-${_form}${_target_suffix})
    _kairn_api_program(${_target} boundary_packed.cpp ${_level} ${_option} ${_form_options})
    add_test(NAME api.boundary.packed.${_form}${_suffix} COMMAND ${_target} --expect none --factor none)
    add_executable(${_target}-unguarded boundary_packed.cpp)
    target_include_directories(${_target}-unguarded BEFORE PRIVATE "${_api_unguarded}")
    target_link_libraries(${_target}-unguarded PRIVATE kairn::fma)
    target_compile_features(${_target}-unguarded PRIVATE cxx_std_20)
    target_compile_options(${_target}-unguarded PRIVATE ${_api_warnings} ${_level} ${_option} ${_form_options})
    target_compile_definitions(${_target}-unguarded PRIVATE KAIRN_TEST_UNGUARDED_COPY)
    # Where the unguarded build was measured to fuse a product into Packed: GCC by default and with
    # =fast, in every form (GCC 16 on AArch64, NEON and scalar; GCC 13 on x86-64, AVX2 and scalar,
    # with and without -mavx2 -mfma in the build's flags); Apple clang 21 with =fast, NEON and
    # scalar; Clang 18 on Linux AArch64 with =fast in the scalar form only (it fused no product
    # written with the NEON intrinsics: 0 of 40 000 registers in every form). Clang 18 on x86-64
    # fused nothing without the guard, in either form and at any setting, and MSVC and clang-cl
    # were not measured with Packed: their builds only report.
    set(_fuses_packed OFF)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND (_variant STREQUAL "" OR _variant STREQUAL "contract-fast"))
      set(_fuses_packed ON)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style AND _variant STREQUAL "contract-fast"
           AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$"
           AND (CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" OR _form STREQUAL "scalar"))
      set(_fuses_packed ON)
    endif()
    if(_fuses_packed)
      set(_expect some)
    else()
      set(_expect report)
    endif()
    # The products of Packed with a factor the compiler sees (--factor): measured to fuse with Apple
    # clang 21 and =fast at -O2, in the NEON form (every product of Packed<T, 2> and Packed<T, 1>)
    # and the scalar form (finite::mul); with the guard too, as in boundary.cpp. Nothing fused with
    # GCC 13 and 16 and Clang 18 on x86-64, in any form.
    set(_factor_packed report)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND _variant STREQUAL "contract-fast"
       AND (_form STREQUAL "native" OR _form STREQUAL "scalar"))
      set(_factor_packed some)
    endif()
    add_test(NAME api.boundary.packed.unguarded.${_form}${_suffix} COMMAND ${_target}-unguarded --expect ${_expect}
      --factor ${_factor_packed})
    set_tests_properties(api.boundary.packed.${_form}${_suffix} api.boundary.packed.unguarded.${_form}${_suffix}
      PROPERTIES LABELS "api;boundary;packed")
    # The same for the functions on arrays (boundary_batch.cpp): arrays the program fills with
    # products, passed into the sums, the maps and axpy; api.boundary.arrays.FORM.* and, against the
    # copy without the guard, api.boundary.arrays.unguarded.FORM.*. At -O3, where the compilers
    # inline the loops of one limb into the function that fills the arrays (at -O2 none did, and
    # the copy without the guard then shows nothing). Measured to fuse without the guard (the sums
    # of one limb in both forms, and the difference of one limb in the scalar form): GCC 16 on
    # AArch64 by default and with =fast, and Apple clang 21 with =fast, in the NEON and the scalar
    # forms; Clang 18 on x86-64 with =fast, in the scalar and the AVX2 forms. GCC 13 on x86-64 fused
    # nothing without the guard, in either form, under any setting. Elsewhere it only reports.
    set(_target kairn-api-boundary-arrays-${_form}${_target_suffix})
    set(_o3 "")
    if(NOT _msvc_style)
      set(_o3 -O3)
    endif()
    _kairn_api_program(${_target} boundary_batch.cpp ${_o3} ${_option} ${_form_options})
    add_test(NAME api.boundary.arrays.${_form}${_suffix} COMMAND ${_target} --expect none --factor none)
    add_executable(${_target}-unguarded boundary_batch.cpp)
    target_include_directories(${_target}-unguarded BEFORE PRIVATE "${_api_unguarded}")
    target_link_libraries(${_target}-unguarded PRIVATE kairn::fma)
    target_compile_features(${_target}-unguarded PRIVATE cxx_std_20)
    target_compile_options(${_target}-unguarded PRIVATE ${_api_warnings} ${_o3} ${_option} ${_form_options})
    target_compile_definitions(${_target}-unguarded PRIVATE KAIRN_TEST_UNGUARDED_COPY)
    set(_fuses_arrays OFF)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND (_variant STREQUAL "" OR _variant STREQUAL "contract-fast")
       AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
      set(_fuses_arrays ON)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND _variant STREQUAL "contract-fast")
      set(_fuses_arrays ON)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang" AND NOT _msvc_style AND _variant STREQUAL "contract-fast"
           AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
      set(_fuses_arrays ON)
    endif()
    if(_fuses_arrays)
      set(_expect some)
    else()
      set(_expect report)
    endif()
    # The arrays and values with a factor the compiler sees (--factor): measured to fuse without the
    # guard, in the dot product of one limb (dot_1_entry's guards taken out), with Clang 18 on x86-64
    # and =fast in the scalar form (not in the AVX2 form), and with Apple clang 21 and =fast in the
    # NEON and the scalar forms. GCC 13 and 16 fused none. Elsewhere the copy only reports.
    set(_factor_arrays report)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND _variant STREQUAL "contract-fast"
       AND (_form STREQUAL "native" OR _form STREQUAL "scalar"))
      set(_factor_arrays some)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang" AND NOT _msvc_style AND _variant STREQUAL "contract-fast"
           AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$" AND _form STREQUAL "scalar")
      set(_factor_arrays some)
    endif()
    add_test(NAME api.boundary.arrays.unguarded.${_form}${_suffix} COMMAND ${_target}-unguarded --expect ${_expect}
      --factor ${_factor_arrays})
    set_tests_properties(api.boundary.arrays.${_form}${_suffix} api.boundary.arrays.unguarded.${_form}${_suffix}
      PROPERTIES LABELS "api;boundary;arrays")
  endforeach()
endforeach()

# --- The environment and the self-test --------------------------------------------------------
_kairn_api_program(kairn-api-environment environment.cpp)
add_test(NAME api.environment COMMAND kairn-api-environment)

# Clang has no macro for these flag sets, so config.hpp cannot reject them, and the self-test must
# catch them at run time. Each is built only if it compiles here (Clang 18 defines __FAST_MATH__ for
# -ffp-model=fast, which config.hpp rejects), and only where the oracle found that it breaks the
# kernels: -fno-signed-zeros with -ffp-contract=fast breaks x * y with Apple clang 21 on AArch64,
# where an opaque product is folded back into a plain one and contracted. With Clang 18 it breaks
# nothing, on x86-64 and on AArch64 Linux alike (there, 4 000 cases of each of eight kernels pass
# the oracle at -O2 and -O3), and the self-test then rightly passes: the case is registered for
# Apple clang only. A later Clang on AArch64 Linux has not been measured.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang" AND NOT _msvc_style)
  include(CheckCXXSourceCompiles)
  include(CMakePushCheckState)
  set(_api_unsafe
    reassociation "-O2 -fassociative-math -fno-signed-zeros -fno-trapping-math"
    fp-model-fast "-O2 -ffp-model=fast")
  if(CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang" AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
    list(APPEND _api_unsafe signed-zeros-contraction "-O2 -fno-signed-zeros -ffp-contract=fast")
  endif()
  list(LENGTH _api_unsafe _n)
  math(EXPR _last "${_n} - 1")
  get_target_property(_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
  if(NOT _fma)
    set(_fma "")
  endif()
  list(JOIN _fma " " _fma_text)
  foreach(_i RANGE 0 ${_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _api_unsafe ${_i} _label)
    list(GET _api_unsafe ${_j} _flags_text)
    separate_arguments(_flags UNIX_COMMAND "${_flags_text}")
    cmake_push_check_state(RESET)
    set(CMAKE_REQUIRED_INCLUDES "${_api_include}")
    set(CMAKE_REQUIRED_FLAGS "-std=c++20 ${_flags_text} ${_fma_text}")
    set(CMAKE_REQUIRED_QUIET ON)
    check_cxx_source_compiles("#include <kairn/kairn.hpp>\nint main() { return 0; }\n" KAIRN_API_UNSAFE_${_i})
    cmake_pop_check_state()
    if(KAIRN_API_UNSAFE_${_i})
      add_executable(kairn-api-unsafe-${_label} selftest_unsafe.cpp)
      target_link_libraries(kairn-api-unsafe-${_label} PRIVATE kairn::kairn kairn::fma)
      target_compile_options(kairn-api-unsafe-${_label} PRIVATE ${_flags})
      add_test(NAME api.self_test.unsafe.${_label} COMMAND kairn-api-unsafe-${_label})
      set_tests_properties(api.self_test.unsafe.${_label} PROPERTIES LABELS api)
    endif()
  endforeach()
endif()

# --- The debug build and the checks of KAIRN_CHECKS -------------------------------------------
#
# api.flags.debug.self_test: kairn::self_test() and kairn::environment_ok() compiled as the debug
# build of flags/ (runner.cpp --self-test), which must pass; api.flags.debug.constexpr:
# constexpr.cpp built so, with the checks. The full tier registers the same for the other flag
# sets (../full/).
#
# The checks of KAIRN_CHECKS (checks.cpp, run by checks.cmake), in the debug build
# (api.checks.debug.*) and with the build's own flags and KAIRN_CHECKS defined to 1
# (api.checks.release.*): .default, in the default environment every operation runs and so does
# every operand the checks must accept; .rounding, under each directed rounding mode
# environment_ok() is false and every operation stops the program with Kairn's message; .flush, the
# same under flush to zero (FTZ and DAZ on x86-64, FZ on AArch64); .operands, every operand that is
# not canonical, and every negative radius, stops the program with its message.
# api.checks.handler: a KAIRN_ENVIRONMENT_FAILURE of the program's own is called instead
# (checks_handler.cpp).
add_test(NAME api.flags.debug.self_test COMMAND kairn-api-runner-debug --self-test)
add_test(NAME api.flags.debug.constexpr COMMAND kairn-api-constexpr-debug)
# rational.cpp in the debug build: KAIRN_CHECKS is 1, and kairn::rational, which does not round,
# must run under each directed rounding mode without stopping the program.
add_test(NAME api.flags.debug.rational COMMAND kairn-api-rational-debug)
set_tests_properties(api.flags.debug.self_test api.flags.debug.constexpr api.flags.debug.rational PROPERTIES
  TIMEOUT 120 LABELS "api;flags")
_kairn_api_program(kairn-api-checks-release checks.cpp)
target_compile_definitions(kairn-api-checks-release PRIVATE KAIRN_CHECKS=1)
set(_api_expect_flush OFF)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64|aarch64|arm64|ARM64)$")
  set(_api_expect_flush ON)
endif()
foreach(_build debug release)
  foreach(_group default rounding flush operands)
    add_test(NAME api.checks.${_build}.${_group}
      COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-api-checks-${_build}>" "-DGROUP=${_group}"
        "-DEXPECT_FLUSH=${_api_expect_flush}" -P "${CMAKE_CURRENT_SOURCE_DIR}/checks.cmake")
    set_tests_properties(api.checks.${_build}.${_group} PROPERTIES TIMEOUT 300 LABELS "api;checks")
  endforeach()
endforeach()
add_test(NAME api.checks.handler COMMAND kairn-api-checks-handler)
set_tests_properties(api.checks.handler PROPERTIES TIMEOUT 120 LABELS "api;checks")
# The same programs, with the build's own flags and KAIRN_CHECKS 1, in the other settings of
# KAIRN_ENCLOSURE_CODE (include/kairn/config.hpp), where the checks of the operations of Ball are in
# functions of their own: outlined, and external, whose definitions are those of definitions.cpp
# (checks_handler.cpp has them itself, with its handler). The full tier runs them
# (full.api.checks.SETTING.*, ../full/CMakeLists.txt).
foreach(_code OUTLINED EXTERNAL)
  string(TOLOWER "${_code}" _name)
  _kairn_api_program(kairn-api-checks-${_name} checks.cpp)
  _kairn_api_program(kairn-api-checks-handler-${_name} checks_handler.cpp)
  target_compile_definitions(kairn-api-checks-${_name} PRIVATE KAIRN_CHECKS=1 KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_code})
  target_compile_definitions(kairn-api-checks-handler-${_name} PRIVATE KAIRN_CHECKS=1
    KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_${_code})
  if(_code STREQUAL "EXTERNAL")
    target_sources(kairn-api-checks-${_name} PRIVATE definitions.cpp)
  endif()
endforeach()
set(_api_expect_flush ${_api_expect_flush} PARENT_SCOPE)
# --- The end of the debug build and the checks -------------------------------------------------

# --- What must not compile --------------------------------------------------------------------
# The compilations below run the compiler directly, with the build's own flags and kairn::fma's.
get_target_property(_api_fma kairn::fma INTERFACE_COMPILE_OPTIONS)
if(NOT _api_fma)
  set(_api_fma "")
endif()
separate_arguments(_api_cxx_flags NATIVE_COMMAND "${CMAKE_CXX_FLAGS}")
list(PREPEND _api_fma ${_api_cxx_flags})
if(_msvc_style)
  set(_api_style msvc)
else()
  set(_api_style gnu)
endif()
list(JOIN _api_fma "|" _api_fma_bars)
set(_api_reject_common "-DCXX=${CMAKE_CXX_COMPILER}" "-DSTYLE=${_api_style}" "-DINCLUDE=${_api_include}"
  "-DSOURCE=${CMAKE_CURRENT_SOURCE_DIR}/reject.cpp" "-DCOMMON=${_api_fma_bars}")
if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
  list(APPEND _api_reject_common "-DSYSROOT=${CMAKE_OSX_SYSROOT}")
endif()

function(_kairn_api_reject name case expect)
  add_test(NAME api.reject.${name}
    COMMAND "${CMAKE_COMMAND}" ${_api_reject_common} "-DCASE=${case}" "-DEXPECT=${expect}" ${ARGN}
      -P "${CMAKE_CURRENT_SOURCE_DIR}/compile_fail.cmake")
  set_tests_properties(api.reject.${name} PROPERTIES LABELS "api;reject")
endfunction()

# Compiler flags (docs/developer/design/phase0/environment.md, "Compiler flags").
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  _kairn_api_reject(fp_fast 0 "Kairn does not work with /fp:fast" "-DOPTIONS=/fp:fast")
elseif(NOT _msvc_style)
  _kairn_api_reject(fast_math 0 "Kairn does not work with -ffast-math" "-DOPTIONS=-ffast-math")
  _kairn_api_reject(finite_math_only 0 "Kairn does not work with -ffinite-math-only" "-DOPTIONS=-ffinite-math-only")
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    _kairn_api_reject(associative_math 0 "Kairn does not work with -fassociative-math"
      "-DOPTIONS=-fassociative-math|-fno-signed-zeros|-fno-trapping-math")
    _kairn_api_reject(unsafe_math 0 "Kairn does not work with -fassociative-math"
      "-DOPTIONS=-funsafe-math-optimizations")
    _kairn_api_reject(no_signed_zeros 0 "Kairn does not work with -fno-signed-zeros" "-DOPTIONS=-fno-signed-zeros")
    _kairn_api_reject(reciprocal_math 0 "Kairn does not work with -freciprocal-math" "-DOPTIONS=-freciprocal-math")
  endif()
endif()

# A value of KAIRN_ENCLOSURE_CODE that is not one of its three (include/kairn/config.hpp): a name the
# preprocessor does not know, nothing, and the 1 of a bare -D; the control, without it, compiles.
if(_msvc_style)
  set(_api_define /D)
else()
  set(_api_define -D)
endif()
_kairn_api_reject(enclosure_code.unknown 0 "KAIRN_ENCLOSURE_CODE must be KAIRN_ENCLOSURE_CODE_INLINE"
  "-DOPTIONS=${_api_define}KAIRN_ENCLOSURE_CODE=outlined")
_kairn_api_reject(enclosure_code.empty 0 "KAIRN_ENCLOSURE_CODE must be KAIRN_ENCLOSURE_CODE_INLINE"
  "-DOPTIONS=${_api_define}KAIRN_ENCLOSURE_CODE=")
_kairn_api_reject(enclosure_code.bare 0 "KAIRN_ENCLOSURE_CODE must be KAIRN_ENCLOSURE_CODE_INLINE"
  "-DOPTIONS=${_api_define}KAIRN_ENCLOSURE_CODE")

# What must not link (link_fail.cmake): with KAIRN_ENCLOSURE_CODE_EXTERNAL, link_main.cpp with the
# definitions (definitions.cpp) compiled with another KAIRN_CHECKS, with another setting, and
# without them; each with a control, both units with the same options, which links and runs.
set(_api_external "${_api_define}KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_EXTERNAL")
set(_api_link_common "-DCXX=${CMAKE_CXX_COMPILER}" "-DSTYLE=${_api_style}" "-DINCLUDE=${_api_include}"
  "-DSOURCE_DIR=${CMAKE_CURRENT_SOURCE_DIR}" "-DCOMMON=${_api_fma_bars}")
if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
  list(APPEND _api_link_common "-DSYSROOT=${CMAKE_OSX_SYSROOT}")
endif()
foreach(_case checks setting missing)
  if(_case STREQUAL "checks")
    set(_main "${_api_external}|${_api_define}KAIRN_CHECKS=1")
    set(_definitions "${_api_external}|${_api_define}KAIRN_CHECKS=0")
    set(_expect "kairn::detail::external_checked::")
  elseif(_case STREQUAL "setting")
    set(_main "${_api_external}|${_api_define}KAIRN_CHECKS=0")
    set(_definitions "${_api_define}KAIRN_ENCLOSURE_CODE=KAIRN_ENCLOSURE_CODE_OUTLINED|${_api_define}KAIRN_CHECKS=0")
    set(_expect "kairn::detail::external::|kairn_enclosure_code")
  else()
    set(_main "${_api_external}|${_api_define}KAIRN_CHECKS=0")
    set(_definitions NONE)
    set(_expect "kairn::detail::external::")
  endif()
  add_test(NAME api.link.external.${_case}
    COMMAND "${CMAKE_COMMAND}" ${_api_link_common} "-DWORK=${CMAKE_CURRENT_BINARY_DIR}/link/${_case}"
      "-DMAIN=${_main}" "-DDEFINITIONS=${_definitions}" "-DEXPECT=${_expect}"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/link_fail.cmake")
  set_tests_properties(api.link.external.${_case} PROPERTIES TIMEOUT 300 LABELS "api;reject")
endforeach()

# UNVERIFIED operations written without the marker, compiled against a copy of the headers in which
# every kernel is marked unverified (compile_fail.cmake), so that the mechanism is tested whatever
# gen/claims.json says today. Where the compiler explains, the message names the concept whose
# constraint failed; Clang does not for a unary operator.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_unmarked "constraint")
else()
  set(_api_unmarked "proof_checked|invalid argument type")
endif()
foreach(_case_name IN ITEMS 1:sub_2_2_full 2:lt_2_2 3:neg_2 4:to_down_2 5:add_1_1 6:ball_add_2_full
                            7:sub_2_2_full_assign 8:mul_pow2_2_full 9:ball_scale_2_full 10:traits_constant
                            12:to_nearest_2_narrowing 13:make_2 14:ball_make_2 29:two_sum_entry 30:next_up
                            31:ball_mul_pow2_2_full 39:interval_add_1 40:interval_make_1 41:interval_to_ball_1)
  string(REPLACE ":" ";" _pair "${_case_name}")
  list(GET _pair 0 _case)
  list(GET _pair 1 _name)
  set(_expect "${_api_unmarked}")
  if(_name STREQUAL "traits_constant")
    set(_expect "unit")
  endif()
  _kairn_api_reject(unverified.${_name} ${_case} "${_expect}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/${_name}")
endforeach()
# One kernel unverified, the others proved: the operation must not compile through a conversion to
# another, proved kernel (x + a as x + Expansion(a), a scaling as a product with a point ball).
foreach(_case_name IN ITEMS 20:add_2_1_full:limb 21:add_2_1_full:one_limb 22:sub_1_2_full:limb
                            23:mul_2_1_full:limb 24:ball_scale_2_full:limb 25:ball_make_2:point
                            26:lt_2_1:limb)
  string(REPLACE ":" ";" _triple "${_case_name}")
  list(GET _triple 0 _case)
  list(GET _triple 1 _kernel)
  list(GET _triple 2 _what)
  _kairn_api_reject(unverified_only.${_kernel}.${_what} ${_case} "${_api_unmarked}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/only-${_kernel}-${_what}"
    "-DUNVERIFIED_ONLY=${_kernel}")
endforeach()
# mul_down and mul_up are not constexpr (include/kairn/blocks.hpp says why): a constant expression
# that calls one must not compile, so that a change cannot make them constexpr by accident; the
# control is the same call at run time.
_kairn_api_reject(not_constexpr.mul_down 27 "constant|constexpr")
_kairn_api_reject(not_constexpr.mul_up 28 "constant|constexpr")
# Intervals (interval.hpp): no operation mixes numbers of limbs, or an interval with a number; the
# conversions between Ball and Interval, and the narrowing of a ball, are explicit; no conversion
# makes an interval of two limbs of one of one limb; the sum is not constexpr (its code is where
# KAIRN_ENCLOSURE_CODE puts it). Each control writes what compiles instead.
# MSVC says C2676, "does not define this operator or a conversion to a type acceptable to the
# predefined operator", when the left operand is a class with no such operator at all.
set(_api_no_operator "invalid operands|no match for|no operator found|does not define this operator")
set(_api_no_conversion "no viable conversion|conversion from|cannot convert|no suitable")
set(_api_no_constructor "no matching|cannot convert|no overloaded function|no suitable")
_kairn_api_reject(interval.mixed_limbs 32 "${_api_no_operator}")
_kairn_api_reject(interval.number_operand 33 "${_api_no_operator}")
_kairn_api_reject(interval.implicit_from_ball 34 "${_api_no_conversion}")
_kairn_api_reject(interval.implicit_to_ball 35 "${_api_no_conversion}")
_kairn_api_reject(ball.implicit_narrowing 36 "${_api_no_conversion}")
_kairn_api_reject(interval.from_one_limb 37 "${_api_no_constructor}")
_kairn_api_reject(not_constexpr.interval_add 38 "constant|constexpr")
# The containers (soa.hpp): nothing writes through a view of const limbs or a const SoA, and no
# view of mutable limbs is made of one. Packed (packed.hpp): no packed operation takes a number or
# a T (no packed kernel does: a program broadcasts it), the narrowing to one limb is explicit, no
# operation mixes limb types, and Packed<T, 1> has no arithmetic. Each control writes what compiles instead.
set(_api_no_assignment "no viable overloaded|no match for|binary '='|no operator found|constraints")
set(_api_no_member "constraints not satisfied|no matching|no overloaded function|associated constraints|satisfied its constraints")
_kairn_api_reject(soa.assign_const_element 42 "${_api_no_assignment}")
_kairn_api_reject(soa.set_const 43 "${_api_no_member}")
_kairn_api_reject(soa.store_const 44 "${_api_no_member}")
_kairn_api_reject(soa.mutable_from_const_view 45 "${_api_no_conversion}")
_kairn_api_reject(soa.mutable_from_const_soa 46 "${_api_no_conversion}")
_kairn_api_reject(soa.assign_const_from_const 47 "${_api_no_assignment}")
_kairn_api_reject(packed.number_operand 48 "${_api_no_operator}")
_kairn_api_reject(packed.limb_operand 49 "${_api_no_operator}")
_kairn_api_reject(packed.implicit_narrowing 50 "${_api_no_conversion}")
_kairn_api_reject(packed.mixed_limb_types 51 "${_api_no_operator}")
_kairn_api_reject(packed.one_limb_arithmetic 53 "${_api_no_operator}")
# The functions on arrays (batch.hpp): nothing writes through a view of const limbs, every view of
# one call has one limb type and one number of limbs, and nothing scales by a two-limb number (no
# loop does). Each control writes what compiles instead.
set(_api_no_function "no matching|no overloaded function|constraints|could not deduce|conflicting|cannot convert")
_kairn_api_reject(batch.map_into_const 54 "${_api_no_function}")
_kairn_api_reject(batch.axpy_into_const 55 "${_api_no_function}")
_kairn_api_reject(batch.mixed_limb_types 56 "${_api_no_function}")
_kairn_api_reject(batch.mixed_limbs 57 "${_api_no_function}")
_kairn_api_reject(batch.scale_by_two_limbs 58 "${_api_no_function}")
# A bound as a function of the length that the kernel does not give, in a constant expression: a
# compile error (traits.hpp); the control computes it at run time, where it is +infinity.
_kairn_api_reject(traits.length_beyond 59 "constant|constexpr")
# The accumulator (accumulator.hpp): no merge of accumulators of two limb types; add_product and
# error_bound are not constexpr (their kernels have fused multiply-adds); each control writes what
# compiles instead.
_kairn_api_reject(accumulator.mixed_limb_types 60 "${_api_no_conversion}|${_api_no_function}")
_kairn_api_reject(not_constexpr.add_product 61 "constant|constexpr")
_kairn_api_reject(not_constexpr.error_bound 62 "constant|constexpr")
# BallVector (ball_vector.hpp): nothing writes a const BallVector or a view of const limbs, no
# operation mixes lengths fixed by the types, limb types, or a ball vector with a Ball, no view of
# mutable limbs is made of one of const limbs nor over arrays of const limbs, a view becomes a
# BallVector only explicitly, a BallVector has at least one entry, and no operation is constexpr.
# Each control writes what compiles instead.
_kairn_api_reject(ball_vector.write_const 97 "${_api_no_member}")
_kairn_api_reject(ball_vector.write_const_view 98 "${_api_no_member}")
_kairn_api_reject(ball_vector.lengths 99 "${_api_no_operator}")
_kairn_api_reject(ball_vector.limb_types 100 "${_api_no_operator}")
_kairn_api_reject(ball_vector.mutable_from_const_view 101 "${_api_no_conversion}")
_kairn_api_reject(ball_vector.implicit_from_view 102 "${_api_no_conversion}")
_kairn_api_reject(ball_vector.no_entry 103 "N is at least 1")
_kairn_api_reject(ball_vector.with_ball 104 "${_api_no_operator}")
_kairn_api_reject(ball_vector.not_constexpr 105 "constant|constexpr")
_kairn_api_reject(ball_vector.view_of_const_limbs 106 "${_api_no_constructor}")
_kairn_api_reject(ball_vector.part_of_mutable_view 107 "${_api_no_member}")
# KAIRN_PACKED_FORM (packed.hpp): a value that is not a form, a bare -D, and the form of another
# target, which the generated header refuses.
_kairn_api_reject(packed_form.unknown 52 "KAIRN_PACKED_FORM must be KAIRN_PACKED_FORM_SCALAR"
  "-DOPTIONS=${_api_define}KAIRN_PACKED_FORM=avx2")
_kairn_api_reject(packed_form.bare 52 "KAIRN_PACKED_FORM must be KAIRN_PACKED_FORM_SCALAR"
  "-DOPTIONS=${_api_define}KAIRN_PACKED_FORM")
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm64|aarch64|ARM64)$")
  _kairn_api_reject(packed_form.other_target 52 "needs AVX2 and FMA"
    "-DOPTIONS=${_api_define}KAIRN_PACKED_FORM=KAIRN_PACKED_FORM_AVX2")
else()
  _kairn_api_reject(packed_form.other_target 52 "needs AArch64"
    "-DOPTIONS=${_api_define}KAIRN_PACKED_FORM=KAIRN_PACKED_FORM_NEON")
endif()
# The enclosure interface of stage B2 (headers-pred; reject.cpp, cases 70 to 92): a three-valued
# answer converts to no bool, intervals and balls have no comparison operators, no function takes
# two kinds of set or two numbers of limbs, the conversions between the two types of two limbs are
# explicit, and a point is never made a set to reach another kernel. A Trit in a condition: Clang
# says it is not contextually convertible, GCC that it could not convert, MSVC that the conditional
# expression is not valid (C2451); a call that matches no function: "no matching", or MSVC's C2672,
# C2664 ("cannot convert argument") or C2665 ("none of the overloads could convert").
set(_api_no_bool "contextually convertible|could not convert|cannot convert|not valid|cannot initialize")
set(_api_no_call "no matching|no overloaded function|cannot convert|could convert|satisfied its constraints")
_kairn_api_reject(enclosure.trit_condition 70 "${_api_no_bool}")
_kairn_api_reject(enclosure.trit_bool 71 "${_api_no_bool}")
_kairn_api_reject(enclosure.interval_operator 72 "${_api_no_operator}")
_kairn_api_reject(enclosure.ball_operator 73 "${_api_no_operator}")
_kairn_api_reject(enclosure.mixed_limbs 74 "${_api_no_call}")
_kairn_api_reject(enclosure.mixed_types 75 "${_api_no_call}")
_kairn_api_reject(enclosure.interval_contains_ball 76 "${_api_no_call}")
_kairn_api_reject(enclosure.ball_relation 77 "${_api_no_call}")
_kairn_api_reject(enclosure.implicit_to_ball 78 "${_api_no_conversion}")
_kairn_api_reject(enclosure.implicit_to_interval 79 "${_api_no_conversion}")
_kairn_api_reject(enclosure.hull_mixed_limbs 80 "${_api_no_call}")
_kairn_api_reject(enclosure.contains_mixed_limbs 81 "${_api_no_call}")
foreach(_case_name IN ITEMS 82:interval_less_1 83:interval_subset_1 84:ball_hull_2 85:interval_rel_disjoint_1
                            86:ball_from_interval_1 87:ball_contains_point_1 88:interval_to_ball_2)
  string(REPLACE ":" ";" _pair "${_case_name}")
  list(GET _pair 0 _case)
  list(GET _pair 1 _name)
  _kairn_api_reject(unverified.${_name} ${_case} "${_api_unmarked}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/${_name}")
endforeach()
foreach(_case_name IN ITEMS 89:interval_contains_1:point 90:interval_contains_2:limb 91:ball_contains_point_1:point
                            92:ball_contains_point_2:limb)
  string(REPLACE ":" ";" _triple "${_case_name}")
  list(GET _triple 0 _case)
  list(GET _triple 1 _kernel)
  list(GET _triple 2 _what)
  _kairn_api_reject(unverified_only.${_kernel}.${_what} ${_case} "${_api_unmarked}"
    "-DUNVERIFIED_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/unverified-fixture/only-${_kernel}-${_what}"
    "-DUNVERIFIED_ONLY=${_kernel}")
endforeach()
# --- The end of the enclosure interface's cases ----------------------------------------------------
_kairn_api_reject(checks.from_limbs_not_canonical 11 "constant|constexpr")
_kairn_api_reject(checks.operator_not_canonical 15 "constant|constexpr")
_kairn_api_reject(checks.ball_negative_radius 16 "constant|constexpr")
# kairn::rational in a constant expression: a zero denominator, whose message names the function
# that says so (MSVC's message was not seen yet: there, any failed constant expression); and a
# result that fails its check, against a copy of the headers in which the flag exact is inverted
# (compile_fail.cmake), which must not compile, while the control, the same copy with
# KAIRN_RATIONAL_CHECK 0, compiles: that wrong constant goes unnoticed at compile time without the
# check.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_zero "rational_denominator_is_zero|expression did not evaluate to a constant")
  set(_api_fails "rational_result_fails_its_specification|expression did not evaluate to a constant")
else()
  set(_api_zero "rational_denominator_is_zero")
  set(_api_fails "rational_result_fails_its_specification")
endif()
_kairn_api_reject(rational.denominator_zero 17 "${_api_zero}")
_kairn_api_reject(rational.result_fails_its_check 18 "${_api_fails}"
  "-DRATIONAL_FAULT_FIXTURE=${CMAKE_CURRENT_BINARY_DIR}/rational-fault-fixture")
# kairn::two_prod in a constant expression on finite operands where an operation of Dekker's product,
# which constant evaluation runs, overflows (blocks.hpp): a partial product while the product is
# finite, and the product itself; each control is the neighboring operand where it compiles. Clang,
# which computes an overflow to infinity, reaches the check, whose message names the function that
# refuses; GCC refuses the overflowing product itself ("... is not a constant expression"); MSVC's
# message was not seen (there, any failed constant expression).
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  set(_api_overflow "two_prod_overflows_in_constant_evaluation|expression did not evaluate to a constant")
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  set(_api_overflow "two_prod_overflows_in_constant_evaluation|is not a constant expression")
else()
  set(_api_overflow "two_prod_overflows_in_constant_evaluation")
endif()
foreach(_case_name IN ITEMS 93:partial_product.double 94:partial_product.float 95:product.double
                            96:product.float)
  string(REPLACE ":" ";" _pair "${_case_name}")
  list(GET _pair 0 _case)
  list(GET _pair 1 _name)
  _kairn_api_reject(two_prod.overflows_in_constant_evaluation.${_name} ${_case} "${_api_overflow}")
endforeach()

# --- The program's names ------------------------------------------------------------------------
#
# api.shadow: a program whose global variables have the names of every parameter and local
# variable of the headers, compiled with the strictest warnings of the compiler about a
# declaration that hides another, as errors, and with the build's own flags (shadow.py, on
# shadow.cpp, every public operation once). MSVC reports such declarations of the headers (C4459,
# and C6244 under /analyze), and GCC 11 and 13 some of them (-Wshadow), which the headers turn off
# for their own; Clang reports none. With the headers' suppression lifted, the program must be
# rejected by MSVC, and the headers alone, without the globals, must compile with every warning on.
if(Python3_Interpreter_FOUND)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    set(_api_shadow_compiler msvc)
  elseif(_msvc_style)
    set(_api_shadow_compiler clang-cl)
  elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(_api_shadow_compiler gcc)
  else()
    set(_api_shadow_compiler clang)
  endif()
  set(_api_shadow_sysroot "")
  if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
    set(_api_shadow_sysroot "--sysroot=${CMAKE_OSX_SYSROOT}")
  endif()
  add_test(NAME api.shadow
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/shadow.py" "--cxx=${CMAKE_CXX_COMPILER}"
      "--compiler=${_api_shadow_compiler}" "--include=${_api_include}"
      "--source=${CMAKE_CURRENT_SOURCE_DIR}/shadow.cpp" "--workdir=${CMAKE_CURRENT_BINARY_DIR}/shadow"
      "--options=${_api_fma_bars}" ${_api_shadow_sysroot})
  set_tests_properties(api.shadow PROPERTIES TIMEOUT 600 LABELS "api;shadow")
endif()

# --- One limb against T -----------------------------------------------------------------------
if(Python3_Interpreter_FOUND)
  set(_api_k1 "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/k1/zero_cost.py" --cxx "${CMAKE_CXX_COMPILER}"
    --include "${_api_include}" --workdir "${CMAKE_CURRENT_BINARY_DIR}/k1")
  set(_api_k1_flags "${_api_fma}")
  if(CMAKE_OSX_SYSROOT AND NOT _msvc_style)
    list(APPEND _api_k1_flags -isysroot "${CMAKE_OSX_SYSROOT}")
  endif()
  list(JOIN _api_k1_flags " " _api_k1_flags)
  if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    list(APPEND _api_k1 --msvc)
  endif()
  if(NOT _msvc_style OR CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    add_test(NAME api.k1.zero_cost COMMAND ${_api_k1} "--flags=${_api_k1_flags}")
    set_tests_properties(api.k1.zero_cost PROPERTIES LABELS api)
  endif()
endif()

# --- The documentation's examples -------------------------------------------------------------
_kairn_api_program(kairn-example-first-steps "${PROJECT_SOURCE_DIR}/docs/examples/cpp/first_steps.cpp")
add_test(NAME api.example.first_steps COMMAND kairn-example-first-steps)
# The examples of "Choosing T and k" and "Troubleshooting" in Getting started; the second changes
# the rounding mode and flush-to-zero, and checks the messages the page quotes.
_kairn_api_program(kairn-example-choosing "${PROJECT_SOURCE_DIR}/docs/examples/cpp/choosing.cpp")
add_test(NAME api.example.choosing COMMAND kairn-example-choosing)
_kairn_api_program(kairn-example-troubleshooting "${PROJECT_SOURCE_DIR}/docs/examples/cpp/troubleshooting.cpp")
add_test(NAME api.example.troubleshooting COMMAND kairn-example-troubleshooting)
# The example of "Constants from fractions" in Getting started.
_kairn_api_program(kairn-example-constants "${PROJECT_SOURCE_DIR}/docs/examples/cpp/constants.cpp")
add_test(NAME api.example.constants COMMAND kairn-example-constants)
# The example of "Building blocks" in Getting started: the functions of blocks.hpp, the exact
# scaling of a ball, the ball of a constant and the sign predicates.
_kairn_api_program(kairn-example-building-blocks "${PROJECT_SOURCE_DIR}/docs/examples/cpp/building_blocks.cpp")
add_test(NAME api.example.building_blocks COMMAND kairn-example-building-blocks)
set_tests_properties(api.example.first_steps api.example.choosing api.example.troubleshooting api.example.constants
  api.example.building_blocks PROPERTIES LABELS "api;example")

# The tutorial's program prints the same text on every platform and under every contraction
# setting (its data are chosen so that even its double loops give one answer), and the tutorial
# shows that text: it is built with the build's flags and once per contraction setting, as
# api.boundary.* is, and each build's output is compared with accurate_sums.txt.
list(LENGTH _api_contraction _n)
math(EXPR _last "${_n} - 1")
foreach(_i RANGE 0 ${_last} 2)
  math(EXPR _j "${_i} + 1")
  list(GET _api_contraction ${_i} _variant)
  list(GET _api_contraction ${_j} _option)
  if(_variant STREQUAL "")
    set(_suffix "")
  else()
    set(_suffix ".${_variant}")
  endif()
  string(REPLACE "." "-" _target_suffix "${_suffix}")
  _kairn_api_program(kairn-example-accurate-sums${_target_suffix}
    "${PROJECT_SOURCE_DIR}/docs/examples/cpp/accurate_sums.cpp" ${_option})
  add_test(NAME api.example.accurate_sums${_suffix}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-accurate-sums${_target_suffix}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/accurate_sums.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.accurate_sums${_suffix} PROPERTIES LABELS "api;example")
  # The tutorial on intervals (docs/tutorials/intervals.md), the same way.
  _kairn_api_program(kairn-example-intervals${_target_suffix} "${PROJECT_SOURCE_DIR}/docs/examples/cpp/intervals.cpp"
    ${_option})
  add_test(NAME api.example.intervals${_suffix}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-intervals${_target_suffix}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/intervals.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.intervals${_suffix} PROPERTIES LABELS "api;example")
  # The tutorial on bisection (docs/tutorials/bisection.md), the same way: one algorithm for an
  # interval and two balls, whose output is the same text everywhere (headers-pred).
  _kairn_api_program(kairn-example-bisection${_target_suffix} "${PROJECT_SOURCE_DIR}/docs/examples/cpp/bisection.cpp"
    ${_option})
  add_test(NAME api.example.bisection${_suffix}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-bisection${_target_suffix}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/bisection.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.bisection${_suffix} PROPERTIES LABELS "api;example")
  # The tutorial on ball vectors (docs/tutorials/ball-vectors.md), the same way: its program checks
  # every result against exact arithmetic, and prints the same text in every form of Packed (the two
  # orders give the same bits).
  _kairn_api_program(kairn-example-ball-vectors${_target_suffix}
    "${PROJECT_SOURCE_DIR}/docs/examples/cpp/ball_vectors.cpp" ${_option})
  add_test(NAME api.example.ball_vectors${_suffix}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-ball-vectors${_target_suffix}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/ball_vectors.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.ball_vectors${_suffix} PROPERTIES LABELS "api;example;ball_vector")
endforeach()
# The tutorial on a vector loop (docs/tutorials/vector-loop.md), in every form of Packed (above):
# the same text in each, which the program checks against an exact reference and the bound it
# states, and which the tutorial shows.
foreach(_form IN LISTS _api_packed_forms)
  set(_options "")
  if(_form STREQUAL "scalar")
    set(_options ${_api_scalar_form})
  elseif(_form STREQUAL "avx2")
    set(_options ${_isa_option})
  endif()
  _kairn_api_program(kairn-example-packed-dot-${_form} "${PROJECT_SOURCE_DIR}/docs/examples/cpp/packed_dot.cpp"
    ${_options})
  add_test(NAME api.example.packed_dot.${_form}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-packed-dot-${_form}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/packed_dot.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.packed_dot.${_form} PROPERTIES LABELS "api;example;packed")
  # The tutorial on sums and dot products of arrays (docs/tutorials/arrays.md): the results of the
  # sequential order, the same in every form, which the program checks against an exact reference
  # and the bounds of kairn::traits, as the results of the lane order of the form, which it prints
  # to the standard error only.
  _kairn_api_program(kairn-example-arrays-${_form} "${PROJECT_SOURCE_DIR}/docs/examples/cpp/arrays.cpp" ${_options})
  add_test(NAME api.example.arrays.${_form}
    COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-example-arrays-${_form}>"
      "-DEXPECTED=${PROJECT_SOURCE_DIR}/docs/examples/cpp/arrays.txt"
      -P "${CMAKE_CURRENT_SOURCE_DIR}/example_output.cmake")
  set_tests_properties(api.example.arrays.${_form} PROPERTIES LABELS "api;example;arrays")
endforeach()
set_tests_properties(api.constexpr api.environment PROPERTIES LABELS api)

# Every test here is in the quick tier (../CMakeLists.txt, "The two tiers").
get_property(_api_tests DIRECTORY PROPERTY TESTS)
set_property(TEST ${_api_tests} APPEND PROPERTY LABELS quick)
