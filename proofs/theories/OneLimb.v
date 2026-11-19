(* One rounded operation as a kernel: add_1_1 and mul_1_1.

   These two kernels are one rounding to nearest each, s = RN (a + b) and p = RN (a b).
   They exist to state the error of the center of a one-limb ball, from which the ball
   kernels take their constants (Ball.v).

   What is proved (the generated statements of proofs/gen/Statements.v), for every
   precision and every eta, with u = 2^-prec:
   - add_1_1: |s - (a + b)| <= u / (1 + u) |a + b|, with no underflow term: the sum of two
     numbers of the format is a multiple of eta, so it is rounded as it would be without
     underflow (Format.round_plus_FLT_FLX).
   - mul_1_1: |p - a b| <= u / (1 + u) |a b| + eta / 2. In fact one of the two terms is
     enough: the relative one when |a b| >= 2^(emin + prec - 1), eta / 2 below.

   Source: the bound u / (1 + u) for one rounding to nearest is Flocq's
   relative_error_N_FLX' (Relative.v; the bound is due to Knuth and is sharp), and the
   form with the underflow term is its relative_error_N_FLT'_ex. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Relative.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format.
Open Scope R_scope.

(* Flocq writes the unit roundoff u_ro = 2^(1 - prec) / 2; it is u. *)
Lemma u_ro_eq : forall prec : Z, u_ro radix2 prec = u prec.
Proof. intros prec. unfold u_ro, u. rewrite bpow_plus, pow2_1. field. Qed.

(* The constant of the two statements, as the generator prints it, is u / (1 + u). *)
Lemma rel_one_eq :
  forall prec : Z,
  1 / (1 + u prec) * u prec ^ 1 = u_ro radix2 prec / (1 + u_ro radix2 prec).
Proof.
intros prec. rewrite u_ro_eq.
assert (H : 0 < u prec) by apply bpow_gt_0.
field. lra.
Qed.

Theorem add_1_1_correct : add_1_1_spec.
Proof.
intros emin prec Hp a b Fa Fb s. unfold s, add_1_1. clear s. cbv zeta.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 1%Z; lia).
unfold fmt in Fa, Fb.
split. reflexivity.
rewrite rel_one_eq.
rewrite (round_plus_FLT_FLX emin prec (Znearest tie_even) a b Fa Fb).
apply relative_error_N_FLX'. exact Hp0.
Qed.

Theorem mul_1_1_correct : mul_1_1_spec.
Proof.
intros emin prec Hp a b Fa Fb p. unfold p, mul_1_1. clear p. cbv zeta.
assert (Hp0 : (0 < prec)%Z) by lia.
rewrite !Rplus_0_r.
split. reflexivity.
rewrite rel_one_eq.
destruct (relative_error_N_FLT'_ex radix2 emin prec Hp0 tie_even (a * b))
  as [eps [et [He [Ht [_ Hr]]]]].
rewrite Hr.
replace (a * b * (1 + eps) + et - a * b) with (a * b * eps + et) by ring.
apply Rle_trans with (1 := Rabs_triang _ _).
apply Rplus_le_compat.
- rewrite Rabs_mult, (Rmult_comm (Rabs (a * b))).
  apply Rmult_le_compat_r. apply Rabs_pos. exact He.
- unfold eta. lra.
Qed.
