(* add_2_2: the accurate sum of two 2-limb numbers (JMP17 Algorithm 6, AccurateDWPlusDW).

   Statement (add_2_2_spec): for x and y normalized, in any format with gradual underflow
   and precision at least 3, the result z is normalized and
       |z - (x + y)| <= 3u^2 / (1 - 4u) * |x + y|,
   with no underflow term.

   Route. MR22 (Muller and Rideau, ACM TOMS 48(1), 2022; their Rocq development is in
   third_party/mr22) proved the error bound in a format without underflow, for x + y <> 0
   (theorem DWPlusDW_relerr_bound). Three things are added here.
   1. The result is normalized. MR22's proof establishes it together with the bound
      after reducing to 1 <= x0 < 2, x0 > 0, |y0| <= |x0|, x0 + y0 <> 0 (lemma
      DWPlusDW_relerr_bound_pre), but their final theorem keeps only the bound. The
      same reductions are redone here for the normalization, and the remaining case
      x0 + y0 = 0 is treated directly.
   2. The case x + y = 0, where the result is exactly (0, 0).
   3. Underflow. The kernel only adds and subtracts, so with operands in the format with
      gradual underflow it computes the same values as in the format without underflow
      (Transfer.v); the theorem is carried over as it is. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core Plus_error Relative.
From Double Require Import F2Sum DWPlus.
From Kairn Require Import ModelDraft SpecDraft Format Transfer EFT.
Open Scope R_scope.

(** * Without underflow: MR22's algorithm and what is added to their theorem *)

Section NoUnderflow.
Variable p : Z.
Hypothesis Hp3 : (3 <= p)%Z.

Let Hp : (1 < p)%Z.
Proof. lia. Qed.

Local Instance p_gt_0 : Prec_gt_0 p.
Proof. unfold Prec_gt_0. lia. Qed.

(* MR22 state their theorems for a tie rule `choice` equal to this function. *)
Let ZNE : tie_even = (fun n : Z => negb (Z.even n)).
Proof. reflexivity. Qed.

Notation rndx := (round radix2 (FLX_exp p) (Znearest tie_even)).
Notation formatx := (generic_format radix2 (FLX_exp p)).
Notation DW := (double_word p tie_even).
Notation TS := (TwoSum p tie_even).
Notation F2S := (Fast2Sum p tie_even).

Let rndx_opp : forall x, rndx (- x) = - rndx x.
Proof. intros x. apply round_NE_opp. Qed.

Let Frndx : forall x, formatx (rndx x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.

(* AccurateDWPlusDW in MR22's terms: the term of which their theorems speak. *)
Definition mr_add (xh xl yh yl : R) : R * R :=
  let sh := TwoSum_sum p tie_even xh yh in
  let sl := TwoSum_err p tie_even xh yh in
  let th := TwoSum_sum p tie_even xl yl in
  let tl := TwoSum_err p tie_even xl yl in
  let c := rndx (sl + th) in
  let v := F2S sh c in
  let w := rndx (tl + snd v) in
  F2S (fst v) w.

(* The kernel of the model, run without underflow, is that term. (Kairn's two_sum
   performs MR22's TwoSum with the operands exchanged, which changes nothing.) *)
Lemma g_two_sum_TS : forall a b, g_two_sum rndx a b = TS b a.
Proof.
intros a b. unfold g_two_sum, TwoSum. cbv zeta.
rewrite (Rplus_comm b a). f_equal. f_equal. apply Rplus_comm.
Qed.

Lemma g_add_2_2_mr_add :
  forall x0 x1 y0 y1, formatx x0 -> formatx x1 -> formatx y0 -> formatx y1 ->
  g_add_2_2 rndx x0 x1 y0 y1 = mr_add x0 x1 y0 y1.
Proof.
intros x0 x1 y0 y1 F0 F1 G0 G1. unfold g_add_2_2.
rewrite 2!g_two_sum_TS.
rewrite (@TwoSumC p Hp tie_even ZNE y0 x0 G0 F0), (@TwoSumC p Hp tie_even ZNE y1 x1 G1 F1).
reflexivity.
Qed.

(* Three symmetries of the algorithm: exchanging the operands, changing both signs,
   scaling both operands by a power of two. *)
Lemma mr_add_comm :
  forall xh xl yh yl, formatx xh -> formatx xl -> formatx yh -> formatx yl ->
  mr_add yh yl xh xl = mr_add xh xl yh yl.
Proof.
intros xh xl yh yl Fxh Fxl Fyh Fyl. unfold mr_add, TwoSum_sum, TwoSum_err.
rewrite (@TwoSumC p Hp tie_even ZNE yh xh Fyh Fxh), (@TwoSumC p Hp tie_even ZNE yl xl Fyl Fxl).
reflexivity.
Qed.

Lemma F2S_opp : forall a b, F2S (- a) (- b) = (- fst (F2S a b), - snd (F2S a b)).
Proof. intros a b. now rewrite (@Fast2Sum_asym p tie_even rndx_opp a b). Qed.

Lemma TS_opp : forall a b, TS (- a) (- b) = (- fst (TS a b), - snd (TS a b)).
Proof. intros a b. now rewrite (@TwoSum_asym p tie_even ZNE a b). Qed.

Lemma mr_add_opp :
  forall xh xl yh yl,
  mr_add (- xh) (- xl) (- yh) (- yl) = (- fst (mr_add xh xl yh yl), - snd (mr_add xh xl yh yl)).
Proof.
intros xh xl yh yl. unfold mr_add, TwoSum_sum, TwoSum_err. cbv zeta.
rewrite 2!TS_opp. cbn [fst snd].
set (sh := fst (TS xh yh)). set (sl := snd (TS xh yh)).
set (th := fst (TS xl yl)). set (tl := snd (TS xl yl)).
replace (- sl + - th) with (- (sl + th)) by ring. rewrite rndx_opp.
rewrite F2S_opp. cbn [fst snd].
set (v := F2S sh (rndx (sl + th))).
replace (- tl + - snd v) with (- (tl + snd v)) by ring. rewrite rndx_opp.
apply F2S_opp.
Qed.

Lemma mr_add_scale :
  forall xh xl yh yl e, formatx xh -> formatx xl -> formatx yh -> formatx yl ->
  mr_add (xh * pow2 e) (xl * pow2 e) (yh * pow2 e) (yl * pow2 e)
  = (fst (mr_add xh xl yh yl) * pow2 e, snd (mr_add xh xl yh yl) * pow2 e).
Proof.
intros xh xl yh yl e Fxh Fxl Fyh Fyl. unfold mr_add, TwoSum_sum, TwoSum_err. cbv zeta.
rewrite (@TwoSumS p tie_even xh yh e Fxh Fyh), (@TwoSumS p tie_even xl yl e Fxl Fyl).
cbn [fst snd].
assert (Fts : forall a b, formatx (fst (TS a b)) /\ formatx (snd (TS a b))).
{ intros a b. unfold TwoSum. simpl. split; apply Frndx. }
assert (Ffs : forall a b, formatx (fst (F2S a b)) /\ formatx (snd (F2S a b))).
{ intros a b. unfold Fast2Sum, F2SumFLX.Fast2Sum. simpl. split; apply Frndx. }
set (sh := fst (TS xh yh)). set (sl := snd (TS xh yh)).
set (th := fst (TS xl yl)). set (tl := snd (TS xl yl)).
rewrite <- Rmult_plus_distr_r, (F2SumFLX.round_bpow radix2 p tie_even).
rewrite (@Fast2SumS p tie_even sh (rndx (sl + th)) e); [|apply Fts|apply Frndx].
cbn [fst snd].
set (v := F2S sh (rndx (sl + th))).
rewrite <- Rmult_plus_distr_r, (F2SumFLX.round_bpow radix2 p tie_even).
apply (@Fast2SumS p tie_even); [apply Ffs|apply Frndx].
Qed.

(* Facts about normalized pairs (double-word numbers) without underflow. *)
Lemma DW_abs_le : forall a b, DW a b -> Rabs b <= Rabs a.
Proof.
intros a b H. generalize (@dw_ulp p Hp tie_even a b H). intros Hb.
destruct H as [[Fa Fb] _].
destruct (Req_dec a 0) as [Za|Za].
- rewrite Za, ulp_FLX_0 in Hb; auto with typeclass_instances.
  rewrite Za, Rabs_R0. lra.
- generalize (ulp_le_abs radix2 (FLX_exp p) a Za Fa). generalize (Rabs_pos b). lra.
Qed.

Lemma DW_scale_inv : forall a b e, DW (a * pow2 e) (b * pow2 e) -> DW a b.
Proof.
intros a b e H. generalize (@DW_S p Hp tie_even _ _ (- e)%Z H).
rewrite 2!Rmult_assoc, <- bpow_plus, Z.add_opp_diag_r. simpl. now rewrite 2!Rmult_1_r.
Qed.

(* If two normalized numbers have opposite values, their leading limbs are opposite. *)
Lemma DW_sum_0 :
  forall xh xl yh yl, DW xh xl -> DW yh yl -> xh + xl + (yh + yl) = 0 -> xh + yh = 0.
Proof.
intros xh xl yh yl [_ Hx] [_ Hy] H.
rewrite Hx, Hy. replace (xh + xl) with (- (yh + yl)) by lra.
rewrite rndx_opp. ring.
Qed.

(* When the leading limbs cancel, the result is the error-free sum of the trailing
   limbs, renormalized: it is normalized and exact. *)
Lemma mr_add_cancel :
  forall xh xl yh yl, DW xh xl -> DW yh yl -> xh + yh = 0 ->
  DW (fst (mr_add xh xl yh yl)) (snd (mr_add xh xl yh yl)) /\
  fst (mr_add xh xl yh yl) + snd (mr_add xh xl yh yl) = xh + xl + (yh + yl).
Proof.
intros xh xl yh yl [[Fxh Fxl] Hx] [[Fyh Fyl] Hy] H0.
assert (Hsh : TwoSum_sum p tie_even xh yh = 0).
{ rewrite TwoSum_sumE, H0. apply round_0; auto with typeclass_instances. }
assert (Hsl : TwoSum_err p tie_even xh yh = 0).
{ rewrite (@TwoSum_correct p Hp tie_even ZNE xh yh Fxh Fyh), Hsh, H0. ring. }
assert (Hth : TwoSum_sum p tie_even xl yl = rndx (xl + yl)) by apply TwoSum_sumE.
assert (Htl : TwoSum_err p tie_even xl yl = xl + yl - TwoSum_sum p tie_even xl yl).
{ apply (@TwoSum_correct p Hp tie_even ZNE xl yl Fxl Fyl). }
generalize (@DW_TwoSum p Hp tie_even ZNE xl yl Fxl Fyl). intros Ht.
unfold mr_add. cbv zeta. rewrite Hsh, Hsl.
set (th := TwoSum_sum p tie_even xl yl) in *. set (tl := TwoSum_err p tie_even xl yl) in *.
destruct (Ht) as [[Fth Ftl] _].
rewrite Rplus_0_l, (round_generic radix2 (FLX_exp p) (Znearest tie_even) th Fth).
rewrite (@Fast2Sum0f p tie_even th Fth). cbn [fst snd].
rewrite Rplus_0_r, (round_generic radix2 (FLX_exp p) (Znearest tie_even) tl Ftl).
assert (Hc : Fast2Sum_correct p tie_even th tl).
{ apply (@F2Sum_correct_abs p Hp tie_even rndx_opp); trivial.
  - simpl. lia.
  - now apply DW_abs_le. }
split.
- now apply (@F2Sum_correct_DW' p Hp tie_even th tl).
- unfold Fast2Sum_correct in Hc. cbv zeta in Hc. rewrite Hc, Htl. lra.
Qed.

(* The result is normalized. Successive reductions, each to the previous case: *)

(* ... 1 <= xh <= 2 - 2u, |yh| <= |xh|, xh + yh <> 0: MR22. *)
Lemma mr_add_DW_scaled :
  forall xh xl yh yl, DW xh xl -> DW yh yl ->
  Rabs yh <= Rabs xh -> xh + yh <> 0 -> 1 <= xh <= 2 - 2 * pow2 (- p) ->
  DW (fst (mr_add xh xl yh yl)) (snd (mr_add xh xl yh yl)).
Proof.
intros xh xl yh yl Hx Hy Hxy Hs [H1 H2].
assert (Hn : xh + xl + (yh + yl) <> 0).
{ intros H. apply Hs. now apply DW_sum_0 with xl yl. }
apply (@DWPlusDW_relerr_bound_pre p Hp tie_even ZNE Hp3 xh xl yh yl Hx Hy Hn Hxy Hs); lra.
Qed.

(* ... xh > 0: scale xh into [1, 2). *)
Lemma mr_add_DW_pos :
  forall xh xl yh yl, DW xh xl -> DW yh yl ->
  Rabs yh <= Rabs xh -> xh + yh <> 0 -> 0 < xh ->
  DW (fst (mr_add xh xl yh yl)) (snd (mr_add xh xl yh yl)).
Proof.
intros xh xl yh yl Hx Hy Hxy Hs Hpos.
destruct (Hx) as [[Fxh Fxl] _]. destruct (Hy) as [[Fyh Fyl] _].
destruct (@scale_generic_12 p xh Fxh Hpos) as [e He].
assert (He0 : 0 < pow2 e) by apply bpow_gt_0.
apply DW_scale_inv with e.
generalize (mr_add_scale xh xl yh yl e Fxh Fxl Fyh Fyl). intros E.
replace (fst (mr_add xh xl yh yl) * pow2 e)
  with (fst (mr_add (xh * pow2 e) (xl * pow2 e) (yh * pow2 e) (yl * pow2 e))) by now rewrite E.
replace (snd (mr_add xh xl yh yl) * pow2 e)
  with (snd (mr_add (xh * pow2 e) (xl * pow2 e) (yh * pow2 e) (yl * pow2 e))) by now rewrite E.
apply mr_add_DW_scaled; trivial.
- now apply (@DW_S p Hp tie_even).
- now apply (@DW_S p Hp tie_even).
- rewrite 2!Rabs_mult. apply Rmult_le_compat_r; trivial. apply Rabs_pos.
- rewrite <- Rmult_plus_distr_r. intros H. apply Rmult_integral in H. destruct H; lra.
Qed.

(* ... xh < 0: change the signs. *)
Lemma mr_add_DW_ge :
  forall xh xl yh yl, DW xh xl -> DW yh yl ->
  Rabs yh <= Rabs xh -> xh + yh <> 0 ->
  DW (fst (mr_add xh xl yh yl)) (snd (mr_add xh xl yh yl)).
Proof.
intros xh xl yh yl Hx Hy Hxy Hs.
destruct (Rtotal_order xh 0) as [Hneg|[Hz|Hpos]].
- generalize (mr_add_opp xh xl yh yl). intros E.
  assert (H : DW (fst (mr_add (- xh) (- xl) (- yh) (- yl))) (snd (mr_add (- xh) (- xl) (- yh) (- yl)))).
  { apply mr_add_DW_pos.
    - now apply (@DW_asym p tie_even ZNE).
    - now apply (@DW_asym p tie_even ZNE).
    - now rewrite 2!Rabs_Ropp.
    - lra.
    - lra. }
  rewrite E in H. cbn [fst snd] in H.
  apply (@DW_asym p tie_even ZNE) in H. now rewrite 2!Ropp_involutive in H.
- exfalso. apply Hs. rewrite Hz, Rabs_R0 in Hxy.
  assert (yh = 0). { destruct (Req_dec yh 0) as [Zy|Zy]; trivial.
    generalize (Rabs_pos_lt yh Zy). lra. }
  lra.
- now apply mr_add_DW_pos.
Qed.

(* ... |yh| > |xh|: exchange the operands. With the case xh + yh = 0, all cases. *)
Lemma mr_add_DW :
  forall xh xl yh yl, DW xh xl -> DW yh yl ->
  DW (fst (mr_add xh xl yh yl)) (snd (mr_add xh xl yh yl)).
Proof.
intros xh xl yh yl Hx Hy.
destruct (Req_dec (xh + yh) 0) as [Hs|Hs].
- now apply mr_add_cancel.
- destruct (Rle_or_lt (Rabs yh) (Rabs xh)) as [Hxy|Hxy].
  + now apply mr_add_DW_ge.
  + destruct (Hx) as [[Fxh Fxl] _]. destruct (Hy) as [[Fyh Fyl] _].
    rewrite <- (mr_add_comm xh xl yh yl Fxh Fxl Fyh Fyl).
    apply mr_add_DW_ge; trivial; lra.
Qed.

(* The error bound, including the case x + y = 0. *)
Lemma mr_add_error :
  forall xh xl yh yl, DW xh xl -> DW yh yl ->
  Rabs (fst (mr_add xh xl yh yl) + snd (mr_add xh xl yh yl) - (xh + xl + (yh + yl)))
  <= 3 * pow2 (- p) ^ 2 / (1 - 4 * pow2 (- p)) * Rabs (xh + xl + (yh + yl)).
Proof.
intros xh xl yh yl Hx Hy.
generalize (@boundDWDW_ge_0 p Hp3). intros Hb.
destruct (Req_dec (xh + yh) 0) as [Hs|Hs].
- destruct (mr_add_cancel xh xl yh yl Hx Hy Hs) as [_ E]. rewrite E.
  unfold Rminus. rewrite Rplus_opp_r, Rabs_R0.
  apply Rmult_le_pos; trivial. apply Rabs_pos.
- assert (Hn : xh + xl + (yh + yl) <> 0).
  { intros H. apply Hs. now apply DW_sum_0 with xl yl. }
  generalize (@DWPlusDW_relerr_bound p Hp tie_even ZNE Hp3 xh xl yh yl Hx Hy Hn).
  unfold relative_errorDWDW. fold (mr_add xh xl yh yl).
  unfold Rdiv at 1. rewrite Rabs_mult, Rabs_inv. intros H.
  apply Rmult_le_reg_r with (/ Rabs (xh + xl + (yh + yl))).
  { apply Rinv_0_lt_compat. now apply Rabs_pos_lt. }
  rewrite Rmult_assoc, Rinv_r, Rmult_1_r. exact H.
  now apply Rabs_no_R0.
Qed.

End NoUnderflow.

(** * With gradual underflow: the statement of SpecDraft.v *)

Theorem add_2_2_correct : add_2_2_spec.
Proof.
intros emin prec Hp x0 x1 y0 y1 [F0 [F1 Hx]] [G0 [G1 Hy]].
assert (Hp0 : Prec_gt_0 prec) by (apply prec_gt_0_of_le with 3%Z; lia).
unfold fmt in F0, F1, G0, G1.
(* the operands are normalized in the format without underflow as well *)
assert (Dx : double_word prec tie_even x0 x1).
{ repeat split; try now apply generic_format_FLX_FLT with emin.
  rewrite Hx at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
assert (Dy : double_word prec tie_even y0 y1).
{ repeat split; try now apply generic_format_FLX_FLT with emin.
  rewrite Hy at 1. unfold RN. apply round_plus_FLT_FLX; auto with typeclass_instances. }
(* the limbs of the result are numbers of the format *)
assert (Fz : fmt emin prec (fst (add_2_2 emin prec tie_even x0 x1 y0 y1)) /\
             fmt emin prec (snd (add_2_2 emin prec tie_even x0 x1 y0 y1))).
{ unfold add_2_2, two_sum, fast_two_sum. cbv zeta beta iota. cbn [fst snd].
  split; apply generic_format_round; auto with typeclass_instances. }
(* the kernel computes MR22's term *)
assert (E : add_2_2 emin prec tie_even x0 x1 y0 y1 = mr_add prec x0 x1 y0 y1).
{ rewrite add_2_2_FLX; trivial.
  apply g_add_2_2_mr_add; trivial; now apply generic_format_FLX_FLT with emin. }
generalize (mr_add_DW prec Hp x0 x1 y0 y1 Dx Dy) (mr_add_error prec Hp x0 x1 y0 y1 Dx Dy).
rewrite <- E. destruct Fz as [Fz0 Fz1].
destruct (add_2_2 emin prec tie_even x0 x1 y0 y1) as [z0 z1].
cbn [fst snd] in *.
intros [_ Hz] Hb. split.
- repeat split; trivial.
  rewrite Hz at 1. unfold RN. symmetry. apply round_plus_FLT_FLX; auto with typeclass_instances.
- replace (3 / (1 - 4 * u prec) * u prec ^ 2) with (3 * u prec ^ 2 / (1 - 4 * u prec)).
  exact Hb.
  assert (u prec <= / 8).
  { unfold u. change (/ 8) with (pow2 (-3)). apply bpow_le. lia. }
  field. lra.
Qed.
