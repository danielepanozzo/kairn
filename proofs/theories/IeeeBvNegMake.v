(* The negation and the constructor of a ball vector in the IEEE model: the generated
   statements of their kernels (proofs/gen/IeeeStatements.v, the steps' leading limbs in
   proofs/gen/IeeeFoldStatements.v) and of the folds bv_neg_k and bv_make_k in both orders
   (proofs/gen/IeeeFoldStatements.v).

   The kernels.
   - neg_1 and bv_center_entry_1, of one instruction each (a negation, a guard): their
     bridges by the cone of the result, as for the steps of the maps (bridge_cone of
     IeeeMapSteps.v), and their leading limbs (a negation and a guard keep finiteness).
   - bv_center_2 copies a pair; neg_2 negates both limbs (its leading limb).
   - bv_make_finish: norm_finish_1 under ok and le(+0, rz); le of two finite numbers is the
     order of their values, so the flag is true exactly when ok holds and rz is finite and
     not negative.

   The negation of a ball vector (bv_neg_k). A canonical operand has finite centers (a
   finite ball vector) or zero ones (the whole space), and so has its negation: every center
   written is finite, so the state of the record is finite with a true mask
   (seq_1_good of IeeeFoldNorm.v), the radius kernel returns rx, and the finish's flag is
   true exactly when rx is finite. So the result is (the negated centers, rx, true) for a
   finite ball vector and the whole space for the whole space (bv_neg_k_result), and every
   clause follows: the ball of a negated center with radius rx is exactly the image of the
   ball of the center (neg_ball_image of BvNegMake.v, on the values).

   The constructor (bv_make_k). The radius kernel returns, for a finite m and a finite r, a
   finite number of the value of r (m - m is a finite zero, r + 0 is r); a finite radius
   comes from a finite m and a finite r (make_radius_ieee). The record's state is finite
   with a true mask exactly when every center written is finite (seq_1_state,
   seq_1_good), and a center written is finite exactly when the center given is (a guard,
   or a copy). So the flag of bv_make_finish is true exactly when r is finite and not
   negative and every center given is finite, and then the result is the centers and the
   radius given (bv_make_k_result); otherwise it is the whole space.

   The lane order returns what the sequential order returns (norm_upper_k_lanes_seq_state),
   so its statements are those of the sequential order. *)
From Stdlib Require Import Reals ZArith List Lia Lra Bool.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldModel FoldStatements
  IeeeFoldStatements.
From Kairn Require Import Format Normalized Folds Program IeeeBridge IeeeVocabulary IeeeOps
  FoldTransfer IeeeFoldNorm IeeeMapSteps BvNegMake.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

(** * The kernels *)

Theorem neg_1_ieee_bridge : neg_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 x Fx. cbv zeta. intros Fz.
assert (EB : IeeeModel.neg_1 prec emax nan_opp x =
             nth 1 (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma) IeeeModel.neg_1_prog
                      [x]) (d0 prec emax)).
{ cbv [IeeeModel.neg_1 run stepB nth app IeeeModel.neg_1_prog]. reflexivity. }
assert (ER : neg_1 (val x) =
             nth 1 (runR (ieee_emin prec emax) prec tie_even IeeeModel.neg_1_prog [val x]) 0).
{ cbv [neg_1 runR run stepR nth app IeeeModel.neg_1_prog]. reflexivity. }
rewrite EB in Fz |- *. rewrite ER.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem bv_center_entry_1_ieee_bridge : bv_center_entry_1_ieee_bridge_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_fma Hp1 c Fc. cbv zeta. intros Fz.
assert (EB : IeeeModel.bv_center_entry_1 prec emax nan_plus c =
             nth 1 (run (stepB prec emax nan_plus nan_minus nan_opp nan_fma)
                      IeeeModel.bv_center_entry_1_prog [c]) (d0 prec emax)).
{ cbv [IeeeModel.bv_center_entry_1 run stepB nth app IeeeModel.bv_center_entry_1_prog].
  reflexivity. }
assert (ER : bv_center_entry_1 (ieee_emin prec emax) prec tie_even (val c) =
             nth 1 (runR (ieee_emin prec emax) prec tie_even IeeeModel.bv_center_entry_1_prog
                      [val c]) 0).
{ cbv [bv_center_entry_1 runR run stepR nth app IeeeModel.bv_center_entry_1_prog]. reflexivity. }
rewrite EB in Fz |- *. rewrite ER.
apply (bridge_cone prec emax nan_plus nan_minus nan_opp nan_fma).
- repeat constructor; assumption.
- reflexivity.
- reflexivity.
- exact Fz.
Qed.

Theorem neg_1_ieee_lead : neg_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_opp x. cbv zeta. unfold IeeeModel.neg_1, finite. cbv zeta.
unfold IeeeOperations.neg. rewrite is_finite_Bopp. exact (fun F => F).
Qed.

Theorem bv_center_entry_1_ieee_lead : bv_center_entry_1_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus c. cbv zeta. unfold IeeeModel.bv_center_entry_1, finite. cbv zeta.
rewrite (guard_finite prec emax nan_plus). exact (fun F => F).
Qed.

(* The leading limb of neg_2, the step of bv_neg_2 (a kernel of the extended domain, whose
   description cannot name this theorem). *)
Theorem neg_2_ieee_lead : neg_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_opp x0 x1. unfold IeeeModel.neg_2. cbv zeta. unfold finite.
unfold IeeeOperations.neg. rewrite is_finite_Bopp. exact (fun F => F).
Qed.

Theorem bv_center_2_ieee_correct : bv_center_2_ieee_spec.
Proof.
intros prec emax Hp He Hp1 x0 x1 H. unfold IeeeModel.bv_center_2. cbv beta iota zeta.
split. exact H. split. reflexivity. intros _. split; reflexivity.
Qed.

(* The leading limb of bv_center_2 (a kernel of the extended domain, whose description
   cannot name this theorem). *)
Theorem bv_center_2_ieee_lead : bv_center_2_ieee_lead_spec.
Proof.
intros prec emax Hp He x0 x1. unfold IeeeModel.bv_center_2. cbv beta iota zeta.
exact (fun F => F).
Qed.

(* The guard of each limb of a canonical pair (rule R3, bv_center_entry_2): a finite limb keeps
   its value, an infinity stays itself, a zero becomes +0 and a NaN stays a NaN, so the pair stays
   canonical and stands for the same extended real number. *)
Lemma guard_canonical_2 (prec emax : Z) {prec_gt_0_ : Prec_gt_0 prec}
    {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax} (nan_plus : nan2 prec emax)
    (c0 c1 : binary_float prec emax) :
  canonical_2 c0 c1 ->
  canonical_2 (IeeeOperations.guard prec emax nan_plus c0) (IeeeOperations.guard prec emax nan_plus c1) /\
  xval_2 (IeeeOperations.guard prec emax nan_plus c0) (IeeeOperations.guard prec emax nan_plus c1) =
  xval_2 c0 c1.
Proof.
intros [[F0 [F1 N]]|[[[s Ei] [s' Ez]]|[N0 N1]]].
- assert (G0 : finite (IeeeOperations.guard prec emax nan_plus c0))
    by (unfold finite; rewrite (guard_finite prec emax nan_plus); exact F0).
  assert (G1 : finite (IeeeOperations.guard prec emax nan_plus c1))
    by (unfold finite; rewrite (guard_finite prec emax nan_plus); exact F1).
  assert (V0 : val (IeeeOperations.guard prec emax nan_plus c0) = val c0)
    by exact (guard_val prec emax nan_plus c0).
  assert (V1 : val (IeeeOperations.guard prec emax nan_plus c1) = val c1)
    by exact (guard_val prec emax nan_plus c1).
  split.
  + left. split. exact G0. split. exact G1. rewrite V0, V1. exact N.
  + unfold xval_2. unfold finite in F0, G0. rewrite G0, F0, V0, V1. reflexivity.
- subst c0 c1. unfold infinity.
  rewrite (guard_inf prec emax nan_plus s), (guard_zero prec emax nan_plus s').
  split; [|reflexivity]. right. left. split. exists s. reflexivity. exists false. reflexivity.
- unfold nan in N0, N1.
  assert (G0 : is_nan prec emax (IeeeOperations.guard prec emax nan_plus c0) = true)
    by (rewrite (guard_nan prec emax nan_plus); exact N0).
  assert (G1 : is_nan prec emax (IeeeOperations.guard prec emax nan_plus c1) = true)
    by (rewrite (guard_nan prec emax nan_plus); exact N1).
  split.
  + right. right. split. exact G0. exact G1.
  + unfold xval_2. rewrite (nan_not_finite prec emax _ G0), (nan_not_finite prec emax _ N0), G0, N0.
    reflexivity.
Qed.

(* bv_center_entry_2: bv_center_2 on the guarded limbs (rule R3), of the extended domain. *)
Theorem bv_center_entry_2_ieee_correct : bv_center_entry_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus Hp1 c0 c1 H.
unfold IeeeModel.bv_center_entry_2, IeeeModel.bv_center_2. cbv beta iota zeta.
destruct (guard_canonical_2 prec emax nan_plus c0 c1 H) as [C X].
split. exact C. split. exact X.
intros _. split; apply (guard_val prec emax nan_plus).
Qed.

Theorem bv_center_entry_2_ieee_lead : bv_center_entry_2_ieee_lead_spec.
Proof.
intros prec emax Hp He nan_plus c0 c1.
unfold IeeeModel.bv_center_entry_2, IeeeModel.bv_center_2. cbv beta iota zeta.
unfold finite. rewrite (guard_finite prec emax nan_plus). exact (fun F => F).
Qed.

Theorem bv_make_finish_correct : bv_make_finish_spec.
Proof.
intros prec emax Hp He nan_abs nan_const rz ok. unfold IeeeModel.bv_make_finish. cbv zeta.
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz
              (ok && IeeeOperations.le prec emax (IeeeOperations.pzero prec emax) rz)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz
            (ok && IeeeOperations.le prec emax (IeeeOperations.pzero prec emax) rz)) as [r flag].
intros [H1 [H2 H3]]. split; [|split; assumption].
rewrite H1. rewrite andb_true_iff. split.
- intros [[Eok Ele] Fz]. split. exact Eok. split. exact Fz.
  rewrite (le_finite prec emax (IeeeOperations.pzero prec emax) rz eq_refl Fz) in Ele.
  destruct (Rle_bool_spec (B2R prec emax (IeeeOperations.pzero prec emax)) (B2R prec emax rz))
    as [P|P]; [exact P|discriminate Ele].
- intros [Eok [Fz Pz]]. split; [split|]; try assumption.
  rewrite (le_finite prec emax (IeeeOperations.pzero prec emax) rz eq_refl Fz). apply Rle_bool_true. exact Pz.
Qed.

(** * The folds *)

Section IeeeBvNegMake.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_const : nan_of.

Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation pinf := (IeeeOperations.pinf prec emax).
Notation fneg := (IeeeOperations.neg prec emax nan_opp).
Notation step_1 := (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
Notation zero_state := (pzero, true).

Lemma neg_val : forall x : float, b2r (fneg x) = - b2r x.
Proof. intros x. apply B2R_Bopp. Qed.

Lemma neg_fin : forall x : float, is_finite prec emax (fneg x) = is_finite prec emax x.
Proof. intros x. apply is_finite_Bopp. Qed.

Lemma zero_fin : forall x : float, zero x -> fin x.
Proof. intros x [s ->]. reflexivity. Qed.

Lemma neg_zero : forall x : float, zero x -> zero (fneg x).
Proof. intros x [s ->]. exists (negb s). reflexivity. Qed.

(* The record of two limbs reads the leading limbs. *)
Lemma record_2_seq :
  forall ws : list (float * float),
  fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs) zero_state ws =
  fold_seq step_1 zero_state (map fst ws).
Proof.
intros ws. rewrite <- (fold_seq_map _ _ _ step_1 fst zero_state ws).
apply fold_seq_ext. intros t x. reflexivity.
Qed.

(** ** The negation *)

Lemma bv_neg_1_result :
  forall (rx : float) (xs : list float),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
   (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  let ws := map (IeeeFoldModel.bv_neg_1_step prec emax nan_opp) xs in
  (finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs /\
   IeeeFoldModel.bv_neg_1_seq prec emax nan_opp nan_abs nan_const rx xs = (ws, rx, true)) \/
  (rx = pinf /\ Forall (fun x => ball_whole_1 x rx) xs /\
   IeeeFoldModel.bv_neg_1_seq prec emax nan_opp nan_abs nan_const rx xs =
     (map (fun _ => pzero) ws, pinf, false)).
Proof.
intros rx xs HX ws.
assert (Fws : Forall (fun w => fin w) ws).
{ unfold ws. apply Forall_map.
  destruct HX as [[_ [_ B]]|[_ B]]; revert B; apply Forall_impl; intros x Bx;
    unfold IeeeFoldModel.bv_neg_1_step, IeeeModel.neg_1; cbv zeta; rewrite neg_fin.
  - exact (proj1 Bx).
  - exact (zero_fin x (proj1 Bx)). }
destruct (seq_1_good prec emax nan_abs ws Fws) as [_ [_ Eok]].
unfold IeeeFoldModel.bv_neg_1_seq. cbv zeta. fold ws.
change (IeeeFoldModel.bv_neg_1_record prec emax nan_abs) with step_1.
unfold IeeeModel.bv_neg_radius. cbv zeta.
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rx
              (snd (fold_seq step_1 zero_state ws))).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rx
            (snd (fold_seq step_1 zero_state ws))) as [r flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct HX as [[Frx [Prx B]]|[Erx B]].
- left. split. exact Frx. split. exact Prx. split. exact B.
  assert (Ef : flag = true) by (apply H1; split; assumption).
  rewrite Ef, (H2 Ef). reflexivity.
- right. split. exact Erx. split. exact B.
  destruct flag.
  + destruct (proj1 H1 eq_refl) as [_ F]. rewrite Erx in F. discriminate F.
  + reflexivity.
Qed.

Lemma bv_neg_2_result :
  forall (rx : float) (xs : list (float * float)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
   (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  let ws := map (IeeeFoldModel.bv_neg_2_step prec emax nan_opp) xs in
  (finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs /\
   IeeeFoldModel.bv_neg_2_seq prec emax nan_opp nan_abs nan_const rx xs = (ws, rx, true)) \/
  (rx = pinf /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs /\
   IeeeFoldModel.bv_neg_2_seq prec emax nan_opp nan_abs nan_const rx xs =
     (map (fun _ => (pzero, pzero)) ws, pinf, false)).
Proof.
intros rx xs HX ws.
assert (Fws : Forall (fun w => fin w) (map fst ws)).
{ unfold ws. rewrite map_map. apply Forall_map.
  destruct HX as [[_ [_ B]]|[_ B]]; revert B; apply Forall_impl; intros x Bx;
    unfold IeeeFoldModel.bv_neg_2_step, IeeeModel.neg_2; cbv zeta; cbn [fst]; rewrite neg_fin.
  - exact (proj1 Bx).
  - exact (zero_fin _ (proj1 Bx)). }
destruct (seq_1_good prec emax nan_abs (map fst ws) Fws) as [_ [_ Eok]].
unfold IeeeFoldModel.bv_neg_2_seq. cbv zeta. fold ws.
change (IeeeFoldModel.bv_neg_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
rewrite record_2_seq.
unfold IeeeModel.bv_neg_radius. cbv zeta.
generalize (norm_finish_1_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rx
              (snd (fold_seq step_1 zero_state (map fst ws)))).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rx
            (snd (fold_seq step_1 zero_state (map fst ws)))) as [r flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct HX as [[Frx [Prx B]]|[Erx B]].
- left. split. exact Frx. split. exact Prx. split. exact B.
  assert (Ef : flag = true) by (apply H1; split; assumption).
  rewrite Ef, (H2 Ef). reflexivity.
- right. split. exact Erx. split. exact B.
  destruct flag.
  + destruct (proj1 H1 eq_refl) as [_ F]. rewrite Erx in F. discriminate F.
  + reflexivity.
Qed.

(** ** The constructor *)

(* The radius kernel of the constructor: finite only from a finite m and a finite r, and
   then, and for every finite m and r, the value of r. *)
Lemma make_radius_ieee :
  forall m r : float,
  let rz := IeeeModel.bv_make_radius prec emax nan_plus nan_minus m r in
  (fin rz -> fin m /\ fin r) /\ (fin m -> fin r -> fin rz /\ b2r rz = b2r r).
Proof.
intros m r. unfold IeeeModel.bv_make_radius. cbv zeta. split.
- intros F. destruct (add_finite_inv prec emax nan_plus _ _ F) as [Fg Fd].
  destruct (sub_finite_inv prec emax nan_minus _ _ Fd)
    as [Fm _].
  split. exact Fm. rewrite (guard_finite prec emax nan_plus) in Fg. exact Fg.
- intros Fm Fr.
  assert (Fg : fin (IeeeOperations.guard prec emax nan_plus r))
    by (rewrite (guard_finite prec emax nan_plus); exact Fr).
  assert (Vg : b2r (IeeeOperations.guard prec emax nan_plus r) = b2r r)
    by apply (guard_val prec emax nan_plus).
  destruct (sub_spec prec emax nan_minus m m Fm Fm)
    as [Sd Vd].
  replace (b2r m - b2r m) with 0 in Sd, Vd by ring.
  rewrite round_0 in Sd, Vd by auto with typeclass_instances.
  assert (Fd : fin (IeeeOperations.sub prec emax nan_minus m m)).
  { apply Sd. unfold inrange. rewrite Rabs_R0. apply bpow_gt_0. }
  destruct (add_spec prec emax nan_plus _ _ Fg Fd)
    as [Sa Va].
  rewrite (Vd Fd), Vg, Rplus_0_r in Sa, Va.
  rewrite round_generic in Sa, Va by (auto with typeclass_instances; apply b2r_format).
  assert (Fz : fin (IeeeOperations.add prec emax nan_plus (IeeeOperations.guard prec emax nan_plus r)
                      (IeeeOperations.sub prec emax nan_minus m m))).
  { apply Sa. apply b2r_inrange. }
  split. exact Fz. exact (Va Fz).
Qed.

Lemma bv_make_1_result :
  forall (r : float) (cs : list float),
  let ws := map (IeeeFoldModel.bv_make_1_step prec emax nan_plus) cs in
  (finite r /\ 0 <= val r /\ Forall (fun c => finite c) cs /\
   exists rz, finite rz /\ val rz = val r /\
   IeeeFoldModel.bv_make_1_seq prec emax nan_plus nan_minus nan_abs nan_const r cs = (ws, rz, true))
  \/
  (~ (finite r /\ 0 <= val r /\ Forall (fun c => finite c) cs) /\
   IeeeFoldModel.bv_make_1_seq prec emax nan_plus nan_minus nan_abs nan_const r cs =
     (map (fun _ => pzero) ws, pinf, false)).
Proof.
intros r cs ws.
assert (Ews : forall c, fin (IeeeFoldModel.bv_make_1_step prec emax nan_plus c) <-> fin c).
{ intros c. unfold IeeeFoldModel.bv_make_1_step, IeeeModel.bv_center_entry_1. cbv zeta.
  rewrite (guard_finite prec emax nan_plus). reflexivity. }
unfold IeeeFoldModel.bv_make_1_seq. cbv zeta. fold ws.
change (IeeeFoldModel.bv_make_1_record prec emax nan_abs) with step_1.
destruct (seq_1_state prec emax nan_abs ws) as [_ HS].
set (s := fold_seq step_1 zero_state ws) in *.
set (rz := IeeeModel.bv_make_radius prec emax nan_plus nan_minus (fst s) r).
destruct (make_radius_ieee (fst s) r) as [R1 R2]. fold rz in R1, R2.
generalize (bv_make_finish_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.bv_make_finish prec emax nan_abs nan_const rz (snd s)) as [rr flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct flag.
- left. destruct (proj1 H1 eq_refl) as [Eok [Frz Prz]].
  destruct (R1 Frz) as [Fm Fr]. destruct (R2 Fm Fr) as [_ Vrz].
  destruct (HS Fm Eok) as [Fws _].
  split. exact Fr. split. unfold val. rewrite <- Vrz. exact Prz. split.
  + unfold ws in Fws. apply Forall_map_inv in Fws. revert Fws. apply Forall_impl.
    intros c Fc. exact (proj1 (Ews c) Fc).
  + exists rz. split. exact Frz. split. exact Vrz. rewrite (H2 eq_refl). reflexivity.
- right. split; [|reflexivity]. intros [Fr [Pr Fc]].
  assert (Fws : Forall (fun w => fin w) ws).
  { unfold ws. apply Forall_map. revert Fc. apply Forall_impl. intros c F. exact (proj2 (Ews c) F). }
  destruct (seq_1_good prec emax nan_abs ws Fws) as [_ [Fm Eok]].
  destruct (R2 Fm Fr) as [Frz Vrz].
  assert (E : false = true).
  { apply H1. split. exact Eok. split. exact Frz. unfold val. rewrite Vrz. exact Pr. }
  discriminate E.
Qed.

Lemma bv_make_2_result :
  forall (r : float) (cs : list (float * float)),
  let ws := map (IeeeFoldModel.bv_make_2_step prec emax) cs in
  (finite r /\ 0 <= val r /\ Forall (fun c => finite (fst c)) cs /\
   exists rz, finite rz /\ val rz = val r /\
   IeeeFoldModel.bv_make_2_seq prec emax nan_plus nan_minus nan_abs nan_const r cs = (ws, rz, true))
  \/
  (~ (finite r /\ 0 <= val r /\ Forall (fun c => finite (fst c)) cs) /\
   IeeeFoldModel.bv_make_2_seq prec emax nan_plus nan_minus nan_abs nan_const r cs =
     (map (fun _ => (pzero, pzero)) ws, pinf, false)).
Proof.
intros r cs ws.
assert (Ews : map fst ws = map fst cs).
{ unfold ws. rewrite map_map. apply map_ext. intros c. reflexivity. }
unfold IeeeFoldModel.bv_make_2_seq. cbv zeta. fold ws.
change (IeeeFoldModel.bv_make_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
rewrite record_2_seq, Ews.
destruct (seq_1_state prec emax nan_abs (map fst cs)) as [_ HS].
set (s := fold_seq step_1 zero_state (map fst cs)) in *.
set (rz := IeeeModel.bv_make_radius prec emax nan_plus nan_minus (fst s) r).
destruct (make_radius_ieee (fst s) r) as [R1 R2]. fold rz in R1, R2.
generalize (bv_make_finish_correct prec emax prec_gt_0_ prec_lt_emax_ nan_abs nan_const rz (snd s)).
destruct (IeeeModel.bv_make_finish prec emax nan_abs nan_const rz (snd s)) as [rr flag].
intros [H1 [H2 _]]. cbn [fst snd].
destruct flag.
- left. destruct (proj1 H1 eq_refl) as [Eok [Frz Prz]].
  destruct (R1 Frz) as [Fm Fr]. destruct (R2 Fm Fr) as [_ Vrz].
  destruct (HS Fm Eok) as [Fcs _].
  split. exact Fr. split. unfold val. rewrite <- Vrz. exact Prz. split.
  + apply Forall_map_inv in Fcs. exact Fcs.
  + exists rz. split. exact Frz. split. exact Vrz. rewrite (H2 eq_refl). reflexivity.
- right. split; [|reflexivity]. intros [Fr [Pr Fc]].
  assert (Fcs : Forall (fun w => fin w) (map fst cs)) by (apply Forall_map; exact Fc).
  destruct (seq_1_good prec emax nan_abs (map fst cs) Fcs) as [_ [Fm Eok]].
  destruct (R2 Fm Fr) as [Frz Vrz].
  assert (E : false = true).
  { apply H1. split. exact Eok. split. exact Frz. unfold val. rewrite Vrz. exact Pr. }
  discriminate E.
Qed.

End IeeeBvNegMake.

(** * The lane order returns what the sequential order returns *)

Lemma bv_neg_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp nan_abs : nan1 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx : binary_float prec emax) (xs : list (binary_float prec emax)),
  IeeeFoldModel.bv_neg_1_lanes prec emax nan_opp nan_abs nan_const W rx xs =
  IeeeFoldModel.bv_neg_1_seq prec emax nan_opp nan_abs nan_const rx xs.
Proof.
intros. unfold IeeeFoldModel.bv_neg_1_lanes, IeeeFoldModel.bv_neg_1_seq. cbv zeta.
change (IeeeFoldModel.bv_neg_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_neg_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Lemma bv_neg_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_opp nan_abs : nan1 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (rx : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_neg_2_lanes prec emax nan_opp nan_abs nan_const W rx xs =
  IeeeFoldModel.bv_neg_2_seq prec emax nan_opp nan_abs nan_const rx xs.
Proof.
intros. unfold IeeeFoldModel.bv_neg_2_lanes, IeeeFoldModel.bv_neg_2_seq. cbv zeta.
change (IeeeFoldModel.bv_neg_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_neg_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
now rewrite norm_upper_2_lanes_seq_state.
Qed.

Lemma bv_make_1_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (r : binary_float prec emax) (cs : list (binary_float prec emax)),
  IeeeFoldModel.bv_make_1_lanes prec emax nan_plus nan_minus nan_abs nan_const W r cs =
  IeeeFoldModel.bv_make_1_seq prec emax nan_plus nan_minus nan_abs nan_const r cs.
Proof.
intros. unfold IeeeFoldModel.bv_make_1_lanes, IeeeFoldModel.bv_make_1_seq. cbv zeta.
change (IeeeFoldModel.bv_make_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
change (IeeeFoldModel.bv_make_1_combine prec emax)
  with (IeeeFoldModel.norm_upper_1_combine prec emax).
now rewrite norm_upper_1_lanes_seq_state.
Qed.

Lemma bv_make_2_lanes_seq_ieee :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (W : nat) (r : binary_float prec emax)
         (cs : list (binary_float prec emax * binary_float prec emax)),
  IeeeFoldModel.bv_make_2_lanes prec emax nan_plus nan_minus nan_abs nan_const W r cs =
  IeeeFoldModel.bv_make_2_seq prec emax nan_plus nan_minus nan_abs nan_const r cs.
Proof.
intros. unfold IeeeFoldModel.bv_make_2_lanes, IeeeFoldModel.bv_make_2_seq. cbv zeta.
change (IeeeFoldModel.bv_make_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
change (IeeeFoldModel.bv_make_2_combine prec emax)
  with (IeeeFoldModel.norm_upper_2_combine prec emax).
now rewrite norm_upper_2_lanes_seq_state.
Qed.

(** * The generated statements of the negation *)

Theorem bv_neg_1_seq_ieee_correct : bv_neg_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_opp nan_abs nan_const Hp1 rx xs HX.
assert (Vz : forall x, val (IeeeFoldModel.bv_neg_1_step prec emax nan_opp x) = - val x).
{ intros x. exact (neg_val prec emax nan_opp x). }
destruct (bv_neg_1_result prec emax nan_opp nan_abs nan_const rx xs HX)
  as [[Frx [Prx [B E]]]|[Erx [B E]]]; rewrite E; cbv beta iota.
- (* a finite ball vector: the negated centers and the radius rx *)
  assert (Bz : Forall (fun x => ball_finite_1 (IeeeFoldModel.bv_neg_1_step prec emax nan_opp x) rx)
                      xs).
  { revert B. apply Forall_impl. intros x [Fx _]. split; [|split; assumption].
    unfold finite, IeeeFoldModel.bv_neg_1_step, IeeeModel.neg_1. cbv zeta.
    rewrite (neg_fin prec emax nan_opp). exact Fx. }
  split; [left; split; [exact Frx|split; [exact Prx|apply Forall_map; exact Bz]]|].
  split; [split; intros _; [exact Frx|reflexivity]|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros x Hin. cbv zeta. intros x_ [[_ Ei]|[_ D]].
    { rewrite Ei in Frx. discriminate Frx. }
    right. split. exact (proj1 (Forall_forall _ xs) Bz x Hin).
    exact (proj1 (neg_ball_image (val x) _ (val rx) (Vz x)) x_ D).
  + intros _. apply Forall2_map_r. apply Forall_forall. intros x Hin. cbv zeta.
    intros v_ [[_ Ei]|[_ D]]. { rewrite Ei in Frx. discriminate Frx. }
    destruct (proj2 (neg_ball_image (val x) _ (val rx) (Vz x)) v_ D) as [x_ [Dx Ev]].
    exists x_. split; [|exact Ev]. right. split. exact (proj1 (Forall_forall _ xs) B x Hin).
    exact Dx.
  + intros _. split. exact Frx. split; [|reflexivity].
    apply Forall2_map_r. apply Forall_forall. intros x _. cbv zeta. exact (Vz x).
  + intros _ _ _. exact Frx.
- (* the whole space *)
  rewrite map_map.
  split; [right; split; [reflexivity|]|].
  { apply Forall_map. apply Forall_forall. intros x _. split. exists false. reflexivity.
    reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros x _. cbv zeta. intros x_ _. left.
    split. exists false. reflexivity. reflexivity.
  + intros F. discriminate F.
  + intros F. discriminate F.
  + rewrite Erx. intros F. discriminate F.
Qed.

Theorem bv_neg_1_lanes_ieee_correct : bv_neg_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_opp nan_abs nan_const Hp1 W rx xs HX.
rewrite (bv_neg_1_lanes_seq_ieee prec emax Hp He nan_opp nan_abs nan_const W rx xs).
exact (bv_neg_1_seq_ieee_correct prec emax Hp He nan_opp nan_abs nan_const Hp1 rx xs HX).
Qed.

Theorem bv_neg_2_seq_ieee_correct : bv_neg_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_opp nan_abs nan_const Hp1 rx xs HX.
assert (Vz : forall x0 x1 : binary_float prec emax,
          val (IeeeOperations.neg prec emax nan_opp x0) + val (IeeeOperations.neg prec emax nan_opp x1)
          = - (val x0 + val x1)).
{ intros x0 x1. unfold val. rewrite !(neg_val prec emax nan_opp). ring. }
destruct (bv_neg_2_result prec emax nan_opp nan_abs nan_const rx xs HX)
  as [[Frx [Prx [B E]]]|[Erx [B E]]]; rewrite E; cbv beta iota.
- (* a finite ball vector: the negated centers and the radius rx *)
  assert (Bz : Forall (fun x => ball_finite_2
                 (fst (IeeeFoldModel.bv_neg_2_step prec emax nan_opp x))
                 (snd (IeeeFoldModel.bv_neg_2_step prec emax nan_opp x)) rx) xs).
  { revert B. apply Forall_impl. intros [x0 x1] [F0 [F1 [N _]]]. cbn [fst snd] in *.
    unfold IeeeFoldModel.bv_neg_2_step, IeeeModel.neg_2. cbv zeta. cbn [fst snd].
    split; [|split; [|split; [|split; assumption]]].
    - unfold finite. rewrite (neg_fin prec emax nan_opp). exact F0.
    - unfold finite. rewrite (neg_fin prec emax nan_opp). exact F1.
    - unfold val. rewrite !(neg_val prec emax nan_opp). apply normalized_2_opp. exact N. }
  split; [left; split; [exact Frx|split; [exact Prx|apply Forall_map; exact Bz]]|].
  split; [split; intros _; [exact Frx|reflexivity]|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
    pose proof (proj1 (Forall_forall _ xs) Bz (x0, x1) Hin) as Bzx.
    unfold IeeeFoldModel.bv_neg_2_step, IeeeModel.neg_2 in Bzx |- *. cbv beta iota zeta in Bzx |- *.
    cbn [fst snd] in Bzx |- *.
    intros x_ [[_ [_ Ei]]|[_ D]]. { rewrite Ei in Frx. discriminate Frx. }
    right. split. exact Bzx.
    exact (proj1 (neg_ball_image (val x0 + val x1) _ (val rx) (Vz x0 x1)) x_ D).
  + intros _. apply Forall2_map_r. apply Forall_forall. intros [x0 x1] Hin.
    pose proof (proj1 (Forall_forall _ xs) B (x0, x1) Hin) as Bx.
    unfold IeeeFoldModel.bv_neg_2_step, IeeeModel.neg_2. cbv beta iota zeta. cbn [fst snd] in Bx |- *.
    intros v_ [[_ [_ Ei]]|[_ D]]. { rewrite Ei in Frx. discriminate Frx. }
    destruct (proj2 (neg_ball_image (val x0 + val x1) _ (val rx) (Vz x0 x1)) v_ D) as [x_ [Dx Ev]].
    exists x_. split; [|exact Ev]. right. split. exact Bx. exact Dx.
  + intros _. split. exact Frx. split; [|reflexivity].
    apply Forall2_map_r. apply Forall_forall. intros [x0 x1] _.
    unfold IeeeFoldModel.bv_neg_2_step, IeeeModel.neg_2. cbv beta iota zeta. cbn [fst snd].
    unfold neg_2, val. rewrite !(neg_val prec emax nan_opp). reflexivity.
  + intros _ _ _. exact Frx.
- (* the whole space *)
  rewrite map_map.
  split; [right; split; [reflexivity|]|].
  { apply Forall_map. apply Forall_forall. intros x _. cbn [fst snd].
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [|split; [|split]].
  + apply Forall2_map_r. apply Forall_forall. intros [x0 x1] _. cbv beta iota zeta. intros x_ _.
    left. split. exists false. reflexivity. split. exists false. reflexivity. reflexivity.
  + intros F. discriminate F.
  + intros F. discriminate F.
  + rewrite Erx. intros F. discriminate F.
Qed.

Theorem bv_neg_2_lanes_ieee_correct : bv_neg_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_opp nan_abs nan_const Hp1 W rx xs HX.
rewrite (bv_neg_2_lanes_seq_ieee prec emax Hp He nan_opp nan_abs nan_const W rx xs).
exact (bv_neg_2_seq_ieee_correct prec emax Hp He nan_opp nan_abs nan_const Hp1 rx xs HX).
Qed.

(** * The generated statements of the constructor *)

Theorem bv_make_1_seq_ieee_correct : bv_make_1_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs.
destruct (bv_make_1_result prec emax nan_plus nan_minus nan_abs nan_const r cs)
  as [[Fr [Pr [Fc [rz [Frz [Vrz E]]]]]]|[N E]]; rewrite E; cbv beta iota.
- (* the centers and the radius given *)
  assert (Fw : Forall (fun c => finite (IeeeFoldModel.bv_make_1_step prec emax nan_plus c)) cs).
  { revert Fc. apply Forall_impl. intros c Fc.
    unfold finite, IeeeFoldModel.bv_make_1_step, IeeeModel.bv_center_entry_1. cbv zeta.
    rewrite (guard_finite prec emax nan_plus). exact Fc. }
  assert (Prz : 0 <= val rz) by (rewrite Vrz; exact Pr).
  split.
  { left. split. exact Frz. split. exact Prz. apply Forall_map. revert Fw. apply Forall_impl.
    intros c Fwc. split. exact Fwc. split. exact Frz. exact Prz. }
  split; [split; intros _; [exact Frz|reflexivity]|].
  split; [split; intros _; [split; [exact Fr|split; [exact Pr|exact Fc]]|reflexivity]|].
  split; [|intros _; exact Vrz].
  apply Forall2_map_r. apply Forall_forall. intros c _. cbv zeta. intros _.
  unfold IeeeFoldModel.bv_make_1_step, IeeeModel.bv_center_entry_1, val. cbv zeta.
  apply (guard_val prec emax nan_plus).
- (* the whole space *)
  rewrite map_map.
  split.
  { right. split. reflexivity. apply Forall_map. apply Forall_forall. intros c _.
    split. exists false. reflexivity. reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [split; [intros H; discriminate H|intros H; contradiction (N H)]|].
  split; [|intros H; discriminate H].
  apply Forall2_map_r. apply Forall_forall. intros c _. cbv zeta. intros H. discriminate H.
Qed.

Theorem bv_make_1_lanes_ieee_correct : bv_make_1_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 W r cs.
rewrite (bv_make_1_lanes_seq_ieee prec emax Hp He nan_plus nan_minus nan_abs nan_const W r cs).
exact (bv_make_1_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs).
Qed.

Theorem bv_make_2_seq_ieee_correct : bv_make_2_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs Hc.
destruct (bv_make_2_result prec emax nan_plus nan_minus nan_abs nan_const r cs)
  as [[Fr [Pr [Fc [rz [Frz [Vrz E]]]]]]|[N E]]; rewrite E; cbv beta iota.
- (* the centers and the radius given *)
  assert (Prz : 0 <= val rz) by (rewrite Vrz; exact Pr).
  split.
  { left. split. exact Frz. split. exact Prz. apply Forall_map. apply Forall_forall.
    intros [c0 c1] Hin.
    pose proof (proj1 (Forall_forall _ cs) Fc (c0, c1) Hin) as F0.
    pose proof (proj1 (Forall_forall _ cs) Hc (c0, c1) Hin) as Cc.
    unfold IeeeFoldModel.bv_make_2_step, IeeeModel.bv_center_2. cbv beta iota zeta.
    cbn [fst snd] in F0, Cc |- *.
    destruct Cc as [[_ [F1 Nc]]|[[[s Ei] _]|[Ni _]]].
    - split. exact F0. split. exact F1. split. exact Nc. split. exact Frz. exact Prz.
    - rewrite Ei in F0. discriminate F0.
    - unfold finite in F0. rewrite (nan_not_finite prec emax c0 Ni) in F0. discriminate F0. }
  split; [split; intros _; [exact Frz|reflexivity]|].
  split; [split; intros _; [split; [exact Fr|split; [exact Pr|exact Fc]]|reflexivity]|].
  split; [|intros _; exact Vrz].
  apply Forall2_map_r. apply Forall_forall. intros [c0 c1] _.
  unfold IeeeFoldModel.bv_make_2_step, IeeeModel.bv_center_2. cbv beta iota zeta. cbn [fst snd].
  intros _. split; reflexivity.
- (* the whole space *)
  rewrite map_map.
  split.
  { right. split. reflexivity. apply Forall_map. apply Forall_forall. intros c _. cbn [fst snd].
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity. }
  split; [split; intros H; discriminate H|].
  split; [split; [intros H; discriminate H|intros H; contradiction (N H)]|].
  split; [|intros H; discriminate H].
  apply Forall2_map_r. apply Forall_forall. intros [c0 c1] _. cbv beta iota zeta.
  intros H. discriminate H.
Qed.

Theorem bv_make_2_lanes_ieee_correct : bv_make_2_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 W r cs Hc.
rewrite (bv_make_2_lanes_seq_ieee prec emax Hp He nan_plus nan_minus nan_abs nan_const W r
  cs).
exact (bv_make_2_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs Hc).
Qed.

(** * The constructor of a ball vector on the guarded limbs of its centers *)

(* bv_make_2_entry (rule R3): its step bv_center_entry_2 is bv_center_2 on the guarded limbs, so
   the loop is bv_make_2 on the centers guarded limb by limb, in both orders, float for float. Its
   statements follow from those of bv_make_2 there: a guarded canonical pair is canonical, finite
   exactly when the pair is, with the same values (guard_canonical_2). *)
Definition guard_pair (prec emax : Z) {prec_gt_0_ : Prec_gt_0 prec}
    {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax} (nan_plus : nan2 prec emax)
    (c : binary_float prec emax * binary_float prec emax) : binary_float prec emax * binary_float prec emax :=
  (IeeeOperations.guard prec emax nan_plus (fst c), IeeeOperations.guard prec emax nan_plus (snd c)).

Lemma bv_make_2_entry_seq_eq (prec emax : Z) {prec_gt_0_ : Prec_gt_0 prec}
    {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}
    (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
    (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
    (r : binary_float prec emax) (cs : list (binary_float prec emax * binary_float prec emax)) :
  IeeeFoldModel.bv_make_2_entry_seq prec emax nan_plus nan_minus nan_abs nan_const r cs =
  IeeeFoldModel.bv_make_2_seq prec emax nan_plus nan_minus nan_abs nan_const r
    (map (guard_pair prec emax nan_plus) cs).
Proof.
unfold IeeeFoldModel.bv_make_2_entry_seq, IeeeFoldModel.bv_make_2_seq. cbv zeta.
assert (E : map (IeeeFoldModel.bv_make_2_entry_step prec emax nan_plus) cs =
            map (IeeeFoldModel.bv_make_2_step prec emax) (map (guard_pair prec emax nan_plus) cs)).
{ rewrite map_map. apply map_ext. intros [c0 c1]. reflexivity. }
rewrite E. reflexivity.
Qed.

Lemma bv_make_2_entry_lanes_eq (prec emax : Z) {prec_gt_0_ : Prec_gt_0 prec}
    {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}
    (nan_plus nan_minus : nan2 prec emax) (nan_abs : nan1 prec emax)
    (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
    (W : nat) (r : binary_float prec emax) (cs : list (binary_float prec emax * binary_float prec emax)) :
  IeeeFoldModel.bv_make_2_entry_lanes prec emax nan_plus nan_minus nan_abs nan_const W r cs =
  IeeeFoldModel.bv_make_2_lanes prec emax nan_plus nan_minus nan_abs nan_const W r
    (map (guard_pair prec emax nan_plus) cs).
Proof.
unfold IeeeFoldModel.bv_make_2_entry_lanes, IeeeFoldModel.bv_make_2_lanes. cbv zeta.
assert (E : map (IeeeFoldModel.bv_make_2_entry_step prec emax nan_plus) cs =
            map (IeeeFoldModel.bv_make_2_step prec emax) (map (guard_pair prec emax nan_plus) cs)).
{ rewrite map_map. apply map_ext. intros [c0 c1]. reflexivity. }
rewrite E. reflexivity.
Qed.

Lemma Forall2_map_l_inv {A B C : Type} (f : A -> C) (P : C -> B -> Prop) (l : list A) (l' : list B) :
  Forall2 P (map f l) l' -> Forall2 (fun x y => P (f x) y) l l'.
Proof.
revert l'. induction l as [|a l IH]; intros l' H; cbn in H.
- inversion H. constructor.
- inversion H; subst. constructor. assumption. apply IH. assumption.
Qed.

Lemma guard_pair_finite_fst (prec emax : Z) {prec_gt_0_ : Prec_gt_0 prec}
    {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax} (nan_plus : nan2 prec emax)
    (cs : list (binary_float prec emax * binary_float prec emax)) :
  Forall (fun c => finite (fst c)) (map (guard_pair prec emax nan_plus) cs) <->
  Forall (fun c => finite (fst c)) cs.
Proof.
induction cs as [|[c0 c1] cs IH]; cbn [map].
- split; intros _; constructor.
- split; intros G; inversion G as [|x l Hx Hl]; subst; constructor.
  + unfold guard_pair, finite in Hx. cbn [fst snd] in Hx |- *.
    rewrite (guard_finite prec emax nan_plus) in Hx. exact Hx.
  + apply IH. exact Hl.
  + unfold guard_pair, finite. cbn [fst snd]. rewrite (guard_finite prec emax nan_plus). exact Hx.
  + apply IH. exact Hl.
Qed.

Theorem bv_make_2_entry_seq_ieee_correct : bv_make_2_entry_seq_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs Hc.
rewrite (bv_make_2_entry_seq_eq prec emax nan_plus nan_minus nan_abs nan_const r cs).
assert (Hg : Forall (fun c => canonical_2 (fst c) (snd c)) (map (guard_pair prec emax nan_plus) cs)).
{ apply Forall_map. revert Hc. apply Forall_impl. intros [c0 c1] C. cbn [fst snd] in C |- *.
  unfold guard_pair. cbn [fst snd]. exact (proj1 (guard_canonical_2 prec emax nan_plus c0 c1 C)). }
generalize (bv_make_2_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r
              (map (guard_pair prec emax nan_plus) cs) Hg).
destruct (IeeeFoldModel.bv_make_2_seq prec emax nan_plus nan_minus nan_abs nan_const r
            (map (guard_pair prec emax nan_plus) cs)) as [[ws r_] flag].
intros [A [B [C [D E]]]].
pose proof (guard_pair_finite_fst prec emax nan_plus cs) as Fg.
split. exact A. split. exact B. split.
- split.
  + intros Hf. destruct (proj1 C Hf) as [X [Y Z]]. split. exact X. split. exact Y. apply Fg. exact Z.
  + intros [X [Y Z]]. apply (proj2 C). split. exact X. split. exact Y. apply Fg. exact Z.
- split; [|exact E].
  apply Forall2_map_l_inv in D. revert D. apply Forall2_impl. intros [c0 c1] [z0 z1] H Hf.
  unfold guard_pair in H. cbn [fst snd] in H. destruct (H Hf) as [V0 V1].
  rewrite V0, V1. split; apply (guard_val prec emax nan_plus).
Qed.

Theorem bv_make_2_entry_lanes_ieee_correct : bv_make_2_entry_lanes_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 W r cs Hc.
rewrite (bv_make_2_entry_lanes_eq prec emax nan_plus nan_minus nan_abs nan_const W r cs).
rewrite (bv_make_2_lanes_seq_ieee prec emax Hp He nan_plus nan_minus nan_abs nan_const W r
  (map (guard_pair prec emax nan_plus) cs)).
rewrite <- (bv_make_2_entry_seq_eq prec emax nan_plus nan_minus nan_abs nan_const r cs).
exact (bv_make_2_entry_seq_ieee_correct prec emax Hp He nan_plus nan_minus nan_abs nan_const Hp1 r cs Hc).
Qed.
