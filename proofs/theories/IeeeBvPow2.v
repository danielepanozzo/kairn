(* The scaling of a ball vector by a power of two in the IEEE model: the generated
   statements of its steps (proofs/gen/IeeeStatements.v; their leading limbs in
   proofs/gen/IeeeFoldStatements.v) and of the folds bv_mul_pow2_1 and bv_mul_pow2_2 in
   both orders (proofs/gen/IeeeFoldStatements.v).

   The steps. For finite operands and a finite center, every operation of the step is that
   of the real model, the comparisons of the mask included (step_k_values, as
   ball_mul_pow2_k_core of IeeeBallPow2.v): so the claims of the real model
   (bv_mul_pow2_step_k_correct of BvPow2.v) hold of the values. The leading limb of the
   center is a product of the leading limb by c, or a sum of such products.

   The radius kernel (radius_ieee): the radius lines of ball_mul_pow2_k (radius_pow2 of
   IeeeBallPow2.v, nonnegative, +infinity or a NaN, and when finite the real model's), plus
   m - m, which is +0 for a finite m and a NaN for m = +infinity. So the radius is
   nonnegative, +infinity or a NaN; when finite, m and rx are finite, and the radius is the
   real model's, which does not depend on m (radius_any_m of BvPow2.v).

   The folds. As for the other ball vectors (IeeeBv.v): when the flag is true, the radius is
   finite, so m is, so every center written is (the record), so every operand is
   (the leading limb of the step), and the values are those of the real model, the masks
   included, hence the mask ex of the state is that of the real model, and the radius is
   the real model's (bv_mul_pow2_k_result). V2 and exactness are then the real-model
   theorems (BvPow2.v) read on the values; V3 is what the result says; when the flag is
   false the result is the whole space. V4: under its conditions every scaled center is
   finite (one rounding of a number at most 2^(emax - 2), mul_pow2_2_ieee_finite_any for two
   limbs), so the record's state is finite with a true mask, and the radius lines on
   rx c <= 2^(emax - 2) are finite (radius_pow2_fin of IeeeBallPow2.v). The lane order
   returns what the sequential order returns: the record's state by
   norm_upper_k_lanes_seq_state, the mask by fold_lanes_and and fold_seq_and. *)
From Stdlib Require Import Reals ZArith List Lia Lra Bool Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel FoldStatements
  IeeeFoldStatements.
From Kairn Require Import Format Normalized Folds FoldTransfer IeeeBridge IeeeVocabulary IeeeOps IeeeEFT
  IeeeFoldNorm IeeeFoldMaps IeeeSub IeeeFinite IeeeBallFinite IeeeBallPow2 BvPow2.
From Kairn Require BallPow2 IeeeOperations IeeeBv.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

(* forallb of a map, against a list of the same length entry by entry. *)
Lemma forallb_map_ext :
  forall (A B : Type) (f : B -> bool) (h : A -> B) (g : A -> bool) (l : list A),
  (forall x, In x l -> f (h x) = g x) -> forallb f (map h l) = forallb g l.
Proof.
intros A B f h g l. induction l as [|x r IH]; intros H; cbn [map forallb]; trivial.
rewrite (H x (or_introl eq_refl)), IH; trivial. intros y Hy. apply H. right. exact Hy.
Qed.

Section IeeeBvPow2.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation fabs := (IeeeOperations.abs prec emax nan_abs).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation flt := (IeeeOperations.lt prec emax).
Notation feq := (IeeeOperations.eq prec emax).
Notation fsucc := (IeeeOperations.succ prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation Nc := (IeeeModel.up_ball_mul_pow2_1_0 prec emax).
Notation Nr := (bpow radix2 (emin + prec - 1)).
Notation step_1 := (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
Notation zero_state := (pzero, true).
Notation st1 := (IeeeModel.bv_mul_pow2_step_1 prec emax nan_abs nan_fma).
Notation st2 := (IeeeModel.bv_mul_pow2_step_2 prec emax nan_plus nan_minus nan_abs nan_fma).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(** * The steps *)

Lemma step_1_values :
  forall x c : float, fin x -> fin c ->
  fin (fst (st1 x c)) ->
  fin x /\ (b2r (fst (st1 x c)), snd (st1 x c)) = Model.bv_mul_pow2_step_1 emin prec tie_even (b2r x) (b2r c).
Proof.
intros x c Fx Fc. unfold IeeeModel.bv_mul_pow2_step_1, Model.bv_mul_pow2_step_1. cbv beta iota zeta.
cbn [fst snd]. intros Fz. split. exact Fx.
destruct (const_N prec emax) as [FN EN].
rewrite (lt_finite prec emax Nc (fabs (prod x c)) FN) by (now rewrite (abs_finite prec emax nan_abs)).
rewrite EN, (abs_val prec emax nan_abs), (eq_finite prec emax x pzero Fx eq_refl).
rewrite (prod_val prec emax nan_fma x c Fx Fc Fz), (BallPow2.up_ball_mul_pow2_1_0_eq emin prec).
reflexivity.
Qed.

Lemma step_2_values :
  (2 <= prec)%Z ->
  forall x0 x1 c : float, fin x0 -> fin x1 -> fin c ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> (exists n : Z, b2r c = bpow radix2 n) ->
  fin (fst (fst (st2 x0 x1 c))) ->
  fin (snd (fst (st2 x0 x1 c))) /\
  (b2r (fst (fst (st2 x0 x1 c))), b2r (snd (fst (st2 x0 x1 c))), snd (st2 x0 x1 c))
  = Model.bv_mul_pow2_step_2 emin prec tie_even (b2r x0) (b2r x1) (b2r c).
Proof.
intros Hp2 x0 x1 c F0 F1 Fc Nx Pc.
unfold IeeeModel.bv_mul_pow2_step_2, Model.bv_mul_pow2_step_2.
generalize (mul_pow2_2_values prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_fma Hp2 x0 x1 c
              F0 F1 Fc Nx Pc).
unfold IeeeModel.mul_pow2_2, Model.mul_pow2_2. cbv zeta.
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (prod x0 c) (prod x1 c))
  as [z0 z1] eqn:EF.
destruct (Model.fast_two_sum emin prec tie_even (rnd (b2r x0 * b2r c + 0))
            (rnd (b2r x1 * b2r c + 0))) as [r0 r1].
cbv beta iota zeta. cbn [fst snd]. intros V Fz.
destruct (V Fz) as [Fz1 Ez]. split. exact Fz1.
assert (E0 : z0 = add (prod x0 c) (prod x1 c)).
{ unfold IeeeModel.fast_two_sum in EF. cbv zeta in EF. now inversion EF. }
assert (Fhl : fin (prod x0 c) /\ fin (prod x1 c)).
{ apply (add_finite_inv prec emax nan_plus). now rewrite <- E0. }
destruct Fhl as [Fh Fl].
destruct (const_N prec emax) as [FN EN].
rewrite (eq_finite prec emax x1 pzero F1 eq_refl), (eq_finite prec emax x0 pzero F0 eq_refl).
change (b2r pzero) with 0.
injection Ez as Ez0 Ez1. rewrite Ez0, Ez1, (BallPow2.up_ball_mul_pow2_1_0_eq emin prec).
destruct (Req_bool (b2r x1) 0).
- rewrite (lt_finite prec emax Nc (fabs (prod x0 c)) FN) by (now rewrite (abs_finite prec emax nan_abs)).
  now rewrite EN, (abs_val prec emax nan_abs), (prod_val prec emax nan_fma x0 c F0 Fc Fh).
- rewrite (lt_finite prec emax Nc (fabs (prod x1 c)) FN) by (now rewrite (abs_finite prec emax nan_abs)).
  now rewrite EN, (abs_val prec emax nan_abs), (prod_val prec emax nan_fma x1 c F1 Fc Fl).
Qed.

Lemma step_1_lead : forall x c : float, fin (fst (st1 x c)) -> fin x /\ fin c.
Proof.
intros x c. unfold IeeeModel.bv_mul_pow2_step_1. cbv zeta. cbn [fst]. intros F.
unfold IeeeOperations.prod in F.
destruct (fma_finite_inv prec emax nan_fma x c pzero F) as [Fx [Fc _]]. split; assumption.
Qed.

Lemma step_2_lead : forall x0 x1 c : float, fin (fst (fst (st2 x0 x1 c))) -> fin x0 /\ fin c.
Proof.
intros x0 x1 c. unfold IeeeModel.bv_mul_pow2_step_2. cbv zeta.
destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (prod x0 c) (prod x1 c))
  as [z0 z1] eqn:EF.
cbn [fst]. intros F.
assert (E0 : z0 = add (prod x0 c) (prod x1 c)).
{ unfold IeeeModel.fast_two_sum in EF. cbv zeta in EF. now inversion EF. }
rewrite E0 in F. destruct (add_finite_inv prec emax nan_plus _ _ F) as [Fh _].
unfold IeeeOperations.prod in Fh.
destruct (fma_finite_inv prec emax nan_fma x0 c pzero Fh) as [Fx [Fc _]]. split; assumption.
Qed.

(** * The radius kernel *)

(* The radius lines of the real model, with m - m = 0 taken out. *)
Lemma real_radius_eq :
  forall (m : R) (ex : bool) (rx c : R),
  Model.bv_mul_pow2_radius emin prec tie_even m ex rx c =
  if andb ex (orb (Rlt_bool Nr (rnd (rx * c + 0))) (Req_bool rx 0)) then rnd (rx * c + 0)
  else Ulp.succ radix2 fexp (Ulp.succ radix2 fexp (rnd (rx * c + 0))).
Proof.
intros m ex rx c. unfold Model.bv_mul_pow2_radius. cbv zeta.
rewrite (BallPow2.up_ball_mul_pow2_1_0_eq emin prec).
replace (m - m) with 0 by ring. rewrite round_0 by auto with typeclass_instances.
rewrite Rplus_0_r. apply round_generic; auto with typeclass_instances.
destruct (andb _ _).
- apply generic_format_round; auto with typeclass_instances.
- apply generic_format_succ; auto with typeclass_instances.
  apply generic_format_succ; auto with typeclass_instances.
  apply generic_format_round; auto with typeclass_instances.
Qed.

Lemma radius_ieee :
  forall (m : float) (ex : bool) (rx c : float),
  mag prec emax m -> nonneg_ext rx -> fin c -> 0 <= b2r c ->
  let rz := IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma m ex rx c in
  nonneg_ext rz /\
  (fin rz -> fin m /\ fin rx /\
   b2r rz = Model.bv_mul_pow2_radius emin prec tie_even (b2r m) ex (b2r rx) (b2r c)).
Proof.
intros m ex rx c M Nrx Fc Pc. unfold IeeeModel.bv_mul_pow2_radius. cbv zeta.
generalize (radius_pow2 prec emax nan_fma rx c ex Nrx Fc Pc). cbv zeta. intros [Ns Ks].
set (rs := if andb ex (orb (flt Nc (prod rx c)) (feq rx pzero)) then prod rx c
           else fsucc (fsucc (prod rx c))) in *.
assert (Nd : nonneg_ext (sub m m) /\ (fin (sub m m) -> fin m /\ b2r (sub m m) = 0)).
{ destruct (mag_cases prec emax m M) as [Fm|Em].
  - destruct (sub_spec prec emax nan_minus m m Fm Fm) as [S V].
    replace (b2r m - b2r m) with 0 in S, V by ring.
    rewrite round_0 in S, V by auto with typeclass_instances.
    assert (Fd : fin (sub m m)).
    { apply S. unfold inrange. rewrite Rabs_R0. apply bpow_gt_0. }
    split.
    + apply (nonneg_ext_finite prec emax). exact Fd. rewrite (V Fd). lra.
    + intros _. split. exact Fm. exact (V Fd).
  - subst m. split.
    + apply (nonneg_ext_nan prec emax). reflexivity.
    + intros F. discriminate F. }
destruct Nd as [Nd Kd].
destruct (add_nonneg prec emax nan_plus rs (sub m m) Ns Nd) as [Nz [Kz _]].
split. exact Nz.
intros Frz. destruct (Kz Frz) as [Frs [Fd Vz]].
destruct (Ks Frs) as [Frx [Frr [Err Ers]]]. destruct (Kd Fd) as [Fm Vd].
split. exact Fm. split. exact Frx.
rewrite Vz, Vd, Rplus_0_r, round_generic by (auto with typeclass_instances; apply b2r_format).
rewrite Ers, real_radius_eq, Err. reflexivity.
Qed.

(** * The fold of one limb *)

Notation stp1 c := (IeeeFoldModel.bv_mul_pow2_1_step prec emax nan_abs nan_fma c).

Lemma bv_mul_pow2_1_result :
  forall (rx c : float) (xs : list float),
  nonneg_ext rx -> fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  let es := map (stp1 c) xs in
  let ws := map fst es in
  (exists rz : float, fin rz /\ 0 <= b2r rz /\ fin rx /\
     Forall (fun x => fin x /\ fin (fst (stp1 c x)) /\
        (b2r (fst (stp1 c x)), snd (stp1 c x)) =
        Model.bv_mul_pow2_step_1 emin prec tie_even (b2r x) (b2r c)) xs /\
     b2r rz = FoldModel.bv_mul_pow2_1_radius emin prec tie_even (b2r rx) (b2r c) (map b2r xs) /\
     IeeeFoldModel.bv_mul_pow2_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs =
       (ws, rz, true)) \/
  IeeeFoldModel.bv_mul_pow2_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs =
    (map (fun _ => pzero) ws, pinf, false).
Proof.
intros rx c xs Nrx Fc Pc es ws.
assert (Pc0 : 0 <= b2r c) by (destruct Pc as [n E]; rewrite E; apply bpow_ge_0).
unfold IeeeFoldModel.bv_mul_pow2_1_seq. cbv zeta. fold es. fold ws.
change (IeeeFoldModel.bv_mul_pow2_1_record prec emax nan_abs) with step_1.
destruct (seq_1_state prec emax nan_abs ws) as [M HS].
set (s := fold_seq step_1 zero_state ws) in *.
set (ex := fold_seq (fun m_ e_ => andb m_ (snd e_)) true es).
destruct (radius_ieee (fst s) ex rx c M Nrx Fc Pc0) as [Nr Er].
set (rz := IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma (fst s) ex rx c) in *.
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct flag; [left|right; reflexivity].
destruct (proj1 H1 eq_refl) as [Eok Frz].
destruct (Er Frz) as [Fm [Frx Vr]].
destruct (HS Fm Eok) as [Fws _].
assert (Hz : Forall (fun x => fin x /\ fin (fst (stp1 c x)) /\
                (b2r (fst (stp1 c x)), snd (stp1 c x)) =
                Model.bv_mul_pow2_step_1 emin prec tie_even (b2r x) (b2r c)) xs).
{ unfold ws, es in Fws. rewrite map_map in Fws. apply Forall_map_inv in Fws. revert Fws.
  apply Forall_impl. intros x Fz.
  destruct (step_1_lead x c Fz) as [Fx _].
  destruct (step_1_values x c Fx Fc Fz) as [_ V].
  split. exact Fx. split. exact Fz. exact V. }
exists rz. split. exact Frz. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Frx. split. exact Hz. split.
- rewrite Vr. unfold FoldModel.bv_mul_pow2_1_radius.
  rewrite (radius_any_m emin prec (b2r (fst s))), (radius_any_m emin prec (fst _)). f_equal.
  unfold ex, es. rewrite fold_seq_and. unfold FoldModel.bv_mul_pow2_1_exact.
  rewrite forallb_map_ext with (g := fun x => snd (stp1 c x)).
  + symmetry. apply forallb_map_ext. intros x Hin.
    destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [_ [_ V]].
    unfold FoldModel.bv_mul_pow2_1_step. rewrite <- V. reflexivity.
  + intros x _. reflexivity.
- rewrite (H2 eq_refl). reflexivity.
Qed.

(* V4 of one limb: under its conditions the record's state is finite with a true mask and
   the radius is finite, so the flag is true. *)
Lemma bv_mul_pow2_1_finite :
  (2 <= prec)%Z ->
  forall (rx c : float) (xs : list float),
  Forall (fun x => fin x) xs -> fin rx -> 0 <= b2r rx -> fin c ->
  (exists n : Z, b2r c = bpow radix2 n) ->
  Rabs (b2r rx * b2r c) <= bpow radix2 (emax - 2) ->
  Forall (fun x => Rabs ((Rabs (b2r x) + b2r rx) * b2r c) <= bpow radix2 (emax - 2)) xs ->
  snd (IeeeFoldModel.bv_mul_pow2_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const
         rx c xs) = true.
Proof.
intros Hp2 rx c xs Fx Frx Prx Fc Pc Hr Hx.
assert (Pc0 : 0 <= b2r c) by (destruct Pc as [n E]; rewrite E; apply bpow_ge_0).
unfold IeeeFoldModel.bv_mul_pow2_1_seq. cbv zeta.
change (IeeeFoldModel.bv_mul_pow2_1_record prec emax nan_abs) with step_1.
set (es := map (stp1 c) xs). set (ws := map fst es).
assert (Fws : Forall (fun w => fin w) ws).
{ unfold ws, es. rewrite map_map. apply Forall_map. apply Forall_forall. intros x Hin.
  pose proof (proj1 (Forall_forall _ xs) Fx x Hin) as F.
  pose proof (proj1 (Forall_forall _ xs) Hx x Hin) as B.
  unfold IeeeFoldModel.bv_mul_pow2_1_step, IeeeModel.bv_mul_pow2_step_1. cbv zeta. cbn [fst].
  assert (I : inrange emax (rnd (b2r x * b2r c + 0))).
  { apply (le_bpow_inrange emax) with (emax - 2)%Z. lia.
    apply (RN_abs_le_bpow emin prec). rewrite Rplus_0_r, Rabs_mult, (Rabs_pos_eq (b2r c)) by exact Pc0.
    apply Rle_trans with (2 := Rle_trans _ _ _ (Rle_abs _) B). apply Rmult_le_compat_r. exact Pc0.
    generalize (Rabs_pos (b2r x)). lra. }
  exact (proj1 (prod_fin prec emax nan_fma x c F Fc I)). }
destruct (seq_1_good prec emax nan_abs ws Fws) as [M [Fm Eok]].
set (s := fold_seq step_1 zero_state ws) in *.
set (ex := fold_seq (fun m_ e_ => andb m_ (snd e_)) true es).
set (rz := IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma (fst s) ex rx c).
assert (Frz : fin rz).
{ unfold rz, IeeeModel.bv_mul_pow2_radius. cbv zeta.
  set (q := andb ex (orb (flt Nc (prod rx c)) (feq rx pzero))).
  assert (Fs : fin (if q then prod rx c else fsucc (fsucc (prod rx c)))).
  { apply (radius_pow2_fin prec emax nan_fma Hp2 rx c q Frx Fc). split.
    - apply Rmult_le_pos; assumption.
    - rewrite Rabs_pos_eq in Hr by (apply Rmult_le_pos; assumption). exact Hr. }
  destruct (sub_spec prec emax nan_minus (fst s) (fst s) Fm Fm) as [S V].
  replace (b2r (fst s) - b2r (fst s)) with 0 in S, V by ring.
  rewrite round_0 in S, V by auto with typeclass_instances.
  assert (Fd : fin (sub (fst s) (fst s))).
  { apply S. unfold inrange. rewrite Rabs_R0. apply bpow_gt_0. }
  destruct (add_spec prec emax nan_plus _ _ Fs Fd) as [Sa _].
  apply Sa. rewrite (V Fd), Rplus_0_r, round_generic by (auto with typeclass_instances; apply b2r_format).
  apply b2r_inrange. }
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
intros [H1 _]. cbn [snd]. apply H1. split; assumption.
Qed.

(** * The fold of two limbs *)

Notation stp2 c := (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c).

(* The record of two limbs reads the leading limbs. *)
Lemma record_2_seq :
  forall ws : list (float * float),
  fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) zero_state ws =
  fold_seq step_1 zero_state (map fst ws).
Proof.
intros ws. rewrite <- (fold_seq_map _ _ _ step_1 fst zero_state ws).
apply fold_seq_ext. intros t x. reflexivity.
Qed.

Lemma bv_mul_pow2_2_result :
  (2 <= prec)%Z ->
  forall (rx c : float) (xs : list (float * float)),
  nonneg_ext rx -> fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  Forall (fun x => canonical_2 (fst x) (snd x)) xs ->
  let es := map (stp2 c) xs in
  let ws := map fst es in
  (exists rz : float, fin rz /\ 0 <= b2r rz /\ fin rx /\
     Forall (fun x => fin (fst x) /\ fin (snd x) /\
        normalized_2 emin prec (b2r (fst x)) (b2r (snd x)) /\
        fin (fst (fst (stp2 c x))) /\ fin (snd (fst (stp2 c x))) /\
        (b2r (fst (fst (stp2 c x))), b2r (snd (fst (stp2 c x))), snd (stp2 c x)) =
        Model.bv_mul_pow2_step_2 emin prec tie_even (b2r (fst x)) (b2r (snd x)) (b2r c)) xs /\
     b2r rz = FoldModel.bv_mul_pow2_2_radius emin prec tie_even (b2r rx) (b2r c)
                (map (fun x => (b2r (fst x), b2r (snd x))) xs) /\
     IeeeFoldModel.bv_mul_pow2_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs =
       (ws, rz, true)) \/
  IeeeFoldModel.bv_mul_pow2_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs =
    (map (fun _ => (pzero, pzero)) ws, pinf, false).
Proof.
intros Hp2 rx c xs Nrx Fc Pc Hc es ws.
assert (Pc0 : 0 <= b2r c) by (destruct Pc as [n E]; rewrite E; apply bpow_ge_0).
unfold IeeeFoldModel.bv_mul_pow2_2_seq. cbv zeta. fold es. fold ws.
change (IeeeFoldModel.bv_mul_pow2_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
rewrite record_2_seq.
destruct (seq_1_state prec emax nan_abs (map fst ws)) as [M HS].
set (s := fold_seq step_1 zero_state (map fst ws)) in *.
set (ex := fold_seq (fun m_ e_ => andb m_ (snd e_)) true es).
destruct (radius_ieee (fst s) ex rx c M Nrx Fc Pc0) as [Nr Er].
set (rz := IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma (fst s) ex rx c) in *.
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct flag; [left|right; reflexivity].
destruct (proj1 H1 eq_refl) as [Eok Frz].
destruct (Er Frz) as [Fm [Frx Vr]].
destruct (HS Fm Eok) as [Fws _].
assert (Hz : Forall (fun x => fin (fst x) /\ fin (snd x) /\
        normalized_2 emin prec (b2r (fst x)) (b2r (snd x)) /\
        fin (fst (fst (stp2 c x))) /\ fin (snd (fst (stp2 c x))) /\
        (b2r (fst (fst (stp2 c x))), b2r (snd (fst (stp2 c x))), snd (stp2 c x)) =
        Model.bv_mul_pow2_step_2 emin prec tie_even (b2r (fst x)) (b2r (snd x)) (b2r c)) xs).
{ unfold ws, es in Fws. rewrite !map_map in Fws. apply Forall_map_inv in Fws.
  apply Forall_forall. intros [x0 x1] Hin.
  pose proof (proj1 (Forall_forall _ xs) Fws (x0, x1) Hin) as Fz.
  pose proof (proj1 (Forall_forall _ xs) Hc (x0, x1) Hin) as Cx. cbn [fst snd] in Fz, Cx |- *.
  unfold IeeeFoldModel.bv_mul_pow2_2_step in Fz |- *. cbn [fst snd] in Fz |- *.
  destruct (step_2_lead x0 x1 c Fz) as [F0 _].
  destruct Cx as [[_ [F1 Nx]]|[[[sg Ei] _]|[Ni _]]].
  - destruct (step_2_values Hp2 x0 x1 c F0 F1 Fc Nx Pc Fz) as [Fz1 V].
    split. exact F0. split. exact F1. split. exact Nx. split. exact Fz. split. exact Fz1. exact V.
  - rewrite Ei in F0. discriminate F0.
  - unfold nan in Ni. rewrite (nan_not_finite prec emax x0 Ni) in F0. discriminate F0. }
exists rz. split. exact Frz. split. exact (nonneg_ext_fin prec emax _ Nr Frz).
split. exact Frx. split. exact Hz. split.
- rewrite Vr. unfold FoldModel.bv_mul_pow2_2_radius.
  rewrite (radius_any_m emin prec (b2r (fst s))), (radius_any_m emin prec (fst _)). f_equal.
  unfold ex, es. rewrite fold_seq_and. unfold FoldModel.bv_mul_pow2_2_exact.
  rewrite forallb_map_ext with (g := fun x => snd (stp2 c x)).
  + symmetry. apply forallb_map_ext. intros x Hin.
    destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [_ [_ [_ [_ [_ V]]]]].
    unfold FoldModel.bv_mul_pow2_2_step. cbn [fst snd]. rewrite <- V. reflexivity.
  + intros x _. reflexivity.
- rewrite (H2 eq_refl). reflexivity.
Qed.

Lemma bv_mul_pow2_2_finite :
  (2 <= prec)%Z ->
  forall (rx c : float) (xs : list (float * float)),
  Forall (fun x => fin (fst x) /\ fin (snd x) /\ normalized_2 emin prec (b2r (fst x)) (b2r (snd x)))
    xs ->
  fin rx -> 0 <= b2r rx -> fin c -> (exists n : Z, b2r c = bpow radix2 n) ->
  Rabs (b2r rx * b2r c) <= bpow radix2 (emax - 2) ->
  Forall (fun x => Rabs ((Rabs (b2r (fst x) + b2r (snd x)) + b2r rx) * b2r c) <= bpow radix2 (emax - 2))
    xs ->
  snd (IeeeFoldModel.bv_mul_pow2_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const
         rx c xs) = true.
Proof.
intros Hp2 rx c xs Fx Frx Prx Fc Pc Hr Hx.
assert (Pc0 : 0 <= b2r c) by (destruct Pc as [n E]; rewrite E; apply bpow_ge_0).
unfold IeeeFoldModel.bv_mul_pow2_2_seq. cbv zeta.
change (IeeeFoldModel.bv_mul_pow2_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
rewrite record_2_seq.
set (es := map (stp2 c) xs). set (ws := map fst es).
assert (Fws : Forall (fun w => fin w) (map fst ws)).
{ unfold ws, es. rewrite !map_map. apply Forall_map. apply Forall_forall. intros [x0 x1] Hin.
  pose proof (proj1 (Forall_forall _ xs) Fx (x0, x1) Hin) as [F0 [F1 Nx]].
  pose proof (proj1 (Forall_forall _ xs) Hx (x0, x1) Hin) as B. cbn [fst snd] in F0, F1, Nx, B.
  assert (Hs : Rabs ((b2r x0 + b2r x1) * b2r c) <= bpow radix2 (emax - 1)).
  { rewrite Rabs_mult, (Rabs_pos_eq (b2r c)) by exact Pc0.
    apply Rle_trans with (bpow radix2 (emax - 2)).
    - apply Rle_trans with (2 := Rle_trans _ _ _ (Rle_abs _) B). apply Rmult_le_compat_r. exact Pc0.
      lra.
    - apply bpow_le. lia. }
  generalize (mul_pow2_2_ieee_finite_any prec emax prec_gt_0_ prec_lt_emax_ nan_plus nan_minus
                (fun x => nan_plus x x) nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Hs).
  unfold IeeeFoldModel.bv_mul_pow2_2_step, IeeeModel.bv_mul_pow2_step_2, IeeeModel.mul_pow2_2.
  cbn [fst snd]. cbv zeta.
  destruct (IeeeModel.fast_two_sum prec emax nan_plus nan_minus (prod x0 c) (prod x1 c)) as [z0 z1].
  cbn [fst]. intros [_ [Fz0 _]]. exact Fz0. }
destruct (seq_1_good prec emax nan_abs (map fst ws) Fws) as [M [Fm Eok]].
set (s := fold_seq step_1 zero_state (map fst ws)) in *.
set (ex := fold_seq (fun m_ e_ => andb m_ (snd e_)) true es).
set (rz := IeeeModel.bv_mul_pow2_radius prec emax nan_plus nan_minus nan_fma (fst s) ex rx c).
assert (Frz : fin rz).
{ unfold rz, IeeeModel.bv_mul_pow2_radius. cbv zeta.
  set (q := andb ex (orb (flt Nc (prod rx c)) (feq rx pzero))).
  assert (Fs : fin (if q then prod rx c else fsucc (fsucc (prod rx c)))).
  { apply (radius_pow2_fin prec emax nan_fma Hp2 rx c q Frx Fc). split.
    - apply Rmult_le_pos; assumption.
    - rewrite Rabs_pos_eq in Hr by (apply Rmult_le_pos; assumption). exact Hr. }
  destruct (sub_spec prec emax nan_minus (fst s) (fst s) Fm Fm) as [S V].
  replace (b2r (fst s) - b2r (fst s)) with 0 in S, V by ring.
  rewrite round_0 in S, V by auto with typeclass_instances.
  assert (Fd : fin (sub (fst s) (fst s))).
  { apply S. unfold inrange. rewrite Rabs_R0. apply bpow_gt_0. }
  destruct (add_spec prec emax nan_plus _ _ Fs Fd) as [Sa _].
  apply Sa. rewrite (V Fd), Rplus_0_r, round_generic by (auto with typeclass_instances; apply b2r_format).
  apply b2r_inrange. }
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (snd s)) as [r flag].
intros [H1 _]. cbn [snd]. apply H1. split; assumption.
Qed.

End IeeeBvPow2.

(** * The generated statements of the steps *)

Theorem bv_mul_pow2_step_1_ieee_correct : bv_mul_pow2_step_1_ieee_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma Hp1 x c Fx Fc Pc.
generalize (step_1_values prec emax nan_abs nan_fma x c Fx Fc)
           (bv_mul_pow2_step_1_correct (ieee_emin prec emax) prec Hp1 (val x) (val c)
              (val_format prec emax x) (val_format prec emax c) Pc).
unfold ieee_emin, val.
destruct (IeeeModel.bv_mul_pow2_step_1 prec emax nan_abs nan_fma x c) as [z e]. cbn [fst snd].
intros V R Fz. destruct (V Fz) as [_ E]. rewrite <- E in R. destruct R as [_ R]. exact R.
Qed.

Theorem bv_mul_pow2_step_2_ieee_correct : bv_mul_pow2_step_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Pc.
generalize (step_2_values prec emax nan_plus nan_minus nan_abs nan_fma Hp2 x0 x1 c F0 F1 Fc Nx Pc)
           (bv_mul_pow2_step_2_correct (ieee_emin prec emax) prec Hp2 (val x0) (val x1) (val c)
              Nx (val_format prec emax c) Pc).
unfold ieee_emin, val.
destruct (IeeeModel.bv_mul_pow2_step_2 prec emax nan_plus nan_minus nan_abs nan_fma x0 x1 c)
  as [[z0 z1] e]. cbn [fst snd].
intros V R Fz. destruct (V Fz) as [Fz1 E]. rewrite <- E in R. split. exact Fz1. exact R.
Qed.

Theorem bv_mul_pow2_step_1_ieee_lead : bv_mul_pow2_step_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_abs nan_fma x c.
generalize (step_1_lead prec emax nan_abs nan_fma x c).
destruct (IeeeModel.bv_mul_pow2_step_1 prec emax nan_abs nan_fma x c) as [z e]. exact (fun H => H).
Qed.

Theorem bv_mul_pow2_step_2_ieee_lead : bv_mul_pow2_step_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma x0 x1 c.
generalize (step_2_lead prec emax nan_plus nan_minus nan_abs nan_fma x0 x1 c).
destruct (IeeeModel.bv_mul_pow2_step_2 prec emax nan_plus nan_minus nan_abs nan_fma x0 x1 c)
  as [[z0 z1] e]. exact (fun H => H).
Qed.

(** * The lane order returns what the sequential order returns *)

Lemma bv_mul_pow2_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx c : binary_float prec emax) (xs : list (binary_float prec emax)),
  IeeeFoldModel.bv_mul_pow2_1_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx c xs =
  IeeeFoldModel.bv_mul_pow2_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs.
Proof.
intros. unfold IeeeFoldModel.bv_mul_pow2_1_lanes, IeeeFoldModel.bv_mul_pow2_1_seq. cbv zeta.
change (IeeeFoldModel.bv_mul_pow2_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_mul_pow2_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
rewrite norm_upper_1_lanes_seq_state.
rewrite (fold_lanes_and _ (fun e_ : binary_float prec emax * bool => snd e_)).
rewrite (fold_seq_and _ (fun e_ : binary_float prec emax * bool => snd e_)).
reflexivity.
Qed.

Lemma bv_mul_pow2_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx c : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_mul_pow2_2_lanes prec emax nan_plus nan_minus nan_abs nan_fma nan_const W rx c xs =
  IeeeFoldModel.bv_mul_pow2_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs.
Proof.
intros. unfold IeeeFoldModel.bv_mul_pow2_2_lanes, IeeeFoldModel.bv_mul_pow2_2_seq. cbv zeta.
change (IeeeFoldModel.bv_mul_pow2_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_mul_pow2_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
rewrite norm_upper_2_lanes_seq_state.
rewrite (fold_lanes_and _ (fun e_ : binary_float prec emax * binary_float prec emax * bool => snd e_)).
rewrite (fold_seq_and _ (fun e_ : binary_float prec emax * binary_float prec emax * bool => snd e_)).
reflexivity.
Qed.

(** * The generated statements of the folds *)

Theorem bv_mul_pow2_1_seq_ieee_correct : bv_mul_pow2_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx c xs HX Fc Pc.
pose proof (IeeeBv.canonical_radius_1 prec emax rx _ _ HX) as Nrx.
assert (V4 : finite rx -> finite c -> Rabs (val rx * val c) <= bpow radix2 (emax - 2) ->
             Forall (fun x => Rabs (((Rabs (val x)) + val rx) * val c) <= bpow radix2 (emax - 2)) xs ->
             snd (IeeeFoldModel.bv_mul_pow2_1_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const
                    rx c xs) = true).
{ intros Frx _ Hr Hx.
  destruct HX as [[_ [Prx B]]|[E _]]; [|rewrite E in Frx; discriminate Frx].
  apply (bv_mul_pow2_1_finite prec emax nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx c xs);
    trivial.
  revert B. apply Forall_impl. intros x [Fx _]. exact Fx. }
destruct (bv_mul_pow2_1_result prec emax nan_plus nan_minus nan_abs nan_fma nan_const rx c xs Nrx Fc Pc)
  as [[rz [Frz [Prz [Frx [Hz [Vr E]]]]]]|E]; rewrite E in V4 |- *; cbv beta iota.
- (* a finite result: the real model's on the values *)
  assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs).
  { destruct HX as [[_ [P B]]|[Ei _]]. split; assumption. rewrite Ei in Frx. discriminate Frx. }
  destruct Bx as [Px Bx].
  assert (Fv : Forall (fun x => fmt (ieee_emin prec emax) prec x) (map (fun x => val x) xs)).
  { apply Forall_map. apply Forall_forall. intros x _. apply val_format. }
  destruct (bv_mul_pow2_1_correct (ieee_emin prec emax) prec Hp2 (val rx) (val c)
              (map (fun x => val x) xs) (val_format prec emax rx) Px (val_format prec emax c) Pc Fv)
    as [_ [Cont Exact]].
  assert (Vr' : FoldModel.bv_mul_pow2_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val c)
                  (map (fun x => val x) xs) = val rz) by (symmetry; exact Vr).
  rewrite Vr' in Cont, Exact.
  unfold FoldModel.bv_mul_pow2_1_map in Cont, Exact.
  apply Forall2_map_r_inv, Forall_map_inv in Cont.
  assert (Vz : forall x, In x xs ->
    val (fst (IeeeFoldModel.bv_mul_pow2_1_step prec emax nan_abs nan_fma c x)) =
    fst (FoldModel.bv_mul_pow2_1_step (ieee_emin prec emax) prec tie_even (val c) (val x))).
  { intros x Hin. destruct (proj1 (Forall_forall _ xs) Hz x Hin) as [_ [_ V]].
    unfold FoldModel.bv_mul_pow2_1_step. unfold ieee_emin, val. rewrite <- V. reflexivity. }
  rewrite map_map.
  split.
  { left. split. exact Frz. split. exact Prz. apply Forall_map. apply Forall_forall. intros x Hin.
    split. exact (proj1 (proj2 (proj1 (Forall_forall _ xs) Hz x Hin))). split. exact Frz. exact Prz. }
  split; [split; intros _; [exact Frz|reflexivity]|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros x Hin. cbv zeta.
    intros x_ [[_ Ei]|[_ D]]. { rewrite Ei in Frx. discriminate Frx. }
    right. split.
    * split. exact (proj1 (proj2 (proj1 (Forall_forall _ xs) Hz x Hin))). split. exact Frz. exact Prz.
    * rewrite (Vz x Hin). exact (proj2 (proj1 (Forall_forall _ xs) Cont x Hin) x_ D).
  + intros _ Cr Cx.
    assert (Cx' : Forall (fun x => x * val c = 0 \/ eta (ieee_emin prec emax) / (2 * u prec) <
                                    Rabs (x * val c)) (map (fun x => val x) xs))
      by (apply Forall_map; exact Cx).
    specialize (Exact Cr Cx'). apply Forall2_map_r_inv, Forall_map_inv in Exact.
    apply Forall2_map_r. apply Forall_forall. intros x Hin. cbv zeta.
    intros v_ [[_ Ei]|[_ D]]. { rewrite Ei in Frz. discriminate Frz. }
    rewrite (Vz x Hin) in D.
    destruct (proj1 (Forall_forall _ xs) Exact x Hin v_ D) as [x_ [Dx Ev]].
    exists x_. split; [|exact Ev]. right. split. exact (proj1 (Forall_forall _ xs) Bx x Hin). exact Dx.
  + intros _. split. exact Frx. split. exact Fc. split; [|exact Vr].
    apply Forall2_map_r. apply Forall_forall. intros x Hin. cbv zeta. exact (Vz x Hin).
  + intros _ _ _ _. exact Frz.
- (* the whole space *)
  rewrite !map_map.
  split.
  { right. split. reflexivity. apply Forall_map. apply Forall_forall. intros x _.
    split. exists false. reflexivity. reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros x _. cbv zeta. intros x_ _. left.
    split. exists false. reflexivity. reflexivity.
  + intros F. discriminate F.
  + intros F. discriminate F.
  + intros Frx Fc' Hr Hx. specialize (V4 Frx Fc' Hr Hx). discriminate V4.
Qed.

Theorem bv_mul_pow2_1_lanes_ieee_correct : bv_mul_pow2_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 W rx c xs HX Fc Pc.
rewrite (bv_mul_pow2_1_lanes_seq_ieee prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const
           W rx c xs).
exact (bv_mul_pow2_1_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const
         Hp2 rx c xs HX Fc Pc).
Qed.

Theorem bv_mul_pow2_2_seq_ieee_correct : bv_mul_pow2_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx c xs HX Fc Pc.
pose proof (IeeeBv.canonical_radius_1 prec emax rx _ _ HX) as Nrx.
pose proof (IeeeBv.canonical_operands_2 prec emax rx _ (fun x => x) xs HX) as Hc.
assert (V4 : finite rx -> finite c -> Rabs (val rx * val c) <= bpow radix2 (emax - 2) ->
             Forall (fun x => let '(x0, x1) := x in
                     Rabs (((Rabs (val x0 + val x1)) + val rx) * val c) <= bpow radix2 (emax - 2)) xs ->
             snd (IeeeFoldModel.bv_mul_pow2_2_seq prec emax nan_plus nan_minus nan_abs nan_fma nan_const
                    rx c xs) = true).
{ intros Frx _ Hr Hx.
  destruct HX as [[_ [Prx B]]|[E _]]; [|rewrite E in Frx; discriminate Frx].
  apply (bv_mul_pow2_2_finite prec emax nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx c xs);
    trivial.
  - revert B. apply Forall_impl. intros x [F0 [F1 [Nx _]]]. split. exact F0. split. exact F1. exact Nx.
  - revert Hx. apply Forall_impl. intros [x0 x1] Bx. exact Bx. }
destruct (bv_mul_pow2_2_result prec emax nan_plus nan_minus nan_abs nan_fma nan_const Hp2 rx c xs Nrx Fc
            Pc Hc)
  as [[rz [Frz [Prz [Frx [Hz [Vr E]]]]]]|E]; rewrite E in V4 |- *; cbv beta iota.
- (* a finite result: the real model's on the values *)
  assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs).
  { destruct HX as [[_ [P B]]|[Ei _]]. split; assumption. rewrite Ei in Frx. discriminate Frx. }
  destruct Bx as [Px Bx].
  assert (Fv : Forall (fun x => normalized_2 (ieee_emin prec emax) prec (fst x) (snd x))
                      (map (fun x => (val (fst x), val (snd x))) xs)).
  { apply Forall_map. revert Bx. apply Forall_impl. intros x [_ [_ [N _]]]. exact N. }
  destruct (bv_mul_pow2_2_correct (ieee_emin prec emax) prec Hp2 (val rx) (val c)
              (map (fun x => (val (fst x), val (snd x))) xs) (val_format prec emax rx) Px
              (val_format prec emax c) Pc Fv)
    as [_ [Cont Exact]].
  assert (Vr' : FoldModel.bv_mul_pow2_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val c)
                  (map (fun x => (val (fst x), val (snd x))) xs) = val rz) by (symmetry; exact Vr).
  rewrite Vr' in Cont, Exact.
  unfold FoldModel.bv_mul_pow2_2_map in Cont, Exact.
  apply Forall2_map_r_inv, Forall_map_inv in Cont.
  (* entry by entry, in the values of the center written *)
  assert (Ez : forall x0 x1, In (x0, x1) xs ->
    let w := fst (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c
                    (x0, x1)) in
    finite (fst w) /\ finite (snd w) /\
    (val (fst w), val (snd w)) =
      fst (bv_mul_pow2_step_2 (ieee_emin prec emax) prec tie_even (val x0) (val x1) (val c))).
  { intros x0 x1 Hin. pose proof (proj1 (Forall_forall _ xs) Hz (x0, x1) Hin) as Hzx.
    cbn [fst snd] in Hzx. cbv zeta. revert Hzx.
    destruct (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c (x0, x1))
      as [[z0 z1] e]. cbn [fst snd]. intros [_ [_ [_ [Fz0 [Fz1 V]]]]].
    split. exact Fz0. split. exact Fz1. unfold ieee_emin, val. rewrite <- V. reflexivity. }
  rewrite map_map.
  split.
  { left. split. exact Frz. split. exact Prz. apply Forall_map. apply Forall_forall. intros [x0 x1] Hin.
    pose proof (proj1 (Forall_forall _ xs) Cont (x0, x1) Hin) as Cx. cbn [fst snd] in Cx.
    destruct (Ez x0 x1 Hin) as [Fz0 [Fz1 V]]. revert Fz0 Fz1 V Cx. cbv zeta.
    destruct (fst (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c
                     (x0, x1))) as [z0 z1].
    cbn [fst snd]. intros Fz0 Fz1 V Cx. unfold FoldModel.bv_mul_pow2_2_step in Cx. cbn [fst snd] in Cx.
    rewrite <- V in Cx. cbv beta iota in Cx.
    split. exact Fz0. split. exact Fz1. split. exact (proj1 Cx). split. exact Frz. exact Prz. }
  split; [split; intros _; [exact Frz|reflexivity]|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
    pose proof (proj1 (Forall_forall _ xs) Cont (x0, x1) Hin) as Cx. cbn [fst snd] in Cx.
    destruct (Ez x0 x1 Hin) as [Fz0 [Fz1 V]]. revert Fz0 Fz1 V Cx. cbv zeta.
    destruct (fst (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c
                     (x0, x1))) as [z0 z1].
    cbn [fst snd]. intros Fz0 Fz1 V Cx. unfold FoldModel.bv_mul_pow2_2_step in Cx. cbn [fst snd] in Cx.
    rewrite <- V in Cx. cbv beta iota in Cx. cbv beta iota.
    intros x_ [[_ [_ Ei]]|[_ D]]. { rewrite Ei in Frx. discriminate Frx. }
    right. split.
    * split. exact Fz0. split. exact Fz1. split. exact (proj1 Cx). split. exact Frz. exact Prz.
    * exact (proj2 Cx x_ D).
  + intros _ Cr Cx.
    assert (Cx' : Forall (fun x => let '(x0, x1) := x in
                     (x0 * val c = 0 \/ eta (ieee_emin prec emax) / (2 * u prec) < Rabs (x0 * val c)) /\
                     (x1 * val c = 0 \/ eta (ieee_emin prec emax) / (2 * u prec) < Rabs (x1 * val c)))
                  (map (fun x => (val (fst x), val (snd x))) xs)).
    { apply Forall_map. revert Cx. apply Forall_impl. intros [x0 x1] C. exact C. }
    specialize (Exact Cr Cx'). apply Forall2_map_r_inv, Forall_map_inv in Exact.
    apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
    pose proof (proj1 (Forall_forall _ xs) Exact (x0, x1) Hin) as Xx. cbn [fst snd] in Xx.
    pose proof (proj1 (Forall_forall _ xs) Bx (x0, x1) Hin) as Bxx. cbn [fst snd] in Bxx.
    destruct (Ez x0 x1 Hin) as [Fz0 [Fz1 V]]. revert Fz0 Fz1 V Xx. cbv zeta.
    destruct (fst (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c
                     (x0, x1))) as [z0 z1].
    cbn [fst snd]. intros Fz0 Fz1 V Xx. unfold FoldModel.bv_mul_pow2_2_step in Xx. cbn [fst snd] in Xx.
    rewrite <- V in Xx. cbv beta iota in Xx. cbv beta iota.
    intros v_ [[_ [_ Ei]]|[_ D]]. { rewrite Ei in Frz. discriminate Frz. }
    destruct (Xx v_ D) as [x_ [Dx Ev]].
    exists x_. split; [|exact Ev]. right. split. exact Bxx. exact Dx.
  + intros _. split. exact Frx. split. exact Fc. split; [|exact Vr].
    apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
    destruct (Ez x0 x1 Hin) as [_ [_ V]]. revert V. cbv zeta.
    destruct (fst (IeeeFoldModel.bv_mul_pow2_2_step prec emax nan_plus nan_minus nan_abs nan_fma c
                     (x0, x1))) as [z0 z1].
    cbn [fst snd]. intros V. cbv beta iota. exact V.
  + intros _ _ _ _. exact Frz.
- (* the whole space *)
  rewrite !map_map.
  split.
  { right. split. reflexivity. apply Forall_map. apply Forall_forall. intros x _. cbn [fst snd].
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros [x0 x1] _. cbv beta iota zeta. intros x_ _. left.
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity.
  + intros F. discriminate F.
  + intros F. discriminate F.
  + intros Frx Fc' Hr Hx. specialize (V4 Frx Fc' Hr Hx). discriminate V4.
Qed.

Theorem bv_mul_pow2_2_lanes_ieee_correct : bv_mul_pow2_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const Hp2 W rx c xs HX Fc Pc.
rewrite (bv_mul_pow2_2_lanes_seq_ieee prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const
           W rx c xs).
exact (bv_mul_pow2_2_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_fma nan_const
         Hp2 rx c xs HX Fc Pc).
Qed.
