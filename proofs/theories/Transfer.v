(* Kernels made only of additions and subtractions compute the same values in every
   format in which their operands live.

   The kernels of ModelDraft.v are written with the rounding of one format. Here the same
   programs are written over an arbitrary rounding function (g_two_sum, ...), and shown to
   return the same values for two rounding functions that agree on sums and differences
   of the numbers of a set F which contains every rounded result. By the transfer lemmas
   of Format.v this applies to:
   - the format with gradual underflow and the format without underflow (so theorems
     proved without underflow, such as MR22's, carry over);
   - two formats with gradual underflow and different eta. *)
From Stdlib Require Import Reals ZArith Lia Lra.
From Flocq Require Import Core.
From Kairn Require Import ModelDraft SpecDraft Format.
Open Scope R_scope.

(** * The addition kernels over an arbitrary rounding function *)

Section Generic.
Variable rnd : R -> R.

Definition g_two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let bb := rnd (s - a) in
  let t0 := rnd (s - bb) in
  let t1 := rnd (a - t0) in
  let t2 := rnd (b - bb) in
  let e := rnd (t1 + t2) in
  (s, e).

Definition g_fast_two_sum (a b : R) : R * R :=
  let s := rnd (a + b) in
  let z := rnd (s - a) in
  let e := rnd (b - z) in
  (s, e).

Definition g_add_2_2 (x0 x1 y0 y1 : R) : R * R :=
  let '(sh, sl) := g_two_sum x0 y0 in
  let '(th, tl) := g_two_sum x1 y1 in
  let c := rnd (sl + th) in
  let '(vh, vl) := g_fast_two_sum sh c in
  let w := rnd (tl + vl) in
  let '(z0, z1) := g_fast_two_sum vh w in
  (z0, z1).

Definition g_add_2_1 (x0 x1 a : R) : R * R :=
  let '(sh, sl) := g_two_sum x0 a in
  let v := rnd (x1 + sl) in
  let '(z0, z1) := g_fast_two_sum sh v in
  (z0, z1).

End Generic.

(* The kernels of the model are these programs, by definition. *)
Section Instances.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

Lemma two_sum_g : forall a b, two_sum emin prec choice a b = g_two_sum rnd a b.
Proof. reflexivity. Qed.
Lemma fast_two_sum_g : forall a b, fast_two_sum emin prec choice a b = g_fast_two_sum rnd a b.
Proof. reflexivity. Qed.
Lemma add_2_2_g : forall x0 x1 y0 y1,
  add_2_2 emin prec choice x0 x1 y0 y1 = g_add_2_2 rnd x0 x1 y0 y1.
Proof. reflexivity. Qed.
Lemma add_2_1_g : forall x0 x1 a, add_2_1 emin prec choice x0 x1 a = g_add_2_1 rnd x0 x1 a.
Proof. reflexivity. Qed.
End Instances.

(** * Two rounding functions that agree on sums give the same results *)

Section Agree.
Variables rnd1 rnd2 : R -> R.
Variable F : R -> Prop.
Hypothesis HF : forall x, F (rnd1 x).
Hypothesis Hplus : forall a b, F a -> F b -> rnd1 (a + b) = rnd2 (a + b).
Hypothesis Hminus : forall a b, F a -> F b -> rnd1 (a - b) = rnd2 (a - b).

(* Rewrite the operations of the second program into those of the first, innermost
   first: an operation can be rewritten once its operands are inputs or results of the
   first rounding. *)
Ltac transfer :=
  repeat match goal with
  | |- context [rnd2 (?a + ?b)] => rewrite <- (Hplus a b) by auto
  | |- context [rnd2 (?a - ?b)] => rewrite <- (Hminus a b) by auto
  end.

Lemma g_two_sum_agree : forall a b, F a -> F b -> g_two_sum rnd1 a b = g_two_sum rnd2 a b.
Proof. intros a b Fa Fb. unfold g_two_sum. cbv zeta. transfer. reflexivity. Qed.

Lemma g_fast_two_sum_agree :
  forall a b, F a -> F b -> g_fast_two_sum rnd1 a b = g_fast_two_sum rnd2 a b.
Proof. intros a b Fa Fb. unfold g_fast_two_sum. cbv zeta. transfer. reflexivity. Qed.

Lemma g_add_2_2_agree :
  forall x0 x1 y0 y1, F x0 -> F x1 -> F y0 -> F y1 ->
  g_add_2_2 rnd1 x0 x1 y0 y1 = g_add_2_2 rnd2 x0 x1 y0 y1.
Proof.
intros x0 x1 y0 y1 F0 F1 G0 G1.
unfold g_add_2_2, g_two_sum, g_fast_two_sum. cbv zeta beta iota. transfer. reflexivity.
Qed.

Lemma g_add_2_1_agree :
  forall x0 x1 a, F x0 -> F x1 -> F a ->
  g_add_2_1 rnd1 x0 x1 a = g_add_2_1 rnd2 x0 x1 a.
Proof.
intros x0 x1 a F0 F1 Fa.
unfold g_add_2_1, g_two_sum, g_fast_two_sum. cbv zeta beta iota. transfer. reflexivity.
Qed.

End Agree.

(** * The two instances *)

Section FLT_FLX.
Variable emin prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Variable choice : Z -> bool.
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).
Notation rndx := (round radix2 (FLX_exp prec) (Znearest choice)).

Let HF : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.
Let Hplus : forall a b, format a -> format b -> rnd (a + b) = rndx (a + b).
Proof. intros a b Fa Fb. apply round_plus_FLT_FLX; auto with typeclass_instances. Qed.
Let Hminus : forall a b, format a -> format b -> rnd (a - b) = rndx (a - b).
Proof. intros a b Fa Fb. apply round_minus_FLT_FLX; auto with typeclass_instances. Qed.

(* With operands in F, the addition kernels return the same values with and without
   underflow. *)
Lemma two_sum_FLX : forall a b, format a -> format b ->
  two_sum emin prec choice a b = g_two_sum rndx a b.
Proof. intros. rewrite two_sum_g. now apply g_two_sum_agree with (F := fun x => format x). Qed.

Lemma fast_two_sum_FLX : forall a b, format a -> format b ->
  fast_two_sum emin prec choice a b = g_fast_two_sum rndx a b.
Proof.
intros. rewrite fast_two_sum_g. now apply g_fast_two_sum_agree with (F := fun x => format x).
Qed.

Lemma add_2_2_FLX : forall x0 x1 y0 y1, format x0 -> format x1 -> format y0 -> format y1 ->
  add_2_2 emin prec choice x0 x1 y0 y1 = g_add_2_2 rndx x0 x1 y0 y1.
Proof. intros. rewrite add_2_2_g. now apply g_add_2_2_agree with (F := fun x => format x). Qed.

Lemma add_2_1_FLX : forall x0 x1 a, format x0 -> format x1 -> format a ->
  add_2_1 emin prec choice x0 x1 a = g_add_2_1 rndx x0 x1 a.
Proof. intros. rewrite add_2_1_g. now apply g_add_2_1_agree with (F := fun x => format x). Qed.

End FLT_FLX.

Section FLT_emin.
Variable emin emin' prec : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Hypothesis Hemin : (emin' <= emin)%Z.
Variable choice : Z -> bool.
Notation format := (generic_format radix2 (FLT_exp emin prec)).
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).
Notation rnd' := (round radix2 (FLT_exp emin' prec) (Znearest choice)).

Let HF : forall x, format (rnd x).
Proof. intros x. apply generic_format_round; auto with typeclass_instances. Qed.
Let Hplus : forall a b, format a -> format b -> rnd (a + b) = rnd' (a + b).
Proof. intros a b Fa Fb. apply round_plus_FLT_emin; auto with typeclass_instances. Qed.
Let Hminus : forall a b, format a -> format b -> rnd (a - b) = rnd' (a - b).
Proof. intros a b Fa Fb. apply round_minus_FLT_emin; auto with typeclass_instances. Qed.

(* With operands in F, the two error-free additions return the same values in a format
   with a smaller eta. *)
Lemma two_sum_emin : forall a b, format a -> format b ->
  two_sum emin prec choice a b = two_sum emin' prec choice a b.
Proof.
intros. rewrite 2!two_sum_g. now apply g_two_sum_agree with (F := fun x => format x).
Qed.

Lemma fast_two_sum_emin : forall a b, format a -> format b ->
  fast_two_sum emin prec choice a b = fast_two_sum emin' prec choice a b.
Proof.
intros. rewrite 2!fast_two_sum_g.
now apply g_fast_two_sum_agree with (F := fun x => format x).
Qed.

End FLT_emin.
