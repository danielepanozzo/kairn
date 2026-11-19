# Kairn's tests, registered with ctest when KAIRN_BUILD_TESTS is on; together they are the quick
# tier (docs/developer/testing.md):
#
#   ctest --test-dir build --output-on-failure        (add -C CONFIG for a multi-config generator)
#
# - The entry points of docs/developer/architecture.md that run tests, each registered only if its
#   script exists when CMake runs (configure again after one is added). They need Python 3; without
#   it they are left out, as are the cross-checks, and nothing else changes.
# - The cross-checks: the oracle judges every kernel of gen/claims.json as run by the generator's
#   interpreter on every operand of a toy format, and as compiled with this build's compiler and
#   flags (gen/tests/runner.cpp) on random binary64 and binary32 cases, once as the flags stand and
#   once per contraction setting that matters to this compiler.
# - The consumer checks (consume/): a project that uses kairn::kairn and kairn::fma through
#   add_subdirectory, and one that uses them through find_package after this build tree is
#   installed into a prefix under the build directory.

find_package(Python3 COMPONENTS Interpreter)

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
# - gen/kairn-gen test compiles the generated C++ with this build's compiler (--cxx), passing
#   GCC-style flags, so for MSVC and clang-cl its C++ tests are skipped (--no-cxx). Either option
#   sets KAIRN_GEN_CXX for the tests; an option, rather than the environment, because on Windows an
#   empty environment variable is no variable at all.
# - oracle/kairn-oracle selftest compiles its own C++ runner with the same compiler, in the build
#   tree. It skips the tests that need it, with a SKIP line, if the compiler does not work; with a
#   compiler given that is a failure here. (Its other skip, of rounding_hardware on Python older
#   than 3.13, which has no math.fma, is not.)
# - oracle/kairn-oracle check --claims-only reads every claim of gen/claims.json.
if(_msvc_style)
  set(_gen_cxx --no-cxx)
else()
  set(_gen_cxx --cxx "${CMAKE_CXX_COMPILER}")
endif()
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
    list(APPEND _args ${_gen_cxx})
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
# gen/tests/runner.cpp runs the generated scalar kernels on the line protocol. It is built with
# this build's compiler and flags (kairn-gen-runner), and once more for each contraction setting
# that matters to the compiler, appended to those flags: the regression test of the contraction
# experiment of docs/developer/design/phase0/environment.md. A compiler only contracts when it
# optimizes, which is why a top-level build defaults to Release.
set(_runner_source "${PROJECT_SOURCE_DIR}/gen/tests/runner.cpp")
set(_runners "")          # target names
set(_runner_labels "")    # the same, as they appear in test names
if(EXISTS "${_runner_source}")
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
  set(_variants "" "")    # name, option: the plain runner first
  list(APPEND _variants ${_settings})
  list(LENGTH _variants _n)
  math(EXPR _last "${_n} - 1")
  foreach(_i RANGE 0 ${_last} 2)
    math(EXPR _j "${_i} + 1")
    list(GET _variants ${_i} _variant)
    list(GET _variants ${_j} _option)
    if(_variant STREQUAL "")
      set(_target kairn-gen-runner)
      set(_label cxx)
    else()
      set(_target kairn-gen-runner-${_variant})
      set(_label cxx-${_variant})
    endif()
    add_executable(${_target} "${_runner_source}")
    target_include_directories(${_target} PRIVATE "${PROJECT_SOURCE_DIR}/gen/tests")
    target_link_libraries(${_target} PRIVATE kairn::kairn kairn::fma)
    target_compile_options(${_target} PRIVATE ${_warnings} ${_option})
    list(APPEND _runners ${_target})
    list(APPEND _runner_labels ${_label})
  endforeach()
endif()

# --- The cross-checks ---------------------------------------------------------------------------
#
# One test per kernel of gen/claims.json and runner (and format, for the compiled runners), each a
# pipeline gen | runner | check run by crosscheck.cmake, which prints the oracle's report. The
# toy format of the interpreter's test depends on the kernel's operands (below); every operand
# combination of it is run. A kernel whose toy format is below its min_precision gets a test that
# fails and says so, instead of a format where its claims are not stated.
set(KAIRN_CROSSCHECK_CASES 20000 CACHE STRING
  "Random cases per kernel and format in each cross-check of a compiled runner")
set(KAIRN_CROSSCHECK_SEED 0 CACHE STRING "Seed of the random cases of the cross-checks")

# The toy formats, by operands, chosen so that each enumeration is 50 000 to 250 000 cases. For
# products the range sits below 1, so that most products neither overflow nor vanish.
#   one input, one limb (split)               fp:11:-30:10
#   two inputs of one limb, sum or product    fp:5:-7:4,  fp:5:-12:-1
#   two limbs and one limb                    fp:4:-4:2,  fp:4:-8:-2
#   two limbs and two limbs                   fp:3:-3:2,  fp:4:-7:-3
set(_toy_1 fp:11:-30:10)
set(_toy_1_1_sum fp:5:-7:4)
set(_toy_1_1_product fp:5:-12:-1)
set(_toy_2_1_sum fp:4:-4:2)
set(_toy_2_1_product fp:4:-8:-2)
set(_toy_2_2_sum fp:3:-3:2)
set(_toy_2_2_product fp:4:-7:-3)

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
  foreach(_i RANGE ${_last})
    string(JSON _kernel GET "${_claims}" kernels ${_i} name)
    string(JSON _value GET "${_claims}" kernels ${_i} value)
    string(JSON _min ERROR_VARIABLE _no_min GET "${_claims}" kernels ${_i} min_precision)
    string(JSON _inputs LENGTH "${_claims}" kernels ${_i} inputs)
    set(_shape "")
    math(EXPR _in_last "${_inputs} - 1")
    foreach(_j RANGE ${_in_last})
      string(JSON _limbs GET "${_claims}" kernels ${_i} inputs ${_j} limbs)
      string(APPEND _shape "_${_limbs}")
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

    # The interpreter, on every operand of the toy format.
    set(_name crosscheck.interp.${_kernel})
    set(_toy "${_toy${_shape}}")
    set(_error "")
    if(NOT _toy)
      string(REPLACE "_" " " _operands "${_shape}")
      set(_error "no toy format is chosen for the operands of ${_kernel} (limbs${_operands}): "
        "add one in tests/CMakeLists.txt")
    elseif(_min MATCHES "^[0-9]+$")
      string(REGEX REPLACE "^fp:([0-9]+):.*" "\\1" _p "${_toy}")
      if(_p LESS _min)
        set(_error "the toy format ${_toy} of ${_kernel} is below its min_precision ${_min}: "
          "choose another in tests/CMakeLists.txt")
      endif()
    endif()
    if(_error)
      string(JOIN "" _error ${_error})
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" "-DERROR=${_error}" -P "${_driver}")
    else()
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_common} "-DKERNEL=${_kernel}"
        "-DFORMAT=${_toy}" -DRUNNER=interp -DEXHAUSTIVE=ON
        "-DFAIL_ON_SUSPICIOUS=${_fail_on_suspicious}" "-DSUMMARY=${_summaries}/${_name}.json"
        -P "${_driver}")
    endif()
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "crosscheck;interp")

    # The compiled runners, on random cases of every stratum.
    foreach(_runner _label IN ZIP_LISTS _runners _runner_labels)
      foreach(_format binary64 binary32)
        set(_name crosscheck.${_label}.${_kernel}.${_format})
        add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_common} "-DKERNEL=${_kernel}"
          "-DFORMAT=${_format}" "-DRUNNER=$<TARGET_FILE:${_runner}>"
          "-DCOUNT=${KAIRN_CROSSCHECK_CASES}" "-DSEED=${KAIRN_CROSSCHECK_SEED}"
          "-DFAIL_ON_SUSPICIOUS=${_fail_on_suspicious}" "-DSUMMARY=${_summaries}/${_name}.json"
          -P "${_driver}")
        set(_labels crosscheck cxx)
        if(NOT _label STREQUAL "cxx")
          list(APPEND _labels contraction)
        endif()
        set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "${_labels}")
      endforeach()
    endforeach()
  endforeach()
  list(LENGTH _runners _n_runners)
  message(STATUS "Kairn tests: cross-checks of ${_count} kernels with the interpreter and "
    "${_n_runners} compiled runners (${_runner_labels})")
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
