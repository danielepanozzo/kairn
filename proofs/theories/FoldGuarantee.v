(* What a program relies on: the exported bound covers the error of the fold.

   The library gives a program two things about a sum or a dot product of an array: the
   result of the fold, and a number g (for a dot product, two numbers g and t) computed
   by a bound kernel from a count m. This file proves that they fit together, for every
   fold of proofs/gen/FoldModel.v, in both orders, in the real model:

       if the bound kernel, called with a count m that is at least the count of the fold,
       returns ok = true, then
           |result - sum v_i| <= g sum |v_i|              (a sum)
           |result - sum v_i| <= g sum |v_i| + t          (a dot product, v_i = x_i y_i),
       and the result is valid (a number of the format; normalized for two limbs).

   The count of each fold, for n elements:

       fold                               bound kernel   count        precision
       sum_1, sum_1_entry                 bound_sum_1    m >= n - 1   p >= 1
       sum_2, sum_2_entry                 bound_sum_2    m >= n - 1   p >= 3
       sum_fast_2, sum_fast_2_entry       bound_sum_2    m >= n - 1   p >= 3
       dot_1, dot_1_entry                 bound_dot_1    m >= n       p >= 1
       dot_2, dot_2_entry                 bound_dot_2    m >= n       p >= 4

   n - 1 is a natural number, 0 for the empty array. These are the counts of
   docs/developer/design/milestone2.md, "In the header": sum(n) passes n - 1, the number
   of additions on a path, and dot(n) passes n, the number of terms. m is any number of
   the format that is 0 or at least 1 and not below the count: when the count is not a
   number of the format, the next one above it serves, and so does any larger count for
   which the kernel still answers ok. The same m serves both orders and every number of
   lanes, because the generated statements of the lane order have the heights of the
   sequential one.

   How the two statements compose. The statement of a fold is in the form with a power,
   ((1 + eps)^h - 1) sum |v_i|; the bound kernel proves m eps <= 1/2 and
   g >= m eps / (1 - m eps) (BoundKernels.v). Between them:
       (1 + eps)^h - 1 <= h eps / (1 - h eps)        for h eps < 1 (pow_minus_1_le_gamma)
                       <= m eps / (1 - m eps)        for h <= m, m eps < 1 (gamma_le_real).
   - sum_fast_2 adds with add_fast_2_2, whose relative error 3 u^2 is below the
     3 u^2 / (1 - 4 u) of add_2_2 that bound_sum_2 is computed for (eps_fast_le), so the
     bound of the accurate sum covers it. Its own fold is proved from precision 2; the
     bound kernel from precision 3.
   - dot_1: the relative factor is (1 + eps)^n - 1 <= g, and the absolute term
     (1 + eps)^(n-1) n eta / 2 is at most (1 + g) m eta / 2 <= t, since
     (1 + eps)^(n-1) <= (1 + eps)^n <= 1 + g.
   - dot_2: with ex = 4 u^2 of mul_2_2 and ea = 3 u^2 / (1 - 4 u) of add_2_2, ea <= ex
     from precision 4, so (1 + ex) (1 + ea)^(n-1) <= (1 + ex)^n <= 1 + g, which bounds the
     relative factor and the factor of the absolute term n (3/2) eta. For n = 0 the
     relative factor of the statement is ex and not 0, and there is nothing to bound:
     the sum of the magnitudes is 0.

   The theorems use K_facts of each bound kernel (BoundKernels.v), which has what its
   generated statement says, m eps <= 1/2 included, without which
   g >= m eps / (1 - m eps) bounds nothing, and 0 <= g. *)
From Stdlib Require Import Reals ZArith List Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements FoldModel FoldStatements.
From Kairn Require Import Format Ball2 Folds Summation SummationKernels FoldSums BoundKernels.
Import ListNotations.
Open Scope R_scope.

(** * From the power to the quotient, for a real count *)

(* (1 + e)^h - 1 <= m e / (1 - m e) for a real number m >= h with m e <= 1/2. *)
Lemma gamma_le_real :
  forall (e : R) (h : nat) (m : R), 0 <= e -> INR h <= m -> m * e <= / 2 ->
  (1 + e) ^ h - 1 <= m * e / (1 - m * e).
Proof.
intros e h m He Hm Hme.
assert (Hh : INR h * e <= m * e) by (apply Rmult_le_compat_r; assumption).
assert (H1 : INR h * e < 1) by lra.
apply Rle_trans with (1 := pow_minus_1_le_gamma e h He H1). unfold gamma.
assert (Hx0 : 0 <= INR h * e) by (apply Rmult_le_pos; [apply pos_INR | exact He]).
set (x := INR h * e) in *. set (y := m * e) in *.
apply Rmult_le_reg_r with ((1 - x) * (1 - y)).
- apply Rmult_lt_0_compat; lra.
- replace (x / (1 - x) * ((1 - x) * (1 - y))) with (x * (1 - y)) by (field; lra).
  replace (y / (1 - y) * ((1 - x) * (1 - y))) with (y * (1 - x)) by (field; lra).
  lra.
Qed.

(* A sum: the statement of the fold with the power, for an addition of relative error
   e' <= e, and the two facts of the bound kernel computed for e. *)
Lemma sum_bound_from_power :
  forall (e' e : R) (h : nat) (m g err a : R),
  0 <= e' <= e -> INR h <= m -> m * e <= / 2 -> m * e / (1 - m * e) <= g -> 0 <= a ->
  err <= ((1 + e') ^ h - 1) * a -> err <= g * a.
Proof.
intros e' e h m g err a [He' He] Hn Hm Hg Ha Herr.
assert (He0 : 0 <= e) by lra.
assert (P : (1 + e') ^ h <= (1 + e) ^ h) by (apply pow_incr; split; lra).
assert (G : (1 + e) ^ h - 1 <= g).
{ apply Rle_trans with (2 := Hg). now apply gamma_le_real. }
assert (K : ((1 + e') ^ h - 1) * a <= g * a) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(* A dot product. F is the relative factor of the statement of the fold, plus 1. *)
Lemma dot_bound_core :
  forall (ex ea tau F : R) (n : nat) (m g t err a : R),
  0 <= ea <= ex -> 0 <= tau ->
  INR n <= m -> m * ex <= / 2 -> m * ex / (1 - m * ex) <= g -> m * tau * (1 + g) <= t ->
  0 <= a -> (F <= (1 + ex) ^ n \/ a = 0) ->
  err <= (F - 1) * a + (1 + ea) ^ (n - 1) * (INR n * tau) ->
  err <= g * a + t.
Proof.
intros ex ea tau F n m g t err a [Hea Hex] Htau Hn Hm Hg Ht Ha HF Herr.
assert (Hex0 : 0 <= ex) by lra.
assert (G : (1 + ex) ^ n - 1 <= g).
{ apply Rle_trans with (2 := Hg). now apply gamma_le_real. }
assert (Q1 : (1 + ea) ^ (n - 1) <= (1 + ex) ^ (n - 1)) by (apply pow_incr; split; lra).
assert (Q2 : (1 + ex) ^ (n - 1) <= (1 + ex) ^ n) by (apply Rle_pow; [lra | lia]).
assert (Q0 : 0 <= (1 + ea) ^ (n - 1)) by (apply pow_le; lra).
assert (N0 : 0 <= INR n) by apply pos_INR.
assert (A : (1 + ea) ^ (n - 1) * (INR n * tau) <= (1 + g) * (m * tau)).
{ apply Rmult_le_compat.
  - exact Q0.
  - apply Rmult_le_pos; assumption.
  - lra.
  - apply Rmult_le_compat_r; assumption. }
assert (B : (F - 1) * a <= g * a).
{ destruct HF as [HF|HF].
  - apply Rmult_le_compat_r. exact Ha. lra.
  - rewrite HF. lra. }
lra.
Qed.

(* The relative error of the fast addition is at most that of the accurate one. *)
Lemma eps_fast_le :
  forall prec : Z, (3 <= prec)%Z ->
  0 <= 3 * u prec ^ 2 <= 3 / (1 - 4 * u prec) * u prec ^ 2.
Proof.
intros prec Hp.
assert (Hu : 0 < u prec <= / 8) by exact (u_bounds prec 3 Hp).
assert (Hq : 0 <= u prec ^ 2) by (apply pow_le; lra).
split. lra.
apply Rmult_le_compat_r. exact Hq.
apply Rmult_le_reg_r with (1 - 4 * u prec). lra.
unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra. lra.
Qed.

(** * What the bound kernels give when they answer ok *)

(* bound_sum_1 against a bound with the power of u / (1 + u), as the folds of one limb
   state it. *)
Lemma sum_1_use :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (m g : R) (h : nat) (err a : R),
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR h <= m ->
  bound_sum_1 emin prec tie_even m = (g, true) -> 0 <= a ->
  err <= ((1 + u prec / (1 + u prec)) ^ h - 1) * a -> err <= g * a.
Proof.
intros emin prec Hp Hh m g h err a Fm Hm Hn Hb Ha Herr.
generalize (bound_sum_1_facts emin prec Hp m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [_ [_ H]]. destruct (H eq_refl) as [H1 H2].
rewrite <- (eps_1_eq prec) in Herr.
apply (sum_bound_from_power (1 / (1 + u prec) * u prec ^ 1) (1 / (1 + u prec) * u prec ^ 1)
         h m g err a); try assumption.
split. exact (proj1 (rel_one_limb prec)). apply Rle_refl.
Qed.

(* bound_sum_2 against a bound with the power of 3 u^2 / (1 - 4 u), and against one with
   the power of 3 u^2. *)
Lemma sum_2_use :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (m g : R) (h : nat) (err a : R),
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR h <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) -> 0 <= a ->
  err <= ((1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ h - 1) * a -> err <= g * a.
Proof.
intros emin prec Hp Hh m g h err a Fm Hm Hn Hb Ha Herr.
generalize (bound_sum_2_facts emin prec Hp m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [_ [_ H]]. destruct (H eq_refl) as [H1 H2].
rewrite <- (eps_add_2_eq prec Hp) in Herr.
apply (sum_bound_from_power (3 / (1 - 4 * u prec) * u prec ^ 2)
         (3 / (1 - 4 * u prec) * u prec ^ 2) h m g err a); try assumption.
split. exact (proj1 (rel_add_2_2 prec Hp)). apply Rle_refl.
Qed.

Lemma sum_fast_2_use :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (m g : R) (h : nat) (err a : R),
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR h <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) -> 0 <= a ->
  err <= ((1 + 3 * u prec ^ 2) ^ h - 1) * a -> err <= g * a.
Proof.
intros emin prec Hp Hh m g h err a Fm Hm Hn Hb Ha Herr.
generalize (bound_sum_2_facts emin prec Hp m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [_ [_ H]]. destruct (H eq_refl) as [H1 H2].
apply (sum_bound_from_power (3 * u prec ^ 2) (3 / (1 - 4 * u prec) * u prec ^ 2)
         h m g err a); try assumption.
exact (eps_fast_le prec Hp).
Qed.

(* bound_dot_1 against the two terms of the statement of dot_1. *)
Lemma dot_1_use :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (m g t : R) (n : nat) (err a : R),
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR n <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) -> 0 <= a ->
  err <= ((1 + u prec / (1 + u prec)) ^ n - 1) * a +
         (1 + u prec / (1 + u prec)) ^ (n - 1) * (INR n * (eta emin / 2)) ->
  err <= g * a + t.
Proof.
intros emin prec Hp Hh m g t n err a Fm Hm Hn Hb Ha Herr.
generalize (bound_dot_1_facts emin prec Hp m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [_ [_ [_ H]]]. destruct (H eq_refl) as [H1 [H2 H3]].
rewrite <- (eps_1_eq prec) in Herr.
replace (eta emin / 2) with (1 / 2 * eta emin) in Herr by lra.
assert (He : 0 <= 1 / (1 + u prec) * u prec ^ 1) by exact (proj1 (rel_one_limb prec)).
assert (Htau : 0 <= 1 / 2 * eta emin).
{ assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. }
apply (dot_bound_core (1 / (1 + u prec) * u prec ^ 1) (1 / (1 + u prec) * u prec ^ 1)
         (1 / 2 * eta emin) ((1 + 1 / (1 + u prec) * u prec ^ 1) ^ n) n m g t err a);
  try assumption.
- split. exact He. apply Rle_refl.
- left. apply Rle_refl.
Qed.

(* bound_dot_2 against the two terms of the statement of dot_2. *)
Lemma dot_2_use :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (m g t : R) (n : nat) (err a : R),
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR n <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) -> 0 <= a -> (n = 0%nat -> a = 0) ->
  err <= ((1 + 4 * u prec ^ 2) * (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (n - 1) - 1) * a +
         (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (n - 1) * (INR n * (3 / 2 * eta emin)) ->
  err <= g * a + t.
Proof.
intros emin prec Hp Hh m g t n err a Fm Hm Hn Hb Ha H0 Herr.
assert (Hp3 : (3 <= prec)%Z) by lia.
generalize (bound_dot_2_facts emin prec Hp m Fm Hm Hh). rewrite Hb. cbv beta iota.
intros [_ [_ [_ H]]]. destruct (H eq_refl) as [H1 [H2 H3]].
assert (Hea : 0 <= 3 * u prec ^ 2 / (1 - 4 * u prec) <= 4 * u prec ^ 2).
{ split. now apply eps_add_2_ge_0. now apply eps_add_2_le_mul_2. }
assert (Htau : 0 <= 3 / 2 * eta emin).
{ assert (0 <= eta emin) by (unfold eta; apply bpow_ge_0). lra. }
apply (dot_bound_core (4 * u prec ^ 2) (3 * u prec ^ 2 / (1 - 4 * u prec))
         (3 / 2 * eta emin)
         ((1 + 4 * u prec ^ 2) * (1 + 3 * u prec ^ 2 / (1 - 4 * u prec)) ^ (n - 1))
         n m g t err a); try assumption.
destruct n as [|k].
- right. now apply H0.
- left. replace (S k - 1)%nat with k by lia.
  rewrite <- (tech_pow_Rmult (1 + 4 * u prec ^ 2) k).
  apply Rmult_le_compat_l. lra. apply pow_incr. split; lra.
Qed.

(** * One limb: the sums *)

Theorem sum_1_seq_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list R) (m g : R),
  Forall (fun x => fmt emin prec x) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_1 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_1_seq emin prec tie_even xs in
  fmt emin prec s /\ Rabs (s - sumR xs) <= g * sumabs xs.
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_1_seq_correct emin prec Hp xs Hv) as K. cbv zeta in K.
rewrite map_id in K. destruct K as [Fs Es].
split. exact Fs.
exact (sum_1_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 xs) Es).
Qed.

Theorem sum_1_lanes_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list R) (m g : R),
  Forall (fun x => fmt emin prec x) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_1 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_1_lanes emin prec tie_even W xs in
  fmt emin prec s /\ Rabs (s - sumR xs) <= g * sumabs xs.
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_1_lanes_correct emin prec Hp W xs Hv) as K. cbv zeta in K.
rewrite map_id in K. destruct K as [Fs Es].
split. exact Fs.
exact (sum_1_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 xs) Es).
Qed.

Theorem sum_1_entry_seq_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list R) (m g : R),
  Forall (fun x => fmt emin prec x) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_1 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_1_entry_seq emin prec tie_even xs in
  fmt emin prec s /\ Rabs (s - sumR xs) <= g * sumabs xs.
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_1_entry_seq_correct emin prec Hp xs Hv) as K. cbv zeta in K.
rewrite map_id in K. destruct K as [Fs Es].
split. exact Fs.
exact (sum_1_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 xs) Es).
Qed.

Theorem sum_1_entry_lanes_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list R) (m g : R),
  Forall (fun x => fmt emin prec x) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_1 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_1_entry_lanes emin prec tie_even W xs in
  fmt emin prec s /\ Rabs (s - sumR xs) <= g * sumabs xs.
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_1_entry_lanes_correct emin prec Hp W xs Hv) as K. cbv zeta in K.
rewrite map_id in K. destruct K as [Fs Es].
split. exact Fs.
exact (sum_1_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 xs) Es).
Qed.

(** * Two limbs: the sums *)

Theorem sum_2_seq_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_2_seq emin prec tie_even xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_2_seq_correct emin prec Hp xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_2_lanes_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_2_lanes emin prec tie_even W xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_2_lanes_correct emin prec Hp W xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_2_entry_seq_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_2_entry_seq emin prec tie_even xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_2_entry_seq_correct emin prec Hp xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_2_entry_lanes_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_2_entry_lanes emin prec tie_even W xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (sum_2_entry_lanes_correct emin prec Hp W xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

(** * Two limbs: the sums with the fast addition, under the bound of the accurate one *)

Theorem sum_fast_2_seq_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_fast_2_seq emin prec tie_even xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
assert (Hp2 : (2 <= prec)%Z) by lia.
pose proof (sum_fast_2_seq_correct emin prec Hp2 xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_fast_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_fast_2_lanes_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_fast_2_lanes emin prec tie_even W xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
assert (Hp2 : (2 <= prec)%Z) by lia.
pose proof (sum_fast_2_lanes_correct emin prec Hp2 W xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_fast_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_fast_2_entry_seq_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_fast_2_entry_seq emin prec tie_even xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
assert (Hp2 : (2 <= prec)%Z) by lia.
pose proof (sum_fast_2_entry_seq_correct emin prec Hp2 xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_fast_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem sum_fast_2_entry_lanes_bound :
  forall emin prec : Z, (3 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xs : list (R * R)) (m g : R),
  Forall (fun x => normalized_2 emin prec (fst x) (snd x)) xs ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xs - 1) <= m ->
  bound_sum_2 emin prec tie_even m = (g, true) ->
  let s := FoldModel.sum_fast_2_entry_lanes emin prec tie_even W xs in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) - sumR (map (fun x => fst x + snd x) xs)) <=
    g * sumabs (map (fun x => fst x + snd x) xs).
Proof.
intros emin prec Hp Hh W xs m g Hv Fm Hm Hn Hb s. unfold s. clear s.
assert (Hp2 : (2 <= prec)%Z) by lia.
pose proof (sum_fast_2_entry_lanes_correct emin prec Hp2 W xs Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (sum_fast_2_use emin prec Hp Hh m g _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

(** * The dot products *)

Theorem dot_1_seq_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (xys : list (R * R)) (m g t : R),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_1_seq emin prec tie_even xys in
  fmt emin prec s /\
  Rabs (s - sumR (map (fun xy => fst xy * snd xy) xys)) <=
    g * sumabs (map (fun xy => fst xy * snd xy) xys) + t.
Proof.
intros emin prec Hp Hh xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_1_seq_correct emin prec Hp xys Hv) as K. cbv zeta in K.
destruct K as [Fs Es].
split. exact Fs.
exact (dot_1_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem dot_1_lanes_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xys : list (R * R)) (m g t : R),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_1_lanes emin prec tie_even W xys in
  fmt emin prec s /\
  Rabs (s - sumR (map (fun xy => fst xy * snd xy) xys)) <=
    g * sumabs (map (fun xy => fst xy * snd xy) xys) + t.
Proof.
intros emin prec Hp Hh W xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_1_lanes_correct emin prec Hp W xys Hv) as K. cbv zeta in K.
destruct K as [Fs Es].
split. exact Fs.
exact (dot_1_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem dot_1_entry_seq_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (xys : list (R * R)) (m g t : R),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_1_entry_seq emin prec tie_even xys in
  fmt emin prec s /\
  Rabs (s - sumR (map (fun xy => fst xy * snd xy) xys)) <=
    g * sumabs (map (fun xy => fst xy * snd xy) xys) + t.
Proof.
intros emin prec Hp Hh xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_1_entry_seq_correct emin prec Hp xys Hv) as K. cbv zeta in K.
destruct K as [Fs Es].
split. exact Fs.
exact (dot_1_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

Theorem dot_1_entry_lanes_bound :
  forall emin prec : Z, (1 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xys : list (R * R)) (m g t : R),
  Forall (fun xy => fmt emin prec (fst xy) /\ fmt emin prec (snd xy)) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_1 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_1_entry_lanes emin prec tie_even W xys in
  fmt emin prec s /\
  Rabs (s - sumR (map (fun xy => fst xy * snd xy) xys)) <=
    g * sumabs (map (fun xy => fst xy * snd xy) xys) + t.
Proof.
intros emin prec Hp Hh W xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_1_entry_lanes_correct emin prec Hp W xys Hv) as K. cbv zeta in K.
destruct K as [Fs Es].
split. exact Fs.
exact (dot_1_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _) Es).
Qed.

(* The sum of the magnitudes of no term is zero. *)
Lemma sumabs_map_nil :
  forall (A : Type) (f : A -> R) (l : list A), length l = 0%nat -> sumabs (map f l) = 0.
Proof. intros A f l H. destruct l; [reflexivity | discriminate H]. Qed.

Theorem dot_2_seq_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (xys : list ((R * R) * (R * R))) (m g t : R),
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                    normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_2_seq emin prec tie_even xys in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) -
        sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys)) <=
    g * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys) + t.
Proof.
intros emin prec Hp Hh xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_2_seq_correct emin prec Hp xys Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (dot_2_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _)
         (sumabs_map_nil _ _ xys) Es).
Qed.

Theorem dot_2_lanes_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xys : list ((R * R) * (R * R))) (m g t : R),
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                    normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_2_lanes emin prec tie_even W xys in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) -
        sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys)) <=
    g * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys) + t.
Proof.
intros emin prec Hp Hh W xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_2_lanes_correct emin prec Hp W xys Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (dot_2_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _)
         (sumabs_map_nil _ _ xys) Es).
Qed.

(* dot_2_entry, the loop of kairn::dot of two limbs (rule R3, the factors of a fused operation):
   the same bound, from its own statements. *)
Theorem dot_2_entry_seq_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (xys : list ((R * R) * (R * R))) (m g t : R),
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                    normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_2_entry_seq emin prec tie_even xys in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) -
        sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys)) <=
    g * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys) + t.
Proof.
intros emin prec Hp Hh xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_2_entry_seq_correct emin prec Hp xys Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (dot_2_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _)
         (sumabs_map_nil _ _ xys) Es).
Qed.

Theorem dot_2_entry_lanes_bound :
  forall emin prec : Z, (4 <= prec)%Z -> eta emin <= / 2 ->
  forall (W : nat) (xys : list ((R * R) * (R * R))) (m g t : R),
  Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                    normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) xys ->
  fmt emin prec m -> (m = 0 \/ 1 <= m) -> INR (length xys) <= m ->
  bound_dot_2 emin prec tie_even m = (g, t, true) ->
  let s := FoldModel.dot_2_entry_lanes emin prec tie_even W xys in
  normalized_2 emin prec (fst s) (snd s) /\
  Rabs ((fst s + snd s) -
        sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys)) <=
    g * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) xys) + t.
Proof.
intros emin prec Hp Hh W xys m g t Hv Fm Hm Hn Hb s. unfold s. clear s.
pose proof (dot_2_entry_lanes_correct emin prec Hp W xys Hv) as K. cbv zeta in K.
destruct K as [Ns Es].
split. exact Ns.
exact (dot_2_use emin prec Hp Hh m g t _ _ _ Fm Hm Hn Hb (sumabs_ge_0 _)
         (sumabs_map_nil _ _ xys) Es).
Qed.
