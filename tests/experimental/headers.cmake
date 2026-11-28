# experimental.headers (tests/experimental/CMakeLists.txt): what keeps the experimental headers,
# EXPERIMENTAL and NOT VERIFIED, from being taken for proved code, read from the tree itself. Fails,
# naming every file at fault, when
#
# 1. a header of include/kairn/experimental/ does not start with the banner, "// EXPERIMENTAL, NOT
#    VERIFIED: no bound stated in this file is proved.", or its first preprocessor line is not the
#    guard "#if !defined(KAIRN_EXPERIMENTAL_UNVERIFIED)" followed by an #error that names it;
# 2. a header of include/kairn/ outside experimental/ includes an experimental one (kairn/kairn.hpp
#    and kairn/upward.hpp among them), or any file of the library or of its CMake package defines
#    KAIRN_EXPERIMENTAL_UNVERIFIED, which is the client's to define;
# 3. a header that a client would include stays under experiments/: there, kairn/experimental/
#    holds the forms kept for the measurements only (NAME_forms.hpp), and every other header belongs
#    in include/kairn/experimental/, with the banner;
# 4. the claims (gen/claims.json), from which the proof markers and the reference pages are made,
#    or a reference page (docs/reference/), name the experimental headers or their namespace.
#
#   cmake -DSOURCE_DIR=<the repository> -P headers.cmake
cmake_minimum_required(VERSION 3.21)

if(NOT DEFINED SOURCE_DIR)
  message(FATAL_ERROR "headers.cmake: SOURCE_DIR is not set")
endif()
set(_faults "")

# 1. The banner and the guard.
file(GLOB _headers LIST_DIRECTORIES false "${SOURCE_DIR}/include/kairn/experimental/*")
if(NOT _headers)
  list(APPEND _faults "include/kairn/experimental/ holds no header")
endif()
set(_banner "// EXPERIMENTAL, NOT VERIFIED: no bound stated in this file is proved.")
string(LENGTH "${_banner}" _banner_length)
foreach(_path IN LISTS _headers)
  get_filename_component(_name "${_path}" NAME)
  file(READ "${_path}" _text)
  string(REPLACE "\r\n" "\n" _text "${_text}")
  string(SUBSTRING "${_text}" 0 ${_banner_length} _start)
  if(NOT _start STREQUAL _banner)
    list(APPEND _faults "include/kairn/experimental/${_name} does not start with the banner '${_banner}'")
  endif()
  string(REGEX MATCH "\n#[^\n]*\n#[^\n]*" _guard "${_text}")
  set(_expected "\n#if !defined(KAIRN_EXPERIMENTAL_UNVERIFIED)\n#error \"kairn/experimental/${_name} is EXPERIMENTAL and NOT VERIFIED")
  string(FIND "${_guard}" "${_expected}" _at)
  if(NOT _at EQUAL 0)
    list(APPEND _faults "include/kairn/experimental/${_name}: its first preprocessor lines are not the guard "
      "'#if !defined(KAIRN_EXPERIMENTAL_UNVERIFIED)' and an #error that names it")
  endif()
endforeach()

# 2. Nothing of the library includes an experimental header or opts in for the client.
file(GLOB_RECURSE _library LIST_DIRECTORIES false "${SOURCE_DIR}/include/kairn/*")
foreach(_path IN LISTS _library)
  file(RELATIVE_PATH _rel "${SOURCE_DIR}" "${_path}")
  if(NOT _rel MATCHES "^include/kairn/experimental/")
    file(STRINGS "${_path}" _lines REGEX "#[ \t]*include[ \t]*[<\"]kairn/experimental/")
    if(_lines)
      list(APPEND _faults "${_rel} includes an experimental header: ${_lines}")
    endif()
  endif()
  file(STRINGS "${_path}" _lines REGEX "#[ \t]*define[ \t]+KAIRN_EXPERIMENTAL_UNVERIFIED")
  if(_lines)
    list(APPEND _faults "${_rel} defines KAIRN_EXPERIMENTAL_UNVERIFIED, which only a client may define")
  endif()
endforeach()
file(GLOB _package LIST_DIRECTORIES false "${SOURCE_DIR}/cmake/*")
foreach(_path IN LISTS _package ITEMS "${SOURCE_DIR}/CMakeLists.txt")
  file(RELATIVE_PATH _rel "${SOURCE_DIR}" "${_path}")
  file(STRINGS "${_path}" _lines REGEX "KAIRN_EXPERIMENTAL_UNVERIFIED")
  if(_lines)
    list(APPEND _faults "${_rel} names KAIRN_EXPERIMENTAL_UNVERIFIED: a target of Kairn's would opt in for its clients")
  endif()
endforeach()

# 3. Under experiments/, only the forms of the measurements.
file(GLOB _left LIST_DIRECTORIES false "${SOURCE_DIR}/experiments/*/include/kairn/experimental/*")
foreach(_path IN LISTS _left)
  file(RELATIVE_PATH _rel "${SOURCE_DIR}" "${_path}")
  get_filename_component(_name "${_path}" NAME)
  if(NOT _name MATCHES "_forms\\.hpp$")
    list(APPEND _faults "${_rel} is not a form of the measurements (NAME_forms.hpp): a header that a client "
      "includes belongs in include/kairn/experimental/${_name}, with the banner and the guard")
  endif()
endforeach()

# 4. Neither the claims nor the reference pages name them.
file(GLOB_RECURSE _claimed LIST_DIRECTORIES false "${SOURCE_DIR}/docs/reference/*.md")
foreach(_path IN LISTS _claimed ITEMS "${SOURCE_DIR}/gen/claims.json")
  file(RELATIVE_PATH _rel "${SOURCE_DIR}" "${_path}")
  file(STRINGS "${_path}" _lines REGEX "kairn(/|::)experimental|upward[24](_arrays)?\\.hpp")
  if(_lines)
    list(APPEND _faults "${_rel} names an experimental header or its namespace, which no claim covers")
  endif()
endforeach()

if(_faults)
  list(JOIN _faults "\n  " _text)
  message(FATAL_ERROR "the experimental headers are not kept apart from the proved code:\n  ${_text}")
endif()
list(LENGTH _headers _n)
message(STATUS "the ${_n} experimental headers start with the banner and the guard; nothing of the "
  "library includes them or opts in; experiments/ holds only the forms of the measurements; no claim "
  "and no reference page names them")
