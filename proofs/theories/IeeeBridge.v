(* The bridge between the two models of a kernel, for every straight-line program.

   The real model (proofs/gen/Model.v) computes with real numbers in a format that has
   no largest number; the IEEE model (proofs/gen/IeeeModel.v) computes with IEEE 754 numbers, where
   an operation whose rounded result is 2^emax or more in magnitude returns an infinity,
   and infinities and NaN propagate. This file proves, once for all programs made of
   additions, subtractions, fused multiply-adds and sign changes:

   1. One operation (add_spec, sub_spec, fma_spec, ...). With finite operands, the IEEE
      result is finite exactly when the rounded real result is below 2^emax in
      magnitude, and it is then that rounded real result. With an operand that is not
      finite, the result is not finite.

   2. A whole program (run_sim). With finite inputs: every IEEE value is finite exactly
      when every value of the real model is below 2^emax in magnitude, and the two lists
      of values are then equal. So "no overflow" is a statement about the real model.

   3. The cone (covers_sound). If a value is finite, so is every value it depends on.
      When the cone of output limb 0 covers a program, a finite output limb 0 means that
      all its values are finite. Whether it covers is computed (Program.covers).

   4. The values computed after output limb 0 (bridge_tail, bridge_f2s). The last two
      operations of a final Fast2Sum, z = s - a and e = b - z, use s and are not in its
      cone. Their finiteness follows from the fact that the result (s, e) of the real
      model is normalized (f2s_tail_range): if z overflowed, e = RN(b - z) would be at
      least 2^(emax - prec), one unit in the last place of the largest numbers, while a
      normalized pair has |e| <= ulp(s)/2 <= 2^(emax - prec)/2.

   Here emin = 3 - emax - prec, the smallest exponent of the IEEE format (proofs/gen/IeeeModel.v),
   and the real model is taken in the format FLT with that emin. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized Program.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
Import ListNotations.
Open Scope R_scope.

(** * The real model of a program *)

Section RealProgram.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

(* One instruction over the real numbers, written as in Model.v. *)
Definition stepR (e : list R) (i : instr) : R :=
  match i with
  | Iadd a b => rnd (nth a e 0 + nth b e 0)
  | Isub a b => rnd (nth a e 0 - nth b e 0)
  | Ineg a => - nth a e 0
  | Ifma a b c => rnd (nth a e 0 * nth b e 0 + nth c e 0)
  | Ifms a b c => rnd (nth a e 0 * nth b e 0 + - nth c e 0)
  | Iprod a b => rnd (nth a e 0 * nth b e 0 + 0)
  | Iguard a => rnd (nth a e 0 + 0)
  end.

Definition runR : list instr -> list R -> list R := run stepR.

End RealProgram.

(** * The IEEE model of a program, and its relation to the real model *)

Section IeeeProgram.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation sub := (IeeeOperations.sub prec emax nan_minus).
Notation neg := (IeeeOperations.neg prec emax nan_opp).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation fms := (IeeeOperations.fms prec emax nan_opp nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation pzero := (IeeeOperations.pzero prec emax).
Notation guard := (IeeeOperations.guard prec emax nan_plus).

(* A real number is in range when its magnitude is below 2^emax. For a number of the
   format this means: at most the largest finite number. *)
Definition inrange (r : R) : Prop := Rabs r < bpow radix2 emax.

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

Lemma b2r_inrange : forall x : float, inrange (b2r x).
Proof. intros x. apply abs_B2R_lt_emax. Qed.

Lemma b2r_format : forall x : float, format (b2r x).
Proof. intros x. apply (generic_format_B2R prec emax x). Qed.

(** ** One operation *)

(* A result that Flocq describes as "the overflow value" is an infinity. *)
Lemma overflow_not_finite :
  forall (v : float) (s : bool),
  B2FF prec emax v = binary_overflow prec emax BinarySingleNaN.mode_NE s ->
  is_finite prec emax v = false.
Proof. intros v s H. destruct v; try reflexivity; discriminate H. Qed.

(* Non-finite in, non-finite out. *)
Lemma add_finite_inv : forall x y : float, fin (add x y) -> fin x /\ fin y.
Proof.
intros x y. unfold IeeeOperations.add, Bplus. rewrite is_finite_BSN2B.
destruct x as [sx|sx|sx px Hx|sx mx ex Hx]; destruct y as [sy|sy|sy py Hy|sy my ey Hy];
  try (intros _; split; reflexivity); simpl; try discriminate.
destruct (Bool.eqb sx sy); discriminate.
Qed.

Lemma sub_finite_inv : forall x y : float, fin (sub x y) -> fin x /\ fin y.
Proof.
intros x y. unfold IeeeOperations.sub, Bminus. rewrite is_finite_BSN2B.
destruct x as [sx|sx|sx px Hx|sx mx ex Hx]; destruct y as [sy|sy|sy py Hy|sy my ey Hy];
  try (intros _; split; reflexivity); simpl; try discriminate.
destruct (Bool.eqb sx (negb sy)); discriminate.
Qed.

Lemma neg_finite : forall x : float, is_finite prec emax (neg x) = is_finite prec emax x.
Proof. intros x. apply is_finite_Bopp. Qed.

Lemma fma_finite_inv : forall x y z : float, fin (fma x y z) -> fin x /\ fin y /\ fin z.
Proof.
intros x y z. unfold IeeeOperations.fma, Bfma. rewrite is_finite_BSN2B.
destruct x as [sx|sx|sx px Hx|sx mx ex Hx]; destruct y as [sy|sy|sy py Hy|sy my ey Hy];
  destruct z as [sz|sz|sz pz Hz|sz mz ez Hz];
  try (intros _; repeat split; reflexivity); simpl; try discriminate;
  match goal with |- context [Bool.eqb ?a ?b] => destruct (Bool.eqb a b); discriminate end.
Qed.

(* With finite operands: finite exactly when the rounded real result is in range, and
   then equal to it. From Flocq's Bplus_correct, Bminus_correct, Bfma_correct. *)
Lemma add_spec :
  forall x y : float, fin x -> fin y ->
  (fin (add x y) <-> inrange (rnd (b2r x + b2r y))) /\
  (fin (add x y) -> b2r (add x y) = rnd (b2r x + b2r y)).
Proof.
intros x y Fx Fy.
generalize (Bplus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_NE x y Fx Fy).
fold (add x y).
change (round radix2 (SpecFloat.fexp prec emax) (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE)
          (b2r x + b2r y)) with (rnd (b2r x + b2r y)).
unfold inrange.
destruct (Rlt_bool_spec (Rabs (rnd (b2r x + b2r y))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. split; [split|]; auto.
- intros [E _]. apply overflow_not_finite in E. rewrite E.
  split; [split|]; try discriminate. intros H'. lra.
Qed.

Lemma sub_spec :
  forall x y : float, fin x -> fin y ->
  (fin (sub x y) <-> inrange (rnd (b2r x - b2r y))) /\
  (fin (sub x y) -> b2r (sub x y) = rnd (b2r x - b2r y)).
Proof.
intros x y Fx Fy.
generalize (Bminus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_minus BinarySingleNaN.mode_NE x y Fx Fy).
fold (sub x y).
change (round radix2 (SpecFloat.fexp prec emax) (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE)
          (b2r x - b2r y)) with (rnd (b2r x - b2r y)).
unfold inrange.
destruct (Rlt_bool_spec (Rabs (rnd (b2r x - b2r y))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. split; [split|]; auto.
- intros [E _]. apply overflow_not_finite in E. rewrite E.
  split; [split|]; try discriminate. intros H'. lra.
Qed.

Lemma fma_spec :
  forall x y z : float, fin x -> fin y -> fin z ->
  (fin (fma x y z) <-> inrange (rnd (b2r x * b2r y + b2r z))) /\
  (fin (fma x y z) -> b2r (fma x y z) = rnd (b2r x * b2r y + b2r z)).
Proof.
intros x y z Fx Fy Fz.
generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE x y z Fx Fy Fz).
cbv zeta. fold (fma x y z).
change (round radix2 (SpecFloat.fexp prec emax) (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE)
          (b2r x * b2r y + b2r z)) with (rnd (b2r x * b2r y + b2r z)).
unfold inrange.
destruct (Rlt_bool_spec (Rabs (rnd (b2r x * b2r y + b2r z))) (bpow radix2 emax)) as [H|H].
- intros [E [F _]]. split; [split|]; auto.
- intros E. apply overflow_not_finite in E. rewrite E.
  split; [split|]; try discriminate. intros H'. lra.
Qed.

(** ** One instruction *)

Definition d0 : float := pzero.

(* One instruction over IEEE numbers. *)
Definition stepB (e : list float) (i : instr) : float :=
  match i with
  | Iadd a b => add (nth a e d0) (nth b e d0)
  | Isub a b => sub (nth a e d0) (nth b e d0)
  | Ineg a => neg (nth a e d0)
  | Ifma a b c => fma (nth a e d0) (nth b e d0) (nth c e d0)
  | Ifms a b c => fms (nth a e d0) (nth b e d0) (nth c e d0)
  | Iprod a b => prod (nth a e d0) (nth b e d0)
  | Iguard a => guard (nth a e d0)
  end.

Notation stepR := (stepR emin prec tie_even).
Notation runR := (runR emin prec tie_even).
Notation runB := (run stepB).

Lemma nth_b2r : forall (e : list float) a, nth a (map b2r e) 0 = b2r (nth a e d0).
Proof. intros e a. change 0 with (b2r d0). apply map_nth. Qed.

Lemma nth_fin : forall (e : list float) a, Forall (fun x => fin x) e -> fin (nth a e d0).
Proof.
intros e a Fe. destruct (nth_in_or_default a e d0) as [H|H].
- rewrite Forall_forall in Fe. now apply Fe.
- now rewrite H.
Qed.

(* If the value of an instruction is finite, so are its operands. *)
Lemma step_inv :
  forall e i, fin (stepB e i) -> forall a, In a (operands i) -> fin (nth a e d0).
Proof.
intros e i H a Ha. destruct i as [a1 b1|a1 b1|a1|a1 b1 c1|a1 b1 c1|a1 b1|a1]; simpl in H, Ha.
- apply add_finite_inv in H. intuition (subst; auto).
- apply sub_finite_inv in H. intuition (subst; auto).
- rewrite neg_finite in H. intuition (subst; auto).
- apply fma_finite_inv in H. intuition (subst; auto).
- unfold IeeeOperations.fms in H. apply fma_finite_inv in H. rewrite neg_finite in H.
  intuition (subst; auto).
- unfold IeeeOperations.prod in H. apply fma_finite_inv in H. intuition (subst; auto).
- unfold IeeeOperations.guard in H. apply add_finite_inv in H. intuition (subst; auto).
Qed.

(* With finite operands, the value of an instruction is finite exactly when its value
   in the real model is in range, and it is then that value. *)
Lemma step_spec :
  forall e i, (forall a, In a (operands i) -> fin (nth a e d0)) ->
  (fin (stepB e i) <-> inrange (stepR (map b2r e) i)) /\
  (fin (stepB e i) -> b2r (stepB e i) = stepR (map b2r e) i).
Proof.
intros e i H. destruct i as [a1 b1|a1 b1|a1|a1 b1 c1|a1 b1 c1|a1 b1|a1]; simpl in H |- *;
  rewrite ?nth_b2r.
- apply add_spec; apply H; auto.
- apply sub_spec; apply H; auto.
- rewrite neg_finite. unfold IeeeOperations.neg. rewrite B2R_Bopp. split; [split|]; auto.
  intros _. unfold inrange. rewrite Rabs_Ropp. apply b2r_inrange.
- apply fma_spec; apply H; auto.
- unfold IeeeOperations.fms.
  replace (- b2r (nth c1 e d0)) with (b2r (neg (nth c1 e d0)))
    by (unfold IeeeOperations.neg; apply B2R_Bopp).
  apply fma_spec; try (apply H; auto). rewrite neg_finite. apply H; auto.
- unfold IeeeOperations.prod. change 0 with (b2r pzero).
  apply fma_spec; try (apply H; auto). reflexivity.
- unfold IeeeOperations.guard. change 0 with (b2r pzero).
  apply add_spec; try (apply H; auto). reflexivity.
Qed.

(** ** A whole program *)

(* With finite inputs: all IEEE values are finite exactly when all values of the real
   model are in range, and the two lists of values are then equal. *)
Theorem run_sim :
  forall p (e : list float), Forall (fun x => fin x) e ->
  (Forall (fun x => fin x) (runB p e) <-> Forall inrange (runR p (map b2r e))) /\
  (Forall (fun x => fin x) (runB p e) -> map b2r (runB p e) = runR p (map b2r e)).
Proof.
induction p as [|i q IH]; intros e Fe.
- simpl. split; [split|]; auto. intros _.
  apply Forall_forall. intros r Hr. apply in_map_iff in Hr. destruct Hr as [x [<- _]].
  apply b2r_inrange.
- assert (Hop : forall a, In a (operands i) -> fin (nth a e d0)).
  { intros a _. now apply nth_fin. }
  destruct (step_spec e i Hop) as [S1 S2].
  unfold Kairn.IeeeBridge.runR. simpl run.
  fold (runR q (map b2r e ++ [stepR (map b2r e) i])).
  assert (Key : fin (stepB e i) ->
    (Forall (fun x => fin x) (runB q (e ++ [stepB e i])) <->
     Forall inrange (runR q (map b2r e ++ [stepR (map b2r e) i]))) /\
    (Forall (fun x => fin x) (runB q (e ++ [stepB e i])) ->
     map b2r (runB q (e ++ [stepB e i])) = runR q (map b2r e ++ [stepR (map b2r e) i]))).
  { intros Fv.
    assert (Fe' : Forall (fun x => fin x) (e ++ [stepB e i])).
    { apply Forall_app. split; auto. }
    generalize (IH (e ++ [stepB e i]) Fe'). rewrite map_app. simpl map. now rewrite (S2 Fv). }
  assert (FromB : Forall (fun x => fin x) (runB q (e ++ [stepB e i])) -> fin (stepB e i)).
  { intros H. apply run_Forall_prefix in H. apply Forall_app in H. destruct H as [_ H].
    now inversion H. }
  assert (FromR : Forall inrange (runR q (map b2r e ++ [stepR (map b2r e) i])) -> fin (stepB e i)).
  { intros H. apply run_Forall_prefix in H. apply Forall_app in H. destruct H as [_ H].
    apply S1. now inversion H. }
  split; [split|].
  + intros H. now apply (Key (FromB H)).
  + intros H. now apply (Key (FromR H)).
  + intros H. now apply (Key (FromB H)).
Qed.

(** ** The cone *)

(* If the values at the positions s are finite, so are those at the positions these
   depend on. *)
Lemma cone_sound :
  forall p (e : list float) s, wf p (length e) = true ->
  (forall k, In k s -> fin (nth k (runB p e) d0)) ->
  forall k, In k (cone p (length e) s) -> fin (nth k (runB p e) d0).
Proof.
induction p as [|i q IH]; intros e s Hwf Hs k Hk.
- now apply Hs.
- simpl in Hwf. apply andb_prop in Hwf. destruct Hwf as [Hops Hwf].
  assert (Hlen : length (e ++ [stepB e i]) = S (length e)).
  { rewrite length_app. simpl. lia. }
  assert (IH' : forall j, In j (cone q (S (length e)) s) -> fin (nth j (runB (i :: q) e) d0)).
  { rewrite <- Hlen. apply IH. now rewrite Hlen. exact Hs. }
  simpl cone in Hk.
  destruct (mem (length e) (cone q (S (length e)) s)) eqn:Hm.
  + apply in_app_or in Hk. destruct Hk as [Hk|Hk]; [|now apply IH'].
    assert (Hlt : (k < length e)%nat).
    { rewrite forallb_forall in Hops. apply Nat.ltb_lt. now apply Hops. }
    simpl run. rewrite run_nth_old by (rewrite Hlen; lia). rewrite app_nth1 by exact Hlt.
    apply step_inv with (i := i); trivial.
    rewrite <- (run_nth_new float stepB i q e d0). apply IH'. now apply mem_In.
  + now apply IH'.
Qed.

(* If the cone of position z covers the program and the value at z is finite, every
   value is finite. *)
Theorem covers_sound :
  forall p (e : list float) z, Forall (fun x => fin x) e ->
  wf p (length e) = true -> covers p (length e) z = true ->
  fin (nth z (runB p e) d0) -> Forall (fun x => fin x) (runB p e).
Proof.
intros p e z Fe Hwf Hc Hz. apply Forall_nth. intros k d Hk.
rewrite (nth_indep _ d d0) by exact Hk. rewrite run_length in Hk.
destruct (Nat.lt_ge_cases k (length e)) as [H|H].
- rewrite run_nth_old by exact H. now apply nth_fin.
- apply (cone_sound p e [z] Hwf).
  + intros j [<-|[]]. exact Hz.
  + apply mem_In. unfold covers in Hc. rewrite forallb_forall in Hc. apply Hc.
    apply in_seq. lia.
Qed.

(** ** Programs with values computed after output limb 0 *)

(* body: the part of the program whose values are all in the cone of position z (output
   limb 0); tail: the operations after it. If, when the body runs without overflow, the
   values of the tail are in range in the real model, then a finite value at z means
   that every value is finite and equal to that of the real model. *)
Theorem bridge_tail :
  forall body tail (e : list float) z,
  Forall (fun x => fin x) e ->
  wf body (length e) = true -> covers body (length e) z = true ->
  (z < length e + length body)%nat ->
  (Forall (fun x => fin x) (runB body e) ->
   map b2r (runB body e) = runR body (map b2r e) ->
   Forall inrange (runR (body ++ tail) (map b2r e))) ->
  fin (nth z (runB (body ++ tail) e) d0) ->
  Forall (fun x => fin x) (runB (body ++ tail) e) /\
  map b2r (runB (body ++ tail) e) = runR (body ++ tail) (map b2r e).
Proof.
intros body tail e z Fe Hwf Hc Hz Htail Hfin.
unfold Kairn.IeeeBridge.runR in *. rewrite run_app in Hfin, Htail |- *. rewrite run_app.
rewrite run_nth_old in Hfin by (rewrite run_length; exact Hz).
assert (F1 : Forall (fun x => fin x) (runB body e)) by now apply covers_sound with z.
destruct (run_sim body e Fe) as [_ M1]. specialize (M1 F1).
unfold Kairn.IeeeBridge.runR in M1.
specialize (Htail F1 M1). rewrite <- M1 in Htail |- *.
destruct (run_sim tail (runB body e) F1) as [S1 S2].
unfold Kairn.IeeeBridge.runR in S1, S2.
split. now apply S1. apply S2. now apply S1.
Qed.

(** ** The top of the range *)

(* Omega = 2^emax - 2^(emax - prec) is the largest number of the IEEE format. In the
   format with no largest number it is the number just below 2^emax. *)
Definition Omega : R := bpow radix2 emax - bpow radix2 (emax - prec).

Lemma pred_top : pred radix2 fexp (bpow radix2 emax) = Omega.
Proof. rewrite pred_bpow. unfold Omega, FLT_exp. do 2 f_equal. lia. Qed.

Lemma format_top : format (bpow radix2 emax).
Proof. apply generic_format_bpow. unfold FLT_exp. lia. Qed.

Lemma format_Omega : format Omega.
Proof.
rewrite <- pred_top. apply generic_format_pred; auto with typeclass_instances.
apply format_top.
Qed.

(* A number of the format is in range exactly when it is at most Omega. *)
Lemma inrange_le_Omega : forall x, format x -> inrange x -> Rabs x <= Omega.
Proof.
intros x Fx Hx. rewrite <- pred_top. apply pred_ge_gt; auto with typeclass_instances.
- now apply generic_format_abs.
- apply format_top.
Qed.

Lemma le_Omega_inrange : forall x, Rabs x <= Omega -> inrange x.
Proof.
intros x Hx. unfold inrange. unfold Omega in Hx.
generalize (bpow_gt_0 radix2 (emax - prec)). lra.
Qed.

(* Rounding does not leave the range: Omega is a number of the format. *)
Lemma rnd_le_Omega : forall x, Rabs x <= Omega -> inrange (rnd x).
Proof.
intros x Hx. apply le_Omega_inrange. apply round_abs_le; trivial. apply format_Omega.
Qed.

Lemma b2r_le_Omega : forall x : float, Rabs (b2r x) <= Omega.
Proof. intros x. apply abs_B2R_le_emax_minus_prec. exact prec_gt_0_. Qed.

Lemma top_half : bpow radix2 emax = 2 * bpow radix2 (emax - 1).
Proof.
replace emax with (1 + (emax - 1))%Z at 1 by ring. now rewrite bpow_plus, pow2_1.
Qed.

(* With at least two bits, one unit in the last place of the largest numbers is at most
   a quarter of 2^emax. *)
Lemma top_ulp_le : (2 <= prec)%Z -> bpow radix2 (emax - prec) <= / 2 * bpow radix2 (emax - 1).
Proof.
intros Hp2. apply Rle_trans with (bpow radix2 (emax - 2)).
- apply bpow_le. lia.
- replace (emax - 1)%Z with (1 + (emax - 2))%Z by ring. rewrite bpow_plus, pow2_1. lra.
Qed.

(* The number of the format just below Omega is Omega - 2^(emax - prec): a number of
   the format other than Omega and -Omega is at most that in magnitude. *)
Lemma below_Omega :
  (2 <= prec)%Z -> forall x, format x -> Rabs x <= Omega -> Rabs x <> Omega ->
  Rabs x <= Omega - bpow radix2 (emax - prec).
Proof.
intros Hp2 x Fx Hx Hne.
assert (U0 : 0 < bpow radix2 (emax - prec)) by apply bpow_gt_0.
assert (H0 : 0 < bpow radix2 (emax - 1)) by apply bpow_gt_0.
generalize top_half (top_ulp_le Hp2). intros T1 T2.
assert (Opos : 0 < Omega) by (unfold Omega; lra).
assert (H1 : Rabs x <= pred radix2 fexp Omega).
{ apply pred_ge_gt; auto with typeclass_instances.
  - now apply generic_format_abs.
  - apply format_Omega.
  - lra. }
assert (H2 : bpow radix2 (emax - 1) <= pred radix2 fexp Omega).
{ apply pred_ge_gt; auto with typeclass_instances.
  - apply generic_format_bpow. unfold FLT_exp. lia.
  - apply format_Omega.
  - unfold Omega. lra. }
assert (H3 : ulp radix2 fexp (pred radix2 fexp Omega) = bpow radix2 (emax - prec)).
{ rewrite ulp_neq_0 by lra. unfold cexp.
  replace (mag radix2 (pred radix2 fexp Omega) : Z) with emax.
  - unfold FLT_exp. f_equal. lia.
  - symmetry. apply mag_unique_pos. split. exact H2.
    apply Rlt_trans with Omega.
    + apply pred_lt_id. lra.
    + unfold Omega. lra. }
generalize (pred_plus_ulp radix2 fexp Omega Opos format_Omega). rewrite H3. lra.
Qed.

(* The unit in the last place of a number in range is at most that of the largest
   numbers. *)
Lemma ulp_le_top : forall s : R, inrange s -> ulp radix2 fexp s <= bpow radix2 (emax - prec).
Proof.
intros s Hs. destruct (Req_dec s 0) as [Z|Z].
- rewrite Z, ulp_FLT_0 by exact prec_gt_0_. apply bpow_le. lia.
- rewrite ulp_neq_0 by exact Z. apply bpow_le. unfold cexp, FLT_exp.
  assert (mag radix2 s <= emax)%Z by now apply mag_le_bpow.
  lia.
Qed.

(* The tail of a Fast2Sum. Let s = RN(a + b), z = RN(s - a), t = RN(b - z) in the real
   model, with b a number of the IEEE format and s in range. If (s, t) is normalized
   then z and t are in range. No condition on the magnitudes of a and b. *)
Lemma f2s_tail_range :
  forall a b : R,
  Rabs b <= bpow radix2 emax - bpow radix2 (emax - prec) ->
  let s := rnd (a + b) in
  let z := rnd (s - a) in
  let t := rnd (b - z) in
  inrange s -> normalized_2 emin prec s t -> inrange z /\ inrange t.
Proof.
intros a b Hb s z t Hs Hn. unfold inrange in *.
assert (P : 0 < bpow radix2 (emax - prec)) by apply bpow_gt_0.
assert (Ht : Rabs t <= / 2 * bpow radix2 (emax - prec)).
{ apply Rle_trans with (1 := normalized_2_tail_ulp emin prec s t Hn).
  apply Rmult_le_compat_l. lra. now apply ulp_le_top. }
split.
- destruct (Rlt_or_le (Rabs z) (bpow radix2 emax)) as [H|H]; trivial. exfalso.
  assert (Hbz : bpow radix2 (emax - prec) <= Rabs (b - z)).
  { apply Rle_trans with (Rabs z - Rabs b). lra.
    rewrite <- (Rabs_Ropp (b - z)). replace (- (b - z)) with (z - b) by ring.
    apply Rabs_triang_inv. }
  assert (Ht' : bpow radix2 (emax - prec) <= Rabs t).
  { apply round_abs_ge; trivial. apply generic_format_bpow. unfold FLT_exp. lia. }
  lra.
- apply Rle_lt_trans with (1 := Ht).
  apply Rlt_le_trans with (bpow radix2 (emax - prec)). lra. apply bpow_le. lia.
Qed.

(* A program that ends with a Fast2Sum whose first result is output limb 0:
       pre;  s = a + b;  z = s - a;  t = b - z
   where a and b are the positions ia and ib. If the cone of s covers pre and the
   real-model result (s, t) is normalized (which the theorem of the kernel in the real
   model provides), then a finite s means that every value is finite and equal to that
   of the real model. *)
Theorem bridge_f2s :
  forall pre ia ib (e : list float),
  let n := (length e + length pre)%nat in
  let body := pre ++ [Iadd ia ib] in
  let prog := body ++ [Isub n ia; Isub ib (S n)] in
  Forall (fun x => fin x) e ->
  wf body (length e) = true -> covers body (length e) n = true ->
  normalized_2 emin prec (nth n (runR prog (map b2r e)) 0)
                         (nth (S (S n)) (runR prog (map b2r e)) 0) ->
  fin (nth n (runB prog e) d0) ->
  Forall (fun x => fin x) (runB prog e) /\ map b2r (runB prog e) = runR prog (map b2r e).
Proof.
intros pre ia ib e n body prog Fe Hwf Hc Hn Hz.
assert (Hia : (ia < n)%nat /\ (ib < n)%nat).
{ unfold body in Hwf. rewrite wf_app in Hwf. apply andb_prop in Hwf. destruct Hwf as [_ H].
  simpl in H. fold n in H. rewrite andb_true_r in H. apply andb_prop in H.
  destruct H as [H1 H2]. apply andb_prop in H2. destruct H2 as [H2 _].
  split; now apply Nat.ltb_lt. }
destruct Hia as [Hia Hib].
apply bridge_tail with (z := n); trivial.
{ unfold body. rewrite length_app. simpl. lia. }
intros F1 M1.
unfold prog, Kairn.IeeeBridge.runR in Hn |- *. rewrite run_app in Hn |- *.
fold (runR body (map b2r e)) in Hn |- *.
(* the values of the body in the real model: those of pre, then s *)
assert (E1 : runR body (map b2r e) =
             runR pre (map b2r e) ++ [stepR (runR pre (map b2r e)) (Iadd ia ib)]).
{ unfold body, Kairn.IeeeBridge.runR. now rewrite run_app. }
set (R0 := runR pre (map b2r e)) in *.
assert (L0 : length R0 = n).
{ unfold R0, Kairn.IeeeBridge.runR. rewrite run_length, length_map. reflexivity. }
set (R1 := runR body (map b2r e)) in *.
assert (L1 : length R1 = S n).
{ rewrite E1, length_app, L0. simpl. lia. }
set (a := nth ia R0 0). set (b := nth ib R0 0).
assert (Es : nth n R1 0 = rnd (a + b)).
{ rewrite E1, <- L0, nth_middle. reflexivity. }
assert (Ea : nth ia R1 0 = a).
{ rewrite E1, app_nth1 by lia. reflexivity. }
assert (Eb : nth ib R1 0 = b).
{ rewrite E1, app_nth1 by lia. reflexivity. }
set (zz := stepR R1 (Isub n ia)).
set (z1 := stepR (R1 ++ [zz]) (Isub ib (S n))).
change (run stepR [Isub n ia; Isub ib (S n)] R1) with ((R1 ++ [zz]) ++ [z1]) in Hn |- *.
assert (Ezz : zz = rnd (rnd (a + b) - a)).
{ unfold zz. simpl. now rewrite Es, Ea. }
assert (Ez1 : z1 = rnd (b - zz)).
{ unfold z1. simpl. rewrite app_nth1 by lia. rewrite Eb, <- L1, nth_middle. reflexivity. }
rewrite app_nth1 in Hn by (rewrite length_app, L1; simpl; lia).
rewrite app_nth1 in Hn by lia. rewrite Es in Hn.
replace (S (S n)) with (length (R1 ++ [zz])) in Hn by (rewrite length_app, L1; simpl; lia).
rewrite nth_middle in Hn.
(* b and s are values of the IEEE model *)
assert (Hb : Rabs b <= bpow radix2 emax - bpow radix2 (emax - prec)).
{ rewrite <- Eb. rewrite <- M1, nth_b2r. apply abs_B2R_le_emax_minus_prec. exact prec_gt_0_. }
assert (Hs : inrange (rnd (a + b))).
{ rewrite <- Es. rewrite <- M1, nth_b2r. apply b2r_inrange. }
assert (FR1 : Forall inrange R1).
{ rewrite <- M1. apply Forall_forall. intros r Hr. apply in_map_iff in Hr.
  destruct Hr as [x [<- _]]. apply b2r_inrange. }
rewrite Ez1, Ezz in Hn.
destruct (f2s_tail_range a b Hb Hs Hn) as [Hz' Ht'].
apply Forall_app. split; [apply Forall_app; split|]; trivial.
- constructor; [|constructor]. now rewrite Ezz.
- constructor; [|constructor]. now rewrite Ez1, Ezz.
Qed.

(* The same two theorems in the form in which they are applied to a given kernel: the
   program is named, and the two equations that cut it into parts are checked by
   computation. *)
Theorem bridge_tail_prog :
  forall prog body tail (e : list float) z,
  prog = body ++ tail ->
  Forall (fun x => fin x) e ->
  wf body (length e) = true -> covers body (length e) z = true ->
  (z < length e + length body)%nat ->
  (Forall (fun x => fin x) (runB body e) ->
   map b2r (runB body e) = runR body (map b2r e) ->
   Forall inrange (runR prog (map b2r e))) ->
  fin (nth z (runB prog e) d0) ->
  Forall (fun x => fin x) (runB prog e) /\ map b2r (runB prog e) = runR prog (map b2r e).
Proof. intros prog body tail e z ->. apply bridge_tail. Qed.

Theorem bridge_f2s_prog :
  forall prog pre ia ib (e : list float) n,
  n = (length e + length pre)%nat ->
  prog = (pre ++ [Iadd ia ib]) ++ [Isub n ia; Isub ib (S n)] ->
  Forall (fun x => fin x) e ->
  wf (pre ++ [Iadd ia ib]) (length e) = true ->
  covers (pre ++ [Iadd ia ib]) (length e) n = true ->
  normalized_2 emin prec (nth n (runR prog (map b2r e)) 0)
                         (nth (S (S n)) (runR prog (map b2r e)) 0) ->
  fin (nth n (runB prog e) d0) ->
  Forall (fun x => fin x) (runB prog e) /\ map b2r (runB prog e) = runR prog (map b2r e).
Proof. intros prog pre ia ib e n -> ->. apply bridge_f2s. Qed.

(* Reading one value out of the conclusion of these theorems. *)
Lemma sim_nth :
  forall (E : list float) (R : list R) k, map b2r E = R -> b2r (nth k E d0) = nth k R 0.
Proof. intros E R k <-. symmetry. apply nth_b2r. Qed.

End IeeeProgram.
