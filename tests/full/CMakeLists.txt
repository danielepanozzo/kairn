# The full tier (docs/developer/testing.md): every test that left the quick tier to keep it quick,
# registered here, each named full.* and labelled full, and run by
#
#   ctest --test-dir build/tests/full --output-on-failure
#
# A ctest run at the top of the build tree leaves these out (tests/CMakeLists.txt, "The two
# tiers"). Besides full, a label says what each test depends on, which is how the CI
# (.github/workflows/full.yml) runs each where it must and no more:
#
# - none: the build's compiler. full.crosscheck.compiled.KERNEL.FORMAT, every compiled runner on
#   KAIRN_CROSSCHECK_CASES cases, full.api.oracle.KERNEL.FORMAT, every public form on
#   KAIRN_API_CASES cases (api/CMakeLists.txt), and full.objcode.check and full.objcode.controls,
#   the object code on the whole flag matrix (label objcode): on every platform and compiler of the
#   CI.
# - python: Python alone, in exact arithmetic (the interpreter, the oracle and its Python runner
#   compute with integers and fractions), so the same on every platform: the interpreter's
#   enumerations of toy formats and the oracle's own enumerations. Once in the CI.
# - generator: the generator's tests without C++, which also compare the interpreter with the
#   machine's own arithmetic (Python's float and math.fma), so on every operating system. The CI
#   runs them in generator.yml, inside the generator's whole suite.
# - tools: the tools' own tests (below), which were in the quick tier. Those of the generator are
#   labelled generator too; the others neither python nor generator, so that the CI runs them with
#   every compiler, as it ran them in the quick tier.
#
# This file is processed after tests/CMakeLists.txt and api/, whose variables say what to register.

# --- The longest tests of the generator and of the oracle ---------------------------------------
#
# Each uses a pool of worker processes, by default one per processor: four here (KAIRN_GEN_JOBS,
# --jobs), and ctest counts the four (PROCESSORS), so that it does not start three more tests
# beside them. Without the count, the generator's test ran past its timeout of 600 seconds on the
# Windows machine of docs/developer/testing.md (8 logical processors, --parallel 4), beside the
# oracle's and two enumerations of the interpreter, where it takes 149 seconds counted. The price
# is on a machine with many processors and a low --parallel: with --parallel 4, each runs alone
# (on 16 threads of the Linux machine the full tier took 452 seconds, against 260 uncounted).
# The generator's test judges every kernel in the interpreter and its statements on thousands of
# cases; with the 223 kernels and 44 folds of the joined tree of stage B2 it took 748 seconds alone
# on the Linux machine (GCC 13, its four workers), past the 600 of the oracle's test below: its
# limit is 1800.
if(EXISTS "${PROJECT_SOURCE_DIR}/gen/kairn-gen")
  set(_args "")
  foreach(_pattern IN LISTS _gen_full)
    list(APPEND _args -k "${_pattern}")
  endforeach()
  add_test(NAME full.kairn-gen.test
    COMMAND "${Python3_EXECUTABLE}" gen/kairn-gen test --no-cxx ${_args}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.kairn-gen.test PROPERTIES TIMEOUT 1800 PROCESSORS 4
    ENVIRONMENT KAIRN_GEN_JOBS=4 LABELS "full;generator")
endif()
if(EXISTS "${PROJECT_SOURCE_DIR}/oracle/kairn-oracle")
  add_test(NAME full.kairn-oracle.selftest
    COMMAND "${Python3_EXECUTABLE}" oracle/kairn-oracle selftest --quick
      --only "${_oracle_full_names}" --jobs 4 --cxx "${CMAKE_CXX_COMPILER}"
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/oracle-selftest"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.kairn-oracle.selftest PROPERTIES TIMEOUT 600 PROCESSORS 4
    LABELS "full;python"
    FAIL_REGULAR_EXPRESSION "SKIP [^\n]*(no C\\+\\+ compiler|compiling the C\\+\\+ runner)")
endif()

# --- The tools' own tests -----------------------------------------------------------------------
#
# The tests of the tools rather than of the library, each the quick tier's test of the name after
# full.tools., which they left so that the quick tier keeps to its budget on the hosted runners
# (docs/developer/testing.md, "Time"); together they were two fifths of its test time there, and
# none builds anything of Kairn's with the build's compiler. Run as python3 SCRIPT ARGS from the
# repository root:
# - full.tools.kairn-gen.test: gen/kairn-gen test without its C++ tests (--no-cxx) and without the
#   four test classes that full.kairn-gen.test runs (--skip). The C++ tests build the generated
#   code at -O0 and -O2, with and without -frounding-math, under every contraction setting, and
#   compare it bit for bit with the interpreter: about two thirds of the suite's time, and what the
#   cross-checks cover for this build's compiler and flags. Label generator: the CI runs the whole
#   suite, C++ included, in generator.yml; by hand, python3 gen/kairn-gen test. With the 223
#   kernels and 44 folds of the joined tree of the ball vectors and stage B2 it took 571 seconds on
#   the Linux machine (GCC 13, the full tier), near its limit of 600, as full.kairn-gen.test above
#   had gone past it: its limit is 1800.
# - full.tools.kairn-oracle.selftest: oracle/kairn-oracle selftest --quick without the six tests of
#   full.kairn-oracle.selftest (--skip). It compiles its own C++ runner with this build's compiler,
#   in the build tree, and skips the tests that need it, with a SKIP line, if the compiler does not
#   work: with a compiler given, a failure here. (Its other skip, of rounding_hardware on Python
#   older than 3.13, which has no math.fma, is not.)
# - full.tools.crosscheck.guards.CLASS, one per class of tests/test_crosscheck_guards.py: the
#   cross-checks' guards fail the runs they are there to fail (a
#   partial or restricted enumeration, a missing stratum, nothing judged, a comparison seen one way
#   only), as tests/crosscheck_guards.py, as tests/crosscheck.py calls them (with the interpreter
#   as its runner, and with the public interface's runner of this build), and as crosscheck.cmake
#   runs them with this cmake.
# - full.tools.docs.reference.test: docs/tools/test_reference.py, the tests of the script that
#   writes the reference pages (docs.reference.check, in the quick tier, checks the pages).
# - full.tools.brute.driver.test: tests/brute/test_brute.py, the tests of the brute-force driver
#   (the plan of the enumerations, the forms of the fix-ups, widen.py on one small format), which
#   itself runs by hand, never here (tests/brute/README.md).
if(EXISTS "${PROJECT_SOURCE_DIR}/gen/kairn-gen")
  set(_args "")
  foreach(_pattern IN LISTS _gen_full)
    list(APPEND _args --skip "${_pattern}")
  endforeach()
  add_test(NAME full.tools.kairn-gen.test
    COMMAND "${Python3_EXECUTABLE}" gen/kairn-gen test --no-cxx ${_args}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.tools.kairn-gen.test PROPERTIES TIMEOUT 1800
    LABELS "full;tools;generator")
endif()
if(EXISTS "${PROJECT_SOURCE_DIR}/oracle/kairn-oracle")
  add_test(NAME full.tools.kairn-oracle.selftest
    COMMAND "${Python3_EXECUTABLE}" oracle/kairn-oracle selftest --quick
      --skip "${_oracle_full_names}" --cxx "${CMAKE_CXX_COMPILER}"
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/oracle-selftest-tools"
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.tools.kairn-oracle.selftest PROPERTIES TIMEOUT 600 LABELS "full;tools"
    FAIL_REGULAR_EXPRESSION "SKIP [^\n]*(no C\\+\\+ compiler|compiling the C\\+\\+ runner)")
endif()
if(EXISTS "${PROJECT_SOURCE_DIR}/tests/test_crosscheck_guards.py")
  # One test per class of the file (full.tools.crosscheck.guards.CLASS), so that they run side by
  # side and none nears its time limit: as one test the file took 300 s on a 16-core machine once
  # the guards of the intervals, the maps and the convolutions were in it, and a hosted Windows
  # runner is about four times slower (it starts several hundred Python processes). The classes are
  # read from the file, so a class added there is run without a change here.
  file(STRINGS "${PROJECT_SOURCE_DIR}/tests/test_crosscheck_guards.py" _guard_classes
    REGEX "^class [A-Za-z0-9_]+\\(unittest\\.TestCase\\):")
  if(NOT _guard_classes)
    message(FATAL_ERROR "tests/test_crosscheck_guards.py: no test class found")
  endif()
  foreach(_line IN LISTS _guard_classes)
    string(REGEX REPLACE "^class ([A-Za-z0-9_]+).*" "\\1" _class "${_line}")
    add_test(NAME full.tools.crosscheck.guards.${_class}
      COMMAND "${Python3_EXECUTABLE}" tests/test_crosscheck_guards.py --claims "${KAIRN_ORACLE_CLAIMS}"
        "${CMAKE_COMMAND}" "$<TARGET_FILE:kairn-api-runner>" ${_class}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
    set_tests_properties(full.tools.crosscheck.guards.${_class} PROPERTIES TIMEOUT 900
      LABELS "full;tools;crosscheck")
  endforeach()
endif()
if(EXISTS "${PROJECT_SOURCE_DIR}/docs/tools/test_reference.py")
  add_test(NAME full.tools.docs.reference.test
    COMMAND "${Python3_EXECUTABLE}" docs/tools/test_reference.py
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.tools.docs.reference.test PROPERTIES LABELS "full;tools;docs")
endif()
if(EXISTS "${PROJECT_SOURCE_DIR}/tests/brute/test_brute.py")
  add_test(NAME full.tools.brute.driver.test
    COMMAND "${Python3_EXECUTABLE}" tests/brute/test_brute.py
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.tools.brute.driver.test PROPERTIES LABELS "full;tools")
endif()

# --- The cross-checks ---------------------------------------------------------------------------
#
# Kernel by kernel, as tests/CMakeLists.txt worked them out: the interpreter on every operand of
# the kernel's toy format, or of a restricted domain of it and on random cases of all of it
# (crosscheck.cmake, the three stages of the pipeline at once); and every compiled runner on
# KAIRN_CROSSCHECK_CASES cases of each format, with the kernels' runners of the flag sets
# (api/flags/: the debug build, and one set at -O1 or /O1), in one Python process
# (tests/crosscheck.py).
set(_summaries "${CMAKE_CURRENT_BINARY_DIR}/crosscheck")
set(_compiled_full ${_compiled})
foreach(_runner _label IN ZIP_LISTS _flags_gen_runners _flags_gen_labels)
  list(APPEND _compiled_full --runner "${_label}" "$<TARGET_FILE:${_runner}>")
endforeach()
foreach(_kernel IN LISTS _full_kernels)
  set(_this ${_full_${_kernel}_this})
  set(_this_compiled ${_full_${_kernel}_this_compiled})
  set(_toy "${_full_${_kernel}_toy}")
  set(_restrict "${_full_${_kernel}_restrict}")
  set(_error "${_full_${_kernel}_error}")
  if(_restrict)
    set(_name full.crosscheck.interp-restricted.${_kernel})
    set(_labels full python crosscheck interp restricted)
  else()
    set(_name full.crosscheck.interp.${_kernel})
    set(_labels full python crosscheck interp)
  endif()
  if(_error)
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" "-DERROR=${_error}" -P "${_driver}")
  else()
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy}"
      -DRUNNER=interp -DEXHAUSTIVE=ON "-DRESTRICT=${_restrict}"
      "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
  endif()
  set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "${_labels}")
  # The sampled run: of the whole toy format for a restricted enumeration, or of a format of its
  # own where tests/CMakeLists.txt names one (_toy_sampled..., the interval kernels).
  set(_sampled "${_full_${_kernel}_sampled}")
  if(NOT _sampled AND _restrict)
    set(_sampled "${_toy}")
  endif()
  if(_sampled AND NOT _error)
    set(_name full.crosscheck.interp-sampled.${_kernel})
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_sampled}"
      -DRUNNER=interp ${_random} "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300
      LABELS "full;python;crosscheck;interp;sampled")
  endif()

  if(_compiled)
    foreach(_format binary64 binary32)
      set(_name full.crosscheck.compiled.${_kernel}.${_format})
      add_test(NAME ${_name} COMMAND ${_crosscheck} ${_this_compiled} --format ${_format}
        ${_random_args} --summary "${_summaries}/${_name}.json" ${_compiled_full})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;crosscheck;compiled")
    endforeach()
  endif()
endforeach()

# The folds, as tests/CMakeLists.txt worked them out: the interpreter on every array of a tiny
# format up to a small length (full.crosscheck.interp.FOLD) and on KAIRN_CROSSCHECK_FOLD_CASES
# random arrays of a toy format up to 1024 elements (full.crosscheck.interp-sampled.FOLD); every
# compiled runner on KAIRN_CROSSCHECK_FOLD_CASES random arrays up to KAIRN_CROSSCHECK_FOLD_LENGTH
# elements of each format, the scalar ones on every order and the packed ones on the lane order of
# their register, with the kernels' runners of the flag sets (full.crosscheck.compiled.FOLD.FORMAT).
set(_compiled_full_scalar ${_compiled_scalar})
set(_compiled_full_packed ${_compiled_packed})
foreach(_runner _label IN ZIP_LISTS _flags_gen_runners _flags_gen_labels)
  if(_label MATCHES "^cxx")
    list(APPEND _compiled_full_scalar --runner "${_label}" "$<TARGET_FILE:${_runner}>")
  else()
    list(APPEND _compiled_full_packed --packed-runner "${_label}" "$<TARGET_FILE:${_runner}>")
  endif()
endforeach()
foreach(_fold IN LISTS _full_folds)
  set(_toy "${_full_fold_${_fold}_toy}")
  set(_error "${_full_fold_${_fold}_error}")
  set(_this ${_common} "-DKERNEL=${_fold}" -DFAIL_ON_SUSPICIOUS=ON)
  if(_error)
    add_test(NAME full.crosscheck.interp.${_fold} COMMAND "${CMAKE_COMMAND}" "-DERROR=${_error}"
      -P "${_driver}")
    set_tests_properties(full.crosscheck.interp.${_fold} PROPERTIES LABELS
      "full;python;crosscheck;interp;fold")
  else()
    list(GET _toy 0 _toy_enum)
    list(GET _toy 1 _toy_length)
    list(GET _toy 2 _toy_sampled)
    set(_name full.crosscheck.interp.${_fold})
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy_enum}"
      -DRUNNER=interp -DEXHAUSTIVE=ON "-DMAX_LENGTH=${_toy_length}"
      "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300 LABELS "full;python;crosscheck;interp;fold")
    set(_name full.crosscheck.interp-sampled.${_fold})
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy_sampled}"
      -DRUNNER=interp "-DCOUNT=${_full_fold_${_fold}_cases}" "-DSEED=${KAIRN_CROSSCHECK_SEED}"
      "-DMAX_LENGTH=${_full_fold_${_fold}_sampled_length}" "-DSUMMARY=${_summaries}/${_name}.json"
      -P "${_driver}")
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300
      LABELS "full;python;crosscheck;interp;sampled;fold")
  endif()
  if(_compiled_full_scalar)
    foreach(_format binary64 binary32)
      set(_packed_args "")
      if(_full_fold_${_fold}_${_format}_lanes)
        set(_packed_args ${_compiled_full_packed} --packed-lanes ${_full_fold_${_fold}_${_format}_lanes}
          --packed-count ${KAIRN_CROSSCHECK_FOLD_PACKED_CASES})
      endif()
      set(_name full.crosscheck.compiled.${_fold}.${_format})
      add_test(NAME ${_name} COMMAND ${_crosscheck} ${_full_fold_${_fold}_compiled} --format ${_format}
        --seed "${KAIRN_CROSSCHECK_SEED}" --count "${_full_fold_${_fold}_cases}"
        --max-length "${_full_fold_${_fold}_length}" --summary "${_summaries}/${_name}.json"
        ${_compiled_full_scalar} ${_packed_args})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;crosscheck;compiled;fold")
    endforeach()
  endif()
endforeach()

# --- The object code ----------------------------------------------------------------------------
#
# objcode.check and objcode.controls of tests/CMakeLists.txt on every configuration of the
# compiler's flag matrix, four compilations at once.
if(_objcode_command)
  add_test(NAME full.objcode.check
    COMMAND ${_objcode_command} --tier full --jobs 4 --workdir "${CMAKE_CURRENT_BINARY_DIR}/objcode/check")
  add_test(NAME full.objcode.controls
    COMMAND ${_objcode_command} --controls --tier full --jobs 4
      --workdir "${CMAKE_CURRENT_BINARY_DIR}/objcode/controls")
  set_tests_properties(full.objcode.check full.objcode.controls PROPERTIES TIMEOUT 1200 PROCESSORS 4
    LABELS "full;objcode")
endif()

# --- The adversarial search (begin) -------------------------------------------------------------
#
# full.search.compiled: kairn-oracle search on every kernel with an error, upper, encloses or
# extends entry, binary64 and binary32, through the scalar runner with the build's flags, 5 000
# cases per kernel and format from its seeds (the attaining lines of results/*/brute/, the
# regression cases, the literature, the strata), with --fail-on-suspicious as the cross-checks.
# Four worker processes, counted (PROCESSORS). Fails on any violated claim.
if(TARGET kairn-gen-runner)
  add_test(NAME full.search.compiled
    COMMAND "${Python3_EXECUTABLE}" oracle/kairn-oracle search all binary64,binary32
      --runner "$<TARGET_FILE:kairn-gen-runner>" --evals 5000 --jobs 4 --quiet
      --claims "${KAIRN_ORACLE_CLAIMS}"
      --fail-on-suspicious --suspicious-ok split,two_prod_dekker
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.search.compiled PROPERTIES TIMEOUT 600 PROCESSORS 4
    LABELS "full;search")
endif()
# --- The adversarial search (end) ---------------------------------------------------------------

# --- The public interface against the oracle ----------------------------------------------------
#
# Every public form of every kernel api/CMakeLists.txt maps, with both of its runners, on
# KAIRN_API_CASES cases (the quick tier has KAIRN_API_QUICK_CASES of the same seed), and the
# debug build's runner, which the quick tier leaves out, on the first form of each kernel.
set(_api_full_common ${_api_oracle_common} ${_api_debug_runner} --first-form debug)
# And the runners of the other settings of KAIRN_ENCLOSURE_CODE (the operations of Ball outlined and
# external, include/kairn/config.hpp), built with the build's own level (api/flags/), every form of
# which must write the same bytes as the same form of the runner with the build's flags.
foreach(_set IN LISTS _flags_enclosure_sets)
  list(APPEND _api_full_common --runner ${_set} "$<TARGET_FILE:kairn-api-runner-${_set}>" --same-as ${_set} build)
endforeach()
foreach(_kernel IN LISTS _api_oracle_kernels)
  foreach(_format binary64 binary32)
    set(_name full.api.oracle.${_kernel}.${_format})
    add_test(NAME ${_name}
      COMMAND ${_crosscheck} api --kernel ${_kernel} --format ${_format} --count ${KAIRN_API_CASES}
        --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/api-oracle" ${_api_full_common})
    set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle")
  endforeach()
endforeach()

# --- The flag sets (api/flags/) -----------------------------------------------------------------
#
# full.api.flags.oracle.KERNEL.FORMAT: every public form of the kernel, through the runner of each
# flag set, on KAIRN_API_QUICK_CASES cases (the quick tier's cases). For each set but the debug
# build, which the quick tier has:
# full.api.flags.SET.self_test, kairn::self_test() and kairn::environment_ok() compiled with the
# set's flags (tests/api/runner.cpp --self-test), and full.api.flags.SET.constexpr,
# tests/api/constexpr.cpp built with them.
foreach(_kernel IN LISTS _api_oracle_kernels)
  foreach(_format binary64 binary32)
    set(_name full.api.flags.oracle.${_kernel}.${_format})
    add_test(NAME ${_name}
      COMMAND ${_crosscheck} api --kernel ${_kernel} --format ${_format}
        --count ${KAIRN_API_QUICK_CASES} --summary-dir "${CMAKE_CURRENT_BINARY_DIR}/api-flags"
        ${_api_flags_common})
    set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle;flags")
  endforeach()
endforeach()
foreach(_set IN LISTS _flags_names)
  if(_set STREQUAL "debug")
    continue()
  endif()
  add_test(NAME full.api.flags.${_set}.self_test COMMAND kairn-api-runner-${_set} --self-test)
  add_test(NAME full.api.flags.${_set}.constexpr COMMAND kairn-api-constexpr-${_set})
  add_test(NAME full.api.flags.${_set}.rational COMMAND kairn-api-rational-${_set})
  set_tests_properties(full.api.flags.${_set}.self_test full.api.flags.${_set}.constexpr
    full.api.flags.${_set}.rational PROPERTIES TIMEOUT 120 LABELS "full;api;flags")
endforeach()

# --- The checks in the other settings of KAIRN_ENCLOSURE_CODE -----------------------------------
#
# full.api.checks.SETTING.GROUP and full.api.checks.handler.SETTING: api.checks.release.* and
# api.checks.handler with the operations of Ball outlined and external (include/kairn/config.hpp),
# whose checks are then in functions of their own (api/CMakeLists.txt builds the programs).
foreach(_setting outlined external)
  foreach(_group default rounding flush operands)
    add_test(NAME full.api.checks.${_setting}.${_group}
      COMMAND "${CMAKE_COMMAND}" "-DPROGRAM=$<TARGET_FILE:kairn-api-checks-${_setting}>" "-DGROUP=${_group}"
        "-DEXPECT_FLUSH=${_api_expect_flush}" -P "${PROJECT_SOURCE_DIR}/tests/api/checks.cmake")
    set_tests_properties(full.api.checks.${_setting}.${_group} PROPERTIES TIMEOUT 300 LABELS "full;api;checks")
  endforeach()
  add_test(NAME full.api.checks.handler.${_setting} COMMAND kairn-api-checks-handler-${_setting})
  set_tests_properties(full.api.checks.handler.${_setting} PROPERTIES TIMEOUT 120 LABELS "full;api;checks")
endforeach()

# --- kairn::rational against the oracle ----------------------------------------------------------
#
# full.api.rational.KIND.FORMAT: KAIRN_RATIONAL_CASES cases of rational_KIND (the quick tier has
# KAIRN_RATIONAL_QUICK_CASES of the same seed), through the runner with the build's flags and the
# runner of every flag set, the debug build's included: integer code, so every output must be the
# same bytes, and the oracle judges each distinct output once (tests/crosscheck.py compiled).
if(_api_rational_common)
  set(_runners --runner build "$<TARGET_FILE:kairn-api-rational-runner>")
  foreach(_set IN LISTS _flags_names)
    list(APPEND _runners --runner ${_set} "$<TARGET_FILE:kairn-api-rational-runner-${_set}>")
  endforeach()
  foreach(_kind 1 2)
    foreach(_format binary64 binary32)
      set(_name full.api.rational.${_kind}.${_format})
      add_test(NAME ${_name}
        COMMAND ${_api_rational_common} --kernel rational_${_kind} --format ${_format}
          --count ${KAIRN_RATIONAL_CASES}
          --summary "${CMAKE_CURRENT_BINARY_DIR}/rational/rational_${_kind}.${_format}.json"
          ${_runners})
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle;rational")
    endforeach()
  endforeach()
endif()
