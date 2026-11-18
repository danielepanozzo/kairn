// Phase 0 experiment: what float arithmetic on this Metal device actually does.
//
// One compute kernel evaluates, for each input triple (a, b, c) of float bit patterns, the
// operations Kairn's networks are made of; the host compares every output bit pattern with
// IEEE-754 round-to-nearest-even results computed on the CPU (Swift never contracts or
// reassociates). The shader is compiled at run time under each math mode, once as written and
// once with the scoped pragmas `#pragma METAL fp math_mode(safe)` / `fp contract(off)` at the
// start of the function body.
//
// Reported per configuration: mismatches per operation, split by whether a subnormal is involved
// (an input, or the IEEE result), and for mismatches whether the device result is the IEEE result
// rounded toward zero, or zero (flushed), or the fused / unfused alternative.
import Foundation
import Metal

// where: 0 = no pragmas; 1 = pragmas at the start of the kernel body; 2 = the arithmetic is in a
// helper function that starts with the pragmas, called from a kernel that has none (the shape
// Kairn's MSL header has inside a client's shader).
func shader(_ where_: Int) -> String {
    let p = "#pragma METAL fp math_mode(safe)\n    #pragma METAL fp contract(off)"
    let body = """
        const float s = a + b;                       // 0: sum
        const float bb = s - a;
        const float e = (a - (s - bb)) + (b - bb);   // 1: TwoSum error term
        const float p = a * b;                       // 2: product
        const float pe = fma(a, b, -p);              // 3: TwoProd error term
        const float f = fma(a, b, c);                // 4: fma
        const float t = a * b;
        const float u = t + c;                       // 5: product then sum, two statements
        const float v = a * b + c;                   // 6: product and sum, one expression
        const float q = a / b;                       // 7: quotient
        const float r = sqrt(fabs(a));               // 8: square root (default variant)
        const float z = (a + b) - a;                 // 9: reassociation probe: must not become b
        const float rp = precise::sqrt(fabs(a));     // 10: square root (precise variant)
        R o;
        o.v[0] = s; o.v[1] = e; o.v[2] = p; o.v[3] = pe; o.v[4] = f; o.v[5] = u;
        o.v[6] = v; o.v[7] = q; o.v[8] = r; o.v[9] = z; o.v[10] = rp;
    """
    let helper = where_ == 2 ? "static R compute(float a, float b, float c) {\n    \(p)\n\(body)\n    return o;\n}" : ""
    let inKernel = where_ == 2 ? "    const R o = compute(a, b, c);" : (where_ == 1 ? "    \(p)\n" : "") + body
    return """
    #include <metal_stdlib>
    using namespace metal;
    struct R { float v[11]; };
    \(helper)
    kernel void probe(const device uint *in [[buffer(0)]], device uint *out [[buffer(1)]],
                      uint gid [[thread_position_in_grid]]) {
        const float a = as_type<float>(in[3 * gid]), b = as_type<float>(in[3 * gid + 1]), c = as_type<float>(in[3 * gid + 2]);
    \(inKernel)
        for (int k = 0; k < 11; ++k) out[11 * gid + k] = as_type<uint>(o.v[k]);
    }
    """
}

// A second kernel: how exactly are subnormals flushed? in = (x, y) bit patterns.
let flushShader = """
#include <metal_stdlib>
using namespace metal;
kernel void flush(const device uint *in [[buffer(0)]], device uint *out [[buffer(1)]],
                  uint gid [[thread_position_in_grid]]) {
    #pragma METAL fp math_mode(safe)
    #pragma METAL fp contract(off)
    const float x = as_type<float>(in[2 * gid]), y = as_type<float>(in[2 * gid + 1]);
    out[4 * gid + 0] = as_type<uint>(x * y);
    out[4 * gid + 1] = as_type<uint>(x + y);
    out[4 * gid + 2] = (x != 0.0f) ? 1u : 0u;
    out[4 * gid + 3] = as_type<uint>(fma(x, y, 0.0f));
}
"""

// SplitMix64: deterministic inputs.
var state: UInt64 = 0x9E37_79B9_7F4A_7C15
func next() -> UInt64 {
    state &+= 0x9E37_79B9_7F4A_7C15
    var z = state
    z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
    z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
    return z ^ (z >> 31)
}
// A float with a random 24-bit significand, sign, and exponent in [lo, hi]; exponents below -126
// give subnormals (the significand is shifted, as rounding would).
func rnd(_ lo: Int, _ hi: Int) -> Float {
    let m = Float(1) + Float(next() >> 41) * 0x1p-23
    let e = lo + Int(next() % UInt64(hi - lo + 1))
    let x = Float(sign: .plus, exponent: e, significand: m)  // exact scaling, rounds in the subnormal range
    return next() & 1 == 0 ? x : -x
}
let n = 1 << 18
var inputs = [Float](repeating: 0, count: 3 * n)
for i in 0..<n {
    switch i % 8 {
    case 0, 1, 2:  // ordinary magnitudes, exponents close enough to interact
        inputs[3 * i] = rnd(-20, 20); inputs[3 * i + 1] = rnd(-20, 20); inputs[3 * i + 2] = rnd(-40, 40)
    case 3:  // massive cancellation in a*b + c
        let a = rnd(-10, 10), b = rnd(-10, 10)
        inputs[3 * i] = a; inputs[3 * i + 1] = b; inputs[3 * i + 2] = -(a * b)
    case 4:  // ties: b is exactly half an ulp of a
        let a = rnd(-10, 10)
        inputs[3 * i] = a; inputs[3 * i + 1] = a.ulp / 2 * (next() & 1 == 0 ? 1 : -1); inputs[3 * i + 2] = rnd(-10, 10)
    case 5:  // subnormal operands
        inputs[3 * i] = rnd(-149, -127); inputs[3 * i + 1] = rnd(-149, -127); inputs[3 * i + 2] = rnd(-149, -120)
    case 6:  // normal operands, subnormal products and error terms
        inputs[3 * i] = rnd(-80, -50); inputs[3 * i + 1] = rnd(-90, -50); inputs[3 * i + 2] = rnd(-149, -100)
    default:  // near the smallest normal: sums that land in the subnormal range
        let a = rnd(-126, -120)
        inputs[3 * i] = a; inputs[3 * i + 1] = -a * (1 + Float(next() % 64) * 0x1p-20); inputs[3 * i + 2] = rnd(-126, -110)
    }
}

let names = ["a+b", "TwoSum err", "a*b", "TwoProd err", "fma(a,b,c)", "t=a*b; t+c", "a*b+c", "a/b", "sqrt|a|", "(a+b)-a", "precise::sqrt"]
func isSub(_ x: Float) -> Bool { x.isSubnormal }
func towardZero(_ exact: Double) -> Float {  // exact (a double) rounded toward zero to float
    let r = Float(exact)
    return abs(Double(r)) > abs(exact) ? Float(bitPattern: r.bitPattern - 1) : r
}

let device = MTLCreateSystemDefaultDevice()!
print("device: \(device.name)")
let queue = device.makeCommandQueue()!
let inBuf = device.makeBuffer(bytes: inputs, length: 3 * n * 4, options: .storageModeShared)!
let outBuf = device.makeBuffer(length: 11 * n * 4, options: .storageModeShared)!

func run(_ label: String, pragmas: Int, _ configure: (MTLCompileOptions) -> Void) {
    let options = MTLCompileOptions()
    configure(options)
    let library: MTLLibrary
    do { library = try device.makeLibrary(source: shader(pragmas), options: options) } catch {
        print("== \(label): shader did not compile: \(error.localizedDescription.split(separator: "\n").first ?? "")")
        return
    }
    let pipeline = try! device.makeComputePipelineState(function: library.makeFunction(name: "probe")!)
    let cmd = queue.makeCommandBuffer()!, enc = cmd.makeComputeCommandEncoder()!
    enc.setComputePipelineState(pipeline)
    enc.setBuffer(inBuf, offset: 0, index: 0)
    enc.setBuffer(outBuf, offset: 0, index: 1)
    enc.dispatchThreads(MTLSize(width: n, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 256, height: 1, depth: 1))
    enc.endEncoding()
    cmd.commit()
    cmd.waitUntilCompleted()
    let out = outBuf.contents().bindMemory(to: UInt32.self, capacity: 11 * n)

    // per op: [normal cases, normal mismatches, subnormal cases, subnormal mismatches]; notes on mismatches
    var counts = [[Int]](repeating: [0, 0, 0, 0], count: 11)
    var notes = [[String: Int]](repeating: [:], count: 11)
    for i in 0..<n {
        let a = inputs[3 * i], b = inputs[3 * i + 1], c = inputs[3 * i + 2]
        let s = a + b, bb = s - a, e = (a - (s - bb)) + (b - bb)
        let p = a * b, pe = (-p).addingProduct(a, b), f = c.addingProduct(a, b)
        let u = p + c, q = a / b, r = abs(a).squareRoot(), z = (a + b) - a
        let expect: [Float] = [s, e, p, pe, f, u, u, q, r, z, r]
        let exact: [Double?] = [Double(a) + Double(b), nil, Double(a) * Double(b), nil, nil, nil, nil, nil, nil, nil, nil]
        let subIn = isSub(a) || isSub(b) || isSub(c)
        for k in 0..<11 {
            let got = Float(bitPattern: out[11 * i + k]), want = expect[k]
            // a subnormal anywhere in the computation of this output (inputs, intermediates, result)
            let sub = subIn || isSub(want) || isSub(s) || isSub(p) || (k == 1 && (isSub(bb) || isSub(s - bb)))
            counts[k][sub ? 2 : 0] += 1
            if got.bitPattern == want.bitPattern || (got.isNaN && want.isNaN) || (got == 0 && want == 0) { continue }
            counts[k][sub ? 3 : 1] += 1
            var why = "other"
            if got == 0 { why = "zero (flushed)" }
            else if let x = exact[k], got.bitPattern == towardZero(x).bitPattern { why = "rounded toward zero" }
            else if (k == 5 || k == 6) && got.bitPattern == f.bitPattern { why = "fused (= fma)" }
            else if k == 9 && got.bitPattern == b.bitPattern { why = "reassociated to b" }
            else if k == 1 && got == 0 { why = "zero" }
            notes[k][why, default: 0] += 1
        }
    }
    print("== \(label)")
    for k in 0..<11 {
        let c = counts[k]
        let why = notes[k].sorted { $0.value > $1.value }.map { "\($0.value) \($0.key)" }.joined(separator: ", ")
        print(String(format: "  %-12@ no subnormal involved: %6d / %6d differ    subnormal involved: %6d / %6d differ   %@",
                     names[k] as NSString, c[1], c[0], c[3], c[2], why.isEmpty ? "" : "[" + why + "]"))
    }
}

run("default MTLCompileOptions", pragmas: 0) { _ in }
run("mathMode = .fast", pragmas: 0) { $0.mathMode = .fast }
run("mathMode = .relaxed", pragmas: 0) { $0.mathMode = .relaxed }
run("mathMode = .safe, mathFloatingPointFunctions = .precise", pragmas: 0) { $0.mathMode = .safe; $0.mathFloatingPointFunctions = .precise }
run("default MTLCompileOptions + scoped pragmas at the start of the kernel body", pragmas: 1) { _ in }
run("default MTLCompileOptions + scoped pragmas in a helper function called from an unprotected kernel", pragmas: 2) { _ in }
run("mathMode = .fast + scoped pragmas in a helper function called from an unprotected kernel", pragmas: 2) { $0.mathMode = .fast }

// How subnormals are flushed (safe math mode by pragma).
do {
    let m = Float.leastNormalMagnitude  // 2^-126
    let cases: [(String, Float, Float)] = [
        ("subnormal input: 0x1p-140 * 0x1p+30 (IEEE 0x1p-110)", 0x1p-140, 0x1p+30),
        ("subnormal input: 0x1p-140 + 1 (IEEE 1)", 0x1p-140, 1),
        ("subnormal + subnormal, normal sum: 0x1.8p-127 + 0x1.8p-127 (IEEE 0x1.8p-126)", 0x1.8p-127, 0x1.8p-127),
        ("exact subnormal result: 0x1p-126 * 0.5 (IEEE 0x1p-127)", m, 0.5),
        ("exact subnormal result, negative: -0x1p-126 * 0.5 (IEEE -0x1p-127)", -m, 0.5),
        ("tiny before rounding, rounds to the smallest normal: (1 - 2^-24) * 0x1p-126 (IEEE 0x1p-126)", 0x1.fffffep-1, m),
        ("normal - normal, subnormal difference: 0x1.000002p-126 + -0x1p-126 (IEEE 0x1p-149)", 0x1.000002p-126, -m),
        ("smallest normal passes through: 0x1p-126 * 1 (IEEE 0x1p-126)", m, 1),
    ]
    var fin = [UInt32]()
    for c in cases { fin.append(c.1.bitPattern); fin.append(c.2.bitPattern) }
    let library = try! device.makeLibrary(source: flushShader, options: nil)
    let pipeline = try! device.makeComputePipelineState(function: library.makeFunction(name: "flush")!)
    let ib = device.makeBuffer(bytes: fin, length: fin.count * 4, options: .storageModeShared)!
    let ob = device.makeBuffer(length: cases.count * 16, options: .storageModeShared)!
    let cmd = queue.makeCommandBuffer()!, enc = cmd.makeComputeCommandEncoder()!
    enc.setComputePipelineState(pipeline)
    enc.setBuffer(ib, offset: 0, index: 0)
    enc.setBuffer(ob, offset: 0, index: 1)
    enc.dispatchThreads(MTLSize(width: cases.count, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 1, height: 1, depth: 1))
    enc.endEncoding()
    cmd.commit()
    cmd.waitUntilCompleted()
    let o = ob.contents().bindMemory(to: UInt32.self, capacity: cases.count * 4)
    func hex(_ b: UInt32) -> String {
        let f = Float(bitPattern: b)
        return f == 0 ? (f.sign == .minus ? "-0" : "+0") : "\(f)".isEmpty ? "" : String(format: "%a", Double(f))
    }
    print("== how subnormals are flushed (x, y from a buffer; safe math mode by pragma)")
    for (i, c) in cases.enumerated() {
        print("  \(c.0)\n      x*y = \(hex(o[4 * i]))   x+y = \(hex(o[4 * i + 1]))   (x != 0) = \(o[4 * i + 2])   fma(x,y,0) = \(hex(o[4 * i + 3]))")
    }
}
