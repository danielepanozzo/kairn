(* The product of two ball vectors in the IEEE model: its finish bv_conv_finish
   (proofs/gen/IeeeModel.v), and what its radius kernel conv_radius returns.

   bv_conv_finish is norm_finish_1 under the and of the convolution's mask and the bound's:
   its flag is true exactly when both masks are true and the radius is finite, and then the
   result is the radius; otherwise it is a NaN (bv_conv_finish_facts, from
   norm_finish_1_correct of IeeeFoldNorm.v). That is the generated statement
   bv_conv_finish_spec (proofs/gen/IeeeStatements.v): bv_conv_finish_correct. The statement
   was first printed without the two masks of if_all (flag = true <-> finite rz), which was
   false: for rz = +0, okc = false and okg = true the flag is false. The printer now writes the
   masks, as it writes the one mask of if in the statement of norm_finish_1.

   The radius kernel conv_radius on nonnegative operands is nonnegative, +infinity or a NaN,
   and when finite it comes from finite operands and is the real model's on their values
   (conv_radius_ieee). The count, binary_normalize upward of min(n_x, n_y), is nonnegative or
   +infinity and when finite the count rounded up (count_ieee); the bound kernels on such a
   count return a nonnegative g and t, +infinity or NaN (bound_dot_k_nonneg).

   The folds bv_conv_1 and bv_conv_2 (proofs/gen/IeeeFoldModel.v), V1 to V3 of their generated
   statements bv_conv_k_ieee_spec (proofs/gen/IeeeFoldStatements.v), as lemmas of their own,
   bv_conv_k_ieee_v1, _v2, _v3, in the vocabulary and with the binders of the statement, for
   canonical operands (a finite nonnegative radius and finite centers, normalized for two
   limbs, or the radius +infinity and zero centers):
   - V1: the result is canonical, a finite ball vector or the whole space; it has
     conv_length n_x n_y coefficients; the flag is true exactly when the radius is finite;
   - V2: for all members of the operands' balls, chosen entry by entry, coefficient j of their
     exact product is in the ball of coefficient j written;
   - V3: a finite radius comes from finite radii, the coefficients are the real model's
     convolution on the values and the radius the real model's radius.
   How (bv_conv_k_parts). Every center of a canonical operand is finite (zero for the whole
   space), so the records, the steps of a fold of maxima, keep a finite state with a true mask,
   whose values are the real model's maxima (seq_1_state, seq_1_good of IeeeFoldNorm.v; for two
   limbs the record reads the leading limbs, record_2_lead). The radius kernel then gets
   nonnegative operands (or +infinity or NaN), and when the flag is true (bv_conv_finish_facts:
   both masks true and the radius finite) conv_radius_ieee gives finite radii, a finite count
   (the count rounded up), and a finite t, hence the real model's (g, t, ok)
   (bound_dot_k_real of IeeeAccumulator.v): ok is the real model's mask, true. The
   convolution's mask true means every coefficient finite and the real model's dot product on
   the values of its terms (conv_k_ieee_correct of IeeeFoldConv.v), which are the terms of the
   values (conv_terms_map). V2 is then the real-model theorem bv_conv_k_correct (BvConv.v) on
   the values; when the flag is false, the result is the whole space, which contains
   everything.

   V4 is not proved here: for bv_conv_1 it is, with the generated statement, in
   IeeeBvConvFinite.v, and for bv_conv_2 in IeeeBvConvFinite2.v. (As first printed for
   bv_conv_2 it was false in formats of precision 8 and more whose emax is at most 2 prec - 7:
   its condition on the count admitted counts above the largest number, which round up to
   +infinity, and then the bound is not given and the product is the whole space. The condition
   now has the smallest normal number in place of eta: docs/proofs/index.md.) *)
From Stdlib Require Import Reals ZArith List Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format Folds Summation IeeeBridge IeeeVocabulary IeeeOps IeeeFoldNorm.
From Kairn Require IeeeBv IeeeFoldConv IeeeFoldMaps IeeeAccumulator BvConv.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel FoldModel IeeeFoldModel.
Open Scope R_scope.

Lemma bv_conv_finish_facts :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  forall (rz : binary_float prec emax) (okc okg : bool),
  let '(r, flag) := IeeeModel.bv_conv_finish prec emax nan_abs nan_const rz okc okg in
  (flag = true <-> okc = true /\ okg = true /\ finite rz) /\
  (flag = true -> r = rz) /\
  (flag = false -> nan r).
Proof.
intros prec emax Hp He nan_abs nan_const rz okc okg. unfold IeeeModel.bv_conv_finish. cbv zeta.
generalize (norm_finish_1_correct prec emax Hp He nan_abs nan_const rz (okc && okg)).
destruct (IeeeModel.norm_finish_1 prec emax nan_abs nan_const rz (okc && okg)) as [r flag].
intros [H1 [H2 H3]]. split; [|split; assumption].
rewrite H1, andb_true_iff. split.
- intros [[A B] C]. split. exact A. split. exact B. exact C.
- intros [A [B C]]. split. split. exact A. exact B. exact C.
Qed.

(* The generated statement. *)
Theorem bv_conv_finish_correct : bv_conv_finish_spec.
Proof.
intros prec emax Hp He nan_abs nan_const rz okc okg.
exact (bv_conv_finish_facts prec emax Hp He nan_abs nan_const rz okc okg).
Qed.

(** * The radius kernel in the IEEE model *)

(* For the IEEE-model statements of bv_conv_k (V1 to V4, not proved here), one part of what
   they need: the radius kernel conv_radius on nonnegative operands is nonnegative, +infinity
   or a NaN, and a finite radius comes from finite operands and is the real model's on their
   values (conv_radius_ieee), as for the radius kernels of the other ball vectors. *)
Section ConvRadiusIeee.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).

(* A constant rounded up from a nonnegative expression: nonnegative, +infinity when it
   overflows, and its value when finite. *)
Lemma up_const_cases :
  forall e : R, 0 <= e ->
  let c := IeeeOperations.const_of prec emax (round radix2 fexp Zceil e) in
  nonneg_ext c /\ (fin c -> b2r c = round radix2 fexp Zceil e).
Proof.
intros e He c. apply (IeeeBv.const_of_cases prec emax).
- apply generic_format_round; auto with typeclass_instances.
- apply round_ge_generic; auto with typeclass_instances. apply generic_format_0.
Qed.

Lemma conv_radius_ieee :
  forall ma mb rx ry m g t : float,
  nonneg_ext ma -> nonneg_ext mb -> nonneg_ext rx -> nonneg_ext ry -> nonneg_ext m ->
  nonneg_ext g -> nonneg_ext t ->
  let rz := IeeeModel.conv_radius prec emax nan_fma ma mb rx ry m g t in
  nonneg_ext rz /\
  (fin rz -> fin ma /\ fin mb /\ fin rx /\ fin ry /\ fin m /\ fin g /\ fin t /\
   b2r rz = Model.conv_radius emin prec tie_even (b2r ma) (b2r mb) (b2r rx) (b2r ry) (b2r m)
              (b2r g) (b2r t)).
Proof.
intros ma mb rx ry m g t Na Nb Nx Ny Nm Ng Nt.
unfold IeeeModel.conv_radius, Model.conv_radius. cbv zeta.
assert (P0 : 0 <= 4 * (1 + bpow radix2 (- prec)) ^ 8 * bpow radix2 emin +
                  bpow radix2 emin / (2 * bpow radix2 (- prec))).
{ assert (0 < bpow radix2 emin) by apply bpow_gt_0.
  assert (0 < bpow radix2 (- prec)) by apply bpow_gt_0.
  assert (0 <= (1 + bpow radix2 (- prec)) ^ 8) by (apply pow_le; lra).
  assert (0 <= bpow radix2 emin / (2 * bpow radix2 (- prec))).
  { unfold Rdiv. apply Rmult_le_pos. lra. apply Rlt_le, Rinv_0_lt_compat. lra. }
  assert (0 <= 4 * (1 + bpow radix2 (- prec)) ^ 8 * bpow radix2 emin).
  { apply Rmult_le_pos. lra. lra. }
  lra. }
assert (P1 : 0 <= (1 + bpow radix2 (- prec)) ^ 7).
{ apply pow_le. generalize (bpow_gt_0 radix2 (- prec)). lra. }
destruct (up_const_cases _ P0) as [N0 K0].
destruct (up_const_cases _ P1) as [N1 K1].
change (IeeeOperations.const_of prec emax (round radix2 fexp Zceil
          (4 * (1 + bpow radix2 (- prec)) ^ 8 * bpow radix2 emin +
           bpow radix2 emin / (2 * bpow radix2 (- prec)))))
  with (IeeeModel.up_conv_radius_0 prec emax) in N0, K0.
change (IeeeOperations.const_of prec emax (round radix2 fexp Zceil ((1 + bpow radix2 (- prec)) ^ 7)))
  with (IeeeModel.up_conv_radius_1 prec emax) in N1, K1.
destruct (prod_nonneg prec emax nan_fma rx ry Nx Ny) as [Np Kp].
destruct (fma_nonneg prec emax nan_fma mb rx _ Nb Nx Np) as [Nq Kq].
destruct (fma_nonneg prec emax nan_fma ma ry _ Na Ny Nq) as [Nw Kw].
destruct (prod_nonneg prec emax nan_fma ma mb Na Nb) as [Nab Kab].
destruct (fma_nonneg prec emax nan_fma _ g _ Nab Ng Nw) as [Ne Ke].
destruct (fma_nonneg prec emax nan_fma m _ t Nm Ne Nt) as [Ns Ks].
destruct (prod_nonneg prec emax nan_fma m _ Nm N0) as [Nh Kh].
destruct (fma_nonneg prec emax nan_fma _ _ _ Ns N1 Nh) as [Nz Kz].
split. exact Nz.
intros Fz. destruct (Kz Fz) as [Fs [F1 [Fh Vz]]].
destruct (Ks Fs) as [Fm [Fe [Ft Vs]]].
destruct (Ke Fe) as [Fab [Fg [Fw Ve]]].
destruct (Kab Fab) as [Fa [Fb Vab]].
destruct (Kw Fw) as [_ [Fy [Fq Vw]]].
destruct (Kq Fq) as [_ [Fx [Fp Vq]]].
destruct (Kp Fp) as [_ [_ Vp]].
destruct (Kh Fh) as [_ [F0 Vh]].
split. exact Fa. split. exact Fb. split. exact Fx. split. exact Fy. split. exact Fm.
split. exact Fg. split. exact Ft.
rewrite Vz, Vs, Ve, Vab, Vw, Vq, Vp, Vh, (K0 F0), (K1 F1).
reflexivity.
Qed.

End ConvRadiusIeee.

(** * The count and the bound in the IEEE model *)

Section Parts.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).

(* The count, a number of terms rounded up (binary_normalize upward): nonnegative or
   +infinity, and when finite the rounding up of the number. *)
Lemma count_ieee :
  forall n : nat,
  nonneg_ext (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
                (Z.of_nat n) 0 false) /\
  (fin (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
          (Z.of_nat n) 0 false) ->
   b2r (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
          (Z.of_nat n) 0 false) = round radix2 fexp Zceil (INR n)).
Proof.
intros n.
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
              (Z.of_nat n) 0 false).
assert (E : F2R (Float radix2 (Z.of_nat n) 0) = INR n).
{ unfold F2R. cbn [Fnum Fexp]. rewrite <- INR_IZR_INZ. simpl. ring. }
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_UP) (INR n))
  with (round radix2 fexp Zceil (INR n)).
assert (P : 0 <= round radix2 fexp Zceil (INR n)).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. apply pos_INR. }
destruct (Rlt_bool_spec (Rabs (round radix2 fexp Zceil (INR n))) (bpow radix2 emax)) as [L|L].
- intros [E1 [F1 _]]. split.
  + apply (nonneg_ext_finite prec emax). exact F1. rewrite E1. exact P.
  + intros _. exact E1.
- rewrite (Rlt_bool_false (INR n) 0) by apply pos_INR.
  match goal with |- B2FF _ _ ?z = _ -> _ => destruct z as [s|s|s pl H|s mm ee H] end;
  cbn; intros E2; try discriminate E2.
  injection E2 as Es. subst s. split.
  + exact (nonneg_ext_pinf prec emax).
  + intros F. discriminate F.
Qed.

(* A constant rounded up from a nonnegative expression is nonnegative or +infinity. *)
Lemma up_nonneg :
  forall e : R, 0 <= e ->
  nonneg_ext (IeeeOperations.const_of prec emax (round radix2 fexp Zceil e)).
Proof. intros e He. exact (proj1 (up_const_cases prec emax e He)). Qed.

Ltac pos_tac :=
  generalize (bpow_gt_0 radix2 (- prec)) (bpow_gt_0 radix2 emin); intros;
  repeat first
    [ lra
    | apply Rplus_le_le_0_compat
    | apply Rmult_le_pos
    | apply pow_le
    | (unfold Rdiv; apply Rmult_le_pos)
    | (apply Rlt_le; apply Rinv_0_lt_compat) ].

(* The bound kernels on a nonnegative count: g and t are nonnegative, +infinity or NaN. *)
Lemma bound_dot_1_nonneg :
  forall m : float, nonneg_ext m ->
  nonneg_ext (fst (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))) /\
  nonneg_ext (snd (fst (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m))).
Proof.
intros m Nm. unfold IeeeModel.bound_dot_1. cbv zeta. cbn [fst snd].
assert (N0 : nonneg_ext (IeeeModel.up_bound_dot_1_0 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_0, Model.up_bound_dot_1_0; apply up_nonneg; pos_tac).
assert (N1 : nonneg_ext (IeeeModel.up_bound_dot_1_1 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_1, Model.up_bound_dot_1_1; apply up_nonneg; pos_tac).
assert (N2 : nonneg_ext (IeeeModel.up_bound_dot_1_2 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_2, Model.up_bound_dot_1_2; apply up_nonneg; pos_tac).
assert (N3 : nonneg_ext (IeeeModel.up_bound_dot_1_3 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_3, Model.up_bound_dot_1_3; apply up_nonneg; pos_tac).
assert (N4 : nonneg_ext (IeeeModel.up_bound_dot_1_4 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_4, Model.up_bound_dot_1_4; apply up_nonneg; pos_tac).
destruct (prod_nonneg prec emax nan_fma m _ Nm N0) as [Na _].
destruct (prod_nonneg prec emax nan_fma m _ Nm N1) as [Naa _].
destruct (prod_nonneg prec emax nan_fma _ _ Na N2) as [Nd _].
destruct (add_nonneg prec emax nan_plus _ _ Nd N3) as [Nw _].
destruct (prod_nonneg prec emax nan_fma _ _ Naa Nw) as [Ng _].
destruct (prod_nonneg prec emax nan_fma m _ Nm N4) as [Ntm _].
destruct (add_nonneg prec emax nan_plus _ _ Ng N3) as [Nwg _].
destruct (prod_nonneg prec emax nan_fma _ _ Ntm Nwg) as [Nt _].
split; assumption.
Qed.

Lemma bound_dot_2_nonneg :
  forall m : float, nonneg_ext m ->
  nonneg_ext (fst (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))) /\
  nonneg_ext (snd (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))).
Proof.
intros m Nm. unfold IeeeModel.bound_dot_2. cbv zeta. cbn [fst snd].
assert (N0 : nonneg_ext (IeeeModel.up_bound_dot_2_0 prec emax))
  by (unfold IeeeModel.up_bound_dot_2_0, Model.up_bound_dot_2_0; apply up_nonneg; pos_tac).
assert (N1 : nonneg_ext (IeeeModel.up_bound_dot_2_1 prec emax))
  by (unfold IeeeModel.up_bound_dot_2_1, Model.up_bound_dot_2_1; apply up_nonneg; pos_tac).
assert (N2 : nonneg_ext (IeeeModel.up_bound_dot_1_2 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_2, Model.up_bound_dot_1_2; apply up_nonneg; pos_tac).
assert (N3 : nonneg_ext (IeeeModel.up_bound_dot_1_3 prec emax))
  by (unfold IeeeModel.up_bound_dot_1_3, Model.up_bound_dot_1_3; apply up_nonneg; pos_tac).
assert (N4 : nonneg_ext (IeeeModel.up_bound_dot_2_4 prec emax))
  by (unfold IeeeModel.up_bound_dot_2_4, Model.up_bound_dot_2_4; apply up_nonneg; pos_tac).
destruct (prod_nonneg prec emax nan_fma m _ Nm N0) as [Na _].
destruct (prod_nonneg prec emax nan_fma m _ Nm N1) as [Naa _].
destruct (prod_nonneg prec emax nan_fma _ _ Na N2) as [Nd _].
destruct (add_nonneg prec emax nan_plus _ _ Nd N3) as [Nw _].
destruct (prod_nonneg prec emax nan_fma _ _ Naa Nw) as [Ng _].
destruct (prod_nonneg prec emax nan_fma m _ Nm N4) as [Ntm _].
destruct (add_nonneg prec emax nan_plus _ _ Ng N3) as [Nwg _].
destruct (prod_nonneg prec emax nan_fma _ _ Ntm Nwg) as [Nt _].
split; assumption.
Qed.

End Parts.

(** * Lists *)

Lemma combine_map_map :
  forall (A A' B B' : Type) (f : A -> A') (g : B -> B') (l : list A) (l' : list B),
  combine (map f l) (map g l') = map (fun p => (f (fst p), g (snd p))) (combine l l').
Proof.
intros A A' B B' f g l. induction l as [|a l IH]; intros l'; destruct l' as [|b l']; cbn;
  try reflexivity.
f_equal. apply IH.
Qed.

(* The terms of a coefficient of the values are the values of its terms. *)
Lemma conv_terms_map :
  forall (A A' B B' : Type) (f : A -> A') (g : B -> B') (xs : list A) (ys : list B) (j : nat),
  FoldModel.conv_terms (map f xs) (map g ys) j =
  map (fun p => (f (fst p), g (snd p))) (FoldModel.conv_terms xs ys j).
Proof.
intros. unfold FoldModel.conv_terms. rewrite length_map, !firstn_map, skipn_map, <- map_rev.
apply combine_map_map.
Qed.

Lemma Forall2_flip_map_with :
  forall (A B C : Type) (R : A -> B -> Prop) (R' : B -> C -> Prop) (Q : B -> Prop) (f : A -> C)
         (l1 : list A) (l2 : list B),
  (forall a b, R a b -> Q b -> R' b (f a)) -> Forall2 R l1 l2 -> Forall Q l2 ->
  Forall2 R' l2 (map f l1).
Proof.
intros A B C R R' Q f l1 l2 H H2. induction H2 as [|a b l1 l2 Hab _ IH]; intros HQ; cbn [map].
- constructor.
- inversion HQ as [|b' l2' Qb Ql E]. subst. constructor. exact (H a b Hab Qb). exact (IH Ql).
Qed.

Lemma Forall2_join :
  forall (A B C : Type) (P : A -> B -> Prop) (Q : C -> B -> Prop) (R : A -> C -> Prop)
         (l1 : list A) (l2 : list B) (l3 : list C),
  Forall2 P l1 l2 -> Forall2 Q l3 l2 -> (forall a b c, P a b -> Q c b -> R a c) ->
  Forall2 R l1 l3.
Proof.
intros A B C P Q R l1 l2 l3 H1. revert l3.
induction H1 as [|a b l1 l2 Hab _ IH]; intros l3 H2 K.
- inversion H2. constructor.
- inversion H2 as [|c b' l3' l2' Hcb H2' E1 E2]. subst. constructor.
  + exact (K a b c Hab Hcb).
  + exact (IH l3' H2' K).
Qed.

Lemma Forall2_all_map :
  forall (A B C : Type) (R : A -> C -> Prop) (f : B -> C) (l1 : list A) (l2 : list B),
  length l1 = length l2 -> (forall a b, R a (f b)) -> Forall2 R l1 (map f l2).
Proof.
intros A B C R f l1. induction l1 as [|a l1 IH]; intros l2 E H; destruct l2 as [|b l2];
  cbn [length] in E; try discriminate E; cbn [map]; constructor; auto.
Qed.

Lemma Forall2_map_l_intro :
  forall (A A' B : Type) (f : A -> A') (P : A' -> B -> Prop) (Q : A -> B -> Prop)
         (l : list A) (l' : list B),
  (forall a b, Q a b -> P (f a) b) -> Forall2 Q l l' -> Forall2 P (map f l) l'.
Proof. intros A A' B f P Q l l' H H2. induction H2; cbn [map]; constructor; auto. Qed.

(* A canonical operand of one limb: the radius nonnegative or +infinity, every center finite. *)
Lemma canonical_1_finite :
  forall (prec emax : Z) (r : binary_float prec emax) (xs : list (binary_float prec emax)),
  ((finite r /\ 0 <= val r /\ Forall (fun x => ball_finite_1 x r) xs) \/
   (r = infinity prec emax false /\ Forall (fun x => ball_whole_1 x r) xs)) ->
  nonneg_ext r /\ Forall finite xs.
Proof.
intros prec emax r xs H. split.
- apply (IeeeBv.canonical_radius_1 prec emax r _ _ H).
- destruct H as [[_ [_ B]]|[_ B]]; revert B; apply Forall_impl.
  + intros x [F _]. exact F.
  + intros x [[s E] _]. subst x. reflexivity.
Qed.

Lemma Forall2_Forall_l :
  forall (A B : Type) (P : A -> B -> Prop) (Q : A -> Prop) (l : list A) (l' : list B),
  (forall a b, P a b -> Q a) -> Forall2 P l l' -> Forall Q l.
Proof.
intros A B P Q l l' H H2. induction H2 as [|a b l l' Hab _ IH]; constructor; eauto.
Qed.

(** * bv_conv_1 *)

Lemma conv_1_length :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (xs ys : list (binary_float prec emax)),
  length (fst (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys)) =
  FoldModel.conv_length (length xs) (length ys).
Proof.
intros. unfold IeeeFoldModel.conv_1_conv. cbv zeta.
destruct (fold_seq _ true _); cbn [fst]; rewrite ?length_map, length_seq; reflexivity.
Qed.

(* The parts of bv_conv_1 on canonical operands: the radius kernel's result is nonnegative,
   +infinity or NaN; with both masks true and the radius finite, the radii are finite, every
   coefficient is finite and the real model's on the values, the real model's bound is given,
   and the radius is the real model's. *)
Lemma bv_conv_1_parts :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax) (xs ys : list (binary_float prec emax)),
  nonneg_ext rx -> nonneg_ext ry -> Forall finite xs -> Forall finite ys ->
  let c := IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys in
  let sa := fold_seq (IeeeFoldModel.bv_conv_1_record prec emax nan_abs)
              (IeeeOperations.pzero prec emax, true) xs in
  let sb := fold_seq (IeeeFoldModel.bv_conv_1_record prec emax nan_abs)
              (IeeeOperations.pzero prec emax, true) ys in
  let m := IeeeFoldModel.bv_conv_1_count prec emax xs ys in
  let b := IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m in
  let rz := IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m
              (fst (fst b)) (snd (fst b)) in
  nonneg_ext rz /\
  (snd c = true -> snd b = true -> finite rz ->
   finite rx /\ finite ry /\
   Forall2 (fun w s => finite w /\ val w = s) (fst c)
     (FoldModel.conv_1_conv (ieee_emin prec emax) prec tie_even (map val xs) (map val ys)) /\
   FoldModel.bv_conv_1_ok (ieee_emin prec emax) prec tie_even (map val xs) (map val ys) = true /\
   val rz = FoldModel.bv_conv_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map val xs) (map val ys)).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys Nrx Nry Fxs Fys.
assert (Hp2 : (2 <= prec)%Z) by lia.
assert (Hp1 : (1 <= prec)%Z) by lia.
cbv zeta.
generalize (IeeeFoldConv.conv_1_ieee_correct prec emax Hp He nan_abs nan_fma nan_const Hp1 xs ys).
destruct (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys) as [ws okc].
cbn [fst snd]. intros [Hws Hokc].
change (IeeeFoldModel.bv_conv_1_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_1_step prec emax nan_abs).
destruct (seq_1_state prec emax nan_abs xs) as [Ma HSa].
destruct (seq_1_state prec emax nan_abs ys) as [Mb HSb].
destruct (seq_1_good prec emax nan_abs xs Fxs) as [_ [Fa Ea]].
destruct (seq_1_good prec emax nan_abs ys Fys) as [_ [Fb Eb]].
destruct (HSa Fa Ea) as [_ Va]. destruct (HSb Fb Eb) as [_ Vb].
set (sa := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) xs) in *.
set (sb := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) ys) in *.
unfold IeeeFoldModel.bv_conv_1_count.
destruct (count_ieee prec emax (Nat.min (length xs) (length ys))) as [Nm Vm].
set (m := binary_normalize prec emax Hp He BinarySingleNaN.mode_UP
            (Z.of_nat (Nat.min (length xs) (length ys))) 0 false) in *.
generalize (bound_dot_1_nonneg prec emax nan_plus nan_fma m Nm).
generalize (fun Fm => IeeeAccumulator.bound_dot_1_real prec emax nan_plus nan_fma Hp2 m Fm).
destruct (IeeeModel.bound_dot_1 prec emax nan_plus nan_fma m) as [[g t] ok]. cbn [fst snd].
intros Rb [Ng Nt].
destruct (conv_radius_ieee prec emax nan_fma (fst sa) (fst sb) rx ry m g t
            (mag_nonneg_ext prec emax _ Ma) (mag_nonneg_ext prec emax _ Mb) Nrx Nry Nm Ng Nt)
  as [Nz Kz].
split. exact Nz.
intros Ec Eok Fz.
destruct (Kz Fz) as [_ [_ [Frx [Fry [Fm [Fg [Ft Vz]]]]]]].
specialize (Rb Fm Ft).
assert (Cm : FoldModel.bv_conv_1_count (ieee_emin prec emax) prec (map val xs) (map val ys) =
             B2R prec emax m).
{ unfold FoldModel.bv_conv_1_count. rewrite !length_map, (Vm Fm). reflexivity. }
split. exact Frx. split. exact Fry. split; [|split].
- unfold FoldModel.conv_1_conv. rewrite !length_map.
  eapply Forall2_flip_map_with; [|exact Hws|apply Hokc; exact Ec].
  intros j w [H1 _] Fw. cbv zeta in H1. destruct (H1 Fw) as [_ [Vw _]].
  split. exact Fw. rewrite Vw. f_equal. symmetry. apply conv_terms_map.
- unfold FoldModel.bv_conv_1_ok, FoldModel.bv_conv_1_bound.
  rewrite Cm, <- Rb. exact Eok.
- change (val (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m g t))
    with (B2R prec emax (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m g t)).
  rewrite Vz.
  unfold FoldModel.bv_conv_1_radius, FoldModel.bv_conv_1_bound.
  rewrite Cm, <- Rb. cbn [fst snd].
  change FoldModel.bv_conv_1_record with FoldModel.norm_upper_1_step.
  change (B2R prec emax (fst sa)) with (fst (IeeeFoldNorm.vals prec emax sa)).
  change (B2R prec emax (fst sb)) with (fst (IeeeFoldNorm.vals prec emax sb)).
  rewrite Va, Vb. reflexivity.
Qed.

Lemma bv_conv_1_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax) (xs ys : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_1 y ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_1 y ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_1_conv prec emax nan_plus nan_abs nan_fma nan_const rx ry xs ys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_1 w_ r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_1 w_ r_) ws_)) /\
  length ws_ = FoldModel.conv_length (length xs) (length ys) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
destruct (canonical_1_finite prec emax rx xs HX) as [Nrx Fxs].
destruct (canonical_1_finite prec emax ry ys HY) as [Nry Fys].
pose proof (bv_conv_1_parts prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              Nrx Nry Fxs Fys) as P.
pose proof (conv_1_length prec emax Hp He nan_abs nan_fma nan_const xs ys) as L.
unfold IeeeFoldModel.bv_conv_1_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys) as [ws okc].
cbn [fst snd] in P, L |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [_ [_ [Hc _]]].
  pose proof (nonneg_ext_fin prec emax _ Nz Fz) as Pz.
  split; [|split].
  + left. split. exact Fz. split. exact Pz.
    apply (Forall2_Forall_l _ _ _ _ _ _ (fun w s H => proj1 H)) in Hc.
    revert Hc. apply Forall_impl. intros w Fw. split. exact Fw. split. exact Fz. exact Pz.
  + exact L.
  + split; intros _; [exact Fz|reflexivity].
- split; [|split].
  + right. split. reflexivity. apply Forall_map. apply Forall_forall. intros w _.
    split. exists false. reflexivity. reflexivity.
  + rewrite length_map. exact L.
  + split; intros H; discriminate H.
Qed.

Lemma bv_conv_1_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax) (xs ys : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_1 y ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_1 y ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_1_conv prec emax nan_plus nan_abs nan_fma nan_const rx ry xs ys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun w_ s_ => val w_ = s_) ws_
     (FoldModel.conv_1_conv (ieee_emin prec emax) prec tie_even (map (fun x => val x) xs)
        (map (fun y => val y) ys)) /\
   val r_ = FoldModel.bv_conv_1_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun x => val x) xs) (map (fun y => val y) ys)).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
destruct (canonical_1_finite prec emax rx xs HX) as [Nrx Fxs].
destruct (canonical_1_finite prec emax ry ys HY) as [Nry Fys].
pose proof (bv_conv_1_parts prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              Nrx Nry Fxs Fys) as P.
unfold IeeeFoldModel.bv_conv_1_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys) as [ws okc].
cbn [fst snd] in P |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [Frx [Fry [Hc [_ Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + revert Hc. apply Forall2_impl. intros w s [_ E]. exact E.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_conv_1_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus : nan2 prec emax) (nan_abs : nan1 prec emax) (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax) (xs ys : list (binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_1 x rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_1 x rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_1 y ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_1 y ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_1_conv prec emax nan_plus nan_abs nan_fma nan_const rx ry xs ys in
  (forall xs_ ys_ : list R,
   Forall2 (fun x x_ => in_ball_1 x rx x_) xs xs_ ->
   Forall2 (fun y y_ => in_ball_1 y ry y_) ys ys_ ->
   Forall2 (fun j w_ =>
     in_ball_1 w_ r_ (sumR (map (fun xy => fst xy * snd xy) (FoldModel.conv_terms xs_ ys_ j))))
     (seq 0 (FoldModel.conv_length (length xs) (length ys))) ws_).
Proof.
intros prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
assert (Hp2 : (2 <= prec)%Z) by lia.
destruct (canonical_1_finite prec emax rx xs HX) as [Nrx Fxs].
destruct (canonical_1_finite prec emax ry ys HY) as [Nry Fys].
pose proof (bv_conv_1_parts prec emax Hp He nan_plus nan_abs nan_fma nan_const Hp4 rx ry xs ys
              Nrx Nry Fxs Fys) as P.
pose proof (conv_1_length prec emax Hp He nan_abs nan_fma nan_const xs ys) as L.
unfold IeeeFoldModel.bv_conv_1_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_1_conv prec emax nan_abs nan_fma nan_const xs ys) as [ws okc].
cbn [fst snd] in P, L |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [Frx [Fry [Hc [Hok Vr]]]].
  pose proof (nonneg_ext_fin prec emax _ Nz Fz) as Pz.
  assert (Px : 0 <= val rx).
  { destruct HX as [[_ [Q _]]|[E _]]. exact Q. rewrite E in Frx. discriminate Frx. }
  assert (Py : 0 <= val ry).
  { destruct HY as [[_ [Q _]]|[E _]]. exact Q. rewrite E in Fry. discriminate Fry. }
  assert (Fvx : Forall (fun x => fmt (ieee_emin prec emax) prec x) (map val xs)).
  { apply Forall_map. apply Forall_forall. intros x _. apply IeeeFoldMaps.val_format. }
  assert (Fvy : Forall (fun y => fmt (ieee_emin prec emax) prec y) (map val ys)).
  { apply Forall_map. apply Forall_forall. intros y _. apply IeeeFoldMaps.val_format. }
  generalize (BvConv.bv_conv_1_correct (ieee_emin prec emax) prec Hp4 (val rx) (val ry)
                (map val xs) (map val ys) (IeeeFoldMaps.val_format prec emax rx) Px
                (IeeeFoldMaps.val_format prec emax ry) Py Fvx Fvy
                (IeeeAccumulator.ieee_eta_half prec emax Hp2) Hok).
  cbv zeta. intros [_ [_ C]].
  intros xs_ ys_ IX IY.
  assert (IX' : Forall2 (fun x x_ => Rabs (x_ - x) <= val rx) (map val xs) xs_).
  { revert IX. apply Forall2_map_l_intro. intros x x_ [[_ E]|[_ D]].
    - rewrite E in Frx. discriminate Frx.
    - exact D. }
  assert (IY' : Forall2 (fun y y_ => Rabs (y_ - y) <= val ry) (map val ys) ys_).
  { revert IY. apply Forall2_map_l_intro. intros y y_ [[_ E]|[_ D]].
    - rewrite E in Fry. discriminate Fry.
    - exact D. }
  specialize (C xs_ ys_ IX' IY'). rewrite !length_map in C.
  apply (Forall2_join _ _ _ _ _ _ _ _ _ C Hc).
  intros j s w B [Fw Vw]. right. split.
  + split. exact Fw. split. exact Fz. exact Pz.
  + rewrite Vw. cbn [fst]. rewrite Vr. exact B.
- intros xs_ ys_ _ _. apply Forall2_all_map.
  + rewrite length_seq. symmetry. exact L.
  + intros j w. left. split. exists false. reflexivity. reflexivity.
Qed.

(** * bv_conv_2 *)

(* A canonical operand of two limbs: the radius nonnegative or +infinity, every center
   canonical, with a finite leading limb. *)
Lemma canonical_2_finite :
  forall (prec emax : Z) (r : binary_float prec emax)
         (xs : list (binary_float prec emax * binary_float prec emax)),
  ((finite r /\ 0 <= val r /\ Forall (fun x => ball_finite_2 (fst x) (snd x) r) xs) \/
   (r = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) r) xs)) ->
  nonneg_ext r /\ Forall (fun x => canonical_2 (fst x) (snd x)) xs /\
  Forall (fun x => finite (fst x)) xs.
Proof.
intros prec emax r xs H. split; [|split].
- apply (IeeeBv.canonical_radius_1 prec emax r _ _ H).
- exact (IeeeBv.canonical_operands_2 prec emax r _ (fun x => x) xs H).
- destruct H as [[_ [_ B]]|[_ B]]; revert B; apply Forall_impl.
  + intros x [F _]. exact F.
  + intros x [[s E] _]. rewrite E. reflexivity.
Qed.

Lemma conv_2_length :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true})
         (xs ys : list (binary_float prec emax * binary_float prec emax)),
  length (fst (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
                 nan_const xs ys)) =
  FoldModel.conv_length (length xs) (length ys).
Proof.
intros. unfold IeeeFoldModel.conv_2_conv. cbv zeta.
destruct (fold_seq _ true _); cbn [fst]; rewrite ?length_map, length_seq; reflexivity.
Qed.

(* The record of two limbs reads the leading limbs. *)
Lemma record_2_lead :
  forall (prec emax : Z) (nan_abs : nan1 prec emax)
         (l : list (binary_float prec emax * binary_float prec emax)),
  fold_seq (IeeeFoldModel.norm_upper_2_step prec emax nan_abs)
    (IeeeOperations.pzero prec emax, true) l =
  fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
    (IeeeOperations.pzero prec emax, true) (map fst l).
Proof.
intros prec emax nan_abs l.
rewrite <- (fold_seq_map _ _ _ (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) fst _ l).
apply fold_seq_ext. intros s x. reflexivity.
Qed.

Lemma bv_conv_2_parts :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xs ys : list (binary_float prec emax * binary_float prec emax)),
  nonneg_ext rx -> nonneg_ext ry ->
  Forall (fun x => canonical_2 (fst x) (snd x)) xs ->
  Forall (fun y => canonical_2 (fst y) (snd y)) ys ->
  Forall (fun x => finite (fst x)) xs -> Forall (fun y => finite (fst y)) ys ->
  let c := IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
             nan_const xs ys in
  let sa := fold_seq (IeeeFoldModel.bv_conv_2_record prec emax nan_abs)
              (IeeeOperations.pzero prec emax, true) xs in
  let sb := fold_seq (IeeeFoldModel.bv_conv_2_record prec emax nan_abs)
              (IeeeOperations.pzero prec emax, true) ys in
  let m := IeeeFoldModel.bv_conv_2_count prec emax xs ys in
  let b := IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m in
  let rz := IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m
              (fst (fst b)) (snd (fst b)) in
  nonneg_ext rz /\
  (snd c = true -> snd b = true -> finite rz ->
   finite rx /\ finite ry /\
   Forall2 (fun w s => finite (fst w) /\ finite (snd w) /\ (val (fst w), val (snd w)) = s /\
                       normalized_2 (ieee_emin prec emax) prec (fst s) (snd s)) (fst c)
     (FoldModel.conv_2_conv (ieee_emin prec emax) prec tie_even
        (map (fun x => (val (fst x), val (snd x))) xs)
        (map (fun y => (val (fst y), val (snd y))) ys)) /\
   FoldModel.bv_conv_2_ok (ieee_emin prec emax) prec tie_even
     (map (fun x => (val (fst x), val (snd x))) xs)
     (map (fun y => (val (fst y), val (snd y))) ys) = true /\
   val rz = FoldModel.bv_conv_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun x => (val (fst x), val (snd x))) xs)
              (map (fun y => (val (fst y), val (snd y))) ys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys
  Nrx Nry Cx Cy Fxs Fys.
assert (Hp2 : (2 <= prec)%Z) by lia.
cbv zeta.
generalize (IeeeFoldConv.conv_2_ieee_correct prec emax Hp He nan_plus nan_minus nan_opp nan_abs
              nan_fma nan_const Hp4 xs ys Cx Cy).
destruct (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
            xs ys) as [ws okc].
cbn [fst snd]. intros [Hws Hokc].
change (IeeeFoldModel.bv_conv_2_record prec emax nan_abs)
  with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
rewrite !record_2_lead.
assert (Fxs' : Forall finite (map fst xs)) by (apply Forall_map; exact Fxs).
assert (Fys' : Forall finite (map fst ys)) by (apply Forall_map; exact Fys).
destruct (seq_1_state prec emax nan_abs (map fst xs)) as [Ma HSa].
destruct (seq_1_state prec emax nan_abs (map fst ys)) as [Mb HSb].
destruct (seq_1_good prec emax nan_abs (map fst xs) Fxs') as [_ [Fa Ea]].
destruct (seq_1_good prec emax nan_abs (map fst ys) Fys') as [_ [Fb Eb]].
destruct (HSa Fa Ea) as [_ Va]. destruct (HSb Fb Eb) as [_ Vb].
set (sa := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) (map fst xs)) in *.
set (sb := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs)
             (IeeeOperations.pzero prec emax, true) (map fst ys)) in *.
unfold IeeeFoldModel.bv_conv_2_count.
destruct (count_ieee prec emax (Nat.min (length xs) (length ys))) as [Nm Vm].
set (m := binary_normalize prec emax Hp He BinarySingleNaN.mode_UP
            (Z.of_nat (Nat.min (length xs) (length ys))) 0 false) in *.
generalize (bound_dot_2_nonneg prec emax nan_plus nan_fma m Nm).
generalize (fun Fm => IeeeAccumulator.bound_dot_2_real prec emax nan_plus nan_fma Hp4 m Fm).
destruct (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m) as [[g t] ok]. cbn [fst snd].
intros Rb [Ng Nt].
destruct (conv_radius_ieee prec emax nan_fma (fst sa) (fst sb) rx ry m g t
            (mag_nonneg_ext prec emax _ Ma) (mag_nonneg_ext prec emax _ Mb) Nrx Nry Nm Ng Nt)
  as [Nz Kz].
split. exact Nz.
intros Ec Eok Fz.
destruct (Kz Fz) as [_ [_ [Frx [Fry [Fm [Fg [Ft Vz]]]]]]].
specialize (Rb Fm Ft).
set (f := fun x : binary_float prec emax * binary_float prec emax => (val (fst x), val (snd x))).
assert (Cm : FoldModel.bv_conv_2_count (ieee_emin prec emax) prec (map f xs) (map f ys) =
             B2R prec emax m).
{ unfold FoldModel.bv_conv_2_count. rewrite !length_map, (Vm Fm). reflexivity. }
split. exact Frx. split. exact Fry. split; [|split].
- unfold FoldModel.conv_2_conv. rewrite !length_map.
  eapply Forall2_flip_map_with; [|exact Hws|apply Hokc; exact Ec].
  intros j w [H1 _] Fw. cbv zeta in H1. destruct (H1 Fw) as [_ [Fw1 [Vw [Nw _]]]].
  rewrite (conv_terms_map _ _ _ _ f f xs ys j).
  split. exact Fw. split. exact Fw1. split. exact Vw. exact Nw.
- unfold FoldModel.bv_conv_2_ok, FoldModel.bv_conv_2_bound.
  rewrite Cm, <- Rb. exact Eok.
- change (val (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m g t))
    with (B2R prec emax (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m g t)).
  rewrite Vz.
  unfold FoldModel.bv_conv_2_radius, FoldModel.bv_conv_2_bound.
  rewrite Cm, <- Rb. cbn [fst snd].
  change FoldModel.bv_conv_2_record with FoldModel.norm_upper_2_step.
  rewrite !IeeeBv.real_record_2_seq.
  assert (Ex : forall l : list (binary_float prec emax * binary_float prec emax),
               map val (map fst l) = map fst (map f l)).
  { intros l. rewrite !map_map. reflexivity. }
  rewrite Ex in Va, Vb.
  change (B2R prec emax (fst sa)) with (fst (IeeeFoldNorm.vals prec emax sa)).
  change (B2R prec emax (fst sb)) with (fst (IeeeFoldNorm.vals prec emax sb)).
  rewrite Va, Vb. reflexivity.
Qed.

Lemma bv_conv_2_ieee_v1 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xs ys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_2 (fst y) (snd y) ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_2 (fst y) (snd y) ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      rx ry xs ys in
  ((finite r_ /\ 0 <= val r_ /\ Forall (fun w_ => ball_finite_2 (fst w_) (snd w_) r_) ws_) \/
   (r_ = infinity prec emax false /\ Forall (fun w_ => ball_whole_2 (fst w_) (snd w_) r_) ws_)) /\
  length ws_ = FoldModel.conv_length (length xs) (length ys) /\
  (flag_ = true <-> finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
destruct (canonical_2_finite prec emax rx xs HX) as [Nrx [Cx Fxs]].
destruct (canonical_2_finite prec emax ry ys HY) as [Nry [Cy Fys]].
pose proof (bv_conv_2_parts prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys Nrx Nry Cx Cy Fxs Fys) as P.
pose proof (conv_2_length prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              xs ys) as L.
unfold IeeeFoldModel.bv_conv_2_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
            xs ys) as [ws okc].
cbn [fst snd] in P, L |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [_ [_ [Hc _]]].
  pose proof (nonneg_ext_fin prec emax _ Nz Fz) as Pz.
  split; [|split].
  + left. split. exact Fz. split. exact Pz.
    apply (Forall2_Forall_l _ _ _ (fun w => finite (fst w) /\ finite (snd w) /\
             normalized_2 (ieee_emin prec emax) prec (val (fst w)) (val (snd w))))
      in Hc.
    * revert Hc. apply Forall_impl. intros w [F0 [F1 N]].
      split. exact F0. split. exact F1. split. exact N. split. exact Fz. exact Pz.
    * intros w s [F0 [F1 [E N]]]. rewrite <- E in N. cbn [fst snd] in N.
      split. exact F0. split. exact F1. exact N.
  + exact L.
  + split; intros _; [exact Fz|reflexivity].
- split; [|split].
  + right. split. reflexivity. apply Forall_map. apply Forall_forall. intros w _. cbn [fst snd].
    split. exists false. reflexivity. split. exists false. reflexivity. reflexivity.
  + rewrite length_map. exact L.
  + split; intros H; discriminate H.
Qed.

Lemma bv_conv_2_ieee_v3 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xs ys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_2 (fst y) (snd y) ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_2 (fst y) (snd y) ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      rx ry xs ys in
  (finite r_ ->
   finite rx /\ finite ry /\
   Forall2 (fun w_ s_ => (val (fst w_), val (snd w_)) = s_) ws_
     (FoldModel.conv_2_conv (ieee_emin prec emax) prec tie_even
        (map (fun x => (val (fst x), val (snd x))) xs)
        (map (fun y => (val (fst y), val (snd y))) ys)) /\
   val r_ = FoldModel.bv_conv_2_radius (ieee_emin prec emax) prec tie_even (val rx) (val ry)
              (map (fun x => (val (fst x), val (snd x))) xs)
              (map (fun y => (val (fst y), val (snd y))) ys)).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
destruct (canonical_2_finite prec emax rx xs HX) as [Nrx [Cx Fxs]].
destruct (canonical_2_finite prec emax ry ys HY) as [Nry [Cy Fys]].
pose proof (bv_conv_2_parts prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys Nrx Nry Cx Cy Fxs Fys) as P.
unfold IeeeFoldModel.bv_conv_2_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
            xs ys) as [ws okc].
cbn [fst snd] in P |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- intros _. destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [Frx [Fry [Hc [_ Vr]]]].
  split. exact Frx. split. exact Fry. split.
  + revert Hc. apply Forall2_impl. intros w s [_ [_ [E _]]]. exact E.
  + exact Vr.
- intros F. discriminate F.
Qed.

Lemma bv_conv_2_ieee_v2 :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_plus nan_minus : nan2 prec emax) (nan_opp nan_abs : nan1 prec emax)
         (nan_fma : nan3 prec emax)
         (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  (4 <= prec)%Z ->
  forall (rx ry : binary_float prec emax)
         (xs ys : list (binary_float prec emax * binary_float prec emax)),
  ((finite rx /\ 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs) \/
  (rx = infinity prec emax false /\ Forall (fun x => ball_whole_2 (fst x) (snd x) rx) xs)) ->
  ((finite ry /\ 0 <= val ry /\ Forall (fun y => ball_finite_2 (fst y) (snd y) ry) ys) \/
  (ry = infinity prec emax false /\ Forall (fun y => ball_whole_2 (fst y) (snd y) ry) ys)) ->
  let '(ws_, r_, flag_) :=
    IeeeFoldModel.bv_conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
      rx ry xs ys in
  (forall xs_ ys_ : list R,
   Forall2 (fun x x_ => in_ball_2 (fst x) (snd x) rx x_) xs xs_ ->
   Forall2 (fun y y_ => in_ball_2 (fst y) (snd y) ry y_) ys ys_ ->
   Forall2 (fun j w_ =>
     in_ball_2 (fst w_) (snd w_) r_
       (sumR (map (fun xy => fst xy * snd xy) (FoldModel.conv_terms xs_ ys_ j))))
     (seq 0 (FoldModel.conv_length (length xs) (length ys))) ws_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
assert (Hp2 : (2 <= prec)%Z) by lia.
destruct (canonical_2_finite prec emax rx xs HX) as [Nrx [Cx Fxs]].
destruct (canonical_2_finite prec emax ry ys HY) as [Nry [Cy Fys]].
pose proof (bv_conv_2_parts prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys Nrx Nry Cx Cy Fxs Fys) as P.
pose proof (conv_2_length prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              xs ys) as L.
unfold IeeeFoldModel.bv_conv_2_conv. cbv zeta in P |- *.
destruct (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
            xs ys) as [ws okc].
cbn [fst snd] in P, L |- *. destruct P as [Nz P].
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z okc ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z okc o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z okc o) as [r flag]
end.
intros [H1 [H2 _]].
destruct flag; cbv beta iota.
- destruct (proj1 H1 eq_refl) as [Ec [Eg Fz]]. rewrite (H2 eq_refl).
  destruct (P Ec Eg Fz) as [Frx [Fry [Hc [Hok Vr]]]].
  pose proof (nonneg_ext_fin prec emax _ Nz Fz) as Pz.
  assert (Bx : 0 <= val rx /\ Forall (fun x => ball_finite_2 (fst x) (snd x) rx) xs).
  { destruct HX as [[_ [Q B]]|[E _]]. split; assumption. rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\ Forall (fun y => ball_finite_2 (fst y) (snd y) ry) ys).
  { destruct HY as [[_ [Q B]]|[E _]]. split; assumption. rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Bx]. destruct By as [Py By].
  set (f := fun x : binary_float prec emax * binary_float prec emax => (val (fst x), val (snd x)))
    in *.
  assert (Nvx : Forall (fun x => normalized_2 (ieee_emin prec emax) prec (fst x) (snd x))
                       (map f xs)).
  { apply Forall_map. revert Bx. apply Forall_impl. intros x [_ [_ [N _]]]. exact N. }
  assert (Nvy : Forall (fun y => normalized_2 (ieee_emin prec emax) prec (fst y) (snd y))
                       (map f ys)).
  { apply Forall_map. revert By. apply Forall_impl. intros y [_ [_ [N _]]]. exact N. }
  generalize (BvConv.bv_conv_2_correct (ieee_emin prec emax) prec Hp4 (val rx) (val ry)
                (map f xs) (map f ys) (IeeeFoldMaps.val_format prec emax rx) Px
                (IeeeFoldMaps.val_format prec emax ry) Py Nvx Nvy
                (IeeeAccumulator.ieee_eta_half prec emax Hp2) Hok).
  cbv zeta. intros [_ [_ C]].
  intros xs_ ys_ IX IY.
  assert (IX' : Forall2 (fun x x_ => Rabs (x_ - (fst x + snd x)) <= val rx) (map f xs) xs_).
  { revert IX. apply Forall2_map_l_intro. intros x x_ [[_ [_ E]]|[_ D]].
    - rewrite E in Frx. discriminate Frx.
    - exact D. }
  assert (IY' : Forall2 (fun y y_ => Rabs (y_ - (fst y + snd y)) <= val ry) (map f ys) ys_).
  { revert IY. apply Forall2_map_l_intro. intros y y_ [[_ [_ E]]|[_ D]].
    - rewrite E in Fry. discriminate Fry.
    - exact D. }
  specialize (C xs_ ys_ IX' IY'). rewrite !length_map in C.
  apply (Forall2_join _ _ _ _ _ _ _ _ _ C Hc).
  intros j s w B [Fw0 [Fw1 [E N]]]. rewrite <- E in B, N. cbn [fst snd] in B, N. right. split.
  + split. exact Fw0. split. exact Fw1. split. exact N. split. exact Fz. exact Pz.
  + cbn [fst]. rewrite Vr. exact B.
- intros xs_ ys_ _ _. apply Forall2_all_map.
  + rewrite length_seq. symmetry. exact L.
  + intros j w. left. cbn [fst snd]. split. exists false. reflexivity.
    split. exists false. reflexivity. reflexivity.
Qed.
