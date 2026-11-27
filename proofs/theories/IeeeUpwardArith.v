(* The arithmetic kernels of the round-up interval in the IEEE model, on all values: the sum,
   the difference, the negation, the product, and the sum and the product with a number of the
   program (docs/developer/design/upward.md, "The kernels", "Statements" and "How they are to
   be proved"). The theorems K_correct establish the generated statements K_spec of
   proofs/gen/UpwardStatements.v about the generated models of proofs/gen/UpwardModel.v:
   upward_add_1, upward_sub_1, upward_neg_1, upward_mul_1, upward_add_num_1 and
   upward_mul_num_1. For every precision, every choice of the NaN each operation returns, and
   (for the products) every max_nl with the property max_nl_ok, so both machine forms of the
   maximum.

   Notation: as in IeeeUpwardOps.v. A state (u, n) is the interval [-n, u]; for the operands
   x = (xu, xn) = [a, b] and y = (yu, yn) = [c, d]. xrd and xru are the roundings down and up
   in the format with overflow; the exact range of an operation and its bounds are those of
   IeeeIntervalVocabulary.v.

   What is proved. Each statement says I1 the result is canonical, I2 it is empty exactly
   when an operand is, I3 it contains the exact range, I4 for nonempty operands its bounds are
   the bounds of the exact range rounded outward (exactly, for the negation), and I5 for
   bounded operands (and a finite number) it is bounded exactly when the exact range is within
   Omega. The products are exactly rounded: no step of slack.

   The proofs. Each is the listing put together with the lemmas of the first part:
   - the sum and the difference: two NaN lanes for an empty operand (add_ru_nan_l and _r);
     for nonempty operands the lane u is xru of the sum of the upper bounds (add_ru_xval) and
     the lane n the opposite of xrd of the sum of the lower bounds (add_ru_lower), which are
     the bounds of the exact range (upward_range_add, upward_range_sub); then
     upward_binary_facts gives I1 to I5;
   - the product: the last line makes the empty set when an operand is empty
     (unord_states, cnan_nan); for nonempty operands the two lanes before it are xru of the
     greatest and the opposite of xrd of the least of the four products of bounds with
     0 * infinity = 0 (upward_mul_lane_u and _n, the case analysis of the seed and the dropped
     candidates), the bounds of the exact range (upward_range_mul);
   - the sum and the product with a number t: for a finite t, the same with [t, t]
     (upward_range_add_num, upward_mul_num_lane_u and _n, upward_range_mul_num); for a t that
     is infinite or a NaN, the whole line: x + (+inf, +inf) lane by lane (upward_range_add_whole),
     and for the product the test of |u| + |n| (whole_mul_test), which tells [0, 0], whose
     product with the whole line is [0, 0], from the other nonempty states, whose product is
     the whole line (upward_range_mul_whole); an empty x gives a NaN in both lanes
     (whole_mul_nan);
   - the negation: the two lanes exchanged are the opposites of the bounds, exchanged, which
     are the bounds of the exact range of -x (upward_range_neg). *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeOps IeeeExt IeeeDirected.
From Kairn Require Import Rectangle IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Import IeeeUpwardVocabulary IeeeUpwardMax IeeeUpwardOps IeeeUpwardProduct.
From Kairn Require Import IeeeUpwardRange.
From Kairn Require IeeeOperations IeeeUpwardOperations.
From Kairn.Gen Require Import UpwardStatements.
From Kairn.Gen Require UpwardModel.
Open Scope R_scope.

(** * Two facts the listings need beside those of the first part *)

(* Whether a pair of extended real numbers is (0, 0): the state [0, 0], which the product with
   the whole line tells apart. *)
Lemma upward_zero_pair_dec :
  forall v w : xreal, (v = XFin 0 /\ w = XFin 0) \/ ~ (v = XFin 0 /\ w = XFin 0).
Proof.
assert (D : forall v : xreal, v = XFin 0 \/ v <> XFin 0).
{ intros [|s|r]; [right; discriminate|right; discriminate|].
  destruct (Req_dec r 0) as [E|E]; [left; now rewrite E|right; intros K; apply E; now inversion K]. }
intros v w. destruct (D v) as [Ev|Ev]; [destruct (D w) as [Ew|Ew]|].
- now left.
- right. intros [_ K]. exact (Ew K).
- right. intros [K _]. exact (Ev K).
Qed.

Section IeeeUpwardArith.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.

Notation xv := (@xval prec emax).
Notation add_ru := (IeeeUpwardOperations.add_ru prec emax nan_plus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).

(* The lines of upward_mul_num_1 for a t that is infinite or a NaN, on a lane p that is a NaN
   (an empty x): s = add_ru(abs(p), abs(q)) is a NaN, lt(0, s) is false, and the lane is s. *)
Lemma whole_mul_nan :
  forall p q : float, nan p ->
  nan (if flt pzero (add_ru (fabs p) (fabs q)) then pinf else add_ru (fabs p) (fabs q)).
Proof.
intros p q N.
assert (A : nan (fabs p)).
{ apply (upward_xval_nan prec emax). rewrite (xval_abs prec emax nan_abs).
  now rewrite (proj2 (upward_xval_nan prec emax p) N). }
assert (S : nan (add_ru (fabs p) (fabs q))) by (now apply add_ru_nan_l).
rewrite (lt_xval prec emax), (proj2 (upward_xval_nan prec emax _) S), (xval_pzero prec emax).
exact S.
Qed.

End IeeeUpwardArith.

(** * The generated statements *)

Theorem upward_add_1_correct : upward_add_1_spec.
Proof.
intros prec emax Hp He nan_plus xu xn yu yn CX CY.
unfold UpwardModel.upward_add_1. cbv beta iota zeta.
apply (upward_binary_facts prec emax (fun x y : R => x + y) xu xn yu yn _ _
         (xadd (xopp (xval xn)) (xopp (xval yn))) (xadd (xval xu) (xval yu)) CX CY).
- intros [[Nu Nn]|[Mu Mn]]; split.
  + now apply add_ru_nan_l.
  + now apply add_ru_nan_l.
  + now apply add_ru_nan_r.
  + now apply add_ru_nan_r.
- intros NX NY. destruct (upward_range_add prec emax xu xn yu yn NX NY) as [L U].
  split; [exact L|split; [exact U|split]].
  + apply add_ru_lower.
  + apply add_ru_xval.
- exact (upward_range_add_real prec emax xu xn yu yn).
Qed.

Theorem upward_sub_1_correct : upward_sub_1_spec.
Proof.
intros prec emax Hp He nan_plus xu xn yu yn CX CY.
unfold UpwardModel.upward_sub_1. cbv beta iota zeta.
apply (upward_binary_facts prec emax (fun x y : R => x - y) xu xn yu yn _ _
         (xadd (xopp (xval xn)) (xopp (xval yu))) (xadd (xval xu) (xval yn)) CX CY).
- intros [[Nu Nn]|[Mu Mn]]; split.
  + now apply add_ru_nan_l.
  + now apply add_ru_nan_l.
  + now apply add_ru_nan_r.
  + now apply add_ru_nan_r.
- intros NX NY. destruct (upward_range_sub prec emax xu xn yu yn NX NY) as [L U].
  split; [exact L|split; [exact U|split]].
  + apply add_ru_lower.
  + apply add_ru_xval.
- exact (upward_range_sub_real prec emax xu xn yu yn).
Qed.

Theorem upward_neg_1_correct : upward_neg_1_spec.
Proof.
intros prec emax Hp He xu xn CX.
unfold UpwardModel.upward_neg_1. cbv beta iota zeta.
assert (I3 : forall x : R, in_upward_1 xu xn x -> in_upward_1 xn xu (- x)).
{ intros x Hx. unfold in_upward_1 in *.
  generalize (xmember_opp _ _ x Hx). now rewrite xopp_involutive. }
split; [|split; [|split; [exact I3|split]]].
- (* I1 *)
  destruct CX as [[Nu Nn]|NX]; [left; split; assumption|right].
  unfold upward_nonempty_1 in *. generalize (xnonempty_opp _ _ NX). now rewrite xopp_involutive.
- (* I2 *)
  unfold upward_empty_1. tauto.
- (* I4: the negation is exact *)
  intros NX lo hi Hlo Hhi. destruct (upward_range_neg prec emax xu xn NX) as [L U].
  destruct (upward_nonempty_member prec emax xu xn NX) as [x Hx].
  assert (Ex : exists z : R, range_1 (fun x : R => - x) (in_upward_1 xu xn) z).
  { exists (- x), x. split; [exact Hx|reflexivity]. }
  split; [exact (range_lower_unique _ _ _ Ex L Hlo)|exact (range_upper_unique _ _ _ Ex U Hhi)].
- (* I5: both sides hold for a bounded operand *)
  intros [Fu Fn]. split; [intros _|intros _; split; assumption].
  intros z [x [Hx Ez]]. cbv beta in Ez. subst z. rewrite Rabs_Ropp.
  unfold in_upward_1, xmember in Hx.
  rewrite (upward_xval_finite prec emax xu Fu), (upward_xval_finite prec emax xn Fn) in Hx.
  cbn [xopp xle] in Hx. destruct Hx as [H1 H2].
  apply Rle_bool_inv in H1. apply Rle_bool_inv in H2.
  generalize (b2r_Omega prec emax xu) (b2r_Omega prec emax xn). unfold val in *.
  intros P Q. change (omega prec emax) with (Omega prec emax). apply Rabs_le. lra.
Qed.

Theorem upward_mul_1_correct : upward_mul_1_spec.
Proof.
intros prec emax Hp He nan_mult nan_opp nan_const max_nl Hm xu xn yu yn CX CY.
unfold UpwardModel.upward_mul_1. cbv beta iota zeta.
apply (upward_binary_facts prec emax (fun x y : R => x * y) xu xn yu yn _ _
         (xmin (xmin (xmul0 (xopp (xval xn)) (xopp (xval yn))) (xmul0 (xopp (xval xn)) (xval yu)))
               (xmin (xmul0 (xval xu) (xopp (xval yn))) (xmul0 (xval xu) (xval yu))))
         (xmax (xmax (xmul0 (xopp (xval xn)) (xopp (xval yn))) (xmul0 (xopp (xval xn)) (xval yu)))
               (xmax (xmul0 (xval xu) (xopp (xval yn))) (xmul0 (xval xu) (xval yu))))
         CX CY).
- (* an empty operand: the last line makes the empty set *)
  intros E. destruct (unord_states prec emax xu xn yu yn CX CY) as [[_ Ku] [_ Kn]].
  rewrite (Ku E), (Kn E). split; apply cnan_nan.
- (* nonempty operands: the lanes are the bounds of the exact range rounded outward *)
  intros NX NY.
  destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu [Nn _]].
  destruct (upward_nonempty_lanes prec emax yu yn NY) as [Mu [Mn _]].
  rewrite (unord_not_nan prec emax xu yu Nu Mu), (unord_not_nan prec emax xn yn Nn Mn).
  pose proof (upward_range_mul prec emax xu xn yu yn NX NY) as R. cbv zeta in R.
  destruct R as [L U].
  pose proof (upward_mul_lane_u prec emax nan_mult nan_opp max_nl Hm xu xn yu yn NX NY) as Gu.
  cbv zeta in Gu. destruct Gu as [_ Gu].
  pose proof (upward_mul_lane_n prec emax nan_mult nan_opp max_nl Hm xu xn yu yn NX NY) as Gn.
  cbv zeta in Gn. destruct Gn as [_ Gn].
  split; [exact L|split; [exact U|split; [exact Gn|exact Gu]]].
- intros BX BY. pose proof (upward_range_mul_real prec emax xu xn yu yn BX BY) as R.
  cbv zeta in R. exact R.
Qed.

Theorem upward_add_num_1_correct : upward_add_num_1_spec.
Proof.
intros prec emax Hp He nan_plus nan_opp nan_abs xu xn t CX.
unfold UpwardModel.upward_add_num_1. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs t).
destruct (is_finite prec emax t) eqn:Ft; cbv beta iota.
- (* a finite t: x + [t, t] *)
  assert (FT : finite t) by exact Ft.
  apply (upward_number_facts prec emax (fun x y : R => x + y) xu xn t _ _
           (xadd (xopp (xval xn)) (xval t)) (xadd (xval xu) (xval t)) CX).
  + intros [Nu Nn]. split; now apply add_ru_nan_l.
  + intros NX. destruct (upward_range_add_num prec emax xu xn t NX FT) as [L U].
    split; [exact L|split; [exact U|split]].
    * rewrite (add_ru_lower prec emax nan_plus), (xval_neg prec emax nan_opp), xopp_involutive.
      reflexivity.
    * apply add_ru_xval.
  + intros BX _. exact (upward_range_add_num_real prec emax xu xn t BX FT).
- (* t infinite or a NaN: x + the whole line, lane by lane *)
  assert (NF : ~ finite t) by (unfold finite; rewrite Ft; discriminate).
  apply (upward_number_facts prec emax (fun x y : R => x + y) xu xn t _ _
           (XInf true) (XInf false) CX).
  + intros [Nu Nn]. split; now apply add_ru_nan_l.
  + intros NX. destruct (upward_range_add_whole prec emax xu xn t NX NF) as [L U].
    destruct (upward_nonempty_lane prec emax xu xn NX) as [Lu Ln].
    apply upward_lane_xval in Lu. apply upward_lane_xval in Ln.
    split; [exact L|split; [exact U|split]].
    * rewrite (add_ru_xval prec emax nan_plus). destruct Ln as [E|[r E]]; rewrite E; reflexivity.
    * rewrite (add_ru_xval prec emax nan_plus). destruct Lu as [E|[r E]]; rewrite E; reflexivity.
  + intros _ K. exfalso. exact (NF K).
Qed.

Theorem upward_mul_num_1_correct : upward_mul_num_1_spec.
Proof.
intros prec emax Hp He nan_plus nan_mult nan_opp nan_abs nan_const max_nl Hm xu xn t CX.
unfold UpwardModel.upward_mul_num_1. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs t).
destruct (is_finite prec emax t) eqn:Ft; cbv beta iota.
- (* a finite t: x * [t, t], two candidates per lane *)
  assert (FT : finite t) by exact Ft.
  apply (upward_number_facts prec emax (fun x y : R => x * y) xu xn t _ _
           (xmin (xmul0 (xopp (xval xn)) (xval t)) (xmul0 (xval xu) (xval t)))
           (xmax (xmul0 (xopp (xval xn)) (xval t)) (xmul0 (xval xu) (xval t))) CX).
  + intros E. destruct (unord_state prec emax xu xn CX) as [[_ Ku] [_ Kn]].
    rewrite (Ku E), (Kn E). split; apply cnan_nan.
  + intros NX. destruct (upward_nonempty_lanes prec emax xu xn NX) as [Nu [Nn _]].
    rewrite (unord_not_nan prec emax xu xu Nu Nu), (unord_not_nan prec emax xn xn Nn Nn).
    pose proof (upward_range_mul_num prec emax xu xn t NX FT) as R. cbv zeta in R.
    destruct R as [L U].
    pose proof (upward_mul_num_lane_u prec emax nan_mult nan_opp max_nl Hm xu xn t NX FT) as Gu.
    cbv zeta in Gu. destruct Gu as [_ Gu].
    pose proof (upward_mul_num_lane_n prec emax nan_mult nan_opp max_nl Hm xu xn t NX FT) as Gn.
    cbv zeta in Gn. destruct Gn as [_ Gn].
    split; [exact L|split; [exact U|split; [exact Gn|exact Gu]]].
  + intros BX _. pose proof (upward_range_mul_num_real prec emax xu xn t BX FT) as R.
    cbv zeta in R. exact R.
- (* t infinite or a NaN: x * the whole line, told by |u| + |n| *)
  assert (NF : ~ finite t) by (unfold finite; rewrite Ft; discriminate).
  destruct (upward_zero_pair_dec (xval xu) (xval xn)) as [Z|Z].
  + (* x = [0, 0]: the result is [0, 0] *)
    apply (upward_number_facts prec emax (fun x y : R => x * y) xu xn t _ _
             (XFin 0) (XFin 0) CX).
    * intros [Nu Nn]. split; apply whole_mul_nan; assumption.
    * intros NX. destruct (upward_nonempty_lane prec emax xu xn NX) as [Lu Ln].
      destruct (whole_mul_test prec emax nan_plus nan_abs xu xn Lu Ln) as [Tu _].
      destruct (whole_mul_test prec emax nan_plus nan_abs xn xu Ln Lu) as [Tn _].
      destruct (Tu Z) as [Vu Gu]. destruct (Tn (conj (proj2 Z) (proj1 Z))) as [Vn Gn].
      rewrite Gu, Gn. cbv beta iota.
      pose proof (upward_range_mul_whole prec emax xu xn t NX NF) as R. cbv zeta in R.
      destruct R as [R _]. destruct (R Z) as [L U].
      split; [exact L|split; [exact U|split]].
      -- rewrite Vn, (xrd_0 prec emax). cbn [xopp]. now rewrite Ropp_0.
      -- rewrite Vu. symmetry. apply (xru_0 prec emax).
    * intros _ K. exfalso. exact (NF K).
  + (* any other nonempty x: the whole line *)
    apply (upward_number_facts prec emax (fun x y : R => x * y) xu xn t _ _
             (XInf true) (XInf false) CX).
    * intros [Nu Nn]. split; apply whole_mul_nan; assumption.
    * intros NX. destruct (upward_nonempty_lane prec emax xu xn NX) as [Lu Ln].
      destruct (whole_mul_test prec emax nan_plus nan_abs xu xn Lu Ln) as [_ Tu].
      destruct (whole_mul_test prec emax nan_plus nan_abs xn xu Ln Lu) as [_ Tn].
      rewrite (Tu Z), (Tn (fun K => Z (conj (proj2 K) (proj1 K)))). cbv beta iota.
      pose proof (upward_range_mul_whole prec emax xu xn t NX NF) as R. cbv zeta in R.
      destruct R as [_ R]. destruct (R Z) as [L U].
      split; [exact L|split; [exact U|split; reflexivity]].
    * intros _ K. exfalso. exact (NF K).
Qed.
