// The table of gen/tests/packed_runner.cpp built with lane_fault.hpp (KAIRN_RUNNER_TABLE): one
// kernel, under the name of the generated one, so that the oracle's requests of mul_2_2_full go
// to the planted copy.
KAIRN_RUNNER_KERNEL(mul_2_2_full, "llll", "ll", kairn_lane_fault::mul_2_2_full(in[0], in[1], in[2], in[3], out[0], out[1]))
