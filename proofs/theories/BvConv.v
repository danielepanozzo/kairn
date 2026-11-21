(* The product of two ball vectors (two polynomials with one radius each) in the real model:
   the generated statements of the radius kernel conv_radius (proofs/gen/Statements.v) and of
   the folds bv_conv_1 and bv_conv_2 (proofs/gen/FoldStatements.v).

   The radius kernel. Its listing is
       p = RN(rx ry)  q = RN(mb rx + p)  w = RN(ma ry + q)  ab = RN(ma mb)  e = RN(ab g + w)
       s = RN(m e + t)  hm = RN(m C0)  rz = RN(s C7 + hm)
   with C7 = RU((1 + u)^7) and C0 = RU(4 (1 + u)^8 eta + eta / (2 u)). Each rounding of a
   nonnegative x gives x <= (1 + u) (RN(x) + eta / 2) (rnd_lower of Ball2.v); chained, the six
   first lines give
       m L + t <= (1 + u)^5 s + (1 + u)^5 eta / 2 + m (eta / 2) K,
   L = (1 + u) ma ry + (1 + u) mb rx + rx ry + g (1 + u)^2 ma mb, K <= 5 (1 + u)^4 for g <= 1
   (the requirement at_most(g, 1)); the last line covers the factor and, for a count m >= 1,
   the absolute terms, since m C0 is in the normal range and C0 >= 4 (1 + u)^8 eta
   (radius_tail of Ball2.v). For m = 0 the claim is t <= rz, and s = t.

   The bound kernel's ok gives g <= 1 (bound_dot_k_at_most): its listing tests g against
   up(1), which is 1 when 1 is a number of the format (c6_le of BoundKernels.v).

   The folds. Coefficient j is the dot product of the terms conv_terms xs ys j, within
   g sum |c_x c_y| + t of their exact sum when the bound is given for a count m of at least
   min(n_x, n_y) (conv_k_bound of FoldConv.v). For members x_i and y_k of the balls, chosen
   independently, the terms of conv_terms xs_ ys_ j are those of the centers entry by entry
   (conv_terms_Forall2), and each product is within |c_x| ry + |c_y| rx + rx ry of the product
   of the centers (member_product). Every center is at most (1 + u) times the largest
   magnitude of a leading limb, Ma or Mb (normalized_2_abs_le of Ball2.v; 1 for one limb),
   and there are at most m terms; so the coefficient of the members is within the value of
   the claim of conv_radius of the coefficient written. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Relative.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Normalized Folds Summation FoldNorm FoldConv OneLimb Ball2 BoundKernels
  BvReal.
Import ListNotations.
Open Scope R_scope.

Local Notation maxl l := (fold_right Rmax 0 l).

(** * The radius kernel *)

Section ConvRadius.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Hypothesis Hp2 : (2 <= prec)%Z.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation RUp := (round radix2 fexp Zceil).
Notation uu := (u prec).
Notation ee := (eta emin).
Notation NN := (bpow radix2 (emin + prec - 1)).

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let u4 : uu <= / 4.
Proof. exact (proj2 (u_bounds prec 2 Hp2)). Qed.
Let e0 : 0 < ee.
Proof. apply bpow_gt_0. Qed.

(* One rounding to nearest in the normal range loses at most the factor 1 + u (as
   rnd_lower_normal of AccKernels.v). *)
Lemma rnd_lower_normal_conv : forall x : R, NN <= x -> x <= (1 + uu) * rnd x.
Proof.
intros x Hx.
assert (Hx0 : 0 <= x) by (generalize (bpow_gt_0 radix2 (emin + prec - 1)); lra).
rewrite (round_FLT_FLX radix2 emin prec (Znearest tie_even) x) by (rewrite Rabs_pos_eq; lra).
generalize (relative_error_N_FLX' radix2 prec prec_gt_0_ tie_even x).
rewrite u_ro_eq, (Rabs_pos_eq x Hx0). intros E. apply Rabs_le_inv in E.
set (r := round radix2 (FLX_exp prec) (Znearest tie_even) x) in *.
assert (K : x * (1 - uu / (1 + uu)) <= r) by lra.
assert (K2 : (1 + uu) * (1 - uu / (1 + uu)) = 1) by (field; lra).
apply Rle_trans with ((1 + uu) * (x * (1 - uu / (1 + uu)))).
- replace ((1 + uu) * (x * (1 - uu / (1 + uu)))) with (x * ((1 + uu) * (1 - uu / (1 + uu))))
    by ring. rewrite K2. lra.
- apply Rmult_le_compat_l; lra.
Qed.

Lemma conv_radius_facts :
  forall ma mb rx ry m g t : R,
  format t -> 0 <= ma -> 0 <= mb -> 0 <= rx -> 0 <= ry -> (m = 0 \/ 1 <= m) ->
  0 <= g -> g <= 1 -> 0 <= t ->
  format (conv_radius emin prec tie_even ma mb rx ry m g t) /\
  m * ((1 + uu) * ma * ry + (1 + uu) * mb * rx + rx * ry) + g * m * (1 + uu) ^ 2 * ma * mb + t <=
  conv_radius emin prec tie_even ma mb rx ry m g t.
Proof.
intros ma mb rx ry m g t Ft Pa Pb Px Py Hm Pg Lg Pt.
unfold conv_radius. cbv zeta.
set (C0 := up_conv_radius_0 emin prec). set (C7 := up_conv_radius_1 emin prec).
assert (HC7 : (1 + uu) ^ 7 <= C7) by (unfold C7, up_conv_radius_1, u; apply (RUp_ge emin prec)).
assert (HC0 : 4 * (1 + uu) ^ 8 * ee + NN <= C0).
{ unfold C0, up_conv_radius_0. rewrite <- (nrm_eq emin prec). unfold nrm, u, eta.
  apply (RUp_ge emin prec). }
assert (P1 : 1 <= 1 + uu) by lra.
assert (Pn : forall n : nat, 1 <= (1 + uu) ^ n) by (intros n; apply pow_R1_Rle; exact P1).
split. apply generic_format_round; auto with typeclass_instances.
set (p := rnd (rx * ry + 0)). set (q := rnd (mb * rx + p)). set (w := rnd (ma * ry + q)).
set (ab := rnd (ma * mb + 0)). set (e := rnd (ab * g + w)). set (s := rnd (m * e + t)).
set (hm := rnd (m * C0 + 0)).
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Pp : 0 <= p) by (apply (rnd_ge_0 emin prec); nra).
assert (Pq : 0 <= q) by (apply (rnd_ge_0 emin prec); nra).
assert (Pw : 0 <= w) by (apply (rnd_ge_0 emin prec); nra).
assert (Pab : 0 <= ab) by (apply (rnd_ge_0 emin prec); nra).
assert (Pe : 0 <= e) by (apply (rnd_ge_0 emin prec); nra).
assert (Ps : 0 <= s) by (apply (rnd_ge_0 emin prec); nra).
set (h := ee / 2).
assert (Ph : 0 <= h) by (unfold h; lra).
assert (L1 : rx * ry <= (1 + uu) * (p + h)).
{ unfold p, h. rewrite <- (Rplus_0_r (rx * ry)) at 1. apply (rnd_lower emin prec). nra. }
assert (L2 : mb * rx + p <= (1 + uu) * (q + h)) by (unfold q, h; apply (rnd_lower emin prec); nra).
assert (L3 : ma * ry + q <= (1 + uu) * (w + h)) by (unfold w, h; apply (rnd_lower emin prec); nra).
assert (L4 : ma * mb <= (1 + uu) * (ab + h)).
{ unfold ab, h. rewrite <- (Rplus_0_r (ma * mb)) at 1. apply (rnd_lower emin prec). nra. }
assert (L5 : ab * g + w <= (1 + uu) * (e + h)) by (unfold e, h; apply (rnd_lower emin prec); nra).
assert (L6 : m * e + t <= (1 + uu) * (s + h)) by (unfold s, h; apply (rnd_lower emin prec); nra).
destruct Hm as [Z|M1].
- (* no term: s = t and hm = 0 *)
  assert (Es : s = t).
  { unfold s. rewrite Z, Rmult_0_l, Rplus_0_l. apply round_generic; auto with typeclass_instances. }
  assert (Eh : hm = 0).
  { unfold hm. rewrite Z, Rmult_0_l, Rplus_0_l. apply round_0; auto with typeclass_instances. }
  rewrite Es, Eh, Z.
  apply Rle_trans with t. { right. ring. }
  apply round_ge_generic; auto with typeclass_instances. generalize (Pn 7%nat). nra.
- (* at least one term *)
  set (K := (1 + uu) ^ 4 + (1 + uu) ^ 3 * g + (1 + uu) ^ 3 + (1 + uu) ^ 2 + (1 + uu)).
  assert (HK : K <= 5 * (1 + uu) ^ 4).
  { unfold K. assert (A3 : (1 + uu) ^ 3 <= (1 + uu) ^ 4) by (simpl; nra).
    assert (A2 : (1 + uu) ^ 2 <= (1 + uu) ^ 4) by (simpl; nra).
    assert (A1 : (1 + uu) <= (1 + uu) ^ 4) by (simpl; nra).
    assert (A0 : (1 + uu) ^ 3 * g <= (1 + uu) ^ 3) by (generalize (Pn 3%nat); nra). lra. }
  set (L := (1 + uu) * ma * ry + (1 + uu) * mb * rx + rx * ry + g * (1 + uu) ^ 2 * ma * mb).
  assert (HL : L <= (1 + uu) ^ 4 * e + h * K).
  { unfold L, K.
    (* (1 + u)^2 ma ry + (1 + u) mb rx + rx ry <= (1 + u)^3 w + h ((1 + u)^3 + (1 + u)^2 + (1 + u)) *)
    assert (S1 : (1 + uu) * mb * rx + rx * ry <= (1 + uu) ^ 2 * q + h * ((1 + uu) ^ 2 + (1 + uu))).
    { assert (T2 : (1 + uu) * (mb * rx + p) <= (1 + uu) * ((1 + uu) * (q + h)))
        by (apply Rmult_le_compat_l; lra).
      simpl. nra. }
    assert (S2 : (1 + uu) ^ 2 * ma * ry + (1 + uu) * mb * rx + rx * ry <=
                 (1 + uu) ^ 3 * w + h * ((1 + uu) ^ 3 + (1 + uu) ^ 2 + (1 + uu))).
    { assert (T3 : (1 + uu) ^ 2 * (ma * ry + q) <= (1 + uu) ^ 2 * ((1 + uu) * (w + h)))
        by (apply Rmult_le_compat_l; [generalize (Pn 2%nat); lra|exact L3]).
      simpl in T3 |- *. nra. }
    assert (S3 : g * (1 + uu) ^ 2 * ma * mb <= (1 + uu) ^ 3 * (ab * g) + (1 + uu) ^ 3 * g * h).
    { assert (T4 : g * (1 + uu) ^ 2 * (ma * mb) <= g * (1 + uu) ^ 2 * ((1 + uu) * (ab + h))).
      { apply Rmult_le_compat_l; [generalize (Pn 2%nat); nra|exact L4]. }
      simpl in T4 |- *. nra. }
    assert (S4 : (1 + uu) ^ 3 * (ab * g + w) <= (1 + uu) ^ 3 * ((1 + uu) * (e + h)))
      by (apply Rmult_le_compat_l; [generalize (Pn 3%nat); lra|exact L5]).
    assert (S5 : (1 + uu) * ma * ry <= (1 + uu) ^ 2 * ma * ry).
    { assert (0 <= ma * ry) by nra. simpl. nra. }
    simpl in S2, S3, S4, S5 |- *. nra. }
  assert (HT : m * L + t <= (1 + uu) ^ 5 * s + (1 + uu) ^ 5 * h + m * (h * K)).
  { assert (T6 : (1 + uu) ^ 4 * (m * e + t) <= (1 + uu) ^ 4 * ((1 + uu) * (s + h)))
      by (apply Rmult_le_compat_l; [generalize (Pn 4%nat); lra|exact L6]).
    assert (T7 : m * L <= m * ((1 + uu) ^ 4 * e + h * K)) by (apply Rmult_le_compat_l; lra).
    assert (T8 : t <= (1 + uu) ^ 4 * t) by (generalize (Pn 4%nat); nra).
    simpl in T6 |- *. nra. }
  (* the last line *)
  assert (C0N : NN <= C0).
  { assert (0 <= 4 * (1 + uu) ^ 8 * ee) by (generalize (Pn 8%nat); nra). lra. }
  assert (Hhm : m * C0 <= (1 + uu) * hm).
  { unfold hm. rewrite Rplus_0_r. apply rnd_lower_normal_conv.
    assert (P0 : 0 <= C0) by (generalize (bpow_gt_0 radix2 (emin + prec - 1)); lra).
    apply Rle_trans with C0; [exact C0N|]. rewrite <- (Rmult_1_l C0) at 1.
    apply Rmult_le_compat_r; lra. }
  assert (Last : (1 + uu) ^ 5 * s + ((1 + uu) ^ 5 * h + m * (h * K)) <= rnd (s * C7 + hm)).
  { apply (radius_tail emin prec s C7 hm ((1 + uu) ^ 5) ((1 + uu) ^ 5 * h + m * (h * K))).
    - exact Ps.
    - generalize (Pn 7%nat). lra.
    - apply (rnd_ge_0 emin prec). apply Rplus_le_le_0_compat; [|lra].
      apply Rmult_le_pos; [lra|generalize (bpow_gt_0 radix2 (emin + prec - 1)); lra].
    - assert (A : (1 + uu) * (1 + uu) ^ 5 <= (1 + uu) ^ 7).
      { replace ((1 + uu) ^ 7) with ((1 + uu) * (1 + uu) ^ 5 * (1 + uu)) by ring.
        assert (Z0 : 0 <= (1 + uu) * (1 + uu) ^ 5)
          by (apply Rmult_le_pos; [lra|generalize (Pn 5%nat); lra]).
        assert (Z1 : (1 + uu) * (1 + uu) ^ 5 * 1 <= (1 + uu) * (1 + uu) ^ 5 * (1 + uu))
          by (apply Rmult_le_compat_l; lra).
        lra. }
      lra.
    - (* (1 + u) (c + h) <= hm, from (1 + u)^2 (c + h) <= m C0 *)
      assert (B : (1 + uu) * ((1 + uu) * ((1 + uu) ^ 5 * h + m * (h * K) + h)) <= m * C0).
      { assert (B1 : (1 + uu) ^ 5 * h + h <= m * ((1 + uu) ^ 5 * h + h)).
        { assert (X0 : 0 <= (1 + uu) ^ 5 * h + h).
          { generalize (Pn 5%nat). intros P5.
            apply Rplus_le_le_0_compat; [apply Rmult_le_pos; lra|lra]. }
          assert (X1 : 1 * ((1 + uu) ^ 5 * h + h) <= m * ((1 + uu) ^ 5 * h + h))
            by (apply Rmult_le_compat_r; lra).
          lra. }
        assert (B2 : (1 + uu) ^ 5 * h + m * (h * K) + h <= m * (h * (7 * (1 + uu) ^ 5))).
        { assert (B3 : h * K <= h * (5 * (1 + uu) ^ 4)) by (apply Rmult_le_compat_l; lra).
          assert (B4 : h * (5 * (1 + uu) ^ 4) <= h * (5 * (1 + uu) ^ 5)).
          { apply Rmult_le_compat_l. exact Ph.
            replace ((1 + uu) ^ 5) with ((1 + uu) * (1 + uu) ^ 4) by ring.
            assert (0 <= uu * (1 + uu) ^ 4) by (apply Rmult_le_pos; [lra|generalize (Pn 4%nat); lra]).
            lra. }
          assert (B5 : h * 1 <= h * (1 + uu) ^ 5) by (apply Rmult_le_compat_l; [exact Ph|apply Pn]).
          assert (B21 : m * (h * K) <= m * (h * (5 * (1 + uu) ^ 5)))
            by (apply Rmult_le_compat_l; lra).
          assert (B22 : (1 + uu) ^ 5 * h + h + h * (5 * (1 + uu) ^ 5) <= h * (7 * (1 + uu) ^ 5))
            by lra.
          assert (B23 : m * ((1 + uu) ^ 5 * h + h + h * (5 * (1 + uu) ^ 5)) <=
                        m * (h * (7 * (1 + uu) ^ 5))) by (apply Rmult_le_compat_l; lra).
          lra. }
        assert (B6 : (1 + uu) * ((1 + uu) * (m * (h * (7 * (1 + uu) ^ 5)))) <=
                     m * (4 * (1 + uu) ^ 8 * ee)).
        { unfold h.
          assert (E7 : (1 + uu) * ((1 + uu) * (m * (ee / 2 * (7 * (1 + uu) ^ 5)))) =
                       m * (7 / 2 * (1 + uu) ^ 7 * ee)) by (simpl; field).
          rewrite E7.
          apply Rmult_le_compat_l. lra.
          replace (4 * (1 + uu) ^ 8 * ee) with (4 * (1 + uu) * ((1 + uu) ^ 7 * ee)) by ring.
          assert (Y0 : 0 <= (1 + uu) ^ 7 * ee)
            by (apply Rmult_le_pos; [generalize (Pn 7%nat); lra|lra]).
          assert (Y1 : 4 * 1 * ((1 + uu) ^ 7 * ee) <= 4 * (1 + uu) * ((1 + uu) ^ 7 * ee))
            by (apply Rmult_le_compat_r; lra).
          replace (7 / 2 * (1 + uu) ^ 7 * ee) with (7 / 2 * ((1 + uu) ^ 7 * ee)) by field.
          lra. }
        assert (B7 : m * (4 * (1 + uu) ^ 8 * ee) <= m * C0).
        { apply Rmult_le_compat_l. lra. generalize (bpow_gt_0 radix2 (emin + prec - 1)). lra. }
        assert (B8 : (1 + uu) * ((1 + uu) * ((1 + uu) ^ 5 * h + m * (h * K) + h)) <=
                     (1 + uu) * ((1 + uu) * (m * (h * (7 * (1 + uu) ^ 5))))).
        { apply Rmult_le_compat_l. lra. apply Rmult_le_compat_l. lra. exact B2. }
        lra. }
      assert (B9 : (1 + uu) * ((1 + uu) * ((1 + uu) ^ 5 * h + m * (h * K) + h)) <= (1 + uu) * hm)
        by lra.
      apply Rmult_le_reg_l with (1 + uu). lra. exact B9. }
  unfold L in HT. lra.
Qed.

End ConvRadius.

Theorem conv_radius_correct : conv_radius_spec.
Proof.
intros emin prec Hp ma mb rx ry m g t Fa Fb Fx Fy Fm Fg Ft Pa Pb Px Py Hm Pg Lg Pt. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
exact (conv_radius_facts emin prec Hp ma mb rx ry m g t Ft Pa Pb Px Py Hm Pg Lg Pt).
Qed.

(** * The bound kernels: a true mask gives g <= 1 *)

Lemma bound_dot_1_at_most :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, t, ok) := bound_dot_1 emin prec tie_even m in
  ok = true -> 0 <= g /\ g <= 1 /\ 0 <= t.
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
generalize (bound_dot_1_facts emin prec Hp m Fm Hm Hh).
unfold bound_dot_1. cbv beta iota zeta.
intros [_ [_ [Pg H]]] E. destruct (H E) as [_ [_ Ht]].
apply andb_true_iff in E. destruct E as [_ Eg]. apply Rle_bool_inv in Eg.
split. exact Pg. split. exact (Rle_trans _ _ _ Eg (c6_le emin prec Hh)).
apply Rle_trans with (2 := Ht).
assert (0 <= m) by (destruct Hm; lra). assert (0 <= eta emin) by apply bpow_ge_0.
apply Rmult_le_pos; [apply Rmult_le_pos; lra|lra].
Qed.

Lemma bound_dot_2_at_most :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, t, ok) := bound_dot_2 emin prec tie_even m in
  ok = true -> 0 <= g /\ g <= 1 /\ 0 <= t.
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
generalize (bound_dot_2_facts emin prec Hp m Fm Hm Hh).
unfold bound_dot_2. cbv beta iota zeta.
intros [_ [_ [Pg H]]] E. destruct (H E) as [_ [_ Ht]].
apply andb_true_iff in E. destruct E as [_ Eg]. apply Rle_bool_inv in Eg.
split. exact Pg. split. exact (Rle_trans _ _ _ Eg (c6_le emin prec Hh)).
apply Rle_trans with (2 := Ht).
assert (0 <= m) by (destruct Hm; lra). assert (0 <= eta emin) by apply bpow_ge_0.
apply Rmult_le_pos; [apply Rmult_le_pos; lra|lra].
Qed.

(* The count, a number of terms rounded up: a number of the format, 0 or at least 1, and at
   least the number. *)
Lemma count_facts :
  forall (emin prec : Z) (n : nat), (1 <= prec)%Z ->
  let m := round radix2 (FLT_exp emin prec) Zceil (INR n) in
  fmt emin prec m /\ (m = 0 \/ 1 <= m) /\ INR n <= m.
Proof.
intros emin prec n Hp m.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (L : INR n <= m) by (unfold m; apply (RUp_ge emin prec)).
split. unfold m, fmt. apply generic_format_round; auto with typeclass_instances.
split; [|exact L].
destruct n as [|n].
- left. unfold m. apply round_0; auto with typeclass_instances.
- right. apply Rle_trans with (2 := L). rewrite S_INR. generalize (pos_INR n). lra.
Qed.

(** * Lists *)

Lemma Forall2_firstn_l :
  forall (A B : Type) (P : A -> B -> Prop) (n : nat) (l : list A) (l' : list B),
  Forall2 P l l' -> Forall2 P (firstn n l) (firstn n l').
Proof.
intros A B P n l l' H. revert n.
induction H as [|a b l l' Hab H IH]; intros n; destruct n; cbn [firstn]; constructor; auto.
Qed.

Lemma Forall2_skipn_l :
  forall (A B : Type) (P : A -> B -> Prop) (n : nat) (l : list A) (l' : list B),
  Forall2 P l l' -> Forall2 P (skipn n l) (skipn n l').
Proof.
intros A B P n l l' H. revert n.
induction H as [|a b l l' Hab H IH]; intros n; destruct n; cbn [skipn]; auto; constructor; auto.
Qed.

Lemma Forall2_rev_l :
  forall (A B : Type) (P : A -> B -> Prop) (l : list A) (l' : list B),
  Forall2 P l l' -> Forall2 P (rev l) (rev l').
Proof.
intros A B P l l' H. induction H as [|a b l l' Hab H IH]; cbn [rev].
- constructor.
- apply Forall2_app. exact IH. constructor. exact Hab. constructor.
Qed.

Lemma Forall2_combine_l :
  forall (A A' B B' : Type) (P : A -> A' -> Prop) (Q : B -> B' -> Prop)
         (a : list A) (a' : list A') (b : list B) (b' : list B'),
  Forall2 P a a' -> Forall2 Q b b' ->
  Forall2 (fun p p' => P (fst p) (fst p') /\ Q (snd p) (snd p')) (combine a b) (combine a' b').
Proof.
intros A A' B B' P Q a a' b b' Ha. revert b b'.
induction Ha as [|x x' a a' Hx Ha IH]; intros b b' Hb; cbn [combine].
- constructor.
- destruct Hb as [|y y' b b' Hy Hb]; cbn [combine]; constructor; auto.
Qed.

(* The terms of a coefficient of members chosen entry by entry are, term by term, those of the
   centers. *)
Lemma conv_terms_Forall2 :
  forall (A A' B B' : Type) (P : A -> A' -> Prop) (Q : B -> B' -> Prop)
         (xs : list A) (xs_ : list A') (ys : list B) (ys_ : list B') (j : nat),
  Forall2 P xs xs_ -> Forall2 Q ys ys_ ->
  Forall2 (fun p p_ => P (fst p) (fst p_) /\ Q (snd p) (snd p_))
    (conv_terms xs ys j) (conv_terms xs_ ys_ j).
Proof.
intros A A' B B' P Q xs xs_ ys ys_ j Hx Hy. unfold conv_terms.
rewrite (Forall2_length Hy). apply Forall2_combine_l.
- apply Forall2_skipn_l. apply Forall2_firstn_l. exact Hx.
- apply Forall2_rev_l. apply Forall2_firstn_l. exact Hy.
Qed.

Lemma Forall2_Forall_r :
  forall (A B : Type) (P : A -> B -> Prop) (Q : B -> Prop) (l : list A) (l' : list B),
  (forall a b, P a b -> Q b) -> Forall2 P l l' -> Forall Q l'.
Proof.
intros A B P Q l l' H H2. induction H2 as [|a b l l' Hab _ IH]; constructor; eauto.
Qed.

(** * The coefficient of the members *)

(* A product of members, against the product of the centers. *)
Lemma member_product :
  forall cx cy x_ y_ rx ry : R, Rabs (x_ - cx) <= rx -> Rabs (y_ - cy) <= ry ->
  Rabs (x_ * y_ - cx * cy) <= Rabs cx * ry + Rabs cy * rx + rx * ry.
Proof.
intros cx cy x_ y_ rx ry Hx Hy.
replace (x_ * y_ - cx * cy) with (cx * (y_ - cy) + cy * (x_ - cx) + (x_ - cx) * (y_ - cy)) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rle_trans with (Rabs (cx * (y_ - cy)) + Rabs (cy * (x_ - cx)) + Rabs ((x_ - cx) * (y_ - cy))).
{ apply Rplus_le_compat_r. apply Rabs_triang. }
rewrite !Rabs_mult.
assert (0 <= Rabs (x_ - cx)) by apply Rabs_pos. assert (0 <= Rabs (y_ - cy)) by apply Rabs_pos.
assert (0 <= Rabs cx) by apply Rabs_pos. assert (0 <= Rabs cy) by apply Rabs_pos.
apply Rplus_le_compat; [apply Rplus_le_compat; apply Rmult_le_compat_l; assumption|].
apply Rmult_le_compat; assumption.
Qed.

Lemma sum_members :
  forall (A B : Type) (vx : A -> R) (vy : B -> R) (rx ry : R)
         (T : list (A * B)) (T_ : list (R * R)),
  Forall2 (fun p p_ => Rabs (fst p_ - vx (fst p)) <= rx /\ Rabs (snd p_ - vy (snd p)) <= ry) T T_ ->
  Rabs (sumR (map (fun q => fst q * snd q) T_) - sumR (map (fun p => vx (fst p) * vy (snd p)) T)) <=
  sumR (map (fun p => Rabs (vx (fst p)) * ry + Rabs (vy (snd p)) * rx + rx * ry) T).
Proof.
intros A B vx vy rx ry T T_ H. induction H as [|p p_ T T_ [Hx Hy] _ IH]; cbn [map sumR].
- replace (0 - 0) with 0 by ring. rewrite Rabs_R0. apply Rle_refl.
- match goal with |- Rabs (?a + ?b - (?c + ?d)) <= _ =>
    replace (a + b - (c + d)) with ((a - c) + (b - d)) by ring end.
  apply Rle_trans with (1 := Rabs_triang _ _).
  apply Rplus_le_compat; [apply member_product; assumption|exact IH].
Qed.

Lemma sumR_le_count :
  forall (A : Type) (f : A -> R) (K : R) (l : list A),
  Forall (fun a => f a <= K) l -> sumR (map f l) <= INR (length l) * K.
Proof.
intros A f K l H. induction H as [|a l Ha _ IH]; cbn [map sumR length].
- simpl. lra.
- rewrite S_INR. lra.
Qed.

(* The coefficient j of the members, against a coefficient S within g sum |c_x c_y| + t of the
   exact sum of the products of the centers: within m (Ka ry + Kb rx + rx ry) + g m Ka Kb + t,
   Ka and Kb bounds of the centers, for at most m terms. *)
Lemma coef_bound :
  forall (A B : Type) (vx : A -> R) (vy : B -> R) (xs : list A) (ys : list B)
         (xs_ ys_ : list R) (rx ry Ka Kb m g t S : R) (j : nat),
  0 <= rx -> 0 <= ry -> 0 <= g -> 0 <= Ka -> 0 <= Kb ->
  (forall x, In x xs -> Rabs (vx x) <= Ka) -> (forall y, In y ys -> Rabs (vy y) <= Kb) ->
  INR (Nat.min (length xs) (length ys)) <= m ->
  Forall2 (fun x x_ => Rabs (x_ - vx x) <= rx) xs xs_ ->
  Forall2 (fun y y_ => Rabs (y_ - vy y) <= ry) ys ys_ ->
  Rabs (S - sumR (map (fun p => vx (fst p) * vy (snd p)) (conv_terms xs ys j))) <=
    g * sumabs (map (fun p => vx (fst p) * vy (snd p)) (conv_terms xs ys j)) + t ->
  Rabs (sumR (map (fun q => fst q * snd q) (conv_terms xs_ ys_ j)) - S) <=
    m * (Ka * ry + Kb * rx + rx * ry) + g * m * (Ka * Kb) + t.
Proof.
intros A B vx vy xs ys xs_ ys_ rx ry Ka Kb m g t S j Px Py Pg PKa PKb HKa HKb Hn HX HY HS.
pose proof (conv_terms_Forall2 _ _ _ _ _ _ xs xs_ ys ys_ j HX HY) as Hmem.
assert (In_T : Forall (fun p => In (fst p) xs /\ In (snd p) ys) (conv_terms xs ys j)).
{ apply (conv_terms_Forall A B (fun x => In x xs) (fun y => In y ys)); apply Forall_forall; auto. }
assert (Ln : INR (length (conv_terms xs ys j)) <= m).
{ apply Rle_trans with (2 := Hn). apply le_INR. apply conv_terms_length. }
set (T := conv_terms xs ys j) in *. set (T_ := conv_terms xs_ ys_ j) in *.
set (f := fun p : A * B => vx (fst p) * vy (snd p)) in *.
pose proof (sum_members A B vx vy rx ry T T_ Hmem) as SM. fold f in SM.
set (n := INR (length T)) in *.
assert (P0 : 0 <= n) by apply pos_INR.
assert (L1 : sumR (map (fun p => Rabs (vx (fst p)) * ry + Rabs (vy (snd p)) * rx + rx * ry) T) <=
             n * (Ka * ry + Kb * rx + rx * ry)).
{ apply sumR_le_count. revert In_T. apply Forall_impl. intros p [Ix Iy].
  pose proof (HKa _ Ix) as Hx. pose proof (HKb _ Iy) as Hy.
  apply Rplus_le_compat_r. apply Rplus_le_compat; apply Rmult_le_compat_r; assumption. }
assert (L2 : sumabs (map f T) <= n * (Ka * Kb)).
{ unfold sumabs. rewrite map_map. apply sumR_le_count. revert In_T. apply Forall_impl.
  intros p [Ix Iy]. unfold f. rewrite Rabs_mult.
  apply Rmult_le_compat; try apply Rabs_pos; auto. }
assert (Q1 : 0 <= Ka * ry + Kb * rx + rx * ry).
{ assert (0 <= Ka * ry) by (apply Rmult_le_pos; assumption).
  assert (0 <= Kb * rx) by (apply Rmult_le_pos; assumption).
  assert (0 <= rx * ry) by (apply Rmult_le_pos; assumption). lra. }
assert (Q2 : 0 <= Ka * Kb) by (apply Rmult_le_pos; assumption).
assert (A1 : n * (Ka * ry + Kb * rx + rx * ry) <= m * (Ka * ry + Kb * rx + rx * ry))
  by (apply Rmult_le_compat_r; assumption).
assert (A2 : g * sumabs (map f T) <= g * (n * (Ka * Kb))) by (apply Rmult_le_compat_l; assumption).
assert (A3 : g * (n * (Ka * Kb)) <= g * (m * (Ka * Kb))).
{ apply Rmult_le_compat_l. exact Pg. apply Rmult_le_compat_r; assumption. }
assert (TR : Rabs (sumR (map (fun q => fst q * snd q) T_) - S) <=
             Rabs (sumR (map (fun q => fst q * snd q) T_) - sumR (map f T)) +
             Rabs (S - sumR (map f T))).
{ replace (sumR (map (fun q => fst q * snd q) T_) - S) with
    ((sumR (map (fun q => fst q * snd q) T_) - sumR (map f T)) + - (S - sumR (map f T))) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. apply Rle_refl. }
lra.
Qed.

(** * The folds *)

Theorem bv_conv_1_correct : bv_conv_1_spec.
Proof.
intros emin prec Hp rx ry xs ys Frx Prx Fry Pry Hx Hy Hh Hok. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold bv_conv_1_ok, bv_conv_1_bound in Hok. unfold bv_conv_1_radius, bv_conv_1_bound.
destruct (count_facts emin prec (Nat.min (length xs) (length ys)) Hp1) as [Fm [Hm Lm]].
change (round radix2 (FLT_exp emin prec) Zceil (INR (Nat.min (length xs) (length ys))))
  with (bv_conv_1_count emin prec xs ys) in Fm, Hm, Lm.
set (m := bv_conv_1_count emin prec xs ys) in *.
generalize (bound_dot_1_at_most emin prec Hp1 m Fm Hm Hh) (bound_dot_1_facts emin prec Hp1 m Fm Hm Hh).
destruct (bound_dot_1 emin prec tie_even m) as [[g t] ok] eqn:Eb. cbn [fst snd] in Hok |- *.
rewrite Hok in Eb. intros AM [Fg [Ft _]]. destruct (AM Hok) as [Pg [Lg Pt]].
rewrite (maxc_seq_value R bv_conv_1_record (fun w => Rabs w) record_1_eq xs).
rewrite (maxc_seq_value R bv_conv_1_record (fun w => Rabs w) record_1_eq ys). cbn [fst].
set (Ma := maxl (map (fun w => Rabs w) xs)). set (Mb := maxl (map (fun w => Rabs w) ys)).
destruct (maxl_facts emin prec R (fun w => w) xs Hx) as [FMa [PMa HMa]].
destruct (maxl_facts emin prec R (fun w => w) ys Hy) as [FMb [PMb HMb]].
cbv beta in FMa, PMa, HMa, FMb, PMb, HMb. fold Ma in FMa, PMa, HMa. fold Mb in FMb, PMb, HMb.
destruct (conv_radius_facts emin prec Hp2 Ma Mb rx ry m g t Ft PMa PMb Prx Pry Hm Pg Lg Pt)
  as [Fr Lr].
split. exact Fr.
pose proof (conv_1_bound emin prec Hp1 Hh xs ys m g t Hx Hy Fm Hm Lm Eb) as Cb.
split.
- eapply Forall2_Forall_r; [|exact Cb]. cbv beta zeta. intros j s [F _]. exact F.
- intros xs_ ys_ HX HY. revert Cb. apply Forall2_impl. intros j s [_ Bs]. cbv zeta in Bs.
  assert (U1 : Ma <= (1 + u prec) * Ma).
  { assert (0 <= u prec * Ma) by (apply Rmult_le_pos; [apply bpow_ge_0|exact PMa]). lra. }
  assert (U2 : Mb <= (1 + u prec) * Mb).
  { assert (0 <= u prec * Mb) by (apply Rmult_le_pos; [apply bpow_ge_0|exact PMb]). lra. }
  apply Rle_trans with (2 := Lr).
  apply Rle_trans with (m * (Ma * ry + Mb * rx + rx * ry) + g * m * (Ma * Mb) + t).
  + apply (coef_bound R R (fun x => x) (fun y => y) xs ys xs_ ys_ rx ry Ma Mb m g t s j
             Prx Pry Pg PMa PMb HMa HMb Lm HX HY Bs).
  + assert (0 <= m) by (destruct Hm; lra).
    assert (E1 : Ma * ry <= (1 + u prec) * Ma * ry) by (apply Rmult_le_compat_r; assumption).
    assert (E2 : Mb * rx <= (1 + u prec) * Mb * rx) by (apply Rmult_le_compat_r; assumption).
    assert (E3 : m * (Ma * ry + Mb * rx + rx * ry) <=
                 m * ((1 + u prec) * Ma * ry + (1 + u prec) * Mb * rx + rx * ry))
      by (apply Rmult_le_compat_l; lra).
    assert (E4 : Ma * Mb <= (1 + u prec) ^ 2 * Ma * Mb).
    { assert (1 <= (1 + u prec) ^ 2).
      { apply pow_R1_Rle. generalize (bpow_ge_0 radix2 (- prec)). unfold u. lra. }
      assert (0 <= Ma * Mb) by (apply Rmult_le_pos; assumption). nra. }
    assert (E5 : g * m * (Ma * Mb) <= g * m * (1 + u prec) ^ 2 * Ma * Mb).
    { replace (g * m * (1 + u prec) ^ 2 * Ma * Mb) with (g * m * ((1 + u prec) ^ 2 * Ma * Mb))
        by ring.
      apply Rmult_le_compat_l. apply Rmult_le_pos; assumption. exact E4. }
    lra.
Qed.

Theorem bv_conv_2_correct : bv_conv_2_spec.
Proof.
intros emin prec Hp rx ry xs ys Frx Prx Fry Pry Hx Hy Hh Hok. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hp1 : (1 <= prec)%Z) by lia.
unfold bv_conv_2_ok, bv_conv_2_bound in Hok. unfold bv_conv_2_radius, bv_conv_2_bound.
destruct (count_facts emin prec (Nat.min (length xs) (length ys)) Hp1) as [Fm [Hm Lm]].
change (round radix2 (FLT_exp emin prec) Zceil (INR (Nat.min (length xs) (length ys))))
  with (bv_conv_2_count emin prec xs ys) in Fm, Hm, Lm.
set (m := bv_conv_2_count emin prec xs ys) in *.
generalize (bound_dot_2_at_most emin prec Hp m Fm Hm Hh) (bound_dot_2_facts emin prec Hp m Fm Hm Hh).
destruct (bound_dot_2 emin prec tie_even m) as [[g t] ok] eqn:Eb. cbn [fst snd] in Hok |- *.
rewrite Hok in Eb. intros AM [Fg [Ft _]]. destruct (AM Hok) as [Pg [Lg Pt]].
rewrite (maxc_seq_value (R * R) bv_conv_2_record (fun w => Rabs (fst w)) record_2_eq xs).
rewrite (maxc_seq_value (R * R) bv_conv_2_record (fun w => Rabs (fst w)) record_2_eq ys). cbn [fst].
set (Ma := maxl (map (fun w => Rabs (fst w)) xs)). set (Mb := maxl (map (fun w => Rabs (fst w)) ys)).
assert (Fx0 : Forall (fun x => fmt emin prec (fst x)) xs).
{ revert Hx. apply Forall_impl. intros x N. apply N. }
assert (Fy0 : Forall (fun y => fmt emin prec (fst y)) ys).
{ revert Hy. apply Forall_impl. intros y N. apply N. }
destruct (maxl_facts emin prec (R * R) fst xs Fx0) as [FMa [PMa HMa]].
destruct (maxl_facts emin prec (R * R) fst ys Fy0) as [FMb [PMb HMb]].
fold Ma in FMa, PMa, HMa. fold Mb in FMb, PMb, HMb.
destruct (conv_radius_facts emin prec Hp2 Ma Mb rx ry m g t Ft PMa PMb Prx Pry Hm Pg Lg Pt)
  as [Fr Lr].
split. exact Fr.
pose proof (conv_2_bound emin prec Hp Hh xs ys m g t Hx Hy Fm Hm Lm Eb) as Cb.
split.
- eapply Forall2_Forall_r; [|exact Cb]. cbv beta zeta. intros j s [F _]. exact F.
- intros xs_ ys_ HX HY. revert Cb. apply Forall2_impl. intros j s [_ Bs]. cbv zeta in Bs.
  assert (PU : 0 <= 1 + u prec) by (generalize (bpow_ge_0 radix2 (- prec)); unfold u; lra).
  assert (KA : forall x, In x xs -> Rabs (fst x + snd x) <= (1 + u prec) * Ma).
  { intros x Hin. apply Rle_trans with ((1 + u prec) * Rabs (fst x)).
    - apply (normalized_2_abs_le emin prec). exact (proj1 (Forall_forall _ xs) Hx x Hin).
    - apply Rmult_le_compat_l. exact PU. exact (HMa x Hin). }
  assert (KB : forall y, In y ys -> Rabs (fst y + snd y) <= (1 + u prec) * Mb).
  { intros y Hin. apply Rle_trans with ((1 + u prec) * Rabs (fst y)).
    - apply (normalized_2_abs_le emin prec). exact (proj1 (Forall_forall _ ys) Hy y Hin).
    - apply Rmult_le_compat_l. exact PU. exact (HMb y Hin). }
  apply Rle_trans with (2 := Lr).
  apply Rle_trans with (m * ((1 + u prec) * Ma * ry + (1 + u prec) * Mb * rx + rx * ry) +
                        g * m * ((1 + u prec) * Ma * ((1 + u prec) * Mb)) + t).
  + exact (coef_bound (R * R) (R * R) (fun x => fst x + snd x) (fun y => fst y + snd y) xs ys
             xs_ ys_ rx ry ((1 + u prec) * Ma) ((1 + u prec) * Mb) m g t (fst s + snd s) j
             Prx Pry Pg (Rmult_le_pos _ _ PU PMa) (Rmult_le_pos _ _ PU PMb) KA KB Lm HX HY Bs).
  + right. ring.
Qed.
