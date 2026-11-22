// The packed loops of m2_soa.cpp in the scalar form of Packed, one lane (KAIRN_PACKED_FORM_SCALAR,
// include/kairn/packed.hpp), compiled with the same flags as m2_soa.cpp: backends m2v1 and m2vf1,
// checked against m2v and m2vf, on the arrays of m2_soa.cpp. A program may link translation units of
// different forms: each form of Packed is in an inline namespace of its own.
#define KAIRN_PACKED_FORM KAIRN_PACKED_FORM_SCALAR
#define KB_SOA_SCALAR_FORM 1
#include "m2_soa.cpp"
