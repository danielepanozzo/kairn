(* The radius kernels of the ball vectors (proofs/gen/Model.v): the generated statements
   bv_add_radius_1_spec, bv_add_radius_2_spec, bv_scale_radius_1_spec and
   bv_scale_radius_2_spec (proofs/gen/Statements.v).

   A ball vector has one radius for all its entries. Its radius kernel is the radius lines
   of the Ball kernel of its operation, ball_add_k or ball_scale_k (Ball2.v), with m, the
   largest magnitude of a (leading limb of a) center written, in place of the magnitude of
   one entry's center:

       s = RN (rx + ry)  or  p = RN (|a| rx)
       t = RN (m E + s)                        E = RU (U kappa)
       rz = RN (t G + H)                        G = RU ((1 + u)^3), H = RU (h2 V + nrm)

   with U = rel / (1 - rel) and V = tiny / (1 - rel) from the bound rel |v| + tiny of the
   step (add_1_1, add_2_2, mul_1_1, mul_2_1), and kappa = (1 + u)^(k - 1) for centers of k
   limbs. The claim (upper) is that rz is at least

       rx + ry + U kappa m         (sum, difference)
       |a| rx + U kappa m + V      (scaling)

   which is radius_2 of Ball2.v with e = U kappa m + V: the chain of the first two
   roundings loses at most (1 + u)^2 and (1 + u)^2 eta, and the last operation pays for
   them, G and H being at least what radius_2 asks. These lines are those of the Ball
   kernels: the constants are theirs, by name (e_add_1_eq and the others of Ball2.v), and
   nothing is proved of the arithmetic again.

   What the claim gives a ball vector (BvReal.v): for an entry whose computed center z has
   |z - v| <= U |z| + V for its exact center v (computed_bound of Ball2.v, from the bound of
   the step), and |z| <= kappa m, that radius covers it.

   The claim holds for every m >= 0, rx >= 0, ry >= 0 of the format: no bound of m is
   asked, and nothing overflows in this model. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Ball2.
Open Scope R_scope.

Theorem bv_add_radius_1_correct : bv_add_radius_1_spec.
Proof.
intros emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold bv_add_radius_1. cbv zeta.
split. limb_format.
rewrite e_add_1_eq, g_add_1_eq, h_add_1_eq.
set (rel := rel_1 prec).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
assert (H2 : (1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2) = h2 emin prec 0)
  by (unfold h2; ring).
rewrite H2.
destruct (RU_ge_plus emin prec (h2 emin prec 0) (nrm emin prec)
            (h2_ge_0 emin prec 0 (Rle_refl 0)) (nrm_ge_0 emin prec)) as [H0 H1].
assert (Hq : m * rel / (1 - rel) = uq rel * m) by (unfold uq; field; lra).
rewrite Hq.
apply (radius_2 emin prec (rx + ry) m _ _ _ _ 0);
  [lra|exact Hm|exact E0|exact G0|exact H0| |exact G1|exact H1].
assert (uq rel * m <= RU emin prec (uq rel) * m) by (apply Rmult_le_compat_r; assumption).
lra.
Qed.

Theorem bv_add_radius_2_correct : bv_add_radius_2_spec.
Proof.
intros emin prec Hp m rx ry Fm Frx Fry Hm Hrx Hry.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold bv_add_radius_2. cbv zeta.
split. limb_format.
rewrite e_add_2_eq, g_add_2_eq, h_add_2_eq.
set (rel := rel_add_2 prec).
assert (Hrel : 0 <= rel < 1) by exact (rel_add_2_2 prec Hp).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (K0 : 0 <= uq rel * (1 + u prec)).
{ apply Rmult_le_pos. exact (uq_ge_0 rel Hrel). lra. }
destruct (RU_ge emin prec (uq rel * (1 + u prec)) K0) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
assert (H2 : (1 + u prec) * ((1 + u prec) ^ 2 * eta emin + eta emin / 2) = h2 emin prec 0)
  by (unfold h2; ring).
rewrite H2.
destruct (RU_ge_plus emin prec (h2 emin prec 0) (nrm emin prec)
            (h2_ge_0 emin prec 0 (Rle_refl 0)) (nrm_ge_0 emin prec)) as [H0 H1].
assert (Hq : m * rel / (1 - rel) * (1 + u prec) = uq rel * (1 + u prec) * m)
  by (unfold uq; field; lra).
rewrite Hq.
apply (radius_2 emin prec (rx + ry) m _ _ _ _ 0);
  [lra|exact Hm|exact E0|exact G0|exact H0| |exact G1|exact H1].
assert (uq rel * (1 + u prec) * m <= RU emin prec (uq rel * (1 + u prec)) * m)
  by (apply Rmult_le_compat_r; assumption).
lra.
Qed.

Theorem bv_scale_radius_1_correct : bv_scale_radius_1_spec.
Proof.
intros emin prec Hp m rx a Fm Frx Fa Hm Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold bv_scale_radius_1. cbv zeta.
split. limb_format.
rewrite e_scale_1_eq, g_scale_1_eq, h_scale_1_eq.
rewrite (Rplus_0_r (Rabs a * rx)).
set (rel := rel_1 prec). set (tiny := 1 / 2 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_one_limb prec).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
destruct (RU_ge emin prec (uq rel) (uq_ge_0 rel Hrel)) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
destruct (RU_ge_plus emin prec (h2 emin prec (vq rel tiny)) (nrm emin prec)
            (h2_ge_0 emin prec _ (vq_ge_0 rel tiny Hrel Htiny)) (nrm_ge_0 emin prec)) as [H0 H1].
assert (Hq : Rabs a * rx + m * rel / (1 - rel) + tiny / (1 - rel) =
             Rabs a * rx + (uq rel * m + vq rel tiny)) by (unfold uq, vq; field; lra).
rewrite Hq.
apply (radius_2 emin prec (Rabs a * rx) m _ _ _ _ (vq rel tiny));
  [apply Rmult_le_pos; [apply Rabs_pos|exact Hrx]|exact Hm|exact E0|exact G0|exact H0|
  |exact G1|exact H1].
assert (uq rel * m <= RU emin prec (uq rel) * m) by (apply Rmult_le_compat_r; assumption).
lra.
Qed.

Theorem bv_scale_radius_2_correct : bv_scale_radius_2_spec.
Proof.
intros emin prec Hp m rx a Fm Frx Fa Hm Hrx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
unfold bv_scale_radius_2. cbv zeta.
split. limb_format.
rewrite e_scale_2_eq, g_scale_2_eq, h_scale_2_eq.
rewrite (Rplus_0_r (Rabs a * rx)).
set (rel := rel_mul_21 prec). set (tiny := 1 * eta emin).
assert (Hrel : 0 <= rel < 1) by exact (rel_mul_2_1 prec Hp).
assert (Htiny : 0 <= tiny) by (apply eta_ge_0; lra).
generalize (bpow_gt_0 radix2 (- prec)). fold (u prec). intros U0.
assert (K0 : 0 <= uq rel * (1 + u prec)).
{ apply Rmult_le_pos. exact (uq_ge_0 rel Hrel). lra. }
destruct (RU_ge emin prec (uq rel * (1 + u prec)) K0) as [E0 E1].
destruct (RU_ge emin prec ((1 + u prec) ^ 3) (pow_ge_0' prec 3)) as [G0 G1].
destruct (RU_ge_plus emin prec (h2 emin prec (vq rel tiny)) (nrm emin prec)
            (h2_ge_0 emin prec _ (vq_ge_0 rel tiny Hrel Htiny)) (nrm_ge_0 emin prec)) as [H0 H1].
assert (Hq : Rabs a * rx + m * rel / (1 - rel) * (1 + u prec) + tiny / (1 - rel) =
             Rabs a * rx + (uq rel * (1 + u prec) * m + vq rel tiny))
  by (unfold uq, vq; field; lra).
rewrite Hq.
apply (radius_2 emin prec (Rabs a * rx) m _ _ _ _ (vq rel tiny));
  [apply Rmult_le_pos; [apply Rabs_pos|exact Hrx]|exact Hm|exact E0|exact G0|exact H0|
  |exact G1|exact H1].
assert (uq rel * (1 + u prec) * m <= RU emin prec (uq rel * (1 + u prec)) * m)
  by (apply Rmult_le_compat_r; assumption).
lra.
Qed.
