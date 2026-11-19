(* The full kernels in the IEEE model: F1 to F5 of milestone1.md ("IEEE-like results").

   A full kernel is a finite core followed by a fix-up (IeeeDraft.v). The fix-up is the
   same for every kernel: given the result (z0, z1) of the core and the value t of the
   operation of T on the leading limbs,

       w = (z0, z1)                 when z0 is finite,
       w = the canonical form of t  otherwise: (NaN, NaN) when prod (t, inf) is a NaN,
                                    that is when t is a NaN or a zero; (+-infinity, +0)
                                    with the sign of t for any other t.

   One lemma (full_template) derives the five statements from five facts about a core:

     cone         a finite z0 means finite operands. Every operand limb reaches z0
                  through operations that keep a non-finite value non-finite, which is
                  checked by computing the cone of z0 in the program of the core;
     correctness  on finite operands, a finite z0 gives the statement of the core (the
                  theorem K_values_correct of IeeeAdd22.v, IeeeMul22.v, IeeeMore.v);
     threshold    the "finite when" condition (IeeeAdd22.v, IeeeMul22.v, IeeeRange.v);
     overflow     on finite operands, when z0 is not finite, prod (t, inf) is the
                  infinity of the sign of the exact result. For a kernel that adds:
                  it does not overflow when the exact result is at most 2^(emax - 2)
                  in magnitude (IeeeRange.v), so at overflow the sum of the leading
                  limbs is much larger than the sum of the second limbs and has the
                  sign of the exact result. For a kernel that multiplies: it does not
                  overflow when the leading product rounds to zero, and a product of
                  the leading limbs that is not zero has the sign of the exact result;
     non-finite   t is not finite when an operand is not.

   The statements, in the form of IeeeExtStatementsDraft.v, are at the end of the file. *)
From Stdlib Require Import Reals ZArith List Arith Bool Lia Lra Psatz.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Import Model Statements.
From Kairn Require Import Format Normalized EFT Program IeeeBridge IeeeEFT IeeeAdd22 IeeeMul22
  IeeeMore IeeeStatementsDraft IeeeExtStatementsDraft IeeeOps IeeeRange.
From Kairn Require IeeeDraft.
Import ListNotations.
Open Scope R_scope.

Section IeeeFull.
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
Notation add := (IeeeDraft.add prec emax nan_plus).
Notation sub := (IeeeDraft.sub prec emax nan_minus).
Notation neg := (IeeeDraft.neg prec emax nan_opp).
Notation fabs := (IeeeDraft.abs prec emax nan_abs).
Notation fma := (IeeeDraft.fma prec emax nan_fma).
Notation prod := (IeeeDraft.prod prec emax nan_fma).
Notation flt := (IeeeDraft.lt prec emax).
Notation feq := (IeeeDraft.eq prec emax).
Notation guard := (IeeeDraft.guard prec emax nan_plus).
Notation pzero := (IeeeDraft.pzero prec emax).
Notation pinf := (IeeeDraft.pinf prec emax).
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

(** * The fix-up *)

Definition fixup (z0 z1 t : float) : float * float :=
  let a := fabs z0 in
  let f := flt a pinf in
  let r0 := prod t pinf in
  let n := feq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Lemma fixup_fin : forall z0 z1 t : float, fin z0 -> fixup z0 z1 t = (z0, z1).
Proof.
intros z0 z1 t F. unfold fixup. cbv zeta. rewrite lt_abs_pinf, F. reflexivity.
Qed.

Lemma fixup_nan :
  forall z0 z1 t : float, is_finite prec emax z0 = false ->
  is_nan prec emax (prod t pinf) = true ->
  fixup z0 z1 t = (prod t pinf, prod t pinf).
Proof.
intros z0 z1 t F N. unfold fixup. cbv zeta. rewrite lt_abs_pinf, F, eq_self, N. reflexivity.
Qed.

Lemma fixup_inf :
  forall (z0 z1 t : float) (s : bool), is_finite prec emax z0 = false ->
  prod t pinf = B754_infinity prec emax s ->
  fixup z0 z1 t = (B754_infinity prec emax s, pzero).
Proof.
intros z0 z1 t s F E. unfold fixup. cbv zeta. rewrite lt_abs_pinf, F, eq_self, E. reflexivity.
Qed.

(* The five statements, from five facts about the core. *)
Lemma full_template :
  forall (z0 z1 t : float) (opfin cond : Prop) (P : float -> float -> Prop) (s : bool),
  (fin z0 -> opfin) ->
  (opfin -> fin z0 -> fin z1 /\ normalized_2 emin prec (b2r z0) (b2r z1) /\ P z0 z1) ->
  (opfin -> cond -> fin z0) ->
  (opfin -> is_finite prec emax z0 = false -> prod t pinf = B754_infinity prec emax s) ->
  (~ opfin -> is_finite prec emax t = false) ->
  let '(w0, w1) := fixup z0 z1 t in
  canonical_2 w0 w1 /\
  (fin w0 -> opfin /\ fin w1 /\ normalized_2 emin prec (b2r w0) (b2r w1) /\ P w0 w1) /\
  (opfin -> cond -> fin w0) /\
  (opfin -> ~ fin w0 -> w0 = B754_infinity prec emax s /\ w1 = pzero) /\
  (~ opfin -> canonical_of t w0 w1).
Proof.
intros z0 z1 t opfin cond P s Hcone Hcorr Hthr Hlead Hnf.
destruct (finite_dec prec emax z0) as [Fz|Fz].
- rewrite (fixup_fin z0 z1 t Fz).
  assert (O : opfin) by now apply Hcone.
  destruct (Hcorr O Fz) as [F1 [N B]].
  split; [|split; [|split; [|split]]].
  + left. split; [exact Fz|split; [exact F1|exact N]].
  + intros _. split; [exact O|split; [exact F1|split; [exact N|exact B]]].
  + intros _ _. exact Fz.
  + intros _ K. now elim K.
  + intros K. now elim K.
- assert (NO : opfin -> cond -> False).
  { intros O C. generalize (Hthr O C). congruence. }
  destruct (prod_pinf_cases prec emax nan_fma t) as [N|[s' E]].
  + rewrite (fixup_nan z0 z1 t Fz N).
    split; [|split; [|split; [|split]]].
    * right. right. split; exact N.
    * intros F. apply nan_not_finite in N. congruence.
    * intros O C. now elim (NO O C).
    * intros O _. rewrite (Hlead O Fz) in N. discriminate N.
    * intros K. destruct (not_finite_cases prec emax t (Hnf K)) as [Nt|[s'' Et]].
      -- left. split; [exact Nt|split; exact N].
      -- exfalso. rewrite Et, prod_pinf_inf in N. discriminate N.
  + rewrite (fixup_inf z0 z1 t s' Fz E).
    split; [|split; [|split; [|split]]].
    * right. left. split. now exists s'. now exists false.
    * intros F. discriminate F.
    * intros O C. now elim (NO O C).
    * intros O _. rewrite (Hlead O Fz) in E. inversion E. split; reflexivity.
    * intros K. destruct (not_finite_cases prec emax t (Hnf K)) as [Nt|[s'' Et]].
      -- exfalso. apply (prod_pinf_nan prec emax nan_fma) in Nt. rewrite E in Nt. discriminate Nt.
      -- rewrite Et in E |- *. rewrite prod_pinf_inf in E. inversion E. subst.
         right. exists s'. split; [reflexivity|split; reflexivity].
Qed.

(** * Helpers for the five facts *)

Lemma canonical_2_finite :
  forall x0 x1 : float, canonical_2 x0 x1 -> fin x0 ->
  fin x1 /\ normalized_2 emin prec (b2r x0) (b2r x1).
Proof.
intros x0 x1 [[_ [F1 N]]|[[[s E] _]|[N _]]] F0.
- split; assumption.
- rewrite E in F0. discriminate F0.
- apply nan_not_finite in N. congruence.
Qed.

Lemma not_both_finite :
  forall a b : float, ~ (fin a /\ fin b) ->
  is_finite prec emax a = false \/ is_finite prec emax b = false.
Proof.
intros a b K. destruct (is_finite prec emax a); [|now left].
destruct (is_finite prec emax b); [|now right]. elim K. split; reflexivity.
Qed.

(* A finite value in the cone of which an input lies: that input is finite. *)
Lemma cone_input :
  forall p (e : list float) z k,
  wf p (length e) = true -> mem k (cone p (length e) [z]) = true -> (k < length e)%nat ->
  fin (nth z (runB p e) d0) -> fin (nth k e d0).
Proof.
intros p e z k Hwf Hm Hk Hz.
rewrite <- (run_nth_old float stB p e k d0 Hk).
apply (cone_sound prec emax nan_plus nan_minus nan_opp nan_fma p e [z] Hwf).
- intros j [<-|[]]. exact Hz.
- now apply mem_In.
Qed.

(* A value that is not finite: some value of the real model is out of range. *)
Lemma overflow_out_of_range :
  forall p (e : list float) z, finite_all e ->
  is_finite prec emax (nth z (runB p e) d0) = false ->
  ~ Forall inrange (runR p (map b2r e)).
Proof.
intros p e z Fe Hz K.
destruct (run_sim prec emax nan_plus nan_minus nan_opp nan_fma p e Fe) as [[_ S] _].
assert (F := nth_fin prec emax (runB p e) z (S K)). congruence.
Qed.

(* Rounding keeps the sign of a number that it does not round to zero. *)
Lemma rnd_sign : forall v, rnd v <> 0 -> Rlt_bool (rnd v) 0 = Rlt_bool v 0.
Proof.
intros v Z. destruct (Rlt_bool_spec v 0) as [N|P].
- apply Rlt_bool_true.
  assert (K : rnd v <= 0).
  { apply round_le_generic; auto with typeclass_instances. apply generic_format_0. lra. }
  lra.
- apply Rlt_bool_false. apply round_ge_generic; auto with typeclass_instances.
  apply generic_format_0.
Qed.

(* The operation of T on finite leading limbs, made canonical: when its rounded real
   result is not zero, it is the infinity of the sign of the exact result of that
   operation, whether the operation overflowed or not. *)
Lemma lead_add :
  forall a b : float, fin a -> fin b -> rnd (b2r a + b2r b) <> 0 ->
  prod (add a b) pinf = B754_infinity prec emax (Rlt_bool (b2r a + b2r b) 0).
Proof.
intros a b Fa Fb Z.
assert (Zs : b2r a + b2r b <> 0).
{ intros E. apply Z. rewrite E. apply round_0; auto with typeclass_instances. }
generalize (Bplus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_plus
              BinarySingleNaN.mode_NE a b Fa Fb).
fold (add a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a + b2r b))
  with (rnd (b2r a + b2r b)).
destruct (Rlt_bool_spec (Rabs (rnd (b2r a + b2r b))) (bpow radix2 emax)) as [K|K].
- intros [E [F _]].
  rewrite (prod_pinf_sign prec emax nan_fma (add a b) F) by (rewrite E; exact Z).
  rewrite E. now rewrite rnd_sign.
- intros [E S]. rewrite overflow_NE in E. apply B2FF_inf_inv in E.
  rewrite E, prod_pinf_inf. f_equal.
  destruct (Rlt_bool_spec (b2r a + b2r b) 0) as [N|P].
  + destruct (Rlt_or_le (b2r a) 0) as [L|L]. now apply neg_sign.
    rewrite S. apply neg_sign. lra.
  + destruct (Rlt_or_le 0 (b2r a)) as [L|L]. now apply pos_sign.
    rewrite S. apply pos_sign. lra.
Qed.

Lemma lead_sub :
  forall a b : float, fin a -> fin b -> rnd (b2r a - b2r b) <> 0 ->
  prod (sub a b) pinf = B754_infinity prec emax (Rlt_bool (b2r a - b2r b) 0).
Proof.
intros a b Fa Fb Z.
assert (Zs : b2r a - b2r b <> 0).
{ intros E. apply Z. rewrite E. apply round_0; auto with typeclass_instances. }
generalize (Bminus_correct prec emax prec_gt_0_ prec_lt_emax_ nan_minus
              BinarySingleNaN.mode_NE a b Fa Fb).
fold (sub a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a - b2r b))
  with (rnd (b2r a - b2r b)).
destruct (Rlt_bool_spec (Rabs (rnd (b2r a - b2r b))) (bpow radix2 emax)) as [K|K].
- intros [E [F _]].
  rewrite (prod_pinf_sign prec emax nan_fma (sub a b) F) by (rewrite E; exact Z).
  rewrite E. now rewrite rnd_sign.
- intros [E S]. rewrite overflow_NE in E. apply B2FF_inf_inv in E.
  rewrite E, prod_pinf_inf. f_equal.
  destruct (Rlt_bool_spec (b2r a - b2r b) 0) as [N|P].
  + destruct (Rlt_or_le (b2r a) 0) as [L|L]. now apply neg_sign.
    rewrite S, (pos_sign prec emax b) by lra. reflexivity.
  + destruct (Rlt_or_le 0 (b2r a)) as [L|L]. now apply pos_sign.
    rewrite S, (neg_sign prec emax b) by lra. reflexivity.
Qed.

Lemma lead_prod :
  forall a b : float, fin a -> fin b -> rnd (b2r a * b2r b + 0) <> 0 ->
  prod (prod a b) pinf = B754_infinity prec emax (Rlt_bool (b2r a * b2r b) 0).
Proof.
intros a b Fa Fb Z.
generalize (Bfma_correct prec emax prec_gt_0_ prec_lt_emax_ nan_fma
              BinarySingleNaN.mode_NE a b pzero Fa Fb eq_refl).
cbv zeta. fold (fma a b pzero). fold (prod a b).
change (round radix2 (SpecFloat.fexp prec emax)
          (BinarySingleNaN.round_mode BinarySingleNaN.mode_NE) (b2r a * b2r b + b2r pzero))
  with (rnd (b2r a * b2r b + 0)).
change (b2r pzero) with 0.
destruct (Rlt_bool_spec (Rabs (rnd (b2r a * b2r b + 0))) (bpow radix2 emax)) as [K|K].
- intros [E [F _]].
  rewrite (prod_pinf_sign prec emax nan_fma (prod a b) F) by (rewrite E; exact Z).
  rewrite E, rnd_sign by exact Z. now rewrite Rplus_0_r.
- intros E. rewrite overflow_NE in E. apply B2FF_inf_inv in E.
  rewrite E, prod_pinf_inf. now rewrite Rplus_0_r.
Qed.

(* A value v beyond Q in magnitude and a number S within U of it, with 2 U <= Q: S does
   not round to zero and has the sign of v. Here v is the exact result of an addition
   and S the sum of the leading limbs. *)
Lemma sum_sign :
  (3 <= prec)%Z ->
  forall v S : R, Q < Rabs v -> Rabs (v - S) <= U ->
  rnd S <> 0 /\ Rlt_bool S 0 = Rlt_bool v 0.
Proof.
intros Hp3 v S Hv Hd.
assert (U0 : 0 < U) by apply bpow_gt_0.
assert (T : 2 * U <= Q).
{ rewrite (two_U prec emax). apply bpow_le. lia. }
assert (FU : format U).
{ apply generic_format_bpow. unfold FLT_exp. lia. }
apply Rabs_le_inv in Hd.
assert (HS : U <= Rabs S).
{ unfold Rabs in *. destruct (Rcase_abs v), (Rcase_abs S); lra. }
split.
- intros Z. generalize (round_abs_ge emin prec tie_even S U FU HS). rewrite Z, Rabs_R0. lra.
- unfold Rabs in Hv, HS. destruct (Rcase_abs v), (Rcase_abs S); try lra.
  + rewrite 2!Rlt_bool_true by lra. reflexivity.
  + rewrite 2!Rlt_bool_false by lra. reflexivity.
Qed.

(* The exact product of two normalized pairs has the sign of the product of the
   leading limbs, when that is not zero. *)
Lemma prod_sign :
  forall x0 x1 y0 y1 : R,
  normalized_2 emin prec x0 x1 -> normalized_2 emin prec y0 y1 -> x0 * y0 <> 0 ->
  Rlt_bool (x0 * y0) 0 = Rlt_bool ((x0 + x1) * (y0 + y1)) 0.
Proof.
intros x0 x1 y0 y1 Nx Ny Z.
assert (Zx : x0 <> 0) by (intros E; apply Z; rewrite E; ring).
assert (Zy : y0 <> 0) by (intros E; apply Z; rewrite E; ring).
generalize (normalized_2_pos emin prec x0 x1 Nx) (normalized_2_neg emin prec x0 x1 Nx)
           (normalized_2_pos emin prec y0 y1 Ny) (normalized_2_neg emin prec y0 y1 Ny).
intros Px Mx Py My.
destruct (Rtotal_order x0 0) as [Lx|[Ex|Gx]]; [|now elim Zx|];
  destruct (Rtotal_order y0 0) as [Ly|[Ey|Gy]]; try (now elim Zy);
  [specialize (Mx Lx); specialize (My Ly)|specialize (Mx Lx); specialize (Py Gy)
  |specialize (Px Gx); specialize (My Ly)|specialize (Px Gx); specialize (Py Gy)].
- rewrite 2!Rlt_bool_false by nra. reflexivity.
- rewrite 2!Rlt_bool_true by nra. reflexivity.
- rewrite 2!Rlt_bool_true by nra. reflexivity.
- rewrite 2!Rlt_bool_false by nra. reflexivity.
Qed.

(* The same with a one-limb second factor. *)
Lemma prod_sign_1 :
  forall x0 x1 a : R,
  normalized_2 emin prec x0 x1 -> x0 * a <> 0 ->
  Rlt_bool (x0 * a) 0 = Rlt_bool ((x0 + x1) * a) 0.
Proof.
intros x0 x1 a Nx Z.
assert (Zx : x0 <> 0) by (intros E; apply Z; rewrite E; ring).
assert (Za : a <> 0) by (intros E; apply Z; rewrite E; ring).
generalize (normalized_2_pos emin prec x0 x1 Nx) (normalized_2_neg emin prec x0 x1 Nx).
intros Px Mx.
destruct (Rtotal_order x0 0) as [Lx|[Ex|Gx]]; [|now elim Zx|];
  destruct (Rtotal_order a 0) as [La|[Ea|Ga]]; try (now elim Za);
  [specialize (Mx Lx)|specialize (Mx Lx)|specialize (Px Gx)|specialize (Px Gx)].
- rewrite 2!Rlt_bool_false by nra. reflexivity.
- rewrite 2!Rlt_bool_true by nra. reflexivity.
- rewrite 2!Rlt_bool_true by nra. reflexivity.
- rewrite 2!Rlt_bool_false by nra. reflexivity.
Qed.

(* The leading limb of a pair whose value is at most 2^k is at most 2^k. *)
Lemma lead_le_bpow :
  forall (x0 x1 : R) (k : Z), normalized_2 emin prec x0 x1 ->
  Rabs (x0 + x1) <= bpow radix2 k -> Rabs x0 <= bpow radix2 k.
Proof.
intros x0 x1 k [_ [_ E]] Hx. rewrite E. now apply (RN_abs_le_bpow emin prec).
Qed.

(** * add_2_2_full *)

Notation add_2_2 := (IeeeDraft.add_2_2 prec emax nan_plus nan_minus).
Notation add_2_2_full := (IeeeDraft.add_2_2_full prec emax nan_plus nan_minus nan_abs nan_fma).

Lemma add_2_2_full_eq :
  forall x0 x1 y0 y1 : float,
  add_2_2_full x0 x1 y0 y1
  = fixup (fst (add_2_2 x0 x1 y0 y1)) (snd (add_2_2 x0 x1 y0 y1)) (add x0 y0).
Proof.
intros. unfold IeeeDraft.add_2_2_full.
destruct (IeeeDraft.add_2_2 prec emax nan_plus nan_minus x0 x1 y0 y1) as [z0 z1]. reflexivity.
Qed.

Lemma add_2_2_full_facts :
  (3 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(w0, w1) := add_2_2_full x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (fin w0 -> (fin x0 /\ fin y0) /\ fin w1 /\ normalized_2 emin prec (b2r w0) (b2r w1) /\
   Rabs ((b2r w0 + b2r w1) - ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
   <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1))) /\
  (fin x0 /\ fin y0 ->
   Rabs (b2r x0 + b2r x1) <= Q /\ Rabs (b2r y0 + b2r y1) <= Q -> fin w0) /\
  (fin x0 /\ fin y0 -> ~ fin w0 ->
   w0 = B754_infinity prec emax (Rlt_bool ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)) 0) /\
   w1 = pzero) /\
  (~ (fin x0 /\ fin y0) -> canonical_of (add x0 y0) w0 w1).
Proof.
intros Hp3 x0 x1 y0 y1 Cx Cy. rewrite add_2_2_full_eq.
set (e := [x0; x1; y0; y1]).
assert (Ez : fst (add_2_2 x0 x1 y0 y1) = nth 21 (runB IeeeDraft.add_2_2_prog e) d0).
{ unfold e. now rewrite (add_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma). }
apply (full_template _ _ _ (fin x0 /\ fin y0)
         (Rabs (b2r x0 + b2r x1) <= Q /\ Rabs (b2r y0 + b2r y1) <= Q)
         (fun w0 w1 => Rabs ((b2r w0 + b2r w1) - ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))
            <= (3 / (1 - (4 * u prec))) * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1)))).
- (* cone *)
  rewrite Ez. intros Fz. split.
  + exact (cone_input IeeeDraft.add_2_2_prog e 21 0 eq_refl eq_refl (Nat.lt_0_succ 3) Fz).
  + apply (cone_input IeeeDraft.add_2_2_prog e 21 2 eq_refl eq_refl); trivial. simpl. lia.
- (* correctness *)
  intros [F0 G0]. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  generalize (add_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp3
                x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
  destruct (add_2_2 x0 x1 y0 y1) as [z0 z1]. cbn [fst snd]. tauto.
- (* threshold *)
  intros [F0 G0] [Hx Hy]. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  generalize (add_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp3
                x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny
                (lead_le_bpow _ _ _ Nx Hx) (lead_le_bpow _ _ _ Ny Hy)).
  destruct (add_2_2 x0 x1 y0 y1) as [z0 z1]. cbn [fst snd]. tauto.
- (* overflow *)
  intros [F0 G0] Fz. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  rewrite Ez in Fz.
  assert (Fe : finite_all e) by (repeat constructor; assumption).
  generalize (overflow_out_of_range IeeeDraft.add_2_2_prog e 21 Fe Fz). intros Out.
  assert (Hv : Q < Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1))).
  { apply Rnot_le_lt. intros K. apply Out.
    exact (add_2_2_range_sum prec emax Hp3 x0 x1 y0 y1 Nx Ny K). }
  assert (Hd : Rabs ((b2r x0 + b2r x1) + (b2r y0 + b2r y1) - (b2r x0 + b2r y0)) <= U).
  { replace ((b2r x0 + b2r x1) + (b2r y0 + b2r y1) - (b2r x0 + b2r y0))
      with (b2r x1 + b2r y1) by ring.
    apply Rle_trans with (1 := Rabs_triang _ _).
    generalize (tail_le_half_U prec emax x0 x1 Nx) (tail_le_half_U prec emax y0 y1 Ny). lra. }
  destruct (sum_sign Hp3 _ _ Hv Hd) as [Z E].
  rewrite <- E. now apply lead_add.
- (* a non-finite operand *)
  intros K. apply (add_not_finite prec emax nan_plus). now apply not_both_finite.
Qed.

(** * mul_2_2_full *)

Notation mul_2_2 := (IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma).
Notation mul_2_2_full :=
  (IeeeDraft.mul_2_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma).

Lemma mul_2_2_full_eq :
  forall x0 x1 y0 y1 : float,
  mul_2_2_full x0 x1 y0 y1
  = fixup (fst (mul_2_2 x0 x1 y0 y1)) (snd (mul_2_2 x0 x1 y0 y1)) (prod x0 y0).
Proof.
intros. unfold IeeeDraft.mul_2_2_full.
destruct (IeeeDraft.mul_2_2 prec emax nan_plus nan_minus nan_opp nan_fma x0 x1 y0 y1) as [z0 z1].
reflexivity.
Qed.

Lemma mul_2_2_full_facts :
  (4 <= prec)%Z ->
  forall x0 x1 y0 y1 : float, canonical_2 x0 x1 -> canonical_2 y0 y1 ->
  let '(w0, w1) := mul_2_2_full x0 x1 y0 y1 in
  canonical_2 w0 w1 /\
  (fin w0 -> (fin x0 /\ fin y0) /\ fin w1 /\ normalized_2 emin prec (b2r w0) (b2r w1) /\
   Rabs ((b2r w0 + b2r w1) - ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)))
   <= 4 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) + (3 / 2) * eta emin) /\
  (fin x0 /\ fin y0 ->
   Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 1) -> fin w0) /\
  (fin x0 /\ fin y0 -> ~ fin w0 ->
   w0 = B754_infinity prec emax (Rlt_bool ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) 0) /\
   w1 = pzero) /\
  (~ (fin x0 /\ fin y0) -> canonical_of (prod x0 y0) w0 w1).
Proof.
intros Hp4 x0 x1 y0 y1 Cx Cy. rewrite mul_2_2_full_eq.
set (e := [x0; x1; y0; y1]).
assert (Ez : fst (mul_2_2 x0 x1 y0 y1) = nth 10 (runB IeeeDraft.mul_2_2_prog e) d0).
{ unfold e. now rewrite (mul_2_2_runB prec emax nan_plus nan_minus nan_opp nan_fma). }
apply (full_template _ _ _ (fin x0 /\ fin y0)
         (Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)) <= bpow radix2 (emax - 1))
         (fun w0 w1 => Rabs ((b2r w0 + b2r w1) - ((b2r x0 + b2r x1) * (b2r y0 + b2r y1)))
            <= 4 * u prec ^ 2 * Rabs ((b2r x0 + b2r x1) * (b2r y0 + b2r y1))
               + (3 / 2) * eta emin)).
- (* cone *)
  rewrite Ez. intros Fz. split.
  + exact (cone_input IeeeDraft.mul_2_2_prog e 10 0 eq_refl eq_refl (Nat.lt_0_succ 3) Fz).
  + apply (cone_input IeeeDraft.mul_2_2_prog e 10 2 eq_refl eq_refl); trivial. simpl. lia.
- (* correctness *)
  intros [F0 G0]. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  generalize (mul_2_2_values_correct prec emax nan_plus nan_minus nan_opp nan_fma Hp4
                x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny).
  destruct (mul_2_2 x0 x1 y0 y1) as [z0 z1]. cbn [fst snd]. tauto.
- (* threshold *)
  intros [F0 G0] Hxy. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  generalize (mul_2_2_values_finite prec emax nan_plus nan_minus nan_opp nan_fma Hp4
                x0 x1 y0 y1 F0 F1 G0 G1 Nx Ny Hxy).
  destruct (mul_2_2 x0 x1 y0 y1) as [z0 z1]. cbn [fst snd]. tauto.
- (* overflow *)
  intros [F0 G0] Fz. destruct (canonical_2_finite x0 x1 Cx F0) as [F1 Nx].
  destruct (canonical_2_finite y0 y1 Cy G0) as [G1 Ny].
  rewrite Ez in Fz.
  assert (Fe : finite_all e) by (repeat constructor; assumption).
  generalize (overflow_out_of_range IeeeDraft.mul_2_2_prog e 10 Fe Fz). intros Out.
  assert (Z : rnd (b2r x0 * b2r y0 + 0) <> 0).
  { intros K. apply Out. exact (mul_2_2_range_zero prec emax x0 x1 y0 y1 Nx Ny K). }
  assert (Zp : b2r x0 * b2r y0 <> 0).
  { intros K. apply Z. rewrite K, Rplus_0_r. apply round_0; auto with typeclass_instances. }
  rewrite <- (prod_sign _ _ _ _ Nx Ny Zp). now apply lead_prod.
- (* a non-finite operand *)
  intros K. apply (prod_not_finite prec emax nan_fma). now apply not_both_finite.
Qed.

End IeeeFull.

(** * The statements of IeeeExtStatementsDraft.v *)

(* From the five facts of a kernel to its statement: the same facts, with the
   hypotheses one by one, and with the finiteness of the second limbs, which a canonical
   operand with a finite leading limb has. *)
Ltac full_glue :=
  unfold finite, val, ieee_emin, infinity, pos_zero, IeeeDraft.pzero in *;
  intros [F1 [F2 [F3 [F4 F5]]]]; tauto.

Theorem add_2_2_full_correct : add_2_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_abs nan_fma Hp3 x0 x1 y0 y1 Cx Cy t. subst t.
generalize (add_2_2_full_facts prec emax nan_plus nan_minus (fun x => nan_plus x x) nan_abs nan_fma
              Hp3 x0 x1 y0 y1 Cx Cy).
destruct (IeeeDraft.add_2_2_full prec emax nan_plus nan_minus nan_abs nan_fma x0 x1 y0 y1) as [w0 w1].
generalize (fun F => proj1 (canonical_2_finite prec emax x0 x1 Cx F))
           (fun F => proj1 (canonical_2_finite prec emax y0 y1 Cy F)).
intros Gx Gy. full_glue.
Qed.

Theorem mul_2_2_full_correct : mul_2_2_full_spec.
Proof.
intros prec emax Hp He nan_plus nan_minus nan_opp nan_abs nan_fma Hp4 x0 x1 y0 y1 Cx Cy t. subst t.
generalize (mul_2_2_full_facts prec emax nan_plus nan_minus nan_opp nan_abs nan_fma
              Hp4 x0 x1 y0 y1 Cx Cy).
destruct (IeeeDraft.mul_2_2_full prec emax nan_plus nan_minus nan_opp nan_abs nan_fma x0 x1 y0 y1)
  as [w0 w1].
generalize (fun F => proj1 (canonical_2_finite prec emax x0 x1 Cx F))
           (fun F => proj1 (canonical_2_finite prec emax y0 y1 Cy F)).
intros Gx Gy. full_glue.
Qed.
