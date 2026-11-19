(* Consequences of the normalization invariant for two limbs.

   A 2-limb number (x0, x1) is normalized when x0 = RN (x0 + x1) (SpecDraft.normalized_2).
   The lemmas below are the items of the list "Consequences" of the Phase 0 report
   (Numbers), for k = 2:

     1. |x1| <= ulp(x0) / 2 and |x1| <= u |x0|; if |x0| < 2^(emin + prec), in particular
        if x0 is subnormal, then x1 = 0; and if x0 is a power of two and x1 has the
        opposite sign, |x1| <= ulp(x0) / 4.
     2. If x0 = 0 then x1 = 0.
     3. The value x0 + x1 has the sign of x0, and is zero exactly when x0 is.
     4. |(x0 + x1) - x0| <= u / (1 - u) |x0| (and, relative to the value, <= u |x0 + x1|).

   They hold for every tie rule except where ties to even is mentioned; they are stated
   for the rounding RN of the statements. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Relative.
From Kairn Require Import ModelDraft SpecDraft Format.
Open Scope R_scope.

Section Normalized.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation ulp := (ulp radix2 fexp).

Variables x0 x1 : R.
Hypothesis Hn : normalized_2 emin prec x0 x1.

Let F0 : format x0.
Proof. apply Hn. Qed.
Let F1 : format x1.
Proof. apply Hn. Qed.
Let Hx : x0 = round radix2 fexp (Znearest tie_even) (x0 + x1).
Proof. apply Hn. Qed.
Let Hx1 : x1 = - (round radix2 fexp (Znearest tie_even) (x0 + x1) - (x0 + x1)).
Proof. rewrite <- Hx. ring. Qed.

Let upos : 0 < u prec.
Proof. apply bpow_gt_0. Qed.
Let ule : u prec <= / 2.
Proof.
unfold u. change (/ 2) with (pow2 (-1)). apply bpow_le.
generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.
Let u2 : / 2 * pow2 (- prec + 1) = u prec.
Proof. unfold u. rewrite bpow_plus, pow2_1. field. Qed.

(* 1. The second limb is at most half a unit in the last place of the first. *)
Lemma normalized_2_tail_ulp : Rabs x1 <= / 2 * ulp x0.
Proof.
rewrite Hx1, Rabs_Ropp. rewrite Hx at 3.
apply error_le_half_ulp_round; auto with typeclass_instances.
Qed.

(* A sum of two numbers of the format that is below the normal range is exact, so a
   nonzero second limb forces the value into the normal range. *)
Lemma normalized_2_normal : x1 <> 0 -> pow2 (emin + prec - 1) <= Rabs (x0 + x1).
Proof.
intros Z1. destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs (x0 + x1))) as [H|H]; trivial.
exfalso. apply Z1.
assert (F : format (x0 + x1)).
{ apply FLT_format_plus_small; trivial.
  apply Rlt_le, Rlt_le_trans with (1 := H). apply bpow_le. lia. }
assert (E : x0 = x0 + x1).
{ rewrite Hx at 1. apply round_generic; auto with typeclass_instances. }
lra.
Qed.

(* 1 and 4. The second limb is at most u times the first, and u times the value. *)
Lemma normalized_2_tail_rel : Rabs x1 <= u prec * Rabs x0.
Proof.
destruct (Req_dec x1 0) as [Z1|Z1].
{ rewrite Z1, Rabs_R0. apply Rmult_le_pos. lra. apply Rabs_pos. }
rewrite Hx1, Rabs_Ropp, <- u2. rewrite Hx at 3.
apply relative_error_N_FLT_round; auto with typeclass_instances.
now apply normalized_2_normal.
Qed.

Lemma normalized_2_tail_rel_value : Rabs x1 <= u prec * Rabs (x0 + x1).
Proof.
destruct (Req_dec x1 0) as [Z1|Z1].
{ rewrite Z1, Rabs_R0. apply Rmult_le_pos. lra. apply Rabs_pos. }
rewrite Hx1 at 1. rewrite Rabs_Ropp, <- u2.
apply relative_error_N_FLT; auto with typeclass_instances.
now apply normalized_2_normal.
Qed.

Lemma normalized_2_value_rel : Rabs (x0 + x1 - x0) <= u prec / (1 - u prec) * Rabs x0.
Proof.
replace (x0 + x1 - x0) with x1 by ring.
apply Rle_trans with (1 := normalized_2_tail_rel).
apply Rmult_le_compat_r. apply Rabs_pos.
apply Rmult_le_reg_r with (1 - u prec). lra.
unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. nra.
Qed.

(* 2. Zeros are at the end. *)
Lemma normalized_2_zero : x0 = 0 -> x1 = 0.
Proof.
intros Z0. generalize normalized_2_tail_rel. rewrite Z0, Rabs_R0, Rmult_0_r. intros H.
destruct (Req_dec x1 0) as [Z1|Z1]; trivial.
generalize (Rabs_pos_lt x1 Z1). lra.
Qed.

(* 3. The value has the sign of the first limb. *)
Lemma normalized_2_pos : 0 < x0 -> 0 < x0 + x1.
Proof.
intros H. generalize normalized_2_tail_rel. rewrite (Rabs_pos_eq x0) by lra.
intros H1. apply Rabs_le_inv in H1. nra.
Qed.

Lemma normalized_2_neg : x0 < 0 -> x0 + x1 < 0.
Proof.
intros H. generalize normalized_2_tail_rel. rewrite (Rabs_left x0) by lra.
intros H1. apply Rabs_le_inv in H1. nra.
Qed.

Lemma normalized_2_value_zero : x0 + x1 = 0 <-> x0 = 0.
Proof.
split.
- intros H. destruct (Rtotal_order x0 0) as [Hneg|[Hz|Hpos]]; trivial.
  + generalize (normalized_2_neg Hneg). lra.
  + generalize (normalized_2_pos Hpos). lra.
- intros H. rewrite (normalized_2_zero H), H. ring.
Qed.

(* 1, continued. A number of the format below eta is zero. *)
Lemma format_lt_eta : forall x, format x -> Rabs x < pow2 emin -> x = 0.
Proof.
intros x Fx H.
destruct (FLT_format_generic radix2 emin prec x Fx) as [[m e] E Hm He]. simpl in Hm, He.
destruct (Z.eq_dec m 0) as [Zm|Zm].
- rewrite E, Zm. apply F2R_0.
- exfalso. apply (Rlt_irrefl (pow2 emin)). apply Rle_lt_trans with (2 := H).
  rewrite E, <- F2R_Zabs.
  apply Rle_trans with (pow2 e). now apply bpow_le.
  apply bpow_le_F2R. lia.
Qed.

(* If the first limb is below 2^(emin + prec) (subnormal, or in the first normal
   binade), the second limb is zero: the pair is a single number of the format. *)
Lemma normalized_2_small : Rabs x0 < pow2 (emin + prec) -> x1 = 0.
Proof.
intros H. apply format_lt_eta; trivial.
apply Rle_lt_trans with (1 := normalized_2_tail_ulp).
rewrite (ulp_FLT_small radix2 emin prec x0 H).
generalize (bpow_gt_0 radix2 emin). lra.
Qed.

(* When the first limb is a power of two and the second has the opposite sign, the
   second limb is at most a quarter of a unit in the last place of the first: below a
   power of two the numbers of the format are twice as dense. *)
Lemma normalized_2_tail_pow2_pos :
  forall k : Z, x0 = pow2 k -> x1 <= 0 -> Rabs x1 <= / 4 * ulp x0.
Proof.
intros k Hk Hneg.
destruct (Req_dec x1 0) as [Z1|Z1].
{ rewrite Z1, Rabs_R0. apply Rmult_le_pos. lra. apply ulp_ge_0. }
(* x1 <> 0, so x0 is at least 2^(emin + prec) *)
assert (Hbig : (emin + prec <= k)%Z).
{ destruct (Z_lt_le_dec k (emin + prec)) as [H|H]; trivial.
  exfalso. apply Z1. apply normalized_2_small.
  rewrite Hk, Rabs_pos_eq by apply bpow_ge_0. now apply bpow_lt. }
assert (Hp : (0 < prec)%Z) by exact prec_gt_0_.
assert (Hulp : ulp x0 = pow2 (k + 1 - prec)).
{ rewrite Hk, ulp_bpow. f_equal. unfold FLT_exp. lia. }
assert (Hpred : pred radix2 fexp x0 = x0 - pow2 (k - prec)).
{ rewrite Hk, pred_bpow. f_equal. f_equal. unfold FLT_exp. lia. }
assert (Hhalf : pow2 (k + 1 - prec) = 2 * pow2 (k - prec)).
{ replace (k + 1 - prec)%Z with (1 + (k - prec))%Z by ring. now rewrite bpow_plus, pow2_1. }
assert (H0 : 0 < pow2 (k - prec)) by apply bpow_gt_0.
(* if x0 + x1 were below the midpoint of pred x0 and x0, it would round to pred x0 *)
destruct (Rle_or_lt (- (/ 2 * pow2 (k - prec))) x1) as [H|H].
- rewrite Hulp, Hhalf, Rabs_left1 by exact Hneg. lra.
- exfalso.
  assert (Fp : format (pred radix2 fexp x0)).
  { apply generic_format_pred; auto with typeclass_instances. }
  assert (Hle : round radix2 fexp (Znearest tie_even) (x0 + x1) <= pred radix2 fexp x0).
  { apply round_N_le_midp; auto with typeclass_instances.
    rewrite succ_pred; auto with typeclass_instances.
    rewrite Hpred. lra. }
  rewrite <- Hx, Hpred in Hle. lra.
Qed.

End Normalized.

(* The same for a negative power of two, by symmetry. *)
Lemma normalized_2_opp :
  forall emin prec x0 x1, normalized_2 emin prec x0 x1 -> normalized_2 emin prec (- x0) (- x1).
Proof.
intros emin prec x0 x1 [F0 [F1 H]]. repeat split; try now apply generic_format_opp.
replace (- x0 + - x1) with (- (x0 + x1)) by ring.
rewrite RN_eq, round_NE_opp, <- RN_eq. now rewrite <- H.
Qed.

Lemma normalized_2_tail_pow2_neg :
  forall emin prec {prec_gt_0_ : Prec_gt_0 prec} x0 x1, normalized_2 emin prec x0 x1 ->
  forall k : Z, x0 = - pow2 k -> 0 <= x1 ->
  Rabs x1 <= / 4 * ulp radix2 (FLT_exp emin prec) x0.
Proof.
intros emin prec Hp x0 x1 Hn k Hk Hpos.
rewrite <- (Rabs_Ropp x1), <- (ulp_opp radix2 (FLT_exp emin prec) x0).
apply (normalized_2_tail_pow2_pos emin prec (- x0) (- x1) (normalized_2_opp _ _ _ _ Hn) k).
- rewrite Hk. ring.
- lra.
Qed.
