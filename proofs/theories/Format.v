(* The floating-point format of the model: facts used by every other proof file.

   Notation in the comments: F is the set of numbers of the format (precision prec,
   gradual underflow, smallest positive number eta = 2^emin, no largest number);
   u = 2^-prec; RN is rounding to nearest, ties to even. "FLT" is Flocq's name for this
   format and "FLX" its name for the format with the same precision and no underflow
   (exponents unbounded in both directions).

   Contents:
   - transfer between formats: the sum of two numbers of F rounds to the same value in
     F, in the format without underflow, and in any format with a smaller eta;
   - one rounding: bounds on its error and on its magnitude;
   - multiples of a power of two that are numbers of F, and conversely;
   - scaling by a power of two, which moves eta. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Mult_error Relative.
From Kairn Require Import ModelDraft SpecDraft.
Open Scope R_scope.

Notation pow2 e := (bpow radix2 e).

(* A precision of at least 1 is what Flocq calls a positive precision. *)
Lemma prec_gt_0_of_le : forall k prec : Z, (1 <= k)%Z -> (k <= prec)%Z -> Prec_gt_0 prec.
Proof. intros k prec H1 H2. unfold Prec_gt_0. lia. Qed.

(* The vocabulary of the statements, unfolded to Flocq's terms. *)
Lemma RN_eq : forall emin prec x,
  RN emin prec x = round radix2 (FLT_exp emin prec) ZnearestE x.
Proof. reflexivity. Qed.

Section Transfer.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).

(** * Transfer between formats *)

(* [T2] If a and b are numbers of F, then a + b rounds to the same number in F and in the
   format without underflow. Reason: a + b is a multiple of eta, so either it is below
   2^(emin+prec) and then it is itself a number of both formats, or it is in the range
   where the two formats coincide. Holds for every rounding direction and tie rule. *)
Theorem round_plus_FLT_FLX :
  forall (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  format a -> format b ->
  round radix2 fexp rz (a + b) = round radix2 (FLX_exp prec) rz (a + b).
Proof.
intros rz Hr a b Fa Fb.
destruct (Rle_or_lt (pow2 (emin + prec - 1)) (Rabs (a + b))) as [H|H].
- now apply round_FLT_FLX.
- assert (F : format (a + b)).
  { apply FLT_format_plus_small; trivial.
    apply Rlt_le, Rlt_le_trans with (1 := H). apply bpow_le. lia. }
  rewrite 2!round_generic; auto with typeclass_instances.
  now apply generic_format_FLX_FLT with emin.
Qed.

Theorem round_minus_FLT_FLX :
  forall (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  format a -> format b ->
  round radix2 fexp rz (a - b) = round radix2 (FLX_exp prec) rz (a - b).
Proof.
intros rz Hr a b Fa Fb. unfold Rminus.
apply round_plus_FLT_FLX; trivial. now apply generic_format_opp.
Qed.

(* A number of F is a number of every format with the same precision and a smaller eta. *)
Lemma format_emin_le :
  forall emin' x, (emin' <= emin)%Z -> format x ->
  generic_format radix2 (FLT_exp emin' prec) x.
Proof.
intros emin' x He Fx.
destruct (FLT_format_generic radix2 emin prec x Fx) as [f Hx Hm Hf].
rewrite Hx. apply generic_format_FLT. exists f; trivial. lia.
Qed.

End Transfer.

(* Hence the sum of two numbers of F also rounds to the same number in such a format. *)
Theorem round_plus_FLT_emin :
  forall emin emin' prec {prec_gt_0_ : Prec_gt_0 prec} (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  (emin' <= emin)%Z ->
  generic_format radix2 (FLT_exp emin prec) a -> generic_format radix2 (FLT_exp emin prec) b ->
  round radix2 (FLT_exp emin prec) rz (a + b) = round radix2 (FLT_exp emin' prec) rz (a + b).
Proof.
intros emin emin' prec Hp rz Hr a b He Fa Fb.
rewrite round_plus_FLT_FLX; trivial.
symmetry. apply round_plus_FLT_FLX; trivial; now apply format_emin_le with emin.
Qed.

Theorem round_minus_FLT_emin :
  forall emin emin' prec {prec_gt_0_ : Prec_gt_0 prec} (rz : R -> Z) {Hr : Valid_rnd rz} a b,
  (emin' <= emin)%Z ->
  generic_format radix2 (FLT_exp emin prec) a -> generic_format radix2 (FLT_exp emin prec) b ->
  round radix2 (FLT_exp emin prec) rz (a - b) = round radix2 (FLT_exp emin' prec) rz (a - b).
Proof.
intros emin emin' prec Hp rz Hr a b He Fa Fb. unfold Rminus.
apply round_plus_FLT_emin; trivial. now apply generic_format_opp.
Qed.

(** * Powers of two as real numbers *)

Lemma pow2_1 : pow2 1 = 2.
Proof. reflexivity. Qed.
Lemma pow2_2 : pow2 2 = 4.
Proof. reflexivity. Qed.
Lemma pow2_3 : pow2 3 = 8.
Proof. reflexivity. Qed.
Lemma pow2_m1 : pow2 (-1) = / 2.
Proof. reflexivity. Qed.

Lemma pow2_Zmax : forall a b : Z, pow2 (Z.max a b) = Rmax (pow2 a) (pow2 b).
Proof.
intros a b. destruct (Z.max_spec a b) as [[H ->]|[H ->]].
- symmetry. apply Rmax_right. apply bpow_le. lia.
- symmetry. apply Rmax_left. now apply bpow_le.
Qed.

(** * One rounding: error and magnitude *)

Section Rounding.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).

Section AnyTie.
Variable choice : Z -> bool.
Notation rnd := (round radix2 fexp (Znearest choice)).

(* If |x| <= 2^k then rounding x to nearest moves it by at most half a unit in the last
   place of the binade below 2^k: half of 2^(k - prec), or eta/2 if that is larger. *)
Lemma round_error_bpow :
  forall x k, Rabs x <= pow2 k ->
  Rabs (rnd x - x) <= / 2 * pow2 (Z.max (k - prec) emin).
Proof.
intros x k Hx.
assert (Hhalf : Rabs (rnd x - x) <= / 2 * ulp radix2 fexp x).
{ apply error_le_half_ulp; auto with typeclass_instances. }
destruct (Req_dec x 0) as [Zx|Zx].
{ rewrite Zx, round_0, Rminus_0_r, Rabs_R0; auto with typeclass_instances.
  apply Rmult_le_pos. lra. apply bpow_ge_0. }
destruct Hx as [Hx|Hx].
- (* |x| < 2^k *)
  apply Rle_trans with (1 := Hhalf).
  apply Rmult_le_compat_l. lra.
  rewrite ulp_neq_0 by exact Zx. apply bpow_le. unfold cexp, FLT_exp.
  assert (mag radix2 x <= k)%Z by now apply mag_le_bpow.
  lia.
- (* |x| = 2^k *)
  destruct (Z_lt_le_dec k emin) as [Hk|Hk].
  + apply Rle_trans with (1 := Hhalf).
    apply Rmult_le_compat_l. lra.
    assert (Hu : ulp radix2 fexp x = pow2 emin).
    { apply ulp_FLT_small; trivial.
      rewrite Hx. apply bpow_lt. generalize prec_gt_0_. unfold Prec_gt_0. lia. }
    rewrite Hu. apply bpow_le. lia.
  + rewrite round_generic; auto with typeclass_instances.
    * unfold Rminus. rewrite Rplus_opp_r, Rabs_R0.
      apply Rmult_le_pos. lra. apply bpow_ge_0.
    * apply generic_format_abs_inv. rewrite Hx. apply generic_format_bpow.
      unfold FLT_exp. generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.

(* The same, in the form used in error analyses: B bounds both halves. *)
Lemma round_error_le :
  forall x k B, Rabs x <= pow2 k ->
  pow2 (k - prec) <= 2 * B -> pow2 emin <= 2 * B ->
  Rabs (rnd x - x) <= B.
Proof.
intros x k B Hx H1 H2.
apply Rle_trans with (1 := round_error_bpow x k Hx).
rewrite pow2_Zmax. unfold Rmax. destruct (Rle_dec (pow2 (k - prec)) (pow2 emin)); lra.
Qed.

(* Rounding is monotone, so it does not cross a number of the format. *)
Lemma round_abs_le : forall x y, format y -> Rabs x <= y -> Rabs (rnd x) <= y.
Proof. intros x y Fy H. apply abs_round_le_generic; auto with typeclass_instances. Qed.

Lemma round_abs_ge : forall x y, format y -> y <= Rabs x -> y <= Rabs (rnd x).
Proof. intros x y Fy H. apply abs_round_ge_generic; auto with typeclass_instances. Qed.

End AnyTie.

(* With ties to even, anything of magnitude at most eta/2 rounds to zero (eta/2 itself
   is halfway between 0 and eta, and 0 is even). *)
Lemma RN_half_eta : RN emin prec (pow2 (emin - 1)) = 0.
Proof.
assert (E : FLT_exp emin prec emin = emin).
{ unfold FLT_exp. generalize prec_gt_0_. unfold Prec_gt_0. lia. }
assert (Zn : Znearest tie_even (/ 2) = 0%Z).
{ unfold Znearest.
  assert (F : Zfloor (/ 2) = 0%Z) by (apply Zfloor_imp; simpl; lra).
  rewrite F, Rcompare_Eq by (simpl; lra). reflexivity. }
unfold RN, round, F2R, scaled_mantissa, cexp. simpl.
rewrite mag_bpow. replace (emin - 1 + 1)%Z with emin by ring. rewrite E.
rewrite <- bpow_plus. replace (emin - 1 + - emin)%Z with (-1)%Z by ring.
rewrite pow2_m1, Zn. simpl. ring.
Qed.

Lemma RN_small_zero : forall x, Rabs x <= pow2 (emin - 1) -> RN emin prec x = 0.
Proof.
intros x Hx. apply Rabs_le_inv in Hx. apply Rle_antisym.
- rewrite <- RN_half_eta. apply round_le; auto with typeclass_instances. apply Hx.
- replace 0 with (- RN emin prec (pow2 (emin - 1))) by (rewrite RN_half_eta; ring).
  rewrite RN_eq, <- round_NE_opp, <- RN_eq. apply round_le; auto with typeclass_instances. apply Hx.
Qed.

(* Hence rounding to nearest even never crosses a power of two, representable or not. *)
Lemma RN_abs_le_bpow : forall x k, Rabs x <= pow2 k -> Rabs (RN emin prec x) <= pow2 k.
Proof.
intros x k Hx. destruct (Z_lt_le_dec k emin) as [Hk|Hk].
- rewrite RN_small_zero, Rabs_R0. apply bpow_ge_0.
  apply Rle_trans with (1 := Hx). apply bpow_le. lia.
- apply round_abs_le; trivial. apply generic_format_bpow.
  unfold FLT_exp. generalize prec_gt_0_. unfold Prec_gt_0. lia.
Qed.

(** * Multiples of a power of two *)

(* An integer multiple of 2^k, with k >= emin, of magnitude at most 2^(k + prec), is a
   number of the format. *)
Lemma format_multiple :
  forall (m : Z) (k : Z), (emin <= k)%Z ->
  Rabs (IZR m * pow2 k) <= pow2 (k + prec) -> format (IZR m * pow2 k).
Proof.
intros m k Hk H.
apply format_emin_le with k; trivial.
apply generic_format_FLT_FIX; trivial.
apply generic_format_FIX. now exists (Float radix2 m k).
Qed.

End Rounding.

(* A number with prec significant bits and magnitude at least 2^k is an integer multiple
   of 2^(k - prec + 1). *)
Lemma FLX_multiple :
  forall prec {prec_gt_0_ : Prec_gt_0 prec} y k,
  generic_format radix2 (FLX_exp prec) y -> pow2 k <= Rabs y ->
  exists m : Z, y = IZR m * pow2 (k - prec + 1).
Proof.
intros prec Hp y k Fy Hy.
apply (ex_shift radix2 (FLX_exp prec)); trivial.
unfold cexp, FLX_exp.
assert (k + 1 <= mag radix2 y)%Z.
{ apply mag_ge_bpow. now replace (k + 1 - 1)%Z with k by ring. }
lia.
Qed.

(** * Scaling by a power of two *)

(* Multiplying by 2^k maps the format with smallest number eta onto the format with
   smallest number 2^k eta, and commutes with rounding. This replaces, for a format with
   underflow, the scale invariance of the format without underflow. *)
Theorem round_FLT_scale :
  forall emin prec (rz : R -> Z) {Hr : Valid_rnd rz} x k,
  round radix2 (FLT_exp (emin + k) prec) rz (x * pow2 k)
  = round radix2 (FLT_exp emin prec) rz x * pow2 k.
Proof.
intros emin prec rz Hr x k.
destruct (Req_dec x 0) as [Zx|Zx].
{ rewrite Zx, Rmult_0_l, 2!round_0; trivial. ring. }
unfold round, F2R, scaled_mantissa, cexp. simpl.
rewrite mag_mult_bpow by exact Zx.
replace (FLT_exp (emin + k) prec (mag radix2 x + k))
  with (FLT_exp emin prec (mag radix2 x) + k)%Z by (unfold FLT_exp; lia).
rewrite Rmult_assoc, <- bpow_plus.
replace (k + - (FLT_exp emin prec (mag radix2 x) + k))%Z
  with (- FLT_exp emin prec (mag radix2 x))%Z by ring.
rewrite bpow_plus. ring.
Qed.
