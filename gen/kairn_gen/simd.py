"""The packed printers: include/kairn/gen/avx2.hpp and neon.hpp, one number per lane.

Each kernel becomes one function per limb type that computes, in every lane, what the scalar
kernel of cpp.py computes for that lane's operands, bit for bit. The rules are those of the
scalar printer (calls inlined, one operation per statement, force-inlined up to two limbs), and
for the same reasons: raw intrinsics are contracted by the same compilers under the same flags
(docs/developer/design/phase0/environment.md), so a rounded product is again an FMA with a +0
addend and nothing else is multiplied. A mask is a lane mask (every bit of a lane set or clear),
select a blend, and succ and pred step the bit pattern with integer lane operations, as the
scalar next_up does. Nothing here is constexpr: intrinsics are not constant expressions.

Each backend is a table of spellings and a few helpers; the loop over the statements is shared.
{s} is the floating-point suffix of the intrinsics, {u} the integer one of masks, {f} the suffix
of a literal of the limb type.
"""
from . import cpp, ir

AVX2 = {
    'file': 'avx2.hpp',
    'what': 'AVX2 with FMA: 4 doubles or 8 floats per register',
    'include': '<immintrin.h>',
    'guard': [
        '#if defined(_MSC_VER) && !defined(__clang__)',
        '#if !defined(__AVX2__)',
        '#error "kairn/gen/avx2.hpp needs AVX2 and FMA: compile with /arch:AVX2 or later"',
        '#endif',
        '#elif !defined(__AVX2__) || !defined(__FMA__)',
        '#error "kairn/gen/avx2.hpp needs AVX2 and FMA: compile with -mavx2 -mfma, or -march=haswell or later"',
        '#endif'],
    # limb type: vector type, mask type, intrinsic suffix, mask suffix, lanes
    'types': {'double': ('__m256d', '__m256d', 'pd', 'pd', 4), 'float': ('__m256', '__m256', 'ps', 'ps', 8)},
    'set1': '_mm256_set1_{s}({0})',
    'zero': '_mm256_setzero_{s}()',
    'spell': {
        'add': '_mm256_add_{s}({0}, {1})',
        'sub': '_mm256_sub_{s}({0}, {1})',
        'neg': '_mm256_xor_{s}({0}, _mm256_set1_{s}(-0.0{f}))',        # flips the sign bit
        'abs': '_mm256_andnot_{s}(_mm256_set1_{s}(-0.0{f}), {0})',     # clears it
        'fma': '_mm256_fmadd_{s}({0}, {1}, {2})',
        'fms': '_mm256_fmsub_{s}({0}, {1}, {2})',
        'fnma': '_mm256_fnmadd_{s}({0}, {1}, {2})',
        'prod': '_mm256_fmadd_{s}({0}, {1}, _mm256_setzero_{s}())',  # the opaque product
        'muladd': '_mm256_add_{s}(_mm256_mul_{s}({0}, {1}), {2})',   # the compiler may fuse it
        'lt': '_mm256_cmp_{s}({0}, {1}, _CMP_LT_OQ)',                 # false on NaN, as < is
        'le': '_mm256_cmp_{s}({0}, {1}, _CMP_LE_OQ)',
        'eq': '_mm256_cmp_{s}({0}, {1}, _CMP_EQ_OQ)',
        'and': '_mm256_and_{u}({0}, {1})',
        'or': '_mm256_or_{u}({0}, {1})',
        'not': 'not_mask({0})',
        'select': '_mm256_blendv_{s}({2}, {1}, {0})',               # {1} where the mask is set
        'succ': 'next_up({0})',
        'pred': 'next_down({0})',
        'copy': '{0}',
    },
}

NEON = {
    'file': 'neon.hpp',
    'what': 'AArch64 Advanced SIMD: 2 doubles or 4 floats per register',
    'include': '<arm_neon.h>',
    'guard': [
        '#if !defined(__aarch64__) && !defined(_M_ARM64)',
        '#error "kairn/gen/neon.hpp needs AArch64 (Advanced SIMD with double-precision lanes)"',
        '#endif'],
    'types': {'double': ('float64x2_t', 'uint64x2_t', 'f64', 'u64', 2),
              'float': ('float32x4_t', 'uint32x4_t', 'f32', 'u32', 4)},
    'set1': 'vdupq_n_{s}({0})',
    'zero': 'vdupq_n_{s}(0.0{f})',
    'spell': {
        'add': 'vaddq_{s}({0}, {1})',
        'sub': 'vsubq_{s}({0}, {1})',
        'neg': 'vnegq_{s}({0})',
        'abs': 'vabsq_{s}({0})',
        'fma': 'vfmaq_{s}({2}, {0}, {1})',                 # {2} + {0} {1}, one rounding
        'fms': 'vfmaq_{s}(vnegq_{s}({2}), {0}, {1})',      # -{2} + {0} {1}: fma_rn(a, b, -c)
        'fnma': 'vfmsq_{s}({2}, {0}, {1})',                # {2} - {0} {1}: fma_rn(-a, b, c)
        'prod': 'vfmaq_{s}(vdupq_n_{s}(0.0{f}), {0}, {1})',  # the opaque product
        'muladd': 'vaddq_{s}(vmulq_{s}({0}, {1}), {2})',   # the compiler may fuse it
        'lt': 'vcltq_{s}({0}, {1})',
        'le': 'vcleq_{s}({0}, {1})',
        'eq': 'vceqq_{s}({0}, {1})',
        'and': 'vandq_{u}({0}, {1})',
        'or': 'vorrq_{u}({0}, {1})',
        'not': 'not_mask({0})',
        'select': 'vbslq_{s}({0}, {1}, {2})',              # bits of {1} where the mask is set
        'succ': 'next_up({0})',
        'pred': 'next_down({0})',
        'copy': '{0}',
    },
}

BACKENDS = (AVX2, NEON)

# Names the helpers take, on top of the scalar printer's.
RESERVED = frozenset({'not_mask', 'next_up', 'next_down'})

# The helpers: the complement of a lane mask, and nextUp / nextDown lane by lane, written as the
# scalar next_up (cpp.py) is: the pattern of a positive lane moves up and that of a negative one
# towards zero, either zero becomes the smallest subnormal, NaN and +inf stay.
_AVX2_HELPERS = '''\
KAIRN_GEN_FORCEINLINE __m256d not_mask(__m256d m) noexcept {
    return _mm256_xor_pd(m, _mm256_castsi256_pd(_mm256_set1_epi64x(-1)));
}
KAIRN_GEN_FORCEINLINE __m256 not_mask(__m256 m) noexcept {
    return _mm256_xor_ps(m, _mm256_castsi256_ps(_mm256_set1_epi32(-1)));
}
KAIRN_GEN_FORCEINLINE __m256d next_up(__m256d a) noexcept {
    const __m256i b = _mm256_castpd_si256(a);
    const __m256i m = _mm256_and_si256(b, _mm256_set1_epi64x(0x7fffffffffffffffLL));
    const __m256i inf = _mm256_set1_epi64x(0x7ff0000000000000LL);
    const __m256i one = _mm256_set1_epi64x(1);
    // m and inf have a clear sign bit, so the signed comparison is the unsigned one.
    const __m256i keep = _mm256_or_si256(_mm256_cmpgt_epi64(m, inf), _mm256_cmpeq_epi64(b, inf));
    const __m256i zero = _mm256_cmpeq_epi64(m, _mm256_setzero_si256());
    const __m256i step = _mm256_or_si256(_mm256_cmpgt_epi64(_mm256_setzero_si256(), b), one);  // -1 or +1
    const __m256i r = _mm256_blendv_epi8(_mm256_add_epi64(b, step), one, zero);
    return _mm256_castsi256_pd(_mm256_blendv_epi8(r, b, keep));
}
KAIRN_GEN_FORCEINLINE __m256 next_up(__m256 a) noexcept {
    const __m256i b = _mm256_castps_si256(a);
    const __m256i m = _mm256_and_si256(b, _mm256_set1_epi32(0x7fffffff));
    const __m256i inf = _mm256_set1_epi32(0x7f800000);
    const __m256i one = _mm256_set1_epi32(1);
    const __m256i keep = _mm256_or_si256(_mm256_cmpgt_epi32(m, inf), _mm256_cmpeq_epi32(b, inf));
    const __m256i zero = _mm256_cmpeq_epi32(m, _mm256_setzero_si256());
    const __m256i step = _mm256_or_si256(_mm256_cmpgt_epi32(_mm256_setzero_si256(), b), one);
    const __m256i r = _mm256_blendv_epi8(_mm256_add_epi32(b, step), one, zero);
    return _mm256_castsi256_ps(_mm256_blendv_epi8(r, b, keep));
}
KAIRN_GEN_FORCEINLINE __m256d next_down(__m256d a) noexcept {
    const __m256d sign = _mm256_set1_pd(-0.0);
    return _mm256_xor_pd(next_up(_mm256_xor_pd(a, sign)), sign);
}
KAIRN_GEN_FORCEINLINE __m256 next_down(__m256 a) noexcept {
    const __m256 sign = _mm256_set1_ps(-0.0f);
    return _mm256_xor_ps(next_up(_mm256_xor_ps(a, sign)), sign);
}
'''

_NEON_HELPERS = '''\
KAIRN_GEN_FORCEINLINE uint64x2_t not_mask(uint64x2_t m) noexcept {
    return vreinterpretq_u64_u32(vmvnq_u32(vreinterpretq_u32_u64(m)));   // there is no vmvnq_u64
}
KAIRN_GEN_FORCEINLINE uint32x4_t not_mask(uint32x4_t m) noexcept { return vmvnq_u32(m); }
KAIRN_GEN_FORCEINLINE float64x2_t next_up(float64x2_t a) noexcept {
    const uint64x2_t b = vreinterpretq_u64_f64(a);
    const uint64x2_t m = vandq_u64(b, vdupq_n_u64(0x7fffffffffffffffu));
    const uint64x2_t inf = vdupq_n_u64(0x7ff0000000000000u);
    const uint64x2_t one = vdupq_n_u64(1);
    const uint64x2_t keep = vorrq_u64(vcgtq_u64(m, inf), vceqq_u64(b, inf));
    const uint64x2_t step = vbslq_u64(vceqq_u64(b, m), vaddq_u64(b, one), vsubq_u64(b, one));
    const uint64x2_t r = vbslq_u64(vceqq_u64(m, vdupq_n_u64(0)), one, step);
    return vreinterpretq_f64_u64(vbslq_u64(keep, b, r));
}
KAIRN_GEN_FORCEINLINE float32x4_t next_up(float32x4_t a) noexcept {
    const uint32x4_t b = vreinterpretq_u32_f32(a);
    const uint32x4_t m = vandq_u32(b, vdupq_n_u32(0x7fffffffu));
    const uint32x4_t inf = vdupq_n_u32(0x7f800000u);
    const uint32x4_t one = vdupq_n_u32(1);
    const uint32x4_t keep = vorrq_u32(vcgtq_u32(m, inf), vceqq_u32(b, inf));
    const uint32x4_t step = vbslq_u32(vceqq_u32(b, m), vaddq_u32(b, one), vsubq_u32(b, one));
    const uint32x4_t r = vbslq_u32(vceqq_u32(m, vdupq_n_u32(0)), one, step);
    return vreinterpretq_f32_u32(vbslq_u32(keep, b, r));
}
KAIRN_GEN_FORCEINLINE float64x2_t next_down(float64x2_t a) noexcept { return vnegq_f64(next_up(vnegq_f64(a))); }
KAIRN_GEN_FORCEINLINE float32x4_t next_down(float32x4_t a) noexcept { return vnegq_f32(next_up(vnegq_f32(a))); }
'''

HELPERS = {'avx2.hpp': _AVX2_HELPERS, 'neon.hpp': _NEON_HELPERS}


def _operand(a, b, kernels, ctype, fmt):
    if not a.const:
        return a.name
    if a.name == ir.ZERO:
        return b['zero'].format(**fmt)
    return b['set1'].format(cpp.literal(a.name, kernels, ctype), **fmt)


def function(b, k, kernels, ctype):
    cpp._check_names(k, kernels)
    vec, mask, s, u, _ = b['types'][ctype]
    fmt = {'s': s, 'u': u, 'f': cpp.TYPES[ctype][1]}
    inline = 'KAIRN_GEN_FORCEINLINE' if k.limbs <= 2 else 'inline'
    lines = [f'{inline} void {k.name}({", ".join(cpp.parameters(k, vec, mask))}) noexcept {{']
    for it in ir.flatten(k, kernels):
        if isinstance(it, ir.CallMark):
            lines.append(f'    // ({", ".join(it.dsts)}) = {it.callee}({", ".join(map(str, it.args))})')
            continue
        args = [_operand(a, b, kernels, ctype, fmt) for a in it.args]
        vtype = vec if ir.OPS[it.op][1] == ir.LIMB else mask
        lines.append(f'    const {vtype} {it.dst} = {b["spell"][it.op].format(*args, **fmt)};')
    lines += [f'    {v}_out = {v};' for v in k.output_limbs]
    lines.append('}')
    return lines


HEADER = ('// Generated by gen/kairn-gen from gen/kernels/*.kernel. Do not edit: change the\n'
          '// descriptions or gen/kairn_gen/simd.py, then run python3 gen/kairn-gen build.')


def header(b, kernels, prelude_name='prelude.hpp'):
    lines = [HEADER, '//',
             f'// Packed kernels for {b["what"]}.',
             '// One number per lane (docs/developer/architecture.md, "The kernel IR"): in every lane a',
             '// kernel gives, bit for bit, what the scalar kernel of scalar.hpp gives for that lane\'s',
             '// operands. A mask is a lane mask: every bit of a lane set, or every bit clear.',
             '#pragma once', ''] + b['guard'] + [
             '',
             f'#include {b["include"]}', '',
             f'#include "{prelude_name}"', '',
             'namespace kairn::gen {', '',
             '// The complement of a lane mask, and IEEE 754 nextUp and nextDown in every lane by',
             '// stepping the bit pattern, as next_up of prelude.hpp does for one number.',
             HELPERS[b['file']].rstrip('\n')]
    for k in kernels.values():
        lines += [''] + cpp._description(k, kernels)[:1]
        for ctype in cpp.TYPES:
            lines += function(b, k, kernels, ctype)
    lines += ['', '}  // namespace kairn::gen']
    return '\n'.join(lines) + '\n'
