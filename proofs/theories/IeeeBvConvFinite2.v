(* The product of two ball vectors of two limbs in the IEEE model, V4: under the conditions of
   its generated statement the result is a finite ball vector (bv_conv_2_ieee_v4), and the
   generated statement bv_conv_2_ieee_spec (proofs/gen/IeeeFoldStatements.v), the
   conjunction of V1 to V4 and the flag (bv_conv_2_ieee_correct). As for one limb
   (IeeeBvConvFinite.v, whose lemmas this file uses), every value the IEEE model computes is
   bounded below the largest number, so that every operation returns its rounded real result.

   The conditions, for finite radii, with n = min(n_x, n_y), Q = 2^(emax - 2), u = 2^-prec,
   eta = 2^emin and eta/(2u) = 2^(2 - emax) the smallest normal number:
   n (4u^2 + eta/(2u)) <= 1/16, rx ry <= Q, (|x| + rx) ry <= Q for every entry x (its value
   x0 + x1), (|y| + ry) rx <= Q for every entry y, n (|x| + rx) (|y| + ry) <= Q for every pair.
   The condition on the count was first printed with eta in place of eta/(2u), and V4 was
   then false (docs/proofs/index.md): the count could exceed the largest number.

   - The count (count_bounded): n eta/(2u) <= 1/16 gives n <= 2^(emax - 6), so the count
     rounded up, m, is finite, at most 2^(emax - 6), and m <= (1 + 2u) n <= 9/8 n (the unit
     in the last place of n >= 1 is at most 2u n). Hence m 4u^2 <= 9/128,
     m eta/(2u) <= 9/128 and m eta <= 9/1024.
   - The bound (bound_dot_2_given), from these, with RN(x) <= (1 + u) x + eta/2,
     RU(x) <= (1 + 2u) x + eta for x >= 0, u <= 1/16 and eta <= 1/64: a <= 0.115 <= up(1/4),
     aa <= 0.125, d <= 0.253, w <= 1.64, g <= 0.23 <= up(1), so the mask is true, and
     tm <= 0.136, wg <= 1.62, t <= 1/4.
   - The coefficients (dot_2_forward): coefficient j is the dot product of two limbs of at
     most n terms, each with |x y| <= Q / n. The step is mul_2_2 then add_2_2: mul_2_2 is
     finite when |x y| <= 2^(emax - 1) (IeeeMul22.v), with the real model's result p,
     |p - x y| <= 4u^2 |x y| + 3/2 eta, so |p0| <= (1 + u) |p| <= 1.08 Q + 0.025; and
     add_2_2 is finite when both leading limbs are at most 5/4 Q (add_2_2_values_finite_wide,
     the proof of add_2_2_values_finite of IeeeAdd22.v with 5/4 Q for Q, which precision 4
     still allows: the last sum is at most 3Q + 2U <= 4Q - U, U = 2^(emax - prec) <= Q/4).
     The real model's state after k <= n terms is within
     ((1 + 4u^2)(1 + 3u^2/(1 - 4u))^(k-1) - 1) A + (1 + 3u^2/(1 - 4u))^(k-1) k 3/2 eta of the
     exact sum (dot_2_seq_correct of FoldSums.v), A <= Q the sum of the magnitudes of the
     products, and (1 + 3u^2/(1 - 4u))^(k-1) <= 16/15 since (k - 1) 4u^2 <= 1/16
     (pow_mult_le_1): so it is at most 13/12 Q + 1/60 and its leading limb at most
     17/16 of that, below 5/4 Q (coef_prefix_2). So every state is finite and the real
     model's, and the convolution's mask is true (conv_2_mask_true).
   - The radius (conv_radius_given_2): with P = (Ma + rx) (Mb + ry), Ma and Mb the largest
     magnitudes of the leading limbs (attained, maxl_attained), each at most (1 + u) times the
     magnitude of its entry, P <= (1 + u)^2 Q <= 5/4 Q and m P <= 9/8 (1 + u)^2 Q <= 13/10 Q
     (P_bound_2); the chain of the radius kernel is then at most 1.2745 P + 3 eta at e,
     1.8 Q at s, 0.19 at hm, and 3.35 Q at the radius.
   Nothing else is assumed of the format than the statement's hypotheses, precision at least 4
   and emax > prec (so Q >= 8, u <= 1/16, eta <= 1/64 and eta/(2u) <= 1/8): every format of the
   statement, the smallest (p = 4, emax = 5) included. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements IeeeStatements FoldStatements IeeeFoldStatements.
From Kairn Require Import Format Normalized Program Folds Summation IeeeBridge IeeeEFT IeeeVocabulary
  IeeeOps.
From Kairn Require Import IeeeFoldNorm IeeeBvConv IeeeBvConvFinite.
From Kairn Require IeeeAdd22 IeeeMul22 IeeeRange IeeeFoldMaps FoldConv FoldNorm FoldSums Directed2 Mul22.
From Kairn Require IeeeOperations.
From Kairn.Gen Require IeeeModel FoldModel IeeeFoldModel.
Import ListNotations.
Open Scope R_scope.

(** * add_2_2 with leading limbs up to 5/4 of 2^(emax - 2) *)

Section Add22Wide.
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
Notation inrange := (inrange emax).
Notation Omega := (Omega prec emax).
Notation stB := (stepB prec emax nan_plus nan_minus nan_opp nan_fma).
Notation runB := (run stB).
Notation runR := (runR emin prec tie_even).
Notation d0 := (d0 prec emax).
Notation finite_all := (Forall (fun x : float => fin x)).
Notation Q := (bpow radix2 (emax - 2)).
Notation U := (bpow radix2 (emax - prec)).

Let Hprec : (0 < prec)%Z.
Proof. exact prec_gt_0_. Qed.
Let Hemax : (prec < emax)%Z.
Proof. exact prec_lt_emax_. Qed.

(* Every value of the real model is in range when the leading limbs are at most 5/4 Q:
   the proof of IeeeAdd22.add_2_2_range, with the bounds |sh| <= 5/2 Q, |vh| <= 3 Q and
   |vh + w| <= 3 Q + 2 U <= 4 Q - U, which precision 4 allows (4 U <= Q). *)
Lemma add_2_2_range_wide :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float,
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) <= 5 / 4 * Q -> Rabs (b2r y0) <= 5 / 4 * Q ->
  Forall inrange (runR IeeeModel.add_2_2_prog [b2r x0; b2r x1; b2r y0; b2r y1]).
Proof.
intros Hp4 x0 x1 y0 y1 Nx Ny Hx0 Hy0.
assert (Hp2 : (2 <= prec)%Z) by lia.
(* powers of two *)
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (Q0 : 0 < Q) by apply bpow_gt_0.
assert (T1 : bpow radix2 emax = 4 * Q).
{ replace emax with (2 + (emax - 2))%Z at 1 by ring. rewrite bpow_plus, pow2_2. ring. }
assert (T4 : 4 * U <= Q).
{ replace (4 * U) with (bpow radix2 (emax - prec + 2)).
  - apply bpow_le. lia.
  - rewrite bpow_plus, pow2_2. ring. }
assert (T5 : 2 * U = bpow radix2 (emax - prec + 1)).
{ rewrite bpow_plus, pow2_1. ring. }
assert (T6 : u prec * Q = / 4 * U).
{ unfold u. rewrite <- bpow_plus.
  replace (emax - prec)%Z with (2 + (- prec + (emax - 2)))%Z by ring.
  rewrite (bpow_plus radix2 2), pow2_2. field. }
assert (EO : Omega = 4 * Q - U).
{ unfold IeeeBridge.Omega. rewrite T1. reflexivity. }
assert (EQ : Q = 2 * bpow radix2 (emax - 3)).
{ replace (emax - 2)%Z with (1 + (emax - 3))%Z by ring. rewrite bpow_plus, pow2_1. ring. }
assert (F52 : format (5 / 2 * Q)).
{ replace (5 / 2 * Q) with (IZR 5 * bpow radix2 (emax - 3)) by (rewrite EQ; field).
  apply (format_multiple emin prec). lia.
  assert (B16 : 16 <= bpow radix2 prec).
  { replace 16 with (bpow radix2 4) by reflexivity. apply bpow_le. lia. }
  generalize (bpow_gt_0 radix2 (emax - 3)). intros B0.
  rewrite Rabs_pos_eq by lra.
  rewrite (bpow_plus radix2 (emax - 3) prec). nra. }
assert (F3 : format (3 * Q)).
{ replace (3 * Q) with (IZR 3 * bpow radix2 (emax - 2)) by reflexivity.
  apply (format_multiple emin prec). lia.
  assert (B16 : 16 <= bpow radix2 prec).
  { replace 16 with (bpow radix2 4) by reflexivity. apply bpow_le. lia. }
  rewrite Rabs_pos_eq by lra.
  rewrite (bpow_plus radix2 (emax - 2) prec). nra. }
(* the operands *)
set (X0 := b2r x0) in *. set (X1 := b2r x1) in *. set (Y0 := b2r y0) in *. set (Y1 := b2r y1) in *.
assert (FX0 : format X0) by apply (b2r_format prec emax).
assert (FX1 : format X1) by apply (b2r_format prec emax).
assert (FY0 : format Y0) by apply (b2r_format prec emax).
assert (FY1 : format Y1) by apply (b2r_format prec emax).
assert (Pu : 0 <= u prec) by (unfold u; apply bpow_ge_0).
assert (HX1 : Rabs X1 <= 5 / 16 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec X0 X1 Nx).
  assert (K : u prec * Rabs X0 <= u prec * (5 / 4 * Q)) by (apply Rmult_le_compat_l; assumption).
  replace (u prec * (5 / 4 * Q)) with (5 / 4 * (u prec * Q)) in K by (field; lra).
  rewrite T6 in K. lra. }
assert (HY1 : Rabs Y1 <= 5 / 16 * U).
{ apply Rle_trans with (1 := normalized_2_tail_rel emin prec Y0 Y1 Ny).
  assert (K : u prec * Rabs Y0 <= u prec * (5 / 4 * Q)) by (apply Rmult_le_compat_l; assumption).
  replace (u prec * (5 / 4 * Q)) with (5 / 4 * (u prec * Q)) in K by (field; lra).
  rewrite T6 in K. lra. }
(* the values, by their names in the kernel *)
cbv [IeeeBridge.runR run stepR nth app IeeeModel.add_2_2_prog].
set (sh := rnd (X0 + Y0)). set (bb1 := rnd (sh - X0)). set (t01 := rnd (sh - bb1)).
set (t11 := rnd (X0 - t01)). set (t21 := rnd (Y0 - bb1)). set (sl := rnd (t11 + t21)).
set (th := rnd (X1 + Y1)). set (bb2 := rnd (th - X1)). set (t02 := rnd (th - bb2)).
set (t12 := rnd (X1 - t02)). set (t22 := rnd (Y1 - bb2)). set (tl := rnd (t12 + t22)).
set (c := rnd (sl + th)). set (vh := rnd (sh + c)). set (z := rnd (vh - sh)).
set (vl := rnd (c - z)). set (w := rnd (tl + vl)). set (z0 := rnd (vh + w)).
set (zz := rnd (z0 - vh)). set (z1 := rnd (w - zz)).
(* two_sum(x0, y0) *)
assert (Hsh : Rabs sh <= 5 / 2 * Q).
{ apply round_abs_le; trivial. apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ish : inrange sh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (TS1 : inrange bb1 /\ inrange t01 /\ inrange t11 /\ inrange t21 /\ inrange sl /\
              sl = X0 + Y0 - sh).
{ apply (two_sum_call_range prec emax Hp2 X0 Y0); trivial; rewrite EO; lra. }
destruct TS1 as [Ibb1 [It01 [It11 [It21 [Isl Esl]]]]].
assert (Hsl : Rabs sl <= / 2 * U).
{ rewrite Esl. replace (X0 + Y0 - sh) with (- (sh - (X0 + Y0))) by ring. rewrite Rabs_Ropp.
  exact (round_error_top prec emax (X0 + Y0) Ish). }
(* two_sum(x1, y1) *)
assert (HXY1 : Rabs (X1 + Y1) <= 5 / 8 * U).
{ apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Hth : Rabs th <= U).
{ apply (RN_abs_le_bpow emin prec). lra. }
assert (Ith : inrange th).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hth. }
assert (TS2 : inrange bb2 /\ inrange t02 /\ inrange t12 /\ inrange t22 /\ inrange tl /\
              tl = X1 + Y1 - th).
{ apply (two_sum_call_range prec emax Hp2 X1 Y1); trivial; rewrite EO; lra. }
destruct TS2 as [Ibb2 [It02 [It12 [It22 [Itl Etl]]]]].
assert (Htl : Rabs tl <= 5 / 8 * U).
{ rewrite Etl. replace (X1 + Y1 - th) with (- (th - (X1 + Y1))) by ring. rewrite Rabs_Ropp.
  apply Rle_trans with (Rabs (0 - (X1 + Y1))).
  - apply (round_nearest prec emax). apply generic_format_0.
  - replace (0 - (X1 + Y1)) with (- (X1 + Y1)) by ring. rewrite Rabs_Ropp. exact HXY1. }
(* c and fast_two_sum(sh, c) *)
assert (Hc : Rabs c <= 2 * U).
{ rewrite T5. apply (RN_abs_le_bpow emin prec). rewrite <- T5.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ic : inrange c).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- T5. }
assert (Hvh : Rabs vh <= 3 * Q).
{ apply round_abs_le; trivial. apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Ivh : inrange vh).
{ apply (le_Omega_inrange prec emax). rewrite EO. lra. }
assert (FS1 : inrange z /\ Rabs vl <= U).
{ apply (fast_two_sum_call_range prec emax sh c); trivial.
  - apply generic_format_round; auto with typeclass_instances.
  - rewrite EO. lra. }
destruct FS1 as [Iz Hvl].
assert (Ivl : inrange vl).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hvl. }
(* w and fast_two_sum(vh, w) *)
assert (Hw : Rabs w <= 2 * U).
{ rewrite T5. apply (RN_abs_le_bpow emin prec). rewrite <- T5.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (Iw : inrange w).
{ apply (le_bpow_inrange emax) with (emax - prec + 1)%Z. lia. now rewrite <- T5. }
assert (Iz0 : inrange z0).
{ apply (rnd_le_Omega prec emax). rewrite EO.
  apply Rle_trans with (1 := Rabs_triang _ _). lra. }
assert (FS2 : inrange zz /\ Rabs z1 <= U).
{ apply (fast_two_sum_call_range prec emax vh w); trivial.
  - apply generic_format_round; auto with typeclass_instances.
  - rewrite EO. lra. }
destruct FS2 as [Izz Hz1].
assert (Iz1 : inrange z1).
{ apply (le_bpow_inrange emax) with (emax - prec)%Z. lia. exact Hz1. }
repeat constructor; trivial; apply b2r_inrange.
Qed.

Theorem add_2_2_values_finite_wide :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r x0) <= 5 / 4 * Q -> Rabs (b2r y0) <= 5 / 4 * Q ->
  let '(z0, z1) := IeeeModel.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1 in
  fin z0 /\ fin z1.
Proof.
intros Hp4 x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hx0 Hy0.
assert (Fe : finite_all [x0; x1; y0; y1]) by (repeat constructor; assumption).
assert (F : finite_all (runB IeeeModel.add_2_2_prog [x0; x1; y0; y1])).
{ apply (run_sim prec emax nan_plus nan_minus nan_opp nan_fma IeeeModel.add_2_2_prog _ Fe).
  now apply add_2_2_range_wide. }
rewrite (IeeeAdd22.add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma).
split; now apply nth_fin.
Qed.

End Add22Wide.

(* n times the sum of the magnitudes of products of two-limb values, each at most K / n. *)
Lemma sumabs_scaled_2 :
  forall (c K : R) (l : list ((R * R) * (R * R))),
  Forall (fun xy => c * Rabs ((fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) <= K) l ->
  c * sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) l) <=
  INR (length l) * K.
Proof.
intros c K l H. induction H as [|xy l Hxy _ IH]; cbn [map length].
- unfold sumabs. cbn. lra.
- rewrite sumabs_cons, S_INR. lra.
Qed.

(* P_bound of IeeeBvConvFinite.v with any bound K in place of 2^(emax - 2). *)
Lemma P_bound_K :
  forall (prec emax : Z) (xs ys : list (binary_float prec emax)) (X Y K : R), 0 <= X -> 0 <= Y ->
  Rabs (X * Y) <= K ->
  Forall (fun x => Rabs ((Rabs (val x) + X) * Y) <= K) xs ->
  Forall (fun y => Rabs ((Rabs (val y) + Y) * X) <= K) ys ->
  Forall (fun x => Forall (fun y =>
    Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (val x) + X) * (Rabs (val y) + Y)) <= K)
    ys) xs ->
  let A := fold_right Rmax 0 (map (fun w => Rabs w) (map val xs)) in
  let B := fold_right Rmax 0 (map (fun w => Rabs w) (map val ys)) in
  (A + X) * (B + Y) <= K /\ INR (Nat.min (length xs) (length ys)) * ((A + X) * (B + Y)) <= K.
Proof.
intros prec emax xs ys X Y K PX PY Hr Hx Hy Hxy A B.
assert (Ag : forall l : list (binary_float prec emax), l <> [] ->
          exists x, In x l /\ fold_right Rmax 0 (map (fun w => Rabs w) (map val l)) = Rabs (val x)).
{ intros l Hl. destruct (maxl_attained (map val l)) as [v [Hv E]].
  { destruct l. contradiction. discriminate. }
  apply in_map_iff in Hv. destruct Hv as [x [Ex Hx']]. exists x. subst v. split; assumption. }
assert (A0 : 0 <= A) by apply FoldNorm.maxl_nonneg.
assert (B0 : 0 <= B) by apply FoldNorm.maxl_nonneg.
assert (PP : 0 <= (A + X) * (B + Y)) by (apply Rmult_le_pos; lra).
assert (K0 : 0 <= K) by (apply Rle_trans with (2 := Hr); apply Rabs_pos).
destruct xs as [|x0 xs'].
- assert (EA : A = 0) by reflexivity.
  assert (EN : INR (Nat.min (length (@nil (binary_float prec emax))) (length ys)) = 0) by reflexivity.
  rewrite EN, Rmult_0_l. split; [|lra].
  rewrite EA, Rplus_0_l.
  destruct ys as [|y0 ys'].
  + assert (EB : B = 0) by reflexivity. rewrite EB, Rplus_0_l.
    apply Rle_trans with (2 := Hr). apply Rle_abs.
  + destruct (Ag (y0 :: ys') ltac:(discriminate)) as [y [Iy EB]]. fold B in EB. rewrite EB.
    pose proof (proj1 (Forall_forall _ _) Hy y Iy) as Ky.
    rewrite Rmult_comm. apply Rle_trans with (2 := Ky). apply Rle_abs.
- destruct (Ag (x0 :: xs') ltac:(discriminate)) as [x [Ix EA]]. fold A in EA.
  destruct ys as [|y0 ys'].
  + assert (EB : B = 0) by reflexivity.
    assert (EN : INR (Nat.min (length (x0 :: xs')) (length (@nil (binary_float prec emax)))) = 0)
      by (cbn [length]; rewrite Nat.min_0_r; reflexivity).
    rewrite EN, Rmult_0_l. split; [|lra]. rewrite EB, Rplus_0_l, EA.
    pose proof (proj1 (Forall_forall _ _) Hx x Ix) as Kx.
    apply Rle_trans with (2 := Kx). apply Rle_abs.
  + destruct (Ag (y0 :: ys') ltac:(discriminate)) as [y [Iy EB]]. fold B in EB.
    pose proof (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hxy x Ix) y Iy) as Kxy.
    set (n := Nat.min (length (x0 :: xs')) (length (y0 :: ys'))) in *.
    assert (N1 : 1 <= INR n).
    { change 1 with (INR 1). apply le_INR. unfold n. cbn [length]. lia. }
    assert (E : INR n * ((A + X) * (B + Y)) = INR n * (Rabs (val x) + X) * (Rabs (val y) + Y))
      by (rewrite EA, EB; ring).
    assert (K2 : INR n * ((A + X) * (B + Y)) <= K).
    { rewrite E. apply Rle_trans with (2 := Kxy). apply Rle_abs. }
    split; [|exact K2].
    assert (K3 : 1 * ((A + X) * (B + Y)) <= INR n * ((A + X) * (B + Y)))
      by (apply Rmult_le_compat_r; lra).
    lra.
Qed.

Section V4.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.
Hypothesis Hp4 : (4 <= prec)%Z.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
Variable nan_const : nan_of.

Notation emin := (3 - emax - prec)%Z.
Notation fexp := (FLT_exp emin prec).
Notation format := (generic_format radix2 fexp).
Notation rnd := (round radix2 fexp (Znearest tie_even)).
Notation RU := (round radix2 fexp Zceil).
Notation fin x := (is_finite prec emax x = true).
Notation b2r := (B2R prec emax).
Notation uu := (u prec).
Notation ee := (eta emin).
Notation Q := (bpow radix2 (emax - 2)).
Notation add := (IeeeOperations.add prec emax nan_plus).
Notation fma := (IeeeOperations.fma prec emax nan_fma).
Notation prod := (IeeeOperations.prod prec emax nan_fma).
Notation pzero := (IeeeOperations.pzero prec emax).
Local Notation maxl l := (fold_right Rmax 0 l).
Local Notation v22 := (fun xy : (float * float) * (float * float) =>
  ((b2r (fst (fst xy)), b2r (snd (fst xy))), (b2r (fst (snd xy)), b2r (snd (snd xy))))).
Local Notation good x :=
  (fin (fst x) /\ fin (snd x) /\ normalized_2 emin prec (b2r (fst x)) (b2r (snd x))).
Local Notation vsum x := (b2r (fst x) + b2r (snd x)).

(** * The format *)

Let U16 : 0 < uu <= / 16.
Proof. exact (uu_bounds prec Hp4). Qed.
Let E64 : 0 < ee <= / 64.
Proof. exact (ee_bounds prec emax Hp4). Qed.
Let Q8 : 8 <= Q.
Proof. exact (Q_ge_8 prec emax Hp4). Qed.
Let T8 : 0 <= ee / (2 * uu) <= / 8.
Proof. exact (ee_2u prec emax Hp4). Qed.
Let He : (prec + 1 <= emax)%Z.
Proof. exact (emax_gt prec emax). Qed.

(* The smallest normal number is 2^(2 - emax). *)
Lemma ee_2u_eq : ee / (2 * uu) = bpow radix2 (2 - emax).
Proof.
unfold eta, u. rewrite (bpow_opp radix2 prec).
replace (2 - emax)%Z with ((3 - emax - prec) + prec + -1)%Z by ring.
rewrite !bpow_plus. change (bpow radix2 (-1)) with (/ 2). field.
apply Rgt_not_eq, bpow_gt_0.
Qed.

Lemma ee_split : ee = ee / (2 * uu) * (2 * uu).
Proof. destruct U16 as [U0 _]. field. lra. Qed.

Lemma four_u2 : 0 <= 4 * uu ^ 2 <= / 64.
Proof.
destruct U16 as [U0 U1]. split.
- apply Rmult_le_pos. lra. apply pow_le. lra.
- assert (K : uu ^ 2 <= / 16 * / 16).
  { simpl. rewrite Rmult_1_r. apply Rmult_le_compat; lra. }
  lra.
Qed.

(* From n (4u^2 + eta/(2u)) <= c, each part, and n eta <= c / 8. *)
Lemma count_parts :
  forall N c : R, 0 <= N -> N * (4 * uu ^ 2 + ee / (2 * uu)) <= c ->
  N * (4 * uu ^ 2) <= c /\ N * (ee / (2 * uu)) <= c /\ N * ee <= c / 8.
Proof.
intros N c PN H.
destruct U16 as [U0 U1]. destruct T8 as [I0 I1]. destruct four_u2 as [S0 S1].
assert (A0 : 0 <= N * (4 * uu ^ 2)) by (apply Rmult_le_pos; lra).
assert (B0 : 0 <= N * (ee / (2 * uu))) by (apply Rmult_le_pos; lra).
rewrite Rmult_plus_distr_l in H.
split. lra. split. lra.
rewrite ee_split. replace (N * (ee / (2 * uu) * (2 * uu))) with ((N * (ee / (2 * uu))) * (2 * uu))
  by ring.
assert (K : (N * (ee / (2 * uu))) * (2 * uu) <= c * (2 * / 16)).
{ apply Rmult_le_compat; lra. }
lra.
Qed.

(** * The count *)

(* n eta/(2u) <= 1/16: n <= 2^(emax - 6), so the count rounded up is finite, and at most
   (1 + 2u) n. *)
Lemma count_bounded :
  forall n : nat, INR n * (ee / (2 * uu)) <= / 16 ->
  fin (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
         (Z.of_nat n) 0 false) /\
  b2r (binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
         (Z.of_nat n) 0 false) = RU (INR n) /\
  0 <= RU (INR n) <= (1 + 2 * uu) * INR n.
Proof.
intros n Hn.
destruct U16 as [U0 U1].
assert (Pn : 0 <= INR n) by apply pos_INR.
assert (Nb : INR n <= bpow radix2 (emax - 6)).
{ rewrite ee_2u_eq in Hn.
  assert (E : INR n = INR n * bpow radix2 (2 - emax) * bpow radix2 (emax - 2)).
  { rewrite Rmult_assoc, <- bpow_plus. replace (2 - emax + (emax - 2))%Z with 0%Z by ring.
    simpl. ring. }
  rewrite E. replace (emax - 6)%Z with (-4 + (emax - 2))%Z by ring. rewrite (bpow_plus radix2 (-4)).
  apply Rmult_le_compat_r. apply bpow_ge_0. change (bpow radix2 (-4)) with (/ 16). exact Hn. }
assert (F6 : format (bpow radix2 (emax - 6))).
{ apply generic_format_bpow. unfold FLT_exp. lia. }
assert (R0 : 0 <= RU (INR n)).
{ apply round_ge_generic; auto with typeclass_instances. apply generic_format_0. }
assert (R6 : RU (INR n) <= bpow radix2 (emax - 6)).
{ apply round_le_generic; auto with typeclass_instances. }
assert (Rm : RU (INR n) <= (1 + 2 * uu) * INR n).
{ destruct n as [|k].
  - change (INR 0) with 0. rewrite round_0; auto with typeclass_instances. lra.
  - set (x := INR (S k)) in *.
    assert (X1 : 1 <= x) by (unfold x; rewrite S_INR; generalize (pos_INR k); lra).
    generalize (error_le_ulp radix2 fexp Zceil x) (Directed2.ulp_le_max emin prec x).
    rewrite (Rabs_pos_eq x) by lra. intros E M. apply Rabs_le_inv in E.
    assert (L : ee <= 2 * uu).
    { unfold eta, u. replace (2 * bpow radix2 (- prec)) with (bpow radix2 (1 + - prec)).
      - apply bpow_le. lia.
      - rewrite bpow_plus. reflexivity. }
    assert (K : Rmax ee (2 * uu * x) = 2 * uu * x) by (apply Rmax_right; nra).
    rewrite K in M. lra. }
generalize (binary_normalize_correct prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
              (Z.of_nat n) 0 false).
assert (E : F2R (Float radix2 (Z.of_nat n) 0) = INR n).
{ unfold F2R. cbn [Fnum Fexp]. rewrite <- INR_IZR_INZ. simpl. ring. }
rewrite E.
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_UP) (INR n))
  with (RU (INR n)).
assert (L : Rabs (RU (INR n)) < bpow radix2 emax).
{ rewrite Rabs_pos_eq by exact R0. apply Rle_lt_trans with (1 := R6). apply bpow_lt. lia. }
rewrite (Rlt_bool_true _ _ L). intros [V [F _]].
split. exact F. split. exact V. split. exact R0. exact Rm.
Qed.

(** * The bound *)

Lemma bound_dot_2_given :
  forall m : float, fin m -> 0 <= b2r m ->
  b2r m * (4 * uu ^ 2) <= 9 / 128 -> b2r m * (ee / (2 * uu)) <= 9 / 128 -> b2r m * ee <= 9 / 1024 ->
  fin (fst (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))) /\
  fin (snd (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))) /\
  snd (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m) = true /\
  0 <= b2r (fst (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))) <= / 2 /\
  0 <= b2r (snd (fst (IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m))) <= / 4.
Proof.
intros m Fm Pm Hu Ht Me.
destruct U16 as [U0 U1]. destruct E64 as [H0 H1]. destruct T8 as [I0 I1].
destruct four_u2 as [S0 S1].
set (M := b2r m) in *.
assert (Me0 : 0 <= M * ee) by (apply Rmult_le_pos; lra).
assert (Mt0 : 0 <= M * (ee / (2 * uu))) by (apply Rmult_le_pos; lra).
assert (Mu0 : 0 <= M * (4 * uu ^ 2)) by (apply Rmult_le_pos; lra).
assert (P1 : 1 + uu <= 17 / 16) by lra.
assert (P0 : 0 <= (1 + uu) ^ 2) by (apply pow_le; lra).
assert (P2 : (1 + uu) ^ 2 <= 17 / 16 * (17 / 16)).
{ replace ((1 + uu) ^ 2) with ((1 + uu) * (1 + uu)) by ring. apply Rmult_le_compat; lra. }
unfold IeeeModel.bound_dot_2. cbv zeta. cbn [fst snd].
set (c0 := IeeeModel.up_bound_dot_2_0 prec emax).
set (c1 := IeeeModel.up_bound_dot_2_1 prec emax).
set (c2 := IeeeModel.up_bound_dot_1_2 prec emax).
set (c3 := IeeeModel.up_bound_dot_1_3 prec emax).
set (c4 := IeeeModel.up_bound_dot_2_4 prec emax).
set (c5 := IeeeModel.up_bound_dot_1_5 prec emax).
set (c6 := IeeeModel.up_bound_dot_1_6 prec emax).
assert (X0 : 0 <= (1 + uu) * (4 * uu ^ 2 + ee / 2) <= 2).
{ split. apply Rmult_le_pos; lra.
  assert (K : (1 + uu) * (4 * uu ^ 2 + ee / 2) <= 17 / 16 * (/ 64 + / 128))
    by (apply Rmult_le_compat; lra). lra. }
assert (X1 : 0 <= (1 + uu) ^ 2 * (4 * uu ^ 2 + ee) <= 2).
{ split. apply Rmult_le_pos; lra.
  assert (K : (1 + uu) ^ 2 * (4 * uu ^ 2 + ee) <= 17 / 16 * (17 / 16) * (/ 64 + / 64))
    by (apply Rmult_le_compat; lra). lra. }
assert (X4 : 0 <= (1 + uu) ^ 2 * (3 / 2 * ee + ee) + ee / (2 * uu) <= 2).
{ assert (K0 : 0 <= (1 + uu) ^ 2 * (3 / 2 * ee + ee)) by (apply Rmult_le_pos; lra).
  assert (K : (1 + uu) ^ 2 * (3 / 2 * ee + ee) <= 17 / 16 * (17 / 16) * (5 / 2 * / 64))
    by (apply Rmult_le_compat; lra).
  split; lra. }
destruct (const_ok prec emax Hp4 _ (proj1 X0) (proj2 X0)) as [Fc0 Vc0].
destruct (const_ok prec emax Hp4 _ (proj1 X1) (proj2 X1)) as [Fc1 Vc1].
destruct (const_ok prec emax Hp4 2 ltac:(lra) ltac:(lra)) as [Fc2 Vc2].
destruct (const_ok prec emax Hp4 (1 + 2 * uu) ltac:(lra) ltac:(lra)) as [Fc3 Vc3].
destruct (const_ok prec emax Hp4 _ (proj1 X4) (proj2 X4)) as [Fc4 Vc4].
destruct (const_ok prec emax Hp4 (1 / 4) ltac:(lra) ltac:(lra)) as [Fc5 Vc5].
destruct (const_ok prec emax Hp4 1 ltac:(lra) ltac:(lra)) as [Fc6 Vc6].
change (IeeeOperations.const_of prec emax (RU ((1 + uu) * (4 * uu ^ 2 + ee / 2)))) with c0 in Fc0, Vc0.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 2 * (4 * uu ^ 2 + ee)))) with c1 in Fc1, Vc1.
change (IeeeOperations.const_of prec emax (RU 2)) with c2 in Fc2, Vc2.
change (IeeeOperations.const_of prec emax (RU (1 + 2 * uu))) with c3 in Fc3, Vc3.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 2 * (3 / 2 * ee + ee) + ee / (2 * uu))))
  with c4 in Fc4, Vc4.
change (IeeeOperations.const_of prec emax (RU (1 / 4))) with c5 in Fc5, Vc5.
change (IeeeOperations.const_of prec emax (RU 1)) with c6 in Fc6, Vc6.
assert (F14 : format (1 / 4)).
{ replace (1 / 4) with (bpow radix2 (-2)) by (change (bpow radix2 (-2)) with (/ 4); field).
  apply generic_format_bpow. unfold FLT_exp. lia. }
assert (F1 : format 1).
{ replace 1 with (bpow radix2 0) by reflexivity. apply generic_format_bpow. unfold FLT_exp. lia. }
assert (F2 : format 2).
{ replace 2 with (bpow radix2 1) by reflexivity. apply generic_format_bpow. unfold FLT_exp. lia. }
rewrite (round_generic _ _ _ (1 / 4) F14) in Vc5.
rewrite (round_generic _ _ _ 1 F1) in Vc6.
rewrite (round_generic _ _ _ 2 F2) in Vc2.
assert (B0 : 0 <= b2r c0 <= 9 / 8 * (17 / 16 * (4 * uu ^ 2 + ee / 2)) + ee).
{ rewrite Vc0. apply (RU_bound prec emax Hp4). apply Rmult_le_pos; lra.
  apply Rmult_le_compat_r; lra. }
assert (B1 : 0 <= b2r c1 <= 9 / 8 * (17 / 16 * (17 / 16) * (4 * uu ^ 2 + ee)) + ee).
{ rewrite Vc1. apply (RU_bound prec emax Hp4). apply Rmult_le_pos; lra.
  apply Rmult_le_compat_r; lra. }
assert (B3 : 0 <= b2r c3 <= 9 / 8 * (9 / 8) + ee).
{ rewrite Vc3. apply (RU_bound prec emax Hp4); lra. }
assert (B4 : 0 <= b2r c4 <= 9 / 8 * (17 / 16 * (17 / 16) * (3 / 2 * ee + ee) + ee / (2 * uu)) + ee).
{ rewrite Vc4. apply (RU_bound prec emax Hp4). lra.
  assert (K : (1 + uu) ^ 2 * (3 / 2 * ee + ee) <= 17 / 16 * (17 / 16) * (3 / 2 * ee + ee))
    by (apply Rmult_le_compat_r; lra). lra. }
(* m times the constants *)
assert (MB0 : 0 <= M * b2r c0 <= / 10).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c0 <= M * (9 / 8 * (17 / 16 * (4 * uu ^ 2 + ee / 2)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (4 * uu ^ 2 + ee / 2)) + ee)) with
    (153 / 128 * (M * (4 * uu ^ 2)) + 153 / 256 * (M * ee) + M * ee) in K by (field; lra). lra. }
assert (MB1 : 0 <= M * b2r c1 <= 11 / 100).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c1 <= M * (9 / 8 * (17 / 16 * (17 / 16) * (4 * uu ^ 2 + ee)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (17 / 16) * (4 * uu ^ 2 + ee)) + ee)) with
    (9 / 8 * (289 / 256) * (M * (4 * uu ^ 2)) + 9 / 8 * (289 / 256) * (M * ee) + M * ee) in K
    by (field; lra). lra. }
assert (MB4 : 0 <= M * b2r c4 <= 12 / 100).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c4 <=
              M * (9 / 8 * (17 / 16 * (17 / 16) * (3 / 2 * ee + ee) + ee / (2 * uu)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (17 / 16 * (17 / 16) * (3 / 2 * ee + ee) + ee / (2 * uu)) + ee)) with
    (9 / 8 * (289 / 256 * (5 / 2) * (M * ee) + M * (ee / (2 * uu))) + M * ee) in K by (field; lra).
  lra. }
(* the values *)
set (a := prod m c0). set (aa := prod m c1). set (d := prod a c2). set (w := add d c3).
set (g := prod aa w). set (tm := prod m c4). set (wg := add g c3). set (t := prod tm wg).
pose proof (rnd_bound prec emax Hp4 (M * b2r c0 + 0) (/ 10) ltac:(lra) ltac:(lra)) as [Ra0 Ra1].
destruct (prod_ok prec emax Hp4 nan_fma m c0 Fm Fc0 (range_le emax _ _ Ra0 Ra1 ltac:(lra)))
  as [Fa Ea].
fold a in Fa, Ea. fold M in Ea.
assert (Ba : 0 <= b2r a <= 115 / 1000) by (rewrite Ea; lra).
pose proof (rnd_bound prec emax Hp4 (M * b2r c1 + 0) (11 / 100) ltac:(lra) ltac:(lra))
  as [Raa0 Raa1].
destruct (prod_ok prec emax Hp4 nan_fma m c1 Fm Fc1 (range_le emax _ _ Raa0 Raa1 ltac:(lra)))
  as [Faa Eaa].
fold aa in Faa, Eaa. fold M in Eaa.
assert (Baa : 0 <= b2r aa <= 125 / 1000) by (rewrite Eaa; lra).
assert (Rd : 0 <= rnd (b2r a * b2r c2 + 0) /\
             rnd (b2r a * b2r c2 + 0) <= 17 / 16 * (115 / 1000 * 2) + ee / 2).
{ rewrite Vc2. apply (rnd_bound prec emax Hp4); lra. }
destruct Rd as [Rd0 Rd1].
destruct (prod_ok prec emax Hp4 nan_fma a c2 Fa Fc2 (range_le emax _ _ Rd0 Rd1 ltac:(lra)))
  as [Fd Ed].
fold d in Fd, Ed.
assert (Bd : 0 <= b2r d <= 253 / 1000) by (rewrite Ed; lra).
pose proof (rnd_bound prec emax Hp4 (b2r d + b2r c3) (253 / 1000 + (9 / 8 * (9 / 8) + / 64))
              ltac:(lra) ltac:(lra)) as [Rw0 Rw1].
destruct (add_ok prec emax Hp4 nan_plus d c3 Fd Fc3 (range_le emax _ _ Rw0 Rw1 ltac:(lra)))
  as [Fw Ew].
fold w in Fw, Ew.
assert (Bw : 0 <= b2r w <= 164 / 100) by (rewrite Ew; lra).
pose proof (mul_le (b2r aa) (b2r w) (125 / 1000) (164 / 100) ltac:(lra) ltac:(lra) ltac:(lra)
              ltac:(lra)) as [Paw0 Paw1].
pose proof (rnd_bound prec emax Hp4 (b2r aa * b2r w + 0) (125 / 1000 * (164 / 100)) ltac:(lra)
              ltac:(lra)) as [Rg0 Rg1].
destruct (prod_ok prec emax Hp4 nan_fma aa w Faa Fw (range_le emax _ _ Rg0 Rg1 ltac:(lra)))
  as [Fg Eg].
fold g in Fg, Eg.
assert (Bg : 0 <= b2r g <= 23 / 100) by (rewrite Eg; lra).
pose proof (rnd_bound prec emax Hp4 (M * b2r c4 + 0) (12 / 100) ltac:(lra) ltac:(lra))
  as [Rtm0 Rtm1].
destruct (prod_ok prec emax Hp4 nan_fma m c4 Fm Fc4 (range_le emax _ _ Rtm0 Rtm1 ltac:(lra)))
  as [Ftm Etm].
fold tm in Ftm, Etm. fold M in Etm.
assert (Btm : 0 <= b2r tm <= 136 / 1000) by (rewrite Etm; lra).
pose proof (rnd_bound prec emax Hp4 (b2r g + b2r c3) (23 / 100 + (9 / 8 * (9 / 8) + / 64))
              ltac:(lra) ltac:(lra)) as [Rwg0 Rwg1].
destruct (add_ok prec emax Hp4 nan_plus g c3 Fg Fc3 (range_le emax _ _ Rwg0 Rwg1 ltac:(lra)))
  as [Fwg Ewg].
fold wg in Fwg, Ewg.
assert (Bwg : 0 <= b2r wg <= 162 / 100) by (rewrite Ewg; lra).
pose proof (mul_le (b2r tm) (b2r wg) (136 / 1000) (162 / 100) ltac:(lra) ltac:(lra) ltac:(lra)
              ltac:(lra)) as [Pt0 Pt1].
pose proof (rnd_bound prec emax Hp4 (b2r tm * b2r wg + 0) (136 / 1000 * (162 / 100))
              ltac:(lra) ltac:(lra)) as [Rt0 Rt1].
destruct (prod_ok prec emax Hp4 nan_fma tm wg Ftm Fwg (range_le emax _ _ Rt0 Rt1 ltac:(lra)))
  as [Ft Et].
fold t in Ft, Et.
assert (Bt : 0 <= b2r t <= / 4) by (rewrite Et; lra).
split. exact Fg. split. exact Ft. split; [|split; [lra|lra]].
rewrite (le_finite prec emax a c5 Fa Fc5), (le_finite prec emax g c6 Fg Fc6), Vc5, Vc6.
rewrite !Rle_bool_true by lra. reflexivity.
Qed.

(** * The coefficients *)

(* One step of the dot product of two limbs, mul_2_2 then add_2_2, on a finite normalized
   state whose leading limb is at most 5/4 Q and finite normalized operands whose exact
   product is at most Q: finite, with the values of the real model. *)
Lemma dot_step_2_forward :
  forall s0 s1 x0 x1 y0 y1 : float,
  fin s0 -> fin s1 -> fin x0 -> fin x1 -> fin y0 -> fin y1 ->
  normalized_2 emin prec (b2r s0) (b2r s1) ->
  normalized_2 emin prec (b2r x0) (b2r x1) -> normalized_2 emin prec (b2r y0) (b2r y1) ->
  Rabs (b2r s0) <= 5 / 4 * Q ->
  Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= Q ->
  let t := IeeeModel.dot_step_2 prec emax nan_plus nan_minus nan_opp nan_fma s0 s1 x0 x1 y0 y1 in
  fin (fst t) /\ fin (snd t) /\
  (b2r (fst t), b2r (snd t)) =
    dot_step_2 emin prec tie_even (b2r s0) (b2r s1) (b2r x0) (b2r x1) (b2r y0) (b2r y1).
Proof.
intros s0 s1 x0 x1 y0 y1 Fs0 Fs1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny Hs Hxy t.
destruct U16 as [U0 U1]. destruct E64 as [H0 H1]. destruct four_u2 as [S0 S1].
assert (H2Q : Q <= bpow radix2 (emax - 1)) by (apply bpow_le; lia).
generalize (IeeeMul22.mul_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp4
              x0 x1 y0 y1 Fx0 Fx1 Fy0 Fy1 Nx Ny ltac:(lra)).
generalize (IeeeMul22.mul_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma Hp4
              x0 x1 y0 y1 Fx0 Fx1 Fy0 Fy1 Nx Ny).
generalize (Mul22.mul_2_2_correct emin prec Hp4 (b2r x0) (b2r x1) (b2r y0) (b2r y1) Nx Ny).
unfold t, IeeeModel.dot_step_2, dot_step_2.
destruct (IeeeModel.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [q0 q1].
destruct (mul_2_2 emin prec tie_even (b2r x0) (b2r x1) (b2r y0) (b2r y1)) as [p0 p1].
intros [Np Ep] V [_ [Fq0 Fq1]].
destruct (V Fq0) as [_ Eq]. injection Eq as E0 E1. subst p0 p1.
(* the leading limb of the product *)
assert (Hq : Rabs (b2r q0) <= 5 / 4 * Q).
{ set (XY := (b2r x0 + b2r x1) * (b2r y0 + b2r y1)) in *.
  assert (K1 : 4 * uu ^ 2 * Rabs XY <= / 64 * Q).
  { apply Rmult_le_compat; try lra. apply Rabs_pos. }
  assert (Hp : Rabs (b2r q0 + b2r q1) <= Q + / 64 * Q + 3 / 2 * ee).
  { generalize (Rabs_le_add (b2r q0 + b2r q1) XY). lra. }
  generalize (normalized_2_tail_rel_value emin prec (b2r q0) (b2r q1) Np). intros T.
  assert (K : Rabs (b2r q0) <= Rabs (b2r q0 + b2r q1) + Rabs (b2r q1)).
  { replace (b2r q0) with ((b2r q0 + b2r q1) + - b2r q1) at 1 by ring.
    apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra. }
  assert (K2 : uu * Rabs (b2r q0 + b2r q1) <= / 16 * (Q + / 64 * Q + 3 / 2 * ee)).
  { apply Rmult_le_compat; try lra. apply Rabs_pos. }
  lra. }
generalize (add_2_2_values_finite_wide prec emax nan_plus nan_minus nan_opp nan_fma Hp4
              s0 s1 q0 q1 Fs0 Fs1 Fq0 Fq1 Ns Np Hs Hq).
generalize (IeeeAdd22.add_2_2_values prec emax nan_plus nan_minus nan_opp nan_fma ltac:(lia)
              s0 s1 q0 q1 Fs0 Fs1 Fq0 Fq1 Ns Np).
destruct (IeeeModel.add_2_2 prec emax nan_plus nan_minus s0 s1 q0 q1) as [z0 z1].
intros W [Fz0 Fz1]. destruct (W Fz0) as [_ Ez].
rewrite <- Ez. cbn [fst snd]. split. exact Fz0. split. exact Fz1. reflexivity.
Qed.

(* The dot product of two limbs on finite normalized terms, each of exact product at most Q,
   when the real model's state after every prefix has a leading limb at most 5/4 Q: every
   IEEE state is finite and the real model's. *)
Lemma dot_2_forward :
  forall l : list ((float * float) * (float * float)),
  Forall (fun xy => good (fst xy) /\ good (snd xy)) l ->
  Forall (fun xy => Rabs (vsum (fst xy) * vsum (snd xy)) <= Q) l ->
  (forall l1 l2, l = l1 ++ l2 ->
     Rabs (fst (FoldModel.dot_2_seq emin prec tie_even (map v22 l1))) <= 5 / 4 * Q) ->
  fin (fst (fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
              (pzero, pzero) l)) /\
  fin (snd (fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
              (pzero, pzero) l)) /\
  (b2r (fst (fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
               (pzero, pzero) l)),
   b2r (snd (fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
               (pzero, pzero) l))) =
  FoldModel.dot_2_seq emin prec tie_even (map v22 l).
Proof.
induction l as [|a l IH] using rev_ind; intros G P H.
- split. reflexivity. split. reflexivity. reflexivity.
- apply Forall_app in G. destruct G as [Gl Ga]. apply Forall_inv in Ga.
  apply Forall_app in P. destruct P as [Pl Pa]. apply Forall_inv in Pa.
  assert (H' : forall l1 l2, l = l1 ++ l2 ->
     Rabs (fst (FoldModel.dot_2_seq emin prec tie_even (map v22 l1))) <= 5 / 4 * Q).
  { intros l1 l2 E. apply (H l1 (l2 ++ [a])). rewrite E, app_assoc. reflexivity. }
  destruct (IH Gl Pl H') as [F0 [F1 V]].
  specialize (H l [a] eq_refl).
  assert (Nv : Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                                normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) (map v22 l)).
  { apply Forall_map. revert Gl. apply Forall_impl. intros xy [[_ [_ Nx]] [_ [_ Ny]]].
    cbn [fst snd]. split; assumption. }
  generalize (FoldSums.dot_2_seq_correct emin prec Hp4 (map v22 l) Nv). cbv zeta. intros [Ns _].
  rewrite <- V in H, Ns. cbn [fst snd] in H, Ns.
  set (s := fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
              (pzero, pzero) l) in *.
  assert (Es : fold_seq (IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma)
                 (pzero, pzero) (l ++ [a]) =
               IeeeFoldModel.dot_2_step prec emax nan_plus nan_minus nan_opp nan_fma s a).
  { unfold s, fold_seq. rewrite fold_left_app. reflexivity. }
  assert (Er : FoldModel.dot_2_seq emin prec tie_even (map v22 (l ++ [a])) =
               FoldModel.dot_2_step emin prec tie_even
                 (FoldModel.dot_2_seq emin prec tie_even (map v22 l)) (v22 a)).
  { unfold FoldModel.dot_2_seq, fold_seq. rewrite map_app, fold_left_app. reflexivity. }
  rewrite Es, Er, <- V.
  destruct Ga as [[Fx0 [Fx1 Nx]] [Fy0 [Fy1 Ny]]].
  unfold IeeeFoldModel.dot_2_step, FoldModel.dot_2_step. cbv beta. cbn [fst snd].
  exact (dot_step_2_forward (fst s) (snd s) (fst (fst a)) (snd (fst a)) (fst (snd a)) (snd (snd a))
           F0 F1 Fx0 Fx1 Fy0 Fy1 Ns Nx Ny H Pa).
Qed.

(* The real model's state after a prefix of the terms of a coefficient: its leading limb is at
   most 5/4 Q. *)
Lemma coef_prefix_2 :
  forall (xs ys : list (float * float)) (j : nat) (l1 l2 : list ((float * float) * (float * float))),
  Forall (fun x => good x) xs -> Forall (fun y => good y) ys ->
  INR (Nat.min (length xs) (length ys)) * (4 * uu ^ 2 + ee / (2 * uu)) <= / 16 ->
  Forall (fun x => Forall (fun y =>
    INR (Nat.min (length xs) (length ys)) * (Rabs (vsum x) * Rabs (vsum y)) <= Q) ys) xs ->
  FoldModel.conv_terms xs ys j = l1 ++ l2 ->
  Rabs (fst (FoldModel.dot_2_seq emin prec tie_even (map v22 l1))) <= 5 / 4 * Q.
Proof.
intros xs ys j l1 l2 Gx Gy Hn Hp E.
destruct U16 as [U0 U1]. destruct E64 as [F0 F1]. destruct four_u2 as [S0 S1].
set (n := Nat.min (length xs) (length ys)) in *.
assert (Pn : 0 <= INR n) by apply pos_INR.
destruct (count_parts (INR n) (/ 16) Pn Hn) as [Mu [_ Me]].
set (vs := map v22 l1).
assert (T : Forall (fun ab => In (fst ab) xs /\ In (snd ab) ys) l1).
{ generalize (FoldConv.conv_terms_Forall _ _ (fun x => In x xs) (fun y => In y ys) xs ys j
                (proj2 (Forall_forall _ _) (fun x H => H))
                (proj2 (Forall_forall _ _) (fun y H => H))).
  rewrite E. intros T. apply Forall_app in T. exact (proj1 T). }
assert (Nv : Forall (fun xy => normalized_2 emin prec (fst (fst xy)) (snd (fst xy)) /\
                              normalized_2 emin prec (fst (snd xy)) (snd (snd xy))) vs).
{ unfold vs. apply Forall_map. revert T. apply Forall_impl. intros [x y] [Ix Iy]. cbn [fst snd].
  split.
  - exact (proj2 (proj2 (proj1 (Forall_forall _ _) Gx x Ix))).
  - exact (proj2 (proj2 (proj1 (Forall_forall _ _) Gy y Iy))). }
generalize (FoldSums.dot_2_seq_correct emin prec Hp4 vs Nv). cbv zeta. intros [Ns Er].
assert (Kn : (length vs <= n)%nat).
{ unfold vs. rewrite length_map. pose proof (FoldConv.conv_terms_length _ _ xs ys j) as L.
  rewrite E, length_app in L. unfold n. lia. }
set (k := length vs) in *.
assert (Nk : INR k <= INR n) by (apply le_INR; exact Kn).
assert (Pk : 0 <= INR k) by apply pos_INR.
(* delta = 3u^2/(1 - 4u) <= 4u^2 *)
set (dl := 3 * uu ^ 2 / (1 - 4 * uu)) in *.
assert (D0 : 0 <= dl).
{ unfold dl, Rdiv. apply Rmult_le_pos.
  - apply Rmult_le_pos. lra. apply pow_le. lra.
  - apply Rlt_le, Rinv_0_lt_compat. lra. }
assert (D1 : dl <= 4 * uu ^ 2).
{ unfold dl. apply Rmult_le_reg_r with (1 - 4 * uu). lra.
  unfold Rdiv. rewrite Rmult_assoc, Rinv_l by lra.
  assert (K : 0 <= uu ^ 2) by (apply pow_le; lra). nra. }
generalize (pow_mult_le_1 dl (k - 1) D0). intros PW.
assert (Kd : INR (k - 1) * dl <= / 16).
{ assert (K1 : INR (k - 1) <= INR n) by (apply le_INR; lia).
  assert (K2 : INR (k - 1) * dl <= INR n * (4 * uu ^ 2))
    by (apply Rmult_le_compat; try lra; apply pos_INR).
  lra. }
assert (PD0 : 0 <= (1 + dl) ^ (k - 1)) by (apply pow_le; lra).
assert (PD : (1 + dl) ^ (k - 1) <= 16 / 15).
{ assert (K1 : (1 + dl) ^ (k - 1) * (15 / 16) <= (1 + dl) ^ (k - 1) * (1 - INR (k - 1) * dl))
    by (apply Rmult_le_compat_l; lra). lra. }
assert (PD1 : 1 <= (1 + dl) ^ (k - 1)) by (apply pow_R1_Rle; lra).
(* the sum of the magnitudes *)
set (A := sumabs (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) vs))
  in *.
assert (A0 : 0 <= A) by apply sumabs_ge_0.
assert (HA : A <= Q).
{ assert (Fl : Forall (fun xy => INR n * Rabs ((fst (fst xy) + snd (fst xy)) *
                                               (fst (snd xy) + snd (snd xy))) <= Q) vs).
  { unfold vs. apply Forall_map. revert T. apply Forall_impl. intros [x y] [Ix Iy]. cbn [fst snd].
    rewrite Rabs_mult. exact (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hp x Ix) y Iy). }
  pose proof (sumabs_scaled_2 (INR n) Q vs Fl) as SA. fold A in SA. fold k in SA.
  destruct (Nat.eq_dec k 0) as [K0|K0].
  - assert (Ev : vs = []) by (apply length_zero_iff_nil; exact K0).
    unfold A. rewrite Ev. unfold sumabs. cbn. lra.
  - assert (N1 : 1 <= INR n).
    { change 1 with (INR 1). apply le_INR. lia. }
    assert (K2 : INR k * Q <= INR n * Q) by (apply Rmult_le_compat_r; lra).
    apply Rmult_le_reg_l with (INR n). lra. lra. }
set (S := sumR (map (fun xy => (fst (fst xy) + snd (fst xy)) * (fst (snd xy) + snd (snd xy))) vs))
  in *.
set (s := FoldModel.dot_2_seq emin prec tie_even vs) in *.
assert (HS : Rabs S <= A) by apply sumR_le_sumabs.
(* the value of the state *)
assert (Hs : Rabs (fst s + snd s) <= 13 / 12 * Q + / 60).
{ assert (T1 : Rabs (fst s + snd s) <= Rabs S + Rabs ((fst s + snd s) - S)) by apply Rabs_le_add.
  assert (C1 : (1 + 4 * uu ^ 2) * (1 + dl) ^ (k - 1) <= 65 / 64 * (16 / 15))
    by (apply Rmult_le_compat; lra).
  assert (C0 : 1 <= (1 + 4 * uu ^ 2) * (1 + dl) ^ (k - 1)).
  { assert (K : 1 * 1 <= (1 + 4 * uu ^ 2) * (1 + dl) ^ (k - 1)) by (apply Rmult_le_compat; lra).
    lra. }
  pose proof (mul_le ((1 + 4 * uu ^ 2) * (1 + dl) ^ (k - 1) - 1) A (65 / 64 * (16 / 15) - 1) Q
                ltac:(lra) ltac:(lra) A0 HA) as [_ M1].
  assert (Ke : INR k * (3 / 2 * ee) <= 3 / 2 * / 128).
  { assert (K : INR k * ee <= INR n * ee) by (apply Rmult_le_compat_r; lra). lra. }
  assert (Ke0 : 0 <= INR k * (3 / 2 * ee)) by (apply Rmult_le_pos; lra).
  pose proof (mul_le ((1 + dl) ^ (k - 1)) (INR k * (3 / 2 * ee)) (16 / 15) (3 / 2 * / 128)
                PD0 PD Ke0 Ke) as [_ M2].
  lra. }
(* its leading limb *)
generalize (normalized_2_tail_rel_value emin prec (fst s) (snd s) Ns). intros Tl.
assert (K : Rabs (fst s) <= Rabs (fst s + snd s) + Rabs (snd s)).
{ replace (fst s) with ((fst s + snd s) + - snd s) at 1 by ring.
  apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra. }
assert (K2 : uu * Rabs (fst s + snd s) <= / 16 * (13 / 12 * Q + / 60)).
{ apply Rmult_le_compat; try lra. apply Rabs_pos. }
lra.
Qed.

(* Every coefficient's leading limb finite: the convolution's mask is true. *)
Lemma conv_2_mask_true :
  forall xs ys : list (float * float),
  Forall (fun x => good x) xs -> Forall (fun y => good y) ys ->
  INR (Nat.min (length xs) (length ys)) * (4 * uu ^ 2 + ee / (2 * uu)) <= / 16 ->
  Forall (fun x => Forall (fun y =>
    INR (Nat.min (length xs) (length ys)) * (Rabs (vsum x) * Rabs (vsum y)) <= Q) ys) xs ->
  snd (IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
         xs ys) = true.
Proof.
intros xs ys Gx Gy Hn Hp.
unfold IeeeFoldModel.conv_2_conv. cbv zeta. rewrite fold_seq_and.
match goal with |- context [forallb ?t ?l] => assert (Hb : forallb t l = true) end.
{ apply forallb_forall. intros w Hw. apply in_map_iff in Hw. destruct Hw as [j [Ej _]]. subst w.
  apply (proj2 (IeeeFoldMaps.check_2_flag prec emax nan_abs nan_const _)).
  assert (G : Forall (fun xy => good (fst xy) /\ good (snd xy)) (FoldModel.conv_terms xs ys j))
    by exact (FoldConv.conv_terms_Forall _ _ (fun x => good x) (fun y => good y) xs ys j Gx Gy).
  assert (P : Forall (fun xy => Rabs (vsum (fst xy) * vsum (snd xy)) <= Q)
                (FoldModel.conv_terms xs ys j)).
  { generalize (FoldConv.conv_terms_Forall _ _ (fun x => In x xs) (fun y => In y ys) xs ys j
                  (proj2 (Forall_forall _ _) (fun x H => H))
                  (proj2 (Forall_forall _ _) (fun y H => H))).
    apply Forall_impl. intros [x y] [Ix Iy]. cbn [fst snd].
    pose proof (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hp x Ix) y Iy) as K.
    cbv beta in K.
    assert (N1 : 1 <= INR (Nat.min (length xs) (length ys))).
    { change 1 with (INR 1). apply le_INR.
      destruct xs as [|x0 xs']; [contradiction|]. destruct ys as [|y0 ys']; [contradiction|].
      cbn [length]. lia. }
    rewrite Rabs_mult.
    assert (K1 : 0 <= Rabs (vsum x) * Rabs (vsum y)) by (apply Rmult_le_pos; apply Rabs_pos).
    assert (K2 : 1 * (Rabs (vsum x) * Rabs (vsum y)) <=
                 INR (Nat.min (length xs) (length ys)) * (Rabs (vsum x) * Rabs (vsum y)))
      by (apply Rmult_le_compat_r; lra).
    lra. }
  destruct (dot_2_forward (FoldModel.conv_terms xs ys j) G P
              (fun l1 l2 E => coef_prefix_2 xs ys j l1 l2 Gx Gy Hn Hp E)) as [Fw _].
  exact Fw. }
rewrite Hb. reflexivity.
Qed.

(** * The radius *)

(* conv_radius_given of IeeeBvConvFinite.v with the bounds of two limbs: t <= 1/4,
   m eta and m eta/(2u) small, P <= 5/4 Q and m P <= 13/10 Q. *)
Lemma conv_radius_given_2 :
  forall ma mb rx ry m g t : float,
  fin ma -> fin mb -> fin rx -> fin ry -> fin m -> fin g -> fin t ->
  0 <= b2r ma -> 0 <= b2r mb -> 0 <= b2r rx -> 0 <= b2r ry -> 0 <= b2r m ->
  0 <= b2r g <= / 2 -> 0 <= b2r t <= / 4 ->
  b2r m * ee <= / 100 -> b2r m * (ee / (2 * uu)) <= 9 / 128 ->
  (b2r ma + b2r rx) * (b2r mb + b2r ry) <= 5 / 4 * Q ->
  b2r m * ((b2r ma + b2r rx) * (b2r mb + b2r ry)) <= 13 / 10 * Q ->
  fin (IeeeModel.conv_radius prec emax nan_fma ma mb rx ry m g t).
Proof.
intros ma mb rx ry m g t Fa Fb Fx Fy Fm Fg Ft Pa Pb Px Py Pm [Pg Lg] [Pt Lt] Me Mt HP HMP.
destruct U16 as [U0 U1]. destruct E64 as [H0 H1]. destruct T8 as [I0 I1].
set (A := b2r ma) in *. set (B := b2r mb) in *. set (X := b2r rx) in *. set (Y := b2r ry) in *.
set (M := b2r m) in *.
assert (EP : (A + X) * (B + Y) = A * B + A * Y + B * X + X * Y) by ring.
assert (PAB : 0 <= A * B) by (apply Rmult_le_pos; lra).
assert (PAY : 0 <= A * Y) by (apply Rmult_le_pos; lra).
assert (PBX : 0 <= B * X) by (apply Rmult_le_pos; lra).
assert (PXY : 0 <= X * Y) by (apply Rmult_le_pos; lra).
assert (Me0 : 0 <= M * ee) by (apply Rmult_le_pos; lra).
assert (Mt0 : 0 <= M * (ee / (2 * uu))) by (apply Rmult_le_pos; lra).
unfold IeeeModel.conv_radius. cbv zeta.
set (c0 := IeeeModel.up_conv_radius_0 prec emax). set (c7 := IeeeModel.up_conv_radius_1 prec emax).
destruct (pow_1u prec Hp4 8) as [L8 K8]. destruct (pow_1u prec Hp4 7) as [L7 K7].
assert (N8 : (17 / 16) ^ 8 <= 163 / 100) by (simpl; lra).
assert (N7 : (17 / 16) ^ 7 <= 153 / 100) by (simpl; lra).
assert (X0 : 0 <= 4 * (1 + uu) ^ 8 * ee + ee / (2 * uu) <= 2).
{ assert (K : 4 * (1 + uu) ^ 8 * ee <= 4 * (163 / 100) * ee) by (apply Rmult_le_compat_r; lra).
  assert (0 <= 4 * (1 + uu) ^ 8 * ee) by (apply Rmult_le_pos; lra). split; lra. }
destruct (const_ok prec emax Hp4 _ (proj1 X0) (proj2 X0)) as [Fc0 Vc0].
destruct (const_ok prec emax Hp4 ((1 + uu) ^ 7) ltac:(lra) ltac:(lra)) as [Fc7 Vc7].
change (IeeeOperations.const_of prec emax (RU (4 * (1 + uu) ^ 8 * ee + ee / (2 * uu))))
  with c0 in Fc0, Vc0.
change (IeeeOperations.const_of prec emax (RU ((1 + uu) ^ 7))) with c7 in Fc7, Vc7.
assert (B0 : 0 <= b2r c0 <= 9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee).
{ rewrite Vc0. apply (RU_bound prec emax Hp4). lra.
  assert (K : 4 * (1 + uu) ^ 8 * ee <= 4 * (163 / 100) * ee) by (apply Rmult_le_compat_r; lra).
  lra. }
assert (B7 : 0 <= b2r c7 <= 1737 / 1000).
{ rewrite Vc7.
  destruct (RU_bound prec emax Hp4 ((1 + uu) ^ 7) (153 / 100) ltac:(lra) ltac:(lra)) as [W0 W1].
  split; lra. }
assert (MB0 : 0 <= M * b2r c0 <= 17 / 100).
{ split. apply Rmult_le_pos; lra.
  assert (K : M * b2r c0 <= M * (9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (9 / 8 * (4 * (163 / 100) * ee + ee / (2 * uu)) + ee)) with
    (9 / 8 * (4 * (163 / 100) * (M * ee) + M * (ee / (2 * uu))) + M * ee) in K by (field; lra).
  lra. }
(* the chain *)
set (p := prod rx ry). set (q := fma mb rx p). set (w := fma ma ry q). set (ab := prod ma mb).
set (e := fma ab g w). set (s := fma m e t). set (hm := prod m c0). set (rz := fma s c7 hm).
pose proof (rnd_bound prec emax Hp4 (X * Y + 0) (X * Y) ltac:(lra) ltac:(lra)) as [Rp0 Rp1].
destruct (prod_ok prec emax Hp4 nan_fma rx ry Fx Fy (range_le emax _ _ Rp0 Rp1 ltac:(lra)))
  as [Fp Ep].
fold p in Fp, Ep. fold X Y in Ep.
assert (Bp : 0 <= b2r p <= 17 / 16 * (X * Y) + ee / 2) by (rewrite Ep; lra).
pose proof (rnd_bound prec emax Hp4 (B * X + b2r p) (B * X + (17 / 16 * (X * Y) + ee / 2))
              ltac:(lra) ltac:(lra)) as [Rq0 Rq1].
destruct (fma_ok prec emax Hp4 nan_fma mb rx p Fb Fx Fp (range_le emax _ _ Rq0 Rq1 ltac:(lra)))
  as [Fq Eq].
fold q in Fq, Eq. fold B X in Eq.
assert (Bq : 0 <= b2r q <= 17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2)
  by (rewrite Eq; lra).
pose proof (rnd_bound prec emax Hp4 (A * Y + b2r q)
              (A * Y + (17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2)) ltac:(lra)
              ltac:(lra)) as [Rw0 Rw1].
destruct (fma_ok prec emax Hp4 nan_fma ma ry q Fa Fy Fq (range_le emax _ _ Rw0 Rw1 ltac:(lra)))
  as [Fw Ew].
fold w in Fw, Ew. fold A Y in Ew.
set (Wb := 17 / 16 * (A * Y + (17 / 16 * (B * X + (17 / 16 * (X * Y) + ee / 2)) + ee / 2))
           + ee / 2) in *.
assert (Bw : 0 <= b2r w <= Wb) by (rewrite Ew; lra).
pose proof (rnd_bound prec emax Hp4 (A * B + 0) (A * B) ltac:(lra) ltac:(lra)) as [Rab0 Rab1].
destruct (prod_ok prec emax Hp4 nan_fma ma mb Fa Fb (range_le emax _ _ Rab0 Rab1 ltac:(lra)))
  as [Fab Eab].
fold ab in Fab, Eab. fold A B in Eab.
assert (Bab : 0 <= b2r ab <= 17 / 16 * (A * B) + ee / 2) by (rewrite Eab; lra).
pose proof (mul_le (b2r ab) (b2r g) (17 / 16 * (A * B) + ee / 2) (/ 2) ltac:(lra) ltac:(lra)
              ltac:(lra) ltac:(lra)) as [Pabg0 Pabg1].
pose proof (rnd_bound prec emax Hp4 (b2r ab * b2r g + b2r w) ((17 / 16 * (A * B) + ee / 2) * / 2 + Wb)
              ltac:(lra) ltac:(lra)) as [Re0 Re1].
destruct (fma_ok prec emax Hp4 nan_fma ab g w Fab Fg Fw
            (range_le emax _ _ Re0 Re1 ltac:(unfold Wb in *; lra))) as [Fe Ee].
fold e in Fe, Ee.
assert (Be : 0 <= b2r e <= 12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee).
{ rewrite Ee. split. lra. rewrite EP. unfold Wb in Re1. lra. }
assert (MBe : M * b2r e <= 12745 / 10000 * (13 / 10 * Q) + 3 / 100).
{ assert (K : M * b2r e <= M * (12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee))
    by (apply Rmult_le_compat_l; lra).
  replace (M * (12745 / 10000 * ((A + X) * (B + Y)) + 3 * ee)) with
    (12745 / 10000 * (M * ((A + X) * (B + Y))) + 3 * (M * ee)) in K by (field; lra).
  lra. }
assert (PMe : 0 <= M * b2r e) by (apply Rmult_le_pos; lra).
pose proof (rnd_bound prec emax Hp4 (M * b2r e + b2r t) (12745 / 10000 * (13 / 10 * Q) + 3 / 100 + / 4)
              ltac:(lra) ltac:(lra)) as [Rs0 Rs1].
destruct (fma_ok prec emax Hp4 nan_fma m e t Fm Fe Ft (range_le emax _ _ Rs0 Rs1 ltac:(lra)))
  as [Fs Es].
fold s in Fs, Es. fold M in Es.
assert (Bs : 0 <= b2r s <= 18 / 10 * Q) by (rewrite Es; lra).
pose proof (rnd_bound prec emax Hp4 (M * b2r c0 + 0) (17 / 100) ltac:(lra) ltac:(lra)) as [Rh0 Rh1].
destruct (prod_ok prec emax Hp4 nan_fma m c0 Fm Fc0 (range_le emax _ _ Rh0 Rh1 ltac:(lra)))
  as [Fh Eh].
fold hm in Fh, Eh. fold M in Eh.
assert (Bh : 0 <= b2r hm <= 19 / 100) by (rewrite Eh; lra).
pose proof (mul_le (b2r s) (b2r c7) (18 / 10 * Q) (1737 / 1000) ltac:(lra) ltac:(lra)
              ltac:(lra) ltac:(lra)) as [Psc0 Psc1].
pose proof (rnd_bound prec emax Hp4 (b2r s * b2r c7 + b2r hm) (18 / 10 * Q * (1737 / 1000) + 19 / 100)
              ltac:(lra) ltac:(lra)) as [Rz0 Rz1].
destruct (fma_ok prec emax Hp4 nan_fma s c7 hm Fs Fc7 Fh (range_le emax _ _ Rz0 Rz1 ltac:(lra)))
  as [Fz _].
exact Fz.
Qed.

(* The conditions of V4 bound P = (Ma + rx) (Mb + ry), Ma and Mb the largest magnitudes of the
   leading limbs: each leading limb is at most (1 + u) times the magnitude of its entry. *)
Lemma P_bound_2 :
  forall (xs ys : list (float * float)) (X Y : R), 0 <= X -> 0 <= Y ->
  Forall (fun x => good x) xs -> Forall (fun y => good y) ys ->
  Rabs (X * Y) <= Q ->
  Forall (fun x => Rabs ((Rabs (vsum x) + X) * Y) <= Q) xs ->
  Forall (fun y => Rabs ((Rabs (vsum y) + Y) * X) <= Q) ys ->
  Forall (fun x => Forall (fun y =>
    Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (vsum x) + X) * (Rabs (vsum y) + Y)) <= Q)
    ys) xs ->
  let A := maxl (map (fun w => Rabs w) (map val (map fst xs))) in
  let B := maxl (map (fun w => Rabs w) (map val (map fst ys))) in
  (A + X) * (B + Y) <= (1 + uu) ^ 2 * Q /\
  INR (Nat.min (length xs) (length ys)) * ((A + X) * (B + Y)) <= (1 + uu) ^ 2 * Q.
Proof.
intros xs ys X Y PX PY Gx Gy Hr Hx Hy Hxy A B.
destruct U16 as [U0 U1].
assert (Lead : forall x : float * float, good x -> Rabs (b2r (fst x)) <= (1 + uu) * Rabs (vsum x)).
{ intros x [_ [_ N]]. generalize (normalized_2_tail_rel_value emin prec _ _ N). intros T.
  assert (K : Rabs (b2r (fst x)) <= Rabs (vsum x) + Rabs (b2r (snd x))).
  { replace (b2r (fst x)) with (vsum x + - b2r (snd x)) at 1 by ring.
    apply Rle_trans with (1 := Rabs_triang _ _). rewrite Rabs_Ropp. lra. }
  lra. }
assert (Q0 : 0 < Q) by apply bpow_gt_0.
assert (P2 : 1 <= (1 + uu) ^ 2) by (apply pow_R1_Rle; lra).
assert (K1 : Q <= (1 + uu) ^ 2 * Q).
{ assert (K : 1 * Q <= (1 + uu) ^ 2 * Q) by (apply Rmult_le_compat_r; lra). lra. }
assert (Ku : (1 + uu) * Q <= (1 + uu) ^ 2 * Q).
{ replace ((1 + uu) ^ 2 * Q) with ((1 + uu) * ((1 + uu) * Q)) by ring.
  assert (K : 1 * ((1 + uu) * Q) <= (1 + uu) * ((1 + uu) * Q))
    by (apply Rmult_le_compat_r; [apply Rmult_le_pos|]; lra). lra. }
(* one entry with a radius *)
assert (One : forall (x : float * float) (Z : R), good x -> 0 <= Z ->
          Rabs ((Rabs (vsum x) + X) * Z) <= Q ->
          Rabs ((Rabs (val (fst x)) + X) * Z) <= (1 + uu) ^ 2 * Q).
{ intros x Z Gx' PZ Kx. pose proof (Lead x Gx') as L.
  assert (V0 : 0 <= Rabs (vsum x)) by apply Rabs_pos.
  rewrite Rabs_pos_eq in Kx by (apply Rmult_le_pos; lra).
  change (val (fst x)) with (b2r (fst x)).
  rewrite Rabs_pos_eq by (apply Rmult_le_pos; [generalize (Rabs_pos (b2r (fst x))); lra | lra]).
  assert (K3 : (Rabs (b2r (fst x)) + X) * Z <= ((1 + uu) * Rabs (vsum x) + X) * Z)
    by (apply Rmult_le_compat_r; lra).
  assert (K4 : ((1 + uu) * Rabs (vsum x) + X) * Z <= (1 + uu) * ((Rabs (vsum x) + X) * Z)).
  { assert (0 <= uu * (X * Z)) by (apply Rmult_le_pos; [lra|apply Rmult_le_pos; lra]). nra. }
  assert (K5 : (1 + uu) * ((Rabs (vsum x) + X) * Z) <= (1 + uu) * Q)
    by (apply Rmult_le_compat_l; lra).
  lra. }
generalize (P_bound_K prec emax (map fst xs) (map fst ys) X Y ((1 + uu) ^ 2 * Q) PX PY).
rewrite !length_map. intros PB. apply PB.
- lra.
- apply Forall_map, Forall_forall. intros x Ix.
  exact (One x Y (proj1 (Forall_forall _ _) Gx x Ix) PY (proj1 (Forall_forall _ _) Hx x Ix)).
- apply Forall_map, Forall_forall. intros y Iy.
  pose proof (proj1 (Forall_forall _ _) Gy y Iy) as Gy'.
  pose proof (proj1 (Forall_forall _ _) Hy y Iy) as Ky.
  assert (Ky' : Rabs ((Rabs (vsum y) + Y) * X) <= Q) by exact Ky.
  (* the roles of X and Y exchanged *)
  pose proof (Lead y Gy') as L.
  assert (V0 : 0 <= Rabs (vsum y)) by apply Rabs_pos.
  rewrite Rabs_pos_eq in Ky' by (apply Rmult_le_pos; lra).
  change (val (fst y)) with (b2r (fst y)).
  rewrite Rabs_pos_eq by (apply Rmult_le_pos; [generalize (Rabs_pos (b2r (fst y))); lra | lra]).
  assert (K3 : (Rabs (b2r (fst y)) + Y) * X <= ((1 + uu) * Rabs (vsum y) + Y) * X)
    by (apply Rmult_le_compat_r; lra).
  assert (K4 : ((1 + uu) * Rabs (vsum y) + Y) * X <= (1 + uu) * ((Rabs (vsum y) + Y) * X)).
  { assert (0 <= uu * (Y * X)) by (apply Rmult_le_pos; [lra|apply Rmult_le_pos; lra]). nra. }
  assert (K5 : (1 + uu) * ((Rabs (vsum y) + Y) * X) <= (1 + uu) * Q)
    by (apply Rmult_le_compat_l; lra).
  lra.
- apply Forall_map, Forall_forall. intros x Ix. apply Forall_map, Forall_forall. intros y Iy.
  pose proof (Lead x (proj1 (Forall_forall _ _) Gx x Ix)) as Lx.
  pose proof (Lead y (proj1 (Forall_forall _ _) Gy y Iy)) as Ly.
  pose proof (proj1 (Forall_forall _ _) (proj1 (Forall_forall _ _) Hxy x Ix) y Iy) as Kxy.
  cbv beta in Kxy.
  set (n := INR (Nat.min (length xs) (length ys))) in *.
  assert (Pn : 0 <= n) by apply pos_INR.
  assert (Vx : 0 <= Rabs (vsum x)) by apply Rabs_pos.
  assert (Vy : 0 <= Rabs (vsum y)) by apply Rabs_pos.
  assert (Ax : 0 <= Rabs (b2r (fst x))) by apply Rabs_pos.
  assert (Ay : 0 <= Rabs (b2r (fst y))) by apply Rabs_pos.
  rewrite Rabs_pos_eq in Kxy by (apply Rmult_le_pos; [apply Rmult_le_pos|]; lra).
  change (val (fst x)) with (b2r (fst x)). change (val (fst y)) with (b2r (fst y)).
  rewrite Rabs_pos_eq by (apply Rmult_le_pos; [apply Rmult_le_pos|]; lra).
  assert (Lx' : Rabs (b2r (fst x)) + X <= (1 + uu) * (Rabs (vsum x) + X)) by nra.
  assert (Ly' : Rabs (b2r (fst y)) + Y <= (1 + uu) * (Rabs (vsum y) + Y)) by nra.
  assert (K3 : n * (Rabs (b2r (fst x)) + X) * (Rabs (b2r (fst y)) + Y) <=
               n * ((1 + uu) * (Rabs (vsum x) + X)) * ((1 + uu) * (Rabs (vsum y) + Y))).
  { apply Rmult_le_compat; try lra.
    - apply Rmult_le_pos; lra.
    - apply Rmult_le_compat_l; lra. }
  replace (n * ((1 + uu) * (Rabs (vsum x) + X)) * ((1 + uu) * (Rabs (vsum y) + Y))) with
    ((1 + uu) ^ 2 * (n * (Rabs (vsum x) + X) * (Rabs (vsum y) + Y))) in K3 by ring.
  assert (K4 : (1 + uu) ^ 2 * (n * (Rabs (vsum x) + X) * (Rabs (vsum y) + Y)) <= (1 + uu) ^ 2 * Q)
    by (apply Rmult_le_compat_l; lra).
  lra.
Qed.

(** * The parts of bv_conv_2 under the conditions of V4 *)

Lemma bv_conv_2_finite_parts :
  forall (rx ry : float) (xs ys : list (float * float)),
  fin rx -> fin ry -> 0 <= val rx -> 0 <= val ry ->
  Forall (fun x => good x) xs -> Forall (fun y => good y) ys ->
  INR (Nat.min (length xs) (length ys)) * (4 * uu ^ 2 + ee / (2 * uu)) <= / 16 ->
  Rabs (val rx * val ry) <= Q ->
  Forall (fun x => Rabs ((Rabs (vsum x) + val rx) * val ry) <= Q) xs ->
  Forall (fun y => Rabs ((Rabs (vsum y) + val ry) * val rx) <= Q) ys ->
  Forall (fun x => Forall (fun y =>
    Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (vsum x) + val rx) * (Rabs (vsum y) + val ry))
      <= Q) ys) xs ->
  let c := IeeeFoldModel.conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
             xs ys in
  let sa := fold_seq (IeeeFoldModel.bv_conv_2_record prec emax nan_abs) (pzero, true) xs in
  let sb := fold_seq (IeeeFoldModel.bv_conv_2_record prec emax nan_abs) (pzero, true) ys in
  let m := IeeeFoldModel.bv_conv_2_count prec emax xs ys in
  let b := IeeeModel.bound_dot_2 prec emax nan_plus nan_fma m in
  snd c = true /\ snd b = true /\
  fin (IeeeModel.conv_radius prec emax nan_fma (fst sa) (fst sb) rx ry m (fst (fst b))
         (snd (fst b))).
Proof.
intros rx ry xs ys Frx Fry Px Py Gx Gy Hn Hr Hx Hy Hxy. cbv zeta.
destruct U16 as [U0 U1].
set (n := Nat.min (length xs) (length ys)) in *.
assert (Pn : 0 <= INR n) by apply pos_INR.
destruct (count_parts (INR n) (/ 16) Pn Hn) as [Mu [Mt _]].
(* the count *)
unfold IeeeFoldModel.bv_conv_2_count. fold n.
destruct (count_bounded n Mt) as [Fm [Vm [R0 Rm]]].
set (m := binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_UP
            (Z.of_nat n) 0 false) in *.
assert (M0 : 0 <= b2r m) by (rewrite Vm; exact R0).
assert (M98 : b2r m <= 9 / 8 * INR n).
{ rewrite Vm. apply Rle_trans with (1 := Rm). apply Rmult_le_compat_r; lra. }
assert (Hm : b2r m * (4 * uu ^ 2 + ee / (2 * uu)) <= 9 / 128).
{ destruct four_u2 as [S0 _]. destruct T8 as [I0 _].
  assert (K : b2r m * (4 * uu ^ 2 + ee / (2 * uu)) <= 9 / 8 * INR n * (4 * uu ^ 2 + ee / (2 * uu)))
    by (apply Rmult_le_compat_r; lra).
  lra. }
destruct (count_parts (b2r m) (9 / 128) M0 Hm) as [MU [MT ME]].
destruct (bound_dot_2_given m Fm M0 MU MT ltac:(lra)) as [Fg [Ft [Eok [Bg Bt]]]].
(* the pairs, as products of values *)
assert (Hp : Forall (fun x => Forall (fun y =>
               INR n * (Rabs (vsum x) * Rabs (vsum y)) <= Q) ys) xs).
{ revert Hxy. apply Forall_impl. intros x Hx'. revert Hx'. apply Forall_impl. intros y K.
  assert (K1 : Rabs (vsum x) * Rabs (vsum y) <= (Rabs (vsum x) + val rx) * (Rabs (vsum y) + val ry))
    by (apply Rmult_le_compat; generalize (Rabs_pos (vsum x)) (Rabs_pos (vsum y)); lra).
  assert (K2 : INR n * (Rabs (vsum x) * Rabs (vsum y)) <=
               INR n * ((Rabs (vsum x) + val rx) * (Rabs (vsum y) + val ry)))
    by (apply Rmult_le_compat_l; [exact Pn|exact K1]).
  apply Rle_trans with (1 := K2).
  replace (INR n * ((Rabs (vsum x) + val rx) * (Rabs (vsum y) + val ry))) with
    (INR n * (Rabs (vsum x) + val rx) * (Rabs (vsum y) + val ry)) by ring.
  apply Rle_trans with (2 := K). apply Rle_abs. }
split; [|split].
- exact (conv_2_mask_true xs ys Gx Gy Hn Hp).
- exact Eok.
- change (IeeeFoldModel.bv_conv_2_record prec emax nan_abs)
    with (IeeeFoldModel.norm_upper_2_step prec emax nan_abs).
  rewrite !(record_2_lead prec emax nan_abs).
  assert (Fxs : Forall (fun x => fin x) (map fst xs)).
  { apply Forall_map. revert Gx. apply Forall_impl. intros x [F _]. exact F. }
  assert (Fys : Forall (fun y => fin y) (map fst ys)).
  { apply Forall_map. revert Gy. apply Forall_impl. intros y [F _]. exact F. }
  destruct (maxl_values prec emax nan_abs (map fst xs) Fxs) as [Va Fa].
  destruct (maxl_values prec emax nan_abs (map fst ys) Fys) as [Vb Fb].
  destruct (P_bound_2 xs ys (val rx) (val ry) Px Py Gx Gy Hr Hx Hy Hxy) as [HP HMP].
  fold n in HMP.
  set (sa := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true)
               (map fst xs)) in *.
  set (sb := fold_seq (IeeeFoldModel.norm_upper_1_step prec emax nan_abs) (pzero, true)
               (map fst ys)) in *.
  assert (A0 : 0 <= B2R prec emax (fst sa)) by (rewrite Va; apply FoldNorm.maxl_nonneg).
  assert (B0 : 0 <= B2R prec emax (fst sb)) by (rewrite Vb; apply FoldNorm.maxl_nonneg).
  assert (P2 : (1 + uu) ^ 2 <= 289 / 256).
  { replace ((1 + uu) ^ 2) with ((1 + uu) * (1 + uu)) by ring.
    assert (K : (1 + uu) * (1 + uu) <= 17 / 16 * (17 / 16)) by (apply Rmult_le_compat; lra). lra. }
  assert (Q0 : 0 < Q) by apply bpow_gt_0.
  assert (K2 : (1 + uu) ^ 2 * Q <= 289 / 256 * Q) by (apply Rmult_le_compat_r; lra).
  set (E := (maxl (map (fun w => Rabs w) (map val (map fst xs))) + val rx) *
            (maxl (map (fun w => Rabs w) (map val (map fst ys))) + val ry)) in *.
  assert (Px' : 0 <= B2R prec emax rx) by exact Px.
  assert (Py' : 0 <= B2R prec emax ry) by exact Py.
  set (P := (B2R prec emax (fst sa) + B2R prec emax rx) * (B2R prec emax (fst sb) + B2R prec emax ry)).
  assert (EP : P = E) by (unfold P, E; rewrite Va, Vb; reflexivity).
  assert (PP : 0 <= P) by (unfold P; apply Rmult_le_pos; lra).
  assert (HP' : P <= 5 / 4 * Q) by (rewrite EP; lra).
  assert (HMP' : B2R prec emax m * P <= 13 / 10 * Q).
  { assert (K : B2R prec emax m * P <= 9 / 8 * INR n * P) by (apply Rmult_le_compat_r; lra).
    rewrite EP in K |- *. lra. }
  exact (conv_radius_given_2 (fst sa) (fst sb) rx ry m _ _ Fa Fb Frx Fry Fm Fg Ft A0 B0 Px Py M0
           Bg Bt ltac:(lra) MT HP' HMP').
Qed.

End V4.

(** * V4 and the generated statement *)

Lemma bv_conv_2_ieee_v4 :
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
  (finite rx -> finite ry ->
   ((INR (Nat.min (length xs) (length ys))) *
      ((4 * u prec ^ 2) + (eta (ieee_emin prec emax) / (2 * u prec)))) <= (1 / 16) ->
   Rabs (val rx * val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun x => let '(x0, x1) := x in
     Rabs (((Rabs (val x0 + val x1)) + val rx) * val ry) <= bpow radix2 (emax - 2)) xs ->
   Forall (fun y => let '(y0, y1) := y in
     Rabs (((Rabs (val y0 + val y1)) + val ry) * val rx) <= bpow radix2 (emax - 2)) ys ->
   Forall (fun x => Forall (fun y => let '(x0, x1) := x in let '(y0, y1) := y in
     Rabs (((INR (Nat.min (length xs) (length ys))) * ((Rabs (val x0 + val x1)) + val rx)) *
           ((Rabs (val y0 + val y1)) + val ry)) <= bpow radix2 (emax - 2)) ys) xs ->
   finite r_).
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
unfold IeeeFoldModel.bv_conv_2_conv. cbv zeta.
match goal with
| |- context [IeeeModel.bv_conv_finish prec emax nan_abs nan_const ?z ?a ?o] =>
    generalize (bv_conv_finish_facts prec emax Hp He nan_abs nan_const z a o);
    destruct (IeeeModel.bv_conv_finish prec emax nan_abs nan_const z a o) as [r flag]
end.
intros [H1 [H2 _]].
assert (Parts : finite rx -> finite ry ->
   ((INR (Nat.min (length xs) (length ys))) *
      ((4 * u prec ^ 2) + (eta (ieee_emin prec emax) / (2 * u prec)))) <= (1 / 16) ->
   Rabs (val rx * val ry) <= bpow radix2 (emax - 2) ->
   Forall (fun x => let '(x0, x1) := x in
     Rabs (((Rabs (val x0 + val x1)) + val rx) * val ry) <= bpow radix2 (emax - 2)) xs ->
   Forall (fun y => let '(y0, y1) := y in
     Rabs (((Rabs (val y0 + val y1)) + val ry) * val rx) <= bpow radix2 (emax - 2)) ys ->
   Forall (fun x => Forall (fun y => let '(x0, x1) := x in let '(y0, y1) := y in
     Rabs (((INR (Nat.min (length xs) (length ys))) * ((Rabs (val x0 + val x1)) + val rx)) *
           ((Rabs (val y0 + val y1)) + val ry)) <= bpow radix2 (emax - 2)) ys) xs ->
   flag = true).
{ intros Frx Fry Hn Hr Hx Hy Hxy.
  assert (Bx : 0 <= val rx /\ Forall (fun x => finite (fst x) /\ finite (snd x) /\
                 normalized_2 (ieee_emin prec emax) prec (val (fst x)) (val (snd x))) xs).
  { destruct HX as [[_ [P B]]|[E _]].
    - split. exact P. revert B. apply Forall_impl. intros x [F0 [F1 [N _]]].
      split. exact F0. split. exact F1. exact N.
    - rewrite E in Frx. discriminate Frx. }
  assert (By : 0 <= val ry /\ Forall (fun y => finite (fst y) /\ finite (snd y) /\
                 normalized_2 (ieee_emin prec emax) prec (val (fst y)) (val (snd y))) ys).
  { destruct HY as [[_ [P B]]|[E _]].
    - split. exact P. revert B. apply Forall_impl. intros y [F0 [F1 [N _]]].
      split. exact F0. split. exact F1. exact N.
    - rewrite E in Fry. discriminate Fry. }
  destruct Bx as [Px Gx]. destruct By as [Py Gy].
  assert (Hn' : INR (Nat.min (length xs) (length ys)) *
                  (4 * u prec ^ 2 + eta (3 - emax - prec) / (2 * u prec)) <= / 16)
    by (unfold ieee_emin in Hn; lra).
  assert (Hx' : Forall (fun x => Rabs ((Rabs (val (fst x) + val (snd x)) + val rx) * val ry) <=
                                 bpow radix2 (emax - 2)) xs).
  { revert Hx. apply Forall_impl. intros [x0 x1] K. exact K. }
  assert (Hy' : Forall (fun y => Rabs ((Rabs (val (fst y) + val (snd y)) + val ry) * val rx) <=
                                 bpow radix2 (emax - 2)) ys).
  { revert Hy. apply Forall_impl. intros [y0 y1] K. exact K. }
  assert (Hxy' : Forall (fun x => Forall (fun y =>
            Rabs (INR (Nat.min (length xs) (length ys)) * (Rabs (val (fst x) + val (snd x)) + val rx) *
                  (Rabs (val (fst y) + val (snd y)) + val ry)) <= bpow radix2 (emax - 2)) ys) xs).
  { revert Hxy. apply Forall_impl. intros [x0 x1] K. revert K. apply Forall_impl.
    intros [y0 y1] K. exact K. }
  generalize (bv_conv_2_finite_parts prec emax Hp4 nan_plus nan_minus nan_opp nan_abs nan_fma
                nan_const rx ry xs ys Frx Fry Px Py Gx Gy Hn' Hr Hx' Hy' Hxy').
  cbv zeta. intros [Ec [Eb Fz]]. apply H1. split. exact Ec. split. exact Eb. exact Fz. }
destruct flag; cbv beta iota.
- intros Frx Fry _ _ _ _ _. rewrite (H2 eq_refl).
  destruct (proj1 H1 eq_refl) as [_ [_ Fz]]. exact Fz.
- intros Frx Fry Hn Hr Hx Hy Hxy. discriminate (Parts Frx Fry Hn Hr Hx Hy Hxy).
Qed.

Theorem bv_conv_2_ieee_correct : bv_conv_2_ieee_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const Hp4 rx ry xs ys HX HY.
generalize (bv_conv_2_ieee_v1 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys HX HY)
           (bv_conv_2_ieee_v2 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys HX HY)
           (bv_conv_2_ieee_v3 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys HX HY)
           (bv_conv_2_ieee_v4 prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma nan_const
              Hp4 rx ry xs ys HX HY).
destruct (IeeeFoldModel.bv_conv_2_conv prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
            nan_const rx ry xs ys) as [[ws r] flag].
intros [A1 [A2 A3]] B C D.
split. exact A1. split. exact A2. split. exact A3. split. exact B. split. exact C. exact D.
Qed.
