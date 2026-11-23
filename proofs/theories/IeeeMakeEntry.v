(* The guarded constructors of two limbs in the IEEE model (rule R3; for the ball, the owner's
   decision of 2026-11-23, "one rule for every constructor"): ball_make_2_entry and
   interval_make_2_entry, the listings of ball_make_2 and of interval_make_2 on the limbs of
   the center, or of the bounds, each passed through guard (an addition of +0) first, because
   they are limbs of an Expansion<T, 2> that the program may have written.

   Proved by reduction to the theorems of their cores (ball_make_2_correct of IeeeMake.v,
   interval_make_2_correct of IeeeIntervalExact.v). Each listing is its core's on the guarded
   limbs, by conversion: the description writes the core's listing out, so that the C++
   printer puts the fix-up behind a branch as it does for the core, and the two are the same
   term once the definitions of the guarded limbs are substituted. A guarded canonical pair is
   canonical and stands for the same extended real number (guard_canonical_2 of
   IeeeBvNegMake.v); each guarded limb is finite exactly when the limb is (guard_finite), of the
   same real value (guard_val), and a NaN exactly when the limb is (guard_nan). So:

     ball_make_2_entry(c, r)        the statement of ball_make_2 with the center of a finite
                                    ball of the values of the limbs given, val cw0 = val c0 and
                                    val cw1 = val c1, where ball_make_2 returns the limbs
                                    themselves, cw0 = c0 and cw1 = c1: a zero limb comes out +0
                                    (the generator prints the center so for every constructor
                                    whose center the program supplies, as for ball_make_1).
     interval_make_2_entry(lo, hi)  the statement of interval_make_2, word for word: it is
                                    about extended real values already.

   No statement of an existing theorem changes. The two executions of each (constant
   evaluation, where the guard returns its operand) are in IeeeTwoExecutions.v. The
   statements are in proofs/gen/IeeeStatements.v. *)
From Stdlib Require Import Reals ZArith Bool.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import IeeeStatements.
From Kairn Require Import IeeeVocabulary IeeeOps IeeeMake IeeeIntervalExact IeeeBvNegMake.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Open Scope R_scope.

Theorem ball_make_2_entry_correct : ball_make_2_entry_spec.
Proof.
intros prec emax Hp He nan_plus nan_abs nan_const c0 c1 r C.
replace (IeeeModel.ball_make_2_entry prec emax nan_plus nan_abs nan_const c0 c1 r)
  with (IeeeModel.ball_make_2 prec emax nan_plus nan_abs nan_const
          (IeeeOperations.guard prec emax nan_plus c0) (IeeeOperations.guard prec emax nan_plus c1) r)
  by (unfold IeeeModel.ball_make_2_entry, IeeeModel.ball_make_2; reflexivity).
destruct (guard_canonical_2 prec emax nan_plus c0 c1 C) as [Cg _].
generalize (ball_make_2_correct prec emax Hp He nan_plus nan_abs nan_const
              (IeeeOperations.guard prec emax nan_plus c0) (IeeeOperations.guard prec emax nan_plus c1) r Cg).
destruct (IeeeModel.ball_make_2 prec emax nan_plus nan_abs nan_const
            (IeeeOperations.guard prec emax nan_plus c0) (IeeeOperations.guard prec emax nan_plus c1) r)
  as [[cw0 cw1] rw].
intros [B [E [F W]]].
split; [exact B|split; [exact E|split]].
- (* the ball given: the center of the values of the limbs given *)
  intros Fr Pr Fc.
  assert (Fg : finite (IeeeOperations.guard prec emax nan_plus c0))
    by (unfold finite; rewrite (guard_finite prec emax nan_plus); exact Fc).
  destruct (F Fr Pr Fg) as [Bf [E0 [E1 Er]]].
  split; [exact Bf|]. rewrite E0, E1.
  split; [apply (guard_val prec emax nan_plus)|split; [apply (guard_val prec emax nan_plus)|exact Er]].
- (* the whole line: a guarded center is finite exactly when the center is *)
  intros H. apply W. destruct H as [H|[H|[Fr [Pr Nc]]]].
  + left. exact H.
  + right. left. exact H.
  + right. right. split; [exact Fr|split; [exact Pr|]].
    unfold finite. rewrite (guard_finite prec emax nan_plus). exact Nc.
Qed.

Theorem interval_make_2_entry_correct : interval_make_2_entry_spec.
Proof.
intros prec emax Hp He nan_plus nan_opp lo0 lo1 hi0 hi1 Cl Ch.
replace (IeeeModel.interval_make_2_entry prec emax nan_plus nan_opp lo0 lo1 hi0 hi1)
  with (IeeeModel.interval_make_2 prec emax nan_opp
          (IeeeOperations.guard prec emax nan_plus lo0) (IeeeOperations.guard prec emax nan_plus lo1)
          (IeeeOperations.guard prec emax nan_plus hi0) (IeeeOperations.guard prec emax nan_plus hi1))
  by (unfold IeeeModel.interval_make_2_entry, IeeeModel.interval_make_2; reflexivity).
destruct (guard_canonical_2 prec emax nan_plus lo0 lo1 Cl) as [Cl' Xl].
destruct (guard_canonical_2 prec emax nan_plus hi0 hi1 Ch) as [Ch' Xh].
generalize (interval_make_2_correct prec emax Hp He nan_opp
              (IeeeOperations.guard prec emax nan_plus lo0) (IeeeOperations.guard prec emax nan_plus lo1)
              (IeeeOperations.guard prec emax nan_plus hi0) (IeeeOperations.guard prec emax nan_plus hi1)
              Cl' Ch').
destruct (IeeeModel.interval_make_2 prec emax nan_opp
            (IeeeOperations.guard prec emax nan_plus lo0) (IeeeOperations.guard prec emax nan_plus lo1)
            (IeeeOperations.guard prec emax nan_plus hi0) (IeeeOperations.guard prec emax nan_plus hi1))
  as [[[zl0 zl1] zu0] zu1].
(* The statement of interval_make_2 on the guarded pairs is about their extended values, which
   are those of the pairs given; a guarded leading limb is a NaN exactly when it was. *)
rewrite Xl, Xh. intros [I [N [W E]]].
split; [exact I|split; [exact N|split; [|exact E]]].
intros H. apply W. unfold nan. rewrite !(guard_nan prec emax nan_plus). exact H.
Qed.
