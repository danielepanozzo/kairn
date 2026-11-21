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
  (`IeeeProduct.v`), with what follows for the kernels whose only fused operations are products
  (`IeeeTwoExecutions.v`), the interval kernels with bounds of one limb, on all values:
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
  comparisons of balls with a center of one limb, on exact pairs (`IeeeBallPredicates.v`); and
  the theorems of the
  folds, `F_seq_correct` and `F_lanes_correct` per fold `F` (`FoldSums.v`), of their steps,
  finishes and bound kernels
  (`StepKernels.v`, `IeeeFoldFinish.v`, `BoundKernels.v`), of the two together
  (`FoldGuarantee.v`), and of the folds and their steps in the model with overflow
  (`FoldTransfer.v`, `IeeeSteps.v`, `IeeeFolds.v`; [below](#sums-and-dot-products-of-arrays));
  the theorems of the maps, `F_correct` per map `F`, and of their steps (`FoldMaps.v`,
  `MapSteps.v`; [below](#loops-that-write-an-array)); of the largest magnitude of an array and
  its kernels, over the real numbers and with overflow, infinities and NaN (`FoldNorm.v`,
  `IeeeFoldNorm.v`; [below](#the-largest-magnitude-of-an-array)); and of the product of two
  polynomials (`FoldConv.v`; [below](#the-product-of-two-polynomials));
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
   and convolution, which have one statement (`F_audit : F_spec := F_correct`). A script,
   `proofs/audit/audit.py`, reads what Rocq printed and fails on any axiom outside the allowed
   list, on a missing report, or on any output it does not understand.
3. **The theorems that the generated audits do not list**, the same way, from
   `proofs/audit/HandAudit.v`: the IEEE-model theorems of the kernels of Milestone 1 and of
   the first building blocks of Milestone 2 that also have a real-model statement of their own
   domain (these have generated statements as their types, checked by a definition of the same
   form; their descriptions do not name them yet),
   a few facts whose statements are written by hand because they say more about a kernel than
   its claims can express, the theorems about sums and dot products of arrays, which are
   about no single kernel, and the lemmas of the first building blocks of Milestone 2 that are
   not generated statements, among them what is proved of `mul_dir_1`, of the interval
   kernels with bounds of one limb, of the bounds of two limbs, of the sum of two intervals
   of two limbs, of the conversions of a ball, of the exact interval kernels (the hull and
   the intersection of intervals of extended real numbers), of the difference of two
   intervals of two limbs (the sum with the negated operand), of the conversions between an
   interval and a ball (the midpoint of a bounded interval), of the product of two
   intervals of two limbs (the finite core of the directed product, and what each product of
   bounds gives) and of the predicates and comparisons of intervals and of balls of one limb
   (each relation on the bounds as extended real numbers, and the exact pairs of two_sum_ord)
   beside their generated
   statements, those about the two executions of a product, whose plain-product listings are
   written by hand, and the theorems about the folds, the largest magnitude and the product of
   polynomials whose statements are written by hand ([below](#sums-and-dot-products-of-arrays)).
4. **A negative control**: `proofs/audit/Bad.v`, a false theorem closed with `Admitted`, must be
   rejected by both checks.
5. **The IEEE-model theorem of every kernel that accepts infinite and NaN operands**, from the
   generated `proofs/gen/IeeeAudit.v`, like step 2; then, in the same file, every other
   IEEE-model theorem that a description names: those of the steps and the combinations of
   the folds, and of the folds in their two orders.

What it prints, after the compilation lines, shortened where it says `...` (a run of this version):

```text
== text scan of the proof files
  89 files: no Admitted, admit, Axiom or Parameter
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
  operands are.

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
returns, or of an array written over one it reads; the statement of a map in the model with
overflow is not generated yet, so nothing is proved of the mask.

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
step above the largest leading limb would not be a number of the format.

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

These are statements of the real model, as for a map: the statement of a convolution in the
model with overflow is not generated yet, so nothing is proved of its mask or of a coefficient
that overflows. No theorem is about the product as a polynomial (its value at a point).

## What a proof does not cover

A checked proof establishes its statement, nothing more. It does not show that the statement says
what was meant, which is why every reference page prints the Rocq statement next to the plain one.
It does not cover the generator, which prints the Rocq model and the C++ from one description and
must print both faithfully, nor the compiler, the hardware and the floating-point environment. The
tests are aimed at those
([Testing](../developer/testing.md), [Trusted base](../developer/design/phase0/verification.md#trusted-base)).
