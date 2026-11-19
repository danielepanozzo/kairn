(* mul_pow2_2: a 2-limb number times a power of two.

       h        = RN (x0 c)
       l        = RN (x1 c)
       (z0, z1) = fast_two_sum (h, l)

   for x = (x0, x1) normalized and c = 2^n.

   What is proved (mul_pow2_2_correct, the generated statement mul_pow2_2_spec of
   proofs/gen/Statements.v), for precision at least 2 and every eta: z is normalized and
       |z - c x| <= eta.

   Why:
   - Each product is rounded with an error of at most eta / 2 (lemma scale_error). A
     number of the format times 2^n still has prec significant bits, so it is a number of
     the format, and the rounding is exact, unless the product falls below
     2^(emin + prec), where the numbers of the format are eta apart.
   - |x1| <= |x0| for a normalized x, so |x1 c| <= |x0 c|, and |l| <= |h| because RN is
     monotone and symmetric. Hence the final Fast2Sum is error-free: z0 + z1 = h + l, and
     (z0, z1) is normalized.
   The error is therefore the sum of the two rounding errors, at most eta.

   The requirement that c is a number of the format (n >= emin) is in the statement, as
   for every operand, but the proof does not use it.

   Not stated, because the vocabulary of the claims has no such condition yet: z = c x
   exactly when each product is zero or at least 2^(emin + prec - 1) in magnitude. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Mult_error.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized EFT.
Open Scope R_scope.

Section Scale.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).

(* RN commutes with the absolute value: the format and the tie rule are symmetric. *)
Lemma RN_abs : forall t, RN emin prec (Rabs t) = Rabs (RN emin prec t).
Proof.
intros t. destruct (Rle_or_lt 0 t) as [H|H].
- rewrite (Rabs_pos_eq t H). symmetry. apply Rabs_pos_eq. unfold RN.
  exact (round_ge_generic radix2 fexp (Znearest tie_even) 0 t (generic_format_0 radix2 fexp) H).
- rewrite (Rabs_left t H), RN_opp. symmetry. apply Rabs_left1. unfold RN.
  apply (round_le_generic radix2 fexp (Znearest tie_even) t 0 (generic_format_0 radix2 fexp)).
  lra.
Qed.

(* Hence RN preserves the order of magnitudes. *)
Lemma RN_abs_le :
  forall s t, Rabs s <= Rabs t -> Rabs (RN emin prec s) <= Rabs (RN emin prec t).
Proof.
intros s t H. rewrite <- 2!RN_abs.
unfold RN. apply round_le; auto with typeclass_instances.
Qed.

(* A number of the format times a power of two is rounded with an error of at most
   eta / 2: it is a number of the format unless it is below 2^(emin + prec). *)
Lemma scale_error :
  forall x n, format x ->
  Rabs (RN emin prec (x * pow2 n) - x * pow2 n) <= / 2 * pow2 emin.
Proof.
intros x n Fx. unfold RN.
destruct (Z_le_gt_dec (emin + prec - mag radix2 x) n) as [H|H].
- (* the product has prec significant bits and is a multiple of eta *)
  assert (Fp : format (x * pow2 n)) by exact (mult_bpow_exact_FLT radix2 emin prec x n Fx H).
  rewrite (round_generic radix2 fexp (Znearest tie_even) (x * pow2 n) Fp).
  unfold Rminus. rewrite Rplus_opp_r, Rabs_R0.
  apply Rmult_le_pos. lra. apply bpow_ge_0.
- (* the product is below 2^(emin + prec), where the spacing is eta *)
  assert (Hs : Rabs (x * pow2 n) < pow2 (emin + prec)).
  { rewrite Rabs_mult, (Rabs_pos_eq (pow2 n)) by apply bpow_ge_0.
    apply Rlt_le_trans with (pow2 (mag radix2 x) * pow2 n).
    - apply Rmult_lt_compat_r. apply bpow_gt_0. apply bpow_mag_gt.
    - rewrite <- bpow_plus. apply bpow_le. lia. }
  rewrite <- (ulp_FLT_small radix2 emin prec (x * pow2 n) Hs).
  apply error_le_half_ulp; auto with typeclass_instances.
Qed.

End Scale.

(* The kernel, with c = 2^n and the two products named. *)
Lemma mul_pow2_2_facts :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall (x0 x1 : R) (n : Z), normalized_2 emin prec x0 x1 ->
  let h := RN emin prec (x0 * pow2 n) in
  let l := RN emin prec (x1 * pow2 n) in
  normalized_2 emin prec (fst (fast_two_sum emin prec tie_even h l))
                         (snd (fast_two_sum emin prec tie_even h l)) /\
  Rabs (fst (fast_two_sum emin prec tie_even h l) + snd (fast_two_sum emin prec tie_even h l)
        - (x0 + x1) * pow2 n) <= pow2 emin.
Proof.
intros emin prec Hp x0 x1 n Hn h l.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (F0 : generic_format radix2 (FLT_exp emin prec) x0) by apply Hn.
assert (F1 : generic_format radix2 (FLT_exp emin prec) x1) by apply Hn.
assert (Fh : fmt emin prec h).
{ unfold fmt, h, RN. apply generic_format_round; auto with typeclass_instances. }
assert (Fl : fmt emin prec l).
{ unfold fmt, l, RN. apply generic_format_round; auto with typeclass_instances. }
(* |x1| <= |x0|, hence |l| <= |h| *)
assert (H10 : Rabs x1 <= Rabs x0).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec x0 x1 Hn).
  assert (Hu : u prec <= 1).
  { unfold u. apply Rle_trans with (pow2 0). apply bpow_le. lia. simpl. lra. }
  generalize (Rabs_pos x0). nra. }
assert (Hlh : Rabs l <= Rabs h).
{ unfold l, h. apply (RN_abs_le emin prec).
  rewrite (Rabs_mult x1), (Rabs_mult x0).
  apply Rmult_le_compat_r. apply Rabs_pos. exact H10. }
(* the two rounding errors *)
assert (E0 : Rabs (h - x0 * pow2 n) <= / 2 * pow2 emin)
  by exact (scale_error emin prec x0 n F0).
assert (E1 : Rabs (l - x1 * pow2 n) <= / 2 * pow2 emin)
  by exact (scale_error emin prec x1 n F1).
destruct (fast_two_sum_norm emin prec Hp h l Fh Fl Hlh) as [Nz Hs].
split. exact Nz.
rewrite Hs.
replace (h + l - (x0 + x1) * pow2 n) with ((h - x0 * pow2 n) + (l - x1 * pow2 n)) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
lra.
Qed.

(** * The generated statement *)

Theorem mul_pow2_2_correct : mul_pow2_2_spec.
Proof.
intros emin prec Hp x0 x1 c Hn Fc [n Hc]. subst c.
generalize (mul_pow2_2_facts emin prec Hp x0 x1 n Hn). cbv zeta.
unfold mul_pow2_2. cbv zeta. rewrite !Rplus_0_r. unfold RN.
match goal with |- context [fast_two_sum emin prec tie_even ?h ?l] =>
  destruct (fast_two_sum emin prec tie_even h l) as [z0 z1] end.
cbn [fst snd].
intros [H1 H2]. split. exact H1.
unfold eta. lra.
Qed.
