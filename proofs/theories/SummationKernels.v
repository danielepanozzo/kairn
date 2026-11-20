(* Sums and dot products of arrays: the additions of Kairn in the summation theorems.

   Summation.v bounds a sum made in any order by an addition of which only a relative
   error is known. This file shows that the additions of Kairn are such additions, from
   their generated statements as they are, and states what follows for the sums and dot
   products of one and two limbs in the two orders of Folds.v.

   Notation: u = 2^-prec; eta = 2^emin is the smallest positive number; RN is rounding to
   nearest, ties to even; gamma_m(e) = m e / (1 - m e); n is the number of elements.

   The additions (the hypothesis `adds` of Summation.v):

     addition        valid operand            relative error       from
     add_1_1         a number of the format   u / (1 + u)          add_1_1_correct, prec >= 1
     add_2_2         a normalized pair        3 u^2 / (1 - 4 u)    add_2_2_correct, prec >= 3
     add_fast_2_2    a normalized pair        3 u^2                add_fast_2_2_correct, prec >= 2

   The statements of add_1_1 and add_2_2 bound the error by the magnitude of the exact
   sum; |a + b| <= |a| + |b| gives the form relative to the operands. That of
   add_fast_2_2 is in that form already. Each of the three returns the other operand
   when one operand is zero (add_1_1_zero; add_2_2_zero_l and add_2_2_zero_r;
   add_fast_2_2_zero_l and add_fast_2_2_zero_r, by computation), so a loop that starts
   from zero makes n - 1 rounded additions.

   The terms of a dot product:
   - two limbs: mul_2_2, within 4 u^2 |x y| + 3/2 eta of the exact product (mul_2_2_leaf,
     from mul_2_2_correct, prec >= 4);
   - one limb: no product is computed. The step is one fused operation,
     s <- RN (x y + s), which is the addition add_1_1 of the state and of the real
     number x y, not a number of the format. Such an addition has the relative error
     u / (1 + u) and the absolute error eta / 2 (fused_add_tau); the absolute error is
     absent when both operands are numbers of the format (fused_add_weighted). Adding
     to the zero state is rounded like any other step, so the loop makes n rounded
     additions.

   What follows; the two orders have the same bounds:
   - sum_1_seq, sum_1_lanes, sum_2_seq, sum_2_lanes, sum_fast_2_seq, sum_fast_2_lanes:
     the sum of n valid numbers is valid and within gamma_(n-1)(eps) sum |x_i| of the
     exact sum, with no underflow term;
   - dot_2_seq, dot_2_lanes: the dot product of n pairs of normalized pairs is within
     ((1 + 4 u^2) (1 + eps)^(n-1) - 1) sum |x_i y_i| + (1 + eps)^(n-1) n (3/2 eta),
     eps = 3 u^2 / (1 - 4 u), and the first factor is at most gamma_n(4 u^2)
     (dot_2_seq_gamma, dot_2_lanes_gamma);
   - dot_1_seq, dot_1_lanes: the fused dot product of n pairs of real numbers is within
     ((1 + eps)^n - 1) sum |x_i y_i| + (1 + eps)^(n-1) n (eta / 2), eps = u / (1 + u),
     and the first factor is at most gamma_n(eps) (dot_1_seq_gamma, dot_1_lanes_gamma).
     The additions that combine the lanes add nothing to the term in eta.

   How a model of a loop uses these theorems. A model states a loop as
   fold_seq step zero xs or fold_lanes step combine zero W xs, with a step and a
   combination of its own, written limb by limb. It is enough to prove that they are
   equal to the ones named here (add22, dot_step_2, dot_step_1) on every state and
   element, which is a case analysis on the pairs, and to rewrite with fold_seq_ext or
   fold_lanes_ext. *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core Relative.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format OneLimb Add22 AddFast22 Mul22 Ball2 Folds Summation.
Import ListNotations.
Open Scope R_scope.

(** * The constants *)

Lemma u_pos : forall prec : Z, 0 < u prec.
Proof. intros prec. unfold u. apply bpow_gt_0. Qed.

Lemma eta_pos : forall emin : Z, 0 < eta emin.
Proof. intros emin. unfold eta. apply bpow_gt_0. Qed.

(* u / (1 + u), as the statements of add_1_1 and mul_1_1 print it. *)
Lemma eps_1_eq : forall prec : Z, 1 / (1 + u prec) * u prec ^ 1 = u prec / (1 + u prec).
Proof. intros prec. generalize (u_pos prec). intros H. field. lra. Qed.

Lemma eps_1_ge_0 : forall prec : Z, 0 <= u prec / (1 + u prec).
Proof. intros prec. rewrite <- eps_1_eq. exact (proj1 (rel_one_limb prec)). Qed.

(* 3 u^2 / (1 - 4 u), as the statement of add_2_2 prints it. *)
Lemma eps_add_2_eq :
  forall prec : Z, (3 <= prec)%Z ->
  3 / (1 - 4 * u prec) * u prec ^ 2 = 3 * u prec ^ 2 / (1 - 4 * u prec).
Proof.
intros prec Hp. assert (Hu : 0 < u prec <= / 8) by exact (u_bounds prec 3 Hp).
field. lra.
Qed.

Lemma eps_add_2_ge_0 :
  forall prec : Z, (3 <= prec)%Z -> 0 <= 3 * u prec ^ 2 / (1 - 4 * u prec).
Proof.
intros prec Hp. rewrite <- eps_add_2_eq by exact Hp. exact (proj1 (rel_add_2_2 prec Hp)).
Qed.

Lemma eps_square_ge_0 : forall (c : R) (prec : Z), 0 <= c -> 0 <= c * u prec ^ 2.
Proof.
intros c prec Hc. apply Rmult_le_pos. exact Hc. apply pow_le. apply Rlt_le, u_pos.
Qed.

(* From 4 bits of precision the relative error of add_2_2 is at most that of mul_2_2. *)
Lemma eps_add_2_le_mul_2 :
  forall prec : Z, (4 <= prec)%Z -> 3 * u prec ^ 2 / (1 - 4 * u prec) <= 4 * u prec ^ 2.
Proof.
intros prec Hp.
assert (Hu : 0 < u prec <= / 16) by exact (u_bounds prec 4 Hp).
apply Rmult_le_reg_r with (1 - 4 * u prec). lra.
unfold Rdiv.
rewrite (Rmult_assoc (3 * u prec ^ 2) (/ (1 - 4 * u prec)) (1 - 4 * u prec)), Rinv_l by lra.
assert (K : 0 <= u prec ^ 2 * (1 - 16 * u prec)).
{ apply Rmult_le_pos. apply pow_le. lra. lra. }
lra.
Qed.

(** * One limb: add_1_1 *)

(* add_1_1 is an addition of relative error u / (1 + u) on the numbers of the format. *)
Theorem add_1_1_adds :
  forall emin prec : Z, (1 <= prec)%Z ->
  adds (fun x : R => x) (fmt emin prec) (add_1_1 emin prec tie_even) (u prec / (1 + u prec)).
Proof.
intros emin prec Hp a b Fa Fb. cbv beta.
destruct (add_1_1_correct emin prec Hp a b Fa Fb) as [Fs [_ Hb]].
split. exact Fs.
apply Rle_trans with (1 := Hb). rewrite eps_1_eq.
apply Rmult_le_compat_l. apply eps_1_ge_0. apply Rabs_triang.
Qed.

(* Zero is its zero state: 0 + x is rounded to x when x is a number of the format. *)
Theorem add_1_1_zero :
  forall emin prec : Z, (1 <= prec)%Z ->
  zero_identity (fun x : R => x) (fmt emin prec) (add_1_1 emin prec tie_even) 0.
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split; [|split; [|split]].
- apply generic_format_0.
- reflexivity.
- unfold add_1_1. cbv zeta. rewrite Rplus_0_l. apply round_0; auto with typeclass_instances.
- intros x Fx. unfold add_1_1. cbv beta zeta. rewrite Rplus_0_l.
  apply round_generic; auto with typeclass_instances; exact Fx.
Qed.

(* A sum of n numbers of the format, in the sequential order: the result is a number of
   the format, within gamma_(n-1)(u / (1 + u)) times the sum of the magnitudes of the
   exact sum. *)
Theorem sum_1_seq :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall xs : list R, Forall (fmt emin prec) xs ->
  INR (length xs - 1) * (u prec / (1 + u prec)) < 1 ->
  let s := fold_seq (add_1_1 emin prec tie_even) 0 xs in
  fmt emin prec s /\
  Rabs (s - sumR xs) <= gamma (length xs - 1) (u prec / (1 + u prec)) * sumabs xs.
Proof.
intros emin prec Hp xs Hv Hn.
generalize (fold_seq_sum_gamma _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) xs Hv Hn).
cbv beta zeta. rewrite map_id. intros H. exact H.
Qed.

(* The same in the lane order, for every width W. *)
Theorem sum_1_lanes :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall (W : nat) (xs : list R), Forall (fmt emin prec) xs ->
  INR (length xs - 1) * (u prec / (1 + u prec)) < 1 ->
  let s := fold_lanes (add_1_1 emin prec tie_even) (add_1_1 emin prec tie_even) 0 W xs in
  fmt emin prec s /\
  Rabs (s - sumR xs) <= gamma (length xs - 1) (u prec / (1 + u prec)) * sumabs xs.
Proof.
intros emin prec Hp W xs Hv Hn.
generalize (fold_lanes_sum_gamma _ _ _ _ _ _ (eps_1_ge_0 prec) (add_1_1_adds emin prec Hp)
              (add_1_1_zero emin prec Hp) W xs Hv Hn).
cbv beta zeta. rewrite map_id. intros H. exact H.
Qed.

(** * Two limbs: the vocabulary *)

(* A 2-limb number as one value, a pair of real numbers: the generated kernels take and
   return limbs, and a loop needs its state and its elements as values. *)

(* The value of a pair. *)
Definition val2 (x : R * R) : R := fst x + snd x.

(* The pair is normalized. *)
Definition norm2 (emin prec : Z) (x : R * R) : Prop :=
  normalized_2 emin prec (fst x) (snd x).

(* add_2_2 as a function of two pairs. *)
Definition add22 (emin prec : Z) (x y : R * R) : R * R :=
  add_2_2 emin prec tie_even (fst x) (snd x) (fst y) (snd y).

(* add_fast_2_2 as a function of two pairs. *)
Definition addfast22 (emin prec : Z) (x y : R * R) : R * R :=
  add_fast_2_2 emin prec tie_even (fst x) (snd x) (fst y) (snd y).

(* mul_2_2 as a function of two pairs. *)
Definition mul22 (emin prec : Z) (x y : R * R) : R * R :=
  mul_2_2 emin prec tie_even (fst x) (snd x) (fst y) (snd y).

(** * Two limbs: adding to zero *)

Section Zero.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest tie_even)).

Lemma zero_pair_normalized : normalized_2 emin prec 0 0.
Proof.
split. apply generic_format_0. split. apply generic_format_0.
unfold RN. rewrite Rplus_0_l. symmetry. apply round_0; auto with typeclass_instances.
Qed.

(* TwoSum of zero and a number y of the format is (y, 0). *)
Lemma two_sum_zero_l :
  forall y : R, fmt emin prec y -> two_sum emin prec tie_even 0 y = (y, 0).
Proof.
intros y Fy.
assert (Ry : rnd y = y) by (apply round_generic; auto with typeclass_instances; exact Fy).
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
unfold two_sum. cbv zeta.
repeat first [ rewrite Rplus_0_l | rewrite Rplus_0_r | rewrite Rminus_0_r
             | rewrite Rminus_diag | rewrite Ry | rewrite R0 ].
reflexivity.
Qed.

(* Fast2Sum of the two limbs of a normalized pair returns the pair. *)
Lemma fast_two_sum_normalized :
  forall y0 y1 : R, normalized_2 emin prec y0 y1 ->
  fast_two_sum emin prec tie_even y0 y1 = (y0, y1).
Proof.
intros y0 y1 [F0 [F1 Hx]]. unfold RN in Hx.
assert (R1 : rnd y1 = y1) by (apply round_generic; auto with typeclass_instances; exact F1).
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
unfold fast_two_sum. cbv zeta. rewrite <- Hx.
rewrite Rminus_diag, R0, Rminus_0_r, R1. reflexivity.
Qed.

(* add_2_2 with a zero first operand returns the second operand, limb for limb. *)
Lemma add_2_2_zero_l :
  forall y0 y1 : R, normalized_2 emin prec y0 y1 ->
  add_2_2 emin prec tie_even 0 0 y0 y1 = (y0, y1).
Proof.
intros y0 y1 Hn. pose proof Hn as [F0 [F1 _]].
assert (R1 : rnd y1 = y1) by (apply round_generic; auto with typeclass_instances; exact F1).
unfold add_2_2.
rewrite (two_sum_zero_l y0 F0), (two_sum_zero_l y1 F1). cbv beta iota zeta.
replace (0 + y1) with y1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized y0 y1 Hn). cbv beta iota zeta.
replace (0 + y1) with y1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized y0 y1 Hn). reflexivity.
Qed.

(* And with a zero second operand it returns the first. *)
Lemma two_sum_zero_r :
  forall x : R, fmt emin prec x -> two_sum emin prec tie_even x 0 = (x, 0).
Proof.
intros x Fx.
assert (Rx : rnd x = x) by (apply round_generic; auto with typeclass_instances; exact Fx).
assert (R0 : rnd 0 = 0) by (apply round_0; auto with typeclass_instances).
unfold two_sum. cbv zeta.
repeat first [ rewrite Rplus_0_l | rewrite Rplus_0_r | rewrite Rminus_0_r
             | rewrite Rminus_diag | rewrite Rx | rewrite R0 ].
reflexivity.
Qed.

Lemma add_2_2_zero_r :
  forall x0 x1 : R, normalized_2 emin prec x0 x1 ->
  add_2_2 emin prec tie_even x0 x1 0 0 = (x0, x1).
Proof.
intros x0 x1 Hn. pose proof Hn as [F0 [F1 _]].
assert (R1 : rnd x1 = x1) by (apply round_generic; auto with typeclass_instances; exact F1).
unfold add_2_2.
rewrite (two_sum_zero_r x0 F0), (two_sum_zero_r x1 F1). cbv beta iota zeta.
replace (0 + x1) with x1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized x0 x1 Hn). cbv beta iota zeta.
replace (0 + x1) with x1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized x0 x1 Hn). reflexivity.
Qed.

(* So does add_fast_2_2, on both sides. *)
Lemma add_fast_2_2_zero_r :
  forall x0 x1 : R, normalized_2 emin prec x0 x1 ->
  add_fast_2_2 emin prec tie_even x0 x1 0 0 = (x0, x1).
Proof.
intros x0 x1 Hn. pose proof Hn as [F0 [F1 _]].
assert (R1 : rnd x1 = x1) by (apply round_generic; auto with typeclass_instances; exact F1).
unfold add_fast_2_2.
rewrite (two_sum_zero_r x0 F0). cbv beta iota zeta.
replace (x1 + 0) with x1 by ring. rewrite R1.
replace (0 + x1) with x1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized x0 x1 Hn). reflexivity.
Qed.

Lemma add_fast_2_2_zero_l :
  forall y0 y1 : R, normalized_2 emin prec y0 y1 ->
  add_fast_2_2 emin prec tie_even 0 0 y0 y1 = (y0, y1).
Proof.
intros y0 y1 Hn. pose proof Hn as [F0 [F1 _]].
assert (R1 : rnd y1 = y1) by (apply round_generic; auto with typeclass_instances; exact F1).
unfold add_fast_2_2.
rewrite (two_sum_zero_l y0 F0). cbv beta iota zeta.
replace (0 + y1) with y1 by ring. rewrite R1.
replace (0 + y1) with y1 by ring. rewrite R1.
rewrite (fast_two_sum_normalized y0 y1 Hn). reflexivity.
Qed.

End Zero.

(** * Two limbs: add_2_2 and add_fast_2_2 *)

(* add_2_2 is an addition of relative error 3 u^2 / (1 - 4 u) on the normalized pairs. *)
Theorem add_2_2_adds :
  forall emin prec : Z, (3 <= prec)%Z ->
  adds val2 (norm2 emin prec) (add22 emin prec) (3 * u prec ^ 2 / (1 - 4 * u prec)).
Proof.
intros emin prec Hp [x0 x1] [y0 y1] Nx Ny.
unfold add22, norm2, val2 in *. cbn [fst snd] in *.
generalize (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbn [fst snd].
intros [Nz Hb]. split. exact Nz.
apply Rle_trans with (1 := Hb). rewrite (eps_add_2_eq prec Hp).
apply Rmult_le_compat_l. now apply eps_add_2_ge_0. apply Rabs_triang.
Qed.

(* The pair (0, 0) is its zero state. *)
Theorem add_2_2_zero :
  forall emin prec : Z, (1 <= prec)%Z ->
  zero_identity val2 (norm2 emin prec) (add22 emin prec) (0, 0).
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split; [|split; [|split]].
- unfold norm2. cbn [fst snd]. apply zero_pair_normalized.
- unfold val2. cbn [fst snd]. ring.
- unfold add22. cbn [fst snd]. apply add_2_2_zero_l. apply zero_pair_normalized.
- intros [y0 y1] Ny. unfold add22, norm2 in *. cbn [fst snd] in *.
  now rewrite add_2_2_zero_l.
Qed.

(* add_fast_2_2 is an addition of relative error 3 u^2 on the normalized pairs: its
   statement is in this form. *)
Theorem add_fast_2_2_adds :
  forall emin prec : Z, (2 <= prec)%Z ->
  adds val2 (norm2 emin prec) (addfast22 emin prec) (3 * u prec ^ 2).
Proof.
intros emin prec Hp [x0 x1] [y0 y1] Nx Ny.
unfold addfast22, norm2, val2 in *. cbn [fst snd] in *.
generalize (add_fast_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_fast_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbn [fst snd].
intros H. exact H.
Qed.

(* The pair (0, 0) is its zero state too. *)
Theorem add_fast_2_2_zero :
  forall emin prec : Z, (1 <= prec)%Z ->
  zero_identity val2 (norm2 emin prec) (addfast22 emin prec) (0, 0).
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split; [|split; [|split]].
- unfold norm2. cbn [fst snd]. apply zero_pair_normalized.
- unfold val2. cbn [fst snd]. ring.
- unfold addfast22. cbn [fst snd]. apply add_fast_2_2_zero_l. apply zero_pair_normalized.
- intros [y0 y1] Ny. unfold addfast22, norm2 in *. cbn [fst snd] in *.
  now rewrite add_fast_2_2_zero_l.
Qed.

(* A sum of n normalized pairs, in the sequential order: the result is normalized, and
   within gamma_(n-1)(3 u^2 / (1 - 4 u)) times the sum of the magnitudes of the exact
   sum. There is no underflow term. *)
Theorem sum_2_seq :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall xs : list (R * R), Forall (norm2 emin prec) xs ->
  INR (length xs - 1) * (3 * u prec ^ 2 / (1 - 4 * u prec)) < 1 ->
  let s := fold_seq (add22 emin prec) (0, 0) xs in
  norm2 emin prec s /\
  Rabs (val2 s - sumR (map val2 xs)) <=
    gamma (length xs - 1) (3 * u prec ^ 2 / (1 - 4 * u prec)) * sumabs (map val2 xs).
Proof.
intros emin prec Hp xs Hv Hn.
assert (Hp1 : (1 <= prec)%Z) by lia.
exact (fold_seq_sum_gamma _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
         (add_2_2_zero emin prec Hp1) xs Hv Hn).
Qed.

(* The same in the lane order, for every width W. *)
Theorem sum_2_lanes :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall (W : nat) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  INR (length xs - 1) * (3 * u prec ^ 2 / (1 - 4 * u prec)) < 1 ->
  let s := fold_lanes (add22 emin prec) (add22 emin prec) (0, 0) W xs in
  norm2 emin prec s /\
  Rabs (val2 s - sumR (map val2 xs)) <=
    gamma (length xs - 1) (3 * u prec ^ 2 / (1 - 4 * u prec)) * sumabs (map val2 xs).
Proof.
intros emin prec Hp W xs Hv Hn.
assert (Hp1 : (1 <= prec)%Z) by lia.
exact (fold_lanes_sum_gamma _ _ _ _ _ _ (eps_add_2_ge_0 prec Hp) (add_2_2_adds emin prec Hp)
         (add_2_2_zero emin prec Hp1) W xs Hv Hn).
Qed.

(* The two sums with the fast addition: gamma_(n-1)(3 u^2). *)
Theorem sum_fast_2_seq :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall xs : list (R * R), Forall (norm2 emin prec) xs ->
  INR (length xs - 1) * (3 * u prec ^ 2) < 1 ->
  let s := fold_seq (addfast22 emin prec) (0, 0) xs in
  norm2 emin prec s /\
  Rabs (val2 s - sumR (map val2 xs)) <=
    gamma (length xs - 1) (3 * u prec ^ 2) * sumabs (map val2 xs).
Proof.
intros emin prec Hp xs Hv Hn.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
exact (fold_seq_sum_gamma _ _ _ _ _ _ (eps_square_ge_0 3 prec H3) (add_fast_2_2_adds emin prec Hp)
         (add_fast_2_2_zero emin prec Hp1) xs Hv Hn).
Qed.

(* The same in the lane order, for every width W. *)
Theorem sum_fast_2_lanes :
  forall emin prec : Z, (2 <= prec)%Z ->
  forall (W : nat) (xs : list (R * R)), Forall (norm2 emin prec) xs ->
  INR (length xs - 1) * (3 * u prec ^ 2) < 1 ->
  let s := fold_lanes (addfast22 emin prec) (addfast22 emin prec) (0, 0) W xs in
  norm2 emin prec s /\
  Rabs (val2 s - sumR (map val2 xs)) <=
    gamma (length xs - 1) (3 * u prec ^ 2) * sumabs (map val2 xs).
Proof.
intros emin prec Hp W xs Hv Hn.
assert (Hp1 : (1 <= prec)%Z) by lia.
assert (H3 : 0 <= 3) by lra.
exact (fold_lanes_sum_gamma _ _ _ _ _ _ (eps_square_ge_0 3 prec H3)
         (add_fast_2_2_adds emin prec Hp) (add_fast_2_2_zero emin prec Hp1) W xs Hv Hn).
Qed.

(** * Two limbs: the dot product *)

(* A term of the dot product: the product of two normalized pairs by mul_2_2 is
   normalized and within 4 u^2 |x y| + 3/2 eta of the exact product. *)
Theorem mul_2_2_leaf :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall x y : R * R, norm2 emin prec x -> norm2 emin prec y ->
  norm2 emin prec (mul22 emin prec x y) /\
  Rabs (val2 (mul22 emin prec x y) - val2 x * val2 y) <=
    4 * u prec ^ 2 * Rabs (val2 x * val2 y) + 3 / 2 * eta emin.
Proof.
intros emin prec Hp [x0 x1] [y0 y1] Nx Ny.
unfold mul22, norm2, val2 in *. cbn [fst snd] in *.
generalize (mul_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (mul_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. cbn [fst snd].
intros H. exact H.
Qed.

(* The step of the dot product of two limbs: s <- s + x y, with mul_2_2 and add_2_2. An
   element is a pair (x, y) of 2-limb numbers. *)
Definition dot_step_2 (emin prec : Z) (s : R * R) (xy : (R * R) * (R * R)) : R * R :=
  add22 emin prec s (mul22 emin prec (fst xy) (snd xy)).

(* The products are valid operands of the sum and approximate the exact products. *)
Lemma dot_2_leaves :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall xys : list ((R * R) * (R * R)),
  Forall (fun xy => norm2 emin prec (fst xy) /\ norm2 emin prec (snd xy)) xys ->
  Forall (norm2 emin prec) (map (fun xy => mul22 emin prec (fst xy) (snd xy)) xys) /\
  Forall2 (fun p r => Rabs (val2 p - r) <= 4 * u prec ^ 2 * Rabs r + 3 / 2 * eta emin)
    (map (fun xy => mul22 emin prec (fst xy) (snd xy)) xys)
    (map (fun xy => val2 (fst xy) * val2 (snd xy)) xys).
Proof.
intros emin prec Hp xys Hv. split.
- apply Forall_map. revert Hv. apply Forall_impl. intros xy [Nx Ny].
  exact (proj1 (mul_2_2_leaf emin prec Hp (fst xy) (snd xy) Nx Ny)).
- apply Forall2_map_both. revert Hv. apply Forall_impl. intros xy [Nx Ny].
  exact (proj2 (mul_2_2_leaf emin prec Hp (fst xy) (snd xy) Nx Ny)).
Qed.

(* The dot product of n pairs of normalized pairs, in the sequential order. With
   e = 3 u^2 / (1 - 4 u): the result is normalized and within
       ((1 + 4 u^2) (1 + e)^(n-1) - 1) sum |x_i y_i| + (1 + e)^(n-1) n (3/2 eta)
   of the exact dot product. *)
Theorem dot_2_seq :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall xys : list ((R * R) * (R * R)),
  Forall (fun xy => norm2 emin prec (fst xy) /\ norm2 emin prec (snd xy)) xys ->
  let s := fold_seq (dot_step_2 emin prec) (0, 0) xys in
  let ts := map (fun xy => val2 (fst xy) * val2 (snd xy)) xys in
  let e := 3 * u prec ^ 2 / (1 - 4 * u prec) in
  norm2 emin prec s /\
  Rabs (val2 s - sumR ts) <=
    ((1 + 4 * u prec ^ 2) * (1 + e) ^ (length xys - 1) - 1) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (3 / 2 * eta emin)).
Proof.
intros emin prec Hp xys Hv. cbv zeta.
destruct (dot_2_leaves emin prec Hp xys Hv) as [Hl Ha].
assert (Hp3 : (3 <= prec)%Z) by lia. assert (Hp1 : (1 <= prec)%Z) by lia.
generalize (fold_seq_sum_approx _ _ _ _ _ _ (4 * u prec ^ 2) (3 / 2 * eta emin)
              (eps_add_2_ge_0 prec Hp3) (add_2_2_adds emin prec Hp3)
              (add_2_2_zero emin prec Hp1) _ _ Hl Ha).
cbv zeta. rewrite !length_map.
rewrite <- (fold_seq_map _ _ _ (add22 emin prec)
              (fun xy : (R * R) * (R * R) => mul22 emin prec (fst xy) (snd xy)) (0, 0) xys).
intros H. exact H.
Qed.

(* The same in the lane order, for every width W; the lanes are combined by add_2_2. *)
Theorem dot_2_lanes :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall (W : nat) (xys : list ((R * R) * (R * R))),
  Forall (fun xy => norm2 emin prec (fst xy) /\ norm2 emin prec (snd xy)) xys ->
  let s := fold_lanes (dot_step_2 emin prec) (add22 emin prec) (0, 0) W xys in
  let ts := map (fun xy => val2 (fst xy) * val2 (snd xy)) xys in
  let e := 3 * u prec ^ 2 / (1 - 4 * u prec) in
  norm2 emin prec s /\
  Rabs (val2 s - sumR ts) <=
    ((1 + 4 * u prec ^ 2) * (1 + e) ^ (length xys - 1) - 1) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (3 / 2 * eta emin)).
Proof.
intros emin prec Hp W xys Hv. cbv zeta.
destruct (dot_2_leaves emin prec Hp xys Hv) as [Hl Ha].
assert (Hp3 : (3 <= prec)%Z) by lia. assert (Hp1 : (1 <= prec)%Z) by lia.
generalize (fold_lanes_sum_approx _ _ _ _ _ _ (4 * u prec ^ 2) (3 / 2 * eta emin)
              (eps_add_2_ge_0 prec Hp3) (add_2_2_adds emin prec Hp3)
              (add_2_2_zero emin prec Hp1) W _ _ Hl Ha).
cbv zeta. rewrite !length_map.
rewrite <- (fold_lanes_map _ _ _ (add22 emin prec) (add22 emin prec)
              (fun xy : (R * R) * (R * R) => mul22 emin prec (fst xy) (snd xy)) (0, 0) W xys).
intros H. exact H.
Qed.

(* The first factor in closed form: at most gamma_n(4 u^2), because from 4 bits of
   precision the relative error of the addition is at most that of the product. *)
Lemma dot_2_gamma_form :
  forall (prec : Z) (n : nat) (a c x : R), (4 <= prec)%Z ->
  INR n * (4 * u prec ^ 2) < 1 -> 0 <= a -> (n = 0%nat -> a = 0) ->
  x <= ((1 + 4 * u prec ^ 2) * (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (n - 1) - 1) * a + c ->
  x <= gamma n (4 * u prec ^ 2) * a + c.
Proof.
intros prec n a c x Hp Hn Ha H0 Hx.
assert (Hp3 : (3 <= prec)%Z) by lia.
assert (M : Rmax (4 * u prec ^ 2) (3 * u prec ^ 2 / (1 - 4 * u prec)) = 4 * u prec ^ 2).
{ apply Rmax_left. now apply eps_add_2_le_mul_2. }
rewrite <- M. apply approx_gamma_bound; try assumption.
- apply eps_square_ge_0. lra.
- now apply eps_add_2_ge_0.
- rewrite M. exact Hn.
Qed.

(* The dot product of two limbs in closed form, in the sequential order: within
   gamma_n(4 u^2) sum |x_i y_i| + (1 + e)^(n-1) n (3/2 eta), when 4 n u^2 < 1. *)
Theorem dot_2_seq_gamma :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall xys : list ((R * R) * (R * R)),
  Forall (fun xy => norm2 emin prec (fst xy) /\ norm2 emin prec (snd xy)) xys ->
  INR (length xys) * (4 * u prec ^ 2) < 1 ->
  let s := fold_seq (dot_step_2 emin prec) (0, 0) xys in
  let ts := map (fun xy => val2 (fst xy) * val2 (snd xy)) xys in
  let e := 3 * u prec ^ 2 / (1 - 4 * u prec) in
  norm2 emin prec s /\
  Rabs (val2 s - sumR ts) <=
    gamma (length xys) (4 * u prec ^ 2) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (3 / 2 * eta emin)).
Proof.
intros emin prec Hp xys Hv Hn. cbv zeta.
destruct (dot_2_seq emin prec Hp xys Hv) as [Ns Es].
split. exact Ns.
apply (dot_2_gamma_form prec (length xys) _ _ _ Hp Hn (sumabs_ge_0 _)); [|exact Es].
intros H0. destruct xys; [reflexivity | discriminate].
Qed.

(* The same in the lane order, for every width W. *)
Theorem dot_2_lanes_gamma :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall (W : nat) (xys : list ((R * R) * (R * R))),
  Forall (fun xy => norm2 emin prec (fst xy) /\ norm2 emin prec (snd xy)) xys ->
  INR (length xys) * (4 * u prec ^ 2) < 1 ->
  let s := fold_lanes (dot_step_2 emin prec) (add22 emin prec) (0, 0) W xys in
  let ts := map (fun xy => val2 (fst xy) * val2 (snd xy)) xys in
  let e := 3 * u prec ^ 2 / (1 - 4 * u prec) in
  norm2 emin prec s /\
  Rabs (val2 s - sumR ts) <=
    gamma (length xys) (4 * u prec ^ 2) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (3 / 2 * eta emin)).
Proof.
intros emin prec Hp W xys Hv Hn. cbv zeta.
destruct (dot_2_lanes emin prec Hp W xys Hv) as [Ns Es].
split. exact Ns.
apply (dot_2_gamma_form prec (length xys) _ _ _ Hp Hn (sumabs_ge_0 _)); [|exact Es].
intros H0. destruct xys; [reflexivity | discriminate].
Qed.

(** * One limb: the fused step *)

(* One rounding to nearest of any real number: the relative error u / (1 + u) and the
   absolute error eta / 2 (Flocq's relative_error_N_FLT'_ex). *)
Lemma RN_error :
  forall emin prec : Z, (1 <= prec)%Z -> forall z : R,
  Rabs (RN emin prec z - z) <= u prec / (1 + u prec) * Rabs z + eta emin / 2.
Proof.
intros emin prec Hp z.
assert (Hp0 : (0 < prec)%Z) by lia.
destruct (relative_error_N_FLT'_ex radix2 emin prec Hp0 tie_even z)
  as [e [et [He [Ht [_ Hr]]]]].
rewrite u_ro_eq in He. unfold RN. rewrite Hr.
replace (z * (1 + e) + et - z) with (z * e + et) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat.
- rewrite Rabs_mult, (Rmult_comm (Rabs z)).
  apply Rmult_le_compat_r. apply Rabs_pos. exact He.
- unfold eta. lra.
Qed.

(* The rounded sum of two real numbers that need not be numbers of the format: an
   addition of relative error u / (1 + u) with the absolute error eta / 2. This is
   add_1_1 outside the domain of its statement, and the fused step RN (x y + s) of the
   one-limb dot product is add_1_1 s (x y). *)
Theorem fused_add_tau :
  forall emin prec : Z, (1 <= prec)%Z ->
  adds_tau (fun x : R => x) (fun _ : R => True) (add_1_1 emin prec tie_even)
    (u prec / (1 + u prec)) (eta emin / 2).
Proof.
intros emin prec Hp a b _ _. cbv beta. split. exact I.
generalize (RN_error emin prec Hp (a + b)). unfold add_1_1, RN. cbv zeta.
generalize (Rabs_triang a b). intros T E.
assert (K : u prec / (1 + u prec) * Rabs (a + b) <= u prec / (1 + u prec) * (Rabs a + Rabs b)).
{ apply Rmult_le_compat_l. apply eps_1_ge_0. exact T. }
lra.
Qed.

(* What an operand costs in absolute error: nothing if it is a number of the format,
   eta / 2 otherwise. *)
Definition weight_1 (emin prec : Z) (x : R) : R :=
  if Req_dec_T (RN emin prec x) x then 0 else eta emin / 2.

Lemma weight_1_bounds :
  forall (emin prec : Z) (x : R), 0 <= weight_1 emin prec x <= eta emin / 2.
Proof.
intros emin prec x. unfold weight_1. generalize (eta_pos emin). intros H.
destruct (Req_dec_T (RN emin prec x) x); split; lra.
Qed.

Lemma weight_1_fmt :
  forall (emin prec : Z) (x : R), (1 <= prec)%Z -> fmt emin prec x -> weight_1 emin prec x = 0.
Proof.
intros emin prec x Hp Fx.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold weight_1. destruct (Req_dec_T (RN emin prec x) x) as [_|H]. reflexivity.
exfalso. apply H. unfold RN. apply round_generic; auto with typeclass_instances; exact Fx.
Qed.

(* The same addition with the absolute error charged to the operands: the result is a
   number of the format, and two operands of the format are added with no absolute
   error, which is the statement of add_1_1. *)
Theorem fused_add_weighted :
  forall emin prec : Z, (1 <= prec)%Z ->
  adds_weighted (fun x : R => x) (fun _ : R => True) (add_1_1 emin prec tie_even)
    (u prec / (1 + u prec)) (weight_1 emin prec).
Proof.
intros emin prec Hp.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split.
- intros a _. exact (proj1 (weight_1_bounds emin prec a)).
- intros a b _ _. cbv beta. split. exact I. split.
  + apply weight_1_fmt. exact Hp. unfold add_1_1, fmt. cbv zeta.
    apply generic_format_round; auto with typeclass_instances.
  + destruct (fused_add_tau emin prec Hp a b I I) as [_ E]. cbv beta in E.
    generalize (weight_1_bounds emin prec a) (weight_1_bounds emin prec b).
    generalize (eta_pos emin). intros He Wa Wb.
    unfold weight_1 in *.
    destruct (Req_dec_T (RN emin prec a) a) as [Ha|Ha];
      destruct (Req_dec_T (RN emin prec b) b) as [Hb|Hb]; try lra.
    assert (Fa : fmt emin prec a).
    { rewrite <- Ha. unfold RN, fmt. apply generic_format_round; auto with typeclass_instances. }
    assert (Fb : fmt emin prec b).
    { rewrite <- Hb. unfold RN, fmt. apply generic_format_round; auto with typeclass_instances. }
    destruct (add_1_1_adds emin prec Hp a b Fa Fb) as [_ E']. cbv beta in E'. lra.
Qed.

(* The step of the one-limb dot product: one fused operation. An element is a pair
   (x, y) of real numbers. *)
Definition dot_step_1 (emin prec : Z) (s : R) (xy : R * R) : R :=
  RN emin prec (fst xy * snd xy + s).

Lemma dot_step_1_add :
  forall (emin prec : Z) (s : R) (xy : R * R),
  dot_step_1 emin prec s xy = add_1_1 emin prec tie_even s (fst xy * snd xy).
Proof.
intros emin prec s xy. unfold dot_step_1, add_1_1, RN. cbv zeta. now rewrite Rplus_comm.
Qed.

(* From the sum of the costs of the terms to n times eta / 2. *)
Lemma dot_1_weights :
  forall (emin prec : Z) (ts : list R) (n : nat) (v a p : R), length ts = n -> 0 <= p ->
  Rabs v <= a + p * sumR (map (weight_1 emin prec) ts) ->
  Rabs v <= a + p * (INR n * (eta emin / 2)).
Proof.
intros emin prec ts n v a p Hn Hp Hv.
assert (W : sumR (map (weight_1 emin prec) ts) <= INR n * (eta emin / 2)).
{ rewrite <- Hn, <- (length_map (weight_1 emin prec) ts). apply sumR_le_const.
  apply Forall_map. apply Forall_forall. intros x _.
  exact (proj2 (weight_1_bounds emin prec x)). }
assert (K : p * sumR (map (weight_1 emin prec) ts) <= p * (INR n * (eta emin / 2))).
{ apply Rmult_le_compat_l; assumption. }
lra.
Qed.

(* The fused dot product of n pairs of real numbers, in the sequential order. With
   e = u / (1 + u): the result is a number of the format and within
       ((1 + e)^n - 1) sum |x_i y_i| + (1 + e)^(n-1) n (eta / 2)
   of the exact dot product. Nothing is assumed of the operands. *)
Theorem dot_1_seq :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall xys : list (R * R),
  let s := fold_seq (dot_step_1 emin prec) 0 xys in
  let ts := map (fun xy => fst xy * snd xy) xys in
  let e := u prec / (1 + u prec) in
  fmt emin prec s /\
  Rabs (s - sumR ts) <=
    ((1 + e) ^ length xys - 1) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (eta emin / 2)).
Proof.
intros emin prec Hp xys. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split.
- apply fold_seq_inv.
  + apply generic_format_0.
  + intros s e _. unfold dot_step_1, RN, fmt.
    apply generic_format_round; auto with typeclass_instances.
- set (leaf := fun xy : R * R => fst xy * snd xy).
  assert (E : fold_seq (dot_step_1 emin prec) 0 xys =
              fold_seq (add_1_1 emin prec tie_even) 0 (map leaf xys)).
  { rewrite <- fold_seq_map. apply fold_seq_ext. intros s xy.
    exact (dot_step_1_add emin prec s xy). }
  assert (Hall : Forall (fun _ : R => True) (map leaf xys)).
  { apply Forall_forall. intros x _. exact I. }
  destruct (fold_seq_weighted _ _ _ _ _ _ _ (eps_1_ge_0 prec)
              (fused_add_weighted emin prec Hp) I eq_refl
              (weight_1_fmt emin prec 0 Hp (generic_format_0 radix2 (FLT_exp emin prec)))
              _ Hall) as [_ B].
  cbv beta in B. rewrite map_id, length_map in B. rewrite E.
  apply (dot_1_weights emin prec (map leaf xys) (length xys) _ _ _ (length_map leaf xys)).
  + apply pow_le. generalize (eps_1_ge_0 prec). lra.
  + exact B.
Qed.

(* The same in the lane order, for every width W; the lanes are combined by add_1_1. *)
Theorem dot_1_lanes :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall (W : nat) (xys : list (R * R)),
  let s := fold_lanes (dot_step_1 emin prec) (add_1_1 emin prec tie_even) 0 W xys in
  let ts := map (fun xy => fst xy * snd xy) xys in
  let e := u prec / (1 + u prec) in
  fmt emin prec s /\
  Rabs (s - sumR ts) <=
    ((1 + e) ^ length xys - 1) * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (eta emin / 2)).
Proof.
intros emin prec Hp W xys. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split.
- apply fold_lanes_inv.
  + apply generic_format_0.
  + intros s e _. unfold dot_step_1, RN, fmt.
    apply generic_format_round; auto with typeclass_instances.
  + intros a b _ _. unfold add_1_1, fmt. cbv zeta.
    apply generic_format_round; auto with typeclass_instances.
- set (leaf := fun xy : R * R => fst xy * snd xy).
  assert (E : fold_lanes (dot_step_1 emin prec) (add_1_1 emin prec tie_even) 0 W xys =
              fold_lanes (add_1_1 emin prec tie_even) (add_1_1 emin prec tie_even) 0 W
                (map leaf xys)).
  { rewrite <- fold_lanes_map. apply fold_lanes_ext.
    - intros s xy. exact (dot_step_1_add emin prec s xy).
    - reflexivity. }
  assert (Hall : Forall (fun _ : R => True) (map leaf xys)).
  { apply Forall_forall. intros x _. exact I. }
  destruct (fold_lanes_weighted _ _ _ _ _ _ _ (eps_1_ge_0 prec)
              (fused_add_weighted emin prec Hp) I eq_refl
              (weight_1_fmt emin prec 0 Hp (generic_format_0 radix2 (FLT_exp emin prec)))
              (proj1 (proj2 (proj2 (add_1_1_zero emin prec Hp)))) W _ Hall) as [_ B].
  cbv beta in B. rewrite map_id, length_map in B. rewrite E.
  apply (dot_1_weights emin prec (map leaf xys) (length xys) _ _ _ (length_map leaf xys)).
  + apply pow_le. generalize (eps_1_ge_0 prec). lra.
  + exact B.
Qed.

(* The fused dot product in closed form, in the sequential order: within
   gamma_n(e) sum |x_i y_i| + (1 + e)^(n-1) n (eta / 2), e = u / (1 + u), when n e < 1. *)
Theorem dot_1_seq_gamma :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall xys : list (R * R),
  INR (length xys) * (u prec / (1 + u prec)) < 1 ->
  let s := fold_seq (dot_step_1 emin prec) 0 xys in
  let ts := map (fun xy => fst xy * snd xy) xys in
  let e := u prec / (1 + u prec) in
  fmt emin prec s /\
  Rabs (s - sumR ts) <=
    gamma (length xys) e * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (eta emin / 2)).
Proof.
intros emin prec Hp xys Hn. cbv zeta.
destruct (dot_1_seq emin prec Hp xys) as [Fs Es].
split. exact Fs.
exact (gamma_bound _ _ _ _ _ _ (eps_1_ge_0 prec) (le_n _) Hn (sumabs_ge_0 _) Es).
Qed.

(* The same in the lane order, for every width W. *)
Theorem dot_1_lanes_gamma :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall (W : nat) (xys : list (R * R)),
  INR (length xys) * (u prec / (1 + u prec)) < 1 ->
  let s := fold_lanes (dot_step_1 emin prec) (add_1_1 emin prec tie_even) 0 W xys in
  let ts := map (fun xy => fst xy * snd xy) xys in
  let e := u prec / (1 + u prec) in
  fmt emin prec s /\
  Rabs (s - sumR ts) <=
    gamma (length xys) e * sumabs ts +
    (1 + e) ^ (length xys - 1) * (INR (length xys) * (eta emin / 2)).
Proof.
intros emin prec Hp W xys Hn. cbv zeta.
destruct (dot_1_lanes emin prec Hp W xys) as [Fs Es].
split. exact Fs.
exact (gamma_bound _ _ _ _ _ _ (eps_1_ge_0 prec) (le_n _) Hn (sumabs_ge_0 _) Es).
Qed.
