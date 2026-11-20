(* Rounding a sum down and up without a rounding mode, in the IEEE model, on all values:
   finite numbers, infinities and NaN. The rows of the table of
   docs/developer/design/milestone2.md, "Rounding a sum down and up", for two_sum_ord,
   add_down_1, add_up_1, and the differences sub_down_1 and sub_up_1.

   Notation: T is the IEEE format of IeeeOperations.v (precision prec, largest number
   Omega = 2^emax - 2^(emax - prec), smallest positive number 2^emin with
   emin = 3 - emax - prec); RN, RD, RU are the roundings to nearest (ties to even), down
   and up in the format with no largest number (the real model); val is the real value of
   a finite limb and xval the extended real number a limb stands for.

   The directed roundings in the format with overflow (xround_down, xround_up) are those
   of the design page: RD(t) is -infinity when t < -Omega, Omega when t > Omega, and the
   RD of the real model otherwise; symmetrically for RU. (xround of IeeeVocabulary.v gives
   +infinity to an RD at or above 2^emax, which is right for the conversions of a 2-limb
   value, whose RD never is, and not for a sum of two numbers.) The sum of IEEE 754 on
   extended real numbers is xadd: +infinity plus -infinity is a NaN.

   What is proved, from precision 2:
   - two_sum_ord on finite operands (two_sum_ord_ieee_finite): if s is finite then e is
     finite and (s, e) is what the real model computes, so s = RN(a + b), s + e = a + b and
     (s, e) is normalized; otherwise the rounded sum overflows, s is the infinity of the
     sign of a + b, e is the opposite infinity, and a + b is beyond Omega on that side.
     The error term is finite whenever the sum is: no requirement on the operands.
   - add_down_1 and add_up_1 on finite operands (add_down_1_ieee_finite,
     add_up_1_ieee_finite): the result is RD(a + b), or RU(a + b), in the format with
     overflow. One statement for the first three rows of the table.
   - an operand that is not finite (two_sum_ord_ieee_nonfinite, add_down_1_ieee_nonfinite,
     add_up_1_ieee_nonfinite): s, add_down_1 and add_up_1 are the sum of IEEE 754 (an
     infinity plus a finite number or plus itself is that infinity; +infinity plus
     -infinity, or a NaN operand, gives a NaN), and e is a NaN.
   - add_down_1_ieee, add_up_1_ieee, sub_down_1_ieee, sub_up_1_ieee: the two cases in
     one statement, for all operands.
   Also here, because the directed sums need them: the neighbors of the infinities,
   pred(+infinity) = Omega and succ(-infinity) = -Omega (pred_pinf, succ_ninf).

   THE MODELS IN THIS FILE ARE WRITTEN BY HAND (section Listings): each mirrors a listing
   of the design page in the text the generator prints for the IEEE model
   (proofs/gen/IeeeModel.v), and the generated IeeeModel.two_sum_ord, IeeeModel.add_down_1,
   ... replace them. The statements are written by hand too, and will be re-targeted to
   the generated IEEE-model statements, whose shape for a directed sum of two operands is
   not fixed yet. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Convert DirectedSum DirectedProd.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * The listings, as the generator prints a kernel of the IEEE model *)

Section Listings.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.

Local Notation pzero := (IeeeOperations.pzero prec emax).
Local Notation neg := (IeeeOperations.neg prec emax nan_opp).
Local Notation abs := (IeeeOperations.abs prec emax nan_abs).
Local Notation lt := (IeeeOperations.lt prec emax).
Local Notation succ := (IeeeOperations.succ prec emax).
Local Notation pred := (IeeeOperations.pred prec emax).
Local Notation fast_two_sum := (IeeeModel.fast_two_sum prec emax nan_plus nan_minus).

(* Hand-written IEEE model of the listing two_sum_ord; the generated
   IeeeModel.two_sum_ord replaces it. *)
Definition two_sum_ord_ieee_listing (a b : float) : float * float :=
  let aa := abs a in
  let ab := abs b in
  let m := lt aa ab in
  let h := if m then b else a in
  let l := if m then a else b in
  let '(s, e) := fast_two_sum h l in
  (s, e).

(* Hand-written IEEE models of the listings add_down_1 and add_up_1; the generated
   IeeeModel.add_down_1 and IeeeModel.add_up_1 replace them. *)
Definition add_down_1_ieee_listing (a b : float) : float :=
  let '(s, e) := two_sum_ord_ieee_listing a b in
  let n := lt e pzero in
  let p := pred s in
  let r := if n then p else s in
  r.

Definition add_up_1_ieee_listing (a b : float) : float :=
  let '(s, e) := two_sum_ord_ieee_listing a b in
  let n := lt pzero e in
  let q := succ s in
  let r := if n then q else s in
  r.

(* Hand-written IEEE models of the listings sub_down_1 and sub_up_1; the generated
   IeeeModel.sub_down_1 and IeeeModel.sub_up_1 replace them. *)
Definition sub_down_1_ieee_listing (a b : float) : float :=
  let nb := neg b in
  let r := add_down_1_ieee_listing a nb in
  r.

Definition sub_up_1_ieee_listing (a b : float) : float :=
  let nb := neg b in
  let r := add_up_1_ieee_listing a nb in
  r.

End Listings.

(** * The vocabulary of the statements: rounding in the format with overflow *)

(* RD and RU in the format with overflow, as the design page defines them: beyond Omega
   on the side of the rounding the result is the infinity, beyond Omega on the other side
   it is the largest number of that sign. *)
Definition xround_down (prec emax : Z) (t : R) : xreal :=
  if Rlt_bool t (- omega prec emax) then XInf true
  else if Rlt_bool (omega prec emax) t then XFin (omega prec emax)
  else XFin (RD (ieee_emin prec emax) prec t).

Definition xround_up (prec emax : Z) (t : R) : xreal :=
  if Rlt_bool (omega prec emax) t then XInf false
  else if Rlt_bool t (- omega prec emax) then XFin (- omega prec emax)
  else XFin (RU (ieee_emin prec emax) prec t).

(* The sum of IEEE 754 on extended real numbers: an infinity plus a real number or plus
   itself is that infinity, +infinity plus -infinity is a NaN, a NaN gives a NaN. *)
Definition xadd (a b : xreal) : xreal :=
  match a, b with
  | XNaN, _ | _, XNaN => XNaN
  | XFin x, XFin y => XFin (x + y)
  | XInf s, XFin _ => XInf s
  | XFin _, XInf s => XInf s
  | XInf s, XInf s' => if Bool.eqb s s' then XInf s else XNaN
  end.

(* A sum rounded by g when both operands are real numbers, and the sum of IEEE 754
   otherwise. *)
Definition xadd_rounded (g : R -> xreal) (a b : xreal) : xreal :=
  match a, b with
  | XFin x, XFin y => g (x + y)
  | _, _ => xadd a b
  end.

Section IeeeDirected.
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
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation inrange := (inrange emax).
Notation two_sum_ord := (two_sum_ord_ieee_listing prec emax nan_plus nan_minus nan_abs).
Notation add_down_1 := (add_down_1_ieee_listing prec emax nan_plus nan_minus nan_abs).
Notation add_up_1 := (add_up_1_ieee_listing prec emax nan_plus nan_minus nan_abs).
Notation sub_down_1 := (sub_down_1_ieee_listing prec emax nan_plus nan_minus nan_opp nan_abs).
Notation sub_up_1 := (sub_up_1_ieee_listing prec emax nan_plus nan_minus nan_opp nan_abs).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The neighbors of the infinities *)

Lemma Omega_lt_top : Om < bpow radix2 emax.
Proof. unfold Omega. generalize (bpow_gt_0 radix2 (emax - prec)). lra. Qed.

Lemma Omega_gt_0 : 0 < Om.
Proof.
unfold Omega. assert (bpow radix2 (emax - prec) < bpow radix2 emax) by (apply bpow_lt; lia). lra.
Qed.

(* The mantissa of the largest number is 2^prec - 1. *)
Lemma max_mantissa : IZR (Zpos (shift_pos (Z.to_pos prec) 1 - 1)) = bpow radix2 prec - 1.
Proof.
assert (G : forall q : Z, (0 < q)%Z -> Zpos (shift_pos (Z.to_pos q) 1) = Zpower radix2 q).
{ intros [|q|q] Hq; try discriminate Hq. simpl Z.to_pos.
  rewrite shift_pos_correct, Z.mul_1_r. reflexivity. }
assert (E := G prec Hprec).
assert (L : (1 < shift_pos (Z.to_pos prec) 1)%positive).
{ generalize (Zpower_prec_ge_2 prec). lia. }
rewrite (Pos2Z.inj_sub _ _ L), E, minus_IZR, IZR_Zpower by lia. reflexivity.
Qed.

Lemma max_float_value :
  F2R (Float radix2 (Zpos (shift_pos (Z.to_pos prec) 1 - 1)) (emax - prec)) = Om.
Proof.
unfold F2R. cbn [Fnum Fexp]. rewrite max_mantissa. unfold Omega.
rewrite Rmult_minus_distr_r, <- bpow_plus, Rmult_1_l.
replace (prec + (emax - prec))%Z with emax by ring. reflexivity.
Qed.

(* The number of the format before +infinity is Omega, the largest one, and the number
   after -infinity is -Omega. *)
Lemma pred_pinf : fin (fpred pinf) /\ b2r (fpred pinf) = Om.
Proof.
split. reflexivity.
rewrite <- (B2R_B2BSN prec emax (fpred pinf)).
unfold IeeeOperations.pred, Bpred. rewrite B2BSN_lift.
rewrite <- max_float_value. reflexivity.
Qed.

Lemma succ_ninf : fin (fsucc ninf) /\ b2r (fsucc ninf) = - Om.
Proof.
split. reflexivity.
rewrite <- (B2R_B2BSN prec emax (fsucc ninf)).
unfold IeeeOperations.succ, Bsucc. rewrite B2BSN_lift.
rewrite <- max_float_value, <- F2R_Zopp. reflexivity.
Qed.

(** * Sums of finite numbers, and sums with an infinity *)

(* The sign of a finite number and the sign of its value. *)
Lemma sign_false_nonneg : forall x : float, fin x -> Bsign prec emax x = false -> 0 <= b2r x.
Proof.
intros [s|s|s pl H|s m e H] F S; try discriminate F.
- simpl. lra.
- simpl in S. subst s. left. apply finite_sign_pos.
Qed.

Lemma sign_true_nonpos : forall x : float, fin x -> Bsign prec emax x = true -> b2r x <= 0.
Proof.
intros [s|s|s pl H|s m e H] F S; try discriminate F.
- simpl. lra.
- simpl in S. subst s. left. apply finite_sign_neg.
Qed.

(* The sum of two finite numbers: finite, with the rounded real sum as its value, or
   the infinity of the common sign of the operands when the rounded sum is out of range. *)
Lemma add_finite_cases :
  forall h l : float, fin h -> fin l ->
  (fin (add h l) /\ b2r (add h l) = rnd (b2r h + b2r l)) \/
  (add h l = B754_infinity prec emax (Bsign prec emax h) /\
   Bsign prec emax h = Bsign prec emax l /\ ~ inrange (rnd (b2r h + b2r l))).
Proof.
intros h l Fh Fl.
generalize (Bplus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus
              BinarySingleNaN.mode_NE h l Fh Fl).
fold (add h l).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r h + b2r l))
  with (rnd (b2r h + b2r l)).
destruct (Rlt_bool_spec (Rabs (rnd (b2r h + b2r l))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. left. split; assumption.
- intros [E S]. right. split; [|split; [exact S|]].
  + apply B2FF_inf_inv. rewrite E. apply overflow_NE.
  + unfold IeeeBridge.inrange. lra.
Qed.

Lemma sub_inf_finite :
  forall (sg : bool) (h : float), fin h ->
  sub (B754_infinity prec emax sg) h = B754_infinity prec emax sg.
Proof. intros sg [s|s|s pl H|s m e H] F; try discriminate F; reflexivity. Qed.

Lemma sub_finite_inf :
  forall (sg : bool) (l : float), fin l ->
  sub l (B754_infinity prec emax sg) = B754_infinity prec emax (negb sg).
Proof. intros sg [s|s|s pl H|s m e H] F; try discriminate F; reflexivity. Qed.

(* fast_two_sum on finite operands with |l| <= |h|: a finite sum has a finite error term
   and both are those of the real model; otherwise the sum is the infinity of the sign
   of h + l, the error term the opposite infinity, and h + l is beyond Omega. *)
Lemma fast_two_sum_ieee_all :
  (2 <= prec)%Z ->
  forall h l : float, fin h -> fin l -> Rabs (b2r l) <= Rabs (b2r h) ->
  let '(s, e) := IeeeModel.fast_two_sum prec emax nan_plus nan_minus h l in
  (fin s -> fin e /\
   (b2r s, b2r e) = Model.fast_two_sum emin prec tie_even (b2r h) (b2r l)) /\
  (is_finite prec emax s = false ->
   exists sg : bool,
   s = B754_infinity prec emax sg /\ e = B754_infinity prec emax (negb sg) /\
   (if sg then b2r h + b2r l < - Om else Om < b2r h + b2r l)).
Proof.
intros Hp h l Fh Fl Hhl.
generalize (fast_two_sum_values prec emax nan_plus nan_minus nan_abs
              (fun _ _ x => nan_abs x) Hp h l Fh Fl Hhl).
unfold IeeeModel.fast_two_sum. cbv zeta. intros V. split; [exact V|].
intros Fs. destruct (add_finite_cases h l Fh Fl) as [[F _]|[E [S R]]]; [congruence|].
exists (Bsign prec emax h). rewrite E, (sub_inf_finite _ h Fh), (sub_finite_inf _ l Fl).
split; [reflexivity|split; [reflexivity|]].
assert (Big : Om < Rabs (b2r h + b2r l)).
{ apply Rnot_le_lt. intros K. apply R. now apply (rnd_le_Omega prec emax). }
destruct (Bsign prec emax h) eqn:Sh.
- generalize (sign_true_nonpos h Fh Sh) (sign_true_nonpos l Fl (eq_sym S)). intros A B.
  rewrite Rabs_left1 in Big by lra. lra.
- generalize (sign_false_nonneg h Fh Sh) (sign_false_nonneg l Fl (eq_sym S)). intros A B.
  rewrite Rabs_pos_eq in Big by lra. lra.
Qed.

(** * two_sum_ord *)

(* Finite operands. If the sum s is finite, the error term e is finite and (s, e) is the
   pair of the real model: s = RN(a + b), s + e = a + b, (s, e) normalized
   (two_sum_ord_listing_correct). Otherwise the rounded sum overflows: s is the infinity
   of the sign of a + b, e the opposite infinity, and a + b is beyond Omega. *)
Theorem two_sum_ord_ieee_finite :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  let '(s, e) := two_sum_ord a b in
  (fin s -> fin e /\
   (b2r s, b2r e) = two_sum_ord_listing emin prec tie_even (b2r a) (b2r b)) /\
  (is_finite prec emax s = false ->
   exists sg : bool,
   s = B754_infinity prec emax sg /\ e = B754_infinity prec emax (negb sg) /\
   (if sg then b2r a + b2r b < - Om else Om < b2r a + b2r b)).
Proof.
intros Hp a b Fa Fb. unfold two_sum_ord_ieee_listing, two_sum_ord_listing. cbv zeta.
rewrite (lt_finite prec emax (fabs a) (fabs b))
  by (rewrite (abs_finite prec emax nan_abs); assumption).
rewrite 2!(abs_val prec emax nan_abs).
destruct (Rlt_bool_spec (Rabs (b2r a)) (Rabs (b2r b))) as [M|M].
- generalize (fast_two_sum_ieee_all Hp b a Fb Fa (Rlt_le _ _ M)).
  destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus b a) as [s e].
  rewrite (Rplus_comm (b2r b) (b2r a)).
  destruct (Model.fast_two_sum emin prec tie_even (b2r b) (b2r a)). trivial.
- generalize (fast_two_sum_ieee_all Hp a b Fa Fb M).
  destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus a b) as [s e].
  destruct (Model.fast_two_sum emin prec tie_even (b2r a) (b2r b)). trivial.
Qed.

(* An operand that is not finite: s is the sum of IEEE 754, and e is a NaN. *)
Theorem two_sum_ord_ieee_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  let '(s, e) := two_sum_ord a b in
  xv s = xadd (xv a) (xv b) /\ is_nan prec emax e = true.
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [H|H];
  try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  split; reflexivity.
Qed.

(** * add_down_1 and add_up_1 *)

Lemma xround_down_in :
  forall t : R, - Om <= t <= Om ->
  xround_down prec emax t = XFin (RD emin prec t).
Proof.
intros t [H1 H2]. unfold xround_down. change (omega prec emax) with Om.
rewrite Rlt_bool_false by exact H1. now rewrite Rlt_bool_false by exact H2.
Qed.

Lemma xround_up_in :
  forall t : R, - Om <= t <= Om ->
  xround_up prec emax t = XFin (RU emin prec t).
Proof.
intros t [H1 H2]. unfold xround_up. change (omega prec emax) with Om.
rewrite Rlt_bool_false by exact H2. now rewrite Rlt_bool_false by exact H1.
Qed.

(* A finite limb is at most Omega in magnitude. *)
Lemma b2r_Omega : forall x : float, - Om <= b2r x <= Om.
Proof.
intros x. apply Rabs_le_inv. apply (inrange_le_Omega prec emax).
- apply b2r_format.
- apply b2r_inrange.
Qed.

(* A number of the format strictly between -2^emax and 2^emax is at most Omega in
   magnitude. *)
Lemma format_Omega_bounds :
  forall r : R, format r -> - bpow radix2 emax < r < bpow radix2 emax -> - Om <= r <= Om.
Proof.
intros r F H. apply Rabs_le_inv. apply (inrange_le_Omega prec emax); trivial.
unfold IeeeBridge.inrange. now apply Rabs_lt.
Qed.

(* add_down_1 on finite operands: RD(a + b) in the format with overflow. This is the
   first three rows of the table: a sum in range, an overflow upward (Omega), an
   overflow downward (-infinity). *)
Theorem add_down_1_ieee_finite :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  xv (add_down_1 a b) = xround_down prec emax (b2r a + b2r b).
Proof.
intros Hp a b Fa Fb. unfold add_down_1_ieee_listing.
generalize (two_sum_ord_ieee_finite Hp a b Fa Fb).
destruct (two_sum_ord a b) as [s e]. intros [Hfin Hinf]. cbv zeta.
assert (Hp1 : (1 <= prec)%Z) by lia.
destruct (finite_dec prec emax s) as [Fs|Fs].
- destruct (Hfin Fs) as [Fe E].
  destruct (two_sum_ord_listing_facts emin prec Hp (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)) as [Hs [He Hn]].
  rewrite <- E in Hs, He, Hn. cbn [fst snd] in Hs, He, Hn.
  rewrite (lt_finite prec emax e pzero Fe eq_refl). change (b2r pzero) with 0.
  generalize (down_of_normalized emin prec Hp1 (b2r s) (b2r e) (b2r a + b2r b) Hn He).
  destruct (normalized_2_between emin prec (b2r s) (b2r e) Hn) as [B1 B2].
  rewrite He in B1, B2.
  generalize (b2r_Omega s). intros Bs.
  destruct (Rlt_bool_spec (b2r e) 0) as [En|En]; intros D.
  + (* a negative error: one step down, which may leave the range *)
    destruct (pred_finite prec emax s Fs) as [[Fp [Ep Lp]]|[Ep Lp]].
    * rewrite (xval_fin prec emax _ Fp), Ep, D. symmetry. apply xround_down_in.
      assert (K : - Om <= Ulp.pred radix2 fexp (b2r s) <= Om).
      { apply format_Omega_bounds.
        - apply generic_format_pred; auto with typeclass_instances. apply b2r_format.
        - split; [exact Lp|]. generalize (pred_FLT_lt emin prec (b2r s)) Omega_lt_top. lra. }
      lra.
    * rewrite Ep. unfold xround_down. change (omega prec emax) with Om.
      rewrite Rlt_bool_true; [reflexivity|].
      assert (K : b2r s <= - Om).
      { apply Rnot_lt_le. intros K.
        assert (- Om <= Ulp.pred radix2 fexp (b2r s)).
        { apply pred_ge_gt; auto with typeclass_instances.
          - apply generic_format_opp. apply (format_Omega prec emax).
          - apply b2r_format. }
        generalize Omega_lt_top. lra. }
      lra.
  + (* otherwise the rounded sum itself *)
    rewrite (xval_fin prec emax _ Fs).
    unfold xround_down. change (omega prec emax) with Om.
    rewrite Rlt_bool_false by lra.
    destruct (Rlt_bool_spec Om (b2r a + b2r b)) as [C|C].
    * f_equal. apply Rle_antisym; [lra|]. rewrite Hs.
      apply round_ge_generic; auto with typeclass_instances. apply (format_Omega prec emax). lra.
    * now rewrite D.
- destruct (Hinf Fs) as [sg [Es [Ee V]]]. subst s e.
  unfold xround_down. change (omega prec emax) with Om. generalize Omega_gt_0. intros P0.
  destruct sg; cbn [negb].
  + (* overflow downward: -infinity *)
    change (flt (B754_infinity prec emax false) pzero) with false.
    rewrite Rlt_bool_true by exact V. reflexivity.
  + (* overflow upward: Omega *)
    change (flt (B754_infinity prec emax true) pzero) with true.
    destruct pred_pinf as [Fp Ep].
    change (B754_infinity prec emax false) with pinf.
    rewrite (xval_fin prec emax _ Fp), Ep.
    rewrite Rlt_bool_false by lra. now rewrite Rlt_bool_true by exact V.
Qed.

(* add_up_1 on finite operands: RU(a + b) in the format with overflow. *)
Theorem add_up_1_ieee_finite :
  (2 <= prec)%Z ->
  forall a b : float, fin a -> fin b ->
  xv (add_up_1 a b) = xround_up prec emax (b2r a + b2r b).
Proof.
intros Hp a b Fa Fb. unfold add_up_1_ieee_listing.
generalize (two_sum_ord_ieee_finite Hp a b Fa Fb).
destruct (two_sum_ord a b) as [s e]. intros [Hfin Hinf]. cbv zeta.
assert (Hp1 : (1 <= prec)%Z) by lia.
destruct (finite_dec prec emax s) as [Fs|Fs].
- destruct (Hfin Fs) as [Fe E].
  destruct (two_sum_ord_listing_facts emin prec Hp (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)) as [Hs [He Hn]].
  rewrite <- E in Hs, He, Hn. cbn [fst snd] in Hs, He, Hn.
  rewrite (lt_finite prec emax pzero e eq_refl Fe). change (b2r pzero) with 0.
  generalize (up_of_normalized emin prec Hp1 (b2r s) (b2r e) (b2r a + b2r b) Hn He).
  destruct (normalized_2_between emin prec (b2r s) (b2r e) Hn) as [B1 B2].
  rewrite He in B1, B2.
  generalize (b2r_Omega s). intros Bs.
  destruct (Rlt_bool_spec 0 (b2r e)) as [En|En]; intros D.
  + destruct (succ_finite prec emax s Fs) as [[Fp [Ep Lp]]|[Ep Lp]].
    * rewrite (xval_fin prec emax _ Fp), Ep, D. symmetry. apply xround_up_in.
      assert (K : - Om <= Ulp.succ radix2 fexp (b2r s) <= Om).
      { apply format_Omega_bounds.
        - apply generic_format_succ; auto with typeclass_instances. apply b2r_format.
        - split; [|exact Lp]. generalize (succ_FLT_gt emin prec (b2r s)) Omega_lt_top. lra. }
      lra.
    * rewrite Ep. unfold xround_up. change (omega prec emax) with Om.
      rewrite Rlt_bool_true; [reflexivity|].
      assert (K : Om <= b2r s).
      { apply Rnot_lt_le. intros K.
        assert (Ulp.succ radix2 fexp (b2r s) <= Om).
        { apply succ_le_lt; auto with typeclass_instances.
          - apply b2r_format.
          - apply (format_Omega prec emax). }
        generalize Omega_lt_top. lra. }
      lra.
  + rewrite (xval_fin prec emax _ Fs).
    unfold xround_up. change (omega prec emax) with Om.
    rewrite Rlt_bool_false by lra.
    destruct (Rlt_bool_spec (b2r a + b2r b) (- Om)) as [C|C].
    * f_equal. apply Rle_antisym; [|lra]. rewrite Hs.
      apply round_le_generic; auto with typeclass_instances.
      apply generic_format_opp. apply (format_Omega prec emax). lra.
    * now rewrite D.
- destruct (Hinf Fs) as [sg [Es [Ee V]]]. subst s e.
  unfold xround_up. change (omega prec emax) with Om. generalize Omega_gt_0. intros P0.
  destruct sg; cbn [negb].
  + (* overflow downward: -Omega *)
    change (flt pzero (B754_infinity prec emax false)) with true.
    destruct succ_ninf as [Fp Ep].
    rewrite (xval_fin prec emax _ Fp), Ep.
    rewrite Rlt_bool_false by lra. now rewrite Rlt_bool_true by exact V.
  + (* overflow upward: +infinity *)
    change (flt pzero (B754_infinity prec emax true)) with false.
    rewrite Rlt_bool_true by exact V. reflexivity.
Qed.

(* An operand that is not finite: add_down_1 and add_up_1 return the sum of IEEE 754. *)
Theorem add_down_1_ieee_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xv (add_down_1 a b) = xadd (xv a) (xv b).
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [H|H];
  try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  reflexivity.
Qed.

Theorem add_up_1_ieee_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xv (add_up_1 a b) = xadd (xv a) (xv b).
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] [H|H];
  try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  reflexivity.
Qed.

(* All operands, in one statement: the directed rounding, in the format with overflow,
   of the sum of two finite operands, and the sum of IEEE 754 otherwise. *)
Theorem add_down_1_ieee :
  (2 <= prec)%Z ->
  forall a b : float,
  xv (add_down_1 a b) = xadd_rounded (xround_down prec emax) (xv a) (xv b).
Proof.
intros Hp a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xadd_rounded].
  now apply add_down_1_ieee_finite.
- rewrite (add_down_1_ieee_nonfinite a b (or_intror Fb)).
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb; destruct (xv a); reflexivity.
- rewrite (add_down_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- rewrite (add_down_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
Qed.

Theorem add_up_1_ieee :
  (2 <= prec)%Z ->
  forall a b : float,
  xv (add_up_1 a b) = xadd_rounded (xround_up prec emax) (xv a) (xv b).
Proof.
intros Hp a b.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xadd_rounded].
  now apply add_up_1_ieee_finite.
- rewrite (add_up_1_ieee_nonfinite a b (or_intror Fb)).
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb; destruct (xv a); reflexivity.
- rewrite (add_up_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
- rewrite (add_up_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; reflexivity.
Qed.

(** * sub_down_1 and sub_up_1 *)

(* The extended real number of an opposite. *)
Lemma xval_neg : forall b : float, xv (neg b) = xopp (xv b).
Proof.
intros b. destruct (finite_dec prec emax b) as [F|F].
- assert (F' : fin (neg b)) by (unfold IeeeOperations.neg; now rewrite is_finite_Bopp).
  rewrite (xval_fin prec emax b F), (xval_fin prec emax (neg b) F').
  cbn [xopp]. f_equal. apply (neg_value prec emax nan_opp).
- destruct b as [s|s|s pl H|s m e H]; try discriminate F; reflexivity.
Qed.

(* The differences, for all operands: the directed rounding of a - b in the format with
   overflow for finite operands, and the difference of IEEE 754 (the sum of a and of the
   opposite of b) otherwise. *)
Theorem sub_down_1_ieee :
  (2 <= prec)%Z ->
  forall a b : float,
  xv (sub_down_1 a b) = xadd_rounded (xround_down prec emax) (xv a) (xopp (xv b)).
Proof.
intros Hp a b. unfold sub_down_1_ieee_listing. cbv zeta.
rewrite <- xval_neg. now apply add_down_1_ieee.
Qed.

Theorem sub_up_1_ieee :
  (2 <= prec)%Z ->
  forall a b : float,
  xv (sub_up_1 a b) = xadd_rounded (xround_up prec emax) (xv a) (xopp (xv b)).
Proof.
intros Hp a b. unfold sub_up_1_ieee_listing. cbv zeta.
rewrite <- xval_neg. now apply add_up_1_ieee.
Qed.

End IeeeDirected.
