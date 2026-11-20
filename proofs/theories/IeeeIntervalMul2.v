(* The product of two intervals with bounds of two limbs, in the IEEE model, on all values:
   mul_dir_2_2 as a finite core, mul_ext_2_2 and interval_mul_2
   (docs/developer/design/milestone2.md, "Interval kernels": "Bounds of two limbs" and "Two
   limbs").

   Notation as in IeeeInterval2.v: xval_2 is the extended real number a canonical 2-limb
   value stands for; an interval of two limbs, its members and its emptiness are those of
   IeeeIntervalVocabulary.v; xmul0 is the product of extended real numbers with
   0 * infinity = 0 (Rectangle.v). A and B are the constants of the closed form of the
   directed product (mul_outward_rel and mul_outward_abs of Directed2.v). The kernels are the
   generated models of proofs/gen/IeeeModel.v. From precision 4.

   What is proved.

   - The finite core (mul_dir_2_2_ieee_core): for finite normalized operands, a finite
     leading limb of either bound comes with a finite second limb, and the bound is what the
     real model computes (Model.mul_dir_2_2), so that the theorems of Directed2.v hold of it:
     normalized, on its side of x y, within A |x y| + B. And the core is finite within a
     quarter of the range (mul_dir_2_2_ieee_small): for |x y| <= 2^(emax - 2) both leading
     limbs are finite. The radius of mul_ball_2_2 is then at most 2^(emax - 2), because its
     constant E is at most 1/8 from precision 4 (E_mul_2_le_eighth).

   - mul_ext_2_2, for canonical operands that are not NaN (mul_ext_2_2_correct, the
     generated statement, from mul_ext_2_2_all): both outputs are canonical; a zero factor
     gives zero; otherwise neither output is a NaN, an infinite operand gives the product
     of IEEE 754 (an infinity) as both outputs, and finite operands give a lower and an upper
     bound of x y, normalized when finite, within A |x y| + B of it; a bound that the core
     does not return as a finite number is the infinity on its side.

   - interval_mul_2, for canonical operands (interval_mul_2_correct, from
     interval_mul_2_all):
       I1  the result Z is canonical;
       I2  Z is empty exactly when an operand is;
       I3  x y is a member of Z for all members x of X and y of Y, unbounded operands
           included;
       I4  for bounded operands, with lo and hi the bounds of the exact range: if Z is
           bounded, lo - zl <= A |lo| + B and zu - hi <= A |hi| + B; and for nonempty
           operands an infinite bound of the exact range is that bound of Z;
       Z0  for nonempty operands, one of which is [0, 0], Z is [0, 0], limb by limb;
       I5  for bounded operands, Z is bounded when every member of the exact range is at
           most 2^(emax - 2) in magnitude.

   The proofs. mul_ext_2_2 is taken in four cases: a zero factor, an infinite factor
   (xval_prod_nonfinite of IeeeDirectedProd.v, and the leading limb of a canonical value
   that is not zero has the sign of the value), and finite factors (the core). What
   interval_mul_2 needs of each of the four products of bounds is collected in `corner`: the
   lower output is at most, and the upper one at least, the product of the bounds taken with
   0 * infinity = 0; finite outputs are within A |p| + B of the product p. The rectangle
   lemma (Rectangle.v) then gives I3, and I4 holds because v -> v - A |v| does not decrease
   for A <= 1 (min_tight): the least of four values each within A |p_k| + B of its product
   p_k is within A |lo| + B of the least product lo. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Mul22 Directed2 IeeeBridge IeeeVocabulary IeeeEFT.
From Kairn Require Import IeeeOps IeeeExt IeeeMul22 IeeeFull IeeeMake IeeeBallCores IeeeBallFinite.
From Kairn Require Import Rectangle IeeeDirected IeeeDirectedProd.
From Kairn Require Import IeeeIntervalVocabulary IeeeInterval1 IeeeInterval2 IeeeIntervalExact.
From Kairn Require Ball2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

(** * Real numbers: the bound of a least and of a greatest value *)

(* v -> v - A |v| does not decrease, for 0 <= A <= 1. *)
Lemma below_mono :
  forall A p q : R, 0 <= A <= 1 -> q <= p -> q - A * Rabs q <= p - A * Rabs p.
Proof.
intros A p q [A0 A1] H.
assert (T : Rabs p - Rabs q <= p - q).
{ generalize (Rabs_triang_inv p q). rewrite (Rabs_pos_eq (p - q)) by lra. lra. }
assert (K1 : A * (Rabs p - Rabs q) <= A * (p - q)) by (apply Rmult_le_compat_l; lra).
assert (K2 : A * (p - q) <= 1 * (p - q)) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(* A value within A |p| + B below p, for a p at least lo, is within A |lo| + B below lo;
   and above. *)
Lemma min_tight :
  forall A B lo l p : R, 0 <= A <= 1 -> lo <= p -> p - l <= A * Rabs p + B ->
  lo - l <= A * Rabs lo + B.
Proof. intros A B lo l p HA H1 H2. generalize (below_mono A p lo HA H1). lra. Qed.

Lemma max_tight :
  forall A B hi w p : R, 0 <= A <= 1 -> p <= hi -> w - p <= A * Rabs p + B ->
  w - hi <= A * Rabs hi + B.
Proof.
intros A B hi w p HA H1 H2.
generalize (below_mono A (- p) (- hi) HA ltac:(lra)). rewrite 2!Rabs_Ropp. lra.
Qed.

(** * Extended real numbers *)

Lemma xle_ninf : forall v : xreal, xle v (XInf true) = true -> v = XInf true.
Proof. intros [|[|]|r]; cbn; intros H; try discriminate H; reflexivity. Qed.

Lemma xle_pinf : forall v : xreal, xle (XInf false) v = true -> v = XInf false.
Proof. intros [|[|]|r]; cbn; intros H; try discriminate H; reflexivity. Qed.

Lemma xmin4_mono :
  forall v1 v2 v3 v4 m1 m2 m3 m4 : xreal,
  xle v1 m1 = true -> xle v2 m2 = true -> xle v3 m3 = true -> xle v4 m4 = true ->
  xle (xmin (xmin v1 v2) (xmin v3 v4)) (xmin (xmin m1 m2) (xmin m3 m4)) = true.
Proof.
intros v1 v2 v3 v4 m1 m2 m3 m4 H1 H2 H3 H4.
destruct (xmin4_le_each v1 v2 v3 v4 (xle_refl_l _ _ H1) (xle_refl_l _ _ H2)
            (xle_refl_l _ _ H3) (xle_refl_l _ _ H4)) as [D1 [D2 [D3 D4]]].
destruct (xmin4_cases m1 m2 m3 m4) as [E|[E|[E|E]]]; rewrite E.
- exact (xle_trans _ _ _ D1 H1).
- exact (xle_trans _ _ _ D2 H2).
- exact (xle_trans _ _ _ D3 H3).
- exact (xle_trans _ _ _ D4 H4).
Qed.

Lemma xmax4_mono :
  forall v1 v2 v3 v4 m1 m2 m3 m4 : xreal,
  xle m1 v1 = true -> xle m2 v2 = true -> xle m3 v3 = true -> xle m4 v4 = true ->
  xle (xmax (xmax m1 m2) (xmax m3 m4)) (xmax (xmax v1 v2) (xmax v3 v4)) = true.
Proof.
intros v1 v2 v3 v4 m1 m2 m3 m4 H1 H2 H3 H4.
destruct (xmax4_ge_each v1 v2 v3 v4 (xle_refl_r _ _ H1) (xle_refl_r _ _ H2)
            (xle_refl_r _ _ H3) (xle_refl_r _ _ H4)) as [D1 [D2 [D3 D4]]].
destruct (xmax4_cases m1 m2 m3 m4) as [E|[E|[E|E]]]; rewrite E.
- exact (xle_trans _ _ _ H1 D1).
- exact (xle_trans _ _ _ H2 D2).
- exact (xle_trans _ _ _ H3 D3).
- exact (xle_trans _ _ _ H4 D4).
Qed.

(* xmul0 and xmul agree when neither operand is zero. *)
Lemma xmul0_xmul :
  forall a b : xreal, a <> XFin 0 -> b <> XFin 0 -> xmul0 a b = xmul a b.
Proof.
intros [|sa|ra] [|sb|rb] Ha Hb; try reflexivity; cbn [xmul0 xmul].
- rewrite Req_bool_false; [reflexivity|]. intros E. apply Hb. now rewrite E.
- rewrite Req_bool_false; [reflexivity|]. intros E. apply Ha. now rewrite E.
Qed.

(* A zero times a value that is not a NaN is zero, with 0 * infinity = 0. *)
Lemma xmul0_zero_l :
  forall b : xreal, b <> XNaN -> xmul0 (XFin 0) b = XFin 0.
Proof.
intros [|s|r] H; [elim H; reflexivity| |].
- cbn [xmul0]. now rewrite Req_bool_true.
- cbn [xmul0]. now rewrite Rmult_0_l.
Qed.

Lemma xmul0_zero_r :
  forall a : xreal, a <> XNaN -> xmul0 a (XFin 0) = XFin 0.
Proof. intros a H. rewrite xmul0_comm. now apply xmul0_zero_l. Qed.

Lemma xle_refl_nn : forall v : xreal, v <> XNaN -> xle v v = true.
Proof.
intros [|[|]|r] H; [elim H; reflexivity|reflexivity|reflexivity|].
cbn. apply Rle_bool_true. apply Rle_refl.
Qed.

Section IeeeIntervalMul2.
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
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation ninf := (B754_infinity prec emax true).
Notation xv := (@xval prec emax).
Notation xv2 := (@xval_2 prec emax).
Notation Om := (Omega prec emax).
Notation two_sum_ord := (IeeeModel.two_sum_ord prec emax nan_plus nan_minus nan_abs).
Notation add_up_1 := (IeeeModel.add_up_1 prec emax nan_plus nan_minus nan_abs).
Notation mul_ball_2_2 :=
  (IeeeModel.mul_ball_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation mul_dir_2_2 :=
  (IeeeModel.mul_dir_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation mul_ext_2_2 :=
  (IeeeModel.mul_ext_2_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation interval_mul_2 :=
  (IeeeModel.interval_mul_2 prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).
Notation lt_2_2 := (IeeeModel.lt_2_2 prec emax).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The constants *)

(* E, the factor of the leading limb in the radius, is at most 1/8 from precision 4. *)
Lemma E_mul_2_le_eighth : (4 <= prec)%Z -> 0 <= Model.up_ball_mul_2_0 emin prec <= / 8.
Proof.
intros Hp. rewrite Ball2.e_mul_2_eq.
assert (Ut : 0 < u prec <= / 16) by exact (Ball2.u_bounds prec 4 Hp). destruct Ut as [U0 U1].
assert (R : 0 <= 4 * u prec ^ 2 <= / 64).
{ replace (u prec ^ 2) with (u prec * u prec) by ring.
  assert (Q : u prec * u prec <= / 16 * / 16) by (apply Rmult_le_compat; lra).
  split; [apply Rmult_le_pos; [lra|apply Rmult_le_pos; lra]|lra]. }
assert (Q : 0 <= Ball2.uq (4 * u prec ^ 2) <= / 8).
{ unfold Ball2.uq. destruct R as [R0 R1].
  assert (I : 0 < / (1 - 4 * u prec ^ 2)) by (apply Rinv_0_lt_compat; lra).
  split.
  - unfold Rdiv. apply Rmult_le_pos; lra.
  - apply Rmult_le_reg_r with (1 - 4 * u prec ^ 2); [lra|].
    unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra. }
split.
- exact (proj1 (Ball2.RU_ge emin prec _ (proj1 Q))).
- apply (RU_le prec emax); [|exact (proj2 Q)].
  change (/ 8) with (bpow radix2 (-3)). apply (IeeeBallFinite.format_bpow prec emax). lia.
Qed.

(* A <= 1 and B >= 0. *)
Lemma mul_rel_bounds : (4 <= prec)%Z -> 0 <= mul_outward_rel emin prec <= 1.
Proof.
intros Hp.
destruct (E_mul_2_le_eighth Hp) as [E0 E1].
destruct (G_6_le prec emax Hp) as [G0 G1].
assert (Ut : 0 < u prec <= / 16) by exact (Ball2.u_bounds prec 4 Hp). destruct Ut as [U0 U1].
unfold mul_outward_rel, outward_rel.
set (t := u prec) in *. set (E := Model.up_ball_mul_2_0 emin prec) in *.
set (G := Model.up_ball_mul_2_1 emin prec) in *.
assert (P3 : 1 <= (1 + t) ^ 3 <= 2).
{ replace ((1 + t) ^ 3) with ((1 + t) * ((1 + t) * (1 + t))) by ring.
  assert (S : (1 + t) * (1 + t) <= 17 / 16 * (17 / 16)) by (apply Rmult_le_compat; lra).
  assert (S' : 1 <= (1 + t) * (1 + t)) by nra.
  split; [nra|]. apply Rle_trans with (17 / 16 * (17 / 16 * (17 / 16))); [apply Rmult_le_compat; nra|lra]. }
assert (T2 : 0 <= t ^ 2 <= / 256).
{ replace (t ^ 2) with (t * t) by ring.
  split; [apply Rmult_le_pos; lra|]. apply Rle_trans with (/ 16 * / 16); [apply Rmult_le_compat; lra|lra]. }
assert (A1 : 0 <= 2 * (1 + t) ^ 3 * G <= 4 * (3 / 2))
  by (split; [apply Rmult_le_pos; lra|apply Rmult_le_compat; lra]).
assert (A2 : 0 <= 2 * (1 + t) ^ 3 * G * E <= 4 * (3 / 2) * / 8)
  by (split; [apply Rmult_le_pos; lra|apply Rmult_le_compat; lra]).
set (N := 2 * (1 + t) ^ 3 * G * E + 2 * t ^ 2).
assert (QN : 0 <= N <= 97 / 128) by (unfold N; lra).
assert (I0 : 0 < / (1 - t)) by (apply Rinv_0_lt_compat; lra).
assert (I1 : / (1 - t) <= 16 / 15).
{ apply Rmult_le_reg_r with (1 - t); [lra|]. rewrite Rinv_l by lra. lra. }
assert (K1 : 0 <= N * (1 + 4 * t ^ 2) <= 97 / 128 * (65 / 64))
  by (split; [apply Rmult_le_pos; lra|apply Rmult_le_compat; lra]).
assert (K2 : N * (1 + 4 * t ^ 2) * / (1 - t) <= 97 / 128 * (65 / 64) * (16 / 15))
  by (apply Rmult_le_compat; lra).
unfold Rdiv. split; [apply Rmult_le_pos; lra|lra].
Qed.

Lemma mul_abs_ge_0 : (4 <= prec)%Z -> 0 <= mul_outward_abs emin prec.
Proof.
intros Hp.
destruct (E_mul_2_le_eighth Hp) as [E0 _]. destruct (G_6_le prec emax Hp) as [G0 _].
destruct (H_mul_2_le prec emax Hp) as [H0 _].
assert (Ut : 0 < u prec <= / 16) by exact (Ball2.u_bounds prec 4 Hp). destruct Ut as [U0 U1].
assert (e0 : 0 < eta emin) by apply bpow_gt_0.
unfold mul_outward_abs, outward_abs.
set (t := u prec) in *.
assert (I0 : 0 <= / (1 - t)) by (apply Rlt_le; apply Rinv_0_lt_compat; lra).
assert (P2 : 0 <= (1 + t) ^ 2) by (apply pow_le; lra).
assert (P3 : 0 <= (1 + t) ^ 3) by (apply pow_le; lra).
assert (T2 : 0 <= t ^ 2) by (apply pow_le; lra).
assert (N0 : 0 <= 2 * (1 + t) ^ 3 * Model.up_ball_mul_2_1 emin prec * Model.up_ball_mul_2_0 emin prec
                  + 2 * t ^ 2).
{ apply Rplus_le_le_0_compat; [apply Rmult_le_pos; [apply Rmult_le_pos; [apply Rmult_le_pos|]|]|];
    lra. }
assert (B1 : 0 <= / 2 * Model.up_ball_mul_2_1 emin prec * eta emin + Model.up_ball_mul_2_2 emin prec).
{ apply Rplus_le_le_0_compat; [apply Rmult_le_pos; [apply Rmult_le_pos|]|]; lra. }
assert (B2 : 0 <= 2 * (1 + t) ^ 2 * (/ 2 * Model.up_ball_mul_2_1 emin prec * eta emin
                                     + Model.up_ball_mul_2_2 emin prec))
  by (apply Rmult_le_pos; [apply Rmult_le_pos|]; lra).
assert (B3 : 0 <= (2 * (1 + t) ^ 3 * Model.up_ball_mul_2_1 emin prec * Model.up_ball_mul_2_0 emin prec
                   + 2 * t ^ 2) / (1 - t) * (3 / 2 * eta emin)).
{ unfold Rdiv. apply Rmult_le_pos; [apply Rmult_le_pos|]; lra. }
lra.
Qed.

(** * The finite core *)

Lemma mul_ball_2_2_ieee_core :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  let '(z0, z1, d) := mul_ball_2_2 x0 x1 y0 y1 in
  fin z0 ->
  fin z1 /\
  (b2r z0, b2r z1) = Model.mul_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1) /\
  nonneg_ext d /\
  (fin d ->
   b2r d = rnd (rnd (Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec + 0)
                * Model.up_ball_mul_2_1 emin prec + Model.up_ball_mul_2_2 emin prec)).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny.
unfold IeeeModel.mul_ball_2_2.
generalize (mul_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp x0 x1 y0 y1
              F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [z0 z1].
cbv beta iota zeta. intros V Fz0.
destruct (V Fz0) as [Fz1 Ez].
destruct (consts_ball_mul_2 prec emax Hp) as [[FE [EE HE]] [[FG [EG HG]] [FH [EH HH]]]].
destruct (prod_nonneg prec emax nan_fma _ _ (abs_nonneg prec emax nan_abs z0) HE) as [Ht Et].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ht HG HH) as [Hd Ed].
split; [exact Fz1|split; [exact Ez|split; [exact Hd|]]].
intros Fd. destruct (Ed Fd) as [Ft [_ [_ E1]]]. destruct (Et Ft) as [_ [_ E2]].
rewrite E1, E2, (abs_val prec emax nan_abs), EE, EG, EH. reflexivity.
Qed.

(* mul_dir_2_2 on finite normalized operands: a finite leading limb of a bound comes with a
   finite second limb, and the bound is the one of the real model. *)
Lemma mul_dir_2_2_ieee_core :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  forall (l0 l1 h0 h1 : float) (c0 c1 e0 e1 : R),
  mul_dir_2_2 x0 x1 y0 y1 = (l0, l1, h0, h1) ->
  Model.mul_dir_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1) = (c0, c1, e0, e1) ->
  (fin l0 -> fin l1 /\ b2r l0 = c0 /\ b2r l1 = c1) /\
  (fin h0 -> fin h1 /\ b2r h0 = e0 /\ b2r h1 = e1).
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny l0 l1 h0 h1 c0 c1 e0 e1 EI ER.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Ball := mul_ball_2_2_ieee_core Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
unfold IeeeModel.mul_dir_2_2 in EI. unfold Model.mul_dir_2_2 in ER.
revert Ball EI.
destruct (mul_ball_2_2 x0 x1 y0 y1) as [[z0 z1] d]. intros Ball EI.
cbv beta iota zeta in EI.
generalize (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 z0
              (neg (add_up_1 d (neg z1))))
           (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs z0
              (neg (add_up_1 d (neg z1))))
           (two_sum_ord_ieee_finite prec emax nan_plus nan_minus nan_abs Hp2 z0 (add_up_1 z1 d))
           (two_sum_ord_ieee_nonfinite prec emax nan_plus nan_minus nan_abs z0 (add_up_1 z1 d)).
revert EI.
destruct (two_sum_ord z0 (neg (add_up_1 d (neg z1)))) as [p0 p1].
destruct (two_sum_ord z0 (add_up_1 z1 d)) as [q0 q1].
intros EI TFl TNl TFu TNu. cbv beta iota in EI. injection EI as E0 E1 E2 E3. subst l0 l1 h0 h1.
(* The real model, once z0 and d are finite. *)
assert (MB : fin z0 -> fin d ->
             Model.mul_ball_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1)
             = (b2r z0, b2r z1, b2r d) /\ fin z1 /\ 0 <= b2r d).
{ intros Fz0 Fd. destruct (Ball Fz0) as [Fz1 [Ez [Nd Ed]]].
  split; [|split; [exact Fz1|exact (nonneg_ext_fin prec emax d Nd Fd)]].
  unfold Model.mul_ball_2_2. rewrite <- Ez. cbv beta iota zeta. rewrite (Ed Fd). reflexivity. }
split.
- (* the lower bound *)
  intros Fp0.
  assert (NF : ~ (is_finite prec emax z0 = false \/
                  is_finite prec emax (neg (add_up_1 d (neg z1))) = false)).
  { intros K. destruct (TNl K) as [E _]. rewrite (xval_fin prec emax p0 Fp0) in E.
    exact (xadd_not_fin prec emax z0 _ _ K (eq_sym E)). }
  assert (Fz0 : fin z0).
  { destruct (is_finite prec emax z0) eqn:F; trivial. elim NF. now left. }
  assert (Fw : fin (neg (add_up_1 d (neg z1)))).
  { destruct (is_finite prec emax (neg (add_up_1 d (neg z1)))) eqn:F; trivial. elim NF. now right. }
  assert (Ft : fin (add_up_1 d (neg z1))).
  { now rewrite (IeeeExt.neg_finite prec emax nan_opp) in Fw. }
  destruct (TFl Fz0 Fw) as [Hfin _]. destruct (Hfin Fp0) as [Fp1 Ep].
  destruct (add_up_1_fin_inv prec emax nan_plus nan_minus nan_abs Hp2 d (neg z1) Ft) as [Fd Fnz].
  destruct (MB Fz0 Fd) as [EM [Fz1 Pd]].
  assert (Et := add_up_1_value prec emax nan_plus nan_minus nan_abs Hp2 d (neg z1) Fd Fnz
                  (or_introl Pd) Ft).
  rewrite (IeeeExt.neg_value prec emax nan_opp) in Et.
  rewrite (IeeeExt.neg_value prec emax nan_opp), Et in Ep.
  rewrite EM in ER. cbv beta iota zeta in ER. rewrite <- Ep in ER.
  destruct (Model.two_sum_ord emin prec tie_even (b2r z0)
              (Model.add_up_1 emin prec tie_even (b2r z1) (b2r d))) as [m0 m1].
  cbv beta iota in ER. injection ER as R0 R1 _ _. split; [exact Fp1|split; assumption].
- (* the upper bound *)
  intros Fq0.
  assert (NF : ~ (is_finite prec emax z0 = false \/ is_finite prec emax (add_up_1 z1 d) = false)).
  { intros K. destruct (TNu K) as [E _]. rewrite (xval_fin prec emax q0 Fq0) in E.
    exact (xadd_not_fin prec emax z0 _ _ K (eq_sym E)). }
  assert (Fz0 : fin z0).
  { destruct (is_finite prec emax z0) eqn:F; trivial. elim NF. now left. }
  assert (Fw : fin (add_up_1 z1 d)).
  { destruct (is_finite prec emax (add_up_1 z1 d)) eqn:F; trivial. elim NF. now right. }
  destruct (TFu Fz0 Fw) as [Hfin _]. destruct (Hfin Fq0) as [Fq1 Eq].
  destruct (add_up_1_fin_inv prec emax nan_plus nan_minus nan_abs Hp2 z1 d Fw) as [Fz1 Fd].
  destruct (MB Fz0 Fd) as [EM [_ Pd]].
  assert (Ew := add_up_1_value prec emax nan_plus nan_minus nan_abs Hp2 z1 d Fz1 Fd
                  (or_intror Pd) Fw).
  rewrite Ew in Eq.
  rewrite EM in ER. cbv beta iota zeta in ER.
  destruct (Model.two_sum_ord emin prec tie_even (b2r z0)
              (- Model.add_up_1 emin prec tie_even (b2r d) (- b2r z1))) as [m0 m1].
  rewrite <- Eq in ER.
  cbv beta iota in ER. injection ER as _ _ R0 R1. split; [exact Fq1|split; assumption].
Qed.

(* Within a quarter of the range, both leading limbs are finite. *)
Lemma mul_dir_2_2_ieee_small :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 2) ->
  let '(l0, l1, h0, h1) := mul_dir_2_2 x0 x1 y0 y1 in fin l0 /\ fin h0.
Proof.
intros Hp x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hv.
assert (Hp2 : (2 <= prec)%Z) by lia. assert (Hp3 : (3 <= prec)%Z) by lia.
assert (b3 : 0 < bpow radix2 (emax - 3)) by apply bpow_gt_0.
assert (EB : bpow radix2 (emax - 2) = 2 * bpow radix2 (emax - 3)) by apply quarter_range_eq.
assert (E4 : bpow radix2 (emax - 3) = 2 * bpow radix2 (emax - 4)).
{ rewrite <- two_bpow. f_equal. lia. }
assert (E5 : bpow radix2 (emax - 3) = 4 * bpow radix2 (emax - 5)).
{ replace (emax - 3)%Z with (emax - 5 + 1 + 1)%Z by ring. rewrite 2!two_bpow. ring. }
assert (Eta : eta emin <= bpow radix2 (emax - 5)) by (unfold eta; apply bpow_le; lia).
assert (e0 : 0 < eta emin) by apply bpow_gt_0.
assert (Ut : 0 < u prec <= / 16) by exact (Ball2.u_bounds prec 4 Hp). destruct Ut as [U0 U1].
assert (Hs : Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 1)).
{ apply Rle_trans with (1 := Hv). apply bpow_le. lia. }
unfold IeeeModel.mul_dir_2_2, IeeeModel.mul_ball_2_2.
generalize (mul_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hs)
           (mul_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp
              x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [z0 z1].
cbv beta iota zeta. intros [_ [Fz0 Fz1]] V. destruct (V Fz0) as [_ [Nz Ez]].
set (v := (b2r x0 + b2r x1) * (b2r y0 + b2r y1)) in *.
(* the center *)
assert (Q4 : 4 * u prec ^ 2 <= / 64).
{ replace (u prec ^ 2) with (u prec * u prec) by ring.
  assert (Q : u prec * u prec <= / 16 * / 16) by (apply Rmult_le_compat; lra). lra. }
assert (V0 := Rabs_pos v).
assert (Q5 : 4 * u prec ^ 2 * Rabs v <= / 64 * Rabs v) by (apply Rmult_le_compat_r; lra).
assert (Hz : Rabs (b2r z0 + b2r z1) <= 5 / 2 * bpow radix2 (emax - 3)).
{ generalize (Rabs_le_plus_err (b2r z0 + b2r z1) v). lra. }
assert (Hz0 : 3 * Rabs (b2r z0) <= 10 * bpow radix2 (emax - 3)).
{ generalize (lead_le prec emax Hp2 _ _ Nz). lra. }
assert (Hz1 : Rabs (b2r z1) <= / 4 * bpow radix2 (emax - 3)).
{ generalize (normalized_2_tail_rel emin prec _ _ Nz). intros T.
  assert (K : u prec * Rabs (b2r z0) <= / 16 * Rabs (b2r z0))
    by (apply Rmult_le_compat_r; [apply Rabs_pos|lra]).
  lra. }
(* the radius *)
destruct (consts_ball_mul_2 prec emax Hp) as [[FE [EE _]] [[FG [EG _]] [FH [EH _]]]].
destruct (E_mul_2_le_eighth Hp) as [Ea Eb]. destruct (G_6_le prec emax Hp) as [Ga Gb].
destruct (H_mul_2_le prec emax Hp) as [Ha Hb].
assert (Fa : fin (fabs z0)) by now rewrite (abs_finite prec emax nan_abs).
assert (Az := Rabs_pos (b2r z0)).
assert (Y1 : Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec <= bpow radix2 (emax - 4)).
{ apply Rle_trans with (Rabs (b2r z0) * / 8); [apply Rmult_le_compat_l; lra|lra]. }
assert (Y0 : 0 <= Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec) by (apply Rmult_le_pos; lra).
assert (F4 : format (bpow radix2 (emax - 4))) by (apply (IeeeBallFinite.format_bpow prec emax); lia).
assert (F2 : format (bpow radix2 (emax - 2))) by (apply (IeeeBallFinite.format_bpow prec emax); lia).
assert (S0 : 0 <= rnd (Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec + 0))
  by (apply (rnd_pos prec emax); lra).
assert (S1 : rnd (Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec + 0) <= bpow radix2 (emax - 4))
  by (apply (rnd_le_format prec emax); [exact F4|lra]).
assert (LT := Omega_lt_top prec emax).
assert (O7 := Omega_ge_7_eighths prec emax Hp3).
assert (It : IeeeBridge.inrange emax
               (rnd (b2r (fabs z0) * b2r (IeeeModel.up_ball_mul_2_0 prec emax) + 0))).
{ rewrite (abs_val prec emax nan_abs), EE. unfold IeeeBridge.inrange.
  rewrite Rabs_pos_eq by lra. lra. }
destruct (prod_fin prec emax nan_fma _ _ Fa FE It) as [Ft Et].
rewrite (abs_val prec emax nan_abs), EE in Et.
set (t := prod (fabs z0) (IeeeModel.up_ball_mul_2_0 prec emax)) in *.
set (s := rnd (Rabs (b2r z0) * Model.up_ball_mul_2_0 emin prec + 0)) in *.
assert (K0 : 0 <= s * Model.up_ball_mul_2_1 emin prec) by (apply Rmult_le_pos; lra).
assert (K1 : s * Model.up_ball_mul_2_1 emin prec <= bpow radix2 (emax - 4) * (3 / 2))
  by (apply Rmult_le_compat; lra).
assert (D0 : 0 <= rnd (s * Model.up_ball_mul_2_1 emin prec + Model.up_ball_mul_2_2 emin prec))
  by (apply (rnd_pos prec emax); lra).
assert (D1 : rnd (s * Model.up_ball_mul_2_1 emin prec + Model.up_ball_mul_2_2 emin prec)
             <= bpow radix2 (emax - 2))
  by (apply (rnd_le_format prec emax); [exact F2|lra]).
assert (Id : IeeeBridge.inrange emax
               (rnd (b2r t * b2r (IeeeModel.up_ball_mul_2_1 prec emax)
                     + b2r (IeeeModel.up_ball_mul_2_2 prec emax)))).
{ rewrite Et, EG, EH. unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by lra. lra. }
destruct (fma_fin prec emax nan_fma _ _ _ Ft FG FH Id) as [Fd Ed].
rewrite Et, EG, EH in Ed.
set (d := fma t (IeeeModel.up_ball_mul_2_1 prec emax) (IeeeModel.up_ball_mul_2_2 prec emax)) in *.
(* the last lines *)
assert (Fnz : fin (neg z1)) by now rewrite (IeeeExt.neg_finite prec emax nan_opp).
assert (Hs1 : Rabs (b2r d + b2r (neg z1)) <= 3 * bpow radix2 (emax - 3)).
{ rewrite (IeeeExt.neg_value prec emax nan_opp), Ed.
  generalize (Rabs_triang (rnd (s * Model.up_ball_mul_2_1 emin prec + Model.up_ball_mul_2_2 emin prec))
                (- b2r z1)).
  rewrite Rabs_Ropp, (Rabs_pos_eq (rnd _)) by lra. lra. }
destruct (add_up_1_small prec emax nan_plus nan_minus nan_abs Hp3 d (neg z1) Fd Fnz Hs1) as [Fw Bw].
assert (Fw' : fin (neg (add_up_1 d (neg z1)))) by now rewrite (IeeeExt.neg_finite prec emax nan_opp).
assert (Kl : Rabs (b2r z0 + b2r (neg (add_up_1 d (neg z1)))) <= 7 * bpow radix2 (emax - 3)).
{ rewrite (IeeeExt.neg_value prec emax nan_opp).
  generalize (Rabs_triang (b2r z0) (- b2r (add_up_1 d (neg z1)))). rewrite Rabs_Ropp. lra. }
assert (Hs2 : Rabs (b2r z1 + b2r d) <= 3 * bpow radix2 (emax - 3)).
{ rewrite Ed. generalize (Rabs_triang (b2r z1)
    (rnd (s * Model.up_ball_mul_2_1 emin prec + Model.up_ball_mul_2_2 emin prec))).
  rewrite (Rabs_pos_eq (rnd _)) by lra. lra. }
destruct (add_up_1_small prec emax nan_plus nan_minus nan_abs Hp3 z1 d Fz1 Fd Hs2) as [Fu Bu].
assert (Ku : Rabs (b2r z0 + b2r (add_up_1 z1 d)) <= 7 * bpow radix2 (emax - 3)).
{ generalize (Rabs_triang (b2r z0) (b2r (add_up_1 z1 d))). lra. }
generalize (two_sum_ord_small prec emax nan_plus nan_minus nan_abs Hp3 z0 _ Fz0 Fw' Kl)
           (two_sum_ord_small prec emax nan_plus nan_minus nan_abs Hp3 z0 _ Fz0 Fu Ku).
destruct (two_sum_ord z0 (neg (add_up_1 d (neg z1)))) as [l0 l1].
destruct (two_sum_ord z0 (add_up_1 z1 d)) as [h0 h1].
intros A B. exact (conj A B).
Qed.

(** * mul_ext_2_2 *)

(* The sign of a normalized pair whose leading limb is not zero is that limb's, and the pair
   is not zero. *)
Lemma normalized_sign :
  forall a b : R, normalized_2 emin prec a b -> a <> 0 ->
  Rlt_bool (a + b) 0 = Rlt_bool a 0 /\ Req_bool (a + b) 0 = false /\ Req_bool a 0 = false.
Proof.
intros a b N A. assert (T := normalized_2_tail_rel emin prec a b N).
assert (U : u prec < 1) by (unfold u; change 1 with (bpow radix2 0); apply bpow_lt; lia).
assert (U0 : 0 < u prec) by apply bpow_gt_0.
assert (Pa : 0 < Rabs a) by (apply Rabs_pos_lt; exact A).
assert (K : Rabs b < Rabs a).
{ apply Rle_lt_trans with (1 := T). rewrite <- (Rmult_1_l (Rabs a)) at 2.
  apply Rmult_lt_compat_r; lra. }
assert (Kb := Rle_abs b). assert (Kb' : - b <= Rabs b) by (rewrite <- Rabs_Ropp; apply Rle_abs).
destruct (Rlt_bool_spec a 0) as [L|L].
- rewrite (Rabs_left a) in K by exact L.
  split; [apply Rlt_bool_true; lra|split; apply Req_bool_false; intros E; lra].
- assert (Pa' : 0 < a).
  { destruct (Rle_lt_or_eq_dec 0 a L) as [P|P]; [exact P|elim A; symmetry; exact P]. }
  rewrite (Rabs_pos_eq a) in K by lra.
  split; [apply Rlt_bool_false; lra|split; apply Req_bool_false; intros E; lra].
Qed.

(* A canonical value that is neither a NaN nor a zero: an infinity, which it stands for, or a
   finite normalized pair with the sign of its leading limb and not zero. *)
Lemma xval_2_lead_class :
  forall x0 x1 : float, canonical_2 x0 x1 -> ~ nan x0 -> ~ zero x0 ->
  (is_finite prec emax x0 = false /\ xv2 x0 x1 = xv x0) \/
  (fin x0 /\ fin x1 /\ normalized_2 emin prec (b2r x0) (b2r x1) /\
   xv2 x0 x1 = XFin (b2r x0 + b2r x1) /\ xv x0 = XFin (b2r x0) /\
   Rlt_bool (b2r x0 + b2r x1) 0 = Rlt_bool (b2r x0) 0 /\
   Req_bool (b2r x0 + b2r x1) 0 = false /\ Req_bool (b2r x0) 0 = false).
Proof.
intros x0 x1 C N Z.
destruct (canonical_cases prec emax x0 x1 C)
  as [[F0 [F1 [Nx [E0 [E1 E]]]]]|[[s [s' [E0 [E1 [_ [_ E]]]]]]|[N0 _]]].
- right.
  assert (A : b2r x0 <> 0) by (intros K; apply Z; exact (zero_inv prec emax x0 F0 K)).
  destruct (normalized_sign _ _ Nx A) as [S1 [S2 S3]].
  exact (conj F0 (conj F1 (conj Nx (conj E (conj E0 (conj S1 (conj S2 S3))))))).
- left. subst x0. split; [reflexivity|]. rewrite E. reflexivity.
- elim (N N0).
Qed.

Lemma xval_not_nan : forall a : float, ~ nan a -> xv a <> XNaN.
Proof.
intros a N E. unfold xval in E. destruct (is_finite prec emax a); [discriminate E|].
destruct (is_nan prec emax a) eqn:K; [apply N; exact K|discriminate E].
Qed.

(* With an infinite factor, the product of the 2-limb values is that of the leading limbs, an
   infinity. *)
Lemma xmul_2_lead :
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  ~ nan x0 -> ~ nan y0 -> ~ zero x0 -> ~ zero y0 ->
  is_finite prec emax x0 = false \/ is_finite prec emax y0 = false ->
  xmul (xv2 x0 x1) (xv2 y0 y1) = xmul (xv x0) (xv y0) /\
  exists s : bool, xmul (xv x0) (xv y0) = XInf s.
Proof.
intros x0 x1 y0 y1 Cx Cy Nx Ny Zx Zy H.
assert (NNx := xval_not_nan x0 Nx). assert (NNy := xval_not_nan y0 Ny).
destruct (xval_2_lead_class x0 x1 Cx Nx Zx) as [[Fx Ex]|[Fx [_ [_ [Ex [Ex' [Sx [Zx1 Zx2]]]]]]]];
destruct (xval_2_lead_class y0 y1 Cy Ny Zy) as [[Fy Ey]|[Fy [_ [_ [Ey [Ey' [Sy [Zy1 Zy2]]]]]]]].
- rewrite Ex, Ey. split; [reflexivity|].
  destruct (xval_cases prec emax x0) as [[F _]|[[sx Ex0]|Ex0]]; [congruence| |elim (NNx Ex0)].
  destruct (xval_cases prec emax y0) as [[F _]|[[sy Ey0]|Ey0]]; [congruence| |elim (NNy Ey0)].
  rewrite Ex0, Ey0. now exists (xorb sx sy).
- rewrite Ex, Ey, Ey'.
  destruct (xval_cases prec emax x0) as [[F _]|[[sx Ex0]|Ex0]]; [congruence| |elim (NNx Ex0)].
  rewrite Ex0. cbn [xmul]. rewrite Zy1, Zy2, Sy.
  split; [reflexivity|now exists (xorb sx (Rlt_bool (b2r y0) 0))].
- rewrite Ex, Ey, Ex'.
  destruct (xval_cases prec emax y0) as [[F _]|[[sy Ey0]|Ey0]]; [congruence| |elim (NNy Ey0)].
  rewrite Ey0. cbn [xmul]. rewrite Zx1, Zx2, Sx.
  split; [reflexivity|now exists (xorb (Rlt_bool (b2r x0) 0) sy)].
- exfalso. destruct H as [H|H]; congruence.
Qed.

(* mul_ext_2_2, for canonical operands that are not NaN, from precision 4: the generated
   statement, with the constants of the closed form by name. *)
Theorem mul_ext_2_2_all :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  canonical_2 x0 x1 -> canonical_2 y0 y1 -> ~ nan x0 -> ~ nan y0 ->
  let '(l0, l1, h0, h1) := mul_ext_2_2 x0 x1 y0 y1 in
  canonical_2 l0 l1 /\
  (finite x0 /\ finite x1 /\ finite y0 /\ finite y1 -> finite l0 -> finite l1 ->
   normalized_2 emin prec (val l0) (val l1)) /\
  canonical_2 h0 h1 /\
  (finite x0 /\ finite x1 /\ finite y0 /\ finite y1 -> finite h0 -> finite h1 ->
   normalized_2 emin prec (val h0) (val h1)) /\
  (zero x0 \/ zero y0 -> zero l0 /\ zero l1) /\
  (~ (zero x0 \/ zero y0) ->
   ~ nan l0 /\
   (~ (finite x0 /\ finite x1 /\ finite y0 /\ finite y1) ->
    xval_2 l0 l1 = xmul (xval_2 x0 x1) (xval_2 y0 y1)) /\
   (finite x0 /\ finite x1 /\ finite y0 /\ finite y1 ->
    xle (xval_2 l0 l1) (xmul (xval_2 x0 x1) (xval_2 y0 y1)) = true /\
    (finite l0 ->
     Rabs ((val l0 + val l1) - ((val x0 + val x1) * (val y0 + val y1)))
     <= mul_outward_rel emin prec * Rabs ((val x0 + val x1) * (val y0 + val y1))
        + mul_outward_abs emin prec))) /\
  (zero x0 \/ zero y0 -> zero h0 /\ zero h1) /\
  (~ (zero x0 \/ zero y0) ->
   ~ nan h0 /\
   (~ (finite x0 /\ finite x1 /\ finite y0 /\ finite y1) ->
    xval_2 h0 h1 = xmul (xval_2 x0 x1) (xval_2 y0 y1)) /\
   (finite x0 /\ finite x1 /\ finite y0 /\ finite y1 ->
    xle (xmul (xval_2 x0 x1) (xval_2 y0 y1)) (xval_2 h0 h1) = true /\
    (finite h0 ->
     Rabs ((val h0 + val h1) - ((val x0 + val x1) * (val y0 + val y1)))
     <= mul_outward_rel emin prec * Rabs ((val x0 + val x1) * (val y0 + val y1))
        + mul_outward_abs emin prec))).
Proof.
intros Hp x0 x1 y0 y1 Cx Cy Nx Ny.
unfold IeeeModel.mul_ext_2_2.
destruct (mul_dir_2_2 x0 x1 y0 y1) as [[[c0 c1] e0] e1] eqn:EC.
cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs x0), (lt_abs_pinf prec emax nan_abs y0),
        (lt_abs_pinf prec emax nan_abs c0), (lt_abs_pinf prec emax nan_abs e0).
rewrite (neg_pinf prec emax nan_opp).
assert (Zero2 : canonical_2 pzero pzero /\ normalized_2 emin prec (b2r pzero) (b2r pzero)).
{ assert (N0 := normalized_2_lead prec emax pzero).
  split; [left; split; [reflexivity|split; [reflexivity|exact N0]]|exact N0]. }
assert (Zp : zero pzero) by (exists false; reflexivity).
destruct (orb (feq x0 pzero) (feq y0 pzero)) eqn:Z; cbn [negb].
- (* a zero factor: zero *)
  assert (ZZ : zero x0 \/ zero y0) by (apply (zero_factor_test prec emax); exact Z).
  destruct Zero2 as [C0 N0].
  split; [exact C0|split; [intros _ _ _; exact N0|]].
  split; [exact C0|split; [intros _ _ _; exact N0|]].
  split; [intros _; split; exact Zp|].
  split; [intros K; elim (K ZZ)|].
  split; [intros _; split; exact Zp|].
  intros K; elim (K ZZ).
- assert (NZ : ~ (zero x0 \/ zero y0)).
  { intros K. apply (zero_factor_test prec emax) in K. rewrite K in Z. discriminate Z. }
  assert (Zx : ~ zero x0) by (intros K; apply NZ; now left).
  assert (Zy : ~ zero y0) by (intros K; apply NZ; now right).
  assert (Nninf : ~ nan ninf) by (intros K; discriminate K).
  assert (Cninf : canonical_2 ninf pzero)
    by (right; left; split; [exists true; reflexivity|exact Zp]).
  assert (Cpinf : canonical_2 pinf pzero)
    by (right; left; split; [exists false; reflexivity|exact Zp]).
  destruct (andb (is_finite prec emax x0) (is_finite prec emax y0)) eqn:FO.
  + (* finite factors: the core *)
    apply andb_true_iff in FO. destruct FO as [Fx0 Fy0].
    destruct (canonical_2_finite prec emax x0 x1 Cx Fx0) as [Fx1 Nxn].
    destruct (canonical_2_finite prec emax y0 y1 Cy Fy0) as [Fy1 Nyn].
    destruct (Model.mul_dir_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1))
      as [[[mc0 mc1] me0] me1] eqn:ER.
    destruct (mul_dir_2_2_ieee_core Hp x0 x1 y0 y1 Fx0 Fx1 Fy0 Fy1 Nxn Nyn
                c0 c1 e0 e1 mc0 mc1 me0 me1 EC ER) as [CL CH].
    generalize (mul_dir_2_2_outward emin prec Hp (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nxn Nyn).
    rewrite ER. intros [NL [NH [LV [TL [HV TH]]]]].
    rewrite (xval_2_fin prec emax x0 x1 Fx0), (xval_2_fin prec emax y0 y1 Fy0). cbn [xmul].
    assert (AF : ~ (finite x0 /\ finite x1 /\ finite y0 /\ finite y1) -> False)
      by (intros K; apply K; exact (conj Fx0 (conj Fx1 (conj Fy0 Fy1)))).
    assert (Low :
      canonical_2 (if is_finite prec emax c0 then c0 else ninf)
                  (if is_finite prec emax c0 then c1 else pzero) /\
      (finite (if is_finite prec emax c0 then c0 else ninf) ->
       finite (if is_finite prec emax c0 then c1 else pzero) ->
       normalized_2 emin prec (val (if is_finite prec emax c0 then c0 else ninf))
                              (val (if is_finite prec emax c0 then c1 else pzero))) /\
      ~ nan (if is_finite prec emax c0 then c0 else ninf) /\
      xle (xv2 (if is_finite prec emax c0 then c0 else ninf)
               (if is_finite prec emax c0 then c1 else pzero))
          (XFin ((b2r x0 + b2r x1) * (b2r y0 + b2r y1))) = true /\
      (finite (if is_finite prec emax c0 then c0 else ninf) ->
       Rabs ((val (if is_finite prec emax c0 then c0 else ninf)
              + val (if is_finite prec emax c0 then c1 else pzero))
             - ((val x0 + val x1) * (val y0 + val y1)))
       <= mul_outward_rel emin prec * Rabs ((val x0 + val x1) * (val y0 + val y1))
          + mul_outward_abs emin prec)).
    { destruct (is_finite prec emax c0) eqn:Fc; cbv beta iota.
      - destruct (CL eq_refl) as [Fc1 [Ec0 Ec1]].
        assert (Nc : normalized_2 emin prec (b2r c0) (b2r c1)) by (rewrite Ec0, Ec1; exact NL).
        split; [left; split; [exact Fc|split; [exact Fc1|exact Nc]]|].
        split; [intros _ _; exact Nc|].
        split; [unfold nan; now rewrite (finite_not_nan prec emax c0 Fc)|].
        split.
        + rewrite (xval_2_fin prec emax c0 c1 Fc). cbn [xle]. apply Rle_bool_true.
          rewrite Ec0, Ec1. exact LV.
        + intros _. unfold val. rewrite Ec0, Ec1. exact TL.
      - split; [exact Cninf|split; [intros K; discriminate K|]].
        split; [exact Nninf|split; [reflexivity|intros K; discriminate K]]. }
    assert (High :
      canonical_2 (if is_finite prec emax e0 then e0 else pinf)
                  (if is_finite prec emax e0 then e1 else pzero) /\
      (finite (if is_finite prec emax e0 then e0 else pinf) ->
       finite (if is_finite prec emax e0 then e1 else pzero) ->
       normalized_2 emin prec (val (if is_finite prec emax e0 then e0 else pinf))
                              (val (if is_finite prec emax e0 then e1 else pzero))) /\
      ~ nan (if is_finite prec emax e0 then e0 else pinf) /\
      xle (XFin ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)))
          (xv2 (if is_finite prec emax e0 then e0 else pinf)
               (if is_finite prec emax e0 then e1 else pzero)) = true /\
      (finite (if is_finite prec emax e0 then e0 else pinf) ->
       Rabs ((val (if is_finite prec emax e0 then e0 else pinf)
              + val (if is_finite prec emax e0 then e1 else pzero))
             - ((val x0 + val x1) * (val y0 + val y1)))
       <= mul_outward_rel emin prec * Rabs ((val x0 + val x1) * (val y0 + val y1))
          + mul_outward_abs emin prec)).
    { destruct (is_finite prec emax e0) eqn:Fe; cbv beta iota.
      - destruct (CH eq_refl) as [Fe1 [Ee0 Ee1]].
        assert (Ne : normalized_2 emin prec (b2r e0) (b2r e1)) by (rewrite Ee0, Ee1; exact NH).
        split; [left; split; [exact Fe|split; [exact Fe1|exact Ne]]|].
        split; [intros _ _; exact Ne|].
        split; [unfold nan; now rewrite (finite_not_nan prec emax e0 Fe)|].
        split.
        + rewrite (xval_2_fin prec emax e0 e1 Fe). cbn [xle]. apply Rle_bool_true.
          rewrite Ee0, Ee1. exact HV.
        + intros _. unfold val. rewrite Ee0, Ee1. exact TH.
      - split; [exact Cpinf|split; [intros K; discriminate K|]].
        split; [intros K; discriminate K|split; [reflexivity|intros K; discriminate K]]. }
    destruct Low as [L1 [L2 [L3 [L4 L5]]]]. destruct High as [H1 [H2 [H3 [H4 H5]]]].
    split; [exact L1|split; [intros _; exact L2|]].
    split; [exact H1|split; [intros _; exact H2|]].
    split; [intros K; elim (NZ K)|].
    split; [intros _; split; [exact L3|split; [intros K; elim (AF K)|intros _; exact (conj L4 L5)]]|].
    split; [intros K; elim (NZ K)|].
    intros _; split; [exact H3|split; [intros K; elim (AF K)|intros _; exact (conj H4 H5)]].
  + (* an infinite factor: the product of IEEE 754, an infinity *)
    assert (H : is_finite prec emax x0 = false \/ is_finite prec emax y0 = false).
    { apply andb_false_iff in FO. exact FO. }
    destruct (xmul_2_lead x0 x1 y0 y1 Cx Cy Nx Ny Zx Zy H) as [XM [s Es]].
    assert (Et := xval_prod_nonfinite prec emax nan_fma x0 y0 H).
    rewrite Es in Et.
    assert (Ft : prod x0 y0 = B754_infinity prec emax s) by exact (xval_inf_inv prec emax _ _ Et).
    rewrite Ft.
    assert (Ct : canonical_2 (B754_infinity prec emax s) pzero)
      by (right; left; split; [exists s; reflexivity|exact Zp]).
    assert (AF : finite x0 /\ finite x1 /\ finite y0 /\ finite y1 -> False).
    { intros [K1 [_ [K3 _]]]. unfold finite in K1, K3. destruct H as [H|H]; congruence. }
    assert (Ev : xval_2 (B754_infinity prec emax s) pzero = xmul (xval_2 x0 x1) (xval_2 y0 y1))
      by (rewrite XM, Es; reflexivity).
    assert (Nt : ~ nan (B754_infinity prec emax s)) by (intros K; discriminate K).
    split; [exact Ct|split; [intros K; elim (AF K)|]].
    split; [exact Ct|split; [intros K; elim (AF K)|]].
    split; [intros K; elim (NZ K)|].
    split; [intros _; split; [exact Nt|split; [intros _; exact Ev|intros K; elim (AF K)]]|].
    split; [intros K; elim (NZ K)|].
    intros _; split; [exact Nt|split; [intros _; exact Ev|intros K; elim (AF K)]].
Qed.

(** * What the product of intervals needs of each product of bounds *)

Lemma xval_2_fin_inv :
  forall (x0 x1 : float) (v : R), xv2 x0 x1 = XFin v -> fin x0 /\ v = b2r x0 + b2r x1.
Proof.
intros x0 x1 v E. unfold xval_2 in E. destruct (is_finite prec emax x0) eqn:F.
- injection E as E. split; [reflexivity|rewrite <- E; reflexivity].
- destruct (is_nan prec emax x0); discriminate E.
Qed.

Lemma xval_2_not_nan : forall x0 x1 : float, canonical_2 x0 x1 -> ~ nan x0 -> xv2 x0 x1 <> XNaN.
Proof.
intros x0 x1 C N.
destruct (canonical_cases prec emax x0 x1 C)
  as [[_ [_ [_ [_ [_ E]]]]]|[[s [s' [_ [_ [_ [_ E]]]]]]|[N0 _]]]; rewrite ?E.
- discriminate.
- discriminate.
- elim (N N0).
Qed.

Lemma xval_2_zero :
  forall x0 x1 : float, canonical_2 x0 x1 -> zero x0 ->
  xv2 x0 x1 = XFin 0 /\ fin x0 /\ b2r x0 + b2r x1 = 0.
Proof.
intros x0 x1 C [s E].
assert (F : fin x0) by (rewrite E; reflexivity).
destruct (canonical_2_finite prec emax x0 x1 C F) as [_ N].
assert (V0 : b2r x0 = 0) by (rewrite E; reflexivity).
assert (V1 := normalized_2_zero emin prec _ _ N V0).
assert (V : b2r x0 + b2r x1 = 0) by lra.
split; [rewrite (xval_2_fin prec emax x0 x1 F), V; reflexivity|split; [exact F|exact V]].
Qed.

Lemma xval_2_nonzero :
  forall x0 x1 : float, canonical_2 x0 x1 -> ~ nan x0 -> ~ zero x0 -> xv2 x0 x1 <> XFin 0.
Proof.
intros x0 x1 C N Z.
destruct (xval_2_lead_class x0 x1 C N Z) as [[F E]|[F [_ [_ [E [_ [_ [Zr _]]]]]]]].
- rewrite E. unfold xval. rewrite F. destruct (is_nan prec emax x0); discriminate.
- rewrite E. intros K. injection K as K. rewrite K in Zr.
  rewrite Req_bool_true in Zr by reflexivity. discriminate Zr.
Qed.

Definition corner (a0 a1 b0 b1 l0 l1 h0 h1 : float) : Prop :=
  canonical_2 l0 l1 /\ canonical_2 h0 h1 /\
  xle (xv2 l0 l1) (xmul0 (xv2 a0 a1) (xv2 b0 b1)) = true /\
  xle (xmul0 (xv2 a0 a1) (xv2 b0 b1)) (xv2 h0 h1) = true /\
  (fin a0 -> fin b0 -> forall v : R, xv2 l0 l1 = XFin v ->
   (b2r a0 + b2r a1) * (b2r b0 + b2r b1) - v
   <= mul_outward_rel emin prec * Rabs ((b2r a0 + b2r a1) * (b2r b0 + b2r b1))
      + mul_outward_abs emin prec) /\
  (fin a0 -> fin b0 -> forall w : R, xv2 h0 h1 = XFin w ->
   w - (b2r a0 + b2r a1) * (b2r b0 + b2r b1)
   <= mul_outward_rel emin prec * Rabs ((b2r a0 + b2r a1) * (b2r b0 + b2r b1))
      + mul_outward_abs emin prec) /\
  (zero a0 \/ zero b0 -> zero l0 /\ zero l1 /\ zero h0 /\ zero h1) /\
  (fin a0 -> fin b0 ->
   Rabs ((b2r a0 + b2r a1) * (b2r b0 + b2r b1)) <= bpow radix2 (emax - 2) ->
   fin l0 /\ fin h0).

(* mul_ext_2_2 is finite on finite operands whose product is within a quarter of the range. *)
Lemma mul_ext_2_2_small :
  (4 <= prec)%Z ->
  forall a0 a1 b0 b1 : float, canonical_2 a0 a1 -> canonical_2 b0 b1 -> fin a0 -> fin b0 ->
  Rabs ((b2r a0 + b2r a1) * (b2r b0 + b2r b1)) <= bpow radix2 (emax - 2) ->
  let '(l0, l1, h0, h1) := mul_ext_2_2 a0 a1 b0 b1 in fin l0 /\ fin h0.
Proof.
intros Hp a0 a1 b0 b1 Ca Cb Fa Fb H.
destruct (canonical_2_finite prec emax a0 a1 Ca Fa) as [Fa1 Na].
destruct (canonical_2_finite prec emax b0 b1 Cb Fb) as [Fb1 Nb].
generalize (mul_dir_2_2_ieee_small Hp a0 a1 b0 b1 Fa Fa1 Fb Fb1 Na Nb H).
unfold IeeeModel.mul_ext_2_2.
destruct (mul_dir_2_2 a0 a1 b0 b1) as [[[c0 c1] e0] e1]. intros [Fc Fe].
cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs a0), (lt_abs_pinf prec emax nan_abs b0),
        (lt_abs_pinf prec emax nan_abs c0), (lt_abs_pinf prec emax nan_abs e0), Fa, Fb, Fc, Fe.
cbn [andb].
destruct (negb (orb (feq a0 pzero) (feq b0 pzero))); split; first [exact Fc|exact Fe|reflexivity].
Qed.

(* The four facts of a product of bounds of canonical intervals. *)
Lemma mul_ext_corner :
  (4 <= prec)%Z ->
  forall a0 a1 b0 b1 : float, canonical_2 a0 a1 -> canonical_2 b0 b1 -> ~ nan a0 -> ~ nan b0 ->
  let '(l0, l1, h0, h1) := mul_ext_2_2 a0 a1 b0 b1 in corner a0 a1 b0 b1 l0 l1 h0 h1.
Proof.
intros Hp a0 a1 b0 b1 Ca Cb Na Nb.
generalize (mul_ext_2_2_all Hp a0 a1 b0 b1 Ca Cb Na Nb) (mul_ext_2_2_small Hp a0 a1 b0 b1 Ca Cb).
destruct (mul_ext_2_2 a0 a1 b0 b1) as [[[l0 l1] h0] h1].
intros [CL [NL [CH [NH [ZL [ML [ZH MH]]]]]]] Small.
destruct (mul_rel_bounds Hp) as [A0 A1]. assert (B0 := mul_abs_ge_0 Hp).
assert (NNa := xval_2_not_nan a0 a1 Ca Na). assert (NNb := xval_2_not_nan b0 b1 Cb Nb).
assert (AFd : (finite a0 /\ finite a1 /\ finite b0 /\ finite b1) \/
              ~ (finite a0 /\ finite a1 /\ finite b0 /\ finite b1)).
{ destruct (finite_dec prec emax a0) as [Fa|Fa]; [destruct (finite_dec prec emax b0) as [Fb|Fb]|].
  - left. destruct (canonical_2_finite prec emax a0 a1 Ca Fa) as [Fa1 _].
    destruct (canonical_2_finite prec emax b0 b1 Cb Fb) as [Fb1 _].
    exact (conj Fa (conj Fa1 (conj Fb Fb1))).
  - right. intros [_ [_ [K _]]]. unfold finite in K. congruence.
  - right. intros [K _]. unfold finite in K. congruence. }
split; [exact CL|split; [exact CH|]].
destruct (orb (feq a0 pzero) (feq b0 pzero)) eqn:Z.
- (* a zero factor: both outputs are zero, and so is the product *)
  assert (ZZ : zero a0 \/ zero b0) by (apply (zero_factor_test prec emax); exact Z).
  destruct (ZL ZZ) as [Zl0 Zl1]. destruct (ZH ZZ) as [Zh0 Zh1].
  destruct (xval_2_zero l0 l1 CL Zl0) as [El _]. destruct (xval_2_zero h0 h1 CH Zh0) as [Eh _].
  assert (EP : xmul0 (xv2 a0 a1) (xv2 b0 b1) = XFin 0 /\
               (fin a0 -> fin b0 -> (b2r a0 + b2r a1) * (b2r b0 + b2r b1) = 0)).
  { destruct ZZ as [Za|Zb].
    - destruct (xval_2_zero a0 a1 Ca Za) as [Ea [_ Va]]. rewrite Ea.
      split; [exact (xmul0_zero_l _ NNb)|intros _ _; rewrite Va; ring].
    - destruct (xval_2_zero b0 b1 Cb Zb) as [Eb [_ Vb]]. rewrite Eb.
      split; [exact (xmul0_zero_r _ NNa)|intros _ _; rewrite Vb; ring]. }
  destruct EP as [EP VP]. rewrite El, Eh, EP.
  assert (R00 : xle (XFin 0) (XFin 0) = true) by (apply xle_refl_nn; discriminate).
  split; [exact R00|split; [exact R00|]].
  split; [intros Fa Fb v Ev; injection Ev as Ev; rewrite (VP Fa Fb), <- Ev, Rabs_R0; lra|].
  split; [intros Fa Fb w Ew; injection Ew as Ew; rewrite (VP Fa Fb), <- Ew, Rabs_R0; lra|].
  split; [intros _; exact (conj Zl0 (conj Zl1 (conj Zh0 Zh1)))|exact Small].
- (* no zero factor *)
  assert (NZ : ~ (zero a0 \/ zero b0)).
  { intros K. apply (zero_factor_test prec emax) in K. rewrite K in Z. discriminate Z. }
  assert (Za : ~ zero a0) by (intros K; apply NZ; now left).
  assert (Zb : ~ zero b0) by (intros K; apply NZ; now right).
  rewrite (xmul0_xmul _ _ (xval_2_nonzero a0 a1 Ca Na Za) (xval_2_nonzero b0 b1 Cb Nb Zb)).
  destruct (ML NZ) as [Nl0 [MLi MLf]]. destruct (MH NZ) as [Nh0 [MHi MHf]].
  destruct AFd as [AF|AF].
  + destruct (MLf AF) as [Ll Tl]. destruct (MHf AF) as [Hh Th].
    split; [exact Ll|split; [exact Hh|]].
    split.
    { intros _ _ v Ev. destruct (xval_2_fin_inv l0 l1 v Ev) as [Fl Vl].
      specialize (Tl Fl). unfold val in Tl. rewrite <- Vl in Tl.
      apply Rabs_le_inv in Tl. lra. }
    split.
    { intros _ _ w Ew. destruct (xval_2_fin_inv h0 h1 w Ew) as [Fh Vh].
      specialize (Th Fh). unfold val in Th. rewrite <- Vh in Th.
      apply Rabs_le_inv in Th. lra. }
    split; [intros K; elim (NZ K)|exact Small].
  + assert (EL := MLi AF). assert (EH := MHi AF).
    assert (Rm : xle (xmul (xv2 a0 a1) (xv2 b0 b1)) (xmul (xv2 a0 a1) (xv2 b0 b1)) = true).
    { rewrite <- EL. apply xle_refl_nn. exact (xval_2_not_nan l0 l1 CL Nl0). }
    assert (NA : fin a0 -> fin b0 -> False).
    { intros Fa Fb. apply AF.
      destruct (canonical_2_finite prec emax a0 a1 Ca Fa) as [Fa1 _].
      destruct (canonical_2_finite prec emax b0 b1 Cb Fb) as [Fb1 _].
      exact (conj Fa (conj Fa1 (conj Fb Fb1))). }
    rewrite EL, EH.
    split; [exact Rm|split; [exact Rm|]].
    split; [intros Fa Fb; elim (NA Fa Fb)|].
    split; [intros Fa Fb; elim (NA Fa Fb)|].
    split; [intros K; elim (NZ K)|exact Small].
Qed.

(** * interval_mul_2 *)

(* The listing for any limbs l and u that stand for the least of the four lower values and the
   greatest of the four upper ones, each limb one of the four. *)
Lemma interval_mul_2_of :
  (4 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
         a0 a1 e0 e1 b0 b1 f0 f1 c0 c1 g0 g1 d0 d1 h0 h1 l0 l1 u0 u1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  corner xl0 xl1 yl0 yl1 a0 a1 e0 e1 -> corner xl0 xl1 yu0 yu1 b0 b1 f0 f1 ->
  corner xu0 xu1 yl0 yl1 c0 c1 g0 g1 -> corner xu0 xu1 yu0 yu1 d0 d1 h0 h1 ->
  canonical_2 l0 l1 ->
  xv2 l0 l1 = xmin (xmin (xv2 a0 a1) (xv2 b0 b1)) (xmin (xv2 c0 c1) (xv2 d0 d1)) ->
  canonical_2 u0 u1 ->
  xv2 u0 u1 = xmax (xmax (xv2 e0 e1) (xv2 f0 f1)) (xmax (xv2 g0 g1) (xv2 h0 h1)) ->
  (l0 = a0 \/ l0 = b0 \/ l0 = c0 \/ l0 = d0) -> (l1 = a1 \/ l1 = b1 \/ l1 = c1 \/ l1 = d1) ->
  (u0 = e0 \/ u0 = f0 \/ u0 = g0 \/ u0 = h0) -> (u1 = e1 \/ u1 = f1 \/ u1 = g1 \/ u1 = h1) ->
  forall zl0 zl1 zu0 zu1 : float,
  zl0 = (if andb (flt xl0 pinf) (flt yl0 pinf) then l0 else pinf) ->
  zl1 = (if andb (flt xl0 pinf) (flt yl0 pinf) then l1 else pzero) ->
  zu0 = (if andb (flt xl0 pinf) (flt yl0 pinf) then u0 else ninf) ->
  zu1 = (if andb (flt xl0 pinf) (flt yl0 pinf) then u1 else pzero) ->
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (x * y)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   forall lo hi : R,
   range_lower (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin lo) ->
   range_upper (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin hi) ->
   (interval_bounded_2 zl0 zl1 zu0 zu1 ->
    lo - (b2r zl0 + b2r zl1) <= mul_outward_rel emin prec * Rabs lo + mul_outward_abs emin prec /\
    (b2r zu0 + b2r zu1) - hi <= mul_outward_rel emin prec * Rabs hi + mul_outward_abs emin prec)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (range_lower (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf true) ->
    xval_2 zl0 zl1 = XInf true) /\
   (range_upper (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf false) ->
    xval_2 zu0 zu1 = XInf false)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (zero xl0 /\ zero xu0) \/ (zero yl0 /\ zero yu0) ->
   zero zl0 /\ zero zl1 /\ zero zu0 /\ zero zu1) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   (forall z : R,
    range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
      (in_interval_2 yl0 yl1 yu0 yu1) z ->
    Rabs z <= bpow radix2 (emax - 2)) ->
   interval_bounded_2 zl0 zl1 zu0 zu1).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 a0 a1 e0 e1 b0 b1 f0 f1 c0 c1 g0 g1 d0 d1 h0 h1
       l0 l1 u0 u1 CX CY KA KB KC KD Cl El Cu Eu L0 L1 U0 U1 zl0 zl1 zu0 zu1 Z0 Z1 Z2 Z3.
destruct (mul_rel_bounds Hp) as [A0 A1].
destruct KA as [_ [_ [Ka1 [Ka2 [Ta1 [Ta2 [Za Fa]]]]]]].
destruct KB as [_ [_ [Kb1 [Kb2 [Tb1 [Tb2 [Zb Fb]]]]]]].
destruct KC as [_ [_ [Kc1 [Kc2 [Tc1 [Tc2 [Zc Fc]]]]]]].
destruct KD as [_ [_ [Kd1 [Kd2 [Td1 [Td2 [Zd Fd]]]]]]].
assert (Core : interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
               canonical_2 l0 l1 /\ canonical_2 u0 u1 /\
               forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
               in_interval_2 l0 l1 u0 u1 (x * y)).
{ intros _ _. split; [exact Cl|split; [exact Cu|]].
  intros x y [Hx1 Hx2] [Hy1 Hy2]. split.
  - rewrite El. exact (rectangle_lower_bound _ _ _ _ x y Hx1 Hx2 Hy1 Hy2 _ _ _ _ Ka1 Kb1 Kc1 Kd1).
  - rewrite Eu. exact (rectangle_upper_bound _ _ _ _ x y Hx1 Hx2 Hy1 Hy2 _ _ _ _ Ka2 Kb2 Kc2 Kd2). }
destruct (interval_tail_2 prec emax (fun x y : R => x * y) xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
            l0 l1 u0 u1 CX CY Core zl0 zl1 zu0 zu1 Z0 Z1 Z2 Z3) as [I1 [I2 [I3 EQ]]].
split; [exact I1|split; [exact I2|split; [exact I3|]]].
(* What a bounded operand is. *)
assert (Bnd : forall p0 p1 q0 q1 : float,
          interval_2 p0 p1 q0 q1 -> interval_bounded_2 p0 p1 q0 q1 ->
          interval_nonempty_2 p0 p1 q0 q1 /\ fin p0 /\ fin q0 /\
          in_interval_2 p0 p1 q0 q1 (b2r p0 + b2r p1) /\
          in_interval_2 p0 p1 q0 q1 (b2r q0 + b2r q1)).
{ intros p0 p1 q0 q1 C B. assert (N := bounded_nonempty_2 prec emax _ _ _ _ C B).
  destruct B as [Fp Fq].
  assert (Ep := xval_2_fin prec emax p0 p1 Fp). assert (Eq := xval_2_fin prec emax q0 q1 Fq).
  split; [exact N|split; [exact Fp|split; [exact Fq|]]].
  destruct N as [_ [_ NN]]. unfold in_interval_2. rewrite Ep, Eq in NN |- *.
  split; [now apply xmember_lower|now apply xmember_upper]. }
split.
{ (* I4, bounded operands *)
  intros BX BY lo hi Hlo Hhi.
  destruct (Bnd _ _ _ _ CX BX) as [NX [Fxl [Fxu [Mxl Mxu]]]].
  destruct (Bnd _ _ _ _ CY BY) as [NY [Fyl [Fyu [Myl Myu]]]].
  destruct (EQ NX NY) as [Q0 [Q1 [Q2 Q3]]]. rewrite Q0, Q1, Q2, Q3.
  assert (InR : forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
                lo <= x * y /\ x * y <= hi).
  { intros x y Hx Hy.
    assert (Rz : range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1) (x * y))
      by (exists x, y; exact (conj Hx (conj Hy eq_refl))).
    generalize (proj1 Hlo _ Rz) (proj1 Hhi _ Rz). cbn [xle]. intros K1 K2.
    split; [exact (Rle_bool_inv _ _ K1)|exact (Rle_bool_inv _ _ K2)]. }
  intros [Fzl Fzu]. split.
  - assert (Ez := xval_2_fin prec emax l0 l1 Fzl). rewrite El in Ez.
    destruct (xmin4_cases (xv2 a0 a1) (xv2 b0 b1) (xv2 c0 c1) (xv2 d0 d1)) as [E|[E|[E|E]]];
      rewrite E in Ez.
    + exact (min_tight _ _ lo _ _ (conj A0 A1) (proj1 (InR _ _ Mxl Myl)) (Ta1 Fxl Fyl _ Ez)).
    + exact (min_tight _ _ lo _ _ (conj A0 A1) (proj1 (InR _ _ Mxl Myu)) (Tb1 Fxl Fyu _ Ez)).
    + exact (min_tight _ _ lo _ _ (conj A0 A1) (proj1 (InR _ _ Mxu Myl)) (Tc1 Fxu Fyl _ Ez)).
    + exact (min_tight _ _ lo _ _ (conj A0 A1) (proj1 (InR _ _ Mxu Myu)) (Td1 Fxu Fyu _ Ez)).
  - assert (Ez := xval_2_fin prec emax u0 u1 Fzu). rewrite Eu in Ez.
    destruct (xmax4_cases (xv2 e0 e1) (xv2 f0 f1) (xv2 g0 g1) (xv2 h0 h1)) as [E|[E|[E|E]]];
      rewrite E in Ez.
    + exact (max_tight _ _ hi _ _ (conj A0 A1) (proj2 (InR _ _ Mxl Myl)) (Ta2 Fxl Fyl _ Ez)).
    + exact (max_tight _ _ hi _ _ (conj A0 A1) (proj2 (InR _ _ Mxl Myu)) (Tb2 Fxl Fyu _ Ez)).
    + exact (max_tight _ _ hi _ _ (conj A0 A1) (proj2 (InR _ _ Mxu Myl)) (Tc2 Fxu Fyl _ Ez)).
    + exact (max_tight _ _ hi _ _ (conj A0 A1) (proj2 (InR _ _ Mxu Myu)) (Td2 Fxu Fyu _ Ez)). }
split.
{ (* an infinite bound of the exact range *)
  intros NX NY. destruct (EQ NX NY) as [Q0 [Q1 [Q2 Q3]]]. rewrite Q0, Q1, Q2, Q3.
  destruct (xnonempty_member _ _ (proj2 (proj2 NX))) as [mx Mx].
  destruct (xnonempty_member _ _ (proj2 (proj2 NY))) as [my My].
  assert (Ex : exists z : R, range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                               (in_interval_2 yl0 yl1 yu0 yu1) z)
    by (exists (mx * my), mx, my; exact (conj Mx (conj My eq_refl))).
  split.
  - intros Hlo.
    assert (Elo := range_lower_unique _ _ _ Ex Hlo
                     (range_mul_lower _ _ _ _ (proj2 (proj2 NX)) (proj2 (proj2 NY)))).
    apply xle_ninf. rewrite El, Elo. exact (xmin4_mono _ _ _ _ _ _ _ _ Ka1 Kb1 Kc1 Kd1).
  - intros Hhi.
    assert (Ehi := range_upper_unique _ _ _ Ex Hhi
                     (range_mul_upper _ _ _ _ (proj2 (proj2 NX)) (proj2 (proj2 NY)))).
    apply xle_pinf. rewrite Eu, Ehi. exact (xmax4_mono _ _ _ _ _ _ _ _ Ka2 Kb2 Kc2 Kd2). }
split.
{ (* a factor [0, 0] *)
  intros NX NY ZZ. destruct (EQ NX NY) as [Q0 [Q1 [Q2 Q3]]]. rewrite Q0, Q1, Q2, Q3.
  assert (All : (zero a0 /\ zero a1 /\ zero e0 /\ zero e1) /\ (zero b0 /\ zero b1 /\ zero f0 /\ zero f1) /\
                (zero c0 /\ zero c1 /\ zero g0 /\ zero g1) /\ (zero d0 /\ zero d1 /\ zero h0 /\ zero h1)).
  { destruct ZZ as [[Zl Zu]|[Zl Zu]].
    - exact (conj (Za (or_introl Zl)) (conj (Zb (or_introl Zl))
               (conj (Zc (or_introl Zu)) (Zd (or_introl Zu))))).
    - exact (conj (Za (or_intror Zl)) (conj (Zb (or_intror Zu))
               (conj (Zc (or_intror Zl)) (Zd (or_intror Zu))))). }
  destruct All as [[za0 [za1 [ze0 ze1]]] [[zb0 [zb1 [zf0 zf1]]] [[zc0 [zc1 [zg0 zg1]]]
                   [zd0 [zd1 [zh0 zh1]]]]]].
  split; [destruct L0 as [E|[E|[E|E]]]; rewrite E; assumption|].
  split; [destruct L1 as [E|[E|[E|E]]]; rewrite E; assumption|].
  split; [destruct U0 as [E|[E|[E|E]]]; rewrite E; assumption|].
  destruct U1 as [E|[E|[E|E]]]; rewrite E; assumption. }
(* I5 *)
intros BX BY W.
destruct (Bnd _ _ _ _ CX BX) as [NX [Fxl [Fxu [Mxl Mxu]]]].
destruct (Bnd _ _ _ _ CY BY) as [NY [Fyl [Fyu [Myl Myu]]]].
destruct (EQ NX NY) as [Q0 [Q1 [Q2 Q3]]]. rewrite Q0, Q1, Q2, Q3.
assert (Wc : forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
             Rabs (x * y) <= bpow radix2 (emax - 2))
  by (intros x y Hx Hy; apply W; exists x, y; exact (conj Hx (conj Hy eq_refl))).
destruct (Fa Fxl Fyl (Wc _ _ Mxl Myl)) as [Fa0 Fe0].
destruct (Fb Fxl Fyu (Wc _ _ Mxl Myu)) as [Fb0 Ff0].
destruct (Fc Fxu Fyl (Wc _ _ Mxu Myl)) as [Fc0 Fg0].
destruct (Fd Fxu Fyu (Wc _ _ Mxu Myu)) as [Fd0 Fh0].
split; unfold finite.
- destruct L0 as [E|[E|[E|E]]]; rewrite E; assumption.
- destruct U0 as [E|[E|[E|E]]]; rewrite E; assumption.
Qed.

(* interval_mul_2, for canonical operands X and Y, from precision 4: I1 to I5 and the factor
   [0, 0] as the generated statement has them, with the constants of the closed form by
   name. *)
Theorem interval_mul_2_all :
  (4 <= prec)%Z ->
  forall xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 : float,
  interval_2 xl0 xl1 xu0 xu1 -> interval_2 yl0 yl1 yu0 yu1 ->
  let '(zl0, zl1, zu0, zu1) := interval_mul_2 xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 in
  interval_2 zl0 zl1 zu0 zu1 /\
  (interval_empty_2 zl0 zl1 zu0 zu1 <->
   interval_empty_2 xl0 xl1 xu0 xu1 \/ interval_empty_2 yl0 yl1 yu0 yu1) /\
  (forall x y : R, in_interval_2 xl0 xl1 xu0 xu1 x -> in_interval_2 yl0 yl1 yu0 yu1 y ->
   in_interval_2 zl0 zl1 zu0 zu1 (x * y)) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   forall lo hi : R,
   range_lower (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin lo) ->
   range_upper (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                  (in_interval_2 yl0 yl1 yu0 yu1)) (XFin hi) ->
   (interval_bounded_2 zl0 zl1 zu0 zu1 ->
    lo - (b2r zl0 + b2r zl1) <= mul_outward_rel emin prec * Rabs lo + mul_outward_abs emin prec /\
    (b2r zu0 + b2r zu1) - hi <= mul_outward_rel emin prec * Rabs hi + mul_outward_abs emin prec)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (range_lower (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf true) ->
    xval_2 zl0 zl1 = XInf true) /\
   (range_upper (range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
                   (in_interval_2 yl0 yl1 yu0 yu1)) (XInf false) ->
    xval_2 zu0 zu1 = XInf false)) /\
  (interval_nonempty_2 xl0 xl1 xu0 xu1 -> interval_nonempty_2 yl0 yl1 yu0 yu1 ->
   (zero xl0 /\ zero xu0) \/ (zero yl0 /\ zero yu0) ->
   zero zl0 /\ zero zl1 /\ zero zu0 /\ zero zu1) /\
  (interval_bounded_2 xl0 xl1 xu0 xu1 -> interval_bounded_2 yl0 yl1 yu0 yu1 ->
   (forall z : R,
    range_2 (fun x y : R => x * y) (in_interval_2 xl0 xl1 xu0 xu1)
      (in_interval_2 yl0 yl1 yu0 yu1) z ->
    Rabs z <= bpow radix2 (emax - 2)) ->
   interval_bounded_2 zl0 zl1 zu0 zu1).
Proof.
intros Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
destruct (interval_2_canonical prec emax _ _ _ _ CX) as [Cxl Cxu].
destruct (interval_2_canonical prec emax _ _ _ _ CY) as [Cyl Cyu].
assert (NN : forall p0 p1 q0 q1 : float, interval_2 p0 p1 q0 q1 -> ~ nan p0 /\ ~ nan q0).
{ intros p0 p1 q0 q1 [[E0 [_ [E2 _]]]|[_ [_ N]]].
  - rewrite E0, E2. split; intros K; discriminate K.
  - split; intros K.
    + rewrite (xval_2_nan prec emax p0 p1 K) in N. destruct N as [N _]. discriminate N.
    + rewrite (xval_2_nan prec emax q0 q1 K) in N. destruct N as [N _].
      destruct (xv2 p0 p1) as [|[|]|r]; discriminate N. }
destruct (NN _ _ _ _ CX) as [Nxl Nxu]. destruct (NN _ _ _ _ CY) as [Nyl Nyu].
unfold IeeeModel.interval_mul_2.
generalize (mul_ext_corner Hp xl0 xl1 yl0 yl1 Cxl Cyl Nxl Nyl)
           (mul_ext_corner Hp xl0 xl1 yu0 yu1 Cxl Cyu Nxl Nyu)
           (mul_ext_corner Hp xu0 xu1 yl0 yl1 Cxu Cyl Nxu Nyl)
           (mul_ext_corner Hp xu0 xu1 yu0 yu1 Cxu Cyu Nxu Nyu).
destruct (mul_ext_2_2 xl0 xl1 yl0 yl1) as [[[a0 a1] e0] e1].
destruct (mul_ext_2_2 xl0 xl1 yu0 yu1) as [[[b0 b1] f0] f1].
destruct (mul_ext_2_2 xu0 xu1 yl0 yl1) as [[[c0 c1] g0] g1].
destruct (mul_ext_2_2 xu0 xu1 yu0 yu1) as [[[d0 d1] h0] h1].
intros KA KB KC KD. cbv beta iota zeta. rewrite (neg_pinf prec emax nan_opp).
destruct (select_lt_2_xmin prec emax a0 a1 b0 b1 (proj1 KA) (proj1 KB)) as [Cp Ep].
destruct (select_lt_2_xmin prec emax c0 c1 d0 d1 (proj1 KC) (proj1 KD)) as [Cq Eq].
destruct (select_lt_2_xmin prec emax _ _ _ _ Cp Cq) as [Cl El].
rewrite Ep, Eq in El.
destruct (select_lt_2_xmax prec emax e0 e1 f0 f1 (proj1 (proj2 KA)) (proj1 (proj2 KB))) as [Cr Er].
destruct (select_lt_2_xmax prec emax g0 g1 h0 h1 (proj1 (proj2 KC)) (proj1 (proj2 KD))) as [Cs Es].
destruct (select_lt_2_xmax prec emax _ _ _ _ Cr Cs) as [Cu Eu].
rewrite Er, Es in Eu.
exact (interval_mul_2_of Hp xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1
         a0 a1 e0 e1 b0 b1 f0 f1 c0 c1 g0 g1 d0 d1 h0 h1 _ _ _ _ CX CY KA KB KC KD
         Cl El Cu Eu
         (select_lt_one_of_four prec emax a0 b0 c0 d0 _ _ _)
         (select_lt_one_of_four prec emax a1 b1 c1 d1 _ _ _)
         (select_lt_one_of_four prec emax e0 f0 g0 h0 _ _ _)
         (select_lt_one_of_four prec emax e1 f1 g1 h1 _ _ _)
         _ _ _ _ eq_refl eq_refl eq_refl eq_refl).
Qed.

End IeeeIntervalMul2.

(** * The generated statements *)

Theorem mul_ext_2_2_correct : mul_ext_2_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp x0 x1 y0 y1 Cx Cy Nx Ny.
exact (mul_ext_2_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
         x0 x1 y0 y1 Cx Cy Nx Ny).
Qed.

Theorem interval_mul_2_correct : interval_mul_2_spec.
Proof.
intros prec emax Hp0 He nan_plus nan_minus nan_opp nan_abs nan_fma Hp
       xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY.
exact (interval_mul_2_all prec emax nan_plus nan_minus nan_opp nan_abs nan_fma Hp
         xl0 xl1 xu0 xu1 yl0 yl1 yu0 yu1 CX CY).
Qed.
