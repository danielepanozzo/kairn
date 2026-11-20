(* The exported bounds of the folds: the generated statements of bound_sum_1,
   bound_sum_2, bound_dot_1 and bound_dot_2 (proofs/gen/Statements.v).

   A program cannot write gamma_m(eps) = m eps / (1 - m eps) exactly in floating point,
   so the library computes a number of the format that is certainly at least it
   (docs/developer/design/milestone2.md, "The bound as a function of n"). The four
   kernels are one listing with different constants. With eps the relative error and tau
   the absolute error of the kernel named, u = 2^-prec, eta = 2^emin, RN rounding to
   nearest and up( ) rounding a constant up to the format:

       a  = RN (m * up ((1 + u) (eps + eta / 2)))
       aa = RN (m * up ((1 + u)^2 (eps + eta)))
       d  = RN (a * up (2))
       w  = RN (d + up (1 + 2 u))
       g  = RN (aa * w)
       ok = a <= up (1 / 4)
   and, for a dot product,
       tm = RN (m * up ((1 + u)^2 (tau + eta) + eta / (2 u)))
       wg = RN (g + up (1 + 2 u))
       t  = RN (tm * wg)
       ok = a <= up (1 / 4) and g <= up (1).

   What is proved, for m a number of the format that is 0 or at least 1, in a format that
   contains 1/2 (eta <= 1/2):
   - g and t are numbers of the format, and 0 <= g;
   - if ok, then m eps <= 1/2 and g >= m eps / (1 - m eps);
   - if ok, for a dot product, t >= m tau (1 + g).
   The generated statements have all of it but 0 <= g, which K_facts adds. What a program
   does with g needs m eps <= 1/2: below m eps = 1 the quotient m eps / (1 - m eps) is
   the closed form of (1 + eps)^m - 1, above it is a negative number that bounds nothing.

   The argument, with x = m eps.
   1. One rounding to nearest of a nonnegative y loses at most a factor 1 + u and
      eta / 2: y <= (1 + u) (RN y + eta / 2) (rnd_lower, Ball2.v). For m >= 1 the first
      constant gives a >= x + (m - 1) eta / 2 >= x (count_prod_1), and the second gives
      aa >= (1 + u) (x + eta / 2) (count_prod_2). For m = 0 both are 0.
   2. up (1/4) <= 1/2 because 1/2 is a number of the format. So ok gives
      x <= a <= 1/2.
   3. d = 2 a exactly: 2 is a number of the format and the format has no largest
      number. (The listing multiplies by 2 and does not add a to itself, because a
      compiler rewrites a + a as a product and may then fuse it.)
   4. The sum of two numbers of the format is a multiple of eta, so its rounding has no
      absolute error: a + b <= (1 + u) RN (a + b) for a + b >= 0 (rnd_sum_lower, from
      add_1_1_correct). Hence (1 + u) w >= 2 a + 1 + 2 u >= (1 + u) (1 + 2 a) for
      a <= 1/2, that is w >= 1 + 2 a.
   5. g >= aa w / (1 + u) - eta / 2 >= (x + eta / 2) (1 + 2 a) - eta / 2 >= x (1 + 2 x),
      and x (1 + 2 x) >= x / (1 - x) for 0 <= x <= 1/2 (div_one_minus_le, Summation.v).
   6. For the dot products: tm >= (1 + u) (m tau + eta / 2) as in step 1, the term
      eta / (2 u) of its constant only making it larger; wg >= 1 + g as in step 4, for
      g <= 1, and up (1) = 1; so t >= (m tau + eta / 2) (1 + g) - eta / 2 >= m tau (1 + g).

   When ok is true is not part of any statement: it is a fact about each format. *)
From Stdlib Require Import Reals ZArith Bool Lia Lra.
From Flocq Require Import Core Mult_error.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format OneLimb Ball2 Summation.
Open Scope R_scope.

Lemma Rle_bool_inv : forall x y : R, Rle_bool x y = true -> x <= y.
Proof. intros x y. case (Rle_bool_spec x y); intros H E. exact H. discriminate E. Qed.

(** * Rounding, and the constants *)

Section Bound.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.

Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation RUp := (round radix2 fexp Zceil).
Notation uu := (u prec).
Notation ee := (eta emin).

Let u0 : 0 < uu.
Proof. apply bpow_gt_0. Qed.
Let e0 : 0 < ee.
Proof. apply bpow_gt_0. Qed.

(* A format that contains 1/2 has emin <= -1, and contains 1 and 2. *)
Lemma half_emin : ee <= / 2 -> (emin <= -1)%Z.
Proof. intros H. apply (le_bpow radix2). rewrite pow2_m1. exact H. Qed.

Lemma fmt_half : ee <= / 2 -> format (/ 2).
Proof.
intros H. rewrite <- pow2_m1.
apply generic_format_FLT_bpow; [exact prec_gt_0_ | now apply half_emin].
Qed.

Lemma fmt_one : ee <= / 2 -> format 1.
Proof.
intros H. change 1 with (pow2 0).
apply generic_format_FLT_bpow; [exact prec_gt_0_ | generalize (half_emin H); lia].
Qed.

Lemma fmt_two : ee <= / 2 -> format 2.
Proof.
intros H. rewrite <- pow2_1.
apply generic_format_FLT_bpow; [exact prec_gt_0_ | generalize (half_emin H); lia].
Qed.

(* Rounding a constant up. *)
Lemma RUp_ge : forall t : R, t <= RUp t.
Proof. intros t. destruct (round_UP_pt radix2 fexp t) as [_ [H _]]. exact H. Qed.

Lemma RUp_format : forall t : R, format (RUp t).
Proof. intros t. apply generic_format_round; auto with typeclass_instances. Qed.

Lemma RUp_id : forall t : R, format t -> RUp t = t.
Proof. intros t Ft. apply round_generic; auto with typeclass_instances. Qed.

Lemma RUp_quarter : ee <= / 2 -> RUp (1 / 4) <= / 2.
Proof.
intros H. apply round_le_generic; [auto with typeclass_instances .. | now apply fmt_half | lra].
Qed.

(* Rounding to nearest. *)
Lemma rnd_format : forall x : R, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

Lemma rnd_prod_0 : forall C : R, rnd (0 * C + 0) = 0.
Proof.
intros C. replace (0 * C + 0) with 0 by ring. apply round_0; auto with typeclass_instances.
Qed.

Lemma rnd_prod_ge_0 : forall x y : R, 0 <= x -> 0 <= y -> 0 <= rnd (x * y + 0).
Proof.
intros x y Hx Hy. apply (rnd_ge_0 emin prec). generalize (Rmult_le_pos x y Hx Hy). lra.
Qed.

(* The sum of two numbers of the format: no absolute error. *)
Lemma rnd_sum_lower :
  forall a b : R, format a -> format b -> 0 <= a + b -> a + b <= (1 + uu) * rnd (a + b).
Proof.
intros a b Fa Fb Hs.
assert (Hp1 : (1 <= prec)%Z) by (generalize prec_gt_0_; unfold Prec_gt_0; lia).
generalize (add_1_1_correct emin prec Hp1 a b Fa Fb). unfold add_1_1. cbv zeta.
intros [_ [_ E]].
rewrite (Rabs_pos_eq (a + b) Hs) in E.
apply Rabs_le_inv in E. destruct E as [E _].
set (s := a + b) in *. set (r := rnd s) in *.
set (d := 1 / (1 + uu) * uu ^ 1) in *.
assert (K : (1 + uu) * (s - d * s) <= (1 + uu) * r) by (apply Rmult_le_compat_l; lra).
replace ((1 + uu) * (s - d * s)) with s in K by (unfold d; field; lra).
exact K.
Qed.

(* A product by a count m >= 1 whose constant holds one factor 1 + u and eta / 2: the
   rounded product is at least m e. *)
Lemma count_prod_1 :
  forall e C m : R, 0 <= e -> (1 + uu) * (e + ee / 2) <= C -> 1 <= m ->
  m * e <= rnd (m * C + 0).
Proof.
intros e C m He HC Hm.
assert (HC0 : 0 <= C).
{ apply Rle_trans with (2 := HC). apply Rmult_le_pos; lra. }
assert (Q : 0 <= m * C) by (apply Rmult_le_pos; lra).
assert (P : 0 <= m * C + 0) by lra.
assert (L : m * C + 0 <= (1 + uu) * (rnd (m * C + 0) + ee / 2))
  by exact (rnd_lower emin prec (m * C + 0) P).
assert (K : m * ((1 + uu) * (e + ee / 2)) <= m * C) by (apply Rmult_le_compat_l; lra).
assert (K2 : 1 * ee <= m * ee) by (apply Rmult_le_compat_r; lra).
assert (K3 : uu * (1 * ee) <= uu * (m * ee)) by (apply Rmult_le_compat_l; lra).
apply Rmult_le_reg_l with (1 + uu). lra. lra.
Qed.

(* The same with two factors and eta: the rounded product is at least
   (1 + u) (m e + eta / 2), which is what the next rounding costs. *)
Lemma count_prod_2 :
  forall e C m : R, 0 <= e -> (1 + uu) ^ 2 * (e + ee) <= C -> 1 <= m ->
  (1 + uu) * (m * e + ee / 2) <= rnd (m * C + 0).
Proof.
intros e C m He HC Hm.
assert (HC0 : 0 <= C).
{ apply Rle_trans with (2 := HC). apply Rmult_le_pos. apply pow_le; lra. lra. }
assert (Q : 0 <= m * C) by (apply Rmult_le_pos; lra).
assert (P : 0 <= m * C + 0) by lra.
assert (L : m * C + 0 <= (1 + uu) * (rnd (m * C + 0) + ee / 2))
  by exact (rnd_lower emin prec (m * C + 0) P).
assert (K : m * ((1 + uu) ^ 2 * (e + ee)) <= m * C) by (apply Rmult_le_compat_l; lra).
assert (K2 : 1 * ee <= m * ee) by (apply Rmult_le_compat_r; lra).
assert (K3 : uu * (1 * ee) <= uu * (m * ee)) by (apply Rmult_le_compat_l; lra).
assert (K4 : uu * (uu * (1 * ee)) <= uu * (uu * (m * ee))) by (apply Rmult_le_compat_l; lra).
assert (K5 : 0 <= uu * ee) by (apply Rmult_le_pos; lra).
assert (K6 : 0 <= uu * (uu * ee)) by (apply Rmult_le_pos; lra).
apply Rmult_le_reg_l with (1 + uu). lra. lra.
Qed.

(** * The five lines that compute g *)

Lemma bound_core :
  forall eps C0 C1 c2 c3 c5 m : R,
  0 <= eps ->
  (1 + uu) * (eps + ee / 2) <= C0 ->
  (1 + uu) ^ 2 * (eps + ee) <= C1 ->
  c2 = 2 -> format c3 -> 1 + 2 * uu <= c3 -> c5 <= / 2 ->
  format m -> (m = 0 \/ 1 <= m) ->
  let a := rnd (m * C0 + 0) in
  let aa := rnd (m * C1 + 0) in
  let d := rnd (a * c2 + 0) in
  let w := rnd (d + c3) in
  let g := rnd (aa * w + 0) in
  0 <= g /\ (a <= c5 -> m * eps <= / 2 /\ m * eps / (1 - m * eps) <= g).
Proof.
intros eps C0 C1 c2 c3 c5 m He HC0 HC1 Hc2 Fc3 Hc3 Hc5 Fm Hm.
subst c2. intros a aa d w g.
assert (HC0p : 0 <= C0).
{ apply Rle_trans with (2 := HC0). apply Rmult_le_pos; lra. }
assert (HC1p : 0 <= C1).
{ apply Rle_trans with (2 := HC1). apply Rmult_le_pos. apply pow_le; lra. lra. }
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Ha0 : 0 <= a) by (unfold a; apply rnd_prod_ge_0; assumption).
assert (Haa0 : 0 <= aa) by (unfold aa; apply rnd_prod_ge_0; assumption).
assert (Fa : format a) by (unfold a; apply rnd_format).
assert (Ed : d = a * 2).
{ unfold d. rewrite Rplus_0_r. apply round_generic; auto with typeclass_instances.
  rewrite <- pow2_1. apply mult_bpow_pos_exact_FLT; auto with typeclass_instances; lia. }
assert (Fd : format d) by (unfold d; apply rnd_format).
assert (Hd0 : 0 <= d) by (rewrite Ed; lra).
assert (Hw0 : 0 <= w) by (unfold w; apply (rnd_ge_0 emin prec); lra).
assert (Hg0 : 0 <= g) by (unfold g; apply rnd_prod_ge_0; assumption).
split. exact Hg0.
intros Hle.
destruct Hm as [Hm|Hm].
- (* no term: a = aa = g = 0 *)
  assert (Eg : g = 0).
  { unfold g, aa. rewrite Hm. rewrite (rnd_prod_0 C1). apply rnd_prod_0. }
  rewrite Eg, Hm, Rmult_0_l. split. lra.
  unfold Rdiv. rewrite Rmult_0_l. lra.
- (* m >= 1 *)
  assert (Hx0 : 0 <= m * eps) by (apply Rmult_le_pos; lra).
  assert (Hxa : m * eps <= a) by (unfold a; apply count_prod_1; assumption).
  assert (Hxaa : (1 + uu) * (m * eps + ee / 2) <= aa)
    by (unfold aa; apply count_prod_2; assumption).
  assert (Hah : a <= / 2) by lra.
  assert (Hw : 1 + 2 * a <= w).
  { assert (S : d + c3 <= (1 + uu) * w)
      by (unfold w; apply rnd_sum_lower; try assumption; lra).
    assert (N : a * uu <= / 2 * uu) by (apply Rmult_le_compat_r; lra).
    apply Rmult_le_reg_l with (1 + uu). lra. rewrite Ed in S. lra. }
  assert (L : aa * w + 0 <= (1 + uu) * (g + ee / 2)).
  { assert (P : 0 <= aa * w + 0) by (generalize (Rmult_le_pos aa w Haa0 Hw0); lra).
    exact (rnd_lower emin prec (aa * w + 0) P). }
  assert (K : (1 + uu) * (m * eps + ee / 2) * w <= aa * w)
    by (apply Rmult_le_compat_r; assumption).
  assert (Hg : (m * eps + ee / 2) * w <= g + ee / 2).
  { apply Rmult_le_reg_l with (1 + uu). lra. lra. }
  assert (K1 : (m * eps + ee / 2) * (1 + 2 * a) <= (m * eps + ee / 2) * w)
    by (apply Rmult_le_compat_l; lra).
  assert (K2 : m * eps * (1 + 2 * (m * eps)) <= m * eps * (1 + 2 * a))
    by (apply Rmult_le_compat_l; lra).
  assert (K3 : 0 <= ee * a) by (apply Rmult_le_pos; lra).
  assert (Hg2 : m * eps * (1 + 2 * (m * eps)) <= g) by lra.
  split. lra.
  apply Rle_trans with (2 := Hg2). apply div_one_minus_le. split; lra.
Qed.

(** * The three lines that compute t *)

Lemma bound_abs :
  forall tau C4 c3 c6 m g : R, 0 <= tau ->
  (1 + uu) ^ 2 * (tau + ee) <= C4 -> format c3 -> 1 + 2 * uu <= c3 -> c6 <= 1 ->
  (m = 0 \/ 1 <= m) -> format g -> 0 <= g ->
  let tm := rnd (m * C4 + 0) in
  let wg := rnd (g + c3) in
  let t := rnd (tm * wg + 0) in
  g <= c6 -> m * tau * (1 + g) <= t.
Proof.
intros tau C4 c3 c6 m g Ht HC4 Fc3 Hc3 Hc6 Hm Fg Hg0 tm wg t Hg1.
assert (HC4p : 0 <= C4).
{ apply Rle_trans with (2 := HC4). apply Rmult_le_pos. apply pow_le; lra. lra. }
assert (Hm0 : 0 <= m) by (destruct Hm; lra).
assert (Htm0 : 0 <= tm) by (unfold tm; apply rnd_prod_ge_0; assumption).
assert (Hwg0 : 0 <= wg) by (unfold wg; apply (rnd_ge_0 emin prec); lra).
destruct Hm as [Hm|Hm].
- assert (Et : t = 0).
  { unfold t, tm. rewrite Hm. rewrite (rnd_prod_0 C4). apply rnd_prod_0. }
  rewrite Et, Hm. lra.
- assert (Htm : (1 + uu) * (m * tau + ee / 2) <= tm)
    by (unfold tm; apply count_prod_2; assumption).
  assert (Hwg : 1 + g <= wg).
  { assert (S : g + c3 <= (1 + uu) * wg)
      by (unfold wg; apply rnd_sum_lower; try assumption; lra).
    assert (N : g * uu <= 1 * uu) by (apply Rmult_le_compat_r; lra).
    apply Rmult_le_reg_l with (1 + uu). lra. lra. }
  assert (L : tm * wg + 0 <= (1 + uu) * (t + ee / 2)).
  { assert (P : 0 <= tm * wg + 0) by (generalize (Rmult_le_pos tm wg Htm0 Hwg0); lra).
    exact (rnd_lower emin prec (tm * wg + 0) P). }
  assert (K : (1 + uu) * (m * tau + ee / 2) * wg <= tm * wg)
    by (apply Rmult_le_compat_r; assumption).
  assert (Hx0 : 0 <= m * tau) by (apply Rmult_le_pos; lra).
  assert (K1 : (m * tau + ee / 2) * (1 + g) <= (m * tau + ee / 2) * wg)
    by (apply Rmult_le_compat_l; lra).
  assert (K2 : (m * tau + ee / 2) * wg <= t + ee / 2).
  { apply Rmult_le_reg_l with (1 + uu). lra. lra. }
  assert (K3 : 0 <= ee * g) by (apply Rmult_le_pos; lra).
  lra.
Qed.

(** * The constants of proofs/gen/Model.v *)

(* The constants that the four kernels share. *)
Lemma c2_eq : ee <= / 2 -> up_bound_dot_1_2 emin prec = 2.
Proof. intros H. unfold up_bound_dot_1_2. apply RUp_id. now apply fmt_two. Qed.

Lemma c3_format : format (up_bound_dot_1_3 emin prec).
Proof. unfold up_bound_dot_1_3. apply RUp_format. Qed.

Lemma c3_ge : 1 + 2 * uu <= up_bound_dot_1_3 emin prec.
Proof. unfold up_bound_dot_1_3, u. apply RUp_ge. Qed.

Lemma c5_le : ee <= / 2 -> up_bound_dot_1_5 emin prec <= / 2.
Proof. intros H. unfold up_bound_dot_1_5. now apply RUp_quarter. Qed.

Lemma c6_le : ee <= / 2 -> up_bound_dot_1_6 emin prec <= 1.
Proof.
intros H. unfold up_bound_dot_1_6. rewrite RUp_id. apply Rle_refl. now apply fmt_one.
Qed.

(* The constants of a and aa, for each of the four relative errors. *)
Lemma C_sum_1_0 :
  (1 + uu) * (1 / (1 + uu) * uu ^ 1 + ee / 2) <= up_bound_sum_1_0 emin prec.
Proof. unfold up_bound_sum_1_0, u, eta. apply RUp_ge. Qed.

Lemma C_sum_1_1 :
  (1 + uu) ^ 2 * (1 / (1 + uu) * uu ^ 1 + ee) <= up_bound_sum_1_1 emin prec.
Proof. unfold up_bound_sum_1_1, u, eta. apply RUp_ge. Qed.

Lemma C_sum_2_0 :
  (1 + uu) * (3 / (1 - 4 * uu) * uu ^ 2 + ee / 2) <= up_bound_sum_2_0 emin prec.
Proof. unfold up_bound_sum_2_0, u, eta. apply RUp_ge. Qed.

Lemma C_sum_2_1 :
  (1 + uu) ^ 2 * (3 / (1 - 4 * uu) * uu ^ 2 + ee) <= up_bound_sum_2_1 emin prec.
Proof. unfold up_bound_sum_2_1, u, eta. apply RUp_ge. Qed.

Lemma C_dot_1_0 :
  (1 + uu) * (1 / (1 + uu) * uu ^ 1 + ee / 2) <= up_bound_dot_1_0 emin prec.
Proof. unfold up_bound_dot_1_0, u, eta. apply RUp_ge. Qed.

Lemma C_dot_1_1 :
  (1 + uu) ^ 2 * (1 / (1 + uu) * uu ^ 1 + ee) <= up_bound_dot_1_1 emin prec.
Proof. unfold up_bound_dot_1_1, u, eta. apply RUp_ge. Qed.

Lemma C_dot_2_0 :
  (1 + uu) * (4 * uu ^ 2 + ee / 2) <= up_bound_dot_2_0 emin prec.
Proof. unfold up_bound_dot_2_0, u, eta. apply RUp_ge. Qed.

Lemma C_dot_2_1 :
  (1 + uu) ^ 2 * (4 * uu ^ 2 + ee) <= up_bound_dot_2_1 emin prec.
Proof. unfold up_bound_dot_2_1, u, eta. apply RUp_ge. Qed.

(* The constants of tm hold the smallest normal number, eta / (2 u), so that they are not
   subnormal; the bound uses of them only that they are at least their first term. *)
Lemma nrm_term_ge_0 : 0 <= ee / (2 * uu).
Proof.
unfold Rdiv. apply Rmult_le_pos. lra. apply Rlt_le, Rinv_0_lt_compat. lra.
Qed.

Lemma C_dot_1_4 :
  (1 + uu) ^ 2 * (1 / 2 * ee + ee) <= up_bound_dot_1_4 emin prec.
Proof.
generalize nrm_term_ge_0. unfold up_bound_dot_1_4, u, eta. intros H.
apply Rle_trans with (2 := RUp_ge _). lra.
Qed.

Lemma C_dot_2_4 :
  (1 + uu) ^ 2 * (3 / 2 * ee + ee) <= up_bound_dot_2_4 emin prec.
Proof.
generalize nrm_term_ge_0. unfold up_bound_dot_2_4, u, eta. intros H.
apply Rle_trans with (2 := RUp_ge _). lra.
Qed.

End Bound.

(** * The bounds of the sums *)

(* bound_sum_1: everything that holds of it. *)
Lemma bound_sum_1_facts :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, ok) := bound_sum_1 emin prec tie_even m in
  fmt emin prec g /\ 0 <= g /\
  (ok = true ->
   m * (1 / (1 + u prec) * u prec ^ 1) <= / 2 /\
   m * (1 / (1 + u prec) * u prec ^ 1) / (1 - m * (1 / (1 + u prec) * u prec ^ 1)) <= g).
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
pose proof (bound_core emin prec (1 / (1 + u prec) * u prec ^ 1)
              (up_bound_sum_1_0 emin prec) (up_bound_sum_1_1 emin prec)
              (up_bound_dot_1_2 emin prec) (up_bound_dot_1_3 emin prec)
              (up_bound_dot_1_5 emin prec) m
              (proj1 (rel_one_limb prec)) (C_sum_1_0 emin prec) (C_sum_1_1 emin prec)
              (c2_eq emin prec Hh) (c3_format emin prec) (c3_ge emin prec)
              (c5_le emin prec Hh) Fm Hm) as H.
cbv zeta in H. destruct H as [Hg0 Hok].
unfold bound_sum_1. cbv beta iota zeta.
split. unfold fmt. apply (rnd_format emin prec).
split. exact Hg0.
intros E. apply Hok. apply Rle_bool_inv. exact E.
Qed.

Theorem bound_sum_1_correct : bound_sum_1_spec.
Proof.
intros emin prec Hp m Fm Hm Hh.
generalize (bound_sum_1_facts emin prec Hp m Fm Hm Hh).
destruct (bound_sum_1 emin prec tie_even m) as [g ok].
intros [Fg [_ H]].
split. exact Fg.
split; intros E; destruct (H E) as [H1 H2].
- apply Rle_trans with (1 := H1). lra.
- exact H2.
Qed.

(* bound_sum_2. *)
Lemma bound_sum_2_facts :
  forall emin prec : Z, (3 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, ok) := bound_sum_2 emin prec tie_even m in
  fmt emin prec g /\ 0 <= g /\
  (ok = true ->
   m * (3 / (1 - 4 * u prec) * u prec ^ 2) <= / 2 /\
   m * (3 / (1 - 4 * u prec) * u prec ^ 2) / (1 - m * (3 / (1 - 4 * u prec) * u prec ^ 2)) <= g).
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
pose proof (bound_core emin prec (3 / (1 - 4 * u prec) * u prec ^ 2)
              (up_bound_sum_2_0 emin prec) (up_bound_sum_2_1 emin prec)
              (up_bound_dot_1_2 emin prec) (up_bound_dot_1_3 emin prec)
              (up_bound_dot_1_5 emin prec) m
              (proj1 (rel_add_2_2 prec Hp)) (C_sum_2_0 emin prec) (C_sum_2_1 emin prec)
              (c2_eq emin prec Hh) (c3_format emin prec) (c3_ge emin prec)
              (c5_le emin prec Hh) Fm Hm) as H.
cbv zeta in H. destruct H as [Hg0 Hok].
unfold bound_sum_2. cbv beta iota zeta.
split. unfold fmt. apply (rnd_format emin prec).
split. exact Hg0.
intros E. apply Hok. apply Rle_bool_inv. exact E.
Qed.

Theorem bound_sum_2_correct : bound_sum_2_spec.
Proof.
intros emin prec Hp m Fm Hm Hh.
generalize (bound_sum_2_facts emin prec Hp m Fm Hm Hh).
destruct (bound_sum_2 emin prec tie_even m) as [g ok].
intros [Fg [_ H]].
split. exact Fg.
split; intros E; destruct (H E) as [H1 H2].
- apply Rle_trans with (1 := H1). lra.
- exact H2.
Qed.

(** * The bounds of the dot products *)

(* bound_dot_1: everything that holds of it. m eps <= 1/2 is what makes the bound on g a
   bound of (1 + eps)^m - 1. *)
Lemma bound_dot_1_facts :
  forall emin prec : Z, (1 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, t, ok) := bound_dot_1 emin prec tie_even m in
  fmt emin prec g /\ fmt emin prec t /\ 0 <= g /\
  (ok = true ->
   m * (1 / (1 + u prec) * u prec ^ 1) <= / 2 /\
   m * (1 / (1 + u prec) * u prec ^ 1) / (1 - m * (1 / (1 + u prec) * u prec ^ 1)) <= g /\
   m * (1 / 2 * eta emin) * (1 + g) <= t).
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
assert (Htau : 0 <= 1 / 2 * eta emin).
{ assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. }
pose proof (bound_core emin prec (1 / (1 + u prec) * u prec ^ 1)
              (up_bound_dot_1_0 emin prec) (up_bound_dot_1_1 emin prec)
              (up_bound_dot_1_2 emin prec) (up_bound_dot_1_3 emin prec)
              (up_bound_dot_1_5 emin prec) m
              (proj1 (rel_one_limb prec)) (C_dot_1_0 emin prec) (C_dot_1_1 emin prec)
              (c2_eq emin prec Hh) (c3_format emin prec) (c3_ge emin prec)
              (c5_le emin prec Hh) Fm Hm) as H.
cbv zeta in H. destruct H as [Hg0 Hok].
pose proof (bound_abs emin prec (1 / 2 * eta emin) (up_bound_dot_1_4 emin prec)
              (up_bound_dot_1_3 emin prec) (up_bound_dot_1_6 emin prec) m _
              Htau (C_dot_1_4 emin prec) (c3_format emin prec) (c3_ge emin prec)
              (c6_le emin prec Hh) Hm (rnd_format emin prec _) Hg0) as HT.
cbv zeta in HT.
unfold bound_dot_1. cbv beta iota zeta.
split. unfold fmt. apply (rnd_format emin prec).
split. unfold fmt. apply (rnd_format emin prec).
split. exact Hg0.
intros E. apply andb_true_iff in E. destruct E as [Ea Eg].
apply Rle_bool_inv in Ea. apply Rle_bool_inv in Eg.
destruct (Hok Ea) as [H1 H2].
split. exact H1. split. exact H2. exact (HT Eg).
Qed.

Theorem bound_dot_1_correct : bound_dot_1_spec.
Proof.
intros emin prec Hp m Fm Hm Hh.
generalize (bound_dot_1_facts emin prec Hp m Fm Hm Hh).
destruct (bound_dot_1 emin prec tie_even m) as [[g t] ok].
intros [Fg [Ft [_ H]]].
split. exact Fg. split. exact Ft.
split; [|split]; intros E; destruct (H E) as [H1 [H2 H3]].
- apply Rle_trans with (1 := H1). lra.
- exact H2.
- exact H3.
Qed.

(* bound_dot_2. *)
Lemma bound_dot_2_facts :
  forall emin prec : Z, (4 <= prec)%Z ->
  forall m : R, fmt emin prec m -> (m = 0 \/ 1 <= m) -> eta emin <= / 2 ->
  let '(g, t, ok) := bound_dot_2 emin prec tie_even m in
  fmt emin prec g /\ fmt emin prec t /\ 0 <= g /\
  (ok = true ->
   m * (4 * u prec ^ 2) <= / 2 /\
   m * (4 * u prec ^ 2) / (1 - m * (4 * u prec ^ 2)) <= g /\
   m * (3 / 2 * eta emin) * (1 + g) <= t).
Proof.
intros emin prec Hp m Fm Hm Hh.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 4%Z; lia).
assert (Htau : 0 <= 3 / 2 * eta emin).
{ assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. }
pose proof (bound_core emin prec (4 * u prec ^ 2)
              (up_bound_dot_2_0 emin prec) (up_bound_dot_2_1 emin prec)
              (up_bound_dot_1_2 emin prec) (up_bound_dot_1_3 emin prec)
              (up_bound_dot_1_5 emin prec) m
              (proj1 (rel_mul_2_2 prec Hp)) (C_dot_2_0 emin prec) (C_dot_2_1 emin prec)
              (c2_eq emin prec Hh) (c3_format emin prec) (c3_ge emin prec)
              (c5_le emin prec Hh) Fm Hm) as H.
cbv zeta in H. destruct H as [Hg0 Hok].
pose proof (bound_abs emin prec (3 / 2 * eta emin) (up_bound_dot_2_4 emin prec)
              (up_bound_dot_1_3 emin prec) (up_bound_dot_1_6 emin prec) m _
              Htau (C_dot_2_4 emin prec) (c3_format emin prec) (c3_ge emin prec)
              (c6_le emin prec Hh) Hm (rnd_format emin prec _) Hg0) as HT.
cbv zeta in HT.
unfold bound_dot_2. cbv beta iota zeta.
split. unfold fmt. apply (rnd_format emin prec).
split. unfold fmt. apply (rnd_format emin prec).
split. exact Hg0.
intros E. apply andb_true_iff in E. destruct E as [Ea Eg].
apply Rle_bool_inv in Ea. apply Rle_bool_inv in Eg.
destruct (Hok Ea) as [H1 H2].
split. exact H1. split. exact H2. exact (HT Eg).
Qed.

Theorem bound_dot_2_correct : bound_dot_2_spec.
Proof.
intros emin prec Hp m Fm Hm Hh.
generalize (bound_dot_2_facts emin prec Hp m Fm Hm Hh).
destruct (bound_dot_2 emin prec tie_even m) as [[g t] ok].
intros [Fg [Ft [_ H]]].
split. exact Fg. split. exact Ft.
split; [|split]; intros E; destruct (H E) as [H1 [H2 H3]].
- apply Rle_trans with (1 := H1). lra.
- exact H2.
- exact H3.
Qed.
