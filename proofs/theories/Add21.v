(* add_2_1: the sum of a 2-limb number and a number of the format (JMP17 Algorithm 4,
   DWPlusFP).

   Statement (add_2_1_spec): for x normalized and a in the format, in any format with
   gradual underflow and precision at least 3, the result z is normalized and
       |z - (x + a)| <= 2 u^2 |x + a|,
   with no underflow term.

   Route: as for add_2_2. MR22's theorem DWPlusFP_correct (third_party/mr22) gives, in a
   format without underflow, both the bound (as a relative error, so for x + a <> 0) and
   the normalization of the result. Added here: the case x + a = 0, and the transfer to
   the format with gradual underflow (the kernel only adds and subtracts). *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Relative.
From Double Require Import F2Sum DWPlus.
From Kairn Require Import ModelDraft SpecDraft Format Transfer EFT Add22.
Open Scope R_scope.

Section NoUnderflow.
Variable p : Z.
Hypothesis Hp3 : (3 <= p)%Z.

Let Hp : (1 < p)%Z.
Proof. lia. Qed.

Local Instance p_gt_0 : Prec_gt_0 p.
Proof. unfold Prec_gt_0. lia. Qed.

Let ZNE : tie_even = (fun n : Z => negb (Z.even n)).
Proof. reflexivity. Qed.

Notation rndx := (round radix2 (FLX_exp p) (Znearest tie_even)).
Notation formatx := (generic_format radix2 (FLX_exp p)).
Notation DW := (double_word p tie_even).

(* The kernel of the model, run without underflow, is MR22's DWPlusFP. *)
Lemma g_add_2_1_DWPlusFP :
  forall x0 x1 a, formatx x0 -> formatx a ->
  g_add_2_1 rndx x0 x1 a = DWPlusFP p tie_even x0 x1 a.
Proof.
intros x0 x1 a F0 Fa. unfold g_add_2_1.
rewrite g_two_sum_TS, (@TwoSumC p Hp tie_even ZNE a x0 Fa F0).
reflexivity.
Qed.

(* x + a = 0: then a = - x0 and x1 = 0, and every value of the kernel is zero. *)
Lemma DWPlusFP_sum_0 :
  forall x0 x1 a, DW x0 x1 -> formatx a -> x0 + x1 + a = 0 ->
  DWPlusFP p tie_even x0 x1 a = (0, 0).
Proof.
intros x0 x1 a [[F0 F1] Hx] Fa H.
assert (E0 : x0 = - a).
{ rewrite Hx. replace (x0 + x1) with (- a) by lra.
  apply round_generic; auto with typeclass_instances. now apply generic_format_opp. }
assert (E1 : x1 = 0) by lra.
assert (Hsh : TwoSum_sum p tie_even x0 a = 0).
{ rewrite TwoSum_sumE. replace (x0 + a) with 0 by lra. apply round_0; auto with typeclass_instances. }
assert (Hsl : TwoSum_err p tie_even x0 a = 0).
{ rewrite (@TwoSum_correct p Hp tie_even ZNE x0 a F0 Fa), Hsh. lra. }
unfold DWPlusFP. rewrite Hsh, Hsl, E1, Rplus_0_l, round_0; auto with typeclass_instances.
apply Fast2Sum0f. apply generic_format_0.
Qed.

Lemma DWPlusFP_all :
  forall x0 x1 a, DW x0 x1 -> formatx a ->
  DW (fst (DWPlusFP p tie_even x0 x1 a)) (snd (DWPlusFP p tie_even x0 x1 a)) /\
  Rabs (fst (DWPlusFP p tie_even x0 x1 a) + snd (DWPlusFP p tie_even x0 x1 a) - (x0 + x1 + a))
  <= 2 * pow2 (- p) ^ 2 * Rabs (x0 + x1 + a).
Proof.
intros x0 x1 a Hx Fa.
destruct (@DWPlusFP_correct p Hp tie_even ZNE Hp3 x0 x1 a Fa Hx) as [Hrel Hdw].
split. exact Hdw.
destruct (Req_dec (x0 + x1 + a) 0) as [Hs|Hs].
- rewrite (DWPlusFP_sum_0 x0 x1 a Hx Fa Hs), Hs. cbn [fst snd].
  replace (0 + 0 - 0) with 0 by ring. rewrite Rabs_R0. lra.
- revert Hrel. unfold relative_errorDWFP. fold (DWPlusFP p tie_even x0 x1 a).
  unfold Rdiv at 1. rewrite Rabs_mult, Rabs_inv. intros H.
  apply Rmult_le_reg_r with (/ Rabs (x0 + x1 + a)).
  { apply Rinv_0_lt_compat. now apply Rabs_pos_lt. }
  rewrite Rmult_assoc, Rinv_r, Rmult_1_r. exact H.
  now apply Rabs_no_R0.
Qed.

End NoUnderflow.

(** * With gradual underflow: the statement of SpecDraft.v *)

Theorem add_2_1_correct : add_2_1_spec.
Proof.
intros emin prec Hp x0 x1 a [F0 [F1 Hx]] Fa.
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold fmt in F0, F1, Fa.
assert (Dx : double_word prec tie_even x0 x1).
{ repeat split; try now apply generic_format_FLX_FLT with emin.
  rewrite Hx at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
assert (Fax : generic_format radix2 (FLX_exp prec) a) by now apply generic_format_FLX_FLT with emin.
assert (Fz : fmt emin prec (fst (add_2_1 emin prec tie_even x0 x1 a)) /\
             fmt emin prec (snd (add_2_1 emin prec tie_even x0 x1 a))).
{ unfold add_2_1, two_sum, fast_two_sum. cbv zeta beta iota. cbn [fst snd].
  split; apply generic_format_round; auto with typeclass_instances. }
assert (E : add_2_1 emin prec tie_even x0 x1 a = DWPlusFP prec tie_even x0 x1 a).
{ rewrite add_2_1_FLX; trivial.
  apply g_add_2_1_DWPlusFP; trivial; now apply generic_format_FLX_FLT with emin. }
generalize (DWPlusFP_all prec Hp x0 x1 a Dx Fax).
rewrite <- E. destruct Fz as [Fz0 Fz1].
destruct (add_2_1 emin prec tie_even x0 x1 a) as [z0 z1].
cbn [fst snd] in *.
intros [[_ Hz] Hb]. split.
- repeat split; trivial.
  rewrite Hz at 1. unfold RN. symmetry. apply round_plus_FLT_FLX; auto with typeclass_instances.
- exact Hb.
Qed.
