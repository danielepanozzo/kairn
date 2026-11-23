# Proofs

Every bound that this site calls *proved* is a theorem checked by the proof assistant
[Rocq](https://rocq-prover.org), with [Flocq](https://flocq.gitlabpages.inria.fr/), its library of
floating-point arithmetic. This page says how to check the proofs yourself, what the check prints,
which axioms the proofs rest on, and in which model of arithmetic each statement holds. The
[reference](../reference/index.md) gives, for every operation, the statement in plain mathematics
next to the same statement as Rocq reads it, and the name and file of its theorem.

## Check them yourself

You need Rocq 9.0, Flocq 4.2 and Python 3. The CI uses Rocq 9.0.1 and Flocq 4.2.2
([`proofs.yml`](https://github.com/danielepanozzo/kairn/blob/main/.github/workflows/proofs.yml)).
The proofs do not need anything else from the repository, and no C++ compiler.

**With the container image the CI uses.** From the root of a checkout, with Docker:

```sh
docker run --rm -it --user root -e OPAMROOT=/home/rocq/.opam -e OPAMROOTISOK=1 \
    -v "$PWD":/kairn -w /kairn rocq/rocq-prover:9.0 bash
# then, inside the container:
opam install -y coq-flocq.4.2.2       # a minute or two
opam exec -- make -C proofs -j4
```

The image is the Rocq team's; the workflow pins it by digest. It runs as root because the image's
own user cannot write a directory mounted from the host, and `OPAMROOT` points opam at the
installation the image ships. The files the build writes into `proofs/` then belong to root;
`make -C proofs clean`, in the container, removes them.

**With opam.** Install Rocq 9.0 (the opam package `rocq-prover`), then Flocq 4.2
(`opam install coq-flocq.4.2.2`, the version of the CI), and run `make -C proofs -j4` in a shell
where `rocq` is on the `PATH`.

A full build and audit takes a minute or two with four cores. `make -C proofs build` builds without
the audit, `make -C proofs audit` builds and audits, and `make -C proofs clean` removes what the
build wrote.

## What `make -C proofs` does

It builds every file that [`proofs/_CoqProject`](https://github.com/danielepanozzo/kairn/blob/main/proofs/_CoqProject)
lists:

- `proofs/gen/Model.v` and `proofs/gen/Statements.v`, which the generator writes from the kernel
  descriptions: a model of each kernel over the real numbers, and the statement of its claims;
- `proofs/gen/IeeeModel.v` and `proofs/gen/IeeeStatements.v`, generated too: each kernel as a
  function of Flocq's binary floating-point numbers, where operations overflow and operands may
  be infinite or NaN, and its statements there;
- `proofs/gen/IeeeWith.v`, generated too: each kernel that is `constexpr` by the rule of the
  product, in the same model with the operations that constant evaluation computes otherwise as
  arguments (the product, and the guard and the multiplication by infinity of a fix-up where the
  kernel has them), so that the same listing stands for its execution at run time (the fused
  product, the guard that adds $+0$, the multiplication) and in constant evaluation (the plain
  product, the guard that returns its operand, the comparisons of `times_inf_ce`, defined there
  from the C++);
- `proofs/gen/FoldModel.v` and `proofs/gen/FoldStatements.v`, generated too: each fold (a loop
  of kernels along arrays: the sums, the dot products and the largest magnitude) as a function
  on lists, in the two orders in which the library runs it, and its statement in each order;
  each map (a loop that writes an array) as the list of the elements it writes, and each
  convolution (the product of two polynomials) as the list of its coefficients, with one
  statement each;
- `proofs/gen/IeeeFoldModel.v` and `proofs/gen/IeeeFoldStatements.v`, generated too: each fold
  as a function on lists of Flocq's binary floating-point numbers, with its finish, in the same
  two orders; its statement in each order; and, for each kernel that is the step or the
  combination of a fold, the statement that the leading limb of its result is finite only if
  those of its operands are;
- `proofs/theories/`, the proofs written by hand, one theorem `K_correct` per kernel `K` and the
  lemmas they share, the theorems about sums and dot products of arrays, which bound a sum
  made in any order of its additions (`Folds.v`, `Summation.v`, `SummationKernels.v`), and the
  first building blocks of Milestone 2: a sum and a product rounded down and up without a
  rounding mode, over the real numbers (`DirectedSum.v`, `DirectedProd.v`) and with overflow,
  infinities and NaN (`IeeeDirected.v`, `IeeeDirectedProd.v`), the neighbors of a number and the
  building blocks that guard their operands (`EntryKernels.v`, `IeeeEntry.v`), the scaling of a
  ball by a power of two over the real numbers (`BallPow2.v`) and, with the special states of a
  ball, with overflow, infinities and NaN (`IeeeBallPow2.v`), the lemma that the product of two
  intervals rests on (`Rectangle.v`), the comparison of the two ways a product is executed
  (`IeeeProduct.v`), with what follows for the 66 kernels whose C++ computes an operation
  otherwise in constant evaluation (the thirty whose only fused operations are products, and 36
  without a product that guard an operand or fix up with `times_inf`), which are `constexpr`: on
  all operands each listing as constant evaluation runs it
  (the plain product, the guard that returns its operand, `times_inf` from comparisons) returns
  outputs of the same values, and the same masks, as the kernel of run time (the fused product,
  the guard that adds $+0$, the multiplication by infinity) (`IeeeTwoExecutions.v`, one theorem
  `K_two_executions` per kernel `K` of `IeeeWith.v`; and for `two_prod` and its entry form
  `two_prod_entry`, which guards its operands at run time (rule R3, the factors of a fused
  operation), `constexpr` through Dekker's product, the same values only when the error term of
  constant evaluation is finite and the product is exact, `two_prod_two_executions_exact` and
  `two_prod_entry_two_executions_exact`), the interval kernels with bounds of one
  limb, on all values:
  the constructor, the negation, the sum, the difference and the product (`IeeeInterval1.v`,
  with the definitions their statements use in `IeeeIntervalVocabulary.v`), and the bounds of
  two limbs over the real numbers: a sum, a difference and a product of two 2-limb numbers,
  moved down or up by a bound of their own error, with how far that moves them
  (`Directed2.v`), and, with overflow, infinities and NaN, the sum of two intervals whose
  bounds have two limbs (`IeeeInterval2.v`) and the conversions of a ball: its bounds as
  numbers of the limb type, the ball of one limb that contains a ball of two, and the ball
  made from an interval of two numbers (`IeeeBallConvert.v`), and the exact interval kernels:
  the negation and the constructor of an interval whose bounds have two limbs, and the hull
  and the intersection of two intervals with bounds of one and of two limbs
  (`IeeeIntervalExact.v`), the difference of two intervals whose bounds have two limbs
  (`IeeeIntervalSub2.v`), the conversions between an interval and a ball of one limb, with
  the midpoint and the radius of an interval and its split at the midpoint
  (`IeeeIntervalConvert.v`), and the product of two intervals whose bounds have two limbs,
  with the product of two bounds on all values (`IeeeIntervalMul2.v`), and the predicates, the
  three-valued comparisons and the relations of IEEE 1788 of intervals with bounds of one and
  of two limbs, all exact (`IeeeIntervalPredicates.v`), and the predicates and the three-valued
  comparisons of balls with a center of one limb, on exact pairs (`IeeeBallPredicates.v`), and
  the ball of one limb made from an interval of two numbers and the split of a ball of one
  limb (`IeeeBallSets.v`), the signs and the split of a ball with a center of two limbs
  (`IeeeBallPredicates2.v`), and the interval of a ball of two limbs, the sum of [c, c] and
  [-r, r] (`IeeeBallConvert2.v`), and the comparisons of balls of two limbs, certain, by the
  distance of the centers that add_ball_2_2 bounds (`IeeeBallCompare2.v`), and the sum of two
  2-limb numbers at the top of the range: it does not overflow when the leading limbs of both
  operands are at most half the largest finite number, a threshold that cannot be raised
  (`IeeeAdd22Top.v`), and the midpoint and a radius of an interval with bounds of two limbs,
  with the ball made of them and the split of the interval at its midpoint
  (`IeeeIntervalConvert2.v`), and whether a ball of two limbs contains a point of two limbs
  (`IeeeBallContains2.v`), and the hull and the intersection of two balls with a center of one
  limb and of two (`IeeeBallHull.v`); and the theorems of
  the
  folds, `F_seq_correct` and `F_lanes_correct` per fold `F` (`FoldSums.v`), of their steps,
  finishes and bound kernels
  (`StepKernels.v`, `IeeeFoldFinish.v`, `BoundKernels.v`), of the two together
  (`FoldGuarantee.v`), and of the folds and their steps in the model with overflow
  (`FoldTransfer.v`, `IeeeSteps.v`, `IeeeFolds.v`; [below](#sums-and-dot-products-of-arrays));
  the theorems of the maps, `F_correct` per map `F`, and of their steps (`FoldMaps.v`,
  `MapSteps.v`), and of the maps and their steps in the model with overflow
  (`IeeeFoldMaps.v`, `IeeeMapSteps.v`; [below](#loops-that-write-an-array)); of the largest
  magnitude of an array and
  its kernels, over the real numbers and with overflow, infinities and NaN (`FoldNorm.v`,
  `IeeeFoldNorm.v`; [below](#the-largest-magnitude-of-an-array)); of the product of two
  polynomials, over the real numbers and with overflow, infinities and NaN (`FoldConv.v`,
  `IeeeFoldConv.v`; [below](#the-product-of-two-polynomials)); of the radius kernels of the
  ball vectors and of the ball vectors themselves, over the real numbers (`BvRadius.v`,
  `BvReal.v`), and with overflow, infinities and NaN (`IeeeBv.v`), and of the negation and
  the constructor of a ball vector and its scaling by a power of two, in both models
  (`BvNegMake.v`, `IeeeBvNegMake.v`, `BvPow2.v`, `IeeeBvPow2.v`), and of the product of two ball
  vectors over the real numbers, and with overflow its finish, V1 to V3 of both products and V4
  of the product of one limb (`BvConv.v`, `IeeeBvConv.v`, `IeeeBvConvFinite.v`;
  [below](#ball-vectors)); and of the
  kernels of
  the accumulator and what a user of it relies on, over the real numbers and with overflow,
  infinities and NaN (`AccKernels.v`, `IeeeAccKernels.v`, `Accumulator.v`,
  `IeeeAccumulator.v`; [below](#the-accumulator));
- `proofs/third_party/mr22/`, five files of the machine-checked proofs of double-word additions by
  Muller and Rideau ([MR22](../developer/design/phase0/references.md#mr22), MIT license), which the
  proofs of the two additions use
  ([`MODIFICATIONS.md`](https://github.com/danielepanozzo/kairn/blob/main/proofs/third_party/mr22/MODIFICATIONS.md)
  says what was taken and changed).

Then it runs the audit, in four steps, each of which stops the build on a failure:

1. **A text scan** of every one of those files: none may contain, outside comments and strings, a
   word that introduces an unproved statement (`Admitted`, `admit`, `Axiom`, `Parameter`, and
   their plural and synonymous forms).
2. **The theorems of the generated statements.** `proofs/gen/Audit.v` has, for every kernel that
   is not UNVERIFIED, a definition `K_audit : K_spec := K_correct`, which compiles only if the
   theorem has exactly the generated statement as its type, followed by
   `Print Assumptions K_correct`; the same two lines for each order of every fold that is
   proved (`F_seq_audit : F_seq_spec := F_seq_correct`, and `F_lanes`), and once for every map
   and convolution, which have one statement (`F_audit : F_spec := F_correct`); then the three
   statements of `conv_terms`, which the convolutions share, whose file they name. A script,
   `proofs/audit/audit.py`, reads what Rocq printed and fails on any axiom outside the allowed
   list, on a missing report, or on any output it does not understand.
3. **The theorems that the generated audits do not list**, the same way, from
   `proofs/audit/HandAudit.v`: the IEEE-model theorems of the kernels of Milestone 1 and of
   the first building blocks of Milestone 2 that also have a real-model statement of their own
   domain (these have generated statements as their types, checked by a definition of the same
   form; their descriptions do not name them yet),
   a few facts whose statements are written by hand because they say more about a kernel than
   its claims can express (among them that the sum of two 2-limb numbers does not overflow up
   to half the range, where its claim says a quarter), the theorems about sums and dot
   products of arrays, which are
   about no single kernel, and the lemmas of the first building blocks of Milestone 2 that are
   not generated statements, among them what is proved of `mul_dir_1`, of the interval
   kernels with bounds of one limb, of the bounds of two limbs, of the sum of two intervals
   of two limbs, of the conversions of a ball, of the exact interval kernels (the hull and
   the intersection of intervals of extended real numbers), of the difference of two
   intervals of two limbs (the sum with the negated operand), of the conversions between an
   interval and a ball (the midpoint of a bounded interval; for bounds of two limbs, the half
   of a 2-limb number, the midpoint, each side of the radius and the point of the split), of
   the product of two
   intervals of two limbs (the finite core of the directed product, and what each product of
   bounds gives) and of the predicates and comparisons of intervals and of balls of one limb
   (each relation on the bounds as extended real numbers, and the exact pairs of two_sum_ord),
   and of the hull and the intersection of balls (the tests of the radii, and that the ball of
   a canonical interval contains its members)
   beside their generated
   statements, those about the two executions of a product and the lemmas of the two
   executions of the kernels `constexpr` by its rule, on the listings of
   `proofs/gen/IeeeWith.v`, the theorems about the folds, the
   largest magnitude and the product of polynomials whose statements are written by hand
   ([below](#sums-and-dot-products-of-arrays)),
   the lemmas of the radius of the accumulator and what a user of it relies on
   ([below](#the-accumulator)), and the lemmas of the ball vectors in the model with overflow
   ([below](#ball-vectors)).
4. **A negative control**: `proofs/audit/Bad.v`, a false theorem closed with `Admitted`, must be
   rejected by both checks.
5. **The IEEE-model theorem of every kernel that accepts infinite and NaN operands**, from the
   generated `proofs/gen/IeeeAudit.v`, like step 2; then, in the same file, every other
   IEEE-model theorem that a description names: those of the steps and the combinations of
   the folds and of the steps of the maps (and of the two steps of the extended domain that
   have one, `neg_2`, `bv_center_2` and `bv_center_entry_2`), of the folds and the maps in their two orders, of the
   two statements more of the folds of maxima, of the convolutions and of the products of two
   BallVectors; and last, for each kernel whose C++ dispatches on constant evaluation (64), the theorem
   of its two executions (`IeeeTwoExecutions.v`) against the statement the generator prints
   for it in `proofs/gen/IeeeWith.v`, `K_two_executions_spec`, which no description names.

What it prints, after the compilation lines, shortened where it says `...` (a run of this version):

```text
== text scan of the proof files
  115 files: no Admitted, admit, Axiom or Parameter
== assumptions of every theorem that establishes a generated statement
  ok           add_1_1_correct: 4 axioms
      allowed      ClassicalDedekindReals.sig_forall_dec
      allowed      ClassicalDedekindReals.sig_not_dec
      allowed      Classical_Prop.classic
      allowed      FunctionalExtensionality.functional_extensionality_dep
  ok           rmul_correct: 4 axioms
  ...
== assumptions of the theorems that the generated audits do not list (audit/HandAudit.v)
  ...
== negative control: a false theorem closed with Admitted must be rejected
  rejected by the text scan, as it must be
  REJECTED     wrong: 1 axioms
      NOT ALLOWED  wrong
  rejected by the assumption check, as it must be
== assumptions of the IEEE-model theorem of every kernel of the extended domain
  ...
== audit passed
```

Each theorem gets a line `ok` or `REJECTED`, with the axioms its proof depends on, each marked
`allowed` or `NOT ALLOWED`; in the control, the admitted theorem `wrong` shows up as an axiom named
after itself, which is how an unfinished proof is caught. In this version most audited theorems
depend on all four axioms. Some depend on two of them only, among them the summation theorems
that use real numbers and nothing of Flocq; the theorems about lists and trees alone depend on
none, and the audit prints `closed under the global context` for them.

A kernel's status in `gen/claims.json` is `proved` only when this audit passes for its theorem,
and the CI runs it on every push and pull request. It keeps what the audit printed as the
artifact `proof-audit` of each run of the
[Proofs workflow](https://github.com/danielepanozzo/kairn/actions/workflows/proofs.yml):
`make.log`, the whole output of `make -C proofs`, with the axioms of every audited theorem, and
the files `audit/*.out`, what Rocq printed for each audit file. The reference page of a kernel
names its theorems and the allowed axioms, and points to that artifact for the axioms of each
theorem, which only a run of Rocq computes.

## The four axioms

Rocq's real numbers are not constructive: proofs about them rest on axioms of Rocq's standard
library. The audit allows exactly four, the ones Phase 0 found under every theorem about real
numbers it checked ([Verification](../developer/design/phase0/verification.md#axiom-policy-for-ci));
Flocq adds none. A fifth would need the owner's approval
([D1](../developer/design/phase0/decisions.md#d1-proof-assistant)).

| Axiom | In the standard library | What it says |
|---|---|---|
| `ClassicalDedekindReals.sig_forall_dec` | the construction of the real numbers | for a decidable property of the natural numbers, either it holds for every $n$, or an $n$ for which it fails can be found |
| `ClassicalDedekindReals.sig_not_dec` | the construction of the real numbers | for every proposition $P$, one can decide between "not $P$" and "not not $P$" |
| `FunctionalExtensionality.functional_extensionality_dep` | the functional extensionality module | two functions that agree on every argument are equal |
| `Classical_Prop.classic` | classical logic | every proposition is true or false (the excluded middle) |

The list is in
[`proofs/audit/allowed_axioms.txt`](https://github.com/danielepanozzo/kairn/blob/main/proofs/audit/allowed_axioms.txt).

## What is proved, and in which model

**The bounds are proved over the real numbers.** The generated model describes each kernel as a
function of real numbers in which every operation returns its exact result rounded to the nearest
number of a binary format, with ties to even and gradual underflow. A statement holds for every
precision from the kernel's minimum on and for every exponent range, with exponents unbounded
above, so that nothing overflows: from numbers of the format that satisfy the requirements, it
concludes that the outputs are numbers of the format and satisfy the claims. This is where every
error bound, normalization, exact comparison, rounding and ball containment of the reference is
proved, for every kernel of `gen/claims.json` whose status is `proved`. For `double` and `float` it
is the guarantee whenever no operation inside the kernel overflows.

**What happens at overflow and with infinities and NaN is proved in Flocq's model of IEEE 754.**
There, values are Flocq's binary floating-point numbers, with signed zeros, infinities and NaN,
and the operations overflow as the hardware does, for formats shaped like `binary32` and
`binary64`. Four kinds of statements are proved there:

- For the arithmetic kernels of two limbs: an overflow anywhere in the kernel never produces a
  finite wrong result (if the leading limb of the result is finite, the result is normalized and
  within its bound), and the result is finite under a stated condition on the operands
  ([Milestone 1 statements](../developer/design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)).
- For the layer that gives overflow and non-finite operands a defined result
  ([IEEE-like results](../developer/design/milestone1.md#ieee-like-results),
  [Ball kernels](../developer/design/milestone1.md#ball-kernels)): the full kernels return
  canonical values, the signed infinity on overflow, and what the operation of the limb type
  returns for non-finite operands; comparisons, conversions and constructors behave as stated on
  infinities and NaN; a Ball operation contains every result in every case, the whole line
  and the empty set included; and it returns a finite ball, not the whole line, under a stated
  condition on its operands
  ([when the result is a finite ball](../developer/design/milestone1.md#when-the-result-is-a-finite-ball)).
- For the interval kernels, whose bounds may be infinite and which are stated in this model only
  ([Interval kernels](../developer/design/milestone2.md#what-is-stated-of-an-interval-kernel)):
  the result is a canonical interval, it is empty exactly when an operand is, and it contains the
  exact result for all members of the operands, unbounded operands included; and how close its
  bounds are to those of the exact range. For bounds of one limb, the constructor, the negation,
  the sum, the difference and the product are proved: the bounds of a sum and of a difference
  are the bounds of the exact range rounded outward, those of a product are within one number
  of `T` of that, and the result is bounded exactly when the exact range is within the largest
  number of `T`. For bounds of two limbs, the sum is proved: each bound of a bounded result is
  within $A\lvert v\rvert + B$ of the bound $v$ of the exact range, with the constants of
  [Bounds of two limbs](../developer/design/milestone2.md#bounds-of-two-limbs), a bound of the
  exact range that is zero is returned as zero, and the result is bounded when the exact range
  is within a quarter of the overflow threshold.
- For the conversions of a ball
  ([Midpoint, radius and the conversions](../developer/design/milestone2.md#midpoint-radius-and-the-conversions)):
  the bounds of a ball as numbers of `T` are on their side of every member, with $+\infty$ and
  $-\infty$ for the empty ball, and they are the bounds rounded outward for a center of one
  limb; a ball of two limbs narrowed to one limb, and a ball of two limbs made from an interval
  of two numbers of `T`, are canonical and contain what they are made from, whatever the
  operands are. For an interval whose bounds have two limbs: the midpoint is a canonical
  number of two limbs for every interval (two NaN for the empty set), and that of a bounded
  interval is finite, in the interval and within $3u^2/(1-4u)\,\lvert m\rvert + 2\eta$ of the
  exact midpoint $m$; its radius is $+\infty$ or a finite number with which the midpoint
  contains the interval, and it is finite when both bounds are within a quarter of the
  overflow threshold; the ball made of the two contains the interval; the split at the
  midpoint gives two canonical intervals with a common finite bound; and the empty set, the
  whole line and the half-lines give the values of IEEE 1788. That the midpoint is finite
  rests on a fact about the sum of two 2-limb numbers, proved here: it does not overflow when
  the leading limbs of both operands are at most half the largest finite number. And whether
  a ball of two limbs contains a point of two limbs: a yes or a no is given only when it is
  right, never both, and exactly when it is right if the ball is the empty set or the whole
  line or the point is not a finite number. And the hull and the intersection of two balls,
  with a center of one limb and of two: the result is a canonical ball that contains every
  member of either ball (of both, for the intersection); the hull is empty exactly when both
  balls are, and the intersection is empty when one of them is; when the first ball is empty
  (for the intersection, the whole line) the result is the second as it is, its very limbs, and
  when the second is and the first is not, the first as it is. Not that the hull is the smallest
  such ball, nor that the intersection is inside either ball or empty for disjoint balls.

These statements and the models of the kernels they are about are generated from the kernel
descriptions, like the C++ (`proofs/gen/IeeeModel.v`, `IeeeStatements.v`). Three files are
written by hand and are part of what must be trusted: `proofs/theories/IeeeOperations.v`, which
says what each operation of a kernel means in Flocq's terms, `IeeeVocabulary.v`, the definitions
the statements use (what a canonical value is, what a ball contains), and
`IeeeIntervalVocabulary.v`, the definitions the statements of the interval kernels use (a
canonical interval, its members, the exact range of an operation and its bounds).
The kernels of the last three
kinds are in the generated headers and are `proved` in the claims; whether an operator of the
library calls them yet is said in
[What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values).

## Sums and dot products of arrays

A fold is a loop of kernels along arrays: `sum_1`, `sum_2`, `sum_fast_2` (the fast addition),
their `_entry` forms for arrays that the program fills, `dot_1` and `dot_2`. Three things are
proved of each, in the real model.

**The bound of the fold, in both orders.** The generated model of a fold `F` is two functions on
lists: `F_seq`, the elements taken one after the other, and `F_lanes W`, the order of a loop
with `W` partial results that are combined at the end, as a SIMD loop runs it. `F_seq_correct`
and `F_lanes_correct` (`FoldSums.v`) have the generated statements as their types: for every
list of valid elements, and in the lane order for every `W`, the result is valid and within

$$\bigl((1 + \varepsilon)^{n-1} - 1\bigr)\sum_i \lvert v_i\rvert$$

of the exact sum of the $n$ values $v_i$, with $\varepsilon$ the relative error of the addition;
for a dot product there is one more factor for the products, and a term for underflow
([the statements](../developer/design/milestone2.md#sum-dot-axpy-convolution)). The bound does
not depend on the order, which is why one statement serves the scalar loop and the SIMD loop.
The proofs show that the generated step and combination are the ones the theorems of
`SummationKernels.v` are about, and apply those theorems.

**The exported bound.** A program cannot write $(1 + \varepsilon)^{n-1} - 1$ in floating
point. The kernels `bound_sum_1`, `bound_sum_2`, `bound_dot_1` and `bound_dot_2` compute, from a
count $m$, a number $g$ of the format (and for a dot product a second one, $t$) and a flag
`ok`; `K_correct` (`BoundKernels.v`) proves that when `ok` is true, $g$ is at least
$m\varepsilon/(1 - m\varepsilon)$ and $t$ at least $m\,\tau\,(1 + g)$, for $m$ zero or at
least 1, in a format that contains $\tfrac12$.

**The two together** (`FoldGuarantee.v`, audited by hand: these statements are not generated).
For each fold and each order, if the bound kernel answers `ok` for a count $m$ that is at least
the count of the fold, then the result of the fold is within $g\sum_i\lvert v_i\rvert$ of the
exact sum, plus $t$ for a dot product. The count of a sum of $n$ elements is $n - 1$, and that
of a dot product of $n$ terms is $n$. These theorems are named `F_seq_bound` and
`F_lanes_bound`.

| Fold | Bound kernel | Count | From precision |
|---|---|---|---|
| `sum_1`, `sum_1_entry` | `bound_sum_1` | $m \ge n - 1$ | 1 |
| `sum_2`, `sum_2_entry`, `sum_fast_2`, `sum_fast_2_entry` | `bound_sum_2` | $m \ge n - 1$ | 3 |
| `dot_1` | `bound_dot_1` | $m \ge n$ | 1 |
| `dot_2` | `bound_dot_2` | $m \ge n$ | 4 |

These are statements of the real model, where nothing overflows. The step of each fold is a
kernel with a statement of its own (`StepKernels.v`).

**When an element is not finite, or an operation overflows.** A fold returns its result
through a finish, a kernel proved in the IEEE model (`IeeeFoldFinish.v`): the flag is true
exactly when the leading limb of the final state is finite, the result is then that state, and
otherwise every limb of the result is a NaN. What a true flag says about the whole loop is
proved for the generated models of the folds in the IEEE model (`proofs/gen/IeeeFoldModel.v`:
the generated IEEE models of the step, the combination and the finish, in the same two orders),
against the generated statements: `F_seq_ieee_correct` and `F_lanes_ieee_correct`
(`IeeeFolds.v`) have `F_seq_ieee_spec` and `F_lanes_ieee_spec` of
`proofs/gen/IeeeFoldStatements.v` as their types. For every fold and both orders, on any
elements (canonical pairs, for two limbs): if the flag is true, every element is finite, the
result is finite and is the result of the real model on the values of the elements, hence valid
and within the bound above; if the flag is false, every limb of the result is a NaN. So an
infinity or a NaN among the elements, or an overflow anywhere in the loop, cannot give a finite
wrong result. In the sequential order the state after every element was finite too, which the
generated statements do not say (`F_seq_ieee_facts`, a statement written by hand about the same
generated model).

The argument is one induction for all folds (`FoldTransfer.v`), from two facts about one
application of a step. The first, that a leading limb which is not finite stays not finite, is
a generated statement for every step and combination, `K_ieee_lead_spec`, proved as
`K_ieee_lead` (`IeeeFolds.v`); it is the rule that the generator checks on every listing, here
as a theorem. The second, that from a finite, valid state a finite leading limb means a finite
element and the values of the real model, is the bridge between the two models. For the steps
as kernels, the generated bridge statements, with the finiteness of every value the step
computes, and the correctness statements of the steps of two limbs are proved in `IeeeSteps.v`
(`K_ieee_bridge`, `K_ieee_correct`).

These theorems are audited by the generated audit of step 5 above: the description of a fold
names the file of its IEEE-model theorems, and that of a step or a combination names the
theorem of each of its IEEE-model statements. `F_seq_ieee_facts` and the facts about one
application of a step, whose statements are written by hand, are audited in step 3.

## Loops that write an array

A map writes one element for each element it reads: the sum and the difference of two arrays
(`add_k`, `sub_k`), `axpy_k` and `axpy_2_1` ($a\,x + y$), their `_entry` forms for arrays that
the program fills, the product by a number (`scale_k`) and by a power of two
(`mul_pow2_map_k`), eighteen in all. The generated model of a map `F` is the list of the
elements it writes, and its statement says of every element written what the statement of its
step says of one element: it is valid and within the step's bound of the exact value for its
own element. `F_correct` (`FoldMaps.v`) is the theorem of the step on every element; the steps
that are kernels of their own are proved in `MapSteps.v`.

These are statements of the real model. They say nothing of the order in which the loop runs
(the model has none: an element written depends on its own element only), of the mask the loop
returns, or of an array written over one it reads.

**The steps in the model with overflow** (`IeeeMapSteps.v`). Each of the sixteen steps that is
not a kernel of Milestone 1 (`add_2_2` and `sub_2_2`, the steps of `add_2` and `sub_2`, have
theirs already) has its generated bridge: from finite operands that satisfy its requirements, a
finite leading limb of its result means that every value it computes is finite and that the
result is that of the real model (`K_ieee_bridge`); for the eight of two limbs, its claims under
the same hypotheses (`K_ieee_correct`); and, for any operands, that a finite leading limb of its
result means a finite leading limb of every operand, the scalars included (`K_ieee_lead`, also
for `sub_2_2`). Each value of a program at an input position or before its leading limb is in
the cone of that limb, which is computed: the same theorems of `IeeeBridge.v` as for the steps
of the folds.

**The maps in the model with overflow** (`IeeeFoldMaps.v`). The generated model of a map in
this model (`proofs/gen/IeeeFoldModel.v`) is that of the scalar loop: the step on every
element, the mask, the and of the check of every element written (its leading limb is finite),
in the sequential order and in the lane order for every `W`, and, when the mask is false, a
second pass in which every element is replaced by what the check returns of it: itself when
its leading limb is finite, NaN in every limb otherwise. `F_seq_ieee_correct` and
`F_lanes_ieee_correct` have the generated statements as their types. For canonical elements
and scalars (of two limbs: finite and normalized, or an infinity and a zero, or two NaN; of
one limb, any value; a power of two, finite), entry by entry: if the leading limb returned is
finite, every limb of the scalars, of the element and of the element returned is finite, the
values are those of the real-model step on the values of the operands, and the claims of the
step hold of them; otherwise every limb returned is a NaN and the mask is false; and the mask
is true exactly when every leading limb returned is finite. So an infinity or a NaN among the
operands, or an overflow in a step, gives a NaN in that entry and a false mask, never a finite
wrong element, and the other entries keep their correct values. The proof writes the mask as
`forallb` of the check, in both orders (`fold_seq_and`, `fold_lanes_and`), and follows its two
values (`map_entries_mask_true`, `map_entries_mask_false` of `Folds.v`), entry by entry with
the theorems of the step: its leading limb, its bridge, and its claims (`K_entry`).

## The largest magnitude of an array

`norm_upper_1` and `norm_upper_2` return the largest magnitude of the elements of an array, or
a bound of it. They are folds of maxima: the state is the largest magnitude so far, with a mask
that no element was a NaN; the combination is a maximum computed by a comparison.

**In the real model** (`FoldNorm.v`): `F_seq_correct` and `F_lanes_correct` have the generated
statements as their types. With $V$ the largest magnitude of the elements ($0$ for an empty
array) and $r$ the result:

- one limb: $V \le r \le \mathrm{RU}(V)$, and since $V$ is a number of the format, $r = V$:
  the result is the largest magnitude itself;
- two limbs: $V \le r \le \mathrm{succ}(\mathrm{RU}(V))$, where $V$ is the largest magnitude of
  the exact values $x_0 + x_1$ of the elements: the result is at least the magnitude of every
  element, and at most one step above the smallest number of the format that is. It is the
  number next above the largest leading limb, and is never $V$ itself (`norm_upper_2_strict`).

The lane order returns the state of the sequential order (`norm_upper_k_lanes_seq`): the
combination is associative and commutative, and the zero state combined with itself is itself
(`fold_lanes_aci` of `Folds.v`). So here the two orders give the same result, not only the same
bound.

**With infinities, NaN and overflow** (`IeeeFoldNorm.v`): the finishes `norm_finish_1` and
`norm_finish_2` and the two folds in both orders have their generated IEEE-model statements
as types. If the flag is true, every element is finite, the result is finite, and it is the
result of the real model on the values of the elements, with the bounds above; if the flag is
false, the result is a NaN. A comparison with a NaN is false, so the maximum alone would lose a
NaN element: the mask keeps it, and the finish tests the mask.

Beyond the generated statements (written by hand, audited in step 3): the two orders return
the same result and the same flag on every input, NaN and infinities included
(`norm_upper_k_lanes_seq_ieee`); for one limb the flag is true exactly when every element is
finite (`norm_upper_1_seq_ieee_flag`); for two limbs, exactly when every leading limb is finite
and the step up from the largest of them is finite (`norm_upper_2_seq_ieee_flag`). So
`norm_upper_2` can answer with a false flag on an array of finite numbers, when the bound one
step above the largest leading limb would not be a number of the format. That the lane order
computes the state of the sequential order, and when exactly the flag is true, are also
generated statements, `F_orders_ieee_spec` and `F_flag_ieee_spec`, whose theorems
`F_orders_ieee_correct` and `F_flag_ieee_correct` are the lemmas above with their variables
bound; the fold's `ieee_theorem` names them with those of its orders, so step 5 audits them.

## The product of two polynomials

`conv_1` and `conv_2` write the coefficients of the product of two polynomials given by their
coefficients, $n_x$ of one and $n_y$ of the other: $n_x + n_y - 1$ coefficients, none when a
polynomial has none. In the generated model coefficient $j$ is the dot product (`dot_1`,
`dot_2`), in its sequential order, of a list of terms, `conv_terms xs ys j`, and the generated
statement says of every coefficient what the statement of the dot product says of that list:
the coefficient is valid and within the bound of the dot product of the sum of the products of
its terms. `conv_k_correct` (`FoldConv.v`) is the theorem of the dot product on the terms of
every coefficient.

The statement names the list of the terms and does not say what it is. That is proved beside
it (`FoldConv.v`, written by hand, audited in step 3): the terms of coefficient $j$ are exactly
the pairs $(x_i, y_{j-i})$ for $i$ from $\max(0, j - n_y + 1)$ to $\min(j, n_x - 1)$, in
increasing $i$ (`conv_terms_eq`, `conv_terms_count`), so the exact sum the coefficient is
compared with is the coefficient of the product as it is usually defined; every coefficient
has at least one term and at most $\min(n_x, n_y)$ (`conv_terms_nonempty`,
`conv_terms_length`); and if the bound kernel of the dot product answers `ok` for a count of at
least $\min(n_x, n_y)$, its two numbers bound the error of every coefficient (`conv_1_bound`,
`conv_2_bound`, from the theorems of [the two together](#sums-and-dot-products-of-arrays)).
Three of these facts are also generated statements, `conv_terms_eq_spec`,
`conv_terms_count_spec` and `conv_terms_length_spec`, whose theorems `conv_terms_eq_correct`,
`conv_terms_count_correct` and `conv_terms_length_correct` are those lemmas; the convolutions
name their file (`terms_theorem`), so step 2 audits them.

These are statements of the real model, as for a map. No theorem is about the product as a
polynomial (its value at a point).

**In the model with overflow** (`IeeeFoldConv.v`): `conv_k_ieee_correct` has the generated
statement as its type. Coefficient $j$ is the final state of the dot product, in its
sequential order, on the terms of $j$; the convolution keeps the and of the check of every
coefficient, and when it is false every coefficient is replaced by what the check returns of
it, as a map does. For canonical entries of the two polynomials, coefficient by coefficient:
if its leading limb is finite, every limb of every term is finite, the values are those of
the dot product of the real model on the values of the terms, and the conclusions of its
statement hold; otherwise every limb of the coefficient is a NaN and the mask is false; and the
mask is true exactly when every leading limb is finite. The proof reads the IEEE-model theorem of the dot product
(`dot_k_seq_ieee_correct`, about the finish of that state) on the state: the finish of a state
whose leading limb is finite returns it, with the flag true.

## Ball vectors

A ball vector is $N$ centers with one radius ([the design](../developer/design/milestone2.md#ballvector)):
`bv_add_k`, `bv_sub_k` and `bv_scale_k` write the centers of the result by the map of their
operation, record the largest magnitude $m$ of a center written (of its leading limb, for two
limbs), and compute the one radius by a radius kernel on $m$ and the scalars.

**The radius kernels** (`BvRadius.v`): `bv_add_radius_k` and `bv_scale_radius_k` have their
generated statements as types. They are the radius lines of `ball_add_k` and `ball_scale_k`
with $m$ in place of the magnitude of one entry's center, and their claim is that the radius
is a number of the format and at least $r_x + r_y + U\kappa\,m$ (sum and difference) or
$\lvert a\rvert r_x + U\kappa\,m + V$ (scaling), with $U$ and $V$ from the bound of the step
relative to its result and $\kappa = (1+u)^{k-1}$: the bound of the radius of the Ball
kernels (`Ball2.v`, `radius_2`) at $m$, for every $m \ge 0$ and radii $\ge 0$. These are
statements of the real model.

**The ball vectors in the real model** (`BvReal.v`): `F_correct` has the generated statement
of each of the six as its type. For nonnegative radii and valid centers (numbers of the
format, normalized pairs for two limbs), the radius is a number of the format and, entry by
entry, the center written is valid and the value of the operation on any members of the balls
of the operands' entries is within the radius of it. Entry by entry: the members' result is
within $r_x + r_y$ (or $\lvert a\rvert r_x$) of the exact result on the centers, which is
within $U\lvert z\rvert + V$ of the center written $z$ (the bound of the step, made relative
to its result); $\lvert z\rvert \le \kappa m$, because the record is the maximum of the
magnitudes (`maxc_seq_value` of `FoldNorm.v`) and a normalized pair is at most $(1+u)$ times
its leading limb; and the claim of the radius kernel at $m$ covers the sum. So no property of
the rounded radius lines as functions of $m$ is needed: that they are nondecreasing, which
makes the one radius the largest of the radii the Ball kernel would compute entry by entry, is
true but not proved.

**The ball vectors in the model with overflow** (`IeeeBv.v`): `F_seq_ieee_correct` and
`F_lanes_ieee_correct` have the generated statements of the six in their two orders as types,
each the conjunction of four lemmas (`F_O_ieee_v1` to `F_O_ieee_v4`, audited in step 3). For
canonical operands (a finite nonnegative radius with finite centers, or the radius
$+\infty$ with zero centers): the result is a finite ball vector or the whole space (zero
centers, radius $+\infty$), and the flag is true exactly when the radius is finite (V1);
entry by entry, the value of the operation on members of the operands' balls is in the ball
of the center written (V2); a finite radius means finite radii and scalar, the centers of
the real model and its radius (V3); and finite radii (and scalar) whose own sum, or
$\lvert a\rvert r_x$, is at most $2^{e_{\max}-2}$, with every entry within the same limit,
give a finite radius, for every length including zero (V4), from precision 2 (3 for the sums
of two limbs, the precision of their statements). The lane
order returns what the sequential order returns. The proof: when the flag is true, the
radius kernel's result is finite, so the record and every center written are, and the
lemmas of the maps and of the folds of maxima in this model give the values of the real
model, where `BvReal.v` applies; when it is false the result is the whole space. V4 is the
finiteness of the Ball kernels' radius (`IeeeBallFinite.v`) at the largest magnitude. At
precision 1, where the other clauses of one limb start, V4 would be false: with
$e_{\max} = 2$ a constant of the radius lines rounds up to $2^{e_{\max}}$, so every radius is
$+\infty$ or a NaN; the statements claim it from precision 2 (`finite_from=2`).

**The negation and the constructor** (`BvNegMake.v`, `IeeeBvNegMake.v`): every kernel of
`bv_neg_k` and `bv_make_k` and the four folds have their generated statements, in both models
and both orders, as types. The negation is exact: the centers are negated and the radius is
the operand's, so the ball of each center written is exactly the set of the negated members of
the operand's ball (`neg_ball_image`); a canonical operand has finite or zero centers, so the
result is the negated finite ball vector, or the whole space when the operand is. The
constructor returns the centers and the radius given (a guard, or a copy, and the radius
kernel $(r + 0) + (m - m)$ is $r$ for a finite largest magnitude $m$), and the whole space
exactly when the radius is negative, a NaN or $+\infty$ or a center (its leading limb) is not
finite: the radius kernel is finite only from a finite $m$ and a finite $r$, $m$ is finite with
the record's mask true exactly when every center is, and the finish tests the sign of the
radius (`bv_make_finish`). The leading limbs of `neg_2`, `bv_center_2` and
`bv_center_entry_2`, the steps of two limbs, are generated statements too, whose theorems their descriptions name
(`ieee_lead_theorem`, which a kernel of the extended domain may name when it has a leading-limb
statement): they are audited in step 5.

**The scaling by a power of two** (`BvPow2.v`, `IeeeBvPow2.v`): the two steps, the radius kernel
and `bv_mul_pow2_k` have their generated statements, in both models and both orders, as types.
With $c = 2^n$ and $N = \eta / (2u)$ the smallest normal number: each step scales the center as
`mul_pow2_step_1` or `mul_pow2_2` does, within $\eta/2$ (one limb) or $\eta$ (two limbs) of
$c\,x$, and its mask is true exactly when every scaled limb is zero or above $N$ in magnitude, in
which case the center is $c\,x$ exactly (`step_mask_k`: a rounded product above $N$ comes from a
product above $N$, which is a number of the format). The radius is $c\,r_x$ when the mask of every
entry is true and $c\,r_x$ is zero or above $N$, at least $c\,r_x$ always, and at least
$c\,r_x + \eta$ when some mask is false (two steps above the rounded $c\,r_x$); the largest
magnitude enters only as $m - m$, which is $0$ in the real model and a NaN for an infinite $m$ in
the IEEE model. So the one radius covers every entry, and under the conditions of `exact_when`
(every scaled limb and $c\,r_x$ zero or above $N$) the result is exactly $c$ times the operand: a
polynomial halved again and again keeps the radius $r/2^i$ exactly, until something underflows.
In the IEEE model a finite result is the real model's on the values, masks included; V4 holds
because under its conditions every scaled center and the radius lines stay below $2^{e_{\max}}$.

**The product of two ball vectors** (`BvConv.v`): the radius kernel `conv_radius` and
`bv_conv_k` have their generated statements of the real model as types. The radius: each of the
six first lines is one rounding of a nonnegative value, which loses at most a factor $1+u$ and
$\eta/2$; chained, with $g \le 1$, they leave the bound of the claim times $(1+u)^5$ plus at most
$(1+u)^5\eta/2 + 5(1+u)^4 m\,\eta/2$, which the last line covers: its factor
$\mathrm{RU}((1+u)^7)$, and its term $m\,\mathrm{RU}(4(1+u)^8\eta + \eta/(2u))$, in the normal
range for $m \ge 1$ (with no term, $m = 0$, the claim is $t \le r_z$). The requirement $g \le 1$ is
what a true mask of `bound_dot_k` gives (`bound_dot_k_at_most`: its listing tests $g$ against
$\mathrm{up}(1) = 1$). The fold: coefficient $j$ is within $g\sum\lvert c_x c_y\rvert + t$ of the
exact sum of the products of the centers of its terms (`conv_k_bound` of `FoldConv.v`, for the
count $m \ge \min(n_x, n_y)$ rounded up), and for members $x_i$, $y_k$ chosen independently in
their balls, the terms of the coefficient of the members are those of the centers term by term
(`conv_terms_Forall2`), each product within $\lvert c_x\rvert r_y + \lvert c_y\rvert r_x + r_x
r_y$ of the product of the centers (`member_product`), every center at most $(1+u)M$ (one limb:
$M$) with $M$ the largest magnitude of a leading limb, and at most $m$ terms: so the exact
coefficient of the members is within the radius's claim of the coefficient written
(`coef_bound`).

**The finish of the product in the model with overflow** (`IeeeBvConv.v`): `bv_conv_finish` has
its generated statement as type: the flag is true exactly when both masks (the convolution's and
the bound's) are true and the radius is finite, the result is then the radius, and otherwise a
NaN. (The statement was first printed without the two masks, "the flag is true exactly when the
radius is finite", which was false: a false mask of the convolution gives a false flag with a
finite radius. The generator now prints the masks of `if_all`, as it prints the one mask of
`if`.)

**The product in the model with overflow.** Its generated statement is one conjunction, V1 to
V4. For `bv_conv_1` it is proved (`bv_conv_1_ieee_correct` of `IeeeBvConvFinite.v`): the
description names the file and the generated audit checks it against the generated statement in
step 5. (A product of two BallVectors has one statement, `bv_conv_1_ieee_spec`, as a convolution
has; the generator's audit first named it `bv_conv_1_seq_ieee_spec`, a statement that does not
exist, and the theorem was checked in step 3 until the printer was mended.) For `bv_conv_2` it is
proved too (`bv_conv_2_ieee_correct` of `IeeeBvConvFinite2.v`, audited in step 5), under the
condition on the count as restated: as first printed its V4 was false (below). V1 to V3 are proved for both, as lemmas of their own in the
vocabulary of the statement (`bv_conv_k_ieee_v1`, `_v2`, `_v3` of `IeeeBvConv.v`, audited in step
3), for canonical operands,
infinite radii (the whole space) included: the result is a finite ball vector or the whole space,
with $n_x + n_y - 1$ coefficients (none when an operand is empty), and the flag is true exactly when
the radius is finite; for all members of the operands' balls, each entry chosen independently,
coefficient $j$ of their exact product is in the ball of coefficient $j$ written (the whole space
contains everything); and a finite radius comes from finite radii, with the coefficients and the
radius of the real model on the values, so that V2 is the real-model theorem read on the values.

**V4 of `bv_conv_1`** (`bv_conv_1_ieee_v4`): finite radii, $n\,(u/(1+u) + \eta) \le \tfrac1{16}$ with
$n = \min(n_x, n_y)$, $r_x r_y \le Q$, $(\lvert x\rvert + r_x)\,r_y \le Q$ for every entry $x$,
$(\lvert y\rvert + r_y)\,r_x \le Q$ for every entry $y$ and $n\,(\lvert x\rvert + r_x)(\lvert y\rvert
+ r_y) \le Q$ for every pair, $Q = 2^{e_{\max}-2}$, give a finite product, in every format of the
statement (precision at least 4, $e_{\max} > p$). Every value the IEEE model computes is shown at
most $\tfrac72 Q$, below the largest number $4Q(1-u)$, so that every operation returns its rounded
real result: the count $n \le 2^p$ is a number of the format; the bound's mask is true ($a \le
0.16 \le \mathrm{up}(\tfrac14)$, $g \le 0.3$), its $t$ at most $Q/4$ (the smallest normal number of
the constant of $tm$, times $n$, is at most $1/(32u) \le Q/16$); every state of the fused dot
product of a coefficient is within $(1+\varepsilon)^k \le \tfrac{16}{15}$ of a sum of at most $n$
products each at most $Q/n$; and with $P = (M_a + r_x)(M_b + r_y)$, the largest magnitudes being
attained, $P \le Q$ and $n P \le Q$ (the pairs' condition with both operands nonempty, an array's
own condition or the radii's otherwise), and the radius kernel stays at most $3.2\,Q$.

**V4 of `bv_conv_2` was false as first printed, and its claim is restated.** In a format of
precision $p \ge 8$ with $p < e_{\max} \le 2p - 7$, the condition on the count as first printed,
$n\,(4u^2 + \eta) \le \tfrac1{16}$, admits $n = 2^{e_{\max}}$, and every $n$ above the largest number
$\Omega = (1 - 2^{-p})\,2^{e_{\max}}$ makes the count rounded up overflow to $+\infty$;
`bound_dot_2(+\infty)` then has its mask false and the product is the whole space, although the
operands are finite and meet every condition. For instance $p = 8$, $e_{\max} = 9$ ($\eta =
2^{-14}$, $\Omega = 510$), both operands 511 entries $(+0, +0)$ with radii $+0$: $511\,(2^{-14} +
2^{-14}) = 511/8192 \le 1/16$, every other condition is $0 \le 2^{7}$, and the interpreter returns
1021 zero coefficients, the radius $+\infty$ and the flag false (with 510 entries the count is 510
and the product is finite). The condition now has the smallest normal number $\eta/(2u) =
2^{2 - e_{\max}}$ in place of $\eta$, $n\,(4u^2 + \eta/(2u)) \le \tfrac1{16}$, which bounds $n$ by
$2^{e_{\max} - 6}$ whatever the precision, so that the count is a number of the format; in that
format it admits $n \le 7$. `binary32` and `binary64` admit exactly the same counts under both forms
(up to $2^{42} - 1$ and $2^{100} - 1$: the $4u^2$ is what bounds them).
`test_bv_conv.Interp.test_the_count_overflowed` keeps the counterexample.

**V4 of `bv_conv_2`** (`bv_conv_2_ieee_v4`), in the manner of one limb: finite radii, $n\,(4u^2 +
\eta/(2u)) \le \tfrac1{16}$, and the conditions on the radii, the entries and the pairs as for
`bv_conv_1` with each entry's value $x_0 + x_1$, give a finite product in every format of the
statement (precision at least 4, $e_{\max} > p$). The count: $n \le 2^{e_{\max}-6}$, so $m$, $n$
rounded up, is finite and at most $(1+2u)\,n \le \tfrac98 n$ (`count_bounded`), and $m\,4u^2$ and
$m\,\eta/(2u)$ are at most $\tfrac9{128}$. The bound's mask is true ($a \le 0.115$, $g \le 0.23$) and
its $t$ at most $\tfrac14$. The coefficients: each step of the dot product of two limbs is `mul_2_2`,
finite when the exact product is at most $2^{e_{\max}-1}$ (`IeeeMul22.v`), then `add_2_2`, finite
when both leading limbs are at most $\tfrac54 Q$ (`add_2_2_values_finite_wide`: the bounds of
`IeeeAdd22.v` with $\tfrac54 Q$ for $Q$, which precision 4 still allows); every state of the real
model is within $(1 + 4u^2)(1 + 3u^2/(1-4u))^{k-1} \le \tfrac{65}{64}\cdot\tfrac{16}{15}$ of a sum of
at most $n$ products each at most $Q/n$, so its leading limb is at most $1.16\,Q$, and the leading limb
of each product at most $1.09\,Q$; so every IEEE state is finite and the real model's
(`dot_2_forward`). The radius: the largest leading limbs are at most $(1+u)$ times their entries'
magnitudes, so $P \le (1+u)^2 Q$ and $m P \le \tfrac98 (1+u)^2 Q$, and the radius kernel stays at most
$3.35\,Q$. The theorem of the generated statement, `bv_conv_2_ieee_correct`, is V1 to V3 of
`IeeeBvConv.v` with V4.

## The accumulator

`Accumulator<T, k>` keeps a running sum $s$ of $k$ limbs, a running sum $a$ in `T` of the
magnitudes of the leading limbs of what was added, and a count
([the design](../developer/design/milestone2.md#the-accumulator)). Its state kernels are
proved against their generated statements in both models: `acc_add_k` (one term),
`acc_mul_k` (one product) and `acc_merge_k` (another accumulator's state) return the next
$s$ with the claims of `add_1_1`, `add_2_2` or the step of the dot product, and the next $a$
as the rounding to nearest of its value (`AccKernels.v`); in the IEEE model each output
group's claims hold where its own leading limb is finite (`IeeeAccKernels.v`).

The radius `acc_radius_k`, from $a$, a count $m$ (0 or at least 1) and the two numbers of
`bound_dot_k(m)`, is proved in both models too: its result $r$ is at least
$g\,(1+u)^2(1 + m u + 2m^2u^2)(a + m\eta/2) + t$ for every $m$, and when its mask is true,
$m u \le \tfrac12$. The proof needs nothing of the format beyond $p \ge 2$: each of its
roundings is in the normal range, or is covered by the constant added in the last line. In
the IEEE model a finite $r$ is the real model's $r$, and the mask the real model's
(`acc_radius_1_real`).

**What a user of the accumulator relies on** (`Accumulator.v` in the real model,
`IeeeAccumulator.v` in the IEEE model; written by hand and audited in step 3). A history of
an accumulator is a tree: `add` and `add_product` add a term to a history, and `merge` joins
two histories, each of which may contain merges. For every such history whose elements are
numbers of the format (normalized pairs for two limbs), with $n$ the number of terms, $s$
the running sum, $a$ the sum of magnitudes and $\Sigma$ the exact sum of the terms ($x$ for
an `add`, $x y$ for an `add_product`):

- $\sum_i \lvert x_i y_i\rvert \le (1+u)^{n+2}\,(a + n\eta/2)$ (`acc_2_terms_mags`; for one
  limb with $(1+u)^n$, `acc_1_mags`): the magnitudes the kernels add are those of the leading
  limbs, each rounding of a nonnegative sum loses at most a factor $1+u$, and $\eta/2$ only in
  a fused multiply-add, and a merge of two histories of $n_1, n_2 \ge 1$ terms costs one
  factor for $n_1 + n_2$ terms;
- $\lvert s - \Sigma\rvert$ is within the statement of `dot_k` for $n$ terms, whatever the
  shape of the tree (`acc_1_error`, `acc_2_error`): the history is mapped to a tree of the
  summation theorem, of height at most $n - 1$ for two limbs and $n$ for one;
- with $(g, t)$ from `bound_dot_k(m)` and $r$ from `acc_radius_k(a, m, g, t)`, for $m$ a
  number of `T` that is 0 or at least 1 and at least $n$, in a format that contains
  $\tfrac12$, when both masks are true:
  $\lvert s - \Sigma\rvert \le g\sum_i\lvert x_i y_i\rvert + t \le r$
  (`acc_1_chain`, `acc_2_chain`; the final statements `acc_1_bound`, `acc_2_bound`).

In the IEEE model, for elements whose limbs are finite: if the running sum and $r$ are
finite and both masks are true, then every state on the way was finite and had the values
of the real model, and the same bound holds (`acc_1_ieee_bound`, `acc_2_ieee_bound`). A true
mask of `acc_radius_k` means a finite $a$ (`acc_radius_1_ok_finite`). Not proved: what the
header does when a value is not finite or a mask is false (it returns the whole line), the
count as a machine integer and its conversion to `T`, and that the header calls the kernels
in this way.

## What a proof does not cover

A checked proof establishes its statement, nothing more. It does not show that the statement says
what was meant, which is why every reference page prints the Rocq statement next to the plain one.
It does not cover the generator, which prints the Rocq model and the C++ from one description and
must print both faithfully, nor the compiler, the hardware and the floating-point environment. The
tests are aimed at those
([Testing](../developer/testing.md), [Trusted base](../developer/design/phase0/verification.md#trusted-base)).
