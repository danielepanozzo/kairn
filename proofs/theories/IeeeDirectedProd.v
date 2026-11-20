(* Rounding a product down and up without a rounding mode, in the IEEE model, on all
   values: finite numbers, infinities and NaN. The IEEE-model statement of
   docs/developer/design/milestone2.md, "Rounding a product down and up", for mul_down_1
   and mul_up_1, and what the product of intervals needs of mul_dir_1 ("One limb").

   Notation as in IeeeDirected.v: Omega is the largest number of the format, val the real
   value of a finite limb, xval the extended real number of a limb; x = val a * val b;
   P = 2^(2 prec - 1) eta; RD and RU in the format with overflow are xround_down and
   xround_up.

   What is proved, for every precision:
   - mul_down_1 and mul_up_1 on finite operands (mul_down_1_ieee_finite,
     mul_up_1_ieee_finite): the result is on the right side of x, as extended real
     numbers (mul_down_1 can be -infinity and mul_up_1 +infinity, never the reverse); it
     is the directed rounding of x in the format with overflow, or, only for a nonzero
     product with |RN(x)| < P, the finite number one step beyond the directed rounding;
     and it is the directed rounding when x = 0 or |RN(x)| >= P. A product that overflows
     upward gives Omega and +infinity, one that overflows downward -infinity and -Omega.
   - an operand that is not finite (mul_down_1_ieee_nonfinite, mul_up_1_ieee_nonfinite):
     both return the product of IEEE 754, prod a b, bit for bit: the infinity of the sign
     of the product, and a NaN for zero times infinity and for a NaN operand.
   - mul_dir_1 (mul_dir_1_ieee_encloses): for operands that are not NaN, the two outputs
     d and v satisfy d <= a b <= v, where a b is the product of extended real numbers
     with 0 * infinity = 0 (xmul0 of Rectangle.v). These are the hypotheses of
     interval_mul_lower and interval_mul_upper for the four products of bounds. In
     particular neither output is a NaN: a zero factor gives the literal zero and never
     meets an infinity.

   THE MODELS IN THIS FILE ARE WRITTEN BY HAND (section Listings): each mirrors a listing
   of the design page in the text the generator prints for the IEEE model, and the
   generated IeeeModel.mul_down_1, IeeeModel.mul_up_1, IeeeModel.mul_dir_1 and the
   generated constant replace them. The statements are written by hand too, and will be
   re-targeted to the generated IEEE-model statements. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Convert DirectedSum DirectedProd.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt.
From Kairn Require Import Rectangle IeeeProduct IeeeDirected.
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

Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Local Notation pzero := (IeeeOperations.pzero prec emax).
Local Notation abs := (IeeeOperations.abs prec emax nan_abs).
Local Notation lt := (IeeeOperations.lt prec emax).
Local Notation eq := (IeeeOperations.eq prec emax).
Local Notation succ := (IeeeOperations.succ prec emax).
Local Notation pred := (IeeeOperations.pred prec emax).
Local Notation const_of := (IeeeOperations.const_of prec emax).
Local Notation two_prod := (IeeeModel.two_prod prec emax nan_opp nan_fma).

(* Hand-written copy of the constant `const up(eta/(2*u^2))` in the IEEE model: the
   number of the format whose value is the constant of the real model. The generated
   constant replaces it. *)
Definition const_P_ieee : float := const_of (const_P (3 - emax - prec) prec).

(* Hand-written IEEE models of the listings mul_down_1, mul_up_1 and mul_dir_1; the
   generated IeeeModel.mul_down_1, IeeeModel.mul_up_1 and IeeeModel.mul_dir_1 replace
   them. *)
Definition mul_down_1_ieee_listing (a b : float) : float :=
  let '(p, e) := two_prod a b in
  let ap := abs p in
  let bd := lt ap const_P_ieee in
  let ez := eq e pzero in
  let un := andb bd ez in
  let n := lt e pzero in
  let sd := orb n un in
  let pp := pred p in
  let d := if sd then pp else p in
  let za := eq a pzero in
  let zb := eq b pzero in
  let zz := orb za zb in
  let r := if zz then p else d in
  r.

Definition mul_up_1_ieee_listing (a b : float) : float :=
  let '(p, e) := two_prod a b in
  let ap := abs p in
  let bd := lt ap const_P_ieee in
  let ez := eq e pzero in
  let un := andb bd ez in
  let n := lt pzero e in
  let su := orb n un in
  let sp := succ p in
  let v := if su then sp else p in
  let za := eq a pzero in
  let zb := eq b pzero in
  let zz := orb za zb in
  let r := if zz then p else v in
  r.

Definition mul_dir_1_ieee_listing (a b : float) : float * float :=
  let '(p, e) := two_prod a b in
  let ap := abs p in
  let bd := lt ap const_P_ieee in
  let ez := eq e pzero in
  let un := andb bd ez in
  let n := lt e pzero in
  let sd := orb n un in
  let pp := pred p in
  let dz := if sd then pp else p in
  let q := lt pzero e in
  let su := orb q un in
  let sp := succ p in
  let vz := if su then sp else p in
  let za := eq a pzero in
  let zb := eq b pzero in
  let zz := orb za zb in
  let d := if zz then pzero else dz in
  let v := if zz then pzero else vz in
  (d, v).

End Listings.

Section IeeeDirectedProd.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation rd := (round radix2 fexp Zfloor).
Notation ru := (round radix2 fexp Zceil).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation fpred := (IeeeOperations.pred prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation Om := (Omega prec emax).
Notation inrange := (inrange emax).
Notation P := (bpow radix2 (2 * prec - 1 + emin)).
Notation cP := (const_P_ieee prec emax).
Notation mul_down_1 := (mul_down_1_ieee_listing prec emax nan_opp nan_abs nan_fma).
Notation mul_up_1 := (mul_up_1_ieee_listing prec emax nan_opp nan_abs nan_fma).
Notation mul_dir_1 := (mul_dir_1_ieee_listing prec emax nan_opp nan_abs nan_fma).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The constant, and the product of two finite numbers *)

(* The constant of the listings is the finite number of value P, and P <= Omega. *)
Lemma const_P_ieee_spec : fin cP /\ b2r cP = const_P emin prec.
Proof.
unfold const_P_ieee. apply const_of_spec; rewrite (const_P_eq emin prec).
- apply generic_format_bpow. unfold FLT_exp. lia.
- rewrite Rabs_pos_eq by apply bpow_ge_0. apply bpow_lt. lia.
Qed.

Lemma P_le_Omega : P <= Om.
Proof.
apply Rle_trans with (bpow radix2 (emax - 1)).
- apply bpow_le. lia.
- unfold Omega. replace emax with (emax - 1 + 1)%Z at 2 by ring.
  rewrite bpow_plus, pow2_1.
  assert (bpow radix2 (emax - prec) <= bpow radix2 (emax - 1)) by (apply bpow_le; lia).
  lra.
Qed.

(* The product of two finite numbers: finite, with the rounded real product as its
   value, or the infinity of the sign of the real product when that is out of range. *)
Lemma prod_finite_cases :
  forall a b : float, fin a -> fin b ->
  (fin (prod a b) /\ b2r (prod a b) = rnd (b2r a * b2r b)) \/
  (prod a b = B754_infinity prec emax (Rlt_bool (b2r a * b2r b) 0) /\
   ~ inrange (rnd (b2r a * b2r b))).
Proof.
intros a b Fa Fb.
generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE
              a b pzero Fa Fb eq_refl).
cbv zeta. change (b2r pzero) with 0. rewrite Rplus_0_r.
change (Bfma prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE a b pzero)
  with (prod a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a * b2r b))
  with (rnd (b2r a * b2r b)).
destruct (Rlt_bool_spec (Rabs (rnd (b2r a * b2r b))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. left. split; assumption.
- intros E. right. split.
  + apply B2FF_inf_inv. rewrite E. apply overflow_NE.
  + unfold IeeeBridge.inrange. lra.
Qed.

Lemma fma_finite_inf :
  forall (a b : float) (sz : bool), fin a -> fin b ->
  fma a b (B754_infinity prec emax sz) = B754_infinity prec emax sz.
Proof.
intros [sa|sa|sa pa Ha|sa ma ea Ha] [sb|sb|sb pb Hb|sb mb eb Hb] sz Fa Fb;
  try discriminate Fa; try discriminate Fb; reflexivity.
Qed.

(* two_prod on finite operands: a finite product has a finite error term and both are
   those of the real model; otherwise the product is the infinity of the sign of a b,
   the error term the opposite infinity, and a b is beyond Omega. *)
Lemma two_prod_ieee_all :
  forall a b : float, fin a -> fin b ->
  let '(p, e) := IeeeModel.two_prod prec emax nan_opp nan_fma a b in
  (fin p -> fin e /\
   (b2r p, b2r e) = Model.two_prod emin prec tie_even (b2r a) (b2r b)) /\
  (is_finite prec emax p = false ->
   exists sg : bool,
   p = B754_infinity prec emax sg /\ e = B754_infinity prec emax (negb sg) /\
   (if sg then b2r a * b2r b < - Om else Om < b2r a * b2r b)).
Proof.
intros a b Fa Fb.
generalize (two_prod_values prec emax (fun x _ => nan_opp x) (fun x _ => nan_opp x)
              nan_opp nan_fma a b Fa Fb).
unfold IeeeModel.two_prod. cbv zeta. intros V. split; [exact V|].
intros Fp. destruct (prod_finite_cases a b Fa Fb) as [[F _]|[E R]]; [congruence|].
exists (Rlt_bool (b2r a * b2r b) 0). rewrite E. unfold IeeeOperations.fms.
change (IeeeOperations.neg prec emax nan_opp
          (B754_infinity prec emax (Rlt_bool (b2r a * b2r b) 0)))
  with (B754_infinity prec emax (negb (Rlt_bool (b2r a * b2r b) 0))).
rewrite (fma_finite_inf a b _ Fa Fb).
split; [reflexivity|split; [reflexivity|]].
assert (Big : Om < Rabs (b2r a * b2r b)).
{ apply Rnot_le_lt. intros K. apply R. now apply (rnd_le_Omega prec emax). }
destruct (Rlt_bool_spec (b2r a * b2r b) 0) as [C|C].
- rewrite Rabs_left in Big by exact C. lra.
- rewrite Rabs_pos_eq in Big by exact C. exact Big.
Qed.

(** * The directed roundings in the format with overflow *)

(* If RD(x), in the format with no largest number, is strictly between -2^emax and 2^emax,
   it is the rounding down of x in the format with overflow; if it is at most -2^emax,
   that rounding is -infinity. Symmetrically for RU. *)
Lemma xround_down_finite :
  forall x : R, - bpow radix2 emax < rd x < bpow radix2 emax ->
  xround_down prec emax x = XFin (rd x).
Proof.
intros x H.
assert (F : format (rd x)) by (apply generic_format_round; auto with typeclass_instances).
destruct (format_Omega_bounds prec emax (rd x) F H) as [B1 B2].
destruct (round_DN_pt radix2 fexp x) as [_ [L G]].
unfold xround_down. change (omega prec emax) with Om.
rewrite Rlt_bool_false by lra.
destruct (Rlt_bool_spec Om x) as [C|C]; [|reflexivity].
f_equal. apply Rle_antisym; [|exact B2].
apply G. apply (format_Omega prec emax). lra.
Qed.

Lemma xround_down_low :
  forall x : R, rd x <= - bpow radix2 emax -> xround_down prec emax x = XInf true.
Proof.
intros x H. unfold xround_down. change (omega prec emax) with Om.
rewrite Rlt_bool_true; [reflexivity|].
apply Rnot_le_lt. intros K.
destruct (round_DN_pt radix2 fexp x) as [_ [_ G]].
assert (- Om <= rd x).
{ apply G; trivial. apply generic_format_opp. apply (format_Omega prec emax). }
generalize (Omega_lt_top prec emax). lra.
Qed.

Lemma xround_up_finite :
  forall x : R, - bpow radix2 emax < ru x < bpow radix2 emax ->
  xround_up prec emax x = XFin (ru x).
Proof.
intros x H.
assert (F : format (ru x)) by (apply generic_format_round; auto with typeclass_instances).
destruct (format_Omega_bounds prec emax (ru x) F H) as [B1 B2].
destruct (round_UP_pt radix2 fexp x) as [_ [L G]].
unfold xround_up. change (omega prec emax) with Om.
rewrite Rlt_bool_false by lra.
destruct (Rlt_bool_spec x (- Om)) as [C|C]; [|reflexivity].
f_equal. apply Rle_antisym; [exact B1|].
apply G. apply generic_format_opp. apply (format_Omega prec emax). lra.
Qed.

Lemma xround_up_high :
  forall x : R, bpow radix2 emax <= ru x -> xround_up prec emax x = XInf false.
Proof.
intros x H. unfold xround_up. change (omega prec emax) with Om.
rewrite Rlt_bool_true; [reflexivity|].
apply Rnot_le_lt. intros K.
destruct (round_UP_pt radix2 fexp x) as [_ [_ G]].
assert (ru x <= Om).
{ apply G; trivial. apply (format_Omega prec emax). }
generalize (Omega_lt_top prec emax). lra.
Qed.

(** * The selections of the listings *)

(* The last lines of mul_down_1 on finite p and e: the limb they select has the value
   that the same lines select in the real model, unless that value is at most -2^emax,
   in which case the limb is -infinity and p is -Omega or below. *)
Lemma down_select_real :
  forall a b p e : float, fin a -> fin b -> fin p -> fin e ->
  let r := if orb (feq a pzero) (feq b pzero) then p
           else if orb (flt e pzero) (andb (flt (fabs p) cP) (feq e pzero))
                then fpred p else p in
  let rr := if orb (Req_bool (b2r a) 0) (Req_bool (b2r b) 0) then b2r p
            else if orb (Rlt_bool (b2r e) 0)
                        (andb (Rlt_bool (Rabs (b2r p)) (const_P emin prec)) (Req_bool (b2r e) 0))
                 then Ulp.pred radix2 fexp (b2r p) else b2r p in
  (fin r /\ b2r r = rr) \/ (r = ninf /\ rr <= - bpow radix2 emax /\ b2r p <= - Om).
Proof.
intros a b p e Fa Fb Fp Fe. cbv zeta.
destruct const_P_ieee_spec as [Fc Ec].
assert (Fap : fin (fabs p)) by (rewrite (abs_finite prec emax nan_abs); exact Fp).
rewrite (lt_finite prec emax (fabs p) cP Fap Fc), (abs_val prec emax nan_abs), Ec.
rewrite (eq_finite prec emax e pzero Fe eq_refl), (lt_finite prec emax e pzero Fe eq_refl).
rewrite (eq_finite prec emax a pzero Fa eq_refl), (eq_finite prec emax b pzero Fb eq_refl).
change (b2r pzero) with 0.
destruct (orb (Req_bool (b2r a) 0) (Req_bool (b2r b) 0)).
{ left. split; [exact Fp|reflexivity]. }
destruct (orb (Rlt_bool (b2r e) 0)
              (andb (Rlt_bool (Rabs (b2r p)) (const_P emin prec)) (Req_bool (b2r e) 0))).
- destruct (pred_finite prec emax p Fp) as [[F' [E' _]]|[E' L']].
  + left. split; assumption.
  + right. split; [exact E'|split; [exact L'|]].
    apply Rnot_lt_le. intros K.
    assert (- Om <= Ulp.pred radix2 fexp (b2r p)).
    { apply pred_ge_gt; auto with typeclass_instances.
      - apply generic_format_opp. apply (format_Omega prec emax).
      - apply b2r_format. }
    generalize (Omega_lt_top prec emax). lra.
- left. split; [exact Fp|reflexivity].
Qed.

Lemma up_select_real :
  forall a b p e : float, fin a -> fin b -> fin p -> fin e ->
  let r := if orb (feq a pzero) (feq b pzero) then p
           else if orb (flt pzero e) (andb (flt (fabs p) cP) (feq e pzero))
                then fsucc p else p in
  let rr := if orb (Req_bool (b2r a) 0) (Req_bool (b2r b) 0) then b2r p
            else if orb (Rlt_bool 0 (b2r e))
                        (andb (Rlt_bool (Rabs (b2r p)) (const_P emin prec)) (Req_bool (b2r e) 0))
                 then Ulp.succ radix2 fexp (b2r p) else b2r p in
  (fin r /\ b2r r = rr) \/ (r = pinf /\ bpow radix2 emax <= rr /\ Om <= b2r p).
Proof.
intros a b p e Fa Fb Fp Fe. cbv zeta.
destruct const_P_ieee_spec as [Fc Ec].
assert (Fap : fin (fabs p)) by (rewrite (abs_finite prec emax nan_abs); exact Fp).
rewrite (lt_finite prec emax (fabs p) cP Fap Fc), (abs_val prec emax nan_abs), Ec.
rewrite (eq_finite prec emax e pzero Fe eq_refl), (lt_finite prec emax pzero e eq_refl Fe).
rewrite (eq_finite prec emax a pzero Fa eq_refl), (eq_finite prec emax b pzero Fb eq_refl).
change (b2r pzero) with 0.
destruct (orb (Req_bool (b2r a) 0) (Req_bool (b2r b) 0)).
{ left. split; [exact Fp|reflexivity]. }
destruct (orb (Rlt_bool 0 (b2r e))
              (andb (Rlt_bool (Rabs (b2r p)) (const_P emin prec)) (Req_bool (b2r e) 0))).
- destruct (succ_finite prec emax p Fp) as [[F' [E' _]]|[E' L']].
  + left. split; assumption.
  + right. split; [exact E'|split; [exact L'|]].
    apply Rnot_lt_le. intros K.
    assert (Ulp.succ radix2 fexp (b2r p) <= Om).
    { apply succ_le_lt; auto with typeclass_instances.
      - apply b2r_format.
      - apply (format_Omega prec emax). }
    generalize (Omega_lt_top prec emax). lra.
- left. split; [exact Fp|reflexivity].
Qed.

(* The same lines when p is an infinity and e the opposite infinity (an overflow). *)
Lemma down_select_inf :
  forall (sg : bool) (c : float),
  (if orb (flt (B754_infinity prec emax (negb sg)) pzero)
          (andb (flt (fabs (B754_infinity prec emax sg)) c)
                (feq (B754_infinity prec emax (negb sg)) pzero))
   then fpred (B754_infinity prec emax sg) else B754_infinity prec emax sg)
  = if sg then ninf else fpred pinf.
Proof. intros [|] [sc|[|]|sc pc Hc|sc mc ec Hc]; reflexivity. Qed.

Lemma up_select_inf :
  forall (sg : bool) (c : float),
  (if orb (flt pzero (B754_infinity prec emax (negb sg)))
          (andb (flt (fabs (B754_infinity prec emax sg)) c)
                (feq (B754_infinity prec emax (negb sg)) pzero))
   then fsucc (B754_infinity prec emax sg) else B754_infinity prec emax sg)
  = if sg then fsucc ninf else pinf.
Proof. intros [|] [sc|[|]|sc pc Hc|sc mc ec Hc]; reflexivity. Qed.

(** * mul_down_1 and mul_up_1 on finite operands *)

(* mul_down_1, finite operands, with x = val a * val b. The result is at most x; it is
   RD(x) in the format with overflow, or (only for a nonzero product with |RN(x)| < P)
   the finite number before RD(x); and it is RD(x) in the format with overflow when
   x = 0 or |RN(x)| >= P. An overflow upward gives Omega, and downward -infinity. *)
Theorem mul_down_1_ieee_finite :
  forall a b : float, fin a -> fin b ->
  let x := b2r a * b2r b in
  let r := mul_down_1 a b in
  xle (xv r) (XFin x) = true /\
  (xv r = xround_down prec emax x \/
   (fin r /\ b2r r = Ulp.pred radix2 fexp (RD emin prec x) /\ x <> 0 /\
    Rabs (RN emin prec x) < P)) /\
  (x = 0 \/ P <= Rabs (RN emin prec x) -> xv r = xround_down prec emax x).
Proof.
intros a b Fa Fb x r. unfold r, mul_down_1_ieee_listing. clear r.
generalize (two_prod_ieee_all a b Fa Fb).
destruct (IeeeModel.two_prod prec emax nan_opp nan_fma a b) as [p e].
intros [Vfin Vinf]. cbv zeta.
destruct (finite_dec prec emax p) as [Fp|Fp].
- destruct (Vfin Fp) as [Fe E].
  destruct (mul_down_1_listing_facts emin prec tie_even (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)) as [_ [L [C X]]].
  revert L C X. unfold mul_down_1_listing. rewrite <- E. cbv beta iota zeta.
  assert (Ep : b2r p = rnd x).
  { rewrite (two_prod_eq emin prec tie_even) in E. now inversion E. }
  fold x. change (RN emin prec x) with (rnd x). rewrite <- Ep.
  destruct (down_select_real a b p e Fa Fb Fp Fe) as [[Fr Er]|[Er [Lr Lp]]];
    revert Er; cbv zeta; intros Er.
  + (* the limb has the value of the real model *)
    rewrite <- Er. intros L C X.
    rewrite (xval_fin prec emax _ Fr).
    assert (Same : b2r (if orb (feq a pzero) (feq b pzero) then p
                        else if orb (flt e pzero) (andb (flt (fabs p) cP) (feq e pzero))
                             then fpred p else p) = rd x ->
                   XFin (b2r (if orb (feq a pzero) (feq b pzero) then p
                              else if orb (flt e pzero) (andb (flt (fabs p) cP) (feq e pzero))
                                   then fpred p else p)) = xround_down prec emax x).
    { intros K. rewrite K. symmetry. apply xround_down_finite. rewrite <- K.
      apply Rabs_lt_inv. apply (b2r_inrange prec emax). }
    split; [|split].
    * cbn [xle]. now apply Rle_bool_true.
    * destruct C as [C|[C [Nz Bd]]]; [left; now apply Same|right].
      split; [exact Fr|split; [exact C|split; [exact Nz|exact Bd]]].
    * intros K. apply Same. now apply X.
  + (* the limb is -infinity: the product is at or below -Omega, so at least P *)
    rewrite Er. intros L C X.
    assert (Big : P <= Rabs (b2r p)).
    { apply Rle_trans with (1 := P_le_Omega). rewrite Rabs_left1; [lra|].
      generalize (Omega_gt_0 prec emax). lra. }
    assert (K : xv ninf = xround_down prec emax x).
    { symmetry. apply xround_down_low. rewrite <- (X (or_intror Big)). exact Lr. }
    split; [reflexivity|split; [now left|intros _; exact K]].
- (* overflow *)
  destruct (Vinf Fp) as [sg [Es [Ee V]]]. subst p e.
  assert (Nz : x <> 0).
  { generalize (Omega_gt_0 prec emax). unfold x. destruct sg; lra. }
  assert (Za : feq a pzero = false).
  { rewrite (eq_finite prec emax a pzero Fa eq_refl). apply Req_bool_false.
    intros Z. apply Nz. unfold x. change (b2r pzero) with 0 in Z. rewrite Z. ring. }
  assert (Zb : feq b pzero = false).
  { rewrite (eq_finite prec emax b pzero Fb eq_refl). apply Req_bool_false.
    intros Z. apply Nz. unfold x. change (b2r pzero) with 0 in Z. rewrite Z. ring. }
  rewrite Za, Zb. cbn [orb]. rewrite down_select_inf.
  generalize (Omega_gt_0 prec emax). intros P0.
  assert (K : xv (if sg then ninf else fpred pinf) = xround_down prec emax x
              /\ xle (xv (if sg then ninf else fpred pinf)) (XFin x) = true).
  { unfold xround_down. change (omega prec emax) with Om. fold x in V. destruct sg.
    - rewrite Rlt_bool_true by exact V. split; reflexivity.
    - destruct (pred_pinf prec emax) as [Fq Eq]. rewrite (xval_fin prec emax _ Fq), Eq.
      rewrite Rlt_bool_false by lra. rewrite Rlt_bool_true by exact V.
      split; [reflexivity|]. cbn [xle]. apply Rle_bool_true. lra. }
  destruct K as [K1 K2]. split; [exact K2|split; [now left|intros _; exact K1]].
Qed.

(* mul_up_1, finite operands, likewise: the result is at least x; it is RU(x) in the
   format with overflow, or (only for a nonzero product with |RN(x)| < P) the finite
   number after RU(x); and it is RU(x) in the format with overflow when x = 0 or
   |RN(x)| >= P. An overflow upward gives +infinity, and downward -Omega. *)
Theorem mul_up_1_ieee_finite :
  forall a b : float, fin a -> fin b ->
  let x := b2r a * b2r b in
  let r := mul_up_1 a b in
  xle (XFin x) (xv r) = true /\
  (xv r = xround_up prec emax x \/
   (fin r /\ b2r r = Ulp.succ radix2 fexp (RU emin prec x) /\ x <> 0 /\
    Rabs (RN emin prec x) < P)) /\
  (x = 0 \/ P <= Rabs (RN emin prec x) -> xv r = xround_up prec emax x).
Proof.
intros a b Fa Fb x r. unfold r, mul_up_1_ieee_listing. clear r.
generalize (two_prod_ieee_all a b Fa Fb).
destruct (IeeeModel.two_prod prec emax nan_opp nan_fma a b) as [p e].
intros [Vfin Vinf]. cbv zeta.
destruct (finite_dec prec emax p) as [Fp|Fp].
- destruct (Vfin Fp) as [Fe E].
  destruct (mul_up_1_listing_facts emin prec tie_even (b2r a) (b2r b)
              (b2r_format prec emax a) (b2r_format prec emax b)) as [_ [L [C X]]].
  revert L C X. unfold mul_up_1_listing. rewrite <- E. cbv beta iota zeta.
  assert (Ep : b2r p = rnd x).
  { rewrite (two_prod_eq emin prec tie_even) in E. now inversion E. }
  fold x. change (RN emin prec x) with (rnd x). rewrite <- Ep.
  destruct (up_select_real a b p e Fa Fb Fp Fe) as [[Fr Er]|[Er [Lr Lp]]];
    revert Er; cbv zeta; intros Er.
  + rewrite <- Er. intros L C X.
    rewrite (xval_fin prec emax _ Fr).
    assert (Same : b2r (if orb (feq a pzero) (feq b pzero) then p
                        else if orb (flt pzero e) (andb (flt (fabs p) cP) (feq e pzero))
                             then fsucc p else p) = ru x ->
                   XFin (b2r (if orb (feq a pzero) (feq b pzero) then p
                              else if orb (flt pzero e) (andb (flt (fabs p) cP) (feq e pzero))
                                   then fsucc p else p)) = xround_up prec emax x).
    { intros K. rewrite K. symmetry. apply xround_up_finite. rewrite <- K.
      apply Rabs_lt_inv. apply (b2r_inrange prec emax). }
    split; [|split].
    * cbn [xle]. now apply Rle_bool_true.
    * destruct C as [C|[C [Nz Bd]]]; [left; now apply Same|right].
      split; [exact Fr|split; [exact C|split; [exact Nz|exact Bd]]].
    * intros K. apply Same. now apply X.
  + rewrite Er. intros L C X.
    assert (Big : P <= Rabs (b2r p)).
    { apply Rle_trans with (1 := P_le_Omega). rewrite Rabs_pos_eq; [lra|].
      generalize (Omega_gt_0 prec emax). lra. }
    assert (K : xv pinf = xround_up prec emax x).
    { symmetry. apply xround_up_high. rewrite <- (X (or_intror Big)). exact Lr. }
    split; [reflexivity|split; [now left|intros _; exact K]].
- destruct (Vinf Fp) as [sg [Es [Ee V]]]. subst p e.
  assert (Nz : x <> 0).
  { generalize (Omega_gt_0 prec emax). unfold x. destruct sg; lra. }
  assert (Za : feq a pzero = false).
  { rewrite (eq_finite prec emax a pzero Fa eq_refl). apply Req_bool_false.
    intros Z. apply Nz. unfold x. change (b2r pzero) with 0 in Z. rewrite Z. ring. }
  assert (Zb : feq b pzero = false).
  { rewrite (eq_finite prec emax b pzero Fb eq_refl). apply Req_bool_false.
    intros Z. apply Nz. unfold x. change (b2r pzero) with 0 in Z. rewrite Z. ring. }
  rewrite Za, Zb. cbn [orb]. rewrite up_select_inf.
  generalize (Omega_gt_0 prec emax). intros P0.
  assert (K : xv (if sg then fsucc ninf else pinf) = xround_up prec emax x
              /\ xle (XFin x) (xv (if sg then fsucc ninf else pinf)) = true).
  { unfold xround_up. change (omega prec emax) with Om. fold x in V. destruct sg.
    - destruct (succ_ninf prec emax) as [Fq Eq]. rewrite (xval_fin prec emax _ Fq), Eq.
      rewrite Rlt_bool_false by lra. rewrite Rlt_bool_true by exact V.
      split; [reflexivity|]. cbn [xle]. apply Rle_bool_true. lra.
    - rewrite Rlt_bool_true by exact V. split; reflexivity. }
  destruct K as [K1 K2]. split; [exact K2|split; [now left|intros _; exact K1]].
Qed.

(** * An operand that is not finite *)

(* mul_down_1 and mul_up_1 return the product of IEEE 754, prod a b, as it is: the
   infinity of the sign of the product, and a NaN for zero times infinity and for a NaN
   operand. *)
Theorem mul_down_1_ieee_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  mul_down_1 a b = prod a b.
Proof.
intros a b H. unfold mul_down_1_ieee_listing. generalize cP. intros c. revert H.
destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; destruct b as [sb|sb|sb pb Hb|sb mb eb Hb];
  intros [H|H]; try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  destruct c as [sc|[|]|sc pc Hc|sc mc ec Hc]; reflexivity.
Qed.

Theorem mul_up_1_ieee_nonfinite :
  forall a b : float,
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  mul_up_1 a b = prod a b.
Proof.
intros a b H. unfold mul_up_1_ieee_listing. generalize cP. intros c. revert H.
destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; destruct b as [sb|sb|sb pb Hb|sb mb eb Hb];
  intros [H|H]; try discriminate H;
  repeat match goal with s : bool |- _ => destruct s end;
  destruct c as [sc|[|]|sc pc Hc|sc mc ec Hc]; reflexivity.
Qed.

(** * mul_dir_1: the product of two bounds *)

(* mul_dir_1 returns the results of mul_down_1 and of mul_up_1, with the literal zero
   in place of both when a factor is a zero. *)
Lemma mul_dir_1_ieee_eq :
  forall a b : float,
  mul_dir_1 a b
  = (if orb (feq a pzero) (feq b pzero) then pzero else mul_down_1 a b,
     if orb (feq a pzero) (feq b pzero) then pzero else mul_up_1 a b).
Proof.
intros a b. unfold mul_dir_1_ieee_listing, mul_down_1_ieee_listing, mul_up_1_ieee_listing.
destruct (IeeeModel.two_prod prec emax nan_opp nan_fma a b) as [p e]. cbv zeta.
destruct (orb (feq a pzero) (feq b pzero)); reflexivity.
Qed.

(* For operands that are not NaN, the two outputs enclose the product of the extended
   real numbers the operands stand for, taken with 0 * infinity = 0: d <= a b <= v. *)
Theorem mul_dir_1_ieee_encloses :
  forall a b : float,
  is_nan prec emax a = false -> is_nan prec emax b = false ->
  let '(d, v) := mul_dir_1 a b in
  xle (xv d) (xmul0 (xv a) (xv b)) = true /\ xle (xmul0 (xv a) (xv b)) (xv v) = true.
Proof.
intros a b Na Nb. rewrite mul_dir_1_ieee_eq.
destruct (finite_dec prec emax a) as [Fa|Fa]; destruct (finite_dec prec emax b) as [Fb|Fb].
- (* finite operands *)
  rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb). cbn [xmul0].
  rewrite (eq_finite prec emax a pzero Fa eq_refl), (eq_finite prec emax b pzero Fb eq_refl).
  change (b2r pzero) with 0.
  destruct (mul_down_1_ieee_finite a b Fa Fb) as [D _].
  destruct (mul_up_1_ieee_finite a b Fa Fb) as [U _].
  destruct (Req_bool_spec (b2r a) 0) as [Za|Za]; cbn [orb].
  { rewrite Za, Rmult_0_l. split; apply Rle_bool_true; apply Rle_refl. }
  destruct (Req_bool_spec (b2r b) 0) as [Zb|Zb].
  { rewrite Zb, Rmult_0_r. split; apply Rle_bool_true; apply Rle_refl. }
  split; assumption.
- (* a finite, b an infinity *)
  rewrite (mul_down_1_ieee_nonfinite a b (or_intror Fb)),
          (mul_up_1_ieee_nonfinite a b (or_intror Fb)).
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb; try discriminate Nb.
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa.
  + (* a zero: the literal zero, and 0 * infinity = 0 *)
    change (xv (B754_zero prec emax sa)) with (XFin 0).
    change (xv (B754_infinity prec emax sb)) with (XInf sb). cbn [xmul0].
    rewrite Req_bool_true by reflexivity.
    replace (orb (feq (B754_zero prec emax sa) pzero) (feq (B754_infinity prec emax sb) pzero))
      with true by (destruct sa, sb; reflexivity).
    change (xv pzero) with (XFin 0). cbn [xle]. split; apply Rle_bool_true; apply Rle_refl.
  + (* a finite number that is not zero: the infinity of the sign of the product *)
    replace (orb (feq (B754_finite prec emax sa ma ea Ha) pzero)
                 (feq (B754_infinity prec emax sb) pzero))
      with false by (destruct sa, sb; reflexivity).
    change (prod (B754_finite prec emax sa ma ea Ha) (B754_infinity prec emax sb))
      with (B754_infinity prec emax (xorb sa sb)).
    rewrite (xval_fin prec emax (B754_finite prec emax sa ma ea Ha) eq_refl).
    change (xv (B754_infinity prec emax sb)) with (XInf sb).
    change (xv (B754_infinity prec emax (xorb sa sb))) with (XInf (xorb sa sb)).
    cbn [xmul0].
    assert (S : Req_bool (b2r (B754_finite prec emax sa ma ea Ha)) 0 = false /\
                Rlt_bool (b2r (B754_finite prec emax sa ma ea Ha)) 0 = sa).
    { destruct sa.
      - generalize (finite_sign_neg prec emax ma ea Ha). intros K.
        split; [apply Req_bool_false; lra|now apply Rlt_bool_true].
      - generalize (finite_sign_pos prec emax ma ea Ha). intros K.
        split; [apply Req_bool_false; lra|apply Rlt_bool_false; lra]. }
    destruct S as [S1 S2]. rewrite S1, S2. destruct (xorb sa sb); split; reflexivity.
- (* a an infinity, b finite *)
  rewrite (mul_down_1_ieee_nonfinite a b (or_introl Fa)),
          (mul_up_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; try discriminate Na.
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb.
  + change (xv (B754_zero prec emax sb)) with (XFin 0).
    change (xv (B754_infinity prec emax sa)) with (XInf sa). cbn [xmul0].
    rewrite Req_bool_true by reflexivity.
    replace (orb (feq (B754_infinity prec emax sa) pzero) (feq (B754_zero prec emax sb) pzero))
      with true by (destruct sa, sb; reflexivity).
    change (xv pzero) with (XFin 0). cbn [xle]. split; apply Rle_bool_true; apply Rle_refl.
  + replace (orb (feq (B754_infinity prec emax sa) pzero)
                 (feq (B754_finite prec emax sb mb eb Hb) pzero))
      with false by (destruct sa, sb; reflexivity).
    change (prod (B754_infinity prec emax sa) (B754_finite prec emax sb mb eb Hb))
      with (B754_infinity prec emax (xorb sa sb)).
    rewrite (xval_fin prec emax (B754_finite prec emax sb mb eb Hb) eq_refl).
    change (xv (B754_infinity prec emax sa)) with (XInf sa).
    change (xv (B754_infinity prec emax (xorb sa sb))) with (XInf (xorb sa sb)).
    cbn [xmul0].
    assert (S : Req_bool (b2r (B754_finite prec emax sb mb eb Hb)) 0 = false /\
                Rlt_bool (b2r (B754_finite prec emax sb mb eb Hb)) 0 = sb).
    { destruct sb.
      - generalize (finite_sign_neg prec emax mb eb Hb). intros K.
        split; [apply Req_bool_false; lra|now apply Rlt_bool_true].
      - generalize (finite_sign_pos prec emax mb eb Hb). intros K.
        split; [apply Req_bool_false; lra|apply Rlt_bool_false; lra]. }
    destruct S as [S1 S2]. rewrite S1, S2. destruct (xorb sa sb); split; reflexivity.
- (* two infinities *)
  rewrite (mul_down_1_ieee_nonfinite a b (or_introl Fa)),
          (mul_up_1_ieee_nonfinite a b (or_introl Fa)).
  destruct a as [sa|sa|sa pa Ha|sa ma ea Ha]; try discriminate Fa; try discriminate Na.
  destruct b as [sb|sb|sb pb Hb|sb mb eb Hb]; try discriminate Fb; try discriminate Nb.
  destruct sa, sb; split; reflexivity.
Qed.

End IeeeDirectedProd.
