(* Scaling a ball by a power of two, in the IEEE model: ball_mul_pow2_1_full and
   ball_mul_pow2_2_full (docs/developer/design/milestone2.md, "Scaling a ball by a power
   of two"), against the statements of proofs/gen/IeeeStatements.v.

   The cores (proofs/gen/IeeeModel.v), with c = 2^n a finite number of the format and
   N = eta / (2 u) the smallest normal number:

       ball_mul_pow2_1(cx, rx, c) -> (cz, rz)
         cz = prod(cx, c)        rr = prod(rx, c)
         ec = N < |cz| or cx = 0                      the center is exact
         er = N < rr or rx = 0                        the radius is exact
         rz = rr if ec and er, else succ(succ(rr))

   ball_mul_pow2_2 scales the two limbs of the center as mul_pow2_2 does and tests the
   limb that is rounded in the smallest binade. A full kernel is its core followed by the
   fix-up of the special states of a ball, the same as for ball_scale_k_full (IeeeBall.v).

   What is proved, for a canonical ball operand (a finite ball, the whole line or the empty
   set) and a finite c that is a power of two, from precision 2:

     B1   the result is a canonical ball;
     B2   it is empty exactly when the operand is;
     B3   if it is a finite ball, the operand is one and every x c with x in the operand
          is in it;
     E    if it is a finite ball and each scaled limb of the center and the scaled radius
          is zero or above N in magnitude, every member of the result is c times a
          member of the operand: the result is the exact image of the ball;
     B4   it is a finite ball when the operand is one and (|cx| + rx) c <= 2^(emax - 2);
     C    containment in every case, the whole line included.

   Why. The radius is computed from the radius of the operand by an opaque product and
   steps to the next number, and c is positive: every value of that computation is
   nonnegative, +infinity or a NaN (prod_nonneg, succ_nonneg of IeeeOps.v), so the test
   lt (rz, inf) of the fix-up means "finite", and a finite radius means that the scaled
   radius and the radius of the operand are finite (radius_pow2). A finite center means
   finite scaled limbs. With every value finite, each operation of the IEEE model returns
   what the same operation of the real model returns, the comparisons included, so a
   finite result is the result of the real model on the values of the operands
   (ball_mul_pow2_k_core), and the theorems of BallPow2.v give B3 and E. The corners: the
   whole line has radius +infinity, which the product by c > 0 and the steps keep, so the
   result is the whole line; an overflow of the scaled center or radius gives the whole
   line too.

   B4. With B = 2^(emax - 2): the scaled center is one rounding of a number of magnitude
   at most B (for two limbs, the threshold of mul_pow2_2, IeeeFinite.v), the scaled radius
   is at most B, and two steps above a number of the format that is at most B are at most
   3 B, a number of the format below 2^emax = 4 B from precision 2 on (radius_pow2_fin).
   In the smallest format, prec = 2, the numbers from B on are B, 3/2 B, 2 B, 3 B: two
   steps from B arrive at 2 B.

   The template of the fix-up (ball_template_k) is used with the conjunction of
   containment and E as the property of a finite result (full_1_pow2, full_2_pow2: the
   lemmas full_k_scale of IeeeBallCores.v for any property of the real-model result). *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Normalized Program IeeeBridge IeeeEFT IeeeSub
  IeeeVocabulary IeeeOps IeeeFinite IeeeBall IeeeBallCores IeeeBallFinite.
From Kairn Require BallPow2 IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

Section IeeeBallPow2.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation inrange := (inrange emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation fixup_1 := (IeeeBall.ball_fixup_1 prec emax nan_abs).
Notation fixup_2 := (IeeeBall.ball_fixup_2 prec emax nan_abs).
(* The constant of the listings in the IEEE model, and its value: the smallest normal
   number. *)
Notation Nc := (IeeeModel.up_ball_mul_pow2_1_0 prec emax).
Notation Nr := (bpow radix2 (emin + prec - 1)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The constant *)

Lemma const_N : fin Nc /\ b2r Nc = Nr.
Proof.
unfold IeeeModel.up_ball_mul_pow2_1_0.
rewrite (BallPow2.up_ball_mul_pow2_1_0_eq emin prec).
apply (const_of_spec prec emax).
- apply generic_format_bpow. unfold FLT_exp. lia.
- rewrite Rabs_pos_eq by apply bpow_ge_0. apply bpow_lt. lia.
Qed.

(* A positive power of two. *)
Lemma pow2_nonneg : forall c : float, (exists n : Z, b2r c = bpow radix2 n) -> 0 <= b2r c.
Proof. intros c [n E]. rewrite E. apply bpow_ge_0. Qed.

Lemma prod_val :
  forall x y : float, fin x -> fin y -> fin (prod x y) ->
  b2r (prod x y) = rnd (b2r x * b2r y + 0).
Proof.
intros x y Fx Fy F. unfold IeeeOperations.prod in *.
change 0 with (b2r pzero).
now apply (fma_spec prec emax nan_fma x y pzero Fx Fy eq_refl).
Qed.

(** * The radius *)

(* The radius of both cores, for a test ec of the center: it is nonnegative, +infinity or
   a NaN, and when it is finite the radius of the operand and its scaling are finite, the
   test of the radius is that of the real model, and so is the radius. *)
Lemma radius_pow2 :
  forall (rx c : float) (ec : bool),
  nonneg_ext rx -> fin c -> 0 <= b2r c ->
  let rr := prod rx c in
  let er := orb (flt Nc rr) (feq rx pzero) in
  let rz := if andb ec er then rr else fsucc (fsucc rr) in
  nonneg_ext rz /\
  (fin rz ->
   fin rx /\ fin rr /\ b2r rr = rnd (b2r rx * b2r c + 0) /\
   b2r rz = if andb ec (orb (Rlt_bool Nr (b2r rr)) (Req_bool (b2r rx) 0)) then b2r rr
            else Ulp.succ radix2 fexp (Ulp.succ radix2 fexp (b2r rr))).
Proof.
intros rx c ec Hrx Fc Pc rr er rz.
assert (Hc : nonneg_ext c) by (apply (nonneg_ext_finite prec emax); assumption).
destruct (prod_nonneg prec emax nan_fma rx c Hrx Hc) as [Hrr Frr]. fold rr in Hrr, Frr.
destruct (succ_nonneg prec emax rr Hrr) as [Hs1 Fs1].
destruct (succ_nonneg prec emax (fsucc rr) Hs1) as [Hs2 Fs2].
destruct const_N as [FN EN].
assert (K : fin rr ->
            fin rx /\ b2r rr = rnd (b2r rx * b2r c + 0) /\
            er = orb (Rlt_bool Nr (b2r rr)) (Req_bool (b2r rx) 0)).
{ intros F. destruct (Frr F) as [Frx [_ E]]. split; [exact Frx|split; [exact E|]].
  unfold er. rewrite (lt_finite prec emax Nc rr FN F), EN.
  rewrite (eq_finite prec emax rx pzero Frx eq_refl). reflexivity. }
split.
- unfold rz. destruct (andb ec er); assumption.
- intros Frz.
  assert (F : fin rr).
  { unfold rz in Frz. destruct (andb ec er); trivial.
    destruct (Fs2 Frz) as [F1 _]. exact (proj1 (Fs1 F1)). }
  destruct (K F) as [Frx [E Eer]].
  split; [exact Frx|split; [exact F|split; [exact E|]]].
  rewrite <- Eer. unfold rz in *. destruct (andb ec er); trivial.
  destruct (Fs2 Frz) as [F1 E2]. destruct (Fs1 F1) as [_ E1]. now rewrite E2, E1.
Qed.

(* The radius is finite when the scaled radius of the operand is at most 2^(emax - 2):
   two steps above a number of the format that is at most a quarter of 2^emax stay
   below 2^emax. *)
Lemma radius_pow2_fin :
  (2 <= prec)%Z ->
  forall (rx c : float) (ex : bool), fin rx -> fin c ->
  0 <= b2r rx * b2r c <= bpow radix2 (emax - 2) ->
  fin (if ex then prod rx c else fsucc (fsucc (prod rx c))).
Proof.
intros Hp rx c ex Frx Fc [M0 M1].
generalize (bpow_gt_0 radix2 (emax - 2)). intros Q0.
assert (T4 : bpow radix2 emax = 4 * bpow radix2 (emax - 2)).
{ change 4 with (bpow radix2 2). rewrite <- bpow_plus. f_equal. lia. }
assert (T2 : bpow radix2 (emax - 1) = 2 * bpow radix2 (emax - 2)).
{ change 2 with (bpow radix2 1). rewrite <- bpow_plus. f_equal. lia. }
assert (FQ : format (bpow radix2 (emax - 2))) by (apply generic_format_bpow; unfold FLT_exp; lia).
assert (FH : format (bpow radix2 (emax - 1))) by (apply generic_format_bpow; unfold FLT_exp; lia).
assert (F3 : format (3 * bpow radix2 (emax - 2))).
{ apply generic_format_FLT. exists (Float radix2 3 (emax - 2)).
  - reflexivity.
  - apply Z.lt_le_trans with (2 := Zpower_le radix2 2 prec Hp). reflexivity.
  - change (emin <= emax - 2)%Z. lia. }
assert (R0 : 0 <= rnd (b2r rx * b2r c + 0)).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. lra. }
assert (R1 : rnd (b2r rx * b2r c + 0) <= bpow radix2 (emax - 2)).
{ apply round_le_generic; auto with typeclass_instances. lra. }
assert (Ir : inrange (rnd (b2r rx * b2r c + 0))).
{ unfold IeeeBridge.inrange. rewrite Rabs_pos_eq by exact R0. lra. }
destruct (prod_fin prec emax nan_fma rx c Frx Fc Ir) as [Frr Err].
destruct ex; [exact Frr|].
assert (S1 : Ulp.succ radix2 fexp (b2r (prod rx c)) <= bpow radix2 (emax - 1)).
{ apply succ_le_lt; auto with typeclass_instances.
  - apply (b2r_format prec emax).
  - rewrite Err. lra. }
destruct (succ_finite prec emax (prod rx c) Frr) as [[F1 [Es1 _]]|[_ L]]; [|exfalso; lra].
assert (S2 : Ulp.succ radix2 fexp (b2r (fsucc (prod rx c))) <= 3 * bpow radix2 (emax - 2)).
{ apply succ_le_lt; auto with typeclass_instances.
  - apply (b2r_format prec emax).
  - rewrite Es1. lra. }
destruct (succ_finite prec emax (fsucc (prod rx c)) F1) as [[F2 _]|[_ L]]; [exact F2|exfalso; lra].
Qed.

(** * The cores *)

Notation ball_mul_pow2_1 := (IeeeModel.ball_mul_pow2_1 prec emax nan_abs nan_fma).
Notation ball_mul_pow2_2 :=
  (IeeeModel.ball_mul_pow2_2 prec emax nan_plus nan_minus nan_abs nan_fma).

(* A center of one limb: the radius is nonnegative, +infinity or a NaN; a finite center
   and a finite radius are those of the real model, and the radius of the operand is
   finite. *)
Lemma ball_mul_pow2_1_core :
  forall cx rx c : float, fin cx -> nonneg_ext rx -> fin c -> 0 <= b2r c ->
  let '(cz, rz) := ball_mul_pow2_1 cx rx c in
  nonneg_ext rz /\
  (fin cz -> fin rz ->
   fin rx /\ fin c /\
   (b2r cz, b2r rz) = Model.ball_mul_pow2_1 emin prec tie_even (b2r cx) (b2r rx) (b2r c)).
Proof.
intros cx rx c Fx Hrx Fc Pc.
unfold IeeeModel.ball_mul_pow2_1, Model.ball_mul_pow2_1. cbv beta iota zeta.
set (ec := orb (flt Nc (fabs (prod cx c))) (feq cx pzero)).
generalize (radius_pow2 rx c ec Hrx Fc Pc). cbv zeta. intros [Hrz Krz].
split. exact Hrz.
intros Fz Frz. destruct (Krz Frz) as [Frx [Frr [Err Erz]]].
split. exact Frx. split. exact Fc.
destruct const_N as [FN EN].
assert (Ec : b2r (prod cx c) = rnd (b2r cx * b2r c + 0)) by now apply prod_val.
assert (Eec : ec = orb (Rlt_bool Nr (Rabs (b2r (prod cx c)))) (Req_bool (b2r cx) 0)).
{ unfold ec. rewrite (lt_finite prec emax Nc (fabs (prod cx c)) FN).
  - rewrite EN, (abs_val prec emax nan_abs), (eq_finite prec emax cx pzero Fx eq_refl).
    reflexivity.
  - now rewrite (abs_finite prec emax nan_abs). }
rewrite Erz, Eec, Err, Ec, (BallPow2.up_ball_mul_pow2_1_0_eq emin prec). reflexivity.
Qed.

(* A center of two limbs: the same, and the second limb of the center is finite. The
   center is that of mul_pow2_2 (IeeeSub.v). *)
Lemma ball_mul_pow2_2_core :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx c : float,
  fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) -> nonneg_ext rx ->
  fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  let '(cz0, cz1, rz) := ball_mul_pow2_2 cx0 cx1 rx c in
  nonneg_ext rz /\
  (fin cz0 -> fin rz ->
   fin rx /\ fin c /\ fin cz1 /\
   (b2r cz0, b2r cz1, b2r rz)
   = Model.ball_mul_pow2_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx) (b2r c)).
Proof.
intros Hp cx0 cx1 rx c F0 F1 Nx Hrx Fc Pc.
generalize (pow2_nonneg c Pc). intros Pc0.
unfold IeeeModel.ball_mul_pow2_2, Model.ball_mul_pow2_2.
generalize (mul_pow2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp cx0 cx1 c
              F0 F1 Fc Nx Pc).
unfold IeeeModel.mul_pow2_2, Model.mul_pow2_2. cbv zeta.
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (prod cx0 c) (prod cx1 c))
  as [cz0 cz1] eqn:EF.
destruct (Model.fast_two_sum emin prec tie_even (rnd (b2r cx0 * b2r c + 0))
            (rnd (b2r cx1 * b2r c + 0))) as [z0 z1].
cbv beta iota zeta. intros V.
assert (E0 : cz0 = add (prod cx0 c) (prod cx1 c)).
{ unfold IeeeModel.fast_two_sum in EF. cbv zeta in EF. now inversion EF. }
set (ec := orb (flt Nc (fabs (if feq cx1 pzero then prod cx0 c else prod cx1 c)))
               (feq cx0 pzero)).
generalize (radius_pow2 rx c ec Hrx Fc Pc0). cbv zeta. intros [Hrz Krz].
split. exact Hrz.
intros Fz Frz. destruct (Krz Frz) as [Frx [Frr [Err Erz]]].
destruct (V Fz) as [Fz1 Ez].
split. exact Frx. split. exact Fc. split. exact Fz1.
destruct const_N as [FN EN].
assert (Fhl : fin (prod cx0 c) /\ fin (prod cx1 c)).
{ apply (add_finite_inv prec emax nan_plus). now rewrite <- E0. }
destruct Fhl as [Fh Fl].
assert (Eh : b2r (prod cx0 c) = rnd (b2r cx0 * b2r c + 0)) by now apply prod_val.
assert (El : b2r (prod cx1 c) = rnd (b2r cx1 * b2r c + 0)) by now apply prod_val.
assert (Eec : ec = orb (Rlt_bool Nr (Rabs (if Req_bool (b2r cx1) 0
                                           then rnd (b2r cx0 * b2r c + 0)
                                           else rnd (b2r cx1 * b2r c + 0))))
                       (Req_bool (b2r cx0) 0)).
{ unfold ec.
  rewrite (eq_finite prec emax cx1 pzero F1 eq_refl), (eq_finite prec emax cx0 pzero F0 eq_refl).
  change (b2r pzero) with 0.
  destruct (Req_bool (b2r cx1) 0).
  - rewrite (lt_finite prec emax Nc (fabs (prod cx0 c)) FN).
    + now rewrite EN, (abs_val prec emax nan_abs), Eh.
    + now rewrite (abs_finite prec emax nan_abs).
  - rewrite (lt_finite prec emax Nc (fabs (prod cx1 c)) FN).
    + now rewrite EN, (abs_val prec emax nan_abs), El.
    + now rewrite (abs_finite prec emax nan_abs). }
injection Ez as Ez0 Ez1.
rewrite Erz, Eec, Err, Ez0, Ez1, (BallPow2.up_ball_mul_pow2_1_0_eq emin prec). reflexivity.
Qed.

(** * The cores: finite under the condition *)

Lemma ball_mul_pow2_1_finite :
  (2 <= prec)%Z ->
  forall cx rx c : float, fin cx -> fin rx -> fin c -> 0 <= b2r rx -> 0 <= b2r c ->
  (Rabs (b2r cx) + b2r rx) * b2r c <= bpow radix2 (emax - 2) ->
  let '(cz, rz) := ball_mul_pow2_1 cx rx c in fin cz /\ fin rz.
Proof.
intros Hp cx rx c Fx Frx Fc Prx Pc Hc.
unfold IeeeModel.ball_mul_pow2_1. cbv beta iota zeta.
generalize (Rabs_pos (b2r cx)). intros C0.
assert (M0 : 0 <= Rabs (b2r cx) * b2r c) by now apply Rmult_le_pos.
assert (M1 : 0 <= b2r rx * b2r c) by now apply Rmult_le_pos.
assert (Ic : inrange (rnd (b2r cx * b2r c + 0))).
{ apply (le_bpow_inrange emax) with (emax - 2)%Z. lia.
  apply (RN_abs_le_bpow emin prec).
  rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (b2r c)) by exact Pc. lra. }
destruct (prod_fin prec emax nan_fma cx c Fx Fc Ic) as [Fz _].
split. exact Fz.
apply radius_pow2_fin; trivial. lra.
Qed.

Lemma ball_mul_pow2_2_finite :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx c : float,
  fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) ->
  fin rx -> fin c -> 0 <= b2r rx -> 0 <= b2r c ->
  (Rabs (b2r cx0 + b2r cx1) + b2r rx) * b2r c <= bpow radix2 (emax - 2) ->
  let '(cz0, cz1, rz) := ball_mul_pow2_2 cx0 cx1 rx c in fin cz0 /\ fin rz.
Proof.
intros Hp cx0 cx1 rx c F0 F1 Nx Frx Fc Prx Pc Hc.
generalize (Rabs_pos (b2r cx0 + b2r cx1)). intros C0.
assert (M0 : 0 <= Rabs (b2r cx0 + b2r cx1) * b2r c) by now apply Rmult_le_pos.
assert (M1 : 0 <= b2r rx * b2r c) by now apply Rmult_le_pos.
assert (Hs : Rabs ((b2r cx0 + b2r cx1) * b2r c) <= bpow radix2 (emax - 1)).
{ rewrite Rabs_mult, (Rabs_pos_eq (b2r c)) by exact Pc.
  apply Rle_trans with (bpow radix2 (emax - 2)). lra. apply bpow_le. lia. }
unfold IeeeModel.ball_mul_pow2_2.
generalize (mul_pow2_2_ieee_finite_any prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
              nan_opp nan_fma Hp cx0 cx1 c F0 F1 Fc Nx Hs).
unfold IeeeModel.mul_pow2_2. cbv zeta.
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (prod cx0 c) (prod cx1 c))
  as [cz0 cz1].
cbv beta iota zeta. intros [_ [Fz0 _]].
split. exact Fz0.
apply radius_pow2_fin; trivial. lra.
Qed.

(** * From a core to its full kernel *)

(* The lemmas full_k_scale of IeeeBallCores.v, for any property P of the result of the
   real model: B1, B2, and a finite result has a finite operand and the property. *)
Lemma full_1_pow2 :
  forall (core : float * float) (real : R * R) (cx rx a : float) (P : R -> R -> Prop),
  ball_1 cx rx ->
  (fin cx ->
   let '(cz, rz) := core in
   nonneg_ext rz /\ (fin cz -> fin rz -> fin rx /\ fin a /\ (b2r cz, b2r rz) = real)) ->
  (0 <= b2r rx -> let '(z, r) := real in P z r) ->
  let '(cw, rw) := (let '(cz, rz) := core in fixup_1 cz rz rx) in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cw rw -> (ball_finite_1 cx rx /\ fin a) /\ P (b2r cw) (b2r rw)).
Proof.
intros core real cx rx a P Bx Hcore Hreal.
generalize (ball_1_radius prec emax _ _ Bx). intros Hrx.
assert (K : ~ ball_empty_1 cx rx ->
  let '(cz, rz) := core in
  fin cz ->
  nonneg_ext rz /\ (fin rz -> (ball_finite_1 cx rx /\ fin a) /\ P (b2r cz) (b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. now apply (ball_1_empty prec emax). }
  specialize (Hcore (ball_1_center prec emax _ _ Bx Nrx)).
  destruct core as [cz rz]. destruct Hcore as [Hrz Kc]. intros Fz. split. exact Hrz.
  intros Frz. destruct (Kc Fz Frz) as [Frx [Fa E]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx)).
  rewrite <- E in Hreal. cbv beta iota in Hreal.
  split; [split; [now apply (ball_1_finite prec emax)|exact Fa]|exact Hreal]. }
revert K. destruct core as [cz rz]. intros K.
exact (ball_template_1 prec emax nan_abs cz rz rx _ _ (fun cw rw => P (b2r cw) (b2r rw))
         (q_empty_scale_1 prec emax _ _ Bx) K).
Qed.

Lemma full_2_pow2 :
  forall (core : float * float * float) (real : R * R * R) (cx0 cx1 rx a : float)
         (P : R -> R -> R -> Prop),
  ball_2 cx0 cx1 rx ->
  (fin cx0 -> fin cx1 -> normalized_2 emin prec (b2r cx0) (b2r cx1) ->
   let '(cz0, cz1, rz) := core in
   nonneg_ext rz /\
   (fin cz0 -> fin rz -> fin rx /\ fin a /\ fin cz1 /\ (b2r cz0, b2r cz1, b2r rz) = real)) ->
  (normalized_2 emin prec (b2r cx0) (b2r cx1) -> 0 <= b2r rx ->
   let '(z0, z1, r) := real in normalized_2 emin prec z0 z1 /\ P z0 z1 r) ->
  let '(cw0, cw1, rw) := (let '(cz0, cz1, rz) := core in fixup_2 cz0 cz1 rz rx) in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ fin a) /\ P (b2r cw0) (b2r cw1) (b2r rw)).
Proof.
intros core real cx0 cx1 rx a P Bx Hcore Hreal.
generalize (ball_2_radius prec emax _ _ _ Bx). intros Hrx.
assert (K : ~ ball_empty_2 cx0 cx1 rx ->
  let '(cz0, cz1, rz) := core in
  fin cz0 ->
  nonneg_ext rz /\
  (fin rz ->
   (ball_finite_2 cx0 cx1 rx /\ fin a) /\ fin cz1 /\
   normalized_2 emin prec (b2r cz0) (b2r cz1) /\ P (b2r cz0) (b2r cz1) (b2r rz))).
{ intros NE.
  assert (Nrx : is_nan prec emax rx = false).
  { destruct (is_nan prec emax rx) eqn:N; trivial. elim NE. now apply (ball_2_empty prec emax). }
  destruct (ball_2_center prec emax _ _ _ Bx Nrx) as [F0 [F1 Nx]].
  specialize (Hcore F0 F1 Nx). specialize (Hreal Nx).
  destruct core as [[cz0 cz1] rz]. destruct Hcore as [Hrz Kc]. intros Fz0. split. exact Hrz.
  intros Frz. destruct (Kc Fz0 Frz) as [Frx [Fa [Fz1 E]]].
  specialize (Hreal (nonneg_ext_fin prec emax rx Hrx Frx)).
  rewrite <- E in Hreal. cbv beta iota in Hreal. destruct Hreal as [Nz C].
  split; [split; [now apply (ball_2_finite prec emax)|exact Fa]
         |split; [exact Fz1|split; [exact Nz|exact C]]]. }
revert K. destruct core as [[cz0 cz1] rz]. intros K.
exact (ball_template_2 prec emax nan_abs cz0 cz1 rz rx _ _
         (fun cw0 cw1 rw => P (b2r cw0) (b2r cw1) (b2r rw))
         (q_empty_scale_2 prec emax _ _ _ Bx) K).
Qed.

(** * The full kernels: B1 to B3 and exactness *)

Notation ball_mul_pow2_1_full := (IeeeModel.ball_mul_pow2_1_full prec emax nan_abs nan_fma).
Notation ball_mul_pow2_2_full :=
  (IeeeModel.ball_mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma).

Lemma ball_mul_pow2_1_full_facts :
  (2 <= prec)%Z ->
  forall cx rx c : float, ball_1 cx rx -> fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  let '(cw, rw) := ball_mul_pow2_1_full cx rx c in
  ball_1 cw rw /\
  (ball_empty_1 cw rw <-> ball_empty_1 cx rx) /\
  (ball_finite_1 cw rw ->
   (ball_finite_1 cx rx /\ fin c) /\
   (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r c - b2r cw) <= b2r rw) /\
   ((b2r cx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx * b2r c)) /\
    (b2r rx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r rx * b2r c)) ->
    forall s_ : R, Rabs (s_ - b2r cw) <= b2r rw ->
    exists x : R, Rabs (x - b2r cx) <= b2r rx /\ s_ = x * b2r c)).
Proof.
intros Hp cx rx c Bx Fc Pc.
refine (full_1_pow2 (ball_mul_pow2_1 cx rx c)
          (Model.ball_mul_pow2_1 emin prec tie_even (b2r cx) (b2r rx) (b2r c)) cx rx c
          (fun z r =>
             (forall x : R, Rabs (x - b2r cx) <= b2r rx -> Rabs (x * b2r c - z) <= r) /\
             ((b2r cx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx * b2r c)) /\
              (b2r rx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r rx * b2r c)) ->
              forall s_ : R, Rabs (s_ - z) <= r ->
              exists x : R, Rabs (x - b2r cx) <= b2r rx /\ s_ = x * b2r c))
          Bx _ _).
- intros Fx.
  exact (ball_mul_pow2_1_core cx rx c Fx (ball_1_radius prec emax _ _ Bx) Fc (pow2_nonneg c Pc)).
- intros Px.
  generalize (BallPow2.ball_mul_pow2_1_correct emin prec Hp (b2r cx) (b2r rx) (b2r c)
                (b2r_format prec emax cx) (b2r_format prec emax rx) (b2r_format prec emax c)
                Px Pc).
  destruct (Model.ball_mul_pow2_1 emin prec tie_even (b2r cx) (b2r rx) (b2r c)) as [z r].
  intros [_ [_ K]]. exact K.
Qed.

Lemma ball_mul_pow2_2_full_facts :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx c : float,
  ball_2 cx0 cx1 rx -> fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  let '(cw0, cw1, rw) := ball_mul_pow2_2_full cx0 cx1 rx c in
  ball_2 cw0 cw1 rw /\
  (ball_empty_2 cw0 cw1 rw <-> ball_empty_2 cx0 cx1 rx) /\
  (ball_finite_2 cw0 cw1 rw ->
   (ball_finite_2 cx0 cx1 rx /\ fin c) /\
   (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
    Rabs (x * b2r c - (b2r cw0 + b2r cw1)) <= b2r rw) /\
   ((b2r cx0 * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx0 * b2r c)) /\
    (b2r cx1 * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx1 * b2r c)) /\
    (b2r rx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r rx * b2r c)) ->
    forall s_ : R, Rabs (s_ - (b2r cw0 + b2r cw1)) <= b2r rw ->
    exists x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx /\ s_ = x * b2r c)).
Proof.
intros Hp cx0 cx1 rx c Bx Fc Pc.
refine (full_2_pow2 (ball_mul_pow2_2 cx0 cx1 rx c)
          (Model.ball_mul_pow2_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx) (b2r c))
          cx0 cx1 rx c
          (fun z0 z1 r =>
             (forall x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx ->
              Rabs (x * b2r c - (z0 + z1)) <= r) /\
             ((b2r cx0 * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx0 * b2r c)) /\
              (b2r cx1 * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r cx1 * b2r c)) /\
              (b2r rx * b2r c = 0 \/ eta emin / (2 * u prec) < Rabs (b2r rx * b2r c)) ->
              forall s_ : R, Rabs (s_ - (z0 + z1)) <= r ->
              exists x : R, Rabs (x - (b2r cx0 + b2r cx1)) <= b2r rx /\ s_ = x * b2r c))
          Bx _ _).
- intros F0 F1 Nx.
  exact (ball_mul_pow2_2_core Hp cx0 cx1 rx c F0 F1 Nx (ball_2_radius prec emax _ _ _ Bx) Fc Pc).
- intros Nx Px.
  generalize (BallPow2.ball_mul_pow2_2_correct emin prec Hp (b2r cx0) (b2r cx1) (b2r rx) (b2r c)
                Nx (b2r_format prec emax rx) (b2r_format prec emax c) Px Pc).
  destruct (Model.ball_mul_pow2_2 emin prec tie_even (b2r cx0) (b2r cx1) (b2r rx) (b2r c))
    as [[z0 z1] r].
  intros [_ [Nz K]]. split; [exact Nz|exact K].
Qed.

(** * The full kernels: B4 *)

Lemma ball_mul_pow2_1_full_finite :
  (2 <= prec)%Z ->
  forall cx rx c : float, ball_finite_1 cx rx -> fin c -> 0 <= b2r c ->
  Rabs ((Rabs (b2r cx) + b2r rx) * b2r c) <= bpow radix2 (emax - 2) ->
  let '(cw, rw) := ball_mul_pow2_1_full cx rx c in ball_1 cw rw -> ball_finite_1 cw rw.
Proof.
intros Hp cx rx c [Fx [Frx Prx]] Fc Pc Hc. unfold val in Prx.
generalize (Rabs_pos (b2r cx)). intros C0.
rewrite Rabs_pos_eq in Hc by (apply Rmult_le_pos; lra).
exact (finite_ball_1 prec emax nan_abs (ball_mul_pow2_1 cx rx c) rx
         (finite_not_nan prec emax rx Frx)
         (ball_mul_pow2_1_finite Hp cx rx c Fx Frx Fc Prx Pc Hc)).
Qed.

Lemma ball_mul_pow2_2_full_finite :
  (2 <= prec)%Z ->
  forall cx0 cx1 rx c : float, ball_finite_2 cx0 cx1 rx -> fin c -> 0 <= b2r c ->
  Rabs ((Rabs (b2r cx0 + b2r cx1) + b2r rx) * b2r c) <= bpow radix2 (emax - 2) ->
  let '(cw0, cw1, rw) := ball_mul_pow2_2_full cx0 cx1 rx c in
  ball_2 cw0 cw1 rw -> ball_finite_2 cw0 cw1 rw.
Proof.
intros Hp cx0 cx1 rx c [F0 [F1 [Nx [Frx Prx]]]] Fc Pc Hc. unfold val in Prx.
generalize (Rabs_pos (b2r cx0 + b2r cx1)). intros C0.
rewrite Rabs_pos_eq in Hc by (apply Rmult_le_pos; lra).
exact (finite_ball_2 prec emax nan_abs (ball_mul_pow2_2 cx0 cx1 rx c) rx
         (finite_not_nan prec emax rx Frx)
         (ball_mul_pow2_2_finite Hp cx0 cx1 rx c F0 F1 Nx Frx Fc Prx Pc Hc)).
Qed.

End IeeeBallPow2.

(** * The statements of proofs/gen/IeeeStatements.v *)

Theorem ball_mul_pow2_1_full_correct : ball_mul_pow2_1_full_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma Hp2 cx rx c Bx Fc Pc.
generalize (ball_mul_pow2_1_full_facts prec emax nan_abs nan_fma Hp2 cx rx c Bx Fc Pc)
           (ball_mul_pow2_1_full_finite prec emax nan_abs nan_fma Hp2 cx rx c)
           (pow2_nonneg prec emax c Pc).
destruct (IeeeModel.ball_mul_pow2_1_full prec emax nan_abs nan_fma cx rx c) as [cw rw].
intros [B1 [B2 B3]] B4 Pc0.
split; [exact B1|split; [exact B2|split; [|split; [|split]]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] [C _]]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fw. exact (proj2 (proj2 (B3 Fw))).
- intros Fx Fa Hc. exact (B4 Fx Fa Pc0 Hc B1).
- intros Fa. apply (every_case_scale_1 prec emax (fun x : R => x * val c) _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] [C _]]. split; [exact Fx|exact C].
Qed.

Theorem ball_mul_pow2_2_full_correct : ball_mul_pow2_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp2 cx0 cx1 rx c Bx Fc Pc.
generalize (ball_mul_pow2_2_full_facts prec emax nan_plus nan_minus (fun x => nan_plus x x)
              nan_abs nan_fma Hp2 cx0 cx1 rx c Bx Fc Pc)
           (ball_mul_pow2_2_full_finite prec emax nan_plus nan_minus (fun x => nan_plus x x)
              nan_abs nan_fma Hp2 cx0 cx1 rx c)
           (pow2_nonneg prec emax c Pc).
destruct (IeeeModel.ball_mul_pow2_2_full prec emax nan_plus nan_minus nan_abs nan_fma
            cx0 cx1 rx c) as [[cw0 cw1] rw].
intros [B1 [B2 B3]] B4 Pc0.
split; [exact B1|split; [exact B2|split; [|split; [|split]]]].
- intros Fw. destruct (B3 Fw) as [[Fx Fa] [C _]]. split; [exact Fx|split; [exact Fa|exact C]].
- intros Fw. exact (proj2 (proj2 (B3 Fw))).
- intros Fx Fa Hc. exact (B4 Fx Fa Pc0 Hc B1).
- intros Fa. apply (every_case_scale_2 prec emax (fun x : R => x * val c) _ _ _ _ _ _ B1 B2).
  intros Fw. destruct (B3 Fw) as [[Fx _] [C _]]. split; [exact Fx|exact C].
Qed.
