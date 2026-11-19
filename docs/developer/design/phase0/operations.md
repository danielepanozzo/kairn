# Operations: what each one requires, returns and guarantees

Theorem statements in plain mathematics for every operation of the brief. Notation and the
definition of *normalized* are in [Numbers](numbers.md). Nothing on this page is implemented yet,
and most of it is not yet proved by Kairn: each statement carries a status.

| Status | Meaning |
|---|---|
| **F** | Machine-checked in the literature (Rocq + Flocq), but in a model with no underflow and no overflow. Kairn must redo it with gradual underflow. |
| **S** | Verified in the literature by an SMT solver, in a model with unbounded exponents, with the solver's `unsat` trusted as is. Kairn must prove it in Rocq. |
| **P** | Pen-and-paper proof in the literature. Kairn must formalize it. |
| **K** | New: to be established by Kairn. A constant shown under this status is a *target* derived by counting roundings, not a guarantee. |

Until its Rocq proof exists, an operation ships with the `UNVERIFIED` marker and its constants are
not exported through `kairn::traits`.

## The shape of every statement

**Schema.** Let $\circ$ be an operation, $K$ its kernel for a given $(T, k)$, and let the operands
be finite and normalized. Let $z = K(x, y)$ be computed in round-to-nearest-even with gradual
underflow, *under any contraction of the kernel that the rules of the IR allow*
([Environment](environment.md#contraction)). Then either $z_0$ is not finite, or all of:

1. $z$ is normalized;
2. $|z - (x \circ y)| \le c\,u^k\,|x \circ y| + t\,\eta$ (form **R**, relative to the exact
   result), or, where that is all that holds,
   $|z - (x \circ y)| \le c\,u^k\,(|x| + |y|) + t\,\eta$ (form **A**, relative to the operands);
3. if $|x \circ y| \le \Omega_{\mathrm{safe}}$ then $z_0$ is finite.

**Exported constants.** For each operation, `kairn::traits<Expansion<T, k>>` exposes
`unit` $\ge c\,u^k$ and `tiny` $\ge t\,\eta$ as `constexpr` values of type $T$ rounded up, the
form (R or A), and `unit_computed` $\ge \mathrm{unit}/(1 - \mathrm{unit})$ for clients whose
analysis is written relative to the computed value (Higham's (2.5)). A client proof written for
$u = 2^{-53}$ in the standard model carries over by substituting these.

"Correct rounding" in Kairn always means *this*: an outward or nearest result within the stated
bound, never rounding to a nearest k-number (which is not even well defined, since k-numbers of a
given $k$ are not a floating-point format).

## Building blocks

These are the only places where exactness, rather than a bound, is claimed. The first three are
already checked by the Phase 0 tracer
([`experiments/phase0/tracer/Proofs.v`](https://github.com/danielepanozzo/kairn/blob/main/experiments/phase0/tracer/Proofs.v)),
parametric in $p$, $\eta$ and the tie rule.

| Block | Code (one rounding per line) | Statement (model G) | Status |
|---|---|---|---|
| `TwoSum(a, b)` | 6 additions/subtractions (Knuth) | $s = \mathrm{RN}(a+b)$ and $s + e = a + b$ exactly, for all finite $a, b$ including subnormals, provided $s$ is finite. | proved in the tracer from Flocq's `TwoSum_correct` |
| `Fast2Sum(a, b)` | $s = a \oplus b$; $z = s \ominus a$; $e = b \ominus z$ | The same, when $\lvert a\rvert \ge \lvert b\rvert$ (or the exponent of $a$ is at least that of $b$). The result $(s, e)$ is normalized. | proved in the tracer |
| `TwoProd(a, b)` | $p = \mathrm{fma}(a, b, 0)$; $e = \mathrm{fma}(a, b, -p)$ | $p = \mathrm{RN}(ab)$, and $p + e = ab$ exactly when $ab = 0$ or $\lvert ab\rvert \ge 2^{2p-1}\eta$ ($2^{-969}$ in `double`, $2^{-102}$ in `float`). | proved in the tracer from Flocq's `mult_error_FLT` |
| `TwoProd`, small products | same | For all finite $a, b$: $\lvert p + e - ab\rvert \le \eta/2$. | **K** (known with constant 1 for any rounding: [HJZRT23](references.md#hjzrt23)) |
| `TwoProd`, constant evaluation | Dekker's product with Veltkamp's split (17 operations) | Exact under the same condition, and $\lvert p + e - ab\rvert \le \tfrac72\eta$ always, when no intermediate overflows. | Flocq `Dekker`; overflow precondition **P** ([BM11](references.md#bm11)) |
| Opaque product | $p = \mathrm{fma}(a, b, 0)$ | $p = \mathrm{RN}(ab)$ as a real number (the sign of a zero may differ from `a * b`). | trivial; see [why](environment.md#the-rule-no-product-feeds-an-addition) |

`TwoSum`, `Fast2Sum` and `TwoProd` are public API (`kairn::two_sum`, …): clients such as miso2
use them for their own exactness tests.

## k = 1

`Expansion<T, 1>` is `T`. Its operations are `T`'s, and their bounds are the optimal ones of
[JR18](references.md#jr18), available in Flocq with the underflow term (`relative_error_N_FLT'_ex`).

| Operation | $c$ (form R) | $t$ | Status |
|---|---|---|---|
| $a \pm b$ | $1/(1+u)$ | 0 (sums are exact in the subnormal range) | Flocq |
| $a \cdot b$, $\mathrm{fma}(a, b, c)$ | $1/(1+u)$ | $1/2$ | Flocq |
| $a / b$ | $1 - 2u$ | $1/2$ | [JR18](references.md#jr18) **P**; underflow form in Flocq |
| $\sqrt a$ | $(1 - 1/\sqrt{1+2u})/u$, below 1 | 0 | Flocq (`sqrt_error_N_FLT_ex`) |

Exported: `unit` $= u$, `tiny` $= \eta$ for products and quotients and $0$ otherwise. One
subtlety is specific to $k = 1$: its `*` and `+` are the client's `T` operators, so the client's
compiler may fuse `a * b + c`. The statements above hold either way (a fused result is
$\mathrm{RN}(ab + c)$, which satisfies the bound of the two-operation composition), but the
intermediate product is then not a value of $T$. See
[D6](decisions.md#d6-one-limb-and-contraction-under-clang).

## k = 2 (double-word)

The algorithms are those of [JMP17](references.md#jmp17) with the bounds as corrected and
machine-checked by [MR22](references.md#mr22), and the square root of
[LLMPR23](references.md#llmpr23). Operation counts take `TwoProd` as two FMAs.

| Operation | Algorithm | Flops | $c$ (form R unless noted) | Literature status | $t$ target |
|---|---|---|---|---|---|
| $x + y$, **accurate (default)** | AccurateDWPlusDW (JMP Alg. 6) | 20 | $3/(1-4u)$, asymptotically optimal | **F** `DWPlusDW_relerr_bound` ($p \ge 3$, ties to even) | 0 |
| | or "madd" ([ZA25](references.md#za25)): the same six gates wired differently, depth 4 instead of 5 | 20 | $2(1+2u)$ by SMT; $3/2$ in an unreviewed Rocq proof | **S** | 0 |
| $x + y$, fast | SloppyDWPlusDW (JMP Alg. 5) | 11 | form **A**: $4$ (Dekker's bound, as cited); $3$ in form R when $x$ and $y$ have the same sign | **P**; no formal proof exists | 0 |
| $x + a$, $a \in T$ | DWPlusFP (JMP Alg. 4) | 10 | 2 | **F** `DWPlusFP_bound` | 0 |
| $x \cdot y$ | DWTimesDW3 (JMP Alg. 12) | 9 | 4 | **F** `DWTimesDW12_correct` ($p \ge 5$) | ≤ 4 |
| $x \cdot a$ | DWTimesFP3 (JMP Alg. 9) | 6 | 2 | **F** `DWTimesFP9_correct` | ≤ 2 |
| $x / y$ | DWDivDW3 (JMP Alg. 18) | 31 | 9.8 | **F** `DWDDW3_correct` ($p \ge 14$) | **K** |
| $x / a$ | DWDivFP3 (JMP Alg. 15) | 10 | 3 | **F** `DWDFP3_correct` | **K** |
| $\sqrt x$ | SQRTDWtoDW (LLMPR Alg. 8) | 8 | 25/8, asymptotically optimal | **F**, with case lemmas for underflow when $x \ge 2^{p}\lambda$ | 0 by exact rescaling of small $x$ |
| $\mathrm{fma}(x, y, w)$ | product then accurate sum; a dedicated kernel ([JJLM26](references.md#jjlm26)) later | 29 | not form R: $3u^2\lvert xy + w\rvert + 4u^2\lvert xy\rvert$ (a relative bound under cancellation needs the dedicated kernel) | **K** | ≤ 4 |

Remarks:

- The Phase 0 experiment measured a maximum of $3.09\,u^2$ for the product on 20 000 random
  cases, against the proven $4u^2$
  ([contraction results](https://github.com/danielepanozzo/kairn/tree/main/experiments/phase0/contraction/results)).
- **Accurate versus fast addition** is the accuracy variant pair the brief asks for. The fast one
  has no relative bound under cancellation (JMP give an example with relative error 1), which is
  exactly why it is not the default. Whether "madd" replaces AccurateDWPlusDW is a Milestone 1
  benchmark decision; both will have Rocq proofs or neither ships.
- **What is missing from the literature for every row**: the underflow term, a statement that the
  result is normalized (MR22's Rocq states it for three of fifteen algorithms), and the `TwoProd`
  exactness, which MR22 assume as a hypothesis. The $t$ targets count the product-type roundings
  of each network at $\eta/2$ each, fused and unfused variants included.
- Division and square root may land behind `UNVERIFIED` first, as the brief allows.

## k = 3 and k = 4

The only branch-free algorithms whose inputs and outputs are both normalized in our sense are the
networks of [ZA-SC25](references.md#za-sc25) (MIT license). MultiFloats.jl 3.x uses the same
networks.

| Operation | k | Network | Depth | Published bound (form R) | Status |
|---|---|---|---|---|---|
| $x + y$ | 3 | 16 gates (9 TwoSum, 7 Fast2Sum) | 10 | $8u^3$ | **S** |
| $x + y$ | 4 | 31 gates (13 TwoSum, 18 Fast2Sum) | 13 | $8u^4$ | **S** |
| $x \cdot y$ | 3 | 3 TwoProd + 3 products, then 13 gates | 8 | $64u^3$ | **S**, and the product phase assumes exact TwoProd |
| $x \cdot y$ | 4 | 6 TwoProd + 4 products, then 33 gates | 14 | $256u^4$ | **S**, same |
| $x / y$, $\sqrt x$ | 3, 4 | Newton iteration on the above | — | none published | **K** |

A gate whose error output is discarded costs one flop instead of six or three, so the flop counts
are below $6 \times$ gates; exact counts come with the implementation.

What "S" means here, precisely ([research notes](references.md#za25)): the verifier abstracts each
float by its sign, exponent and counts of leading and trailing zeros and ones, and asks Z3 whether
the abstraction admits a counterexample. The top-level query is symbolic in $p$, but the lemmas
about `TwoSum` underneath it were checked by bit-blasting at five precisions only (8, 11, 24, 53,
113); no proof object is produced; exponents are unbounded; constants can only be powers of two
(the method proves $4u^2$ where $3u^2$ is known for the 2-limb sum); and the authors state that
they "are unable to include human-readable proofs". The bounds in the table are therefore
**targets**, and proving them in Rocq is the main verification risk of the project
([Verification](verification.md#proof-plan-per-k)).

A possible fallback for $k = 3$ is triple-word arithmetic ([FMP19](references.md#fmp19)): better
constants ($2u^3$ for the sum, $28u^3$ for the product), but pen-and-paper proofs, a weaker
invariant, and data-dependent tests in every algorithm that returns a normalized result.

## Eight limbs and runtime k

**There is no published algorithm for five or more limbs with a machine-checked, SMT-checked or
even complete pen-and-paper correctness proof under an invariant that is preserved.**
MultiFloats.jl removed its 5- to 8-limb types in version 3 because "the arithmetic algorithms for
these types were fundamentally broken". CAMPARY's proven addition bound is relative to
$|x| + |y|$, its invariant is the weak ulp one, and its code is GPL. QD stops at four and its paper
states that its renormalization is unproven.

Kairn therefore has to design and prove these. The plan, in the order of preference:

1. **One parametric algorithm**, defined by recursion on $k$, built from `TwoSum`/`TwoProd` and
   *selects* (branch-free conditional moves, which SIMD lanes and GPU threads need anyway), with a
   Rocq proof by induction on $k$ giving
   $|z - (x \circ y)| \le c(k)\,u^k\,|x \circ y| + t(k)\,\eta$ with $c(k)$ polynomial in $k$.
   Looser constants than at $k \le 4$ are acceptable per the brief.
2. **The baked-in $k = 8$ kernels are that algorithm unrolled by the generator**; the formal model
   of the unrolled network is shown equal to the parametric definition at $k = 8$ by computation
   inside Rocq, so it inherits the theorem. A tighter instance-specific bound is an optional
   later refinement, not a prerequisite.
3. If selects turn out to be insufficient, data-dependent loops are confined to a renormalization
   step with an existing Rocq proof ([BJMP17](references.md#bjmp17)) and the scalar path only.

This is research with schedule risk, and it is why $k = 8$ and runtime $k$ come late in the
[milestone plan](plan.md#milestones). **[D3](decisions.md#d3-eight-limbs-and-runtime-k) asks how you want
to handle that.**

## Conversions and scaling

| Operation | Statement | $t$ |
|---|---|---|
| $T \to$ k-number | $(a, 0, \dots, 0)$: exact, normalized. | — |
| k-number $\to$ k'-number, $k' > k$ | Append zeros: exact, normalized. | — |
| k-number $\to$ k'-number, $k' < k$ | Keep the first $k'$ limbs: normalized, error at most $\frac{u^{k'}}{1-u}\lvert x_0\rvert$. | 0 |
| Mixed-k arithmetic | Defined as: convert the narrower operand, then operate. | — |
| `double` limbs $\leftrightarrow$ `float` limbs | A `double` is exactly a 3-limb `float` number when it is in `float` range; the conversions are exact splitting or exact summation followed by truncation, with overflow to $\pm\infty$ and an underflow term. Not in the brief: added because miso2 builds in `double` on the host and narrows to `float` for the device ([API](library.md#what-miso2-needs)). | $\le k'$ |
| `ldexp(x, n)`, `half(x)` | Each limb is scaled; the result is renormalized. Exact unless a limb becomes subnormal; always $\lvert z - 2^n x\rvert \le \tfrac k2\,\eta$. | $k/2$ |
| `neg`, `abs` | Exact; limb-wise sign change (the sign of $x$ is the sign of $x_0$). | — |
| `renormalize(x)` | For limbs of decreasing magnitude with bounded overlap: a normalized result with form-R error $c\,u^k$. Status **K**: the Rocq-proved renormalization of [BJMP17](references.md#bjmp17) is the starting point, but it returns the weaker ulp-nonoverlap and uses data-dependent tests. | 0 |
| Constant from an integer or a rational $n/d$ | `constexpr`, integer arithmetic only: returns the k-number $z$, a bound $\beta \in T$ with $\lvert z - n/d\rvert \le \beta$, and a flag that is true exactly when $z = n/d$. $\beta \le u^k \lvert n/d\rvert (1 + 2u) + \eta$. | — |

The first three rows are immediate; the others are status **K**.

## Comparisons and sign

**Statement.** For finite normalized $x, y$ (and for $y \in T$): `x < y`, `x <= y`, `x == y`,
`compare(x, y)` and `sign(x)` return the truth about the real values, always. No tolerance, no
"almost equal".

**How.** $\mathrm{sign}(x) = \mathrm{sign}(x_0)$ by consequence 3 of the invariant. For
`compare`, lexicographic comparison of limbs is wrong (see [Numbers](numbers.md#a-k-number)), so:
if $x_0$ and $y_0$ differ by more than $2u(|x_0| + |y_0|)$ the leading limbs decide; otherwise the
sign of the accurate difference decides. That is sound because the accurate subtraction has a
purely relative bound with $c\,u^k < 1$ and $t = 0$ under gradual underflow: its result is zero
exactly when the operands are equal and has the sign of the exact difference otherwise. Cost: two
comparisons in the common case, one k-subtraction when the leading limbs are within two ulps.
Status: **K**, a corollary of the addition theorem.

With a NaN operand comparisons return false (and `compare` returns "unordered"), as for `T`.

**Directed conversions to T**, all exact:

| Operation | Value | How |
|---|---|---|
| `to_down(x)` | largest $t \in T$ with $t \le x$ | $x_0$ if the tail $x_1 + \dots$ is $\ge 0$, else $\mathrm{pred}(x_0)$; the sign of the tail is the sign of $x_1$. |
| `to_up(x)` | smallest $t \in T$ with $t \ge x$ | symmetric |
| `to_nearest(x)` | $\mathrm{RN}(x)$ | $x_0$, except when $x_1$ is exactly half the gap to a neighbor of $x_0$ and $x_2$ has the sign of $x_1$: then that neighbor. |
| `abs_upper(x)` | smallest $t \in T$ with $t \ge \lvert x\rvert$ | `to_up(abs(x))` |

## Enclosures

### Directed rounding without a rounding mode

Kairn never calls `fesetround`. A result rounded down or up is obtained from the round-to-nearest
result and the *sign of its exact error*, then one step to the neighbor:

$$\mathrm{RD}(a + b) = \begin{cases} \mathrm{pred}(s) & \text{if } e < 0 \\ s & \text{otherwise} \end{cases}
\qquad (s, e) = \mathrm{TwoSum}(a, b),$$

and likewise with `TwoProd` for products, and with the exact remainders $a - qb$ and $a - s^2$
(one FMA each) for quotients and square roots. `pred` and `succ` are computed in
round-to-nearest ([RZBM09](references.md#rzbm09), Algorithm 2, with its three cases as selects) or
by stepping the bit pattern. This is the technique of the kv library's `KV_NOHWROUND` mode
([kv](references.md#kv)).

| Primitive on $T$ | Statement | Status |
|---|---|---|
| `add_down`, `add_up`, `sub_*` | Exactly $\mathrm{RD}$ / $\mathrm{RU}$ of the exact result, for all finite operands. If the nearest result overflows, the lower bound is $\Omega$ and the upper bound $+\infty$ (and symmetrically). | **K**, from `TwoSum` and Flocq's `succ`/`pred` theory |
| `mul_down`, `mul_up` | Exactly $\mathrm{RD}$ / $\mathrm{RU}$ when $ab = 0$ or $\lvert ab\rvert \ge 2^{2p-1}\eta$. Below that, a valid bound within $2\eta$ of the exact product. | **K** |
| `div_*`, `sqrt_*` | Exactly $\mathrm{RD}$ / $\mathrm{RU}$ when the remainder is representable; a valid bound one ulp wider otherwise. | **K** (the remainder properties are in Flocq for unbounded exponents only) |
| `next_up`, `next_down` | Exactly $\mathrm{succ}$, $\mathrm{pred}$ for finite arguments; $\mathrm{succ}(\Omega) = +\infty$. | Flocq `Bsucc_correct` |
| Radius arithmetic: `radd(a, b)`, `rmul(a, b)` for $a, b \ge 0$ | $\mathrm{next\_up}(a \oplus b) \ge a + b$ and $\mathrm{next\_up}(a \otimes b) \ge ab$, always, at most two ulps above. | **K**, immediate (this is miso2's `addUpAtNearest`) |

**Fast paths**, used only where the instruction is by definition the same function, and only
after the equivalence is tested on that backend: CUDA's `__dadd_rd`, `__dmul_ru`, `__fma_rd`, …
(Phase 0 found no disagreement with the emulation on $4 \cdot 2^{20}$ operations on an RTX 3080 Ti)
and AVX-512's per-instruction static rounding (`_mm512_add_round_pd`).

### Interval

A value is the empty set or a closed interval $[\ell, h]$ with $\ell \le h$, $\ell < +\infty$,
$h > -\infty$, stored as two k-numbers; $\ell = -\infty$ or $h = +\infty$ make it unbounded. Empty
is stored as $(+\infty, -\infty)$. This is the set-based model of IEEE 1788.1-2017, without
decorations; the semantics below were taken from the P1788 drafts
([1788](references.md#ieee-1788)), since the standard itself was not consulted.

- **Containment (all operations).** For nonempty $X, Y$:
  $\{x \circ y : x \in X,\ y \in Y,\ x \circ y \text{ defined}\} \subseteq X \circledcirc Y$.
  An empty operand gives an empty result.
- **Tightness.** For bounded operands and a finite result, each endpoint of the result is within
  $w\,u^k\,|e| + w'\eta$ of the corresponding endpoint $e$ of the exact range.
  For $k = 1$: $w = 0$ for sums (the endpoints are the exact directed roundings, the tightest
  possible) and for products, quotients and square roots outside the underflow band of the table
  above. For $k \ge 2$: the endpoint is the round-to-nearest kernel result moved outward by its
  own proven bound, so the target is $w \le 2c + 3$ with $c$ the constant of the kernel (status **K**).
- **Partial functions** follow 1788: points outside the domain are ignored
  ($\sqrt{[-1, 4]} = [0, 2]$, $\sqrt{[-2, -1]} = \emptyset$).
- **Division by an interval containing zero** is defined: $X / [0, 0] = \emptyset$; otherwise the
  result is the hull of the (possibly two-piece) quotient set, which is a half-line or the whole
  line. `mul_rev_to_pair` returns the two pieces separately, as 1788's function of that name.
- **Products with zero and infinity**: $[0, 0] \cdot X = [0, 0]$ for any nonempty $X$, including
  unbounded ones. The endpoint arithmetic uses $0 \cdot \infty = 0$ for this reason (miso2's
  `mulUpZ`).
- **Comparisons are three-valued.** `less(X, Y)` is *true* when $x < y$ for all $x \in X, y \in Y$,
  *false* when $x \ge y$ for all of them, *unknown* otherwise; same for the other five orderings.
  The set relations of 1788 (`equal`, `subset`, `interior`, `disjoint`, `precedes`, …) are separate
  functions returning `bool`, with the standard's conventions for the empty set.

### Ball

A value is $\{t : |t - c| \le r\}$ with center $c$ a k-number and radius $r \in T$, $r \ge 0$.
Special states: the whole line is $r = +\infty$ with $c = 0$ (a ball cannot represent a
half-line; any unbounded result becomes the whole line); the empty set is $r = \mathrm{NaN}$.

**Statement (each operation).** The center of the result is the round-to-nearest kernel applied
to the centers; the radius is the propagated radius plus the kernel's proven bound, evaluated with
`radd`/`rmul`. For all $x \in X$, $y \in Y$: $x \circ y \in Z$. If the center is not finite the
result is the whole line.

In the table, $\lvert c\rvert^{+}$ is `abs_upper` of a center, and $\delta$ is the kernel's own
error bound evaluated at the new center $c_z$: the operation's `unit` times
$\lvert c_z\rvert^{+}$, plus its `tiny`. The formulas are shown before the rounding up.

| Operation | Radius |
|---|---|
| $X \pm Y$ | $r_x + r_y + \delta$ |
| $X \cdot Y$ | $\lvert c_x\rvert^{+} r_y + \lvert c_y\rvert^{+} r_x + r_x r_y + \delta$ |
| $a \cdot X$, $a \in T$ exact | $\lvert a\rvert\, r_x + \delta$ |
| $X / Y$, $0 \notin Y$ | $\dfrac{\lvert c_x\rvert^{+} r_y + \lvert c_y\rvert^{+} r_x}{m\,(m - r_y)} + \delta$ with $m$ a lower bound of $\lvert c_y\rvert$; the whole line if $0 \in Y$ |
| $\sqrt X$ | $r_x / \sqrt{m - r_x} + \delta$ with $m$ a lower bound of $c_x$ when $m > r_x$; otherwise the ball enclosing $[0, \sqrt{c_x + r_x}]$; empty if $c_x + r_x < 0$ |

**Tightness.** The radius is at most $(1 + 3u)^d$ times the exact value of its formula, with
$d \le 5$ the nesting depth of the formula: only the `radd`/`rmul` steps inflate it. Against exact range arithmetic, midpoint-radius products
overestimate the radius by a factor of at most 1.5 ([Rump99](references.md#rump99)).

Why `Ball` is the cheap enclosure at $k \ge 2$: one k-number kernel and a handful of `T`
operations, against two kernels plus two outward steps for `Interval`.

### BallVector

A value is $\{v \in \mathbb{R}^N : \max_i |v_i - c_i| \le r\}$: $N$ k-number centers and one radius
$r \in T$. It is the max-norm ball of [vdH09](references.md#vdh09) and exactly miso2's
`BallVector` and `Polynomial` representation with k-number centers. The whole space is
$r = +\infty$ with all centers zero (miso2's "void" state).

**Semantics of every kernel.** Let $f$ be the exact map (sum, scaling, dot product, convolution,
matrix-vector product, …). The result $Z$ satisfies $f(X, Y) \subseteq Z$, and its radius is at
least what `Ball` arithmetic would return for each output entry: *a `BallVector` kernel is a
vector of `Ball` operations followed by taking the largest radius*, computed in one fused pass.
A kernel may use a cheaper a priori bound (a norm of the centers times the rounding unit) as long
as that bound dominates the entrywise one; each kernel's reference page states which formula it
uses. Two requirements come from miso2 and are not in the brief's list: `norm_upper` (an upper
bound in $T$ of $\max_i |c_i|$) as a kernel of its own, and a result flag saying whether all
centers stayed finite.

### One interface, and conversions

`Interval<T, k>` and `Ball<T, k>` both provide: `lower`, `upper` (k-numbers), `lower_as<T>`,
`upper_as<T>` (directed conversions), `midpoint`, `radius` (an upper bound in $T$, such that the
set is inside midpoint ± radius), `contains`, `certainly_positive` / `negative` / `zero`, `hull`,
`intersection`, `split`, `is_empty`, `is_entire`. Conversions are outward in both directions:
interval to ball takes the rounded midpoint and a radius covering both ends; ball to interval
computes $c - r$ downward and $c + r$ upward with the kernel that adds a `T` to a k-number. An unbounded
interval becomes the whole-line ball.

## Batch kernels

Bounds are exported as `constexpr` functions of $n$ in Higham's form, with
$\gamma_m(\varepsilon) = m\varepsilon/(1 - m\varepsilon)$ and the precondition
$m\,\varepsilon < 1$ checked at compile time when $n$ is a constant and at run time otherwise.

| Kernel | Bound | Notes |
|---|---|---|
| `sum` of $n$ k-numbers | $\lvert \tilde s - s\rvert \le \gamma_{n-1}(\varepsilon_{+}) \sum \lvert x_i\rvert$ | No underflow term. Holds for any order; the proof is done for the orders actually emitted (sequential and the SIMD lane-then-reduce order). |
| `dot` | $\lvert \tilde s - x^{\mathsf T} y\rvert \le \gamma_n(\varepsilon_{\mathrm{dot}}) \sum \lvert x_i y_i\rvert + n\,\mathrm{tiny}_{\times}$ | |
| `axpy`, elementwise maps | The scalar bound per entry. | |
| `convolution` | The `dot` bound per output coefficient with $n = \min(n_a, n_b)$. | miso2's polynomial product. |
| `gemv`, `gemm` | $\lvert \widetilde{Ax} - Ax\rvert \le \gamma_n(\varepsilon_{\mathrm{dot}})\,\lvert A\rvert\lvert x\rvert + n\,\mathrm{tiny}_{\times}$ entrywise | |
| `sum`/`dot` of $T$ inputs returning a k-number | $\lvert \tilde s - s\rvert \le \gamma^{(k)}_n \sum \lvert x_i\rvert$ with $\gamma^{(k)}_n = O((nu)^k)$, plus $n\,\eta$ for `dot` | The k-fold-precision algorithms of [ORO05](references.md#oro05). |

"Fused" means the loop body keeps an unnormalized accumulator (the error-free transformations
without the final renormalization gates) and normalizes once at the end. That is allowed exactly
where its own proof goes through; $\varepsilon_{\mathrm{dot}}$ and the constants above are then
those of the fused loop, not the product of the scalar constants. All status **K**. An
`Accumulator` type exposes the same fused state to clients for loops Kairn does not provide (for
example miso2's convolutions over multi-indices).

## Decimal input and output

| Operation | Statement |
|---|---|
| `parse` to a k-number | For a decimal (or hexadecimal) literal with value $d$: $\lvert z - d\rvert \le \mathrm{unit}\,\lvert d\rvert + \eta$, with a flag that is true exactly when $z = d$. |
| `parse` to `Interval` / `Ball` | The result contains $d$ (and, for interval literals `[a, b]`, the interval), within the tightness of the conversion above. |
| `print` a k-number with $n$ digits | A decimal $d$ with $\lvert d - x\rvert \le \tfrac12 10^{-n}$ in the last place shown, or all digits (every k-number is a finite decimal). |
| `print` an `Interval` / `Ball` | Lower bound printed downward, upper bound upward: the printed interval contains the value. |
| Hexadecimal form | Exact in both directions (the test corpus uses it exclusively). |

The algorithm is exact integer arithmetic on a fixed-capacity big integer, usable in constant
evaluation. Status **K**; the only formally proved decimal parser found is CompCert's
round-to-nearest `Bparse`.

## Elementary functions

**Statement**, for each function $f$ and each pair $T$, $k$. For $x$ in the stated domain,
$|\tilde f(x) - f(x)| \le c_f\,u^k\,|f(x)| + \mathrm{tiny}_f$; the `Interval` and `Ball` versions
enclose $f$ over the whole operand. Planned set: `exp`, `expm1`, `log`, `log1p`, `log2`, `log10`,
`sin`, `cos`, `tan`, `sinpi`, `cospi`, `asin`, `acos`, `atan`, `atan2`, `sinh`, `cosh`, `tanh`,
`pow`, `cbrt`.

Each proof has three parts: constants ($\pi$, $\ln 2$, tables) as $(k+2)$-limb numbers with
errors bounded by exact rational computation; argument reduction, including large trigonometric
arguments; and polynomial approximation, with the remainder bounded by CoqInterval and the
evaluation error by composing the operation bounds.

**A relaxation to flag now**: these proofs cannot be parametric in $p$. Polynomial degrees,
coefficients and tables are chosen per target precision, so each $(f, T, k)$ is a separate checked
proof. All of them start `UNVERIFIED` and none is released before its proof is checked.

## Flush-to-zero (Metal)

The statements above are for model G. For Metal each kernel has a second theorem under model Z:
the same shape with $\eta$ replaced by $\lambda$, with $t$ counting *every* operation of the
network (a sum can now lose up to $\lambda$ too, so `TwoSum` is error-free only when no
intermediate is below $\lambda$), and with "normalized" strengthened to "every nonzero limb is at
least $\lambda$ in magnitude". Comparison rescales operands near $\lambda$ by an exact power of two
before subtracting, so that a nonzero difference cannot be flushed. Values with subnormal limbs
passed to a Metal kernel are read by the device as zeros; that is a documented precondition, not
something a proof can repair. All status **K**; nothing about expansions under flush-to-zero
exists in the literature, and Flocq's `FTZ` format is not a usable base
([Verification](verification.md#underflow-models)).
