(* The guard in the real model.

   A value that the program supplies passes through guard before a kernel adds or
   subtracts it (rule R3 of docs/developer/architecture.md): guard a is RN(a + 0). In the
   real model this is a itself whenever a is a number of the format, so a kernel with a
   guard computes the same values as the kernel without it, and its theorem needs no
   other change than this one rewriting.

   The same fact for the IEEE model (the guard keeps the real value and the finiteness
   of its operand, turns a zero into +0, and leaves an infinity or a NaN what it is) is
   in IeeeOps.v. *)
From Stdlib Require Import Reals ZArith Lia.
From Flocq Require Import Core.
From Kairn.Gen Require Import Statements.
Open Scope R_scope.

(* For any tie rule, in the form in which a model with a guard is unfolded. *)
Lemma guard_real_any :
  forall (emin prec : Z) (choice : Z -> bool) (a : R),
  generic_format radix2 (FLT_exp emin prec) a ->
  round radix2 (FLT_exp emin prec) (Znearest choice) (a + 0) = a.
Proof.
intros emin prec choice a Fa. rewrite Rplus_0_r.
apply round_generic; auto with typeclass_instances.
Qed.

(* The statement, in the vocabulary of proofs/gen/Statements.v. *)
Definition guard_real_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall a : R,
  fmt emin prec a ->
  RN emin prec (a + 0) = a.

Theorem guard_real : guard_real_spec.
Proof. intros emin prec _ a Fa. exact (guard_real_any emin prec tie_even a Fa). Qed.
