# Numbers: representation, invariant, special values, range

This page fixes what a k-number *is*. Everything else in the report (theorems, proofs, tests, the
API) refers to the definitions here.

## Notation

A limb type $T$ is an IEEE 754 binary format with precision $p$:

| | $p$ | $u = 2^{-p}$ | smallest subnormal $\eta$ | smallest normal $\lambda = 2^{p-1}\eta$ | largest finite $\Omega$ |
|---|---|---|---|---|---|
| `float` | 24 | $2^{-24}$ | $2^{-149}$ | $2^{-126}$ | $(2-2^{-23})\,2^{127}$ |
| `double` | 53 | $2^{-53}$ | $2^{-1074}$ | $2^{-1022}$ | $(2-2^{-52})\,2^{1023}$ |

- $\mathbb{F}$ is the set of finite numbers of the format: $M \cdot 2^{q}$ with integers $|M| < 2^p$
  and $q \ge \log_2 \eta$, up to $\Omega$.
- $\mathrm{RN}(t)$ is $t$ rounded to the nearest element of $\mathbb{F}$, ties to even, and
  $\pm\infty$ when $|t| \ge \Omega + \tfrac12\mathrm{ulp}(\Omega)$ (the IEEE overflow rule). It is
  the only rounding Kairn ever uses.
- $\mathrm{ulp}(x) = 2^{\max(\lfloor \log_2 |x| \rfloor - p + 1,\ \log_2\eta)}$ for $x \ne 0$: the
  gap between consecutive numbers of the format around $x$.
- $\mathrm{succ}(x)$ and $\mathrm{pred}(x)$ are the next number of the format above and below $x$.

Two **underflow models** appear in the theorems:

- **G (gradual underflow)**: IEEE arithmetic. Every operation returns $\mathrm{RN}$ of its exact
  result. This is the model of every CPU backend and of CUDA.
- **Z (flush to zero)**: an operand smaller than $\lambda$ in magnitude may be read as zero, and a
  result whose exact value is smaller than $\lambda$ in magnitude may be returned as zero instead
  of $\mathrm{RN}$ of it; the sign of such a zero is unspecified. "May" is a nondeterministic
  choice made per operation, so that one statement covers every hardware convention. This is the
  model of Metal ([measured](environment.md#metal): the M3 GPU reads subnormal operands as zero and
  flushes before rounding).

## A k-number

A **k-number** over $T$ is a sequence of $k \ge 1$ limbs $x = (x_0, \dots, x_{k-1})$, each a value
of type $T$, most significant first. Its **value** is the exact real sum
$x_0 + x_1 + \dots + x_{k-1}$, written $x$ again when no confusion arises. `Expansion<T, k>` stores
exactly these $k$ limbs and nothing else.

### The normalization invariant

**Definition (normalized).** A k-number with finite limbs is *normalized* when

$$x_i = \mathrm{RN}(x_i + x_{i+1}) \qquad \text{for } i = 0, \dots, k-2 .$$

In words: adding the next limb to a limb and rounding gives the limb back. For $k = 1$ the
condition is empty: every finite `T` is a normalized 1-number. For $k = 2$ this is the definition
of a double-word number used by every formal proof in the literature
([JMP17](references.md#jmp17), [MR22](references.md#mr22)); for general $k$ it is the *strongly
nonoverlapping* condition of [Zhang's thesis](references.md#zhang-thesis), under which the only
known branch-free 3- and 4-limb algorithms are stated.

**Consequences** (each is a short lemma; they will be the first entries of the proof library):

1. $|x_{i+1}| \le \tfrac12 \mathrm{ulp}(x_i)$ and $|x_{i+1}| \le u\,|x_i|$. (If $x_i$ is subnormal
   then $x_{i+1} = 0$, because sums in the subnormal range are exact.) When $x_i$ is a power of
   two and $x_{i+1}$ has the opposite sign, the first bound tightens to
   $\tfrac14 \mathrm{ulp}(x_i)$.
2. Zeros are at the end: $x_i = 0$ implies $x_{i+1} = 0$. There are no interleaved zeros.
3. The sign of the value is the sign of $x_0$, and the value is zero exactly when $x_0 = 0$.
4. $|x - x_0| \le \frac{u}{1-u}\,|x_0|$, so $x_0$ approximates $x$ with relative error below $2u$.
5. A prefix $(x_0, \dots, x_{j-1})$ is a normalized j-number, and dropping the rest changes the
   value by at most $\frac{u^{j}}{1-u}\,|x_0|$.
6. The invariant is decidable exactly with $k - 1$ floating-point additions and comparisons:
   `x[i] + x[i+1] == x[i]`. `kairn::is_normalized` does that, and debug builds assert it on every
   operand.

**What it does not give, from three limbs on.** For $k = 2$ the invariant says
$x_0 = \mathrm{RN}(x)$, so the representation is unique and comparing limbs in order compares
values. For $k \ge 3$ neither holds: $1 + u + u^2$ is both $(1,\ u,\ u^2)$ and
$(1 + 2u,\ -u(1-u),\ 0)$, and both are normalized. Two consequences for $k \ge 3$:

- Comparing limbs lexicographically is **not** an exact comparison (the example compares
  $1 < 1 + 2u$ on the first limb for two equal values). Exact comparison is an operation with its
  own algorithm and theorem ([Operations](operations.md#comparisons-and-sign)).
- $x_0$ is not always the correct rounding of $x$ to $T$ (a tie on $x_0 + x_1$ is broken by
  $x_2$). Directed and nearest conversions to $T$ are operations too.

### Why this invariant

| Candidate | Condition | Why not |
|---|---|---|
| Priest (P) | $\lvert x_{i+1}\rvert < \mathrm{ulp}(x_i)$ | Used by triple-word arithmetic ([FMP19](references.md#fmp19)), whose algorithms need data-dependent tests to restore it. |
| ulp (CAMPARY) | $\lvert x_{i+1}\rvert \le \mathrm{ulp}(x_i)$ | Weakest; the proven CAMPARY addition bound is relative to $\lvert x\rvert + \lvert y\rvert$, not to the result, and renormalization branches ([JMMP16](references.md#jmmp16)). |
| Bailey / QD | $\lvert x_{i+1}\rvert \le \tfrac12\mathrm{ulp}(x_i)$ | Implied by ours. QD's own paper says its renormalization "remains to be proven" ([QD](references.md#qd)). |
| **Strong (ours)** | $x_i = \mathrm{RN}(x_i + x_{i+1})$ | — |
| Canonical | $x_i = \mathrm{RN}(x_i + \dots + x_{k-1})$ | Unique and lexicographically ordered, but no known fixed network restores it for $k \ge 3$ (a tie can be decided by the last limb). |

The strong invariant is what `Fast2Sum` and `TwoSum` return for free, it is the hypothesis and the
conclusion of every machine-checked double-word theorem, it is the strongest of the non-canonical
notions (a theorem proved under a weaker hypothesis applies to our inputs), and it can be checked
exactly at run time. **Decision [D4](decisions.md#d4-normalization-invariant) asks you to confirm
it.**

### Zero and signs

- Zero is the k-number with all limbs zero (consequence 2 makes this the only normalized zero up
  to the signs of the limbs).
- The sign of a zero limb is **unspecified**: $+0$ and $-0$ limbs are both valid and compare
  equal. Kairn's networks do not preserve the sign of a zero (a `TwoSum` of two negative zeros returns
  a negative and a positive zero), and making them do so would cost operations on every path.
- `sign(x)` returns $-1$, $0$ or $+1$ from $x_0$; `signbit`-style queries on a zero are not
  provided.

### Non-finite values

**Definition.** A k-number is *finite* when $x_0$ is finite. Every operation maintains one
more invariant: if any limb is not finite, then $x_0$ is not finite. So `isfinite(x)` reads one limb.
This holds by construction: the generator checks that every intermediate value of a network
reaches the first output limb through additions, subtractions, products and FMAs, all of which
keep a NaN and turn an infinity into an infinity or a NaN
([Verification](verification.md#generator)).

Canonical non-finite forms are $(+\infty, 0, \dots, 0)$, $(-\infty, 0, \dots, 0)$ and
$(\mathrm{NaN}, \dots, \mathrm{NaN})$. `Expansion<T, k>(T x)` produces them from a non-finite `T`.

How arithmetic treats them is the one semantic choice in this page with a measurable cost, and it
is yours to make ([D5](decisions.md#d5-non-finite-results)):

| | **IEEE-like (recommended default)** | **Sticky (opt-in `kairn::finite::` variants, and inside batch kernels)** |
|---|---|---|
| Non-finite operand | Result is the canonical form of the IEEE operation on the leading limbs ($+\infty + 1 = +\infty$, $\infty - \infty = \mathrm{NaN}$, $0 \cdot \infty = \mathrm{NaN}$). | Result is not finite; which non-finite value is unspecified. |
| Overflow on finite operands | $\pm\infty$ with the sign of the exact result. | Result is not finite. |
| Cost over the bare network | One finiteness test of the result and $k$ selects. Estimated 10 to 20% on a 2-limb addition, less on larger networks; to be measured in Milestone 1. | None. |
| Used by | Scalar generic code, `Interval` endpoints (unbounded intervals need $\pm\infty$ arithmetic). | Batch kernels, which canonicalize once at the end; `Ball` and `BallVector`, which test the center once per operation and turn a non-finite center into an infinite radius. |

In both variants a finite result carries the full guarantee: **either the first limb of the
result is not finite, or the result is normalized and satisfies the operation's bound.** No
operation ever returns a finite wrong value because an intermediate overflowed.

### Requires and guarantees

Every core operation has the same contract shape; the per-operation statements are in
[Operations](operations.md).

- **Requires**: each operand is normalized or a canonical non-finite value. For batch kernels:
  the floating-point environment is the default one ([Environment](environment.md)).
- **Guarantees**: the result is normalized or canonical non-finite; if finite it satisfies the
  operation's proven bound; the operation has no side effects and touches no global state.
- **Operands that are finite but not normalized** (possible only through the unchecked
  constructor from limbs): no undefined behavior, no trap; the result is some k-number with no
  accuracy or normalization guarantee. `renormalize` is the operation that accepts such input
  ([Operations](operations.md#conversions-and-scaling)).

## Precision depends on magnitude

A normalized k-number has its limbs at least $p$ binades apart, so a number near $|x| = 1$ can
have at most 21 nonzero `double` limbs or 7 nonzero `float` limbs (the brief's "about 20" and
"about 6"): at magnitude $2^E$ the count is $\lfloor (E - \log_2\eta)/p \rfloor + 1$. More to the
point, every bound has the form

$$|\text{computed} - \text{exact}| \le \mathrm{unit} \cdot |\text{exact}| + \mathrm{tiny},
\qquad \mathrm{unit} \approx c\,u^k, \quad \mathrm{tiny} \approx t\,\eta \ \text{(model G)}\ \text{or}\ t\,\lambda \ \text{(model Z)},$$

and the k-number delivers its full $k\,p$ bits only where the relative term dominates.

- **Model G**: the absolute term is of the order of $\eta/2$, so the threshold is
  $|x| \ge 2^{kp-1}\,\eta$. This is also exactly where the last limb's unit in the last place
  reaches $\eta$; for $k = 1$ it is $\lambda$, and for $k = 2$ it is the `TwoProd` exactness
  threshold of [Operations](operations.md#building-blocks). Below it a value with
  $2^E \le |x| < 2^{E+1}$ has $\min(k\,p,\ E - \log_2\eta + 1)$ bits: one bit is lost per binade.
- **Model Z**: the absolute term is of the order of $\lambda$, so the threshold is
  $|x| \ge 2^{kp}\lambda$ and below it there are $\min(k\,p,\ E - \log_2\lambda)$ bits. The
  exception is $k = 1$: a normal result is never flushed, so plain `float` keeps its 24 bits down
  to $\lambda$.

The table is computed by
[`experiments/phase0/ranges/ranges.py`](https://github.com/danielepanozzo/kairn/blob/main/experiments/phase0/ranges/ranges.py)
and ignores the small constants $c$ and $t$.

| T | k | bits ($k\,p$) | decimal digits | full precision for $\lvert x\rvert \ge$ (G: CPU, CUDA) | (Z: Metal) | bits at $\lvert x\rvert = 10^{-30}$ (G) | (Z) |
|---|---|---|---|---|---|---|---|
| double | 1 | 53 | 16.0 | $2^{-1022} \approx 2.2\cdot10^{-308}$ | — | 53 | — |
| double | 2 | 106 | 31.9 | $2^{-969} \approx 2.0\cdot10^{-292}$ | — | 106 | — |
| double | 3 | 159 | 47.9 | $2^{-916} \approx 1.8\cdot10^{-276}$ | — | 159 | — |
| double | 4 | 212 | 63.8 | $2^{-863} \approx 1.6\cdot10^{-260}$ | — | 212 | — |
| double | 8 | 424 | 127.6 | $2^{-651} \approx 1.1\cdot10^{-196}$ | — | 424 | — |
| float | 1 | 24 | 7.2 | $2^{-126} \approx 1.2\cdot10^{-38}$ | $2^{-126} \approx 1.2\cdot10^{-38}$ | 24 | 24 |
| float | 2 | 48 | 14.4 | $2^{-102} \approx 2.0\cdot10^{-31}$ | $2^{-78} \approx 3.3\cdot10^{-24}$ | 48 | 26 |
| float | 3 | 72 | 21.7 | $2^{-78} \approx 3.3\cdot10^{-24}$ | $2^{-54} \approx 5.6\cdot10^{-17}$ | 50 | 26 |
| float | 4 | 96 | 28.9 | $2^{-54} \approx 5.6\cdot10^{-17}$ | $2^{-30} \approx 9.3\cdot10^{-10}$ | 50 | 26 |

Metal has no `double`, so the Z column applies to `float` only. What the table says in practice:

- **`double` limbs** have full precision over an enormous range at every baked-in $k$; the
  underflow term matters only for adversarial inputs.
- **`float` limbs lose precision at magnitudes that occur in real data.** `Expansion<float, 4>`
  keeps its 96 bits only above about $10^{-16}$ on CUDA and only above about $10^{-9}$ on Metal.
  A quantity near $10^{-30}$ has at most 50 bits on CUDA and 26 on Metal, however large $k$ is. This is a
  property of the format, not of the algorithms, and no implementation can avoid it; the cure is
  for the client to scale its data (exact scaling by powers of two is provided). The getting-started
  page on choosing $T$ and $k$ will lead with this table, and it is part of the
  float-versus-double recommendation for CUDA ([Plan](plan.md#performance-targets)).
- **Runtime k** is useful up to $\lfloor (E - \log_2\eta)/p \rfloor + 1$ limbs at magnitude
  $2^E$: 21 `double` or 7 `float` limbs near 1, 40 or 12 at the top of the range. The runtime-k
  path rejects larger $k$ at construction rather than carry limbs that cannot hold bits.

### The top of the range

Flocq's formats, and therefore the proofs, have no largest exponent. The connection to real
arithmetic is the dichotomy stated above (*finite first limb implies the bound*) plus, for each
operation, a **no-spurious-overflow** lemma: if the operands and the exact result are at most
$\Omega_{\mathrm{safe}}$ in magnitude then the result is finite. The safe threshold is an output
of each proof, and it has to be a condition on the operands too, not only on the result: a
`TwoSum` whose first operand is exactly $\pm\Omega$ can return a NaN error term although its sum
is finite ([BGM17](references.md#bgm17); with $x = \Omega$ and $y \approx -\Omega/2$ the 2-limb
addition returns NaN for an exact result of $\Omega/2$). The target is
$\Omega_{\mathrm{safe}} = \Omega/4$ for additions, and where the leading product overflows for
products. Between $\Omega_{\mathrm{safe}}$ and $\Omega$ a result is either correct or not finite.
The compile-time path is narrower: Dekker's product splits a limb by multiplying it by
$2^{\lceil p/2 \rceil} + 1$, which overflows for limbs above about $2^{997}$ in `double` (the
published sufficient condition is $2^{995}$, [BM11](references.md#bm11)), so the
constant-evaluation variant rescales by an exact power of two first; that rescaling is part of
the kernel and of its proof.

## Other number types

They are defined in [Operations](operations.md#enclosures); in one line each:

- `Interval<T, k>`: a closed, connected set of reals stored as two k-numbers (lower, upper), with
  an empty set and unbounded intervals, following the set-based flavor of IEEE 1788.1 without
  decorations.
- `Ball<T, k>`: the set $\{t : |t - c| \le r\}$ with a k-number center $c$ and a radius $r \ge 0$
  of type $T$.
- `BallVector<T, k>`: $N$ k-number centers $c_i$ and one radius $r$ of type $T$: the set of
  vectors $v$ with $\max_i |v_i - c_i| \le r$.
