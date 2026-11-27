// The program kairn-bench-up-LEVEL (bench/up_data.hpp) is the driver of Milestone 2 (m2_main.cpp)
// with the units of the first part of that benchmark and the units of the round-up interval: the
// tables of the second and third parts of kairn-bench-m2-LEVEL, which it does not build, are empty
// here, and so are the JSON summaries of their bisections and ball vectors.
#include <string>

#include "m2_data.hpp"

namespace kairn_bench::m2 {

namespace {
constexpr Entry kNone[] = {{nullptr, nullptr, 0, 0, 0, 0, 0, nullptr}};
}

const Entry m2_soa_entries[] = {kNone[0]};
const Entry m2_soa_scalar_entries[] = {kNone[0]};
const Entry m2_enc_entries[] = {kNone[0]};
const Entry m2_run_entries[] = {kNone[0]};
const Entry m2_batch_entries[] = {kNone[0]};
const Entry m2_bv_entries[] = {kNone[0]};
const Entry m2_bvs_entries[] = {kNone[0]};

std::string m2_run_json() { return "[]"; }
std::string m2_bv_widths_json() { return "[]"; }

}  // namespace kairn_bench::m2
