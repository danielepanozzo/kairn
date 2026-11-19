# Kairn's tests, registered with ctest when KAIRN_BUILD_TESTS is on; together they are the quick
# tier (docs/developer/testing.md):
#
#   ctest --test-dir build --output-on-failure        (add -C CONFIG for a multi-config generator)
#
# - The entry points of docs/developer/architecture.md that run tests, each registered only if its
#   script exists when CMake runs (configure again after one is added). They need Python 3; without
#   it they are left out, as are the cross-checks, and nothing else changes.
# - The cross-checks: the oracle judges every kernel of gen/claims.json as run by the generator's
#   interpreter on every operand of a toy format (or, where that is too many, on every operand of
#   a restricted domain and on random cases of the whole format), and as compiled with this
#   build's compiler and flags, on random binary64 and binary32 cases, once as the flags stand and
#   once per contraction setting that matters to this compiler: the scalar kernels
#   (gen/tests/runner.cpp), and the packed kernels of the target's backend, NEON or AVX2
#   (gen/tests/packed_runner.cpp).
# - The consumer checks (consume/): a project that uses kairn::kairn and kairn::fma through
#   add_subdirectory, and one that uses them through find_package after this build tree is
#   installed into a prefix under the build directory.

find_package(Python3 COMPONENTS Interpreter)
include(CheckCXXSourceCompiles)
include(CMakePushCheckState)

# MSVC and clang-cl take MSVC-style options; everything else here takes GCC-style ones.
if(CMAKE_CXX_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC" OR
   (MSVC AND NOT CMAKE_CXX_COMPILER_FRONTEND_VARIANT))
  set(_msvc_style ON)
else()
  set(_msvc_style OFF)
endif()

# --- The entry points ---------------------------------------------------------------------------
#
# Each is "SCRIPT COMMAND" from the repository root, run as python3 SCRIPT COMMAND ARGS:
# - gen/kairn-gen test runs here without its C++ tests (--no-cxx), which build the generated code
#   at -O0 and -O2, with and without -frounding-math, under every contraction setting, and
#   compare it bit for bit with the interpreter: about two thirds of the suite's time, and what
#   the cross-checks below cover for this build's compiler and flags. The whole suite runs in the
#   workflow .github/workflows/generator.yml, and by hand: python3 gen/kairn-gen test.
# - oracle/kairn-oracle selftest compiles its own C++ runner with this build's compiler, in the
#   build tree. It skips the tests that need it, with a SKIP line, if the compiler does not work;
#   with a compiler given that is a failure here. (Its other skip, of rounding_hardware on Python
#   older than 3.13, which has no math.fma, is not.)
# - oracle/kairn-oracle check --claims-only reads every claim of gen/claims.json.
set(_entries "gen/kairn-gen check" "gen/kairn-gen test" "oracle/kairn-oracle selftest"
  "oracle/kairn-oracle claims")
set(_present "")
set(_absent "")
foreach(_entry IN LISTS _entries)
  separate_arguments(_words UNIX_COMMAND "${_entry}")
  list(GET _words 0 _script)
  list(GET _words 1 _command)
  if(NOT EXISTS "${PROJECT_SOURCE_DIR}/${_script}")
    list(APPEND _absent "${_entry}")
    continue()
  endif()
  list(APPEND _present "${_entry}")
  if(NOT Python3_Interpreter_FOUND)
    continue()
  endif()
  get_filename_component(_name "${_script}" NAME)
  set(_args "${_command}")
  if(_entry STREQUAL "gen/kairn-gen test")
    list(APPEND _args --no-cxx)
  elseif(_entry STREQUAL "oracle/kairn-oracle selftest")
    list(APPEND _args --quick --cxx "${CMAKE_CXX_COMPILER}"
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/oracle-selftest")
  elseif(_entry STREQUAL "oracle/kairn-oracle claims")
    set(_args check --claims gen/claims.json --claims-only)
  endif()
  add_test(NAME "${_name}.${_command}"
    COMMAND "${Python3_EXECUTABLE}" "${_script}" ${_args}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  if(_entry STREQUAL "gen/kairn-gen test")
    set_tests_properties("${_name}.${_command}" PROPERTIES TIMEOUT 600)
  elseif(_entry STREQUAL "oracle/kairn-oracle selftest")
    set_tests_properties("${_name}.${_command}" PROPERTIES TIMEOUT 600
      FAIL_REGULAR_EXPRESSION "SKIP [^\n]*(no C\\+\\+ compiler|compiling the C\\+\\+ runner)")
  endif()
endforeach()
list(JOIN _present ", " _present)
list(JOIN _absent ", " _absent)
if(NOT _present)
  set(_present "none")
endif()
if(Python3_Interpreter_FOUND)
  set(_line "Kairn tests: registered: ${_present}")
else()
  set(_line "Kairn tests: Python 3 not found, so not registered: ${_present}, nor the cross-checks")
endif()
if(_absent)
  string(APPEND _line "; not present yet: ${_absent}")
endif()
message(STATUS "${_line}")

# --- The compiled runners -----------------------------------------------------------------------
#
# gen/tests/runner.cpp runs the generated scalar kernels on the line protocol, and
# gen/tests/packed_runner.cpp the packed ones, consecutive requests one per lane. Each is built
# with this build's compiler and flags (kairn-gen-runner, kairn-gen-packed-runner), and once more
# for each contraction setting that matters to the compiler, appended to those flags: the
# regression test of the contraction experiment of docs/developer/design/phase0/environment.md.
# A compiler only contracts when it optimizes, which is why a top-level build defaults to Release.
if(_msvc_style)
  set(_warnings /W4)
else()
  set(_warnings -Wall -Wextra -Wpedantic)
endif()
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  # /fp:precise does not contract (since Visual Studio 2022), /fp:contract does, and /fp:strict
  # does not either; it is where std::fma becomes a library call, which is why the kernels use
  # the FMA intrinsic on MSVC.
  set(_settings fp-precise /fp:precise fp-contract /fp:contract fp-strict /fp:strict)
elseif(_msvc_style)
  # clang-cl: /fp:strict is -ffp-contract=off, /fp:precise and /fp:contract are =on, and =fast,
  # the setting that broke the textbook product in Phase 0, has no /fp: spelling but /fp:fast,
  # which also assumes there are no NaNs.
  set(_settings fp-strict /fp:strict fp-precise /fp:precise fp-contract /fp:contract
    contract-fast /clang:-ffp-contract=fast)
else()
  set(_settings contract-off -ffp-contract=off contract-on -ffp-contract=on
    contract-fast -ffp-contract=fast)
endif()
set(_variants "" "")    # name, option: the runner with the build's flags first
list(APPEND _variants ${_settings})
list(LENGTH _variants _n)
math(EXPR _variants_last "${_n} - 1")

# The packed backend: NEON where the target has it (AArch64), otherwise AVX2 with FMA, and its
# option chosen as kairn::fma's is (cmake/kairn_fma.cmake): nothing if CMAKE_CXX_FLAGS already
# enable it, otherwise /arch:AVX2 (MSVC, clang-cl) or -mavx2 -mfma (GCC, Clang), each tried by
# compiling the backend's header as C++20. With neither, there are no packed kernels for this
# target, no packed runner is built, and configuring says so. The results are cached
# (KAIRN_TESTS_NEON, KAIRN_TESTS_AVX2_WITHOUT_OPTION, KAIRN_TESTS_AVX2_WITH_OPTION). A CPU without
# AVX2 fails the AVX2 cross-checks with an illegal instruction, as one without FMA fails all.
function(_kairn_packed_backend out_backend out_option)
  set(CMAKE_CXX_STANDARD 20)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
  cmake_push_check_state(RESET)
  set(CMAKE_REQUIRED_INCLUDES "${PROJECT_SOURCE_DIR}/include")
  set(CMAKE_REQUIRED_QUIET ON)
  set(_main "int main() { return 0; }\n")
  set(_backend "")
  set(_option "")
  check_cxx_source_compiles("#include <kairn/gen/neon.hpp>\n${_main}" KAIRN_TESTS_NEON)
  if(KAIRN_TESTS_NEON)
    set(_backend neon)
  else()
    set(_source "#include <kairn/gen/avx2.hpp>\n${_main}")
    check_cxx_source_compiles("${_source}" KAIRN_TESTS_AVX2_WITHOUT_OPTION)
    if(KAIRN_TESTS_AVX2_WITHOUT_OPTION)
      set(_backend avx2)
    else()
      if(_msvc_style)
        set(_candidate /arch:AVX2)
      else()
        set(_candidate -mavx2 -mfma)
      endif()
      list(JOIN _candidate " " CMAKE_REQUIRED_FLAGS)
      check_cxx_source_compiles("${_source}" KAIRN_TESTS_AVX2_WITH_OPTION)
      if(KAIRN_TESTS_AVX2_WITH_OPTION)
        set(_backend avx2)
        set(_option ${_candidate})
      endif()
    endif()
  endif()
  cmake_pop_check_state()
  set(${out_backend} "${_backend}" PARENT_SCOPE)
  set(${out_option} "${_option}" PARENT_SCOPE)
endfunction()

set(_runners "")          # target names
set(_runner_labels "")    # the same, as they appear in test names
set(_runner_kinds "")     # scalar or packed
foreach(_kind scalar packed)
  if(_kind STREQUAL "scalar")
    set(_source "${PROJECT_SOURCE_DIR}/gen/tests/runner.cpp")
    set(_base kairn-gen-runner)
    set(_prefix cxx)
    set(_isa_option "")
  else()
    set(_source "${PROJECT_SOURCE_DIR}/gen/tests/packed_runner.cpp")
    set(_base kairn-gen-packed-runner)
    set(_packed_backend "")
    if(EXISTS "${_source}")
      _kairn_packed_backend(_packed_backend _isa_option)
    endif()
    set(_prefix "${_packed_backend}")
  endif()
  if(NOT EXISTS "${_source}" OR NOT _prefix)
    continue()
  endif()
  foreach(_i RANGE 0 ${_variants_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _variants ${_i} _variant)
    list(GET _variants ${_j} _option)
    if(_variant STREQUAL "")
      set(_target ${_base})
      set(_label ${_prefix})
    else()
      set(_target ${_base}-${_variant})
      set(_label ${_prefix}-${_variant})
    endif()
    add_executable(${_target} "${_source}")
    target_include_directories(${_target} PRIVATE "${PROJECT_SOURCE_DIR}/gen/tests")
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_warnings} ${_isa_option} ${_option})
    list(APPEND _runners ${_target})
    list(APPEND _runner_labels ${_label})
    list(APPEND _runner_kinds ${_kind})
  endforeach()
endforeach()

# --- The cross-checks ---------------------------------------------------------------------------
#
# One test per kernel of gen/claims.json and runner (and format, for the compiled runners), each a
# pipeline gen | runner | check run by crosscheck.cmake, which prints the oracle's report and
# fails when the run did not check what it set out to (see there). The toy format of the
# interpreter's test depends on the kernel's inputs (below). A kernel without a toy format, or
# whose toy format is below its min_precision, gets a test that fails and says so, instead of a
# format where its claims are not stated.
set(KAIRN_CROSSCHECK_CASES 20000 CACHE STRING
  "Random cases in each cross-check of a compiled runner, and in each sampled one of the interpreter")
set(KAIRN_CROSSCHECK_SEED 0 CACHE STRING "Seed of the random cases of the cross-checks")

# The toy formats of the interpreter, by the kernel's inputs, each written as its role: 1 a limb,
# 2 a normalized pair of limbs, r a radius (a limb with nonneg()), c a power of two (a limb with
# power_of_two()), m a mask; and then, for more than one input, sum or product: product when the
# kernel's value has a multiplication. Each is chosen so that the enumeration of every operand
# is 50 000 to 250 000 cases (gen --exhaustive --total), with the range of products below 1 so
# that most products neither overflow nor vanish, and at least the kernel's min_precision. Where
# no such format exists, the entry also names restrictions of the oracle (gen --restrict,
# comma-separated): the test then enumerates that restricted domain, and a second test runs
# KAIRN_CROSSCHECK_CASES random cases of the oracle's generator on the whole format.
#
#   inputs   kernels                                  format         cases
#   1        split                                    fp:11:-30:10    86 015
#   1 1      two_sum, fast_two_sum, add_1_1           fp:5:-7:4      172 225
#            two_prod, two_prod_dekker, mul_1_1       fp:5:-12:-1    172 225
#   r r      radd                                     fp:6:-8:4      200 704
#            rmul                                     fp:6:-13:-2    173 056
#   2        neg_2, abs_2, the conversions            fp:6:-8:4      118 335
#   2 1      add_2_1, sub_2_1, comparisons            fp:4:-4:2      221 361
#   1 2      sub_1_2, comparisons                     fp:4:-4:2      221 361
#   2 1      mul_2_1                                  fp:4:-8:-2     221 361
#   2 2      add_2_2, add_fast_2_2, sub_2_2,          fp:3:-3:2      178 929
#            comparisons
#   2 2      mul_2_2                                  fp:4:-7:-3     245 025
#   2 c      mul_pow2_2                               fp:5:-6:2      144 755
#   1 r      ball_neg_1                               fp:5:-7:4       86 320
#   2 r      ball_neg_2                               fp:4:-4:2      111 552
#   1 r 1    ball_scale_1                             fp:3:-5:0       84 700
#   2 r 1    ball_scale_2                             fp:2:-4:1       60 102
#   1 r 1 r  ball_add_1, ball_sub_1                   fp:2:-3:1       76 176
#            ball_mul_1                               fp:2:-4:0       76 176
#   2 r 2 r  ball_add_2, ball_sub_2: radii 0, 1/8,    fp:3:-3:2      148 896 of 140 million
#            1/2, 5/2 and cx in [1/2, 2)
#            ball_mul_2: radii 0, eta, 3/2, cx in     fp:4:-5:1       64 728 of 12.4 billion
#            [1, 2) and cy in [1/8, 2)
set(_toy_1 fp:11:-30:10)
set(_toy_1_1_sum fp:5:-7:4)
set(_toy_1_1_product fp:5:-12:-1)
set(_toy_r_r_sum fp:6:-8:4)
set(_toy_r_r_product fp:6:-13:-2)
set(_toy_2 fp:6:-8:4)
set(_toy_2_1_sum fp:4:-4:2)
set(_toy_1_2_sum fp:4:-4:2)
set(_toy_2_1_product fp:4:-8:-2)
set(_toy_2_2_sum fp:3:-3:2)
set(_toy_2_2_product fp:4:-7:-3)
set(_toy_2_c_product fp:5:-6:2)
set(_toy_1_r_sum fp:5:-7:4)
set(_toy_2_r_sum fp:4:-4:2)
set(_toy_1_r_1_product fp:3:-5:0)
set(_toy_2_r_1_product fp:2:-4:1)
set(_toy_1_r_1_r_sum fp:2:-3:1)
set(_toy_1_r_1_r_product fp:2:-4:0)
set(_radii "0x0p+0/0x1p-3/0x1p-1/0x1.4p+1")
set(_toy_2_r_2_r_sum fp:3:-3:2 "rx.in=${_radii},ry.in=${_radii},cx.lead=-1:0")
set(_radii "0x0p+0/0x1p-5/0x1.8p+0")
set(_toy_2_r_2_r_product fp:4:-5:1 "rx.in=${_radii},ry.in=${_radii},cx.lead=0:0,cy.lead=-3:0")

# Kernels whose intermediate values can overflow for operands far below the largest number (the
# product by the splitter), as their requirement of no intermediate overflow allows. The oracle
# counts the non-finite results of such operands as suspicious; any other kernel that returns one
# fails its cross-check (--fail-on-suspicious).
set(_intermediate_overflow split two_prod_dekker)

set(_claims_file "${PROJECT_SOURCE_DIR}/gen/claims.json")
if(Python3_Interpreter_FOUND AND EXISTS "${_claims_file}")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${_claims_file}")
  file(READ "${_claims_file}" _claims)
  string(JSON _count LENGTH "${_claims}" kernels)
  math(EXPR _last "${_count} - 1")
  set(_driver "${CMAKE_CURRENT_SOURCE_DIR}/crosscheck.cmake")
  set(_summaries "${CMAKE_CURRENT_BINARY_DIR}/crosscheck")
  set(_common "-DPYTHON=${Python3_EXECUTABLE}" "-DSOURCE_DIR=${PROJECT_SOURCE_DIR}")
  set(_random "-DCOUNT=${KAIRN_CROSSCHECK_CASES}" "-DSEED=${KAIRN_CROSSCHECK_SEED}")
  set(_n_complete 0)
  set(_n_restricted 0)
  foreach(_i RANGE ${_last})
    string(JSON _kernel GET "${_claims}" kernels ${_i} name)
    string(JSON _value ERROR_VARIABLE _no_value GET "${_claims}" kernels ${_i} value)
    string(JSON _min ERROR_VARIABLE _no_min GET "${_claims}" kernels ${_i} min_precision)
    set(_requires "")
    string(JSON _n_requires LENGTH "${_claims}" kernels ${_i} requires)
    if(_n_requires GREATER 0)
      math(EXPR _req_last "${_n_requires} - 1")
      foreach(_j RANGE ${_req_last})
        string(JSON _req GET "${_claims}" kernels ${_i} requires ${_j})
        string(REPLACE " " "" _req "${_req}")
        list(APPEND _requires "${_req}")
      endforeach()
    endif()
    # The roles of the inputs, then the operation.
    string(JSON _inputs LENGTH "${_claims}" kernels ${_i} inputs)
    set(_shape "")
    math(EXPR _in_last "${_inputs} - 1")
    foreach(_j RANGE ${_in_last})
      string(JSON _input GET "${_claims}" kernels ${_i} inputs ${_j} name)
      string(JSON _type ERROR_VARIABLE _no_type GET "${_claims}" kernels ${_i} inputs ${_j} type)
      string(JSON _limbs ERROR_VARIABLE _no_limbs GET "${_claims}" kernels ${_i} inputs ${_j} limbs)
      if(_type STREQUAL "mask")
        set(_role m)
      elseif(NOT _limbs STREQUAL "1")
        set(_role "${_limbs}")
      elseif("nonneg(${_input})" IN_LIST _requires)
        set(_role r)
      elseif("power_of_two(${_input})" IN_LIST _requires)
        set(_role c)
      else()
        set(_role 1)
      endif()
      string(APPEND _shape "_${_role}")
    endforeach()
    if(_inputs GREATER 1)
      if(_value MATCHES "\\*")
        string(APPEND _shape "_product")
      else()
        string(APPEND _shape "_sum")
      endif()
    endif()
    set(_fail_on_suspicious ON)
    if(_kernel IN_LIST _intermediate_overflow)
      set(_fail_on_suspicious OFF)
    endif()
    set(_this ${_common} "-DKERNEL=${_kernel}" "-DFAIL_ON_SUSPICIOUS=${_fail_on_suspicious}")

    # The interpreter, on every operand of the toy format, or of a restricted domain of it and
    # on random cases of all of it.
    set(_toy "${_toy${_shape}}")
    list(LENGTH _toy _toy_length)
    set(_restrict "")
    if(_toy_length GREATER 1)
      list(GET _toy 1 _restrict)
      list(GET _toy 0 _toy)
    endif()
    set(_error "")
    if(NOT _toy)
      string(REPLACE "_" " " _operands "${_shape}")
      set(_error "no toy format is chosen for the inputs of ${_kernel} (${_operands}): "
        "add one in tests/CMakeLists.txt")
    elseif(_min MATCHES "^[0-9]+$")
      string(REGEX REPLACE "^fp:([0-9]+):.*" "\\1" _p "${_toy}")
      if(_p LESS _min)
        set(_error "the toy format ${_toy} of ${_kernel} is below its min_precision ${_min}: "
          "choose another in tests/CMakeLists.txt")
      endif()
    endif()
    if(_restrict)
      set(_name crosscheck.interp-restricted.${_kernel})
      set(_labels crosscheck interp restricted)
      math(EXPR _n_restricted "${_n_restricted} + 1")
    else()
      set(_name crosscheck.interp.${_kernel})
      set(_labels crosscheck interp)
      math(EXPR _n_complete "${_n_complete} + 1")
    endif()
    if(_error)
      string(JOIN "" _error ${_error})
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" "-DERROR=${_error}" -P "${_driver}")
    else()
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy}"
        -DRUNNER=interp -DEXHAUSTIVE=ON "-DRESTRICT=${_restrict}"
        "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
    endif()
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "${_labels}")
    if(_restrict AND NOT _error)
      set(_name crosscheck.interp-sampled.${_kernel})
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy}"
        -DRUNNER=interp ${_random} "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
      set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;interp;sampled")
    endif()

    # The compiled runners, on random cases of every stratum.
    foreach(_runner _label _kind IN ZIP_LISTS _runners _runner_labels _runner_kinds)
      foreach(_format binary64 binary32)
        set(_name crosscheck.${_label}.${_kernel}.${_format})
        add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_format}"
          "-DRUNNER=$<TARGET_FILE:${_runner}>" ${_random} "-DSUMMARY=${_summaries}/${_name}.json"
          -P "${_driver}")
        if(_kind STREQUAL "scalar")
          set(_labels crosscheck cxx)
        else()
          set(_labels crosscheck packed)
        endif()
        if(_label MATCHES "-")
          list(APPEND _labels contraction)
        endif()
        set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "${_labels}")
      endforeach()
    endforeach()
  endforeach()
  # The guards of crosscheck.cmake fail the runs they are there to fail: a partial or restricted
  # enumeration, a missing stratum, nothing judged, a comparison seen one way only.
  add_test(NAME crosscheck.guards
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_crosscheck_guards.py"
      "${CMAKE_COMMAND}"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(crosscheck.guards PROPERTIES TIMEOUT 300 LABELS crosscheck)

  set(_packed "no packed runners (no packed backend for this target)")
  if(_packed_backend)
    if(_isa_option)
      list(JOIN _isa_option " " _packed)
      set(_packed "packed runners for ${_packed_backend}, with ${_packed}")
    else()
      set(_packed "packed runners for ${_packed_backend}")
    endif()
  endif()
  list(JOIN _runner_labels ", " _labels)
  message(STATUS "Kairn tests: cross-checks of ${_count} kernels: the interpreter on "
    "${_n_complete} complete enumerations of toy formats and ${_n_restricted} restricted ones "
    "(each with a sampled run), and the compiled runners ${_labels} (${_packed})")
endif()

# --- The consumer checks ------------------------------------------------------------------------
#
# They build their project with ctest --build-and-test, with this build's generator and compiler,
# and run its program, which checks the version it is given against version.hpp and runs a kernel.
set(_consume_dir "${CMAKE_CURRENT_BINARY_DIR}/consume")
set(_build_and_test --build-generator "${CMAKE_GENERATOR}" --build-project kairn_consume)
if(CMAKE_GENERATOR_PLATFORM)
  list(APPEND _build_and_test --build-generator-platform "${CMAKE_GENERATOR_PLATFORM}")
endif()
if(CMAKE_GENERATOR_TOOLSET)
  list(APPEND _build_and_test --build-generator-toolset "${CMAKE_GENERATOR_TOOLSET}")
endif()
if(CMAKE_MAKE_PROGRAM)
  list(APPEND _build_and_test --build-makeprogram "${CMAKE_MAKE_PROGRAM}")
endif()
set(_config "")
set(_build_type "")
get_property(_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(_multi_config)
  set(_config -C "$<CONFIG>")
elseif(CMAKE_BUILD_TYPE)
  set(_build_type "-DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}")
endif()
set(_build_options --build-options "-DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}" ${_build_type})
set(_run --test-command consume "${PROJECT_VERSION}")

add_test(NAME consume.add_subdirectory
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${CMAKE_CURRENT_SOURCE_DIR}/consume/add_subdirectory" "${_consume_dir}/add_subdirectory"
    ${_build_and_test} ${_build_options} "-DKAIRN_SOURCE_DIR=${PROJECT_SOURCE_DIR}" ${_run})

add_test(NAME consume.install
  COMMAND "${CMAKE_COMMAND}" "-DBUILD_DIR=${PROJECT_BINARY_DIR}" "-DPREFIX=${_consume_dir}/prefix"
    "-DCONFIG=$<CONFIG>" -P "${CMAKE_CURRENT_SOURCE_DIR}/consume/install.cmake")
set_tests_properties(consume.install PROPERTIES FIXTURES_SETUP kairn_installed)

add_test(NAME consume.find_package
  COMMAND "${CMAKE_CTEST_COMMAND}" ${_config} --build-and-test
    "${CMAKE_CURRENT_SOURCE_DIR}/consume/find_package" "${_consume_dir}/find_package"
    ${_build_and_test} ${_build_options} "-DCMAKE_PREFIX_PATH=${_consume_dir}/prefix" ${_run})
set_tests_properties(consume.find_package PROPERTIES FIXTURES_REQUIRED kairn_installed)
add_subdirectory(api)
