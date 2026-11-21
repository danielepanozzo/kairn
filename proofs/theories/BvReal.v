(* The ball vectors in the real model: the generated statements bv_add_k_spec,
   bv_sub_k_spec and bv_scale_k_spec (proofs/gen/FoldStatements.v).

   A ball vector is N centers and one radius. bv_add_k writes the centers of the sum
   entry by entry, by the map add_k (add_1_1 or add_2_2 on each pair of centers); records
   the largest magnitude m of a (leading limb of a) center written, by the step of the
   fold of maxima, norm_step_k; and gives the one radius by bv_add_radius_k on m and the
   two radii (BvRadius.v). bv_sub_k is the same with sub_1_1 or sub_2_2, and bv_scale_k
   with scale_step_k and bv_scale_radius_k on m, the radius and the factor a.

   The statement: for nonnegative radii and valid centers, the radius is a number of the
   format, and entry by entry the center written is valid and the value of the operation
   on any members of the balls of the operands' entries is within the radius of it.

   How, entry by entry, with z the center written and v the exact value of the operation
   on the centers of the operands:
   - the value on members is within rx + ry of v (or |a| rx, for a scaling), and v within
     |z - v| of z (enclose_add, enclose_scale of Ball2.v);
   - the bound of the step, rel |v| + tiny, turned into one relative to the result:
     |z - v| <= U |z| + V, U = rel / (1 - rel), V = tiny / (1 - rel) (computed_bound);
   - |z| <= kappa m: m is the largest |z| of one limb, or |z0| of two, over the centers
     written (record_seq_value: the record is the maximum of the state with the
     magnitude of the element, and the sequential order of it from (0, true) is the
     largest of 0 and the magnitudes, FoldNorm.v), and |z0 + z1| <= (1 + u) |z0| for a
     normalized pair (normalized_2_abs_le);
   - the claim of the radius kernel: rx + ry + U kappa m <= r (or |a| rx + U kappa m + V).

   So the one radius at the largest magnitude covers every entry because the claim of the
   radius kernel is stated at m, and the error bound of each entry is at most its value at
   m: nothing about the rounded radius lines as functions of m is needed. That they are
   nondecreasing in m (each is a rounding to nearest of a nondecreasing expression of m
   and of numbers that do not depend on it), so that the one radius is the largest of the
   radii the Ball kernel computes entry by entry, is true but not used here, and not
   proved. *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Normalized Folds OneLimb Add22 Sign Mul21 MapSteps FoldNorm Ball2
  BvRadius.
Import ListNotations.
Open Scope R_scope.

(* The largest of 0 and the elements of a list, as FoldNorm.v writes it. *)
Local Notation maxl l := (fold_right Rmax 0 l).

(** * The record: the largest magnitude of a center written *)

Lemma record_1_eq :
  forall (s : R * bool) (w : R), norm_step_1 (fst s) (snd s) w = maxc s (Rabs w, true).
Proof.
intros s w. unfold norm_step_1, norm_combine, maxc. cbv beta iota zeta. cbn [fst snd].
now rewrite lt_select_max, (Req_bool_true _ _ (eq_refl (Rabs w))).
Qed.

Lemma record_2_eq :
  forall (s : R * bool) (w : R * R),
  norm_step_2 (fst s) (snd s) (fst w) (snd w) = maxc s (Rabs (fst w), true).
Proof.
intros s w. unfold norm_step_2. rewrite record_1_eq. reflexivity.
Qed.

(* The magnitude of every element written is at most the largest one, which is a
   nonnegative number of the format when every element is. *)
Lemma maxl_facts :
  forall (emin prec : Z) (B : Type) (h : B -> R) (ws : list B),
  Forall (fun w => fmt emin prec (h w)) ws ->
  fmt emin prec (maxl (map (fun w => Rabs (h w)) ws)) /\
  0 <= maxl (map (fun w => Rabs (h w)) ws) /\
  forall w, In w ws -> Rabs (h w) <= maxl (map (fun w => Rabs (h w)) ws).
Proof.
intros emin prec B h ws H. split; [|split].
- apply maxl_fmt. apply Forall_map. revert H. apply Forall_impl. intros w Fw.
  unfold fmt in *. now apply generic_format_abs.
- apply maxl_nonneg.
- intros w Hw. apply maxl_ge. apply in_map_iff. exists w. split; [reflexivity | exact Hw].
Qed.

(** * The error of an entry, at the largest magnitude *)

(* For an entry whose center z is within rel |v| + tiny of its exact value v, with
   |z| <= K m: the error is at most uq rel K m + vq rel tiny. *)
Lemma entry_error :
  forall rel tiny K m z v : R, 0 <= rel < 1 -> 0 <= tiny -> 0 <= K ->
  Rabs (z - v) <= rel * Rabs v + tiny -> Rabs z <= K * m ->
  Rabs (z - v) <= uq rel * K * m + vq rel tiny.
Proof.
intros rel tiny K m z v Hrel Ht HK Hb Hz.
apply Rle_trans with (1 := computed_bound rel tiny z v Hrel Ht Hb). fold (uq rel) (vq rel tiny).
assert (uq rel * Rabs z <= uq rel * (K * m))
  by (apply Rmult_le_compat_l; [apply uq_ge_0|]; assumption).
lra.
Qed.

(** * The generated statements *)

Theorem bv_add_1_correct : bv_add_1_spec.
Proof.
intros emin prec Hp rx ry xys Frx Hrx Fry Hry H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
set (ws := bv_add_1_map emin prec tie_even xys).
assert (Fw : Forall (fun w => fmt emin prec w) ws).
{ unfold ws, bv_add_1_map. apply Forall_map. revert H. apply Forall_impl.
  intros [x y] [Fx Fy]. exact (proj1 (add_1_1_correct emin prec Hp x y Fx Fy)). }
destruct (maxl_facts emin prec R (fun w => w) ws Fw) as [Fm [Hm Hle]].
cbv beta in Fm, Hm, Hle.
unfold bv_add_1_radius. fold ws.
rewrite (maxc_seq_value R bv_add_1_record (fun w => Rabs w) record_1_eq ws). cbn [fst].
set (m := maxl (map (fun w => Rabs w) ws)) in *.
destruct (bv_add_radius_1_correct emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry) as [Fr Hr].
split. exact Fr.
set (rel := rel_1 prec) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Hq : m * rel / (1 - rel) = uq rel * 1 * m) by (unfold uq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_add_1_map. apply Forall2_map_r. apply Forall_forall. intros [x y] Hin.
destruct (proj1 (Forall_forall _ xys) H (x, y) Hin) as [Fx Fy]. cbn [fst snd] in Fx, Fy.
destruct (add_1_1_correct emin prec Hp x y Fx Fy) as [Fz [_ B]].
unfold bv_add_1_step. cbn [fst snd]. split. exact Fz.
intros x_ y_ H1 H2.
assert (Hz : Rabs (add_1_1 emin prec tie_even x y) <= 1 * m).
{ rewrite Rmult_1_l. apply (Hle (add_1_1 emin prec tie_even x y)).
  unfold ws, bv_add_1_map. apply in_map_iff. exists (x, y). split; [reflexivity | exact Hin]. }
assert (B0 : Rabs (add_1_1 emin prec tie_even x y - (x + y)) <= rel * Rabs (x + y) + 0)
  by (rewrite Rplus_0_r; exact B).
generalize (entry_error rel 0 1 m _ _ Hrel (Rle_refl 0) Rle_0_1 B0 Hz). unfold vq.
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros E.
generalize (enclose_add x_ y_ x y (add_1_1 emin prec tie_even x y) rx ry _ H1 H2 E). lra.
Qed.

Theorem bv_sub_1_correct : bv_sub_1_spec.
Proof.
intros emin prec Hp rx ry xys Frx Hrx Fry Hry H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
set (ws := bv_sub_1_map emin prec tie_even xys).
assert (Fw : Forall (fun w => fmt emin prec w) ws).
{ unfold ws, bv_sub_1_map. apply Forall_map. revert H. apply Forall_impl.
  intros [x y] [Fx Fy]. exact (proj1 (sub_1_1_correct emin prec Hp x y Fx Fy)). }
destruct (maxl_facts emin prec R (fun w => w) ws Fw) as [Fm [Hm Hle]].
cbv beta in Fm, Hm, Hle.
unfold bv_sub_1_radius. fold ws.
rewrite (maxc_seq_value R bv_sub_1_record (fun w => Rabs w) record_1_eq ws). cbn [fst].
set (m := maxl (map (fun w => Rabs w) ws)) in *.
destruct (bv_add_radius_1_correct emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry) as [Fr Hr].
split. exact Fr.
set (rel := rel_1 prec) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Hq : m * rel / (1 - rel) = uq rel * 1 * m) by (unfold uq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_sub_1_map. apply Forall2_map_r. apply Forall_forall. intros [x y] Hin.
destruct (proj1 (Forall_forall _ xys) H (x, y) Hin) as [Fx Fy]. cbn [fst snd] in Fx, Fy.
destruct (sub_1_1_correct emin prec Hp x y Fx Fy) as [Fz [_ B]].
unfold bv_sub_1_step. cbn [fst snd]. split. exact Fz.
intros x_ y_ H1 H2.
assert (H2' : Rabs (- y_ - - y) <= ry).
{ replace (- y_ - - y) with (- (y_ - y)) by ring. now rewrite Rabs_Ropp. }
assert (Hz : Rabs (sub_1_1 emin prec tie_even x y) <= 1 * m).
{ rewrite Rmult_1_l. apply (Hle (sub_1_1 emin prec tie_even x y)).
  unfold ws, bv_sub_1_map. apply in_map_iff. exists (x, y). split; [reflexivity | exact Hin]. }
assert (B0 : Rabs (sub_1_1 emin prec tie_even x y - (x + - y)) <= rel * Rabs (x + - y) + 0)
  by (rewrite Rplus_0_r; replace (x + - y) with (x - y) by ring; exact B).
generalize (entry_error rel 0 1 m _ _ Hrel (Rle_refl 0) Rle_0_1 B0 Hz). unfold vq.
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros E.
generalize (enclose_add x_ (- y_) x (- y) (sub_1_1 emin prec tie_even x y) rx ry _ H1 H2' E).
replace (x_ + - y_) with (x_ - y_) by ring. lra.
Qed.

Theorem bv_scale_1_correct : bv_scale_1_spec.
Proof.
intros emin prec Hp rx a xs Frx Hrx Fa H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
set (ws := bv_scale_1_map emin prec tie_even a xs).
assert (Fw : Forall (fun w => fmt emin prec w) ws).
{ unfold ws, bv_scale_1_map. apply Forall_map. revert H. apply Forall_impl.
  intros x Fx. exact (proj1 (scale_step_1_correct emin prec Hp x a Fx Fa)). }
destruct (maxl_facts emin prec R (fun w => w) ws Fw) as [Fm [Hm Hle]].
cbv beta in Fm, Hm, Hle.
unfold bv_scale_1_radius. fold ws.
rewrite (maxc_seq_value R bv_scale_1_record (fun w => Rabs w) record_1_eq ws). cbn [fst].
set (m := maxl (map (fun w => Rabs w) ws)) in *.
destruct (bv_scale_radius_1_correct emin prec Hp m rx a Fm Frx Fa Hm Hrx) as [Fr Hr].
split. exact Fr.
set (rel := rel_1 prec) in *. set (tiny := 1 / 2 * eta emin) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
assert (Hq : Rabs a * rx + m * rel / (1 - rel) + tiny / (1 - rel) =
             Rabs a * rx + (uq rel * 1 * m + vq rel tiny)) by (unfold uq, vq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_scale_1_map. apply Forall2_map_r. apply Forall_forall. intros x Hin.
pose proof (proj1 (Forall_forall _ xs) H x Hin) as Fx.
destruct (scale_step_1_correct emin prec Hp x a Fx Fa) as [Fz [_ B]].
unfold bv_scale_1_step. split. exact Fz.
intros x_ H1.
assert (Hz : Rabs (scale_step_1 emin prec tie_even x a) <= 1 * m).
{ rewrite Rmult_1_l. apply (Hle (scale_step_1 emin prec tie_even x a)).
  unfold ws, bv_scale_1_map. apply in_map_iff. exists x. split; [reflexivity | exact Hin]. }
generalize (entry_error rel tiny 1 m _ _ Hrel Htiny Rle_0_1 B Hz). intros E.
generalize (enclose_scale x_ a x (scale_step_1 emin prec tie_even x a) rx _ H1 E). lra.
Qed.

Theorem bv_add_2_correct : bv_add_2_spec.
Proof.
intros emin prec Hp rx ry xys Frx Hrx Fry Hry H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
set (ws := bv_add_2_map emin prec tie_even xys).
assert (Fw : Forall (fun w => fmt emin prec (fst w)) ws).
{ unfold ws, bv_add_2_map. apply Forall_map. revert H. apply Forall_impl.
  intros [[x0 x1] [y0 y1]] [Nx Ny]. unfold bv_add_2_step. cbn [fst snd] in *.
  generalize (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
  destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. intros [Nz _]. apply Nz. }
destruct (maxl_facts emin prec (R * R) fst ws Fw) as [Fm [Hm Hle]].
unfold bv_add_2_radius. fold ws.
rewrite (maxc_seq_value (R * R) bv_add_2_record (fun w => Rabs (fst w)) record_2_eq ws). cbn [fst].
set (m := maxl (map (fun w => Rabs (fst w)) ws)) in *.
destruct (bv_add_radius_2_correct emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry) as [Fr Hr].
split. exact Fr.
set (rel := rel_add_2 prec) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_add_2_2 prec Hp).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hq : m * rel / (1 - rel) * (1 + u prec) = uq rel * (1 + u prec) * m)
  by (unfold uq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_add_2_map. apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
destruct (proj1 (Forall_forall _ xys) H _ Hin) as [Nx Ny]. cbn [fst snd] in Nx, Ny.
assert (Hz0 : Rabs (fst (bv_add_2_step emin prec tie_even ((x0, x1), (y0, y1)))) <= m).
{ apply (Hle (bv_add_2_step emin prec tie_even ((x0, x1), (y0, y1)))).
  unfold ws, bv_add_2_map. apply in_map_iff. exists ((x0, x1), (y0, y1)).
  split; [reflexivity | exact Hin]. }
unfold bv_add_2_step in *. cbn [fst snd] in *.
generalize (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbn [fst] in Hz0.
intros [Nz B]. split. exact Nz.
intros x_ y_ H1 H2.
assert (Hz : Rabs (z0 + z1) <= (1 + u prec) * m).
{ apply Rle_trans with ((1 + u prec) * Rabs z0).
  - exact (normalized_2_abs_le emin prec z0 z1 Nz).
  - apply Rmult_le_compat_l. lra. exact Hz0. }
assert (B0 : Rabs (z0 + z1 - (x0 + x1 + (y0 + y1))) <= rel * Rabs (x0 + x1 + (y0 + y1)) + 0)
  by (rewrite Rplus_0_r; exact B).
generalize (entry_error rel 0 (1 + u prec) m _ _ Hrel (Rle_refl 0) ltac:(lra) B0 Hz). unfold vq.
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros E.
generalize (enclose_add x_ y_ (x0 + x1) (y0 + y1) (z0 + z1) rx ry _ H1 H2 E). lra.
Qed.

Theorem bv_sub_2_correct : bv_sub_2_spec.
Proof.
intros emin prec Hp rx ry xys Frx Hrx Fry Hry H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
set (ws := bv_sub_2_map emin prec tie_even xys).
assert (Fw : Forall (fun w => fmt emin prec (fst w)) ws).
{ unfold ws, bv_sub_2_map. apply Forall_map. revert H. apply Forall_impl.
  intros [[x0 x1] [y0 y1]] [Nx Ny]. unfold bv_sub_2_step. cbn [fst snd] in *.
  generalize (sub_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
  destruct (sub_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. intros [Nz _]. apply Nz. }
destruct (maxl_facts emin prec (R * R) fst ws Fw) as [Fm [Hm Hle]].
unfold bv_sub_2_radius. fold ws.
rewrite (maxc_seq_value (R * R) bv_sub_2_record (fun w => Rabs (fst w)) record_2_eq ws). cbn [fst].
set (m := maxl (map (fun w => Rabs (fst w)) ws)) in *.
destruct (bv_add_radius_2_correct emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry) as [Fr Hr].
split. exact Fr.
set (rel := rel_add_2 prec) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_add_2_2 prec Hp).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hq : m * rel / (1 - rel) * (1 + u prec) = uq rel * (1 + u prec) * m)
  by (unfold uq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_sub_2_map. apply Forall2_map_r. apply Forall_forall. intros [[x0 x1] [y0 y1]] Hin.
destruct (proj1 (Forall_forall _ xys) H _ Hin) as [Nx Ny]. cbn [fst snd] in Nx, Ny.
assert (Hz0 : Rabs (fst (bv_sub_2_step emin prec tie_even ((x0, x1), (y0, y1)))) <= m).
{ apply (Hle (bv_sub_2_step emin prec tie_even ((x0, x1), (y0, y1)))).
  unfold ws, bv_sub_2_map. apply in_map_iff. exists ((x0, x1), (y0, y1)).
  split; [reflexivity | exact Hin]. }
unfold bv_sub_2_step in *. cbn [fst snd] in *.
generalize (sub_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (sub_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbn [fst] in Hz0.
intros [Nz B]. split. exact Nz.
intros x_ y_ H1 H2.
assert (H2' : Rabs (- y_ - - (y0 + y1)) <= ry).
{ replace (- y_ - - (y0 + y1)) with (- (y_ - (y0 + y1))) by ring. now rewrite Rabs_Ropp. }
assert (Hz : Rabs (z0 + z1) <= (1 + u prec) * m).
{ apply Rle_trans with ((1 + u prec) * Rabs z0).
  - exact (normalized_2_abs_le emin prec z0 z1 Nz).
  - apply Rmult_le_compat_l. lra. exact Hz0. }
assert (B0 : Rabs (z0 + z1 - (x0 + x1 + - (y0 + y1))) <= rel * Rabs (x0 + x1 + - (y0 + y1)) + 0).
{ rewrite Rplus_0_r. replace (x0 + x1 + - (y0 + y1)) with (x0 + x1 - (y0 + y1)) by ring. exact B. }
generalize (entry_error rel 0 (1 + u prec) m _ _ Hrel (Rle_refl 0) ltac:(lra) B0 Hz). unfold vq.
replace (0 / (1 - rel)) with 0 by (unfold Rdiv; ring). intros E.
generalize (enclose_add x_ (- y_) (x0 + x1) (- (y0 + y1)) (z0 + z1) rx ry _ H1 H2' E).
replace (x_ + - y_) with (x_ - y_) by ring. lra.
Qed.

Theorem bv_scale_2_correct : bv_scale_2_spec.
Proof.
intros emin prec Hp rx a xs Frx Hrx Fa H. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
set (ws := bv_scale_2_map emin prec tie_even a xs).
assert (Fw : Forall (fun w => fmt emin prec (fst w)) ws).
{ unfold ws, bv_scale_2_map. apply Forall_map. revert H. apply Forall_impl.
  intros [x0 x1] Nx. unfold bv_scale_2_step. cbn [fst snd] in *.
  generalize (scale_step_2_correct emin prec Hp x0 x1 a Nx Fa).
  destruct (scale_step_2 emin prec tie_even x0 x1 a) as [z0 z1]. intros [Nz _]. apply Nz. }
destruct (maxl_facts emin prec (R * R) fst ws Fw) as [Fm [Hm Hle]].
unfold bv_scale_2_radius. fold ws.
rewrite (maxc_seq_value (R * R) bv_scale_2_record (fun w => Rabs (fst w)) record_2_eq ws).
cbn [fst].
set (m := maxl (map (fun w => Rabs (fst w)) ws)) in *.
destruct (bv_scale_radius_2_correct emin prec Hp m rx a Fm Frx Fa Hm Hrx) as [Fr Hr].
split. exact Fr.
set (rel := rel_mul_21 prec) in *. set (tiny := 1 * eta emin) in *.
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_1 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (Hq : Rabs a * rx + m * rel / (1 - rel) * (1 + u prec) + tiny / (1 - rel) =
             Rabs a * rx + (uq rel * (1 + u prec) * m + vq rel tiny))
  by (unfold uq, vq; field; lra).
rewrite Hq in Hr.
unfold ws, bv_scale_2_map. apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
pose proof (proj1 (Forall_forall _ xs) H _ Hin) as Nx. cbn [fst snd] in Nx.
assert (Hz0 : Rabs (fst (bv_scale_2_step emin prec tie_even a (x0, x1))) <= m).
{ apply (Hle (bv_scale_2_step emin prec tie_even a (x0, x1))).
  unfold ws, bv_scale_2_map. apply in_map_iff. exists (x0, x1). split; [reflexivity | exact Hin]. }
unfold bv_scale_2_step in *. cbn [fst snd] in *.
generalize (scale_step_2_correct emin prec Hp x0 x1 a Nx Fa).
destruct (scale_step_2 emin prec tie_even x0 x1 a) as [z0 z1]. cbn [fst] in Hz0.
intros [Nz B]. split. exact Nz.
intros x_ H1.
assert (Hz : Rabs (z0 + z1) <= (1 + u prec) * m).
{ apply Rle_trans with ((1 + u prec) * Rabs z0).
  - exact (normalized_2_abs_le emin prec z0 z1 Nz).
  - apply Rmult_le_compat_l. lra. exact Hz0. }
generalize (entry_error rel tiny (1 + u prec) m _ _ Hrel Htiny ltac:(lra) B Hz). intros E.
generalize (enclose_scale x_ a (x0 + x1) (z0 + z1) rx _ H1 E). lra.
Qed.
