# References, prior art and licenses

How to read this page: most entries were collected by research agents working from primary
sources (paper PDFs, repository files, vendor documentation) on 2026-11-18, with quotations kept
in their reports; I did not re-read every source myself. Where a fact matters for a decision and
could be tested, it was tested, and the result is under
[`experiments/phase0/`](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0).
Items the agents could not confirm from a primary source are listed at the end.

**License rule.** Algorithms are taken from papers and cited. Code is reused only from MIT-,
BSD- or Apache-licensed sources and only with attribution; nothing is taken from GPL code.
Proof-library dependencies under LGPL (Flocq, the Gappa support library) are build-time
dependencies of the proofs, not of the library.

## Double-word arithmetic

<a id="jmp17"></a>**JMP17.** M. Joldes, J.-M. Muller, V. Popescu. *Tight and rigorous error
bounds for basic building blocks of double-word arithmetic.* ACM TOMS 44(2), 2017.
[hal-01351529](https://hal.science/hal-01351529). The fifteen algorithms of the $k = 2$ table.
Unbounded exponent range throughout.

<a id="mr22"></a>**MR22.** J.-M. Muller, L. Rideau. *Formalization of double-word arithmetic, and
comments on "Tight and rigorous error bounds…".* ACM TOMS 48(1), 2022.
[hal-02972245](https://hal.science/hal-02972245). Rocq + Flocq proofs of all of JMP17, with three
bounds improved (DWTimesDW1 and 2 to $5u^2$, DWTimesDW3 to $4u^2$) and one proof repaired.
19 000 lines, **MIT**, written for Coq 8.12 and Flocq 3.3; format `FLX` (no underflow, no
overflow); `TwoProd` exactness is a section hypothesis; the archive is at the URL given in the
paper. Whether it builds on current Rocq was not tried.

<a id="llmpr23"></a>**LLMPR23.** V. Lefèvre, N. Louvet, J.-M. Muller, J. Picot, L. Rideau.
*Accurate calculation of Euclidean norms using double-word arithmetic.* ACM TOMS, 2023.
[hal-03482567](https://hal.science/hal-03482567). Double-word square root with bound
$\tfrac{25}{8}u^2$, Rocq-proved (MIT), with case lemmas for gradual underflow.

<a id="jjlm26"></a>**JJLM26.** C.-P. Jeannerod, M. Joldes, N. Louvet, J.-M. Muller.
*Extended-precision FMA under parameterized double-word overlap.* ARITH 2026.
[hal-05517451](https://inria.hal.science/hal-05517451). Candidate for a dedicated 2-limb FMA; not
studied yet.

<a id="hjzrt23"></a>**HJZRT23.** T. Hubrecht, C.-P. Jeannerod, P. Zimmermann, L. Rideau,
L. Théry. *Towards a correctly-rounded and fast power function in binary64 arithmetic.*
[hal-04159652](https://hal.science/hal-04159652). Double-word building blocks *with* underflow
terms, for one function.

<a id="expfloat"></a>**ExpFloat.** L. Théry, L. Rideau. [github.com/thery/ExpFloat](https://github.com/thery/ExpFloat),
**MIT**, active in 2026 (Rocq 9.2, Flocq 4.2.2). Rocq proofs behind HJZRT23, including `Fast2Sum`
robustness with gradual underflow and the bound $|h + l - ab| < \eta$ for the FMA product. The
closest existing development to what Kairn needs.

<a id="bgm17"></a>**BGM17.** S. Boldo, S. Graillat, J.-M. Muller. *On the robustness of the 2Sum
and Fast2Sum algorithms.* ACM TOMS 44(1), 2017. [ensl-01310023](https://hal.science/ensl-01310023).
Overflow: the only spurious overflow of 2Sum is at $|a| = \Omega$. Pen-and-paper.

<a id="bm11"></a>**BM11.** S. Boldo, C. Marché. *Formal verification of numerical programs: from
C annotated programs to mechanical proofs.* Math. Comput. Sci., 2011.
[hal-00777605](https://inria.hal.science/hal-00777605). Overflow preconditions of Dekker's product
in `double`.

<a id="jr18"></a>**JR18.** C.-P. Jeannerod, S. M. Rump. *On relative errors of floating-point
operations: optimal bounds and applications.* Math. Comp. 87, 2018.
[hal-00934443](https://hal.science/hal-00934443). The $u/(1+u)$ family.

## More than two limbs

<a id="za25"></a>**ZA25.** D. K. Zhang, A. Aiken. *Automatic verification of floating-point
accumulation networks.* CAV 2025. [arXiv:2505.18791](https://arxiv.org/abs/2505.18791). Verifier:
[github.com/dzhang314/FPANVerifier](https://github.com/dzhang314/FPANVerifier), **MIT**. Proves
two 2-limb additions; SMT on an abstraction; unbounded exponents; the result is a bare `unsat`.

<a id="za-sc25"></a>**ZA-SC25.** D. K. Zhang, A. Aiken. *High-performance branch-free algorithms
for extended-precision floating-point arithmetic.* SC'25,
[doi:10.1145/3712285.3759876](https://doi.org/10.1145/3712285.3759876). The 3- and 4-limb addition
and multiplication networks, with bounds stated in figure captions. The network descriptions are
in the FPANVerifier repository (**MIT**) and were read to count their gates.

<a id="zhang-thesis"></a>**Zhang's thesis.** D. K. Zhang, Stanford, 2025
([PDF](https://theory.stanford.edu/~aiken/publications/theses/zhang.pdf)). Defines *strongly
nonoverlapping*, the invariant Kairn adopts. Also
[github.com/dzhang314/MultiFloatProofs](https://github.com/dzhang314/MultiFloatProofs) (**MIT**):
Rocq proofs of five 2-limb operations without underflow, described by their author as
AI-generated and awaiting review; not relied on.

<a id="fmp19"></a>**FMP19.** N. Fabiano, J.-M. Muller, J. Picot. *Algorithms for triple-word
arithmetic.* IEEE TC 68(11), 2019. [hal-01869009](https://hal.science/hal-01869009).
Pen-and-paper; data-dependent tests; no underflow.

<a id="jmmp16"></a>**JMMP16.** M. Joldes, O. Marty, J.-M. Muller, V. Popescu. *Arithmetic
algorithms for extended precision using floating-point expansions.* IEEE TC 65(4), 2016.
[hal-01111551](https://hal.science/hal-01111551). With V. Popescu's thesis
([tel-01534090](https://hal.science/tel-01534090)), the theory behind **CAMPARY**, whose code is
**GPL v2 or later**: no code is taken from it.

<a id="bjmp17"></a>**BJMP17.** S. Boldo, M. Joldes, J.-M. Muller, V. Popescu. *Formal
verification of a floating-point expansion renormalization algorithm.* ITP 2017.
[hal-01512417](https://hal.science/hal-01512417). Rocq proof, with subnormals, of a branching
renormalization returning the ulp-nonoverlapping form. Code location not found.

<a id="hm26"></a>**HM26.** T. Hubrecht, G. Melquiond. *Verifying code that uses error-free
transformations.* ARITH 2026 ([slides](https://hubrecht.ovh/_uploads/pdf/2026-06-ARITH.pdf)).
Gappa extended to error-free transformations; triple-word product bound reproduced. Slides only.

<a id="qd"></a>**QD.** Y. Hida, X. S. Li, D. H. Bailey. *Algorithms for quad-double precision
floating point arithmetic.* ARITH-15, 2001. Code:
[github.com/BL-highprecision/QD](https://github.com/BL-highprecision/QD), **BSD-3-Clause** with an
LBNL note asking commercial users to contact them; no code is taken. Performance baseline.

**MultiFloats.jl.** [github.com/dzhang314/MultiFloats.jl](https://github.com/dzhang314/MultiFloats.jl),
**MIT**, v3.3.2. Uses the ZA-SC25 networks for 2 to 4 limbs; removed 5 to 8 limbs as "fundamentally
broken". Treats infinities as NaN. Performance baseline.

**CCCL fpmp2.** `cuda::fpmp2` in NVIDIA's CUDA Core Compute Libraries
([github.com/NVIDIA/cccl](https://github.com/NVIDIA/cccl)), **Apache-2.0 with LLVM exception**.
Two limbs only (`float` or `double`), three accuracy levels, first committed in August 2026 and
not yet in a release. Its own documentation says that none of its bounds comes from verifying its
sources and that division and square root are measured only. Performance baseline on CUDA.

## Sums, dot products, enclosures

<a id="oro05"></a>**ORO05.** T. Ogita, S. M. Rump, S. Oishi. *Accurate sum and dot product.* SIAM
J. Sci. Comput. 26(6), 2005 ([PDF](https://www.tuhh.de/ti3/paper/rump/OgRuOi05.pdf)). Sum2, SumK,
Dot2, DotK with underflow terms. Also S. M. Rump, *Error estimation of floating-point summation
and dot product*, BIT 52, 2012, for a priori bounds in round-to-nearest.

<a id="higham"></a>**Higham.** N. J. Higham. *Accuracy and Stability of Numerical Algorithms*, 2nd ed., SIAM, 2002.
The standard model and $\gamma_n$; the form in which Kairn exports its error model, and the
reference cited by the proofs of the first client (a library for verified computation with balls
on CPU and CUDA). Section 4.2 gives the bound of a sum for any order of the additions, and
Lemma 3.1 the bound $(1 + \varepsilon)^n - 1 \le \gamma_n$, which the
[Milestone 2 statements](../milestone2.md#summation-over-any-tree) restate over trees.

<a id="rzbm09"></a>**RZBM09.** S. M. Rump, P. Zimmermann, S. Boldo, G. Melquiond. *Computing
predecessor and successor in rounding to nearest.* BIT 49, 2009
([PDF](https://www.tuhh.de/ti3/paper/rump/RuZiBoMe08.pdf)). Algorithm 1 (branch-free, always a
valid bound, exact outside $[\tfrac12, 2]\,u^{-1}\eta$) and Algorithm 2 (exact everywhere).

<a id="kv"></a>**kv.** M. Kashiwagi. [verifiedby.me/kv](http://verifiedby.me/kv/),
[github.com/mskashi/kv](https://github.com/mskashi/kv), **MIT**. Interval arithmetic that can run
without changing the rounding mode (`KV_NOHWROUND`): directed results from the sign of the exact
error of `twosum`/`twoproduct`, as Kairn will do, including a double-double interval type. Its
thresholds (rescaling below $2^{-969}$) match the `TwoProd` exactness condition above.

**Arb / FLINT.** F. Johansson. *Arb: efficient arbitrary-precision midpoint-radius interval
arithmetic.* IEEE TC 66(8), 2017. FLINT 3 is **LGPL v3 or later**: used by the test oracle only.
Model for ball semantics (whole-line balls, predicates that return "certainly true or unknown").

**MPFR.** [mpfr.org](https://www.mpfr.org/), LGPL v3 or later: test oracle only.

<a id="rump99"></a>**Rump99.** S. M. Rump. *Fast and parallel interval arithmetic.* BIT 39, 1999.
Midpoint-radius arithmetic overestimates by at most 1.5 in radius.

<a id="vdh09"></a>**vdH09.** J. van der Hoeven. *Ball arithmetic.* 2009.
[hal-00432152](https://hal.science/hal-00432152). Balls over normed vector spaces: the model of
`BallVector`.

<a id="ieee-1788"></a>**IEEE 1788.** IEEE Std 1788-2015 and 1788.1-2017. **The standards
themselves were not consulted** (paywalled); the semantics in this report come from the P1788
drafts D9.2 and D9.7, N. Revol's overview, and the documentation of the Octave interval package
and IntervalArithmetic.jl.

<a id="itf1788"></a>**ITF1788.** M. Kiesner, M. Nehmeier, J. Wolff von Gudenberg. *ITF1788:
An Interval Testframework for IEEE 1788*, 2015 (the reference its README gives); the copy read
is O. Heimlich's fork, [github.com/oheim/ITF1788](https://github.com/oheim/ITF1788).
Test cases for the operations of IEEE Std 1788-2015 on intervals with `binary64` bounds, in a
language of its own (`.itl` files). The framework is under the **Apache License 2.0**. The cases
carry the license of the library they were taken from, stated at the top of each file, as read
on 2026-11-19: the `libieeep1788_*.itl` files (from M. Nehmeier's libieeep1788, converted by
O. Heimlich) are **Apache 2.0** and may be converted and stored with their notice and a
statement of the change; `mpfi.itl` (GNU MPFI), `fi_lib.itl` (FI_LIB) and `c-xsc.itl` (C-XSC)
are **LGPL 2.1 or later** and are not copied. Used by the
[Milestone 2 statements](../milestone2.md#ieee-1788) as the public check of the semantics taken
from the drafts.

**CORE-MATH** ([core-math.gitlabpages.inria.fr](https://core-math.gitlabpages.inria.fr/), MIT)
and **CRlibm**: prior art for elementary functions with proofs; the first client's current source
of interval functions.

## Proof tools

<a id="proof-assistants"></a>**Flocq.** S. Boldo, G. Melquiond.
[gitlab.inria.fr/flocq/flocq](https://gitlab.inria.fr/flocq/flocq), LGPL v3 or later, 4.2.2
(February 2026). **Gappa** 1.8 and its Rocq support library; **CoqInterval** 4.11 (CeCILL-C).
**Rocq** 9.3 is current; Phase 0 used the 9.0 container image. Lean 4 candidates surveyed:
FloatSpec, flean, FloatLib. Isabelle: the AFP entry IEEE_Floating_Point.

## Backends

<a id="backends"></a>

- *Metal Shading Language Specification*, version 4.1 (June 2026), sections 1.6.3, 6.6 and 8;
  *Metal Feature Set Tables* (October 2026), for the statement that `float` subnormals are a
  feature of the Apple11 GPU family and later.
- *CUDA Programming Guide* 13.5, appendix on mathematical functions and on C++ support; *CUDA
  Math API*; NVIDIA's white paper on floating point and IEEE 754; the table of FP32-to-FP64
  throughput ratios per compute capability (64:1 for 8.6, 8.9 and 12.x).
- GCC, Clang and MSVC documentation of `-ffp-contract`, `#pragma clang fp`, `/fp:contract`,
  `-frounding-math` and the predefined macros; Intel SDM volume 1 for MXCSR; Arm's FPCR
  description.

## Not confirmed from a primary source

- The Handbook of Floating-Point Arithmetic's statement of the `TwoProd` condition (the condition
  itself was taken from JMP17 and from Flocq, and is now proved in the tracer).
- The final published texts of ORO05's companion papers, of Lange and Rump's pair arithmetic, and
  of IEEE 1788.
- The location and license of the BJMP17 Rocq sources.
- Whether MR22's archive builds on Rocq 9.
- NVIDIA's ULP tables are described by NVIDIA as "derived from extensive, though not exhaustive,
  testing".
- For CCCL fpmp2, MultiFloats.jl and QD: the descriptions are of the repositories as they were on
  2026-11-18.
