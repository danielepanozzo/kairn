(* The steps of the folds, as kernels: the generated statements of dot_step_1, dot_step_2,
   sum_entry_step_1, sum_entry_step_2 and sum_fast_entry_step_2 (proofs/gen/Statements.v).

   A fold applies a step to its state and one element of each array. Each step is a
   kernel with a statement of its own, which says what one application does; the bound of
   the whole loop is not here (FoldSums.v).

   - dot_step_1 (s, x, y) is one fused operation, t = RN (x y + s): a number of the
     format, the rounding to nearest of s + x y.
   - dot_step_2 (s, x, y) is p = mul_2_2 (x, y); t = add_2_2 (s, p). With
     e = 3 u^2 / (1 - 4 u) the bound of add_2_2, and 4 u^2 |x y| + 3/2 eta that of
     mul_2_2,
         |t - (s + x y)| <= e |s + p| + |p - x y|
                         <= e |s| + (e (1 + 4 u^2) + 4 u^2) |x y| + (1 + e) 3/2 eta,
     which is at most (e (1 + 4 u^2) + 4 u^2) (|s| + |x y|) + 2 eta because e <= 1/3
     (from precision 4, e <= 1/64). The generated statement prints the factor as
     (3 (1 + 4 u u) / (1 - 4 u) + 4) u^2.
   - The three entry steps of the sums pass each limb of the element through the guard,
     RN (x + 0), and then call add_1_1, add_2_2 or add_fast_2_2. A limb that is a number
     of the format passes unchanged (guard_real_any), so each statement is that of the
     addition. The entry step of the dot product of one limb, dot_entry_step_1, guards
     both factors and is then dot_step_1, by the same argument. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard OneLimb Add22 AddFast22 Mul22 Ball2.
Open Scope R_scope.

(** * dot_step_1 *)

Theorem dot_step_1_correct : dot_step_1_spec.
Proof.
intros emin prec Hp s x y Fs Fx Fy t. unfold t, dot_step_1. clear t. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
split. limb_format.
unfold RN. now rewrite (Rplus_comm s (x * y)).
Qed.

(** * dot_entry_step_1 *)

(* dot_step_1 on the guarded elements (rule R3, the factors of a fused operation): an element
   of the format passes the guard unchanged (guard_real_any), so the statement is that of
   dot_step_1. *)
Theorem dot_entry_step_1_correct : dot_entry_step_1_spec.
Proof.
intros emin prec Hp s x y Fs Fx Fy t. unfold t, dot_entry_step_1. clear t. cbv zeta.
rewrite (guard_real_any emin prec tie_even x Fx), (guard_real_any emin prec tie_even y Fy).
exact (dot_step_1_correct emin prec Hp s x y Fs Fx Fy).
Qed.

(** * dot_step_2 *)

(* The bound, in real numbers: P is the computed product, T the computed sum, uu and ee
   stand for u and eta. *)
Lemma dot_step_2_arith :
  forall uu ee S X P T : R, 0 < uu <= / 16 -> 0 <= ee ->
  Rabs (P - X) <= 4 * uu ^ 2 * Rabs X + 3 / 2 * ee ->
  Rabs (T - (S + P)) <= 3 / (1 - 4 * uu) * uu ^ 2 * Rabs (S + P) ->
  Rabs (T - (S + X)) <=
    (3 * (1 + 4 * uu * uu) / (1 - 4 * uu) + 4) * uu ^ 2 * (Rabs S + Rabs X) + 2 * ee.
Proof.
intros uu ee S X P T Hu He HP HT.
assert (C : (3 * (1 + 4 * uu * uu) / (1 - 4 * uu) + 4) * uu ^ 2 =
            3 / (1 - 4 * uu) * uu ^ 2 * (1 + 4 * uu ^ 2) + 4 * uu ^ 2) by (field; lra).
rewrite C. clear C.
assert (Hm : 3 / (1 - 4 * uu) * uu ^ 2 * (1 - 4 * uu) = 3 * uu ^ 2) by (field; lra).
set (ea := 3 / (1 - 4 * uu) * uu ^ 2) in *.
assert (Hq : 0 <= uu ^ 2 <= / 256).
{ replace (uu ^ 2) with (uu * uu) by ring. split.
  - apply Rmult_le_pos; lra.
  - replace (/ 256) with (/ 16 * / 16) by lra. apply Rmult_le_compat; lra. }
assert (Hi : 0 < / (1 - 4 * uu)) by (apply Rinv_0_lt_compat; lra).
assert (Hea0 : 0 <= ea).
{ unfold ea, Rdiv. apply Rmult_le_pos; [apply Rmult_le_pos; lra | lra]. }
assert (Hea : ea <= / 3).
{ assert (K : ea * (3 / 4) <= ea * (1 - 4 * uu)) by (apply Rmult_le_compat_l; lra). lra. }
assert (T1 : Rabs (S + P) <= Rabs S + Rabs X + Rabs (P - X)).
{ replace (S + P) with (S + X + (P - X)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang S X). lra. }
assert (T2 : Rabs (T - (S + X)) <= Rabs (T - (S + P)) + Rabs (P - X)).
{ replace (T - (S + X)) with ((T - (S + P)) + (P - X)) by ring. apply Rabs_triang. }
assert (A1 : ea * Rabs (S + P) <= ea * (Rabs S + Rabs X + (4 * uu ^ 2 * Rabs X + 3 / 2 * ee))).
{ apply Rmult_le_compat_l. exact Hea0. lra. }
assert (N1 : 0 <= uu ^ 2 * Rabs S) by (apply Rmult_le_pos; [lra | apply Rabs_pos]).
assert (N2 : 0 <= ea * (uu ^ 2 * Rabs S)) by (apply Rmult_le_pos; assumption).
assert (N3 : ea * ee <= / 3 * ee) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

Theorem dot_step_2_correct : dot_step_2_spec.
Proof.
intros emin prec Hp s0 s1 x0 x1 y0 y1 Ns Nx Ny.
assert (Hp3 : (3 <= prec)%Z) by lia.
unfold dot_step_2.
generalize (mul_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (mul_2_2 emin prec tie_even x0 x1 y0 y1) as [p0 p1]. intros [Np Ep].
generalize (add_2_2_correct emin prec Hp3 s0 s1 p0 p1 Ns Np).
destruct (add_2_2 emin prec tie_even s0 s1 p0 p1) as [t0 t1]. intros [Nt Et].
split. exact Nt.
apply dot_step_2_arith with (P := p0 + p1).
- exact (u_bounds prec 4 Hp).
- unfold eta. apply bpow_ge_0.
- exact Ep.
- exact Et.
Qed.

(** * dot_entry_step_2 *)

(* dot_step_2 on the guarded limbs of the elements (rule R3, the factors of a fused operation):
   the limbs of a normalized pair are numbers of the format and pass the guard unchanged
   (guard_real_any), so the statement is that of dot_step_2. *)
Theorem dot_entry_step_2_correct : dot_entry_step_2_spec.
Proof.
intros emin prec Hp s0 s1 x0 x1 y0 y1 Ns Nx Ny. unfold dot_entry_step_2. cbv zeta.
pose proof Nx as [Fx0 [Fx1 _]]. pose proof Ny as [Fy0 [Fy1 _]].
rewrite (guard_real_any emin prec tie_even x0 Fx0), (guard_real_any emin prec tie_even x1 Fx1),
        (guard_real_any emin prec tie_even y0 Fy0), (guard_real_any emin prec tie_even y1 Fy1).
generalize (dot_step_2_correct emin prec Hp s0 s1 x0 x1 y0 y1 Ns Nx Ny).
destruct (dot_step_2 emin prec tie_even s0 s1 x0 x1 y0 y1) as [t0 t1]. intros H. exact H.
Qed.

(** * The entry steps of the sums *)

Theorem sum_entry_step_1_correct : sum_entry_step_1_spec.
Proof.
intros emin prec Hp s x Fs Fx t. unfold t, sum_entry_step_1. clear t. cbv zeta.
rewrite (guard_real_any emin prec tie_even x Fx).
exact (add_1_1_correct emin prec Hp s x Fs Fx).
Qed.

Theorem sum_entry_step_2_correct : sum_entry_step_2_spec.
Proof.
intros emin prec Hp s0 s1 x0 x1 Ns Nx.
unfold sum_entry_step_2. cbv zeta.
destruct Nx as [F0 [F1 Hx]].
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
assert (Nx : normalized_2 emin prec x0 x1) by (split; [exact F0 | split; [exact F1 | exact Hx]]).
generalize (add_2_2_correct emin prec Hp s0 s1 x0 x1 Ns Nx).
destruct (add_2_2 emin prec tie_even s0 s1 x0 x1) as [t0 t1]. intros H. exact H.
Qed.

Theorem sum_fast_entry_step_2_correct : sum_fast_entry_step_2_spec.
Proof.
intros emin prec Hp s0 s1 x0 x1 Ns Nx.
unfold sum_fast_entry_step_2. cbv zeta.
destruct Nx as [F0 [F1 Hx]].
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1).
assert (Nx : normalized_2 emin prec x0 x1) by (split; [exact F0 | split; [exact F1 | exact Hx]]).
generalize (add_fast_2_2_correct emin prec Hp s0 s1 x0 x1 Ns Nx).
destruct (add_fast_2_2 emin prec tie_even s0 s1 x0 x1) as [t0 t1]. intros H. exact H.
Qed.
