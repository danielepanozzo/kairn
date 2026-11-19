(* The constructor kernels in the IEEE model (docs/developer/design/milestone1.md, "Values
   that enter from the program"): make_2, make_2_limbs, ball_make_1, ball_make_2.

   A constructor takes values of T from the program, which may be anything: a NaN, an
   infinity, a zero of either sign. Its result is a canonical object. Every limb that
   comes from the program passes through guard (an addition of +0), which keeps the value
   and what kind of number it is; the proofs are case analyses on the operands.

     make_2(a)            canonical, with the value of a (as an extended real number).
     make_2_limbs(h, l)   requires (h, l) canonical; canonical, with the same value, and
                          with limbs of the same values when h is finite.
     ball_make_1(c, r)    a canonical ball: empty when r is a NaN or negative (-infinity
     ball_make_2(c, r)    included); else the whole line when r is +infinity or the center
                          is not finite; else the ball of center c and radius r.

   The statements are in IeeeExtStatementsDraft.v. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized IeeeBridge IeeeStatementsDraft IeeeExtStatementsDraft
  IeeeOps.
From Kairn Require IeeeDraft.
Open Scope R_scope.

Section IeeeMake.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation guard := (IeeeDraft.guard prec emax nan_plus).
Notation fabs := (IeeeDraft.abs prec emax nan_abs).
Notation flt := (IeeeDraft.lt prec emax).
Notation fle := (IeeeDraft.le prec emax).
Notation feq := (IeeeDraft.eq prec emax).
Notation pzero := (IeeeDraft.pzero prec emax).
Notation pinf := (IeeeDraft.pinf prec emax).
Notation cnan := (IeeeDraft.cnan prec emax nan_const).
Notation ninf := (B754_infinity prec emax true).

(* A number of the format followed by zero is normalized. *)
Lemma normalized_2_lead : forall x : float, normalized_2 emin prec (b2r x) 0.
Proof.
intros x. split; [apply (b2r_format prec emax)|split; [apply generic_format_0|]].
unfold RN. rewrite Rplus_0_r. symmetry.
apply round_generic; auto with typeclass_instances. apply (b2r_format prec emax).
Qed.

(** * make_2 *)

Lemma make_2_facts :
  forall a : float,
  let '(x0, x1) := IeeeDraft.make_2 prec emax nan_plus a in
  canonical_2 x0 x1 /\ xval_2 x0 x1 = xval a.
Proof.
intros a. unfold IeeeDraft.make_2. cbv beta iota zeta.
rewrite (eq_self prec emax), (guard_nan prec emax nan_plus).
unfold xval_2, xval.
rewrite (guard_finite prec emax nan_plus), (guard_nan prec emax nan_plus).
destruct (finite_dec prec emax a) as [Fa|Fa].
- rewrite (finite_not_nan prec emax a Fa), Fa. cbn [negb].
  unfold finite, val. rewrite (guard_val prec emax nan_plus).
  split.
  + left. unfold finite, val.
    rewrite (guard_finite prec emax nan_plus), (guard_val prec emax nan_plus).
    split; [exact Fa|split; [reflexivity|apply normalized_2_lead]].
  + change (B2R prec emax pzero) with 0. now rewrite Rplus_0_r.
- rewrite Fa. destruct (not_finite_cases prec emax a Fa) as [Na|[s Ea]].
  + rewrite Na. cbn [negb]. split; [|reflexivity].
    right. right. unfold nan. rewrite (guard_nan prec emax nan_plus). now split.
  + subst a. cbn [is_nan negb]. rewrite (guard_inf prec emax nan_plus). split; [|reflexivity].
    right. left. split; [now exists s|now exists false].
Qed.

(** * make_2_limbs *)

Lemma make_2_limbs_facts :
  forall h l : float, canonical_2 h l ->
  let '(x0, x1) := IeeeDraft.make_2_limbs prec emax nan_plus h l in
  canonical_2 x0 x1 /\ xval_2 x0 x1 = xval_2 h l /\
  (fin h -> b2r x0 = b2r h /\ b2r x1 = b2r l).
Proof.
intros h l C. unfold IeeeDraft.make_2_limbs. cbv beta iota zeta.
unfold xval_2. rewrite (guard_finite prec emax nan_plus), (guard_nan prec emax nan_plus).
split; [|split].
- destruct C as [[Fh [Fl N]]|[[[s E] [s' E']]|[Nh Nl]]].
  + left. unfold finite, val in *.
    rewrite 2!(guard_finite prec emax nan_plus), 2!(guard_val prec emax nan_plus). auto.
  + subst h l. rewrite (guard_inf prec emax nan_plus), (guard_zero prec emax nan_plus).
    right. left. split; [now exists s|now exists false].
  + right. right. unfold nan in *. rewrite 2!(guard_nan prec emax nan_plus). now split.
- destruct (is_finite prec emax h) eqn:Fh.
  + unfold val. now rewrite 2!(guard_val prec emax nan_plus).
  + destruct (not_finite_cases prec emax h Fh) as [Nh|[s Eh]].
    * now rewrite Nh.
    * subst h. now rewrite (guard_inf prec emax nan_plus).
- intros _. split; apply (guard_val prec emax nan_plus).
Qed.

End IeeeMake.

Theorem make_2_correct : make_2_spec.
Proof. intros prec emax Hp He nan_plus a. exact (make_2_facts prec emax nan_plus a). Qed.

Theorem make_2_limbs_correct : make_2_limbs_spec.
Proof.
intros prec emax Hp He nan_plus h l C. exact (make_2_limbs_facts prec emax nan_plus h l C).
Qed.
