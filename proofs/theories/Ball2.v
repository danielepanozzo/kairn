(* The Ball cores of the second radius design (proofs/gen/Model.v): containment.

   A ball is a center c (one number of the format, or a normalized 2-limb number) and a
   radius r (a nonnegative number of the format). Each kernel computes the center as
   before and a radius that must be at least

       rx + ry + e                        (sum, difference)
       |cx| ry + |cy| rx + rx ry + e      (product)
       |a| rx + e                         (scaling by a)

   where e = |cz - (cx o cy)| is the error of the center (the triangle inequalities
   enclose_add, enclose_mul, enclose_scale below). In the first design every step of
   the radius was rounded up. Here the radius is evaluated by operations rounded to
   nearest, each of which may round down, and the last operation, rz = RN (t G + H),
   pays for all of them at once.

   One rounding. For a real number x >= 0, with u = 2^-prec and eta = 2^emin,

       x <= (1 + u) (RN (x) + eta / 2)                                    (rnd_lower)

   (Flocq's relative_error_N_FLT'_ex: RN (x) = x (1 + eps) + et with |eps| <= u / (1 + u),
   |et| <= eta / 2). So a rounding loses at most a factor 1 + u and eta / 2.

   A chain. If A <= K v + c and the next value is v' = RN (X + v) with X >= 0, then
   A + X <= K (1 + u) v' + (K (1 + u) eta / 2 + c) (chain_step). After the n rounded
   operations that lead to t, the exact value S of the expression t evaluates satisfies

       S <= (1 + u)^n t + n (1 + u)^n eta / 2            (chain2: n = 2, chain4: n = 4).

   The last operation. If B t + c is what is needed, then B t + c <= RN (t G + H) as
   soon as (1 + u) B <= G and (1 + u) (c + eta / 2) <= H (radius_tail).

   What is needed, in terms of S. The error of the center is at most Uq |cz| + Vq
   (computed_bound of Ball.v, with Uq = rel / (1 - rel), Vq = tiny / (1 - rel) from the
   bound rel |v| + tiny of the center's kernel), and |c| <= (1 + u) |c0| for a normalized
   pair (c0, c1). With k the number of limbs of the centers and kappa = (1 + u)^(k - 1):
   - sum: rx + ry + e <= S for S = rx + ry + E az, when E >= Uq kappa; n = 2;
   - scaling: |a| rx + e <= S + Vq for S = |a| rx + E az, when E >= Uq kappa; n = 2;
   - product: the needed radius is at most kappa S + Vq for
     S = ax ry + ay rx + rx ry + E az, when E >= Uq; n = 4.
   Putting the three steps together gives the constants of proofs/gen/Model.v:
     G >= (1 + u)^3 and H >= (1 + u) ((1 + u)^2 eta + Vq + eta / 2)         (sum, scaling)
     G >= kappa (1 + u)^5 and H >= (1 + u) (2 kappa (1 + u)^4 eta + Vq + eta / 2)  (product)
   The proofs use of E, G, H only that they are nonnegative and at least these
   expressions (lemmas radius_2 and radius_4); that they are rounded up to the format
   matters only to the kernels, which need them as numbers of the format.

   Each statement holds for every eta and from the minimum precision of the center's
   kernel: the radius computation adds no condition of its own.

   What is not claimed: that the radius is close to the smallest one. It exceeds the
   needed value by a factor of about (1 + u)^(n + 1) and a few eta. *)
From Stdlib Require Import Reals ZArith Lia Lra Psatz.
From Flocq Require Import Core Relative.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Add22 Mul22 Mul21 Sign OneLimb.
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

Lemma rel_square_R :
  forall c b t : R, 0 <= c -> 0 < t <= b -> c * (b * b) < 1 -> 0 <= c * t ^ 2 < 1.
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
Notation RUp := (round radix2 fexp Zceil).

(* A radius: a nonnegative number of the format. *)
Definition radius (r : R) : Prop := format r /\ 0 <= r.

Lemma RU_radius : forall t, 0 <= t -> radius (RUp t) /\ t <= RUp t.
Proof.
intros t Ht.
assert (H1 : t <= RUp t).
{ destruct (round_UP_pt radix2 fexp t) as [_ [H _]]. exact H. }
assert (H2 : format (RUp t)).
{ apply generic_format_round; auto with typeclass_instances. }
unfold radius. split; [split|]; [exact H2 | lra | exact H1].
Qed.

End Radius.

Lemma eta_ge_0 : forall (emin : Z) (t : R), 0 <= t -> 0 <= t * eta emin.
Proof. intros emin t Ht. apply Rmult_le_pos. exact Ht. apply bpow_ge_0. Qed.

(** * Negation *)

(* Negation is exact: the center is -cx and the radius is unchanged. *)
Theorem ball_neg_1_correct : ball_neg_1_spec.
Proof.
intros emin prec Hp cx rx Fcx Frx Hrx.
unfold ball_neg_1. cbv beta iota zeta.
split. limb_format.
split. exact Frx.
intros x Hx.
replace (- x - - cx) with (- (x - cx)) by ring. now rewrite Rabs_Ropp.
Qed.

Theorem ball_neg_2_correct : ball_neg_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx Ncx Frx Hrx.
unfold ball_neg_2, neg_2. cbv beta iota zeta.
split. exact Frx.
split.
- now apply normalized_2_opp.
- intros x Hx.
  replace (- x - (- cx0 + - cx1)) with (- (x - (cx0 + cx1))) by ring. now rewrite Rabs_Ropp.
Qed.


(** * Rounding to nearest, from below *)

Section Radius2.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation uu := (u prec).
Notation ee := (bpow radix2 emin).

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let e0 : 0 < ee.
Proof. apply bpow_gt_0. Qed.

Lemma rnd_ge_0 : forall x : R, 0 <= x -> 0 <= rnd x.
Proof.
intros x Hx. apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

Lemma rnd_lower : forall x : R, 0 <= x -> x <= (1 + uu) * (rnd x + ee / 2).
Proof.
intros x Hx.
destruct (relative_error_N_FLT'_ex radix2 emin prec prec_gt_0_ tie_even x)
  as [eps [et [He [Ht [_ Hr]]]]].
rewrite u_ro_eq in He. rewrite Hr.
set (d := uu / (1 + uu)) in *.
apply Rabs_le_inv in He. apply Rabs_le_inv in Ht.
assert (K2 : (1 + uu) * (1 - d) = 1) by (unfold d; field; lra).
assert (K1 : x * (1 - d) <= x * (1 + eps)) by (apply Rmult_le_compat_l; lra).
apply Rle_trans with ((1 + uu) * (x * (1 - d))).
- replace ((1 + uu) * (x * (1 - d))) with (x * ((1 + uu) * (1 - d))) by ring. rewrite K2. lra.
- apply Rmult_le_compat_l; lra.
Qed.

(* The last operation of a radius. *)
Lemma radius_tail :
  forall t G H B c : R, 0 <= t -> 0 <= G -> 0 <= H ->
  (1 + uu) * B <= G -> (1 + uu) * (c + ee / 2) <= H ->
  B * t + c <= rnd (t * G + H).
Proof.
intros t G H B c Ht HG HH HB Hc.
assert (P : 0 <= t * G + H) by (generalize (Rmult_le_pos t G Ht HG); lra).
generalize (rnd_lower (t * G + H) P). intros K.
assert (K1 : (1 + uu) * B * t <= G * t) by (apply Rmult_le_compat_r; assumption).
apply Rmult_le_reg_l with (1 + uu). lra. nra.
Qed.

(* One more rounded operation in a chain. *)
Lemma chain_step :
  forall A X v K c : R, 0 <= X -> 0 <= v -> 1 <= K ->
  A <= K * v + c ->
  A + X <= K * (1 + uu) * rnd (X + v) + (K * (1 + uu) * (ee / 2) + c).
Proof.
intros A X v K c HX Hv HK HA.
assert (P : 0 <= X + v) by lra.
generalize (rnd_lower (X + v) P). intros L.
assert (K1 : K * (X + v) <= K * ((1 + uu) * (rnd (X + v) + ee / 2)))
  by (apply Rmult_le_compat_l; lra).
assert (K2 : X <= K * X) by nra.
nra.
Qed.

Lemma chain2 :
  forall X Y : R, 0 <= X -> 0 <= Y ->
  X + Y <= (1 + uu) ^ 2 * rnd (Y + rnd X) + (1 + uu) ^ 2 * ee.
Proof.
intros X Y HX HY.
set (o := 1 + uu). assert (O1 : 1 <= o) by (unfold o; lra).
set (v1 := rnd X). set (v2 := rnd (Y + v1)).
assert (P1 : 0 <= v1) by now apply rnd_ge_0.
assert (S1 : X <= o * v1 + o * (ee / 2)) by (generalize (rnd_lower X HX); fold v1 o; lra).
assert (S2 := chain_step X Y v1 o (o * (ee / 2)) HY P1 O1 S1). fold o v2 in S2.
assert (Q : o * (ee / 2) <= o * o * (ee / 2)) by (apply Rmult_le_compat_r; nra).
replace (o ^ 2) with (o * o) by ring. lra.
Qed.

Lemma chain4 :
  forall X1 X2 X3 X4 : R, 0 <= X1 -> 0 <= X2 -> 0 <= X3 -> 0 <= X4 ->
  X1 + X2 + X3 + X4
  <= (1 + uu) ^ 4 * rnd (X4 + rnd (X3 + rnd (X2 + rnd X1))) + 2 * (1 + uu) ^ 4 * ee.
Proof.
intros X1 X2 X3 X4 H1 H2 H3 H4.
set (o := 1 + uu). assert (O1 : 1 <= o) by (unfold o; lra).
set (v1 := rnd X1). set (v2 := rnd (X2 + v1)). set (v3 := rnd (X3 + v2)).
set (v4 := rnd (X4 + v3)).
assert (P1 : 0 <= v1) by now apply rnd_ge_0.
assert (P2 : 0 <= v2) by (apply rnd_ge_0; lra).
assert (P3 : 0 <= v3) by (apply rnd_ge_0; lra).
assert (S1 : X1 <= o * v1 + o * (ee / 2)) by (generalize (rnd_lower X1 H1); fold v1 o; lra).
assert (S2 := chain_step X1 X2 v1 o (o * (ee / 2)) H2 P1 O1 S1). fold o v2 in S2.
assert (O2 : 1 <= o * o) by nra.
assert (S3 := chain_step (X1 + X2) X3 v2 (o * o) _ H3 P2 O2 S2). fold o v3 in S3.
assert (O3 : 1 <= o * o * o) by nra.
assert (S4 := chain_step (X1 + X2 + X3) X4 v3 (o * o * o) _ H4 P3 O3 S3). fold o v4 in S4.
assert (Q2 : o <= o * o * o * o) by nra.
assert (Q3 : o * o <= o * o * o * o) by nra.
assert (Q4 : o * o * o <= o * o * o * o) by nra.
assert (Z2 : o * (ee / 2) <= o * o * o * o * (ee / 2)) by (apply Rmult_le_compat_r; lra).
assert (Z3 : o * o * (ee / 2) <= o * o * o * o * (ee / 2)) by (apply Rmult_le_compat_r; lra).
assert (Z4 : o * o * o * (ee / 2) <= o * o * o * o * (ee / 2)) by (apply Rmult_le_compat_r; lra).
replace (o ^ 4) with (o * o * o * o) by ring. lra.
Qed.

(* The radius of a sum (V = 0) or of a scaling: X is rx + ry or |a| rx, e the error of
   the center, az the magnitude of its leading limb. *)
Lemma radius_2 :
  forall X az E G H e V : R,
  0 <= X -> 0 <= az -> 0 <= E -> 0 <= G -> 0 <= H ->
  e <= E * az + V ->
  (1 + uu) ^ 3 <= G ->
  (1 + uu) * ((1 + uu) ^ 2 * ee + V + ee / 2) <= H ->
  X + e <= rnd (rnd (az * E + rnd X) * G + H).
Proof.
intros X az E G H e V HX Haz HE HG HH He HGl HHl.
assert (PY : 0 <= az * E) by now apply Rmult_le_pos.
generalize (chain2 X (az * E) HX PY). intros C2.
set (t := rnd (az * E + rnd X)) in *.
assert (Pt : 0 <= t).
{ unfold t. apply rnd_ge_0. generalize (rnd_ge_0 X HX). lra. }
assert (T1 : (1 + uu) * (1 + uu) ^ 2 <= G).
{ replace ((1 + uu) * (1 + uu) ^ 2) with ((1 + uu) ^ 3) by ring. exact HGl. }
generalize (radius_tail t G H ((1 + uu) ^ 2) ((1 + uu) ^ 2 * ee + V) Pt HG HH T1 HHl).
lra.
Qed.

(* The radius of a product: ax, ay, az are the magnitudes of the leading limbs, cxa and
   cya those of the centers, at most K times as large. *)
Lemma radius_4 :
  forall ax ay az rx ry cxa cya E G H e V K : R,
  0 <= ax -> 0 <= ay -> 0 <= az -> 0 <= rx -> 0 <= ry -> 0 <= E -> 0 <= G -> 0 <= H ->
  1 <= K -> cxa <= K * ax -> cya <= K * ay ->
  e <= K * (E * az) + V ->
  K * (1 + uu) ^ 5 <= G ->
  (1 + uu) * (2 * K * (1 + uu) ^ 4 * ee + V + ee / 2) <= H ->
  cxa * ry + cya * rx + rx * ry + e
  <= rnd (rnd (az * E + rnd (ax * ry + rnd (ay * rx + rnd (rx * ry)))) * G + H).
Proof.
intros ax ay az rx ry cxa cya E G H e V K Hax Hay Haz Hrx Hry HE HG HH HK Hcx Hcy He HGl HHl.
assert (P1 : 0 <= rx * ry) by now apply Rmult_le_pos.
assert (P2 : 0 <= ay * rx) by now apply Rmult_le_pos.
assert (P3 : 0 <= ax * ry) by now apply Rmult_le_pos.
assert (P4 : 0 <= az * E) by now apply Rmult_le_pos.
generalize (chain4 (rx * ry) (ay * rx) (ax * ry) (az * E) P1 P2 P3 P4). intros C4.
assert (Q1 : 0 <= rnd (rx * ry)) by now apply rnd_ge_0.
assert (Q2 : 0 <= rnd (ay * rx + rnd (rx * ry))) by (apply rnd_ge_0; lra).
assert (Q3 : 0 <= rnd (ax * ry + rnd (ay * rx + rnd (rx * ry)))) by (apply rnd_ge_0; lra).
set (t := rnd (az * E + rnd (ax * ry + rnd (ay * rx + rnd (rx * ry))))) in *.
assert (Pt : 0 <= t) by (unfold t; apply rnd_ge_0; lra).
assert (T1 : (1 + uu) * (K * (1 + uu) ^ 4) <= G).
{ replace ((1 + uu) * (K * (1 + uu) ^ 4)) with (K * (1 + uu) ^ 5) by ring. exact HGl. }
generalize (radius_tail t G H (K * (1 + uu) ^ 4) (2 * K * (1 + uu) ^ 4 * ee + V) Pt HG HH T1 HHl).
intros T.
assert (N1 : cxa * ry <= K * (ax * ry)).
{ rewrite <- Rmult_assoc. now apply Rmult_le_compat_r. }
assert (N2 : cya * rx <= K * (ay * rx)).
{ rewrite <- Rmult_assoc. now apply Rmult_le_compat_r. }
assert (N3 : rx * ry <= K * (rx * ry)) by nra.
assert (N4 : K * (rx * ry + ay * rx + ax * ry + az * E)
             <= K * ((1 + uu) ^ 4 * t + 2 * (1 + uu) ^ 4 * ee))
  by (apply Rmult_le_compat_l; lra).
nra.
Qed.

(* The magnitude of a normalized pair, from that of its leading limb. *)
Lemma normalized_2_abs_le :
  forall x0 x1 : R, normalized_2 emin prec x0 x1 -> Rabs (x0 + x1) <= (1 + uu) * Rabs x0.
Proof.
intros x0 x1 N. generalize (normalized_2_tail_rel emin prec x0 x1 N). intros T.
apply Rle_trans with (1 := Rabs_triang _ _). lra.
Qed.

(* A nonnegative expression rounded up: nonnegative, and at least the expression. *)
Lemma RU_ge : forall t : R, 0 <= t -> 0 <= RU emin prec t /\ t <= RU emin prec t.
Proof.
intros t Ht. destruct (RU_radius emin prec t Ht) as [[_ P] L]. split; assumption.
Qed.

Lemma pow_ge_0' : forall n : nat, 0 <= (1 + uu) ^ n.
Proof. intros n. apply pow_le. lra. Qed.

End Radius2.

(** * The constants of proofs/gen/Model.v *)

(* Each is, by definition, the rounding up of the expression of the table of
   proofs/gen/Model.v, with u and eta spelled out. These equalities hold by unfolding. *)
Definition uq (rel : R) : R := rel / (1 - rel).
Definition vq (rel tiny : R) : R := tiny / (1 - rel).

Definition h2 (emin prec : Z) (V : R) : R :=
  (1 + u prec) * ((1 + u prec) ^ 2 * eta emin + V + eta emin / 2).
Definition h4 (emin prec : Z) (n : nat) (V : R) : R :=
  (1 + u prec) * (2 * (1 + u prec) ^ n * eta emin + V + eta emin / 2).

Lemma uq_ge_0 : forall rel : R, 0 <= rel < 1 -> 0 <= uq rel.
Proof. intros rel H. exact (div_pos rel rel (proj1 H) H). Qed.

Lemma vq_ge_0 : forall rel tiny : R, 0 <= rel < 1 -> 0 <= tiny -> 0 <= vq rel tiny.
Proof. intros rel tiny H Ht. exact (div_pos tiny rel Ht H). Qed.

Lemma h2_ge_0 : forall emin prec V, 0 <= V -> 0 <= h2 emin prec V.
Proof.
intros emin prec V HV. unfold h2, eta.
generalize (bpow_gt_0 radix2 (- prec)) (bpow_gt_0 radix2 emin). unfold u. intros U0 E0.
apply Rmult_le_pos. lra.
assert (0 <= (1 + bpow radix2 (- prec)) ^ 2 * bpow radix2 emin).
{ apply Rmult_le_pos. apply pow_le. lra. lra. }
lra.
Qed.

Lemma h4_ge_0 : forall emin prec n V, 0 <= V -> 0 <= h4 emin prec n V.
Proof.
intros emin prec n V HV. unfold h4, eta.
generalize (bpow_gt_0 radix2 (- prec)) (bpow_gt_0 radix2 emin). unfold u. intros U0 E0.
apply Rmult_le_pos. lra.
assert (0 <= 2 * (1 + bpow radix2 (- prec)) ^ n * bpow radix2 emin).
{ apply Rmult_le_pos. apply Rmult_le_pos. lra. apply pow_le. lra. lra. }
lra.
Qed.

Notation rel_1 prec := (1 / (1 + u prec) * u prec ^ 1).
Notation rel_add_2 prec := (3 / (1 - 4 * u prec) * u prec ^ 2).
Notation rel_mul_21 prec := (2 * u prec ^ 2).
Notation rel_mul_22 prec := (4 * u prec ^ 2).

Lemma e_add_1_eq : forall emin prec : Z,
  Model.up_ball_add_1_0 emin prec = RU emin prec (uq (rel_1 prec)).
Proof. reflexivity. Qed.
Lemma g_add_1_eq : forall emin prec : Z,
  Model.up_ball_add_1_1 emin prec = RU emin prec ((1 + u prec) ^ 3).
Proof. reflexivity. Qed.
Lemma h_add_1_eq : forall emin prec : Z,
  Model.up_ball_add_1_2 emin prec
  = RU emin prec ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2)).
Proof. reflexivity. Qed.

Lemma e_add_2_eq : forall emin prec : Z,
  Model.up_ball_add_2_0 emin prec = RU emin prec (uq (rel_add_2 prec) * (1 + u prec)).
Proof. reflexivity. Qed.
Lemma g_add_2_eq : forall emin prec : Z,
  Model.up_ball_add_1_1 emin prec = RU emin prec ((1 + u prec) ^ 3).
Proof. reflexivity. Qed.
Lemma h_add_2_eq : forall emin prec : Z,
  Model.up_ball_add_1_2 emin prec
  = RU emin prec ((1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2)).
Proof. reflexivity. Qed.

Lemma e_scale_1_eq : forall emin prec : Z,
  Model.up_ball_mul_1_0 emin prec = RU emin prec (uq (rel_1 prec)).
Proof. reflexivity. Qed.
Lemma g_scale_1_eq : forall emin prec : Z,
  Model.up_ball_add_1_1 emin prec = RU emin prec ((1 + u prec) ^ 3).
Proof. reflexivity. Qed.
Lemma h_scale_1_eq : forall emin prec : Z,
  Model.up_ball_scale_1_2 emin prec
  = RU emin prec (h2 emin prec (vq (rel_1 prec) (1 / 2 * eta emin))).
Proof. reflexivity. Qed.

Lemma e_scale_2_eq : forall emin prec : Z,
  Model.up_ball_scale_2_0 emin prec
  = RU emin prec (uq (rel_mul_21 prec) * (1 + u prec)).
Proof. reflexivity. Qed.
Lemma g_scale_2_eq : forall emin prec : Z,
  Model.up_ball_add_1_1 emin prec = RU emin prec ((1 + u prec) ^ 3).
Proof. reflexivity. Qed.
Lemma h_scale_2_eq : forall emin prec : Z,
  Model.up_ball_scale_2_2 emin prec
  = RU emin prec (h2 emin prec (vq (rel_mul_21 prec) (1 * eta emin))).
Proof. reflexivity. Qed.

Lemma e_mul_1_eq : forall emin prec : Z,
  Model.up_ball_mul_1_0 emin prec = RU emin prec (uq (rel_1 prec)).
Proof. reflexivity. Qed.
Lemma g_mul_1_eq : forall emin prec : Z,
  Model.up_ball_mul_1_1 emin prec = RU emin prec ((1 + u prec) ^ 5).
Proof. reflexivity. Qed.
Lemma h_mul_1_eq : forall emin prec : Z,
  Model.up_ball_mul_1_2 emin prec
  = RU emin prec (h4 emin prec 4 (vq (rel_1 prec) (1 / 2 * eta emin))).
Proof. reflexivity. Qed.

Lemma e_mul_2_eq : forall emin prec : Z,
  Model.up_ball_mul_2_0 emin prec = RU emin prec (uq (rel_mul_22 prec)).
Proof. reflexivity. Qed.
Lemma g_mul_2_eq : forall emin prec : Z,
  Model.up_ball_mul_2_1 emin prec = RU emin prec ((1 + u prec) ^ 6).
Proof. reflexivity. Qed.
Lemma h_mul_2_eq : forall emin prec : Z,
  Model.up_ball_mul_2_2 emin prec
  = RU emin prec (h4 emin prec 5 (vq (rel_mul_22 prec) (3 / 2 * eta emin))).
Proof. reflexivity. Qed.

(** * One-limb centers *)

(* The center is RN (cx + cy), with error at most u / (1 + u) |cx + cy| (add_1_1). *)
Theorem ball_add_1_correct : Statements.ball_add_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold fmt in *.
unfold Model.ball_add_1. cbv beta iota zeta.
split. limb_format. split. limb_format.
intros x y Hx Hy.
rewrite e_add_1_eq, g_add_1_eq, h_add_1_eq.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx + cy)).
set (rel := rel_1 prec).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hb : Rabs (cz - (cx + cy)) <= rel * Rabs (cx + cy) + 0).
{ rewrite Rplus_0_r. exact (proj2 (proj2 (add_1_1_correct emin prec Hp cx cy Fcx Fcy))). }
generalize (computed_bound rel 0 cz (cx + cy) Hrel (Rle_refl 0) Hb). fold (uq rel).
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros Hc.
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
assert (H2 : (1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2) = h2 emin prec 0)
  by (unfold h2; ring).
rewrite H2.
destruct (RU_ge emin prec (h2 emin prec 0) (h2_ge_0 emin prec 0 (Rle_refl 0))) as [H0 H1].
apply Rle_trans with (rx + ry + Rabs (cz - (cx + cy))).
- exact (enclose_add x y cx cy cz rx ry _ Hx Hy (Rle_refl _)).
- apply (radius_2 emin prec (rx + ry) (Rabs cz) _ _ _ _ 0);
    [lra|apply Rabs_pos|exact E0|exact G0|exact H0| |exact G1|exact H1].
  generalize (Rabs_pos cz). intros A0.
  assert (uq rel * Rabs cz <= RU emin prec (uq rel) * Rabs cz)
    by (apply Rmult_le_compat_r; assumption).
  lra.
Qed.

(* x - y = x + (-y), and -y ranges over the ball of center -cy and radius ry. *)
Theorem ball_sub_1_correct : Statements.ball_sub_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
unfold Model.ball_sub_1. cbv zeta.
assert (Fn : fmt emin prec (- cy)) by (unfold fmt in *; now apply generic_format_opp).
generalize (ball_add_1_correct emin prec Hp cx rx (- cy) ry Fcx Frx Fn Fry Hrx Hry).
destruct (Model.ball_add_1 emin prec tie_even cx rx (- cy) ry) as [cz rz].
cbv beta iota. intros [Fcz [Frz H]]. split. exact Fcz. split. exact Frz.
intros x y Hx Hy.
replace (x - y - cz) with (x + - y - cz) by ring.
apply H. exact Hx.
replace (- y - - cy) with (- (y - cy)) by ring. now rewrite Rabs_Ropp.
Qed.

(* The center is RN (cx cy), with error at most u / (1 + u) |cx cy| + eta / 2 (mul_1_1). *)
Theorem ball_mul_1_correct : Statements.ball_mul_1_spec.
Proof.
intros emin prec Hp cx rx cy ry Fcx Frx Fcy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold fmt in *.
unfold Model.ball_mul_1. cbv beta iota zeta.
split. limb_format. split. limb_format.
intros x y Hx Hy.
rewrite e_mul_1_eq, g_mul_1_eq, h_mul_1_eq.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx * cy + 0)).
rewrite (Rplus_0_r (rx * ry)).
set (rel := rel_1 prec). set (tiny := 1 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hb : Rabs (cz - cx * cy) <= rel * Rabs (cx * cy) + tiny)
  by exact (proj2 (proj2 (mul_1_1_correct emin prec Hp cx cy Fcx Fcy))).
generalize (computed_bound rel tiny cz (cx * cy) Hrel Htiny Hb). fold (uq rel) (vq rel tiny).
intros Hc.
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 5) (pow_ge_0' prec 5)) as [G0 G1].
destruct (RU_ge emin prec (h4 emin prec 4 (vq rel tiny))
            (h4_ge_0 emin prec 4 _ (vq_ge_0 rel tiny Hrel Htiny))) as [H0 H1].
apply Rle_trans with (Rabs cx * ry + Rabs cy * rx + rx * ry + Rabs (cz - cx * cy)).
- exact (enclose_mul x y cx cy cz rx ry (Rabs cx) (Rabs cy) _ Hx Hy
           (Rle_refl _) (Rle_refl _) (Rle_refl _)).
- apply (radius_4 emin prec (Rabs cx) (Rabs cy) (Rabs cz) rx ry (Rabs cx) (Rabs cy)
           _ _ _ _ (vq rel tiny) 1);
    [apply Rabs_pos|apply Rabs_pos|apply Rabs_pos|exact Hrx|exact Hry|exact E0|exact G0|exact H0
    |lra|lra|lra| |lra|unfold h4, eta in *; lra].
  generalize (Rabs_pos cz). intros A0.
  assert (uq rel * Rabs cz <= RU emin prec (uq rel) * Rabs cz)
    by (apply Rmult_le_compat_r; assumption).
  lra.
Qed.

(* The center is RN (cx a); a is a number, not a ball. *)
Theorem ball_scale_1_correct : Statements.ball_scale_1_spec.
Proof.
intros emin prec Hp cx rx a Fcx Frx Fa Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold fmt in *.
unfold Model.ball_scale_1. cbv beta iota zeta.
split. limb_format. split. limb_format.
intros x Hx.
rewrite e_scale_1_eq, g_scale_1_eq, h_scale_1_eq.
set (cz := round radix2 (FLT_exp emin prec) (Znearest tie_even) (cx * a + 0)).
rewrite (Rplus_0_r (Rabs a * rx)).
set (rel := rel_1 prec). set (tiny := 1 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hb : Rabs (cz - cx * a) <= rel * Rabs (cx * a) + tiny)
  by exact (proj2 (proj2 (mul_1_1_correct emin prec Hp cx a Fcx Fa))).
generalize (computed_bound rel tiny cz (cx * a) Hrel Htiny Hb). fold (uq rel) (vq rel tiny).
intros Hc.
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
destruct (RU_ge emin prec (h2 emin prec (vq rel tiny))
            (h2_ge_0 emin prec _ (vq_ge_0 rel tiny Hrel Htiny))) as [H0 H1].
apply Rle_trans with (Rabs a * rx + Rabs (cz - cx * a)).
- exact (enclose_scale x a cx cz rx _ Hx (Rle_refl _)).
- apply (radius_2 emin prec (Rabs a * rx) (Rabs cz) _ _ _ _ (vq rel tiny));
    [apply Rmult_le_pos; [apply Rabs_pos|exact Hrx]|apply Rabs_pos|exact E0|exact G0|exact H0|
    |exact G1|exact H1].
  generalize (Rabs_pos cz). intros A0.
  assert (uq rel * Rabs cz <= RU emin prec (uq rel) * Rabs cz)
    by (apply Rmult_le_compat_r; assumption).
  lra.
Qed.

(** * Two-limb centers *)

(* The center is add_2_2 (cx, cy), with error at most 3 u^2 / (1 - 4u) |cx + cy|. *)
Theorem ball_add_2_correct : Statements.ball_add_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold fmt in *.
unfold Model.ball_add_2.
generalize (add_2_2_correct emin prec Hp cx0 cx1 cy0 cy1 Ncx Ncy).
destruct (add_2_2 emin prec tie_even cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. intros [Ncz Hb].
split. limb_format. split. exact Ncz.
intros x y Hx Hy.
rewrite e_add_2_eq, g_add_2_eq, h_add_2_eq.
set (rel := rel_add_2 prec).
assert (Hrel : 0 <= rel < 1) by exact (rel_add_2_2 prec Hp).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
set (e := Rabs (cz0 + cz1 - (cx0 + cx1 + (cy0 + cy1)))) in *.
assert (Hb' : e <= rel * Rabs (cx0 + cx1 + (cy0 + cy1)) + 0) by (rewrite Rplus_0_r; exact Hb).
generalize (computed_bound rel 0 (cz0 + cz1) _ Hrel (Rle_refl 0) Hb'). fold (uq rel). fold e.
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros Hc.
generalize (normalized_2_abs_le emin prec cz0 cz1 Ncz). intros Hz.
assert (P : 0 <= uq rel * (1 + u prec)).
{ apply Rmult_le_pos. now apply uq_ge_0. lra. }
destruct (RU_ge emin prec (uq rel * (1 + u prec)) P) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
assert (H2 : (1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2) = h2 emin prec 0)
  by (unfold h2; ring).
rewrite H2.
destruct (RU_ge emin prec (h2 emin prec 0) (h2_ge_0 emin prec 0 (Rle_refl 0))) as [H0 H1].
apply Rle_trans with (rx + ry + e).
- exact (enclose_add x y (cx0 + cx1) (cy0 + cy1) (cz0 + cz1) rx ry _ Hx Hy (Rle_refl _)).
- apply (radius_2 emin prec (rx + ry) (Rabs cz0) _ _ _ _ 0);
    [lra|apply Rabs_pos|exact E0|exact G0|exact H0| |exact G1|exact H1].
  generalize (Rabs_pos cz0) (uq_ge_0 rel Hrel). intros A0 Q0.
  assert (K1 : uq rel * Rabs (cz0 + cz1) <= uq rel * ((1 + u prec) * Rabs cz0))
    by (apply Rmult_le_compat_l; assumption).
  assert (K2 : uq rel * (1 + u prec) * Rabs cz0
               <= RU emin prec (uq rel * (1 + u prec)) * Rabs cz0)
    by (apply Rmult_le_compat_r; assumption).
  lra.
Qed.

Theorem ball_sub_2_correct : Statements.ball_sub_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
unfold Model.ball_sub_2, neg_2. cbv zeta.
generalize (ball_add_2_correct emin prec Hp cx0 cx1 rx (- cy0) (- cy1) ry Ncx Frx
              (normalized_2_opp emin prec cy0 cy1 Ncy) Fry Hrx Hry).
cbv beta iota.
destruct (Model.ball_add_2 emin prec tie_even cx0 cx1 rx (- cy0) (- cy1) ry) as [[cz0 cz1] rz].
cbv beta iota.
intros [Frz [Nz H]]. split. exact Frz. split. exact Nz.
intros x y Hx Hy.
replace (x - y - (cz0 + cz1)) with (x + - y - (cz0 + cz1)) by ring.
apply H. exact Hx.
replace (- y - (- cy0 + - cy1)) with (- (y - (cy0 + cy1))) by ring. now rewrite Rabs_Ropp.
Qed.

(* The center is mul_2_2 (cx, cy), with error at most 4 u^2 |cx cy| + (3/2) eta. *)
Theorem ball_mul_2_correct : Statements.ball_mul_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx cy0 cy1 ry Ncx Frx Ncy Fry Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
unfold fmt in *.
unfold Model.ball_mul_2.
generalize (mul_2_2_correct emin prec Hp cx0 cx1 cy0 cy1 Ncx Ncy).
destruct (mul_2_2 emin prec tie_even cx0 cx1 cy0 cy1) as [cz0 cz1].
cbv beta iota zeta. intros [Ncz Hb].
split. limb_format. split. exact Ncz.
intros x y Hx Hy.
rewrite e_mul_2_eq, g_mul_2_eq, h_mul_2_eq. rewrite (Rplus_0_r (rx * ry)).
set (rel := rel_mul_22 prec). set (tiny := 3 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_2 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
set (e := Rabs (cz0 + cz1 - (cx0 + cx1) * (cy0 + cy1))) in *.
generalize (computed_bound rel tiny (cz0 + cz1) _ Hrel Htiny Hb). fold (uq rel) (vq rel tiny). fold e.
intros Hc.
generalize (normalized_2_abs_le emin prec cz0 cz1 Ncz) (normalized_2_abs_le emin prec cx0 cx1 Ncx)
           (normalized_2_abs_le emin prec cy0 cy1 Ncy). intros Hz Hcx Hcy.
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 6) (pow_ge_0' prec 6)) as [G0 G1].
destruct (RU_ge emin prec (h4 emin prec 5 (vq rel tiny))
            (h4_ge_0 emin prec 5 _ (vq_ge_0 rel tiny Hrel Htiny))) as [H0 H1].
apply Rle_trans with (Rabs (cx0 + cx1) * ry + Rabs (cy0 + cy1) * rx + rx * ry + e).
- exact (enclose_mul x y (cx0 + cx1) (cy0 + cy1) (cz0 + cz1) rx ry _ _ _ Hx Hy
           (Rle_refl _) (Rle_refl _) (Rle_refl _)).
- apply (radius_4 emin prec (Rabs cx0) (Rabs cy0) (Rabs cz0) rx ry
           (Rabs (cx0 + cx1)) (Rabs (cy0 + cy1)) _ _ _ _ (vq rel tiny) (1 + u prec));
    [apply Rabs_pos|apply Rabs_pos|apply Rabs_pos|exact Hrx|exact Hry|exact E0|exact G0|exact H0
    |lra|exact Hcx|exact Hcy| | | ].
  + generalize (Rabs_pos cz0) (uq_ge_0 rel Hrel). intros A0 Q0.
    assert (K1 : uq rel * Rabs (cz0 + cz1) <= uq rel * ((1 + u prec) * Rabs cz0))
      by (apply Rmult_le_compat_l; assumption).
    assert (K2 : uq rel * Rabs cz0 <= RU emin prec (uq rel) * Rabs cz0)
      by (apply Rmult_le_compat_r; assumption).
    assert (K3 : (1 + u prec) * (uq rel * Rabs cz0)
                 <= (1 + u prec) * (RU emin prec (uq rel) * Rabs cz0))
      by (apply Rmult_le_compat_l; lra).
    lra.
  + replace ((1 + u prec) * (1 + u prec) ^ 5) with ((1 + u prec) ^ 6) by ring. exact G1.
  + replace (2 * (1 + u prec) * (1 + u prec) ^ 4) with (2 * (1 + u prec) ^ 5) by ring. exact H1.
Qed.

(* The center is mul_2_1 (cx, a), with error at most 2 u^2 |cx a| + eta. *)
Theorem ball_scale_2_correct : Statements.ball_scale_2_spec.
Proof.
intros emin prec Hp cx0 cx1 rx a Ncx Frx Fa Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold fmt in *.
unfold Model.ball_scale_2.
generalize (mul_2_1_correct emin prec Hp cx0 cx1 a Ncx Fa).
destruct (mul_2_1 emin prec tie_even cx0 cx1 a) as [cz0 cz1].
cbv beta iota zeta. intros [Ncz Hb].
split. limb_format. split. exact Ncz.
intros x Hx.
rewrite e_scale_2_eq, g_scale_2_eq, h_scale_2_eq. rewrite (Rplus_0_r (Rabs a * rx)).
set (rel := rel_mul_21 prec). set (tiny := 1 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_1 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
set (e := Rabs (cz0 + cz1 - (cx0 + cx1) * a)) in *.
generalize (computed_bound rel tiny (cz0 + cz1) _ Hrel Htiny Hb). fold (uq rel) (vq rel tiny). fold e.
intros Hc.
generalize (normalized_2_abs_le emin prec cz0 cz1 Ncz). intros Hz.
assert (P : 0 <= uq rel * (1 + u prec)).
{ apply Rmult_le_pos. now apply uq_ge_0. lra. }
destruct (RU_ge emin prec (uq rel * (1 + u prec)) P) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
destruct (RU_ge emin prec (h2 emin prec (vq rel tiny))
            (h2_ge_0 emin prec _ (vq_ge_0 rel tiny Hrel Htiny))) as [H0 H1].
apply Rle_trans with (Rabs a * rx + e).
- exact (enclose_scale x a (cx0 + cx1) (cz0 + cz1) rx _ Hx (Rle_refl _)).
- apply (radius_2 emin prec (Rabs a * rx) (Rabs cz0) _ _ _ _ (vq rel tiny));
    [apply Rmult_le_pos; [apply Rabs_pos|exact Hrx]|apply Rabs_pos|exact E0|exact G0|exact H0|
    |exact G1|exact H1].
  generalize (Rabs_pos cz0) (uq_ge_0 rel Hrel). intros A0 Q0.
  assert (K1 : uq rel * Rabs (cz0 + cz1) <= uq rel * ((1 + u prec) * Rabs cz0))
    by (apply Rmult_le_compat_l; assumption).
  assert (K2 : uq rel * (1 + u prec) * Rabs cz0
               <= RU emin prec (uq rel * (1 + u prec)) * Rabs cz0)
    by (apply Rmult_le_compat_r; assumption).
  lra.
Qed.
