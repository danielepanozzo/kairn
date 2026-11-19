(* The Ball kernels: ball_add_k, ball_sub_k, ball_neg_k, ball_scale_k, ball_mul_k, for
   centers of k = 1 and k = 2 limbs.

   A ball is a center c (one number of the format, or a normalized 2-limb number) and a
   radius r (a nonnegative number of the format); it stands for the real numbers x with
   |x - c| <= r. Each kernel returns a center cz and a radius rz.

   What is proved (the generated statements of proofs/gen/Statements.v): containment. For
   all real x, y in the operand balls, x o y is in the result ball: |x o y - cz| <= rz.
   For k = 2 the returned center is also normalized (it is the result of the center's
   kernel).

   Why (Milestone 1 statements, Ball kernels). Write e for the error of the center,
   e = |cz - (cx o cy)|. By the triangle inequality
       |x + y - cz| <= rx + ry + e,
       |x y - cz|   <= |cx| ry + |cy| rx + rx ry + e,
       |x a - cz|   <= |a| rx + e,
   and the radius computed by the kernel is at least the right-hand side:
   - every radd and rmul returns at least the exact sum or product of its nonnegative
     operands (Directed.v), so a chain of them is at least the exact expression;
   - |cx| is replaced by an upper bound of it: |cx| itself for one limb, RU (|cx|) for two
     limbs (abs_upper_2, Convert.v);
   - e <= U mz + V, where mz is the kernel's upper bound of |cz| and U, V are the
     constants unit_computed (K) and tiny_computed (K) of the center's kernel K (below).

   The constants. K's theorem bounds the error relative to the exact value v:
   e <= rel |v| + tiny, with rel = c u^k and tiny = t eta. Since |v| <= |cz| + e, this gives
   e <= rel / (1 - rel) |cz| + tiny / (1 - rel) as soon as rel < 1 (lemma computed_bound).
   In the model (proofs/gen/Model.v) the constants are DEFINED as
       unit_computed (K) = RU (rel / (1 - rel)),    tiny_computed (K) = RU (tiny / (1 - rel)),
   with rel and tiny written out from K's claims, and RU rounding up to the format. The
   proofs use three facts about them and nothing else: each is a number of the format, is
   nonnegative, and is at least the exact quotient it rounds. All three are properties of
   RU, proved here (lemma RU_radius), not hypotheses. That rel < 1 is proved for each K at
   its minimum precision (lemmas rel_one_limb, rel_add_2_2, rel_mul_2_1, rel_mul_2_2).
   What is NOT proved here is that the literals the generator prints in the C++ for
   binary64 and binary32 are the values of these definitions: that is the generator's
   computation (gen/kairn_gen/consts.py), checked by its tests.

   The statements are in the model without overflow. In a format with a largest number, a
   radius that overflows is +infinity, which still encloses. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Add22 Mul22 Mul21 Directed Sign Convert OneLimb.
Open Scope R_scope.

(** * Real-number facts *)

(* A bound relative to the exact value v, turned into one relative to the computed
   value z: |v| <= |z| + |z - v|. *)
Lemma computed_bound :
  forall rel tiny z v : R, 0 <= rel < 1 -> 0 <= tiny ->
  Rabs (z - v) <= rel * Rabs v + tiny ->
  Rabs (z - v) <= rel / (1 - rel) * Rabs z + tiny / (1 - rel).
Proof.
intros rel tiny z v [H0 H1] Ht H.
assert (Hv : Rabs v <= Rabs z + Rabs (z - v)).
{ unfold Rabs. destruct (Rcase_abs v), (Rcase_abs z), (Rcase_abs (z - v)); lra. }
assert (Hm : rel * Rabs v <= rel * (Rabs z + Rabs (z - v))).
{ apply Rmult_le_compat_l; assumption. }
assert (Hk : Rabs (z - v) * (1 - rel) <= rel * Rabs z + tiny) by nra.
apply Rmult_le_reg_r with (1 - rel). lra.
replace ((rel / (1 - rel) * Rabs z + tiny / (1 - rel)) * (1 - rel))
  with (rel * Rabs z + tiny) by (field; lra).
exact Hk.
Qed.

Lemma div_pos : forall a rel : R, 0 <= a -> 0 <= rel < 1 -> 0 <= a / (1 - rel).
Proof.
intros a rel Ha [H0 H1]. unfold Rdiv. apply Rmult_le_pos. exact Ha.
apply Rlt_le, Rinv_0_lt_compat. lra.
Qed.

(* The three triangle inequalities; e bounds the error of the center. *)
Lemma enclose_add :
  forall x y cx cy cz rx ry e : R,
  Rabs (x - cx) <= rx -> Rabs (y - cy) <= ry -> Rabs (cz - (cx + cy)) <= e ->
  Rabs (x + y - cz) <= rx + ry + e.
Proof.
intros x y cx cy cz rx ry e Hx Hy He.
apply Rabs_le_inv in Hx. apply Rabs_le_inv in Hy. apply Rabs_le_inv in He.
apply Rabs_le. split; lra.
Qed.

(* x y - cx cy = cx (y - cy) + cy (x - cx) + (x - cx) (y - cy); ax and ay are upper bounds
   of |cx| and |cy|. *)
Lemma enclose_mul :
  forall x y cx cy cz rx ry ax ay e : R,
  Rabs (x - cx) <= rx -> Rabs (y - cy) <= ry -> Rabs cx <= ax -> Rabs cy <= ay ->
  Rabs (cz - cx * cy) <= e ->
  Rabs (x * y - cz) <= ax * ry + ay * rx + rx * ry + e.
Proof.
intros x y cx cy cz rx ry ax ay e Hx Hy Hax Hay He.
replace (x * y - cz)
  with (cx * (y - cy) + cy * (x - cx) + (x - cx) * (y - cy) + - (cz - cx * cy)) by ring.
assert (T1 : Rabs (cx * (y - cy)) <= ax * ry).
{ rewrite Rabs_mult. apply Rmult_le_compat; try apply Rabs_pos; assumption. }
assert (T2 : Rabs (cy * (x - cx)) <= ay * rx).
{ rewrite Rabs_mult. apply Rmult_le_compat; try apply Rabs_pos; assumption. }
assert (T3 : Rabs ((x - cx) * (y - cy)) <= rx * ry).
{ rewrite Rabs_mult. apply Rmult_le_compat; try apply Rabs_pos; assumption. }
assert (T4 : Rabs (- (cz - cx * cy)) <= e) by now rewrite Rabs_Ropp.
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat; [|exact T4].
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat; [|exact T3].
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat; assumption.
Qed.

Lemma enclose_scale :
  forall x a cx cz rx e : R,
  Rabs (x - cx) <= rx -> Rabs (cz - cx * a) <= e ->
  Rabs (x * a - cz) <= Rabs a * rx + e.
Proof.
intros x a cx cz rx e Hx He.
replace (x * a - cz) with (a * (x - cx) + - (cz - cx * a)) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat.
- rewrite Rabs_mult. apply Rmult_le_compat_l. apply Rabs_pos. exact Hx.
- now rewrite Rabs_Ropp.
Qed.

(* The relative parts of the bounds of the center kernels are below 1; t stands for u. *)
Lemma rel_one_limb_R : forall t : R, 0 < t -> 0 <= 1 / (1 + t) * t ^ 1 < 1.
Proof.
intros t Ht.
replace (1 / (1 + t) * t ^ 1) with (t / (1 + t)) by (field; lra).
assert (Hi : 0 < / (1 + t)) by (apply Rinv_0_lt_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_lt_reg_r with (1 + t). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

Lemma rel_add_2_2_R : forall t : R, 0 < t <= / 8 -> 0 <= 3 / (1 - 4 * t) * t ^ 2 < 1.
Proof.
intros t [Ht0 Ht8].
replace (3 / (1 - 4 * t) * t ^ 2) with (3 * (t * t) / (1 - 4 * t)) by (field; lra).
assert (Hi : 0 < / (1 - 4 * t)) by (apply Rinv_0_lt_compat; lra).
assert (Hq : 0 <= t * t) by (apply Rmult_le_pos; lra).
assert (Hq2 : t * t <= / 8 * / 8) by (apply Rmult_le_compat; lra).
split.
- unfold Rdiv. apply Rmult_le_pos; lra.
- apply Rmult_lt_reg_r with (1 - 4 * t). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

Lemma rel_square_R : forall c b t : R, 0 <= c -> 0 < t <= b -> c * (b * b) < 1 -> 0 <= c * t ^ 2 < 1.
Proof.
intros c b t Hc [Ht0 Htb] Hcb.
replace (t ^ 2) with (t * t) by ring.
assert (Hq : 0 <= t * t) by (apply Rmult_le_pos; lra).
assert (Hq2 : t * t <= b * b) by (apply Rmult_le_compat; lra).
split.
- apply Rmult_le_pos; lra.
- apply Rle_lt_trans with (2 := Hcb). apply Rmult_le_compat_l; lra.
Qed.

Lemma u_bounds : forall (prec k : Z), (k <= prec)%Z -> 0 < u prec <= pow2 (- k).
Proof.
intros prec k H. unfold u. split. apply bpow_gt_0. apply bpow_le. lia.
Qed.

Lemma rel_one_limb : forall prec : Z, 0 <= 1 / (1 + u prec) * u prec ^ 1 < 1.
Proof. intros prec. apply rel_one_limb_R. apply bpow_gt_0. Qed.

Lemma rel_add_2_2 : forall prec : Z, (3 <= prec)%Z -> 0 <= 3 / (1 - 4 * u prec) * u prec ^ 2 < 1.
Proof. intros prec Hp. apply rel_add_2_2_R. exact (u_bounds prec 3 Hp). Qed.

Lemma rel_mul_2_1 : forall prec : Z, (2 <= prec)%Z -> 0 <= 2 * u prec ^ 2 < 1.
Proof.
intros prec Hp. apply rel_square_R with (/ 4). lra. exact (u_bounds prec 2 Hp). lra.
Qed.

Lemma rel_mul_2_2 : forall prec : Z, (4 <= prec)%Z -> 0 <= 4 * u prec ^ 2 < 1.
Proof.
intros prec Hp. apply rel_square_R with (/ 16). lra. exact (u_bounds prec 4 Hp). lra.
Qed.

(** * Radii *)

Section Radius.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation radd := (radd emin prec tie_even).
Notation rmul := (rmul emin prec tie_even).
Notation RUp := (round radix2 fexp Zceil).

(* A radius: a nonnegative number of the format. These are the operands radd and rmul
   are specified for. *)
Definition radius (r : R) : Prop := format r /\ 0 <= r.

Lemma radius_abs : forall c, format c -> radius (Rabs c).
Proof.
intros c Fc. unfold radius. split.
- now apply generic_format_abs.
- apply Rabs_pos.
Qed.

(* radd and rmul of two radii: again a radius, and at least the exact sum or product. *)
Lemma radd_radius :
  forall a b, radius a -> radius b -> radius (radd a b) /\ a + b <= radd a b.
Proof.
intros a b [Fa Ha] [Fb Hb].
assert (Hs : 0 <= a + b) by lra.
rewrite radd_eq.
assert (H1 := up_above emin prec tie_even (a + b) Hs).
assert (H2 := up_format emin prec tie_even (a + b)).
unfold radius. split; [split|]; [exact H2 | lra | lra].
Qed.

Lemma rmul_radius :
  forall a b, radius a -> radius b -> radius (rmul a b) /\ a * b <= rmul a b.
Proof.
intros a b [Fa Ha] [Fb Hb].
assert (Hs : 0 <= a * b) by now apply Rmult_le_pos.
rewrite rmul_eq.
assert (H1 := up_above emin prec tie_even (a * b) Hs).
assert (H2 := up_format emin prec tie_even (a * b)).
unfold radius. split; [split|]; [exact H2 | lra | lra].
Qed.

(* Rounding a nonnegative number up gives a radius that is at least that number. This is
   all the proofs use of the computed constants and of abs_upper_2. *)
Lemma RU_radius : forall t, 0 <= t -> radius (RUp t) /\ t <= RUp t.
Proof.
intros t Ht.
assert (H1 : t <= RUp t).
{ destruct (round_UP_pt radix2 fexp t) as [_ [H _]]. exact H. }
assert (H2 : format (RUp t)).
{ apply generic_format_round; auto with typeclass_instances. }
unfold radius. split; [split|]; [exact H2 | lra | exact H1].
Qed.

(* The two computed constants, as functions of the relative part rel and of the absolute
   part tiny of a bound. *)
Definition unit_of (rel : R) : R := RUp (rel / (1 - rel)).
Definition tiny_of (rel tiny : R) : R := RUp (tiny / (1 - rel)).

Lemma unit_of_radius : forall rel, 0 <= rel < 1 -> radius (unit_of rel).
Proof.
intros rel Hrel.
exact (proj1 (RU_radius (rel / (1 - rel)) (div_pos rel rel (proj1 Hrel) Hrel))).
Qed.

Lemma tiny_of_radius : forall rel tiny, 0 <= rel < 1 -> 0 <= tiny -> radius (tiny_of rel tiny).
Proof.
intros rel tiny Hrel Ht.
exact (proj1 (RU_radius (tiny / (1 - rel)) (div_pos tiny rel Ht Hrel))).
Qed.

(* The relative part of the error of a center z, with mz an upper bound of |z|. *)
Lemma unit_of_bound :
  forall rel z mz, 0 <= rel < 1 -> Rabs z <= mz ->
  rel / (1 - rel) * Rabs z <= unit_of rel * mz.
Proof.
intros rel z mz Hrel Hm.
assert (Hd := div_pos rel rel (proj1 Hrel) Hrel).
assert (U1 : rel / (1 - rel) <= unit_of rel)
  by exact (proj2 (RU_radius (rel / (1 - rel)) Hd)).
apply Rle_trans with (rel / (1 - rel) * mz).
- apply Rmult_le_compat_l; assumption.
- apply Rmult_le_compat_r. apply Rle_trans with (2 := Hm). apply Rabs_pos. exact U1.
Qed.

(* The error of a center z, from the bound of its kernel relative to the exact value v:
   at most U mz + V with the computed constants. *)
Lemma center_bound :
  forall rel tiny z v mz, 0 <= rel < 1 -> 0 <= tiny ->
  Rabs (z - v) <= rel * Rabs v + tiny -> Rabs z <= mz ->
  Rabs (z - v) <= unit_of rel * mz + tiny_of rel tiny.
Proof.
intros rel tiny z v mz Hrel Ht H Hm.
apply Rle_trans with (1 := computed_bound rel tiny z v Hrel Ht H).
apply Rplus_le_compat.
- now apply unit_of_bound.
- exact (proj2 (RU_radius (tiny / (1 - rel)) (div_pos tiny rel Ht Hrel))).
Qed.

(* The same for a bound with no absolute part (the additions). *)
Lemma center_bound_rel :
  forall rel z v mz, 0 <= rel < 1 ->
  Rabs (z - v) <= rel * Rabs v -> Rabs z <= mz ->
  Rabs (z - v) <= unit_of rel * mz.
Proof.
intros rel z v mz Hrel H Hm.
assert (H' : Rabs (z - v) <= rel * Rabs v + 0) by lra.
assert (Hc := computed_bound rel 0 z v Hrel (Rle_refl 0) H').
replace (0 / (1 - rel)) with 0 in Hc by (unfold Rdiv; ring).
apply Rle_trans with (rel / (1 - rel) * Rabs z).
- lra.
- now apply unit_of_bound.
Qed.

(* The three radius computations: each chain of radd and rmul is at least the exact
   expression it stands for. U and V are the constants, mz the bound of |cz|. *)
Lemma sum_radius :
  forall U mz rx ry, radius U -> radius mz -> radius rx -> radius ry ->
  rx + ry + U * mz <= radd (radd rx ry) (rmul U mz).
Proof.
intros U mz rx ry Ru Rm Rx Ry.
destruct (rmul_radius U mz Ru Rm) as [Rd Hd].
destruct (radd_radius rx ry Rx Ry) as [R0 H0].
destruct (radd_radius _ _ R0 Rd) as [_ H].
lra.
Qed.

Lemma prod_radius :
  forall U V mz ax ay rx ry,
  radius U -> radius V -> radius mz -> radius ax -> radius ay -> radius rx -> radius ry ->
  ax * ry + ay * rx + rx * ry + (U * mz + V)
  <= radd (radd (radd (rmul ax ry) (rmul ay rx)) (rmul rx ry)) (radd (rmul U mz) V).
Proof.
intros U V mz ax ay rx ry Ru Rv Rm Rax Ray Rx Ry.
destruct (rmul_radius ax ry Rax Ry) as [R1 H1].
destruct (rmul_radius ay rx Ray Rx) as [R2 H2].
destruct (rmul_radius rx ry Rx Ry) as [R3 H3].
destruct (radd_radius _ _ R1 R2) as [R4 H4].
destruct (radd_radius _ _ R4 R3) as [R5 H5].
destruct (rmul_radius U mz Ru Rm) as [R6 H6].
destruct (radd_radius _ _ R6 Rv) as [R7 H7].
destruct (radd_radius _ _ R5 R7) as [_ H8].
lra.
Qed.

Lemma scale_radius :
  forall U V mz aa rx,
  radius U -> radius V -> radius mz -> radius aa -> radius rx ->
  aa * rx + (U * mz + V) <= radd (rmul aa rx) (radd (rmul U mz) V).
Proof.
intros U V mz aa rx Ru Rv Rm Raa Rx.
destruct (rmul_radius aa rx Raa Rx) as [R1 H1].
destruct (rmul_radius U mz Ru Rm) as [R6 H6].
destruct (radd_radius _ _ R6 Rv) as [R7 H7].
destruct (radd_radius _ _ R1 R7) as [_ H8].
lra.
Qed.

End Radius.

(** * The constants of the model *)

(* Each computed constant of proofs/gen/Model.v is, by definition, the rounding up of
   rel / (1 - rel) or tiny / (1 - rel), with rel and tiny the two parts of the bound in
   the generated statement of the center's kernel. These equalities hold by unfolding. *)
Lemma unit_add_1_1_eq : forall emin prec : Z,
  unit_computed_add_1_1 emin prec = unit_of emin prec (1 / (1 + u prec) * u prec ^ 1).
Proof. reflexivity. Qed.

Lemma unit_mul_1_1_eq : forall emin prec : Z,
  unit_computed_mul_1_1 emin prec = unit_of emin prec (1 / (1 + u prec) * u prec ^ 1).
Proof. reflexivity. Qed.

Lemma tiny_mul_1_1_eq : forall emin prec : Z,
  tiny_computed_mul_1_1 emin prec
  = tiny_of emin prec (1 / (1 + u prec) * u prec ^ 1) (1 / 2 * eta emin).
Proof. reflexivity. Qed.

Lemma unit_add_2_2_eq : forall emin prec : Z,
  unit_computed_add_2_2 emin prec = unit_of emin prec (3 / (1 - 4 * u prec) * u prec ^ 2).
Proof. reflexivity. Qed.

Lemma unit_mul_2_1_eq : forall emin prec : Z,
  unit_computed_mul_2_1 emin prec = unit_of emin prec (2 * u prec ^ 2).
Proof. reflexivity. Qed.

Lemma tiny_mul_2_1_eq : forall emin prec : Z,
  tiny_computed_mul_2_1 emin prec = tiny_of emin prec (2 * u prec ^ 2) (1 * eta emin).
Proof. reflexivity. Qed.

Lemma unit_mul_2_2_eq : forall emin prec : Z,
  unit_computed_mul_2_2 emin prec = unit_of emin prec (4 * u prec ^ 2).
Proof. reflexivity. Qed.

Lemma tiny_mul_2_2_eq : forall emin prec : Z,
  tiny_computed_mul_2_2 emin prec = tiny_of emin prec (4 * u prec ^ 2) (3 / 2 * eta emin).
Proof. reflexivity. Qed.

Lemma eta_ge_0 : forall (emin : Z) (t : R), 0 <= t -> 0 <= t * eta emin.
Proof. intros emin t Ht. apply Rmult_le_pos. exact Ht. apply bpow_ge_0. Qed.

(** * One-limb centers *)

(* The center is RN (cx + cy), with error at most u / (1 + u) |cx + cy| (add_1_1). *)
Theorem ball_add_1_correct : ball_add_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_add_1. cbv beta iota zeta. rewrite unit_add_1_1_eq.
intros x y Hx Hy.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx + cy)).
set (rel := 1 / (1 + u prec) * u prec ^ 1).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Fcz : generic_format radix2 (FLT_exp emin prec) cz).
{ unfold cz. apply generic_format_round; auto with typeclass_instances. }
assert (Rm : radius emin prec (Rabs cz)) by exact (radius_abs emin prec cz Fcz).
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ry : radius emin prec ry) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Hb : Rabs (cz - (cx + cy)) <= rel * Rabs (cx + cy))
  by exact (proj2 (add_1_1_correct emin prec Hp1 cx cy Fcx Fcy)).
assert (Hc : Rabs (cz - (cx + cy)) <= unit_of emin prec rel * Rabs cz)
  by exact (center_bound_rel emin prec rel cz (cx + cy) (Rabs cz) Hrel Hb (Rle_refl _)).
apply Rle_trans with (rx + ry + unit_of emin prec rel * Rabs cz).
- exact (enclose_add x y cx cy cz rx ry _ Hx Hy Hc).
- exact (sum_radius emin prec _ _ rx ry Ru Rm Rx Ry).
Qed.

(* x - y = x + (-y), and -y ranges over the ball of center -cy and radius ry. *)
Theorem ball_sub_1_correct : ball_sub_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
assert (Fn : fmt emin prec (- cy)).
{ unfold fmt in *. now apply generic_format_opp. }
unfold ball_sub_1. cbv zeta.
generalize (ball_add_1_correct emin prec Hp cx rx (- cy) ry Fcx Frx Fn Fry Hrx Hry).
destruct (ball_add_1 emin prec tie_even cx rx (- cy) ry) as [cz rz].
cbv beta iota.
intros H x y Hx Hy.
replace (x - y - cz) with (x + - y - cz) by ring.
apply H. exact Hx.
replace (- y - - cy) with (- (y - cy)) by ring. now rewrite Rabs_Ropp.
Qed.

(* Negation is exact: the center is -cx and the radius is unchanged. *)
Theorem ball_neg_1_correct : ball_neg_1_spec.
Proof.
intros emin prec Hp cx rx Fcx Frx Hrx.
unfold ball_neg_1. cbv beta iota zeta.
intros x Hx.
replace (- x - - cx) with (- (x - cx)) by ring. now rewrite Rabs_Ropp.
Qed.

(* The center is RN (cx cy), with error at most u / (1 + u) |cx cy| + eta / 2 (mul_1_1). *)
Theorem ball_mul_1_correct : ball_mul_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_mul_1. cbv beta iota zeta. rewrite unit_mul_1_1_eq, tiny_mul_1_1_eq.
intros x y Hx Hy.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx * cy + 0)).
set (rel := 1 / (1 + u prec) * u prec ^ 1).
set (tiny := 1 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
assert (Fcz : generic_format radix2 (FLT_exp emin prec) cz).
{ unfold cz. apply generic_format_round; auto with typeclass_instances. }
assert (Rm : radius emin prec (Rabs cz)) by exact (radius_abs emin prec cz Fcz).
assert (Rax : radius emin prec (Rabs cx)) by exact (radius_abs emin prec cx Fcx).
assert (Ray : radius emin prec (Rabs cy)) by exact (radius_abs emin prec cy Fcy).
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ry : radius emin prec ry) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Rv : radius emin prec (tiny_of emin prec rel tiny))
  by exact (tiny_of_radius emin prec rel tiny Hrel Htiny).
assert (Hb : Rabs (cz - cx * cy) <= rel * Rabs (cx * cy) + tiny)
  by exact (proj2 (mul_1_1_correct emin prec Hp1 cx cy Fcx Fcy)).
assert (Hc : Rabs (cz - cx * cy)
             <= unit_of emin prec rel * Rabs cz + tiny_of emin prec rel tiny)
  by exact (center_bound emin prec rel tiny cz (cx * cy) (Rabs cz) Hrel Htiny Hb (Rle_refl _)).
apply Rle_trans with (Rabs cx * ry + Rabs cy * rx + rx * ry
                      + (unit_of emin prec rel * Rabs cz + tiny_of emin prec rel tiny)).
- exact (enclose_mul x y cx cy cz rx ry (Rabs cx) (Rabs cy) _ Hx Hy
           (Rle_refl _) (Rle_refl _) Hc).
- exact (prod_radius emin prec _ _ _ _ _ rx ry Ru Rv Rm Rax Ray Rx Ry).
Qed.

(* The center is RN (cx a); a is a number, not a ball. *)
Theorem ball_scale_1_correct : ball_scale_1_spec.
Proof.
intros emin prec Hp cx rx a Fcx Frx Fa Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_scale_1. cbv beta iota zeta. rewrite unit_mul_1_1_eq, tiny_mul_1_1_eq.
intros x Hx.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx * a + 0)).
set (rel := 1 / (1 + u prec) * u prec ^ 1).
set (tiny := 1 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
assert (Fcz : generic_format radix2 (FLT_exp emin prec) cz).
{ unfold cz. apply generic_format_round; auto with typeclass_instances. }
assert (Rm : radius emin prec (Rabs cz)) by exact (radius_abs emin prec cz Fcz).
assert (Raa : radius emin prec (Rabs a)) by exact (radius_abs emin prec a Fa).
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Rv : radius emin prec (tiny_of emin prec rel tiny))
  by exact (tiny_of_radius emin prec rel tiny Hrel Htiny).
assert (Hb : Rabs (cz - cx * a) <= rel * Rabs (cx * a) + tiny)
  by exact (proj2 (mul_1_1_correct emin prec Hp1 cx a Fcx Fa)).
assert (Hc : Rabs (cz - cx * a)
             <= unit_of emin prec rel * Rabs cz + tiny_of emin prec rel tiny)
  by exact (center_bound emin prec rel tiny cz (cx * a) (Rabs cz) Hrel Htiny Hb (Rle_refl _)).
apply Rle_trans with (Rabs a * rx
                      + (unit_of emin prec rel * Rabs cz + tiny_of emin prec rel tiny)).
- exact (enclose_scale x a cx cz rx _ Hx Hc).
- exact (scale_radius emin prec _ _ _ (Rabs a) rx Ru Rv Rm Raa Rx).
Qed.

(** * Two-limb centers *)

(* The bound of |c| used for a 2-limb center: abs_upper_2 returns RU (|c0 + c1|), a
   radius that is at least |c0 + c1|. *)
Lemma abs_upper_2_radius :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall c0 c1 : R, normalized_2 emin prec c0 c1 ->
  radius emin prec (abs_upper_2 emin prec c0 c1) /\
  Rabs (c0 + c1) <= abs_upper_2 emin prec c0 c1.
Proof.
intros emin prec Hp c0 c1 Nc.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (E : abs_upper_2 emin prec c0 c1 = RU emin prec (Rabs (c0 + c1)))
  by exact (abs_upper_2_correct emin prec Hp c0 c1 Nc).
rewrite E. exact (RU_radius emin prec (Rabs (c0 + c1)) (Rabs_pos _)).
Qed.

(* The center is add_2_2 (cx, cy), with error at most 3 u^2 / (1 - 4u) |cx + cy|. *)
Theorem ball_add_2_correct : ball_add_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_add_2.
generalize (add_2_2_correct emin prec Hp cx0 cx1 cy0 cy1 Ncx Ncy).
destruct (add_2_2 emin prec tie_even cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. rewrite unit_add_2_2_eq.
intros [Ncz Hb]. split. exact Ncz.
intros x y Hx Hy.
set (rel := 3 / (1 - 4 * u prec) * u prec ^ 2).
set (mz := abs_upper_2 emin prec cz0 cz1).
assert (Hrel : 0 <= rel < 1) by exact (rel_add_2_2 prec Hp).
destruct (abs_upper_2_radius emin prec Hp1 cz0 cz1 Ncz) as [Rm Hm].
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ry : radius emin prec ry) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Hc : Rabs (cz0 + cz1 - (cx0 + cx1 + (cy0 + cy1))) <= unit_of emin prec rel * mz)
  by exact (center_bound_rel emin prec rel (cz0 + cz1) _ mz Hrel Hb Hm).
apply Rle_trans with (rx + ry + unit_of emin prec rel * mz).
- exact (enclose_add x y (cx0 + cx1) (cy0 + cy1) (cz0 + cz1) rx ry _ Hx Hy Hc).
- exact (sum_radius emin prec _ mz rx ry Ru Rm Rx Ry).
Qed.

Theorem ball_sub_2_correct : ball_sub_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
unfold ball_sub_2, neg_2. cbv zeta.
generalize (ball_add_2_correct emin prec Hp cx0 cx1 rx (- cy0) (- cy1) ry Ncx Frx
              (normalized_2_opp emin prec cy0 cy1 Ncy) Fry Hrx Hry).
cbv beta iota.
destruct (ball_add_2 emin prec tie_even cx0 cx1 rx (- cy0) (- cy1) ry) as [[cz0 cz1] rz].
cbv beta iota.
intros [Nz H]. split. exact Nz.
intros x y Hx Hy.
replace (x - y - (cz0 + cz1)) with (x + - y - (cz0 + cz1)) by ring.
apply H. exact Hx.
replace (- y - (- cy0 + - cy1)) with (- (y - (cy0 + cy1))) by ring. now rewrite Rabs_Ropp.
Qed.

Theorem ball_neg_2_correct : ball_neg_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx Ncx Frx Hrx.
unfold ball_neg_2, neg_2. cbv beta iota zeta.
split.
- now apply normalized_2_opp.
- intros x Hx.
  replace (- x - (- cx0 + - cx1)) with (- (x - (cx0 + cx1))) by ring. now rewrite Rabs_Ropp.
Qed.

(* The center is mul_2_2 (cx, cy), with error at most 4 u^2 |cx cy| + (3/2) eta. *)
Theorem ball_mul_2_correct : ball_mul_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_mul_2.
generalize (mul_2_2_correct emin prec Hp cx0 cx1 cy0 cy1 Ncx Ncy).
destruct (mul_2_2 emin prec tie_even cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. rewrite unit_mul_2_2_eq, tiny_mul_2_2_eq.
intros [Ncz Hb]. split. exact Ncz.
intros x y Hx Hy.
set (rel := 4 * u prec ^ 2).
set (tiny := 3 / 2 * eta emin).
set (ax := abs_upper_2 emin prec cx0 cx1).
set (ay := abs_upper_2 emin prec cy0 cy1).
set (mz := abs_upper_2 emin prec cz0 cz1).
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_2 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
destruct (abs_upper_2_radius emin prec Hp1 cx0 cx1 Ncx) as [Rax Hax].
destruct (abs_upper_2_radius emin prec Hp1 cy0 cy1 Ncy) as [Ray Hay].
destruct (abs_upper_2_radius emin prec Hp1 cz0 cz1 Ncz) as [Rm Hm].
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ry : radius emin prec ry) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Rv : radius emin prec (tiny_of emin prec rel tiny))
  by exact (tiny_of_radius emin prec rel tiny Hrel Htiny).
assert (Hc : Rabs (cz0 + cz1 - (cx0 + cx1) * (cy0 + cy1))
             <= unit_of emin prec rel * mz + tiny_of emin prec rel tiny)
  by exact (center_bound emin prec rel tiny (cz0 + cz1) _ mz Hrel Htiny Hb Hm).
apply Rle_trans with (ax * ry + ay * rx + rx * ry
                      + (unit_of emin prec rel * mz + tiny_of emin prec rel tiny)).
- exact (enclose_mul x y (cx0 + cx1) (cy0 + cy1) (cz0 + cz1) rx ry ax ay _ Hx Hy Hax Hay Hc).
- exact (prod_radius emin prec _ _ mz ax ay rx ry Ru Rv Rm Rax Ray Rx Ry).
Qed.

(* The center is mul_2_1 (cx, a), with error at most 2 u^2 |cx a| + eta. *)
Theorem ball_scale_2_correct : ball_scale_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx a Ncx Frx Fa Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold fmt in *.
unfold ball_scale_2.
generalize (mul_2_1_correct emin prec Hp cx0 cx1 a Ncx Fa).
destruct (mul_2_1 emin prec tie_even cx0 cx1 a) as [cz0 cz1].
cbv beta iota zeta. rewrite unit_mul_2_1_eq, tiny_mul_2_1_eq.
intros [Ncz Hb]. split. exact Ncz.
intros x Hx.
set (rel := 2 * u prec ^ 2).
set (tiny := 1 * eta emin).
set (mz := abs_upper_2 emin prec cz0 cz1).
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_1 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
destruct (abs_upper_2_radius emin prec Hp1 cz0 cz1 Ncz) as [Rm Hm].
assert (Raa : radius emin prec (Rabs a)) by exact (radius_abs emin prec a Fa).
assert (Rx : radius emin prec rx) by (unfold radius; split; assumption).
assert (Ru : radius emin prec (unit_of emin prec rel))
  by exact (unit_of_radius emin prec rel Hrel).
assert (Rv : radius emin prec (tiny_of emin prec rel tiny))
  by exact (tiny_of_radius emin prec rel tiny Hrel Htiny).
assert (Hc : Rabs (cz0 + cz1 - (cx0 + cx1) * a)
             <= unit_of emin prec rel * mz + tiny_of emin prec rel tiny)
  by exact (center_bound emin prec rel tiny (cz0 + cz1) _ mz Hrel Htiny Hb Hm).
apply Rle_trans with (Rabs a * rx
                      + (unit_of emin prec rel * mz + tiny_of emin prec rel tiny)).
- exact (enclose_scale x a (cx0 + cx1) (cz0 + cz1) rx _ Hx Hc).
- exact (scale_radius emin prec _ _ mz (Rabs a) rx Ru Rv Rm Raa Rx).
Qed.
