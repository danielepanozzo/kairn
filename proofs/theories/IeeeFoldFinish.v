(* The finish of a fold in the IEEE model: the generated statements of fold_finish_1 and
   fold_finish_2 (proofs/gen/IeeeStatements.v).

   A fold returns its final state through a finish, which tests the leading limb:
       a = abs (s0);  flag = lt (a, inf);  r = select (flag, s, nan).
   lt (abs z, inf) is true exactly when z is finite (lt_abs_pinf, IeeeOps.v): the
   absolute value of a NaN is a NaN, which no comparison accepts, and that of either
   infinity is +infinity, which is not below itself. So the flag is true exactly when
   the leading limb of the state is finite; the result is then the state, limb for limb;
   and otherwise every limb of the result is the NaN that `const nan` denotes. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeOps.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.

Theorem fold_finish_1_correct : fold_finish_1_spec.
Proof.
intros prec emax Hp He nan_abs nan_const s.
unfold IeeeModel.fold_finish_1. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs s).
unfold finite, nan.
destruct (is_finite prec emax s).
- split. tauto. split. reflexivity. discriminate.
- split. split; discriminate. split. discriminate.
  intros _. exact (proj2_sig nan_const).
Qed.

Theorem fold_finish_2_correct : fold_finish_2_spec.
Proof.
intros prec emax Hp He nan_abs nan_const s0 s1.
unfold IeeeModel.fold_finish_2. cbv beta iota zeta.
rewrite (lt_abs_pinf prec emax nan_abs s0).
unfold finite, nan.
destruct (is_finite prec emax s0).
- split. tauto. split. intros _. split; reflexivity. discriminate.
- split. split; discriminate. split. discriminate.
  intros _. split; exact (proj2_sig nan_const).
Qed.
