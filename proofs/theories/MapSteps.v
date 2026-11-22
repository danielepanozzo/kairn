(* The steps of the maps, as kernels: the generated statements of sub_1_1,
   add_entry_step_1, add_entry_step_2, sub_entry_step_1, sub_entry_step_2, scale_step_1,
   scale_step_2, mul_pow2_step_1, mul_pow2_step_2, axpy_step_1, axpy_step_2,
   axpy_step_2_1, axpy_entry_step_1, axpy_entry_step_2 and axpy_entry_step_2_1
   (proofs/gen/Statements.v).

   A map writes an array: element i of the array written is a step applied to element i
   of each array read and to the scalars, which are given once. Each step is a kernel
   with a statement of its own, which says what one application does; that a map
   satisfies it entry by entry is in FoldMaps.v. (The maps add_1, add_2 and sub_2 have
   add_1_1, add_2_2 and sub_2_2 themselves as steps: OneLimb.v, Add22.v, Sign.v.)

   Every step is made of kernels that have theorems, and no arithmetic is proved again
   here. Three kinds:

   - A kernel under another name, or on guarded operands. sub_1_1 (a, b) is RN (a - b),
     which is add_1_1 (a, -b). scale_step_1 is mul_1_1, scale_step_2 is mul_2_1,
     mul_pow2_step_2 is mul_pow2_2. The entry steps add_entry_step_k and
     sub_entry_step_k pass every limb of both operands through the guard, RN (x + 0),
     and call add_1_1, sub_1_1, add_2_2 or sub_2_2; a limb that is a number of the
     format passes unchanged (guard_real_any). The statement of each is the statement
     of the kernel it calls.
   - mul_pow2_step_1 (x, c) is RN (x c) for c a power of two: a number of the format
     times a power of two is a number of the format unless it falls below
     2^(emin + prec), where the numbers of the format are eta apart, so the error is
     at most eta / 2 and there is no relative term (scale_error of MulPow2.v).
   - The steps of axpy, z = (a x) + y: a product, then a sum. If the product P is
     within em |a x| + tm of a x, and the sum S within ea |P + y| of P + y, then
         |S - (a x + y)| <= ea |P + y| + |P - a x|
                         <= (ea (1 + em) + em) |a x| + ea |y| + (1 + ea) tm
                         <= (ea (1 + em) + em) (|a x| + |y|) + (1 + ea) tm
     (axpy_compose). The claims are this composition, with the bounds of the kernels:
       axpy_step_1    mul_1_1, add_1_1    ea = em = e = u / (1 + u), tm = eta / 2
                      e (1 + e) + e = (2 + 3 u) / (1 + u)^2 u
                      (1 + e) / 2 <= 2/3 because e <= 1/3 (u <= 1/2)
       axpy_step_2    mul_2_2, add_2_2    ea = 3 u^2 / (1 - 4 u), em = 4 u^2, tm = 3/2 eta
                      ea (1 + 4 u^2) + 4 u^2 = (3 (1 + 4 u^2) / (1 - 4 u) + 4) u^2
                      (1 + ea) 3/2 <= 2 because ea <= 1/3
       axpy_step_2_1  mul_2_1, add_2_2    ea as above, em = 2 u^2, tm = eta
                      ea (1 + 2 u^2) + 2 u^2 = (3 (1 + 2 u^2) / (1 - 4 u) + 2) u^2
                      1 + ea <= 5/4 because ea <= 1/4
     where ea <= 3/32 from precision 3 (u <= 1/8). The relative constant of each claim
     is exactly what the composition gives; the absolute one is that of the product
     times 1 + ea, rounded up to a simple fraction. The entry forms guard y before the
     sum, and have the statements of the steps they guard. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Guard OneLimb Add22 Sign Mul21 Mul22 MulPow2 Ball2.
Open Scope R_scope.

(** * A kernel under another name *)

(* a - b is a + (-b), and -b is a number of the format. *)
Theorem sub_1_1_correct : sub_1_1_spec.
Proof.
intros emin prec Hp a b Fa Fb.
assert (Fn : fmt emin prec (- b)).
{ unfold fmt in *. now apply generic_format_opp. }
exact (add_1_1_correct emin prec Hp a (- b) Fa Fn).
Qed.

Theorem scale_step_1_correct : scale_step_1_spec.
Proof.
intros emin prec Hp x a Fx Fa.
exact (mul_1_1_correct emin prec Hp x a Fx Fa).
Qed.

Theorem scale_step_2_correct : scale_step_2_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa.
unfold scale_step_2.
generalize (mul_2_1_correct emin prec Hp x0 x1 a Nx Fa).
destruct (mul_2_1 emin prec tie_even x0 x1 a) as [z0 z1]. intros H. exact H.
Qed.

(* scale_step_2 on the limbs of x and on a guarded (rule R3, the factors of a fused operation): numbers
   of the format pass the guard unchanged (guard_real_any), so the statement is that of
   scale_step_2. *)
Theorem scale_entry_step_2_correct : scale_entry_step_2_spec.
Proof.
intros emin prec Hp x0 x1 a Nx Fa. unfold scale_entry_step_2. cbv zeta.
destruct Nx as [F0 [F1 Hx]].
rewrite (guard_real_any emin prec tie_even x0 F0), (guard_real_any emin prec tie_even x1 F1),
        (guard_real_any emin prec tie_even a Fa).
assert (Nx : normalized_2 emin prec x0 x1) by (split; [exact F0 | split; [exact F1 | exact Hx]]).
generalize (scale_step_2_correct emin prec Hp x0 x1 a Nx Fa).
destruct (scale_step_2 emin prec tie_even x0 x1 a) as [z0 z1]. intros H. exact H.
Qed.

Theorem mul_pow2_step_2_correct : mul_pow2_step_2_spec.
Proof.
intros emin prec Hp x0 x1 c Nx Fc Hc.
unfold mul_pow2_step_2.
generalize (mul_pow2_2_correct emin prec Hp x0 x1 c Nx Fc Hc).
destruct (mul_pow2_2 emin prec tie_even x0 x1 c) as [z0 z1]. intros H. exact H.
Qed.

(** * One limb times a power of two *)

Theorem mul_pow2_step_1_correct : mul_pow2_step_1_spec.
Proof.
intros emin prec Hp x c Fx Fc [n Hc] z. unfold z, mul_pow2_step_1. clear z. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
rewrite !Rplus_0_r.
split. limb_format.
split. reflexivity.
subst c.
generalize (scale_error emin prec x n Fx). unfold RN, eta. lra.
Qed.

(** * The entry steps of the sums and differences *)

Theorem add_entry_step_1_correct : add_entry_step_1_spec.
Proof.
intros emin prec Hp x y Fx Fy z. unfold z, add_entry_step_1. clear z. cbv zeta.
rewrite (guard_real_any emin prec tie_even x Fx), (guard_real_any emin prec tie_even y Fy).
exact (add_1_1_correct emin prec Hp x y Fx Fy).
Qed.

Theorem sub_entry_step_1_correct : sub_entry_step_1_spec.
Proof.
intros emin prec Hp x y Fx Fy z. unfold z, sub_entry_step_1. clear z. cbv zeta.
rewrite (guard_real_any emin prec tie_even x Fx), (guard_real_any emin prec tie_even y Fy).
exact (sub_1_1_correct emin prec Hp x y Fx Fy).
Qed.

Theorem add_entry_step_2_correct : add_entry_step_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
unfold add_entry_step_2. cbv zeta.
assert (Fx0 : fmt emin prec x0) by apply Nx.
assert (Fx1 : fmt emin prec x1) by apply Nx.
assert (Fy0 : fmt emin prec y0) by apply Ny.
assert (Fy1 : fmt emin prec y1) by apply Ny.
rewrite (guard_real_any emin prec tie_even x0 Fx0), (guard_real_any emin prec tie_even x1 Fx1),
        (guard_real_any emin prec tie_even y0 Fy0), (guard_real_any emin prec tie_even y1 Fy1).
generalize (add_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. intros H. exact H.
Qed.

Theorem sub_entry_step_2_correct : sub_entry_step_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 Nx Ny.
unfold sub_entry_step_2. cbv zeta.
assert (Fx0 : fmt emin prec x0) by apply Nx.
assert (Fx1 : fmt emin prec x1) by apply Nx.
assert (Fy0 : fmt emin prec y0) by apply Ny.
assert (Fy1 : fmt emin prec y1) by apply Ny.
rewrite (guard_real_any emin prec tie_even x0 Fx0), (guard_real_any emin prec tie_even x1 Fx1),
        (guard_real_any emin prec tie_even y0 Fy0), (guard_real_any emin prec tie_even y1 Fy1).
generalize (sub_2_2_correct emin prec Hp x0 x1 y0 y1 Nx Ny).
destruct (sub_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1]. intros H. exact H.
Qed.

(** * A product, then a sum *)

(* In real numbers: P is the computed product, of exact value X, and S the computed sum
   of P and Y. em and tm are the relative and the absolute error of the product, ea the
   relative error of the sum. *)
Lemma axpy_compose :
  forall ea em tm X Y P S : R, 0 <= ea -> 0 <= em ->
  Rabs (P - X) <= em * Rabs X + tm ->
  Rabs (S - (P + Y)) <= ea * Rabs (P + Y) ->
  Rabs (S - (X + Y)) <= (ea * (1 + em) + em) * (Rabs X + Rabs Y) + (1 + ea) * tm.
Proof.
intros ea em tm X Y P S Ha Hm HP HS.
assert (T1 : Rabs (P + Y) <= Rabs X + Rabs Y + Rabs (P - X)).
{ replace (P + Y) with (X + Y + (P - X)) by ring.
  apply Rle_trans with (1 := Rabs_triang _ _).
  generalize (Rabs_triang X Y). lra. }
assert (T2 : Rabs (S - (X + Y)) <= Rabs (S - (P + Y)) + Rabs (P - X)).
{ replace (S - (X + Y)) with ((S - (P + Y)) + (P - X)) by ring. apply Rabs_triang. }
assert (A1 : ea * Rabs (P + Y) <= ea * (Rabs X + Rabs Y + (em * Rabs X + tm))).
{ apply Rmult_le_compat_l. exact Ha. lra. }
assert (N1 : 0 <= em * Rabs Y) by (apply Rmult_le_pos; [exact Hm | apply Rabs_pos]).
assert (N2 : 0 <= ea * (em * Rabs Y)) by (apply Rmult_le_pos; assumption).
lra.
Qed.

(* One limb: mul_1_1 then add_1_1, both with e = u / (1 + u), which the statements print
   as 1 / (1 + u) u^1. uu and ee stand for u and eta. *)
Lemma axpy_step_1_arith :
  forall uu ee X Y P S : R, 0 < uu <= / 2 -> 0 <= ee ->
  Rabs (P - X) <= 1 / (1 + uu) * uu ^ 1 * Rabs X + 1 / 2 * ee ->
  Rabs (S - (P + Y)) <= 1 / (1 + uu) * uu ^ 1 * Rabs (P + Y) ->
  Rabs (S - (X + Y)) <=
    (2 + 3 * uu) / ((1 + uu) * (1 + uu)) * uu ^ 1 * (Rabs X + Rabs Y) + 2 / 3 * ee.
Proof.
intros uu ee X Y P S Hu He HP HS.
assert (C : (2 + 3 * uu) / ((1 + uu) * (1 + uu)) * uu ^ 1 =
            1 / (1 + uu) * uu ^ 1 * (1 + 1 / (1 + uu) * uu ^ 1) + 1 / (1 + uu) * uu ^ 1)
  by (field; lra).
rewrite C. clear C.
assert (Hm : 1 / (1 + uu) * uu ^ 1 * (1 + uu) = uu) by (field; lra).
set (e := 1 / (1 + uu) * uu ^ 1) in *.
assert (He0 : 0 <= e).
{ apply Rmult_le_reg_r with (1 + uu). lra. rewrite Hm. lra. }
assert (He3 : e <= / 3).
{ apply Rmult_le_reg_r with (1 + uu). lra. rewrite Hm. lra. }
apply Rle_trans with (1 := axpy_compose e e (1 / 2 * ee) X Y P S He0 He0 HP HS).
apply Rplus_le_compat_l.
assert (N : e * ee <= / 3 * ee) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(* The relative error of add_2_2, from precision 3. *)
Lemma rel_add_2_2_le :
  forall uu : R, 0 < uu <= / 8 -> 0 <= 3 / (1 - 4 * uu) * uu ^ 2 <= 3 / 32.
Proof.
intros uu Hu.
assert (Hm : 3 / (1 - 4 * uu) * uu ^ 2 * (1 - 4 * uu) = 3 * uu ^ 2) by (field; lra).
set (ea := 3 / (1 - 4 * uu) * uu ^ 2) in *.
assert (Hq : 0 <= uu ^ 2 <= / 64).
{ replace (uu ^ 2) with (uu * uu) by ring. split.
  - apply Rmult_le_pos; lra.
  - replace (/ 64) with (/ 8 * / 8) by lra. apply Rmult_le_compat; lra. }
assert (Hi : 0 < / (1 - 4 * uu)) by (apply Rinv_0_lt_compat; lra).
assert (Hea0 : 0 <= ea).
{ unfold ea, Rdiv. apply Rmult_le_pos; [apply Rmult_le_pos; lra | lra]. }
split. exact Hea0.
assert (K : ea * / 2 <= ea * (1 - 4 * uu)) by (apply Rmult_le_compat_l; lra).
lra.
Qed.

(* Two limbs, a of two limbs: mul_2_2 then add_2_2. *)
Lemma axpy_step_2_arith :
  forall uu ee X Y P S : R, 0 < uu <= / 16 -> 0 <= ee ->
  Rabs (P - X) <= 4 * uu ^ 2 * Rabs X + 3 / 2 * ee ->
  Rabs (S - (P + Y)) <= 3 / (1 - 4 * uu) * uu ^ 2 * Rabs (P + Y) ->
  Rabs (S - (X + Y)) <=
    (3 * (1 + 4 * uu * uu) / (1 - 4 * uu) + 4) * uu ^ 2 * (Rabs X + Rabs Y) + 2 * ee.
Proof.
intros uu ee X Y P S Hu He HP HS.
assert (C : (3 * (1 + 4 * uu * uu) / (1 - 4 * uu) + 4) * uu ^ 2 =
            3 / (1 - 4 * uu) * uu ^ 2 * (1 + 4 * uu ^ 2) + 4 * uu ^ 2) by (field; lra).
rewrite C. clear C.
assert (Hu8 : 0 < uu <= / 8) by lra.
destruct (rel_add_2_2_le uu Hu8) as [Hea0 Hea].
set (ea := 3 / (1 - 4 * uu) * uu ^ 2) in *.
assert (Hem : 0 <= 4 * uu ^ 2).
{ replace (uu ^ 2) with (uu * uu) by ring.
  apply Rmult_le_pos. lra. apply Rmult_le_pos; lra. }
apply Rle_trans with (1 := axpy_compose ea (4 * uu ^ 2) (3 / 2 * ee) X Y P S Hea0 Hem HP HS).
apply Rplus_le_compat_l.
assert (N : ea * ee <= / 3 * ee) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(* Two limbs, a of one limb: mul_2_1 then add_2_2. *)
Lemma axpy_step_2_1_arith :
  forall uu ee X Y P S : R, 0 < uu <= / 8 -> 0 <= ee ->
  Rabs (P - X) <= 2 * uu ^ 2 * Rabs X + 1 * ee ->
  Rabs (S - (P + Y)) <= 3 / (1 - 4 * uu) * uu ^ 2 * Rabs (P + Y) ->
  Rabs (S - (X + Y)) <=
    (3 * (1 + 2 * uu * uu) / (1 - 4 * uu) + 2) * uu ^ 2 * (Rabs X + Rabs Y) + 5 / 4 * ee.
Proof.
intros uu ee X Y P S Hu He HP HS.
assert (C : (3 * (1 + 2 * uu * uu) / (1 - 4 * uu) + 2) * uu ^ 2 =
            3 / (1 - 4 * uu) * uu ^ 2 * (1 + 2 * uu ^ 2) + 2 * uu ^ 2) by (field; lra).
rewrite C. clear C.
destruct (rel_add_2_2_le uu Hu) as [Hea0 Hea].
set (ea := 3 / (1 - 4 * uu) * uu ^ 2) in *.
assert (Hem : 0 <= 2 * uu ^ 2).
{ replace (uu ^ 2) with (uu * uu) by ring.
  apply Rmult_le_pos. lra. apply Rmult_le_pos; lra. }
apply Rle_trans with (1 := axpy_compose ea (2 * uu ^ 2) (1 * ee) X Y P S Hea0 Hem HP HS).
apply Rplus_le_compat_l.
assert (N : ea * ee <= / 4 * ee) by (apply Rmult_le_compat_r; lra).
lra.
Qed.

(** * The steps of axpy *)

Theorem axpy_step_1_correct : axpy_step_1_spec.
Proof.
intros emin prec Hp a x y Fa Fx Fy z. unfold z, axpy_step_1. clear z. cbv zeta.
generalize (mul_1_1_correct emin prec Hp a x Fa Fx). cbv zeta. intros [Fp [_ Ep]].
generalize (add_1_1_correct emin prec Hp (mul_1_1 emin prec tie_even a x) y Fp Fy).
cbv zeta. intros [Fz [_ Ez]].
split. exact Fz.
apply axpy_step_1_arith with (P := mul_1_1 emin prec tie_even a x).
- exact (u_bounds prec 1 Hp).
- unfold eta. apply bpow_ge_0.
- exact Ep.
- exact Ez.
Qed.

Theorem axpy_step_2_correct : axpy_step_2_spec.
Proof.
intros emin prec Hp a0 a1 x0 x1 y0 y1 Na Nx Ny.
assert (Hp3 : (3 <= prec)%Z) by lia.
unfold axpy_step_2.
generalize (mul_2_2_correct emin prec Hp a0 a1 x0 x1 Na Nx).
destruct (mul_2_2 emin prec tie_even a0 a1 x0 x1) as [p0 p1]. intros [Np Ep].
generalize (add_2_2_correct emin prec Hp3 p0 p1 y0 y1 Np Ny).
destruct (add_2_2 emin prec tie_even p0 p1 y0 y1) as [z0 z1]. intros [Nz Ez].
split. exact Nz.
apply axpy_step_2_arith with (P := p0 + p1).
- exact (u_bounds prec 4 Hp).
- unfold eta. apply bpow_ge_0.
- exact Ep.
- exact Ez.
Qed.

Theorem axpy_step_2_1_correct : axpy_step_2_1_spec.
Proof.
intros emin prec Hp a x0 x1 y0 y1 Fa Nx Ny.
assert (Hp2 : (2 <= prec)%Z) by lia.
unfold axpy_step_2_1.
generalize (mul_2_1_correct emin prec Hp2 x0 x1 a Nx Fa).
destruct (mul_2_1 emin prec tie_even x0 x1 a) as [p0 p1]. intros [Np Ep].
generalize (add_2_2_correct emin prec Hp p0 p1 y0 y1 Np Ny).
destruct (add_2_2 emin prec tie_even p0 p1 y0 y1) as [z0 z1]. intros [Nz Ez].
split. exact Nz.
rewrite (Rmult_comm a (x0 + x1)).
apply axpy_step_2_1_arith with (P := p0 + p1).
- exact (u_bounds prec 3 Hp).
- unfold eta. apply bpow_ge_0.
- exact Ep.
- exact Ez.
Qed.

(** * The entry steps of axpy *)

(* y passes through the guard before the sum; a and x are only multiplied (one limb), or every limb
   of a, x and y passes through the guard and the stored step follows (two limbs: rule R3, the
   factors of a fused operation). A number of the format passes the guard unchanged. *)
Theorem axpy_entry_step_1_correct : axpy_entry_step_1_spec.
Proof.
intros emin prec Hp a x y Fa Fx Fy z. unfold z, axpy_entry_step_1. clear z. cbv zeta.
rewrite (guard_real_any emin prec tie_even y Fy).
exact (axpy_step_1_correct emin prec Hp a x y Fa Fx Fy).
Qed.

Theorem axpy_entry_step_2_correct : axpy_entry_step_2_spec.
Proof.
intros emin prec Hp a0 a1 x0 x1 y0 y1 Na Nx Ny.
unfold axpy_entry_step_2. cbv zeta.
pose proof Na as [Fa0 [Fa1 _]]. pose proof Nx as [Fx0 [Fx1 _]]. pose proof Ny as [Fy0 [Fy1 _]].
rewrite (guard_real_any emin prec tie_even a0 Fa0), (guard_real_any emin prec tie_even a1 Fa1),
        (guard_real_any emin prec tie_even x0 Fx0), (guard_real_any emin prec tie_even x1 Fx1),
        (guard_real_any emin prec tie_even y0 Fy0), (guard_real_any emin prec tie_even y1 Fy1).
generalize (axpy_step_2_correct emin prec Hp a0 a1 x0 x1 y0 y1 Na Nx Ny).
destruct (axpy_step_2 emin prec tie_even a0 a1 x0 x1 y0 y1) as [z0 z1]. intros H. exact H.
Qed.

Theorem axpy_entry_step_2_1_correct : axpy_entry_step_2_1_spec.
Proof.
intros emin prec Hp a x0 x1 y0 y1 Fa Nx Ny.
unfold axpy_entry_step_2_1. cbv zeta.
pose proof Nx as [Fx0 [Fx1 _]]. pose proof Ny as [Fy0 [Fy1 _]].
rewrite (guard_real_any emin prec tie_even a Fa),
        (guard_real_any emin prec tie_even x0 Fx0), (guard_real_any emin prec tie_even x1 Fx1),
        (guard_real_any emin prec tie_even y0 Fy0), (guard_real_any emin prec tie_even y1 Fy1).
generalize (axpy_step_2_1_correct emin prec Hp a x0 x1 y0 y1 Fa Nx Ny).
destruct (axpy_step_2_1 emin prec tie_even a x0 x1 y0 y1) as [z0 z1]. intros H. exact H.
Qed.
