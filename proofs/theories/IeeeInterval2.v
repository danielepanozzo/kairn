(* The sum of two intervals with bounds of two limbs, in the IEEE model, on all values:
   add_ball_2_2, add_down_2_2 and add_up_2_2 as finite cores, and interval_add_2
   (docs/developer/design/milestone2.md, "Interval kernels": "Bounds of two limbs" and
   "Two limbs").

   Notation as in IeeeInterval1.v: xval_2 is the extended real number a canonical 2-limb
   value stands for, and an interval of two limbs, its members and its emptiness are
   those of IeeeIntervalVocabulary.v. X, Y are the operands and Z the result.

   What is proved, from precision 3.

   - The finite cores (add_ball_2_2_ieee_core, add_down_2_2_ieee_core,
     add_up_2_2_ieee_core), for canonical operands of any kind: if the leading limb of
     the result is finite, then every operand limb is finite, the second limb of the
     result is finite, and the result is what the real model computes
     (Directed2.add_down_2_2_listing and add_up_2_2_listing), so that the theorems of
     Directed2.v hold of it: normalized, on its side of the exact sum, zero for a sum
     that is zero, within A |v| + B. An overflow inside a core, or an infinite operand,
     never produces a finite wrong bound. The argument: a finite sum of two_sum_ord has
     finite operands; a finite directed sum has finite operands; so z0 and the bound
     subtracted are finite, and the bridges of add_2_2 and of the radius of ball_add_2
     apply. The select of the rule of the zero sum replaces the radius d by zero only
     when z0 is zero, and then d is not needed.

   - interval_add_2, for canonical operands (interval_add_2_correct): I1 the result Z is
     canonical; I2 Z is empty exactly when an operand is; I3 x + y is a member of Z for
     all members x of X and y of Y, unbounded operands included. A bound that its core
     does not return as a finite number is the infinity on its side.

   What is not proved here: I4 and I5 for interval_add_2 (the tightness A |v| + B of a
   bounded result follows from the cores and Directed2.v but is not stated for the
   interval; the condition under which the result is bounded is not proved); the
   difference, mul_ext_2_2 and the product.

   The listings. The four kernels are not generated yet: add_ball_2_2_ieee_listing and
   the others, in section Listings, are their listings written by hand in the text the
   generator prints for the IEEE model (checked against the generator's printer on the
   kernel descriptions), and the generated IeeeModel.add_ball_2_2 and the others will
   replace them. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Convert DirectedSum DirectedProd Directed2.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt IeeeAdd22.
From Kairn Require Import IeeeFull IeeeBallCores.
From Kairn Require Import Rectangle IeeeProduct IeeeDirected IeeeDirectedProd IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * The listings *)

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
Variable nan_fma : float -> float -> float -> nan_of.

Local Notation pzero := (IeeeOperations.pzero prec emax).
Local Notation pinf := (IeeeOperations.pinf prec emax).
Local Notation neg := (IeeeOperations.neg prec emax nan_opp).
Local Notation abs := (IeeeOperations.abs prec emax nan_abs).
Local Notation fma := (IeeeOperations.fma prec emax nan_fma).
Local Notation prod := (IeeeOperations.prod prec emax nan_fma).
Local Notation lt := (IeeeOperations.lt prec emax).
Local Notation eq := (IeeeOperations.eq prec emax).
Local Notation add_2_2 := (IeeeModel.add_2_2 prec emax nan_plus nan_minus).
Local Notation two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Local Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Local Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
(* The constants E, G, H of ball_add_2, under the names the generator gives them when
   add_ball_2_2 is the first kernel that uses E. *)
Local Notation up_add_ball_2_2_0 := (IeeeModel.up_ball_add_2_0 prec emax).
Local Notation up_ball_add_1_1 := (IeeeModel.up_ball_add_1_1 prec emax).
Local Notation up_ball_add_1_2 := (IeeeModel.up_ball_add_1_2 prec emax).

(* Hand-written IEEE models of the listings, in the text the generator prints for the
   IEEE model. The kernels are not generated yet; the generated IeeeModel.add_ball_2_2,
   add_down_2_2, add_up_2_2 and interval_add_2 will replace these definitions. *)
Definition add_ball_2_2_ieee_listing (x0 x1 y0 y1 : float) : float * float * float :=
  let '(z0, z1) := add_2_2 x0 x1 y0 y1 in
  let az := abs z0 in
  let t := prod az up_add_ball_2_2_0 in
  let d := fma t up_ball_add_1_1 up_ball_add_1_2 in
  (z0, z1, d).

Local Notation add_ball_2_2 := add_ball_2_2_ieee_listing.

Definition add_down_2_2_ieee_listing (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1, d) := add_ball_2_2 x0 x1 y0 y1 in
  let zd := eq z0 pzero in
  let dd := if zd then pzero else d in
  let w := sub_down_1 z1 dd in
  let '(l0, l1) := two_sum_ord z0 w in
  (l0, l1).

Definition add_up_2_2_ieee_listing (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1, d) := add_ball_2_2 x0 x1 y0 y1 in
  let zd := eq z0 pzero in
  let dd := if zd then pzero else d in
  let w := add_up_1 z1 dd in
  let '(h0, h1) := two_sum_ord z0 w in
  (h0, h1).

Local Notation add_down_2_2 := add_down_2_2_ieee_listing.
Local Notation add_up_2_2 := add_up_2_2_ieee_listing.

Definition interval_add_2_listing (xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float) : float * float * float * float :=
  let '(l0, l1) := add_down_2_2 xl0 xl1 yl0 yl1 in
  let '(h0, h1) := add_up_2_2 xu0 xu1 yu0 yu1 in
  let al := abs l0 in
  let fl := lt al pinf in
  let ah := abs h0 in
  let fh := lt ah pinf in
  let mi := neg pinf in
  let a0 := if fl then l0 else mi in
  let a1 := if fl then l1 else pzero in
  let b0 := if fh then h0 else pinf in
  let b1 := if fh then h1 else pzero in
  let nx := lt xl0 pinf in
  let ny := lt yl0 pinf in
  let ne := andb nx ny in
  let zl0 := if ne then a0 else pinf in
  let zl1 := if ne then a1 else pzero in
  let zu0 := if ne then b0 else mi in
  let zu1 := if ne then b1 else pzero in
  (zl0, zl1, zu0, zu1).

End Listings.

Section IeeeInterval2.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation add_2_2 := (IeeeModel.add_2_2 prec emax nan_plus nan_minus).
Notation two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Notation sub_down_1 := (IeeeModel.sub_down_1 prec emax nan_plus nan_minus nan_opp nan_abs).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation ball_add_2 := (IeeeModel.ball_add_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation add_ball_2_2 := (add_ball_2_2_ieee_listing prec emax nan_plus nan_minus nan_abs nan_fma).
Notation add_down_2_2 :=
  (add_down_2_2_ieee_listing prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation add_up_2_2 := (add_up_2_2_ieee_listing prec emax nan_plus nan_minus nan_abs nan_fma).
Notation interval_add_2 :=
  (interval_add_2_listing prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

(** * A finite directed sum has finite operands *)

(* A sum of IEEE 754 with an operand that is not finite is not a real number. *)
Lemma xadd_not_fin :
  forall (a b : float) (r : R),
  is_finite prec emax a = false \/ is_finite prec emax b = false ->
  xadd (xv a) (xv b) <> XFin r.
Proof.
intros a b r H.
destruct (xval_cases prec emax a) as [[Fa Ea]|[[sa Ea]|Ea]];
destruct (xval_cases prec emax b) as [[Fb Eb]|[[sb Eb]|Eb]]; rewrite Ea, Eb;
  try (exfalso; destruct H; congruence); cbn; try discriminate;
  destruct (Bool.eqb sa sb); discriminate.
Qed.

Lemma xrd_fin_inv :
  forall (t : xreal) (r : R), xrd prec emax t = XFin r -> exists q : R, t = XFin q.
Proof. intros [|s|q] r H; try discriminate H. now exists q. Qed.

Lemma xru_fin_inv :
  forall (t : xreal) (r : R), xru prec emax t = XFin r -> exists q : R, t = XFin q.
Proof. intros [|s|q] r H; try discriminate H. now exists q. Qed.

Lemma sub_down_1_fin_inv :
  (2 <= prec)%Z -> forall a b : float, fin (sub_down_1 a b) -> fin a /\ fin b.
Proof.
intros Hp a b F.
generalize (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp a b).
rewrite (xval_fin prec emax _ F), <- (xval_neg prec emax nan_opp b). intros E.
destruct (xrd_fin_inv _ _ (eq_sym E)) as [q Eq].
destruct (is_finite prec emax a) eqn:Fa; [destruct (is_finite prec emax b) eqn:Fb; [now split|]|].
- exfalso. apply (xadd_not_fin a (neg b) q); [right|exact Eq].
  now rewrite (IeeeExt.neg_finite prec emax nan_opp).
- exfalso. apply (xadd_not_fin a (neg b) q); [now left|exact Eq].
Qed.

Lemma add_up_1_fin_inv :
  (2 <= prec)%Z -> forall a b : float, fin (add_up_1 a b) -> fin a /\ fin b.
Proof.
intros Hp a b F.
generalize (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
rewrite (xval_fin prec emax _ F). intros E.
destruct (xru_fin_inv _ _ (eq_sym E)) as [q Eq].
destruct (is_finite prec emax a) eqn:Fa; [destruct (is_finite prec emax b) eqn:Fb; [now split|]|].
- exfalso. apply (xadd_not_fin a b q); [now right|exact Eq].
- exfalso. apply (xadd_not_fin a b q); [now left|exact Eq].
Qed.

(* The value of a finite directed sum whose second operand is nonnegative: that of the
   real model. (The rounding of the format with overflow differs from it only beyond
   Omega on the side that a nonnegative second operand cannot reach.) *)
Lemma sub_down_1_value :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> 0 <= b2r b ->
  fin (sub_down_1 a b) ->
  b2r (sub_down_1 a b) = Model.sub_down_1 emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp a b Fa Fb Pb F.
destruct (sub_down_1_correct emin prec Hp (b2r a) (b2r b)
            (b2r_format prec emax a) (b2r_format prec emax b)) as [_ EM].
rewrite EM.
generalize (sub_down_1_ieee prec emax nan_plus nan_minus nan_opp nan_abs Hp a b).
rewrite (xval_fin prec emax _ F), (xval_fin prec emax a Fa), (xval_fin prec emax b Fb).
cbn [xopp xadd]. rewrite (xrd_real prec emax).
generalize (b2r_Omega prec emax a). intros Ba.
destruct (Rlt_bool_spec (b2r a + - b2r b) (- Om)) as [C|C]; [intros K; discriminate K|].
rewrite Rlt_bool_false by lra. intros K. injection K as K. exact K.
Qed.

Lemma add_up_1_value :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> 0 <= b2r b ->
  fin (add_up_1 a b) ->
  b2r (add_up_1 a b) = Model.add_up_1 emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp a b Fa Fb Pb F.
destruct (add_up_1_correct emin prec Hp (b2r a) (b2r b)
            (b2r_format prec emax a) (b2r_format prec emax b)) as [_ EM].
rewrite EM.
generalize (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
rewrite (xval_fin prec emax _ F), (xval_fin prec emax a Fa), (xval_fin prec emax b Fb).
cbn [xadd]. rewrite (xru_real prec emax).
generalize (b2r_Omega prec emax a). intros Ba.
destruct (Rlt_bool_spec Om (b2r a + b2r b)) as [C|C]; [intros K; discriminate K|].
rewrite Rlt_bool_false by lra. intros K. injection K as K. exact K.
Qed.

(** * The finite cores *)

(* add_ball_2_2 is ball_add_2 with radii zero, in the IEEE model as in the real one. *)
Lemma add_ball_2_2_ieee_eq :
  forall x0 x1 y0 y1 : float,
  add_ball_2_2 x0 x1 y0 y1 = ball_add_2 x0 x1 pzero y0 y1 pzero.
Proof. reflexivity. Qed.

(* add_ball_2_2, for canonical operands of any kind: if z0 is finite then every operand
   limb is finite, the operands are normalized, z1 is finite, (z0, z1) is what add_2_2
   of the real model computes, d is nonnegative, +infinity or NaN, and a finite d is the
   radius that the real model computes. *)
Lemma add_ball_2_2_ieee_core :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(z0, z1, d) := add_ball_2_2 x0 x1 y0 y1 in
  fin z0 ->
  fin x0 /\ fin x1 /\ fin y0 /\ fin y1 /\
  normalized_2 emin prec (b2r x0) (b2r x1) /\ normalized_2 emin prec (b2r y0) (b2r y1) /\
  fin z1 /\
  (b2r z0, b2r z1) = Model.add_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1) /\
  nonneg_ext d /\
  (fin d ->
   b2r d = rnd (rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
                * Model.up_ball_add_1_1 emin prec + Model.up_ball_add_1_2 emin prec)).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. rewrite add_ball_2_2_ieee_eq.
assert (Zn : nonneg_ext pzero) by (right; right; split; [reflexivity|right; reflexivity]).
generalize (add_2_2_core prec emax nan_plus nan_minus nan_opp nan_fma Hp x0 x1 y0 y1).
generalize (fun F0 F1 G0 G1 Nx Ny =>
              ball_add_2_core prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
                x0 x1 pzero y0 y1 pzero F0 F1 G0 G1 Nx Ny Zn Zn).
generalize (fun F0 F1 G0 G1 Nx Ny =>
              add_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp
                x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
unfold IeeeModel.ball_add_2.
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1].
cbv beta iota zeta. intros V B [Cone _] Fz0.
destruct (Cone Fz0) as [F0 G0].
destruct (canonical_2_finite prec emax x0 x1 Cx F0) as [F1 Nx].
destruct (canonical_2_finite prec emax y0 y1 Cy G0) as [G1 Ny].
destruct (V F0 F1 G0 G1 Nx Ny Fz0) as [Fz1 Ez].
destruct (B F0 F1 G0 G1 Nx Ny) as [Nd Ed].
split; [exact F0|split; [exact F1|split; [exact G0|split; [exact G1|]]]].
split; [exact Nx|split; [exact Ny|split; [exact Fz1|split; [exact Ez|split; [exact Nd|]]]]].
intros Fd. destruct (Ed Fz0 Fd) as [_ [_ [_ E3]]].
change (b2r pzero) with 0 in E3.
rewrite <- (add_ball_2_2_listing_eq emin prec tie_even) in E3.
unfold add_ball_2_2_listing in E3. rewrite <- Ez in E3. cbv beta iota zeta in E3.
injection E3 as E3. exact E3.
Qed.

(* add_down_2_2, for canonical operands of any kind: if l0 is finite then every operand
   limb is finite, the operands are normalized, l1 is finite, and (l0, l1) is what the
   real model computes. *)
Lemma add_down_2_2_ieee_core :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(l0, l1) := add_down_2_2 x0 x1 y0 y1 in
  fin l0 ->
  fin x0 /\ fin x1 /\ fin y0 /\ fin y1 /\
  normalized_2 emin prec (b2r x0) (b2r x1) /\ normalized_2 emin prec (b2r y0) (b2r y1) /\
  fin l1 /\
  (b2r l0, b2r l1)
  = add_down_2_2_listing emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold add_down_2_2_ieee_listing.
generalize (add_ball_2_2_ieee_core Hp x0 x1 y0 y1 Cx Cy).
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. intros Ball. cbv zeta.
set (dd := if feq z0 pzero then pzero else d).
set (w := sub_down_1 z1 dd).
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 z0 w)
           (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs z0 w).
destruct (two_sum_ord z0 w) as [l0 l1]. intros TF TN Fl0.
assert (NF : ~ (is_finite prec emax z0 = false \/ is_finite prec emax w = false)).
{ intros K. destruct (TN K) as [E _]. rewrite (xval_fin prec emax l0 Fl0) in E.
  exact (xadd_not_fin z0 w _ K (eq_sym E)). }
assert (Fz0 : fin z0).
{ destruct (is_finite prec emax z0) eqn:F; trivial. elim NF. now left. }
assert (Fw : fin w).
{ destruct (is_finite prec emax w) eqn:F; trivial. elim NF. now right. }
destruct (TF Fz0 Fw) as [Hfin _]. destruct (Hfin Fl0) as [Fl1 El].
destruct (Ball Fz0) as [F0 [F1 [G0 [G1 [Nx [Ny [Fz1 [Ez [Nd Ed]]]]]]]]].
destruct (sub_down_1_fin_inv Hp2 z1 dd Fw) as [_ Fdd].
assert (Edd : 0 <= b2r dd /\
              b2r dd = (if Req_bool (b2r z0) 0 then 0
                        else rnd (rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
                                  * Model.up_ball_add_1_1 emin prec
                                  + Model.up_ball_add_1_2 emin prec))).
{ revert Fdd. unfold dd. rewrite (eq_finite prec emax z0 pzero Fz0 eq_refl).
  change (b2r pzero) with 0.
  destruct (Req_bool (b2r z0) 0).
  - intros _. split; [right; reflexivity|reflexivity].
  - intros Fd. split; [exact (nonneg_ext_fin prec emax d Nd Fd)|exact (Ed Fd)]. }
destruct Edd as [Pdd Edd].
assert (Ew := sub_down_1_value Hp2 z1 dd Fz1 Fdd Pdd Fw).
split; [exact F0|split; [exact F1|split; [exact G0|split; [exact G1|]]]].
split; [exact Nx|split; [exact Ny|split; [exact Fl1|]]].
unfold add_down_2_2_listing, add_ball_2_2_listing.
rewrite <- Ez. cbv beta iota zeta. rewrite <- Edd. fold w in Ew. rewrite <- Ew, <- El.
reflexivity.
Qed.

(* add_up_2_2, likewise. *)
Lemma add_up_2_2_ieee_core :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(h0, h1) := add_up_2_2 x0 x1 y0 y1 in
  fin h0 ->
  fin x0 /\ fin x1 /\ fin y0 /\ fin y1 /\
  normalized_2 emin prec (b2r x0) (b2r x1) /\ normalized_2 emin prec (b2r y0) (b2r y1) /\
  fin h1 /\
  (b2r h0, b2r h1)
  = add_up_2_2_listing emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold add_up_2_2_ieee_listing.
generalize (add_ball_2_2_ieee_core Hp x0 x1 y0 y1 Cx Cy).
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. intros Ball. cbv zeta.
set (dd := if feq z0 pzero then pzero else d).
set (w := add_up_1 z1 dd).
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 z0 w)
           (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs z0 w).
destruct (two_sum_ord z0 w) as [h0 h1]. intros TF TN Fh0.
assert (NF : ~ (is_finite prec emax z0 = false \/ is_finite prec emax w = false)).
{ intros K. destruct (TN K) as [E _]. rewrite (xval_fin prec emax h0 Fh0) in E.
  exact (xadd_not_fin z0 w _ K (eq_sym E)). }
assert (Fz0 : fin z0).
{ destruct (is_finite prec emax z0) eqn:F; trivial. elim NF. now left. }
assert (Fw : fin w).
{ destruct (is_finite prec emax w) eqn:F; trivial. elim NF. now right. }
destruct (TF Fz0 Fw) as [Hfin _]. destruct (Hfin Fh0) as [Fh1 Eh].
destruct (Ball Fz0) as [F0 [F1 [G0 [G1 [Nx [Ny [Fz1 [Ez [Nd Ed]]]]]]]]].
destruct (add_up_1_fin_inv Hp2 z1 dd Fw) as [_ Fdd].
assert (Edd : 0 <= b2r dd /\
              b2r dd = (if Req_bool (b2r z0) 0 then 0
                        else rnd (rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
                                  * Model.up_ball_add_1_1 emin prec
                                  + Model.up_ball_add_1_2 emin prec))).
{ revert Fdd. unfold dd. rewrite (eq_finite prec emax z0 pzero Fz0 eq_refl).
  change (b2r pzero) with 0.
  destruct (Req_bool (b2r z0) 0).
  - intros _. split; [right; reflexivity|reflexivity].
  - intros Fd. split; [exact (nonneg_ext_fin prec emax d Nd Fd)|exact (Ed Fd)]. }
destruct Edd as [Pdd Edd].
assert (Ew := add_up_1_value Hp2 z1 dd Fz1 Fdd Pdd Fw).
split; [exact F0|split; [exact F1|split; [exact G0|split; [exact G1|]]]].
split; [exact Nx|split; [exact Ny|split; [exact Fh1|]]].
unfold add_up_2_2_listing, add_ball_2_2_listing.
rewrite <- Ez. cbv beta iota zeta. rewrite <- Edd. fold w in Ew. rewrite <- Ew, <- Eh.
reflexivity.
Qed.

(** * Canonical 2-limb values and intervals *)

Lemma xval_2_fin : forall x0 x1 : float, fin x0 -> xv2 x0 x1 = XFin (b2r x0 + b2r x1).
Proof. intros x0 x1 F. unfold xval_2. now rewrite F. Qed.

Lemma xval_2_lead :
  forall x0 x1 : float, is_finite prec emax x0 = false -> xv2 x0 x1 = xv x0.
Proof. intros x0 x1 F. unfold xval_2, xval. now rewrite F. Qed.

Lemma xlt_xval_2_pinf :
  forall x0 x1 : float, xlt (xv2 x0 x1) (XInf false) = xlt (xv x0) (XInf false).
Proof.
intros x0 x1. destruct (is_finite prec emax x0) eqn:F.
- rewrite (xval_2_fin x0 x1 F), (xval_fin prec emax x0 F). reflexivity.
- now rewrite (xval_2_lead x0 x1 F).
Qed.

(* The last lines of interval_add_2, shared by the kernels of two limbs: with (a, b) the
   bounds computed for nonempty operands, canonical and containing x o y for all members,
   the result is canonical (I1), empty exactly when an operand is (I2), and contains
   x o y for all members of the operands (I3). *)
Lemma interval_tail_2 :
  forall (op : R -> R -> R) (xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 a0 a1 b0 b1 : float),
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   canonical_2 a0 a1 /\ canonical_2 b0 b1 /\
   forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 a0 a1 b0 b1 (op x y)) ->
  forall zl0 zl1 zu0 zu1 : float,
  zl0 = (if andb (flt xl0 pinf) (flt yl0 pinf) then a0 else pinf) ->
  zl1 = (if andb (flt xl0 pinf) (flt yl0 pinf) then a1 else pzero) ->
  zu0 = (if andb (flt xl0 pinf) (flt yl0 pinf) then b0 else neg pinf) ->
  zu1 = (if andb (flt xl0 pinf) (flt yl0 pinf) then b1 else pzero) ->
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (op x y)).
Proof.
intros op xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 a0 a1 b0 b1 CX CY Core zl0 zl1 zu0 zu1 E0 E1 E2 E3.
rewrite 2!(lt_pinf_xval prec emax) in E0, E1, E2, E3.
rewrite (neg_pinf prec emax nan_opp) in E2.
assert (EmptyZ : interval_empty_2 pinf pzero ninf pzero).
{ split; [reflexivity|split; [exists false; reflexivity|split; [reflexivity|]]].
  exists false; reflexivity. }
assert (NoMem : forall (l0 l1 h0 h1 : float) (x : R),
                interval_empty_2 l0 l1 h0 h1 -> ~ in_interval_2 l0 l1 h0 h1 x).
{ intros l0 l1 h0 h1 x [E _] [H _]. rewrite E in H. discriminate H. }
assert (NotEmpty : forall l0 l1 h0 h1 : float,
                   interval_nonempty_2 l0 l1 h0 h1 -> ~ interval_empty_2 l0 l1 h0 h1).
{ intros l0 l1 h0 h1 [_ [_ N]] E. destruct (xnonempty_member _ _ N) as [x Hx].
  exact (NoMem l0 l1 h0 h1 x E Hx). }
assert (Inf : xlt (xv (infinity prec emax false)) (XInf false) = false) by reflexivity.
assert (Empty : interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1 ->
                zl0 = pinf /\ zl1 = pzero /\ zu0 = ninf /\ zu1 = pzero).
{ intros [[E _]|[E _]]; rewrite E, Inf in E0, E1, E2, E3;
    rewrite ?andb_false_r in E0, E1, E2, E3; cbn [andb] in E0, E1, E2, E3;
    exact (conj E0 (conj E1 (conj E2 E3))). }
destruct CX as [EX|NX].
{ destruct (Empty (or_introl EX)) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  split; [left; exact EmptyZ|].
  split; [split; [intros _; left; exact EX|intros _; exact EmptyZ]|].
  intros x y Hx _. elim (NoMem _ _ _ _ x EX Hx). }
destruct CY as [EY|NY].
{ destruct (Empty (or_intror EY)) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  split; [left; exact EmptyZ|].
  split; [split; [intros _; right; exact EY|intros _; exact EmptyZ]|].
  intros x y _ Hy. elim (NoMem _ _ _ _ y EY Hy). }
assert (NX2 : xlt (xv xl0) (XInf false) = true).
{ rewrite <- (xlt_xval_2_pinf xl0 xl1). exact (proj1 (proj2 (proj2 (proj2 NX)))). }
assert (NY2 : xlt (xv yl0) (XInf false) = true).
{ rewrite <- (xlt_xval_2_pinf yl0 yl1). exact (proj1 (proj2 (proj2 (proj2 NY)))). }
rewrite NX2, NY2 in E0, E1, E2, E3. cbn [andb] in E0, E1, E2, E3.
rewrite E0, E1, E2, E3.
destruct (Core NX NY) as [Ca [Cb I3]].
destruct (xnonempty_member _ _ (proj2 (proj2 NX))) as [mx Mx].
destruct (xnonempty_member _ _ (proj2 (proj2 NY))) as [my My].
assert (NZ : interval_nonempty_2 a0 a1 b0 b1).
{ split; [exact Ca|split; [exact Cb|]]. exact (xmember_nonempty _ _ _ (I3 mx my Mx My)). }
split; [right; exact NZ|split; [|exact I3]].
split.
- intros E. elim (NotEmpty _ _ _ _ NZ E).
- intros [E|E]; [elim (NotEmpty _ _ _ _ NX E)|elim (NotEmpty _ _ _ _ NY E)].
Qed.

(** * interval_add_2 *)

(* interval_add_2, for canonical operands X and Y, from precision 3. I1: the result Z is
   canonical. I2: Z is empty exactly when an operand is. I3: x + y is a member of Z for
   all members x of X and y of Y, unbounded operands included. *)
Theorem interval_add_2_correct :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  let '(zl0, zl1, zu0, zu1) := interval_add_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (x + y)).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
unfold interval_add_2_listing.
generalize (add_down_2_2_ieee_core Hp xl0 xl1 yl0 yl1)
           (add_up_2_2_ieee_core Hp xu0 xu1 yu0 yu1).
destruct (add_down_2_2 xl0 xl1 yl0 yl1) as [l0 l1].
destruct (add_up_2_2 xu0 xu1 yu0 yu1) as [h0 h1].
intros DL DH. cbv beta iota zeta.
apply (interval_tail_2 (fun x y : R => x + y) xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
         (if flt (fabs l0) pinf then l0 else neg pinf)
         (if flt (fabs l0) pinf then l1 else pzero)
         (if flt (fabs h0) pinf then h0 else pinf)
         (if flt (fabs h0) pinf then h1 else pzero) CX CY);
  [|reflexivity|reflexivity|reflexivity|reflexivity].
intros [CXl [CXu NX]] [CYl [CYu NY]].
rewrite 2!(lt_abs_pinf prec emax nan_abs). rewrite (neg_pinf prec emax nan_opp).
assert (L : canonical_2 (if is_finite prec emax l0 then l0 else ninf)
                        (if is_finite prec emax l0 then l1 else pzero) /\
            forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
            xle (xv2 (if is_finite prec emax l0 then l0 else ninf)
                     (if is_finite prec emax l0 then l1 else pzero)) (XFin (x + y)) = true).
{ destruct (is_finite prec emax l0) eqn:Fl; cbv beta iota.
  - destruct (DL CXl CYl eq_refl) as [F0 [F1 [G0 [G1 [Nx [Ny [Fl1 El]]]]]]].
    generalize (add_down_2_2_listing_correct emin prec Hp (b2r xl0) (b2r xl1)
                  (b2r yl0) (b2r yl1) Nx Ny).
    rewrite <- El. intros [Nl [Lv _]].
    split.
    + left. split; [exact Fl|split; [exact Fl1|exact Nl]].
    + intros x y [Hx _] [Hy _].
      rewrite (xval_2_fin xl0 xl1 F0) in Hx. rewrite (xval_2_fin yl0 yl1 G0) in Hy.
      rewrite (xval_2_fin l0 l1 Fl).
      cbn [xle] in Hx, Hy |- *. apply Rle_bool_inv in Hx. apply Rle_bool_inv in Hy.
      apply Rle_bool_true. lra.
  - split.
    + right. left. split; [exists true; reflexivity|exists false; reflexivity].
    + intros x y _ _. reflexivity. }
assert (U : canonical_2 (if is_finite prec emax h0 then h0 else pinf)
                        (if is_finite prec emax h0 then h1 else pzero) /\
            forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
            xle (XFin (x + y))
                (xv2 (if is_finite prec emax h0 then h0 else pinf)
                     (if is_finite prec emax h0 then h1 else pzero)) = true).
{ destruct (is_finite prec emax h0) eqn:Fh; cbv beta iota.
  - destruct (DH CXu CYu eq_refl) as [F0 [F1 [G0 [G1 [Nx [Ny [Fh1 Eh]]]]]]].
    generalize (add_up_2_2_listing_correct emin prec Hp (b2r xu0) (b2r xu1)
                  (b2r yu0) (b2r yu1) Nx Ny).
    rewrite <- Eh. intros [Nh [Hv _]].
    split.
    + left. split; [exact Fh|split; [exact Fh1|exact Nh]].
    + intros x y [_ Hx] [_ Hy].
      rewrite (xval_2_fin xu0 xu1 F0) in Hx. rewrite (xval_2_fin yu0 yu1 G0) in Hy.
      rewrite (xval_2_fin h0 h1 Fh).
      cbn [xle] in Hx, Hy |- *. apply Rle_bool_inv in Hx. apply Rle_bool_inv in Hy.
      apply Rle_bool_true. lra.
  - split.
    + right. left. split; [exists false; reflexivity|exists false; reflexivity].
    + intros x y _ _. reflexivity. }
destruct L as [Ca L]. destruct U as [Cb U].
split; [exact Ca|split; [exact Cb|]].
intros x y Hx Hy. split; [exact (L x y Hx Hy)|exact (U x y Hx Hy)].
Qed.

End IeeeInterval2.
