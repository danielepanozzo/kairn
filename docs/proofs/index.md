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
- `proofs/theories/`, the proofs written by hand, one theorem `K_correct` per kernel `K` and the
  lemmas they share;
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
   `Print Assumptions K_correct`. A script, `proofs/audit/audit.py`, reads what Rocq printed and
   fails on any axiom outside the allowed list, on a missing report, or on any output it does not
   understand.
3. **The theorems whose statements are written by hand**, the same way, from
   `proofs/audit/HandAudit.v`: the IEEE-model theorems below, and facts that say more about a
   kernel than its generated statement does.
4. **A negative control**: `proofs/audit/Bad.v`, a false theorem closed with `Admitted`, must be
   rejected by both checks.

What it prints, after the compilation lines, shortened where it says `...` (a run of this version):

```text
== text scan of the proof files
  33 files: no Admitted, admit, Axiom or Parameter
== assumptions of every theorem that establishes a generated statement
  ok           add_1_1_correct: 4 axioms
      allowed      ClassicalDedekindReals.sig_forall_dec
      allowed      ClassicalDedekindReals.sig_not_dec
      allowed      Classical_Prop.classic
      allowed      FunctionalExtensionality.functional_extensionality_dep
  ok           rmul_correct: 4 axioms
  ...
== assumptions of the theorems whose statements are written by hand
  ...
== negative control: a false theorem closed with Admitted must be rejected
  rejected by the text scan, as it must be
  REJECTED     wrong: 1 axioms
      NOT ALLOWED  wrong
  rejected by the assumption check, as it must be
== audit passed
```

Each theorem gets a line `ok` or `REJECTED`, with the axioms its proof depends on, each marked
`allowed` or `NOT ALLOWED`; in the control, the admitted theorem `wrong` shows up as an axiom named
after itself, which is how an unfinished proof is caught. In this version every audited theorem
depends on the same four axioms.

A kernel's status in `gen/claims.json` is `proved` only when this audit passes for its theorem,
and the CI runs it on every push and pull request.

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
`binary64`. Two kinds of statements are proved there:

- For the arithmetic kernels of two limbs: an overflow anywhere in the kernel never produces a
  finite wrong result (if the leading limb of the result is finite, the result is normalized and
  within its bound), and the result is finite under a stated condition on the operands
  ([Milestone 1 statements](../developer/design/milestone1.md#what-is-proved-about-an-arithmetic-kernel)).
- For the layer that gives overflow and non-finite operands a defined result
  ([IEEE-like results](../developer/design/milestone1.md#ieee-like-results),
  [Ball kernels](../developer/design/milestone1.md#ball-kernels)): the full kernels return
  canonical values, the signed infinity on overflow, and what the operation of the limb type
  returns for non-finite operands; comparisons, conversions and constructors behave as stated on
  infinities and NaN; and a Ball operation contains every result in every case, the whole line
  and the empty set included.

These statements, and the models of the kernels they are about, are **written by hand**
(`proofs/theories/IeeeStatementsDraft.v`, `IeeeExtStatementsDraft.v`, `IeeeDraft.v`,
`BallDraft.v`) from the listings of the design pages, and audited by `proofs/audit/HandAudit.v`.
The generator does not print them yet, and the public headers do not yet call the kernels of the
second kind, so these theorems are not guarantees about what the library does today: the claims keep those
kernels `unverified`, and [What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values)
says what the library does now.

## What a proof does not cover

A checked proof establishes its statement, nothing more. It does not show that the statement says
what was meant, which is why every reference page prints the Rocq statement next to the plain one.
It does not cover the generator, which prints the Rocq model and the C++ from one description and
must print both faithfully, nor the compiler, the hardware and the floating-point environment. The
tests are aimed at those
([Testing](../developer/testing.md), [Trusted base](../developer/design/phase0/verification.md#trusted-base)).
