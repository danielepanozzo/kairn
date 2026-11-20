(* The kernels of the accumulator in the real model: the generated statements of acc_add_1,
   acc_add_2, acc_mul_1, acc_mul_2, acc_merge_1 and acc_merge_2 (proofs/gen/Statements.v).

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
   dot_step_2_correct), and each b is one rounding to nearest, the claim itself. *)
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
