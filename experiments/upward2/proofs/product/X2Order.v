(* EXPERIMENTAL proof probe. Statement 1 of the product: for upper-normalized pairs the order of
   the values is the lexicographic order of (h, l), so lexmax returns the pair of the greater
   value; and the sign of the head is the sign of the value (the sign tests of the product read
   the heads only). Model and definitions: X2Defs.v.

   Main theorems (Print Assumptions at the end of the file):
   - upper_normalized_order: h1 + l1 <= h2 + l2 <-> h1 < h2 \/ (h1 = h2 /\ l1 <= l2);
   - upper_normalized_unique: equal values give equal pairs (h = RU(value), l = value - h);
   - lexmax_correct: lexmax returns one of the two pairs, exactly, the one of the greater
     value, so its value is the greater value and it is upper-normalized;
   - upper_normalized_sign: h <= 0 <-> h + l <= 0, h < 0 <-> h + l < 0, h = 0 -> l = 0.
   They hold for every positive precision and every emin.

   Also here: the facts about RU used by the other files (ru_ge, ru_le_format, pred_ru_lt, ...),
   each one line of Flocq. *)
From Stdlib Require Import Reals ZArith Lia Lra Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Statements.
From Kairn Require Import Format DirectedProd.
From KairnX2P Require Import X2Defs.
Open Scope R_scope.

Section Round.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation ru := (RU emin prec).

(** * Rounding up: the facts used everywhere *)

Lemma ru_ge : forall x, x <= ru x.
Proof.
intros x. unfold RU. destruct (round_UP_pt radix2 fexp x) as [_ [H _]]. exact H.
Qed.

Lemma ru_format : forall x, format (ru x).
Proof. intros x. unfold RU. apply generic_format_round; auto with typeclass_instances. Qed.

Lemma ru_id : forall x, format x -> ru x = x.
Proof. intros x Fx. unfold RU. apply round_generic; auto with typeclass_instances. Qed.

Lemma ru_le : forall x y, x <= y -> ru x <= ru y.
Proof. intros x y H. unfold RU. apply round_le; auto with typeclass_instances. Qed.

Lemma ru_le_format : forall x y, format y -> x <= y -> ru x <= y.
Proof. intros x y Fy H. unfold RU. apply round_le_generic; auto with typeclass_instances. Qed.

Lemma ru_ge_format : forall x y, format y -> y <= x -> y <= ru x.
Proof. intros x y Fy H. unfold RU. apply round_ge_generic; auto with typeclass_instances. Qed.

Lemma ru_0 : ru 0 = 0.
Proof. unfold RU. apply round_0; auto with typeclass_instances. Qed.

Lemma ru_nonpos : forall x, x <= 0 -> ru x <= 0.
Proof. intros x H. apply ru_le_format; trivial. apply generic_format_0. Qed.

(* The number of the format before RU(x) is below x, strictly. *)
Lemma pred_ru_lt : forall x, pred radix2 fexp (ru x) < x.
Proof.
intros x. destruct (generic_format_EM radix2 fexp x) as [Fx|Fx].
- rewrite ru_id by exact Fx. destruct (Req_dec x 0) as [Z0|Z0].
  + rewrite Z0, pred_0, ulp_FLT_0 by exact prec_gt_0_.
    generalize (bpow_gt_0 radix2 emin). lra.
  + now apply pred_lt_id.
- unfold RU. rewrite pred_UP_eq_DN by (auto with typeclass_instances).
  destruct (round_DN_pt radix2 fexp x) as [F [L _]].
  destruct L as [L|L]; trivial. rewrite L in F. contradiction.
Qed.

(* RU(x) = h for a number h of the format exactly when pred(h) < x <= h. *)
Lemma ru_eq_iff : forall x h, format h -> (ru x = h <-> pred radix2 fexp h < x <= h).
Proof.
intros x h Fh. split.
- intros E. rewrite <- E. split; [apply pred_ru_lt | apply ru_ge].
- intros H. unfold RU. now apply round_UP_eq; auto with typeclass_instances.
Qed.

(* A number of the format in (-eta, eta) is zero. *)
Lemma format_small_zero : forall l, format l -> Rabs l < eta emin -> l = 0.
Proof.
intros l Fl H.
destruct (format_multiple_eta emin prec l Fl) as [m Hm].
assert (E : 0 < pow2 emin) by apply bpow_gt_0.
unfold eta in H. rewrite Hm, Rabs_mult, (Rabs_pos_eq (pow2 emin)) in H by lra.
assert (Hm1 : Rabs (IZR m) < 1).
{ apply Rmult_lt_reg_r with (pow2 emin); lra. }
rewrite <- abs_IZR in Hm1. apply lt_IZR in Hm1.
assert (m = 0%Z) by lia. subst m. rewrite Hm. ring.
Qed.

(** * Upper-normalized pairs *)

Lemma upper_normalized_bounds :
  forall h l, upper_normalized emin prec h l ->
  pred radix2 fexp h < h + l <= h.
Proof.
intros h l [Fh [Fl E]]. apply (ru_eq_iff (h + l) h Fh). exact E.
Qed.

Lemma upper_normalized_l_nonpos : forall h l, upper_normalized emin prec h l -> l <= 0.
Proof. intros h l H. generalize (upper_normalized_bounds h l H). lra. Qed.

(* A smaller head means a smaller value: h1 + l1 <= h1 <= pred(h2) < h2 + l2. *)
Lemma upper_normalized_lt :
  forall h1 l1 h2 l2,
  upper_normalized emin prec h1 l1 -> upper_normalized emin prec h2 l2 ->
  h1 < h2 -> h1 + l1 < h2 + l2.
Proof.
intros h1 l1 h2 l2 N1 N2 H.
assert (P : h1 <= pred radix2 fexp h2).
{ apply pred_ge_gt; auto with typeclass_instances; [apply N1 | apply N2]. }
generalize (upper_normalized_bounds h1 l1 N1) (upper_normalized_bounds h2 l2 N2). lra.
Qed.

(** * Statement 1: the order *)

Theorem upper_normalized_order :
  forall h1 l1 h2 l2,
  upper_normalized emin prec h1 l1 -> upper_normalized emin prec h2 l2 ->
  (h1 + l1 <= h2 + l2 <-> (h1 < h2 \/ (h1 = h2 /\ l1 <= l2))).
Proof.
intros h1 l1 h2 l2 N1 N2. split.
- intros H.
  assert (Hh : ru (h1 + l1) <= ru (h2 + l2)) by now apply ru_le.
  destruct N1 as [_ [_ E1]]. destruct N2 as [_ [_ E2]]. rewrite E1, E2 in Hh.
  destruct Hh as [Hh|Hh]; [now left | right]. split; [exact Hh | lra].
- intros [H|[H1 H2]].
  + apply Rlt_le. now apply upper_normalized_lt.
  + lra.
Qed.

(* Hence an upper-normalized pair is determined by its value. *)
Theorem upper_normalized_unique :
  forall h1 l1 h2 l2,
  upper_normalized emin prec h1 l1 -> upper_normalized emin prec h2 l2 ->
  h1 + l1 = h2 + l2 -> h1 = h2 /\ l1 = l2.
Proof.
intros h1 l1 h2 l2 [_ [_ E1]] [_ [_ E2]] H.
rewrite H, E2 in E1. split; [now rewrite E1 | lra].
Qed.

(* lexmax: the greater of two upper-normalized pairs, exactly one of them. *)
Theorem lexmax_correct :
  forall ah al bh bl,
  upper_normalized emin prec ah al -> upper_normalized emin prec bh bl ->
  let m := lexmax ah al bh bl in
  (m = (ah, al) \/ m = (bh, bl)) /\
  fst m + snd m = Rmax (ah + al) (bh + bl) /\
  upper_normalized emin prec (fst m) (snd m).
Proof.
intros ah al bh bl Na Nb m.
assert (K : m = (ah, al) \/ m = (bh, bl) ->
            fst m + snd m = Rmax (ah + al) (bh + bl) ->
            (m = (ah, al) \/ m = (bh, bl)) /\
            fst m + snd m = Rmax (ah + al) (bh + bl) /\
            upper_normalized emin prec (fst m) (snd m)).
{ intros Hm Hv. split; [exact Hm | split; [exact Hv |]].
  destruct Hm as [Hm|Hm]; rewrite Hm; assumption. }
unfold m, lexmax, vmax, eqb, blend. clear K m.
destruct (Rlt_bool_spec bh ah) as [H|H].
- (* ah > bh: the first pair *)
  rewrite Req_bool_true by reflexivity. rewrite Req_bool_false by lra. simpl.
  generalize (upper_normalized_lt bh bl ah al Nb Na H). intros V.
  split; [now left | split].
  + simpl. rewrite Rmax_left; lra.
  + exact Na.
- rewrite (Req_bool_true bh bh) by reflexivity.
  destruct (Req_dec bh ah) as [E|E].
  + (* equal heads: the pair of the greater second limb *)
    rewrite Req_bool_true by exact E. simpl. subst bh.
    destruct (Rlt_bool_spec bl al) as [L|L].
    * split; [now left | split].
      -- simpl. rewrite Rmax_left; lra.
      -- exact Na.
    * split; [now right | split].
      -- simpl. rewrite Rmax_right; lra.
      -- exact Nb.
  + (* ah < bh: the second pair *)
    rewrite Req_bool_false by exact E. simpl.
    assert (L : ah < bh) by (destruct H as [H|H]; [exact H | now elim E]).
    generalize (upper_normalized_lt ah al bh bl Na Nb L). intros V.
    split; [now right | split].
    * simpl. rewrite Rmax_right; lra.
    * exact Nb.
Qed.

(* The sign of the value is the sign of the head. *)
Theorem upper_normalized_sign :
  forall h l, upper_normalized emin prec h l ->
  (h <= 0 <-> h + l <= 0) /\ (h < 0 <-> h + l < 0) /\ (h = 0 -> l = 0).
Proof.
intros h l N.
generalize (upper_normalized_bounds h l N). intros [B1 B2].
assert (Z : h = 0 -> l = 0).
{ intros H0. apply format_small_zero; [apply N|].
  rewrite H0, pred_0, ulp_FLT_0 in B1 by exact prec_gt_0_.
  unfold eta. apply Rabs_lt. lra. }
assert (S : h + l <= 0 -> h <= 0).
{ intros H. destruct N as [_ [_ E]]. rewrite <- E. now apply ru_nonpos. }
split; [|split]; [split|split|exact Z].
- lra.
- exact S.
- lra.
- intros H. destruct (S (Rlt_le _ _ H)) as [H1|H1]; trivial.
  rewrite (Z H1), H1 in H. lra.
Qed.

(* The tests of mul_branch: le0 of a head is the sign of the value. *)
Lemma le0_upper_normalized :
  forall h l, upper_normalized emin prec h l ->
  (le0 h = true -> h + l <= 0) /\ (le0 h = false -> 0 < h + l).
Proof.
intros h l N. destruct (upper_normalized_sign h l N) as [[S1 S2] _].
unfold le0. destruct (Rle_bool_spec h 0) as [H|H]; split; intros E; try discriminate.
- now apply S1.
- destruct (Rlt_or_le 0 (h + l)) as [L|L]; trivial. generalize (S2 L). lra.
Qed.

End Round.

Print Assumptions upper_normalized_order.
Print Assumptions upper_normalized_unique.
Print Assumptions lexmax_correct.
Print Assumptions upper_normalized_sign.
