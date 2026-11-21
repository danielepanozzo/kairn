(* The product of two ball vectors in the IEEE model: what holds of its finish,
   bv_conv_finish (proofs/gen/IeeeModel.v).

   bv_conv_finish is norm_finish_1 under the and of the convolution's mask and the bound's:
   its flag is true exactly when both masks are true and the radius is finite, and then the
   result is the radius; otherwise it is a NaN (bv_conv_finish_facts, from
   norm_finish_1_correct of IeeeFoldNorm.v).

   The generated statement bv_conv_finish_spec (proofs/gen/IeeeStatements.v) is not proved:
   its first clause, flag = true <-> finite rz, leaves out the two masks of if_all and is
   false. For rz = +0, okc = false and okg = true (any format), q = false, so norm_finish_1
   tests the canonical NaN and its flag is false, while rz is finite. The clause the claim
   finite_or_nan r flag=flag if_all=okc,okg means is the first conjunct of
   bv_conv_finish_facts, as the statement of norm_finish_1 prints its if=ok. *)
From Stdlib Require Import Reals ZArith List Bool Lia Lra.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements.
From Kairn Require Import Format IeeeBridge IeeeVocabulary IeeeOps IeeeFoldNorm.
From Kairn Require IeeeBv.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel.
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

(* The kernel counterexample to the first clause of bv_conv_finish_spec: a finite radius and a
   false mask of the convolution give a false flag. *)
Lemma bv_conv_finish_spec_counterexample :
  forall (prec emax : Z) (prec_gt_0_ : Prec_gt_0 prec)
         (prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax)
         (nan_abs : nan1 prec emax) (nan_const : {x : binary_float prec emax | is_nan prec emax x = true}),
  let rz := IeeeOperations.pzero prec emax in
  finite rz /\
  snd (IeeeModel.bv_conv_finish prec emax nan_abs nan_const rz false true) = false.
Proof.
intros prec emax Hp He nan_abs nan_const rz. split. reflexivity.
generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const rz false true).
destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const rz false true) as [r flag].
intros [H1 _]. cbn [snd]. destruct flag; [|reflexivity].
destruct (proj1 H1 eq_refl) as [E _]. discriminate E.
Qed.

(* Hence the generated statement is false, in binary64 for instance. *)
Lemma not_bv_conv_finish_spec : ~ bv_conv_finish_spec.
Proof.
intros S.
pose (nn := B754_nan 53 1024 false 1 eq_refl).
assert (Nn : is_nan 53 1024 nn = true) by reflexivity.
pose (na := fun _ : binary_float 53 1024 => exist (fun x => is_nan 53 1024 x = true) nn Nn).
pose (nc := exist (fun x => is_nan 53 1024 x = true) nn Nn).
generalize (S 53%Z 1024%Z eq_refl eq_refl na nc (IeeeOperations.pzero 53 1024) false true)
           (bv_conv_finish_spec_counterexample 53%Z 1024%Z eq_refl eq_refl na nc).
cbv zeta.
destruct (IeeeModel.bv_conv_finish 53 1024 na nc (IeeeOperations.pzero 53 1024) false true)
  as [r flag].
cbn [snd]. intros [[_ B] _] [F E]. rewrite E in B. discriminate (B F).
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
