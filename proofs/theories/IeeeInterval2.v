(* The sum of two intervals with bounds of two limbs, in the IEEE model, on all values:
   add_ball_2_2, add_down_2_2 and add_up_2_2 as finite cores, and interval_add_2
   (docs/developer/design/milestone2.md, "Interval kernels": "Bounds of two limbs" and
   "Two limbs").

   Notation as in IeeeInterval1.v: xval_2 is the extended real number a canonical 2-limb
   value stands for, and an interval of two limbs, its members and its emptiness are
   those of IeeeIntervalVocabulary.v. X, Y are the operands and Z the result; A and B are
   the constants of the closed form of Directed2.v (add_outward_rel, add_outward_abs).
   The four kernels are the generated models of proofs/gen/IeeeModel.v.

   What is proved, from precision 3.

   - The finite cores (add_ball_2_2_ieee_core, add_down_2_2_ieee_core,
     add_up_2_2_ieee_core), for canonical operands of any kind: if the leading limb of
     the result is finite, then every operand limb is finite, the second limb of the
     result is finite, and the result is what the real model computes
     (Model.add_down_2_2 and Model.add_up_2_2), so that the theorems of Directed2.v hold
     of it: normalized, on its side of the exact sum, zero for a sum that is zero,
     within A |v| + B. An overflow inside a core, or an infinite operand, never produces
     a finite wrong bound. The argument: a finite sum of two_sum_ord has finite operands;
     a finite directed sum has finite operands; so z0 and the bound subtracted are
     finite, and the bridges of add_2_2 and of the radius of ball_add_2 apply. The select
     of the rule of the zero sum replaces the radius d by zero only when z0 is zero, and
     then d is not needed. The second limb of the lower bound is the three lines
     nz = neg(z1); t = add_up_1(dd, nz); w = neg(t) of the generated listing, minus the
     rounding up of dd - z1: w is finite exactly when t is, and t is a directed sum whose
     first operand is nonnegative, so that its finite value is that of the real model.

   - The cores are finite within a quarter of the range (add_ball_2_2_ieee_small,
     add_down_2_2_ieee_small, add_up_2_2_ieee_small): for finite normalized operands
     whose exact sum v is at most 2^(emax - 2) in magnitude, the leading limb of each
     bound is finite. With T = 2^(emax - 2): add_2_2 returns a finite z
     (add_2_2_ieee_finite_result) with |z0| <= (5/3) T; the radius d is at most T, because
     E <= 1/8, G <= 2 and H <= T / 4 (E_add_2_le_eighth, G_3_le, H_add_le_tiny); so the
     directed sum of d and the second limb is at most (3/2) T in magnitude, and the last
     sum at most (7/2) T, which is at most the largest number of the format.

   - interval_add_2, for canonical operands (interval_add_2_correct, the generated
     statement, from interval_add_2_all):
       I1  the result Z is canonical;
       I2  Z is empty exactly when an operand is;
       I3  x + y is a member of Z for all members x of X and y of Y, unbounded operands
           included;
       I4  for bounded operands, with lo and hi the bounds of the exact range: if Z is
           bounded, lo - zl <= A |lo| + B and zu - hi <= A |hi| + B; a sum of lower
           bounds that is exactly zero gives the lower bound lo (which is zero), and a
           sum of upper bounds that is zero the upper bound hi, whatever the other bound
           does; and for nonempty operands a bound of the exact range that is infinite
           is that bound of Z;
       I5  for bounded operands, Z is bounded when every member of the exact range is at
           most 2^(emax - 2) in magnitude.
     A bound that its core does not return as a finite number is the infinity on its
     side. I1 to I3 alone are interval_add_2_enclosure.

   The difference of two intervals of two limbs is proved in IeeeIntervalSub2.v, as this sum
   on the negated operand; mul_ext_2_2 and the product in IeeeIntervalMul2.v. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Add22 Convert DirectedSum DirectedProd Directed2.
From Kairn Require Import IeeeBridge IeeeVocabulary IeeeEFT IeeeOps IeeeExt IeeeAdd22.
From Kairn Require Import IeeeFull IeeeBallCores IeeeBallFinite.
From Kairn Require Import Rectangle IeeeProduct IeeeDirected IeeeDirectedProd IeeeEntry.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

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
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation ball_add_2 := (IeeeModel.ball_add_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation add_ball_2_2 := (IeeeModel.add_ball_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation add_down_2_2 :=
  (IeeeModel.add_down_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation add_up_2_2 := (IeeeModel.add_up_2_2 prec emax nan_plus nan_minus nan_abs nan_fma).
Notation interval_add_2 :=
  (IeeeModel.interval_add_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

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

Lemma xru_fin_inv :
  forall (t : xreal) (r : R), xru prec emax t = XFin r -> exists q : R, t = XFin q.
Proof. intros [|s|q] r H; try discriminate H. now exists q. Qed.

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

(* The value of a finite directed sum one of whose operands is nonnegative: that of the
   real model. (The rounding up of the format with overflow differs from it only below
   -Omega, which a sum with a nonnegative operand cannot reach.) *)
Lemma add_up_1_value :
  (2 <= prec)%Z -> forall a b : float, fin a -> fin b -> 0 <= b2r a \/ 0 <= b2r b ->
  fin (add_up_1 a b) ->
  b2r (add_up_1 a b) = Model.add_up_1 emin prec tie_even (b2r a) (b2r b).
Proof.
intros Hp a b Fa Fb P F.
destruct (add_up_1_correct emin prec Hp (b2r a) (b2r b)
            (b2r_format prec emax a) (b2r_format prec emax b)) as [_ EM].
rewrite EM.
generalize (add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp a b).
rewrite (xval_fin prec emax _ F), (xval_fin prec emax a Fa), (xval_fin prec emax b Fb).
cbn [xadd]. rewrite (xru_real prec emax).
generalize (b2r_Omega prec emax a) (b2r_Omega prec emax b). intros Ba Bb.
destruct (Rlt_bool_spec Om (b2r a + b2r b)) as [C|C]; [intros K; discriminate K|].
rewrite Rlt_bool_false by (destruct P; lra). intros K. injection K as K. exact K.
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
rewrite <- (add_ball_2_2_eq emin prec tie_even) in E3.
unfold Model.add_ball_2_2 in E3. rewrite <- Ez in E3. cbv beta iota zeta in E3.
injection E3 as E3. exact E3.
Qed.

(* The bound that the directed sums subtract and add, dd = select(eq(z0, 0), 0, d): when
   z0 is finite and dd is finite, dd is nonnegative and is the dd of the real model. *)
Lemma dd_value :
  forall z0 d : float, fin z0 -> nonneg_ext d ->
  (fin d ->
   b2r d = rnd (rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
                * Model.up_ball_add_1_1 emin prec + Model.up_ball_add_1_2 emin prec)) ->
  fin (if feq z0 pzero then pzero else d) ->
  0 <= b2r (if feq z0 pzero then pzero else d) /\
  b2r (if feq z0 pzero then pzero else d)
  = (if Req_bool (b2r z0) 0 then 0
     else rnd (rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
               * Model.up_ball_add_1_1 emin prec + Model.up_ball_add_1_2 emin prec)).
Proof.
intros z0 d Fz0 Nd Ed. rewrite (eq_finite prec emax z0 pzero Fz0 eq_refl).
change (b2r pzero) with 0.
destruct (Req_bool (b2r z0) 0).
- intros _. split; [right; reflexivity|reflexivity].
- intros Fd. split; [exact (nonneg_ext_fin prec emax d Nd Fd)|exact (Ed Fd)].
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
  = Model.add_down_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeModel.add_down_2_2.
generalize (add_ball_2_2_ieee_core Hp x0 x1 y0 y1 Cx Cy).
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. intros Ball. cbv zeta.
set (dd := if feq z0 pzero then pzero else d).
set (t := add_up_1 dd (neg z1)).
set (w := neg t).
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
assert (Ft : fin t).
{ unfold w in Fw. now rewrite (IeeeExt.neg_finite prec emax nan_opp) in Fw. }
destruct (TF Fz0 Fw) as [Hfin _]. destruct (Hfin Fl0) as [Fl1 El].
destruct (Ball Fz0) as [F0 [F1 [G0 [G1 [Nx [Ny [Fz1 [Ez [Nd Ed]]]]]]]]].
destruct (add_up_1_fin_inv Hp2 dd (neg z1) Ft) as [Fdd Fnz].
destruct (dd_value z0 d Fz0 Nd Ed Fdd) as [Pdd Edd]. fold dd in Pdd, Edd.
assert (Et := add_up_1_value Hp2 dd (neg z1) Fdd Fnz (or_introl Pdd) Ft).
rewrite (IeeeExt.neg_value prec emax nan_opp) in Et. fold t in Et.
assert (Ew : b2r w = - Model.add_up_1 emin prec tie_even (b2r dd) (- b2r z1)).
{ unfold w. rewrite (IeeeExt.neg_value prec emax nan_opp). now rewrite Et. }
split; [exact F0|split; [exact F1|split; [exact G0|split; [exact G1|]]]].
split; [exact Nx|split; [exact Ny|split; [exact Fl1|]]].
unfold Model.add_down_2_2, Model.add_ball_2_2.
rewrite <- Ez. cbv beta iota zeta. rewrite <- Edd, <- Ew, <- El.
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
  = Model.add_up_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy. assert (Hp2 : (2 <= prec)%Z) by lia.
unfold IeeeModel.add_up_2_2.
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
destruct (dd_value z0 d Fz0 Nd Ed Fdd) as [Pdd Edd]. fold dd in Pdd, Edd.
assert (Ew := add_up_1_value Hp2 z1 dd Fz1 Fdd (or_intror Pdd) Fw).
split; [exact F0|split; [exact F1|split; [exact G0|split; [exact G1|]]]].
split; [exact Nx|split; [exact Ny|split; [exact Fh1|]]].
unfold Model.add_up_2_2, Model.add_ball_2_2.
rewrite <- Ez. cbv beta iota zeta. rewrite <- Edd. fold w in Ew. rewrite <- Ew, <- Eh.
reflexivity.
Qed.

(** * The cores are finite within a quarter of the range *)

(* The constants of the radius, from above. E is at most 1/8 (IeeeBallFinite.v has 1/2,
   which is what a radius needs to be finite; the last sum of a directed sum needs more
   room), and H, which is at most four times the smallest normal number, is at most
   2^(emax - 4). From precision 3. *)
Lemma E_add_2_le_eighth :
  (3 <= prec)%Z -> 0 <= Model.up_ball_add_2_0 emin prec <= / 8.
Proof.
intros Hp. rewrite Ball2.e_add_2_eq.
assert (Ht : 0 < u prec <= / 8) by exact (Ball2.u_bounds prec 3 Hp).
destruct Ht as [T0 T8].
assert (Q : 0 <= Ball2.uq (3 / (1 - 4 * u prec) * u prec ^ 2) * (1 + u prec) <= / 8).
{ set (t := u prec) in *.
  assert (I : 0 < / (1 - 4 * t)) by (apply Rinv_0_lt_compat; lra).
  assert (Hq : 0 <= t * t) by (apply Rmult_le_pos; lra).
  assert (Hq2 : t * t <= / 8 * / 8) by (apply Rmult_le_compat; lra).
  assert (R : 0 <= 3 / (1 - 4 * t) * t ^ 2 <= 3 / 32).
  { replace (3 / (1 - 4 * t) * t ^ 2) with (3 * (t * t) / (1 - 4 * t)) by (field; lra).
    split.
    - unfold Rdiv. apply Rmult_le_pos; lra.
    - apply Rmult_le_reg_r with (1 - 4 * t); [lra|].
      unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
  destruct R as [R0 R1]. set (rel := 3 / (1 - 4 * t) * t ^ 2) in *.
  unfold Ball2.uq.
  assert (J : 0 < / (1 - rel)) by (apply Rinv_0_lt_compat; lra).
  assert (Q0 : 0 <= rel / (1 - rel)) by (unfold Rdiv; apply Rmult_le_pos; lra).
  assert (Q1 : rel / (1 - rel) <= 3 / 29).
  { apply Rmult_le_reg_r with (1 - rel); [lra|].
    unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
  split.
  - apply Rmult_le_pos; lra.
  - apply Rle_trans with (3 / 29 * (9 / 8)); [apply Rmult_le_compat; lra|lra]. }
split.
- exact (proj1 (Ball2.RU_ge emin prec _ (proj1 Q))).
- apply (RU_le prec emax); [|exact (proj2 Q)].
  change (/ 8) with (bpow radix2 (-3)). apply (IeeeBallFinite.format_bpow prec emax). lia.
Qed.

Lemma H_add_le_tiny :
  (3 <= prec)%Z -> 0 <= Model.up_ball_add_1_2 emin prec <= bpow radix2 (emax - 4).
Proof.
intros Hp. assert (Hp2 : (2 <= prec)%Z) by lia. rewrite Ball2.h_add_1_eq.
replace ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2))
  with (Ball2.h2 emin prec 0) by (unfold Ball2.h2; ring).
assert (HV : 0 <= 0 <= 2 * eta emin).
{ generalize (bpow_gt_0 radix2 emin). unfold eta. lra. }
destruct (h2_le_6 prec emax Hp2 0 HV) as [h0 h1].
generalize (eta_le_nrm prec emax Hp2). intros EN.
assert (HH : 0 <= Ball2.h2 emin prec 0 <= 3 * Ball2.nrm emin prec) by lra.
destruct (RU_nrm_le_4 prec emax _ HH) as [R0 R1].
split; [exact R0|]. apply Rle_trans with (1 := R1). apply bpow_le. lia.
Qed.

(* 3/8 of 2^emax is a number of the format, and 7/8 of 2^emax is at most the largest
   one. *)
Lemma format_3_eighths : (2 <= prec)%Z -> format (3 * bpow radix2 (emax - 3)).
Proof.
intros Hp. apply generic_format_FLT. exists (Float radix2 3 (emax - 3)).
- reflexivity.
- apply Z.lt_le_trans with (2 := Zpower_le radix2 2 prec Hp). reflexivity.
- change (emin <= emax - 3)%Z. lia.
Qed.

Lemma Omega_ge_7_eighths : (3 <= prec)%Z -> 7 * bpow radix2 (emax - 3) <= Om.
Proof.
intros Hp. unfold Omega. rewrite (top_8 emax).
assert (bpow radix2 (emax - prec) <= bpow radix2 (emax - 3)) by (apply bpow_le; lia).
lra.
Qed.

Lemma quarter_range_eq : bpow radix2 (emax - 2) = 2 * bpow radix2 (emax - 3).
Proof. replace (emax - 2)%Z with (emax - 3 + 1)%Z by ring. apply two_bpow. Qed.

(* add_ball_2_2 on finite normalized operands whose exact sum is at most T = 2^(emax - 2)
   in magnitude: z and d are finite, |z0| <= (5/3) T, |z1| <= (5/24) T and d <= T. *)
Lemma add_ball_2_2_ieee_small :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) <= bpow radix2 (emax - 2) ->
  let '(z0, z1, d) := add_ball_2_2 x0 x1 y0 y1 in
  fin z0 /\ fin z1 /\ fin d /\
  3 * Rabs (b2r z0) <= 5 * bpow radix2 (emax - 2) /\
  24 * Rabs (b2r z1) <= 5 * bpow radix2 (emax - 2) /\
  0 <= b2r d <= bpow radix2 (emax - 2).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Cx : canonical_2 x0 x1) by (left; split; [exact F0|split; [exact F1|exact Nx]]).
assert (Cy : canonical_2 y0 y1) by (left; split; [exact G0|split; [exact G1|exact Ny]]).
assert (Hc : Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) + b2r pzero + b2r pzero
             <= bpow radix2 (emax - 2)).
{ change (b2r pzero) with 0. lra. }
generalize (ball_add_2_finite prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
              x0 x1 pzero y0 y1 pzero F0 F1 G0 G1 Nx Ny eq_refl eq_refl
              (Rle_refl 0) (Rle_refl 0) Hc)
           (add_ball_2_2_ieee_core Hp x0 x1 y0 y1 Cx Cy).
rewrite <- add_ball_2_2_ieee_eq.
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d].
intros [Fz0 Fd] Core.
destruct (Core Fz0) as [_ [_ [_ [_ [_ [_ [Fz1 [Ez [Nd Ed]]]]]]]]].
generalize (add_2_2_correct emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
rewrite <- Ez. intros [Nz Hb].
destruct (rel_add_2_quarter prec Hp) as [R0 R1].
assert (Ht : 0 < u prec <= / 8) by exact (Ball2.u_bounds prec 3 Hp).
assert (T0 : 0 < bpow radix2 (emax - 2)) by apply bpow_gt_0.
assert (V0 := Rabs_pos ((b2r x0 + b2r x1) + (b2r y0 + b2r y1))).
assert (RC : 3 / (1 - 4 * u prec) * u prec ^ 2
               * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1))
             <= / 4 * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
  by (apply Rmult_le_compat_r; lra).
assert (Hz := Rabs_le_plus_err (b2r z0 + b2r z1) ((b2r x0 + b2r x1) + (b2r y0 + b2r y1))).
assert (Hl := lead_le prec emax Hp2 _ _ Nz).
assert (A0 := Rabs_pos (b2r z0)).
assert (L0 : 3 * Rabs (b2r z0) <= 5 * bpow radix2 (emax - 2)) by lra.
assert (Tl := normalized_2_tail_rel emin prec _ _ Nz).
assert (L1 : u prec * Rabs (b2r z0) <= / 8 * Rabs (b2r z0))
  by (apply Rmult_le_compat_r; lra).
split; [exact Fz0|split; [exact Fz1|split; [exact Fd|split; [exact L0|split; [lra|]]]]].
(* the radius *)
rewrite (Ed Fd).
destruct (E_add_2_le_eighth Hp) as [E0 E1].
destruct (G_3_le prec emax Hp2) as [Gl Gu].
destruct (H_add_le_tiny Hp) as [H0 H1].
assert (B4 : bpow radix2 (emax - 4) = / 4 * bpow radix2 (emax - 2)).
{ replace (emax - 4)%Z with (-2 + (emax - 2))%Z by ring. rewrite bpow_plus. reflexivity. }
assert (Y0 : 0 <= Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec)
  by (apply Rmult_le_pos; lra).
assert (Y1 : Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec <= bpow radix2 (emax - 4)).
{ rewrite B4. apply Rle_trans with (Rabs (b2r z0) * / 8); [apply Rmult_le_compat_l; lra|lra]. }
assert (S0 : 0 <= rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0))
  by (apply (rnd_pos prec emax); lra).
assert (S1 : rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)
             <= bpow radix2 (emax - 4)).
{ apply (rnd_le_format prec emax); [|lra].
  apply (IeeeBallFinite.format_bpow prec emax). lia. }
set (s := rnd (Rabs (b2r z0) * Model.up_ball_add_2_0 emin prec + 0)) in *.
assert (K0 : 0 <= s * Model.up_ball_add_1_1 emin prec) by (apply Rmult_le_pos; lra).
assert (K1 : s * Model.up_ball_add_1_1 emin prec <= bpow radix2 (emax - 4) * 2)
  by (apply Rmult_le_compat; lra).
split.
- apply (rnd_pos prec emax). lra.
- apply (rnd_le_format prec emax); [|lra].
  apply (IeeeBallFinite.format_bpow prec emax). lia.
Qed.

(* A directed sum, rounded up, of two finite numbers whose sum is at most 3/8 of 2^emax
   in magnitude is finite and at most that in magnitude. *)
Lemma add_up_1_small :
  (3 <= prec)%Z -> forall a b : float, fin a -> fin b ->
  Rabs (b2r a + b2r b) <= 3 * bpow radix2 (emax - 3) ->
  fin (add_up_1 a b) /\ Rabs (b2r (add_up_1 a b)) <= 3 * bpow radix2 (emax - 3).
Proof.
intros Hp a b Fa Fb H. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (O7 := Omega_ge_7_eighths Hp).
assert (b0 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
apply Rabs_le_inv in H.
assert (E := add_up_1_ieee prec emax nan_plus nan_minus nan_abs Hp2 a b).
rewrite (xval_fin prec emax a Fa), (xval_fin prec emax b Fb) in E. cbn [xadd] in E.
rewrite (xru_in prec emax) in E by lra.
assert (F : fin (add_up_1 a b)) by exact (xval_fin_inv prec emax _ _ E).
split; [exact F|].
rewrite (xval_fin prec emax _ F) in E. injection E as E. rewrite E.
apply Rabs_le. split.
- apply Rle_trans with (b2r a + b2r b); [lra|].
  unfold RU. destruct (round_UP_pt radix2 fexp (b2r a + b2r b)) as [_ [L _]]. exact L.
- apply (RU_le prec emax); [exact (format_3_eighths Hp2)|lra].
Qed.

(* The last sum of a directed sum: two_sum_ord of two finite numbers whose sum is at most
   7/8 of 2^emax in magnitude has a finite sum. *)
Lemma two_sum_ord_small :
  (3 <= prec)%Z -> forall a b : float, fin a -> fin b ->
  Rabs (b2r a + b2r b) <= 7 * bpow radix2 (emax - 3) ->
  let '(s, e) := two_sum_ord a b in fin s.
Proof.
intros Hp a b Fa Fb H. assert (Hp2 : (2 <= prec)%Z) by lia.
assert (O7 := Omega_ge_7_eighths Hp). apply Rabs_le_inv in H.
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 a b Fa Fb).
destruct (two_sum_ord a b) as [s e]. intros [_ NF].
destruct (finite_dec prec emax s) as [Fs|Fs]; [exact Fs|].
exfalso. destruct (NF Fs) as [sg [_ [_ K]]]. destruct sg; lra.
Qed.

(* add_down_2_2 and add_up_2_2 on finite normalized operands whose exact sum is at most
   2^(emax - 2) in magnitude: the leading limb of the bound is finite. *)
Lemma add_down_2_2_ieee_small :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) <= bpow radix2 (emax - 2) ->
  let '(l0, l1) := add_down_2_2 x0 x1 y0 y1 in fin l0.
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv.
unfold IeeeModel.add_down_2_2.
generalize (add_ball_2_2_ieee_small Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv).
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. cbv zeta.
intros [Fz0 [Fz1 [Fd [Z0 [Z1 [D0 D1]]]]]].
assert (EB := quarter_range_eq).
assert (b0 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
set (dd := if feq z0 pzero then pzero else d).
assert (Hdd : fin dd /\ 0 <= b2r dd <= bpow radix2 (emax - 2)).
{ unfold dd. destruct (feq z0 pzero).
  - split; [reflexivity|]. change (b2r pzero) with 0. lra.
  - split; [exact Fd|split; assumption]. }
destruct Hdd as [Fdd [Dd0 Dd1]].
assert (Fnz : fin (neg z1)) by now rewrite (IeeeExt.neg_finite prec emax nan_opp).
assert (Hs : Rabs (b2r dd + b2r (neg z1)) <= 3 * bpow radix2 (emax - 3)).
{ rewrite (IeeeExt.neg_value prec emax nan_opp).
  generalize (Rabs_triang (b2r dd) (- b2r z1)).
  rewrite Rabs_Ropp, (Rabs_pos_eq (b2r dd)) by lra. lra. }
destruct (add_up_1_small Hp dd (neg z1) Fdd Fnz Hs) as [Ft Bt].
set (t := add_up_1 dd (neg z1)) in *.
assert (Fw : fin (neg t)) by now rewrite (IeeeExt.neg_finite prec emax nan_opp).
assert (K : Rabs (b2r z0 + b2r (neg t)) <= 7 * bpow radix2 (emax - 3)).
{ rewrite (IeeeExt.neg_value prec emax nan_opp).
  generalize (Rabs_triang (b2r z0) (- b2r t)). rewrite Rabs_Ropp. lra. }
generalize (two_sum_ord_small Hp z0 (neg t) Fz0 Fw K).
destruct (two_sum_ord z0 (neg t)) as [l0 l1]. intros Q. exact Q.
Qed.

Lemma add_up_2_2_ieee_small :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) <= bpow radix2 (emax - 2) ->
  let '(h0, h1) := add_up_2_2 x0 x1 y0 y1 in fin h0.
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv.
unfold IeeeModel.add_up_2_2.
generalize (add_ball_2_2_ieee_small Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv).
destruct (add_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. cbv zeta.
intros [Fz0 [Fz1 [Fd [Z0 [Z1 [D0 D1]]]]]].
assert (EB := quarter_range_eq).
assert (b0 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
set (dd := if feq z0 pzero then pzero else d).
assert (Hdd : fin dd /\ 0 <= b2r dd <= bpow radix2 (emax - 2)).
{ unfold dd. destruct (feq z0 pzero).
  - split; [reflexivity|]. change (b2r pzero) with 0. lra.
  - split; [exact Fd|split; assumption]. }
destruct Hdd as [Fdd [Dd0 Dd1]].
assert (Hs : Rabs (b2r z1 + b2r dd) <= 3 * bpow radix2 (emax - 3)).
{ generalize (Rabs_triang (b2r z1) (b2r dd)). rewrite (Rabs_pos_eq (b2r dd)) by lra. lra. }
destruct (add_up_1_small Hp z1 dd Fz1 Fdd Hs) as [Fw Bw].
set (w := add_up_1 z1 dd) in *.
assert (K : Rabs (b2r z0 + b2r w) <= 7 * bpow radix2 (emax - 3)).
{ generalize (Rabs_triang (b2r z0) (b2r w)). lra. }
generalize (two_sum_ord_small Hp z0 w Fz0 Fw K).
destruct (two_sum_ord z0 w) as [h0 h1]. intros Q. exact Q.
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

(* A bounded canonical interval is not empty. *)
Lemma bounded_nonempty_2 :
  forall l0 l1 h0 h1 : float,
  interval_2 l0 l1 h0 h1 -> interval_bounded_2 l0 l1 h0 h1 -> interval_nonempty_2 l0 l1 h0 h1.
Proof.
intros l0 l1 h0 h1 [[E _]|N] [F _]; trivial. rewrite E in F. discriminate F.
Qed.

(* The last lines of interval_add_2, shared by the kernels of two limbs: with (a, b) the
   bounds computed for nonempty operands, canonical and containing x o y for all members,
   the result is canonical (I1), empty exactly when an operand is (I2), contains x o y
   for all members of the operands (I3), and is (a, b) for nonempty operands. *)
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
  zu0 = (if andb (flt xl0 pinf) (flt yl0 pinf) then b0 else ninf) ->
  zu1 = (if andb (flt xl0 pinf) (flt yl0 pinf) then b1 else pzero) ->
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (op x y)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   zl0 = a0 /\ zl1 = a1 /\ zu0 = b0 /\ zu1 = b1).
Proof.
intros op xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 a0 a1 b0 b1 CX CY Core zl0 zl1 zu0 zu1 E0 E1 E2 E3.
rewrite 2!(lt_pinf_xval prec emax) in E0, E1, E2, E3.
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
  split.
  - intros x y Hx _. elim (NoMem _ _ _ _ x EX Hx).
  - intros N _. elim (NotEmpty _ _ _ _ N EX). }
destruct CY as [EY|NY].
{ destruct (Empty (or_intror EY)) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  split; [left; exact EmptyZ|].
  split; [split; [intros _; right; exact EY|intros _; exact EmptyZ]|].
  split.
  - intros x y _ Hy. elim (NoMem _ _ _ _ y EY Hy).
  - intros _ N. elim (NotEmpty _ _ _ _ N EY). }
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
split; [right; exact NZ|split; [|split; [exact I3|intros _ _; repeat split]]].
split.
- intros E. elim (NotEmpty _ _ _ _ NZ E).
- intros [E|E]; [elim (NotEmpty _ _ _ _ NX E)|elim (NotEmpty _ _ _ _ NY E)].
Qed.

(** * interval_add_2 *)

(* What the listing returns, with the two cores named. *)
Lemma interval_add_2_eq :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_add_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
  = (let l := add_down_2_2 xl0 xl1 yl0 yl1 in
     let h := add_up_2_2 xu0 xu1 yu0 yu1 in
     let ne := andb (flt xl0 pinf) (flt yl0 pinf) in
     (if ne then (if flt (fabs (fst l)) pinf then fst l else neg pinf) else pinf,
      if ne then (if flt (fabs (fst l)) pinf then snd l else pzero) else pzero,
      if ne then (if flt (fabs (fst h)) pinf then fst h else pinf) else neg pinf,
      if ne then (if flt (fabs (fst h)) pinf then snd h else pzero) else pzero)).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1. unfold IeeeModel.interval_add_2.
destruct (add_down_2_2 xl0 xl1 yl0 yl1) as [l0 l1].
destruct (add_up_2_2 xu0 xu1 yu0 yu1) as [h0 h1]. reflexivity.
Qed.

(* The bounds computed for nonempty operands: the result of each core when its leading
   limb is finite, the infinity on its side otherwise. They are canonical and enclose
   x + y for all members of the operands. *)
Lemma interval_add_2_core :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
  let l := add_down_2_2 xl0 xl1 yl0 yl1 in
  let h := add_up_2_2 xu0 xu1 yu0 yu1 in
  canonical_2 (if is_finite prec emax (fst l) then fst l else ninf)
              (if is_finite prec emax (fst l) then snd l else pzero) /\
  canonical_2 (if is_finite prec emax (fst h) then fst h else pinf)
              (if is_finite prec emax (fst h) then snd h else pzero) /\
  forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
  in_interval_2 (if is_finite prec emax (fst l) then fst l else ninf)
                (if is_finite prec emax (fst l) then snd l else pzero)
                (if is_finite prec emax (fst h) then fst h else pinf)
                (if is_finite prec emax (fst h) then snd h else pzero) (x + y).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 [CXl [CXu NX]] [CYl [CYu NY]]. cbv zeta.
generalize (add_down_2_2_ieee_core Hp xl0 xl1 yl0 yl1 CXl CYl)
           (add_up_2_2_ieee_core Hp xu0 xu1 yu0 yu1 CXu CYu).
destruct (add_down_2_2 xl0 xl1 yl0 yl1) as [l0 l1].
destruct (add_up_2_2 xu0 xu1 yu0 yu1) as [h0 h1].
intros DL DH. cbn [fst snd].
assert (L : canonical_2 (if is_finite prec emax l0 then l0 else ninf)
                        (if is_finite prec emax l0 then l1 else pzero) /\
            forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
            xle (xv2 (if is_finite prec emax l0 then l0 else ninf)
                     (if is_finite prec emax l0 then l1 else pzero)) (XFin (x + y)) = true).
{ destruct (is_finite prec emax l0) eqn:Fl; cbv beta iota.
  - destruct (DL eq_refl) as [F0 [F1 [G0 [G1 [Nx [Ny [Fl1 El]]]]]]].
    generalize (add_down_2_2_outward emin prec Hp (b2r xl0) (b2r xl1)
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
  - destruct (DH eq_refl) as [F0 [F1 [G0 [G1 [Nx [Ny [Fh1 Eh]]]]]]].
    generalize (add_up_2_2_outward emin prec Hp (b2r xu0) (b2r xu1)
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

(* interval_add_2, for canonical operands X and Y, from precision 3. I1: the result Z is
   canonical. I2: Z is empty exactly when an operand is. I3: x + y is a member of Z for
   all members x of X and y of Y, unbounded operands included. *)
Theorem interval_add_2_enclosure :
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
assert (Core := interval_add_2_core Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1).
cbv zeta in Core.
rewrite interval_add_2_eq. cbv beta iota zeta.
rewrite 2!(lt_abs_pinf prec emax nan_abs). change (neg pinf) with ninf.
destruct (interval_tail_2 (fun x y : R => x + y) xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 _ _ _ _
            CX CY Core _ _ _ _ eq_refl eq_refl eq_refl eq_refl) as [I1 [I2 [I3 _]]].
exact (conj I1 (conj I2 I3)).
Qed.

(* The bounds of the exact range of the sum of two nonempty intervals of two limbs are
   the sums of the bounds, as extended real numbers. *)
Lemma range_add_2_lower :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
  forall lo : xreal,
  range_lower (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                 (in_interval_2 yl0 yl1 yu0 yu1)) lo ->
  lo = xadd (xv2 xl0 xl1) (xv2 yl0 yl1).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 [_ [_ NX]] [_ [_ NY]] lo Hlo.
destruct (xnonempty_member _ _ NX) as [mx Mx]. destruct (xnonempty_member _ _ NY) as [my My].
assert (Ex : exists z : R,
             range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
               (in_interval_2 yl0 yl1 yu0 yu1) z).
{ exists (mx + my), mx, my. exact (conj Mx (conj My eq_refl)). }
exact (range_lower_unique _ _ _ Ex Hlo
         (range_add_lower (xv2 xl0 xl1) (xv2 xu0 xu1) (xv2 yl0 yl1) (xv2 yu0 yu1) NX NY)).
Qed.

Lemma range_add_2_upper :
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
  forall hi : xreal,
  range_upper (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                 (in_interval_2 yl0 yl1 yu0 yu1)) hi ->
  hi = xadd (xv2 xu0 xu1) (xv2 yu0 yu1).
Proof.
intros xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 [_ [_ NX]] [_ [_ NY]] hi Hhi.
destruct (xnonempty_member _ _ NX) as [mx Mx]. destruct (xnonempty_member _ _ NY) as [my My].
assert (Ex : exists z : R,
             range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
               (in_interval_2 yl0 yl1 yu0 yu1) z).
{ exists (mx + my), mx, my. exact (conj Mx (conj My eq_refl)). }
exact (range_upper_unique _ _ _ Ex Hhi
         (range_add_upper (xv2 xl0 xl1) (xv2 xu0 xu1) (xv2 yl0 yl1) (xv2 yu0 yu1) NX NY)).
Qed.

(* interval_add_2, for canonical operands X and Y, from precision 3: I1 to I5 as the
   generated statement has them, with the constants of the closed form by name
   (add_outward_rel and add_outward_abs of Directed2.v). I4: for bounded operands, with
   lo and hi the bounds of the exact range, a bounded Z has lo - zl <= A |lo| + B and
   zu - hi <= A |hi| + B, and a sum of lower (upper) bounds that is zero gives the lower
   (upper) bound lo (hi); for nonempty operands, an infinite bound of the exact range is
   that bound of Z. I5: for bounded operands, Z is bounded when every member of the
   exact range is at most 2^(emax - 2) in magnitude. *)
Theorem interval_add_2_all :
  (3 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  let '(zl0, zl1, zu0, zu1) := interval_add_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (x + y)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   forall lo hi : R,
   range_lower (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin lo) ->
   range_upper (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin hi) ->
   (interval_bounded_2 zl0 zl1 zu0 zu1 ->
    lo - (b2r zl0 + b2r zl1) <= add_outward_rel emin prec * Rabs lo + add_outward_abs emin prec /\
    (b2r zu0 + b2r zu1) - hi <= add_outward_rel emin prec * Rabs hi + add_outward_abs emin prec) /\
   (((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1)) = 0 -> xval_2 zl0 zl1 = XFin lo) /\
   (((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1)) = 0 -> xval_2 zu0 zu1 = XFin hi)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (range_lower (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf true) ->
    xval_2 zl0 zl1 = XInf true) /\
   (range_upper (range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf false) ->
    xval_2 zu0 zu1 = XInf false)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   (forall z : R,
    range_2 (fun x y : R => x + y) (in_interval_2 xl0 xl1 xu0 xu1)
      (in_interval_2 yl0 yl1 yu0 yu1) z ->
    Rabs z <= bpow radix2 (emax - 2)) ->
   interval_bounded_2 zl0 zl1 zu0 zu1).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
assert (Core := interval_add_2_core Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1).
cbv zeta in Core.
rewrite interval_add_2_eq. cbv beta iota zeta.
rewrite 2!(lt_abs_pinf prec emax nan_abs). change (neg pinf) with ninf.
destruct (interval_tail_2 (fun x y : R => x + y) xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 _ _ _ _
            CX CY Core _ _ _ _ eq_refl eq_refl eq_refl eq_refl) as [I1 [I2 [I3 EQ]]].
split; [exact I1|split; [exact I2|split; [exact I3|]]].
(* The facts about the cores, on the two pairs they return. *)
generalize (add_down_2_2_ieee_core Hp xl0 xl1 yl0 yl1)
           (add_up_2_2_ieee_core Hp xu0 xu1 yu0 yu1)
           (add_down_2_2_ieee_small Hp xl0 xl1 yl0 yl1)
           (add_up_2_2_ieee_small Hp xu0 xu1 yu0 yu1)
           (add_down_2_2_outward emin prec Hp (b2r xl0) (b2r xl1) (b2r yl0) (b2r yl1))
           (add_up_2_2_outward emin prec Hp (b2r xu0) (b2r xu1) (b2r yu0) (b2r yu1)).
revert EQ. clear I1 I2 I3 Core.
destruct (add_down_2_2 xl0 xl1 yl0 yl1) as [l0 l1].
destruct (add_up_2_2 xu0 xu1 yu0 yu1) as [h0 h1]. cbn [fst snd].
intros EQ DL DH SL SH OL OH.
(* What a bounded operand is. *)
assert (Bounded : forall a0 a1 b0 b1 : float,
          interval_2 a0 a1 b0 b1 -> interval_bounded_2 a0 a1 b0 b1 ->
          interval_nonempty_2 a0 a1 b0 b1 /\
          (fin a0 /\ fin a1 /\ normalized_2 emin prec (b2r a0) (b2r a1)) /\
          (fin b0 /\ fin b1 /\ normalized_2 emin prec (b2r b0) (b2r b1)) /\
          xv2 a0 a1 = XFin (b2r a0 + b2r a1) /\ xv2 b0 b1 = XFin (b2r b0 + b2r b1)).
{ intros a0 a1 b0 b1 C B. assert (N := bounded_nonempty_2 a0 a1 b0 b1 C B).
  destruct B as [Fa Fb]. destruct N as [Ca [Cb N]].
  destruct (canonical_2_finite prec emax a0 a1 Ca Fa) as [Fa1 Na].
  destruct (canonical_2_finite prec emax b0 b1 Cb Fb) as [Fb1 Nb].
  split; [exact (conj Ca (conj Cb N))|].
  split; [exact (conj Fa (conj Fa1 Na))|split; [exact (conj Fb (conj Fb1 Nb))|]].
  split; [exact (xval_2_fin a0 a1 Fa)|exact (xval_2_fin b0 b1 Fb)]. }
(* A bound of the result that is finite is the pair of its core, and the core's facts. *)
assert (Lower : fin l0 -> canonical_2 xl0 xl1 -> canonical_2 yl0 yl1 ->
          forall Nx : normalized_2 emin prec (b2r xl0) (b2r xl1),
          forall Ny : normalized_2 emin prec (b2r yl0) (b2r yl1),
          (b2r l0 + b2r l1) <= ((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1)) /\
          Rabs ((b2r l0 + b2r l1) - ((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1)))
          <= add_outward_rel emin prec * Rabs ((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1))
             + add_outward_abs emin prec /\
          (((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1)) = 0 ->
           (b2r l0 + b2r l1) = ((b2r xl0 + b2r xl1) + (b2r yl0 + b2r yl1)))).
{ intros Fl Cx Cy Nx Ny.
  destruct (DL Cx Cy Fl) as [_ [_ [_ [_ [_ [_ [_ El]]]]]]].
  generalize (OL Nx Ny). rewrite <- El. intros [_ K]. exact K. }
assert (Upper : fin h0 -> canonical_2 xu0 xu1 -> canonical_2 yu0 yu1 ->
          forall Nx : normalized_2 emin prec (b2r xu0) (b2r xu1),
          forall Ny : normalized_2 emin prec (b2r yu0) (b2r yu1),
          ((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1)) <= (b2r h0 + b2r h1) /\
          Rabs ((b2r h0 + b2r h1) - ((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1)))
          <= add_outward_rel emin prec * Rabs ((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1))
             + add_outward_abs emin prec /\
          (((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1)) = 0 ->
           (b2r h0 + b2r h1) = ((b2r xu0 + b2r xu1) + (b2r yu0 + b2r yu1)))).
{ intros Fh Cx Cy Nx Ny.
  destruct (DH Cx Cy Fh) as [_ [_ [_ [_ [_ [_ [_ Eh]]]]]]].
  generalize (OH Nx Ny). rewrite <- Eh. intros [_ K]. exact K. }
split; [|split].
- (* I4, bounded operands *)
  intros BX BY lo hi Hlo Hhi.
  destruct (Bounded _ _ _ _ CX BX) as [NX [[Fxl0 [Fxl1 Nxl]] [[Fxu0 [Fxu1 Nxh]] [Exl Exu]]]].
  destruct (Bounded _ _ _ _ CY BY) as [NY [[Fyl0 [Fyl1 Nyl]] [[Fyu0 [Fyu1 Nyh]] [Eyl Eyu]]]].
  destruct (EQ NX NY) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  assert (Elo := range_add_2_lower _ _ _ _ _ _ _ _ NX NY _ Hlo).
  assert (Ehi := range_add_2_upper _ _ _ _ _ _ _ _ NX NY _ Hhi).
  rewrite Exl, Eyl in Elo. rewrite Exu, Eyu in Ehi. cbn [xadd] in Elo, Ehi.
  injection Elo as Elo. injection Ehi as Ehi.
  destruct NX as [CXl [CXu _]]. destruct NY as [CYl [CYu _]].
  split; [|split].
  + intros [Fzl Fzu].
    assert (Fl : fin l0).
    { destruct (finite_dec prec emax l0) as [F|F]; [exact F|].
      exfalso. rewrite F in Fzl. exact (Bool.diff_false_true Fzl). }
    assert (Fh : fin h0).
    { destruct (finite_dec prec emax h0) as [F|F]; [exact F|].
      exfalso. rewrite F in Fzu. exact (Bool.diff_false_true Fzu). }
    rewrite Fl, Fh. cbv beta iota.
    destruct (Lower Fl CXl CYl Nxl Nyl) as [Lv [TightL _]].
    destruct (Upper Fh CXu CYu Nxh Nyh) as [Hv [TightH _]].
    rewrite Elo, Ehi.
    rewrite Rabs_left1 in TightL by lra. rewrite Rabs_pos_eq in TightH by lra.
    split; lra.
  + intros V0.
    assert (Fl : fin l0).
    { apply (SL Fxl0 Fxl1 Fyl0 Fyl1 Nxl Nyl). rewrite V0, Rabs_R0. apply bpow_ge_0. }
    rewrite Fl. cbv beta iota.
    destruct (Lower Fl CXl CYl Nxl Nyl) as [_ [_ Zero]].
    rewrite (xval_2_fin l0 l1 Fl), Elo. f_equal. exact (Zero V0).
  + intros V0.
    assert (Fh : fin h0).
    { apply (SH Fxu0 Fxu1 Fyu0 Fyu1 Nxh Nyh). rewrite V0, Rabs_R0. apply bpow_ge_0. }
    rewrite Fh. cbv beta iota.
    destruct (Upper Fh CXu CYu Nxh Nyh) as [_ [_ Zero]].
    rewrite (xval_2_fin h0 h1 Fh), Ehi. f_equal. exact (Zero V0).
- (* an infinite bound of the exact range *)
  intros NX NY.
  destruct (EQ NX NY) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  assert (CXl := proj1 NX). assert (CXu := proj1 (proj2 NX)).
  assert (CYl := proj1 NY). assert (CYu := proj1 (proj2 NY)).
  split.
  + intros Hlo. assert (Elo := range_add_2_lower _ _ _ _ _ _ _ _ NX NY _ Hlo).
    destruct (finite_dec prec emax l0) as [Fl|Fl]; rewrite Fl; cbv beta iota; [exfalso|reflexivity].
    destruct (DL CXl CYl Fl) as [F0 [_ [G0 _]]].
    rewrite (xval_2_fin xl0 xl1 F0), (xval_2_fin yl0 yl1 G0) in Elo. discriminate Elo.
  + intros Hhi. assert (Ehi := range_add_2_upper _ _ _ _ _ _ _ _ NX NY _ Hhi).
    destruct (finite_dec prec emax h0) as [Fh|Fh]; rewrite Fh; cbv beta iota; [exfalso|reflexivity].
    destruct (DH CXu CYu Fh) as [F0 [_ [G0 _]]].
    rewrite (xval_2_fin xu0 xu1 F0), (xval_2_fin yu0 yu1 G0) in Ehi. discriminate Ehi.
- (* I5 *)
  intros BX BY W.
  destruct (Bounded _ _ _ _ CX BX) as [NX [[Fxl0 [Fxl1 Nxl]] [[Fxu0 [Fxu1 Nxh]] [Exl Exu]]]].
  destruct (Bounded _ _ _ _ CY BY) as [NY [[Fyl0 [Fyl1 Nyl]] [[Fyu0 [Fyu1 Nyh]] [Eyl Eyu]]]].
  destruct (EQ NX NY) as [Z0 [Z1 [Z2 Z3]]]. rewrite Z0, Z1, Z2, Z3.
  assert (NXv := proj2 (proj2 NX)). assert (NYv := proj2 (proj2 NY)).
  assert (Mxl : in_interval_2 xl0 xl1 xu0 xu1 (b2r xl0 + b2r xl1)).
  { unfold in_interval_2. rewrite Exl in NXv |- *. now apply xmember_lower. }
  assert (Mxu : in_interval_2 xl0 xl1 xu0 xu1 (b2r xu0 + b2r xu1)).
  { unfold in_interval_2. rewrite Exu in NXv |- *. now apply xmember_upper. }
  assert (Myl : in_interval_2 yl0 yl1 yu0 yu1 (b2r yl0 + b2r yl1)).
  { unfold in_interval_2. rewrite Eyl in NYv |- *. now apply xmember_lower. }
  assert (Myu : in_interval_2 yl0 yl1 yu0 yu1 (b2r yu0 + b2r yu1)).
  { unfold in_interval_2. rewrite Eyu in NYv |- *. now apply xmember_upper. }
  assert (Fl : fin l0).
  { apply (SL Fxl0 Fxl1 Fyl0 Fyl1 Nxl Nyl). apply W.
    exists (b2r xl0 + b2r xl1), (b2r yl0 + b2r yl1). exact (conj Mxl (conj Myl eq_refl)). }
  assert (Fh : fin h0).
  { apply (SH Fxu0 Fxu1 Fyu0 Fyu1 Nxh Nyh). apply W.
    exists (b2r xu0 + b2r xu1), (b2r yu0 + b2r yu1). exact (conj Mxu (conj Myu eq_refl)). }
  rewrite Fl, Fh. split; assumption.
Qed.

End IeeeInterval2.

(** * The generated statement *)

(* interval_add_2: the generated statement, which prints the constants A and B of the
   closed form unfolded, is interval_add_2_all. *)
Theorem interval_add_2_correct : interval_add_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp
       xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
exact (interval_add_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
         xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY).
Qed.
