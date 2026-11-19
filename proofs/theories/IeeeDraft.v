(* DRAFT of the IEEE model of the kernels, written by hand in the form the generator is
   meant to print. Nothing in this file is a proof.

   What it is. proofs/gen/Model.v defines each kernel over the real numbers, in a format
   with no largest number. Here the same kernels are defined over Flocq's type
   binary_float prec emax: the finite numbers of the format with signed zeros, the two
   infinities, and NaN, with Flocq's definitions of the IEEE 754 operations, overflow
   included. Rounding is to nearest, ties to even (mode_NE).

   The format. binary_float prec emax is the IEEE format with precision prec whose
   numbers are below 2^emax in magnitude: the largest one is
   Omega = 2^emax - 2^(emax - prec), and the smallest positive one is 2^emin with
   emin = 3 - emax - prec. Flocq fixes this relation between the two ends of the range,
   as IEEE 754 does. binary64 is prec = 53, emax = 1024; binary32 is prec = 24,
   emax = 128. Flocq requires 0 < prec < emax. So, of the toy formats (p, qmin, qmax) of
   the test tools, this model covers those with qmin + qmax = 3 - 2 p.

   NaN. Which NaN an operation returns (its sign and payload) is not specified here:
   Flocq's operations take it as a function of the operands, and these functions are
   variables of the section below, hence parameters of every definition. The NaN that
   `const nan` denotes is one more such variable. No statement depends on them. They are
   not axioms.

   Correspondence with the kernel descriptions (gen/kernels), one operation each:
     add a b      Bplus          a + b
     sub a b      Bminus         a - b
     neg a        Bopp           - a
     abs a        Babs           |a|
     fma a b c    Bfma           fma(a, b, c)
     fms a b c    Bfma, Bopp     fma(a, b, -c)
     prod a b     Bfma           fma(a, b, +0.0)
     lt le eq     Bltb Bleb Beqb a mask is a bool; a comparison with a NaN is false
     and or not   andb orb negb
     select m a b                if m then a else b
     succ a       Bsucc          the next number above a: +infinity above the largest
                                 number, the smallest positive number above either zero,
                                 the largest negative number above -infinity
     pred a       Bpred          the next number below a
     guard a      Bplus          a + (+0): the value of a; a zero comes out as +0, an
                                 infinity is unchanged, a NaN stays a NaN
     0            pzero          +0
     const inf    pinf           +infinity
     const nan    cnan           a NaN
     const radius_e(K), const radius_g(K), const radius_h(K)
                  const_of       the number of the format whose value is the constant
                                 of the same name in the real model (BallDraft.v)
   A call stays a call, as in Model.v, and the names of the values are those of the
   kernel descriptions and of the listings of docs/developer/design/milestone1.md.

   The file has four parts: the finite cores (the kernels of gen/kernels); the full
   kernels, each a core followed by the fix-up that makes its result canonical; the
   constructor kernels; and some of the cores as straight-line programs (Program.v), the
   list of their operations after inlining the calls. The programs are the form on which
   the relation between the two models is proved (IeeeBridge.v); that each program is
   its kernel is checked by computation where it is used.

   Four points where this draft is ahead of the generated files:
   - the Ball cores are those of the second radius design (BallDraft.v): the radius is
     evaluated by operations rounded to nearest and inflated once. proofs/gen/Model.v
     still has the first design;
   - add_2_1 guards its one-limb operand in its first line, as in the listing of
     milestone1.md; the real model of proofs/gen/Model.v does not yet. The two compute
     the same values (IeeeMore.v, add_2_1_runR);
   - the full kernels and the constructor kernels have no description in gen/kernels yet;
   - where a listing would define the value `a` twice (the fix-up computes a = abs(z0),
     and four full kernels and ball_scale_k_full also have an operand `a`), the value of
     the fix-up is named `az` here. In ball_make_1 the guarded center is named `h`. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Model.
From Kairn Require BallDraft.
From Kairn Require Import Program.
Import ListNotations.

Section IeeeKernels.
Variable prec emax : Z.
Context {prec_gt_0_ : Prec_gt_0 prec}.
Context {prec_lt_emax_ : BinarySingleNaN.Prec_lt_emax prec emax}.

Notation float := (binary_float prec emax).
Notation nan_of := {x : float | is_nan prec emax x = true}.

(* The NaN returned by each operation, as a function of its operands. *)
Variable nan_plus : float -> float -> nan_of.
Variable nan_minus : float -> float -> nan_of.
Variable nan_opp : float -> nan_of.
Variable nan_abs : float -> nan_of.
Variable nan_fma : float -> float -> float -> nan_of.
(* The NaN that `const nan` denotes. *)
Variable nan_const : nan_of.

(** * The operations *)

Definition pzero : float := B754_zero prec emax false.
Definition pinf : float := B754_infinity prec emax false.
Definition cnan : float := proj1_sig nan_const.

Definition add (a b : float) : float :=
  Bplus prec emax prec_gt_0_ prec_lt_emax_ nan_plus BinarySingleNaN.mode_NE a b.
Definition sub (a b : float) : float :=
  Bminus prec emax prec_gt_0_ prec_lt_emax_ nan_minus BinarySingleNaN.mode_NE a b.
Definition neg (a : float) : float :=
  Bopp prec emax nan_opp a.
Definition fma (a b c : float) : float :=
  Bfma prec emax prec_gt_0_ prec_lt_emax_ nan_fma BinarySingleNaN.mode_NE a b c.
Definition fms (a b c : float) : float := fma a b (neg c).
Definition prod (a b : float) : float := fma a b pzero.
Definition abs (a : float) : float :=
  Babs prec emax nan_abs a.
Definition lt (a b : float) : bool :=
  @BinarySingleNaN.Bltb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition le (a b : float) : bool :=
  @BinarySingleNaN.Bleb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition eq (a b : float) : bool :=
  @BinarySingleNaN.Beqb prec emax (B2BSN prec emax a) (B2BSN prec emax b).
Definition succ (a : float) : float :=
  Bsucc prec emax prec_gt_0_ prec_lt_emax_ a.
Definition pred (a : float) : float :=
  Bpred prec emax prec_gt_0_ prec_lt_emax_ a.
Definition guard (a : float) : float := add a pzero.

(* The number of the format whose value is r, for a real number r that is one (r is a
   number of the format with no largest number, and below 2^emax in magnitude); for any
   other r, some number. The constants of the Ball kernels are given this way, from their
   definitions in the real model (BallDraft.v). *)
Definition const_of (r : R) : float :=
  binary_normalize prec emax prec_gt_0_ prec_lt_emax_ BinarySingleNaN.mode_NE
    (Ztrunc (scaled_mantissa radix2 (FLT_exp (3 - emax - prec) prec) r))
    (cexp radix2 (FLT_exp (3 - emax - prec) prec) r) false.

Definition radius_e_ball_add_1 : float :=
  const_of (BallDraft.radius_e_ball_add_1 (3 - emax - prec) prec).
Definition radius_g_ball_add_1 : float :=
  const_of (BallDraft.radius_g_ball_add_1 (3 - emax - prec) prec).
Definition radius_h_ball_add_1 : float :=
  const_of (BallDraft.radius_h_ball_add_1 (3 - emax - prec) prec).
Definition radius_e_ball_add_2 : float :=
  const_of (BallDraft.radius_e_ball_add_2 (3 - emax - prec) prec).
Definition radius_g_ball_add_2 : float :=
  const_of (BallDraft.radius_g_ball_add_2 (3 - emax - prec) prec).
Definition radius_h_ball_add_2 : float :=
  const_of (BallDraft.radius_h_ball_add_2 (3 - emax - prec) prec).
Definition radius_e_ball_scale_1 : float :=
  const_of (BallDraft.radius_e_ball_scale_1 (3 - emax - prec) prec).
Definition radius_g_ball_scale_1 : float :=
  const_of (BallDraft.radius_g_ball_scale_1 (3 - emax - prec) prec).
Definition radius_h_ball_scale_1 : float :=
  const_of (BallDraft.radius_h_ball_scale_1 (3 - emax - prec) prec).
Definition radius_e_ball_scale_2 : float :=
  const_of (BallDraft.radius_e_ball_scale_2 (3 - emax - prec) prec).
Definition radius_g_ball_scale_2 : float :=
  const_of (BallDraft.radius_g_ball_scale_2 (3 - emax - prec) prec).
Definition radius_h_ball_scale_2 : float :=
  const_of (BallDraft.radius_h_ball_scale_2 (3 - emax - prec) prec).
Definition radius_e_ball_mul_1 : float :=
  const_of (BallDraft.radius_e_ball_mul_1 (3 - emax - prec) prec).
Definition radius_g_ball_mul_1 : float :=
  const_of (BallDraft.radius_g_ball_mul_1 (3 - emax - prec) prec).
Definition radius_h_ball_mul_1 : float :=
  const_of (BallDraft.radius_h_ball_mul_1 (3 - emax - prec) prec).
Definition radius_e_ball_mul_2 : float :=
  const_of (BallDraft.radius_e_ball_mul_2 (3 - emax - prec) prec).
Definition radius_g_ball_mul_2 : float :=
  const_of (BallDraft.radius_g_ball_mul_2 (3 - emax - prec) prec).
Definition radius_h_ball_mul_2 : float :=
  const_of (BallDraft.radius_h_ball_mul_2 (3 - emax - prec) prec).

(** * The finite cores *)

(* fast_two_sum: Fast2Sum (Dekker 1971). *)
Definition fast_two_sum (a b : float) : float * float :=
  let s := add a b in
  let z := sub s a in
  let e := sub b z in
  (s, e).

(* two_prod: TwoProd with an FMA (folklore; see JMP17). *)
Definition two_prod (a b : float) : float * float :=
  let p := prod a b in
  let e := fms a b p in
  (p, e).

(* two_sum: TwoSum (Knuth, TAOCP vol. 2, 4.2.2; Moller 1965). *)
Definition two_sum (a b : float) : float * float :=
  let s := add a b in
  let bb := sub s a in
  let t0 := sub s bb in
  let t1 := sub a t0 in
  let t2 := sub b bb in
  let e := add t1 t2 in
  (s, e).

(* add_2_2: JMP17 Alg. 6 (AccurateDWPlusDW); bound from MR22. *)
Definition add_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let '(sh, sl) := two_sum x0 y0 in
  let '(th, tl) := two_sum x1 y1 in
  let c := add sl th in
  let '(vh, vl) := fast_two_sum sh c in
  let w := add tl vl in
  let '(z0, z1) := fast_two_sum vh w in
  (z0, z1).

(* mul_2_2: JMP17 Alg. 12 (DWTimesDW3); bound from MR22. *)
Definition mul_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let '(ch, cl1) := two_prod x0 y0 in
  let tl0 := prod x1 y1 in
  let tl1 := fma x0 y1 tl0 in
  let cl2 := fma x1 y0 tl1 in
  let cl3 := add cl1 cl2 in
  let '(z0, z1) := fast_two_sum ch cl3 in
  (z0, z1).

(* add_2_1: JMP17 Alg. 4 (DWPlusFP); bound from MR22. The operand a enters from the
   program and is guarded (rule R3). *)
Definition add_2_1 (x0 x1 a : float) : float * float :=
  let g := guard a in
  let '(sh, sl) := two_sum x0 g in
  let v := add x1 sl in
  let '(z0, z1) := fast_two_sum sh v in
  (z0, z1).

(* mul_2_1: JMP17 Alg. 9 (DWTimesFP3); bound from MR22. *)
Definition mul_2_1 (x0 x1 a : float) : float * float :=
  let '(ch, cl1) := two_prod x0 a in
  let cl3 := fma x1 a cl1 in
  let '(z0, z1) := fast_two_sum ch cl3 in
  (z0, z1).

(* add_fast_2_2: JMP17 Alg. 5 (SloppyDWPlusDW). *)
Definition add_fast_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let '(sh, sl) := two_sum x0 y0 in
  let v := add x1 y1 in
  let w := add sl v in
  let '(z0, z1) := fast_two_sum sh w in
  (z0, z1).

(* add_1_1, mul_1_1: one rounding to nearest. *)
Definition add_1_1 (a b : float) : float :=
  let s := add a b in
  s.

Definition mul_1_1 (a b : float) : float :=
  let p := prod a b in
  p.

(* neg_2: limb by limb (Milestone 1 listing). *)
Definition neg_2 (x0 x1 : float) : float * float :=
  let z0 := neg x0 in
  let z1 := neg x1 in
  (z0, z1).

(* abs_2: the sign of x0 (Milestone 1 listing). *)
Definition abs_2 (x0 x1 : float) : float * float :=
  let m := lt x0 pzero in
  let n0 := neg x0 in
  let n1 := neg x1 in
  let z0 := if m then n0 else x0 in
  let z1 := if m then n1 else x1 in
  (z0, z1).

(* sub_2_2: add_2_2 (JMP17 Alg. 6) on -y. *)
Definition sub_2_2 (x0 x1 y0 y1 : float) : float * float :=
  let n0 := neg y0 in
  let n1 := neg y1 in
  let '(z0, z1) := add_2_2 x0 x1 n0 n1 in
  (z0, z1).

(* sub_2_1: add_2_1 (JMP17 Alg. 4) on -a. *)
Definition sub_2_1 (x0 x1 a : float) : float * float :=
  let n := neg a in
  let '(z0, z1) := add_2_1 x0 x1 n in
  (z0, z1).

(* sub_1_2: add_2_1 (JMP17 Alg. 4) on -y and a. *)
Definition sub_1_2 (a y0 y1 : float) : float * float :=
  let n0 := neg y0 in
  let n1 := neg y1 in
  let '(z0, z1) := add_2_1 n0 n1 a in
  (z0, z1).

(* mul_pow2_2: both limbs scaled, then Fast2Sum (Milestone 1 listing). *)
Definition mul_pow2_2 (x0 x1 c : float) : float * float :=
  let h := prod x0 c in
  let l := prod x1 c in
  let '(z0, z1) := fast_two_sum h l in
  (z0, z1).

(* The comparisons: limbs compared in order (Milestone 1 listing). *)
Definition lt_2_2 (x0 x1 y0 y1 : float) : bool :=
  let h := lt x0 y0 in
  let e := eq x0 y0 in
  let l := lt x1 y1 in
  let t := andb e l in
  let m := orb h t in
  m.

Definition le_2_2 (x0 x1 y0 y1 : float) : bool :=
  let h := lt x0 y0 in
  let e := eq x0 y0 in
  let l := le x1 y1 in
  let t := andb e l in
  let m := orb h t in
  m.

Definition eq_2_2 (x0 x1 y0 y1 : float) : bool :=
  let h := eq x0 y0 in
  let l := eq x1 y1 in
  let m := andb h l in
  m.

Definition lt_2_1 (x0 x1 a : float) : bool :=
  let h := lt x0 a in
  let e := eq x0 a in
  let l := lt x1 pzero in
  let t := andb e l in
  let m := orb h t in
  m.

Definition le_2_1 (x0 x1 a : float) : bool :=
  let h := lt x0 a in
  let e := eq x0 a in
  let l := le x1 pzero in
  let t := andb e l in
  let m := orb h t in
  m.

Definition eq_2_1 (x0 x1 a : float) : bool :=
  let h := eq x0 a in
  let l := eq x1 pzero in
  let m := andb h l in
  m.

Definition lt_1_2 (a y0 y1 : float) : bool :=
  let h := lt a y0 in
  let e := eq a y0 in
  let l := lt pzero y1 in
  let t := andb e l in
  let m := orb h t in
  m.

Definition le_1_2 (a y0 y1 : float) : bool :=
  let h := lt a y0 in
  let e := eq a y0 in
  let l := le pzero y1 in
  let t := andb e l in
  let m := orb h t in
  m.

(* The conversions to one limb (Milestone 1 listing). *)
Definition to_nearest_2 (x0 x1 : float) : float :=
  let t := x0 in
  t.

Definition to_down_2 (x0 x1 : float) : float :=
  let m := lt x1 pzero in
  let p := pred x0 in
  let t := if m then p else x0 in
  t.

Definition to_up_2 (x0 x1 : float) : float :=
  let m := lt pzero x1 in
  let s := succ x0 in
  let t := if m then s else x0 in
  t.

Definition abs_upper_2 (x0 x1 : float) : float :=
  let '(a0, a1) := abs_2 x0 x1 in
  let t := to_up_2 a0 a1 in
  t.

(* radd, rmul: one step up from the rounded sum, from the rounded product. *)
Definition radd (a b : float) : float :=
  let s := add a b in
  let r := succ s in
  r.

Definition rmul (a b : float) : float :=
  let p := prod a b in
  let r := succ p in
  r.

(* The Ball kernels, second radius design (BallDraft.v): center of one limb. *)
Definition ball_add_1 (cx rx cy ry : float) : float * float :=
  let cz := add cx cy in
  let az := abs cz in
  let s := add rx ry in
  let t := fma az radius_e_ball_add_1 s in
  let rz := fma t radius_g_ball_add_1 radius_h_ball_add_1 in
  (cz, rz).

Definition ball_sub_1 (cx rx cy ry : float) : float * float :=
  let n := neg cy in
  let '(cz, rz) := ball_add_1 cx rx n ry in
  (cz, rz).

Definition ball_mul_1 (cx rx cy ry : float) : float * float :=
  let cz := prod cx cy in
  let ax := abs cx in
  let ay := abs cy in
  let az := abs cz in
  let p := prod rx ry in
  let q := fma ay rx p in
  let w := fma ax ry q in
  let t := fma az radius_e_ball_mul_1 w in
  let rz := fma t radius_g_ball_mul_1 radius_h_ball_mul_1 in
  (cz, rz).

Definition ball_neg_1 (cx rx : float) : float * float :=
  let cz := neg cx in
  let rz := rx in
  (cz, rz).

Definition ball_scale_1 (cx rx a : float) : float * float :=
  let cz := prod cx a in
  let aa := abs a in
  let az := abs cz in
  let p := prod aa rx in
  let t := fma az radius_e_ball_scale_1 p in
  let rz := fma t radius_g_ball_scale_1 radius_h_ball_scale_1 in
  (cz, rz).

(* The Ball kernels: center of two limbs. *)
Definition ball_add_2 (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(cz0, cz1) := add_2_2 cx0 cx1 cy0 cy1 in
  let az := abs cz0 in
  let s := add rx ry in
  let t := fma az radius_e_ball_add_2 s in
  let rz := fma t radius_g_ball_add_2 radius_h_ball_add_2 in
  (cz0, cz1, rz).

Definition ball_sub_2 (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(n0, n1) := neg_2 cy0 cy1 in
  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx n0 n1 ry in
  (cz0, cz1, rz).

Definition ball_mul_2 (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(cz0, cz1) := mul_2_2 cx0 cx1 cy0 cy1 in
  let ax := abs cx0 in
  let ay := abs cy0 in
  let az := abs cz0 in
  let p := prod rx ry in
  let q := fma ay rx p in
  let w := fma ax ry q in
  let t := fma az radius_e_ball_mul_2 w in
  let rz := fma t radius_g_ball_mul_2 radius_h_ball_mul_2 in
  (cz0, cz1, rz).

Definition ball_neg_2 (cx0 cx1 rx : float) : float * float * float :=
  let '(cz0, cz1) := neg_2 cx0 cx1 in
  let rz := rx in
  (cz0, cz1, rz).

Definition ball_scale_2 (cx0 cx1 rx a : float) : float * float * float :=
  let '(cz0, cz1) := mul_2_1 cx0 cx1 a in
  let aa := abs a in
  let az := abs cz0 in
  let p := prod aa rx in
  let t := fma az radius_e_ball_scale_2 p in
  let rz := fma t radius_g_ball_scale_2 radius_h_ball_scale_2 in
  (cz0, cz1, rz).

(** * The full kernels *)

(* Each is its finite core followed by the fix-up of milestone1.md ("IEEE-like results"):
   t is the operation of T on the leading limbs; f says that z0 is finite; r0 is t made
   canonical: a NaN stays a NaN, any other t becomes the infinity of its sign (a zero t
   would become a NaN). A one-limb operand that is added or subtracted is guarded before
   it enters t; the core is called with the operand itself. *)

Definition add_2_2_full (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1) := add_2_2 x0 x1 y0 y1 in
  let t := add x0 y0 in
  let a := abs z0 in
  let f := lt a pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition add_fast_2_2_full (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1) := add_fast_2_2 x0 x1 y0 y1 in
  let t := add x0 y0 in
  let a := abs z0 in
  let f := lt a pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition sub_2_2_full (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1) := sub_2_2 x0 x1 y0 y1 in
  let t := sub x0 y0 in
  let a := abs z0 in
  let f := lt a pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition add_2_1_full (x0 x1 a : float) : float * float :=
  let g := guard a in
  let '(z0, z1) := add_2_1 x0 x1 a in
  let t := add x0 g in
  let az := abs z0 in
  let f := lt az pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition sub_2_1_full (x0 x1 a : float) : float * float :=
  let g := guard a in
  let '(z0, z1) := sub_2_1 x0 x1 a in
  let t := sub x0 g in
  let az := abs z0 in
  let f := lt az pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition sub_1_2_full (a y0 y1 : float) : float * float :=
  let g := guard a in
  let '(z0, z1) := sub_1_2 a y0 y1 in
  let t := sub g y0 in
  let az := abs z0 in
  let f := lt az pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition mul_2_2_full (x0 x1 y0 y1 : float) : float * float :=
  let '(z0, z1) := mul_2_2 x0 x1 y0 y1 in
  let t := prod x0 y0 in
  let a := abs z0 in
  let f := lt a pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition mul_2_1_full (x0 x1 a : float) : float * float :=
  let '(z0, z1) := mul_2_1 x0 x1 a in
  let t := prod x0 a in
  let az := abs z0 in
  let f := lt az pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

Definition mul_pow2_2_full (x0 x1 c : float) : float * float :=
  let '(z0, z1) := mul_pow2_2 x0 x1 c in
  let t := prod x0 c in
  let a := abs z0 in
  let f := lt a pinf in
  let r0 := prod t pinf in
  let n := eq r0 r0 in
  let r1 := if n then pzero else r0 in
  let w0 := if f then z0 else r0 in
  let w1 := if f then z1 else r1 in
  (w0, w1).

(* The full Ball kernels (milestone1.md, "Ball kernels"): q is a NaN exactly when an
   operand is the empty set; f says that the center and the radius of the core are
   finite; otherwise the result is the whole line. *)

Definition ball_add_1_full (cx rx cy ry : float) : float * float :=
  let '(cz, rz) := ball_add_1 cx rx cy ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else q in
  let rw := if e then r else q in
  (cw, rw).

Definition ball_sub_1_full (cx rx cy ry : float) : float * float :=
  let '(cz, rz) := ball_sub_1 cx rx cy ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else q in
  let rw := if e then r else q in
  (cw, rw).

Definition ball_mul_1_full (cx rx cy ry : float) : float * float :=
  let '(cz, rz) := ball_mul_1 cx rx cy ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else q in
  let rw := if e then r else q in
  (cw, rw).

Definition ball_scale_1_full (cx rx a : float) : float * float :=
  let '(cz, rz) := ball_scale_1 cx rx a in
  let e := eq rx rx in
  let az := abs cz in
  let f1 := lt az pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz else pzero in
  let r := if f then rz else pinf in
  let cw := if e then c0 else rx in
  let rw := if e then r else rx in
  (cw, rw).

Definition ball_add_2_full (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx cy0 cy1 ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz0 in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else q in
  let cw1 := if e then c1 else q in
  let rw := if e then r else q in
  (cw0, cw1, rw).

Definition ball_sub_2_full (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(cz0, cz1, rz) := ball_sub_2 cx0 cx1 rx cy0 cy1 ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz0 in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else q in
  let cw1 := if e then c1 else q in
  let rw := if e then r else q in
  (cw0, cw1, rw).

Definition ball_mul_2_full (cx0 cx1 rx cy0 cy1 ry : float) : float * float * float :=
  let '(cz0, cz1, rz) := ball_mul_2 cx0 cx1 rx cy0 cy1 ry in
  let q := add rx ry in
  let e := eq q q in
  let a := abs cz0 in
  let f1 := lt a pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else q in
  let cw1 := if e then c1 else q in
  let rw := if e then r else q in
  (cw0, cw1, rw).

Definition ball_scale_2_full (cx0 cx1 rx a : float) : float * float * float :=
  let '(cz0, cz1, rz) := ball_scale_2 cx0 cx1 rx a in
  let e := eq rx rx in
  let az := abs cz0 in
  let f1 := lt az pinf in
  let f2 := lt rz pinf in
  let f := andb f1 f2 in
  let c0 := if f then cz0 else pzero in
  let c1 := if f then cz1 else pzero in
  let r := if f then rz else pinf in
  let cw0 := if e then c0 else rx in
  let cw1 := if e then c1 else rx in
  let rw := if e then r else rx in
  (cw0, cw1, rw).

(** * The constructor kernels *)

(* milestone1.md, "Values that enter from the program". *)

Definition make_2 (a : float) : float * float :=
  let x0 := guard a in
  let n := eq x0 x0 in
  let x1 := if n then pzero else x0 in
  (x0, x1).

Definition make_2_limbs (h l : float) : float * float :=
  let x0 := guard h in
  let x1 := guard l in
  (x0, x1).

Definition ball_make_1 (c r : float) : float * float :=
  let h := guard c in
  let g := guard r in
  let e := le pzero g in
  let a := abs h in
  let f1 := lt a pinf in
  let f2 := lt g pinf in
  let f := andb f1 f2 in
  let k0 := if f then h else pzero in
  let s := if f then g else pinf in
  let cw := if e then k0 else cnan in
  let rw := if e then s else cnan in
  (cw, rw).

Definition ball_make_2 (c0 c1 r : float) : float * float * float :=
  let g := guard r in
  let e := le pzero g in
  let a := abs c0 in
  let f1 := lt a pinf in
  let f2 := lt g pinf in
  let f := andb f1 f2 in
  let k0 := if f then c0 else pzero in
  let k1 := if f then c1 else pzero in
  let s := if f then g else pinf in
  let cw0 := if e then k0 else cnan in
  let cw1 := if e then k1 else cnan in
  let rw := if e then s else cnan in
  (cw0, cw1, rw).

End IeeeKernels.

(** * The same kernels as straight-line programs *)

(* Positions: the inputs are numbered from 0 in the order of the kernel's arguments, and
   each instruction defines the next position. The comment of each line gives the
   position and the name of the value in the kernel description. *)

(* inputs: 0 a, 1 b *)
Definition fast_two_sum_prog : list instr :=
  [ Iadd 0 1     (*  2 s *)
  ; Isub 2 0     (*  3 z *)
  ; Isub 1 3     (*  4 e *)
  ].

(* inputs: 0 a, 1 b *)
Definition two_prod_prog : list instr :=
  [ Iprod 0 1    (*  2 p *)
  ; Ifms 0 1 2   (*  3 e *)
  ].

(* inputs: 0 a, 1 b *)
Definition two_sum_prog : list instr :=
  [ Iadd 0 1     (*  2 s *)
  ; Isub 2 0     (*  3 bb *)
  ; Isub 2 3     (*  4 t0 *)
  ; Isub 0 4     (*  5 t1 *)
  ; Isub 1 3     (*  6 t2 *)
  ; Iadd 5 6     (*  7 e *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition add_2_2_prog : list instr :=
  [ Iadd 0 2     (*  4 sh      two_sum(x0, y0) *)
  ; Isub 4 0     (*  5 bb *)
  ; Isub 4 5     (*  6 t0 *)
  ; Isub 0 6     (*  7 t1 *)
  ; Isub 2 5     (*  8 t2 *)
  ; Iadd 7 8     (*  9 sl *)
  ; Iadd 1 3     (* 10 th      two_sum(x1, y1) *)
  ; Isub 10 1    (* 11 bb *)
  ; Isub 10 11   (* 12 t0 *)
  ; Isub 1 12    (* 13 t1 *)
  ; Isub 3 11    (* 14 t2 *)
  ; Iadd 13 14   (* 15 tl *)
  ; Iadd 9 10    (* 16 c *)
  ; Iadd 4 16    (* 17 vh      fast_two_sum(sh, c) *)
  ; Isub 17 4    (* 18 z *)
  ; Isub 16 18   (* 19 vl *)
  ; Iadd 15 19   (* 20 w *)
  ; Iadd 17 20   (* 21 z0      fast_two_sum(vh, w) *)
  ; Isub 21 17   (* 22 z *)
  ; Isub 20 22   (* 23 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition mul_2_2_prog : list instr :=
  [ Iprod 0 2    (*  4 ch      two_prod(x0, y0) *)
  ; Ifms 0 2 4   (*  5 cl1 *)
  ; Iprod 1 3    (*  6 tl0 *)
  ; Ifma 0 3 6   (*  7 tl1 *)
  ; Ifma 1 2 7   (*  8 cl2 *)
  ; Iadd 5 8     (*  9 cl3 *)
  ; Iadd 4 9     (* 10 z0      fast_two_sum(ch, cl3) *)
  ; Isub 10 4    (* 11 z *)
  ; Isub 9 11    (* 12 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 a *)
Definition add_2_1_prog : list instr :=
  [ Iguard 2     (*  3 g *)
  ; Iadd 0 3     (*  4 sh      two_sum(x0, g) *)
  ; Isub 4 0     (*  5 bb *)
  ; Isub 4 5     (*  6 t0 *)
  ; Isub 0 6     (*  7 t1 *)
  ; Isub 3 5     (*  8 t2 *)
  ; Iadd 7 8     (*  9 sl *)
  ; Iadd 1 9     (* 10 v *)
  ; Iadd 4 10    (* 11 z0      fast_two_sum(sh, v) *)
  ; Isub 11 4    (* 12 z *)
  ; Isub 10 12   (* 13 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 a *)
Definition mul_2_1_prog : list instr :=
  [ Iprod 0 2    (*  3 ch      two_prod(x0, a) *)
  ; Ifms 0 2 3   (*  4 cl1 *)
  ; Ifma 1 2 4   (*  5 cl3 *)
  ; Iadd 3 5     (*  6 z0      fast_two_sum(ch, cl3) *)
  ; Isub 6 3     (*  7 z *)
  ; Isub 5 7     (*  8 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition add_fast_2_2_prog : list instr :=
  [ Iadd 0 2     (*  4 sh      two_sum(x0, y0) *)
  ; Isub 4 0     (*  5 bb *)
  ; Isub 4 5     (*  6 t0 *)
  ; Isub 0 6     (*  7 t1 *)
  ; Isub 2 5     (*  8 t2 *)
  ; Iadd 7 8     (*  9 sl *)
  ; Iadd 1 3     (* 10 v *)
  ; Iadd 9 10    (* 11 w *)
  ; Iadd 4 11    (* 12 z0      fast_two_sum(sh, w) *)
  ; Isub 12 4    (* 13 z *)
  ; Isub 11 13   (* 14 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 y0, 3 y1 *)
Definition sub_2_2_prog : list instr :=
  [ Ineg 2       (*  4 n0 *)
  ; Ineg 3       (*  5 n1 *)
  ; Iadd 0 4     (*  6 sh      add_2_2(x0, x1, n0, n1): two_sum(x0, n0) *)
  ; Isub 6 0     (*  7 bb *)
  ; Isub 6 7     (*  8 t0 *)
  ; Isub 0 8     (*  9 t1 *)
  ; Isub 4 7     (* 10 t2 *)
  ; Iadd 9 10    (* 11 sl *)
  ; Iadd 1 5     (* 12 th      two_sum(x1, n1) *)
  ; Isub 12 1    (* 13 bb *)
  ; Isub 12 13   (* 14 t0 *)
  ; Isub 1 14    (* 15 t1 *)
  ; Isub 5 13    (* 16 t2 *)
  ; Iadd 15 16   (* 17 tl *)
  ; Iadd 11 12   (* 18 c *)
  ; Iadd 6 18    (* 19 vh      fast_two_sum(sh, c) *)
  ; Isub 19 6    (* 20 z *)
  ; Isub 18 20   (* 21 vl *)
  ; Iadd 17 21   (* 22 w *)
  ; Iadd 19 22   (* 23 z0      fast_two_sum(vh, w) *)
  ; Isub 23 19   (* 24 z *)
  ; Isub 22 24   (* 25 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 a *)
Definition sub_2_1_prog : list instr :=
  [ Ineg 2       (*  3 n *)
  ; Iguard 3     (*  4 g       add_2_1(x0, x1, n) *)
  ; Iadd 0 4     (*  5 sh      two_sum(x0, g) *)
  ; Isub 5 0     (*  6 bb *)
  ; Isub 5 6     (*  7 t0 *)
  ; Isub 0 7     (*  8 t1 *)
  ; Isub 4 6     (*  9 t2 *)
  ; Iadd 8 9     (* 10 sl *)
  ; Iadd 1 10    (* 11 v *)
  ; Iadd 5 11    (* 12 z0      fast_two_sum(sh, v) *)
  ; Isub 12 5    (* 13 z *)
  ; Isub 11 13   (* 14 z1 *)
  ].

(* inputs: 0 a, 1 y0, 2 y1 *)
Definition sub_1_2_prog : list instr :=
  [ Ineg 1       (*  3 n0 *)
  ; Ineg 2       (*  4 n1 *)
  ; Iguard 0     (*  5 g       add_2_1(n0, n1, a) *)
  ; Iadd 3 5     (*  6 sh      two_sum(n0, g) *)
  ; Isub 6 3     (*  7 bb *)
  ; Isub 6 7     (*  8 t0 *)
  ; Isub 3 8     (*  9 t1 *)
  ; Isub 5 7     (* 10 t2 *)
  ; Iadd 9 10    (* 11 sl *)
  ; Iadd 4 11    (* 12 v *)
  ; Iadd 6 12    (* 13 z0      fast_two_sum(sh, v) *)
  ; Isub 13 6    (* 14 z *)
  ; Isub 12 14   (* 15 z1 *)
  ].

(* inputs: 0 x0, 1 x1, 2 c *)
Definition mul_pow2_2_prog : list instr :=
  [ Iprod 0 2    (*  3 h *)
  ; Iprod 1 2    (*  4 l *)
  ; Iadd 3 4     (*  5 z0      fast_two_sum(h, l) *)
  ; Isub 5 3     (*  6 z *)
  ; Isub 4 6     (*  7 z1 *)
  ].
