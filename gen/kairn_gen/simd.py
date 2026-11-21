"""The packed printers: include/kairn/gen/avx2.hpp and neon.hpp, one number per lane.

Each kernel becomes one function per limb type that computes, in every lane, what the scalar
kernel of cpp.py computes for that lane's operands, bit for bit. The rules are those of the
scalar printer (calls inlined, one operation per statement, force-inlined up to two limbs but for
`ordinary_inline:`), and for the same reasons: raw intrinsics are contracted by the same compilers under the same flags
(docs/developer/design/phase0/environment.md), so a rounded product is again an FMA with a +0
addend and nothing else is multiplied. A mask is a lane mask (every bit of a lane set or clear),
select a blend, and succ and pred step the bit pattern with integer lane operations, as the
scalar next_up_bits does. Nothing here is constexpr: intrinsics are not constant expressions.

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
    'load': '_mm256_loadu_{s}({0})',          # the lanes of a register from memory (a fold's loop)
    'store': '_mm256_storeu_{s}({0}, {1})',
    # Whether every lane of a mask is set (a map's mask, at the end of its packed loop).
    'all': {'double': '_mm256_movemask_pd({0}) == 0xF', 'float': '_mm256_movemask_ps({0}) == 0xFF'},
    # The lanes of a mask of a fold's state, stored and read one by one (a fold of maxima): the
    # declaration of the store (none: the bits are an int), the store, and lane {1} as a bool.
    'mask_decl': {'double': None, 'float': None},
    'mask_store': {'double': 'const int {0} = _mm256_movemask_pd({1})', 'float': 'const int {0} = _mm256_movemask_ps({1})'},
    'mask_lane': {'double': '(({0} >> {1}) & 1) != 0', 'float': '(({0} >> {1}) & 1) != 0'},
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
        'succ': 'next_up_bits({0})',
        'pred': 'next_down_bits({0})',
        'copy': '{0}',
        'guard': '_mm256_add_{s}({0}, _mm256_setzero_{s}())',      # RN(a + 0), with a zero vector
        'times_inf': '_mm256_mul_{s}({0}, _mm256_set1_{s}({inf}))',  # exact; only compared or selected
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
    'load': 'vld1q_{s}({0})',
    'store': 'vst1q_{s}({0}, {1})',
    'all': {'double': 'vminvq_u32(vreinterpretq_u32_u64({0})) != 0U', 'float': 'vminvq_u32({0}) != 0U'},
    'mask_decl': {'double': 'uint64_t {0}[2]', 'float': 'uint32_t {0}[4]'},
    'mask_store': {'double': 'vst1q_u64({0}, {1})', 'float': 'vst1q_u32({0}, {1})'},
    'mask_lane': {'double': '{0}[{1}] != 0U', 'float': '{0}[{1}] != 0U'},
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
        'succ': 'next_up_bits({0})',
        'pred': 'next_down_bits({0})',
        'copy': '{0}',
        'guard': 'vaddq_{s}({0}, vdupq_n_{s}(0.0{f}))',             # RN(a + 0), with a zero vector
        'times_inf': 'vmulq_{s}({0}, vdupq_n_{s}({inf}))',          # exact; only compared or selected
    },
}

BACKENDS = (AVX2, NEON)

# Names the helpers take, on top of the scalar printer's.
RESERVED = frozenset({'not_mask', 'next_up_bits', 'next_down_bits'})

# The helpers: the complement of a lane mask, and nextUp / nextDown lane by lane, written as the
# scalar next_up_bits and next_down_bits (cpp.py) are: for nextUp the pattern of a positive lane
# moves up and that of a negative one towards zero, either zero becomes the smallest subnormal, NaN
# and +inf stay; nextDown the same on the other side, without a negation of the value.
_AVX2_HELPERS = '''\
KAIRN_GEN_FORCEINLINE __m256d not_mask(__m256d m) noexcept {
    return _mm256_xor_pd(m, _mm256_castsi256_pd(_mm256_set1_epi64x(-1)));
}
KAIRN_GEN_FORCEINLINE __m256 not_mask(__m256 m) noexcept {
    return _mm256_xor_ps(m, _mm256_castsi256_ps(_mm256_set1_epi32(-1)));
}
KAIRN_GEN_FORCEINLINE __m256d next_up_bits(__m256d a) noexcept {
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
KAIRN_GEN_FORCEINLINE __m256 next_up_bits(__m256 a) noexcept {
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
// nextDown, with no sign flip of a floating-point value, which a compiler can fold into an FMA
// that computes the operand: a positive lane moves towards zero, a negative one down, either zero
// becomes -eta (0x8000...01), NaN and -inf (0xfff0...0) stay.
KAIRN_GEN_FORCEINLINE __m256d next_down_bits(__m256d a) noexcept {
    const __m256i b = _mm256_castpd_si256(a);
    const __m256i m = _mm256_and_si256(b, _mm256_set1_epi64x(0x7fffffffffffffffLL));
    const __m256i inf = _mm256_set1_epi64x(0x7ff0000000000000LL);
    const __m256i one = _mm256_set1_epi64x(1);
    const __m256i keep = _mm256_or_si256(_mm256_cmpgt_epi64(m, inf),
                                         _mm256_cmpeq_epi64(b, _mm256_set1_epi64x(-0x10000000000000LL)));
    const __m256i zero = _mm256_cmpeq_epi64(m, _mm256_setzero_si256());
    const __m256i step = _mm256_or_si256(_mm256_cmpgt_epi64(_mm256_setzero_si256(), b), one);  // -1 or +1
    const __m256i r = _mm256_blendv_epi8(_mm256_sub_epi64(b, step), _mm256_set1_epi64x(-0x7fffffffffffffffLL), zero);
    return _mm256_castsi256_pd(_mm256_blendv_epi8(r, b, keep));
}
KAIRN_GEN_FORCEINLINE __m256 next_down_bits(__m256 a) noexcept {
    const __m256i b = _mm256_castps_si256(a);
    const __m256i m = _mm256_and_si256(b, _mm256_set1_epi32(0x7fffffff));
    const __m256i inf = _mm256_set1_epi32(0x7f800000);
    const __m256i one = _mm256_set1_epi32(1);
    const __m256i keep = _mm256_or_si256(_mm256_cmpgt_epi32(m, inf), _mm256_cmpeq_epi32(b, _mm256_set1_epi32(-0x800000)));
    const __m256i zero = _mm256_cmpeq_epi32(m, _mm256_setzero_si256());
    const __m256i step = _mm256_or_si256(_mm256_cmpgt_epi32(_mm256_setzero_si256(), b), one);
    const __m256i r = _mm256_blendv_epi8(_mm256_sub_epi32(b, step), _mm256_set1_epi32(-0x7fffffff), zero);
    return _mm256_castsi256_ps(_mm256_blendv_epi8(r, b, keep));
}
'''

_NEON_HELPERS = '''\
KAIRN_GEN_FORCEINLINE uint64x2_t not_mask(uint64x2_t m) noexcept {
    return vreinterpretq_u64_u32(vmvnq_u32(vreinterpretq_u32_u64(m)));   // there is no vmvnq_u64
}
KAIRN_GEN_FORCEINLINE uint32x4_t not_mask(uint32x4_t m) noexcept { return vmvnq_u32(m); }
KAIRN_GEN_FORCEINLINE float64x2_t next_up_bits(float64x2_t a) noexcept {
    const uint64x2_t b = vreinterpretq_u64_f64(a);
    const uint64x2_t m = vandq_u64(b, vdupq_n_u64(0x7fffffffffffffffu));
    const uint64x2_t inf = vdupq_n_u64(0x7ff0000000000000u);
    const uint64x2_t one = vdupq_n_u64(1);
    const uint64x2_t keep = vorrq_u64(vcgtq_u64(m, inf), vceqq_u64(b, inf));
    const uint64x2_t step = vbslq_u64(vceqq_u64(b, m), vaddq_u64(b, one), vsubq_u64(b, one));
    const uint64x2_t r = vbslq_u64(vceqq_u64(m, vdupq_n_u64(0)), one, step);
    return vreinterpretq_f64_u64(vbslq_u64(keep, b, r));
}
KAIRN_GEN_FORCEINLINE float32x4_t next_up_bits(float32x4_t a) noexcept {
    const uint32x4_t b = vreinterpretq_u32_f32(a);
    const uint32x4_t m = vandq_u32(b, vdupq_n_u32(0x7fffffffu));
    const uint32x4_t inf = vdupq_n_u32(0x7f800000u);
    const uint32x4_t one = vdupq_n_u32(1);
    const uint32x4_t keep = vorrq_u32(vcgtq_u32(m, inf), vceqq_u32(b, inf));
    const uint32x4_t step = vbslq_u32(vceqq_u32(b, m), vaddq_u32(b, one), vsubq_u32(b, one));
    const uint32x4_t r = vbslq_u32(vceqq_u32(m, vdupq_n_u32(0)), one, step);
    return vreinterpretq_f32_u32(vbslq_u32(keep, b, r));
}
// nextDown, with no negation of a floating-point value, which a compiler can fold into an FMA
// that computes the operand: a positive lane moves towards zero, a negative one down, either zero
// becomes -eta (0x8000...01), NaN and -inf (0xfff0...0) stay.
KAIRN_GEN_FORCEINLINE float64x2_t next_down_bits(float64x2_t a) noexcept {
    const uint64x2_t b = vreinterpretq_u64_f64(a);
    const uint64x2_t m = vandq_u64(b, vdupq_n_u64(0x7fffffffffffffffu));
    const uint64x2_t inf = vdupq_n_u64(0x7ff0000000000000u);
    const uint64x2_t one = vdupq_n_u64(1);
    const uint64x2_t keep = vorrq_u64(vcgtq_u64(m, inf), vceqq_u64(b, vdupq_n_u64(0xfff0000000000000u)));
    const uint64x2_t step = vbslq_u64(vceqq_u64(b, m), vsubq_u64(b, one), vaddq_u64(b, one));
    const uint64x2_t r = vbslq_u64(vceqq_u64(m, vdupq_n_u64(0)), vdupq_n_u64(0x8000000000000001u), step);
    return vreinterpretq_f64_u64(vbslq_u64(keep, b, r));
}
KAIRN_GEN_FORCEINLINE float32x4_t next_down_bits(float32x4_t a) noexcept {
    const uint32x4_t b = vreinterpretq_u32_f32(a);
    const uint32x4_t m = vandq_u32(b, vdupq_n_u32(0x7fffffffu));
    const uint32x4_t inf = vdupq_n_u32(0x7f800000u);
    const uint32x4_t one = vdupq_n_u32(1);
    const uint32x4_t keep = vorrq_u32(vcgtq_u32(m, inf), vceqq_u32(b, vdupq_n_u32(0xff800000u)));
    const uint32x4_t step = vbslq_u32(vceqq_u32(b, m), vsubq_u32(b, one), vaddq_u32(b, one));
    const uint32x4_t r = vbslq_u32(vceqq_u32(m, vdupq_n_u32(0)), vdupq_n_u32(0x80000001u), step);
    return vreinterpretq_f32_u32(vbslq_u32(keep, b, r));
}
'''

HELPERS = {'avx2.hpp': _AVX2_HELPERS, 'neon.hpp': _NEON_HELPERS}


def _operand(a, b, kernels, ctype, fmt):
    if not a.const:
        return a.name
    if a.name == ir.ZERO:
        return b['zero'].format(**fmt)
    return b['set1'].format(cpp.literal(a.name, kernels, ctype), **fmt)


def _format(b, kernels, ctype):
    _, _, s, u, _ = b['types'][ctype]
    return {'s': s, 'u': u, 'f': cpp.TYPES[ctype][1], 'inf': cpp.literal('inf', kernels, ctype)}


def _statements(b, items, kernels, ctype, pad):
    vec, mask, _, _, _ = b['types'][ctype]
    fmt = _format(b, kernels, ctype)
    lines = []
    for it in items:
        if isinstance(it, ir.CallMark):
            lines.append(f'{pad}// ({", ".join(it.dsts)}) = {it.callee}({", ".join(map(str, it.args))})')
            continue
        args = [_operand(a, b, kernels, ctype, fmt) for a in it.args]
        vtype = vec if ir.OPS[it.op][1] == ir.LIMB else mask
        lines.append(f'{pad}const {vtype} {it.dst} = {b["spell"][it.op].format(*args, **fmt)};')
    return lines


def function(b, k, kernels, ctype):
    cpp._check_names(k, kernels)
    vec, mask, _, _, _ = b['types'][ctype]
    inline = 'KAIRN_GEN_FORCEINLINE' if k.forced_inline else 'inline'
    lines = [f'{inline} void {k.name}({", ".join(cpp.parameters(k, vec, mask))}) noexcept {{']
    lines += _statements(b, ir.flatten(k, kernels), kernels, ctype, '    ')
    lines += [f'    {v}_out = {v};' for v in k.output_limbs]
    lines.append('}')
    return lines


def fold_packed(b, fd, kernels, ctype):
    """The lane order of a fold (proofs/theories/Folds.v, fold_lanes) with W the lanes of the
    register: the first W (n / W) elements in blocks of W, element i in lane i mod W, each lane
    folded by the packed step from the zero state; the W lane states, stored, combined from lane 0
    upward by the scalar combination; the remaining elements folded into the result by the scalar
    step; the finish. In every lane the packed step computes what the scalar step computes, so
    this is, bit for bit, F_lanes of scalar.hpp with lanes = W."""
    vec, mask, _, _, w = b['types'][ctype]
    fmt = _format(b, kernels, ctype)
    step, combine, _ = cpp.fold_kernels(fd, kernels)
    state = fd.state_limbs()
    kinds = fd.state_kinds()
    lane = [f'{v}_lane_' for v in state]
    stored = [f'{v}_lanes_' for v in state]
    nxt = [f'{v}_next_' for v in state]
    zero = b['zero'].format(**fmt)
    lines = cpp.fold_description(fd, kernels, 'packed')
    lines.append(f'inline void {fd.name}_packed({", ".join(cpp.fold_parameters(fd, ctype, "bool", False, kernels))}) '
                 'noexcept {')
    lines.append(f'    const std::size_t full_ = n - n % {w};')
    # The zero state in every lane: +0, and a mask true (every bit set).
    lines += [f'    {mask} {v} = {b["spell"]["eq"].format(zero, zero, **fmt)};' if kind == ir.MASK else
              f'    {vec} {v} = {zero};' for v, kind in zip(lane, kinds)]
    lines.append(f'    for (std::size_t i_ = 0; i_ < full_; i_ += {w}) {{')
    lines += [f'        const {vec} {v} = {b["load"].format(f"{v}_in + i_", **fmt)};' for v in cpp.loaded_limbs(fd, kernels)]
    items, outs = ir.inline_call(step, kernels, [ir.Operand(a) for a in cpp.step_arguments(
        fd, lane, {g.name: list(g.limbs) for g in fd.arrays})], cpp.STEP)
    lines += _statements(b, items, kernels, ctype, ' ' * 8) + cpp._assign(lane, outs, ' ' * 8) + ['    }']
    # Not initialized: the store writes every lane before any is read. (An initializer `= {}` is a
    # call of memset at -O0 with Clang for 32 bytes, which the object-code check cannot count.) A
    # mask is stored as the bits of its lanes, one per lane (mask_store), and read as a bool.
    for v, kind in zip(stored, kinds):
        decl = b['mask_decl'][ctype] if kind == ir.MASK else f'{ctype} {{0}}[{w}]'
        if decl:
            lines.append(f'    {decl.format(v)};')
    lines += [f'    {(b["mask_store"][ctype] if kind == ir.MASK else b["store"]).format(v, r, **fmt)};'
              for v, r, kind in zip(stored, lane, kinds)]
    lines += [f'    bool {v} = {b["mask_lane"][ctype].format(r, "0")};' if kind == ir.MASK else
              f'    {ctype} {v} = {r}[0];' for v, r, kind in zip(state, stored, kinds)]
    lines.append(f'    for (std::size_t j_ = 1; j_ < {w}; ++j_) {{')
    lines += [f'        const bool {v} = {b["mask_lane"][ctype].format(r, "j_")};' if kind == ir.MASK else
              f'        const {ctype} {v} = {r}[j_];' for v, r, kind in zip(nxt, stored, kinds)]
    body, outs = cpp._call(combine, kernels, ctype, state + nxt, cpp.COMB, ' ' * 8)
    lines += body + cpp._assign(state, outs, ' ' * 8) + ['    }']
    lines += cpp.fold_step_loop(fd, kernels, ctype, state, 'full_')
    return lines + cpp.fold_finish_lines(fd, kernels, ctype, state) + ['}']


def map_packed(b, fd, kernels, ctype):
    """The lane order of a map with W the lanes of the register: the elements of the first
    W (n / W) in blocks of W, the packed step and the elements written; the packed check's flag
    and-ed into a lane mask, which is then the and of its lanes; the rest by the scalar step; the
    second pass of the scalar code. In every lane the packed step and check compute what the
    scalar ones compute, so the elements written and the mask are those of F_lanes with W lanes,
    and of F_seq."""
    vec, mask, _, _, w = b['types'][ctype]
    fmt = _format(b, kernels, ctype)
    step, check = kernels[fd.step[0]], kernels[fd.check]
    state = fd.state.limbs[0]
    lane = f'{state}_lane_'
    scalar = {v: f'{v}_v_' for v in fd.scalar_limbs()}
    lines = cpp.map_description(fd, kernels, 'packed')
    lines.append(f'inline void {fd.name}_packed({", ".join(cpp.map_parameters(fd, ctype, "bool", False))}) noexcept {{')
    lines.append(f'    const std::size_t full_ = n - n % {w};')
    zero = b['zero'].format(**fmt)
    lines += [f'    const {vec} {p} = {b["set1"].format(v, **fmt)};' for v, p in scalar.items()]
    lines.append(f'    {mask} {lane} = {b["spell"]["eq"].format(zero, zero, **fmt)};')
    lines.append(f'    for (std::size_t i_ = 0; i_ < full_; i_ += {w}) {{')
    lines += [f'        const {vec} {v} = {b["load"].format(f"{v}_in + i_", **fmt)};' for v in fd.array_limbs()]
    groups = {g.name: list(g.limbs) for g in fd.arrays}
    groups.update({g.name: [scalar[v] for v in g.limbs] for g in fd.scalars})
    args = [v for a in fd.step[1] for v in groups[a]]
    items, outs = ir.inline_call(step, kernels, [ir.Operand(a) for a in args], cpp.STEP)
    lines += _statements(b, items, kernels, ctype, ' ' * 8)
    lines += [f'        {b["store"].format(f"{v}_out + i_", o, **fmt)};' for v, o in zip(fd.write_limbs(), outs)]
    items, couts = ir.inline_call(check, kernels, [ir.Operand(o) for o in outs], cpp.CHECK)
    lines += _statements(b, cpp.needed(items, couts[-1:]), kernels, ctype, ' ' * 8)
    lines += [f'        {lane} = {b["spell"]["and"].format(lane, couts[-1], **fmt)};', '    }']
    lines.append(f'    bool {state} = {b["all"][ctype].format(lane)};')
    lines.append('    for (std::size_t i_ = full_; i_ < n; ++i_) {')
    lines += cpp.map_element(fd, kernels, ctype, 'bool', ' ' * 8, state) + ['    }']
    return lines + cpp.map_second_pass(fd, kernels, ctype) + ['}']


def bv_packed(b, fd, kernels, ctype):
    """The lane order of a ball vector with W the lanes of the register: the elements of the first
    W (n / W) in blocks of W, the packed step, the centers written, and the packed record on the W lane
    states, each from the zero state; the lane states stored and combined from lane 0 upward by the
    scalar combination; the rest by the scalar step and record; the radius, the finish and the second
    pass of the scalar code. In every lane the packed step and record compute what the scalar ones
    compute, so this is, bit for bit, F_lanes of scalar.hpp with lanes = W."""
    vec, mask, _, _, w = b['types'][ctype]
    fmt = _format(b, kernels, ctype)
    step, record, combine = (kernels[c[0]] for c in (fd.step, fd.record, fd.combine))
    state = fd.state_limbs()
    kinds = fd.state_kinds()
    lane = [f'{v}_lane_' for v in state]
    stored = [f'{v}_lanes_' for v in state]
    nxt = [f'{v}_next_' for v in state]
    zero = b['zero'].format(**fmt)
    scalar = {v: f'{v}_v_' for v in fd.scalar_limbs() if any(v in g.limbs for g in fd.scalars if g.name in fd.step[1])}
    lines = cpp.bv_description(fd, kernels, 'packed')
    lines.append(f'inline void {fd.name}_packed({", ".join(cpp.bv_parameters(fd, ctype, "bool", False))}) noexcept {{')
    lines.append(f'    const std::size_t full_ = n - n % {w};')
    lines += [f'    const {vec} {p} = {b["set1"].format(v, **fmt)};' for v, p in scalar.items()]
    lines += [f'    {mask} {v} = {b["spell"]["eq"].format(zero, zero, **fmt)};' if kind == ir.MASK else
              f'    {vec} {v} = {zero};' for v, kind in zip(lane, kinds)]
    lines.append(f'    for (std::size_t i_ = 0; i_ < full_; i_ += {w}) {{')
    lines += [f'        const {vec} {v} = {b["load"].format(f"{v}_in + i_", **fmt)};' for v in fd.array_limbs()]
    groups = {g.name: list(g.limbs) for g in fd.arrays}
    groups.update({g.name: [scalar[v] for v in g.limbs] for g in fd.scalars if g.name in fd.step[1]})
    args = [v for a in fd.step[1] for v in groups[a]]
    items, outs = ir.inline_call(step, kernels, [ir.Operand(a) for a in args], cpp.STEP)
    lines += _statements(b, items, kernels, ctype, ' ' * 8)
    lines += [f'        {b["store"].format(f"{v}_out + i_", o, **fmt)};' for v, o in zip(fd.write_limbs(), outs)]
    items, routs = ir.inline_call(record, kernels, [ir.Operand(a) for a in lane + outs], cpp.REC)
    lines += _statements(b, items, kernels, ctype, ' ' * 8) + cpp._assign(lane, routs, ' ' * 8) + ['    }']
    for v, kind in zip(stored, kinds):
        decl = b['mask_decl'][ctype] if kind == ir.MASK else f'{ctype} {{0}}[{w}]'
        if decl:
            lines.append(f'    {decl.format(v)};')
    lines += [f'    {(b["mask_store"][ctype] if kind == ir.MASK else b["store"]).format(v, r, **fmt)};'
              for v, r, kind in zip(stored, lane, kinds)]
    lines += [f'    bool {v} = {b["mask_lane"][ctype].format(r, "0")};' if kind == ir.MASK else
              f'    {ctype} {v} = {r}[0];' for v, r, kind in zip(state, stored, kinds)]
    lines.append(f'    for (std::size_t j_ = 1; j_ < {w}; ++j_) {{')
    lines += [f'        const bool {v} = {b["mask_lane"][ctype].format(r, "j_")};' if kind == ir.MASK else
              f'        const {ctype} {v} = {r}[j_];' for v, r, kind in zip(nxt, stored, kinds)]
    body, couts = cpp._call(combine, kernels, ctype, state + nxt, cpp.COMB, ' ' * 8)
    lines += body + cpp._assign(state, couts, ' ' * 8) + ['    }']
    lines.append('    for (std::size_t i_ = full_; i_ < n; ++i_) {')
    lines += cpp.bv_element(fd, kernels, ctype, ' ' * 8, state) + ['    }']
    return lines + cpp.bv_end(fd, kernels, ctype, state, packed=True) + ['}']


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
             f'#include {b["include"]}'] + (['#include <cstddef>'] if getattr(kernels, 'folds', {}) else []) + [
             '',
             f'#include "{prelude_name}"', '',
             'KAIRN_GEN_PUSH_WARNINGS',
             'namespace kairn::gen {', '',
             '// The complement of a lane mask, and IEEE 754 nextUp and nextDown in every lane by',
             '// stepping the bit pattern, as next_up_bits of prelude.hpp does for one number.',
             HELPERS[b['file']].rstrip('\n')]
    for k in kernels.values():
        lines += [''] + cpp._description(k, kernels)[:1]
        for ctype in cpp.TYPES:
            lines += function(b, k, kernels, ctype)
    folds = [fd for fd in getattr(kernels, 'folds', {}).values() if 'lanes' in fd.orders]
    if folds:
        lanes = ', '.join(f'{b["types"][t][4]} for {t}' for t in cpp.TYPES)
        lines += ['', '// --- Folds: the lane order with the lanes of a register (docs/developer/architecture.md,',
                  f'// "Folds"): {lanes}. The packed step in the loop, the scalar combination, step and',
                  '// finish of scalar.hpp after it, inlined in the same way: values step_V, comb_V, fin_V.']
        for fd in folds:
            lines.append('')
            for i, ctype in enumerate(cpp.TYPES):
                printer = map_packed if fd.is_map else bv_packed if fd.is_bv else fold_packed
                if fd.is_bv:
                    lines += cpp.bv_end_function(fd, kernels, ctype, packed=True)
                lines += printer(b, fd, kernels, ctype)[(1 if i else 0):]
    lines += ['', '}  // namespace kairn::gen', 'KAIRN_GEN_POP_WARNINGS']
    return '\n'.join(lines) + '\n'
