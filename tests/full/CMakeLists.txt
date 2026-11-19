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
#   KAIRN_CROSSCHECK_CASES cases, and full.api.oracle.KERNEL.FORMAT, every public form on
#   KAIRN_API_CASES cases (api/CMakeLists.txt): on every platform and compiler of the CI.
# - python: Python alone, in exact arithmetic (the interpreter, the oracle and its Python runner
#   compute with integers and fractions), so the same on every platform: the interpreter's
#   enumerations of toy formats and the oracle's own enumerations. Once in the CI.
# - generator: the generator's longest tests, which also compare the interpreter with the
#   machine's own arithmetic (Python's float and math.fma), so on every operating system. The CI
#   runs them in generator.yml, inside the generator's whole suite.
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
if(EXISTS "${PROJECT_SOURCE_DIR}/gen/kairn-gen")
  set(_args "")
  foreach(_pattern IN LISTS _gen_full)
    list(APPEND _args -k "${_pattern}")
  endforeach()
  add_test(NAME full.kairn-gen.test
    COMMAND "${Python3_EXECUTABLE}" gen/kairn-gen test --no-cxx ${_args}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.kairn-gen.test PROPERTIES TIMEOUT 600 PROCESSORS 4
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

# --- The cross-checks ---------------------------------------------------------------------------
#
# Kernel by kernel, as tests/CMakeLists.txt worked them out: the interpreter on every operand of
# the kernel's toy format, or of a restricted domain of it and on random cases of all of it; and
# every compiled runner on KAIRN_CROSSCHECK_CASES cases of each format.
set(_summaries "${CMAKE_CURRENT_BINARY_DIR}/crosscheck")
foreach(_kernel IN LISTS _full_kernels)
  set(_this ${_full_${_kernel}_this})
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
  if(_restrict AND NOT _error)
    set(_name full.crosscheck.interp-sampled.${_kernel})
    add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_toy}"
      -DRUNNER=interp ${_random} "-DSUMMARY=${_summaries}/${_name}.json" -P "${_driver}")
    set_tests_properties(${_name} PROPERTIES TIMEOUT 300
      LABELS "full;python;crosscheck;interp;sampled")
  endif()

  if(_compiled)
    foreach(_format binary64 binary32)
      set(_name full.crosscheck.compiled.${_kernel}.${_format})
      add_test(NAME ${_name} COMMAND "${CMAKE_COMMAND}" ${_this} "-DFORMAT=${_format}"
        "-DRUNNERS=${_compiled}" ${_random} "-DSUMMARY=${_summaries}/${_name}.json"
        -P "${_driver}")
      set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;crosscheck;compiled")
    endforeach()
  endif()
endforeach()

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
      --fail-on-suspicious --suspicious-ok split,two_prod_dekker
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}")
  set_tests_properties(full.search.compiled PROPERTIES TIMEOUT 600 PROCESSORS 4
    LABELS "full;search")
endif()
# --- The adversarial search (end) ---------------------------------------------------------------

# --- The public interface against the oracle ----------------------------------------------------
#
# Every public form of every kernel api/CMakeLists.txt maps, with both of its runners, on
# KAIRN_API_CASES cases (the quick tier has KAIRN_API_QUICK_CASES of the same seed).
foreach(_kernel IN LISTS _api_oracle_kernels)
  foreach(_format binary64 binary32)
    set(_name full.api.oracle.${_kernel}.${_format})
    add_test(NAME ${_name}
      COMMAND "${CMAKE_COMMAND}" ${_api_oracle_common} "-DKERNEL=${_kernel}" "-DFORMAT=${_format}"
        "-DCOUNT=${KAIRN_API_CASES}" "-DSUMMARY_DIR=${CMAKE_CURRENT_BINARY_DIR}/api-oracle"
        -P "${PROJECT_SOURCE_DIR}/tests/api/pipeline.cmake")
    set_tests_properties(${_name} PROPERTIES TIMEOUT 600 LABELS "full;api;oracle")
  endforeach()
endforeach()
