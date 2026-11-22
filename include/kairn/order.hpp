/// @file
/// The order of a loop over arrays (docs/developer/design/milestone2.md, "Folds, the extension of
/// the IR"): kairn::sequential, the tag with which a program asks a function on arrays for the
/// sequential order by name. Its one home: kairn/batch.hpp and kairn/ball_vector.hpp include it.
///
/// Every loop over arrays is generated in two orders. In the sequential order element i is done
/// after element i - 1. In the lane order of W lanes the first W floor(n / W) elements are dealt to W
/// lanes, element i to lane i mod W, each lane is done from the start, the lanes are combined from
/// lane 0 upward and the remaining elements are done after them; it is what the packed code of
/// AVX2 and NEON computes, with W the lanes of Packed<T, 1> (packed.hpp). A function on arrays
/// without the tag computes in the fast order of the translation unit, the lane order of the
/// register where Packed has more than one lane and the sequential order where it has one; with
/// kairn::sequential, in the sequential order, in every build. The tag is the first argument of every
/// function that takes it, as the execution policies of the standard library are: of an operation
/// of BallVector (ball_vector.hpp) and of sum, sum_fast and dot (batch.hpp). What
/// each function states holds in both orders: its statements are proved for the sequential order
/// and for the lane order of every W. Where the two orders can give other bits, each function says
/// so.
#pragma once

namespace kairn {

/// The type of kairn::sequential.
struct Sequential {
    /// Explicit, so that {} is never taken for the tag.
    explicit constexpr Sequential() noexcept = default;
};

/// The sequential order: as the first argument of an operation of BallVector,
/// `kairn::add(kairn::sequential, x, y, z)`, and of sum, sum_fast and dot,
/// `kairn::sum(kairn::sequential, x)`, it asks for the elements one after the other, in every build,
/// where the function without it computes in the fast order of the translation unit (the lane order
/// of Packed's register, or the sequential order where Packed has one lane).
inline constexpr Sequential sequential{};

}  // namespace kairn
