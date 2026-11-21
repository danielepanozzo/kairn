(* The kernels of the accumulator in the real model: the generated statements of acc_add_1,
   acc_add_2, acc_mul_1, acc_mul_2, acc_merge_1, acc_merge_2, acc_radius_1 and
   acc_radius_2 (proofs/gen/Statements.v).

   An accumulator (docs/developer/design/milestone2.md, "The accumulator") holds a
   running k-number s, a running sum a of the magnitudes of the leading limbs of what
   was added, and a count. Each of the six state kernels returns the next s, which is t,
   and the next a, which is b:

       kernel        t                                  b
       acc_add_1     RN (s + x)       (add_1_1)         RN (a + |x|)
       acc_add_2     add_2_2 (s, x)                     RN (a + |x0|)
       acc_mul_1     RN (x y + s)     (dot_step_1)      RN (|x| |y| + a)
       acc_mul_2     dot_step_2 (s, x, y)               RN (|x0| |y0| + a)
       acc_merge_1   RN (s + v)       (add_1_1)         RN (a + c)
       acc_merge_2   add_2_2 (s, v)                     RN (a + c)

   The element x of acc_add_k is a value of the program and passes through the guard,
   RN (x + 0), which returns a number of the format unchanged (guard_real_any); so each
   t is the theorem of its addition or step (add_1_1_correct, add_2_2_correct,
   dot_step_2_correct), and each b is one rounding to nearest, the claim itself.

   The radius (acc_radius_1, which acc_radius_2 calls). With u = 2^-prec, eta = 2^emin,
   N = eta / (2 u) = 2^(emin + prec - 1) the smallest normal number, RN rounding to
   nearest and up( ) rounding a constant up, the listing is

       q  = RN (m up ((1 + u) u + N))         d = RN (q up (2))       w = RN (q d + q)
       c  = RN (m up (N) + a)                 e = RN (c w + c)        f = RN (e g)
       s  = RN (f + t)                        r = RN (s up ((1 + u)^8) + up ((1 + u)^7 eta / 2 + N))
       ok = (d <= up (1)) and (a - a = a - a)

   and the statement: r is a number of the format, and if ok then
       r >= g (1 + u)^2 (1 + m u + 2 m^2 u^2) (a + m eta / 2) + t     and     m u <= 1/2,
   for a, g, t >= 0 of the format and m = 0 or m >= 1 of the format.

   The argument. Two facts about one rounding to nearest of y >= 0: in general
   y <= (1 + u) (RN y + eta / 2) (rnd_lower, Ball2.v), with no eta / 2 when y is a sum of
   two numbers of the format (rnd_sum_lower, BoundKernels.v), and with none when y >= N
   (rnd_lower_normal below: the rounding of the normal range has the relative error
   u / (1 + u), Flocq's relative_error_N_FLX'). Then:
   1. The tail (acc_tail): for e, g, t >= 0, r >= (1 + u)^5 e g + t. One factor 1 + u
      for each of f, s and r, the eta / 2 that f may lose covered by the constant added
      in r, which is at least (1 + u)^7 eta / 2 + N and so at least the
      (1 + u)^7 eta / 2 + (1 + u) eta / 2 that it costs.
   2. For m = 0: q = d = w = 0 and c = e = a, so r >= (1 + u)^5 a g + t, which is the
      claim. For m >= 1: m up ((1 + u) u + N) >= N, so q >= N and q >= m u; d >= 2 q;
      q d + q >= N, so (1 + u) w >= q + 2 q^2 >= m u + 2 m^2 u^2; m N + a >= N and
      N >= eta / 2, so (1 + u) c >= a + m eta / 2; c w + c >= N, so
      (1 + u) e >= c (1 + w). Hence (1 + u)^3 e >= (1 + m u + 2 m^2 u^2) (a + m eta / 2)
      and the tail gives the claim. Neither case uses ok: the bound on r holds always.
   3. The mask. ok gives d <= up (1), and d >= 2 q >= 2 m u. If emin <= 0 then 1 is a
      number of the format, up (1) = 1, and m u <= 1/2. If emin > 0 then up (1) <= eta
      < 2 N <= d for m >= 1, so ok is false; for m = 0 the claim is 0 <= 1/2. The test
      a - a = a - a is always true in the real model.
   No hypothesis on the format is needed beyond prec >= 2 (so that u <= 1/4 and
   u (1 + u) <= 1), not even that it contains 1/2: the generated statement has none. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Relative Mult_error.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard OneLimb Add22 Mul22 Ball2 BoundKernels StepKernels.
Open Scope R_scope.

(** * The six state kernels *)

Theorem acc_add_1_correct : acc_add_1_spec.
Proof.
intros emin prec Hp s a x Fs Fa Fx Ha.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold acc_add_1. cbv beta iota zeta.
rewrite (guard_real_any emin prec tie_even x Fx).
destruct (add_1_1_correct emin prec Hp s x Fs Fx) as [Ft [Et Bt]].
unfold add_1_1 in Ft, Et, Bt. cbv zeta in Ft, Et, Bt.
split. exact Ft.
split. limb_format.
split. exact Et.
split. exact Bt.
reflexivity.
Qed.

Theorem acc_merge_1_correct : acc_merge_1_spec.
Proof.
intros emin prec Hp s a v c Fs Fa Fv Fc Ha Hc.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold acc_merge_1. cbv beta iota zeta.
destruct (add_1_1_correct emin prec Hp s v Fs Fv) as [Ft [Et Bt]].
unfold add_1_1 in Ft, Et, Bt. cbv zeta in Ft, Et, Bt.
split. exact Ft.
split. limb_format.
split. exact Et.
split. exact Bt.
reflexivity.
Qed.

Theorem acc_mul_1_correct : acc_mul_1_spec.
Proof.
intros emin prec Hp s a x y Fs Fa Fx Fy Ha.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold acc_mul_1. cbv beta iota zeta.
split. limb_format.
split. limb_format.
split; unfold RN; f_equal; ring.
Qed.

(* acc_mul_1 on x and y guarded (rule R3, the factors of a fused operation): numbers of the
   format pass the guard unchanged (guard_real_any), so the statement is that of acc_mul_1. *)
Theorem acc_mul_entry_1_correct : acc_mul_entry_1_spec.
Proof.
intros emin prec Hp s a x y Fs Fa Fx Fy Ha.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold acc_mul_entry_1. cbv beta iota zeta.
rewrite (guard_real_any emin prec tie_even x Fx), (guard_real_any emin prec tie_even y Fy).
split. limb_format.
split. limb_format.
split; unfold RN; f_equal; ring.
Qed.

Theorem acc_add_2_correct : acc_add_2_spec.
Proof.
intros emin prec Hp s0 s1 a x0 x1 Ns Fa Nx Ha.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold acc_add_2. cbv zeta.
pose proof Nx as [F0 [F1 _]].
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
generalize (add_2_2_correct emin prec Hp s0 s1 x0 x1 Ns Nx).
destruct (add_2_2 emin prec tie_even s0 s1 x0 x1) as [t0 t1]. intros [Nt Et].
split. limb_format.
split. exact Nt.
split. exact Et.
reflexivity.
Qed.

Theorem acc_merge_2_correct : acc_merge_2_spec.
Proof.
intros emin prec Hp s0 s1 a v0 v1 c Ns Fa Nv Fc Ha Hc.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold acc_merge_2. cbv zeta.
generalize (add_2_2_correct emin prec Hp s0 s1 v0 v1 Ns Nv).
destruct (add_2_2 emin prec tie_even s0 s1 v0 v1) as [t0 t1]. intros [Nt Et].
split. limb_format.
split. exact Nt.
split. exact Et.
reflexivity.
Qed.

Theorem acc_mul_2_correct : acc_mul_2_spec.
Proof.
intros emin prec Hp s0 s1 a x0 x1 y0 y1 Ns Fa Nx Ny Ha.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
unfold acc_mul_2. cbv zeta.
generalize (dot_step_2_correct emin prec Hp s0 s1 x0 x1 y0 y1 Ns Nx Ny).
destruct (dot_step_2 emin prec tie_even s0 s1 x0 x1 y0 y1) as [t0 t1]. intros [Nt Et].
split. limb_format.
split. exact Nt.
split. exact Et.
unfold RN. f_equal. ring.
Qed.

(* acc_mul_2 on the limbs of x and y guarded (rule R3, the factors of a fused operation): the limbs
   of a normalized pair are numbers of the format, which pass the guard unchanged (guard_real_any),
   so the statement is that of acc_mul_2. *)
Theorem acc_mul_entry_2_correct : acc_mul_entry_2_spec.
Proof.
intros emin prec Hp s0 s1 a x0 x1 y0 y1 Ns Fa Nx Ny Ha.
unfold acc_mul_entry_2. cbv zeta.
destruct Nx as [F0 [F1 Hx]]. destruct Ny as [G0 [G1 Hy]].
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1),
        (guard_real_any emin prec tie_even y0 G0), (guard_real_any emin prec tie_even y1 G1).
assert (Nx : normalized_2 emin prec x0 x1) by (split; [exact F0 | split; [exact F1 | exact Hx]]).
assert (Ny : normalized_2 emin prec y0 y1) by (split; [exact G0 | split; [exact G1 | exact Hy]]).
generalize (acc_mul_2_correct emin prec Hp s0 s1 a x0 x1 y0 y1 Ns Fa Nx Ny Ha).
destruct (acc_mul_2 emin prec tie_even s0 s1 a x0 x1 y0 y1) as [[t0 t1] b]. intros H. exact H.
Qed.

(** * The radius *)

Section Radius.
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

(* The smallest normal number is eta / (2 u), and it is at least (1 + u) eta / 2. *)
Lemma NN_eq : ee / (2 * uu) = NN.
Proof. exact (nrm_eq emin prec). Qed.

Lemma NN_ge : (1 + uu) * (ee / 2) <= NN.
Proof.
rewrite <- NN_eq.
assert (K : (1 + uu) * (ee / 2) * (2 * uu) <= ee).
{ replace ((1 + uu) * (ee / 2) * (2 * uu)) with (ee * (uu * (1 + uu))) by field.
  assert (H : uu * (1 + uu) <= 1) by nra.
  generalize (Rmult_le_compat_l ee _ _ (Rlt_le _ _ e0) H). lra. }
apply Rmult_le_reg_r with (2 * uu). lra.
replace (ee / (2 * uu) * (2 * uu)) with ee by (field; lra). exact K.
Qed.

Lemma NN_ge_half : ee / 2 <= NN.
Proof.
generalize NN_ge. intros G.
assert (K : 0 <= uu * (ee / 2)) by (apply Rmult_le_pos; lra). lra.
Qed.

Lemma NN_format : format NN.
Proof. apply generic_format_FLT_bpow. exact prec_gt_0_. lia. Qed.

Lemma NN_pos : 0 < NN.
Proof. apply bpow_gt_0. Qed.

(* One rounding to nearest in the normal range loses at most the factor 1 + u. *)
Lemma rnd_lower_normal : forall x : R, NN <= x -> x <= (1 + uu) * rnd x.
Proof.
intros x Hx.
assert (Hx0 : 0 <= x) by (generalize NN_pos; lra).
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

(* A rounding to nearest is at least a number of the format below its operand. *)
Lemma rnd_ge_format : forall x y : R, format y -> y <= x -> y <= rnd x.
Proof. intros x y Fy H. apply round_ge_generic; auto with typeclass_instances. Qed.

(* The last three lines: r >= (1 + u)^5 e g + t. *)
Lemma acc_tail :
  forall e g t K C : R, 0 <= e -> 0 <= g -> format t -> 0 <= t ->
  (1 + uu) ^ 8 <= K -> (1 + uu) ^ 7 * ee / 2 + NN <= C ->
  let f := rnd (e * g + 0) in
  let s := rnd (f + t) in
  (1 + uu) ^ 5 * (e * g) + t <= rnd (s * K + C).
Proof.
intros e g t K C He Hg Ft Ht HK HC f s.
assert (P1 : 1 <= 1 + uu) by lra.
assert (Pn : forall n : nat, 1 <= (1 + uu) ^ n) by (intros n; apply pow_R1_Rle; exact P1).
assert (Heg : 0 <= e * g) by (apply Rmult_le_pos; assumption).
assert (Hf0 : 0 <= f) by (unfold f; apply (rnd_ge_0 emin prec); lra).
assert (Ff : format f) by (unfold f; apply generic_format_round; auto with typeclass_instances).
assert (Hs0 : 0 <= s) by (unfold s; apply (rnd_ge_0 emin prec); lra).
assert (Lf : e * g + 0 <= (1 + uu) * (f + ee / 2)) by (apply (rnd_lower emin prec); lra).
assert (Ls : f + t <= (1 + uu) * s) by (apply (rnd_sum_lower emin prec); assumption || lra).
assert (HK0 : 0 <= K) by (generalize (Pn 8%nat); lra).
assert (Hee7 : 0 <= (1 + uu) ^ 7 * ee) by (apply Rmult_le_pos; [generalize (Pn 7%nat) | ]; lra).
assert (HC0 : 0 <= C) by (generalize NN_pos; lra).
assert (Lr : (1 + uu) ^ 7 * s + (1 + uu) ^ 6 * (ee / 2) <= rnd (s * K + C)).
{ assert (G1 : (1 + uu) * (1 + uu) ^ 7 <= K).
  { replace ((1 + uu) * (1 + uu) ^ 7) with ((1 + uu) ^ 8) by ring. exact HK. }
  assert (G2 : (1 + uu) * ((1 + uu) ^ 6 * (ee / 2) + ee / 2) <= C).
  { generalize NN_ge. intros G.
    replace ((1 + uu) * ((1 + uu) ^ 6 * (ee / 2) + ee / 2))
      with ((1 + uu) ^ 7 * ee / 2 + (1 + uu) * (ee / 2)) by field.
    lra. }
  exact (radius_tail emin prec s K C ((1 + uu) ^ 7) ((1 + uu) ^ 6 * (ee / 2)) Hs0 HK0 HC0 G1 G2). }
assert (P5 := Pn 5%nat). assert (P6 := Pn 6%nat).
assert (K1 : (1 + uu) ^ 6 * (f + t) <= (1 + uu) ^ 7 * s).
{ replace ((1 + uu) ^ 7 * s) with ((1 + uu) ^ 6 * ((1 + uu) * s)) by ring.
  apply Rmult_le_compat_l. lra. exact Ls. }
assert (K2 : (1 + uu) ^ 5 * (e * g) <= (1 + uu) ^ 6 * (f + ee / 2)).
{ replace ((1 + uu) ^ 6 * (f + ee / 2)) with ((1 + uu) ^ 5 * ((1 + uu) * (f + ee / 2))) by ring.
  apply Rmult_le_compat_l. lra. lra. }
assert (K3 : t <= (1 + uu) ^ 6 * t).
{ generalize (Rmult_le_compat_r t 1 _ Ht P6). lra. }
lra.
Qed.

(* The constants of the listing (proofs/gen/Model.v). *)
Lemma C0_ge : (1 + uu) * uu + NN <= up_acc_radius_1_0 emin prec.
Proof. rewrite <- NN_eq. unfold up_acc_radius_1_0, u, eta. apply (RUp_ge emin prec). Qed.

Lemma c2_ge : 2 <= up_bound_dot_1_2 emin prec.
Proof. unfold up_bound_dot_1_2. apply (RUp_ge emin prec). Qed.

Lemma N_eq : up_ball_mul_pow2_1_0 emin prec = NN.
Proof.
unfold up_ball_mul_pow2_1_0. fold (eta emin) (u prec). rewrite NN_eq.
apply (RUp_id emin prec). exact NN_format.
Qed.

Lemma K_ge : (1 + uu) ^ 8 <= up_acc_radius_1_3 emin prec.
Proof. unfold up_acc_radius_1_3, u. apply (RUp_ge emin prec). Qed.

Lemma C_ge : (1 + uu) ^ 7 * ee / 2 + NN <= up_acc_radius_1_4 emin prec.
Proof. rewrite <- NN_eq. unfold up_acc_radius_1_4, u, eta. apply (RUp_ge emin prec). Qed.

(* up (1) is 1 when 1 is a number of the format, and at most eta otherwise. *)
Lemma c6_cases :
  ((emin <= 0)%Z /\ up_bound_dot_1_6 emin prec = 1) \/
  ((0 < emin)%Z /\ up_bound_dot_1_6 emin prec <= ee).
Proof.
unfold up_bound_dot_1_6. destruct (Z_le_gt_dec emin 0) as [H|H].
- left. split. exact H. apply (RUp_id emin prec). change 1 with (bpow radix2 0).
  apply generic_format_FLT_bpow. exact prec_gt_0_. lia.
- right. split. lia. apply round_le_generic; auto with typeclass_instances.
  + apply generic_format_bpow. unfold FLT_exp. lia.
  + change 1 with (bpow radix2 0). apply bpow_le. lia.
Qed.

(* Everything that holds of acc_radius_1: the bound on r always, m u <= 1/2 when ok. *)
Lemma acc_radius_1_facts :
  forall a m g t : R, format a -> format m -> format g -> format t ->
  0 <= a -> (m = 0 \/ 1 <= m) -> 0 <= g -> 0 <= t ->
  let '(r, ok) := acc_radius_1 emin prec tie_even a m g t in
  format r /\
  g * (1 + uu) ^ 2 * (1 + m * uu + 2 * m ^ 2 * uu ^ 2) * (a + m * ee / 2) + t <= r /\
  (ok = true -> m * uu <= / 2).
Proof.
intros a m g t Fa Fm Fg Ft Ha Hm Hg Ht.
unfold acc_radius_1. cbv beta iota zeta.
set (C0 := up_acc_radius_1_0 emin prec).
set (c2 := up_bound_dot_1_2 emin prec).
set (K := up_acc_radius_1_3 emin prec).
set (C := up_acc_radius_1_4 emin prec).
set (c6 := up_bound_dot_1_6 emin prec).
rewrite N_eq.
set (q := rnd (m * C0 + 0)).
set (d := rnd (q * c2 + 0)).
set (w := rnd (q * d + q)).
set (c := rnd (m * NN + a)).
set (e := rnd (c * w + c)).
assert (HC0 : (1 + uu) * uu + NN <= C0) by exact C0_ge.
assert (Hc2 : 2 <= c2) by exact c2_ge.
assert (HK : (1 + uu) ^ 8 <= K) by exact K_ge.
assert (HC : (1 + uu) ^ 7 * ee / 2 + NN <= C) by exact C_ge.
assert (NP := NN_pos).
assert (Huu : 0 <= (1 + uu) * uu) by (apply Rmult_le_pos; lra).
assert (HC0p : 0 <= C0) by lra.
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Hq0 : 0 <= q).
{ unfold q. apply (rnd_ge_0 emin prec). generalize (Rmult_le_pos m C0 Hm0 HC0p). lra. }
assert (Fq : format q) by (unfold q; apply generic_format_round; auto with typeclass_instances).
(* d >= 2 q: 2 q is a number of the format below q c2 *)
assert (Hd : 2 * q <= d).
{ unfold d. apply rnd_ge_format.
  - rewrite Rmult_comm, <- pow2_1. apply mult_bpow_pos_exact_FLT; auto with typeclass_instances.
    lia.
  - assert (K1 : q * 2 <= q * c2) by (apply Rmult_le_compat_l; lra). lra. }
assert (Hw0 : 0 <= w).
{ unfold w. apply (rnd_ge_0 emin prec). assert (0 <= q * d) by (apply Rmult_le_pos; lra). lra. }
assert (Hc0 : 0 <= c).
{ unfold c. apply (rnd_ge_0 emin prec). assert (0 <= m * NN) by (apply Rmult_le_pos; lra). lra. }
assert (He0 : 0 <= e).
{ unfold e. apply (rnd_ge_0 emin prec). assert (0 <= c * w) by (apply Rmult_le_pos; lra). lra. }
split. apply generic_format_round; auto with typeclass_instances.
split.
- (* the bound on r *)
  generalize (acc_tail e g t K C He0 Hg Ft Ht HK HC). cbv zeta. intros T.
  apply Rle_trans with (2 := T).
  apply Rplus_le_compat_r.
  destruct Hm as [Hm|Hm].
  + (* no term: e = a *)
    assert (Eq : q = 0).
    { unfold q. rewrite Hm, Rmult_0_l, Rplus_0_l. apply round_0; auto with typeclass_instances. }
    assert (Ew : w = 0).
    { unfold w, d. rewrite Eq, !Rmult_0_l, Rplus_0_l. apply round_0; auto with typeclass_instances. }
    assert (Ec : c = a).
    { unfold c. rewrite Hm, Rmult_0_l, Rplus_0_l. apply round_generic; auto with typeclass_instances. }
    assert (Ee : e = a).
    { unfold e. rewrite Ew, Ec, Rmult_0_r, Rplus_0_l. apply round_generic; auto with typeclass_instances. }
    rewrite Ee, Hm.
    replace (g * (1 + uu) ^ 2 * (1 + 0 * uu + 2 * 0 ^ 2 * uu ^ 2) * (a + 0 * ee / 2))
      with ((1 + uu) ^ 2 * (a * g)) by field.
    apply Rmult_le_compat_r. apply Rmult_le_pos; assumption.
    apply Rle_pow. lra. lia.
  + (* m >= 1 *)
    assert (Q1 : NN <= m * C0 + 0).
    { assert (K1 : 1 * C0 <= m * C0) by (apply Rmult_le_compat_r; lra). lra. }
    assert (HqN : NN <= q) by (unfold q; apply rnd_ge_format; [exact NN_format | exact Q1]).
    assert (Hqm : m * uu <= q).
    { generalize (rnd_lower_normal _ Q1). fold q. intros L.
      assert (K1 : m * ((1 + uu) * uu) <= m * C0) by (apply Rmult_le_compat_l; lra).
      assert (K2 : 0 <= m * NN) by (apply Rmult_le_pos; lra).
      apply Rmult_le_reg_l with (1 + uu). lra. lra. }
    assert (Lw : q + 2 * (q * q) <= (1 + uu) * w).
    { assert (W1 : q * (2 * q) <= q * d) by (apply Rmult_le_compat_l; lra).
      assert (W0 : 0 <= q * (2 * q)) by (apply Rmult_le_pos; lra).
      assert (W2 : NN <= q * d + q) by lra.
      generalize (rnd_lower_normal _ W2). fold w. intros L. lra. }
    assert (Lc : a + m * ee / 2 <= (1 + uu) * c).
    { assert (C1 : NN <= m * NN + a).
      { assert (K1 : 1 * NN <= m * NN) by (apply Rmult_le_compat_r; lra). lra. }
      generalize (rnd_lower_normal _ C1). fold c. intros L.
      generalize NN_ge_half. intros G.
      assert (K1 : m * (ee / 2) <= m * NN) by (apply Rmult_le_compat_l; lra). lra. }
    assert (Le : c * (1 + w) <= (1 + uu) * e).
    { assert (E1 : NN <= c * w + c).
      { assert (C1 : NN <= m * NN + a).
        { assert (K1 : 1 * NN <= m * NN) by (apply Rmult_le_compat_r; lra). lra. }
        assert (HcN : NN <= c) by (unfold c; apply rnd_ge_format; [exact NN_format | exact C1]).
        generalize (Rmult_le_pos c w Hc0 Hw0). lra. }
      generalize (rnd_lower_normal _ E1). fold e. intros L. lra. }
    (* (1 + u) (1 + w) >= 1 + m u + 2 m^2 u^2 *)
    assert (P : 1 + m * uu + 2 * m ^ 2 * uu ^ 2 <= (1 + uu) * (1 + w)).
    { assert (Hmu : 0 <= m * uu) by (apply Rmult_le_pos; lra).
      assert (S1 : (m * uu) * (m * uu) <= q * q) by (apply Rmult_le_compat; lra).
      replace (2 * m ^ 2 * uu ^ 2) with (2 * ((m * uu) * (m * uu))) by ring.
      replace ((1 + uu) * (1 + w)) with (1 + uu + (1 + uu) * w) by ring.
      lra. }
    set (P0 := 1 + m * uu + 2 * m ^ 2 * uu ^ 2) in *.
    set (X := a + m * ee / 2) in *.
    assert (HX0 : 0 <= X) by (unfold X; assert (0 <= m * ee) by (apply Rmult_le_pos; lra); lra).
    assert (HP0 : 0 <= P0).
    { unfold P0. assert (Hmu : 0 <= m * uu) by (apply Rmult_le_pos; lra).
      assert (S2 : 0 <= (m * uu) * (m * uu)) by (apply Rmult_le_pos; lra).
      replace (2 * m ^ 2 * uu ^ 2) with (2 * ((m * uu) * (m * uu))) by ring.
      lra. }
    (* (1 + u)^3 e >= P0 X *)
    assert (E3 : P0 * X <= (1 + uu) ^ 3 * e).
    { assert (K1 : P0 * X <= (1 + uu) * (1 + w) * X) by (apply Rmult_le_compat_r; assumption).
      assert (K2 : (1 + uu) * (1 + w) * X <= (1 + uu) * (1 + w) * ((1 + uu) * c)).
      { apply Rmult_le_compat_l. apply Rmult_le_pos; lra. exact Lc. }
      assert (K3 : (1 + uu) * (1 + w) * ((1 + uu) * c) = (1 + uu) ^ 2 * (c * (1 + w))) by ring.
      assert (K4 : (1 + uu) ^ 2 * (c * (1 + w)) <= (1 + uu) ^ 2 * ((1 + uu) * e)).
      { apply Rmult_le_compat_l. apply pow_le; lra. exact Le. }
      assert (K5 : (1 + uu) ^ 2 * ((1 + uu) * e) = (1 + uu) ^ 3 * e) by ring.
      lra. }
    replace (g * (1 + uu) ^ 2 * P0 * X) with ((1 + uu) ^ 2 * g * (P0 * X)) by ring.
    replace ((1 + uu) ^ 5 * (e * g)) with ((1 + uu) ^ 2 * g * ((1 + uu) ^ 3 * e)) by ring.
    apply Rmult_le_compat_l. apply Rmult_le_pos. apply pow_le; lra. exact Hg. exact E3.
- (* the mask *)
  intros Hok. apply andb_true_iff in Hok. destruct Hok as [Hd6 _].
  apply Rle_bool_inv in Hd6.
  destruct Hm as [Hm|Hm].
  + rewrite Hm. lra.
  + assert (Q1 : NN <= m * C0 + 0).
    { assert (K1 : 1 * C0 <= m * C0) by (apply Rmult_le_compat_r; lra). lra. }
    assert (HqN : NN <= q) by (unfold q; apply rnd_ge_format; [exact NN_format | exact Q1]).
    assert (Hqm : m * uu <= q).
    { generalize (rnd_lower_normal _ Q1). fold q. intros L.
      assert (K1 : m * ((1 + uu) * uu) <= m * C0) by (apply Rmult_le_compat_l; lra).
      assert (K2 : 0 <= m * NN) by (apply Rmult_le_pos; lra).
      apply Rmult_le_reg_l with (1 + uu). lra. lra. }
    destruct c6_cases as [[_ E6]|[He6 L6]].
    * fold c6 in E6. rewrite E6 in Hd6. lra.
    * fold c6 in L6. exfalso.
      assert (L : ee < 2 * NN).
      { unfold eta. rewrite <- pow2_1, <- bpow_plus. apply bpow_lt. lia. }
      lra.
Qed.

End Radius.

Theorem acc_radius_1_correct : acc_radius_1_spec.
Proof.
intros emin prec Hp a m g t Fa Fm Fg Ft Ha Hm Hg Ht.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 2%Z; lia).
generalize (acc_radius_1_facts emin prec Hp a m g t Fa Fm Fg Ft Ha Hm Hg Ht).
destruct (acc_radius_1 emin prec tie_even a m g t) as [r ok].
intros [Fr [Br Mr]].
split. exact Fr.
split.
- intros _. exact Br.
- intros E. generalize (Mr E). lra.
Qed.

Theorem acc_radius_2_correct : acc_radius_2_spec.
Proof.
intros emin prec Hp a m g t Fa Fm Fg Ft Ha Hm Hg Ht.
unfold acc_radius_2.
generalize (acc_radius_1_correct emin prec Hp a m g t Fa Fm Fg Ft Ha Hm Hg Ht).
destruct (acc_radius_1 emin prec tie_even a m g t) as [r ok]. intros H. exact H.
Qed.
