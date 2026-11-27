(* EXPERIMENTAL: a proof probe, not part of the library. The operations of the experimental
   two-limb interval rounded upward that its product rests on, transcribed by hand, operation for
   operation, from experiments/upward2/include/kairn/experimental/upward2.hpp (the line numbers
   below are those of that header at the commit of the experiment, 21f4ba41).

   The model is the one of the library's real-number proofs (proofs/theories/Format.v): the
   format FLT(emin, prec) of Flocq, precision prec, gradual underflow, smallest positive number
   eta = 2^emin, NO OVERFLOW (no largest number, no infinity, no NaN), and RU the rounding toward
   +infinity of that format, RU of proofs/gen/Statements.v, which is
   round radix2 (FLT_exp emin prec) Zceil. So the special values, the slow path mul_special, the
   test big(p) of the fast path and the signed zeros are outside the model; what is modelled is
   the fast path, on numbers of the format.

   Definitions and the header lines they transcribe:
   - add_up, sub_up, mul_up, fma_up: add, sub, mul, fmadd of a lane under the mode upward
     (lines 106-111 and the NUMBERS form, lines 211-214); neg: neg, exact (line 217);
   - vmax: vmax of the form NUMBERS, a > b ? a : b (line 216; the SSE form _mm_max_pd(a, b)
     returns the same number for operands that are not NaN, and NEON's vmaxq_f64 too, up to the
     sign of a zero, which the model does not have); eqb: eq (line 236); blend: blend (line 222);
     le0: le0 (line 234);
   - upper_pair, upper_normalized: the vocabulary of the brief (lines 14-19 of the header);
   - fast_two_sum: lines 331-334;
   - pair_mul: lines 366-372 (it returns p and the pair (zh, zl));
   - lexmax: lines 379-383;
   - the registers V (two lanes) and Rg (struct R, two registers h and l: lines 92-95), with
     lane0, lane1, swap, dup0, dup1, flip, mall, mlane1, mswap (lines 209-210, 219-221, 224,
     231, 241-242); pair_mul_v and lexmax_v: the same operations on the two lanes;
   - the case table kCases: lines 456-477; lanes: lines 500-506; mul_one: lines 491-497 (its
     fast path); mul_case: lines 507-518; mul_zero_zero: lines 480-489 (its fast path);
     mul_branch: lines 519-535.
   - hi, nlo, canonical, mem: the meaning of a register pair (lines 8-19): lane 0 of (H, L) is an
     upper pair (uh, ul) of the upper bound, lane 1 an upper pair (nh, nl) of the negated lower
     bound; the interval a pair of registers stands for is [-(nh + nl), uh + ul]. *)
From Stdlib Require Import Reals ZArith Bool.
From Flocq Require Import Core.
From Kairn.Gen Require Import Statements.
Open Scope R_scope.

(** * The operations of one lane *)

Definition add_up (emin prec : Z) (a b : R) : R := RU emin prec (a + b).
Definition sub_up (emin prec : Z) (a b : R) : R := RU emin prec (a - b).
Definition mul_up (emin prec : Z) (a b : R) : R := RU emin prec (a * b).
Definition fma_up (emin prec : Z) (a b c : R) : R := RU emin prec (a * b + c).
Definition neg (a : R) : R := - a.

Definition vmax (a b : R) : R := if Rlt_bool b a then a else b.
Definition eqb (a b : R) : bool := Req_bool a b.
Definition blend (m : bool) (a b : R) : R := if m then a else b.
Definition le0 (a : R) : bool := Rle_bool a 0.

(** * Upper pairs *)

(* (h, l) is an upper pair of v: h + l >= v. *)
Definition upper_pair (h l v : R) : Prop := v <= h + l.

(* (h, l) is upper-normalized: both are numbers of the format and h = RU(h + l). *)
Definition upper_normalized (emin prec : Z) (h l : R) : Prop :=
  fmt emin prec h /\ fmt emin prec l /\ RU emin prec (h + l) = h.

(** * The building blocks *)

(* fast_two_sum(a, b) -> (s, t): s = RU(a + b), t = RU(RU(a - s) + b). *)
Definition fast_two_sum (emin prec : Z) (a b : R) : R * R :=
  let s := add_up emin prec a b in
  let t := add_up emin prec (sub_up emin prec a s) b in
  (s, t).

(* pair_mul(P, Q) -> (p, (zh, zl)). *)
Definition pair_mul (emin prec : Z) (ph pl qh ql : R) : R * (R * R) :=
  let p := mul_up emin prec ph qh in
  let e := fma_up emin prec ph qh (neg p) in
  let c := fma_up emin prec ph ql (fma_up emin prec pl qh (mul_up emin prec pl ql)) in
  let w := add_up emin prec e c in
  (p, fast_two_sum emin prec p w).

(* lexmax(a, b) -> (mh, ml). *)
Definition lexmax (ah al bh bl : R) : R * R :=
  let mh := vmax ah bh in
  let ea := eqb mh ah in
  let eb := eqb mh bh in
  let ml := blend (ea && eb) (vmax al bl) (blend ea al bl) in
  (mh, ml).

(** * Registers of two lanes *)

Definition V : Type := (R * R)%type.
Definition M : Type := (bool * bool)%type.
(* struct R { V h, l; }: the heads and the second limbs. *)
Definition Rg : Type := (V * V)%type.

Definition lane0 (a : V) : R := fst a.
Definition lane1 (a : V) : R := snd a.
Definition swap (a : V) : V := (lane1 a, lane0 a).
Definition dup0 (a : V) : V := (lane0 a, lane0 a).
Definition dup1 (a : V) : V := (lane1 a, lane1 a).
Definition flip (m : M) (a : V) : V :=
  (if fst m then - lane0 a else lane0 a, if snd m then - lane1 a else lane1 a).
Definition mall : M := (true, true).
Definition mlane1 : M := (false, true).
Definition mswap (m : M) : M := (snd m, fst m).

Definition pair_mul_v (emin prec : Z) (ph pl qh ql : V) : V * (V * V) :=
  let r0 := pair_mul emin prec (lane0 ph) (lane0 pl) (lane0 qh) (lane0 ql) in
  let r1 := pair_mul emin prec (lane1 ph) (lane1 pl) (lane1 qh) (lane1 ql) in
  ((fst r0, fst r1), ((fst (snd r0), fst (snd r1)), (snd (snd r0), snd (snd r1)))).

Definition lexmax_v (ah al bh bl : V) : Rg :=
  let m0 := lexmax (lane0 ah) (lane0 al) (lane0 bh) (lane0 bl) in
  let m1 := lexmax (lane1 ah) (lane1 al) (lane1 bh) (lane1 bl) in
  ((fst m0, fst m1), (snd m0, snd m1)).

(** * The product, form "branch" (its fast path) *)

Record Case := mkCase { p0 : Z; p1 : Z; q0 : Z; q1 : Z; s0 : Z; s1 : Z }.

(* kCases[16], index xc + 4 yc. *)
Definition kCases (k : nat) : Case :=
  match k with
  | 0 => mkCase (-1) (-1) (-1) (-1) 0 0     (* x ∋ 0, y ∋ 0: two candidates *)
  | 1 => mkCase 1 1 1 0 0 0                 (* x <= 0, y ∋ 0 *)
  | 2 => mkCase 0 0 0 1 0 0                 (* x >= 0, y ∋ 0 *)
  | 3 => mkCase 0 0 0 1 0 0                 (* x = 0, y ∋ 0 (as x >= 0) *)
  | 4 => mkCase 1 0 1 1 0 0                 (* x ∋ 0, y <= 0 *)
  | 5 => mkCase 1 0 1 0 0 1                 (* x <= 0, y <= 0 *)
  | 6 => mkCase 1 0 0 1 1 0                 (* x >= 0, y <= 0 *)
  | 7 => mkCase 1 0 0 1 1 0                 (* x = 0, y <= 0 *)
  | 8 => mkCase 0 1 0 0 0 0                 (* x ∋ 0, y >= 0 *)
  | 9 => mkCase 0 1 1 0 1 0                 (* x <= 0, y >= 0 *)
  | 10 => mkCase 0 1 0 1 0 1                (* x >= 0, y >= 0 *)
  | 11 => mkCase 0 1 0 1 0 1                (* x = 0, y >= 0 *)
  | 12 => mkCase 0 1 0 0 0 0                (* x ∋ 0, y = 0 (as y >= 0) *)
  | 13 => mkCase 0 1 1 0 1 0                (* x <= 0, y = 0 *)
  | 14 => mkCase 0 1 0 1 0 1                (* x >= 0, y = 0 *)
  | _ => mkCase 0 1 0 1 0 1                 (* 15: x = 0, y = 0 *)
  end.

(* lanes<P0, P1>(a). *)
Definition lanes (P0 P1 : Z) (a : V) : V :=
  if (Z.eqb P0 0 && Z.eqb P1 1)%bool then a
  else if (Z.eqb P0 1 && Z.eqb P1 0)%bool then swap a
  else if Z.eqb P0 0 then dup0 a
  else dup1 a.

(* mul_one(p, q, x, y), its fast path: the pair (zh, zl) of pair_mul. In the model nothing
   overflows, so the test big(pr) that leads to mul_special is never taken. *)
Definition mul_one (emin prec : Z) (p q : Rg) : Rg :=
  snd (pair_mul_v emin prec (fst p) (snd p) (fst q) (snd q)).

(* The integer flags of a Case read as C++ conditions: nonzero is true. *)
Definition nz (k : Z) : bool := negb (Z.eqb k 0).

(* mul_case<K>(x, y). *)
Definition mul_case (emin prec : Z) (k : nat) (x y : Rg) : Rg :=
  let c := kCases k in
  let p : Rg := (lanes (p0 c) (p1 c) (fst x), lanes (p0 c) (p1 c) (snd x)) in
  let q : Rg := (lanes (q0 c) (q1 c) (fst y), lanes (q0 c) (q1 c) (snd y)) in
  let q : Rg :=
    if (nz (s0 c) || nz (s1 c))%bool then
      let s := if (nz (s0 c) && nz (s1 c))%bool then mall
               else if nz (s1 c) then mlane1 else mswap mlane1 in
      (flip s (fst q), flip s (snd q))
    else q in
  mul_one emin prec p q.

(* mul_zero_zero(x, y), its fast path. *)
Definition mul_zero_zero (emin prec : Z) (x y : Rg) : Rg :=
  let a := pair_mul_v emin prec (dup1 (fst x)) (dup1 (snd x)) (swap (fst y)) (swap (snd y)) in
  let b := pair_mul_v emin prec (dup0 (fst x)) (dup0 (snd x)) (fst y) (snd y) in
  lexmax_v (fst (snd a)) (snd (snd a)) (fst (snd b)) (snd (snd b)).

(* mul_branch(x, y). *)
Definition mul_branch (emin prec : Z) (x y : Rg) : Rg :=
  let xn := le0 (lane0 (fst x)) in   (* b <= 0 *)
  let xp := le0 (lane1 (fst x)) in   (* a >= 0 *)
  let yn := le0 (lane0 (fst y)) in   (* d <= 0 *)
  let yp := le0 (lane1 (fst y)) in   (* c >= 0 *)
  if xp then
    (if yp then mul_case emin prec 10 x y
     else if yn then mul_case emin prec 6 x y
     else mul_case emin prec 2 x y)
  else if xn then
    (if yp then mul_case emin prec 9 x y
     else if yn then mul_case emin prec 5 x y
     else mul_case emin prec 1 x y)
  else if yp then mul_case emin prec 8 x y
  else if yn then mul_case emin prec 4 x y
  else mul_zero_zero emin prec x y.

(** * What a pair of registers stands for *)

(* The value of the upper pair of the upper bound, uh + ul, and of the negated lower bound,
   nh + nl. *)
Definition hi (x : Rg) : R := lane0 (fst x) + lane0 (snd x).
Definition nlo (x : Rg) : R := lane1 (fst x) + lane1 (snd x).

(* The invariant of the type in the model: both lanes upper-normalized. *)
Definition canonical (emin prec : Z) (x : Rg) : Prop :=
  upper_normalized emin prec (lane0 (fst x)) (lane0 (snd x)) /\
  upper_normalized emin prec (lane1 (fst x)) (lane1 (snd x)).

(* t is in the interval [-(nh + nl), uh + ul]. *)
Definition mem (x : Rg) (t : R) : Prop := - nlo x <= t <= hi x.
