(* The product of two polynomials in the IEEE model: the generated statements
   conv_1_ieee_spec and conv_2_ieee_spec (proofs/gen/IeeeFoldStatements.v).

   The model (proofs/gen/IeeeFoldModel.v). Coefficient j of the product of xs and ys is
   the final state of the dot product dot_k, in its sequential order, on the terms
   conv_terms xs ys j: fold_seq of its step from the zero state, without its finish. The
   convolution keeps a mask, the and of the check of every coefficient (its leading limb
   is finite), and when the mask is false every coefficient is replaced by what the check
   returns of it (the second pass), as a map does.

   The statement, coefficient by coefficient (Forall2 of the indices and the
   coefficients): if the leading limb of a coefficient is finite, every limb of every
   term is finite, the values are those of the real-model dot product on the values of
   the terms, and the conclusions of dot_k_seq_spec hold of them; otherwise every limb of
   the coefficient is a NaN; and the mask is true exactly when the leading limb of every
   coefficient is finite.

   How. The mask and the second pass are those of a map whose step, on an index j, is the
   state of the dot product on the terms of j: map_k_true and map_k_false of
   IeeeFoldMaps.v. Coefficient by coefficient, the theorem of the dot product in the IEEE
   model, dot_k_seq_ieee_correct (IeeeFolds.v), is about the finish of that state, and
   the finish of a state whose leading limb is finite returns it with the flag true
   (fold_finish_k_correct, IeeeFoldFinish.v): so its conclusions hold of the state. For
   two limbs the terms are canonical when the entries of both polynomials are
   (conv_terms_Forall, FoldConv.v). *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel IeeeFoldStatements.
From Kairn Require Import IeeeVocabulary Folds Summation IeeeFoldFinish IeeeFolds FoldConv
  IeeeFoldMaps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

Theorem conv_1_ieee_correct : conv_1_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma nan_const Hp1 xs ys.
(* A coefficient whose leading limb is finite. *)
assert (Good : forall (j : nat) (w : binary_float prec emax),
  fold_seq (IeeeFoldModel.dot_1_step prec emax nan_fma) (IeeeOperations.pzero prec emax)
    (conv_terms xs ys j) = w -> finite w ->
  let xys := conv_terms xs ys j in
  Forall (fun xy => finite (fst xy) /\ finite (snd xy)) xys /\
  let vs := map (fun xy => (val (fst xy), val (snd xy))) xys in
  let s := FoldModel.dot_1_seq (ieee_emin prec emax) prec tie_even vs in
  val w = s /\ fmt (ieee_emin prec emax) prec s /\
  Rabs (s - sumR (map (fun xy => (fst xy * snd xy)) vs)) <=
     ((1 + (u prec / (1 + u prec))) ^ length vs - 1) *
       sumabs (map (fun xy => (fst xy * snd xy)) vs) +
     (1 + (u prec / (1 + u prec))) ^ (length vs - 1) *
       (INR (length vs) * (eta (ieee_emin prec emax) / 2))).
{ intros j w Ew Fw.
  generalize (dot_1_seq_ieee_correct prec emax Hp He nan_abs nan_fma nan_const Hp1
                (conv_terms xs ys j)).
  unfold IeeeFoldModel.dot_1_seq. cbv zeta. rewrite Ew.
  generalize (fold_finish_1_correct prec emax Hp He nan_abs nan_const w).
  destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const w) as [r flag].
  intros [F1 [F2 _]] [H1 _].
  assert (Ef : flag = true) by (apply F1; exact Fw).
  specialize (H1 Ef). rewrite (F2 Ef) in H1.
  destruct H1 as [HF [_ R]]. split. exact HF. exact R. }
unfold IeeeFoldModel.conv_1_conv. cbv zeta. rewrite fold_seq_and.
match goal with |- context [forallb ?t (map ?f ?l)] => destruct (forallb t (map f l)) eqn:? end;
  cbv beta iota.
- eapply map_1_true; try exact (Forall_True _ _); try eassumption.
  intros j w _ Ew Fw. cbv beta iota zeta. split.
  + intros _. exact (Good j w Ew Fw).
  + intros N. contradiction.
- eapply map_1_false; try exact (Forall_True _ _); try eassumption.
  + intros j w _ Ew Fw. cbv beta iota zeta. split.
    * intros _. exact (Good j w Ew Fw).
    * intros N. contradiction.
  + intros j w _ _ Nw. cbv beta iota zeta. split.
    * intros Fw. exfalso. exact (nan_1_not_finite _ _ w Nw Fw).
    * intros _. split; [exact Nw | reflexivity].
Qed.

Theorem conv_2_ieee_correct : conv_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 xs ys Hx Hy.
(* A coefficient whose leading limb is finite. *)
assert (Good : forall (j : nat) (z0 z1 : binary_float prec emax),
  fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
    (IeeeOperations.pzero prec emax, IeeeOperations.pzero prec emax) (conv_terms xs ys j) =
    (z0, z1) -> finite z0 ->
  let xys := conv_terms xs ys j in
  Forall (fun xy => finite (fst (fst xy)) /\ finite (snd (fst xy)) /\ finite (fst (snd xy)) /\
                    finite (snd (snd xy))) xys /\
  finite z1 /\
  let vs := map (fun xy => ((val (fst (fst xy)), val (snd (fst xy))),
                            (val (fst (snd xy)), val (snd (snd xy))))) xys in
  let s := FoldModel.dot_2_seq (ieee_emin prec emax) prec tie_even vs in
  (val z0, val z1) = s /\
  normalized_2 (ieee_emin prec emax) prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun xy => ((fst (fst xy) + snd (fst xy)) *
                                               (fst (snd xy) + snd (snd xy)))) vs)) <=
     ((1 + (4 * (u prec ^ 2))) *
        (1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length vs - 1) - 1) *
       sumabs (map (fun xy => ((fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy)))) vs) +
     (1 + ((3 * (u prec ^ 2)) / (1 - (4 * u prec)))) ^ (length vs - 1) *
       (INR (length vs) * ((3 / 2) * eta (ieee_emin prec emax)))).
{ intros j z0 z1 Ew Fz.
  generalize (dot_2_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma
                nan_const Hp4 (conv_terms xs ys j)
                (conv_terms_Forall _ _ (fun x => canonical_2 (fst x) (snd x))
                   (fun y => canonical_2 (fst y) (snd y)) xs ys j Hx Hy)).
  unfold IeeeFoldModel.dot_2_seq. cbv zeta. rewrite Ew. cbn [fst snd].
  generalize (fold_finish_2_correct prec emax Hp He nan_abs nan_const z0 z1).
  destruct (IeeeModel.fold_finish_2 prec emax nan_abs nan_const z0 z1) as [[r0 r1] flag].
  intros [F1 [F2 _]] [H1 _].
  assert (Ef : flag = true) by (apply F1; exact Fz).
  specialize (H1 Ef). destruct (F2 Ef) as [E0 E1]. rewrite E0, E1 in H1.
  destruct H1 as [HF [_ [Fz1 R]]]. split. exact HF. split. exact Fz1. exact R. }
unfold IeeeFoldModel.conv_2_conv. cbv zeta. rewrite fold_seq_and.
match goal with |- context [forallb ?t (map ?f ?l)] => destruct (forallb t (map f l)) eqn:? end;
  cbv beta iota.
- eapply map_2_true; try exact (Forall_True _ _); try eassumption.
  intros j [z0 z1] _ Ew Fz. cbv beta iota zeta. cbn [fst snd] in *. split.
  + intros _. exact (Good j z0 z1 Ew Fz).
  + intros N. contradiction.
- eapply map_2_false; try exact (Forall_True _ _); try eassumption.
  + intros j [z0 z1] _ Ew Fz. cbv beta iota zeta. cbn [fst snd] in *. split.
    * intros _. exact (Good j z0 z1 Ew Fz).
    * intros N. contradiction.
  + intros j [w0 w1] _ _ [N0 N1]. cbv beta iota zeta. cbn [fst snd] in *. split.
    * intros Fw. exfalso. exact (nan_1_not_finite _ _ w0 N0 Fw).
    * intros _. split; [assumption | split; [assumption | reflexivity]].
Qed.
