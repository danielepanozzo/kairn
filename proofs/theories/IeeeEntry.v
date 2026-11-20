(* The building blocks on T that become public in Milestone 2, in the IEEE model, on all
   values: next_up and next_down, and the entry forms of the directed sums, of radd and of
   fast_two_sum (docs/developer/design/milestone2.md, "next_up and next_down on every
   input", "Values that enter from the program"). The statements are those of
   proofs/gen/IeeeStatements.v.

   What is proved:
   - next_up a and next_down a are nextUp and nextDown of IEEE 754 on every input
     (next_up_ieee, next_down_ieee): as extended real numbers they are xsucc and xpred of
     the operand. A finite number goes to its neighbor in the format, or to the infinity
     beyond the largest number; +infinity stays under next_up and goes to Omega under
     next_down, -infinity goes to -Omega under next_up and stays under next_down; a NaN
     stays a NaN. The sign of a zero result is not part of the statement.
   - the guard keeps the extended real number of its operand (xval_guard), and a value
     that is nonnegative, +infinity or NaN stays one (guard_nonneg). So an entry form,
     which guards its operands and calls the kernel of the same name, has that kernel's
     statement: add_down_entry, add_up_entry, sub_down_entry, sub_up_entry (the directed
     rounding of the sum or difference of IEEE 754), radd_entry (as radd), and
     fast_two_sum_entry (as fast_two_sum, on finite operands). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt IeeeDirected.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeEntry.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).

(** * next_up and next_down *)

Lemma pred_ninf : fpred ninf = ninf.
Proof.
apply B2BSN_inf_inv. unfold IeeeOperations.pred, Bpred. rewrite B2BSN_lift. reflexivity.
Qed.

(* next_up on every input. *)
Theorem next_up_ieee : forall a : float, xv (fsucc a) = xsucc prec emax (xv a).
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- rewrite (xval_fin prec emax a F). unfold xsucc, overflow_of.
  change (ieee_emin prec emax) with emin.
  generalize (b2r_inrange prec emax a) (succ_ge_id radix2 fexp (b2r a))
             (bpow_gt_0 radix2 emax).
  intros K S P. apply Rabs_lt_inv in K.
  destruct (succ_finite prec emax a F) as [[Fs [Es Ls]]|[Es Ls]].
  + rewrite (xval_fin prec emax _ Fs), Es.
    rewrite Rlt_bool_true; [reflexivity|]. apply Rabs_lt. lra.
  + rewrite Es. rewrite Rlt_bool_false by (rewrite Rabs_pos_eq; lra).
    rewrite Rlt_bool_false by lra. reflexivity.
- destruct a as [s|[|]|s pl H|s m e H]; try discriminate F.
  + destruct (succ_ninf prec emax) as [Fq Eq]. rewrite (xval_fin prec emax _ Fq), Eq.
    reflexivity.
  + change (B754_infinity prec emax false) with pinf. rewrite (succ_pinf prec emax).
    reflexivity.
  + reflexivity.
Qed.

(* next_down on every input. *)
Theorem next_down_ieee : forall a : float, xv (fpred a) = xpred prec emax (xv a).
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- rewrite (xval_fin prec emax a F). unfold xpred, xsucc, overflow_of. cbn [xopp].
  change (ieee_emin prec emax) with emin.
  generalize (b2r_inrange prec emax a) (succ_ge_id radix2 fexp (- b2r a))
             (bpow_gt_0 radix2 emax).
  intros K S P. apply Rabs_lt_inv in K.
  destruct (pred_finite prec emax a F) as [[Fs [Es Ls]]|[Es Ls]];
    unfold Ulp.pred in Es, Ls.
  + rewrite (xval_fin prec emax _ Fs), Es.
    rewrite Rlt_bool_true; [reflexivity|]. apply Rabs_lt. lra.
  + rewrite Es. rewrite Rlt_bool_false by (rewrite Rabs_pos_eq; lra).
    rewrite Rlt_bool_false by lra. reflexivity.
- destruct a as [s|[|]|s pl H|s m e H]; try discriminate F.
  + rewrite pred_ninf. reflexivity.
  + destruct (pred_pinf prec emax) as [Fq Eq].
    change (B754_infinity prec emax false) with pinf.
    rewrite (xval_fin prec emax _ Fq), Eq.
    change (xpred prec emax (xv pinf)) with (XFin (- - Om)).
    now rewrite Ropp_involutive.
  + reflexivity.
Qed.

(** * The guard *)

(* The guard keeps the extended real number of its operand. *)
Lemma xval_guard : forall a : float, xv (guard a) = xv a.
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- assert (F' : fin (guard a)) by (rewrite (guard_finite prec emax nan_plus); exact F).
  rewrite (xval_fin prec emax a F), (xval_fin prec emax (guard a) F').
  f_equal. apply (guard_val prec emax nan_plus).
- destruct a as [s|s|s pl H|s m e H]; try discriminate F; reflexivity.
Qed.

(* A value that is nonnegative, +infinity or NaN stays one. *)
Lemma guard_nonneg : forall a : float, nonneg_ext a -> nonneg_ext (guard a).
Proof.
intros a [N|[I|[F P]]].
- left. unfold nan in *. now rewrite (guard_nan prec emax nan_plus).
- right. left. rewrite I. reflexivity.
- right. right. unfold finite, val in *.
  rewrite (guard_finite prec emax nan_plus), (guard_val prec emax nan_plus). now split.
Qed.

(** * The entry forms *)

Theorem add_down_entry_ieee :
  (2 <= prec)%Z -> forall a b : float,
  xv (IeeeModel.add_down_entry prec emax nan_plus nan_minus nan_abs a b)
  = xrd prec emax (xadd (xv a) (xv b)).
Proof.
intros Hp a b. unfold IeeeModel.add_down_entry. cbv zeta.
rewrite (add_down_1_ieee prec emax nan_plus nan_minus nan_abs Hp), 2!xval_guard. reflexivity.
Qed.

Theorem add_up_entry_ieee :
  (2 <= prec)%Z -> forall a b : float,
  xv (IeeeModel.add_up_entry prec emax nan_plus nan_minus nan_abs a b)
  = xru prec emax (xadd (xv a) (xv b)).
Proof.
intros Hp a b. unfold IeeeModel.add_up_entry. cbv zeta.
rewrite (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp), 2!xval_guard. reflexivity.
Qed.

Theorem sub_down_entry_ieee :
  (2 <= prec)%Z -> forall a b : float,
  xv (IeeeModel.sub_down_entry prec emax nan_plus nan_minus nan_opp nan_abs a b)
  = xrd prec emax (xadd (xv a) (xopp (xv b))).
Proof.
intros Hp a b. unfold IeeeModel.sub_down_entry. cbv zeta.
rewrite (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp), 2!xval_guard.
reflexivity.
Qed.

Theorem sub_up_entry_ieee :
  (2 <= prec)%Z -> forall a b : float,
  xv (IeeeModel.sub_up_entry prec emax nan_plus nan_minus nan_opp nan_abs a b)
  = xru prec emax (xadd (xv a) (xopp (xv b))).
Proof.
intros Hp a b. unfold IeeeModel.sub_up_entry. cbv zeta.
rewrite (sub_up_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp), 2!xval_guard.
reflexivity.
Qed.

(* radd_entry on operands that are nonnegative, +infinity or NaN: as radd. *)
Theorem radd_entry_ieee :
  (2 <= prec)%Z -> forall a b : float, nonneg_ext a -> nonneg_ext b ->
  let r := IeeeModel.radd_entry prec emax nan_plus a b in
  nonneg_ext r /\
  (fin r -> fin a /\ fin b /\ b2r a + b2r b <= b2r r /\
   b2r r - (b2r a + b2r b) <= 3 / 2 * (b2r r - Ulp.pred radix2 fexp (b2r r))).
Proof.
intros Hp a b Ha Hb. unfold IeeeModel.radd_entry. cbv zeta.
generalize (radd_ext prec emax nan_plus Hp (guard a) (guard b)
              (guard_nonneg a Ha) (guard_nonneg b Hb)).
cbv zeta. intros [Hr Fr]. split; [exact Hr|].
intros F. destruct (Fr F) as [Fa [Fb K]].
rewrite (guard_finite prec emax nan_plus) in Fa, Fb.
rewrite 2!(guard_val prec emax nan_plus) in K.
split; [exact Fa|split; [exact Fb|exact K]].
Qed.

(* fast_two_sum_entry on finite operands with |b| <= |a|: as fast_two_sum. *)
Theorem fast_two_sum_entry_ieee :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b ->
  Rabs (b2r b) <= Rabs (b2r a) ->
  let '(s, e) := IeeeModel.fast_two_sum_entry prec emax nan_plus nan_minus a b in
  fin s ->
  fin e /\
  b2r s = RN emin prec (b2r a + b2r b) /\
  b2r s + b2r e = b2r a + b2r b /\
  normalized_2 emin prec (b2r s) (b2r e).
Proof.
intros Hp a b Fa Fb Hab. unfold IeeeModel.fast_two_sum_entry. cbv zeta.
assert (Fga : fin (guard a)) by (rewrite (guard_finite prec emax nan_plus); exact Fa).
assert (Fgb : fin (guard b)) by (rewrite (guard_finite prec emax nan_plus); exact Fb).
assert (Hg : Rabs (b2r (guard b)) <= Rabs (b2r (guard a))).
{ now rewrite 2!(guard_val prec emax nan_plus). }
generalize (fast_two_sum_ieee_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              Hp (guard a) (guard b) Fga Fgb Hg).
unfold finite, val, ieee_emin. rewrite 2!(guard_val prec emax nan_plus).
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (guard a) (guard b)) as [s e].
trivial.
Qed.

End IeeeEntry.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem next_up_ieee_correct : next_up_ieee_spec.
Proof. intros prec emax Hp0 He Hp a. exact (next_up_ieee prec emax a). Qed.

Theorem next_down_ieee_correct : next_down_ieee_spec.
Proof. intros prec emax Hp0 He Hp a. exact (next_down_ieee prec emax a). Qed.

Theorem add_down_entry_ieee_correct : add_down_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_abs Hp a b.
exact (add_down_entry_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
Qed.

Theorem add_up_entry_ieee_correct : add_up_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_abs Hp a b.
exact (add_up_entry_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
Qed.

Theorem sub_down_entry_ieee_correct : sub_down_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp a b.
exact (sub_down_entry_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp a b).
Qed.

Theorem sub_up_entry_ieee_correct : sub_up_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs Hp a b.
exact (sub_up_entry_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp a b).
Qed.

Theorem radd_entry_ieee_correct : radd_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus Hp a b Ha Hb.
exact (radd_entry_ieee prec emax nan_plus Hp a b Ha Hb).
Qed.

Theorem fast_two_sum_entry_ieee_correct : fast_two_sum_entry_ieee_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus Hp a b Fa Fb Hab.
exact (fast_two_sum_entry_ieee prec emax nan_plus nan_minus Hp a b Fa Fb Hab).
Qed.
