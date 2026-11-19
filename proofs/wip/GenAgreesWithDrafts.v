(* NOT PART OF THE BUILD: make -C proofs agree. The generated files say what the drafts say:
   every definition and statement of proofs/theories/BallDraft.v, IeeeDraft.v,
   IeeeStatementsDraft.v and IeeeExtStatementsDraft.v that the generator prints is equal to the
   generated one by eq_refl, that is, by conversion alone. Definitions are compared as
   functions (with @, every argument abstracted), so no kernel is ever applied to values here.
   The constants of the drafts are named radius_e_K, radius_g_K, radius_h_K; the generated ones
   up_K_i, after the first kernel that uses them. A difference is stated with Fail, which
   checks that the equality does not hold, and explained beside it. *)
From Stdlib Require Import Reals ZArith List.
From Flocq Require Import Core Binary.
From Kairn.Gen Require Model Statements IeeeModel IeeeStatements.
From Kairn Require BallDraft IeeeDraft IeeeStatementsDraft IeeeExtStatementsDraft.

(** * The real model of the Ball cores (BallDraft.v) *)

Definition real_radius_e_ball_add_1_agrees : @Model.up_ball_add_1_0 = @BallDraft.radius_e_ball_add_1 := eq_refl.
Definition real_radius_g_ball_add_1_agrees : @Model.up_ball_add_1_1 = @BallDraft.radius_g_ball_add_1 := eq_refl.
Definition real_radius_h_ball_add_1_agrees : @Model.up_ball_add_1_2 = @BallDraft.radius_h_ball_add_1 := eq_refl.
Definition real_radius_e_ball_add_2_agrees : @Model.up_ball_add_2_0 = @BallDraft.radius_e_ball_add_2 := eq_refl.
Definition real_radius_g_ball_add_2_agrees : @Model.up_ball_add_1_1 = @BallDraft.radius_g_ball_add_2 := eq_refl.
Definition real_radius_h_ball_add_2_agrees : @Model.up_ball_add_1_2 = @BallDraft.radius_h_ball_add_2 := eq_refl.
Definition real_radius_e_ball_scale_1_agrees : @Model.up_ball_mul_1_0 = @BallDraft.radius_e_ball_scale_1 := eq_refl.
Definition real_radius_g_ball_scale_1_agrees : @Model.up_ball_add_1_1 = @BallDraft.radius_g_ball_scale_1 := eq_refl.
Definition real_radius_h_ball_scale_1_agrees : @Model.up_ball_scale_1_2 = @BallDraft.radius_h_ball_scale_1 := eq_refl.
Definition real_radius_e_ball_scale_2_agrees : @Model.up_ball_scale_2_0 = @BallDraft.radius_e_ball_scale_2 := eq_refl.
Definition real_radius_g_ball_scale_2_agrees : @Model.up_ball_add_1_1 = @BallDraft.radius_g_ball_scale_2 := eq_refl.
Definition real_radius_h_ball_scale_2_agrees : @Model.up_ball_scale_2_2 = @BallDraft.radius_h_ball_scale_2 := eq_refl.
Definition real_radius_e_ball_mul_1_agrees : @Model.up_ball_mul_1_0 = @BallDraft.radius_e_ball_mul_1 := eq_refl.
Definition real_radius_g_ball_mul_1_agrees : @Model.up_ball_mul_1_1 = @BallDraft.radius_g_ball_mul_1 := eq_refl.
Definition real_radius_h_ball_mul_1_agrees : @Model.up_ball_mul_1_2 = @BallDraft.radius_h_ball_mul_1 := eq_refl.
Definition real_radius_e_ball_mul_2_agrees : @Model.up_ball_mul_2_0 = @BallDraft.radius_e_ball_mul_2 := eq_refl.
Definition real_radius_g_ball_mul_2_agrees : @Model.up_ball_mul_2_1 = @BallDraft.radius_g_ball_mul_2 := eq_refl.
Definition real_radius_h_ball_mul_2_agrees : @Model.up_ball_mul_2_2 = @BallDraft.radius_h_ball_mul_2 := eq_refl.
Definition real_ball_add_1_agrees : @Model.ball_add_1 = @BallDraft.ball_add_1 := eq_refl.
Definition real_ball_sub_1_agrees : @Model.ball_sub_1 = @BallDraft.ball_sub_1 := eq_refl.
Definition real_ball_mul_1_agrees : @Model.ball_mul_1 = @BallDraft.ball_mul_1 := eq_refl.
Definition real_ball_scale_1_agrees : @Model.ball_scale_1 = @BallDraft.ball_scale_1 := eq_refl.
Definition real_ball_add_2_agrees : @Model.ball_add_2 = @BallDraft.ball_add_2 := eq_refl.
Definition real_ball_sub_2_agrees : @Model.ball_sub_2 = @BallDraft.ball_sub_2 := eq_refl.
Definition real_ball_mul_2_agrees : @Model.ball_mul_2 = @BallDraft.ball_mul_2 := eq_refl.
Definition real_ball_scale_2_agrees : @Model.ball_scale_2 = @BallDraft.ball_scale_2 := eq_refl.
Definition real_ball_add_1_spec_agrees : Statements.ball_add_1_spec = BallDraft.ball_add_1_spec := eq_refl.
Definition real_ball_sub_1_spec_agrees : Statements.ball_sub_1_spec = BallDraft.ball_sub_1_spec := eq_refl.
Definition real_ball_mul_1_spec_agrees : Statements.ball_mul_1_spec = BallDraft.ball_mul_1_spec := eq_refl.
Definition real_ball_scale_1_spec_agrees : Statements.ball_scale_1_spec = BallDraft.ball_scale_1_spec := eq_refl.
Definition real_ball_add_2_spec_agrees : Statements.ball_add_2_spec = BallDraft.ball_add_2_spec := eq_refl.
Definition real_ball_sub_2_spec_agrees : Statements.ball_sub_2_spec = BallDraft.ball_sub_2_spec := eq_refl.
Definition real_ball_mul_2_spec_agrees : Statements.ball_mul_2_spec = BallDraft.ball_mul_2_spec := eq_refl.
Definition real_ball_scale_2_spec_agrees : Statements.ball_scale_2_spec = BallDraft.ball_scale_2_spec := eq_refl.

(** * The IEEE model (IeeeDraft.v): constants, kernels, programs *)

Definition ieee_radius_e_ball_add_1_agrees : @IeeeModel.up_ball_add_1_0 = @IeeeDraft.radius_e_ball_add_1 := eq_refl.
Definition ieee_radius_g_ball_add_1_agrees : @IeeeModel.up_ball_add_1_1 = @IeeeDraft.radius_g_ball_add_1 := eq_refl.
Definition ieee_radius_h_ball_add_1_agrees : @IeeeModel.up_ball_add_1_2 = @IeeeDraft.radius_h_ball_add_1 := eq_refl.
Definition ieee_radius_e_ball_add_2_agrees : @IeeeModel.up_ball_add_2_0 = @IeeeDraft.radius_e_ball_add_2 := eq_refl.
Definition ieee_radius_g_ball_add_2_agrees : @IeeeModel.up_ball_add_1_1 = @IeeeDraft.radius_g_ball_add_2 := eq_refl.
Definition ieee_radius_h_ball_add_2_agrees : @IeeeModel.up_ball_add_1_2 = @IeeeDraft.radius_h_ball_add_2 := eq_refl.
Definition ieee_radius_e_ball_scale_1_agrees : @IeeeModel.up_ball_mul_1_0 = @IeeeDraft.radius_e_ball_scale_1 := eq_refl.
Definition ieee_radius_g_ball_scale_1_agrees : @IeeeModel.up_ball_add_1_1 = @IeeeDraft.radius_g_ball_scale_1 := eq_refl.
Definition ieee_radius_h_ball_scale_1_agrees : @IeeeModel.up_ball_scale_1_2 = @IeeeDraft.radius_h_ball_scale_1 := eq_refl.
Definition ieee_radius_e_ball_scale_2_agrees : @IeeeModel.up_ball_scale_2_0 = @IeeeDraft.radius_e_ball_scale_2 := eq_refl.
Definition ieee_radius_g_ball_scale_2_agrees : @IeeeModel.up_ball_add_1_1 = @IeeeDraft.radius_g_ball_scale_2 := eq_refl.
Definition ieee_radius_h_ball_scale_2_agrees : @IeeeModel.up_ball_scale_2_2 = @IeeeDraft.radius_h_ball_scale_2 := eq_refl.
Definition ieee_radius_e_ball_mul_1_agrees : @IeeeModel.up_ball_mul_1_0 = @IeeeDraft.radius_e_ball_mul_1 := eq_refl.
Definition ieee_radius_g_ball_mul_1_agrees : @IeeeModel.up_ball_mul_1_1 = @IeeeDraft.radius_g_ball_mul_1 := eq_refl.
Definition ieee_radius_h_ball_mul_1_agrees : @IeeeModel.up_ball_mul_1_2 = @IeeeDraft.radius_h_ball_mul_1 := eq_refl.
Definition ieee_radius_e_ball_mul_2_agrees : @IeeeModel.up_ball_mul_2_0 = @IeeeDraft.radius_e_ball_mul_2 := eq_refl.
Definition ieee_radius_g_ball_mul_2_agrees : @IeeeModel.up_ball_mul_2_1 = @IeeeDraft.radius_g_ball_mul_2 := eq_refl.
Definition ieee_radius_h_ball_mul_2_agrees : @IeeeModel.up_ball_mul_2_2 = @IeeeDraft.radius_h_ball_mul_2 := eq_refl.
Definition ieee_fast_two_sum_agrees : @IeeeModel.fast_two_sum = @IeeeDraft.fast_two_sum := eq_refl.
Definition ieee_two_prod_agrees : @IeeeModel.two_prod = @IeeeDraft.two_prod := eq_refl.
Definition ieee_two_sum_agrees : @IeeeModel.two_sum = @IeeeDraft.two_sum := eq_refl.
Definition ieee_add_2_2_agrees : @IeeeModel.add_2_2 = @IeeeDraft.add_2_2 := eq_refl.
Definition ieee_mul_2_2_agrees : @IeeeModel.mul_2_2 = @IeeeDraft.mul_2_2 := eq_refl.
Definition ieee_add_2_1_agrees : @IeeeModel.add_2_1 = @IeeeDraft.add_2_1 := eq_refl.
Definition ieee_mul_2_1_agrees : @IeeeModel.mul_2_1 = @IeeeDraft.mul_2_1 := eq_refl.
Definition ieee_add_fast_2_2_agrees : @IeeeModel.add_fast_2_2 = @IeeeDraft.add_fast_2_2 := eq_refl.
Definition ieee_add_1_1_agrees : @IeeeModel.add_1_1 = @IeeeDraft.add_1_1 := eq_refl.
Definition ieee_mul_1_1_agrees : @IeeeModel.mul_1_1 = @IeeeDraft.mul_1_1 := eq_refl.
Definition ieee_neg_2_agrees : @IeeeModel.neg_2 = @IeeeDraft.neg_2 := eq_refl.
Definition ieee_abs_2_agrees : @IeeeModel.abs_2 = @IeeeDraft.abs_2 := eq_refl.
Definition ieee_sub_2_2_agrees : @IeeeModel.sub_2_2 = @IeeeDraft.sub_2_2 := eq_refl.
Definition ieee_sub_2_1_agrees : @IeeeModel.sub_2_1 = @IeeeDraft.sub_2_1 := eq_refl.
Definition ieee_sub_1_2_agrees : @IeeeModel.sub_1_2 = @IeeeDraft.sub_1_2 := eq_refl.
Definition ieee_mul_pow2_2_agrees : @IeeeModel.mul_pow2_2 = @IeeeDraft.mul_pow2_2 := eq_refl.
Definition ieee_lt_2_2_agrees : @IeeeModel.lt_2_2 = @IeeeDraft.lt_2_2 := eq_refl.
Definition ieee_le_2_2_agrees : @IeeeModel.le_2_2 = @IeeeDraft.le_2_2 := eq_refl.
Definition ieee_eq_2_2_agrees : @IeeeModel.eq_2_2 = @IeeeDraft.eq_2_2 := eq_refl.
Definition ieee_lt_2_1_agrees : @IeeeModel.lt_2_1 = @IeeeDraft.lt_2_1 := eq_refl.
Definition ieee_le_2_1_agrees : @IeeeModel.le_2_1 = @IeeeDraft.le_2_1 := eq_refl.
Definition ieee_eq_2_1_agrees : @IeeeModel.eq_2_1 = @IeeeDraft.eq_2_1 := eq_refl.
Definition ieee_lt_1_2_agrees : @IeeeModel.lt_1_2 = @IeeeDraft.lt_1_2 := eq_refl.
Definition ieee_le_1_2_agrees : @IeeeModel.le_1_2 = @IeeeDraft.le_1_2 := eq_refl.
Definition ieee_to_nearest_2_agrees : @IeeeModel.to_nearest_2 = @IeeeDraft.to_nearest_2 := eq_refl.
Definition ieee_to_down_2_agrees : @IeeeModel.to_down_2 = @IeeeDraft.to_down_2 := eq_refl.
Definition ieee_to_up_2_agrees : @IeeeModel.to_up_2 = @IeeeDraft.to_up_2 := eq_refl.
Definition ieee_abs_upper_2_agrees : @IeeeModel.abs_upper_2 = @IeeeDraft.abs_upper_2 := eq_refl.
Definition ieee_radd_agrees : @IeeeModel.radd = @IeeeDraft.radd := eq_refl.
Definition ieee_rmul_agrees : @IeeeModel.rmul = @IeeeDraft.rmul := eq_refl.
Definition ieee_ball_add_1_agrees : @IeeeModel.ball_add_1 = @IeeeDraft.ball_add_1 := eq_refl.
Definition ieee_ball_sub_1_agrees : @IeeeModel.ball_sub_1 = @IeeeDraft.ball_sub_1 := eq_refl.
Definition ieee_ball_mul_1_agrees : @IeeeModel.ball_mul_1 = @IeeeDraft.ball_mul_1 := eq_refl.
Definition ieee_ball_neg_1_agrees : @IeeeModel.ball_neg_1 = @IeeeDraft.ball_neg_1 := eq_refl.
Definition ieee_ball_scale_1_agrees : @IeeeModel.ball_scale_1 = @IeeeDraft.ball_scale_1 := eq_refl.
Definition ieee_ball_add_2_agrees : @IeeeModel.ball_add_2 = @IeeeDraft.ball_add_2 := eq_refl.
Definition ieee_ball_sub_2_agrees : @IeeeModel.ball_sub_2 = @IeeeDraft.ball_sub_2 := eq_refl.
Definition ieee_ball_mul_2_agrees : @IeeeModel.ball_mul_2 = @IeeeDraft.ball_mul_2 := eq_refl.
Definition ieee_ball_neg_2_agrees : @IeeeModel.ball_neg_2 = @IeeeDraft.ball_neg_2 := eq_refl.
Definition ieee_ball_scale_2_agrees : @IeeeModel.ball_scale_2 = @IeeeDraft.ball_scale_2 := eq_refl.
Definition ieee_add_2_2_full_agrees : @IeeeModel.add_2_2_full = @IeeeDraft.add_2_2_full := eq_refl.
Definition ieee_add_fast_2_2_full_agrees : @IeeeModel.add_fast_2_2_full = @IeeeDraft.add_fast_2_2_full := eq_refl.
Definition ieee_sub_2_2_full_agrees : @IeeeModel.sub_2_2_full = @IeeeDraft.sub_2_2_full := eq_refl.
Definition ieee_add_2_1_full_agrees : @IeeeModel.add_2_1_full = @IeeeDraft.add_2_1_full := eq_refl.
Definition ieee_sub_2_1_full_agrees : @IeeeModel.sub_2_1_full = @IeeeDraft.sub_2_1_full := eq_refl.
Definition ieee_sub_1_2_full_agrees : @IeeeModel.sub_1_2_full = @IeeeDraft.sub_1_2_full := eq_refl.
Definition ieee_mul_2_2_full_agrees : @IeeeModel.mul_2_2_full = @IeeeDraft.mul_2_2_full := eq_refl.
Definition ieee_mul_2_1_full_agrees : @IeeeModel.mul_2_1_full = @IeeeDraft.mul_2_1_full := eq_refl.
Definition ieee_mul_pow2_2_full_agrees : @IeeeModel.mul_pow2_2_full = @IeeeDraft.mul_pow2_2_full := eq_refl.
Definition ieee_ball_add_1_full_agrees : @IeeeModel.ball_add_1_full = @IeeeDraft.ball_add_1_full := eq_refl.
Definition ieee_ball_sub_1_full_agrees : @IeeeModel.ball_sub_1_full = @IeeeDraft.ball_sub_1_full := eq_refl.
Definition ieee_ball_mul_1_full_agrees : @IeeeModel.ball_mul_1_full = @IeeeDraft.ball_mul_1_full := eq_refl.
Definition ieee_ball_scale_1_full_agrees : @IeeeModel.ball_scale_1_full = @IeeeDraft.ball_scale_1_full := eq_refl.
Definition ieee_ball_add_2_full_agrees : @IeeeModel.ball_add_2_full = @IeeeDraft.ball_add_2_full := eq_refl.
Definition ieee_ball_sub_2_full_agrees : @IeeeModel.ball_sub_2_full = @IeeeDraft.ball_sub_2_full := eq_refl.
Definition ieee_ball_mul_2_full_agrees : @IeeeModel.ball_mul_2_full = @IeeeDraft.ball_mul_2_full := eq_refl.
Definition ieee_ball_scale_2_full_agrees : @IeeeModel.ball_scale_2_full = @IeeeDraft.ball_scale_2_full := eq_refl.
Definition ieee_make_2_agrees : @IeeeModel.make_2 = @IeeeDraft.make_2 := eq_refl.
Definition ieee_make_2_limbs_agrees : @IeeeModel.make_2_limbs = @IeeeDraft.make_2_limbs := eq_refl.
(* the draft guards c first and names the guarded center h; the kernel (milestone1.md) guards
   r first and names it c0. The two agree by conversion, which substitutes the lets. *)
Definition ieee_ball_make_1_agrees : @IeeeModel.ball_make_1 = @IeeeDraft.ball_make_1 := eq_refl.
Definition ieee_ball_make_2_agrees : @IeeeModel.ball_make_2 = @IeeeDraft.ball_make_2 := eq_refl.
Definition ieee_fast_two_sum_prog_agrees : IeeeModel.fast_two_sum_prog = IeeeDraft.fast_two_sum_prog := eq_refl.
Definition ieee_two_prod_prog_agrees : IeeeModel.two_prod_prog = IeeeDraft.two_prod_prog := eq_refl.
Definition ieee_two_sum_prog_agrees : IeeeModel.two_sum_prog = IeeeDraft.two_sum_prog := eq_refl.
Definition ieee_add_2_2_prog_agrees : IeeeModel.add_2_2_prog = IeeeDraft.add_2_2_prog := eq_refl.
Definition ieee_mul_2_2_prog_agrees : IeeeModel.mul_2_2_prog = IeeeDraft.mul_2_2_prog := eq_refl.
Definition ieee_add_2_1_prog_agrees : IeeeModel.add_2_1_prog = IeeeDraft.add_2_1_prog := eq_refl.
Definition ieee_mul_2_1_prog_agrees : IeeeModel.mul_2_1_prog = IeeeDraft.mul_2_1_prog := eq_refl.
Definition ieee_add_fast_2_2_prog_agrees : IeeeModel.add_fast_2_2_prog = IeeeDraft.add_fast_2_2_prog := eq_refl.
Definition ieee_sub_2_2_prog_agrees : IeeeModel.sub_2_2_prog = IeeeDraft.sub_2_2_prog := eq_refl.
Definition ieee_sub_2_1_prog_agrees : IeeeModel.sub_2_1_prog = IeeeDraft.sub_2_1_prog := eq_refl.
Definition ieee_sub_1_2_prog_agrees : IeeeModel.sub_1_2_prog = IeeeDraft.sub_1_2_prog := eq_refl.
Definition ieee_mul_pow2_2_prog_agrees : IeeeModel.mul_pow2_2_prog = IeeeDraft.mul_pow2_2_prog := eq_refl.

(** * The IEEE-model statements (IeeeStatementsDraft.v, IeeeExtStatementsDraft.v) *)

Definition ieee_fast_two_sum_ieee_spec_agrees : IeeeStatements.fast_two_sum_ieee_spec = IeeeStatementsDraft.fast_two_sum_ieee_spec := eq_refl.
Definition ieee_two_prod_ieee_spec_agrees : IeeeStatements.two_prod_ieee_spec = IeeeStatementsDraft.two_prod_ieee_spec := eq_refl.
Definition ieee_add_2_2_ieee_bridge_spec_agrees : IeeeStatements.add_2_2_ieee_bridge_spec = IeeeStatementsDraft.add_2_2_ieee_bridge_spec := eq_refl.
Definition ieee_add_2_2_ieee_spec_agrees : IeeeStatements.add_2_2_ieee_spec = IeeeStatementsDraft.add_2_2_ieee_spec := eq_refl.
Definition ieee_add_2_2_ieee_finite_spec_agrees : IeeeStatements.add_2_2_ieee_finite_spec = IeeeStatementsDraft.add_2_2_ieee_finite_spec := eq_refl.
Definition ieee_mul_2_2_ieee_bridge_spec_agrees : IeeeStatements.mul_2_2_ieee_bridge_spec = IeeeStatementsDraft.mul_2_2_ieee_bridge_spec := eq_refl.
Definition ieee_mul_2_2_ieee_spec_agrees : IeeeStatements.mul_2_2_ieee_spec = IeeeStatementsDraft.mul_2_2_ieee_spec := eq_refl.
Definition ieee_mul_2_2_ieee_finite_spec_agrees : IeeeStatements.mul_2_2_ieee_finite_spec = IeeeStatementsDraft.mul_2_2_ieee_finite_spec := eq_refl.
Definition ieee_add_2_1_ieee_bridge_spec_agrees : IeeeStatements.add_2_1_ieee_bridge_spec = IeeeStatementsDraft.add_2_1_ieee_bridge_spec := eq_refl.
Definition ieee_add_2_1_ieee_spec_agrees : IeeeStatements.add_2_1_ieee_spec = IeeeStatementsDraft.add_2_1_ieee_spec := eq_refl.
Definition ieee_mul_2_1_ieee_bridge_spec_agrees : IeeeStatements.mul_2_1_ieee_bridge_spec = IeeeStatementsDraft.mul_2_1_ieee_bridge_spec := eq_refl.
Definition ieee_mul_2_1_ieee_spec_agrees : IeeeStatements.mul_2_1_ieee_spec = IeeeStatementsDraft.mul_2_1_ieee_spec := eq_refl.
Definition ieee_add_fast_2_2_ieee_bridge_spec_agrees : IeeeStatements.add_fast_2_2_ieee_bridge_spec = IeeeStatementsDraft.add_fast_2_2_ieee_bridge_spec := eq_refl.
Definition ieee_add_fast_2_2_ieee_spec_agrees : IeeeStatements.add_fast_2_2_ieee_spec = IeeeStatementsDraft.add_fast_2_2_ieee_spec := eq_refl.
Definition ieee_sub_2_2_ieee_bridge_spec_agrees : IeeeStatements.sub_2_2_ieee_bridge_spec = IeeeStatementsDraft.sub_2_2_ieee_bridge_spec := eq_refl.
Definition ieee_sub_2_2_ieee_spec_agrees : IeeeStatements.sub_2_2_ieee_spec = IeeeStatementsDraft.sub_2_2_ieee_spec := eq_refl.
Definition ieee_sub_2_1_ieee_bridge_spec_agrees : IeeeStatements.sub_2_1_ieee_bridge_spec = IeeeStatementsDraft.sub_2_1_ieee_bridge_spec := eq_refl.
Definition ieee_sub_2_1_ieee_spec_agrees : IeeeStatements.sub_2_1_ieee_spec = IeeeStatementsDraft.sub_2_1_ieee_spec := eq_refl.
Definition ieee_sub_1_2_ieee_bridge_spec_agrees : IeeeStatements.sub_1_2_ieee_bridge_spec = IeeeStatementsDraft.sub_1_2_ieee_bridge_spec := eq_refl.
Definition ieee_sub_1_2_ieee_spec_agrees : IeeeStatements.sub_1_2_ieee_spec = IeeeStatementsDraft.sub_1_2_ieee_spec := eq_refl.
Definition ieee_mul_pow2_2_ieee_bridge_spec_agrees : IeeeStatements.mul_pow2_2_ieee_bridge_spec = IeeeStatementsDraft.mul_pow2_2_ieee_bridge_spec := eq_refl.
Definition ieee_mul_pow2_2_ieee_spec_agrees : IeeeStatements.mul_pow2_2_ieee_spec = IeeeStatementsDraft.mul_pow2_2_ieee_spec := eq_refl.
Definition ieee_add_2_2_ieee_finite_result_spec_agrees : IeeeStatements.add_2_2_ieee_finite_result_spec = IeeeStatementsDraft.add_2_2_ieee_finite_result_spec := eq_refl.
Definition ieee_add_fast_2_2_ieee_finite_spec_agrees : IeeeStatements.add_fast_2_2_ieee_finite_spec = IeeeStatementsDraft.add_fast_2_2_ieee_finite_spec := eq_refl.
Definition ieee_add_fast_2_2_ieee_finite_result_spec_agrees : IeeeStatements.add_fast_2_2_ieee_finite_result_spec = IeeeStatementsDraft.add_fast_2_2_ieee_finite_result_spec := eq_refl.
Definition ieee_sub_2_2_ieee_finite_spec_agrees : IeeeStatements.sub_2_2_ieee_finite_spec = IeeeStatementsDraft.sub_2_2_ieee_finite_spec := eq_refl.
Definition ieee_sub_2_2_ieee_finite_result_spec_agrees : IeeeStatements.sub_2_2_ieee_finite_result_spec = IeeeStatementsDraft.sub_2_2_ieee_finite_result_spec := eq_refl.
Definition ieee_add_2_1_ieee_finite_spec_agrees : IeeeStatements.add_2_1_ieee_finite_spec = IeeeStatementsDraft.add_2_1_ieee_finite_spec := eq_refl.
Definition ieee_add_2_1_ieee_finite_result_spec_agrees : IeeeStatements.add_2_1_ieee_finite_result_spec = IeeeStatementsDraft.add_2_1_ieee_finite_result_spec := eq_refl.
Definition ieee_sub_2_1_ieee_finite_spec_agrees : IeeeStatements.sub_2_1_ieee_finite_spec = IeeeStatementsDraft.sub_2_1_ieee_finite_spec := eq_refl.
Definition ieee_sub_2_1_ieee_finite_result_spec_agrees : IeeeStatements.sub_2_1_ieee_finite_result_spec = IeeeStatementsDraft.sub_2_1_ieee_finite_result_spec := eq_refl.
Definition ieee_sub_1_2_ieee_finite_spec_agrees : IeeeStatements.sub_1_2_ieee_finite_spec = IeeeStatementsDraft.sub_1_2_ieee_finite_spec := eq_refl.
Definition ieee_sub_1_2_ieee_finite_result_spec_agrees : IeeeStatements.sub_1_2_ieee_finite_result_spec = IeeeStatementsDraft.sub_1_2_ieee_finite_result_spec := eq_refl.
Definition ieee_mul_2_1_ieee_finite_spec_agrees : IeeeStatements.mul_2_1_ieee_finite_spec = IeeeStatementsDraft.mul_2_1_ieee_finite_spec := eq_refl.
(* DIFFERS: the generated statement has the hypothesis (exists n : Z, val c = bpow radix2 n), the
   requirement power_of_two of mul_pow2_2, which the draft leaves out. *)
Fail Definition ieee_mul_pow2_2_ieee_finite_spec_agrees : IeeeStatements.mul_pow2_2_ieee_finite_spec = IeeeStatementsDraft.mul_pow2_2_ieee_finite_spec := eq_refl.
Definition ieee_add_2_2_full_spec_agrees : IeeeStatements.add_2_2_full_spec = IeeeExtStatementsDraft.add_2_2_full_spec := eq_refl.
Definition ieee_mul_2_2_full_spec_agrees : IeeeStatements.mul_2_2_full_spec = IeeeExtStatementsDraft.mul_2_2_full_spec := eq_refl.
Definition ieee_ball_add_1_full_spec_agrees : IeeeStatements.ball_add_1_full_spec = IeeeExtStatementsDraft.ball_add_1_full_spec := eq_refl.
Definition ieee_ball_sub_1_full_spec_agrees : IeeeStatements.ball_sub_1_full_spec = IeeeExtStatementsDraft.ball_sub_1_full_spec := eq_refl.
Definition ieee_ball_mul_1_full_spec_agrees : IeeeStatements.ball_mul_1_full_spec = IeeeExtStatementsDraft.ball_mul_1_full_spec := eq_refl.
Definition ieee_ball_scale_1_full_spec_agrees : IeeeStatements.ball_scale_1_full_spec = IeeeExtStatementsDraft.ball_scale_1_full_spec := eq_refl.
Definition ieee_ball_add_2_full_spec_agrees : IeeeStatements.ball_add_2_full_spec = IeeeExtStatementsDraft.ball_add_2_full_spec := eq_refl.
Definition ieee_ball_sub_2_full_spec_agrees : IeeeStatements.ball_sub_2_full_spec = IeeeExtStatementsDraft.ball_sub_2_full_spec := eq_refl.
Definition ieee_ball_mul_2_full_spec_agrees : IeeeStatements.ball_mul_2_full_spec = IeeeExtStatementsDraft.ball_mul_2_full_spec := eq_refl.
Definition ieee_ball_scale_2_full_spec_agrees : IeeeStatements.ball_scale_2_full_spec = IeeeExtStatementsDraft.ball_scale_2_full_spec := eq_refl.
Definition ieee_ball_neg_1_ieee_spec_agrees : IeeeStatements.ball_neg_1_ieee_spec = IeeeExtStatementsDraft.ball_neg_1_ieee_spec := eq_refl.
Definition ieee_ball_neg_2_ieee_spec_agrees : IeeeStatements.ball_neg_2_ieee_spec = IeeeExtStatementsDraft.ball_neg_2_ieee_spec := eq_refl.
Definition ieee_add_fast_2_2_full_spec_agrees : IeeeStatements.add_fast_2_2_full_spec = IeeeExtStatementsDraft.add_fast_2_2_full_spec := eq_refl.
Definition ieee_sub_2_2_full_spec_agrees : IeeeStatements.sub_2_2_full_spec = IeeeExtStatementsDraft.sub_2_2_full_spec := eq_refl.
Definition ieee_add_2_1_full_spec_agrees : IeeeStatements.add_2_1_full_spec = IeeeExtStatementsDraft.add_2_1_full_spec := eq_refl.
Definition ieee_sub_2_1_full_spec_agrees : IeeeStatements.sub_2_1_full_spec = IeeeExtStatementsDraft.sub_2_1_full_spec := eq_refl.
Definition ieee_sub_1_2_full_spec_agrees : IeeeStatements.sub_1_2_full_spec = IeeeExtStatementsDraft.sub_1_2_full_spec := eq_refl.
Definition ieee_mul_2_1_full_spec_agrees : IeeeStatements.mul_2_1_full_spec = IeeeExtStatementsDraft.mul_2_1_full_spec := eq_refl.
Definition ieee_mul_pow2_2_full_spec_agrees : IeeeStatements.mul_pow2_2_full_spec = IeeeExtStatementsDraft.mul_pow2_2_full_spec := eq_refl.
Definition ieee_make_2_spec_agrees : IeeeStatements.make_2_spec = IeeeExtStatementsDraft.make_2_spec := eq_refl.
Definition ieee_make_2_limbs_spec_agrees : IeeeStatements.make_2_limbs_spec = IeeeExtStatementsDraft.make_2_limbs_spec := eq_refl.
Definition ieee_neg_2_ieee_spec_agrees : IeeeStatements.neg_2_ieee_spec = IeeeExtStatementsDraft.neg_2_ieee_spec := eq_refl.
Definition ieee_abs_2_ieee_spec_agrees : IeeeStatements.abs_2_ieee_spec = IeeeExtStatementsDraft.abs_2_ieee_spec := eq_refl.
Definition ieee_lt_2_2_ieee_spec_agrees : IeeeStatements.lt_2_2_ieee_spec = IeeeExtStatementsDraft.lt_2_2_ieee_spec := eq_refl.
Definition ieee_le_2_2_ieee_spec_agrees : IeeeStatements.le_2_2_ieee_spec = IeeeExtStatementsDraft.le_2_2_ieee_spec := eq_refl.
Definition ieee_eq_2_2_ieee_spec_agrees : IeeeStatements.eq_2_2_ieee_spec = IeeeExtStatementsDraft.eq_2_2_ieee_spec := eq_refl.
Definition ieee_lt_2_1_ieee_spec_agrees : IeeeStatements.lt_2_1_ieee_spec = IeeeExtStatementsDraft.lt_2_1_ieee_spec := eq_refl.
Definition ieee_le_2_1_ieee_spec_agrees : IeeeStatements.le_2_1_ieee_spec = IeeeExtStatementsDraft.le_2_1_ieee_spec := eq_refl.
Definition ieee_eq_2_1_ieee_spec_agrees : IeeeStatements.eq_2_1_ieee_spec = IeeeExtStatementsDraft.eq_2_1_ieee_spec := eq_refl.
Definition ieee_lt_1_2_ieee_spec_agrees : IeeeStatements.lt_1_2_ieee_spec = IeeeExtStatementsDraft.lt_1_2_ieee_spec := eq_refl.
Definition ieee_le_1_2_ieee_spec_agrees : IeeeStatements.le_1_2_ieee_spec = IeeeExtStatementsDraft.le_1_2_ieee_spec := eq_refl.
Definition ieee_to_nearest_2_ieee_spec_agrees : IeeeStatements.to_nearest_2_ieee_spec = IeeeExtStatementsDraft.to_nearest_2_ieee_spec := eq_refl.
Definition ieee_to_down_2_ieee_spec_agrees : IeeeStatements.to_down_2_ieee_spec = IeeeExtStatementsDraft.to_down_2_ieee_spec := eq_refl.
Definition ieee_to_up_2_ieee_spec_agrees : IeeeStatements.to_up_2_ieee_spec = IeeeExtStatementsDraft.to_up_2_ieee_spec := eq_refl.
Definition ieee_abs_upper_2_ieee_spec_agrees : IeeeStatements.abs_upper_2_ieee_spec = IeeeExtStatementsDraft.abs_upper_2_ieee_spec := eq_refl.
Definition ieee_radd_ieee_spec_agrees : IeeeStatements.radd_ieee_spec = IeeeExtStatementsDraft.radd_ieee_spec := eq_refl.
Definition ieee_rmul_ieee_spec_agrees : IeeeStatements.rmul_ieee_spec = IeeeExtStatementsDraft.rmul_ieee_spec := eq_refl.
Definition ieee_ball_make_1_spec_agrees : IeeeStatements.ball_make_1_spec = IeeeExtStatementsDraft.ball_make_1_spec := eq_refl.
Definition ieee_ball_make_2_spec_agrees : IeeeStatements.ball_make_2_spec = IeeeExtStatementsDraft.ball_make_2_spec := eq_refl.
