(* DRAFT of the Ball cores of the second radius design: their real model and their
   statements, written by hand in the form the generator is meant to print (as
   proofs/gen/Model.v and proofs/gen/Statements.v do for the kernels it knows). Nothing
   in this file is a proof; the theorems are in Ball2.v.

   The kernels of the same names in proofs/gen/Model.v are those of the first design, in
   which every step of the radius is a rounded operation followed by a step to the next
   number up. They stay there, with their theorems (Ball.v), until the generator
   switches. Refer to the definitions of this file by their qualified names
   (BallDraft.ball_add_2).

   The second design (docs/developer/design/milestone1.md, "The radius, second design").
   The center is computed as before. The radius is evaluated with ordinary operations
   rounded to nearest, and inflated once at the end:

     ball_add_k(cx, rx, cy, ry) -> (cz, rz)        ball_mul_k(cx, rx, cy, ry) -> (cz, rz)
       cz = add(cx, cy)                              cz = mul(cx, cy)
       az = abs(cz0)                                 ax = abs(cx0)
       s  = add(rx, ry)                              ay = abs(cy0)
       t  = fma(az, const E, s)                      az = abs(cz0)
       rz = fma(t, const G, const H)                 p  = prod(rx, ry)
                                                     q  = fma(ay, rx, p)
     ball_scale_k(cx, rx, a) -> (cz, rz)             w  = fma(ax, ry, q)
       cz = mul(cx, a)                               t  = fma(az, const E, w)
       aa = abs(a)                                   rz = fma(t, const G, const H)
       az = abs(cz0)
       p  = prod(aa, rx)                           ball_sub_k: neg, then ball_add_k
       t  = fma(az, const E, p)
       rz = fma(t, const G, const H)

   cz0 is the leading limb of the center (the center itself for k = 1). For k = 1 the
   center is one operation of T; for k = 2 it is add_2_2, mul_2_2 or mul_2_1.

   The constants. Write u = 2^-prec, eta = 2^emin, and for the kernel K of the center:
   rel and tiny, the two parts of its proved bound |cz - v| <= rel |v| + tiny (from K's
   claims, written out below as in Model.v), Uq = rel / (1 - rel), Vq = tiny / (1 - rel).
   Each constant is an exact expression rounded up to the format (RU):

     kernel         E                    G                  H
     ball_add_1     RU (Uq)              RU ((1+u)^3)       RU ((1+u) ((1+u)^2 eta + eta/2))
     ball_add_2     RU (Uq (1+u))        RU ((1+u)^3)       RU ((1+u) ((1+u)^2 eta + eta/2))
     ball_scale_1   RU (Uq)              RU ((1+u)^3)       RU ((1+u) ((1+u)^2 eta + Vq + eta/2))
     ball_scale_2   RU (Uq (1+u))        RU ((1+u)^3)       RU ((1+u) ((1+u)^2 eta + Vq + eta/2))
     ball_mul_1     RU (Uq)              RU ((1+u)^5)       RU ((1+u) (2 (1+u)^4 eta + Vq + eta/2))
     ball_mul_2     RU (Uq)              RU ((1+u)^6)       RU ((1+u) (2 (1+u)^5 eta + Vq + eta/2))

   with K = add_1_1 (rel = u / (1 + u)), add_2_2 (rel = 3 u^2 / (1 - 4 u)), mul_1_1
   (rel = u / (1 + u), tiny = eta / 2), mul_2_1 (rel = 2 u^2, tiny = eta), mul_2_2
   (rel = 4 u^2, tiny = 3/2 eta). The proofs use of a constant only that it is a number
   of the format, nonnegative, and at least the expression it rounds. Why these
   expressions are enough is explained in Ball2.v.

   The statements have the shape of the generated ones: the radius is a number of the
   format, the center is one (normalized for k = 2), and for all real x, y in the
   operand balls, x o y is in the result ball. They are for every eta and every
   precision from the minimum of the center's kernel on: 1 for a center of one limb, 3
   for ball_add_2 and ball_sub_2, 4 for ball_mul_2, 2 for ball_scale_2. *)
From Stdlib Require Import Reals ZArith.
From Flocq Require Import Core.
From Kairn.Gen Require Import Model Statements.
Open Scope R_scope.

Section Kernels.
Variable emin prec : Z.
Variable choice : Z -> bool.
Notation rnd := (round radix2 (FLT_exp emin prec) (Znearest choice)).

(** * The constants *)

(* radius_e(ball_add_1): Uq, rounded up, for the bound rel |v| of add_1_1. *)
Definition radius_e_ball_add_1 : R :=
  let rel := (1 / (1 + bpow radix2 (- prec))) * bpow radix2 (- prec) ^ 1 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel)).

(* radius_g(ball_add_1): (1 + u)^3, rounded up. *)
Definition radius_g_ball_add_1 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 3).

(* radius_h(ball_add_1): (1 + u) ((1 + u)^2 eta + eta / 2), rounded up. *)
Definition radius_h_ball_add_1 : R :=
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * ((1 + bpow radix2 (- prec)) ^ 2 * bpow radix2 emin + bpow radix2 emin / 2)).

(* radius_e(ball_add_2): Uq (1 + u), rounded up, for the bound rel |v| of add_2_2. *)
Definition radius_e_ball_add_2 : R :=
  let rel := (3 / (1 - (4 * bpow radix2 (- prec)))) * bpow radix2 (- prec) ^ 2 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel) * (1 + bpow radix2 (- prec))).

(* radius_g(ball_add_2): (1 + u)^3, rounded up. *)
Definition radius_g_ball_add_2 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 3).

(* radius_h(ball_add_2): (1 + u) ((1 + u)^2 eta + eta / 2), rounded up. *)
Definition radius_h_ball_add_2 : R :=
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * ((1 + bpow radix2 (- prec)) ^ 2 * bpow radix2 emin + bpow radix2 emin / 2)).

(* radius_e(ball_scale_1): Uq, rounded up, for the bound rel |v| + tiny of mul_1_1. *)
Definition radius_e_ball_scale_1 : R :=
  let rel := (1 / (1 + bpow radix2 (- prec))) * bpow radix2 (- prec) ^ 1 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel)).

(* radius_g(ball_scale_1): (1 + u)^3, rounded up. *)
Definition radius_g_ball_scale_1 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 3).

(* radius_h(ball_scale_1): (1 + u) ((1 + u)^2 eta + Vq + eta / 2), rounded up. *)
Definition radius_h_ball_scale_1 : R :=
  let rel := (1 / (1 + bpow radix2 (- prec))) * bpow radix2 (- prec) ^ 1 in
  let tiny := (1 / 2) * bpow radix2 emin in
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * ((1 + bpow radix2 (- prec)) ^ 2 * bpow radix2 emin + tiny / (1 - rel)
        + bpow radix2 emin / 2)).

(* radius_e(ball_scale_2): Uq (1 + u), rounded up, for the bound rel |v| + tiny of mul_2_1. *)
Definition radius_e_ball_scale_2 : R :=
  let rel := 2 * bpow radix2 (- prec) ^ 2 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel) * (1 + bpow radix2 (- prec))).

(* radius_g(ball_scale_2): (1 + u)^3, rounded up. *)
Definition radius_g_ball_scale_2 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 3).

(* radius_h(ball_scale_2): (1 + u) ((1 + u)^2 eta + Vq + eta / 2), rounded up. *)
Definition radius_h_ball_scale_2 : R :=
  let rel := 2 * bpow radix2 (- prec) ^ 2 in
  let tiny := 1 * bpow radix2 emin in
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * ((1 + bpow radix2 (- prec)) ^ 2 * bpow radix2 emin + tiny / (1 - rel)
        + bpow radix2 emin / 2)).

(* radius_e(ball_mul_1): Uq, rounded up, for the bound rel |v| + tiny of mul_1_1. *)
Definition radius_e_ball_mul_1 : R :=
  let rel := (1 / (1 + bpow radix2 (- prec))) * bpow radix2 (- prec) ^ 1 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel)).

(* radius_g(ball_mul_1): (1 + u)^5, rounded up. *)
Definition radius_g_ball_mul_1 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 5).

(* radius_h(ball_mul_1): (1 + u) (2 (1 + u)^4 eta + Vq + eta / 2), rounded up. *)
Definition radius_h_ball_mul_1 : R :=
  let rel := (1 / (1 + bpow radix2 (- prec))) * bpow radix2 (- prec) ^ 1 in
  let tiny := (1 / 2) * bpow radix2 emin in
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * (2 * (1 + bpow radix2 (- prec)) ^ 4 * bpow radix2 emin + tiny / (1 - rel)
        + bpow radix2 emin / 2)).

(* radius_e(ball_mul_2): Uq, rounded up, for the bound rel |v| + tiny of mul_2_2. *)
Definition radius_e_ball_mul_2 : R :=
  let rel := 4 * bpow radix2 (- prec) ^ 2 in
  round radix2 (FLT_exp emin prec) Zceil (rel / (1 - rel)).

(* radius_g(ball_mul_2): (1 + u)^6, rounded up. *)
Definition radius_g_ball_mul_2 : R :=
  round radix2 (FLT_exp emin prec) Zceil ((1 + bpow radix2 (- prec)) ^ 6).

(* radius_h(ball_mul_2): (1 + u) (2 (1 + u)^5 eta + Vq + eta / 2), rounded up. *)
Definition radius_h_ball_mul_2 : R :=
  let rel := 4 * bpow radix2 (- prec) ^ 2 in
  let tiny := (3 / 2) * bpow radix2 emin in
  round radix2 (FLT_exp emin prec) Zceil
    ((1 + bpow radix2 (- prec))
     * (2 * (1 + bpow radix2 (- prec)) ^ 5 * bpow radix2 emin + tiny / (1 - rel)
        + bpow radix2 emin / 2)).

(** * The kernels *)

(* ball_add_1: midpoint-radius sum, radius rounded to nearest and inflated once. *)
Definition ball_add_1 (cx rx cy ry : R) : R * R :=
  let cz := rnd (cx + cy) in
  let az := Rabs cz in
  let s := rnd (rx + ry) in
  let t := rnd (az * radius_e_ball_add_1 + s) in
  let rz := rnd (t * radius_g_ball_add_1 + radius_h_ball_add_1) in
  (cz, rz).

(* ball_sub_1: ball_add_1 with the second center negated. *)
Definition ball_sub_1 (cx rx cy ry : R) : R * R :=
  let n := - cy in
  let '(cz, rz) := ball_add_1 cx rx n ry in
  (cz, rz).

(* ball_mul_1: midpoint-radius product. *)
Definition ball_mul_1 (cx rx cy ry : R) : R * R :=
  let cz := rnd (cx * cy + 0) in
  let ax := Rabs cx in
  let ay := Rabs cy in
  let az := Rabs cz in
  let p := rnd (rx * ry + 0) in
  let q := rnd (ay * rx + p) in
  let w := rnd (ax * ry + q) in
  let t := rnd (az * radius_e_ball_mul_1 + w) in
  let rz := rnd (t * radius_g_ball_mul_1 + radius_h_ball_mul_1) in
  (cz, rz).

(* ball_scale_1: midpoint-radius scaling by a number of the format. *)
Definition ball_scale_1 (cx rx a : R) : R * R :=
  let cz := rnd (cx * a + 0) in
  let aa := Rabs a in
  let az := Rabs cz in
  let p := rnd (aa * rx + 0) in
  let t := rnd (az * radius_e_ball_scale_1 + p) in
  let rz := rnd (t * radius_g_ball_scale_1 + radius_h_ball_scale_1) in
  (cz, rz).

(* ball_add_2: the center by add_2_2. *)
Definition ball_add_2 (cx0 cx1 rx cy0 cy1 ry : R) : R * R * R :=
  let '(cz0, cz1) := add_2_2 emin prec choice cx0 cx1 cy0 cy1 in
  let az := Rabs cz0 in
  let s := rnd (rx + ry) in
  let t := rnd (az * radius_e_ball_add_2 + s) in
  let rz := rnd (t * radius_g_ball_add_2 + radius_h_ball_add_2) in
  (cz0, cz1, rz).

(* ball_sub_2: ball_add_2 with the second center negated. *)
Definition ball_sub_2 (cx0 cx1 rx cy0 cy1 ry : R) : R * R * R :=
  let '(n0, n1) := neg_2 cy0 cy1 in
  let '(cz0, cz1, rz) := ball_add_2 cx0 cx1 rx n0 n1 ry in
  (cz0, cz1, rz).

(* ball_mul_2: the center by mul_2_2. *)
Definition ball_mul_2 (cx0 cx1 rx cy0 cy1 ry : R) : R * R * R :=
  let '(cz0, cz1) := mul_2_2 emin prec choice cx0 cx1 cy0 cy1 in
  let ax := Rabs cx0 in
  let ay := Rabs cy0 in
  let az := Rabs cz0 in
  let p := rnd (rx * ry + 0) in
  let q := rnd (ay * rx + p) in
  let w := rnd (ax * ry + q) in
  let t := rnd (az * radius_e_ball_mul_2 + w) in
  let rz := rnd (t * radius_g_ball_mul_2 + radius_h_ball_mul_2) in
  (cz0, cz1, rz).

(* ball_scale_2: the center by mul_2_1. *)
Definition ball_scale_2 (cx0 cx1 rx a : R) : R * R * R :=
  let '(cz0, cz1) := mul_2_1 emin prec choice cx0 cx1 a in
  let aa := Rabs a in
  let az := Rabs cz0 in
  let p := rnd (aa * rx + 0) in
  let t := rnd (az * radius_e_ball_scale_2 + p) in
  let rz := rnd (t * radius_g_ball_scale_2 + radius_h_ball_scale_2) in
  (cz0, cz1, rz).

End Kernels.

(** * The statements *)

Definition ball_add_1_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall cx rx cy ry : R,
  fmt emin prec cx ->
  fmt emin prec rx ->
  fmt emin prec cy ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz, rz) := ball_add_1 emin prec tie_even cx rx cy ry in
  fmt emin prec cz /\
  fmt emin prec rz /\
  (forall x y : R, Rabs (x - cx) <= rx -> Rabs (y - cy) <= ry -> Rabs ((x + y) - cz) <= rz).

Definition ball_sub_1_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall cx rx cy ry : R,
  fmt emin prec cx ->
  fmt emin prec rx ->
  fmt emin prec cy ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz, rz) := ball_sub_1 emin prec tie_even cx rx cy ry in
  fmt emin prec cz /\
  fmt emin prec rz /\
  (forall x y : R, Rabs (x - cx) <= rx -> Rabs (y - cy) <= ry -> Rabs ((x - y) - cz) <= rz).

Definition ball_mul_1_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall cx rx cy ry : R,
  fmt emin prec cx ->
  fmt emin prec rx ->
  fmt emin prec cy ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz, rz) := ball_mul_1 emin prec tie_even cx rx cy ry in
  fmt emin prec cz /\
  fmt emin prec rz /\
  (forall x y : R, Rabs (x - cx) <= rx -> Rabs (y - cy) <= ry -> Rabs ((x * y) - cz) <= rz).

Definition ball_scale_1_spec : Prop :=
  forall emin prec : Z, (1 <= prec)%Z ->
  forall cx rx a : R,
  fmt emin prec cx ->
  fmt emin prec rx ->
  fmt emin prec a ->
  0 <= rx ->
  let '(cz, rz) := ball_scale_1 emin prec tie_even cx rx a in
  fmt emin prec cz /\
  fmt emin prec rz /\
  (forall x : R, Rabs (x - cx) <= rx -> Rabs ((x * a) - cz) <= rz).

Definition ball_add_2_spec : Prop :=
  forall emin prec : Z, (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : R,
  normalized_2 emin prec cx0 cx1 ->
  fmt emin prec rx ->
  normalized_2 emin prec cy0 cy1 ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz0, cz1, rz) := ball_add_2 emin prec tie_even cx0 cx1 rx cy0 cy1 ry in
  fmt emin prec rz /\
  normalized_2 emin prec cz0 cz1 /\
  (forall x y : R, Rabs (x - (cx0 + cx1)) <= rx -> Rabs (y - (cy0 + cy1)) <= ry -> Rabs ((x + y) - (cz0 + cz1)) <= rz).

Definition ball_sub_2_spec : Prop :=
  forall emin prec : Z, (3 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : R,
  normalized_2 emin prec cx0 cx1 ->
  fmt emin prec rx ->
  normalized_2 emin prec cy0 cy1 ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz0, cz1, rz) := ball_sub_2 emin prec tie_even cx0 cx1 rx cy0 cy1 ry in
  fmt emin prec rz /\
  normalized_2 emin prec cz0 cz1 /\
  (forall x y : R, Rabs (x - (cx0 + cx1)) <= rx -> Rabs (y - (cy0 + cy1)) <= ry -> Rabs ((x - y) - (cz0 + cz1)) <= rz).

Definition ball_mul_2_spec : Prop :=
  forall emin prec : Z, (4 <= prec)%Z ->
  forall cx0 cx1 rx cy0 cy1 ry : R,
  normalized_2 emin prec cx0 cx1 ->
  fmt emin prec rx ->
  normalized_2 emin prec cy0 cy1 ->
  fmt emin prec ry ->
  0 <= rx ->
  0 <= ry ->
  let '(cz0, cz1, rz) := ball_mul_2 emin prec tie_even cx0 cx1 rx cy0 cy1 ry in
  fmt emin prec rz /\
  normalized_2 emin prec cz0 cz1 /\
  (forall x y : R, Rabs (x - (cx0 + cx1)) <= rx -> Rabs (y - (cy0 + cy1)) <= ry -> Rabs ((x * y) - (cz0 + cz1)) <= rz).

Definition ball_scale_2_spec : Prop :=
  forall emin prec : Z, (2 <= prec)%Z ->
  forall cx0 cx1 rx a : R,
  normalized_2 emin prec cx0 cx1 ->
  fmt emin prec rx ->
  fmt emin prec a ->
  0 <= rx ->
  let '(cz0, cz1, rz) := ball_scale_2 emin prec tie_even cx0 cx1 rx a in
  fmt emin prec rz /\
  normalized_2 emin prec cz0 cz1 /\
  (forall x : R, Rabs (x - (cx0 + cx1)) <= rx -> Rabs ((x * a) - (cz0 + cz1)) <= rz).
