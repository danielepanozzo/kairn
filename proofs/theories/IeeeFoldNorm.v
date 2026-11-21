(* The folds of maxima in the IEEE model: the finishes, the flag, and the two orders.

   The generator prints the IEEE model of norm_upper_1 and norm_upper_2
   (proofs/gen/IeeeFoldModel.v): the state is a number m, from +0, and a mask, from true;
   the step is the IEEE model of norm_step_k and the combination that of norm_combine,

       step (m, ok) x      =  (if m < |x| then |x| else m,  ok and (|x| = |x|))
       combine (m, ok) (n, okn)  =  (if m < n then n else m,  ok and okn),

   with |x0| for an element of two limbs; and F_seq xs, F_lanes W xs are the finish
   norm_finish_k on the final state of the two orders of Folds.v. This file proves the
   generated statements of the two finishes (proofs/gen/IeeeStatements.v),

       norm_finish_1_correct : norm_finish_1_spec
       norm_finish_2_correct : norm_finish_2_spec,

   and of the two folds in both orders (proofs/gen/IeeeFoldStatements.v), the lane order
   for every number of lanes,

       norm_upper_k_seq_ieee_correct : norm_upper_k_seq_ieee_spec
       norm_upper_k_lanes_ieee_correct : norm_upper_k_lanes_ieee_spec.

   What they say. For every list of elements (any numbers, infinities and NaN included,
   for one limb; canonical pairs for two), with (r, flag) the result:
   - if flag is true: every limb of every element is finite; r is finite; its value is
     the result of the real model on the values of the elements (the largest magnitude
     for one limb, the successor of the largest |x0| for two), which satisfies the bounds
     of the real-model statement (FoldNorm.v);
   - if flag is false: r is a NaN.

   How.
   - A comparison with a NaN is false, so the maximum by comparison keeps m when the
     element is a NaN, and the test |x| = |x| puts the NaN into the mask. An infinite
     element makes m infinite, and m stays so. The state therefore stays a magnitude
     (mag below: not a NaN, sign +: +0, a positive number or +infinity), and on
     magnitudes the comparison is the order of the real numbers with +infinity above
     them (key, key_lt), under which a magnitude is determined by its place (key_inj).
   - The sequential order is transferred to the real model by FoldTransfer.v, with
     "live" read on the states the loop can be in: a magnitude that is finite with a
     true mask. From such a state, a result of that kind shows a finite element and is
     the step of the real model on the values (step_1_live).
   - The lane order returns the state of the sequential order, bit for bit, on every
     list, NaN and infinities included: norm_upper_k_lanes_seq_ieee, by
     fold_lanes_aci_step of Folds.v on the magnitudes, where the combination is
     associative and commutative (it is neither on all states: with a NaN on the left
     the comparison keeps the NaN, with a NaN on the right it keeps the other operand;
     and it returns its first operand on the two zeros). The step is the combination
     with (|x|, true) for an element that is not a NaN and with (+0, false) for a NaN
     (img, step_1_cmb). So the statements of the lane order are those of the
     sequential order, in this model and in the real one (norm_upper_k_lanes_seq of
     FoldNorm.v).
   - The finish of two limbs steps the maximum up before the test: the successor of a
     magnitude is finite only if the magnitude is, and is then the successor of the
     real model (succ_nonneg of IeeeOps.v).

   What the statements do not say, and is proved here or true of the model.
   - The two orders return the same result and the same flag on every input
     (norm_upper_k_lanes_seq_ieee).
   - When the flag is true. For one limb, exactly when every element is finite
     (norm_upper_1_seq_ieee_flag): no array of finite numbers is refused. For two limbs,
     exactly when every leading limb is finite and the step up from the final state,
     the largest |x0|, is finite (norm_upper_2_seq_ieee_flag). So an array of finite
     elements can have the flag false: the step up from the largest finite number is
     +infinity (IeeeOperations.v, succ), and the bound one step above it is not a
     number of the format. That this is the only such case is not proved here.
   - The statements for two limbs assume canonical elements. The flag and the result
     depend on the leading limbs alone, which is how norm_upper_2_seq_ieee_flag is
     stated, for any pairs; the second limbs are not read. *)
From Stdlib Require Import Reals ZArith List Lia Lra Bool.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel FoldStatements.
From Kairn Require Import Format Folds FoldTransfer FoldNorm IeeeBridge IeeeVocabulary IeeeOps
  IeeeFoldFinish IeeeFolds.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
From Kairn.Gen Require Import IeeeFoldStatements.
Import ListNotations.
Open Scope R_scope.

(** * The finishes *)

Theorem norm_finish_1_correct : norm_finish_1_spec.
Proof.
intros prec emax Hp He nan_abs nan_const m ok.
unfold IeeeModel.norm_finish_1. cbv zeta.
match goal with
| |- context [IeeeModel.fold_finish_1 prec emax nan_abs nan_const ?t] =>
    generalize (fold_finish_1_correct prec emax Hp He nan_abs nan_const t);
    destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const t) as [r flag]
end.
intros [H1 [H2 H3]]. destruct ok.
- split.
  + split. intros E. split. reflexivity. now apply H1. intros [_ F]. now apply H1.
  + split. exact H2. exact H3.
- assert (N : ~ finite (IeeeOperations.cnan prec emax nan_const)).
  { unfold finite, IeeeOperations.cnan.
    rewrite (nan_not_finite prec emax _ (proj2_sig nan_const)). discriminate. }
  split.
  + split. intros E. elim N. now apply H1. intros [E _]. discriminate E.
  + split. intros E. elim N. now apply H1. exact H3.
Qed.

Theorem norm_finish_2_correct : norm_finish_2_spec.
Proof.
intros prec emax Hp He nan_abs nan_const m ok.
unfold IeeeModel.norm_finish_2. cbv zeta.
match goal with
| |- context [IeeeModel.fold_finish_1 prec emax nan_abs nan_const ?t] =>
    generalize (fold_finish_1_correct prec emax Hp He nan_abs nan_const t);
    destruct (IeeeModel.fold_finish_1 prec emax nan_abs nan_const t) as [r flag]
end.
intros [H1 [H2 H3]]. destruct ok.
- split.
  + split. intros E. split. reflexivity. now apply H1. intros [_ F]. now apply H1.
  + split. exact H2. exact H3.
- assert (N : ~ finite (IeeeOperations.cnan prec emax nan_const)).
  { unfold finite, IeeeOperations.cnan.
    rewrite (nan_not_finite prec emax _ (proj2_sig nan_const)). discriminate. }
  split.
  + split. intros E. elim N. now apply H1. intros [E _]. discriminate E.
  + split. intros E. elim N. now apply H1. exact H3.
Qed.

Section IeeeFoldNorm.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_abs : float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (ieee_emin prec emax).
Notation fexp := (FLT_exp emin prec).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation top := (bpow radix2 emax).

(* The generated models (proofs/gen/IeeeFoldModel.v), with the NaN choices of this
   section: notations, so that every statement below is about the generated
   definitions. *)
Notation step_1 := (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
Notation combine_1 := (IeeeFoldModel.norm_upper_1_combine prec emax).
Notation seq_1_ieee := (IeeeFoldModel.norm_upper_1_seq prec emax nan_abs nan_const).
Notation lanes_1_ieee := (IeeeFoldModel.norm_upper_1_lanes prec emax nan_abs nan_const).
Notation step_2 := (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
Notation combine_2 := (IeeeFoldModel.norm_upper_2_combine prec emax).
Notation seq_2_ieee := (IeeeFoldModel.norm_upper_2_seq prec emax nan_abs nan_const).
Notation lanes_2_ieee := (IeeeFoldModel.norm_upper_2_lanes prec emax nan_abs nan_const).
Notation zero_state := (pzero, true).

(** * Magnitudes *)

(* What the first part of the state is: not a NaN, with the sign +. So +0, a positive
   number, or +infinity. *)
Definition mag (m : float) : Prop :=
  is_nan prec emax m = false /\ Bsign prec emax m = false.

Lemma mag_pzero : mag pzero.
Proof. split; reflexivity. Qed.

Lemma mag_cases : forall m : float, mag m -> finite m \/ m = pinf.
Proof.
intros [s|s|s pl H|s mm e H] [N S]; cbn in N, S.
- left. reflexivity.
- right. rewrite S. reflexivity.
- discriminate N.
- left. reflexivity.
Qed.

Lemma mag_nonneg : forall m : float, mag m -> finite m -> 0 <= val m.
Proof.
intros [s|s|s pl H|s mm e H] [N S] F; cbn in N, S; try discriminate F.
- apply Rle_refl.
- rewrite S. apply Rlt_le. exact (finite_sign_pos prec emax mm e H).
Qed.

Lemma mag_nonneg_ext : forall m : float, mag m -> nonneg_ext m.
Proof.
intros m M. destruct (mag_cases m M) as [F|E].
- right. right. split. exact F. now apply mag_nonneg.
- right. left. exact E.
Qed.

(* The absolute value of a number that is not a NaN is a magnitude; that of a NaN is a
   NaN. *)
Lemma abs_mag : forall x : float, is_nan prec emax x = false -> mag (fabs x).
Proof. intros [s|s|s pl H|s mm e H] N; try discriminate N; split; reflexivity. Qed.

Lemma abs_nan : forall x : float, is_nan prec emax x = true -> is_nan prec emax (fabs x) = true.
Proof.
intros [s|s|s pl H|s mm e H] N; try discriminate N.
unfold IeeeOperations.abs, Babs. apply is_nan_build_nan.
Qed.

(* A comparison with a NaN on the right is false. *)
Lemma lt_nan_r : forall m n : float, is_nan prec emax n = true -> flt m n = false.
Proof.
intros m [s|s|s pl H|s mm e H] N; try discriminate N.
destruct m; reflexivity.
Qed.

(* The place of a magnitude in the order: its value, and 2^emax, which is above every
   value of the format, for +infinity. *)
Definition key (m : float) : R := if is_finite prec emax m then val m else top.

Lemma key_finite : forall m : float, finite m -> key m = val m.
Proof. intros m F. unfold key. now rewrite F. Qed.

Lemma key_pinf : key pinf = top.
Proof. reflexivity. Qed.

Lemma val_lt_top : forall m : float, val m < top.
Proof.
intros m. apply Rle_lt_trans with (1 := Rle_abs _). apply abs_B2R_lt_emax.
Qed.

Lemma key_le_top : forall m : float, key m <= top.
Proof.
intros m. unfold key. destruct (is_finite prec emax m).
- apply Rlt_le. apply val_lt_top.
- apply Rle_refl.
Qed.

Lemma key_nonneg : forall m : float, mag m -> 0 <= key m.
Proof.
intros m M. destruct (mag_cases m M) as [F|E].
- rewrite (key_finite m F). now apply mag_nonneg.
- rewrite E, key_pinf. apply bpow_ge_0.
Qed.

(* A magnitude is finite exactly when its place is below 2^emax. *)
Lemma key_lt_top : forall m : float, mag m -> (finite m <-> key m < top).
Proof.
intros m M. destruct (mag_cases m M) as [F|E].
- rewrite (key_finite m F). split. intros _. apply val_lt_top. intros _. exact F.
- rewrite E, key_pinf. split. discriminate. intros H. elim (Rlt_irrefl _ H).
Qed.

(* On magnitudes the comparison of the format is the order of the places. *)
Lemma key_lt : forall m n : float, mag m -> mag n -> flt m n = Rlt_bool (key m) (key n).
Proof.
intros m n Mm Mn.
destruct (mag_cases m Mm) as [Fm|Em]; destruct (mag_cases n Mn) as [Fn|En].
- rewrite (key_finite m Fm), (key_finite n Fn). now apply lt_finite.
- rewrite En, key_pinf, (key_finite m Fm).
  rewrite (lt_pinf_finite prec emax m Fm). symmetry. apply Rlt_bool_true. apply val_lt_top.
- rewrite Em, key_pinf. symmetry. rewrite Rlt_bool_false by apply key_le_top.
  destruct n as [s|s|s pl H|s mm e H]; try discriminate Fn; reflexivity.
- rewrite Em, En. symmetry. rewrite Rlt_bool_false by apply Rle_refl. reflexivity.
Qed.

(* A magnitude is determined by its place. *)
Lemma key_inj : forall m n : float, mag m -> mag n -> key m = key n -> m = n.
Proof.
intros m n Mm Mn E.
destruct (mag_cases m Mm) as [Fm|Em]; destruct (mag_cases n Mn) as [Fn|En].
- rewrite (key_finite m Fm), (key_finite n Fn) in E.
  apply (B2R_Bsign_inj prec emax m n Fm Fn E).
  rewrite (proj2 Mm), (proj2 Mn). reflexivity.
- exfalso. rewrite En, key_pinf, (key_finite m Fm) in E.
  generalize (val_lt_top m). lra.
- exfalso. rewrite Em, key_pinf, (key_finite n Fn) in E.
  generalize (val_lt_top n). lra.
- now rewrite Em, En.
Qed.

(** * The maximum by a comparison *)

Definition fmax (m n : float) : float := if flt m n then n else m.

Lemma fmax_mag : forall m n : float, mag m -> mag n -> mag (fmax m n).
Proof. intros m n Mm Mn. unfold fmax. destruct (flt m n); assumption. Qed.

Lemma fmax_key :
  forall m n : float, mag m -> mag n -> key (fmax m n) = Rmax (key m) (key n).
Proof.
intros m n Mm Mn. unfold fmax. rewrite (key_lt m n Mm Mn). unfold Rmax.
destruct (Rlt_bool_spec (key m) (key n)) as [H|H];
  destruct (Rle_dec (key m) (key n)) as [L|L]; lra.
Qed.

Lemma fmax_comm : forall m n : float, mag m -> mag n -> fmax m n = fmax n m.
Proof.
intros m n Mm Mn. apply key_inj; try now apply fmax_mag.
rewrite !fmax_key by assumption. apply Rmax_comm.
Qed.

Lemma fmax_assoc :
  forall a b c : float, mag a -> mag b -> mag c ->
  fmax (fmax a b) c = fmax a (fmax b c).
Proof.
intros a b c Ma Mb Mc.
apply key_inj; try (apply fmax_mag; trivial; now apply fmax_mag).
rewrite !fmax_key by (trivial; now apply fmax_mag).
symmetry. apply Rmax_assoc.
Qed.

(* The maximum of two magnitudes is finite exactly when both are. *)
Lemma fmax_finite :
  forall m n : float, mag m -> mag n -> (finite (fmax m n) <-> finite m /\ finite n).
Proof.
intros m n Mm Mn.
rewrite (key_lt_top _ (fmax_mag m n Mm Mn)), (key_lt_top m Mm), (key_lt_top n Mn).
rewrite (fmax_key m n Mm Mn). split.
- intros H. split.
  + apply Rle_lt_trans with (2 := H). apply Rmax_l.
  + apply Rle_lt_trans with (2 := H). apply Rmax_r.
- intros [H1 H2]. now apply Rmax_lub_lt.
Qed.

(* On finite numbers it is the maximum of the values. *)
Lemma fmax_val :
  forall m n : float, finite m -> finite n -> val (fmax m n) = Rmax (val m) (val n).
Proof.
intros m n Fm Fn. unfold fmax. rewrite (lt_finite prec emax m n Fm Fn). unfold Rmax, val.
destruct (Rlt_bool_spec (B2R prec emax m) (B2R prec emax n)) as [H|H];
  destruct (Rle_dec (B2R prec emax m) (B2R prec emax n)) as [L|L]; lra.
Qed.

(* A magnitude is not below +0. *)
Lemma fmax_pzero : forall m : float, mag m -> fmax m pzero = m.
Proof.
intros m M. unfold fmax. rewrite (key_lt m pzero M mag_pzero).
rewrite Rlt_bool_false. reflexivity.
change (key pzero) with 0. now apply key_nonneg.
Qed.

(** * The combination and the step, on states *)

(* The combination of two states, written with fmax: it is the generated one. *)
Definition cmb (a b : float * bool) : float * bool :=
  (fmax (fst a) (fst b), andb (snd a) (snd b)).

Lemma combine_1_eq : forall a b : float * bool, combine_1 a b = cmb a b.
Proof. reflexivity. Qed.

Lemma combine_2_eq : forall a b : float * bool, combine_2 a b = cmb a b.
Proof. reflexivity. Qed.

(* The states the loop stays in. *)
Definition magst (s : float * bool) : Prop := mag (fst s).

Lemma cmb_mag : forall a b : float * bool, magst a -> magst b -> magst (cmb a b).
Proof. intros a b Ma Mb. unfold magst, cmb. cbn [fst]. now apply fmax_mag. Qed.

Lemma cmb_comm : forall a b : float * bool, magst a -> magst b -> cmb a b = cmb b a.
Proof.
intros a b Ma Mb. unfold cmb. now rewrite (fmax_comm _ _ Ma Mb), andb_comm.
Qed.

Lemma cmb_assoc :
  forall a b c : float * bool, magst a -> magst b -> magst c ->
  cmb (cmb a b) c = cmb a (cmb b c).
Proof.
intros a b c Ma Mb Mc. unfold cmb. cbn [fst snd].
now rewrite (fmax_assoc _ _ _ Ma Mb Mc), andb_assoc.
Qed.

Lemma cmb_zero : cmb zero_state zero_state = zero_state.
Proof. unfold cmb, fmax. cbn [fst snd andb]. destruct (flt pzero pzero); reflexivity. Qed.

(* What an element is combined into the state as: its magnitude with a true mask, or,
   for a NaN, +0 with a false mask. *)
Definition img (x : float) : float * bool :=
  if is_nan prec emax x then (pzero, false) else (fabs x, true).

Lemma img_mag : forall x : float, magst (img x).
Proof.
intros x. unfold magst, img. destruct (is_nan prec emax x) eqn:N; cbn [fst].
- exact mag_pzero.
- now apply abs_mag.
Qed.

(* On a state the loop can be in, the generated step is the combination with img x. *)
Lemma step_1_cmb :
  forall (s : float * bool) (x : float), magst s -> step_1 s x = cmb s (img x).
Proof.
intros [m ok] x M. unfold magst in M. cbn [fst] in M.
unfold IeeeFoldModel.norm_upper_1_step, IeeeModel.norm_step_1, IeeeModel.norm_combine.
cbv zeta. cbn [fst snd].
rewrite (eq_self prec emax (fabs x)).
unfold img. destruct (is_nan prec emax x) eqn:N.
- rewrite (abs_nan x N). rewrite (lt_nan_r m (fabs x) (abs_nan x N)).
  unfold cmb. cbn [fst snd negb]. now rewrite (fmax_pzero m M).
- rewrite (proj1 (abs_mag x N)). reflexivity.
Qed.

(* The step of two limbs is the step of one limb on the leading limb. *)
Lemma step_2_eq :
  forall (s : float * bool) (x : float * float), step_2 s x = step_1 s (fst x).
Proof. reflexivity. Qed.

Lemma step_1_mag : forall (s : float * bool) (x : float), magst s -> magst (step_1 s x).
Proof. intros s x M. rewrite (step_1_cmb s x M). apply cmb_mag. exact M. apply img_mag. Qed.

(** * The two orders return the same state *)

Theorem norm_upper_1_lanes_seq_state :
  forall (W : nat) (xs : list float),
  fold_lanes step_1 combine_1 zero_state W xs = fold_seq step_1 zero_state xs.
Proof.
intros W xs.
apply (fold_lanes_aci_step (float * bool) float magst step_1 cmb img zero_state
         mag_pzero cmb_mag cmb_comm cmb_assoc cmb_zero).
apply Forall_forall. intros x _. split. apply img_mag. intros s M. now apply step_1_cmb.
Qed.

Theorem norm_upper_2_lanes_seq_state :
  forall (W : nat) (xs : list (float * float)),
  fold_lanes step_2 combine_2 zero_state W xs = fold_seq step_2 zero_state xs.
Proof.
intros W xs.
apply (fold_lanes_aci_step (float * bool) (float * float) magst step_2 cmb
         (fun x => img (fst x)) zero_state mag_pzero cmb_mag cmb_comm cmb_assoc cmb_zero).
apply Forall_forall. intros x _. split. apply img_mag.
intros s M. rewrite step_2_eq. now apply step_1_cmb.
Qed.

(* The generated folds, with their finish: bit for bit the same result and the same
   flag in the two orders, for every number of lanes and every list. *)
Theorem norm_upper_1_lanes_seq_ieee :
  forall (W : nat) (xs : list float), lanes_1_ieee W xs = seq_1_ieee xs.
Proof.
intros W xs. unfold IeeeFoldModel.norm_upper_1_lanes, IeeeFoldModel.norm_upper_1_seq.
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Theorem norm_upper_2_lanes_seq_ieee :
  forall (W : nat) (xs : list (float * float)), lanes_2_ieee W xs = seq_2_ieee xs.
Proof.
intros W xs. unfold IeeeFoldModel.norm_upper_2_lanes, IeeeFoldModel.norm_upper_2_seq.
now rewrite norm_upper_2_lanes_seq_state.
Qed.

(** * The sequential order and the real model *)

(* The values of a state; a state that is live, on the states the loop can be in: finite
   with a true mask; a good state. *)
Definition vals (s : float * bool) : R * bool := (val (fst s), snd s).
Definition live (s : float * bool) : Prop := magst s -> finite (fst s) /\ snd s = true.
Definition good (s : float * bool) : Prop := magst s /\ finite (fst s) /\ snd s = true.

Lemma zero_good : good zero_state.
Proof. split. exact mag_pzero. split; reflexivity. Qed.

(* A state that is not live stays so. *)
Lemma step_1_dead : forall (s : float * bool) (x : float), live (step_1 s x) -> live s.
Proof.
intros s x L M. destruct (L (step_1_mag s x M)) as [F E].
rewrite (step_1_cmb s x M) in F, E. unfold cmb in F, E. cbn [fst snd] in F, E.
split.
- exact (proj1 (proj1 (fmax_finite _ _ M (img_mag x)) F)).
- exact (proj1 (andb_prop _ _ E)).
Qed.

(* From a good state, a live result is good, shows a finite element, and has the values
   of the step of the real model. *)
Lemma step_1_live :
  forall (s : float * bool) (x : float), good s -> live (step_1 s x) ->
  good (step_1 s x) /\ finite x /\
  vals (step_1 s x) = FoldModel.norm_upper_1_step (vals s) (val x).
Proof.
intros s x [M [Fs Es]] L.
pose proof (step_1_mag s x M) as M1. destruct (L M1) as [F E].
split. { split. exact M1. split; assumption. }
rewrite (step_1_cmb s x M) in F, E |- *. unfold cmb in F, E |- *. cbn [fst snd] in F, E.
destruct (proj1 (fmax_finite _ _ M (img_mag x)) F) as [_ Fi].
apply andb_prop in E. destruct E as [_ Ei].
unfold img in Fi, Ei |- *. destruct (is_nan prec emax x) eqn:N; cbn [fst snd] in Fi, Ei.
- discriminate Ei.
- assert (Fx : finite x).
  { unfold finite in Fi |- *. now rewrite (abs_finite prec emax nan_abs) in Fi. }
  split. exact Fx.
  rewrite norm_upper_1_step_eq. unfold vals, maxc. cbn [fst snd].
  rewrite (fmax_val _ _ Fs Fi). unfold val. now rewrite (abs_val prec emax nan_abs).
Qed.

(* One limb, the sequential order: the final state is a magnitude, and if it is finite
   with a true mask, every element is finite and its values are the final state of the
   real model. *)
Lemma seq_1_state :
  forall xs : list float,
  let s := fold_seq step_1 zero_state xs in
  magst s /\
  (finite (fst s) -> snd s = true ->
   Forall finite xs /\ vals s = FoldModel.norm_upper_1_seq (map val xs)).
Proof.
intros xs s.
assert (M : magst s).
{ unfold s. apply fold_seq_inv. exact mag_pzero. intros t e. apply step_1_mag. }
split. exact M. intros F E.
assert (Hl : forall (t : float * bool) (e : float), good t -> True -> live (step_1 t e) ->
             good (step_1 t e) /\ finite e /\
             vals (step_1 t e) = FoldModel.norm_upper_1_step (vals t) (val e)).
{ intros t e G _ L. now apply step_1_live. }
assert (Ht : Forall (fun _ : float => True) xs) by (apply Forall_forall; intros; exact I).
assert (L : live (fold_seq step_1 zero_state xs)) by (intros _; split; assumption).
destruct (fold_seq_transfer _ _ _ _ step_1 FoldModel.norm_upper_1_step vals (@val prec emax)
            live good (fun _ => True) (@finite prec emax) step_1_dead Hl zero_state xs
            zero_good Ht L) as [_ [Fx V]].
split. exact Fx. exact V.
Qed.

(* Two limbs: the same on the leading limbs, and a canonical element with a finite
   leading limb is a finite normalized pair (good2 of IeeeFolds.v). *)
Lemma step_2_dead :
  forall (s : float * bool) (x : float * float), live (step_2 s x) -> live s.
Proof. intros s x. rewrite step_2_eq. apply step_1_dead. Qed.

Lemma step_2_live :
  forall (s : float * bool) (x : float * float), good s -> can2 prec emax x ->
  live (step_2 s x) ->
  good (step_2 s x) /\ good2 prec emax x /\
  vals (step_2 s x) = FoldModel.norm_upper_2_step (vals s) (vals2 prec emax x).
Proof.
intros s x G C L. rewrite step_2_eq in L |- *.
destruct (step_1_live s (fst x) G L) as [G1 [Fx V]].
split. exact G1. split. exact (can2_good prec emax x C Fx).
rewrite V. reflexivity.
Qed.

Lemma seq_2_state :
  forall xs : list (float * float), Forall (can2 prec emax) xs ->
  let s := fold_seq step_2 zero_state xs in
  magst s /\
  (finite (fst s) -> snd s = true ->
   Forall (good2 prec emax) xs /\
   vals s = FoldModel.norm_upper_2_seq (map (vals2 prec emax) xs)).
Proof.
intros xs Hx s.
assert (M : magst s).
{ unfold s. apply fold_seq_inv. exact mag_pzero.
  intros t e. rewrite step_2_eq. apply step_1_mag. }
split. exact M. intros F E.
assert (L : live (fold_seq step_2 zero_state xs)) by (intros _; split; assumption).
destruct (fold_seq_transfer _ _ _ _ step_2 FoldModel.norm_upper_2_step vals
            (vals2 prec emax) live good (can2 prec emax) (good2 prec emax)
            step_2_dead step_2_live zero_state xs zero_good Hx L) as [_ [Fx V]].
split. exact Fx. exact V.
Qed.

(** * The folds with their finish *)

(* One limb, the sequential order. *)
Theorem norm_upper_1_seq_ieee_facts :
  (1 <= prec)%Z ->
  forall xs : list float,
  let '(r, flag) := seq_1_ieee xs in
  (flag = true ->
   Forall finite xs /\ finite r /\
   let vs := map val xs in
   let s := FoldModel.norm_upper_1_seq vs in
   let r_ := fst s in
   let v_ := fold_right Rmax 0 (map (fun x => Rabs x) vs) in
   val r = r_ /\
   fmt emin prec r_ /\
   v_ <= r_ /\
   r_ <= RU emin prec v_) /\
  (flag = false -> nan r).
Proof.
intros Hp xs. unfold IeeeFoldModel.norm_upper_1_seq. cbv zeta.
destruct (seq_1_state xs) as [M HS].
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (fst (fold_seq step_1 zero_state xs)) (snd (fold_seq step_1 zero_state xs))).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (fst (fold_seq step_1 zero_state xs)) (snd (fold_seq step_1 zero_state xs)))
  as [r flag].
intros [H1 [H2 H3]]. split; [|exact H3].
intros E. destruct (proj1 H1 E) as [Eok F]. destruct (HS F Eok) as [Fx V].
rewrite (H2 E). split. exact Fx. split. exact F. split.
- rewrite <- V. reflexivity.
- exact (norm_upper_1_seq_correct emin prec Hp (map val xs) (vals_fmt prec emax xs)).
Qed.

(* Two limbs, the sequential order. *)
Theorem norm_upper_2_seq_ieee_facts :
  (1 <= prec)%Z ->
  forall xs : list (float * float), Forall (can2 prec emax) xs ->
  let '(r, flag) := seq_2_ieee xs in
  (flag = true ->
   Forall (good2 prec emax) xs /\ finite r /\
   let vs := map (vals2 prec emax) xs in
   let s := FoldModel.norm_upper_2_seq vs in
   let r_ := succ radix2 fexp (fst s) in
   let v_ := fold_right Rmax 0 (map (fun x => Rabs (fst x + snd x)) vs) in
   val r = r_ /\
   fmt emin prec r_ /\
   v_ <= r_ /\
   r_ <= succ radix2 fexp (RU emin prec v_)) /\
  (flag = false -> nan r).
Proof.
intros Hp xs Hx. unfold IeeeFoldModel.norm_upper_2_seq. cbv zeta.
destruct (seq_2_state xs Hx) as [M HS].
generalize (norm_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (fst (fold_seq step_2 zero_state xs)) (snd (fold_seq step_2 zero_state xs))).
destruct (IeeeModel.norm_finish_2 prec emax nan_abs nan_const
            (fst (fold_seq step_2 zero_state xs)) (snd (fold_seq step_2 zero_state xs)))
  as [r flag].
intros [H1 [H2 H3]]. split; [|exact H3].
intros E. destruct (proj1 H1 E) as [Eok Fs].
destruct (succ_nonneg prec emax _ (mag_nonneg_ext _ M)) as [_ HN].
destruct (HN Fs) as [F Vs].
destruct (HS F Eok) as [Gx V].
rewrite (H2 E). split. exact Gx. split. exact Fs. split.
- unfold val. rewrite Vs. rewrite <- V. reflexivity.
- exact (norm_upper_2_seq_correct emin prec Hp (map (vals2 prec emax) xs)
           (good2_normalized prec emax xs Gx)).
Qed.

(** * When the flag is true *)

(* From a good state a finite element gives a good state. *)
Lemma step_1_good :
  forall (s : float * bool) (x : float), good s -> finite x -> good (step_1 s x).
Proof.
intros s x [M [F E]] Fx.
split. now apply step_1_mag.
rewrite (step_1_cmb s x M). unfold cmb, img. cbn [fst snd].
rewrite (finite_not_nan prec emax x Fx). cbn [fst snd].
split.
- apply (proj2 (fmax_finite _ _ M (abs_mag x (finite_not_nan prec emax x Fx)))).
  split. exact F. unfold finite. now rewrite (abs_finite prec emax nan_abs).
- now rewrite E.
Qed.

Lemma seq_1_good :
  forall xs : list float, Forall finite xs -> good (fold_seq step_1 zero_state xs).
Proof.
intros xs H. unfold fold_seq. generalize zero_state zero_good.
induction H as [|x r Fx _ IH]; intros s G; cbn [fold_left].
- exact G.
- apply IH. now apply step_1_good.
Qed.

(* One limb: the flag is true exactly when every element is finite. *)
Theorem norm_upper_1_seq_ieee_flag :
  forall xs : list float, snd (seq_1_ieee xs) = true <-> Forall finite xs.
Proof.
intros xs. unfold IeeeFoldModel.norm_upper_1_seq. cbv zeta.
destruct (seq_1_state xs) as [M HS].
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (fst (fold_seq step_1 zero_state xs)) (snd (fold_seq step_1 zero_state xs))).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const
            (fst (fold_seq step_1 zero_state xs)) (snd (fold_seq step_1 zero_state xs)))
  as [r flag].
intros [H1 _]. cbn [snd]. split.
- intros E. destruct (proj1 H1 E) as [Eok F]. exact (proj1 (HS F Eok)).
- intros Fx. destruct (seq_1_good xs Fx) as [_ [F E]]. apply H1. split; assumption.
Qed.

(* Two limbs: the flag is true exactly when every leading limb is finite and the
   successor of the final state, the largest |x0|, is finite. *)
Theorem norm_upper_2_seq_ieee_flag :
  forall xs : list (float * float),
  snd (seq_2_ieee xs) = true <->
  Forall (fun x => finite (fst x)) xs /\
  finite (fsucc (fst (fold_seq step_2 zero_state xs))).
Proof.
intros xs. unfold IeeeFoldModel.norm_upper_2_seq. cbv zeta.
assert (E2 : fold_seq step_2 zero_state xs = fold_seq step_1 zero_state (map fst xs)).
{ rewrite <- (fold_seq_map _ _ _ step_1 fst zero_state xs).
  apply fold_seq_ext. intros s x. apply step_2_eq. }
rewrite E2.
destruct (seq_1_state (map fst xs)) as [M HS].
generalize (norm_finish_2_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const
              (fst (fold_seq step_1 zero_state (map fst xs)))
              (snd (fold_seq step_1 zero_state (map fst xs)))).
destruct (IeeeModel.norm_finish_2 prec emax nan_abs nan_const
            (fst (fold_seq step_1 zero_state (map fst xs)))
            (snd (fold_seq step_1 zero_state (map fst xs))))
  as [r flag].
intros [H1 _]. cbn [snd]. split.
- intros E. destruct (proj1 H1 E) as [Eok Fs]. split; [|exact Fs].
  destruct (succ_nonneg prec emax _ (mag_nonneg_ext _ M)) as [_ HN].
  destruct (HN Fs) as [F _].
  apply Forall_map. exact (proj1 (HS F Eok)).
- intros [Fx Fs]. apply H1. split; [|exact Fs].
  apply Forall_map in Fx. exact (proj2 (proj2 (seq_1_good (map fst xs) Fx))).
Qed.

End IeeeFoldNorm.

(** * The generated statements of the folds *)

Theorem norm_upper_1_seq_ieee_correct : norm_upper_1_seq_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const Hp xs.
exact (norm_upper_1_seq_ieee_facts prec emax nan_abs nan_const Hp xs).
Qed.

Theorem norm_upper_1_lanes_ieee_correct : norm_upper_1_lanes_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const Hp W xs.
rewrite (norm_upper_1_lanes_seq_ieee prec emax nan_abs nan_const W xs).
generalize (norm_upper_1_seq_ieee_facts prec emax nan_abs nan_const Hp xs).
destruct (IeeeFoldModel.norm_upper_1_seq prec emax nan_abs nan_const xs) as [r flag].
cbv zeta. rewrite norm_upper_1_lanes_seq. intros H. exact H.
Qed.

Theorem norm_upper_2_seq_ieee_correct : norm_upper_2_seq_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const Hp xs Hx.
generalize (norm_upper_2_seq_ieee_facts prec emax nan_abs nan_const Hp xs Hx).
destruct (IeeeFoldModel.norm_upper_2_seq prec emax nan_abs nan_const xs) as [r flag].
intros [HT HF]. split; [|exact HF].
intros E. destruct (HT E) as [G [Fr H]].
split.
{ eapply Forall_impl; [|exact G]. intros x [A [B _]]. split; assumption. }
split. exact Fr. exact H.
Qed.

Theorem norm_upper_2_lanes_ieee_correct : norm_upper_2_lanes_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const Hp W xs Hx.
rewrite (norm_upper_2_lanes_seq_ieee prec emax nan_abs nan_const W xs).
generalize (norm_upper_2_seq_ieee_correct prec emax Hg Hl nan_abs nan_const Hp xs Hx).
destruct (IeeeFoldModel.norm_upper_2_seq prec emax nan_abs nan_const xs) as [r flag].
cbv zeta. rewrite norm_upper_2_lanes_seq. intros H. exact H.
Qed.

(** * The generated statements of the orders and the flag *)

(* F_orders_ieee_spec and F_flag_ieee_spec (proofs/gen/IeeeFoldStatements.v): the lane order
   computes the state of the sequential order, and when exactly the flag of the sequential
   order is true; the theorems of the section above with its variables bound. *)
Theorem norm_upper_1_orders_ieee_correct : norm_upper_1_orders_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs W xs.
exact (norm_upper_1_lanes_seq_state prec emax nan_abs W xs).
Qed.

Theorem norm_upper_1_flag_ieee_correct : norm_upper_1_flag_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const xs.
exact (norm_upper_1_seq_ieee_flag prec emax nan_abs nan_const xs).
Qed.

Theorem norm_upper_2_orders_ieee_correct : norm_upper_2_orders_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs W xs.
exact (norm_upper_2_lanes_seq_state prec emax nan_abs W xs).
Qed.

Theorem norm_upper_2_flag_ieee_correct : norm_upper_2_flag_ieee_spec.
Proof.
intros prec emax Hg Hl nan_abs nan_const xs.
exact (norm_upper_2_seq_ieee_flag prec emax nan_abs nan_const xs).
Qed.
