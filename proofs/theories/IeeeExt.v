(* The kernels that need no fix-up, in the IEEE model, on canonical operands that may be
   infinite or NaN: neg_2, abs_2, the eight comparisons, to_nearest_2, to_down_2,
   to_up_2 and abs_upper_2; and radd and rmul on operands that are nonnegative,
   +infinity or NaN (at the end of the file). The statements are in
   proofs/gen/IeeeStatements.v.

   Each result is given as an extended real number. The proofs go through three facts:

     - a comparison of two limbs is the comparison of the extended real numbers they
       stand for (lt_xval, le_xval, eq_xval), whatever the limbs;
     - a canonical 2-limb value is one of three things (canonical_cases): two finite
       normalized limbs; an infinity followed by a zero, which the limbs see as
       (+-infinity, 0); or two NaN;
     - on finite operands the kernel of the IEEE model computes what the kernel of the
       real model computes, and the theorems of Sign.v, Compare.v and Convert.v apply.

   The other cases are computations on the signs. The only overflow is in to_down_2
   and to_up_2: the neighbor of the largest number is an infinity, and so is the
   rounding of the value in the sense of T. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Sign Compare Convert Directed IeeeBridge IeeeVocabulary IeeeOps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Section IeeeExt.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_opp : float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation flt := (IeeeOperations.lt prec emax).
Notation fle := (IeeeOperations.le prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).

(** * The extended real number of a limb *)

Lemma xval_fin : forall a : float, fin a -> xv a = XFin (b2r a).
Proof. intros a F. unfold xval. now rewrite F. Qed.

Lemma xval_nan : forall a : float, is_nan prec emax a = true -> xv a = XNaN.
Proof. intros a N. unfold xval. now rewrite (nan_not_finite prec emax a N), N. Qed.

Lemma xval_inf : forall s : bool, xv (B754_infinity prec emax s) = XInf s.
Proof. intros s. reflexivity. Qed.

Lemma xval_pzero : xv pzero = XFin 0.
Proof. reflexivity. Qed.

Lemma xval_cases :
  forall a : float,
  (fin a /\ xv a = XFin (b2r a)) \/ (exists s : bool, xv a = XInf s) \/ xv a = XNaN.
Proof.
intros a. destruct (finite_dec prec emax a) as [F|F].
- left. split; [exact F|now apply xval_fin].
- destruct (not_finite_cases prec emax a F) as [N|[s E]].
  + right. right. now apply xval_nan.
  + right. left. exists s. subst a. apply xval_inf.
Qed.

(* A comparison of two limbs is the comparison of what they stand for. *)
Lemma lt_xval : forall a b : float, flt a b = xlt (xv a) (xv b).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- rewrite (xval_fin a Fa), (xval_fin b Fb). exact (lt_finite prec emax a b Fa Fb).
- destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
- destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb;
  destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
Qed.

Lemma le_xval : forall a b : float, fle a b = xle (xv a) (xv b).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- rewrite (xval_fin a Fa), (xval_fin b Fb). exact (le_finite prec emax a b Fa Fb).
- destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
- destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb;
  destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
Qed.

Lemma eq_xval : forall a b : float, feq a b = xeq (xv a) (xv b).
Proof.
intros a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- rewrite (xval_fin a Fa), (xval_fin b Fb). exact (eq_finite prec emax a b Fa Fb).
- destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
- destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb;
  destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- destruct a as [sa|[|]|sa pa Ha|sa ma ea Ha]; try discriminate Fa;
  destruct b as [sb|[|]|sb pb Hb|sb mb eb Hb]; try discriminate Fb; reflexivity.
Qed.

(** * The three kinds of canonical 2-limb values *)

Lemma canonical_cases :
  forall x0 x1 : float, canonical_2 x0 x1 ->
  (fin x0 /\ fin x1 /\ normalized_2 emin prec (b2r x0) (b2r x1) /\
   xv x0 = XFin (b2r x0) /\ xv x1 = XFin (b2r x1) /\ xv2 x0 x1 = XFin (b2r x0 + b2r x1)) \/
  (exists s s' : bool,
   x0 = B754_infinity prec emax s /\ x1 = B754_zero prec emax s' /\
   xv x0 = XInf s /\ xv x1 = XFin 0 /\ xv2 x0 x1 = XInf s) \/
  (is_nan prec emax x0 = true /\ is_nan prec emax x1 = true /\
   xv x0 = XNaN /\ xv x1 = XNaN /\ xv2 x0 x1 = XNaN).
Proof.
intros x0 x1 [[F0 [F1 N]]|[[[s E] [s' E']]|[N0 N1]]].
- left. unfold finite, val in *. unfold xval_2, xval. rewrite F0, F1. auto 6.
- right. left. exists s, s'. subst x0 x1. repeat split; reflexivity.
- right. right. unfold nan in *. unfold xval_2.
  rewrite (xval_nan x0 N0), (xval_nan x1 N1), (nan_not_finite prec emax x0 N0), N0. auto.
Qed.

Lemma Rlt_bool_0_0 : Rlt_bool 0 0 = false.
Proof. apply Rlt_bool_false. lra. Qed.

Lemma Rle_bool_0_0 : Rle_bool 0 0 = true.
Proof. apply Rle_bool_true. lra. Qed.

Lemma Req_bool_0_0 : Req_bool 0 0 = true.
Proof. now apply Req_bool_true. Qed.

(* The cases with an operand that is not finite: computations on the signs. *)
Ltac signs :=
  cbn [xlt xle xeq];
  rewrite ?Rlt_bool_0_0, ?Rle_bool_0_0, ?Req_bool_0_0;
  repeat match goal with s : bool |- _ => destruct s end;
  reflexivity.

(** * The comparisons *)

Ltac compare_22 Cx Cy real :=
  let F0 := fresh in let F1 := fresh in let Nx := fresh in
  let G0 := fresh in let G1 := fresh in let Ny := fresh in
  let E0 := fresh in let E1 := fresh in let E := fresh in
  let D0 := fresh in let D1 := fresh in let D := fresh in
  let s := fresh "s" in let s' := fresh "s" in let t := fresh "s" in let t' := fresh "s" in
  destruct (canonical_cases _ _ Cx)
    as [[F0 [F1 [Nx [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  destruct (canonical_cases _ _ Cy)
    as [[G0 [G1 [Ny [D0 [D1 D]]]]]|[[t [t' [_ [_ [D0 [D1 D]]]]]]|[_ [_ [D0 [D1 D]]]]]];
  rewrite E0, E1, E, D0, D1, D;
  [exact (real Nx Ny)|signs..].

Lemma lt_2_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  IeeeModel.lt_2_2 prec emax x0 x1 y0 y1 = xlt (xv2 x0 x1) (xv2 y0 y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. unfold IeeeModel.lt_2_2. cbv zeta.
rewrite 2!lt_xval, eq_xval.
compare_22 Cx Cy (lt_2_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1)).
Qed.

Lemma le_2_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  IeeeModel.le_2_2 prec emax x0 x1 y0 y1 = xle (xv2 x0 x1) (xv2 y0 y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. unfold IeeeModel.le_2_2. cbv zeta.
rewrite lt_xval, eq_xval, le_xval.
compare_22 Cx Cy (le_2_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1)).
Qed.

Lemma eq_2_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  IeeeModel.eq_2_2 prec emax x0 x1 y0 y1 = xeq (xv2 x0 x1) (xv2 y0 y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. unfold IeeeModel.eq_2_2. cbv zeta.
rewrite 2!eq_xval.
compare_22 Cx Cy (eq_2_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1)).
Qed.

(* A 2-limb value and a limb. *)
Ltac compare_21 Cx a real :=
  let F0 := fresh in let F1 := fresh in let Nx := fresh in
  let E0 := fresh in let E1 := fresh in let E := fresh in
  let Fa := fresh in let Ea := fresh in
  let s := fresh "s" in let s' := fresh "s" in let t := fresh "s" in
  destruct (canonical_cases _ _ Cx)
    as [[F0 [F1 [Nx [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  destruct (xval_cases a) as [[Fa Ea]|[[t Ea]|Ea]];
  rewrite E0, E1, E, Ea;
  [exact (real Nx (b2r_format prec emax a))|signs..].

Lemma lt_2_1_ext :
  (1 <= prec)%Z ->
  forall x0 x1 a : float, canonical_2 x0 x1 ->
  IeeeModel.lt_2_1 prec emax x0 x1 a = xlt (xv2 x0 x1) (xv a).
Proof.
intros Hp x0 x1 a Cx. unfold IeeeModel.lt_2_1. cbv zeta.
rewrite 2!lt_xval, eq_xval, xval_pzero.
compare_21 Cx a (lt_2_1_correct emin prec Hp (b2r x0) (b2r x1) (b2r a)).
Qed.

Lemma le_2_1_ext :
  (1 <= prec)%Z ->
  forall x0 x1 a : float, canonical_2 x0 x1 ->
  IeeeModel.le_2_1 prec emax x0 x1 a = xle (xv2 x0 x1) (xv a).
Proof.
intros Hp x0 x1 a Cx. unfold IeeeModel.le_2_1. cbv zeta.
rewrite lt_xval, eq_xval, le_xval, xval_pzero.
compare_21 Cx a (le_2_1_correct emin prec Hp (b2r x0) (b2r x1) (b2r a)).
Qed.

Lemma eq_2_1_ext :
  (1 <= prec)%Z ->
  forall x0 x1 a : float, canonical_2 x0 x1 ->
  IeeeModel.eq_2_1 prec emax x0 x1 a = xeq (xv2 x0 x1) (xv a).
Proof.
intros Hp x0 x1 a Cx. unfold IeeeModel.eq_2_1. cbv zeta.
rewrite 2!eq_xval, xval_pzero.
compare_21 Cx a (eq_2_1_correct emin prec Hp (b2r x0) (b2r x1) (b2r a)).
Qed.

(* A limb and a 2-limb value. *)
Ltac compare_12 a Cy real :=
  let G0 := fresh in let G1 := fresh in let Ny := fresh in
  let D0 := fresh in let D1 := fresh in let D := fresh in
  let Fa := fresh in let Ea := fresh in
  let s := fresh "s" in let s' := fresh "s" in let t := fresh "s" in
  destruct (xval_cases a) as [[Fa Ea]|[[t Ea]|Ea]];
  destruct (canonical_cases _ _ Cy)
    as [[G0 [G1 [Ny [D0 [D1 D]]]]]|[[s [s' [_ [_ [D0 [D1 D]]]]]]|[_ [_ [D0 [D1 D]]]]]];
  rewrite Ea, D0, D1, D;
  [exact (real (b2r_format prec emax a) Ny)|signs..].

Lemma lt_1_2_ext :
  (1 <= prec)%Z ->
  forall a y0 y1 : float, canonical_2 y0 y1 ->
  IeeeModel.lt_1_2 prec emax a y0 y1 = xlt (xv a) (xv2 y0 y1).
Proof.
intros Hp a y0 y1 Cy. unfold IeeeModel.lt_1_2. cbv zeta.
rewrite 2!lt_xval, eq_xval, xval_pzero.
compare_12 a Cy (lt_1_2_correct emin prec Hp (b2r a) (b2r y0) (b2r y1)).
Qed.

Lemma le_1_2_ext :
  (1 <= prec)%Z ->
  forall a y0 y1 : float, canonical_2 y0 y1 ->
  IeeeModel.le_1_2 prec emax a y0 y1 = xle (xv a) (xv2 y0 y1).
Proof.
intros Hp a y0 y1 Cy. unfold IeeeModel.le_1_2. cbv zeta.
rewrite lt_xval, eq_xval, le_xval, xval_pzero.
compare_12 a Cy (le_1_2_correct emin prec Hp (b2r a) (b2r y0) (b2r y1)).
Qed.

(** * neg_2 and abs_2 *)

Lemma neg_finite : forall y : float, is_finite prec emax (neg y) = is_finite prec emax y.
Proof. intros y. apply is_finite_Bopp. Qed.

Lemma neg_value : forall y : float, b2r (neg y) = - b2r y.
Proof. intros y. apply B2R_Bopp. Qed.

Lemma neg_nan : forall y : float, is_nan prec emax (neg y) = is_nan prec emax y.
Proof. intros [s|s|s pl H|s m e H]; reflexivity. Qed.

Lemma neg_2_ext :
  forall x0 x1 : float, canonical_2 x0 x1 ->
  let '(z0, z1) := IeeeModel.neg_2 prec emax nan_opp x0 x1 in
  canonical_2 z0 z1 /\ xv2 z0 z1 = xopp (xv2 x0 x1).
Proof.
intros x0 x1 C. unfold IeeeModel.neg_2. cbv beta iota zeta.
destruct C as [[F0 [F1 N]]|[[[s E] [s' E']]|[N0 N1]]].
- unfold finite, val in *. split.
  + left. unfold finite, val. rewrite 2!neg_finite, 2!neg_value.
    split; [exact F0|split; [exact F1|now apply normalized_2_opp]].
  + unfold xval_2, val. rewrite neg_finite, F0, 2!neg_value. cbn [xopp]. f_equal. ring.
- subst x0 x1. split.
  + right. left. split; [now exists (negb s)|now exists (negb s')].
  + reflexivity.
- unfold nan in *. split.
  + right. right. unfold nan. rewrite 2!neg_nan. now split.
  + unfold xval_2. rewrite neg_finite, (nan_not_finite prec emax x0 N0), neg_nan, N0. reflexivity.
Qed.

Lemma abs_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 : float, canonical_2 x0 x1 ->
  let '(z0, z1) := IeeeModel.abs_2 prec emax nan_opp x0 x1 in
  canonical_2 z0 z1 /\ xv2 z0 z1 = xabs (xv2 x0 x1).
Proof.
intros Hp x0 x1 C. unfold IeeeModel.abs_2. cbv beta iota zeta.
destruct C as [[F0 [F1 N]]|[[[s E] [s' E']]|[N0 N1]]].
- unfold finite, val in *.
  assert (Fz : fin pzero) by reflexivity.
  rewrite (lt_finite prec emax x0 pzero F0 Fz). change (b2r pzero) with 0.
  generalize (abs_2_correct emin prec Hp (b2r x0) (b2r x1) N). unfold Model.abs_2. cbv zeta.
  destruct (Rlt_bool (b2r x0) 0); intros [Nz Ez].
  + split.
    * left. unfold finite, val. rewrite 2!neg_finite, 2!neg_value. auto.
    * unfold xval_2, val. rewrite neg_finite, F0, 2!neg_value. cbn [xabs]. now f_equal.
  + split.
    * left. unfold finite, val. auto.
    * unfold xval_2, val. rewrite F0. cbn [xabs]. now f_equal.
- subst x0 x1. destruct s.
  + split; [right; left; split; [now exists false|now exists (negb s')]|reflexivity].
  + split; [right; left; split; [now exists false|now exists s']|reflexivity].
- assert (M : flt x0 pzero = false).
  { rewrite lt_xval, (xval_nan x0 N0). reflexivity. }
  rewrite M. split.
  + right. right. now split.
  + unfold nan in N0. unfold xval_2. rewrite (nan_not_finite prec emax x0 N0), N0. reflexivity.
Qed.

(** * The conversions to one limb *)

(* A real number below 2^emax in magnitude is returned as it is. *)
Lemma overflow_of_inrange :
  forall r : R, Rabs r < bpow radix2 emax -> overflow_of emax r = XFin r.
Proof. intros r H. unfold overflow_of. now rewrite Rlt_bool_true. Qed.

Lemma to_nearest_2_ext :
  forall x0 x1 : float, canonical_2 x0 x1 ->
  xv (IeeeModel.to_nearest_2 prec emax x0 x1) = xround emax (RN emin prec) (xv2 x0 x1).
Proof.
intros x0 x1 C. unfold IeeeModel.to_nearest_2. cbv zeta.
destruct (canonical_cases x0 x1 C)
  as [[F0 [F1 [[_ [_ N]] [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  rewrite E0, E; try reflexivity.
cbn [xround]. rewrite <- N. symmetry. apply overflow_of_inrange. apply (b2r_inrange prec emax).
Qed.

Lemma to_up_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 : float, canonical_2 x0 x1 ->
  xv (IeeeModel.to_up_2 prec emax x0 x1) = xround emax (RU emin prec) (xv2 x0 x1).
Proof.
intros Hp x0 x1 C. unfold IeeeModel.to_up_2. cbv zeta. rewrite lt_xval, xval_pzero.
destruct (canonical_cases x0 x1 C)
  as [[F0 [F1 [N [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  rewrite E1, E.
- cbn [xlt xround].
  destruct (to_up_2_correct emin prec Hp (b2r x0) (b2r x1) N) as [_ R]. revert R.
  unfold Model.to_up_2. cbv zeta. destruct (Rlt_bool 0 (b2r x1)); intros R; rewrite <- R.
  + destruct (succ_finite prec emax x0 F0) as [[Fs [Es Ls]]|[Es Ls]].
    * rewrite (xval_fin _ Fs), Es. symmetry. apply overflow_of_inrange.
      apply Rabs_lt. split; [|exact Ls].
      apply Rlt_le_trans with (b2r x0); [|apply succ_ge_id].
      generalize (b2r_inrange prec emax x0). unfold inrange. intros K.
      apply Rabs_lt_inv in K. apply K.
    * rewrite Es. unfold overflow_of.
      generalize (bpow_gt_0 radix2 emax). intros P.
      rewrite Rlt_bool_false by (rewrite Rabs_pos_eq; lra).
      rewrite Rlt_bool_false by lra. reflexivity.
  + rewrite E0. symmetry. apply overflow_of_inrange. apply (b2r_inrange prec emax).
- cbn [xlt xround]. rewrite Rlt_bool_0_0. exact E0.
- cbn [xlt xround]. exact E0.
Qed.

Lemma to_down_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 : float, canonical_2 x0 x1 ->
  xv (IeeeModel.to_down_2 prec emax x0 x1) = xround emax (RD emin prec) (xv2 x0 x1).
Proof.
intros Hp x0 x1 C. unfold IeeeModel.to_down_2. cbv zeta. rewrite lt_xval, xval_pzero.
destruct (canonical_cases x0 x1 C)
  as [[F0 [F1 [N [E0 [E1 E]]]]]|[[s [s' [_ [_ [E0 [E1 E]]]]]]|[_ [_ [E0 [E1 E]]]]]];
  rewrite E1, E.
- cbn [xlt xround].
  destruct (to_down_2_correct emin prec Hp (b2r x0) (b2r x1) N) as [_ R]. revert R.
  unfold Model.to_down_2. cbv zeta. destruct (Rlt_bool (b2r x1) 0); intros R; rewrite <- R.
  + destruct (pred_finite prec emax x0 F0) as [[Fs [Es Ls]]|[Es Ls]].
    * rewrite (xval_fin _ Fs), Es. symmetry. apply overflow_of_inrange.
      apply Rabs_lt. split; [exact Ls|].
      apply Rle_lt_trans with (b2r x0); [apply pred_le_id|].
      generalize (b2r_inrange prec emax x0). unfold inrange. intros K.
      apply Rabs_lt_inv in K. apply K.
    * rewrite Es. unfold overflow_of.
      generalize (bpow_gt_0 radix2 emax). intros P.
      rewrite Rlt_bool_false by (rewrite Rabs_left1; lra).
      rewrite Rlt_bool_true by lra. reflexivity.
  + rewrite E0. symmetry. apply overflow_of_inrange. apply (b2r_inrange prec emax).
- cbn [xlt xround]. rewrite Rlt_bool_0_0. exact E0.
- cbn [xlt xround]. exact E0.
Qed.

(** * abs_upper_2, radd and rmul *)

(* abs_upper_2 is abs_2 followed by to_up_2. *)
Lemma abs_upper_2_ext :
  (1 <= prec)%Z ->
  forall x0 x1 : float, canonical_2 x0 x1 ->
  xv (IeeeModel.abs_upper_2 prec emax nan_opp x0 x1)
  = xround emax (RU emin prec) (xabs (xv2 x0 x1)).
Proof.
intros Hp x0 x1 C. unfold IeeeModel.abs_upper_2.
generalize (abs_2_ext Hp x0 x1 C).
destruct (IeeeModel.abs_2 prec emax nan_opp x0 x1) as [a0 a1]. intros [Ca Ea]. cbv zeta.
rewrite <- Ea. exact (to_up_2_ext Hp a0 a1 Ca).
Qed.

(* radd and rmul on operands that are nonnegative, +infinity or NaN: the result is of
   that kind too, and a finite result means finite operands and the statement of the
   real model. *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Lemma radd_ext :
  (2 <= prec)%Z ->
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  let r := IeeeModel.radd prec emax nan_plus a b in
  nonneg_ext r /\
  (fin r -> fin a /\ fin b /\ b2r a + b2r b <= b2r r /\
   b2r r - (b2r a + b2r b) <= 3 / 2 * (b2r r - Ulp.pred radix2 fexp (b2r r))).
Proof.
intros Hp a b Ha Hb. cbv zeta.
destruct (radd_nonneg prec emax nan_plus a b Ha Hb) as [Hr Fr].
split; [exact Hr|]. intros F. destruct (Fr F) as [Fa [Fb E]].
split; [exact Fa|split; [exact Fb|]]. rewrite E.
exact (proj2 (radd_correct emin prec Hp (b2r a) (b2r b)
                (b2r_format prec emax a) (b2r_format prec emax b)
                (nonneg_ext_fin prec emax a Ha Fa) (nonneg_ext_fin prec emax b Hb Fb))).
Qed.

Lemma rmul_ext :
  (2 <= prec)%Z ->
  forall a b : float, nonneg_ext a -> nonneg_ext b ->
  let r := IeeeModel.rmul prec emax nan_fma a b in
  nonneg_ext r /\
  (fin r -> fin a /\ fin b /\ b2r a * b2r b <= b2r r /\
   b2r r - (b2r a * b2r b) <= 3 / 2 * (b2r r - Ulp.pred radix2 fexp (b2r r))).
Proof.
intros Hp a b Ha Hb. cbv zeta.
destruct (rmul_nonneg prec emax nan_fma a b Ha Hb) as [Hr Fr].
split; [exact Hr|]. intros F. destruct (Fr F) as [Fa [Fb E]].
split; [exact Fa|split; [exact Fb|]]. rewrite E.
exact (proj2 (rmul_correct emin prec Hp (b2r a) (b2r b)
                (b2r_format prec emax a) (b2r_format prec emax b)
                (nonneg_ext_fin prec emax a Ha Fa) (nonneg_ext_fin prec emax b Hb Fb))).
Qed.

End IeeeExt.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem neg_2_ieee_correct : neg_2_ieee_spec.
Proof. intros prec emax Hp He nan_opp _ x0 x1 C. exact (neg_2_ext prec emax nan_opp x0 x1 C). Qed.

Theorem abs_2_ieee_correct : abs_2_ieee_spec.
Proof.
intros prec emax Hp He nan_opp Hp1 x0 x1 C. exact (abs_2_ext prec emax nan_opp Hp1 x0 x1 C).
Qed.

Theorem lt_2_2_ieee_correct : lt_2_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 y0 y1 Cx Cy. exact (lt_2_2_ext prec emax Hp1 x0 x1 y0 y1 Cx Cy). Qed.

Theorem le_2_2_ieee_correct : le_2_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 y0 y1 Cx Cy. exact (le_2_2_ext prec emax Hp1 x0 x1 y0 y1 Cx Cy). Qed.

Theorem eq_2_2_ieee_correct : eq_2_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 y0 y1 Cx Cy. exact (eq_2_2_ext prec emax Hp1 x0 x1 y0 y1 Cx Cy). Qed.

Theorem lt_2_1_ieee_correct : lt_2_1_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 a Cx. exact (lt_2_1_ext prec emax Hp1 x0 x1 a Cx). Qed.

Theorem le_2_1_ieee_correct : le_2_1_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 a Cx. exact (le_2_1_ext prec emax Hp1 x0 x1 a Cx). Qed.

Theorem eq_2_1_ieee_correct : eq_2_1_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 a Cx. exact (eq_2_1_ext prec emax Hp1 x0 x1 a Cx). Qed.

Theorem lt_1_2_ieee_correct : lt_1_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 a y0 y1 Cy. exact (lt_1_2_ext prec emax Hp1 a y0 y1 Cy). Qed.

Theorem le_1_2_ieee_correct : le_1_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 a y0 y1 Cy. exact (le_1_2_ext prec emax Hp1 a y0 y1 Cy). Qed.

Theorem to_nearest_2_ieee_correct : to_nearest_2_ieee_spec.
Proof. intros prec emax Hp He _ x0 x1 C. exact (to_nearest_2_ext prec emax x0 x1 C). Qed.

Theorem to_down_2_ieee_correct : to_down_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 C. exact (to_down_2_ext prec emax Hp1 x0 x1 C). Qed.

Theorem to_up_2_ieee_correct : to_up_2_ieee_spec.
Proof. intros prec emax Hp He Hp1 x0 x1 C. exact (to_up_2_ext prec emax Hp1 x0 x1 C). Qed.

Theorem abs_upper_2_ieee_correct : abs_upper_2_ieee_spec.
Proof.
intros prec emax Hp He nan_opp Hp1 x0 x1 C. exact (abs_upper_2_ext prec emax nan_opp Hp1 x0 x1 C).
Qed.

Theorem radd_ieee_correct : radd_ieee_spec.
Proof.
intros prec emax Hp He nan_plus Hp2 a b Ha Hb. exact (radd_ext prec emax nan_plus Hp2 a b Ha Hb).
Qed.

Theorem rmul_ieee_correct : rmul_ieee_spec.
Proof.
intros prec emax Hp He nan_fma Hp2 a b Ha Hb. exact (rmul_ext prec emax nan_fma Hp2 a b Ha Hb).
Qed.
